/**
 * POST /api/shop/baslat IP TAVANI — kabul bataryasi (17 Eyl 2026).
 *
 * OLCULEN OLAY: 17 Eyl 00:44-02:30Z bir bot sahte musteri verisiyle 96 kart odemesi BASLATTI
 * (en ucuz 15 TL urun, saniye arali seriler, uydurma GA/fbp kimlikleri) — uc tavansizdi.
 *
 * IDDIALAR (her biri GERCEK worker kodundan, sahte D1 + sahte iyzico ile):
 *   V1 tavan asildi (limiter success:false) -> 429 · D1'e siparis YAZILMAZ · iyzico ACILMAZ
 *   V2 tavan asilmadi (success:true)        -> 429 DEGIL (istek islenir)
 *   V3 binding YOK                          -> 429 DEGIL (FAIL-OPEN: odeme yolu kapanmaz)
 *   V4 limiter patlar                       -> 429 DEGIL (fail-open)
 *   V5 limiter anahtari CF-Connecting-IP
 *   V6 wrangler.toml BASLAT_RATE_LIMIT blogu var, namespace diger limiterlardan AYRI
 *   M1 MUTANT: baslat() icindeki tavan cagrisi silinirse V1 KIRMIZI yanar (bekci olu degil)
 * Calistir: node shop/test/baslat-hiz-siniri.mjs  -> rc=0 ve "SONUC: YESIL"
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const SRC = path.join(SHOP, "src");
const TEMP_ONEK = "src-test-tmp-baslat-";
const TEMP_DIZIN = path.join(SHOP, TEMP_ONEK + process.pid);

function jsonGom(kaynak) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(SRC, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) { throw new Error("JSON import gomulemedi"); }
  return cikti;
}

for (const ad of fs.readdirSync(SHOP)) {
  if (ad.startsWith(TEMP_ONEK)) { fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true }); }
}
fs.mkdirSync(TEMP_DIZIN, { recursive: true });
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });
for (const ad of fs.readdirSync(SRC)) {
  if (/\.m?js$/.test(ad)) {
    fs.writeFileSync(path.join(TEMP_DIZIN, ad), jsonGom(fs.readFileSync(path.join(SRC, ad), "utf8")));
  }
}

let sayac = 0;
async function yukle(kaynak) {
  sayac += 1;
  const yol = path.join(TEMP_DIZIN, "index-baslat-" + sayac + ".js");
  fs.writeFileSync(yol, jsonGom(kaynak));
  return await import(pathToFileURL(yol).href);
}

let iyzicoCagri = 0;
globalThis.fetch = async function (hedef) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (u.includes("iyzico.test")) {
    iyzicoCagri += 1;
    return new Response(JSON.stringify({ status: "success", token: "t-" + iyzicoCagri,
      paymentPageUrl: "https://odeme.test/s" }), { status: 200 });
  }
  return new Response("{}", { status: 200 });   // telegram/olcum yan kanallari
};

function d1Sahte(kayitlar) {
  return {
    prepare(sql) {
      return { bind(...arg) { return {
        async all() { return { results: [] }; },
        async first() { return null; },
        async run() { kayitlar.push({ sql, arg }); return { meta: { changes: 1 } }; },
      }; } };
    },
  };
}

async function cagir(mod, limiter) {
  const kayitlar = [];
  const env = { SITE_URL: "https://pruvo3d.com", IYZICO_BASE_URL: "https://iyzico.test",
    IYZICO_API_KEY: "k", IYZICO_SECRET_KEY: "s", KATALOG: d1Sahte(kayitlar) };
  if (limiter !== undefined) { env.BASLAT_RATE_LIMIT = limiter; }
  const once = iyzicoCagri;
  const istek = new Request("https://pruvo3d.com/api/shop/baslat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": "203.0.113.7" },
    body: JSON.stringify({ sozlesme_onay: true, odeme: "kart", sepet: [],
      musteri: { ad: "Test Musteri", tel: "05321112233", eposta: "test@pruvo3d.com",
                 adres: "Test mahallesi test sokak no 1", sehir: "Mugla" } }),
  });
  const cevap = await mod.default.fetch(istek, env, { waitUntil() {} });
  return { kod: cevap.status,
           d1Siparis: kayitlar.some((k) => /INSERT INTO siparisler/.test(k.sql)),
           iyzico: iyzicoCagri > once };
}

const sonuclar = [];
function iddia(ad, kosul, detay) { sonuclar.push({ ad, kosul: Boolean(kosul), detay }); }

const kaynak = fs.readFileSync(path.join(SRC, "index.js"), "utf8");
const mod = await yukle(kaynak);

const reddeden = { async limit() { return { success: false }; } };
let r = await cagir(mod, reddeden);
iddia("V1 tavan asildi -> 429, D1 yok, iyzico yok",
  r.kod === 429 && !r.d1Siparis && !r.iyzico, JSON.stringify(r));

let gorulenAnahtar = null;
const kabul = { async limit(o) { gorulenAnahtar = o && o.key; return { success: true }; } };
r = await cagir(mod, kabul);
iddia("V2 tavan asilmadi -> 429 DEGIL", r.kod !== 429, JSON.stringify(r));
iddia("V5 anahtar = CF-Connecting-IP", gorulenAnahtar === "203.0.113.7", String(gorulenAnahtar));

r = await cagir(mod, undefined);
iddia("V3 binding yok -> fail-open (429 DEGIL)", r.kod !== 429, JSON.stringify(r));

r = await cagir(mod, { async limit() { throw new Error("patladi"); } });
iddia("V4 limiter patladi -> fail-open (429 DEGIL)", r.kod !== 429, JSON.stringify(r));

const toml = fs.readFileSync(path.join(SHOP, "wrangler.toml"), "utf8");
const bloklar = [...toml.matchAll(/name\s*=\s*"([A-Z_]+_RATE_LIMIT)"\s*\ntype\s*=\s*"ratelimit"\s*\nnamespace_id\s*=\s*"(\d+)"/g)]
  .map((m) => ({ ad: m[1], ns: m[2] }));
const baslatBlok = bloklar.find((b) => b.ad === "BASLAT_RATE_LIMIT");
const nsler = bloklar.map((b) => b.ns);
iddia("V6 wrangler.toml BASLAT_RATE_LIMIT var + namespace benzersiz",
  baslatBlok && new Set(nsler).size === nsler.length, JSON.stringify(bloklar));

// M1: tavan cagrisini sil -> V1 KIRMIZI olmali
const cagriSatiri = "if (await baslatHizSiniriAsildi(request, env)) { return cokIstek(env); }";
const adet = kaynak.split(cagriSatiri).length - 1;
iddia("M1 capa kaynakta TEK", adet === 1, "adet=" + adet);
if (adet === 1) {
  const mutant = await yukle(kaynak.replace(cagriSatiri, ""));
  const m = await cagir(mutant, reddeden);
  iddia("M1 mutant (cagri silindi) V1'i KIRMIZI yakar", m.kod !== 429, JSON.stringify(m));
}

let kirmizi = 0;
for (const s of sonuclar) {
  if (!s.kosul) { kirmizi += 1; }
  console.log((s.kosul ? "  ✅ " : "  🔴 ") + s.ad + (s.kosul ? "" : "  -> " + s.detay));
}
console.log("IDDIA=" + sonuclar.length + " KIRMIZI=" + kirmizi);
console.log("SONUC: " + (kirmizi === 0 ? "YESIL" : "KIRMIZI"));
process.exit(kirmizi === 0 ? 0 : 1);
