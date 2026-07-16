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
