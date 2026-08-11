#!/usr/bin/env node
/**
 * CURUTME 02 — EKSEN 5: `yeniRef` cozumu (istemci havuzu) kirilir mi?
 *
 * Derleme (build.py) havuz uyeligini PYTHON sozlugu ile, istemci (index.html ozetAc)
 * JS OBJESI ile kurar. Iki dilin "anahtar var mi / deger dogru mu" yuklemi AYNI DEGIL:
 *   - Python: `kart.get("id") is not None`      -> "" (bos dize) HAVUZDA
 *   - JS    : `if(k && k.id && !havuz[k.id])`   -> "" FALSY, havuza GIRMEZ
 *   - JS    : `havuz[oge]` Object.prototype'tan MIRAS anahtari da bulur
 * Bu surucu her senaryoyu GERCEK build.py + CANLI ozetAc ile kosar ve
 * "build ne diyor / istemci ne ciziyor" ayrismasini SAYIYLA basar.
 *
 * Cikis: 0 = hicbir senaryo ayrismadi · 1 = en az bir SESSIZ AYRISMA bulundu.
 */
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const KOK = path.dirname(path.dirname(__dirname));
const BUILD = path.join(KOK, "tools", "build.py");
const ozetAc = require(path.join(KOK, "tools", "ozet-ac-ayikla.js")).ozetAcAl();
const GECICI = fs.mkdtempSync(path.join(os.tmpdir(), "curut-yeniref-"));
const ONEK = "https://media.pruvo3d.com/urunler/";

let no = 0;
function uret(urunler, surum) {
  no += 1;
  const kat = path.join(GECICI, "k" + no + ".json");
  const cik = path.join(GECICI, "o" + no + ".json");
  fs.writeFileSync(kat, JSON.stringify(urunler), "utf8");
  const r = spawnSync("python3", [BUILD, "--sadece-ozet", "--katalog", kat,
    "--cikti", cik, "--ozet-surum", String(surum)], { encoding: "utf8" });
  if (r.status !== 0) {
    return { hata: "rc=" + r.status + " " + String(r.stderr || r.stdout).trim().slice(-260) };
  }
  const ham = fs.readFileSync(cik, "utf8");
  return { ham, ozet: JSON.parse(ham) };
}

let n = 0;
function urun(kategori, ek) {
  const i = n++;
  return Object.assign({
    id: "cu-" + i, kategori, marka: [], baslik: "Curut " + i,
    aciklama: "Curut aciklama " + i, fiyat: (100 + i) + " TL",
    gorseller: [ONEK + "cu-" + i + "-1.jpg"],
  }, ek || {});
}

/** Senaryo: ilk urun PATOLOJIK id tasir, kategori Marin (havuza da girer, `yeni`ye de). */
function senaryo(ad, patolojikId, ekstra) {
  const l = [];
  l.push(urun("Marin", Object.assign({ id: patolojikId }, ekstra || {})));
  for (let i = 0; i < 20; i++) { l.push(urun("Marin")); }
  const v3 = uret(l, 3);
  if (v3.hata) {
    console.log("  [%s] BUILD KIRMIZI (fail-closed) -> %s", ad, v3.hata);
    return { ad, buildKirmizi: true, kayip: 0, bozuk: 0 };
  }
  const acilan = ozetAc(JSON.parse(v3.ham));
  const yeni = acilan.yeni || [];
  const beklenenAdet = Math.min(48, l.length);
  const kayip = beklenenAdet - yeni.length;
  const bozuk = yeni.filter((k) => !k || typeof k !== "object" || Array.isArray(k)
    || typeof k.baslik !== "string").length;
  const refTipi = JSON.stringify((v3.ozet.yeniRef || [])[0]);
  console.log("  [%s] build YESIL | yeniRef[0]=%s | istemci `yeni` %d/%d kart "
    + "(KAYIP %d) | KART OLMAYAN nesne %d",
  ad, refTipi, yeni.length, beklenenAdet, kayip, bozuk);
  if (bozuk) {
    console.log("        bozuk ornek: %s", Object.prototype.toString.call(yeni[0])
      + " " + String(yeni[0]).slice(0, 60));
  }
  return { ad, buildKirmizi: false, kayip, bozuk };
}

console.log("=== CURUTME 02 — yeniRef cozumu (build vs CANLI ozetAc)\n");
const sonuc = [];
sonuc.push(senaryo("kontrol: normal id", "cu-kontrol"));
sonuc.push(senaryo("id = BOS DIZE", ""));
sonuc.push(senaryo("id = 0 (sayi)", 0));
sonuc.push(senaryo("id = 'constructor'", "constructor"));
sonuc.push(senaryo("id = '__proto__'", "__proto__"));
sonuc.push(senaryo("id = 'toString'", "toString"));
sonuc.push(senaryo("id = 'hasOwnProperty'", "hasOwnProperty"));

// MUKERRER id: ayni id iki FARKLI urunde (biri havuzda, digeri sadece `yeni`de)
(function () {
  const l = [];
  l.push(urun("Kamera", { id: "cu-ikiz", baslik: "KAMERA IKIZ", fiyat: "999 TL" }));
  l.push(urun("Marin", { id: "cu-ikiz", baslik: "MARIN IKIZ", fiyat: "111 TL" }));
  for (let i = 0; i < 10; i++) { l.push(urun("Marin")); }
  const v3 = uret(l, 3);
  if (v3.hata) { console.log("  [mukerrer id] BUILD KIRMIZI -> %s", v3.hata); return; }
  const a = ozetAc(JSON.parse(v3.ham));
  const y = a.yeni || [];
  console.log("  [mukerrer id: ayni id iki FARKLI urun] build YESIL | `yeni` %d kart | "
    + "ilk iki basligi: %j / %j (beklenen KAMERA IKIZ / MARIN IKIZ)",
  y.length, (y[0] || {}).baslik, (y[1] || {}).baslik);
  const sapma = (y[0] || {}).baslik !== "KAMERA IKIZ" || (y[1] || {}).baslik !== "MARIN IKIZ";
  sonuc.push({ ad: "mukerrer id", buildKirmizi: false, kayip: 0, bozuk: sapma ? 1 : 0 });
}());

fs.rmSync(GECICI, { recursive: true, force: true });
const kirik = sonuc.filter((s) => !s.buildKirmizi && (s.kayip > 0 || s.bozuk > 0));
console.log("");
console.log("SONUC: build YESIL iken istemcide ayrisan senaryo %d/%d -> %s",
  kirik.length, sonuc.length, kirik.length ? "KIRILDI" : "SAGLAM");
kirik.forEach((k) => console.log("   ✘ %s (kayip %d, bozuk %d)", k.ad, k.kayip, k.bozuk));
process.exit(kirik.length ? 1 : 0);
