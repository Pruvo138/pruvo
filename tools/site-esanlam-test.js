#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const cp = require("node:child_process");

const KOK = path.dirname(__dirname);
const SORGULAR = ["araba", "oto", "audi araba", "audi arac", "oto conta", "araba icin braket"];
const TERS = ["audi", "audi braket", "kamera"];
const ARAC_TAM_JETON = /(^|[^a-z0-9])(oto|otomobil|araba|arac)(?=$|[^a-z0-9])/;

function sayimlar(kok) {
  process.env.PARITE_INDEX_KOK = kok;
  delete require.cache[require.resolve("./index-arama-referansi.js")];
  const R = require("./index-arama-referansi.js").referans();
  const urunler = JSON.parse(fs.readFileSync(path.join(kok, "urunler.json"), "utf8"));
  const say = (q) => {
    const plan = R.aramaPlani(q);
    return urunler.reduce((n, p) => n + (R.aramaPlaniEsler(p, plan) ? 1 : 0), 0);
  };
  const eskiSay = (q) => {
    const plan = R.aramaPlani(q);
    if (plan.kanon) return say(q);
    const tokens = R.norm(q).split(/\s+/).filter(Boolean).map(R.aramaKok);
    return urunler.reduce((n, p) => {
      const hs = R.haystack(p);
      return n + (tokens.every((t) => hs.indexOf(t) !== -1) ? 1 : 0);
    }, 0);
  };
  const arabaPlani = R.aramaPlani("araba");
  const motosikletSonuclari = urunler.filter((p) => p.kategori === "Motosiklet" &&
    R.aramaPlaniEsler(p, arabaPlani));
  const motosikletKirli = motosikletSonuclari.filter((p) =>
    !ARAC_TAM_JETON.test(R.haystack(p)));
  return { yeni: Object.fromEntries([...SORGULAR, ...TERS].map((q) => [q, say(q)])),
    eski: Object.fromEntries([...SORGULAR, ...TERS].map((q) => [q, eskiSay(q)])),
    motosikletSonuc: motosikletSonuclari.length, motosikletKirli: motosikletKirli.length };
}

function fikstur(kok) {
  const s = sayimlar(kok);
  const hata = [];
  for (const q of SORGULAR) if (s.yeni[q] === 0) hata.push(q + " sifir dondu");
  if (s.yeni["audi araba"] < s.yeni.audi) hata.push("audi araba, audi'den kucuk");
  for (const q of TERS) if (s.yeni[q] !== s.eski[q]) hata.push(q + " sinif disinda sisti");
  // BEKLENEN DAVRANIS DEGISIKLIGI: yalniz `oto` eskiden motosiklet/motor/foto icindeki
  // alt-dizeyi de esliyordu (23.811 sonuc). Tam-jeton siniri bu kirli tabani DUSURMELI;
  // bu kayip regresyon degil, pre-mevcut kirliligin temizlenmesidir.
  if (s.yeni.oto >= s.eski.oto) hata.push("oto tam-jeton daralmasi gerceklesmedi");
  if (s.motosikletKirli !== 0) hata.push("araba sorgusunda oto alt-dizesinden " +
    s.motosikletKirli + " kirli Motosiklet sonucu var");
  if (hata.length) throw new Error(hata.join("; "));
  return s;
}

function aynaKur(src) {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-site-esanlam-"));
  fs.writeFileSync(path.join(d, "index.html"), src);
  fs.symlinkSync(path.join(KOK, "urunler.json"), path.join(d, "urunler.json"));
  fs.symlinkSync(path.join(KOK, "tools"), path.join(d, "tools"));
  return d;
}

function mutantOldur(ad, degistir, pythonKapisi) {
  const asil = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
  const mutant = degistir(asil);
  if (mutant === asil) throw new Error(ad + " mutant capasi tutmadi");
  const d = aynaKur(mutant);
  let oldu = false;
  try {
    if (pythonKapisi) {
      const r = cp.spawnSync("python3", ["-c", "import arama"],
        { cwd: d, env: Object.assign({}, process.env, { PYTHONPATH: path.join(d, "tools") }) });
      oldu = r.status !== 0;
    } else {
      try { fikstur(d); } catch (e) { oldu = true; }
    }
  } finally { fs.rmSync(d, { recursive: true, force: true }); }
  if (!oldu) throw new Error(ad + " mutantini fikstur OLDUREMEDI");
  console.log("OLDU: " + ad);
}

try {
  const s = fikstur(KOK);
  console.log("FIKSTUR YESIL: " + SORGULAR.map((q) => q + "=" + s.yeni[q]).join(" | ") +
    " | araba/Motosiklet=" + s.motosikletSonuc + " kirli=" + s.motosikletKirli);
  mutantOldur("M1 es anlamli kumesi bos",
    (x) => x.replace('var ARAC_ES_ANLAMLI = ["oto", "otomobil", "araba", "arac"];',
      "var ARAC_ES_ANLAMLI = [];"));
  mutantOldur("M2 coklu jeton AND yerine tum sorgu OR",
    (x) => x.replace("if(!aramaSecenegiEsler(hs, plan.tokens[i])){ return false; }",
      "if(plan.tokens.some(function(t){ return aramaSecenegiEsler(hs, t); })){ return true; }"));
  mutantOldur("M3 ikiz tanim ayrismasi",
    (x) => x.replace('var ARAC_ES_ANLAMLI = ["oto", "otomobil", "araba", "arac"];',
      'var ARAC_ES_ANLAMLI = ["oto", "otomobil", "araba", "arac"];\n' +
      '  var ARAC_ES_ANLAMLI = ["oto", "otomobil"];'), true);
  mutantOldur("M4 arac sinifinda kelime siniri kaldirildi",
    (x) => x.replace("? secenek.some(function(t){ return aramaTamJetonEsler(hs, t); })",
      "? secenek.some(function(t){ return hs.indexOf(t) !== -1; })"));
  console.log("MUTANT: 4/4 olduruldu");
} catch (e) {
  console.error("KIRMIZI: " + e.message);
  process.exit(1);
}
