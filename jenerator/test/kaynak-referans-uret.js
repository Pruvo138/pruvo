#!/usr/bin/env node
/* KALIBRASYON KAYNAK REFERANSI URETECI — kabul testi DEGIL, fikstur ureteci.

   NE URETIR: jenerator/test/kaynak-referans.json — kapsamdaki her aile icin
   deterministik sema izgarasindan uretilmis parametre setleri ve o setlerin
   KALIBRASYON KAYNAGINDAN (kardes ev dogrulama/test/aileler/<aile>.js)
   hesaplanan hacimleri + kapsam DISI birakilan ailelerin OLCULMUS gerekcesi.

   NEDEN: kalibrasyon-senkron.js'in 2. katmani (kaynak senkronu) kardes ev dizini
   olmadan YAPISAL olarak kosamaz; CI fresh checkout'unda o kol SESSIZCE atlanir.
   Olculdu (3 Agu 2026): `yay` ailesine konan +%5 tahsilat mutanti kardes ev VARKEN
   kirmizi yaniyor (26 kontrol), kardes ev YOKKEN tamamen YESIL geciyor.

   🔴 HACIM.JS'TEN URETMEZ. Degerler YALNIZ kalibrasyon kaynagindan gelir; aksi
   halde test kendi kendini onaylardi ([[anahat-referans-tautolojisi]]).
   🔴 CI'DA KOSMAZ (ci-kapsam-test.py MUAF, uretec sinifi): kosarsa kabul testinin
   karsilastirdigi referansi EZER.

   KAPSAM OLCUTU (iki sart, IKISI DE olculur ve dosyaya yazilir):
     (1) esleme/<aile>.json `motor` == "pruvo" — yani ailenin kalibrasyon otoritesi
         KARDES EVDEKI uretec kaynagidir. `motor` == "uretim" ailelerinde hacim.js
         GIZLI uretim motoruna kalibredir; kardes evdeki dosya BASKA bir modeldir,
         onu referans almak SAHTE-KIRMIZI uretir (olculdu: izgara %150,3 · pervane
         %62,1 · kayis %37,6 · petek %37,5 · huni %32,4 · kasnak %19,5 · rulman
         %14,0 · oring %6,7 sapma — hepsi MESRU).
     (2) bugunku hacim.js kaynakla <= tolerans ortusuyor. Ortusmeyen motor=pruvo
         ailesi (rampa · profil) kapsam DISI kalir ve gerekcesi OLCULEN SAYIYLA
         dosyaya yazilir — susturma degil, ACIK KALEM kaydidir.

   Kullanim: node jenerator/test/kaynak-referans-uret.js [--yaz]
   --yaz olmadan yalniz OZET basar (dosya YAZILMAZ).
*/
"use strict";
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const TEST_DIR = __dirname;
const CIKTI = path.join(TEST_DIR, "kaynak-referans.json");
const SET_SAYISI = 25;
const TOHUM = 424242;
const TOLERANS_YUZDE = 0.01;   // kalibrasyon-senkron.js :: KAYNAK_YUZDE ile AYNI

const dogrulamaDir = process.env.PRUVO_DOGRULAMA_DIR ||
  path.join(process.env.HOME || "", "dev", "pruvo-jenerator", "dogrulama");
if (!fs.existsSync(dogrulamaDir)) {
  console.error("OLCULEMEDI: kalibrasyon kaynagi yok: " + dogrulamaDir);
  process.exit(2);
}

// kalibrasyon-senkron.js 2. katmanindaki LCG ile AYNI; tohum AILE BASINA sifirlanir
// (boylece kapsam listesi degisince onceki ailelerin setleri KAYMAZ).
function setUretici() {
  let tohum = TOHUM;
  function rasgele() {
    tohum = (tohum * 1103515245 + 12345) % 2147483648;
    return tohum / 2147483648;
  }
  return function (sema) {
    const s = {};
    sema.parametreler.forEach(function (p) {
      if (p.tip === "sayi") {
        const adim = p.adim || 1;
        const n = Math.round((p.max - p.min) / adim);
        s[p.ad] = Math.round((p.min + Math.floor(rasgele() * (n + 1)) * adim) * 1e6) / 1e6;
      } else if (p.tip === "secim") {
        const secenekler = p.secenekler.map(function (x) {
          return typeof x === "object" ? x.deger : x;
        });
        s[p.ad] = secenekler[Math.floor(rasgele() * secenekler.length)];
      } else {
        s[p.ad] = p.varsayilan || "";
      }
    });
    return s;
  };
}

const HACIM = require(path.join(TEST_DIR, "..", "hacim.js"));
const aileler = fs.readdirSync(path.join(TEST_DIR, "esleme"))
  .filter(function (f) { return f.endsWith(".json"); })
  .map(function (f) { return f.slice(0, -5); }).sort();

const cikti = {
  _not: "URETEC: jenerator/test/kaynak-referans-uret.js — ELLE kosulur, CI'da KOSMAZ. " +
    "Hacimler KALIBRASYON KAYNAGINDAN (kardes ev) gelir, hacim.js'ten DEGIL. " +
    "Kapsam disi aileler gerekce + OLCULEN sapma ile asagida beyan edilir.",
  uretildi: new Date().toISOString().slice(0, 10),
  node: process.version,
  tohum: TOHUM,
  set_sayisi: SET_SAYISI,
  tolerans_yuzde: TOLERANS_YUZDE,
  aileler: {},
  disi_birakilan: {}
};

let toplamSet = 0;
aileler.forEach(function (aile) {
  const kaynakYol = path.join(dogrulamaDir, "test", "aileler", aile + ".js");
  const esleme = JSON.parse(fs.readFileSync(
    path.join(TEST_DIR, "esleme", aile + ".json"), "utf8"));
  const semaYol = path.join(TEST_DIR, "..", "urunler", esleme.urunId + ".json");
  if (!fs.existsSync(kaynakYol) || !fs.existsSync(semaYol)) {
    console.error("OLCULEMEDI: " + aile + " icin kaynak ya da sema yok");
    process.exit(2);
  }
  const govde = fs.readFileSync(kaynakYol, "utf8");
  const sandbox = { Math: Math };
  vm.runInNewContext(govde + "\n;__fn = " + aile + ";", sandbox);
  const refFn = sandbox.__fn;
  const sema = JSON.parse(fs.readFileSync(semaYol, "utf8"));
  const fonksiyon = esleme.fonksiyon || aile;
  const canliFn = HACIM[fonksiyon];
  const uret = setUretici();

  const varsayilan = {};
  sema.parametreler.forEach(function (p) { varsayilan[p.ad] = p.varsayilan; });

  const setler = [];
  let enKotu = 0;
  let asan = 0;
  for (let i = 0; i < SET_SAYISI; i++) {
    const p = uret(sema);
    const h = refFn(p);
    if (!isFinite(h) || h <= 0) {
      console.error("OLCULEMEDI: " + aile + " set" + i + " gecersiz hacim " + h);
      process.exit(2);
    }
    const c = canliFn(p);
    const sapma = Math.abs(c - h) / h * 100;
    if (sapma > enKotu) enKotu = sapma;
    if (sapma > TOLERANS_YUZDE) asan++;
    setler.push({ p: p, hacimMm3: h });
  }
  const taban = refFn(varsayilan);
  if (!isFinite(taban) || taban <= 0) {
    console.error("OLCULEMEDI: " + aile + " taban hacmi gecersiz " + taban);
    process.exit(2);
  }
  const tabanSapma = Math.abs(canliFn(varsayilan) - taban) / taban * 100;
  if (tabanSapma > enKotu) enKotu = tabanSapma;

  const motor = esleme.motor || "?";
  if (motor !== "pruvo") {
    cikti.disi_birakilan[aile] = {
      sebep: "motor=" + motor + " — hacim.js GIZLI uretim motoruna kalibre; " +
        "kardes evdeki dosya BASKA bir model, referans alinamaz (sahte-kirmizi).",
      olculen_en_kotu_sapma_yuzde: Number(enKotu.toFixed(4)),
      tolerans_asan_set: asan + "/" + SET_SAYISI
    };
  } else if (asan > 0) {
    cikti.disi_birakilan[aile] = {
      sebep: "motor=pruvo AMA hacim.js bugun kalibrasyon kaynagindan SAPIYOR — " +
        "ACIK KALEM (kapsama alinmasi ONCE sapmanin onarilmasini gerektirir).",
      olculen_en_kotu_sapma_yuzde: Number(enKotu.toFixed(4)),
      tolerans_asan_set: asan + "/" + SET_SAYISI
    };
  } else {
    toplamSet += setler.length;
    cikti.aileler[aile] = {
      fonksiyon: fonksiyon,
      urunId: esleme.urunId,
      motor: motor,
      kaynak_sha256: crypto.createHash("sha256").update(govde).digest("hex"),
      taban_hacim_mm3: taban,
      setler: setler
    };
  }
  console.log(aile.padEnd(10) + " motor=" + motor.padEnd(7) +
    " en kotu %" + enKotu.toFixed(4).padStart(9) +
    "  asan " + asan + "/" + SET_SAYISI +
    "  -> " + (cikti.aileler[aile] ? "KAPSAMDA" : "DISI"));
});

const kapsam = Object.keys(cikti.aileler).length;
const disi = Object.keys(cikti.disi_birakilan).length;
console.log("KAPSAM " + kapsam + " aile / " + toplamSet + " set · DISI " +
  disi + " aile (gerekce+olcum dosyada)");
if (kapsam + disi !== aileler.length) {
  console.error("OLCULEMEDI: aile sayisi tutmuyor");
  process.exit(2);
}
if (process.argv.indexOf("--yaz") >= 0) {
  fs.writeFileSync(CIKTI, JSON.stringify(cikti, null, 1) + "\n");
  console.log("YAZILDI: " + CIKTI);
} else {
  console.log("(--yaz verilmedi, dosya yazilmadi)");
}
