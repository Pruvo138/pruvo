#!/usr/bin/env node
/* KALIBRASYON SENKRON TESTI — canli jenerator/hacim.js vs olcuye gore
   uretec v2 kalibre referanslari (konektor + braket + disli) + yeni sari
   aileler 1. dalga (adaptor + kutu + kavanoz, 2026-07-17).

   Iki katman:
   1) DONDURULMUS REFERANS (her yerde kosar, openscad gerekmez):
      kalibrasyon-referans.json'daki gercek OpenSCAD STL hacimlerine karsi
      canli hacim.js kapali-formu, sapma <= %3. Ayrica urunler/<id>.json
      tabanHacimMm3 == fn(varsayilan) (%0.1).
   2) DOGRULAMA KAYNAGI SENKRONU (dizin varsa): ~/dev/pruvo-jenerator/
      dogrulama/test/aileler/{konektor,braket}.js v2 kalibre fonksiyonlari
      ile canli fonksiyonlar deterministik sema gridinde birebir (<= %0.5)
      karsilastirilir — el kopyasi surüklenirse burasi kirmizi yanar.

   Kirmizi kaniti (senkron oncesi kodda kosum):
     git show <eski>:jenerator/hacim.js > /tmp/eski-hacim.js
     PRUVO_HACIM_YOL=/tmp/eski-hacim.js node jenerator/test/kalibrasyon-senkron.js
*/
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const TEST_DIR = __dirname;
const SINIR_YUZDE = 3.0;
const SENKRON_YUZDE = 0.5;
const TABAN_TOLERANS = 0.001;

const hacimYol = process.env.PRUVO_HACIM_YOL ||
  path.join(TEST_DIR, "..", "hacim.js");
const HACIM = require(path.resolve(hacimYol));
console.log("hacim.js: " + hacimYol);

let kirmizi = 0;

function kontrol(ok, satir) {
  console.log("  [" + (ok ? "OK " : "SAP") + "] " + satir);
  if (!ok) kirmizi++;
}

// ---------- 1) dondurulmus referans ----------
const REF = JSON.parse(fs.readFileSync(
  path.join(TEST_DIR, "kalibrasyon-referans.json"), "utf8"));
console.log("\n== 1) dondurulmus STL referanslari (sinir <=%" +
  SINIR_YUZDE + ") ==");
for (const aile of Object.keys(REF.aileler)) {
  const veri = REF.aileler[aile];
  const fn = HACIM[veri.fonksiyon];
  if (typeof fn !== "function") {
    kontrol(false, aile + ": hacim.js'te '" + veri.fonksiyon + "' yok");
    continue;
  }
  let enKotu = 0;
  veri.setler.forEach(function (s, i) {
    const js = fn(s.parametreler);
    const sapma = Math.abs(js - s.referansMm3) / s.referansMm3 * 100;
    if (sapma > enKotu) enKotu = sapma;
    if (sapma > SINIR_YUZDE) {
      kontrol(false, aile + " set" + i + " js=" + js.toFixed(1) +
        " referans=" + s.referansMm3.toFixed(1) +
        " sapma=%" + sapma.toFixed(2) + "  (" +
        JSON.stringify(s.parametreler) + ")");
    }
  });
  kontrol(enKotu <= SINIR_YUZDE, aile + ": " + veri.setler.length +
    " set, en kotu sapma %" + enKotu.toFixed(2));

  // tabanHacimMm3 tutarliligi
  const sema = JSON.parse(fs.readFileSync(path.join(
    TEST_DIR, "..", "urunler", veri.urunId + ".json"), "utf8"));
  const varsayilan = {};
  sema.parametreler.forEach(function (p) { varsayilan[p.ad] = p.varsayilan; });
  const taban = fn(varsayilan);
  const fark = Math.abs(taban - sema.tabanHacimMm3) / sema.tabanHacimMm3;
  kontrol(fark <= TABAN_TOLERANS, aile + ": tabanHacimMm3=" +
    sema.tabanHacimMm3.toFixed(1) + " fn(varsayilan)=" + taban.toFixed(1));
}

// ---------- 2) dogrulama kaynagi senkronu ----------
const dogrulamaDir = process.env.PRUVO_DOGRULAMA_DIR ||
  path.join(process.env.HOME || "", "dev", "pruvo-jenerator", "dogrulama");
console.log("\n== 2) dogrulama kaynagi senkronu (" + dogrulamaDir + ") ==");
if (!fs.existsSync(dogrulamaDir)) {
  console.log("  [ATLA] dogrulama dizini yok — katman 2 kosulamadi " +
    "(mimar makinesinde kosun)");
} else {
  // deterministik LCG — tekrar uretilebilir sema-grid setleri
  let tohum = 424242;
  function rasgele() {
    tohum = (tohum * 1103515245 + 12345) % 2147483648;
    return tohum / 2147483648;
  }
  function setUret(sema) {
    const s = {};
    sema.parametreler.forEach(function (p) {
      if (p.tip === "sayi") {
        const adim = p.adim || 1;
        const n = Math.round((p.max - p.min) / adim);
        s[p.ad] = Math.round((p.min + Math.floor(rasgele() * (n + 1)) *
          adim) * 1e6) / 1e6;
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
  }
  ["konektor", "braket", "adaptor", "kutu", "kavanoz"].forEach(function (aile) {
    const kaynakYol = path.join(dogrulamaDir, "test", "aileler",
      aile + ".js");
    if (!fs.existsSync(kaynakYol)) {
      kontrol(false, aile + ": dogrulama kaynak dosyasi yok: " + kaynakYol);
      return;
    }
    const sandbox = { Math: Math };
    vm.runInNewContext(fs.readFileSync(kaynakYol, "utf8") +
      "\n;__fn = " + aile + ";", sandbox);
    const refFn = sandbox.__fn;
    const esleme = JSON.parse(fs.readFileSync(path.join(
      TEST_DIR, "esleme", aile + ".json"), "utf8"));
    const sema = JSON.parse(fs.readFileSync(path.join(
      TEST_DIR, "..", "urunler", esleme.urunId + ".json"), "utf8"));
    let enKotu = 0;
    for (let i = 0; i < 25; i++) {
      const s = setUret(sema);
      const canli = HACIM[aile](s);
      const ref = refFn(s);
      const sapma = Math.abs(canli - ref) / ref * 100;
      if (sapma > enKotu) enKotu = sapma;
      if (sapma > SENKRON_YUZDE) {
        kontrol(false, aile + " set" + i + " canli=" + canli.toFixed(1) +
          " dogrulama=" + ref.toFixed(1) + " sapma=%" + sapma.toFixed(3) +
          " (" + JSON.stringify(s) + ")");
      }
    }
    kontrol(enKotu <= SENKRON_YUZDE, aile +
      ": 25 sette dogrulama kaynagi ile en kotu fark %" + enKotu.toFixed(3));
    // dogrulama urun semasindaki taban hacimle de karsilastir
    const dogUrun = path.join(dogrulamaDir, "urunler", esleme.urunId + ".json");
    if (fs.existsSync(dogUrun)) {
      const dSema = JSON.parse(fs.readFileSync(dogUrun, "utf8"));
      const fark = Math.abs(dSema.tabanHacimMm3 - sema.tabanHacimMm3) /
        dSema.tabanHacimMm3;
      kontrol(fark <= TABAN_TOLERANS, aile + ": tabanHacimMm3 canli=" +
        sema.tabanHacimMm3.toFixed(1) + " dogrulama=" +
        dSema.tabanHacimMm3.toFixed(1));
    }
  });
}

console.log(kirmizi ? "\nKIRMIZI: " + kirmizi + " kontrol" : "\nYESIL");
process.exit(kirmizi ? 1 : 0);
