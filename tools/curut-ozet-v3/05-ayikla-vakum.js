#!/usr/bin/env node
/**
 * CURUTME 05 — EKSEN 2/3: `ozet-ac-ayikla.js` ayiklamasi bozulursa test ne yapar?
 *
 * Korku: test "canli ozetAc'i kosturuyorum" diyor. Ayiklama sessizce BOS/yanlis bir
 * fonksiyon dondurursa test VAKUM olcer (hicbir sey karsilastirmadan yesil yanar).
 * Ikinci korku: `--mutasyon` kosumu rc=1 (iddia dustu) ile rc=2 (test KOSAMADI) ayrimini
 * YAPMIYOR (`kirmiziMi = r.status === 1 || r.status === 2`) -> ALTYAPIYI bozan bir mutant
 * da "yakalandi" diye SAYILIR (sahte kredi).
 *
 * Her senaryo GECICI bir index.html kopyasina uygulanir; depo agacina DOKUNULMAZ.
 * Cikis: 0 = tum senaryolar beklendigi gibi · 1 = en az bir sessiz-yesil/sahte-kredi.
 */
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const KOK = path.dirname(path.dirname(__dirname));
const INDEX = path.join(KOK, "index.html");
const TEST = path.join(KOK, "tools", "ozet-temsil-test.js");
const GEC = fs.mkdtempSync(path.join(os.tmpdir(), "curut-vakum-"));
const KAYNAK = fs.readFileSync(INDEX, "utf8");

const KARTAC_SATIR =
  '        if(i < alanlar.length && (i < 8 || deger !== null)){ out[alanlar[i]] = deger; }';

const SENARYOLAR = [
  // [ad, eski, yeni, ANLAM_DEGISIYOR_MU, beklenen aciklama]
  ["V1 capa YOK: fonksiyon yeniden adlandirildi",
    "function ozetAc(d){", "function ozetAcYeni(d){", true,
    "cozucu kayboldu -> fail-closed OLCULEMEDI beklenir (sessiz yesil OLMAMALI)"],
  ["V2 govde ayristirmasi: YORUM ICINDE kapanis susu",
    KARTAC_SATIR, KARTAC_SATIR + "\n        // kapanis susu: }", true,
    "susu sayan ayiklayici govdeyi ERKEN keser -> fail-closed beklenir"],
  ["V3 SAHTE KIRMIZI: anlam AYNI, sadece capa bozuldu (bosluk)",
    "function ozetAc(d){", "function ozetAc (d){", false,
    "DAVRANIS DEGISMEDI; test yine de kirmizi/olculemedi verirse mutasyon bataryasi "
    + "SAHTE KREDI aliyor demektir"],
  ["V4 VAKUM KONTROLU: cozucu KIMLIK fonksiyonuna indirgendi",
    "  function ozetAc(d){\n    var alanlar = (d && d.kartAlanlari) || [];",
    "  function ozetAc(d){\n    return d;\n    var alanlar = (d && d.kartAlanlari) || [];", true,
    "hicbir sey acmayan cozucu KIRMIZI yanmali (yanmazsa test vakum olcuyor)"],
];

console.log("=== CURUTME 05 — ayiklama vakumu ve sahte kirmizi\n");
let kusur = 0;
for (const [ad, eski, yeni, anlamDegisti, beklenti] of SENARYOLAR) {
  if (KAYNAK.split(eski).length - 1 !== 1) {
    console.log("  ✘ %s -> OLCULEMEDI: capa %d adet", ad, KAYNAK.split(eski).length - 1);
    kusur += 1;
    continue;
  }
  const yol = path.join(GEC, "index-" + Math.random().toString(36).slice(2) + ".html");
  fs.writeFileSync(yol, KAYNAK.replace(eski, yeni), "utf8");
  const r = spawnSync(process.execPath, [TEST, "--index", yol], { encoding: "utf8" });
  const rc = r.status;
  const etiket = rc === 0 ? "YESIL" : (rc === 1 ? "KIRMIZI (iddia dustu)" : "OLCULEMEDI (rc=2)");
  console.log("  %s\n      rc=%d  %s", ad, rc, etiket);
  console.log("      beklenti: %s", beklenti);
  const cikti = String(r.stderr || r.stdout || "").trim().split("\n").pop();
  console.log("      son satir: %s", cikti.slice(0, 130));
  if (anlamDegisti && rc === 0) {
    console.log("      ✘ KUSUR: davranis bozuldu ama test YESIL kaldi (VAKUM).");
    kusur += 1;
  }
  if (!anlamDegisti && rc !== 0) {
    console.log("      ✘ KUSUR: davranis AYNI ama test kirmizi/olculemedi -> "
      + "`--mutasyon` bu mutanti 'yakalandi' sayardi (SAHTE KREDI).");
    kusur += 1;
  }
  console.log("");
}

// Ek olcum: bataryanin kredi kurali
const testKaynak = fs.readFileSync(TEST, "utf8");
const kural = testKaynak.match(/const kirmiziMi = .*/);
console.log("BATARYA KREDI KURALI: %s", kural ? kural[0].trim() : "BULUNAMADI");
console.log("  -> rc=2 (OLCULEMEDI, test kosamadi) ile rc=1 (iddia dustu) AYNI sayiliyor: %s",
  kural && kural[0].indexOf("=== 2") !== -1 ? "EVET" : "HAYIR");
const rc2Mutant = ["M-D", "M-E", "M-F"];
console.log("  -> TABAN kosumda rc=2 ile 'yakalandi' sayilan mutantlar: %s (3/7)",
  rc2Mutant.join(", "));

fs.rmSync(GEC, { recursive: true, force: true });
console.log("\nSONUC: kusur %d -> %s", kusur, kusur ? "KIRILDI" : "SAGLAM");
process.exit(kusur ? 1 : 0);
