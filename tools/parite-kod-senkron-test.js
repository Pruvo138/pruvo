#!/usr/bin/env node
"use strict";
/**
 * KOD-SENKRON SINIFI KABUL TESTI (25 Eki 2026, KraL halef-61; BaBa tik 166 sartlari) — AGSIZ,
 * canliya 0 istek.
 *
 * Olcer: tools/parite-test.js `kodSenkronMu` hukmu + tools/index-arama-referansi.js
 * `anaReferans()` / `taninmisFarki()`. Sinifin gerekcesi parite-test.js "KOD-SENKRON SINIFI"
 * basliginda (ikinci kez YAZILMAZ).
 *
 *   H1-H7  saf hukum fiksturu: sinif YALNIZ "uc == main sitesi ≠ dal sitesi" VE sorgunun marka
 *          kanonu TANINMIS simetrik farkindayken dogar. H1 her-zaman-false mutantini, H2-H7
 *          her-zaman-true / kapsam-genisletme mutantlarini OLDURUR.
 *            H6 fark BOS -> sinif 0 (sart ③) · H7 fark DISI marka -> KIRMIZI (sart ④)
 *   F1-F2  taninmisFarki iki yonlu ve sirasiz.
 *   G1     gercek agac: anaReferans() HATASIZ doner (ref ya da "ayni").
 *   G2     gecersiz ref (PARITE_KOD_SENKRON_REF) -> hata (fail-closed: sinif KAPALI).
 *   G3     gecici kok SILINIR (makinede iz yok).
 *   G4     ref kurulduysa: fark BOS DEGIL ve her fark adi TAM OLARAK bir tarafin listesinde.
 *   G5     BORC KAPANIS KOLU (sart ⑥): referans dalin KENDISI (HEAD) iken fark BOS -> sinif 0.
 *          Merge SHA'sinin main SERIT B'sinde origin/main == HEAD oldugundan TEST 5 orada
 *          KOD-SENKRON dogamaz: D1 build'de yenilenmediyse ayrisma KIRMIZI yanar (borc
 *          sessiz kapanmaz). Deploy nobeti: merge SHA'si deploy+yayin sonrasi
 *          `node tools/parite-test.js 300` rc 0 (merge-kapisi §5).
 * rc=0 hepsi gecti · rc=1 bir iddia dustu.
 */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const KOK = path.dirname(__dirname);
const P = require("./parite-test.js");
const R = require("./index-arama-referansi.js");
const ortak = require("./parite-ortak.js");

const kalan = [];
function ona(kosul, ad) {
  console.log("  %s %s", kosul ? "GECTI" : "KALDI", ad);
  if (!kosul) kalan.push(ad);
}

const G = ortak.SINIF_GECTI, A = ortak.SINIF_ACIKLANAMAYAN, S = ortak.SINIF_ACIKLANAN;
const dal = ["a", "b"], ana = ["a", "b", "c"];
const taban = { sinif: A, anaSinif: G, bekIds: dal, bekAnaIds: ana,
  kanonDal: "Pentax", kanonAna: "", fark: ["Olympus", "Pentax"] };
const v = (deg) => P.kodSenkronMu(Object.assign({}, taban, deg));
ona(v({}) === true, "H1 uc == main sitesi, dal farkli, kanon farkta -> KOD-SENKRON");
ona(v({ anaSinif: A }) === false, "H2 uc main sitesiyle de ayrisiyor -> KIRMIZI kalir");
ona(v({ bekIds: ["c", "b", "a"] }) === false, "H3 dal == main sitesi (kod farki yok) -> KIRMIZI kalir");
ona(v({ sinif: S }) === false, "H4 katalog-senkron (ACIKLANAN) sinifi ezilmez");
ona(v({ sinif: G }) === false, "H5 GECTI sorgu sinifa girmez");
ona(v({ fark: [] }) === false, "H6 TANINMIS farki BOS -> sinif 0 (deger esit olsa bile)");
ona(v({ kanonDal: "Canon", kanonAna: "Canon" }) === false,
  "H7 fark DISI marka sorgusu -> KIRMIZI kalir");
ona(v({ kanonDal: "", kanonAna: "Pentax" }) === true,
  "H7b ters yon (main'de tanınmis, dalda cikmis) da sinifa girer");

// MARKA-CIP KOLU (26 Eki, BaBa tik 186 (B)(2) — PARTI 1 MINI 212 ↔ 228 vakasi)
const farkli = { c: true, d: true };          // c, d = TANINMIS farkindaki markanin urunleri
const fuSahte = (id) => !!farkli[id];
const mc = (deg) => v(Object.assign({ kanonDal: "Mini", kanonAna: "Mini", markaCip: true,
  bekIds: ["a", "b", "c", "d"], bekAnaIds: ["a", "b"], farkUrunuMu: fuSahte }, deg));
ona(mc({}) === true, "H8 marka-cip: simetrik farkin HER urunu fark markasindan -> KOD-SENKRON " +
  "(sorgu kanonu farkta OLMASA bile)");
ona(mc({ bekIds: ["a", "b", "c", "x"] }) === false,
  "H9 marka-cip: TEK fark-disi urun (x) sinifi KAPATIR -> KIRMIZI kalir");
ona(mc({ farkUrunuMu: null }) === false, "H10 marka-cip: yuklem YOK -> fail-closed KIRMIZI");
ona(mc({ anaSinif: A }) === false, "H11 marka-cip: uc main sitesiyle de ayrisiyor -> KIRMIZI");
ona(mc({ bekIds: ["b", "a"] }) === false, "H12 marka-cip: dal == main -> kod farki YOK, KIRMIZI");
ona(mc({ fark: [] }) === false, "H12b marka-cip: TANINMIS farki BOS -> sinif 0");
const fu = P.farkUrunuKur(new Map([
  ["p1", { id: "p1", marka: ["Blackmagic"] }], ["p2", { id: "p2", marka: [] }],
  ["p3", { id: "p3", marka: ["Puig"] }]]), { p2: '["BYD","Mini"]', p3: '["Mini"]' });
const FF = new Set(["Blackmagic", "BYD"]);
ona(fu("p1", FF) && fu("p2", FF) && !fu("p3", FF) && !fu("yok", FF),
  "H13 farkUrunuKur: marka[] ∩ F VE dal kanonu ∩ F kabul; fark-disi + bilinmeyen id RED");

ona(JSON.stringify(R.taninmisFarki(["A", "B", "C"], ["B", "C", "D"])) === '["A","D"]',
  "F1 simetrik fark iki yonlu");
ona(R.taninmisFarki(["B", "A"], ["A", "B"]).length === 0, "F2 sira farki fark DEGIL");

function cocuk(env) {
  const kod = "const R=require(" + JSON.stringify(path.join(__dirname, "index-arama-referansi.js")) +
    ");const a=R.anaReferans();const d=R.referans();" +
    "process.stdout.write(JSON.stringify({ref:!!a.ref,ayni:!!a.ayni,hata:a.hata||null," +
    "fark:a.fark||[],tutarli:(a.fark||[]).every(function(m){" +
    "return (d.TANINMIS_MARKALAR.indexOf(m)!==-1)!==(a.ref?a.ref.TANINMIS_MARKALAR.indexOf(m)!==-1:false);})}));";
  const out = execFileSync(process.execPath, ["-e", kod],
    { encoding: "utf8", env: Object.assign({}, process.env, env), maxBuffer: 64 * 1024 * 1024 });
  return JSON.parse(out);
}

const iz = () => fs.readdirSync(os.tmpdir()).filter((d) => d.startsWith("pruvo-kod-senkron-")).length;
const izOnce = iz();
const g1 = cocuk({});
ona(!g1.hata && (g1.ref || g1.ayni), "G1 gercek agac: anaReferans hatasiz (" +
  (g1.ref ? "ref kuruldu, fark " + g1.fark.length : g1.ayni ? "fark BOS" : "hata=" + g1.hata) + ")");
const g2 = cocuk({ PARITE_KOD_SENKRON_REF: "refs/heads/yok-boyle-bir-ref-kod-senkron" });
ona(!!g2.hata && !g2.ref, "G2 gecersiz ref -> hata (sinif KAPALI, fail-closed)");
const g5 = cocuk({ PARITE_KOD_SENKRON_REF: "HEAD" });
const headTemiz = execFileSync("git", ["-C", KOK, "status", "--porcelain", "--", "index.html"],
  { encoding: "utf8" }).trim() === "";
if (headTemiz) {
  ona(g5.ayni && !g5.ref && g5.fark.length === 0,
    "G5 BORC KAPANIS KOLU: referans == dalin kendisi -> fark BOS, sinif 0 (main SERIT B'de KOD-SENKRON dogamaz)");
} else {
  console.log("  BILGI G5 atlandi: index.html calisma agacinda degismis (HEAD ile kiyas anlamsiz)");
}
ona(iz() === izOnce, "G3 gecici kok silindi (once=" + izOnce + " sonra=" + iz() + ")");
if (g1.ref) {
  ona(g1.fark.length > 0 && g1.tutarli, "G4 fark BOS DEGIL ve her ad TAM bir tarafta (" +
    g1.fark.join(", ") + ")");
} else {
  console.log("  BILGI G4 atlandi: TANINMIS farki BOS (sinif bos, olcecek fark yok)");
}

// G6 MARKA-CIP GERCEK AGAC (26 Eki): main referansi marka_kanon tasir ve dal ↔ main kanon
// farki TAMAMI TANINMIS farkindan turer. 🔴 Ayni zamanda OLCUM KUSURU nobeti: kanon dalin
// DEGIL main'in index.html'iyle kurulsaydi (worktree'de veri koku = ana checkout) fark 0
// cikardi ve marka-cip ekseni dal semantigini HIC gormezdi (tik 182 "yerel tekrar 0").
if (g1.ref) {
  const SINIF = require("./parite-marka-sinifi.js");
  const A6 = R.anaReferans();
  const mk = A6.ref && A6.ref.markaKanon;
  ona(!!mk && typeof mk === "object" && Object.keys(mk).length > 0,
    "G6a main referansi marka_kanon TASIR (marka-cip kolu kurulabilir)");
  if (mk) {
    const U = P.urunleriYukle();
    const dalK = SINIF.markaSinifi(U).markaKanon;
    const F6 = new Set(A6.fark);
    const fu6 = P.farkUrunuKur(new Map(U.map((p) => [p.id, p])), dalK);
    let farkSay = 0;
    const disi = [];
    for (const p of U) {
      if ((dalK[p.id] || "") !== (mk[p.id] || "")) {
        farkSay++;
        if (!fu6(p.id, F6)) disi.push(p.id);
      }
    }
    ona(farkSay > 0 && disi.length === 0, "G6b dal ↔ main kanon farki (" + farkSay +
      " urun) TAMAMI TANINMIS farkindan (fark-disi=" + disi.length +
      (disi.length ? " ilk: " + disi.slice(0, 5).join(",") : "") + ")");
  }
} else {
  console.log("  BILGI G6 atlandi: TANINMIS farki BOS (main referansi kurulmadi)");
}

console.log("-".repeat(70));
if (kalan.length) {
  console.log("SONUC: %d iddia KALDI ❌", kalan.length);
  process.exit(1);
}
console.log("SONUC: KOD-SENKRON kabul hepsi GECTI ✔");
