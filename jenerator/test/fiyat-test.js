/* KABUL TESTI #2 (fiyat orantısı) + #3'ün saf kısmı (sınır doğrulama).
   secenekler.js tarayıcı-IIFE'si vm sandbox'ında window ile yüklenir;
   konfigurator.js node'da module olarak çalışır. Başarısızlıkta exit 1. */
"use strict";
var fs = require("fs");
var vm = require("vm");
var path = require("path");

var KOK = path.join(__dirname, "..", "..");
// MUTANT KOLU (jenerator/test/saksi-fiyat-mutasyon.js): secenekler.js ve Worker
// parametrik.js YOLU ortamdan ezilebilir — mutant kopya canli agaca YAZILMADAN olculur.
var SECENEK_YOL = process.env.PRUVO_SECENEK_YOL || path.join(KOK, "secenekler.js");
var PARAMETRIK_YOL = process.env.PRUVO_PARAMETRIK_YOL ||
  path.join(KOK, "shop", "src", "parametrik.js");
function secenekYukle() {
  var sb = { window: {} };
  vm.createContext(sb);
  vm.runInContext(fs.readFileSync(SECENEK_YOL, "utf8"), sb);
  return sb.window.PRUVO_SECENEK;
}
var SECENEK = secenekYukle();
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
  "olcuye-ozel-cerceve": 200,
  // Olcuye ozel saksi/vazo (2026-10-13 — mimar karari KraL halef-27): taban = M boy
  // (140/100/120) 800 TL; ZEMIN 400 TL ayri (secenekler.js AILE_FIYAT_KURALI). Aile
  // bugun KAPALI (hacim allowlist'inde yok: kisitli sema -> parite kaydi bekler).
  // Drift kilidi: sema sayisi 23 -> 24 lockstep.
  "olcuye-ozel-saksi-vazo": 800
};
var URUN_DIR = path.join(KOK, "jenerator", "urunler");
var semaDosyalari = fs.readdirSync(URUN_DIR).filter(function (f) { return /\.json$/.test(f); });
esit("şema sayısı 24", semaDosyalari.length, 24);
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
  // çağrılır): bu ailelerin bir kısmı bugün hacim kapısıyla KAPALI (rampa/vida) ve
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
// FAIL-CLOSED fikstürü: hacim kapısıyla KAPALI bir aile ondan tutar ÜRETMEMELİ.
// (2026-08-02'ye kadar burada oring vardı; oring bağımsız ölçümle AÇILDI → fikstür
// `rampa`ya taşındı. 2026-08-03: rampa da üretilebilirlik ölçümüyle AÇILDI → fikstür
// hâlâ kapalı olan `cetvel`e taşındı.)
// 🔴 ADAY SEÇİM ŞARTI (ölçüldü, aynı koşumda): seçilen ailenin varsayılanında
// hacim == tabanHacimMm3 OLMALI — yani ölçek çarpanı tam 1. Böylece "null" sonucu
// ÖLÇEKTEN değil YALNIZCA KAPIDAN gelir. Kontrol: aynı hacim AÇIK bir aile adıyla
// çağrıldığında tam 10000 kuruş (taban) veriyor; cetvel 14265.224351646924 mm³ =
// tabanHacim, ölçek 1.
var kapaliSema = JSON.parse(fs.readFileSync(
  path.join(KOK, "jenerator", "urunler", "olcuye-ozel-cetvel.json"), "utf8"));
var kapaliVd = KONF.varsayilanDegerler(kapaliSema);
esit("cetvel şema varsayılanları geçerli", KONF.dogrula(kapaliSema, kapaliVd).gecerli, true);
esit("fikstür ailesi HÂLÂ kapalı (fikstür bayatlarsa kırmızı)",
     SECENEK.hacimDogrulanmisMi(kapaliSema.hacimFormulu), false);
esit("fikstür ailesinde ölçek tam 1 (null ölçekten değil kapıdan gelsin)",
     Math.abs(KONF.hacimMm3(kapaliSema, kapaliVd, HACIM) - kapaliSema.tabanHacimMm3) < 1e-9,
     true);
var denemeSema = Object.assign({}, kapaliSema, { tabanFiyatTL: 100 });
esit("kapalı ailede fiyat ucu tutar üretmez (cetvel)",
     KONF.fiyatKurus(denemeSema, kapaliVd, "PLA", "Siyah",
                     { secenek: SECENEK, hacim: HACIM }), null);
// AÇILAN aile (rampa) artık AYNI uçtan tutar üretir — bu turun açılışı uçtan uca ölçülür.
var rampaSema = JSON.parse(fs.readFileSync(
  path.join(KOK, "jenerator", "urunler", "olcuye-ozel-ramp-sim-takoz.json"), "utf8"));
var rampaVd = KONF.varsayilanDegerler(rampaSema);
esit("rampa şema varsayılanları geçerli", KONF.dogrula(rampaSema, rampaVd).gecerli, true);
esit("AÇILAN ailede fiyat ucu taban üretir (rampa, varsayılan)",
     KONF.fiyatKurus(Object.assign({}, rampaSema, { tabanFiyatTL: 100 }), rampaVd,
                     "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }), 10000);
esit("rampa GERÇEK taban fiyatıyla varsayılan = 16000 kuruş",
     KONF.fiyatKurus(rampaSema, rampaVd, "PLA", "Siyah",
                     { secenek: SECENEK, hacim: HACIM }), 16000);
// AÇILAN aile (oring) artık AYNI uçtan tutar üretir — kapı seçici, kör değil.
esit("açılan ailede fiyat ucu taban üretir (oring)",
     KONF.fiyatKurus(Object.assign({}, oringSema, { tabanFiyatTL: 100 }), vd, "PLA", "Siyah",
                     { secenek: SECENEK, hacim: HACIM }), 10000);
// Aynı uç, DOĞRULANMIŞ ailede (kutu) varsayılanda tabanı verir — uç sağlam, kapı seçici.
var kutuSema = JSON.parse(fs.readFileSync(
  path.join(URUN_DIR, "olcuye-ozel-kutu-organizer.json"), "utf8"));
var kutuVd = KONF.varsayilanDegerler(kutuSema);
esit("varsayılanda fiyat = taban (PLA/Siyah, doğrulanmış aile)",
     KONF.fiyatKurus(Object.assign({}, kutuSema, { tabanFiyatTL: 100 }), kutuVd,
                     "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }), 10000);

/* --- HACİM DOĞRULAMA KAPISI (para, 2026-07-31 + 2026-08-02) — POZİTİF + NEGATİF ---
   Ölçüm: hacim.js ↔ gerçek geometri, 22 aile. Tutar YALNIZ ölçülmüş-ve-geçmiş ailede
   üretilir (fail-closed); kapalı ailede null döner.
   2026-08-02: eski 9 kırmızının 8'i (huni, izgara, kasnak, kayis, oring, pervane,
   petek, rulman) REFERANS ARIZASI çıktı — bağımsız ölçümde hepsi ≤ %0,39.
   Bunlardan 7'si listeye alındı; açık aile 13 → 20.
   2026-08-03 ŞEMA ARALIĞI TARAMASI: `rulman`ın kusuru rulmana özel değilmiş. Şema
   kapısından (`KONF.dogrula` → gecerli:true) GEÇEN ama üretim ucunun 400/422 ile
   REDDETTİĞİ bölgeler ölçüldü (aile başına 2001 set + köşe alt-uzayının %100'ü):
   petek %50,0 (mod="kabartma" tümü) · cetvel %66,7 (secim-tanimsiz:tip) ·
   kase %83,3 (sap + bicim). Üçü de KAPATILDI; açık aile 20 → 17, kapalı 3 → 6.
   (huni/izgara/kasnak/kayis/oring/pervane %0,00 — temiz, açık kalır.)
   2026-08-03 ÜRETİLEBİLİRLİK ÖLÇÜMÜ — `rampa` AÇILDI (işletme onayı): kapalı kalma
   gerekçesi "sapması bağımsız doğrulanmadı" idi ve ölçümle geçersiz kaldı. 944.559
   noktalık ilan edilmiş ızgarada şema kapısı 0 nokta reddediyor; geçenlerden render
   edilen 1.686 GERÇEK render'da üretilemez 0 (%0,0000, altı kolun altısında) ve hacim
   kapalı formunun en kötü sapması %0,0000079. Şemasında `kisitlar` YOK →
   onizleme-vaat-kapisi A3 tetiklenmiyor. Açık aile 17 → 18, kapalı 6 → 5.
   Sürücü: jenerator/test/rampa-uretilebilirlik-olcum.py (25 iddia / 0 kırmızı).
   2026-08-04 ÜRETİLEBİLİRLİK PARİTESİ — `rulman` AÇILDI. Öncül değişti: "şemasında
   `kisitlar` var" tek başına kapatmıyor; kapatan şey "kısıt var VE yeşil+taze parite
   kaydı YOK". Kayıt üretildi: şema kapısı ↔ üretim motoru dört kovada karşılaştırıldı,
   "şema KABUL + motor RET" (para alınıp ürün çıkmayan) kovası 16.000 ölçülen noktada 0,
   çözülmeyen 0; ölçümün kör olmadığı kontrol mutantlarıyla kanıtlandı (kısıdı GENİŞLETEN
   M1/M2/M3 tehlikeli nokta üretti, DARALTAN M4 üretmedi). Hacim ekseni ayrı: en kötü
   sapma %1,2848 (%3 tavanının altında). Açık aile 18 → 19, kapalı 5 → 4.
   Sürücü: jenerator/test/rulman-uretilebilirlik-olcum.py --parite ·
   kayıt sözleşmesi: tools/parite_kaydi.py · okuyucu kapı: tools/onizleme-vaat-kapisi.py A3.
   KAPALI KALAN (4): vida (hiç ölçülmedi), petek + cetvel + kase (hacmi yeşil
   ama ŞEMA ARALIĞI üretilemez kombinasyon veriyor — üretemediğimiz konfigürasyon
   satılabilir görünmez; şema onarılana kadar fail-closed).
   Yapısal kural + kapı: tools/onizleme-vaat-kapisi.py. */
// 2026-10-13: `saksi` KAPALI olarak eklendi (hiç açılmadı): şemasında `kisitlar` var
// (alt≤üst çap, yan eğim ≤40°) → satışa açılması için onizleme-vaat-kapisi A3 YEŞİL+TAZE
// parite kaydı ister; kayıt üretim paketi (saksi_vazo.scad) yüklenmeden üretilemez.
// Fiyat kuralı aşağıda "SAKSI" bölümünde AÇILIŞ SİMÜLASYONUYLA ölçülür.
var KAPALI_AILELER = ["cetvel", "kase", "petek", "saksi", "vida"];
var ACIK_AILELER = ["adaptor", "braket", "cerceve", "disli", "huni", "izgara",
                    "jeton", "kasnak", "kavanoz", "kayis", "konektor", "kutu",
                    "oring", "pervane", "profil", "rampa", "rulman", "toka", "yay"];
esit("kapı sayacı: kapalı 5 / açık 19 (2026-10-13 saksı KAPALI eklendi)",
     [KAPALI_AILELER.length, ACIK_AILELER.length], [5, 19]);

// POZİTİF: kapı tutuyor — sapan/ölçülmemiş ailede tutar HİÇ üretilmez (0 TL DEĞİL, null).
KAPALI_AILELER.forEach(function (aile) {
  esit("kapı: " + aile + " tutar üretmez (null)",
       SECENEK.parametrikFiyatKurus(aile, 100, 1000, 5000, "PLA", "Siyah"), null);
  esit("kapı: " + aile + " doğrulanmış sayılmaz",
       SECENEK.hacimDogrulanmisMi(aile), false);
});

/* NEGATİF: meşru iş DURMUYOR — doğrulanmış ailelerde fiyat AYNEN üretiliyor.
   (Tek yönlü test ölü olurdu: her şeye null döndüren bir kapı da pozitifi geçerdi.)

   ÇAPA AİLELERİ AYRI ÖLÇÜLÜR (2026-08-04): `AILE_CAP_CAPASI`'daki aileler (bugün
   rulman) fiyatı hacim ORANINDAN değil ÇAPTAN çapalar; hesap için şema+ölçü+hacim
   motorunu taşıyan `baglam` şarttır ve bağlamsız çağrı FAIL-CLOSED null döner.
   Liste buraya YAZILMAZ, secenekler.js'ten OKUNUR (bayatlayamaz). */
var CAPALI_AILELER = ACIK_AILELER.filter(function (a) { return !!SECENEK.capCapasi(a); });
esit("çapa ailesi sayısı (bugün yalnız rulman)", CAPALI_AILELER, ["rulman"]);
ACIK_AILELER.forEach(function (aile) {
  if (SECENEK.capCapasi(aile)) {
    // Çapa ailesi: bağlamsız çağrı tutar ÜRETMEZ (güncellenmemiş çağrı yeri sessiz
    // yanlış fiyat değil, KAPALI KART üretir).
    esit("kapı NEGATİF: " + aile + " çapa ailesi — bağlamsız çağrı null",
         SECENEK.parametrikFiyatKurus(aile, 100, 1000, 1080, "PLA", "Siyah"), null);
  } else {
    esit("kapı NEGATİF: " + aile + " fiyatlanmaya devam eder",
         SECENEK.parametrikFiyatKurus(aile, 100, 1000, 1080, "PLA", "Siyah"), 10800);
  }
  esit("kapı NEGATİF: " + aile + " doğrulanmış",
       SECENEK.hacimDogrulanmisMi(aile), true);
});

/* ---- ÇAP ÇAPALI FİYAT (rulman) — Okan kararı 2026-08-04: 10 TL × dış çap ------
   Meşru iş burada ölçülür: gerçek şema + gerçek hacim motoruyla, KONF.fiyatKurus
   üzerinden (Worker ile AYNI yol). Üç çapa noktası BİREBİR, çapa dışı seçimler
   (flanş/eleman) tutarı OYNATIR — yoksa "flanşlı" bedava olurdu. */
(function () {
  var rSema = JSON.parse(fs.readFileSync(
    path.join(URUN_DIR, "olcuye-ozel-rulman.json"), "utf8"));
  var vars = KONF.varsayilanDegerler(rSema);
  function izgara(ad, v) {
    for (var i = 0; i < rSema.parametreler.length; i++) {
      if (rSema.parametreler[i].ad === ad) {
        var a = rSema.parametreler[i].adim;
        return a ? Math.round(v / a) * a : v;
      }
    }
    return v;
  }
  // ORANTILI/VARSAYILAN konfigürasyon: şemanın kendi varsayılanları + çapla
  // ölçeklenen iki ölçü (ic_cap = çap/3, genislik = çap×0,3, şema ızgarasında).
  function ref(dis) {
    var p = {};
    for (var k in vars) { if (vars.hasOwnProperty(k)) { p[k] = vars[k]; } }
    p.dis_cap = dis;
    p.ic_cap = izgara("ic_cap", dis / 3);
    p.genislik = izgara("genislik", dis * 0.3);
    return p;
  }
  function fy(p, m, r) {
    return KONF.fiyatKurus(rSema, p, m || "PLA", r || "Siyah",
                           { secenek: SECENEK, hacim: HACIM });
  }
  esit("rulman çapa: 60/80/100 mm varsayılan ayarlarda 600/800/1000 TL",
       [fy(ref(60)), fy(ref(80)), fy(ref(100))], [60000, 80000, 100000]);
  esit("rulman çapa: ölçülen noktalar şemaya göre GEÇERLİ konfigürasyon",
       [60, 80, 100].map(function (d) { return KONF.dogrula(rSema, ref(d)).gecerli; }),
       [true, true, true]);
  esit("rulman çapa: eğri çapla KESİN ARTAN (28→100 mm), doygunluk YOK",
       [28, 30, 40, 50, 60, 80, 100].map(function (d) { return fy(ref(d)); }),
       [28000, 30000, 40000, 50000, 60000, 80000, 100000]);
  // ZEMİN: 200,00 TL altına inilmez (ince/geniş delikli uçlarda oran 1'in altına iner).
  var ince = { ic_cap: 33.5, dis_cap: 41.5, genislik: 5, eleman: "bilya",
               bosluk: 0.15, flans: "yok" };
  esit("rulman zemin: en ince meşru konfigürasyon geçerli", KONF.dogrula(rSema, ince).gecerli, true);
  esit("rulman zemin: taban 200,00 TL altına inilmez", fy(ince), 20000);
  // MODÜLASYON: çapa dışı seçimler BEDAVA değil.
  var f100 = ref(100); f100.flans = "var";
  esit("rulman modülasyon: 100 mm flanşlı > flanşsız", fy(f100) > fy(ref(100)), true);
  var mak60 = ref(60); mak60.eleman = "makara";
  var tut60 = ref(60); tut60.eleman = "tutmali";
  esit("rulman modülasyon: 60 mm bilya/makara/tutmalı üç AYRI tutar",
       [fy(ref(60)), fy(mak60), fy(tut60)], [60000, 63332, 66402]);
  // Malzeme/renk çarpanları çapa kolunda da AYNI sırada uygulanır.
  esit("rulman 100 mm ASA/Diğer = 1000 × 1,60 × 1,15",
       fy(ref(100), "ASA", "Diğer"), 184000);
  // TAVAN çapaya görelidir (taban × 3 DEĞİL) ve meşru işi kırpmaz.
  var bag = KONF.fiyatBaglami(rSema, ref(100), HACIM);
  esit("rulman tavanı: 100 mm'de çapanın 20 katı (dev hacim)",
       SECENEK.parametrikFiyatKurus("rulman", rSema.tabanFiyatTL, rSema.tabanHacimMm3,
                                    1e12, "PLA", "Siyah", bag), 2000000);
}());

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

/* ==== SAKSI / VAZO (olcuye-ozel-saksi-vazo) — mimar kararı KraL halef-27, 13 Eki 2026 ====
   Biçim: TEK sarı seri kaydı; S/M/L = konfigüratör HAZIR ÖN-AYARI (şema `onAyarlar`).
   Fiyat: temel = max(400 TL, 800 TL × hacim / M hacmi) × malzeme × renk, 3× taban tavanı;
   alt tabak = SABİT kademe eki (+100/+150/+200 TL, alt çapa en yakın boy, eşitlikte büyük).
   Aile BUGÜN KAPALI (kisitli şema → parite kaydı bekler) — fiyat kuralı "AÇILIŞ
   SİMÜLASYONU"nda ölçülür: secenekler.js'in TAZE bir kopyasında yalnız allowlist'e
   `saksi` eklenir; formül/kademe/tavan kodu CANLI dosyanın AYNISIDIR. Mutant sürücüsü:
   jenerator/test/saksi-fiyat-mutasyon.js (bu dosyayı mutant kopyalarla koşar). */
var saksiSema = JSON.parse(fs.readFileSync(
  path.join(URUN_DIR, "olcuye-ozel-saksi-vazo.json"), "utf8"));
var saksiVd = KONF.varsayilanDegerler(saksiSema);
function saksiSet(ek) { return Object.assign({}, saksiVd, ek || {}); }
var saksiOA = {};
(saksiSema.onAyarlar || []).forEach(function (oa) {
  saksiOA[oa.ad] = KONF.onAyarDegerleri(saksiSema, oa.ad);
});

// --- A. HACİM + KALİBRASYON (TeKiN §2 analitik formül) ---
// GERÇEK STL (OpenSCAD render, saksi_vazo.scad, $fn=96) — jenerator/test/
// kalibrasyon-referans.json "saksi" (kalibrasyon-referans-uret.py --aile saksi, 13 Eki).
// Analitik formül çokgen yaklaşımını BİLEREK içermez (fiyat referansı analitiktir):
// beklenen fark ≈ 1 − (96/2π)·sin(2π/96) = %0,071.
var SAKSI_KALIB = JSON.parse(fs.readFileSync(
  path.join(__dirname, "kalibrasyon-referans.json"), "utf8")).aileler.saksi;
var saksiM = KONF.hacimMm3(saksiSema, saksiVd, HACIM);
esit("saksı M (140/100/120, Ø12) analitik hacim = 137.645,99 mm³",
     Math.round(saksiM * 100) / 100, 137645.99);
esit("saksı tabanHacimMm3 = fn(varsayılan)",
     Math.abs(saksiM - saksiSema.tabanHacimMm3) < 1e-6, true);
esit("saksı kalibrasyon fikstürü var + set0 = varsayılan (M)",
     !!SAKSI_KALIB && JSON.stringify(SAKSI_KALIB.setler[0].parametreler) ===
       JSON.stringify(saksiVd), true);
esit("saksı M analitik ↔ gerçek STL ±%0,1 (mimar kalibrasyon şartı)",
     Math.abs(saksiM - SAKSI_KALIB.setler[0].referansMm3) /
       SAKSI_KALIB.setler[0].referansMm3 <= 0.001, true);
esit("saksı TÜM kalibrasyon setleri analitik ↔ STL ±%0,2 (köşeler dahil)",
     SAKSI_KALIB.setler.filter(function (s) {
       var h = HACIM.saksi(s.parametreler);
       return !(Math.abs(h - s.referansMm3) / s.referansMm3 <= 0.002);
     }).length, 0);
// Tabak: aynı aile fonksiyonu, parca="tabak" kolu (ürün şemasında `parca` YOK).
// GERÇEK STL (OpenSCAD, parca="tabak", alt çap 70/100/130, duvar 2,4, taban 3, h 18).
// Ölçüm 13 Eki 2026 (OpenSCAD 2021.01 render, ağır-iş kapısı; geçici ölçüm betiği silindi).
var TABAK_STL = [21917.6891, 38163.8265, 58648.0810];
var tabakJs = [70, 100, 130].map(function (a) {
  return HACIM.saksi({ parca: "tabak", alt_cap: a, duvar: 2.4, taban: 3,
                       tabak_yuksekligi: 18 });
});
esit("tabak S/M/L analitik ↔ gerçek STL ±%0,1",
     tabakJs.map(function (h, i) { return Math.abs(h - TABAK_STL[i]) / TABAK_STL[i] <= 0.001; }),
     [true, true, true]);

// --- B. ŞEMA: ön-ayarlar, sınırlar, kısıtlar ---
esit("saksı ön-ayar adları S/M/L", Object.keys(saksiOA), ["S", "M", "L"]);
esit("saksı ön-ayarlar şemaya göre GEÇERLİ",
     ["S", "M", "L"].map(function (k) { return KONF.dogrula(saksiSema, saksiOA[k]).gecerli; }),
     [true, true, true]);
esit("saksı M ön-ayarı = şema varsayılanı (taban hacmi = M)",
     JSON.stringify(saksiOA.M), JSON.stringify(saksiVd));
esit("saksı ön-ayar alt tabak seçimini EZMEZ (müşteri seçimi kalır)",
     KONF.onAyarDegerleri(saksiSema, "L", saksiSet({ tabak: "var" })).tabak, "var");
esit("saksı ön-ayar eşleşmesi (düğme vurgusu)",
     [KONF.onAyarEslesen(saksiSema, saksiOA.S), KONF.onAyarEslesen(saksiSema, saksiOA.L),
      KONF.onAyarEslesen(saksiSema, saksiSet({ yukseklik: 121 }))], ["S", "L", null]);
esit("bilinmeyen ön-ayar -> null", KONF.onAyarDegerleri(saksiSema, "XL"), null);
// TeKiN §1 sınırları AYNEN: her sayısal eksen min−adım / max+adım RED, min/max KABUL.
var SAKSI_SINIR = { ust_cap: [60, 260], alt_cap: [40, 200], yukseklik: [50, 300],
                    duvar: [1.6, 4], taban: [2, 5], drenaj_capi: [6, 20],
                    tabak_yuksekligi: [12, 30] };
esit("saksı şema sınırları TeKiN §1 ile birebir",
     Object.keys(SAKSI_SINIR).map(function (ad) {
       var p = saksiSema.parametreler.filter(function (x) { return x.ad === ad; })[0];
       return [p.min, p.max];
     }), Object.keys(SAKSI_SINIR).map(function (ad) { return SAKSI_SINIR[ad]; }));
var sinirDisi = [];
Object.keys(SAKSI_SINIR).forEach(function (ad) {
  var p = saksiSema.parametreler.filter(function (x) { return x.ad === ad; })[0];
  [p.min - p.adim, p.max + p.adim].forEach(function (v) {
    var s = saksiSet(); s[ad] = Math.round(v * 1000) / 1000;
    if (ad === "ust_cap" && v > p.max) { s.alt_cap = 40; s.yukseklik = 300; }
    if (KONF.dogrula(saksiSema, s).gecerli) { sinirDisi.push(ad + "=" + s[ad]); }
  });
});
esit("saksı sınır dışı (min−adım, max+adım) HEPSİ RED", sinirDisi, []);
esit("saksı secim dışı değer RED (drenaj/tabak)",
     [KONF.dogrula(saksiSema, saksiSet({ drenaj: 1 })).gecerli,
      KONF.dogrula(saksiSema, saksiSet({ tabak: "belki" })).gecerli], [false, false]);
esit("saksı alt çap > üst çap RED, eşit KABUL (düz silindir)",
     [KONF.dogrula(saksiSema, saksiSet({ ust_cap: 100, alt_cap: 101 })).gecerli,
      KONF.dogrula(saksiSema, saksiSet({ ust_cap: 100, alt_cap: 100 })).gecerli],
     [false, true]);
// Eğim kısıtı katsayısı = 1 / (2·tan 40°) — üretecin assert'iyle AYNI sınır.
var egimKs = saksiSema.kisitlar.filter(function (k) { return k.parametre === "yukseklik"; })[0];
esit("saksı eğim katsayısı 1/(2·tan40°)",
     Math.abs(egimKs.min.terimler.ust_cap - 1 / (2 * Math.tan(40 * Math.PI / 180))) < 1e-12 &&
     egimKs.min.terimler.alt_cap === -egimKs.min.terimler.ust_cap, true);
// PARİTE (ızgaranın TAMAMI, eğim ekseni): şema kısıtı ↔ üretecin assert'i
// `atan((R_ust−R_alt)/yukseklik) <= 40` — çap farkı 0..220 × yükseklik 50..300.
var egimAyrisma = 0, egimNokta = 0;
for (var dCap = 0; dCap <= 220; dCap++) {
  for (var yk = 50; yk <= 300; yk++) {
    var altC = dCap <= 200 ? 60 : 40;   // ust_cap >= 60 sema alt siniri
    var se = saksiSet({ alt_cap: altC, ust_cap: altC + dCap, yukseklik: yk });
    var motor = Math.atan(dCap / 2 / yk) * 180 / Math.PI <= 40;
    if (KONF.dogrula(saksiSema, se).gecerli !== motor) { egimAyrisma++; }
    egimNokta++;
  }
}
esit("saksı eğim kısıtı ↔ üretec assert paritesi (55.471 nokta, ayrışma 0)",
     [egimNokta, egimAyrisma], [55471, 0]);
esit("saksı eğim sınırı: Δçap 220'de yükseklik 131 RED / 132 KABUL",
     [KONF.dogrula(saksiSema, saksiSet({ ust_cap: 260, alt_cap: 40, yukseklik: 131 })).gecerli,
      KONF.dogrula(saksiSema, saksiSet({ ust_cap: 260, alt_cap: 40, yukseklik: 132 })).gecerli],
     [false, true]);
// Drenaj assert'i (drenaj_capi/2 < alt_cap/2 − duvar) KUTU İÇİNDE HİÇ BAĞLAMAZ:
// en kötü köşe Ø20 delik (r 10) ↔ alt 40 / duvar 4 (iç r 16) → kısıt YAZILMADI.
esit("saksı drenaj assert'i kutu içinde boş (en kötü köşe 10 < 16)",
     20 / 2 < 40 / 2 - 4, true);
esit("saksı şemasında tam 2 kısıt (alt≤üst + eğim)", saksiSema.kisitlar.length, 2);

// --- C. GERÇEK DURUM: aile KAPALI (allowlist'te yok) → TUTAR YOK ---
esit("saksı hacim allowlist'inde DEĞİL (kapalı)",
     SECENEK.hacimDogrulanmisMi(saksiSema.hacimFormulu), false);
esit("saksı kapalıyken M fiyatı null (kart kapalı, WhatsApp kanalı)",
     KONF.fiyatKurus(saksiSema, saksiVd, "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }),
     null);

// --- D. AÇILIŞ SİMÜLASYONU: fiyat kuralının kendisi ---
var SAKSI_ACIK = secenekYukle();
SAKSI_ACIK.HACIM_DOGRULANMIS_AILELER.saksi = 0;
function sfy(d, m, r, sec) {
  return KONF.fiyatKurus(saksiSema, d, m || "PLA", r || "Siyah",
                         { secenek: sec || SAKSI_ACIK, hacim: HACIM });
}
esit("saksı kural kaydı: zemin 400 TL, sabit 180 TL (doğru), taban 800 TL",
     [SAKSI_ACIK.aileFiyatKurali("saksi").zeminTL, SAKSI_ACIK.aileFiyatKurali("saksi").sabitTL,
      saksiSema.tabanFiyatTL], [400, 180, 800]);
// Ön-ayar fiyatları kararı ≈500 / 800 / ≈1.250 TL (mimar hükmü 13 Eki: sabitTL 180).
// Elle sağlama: 180 + 620 × 71.043,60 / 137.645,99 = 500,00 ·
// 180 + 620 × 237.399,73 / 137.645,99 = 1.249,32. (Saf oran — sabitTL 0 — 412,91 /
// 1.379,77 verirdi; mutant M4 o geri dönüşü bu satırda KIRMIZI yakar.)
esit("saksı ön-ayar fiyatı S/M/L (PLA/Siyah, tabaksız, kuruş)",
     [sfy(saksiOA.S), sfy(saksiOA.M), sfy(saksiOA.L)], [50000, 80000, 124932]);
// ZEMİN: en küçük meşru saksı 400,00 TL'nin altına inmez; çarpanlar zemine uygulanır.
var saksiMin = saksiSet({ ust_cap: 60, alt_cap: 40, yukseklik: 50, duvar: 1.6, taban: 2,
                          drenaj: "var", drenaj_capi: 6 });
esit("saksı zemin seti geçerli + oran zeminin ALTINDA (test boş yeşil yanmasın)",
     [KONF.dogrula(saksiSema, saksiMin).gecerli,
      180 + 620 * KONF.hacimMm3(saksiSema, saksiMin, HACIM) / saksiSema.tabanHacimMm3 < 400],
     [true, true]);
esit("saksı ZEMİN: en küçük saksı = 400,00 TL (PLA) · 520,00 TL (PETG ×1,30)",
     [sfy(saksiMin), sfy(saksiMin, "PETG")], [40000, 52000]);
// ALT TABAK: sabit kademe eki, çarpan dışı, tavan sonrası.
esit("saksı alt tabak eki S/M/L ön-ayarında +100 / +150 / +200 TL",
     ["S", "M", "L"].map(function (k) {
       var t = Object.assign({}, saksiOA[k], { tabak: "var" });
       return sfy(t) - sfy(saksiOA[k]);
     }), [10000, 15000, 20000]);
esit("saksı tabak kademesi serbest ölçüde EN YAKIN boy (eşitlikte büyük)",
     [40, 84, 85, 114, 115, 200].map(function (a) {
       return SAKSI_ACIK.ekParcaKademesi(SAKSI_ACIK.aileFiyatKurali("saksi").ekParca,
         { parametreler: { tabak: "var", alt_cap: a } }).boy;
     }), ["S", "S", "M", "M", "L", "L"]);
esit("saksı tabak eki malzeme çarpanı DIŞINDA (ASA/Diğer M + tabak = M×1,84 + 150)",
     sfy(Object.assign({}, saksiOA.M, { tabak: "var" }), "ASA", "Diğer"),
     Math.round(80000 * 1.6 * 1.15) + 15000);
// TAVAN: 3× taban (2.400 TL) — en büyük saksı orantıda ~6.083 TL olurdu, KIRPILIR.
var saksiMax = saksiSet({ ust_cap: 260, alt_cap: 200, yukseklik: 300, duvar: 4, taban: 5,
                          drenaj: "yok", tabak: "var" });
esit("saksı TAVAN: en büyük saksı 2.400 TL + tabak 200 TL (eki tavan dışı)",
     [KONF.dogrula(saksiSema, saksiMax).gecerli, sfy(saksiMax)], [true, 260000]);
// FAIL-CLOSED: bağlamsız çağrı / tanınmayan tabak değeri tutar ÜRETMEZ.
esit("saksı bağlamsız çağrı null (ek parça kararı ölçüye bağlı)",
     SAKSI_ACIK.parametrikFiyatKurus("saksi", 800, saksiSema.tabanHacimMm3, saksiM,
                                     "PLA", "Siyah"), null);
esit("saksı tanınmayan tabak değeri null",
     sfy(saksiSet({ tabak: "belki" })), null);
esit("saksı kuralı başka aileye SIZMAZ (kutu bağlamsız hâlâ 10800)",
     SAKSI_ACIK.parametrikFiyatKurus("kutu", 100, 1000, 1080, "PLA", "Siyah"), 10800);

// --- E. İSTEMCİ = SUNUCU (Worker shop/src/parametrik.js, aynı açılış kopyasıyla) ---
import("file://" + path.resolve(PARAMETRIK_YOL)).then(function (PAR) {
  var ayrisan = [], sayac = 0;
  ["S", "M", "L"].forEach(function (k) {
    ["yok", "var"].forEach(function (tb) {
      ["PLA", "PETG", "ASA"].forEach(function (m) {
        ["Siyah", "Diğer"].forEach(function (r) {
          var d = Object.assign({}, saksiOA[k], { tabak: tb });
          var istemci = sfy(d, m, r);
          var sunucu = PAR.parametrikHesapla(
            { id: saksiSema.id, malzeme: m, renk: r, parametreler: d }, SAKSI_ACIK, saksiSema);
          sayac++;
          if (!(istemci > 0) || sunucu.birimKurus !== istemci) {
            ayrisan.push(k + "/" + tb + "/" + m + "/" + r + ": " + istemci + " ≠ " +
                         JSON.stringify(sunucu.birimKurus));
          }
        });
      });
    });
  });
  esit("saksı istemci = sunucu (36 kombinasyon, ayrışma 0)", [sayac, ayrisan], [36, []]);
  var red = PAR.parametrikHesapla({ id: saksiSema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: saksiSet({ ust_cap: 100, alt_cap: 120 }) }, SAKSI_ACIK, saksiSema);
  esit("saksı sınır dışı ölçü sunucuda RED (sepet 400)", red.hata, "parametre-araligi");
  var kapali = PAR.parametrikHesapla({ id: saksiSema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: saksiVd }, SECENEK, saksiSema);
  esit("saksı GERÇEK durumda sunucu tutar üretmez (hacim-dogrulanmamis)",
       kapali.hata, "hacim-dogrulanmamis");
  process.exit(hata ? 1 : 0);
}, function (e) {
  console.log("  [HATA] parametrik.js yüklenemedi: " + e.message);
  process.exit(1);
});
