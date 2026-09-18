#!/usr/bin/env node
/**
 * POST /api/onizleme/olustur DERLEME TAVANI — kabul bataryasi (18 Eyl 2026, public uc taramasi).
 *
 * NEDEN VAR: /olustur herkese aciktir; her onbellek ISKASI tek paylasilan derleyici
 * konteynerine OpenSCAD isi yukler (ayni konteyner yonetimin /ic-derle uretim STL'ini de
 * derler). Tek fren izolat-ici bir Map'ti — ayni desen shop /fiyat'ta canli olculmus ve
 * yeni baglantili istemciye 40/40 200 donmustu (fren YOK). Onarim: native Cloudflare rate
 * limiting binding (ONIZLEME_RATE_LIMIT); binding yok/patlarsa eski izolat sayacina duser.
 *
 * IDDIALAR (GERCEK onizleme/src/index.js, sahte R2 + sahte derleyici ile):
 *   V1 limiter success:false -> 429 · derleyici CAGRILMAZ · R2'ye YAZILMAZ
 *   V2 limiter success:true  -> 200 · derleyici 1 kez
 *   V3 limiter anahtari = CF-Connecting-IP
 *   V4 onbellek ISABETI limiter'a SORULMAZ (muafiyet korunur) ve 200 doner
 *   V5 binding YOK  -> izolat sayaci devrede: ayni IP'den 11. derleme 429 (fail-open DEGIL)
 *   V6 limiter PATLAR -> izolat sayacina duser: 1. istek 200, 11. istek 429
 *   V7 onizleme/wrangler.toml ONIZLEME_RATE_LIMIT blogu var; namespace shop'unkilerden AYRI
 *   M1 MUTANT: /olustur'daki tavan cagrisi etkisizlesirse V1 KIRMIZI yanar
 *   M2 MUTANT: binding-yok kolu izolat sayaci yerine `false` donerse V5 KIRMIZI yanar
 * OFFLINE: ag yok, wrangler yok, R2 yok. Repo dosyasi YAZILMAZ (gecici dizin, cikista silinir).
 * Calistir: node onizleme/test/derleme-hiz-siniri.mjs  -> rc=0 ve "SONUC: YESIL"
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const ONIZLEME = path.dirname(TEST_DIR);
const KOK = path.dirname(ONIZLEME);
const SRC = path.join(ONIZLEME, "src");
const SHOP_SRC = path.join(KOK, "shop", "src");

// Gecici dizin onizleme/src ILE AYNI DERINLIKTE: ../../secenekler.js ve
// ../../jenerator/konfigurator.js GERCEK dosyalara cozulur (onbellek-surum.mjs deseni).
const TEMP_ONEK = "src-test-tmp-hiz-";
const TEMP_DIZIN = path.join(ONIZLEME, TEMP_ONEK + process.pid);

function jsonGom(kaynak, kaynakDizin) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) { throw new Error("JSON import gomulemedi"); }
  return cikti;
}

for (const ad of fs.readdirSync(ONIZLEME)) {
  if (ad.startsWith(TEMP_ONEK)) { fs.rmSync(path.join(ONIZLEME, ad), { recursive: true, force: true }); }
}
fs.mkdirSync(TEMP_DIZIN, { recursive: true });
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });
fs.writeFileSync(path.join(TEMP_DIZIN, "derleyici.js"),
                 fs.readFileSync(path.join(SRC, "derleyici.js"), "utf8"));
fs.writeFileSync(path.join(TEMP_DIZIN, "semalar.js"),
                 jsonGom(fs.readFileSync(path.join(SHOP_SRC, "semalar.js"), "utf8"), SHOP_SRC));

let sayac = 0;
/** Her cagri TAZE modul: izolat sayaci (modul-ici Map) senaryolar arasinda tasinmaz. */
async function yukle(kaynak) {
  const yeni = kaynak.replace('from "../../shop/src/semalar.js"', 'from "./semalar.js"');
  if (yeni === kaynak) { throw new Error("semalar.js import yolu bulunamadi — yukleyici bayat"); }
  sayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-" + sayac + ".js");
  fs.writeFileSync(yol, jsonGom(yeni, SRC));
  return await import(pathToFileURL(yol).href);
}

let derleyiciCagri = 0;
globalThis.fetch = async function (hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.startsWith("http://derleyici.test/")) {
    derleyiciCagri += 1;
    return new Response(new Uint8Array(84), { status: 200 });   // bos ikili STL
  }
  throw new Error("beklenmeyen ag cagrisi: " + u);
};

const console_error = console.error;
console.error = () => {};   // worker'in bilincli yuksek sesli loglari test ciktisini bogmasin

const AILE = "olcuye-ozel-cerceve";
const PARAM = { acilik_eni: 100, acilik_boyu: 150, kenar_genisligi: 12,
                derinlik: 5.2, kenar_stili: "chamfer", yazi: "OKAN" };

function r2Sahte(isabet) {
  const r2 = { yazma: 0,
    async get() { return isabet ? { body: new Uint8Array(4), customMetadata: { hamBoyut: "84" } } : null; },
    async put() { r2.yazma += 1; } };
  return r2;
}

async function cagir(mod, limiter, secenek) {
  const s = secenek || {};
  const env = { SITE_URL: "https://pruvo3d.com", DERLEYICI_URL: "http://derleyici.test",
                ONBELLEK: r2Sahte(!!s.isabet) };
  if (limiter !== undefined) { env.ONIZLEME_RATE_LIMIT = limiter; }
  const once = derleyiciCagri;
  const istek = new Request("https://pruvo3d.com/api/onizleme/olustur", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": "203.0.113.9" },
    body: JSON.stringify({ aile: AILE, parametreler: PARAM }),
  });
  const cevap = await mod.default.fetch(istek, env);
  return { kod: cevap.status, derleyici: derleyiciCagri - once, r2Yazma: env.ONBELLEK.yazma };
}

/** Ayni modulde ayni IP'den n istek; son cevabi ve 429 alinan ilk sirayi doner. */
async function seri(mod, limiter, n) {
  let ilk429 = 0;
  let son = null;
  for (let i = 1; i <= n; i++) {
    son = await cagir(mod, limiter);
    if (son.kod === 429 && !ilk429) { ilk429 = i; }
  }
  return { ilk429, son };
}

const sonuclar = [];
function iddia(ad, kosul, detay) { sonuclar.push({ ad, kosul: Boolean(kosul), detay }); }

const kaynak = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
const reddeden = { async limit() { return { success: false }; } };
const patlayan = { async limit() { throw new Error("patladi"); } };

let r = await cagir(await yukle(kaynak), reddeden);
iddia("V1 tavan asildi -> 429, derleyici 0, R2 yazma 0",
  r.kod === 429 && r.derleyici === 0 && r.r2Yazma === 0, JSON.stringify(r));

let gorulen = null;
let sorulma = 0;
const kabul = { async limit(o) { sorulma += 1; gorulen = o && o.key; return { success: true }; } };
r = await cagir(await yukle(kaynak), kabul);
iddia("V2 tavan asilmadi -> 200, derleyici 1", r.kod === 200 && r.derleyici === 1, JSON.stringify(r));
iddia("V3 anahtar = CF-Connecting-IP", gorulen === "203.0.113.9", String(gorulen));

sorulma = 0;
r = await cagir(await yukle(kaynak), kabul, { isabet: true });
iddia("V4 onbellek isabeti limiter'a sorulmaz + 200", r.kod === 200 && sorulma === 0 && r.derleyici === 0,
  JSON.stringify({ ...r, sorulma }));

let s = await seri(await yukle(kaynak), undefined, 11);
iddia("V5 binding yok -> izolat sayaci: 11. istek 429", s.ilk429 === 11, JSON.stringify(s));

s = await seri(await yukle(kaynak), patlayan, 11);
iddia("V6 limiter patlar -> izolat sayaci: ilk 10 gecer, 11. 429", s.ilk429 === 11, JSON.stringify(s));

const onizToml = fs.readFileSync(path.join(ONIZLEME, "wrangler.toml"), "utf8");
const shopToml = fs.readFileSync(path.join(KOK, "shop", "wrangler.toml"), "utf8");
const BLOK_RE = /name\s*=\s*"([A-Z_]+_RATE_LIMIT)"\s*\ntype\s*=\s*"ratelimit"\s*\nnamespace_id\s*=\s*"(\d+)"\s*\nsimple\s*=\s*\{\s*limit\s*=\s*(\d+)\s*,\s*period\s*=\s*(\d+)\s*\}/g;
const blok = (t) => [...t.matchAll(BLOK_RE)].map((m) => ({ ad: m[1], ns: m[2], limit: +m[3], period: +m[4] }));
const oniz = blok(onizToml).find((b) => b.ad === "ONIZLEME_RATE_LIMIT");
const hepsi = blok(onizToml).concat(blok(shopToml)).map((b) => b.ns);
iddia("V7 wrangler.toml ONIZLEME_RATE_LIMIT var (10/60) + namespace hesap genelinde benzersiz",
  oniz && oniz.limit === 10 && oniz.period === 60 && new Set(hepsi).size === hepsi.length,
  JSON.stringify({ oniz, hepsi }));

// M1: tavan cagrisini etkisizlestir -> V1 KIRMIZI olmali
const cagri = "if (await derlemeHizSiniriAsildi(request, env)) {";
const adet1 = kaynak.split(cagri).length - 1;
iddia("M1 capa kaynakta TEK", adet1 === 1, "adet=" + adet1);
if (adet1 === 1) {
  const m = await cagir(await yukle(kaynak.replace(cagri, "if (false) {")), reddeden);
  iddia("M1 mutant (cagri etkisiz) V1'i KIRMIZI yakar", m.kod !== 429, JSON.stringify(m));
}

// M2: binding-yok/patlama kolu fail-open'a cevrilirse -> V5 KIRMIZI olmali
const dusus = "  return hizSiniriAsildi(ip);\n}";
const adet2 = kaynak.split(dusus).length - 1;
iddia("M2 capa kaynakta TEK", adet2 === 1, "adet=" + adet2);
if (adet2 === 1) {
  const m = await seri(await yukle(kaynak.replace(dusus, "  return false;\n}")), undefined, 11);
  iddia("M2 mutant (izolat dususu yerine fail-open) V5'i KIRMIZI yakar", m.ilk429 === 0, JSON.stringify(m));
}

console.error = console_error;
let kirmizi = 0;
for (const x of sonuclar) {
  if (!x.kosul) { kirmizi += 1; }
  console.log((x.kosul ? "  ✅ " : "  🔴 ") + x.ad + (x.kosul ? "" : "  -> " + x.detay));
}
console.log("IDDIA=" + sonuclar.length + " KIRMIZI=" + kirmizi);
console.log("SONUC: " + (kirmizi === 0 ? "YESIL" : "KIRMIZI"));
process.exit(kirmizi === 0 ? 0 : 1);
