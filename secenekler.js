/* PRUVO — Malzeme/Renk/Boy seçenekleri + fiyat hesaplama + sepet veri modeli.
   index.html VE tools/build.py'nin ürettiği urun/<id>/index.html sayfaları bu dosyayı
   ORTAK kullanır (tek kaynak — ikisine ayrı ayrı kopyalanmaz, drift riski kalmaz).
   shop/ Worker'ı da BU dosyayı import eder (shop/src/index.js): ödeme tutarı sunucuda
   aynı katsayı/renk/sıra kuralıyla hesaplanır — katsayı tablosunun ikinci kopyası YOKTUR.
   Kategori listesi değişirse tools/build.py'deki FONKSIYONEL_KATEGORILER ile BİRLİKTE
   güncelle (build.py hangi ürün sayfasına seçici HTML'i basacağını bu listeyle karar verir).

   PARA KURALI (Okan, 16 Tem): YUVARLAMA YOK — küsurat aynen korunur, kuruşuyla tahsil edilir
   (333 × 1.30 = 432,90 TL). Para tamsayı KURUŞTA taşınır; TL'de çarpım yapılsa kayan nokta
   432.90000000000003 üretir ve istemci ile Worker'ın tutarı sessizce ayrışır. */
(function (root) {
  "use strict";

  // PLA taban (fark yok); yüzdeler PLA fiyatına göre ek maliyet.
  // ABS ve Karbon katkılı KALDIRILDI (Okan, 16 Tem) — mühendislik malzemeleri WhatsApp'tan.
  var FILAMENT_FARK = { "PLA": 0, "PETG": 30, "ASA": 60, "TPU": 55 };
  var FILAMENT_SIRA = ["PLA", "PETG", "ASA", "TPU"];
  var RENK_SECENEKLERI = ["Siyah", "Beyaz", "Gri", "Diğer"];
  var RENK_DIGER_YUZDE = 15;
  var FONKSIYONEL_KATEGORILER = ["Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin", "Bisiklet", "Bahçe", "Ofis", "Kamera"];

  /* Liste fiyatı metninden TL sayısı. tools/build.py feed_price ve Worker ile AYNI kural:
     İLK sayı grubunu alır ("1.250 TL" -> 1250, "300 TL (30 cm)" -> 300).
     DİKKAT: eski kural tüm rakamları birleştiriyordu (replace(/[^0-9]/g,"")), o yüzden
     "300 TL (30 cm)" 30030 TL görünüyordu — istemci 30.030 TL gösterip Worker 300 TL tahsil
     ederdi. Kural üç yerde (burada, feed_price, Worker) birebir aynı olmalı. */
  function fiyatSayisi(fiyat) {
    if (!fiyat) { return null; }
    var s = String(fiyat);
    var m = /([0-9][0-9.]*)\s*(?:TL|TRY|₺)/i.exec(s) || /([0-9][0-9.]*)/.exec(s);
    if (!m) { return null; }
    var n = parseInt(m[1].replace(/\./g, ""), 10);
    return (n > 0) ? n : null;
  }

  function fonksiyonelMi(kategori) {
    return FONKSIYONEL_KATEGORILER.indexOf(kategori) !== -1;
  }

  function boyFarki(urun, boyEtiket) {
    var secenekler = (urun && urun.boy_secenekleri) || [];
    if (!boyEtiket) { return 0; }
    for (var i = 0; i < secenekler.length; i++) {
      if (secenekler[i].etiket === boyEtiket) { return secenekler[i].fark_tl || 0; }
    }
    return 0;
  }

  var ADET_EN_AZ = 1;
  var ADET_EN_COK = 99;

  /* KARGO (Okan, 16 Tem — KESİN, değişiklik SADECE Okan'dan; tools/paket-shop-kargo.md):
     ürün toplamı < 2.500,00 TL -> 250,00 TL gönderim; >= 2.500,00 TL (tam 2.500 DAHİL) ->
     bedava. Eşik ÜRÜN toplamına bakar (kargo hariç); kargo ayrı kalemdir, ürün fiyatına
     yedirilmez. Sepet paneli, WhatsApp metni ve shop Worker'ı (/api/shop/baslat) AYNI
     fonksiyonu okur — asıl hesap sunucuda, istemciden gelen kargo/tutar alanları okunmaz. */
  var KARGO_UCRET_KURUS = 25000;
  var KARGO_BEDAVA_ESIK_KURUS = 250000;
  function kargoKurus(urunToplamKurus) {
    if (!(urunToplamKurus > 0)) { return 0; }
    return urunToplamKurus >= KARGO_BEDAVA_ESIK_KURUS ? 0 : KARGO_UCRET_KURUS;
  }

  /* KDV (Okan KESİN %20, 16 Tem gece — değişiklik SADECE Okan'dan; paket kalem 8):
     fiyatlar KDV DAHİL, tahsilat DEĞİŞMEZ — bu yalnız döküm + kayıt. net = brüt/(1+oran)
     kuruşta; yuvarlama farkı toplamı BOZAMAZ: KDV = brüt − net (fark KDV'ye yedirilir,
     net + KDV = brüt birebir). Döküm KARGO DAHİL genel toplam üzerinden tek sefer yapılır.
     Sepet paneli, havale ekranı ve Worker (D1 kdv_kurus kaydı) AYNI fonksiyonu okur. */
  var KDV_YUZDE = 20;
  function kdvAyristir(brutKurus) {
    if (!(brutKurus > 0)) { return { netKurus: 0, kdvKurus: 0 }; }
    var net = Math.round(brutKurus * 100 / (100 + KDV_YUZDE));
    return { netKurus: net, kdvKurus: brutKurus - net };
  }

  /* Parametrik (sarı seri) ürünlerde SELF-SERVİS ÖDEME anahtarı — TEK yerde, front + Worker
     aynı sabiti okur. AÇIK (Okan kararı + mimar, 17 Tem 2026). Ön koşullar sağlandı:
     taban fiyatlar 18/18 dolu (vida dahil, 100 TL), şema kapısı üretilemez ölçüyü
     reddediyor (gecerliDegerler/kisitlar), Worker fiyatı şema+hacim.js ile SUNUCUDA
     yeniden hesaplıyor (shop/src/parametrik.js; istemcinin hacim/fiyat alanları OKUNMAZ).
     Kabul testi #5 "parametrik kanal": şemalı KABUL, şemasız/fiyatsız RED (WhatsApp'a).
     KAPATMAK gerekirse: burası false + Worker yeniden deploy (bundle'a gömülü) —
     tek başına front push'u Worker'ı DEĞİŞTİRMEZ. */
  var PARAMETRIK_ODEME_ACIK = true;

  /* SELF-SERVİS KARTLA ÖDEME anahtarı (sitedeki "Kartla Güvenli Öde" butonu).
     Bugün KAPALI — sebebi teknik değil, TİCARİ: elimizde yalnız iyzico SANDBOX anahtarı var
     (canlı başvuru sürüyor). Buton canlı sitede açık olsaydı müşteri GERÇEK kartını SANDBOX
     sayfasına girerdi: para hareket etmez ama sandbox `retrieve` "başarılı" döner, sipariş
     'odendi' yazılır ve Okan parayı almadan üretip kargolar. Sepet + WhatsApp kanalı normal
     çalışmaya devam eder (bugünkü davranışın aynısı).
     AÇMAK İÇİN (sırayla): 1) Okan'ın CANLI iyzico anahtarları gelir, 2) wrangler.toml
     IYZICO_BASE_URL -> https://api.iyzipay.com + `wrangler secret put` ile canlı anahtarlar,
     3) `node shop/test/kabul.js --sandbox` uçtan uca YEŞİL (kart girişi elle), 4) burası true,
     5) düşük tutarlı gerçek kart duman testi + iade.
     Worker BU anahtardan bağımsız çalışır (uç açık kalır; curl ile doğrulanabilir) — kapali
     olan yalnızca müşteriye gösterilen buton. */
  var ODEME_ACIK = true; /* CANLI (Okan karari + canli anahtarlar, 17 Tem aksam) */

  /* SARI SERI 3D ONIZLEME (tools/paket-onizleme-3d.md, Faz C pilot).
     ONIZLEME_AILELER: /api/onizleme/olustur ucunun kabul ettigi aile beyaz listesi —
     onizleme Worker'i (onizleme/src/index.js) ve build.py (urun sayfasina "Onizle (3D)"
     butonunu basma karari) AYNI listeyi buradan okur, ikinci kopya YOK.
     ONIZLEME_3D_ACIK: butonun musteride gorunmesi. KAPALI tutulur; derleme arka ucu
     (Cloudflare Container, Workers Paid bekliyor) deploy edilip kabul 4e/4g yesillenince
     MIMAR karariyla acilir. Kapaliyken bu degisiklik canlida SIFIR gorunur fark yaratir. */
  var ONIZLEME_3D_ACIK = true;
  /* Faz E (Okan karari 16 Tem: onizleme TUM sari ailelerde): 13 uyelik-motoru
     ailesinin eslem/hacim duzeltme turu sonrasi <=%3 olcum kapisini gecen 12 aile
     listeye alindi (aile basina 25 set olcumler: onizleme/test/eslem-olcum.py).
     VIDA yok: fiyat formulu capa duyarsiz, ayri paket (tools/paket-vida-fiyat.md)
     merge olunca olculup eklenecek. Bazi ailelerde motorda karsiligi olmayan
     secenekler ONIZLEME_KISITLAR ile onizleme disi (fiyat/siparis etkilenmez).
     DIKKAT — yayin kapisi: bu listeye aile eklemek = butonun o urun sayfalarinda
     MUSTERIYE gorunmesi; main'e merge MIMAR kabulu ister. */
  /* Yeni sari aileler 1. dalga (2026-07-17, tools/paket-yeni-aileler-1.md):
     adaptor/kutu/kavanoz bizim ureteclerimiz (pruvo-jenerator), 4d olcumu
     ile eklendi — yayin yine merge kapisindan gecer. */
  var ONIZLEME_AILELER = ["olcuye-ozel-profil-beam", "olcuye-ozel-oring-conta",
    "olcuye-ozel-baglanti-konektor", "olcuye-ozel-montaj-braketi",
    "ozel-disli-kramayer-uretimi",
    "olcuye-ozel-yay-dalga-flexure", "kisiye-ozel-jeton-cip-madalyon",
    "olcuye-ozel-ramp-sim-takoz", "olcuye-ozel-cetvel", "olcuye-ozel-huni",
    "olcuye-ozel-damga-kase", "olcuye-ozel-rulman", "olcuye-ozel-triger-kasnagi",
    "olcuye-ozel-triger-kayisi", "olcuye-ozel-petek-delikli-panel",
    "olcuye-ozel-pervane-fan-cark", "olcuye-ozel-izgara-menfez-kapak",
    "olcuye-ozel-hortum-adaptoru", "olcuye-ozel-kutu-organizer",
    "olcuye-ozel-vidali-kavanoz-tapa"];

  /* Onizleme secenek kisitlari: uretim motorunda 3D karsiligi olmayan secim
     degerleri (mimar tablosunda; siparis/fiyat AKISINA DOKUNMAZ, yalniz 3D
     onizleme bu degerlerle sunulamaz). Worker sema kapisinda reddeder
     (onizleme-secenek-kisiti), urun sayfasi ayni listeyle onceden uyarir. */
  var ONIZLEME_KISITLAR = {
    "olcuye-ozel-cetvel": { tip: ["duz"] },
    "olcuye-ozel-damga-kase": { sap: ["sapsiz"], bicim: ["dikdortgen"] },
    "olcuye-ozel-petek-delikli-panel": { mod: ["delikli"] }
  };

  /* Birim fiyat, tamsayı KURUŞ. Sıra (Okan, 16 Tem): filament katsayısı -> SONRA "Diğer"
     renk +%15 -> sonra boy farkı (TL, sabit ek). Yuvarlama YOK; tek yuvarlama kuruşun ALTINA
     inen artık içindir (yarım kuruş tahsil edilemez; ör. "Diğer" renkte 333 -> 497,835 TL). */
  function hesaplaFiyatKurus(temelFiyatTL, malzeme, renk, boyFarkTL) {
    if (temelFiyatTL == null) { return null; }
    var yuzde = FILAMENT_FARK.hasOwnProperty(malzeme) ? FILAMENT_FARK[malzeme] : 0;
    var renkCarpan = (renk === "Diğer") ? (100 + RENK_DIGER_YUZDE) : 100;
    // Bölmeler en sona: 333*100*130*115 = 497835000 (tamsayı, güvenli) -> /10000 -> 49783.5
    var kurus = Math.round(temelFiyatTL * 100 * (100 + yuzde) * renkCarpan / 10000);
    return kurus + Math.round((boyFarkTL || 0) * 100);
  }

  function adetDuzelt(a) {
    var n = parseInt(a, 10);
    if (!(n >= ADET_EN_AZ)) { return ADET_EN_AZ; }
    return n > ADET_EN_COK ? ADET_EN_COK : n;
  }

  // ---- parametrik ("ölçüye özel") fiyat ----
  // Okan kuralı (16 Tem, tools/paket-sari-fiyat.md):
  //   fiyat = tabanFiyat × max(1, hacim/tabanHacim) × filamentKatsayı × renkFaktör.
  // Taban fiyat ZEMİNDİR — varsayılandan küçük ölçüde çarpan 1'e sabitlenir, altına
  // İNİLMEZ; taban üstünde hacimle SÜREKLİ oran (basamak yok: eşik uçurumu güven kırar
  // + eşik-altı oynamaya iter). Kuruş cinsinden tutulur; yuvarlama YALNIZ kuruş
  // basamağında (float artığı temizliği), TL'ye yuvarlama yok — kusurat kuruşuyla
  // gösterilir/tahsil edilir.
  function parametrikFiyatKurus(tabanFiyatTL, tabanHacimMm3, hacimMm3, malzeme, renk) {
    if (tabanFiyatTL == null || !tabanHacimMm3 || !hacimMm3) { return null; }
    var yuzde = FILAMENT_FARK.hasOwnProperty(malzeme) ? FILAMENT_FARK[malzeme] : 0;
    var kurus = tabanFiyatTL * 100 * Math.max(1, hacimMm3 / tabanHacimMm3) * (1 + yuzde / 100);
    if (renk === "Diğer") { kurus = kurus * (1 + RENK_DIGER_YUZDE / 100); }
    return Math.round(kurus);
  }

  /* Kuruşu ekran metnine çevirir: 43290 -> "432,90 TL", 129870 -> "1.298,70 TL".
     TEK formatter (site + konfigüratör + sepet): spec gereği DAİMA 2 ondalık ve virgüllü —
     tam TL'de de "300,00 TL" yazar. Küsurat korunuyorsa gösterimi de tutarlı olmalı; ayrıca
     iki ayrı formatter tutmak (biri ondalık düşüren) fiyatın yerine göre farklı görünmesine
     yol açardı. iyzico'ya giden NOKTALI metin ayrı (shop/src/index.js kurusMetin). */
  function kurusMetni(kurus) {
    if (kurus == null) { return null; }
    return (kurus / 100).toLocaleString("tr-TR",
      { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " TL";
  }

  function tlMetni(tutarTL) {
    if (tutarTL == null) { return null; }
    return kurusMetni(Math.round(tutarTL * 100));
  }

  // ---- sepet satırı ----
  function bosSatir(id) {
    return { id: id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", boy_etiket: null, adet: 1 };
  }

  /* Aynı konfigürasyonun tek satırda toplanması için anahtar. ADET BİLEREK DIŞARIDA:
     aynı ürün+malzeme+renk+boy ikinci kez eklenince yeni satır değil, adet artmalı. */
  function satirAnahtari(satir) {
    return [satir.id, satir.malzeme, satir.renk, satir.renk_ozel || "", satir.boy_etiket || "",
            satir.parametreler ? JSON.stringify(satir.parametreler) : ""].join("|");
  }

  // Sepet/WhatsApp mesajında ürün+seçim satırının metnini ve hesaplanan fiyatını üretir.
  // fonksiyonel OLMAYAN kategorilerde (Dekorasyon, Oyun/Hobi...) seçici hiç gösterilmediği
  // için detay boş döner — mevcut (öncesi) davranış korunur, mesaj kirlenmez.
  function satirOzeti(urun, satir) {
    if (satir && satir.parametreler) { return parametrikSatirOzeti(satir); }
    var fonksiyonel = fonksiyonelMi(urun && urun.kategori);
    var parcalar = [];
    if (fonksiyonel) {
      // Kart-secim urununde malzeme secilmeden WhatsApp'tan sorulabilir -> bos malzeme satiri yazma.
      if (satir.malzeme) {
        var mYuzde = FILAMENT_FARK.hasOwnProperty(satir.malzeme) ? FILAMENT_FARK[satir.malzeme] : 0;
        parcalar.push("Malzeme: " + satir.malzeme + (mYuzde ? " (+%" + mYuzde + ")" : ""));
      }
      if (satir.renk === "Diğer") {
        parcalar.push("Renk: " + (satir.renk_ozel || "özel renk") + " (özel, +%" + RENK_DIGER_YUZDE + ")");
      } else if (satir.renk) {
        parcalar.push("Renk: " + satir.renk);
      }
      if (satir.boy_etiket) { parcalar.push("Boy: " + satir.boy_etiket); }
    }
    var adet = adetDuzelt(satir.adet);
    if (fonksiyonel && adet > 1) { parcalar.push("Adet: " + adet); }
    var temel = fiyatSayisi(urun && urun.fiyat);
    var bf = fonksiyonel ? boyFarki(urun, satir.boy_etiket) : 0;
    // Fonksiyonel olmayan kategoride (Dekorasyon, Oyun/Hobi) seçici yok -> liste fiyatı aynen.
    var birim = fonksiyonel
      ? hesaplaFiyatKurus(temel, satir.malzeme, satir.renk, bf)
      : (temel == null ? null : temel * 100);
    // Satır tutarı = kuruşlu birim × adet (ara yuvarlama yok: 432,90 × 3 = 1.298,70)
    var hesap = (birim == null) ? null : birim * adet;
    var fiyatMetni;
    if (hesap != null) { fiyatMetni = kurusMetni(hesap); }
    else if (urun && urun.parametrik) { fiyatMetni = "Ölçüye özel fiyat — teklif için sipariş verin"; }
    else { fiyatMetni = "Fiyat için sipariş verin"; }
    return {
      detay: parcalar.join(" · "), adet: adet,
      birimKurus: birim, kurus: hesap, fiyatMetni: fiyatMetni,
      birimMetni: kurusMetni(birim),
      // odenebilir: parametrik/fiyatsız ürün ödeme akışına GİREMEZ (kanal WhatsApp)
      odenebilir: hesap != null && !(urun && urun.parametrik)
    };
  }

  // Parametrik (sarı seri) satır: konfigüratörün yazdığı parametre detayı + kuruşlu fiyat.
  // Fiyat satıra eklenirken hesaplanıp satırda taşınır (taban fiyat yoksa null kalır);
  // sipariş tarafı istemci fiyatına GÜVENMEZ — Worker şema + hacim.js + taban fiyatla
  // kendi yeniden hesabını yapar (shop/src/parametrik.js).
  // Dönüş şekli sabit-fiyat dalıyla AYNI olmalı: sepet paneli tek kod yolu kullanıyor.
  function parametrikSatirOzeti(satir) {
    var parcalar = [];
    if (satir.parametre_detay) { parcalar.push(satir.parametre_detay); }
    // Boş malzeme/renk satıra yazılmaz (kart-seçim/konfigur sayfasında seçim yapılmadan
    // WhatsApp'tan sorulabilir; "Malzeme: " gibi boş etiket mesajı kirletmesin).
    if (satir.malzeme) {
      var mYuzde = FILAMENT_FARK.hasOwnProperty(satir.malzeme) ? FILAMENT_FARK[satir.malzeme] : 0;
      parcalar.push("Malzeme: " + satir.malzeme + (mYuzde ? " (+%" + mYuzde + ")" : ""));
    }
    if (satir.renk === "Diğer") {
      parcalar.push("Renk: " + (satir.renk_ozel || "özel renk") + " (özel, +%" + RENK_DIGER_YUZDE + ")");
    } else if (satir.renk) {
      parcalar.push("Renk: " + satir.renk);
    }
    var adet = adetDuzelt(satir.adet);
    if (adet > 1) { parcalar.push("Adet: " + adet); }
    var birim = (satir.parametrik_fiyat_kurus == null) ? null : satir.parametrik_fiyat_kurus;
    var kurus = (birim == null) ? null : birim * adet;
    return {
      detay: parcalar.join(" · "), adet: adet,
      birimKurus: birim, kurus: kurus,
      fiyat: (kurus == null) ? null : kurus / 100,
      birimMetni: kurusMetni(birim),
      fiyatMetni: (kurus == null) ? "Ölçüye özel fiyat — teklif için sipariş verin" : kurusMetni(kurus),
      // Taban fiyat boş üründe (bugün yalnız vida) fiyat null -> ödeme akışına giremez;
      // PARAMETRIK_ODEME_ACIK ise mimarın açacağı anahtar (Worker da AYNI sabiti okur).
      // satir.konfigur (dekor konfigüratörü, /konfigur.js): kart-ödeme kanalı FAIL-CLOSED
      // KAPALI — Worker bu satırın fiyatını sunucuda YENİDEN HESAPLAYAMIYOR (D1'de yalnız
      // taban fiyat var, jenerator şeması yok; istemci fiyatına güvenilmez -> sessiz eksik
      // tahsilat riski). Kanal WhatsApp; Worker'a konfigur desteği gelince açılır.
      odenebilir: PARAMETRIK_ODEME_ACIK && kurus != null && !satir.konfigur
    };
  }

  // ---- sepet (localStorage) ----
  var CART_KEY = "pruvo_sepet";

  // Eski format (düz id dizisi) otomatik migrate edilir: varsayılan PLA/Siyah satırına çevrilir.
  // Adetsiz eski satırlar (Faz 1) adet=1 alır; bozuk/aralık dışı adet 1-99'a çekilir.
  function sepetYukle() {
    var ham;
    try { ham = JSON.parse(localStorage.getItem(CART_KEY) || "[]"); }
    catch (e) { ham = []; }
    if (!Array.isArray(ham)) { return []; }
    return ham.map(function (x) {
      if (typeof x === "string") { return bosSatir(x); }
      if (x && typeof x === "object" && x.id) {
        var s = {
          id: x.id, malzeme: x.malzeme || "PLA", renk: x.renk || "Siyah",
          renk_ozel: x.renk_ozel || "", boy_etiket: x.boy_etiket || null,
          adet: adetDuzelt(x.adet == null ? 1 : x.adet)
        };
        if (x.parametreler && typeof x.parametreler === "object") {
          s.parametreler = x.parametreler;
          s.parametre_detay = x.parametre_detay || "";
          s.hacim_mm3 = x.hacim_mm3 || null;
          s.parametrik_fiyat_kurus = (x.parametrik_fiyat_kurus == null) ? null : x.parametrik_fiyat_kurus;
          // Konfigur (dekor konfigüratörü) bayrağı korunur: parametrikSatirOzeti kart-ödeme
          // kanalını bu bayrakla kapatır; düşerse satır sayfa yenilenince ödenebilir görünürdü.
          if (x.konfigur === true) { s.konfigur = true; }
        }
        return s;
      }
      return null;
    }).filter(Boolean);
  }

  function sepetKaydet(sepet) {
    try { localStorage.setItem(CART_KEY, JSON.stringify(sepet)); } catch (e) { }
  }

  root.PRUVO_SECENEK = {
    FILAMENT_FARK: FILAMENT_FARK,
    FILAMENT_SIRA: FILAMENT_SIRA,
    RENK_SECENEKLERI: RENK_SECENEKLERI,
    RENK_DIGER_YUZDE: RENK_DIGER_YUZDE,
    FONKSIYONEL_KATEGORILER: FONKSIYONEL_KATEGORILER,
    ADET_EN_AZ: ADET_EN_AZ,
    ADET_EN_COK: ADET_EN_COK,
    KARGO_UCRET_KURUS: KARGO_UCRET_KURUS,
    KARGO_BEDAVA_ESIK_KURUS: KARGO_BEDAVA_ESIK_KURUS,
    kargoKurus: kargoKurus,
    KDV_YUZDE: KDV_YUZDE,
    kdvAyristir: kdvAyristir,
    ODEME_ACIK: ODEME_ACIK,
    PARAMETRIK_ODEME_ACIK: PARAMETRIK_ODEME_ACIK,
    ONIZLEME_3D_ACIK: ONIZLEME_3D_ACIK,
    ONIZLEME_AILELER: ONIZLEME_AILELER,
    ONIZLEME_KISITLAR: ONIZLEME_KISITLAR,
    fiyatSayisi: fiyatSayisi,
    fonksiyonelMi: fonksiyonelMi,
    boyFarki: boyFarki,
    hesaplaFiyatKurus: hesaplaFiyatKurus,
    parametrikFiyatKurus: parametrikFiyatKurus,
    adetDuzelt: adetDuzelt,
    kurusMetni: kurusMetni,
    tlMetni: tlMetni,
    bosSatir: bosSatir,
    satirAnahtari: satirAnahtari,
    satirOzeti: satirOzeti,
    CART_KEY: CART_KEY,
    sepetYukle: sepetYukle,
    sepetKaydet: sepetKaydet
  };
  // Tarayıcıda window, Worker'da (shop/src/index.js import eder) globalThis — aynı tek kaynak.
})(typeof window !== "undefined" ? window : globalThis);
