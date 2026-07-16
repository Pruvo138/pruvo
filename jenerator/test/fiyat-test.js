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

// --- #2 Fiyat orantısı ---
// Taban 100 TL, hacim +%8, ASA (×1.60), Diğer renk (×1.15) -> 198,72 TL birebir.
esit("bileşik örnek 100×1.08×1.60×1.15 (kuruş)",
     SECENEK.parametrikFiyatKurus(100, 1000, 1080, "ASA", "Diğer"), 19872);
esit("bileşik örnek metin", SECENEK.kurusMetni(19872), "198,72 TL");
// Taban ×1.08 hacim, PLA/Siyah -> TAM ×1.08 (yuvarlama yok, kuruş korunur).
esit("saf hacim oranı ×1.08", SECENEK.parametrikFiyatKurus(100, 1000, 1080, "PLA", "Siyah"), 10800);
esit("kuruş kesirli örnek 250×1.037", SECENEK.parametrikFiyatKurus(250, 1000, 1037, "PLA", "Siyah"), 25925);
esit("kuruş metni 259,25", SECENEK.kurusMetni(25925), "259,25 TL");
// ABS ve Karbon KALDIRILDI (Okan, 16 Tem) — mühendislik malzemeleri WhatsApp'tan.
esit("filament katsayıları PLA/PETG/TPU/ASA",
     ["PLA", "PETG", "TPU", "ASA"].map(function (m) {
       return SECENEK.parametrikFiyatKurus(100, 1000, 1000, m, "Siyah");
     }), [10000, 13000, 15500, 16000]);
// Taban fiyat yoksa fiyat yok ("—" davranışının çekirdeği).
esit("tabanFiyat null -> fiyat null", SECENEK.parametrikFiyatKurus(null, 1000, 1080, "ASA", "Diğer"), null);

// --- ZEMİN (Okan kuralı, 16 Tem — tools/paket-sari-fiyat.md) ---
// fiyat = taban × max(1, hacim/tabanHacim) × filament × renk.
// Taban fiyat ZEMİNDİR: varsayılandan küçük her ölçüde çarpan 1'e sabitlenir,
// filament/renk çarpanları zemin fiyata AYNEN uygulanır. Basamak yok: taban
// üstünde sürekli oran, kuruş korunur.
esit("zemin: hacim tabanın yarısı -> taban aynen (PLA/Siyah)",
     SECENEK.parametrikFiyatKurus(100, 1000, 500, "PLA", "Siyah"), 10000);
esit("zemin: sınırın hemen altı -> taban",
     SECENEK.parametrikFiyatKurus(100, 1000, 999.9, "PLA", "Siyah"), 10000);
esit("zemin: kuruş korunur (333 zemin × PETG 1.30 = 432,90)",
     SECENEK.parametrikFiyatKurus(333, 1000, 500, "PETG", "Siyah"), 43290);
esit("zemin: filament+renk zemine uygulanır (100×1×1.60×1.15)",
     SECENEK.parametrikFiyatKurus(100, 1000, 500, "ASA", "Diğer"), 18400);
// BÜYÜME: taban üstünde hacimle monoton artış (zemin büyümeyi bozmaz).
var buyume = [1000, 1080, 2000, 5000].map(function (h) {
  return SECENEK.parametrikFiyatKurus(100, 1000, h, "PLA", "Siyah");
});
esit("büyüme: taban üstü sürekli oran", buyume, [10000, 10800, 20000, 50000]);
esit("büyüme: sıkı artan", buyume.every(function (v, i) {
  return i === 0 || v > buyume[i - 1];
}), true);

// --- TABAN FİYATLAR (Okan KESİN tablosu — tools/paket-sari-fiyat.md) ---
// Vida istisnası KALKTI (tools/paket-vida-fiyat.md): hacim.js vida üretim
// motorunun STL hacimlerine kalibre edildi (kalibrasyon-referans.json "vida",
// 77 set ≤%3) — 18/18 aile dolu, vida tabanı 100 TL (Okan kesin değeri).
var TABAN_FIYATLAR = {
  "kisiye-ozel-jeton-cip-madalyon": 150,
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
  "ozel-disli-kramayer-uretimi": 300
};
var URUN_DIR = path.join(KOK, "jenerator", "urunler");
var semaDosyalari = fs.readdirSync(URUN_DIR).filter(function (f) { return /\.json$/.test(f); });
esit("şema sayısı 18", semaDosyalari.length, 18);
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
  esit("zemin PLA/Siyah = taban: " + id,
       SECENEK.parametrikFiyatKurus(taban, s.tabanHacimMm3, h, "PLA", "Siyah"), taban * 100);
  esit("zemin PETG = taban×1.30: " + id,
       SECENEK.parametrikFiyatKurus(taban, s.tabanHacimMm3, h, "PETG", "Siyah"),
       Math.round(taban * 130));
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
var denemeSema = Object.assign({}, oringSema, { tabanFiyatTL: 100 });
esit("varsayılanda fiyat = taban (PLA/Siyah)",
     KONF.fiyatKurus(denemeSema, vd, "PLA", "Siyah", { secenek: SECENEK, hacim: HACIM }), 10000);

process.exit(hata ? 1 : 0);
