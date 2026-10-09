/*
 * foto-uretim.js — PRUVO ana sayfa "Fotoğrafından özel üretim" bölümü ekranı.
 *
 * - Veri: window.PRUVO_FOTO (foto-uretim-veri.js) — turler, ornekler, onay.
 * - API'ler: GET /api/shop/foto/acik, POST /api/shop/foto/onizleme,
 *   GET /api/shop/foto/durum. Odeme AYRI YOL DEGIL: ③ "Sepete ekle" kalemi sitenin normal sepetine koyar
 *   (window.pruvoSepeteFotoEkle, index.html); odeme + musteri bilgisi normal checkout'ta.
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
      ret: "Anahtarlık için net bir fotoğraf ya da kısa bir yazı gerekir." },
    { kod: "yapboz", tur: "yapboz", alt: null, ad: "Yapboz",
      ret: "Yapboz için açık-koyu tonları belirgin, yüksek çözünürlüklü fotoğraf gerekir." }
  ];
  // İnsan kartı ②'de: ret cümlesinin altında tek satır büste yönlendirme (Büst kartına döner).
  var BUST_YONLENDIRME = "Portre için Büst";
  // PENCERELER — kutu başlığındaki ①②③④ göstergesi + açıklama (sayfa metni, BİREBİR).
  var PENCERELER = [
    { no: "①", ad: "Tür seç", aciklama: "6 seçenekten birini seç: insan figürü, hayvan ve model figürü, kabartma plaket, büst, anahtarlık ya da yapboz." },
    { no: "②", ad: "Resim yükle", aciklama: "Resmi yükle; \"Nasıl olsun?\" kısmında ne istediğini kısaca yaz. Uyumsuz resimde tek kısa mesaj gösterilir." },
    { no: "③", ad: "Renk, boyut ve malzeme", aciklama: "Renk: Siyah, Beyaz, Gri ya da Renkli (+%15; renkler fotoğrafından otomatik seçilir). Malzeme: PLA ya da PETG (+%30). Boyut sürgüden ayarlanır; fiyat ölçüye göre canlı görünür; en uzun boyut mm × 10 TL, en az ₺600." },
    { no: "④", ad: "Önizleme ve onay", aciklama: "Önizlemeyi gör, onayları ver; Sepete ekle açılır." }
  ];
  var SS_IS = "pruvo_foto_is";
  // ORTAK RET CÜMLESİ (sayfa metni "Ortak ret cümlesi (parça / yedek parça)", BİREBİR): parça kapısı
  // `uygun_degil` dediğinde ② içinde gösterilen tek mesaj + ①'e dönüş düğmesi.
  var A_METIN_BIREBIR = "Fotoğraftan parça ya da yedek parça üretmiyoruz.";
  // UYUM KAPISI (BaBa 17:5x + 18:0x — parça/yedek parça foto programından ÇIKTI): 2D önizleme isteği
  // PARA harcıyor; tarayıcıdaki önizleyici görsel sınıflayıcı (ücretli API) bu turda YOK → foto türleri
  // için tek kapalı soru (Evet/Hayır) vardı — Okan 9 Eki "bunu sil": SORU YOK, her türde yalnız anahtar kelime denetimi.
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
    // ① (10 Eki): kalan günlük önizleme hakkı — YALNIZ sunucu yanıtından (200 `kalan` · 429 onizleme-siniri -> 0);
    // null = henüz bilinmiyor. programKapali: /foto/onizleme 503 "kapali" döndü.
    kalanHak: null,
    programKapali: false,
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
    alanYazi: null,
    yaziHata: null,
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
    uyumSonuc: null
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
     Deterministik kol: anahtar kelime denetimi (foto türlerindeki kapalı soru Okan 9 Eki ile SİLİNDİ).
     Kapalı küme: "uygun" | "uygun_degil" (başka değer yok). Kredi harcayan 2D/3D
     önizleme çağrıları bu fonksiyonu ÖNCE çağırır; sonuç "uygun_degil" ise A ekranı + 0 istek. */
  function trNorm(metin) {
    var s = String(metin == null ? "" : metin).toLowerCase();
    s = s.replace(/ı/g, "i").replace(/i̇/g, "i").replace(/i/g, "i");
    s = s.replace(/ş/g, "s").replace(/ğ/g, "g").replace(/ü/g, "u")
         .replace(/ö/g, "o").replace(/ç/g, "c");
    s = s.replace(/[^a-zçğıöşü0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
    return s;
  }
  function uyumKontrol(kod, tarif) {
    // Anahtar kelime denetimi (her türde; foto + girdi). Foto türlerindeki kapalı soru ("Tasarım mı,
    // parça mı?") Okan 9 Eki "bunu sil" ile KALDIRILDI — sonuç kümesi artık "uygun" | "uygun_degil".
    if (tarif && typeof tarif === "string" && trNorm(tarif).length) {
      if (UYUM_DESEN.test(trNorm(tarif))) return "uygun_degil";
    }
    return "uygun";
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
    // Bölüm içindeki HER `hidden` eleman gizli: sınıf kuralı `display:flex` vb. `[hidden]`ı EZMEZ (9 Eki: "Foto ekle"
    // kutusu hidden=true iken display:flex ile görünüyordu — Okan "foto ekle çalışmıyor").
    ".foto-uretim [hidden]{display:none!important;}" +
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
    ".foto-uretim-not{width:100%;min-height:72px;resize:vertical;padding:8px 10px;border:1px solid #d4dae3;" +
    "border-radius:6px;font:inherit;font-size:14px;box-sizing:border-box;}" +
    ".foto-uretim-not-sayac{font-size:12px;color:#5b6573;text-align:right;}" +
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

  /* ============== FOTOĞRAFTAN RENK (R2, Okan 9 Eki) ==============
     "ürünün renk seçimini müşterinin eklediği resime otomatik yapılsın": seçilen fotoğraf 64×64'e küçültülür,
     F.fotoRenkleri baskın renkleri filament renklerine eşler (tarayıcıda; kredi 0, harici API YOK). */
  function fotoRenkCikar(dosya) {
    if (S.fotoRenkDosya === dosya) return;
    S.fotoRenkDosya = dosya;
    S.fotoRenkleri = [];
    var yenile = function () { if (S.alanSecim && S.tur) { doldurS1Secim(); guncelleS1Buton(); } };
    if (!dosya || !kok.URL || typeof kok.URL.createObjectURL !== "function" || typeof Image === "undefined") {
      yenile(); return;
    }
    var url;
    try { url = kok.URL.createObjectURL(dosya); } catch (e) { yenile(); return; }
    var img = new Image();
    img.onload = function () {
      try {
        var tuval = document.createElement("canvas");
        tuval.width = 64; tuval.height = 64;
        var ctx = tuval.getContext("2d");
        ctx.drawImage(img, 0, 0, 64, 64);
        if (S.fotoRenkDosya === dosya) S.fotoRenkleri = F.fotoRenkleri(ctx.getImageData(0, 0, 64, 64).data, 4);
      } catch (e) { S.fotoRenkleri = []; }
      try { kok.URL.revokeObjectURL(url); } catch (e) { }
      yenile();
    };
    img.onerror = function () { try { kok.URL.revokeObjectURL(url); } catch (e) { } };
    img.src = url;
  }

  /* ============== OTURUM DEPOSU ============== */
  function ssIsKaydet() {
    if (!S.is) return;
    var kayit = { is: S.is, tur: S.tur, olcu: S.olcu };
    if (false && S.secim) kayit.secim = S.secim;
    if (S.renkler && S.renkler.length) kayit.renkler = S.renkler;
    kayit.renk_secim = S.renkSecim;
    kayit.malzeme = S.malzeme;
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
  // İleri şartı: ① tür seçili · ② girdilerden EN AZ BİRİ (foto ya da yazı; F.girdiYeterli — sunucuyla AYNI)
  // + parça kapısı "uygun" · ③ ölçü + form geçerli.
  function ileriAcikMi() {
    if (S.pencere === 1) return !!S.tur;
    if (S.pencere === 2) {
      return !!S.tur && F.girdiYeterli(S.tur, { foto: !!S.dosya, parametreler: parametreGovde() }) === "" &&
        uyumKontrol(S.tur, S.uretimNotu) === "uygun";
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
  // Türün girdisinde yazı (form metin alanı) var mı — varsa metin alanları ② ekranında çizilir.
  function metinGirdisi() {
    var t = litofanKaydi();
    return !!t && !!t.girdi && t.girdi.indexOf("metin") >= 0;
  }
  // Kayıttan varsayılan seçim: her malzeme bölgesinin ilk malzemesi, her renk bölgesinin ilk rengi.
  // RENK + MALZEME (Okan 9 Eki 17:0x): renk 3 ana renkten biri (ürün TEK renk) ya da "Renkli" (+%15; renkler
  // müşterinin fotoğrafından OTOMATİK, F.fotoRenkleri — tarayıcıda, kredi 0); Renkli yalnız fotoğraflı akışta.
  // Malzeme PLA ya da PETG (+%30) kartı. Fiyat F.fiyatKurus(kod, mm, fiyatSecimi()) — sunucu AYNI fonksiyonu çağırır.
  var RENKLI = "Renkli";
  function renkliSunulur(kod) {
    return !!F.renkliSecilebilir(kod) && !!(S.fotoRenkleri && S.fotoRenkleri.length);
  }
  function renkliMi() { return S.renkSecim === RENKLI && renkliSunulur(S.tur); }
  function anaRenk() { return F.ANA_RENKLER.indexOf(S.renkSecim) >= 0 ? S.renkSecim : F.VARSAYILAN_RENK; }
  function seciliMalzeme() { return F.malzemeBul(S.malzeme) ? S.malzeme : F.VARSAYILAN_MALZEME; }
  function fiyatSecimi() { return { renkli: renkliMi(), malzeme: seciliMalzeme() }; }
  // Palet türünde renkler: ana renkte [renk]; Renkli'de fotoğraftan çıkan renkler (türün tavanı kadar).
  function paletRenkleri(kod) {
    var tavan = F.renkTavani(kod) || 1;
    return renkliMi() ? S.fotoRenkleri.slice(0, tavan) : [anaRenk()];
  }
  // Bölge türünde (deterministik seçim): ana renkte TÜM bölgeler o renk; Renkli'de fotoğraf renkleri sırayla
  // (tavan kadar). Malzeme her bölgeye aynı (yığılı gövdede karışık malzeme yok).
  function secimiEsle(t) {
    if (!S.secim) return;
    var bolgeler = t.renk_bolgeleri || [], fr = renkliMi() ? paletRenkleri(t.kod) : [anaRenk()];
    for (var i = 0; i < bolgeler.length; i++) S.secim[bolgeler[i].kod + "_renk"] = fr[i % fr.length];
    for (var m in (t.malzemeler || {})) {
      if (Object.prototype.hasOwnProperty.call(t.malzemeler, m)) S.secim[m + "_malzeme"] = seciliMalzeme();
    }
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
  // Ödeme kalemi: deterministik türde bölge seçimi (yalnız AKTİF bölgelerin rengi), palet türünde renkler,
  // renkli + malzeme (sunucu hepsini kayda karşı doğrular ve fiyatı kendisi hesaplar).
  function sepetKalemi() {
    var k = { foto_is: S.is, olcu_mm: S.olcu, adet: S.adet, renkli: renkliMi(), malzeme: seciliMalzeme() };
    if (F.kolu(S.tur) === "deterministik" && S.secim) k.secim = aktifRenkSecimi();
    if (F.renkPaleti(S.tur)) k.renkler = paletRenkleri(S.tur);
    return k;
  }
  // Renk seçici: tek seçim — Siyah · Beyaz · Gri · Renkli (+%15) (Renkli yalnız fotoğraflı akışta, renkler çıktıysa).
  // ③ ortak alan (renk/olcu/malzeme) altındaki TÜR cümlesi: kaydın `alan_aciklamalari`sı; yoksa "" (metin uydurulmaz).
  function alanAciklamasi(kod, alan) {
    var t = F && typeof F.turBul === "function" ? F.turBul(kod) : null;
    var m = t && t.alan_aciklamalari ? t.alan_aciklamalari[alan] : "";
    return typeof m === "string" ? m : "";
  }
  function renkSecici(nt, degisti) {
    var secenek = F.ANA_RENKLER.slice();
    if (renkliSunulur(nt.kod)) secenek.push(RENKLI);
    if (secenek.indexOf(S.renkSecim) < 0) S.renkSecim = F.VARSAYILAN_RENK;
    var g = el("div", "foto-uretim-form-grup");
    var fs_ = el("fieldset", "foto-uretim-renk-secim");
    fs_.appendChild(el("legend", "foto-uretim-form-etiket", "Renk"));
    for (var i = 0; i < secenek.length; i++) {
      (function (renk) {
        var lbl = el("label", "foto-uretim-form-secenek-inline");
        var inp = el("input");
        inp.type = "radio"; inp.name = "foto-renk"; inp.value = renk;
        inp.checked = S.renkSecim === renk;
        inp.addEventListener("change", function (e) {
          if (!e.target.checked) return;
          S.renkSecim = renk;
          degisti();
        });
        ek(lbl, inp, " " + (renk === RENKLI ? F.RENKLI_ETIKET : renk));
        fs_.appendChild(lbl);
      })(secenek[i]);
    }
    g.appendChild(fs_);
    var renkAcik = alanAciklamasi(nt.kod, "renk");
    if (renkAcik) g.appendChild(el("p", "foto-uretim-ayrinti", renkAcik));
    if (renkliMi()) {
      g.appendChild(el("p", "foto-uretim-ayrinti", "Fotoğrafından seçilen renkler: " + paletRenkleri(nt.kod).join(", ")));
    }
    return g;
  }
  // Malzeme kartları (2. resim): sıcaklık / ad / kullanım / o malzemeyle güncel fiyat; seçili kart lacivert çerçeveli.
  function malzemeKartFiyati(nt, kod) {
    var sec = { renkli: renkliMi(), malzeme: kod };
    if (F.olcuTuretilmis(nt.kod)) return S.fiyatKurus != null ? F.secimliKurus(S.fiyatKurus, sec) : null;
    return F.fiyatKurus(nt.kod, S.olcu, sec);
  }
  function malzemeKartlari(nt, degisti) {
    var g = el("div", "foto-uretim-malzeme-kartlar");
    g.setAttribute("role", "radiogroup");
    g.setAttribute("aria-label", "Malzeme");
    g.style.display = "flex"; g.style.flexWrap = "wrap"; g.style.gap = "12px";
    S.malzemeFiyatEl = {};
    for (var i = 0; i < F.MALZEMELER.length; i++) {
      (function (m) {
        var secili = seciliMalzeme() === m.kod;
        var b = el("button", "foto-uretim-malzeme-kart");
        b.type = "button";
        b.setAttribute("role", "radio");
        b.setAttribute("aria-checked", secili ? "true" : "false");
        b.setAttribute("data-malzeme", m.kod);
        b.style.flex = "1 1 140px"; b.style.textAlign = "left"; b.style.padding = "12px";
        b.style.borderRadius = "8px"; b.style.cursor = "pointer"; b.style.color = "#12294d";
        b.style.border = secili ? "2px solid #12294d" : "1px solid #c5cbd3";
        b.style.background = secili ? "#eef2f8" : "#fff";
        var satirlar = [el("span", "foto-uretim-malzeme-sicaklik", m.sicaklik), el("strong", null, m.kod),
          el("span", "foto-uretim-malzeme-kullanim", m.kullanim), el("span", "foto-uretim-malzeme-fiyat", "")];
        for (var j = 0; j < satirlar.length; j++) { satirlar[j].style.display = "block"; b.appendChild(satirlar[j]); }
        S.malzemeFiyatEl[m.kod] = satirlar[3];
        b.addEventListener("click", function () { S.malzeme = m.kod; degisti(); });
        g.appendChild(b);
      })(F.MALZEMELER[i]);
    }
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
  // FORM SUNUMU (BaBa 9 Eki 20:38): kaydın `form_sunum`undaki alan ③'te ÇİZİLMEZ; değeri Ölçü sürgüsünden
  // (uzun_kenar_mm = olcu_mm) ya da form varsayılanından (tohum) VERI.formSunumDegeri ile gövdeye girer.
  function sunumAlani(a) {
    var t = litofanKaydi();
    return !!(t && t.form_sunum && Object.prototype.hasOwnProperty.call(t.form_sunum, a));
  }
  function aktifParametreler() {
    var form = formSemasi(), g = {}, aktif = {};
    for (var a in form) {
      if (!Object.prototype.hasOwnProperty.call(form, a)) continue;
      aktif[a] = F.alanAktif(form, a, g);
      var v = sunumAlani(a) ? F.formSunumDegeri(S.tur, a, S.olcu) : S.parametre[a];
      if (aktif[a] && v !== undefined) g[a] = v;
    }
    return { govde: g, aktif: aktif };
  }
  function parametreGovde() {
    return aktifParametreler().govde;
  }
  function kosulGuncelle() {
    renkKosulGuncelle();
    if (!S.alanForm) return;
    var aktif = aktifParametreler().aktif, kaplar = [S.alanForm, S.alanYazi];
    for (var k = 0; k < kaplar.length; k++) {
      var d = kaplar[k] ? kaplar[k].childNodes : [];
      for (var i = 0; i < d.length; i++) {
        var a = d[i].nodeType === 1 ? d[i].getAttribute("data-param") : null;
        if (a) d[i].hidden = aktif[a] === false;
      }
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
    if (S.yaziHata) {
      // ② yazı alanı: değer girilmiş ama şemaya uymuyorsa (ör. satır > 40 karakter) ③'teki ortak hata metni.
      var yd = formDogrula(), yaziDolu = false, fs = formSemasi(), pg = parametreGovde();
      for (var ya in fs) if (fs[ya] && fs[ya].tip === "metin" && pg[ya] !== undefined) yaziDolu = true;
      S.yaziHata.hidden = !(yaziDolu && !yd.ok && yd.hata === "parametre-metin");
      S.yaziHata.textContent = S.yaziHata.hidden ? "" : "Bu alanları kontrol et.";
    }
    if (!S.alanForm || !S.formHata) return;
    var d = formDogrula();
    S.formHata.textContent = d.ok ? "" : (PARAMETRE_HATA[d.hata] || "Bu alanları kontrol et.");
    S.formHata.hidden = d.ok;
  }
  // ③ FORM KURALI (Okan 9 Eki 20:2x, TÜM türler): sayi -> SÜRGÜ (range) + canlı değer ("3 mm"); bool -> aç/kapa
  // DÜĞMESİ (role="switch" + aria-checked); secim -> seçenek listesi; metin kutusu YALNIZ yazı girdisi (metin).
  // Aralık/adım/varsayılan/açıklama form kaydından (TEK kaynak); S.parametre değer tipleri sayı/bool olarak kalır.
  function sayiVarsayilan(sema) {
    var v = sema.varsayilan;
    return typeof v === "number" && isFinite(v) && v >= sema.min && v <= sema.max ? v : sema.min;
  }
  function sayiYazi(v, sema) {
    if (typeof v !== "number" || !isFinite(v)) return "";
    return String(v).replace(".", ",") + (sema.birim ? " " + sema.birim : "");
  }
  function doldurS1Form() {
    if (!S.alanForm) return;
    while (S.alanForm.firstChild) S.alanForm.removeChild(S.alanForm.firstChild);
    if (S.alanYazi) while (S.alanYazi.firstChild) S.alanYazi.removeChild(S.alanYazi.firstChild);
    var form = formSemasi(), alanlar = Object.keys(form).filter(function (a) { return !sunumAlani(a); });
    // ② YAZI (anahtarlık 9 Eki): girdisi "metin" olan türün metin alanları ② ekranında, foto kutusunun
    // altında; kalan alanlar ③'te. ② "İleri" F.girdiYeterli ile bu alanlara bakar.
    var yaziVar = false;
    for (var y = 0; y < alanlar.length; y++) if ((form[alanlar[y]] || {}).tip === "metin") yaziVar = true;
    if (S.alanYazi) S.alanYazi.hidden = !(yaziVar && metinGirdisi());
    S.alanForm.hidden = !alanlar.length;
    if (!alanlar.length) return;
    for (var i = 0; i < alanlar.length; i++) {
      var hedefKap = S.alanYazi && metinGirdisi() && (form[alanlar[i]] || {}).tip === "metin" ? S.alanYazi : S.alanForm;
      var ilkDugum = hedefKap.childNodes.length;
      (function (a, sema) {
        var id = "foto-param-" + a;
        var lbl = el("label", "foto-uretim-form-etiket",
          (sema.etiket || a) + (sema.tip === "sayi" && sema.birim ? " (" + sema.birim + ")" : ""));
        lbl.setAttribute("for", id);
        hedefKap.appendChild(lbl);
        var g, deger = null;
        if (sema.tip === "secim") {
          g = el("select", "foto-uretim-form-secenek-girdi");
          var ss = sema.secenekler || [];
          // Madde 6: değer kodu AYNI kalır, kullanıcıya Türkçe etiket KODDAN TÜRETİLİR (manifest alanı DEĞİL;
          // üreteç/köprü şemasını kirletmeden UI düzeltmesi — kabul R1/R2 YEŞİL kalır).
          var etMap = (typeof KUBAR_ETIKET_MAP === "object" ? KUBAR_ETIKET_MAP[a] : null) || null;
          for (var j = 0; j < ss.length; j++) {
            var k = String(ss[j]);
            var op = el("option", null, etMap && etMap[k] ? etMap[k] : k);
            op.value = k;
            g.appendChild(op);
          }
          if (S.parametre[a] === undefined && ss.length) S.parametre[a] = ss[0];
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
        } else if (sema.tip === "bool") {
          // Aç/kapa düğmesi (checkbox DEĞİL): değer YALNIZ true/false (F.parametreDogrula); varsayılan manifestten.
          g = el("button", "foto-uretim-form-dugme");
          g.type = "button"; g.id = id; g.name = id;
          g.setAttribute("role", "switch");
          g.style.minWidth = "88px"; g.style.padding = "8px 16px"; g.style.borderRadius = "999px"; g.style.cursor = "pointer";
          if (S.parametre[a] !== true && S.parametre[a] !== false) S.parametre[a] = sema.varsayilan === true;
          var dugmeCiz = function () {
            var acik = S.parametre[a] === true;
            g.setAttribute("aria-checked", acik ? "true" : "false");
            g.textContent = acik ? "Açık" : "Kapalı";
            g.style.border = acik ? "2px solid #12294d" : "1px solid #c5cbd3";
            g.style.background = acik ? "#12294d" : "#fff";
            g.style.color = acik ? "#fff" : "#12294d";
          };
          dugmeCiz();
          g.addEventListener("click", function () {
            S.parametre[a] = S.parametre[a] !== true;
            dugmeCiz();
            formHataGoster();
            guncelleS1Buton();
          });
          hedefKap.appendChild(g);
          return;
        } else if (sema.tip === "sayi") {
          g = el("input", "foto-uretim-surgu");
          g.type = "range"; g.min = String(sema.min); g.max = String(sema.max);
          g.step = String(sema.adim > 0 ? sema.adim : 1);
          if (S.parametre[a] === undefined) S.parametre[a] = sayiVarsayilan(sema);
          if (S.parametre[a] !== undefined) g.value = String(S.parametre[a]);
          deger = el("p", "foto-uretim-surgu-deger", sayiYazi(S.parametre[a], sema));
          deger.setAttribute("aria-live", "polite");
        } else if (sema.tip === "metin") {
          // K3c metin dalı: liste=true -> textarea (dizi), değilse -> text input (dize). Doğrulama
          // VERI.parametreDogrula'da (metin/l ~661-670); burada kırpma/kesme YAPMA, yalnız
          // sondaki boş satırları at + boşsa undefined. Varsayılan atama YOK (örnek metni müşterinin
          // siparişine sızmasın).
          if (sema.liste === true) {
            g = el("textarea", "foto-uretim-form-secenek-girdi");
            g.rows = sema.satir_max;
            g.placeholder = (sema.ornek || []).join("\n");
            if (Array.isArray(S.parametre[a])) g.value = S.parametre[a].join("\n");
            g.id = id; g.name = id;
            g.addEventListener("input", function (e) {
              var satirlar = e.target.value.split("\n");
              while (satirlar.length > 0 && satirlar[satirlar.length - 1] === "") satirlar.pop();
              S.parametre[a] = satirlar.length === 0 ? undefined : satirlar;
              formHataGoster();
              guncelleS1Buton();
            });
            g.addEventListener("change", function (e) {
              var satirlar = e.target.value.split("\n");
              while (satirlar.length > 0 && satirlar[satirlar.length - 1] === "") satirlar.pop();
              S.parametre[a] = satirlar.length === 0 ? undefined : satirlar;
              formHataGoster();
              guncelleS1Buton();
            });
            hedefKap.appendChild(g);
            return;
          }
          g = el("input", "foto-uretim-form-secenek-girdi");
          g.type = "text";
          g.maxLength = sema.max;
          if (typeof S.parametre[a] === "string") g.value = S.parametre[a];
          g.id = id; g.name = id;
          g.addEventListener("input", function (e) {
            var v = e.target.value;
            S.parametre[a] = v === "" ? undefined : v;
            formHataGoster();
            guncelleS1Buton();
          });
          g.addEventListener("change", function (e) {
            var v = e.target.value;
            S.parametre[a] = v === "" ? undefined : v;
            formHataGoster();
            guncelleS1Buton();
          });
          hedefKap.appendChild(g);
          return;
        }
        if (!g) return;
        g.id = id; g.name = id;
        var degis = function (e) {
          var v = e.target.value;
          if (sema.tip === "sayi") {
            S.parametre[a] = v === "" ? undefined : Number(v);
            if (deger) deger.textContent = sayiYazi(S.parametre[a], sema);
          } else if (sema.tip === "secim") {
            var ss2 = sema.secenekler || [], bul;
            for (var k = 0; k < ss2.length; k++) { if (String(ss2[k]) === v) { bul = ss2[k]; break; } }
            S.parametre[a] = bul;
          } else S.parametre[a] = v === "" ? undefined : v;
          formHataGoster();
          guncelleS1Buton();
        };
        g.addEventListener("input", degis);
        g.addEventListener("change", degis);
        hedefKap.appendChild(g);
        if (deger) hedefKap.appendChild(deger);
      })(alanlar[i], form[alanlar[i]] || {});
      // Alan açıklaması (form kaydının `aciklama`sı) girdinin ALTINDA; açıklaması olmayan alana metin UYDURULMAZ.
      var acik_ = (form[alanlar[i]] || {}).aciklama;
      if (typeof acik_ === "string" && acik_) hedefKap.appendChild(el("p", "foto-uretim-ayrinti", acik_));
      // Alanın tüm düğümleri (etiket + girdi) `data-param` taşır: kosulGuncelle onları birlikte gizler.
      for (var dn = ilkDugum; dn < hedefKap.childNodes.length; dn++) {
        if (hedefKap.childNodes[dn].nodeType === 1) hedefKap.childNodes[dn].setAttribute("data-param", alanlar[i]);
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
    // Fotoğraf almayan türde (bugün yalnız yazılı anahtarlık) kutu ÇİZİLMEZ: ölü "Foto ekle" gösterilmez.
    S.yukleKutu.hidden = !fotoGerekir();
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
    fotoRenkCikar(S.dosya || null);
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
      // Madde 4: orneği olmayan kart YAKINDA kartı olarak görünür ama DEVRE DIŞI (tıklanamaz).
      // Anahtarlık örneği 9 Eki'de eklendi; yakında kolu artık örneği olmayan YENİ tür içindir.
      if (!o) { if (k.yakinda) liste.push({ kart: k, tur: t, ornek: null, kanit: "yakinda" }); continue; }
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
        // Madde 4: "Yakında" kartı (orneği olmayan) DEVRE DIŞI — tıklanamaz, aria-disabled=true.
        var devreDisi = it.kanit === "yakinda";
        if (devreDisi) {
          d.disabled = true;
          d.setAttribute("aria-disabled", "true");
        }
        var im = el("img");
        im.src = it.kanit === "render" ? it.ornek.render
          : it.kanit === "yakinda" ? "" : it.ornek.baski;
        im.alt = ""; im.width = 240; im.height = 240; im.decoding = "async";
        if (sira > 0) im.loading = "lazy";
        d.appendChild(im);
        d.appendChild(el("span", "foto-uretim-kart-ad",
          devreDisi ? (it.kart.yakinda || it.kart.ad) : it.kart.ad));
        d.appendChild(el("span", "foto-uretim-kart-etiket",
          devreDisi ? "yakında" : (it.kanit === "render" ? "önizleme/render" : "basılmış ürün")));
        if (!devreDisi) d.addEventListener("click", function () { galeriSec(it.kart.kod); });
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
  // Madde 6: ham değer kodu AYNI kalır (köprü manifest şemasını kirletmemek için), kullanıcıya UI'da
  // gösterilecek Türkçe etiket bu sabitten türetilir (tekilko kutucuk KUBAR_ETIKET_MAP).
  var KUBAR_ETIKET_MAP = {
    kabartma_yon: { "acik_yuksek": "Açık tonlar yüksek", "koyu_yuksek": "Koyu tonlar yüksek" }
  };
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
    // ② YAZI (anahtarlık 9 Eki): metin girdili türün yazı alanı foto kutusuyla AYNI ekranda (doldurS1Form doldurur).
    S.alanYazi = el("div", "foto-uretim-form-grup");
    S.alanYazi.id = "foto-yazi";
    S.alanYazi.hidden = true;
    p2.appendChild(S.alanYazi);
    S.yaziHata = el("p", "foto-uretim-ayrinti");
    S.yaziHata.hidden = true;
    p2.appendChild(S.yaziHata);
    doldurS1Dosya();
    // K2b: UYUM KAPISI paneli — dosya/not girdilerinden sonra (arka planda; yalnız soru/RED'de görünür).
    // uyumSonuc: null | "uygun" | "uygun_degil". uygun_degil'de ret cümlesi.
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

  // ③ renk + malzeme (Okan 9 Eki): renk seçici (3 ana renk / Renkli) + PLA/PETG kartları — TÜM türlerde aynı.
  // Bölge türünde seçim secimiEsle ile bölgelere yazılır (sunucu `<bolge>_renk` / `<bolge>_malzeme` ister).
  function doldurS1Secim() {
    if (!S.alanSecim || !S.alanMalzeme) return;
    while (S.alanSecim.firstChild) S.alanSecim.removeChild(S.alanSecim.firstChild);
    while (S.alanMalzeme.firstChild) S.alanMalzeme.removeChild(S.alanMalzeme.firstChild);
    var t = F.turBul(S.tur);
    if (!t) return;
    if (!S.secim) S.secim = varsayilanSecim(S.tur);
    var degisti = function () { doldurS1Secim(); guncelleS1Buton(); };
    S.alanSecim.appendChild(renkSecici(t, degisti));
    S.renkler = paletRenkleri(t.kod);
    secimiEsle(t);
    S.alanMalzeme.hidden = false;
    S.alanMalzeme.appendChild(el("span", "foto-uretim-form-etiket", "Malzeme"));
    S.alanMalzeme.appendChild(malzemeKartlari(t, degisti));
    var malzemeAcik = alanAciklamasi(t.kod, "malzeme");
    if (malzemeAcik) S.alanMalzeme.appendChild(el("p", "foto-uretim-ayrinti", malzemeAcik));
    renkKosulGuncelle();
    canliFiyatGuncelle();
  }

  // ③ CANLI FİYAT — TEK formül (F.fiyatKurus; sunucunun ödemede kullandığı AYNI fonksiyon), renkli + malzemeyle;
  // malzeme kartlarının fiyatı da buradan (ölçü değişince kartlar da güncellenir).
  function canliFiyatGuncelle() {
    if (!S.alanCanliFiyat) return;
    var nt = seciliTurBul();
    var kurus = nt && !F.olcuTuretilmis(nt.kod) ? F.fiyatKurus(nt.kod, S.olcu, fiyatSecimi()) : null;
    S.alanCanliFiyat.textContent = kurus != null ? "Fiyat: " + F.tlMetni(kurus) : "";
    var t = F.turBul(S.tur);
    for (var m in (S.malzemeFiyatEl || {})) {
      if (!Object.prototype.hasOwnProperty.call(S.malzemeFiyatEl, m)) continue;
      var k = t ? malzemeKartFiyati(t, m) : null;
      S.malzemeFiyatEl[m].textContent = k != null ? F.tlMetni(k) : "";
    }
  }

  /* ============== ④ S1 — ÖNİZLEME İSTEĞİ ==============
     Aydınlatma tiki (tek) + doğrulama → "Önizleme oluştur" (parça kapısı ÖNCE koşar). D/R türünde örnek
     render + ONIZLEME_SONRA. */
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

    S.alanNotu = el("p", "foto-uretim-ayrinti", "");
    S.alanNotu.id = "foto-onizle-hak";
    S.alan.appendChild(S.alanNotu);

    S.alanButon = el("div", "foto-uretim-s1-buton-sira");
    var btn = el("button", "foto-uretim-buton-birincil", "Önizleme oluştur");
    btn.type = "button";
    btn.id = "foto-onizle-buton";
    btn.disabled = true;
    btn.addEventListener("click", onizleOlustur);
    S.alanButon.appendChild(btn);
    // ① Düğme KAPALIYKEN altında TEK cümle: ilk eksik koşul (s1Sebep); hepsi tamken GİZLİ.
    S.alanSebep = el("p", "foto-uretim-ayrinti", "");
    S.alanSebep.id = "foto-onizle-sebep";
    S.alanSebep.hidden = true;
    S.alanButon.appendChild(S.alanSebep);
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
    kap.appendChild(el("p", "foto-uretim-ayrinti",
      alanAciklamasi(nt.kod, "olcu") || "Ölçü, ürünün en uzun boyutudur (en, boy ya da yükseklik)."));
    return kap;
  }

  function doldurS1Dosya() {
    while (S.alanDosya.firstChild) S.alanDosya.removeChild(S.alanDosya.firstChild);
    S.dosya = null;
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
    var lbl = el("label", "foto-uretim-form-etiket", "Nasıl olsun?");
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
    // Okan 10 Eki 01:3x: büstte not İSTEĞE BAĞLI (ArTisT cümlesi, icerik/foto-ozel-uretim-sayfa-metni.md);
    // diğer türlerde zorunluluk cümlesi AYNEN.
    kap.appendChild(el("p", "foto-uretim-ayrinti", notIstegeBagli(S.tur) ?
      "İsteğe bağlı: kısa bir not ekleyebilirsin." : "Üretim notu zorunlu; boşsa önizleme oluşturulamaz."));
    S.alanDosya.appendChild(kap);
    notAlaniGoster();
  }

  /* ============== UYUM PANELİ ==============
     "Nasıl olsun?" notu (S.uretimNotu) değiştikçe yeniden çizilir.
     - "uygun": panel boş (form görünür, önizleme açılır).
     - "uygun_degil": A metni (birebir) + ① ızgarasına dönen düğme; önizleme düğmesi pasif. */
  function cizUyum() {
    if (!S.alanUyum) return;
    while (S.alanUyum.firstChild) S.alanUyum.removeChild(S.alanUyum.firstChild);
    if (!S.tur) return;
    var sonuc = uyumKontrol(S.tur, S.uretimNotu);
    S.uyumSonuc = sonuc;
    if (sonuc === "uygun") return;  // görünmez — önizleme düğmesi açılır
    // "uygun_degil" — A ekranı: metin (birebir) + ① ızgarasına dönen düğme
    var baslik = el("h3", "foto-uretim-uyum-baslik", "Parça / yedek parça isteği");
    S.alanUyum.appendChild(baslik);
    var p = el("p", "foto-uretim-uyum-metin", A_METIN_BIREBIR);
    S.alanUyum.appendChild(p);
    var donBtn = el("button", "foto-uretim-buton-birincil", "Tasarım ürünlerine dön");
    donBtn.type = "button";
    donBtn.id = "foto-uyum-don";
    donBtn.addEventListener("click", function () {
      S.uyumSonuc = null;
      adimKoy("secim");
    });
    S.alanUyum.appendChild(donBtn);
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
    // Madde 7: gizlilik cümlesi YALNIZ aydinlatma maddesi olarak TEK kez görünür (VERI.onay.aydinlatma).
    S.alanOnay.appendChild(det);

    // TEK ONAY KUTUSU (metin sürümü taslak-2): metnin ALTINDA; hak beyanı ve aktarım rızası
    // cümleleri metnin içinde. İşaretlenmeden önizleme ve sipariş düğmeleri açılmaz.
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

  // ① "Önizleme oluştur" kapalıyken gösterilen sebep — SIRA sabit: ilk eksik koşul yazılır, diğerleri yazılmaz.
  var S1_SEBEP = {
    not: "Önce \"Nasıl olsun?\" kısmına kısa bir not yaz.",
    foto: "Önce fotoğrafını yükle.",
    onay: "Aydınlatma metnini okuyup onay kutusunu işaretle.",
    dogrulama: "Güvenlik doğrulaması bekleniyor.",
    hak: "Bugünkü önizleme hakkın doldu; yarın yenilenir.",
    program: "Önizleme şu an kapalı; biraz sonra yeniden dene."
  };
  // Okan 10 Eki 01:3x "büstte not zorunlu olmasın": bu türlerde boş not düğmeyi KAPATMAZ, sebep listesinde "not" YOK.
  var NOT_ISTEGE_BAGLI_TURLER = ["bust"];
  function notIstegeBagli(kod) { return NOT_ISTEGE_BAGLI_TURLER.indexOf(kod) >= 0; }
  function s1Sebep() {
    var sira = [
      [!notIstegeBagli(S.tur) && !((S.uretimNotu || "").trim()), S1_SEBEP.not],
      [fotoGerekir() && !S.dosya, S1_SEBEP.foto],
      [!S.aydinlatmaOnay, S1_SEBEP.onay],
      [!S.captchaToken1, S1_SEBEP.dogrulama],
      [S.kalanHak === 0, S1_SEBEP.hak],
      [!!S.programKapali, S1_SEBEP.program]
    ];
    for (var i = 0; i < sira.length; i++) { if (sira[i][0]) return sira[i][1]; }
    return "";
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
    // K2b: uyum kontrolü geçmeden önizleme düğmesi AÇILMAZ ("uygun_degil" ise).
    var uyumOK = uyumKontrol(S.tur, S.uretimNotu) === "uygun";
    // Madde 1 (Okan 8 Eki 14:1x): "Nasıl olsun?" üretim notu ZORUNLU; boşken "Önizleme oluştur" KAPALI.
    // ① not · fotoğraf · onay · doğrulama · günlük hak · program — s1Sebep TEK kaynak (cümle ile kapı aynı).
    var sebep = s1Sebep();
    var tam = uyumOK && !sebep && !!S.tur && !!S.olcu && (!lit || !!null) &&
      formDogrula().ok;
    btn.disabled = !tam;
    if (S.alanSebep) {
      S.alanSebep.textContent = tam ? "" : sebep;
      S.alanSebep.hidden = tam || !sebep;
    }
    // "Bugün N/<sınır>": N yalnız sunucu yanıtından; bilinmiyorsa günlük sınır cümlesi (sayı uydurulmaz).
    if (S.alanNotu) {
      S.alanNotu.textContent = typeof S.kalanHak === "number" ?
        "Bugün " + S.kalanHak + "/" + F.sinir_ziyaretci_24s + " önizleme hakkın kaldı." :
        "Günde en çok " + F.sinir_ziyaretci_24s + " önizleme hakkın var.";
    }
    btn.textContent = lit ? "Siparişe geç" : "Önizleme oluştur";
  }

  /* ============== S2 ============== */
  /* Türetilmiş eksen fiyat satırı: fiyat yalnız durum yanıtından (S.fiyatKurus); yeni önizleme isteğinde
     sıfırlanır, o yüzden önizleme beklenirken eski fiyat GÖSTERİLMEZ ("hesaplanıyor" yazar). */
  function olculenFiyatEl(bekliyor) {
    return el("p", "foto-uretim-surgu-fiyat foto-uretim-olculen-fiyat", S.fiyatKurus != null
      ? S.olcu + " mm → " + F.tlMetni(F.secimliKurus(S.fiyatKurus, fiyatSecimi()))
      : bekliyor ? "Fiyat hesaplanıyor — önizlemede ölçülen en uzun boyuttan."
      : "Fiyat hesaplanamadı; yeni önizleme oluştur.");
  }

  function cizS2() {
    if (!S.alan) return;
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
      "Önizleme — ürün bunun seçtiğin renk sayısında olur; tam kopyası değildir."));
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
    // Birim fiyat TEK formülden (sunucunun ödemede kullandığı AYNI F.fiyatKurus), renkli + malzeme çarpanıyla.
    var rs = renkSayisi(nt);
    var fiyat = nt ? (F.olcuTuretilmis(nt.kod) ? (S.fiyatKurus != null ? F.secimliKurus(S.fiyatKurus, fiyatSecimi()) : null)
      : F.fiyatKurus(nt.kod, S.olcu, fiyatSecimi())) : null;
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
     checkout'ta (karma sepet tek ödeme). Kalem {foto_is, tur, olcu_mm, renkler[], renk_sayisi, renkli, malzeme,
     onizleme_ref, atif};
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
      renkli: k.renkli, malzeme: k.malzeme,
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
        if (typeof kayit.renk_secim === "string") S.renkSecim = kayit.renk_secim;
        if (F.malzemeBul(kayit.malzeme)) S.malzeme = kayit.malzeme;
        // Renkli önizleme yeniden yüklemede fotoğrafsız döner: fotoğraftan çıkmış renkler kayıttan gelir.
        if (kayit.renk_secim === RENKLI && Array.isArray(kayit.renkler)) {
          S.fotoRenkleri = kayit.renkler.filter(function (x) { return F.PLA_RENKLERI.indexOf(x) >= 0; }).slice(0, 4);
        }
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
  /* ① Kalan hak + program durumu YALNIZ sunucu yanıtından: 200 `kalan` · 429 onizleme-siniri -> 0 · 503 kapali. */
  function hakYanitiIsle(kod, veri) {
    if (!veri) return;
    if (kod === 200 && typeof veri.kalan === "number") S.kalanHak = veri.kalan;
    else if (kod === 429 && veri.hata === "onizleme-siniri") S.kalanHak = 0;
    else if (kod === 503 && veri.hata === "kapali") S.programKapali = true;
  }

  function onizleOlustur() {
    
    if (!!(F && F.kolu && F.kolu(S.tur) === "deterministik")) { uretecOnizle(); return; }
    // K2b: UYUM KAPISI — kredi harcayan 3D önizleme isteğinden ÖNCE koşar. "uygun_degil"
    // ise 2D önizleme = 0 istek (cizUyum A ekranını veya soruyu zaten gösterdi). Burada yalnız UI tutarlılığı.
    var uyum = uyumKontrol(S.tur, S.uretimNotu);
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
    adimKoy("S2", "Fotoğrafın yükleniyor…", false);
    kucultGorsel(S.dosya, function (err, dataUrl) {
      if (err || !dataUrl) {
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
      govde.gorsel = dataUrl;
      notGovdeyeKoy(govde);
      if (Object.keys(formSemasi()).length) govde.parametreler = parametreGovde();
      jsonPost(ONIZLEME_URL, govde, function (ok, kod, veri) {
        turnsSifirla(S.alanCap1);
        hakYanitiIsle(kod, veri);
        // 429/503 gövdeli yanıt aşağıdaki dallara iner (eski `!ok` kapısı onizleme-siniri dalını ölü bırakıyordu).
        if (!veri) {
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
    var uyum = uyumKontrol(S.tur, S.uretimNotu);
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
        hakYanitiIsle(kod, veri);
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