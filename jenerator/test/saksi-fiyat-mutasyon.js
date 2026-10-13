#!/usr/bin/env node
/* SAKSI FİYAT MUTANT BATARYASI — jenerator/test/fiyat-test.js'in saksı bölümü KÖR mü?

   Her mutant secenekler.js ya da Worker shop/src/parametrik.js'in GEÇİCİ bir kopyasına
   uygulanır (canlı ağaca YAZILMAZ); fiyat-test.js PRUVO_SECENEK_YOL /
   PRUVO_PARAMETRIK_YOL ile o kopyaya yöneltilip koşulur. Hüküm:
     KONTROL (mutantsız kopyalar)            -> rc 0, kırmızı satır 0
     M1 zemin kaldırılır (zeminTL 400 -> 0)  -> rc 1 + kırmızı "saksı ZEMİN" satırı
     M2 tabak eki 0 (kademe kuruşları -> 0)  -> rc 1 + kırmızı "alt tabak eki" satırı
     M3 sunucu formülü ×100 (Worker tutarı)  -> rc 1 + kırmızı "istemci = sunucu" satırı
     M4 sabitTL 180 -> 0 (saf orana dönüş)  -> rc 1 + kırmızı "ön-ayar fiyatı S/M/L" satırı
   İŞARET ŞARTI: "rc 1" yetmez — beklenen satır kırmızı yanmalı (başka bir sebeple
   kırmızı = mutant ÖLMEDİ sayılır). Çapa bulunamazsa BAYAT HARNESS ile patlar (rc 2).
   Geçici dizin her koşum sonunda SİLİNİR (makinede iz yok). */
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const KOK = path.join(__dirname, "..", "..");
const SECENEK = path.join(KOK, "secenekler.js");
const PARAMETRIK = path.join(KOK, "shop", "src", "parametrik.js");
const TEST = path.join(__dirname, "fiyat-test.js");

function degistir(metin, eski, yeni, ad) {
  const n = metin.split(eski).length - 1;
  if (n < 1) {
    console.log("BAYAT HARNESS: " + ad + " çapası bulunamadı: " + JSON.stringify(eski));
    process.exit(2);
  }
  return metin.split(eski).join(yeni);
}

// parametrik.js göreli import'ları geçici kopyada MUTLAK file:// adrese çevrilir
// (kopya başka dizinde; aynı konfigurator.js / hacim.js modülleri yüklenir).
function parametrikKopya(metin) {
  return metin.replace(/from "(\.\.\/\.\.\/[^"]+)"/g, function (_, g) {
    return 'from "file://' + path.resolve(path.dirname(PARAMETRIK), g) + '"';
  });
}

const MUTANTLAR = [
  { ad: "KONTROL", beklenen: null },
  { ad: "M1 zemin kaldırılır", beklenen: "saksı ZEMİN",
    secenek: (m) => degistir(m, "zeminTL: 400,", "zeminTL: 0,", "M1") },
  { ad: "M2 tabak eki 0", beklenen: "alt tabak eki",
    secenek: (m) => degistir(degistir(degistir(m,
      "olcu: 70, kurus: 10000", "olcu: 70, kurus: 0", "M2a"),
      "olcu: 100, kurus: 15000", "olcu: 100, kurus: 0", "M2b"),
      "olcu: 130, kurus: 20000", "olcu: 130, kurus: 0", "M2c") },
  { ad: "M4 sabitTL 0 (saf orana dönüş)", beklenen: "ön-ayar fiyatı S/M/L",
    secenek: (m) => degistir(m, "sabitTL: 180,", "sabitTL: 0,", "M4") },
  { ad: "M3 sunucu formülü ×100", beklenen: "istemci = sunucu",
    parametrik: (m) => degistir(m, "    birimKurus: birimKurus,\n",
                                "    birimKurus: birimKurus * 100,\n", "M3") },
];

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "saksi-mutant-"));
let olmeyen = 0;
try {
  const kaynakS = fs.readFileSync(SECENEK, "utf8");
  const kaynakP = parametrikKopya(fs.readFileSync(PARAMETRIK, "utf8"));
  MUTANTLAR.forEach(function (mt, i) {
    const sYol = path.join(tmp, "secenekler-" + i + ".js");
    const pYol = path.join(tmp, "parametrik-" + i + ".mjs");
    fs.writeFileSync(sYol, mt.secenek ? mt.secenek(kaynakS) : kaynakS);
    fs.writeFileSync(pYol, mt.parametrik ? mt.parametrik(kaynakP) : kaynakP);
    const r = spawnSync(process.execPath, [TEST], {
      env: Object.assign({}, process.env,
        { PRUVO_SECENEK_YOL: sYol, PRUVO_PARAMETRIK_YOL: pYol }),
      encoding: "utf8", timeout: 120000 });
    const kirmizi = (r.stdout || "").split("\n").filter((s) => s.indexOf("[HATA]") >= 0);
    let ok;
    if (mt.beklenen === null) {
      ok = r.status === 0 && kirmizi.length === 0;
    } else {
      ok = r.status === 1 && kirmizi.some((s) => s.indexOf(mt.beklenen) >= 0);
    }
    if (!ok) { olmeyen++; }
    console.log("  [" + (ok ? "OK " : "HATA") + "] " + mt.ad + " -> rc=" + r.status +
                " kırmızı=" + kirmizi.length +
                (mt.beklenen ? " (beklenen satır: \"" + mt.beklenen + "\")" : " (kontrol yeşil)"));
    kirmizi.slice(0, 3).forEach((s) => console.log("        " + s.trim().slice(0, 160)));
  });
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
console.log("MUTANT " + (MUTANTLAR.length - 1) + " + KONTROL 1 · ölmeyen/bozuk: " + olmeyen);
process.exit(olmeyen ? 1 : 0);
