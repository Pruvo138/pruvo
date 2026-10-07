/*
 * foto-uretim.js — PRUVO ana sayfa "Fotoğrafından özel üretim" bölümü ekranı.
 *
 * - Veri: window.PRUVO_FOTO (foto-uretim-veri.js) — turler, ornekler, onay.
 * - API'ler: GET /api/shop/foto/acik, POST /api/shop/foto/onizleme,
 *   GET /api/shop/foto/durum, POST /api/shop/baslat,
 *   2D KONSEPT: POST /api/shop/foto/konsept, GET /api/shop/foto/konsept-durum.
 * - Bot: Cloudflare Turnstile (sitekey, script URL).
 * - Durum makinesi: kapali (bolum kapali) · S1 (form) · S2 (onizleme bekleniyor)
 *   · S3 (onizleme hazir) · S4 (siparis formu).
 * - ES5 IIFE; template literal yok, regex literal yok (yayin minifier uyumu);
 *   dis kutuphane yok. DOM yalniz createElement + textContent ile.
 */
(function () {
  "use strict";

  /* ============== SABITLER ============== */
  var ACIK_URL = "/api/shop/foto/acik";
  var ONIZLEME_URL = "/api/shop/foto/onizleme";
  var DURUM_URL = "/api/shop/foto/durum";
  var LITOFAN_URL = "/api/shop/foto/litofan";
  // 2D KONSEPT (Okan 7 Eki 14:5x): foto + "Nasıl olsun?" notu -> konsept; "Bunu kullan" -> 3D önizleme
  // girdisi. İSTEĞE BAĞLI ara adım: doğrudan "Önizleme oluştur" yolu AYNEN durur (konsept düşerse satış durmaz).
  var KONSEPT_URL = "/api/shop/foto/konsept";
  var KONSEPT_DURUM_URL = "/api/shop/foto/konsept-durum";
  var KONSEPT_YOKLAMA_MS = 3000;
  var KONSEPT_YOKLAMA_TAVAN = 60;
  var KONSEPT_METNI = "Konsept, notunuza göre çizilen bir önizlemedir.";
  // LITOFAN (deterministik kol): gri ton -> kalınlık (koyu = kalın), arkadan ışık benzetimi.
  var LITOFAN_KALINLIK_EN_AZ = 0.6;
  var LITOFAN_KALINLIK_EN_COK = 3.0;
  var LITOFAN_KENAR_PX = 1200;
  var LITOFAN_ORAN_EN_COK = 5;
  var LITOFAN_ONIZLEME_PX = 320;
  var LITOFAN_DURUSTLUK =
    "Önizleme, ışığa tutulduğunda görünecek görüntünün yaklaşık benzetimidir; birebir aynısı değildir.";
  var BASLAT_URL = "/api/shop/baslat";
  var TURNS_SITEKEY = "0x4AAAAAAE6AA20ln7MIOR9k";
  var TURNS_KAYNAK = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
  var MAKS_DOSYA_BAYT = 15 * 1024 * 1024;
  var MAKS_KENAR = 1600;
  var MIN_ADET = 1;
  var MAKS_ADET = 5;
  var YOKLAMA_MS = 3000;
  var YOKLAMA_TAVAN = 80;
  var WA = "https://wa.me/905451386526";
  var GIZLILIK_URL = "/gizlilik/";
  var TESLIMAT_URL = "/teslimat-iade/";
  var MESAFELI_URL = "/mesafeli-satis/";
  var ANA_BOLUM_ID = "fotoUretim";
  var STIL_ID = "fotoUretimStil";
  // YER TUTUCU — henüz açılmamış türler (Okan 7 Eki 21:5x(a) "9 kategorinin tamamı galeride görünsün";
  // BaBa 7 Eki 23:1x(a) "figür + büst Yakında kartı, kredi 0"). Liste ornekCiz'in SONUNA eklenir; kayıt
  // YOK (sunucu tarafı etkilenmez — sipariş/tür seçimi /acik aynen). Görsel değil metin (emoji) ikonu.
  var YER_TUTUCU = [
    { kod: "figur", ad: "Figür", ikon: "\u{1F5FF}" },
    { kod: "bust", ad: "Büst", ikon: "\u{1F464}" }
  ];
  var SS_IS = "pruvo_foto_is";
  var SS_SIPARIS = "pruvo_foto_siparis";
  // Render orneginin altindaki cumle TUR KAYDINDA (`ornek_notu`, mimar karari 7 Eki; AYNEN).
  // D/R turunde TARAYICI onizleyicisi YOKSA (manifest F.TARAYICI_ONIZLEYICI) ornek render + bu cumle;
  // onizlemeyi siparis oncesi ureteç koşucusu cikarir (/foto/onizleme kuyrugu).
  // "Nasıl olsun?" üretim notu: sunucu sınırıyla AYNI (shop/src/foto.js URETIM_NOTU_EN_COK).
  var URETIM_NOTU_EN_COK = 300;
  var NOT_HATA = {
    "not-uzun": "Not en çok " + URETIM_NOTU_EN_COK + " karakter olabilir.",
    "not-kisisel-veri": "Nota e-posta ya da telefon yazma; iletişim bilgilerini sipariş adımında alıyoruz.",
    "not-gecersiz": "Not okunamadı; yeniden yaz."
  };
  var ONIZLEME_SONRA = "Önizleme, üretim dosyasıyla birlikte hazırlanır; birkaç dakika sürebilir.";
  // Ureteç onizlemesinin yoklamasi: 5 sn aralik, en cok 180 sn (sonra "hazirlaninca gosterilecek").
  var URETEC_YOKLAMA_MS = 5000;
  var URETEC_YOKLAMA_TAVAN_MS = 180000;
  var PARAMETRE_HATA = {
    "parametre-aralik": "Değer izinli aralığın dışında.",
    "parametre-adim": "Değer izinli adıma uymuyor.",
    "parametre-secim": "Listeden bir seçenek seç.",
    "parametre-metin": "Metin alanını doldur (izinli uzunlukta).",
    "parametre-url": "Bağlantı https:// ile başlamalı."
  };
  /* Dürüstlük kutusu metni TÜR BAZLI: manifest `durustluk` (seçili türünki; durustlukGuncelle). */
  /* ============== REFERANSLAR ============== */
  var kok = typeof window !== "undefined" ? window :
    (typeof globalThis !== "undefined" ? globalThis : this);
  var F = kok.PRUVO_FOTO || null;
  var SECENEK = kok.PRUVO_SECENEK || null;

  /* ============== DOGRULAMA KALIPLARI (RegExp literal YOK) ============== */
  var isKalibi = new RegExp("^[a-f0-9]{32}$");
  var rakDisi = new RegExp("[^0-9]", "g");
  var epostaKalibi = new RegExp("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$");

  /* ============== DURUM ============== */
  var S = {
    adim: "kapali",
    acikVeri: null,
    tur: null,
    olcu: null,
    adet: 1,
    dosya: null,
    aydinlatmaOnay: false,
    captchaToken1: "",
    captchaToken2: "",
    is: null,
    gorsel: null,
    gecerlilik: null,
    ilerleme: null,
    bildirim: "",
    bildirimHata: false,
    yoksIs: null,
    yoksSayac: 0,
    alan: null,
    adimCubugu: null,
    alanTur: null,
    alanOlcu: null,
    alanForm: null,
    alanOnizlemeSonra: null,
    ornekBlok: null,
    parametre: {},
    alanDosya: null,
    yukleKutu: null,
    yukleGirdi: null,
    yukleEtiket: null,
    yukleSecili: null,
    yukleHata: null,
    yukleKabul: null,
    yukleOnizUrl: null,
    alanOnay: null,
    alanCap1: null,
    alanNotu: null,
    alanButon: null,
    alanAd: null,
    alanTel: null,
    alanEposta: null,
    alanAdres: null,
    alanSehir: null,
    alanNotM: null,
    alanSoz: null,
    alanCap2: null,
    alanOde: null,
    sozlesme: false,
    ad: "",
    tel: "",
    eposta: "",
    adres: "",
    sehir: "",
    musteriNotu: "",
    uretimNotu: "",
    alanUretimNotu: null,
    alanKonsept: null,
    konsept: null,
    konseptOturum: null,
    konseptKalan: null,
    konseptGorsel: null,
    konseptAsama: "",
    konseptHata: "",
    konseptSecili: null,
    konseptYoks: null,
    konseptSayac: 0,
    konseptGonderBtn: [],
    konseptKullanBtn: null,
    fotoUrl: null,
    vitrinTur: null,
    fiyatEl: null,
    olcuAltEl: null,
    galeriListe: [],
    galeriSecili: 0,
    galeriKutu: null,
    galeriSeciliKod: null,
    buyukKart: null,
    isik: null
  };

  /* ============== DOM YARDIMCILAR ============== */
  function el(etiket, sinif, metin) {
    var n = document.createElement(etiket);
    if (sinif) n.className = sinif;
    if (metin != null) n.textContent = String(metin);
    return n;
  }
  function ek(parent) {
    for (var i = 1; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null) continue;
      if (typeof c === "string") parent.appendChild(document.createTextNode(c));
      else parent.appendChild(c);
    }
    return parent;
  }
  function tlMetni(kurus) {
    if (SECENEK && typeof SECENEK.kurusMetni === "function") return SECENEK.kurusMetni(kurus);
    if (kurus == null) return "";
    var t = (kurus / 100).toFixed(2);
    return t.replace(".", ",") + " TL";
  }
  function kargoUcreti(urunToplamKurus) {
    if (SECENEK && typeof SECENEK.kargoKurus === "function") return SECENEK.kargoKurus(urunToplamKurus);
    if (!(urunToplamKurus > 0)) return 0;
    return urunToplamKurus >= 250000 ? 0 : 25000;
  }
  function yerelSaat(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var gun = String(d.getDate());
    var ay = String(d.getMonth() + 1);
    var saat = String(d.getHours());
    var dak = String(d.getMinutes());
    if (gun.length < 2) gun = "0" + gun;
    if (ay.length < 2) ay = "0" + ay;
    if (saat.length < 2) saat = "0" + saat;
    if (dak.length < 2) dak = "0" + dak;
    return gun + "." + ay + "." + d.getFullYear() + " " + saat + ":" + dak;
  }

  /* ============== STIL ENJEKSIYONU ============== */
  function stilEnjeket() {
    if (document.getElementById(STIL_ID)) return;
    var stil = document.createElement("style");
    stil.id = STIL_ID;
    stil.textContent = cssMetin;
    document.head.appendChild(stil);
  }
  var cssMetin =
    ".foto-uretim{margin:0 -20px 22px;padding:28px 20px;min-height:100vh;" +
    "min-height:100svh;background:var(--navy);color:#fff;" +
    "box-shadow:0 0 0 100vmax var(--navy);clip-path:inset(0 -100vmax);}" +
    ".foto-uretim[hidden]{display:none!important;}" +
    ".foto-uretim-icerik{max-width:1100px;margin:0 auto;}" +
    ".foto-uretim-baslik{font-size:24px;font-weight:700;margin:0 0 8px;" +
    "color:#fff;line-height:1.3;}" +
    ".foto-uretim-alt{font-size:15px;margin:0 0 18px;color:#cfd6e0;line-height:1.5;}" +
    ".foto-uretim-durustluk{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:14px 18px;margin:0 0 20px;font-size:14px;line-height:1.5;}" +
    ".foto-uretim-durustluk p{margin:0;}" +
    ".foto-uretim-blok{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:16px;margin:0 0 14px;}" +
    ".foto-uretim-blok-baslik{font-size:16px;font-weight:700;margin:0 0 12px;}" +
    ".foto-uretim-ornek-grup{margin:0 0 16px;}" +
    ".foto-uretim-ornek-grup:last-child{margin-bottom:0;}" +
    ".foto-uretim-ornek-gorseller{display:flex;gap:10px;margin:0 0 6px;}" +
    ".foto-uretim-ornek-gorsel{flex:1;aspect-ratio:1/1;width:100%;" +
    "height:auto;max-width:100%;object-fit:cover;border-radius:6px;" +
    "background:#eef0f3;display:block;}" +
    ".foto-uretim-ornek-baslik{font-size:13px;color:var(--navy);line-height:1.4;}" +
    ".foto-uretim-ornek-etiket{font-size:11px;color:#5b6573;margin-top:2px;}" +
    ".foto-uretim-ornek-not{font-size:12px;color:#5b6573;line-height:1.45;margin:4px 0 0;}" +
    ".foto-uretim-adimlar{display:flex;align-items:center;gap:8px;margin:14px 0;" +
    "flex-wrap:wrap;}" +
    ".foto-uretim-adim{flex:1 1 120px;padding:8px 10px;background:rgba(255,255,255,0.12);" +
    "border-radius:6px;text-align:center;font-size:13px;color:#fff;font-weight:600;}" +
    ".foto-uretim-adim.aktif{background:#d1332e;}" +
    ".foto-uretim-adim-ok{color:#fff;font-size:16px;}" +
    ".foto-uretim-alani{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:18px;margin-top:6px;}" +
    ".foto-uretim-durum{padding:8px 12px;border-radius:6px;background:#eef0f3;" +
    "font-size:14px;margin:0 0 12px;}" +
    ".foto-uretim-durum.hata{background:#fde7e7;color:#a3261e;}" +
    ".foto-uretim-form-grup{margin:0 0 14px;}" +
    ".foto-uretim-form-etiket{display:block;font-size:14px;font-weight:600;" +
    "margin:0 0 6px;}" +
    ".foto-uretim-form-secenek{display:block;padding:8px 10px;border:1px solid #d4dae3;" +
    "border-radius:6px;margin:0 0 6px;cursor:pointer;font-size:14px;}" +
    ".foto-uretim-form-secenek-girdi{display:block;width:100%;max-width:100%;" +
    "padding:8px 10px;border:1px solid #d4dae3;border-radius:6px;font-size:14px;" +
    "box-sizing:border-box;margin:0 0 6px;}" +
    ".foto-uretim-form-secenek-inline{display:flex;align-items:flex-start;" +
    "gap:8px;padding:8px 10px;border:1px solid #d4dae3;border-radius:6px;" +
    "margin:0 0 6px;cursor:pointer;font-size:14px;}" +
    ".foto-uretim-form-secenek-inline input{flex-shrink:0;margin-top:3px;}" +
    ".foto-uretim-buton-birincil{background:#d1332e;color:#fff;border:none;" +
    "padding:11px 22px;border-radius:6px;font-size:15px;font-weight:600;" +
    "cursor:pointer;max-width:100%;}" +
    ".foto-uretim-buton-birincil[disabled]{background:#b0b8c0;cursor:not-allowed;}" +
    ".foto-uretim-buton-ikincil{background:transparent;color:var(--navy);" +
    "border:1px solid var(--navy);padding:9px 18px;border-radius:6px;" +
    "font-size:14px;cursor:pointer;max-width:100%;margin-top:8px;}" +
    ".foto-uretim-captcha{margin:14px 0;}" +
    ".foto-uretim-onizleme-img{display:block;max-width:100%;height:auto;" +
    "border-radius:6px;margin:10px 0;background:#eef0f3;}" +
    ".foto-uretim-ozet{background:#eef0f3;padding:12px;border-radius:6px;" +
    "font-size:14px;margin:10px 0;line-height:1.6;}" +
    ".foto-uretim-ayrinti{font-size:13px;color:#5b6573;margin:8px 0;line-height:1.5;}" +
    ".foto-uretim-aydinlatma{margin:8px 0;font-size:13px;}" +
    ".foto-uretim-aydinlatma summary{cursor:pointer;font-weight:600;}" +
    ".foto-uretim-aydinlatma p{margin:6px 0;}" +
    ".foto-uretim-kapat-a{color:#d1332e;text-decoration:underline;}" +
    ".foto-uretim-iliskili{display:flex;flex-wrap:wrap;gap:10px;align-items:center;" +
    "margin:8px 0;}" +
    ".foto-uretim-ilerleme-dis{height:8px;background:#eef0f3;border-radius:4px;" +
    "overflow:hidden;margin:8px 0;}" +
    ".foto-uretim-ilerleme-ic{height:100%;background:#d1332e;width:0;}" +
    ".foto-uretim-s1-buton-sira{margin-top:8px;}" +
    ".foto-uretim-serit{list-style:none;background:#fff;color:var(--navy);border-radius:14px;padding:22px 12px 18px;" +
    "margin:0 0 22px;display:flex;align-items:flex-start;justify-content:center;}" +
    ".foto-uretim-serit-adim{flex:0 1 200px;display:flex;flex-direction:column;align-items:center;" +
    "text-align:center;gap:6px;min-width:0;}" +
    ".foto-uretim-serit-no{width:48px;height:48px;border-radius:50%;background:var(--navy);color:#fff;" +
    "display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;}" +
    ".foto-uretim-serit-ikon{font-size:20px;line-height:1;color:#5b6573;}" +
    ".foto-uretim-serit-ad{font-size:15px;font-weight:700;color:var(--navy);}" +
    ".foto-uretim-serit-cizgi{flex:1 1 40px;height:1px;background:#c9d0da;margin-top:24px;min-width:12px;}" +
    ".foto-uretim-vitrin{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:24px;" +
    "background:#fff;color:var(--navy);border-radius:14px;padding:18px;margin:0 0 22px;}" +
    ".foto-uretim-galeri{display:flex;gap:12px;min-width:0;}" +
    ".foto-uretim-galeri-kucukler{display:flex;flex-direction:column;gap:8px;flex:0 0 68px;" +
    "max-height:560px;overflow-y:auto;scroll-snap-type:y proximity;}" +
    ".foto-uretim-galeri-kucuk{position:relative;display:block;flex:0 0 auto;width:64px;height:64px;padding:0;" +
    "border:2px solid transparent;border-radius:10px;background:#eef0f3;cursor:pointer;overflow:hidden;scroll-snap-align:start;}" +
    ".foto-uretim-yakinda{position:absolute;left:2px;top:2px;background:var(--navy);color:#fff;font-size:9px;" +
    "font-weight:700;line-height:1;padding:3px 4px;border-radius:4px;pointer-events:none;}" +
    ".foto-uretim-galeri-kucuk img{display:block;width:100%;height:100%;object-fit:cover;}" +
    ".foto-uretim-galeri-kucuk.secili{border-color:var(--navy);box-shadow:0 0 0 2px #fff inset;}" +
    ".foto-uretim-buyuk{flex:1 1 auto;min-width:0;}" +
    ".foto-uretim-buyuk-kart{position:relative;background:#e6ebf1;border-radius:14px;overflow:hidden;cursor:zoom-in;}" +
    ".foto-uretim-buyuk-kart:focus-visible{outline:2px solid var(--navy);outline-offset:2px;}" +
    ".foto-uretim-buyuk-kart .foto-uretim-yakinda{left:10px;top:10px;font-size:12px;padding:5px 8px;z-index:1;}" +
    ".foto-uretim-isik{position:fixed;top:0;right:0;bottom:0;left:0;z-index:2147483000;background:rgba(6,12,22,.94);" +
    "display:flex;align-items:center;justify-content:center;padding:56px 12px 24px;box-sizing:border-box;outline:none;}" +
    ".foto-uretim-isik-sahne{margin:0;max-width:min(92vw,1100px);max-height:100%;display:flex;flex-direction:column;" +
    "align-items:center;gap:10px;}" +
    ".foto-uretim-isik-img{display:block;max-width:100%;max-height:calc(100vh - 160px);width:auto;height:auto;" +
    "object-fit:contain;border-radius:8px;background:#e6ebf1;}" +
    ".foto-uretim-isik-alt{color:#e9edf3;font-size:13px;text-align:center;line-height:1.4;overflow-wrap:anywhere;}" +
    ".foto-uretim-isik-kapat,.foto-uretim-isik-ok{position:absolute;width:44px;height:44px;border:0;border-radius:50%;" +
    "background:rgba(255,255,255,.16);color:#fff;font-size:28px;line-height:1;cursor:pointer;padding:0;}" +
    ".foto-uretim-isik-kapat{top:8px;right:8px;}" +
    ".foto-uretim-isik-ok{top:50%;transform:translateY(-50%);}" +
    ".foto-uretim-isik-ok.onceki{left:8px;}.foto-uretim-isik-ok.sonraki{right:8px;}" +
    ".foto-uretim-isik button:focus-visible{outline:2px solid #fff;outline-offset:2px;}" +
    ".foto-uretim-buyuk-kart .foto-uretim-ornek-gorsel{border-radius:0;}" +
    // YER TUTUCU (figür, büst — henüz açılmamış türler): küçük resimde ikon, büyük kartta ikon + "Bu tür
    // yakında eklenecek."; lightbox yok (görsel yok). Görsel değil metin (emoji) — kaynak/kredi 0.
    ".foto-uretim-galeri-yer-ikon{display:flex;align-items:center;justify-content:center;" +
    "width:100%;height:100%;font-size:32px;line-height:1;color:var(--navy);}" +
    ".foto-uretim-buyuk-kart.yer-tutucu{cursor:default;}" +
    ".foto-uretim-yer-ikon-buyuk{display:flex;align-items:center;justify-content:center;" +
    "min-height:300px;font-size:120px;line-height:1;color:var(--navy);padding:40px 0;}" +
    ".foto-uretim-polaroid{position:absolute;right:6%;bottom:6%;width:38%;background:#fff;padding:6px 6px 18px;" +
    "border-radius:6px;transform:rotate(6deg);box-shadow:0 4px 14px rgba(0,0,0,.18);}" +
    ".foto-uretim-polaroid.sol{right:auto;left:6%;transform:rotate(-5deg);width:30%;}" +
    ".foto-uretim-polaroid-img{display:block;width:100%;height:auto;aspect-ratio:1/1;object-fit:cover;border-radius:3px;}" +
    ".foto-uretim-sag{min-width:0;display:flex;flex-direction:column;gap:10px;}" +
    ".foto-uretim-vitrin .foto-uretim-baslik{color:var(--navy);font-size:28px;margin:0;}" +
    ".foto-uretim-fiyat{font-size:24px;font-weight:700;color:#d1332e;margin:0;}" +
    ".foto-uretim-surgu{display:block;width:100%;max-width:100%;box-sizing:border-box;margin:8px 0 0;accent-color:#12294d;}" +
    ".foto-uretim-surgu-fiyat{font-size:18px;font-weight:700;color:#12294d;margin:6px 0 0;}" +
    ".foto-uretim-aciklama{font-size:15px;line-height:1.6;color:#5b6573;margin:0;}" +
    ".foto-uretim-yukle-kutu{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;" +
    "width:100%;min-height:150px;border:2px dashed #b9c2ce;border-radius:14px;background:#f4f6f9;" +
    "color:var(--navy);font-size:18px;font-weight:700;cursor:pointer;padding:16px;}" +
    ".foto-uretim-yukle-kutu{position:relative;box-sizing:border-box;min-width:0;}" +
    ".foto-uretim-yukle-kutu:hover,.foto-uretim-yukle-kutu:focus-within,.foto-uretim-yukle-kutu.surukle{border-color:var(--navy);}" +
    ".foto-uretim-yukle-kutu.surukle{background:#e9eef5;}" +
    ".foto-uretim-gizli-girdi{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;" +
    "clip:rect(0,0,0,0);white-space:nowrap;border:0;}" +
    ".foto-uretim-yukle-etiket{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;" +
    "width:100%;min-height:114px;cursor:pointer;}" +
    ".foto-uretim-gizli-girdi:focus-visible+.foto-uretim-yukle-etiket{outline:2px solid var(--navy);outline-offset:4px;}" +
    ".foto-uretim-yukle-secili{display:flex;align-items:center;gap:12px;width:100%;min-width:0;}" +
    ".foto-uretim-yukle-etiket[hidden],.foto-uretim-yukle-secili[hidden],.foto-uretim-yukle-hata[hidden]," +
    ".foto-uretim-yukle-kabul[hidden]{display:none;}" +
    ".foto-uretim-yukle-onizleme{width:64px;height:64px;flex:0 0 64px;object-fit:cover;border-radius:8px;background:#fff;}" +
    ".foto-uretim-yukle-ad{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" +
    "font-size:15px;font-weight:600;}" +
    ".foto-uretim-yukle-degistir{flex:0 0 auto;border:1px solid var(--navy);background:#fff;color:var(--navy);" +
    "border-radius:8px;padding:8px 12px;font-size:14px;font-weight:700;cursor:pointer;}" +
    ".foto-uretim-yukle-hata{margin:0;font-size:14px;font-weight:600;color:#d1332e;text-align:center;}" +
    ".foto-uretim-yukle-kabul{margin:-4px 0 0;font-size:13px;color:#5b6573;}" +
    ".foto-uretim-yukle-ikon{font-size:28px;line-height:1;}" +
    ".foto-uretim-guven{font-size:14px;color:var(--navy);margin:0;display:flex;align-items:center;gap:8px;}" +
    ".foto-uretim-guven-tik{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;" +
    "border-radius:50%;background:#2e8540;color:#fff;font-size:12px;flex:0 0 20px;}" +
    ".foto-uretim-adim2-baslik{font-size:18px;font-weight:700;color:#fff;margin:0 0 12px;}" +
    ".foto-uretim-not{width:100%;min-height:72px;resize:vertical;padding:8px 10px;border:1px solid #d4dae3;" +
    "border-radius:6px;font:inherit;font-size:14px;box-sizing:border-box;}" +
    ".foto-uretim-not-sayac{font-size:12px;color:#5b6573;text-align:right;}" +
    ".foto-uretim-konsept{margin:10px 0 0;}" +
    ".foto-uretim-konsept-kart{border:1px solid #d4dae3;border-radius:8px;padding:10px;margin:8px 0;}" +
    ".foto-uretim-konsept-gorseller{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;}" +
    ".foto-uretim-konsept-img{display:block;width:220px;max-width:100%;height:auto;border-radius:6px;background:#eef0f3;}" +
    ".foto-uretim-konsept-foto{display:block;width:72px;height:72px;object-fit:cover;border-radius:4px;" +
    "border:2px solid #fff;box-shadow:0 1px 4px rgba(18,41,77,.3);}" +
    ".foto-uretim-konsept-butonlar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px;}" +
    ".foto-uretim-konsept-butonlar .foto-uretim-buton-ikincil{margin-top:0;}" +
    ".foto-uretim-konsept-hata{color:#b3261e;}" +
    "img,input,button,textarea,select{max-width:100%;}" +
    ".foto-uretim *{overflow-wrap:anywhere;}" +
    "@media (max-width:760px){" +
    ".foto-uretim-vitrin{grid-template-columns:minmax(0,1fr);padding:12px;gap:16px;}" +
    ".foto-uretim-galeri{flex-direction:column-reverse;}" +
    ".foto-uretim-galeri-kucukler{flex-direction:row;flex:0 0 auto;max-width:100%;max-height:none;min-width:0;" +
    "overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;padding-bottom:2px;}" +
    ".foto-uretim-galeri-kucuk{flex:0 0 56px;width:56px;height:56px;}" +
    ".foto-uretim-vitrin .foto-uretim-baslik{font-size:22px;}" +
    "}" +
    "@media (max-width:640px){" +
    ".foto-uretim-ornek-gorseller{flex-direction:column;}" +
    ".foto-uretim-serit{padding:16px 6px 14px;}" +
    ".foto-uretim-serit-no{width:38px;height:38px;font-size:17px;}" +
    ".foto-uretim-serit-cizgi{margin-top:19px;}" +
    ".foto-uretim-serit-ad{font-size:13px;}" +
    "}";

  /* ============== TURNSTILE ============== */
  function turnsYukle(cb) {
    if (kok.turnstile && typeof kok.turnstile.render === "function") { cb(true); return; }
    var mevcut = document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]');
    if (mevcut) {
      var deneme = 0;
      var id = setInterval(function () {
        deneme++;
        if (kok.turnstile || deneme > 30) { clearInterval(id); cb(!!kok.turnstile); }
      }, 100);
      return;
    }
    var s = document.createElement("script");
    s.src = TURNS_KAYNAK;
    s.async = true;
    s.onload = function () { cb(true); };
    s.onerror = function () { cb(false); };
    document.head.appendChild(s);
  }
  function turnsRender(kutu, cb) {
    if (!kutu) { cb(""); return; }
    turnsYukle(function (ok) {
      if (!ok || !kok.turnstile) { cb(""); return; }
      try {
        var wid = kok.turnstile.render(kutu, {
          sitekey: TURNS_SITEKEY,
          callback: function (t) { cb(t || ""); },
          "error-callback": function () { cb(""); },
          "expired-callback": function () { cb(""); }
        });
        kutu.setAttribute("data-wid", String(wid));
      } catch (e) { cb(""); }
    });
  }
  function turnsTemizle(kutu) {
    if (!kutu) return;
    var wid = kutu.getAttribute("data-wid");
    if (wid && kok.turnstile && typeof kok.turnstile.remove === "function") {
      try { kok.turnstile.remove(wid); } catch (e) { }
    }
    kutu.removeAttribute("data-wid");
    while (kutu.firstChild) kutu.removeChild(kutu.firstChild);
  }
  function turnsSifirla(kutu) {
    if (!kutu) return;
    var wid = kutu.getAttribute("data-wid");
    if (wid && kok.turnstile && typeof kok.turnstile.reset === "function") {
      try { kok.turnstile.reset(wid); } catch (e) { }
    }
  }

  /* ============== GORSEL KUCULTME ============== */
  function kucultGorsel(dosya, cb) {
    if (!dosya) { cb(new Error("yok"), null); return; }
    if (dosya.size > MAKS_DOSYA_BAYT) { cb(new Error("boyut-buyuk"), null); return; }
    if (dosya.size < 100) { cb(new Error("boyut-kucuk"), null); return; }
    var okuyucu = new FileReader();
    okuyucu.onload = function (e) {
      var img = new Image();
      img.onload = function () {
        var w = img.width, h = img.height;
        if (!w || !h) { cb(new Error("boyut"), null); return; }
        var enUzun = w > h ? w : h;
        var olcek = enUzun > MAKS_KENAR ? MAKS_KENAR / enUzun : 1;
        var nw = Math.round(w * olcek), nh = Math.round(h * olcek);
        var tuval = document.createElement("canvas");
        tuval.width = nw; tuval.height = nh;
        var ctx = tuval.getContext("2d");
        ctx.drawImage(img, 0, 0, nw, nh);
        try {
          var dataUrl = tuval.toDataURL("image/jpeg", 0.9);
          cb(null, dataUrl);
        } catch (er) { cb(er, null); }
      };
      img.onerror = function () { cb(new Error("okuma"), null); };
      img.src = e.target.result;
    };
    okuyucu.onerror = function () { cb(new Error("dosya"), null); };
    okuyucu.readAsDataURL(dosya);
  }

  /* ============== AG ============== */
  function jsonGetir(url, cb) {
    fetch(url, { credentials: "same-origin" }).then(function (r) {
      var ok = r.ok;
      r.json().then(function (d) { cb(ok, r.status, d); }, function () { cb(ok, r.status, null); });
    }, function () { cb(false, 0, null); });
  }
  function jsonPost(url, govde, cb) {
    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(govde)
    }).then(function (r) {
      var ok = r.ok;
      r.json().then(function (d) { cb(ok, r.status, d); }, function () { cb(ok, r.status, null); });
    }, function () { cb(false, 0, null); });
  }

  /* ============== OTURUM DEPOSU ============== */
  function ssIsKaydet() {
    if (!S.is) return;
    var kayit = { is: S.is, tur: S.tur, olcu: S.olcu };
    if (litofanSecili() && S.secim) kayit.secim = S.secim;
    if (S.aydinlatmaOnay) kayit.onay = F.onay_surum;
    try { sessionStorage.setItem(SS_IS, JSON.stringify(kayit)); }
    catch (e) { }
  }
  function ssIsSil() {
    try { sessionStorage.removeItem(SS_IS); } catch (e) { }
    S.is = null;
  }
  function ssIsOku() {
    try {
      var ham = sessionStorage.getItem(SS_IS);
      if (!ham) return null;
      var p = JSON.parse(ham);
      if (!p || typeof p.is !== "string" || !isKalibi.test(p.is)) return null;
      return p;
    } catch (e) { return null; }
  }

  /* ============== YOKLAMA DURDURMA ============== */
  function yoksDurdur() {
    if (S.yoksIs) { clearInterval(S.yoksIs); S.yoksIs = null; }
    S.yoksSayac = 0;
  }

  /* ============== ADIM CUBUGU ============== */
  function adimGoster(n) {
    if (!S.adimCubugu) return;
    var dugumler = S.adimCubugu.childNodes;
    for (var i = 0; i < dugumler.length; i++) {
      var node = dugumler[i];
      if (node && node.nodeType === 1 && node.classList && node.classList.contains("foto-uretim-adim")) {
        var no = parseInt(node.getAttribute("data-no"), 10);
        if (no === n) node.classList.add("aktif"); else node.classList.remove("aktif");
      }
    }
  }

  /* ============== DURUM CUBUGU (siparis alani ustunde) ============== */
  function durumCubuguGoster() {
    if (!S.alan) return;
    var eski = S.alan.querySelector(".foto-uretim-durum");
    if (eski && eski.parentNode) eski.parentNode.removeChild(eski);
    if (!S.bildirim) return;
    var d = el("div", "foto-uretim-durum" + (S.bildirimHata ? " hata" : ""), S.bildirim);
    if (S.alan.firstChild) S.alan.insertBefore(d, S.alan.firstChild); else S.alan.appendChild(d);
  }

  /* ============== ANA YAPISI ============== */
  // Adım 2 etiketi tür SAYISINA göre: F = veri dosyası ya da /acik yanıtı (ikisi de .turler taşır).
  function adim2Etiketi(F) { return F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"; }

  /* ============== LITOFAN (deterministik kol) ============== */
  // Deterministik kol + tarayıcı önizleyicisi kayıtlı üreteç (bugün litofan).
  function litofanSecili() {
    var t = F && typeof F.turBul === "function" && S.tur ? F.turBul(S.tur) : null;
    return !!(t && F.kolu(S.tur) === "deterministik" && F.TARAYICI_ONIZLEYICI[t.uretec] === true);
  }
  // Deterministik kol, tarayıcı önizleyicisi YOK: örnek render + ONIZLEME_SONRA; önizlemeyi koşucu üretir.
  function onizlemeSonraSecili() {
    var t = F && typeof F.turBul === "function" && S.tur ? F.turBul(S.tur) : null;
    return !!(t && F.kolu(S.tur) === "deterministik" && F.TARAYICI_ONIZLEYICI[t.uretec] !== true);
  }
  function litofanKaydi() { return F && typeof F.turBul === "function" ? F.turBul(S.tur) : null; }
  // Türün girdisinde fotoğraf var mı (kayıt yoksa var say).
  function fotoGerekir() {
    var t = litofanKaydi();
    return !t || !t.girdi || t.girdi.indexOf("foto-1") >= 0 || t.girdi.indexOf("foto-1-3") >= 0;
  }
  // Türün girdisi SVG mi (logo kabartma): dosya alanı SVG alır, metni gövdede `svg` olarak gider.
  function svgGerekir() {
    var t = litofanKaydi();
    return !!(t && t.girdi && t.girdi.indexOf("svg") >= 0);
  }
  // Kayıttan varsayılan seçim: her malzeme bölgesinin ilk malzemesi, her renk bölgesinin ilk rengi.
  function litofanSecimKur() {
    var t = litofanKaydi();
    var sec = {};
    if (!t) return sec;
    var mb = t.malzemeler || {};
    for (var b in mb) {
      if (Object.prototype.hasOwnProperty.call(mb, b) && mb[b] && mb[b].length) {
        sec[b + "_malzeme"] = S.secim && mb[b].indexOf(S.secim[b + "_malzeme"]) >= 0 ? S.secim[b + "_malzeme"] : mb[b][0];
      }
    }
    var rb = t.renk_bolgeleri || [];
    for (var i = 0; i < rb.length; i++) {
      var r = rb[i].renkler || [];
      if (!r.length) continue;
      sec[rb[i].kod + "_renk"] = S.secim && r.indexOf(S.secim[rb[i].kod + "_renk"]) >= 0 ? S.secim[rb[i].kod + "_renk"] : r[0];
    }
    return sec;
  }
  function radyoGrubu(kutu, etiket, ad, liste, secili, cb) {
    var g = el("div", "foto-uretim-litofan-secim");
    g.appendChild(el("span", "foto-uretim-form-etiket", etiket));
    for (var i = 0; i < liste.length; i++) {
      var lbl = el("label", "foto-uretim-form-secenek-inline");
      var inp = el("input");
      inp.type = "radio"; inp.name = ad; inp.value = liste[i];
      if (secili === liste[i]) inp.checked = true;
      (function (deger) {
        inp.addEventListener("change", function (e) { if (e.target.checked) cb(deger); });
      })(liste[i]);
      ek(lbl, inp, " " + liste[i]);
      g.appendChild(lbl);
    }
    kutu.appendChild(g);
  }
  // Renk (ayak) + malzeme (panel/ayak) seçimi — kayıttan çizilir; tek seçenekli bölge yazıyla gösterilir.
  function doldurS1Litofan() {
    if (!S.alanSecim || !S.alanLitofan) return;
    while (S.alanSecim.firstChild) S.alanSecim.removeChild(S.alanSecim.firstChild);
    var t = litofanKaydi();
    var secimVar = !!(t && t.renk_bolgeleri && t.renk_bolgeleri.length);
    S.alanSecim.hidden = !secimVar;
    S.alanLitofan.hidden = !litofanSecili();
    doldurS1OnizlemeSonra();
    if (!secimVar) { if (litofanSecili()) litofanOnizle(); else guncelleS1Buton(); return; }
    S.secim = litofanSecimKur();
    S.alanSecim.appendChild(el("label", "foto-uretim-form-etiket", "Malzeme ve renk"));
    var rb = (t && t.renk_bolgeleri) || [];
    var mb = (t && t.malzemeler) || {};
    for (var i = 0; i < rb.length; i++) {
      (function (bolge) {
        var ml = mb[bolge.kod] || [];
        if (ml.length > 1) {
          radyoGrubu(S.alanSecim, bolge.ad + " — malzeme", "foto-litofan-" + bolge.kod + "-malzeme", ml,
            S.secim[bolge.kod + "_malzeme"], function (d) { S.secim[bolge.kod + "_malzeme"] = d; });
        }
        var rl = bolge.renkler || [];
        if (rl.length > 1) {
          radyoGrubu(S.alanSecim, bolge.ad + " — renk", "foto-litofan-" + bolge.kod + "-renk", rl,
            S.secim[bolge.kod + "_renk"], function (d) { S.secim[bolge.kod + "_renk"] = d; });
        } else if (rl.length === 1) {
          S.alanSecim.appendChild(el("p", "foto-uretim-ayrinti", bolge.ad + ": " + rl[0] +
            (ml.length === 1 ? " · " + ml[0] : "")));
        }
      })(rb[i]);
    }
    if (litofanSecili()) litofanOnizle(); else guncelleS1Buton();
  }
  // D/R türünde sipariş öncesi önizleme yoksa: türün örnek render'ı + ONIZLEME_SONRA.
  function doldurS1OnizlemeSonra() {
    if (!S.alanOnizlemeSonra) return;
    while (S.alanOnizlemeSonra.firstChild) S.alanOnizlemeSonra.removeChild(S.alanOnizlemeSonra.firstChild);
    var acik = onizlemeSonraSecili();
    S.alanOnizlemeSonra.hidden = !acik;
    if (!acik) return;
    var t = litofanKaydi();
    for (var i = 0; i < F.ornekler.length; i++) {
      var o = F.ornekler[i];
      if (o && o.tur === S.tur && F.ornekGecerli(o) && (o.render || o.baski)) {
        S.alanOnizlemeSonra.appendChild(el("p", "foto-uretim-form-etiket", "Örnek"));
        var img = el("img", "foto-uretim-ornek-gorsel");
        img.src = o.render || o.baski; img.alt = t.ad + " örnek";
        img.width = 300; img.height = 300; img.loading = "lazy"; img.decoding = "async";
        S.alanOnizlemeSonra.appendChild(img);
        break;
      }
    }
    S.alanOnizlemeSonra.appendChild(el("p", "foto-uretim-ayrinti", ONIZLEME_SONRA));
  }

  // FORM ALANLARI — türün `form` şemasından (sayi/secim/metin/url); doğrulama sunucuyla AYNI
  // fonksiyon (F.parametreDogrula). Şema boşsa alan gizli, gövdeye `parametreler` girmez.
  function formSemasi() {
    var t = litofanKaydi();
    return t && t.form && typeof t.form === "object" ? t.form : {};
  }
  function parametreGovde() {
    var form = formSemasi(), g = {};
    for (var a in form) {
      if (Object.prototype.hasOwnProperty.call(form, a) && S.parametre[a] !== undefined) g[a] = S.parametre[a];
    }
    return g;
  }
  function formDogrula() {
    if (!Object.keys(formSemasi()).length) return { ok: true };
    return F.parametreDogrula(S.tur, parametreGovde());
  }
  // YAPBOZ PARÇA SINIRI — üreteç her parçanın kısa kenarını ≥ 24 mm ister (geçmeli kesim sığsın);
  // köprü 12/20/30 parçayı 3×4 / 4×5 / 5×6 ızgaraya çevirir (sütun uzun kenarda). 4:3 fotoğrafla bu
  // ölçüde sığmayan seçenek KAPATILIR ve "bu ölçüde en çok N parça" yazılır (üreteç yine son sözdür).
  var YAPBOZ_IZGARA = { "12": [3, 4], "20": [4, 5], "30": [5, 6] };
  var YAPBOZ_KISA_KENAR_MM = 24;
  function yapbozParcaSiniri(olcu) {
    var enCok = 0;
    for (var p in YAPBOZ_IZGARA) {
      if (!Object.prototype.hasOwnProperty.call(YAPBOZ_IZGARA, p)) continue;
      var g = YAPBOZ_IZGARA[p];
      if (Math.min(olcu / g[1], olcu * 0.75 / g[0]) >= YAPBOZ_KISA_KENAR_MM && Number(p) > enCok) enCok = Number(p);
    }
    return enCok;
  }
  function yapbozParcaNotu() {
    if (!S.alanForm || S.tur !== "yapboz") return;
    var sec = S.alanForm.querySelector("#foto-param-parca");
    if (!sec) return;
    var n = S.olcu ? yapbozParcaSiniri(S.olcu) : 0;
    var enIyi = null;
    for (var i = 0; i < sec.options.length; i++) {
      var op = sec.options[i];
      op.disabled = !!S.olcu && Number(op.value) > n;
      if (!op.disabled) enIyi = op.value;
    }
    if (sec.selectedOptions[0] && sec.selectedOptions[0].disabled && enIyi !== null) {
      sec.value = enIyi; S.parametre.parca = enIyi;
    }
    var not = S.alanForm.querySelector(".foto-uretim-parca-notu");
    if (!not) {
      not = el("p", "foto-uretim-ayrinti foto-uretim-parca-notu");
      sec.parentNode.insertBefore(not, sec.nextSibling);
    }
    not.textContent = S.olcu && n ? "Bu ölçüde en çok " + n + " parça." : "";
    not.hidden = !(S.olcu && n);
  }
  function formHataGoster() {
    yapbozParcaNotu();
    if (!S.alanForm || !S.formHata) return;
    var d = formDogrula();
    S.formHata.textContent = d.ok ? "" : (PARAMETRE_HATA[d.hata] || "Bu alanları kontrol et.");
    S.formHata.hidden = d.ok;
  }
  function doldurS1Form() {
    if (!S.alanForm) return;
    while (S.alanForm.firstChild) S.alanForm.removeChild(S.alanForm.firstChild);
    var form = formSemasi(), alanlar = Object.keys(form);
    S.alanForm.hidden = !alanlar.length;
    if (!alanlar.length) return;
    for (var i = 0; i < alanlar.length; i++) {
      (function (a, sema) {
        var id = "foto-param-" + a;
        var lbl = el("label", "foto-uretim-form-etiket",
          (sema.etiket || a) + (sema.tip === "sayi" && sema.birim ? " (" + sema.birim + ")" : ""));
        lbl.setAttribute("for", id);
        S.alanForm.appendChild(lbl);
        var g;
        if (sema.tip === "secim") {
          g = el("select", "foto-uretim-form-secenek-girdi");
          var ss = sema.secenekler || [];
          for (var j = 0; j < ss.length; j++) {
            var op = el("option", null, String(ss[j]));
            op.value = String(ss[j]);
            g.appendChild(op);
          }
          if (S.parametre[a] === undefined && ss.length) S.parametre[a] = ss[0];
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
        } else if (sema.tip === "metin" && sema.satir_en_cok > 1) {
          // Çok satırlı metin (isimlik): satırlar "\n" ile; satır sınırı F.parametreDogrula'da.
          g = el("textarea", "foto-uretim-form-secenek-girdi");
          g.rows = sema.satir_en_cok;
          if (sema.max > 0) g.maxLength = sema.max;
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
        } else {
          g = el("input", "foto-uretim-form-secenek-girdi");
          if (sema.tip === "sayi") {
            g.type = "number"; g.min = String(sema.min); g.max = String(sema.max);
            g.step = String(sema.adim > 0 ? sema.adim : 1);
            if (S.parametre[a] === undefined) S.parametre[a] = sema.min;
          } else if (sema.tip === "url") {
            g.type = "url"; g.placeholder = "https://";
          } else {
            g.type = "text";
            if (sema.max > 0) g.maxLength = sema.max;
          }
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
        }
        g.id = id; g.name = id;
        var degis = function (e) {
          var v = e.target.value;
          if (sema.tip === "sayi") S.parametre[a] = v === "" ? undefined : Number(v);
          else if (sema.tip === "secim") {
            var ss2 = sema.secenekler || [], bul;
            for (var k = 0; k < ss2.length; k++) { if (String(ss2[k]) === v) { bul = ss2[k]; break; } }
            S.parametre[a] = bul;
          } else S.parametre[a] = v === "" ? undefined : v;
          formHataGoster();
          guncelleS1Buton();
        };
        g.addEventListener("input", degis);
        g.addEventListener("change", degis);
        S.alanForm.appendChild(g);
      })(alanlar[i], form[alanlar[i]] || {});
    }
    S.formHata = el("p", "foto-uretim-ayrinti");
    S.alanForm.appendChild(S.formHata);
    formHataGoster();
  }
  // Seçilen fotoğraftan ANINDA önizleme (tarayıcıda; fotoğraf hiçbir yere gönderilmez).
  function litofanOnizle() {
    if (!S.alanLitofan) return;
    while (S.alanLitofan.firstChild) S.alanLitofan.removeChild(S.alanLitofan.firstChild);
    S.litofanHarita = null;
    S.litofanOnizleme = null;
    if (!litofanSecili()) { guncelleS1Buton(); return; }
    S.alanLitofan.appendChild(el("p", "foto-uretim-ayrinti",
      "Litofan önizlemesi tarayıcında çizilir: fotoğrafın sunucuya ya da hizmet sağlayıcıya gönderilmez; " +
      "siparişte yalnız ondan çıkarılan gri kalınlık haritası alınır."));
    if (!S.dosya) { guncelleS1Buton(); return; }
    var okuyucu = new FileReader();
    okuyucu.onload = function (e) {
      var img = new Image();
      img.onload = function () { litofanCiz(img); };
      img.onerror = function () { litofanUyari("Fotoğraf okunamadı (JPEG, PNG ya da WEBP)."); };
      img.src = e.target.result;
    };
    okuyucu.onerror = function () { litofanUyari("Fotoğraf okunamadı."); };
    okuyucu.readAsDataURL(S.dosya);
  }
  function litofanUyari(metin) {
    S.alanLitofan.appendChild(el("p", "foto-uretim-bildirim foto-uretim-bildirim-hata", metin));
    guncelleS1Buton();
  }
  function litofanCiz(img) {
    var en = img.naturalWidth || img.width, boy = img.naturalHeight || img.height;
    if (!en || !boy) { litofanUyari("Fotoğraf okunamadı."); return; }
    if (Math.max(en, boy) > LITOFAN_ORAN_EN_COK * Math.min(en, boy)) {
      litofanUyari("Bu fotoğraf çok uzun ya da çok dar (en/boy oranı 5:1'den büyük); litofan için başka bir fotoğraf seç.");
      return;
    }
    var o = Math.min(1, LITOFAN_KENAR_PX / Math.max(en, boy));
    var hw = Math.max(1, Math.round(en * o)), hh = Math.max(1, Math.round(boy * o));
    var harita = document.createElement("canvas");
    harita.width = hw; harita.height = hh;
    var hc = harita.getContext("2d");
    hc.drawImage(img, 0, 0, hw, hh);
    var veri = hc.getImageData(0, 0, hw, hh);
    var d = veri.data;
    for (var i = 0; i < d.length; i += 4) {
      var g = Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
      d[i] = g; d[i + 1] = g; d[i + 2] = g; d[i + 3] = 255;
    }
    hc.putImageData(veri, 0, 0);
    S.litofanHarita = harita.toDataURL("image/png");
    // Arkadan ışık: kalınlık 0,6–3,0 mm (koyu = kalın); geçen ışık kalınlıkla üstel azalır.
    var po = Math.min(1, LITOFAN_ONIZLEME_PX / Math.max(hw, hh));
    var pw = Math.max(1, Math.round(hw * po)), ph = Math.max(1, Math.round(hh * po));
    var tuval = document.createElement("canvas");
    tuval.width = pw; tuval.height = ph;
    tuval.className = "foto-uretim-onizleme-img";
    var tc = tuval.getContext("2d");
    tc.drawImage(harita, 0, 0, pw, ph);
    var pv = tc.getImageData(0, 0, pw, ph);
    var pd = pv.data;
    var aralik = LITOFAN_KALINLIK_EN_COK - LITOFAN_KALINLIK_EN_AZ;
    for (var j = 0; j < pd.length; j += 4) {
      var kalinlik = LITOFAN_KALINLIK_EN_AZ + (1 - pd[j] / 255) * aralik;
      var isik = Math.exp(-1.25 * (kalinlik - LITOFAN_KALINLIK_EN_AZ));
      pd[j] = Math.round(255 * isik); pd[j + 1] = Math.round(236 * isik); pd[j + 2] = Math.round(200 * isik); pd[j + 3] = 255;
    }
    tc.putImageData(pv, 0, 0);
    S.litofanOnizleme = tuval.toDataURL("image/png");
    var kap = el("div", "foto-uretim-litofan-onizleme");
    kap.appendChild(el("p", "foto-uretim-form-etiket", "Önizleme"));
    kap.appendChild(tuval);
    kap.appendChild(el("p", "foto-uretim-ayrinti", LITOFAN_DURUSTLUK));
    S.alanLitofan.appendChild(kap);
    guncelleS1Buton();
  }
  // "Siparişe geç": gri haritayı gönder, dönen iş numarasıyla ödeme adımına geç.
  function litofanGonder() {
    if (!S.litofanHarita) { adimKoy("S1", "Önce fotoğrafını seç; önizleme çizilsin.", true); return; }
    if (!S.aydinlatmaOnay) { adimKoy("S1", "Aydınlatma metnini onaylamalısın.", true); return; }
    if (!S.captchaToken1) { adimKoy("S1", "Lütfen doğrulama kutusunu işaretle.", true); return; }
    if (!S.tur || !S.olcu) { adimKoy("S1", "Ölçü seçmelisin.", true); return; }
    var onizleme = S.litofanOnizleme;
    var govde = {
      tur: S.tur,
      olcu_mm: S.olcu,
      gorsel: S.litofanHarita,
      aydinlatma_onay: true,
      onay_surum: F.onay_surum,
      turnstile_token: S.captchaToken1
    };
    if (Object.keys(formSemasi()).length) govde.parametreler = parametreGovde();
    jsonPost(LITOFAN_URL, govde, function (ok, kod, veri) {
      turnsSifirla(S.alanCap1);
      if (kod === 200 && veri && veri.is) {
        S.is = veri.is;
        S.gorsel = onizleme;
        S.gecerlilik = veri.gecerlilik_bitis || null;
        S.adet = 1;
        ssIsKaydet();
        adimKoy("S3");
        return;
      }
      var h = veri && veri.hata;
      var m = h === "onizleme-siniri" ? "Bugünkü önizleme hakkın doldu; yarın yeniden deneyebilirsin."
        : (h === "gorsel-gecersiz" ? "Bu fotoğraftan litofan haritası çıkarılamadı; başka bir fotoğraf dene."
        : (h === "bot-dogrulama" ? "Doğrulama tamamlanamadı; kutuyu yeniden işaretle."
        : (h === "onay-surumu-eski" ? "Onay metni güncellendi; sayfayı yenileyip yeniden dene."
        : "Şu an sipariş başlatılamıyor, biraz sonra yeniden dene.")));
      adimKoy("S1", m, true);
    });
  }

  function cizAna(bolum) {
    while (bolum.firstChild) bolum.removeChild(bolum.firstChild);
    var ic = el("div", "foto-uretim-icerik");

    /* ÜST: 3 adım şeridi (① foto → ② tasarım → ③ üretim ve gönderim) */
    cizSerit(ic);

    /* VİTRİN: sol galeri + büyük önizleme kartı · sağ başlık/fiyat/açıklama/yükleme kutusu */
    var vitrin = el("div", "foto-uretim-vitrin");
    var ornekBlok = el("div", "foto-uretim-galeri-blok");
    S.ornekBlok = ornekBlok;
    vitrin.appendChild(ornekBlok);
    var sag = el("div", "foto-uretim-sag");
    ek(sag, el("h2", "foto-uretim-baslik", "Fotoğrafın, elinde tutacağın bir parça olsun."));
    S.fiyatEl = el("p", "foto-uretim-fiyat", "");
    sag.appendChild(S.fiyatEl);
    S.olcuAltEl = el("p", "foto-uretim-aciklama", "");
    sag.appendChild(S.olcuAltEl);
    cizYukleKutu(sag);
    var guven = el("p", "foto-uretim-guven");
    var tik = el("span", "foto-uretim-guven-tik", "✓");
    tik.setAttribute("aria-hidden", "true");
    ek(guven, tik, "Satın almadan önce 3D olarak görün");
    sag.appendChild(guven);
    vitrin.appendChild(sag);
    ic.appendChild(vitrin);
    ornekCiz(ornekBlok, null);

    /* ADIM ②: mevcut akış (tür + ölçü + renk + malzeme + onay + ödeme) */
    var adim2 = el("div", "foto-uretim-adim2");
    adim2.id = "foto-adim2";
    adim2.appendChild(el("h3", "foto-uretim-adim2-baslik", "② Bir tasarım seçin"));
    var durust = el("div", "foto-uretim-durustluk");
    S.durustP = el("p", null, "");
    durust.appendChild(S.durustP);
    adim2.appendChild(durust);
    durustlukGuncelle();

    /* 4 adim cubugu (akışın iç ilerlemesi) */
    cizAdimlar(adim2);

    /* siparis alani */
    var alan = el("div", "foto-uretim-alani");
    alan.setAttribute("aria-live", "polite");
    S.alan = alan;
    adim2.appendChild(alan);
    ic.appendChild(adim2);

    bolum.appendChild(ic);
  }

  function cizSerit(ic) {
    var serit = el("ol", "foto-uretim-serit");
    serit.setAttribute("aria-label", "Nasıl çalışır");
    var adimlar = [["1", "⇪", "Foto ekle"], ["2", "✦", "Bir tasarım seçin"], ["3", "➜", "Üretim ve gönderim"]];
    for (var i = 0; i < adimlar.length; i++) {
      if (i > 0) {
        var c = el("li", "foto-uretim-serit-cizgi");
        c.setAttribute("aria-hidden", "true");
        serit.appendChild(c);
      }
      var li = el("li", "foto-uretim-serit-adim");
      li.appendChild(el("span", "foto-uretim-serit-no", adimlar[i][0]));
      var ikon = el("span", "foto-uretim-serit-ikon", adimlar[i][1]);
      ikon.setAttribute("aria-hidden", "true");
      li.appendChild(ikon);
      li.appendChild(el("span", "foto-uretim-serit-ad", adimlar[i][2]));
      serit.appendChild(li);
    }
    ic.appendChild(serit);
  }

  /* TEK yükleme alanı ("Foto ekle" kutusu): sayfadaki tek dosya girdisi burada. Tıklama (etiket →
     dosya seçici) ve sürükle-bırak aynı işleyiciye (dosyaKoy) gider. Dosya istemeyen türde ya da
     S1 dışında girdi kapalıdır; tıklama yalnız adım ②'ye kaydırır. */
  function cizYukleKutu(sag) {
    var kutu = el("div", "foto-uretim-yukle-kutu");
    kutu.id = "foto-yukle-kutu";
    var inp = el("input", "foto-uretim-gizli-girdi");
    inp.type = "file";
    inp.id = "foto-dosya";
    inp.addEventListener("change", function (e) {
      var f = e.target.files && e.target.files[0] ? e.target.files[0] : null;
      dosyaKoy(f);
    });
    var etiket = el("label", "foto-uretim-yukle-etiket");
    etiket.setAttribute("for", "foto-dosya");
    var ikon = el("span", "foto-uretim-yukle-ikon", "⇪");
    ikon.setAttribute("aria-hidden", "true");
    ek(etiket, ikon, el("span", null, "Foto ekle"));
    etiket.addEventListener("click", fotoEkleTikla);
    etiket.addEventListener("keydown", function (e) {
      if (inp.disabled && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); fotoEkleTikla(); }
    });
    var secili = el("div", "foto-uretim-yukle-secili");
    secili.hidden = true;
    var hata = el("p", "foto-uretim-yukle-hata");
    hata.setAttribute("role", "alert");
    hata.hidden = true;
    ek(kutu, inp, etiket, secili, hata);
    kutu.addEventListener("dragenter", surukleUstunde);
    kutu.addEventListener("dragover", surukleUstunde);
    kutu.addEventListener("dragleave", function (e) {
      if (e.relatedTarget && typeof kutu.contains === "function" && kutu.contains(e.relatedTarget)) return;
      kutu.classList.remove("surukle");
    });
    kutu.addEventListener("drop", function (e) {
      // Kutuya bırakılan dosya tarayıcıda açılmaz; girdi kapalıysa yok sayılır.
      if (e.preventDefault) e.preventDefault();
      kutu.classList.remove("surukle");
      if (!yuklemeAcik()) return;
      var fl = e.dataTransfer && e.dataTransfer.files;
      dosyaKoy(fl && fl[0] ? fl[0] : null);
    });
    sag.appendChild(kutu);
    var kabul = el("p", "foto-uretim-yukle-kabul", "");
    sag.appendChild(kabul);
    S.yukleKutu = kutu;
    S.yukleGirdi = inp;
    S.yukleEtiket = etiket;
    S.yukleSecili = secili;
    S.yukleHata = hata;
    S.yukleKabul = kabul;
    yukleKutuGuncelle("");
  }
  function surukleUstunde(e) {
    if (e.preventDefault) e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = yuklemeAcik() ? "copy" : "none";
    if (yuklemeAcik() && S.yukleKutu) S.yukleKutu.classList.add("surukle");
  }
  function yuklemeAcik() {
    return S.adim === "S1" && (svgGerekir() || fotoGerekir());
  }

  /* Seçim ve bırakmanın ORTAK yolu: tür + 15 MB denetimi, sonra eski change işleyicisinin yan etkileri. */
  function dosyaKoy(f) {
    var svg = svgGerekir();
    var hata = "";
    if (f) {
      var ad = String(f.name || "").toLowerCase();
      var tip = String(f.type || "").toLowerCase();
      var uygun = svg ? (tip === "image/svg+xml" || (!tip && /\.svg$/.test(ad))) :
        (/^image\/(jpeg|png|webp)$/.test(tip) || (!tip && /\.(jpe?g|png|webp)$/.test(ad)));
      if (!uygun) hata = svg ? "Yalnız SVG dosyası seçebilirsin." : "Yalnız JPEG, PNG ya da WEBP fotoğraf seçebilirsin.";
      else if (f.size > MAKS_DOSYA_BAYT) hata = (svg ? "Dosya" : "Fotoğraf") + " 15 MB'dan büyük olamaz.";
    }
    S.dosya = hata ? null : (f || null);
    if (hata && S.yukleGirdi) S.yukleGirdi.value = "";
    yukleKutuGuncelle(hata);
    konseptSifirla();
    notAlaniGoster();
    if (litofanSecili()) { litofanOnizle(); }
    guncelleS1Buton();
  }

  /* Kutunun hâli: kabul türü + küçük yazı, girdi açık/kapalı, seçili dosyanın önizlemesi ya da hata satırı. */
  function yukleKutuGuncelle(hata) {
    if (!S.yukleKutu) return;
    var svg = svgGerekir();
    var acik = yuklemeAcik();
    var inp = S.yukleGirdi;
    inp.accept = svg ? ".svg,image/svg+xml" : "image/jpeg,image/png,image/webp";
    inp.disabled = !acik;
    if (acik) { S.yukleEtiket.removeAttribute("tabindex"); S.yukleEtiket.removeAttribute("role"); }
    else { S.yukleEtiket.setAttribute("tabindex", "0"); S.yukleEtiket.setAttribute("role", "button"); }
    S.yukleKabul.textContent = svg ? "Yazıları şekle çevrilmiş düz SVG — en çok 15 MB" : "JPEG, PNG veya WEBP — en çok 15 MB";
    S.yukleKabul.hidden = !svg && !fotoGerekir();
    if (S.yukleOnizUrl && kok.URL && typeof kok.URL.revokeObjectURL === "function") {
      try { kok.URL.revokeObjectURL(S.yukleOnizUrl); } catch (e) { }
    }
    S.yukleOnizUrl = null;
    var sec = S.yukleSecili;
    while (sec.firstChild) sec.removeChild(sec.firstChild);
    sec.hidden = !S.dosya;
    S.yukleEtiket.hidden = !!S.dosya;
    if (S.dosya) {
      if (kok.URL && typeof kok.URL.createObjectURL === "function") {
        try { S.yukleOnizUrl = kok.URL.createObjectURL(S.dosya); } catch (e) { S.yukleOnizUrl = null; }
      }
      if (S.yukleOnizUrl) {
        var img = el("img", "foto-uretim-yukle-onizleme");
        img.alt = "";
        img.src = S.yukleOnizUrl;
        sec.appendChild(img);
      }
      sec.appendChild(el("span", "foto-uretim-yukle-ad", S.dosya.name || "Seçilen dosya"));
      if (acik) {
        var deg = el("button", "foto-uretim-yukle-degistir", "Değiştir");
        deg.type = "button";
        deg.addEventListener("click", function () {
          if (S.yukleGirdi && typeof S.yukleGirdi.click === "function") S.yukleGirdi.click();
        });
        sec.appendChild(deg);
      }
    }
    S.yukleHata.textContent = hata || "";
    S.yukleHata.hidden = !hata;
  }

  /* Etiket tıklaması: adım ②'ye iner; girdi açıksa seçiciyi tarayıcı (label for) açar. */
  function fotoEkleTikla() {
    var hedef = document.getElementById("foto-adim2");
    if (hedef && typeof hedef.scrollIntoView === "function") { hedef.scrollIntoView({ behavior: "smooth", block: "start" }); }
  }

  /* Türkçe ayrılma eki: sayının okunuşunun son sözcüğüne göre ('den/'dan/'ten/'tan). */
  function denEki(n) {
    var birler = ["", "den", "den", "ten", "ten", "ten", "dan", "den", "den", "dan"];
    var onlar = ["", "dan", "den", "dan", "tan", "den", "tan", "ten", "den", "dan"];
    if (n === 0) return "dan";
    if (n % 10) return birler[n % 10];
    if (n % 100) return onlar[(n % 100) / 10];
    return "den"; // yüz / bin
  }

  /* Vitrin fiyatı + ölçü cümlesi: seçili türün en küçük ölçüsünün fiyatı (TEK formül F.fiyatKurus; sabit YOK). */
  function vitrinGuncelle(kod) {
    if (!S.fiyatEl || !F) return;
    var t = (kod && F.turBul(kod)) || null;
    if (!t || !t.olcu_mm || !(t.olcu_mm.en_az > 0)) { S.fiyatEl.textContent = ""; return; }
    var kurus = F.fiyatKurus(t.kod, t.olcu_mm.en_az);
    if (!(kurus > 0)) { S.fiyatEl.textContent = ""; return; }
    S.vitrinTur = t.kod;
    var tl = Math.round(kurus / 100);
    S.fiyatEl.textContent = "₺" + tl.toLocaleString("tr-TR") + "'" + denEki(tl) + " itibaren";
    S.fiyatEl.setAttribute("data-tl", String(tl));
    S.fiyatEl.setAttribute("data-tur", t.kod);
    var cm = t.olcu_mm.en_az / 10;
    var cmMetin = (cm % 1 ? cm.toLocaleString("tr-TR") : String(cm));
    S.olcuAltEl.textContent = "Bir fotoğraf yükleyin; seçtiğiniz türde size özel üretelim. " + cmMetin + " cm'" + denEki(cm % 1 ? 0 : cm) +
      " itibaren, sipariş üzerine üretilir; her parça tektir.";
  }

  /* ornekler — kanitina gore (baski: gercek fotograf · render: onizleme + uretim dosyasi).
     Sol galeri: TÜM türlerin ilk geçerli örneği (Okan 7 Eki: "farklı çeşitteki ürünlerden"), seçili çerçeveli,
     + büyük önizleme kartı + tam ekran büyütme (isikAc).
     acikKodlar: /foto/acik turleri — SÜZMEZ; açık türler önce, açık olmayanlar "Yakında" etiketli (sipariş edilemez).
     null = henüz bilinmiyor (etiket yok, veri sırası). */
  function ornekCiz(ornekBlok, acikKodlar) {
    while (ornekBlok.firstChild) ornekBlok.removeChild(ornekBlok.firstChild);
    var aciklar = [], digerleri = [];
    for (var i = 0; i < F.turler.length; i++) {
      var t = F.turler[i];
      if (F.ornekSayisi(t.kod) === 0) continue;
      for (var j = 0; j < F.ornekler.length; j++) {
        var o = F.ornekler[j];
        // Render ornegi turun dürüstlük cümlesi (ornek_notu) olmadan CIZILMEZ (fail-closed).
        if (o && o.tur === t.kod && F.ornekGecerli(o) && (F.ornekKaniti(o) !== "render" || t.ornek_notu)) {
          var yakinda = !!acikKodlar && acikKodlar.indexOf(t.kod) < 0;
          (yakinda ? digerleri : aciklar).push({ tur: t, ornek: o, kanit: F.ornekKaniti(o), yakinda: yakinda });
          break; // tür başına ilk örnek
        }
      }
    }
    var liste = aciklar.concat(digerleri);
    // YER TUTUCU: açık olmayan türler (kayıt YOK → sunucu etkilenmez; galeri TÜM kategorileri gösterir).
    // `yerTutucu:true` küçük resimde ikon kutusu, büyük kartta ikon + "Bu tür yakında eklenecek." yazar;
    // lightbox açılmaz (görsel yok). Sıra: görsel türler → yer tutucular (lightbox gezintisi görsellerde kalır).
    for (var yi = 0; yi < YER_TUTUCU.length; yi++) {
      var yt = YER_TUTUCU[yi];
      liste.push({ tur: { kod: yt.kod, ad: yt.ad }, ornek: null, kanit: "",
        yakinda: true, yerTutucu: true, ikon: yt.ikon });
    }
    S.galeriListe = liste;
    var renderSay = 0;
    for (var r = 0; r < liste.length; r++) { if (liste[r].kanit === "render") renderSay++; }
    // Baslik kanittan: hepsi basilmis urunse "Gerçek örnekler"; render varsa render oldugu yazar.
    var baslik = el("h3", "foto-uretim-blok-baslik",
      !liste.length || renderSay === 0 ? "Gerçek örnekler"
        : (renderSay === liste.length ? "Örnekler (önizleme/render)" : "Örnekler"));
    ornekBlok.appendChild(baslik);
    if (!liste.length) {
      ornekBlok.appendChild(el("p", "foto-uretim-ayrinti", "Henüz gerçek örnek yayınlanmadı."));
      vitrinGuncelle(S.tur || (F.turler[0] && F.turler[0].kod));
      return;
    }
    // Ziyaretçinin seçtiği tür yeniden çizimde (açık liste gelince sıra değişir) korunur.
    S.galeriSecili = 0;
    for (var s = 0; s < liste.length; s++) { if (liste[s].tur.kod === S.galeriSeciliKod) S.galeriSecili = s; }
    var galeri = el("div", "foto-uretim-galeri");
    var kucukler = el("div", "foto-uretim-galeri-kucukler");
    kucukler.setAttribute("role", "list");
    S.galeriKutu = kucukler;
    for (var k = 0; k < liste.length; k++) {
      (function (n) {
        var it = liste[n];
        var d = el("button", "foto-uretim-galeri-kucuk" + (n === S.galeriSecili ? " secili" : ""));
        d.type = "button";
        d.setAttribute("role", "listitem");
        d.setAttribute("aria-label", it.tur.ad + " örneği" + (it.yakinda ? " (yakında)" : ""));
        d.setAttribute("data-tur", it.tur.kod);
        d.setAttribute("aria-pressed", n === S.galeriSecili ? "true" : "false");
        if (it.yerTutucu) {
          // YER TUTUCU: <img> yerine ikon kutusu (görsel değil metin; kaynak/kredi 0).
          var ikSpan = el("span", "foto-uretim-galeri-yer-ikon", it.ikon);
          ikSpan.setAttribute("aria-hidden", "true");
          d.appendChild(ikSpan);
        } else {
          var im = el("img");
          im.src = it.kanit === "render" ? it.ornek.render : it.ornek.baski;
          im.alt = ""; im.width = 64; im.height = 64; im.decoding = "async";
          if (n > 0) im.loading = "lazy";
          d.appendChild(im);
        }
        if (it.yakinda) d.appendChild(el("span", "foto-uretim-yakinda", "Yakında"));
        // Seçili küçük resme ikinci basış tam ekran büyütür (yer tutucuda isikAc engeli no-op; görsel yok).
        d.addEventListener("click", function () {
          if (n === S.galeriSecili) isikAc(n, d); else galeriSec(n);
        });
        kucukler.appendChild(d);
      })(k);
    }
    galeri.appendChild(kucukler);
    S.buyukKart = el("div", "foto-uretim-buyuk");
    galeri.appendChild(S.buyukKart);
    ornekBlok.appendChild(galeri);
    buyukCiz();
  }

  function galeriSec(n) {
    S.galeriSecili = n;
    if (S.galeriListe[n]) S.galeriSeciliKod = S.galeriListe[n].tur.kod;
    var d = S.galeriKutu ? S.galeriKutu.childNodes : [];
    for (var i = 0; i < d.length; i++) {
      if (i === n) { d[i].classList.add("secili"); d[i].setAttribute("aria-pressed", "true"); }
      else { d[i].classList.remove("secili"); d[i].setAttribute("aria-pressed", "false"); }
    }
    var g = S.buyukKart ? S.buyukKart.childNodes : [];
    for (var j = 0; j < g.length; j++) { g[j].hidden = j !== n; }
    var it = S.galeriListe[n];
    // Fiyat/açıklama yalnız AÇIK türde güncellenir ("Yakında" türün fiyatı vitrine yazılmaz).
    if (it && !it.yakinda) vitrinGuncelle(it.tur.kod);
  }

  /* Büyük önizleme kartı: her örneğin grubu çizilir, yalnız seçili olan görünür (galeri sekmesi). */
  function buyukCiz() {
    var kap = S.buyukKart;
    if (!kap) return;
    while (kap.firstChild) kap.removeChild(kap.firstChild);
    var tembel = true;
    function gorsel(src, alt, sinif) {
      var img = el("img", sinif || "foto-uretim-ornek-gorsel");
      img.src = src; img.alt = alt;
      img.width = 600; img.height = 600;
      if (tembel) img.loading = "lazy";
      img.decoding = "async";
      return img;
    }
    function polaroid(src, alt, sol) {
      var pol = el("div", "foto-uretim-polaroid" + (sol ? " sol" : ""));
      pol.appendChild(gorsel(src, alt, "foto-uretim-polaroid-img"));
      return pol;
    }
    for (var k = 0; k < S.galeriListe.length; k++) {
      var it = S.galeriListe[k];
      var grup = el("div", "foto-uretim-ornek-grup");
      grup.setAttribute("data-kanit", it.kanit);
      grup.setAttribute("data-tur", it.tur.kod);
      grup.hidden = k !== S.galeriSecili;
      tembel = k !== S.galeriSecili; // ilk görünen büyük kart hemen yüklenir
      var satir = el("div", "foto-uretim-buyuk-kart");
      if (it.yerTutucu) {
        // YER TUTUCU: büyük kartta ikon + başlık + "Bu tür yakında eklenecek." + Yakında rozeti.
        // Tam ekran büyütme YOK (görsel yok; isikAc zaten yer tutucuya açmaz).
        satir.classList.add("yer-tutucu");
        satir.appendChild(el("span", "foto-uretim-yakinda", "Yakında"));
        var ikBuyuk = el("div", "foto-uretim-yer-ikon-buyuk", it.ikon);
        ikBuyuk.setAttribute("aria-hidden", "true");
        satir.appendChild(ikBuyuk);
        grup.appendChild(satir);
        grup.appendChild(el("div", "foto-uretim-ornek-baslik", it.tur.ad));
        grup.appendChild(el("p", "foto-uretim-ornek-not", "Bu tür yakında eklenecek."));
      } else {
        // Büyük karta basınca tam ekran (klavye: Enter/Boşluk).
        satir.setAttribute("role", "button");
        satir.setAttribute("tabindex", "0");
        satir.setAttribute("aria-haspopup", "dialog");
        satir.setAttribute("aria-label", it.tur.ad + " örneğini büyüt");
        (function (n, hedef) {
          hedef.addEventListener("click", function () { isikAc(n, hedef); });
          hedef.addEventListener("keydown", function (e) {
            if (e && (e.key === "Enter" || e.key === " ")) { if (e.preventDefault) e.preventDefault(); isikAc(n, hedef); }
          });
        })(k, satir);
        if (it.yakinda) satir.appendChild(el("span", "foto-uretim-yakinda", "Yakında"));
        if (it.kanit === "render") {
          // Ozgun fotograf yayinlanmaz: onizleme (koşede polaroid) + uretim dosyasinin render'i (ayni gorselse TEK kez).
          if (it.ornek.onizleme !== it.ornek.render) {
            satir.appendChild(polaroid(it.ornek.onizleme, it.tur.ad + " önizleme"));
          }
          satir.appendChild(gorsel(it.ornek.render, it.tur.ad + " üretim dosyası render"));
          grup.appendChild(satir);
          grup.appendChild(el("div", "foto-uretim-ornek-etiket", "önizleme/render"));
          grup.appendChild(el("p", "foto-uretim-ornek-not", it.tur.ornek_notu));
        } else {
          // Orijinal fotograf koşede polaroid, onizleme sol koşede, basilmis urun buyuk kartta.
          satir.appendChild(polaroid(it.ornek.foto, it.tur.ad + " fotoğraf"));
          satir.appendChild(polaroid(it.ornek.onizleme, it.tur.ad + " önizleme", true));
          satir.appendChild(gorsel(it.ornek.baski, it.tur.ad + " basılmış ürün"));
          grup.appendChild(satir);
          grup.appendChild(el("div", "foto-uretim-ornek-etiket",
            "Fotoğraf → Önizleme → Basılmış ürün (gerçek fotoğraf)"));
        }
        var baslikMetni = it.tur.ad + " · " + it.ornek.olcu_mm + " mm" +
          (it.ornek.not ? " · " + it.ornek.not : "");
        grup.appendChild(el("div", "foto-uretim-ornek-baslik", baslikMetni));
      }
      kap.appendChild(grup);
    }
    var sec = S.galeriListe[S.galeriSecili];
    if (sec && !sec.yakinda) vitrinGuncelle(sec.tur.kod);
  }

  /* Tam ekran büyütme (Okan 7 Eki: "resimlerin üzerine basınca büyüsün"): koyu zemin · × · Esc · ←/→ ·
     mobilde yatay kaydırma · zemine dokununca kapanır. Açıkken gövde kaydırması kilitli; kapanınca odak
     tetikleyen öğeye döner. Saf JS, kitaplık YOK. */
  function isikAc(n, tetikleyen) {
    if (!S.galeriListe.length || !document.body) return;
    // YER TUTUCU: görsel yok; tam ekran büyütme açılmaz (küçük resim/büyük kart tıklaması no-op).
    var acIt = S.galeriListe[n];
    if (!acIt || acIt.yerTutucu) return;
    if (S.isik) isikKapat();
    var kutu = el("div", "foto-uretim-isik");
    kutu.setAttribute("role", "dialog");
    kutu.setAttribute("aria-modal", "true");
    kutu.setAttribute("aria-label", "Örnek görsel");
    kutu.setAttribute("tabindex", "-1");
    var sahne = el("figure", "foto-uretim-isik-sahne");
    var img = el("img", "foto-uretim-isik-img");
    img.width = 1200; img.height = 1200; img.decoding = "async";
    var alt = el("figcaption", "foto-uretim-isik-alt");
    sahne.appendChild(img); sahne.appendChild(alt);
    kutu.appendChild(sahne);
    var dugmeler = [];
    function dugme(sinif, metin, etiket, fn) {
      var b = el("button", sinif, metin);
      b.type = "button"; b.setAttribute("aria-label", etiket);
      b.addEventListener("click", fn);
      kutu.appendChild(b); dugmeler.push(b);
      return b;
    }
    if (S.galeriListe.length > 1) {
      dugme("foto-uretim-isik-ok onceki", "‹", "Önceki örnek", function () { isikGit(-1); });
      dugme("foto-uretim-isik-ok sonraki", "›", "Sonraki örnek", function () { isikGit(1); });
    }
    var kapat = dugme("foto-uretim-isik-kapat", "×", "Kapat", function () { isikKapat(); });
    // Zemine (görselin dışına) dokununca kapanır.
    kutu.addEventListener("click", function (e) { if (e && (e.target === kutu || e.target === sahne)) isikKapat(); });
    kutu.addEventListener("keydown", function (e) {
      if (!e) return;
      if (e.key === "Escape" || e.key === "Esc") { if (e.preventDefault) e.preventDefault(); isikKapat(); }
      else if (e.key === "ArrowLeft") { if (e.preventDefault) e.preventDefault(); isikGit(-1); }
      else if (e.key === "ArrowRight") { if (e.preventDefault) e.preventDefault(); isikGit(1); }
      else if (e.key === "Tab") {
        // Odak diyalogda kalır (düğmeler arasında döner).
        if (e.preventDefault) e.preventDefault();
        var i = dugmeler.indexOf(document.activeElement);
        var y = dugmeler[(i < 0 ? 0 : i + (e.shiftKey ? dugmeler.length - 1 : 1)) % dugmeler.length];
        if (y && y.focus) y.focus();
      }
    });
    // Mobil: yatay kaydırma önceki/sonraki.
    var x0 = null, y0 = null;
    kutu.addEventListener("touchstart", function (e) {
      var t = e && e.touches && e.touches[0];
      x0 = t ? t.clientX : null; y0 = t ? t.clientY : null;
    }, { passive: true });
    kutu.addEventListener("touchend", function (e) {
      var t = e && e.changedTouches && e.changedTouches[0];
      if (!t || x0 == null) return;
      var dx = t.clientX - x0, dy = t.clientY - y0;
      x0 = null;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) isikGit(dx < 0 ? 1 : -1);
    });
    S.isik = { kutu: kutu, img: img, alt: alt, n: 0, tetikleyen: tetikleyen || null,
      tasma: document.body.style ? document.body.style.overflow : "" };
    isikGoster(n);
    if (document.body.style) document.body.style.overflow = "hidden";
    document.body.appendChild(kutu);
    if (kapat.focus) kapat.focus();
  }

  function isikGoster(n) {
    var L = S.galeriListe.length;
    if (!S.isik || !L) return;
    n = ((n % L) + L) % L;
    var it = S.galeriListe[n];
    S.isik.n = n;
    var render = it.kanit === "render";
    S.isik.img.src = render ? it.ornek.render : it.ornek.baski;
    S.isik.img.alt = it.tur.ad + (render ? " örnek render" : " basılmış ürün");
    S.isik.alt.textContent = it.tur.ad + " · " + it.ornek.olcu_mm + " mm" + (it.yakinda ? " · Yakında" : "") +
      " — " + (render ? "önizleme/render" : "gerçek fotoğraf") + " · " + (n + 1) + "/" + L;
  }

  function isikGit(d) {
    if (!S.isik) return;
    // YER TUTUCU atlama: ←/→ görsel türler arasında döner (figür/büst görsel değil).
    var L = S.galeriListe.length, n = S.isik.n, ilerleme = 0;
    do {
      n = ((n + d) % L + L) % L;
      ilerleme++;
    } while (S.galeriListe[n].yerTutucu && ilerleme <= L);
    if (S.galeriListe[n].yerTutucu) return; // tüm liste yer tutucu (defansif; gerçekte olmaz)
    isikGoster(n);
    galeriSec(n); // kapanınca büyük kart aynı örnekte
  }

  function isikKapat() {
    var ik = S.isik;
    if (!ik) return;
    S.isik = null;
    if (ik.kutu.parentNode) ik.kutu.parentNode.removeChild(ik.kutu);
    if (document.body && document.body.style) document.body.style.overflow = ik.tasma || "";
    if (ik.tetikleyen && ik.tetikleyen.focus) ik.tetikleyen.focus();
  }

  function cizAdimlar(ic) {
    var cubuk = el("div", "foto-uretim-adimlar");
    function adim(no, ad) {
      var a = el("div", "foto-uretim-adim", no + ". " + ad);
      a.setAttribute("data-no", String(no));
      cubuk.appendChild(a);
    }
    adim(1, "Fotoğraf yükle");
    cubuk.appendChild(el("span", "foto-uretim-adim-ok", "→"));
    // Tek tür sunuluyorsa tür seçimi YOK: adım yalnız ölçüdür (açık tür listesi gelince yeniden yazılır).
    adim(2, adim2Etiketi(S.acikVeri || F));
    S.adim2El = cubuk.childNodes[cubuk.childNodes.length - 1];
    cubuk.appendChild(el("span", "foto-uretim-adim-ok", "→"));
    adim(3, "Önizleme");
    cubuk.appendChild(el("span", "foto-uretim-adim-ok", "→"));
    adim(4, "Ödeme");
    S.adimCubugu = cubuk;
    ic.appendChild(cubuk);
  }

  /* ============== KAPALI ============== */
  function cizKapali() {
    if (!S.alan) return;
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);
    var kutu = el("div", "foto-uretim-blok");
    var p = el("p");
    p.appendChild(document.createTextNode(
      "Şu an fotoğraftan sipariş alınamıyor. Örnekleri inceleyebilir, sorunu "));
    var a = el("a", "foto-uretim-kapat-a", "WhatsApp'tan yaz");
    a.href = WA; a.target = "_blank"; a.rel = "noopener";
    p.appendChild(a);
    p.appendChild(document.createTextNode("abilirsin."));
    kutu.appendChild(p);
    S.alan.appendChild(kutu);
  }

  // /acik cevabı gelene dek nötr yer tutucu: durum BİLİNMEDEN "alınamıyor" denmez
  // (bölüm görünüme girmeden /acik istenmez; gizli sekmede saatlerce sürebilir).
  function cizYukleniyor() {
    if (!S.alan) return;
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);
    var kutu = el("div", "foto-uretim-blok");
    kutu.appendChild(el("p", null, "Sipariş formu yükleniyor…"));
    S.alan.appendChild(kutu);
  }

  /* ============== S1 ============== */
  function cizS1() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alanTur = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanTur);
    doldurS1Tur();

    S.alanOlcu = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOlcu);
    doldurS1Olcu();

    S.alanForm = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanForm);
    doldurS1Form();

    S.alanDosya = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanDosya);
    doldurS1Dosya();

    S.alanSecim = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanSecim);
    S.alanLitofan = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanLitofan);
    S.alanOnizlemeSonra = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOnizlemeSonra);
    doldurS1Litofan();

    S.alanOnay = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOnay);
    doldurS1Onay();

    S.alanCap1 = el("div", "foto-uretim-captcha");
    S.alan.appendChild(S.alanCap1);
    turnsRender(S.alanCap1, function (t) {
      S.captchaToken1 = t;
      guncelleS1Buton();
    });

    S.alanNotu = el("p", "foto-uretim-ayrinti",
      "Günde en çok " + F.sinir_ziyaretci_24s + " önizleme hakkın var.");
    S.alan.appendChild(S.alanNotu);

    S.alanButon = el("div", "foto-uretim-s1-buton-sira");
    var btn = el("button", "foto-uretim-buton-birincil", "Önizleme oluştur");
    btn.type = "button";
    btn.id = "foto-onizle-buton";
    btn.disabled = true;
    btn.addEventListener("click", onizleOlustur);
    S.alanButon.appendChild(btn);
    S.alan.appendChild(S.alanButon);
    guncelleS1Buton();
  }

  function seciliTurBul() {
    if (!S.acikVeri || !S.acikVeri.turler) return null;
    for (var i = 0; i < S.acikVeri.turler.length; i++) {
      if (S.acikVeri.turler[i].kod === S.tur) return S.acikVeri.turler[i];
    }
    return null;
  }

  /* Üst dürüstlük kutusu seçili türün manifest metnini basar (tür yoksa ilk türünkini). */
  function durustlukGuncelle() {
    if (!S.durustP || !F) return;
    var t = (S.tur && F.turBul(S.tur)) || (F.turler && F.turler[0]) || null;
    S.durustP.textContent = t && t.durustluk ? t.durustluk : "";
    if (S.tur) vitrinGuncelle(S.tur);
  }

  function doldurS1Tur() {
    while (S.alanTur.firstChild) S.alanTur.removeChild(S.alanTur.firstChild);
    // TEK TÜR: seçim adımı çizilmez (radyo düğmesi 0), tür kendiliğinden seçilir.
    if (S.acikVeri.turler.length === 1) {
      S.tur = S.acikVeri.turler[0].kod;
      durustlukGuncelle();
      S.alanTur.hidden = true;
      return;
    }
    S.alanTur.hidden = false;
    S.alanTur.appendChild(el("label", "foto-uretim-form-etiket", "Tür"));
    for (var i = 0; i < S.acikVeri.turler.length; i++) {
      var t = S.acikVeri.turler[i];
      var rid = "foto-tur-" + t.kod;
      var lbl = el("label", "foto-uretim-form-secenek-inline");
      lbl.setAttribute("for", rid);
      var inp = el("input");
      inp.type = "radio"; inp.name = "foto-tur"; inp.value = t.kod; inp.id = rid;
      if (S.tur === t.kod) inp.checked = true;
      (function (kod) {
        inp.addEventListener("change", function (e) {
          if (!e.target.checked) return;
          S.tur = kod;
          durustlukGuncelle();
          var nt = null;
          for (var j = 0; j < S.acikVeri.turler.length; j++) {
            if (S.acikVeri.turler[j].kod === kod) { nt = S.acikVeri.turler[j]; break; }
          }
          S.olcu = nt && nt.olculer && nt.olculer[0] ? nt.olculer[0].mm : null;
          S.parametre = {};
          doldurS1Olcu();
          doldurS1Form();
          doldurS1Dosya();
          doldurS1Onay();
          doldurS1Litofan();
          guncelleS1Buton();
        });
      })(t.kod);
      ek(lbl, inp);
      ek(lbl, " " + t.ad);
      if (t.aciklama) ek(lbl, " — " + t.aciklama);
      S.alanTur.appendChild(lbl);
    }
  }

  function doldurS1Olcu() {
    while (S.alanOlcu.firstChild) S.alanOlcu.removeChild(S.alanOlcu.firstChild);
    var nt = seciliTurBul();
    var tekTur = S.acikVeri.turler.length === 1;
    S.alanOlcu.appendChild(el("label", "foto-uretim-form-etiket",
      tekTur && nt ? nt.ad + " — ölçü (en uzun boyut)" : "Ölçü"));
    if (tekTur && nt && nt.aciklama) {
      S.alanOlcu.appendChild(el("p", "foto-uretim-ayrinti", nt.aciklama));
    }
    if (!nt || !nt.olculer || !nt.olculer.length) {
      S.alanOlcu.appendChild(el("p", "foto-uretim-ayrinti",
        "Bu tür için ölçü seçeneği yok."));
      return;
    }
    // Her türde SÜRGÜ (fiyat listesi YOK, Okan 7 Eki): kayarken "120 mm → 1.200 TL".
    S.alanOlcu.appendChild(olcuSurgusu(nt, "foto-olcu", guncelleS1Buton, null));
  }

  /*
   * ÖLÇÜ SÜRGÜSÜ — ölçü = nesnenin EN UZUN boyutu (en/boy/yükseklik hangisi uzunsa). Fiyat listesi/tablosu
   * ÇİZİLMEZ; sürgü kayarken yalnız seçili ölçünün fiyatı yazılır (F.fiyatSatiri: TEK formül, sunucuyla
   * AYNI fonksiyon). girdi: her kayışta · degisti: bırakınca (ör. S3 yeniden çizimi).
   */
  function olcuSurgusu(nt, id, girdi, degisti) {
    var kap = el("div", "foto-uretim-form-grup");
    var sira = 0;
    for (var x = 0; x < nt.olculer.length; x++) { if (nt.olculer[x].mm === S.olcu) sira = x; }
    S.olcu = nt.olculer[sira].mm;
    var surgu = el("input", "foto-uretim-surgu");
    surgu.type = "range"; surgu.id = id; surgu.name = id;
    surgu.min = "0"; surgu.max = String(nt.olculer.length - 1); surgu.step = "1"; surgu.value = String(sira);
    surgu.setAttribute("aria-label", "Ölçü — en uzun boyut (mm)");
    var yazi = el("p", "foto-uretim-surgu-fiyat", F.fiyatSatiri(nt.kod, S.olcu));
    yazi.setAttribute("aria-live", "polite");
    var sec = function (e) {
      var o2 = nt.olculer[parseInt(e.target.value, 10)] || nt.olculer[0];
      S.olcu = o2.mm;
      yazi.textContent = F.fiyatSatiri(nt.kod, o2.mm);
      return o2;
    };
    surgu.addEventListener("input", function (e) { sec(e); if (girdi) girdi(); });
    surgu.addEventListener("change", function (e) { sec(e); if (degisti) degisti(); });
    kap.appendChild(surgu);
    kap.appendChild(yazi);
    kap.appendChild(el("p", "foto-uretim-ayrinti", "Ölçü, ürünün en uzun boyutudur (en, boy ya da yükseklik)."));
    return kap;
  }

  function doldurS1Dosya() {
    while (S.alanDosya.firstChild) S.alanDosya.removeChild(S.alanDosya.firstChild);
    S.dosya = null;
    konseptSifirla();
    // Dosya girdisi üstteki "Foto ekle" kutusunda (tek alan); tür değişince kutu sıfırlanır.
    if (S.yukleGirdi) S.yukleGirdi.value = "";
    yukleKutuGuncelle("");
    // Yalnız form girdili türde (isimlik, QR) dosya ve not alanı YOK.
    S.alanDosya.hidden = !svgGerekir() && !fotoGerekir();
    if (S.alanDosya.hidden) return;
    cizUretimNotu();
  }

  /* "Nasıl olsun?" — görsel seçildikten sonra ≤300 karakter serbest not (sayaçlı). Bu turda 2D
     üretim YOK: not "üretim notu" olarak önizleme isteğiyle gider, operatör görür. */
  function cizUretimNotu() {
    var kap = el("div", "foto-uretim-form-grup");
    kap.id = "foto-not-alani";
    S.alanUretimNotu = kap;
    var lbl = el("label", "foto-uretim-form-etiket", "Nasıl olsun? (isteğe bağlı)");
    lbl.setAttribute("for", "foto-not");
    kap.appendChild(lbl);
    var ta = el("textarea", "foto-uretim-not");
    ta.id = "foto-not";
    ta.maxLength = URETIM_NOTU_EN_COK;
    ta.rows = 3;
    ta.placeholder = "Örn. şapkalı olsun · çizgi film tarzı · sadece baş";
    ta.value = S.uretimNotu;
    var sayac = el("div", "foto-uretim-not-sayac", "");
    sayac.id = "foto-not-sayac";
    sayac.setAttribute("aria-live", "polite");
    function say() {
      var dizi = Array.from(ta.value);
      if (dizi.length > URETIM_NOTU_EN_COK) { ta.value = dizi.slice(0, URETIM_NOTU_EN_COK).join(""); }
      S.uretimNotu = ta.value;
      sayac.textContent = Array.from(ta.value).length + "/" + URETIM_NOTU_EN_COK;
    }
    ta.addEventListener("input", say);
    say();
    kap.appendChild(ta);
    kap.appendChild(sayac);
    kap.appendChild(el("p", "foto-uretim-ayrinti", "Notunuz üretime iletilir."));
    S.alanKonsept = el("div", "foto-uretim-konsept");
    S.alanKonsept.id = "foto-konsept";
    kap.appendChild(S.alanKonsept);
    S.alanDosya.appendChild(kap);
    notAlaniGoster();
    cizKonsept();
  }

  /* ============== 2D KONSEPT (adım ② içinde, isteğe bağlı) ============== */
  // Konsept yalnız sunucunun /foto/acik `konsept.turler` listesindeki (sağlayıcı kollu) türde ve
  // fotoğraf seçiliyken sunulur. Not boşsa da çalışır (foto -> stil konsepti).
  function konseptAcik() {
    var k = S.acikVeri && S.acikVeri.konsept;
    return !!(k && k.turler && k.turler.indexOf(S.tur) >= 0 && fotoGerekir() &&
      !litofanSecili() && !onizlemeSonraSecili());
  }
  function konseptDurdur() {
    if (S.konseptYoks) { clearInterval(S.konseptYoks); S.konseptYoks = null; }
  }
  function konseptSifirla() {
    konseptDurdur();
    S.konsept = null; S.konseptOturum = null; S.konseptKalan = null; S.konseptGorsel = null;
    S.konseptAsama = ""; S.konseptHata = ""; S.konseptSecili = null;
    if (S.fotoUrl && kok.URL && typeof kok.URL.revokeObjectURL === "function") {
      try { kok.URL.revokeObjectURL(S.fotoUrl); } catch (e) { }
    }
    S.fotoUrl = null;
    cizKonsept();
  }
  function konseptHazirMi() {
    return !!S.dosya && !!S.aydinlatmaOnay && !!S.captchaToken1 && !!S.tur;
  }
  function konseptButonGuncelle() {
    var b = S.konseptGonderBtn || [];
    for (var i = 0; i < b.length; i++) b[i].disabled = !konseptHazirMi();
    if (S.konseptKullanBtn) S.konseptKullanBtn.disabled = !S.captchaToken1;
  }
  function cizKonsept() {
    var kutu = S.alanKonsept;
    if (!kutu) return;
    while (kutu.firstChild) kutu.removeChild(kutu.firstChild);
    S.konseptGonderBtn = [];
    S.konseptKullanBtn = null;
    kutu.hidden = !konseptAcik() || !S.dosya;
    if (kutu.hidden) return;
    var deneme = (S.acikVeri.konsept && S.acikVeri.konsept.deneme) || 3;
    var kalan = typeof S.konseptKalan === "number" ? S.konseptKalan : deneme;
    if (S.konseptAsama === "bekliyor") {
      kutu.appendChild(el("p", "foto-uretim-ayrinti", "Konsept çiziliyor… (genelde 1 dakika)"));
      return;
    }
    if (S.konseptAsama === "hazir" && S.konseptGorsel) {
      var kart = el("div", "foto-uretim-konsept-kart");
      var gs = el("div", "foto-uretim-konsept-gorseller");
      var img = el("img", "foto-uretim-konsept-img");
      img.src = S.konseptGorsel; img.alt = "Konsept"; img.width = 220; img.height = 220;
      img.decoding = "async";
      gs.appendChild(img);
      if (!S.fotoUrl && S.dosya && kok.URL && typeof kok.URL.createObjectURL === "function") {
        try { S.fotoUrl = kok.URL.createObjectURL(S.dosya); } catch (e) { S.fotoUrl = null; }
      }
      if (S.fotoUrl) {
        var fi = el("img", "foto-uretim-konsept-foto");
        fi.src = S.fotoUrl; fi.alt = "Orijinal fotoğraf"; fi.width = 72; fi.height = 72;
        gs.appendChild(fi);
      }
      kart.appendChild(gs);
      kart.appendChild(el("p", "foto-uretim-ayrinti", KONSEPT_METNI));
      var bs = el("div", "foto-uretim-konsept-butonlar");
      var kul = el("button", "foto-uretim-buton-birincil", "Bunu kullan");
      kul.type = "button"; kul.id = "foto-konsept-kullan";
      S.konseptKullanBtn = kul;
      kul.addEventListener("click", konseptKullan);
      bs.appendChild(kul);
      if (kalan > 0) {
        var yen = el("button", "foto-uretim-buton-ikincil", "Notu değiştir, yeniden dene (" + kalan + " hak kaldı)");
        yen.type = "button"; yen.id = "foto-konsept-yeniden";
        S.konseptGonderBtn.push(yen);
        yen.addEventListener("click", konseptOlustur);
        bs.appendChild(yen);
      } else {
        bs.appendChild(el("span", "foto-uretim-ayrinti", "Bu fotoğraf için konsept hakkın doldu."));
      }
      kart.appendChild(bs);
      kutu.appendChild(kart);
      if (S.konseptHata) kutu.appendChild(el("p", "foto-uretim-ayrinti foto-uretim-konsept-hata", S.konseptHata));
      konseptButonGuncelle();
      return;
    }
    kutu.appendChild(el("p", "foto-uretim-ayrinti",
      "İstersen önce notuna göre 2D bir konsept çizelim; beğenirsen 3D önizleme onunla hazırlanır."));
    if (S.konseptHata) kutu.appendChild(el("p", "foto-uretim-ayrinti foto-uretim-konsept-hata", S.konseptHata));
    if (kalan > 0) {
      var btn = el("button", "foto-uretim-buton-ikincil", "Konsept oluştur");
      btn.type = "button"; btn.id = "foto-konsept-buton";
      S.konseptGonderBtn.push(btn);
      btn.addEventListener("click", konseptOlustur);
      kutu.appendChild(btn);
    }
    konseptButonGuncelle();
  }
  function konseptHataKoy(metin) {
    S.konseptAsama = S.konseptGorsel ? "hazir" : "";
    S.konseptHata = metin;
    cizKonsept();
  }
  function konseptOlustur() {
    if (!konseptAcik()) return;
    if (!S.dosya) { konseptHataKoy("Lütfen fotoğrafını seç."); return; }
    if (!S.aydinlatmaOnay) { konseptHataKoy("Önce aşağıdaki aydınlatma metnini onaylamalısın."); return; }
    if (!S.captchaToken1) { konseptHataKoy("Lütfen doğrulama kutusunu işaretle."); return; }
    var jeton = S.captchaToken1;
    S.captchaToken1 = "";
    S.konseptHata = "";
    S.konseptAsama = "bekliyor";
    cizKonsept();
    guncelleS1Buton();
    kucultGorsel(S.dosya, function (err, dataUrl) {
      if (err || !dataUrl) { turnsSifirla(S.alanCap1); konseptHataKoy("Fotoğraf okunamadı (JPEG, PNG ya da WEBP)."); return; }
      var govde = { tur: S.tur, gorsel: dataUrl, aydinlatma_onay: true,
        onay_surum: F.onay_surum, turnstile_token: jeton };
      notGovdeyeKoy(govde);
      if (S.konseptOturum) govde.oturum = S.konseptOturum;
      jsonPost(KONSEPT_URL, govde, function (ok, kod, veri) {
        turnsSifirla(S.alanCap1);
        if (ok && kod === 200 && veri && veri.konsept) {
          S.konsept = veri.konsept;
          S.konseptOturum = veri.oturum || S.konseptOturum;
          S.konseptKalan = typeof veri.kalan === "number" ? veri.kalan : S.konseptKalan;
          S.konseptGorsel = null;
          konseptYoklaBaslat();
          return;
        }
        var h = veri && veri.hata;
        if (kod === 429 && h === "konsept-hakki-bitti") { S.konseptKalan = 0; konseptHataKoy("Bu fotoğraf için konsept hakkın doldu; 3D önizlemeye geçebilirsin."); return; }
        if (kod === 429 && h === "konsept-siniri") { konseptHataKoy("Bugünkü konsept hakkın doldu; doğrudan 3D önizleme oluşturabilirsin."); return; }
        if (kod === 403) { konseptHataKoy("Doğrulama tamamlanamadı, kutucuğu yeniden işaretleyip dene."); return; }
        if (kod === 422) { konseptHataKoy("Bu fotoğraftan konsept çizilemedi; başka bir fotoğraf dene."); return; }
        if (kod === 400 && h && NOT_HATA[h]) { konseptHataKoy(NOT_HATA[h]); return; }
        if (kod === 400 && h === "onay-surumu-eski") { konseptHataKoy("Metin güncellendi, sayfayı yenile."); return; }
        konseptHataKoy("Şu an konsept oluşturulamıyor; doğrudan 3D önizleme oluşturabilirsin.");
      });
    });
  }
  function konseptYoklaBaslat() {
    konseptDurdur();
    S.konseptSayac = 0;
    var no = S.konsept;
    var sor = function () {
      S.konseptSayac++;
      if (S.konseptSayac > KONSEPT_YOKLAMA_TAVAN) { konseptDurdur(); konseptHataKoy("Konsept beklenenden uzun sürdü; yeniden deneyebilir ya da doğrudan 3D önizleme oluşturabilirsin."); return; }
      jsonGetir(KONSEPT_DURUM_URL + "?konsept=" + encodeURIComponent(no), function (ok, kod, veri) {
        if (no !== S.konsept || !veri) return;
        if (veri.asama === "hazir" && veri.gorsel) {
          konseptDurdur();
          S.konseptGorsel = veri.gorsel; S.konseptAsama = "hazir"; S.konseptHata = "";
          cizKonsept();
          return;
        }
        if (veri.asama === "basarisiz" || veri.asama === "suresi-doldu" || kod === 404) {
          konseptDurdur();
          konseptHataKoy(veri.hata === "gorsel-uygun-degil" ? "Bu fotoğraftan konsept çizilemedi; başka bir fotoğraf dene." :
            "Konsept çizilemedi; yeniden deneyebilir ya da doğrudan 3D önizleme oluşturabilirsin.");
        }
      });
    };
    S.konseptYoks = setInterval(sor, KONSEPT_YOKLAMA_MS);
    sor();
  }
  function konseptKullan() {
    if (!S.konsept || S.konseptAsama !== "hazir") return;
    S.konseptSecili = S.konsept;
    onizleOlustur();
  }

  function notAlaniGoster() {
    if (!S.alanUretimNotu) return;
    S.alanUretimNotu.hidden = !S.dosya;
  }

  function notGovdeyeKoy(govde) {
    var n = (S.uretimNotu || "").trim();
    if (S.dosya && n) govde.not = n;
  }

  function doldurS1Onay() {
    while (S.alanOnay.firstChild) S.alanOnay.removeChild(S.alanOnay.firstChild);
    S.alanOnay.appendChild(el("label", "foto-uretim-form-etiket", "Onaylar"));
    // "Nasıl olsun?" notu: 2D açıldığında da geçerli kalan cümle (onay sürümüne bağlı metin DEĞİŞMEZ).
    S.alanOnay.appendChild(el("p", "foto-uretim-ayrinti",
      "Not yazarsanız notunuz görsel üretimine iletilir; nota iletişim bilgisi yazmayın."));

    var det = el("details", "foto-uretim-aydinlatma");
    det.appendChild(el("summary", null, "Aydınlatma metni"));
    // Maddeler türün motoruna göre (manifest `kol` etiketi): D türünde aktarım maddesi GÖRÜNMEZ.
    var maddeler = F.aydinlatmaMaddeleri(S.tur);
    for (var p = 0; p < maddeler.length; p++) {
      det.appendChild(el("p", null, maddeler[p]));
    }
    var sonP = el("p");
    sonP.appendChild(document.createTextNode("Kişisel verilerinle ilgili haklar için "));
    var glnk = el("a", null, "Gizlilik Politikası");
    glnk.href = GIZLILIK_URL;
    sonP.appendChild(glnk);
    sonP.appendChild(document.createTextNode(" sayfasına bakabilirsin."));
    det.appendChild(sonP);
    S.alanOnay.appendChild(det);

    // TEK ONAY KUTUSU (metin sürümü taslak-2): metnin ALTINDA; hak beyanı ve aktarım rızası
    // cümleleri metnin içinde. İşaretlenmeden konsept, önizleme ve sipariş düğmeleri açılmaz.
    var onLbl = el("label", "foto-uretim-form-secenek-inline");
    onLbl.setAttribute("for", "foto-aydinlatma-onay");
    var onInp = el("input");
    onInp.type = "checkbox"; onInp.id = "foto-aydinlatma-onay";
    onInp.checked = !!S.aydinlatmaOnay;
    onInp.addEventListener("change", function (e) {
      S.aydinlatmaOnay = !!e.target.checked;
      guncelleS1Buton();
    });
    ek(onLbl, onInp);
    ek(onLbl, " Aydınlatma metnini okudum, onaylıyorum.");
    S.alanOnay.appendChild(onLbl);
  }

  function guncelleS1Buton() {
    yapbozParcaNotu();
    if (!S.alanButon) return;
    var btn = S.alanButon.querySelector("button");
    if (!btn) return;
    var lit = litofanSecili();
    // Tarayıcı önizleyicisi olmayan D/R türü: önizlemeyi üreteç koşucusu çıkarır (/foto/onizleme
    // kuyruğu); fotoğraf yalnız türün girdisinde varsa istenir.
    var tam = (!!S.dosya || !fotoGerekir()) && !!S.aydinlatmaOnay &&
      !!S.captchaToken1 && !!S.tur && !!S.olcu && (!lit || !!S.litofanHarita) &&
      formDogrula().ok;
    btn.disabled = !tam;
    btn.textContent = lit ? "Siparişe geç" : "Önizleme oluştur";
    konseptButonGuncelle();
  }

  /* ============== S2 ============== */
  function cizS2() {
    if (!S.alan) return;
    konseptDurdur();
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);
    S.alan.appendChild(el("p", null, onizlemeSonraSecili() ?
      "Önizlemen sırada; üretim dosyasıyla birlikte hazırlanıyor…" :
      "Önizlemen hazırlanıyor… (genelde 1 dakika)"));
    if (typeof S.ilerleme === "number") {
      var dis = el("div", "foto-uretim-ilerleme-dis");
      var ic = el("div", "foto-uretim-ilerleme-ic");
      var yuzde = S.ilerleme;
      if (yuzde < 0) yuzde = 0;
      if (yuzde > 100) yuzde = 100;
      ic.style.width = yuzde + "%";
      dis.appendChild(ic);
      S.alan.appendChild(dis);
    }
    var btn = el("button", "foto-uretim-buton-ikincil", "Yeniden kontrol et");
    btn.type = "button";
    btn.addEventListener("click", function () {
      if (!S.is) return;
      S.ilerleme = null;
      yoksBaslat(S.is);
      cizS2();
    });
    S.alan.appendChild(btn);
  }

  /* ============== S3 ============== */
  function cizS3() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alan.appendChild(el("p", "foto-uretim-ayrinti", litofanSecili() ? LITOFAN_DURUSTLUK :
      onizlemeSonraSecili() ? ((litofanKaydi() || {}).durustluk || "") :
      "Önizleme — ürün bunun en çok 4 renkli kabartma yorumu olur; birebir aynısı değildir."));
    if (litofanSecili() && S.secim) {
      var secMetin = [];
      for (var sa in S.secim) {
        if (Object.prototype.hasOwnProperty.call(S.secim, sa)) secMetin.push(S.secim[sa]);
      }
      S.alan.appendChild(el("p", "foto-uretim-ayrinti", "Seçimin: " + secMetin.join(" · ")));
    }

    if (S.gorsel) {
      var img = el("img", "foto-uretim-onizleme-img");
      img.src = S.gorsel; img.alt = "Önizleme";
      img.width = 300; img.height = 300;
      img.loading = "lazy"; img.decoding = "async";
      S.alan.appendChild(img);
    }

    var nt = seciliTurBul();

    /* olcu degistirme — sürgü; bırakınca kayıt + yeniden çizim (toplam güncellenir) */
    if (nt && nt.olculer && nt.olculer.length > 1) {
      var olcuG = el("div", "foto-uretim-form-grup");
      olcuG.appendChild(el("label", "foto-uretim-form-etiket", "Ölçü"));
      olcuG.appendChild(olcuSurgusu(nt, "foto-olcu-s3", null, function () { ssIsKaydet(); cizS3(); }));
      S.alan.appendChild(olcuG);
    }

    /* adet */
    var adetG = el("div", "foto-uretim-form-grup");
    adetG.appendChild(el("label", "foto-uretim-form-etiket", "Adet (1-5)"));
    var adetInp = el("input", "foto-uretim-form-secenek-girdi");
    adetInp.type = "number";
    adetInp.min = String(MIN_ADET);
    adetInp.max = String(MAKS_ADET);
    adetInp.step = "1";
    adetInp.value = String(S.adet);
    adetInp.id = "foto-adet";
    adetInp.addEventListener("change", function (e) {
      var n = parseInt(e.target.value, 10);
      if (!isFinite(n) || n < MIN_ADET || n > MAKS_ADET) {
        e.target.value = String(S.adet); return;
      }
      S.adet = n;
      cizS3();
    });
    adetG.appendChild(adetInp);
    S.alan.appendChild(adetG);

    /* ozet */
    // Birim fiyat TEK formülden (sunucunun ödemede kullandığı AYNI F.fiyatKurus).
    var fiyat = nt ? F.fiyatKurus(nt.kod, S.olcu) : null;
    if (fiyat != null) {
      var urunToplam = fiyat * S.adet;
      var kargo = kargoUcreti(urunToplam);
      var genel = urunToplam + kargo;
      var ozet = el("div", "foto-uretim-ozet");
      ozet.appendChild(el("div", null, "Ürün: " + tlMetni(urunToplam)));
      ozet.appendChild(el("div", null, "Gönderim: " + tlMetni(kargo)));
      ozet.appendChild(el("div", null, "Toplam: " + tlMetni(genel)));
      S.alan.appendChild(ozet);
    }

    if (S.gecerlilik) {
      S.alan.appendChild(el("p", "foto-uretim-ayrinti",
        "Bu önizleme " + yerelSaat(S.gecerlilik) +
        " saatine kadar siparişe dönüşebilir."));
    }

    var butonG = el("div", "foto-uretim-iliskili");
    var sipBtn = el("button", "foto-uretim-buton-birincil", "Sipariş ver");
    sipBtn.type = "button";
    sipBtn.addEventListener("click", function () {
      S.ad = ""; S.tel = ""; S.eposta = ""; S.adres = "";
      S.sehir = ""; S.musteriNotu = ""; S.sozlesme = false;
      S.captchaToken2 = "";
      adimKoy("S4");
    });
    // Aydınlatma onayı olmadan sipariş düğmesi açılmaz (eski sürüm onayıyla geri gelen iş dahil).
    sipBtn.disabled = !S.aydinlatmaOnay;
    butonG.appendChild(sipBtn);
    if (!S.aydinlatmaOnay) {
      butonG.appendChild(el("p", "foto-uretim-ayrinti", "Aydınlatma metni güncellendi; sipariş için yeni önizleme oluştur."));
    }
    var baskaBtn = el("button", "foto-uretim-buton-ikincil", "Başka fotoğraf dene");
    baskaBtn.type = "button";
    baskaBtn.style.marginTop = "0";
    baskaBtn.addEventListener("click", function () {
      yoksDurdur();
      ssIsSil();
      S.dosya = null;
      S.aydinlatmaOnay = false;
      S.gorsel = null;
      S.gecerlilik = null;
      S.adet = 1;
      adimKoy("S1");
    });
    butonG.appendChild(baskaBtn);
    S.alan.appendChild(butonG);
  }

  /* ============== S4 ============== */
  function cizS4() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alanAd = el("div", "foto-uretim-form-grup");
    S.alanAd.appendChild(el("label", "foto-uretim-form-etiket", "Ad soyad"));
    var adInp = el("input", "foto-uretim-form-secenek-girdi");
    adInp.type = "text"; adInp.id = "foto-ad";
    adInp.value = S.ad || "";
    adInp.maxLength = 120;
    adInp.addEventListener("input", function (e) { S.ad = e.target.value; guncelleS4Buton(); });
    S.alanAd.appendChild(adInp);
    S.alan.appendChild(S.alanAd);

    S.alanTel = el("div", "foto-uretim-form-grup");
    S.alanTel.appendChild(el("label", "foto-uretim-form-etiket", "Telefon"));
    var telInp = el("input", "foto-uretim-form-secenek-girdi");
    telInp.type = "tel"; telInp.id = "foto-tel";
    telInp.value = S.tel || "";
    telInp.maxLength = 13;
    telInp.inputMode = "tel";
    telInp.addEventListener("input", function (e) { S.tel = e.target.value; guncelleS4Buton(); });
    S.alanTel.appendChild(telInp);
    S.alan.appendChild(S.alanTel);

    S.alanEposta = el("div", "foto-uretim-form-grup");
    S.alanEposta.appendChild(el("label", "foto-uretim-form-etiket", "E-posta"));
    var epInp = el("input", "foto-uretim-form-secenek-girdi");
    epInp.type = "email"; epInp.id = "foto-eposta";
    epInp.value = S.eposta || "";
    epInp.maxLength = 200;
    epInp.inputMode = "email";
    epInp.addEventListener("input", function (e) { S.eposta = e.target.value; guncelleS4Buton(); });
    S.alanEposta.appendChild(epInp);
    S.alan.appendChild(S.alanEposta);

    S.alanAdres = el("div", "foto-uretim-form-grup");
    S.alanAdres.appendChild(el("label", "foto-uretim-form-etiket", "Açık adres"));
    var adrInp = el("textarea", "foto-uretim-form-secenek-girdi");
    adrInp.id = "foto-adres";
    adrInp.value = S.adres || "";
    adrInp.maxLength = 500;
    adrInp.rows = 3;
    adrInp.addEventListener("input", function (e) { S.adres = e.target.value; guncelleS4Buton(); });
    S.alanAdres.appendChild(adrInp);
    S.alan.appendChild(S.alanAdres);

    S.alanSehir = el("div", "foto-uretim-form-grup");
    S.alanSehir.appendChild(el("label", "foto-uretim-form-etiket", "Şehir"));
    var sehInp = el("input", "foto-uretim-form-secenek-girdi");
    sehInp.type = "text"; sehInp.id = "foto-sehir";
    sehInp.value = S.sehir || "";
    sehInp.maxLength = 60;
    sehInp.addEventListener("input", function (e) { S.sehir = e.target.value; guncelleS4Buton(); });
    S.alanSehir.appendChild(sehInp);
    S.alan.appendChild(S.alanSehir);

    S.alanNotM = el("div", "foto-uretim-form-grup");
    S.alanNotM.appendChild(el("label", "foto-uretim-form-etiket",
      "Not (en çok 500 karakter)"));
    var notInp = el("textarea", "foto-uretim-form-secenek-girdi");
    notInp.id = "foto-not";
    notInp.value = S.musteriNotu || "";
    notInp.maxLength = 500;
    notInp.rows = 3;
    notInp.addEventListener("input", function (e) {
      if (e.target.value.length > 500) e.target.value = e.target.value.slice(0, 500);
      S.musteriNotu = e.target.value;
    });
    S.alanNotM.appendChild(notInp);
    S.alan.appendChild(S.alanNotM);

    var sozG = el("div", "foto-uretim-form-grup");
    var sozLbl = el("label", "foto-uretim-form-secenek-inline");
    sozLbl.setAttribute("for", "foto-sozlesme");
    var sozInp = el("input");
    sozInp.type = "checkbox"; sozInp.id = "foto-sozlesme";
    sozInp.checked = !!S.sozlesme;
    sozInp.addEventListener("change", function (e) {
      S.sozlesme = !!e.target.checked;
      guncelleS4Buton();
    });
    ek(sozLbl, sozInp);
    ek(sozLbl, " ");
    var a1 = el("a", null, "Ön Bilgilendirme Formu");
    a1.href = TESLIMAT_URL; a1.target = "_blank"; a1.rel = "noopener";
    var a2 = el("a", null, "Mesafeli Satış Sözleşmesi");
    a2.href = MESAFELI_URL; a2.target = "_blank"; a2.rel = "noopener";
    ek(sozLbl, a1);
    ek(sozLbl, "'nu ve ");
    ek(sozLbl, a2);
    ek(sozLbl, "'ni okudum, onaylıyorum.");
    sozG.appendChild(sozLbl);
    S.alan.appendChild(sozG);

    S.alanCap2 = el("div", "foto-uretim-captcha");
    S.alan.appendChild(S.alanCap2);
    turnsRender(S.alanCap2, function (t) {
      S.captchaToken2 = t;
      guncelleS4Buton();
    });

    var odeG = el("div", "foto-uretim-s1-buton-sira");
    var btn = el("button", "foto-uretim-buton-birincil", "Kartla öde");
    btn.type = "button";
    btn.id = "foto-kartla-ode";
    btn.disabled = true;
    btn.addEventListener("click", siparisVer);
    odeG.appendChild(btn);
    S.alan.appendChild(odeG);

    S.alan.appendChild(el("p", "foto-uretim-ayrinti",
      "Kart bilgilerin iyzico'nun güvenli sayfasında alınır."));
    guncelleS4Buton();
  }

  function guncelleS4Buton() {
    var btn = document.getElementById("foto-kartla-ode");
    if (!btn) return;
    var ad = S.ad || "";
    var tel = (S.tel || "").replace(rakDisi, "");
    var eposta = S.eposta || "";
    var adres = S.adres || "";
    var sehir = S.sehir || "";
    var tam = ad.length >= 3 && tel.length >= 10 &&
      epostaKalibi.test(eposta) && adres.length >= 10 &&
      sehir.length >= 2 && !!S.sozlesme && !!S.aydinlatmaOnay && !!S.captchaToken2;
    btn.disabled = !tam;
  }

  /* ============== ADIM GECISI ============== */
  function adimKoy(adim, bildirim, hata) {
    S.adim = adim;
    if (bildirim != null) {
      S.bildirim = bildirim;
      S.bildirimHata = !!hata;
    } else {
      S.bildirim = "";
      S.bildirimHata = false;
    }
    var no = 1;
    if (adim === "S1") no = 2;
    else if (adim === "S2" || adim === "S3") no = 3;
    else if (adim === "S4") no = 4;
    adimGoster(no);

    if (adim === "kapali") cizKapali();
    else if (adim === "S1") cizS1();
    else if (adim === "S2") cizS2();
    else if (adim === "S3") cizS3();
    else if (adim === "S4") cizS4();
    yukleKutuGuncelle("");
    durumCubuguGoster();
  }

  /* ============== /acik ============== */
  function acikYukle() {
    jsonGetir(ACIK_URL, function (ok, kod, veri) {
      if (!ok || !veri) { adimKoy("kapali"); return; }
      if (veri.acik !== true || !veri.turler || !veri.turler.length) {
        adimKoy("kapali");
        return;
      }
      S.acikVeri = veri;
      if (S.adim2El) S.adim2El.textContent = "2. " + adim2Etiketi(veri);
      // Açık kod listesi = "Yakında" etiketi + sıra için (galeri TÜM türleri çizer; sipariş tür seçimi açıklarla kalır).
      if (S.ornekBlok) ornekCiz(S.ornekBlok, veri.turler.map(function (x) { return x.kod; }));
      var kayit = ssIsOku();
      if (kayit) {
        S.is = kayit.is;
        S.tur = kayit.tur || S.tur || (veri.turler[0] ? veri.turler[0].kod : null);
        S.olcu = kayit.olcu || null;
        if (kayit.secim && typeof kayit.secim === "object") S.secim = kayit.secim;
        // Onay yalnız AYNI metin sürümüne verildiyse geri gelir (eski sürüm onayı sayılmaz).
        S.aydinlatmaOnay = kayit.onay === F.onay_surum;
        durumSorgula(kayit.is, true);
        return;
      }
      if (!S.tur && veri.turler[0]) S.tur = veri.turler[0].kod;
      if (S.tur) {
        var nt = null;
        for (var i = 0; i < veri.turler.length; i++) {
          if (veri.turler[i].kod === S.tur) { nt = veri.turler[i]; break; }
        }
        if (!S.olcu && nt && nt.olculer && nt.olculer[0]) {
          S.olcu = nt.olculer[0].mm;
        }
      }
      adimKoy("S1");
    });
  }

  /* ============== /durum ============== */
  function durumSorgula(isNo, ilk) {
    jsonGetir(DURUM_URL + "?is=" + encodeURIComponent(isNo),
      function (ok, kod, veri) {
        if (!ok || !veri) {
          if (ilk) { adimKoy("S1"); }
          return;
        }
        var a = veri.asama;
        if (a === "hazir") {
          S.is = isNo;
          S.gorsel = veri.gorsel || S.gorsel;
          if (typeof veri.olcu_mm === "number") S.olcu = veri.olcu_mm;
          if (veri.tur) S.tur = veri.tur;
          S.gecerlilik = veri.gecerlilik_bitis || S.gecerlilik;
          S.adet = 1;
          yoksDurdur();
          ssIsKaydet();
          adimKoy("S3");
          return;
        }
        if (a === "basarisiz") {
          yoksDurdur();
          ssIsSil();
          var m = veri.hata === "uretec-red" && typeof veri.metin === "string" && veri.metin ? veri.metin :
            onizlemeSonraSecili() ? "Önizleme hazırlanamadı, tekrar deneyebilirsin." :
            veri.hata === "gorsel-uygun-degil"
            ? "Bu fotoğraftan önizleme üretilemedi. Konusu net, tek kişi/hayvan/araç olan başka bir fotoğraf dene."
            : "Önizleme üretilemedi; başka bir fotoğrafla dene.";
          adimKoy("S1", m, true);
          return;
        }
        if (a === "suresi-doldu") {
          yoksDurdur();
          ssIsSil();
          adimKoy("S1", "Önizlemenin süresi doldu; yeni önizleme oluştur.", true);
          return;
        }
        if (ilk) {
          ssIsKaydet();
          S.ilerleme = typeof veri.ilerleme === "number" ? veri.ilerleme : null;
          adimKoy("S2");
        } else {
          S.ilerleme = typeof veri.ilerleme === "number" ? veri.ilerleme : null;
          cizS2();
        }
      });
  }
  function yoksBaslat(isNo) {
    yoksDurdur();
    S.yoksSayac = 0;
    // Üreteç önizlemesi: 5 sn aralık, 180 sn tavan; sonra "hazırlanınca gösterilecek" + yeniden dene.
    var uretec = onizlemeSonraSecili();
    var aralik = uretec ? URETEC_YOKLAMA_MS : YOKLAMA_MS;
    var tavan = uretec ? Math.round(URETEC_YOKLAMA_TAVAN_MS / URETEC_YOKLAMA_MS) : YOKLAMA_TAVAN;
    S.yoksIs = setInterval(function () {
      S.yoksSayac++;
      if (S.yoksSayac >= tavan) {
        yoksDurdur();
        S.ilerleme = null;
        cizS2();
        S.bildirim = uretec ? "Önizlemen hazırlanınca burada gösterilecek; biraz sonra yeniden kontrol et." :
          "Önizleme hazırlanması beklenenden uzun sürdü.";
        S.bildirimHata = true;
        durumCubuguGoster();
        return;
      }
      durumSorgula(isNo, false);
    }, aralik);
  }

  /* ============== /onizleme ============== */
  function onizleOlustur() {
    if (litofanSecili()) { litofanGonder(); return; }
    if (onizlemeSonraSecili()) { uretecOnizle(); return; }
    if (!S.dosya) { adimKoy("S1", "Lütfen fotoğrafını seç.", true); return; }
    if (S.dosya.size > MAKS_DOSYA_BAYT) {
      adimKoy("S1", "Fotoğraf 15 MB'dan büyük olamaz.", true);
      return;
    }
    if (!S.aydinlatmaOnay) {
      adimKoy("S1", "Aydınlatma metnini onaylamalısın.", true);
      return;
    }
    if (!S.captchaToken1) {
      adimKoy("S1", "Lütfen doğrulama kutusunu işaretle.", true);
      return;
    }
    if (!S.tur || !S.olcu) {
      adimKoy("S1", "Tür ve ölçü seçmelisin.", true);
      return;
    }
    // Jeton S2'ye geçmeden alınır: adimKoy("S2") doğrulama kutusunu (ve jetonu) temizler.
    var jeton = S.captchaToken1;
    // KONSEPT seçildiyse ("Bunu kullan") 3D önizlemenin girdisi konsepttir: foto ikinci kez gönderilmez.
    var konsept = S.konseptSecili;
    adimKoy("S2", konsept ? "Konseptin 3D önizlemeye gönderiliyor…" : "Fotoğrafın yükleniyor…", false);
    var hazirla = konsept ? function (cb) { cb(null, ""); } : function (cb) { kucultGorsel(S.dosya, cb); };
    hazirla(function (err, dataUrl) {
      if (err || (!konsept && !dataUrl)) {
        turnsSifirla(S.alanCap1);
        adimKoy("S1", "Fotoğraf okunamadı (JPEG, PNG ya da WEBP).", true);
        return;
      }
      var govde = {
        tur: S.tur,
        olcu_mm: S.olcu,
        aydinlatma_onay: true,
        onay_surum: F.onay_surum,
        turnstile_token: jeton
      };
      if (konsept) govde.konsept = konsept; else govde.gorsel = dataUrl;
      notGovdeyeKoy(govde);
      if (Object.keys(formSemasi()).length) govde.parametreler = parametreGovde();
      jsonPost(ONIZLEME_URL, govde, function (ok, kod, veri) {
        turnsSifirla(S.alanCap1);
        if (!ok || !veri) {
          adimKoy("S1", "Şu an önizleme üretilemiyor, biraz sonra yeniden dene.", true);
          return;
        }
        if (kod === 200 && veri.is) {
          S.is = veri.is;
          ssIsKaydet();
          S.ilerleme = null;
          adimKoy("S2");
          yoksBaslat(S.is);
          return;
        }
        if (kod === 429 && veri.hata === "onizleme-siniri") {
          var sinir = typeof veri.sinir === "number" ? veri.sinir : F.sinir_ziyaretci_24s;
          adimKoy("S1",
            "Bugünkü önizleme hakkın doldu (günde " + sinir + "). Yarın yeniden deneyebilirsin.",
            true);
          return;
        }
        if (kod === 403) {
          adimKoy("S1", "Doğrulama tamamlanamadı, kutucuğu yeniden işaretleyip dene.", true);
          return;
        }
        if (kod === 422) {
          adimKoy("S1",
            "Bu fotoğraftan önizleme üretilemedi. Konusu net, tek kişi/hayvan/araç olan başka bir fotoğraf dene.",
            true);
          return;
        }
        if (kod === 400 && veri.hata === "gorsel-gecersiz") {
          adimKoy("S1", "Fotoğraf okunamadı (JPEG, PNG ya da WEBP).", true);
          return;
        }
        if (kod === 400 && NOT_HATA[veri.hata]) { turnsSifirla(S.alanCap1); adimKoy("S1", NOT_HATA[veri.hata], true); return; }
        if (kod === 400 && veri.hata === "onay-surumu-eski") {
          adimKoy("S1", "Metin güncellendi, sayfayı yenile.", true);
          return;
        }
        adimKoy("S1", "Şu an önizleme üretilemiyor, biraz sonra yeniden dene.", true);
      });
    });
  }

  /* Tarayıcı önizleyicisi olmayan D/R türü: önizlemeyi üreteç koşucusu çıkarır (aynı uç, kuyruk). */
  function uretecOnizle() {
    if (fotoGerekir() && !S.dosya) { adimKoy("S1", "Lütfen fotoğrafını seç.", true); return; }
    if (svgGerekir() && !S.dosya) { adimKoy("S1", "Lütfen SVG dosyanı seç.", true); return; }
    if (!S.aydinlatmaOnay) { adimKoy("S1", "Aydınlatma metnini onaylamalısın.", true); return; }
    if (!S.captchaToken1) { adimKoy("S1", "Lütfen doğrulama kutusunu işaretle.", true); return; }
    if (!S.tur || !S.olcu) { adimKoy("S1", "Tür ve ölçü seçmelisin.", true); return; }
    var fd = formDogrula();
    if (!fd.ok) { adimKoy("S1", PARAMETRE_HATA[fd.hata] || "Form alanlarını kontrol et.", true); return; }
    // Jeton S2'ye geçmeden alınır: adimKoy("S2") doğrulama kutusunu (ve jetonu) temizler.
    var jeton = S.captchaToken1;
    var gonder = function (dataUrl, svgMetin) {
      var govde = { tur: S.tur, olcu_mm: S.olcu, aydinlatma_onay: !!S.aydinlatmaOnay, onay_surum: F.onay_surum,
        turnstile_token: jeton };
      if (dataUrl) govde.gorsel = dataUrl;
      if (svgMetin) govde.svg = svgMetin;
      if (Object.keys(formSemasi()).length) govde.parametreler = parametreGovde();
      if (S.secim) govde.secim = S.secim;
      notGovdeyeKoy(govde);
      jsonPost(ONIZLEME_URL, govde, function (ok, kod, veri) {
        turnsSifirla(S.alanCap1);
        if (ok && kod === 200 && veri && veri.is) {
          S.is = veri.is;
          ssIsKaydet();
          S.ilerleme = null;
          adimKoy("S2");
          yoksBaslat(S.is);
          return;
        }
        if (kod === 429 && veri && veri.hata === "onizleme-siniri") {
          adimKoy("S1", "Bugünkü önizleme hakkın doldu. Yarın yeniden deneyebilirsin.", true);
          return;
        }
        if (kod === 403) { adimKoy("S1", "Doğrulama tamamlanamadı, kutucuğu yeniden işaretleyip dene.", true); return; }
        if (kod === 400 && veri && veri.hata === "onay-surumu-eski") { adimKoy("S1", "Metin güncellendi, sayfayı yenile.", true); return; }
        if (kod === 400 && veri && NOT_HATA[veri.hata]) { turnsSifirla(S.alanCap1); adimKoy("S1", NOT_HATA[veri.hata], true); return; }
        adimKoy("S1", "Şu an önizleme hazırlanamıyor, biraz sonra yeniden dene.", true);
      });
    };
    if (svgGerekir()) {
      adimKoy("S2", "Dosyan yükleniyor…", false);
      var okuyucu = new FileReader();
      okuyucu.onload = function () {
        var m = typeof okuyucu.result === "string" ? okuyucu.result : "";
        if (F.svgDogrula(m)) {
          turnsSifirla(S.alanCap1);
          adimKoy("S1", F.uretecRedMetni("uretec-red:svg"), true);
          return;
        }
        gonder("", m);
      };
      okuyucu.onerror = function () { turnsSifirla(S.alanCap1); adimKoy("S1", "Dosya okunamadı.", true); };
      okuyucu.readAsText(S.dosya);
      return;
    }
    if (!fotoGerekir()) { adimKoy("S2", "Önizleme sıraya alınıyor…", false); gonder(""); return; }
    adimKoy("S2", "Fotoğrafın yükleniyor…", false);
    kucultGorsel(S.dosya, function (err, dataUrl) {
      if (err || !dataUrl) {
        turnsSifirla(S.alanCap1);
        adimKoy("S1", "Fotoğraf okunamadı (JPEG, PNG ya da WEBP).", true);
        return;
      }
      gonder(dataUrl);
    });
  }

  /* ============== /baslat ============== */
  function siparisVer() {
    if (!S.is || !S.olcu || S.adet < MIN_ADET || S.adet > MAKS_ADET) {
      adimKoy("S3", "Adet 1-5 arasında olmalı.", true); return;
    }
    if (!S.captchaToken2) {
      adimKoy("S4", "Lütfen doğrulama kutusunu işaretle.", true); return;
    }
    var ad = (S.ad || "").trim();
    var tel = (S.tel || "").replace(rakDisi, "");
    var eposta = (S.eposta || "").trim();
    var adres = (S.adres || "").trim();
    var sehir = (S.sehir || "").trim();
    var notu = (S.musteriNotu || "").trim();
    if (ad.length < 3) { adimKoy("S4", "Adını yaz.", true); return; }
    if (tel.length < 10 || tel.length > 13) { adimKoy("S4", "Telefon numaranı yaz.", true); return; }
    if (!epostaKalibi.test(eposta)) { adimKoy("S4", "E-posta adresini yaz.", true); return; }
    if (adres.length < 10) { adimKoy("S4", "Açık adresini yaz.", true); return; }
    if (sehir.length < 2) { adimKoy("S4", "Şehir yaz.", true); return; }
    if (!S.sozlesme) { adimKoy("S4", "Sözleşmeyi onaylamalısın.", true); return; }
    var atif = (typeof kok.pruvoAtifTopla === "function") ? kok.pruvoAtifTopla() : {};
    var govde = {
      sepet: [F.kolu(S.tur) === "deterministik" && S.secim
        ? { foto_is: S.is, olcu_mm: S.olcu, adet: S.adet, secim: S.secim }
        : { foto_is: S.is, olcu_mm: S.olcu, adet: S.adet }],
      musteri: { ad: ad, tel: tel, eposta: eposta, adres: adres, sehir: sehir },
      musteri_notu: notu,
      sozlesme_onay: true,
      aydinlatma_onay: !!S.aydinlatmaOnay,
      onay_surum: F.onay_surum,
      odeme: "kart",
      turnstile_token: S.captchaToken2,
      atif: atif
    };
    jsonPost(BASLAT_URL, govde, function (ok, kod, veri) {
      turnsSifirla(S.alanCap2);
      if (kod === 200 && veri && veri.url) {
        try { sessionStorage.setItem(SS_SIPARIS, veri.no || ""); } catch (e) { }
        ssIsSil();
        kok.location.href = veri.url;
        return;
      }
      if (kod === 400 && veri && veri.hata === "foto-onizleme-suresi-doldu") {
        ssIsSil();
        adimKoy("S1", "Önizlemenin süresi doldu; yeni önizleme oluştur.", true);
        return;
      }
      if (kod === 400 && veri) {
        var h = veri.hata || "";
        if (h === "musteri-ad") { adimKoy("S4", "Adını yaz.", true); return; }
        if (h === "musteri-tel") { adimKoy("S4", "Telefon numaranı yaz.", true); return; }
        if (h === "musteri-eposta") { adimKoy("S4", "E-posta adresini yaz.", true); return; }
        if (h === "musteri-adres") { adimKoy("S4", "Açık adresini yaz.", true); return; }
        if (h === "musteri-sehir") { adimKoy("S4", "Şehir yaz.", true); return; }
        if (h === "onay-yok" || h === "onay-surumu-eski") {
          adimKoy("S4", "Onay metni güncellendi; sayfayı yenileyip yeniden dene.", true);
          return;
        }
      }
      adimKoy("S4", "Ödeme başlatılamadı; biraz sonra dene ya da WhatsApp'tan yaz.", true);
    });
  }

  /* ============== BASLANGIC ============== */
  function basla() {
    if (!F || !F.turler || !F.turler.length) return;
    var ornekVar = false;
    for (var i = 0; i < F.turler.length; i++) {
      if (F.ornekSayisi(F.turler[i].kod) > 0) { ornekVar = true; break; }
    }
    if (!ornekVar) return;
    if (!SECENEK || typeof SECENEK.kargoKurus !== "function" ||
        typeof SECENEK.kurusMetni !== "function") return;
    var bolum = document.getElementById(ANA_BOLUM_ID);
    if (!bolum) return;
    stilEnjeket();
    cizAna(bolum);
    bolum.removeAttribute("hidden");
    cizYukleniyor();
    adimGoster(1);

    if (typeof IntersectionObserver !== "undefined") {
      var io = new IntersectionObserver(function (entries) {
        for (var j = 0; j < entries.length; j++) {
          if (entries[j].isIntersecting) { acikYukle(); io.disconnect(); break; }
        }
      }, { rootMargin: "200px" });
      io.observe(bolum);
    } else {
      acikYukle();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", basla);
  } else {
    basla();
  }
})();