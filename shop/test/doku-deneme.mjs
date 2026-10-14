#!/usr/bin/env node
/**
 * PRUVO shop — DOKU DENEMESI kabul kapisi (shop/src/foto.js dokuDenemeUcu; Okan 14 Eki duz-renk 15 kr,
 * dokusuz 5 kr). Kredi harcayan tek seferlik uc; hatasi PARA kaybidir.
 *
 *   node shop/test/doku-deneme.mjs
 *
 * OLCULEN:
 *   C1 canli (ONIZLEME yok) + istek dosyasi VAR -> 404, saglayiciya istek 0, istek dosyasi YERINDE
 *   C2 onizleme + istek YOK -> 404, saglayiciya istek 0 · bilinmeyen tur -> 404, istek 0
 *   C3 duz-renk istek VAR -> TAM 1 POST /v1/image-to-3d, govde SABIT (istekteki <ad>-6-lite, should_texture,
 *      duz renk istemi, pbr kapali, image_url data:image/png), istek SILINDI, durum 'surdu'
 *   C4 yoklama: yeni image-to-3d POST 0; SUCCEEDED -> gorseller + GLB R2'ye, analiz POST 1 (ucretsiz),
 *      analiz bitince durum 'bitti' + printability; sonraki cagri saglayiciya 0 istek; durum kaybolursa 404
 *   C5 istek gecersiz is_no -> POST 0, istek yine silinir
 *   C6 istek modeli -6-lite DEGIL (<ad>-6 = dokulu 30 kr) -> POST 0, istek yine silinir
 *   C7 dokusuz istek -> POST govdesi should_texture:false, texture_prompt YOK, KENDI dizininde
 *      (doku-deneme/dokusuz/); duz-renk dizinindeki durum dokusuz istegini ENGELLEMEZ ve DEGISMEZ
 * MUTANTLAR (gecici kopya shop/src/.mutant-doku-*.mjs, finally'de SILINIR; hedef kume TAM eslesmeli):
 *   M1 onizlemeMi denetimi silindi -> C1 · M2 istek silme satiri silindi -> C3/C4/C5/C6/C7
 *   M3 model kalibi -6-lite'tan -6'ya gevsedi (30 kr) -> C6 · M4 dokusuz govdesinde doku ACIK -> C7
 * CIKIS: 0 yesil · 1 kirmizi.
 */
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURA = dirname(fileURLToPath(import.meta.url));
const KAYNAK = join(BURA, "..", "src", "foto.js");
const IS = "3906f993a476d5a0cd33fa12da49ecbe";
const MODEL = "abcdef-6-lite";
const adres = (tur) => new URL("https://x.invalid/api/shop/foto/doku-deneme" + (tur ? "?tur=" + tur : ""));

function sahteEnv(onizleme, istekler) {
  const kova = new Map();
  kova.set("foto-onizleme/" + IS + ".png", new Uint8Array([137, 80, 78, 71, 1, 2, 3]).buffer);
  for (const [anahtar, v] of Object.entries(istekler || {})) { kova.set(anahtar, JSON.stringify(v)); }
  const nesne = (v) => ({
    text: async () => (typeof v === "string" ? v : new TextDecoder().decode(v)),
    arrayBuffer: async () => (typeof v === "string" ? new TextEncoder().encode(v).buffer : v),
  });
  return {
    kova,
    env: {
      ...(onizleme ? { ONIZLEME: "1" } : {}),
      KATALOG: {}, URETIM_API_ANAHTAR: "k", URETIM_API_TABAN: "https://saglayici.invalid/openapi",
      OZEL_DOSYA: {
        get: async (k) => (kova.has(k) ? nesne(kova.get(k)) : null),
        put: async (k, v) => { kova.set(k, v); },
        delete: async (k) => { kova.delete(k); },
      },
    },
  };
}

function sahteFetch(durumSirasi) {
  const cagri = [];
  globalThis.fetch = async (a, ops) => {
    const o = ops || {};
    const s = String(a);
    cagri.push({ adres: s, yontem: o.method || "GET", govde: o.body ? JSON.parse(o.body) : null });
    const yanit = (kod, v, tip) => ({ status: kod, json: async () => v, headers: { get: (h) => (h === "content-type" ? (tip || null) : null) },
                                      arrayBuffer: async () => new Uint8Array([1, 2]).buffer });
    if (s.startsWith("https://cdn.invalid/")) { return yanit(200, null, "image/png"); }
    if ((o.method || "GET") === "POST") { return yanit(202, { result: s.includes("/print/") ? "analiz-0001" : "gorev-0001" }); }
    if (s.includes("/print/analyze/")) { return yanit(200, { status: "SUCCEEDED", printability: { status: "healthy" } }); }
    const st = durumSirasi.shift() || "IN_PROGRESS";
    return yanit(200, { status: st, progress: 50, consumed_credits: st === "SUCCEEDED" ? 15 : 0,
                        thumbnail_url: "https://cdn.invalid/k.png", alpha_thumbnail_url: "https://cdn.invalid/a.png",
                        model_urls: { glb: "https://cdn.invalid/m.glb" } });
  };
  return cagri;
}

const postlar = (cagri, parca) => cagri.filter((c) => c.yontem === "POST" && c.adres.includes(parca));

async function vakalar(mod) {
  const sonuc = {};
  const v = (ad, kosul) => { sonuc[ad] = sonuc[ad] === false ? false : !!kosul; };
  const u = (env, tur) => mod.dokuDenemeUcu(env, adres(tur));
  // C1
  {
    const { env, kova } = sahteEnv(false, { "doku-deneme/istek.json": { is_no: IS, model: MODEL } });
    const cagri = sahteFetch([]);
    const r = await u(env);
    v("C1", r.status === 404 && cagri.length === 0 && kova.has("doku-deneme/istek.json"));
  }
  // C2
  {
    const { env } = sahteEnv(true, { "doku-deneme/x/istek.json": { is_no: IS, model: MODEL } });
    const cagri = sahteFetch([]);
    const r = await u(env);
    const r2 = await u(env, "x");
    const r3 = await u(env, "__proto__");
    v("C2", r.status === 404 && r2.status === 404 && r3.status === 404 && cagri.length === 0);
  }
  // C3 + C4
  {
    const { env, kova } = sahteEnv(true, { "doku-deneme/istek.json": { is_no: IS, model: MODEL } });
    const cagri = sahteFetch(["IN_PROGRESS", "SUCCEEDED"]);
    const r1 = await (await u(env)).json();
    const post = postlar(cagri, "/image-to-3d");
    const g = post.length === 1 ? post[0].govde : {};
    v("C3", post.length === 1 && post[0].adres.endsWith("/openapi/v1/image-to-3d") &&
      g.ai_model === MODEL && g.should_texture === true && g.enable_pbr === false &&
      g.texture_prompt === "solid matte white, uniform single color, no pattern, no gradient" &&
      String(g.image_url).startsWith("data:image/png;base64,") &&
      !kova.has("doku-deneme/istek.json") && r1.asama === "surdu" && r1.gorev === "gorev-0001");
    const r2 = await (await u(env)).json();
    const r3 = await (await u(env)).json();
    const r4 = await (await u(env)).json();
    const once = cagri.length;
    const r5 = await (await u(env)).json();
    kova.delete("doku-deneme/durum.json");
    const r6 = await u(env);
    v("C4", postlar(cagri, "/image-to-3d").length === 1 && postlar(cagri, "/print/analyze").length === 1 &&
      r2.asama === "surdu" && r3.asama === "analiz" && r3.kredi === 15 && r3.glb_bayt === 2 &&
      kova.has("doku-deneme/kucuk.png") && kova.has("doku-deneme/alfa.png") && kova.has("doku-deneme/model.glb") &&
      r4.asama === "bitti" && r4.analiz && r4.analiz.status === "healthy" &&
      r5.asama === "bitti" && cagri.length === once && r6.status === 404);
  }
  // C5
  {
    const { env, kova } = sahteEnv(true, { "doku-deneme/istek.json": { is_no: "../x", model: MODEL } });
    const cagri = sahteFetch([]);
    const r = await u(env);
    v("C5", r.status === 404 && cagri.length === 0 && !kova.has("doku-deneme/istek.json"));
  }
  // C6
  {
    const { env, kova } = sahteEnv(true, { "doku-deneme/istek.json": { is_no: IS, model: "abcdef-6" } });
    const cagri = sahteFetch([]);
    const r = await u(env);
    v("C6", r.status === 404 && cagri.length === 0 && !kova.has("doku-deneme/istek.json"));
  }
  // C7
  {
    const { env, kova } = sahteEnv(true, { "doku-deneme/dokusuz/istek.json": { is_no: IS, model: MODEL } });
    const eski = JSON.stringify({ asama: "bitti", gorev: "eski-0001" });
    kova.set("doku-deneme/durum.json", eski);
    const cagri = sahteFetch([]);
    const r = await (await u(env, "dokusuz")).json();
    const post = postlar(cagri, "/image-to-3d");
    const g = post.length === 1 ? post[0].govde : {};
    v("C7", post.length === 1 && g.should_texture === false && !("texture_prompt" in g) && g.ai_model === MODEL &&
      r.asama === "surdu" && r.tur === "dokusuz" && kova.has("doku-deneme/dokusuz/durum.json") &&
      !kova.has("doku-deneme/dokusuz/istek.json") && kova.get("doku-deneme/durum.json") === eski);
  }
  return sonuc;
}

const kirmizilar = (s) => Object.keys(s).filter((k) => !s[k]).sort();
let hata = 0;
const asil = await vakalar(await import(pathToFileURL(KAYNAK).href));
console.log("ASIL " + JSON.stringify(asil));
if (kirmizilar(asil).length) { console.log("KIRMIZI asil: " + kirmizilar(asil)); hata = 1; }

const MUTANTLAR = [
  ["M1", "!onizlemeMi(env) || ", "", ["C1"]],
  ["M2", "  await env.OZEL_DOSYA.delete(dizin + \"istek.json\");\n", "", ["C3", "C4", "C5", "C6", "C7"]],
  ["M3", "const DOKU_DENEME_MODEL = /^[a-z]{3,12}-6-lite$/;", "const DOKU_DENEME_MODEL = /^[a-z]{3,12}-6(-lite)?$/;", ["C6"]],
  ["M4", "govde: { should_texture: false,", "govde: { should_texture: true,", ["C7"]],
];
const metin = readFileSync(KAYNAK, "utf8");
for (const [ad, eski, yeni, hedef] of MUTANTLAR) {
  const yol = join(BURA, "..", "src", ".mutant-doku-" + ad + ".mjs");
  try {
    if (!metin.includes(eski)) { console.log("KIRMIZI " + ad + ": mutant uygulanamadi"); hata = 1; continue; }
    writeFileSync(yol, metin.replace(eski, yeni));
    const s = await vakalar(await import(pathToFileURL(yol).href));
    const k = kirmizilar(s);
    const tamam = JSON.stringify(k) === JSON.stringify([...hedef].sort());
    console.log((tamam ? "OK " : "KIRMIZI ") + ad + " kirmizi=" + JSON.stringify(k) + " beklenen=" + JSON.stringify(hedef));
    if (!tamam) { hata = 1; }
  } finally {
    try { unlinkSync(yol); } catch (e) { /* yok */ }
  }
}
console.log(hata ? "SONUC KIRMIZI" : "SONUC YESIL");
process.exit(hata);
