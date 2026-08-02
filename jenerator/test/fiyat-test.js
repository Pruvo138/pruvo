/* KABUL TESTI #2 (fiyat orantısı) + #3'ün saf kısmı (sınır doğrulama).
   secenekler.js tarayıcı-IIFE'si vm sandbox'ında window ile yüklenir;
   konfigurator.js node'da module olarak çalışır. Başarısızlıkta exit 1. */
"use strict";
var fs = require("fs");
var vm = require("vm");
var path = require("path");

var KOK = path.join(__dirname, "..", "..");
var sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), sandbox);
var SECENEK = sandbox.window.PRUVO_SECENEK;
var KONF = require(path.join(KOK, "jenerator", "konfigurator.js"));
var HACIM = require(path.join(KOK, "jenerator", "hacim.js"));

var hata = 0;
function esit(ad, gercek, beklenen) {
  var ok = JSON.stringify(gercek) === JSON.stringify(beklenen);
  console.log((ok ? "  [OK ] " : "  [HATA] ") + ad + " -> " + JSON.stringify(gercek) +
              (ok ? "" : " (beklenen: " + JSON.stringify(beklenen) + ")"));
  if (!ok) { hata++; }
}

/* HACİM DOĞRULAMA KAPISI (2026-07-31): parametrikFiyatKurus artık İLK argüman olarak
   aileyi (sema.hacimFormulu) alır ve hacmi gerçek geometriye karşı doğrulanmamış
   ailede null döner. Aşağıdaki testlerin çoğu FİYAT FORMÜLÜNÜ sınar, kapıyı değil —
   onlar doğrulanmış bir aile adıyla çağrılır. Kapının kendisi ayrı bölümde
   (+ jenerator/test/hacim-guveni-kabul.mjs) sınanır. */
var A = "kutu";   // doğrulanmış aile (sapma %0.00) — saf formül testleri için
function F(taban, tabanHacim, hacim, malzeme, renk) {
  return SECENEK.parametrikFiyatKurus(A, taban, tabanHacim, hacim, malzeme, renk);
}

// --- #2 Fiyat orantısı ---
// Taban 100 TL, hacim +%8, ASA (×1.60), Diğer renk (×1.15) -> 198,72 TL birebir.
esit("bileşik örnek 100×1.08×1.60×1.15 (kuruş)",
     F(100, 1000, 1080, "ASA", "Diğer"), 19872);
esit("bileşik örnek metin", SECENEK.kurusMetni(19872), "198,72 TL");
// Taban ×1.08 hacim, PLA/Siyah -> TAM ×1.08 (yuvarlama yok, kuruş korunur).
esit("saf hacim oranı ×1.08", F(100, 1000, 1080, "PLA", "Siyah"), 10800);
esit("kuruş kesirli örnek 250×1.037", F(250, 1000, 1037, "PLA", "Siyah"), 25925);
esit("kuruş metni 259,25", SECENEK.kurusMetni(25925), "259,25 TL");
// ABS ve Karbon KALDIRILDI (Okan, 16 Tem) — mühendislik malzemeleri WhatsApp'tan.
esit("filament katsayıları PLA/PETG/TPU/ASA",
     ["PLA", "PETG", "TPU", "ASA"].map(function (m) {
       return F(100, 1000, 1000, m, "Siyah");
     }), [10000, 13000, 15500, 16000]);
// Taban fiyat yoksa fiyat yok ("—" davranışının çekirdeği).
esit("tabanFiyat null -> fiyat null", F(null, 1000, 1080, "ASA", "Diğer"), null);

// --- ZEMİN (Okan kuralı, 16 Tem — tools/paket-sari-fiyat.md) ---
// fiyat = taban × max(1, hacim/tabanHacim) × filament × renk.
// Taban fiyat ZEMİNDİR: varsayılandan küçük her ölçüde çarpan 1'e sabitlenir,
// filament/renk çarpanları zemin fiyata AYNEN uygulanır. Basamak yok: taban
// üstünde sürekli oran, kuruş korunur.
esit("zemin: hacim tabanın yarısı -> taban aynen (PLA/Siyah)",
     F(100, 1000, 500, "PLA", "Siyah"), 10000);
esit("zemin: sınırın hemen altı -> taban",
     F(100, 1000, 999.9, "PLA", "Siyah"), 10000);
esit("zemin: kuruş korunur (333 zemin × PETG 1.30 = 432,90)",
     F(333, 1000, 500, "PETG", "Siyah"), 43290);
esit("zemin: filament+renk zemine uygulanır (100×1×1.60×1.15)",
     F(100, 1000, 500, "ASA", "Diğer"), 18400);
// BÜYÜME: taban üstünde hacimle monoton artış (zemin büyümeyi bozmaz).
var buyume = [1000, 1080, 2000, 5000].map(function (h) {
  return F(100, 1000, h, "PLA", "Siyah");
});
esit("büyüme: taban üstü sürekli oran (son adım 3× TAVANA çarpar: 50000->30000)",
     buyume, [10000, 10800, 20000, 30000]);
esit("büyüme: sıkı artan", buyume.every(function (v, i) {
  return i === 0 || v > buyume[i - 1];
}), true);

// --- TABAN FİYATLAR (Okan KESİN tablosu — tools/paket-sari-fiyat.md) ---
// Vida istisnası KALKTI (tools/paket-vida-fiyat.md): hacim.js vida üretim
// motorunun STL hacimlerine kalibre edildi (kalibrasyon-referans.json "vida",
// 77 set ≤%3) — 18/18 aile dolu, vida tabanı 100 TL (Okan kesin değeri).
var TABAN_FIYATLAR = {
  "kisiye-ozel-jeton-cip-madalyon": 15,
  "olcuye-ozel-baglanti-konektor": 170,
  "olcuye-ozel-cetvel": 130,
  "olcuye-ozel-damga-kase": 350,
  "olcuye-ozel-huni": 170,
  "olcuye-ozel-izgara-menfez-kapak": 250,
  "olcuye-ozel-montaj-braketi": 150,
  "olcuye-ozel-oring-conta": 100,
  "olcuye-ozel-pervane-fan-cark": 300,
  "olcuye-ozel-petek-delikli-panel": 200,
  "olcuye-ozel-profil-beam": 150,
  "olcuye-ozel-ramp-sim-takoz": 160,
  "olcuye-ozel-rulman": 200,
  "olcuye-ozel-triger-kasnagi": 180,
  "olcuye-ozel-triger-kayisi": 150,
  "olcuye-ozel-vida-civata-somun-pul": 100,
  "olcuye-ozel-yay-dalga-flexure": 130,
  "ozel-disli-kramayer-uretimi": 300,
  // Yeni sarı aileler 1. dalga — Okan kararı (17 Tem, düzeltme): üçü de 150 TL'den
  // başlar (taban = zemin; varsayılan ölçünün altında bu fiyatın altına inilmez).
  "olcuye-ozel-hortum-adaptoru": 150,
  "olcuye-ozel-kutu-organizer": 150,
  "olcuye-ozel-vidali-kavanoz-tapa": 150,
  // Olcuye ozel toka (yeni sari aile, 2026-07-26 — Okan karari): 150 TL taban/zemin
  // (varsayilan 25mm/PLA/dikis). Drift kilidi: sema sayisi 21 -> 22 lockstep.
  "olcuye-ozel-toka": 150,
  // Olcuye ozel cerceve (yeni parametrik aile, 2026-07-27 — Okan karari): 200 TL taban/zemin
  // (varsayilan 100x150/k12/d5.2/chamfer). 3x tavan -> max 600 TL. 2-renk yazi ek ucreti
  // secenekler.js IKI_RENK_EK_KURUS'tan gelir (clamp DISI) ve 2026-07-29'dan beri 0 =
  // TAHSIL EDILMEZ. Drift kilidi: sema sayisi 22 -> 23 lockstep.
  "olcuye-ozel-cerceve": 200
};
var URUN_DIR = path.join(KOK, "jenerator", "urunler");
var semaDosyalari = fs.readdirSync(URUN_DIR).filter(function (f) { return /\.json$/.test(f); });
esit("şema sayısı 23", semaDosyalari.length, 23);
semaDosyalari.forEach(function (dosya) {
  var s = JSON.parse(fs.readFileSync(path.join(URUN_DIR, dosya), "utf8"));
  esit("tabanFiyatTL " + s.id, s.tabanFiyatTL, TABAN_FIYATLAR[s.id]);
});

// --- ZEMİN, GERÇEK AİLELERDE: varsayılandan KÜÇÜK geçerli setlerde fiyat =
// taban × filament × renk (hacim gerçek hacim.js ile hesaplanır; setin gerçekten
// taban altında kaldığı da doğrulanır ki test boş yere yeşil yanmasın).
var KUCUK_SETLER = {
  "olcuye-ozel-oring-conta": { ic_cap: 10, kesit_cap: 2, profil: "yuvarlak" },
  "olcuye-ozel-cetvel": { tip: "duz", sistem: "metrik", uzunluk: 10, genislik: 20,
                          kalinlik: 2, isaret_stili: "oyma" },
  "olcuye-ozel-huni": { agiz_capi: 40, yukseklik: 30, uc_capi: 4, uc_boyu: 54, uc_acisi: 0 },
  "olcuye-ozel-baglanti-konektor": { kol_sayisi: 2, kol_kesiti: "yuvarlak", cubuk_capi: 6,
                                     kol_boyu: 20, cidar: 2, gecme: "normal" },
  // Vida zemin kanıtı: varsayılan M5 cıvatadan KÜÇÜK set (M3 somun) → 100 TL tabanı.
  "olcuye-ozel-vida-civata-somun-pul": { urun_tipi: "somun", cap: 3, boy: 10, tolerans: 0.2 }
};
Object.keys(KUCUK_SETLER).forEach(function (id) {
  var s = JSON.parse(fs.readFileSync(path.join(URUN_DIR, id + ".json"), "utf8"));
  var set = KUCUK_SETLER[id];
  esit("küçük set geçerli: " + id, KONF.dogrula(s, set).gecerli, true);
  var h = KONF.hacimMm3(s, set, HACIM);
  esit("küçük set taban altında: " + id, h != null && h < s.tabanHacimMm3, true);
  var taban = TABAN_FIYATLAR[id];
  // ZEMİN kuralı FORMÜL testidir (ürünün kendi ailesiyle değil, doğrulanmış aile A ile
  // çağrılır): bu ailelerin bir kısmı bugün hacim kapısıyla KAPALI (oring/huni/vida) ve
  // gerçek aileyle çağrılsa null dönerdi — o kapı ayrı bölümde sınanıyor.
  esit("zemin PLA/Siyah = taban: " + id,
       F(taban, s.tabanHacimMm3, h, "PLA", "Siyah"), taban * 100);
  esit("zemin PETG = taban×1.30: " + id,
       F(taban, s.tabanHacimMm3, h, "PETG", "Siyah"),
       Math.round(taban * 130));
});

// --- VİDA: üretilemez ölçü şemadan seçilemez/reddedilir (mimar kabul şartı) ---
// Motor kanıtı (kanit/vida-motor-olcu-kaniti.txt): üretim eşlemi SADECE
// 11 standart M kabul eder (3,4,5,6,8,10,12,14,16,18,20; 24 ara değer RET);
// cıvata M3/M4 motorda BOŞ GEOMETRİ (altıgen kafa tablosu M5'ten başlar).
var vidaSema = JSON.parse(fs.readFileSync(
  path.join(URUN_DIR, "olcuye-ozel-vida-civata-somun-pul.json"), "utf8"));
function vidaSet(tip, cap) { return { urun_tipi: tip, cap: cap, boy: 20, tolerans: 0.2 }; }
esit("vida: yarım ölçü reddedilir (somun M7.5)",
     KONF.dogrula(vidaSema, vidaSet("somun", 7.5)).gecerli, false);
esit("vida: tablo dışı tam ölçü reddedilir (mil M7)",
     KONF.dogrula(vidaSema, vidaSet("mil", 7)).gecerli, false);
esit("vida: tablo dışı tam ölçü reddedilir (civata M13)",
     KONF.dogrula(vidaSema, vidaSet("civata", 13)).gecerli, false);
esit("vida: üretilemez cıvata reddedilir (M3)",
     KONF.dogrula(vidaSema, vidaSet("civata", 3)).gecerli, false);
esit("vida: üretilemez cıvata reddedilir (M4)",
     KONF.dogrula(vidaSema, vidaSet("civata", 4)).gecerli, false);
esit("vida: üretilebilir küçük ölçüler satışta kalır (somun M3, pul M4, mil M3)",
     [KONF.dogrula(vidaSema, vidaSet("somun", 3)).gecerli,
      KONF.dogrula(vidaSema, vidaSet("pul", 4)).gecerli,
      KONF.dogrula(vidaSema, vidaSet("mil", 3)).gecerli], [true, true, true]);
esit("vida: standart ölçüler geçerli (civata M5/M12/M20)",
     [KONF.dogrula(vidaSema, vidaSet("civata", 5)).gecerli,
      KONF.dogrula(vidaSema, vidaSet("civata", 12)).gecerli,
      KONF.dogrula(vidaSema, vidaSet("civata", 20)).gecerli], [true, true, true]);

// --- sema.kisitlar KABUL TABLOSU (rulman çapraz-parametre + vida sabit-min çapası) ---
// Tablo TEK KAYNAK: jenerator/test/kisit-vakalar.js — mutasyon sürücüsü
// (jenerator/test/kisit-mutasyon.js) AYNI tabloyu koşar, ikinci kopya yok.
// Rulman satırlarının dayanağı ÖLÇÜM: üretim motoruna gerçek render (601 render,
// 0 ayrışma). Her sınır İKİ YÖNLÜ pinlenir (kabul + ret komşusu).
var KISIT = require(path.join(__dirname, "kisit-vakalar.js"));
KISIT.kosu(KONF, {
  rulman: JSON.parse(fs.readFileSync(path.join(URUN_DIR, "olcuye-ozel-rulman.json"), "utf8")),
  vida: vidaSema
}).forEach(function (r) {
  esit("kisit " + r.kod + " (" + r.sema + "): " + r.not, r.gercek, r.beklenen);
});

// --- parametrik sepet satırı özeti ---
var satir = { id: "x", malzeme: "ASA", renk: "Diğer", renk_ozel: "mor", boy_etiket: null,
              parametreler: { ic_cap: 32 }, parametre_detay: "İç çap: 32 mm",
              hacim_mm3: 1080, parametrik_fiyat_kurus: 19872 };
var ozet = SECENEK.satirOzeti({ id: "x", kategori: "Oyun/Hobi", parametrik: true }, satir);
esit("satır özeti fiyat metni", ozet.fiyatMetni, "198,72 TL");
esit("satır özeti detay",
     ozet.detay, "İç çap: 32 mm · Malzeme: ASA (+%60) · Renk: mor (özel, +%15)");
esit("satır anahtarı parametre ayrımı",
     SECENEK.satirAnahtari(satir) !== SECENEK.satirAnahtari(
       Object.assign({}, satir, { parametreler: { ic_cap: 33 } })), true);
var fiyatsiz = Object.assign({}, satir, { parametrik_fiyat_kurus: null });
esit("taban fiyatsız satır metni",
     SECENEK.satirOzeti({ id: "x" }, fiyatsiz).fiyatMetni,
     "Ölçüye özel fiyat — teklif için sipariş verin");

// --- Yeni sarı aileler (1. dalga): 150 TL taban/zemin yolu uçtan uca ---
// Okan kararı (17 Tem, düzeltme "1500->150"): varsayılanda fiyat = 150,
// PETG'de 150×1.30, en küçük geçerli ölçüde de zemin delinmez.
var YENI_KUCUK = {
  "olcuye-ozel-hortum-adaptoru": { uc1_cap: 10, uc1_gecme: "ic", uc2_cap: 10,
                                   uc2_gecme: "ic", boy: 40, cidar: 1.6 },
  "olcuye-ozel-kutu-organizer": { ic_en: 20, ic_boy: 20, ic_yukseklik: 10,
                                  duvar: 1.2, kapak: "yok", bolme_sayisi: 0 },
  "olcuye-ozel-vidali-kavanoz-tapa": { urun_tipi: "tapa", govde_capi: 20,
                                       yukseklik: 20, dis_adimi: 4, cidar: 1.6 }
};
Object.keys(YENI_KUCUK).forEach(function (id) {
  var s = JSON.parse(fs.readFileSync(path.join(URUN_DIR, id + ".json"), "utf8"));
  var vd = KONF.varsayilanDegerler(s);
  esit("varsayılanlar geçerli: " + id, KONF.dogrula(s, vd).gecerli, true);
  esit("hacim = tabanHacim: " + id,
       Math.abs(KONF.hacimMm3(s, vd, HACIM) - s.tabanHacimMm3) < 1e-6, true);
  esit("varsayılanda fiyat = 150 (PLA/Siyah): " + id,
       KONF.fiyatKurus(s, vd, "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }),
       15000);
  esit("PETG = 150×1.30: " + id,
       KONF.fiyatKurus(s, vd, "PETG", "Siyah", { secenek: SECENEK, hacim: HACIM }),
       19500);
  var kucuk = YENI_KUCUK[id];
  esit("küçük set geçerli: " + id, KONF.dogrula(s, kucuk).gecerli, true);
  var kh = KONF.hacimMm3(s, kucuk, HACIM);
  esit("küçük set taban altında: " + id, kh != null && kh < s.tabanHacimMm3, true);
  esit("zemin delinmez (küçük ölçüde de 150): " + id,
       KONF.fiyatKurus(s, kucuk, "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }),
       15000);
});

// --- #3 Sınır doğrulama (saf çekirdek) ---
var sema = {
  hacimFormulu: "oring", tabanHacimMm3: 1000, tabanFiyatTL: null,
  parametreler: [
    { ad: "a", etiket: "A", birim: "mm", tip: "sayi", min: 10, max: 50, adim: 0.5, varsayilan: 20 },
    { ad: "s", etiket: "S", tip: "secim", secenekler: [{ deger: "x", etiket: "X" }], varsayilan: "x" }
  ]
};
esit("geçerli set", KONF.dogrula(sema, { a: 25.5, s: "x" }).gecerli, true);
esit("min altı reddedilir", KONF.dogrula(sema, { a: 9.5, s: "x" }).gecerli, false);
esit("max üstü reddedilir", KONF.dogrula(sema, { a: 51, s: "x" }).gecerli, false);
esit("adım dışı reddedilir", KONF.dogrula(sema, { a: 20.3, s: "x" }).gecerli, false);
esit("boş sayı reddedilir", KONF.dogrula(sema, { a: "", s: "x" }).gecerli, false);
esit("liste dışı seçim reddedilir", KONF.dogrula(sema, { a: 20, s: "yok" }).gecerli, false);

// --- konfigüratör fiyat ucu: geçersiz set fiyat üretmez, geçerli set kuruş üretir ---
var oringSema = JSON.parse(fs.readFileSync(
  path.join(KOK, "jenerator", "urunler", "olcuye-ozel-oring-conta.json"), "utf8"));
var vd = KONF.varsayilanDegerler(oringSema);
esit("örnek şema varsayılanları geçerli", KONF.dogrula(oringSema, vd).gecerli, true);
esit("hacim = tabanHacim (varsayılanlar)",
     Math.abs(KONF.hacimMm3(oringSema, vd, HACIM) - oringSema.tabanHacimMm3) < 1e-6, true);
// oring bugün hacim kapısıyla KAPALI: fiyat ucu ondan tutar ÜRETMEMELİ (fail-closed).
var denemeSema = Object.assign({}, oringSema, { tabanFiyatTL: 100 });
esit("kapalı ailede fiyat ucu tutar üretmez (oring)",
     KONF.fiyatKurus(denemeSema, vd, "PLA", "Siyah",
                     { secenek: SECENEK, hacim: HACIM }), null);
// Aynı uç, DOĞRULANMIŞ ailede (kutu) varsayılanda tabanı verir — uç sağlam, kapı seçici.
var kutuSema = JSON.parse(fs.readFileSync(
  path.join(URUN_DIR, "olcuye-ozel-kutu-organizer.json"), "utf8"));
var kutuVd = KONF.varsayilanDegerler(kutuSema);
esit("varsayılanda fiyat = taban (PLA/Siyah, doğrulanmış aile)",
     KONF.fiyatKurus(Object.assign({}, kutuSema, { tabanFiyatTL: 100 }), kutuVd,
                     "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }), 10000);

/* --- HACİM DOĞRULAMA KAPISI (para, 2026-07-31) — POZİTİF + NEGATİF ---------------
   Ölçüm: hacim.js ↔ OpenSCAD, 22 aile. %3 sınırını aşan 9 aile + hiç ölçülmemiş vida
   tutar ÜRETMEZ (fail-closed); geçen 13 aile AYNEN fiyatlanmaya devam eder. */
var KAPALI_AILELER = ["huni", "izgara", "kasnak", "kayis", "oring", "pervane",
                      "petek", "rampa", "rulman", "vida"];
var ACIK_AILELER = ["adaptor", "braket", "cerceve", "cetvel", "disli", "jeton", "kase",
                    "kavanoz", "konektor", "kutu", "profil", "toka", "yay"];

// POZİTİF: kapı tutuyor — sapan/ölçülmemiş ailede tutar HİÇ üretilmez (0 TL DEĞİL, null).
KAPALI_AILELER.forEach(function (aile) {
  esit("kapı: " + aile + " tutar üretmez (null)",
       SECENEK.parametrikFiyatKurus(aile, 100, 1000, 5000, "PLA", "Siyah"), null);
  esit("kapı: " + aile + " doğrulanmış sayılmaz",
       SECENEK.hacimDogrulanmisMi(aile), false);
});

// NEGATİF: meşru iş DURMUYOR — doğrulanmış ailelerde fiyat AYNEN üretiliyor.
// (Tek yönlü test ölü olurdu: her şeye null döndüren bir kapı da pozitifi geçerdi.)
ACIK_AILELER.forEach(function (aile) {
  esit("kapı NEGATİF: " + aile + " fiyatlanmaya devam eder",
       SECENEK.parametrikFiyatKurus(aile, 100, 1000, 1080, "PLA", "Siyah"), 10800);
  esit("kapı NEGATİF: " + aile + " doğrulanmış",
       SECENEK.hacimDogrulanmisMi(aile), true);
});

// FAIL-CLOSED YÖN: bilinmeyen/boş/prototip adı YEŞİL sayılmaz (yeni aile kendiliğinden
// AÇILMAZ — denylist olsaydı açılırdı).
esit("kapı: hiç tanınmayan yeni aile kapalı",
     SECENEK.hacimDogrulanmisMi("yepyeni-aile"), false);
esit("kapı: prototip adı (toString) yeşil sayılmaz",
     SECENEK.hacimDogrulanmisMi("toString"), false);
esit("kapı: undefined/boş aile kapalı",
     [SECENEK.hacimDogrulanmisMi(undefined), SECENEK.hacimDogrulanmisMi(""),
      SECENEK.hacimDogrulanmisMi(null)], [false, false, false]);
// İMZA KAYMASI: eski sırayla (aile'siz) çağıran bir yer kalırsa tutar üretmemeli.
esit("kapı: eski imzayla çağrı tutar üretmez",
     SECENEK.parametrikFiyatKurus(100, 1000, 1080, "PLA", "Siyah"), null);

// Şemaların hacimFormulu değerleri ile kapı listesi ÖRTÜŞMELİ (liste bayatlarsa kırmızı).
var tumAileler = semaDosyalari.map(function (dosya) {
  return JSON.parse(fs.readFileSync(path.join(URUN_DIR, dosya), "utf8")).hacimFormulu;
}).sort();
esit("kapı kapsamı: her şema ailesi ya açık ya kapalı listede",
     tumAileler.filter(function (a) {
       return ACIK_AILELER.indexOf(a) < 0 && KAPALI_AILELER.indexOf(a) < 0;
     }), []);
esit("kapı kapsamı: açık liste secenekler.js ile birebir",
     Object.keys(SECENEK.HACIM_DOGRULANMIS_AILELER).sort(), ACIK_AILELER.slice().sort());

process.exit(hata ? 1 : 0);
