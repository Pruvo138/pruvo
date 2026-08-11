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

  /* ---- HAZIR TICARI MAL (fiziksel urun) — MALZEME/RENK CARPANI YOK ----------------
     `tur == "fiziksel"` olan kayit HAZIR TICARI MALDIR (tekne boyasi, vernik, tiner...):
     biz URETMEYIZ, RAFTAN satariz. Dolayisiyla o urunde uretim malzemesi (PLA/PETG/ASA/TPU)
     ve "Diğer" renk SECIMI KARSILIKSIZDIR -> fiyati SABITTIR, liste fiyatinin ta kendisi.

     🔴 NEDEN BURADA (para yolu, 2026-08-01 — olculdu): 31 Tem'de fiziksel urun SAYFASINDAN
     secici UI'i kaldirildi, ama SUNUCU fiyatlama fonksiyonu `tur`-KORDU. Canli /api/shop/fiyat
     prova ucuyla olculdu, 1.000 TL'lik fiziksel urunde:
         PLA + Siyah   -> 100000 krs (liste, dogru)
         PLA + "Diğer" -> 115000 krs (+%15)
         ASA + "Diğer" -> 184000 krs (+%84)
     UI artik boyle bir satir URETEMEZ; ama sepet localStorage'da YASAR — onarim oncesi
     kaydedilmis BAYAT bir satir hala fazla tahsil edilirdi ve hicbir dogrulamaya takilmazdi.
     Istemcide secici gizlemek bu yolu KAPATMAZ, yalnizca zorlastirir.

     🔴 FAIL-CLOSED YONU: kural "fiziksel ISE carpan YOK"tur, "3D ISE carpan VAR" DEGIL.
     `tur` alani YOKSA, bossa ya da taninmayan bir deger tasiyorsa (" fiziksel", "Fiziksel",
     0, [] ...) BUGUNKU davranis aynen korunur -> `tur`suz 15.930 baski urununde regresyon 0.
     Karsilastirma TAM dize esitligidir (sayfa ureteci + arama hatti + D1
     semasi ile AYNI kural; kirpma/kucultme YOK).

     TEK KAYNAK: bu fonksiyonu hem site (index.html sepet paneli, urun sayfasi) hem shop
     Worker'i (sepetiFiyatla) cagirir — kural ikinci bir yerde
     TEKRARLANMAZ. Worker `tur`u D1 `urunler.tur` kolonundan okur ve satirOzeti'ye verir. */
  var TUR_FIZIKSEL = "fiziksel";
  function fizikselMi(tur) { return tur === TUR_FIZIKSEL; }

  /* ===================== SINIF BEYANI (tuketici hukuku) ===================== BEGIN BEYAN
     🔴 NEDEN VAR (olculdu 1 Agu): `tur` alani uzun sure YALNIZ PARA yolunu suruyordu
     (hazir ticari malda malzeme/renk carpanini 1,00'e sabitler). Hicbir HUKUKI BEYANI
     surmuyordu: siparis onay e-postasi 659 HAZIR TICARI MAL siparisinde de KOSULSUZ
     "Ürünleriniz özel olarak üretilip gönderilecektir" diyordu. Mesafeli satis
     sozlesmesi ise "bu urunler siparis sirasinda ACIKCA ozel uretim olarak TEYIT
     EDILIR" der — yani o cumle, musterinin stok urunde sahip oldugu 14 GUNLUK CAYMA
     HAKKINI reddetmeye yarayacak teyidi siparis aninda veriyordu. TERS YONDE ihlal.

     BU BLOK YENI HAK/YUKUMLULUK ICAT ETMEZ: yasal sayfalarda (Teslimat ve Iade
     Kosullari · Mesafeli Satis Sozlesmesi m.5-m.6) ZATEN yazili olan iki sinifli
     ayrimi musteriye GORUNUR kilar. Cumleler TEK KAYNAKTIR: siparis e-postasi,
     odeme ekrani ve urun sayfasi ureteci hepsi bu sozlukten beslenir — ikinci kopya
     YOK, iki yuzey sessizce ayrisamaz.

     🔴 FAIL-CLOSED: sinif "fiziksel ISE hazir"dir, "3D ISE ozel" DEGIL. `tur` yoksa ya
     da taninmayan bir deger tasiyorsa sinif "ozel"dir = BUGUNKU metin -> `tur`suz
     15.930 kayitta regresyon 0. Bos sepet de "ozel"dir (bugunku ekran metni).

     ⚠️ KAPSAM DISI: iade/cayma halinde KARGO BEDELININ kime ait oldugu ticari bir
     karardir ve HENUZ VERILMEMISTIR. Buraya "kargo bedeli su tarafa aittir" cumlesi
     YAZILMAZ; yeri IADE_KARGO_YER'dir ve BOS kalir (cayma beyani kapisi C4 nobet tutar).

     🔴 URUN SAYFASI TESLIM BEYANI (10 Agu karari) — IKI SINIF, AYNI SAYI,
     AYRI TETIKLEYICI. Ziyaretci "ne zaman elime gecer" bilmeden odeme karari
     veriyordu; sure sitede 69 yerde yaziliydi ama urun sayfasinda HIC yoktu.
       · SURE her iki sinifta da "3-5 is gunu": site genelindeki teslim taahhudu
         (SSS · teslimat-iade · mesafeli-satis m.4) BU araliktir; baska sayi yazmak
         SINIF TUTARLILIGINI bozar (cayma-beyani-kapisi C5/C6 + B5 nobet tutar).
       · TETIKLEYICI = SAYACIN BASLADIGI OLAY. Ozel uretimde "siparisiniz
         onaylandiktan sonra", hazir/stokta "odemeniz onaylandiktan sonra".
         🔴 "OLCU ONAYINDAN SONRA" YAZILMAZ (olculdu 10 Agu, curutucu bulgusu):
         ozel uretim sinifinin 23.929/23.968'i (%99,84) SABIT TASARIM katalog
         parcasidir; alicidan olcu girdisi ALINMAZ (parametrik/konfigurlu yalniz
         39 kayit) ve odeme akisinda (iyzico hosted) "olcu onayi" diye bir asama
         YOKTUR. Var olmayan bir olaya baglanan taahhudun saati HIC BASLAMAZ.
         Ayrica "olcuye ozel" ifadesi Mesafeli Sozlesmeler Yonetmeligi m.15
         istisnasinin ANAHTAR IFADESIDIR: sabit tasarim katalog urunune urun
         bazinda o damgayi basmak, 1 Agu'da olculen kusurun AYNA GORUNTUSUDUR.
       · TETIKLEYICI SURUYLE AYNI YUZEYDE CELISEMEZ: bu cumlenin tetikleyicisi
         SATIR_OZEL ("siparisinizden sonra uretilir") ve EPOSTA_ODENDI_OZEL
         ("siparisiniz onaylandi") ile AYNI SINIFTADIR. Ayni musteri iki yuzeyde
         iki farkli saat baslangici GORMEZ (kapi B7 nobet tutar).
       · CAYMA yalnizca HAZIR kolda gecer: ozel uretim Mesafeli Sozlesmeler
         Yonetmeligi m.15 kapsamindadir — ama urun sayfasinda hak REDDI de
         YAZILMAZ ("iade hakkiniz yoktur" vb.); hakkin kapsami yasal govdede
         anlatilir (kapi B2/B5/B8 nobet tutar).
       · 39 OLCUYE OZEL (parametrik/konfigurlu) urun icin AYRI METIN ACILMADI:
         yasal govde zaten "Ozel/karmasik islerde sure siparis sirasinda
         bildirilir" kaydini tasiyor; kapsam buyutulmedi (mimar karari).

     ⚠️ BICIM: asagidaki nesne GECERLI JSON olmak zorundadir — sayfa ureteci onu ayni
     sozluk olarak okur (json ayristirici). Cift tirnak, sondaki virgul yok, icinde
     yorum yok. Ayrisirsa uretim PATLAR (fail-closed). */
  var BEYAN = {
    "ETIKET_HAZIR": "Hazır ürün",
    "ETIKET_OZEL": "Özel üretim",
    "SATIR_HAZIR": "Hazır ürün — stoktan gönderilir",
    "SATIR_OZEL": "Özel üretim — siparişinizden sonra üretilir",
    "CAYMA_HAZIR": "Hazır/stok ürünlerde teslim tarihinden itibaren 14 gün içinde gerekçe göstermeden cayma hakkınız vardır.",
    "CAYMA_KARMA": "Hazır ürün olarak işaretli kalemlerde teslim tarihinden itibaren 14 gün içinde gerekçe göstermeden cayma hakkınız vardır; Özel üretim olarak işaretli kalemler kişiye/ölçüye özel hazırlandığından Mesafeli Sözleşmeler Yönetmeliği m.15 uyarınca bu hakkın kapsamı dışındadır.",
    "SAYFA_HAZIR": "Hazır ürün — stoktan gönderilir. Ödemeniz onaylandıktan sonra 3-5 iş günü içinde kargoya verilir. Teslim tarihinden itibaren 14 gün içinde gerekçe göstermeden cayma hakkınız vardır.",
    "SAYFA_OZEL": "Sipariş üzerine özel üretilir — siparişiniz onaylandıktan sonra 3-5 iş günü içinde üretilip kargoya verilir.",
    "EPOSTA_ODENDI_HAZIR": "Ödemeniz alındı, siparişiniz onaylandı. Siparişiniz stoktan hazırlanıp gönderilecektir.",
    "EPOSTA_ODENDI_OZEL": "Ödemeniz alındı, siparişiniz onaylandı. Ürünleriniz özel olarak üretilip gönderilecektir.",
    "EPOSTA_ODENDI_KARMA": "Ödemeniz alındı, siparişiniz onaylandı. Hazır ürün kalemleriniz stoktan hazırlanıp gönderilir; Özel üretim kalemleriniz özel olarak üretilip gönderilir.",
    "EPOSTA_HAVALE_HAZIR": "Siparişiniz alındı. Havale/EFT ödemeniz hesabımıza geçtiğinde siparişiniz stoktan hazırlanıp gönderilir.",
    "EPOSTA_HAVALE_OZEL": "Siparişiniz alındı. Havale/EFT ödemeniz hesabımıza geçtiğinde üretime başlanır.",
    "EPOSTA_HAVALE_KARMA": "Siparişiniz alındı. Havale/EFT ödemeniz hesabımıza geçtiğinde Hazır ürün kalemleriniz gönderime hazırlanır, Özel üretim kalemleriniz üretime alınır.",
    "ODEME_HAVALE_HAZIR": "Devam ettiğinizde siparişiniz kaydedilir ve ödeme için IBAN bilgileri gösterilir; ödemeniz hesabımıza geçince siparişiniz stoktan hazırlanıp gönderilir.",
    "ODEME_HAVALE_OZEL": "Devam ettiğinizde siparişiniz kaydedilir ve ödeme için IBAN bilgileri gösterilir; ödemeniz hesabımıza geçince üretim başlar.",
    "ODEME_HAVALE_KARMA": "Devam ettiğinizde siparişiniz kaydedilir ve ödeme için IBAN bilgileri gösterilir; ödemeniz hesabımıza geçince Hazır ürün kalemleriniz gönderime hazırlanır, Özel üretim kalemleriniz üretime alınır.",
    "HAVALE_KUTU_HAZIR": "Ödemeniz hesabımıza geçince siparişiniz stoktan hazırlanıp gönderilir; dilerseniz dekontu WhatsApp'tan iletebilirsiniz.",
    "HAVALE_KUTU_OZEL": "Ödemeniz hesabımıza geçince üretim başlar; dilerseniz dekontu WhatsApp'tan iletebilirsiniz.",
    "HAVALE_KUTU_KARMA": "Ödemeniz hesabımıza geçince Hazır ürün kalemleriniz gönderime hazırlanır, Özel üretim kalemleriniz üretime alınır; dilerseniz dekontu WhatsApp'tan iletebilirsiniz.",
    "IADE_KARGO_YER": ""
  };

  /* Tek kalemin sinifi. Karar TEK YERDE (fizikselMi) — cagiran hicbir yuzey
     `tur == "fiziksel"` karsilastirmasini TEKRARLAMAZ. */
  function satirSinifi(tur) { return fizikselMi(tur) ? "hazir" : "ozel"; }

  /* Sepetin sinifi: "hazir" | "ozel" | "karma". Girdi, satirlarin `tur` degerleri.
     KARMA sepet TEK CUMLEYE INDIRGENMEZ: cagiran yuzey kalem bazinda da isaretler. */
  function sepetSinifi(turler) {
    var hazir = false, ozel = false;
    (turler || []).forEach(function (t) {
      if (fizikselMi(t)) { hazir = true; } else { ozel = true; }
    });
    if (hazir && ozel) { return "karma"; }
    if (hazir) { return "hazir"; }
    return "ozel";                       // bos sepet + taninmayan deger -> bugunku metin
  }

  /* Sinifa gore secim. Taninmayan sinif adi -> OZEL (fail-closed, bugunku davranis). */
  function _sinifSec(sinif, hazir, karma, ozel) {
    if (sinif === "hazir") { return hazir; }
    if (sinif === "karma") { return karma; }
    return ozel;
  }

  function satirBeyani(tur) {
    return _sinifSec(satirSinifi(tur), BEYAN.SATIR_HAZIR, BEYAN.SATIR_OZEL,
                     BEYAN.SATIR_OZEL);
  }
  function epostaDurumBeyani(sinif, havale) {
    return havale
      ? _sinifSec(sinif, BEYAN.EPOSTA_HAVALE_HAZIR, BEYAN.EPOSTA_HAVALE_KARMA,
                  BEYAN.EPOSTA_HAVALE_OZEL)
      : _sinifSec(sinif, BEYAN.EPOSTA_ODENDI_HAZIR, BEYAN.EPOSTA_ODENDI_KARMA,
                  BEYAN.EPOSTA_ODENDI_OZEL);
  }
  /* Cayma beyani: OZEL sepette BOS doner. Sebep — sozlesmenin hukmu degismiyor ve
     ozel uretim sepetinin bugunku metni BAYT-BAYT korunuyor (regresyon butcesi).
     Cayma istisnasi zaten /teslimat-iade ve /mesafeli-satis §6'da yazili ve odeme
     ekraninda o sayfalar ONAY KUTUSUYLA baglaniyor. */
  function caymaBeyani(sinif) {
    return _sinifSec(sinif, BEYAN.CAYMA_HAZIR, BEYAN.CAYMA_KARMA, "");
  }
  function odemeBeyani(sinif) {
    return _sinifSec(sinif, BEYAN.ODEME_HAVALE_HAZIR, BEYAN.ODEME_HAVALE_KARMA,
                     BEYAN.ODEME_HAVALE_OZEL);
  }
  function havaleKutuBeyani(sinif) {
    return _sinifSec(sinif, BEYAN.HAVALE_KUTU_HAZIR, BEYAN.HAVALE_KUTU_KARMA,
                     BEYAN.HAVALE_KUTU_OZEL);
  }
  /* ===================== SINIF BEYANI ===================== END BEYAN */
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
     VIDA yok: hacim/fiyat formulu OLCUYE DUYARLI (2026-08-04 olcumu — civata ve mil
     CAP+BOY'a, somun ve pul YALNIZ CAP'e duyarli; dort tipte de cap degisince hacim
     degisiyor); aileyi onizleme+satis disinda tutan bugunku sebep FIYAT FORMULU DEGIL,
     sema araligi kusurudur (asagidaki CIKARILANLAR blogu). Bazi ailelerde motorda karsiligi olmayan
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
  /* KOSULLU BEYAN (`eger`, 2026-08-03): bir ailenin uretilemez bolgesi KOSULLU
     olabilir. vida semasi (jenerator/urunler/olcuye-ozel-vida-civata-somun-pul.json
     `kisitlar`) "urun_tipi=civata iken cap >= 5" der. Kosulsuz yazilsaydi
     mil/somun/pul x M3-M4 bolgesi (izgaranin ~%13,6'si) YANLIS bloklanir, yani
     URETILEBILIR bir konfigurasyona "bu secenekle siparis alinmiyor" basilirdi.
     `eger` bir beyaz liste DEGILDIR: parametre->deger KOSUL cifti tasir ve
     onizlemeKisitIhlali() disinda hicbir yerde beyaz liste gibi ele alinmaz.
     vida `cap` listesi SEMADAN turer (cap.gecerliDegerler ∩ kisit min 5) — elle
     tutulan ikinci bir liste YOK; ayrisma kabul kapisinda KIRMIZI yanar.
     Bu blok icine YORUM YAZILMAZ: kapi sabiti JSON'a cevirerek okur. */
  var ONIZLEME_KISIT_KOSUL = "eger";
  var ONIZLEME_KISITLAR = {
    "olcuye-ozel-cetvel": { tip: ["duz"] },
    "olcuye-ozel-damga-kase": { sap: ["sapsiz"], bicim: ["dikdortgen"] },
    "olcuye-ozel-petek-delikli-panel": { mod: ["delikli"] },
    "olcuye-ozel-vida-civata-somun-pul": {
      eger: { urun_tipi: "civata" },
      cap: [5, 6, 8, 10, 12, 14, 16, 18, 20]
    }
  };

  /* Beyan degeri ile MUSTERI degeri ayni mi (kisit karsilastirmasinin TEK yeri).
     🔴 OLCULEN TIP TUZAGI: `cap` SAYISAL bir parametredir ve iki cagri yerine iki
     FARKLI tipte gelir — urun sayfasinda konfigurator (jenerator/konfigurator.js
     degerler()) sayi parametrelerini parseFloat ile NUMBER yapar; Worker'a ise JSON
     gelir ve sema kapisi SAF SAYI METNINI de ("5") kabul eder. Kati `indexOf` ile
     karsilastirilsaydi Worker'a "5" gelen istek beyan listesinde BULUNAMAZ ve
     uretilebilir bir konfigurasyon SESSIZCE yanlis bloklanirdi. Sayi-disi metin
     ("civata") asla sayiya cevrilmez -> gevsek `==` tuzagi yok. */
  function kisitDegeriEsit(beyan, deger) {
    if (beyan === deger) { return true; }
    if (typeof beyan === "number" && typeof deger === "string") {
      var t = deger.trim();
      return /^-?[0-9]+([.,][0-9]+)?$/.test(t) && parseFloat(t.replace(",", ".")) === beyan;
    }
    if (typeof beyan === "string" && typeof deger === "number") {
      return kisitDegeriEsit(deger, beyan);
    }
    return false;
  }

  /* `eger` KOSUL DEGERI o parametrenin SEMADAKI tanimiyla ESLESEBILIR MI —
     yazim hatasi kapisi. Bir kosul degeri semaya gore HICBIR musteri girdisiyle
     eslesemiyorsa (or. `secim` parametresinde tanimli olmayan bir deger, `sayi`
     parametresinde sayiya cevrilemeyen bir deger) kosul EBEDIYEN tutmaz ->
     girdinin beyaz listeleri HIC uygulanmaz -> uretilemez bolge SESSIZCE serbest
     kalir. Olculdu (3 Agu 2026): `urun_tipi` degeri ["civata"] ya da 7 yazilinca
     civata-M3 vakasi BLOK'tan SERBEST'e dusuyordu.
     Sema VERILMEZSE (ucuncu argumansiz eski cagri) tanim yoktur: yalnizca TIP
     AILESI olculebilir — dizi/nesne/bool/null gibi hicbir parametre degeri
     olamayan turler yakalanir, YANLIS ama dogru aileden bir deger (secim
     parametresine yazilmis 7 gibi) YAKALANAMAZ.
     Doner: true = deger bu tanimla eslesebilir, false = yazim hatasi. */
  function kosulDegeriEslesebilirMi(tanim, deger) {
    if (!tanim) {
      return typeof deger === "string" ||
             (typeof deger === "number" && isFinite(deger));
    }
    var tip = tanim.tip || "sayi";
    if (tip === "secim") {
      if (!Array.isArray(tanim.secenekler)) { return false; }
      for (var i = 0; i < tanim.secenekler.length; i++) {
        var s = tanim.secenekler[i];
        if (kisitDegeriEsit((s && typeof s === "object") ? s.deger : s, deger)) {
          return true;
        }
      }
      return false;
    }
    if (tip === "sayi") {
      var sayi = null;
      if (typeof deger === "number" && isFinite(deger)) {
        sayi = deger;
      } else if (typeof deger === "string" &&
                 /^-?[0-9]+([.,][0-9]+)?$/.test(deger.trim())) {
        sayi = parseFloat(deger.trim().replace(",", "."));
      }
      if (sayi === null) { return false; }
      /* Uretim motoru araligin tamamini degil yalniz belirli olculeri destekliyorsa
         (vida M olculeri) o liste DISI bir kosul degeri de asla eslesemez. */
      if (Array.isArray(tanim.gecerliDegerler)) {
        for (var j = 0; j < tanim.gecerliDegerler.length; j++) {
          if (Math.abs(sayi - tanim.gecerliDegerler[j]) < 1e-9) { return true; }
        }
        return false;
      }
      return true;
    }
    if (tip === "metin") { return typeof deger === "string"; }
    return false;                      // bilinmeyen tip -> fail-closed
  }

  /* Semanin parametre tanimlari ad->tanim haritasi; sema yoksa/bozuksa null
     (o zaman kosul degeri yalniz TIP AILESI olarak olculur). */
  function semaParametreHaritasi(sema) {
    if (!sema || typeof sema !== "object" || !Array.isArray(sema.parametreler)) {
      return null;
    }
    var harita = {};
    for (var i = 0; i < sema.parametreler.length; i++) {
      var t = sema.parametreler[i];
      if (t && typeof t === "object" && typeof t.ad === "string") { harita[t.ad] = t; }
    }
    return harita;
  }

  /* ONIZLEME kisit beyani IHLAL EDILDI MI — TEK KAYNAK. Urun sayfasi on-kontrolu
     ve onizleme Worker'inin sema kapisi BU fonksiyonu cagirir; ikinci bir
     yorumlayici kod yolu YOK ([[ikiz-tanim-sessiz-ayrisma]]).
     `sema` (3. argüman, OPSIYONEL) = ailenin parametre semasi; verilirse `eger`
     kosul degerleri ONA GORE dogrulanir (asagi bak).
     Doner: ihlal edilen parametre adi (metin) ya da null (ihlal yok).
       `eger` YOKSA -> bugunku davranis BIREBIR: her anahtar bir beyaz listedir ve
                       parametre VERILMEMISSE (undefined) o anahtar atlanir.
       `eger` VARSA -> kosul ciftlerinin HEPSI tutuyorsa beyaz listeler uygulanir;
                       biri tutmuyorsa girdi HIC uygulanmaz (null).
     FAIL-CLOSED, TAM OLARAK SU KADARI (fazlasi iddia EDILMEZ):
       1. Kosul parametresi musteri setinde hic verilmemisse kosul COZULEMEDI
          sayilir ve beyaz listeler UYGULANIR ("okuyamadim, demek ki kisit yok" bu
          depoyu isiran fail-open desenidir).
       2. `eger` blogunun ya da bir beyaz listenin BICIMI taninmiyorsa (nesne
          olmayan kosul blogu / dizi olmayan beyaz liste) ihlal dondurulur.
       3. Bir `eger` KOSUL DEGERI, `sema` VERILDIGINDE, o parametrenin semadaki
          tanimiyla hicbir zaman eslesemiyorsa — ya da kosul semada TANIMLI OLMAYAN
          bir parametre adina yazilmissa — ihlal dondurulur.
       4. `sema` VERILMEZSE 3. madde TIP AILESI kadar olculur: dizi/nesne/bool/null
          yakalanir, dogru aileden yanlis deger (secim parametresine yazilmis 7,
          liste disi bir "civata2") YAKALANMAZ. Bu, sema tasimayan cagri yerinin
          BILINEN sinirdir; iki canli cagri yeri de semayi TASIR.
     Beyaz liste (kosul disi anahtar) DEGERLERI bu kapiya girmez: onlarin semaya
     gore dogru olup olmadigi ayri bir kabul kapisinin ("semadan turetme" ekseni)
     isidir. */
  function onizlemeKisitIhlali(kisit, parametreler, sema) {
    if (!kisit || typeof kisit !== "object") { return null; }
    var p = parametreler || {};
    var kosul = kisit[ONIZLEME_KISIT_KOSUL];
    if (kosul !== undefined) {
      if (!kosul || typeof kosul !== "object") { return ONIZLEME_KISIT_KOSUL; }
      var tanimlar = semaParametreHaritasi(sema);
      for (var k in kosul) {
        if (!Object.prototype.hasOwnProperty.call(kosul, k)) { continue; }
        var tanim = tanimlar ? tanimlar[k] : null;
        if (tanimlar && !tanim) { return ONIZLEME_KISIT_KOSUL; }
        if (!kosulDegeriEslesebilirMi(tanim, kosul[k])) { return ONIZLEME_KISIT_KOSUL; }
        if (p[k] === undefined) { continue; }
        if (!kisitDegeriEsit(kosul[k], p[k])) { return null; }
      }
    }
    for (var ad in kisit) {
      if (!Object.prototype.hasOwnProperty.call(kisit, ad)) { continue; }
      if (ad === ONIZLEME_KISIT_KOSUL) { continue; }
      var v = p[ad];
      if (v === undefined) { continue; }
      if (!Array.isArray(kisit[ad])) { return ad; }
      var bulundu = false;
      for (var i = 0; i < kisit[ad].length; i++) {
        if (kisitDegeriEsit(kisit[ad][i], v)) { bulundu = true; break; }
      }
      if (!bulundu) { return ad; }
    }
    return null;
  }

  /* Birim fiyat, tamsayı KURUŞ. Sıra (işletme kararı, 16 Tem): malzeme katsayısı -> SONRA "Diğer"
     renk +%15 -> sonra boy farkı (TL, sabit ek). Yuvarlama YOK; tek yuvarlama kuruşun ALTINA
     inen artık içindir (yarım kuruş tahsil edilemez; ör. "Diğer" renkte 333 -> 497,835 TL).

     `tur` (5. parametre, OPSİYONEL — bkz. TUR_FIZIKSEL bloğu): tam "fiziksel" ise HAZIR TİCARİ
     MAL demektir; üretim malzemesi/rengi karşılıksızdır -> her İKİ çarpan da 1,00'e sabitlenir
     (tutar = liste fiyatı). Parametre VERİLMEZSE (eski çağrı yerleri) bugünkü davranış aynen
     korunur — imza genişlemesi fail-closed'dur. Boy farkı BİLEREK dokunulmaz: o bir liste
     varyantı farkıdır, baskı çarpanı değil (fiziksel üründe zaten boy_secenekleri yok ve
     Worker boy_etiket taşıyan kalemi baştan reddeder). */
  function hesaplaFiyatKurus(temelFiyatTL, malzeme, renk, boyFarkTL, tur) {
    if (temelFiyatTL == null) { return null; }
    var fiziksel = fizikselMi(tur);
    var yuzde = (!fiziksel && FILAMENT_FARK.hasOwnProperty(malzeme)) ? FILAMENT_FARK[malzeme] : 0;
    var renkCarpan = (!fiziksel && renk === "Diğer") ? (100 + RENK_DIGER_YUZDE) : 100;
    // Bölmeler en sona: 333*100*130*115 = 497835000 (tamsayı, güvenli) -> /10000 -> 49783.5
    var kurus = Math.round(temelFiyatTL * 100 * (100 + yuzde) * renkCarpan / 10000);
    return kurus + Math.round((boyFarkTL || 0) * 100);
  }

  /* ===================== ÖN-SEÇİLİ MALZEME (ürüne göre) ===================== BEGIN ONSECIM
     İSTENEN (işletme, 11 Ağu): "PLA ön-seçili DEĞİL — her ürün için hangi malzeme
     öneriliyorsa O ön-seçili gelsin." Öneri zaten VAR: kategori haritası + ürünün
     opsiyonel malzeme önerisi alanı (aynı harita malzeme rehberini ve öneri rozetini
     de sürer). Burada İKİNCİ bir harita TUTULMAZ — kural haritayı DIŞARIDAN alır.

     🔴 NEDEN FİYATLA BİRLİKTE (sessiz zam sınıfı): PETG +%30, ASA +%60. Ön-seçim
     ilan edilen fiyattan BAĞIMSIZ yapılırsa, hiç seçim yapmayan müşteri sayfada
     gördüğü tutarın %30-60 üstünü sepete yazar ve fark hiçbir yerde GÖRÜNMEZ. Bu
     yüzden ön-seçim ve ilan fiyatı TEK türetme noktasından çıkar: ilanBirimKurus,
     onSecimMalzeme'yi ÇAĞIRIR — ikisi ayrı ayrı hesaplanamaz.

     🔴 AÇMA/KAPAMA ANAHTARI: bayrak KAPALIYKEN kural güvenli varsayılana (bosSatir
     malzemesi, farkı %0) düşer ve BUGÜNKÜ davranış birebir korunur. Bayrağı açmak
     katalogda ilan edilen tutarları yukarı taşır — ticari karardır, kod kararı değil.

     FAIL-CLOSED: referans yoksa/bozuksa, kategori haritada yoksa, öneri sitede
     satılmayan ya da katsayı tablosunda bulunmayan bir ad ise -> güvenli varsayılan.
     Hazır ticari malda (tur "fiziksel") üretim malzemesi karşılıksızdır -> güvenli
     varsayılan (çarpan zaten 1,00). */
  var ONERI_ONSECIM_ACIK = false;
  var KATEGORI_ESADI = { "Bahce": "Bahçe" };

  function _guvenliMalzeme() { return bosSatir("").malzeme; }

  function _siteAdlari(ref) {
    var out = {};
    var liste = (ref && ref.filamentler) || [];
    for (var i = 0; i < liste.length; i++) {
      if (liste[i] && liste[i].site) { out[liste[i].ad] = true; }
    }
    return out;
  }

  /* Ürünün ÖN-SEÇİLİ malzemesi. `ref` = malzeme referansı (satılan malzeme listesi +
     kategori haritası). Sıra ve eleme kuralı öneri rozetiyle AYNIDIR: ürün kendi
     önerisini taşıyorsa harita yerine o geçer, sitede satılmayan ad sessizce atılır,
     kalan İLK ad öneridir. */
  function onSecimMalzeme(urun, ref) {
    var guvenli = _guvenliMalzeme();
    if (!ONERI_ONSECIM_ACIK || !urun || !ref) { return guvenli; }
    /* KAPSAM — BEYAN EDİLEN SINIR: kural yalnız SABİT fiyatlı katalog kolundadır.
       Ölçüye özel / yapılandırıcılı üründe tutar tabandan CANLI hesaplanır ve kart
       yüzeyi tabanı ayrı bir haritadan okur; oralarda ön-seçimi değiştirmek ilan
       edilen tabanı bu değişiklikle ÖLÇÜLMEYEN bir yoldan kaydırırdı.
       Hazır ticari malda üretim malzemesi karşılıksızdır (çarpan zaten 1,00). */
    if (fizikselMi(urun.tur) || urun.parametrik || urun.konfigur) { return guvenli; }
    var siteAd = _siteAdlari(ref);
    var adaylar = [];
    var i;
    var ovr = urun.tavsiyeFilament;
    if (ovr) {
      /* 🔴 BICIMI TANINMAYAN ALAN -> ONERI TURETILEMEZ (fail-closed; ureteç tarafi
         filament_ortak.tavsiyeler ile AYNI kural). Alan DIZI olmak zorundadir.
         Kategori haritasina DUSULMEZ: dusulseydi alani bozuk urun sessizce
         %30-60 zamlanirdi. */
      if (!Array.isArray(ovr)) { return guvenli; }
      for (i = 0; i < ovr.length; i++) {
        if (siteAd[ovr[i]]) { adaylar.push(ovr[i]); }
      }
    } else {
      var kat = KATEGORI_ESADI[urun.kategori] || urun.kategori;
      var harita = (ref.kategoriTavsiye || {})[kat] || [];
      for (i = 0; i < harita.length; i++) {
        if (harita[i] && siteAd[harita[i].ad]) { adaylar.push(harita[i].ad); }
      }
    }
    for (i = 0; i < adaylar.length; i++) {
      if (FILAMENT_FARK.hasOwnProperty(adaylar[i])) { return adaylar[i]; }
    }
    return guvenli;
  }

  /* İLAN EDİLEN BİRİM TUTAR (kuruş) — kart yüzeyi, ürün sayfası ve yapılandırılmış veri
     AYNI sayıyı buradan alır. Ön-seçimle aynı fonksiyondan türer: müşteri hiçbir şey
     seçmeden sepete eklerse satır tutarı BU sayının ta kendisidir. */
  function ilanBirimKurus(urun, ref) {
    var temel = fiyatSayisi(urun && urun.fiyat);
    if (temel == null) { return null; }
    return hesaplaFiyatKurus(temel, onSecimMalzeme(urun, ref), bosSatir("").renk, 0,
                             urun && urun.tur);
  }
  /* ===================== END ONSECIM ===================== */

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

     ---- DÜZELTME — 2026-08-02: yukarıdaki 9 kırmızının 8'i REFERANS ARIZASIYDI ----
     Aile doğrulama çekirdeği 8 ailede YANLIŞ KATIYI ölçüyordu: eşleme kayıtlarındaki
     model referansı ÇIPLAK bir dosya adı olduğu için karşılaştırma nesnesi yanlış
     kaynağa çözülüyordu. O kaynak, asıl üretim zincirinin DROP-IN yerine geçmesi için
     AYNI değişken adlarını kullandığından parametreler hatasız uygulandı ve ölçüm
     BAŞARILI göründü — ama ölçülen geometri bambaşkaydı. Aynı dosya adı + aynı
     değişken adları = SESSİZ nesne değişimi; hiçbir şey bağırmadı.

     KARŞI ÖLÇÜM (bağımsız, asıl üretim zincirine karşı; seed 20260802, 3 rastgele set
     + varsayılan) — 8 ailenin hepsi %3'ün ÇOK altında; sahte sapma → gerçek sapma:
       huni  11,53→0,13 · izgara 39,00→0,00 · kasnak 13,28→0,02 · kayis 28,67→0,15
       oring  6,70→0,39 · pervane 49,21→0,38 · petek 25,76→0,00 · rulman 29,21→0,08
     Yani hacim.js bu ailelerde DOĞRUYDU, referans yanlıştı. Arıza FAZLA TAHSİL değil,
     HAKLI fiyatın hiç üretilmemesiydi (ürünler satılamıyordu).
     Referans çıpası: eşleme kayıtlarına zorunlu kaynak-zinciri beyanı.

     🔴 8 ailenin 7'si listeye alındı; `rulman` BİLEREK DIŞARIDA BIRAKILDI. Hacim
     doğruluğu yeşil (%0,08) ama ŞEMA ARALIĞI kusurlu: doğrulamadan geçen parametre
     kombinasyonlarının bir kısmı ÜRETİLEMİYOR. Üretemeyeceğimiz bir konfigürasyonu
     satılabilir göstermeyiz → şema onarılana kadar tutar üretmez (fail-closed).

     ---- ŞEMA ARALIĞI TARAMASI — 2026-08-03: ÜÇ AİLE DAHA KAPATILDI ------------
     `rulman`daki kusur rulmana ÖZEL DEĞİLMİŞ. Bağımsız tarama (aile başına 2001
     parametre seti + köşe alt-uzayının %100'ü; hüküm üretim ucunun KENDİSİNDEN:
     şema kapısı `KONF.dogrula` → `gecerli:true` derken /ic-derle aynı seti
     assert ile 400/422 ile REDDEDİYOR) şu üretilemez bölgeleri ölçtü:
       petek  %50,0   — `mod="kabartma"` bölgesinin TAMAMI
       cetvel %66,7   — `secim-tanimsiz:tip`
       kase   %83,3   — `sap`, `bicim`   (ürün: ölçüye özel damga/kaşe)
       rulman %32,88  — bilya + makara   (zaten kapalıydı, kıyas ölçütü)
       huni · izgara · kasnak · kayis · oring · pervane → %0,00 (TEMİZ, açık kalır)

     🔴 ÖLÇÜLEN CANLI ZARAR (petek): `mod=kabartma, desen=petek, en=125, boy=114,
     kalinlik=7, goz=15` → 60000 kuruş (600,00 TL) tutar üretiliyor, sipariş kabul
     ediliyor ve para tahsil ediliyordu; AYNI konfigürasyonu üretim ucu 400 ile
     reddediyor ve hiçbir yerde alarm çalmıyordu. Sessiz-hata sınıfı tam olarak bu.
     🔴 EK: petek'in "%0,00 hacim doğruluğu" iddiası YALNIZ `delikli` kolunu
     kapsıyordu; `kabartma` kolu HİÇ ölçülmedi, oysa fiyat o formülden çıkıyordu
     (kabartma 116.551 mm³ · delikli 57.746 mm³ — aynı formül, iki ayrı katı).

     KURAL — YAPISAL, TEK SATIRLIK LİSTE DÜZELTMESİ DEĞİL: bir ailenin parametre
     kutusu ŞARTLI ise (her noktası üretilemiyor) o aile SATIŞA AÇILAMAZ. Bu şart
     bu depoda İKİ yerde beyan edilir ve kural İKİSİNİN BİRLEŞİMİNE bakar:
       KOL 1  ONIZLEME_KISITLAR (ürün id bazlı, yukarıda)
       KOL 2  ürün şemasının `kisitlar` bloğu (`jenerator/urunler/<id>.json`)
     KISITLI AİLELER (KOL1 ∪ KOL2) ∩ bu liste = BOŞ olmalıdır.
     🔴 2026-08-03 ÖLÇÜLDÜ: kural bir süre YALNIZ KOL1'e bakıyordu; şemasında
     `kisitlar` tanımlı `rulman`/`vida` satış listesine eklendiğinde hiçbir kapı
     kırmızı yanmıyordu (kopyada ölçüm: rc=0, A3 "[OK]").
     Bu kural yayın öncesi bloklayıcı bir kabul kapısıyla ölçülür: yarın hangi koldan
     olursa olsun yeni bir kısıt beyan edilirse o aile kendiliğinden satışta KALAMAZ,
     kapı kırmızı yakar. Şemanın onarımı üretim/şema tarafının işidir; onarılıp kısıt
     kalkınca aile kendiliğinden geri açılır (burada ikinci bir liste tutulmaz).

     ---- `rampa` AÇILDI — 2026-08-03, ÜRETİLEBİLİRLİK ÖLÇÜMÜ (işletme onayı) ----
     `rampa` bu listeye "hacmi doğru" diye DEĞİL, satışa açmanın İKİ sorusu da
     ölçüldüğü için girdi. Ölçüm sürücüsü depoda duruyor (parametrik ürün test
     paketindeki üretilebilirlik ölçümü; 25 iddia / 0 kırmızı):
       SORU 1 — fiyat doğru mu: 1.686 GERÇEK render'a karşı hacim kapalı formunun
                en kötü sapması %0,0000079; %0,01 eşiğini aşan nokta 0.
       SORU 2 — bu kutunun HER noktası üretilebilir mi: 944.559 noktalık ilan
                edilmiş ızgarada şema kapısı 0 nokta reddediyor; geçenlerden
                render edilen 1.686 noktanın ÜRETİLEMEZ olanı 0 (%0,0000),
                altı kolun (2 eğim yöntemi × 3 üst yüzey) altısında da 0.
                Kıyas: petek %50,0 · cetvel %66,7 · kase %83,3 · rulman %32,88.
       TERS EKSEN (aşırı red): kutu içinde 0. Kutu DIŞI 99 noktalık sondada 87
                nokta motorda üretilebiliyor ama şema reddediyor — bu bir arıza
                değil KASITLI ürün zarfı (açı üst sınırı 30° iken motor 89°'a
                kadar üretiyor, `adim`=1 mm/1° ara değerleri kapatıyor).
       `kisitlar`: şemada YOK, ONIZLEME_KISITLAR'da da YOK → A3 tetiklenmiyor
                (aynada ölçüldü: rampa eklenince kapı yeşil, KONTROL olarak
                `rulman` eklenince kırmızı — kapı kör değil).
     Müşterinin göreceği aralık: varsayılan 16.000 kuruş, azami 48.000 kuruş
     (3× tavana dayanıyor, aşmıyor).

     KAPALI KALANLAR (5): `vida` (hiç ölçülmedi), `rulman` + `petek` + `cetvel` +
     `kase` (şema aralığı kusuru — yukarıya bak). Beşi de tutar üretmez —
     fail-closed aynen sürer.

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
  /* ⚠️ 2026-08-03 — RASTGELE TOHUM KÖRLÜĞÜ (ölçülmüş, `yay` vakası): aşağıdaki
     sayıların dayanağı olan aile doğrulama çekirdeği her koşumda RASTGELE tohum
     kullanır. Yeşil bir koşum "BU TOHUMDA kırmızı yok" demektir, "aile temiz"
     DEMEZ. `yay` bu listeye 0.07 beyanıyla girmişti; deterministik ızgara
     taraması (810 nokta, aile tarama sürücüsü) aynı ailenin üçgen
     kolunda %3.80, testere kolunda %1.19 sapma ölçtü — yani beyan edilen sayı
     ailenin EN KÖTÜSÜ değil, o tohumun gördüğü noktaydı. Aşağıdaki `yay` değeri
     artık deterministik taramanın en kötüsüdür. DİĞER AİLELER AYNI KÖRLÜKTEDİR:
     onlar için de deterministik tarama koşulmadan sayıları "en kötü" saymayın. */
  var HACIM_DOGRULANMIS_AILELER = {
    // aile: ölçülen en kötü hacim sapması (%) — 2026-07-31, seed 4242, 3 rastgele set + varsayılan
    adaptor: 0.00, braket: 0.27, cerceve: 0.00, disli: 0.24,
    jeton: 0.01, kavanoz: 0.03, konektor: 0.55, kutu: 0.00,
    toka: 0.01,
    // profil: 2026-08-03, DETERMİNİSTİK ızgara (198 nokta: 9 kesit × 2 iç yapı ×
    // {varsayılan, her sayısal eksenin min/max, tüm-min ve tüm-max köşe}), ÜRETİM
    // motoru render'ına karşı en kötü %1.0618 — yalnız `sigma` (40 serisi alüminyum)
    // kolunda, diğer 8 kesit %0.0000 (elips %0.0813). Sınır %3'ün ALTINDA, sınır üstü
    // nokta 0. Eski beyan 0.01 rastgele setin gördüğü noktaydı, ailenin en kötüsü
    // DEĞİLDİ (yay ile aynı körlük) → yukarı yuvarlanmış:
    profil: 1.07,
    // yay: 2026-08-03, DETERMİNİSTİK ızgara (810 nokta: 2 tip × 5 dalga formu ×
    // her sayısal parametrenin min/orta/max'ı), gerçek geometri render'ına karşı
    // en kötü %0.824 (dalga/sinüs, dalga_boyu=40) → yukarı yuvarlanmış:
    yay: 0.83,
    // 2026-08-02 eklenen aileler — bağımsız ölçüm, seed 20260802
    // (yukarıdaki DÜZELTME bloğu: eski kırmızıları referans arızası üretmişti)
    huni: 0.13, izgara: 0.00, kasnak: 0.02, kayis: 0.15,
    oring: 0.39, pervane: 0.38,
    // rampa: 2026-08-03, DETERMİNİSTİK ızgara BEYANI 944.559 nokta (2 eğim yöntemi
    // kolu × 3 üst yüzey; ölü eksenler dahil), üretim motoru render'ına karşı
    // 1.686 GERÇEK render (kova başına 200 deterministik örnek + köşe alt-uzayının
    // %100'ü). En kötü sapma %0.0000079, %0.01 üstü nokta 0 → yukarı yuvarlanmış.
    // ÜRETİLEBİLİRLİK (satışa açmanın İKİNCİ sorusu, bu listeye girmenin şartı):
    // şema kapısı kutu içinde 0 nokta reddediyor, render edilen 1.686 noktanın
    // üretilemezi 0 (%0.0000), altı kolun altısında da 0; kutu içi aşırı red 0.
    // Ölçüm sürücüsü depoda (25 iddia / 0 kırmızı, 11 mutant: 9 öldürücü işaret
    // şartıyla öldü, 2 kontrol yeşil).
    rampa: 0.01,
    // rulman: 2026-08-04. İki AYRI soru ayrı ayrı ölçüldü:
    //  (1) HACİM — satılabilir (şema kapısından geçen) kümede 13.745 nokta, en kötü
    //      sapma %1,2848, %2 üstü nokta 0 → yukarı yuvarlanmış 1.29.
    //  (2) ÜRETİLEBİLİRLİK — şemanın `kisitlar` bloğu ile üretim motorunun kabul
    //      kümesi DÖRT KOVADA karşılaştırıldı; "şema KABUL + motor RET" (yani para
    //      alınıp ürün çıkmayan) kovası 15.608 gerçek render'da 0. Ölçümün kör
    //      olmadığı kendi kontrol mutantlarıyla kanıtlandı: kısıdı GEVŞETEN üç
    //      mutant tehlikeli nokta üretti (284 · 67 · 1.356), DARALTAN kontrol
    //      mutantı üretmedi (486 güvenli sapma).
    // Bu satır tek başına yetmez: ölçümün YEŞİL ve TAZE parite kaydı depoda durur ve
    // her koşumda doğrulanır (motor parmakizi / şema kısıt özeti / nokta eşiği / kova).
    // Kayıt bayatlar ya da kaybolursa satış kapısı bu aileyi KIRMIZI yakar.
    rulman: 1.29
    // 🔴 ÇIKARILANLAR — hacim ekseni yeşil ama ŞEMA ARALIĞI üretilemez konfigürasyon
    // veriyor (yukarıdaki "ŞEMA ARALIĞI TARAMASI" bloğu). Şema onarılana kadar KAPALI:
    //   petek  — bölge `mod="kabartma"` tümü, %50,0 üretilemez, ölçüm 2026-08-03
    //   cetvel — bölge `secim-tanimsiz:tip`, %66,7 üretilemez, ölçüm 2026-08-03
    //   kase   — bölge `sap` + `bicim`, %83,3 üretilemez, ölçüm 2026-08-03
    //   vida   — bölge civata M3 altı, ölçüm 2026-08-03
  };

  /* Aile hacim doğrulamasından geçti mi? Anahtar `sema.hacimFormulu`.
     hasOwnProperty ile bakılır: prototip zincirinden gelen ("toString" gibi) bir ad
     kazara YEŞİL saymasın. */
  function hacimDogrulanmisMi(aile) {
    return typeof aile === "string" &&
      Object.prototype.hasOwnProperty.call(HACIM_DOGRULANMIS_AILELER, aile);
  }

  /* ---- FİYAT TAVANI ÇARPANI (× tabanFiyat) — TEK KAYNAK -------------------
     İşletme kuralı: HACİM-ORANLI fiyat tabanın belli bir katını AŞMAZ (malzeme+renk
     DAHİL). Çarpan bugün tüm hacim-oranlı ailelerde 3'tür; aile adıyla istisna
     yazılabilir (bugün istisna YOK — tablo bilerek BOŞ, mekanizma duruyor).
     Çap çapalı ailelerde (aşağıdaki AILE_CAP_CAPASI) tavan ÇAPAYA görelidir ve
     BU tablodan gelmez; oradaki `tavanCarpani` alanı kullanılır.

     🔴 İKİNCİ LİSTE YOK: tavanı kullanan tek yer `parametrikFiyatKurus`, tavanı
     beyan eden tek yer bu tablodur; nöbetçi de sayıyı buradan DEĞİL, gerçek
     `parametrikFiyatKurus` koşumundan ölçer. Ailede kayıt yoksa varsayılan
     geçerlidir (hasOwnProperty: prototip zincirinden gelen "toString" gibi bir ad
     çarpan SAYILMAZ). */
  var TAVAN_CARPANI_VARSAYILAN = 3;
  var AILE_TAVAN_CARPANI = {};

  function tavanCarpani(aile) {
    return (typeof aile === "string" &&
            Object.prototype.hasOwnProperty.call(AILE_TAVAN_CARPANI, aile))
      ? AILE_TAVAN_CARPANI[aile] : TAVAN_CARPANI_VARSAYILAN;
  }

  /* ---- ÇAP ÇAPALI FİYAT (aile-özel) — TEK KAYNAK ---------------------------
     İşletme kuralı (2026-08-04): `rulman` fiyatı DIŞ ÇAPLA DOĞRU ORANTILI
     olsun — 60 mm = 600,00 TL · 80 mm = 800,00 TL · 100 mm = 1.000,00 TL, yani
     çapa 10 TL × dış çap (mm) = `kurusMm` × mm.

     Çapa fiyatın ZEMİNİNİ değil ÇAPASINI verir; müşterinin seçtiği diğer ayarlar
     (eleman, flanş, genişlik, boşluk, iç çap) bu çapanın etrafında HACİM ORANINCA
     modüle eder:
         kuruş = kurusMm × çap × (hacim / REFERANS hacim(çap))
     REFERANS = o çaptaki ORANTILI/VARSAYILAN konfigürasyon: şemanın kendi
     varsayılanları + `oran` tablosundaki ölçüler çapla ölçeklenir (şemanın `adim`
     ızgarasına yuvarlanarak — referans GERÇEKTEN seçilebilir bir konfigürasyondur).
     Varsayılan ayarlarda pay = payda olur ve üç nokta BİREBİR tutar; buna karşılık
     "Flanşlı"/"Makara" seçimi BEDAVA olmaz (hacmi büyütür, oranı 1'in üstüne çıkarır).

     🔴 REFERANS HACİM ÇALIŞMA ANINDA HESAPLANIR (sabit tablo GÖMÜLMEZ): çağıran
     `baglam.hacimFn` ile aynı hacim motorunu (jenerator/hacim.js) verir. Sabit
     tablo, hacim motoru değişince sessizce yanlış fiyat üretirdi.
     🔴 `oran` yalnız ÇAPLA ÖLÇEKLENEN ölçüleri sayar; ölçeklenmeyen ayarlar
     (eleman/flanş/boşluk) şemanın VARSAYILANINDAN gelir — burada ikinci kopya YOK.
     🔴 TAVAN ARTIK TABANIN DEĞİL ÇAPANIN KATIDIR: çapa × `tavanCarpani`. Eski
     kural (taban × 5 = 100000 kuruş) bu ailede ARTIK ANLAMSIZ olurdu — çapa zaten
     çapla sınırlı, ama sabit 100000 kuruş tavanı 100 mm'de flanş/makara seçimini
     BEDAVA yapardı (kırpardı). Ölçüldü (2026-08-04, şema ızgarasındaki 1.791.424
     geçerli konfigürasyonun TAMAMI): en büyük hacim/referans oranı 4,461;
     malzeme+renk azamisi (ASA ×1,60 · Diğer ×1,15 = ×1,84) ile çapanın 8,21 katı.
     Tavan 20 seçildi: meşru HİÇBİR konfigürasyonu kırpmaz (ölçüm: 0/1.791.424) ve
     kutu ileride genişlerse 2,4× pay bırakır; buna karşılık hacim motoru bozulursa
     tutarı çapanın 20 katıyla (100 mm'de 20.000,00 TL) sınırlar. Tavanın meşru işi
     kırpmadığı nöbetçide AYRI iddiadır (en pahalı meşru konfigürasyon ölçülür). */
  var AILE_CAP_CAPASI = {
    rulman: {
      parametre: "dis_cap",
      kurusMm: 1000,                            // 10,00 TL / mm
      oran: { ic_cap: 1 / 3, genislik: 0.3 },   // çapla ölçeklenen ölçüler
      tavanCarpani: 20                          // × çapa (kaçak sınırı; meşru işi kırpmaz)
    }
  };

  function capCapasi(aile) {
    return (typeof aile === "string" &&
            Object.prototype.hasOwnProperty.call(AILE_CAP_CAPASI, aile))
      ? AILE_CAP_CAPASI[aile] : null;
  }

  /* Değeri şemanın kendi `adim` ızgarasına yuvarlar. Parametre şemada yoksa null
     (fail-closed): ızgarasını bilmediğimiz bir ölçüyü referansa koymayız. */
  function semaIzgarasina(sema, ad, deger) {
    var liste = sema && sema.parametreler;
    if (!Array.isArray(liste)) { return null; }
    for (var i = 0; i < liste.length; i++) {
      if (liste[i].ad === ad) {
        var adim = liste[i].adim;
        return (typeof adim === "number" && adim > 0)
          ? Math.round(deger / adim) * adim : deger;
      }
    }
    return null;
  }

  /* Çapa hesabı — {temel, tavan} (kuruş) veya null (fail-closed).
     `baglam` eksik/bozuksa TUTAR ÜRETİLMEZ: eski hacim-oranı kuralına SESSİZCE
     düşmek, çağrı yeri güncellenmeden kalınca YANLIŞ FİYAT tahsil ettirirdi. */
  function capaHesabi(capa, hacimMm3, baglam) {
    if (!baglam || typeof baglam !== "object") { return null; }
    var sema = baglam.sema, varsayilanlar = baglam.varsayilanlar,
        parametreler = baglam.parametreler, hacimFn = baglam.hacimFn;
    if (!sema || typeof hacimFn !== "function") { return null; }
    if (!varsayilanlar || typeof varsayilanlar !== "object") { return null; }
    if (!parametreler || typeof parametreler !== "object") { return null; }
    var ham = parametreler[capa.parametre];
    var deger = (typeof ham === "number") ? ham
      : parseFloat(String(ham).replace(",", "."));
    if (!isFinite(deger) || deger <= 0) { return null; }

    var ref = {};
    for (var k in varsayilanlar) {
      if (Object.prototype.hasOwnProperty.call(varsayilanlar, k)) { ref[k] = varsayilanlar[k]; }
    }
    if (!Object.prototype.hasOwnProperty.call(ref, capa.parametre)) { return null; }
    ref[capa.parametre] = deger;
    for (var ad in capa.oran) {
      if (!Object.prototype.hasOwnProperty.call(capa.oran, ad)) { continue; }
      if (!Object.prototype.hasOwnProperty.call(ref, ad)) { return null; }
      var olcek = semaIzgarasina(sema, ad, deger * capa.oran[ad]);
      if (olcek == null || !isFinite(olcek)) { return null; }
      ref[ad] = olcek;
    }
    var refHacim = hacimFn(ref);
    if (typeof refHacim !== "number" || !isFinite(refHacim) || refHacim <= 0) { return null; }
    return {
      temel: capa.kurusMm * deger * (hacimMm3 / refHacim),
      tavan: capa.kurusMm * deger * capa.tavanCarpani
    };
  }

  // ---- parametrik ("ölçüye özel") fiyat ----
  // İşletme kuralı (16 Tem, sarı fiyat paketi) — ÇAPASIZ ailelerde (bugün 18/19):
  //   fiyat = tabanFiyat × max(1, hacim/tabanHacim) × malzemeKatsayı × renkFaktör.
  // ÇAPA ailelerinde (AILE_CAP_CAPASI, bugün yalnız rulman) zemin/malzeme/renk/tavan
  // SIRASI aynıdır, yalnız temel tutar hacim oranı yerine ÇAPADAN türer (yukarıdaki blok).
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
  function parametrikFiyatKurus(aile, tabanFiyatTL, tabanHacimMm3, hacimMm3, malzeme, renk,
                                baglam) {
    // HACİM DOĞRULAMA KAPISI — her şeyden ÖNCE (bkz. yukarıdaki blok).
    if (!hacimDogrulanmisMi(aile)) { return null; }
    if (tabanFiyatTL == null || !tabanHacimMm3 || !hacimMm3) { return null; }
    // ÇAPA KOLU (aile-özel): fiyatın çapasını bir ÖLÇÜ belirler, hacim onu modüle
    // eder. Çapasız ailelerde bugünkü hacim-oranı kuralı AYNEN geçerlidir.
    var capa = capCapasi(aile);
    var temelKurus, tavanKurus;
    if (capa) {
      var c = capaHesabi(capa, hacimMm3, baglam);
      if (c == null) { return null; }                 // FAIL-CLOSED (bkz. capaHesabi)
      // Taban fiyat ZEMİN olarak KORUNUR — çapa kolunda da altına inilmez.
      temelKurus = Math.max(tabanFiyatTL * 100, c.temel);
      tavanKurus = c.tavan;
    } else {
      temelKurus = tabanFiyatTL * 100 * Math.max(1, hacimMm3 / tabanHacimMm3);
      tavanKurus = tabanFiyatTL * 100 * tavanCarpani(aile);
    }
    // SIRA DEĞİŞMEZ: zemin -> malzeme -> renk -> tavan -> kuruş yuvarlaması.
    var yuzde = FILAMENT_FARK.hasOwnProperty(malzeme) ? FILAMENT_FARK[malzeme] : 0;
    var kurus = temelKurus * (1 + yuzde / 100);
    if (renk === "Diğer") { kurus = kurus * (1 + RENK_DIGER_YUZDE / 100); }
    // TAVAN (işletme kuralı) — malzeme+renk DAHİL. Çarpanın TEK kaynağı yukarıdaki
    // AILE_TAVAN_CARPANI/TAVAN_CARPANI_VARSAYILAN ikilisi ya da AILE_CAP_CAPASI'dır.
    kurus = Math.min(kurus, tavanKurus);
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
    // HAZIR TICARI MAL: malzeme/renk secimi karsiliksizdir -> ne fiyata ne METNE girer.
    // Metin de susturulur, cunku "Malzeme: ASA (+%60)" yazip liste fiyatini tahsil eden bir
    // satir musteriye YALAN SOYLER (fis/WhatsApp mesaji fiyatla celisemez).
    var fiziksel = fizikselMi(urun && urun.tur);
    var fonksiyonel = fonksiyonelMi(urun && urun.kategori);
    // Fiziksel üründe SEÇİM yoktur (fiyat da metin de); ADET vardır — o satır korunur.
    var secimVar = fonksiyonel && !fiziksel;
    var parcalar = [];
    if (secimVar) {
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
    var bf = secimVar ? boyFarki(urun, satir.boy_etiket) : 0;
    // Fonksiyonel olmayan kategoride seçici yok -> liste fiyatı aynen.
    // Fiziksel üründe hesap YİNE hesaplaFiyatKurus'tan geçer (ikinci fiyat kolu AÇILMAZ):
    // `tur` parametresi çarpanları 1,00'e sabitler -> tutar = liste fiyatı. Kural TEK yerde.
    var birim = fonksiyonel
      ? hesaplaFiyatKurus(temel, satir.malzeme, satir.renk, bf, urun && urun.tur)
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
    TUR_FIZIKSEL: TUR_FIZIKSEL,
    fizikselMi: fizikselMi,
    BEYAN: BEYAN,
    satirSinifi: satirSinifi,
    sepetSinifi: sepetSinifi,
    satirBeyani: satirBeyani,
    epostaDurumBeyani: epostaDurumBeyani,
    caymaBeyani: caymaBeyani,
    odemeBeyani: odemeBeyani,
    havaleKutuBeyani: havaleKutuBeyani,
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
    ONIZLEME_KISIT_KOSUL: ONIZLEME_KISIT_KOSUL,
    onizlemeKisitIhlali: onizlemeKisitIhlali,
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
    TAVAN_CARPANI_VARSAYILAN: TAVAN_CARPANI_VARSAYILAN,
    AILE_TAVAN_CARPANI: AILE_TAVAN_CARPANI,
    tavanCarpani: tavanCarpani,
    AILE_CAP_CAPASI: AILE_CAP_CAPASI,
    capCapasi: capCapasi,
    HACIM_DOGRULANMIS_AILELER: HACIM_DOGRULANMIS_AILELER,
    hacimDogrulanmisMi: hacimDogrulanmisMi,
    IKI_RENK_EK_KURUS: IKI_RENK_EK_KURUS,
    ikiRenkDetayEki: ikiRenkDetayEki,
    ONERI_ONSECIM_ACIK: ONERI_ONSECIM_ACIK,
    onSecimMalzeme: onSecimMalzeme,
    ilanBirimKurus: ilanBirimKurus,
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
