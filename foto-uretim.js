/*
 * foto-uretim.js — PRUVO ana sayfa "Fotoğrafından özel üretim" bölümü ekranı.
 *
 * - Veri: window.PRUVO_FOTO (foto-uretim-veri.js) — turler, ornekler, onay.
 * - API'ler: GET /api/shop/foto/acik, POST /api/shop/foto/onizleme,
 *   GET /api/shop/foto/durum. Odeme AYRI YOL DEGIL: ③ "Sepete ekle" kalemi sitenin normal sepetine koyar
 *   (window.pruvoSepeteFotoEkle, index.html); odeme + musteri bilgisi normal checkout'ta.
 *   2D KONSEPT: POST /api/shop/foto/konsept, GET /api/shop/foto/konsept-durum.
 * - Bot: Cloudflare Turnstile (sitekey, script URL).
 * - EKRAN (sayfa-3adim K3b, Okan 9 Eki 01:0x/01:4x): #fotoUretim icinde TEK KUTU; kutu basliginda
 *   ①②③④ gostergesi, ayni anda TEK pencere, "Geri"/"İleri" kutu icinde. ① Tür seç (KARTLAR) ·
 *   ② Resim yükle (yukleme + "Nasıl olsun?" + parca kapisi) · ③ Renk, boyut ve malzeme (canli fiyat) ·
 *   ④ Önizleme ve onay (aydinlatma → onizleme → B2 → "Sepete ekle" / "İptal").
 * - Durum makinesi (④ icindeki panel): kapali (bolum kapali) · S1 (onizleme istegi) · S2 (onizleme
 *   bekleniyor) · S3 (onizleme hazir → sepete ekle).
 * - ES5 IIFE; template literal yok, regex literal yok (yayin minifier uyumu);
 *   dis kutuphane yok. DOM yalniz createElement + textContent ile.
 */
(function () {
  "use strict";

  /* ============== SABITLER ============== */
  var ACIK_URL = "/api/shop/foto/acik";
  var ONIZLEME_URL = "/api/shop/foto/onizleme";
  var DURUM_URL = "/api/shop/foto/durum";
  // 2D KONSEPT (Okan 7 Eki 14:5x): foto + "Nasıl olsun?" notu -> konsept; "Bunu kullan" -> 3D önizleme
  // girdisi. İSTEĞE BAĞLI ara adım: doğrudan "Önizleme oluştur" yolu AYNEN durur (konsept düşerse satış durmaz).
  var KONSEPT_URL = "/api/shop/foto/konsept";
  var KONSEPT_DURUM_URL = "/api/shop/foto/konsept-durum";
  var KONSEPT_YOKLAMA_MS = 3000;
  var KONSEPT_YOKLAMA_TAVAN = 60;
  var KONSEPT_METNI = "Konsept, notunuza göre çizilen bir önizlemedir.";
  var TURNS_SITEKEY = "0x4AAAAAAE6AA20ln7MIOR9k";
  var TURNS_KAYNAK = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
  var MAKS_DOSYA_BAYT = 15 * 1024 * 1024;
  var MAKS_KENAR = 1600;
  var YOKLAMA_MS = 3000;
  var YOKLAMA_TAVAN = 80;
  var WA = "https://wa.me/905451386526";
  var GIZLILIK_URL = "/gizlilik/";
  var TESLIMAT_URL = "/teslimat-iade/";
  var MESAFELI_URL = "/mesafeli-satis/";
  var ANA_BOLUM_ID = "fotoUretim";
  var STIL_ID = "fotoUretimStil";
  // ① KARTLAR — TEK tablo (Okan 9 Eki 01:4x: "1- insan 2- hayvan ve model 3-kabartma plaket, 4-büst,
  // 5-anahtarlık, 6- yapboz"). kod = kart · tur = üretim türü (manifest/`/acik` kodu) · alt = istemcide tutulan
  // alt tür (S.altTur; sepet kalemine GİRMEZ) · ad + ret = sayfa metni tablosu (ArTisT c35a848d, BİREBİR).
  // Türü `/acik` listesinde olmayan kart ÇİZİLMEZ ("Yakında" etiketi YOK).
  var KARTLAR = [
    { kod: "insan", tur: "figur", alt: "insan", ad: "İnsan figürü",
      ret: "İnsan figürü için tek kişinin cepheden net fotoğrafı gerekir." },
    { kod: "hayvan_model", tur: "figur", alt: "hayvan_model", ad: "Hayvan ve model figürü",
      ret: "Figür için tek hayvan, araç ya da oyuncağın net fotoğrafı gerekir." },
    { kod: "plaket", tur: "plaket", alt: null, ad: "Kabartma Plaket",
      ret: "Kabartma plaket için yüksek çözünürlüklü, iyi aydınlatılmış fotoğraf gerekir." },
    { kod: "bust", tur: "bust", alt: null, ad: "Büst",
      ret: "Büst için yüzü net görünen bir portre fotoğrafı gerekir." },
    { kod: "anahtarlik", tur: "anahtarlik", alt: null, ad: "Anahtarlık",
      ret: "Anahtarlık için net bir fotoğraf ya da metin/logo gerekir." },
    { kod: "yapboz", tur: "yapboz", alt: null, ad: "Yapboz",
      ret: "Yapboz için açık-koyu tonları belirgin, yüksek çözünürlüklü fotoğraf gerekir." }
  ];
  // İnsan kartı ②'de: ret cümlesinin altında tek satır büste yönlendirme (Büst kartına döner).
  var BUST_YONLENDIRME = "Portre için Büst";
  // PENCERELER — kutu başlığındaki ①②③④ göstergesi + açıklama (sayfa metni, BİREBİR).
  var PENCERELER = [
    { no: "①", ad: "Tür seç", aciklama: "6 seçenekten birini seç: insan figürü, hayvan ve model figürü, kabartma plaket, büst, anahtarlık ya da yapboz." },
    { no: "②", ad: "Resim yükle", aciklama: "Resmi yükle; \"Nasıl olsun?\" kısmında ne istediğini kısaca yaz. Uyumsuz resimde tek kısa mesaj gösterilir." },
    { no: "③", ad: "Renk, boyut ve malzeme", aciklama: "Renk adedi 1–4 (ek renk ₺100), boyut sürgüden ayarlanır; malzemeyi listeden seç. Fiyat ölçüye göre canlı görünür; en uzun boyut mm × 10 TL, en az ₺600." },
    { no: "④", ad: "Önizleme ve onay", aciklama: "Önizlemeyi gör, onayları ver; Sepete ekle açılır." }
  ];
  var SS_IS = "pruvo_foto_is";
  // ORTAK RET CÜMLESİ (sayfa metni "Ortak ret cümlesi (parça / yedek parça)", BİREBİR): parça kapısı
  // `uygun_degil` dediğinde ② içinde gösterilen tek mesaj + ①'e dönüş düğmesi.
  var A_METIN_BIREBIR = "Fotoğraftan parça ya da yedek parça üretmiyoruz.";
  // UYUM KAPISI (BaBa 17:5x + 18:0x — parça/yedek parça foto programından ÇIKTI): 2D önizleme isteği
  // PARA harcıyor; tarayıcıdaki önizleyici görsel sınıflayıcı (ücretli API) bu turda YOK → foto türleri
  // için tek kapalı soru (Evet/Hayır). Girdi türlerinde yalnız anahtar kelime denetimi.
  var UYUM_SORU = "Bu bir yedek ya da mekanik parça mı?";
  // Anahtar kelime KÖKLERİ (küçük harfe + Türkçe ı/İ normalize edilmiş metinde aranır). Liste BaBa
  // hükmünün örneklerini + Türkçe eş biçimleri kapsar: "parçası", "yedeği", "kırıldı", "dişlisi" vb.
  // K2b-fin: TEK satır — mutantın `.split("var UYUM_KOKLER = [").join(...)` ile TEK hamlede
  // boşaltabilmesi için (çok satırlı replace güvenilir değil; bkz. M-KAPI-B kapama testi).
  // K2b-fin2: düz "ayni" kökü çıkarıldı — "aynı" sıradan eşitlik sıfatı olarak tarifte geçer
  // ("annemle aynı gün doğduk") ve yanlış DUR üretiyordu. Parça eşleştirmesi BaBa'nın listesi:
  // "aynısı" / "aynisini" / "aynisindan" / "aynıları" (bunlar "aynı" + iyelik/hal eki; parça listesi).
  var UYUM_KOKLER = ["parca", "parcas", "parcasi", "parcay", "parcayi", "parcam", "parcan", "parcalar", "parcalari", "parcalarin", "parcasin", "parcasini", "yedek", "yedegi", "yedekle", "yedekleri", "yedeklerin", "yedekten", "kirik", "kirigi", "kirdi", "kirildi", "kirilmis", "kirilir", "kiriklar", "kiriklari", "kayip", "kaybi", "kaybol", "kayboldu", "kaybolan", "kayipoldu", "kayipolmus", "mekanizma", "mekanizmasi", "mekanizmayi", "mekanizmalar", "mekanizmalari", "mekanizmada", "mekanizmadan", "disli", "dislisi", "disliyi", "disliler", "dislileri", "dislilerin", "dislide", "disliden", "kilit", "kilidi", "kilide", "kilitler", "kilitleri", "kilitlerin", "kilitten", "klips", "klipsi", "klipsler", "klipsleri", "klipslerin", "klipsten", "yuva", "yuvasi", "yuvayi", "yuvalar", "yuvalari", "yuvalarin", "yuvada", "yuvadan", "orijinal", "orijinali", "orijinale", "orijinalden", "orijinalinde", "aynisi", "aynisini", "aynilar", "aynilari", "aynisindan"];
  // Tek bir regex'e derlenir; Türkçe karakterlere özel kelime sınırı (JS \b Türkçe'de tutarsız).
  var UYUM_HARF = "[a-zçğıöşü0-9]";
  var UYUM_DESEN = new RegExp("(?:^|[^a-zçğıöşü0-9])(?:" + UYUM_KOKLER.join("|") + ")(?:[^a-zçğıöşü0-9]|$)");
  // Görsel sınıflayıcı kancası (null iken (c) kolu çalışır): sağlayıcı/URL/anahtar bu turda YOK.
  var uyumGorselSinif = null;
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
    "parametre-bool": "Kutuyu işaretle ya da boş bırak."
  };
  /* Dürüstlük kutusu metni TÜR BAZLI: manifest `durustluk` (seçili türünki; durustlukGuncelle). */
  /* ============== REFERANSLAR ============== */
  var kok = typeof window !== "undefined" ? window :
    (typeof globalThis !== "undefined" ? globalThis : this);
  var F = kok.PRUVO_FOTO || null;
  var SECENEK = kok.PRUVO_SECENEK || null;

  /* ============== DOGRULAMA KALIPLARI (RegExp literal YOK) ============== */
  var isKalibi = new RegExp("^[a-f0-9]{32}$");

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
    alanOde: null,
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
    galeriListe: [],
    galeriKutu: null,
    kartKod: null,
    altTur: null,
    pencere: 1,
    pencereler: [],
    gosterge: null,
    pencereAciklama: null,
    geriBtn: null,
    ileriBtn: null,
    alanCanliFiyat: null,
    alanKartRet: null,
    secim: null,
    renkler: [],
    b2Onay: false,
    uyumSonuc: null,
    belirsizCevap: null
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

  /* ============== UYUM KAPISI ==============
     Deterministik kol: görsel sınıflayıcı YOK → (c) kolu foto türlerinde tek kapalı soruya düşer.
     Kapalı küme: "uygun" | "uygun_degil" | "belirsiz" (başka değer yok). Kredi harcayan 2D/3D
     önizleme çağrıları bu fonksiyonu ÖNCE çağırır; sonuç "uygun_degil" ise A ekranı + 0 istek. */
  function trNorm(metin) {
    var s = String(metin == null ? "" : metin).toLowerCase();
    s = s.replace(/ı/g, "i").replace(/i̇/g, "i").replace(/i/g, "i");
    s = s.replace(/ş/g, "s").replace(/ğ/g, "g").replace(/ü/g, "u")
         .replace(/ö/g, "o").replace(/ç/g, "c");
    s = s.replace(/[^a-zçğıöşü0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
    return s;
  }
  function uyumKontrol(kod, tarif, cevap) {
    // (b) anahtar kelime denetimi (her türde; foto + girdi).
    if (tarif && typeof tarif === "string" && trNorm(tarif).length) {
      if (UYUM_DESEN.test(trNorm(tarif))) return "uygun_degil";
    }
    // (c) görsel sınıflayıcı kancası boş; foto türlerinde kapalı soru ÇIKAR. Girdi bilgisi MANIFESTTEN (K3c):
    // /acik türleri {kod, ad, aciklama, ornek_sayisi, olculer} — `girdi` taşımaz, oradan okunursa soru hiç çıkmaz.
    var nt = F && typeof F.turBul === "function" && kod ? F.turBul(kod) : null;
    var foto = nt && nt.girdi && nt.girdi.length &&
      (nt.girdi[0] === "foto-1" || nt.girdi[0] === "foto-1-3");
    if (foto) {
      if (cevap === true) return "uygun_degil";   // Evet
      if (cevap === false) return "uygun";        // Hayır
      return "belirsiz";                          // cevapsız → fail-closed: soru ÇIKAR
    }
    return "uygun";                               // girdi türü: soru yok, anahtar kelime yoksa OK
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
    // TEK KUTU (K3b): bölümün tek çocuğu; başlıkta ①②③④ göstergesi, altında TEK görünür pencere + Geri/İleri.
    ".foto-uretim-kutu{max-width:1100px;margin:0 auto;background:#fff;color:var(--navy);border-radius:14px;" +
    "padding:20px;box-sizing:border-box;min-width:0;}" +
    ".foto-uretim-kutu-bas{margin:0 0 16px;}" +
    ".foto-uretim-gosterge{list-style:none;margin:0 0 10px;padding:0;display:grid;" +
    "grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;}" +
    ".foto-uretim-gosterge-adim{display:flex;align-items:center;gap:6px;padding:8px;border-radius:8px;" +
    "background:#eef0f3;color:#5b6573;font-size:13px;font-weight:600;min-width:0;}" +
    ".foto-uretim-gosterge-adim.aktif{background:var(--navy);color:#fff;}" +
    ".foto-uretim-gosterge-no{font-size:18px;line-height:1;flex:0 0 auto;}" +
    ".foto-uretim-gosterge-ad{min-width:0;}" +
    ".foto-uretim-pencere-aciklama{margin:0;font-size:14px;line-height:1.5;color:#5b6573;}" +
    ".foto-uretim-pencere{min-width:0;}" +
    ".foto-uretim-pencere[hidden]{display:none!important;}" +
    // ① KARTLAR: masaüstü 3 sütun, ≤640 px 2 sütun; kart = örnek görsel + ad.
    ".foto-uretim-kartlar{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}" +
    ".foto-uretim-kart{display:flex;flex-direction:column;align-items:stretch;gap:6px;padding:8px;" +
    "border:2px solid transparent;border-radius:12px;background:#eef0f3;cursor:pointer;text-align:left;" +
    "color:inherit;font:inherit;min-width:0;}" +
    ".foto-uretim-kart img{display:block;width:100%;aspect-ratio:1/1;height:auto;object-fit:cover;" +
    "border-radius:8px;background:#fff;}" +
    ".foto-uretim-kart-ad{display:block;font-size:15px;font-weight:700;color:var(--navy);line-height:1.3;}" +
    ".foto-uretim-kart-etiket{display:block;font-size:11px;color:#5b6573;line-height:1.2;}" +
    ".foto-uretim-kart.secili{border-color:var(--navy);background:#fff;}" +
    ".foto-uretim-kart:focus-visible{outline:2px solid var(--navy);outline-offset:2px;}" +
    ".foto-uretim-kartlar>.foto-uretim-blok{grid-column:1/-1;margin:0;}" +
    ".foto-uretim-kart-ret{font-size:14px;font-weight:600;margin:0 0 6px;line-height:1.5;}" +
    ".foto-uretim-yonlendir{font-size:14px;margin:0 0 12px;}" +
    ".foto-uretim-yonlendir button{background:none;border:0;padding:0;color:#d1332e;text-decoration:underline;" +
    "font:inherit;font-weight:700;cursor:pointer;}" +
    ".foto-uretim-gezinti{display:flex;justify-content:space-between;gap:10px;margin:18px 0 0;}" +
    ".foto-uretim-gezinti button{margin-top:0;}" +
    ".foto-uretim-gezinti button[hidden]{display:none;}" +
    ".foto-uretim-canli-fiyat{font-size:20px;font-weight:700;color:#d1332e;margin:8px 0 0;}" +
    ".foto-uretim-durustluk{background:#eef0f3;color:var(--navy);border-radius:8px;" +
    "padding:12px 14px;margin:0 0 14px;font-size:14px;line-height:1.5;}" +
    ".foto-uretim-durustluk p{margin:0;}" +
    ".foto-uretim-durustluk p+p{margin-top:6px;}" +
    ".foto-uretim-blok{background:#fff;color:var(--navy);border-radius:8px;" +
    "padding:16px;margin:0 0 14px;}" +
    ".foto-uretim-ornek-gorsel{display:block;width:100%;max-width:300px;aspect-ratio:1/1;height:auto;" +
    "object-fit:cover;border-radius:6px;background:#eef0f3;}" +
    ".foto-uretim-alani{min-width:0;}" +
    ".foto-uretim-durum{padding:8px 12px;border-radius:6px;background:#eef0f3;" +
    "font-size:14px;margin:0 0 12px;}" +
    ".foto-uretim-durum.hata{background:#fde7e7;color:#a3261e;}" +
    ".foto-uretim-form-grup{margin:0 0 14px;}" +
    ".foto-uretim-form-grup[hidden]{display:none;}" +
    ".foto-uretim-form-etiket{display:block;font-size:14px;font-weight:600;" +
    "margin:0 0 6px;}" +
    ".foto-uretim-form-secenek-girdi{display:block;width:100%;max-width:100%;" +
    "padding:8px 10px;border:1px solid #d4dae3;border-radius:6px;font-size:14px;" +
    "box-sizing:border-box;margin:0 0 6px;}" +
    ".foto-uretim-form-secenek-inline{display:flex;align-items:flex-start;" +
    "gap:8px;padding:8px 10px;border:1px solid #d4dae3;border-radius:6px;" +
    "margin:0 0 6px;cursor:pointer;font-size:14px;}" +
    ".foto-uretim-form-secenek-inline input{flex-shrink:0;margin-top:3px;}" +
    ".foto-uretim-renk-secim{border:0;margin:0;padding:0;min-width:0;display:flex;flex-wrap:wrap;gap:6px;}" +
    ".foto-uretim-renk-secim legend,.foto-uretim-renk-secim>.foto-uretim-form-etiket{width:100%;}" +
    ".foto-uretim-buton-birincil{background:#d1332e;color:#fff;border:none;" +
    "padding:11px 22px;border-radius:6px;font-size:15px;font-weight:600;" +
    "cursor:pointer;max-width:100%;}" +
    ".foto-uretim-buton-birincil[disabled]{background:#b0b8c0;cursor:not-allowed;}" +
    ".foto-uretim-buton-ikincil{background:transparent;color:var(--navy);" +
    "border:1px solid var(--navy);padding:9px 18px;border-radius:6px;" +
    "font-size:14px;cursor:pointer;max-width:100%;margin-top:8px;}" +
    ".foto-uretim-buton-ikincil[disabled]{opacity:.45;cursor:not-allowed;}" +
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
    ".foto-uretim-surgu{display:block;width:100%;max-width:100%;box-sizing:border-box;margin:8px 0 0;accent-color:#12294d;}" +
    ".foto-uretim-surgu-fiyat{font-size:18px;font-weight:700;color:#12294d;margin:6px 0 0;}" +
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
    ".foto-uretim-yukle-kabul{margin:6px 0 12px;font-size:13px;color:#5b6573;}" +
    ".foto-uretim-yukle-ikon{font-size:28px;line-height:1;}" +
    ".foto-uretim-uyum-baslik{font-size:16px;font-weight:700;margin:0 0 6px;}" +
    ".foto-uretim-uyum-butonlar{display:flex;gap:10px;flex-wrap:wrap;}" +
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
    // Mobil: tek sütun akış; kartlar 2 sütun, gösterge 2×2 (375 px yatay taşma 0).
    "@media (max-width:640px){" +
    ".foto-uretim-kutu{padding:14px;}" +
    ".foto-uretim-kartlar{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}" +
    ".foto-uretim-gosterge{grid-template-columns:repeat(2,minmax(0,1fr));}" +
    ".foto-uretim-gosterge-adim{font-size:12px;padding:6px;}" +
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
    if (false && S.secim) kayit.secim = S.secim;
    if (S.renkler && S.renkler.length) kayit.renkler = S.renkler;
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

  /* ============== GÖSTERGE + PENCERE ==============
     Kutu başlığındaki ①②③④ göstergesi aktif pencereyi işaretler; aynı anda TEK pencere görünür
     (diğerleri `hidden`). "İleri" pencerenin şartı tutmadıkça pasif; ①'de "Geri", ④'te "İleri" çizilmez. */
  function pencereGit(n) {
    if (!(n >= 1 && n <= 4)) n = 1;
    if (n > 1 && !S.tur) n = 1;
    S.pencere = n;
    for (var i = 0; i < S.pencereler.length; i++) S.pencereler[i].hidden = (i + 1) !== n;
    if (S.gosterge) {
      var d = S.gosterge.childNodes;
      for (var j = 0; j < d.length; j++) {
        if (parseInt(d[j].getAttribute("data-no"), 10) === n) {
          d[j].classList.add("aktif"); d[j].setAttribute("aria-current", "step");
        } else {
          d[j].classList.remove("aktif"); d[j].removeAttribute("aria-current");
        }
      }
    }
    if (S.pencereAciklama) S.pencereAciklama.textContent = PENCERELER[n - 1].aciklama;
    if (n === 4 && S.adim === "S3") cizS3();
    gezintiGuncelle();
  }
  // İleri şartı: ① tür seçili · ② dosya (gerekiyorsa) + parça kapısı "uygun" · ③ ölçü + form geçerli.
  function ileriAcikMi() {
    if (S.pencere === 1) return !!S.tur;
    if (S.pencere === 2) {
      return !!S.tur && (!!S.dosya || !fotoGerekir()) &&
        uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap) === "uygun";
    }
    if (S.pencere === 3) return !!S.tur && !!S.olcu && formDogrula().ok;
    return false;
  }
  function gezintiGuncelle() {
    if (S.geriBtn) S.geriBtn.hidden = S.pencere === 1;
    if (S.ileriBtn) {
      S.ileriBtn.hidden = S.pencere === 4;
      S.ileriBtn.disabled = !ileriAcikMi();
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
  // Adım 2 etiketi (geriye uyumluluk): kullanılmıyor; pencere adları PENCERELER tablosundan.
  function adim2Etiketi(F) { return F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"; }

  /* ============== LITOFAN (deterministik kol) ============== */
  // Deterministik kol + tarayıcı önizleyicisi kayıtlı üreteç (bugün litofan).
    // Deterministik kol, tarayıcı önizleyicisi YOK: örnek render + ONIZLEME_SONRA; önizlemeyi koşucu üretir.
    function litofanKaydi() { return F && typeof F.turBul === "function" ? F.turBul(S.tur) : null; }
  // Türün girdisinde fotoğraf var mı (kayıt yoksa var say).
  function fotoGerekir() {
    var t = litofanKaydi();
    return !t || !t.girdi || t.girdi.indexOf("foto-1") >= 0 || t.girdi.indexOf("foto-1-3") >= 0;
  }
  // Kayıttan varsayılan seçim: her malzeme bölgesinin ilk malzemesi, her renk bölgesinin ilk rengi.
    // EK RENK (Okan 8 Eki: "ilk renk ücretsiz, her + renk için +100 TL", en çok 4): palet türünde (plaket/figür/büst)
  // müşterinin seçtiği renkler; bölge türünde bölgelerde seçilen FARKLI renkler; bölgesiz türde 1. Sunucu AYNI sayımı yapar.
  function paletRenkleri(kod) {
    var tavan = F.renkTavani(kod) || 1;
    var r = (S.renkler || []).filter(function (x, i, d) { return F.PLA_RENKLERI.indexOf(x) >= 0 && d.indexOf(x) === i; });
    if (!r.length) r = [F.PLA_RENKLERI[0]];
    return r.slice(0, tavan);
  }
  function renkSayisi(nt) {
    if (!nt) return 1;
    if (F.renkPaleti(nt.kod)) return paletRenkleri(nt.kod).length;
    var fark = [], sec = aktifRenkSecimi();
    for (var a in sec) {
      if (Object.prototype.hasOwnProperty.call(sec, a) && /_renk$/.test(a) && fark.indexOf(sec[a]) < 0) fark.push(sec[a]);
    }
    return Math.max(1, fark.length);
  }
  // Ödeme kalemi: deterministik türde bölge seçimi (yalnız AKTİF bölgelerin rengi), palet türünde renkler
  // (sunucu ikisini de kayda karşı doğrular).
  function sepetKalemi() {
    var k = { foto_is: S.is, olcu_mm: S.olcu, adet: S.adet };
    if (F.kolu(S.tur) === "deterministik" && S.secim) k.secim = aktifRenkSecimi();
    if (F.renkPaleti(S.tur)) k.renkler = paletRenkleri(S.tur);
    return k;
  }
  // Palet seçici: 9 PLA rengi, en az 1, en çok tavan (dolunca kalanlar kapalı); değişince özet yeniden çizilir.
  function paletSecici(nt, degisti) {
    var tavan = F.renkTavani(nt.kod) || 1;
    S.renkler = paletRenkleri(nt.kod);
    var g = el("div", "foto-uretim-form-grup");
    var fs_ = el("fieldset", "foto-uretim-renk-secim");
    fs_.appendChild(el("legend", "foto-uretim-form-etiket", "Renkler (1–" + tavan + "; ilk renk dahil, her ek renk +" +
      F.tlMetni(F.ekRenkKurus(nt.kod) || 0) + ")"));
    for (var i = 0; i < F.PLA_RENKLERI.length; i++) {
      (function (renk) {
        var lbl = el("label", "foto-uretim-form-secenek-inline");
        var inp = el("input");
        inp.type = "checkbox"; inp.name = "foto-renk"; inp.value = renk;
        var secili = S.renkler.indexOf(renk) >= 0;
        inp.checked = secili;
        // Tavan doluysa seçilmemiş kutular kapalı; tek seçili kutu kaldırılamaz (en az 1 renk).
        inp.disabled = (!secili && S.renkler.length >= tavan) || (secili && S.renkler.length === 1);
        inp.addEventListener("change", function (e) {
          var d = S.renkler.slice();
          if (e.target.checked) { if (d.indexOf(renk) < 0 && d.length < tavan) d.push(renk); }
          else if (d.length > 1) { d = d.filter(function (x) { return x !== renk; }); }
          S.renkler = d;
          degisti();
        });
        ek(lbl, inp, " " + renk);
        fs_.appendChild(lbl);
      })(F.PLA_RENKLERI[i]);
    }
    g.appendChild(fs_);
    return g;
  }
  function radyoGrubu(kutu, etiket, ad, liste, secili, cb) {
    var g = el("div", "foto-uretim-renk-secim");
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
    // D/R türünde sipariş öncesi önizleme yoksa: türün örnek render'ı + ONIZLEME_SONRA.
  function doldurS1OnizlemeSonra() {
    if (!S.alanOnizlemeSonra) return;
    while (S.alanOnizlemeSonra.firstChild) S.alanOnizlemeSonra.removeChild(S.alanOnizlemeSonra.firstChild);
    var acik = !!(F && F.kolu && F.kolu(S.tur) === "deterministik");
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
  // KOŞULLU ALAN (`kosul`): form sırasıyla, yalnız AKTİF alanların değerleri üzerinden (F.alanAktif —
  // sunucuyla aynı); koşulu sağlanmayan alan gövdeye GİRMEZ ve formda gizlenir.
  function aktifParametreler() {
    var form = formSemasi(), g = {}, aktif = {};
    for (var a in form) {
      if (!Object.prototype.hasOwnProperty.call(form, a)) continue;
      aktif[a] = F.alanAktif(form, a, g);
      if (aktif[a] && S.parametre[a] !== undefined) g[a] = S.parametre[a];
    }
    return { govde: g, aktif: aktif };
  }
  function parametreGovde() {
    return aktifParametreler().govde;
  }
  function kosulGuncelle() {
    renkKosulGuncelle();
    if (!S.alanForm) return;
    var aktif = aktifParametreler().aktif, d = S.alanForm.childNodes;
    for (var i = 0; i < d.length; i++) {
      var a = d[i].nodeType === 1 ? d[i].getAttribute("data-param") : null;
      if (a) d[i].hidden = aktif[a] === false;
    }
  }
  // KOŞULLU RENK BÖLGESİ (BaBa 8 Eki 15:5x): bölge üretilmiyorsa (logo tabanı "Yok", rölyef tek renk, ses başlığı /
  // braille üst yazısı boş) seçicisi GİZLİ ve rengi renk sayısına girmez — müşteri seçemediği renge ödemez.
  // Sunucu AYNI fonksiyonla (F.renkBolgesiAktif) önizleme parametrelerinden sayar.
  function renkKosulGuncelle() {
    if (!S.alanSecim) return;
    var p = aktifParametreler().govde, d = S.alanSecim.childNodes;
    for (var i = 0; i < d.length; i++) {
      var b = d[i].nodeType === 1 ? d[i].getAttribute("data-renk-bolge") : null;
      if (b) d[i].hidden = !F.renkBolgesiAktif(S.tur, b, p);
    }
  }
  function aktifRenkSecimi() {
    var p = aktifParametreler().govde, c = {};
    for (var a in (S.secim || {})) {
      if (!Object.prototype.hasOwnProperty.call(S.secim, a)) continue;
      if (!/_renk$/.test(a) || F.renkBolgesiAktif(S.tur, a.replace(/_renk$/, ""), p)) c[a] = S.secim[a];
    }
    return c;
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
    kosulGuncelle();
    if (!S.alanForm || !S.formHata) return;
    var d = formDogrula();
    S.formHata.textContent = d.ok ? "" : (PARAMETRE_HATA[d.hata] || "Bu alanları kontrol et.");
    S.formHata.hidden = d.ok;
  }
  // K3a: form tipleri yalnız secim/sayi/bool (yapboz: parca secim; bust: uzun_kenar_mm/rol_yuksekligi_mm sayi,
        //   ters/iki_renk bool). metin/url/ses/konum/tarih/svg kaldırıldı.
        function doldurS1Form() {
    if (!S.alanForm) return;
    while (S.alanForm.firstChild) S.alanForm.removeChild(S.alanForm.firstChild);
    var form = formSemasi(), alanlar = Object.keys(form);
    S.alanForm.hidden = !alanlar.length;
    if (!alanlar.length) return;
    for (var i = 0; i < alanlar.length; i++) {
      var ilkDugum = S.alanForm.childNodes.length;
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
        } else if (sema.tip === "bool") {
          // Onay kutusu: değer YALNIZ true/false (F.parametreDogrula); varsayılan manifestten.
          g = el("input", "foto-uretim-form-onay-kutusu");
          g.type = "checkbox"; g.id = id; g.name = id;
          if (S.parametre[a] !== true && S.parametre[a] !== false) S.parametre[a] = sema.varsayilan === true;
          g.checked = S.parametre[a] === true;
          g.addEventListener("change", function (e) {
            S.parametre[a] = e.target.checked === true;
            formHataGoster();
            guncelleS1Buton();
          });
          S.alanForm.appendChild(g);
          return;
        } else if (sema.tip === "sayi") {
          g = el("input", "foto-uretim-form-secenek-girdi");
          g.type = "number"; g.min = String(sema.min); g.max = String(sema.max);
          g.step = String(sema.adim > 0 ? sema.adim : 1);
          if (S.parametre[a] === undefined) S.parametre[a] = sema.min;
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
      // Alanın tüm düğümleri (etiket + girdi) `data-param` taşır: kosulGuncelle onları birlikte gizler.
      for (var dn = ilkDugum; dn < S.alanForm.childNodes.length; dn++) {
        if (S.alanForm.childNodes[dn].nodeType === 1) S.alanForm.childNodes[dn].setAttribute("data-param", alanlar[i]);
      }
    }
    S.formHata = el("p", "foto-uretim-ayrinti");
    S.alanForm.appendChild(S.formHata);
    formHataGoster();
  }

  function cizAna(bolum) {
    while (bolum.firstChild) bolum.removeChild(bolum.firstChild);
    // TEK KUTU: #fotoUretim'in TEK çocuğu; kutunun dışında öğe YOK (Okan 01:0x: "assağısı yukarısı sağı solu yok").
    var kutu = el("div", "foto-uretim-kutu");
    kutu.id = "foto-kutu";
    var bas = el("div", "foto-uretim-kutu-bas");
    cizGosterge(bas);
    S.pencereAciklama = el("p", "foto-uretim-pencere-aciklama", "");
    S.pencereAciklama.setAttribute("aria-live", "polite");
    bas.appendChild(S.pencereAciklama);
    kutu.appendChild(bas);
    S.pencereler = [];
    for (var i = 1; i <= 4; i++) {
      var p = el("div", "foto-uretim-pencere");
      p.id = "foto-pencere-" + i;
      p.setAttribute("data-pencere", String(i));
      p.setAttribute("role", "group");
      p.setAttribute("aria-label", PENCERELER[i - 1].ad);
      S.pencereler.push(p);
      kutu.appendChild(p);
    }
    /* ① TÜR SEÇ: yalnız kartlar (yükleme alanı 0, başka öğe 0). */
    S.ornekBlok = el("div", "foto-uretim-kartlar");
    S.ornekBlok.id = "foto-kartlar";
    S.ornekBlok.setAttribute("role", "list");
    S.pencereler[0].appendChild(S.ornekBlok);
    /* ④ ÖNİZLEME VE ONAY: durum makinesinin paneli (S1 önizleme isteği · S2 bekliyor · S3 sepet). */
    var alan = el("div", "foto-uretim-alani");
    alan.setAttribute("aria-live", "polite");
    S.alan = alan;
    S.pencereler[3].appendChild(alan);
    /* Geri / İleri — kutu içinde, altta. */
    var gez = el("div", "foto-uretim-gezinti");
    var geri = el("button", "foto-uretim-buton-ikincil", "Geri");
    geri.type = "button"; geri.id = "foto-geri";
    geri.addEventListener("click", function () { pencereGit(S.pencere - 1); });
    var ileri = el("button", "foto-uretim-buton-birincil", "İleri");
    ileri.type = "button"; ileri.id = "foto-ileri";
    ileri.addEventListener("click", function () { if (ileriAcikMi()) pencereGit(S.pencere + 1); });
    ek(gez, geri, ileri);
    S.geriBtn = geri; S.ileriBtn = ileri;
    kutu.appendChild(gez);
    bolum.appendChild(kutu);
    pencereGit(1);
  }

  function cizGosterge(bas) {
    var g = el("ol", "foto-uretim-gosterge");
    g.setAttribute("aria-label", "Adımlar");
    for (var i = 0; i < PENCERELER.length; i++) {
      var li = el("li", "foto-uretim-gosterge-adim");
      li.setAttribute("data-no", String(i + 1));
      var no = el("span", "foto-uretim-gosterge-no", PENCERELER[i].no);
      no.setAttribute("aria-hidden", "true");
      ek(li, no, el("span", "foto-uretim-gosterge-ad", PENCERELER[i].ad));
      g.appendChild(li);
    }
    S.gosterge = g;
    bas.appendChild(g);
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
    return !!S.tur && S.adim !== "S2" && fotoGerekir();
  }

  /* Seçim ve bırakmanın ORTAK yolu: tür + 15 MB denetimi, sonra eski change işleyicisinin yan etkileri. */
  function dosyaKoy(f) {
    var svg = false;
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
    if (S.adim === "S3") onizlemeSifirla();
    yukleKutuGuncelle(hata);
    konseptSifirla();
    notAlaniGoster();
    
    guncelleS1Buton();
  }

  /* Kutunun hâli: kabul türü + küçük yazı, girdi açık/kapalı, seçili dosyanın önizlemesi ya da hata satırı. */
  function yukleKutuGuncelle(hata) {
    if (!S.yukleKutu) return;
    var svg = false;
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
    var hedef = document.getElementById("foto-pencere-2");
    if (hedef && typeof hedef.scrollIntoView === "function") { hedef.scrollIntoView({ behavior: "smooth", block: "start" }); }
  }

  /* ① KARTLAR — `KARTLAR` tablosundan; türü `/acik` listesinde olmayan ya da sayılan örneği olmayan kart
     ÇİZİLMEZ. Kart = türün sayılan örneğinin görseli + ad (+ kanıt etiketi: render "önizleme/render",
     baskı "basılmış ürün" — hukuk kapısı 13:4x). Render örneği türün dürüstlük cümlesi (ornek_notu)
     olmadan çizilmez (fail-closed). acikKodlar: /foto/acik türleri; null = henüz bilinmiyor (kart 0). */
  function kartOrnegi(t) {
    if (!t || F.ornekSayisi(t.kod) === 0) return null;
    for (var j = 0; j < F.ornekler.length; j++) {
      var o = F.ornekler[j];
      if (o && o.tur === t.kod && F.ornekGecerli(o) && (F.ornekKaniti(o) !== "render" || t.ornek_notu)) return o;
    }
    return null;
  }
  function ornekCiz(ornekBlok, acikKodlar) {
    while (ornekBlok.firstChild) ornekBlok.removeChild(ornekBlok.firstChild);
    var liste = [];
    for (var i = 0; i < KARTLAR.length; i++) {
      var k = KARTLAR[i];
      if (!acikKodlar || acikKodlar.indexOf(k.tur) < 0) continue;
      var t = F.turBul(k.tur), o = kartOrnegi(t);
      if (!o) continue;
      liste.push({ kart: k, tur: t, ornek: o, kanit: F.ornekKaniti(o) });
    }
    S.galeriListe = liste;
    S.galeriKutu = ornekBlok;
    for (var n = 0; n < liste.length; n++) {
      (function (it, sira) {
        var d = el("button", "foto-uretim-kart");
        d.type = "button";
        d.setAttribute("role", "listitem");
        d.setAttribute("data-kart", it.kart.kod);
        d.setAttribute("data-tur", it.tur.kod);
        d.setAttribute("aria-pressed", "false");
        var im = el("img");
        im.src = it.kanit === "render" ? it.ornek.render : it.ornek.baski;
        im.alt = ""; im.width = 240; im.height = 240; im.decoding = "async";
        if (sira > 0) im.loading = "lazy";
        d.appendChild(im);
        d.appendChild(el("span", "foto-uretim-kart-ad", it.kart.ad));
        d.appendChild(el("span", "foto-uretim-kart-etiket", it.kanit === "render" ? "önizleme/render" : "basılmış ürün"));
        d.addEventListener("click", function () { galeriSec(it.kart.kod); });
        ornekBlok.appendChild(d);
      })(liste[n], n);
    }
    // Yenilemede seçim korunur (URL #tur + sessionStorage); listede olmayan kart seçili kalmaz.
    turSecimiYukle();
    if (S.kartKod && !kartListede(S.kartKod)) { S.kartKod = null; S.altTur = null; }
    kartVurgula();
  }
  function kartListede(kod) {
    for (var i = 0; i < S.galeriListe.length; i++) { if (S.galeriListe[i].kart.kod === kod) return S.galeriListe[i]; }
    return null;
  }
  function kartVurgula() {
    var d = S.galeriKutu ? S.galeriKutu.childNodes : [];
    for (var i = 0; i < d.length; i++) {
      var secili = d[i].getAttribute("data-kart") === S.kartKod;
      if (secili) d[i].classList.add("secili"); else d[i].classList.remove("secili");
      d[i].setAttribute("aria-pressed", secili ? "true" : "false");
    }
  }

  /* Kart tıkı = SEÇ + ② penceresine geç. İki figür kartı aynı üretim türünü (figur) seçer; alt tür
     (S.altTur) yalnız istemcide tutulur. Tür değişince ②/③ formu türün kaydından yeniden doldurulur. */
  function galeriSec(kod) {
    var it = kartListede(kod);
    if (!it) return;
    S.kartKod = it.kart.kod;
    S.altTur = it.kart.alt;
    kartVurgula();
    var eski = S.tur;
    S.tur = it.tur.kod;
    if (eski !== S.tur) {
      // Önizleme/sepet paneli eski türe aitse sıfırlanır (eski önizleme yeni türün sepetine giremez).
      if (S.adim === "S2" || S.adim === "S3") onizlemeSifirla();
      var nt = seciliTurBul();
      S.olcu = nt && nt.olculer && nt.olculer[0] ? nt.olculer[0].mm : null;
      S.parametre = {};
      S.renkler = [];
      S.secim = varsayilanSecim(S.tur);
      // K3a: ②/③ formu (cizForm) henüz çizilmediyse S.alanOlcu/S.alanForm/... null olur; doldur* çağrısı
      // istisna fırlatır, dürüstlukGuncelle yarıda kalır. Koruma: form çizilmemişse doldur* atlanır;
      // cizForm aşağıda formu kurar.
      if (S.alanOlcu) {
        doldurS1Olcu();
        doldurS1Secim();
        doldurS1Form();
        doldurS1Dosya();
        cizUyum();
      }
    }
    if (!S.alanOlcu) cizForm();
    durustlukGuncelle();
    kartRetGuncelle(it);
    turSecimiKaydet(it.kart.kod);
    if (S.adim === "S1") cizS1();
    pencereGit(2);
  }

  /* ② başı: kartın foto şartı (sayfa metni ret cümlesi) + insan kartında büste yönlendirme (tek satır). */
  function kartRetGuncelle(it) {
    var r = S.alanKartRet;
    if (!r) return;
    while (r.firstChild) r.removeChild(r.firstChild);
    if (S.ornekNotP) S.ornekNotP.textContent = it && it.kanit === "render" ? it.tur.ornek_notu || "" : "";
    if (!it) return;
    r.appendChild(el("p", "foto-uretim-kart-ret", it.kart.ret));
    if (it.kart.alt === "insan" && kartListede("bust")) {
      var y = el("p", "foto-uretim-yonlendir");
      var b = el("button", null, BUST_YONLENDIRME);
      b.type = "button"; b.id = "foto-bust-yonlendir";
      b.addEventListener("click", function () {
        pencereGit(1);
        var d = S.galeriKutu ? S.galeriKutu.childNodes : [];
        for (var i = 0; i < d.length; i++) {
          if (d[i].getAttribute("data-kart") === "bust" && typeof d[i].focus === "function") d[i].focus();
        }
      });
      y.appendChild(b);
      r.appendChild(y);
    }
  }

  /* Tür seçimini URL hash (#tur=<kart>) ve sessionStorage'a yazar (13:5x; yenilemede korunur). */
  function turSecimiKaydet(kod) {
    try {
      if (kok.sessionStorage && kok.sessionStorage.setItem) {
        kok.sessionStorage.setItem("pruvo_foto_tur", kod);
      }
    } catch (e) { /* sessionStorage yoksa sessizce geç */ }
    try {
      if (kok.location && kok.location.hash !== undefined) {
        var yeni = "#tur=" + encodeURIComponent(kod);
        if (history && history.replaceState) {
          history.replaceState(null, "", yeni);
        } else if (kok.location.replace) {
          kok.location.replace(yeni);
        }
      }
    } catch (e) { /* hash yazılamıyorsa sessizce geç */ }
  }

  /* Kartlar çizildiğinde URL hash + sessionStorage'dan seçimi dene (kart kodu ya da tür kodu; tür
     kodundan ilk kartı). Yalnız ÇİZİLEN kart seçilebilir. */
  function turSecimiYukle() {
    var kod = null;
    try {
      if (kok.sessionStorage && kok.sessionStorage.getItem) {
        kod = kok.sessionStorage.getItem("pruvo_foto_tur");
      }
    } catch (e) { /* yoksay */ }
    if (!kod && kok.location && typeof kok.location.hash === "string") {
      var m = kok.location.hash.match(/tur=([^&]+)/);
      if (m) { try { kod = decodeURIComponent(m[1]); } catch (e) { kod = null; } }
    }
    if (!kod || !S.galeriListe) return;
    for (var i = 0; i < S.galeriListe.length; i++) {
      var it = S.galeriListe[i];
      if (it.kart.kod === kod || it.tur.kod === kod) {
        S.kartKod = it.kart.kod;
        S.altTur = it.kart.alt;
        S.tur = it.tur.kod;
        return;
      }
    }
  }

  /* ============== KAPALI ============== */
  // Kapalı / yükleniyor yazısı ① penceresinin kart alanına yazılır (kutu dışında öğe YOK).
  function cizKapali() {
    var hedef = S.ornekBlok;
    if (!hedef) return;
    while (hedef.firstChild) hedef.removeChild(hedef.firstChild);
    var kutu = el("div", "foto-uretim-blok");
    var p = el("p");
    p.appendChild(document.createTextNode(
      "Şu an fotoğraftan sipariş alınamıyor. Sorunu "));
    var a = el("a", "foto-uretim-kapat-a", "WhatsApp'tan yaz");
    a.href = WA; a.target = "_blank"; a.rel = "noopener";
    p.appendChild(a);
    p.appendChild(document.createTextNode("abilirsin."));
    kutu.appendChild(p);
    hedef.appendChild(kutu);
  }

  // /acik cevabı gelene dek nötr yer tutucu: durum BİLİNMEDEN "alınamıyor" denmez
  // (bölüm görünüme girmeden /acik istenmez; gizli sekmede saatlerce sürebilir).
  function cizYukleniyor() {
    var hedef = S.ornekBlok;
    if (!hedef) return;
    while (hedef.firstChild) hedef.removeChild(hedef.firstChild);
    var kutu = el("div", "foto-uretim-blok");
    kutu.appendChild(el("p", null, "Sipariş formu yükleniyor…"));
    hedef.appendChild(kutu);
  }

  /* ============== ② + ③ FORMU ==============
     ② Resim yükle: kartın foto şartı + dürüstlük + TEK yükleme kutusu + "Nasıl olsun?" + parça kapısı.
     ③ Renk, boyut ve malzeme: renk (palet 1..tavan / bölge rengi) + ölçü sürgüsü + malzeme (kayıttaki
     `malzemeler`; boşsa satır YOK) + form parametreleri + CANLI FİYAT (F.fiyatKurus). */
  function cizForm() {
    if (!S.pencereler.length || !S.tur) return;
    var p2 = S.pencereler[1], p3 = S.pencereler[2];
    while (p2.firstChild) p2.removeChild(p2.firstChild);
    while (p3.firstChild) p3.removeChild(p3.firstChild);
    if (!S.secim) S.secim = varsayilanSecim(S.tur);

    S.alanKartRet = el("div", "foto-uretim-kart-sart");
    p2.appendChild(S.alanKartRet);
    var durust = el("div", "foto-uretim-durustluk");
    S.durustP = el("p", null, "");
    S.ornekNotP = el("p", null, "");
    ek(durust, S.durustP, S.ornekNotP);
    p2.appendChild(durust);
    cizYukleKutu(p2);
    S.alanDosya = el("div", "foto-uretim-form-grup");
    p2.appendChild(S.alanDosya);
    doldurS1Dosya();
    // K2b: UYUM KAPISI paneli — dosya/not girdilerinden sonra (arka planda; yalnız soru/RED'de görünür).
    // uyumSonuc: null | "uygun" | "uygun_degil" | "belirsiz". uygun_degil'de ret cümlesi; belirsiz'de soru.
    S.alanUyum = el("div", "foto-uretim-form-grup foto-uretim-uyum");
    S.alanUyum.id = "foto-uyum";
    p2.appendChild(S.alanUyum);
    cizUyum();

    S.alanSecim = el("div", "foto-uretim-form-grup");
    S.alanSecim.id = "foto-renk";
    p3.appendChild(S.alanSecim);
    S.alanOlcu = el("div", "foto-uretim-form-grup");
    p3.appendChild(S.alanOlcu);
    S.alanMalzeme = el("div", "foto-uretim-form-grup");
    S.alanMalzeme.id = "foto-malzeme";
    p3.appendChild(S.alanMalzeme);
    S.alanForm = el("div", "foto-uretim-form-grup");
    p3.appendChild(S.alanForm);
    S.alanCanliFiyat = el("p", "foto-uretim-canli-fiyat");
    S.alanCanliFiyat.id = "foto-canli-fiyat";
    S.alanCanliFiyat.setAttribute("aria-live", "polite");
    p3.appendChild(S.alanCanliFiyat);
    doldurS1Olcu();
    doldurS1Secim();
    doldurS1Form();
    durustlukGuncelle();
    kartRetGuncelle(kartListede(S.kartKod));
    guncelleS1Buton();
  }

  // Kayıttan varsayılan seçim: her renk bölgesinin ilk rengi, her malzeme bölgesinin ilk malzemesi
  // (sunucu deterministik türde `<bolge>_renk` / `<bolge>_malzeme` ister; secimDogrula).
  function varsayilanSecim(kod) {
    var t = F && F.turBul ? F.turBul(kod) : null, c = {}, var_ = false;
    if (!t) return null;
    for (var i = 0; i < (t.renk_bolgeleri || []).length; i++) {
      var b = t.renk_bolgeleri[i];
      if (b && b.renkler && b.renkler.length) { c[b.kod + "_renk"] = b.renkler[0]; var_ = true; }
    }
    for (var m in (t.malzemeler || {})) {
      if (Object.prototype.hasOwnProperty.call(t.malzemeler, m) && t.malzemeler[m] && t.malzemeler[m].length) {
        c[m + "_malzeme"] = t.malzemeler[m][0]; var_ = true;
      }
    }
    return var_ ? c : null;
  }

  // ③ renk + malzeme: palet türünde 1..tavan renk (paletSecici); bölge türünde bölge başına renk;
  // malzeme listesi kayıttan (bölge başına; boşsa satır çıkmaz). Malzeme fiyata ETKİ ETMEZ.
  function doldurS1Secim() {
    if (!S.alanSecim || !S.alanMalzeme) return;
    while (S.alanSecim.firstChild) S.alanSecim.removeChild(S.alanSecim.firstChild);
    while (S.alanMalzeme.firstChild) S.alanMalzeme.removeChild(S.alanMalzeme.firstChild);
    var t = F.turBul(S.tur);
    if (!t) return;
    if (!S.secim) S.secim = varsayilanSecim(S.tur);
    if (F.renkPaleti(t.kod)) {
      S.alanSecim.appendChild(paletSecici(t, function () { doldurS1Secim(); guncelleS1Buton(); }));
    } else {
      for (var i = 0; i < (t.renk_bolgeleri || []).length; i++) {
        (function (b) {
          var g = el("div", "foto-uretim-form-grup");
          g.setAttribute("data-renk-bolge", b.kod);
          radyoGrubu(g, b.ad + " rengi", "foto-renk-" + b.kod, b.renkler || [], S.secim[b.kod + "_renk"], function (d) {
            S.secim[b.kod + "_renk"] = d;
            guncelleS1Buton();
          });
          S.alanSecim.appendChild(g);
        })(t.renk_bolgeleri[i]);
      }
    }
    var bolgeler = Object.keys(t.malzemeler || {});
    S.alanMalzeme.hidden = !bolgeler.length;
    for (var j = 0; j < bolgeler.length; j++) {
      (function (bolge) {
        radyoGrubu(S.alanMalzeme, "Malzeme", "foto-malzeme-" + bolge, t.malzemeler[bolge] || [],
          S.secim[bolge + "_malzeme"], function (d) { S.secim[bolge + "_malzeme"] = d; guncelleS1Buton(); });
      })(bolgeler[j]);
    }
    renkKosulGuncelle();
  }

  // ③ CANLI FİYAT — TEK formül (F.fiyatKurus; sunucunun ödemede kullandığı AYNI fonksiyon), renk sayısıyla.
  function canliFiyatGuncelle() {
    if (!S.alanCanliFiyat) return;
    var nt = seciliTurBul();
    var kurus = nt && !F.olcuTuretilmis(nt.kod) ? F.fiyatKurus(nt.kod, S.olcu, renkSayisi(nt)) : null;
    S.alanCanliFiyat.textContent = kurus != null ? "Fiyat: " + F.tlMetni(kurus) : "";
  }

  /* ============== ④ S1 — ÖNİZLEME İSTEĞİ ==============
     Aydınlatma tiki (tek) + doğrulama → "Önizleme oluştur" (parça kapısı ÖNCE koşar). D/R türünde örnek
     render + ONIZLEME_SONRA; sağlayıcı türünde isteğe bağlı 2D konsept. */
  function cizS1() {
    if (!S.alan) return;
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);

    S.alanOnizlemeSonra = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOnizlemeSonra);
    doldurS1OnizlemeSonra();

    S.alanOnay = el("div", "foto-uretim-form-grup");
    S.alan.appendChild(S.alanOnay);
    doldurS1Onay();

    S.alanCap1 = el("div", "foto-uretim-captcha");
    S.alan.appendChild(S.alanCap1);
    turnsRender(S.alanCap1, function (t) {
      S.captchaToken1 = t;
      guncelleS1Buton();
    });

    S.alanKonsept = el("div", "foto-uretim-konsept");
    S.alanKonsept.id = "foto-konsept";
    S.alan.appendChild(S.alanKonsept);
    cizKonsept();

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

  /* Önizleme/sepet paneli sıfırlanır (tür ya da fotoğraf değişti): eski önizleme yeni seçimin sepetine girmez. */
  function onizlemeSifirla() {
    yoksDurdur();
    ssIsSil();
    S.is = null;
    S.gorsel = null;
    S.gecerlilik = null;
    S.fiyatKurus = null;
    S.b2Onay = false;
    S.adet = 1;
    adimKoy("S1");
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
    // TÜRETİLMİŞ ölçü ekseni: sürgü YOK — fiyat önizlemede ölçülen en uzun boyuttan (sunucu kaydı).
    if (F.olcuTuretilmis(nt.kod)) {
      S.alanOlcu.appendChild(el("p", "foto-uretim-ayrinti foto-uretim-olculen-not", F.OLCULEN_FIYAT_NOTU));
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
    S.alanDosya.hidden = !false && !fotoGerekir();
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
      // K2b: uretimNotu değişti → uyum kontrolü yeniden koşar (b) kolu için.
      cizUyum();
      guncelleS1Buton();
    }
    ta.addEventListener("input", say);
    say();
    kap.appendChild(ta);
    kap.appendChild(sayac);
    kap.appendChild(el("p", "foto-uretim-ayrinti", "Notunuz üretime iletilir."));
    S.alanDosya.appendChild(kap);
    notAlaniGoster();
  }

  /* ============== 2D KONSEPT (adım ② içinde, isteğe bağlı) ============== */
  // Konsept yalnız sunucunun /foto/acik `konsept.turler` listesindeki (sağlayıcı kollu) türde ve
  // fotoğraf seçiliyken sunulur. Not boşsa da çalışır (foto -> stil konsepti).
  function konseptAcik() {
    var k = S.acikVeri && S.acikVeri.konsept;
    return !!(k && k.turler && k.turler.indexOf(S.tur) >= 0 && fotoGerekir() &&
      !false && !!!(F && F.kolu && F.kolu(S.tur) === "deterministik"));
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

  /* ============== UYUM PANELİ ==============
     "Nasıl olsun?" notu (S.uretimNotu) değiştikçe + belirsiz soruya tıklandıkça yeniden çizilir.
     - "uygun": panel boş (form görünür, önizleme açılır).
     - "belirsiz": foto türünde kapalı soru (Evet/Hayır). Cevap → uyumSonuc güncellenir.
     - "uygun_degil": A metni (birebir) + ① ızgarasına dönen düğme; önizleme düğmesi pasif. */
  function cizUyum() {
    if (!S.alanUyum) return;
    while (S.alanUyum.firstChild) S.alanUyum.removeChild(S.alanUyum.firstChild);
    if (!S.tur) return;
    var sonuc = uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap);
    S.uyumSonuc = sonuc;
    if (sonuc === "uygun") return;  // görünmez — önizleme düğmesi açılır
    if (sonuc === "uygun_degil") {
      // A ekranı: metin (birebir) + ① ızgarasına dönen düğme
      var baslik = el("h3", "foto-uretim-uyum-baslik", "Parça / yedek parça isteği");
      S.alanUyum.appendChild(baslik);
      var p = el("p", "foto-uretim-uyum-metin", A_METIN_BIREBIR);
      S.alanUyum.appendChild(p);
      var donBtn = el("button", "foto-uretim-buton-birincil", "Tasarım ürünlerine dön");
      donBtn.type = "button";
      donBtn.id = "foto-uyum-don";
      donBtn.addEventListener("click", function () {
        S.belirsizCevap = null;
        S.uyumSonuc = null;
        adimKoy("secim");
      });
      S.alanUyum.appendChild(donBtn);
      return;
    }
    // sonuc === "belirsiz" → foto türünde kapalı soru (Evet/Hayır)
    S.alanUyum.appendChild(el("h3", "foto-uretim-uyum-baslik", "Tasarım mı, parça mı?"));
    S.alanUyum.appendChild(el("p", "foto-uretim-uyum-soru", UYUM_SORU));
    var evet = el("button", "foto-uretim-buton-ikincil", "Evet");
    evet.type = "button";
    evet.id = "foto-uyum-evet";
    evet.addEventListener("click", function () {
      S.belirsizCevap = true;
      cizUyum();
      guncelleS1Buton();
    });
    var hayir = el("button", "foto-uretim-buton-birincil", "Hayır");
    hayir.type = "button";
    hayir.id = "foto-uyum-hayir";
    hayir.addEventListener("click", function () {
      S.belirsizCevap = false;
      cizUyum();
      guncelleS1Buton();
    });
    var dugumG = el("div", "foto-uretim-uyum-butonlar");
    dugumG.appendChild(evet);
    dugumG.appendChild(hayir);
    S.alanUyum.appendChild(dugumG);
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
    // K2b: UYUM KAPISI — 2D konsept (ücretli çağrı) isteğinden ÖNCE. "uygun_degil"/"belirsiz" → 0 istek.
    var uyumK = uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap);
    if (uyumK !== "uygun") { konseptHataKoy(""); cizUyum(); guncelleS1Buton(); return; }
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
    // K2b: B2 satırı (foto-b2-onay-s1) buradan ÇIKARILDI — TEK B2 yalnız ③'te ("Sepete ekle" yanında).
    // "Sepete ekle" tik kapısı ③'te zaten aydınlatma + B2 + (türetilmiş eksen fiyatsız) ile çalışır.
  }

  function guncelleS1Buton() {
    yapbozParcaNotu();
    canliFiyatGuncelle();
    gezintiGuncelle();
    if (!S.alanButon) return;
    var btn = S.alanButon.querySelector("button");
    if (!btn) return;
    var lit = false;
    // Tarayıcı önizleyicisi olmayan D/R türü: önizlemeyi üreteç koşucusu çıkarır (/foto/onizleme
    // kuyruğu); fotoğraf yalnız türün girdisinde varsa istenir.
    // K2b: uyum kontrolü geçmeden önizleme/konsept düğmesi AÇILMAZ ("uygun_degil" veya "belirsiz" ise).
    var uyumOK = uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap) === "uygun";
    var tam = uyumOK && (!!S.dosya || !fotoGerekir()) && !!S.aydinlatmaOnay &&
      !!S.captchaToken1 && !!S.tur && !!S.olcu && (!lit || !!null) &&
      formDogrula().ok;
    btn.disabled = !tam;
    btn.textContent = lit ? "Siparişe geç" : "Önizleme oluştur";
    konseptButonGuncelle();
  }

  /* ============== S2 ============== */
  /* Türetilmiş eksen fiyat satırı: fiyat yalnız durum yanıtından (S.fiyatKurus); yeni önizleme isteğinde
     sıfırlanır, o yüzden önizleme beklenirken eski fiyat GÖSTERİLMEZ ("hesaplanıyor" yazar). */
  function olculenFiyatEl(bekliyor) {
    return el("p", "foto-uretim-surgu-fiyat foto-uretim-olculen-fiyat", S.fiyatKurus != null
      ? S.olcu + " mm → " + F.tlMetni(S.fiyatKurus)
      : bekliyor ? "Fiyat hesaplanıyor — önizlemede ölçülen en uzun boyuttan."
      : "Fiyat hesaplanamadı; yeni önizleme oluştur.");
  }

  function cizS2() {
    if (!S.alan) return;
    konseptDurdur();
    turnsTemizle(S.alanCap1);
    S.captchaToken1 = "";
    while (S.alan.firstChild) S.alan.removeChild(S.alan.firstChild);
    S.alan.appendChild(el("p", null, !!(F && F.kolu && F.kolu(S.tur) === "deterministik") ?
      "Önizlemen sırada; üretim dosyasıyla birlikte hazırlanıyor…" :
      "Önizlemen hazırlanıyor… (genelde 1 dakika)"));
    var t2 = seciliTurBul();
    if (t2 && F.olcuTuretilmis(t2.kod)) S.alan.appendChild(olculenFiyatEl(true));
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

    S.alan.appendChild(el("p", "foto-uretim-ayrinti", false ? "" :
      !!(F && F.kolu && F.kolu(S.tur) === "deterministik") ? ((litofanKaydi() || {}).durustluk || "") :
      "Önizleme — ürün bunun seçtiğin renk sayısında (1–4) kabartma yorumu olur; birebir aynısı değildir."));
    if (false && S.secim) {
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

    /* Ölçü/renk ③'te seçilir (sürgü + palet ③'e taşındı). Türetilmiş eksende fiyat ÖNİZLEME SONUCUNA bağlı
       (sunucunun ölçtüğü en uzun boyut) → o satır ④'te kalır. */
    if (nt && F.olcuTuretilmis(nt.kod)) {
      var olcG = el("div", "foto-uretim-form-grup");
      olcG.appendChild(el("label", "foto-uretim-form-etiket", "Ölçü"));
      olcG.appendChild(olculenFiyatEl(false));
      olcG.appendChild(el("p", "foto-uretim-ayrinti", F.OLCULEN_FIYAT_NOTU));
      S.alan.appendChild(olcG);
    }

    /* ozet */
    // Birim fiyat TEK formülden (sunucunun ödemede kullandığı AYNI F.fiyatKurus), renk sayısıyla (ek renk dahil).
    var rs = renkSayisi(nt);
    var ekRenk = nt && rs > 1 ? (rs - 1) * (F.ekRenkKurus(nt.kod) || 0) : 0;
    var fiyat = nt ? (F.olcuTuretilmis(nt.kod) ? (S.fiyatKurus != null ? S.fiyatKurus + ekRenk : null)
      : F.fiyatKurus(nt.kod, S.olcu, renkSayisi(nt))) : null;
    if (fiyat != null) {
      var urunToplam = fiyat * S.adet;
      var kargo = kargoUcreti(urunToplam);
      var genel = urunToplam + kargo;
      var ozet = el("div", "foto-uretim-ozet");
      if (ekRenk > 0) ozet.appendChild(el("div", null, "Ek renk ×" + (rs - 1) + ": " + tlMetni(ekRenk) + (S.adet > 1 ? " (adet başı)" : "")));
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
    // B2 SORUMLULUK SATIRI (BaBa 8 Eki 18:4x — sayfa-3adim K2): aydınlatma onayının YANINA ikinci onay
    // kutusu; ikisi de işaretli değilken "Sepete ekle" pasif kalır.
    var b2Lbl = el("label", "foto-uretim-form-secenek-inline");
    b2Lbl.setAttribute("for", "foto-b2-onay");
    var b2Inp = el("input");
    b2Inp.type = "checkbox"; b2Inp.id = "foto-b2-onay";
    b2Inp.checked = !!S.b2Onay;
    b2Inp.addEventListener("change", function (e) {
      S.b2Onay = !!e.target.checked;
      guncelleSipButonu();
    });
    ek(b2Lbl, b2Inp);
    ek(b2Lbl, " Fotoğraftan üretilen ürünler tasarım ürünüdür; mekanik uyum ve ölçü uygunluğu taahhüt edilmez.");
    butonG.appendChild(b2Lbl);
    S.b2Inp = b2Inp;
    var sipBtn = el("button", "foto-uretim-buton-birincil", "Sepete ekle");
    sipBtn.type = "button";
    sipBtn.id = "foto-sip-btn";
    sipBtn.addEventListener("click", function () { sepeteEkle(nt, fiyat, rs); });
    // Aydınlatma onayı + B2 sorumluluk satırı olmadan sipariş düğmesi açılmaz (K2: B2 tik kapısı);
    // türetilmiş eksende bu önizlemenin ölçülmüş fiyatı yoksa da açılmaz (fiyatsız sipariş yok).
    // K2b-fin: formül TEK fonksiyona toplandı (cizS3 + guncelleSipButonu aynı yerden okur; mutant testi
    // birebir çalışır — bkz. M-B2 kapama testi).
    sipBtn.disabled = sipBtnKapaliMi(nt);
    butonG.appendChild(sipBtn);
    if (!S.aydinlatmaOnay) {
      butonG.appendChild(el("p", "foto-uretim-ayrinti", "Aydınlatma metni güncellendi; sipariş için yeni önizleme oluştur."));
    }
    // İPTAL: ④ → ① Tür seç; durum sıfırlanır (tür, kart, alt tür, dosya, onaylar, önizleme).
    // K2b: ② çocukları SİLİNMEZ — İptal yalnız ①'e döner (Kabul: İptal→yeni tür seç→② yükleme kutusu +
    // not alanı + uyum paneli DOM'da kalır; galeriSec yeni türün kaydıyla yeniden doldurur).
    var iptalBtn = el("button", "foto-uretim-buton-ikincil", "İptal");
    iptalBtn.type = "button";
    iptalBtn.id = "foto-iptal-btn";
    iptalBtn.addEventListener("click", function () {
      yoksDurdur();
      ssIsSil();
      S.is = null;
      S.dosya = null;
      S.aydinlatmaOnay = false;
      S.b2Onay = false;
      S.gorsel = null;
      S.gecerlilik = null;
      S.fiyatKurus = null;
      S.adet = 1;
      S.tur = null;
      S.kartKod = null;
      S.altTur = null;
      S.olcu = null;
      S.parametre = {};
      S.secim = null;
      S.renkler = [];
      S.uretimNotu = "";
      S.belirsizCevap = null;
      S.uyumSonuc = null;
      turSecimiKayitTemizle();
      if (S.ornekBlok) ornekCiz(S.ornekBlok, S.acikVeri ? S.acikVeri.turler.map(function (x) { return x.kod; }) : null);
      adimKoy("secim");
    });
    butonG.appendChild(iptalBtn);
    S.alan.appendChild(butonG);
  }
  // Tik kapısı: aydınlatma onayı ve B2 satırı değiştikçe "Sepete ekle" disabled güncellenir.
  // NOT: aynı formül cizS3'te zaten yazılı; burada B2 değişiminde yeniden hesaplanır (tek kapı).
  // K2b-fin: B2/aydinlatma/fiyat kapı formülü TEK yerde (cizS3 + guncelleSipButonu çağırır).
  function sipBtnKapaliMi(nt) {
    return !S.aydinlatmaOnay || !S.b2Onay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);
  }
  function guncelleSipButonu() {
    if (!S.alan) return;
    var sipBtn = document.getElementById("foto-sip-btn");
    if (!sipBtn) return;
    var nt = seciliTurBul();
    sipBtn.disabled = sipBtnKapaliMi(nt);
  }
  // ③ → ① dönüşünde sessionStorage'daki tür seçimi temizlenir.
  function turSecimiKayitTemizle() {
    try { if (kok.sessionStorage && kok.sessionStorage.removeItem) kok.sessionStorage.removeItem("pruvo_foto_tur"); } catch (e) { }
    try { if (kok.history && history.replaceState) history.replaceState(null, "", location.pathname + location.search); } catch (e) { }
  }

  /* ============== ③ → NORMAL SEPET ==============
     Ayrı foto ödeme yolu YOK (sayfa-3adim K1): kalem sitenin sepetine girer, ödeme + müşteri bilgisi normal
     checkout'ta (karma sepet tek ödeme). Kalem {foto_is, tur, olcu_mm, renkler[], renk_sayisi, onizleme_ref, atif};
     gosterim_kurus YALNIZ sepette gösterim içindir — /baslat'a gitmez, Worker fiyatı yeniden hesaplar. */
  function onizlemeRef() {
    var g = S.gorsel;
    return typeof g === "string" && g.length <= 300 && g.indexOf("/api/shop/foto/") === 0 ? g : "";
  }
  function fotoSepetSatiri(nt, fiyat, rs) {
    var k = sepetKalemi();
    var renkler = k.renkler || [];
    if (!k.renkler && k.secim) {
      for (var a in k.secim) {
        if (Object.prototype.hasOwnProperty.call(k.secim, a) && a.slice(-5) === "_renk" && renkler.indexOf(k.secim[a]) < 0) {
          renkler.push(k.secim[a]);
        }
      }
    }
    var satir = {
      foto_is: S.is, tur: nt.kod, olcu_mm: S.olcu, renkler: renkler, renk_sayisi: rs,
      onizleme_ref: onizlemeRef(),
      atif: (typeof kok.pruvoAtifTopla === "function") ? kok.pruvoAtifTopla() : {},
      adet: 1,
      baslik: "Fotoğrafından özel üretim — " + nt.ad + " (" + S.olcu + " mm)",
      gosterim_kurus: fiyat,
      aydinlatma_onay: !!S.aydinlatmaOnay, onay_surum: F.onay_surum
    };
    if (k.secim) satir.secim = k.secim;
    if (S.gecerlilik) satir.gecerlilik = S.gecerlilik;
    return satir;
  }
  function sepeteEkle(nt, fiyat, rs) {
    if (!S.is || !S.olcu || !nt || fiyat == null || !S.aydinlatmaOnay) {
      adimKoy("S3", "Sepete eklemek için önizleme ve onay gerekli.", true); return;
    }
    var ekle = kok.pruvoSepeteFotoEkle;
    if (typeof ekle !== "function" || !ekle(fotoSepetSatiri(nt, fiyat, rs))) {
      adimKoy("S3", "Sepete eklenemedi; sayfayı yenileyip yeniden dene.", true); return;
    }
    adimKoy("S3", "Sepete eklendi. Ödemeyi sepetten tamamlayabilirsin.");
  }

  /* ============== ADIM GECISI ==============
     Panel (④) durumu + pencere: "secim" = ① (panel S1'e sıfırlanır) · S1 = ④ paneli önizleme isteği
     (pencere değişmez) · S2/S3 = ④ (önizleme bekleniyor / hazır). */
  function adimKoy(adim, bildirim, hata) {
    S.adim = adim === "secim" ? "S1" : adim;
    if (bildirim != null) {
      S.bildirim = bildirim;
      S.bildirimHata = !!hata;
    } else {
      S.bildirim = "";
      S.bildirimHata = false;
    }
    if (adim === "kapali") { cizKapali(); pencereGit(1); }
    else if (adim === "secim") { cizS1(); pencereGit(1); }
    else if (adim === "S1") cizS1();
    else if (adim === "S2") { cizS2(); pencereGit(4); }
    else if (adim === "S3") { if (S.pencere === 4) cizS3(); else pencereGit(4); }
    yukleKutuGuncelle("");
    durumCubuguGoster();
    gezintiGuncelle();
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
      // ① kartları: yalnız /acik listesindeki türlerin kartları çizilir.
      if (S.ornekBlok) ornekCiz(S.ornekBlok, veri.turler.map(function (x) { return x.kod; }));
      var kayit = ssIsOku();
      if (kayit) {
        S.is = kayit.is;
        // 13:5x: tür seçimi artık kullanıcı TIKINDAN (kart); otomatik ilk-açık KALMAZ.
        S.tur = kayit.tur || S.tur || null;
        if (S.tur && (!S.kartKod || !kartListede(S.kartKod) || kartListede(S.kartKod).tur.kod !== S.tur)) {
          S.kartKod = null; S.altTur = null;
          for (var ki = 0; ki < S.galeriListe.length; ki++) {
            if (S.galeriListe[ki].tur.kod === S.tur) { S.kartKod = S.galeriListe[ki].kart.kod; S.altTur = S.galeriListe[ki].kart.alt; break; }
          }
          kartVurgula();
        }
        S.olcu = kayit.olcu || null;
        if (kayit.secim && typeof kayit.secim === "object") S.secim = kayit.secim;
        if (Array.isArray(kayit.renkler)) S.renkler = kayit.renkler;
        // Onay yalnız AYNI metin sürümüne verildiyse geri gelir (eski sürüm onayı sayılmaz).
        S.aydinlatmaOnay = kayit.onay === F.onay_surum;
        if (S.tur && seciliTurBul()) cizForm();
        durumSorgula(kayit.is, true);
        return;
      }
      // 13:5x: ilk-açık otomatik seçim yok — kullanıcı karta basmalı (yenilemede seçili kart korunur).
      if (S.tur && seciliTurBul()) cizForm(); else S.tur = null;
      adimKoy("S1");
      pencereGit(S.tur ? 2 : 1);
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
          // Türetilmiş eksen: fiyat SUNUCUNUN (önizlemede ölçülen ölçüden); bölüm kendisi hesaplamaz.
          S.fiyatKurus = typeof veri.fiyat_kurus === "number" ? veri.fiyat_kurus : null;
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
            !!(F && F.kolu && F.kolu(S.tur) === "deterministik") ? "Önizleme hazırlanamadı, tekrar deneyebilirsin." :
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
    var uretec = !!(F && F.kolu && F.kolu(S.tur) === "deterministik");
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
    
    if (!!(F && F.kolu && F.kolu(S.tur) === "deterministik")) { uretecOnizle(); return; }
    // K2b: UYUM KAPISI — kredi harcayan 3D önizleme isteğinden ÖNCE koşar. "uygun_degil" veya "belirsiz"
    // ise 2D önizleme = 0 istek (cizUyum A ekranını veya soruyu zaten gösterdi). Burada yalnız UI tutarlılığı.
    var uyum = uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap);
    if (uyum !== "uygun") {
      cizUyum();
      guncelleS1Buton();
      return;
    }
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
    // K2b: UYUM KAPISI — üreteç önizlemesi (ücretli) isteğinden ÖNCE.
    var uyum = uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap);
    if (uyum !== "uygun") { cizUyum(); guncelleS1Buton(); return; }
    if (fotoGerekir() && !S.dosya) { adimKoy("S1", "Lütfen fotoğrafını seç.", true); return; }
    if (false && !S.dosya) { adimKoy("S1", "Lütfen SVG dosyanı seç.", true); return; }
    if (!S.aydinlatmaOnay) { adimKoy("S1", "Aydınlatma metnini onaylamalısın.", true); return; }
    if (!S.captchaToken1) { adimKoy("S1", "Lütfen doğrulama kutusunu işaretle.", true); return; }
    if (!S.tur || !S.olcu) { adimKoy("S1", "Tür ve ölçü seçmelisin.", true); return; }
    // Yeni önizleme = yeni ölçü: eski önizlemenin fiyatı yeni parametreyle GÖSTERİLMEZ (durum yanıtı yazar).
    S.fiyatKurus = null;
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
    if (false) {
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