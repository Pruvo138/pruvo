#!/usr/bin/env node
"use strict";
/**
 * KOD-SENKRON SINIFI KABUL TESTI (25 Eki 2026, KraL halef-61) — AGSIZ, canliya 0 istek.
 *
 * Olcer: tools/parite-test.js `kodSenkronMu` hukmu + tools/index-arama-referansi.js
 * `anaReferans()` kurulumu. Sinifin gerekcesi parite-test.js "KOD-SENKRON SINIFI"
 * basliginda (ikinci kez YAZILMAZ).
 *
 *   H1-H5  saf hukum fiksturu: sinif YALNIZ "uc == main sitesi ≠ dal sitesi" halinde dogar.
 *          H1 her-zaman-false mutantini, H2-H5 her-zaman-true mutantini OLDURUR.
 *   G1     gercek agac: anaReferans() HATASIZ doner (ref ya da "ayni").
 *   G2     gecersiz ref (PARITE_KOD_SENKRON_REF) -> hata (fail-closed: sinif KAPALI).
 *   G3     gecici kok SILINIR (makinede iz yok).
 *   G4     ref kurulduysa: iki referansin markaKatla'si en az bir katalog markasinda
 *          AYRISIR (sinifin olcecegi kod farki gercekten VAR) — yoksa ref kurulmamaliydi.
 * rc=0 hepsi gecti · rc=1 bir iddia dustu.
 */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const KOK = path.dirname(__dirname);
const P = require("./parite-test.js");
const ortak = require("./parite-ortak.js");

const kalan = [];
function ona(kosul, ad) {
  console.log("  %s %s", kosul ? "GECTI" : "KALDI", ad);
  if (!kosul) kalan.push(ad);
}

const G = ortak.SINIF_GECTI, A = ortak.SINIF_ACIKLANAMAYAN, S = ortak.SINIF_ACIKLANAN;
const dal = ["a", "b"], ana = ["a", "b", "c"];
ona(P.kodSenkronMu({ sinif: A, anaSinif: G, bekIds: dal, bekAnaIds: ana }) === true,
  "H1 uc == main sitesi, dal farkli -> KOD-SENKRON");
ona(P.kodSenkronMu({ sinif: A, anaSinif: A, bekIds: dal, bekAnaIds: ana }) === false,
  "H2 uc main sitesiyle de ayrisiyor -> KIRMIZI kalir");
ona(P.kodSenkronMu({ sinif: A, anaSinif: G, bekIds: ["b", "a"], bekAnaIds: ["a", "b"] }) === false,
  "H3 dal == main sitesi (kod farki yok) -> KIRMIZI kalir");
ona(P.kodSenkronMu({ sinif: S, anaSinif: G, bekIds: dal, bekAnaIds: ana }) === false,
  "H4 katalog-senkron (ACIKLANAN) sinifi ezilmez");
ona(P.kodSenkronMu({ sinif: G, anaSinif: G, bekIds: dal, bekAnaIds: ana }) === false,
  "H5 GECTI sorgu sinifa girmez");

function cocuk(env) {
  const kod = "const R=require(" + JSON.stringify(path.join(__dirname, "index-arama-referansi.js")) +
    ");const a=R.anaReferans();process.stdout.write(JSON.stringify({ref:!!a.ref,ayni:!!a.ayni," +
    "hata:a.hata||null,ayrisan:a.ref?(function(){const d=R.referans();const m=new Set();" +
    "for(const p of JSON.parse(require('fs').readFileSync(" + JSON.stringify(path.join(KOK, "urunler.json")) +
    ",'utf8')))for(const x of (p.marka||[])){const v=String(x).toLowerCase();" +
    "if(d.markaKatla(v)!==a.ref.markaKatla(v))m.add(v);}return m.size;})():0}));";
  const out = execFileSync(process.execPath, ["-e", kod],
    { encoding: "utf8", env: Object.assign({}, process.env, env), maxBuffer: 64 * 1024 * 1024 });
  return JSON.parse(out);
}

const izOnce = fs.readdirSync(os.tmpdir()).filter((d) => d.startsWith("pruvo-kod-senkron-")).length;
const g1 = cocuk({});
ona(!g1.hata && (g1.ref || g1.ayni), "G1 gercek agac: anaReferans hatasiz (" +
  (g1.ref ? "ref kuruldu" : g1.ayni ? "index.html == origin/main" : "hata=" + g1.hata) + ")");
const g2 = cocuk({ PARITE_KOD_SENKRON_REF: "refs/heads/yok-boyle-bir-ref-kod-senkron" });
ona(!!g2.hata && !g2.ref, "G2 gecersiz ref -> hata (sinif KAPALI, fail-closed)");
const izSonra = fs.readdirSync(os.tmpdir()).filter((d) => d.startsWith("pruvo-kod-senkron-")).length;
ona(izSonra === izOnce, "G3 gecici kok silindi (once=" + izOnce + " sonra=" + izSonra + ")");
if (g1.ref) {
  ona(g1.ayrisan > 0, "G4 dal ↔ main markaKatla en az bir katalog degerinde ayrisiyor (" +
    g1.ayrisan + " deger)");
} else {
  console.log("  BILGI G4 atlandi: dal index.html == origin/main (sinif bos, olcecek fark yok)");
}

console.log("-".repeat(70));
if (kalan.length) {
  console.log("SONUC: %d iddia KALDI ❌", kalan.length);
  process.exit(1);
}
console.log("SONUC: KOD-SENKRON kabul hepsi GECTI ✔");
