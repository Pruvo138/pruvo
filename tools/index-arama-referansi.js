#!/usr/bin/env node
"use strict";
/**
 * SITE ARAMA REFERANSI — index.html'in GERCEK arama yuklemi, KOPYA DEGIL.
 *
 * NEDEN VAR (olculdu 5 Agu 2026): tools/parite-test.js sitenin arama yuklemini ELLE
 * KOPYALANMIS bir norm()+haystack()+filtered() ucluyle taklit ediyordu. index.html
 * "marka adiyla yapilan sorgu" kuralini UYELIK ∪ BASLIKTA TAM KELIME yuklemine
 * baglayinca (8913db28) kopya sessizce BAYAT AYNA'ya dondu: test 33/1199 ayrisim
 * bastigi halde SITE ile UC ARASINDA HICBIR KUSUR YOKTU — sapan taraf testin
 * kendisiydi. [[ikiz-tanim-sessiz-ayrisma]]
 *
 * COZUM: ikinci bir yuklem YAZILMAZ. index.html'in kanonik bloklari kaynaktan
 * AYIKLANIR ve node:vm icinde CALISTIRILIR; referans, musterinin tarayicisinda kosan
 * kodun TA KENDISIDIR. Kural degisince referans kendiliginden degisir — bayatlayacak
 * bir kopya kalmaz.
 *
 * CAPALAR (marka-liste-test.py ile AYNI marker/regex'ler; o kapi varliklarini olcer):
 *   "// --- MARKA KURATORLUGU BAS/SON ---"  -> TANINMIS_MARKALAR + markaKatla + markaNorm
 *   "// --- MARKA SORGUSU BAS/SON ---"      -> aramaPlani + aramaPlaniEsler + markaUyeMi
 *   norm() / ARAMA_EKLER+aramaKok() / haystack() / cipIndeks()
 *
 * CIP INDEKSI UYDURULMAZ: uretim ureteci (tools/cip-indeks.py --yazdir) kosturulur.
 * index.html cip indeksi YOKKEN bilerek fail-OPEN'dir (cip evreni markalari serbest
 * metinde kalir) — ama UC oyle DEGIL (`marka_arama` kolonu o markalari da tasir).
 * Indeks uydurulsa ya da bos gecilse referans ile uc cip evreni markalarinda
 * ayrisirdi. Bu yuzden burada indeks SART: uretilemezse fail-CLOSED HATA atilir,
 * cagiran (parite-test.js) bunu OLCULEMEDI'ye cevirir, sessiz YESIL'e DEGIL.
 *
 * ENV (yalniz izole kosumlar icin — normal kosumda VERILMEZ):
 *   PARITE_INDEX_KOK  index.html'in bulundugu agac (varsayilan: bu betigin agaci)
 *   PARITE_CIP_INDEKS hazir cip indeksi JSON yolu (uretici kosturulmaz)
 */

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");

/** Ayiklama capalari — biri tutmazsa referans KURULAMAZ (fail-closed). */
const BLOK_MARKERLARI = [
  ["// --- MARKA KÜRATÖRLÜĞÜ BAŞ", "// --- MARKA KÜRATÖRLÜĞÜ SON ---"],
  ["// --- MARKA SORGUSU BAŞ", "// --- MARKA SORGUSU SON ---"],
];
const FONKSIYON_RE = [
  ["norm()", /function norm\(s\)\{[\s\S]*?\n  \}/],
  ["aramaKok()", /var ARAMA_EKLER=\[[^\n]*\n  function aramaKok\(w\)\{[^\n]*\n/],
  ["haystack()", /function haystack\(p\)\{[\s\S]*?\n  \}/],
  ["cipIndeks()", /function cipIndeks\(\)\{[\s\S]*?\n  \}/],
];
/** Referansin FIILEN tasidigi imzalar; biri dusesse yuklem sessizce degisirdi. */
const ZORUNLU_IMZALAR = ["markaAdiKanonu", "baslikMarkalari", "markaUyeMi",
  "markaSorgusuEsler", "aramaPlani", "aramaPlaniEsler", "markaKatla", "markaNorm"];

function blokAyikla(src, bas, son) {
  const i = src.indexOf(bas);
  const j = src.indexOf(son);
  if (i === -1 || j <= i) {
    throw new Error("index.html capasi tutmadi: " + bas + " ... " + son +
      " (blok yeniden adlandirildi mi? referans KURULAMADI)");
  }
  return src.slice(src.indexOf("\n", i) + 1, j);
}

/**
 * Onbellek anahtari: uretecin IKI girdisinin (index.html + urunler.json) boyut+mtime'i.
 * 🔴 NEDEN ONBELLEK VAR (olculdu 5 Agu): uretici SUREC BASINA ~1 sn suruyor ve fikstur
 * harness'leri tek kosumda YUZLERCE cocuk surec aciyor. Onbelleksiz surumde
 * tools/parite-mutasyon-test.js 25/25'ten 9/25'e dustu (16 mutant "yakalanmadi"
 * gorundu — gerileme DEGIL, yuk); PARITE_CIP_INDEKS elle verildiginde 25/25 geri geldi.
 * Anahtar iki girdinin de damgasini tasidigi icin biri degisince onbellek DUSER.
 */
function onbellekAnahtari(kok) {
  const parcalar = ["index.html", "urunler.json"].map(function (ad) {
    const s = fs.statSync(path.join(kok, ad));
    return ad + ":" + s.size + ":" + s.mtimeMs;
  });
  return require("node:crypto").createHash("sha1")
    .update(kok + "|" + parcalar.join("|")).digest("hex").slice(0, 16);
}

/** Cip indeksini URETIM ureticisinden al (uydurma YOK). */
function cipIndeksiAl(kok) {
  const hazir = process.env.PARITE_CIP_INDEKS;
  if (hazir) { return dogrula(JSON.parse(fs.readFileSync(hazir, "utf8"))); }

  let onbellek = null;
  try { onbellek = path.join(os.tmpdir(), "pruvo-cip-indeks-" + onbellekAnahtari(kok) + ".json"); }
  catch (e) { /* urunler.json yoksa anahtar kurulamaz -> onbelleksiz devam */ }
  if (onbellek && fs.existsSync(onbellek)) {
    try { return dogrula(JSON.parse(fs.readFileSync(onbellek, "utf8"))); }
    catch (e) { /* bozuk onbellek: yok say, yeniden uret */ }
  }

  const uretec = path.join(kok, "tools", "cip-indeks.py");
  if (!fs.existsSync(uretec)) {
    throw new Error("cip indeksi ureteci yok: " + uretec);
  }
  const cikti = execFileSync("python3", [uretec, "--kok", kok, "--yazdir"],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  const ix = dogrula(JSON.parse(cikti));
  // Yazma ATOMIK: paralel cocuk surecler ayni dosyayi yarim halde okumasin.
  if (onbellek) {
    try {
      const gecici = onbellek + "." + process.pid + ".tmp";
      fs.writeFileSync(gecici, cikti);
      fs.renameSync(gecici, onbellek);
    } catch (e) { /* onbellek yazilamadi: olcum yine dogru, yalniz yavas */ }
  }
  return ix;
}

function dogrula(ix) {
  if (!ix || !ix.kat || !Array.isArray(ix.alt)) {
    throw new Error("cip indeksi bicimi taninmadi (kat/alt yok)");
  }
  return ix;
}

let _bellek = null;

/**
 * index.html'in arama yuklemini kurar ve DISA VERIR.
 * @returns {{norm:Function, aramaKok:Function, haystack:Function,
 *            aramaPlani:Function, aramaPlaniEsler:Function,
 *            markaKatla:Function, markaUyeMi:Function, kok:string}}
 */
function referans() {
  if (_bellek) { return _bellek; }
  const kok = process.env.PARITE_INDEX_KOK || path.dirname(__dirname);
  const indexYolu = path.join(kok, "index.html");
  if (!fs.existsSync(indexYolu)) {
    throw new Error("index.html bulunamadi: " + indexYolu +
      " (izole kosumda PARITE_INDEX_KOK verilmeli)");
  }
  const src = fs.readFileSync(indexYolu, "utf8");

  const parcalar = [];
  for (const [ad, re] of FONKSIYON_RE) {
    const m = re.exec(src);
    if (!m) { throw new Error("index.html'den " + ad + " ayiklanamadi (yapi degisti mi?)"); }
    parcalar.push(m[0]);
  }
  for (const [bas, son] of BLOK_MARKERLARI) { parcalar.push(blokAyikla(src, bas, son)); }

  const govde = parcalar.join("\n");
  for (const imza of ZORUNLU_IMZALAR) {
    if (govde.indexOf("function " + imza) === -1) {
      throw new Error("ayiklanan govdede " + imza + "() YOK — referans EKSIK kurulurdu");
    }
  }

  const ix = cipIndeksiAl(kok);
  const ctx = vm.createContext({ window: { PRUVO_CIP_INDEKS: ix } });
  vm.runInContext(govde + "\n;({ norm: norm, aramaKok: aramaKok, haystack: haystack," +
    " aramaPlani: aramaPlani, aramaPlaniEsler: aramaPlaniEsler," +
    " markaKatla: markaKatla, markaUyeMi: markaUyeMi });",
    ctx, { filename: indexYolu });
  const disa = vm.runInContext("({ norm: norm, aramaKok: aramaKok, haystack: haystack," +
    " aramaPlani: aramaPlani, aramaPlaniEsler: aramaPlaniEsler," +
    " markaKatla: markaKatla, markaUyeMi: markaUyeMi })", ctx);

  _bellek = Object.assign({ kok: kok }, disa);
  return _bellek;
}

module.exports = { referans, BLOK_MARKERLARI, ZORUNLU_IMZALAR };
