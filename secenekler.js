/* PRUVO — Malzeme/Renk/Boy seçenekleri + fiyat hesaplama + sepet veri modeli.
   index.html VE sayfa üretecinin ürettiği urun/<id>/index.html sayfaları bu dosyayı
   ORTAK kullanır (tek kaynak — ikisine ayrı ayrı kopyalanmaz, drift riski kalmaz).
   shop/ Worker'ı da BU dosyayı import eder: ödeme tutarı sunucuda
   aynı katsayı/renk/sıra kuralıyla hesaplanır — katsayı tablosunun ikinci kopyası YOKTUR.
   Kategori listesi değişirse sayfa üretecindeki FONKSIYONEL_KATEGORILER ile BİRLİKTE
   güncelle (üreteç hangi ürün sayfasına seçici HTML'i basacağını bu listeyle karar verir).

   PARA KURALI (işletme kararı, 16 Tem): YUVARLAMA YOK — küsurat aynen korunur, kuruşuyla tahsil edilir
   (333 × 1.30 = 432,90 TL). Para tamsayı KURUŞTA taşınır; TL'de çarpım yapılsa kayan nokta
   432.90000000000003 üretir ve istemci ile Worker'ın tutarı sessizce ayrışır. */
(function (root) {
  "use strict";

  // PLA taban (fark yok); yüzdeler PLA fiyatına göre ek maliyet.
  // ABS ve Karbon katkılı KALDIRILDI (işletme kararı, 16 Tem) — mühendislik malzemeleri WhatsApp'tan.
  var FILAMENT_FARK = { "PLA": 0, "PETG": 30, "ASA": 60, "TPU": 55 };
  var FILAMENT_SIRA = ["PLA", "PETG", "ASA", "TPU"];
  var RENK_SECENEKLERI = ["Siyah", "Beyaz", "Gri", "Diğer"];
  var RENK_DIGER_YUZDE = 15;
  // İşletme kararı 23 Tem: Dekorasyon + Oyun/Hobi de standart ürün kartını (Renk+Adet+kompakt ikon,
  // katsayılı fiyat) alır — Marin/Otomobil ile birebir. Sayfa üreteci ile BİRLİKTE güncellendi.
  // "Skan Art" (gizli dekor alt-serisi) da aynı düzeni alır: kategori Dekorasyon'dan
  // ayrıldığı an bu listede olmazsa ürün sessizce eski geniş-buton düzenine düşer.
  var FONKSIYONEL_KATEGORILER = ["Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin", "Bisiklet", "Bahçe", "Ofis", "Kamera", "Dekorasyon", "Oyun/Hobi", "Skan Art"];

  /* Liste fiyatı metninden TL sayısı. Sayfa üreteci feed_price ve Worker ile AYNI kural:
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

  /* KARGO (işletme kararı, 16 Tem — KESİN, değişiklik SADECE işletme onayıyla):
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

  /* KDV (KESİN %20, 16 Tem gece — değişiklik SADECE işletme onayıyla; paket kalem 8):
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
     aynı sabiti okur. AÇIK (işletme kararı + mimar, 17 Tem 2026). Ön koşullar sağlandı:
     taban fiyatlar 18/18 dolu (vida dahil, 100 TL), şema kapısı üretilemez ölçüyü
     reddediyor (gecerliDegerler/kisitlar), Worker fiyatı şema+hacim.js ile SUNUCUDA
     yeniden hesaplıyor (Worker parametrik kolu; istemcinin hacim/fiyat alanları OKUNMAZ).
     Kabul testi #5 "parametrik kanal": şemalı KABUL, şemasız/fiyatsız RED (WhatsApp'a).
     KAPATMAK gerekirse: burası false + Worker yeniden deploy (bundle'a gömülü) —
     tek başına front push'u Worker'ı DEĞİŞTİRMEZ. */
  var PARAMETRIK_ODEME_ACIK = true;

  /* Konfigur (dekor konfigüratörü, /konfigur.js) ürünlerinde SELF-SERVİS KART ÖDEMESİ anahtarı
     — TEK yerde, front + Worker aynı sabiti okur. AÇIK (mimar kararı, 2026-07-24). Ön koşul:
     Worker konfigur fiyatını SUNUCUDA yeniden hesaplıyor (Worker konfigür kolu; boy KIRPILIR,
     malzeme katsayısı şema LİSTESİNDEN, istemcinin hacim/fiyat alanları OKUNMAZ) — manipülasyon
     imkansız. Önceden bu satırlar FAIL-CLOSED WhatsApp'a düşüyordu (Worker yeniden hesaplayamıyor
     diye); artık hesaplayabildiği için kart kanalı açılır. KAPATMAK gerekirse: burası false +
     Worker yeniden deploy (bundle'a gömülü) — tek başına front push'u Worker'ı DEĞİŞTİRMEZ. */
  var KONFIGUR_ODEME_ACIK = true;

  /* SELF-SERVİS KARTLA ÖDEME anahtarı (sitedeki "Kartla Güvenli Öde" butonu).
     Bugün KAPALI — sebebi teknik değil, TİCARİ: elimizde yalnız iyzico SANDBOX anahtarı var
     (canlı başvuru sürüyor). Buton canlı sitede açık olsaydı müşteri GERÇEK kartını SANDBOX
     sayfasına girerdi: para hareket etmez ama sandbox `retrieve` "başarılı" döner, sipariş
     'odendi' yazılır ve işletme parayı almadan üretip kargolar. Sepet + WhatsApp kanalı normal
     çalışmaya devam eder (bugünkü davranışın aynısı).
     AÇMAK İÇİN (sırayla): 1) CANLI iyzico anahtarları gelir, 2) Worker yapılandırması
     IYZICO_BASE_URL -> https://api.iyzipay.com + `wrangler secret put` ile canlı anahtarlar,
     3) ödeme kabul testi (sandbox) uçtan uca YEŞİL (kart girişi elle), 4) burası true,
     5) düşük tutarlı gerçek kart duman testi + iade.
     Worker BU anahtardan bağımsız çalışır (uç açık kalır; curl ile doğrulanabilir) — kapali
     olan yalnızca müşteriye gösterilen buton. */
  var ODEME_ACIK = true; /* CANLI (isletme karari + canli anahtarlar, 17 Tem aksam) */

  /* SARI SERI 3D ONIZLEME (onizleme paketi, Faz C pilot).
     ONIZLEME_AILELER: /api/onizleme/olustur ucunun kabul ettigi aile beyaz listesi —
     onizleme Worker'i ve sayfa ureteci (urun sayfasina "Onizle (3D)"
     butonunu basma karari) AYNI listeyi buradan okur, ikinci kopya YOK.
     ONIZLEME_3D_ACIK: butonun musteride gorunmesi. KAPALI tutulur; derleme arka ucu
     (Cloudflare Container, Workers Paid bekliyor) deploy edilip kabul 4e/4g yesillenince
     MIMAR karariyla acilir. Kapaliyken bu degisiklik canlida SIFIR gorunur fark yaratir. */
  var ONIZLEME_3D_ACIK = true;
  /* Faz E (isletme karari 16 Tem: onizleme TUM sari ailelerde): 13 uyelik-motoru
     ailesinin eslem/hacim duzeltme turu sonrasi <=%3 olcum kapisini gecen 12 aile
     listeye alindi (aile basina 25 set eslem olcumu yapildi).
     VIDA yok: fiyat formulu capa duyarsiz, ayri paket
     merge olunca olculup eklenecek. Bazi ailelerde motorda karsiligi olmayan
     secenekler ONIZLEME_KISITLAR ile onizleme disi (fiyat/siparis etkilenmez).
     DIKKAT — yayin kapisi: bu listeye aile eklemek = butonun o urun sayfalarinda
     MUSTERIYE gorunmesi; main'e merge MIMAR kabulu ister. */
  /* Yeni sari aileler 1. dalga (2026-07-17):
     adaptor/kutu/kavanoz bizim ureteclerimiz, 4d olcumu
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
    "olcuye-ozel-vidali-kavanoz-tapa",
    "olcuye-ozel-toka", "olcuye-ozel-cerceve"];
  // v1.2 NOTU (2026-07-28): "olcuye-ozel-cerceve" onizlemeye GERI ALINDI. Aile bizim
  // uretecimizdir (cerceve uretim modeli) -> pakete ACIK_AILELER
  // (paket yukleyici) uzerinden girer; onizleme eslemi public
  // cerceve esleme semasindan turer (5 geometri parametresi + MUSTERI YAZISI
  // yazi->Caption_Text + Output="frame").
  // 🔴 v1.3 (2026-07-29, isletme karari — ONCEKI CUMLE BAYATTI): eski not "yazi/2-renk caption
  // onizleme kapsaminda DEGIL, Caption_Text='' sabit" diyordu; o kapsam-disi karari
  // KALDIRILDI. Onizleme artik musterinin GIRDIGI METNI gosterir (onizleme ile uretim
  // /ic-derle AYNI derleyiciyi kullanir -> onizlemede gorunen govde teslim edilen govdedir).
  // KAPSAM DISI kalan TEK sey: 2-RENK caption akisi (ayri frame_no_caption + caption
  // govdeleri; `Output` sozlesmesi degismeden yapilamaz) — onizleme TEK RENK govdeyi
  // yazisiyla render eder, 2-renk ucreti + min-kenar-10 kisiti siparis yolunda kalir.
  // NOBETCI: metin eslem kapisi + onizleme imaj "metin farklilasma" dumani.
  // YAYIN KAPISI: buton ancak cerceve modelli yeni derleyici imaji (R2 paket + container
  // rebuild) deploy edilince gercek render verir; main'e merge MIMAR onayi ister.

  /* Onizleme model RENGI (aile bazli; viewer.js taban rengi). Liste DISI aileler
     sari-seri kimlik rengini (viewer.js varsayilani, parlak sari) alir. Toka
     (isletme direktifi 26 Tem): toka SIYAH gorunmeli — kemer donanimi sari degil.
     Deger = golgelendirici taban rengi [r,g,b] (0..1); viewer isik carpaniyla
     0.32..~1.06 arasi olcekler, bu yuzden koyu ama sifir-olmayan taban form
     detayini korur (saf 0 tum yuzu duz siyaha yutardi). */
  var ONIZLEME_RENKLER = {
    "olcuye-ozel-toka": [0.12, 0.12, 0.13],
    // Cerceve: gercekci koyu ton (foto-pano cercevesi) — sari-seri kimlik
    // rengine dusmesin diye acikca koyu taban verilir.
    "olcuye-ozel-cerceve": [0.15, 0.15, 0.16]
  };

  /* MUSTERININ SECTIGI RENGIN onizlemedeki karsiligi (viewer.js taban rengi).
     Deger = golgelendirici TABAN rengi [r,g,b] (0..1); viewer isik carpaniyla
     olcekler, bu yuzden "siyah" saf 0 DEGILDIR (saf 0 tum yuzu duz siyaha
     yutar, form detayi kaybolur — kabartma yazi da dahil).
     "Diger" (serbest metin ozel renk) BILEREK YOK: hangi renk oldugunu
     bilmedigimiz icin onizlemede TEMSIL EDILEMEZ -> aile varsayilanina duser. */
  var ONIZLEME_RENK_RGB = {
    "Siyah": [0.13, 0.13, 0.14],
    "Beyaz": [0.90, 0.91, 0.92],
    "Gri": [0.52, 0.55, 0.58]
  };

  /* Renk seciminin onizlemeye UYGULANDIGI aileler. Liste DISI ailede onizleme
     bugunku gibi aile/seri rengini gosterir (canlida sifir gorunur fark).
     🔴 NEDEN LISTE, NEDEN "hepsi" DEGIL: sari, parametrik serinin MARKA kimlik
     rengidir (isletme karari) — 21 ailenin onizleme rengini tek hamlede degistirmek marka
     karari, muhendislik karari degil. Cerceve 29 Tem'de acildi: isletmenin canli
     sikayeti tam olarak "renk secimi onizlemeyi degistirmiyor" idi.
     GENISLETME: aile id'sini listeye ekle (baska dokunus gerekmez). */
  var ONIZLEME_RENK_SECIMI = ["olcuye-ozel-cerceve"];

  /* Onizlemede kullanilacak taban renk. TEK KAYNAK: hem urun sayfasi scripti
     (sayfa ureteci ONIZLEME_JS) hem testler bunu cagirir.
       secilenRenk tanimli + aile listede -> musterinin rengi
       aksi halde                         -> aile rengi (yoksa null = viewer sarisi)
     null donmesi "renk verme" demektir; viewer varsayilanini korur. */
  function onizlemeRengi(urunId, secilenRenk) {
    if (ONIZLEME_RENK_SECIMI.indexOf(urunId) !== -1 &&
        Object.prototype.hasOwnProperty.call(ONIZLEME_RENK_RGB, secilenRenk)) {
      return ONIZLEME_RENK_RGB[secilenRenk];
    }
    return ONIZLEME_RENKLER[urunId] || null;
  }

  /* ---- COK GOVDELI (2-RENK) URUN SOZLESMESI — TEK KAYNAK ------------------
     Bir ailenin AYRI BASILABILIR GOVDELERI. Derleyicide her govde ayri bir eslem
     ailesidir ("<aile>#<parca>", paket yukleyicideki parca bloklari):
     ayni uretim modeli, ayni -D bayraklari, YALNIZ `Output` farkli.
       govde -> Output="frame_no_caption"  (yazisiz cerceve kabugu)
       yazi  -> Output="caption"           (yalniz kabartma yazi govdesi)
     Onizleme Worker'i istegin `parca` alanini BU listeye karsi
     dogrular; liste disi deger 400 alir (fail-closed). Alan HIC verilmezse
     bugunku TEK GOVDE yolu (Output="frame") aynen calisir — geriye donuk uyum.
     Uretim ve onizleme AYNI ucu kullanir; boylece ekranda iki renkte gorunen
     sey, uretimde iki malzemeyle uretilecek olan seyin ta kendisidir.
     GENISLETME: yeni cok-govdeli aile = burada bir satir + esleme json'una
     `parcalar` blogu (baska dokunus gerekmez). */
  var ONIZLEME_PARCALAR = {
    "olcuye-ozel-cerceve": ["govde", "yazi"]
  };

  /* 2-renk onizleme YAPILABILIR MI (tek kaynak — sayfa scripti ve testler bunu
     cagirir). Kosullar (hepsi saglanmali, aksi halde TEK GOVDE yoluna dusulur):
       1. aile cok govdeli listede,
       2. musteri yazi rengi secmis ve o renk GOVDE renginden FARKLI
          (ayni renk = tek malzeme = tek govde; konfigurator de oyle sayar),
       3. HER IKI rengin de onizlemede sayisal karsiligi VAR.
          "Diger" (serbest metin ozel renk) BILEREK temsil edilemez -> tek govde.
     Doner: null (2-renk degil) | {govdeRenk:[r,g,b], yaziRenk:[r,g,b]} */
  function onizlemeIkiRenk(urunId, secilenRenk, yaziRengi) {
    if (!Object.prototype.hasOwnProperty.call(ONIZLEME_PARCALAR, urunId)) { return null; }
    if (!yaziRengi || yaziRengi === secilenRenk) { return null; }
    var g = ONIZLEME_RENK_RGB[secilenRenk], y = ONIZLEME_RENK_RGB[yaziRengi];
    if (!g || !y) { return null; }
    return { govdeRenk: g, yaziRenk: y };
  }

  /* Onizleme secenek kisitlari: uretim motorunda 3D karsiligi olmayan secim
     degerleri (mimar tablosunda; siparis/fiyat AKISINA DOKUNMAZ, yalniz 3D
     onizleme bu degerlerle sunulamaz). Worker sema kapisinda reddeder
     (onizleme-secenek-kisiti), urun sayfasi ayni listeyle onceden uyarir. */
  var ONIZLEME_KISITLAR = {
    "olcuye-ozel-cetvel": { tip: ["duz"] },
    "olcuye-ozel-damga-kase": { sap: ["sapsiz"], bicim: ["dikdortgen"] },
    "olcuye-ozel-petek-delikli-panel": { mod: ["delikli"] }
  };

  /* Birim fiyat, tamsayı KURUŞ. Sıra (işletme kararı, 16 Tem): malzeme katsayısı -> SONRA "Diğer"
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

  /* ---- HACİM DOĞRULAMA KAPISI (para) — 2026-07-31, ÖLÇÜLDÜ ------------------
     NEDEN VAR: parametrik fiyat = tabanFiyat × max(1, hacim/tabanHacim); hacmi
     `jenerator/hacim.js` kapalı-form formülü verir. O formül GERÇEK geometriden
     (gerçek geometri ölçümü) saparsa müşteriden yanlış tutar tahsil edilir ve HİÇBİR ŞEY
     alarm çalmaz: sipariş normal görünür, kart döner, kayıt tutarlıdır. Sessiz-hata
     sınıfı tam olarak budur.

     ÖLÇÜM (22 aile × 31 parametre seti × 4 malzeme = 2.728 karşılaştırma; hacim.js
     ↔ gerçek geometri; aile doğrulama çekirdeği):
       - 9 aile %3 hacim doğruluk sınırını AŞTI.
       - Para etkisi hacim sapmasıyla AYNI eksen DEĞİL: fiyat bir ORAN olduğu için
         (pay ve payda ikisi de hacim.js'ten gelir) ORANTILI hata SADELEŞİR; ayrıca
         max(1,·) tabanı ve 3× tavanı sapmayı yutabilir. Ölçülen en kötü tutar farkı:
           izgara +463,43 TL (taban 250) · rulman +232,12 TL (taban 200)
           petek  -180,74 TL (taban 200) · pervane -172,89 TL (taban 300)
           rampa   +78,28 TL · kayis +77,29 TL · huni +58,28 TL
         (+ = müşteriden FAZLA tahsil = ticari/hukuki risk; − = EKSİK tahsil = zarar.)

     KURAL — ALLOWLIST, DENYLIST DEĞİL (fail-closed): fiyat YALNIZCA gerçek geometriye
     karşı ölçülmüş ve %3 sınırını GEÇMİŞ ailelerde üretilir. Listede olmayan aile
     (yeni eklenen, hiç ölçülmemiş, ölçümü kırmızı) tutar ÜRETMEZ → kart kapanır,
     kalem WhatsApp kanalına düşer. Denylist yazsaydık yarın eklenen ölçülmemiş bir
     aile kendiliğinden AÇIK olurdu — bu deponun tekrar tekrar ısırıldığı sessiz
     fail-open deseni budur.

     🔴 FAIL-CLOSED: sınır aşılınca 0 TL üretilmez, sessiz varsayılana ya da eski
     fiyata DÜŞÜLMEZ, yuvarlanarak kapatılmaz — tutar HİÇ üretilmez (null).
     Sipariş kaybetmek yanlış tahsilattan iyidir (işletme kuralı).

     LİSTEYE AİLE EKLEMENİN TEK YOLU: aile doğrulama çekirdeği o aile için
     yeşil (sapma ≤ %3, gerçek geometri ölçümüyle) — sonra buraya yazılır. Ölçmeden
     ekleme YASAK; ölçüm CI'da koşmuyor (geometri motoru + kardeş depodaki model ister),
     o yüzden bu liste ÖLÇÜM BEYANIDIR ve dayanağı yukarıdaki tarihtir.
     Kapı: hacim güveni kabul testi. */
  var HACIM_DOGRULANMIS_AILELER = {
    // aile: ölçülen en kötü hacim sapması (%) — 2026-07-31, seed 4242, 3 rastgele set + varsayılan
    adaptor: 0.00, braket: 0.27, cerceve: 0.00, cetvel: 0.11, disli: 0.24,
    jeton: 0.01, kase: 0.09, kavanoz: 0.03, konektor: 0.55, kutu: 0.00,
    profil: 0.01, toka: 0.01, yay: 0.07
  };

  /* Aile hacim doğrulamasından geçti mi? Anahtar `sema.hacimFormulu`.
     hasOwnProperty ile bakılır: prototip zincirinden gelen ("toString" gibi) bir ad
     kazara YEŞİL saymasın. */
  function hacimDogrulanmisMi(aile) {
    return typeof aile === "string" &&
      Object.prototype.hasOwnProperty.call(HACIM_DOGRULANMIS_AILELER, aile);
  }

  // ---- parametrik ("ölçüye özel") fiyat ----
  // İşletme kuralı (16 Tem, sarı fiyat paketi):
  //   fiyat = tabanFiyat × max(1, hacim/tabanHacim) × malzemeKatsayı × renkFaktör.
  // Taban fiyat ZEMİNDİR — varsayılandan küçük ölçüde çarpan 1'e sabitlenir, altına
  // İNİLMEZ; taban üstünde hacimle SÜREKLİ oran (basamak yok: eşik uçurumu güven kırar
  // + eşik-altı oynamaya iter). Kuruş cinsinden tutulur; yuvarlama YALNIZ kuruş
  // basamağında (float artığı temizliği), TL'ye yuvarlama yok — kusurat kuruşuyla
  // gösterilir/tahsil edilir.
  //
  // `aile` (= sema.hacimFormulu) BİLEREK İLK parametredir: imza değiştiği için eski
  // sırayla çağıran bir yer güncellenmeden kalırsa `aile` yerine tabanFiyat (sayı)
  // geçer, allowlist'te bulunmaz ve fiyat null döner — yani unutulan çağrı yeri
  // sessizce YANLIŞ FİYAT değil, KAPALI KART üretir (fail-closed refactor).
  function parametrikFiyatKurus(aile, tabanFiyatTL, tabanHacimMm3, hacimMm3, malzeme, renk) {
    // HACİM DOĞRULAMA KAPISI — her şeyden ÖNCE (bkz. yukarıdaki blok).
    if (!hacimDogrulanmisMi(aile)) { return null; }
    if (tabanFiyatTL == null || !tabanHacimMm3 || !hacimMm3) { return null; }
    var yuzde = FILAMENT_FARK.hasOwnProperty(malzeme) ? FILAMENT_FARK[malzeme] : 0;
    var kurus = tabanFiyatTL * 100 * Math.max(1, hacimMm3 / tabanHacimMm3) * (1 + yuzde / 100);
    if (renk === "Diğer") { kurus = kurus * (1 + RENK_DIGER_YUZDE / 100); }
    kurus = Math.min(kurus, tabanFiyatTL * 100 * 3);   // 3× TAVAN (işletme kuralı) — malzeme+renk DAHİL
    return Math.round(kurus);
  }

  /* ÇERÇEVE 2-RENK YAZI EK ÜCRETİ (kuruş) — TEK KAYNAK. Hem ön yüz (jenerator/konfigurator.js)
     hem Worker (parametrik kol) BU değeri okur; iki tarafta ayrı sabit TUTULMAZ
     (ayrışırsa müşteriye gösterilen fiyat ile tahsil edilen fiyat farklı olur — bu depoda
     yaşandı). Satır detayındaki metin de aynı sayıdan türetilir, yani metin fiyatla YALAN
     SÖYLEYEMEZ.

     🔴 BUGÜN 0 = TAHSİL EDİLMEZ (2026-07-29, işletme onayı "para aktığı deliği kapat"):
     ölçüm, canlı derleyiciye aynı geometriyle yazı='' / 4 harfli / 12 harfli metin gönderdi;
     üç çıktı da 65284 bayt / 1304 üçgen / SHA-256 BİREBİR AYNI çıktı — yazı üretilen
     katı modele hiç girmiyor, yani ayrı gövde/ikinci malzeme maliyeti OLUŞMUYOR. Karşılığı olmayan
     +75 TL tahsilatı durduruldu. Ücret 0 iken 2-renk seçimi ve kenar≥10 mm basılabilirlik
     kapısı OLDUĞU GİBİ kalır (ürün satıştan çekilmedi), yalnız para eklenmez.
     GERİ AÇMAK: burayı 7500 yap + Worker'ı yeniden deploy et (değer bundle'a gömülüdür;
     tek başına site push'u Worker'ı DEĞİŞTİRMEZ — PARAMETRIK_ODEME_ACIK ile aynı kural). */
  var IKI_RENK_EK_KURUS = 0;

  /* 2-renk satır detayı eki — ücret metni AYNI sabitten türer (0 iken "+... TL" ibaresi
     hiç yazılmaz). Ön yüz ve Worker aynı fonksiyonu çağırır: iki farklı metin üretilemez. */
  function ikiRenkDetayEki(yaziRenk) {
    return " · Yazı rengi: " + yaziRenk + " (2 renk" +
      (IKI_RENK_EK_KURUS > 0 ? ", +" + (IKI_RENK_EK_KURUS / 100) + " TL" : "") + ")";
  }

  /* Kuruşu ekran metnine çevirir: 43290 -> "432,90 TL", 129870 -> "1.298,70 TL".
     TEK formatter (site + konfigüratör + sepet): spec gereği DAİMA 2 ondalık ve virgüllü —
     tam TL'de de "300,00 TL" yazar. Küsurat korunuyorsa gösterimi de tutarlı olmalı; ayrıca
     iki ayrı formatter tutmak (biri ondalık düşüren) fiyatın yerine göre farklı görünmesine
     yol açardı. iyzico'ya giden NOKTALI metin ayrı (Worker kurusMetin). */
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
    // yazi_renk (cerceve 2. renk) anahtara girer: farkli yazi rengi AYRI satir olmali,
    // yoksa iki farkli 2-renk konfigurasyonu tek satira toplanip biri sessizce kaybolur.
    return [satir.id, satir.malzeme, satir.renk, satir.renk_ozel || "", satir.boy_etiket || "",
            satir.yazi_renk || "",
            satir.parametreler ? JSON.stringify(satir.parametreler) : ""].join("|");
  }

  // Sepet/WhatsApp mesajında ürün+seçim satırının metnini ve hesaplanan fiyatını üretir.
  // fonksiyonel OLMAYAN kategorilerde (seçici hiç gösterilmeyen ürün) detay boş döner —
  // mevcut (öncesi) davranış korunur, mesaj kirlenmez.
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
    // Fonksiyonel olmayan kategoride seçici yok -> liste fiyatı aynen.
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
  // kendi yeniden hesabını yapar (parametrik kol).
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
      // satir.konfigur (dekor konfigüratörü, /konfigur.js): artık Worker fiyatı SUNUCUDA
      // yeniden hesaplıyor (Worker konfigür kolu: boy KIRPILIR, katsayı şema listesinden,
      // istemci hacim/fiyat OKUNMAZ) -> KONFIGUR_ODEME_ACIK ile kart kanalı açık. Bayrak
      // false ise konfigur satırı yine WhatsApp'a düşer (Worker da AYNI sabiti okur).
      odenebilir: PARAMETRIK_ODEME_ACIK && kurus != null &&
                  (!satir.konfigur || KONFIGUR_ODEME_ACIK)
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
          // yazi_renk (cerceve 2. renk): korunur — dusen satir yenilenince 2-renk
          // ek ucreti + ayri-satir anahtari sessizce kaybolurdu.
          if (x.yazi_renk) { s.yazi_renk = x.yazi_renk; }
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
    KONFIGUR_ODEME_ACIK: KONFIGUR_ODEME_ACIK,
    ONIZLEME_3D_ACIK: ONIZLEME_3D_ACIK,
    ONIZLEME_AILELER: ONIZLEME_AILELER,
    ONIZLEME_KISITLAR: ONIZLEME_KISITLAR,
    ONIZLEME_RENKLER: ONIZLEME_RENKLER,
    ONIZLEME_RENK_RGB: ONIZLEME_RENK_RGB,
    ONIZLEME_RENK_SECIMI: ONIZLEME_RENK_SECIMI,
    ONIZLEME_PARCALAR: ONIZLEME_PARCALAR,
    onizlemeRengi: onizlemeRengi,
    onizlemeIkiRenk: onizlemeIkiRenk,
    fiyatSayisi: fiyatSayisi,
    fonksiyonelMi: fonksiyonelMi,
    boyFarki: boyFarki,
    hesaplaFiyatKurus: hesaplaFiyatKurus,
    parametrikFiyatKurus: parametrikFiyatKurus,
    HACIM_DOGRULANMIS_AILELER: HACIM_DOGRULANMIS_AILELER,
    hacimDogrulanmisMi: hacimDogrulanmisMi,
    IKI_RENK_EK_KURUS: IKI_RENK_EK_KURUS,
    ikiRenkDetayEki: ikiRenkDetayEki,
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
  // Tarayıcıda window, Worker'da (Worker import eder) globalThis — aynı tek kaynak.
})(typeof window !== "undefined" ? window : globalThis);
