#!/usr/bin/env node
/**
 * KABUL TESTI 3 — ana sayfa ilk yuk butcesi (FAZ 3).
 *
 *   node tools/faz3-yuk.js        # once: python3 tools/build.py  (ozet.json'u uretir)
 *
 * BUTCE (is paketi):
 *   - ozet.json           < 150 KB
 *   - bayrak ACIK ilk yuk < 500 KB  (gorseller HARIC)
 *
 * NEDEN: bu paketin butun varlik sebebi ilk yukun kucuk olmasi. 20k urunde urunler.json
 * ~14-15 MB olur (bugun 6,6 MB / 7.171 urun) = mobil ilk acilis + bellek riski
 * ([[katalog-olcek-siniri]]). "Herhalde kucuktur" demek yerine olcup yaziyoruz.
 *
 * NOT: ham (raw) bayt butceye bakilan sayidir; gzip de yazilir cunku kullaniciya fiilen
 * inen odur (Cloudflare sikistirarak sunar). Ikisi de raporlanir, karar hamda verilir.
 */

const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const KOK = path.dirname(__dirname);
const BUTCE_OZET = 150 * 1024;
const BUTCE_ILK_YUK = 500 * 1024;

function boyut(dosya) {
  const tam = path.join(KOK, dosya);
  if (!fs.existsSync(tam)) return null;
  const ham = fs.readFileSync(tam);
  return { ham: ham.length, gzip: zlib.gzipSync(ham).length };
}
const kb = (n) => (n / 1024).toFixed(1) + " KB";

const ozet = boyut("ozet.json");
const index = boyut("index.html");
const urunler = boyut("urunler.json");

if (!ozet) {
  console.log("ozet.json YOK — once `python3 tools/build.py` calistir.");
  process.exit(1);
}

console.log("Ilk yuk butcesi (gorseller haric)\n");
console.log("  index.html    ham %s / gzip %s", kb(index.ham), kb(index.gzip));
console.log("  ozet.json     ham %s / gzip %s", kb(ozet.ham), kb(ozet.gzip));
console.log("  urunler.json  ham %s / gzip %s   (bayrak ACIKKEN INMEZ)",
  kb(urunler.ham), kb(urunler.gzip));

const acik = index.ham + ozet.ham;
const acikGzip = index.gzip + ozet.gzip;
const kapali = index.ham + urunler.ham;
const kapaliGzip = index.gzip + urunler.gzip;

console.log("\n  BAYRAK ACIK  (index.html + ozet.json)     : ham %s / gzip %s", kb(acik), kb(acikGzip));
console.log("  BAYRAK KAPALI (index.html + urunler.json) : ham %s / gzip %s", kb(kapali), kb(kapaliGzip));
console.log("  kazanc: ham %sx / gzip %sx kucuk ilk yuk",
  (kapali / acik).toFixed(1), (kapaliGzip / acikGzip).toFixed(1));

// 20k projeksiyonu: urunler.json urun basina dogrusal buyur; ozet.json'un buyuyen tek
// parcasi marka/kategori haritasi + sabit N kart (yeni). Kaba ama karar icin yeterli.
const urunSayisi = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8")).length;
const olcek = 20000 / urunSayisi;
console.log("\n  20k projeksiyonu (bugun %d urun):", urunSayisi);
console.log("    urunler.json ~ %s ham / ~%s gzip  <- bayrak KAPALI iken her acilista",
  kb(urunler.ham * olcek), kb(urunler.gzip * olcek));
console.log("    ozet.json    ~ %s ham (marka haritasi buyur; kart sayisi SABIT)",
  kb(ozet.ham * Math.min(olcek, 2.2)));

let hata = 0;
console.log("");
if (ozet.ham > BUTCE_OZET) {
  console.log("  ❌ ozet.json butceyi asti: %s > %s", kb(ozet.ham), kb(BUTCE_OZET));
  hata++;
} else {
  console.log("  ✅ ozet.json %s < %s", kb(ozet.ham), kb(BUTCE_OZET));
}
if (acik > BUTCE_ILK_YUK) {
  console.log("  ❌ bayrak acik ilk yuk butceyi asti: %s > %s", kb(acik), kb(BUTCE_ILK_YUK));
  hata++;
} else {
  console.log("  ✅ bayrak acik ilk yuk %s < %s", kb(acik), kb(BUTCE_ILK_YUK));
}

if (hata) {
  console.log("\nSONUC: YUK BUTCESI ASILDI ❌");
  process.exit(1);
}
console.log("\nSONUC: YUK BUTCESI ICINDE ✅");
