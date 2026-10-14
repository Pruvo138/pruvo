#!/usr/bin/env node
/**
 * PRUVO shop — DOKU DENEMESI kabul kapisi (shop/src/foto.js dokuDenemeUcu, Okan 14 Eki 13:1x 15 kr).
 *
 *   node shop/test/doku-deneme.mjs
 *
 * OLCULEN (kredi harcayan tek seferlik uc; hatasi PARA kaybidir):
 *   C1 canli (ONIZLEME yok) + istek dosyasi VAR -> 404, saglayiciya istek 0, istek dosyasi YERINDE
 *   C2 onizleme + istek YOK -> 404, saglayiciya istek 0
 *   C3 onizleme + istek VAR -> TAM 1 POST /v1/image-to-3d, govde SABIT (istekteki <ad>-6-lite, should_texture,
 *      duz renk istemi, pbr kapali, image_url data:image/png), istek dosyasi SILINDI, durum 'surdu'
 *   C4 ayni durumla 2. ve 3. cagri -> yeni POST 0 (yalniz GET yoklama); SUCCEEDED -> gorseller R2'ye,
 *      durum 'bitti' + kredi; 4. cagri saglayiciya 0 istek
 *   C5 istek gecersiz is_no -> POST 0, istek yine silinir
 *   C6 istek modeli -6-lite DEGIL (<ad>-6 = dokulu 30 kr) -> POST 0, istek yine silinir
 * MUTANTLAR (gecici kopya shop/src/.mutant-doku-*.mjs, finally'de SILINIR; hedef vaka KIRMIZI olmali):
 *   M1 onizlemeMi denetimi silindi -> C1 · M2 istek silme satiri silindi -> C3/C4/C5/C6
 *   M3 model kalibi -6-lite'tan -6'ya gevsedi (30 kr) -> C6
 * CIKIS: 0 yesil · 1 kirmizi.
 */
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURA = dirname(fileURLToPath(import.meta.url));
const KAYNAK = join(BURA, "..", "src", "foto.js");
const IS = "3906f993a476d5a0cd33fa12da49ecbe";

function sahteEnv(onizleme, istek) {
  const kova = new Map();
  kova.set("foto-onizleme/" + IS + ".png", new Uint8Array([137, 80, 78, 71, 1, 2, 3]).buffer);
  if (istek !== undefined) { kova.set("doku-deneme/istek.json", JSON.stringify(istek)); }
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
  globalThis.fetch = async (adres, ops) => {
    const o = ops || {};
    cagri.push({ adres: String(adres), yontem: o.method || "GET", govde: o.body ? JSON.parse(o.body) : null });
    const yanit = (kod, v, ek) => ({ status: kod, json: async () => v, headers: { get: () => (ek || null) },
                                    arrayBuffer: async () => new Uint8Array([1, 2]).buffer });
    if (String(adres).startsWith("https://cdn.invalid/")) { return yanit(200, null, "image/png"); }
    if ((o.method || "GET") === "POST") { return yanit(202, { result: "gorev-0001" }); }
    const s = durumSirasi.shift() || "IN_PROGRESS";
    return yanit(200, { status: s, progress: 50, consumed_credits: s === "SUCCEEDED" ? 15 : 0,
                        thumbnail_url: "https://cdn.invalid/k.png", alpha_thumbnail_url: "https://cdn.invalid/a.png" });
  };
  return cagri;
}

async function vakalar(mod) {
  const sonuc = {};
  const v = (ad, kosul) => { sonuc[ad] = sonuc[ad] === false ? false : !!kosul; };
  // C1
  {
    const { env, kova } = sahteEnv(false, { is_no: IS, model: "abcdef-6-lite" });
    const cagri = sahteFetch([]);
    const r = await mod.dokuDenemeUcu(env);
    v("C1", r.status === 404 && cagri.length === 0 && kova.has("doku-deneme/istek.json"));
  }
  // C2
  {
    const { env } = sahteEnv(true);
    const cagri = sahteFetch([]);
    const r = await mod.dokuDenemeUcu(env);
    v("C2", r.status === 404 && cagri.length === 0);
  }
  // C3 + C4
  {
    const { env, kova } = sahteEnv(true, { is_no: IS, model: "abcdef-6-lite" });
    const cagri = sahteFetch(["IN_PROGRESS", "SUCCEEDED"]);
    const r1 = await (await mod.dokuDenemeUcu(env)).json();
    const post = cagri.filter((c) => c.yontem === "POST");
    const g = post.length === 1 ? post[0].govde : {};
    v("C3", post.length === 1 && post[0].adres.endsWith("/openapi/v1/image-to-3d") &&
      g.ai_model === "abcdef-6-lite" && g.should_texture === true && g.enable_pbr === false &&
      g.texture_prompt === "solid matte white, uniform single color, no pattern, no gradient" &&
      String(g.image_url).startsWith("data:image/png;base64,") &&
      !kova.has("doku-deneme/istek.json") && r1.asama === "surdu" && r1.gorev === "gorev-0001");
    // Istek dosyasi silinmemis olsa bile (M2) yeni POST olmamali: durum varken istek OKUNMAZ;
    // M2'yi yakalayan ayri kol: durum dosyasi kaybolursa istek tekrar harcatir.
    const r2 = await (await mod.dokuDenemeUcu(env)).json();
    const r3 = await (await mod.dokuDenemeUcu(env)).json();
    const once = cagri.length;
    const r4 = await (await mod.dokuDenemeUcu(env)).json();
    kova.delete("doku-deneme/durum.json");
    const r5 = await mod.dokuDenemeUcu(env);
    v("C4", cagri.filter((c) => c.yontem === "POST").length === 1 && r2.asama === "surdu" &&
      r3.asama === "bitti" && r3.kredi === 15 && kova.has("doku-deneme/kucuk.png") &&
      kova.has("doku-deneme/alfa.png") && r4.asama === "bitti" && cagri.length === once &&
      r5.status === 404);
  }
  // C5
  {
    const { env, kova } = sahteEnv(true, { is_no: "../x" });
    const cagri = sahteFetch([]);
    const r = await mod.dokuDenemeUcu(env);
    v("C5", r.status === 404 && cagri.filter((c) => c.yontem === "POST").length === 0 &&
      !kova.has("doku-deneme/istek.json"));
  }
  // C6
  {
    const { env, kova } = sahteEnv(true, { is_no: IS, model: "abcdef-6" });
    const cagri = sahteFetch([]);
    const r = await mod.dokuDenemeUcu(env);
    v("C6", r.status === 404 && cagri.length === 0 && !kova.has("doku-deneme/istek.json"));
  }
  return sonuc;
}

const kirmizilar = (s) => Object.keys(s).filter((k) => !s[k]).sort();
let hata = 0;
const asil = await vakalar(await import(pathToFileURL(KAYNAK).href));
console.log("ASIL " + JSON.stringify(asil));
if (kirmizilar(asil).length) { console.log("KIRMIZI asil: " + kirmizilar(asil)); hata = 1; }

const MUTANTLAR = [
  ["M1", "if (!onizlemeMi(env) || !env.OZEL_DOSYA", "if (!env.OZEL_DOSYA", ["C1"]],
  ["M2", "  await env.OZEL_DOSYA.delete(DOKU_DENEME_DIZIN + \"istek.json\");\n", "", ["C3", "C4", "C5", "C6"]],
  ["M3", "const DOKU_DENEME_MODEL = /^[a-z]{3,12}-6-lite$/;", "const DOKU_DENEME_MODEL = /^[a-z]{3,12}-6(-lite)?$/;", ["C6"]],
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
