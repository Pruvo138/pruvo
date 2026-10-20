#!/usr/bin/env node
/**
 * URETIM SAGLAYICI VEKIL UCU KABUL TESTI (shop/src/uretim-vekil.js; Okan 20 Eki 2026
 * pencere secimi "KraL araci kursun").
 *
 *   node shop/test/uretim-vekil.mjs
 *
 * NASIL (OFFLINE — wrangler/ag/gercek saglayici YOK): shop/src gecici kopyaya alinir
 * (shop/src-test-tmp-vekil-<pid>/, JSON import'lari gomulu — konfigur-fail-closed.mjs deseni),
 * index.js'in KENDISI ve uretim-vekil.js yuklenir; D1 ve saglayici bellek-ici sahtedir.
 *
 * VAKALAR:
 *   V1  secret YOK -> 404, saglayiciya 0 cagri
 *   V2  secret KISA (<32) ve jeton ayni -> 404 (uzunluk tabani)
 *   V3  yanlis jeton -> 404, saglayiciya 0
 *   V4  dogru jeton GET balance -> saglayici /v1/balance, Bearer anahtar YALNIZ giden istekte,
 *       cevapta anahtar 0
 *   V5  izin kumesi disi yol / yontem -> 404, saglayiciya 0
 *   V6  retexture/<gorev>: bozuk kimlik 400 (0 cagri) · gecerli -> /v1/retexture/<gorev>
 *   V7  multi-color/<gorev> GET -> /v1/print/multi-color/<gorev>
 *   V8  POST model_url: http / yabanci alan / kok-taklidi alan / taban YOK -> 400, 0 cagri
 *   V9  POST max_colors 0 / 9 / "4" / 2.5 -> 400, 0 cagri
 *   V10 POST gecerli + fazladan alan -> saglayiciya YENIDEN KURULAN govde (3 alan, bambu),
 *       foto_kredi'ye 'vekil-renk' 10 kredi TEK satir
 *   V11 ayni gun 2. POST -> 429, saglayiciya 0 (gunluk tavan 1)
 *   V12 saglayici 402 -> kod aynen, defter satiri 0, tavan TUKENMEZ
 *   V13 ag hatasi -> 502
 *   V14 index.js rotasi: /api/shop/ic/uretim-vekil/balance jetonlu -> saglayici; jetonsuz 404
 * MUTANTLAR (gecici kopyada; her biri en az bir vakayi KIRMIZI yakmali):
 *   M1 yetki kontrolu kalkti · M2 uzunluk tabani kalkti · M3 alan kontrolu kalkti ·
 *   M4 govde aynen iletilir · M5 gunluk tavan kalkti · M6 kredi defteri yazilmaz
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const SRC = path.join(SHOP, "src");
const TEMP_ONEK = "src-test-tmp-vekil-";
const TEMP_DIZIN = path.join(SHOP, TEMP_ONEK + process.pid);

function jsonGom(kaynak, kaynakDizin, etiket) {
  const cikti = kaynak.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, ad, rel) => {
      const ham = fs.readFileSync(path.resolve(kaynakDizin, rel), "utf8").trim();
      JSON.parse(ham);
      return "const " + ad + " = " + ham + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(cikti)) {
    throw new Error("JSON import gomulemedi (" + etiket + ") — desen guncellenmeli");
  }
  return cikti;
}

for (const ad of fs.readdirSync(SHOP)) {
  if (ad.startsWith(TEMP_ONEK)) { fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true }); }
}
fs.mkdirSync(TEMP_DIZIN, { recursive: true });
process.on("exit", () => { fs.rmSync(TEMP_DIZIN, { recursive: true, force: true }); });
for (const ad of fs.readdirSync(SRC)) {
  if (!/\.m?js$/.test(ad)) { continue; }
  fs.writeFileSync(path.join(TEMP_DIZIN, ad), jsonGom(fs.readFileSync(path.join(SRC, ad), "utf8"), SRC, ad));
}

// ---------------------------------------------------------------- sahte cevre

const ANAHTAR = "test-saglayici-anahtari-ASLA-CEVAPTA-OLMAZ";
const JETON = "j".repeat(40);
const TABAN = "https://api.saglayici.test";
const SIMDI = Date.UTC(2026, 9, 20, 12, 0, 0);

let cagrilar = [];
let saglayiciDavranis = "ok";            // ok | 402 | ag
globalThis.fetch = async function sahteFetch(hedef, opt) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  if (!u.startsWith(TABAN)) { throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u); }
  const o = opt || {};
  cagrilar.push({ url: u, yontem: o.method, yetki: (o.headers || {})["Authorization"], govde: o.body });
  if (saglayiciDavranis === "ag") { throw new Error("ag yok"); }
  if (saglayiciDavranis === "402") {
    return new Response(JSON.stringify({ message: "yetersiz kredi" }), { status: 402 });
  }
  const yol = u.slice(TABAN.length);
  const govde = yol === "/v1/balance" ? { balance: 123 }
    : (o.method === "POST" ? { result: "gorev-0123456789" } : { id: yol.split("/").pop(), status: "SUCCEEDED" });
  return new Response(JSON.stringify(govde), { status: 200, headers: { "Content-Type": "application/json" } });
};

function d1Sahte(satirlar) {
  return {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async first() {
              if (/SELECT COUNT\(\*\) AS n FROM foto_kredi/.test(sql)) {
                return { n: satirlar.filter((s) => s.adim === "vekil-renk" && s.tarih.slice(0, 10) === arg[0]).length };
              }
              throw new Error("BEKLENMEYEN first SQL: " + sql);
            },
            async run() {
              if (/INSERT OR IGNORE INTO foto_kredi/.test(sql)) {
                const [tarih, siparis_no, gorev, kredi] = arg;
                satirlar.push({ tarih, adim: "vekil-renk", is_no: "vekil", siparis_no, gorev, kredi });
                return { success: true };
              }
              throw new Error("BEKLENMEYEN run SQL: " + sql);
            },
          };
        },
      };
    },
  };
}

function ortam(ek) {
  const satirlar = [];
  return Object.assign({ URETIM_API_ANAHTAR: ANAHTAR, URETIM_API_TABAN: TABAN, URETIM_VEKIL_JETON: JETON,
                         KATALOG: d1Sahte(satirlar), _satirlar: satirlar }, ek || {});
}

function istek(yol, yontem, jeton, govde) {
  const h = { "Content-Type": "application/json" };
  if (jeton !== null) { h["X-Vekil-Jeton"] = jeton; }
  return new Request("https://pruvo3d.com/api/shop/ic/uretim-vekil/" + yol,
                     { method: yontem, headers: h, body: govde === undefined ? undefined : JSON.stringify(govde) });
}

// ---------------------------------------------------------------- vaka kumesi

async function vakalar(M) {
  const s = {};
  const cagir = async (env, yol, yontem, jeton, govde) => {
    const r = await M.uretimVekil(istek(yol, yontem, jeton, govde), env, "/ic/uretim-vekil/" + yol, SIMDI);
    const metin = await r.text();
    return { kod: r.status, metin };
  };
  const sifirla = () => { cagrilar = []; saglayiciDavranis = "ok"; };
  const dene = async (ad, f) => { sifirla(); try { s[ad] = !!(await f()); } catch (e) { s[ad] = false; s[ad + "_hata"] = String(e); } };

  await dene("V1", async () => {
    const r = await cagir(ortam({ URETIM_VEKIL_JETON: undefined }), "balance", "GET", "");
    const r2 = await cagir(ortam({ URETIM_VEKIL_JETON: undefined }), "balance", "GET", JETON);
    return r.kod === 404 && r2.kod === 404 && cagrilar.length === 0;
  });
  await dene("V2", async () => {
    const r = await cagir(ortam({ URETIM_VEKIL_JETON: "kisa-jeton" }), "balance", "GET", "kisa-jeton");
    return r.kod === 404 && cagrilar.length === 0;
  });
  await dene("V3", async () => {
    const a = await cagir(ortam(), "balance", "GET", "y".repeat(40));
    const b = await cagir(ortam(), "balance", "GET", null);
    return a.kod === 404 && b.kod === 404 && cagrilar.length === 0;
  });
  await dene("V4", async () => {
    const r = await cagir(ortam(), "balance", "GET", JETON);
    return r.kod === 200 && cagrilar.length === 1 && cagrilar[0].url === TABAN + "/v1/balance" &&
      cagrilar[0].yetki === "Bearer " + ANAHTAR && !r.metin.includes(ANAHTAR) && JSON.parse(r.metin).govde.balance === 123;
  });
  await dene("V5", async () => {
    const yollar = [["text-to-3d", "GET"], ["text-to-3d", "POST"], ["balance", "POST"], ["balance", "DELETE"],
                    ["multi-color", "GET"], ["retexture", "POST"], ["../v1/balance", "GET"], ["", "GET"]];
    for (const [y, m] of yollar) {
      const r = await cagir(ortam(), y, m, JETON, m === "POST" ? {} : undefined);
      if (r.kod !== 404) { return false; }
    }
    return cagrilar.length === 0;
  });
  await dene("V6", async () => {
    const bozuk = await cagir(ortam(), "retexture/kisa", "GET", JETON);
    const bozuk2 = await cagir(ortam(), "retexture/abc$defghij", "GET", JETON);
    if (bozuk.kod !== 400 || bozuk2.kod !== 400 || cagrilar.length !== 0) { return false; }
    const r = await cagir(ortam(), "retexture/gorev-ABCDEF12", "GET", JETON);
    return r.kod === 200 && cagrilar.length === 1 && cagrilar[0].url === TABAN + "/v1/retexture/gorev-ABCDEF12";
  });
  await dene("V7", async () => {
    const r = await cagir(ortam(), "multi-color/gorev-ABCDEF12", "GET", JETON);
    return r.kod === 200 && cagrilar.length === 1 && cagrilar[0].url === TABAN + "/v1/print/multi-color/gorev-ABCDEF12" &&
      cagrilar[0].yontem === "GET";
  });
  await dene("V8", async () => {
    const kotu = ["http://assets.saglayici.test/m.glb", "https://kotu.example/m.glb",
                  "https://saglayici.test.kotu.example/m.glb", "https://kotusaglayici.test/m.glb", "bozuk", ""];
    for (const m of kotu) {
      const r = await cagir(ortam(), "multi-color", "POST", JETON, { model_url: m, max_colors: 4 });
      if (r.kod !== 400) { return false; }
    }
    const tabansiz = await cagir(ortam({ URETIM_API_TABAN: "" }), "multi-color", "POST", JETON,
                                 { model_url: "https://assets.saglayici.test/m.glb", max_colors: 4 });
    return tabansiz.kod === 400 && cagrilar.length === 0;
  });
  await dene("V9", async () => {
    for (const n of [0, 9, "4", 2.5, null, -1]) {
      const r = await cagir(ortam(), "multi-color", "POST", JETON, { model_url: "https://assets.saglayici.test/m.glb", max_colors: n });
      if (r.kod !== 400) { return false; }
    }
    return cagrilar.length === 0;
  });
  await dene("V10", async () => {
    const env = ortam();
    const r = await cagir(env, "multi-color", "POST", JETON,
      { model_url: "https://assets.saglayici.test/m.glb", max_colors: 8, printer_brand: "baska",
        callback_url: "https://kotu.example/cb", siparis_no: "PR-201026-120000-AB1" });
    if (r.kod !== 200 || cagrilar.length !== 1) { return false; }
    const g = JSON.parse(cagrilar[0].govde);
    const anahtarlar = Object.keys(g).sort().join(",");
    return cagrilar[0].url === TABAN + "/v1/print/multi-color" && anahtarlar === "max_colors,model_url,printer_brand" &&
      g.printer_brand === "bambu" && g.max_colors === 8 && env._satirlar.length === 1 &&
      env._satirlar[0].kredi === 10 && env._satirlar[0].gorev === "gorev-0123456789" &&
      env._satirlar[0].siparis_no === "PR-201026-120000-AB1" && !r.metin.includes(ANAHTAR);
  });
  await dene("V11", async () => {
    const env = ortam();
    const govde = { model_url: "https://assets.saglayici.test/m.glb", max_colors: 4 };
    const a = await cagir(env, "multi-color", "POST", JETON, govde);
    const once = cagrilar.length;
    const b = await cagir(env, "multi-color", "POST", JETON, govde);
    return a.kod === 200 && once === 1 && b.kod === 429 && cagrilar.length === 1 && env._satirlar.length === 1;
  });
  await dene("V12", async () => {
    const env = ortam();
    const govde = { model_url: "https://assets.saglayici.test/m.glb", max_colors: 4 };
    saglayiciDavranis = "402";
    const a = await cagir(env, "multi-color", "POST", JETON, govde);
    saglayiciDavranis = "ok";
    const b = await cagir(env, "multi-color", "POST", JETON, govde);
    return a.kod === 402 && JSON.parse(a.metin).kod === 402 && b.kod === 200 && env._satirlar.length === 1;
  });
  await dene("V13", async () => {
    saglayiciDavranis = "ag";
    const r = await cagir(ortam(), "balance", "GET", JETON);
    return r.kod === 502 && JSON.parse(r.metin).kod === 0;
  });
  return s;
}

// ---------------------------------------------------------------- kosum

let kirmizi = 0;
function ol(ad, kosul, ayrinti) {
  console.log((kosul ? "  YESIL  " : "  KIRMIZI ") + ad + (kosul || ayrinti === undefined ? "" : "  <- " + ayrinti));
  if (!kosul) { kirmizi += 1; }
}

const gercek = await import(pathToFileURL(path.join(TEMP_DIZIN, "uretim-vekil.js")).href);
console.log("VEKIL UCU — gercek kaynak");
const sonuc = await vakalar(gercek);
const VAKA_ADLARI = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12", "V13"];
for (const ad of VAKA_ADLARI) { ol(ad, sonuc[ad] === true, sonuc[ad + "_hata"]); }

console.log("V14) index.js rotasi");
{
  const idx = await import(pathToFileURL(path.join(TEMP_DIZIN, "index.js")).href);
  cagrilar = []; saglayiciDavranis = "ok";
  const env = ortam();
  const a = await idx.default.fetch(istek("balance", "GET", JETON), env, { waitUntil() {} });
  const aCagri = cagrilar.length;
  const b = await idx.default.fetch(istek("balance", "GET", null), env, { waitUntil() {} });
  ol("V14 jetonlu rota saglayiciya ulasir (200, 1 cagri) · jetonsuz 404 (ek cagri 0)",
     a.status === 200 && aCagri === 1 && b.status === 404 && cagrilar.length === 1,
     [a.status, aCagri, b.status, cagrilar.length].join("/"));
}

console.log("MUTANTLAR (gecici kopyada)");
const kaynak = fs.readFileSync(path.join(SRC, "uretim-vekil.js"), "utf8");
const MUTANTLAR = [
  ["M1 yetki kontrolu kalkti", "if (!vekilYetkiliMi(request, env)) { return BULUNAMADI(); }", "", ["V1", "V3"]],
  ["M2 uzunluk tabani kalkti", "if (beklenen.length < 32) { return false; }", "", ["V2"]],
  ["M3 alan kontrolu kalkti", "if (!modelAdresiGecerliMi(g.model_url, env)) { return yanit({ hata: \"model-adresi-gecersiz\" }, 400); }", "", ["V8"]],
  ["M4 govde aynen iletilir", "{ model_url: String(g.model_url), max_colors: n, printer_brand: \"bambu\" }", "g", ["V10"]],
  ["M5 gunluk tavan kalkti", "if (await bugunPostSayisi(env, simdi) >= GUNLUK_POST_TAVANI) {", "if (false) {", ["V11"]],
  ["M6 kredi defteri yazilmaz", "if (c.kod >= 200 && c.kod < 300 && gorev) {", "if (false) {", ["V10"]],
];
let sayac = 0;
for (const [ad, eski, yeni, beklenen] of MUTANTLAR) {
  const n = kaynak.split(eski).length - 1;
  if (n !== 1) { ol(ad + " — capa kaynakta TEK kez bulunmali", false, "isabet " + n); continue; }
  sayac += 1;
  const dosya = path.join(TEMP_DIZIN, "uretim-vekil-mutant-" + sayac + ".js");
  fs.writeFileSync(dosya, kaynak.replace(eski, yeni));
  const s = await vakalar(await import(pathToFileURL(dosya).href));
  const yanan = VAKA_ADLARI.filter((v) => s[v] !== true);
  ol(ad + " -> KIRMIZI yanan: " + (yanan.join(",") || "YOK"), beklenen.every((v) => yanan.includes(v)),
     "beklenen " + beklenen.join(","));
}

console.log(kirmizi === 0 ? "SONUC: YESIL (" + VAKA_ADLARI.length + " vaka + V14 + " + MUTANTLAR.length + " mutant)"
                          : "SONUC: KIRMIZI " + kirmizi);
process.exit(kirmizi === 0 ? 0 : 1);
