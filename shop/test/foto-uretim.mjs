#!/usr/bin/env node
/**
 * PRUVO shop — FOTOGRAFTAN OZEL URETIM KABUL KAPISI (Okan karari 5 Eki 2026; kod
 * shop/src/foto.js + index.js /baslat kalemi + yonet.js panel uclari).
 *
 *   node shop/test/foto-uretim.mjs
 *
 * OLCTUGU HUKUMLER (BaBa kutu 5 Eki 18:1x, 8 madde):
 *   A KAPALI-VARSAYILAN : bugunku veri dosyasiyla (onay metni onaysiz, gercek ornek 0) bolum
 *                         KAPALI; onizleme 503, /baslat foto kalemi 400, cron D1'e dokunmaz
 *   B FIYAT KABI        : fiyat tablosu bos -> tur sunulmaz; panelden satir yazilinca sunulur
 *   C ONIZLEME          : saglayiciya yalniz ONIZLEME gider (odemeden once tek kredi adimi);
 *                         gorsel bizim ucumuzdan sunulur; kredi defterine BIR kez yazilir
 *   D SINIR             : ziyaretci basi 24 saatte N onizleme; N+1. istek 429 ve saglayiciya
 *                         GITMEZ; baska ziyaretci etkilenmez            (Kapatan: "sinir+1 RED")
 *   E BOT KAPISI        : jeton yok/red/ag hatasi -> 403 (fail-CLOSED), saglayiciya gitmez
 *   F ONAY + GORSEL     : iki onay kutusu + guncel onay surumu sart; sahte gorsel reddedilir
 *   G HAVUZ             : bakiye esigin altinda -> bolum kapanir + Telegram TEK bildirim
 *   H /baslat           : fiyat SUNUCUDA tablodan (+kargo kurali), havale RED, suresi dolmus
 *                         onizleme RED
 *   I URETIM ZINCIRI    : 'bekliyor' siparis uretime GIRMEZ; 'odendi' -> model -> analiz ->
 *                         4 renk -> 3MF+GLB ozel kovada -> panelde indirilebilir; kredi 46
 *   J ANALIZ KIRMIZI    : renk adimi KOSMAZ, satir 'elle' + Telegram bir kez
 *   K MARKASIZ          : saglayici adi / anahtar oneki calisma agacinda 0 (git grep)
 *   L DRIFT             : wrangler.toml cron + hiz siniri beyani index.js ile ayni
 *   M PANEL OZETI       : tur basina kalem ↔ elle sayisi + aylik kredi
 * PLAKET KARARI (BaBa 5 Eki 21:4x(b) — Okan: "plaket yapalim"; yalniz plastik uretiyoruz):
 *   P TUR LISTESI       : sunulan tur 1 (plaket); anahtarlik/magnet/figur panel fiyatinda ve
 *                         onizlemede RED; saglayici tur yolu kodda degil ORTAM DEGISKENINDE
 *   Q SUNULMAYAN TUR    : eski kayittan /baslat RED · odenmis magnet kalemi kuyruga girmez ·
 *                         kuyruktaki anahtarlik satiri saglayiciya gitmeden 'elle'
 *   I3b/I8b/J4 AYAK     : Build'e sabit kabartma/taban + kapali sirt; kalemde foto_ayak 1,
 *                         panel baski notunda "AYAK: <adet> adet"
 *   S EKRAN             : foto-uretim.js SAHTE DOM'da kosar: tek turde tur radyosu 0 + adim
 *                         "Olcu"; olcu radyolari (S1 + S3) gercekten cizilir (5 Eki olculen hata)
 *
 * NASIL: GERCEK worker (shop/src/index.js) import edilir. D1 = GERCEK SQLite: sema
 * tools/d1-sema.sql'den kurulur (shop/test/ortak/sqlite-koprusu.py) — elle yazilmis
 * ikinci sema YOK. Saglayici, bot dogrulayici, iyzico ve Telegram `globalThis.fetch`
 * stub'idir: GERCEK AG ISTEGI YOK. R2 bellekte sahtedir.
 *
 * ONCE-KIRMIZI KANITI (mutantlar bu dosyanin sonunda; foto.js'in GECICI kopyasina
 * uygulanir, calisma agacina YAZMAZ):
 *   M1 SINIR  : ziyaretci siniri kontrolu devre disi   -> D OLUR
 *   M2 BOT    : bot dogrulamasi devre disi             -> E OLUR
 *   M3 ANALIZ : kirmizi analiz kapisi devre disi       -> J OLUR
 *   M4 TUR    : anahtarlik tur tablosuna geri acilir   -> T OLUR
 *   M5 AYAK   : odeme kaleminden foto_ayak duser       -> A OLUR
 *   K0 KONTROL: yalniz log metni degisir               -> HICBIRI OLMEZ
 *   (ekran mutantlari S-M1..S-M4 bellekteki kaynak metnine uygulanir)
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (modul/kopru kurulamadi).
 */

// ---- JSON IMPORT KOPRUSU (terk-supurme.mjs ile ayni gerekce; uretim kodunu ETKILEMEZ) ----
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) {" +
  "    return { ...r, format: 'json', importAttributes: { type: 'json' } }; }" +
  "  return r; }"));

import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import readline from "node:readline";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const SHOP = path.join(KOK, "shop");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

// ---------------------------------------------------------------- gercek SQLite koprusu

function koprukur() {
  const p = spawn("python3", [path.join(BURASI, "ortak", "sqlite-koprusu.py")],
                  { stdio: ["pipe", "pipe", "inherit"] });
  const rl = readline.createInterface({ input: p.stdout });
  const bekleyen = [];
  rl.on("line", (s) => { const c = bekleyen.shift(); if (c) { c(JSON.parse(s)); } });
  const istek = (o) => new Promise((coz) => { bekleyen.push(coz); p.stdin.write(JSON.stringify(o) + "\n"); });
  const hazir = new Promise((coz) => bekleyen.push(coz));
  const d1 = {
    prepare(sql) {
      let binds = [];
      const st = {
        bind(...b) { binds = b; return st; },
        async all() { const c = await istek({ sql, binds, mod: "all" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return { results: c.results, meta: c.meta, success: true }; },
        async first() { const c = await istek({ sql, binds, mod: "all" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return c.results[0] || null; },
        async run() { const c = await istek({ sql, binds, mod: "run" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return { meta: c.meta, success: true }; },
      };
      return st;
    },
  };
  return { d1, hazir, kapat: () => p.stdin.end() };
}

function r2Kur() {
  const m = new Map();
  return {
    m,
    async put(k, v, o) { m.set(k, { bayt: new Uint8Array(v), httpMetadata: (o && o.httpMetadata) || {} }); },
    async get(k) { const x = m.get(k); return x ? { body: x.bayt, httpMetadata: x.httpMetadata } : null; },
    async delete(k) { m.delete(k); },
    async list() { return { objects: [] }; },
  };
}

// ---------------------------------------------------------------- sahte ag (saglayici + digerleri)

const TABAN = "https://saglayici.test/openapi";
const PNG = Uint8Array.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ...new Array(64).fill(7)]);
const UCMF = new TextEncoder().encode("PK-sahte-3mf-govdesi-4-renk");
const GLB = new TextEncoder().encode("glTF-sahte-govde");
const P = {
  cagri: [], bakiye: 1000, analiz: "healthy", turnstile: "ok", telegram: [], iyzico: [],
  protoDurum: new Map(),
};
let sayac = 0;
const yeniId = () => "gorev-" + String(++sayac).padStart(4, "0") + "-aaaa";
const yanit = (v, kod) => new Response(JSON.stringify(v), { status: kod || 200, headers: { "Content-Type": "application/json" } });

globalThis.fetch = async function sahteFetch(hedef, init) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  const yontem = (init && init.method) || "GET";
  if (u.startsWith(TABAN)) {
    const yol = u.slice(TABAN.length);
    P.cagri.push(yontem + " " + yol);
    if (yol === "/v1/balance") { return yanit({ balance: P.bakiye }); }
    let m;
    if (yontem === "POST" && /^\/tur-onek\/tur-plaket\/v1\/prototype$/.test(yol)) {
      const g = JSON.parse(init.body);
      if (!/^data:image\/png;base64,/.test(g.image_url)) { return yanit({ message: "bad" }, 400); }
      const id = yeniId(); P.protoDurum.set(id, 0); return yanit({ result: id });
    }
    if ((m = /^\/tur-onek\/tur-plaket\/v1\/prototype\/(.+)$/.exec(yol))) {
      const n = (P.protoDurum.get(m[1]) || 0) + 1; P.protoDurum.set(m[1], n);
      return n < 2 ? yanit({ id: m[1], status: "IN_PROGRESS", progress: 40 })
        : yanit({ id: m[1], status: "SUCCEEDED", consumed_credits: 6, image_urls: ["https://dosya.test/onizleme.png?Expires=1"] });
    }
    if (yontem === "POST" && /^\/tur-onek\/tur-plaket\/v1\/build$/.test(yol)) {
      const g = JSON.parse(init.body);
      P.sonBuild = g; return yanit({ result: yeniId() });
    }
    if (/\/v1\/build\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 30, model_urls: { glb: "https://dosya.test/model.glb?Expires=1" } });
    }
    if (yontem === "POST" && yol === "/v1/print/analyze") { return yanit({ result: yeniId() }); }
    if (/^\/v1\/print\/analyze\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 0,
        printability: { status: P.analiz, error_count: P.analiz === "error" ? 1 : 0, warning_count: 0,
                        metrics: { is_watertight: P.analiz !== "error", non_manifold_edges: P.analiz === "error" ? 12 : 0 } } });
    }
    if (yontem === "POST" && yol === "/v1/print/multi-color") { P.sonRenk = JSON.parse(init.body); return yanit({ result: yeniId() }); }
    if (/^\/v1\/print\/multi-color\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 10, model_urls: { "3mf": "https://dosya.test/model.3mf?Expires=1" } });
    }
    return yanit({ message: "bilinmeyen" }, 404);
  }
  if (u.startsWith("https://dosya.test/onizleme.png")) { return new Response(PNG, { headers: { "Content-Type": "image/png", "Content-Length": String(PNG.length) } }); }
  if (u.startsWith("https://dosya.test/model.3mf")) { return new Response(UCMF, { headers: { "Content-Type": "application/octet-stream" } }); }
  if (u.startsWith("https://dosya.test/model.glb")) { return new Response(GLB, { headers: { "Content-Type": "model/gltf-binary" } }); }
  if (u.includes("challenges.cloudflare.com/turnstile")) {
    P.cagri.push("TURNSTILE");
    if (P.turnstile === "ag") { throw new Error("ag yok"); }
    return yanit(P.turnstile === "ok" ? { success: true, hostname: "pruvo3d.com" } : { success: false, "error-codes": ["x"] });
  }
  if (u.startsWith("https://telegram.test")) { P.telegram.push(JSON.parse(init.body).text); return yanit({ ok: true }); }
  if (u.startsWith("https://iyzico.test")) {
    P.iyzico.push(JSON.parse(init.body));
    return yanit({ status: "success", token: "iyz-" + P.iyzico.length, paymentPageUrl: "https://odeme.test/sayfa" });
  }
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

// ---------------------------------------------------------------- ortam

const limiter = () => ({ limit: async () => ({ success: true }) });
function envKur(d1, r2, ek) {
  return {
    KATALOG: d1, OZEL_DOSYA: r2, SITE_URL: "https://pruvo3d.com",
    IYZICO_BASE_URL: "https://iyzico.test", IYZICO_API_KEY: "k", IYZICO_SECRET_KEY: "s",
    TELEGRAM_TOKEN: "t", TELEGRAM_API: "https://telegram.test", TELEGRAM_CHAT: "1",
    TURNSTILE_SECRET: "ts", YONET_ANAHTAR: "yonet-test-anahtari",
    BASLAT_RATE_LIMIT: limiter(), FIYAT_RATE_LIMIT: limiter(), FOTO_RATE_LIMIT: limiter(),
    URETIM_API_TABAN: TABAN, URETIM_TUR_ONEK: "tur-onek", URETIM_TUR_PLAKET: "tur-plaket", URETIM_API_ANAHTAR: "sahte-anahtar",
    ...(ek || {}),
  };
}
const ctx = { bekleyen: [], waitUntil(p) { this.bekleyen.push(p); } };

const B64 = Buffer.from(Uint8Array.from([...PNG, ...new Array(4096).fill(3)])).toString("base64");
const GORSEL = "data:image/png;base64," + B64;
const SAHTE_GORSEL = "data:image/png;base64," + Buffer.from(new Uint8Array(4200).fill(65)).toString("base64");

let modul, foto;
try {
  modul = (await import(url.pathToFileURL(path.join(SHOP, "src", "index.js")).href)).default;
  foto = await import(url.pathToFileURL(path.join(SHOP, "src", "foto.js")).href);
} catch (e) {
  console.log("OLCULEMEDI: worker modulu yuklenemedi — " + ((e && e.stack) || e));
  process.exit(3);
}
const VERI = globalThis.PRUVO_FOTO;

async function istek(env, yol, o) {
  o = o || {};
  const basliklar = { "CF-Connecting-IP": o.ip || "198.51.100.7", ...(o.basliklar || {}) };
  if (o.govde) { basliklar["Content-Type"] = "application/json"; }
  const r = await modul.fetch(new Request("https://pruvo3d.com/api/shop" + yol, {
    method: o.yontem || (o.govde ? "POST" : "GET"), headers: basliklar,
    body: o.govde ? JSON.stringify(o.govde) : undefined }), env, ctx);
  let v = null; const tip = r.headers.get("Content-Type") || "";
  if (tip.includes("json")) { try { v = await r.json(); } catch (e) { v = null; } }
  return { kod: r.status, v, r };
}
const YONET = { "X-Yonet-Anahtar": "yonet-test-anahtari" };
const onizlemeGovde = (ek) => ({ tur: "plaket", olcu_mm: 100, gorsel: GORSEL, hak_onay: true,
  aktarim_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton", ...(ek || {}) });
const protoSayisi = () => P.cagri.filter((c) => /^POST .*\/v1\/prototype$/.test(c)).length;

// ================================================================ ANA KOSUM

const kopru = koprukur();
const ilk = await kopru.hazir;
if (!ilk || !ilk.hazir) { console.log("OLCULEMEDI: SQLite koprusu kurulamadi — " + JSON.stringify(ilk)); process.exit(3); }
const d1 = kopru.d1;
const r2 = r2Kur();
const env = envKur(d1, r2);

console.log("A) KAPALI-VARSAYILAN (bugunku veri dosyasi)");
{
  const y = foto.yapilandirma(env);
  // Onay metni Okan'ca onaylandi (6 Eki); eksik listesi onay kolunu veri dosyasina gore yazar.
  ol("A1 gercek ornek 0 -> yapilandirma HAZIR DEGIL (onay eksigi yalniz onaysizken listelenir)",
     !y.hazir && y.eksik.includes("gercek-ornek") &&
       y.eksik.includes("onay-metni-onayi") === (VERI.onay_onayli !== true), JSON.stringify(y));
  // A1b: onay kapisi veri dosyasinin bugunku halinden BAGIMSIZ olculur (onaysiz -> eksik).
  const onayOnce = VERI.onay_onayli;
  VERI.onay_onayli = false;
  const yb = foto.yapilandirma(env);
  VERI.onay_onayli = onayOnce;
  ol("A1b onay bayragi kapali -> eksik listesinde onay-metni-onayi VAR, hazir DEGIL",
     !yb.hazir && yb.eksik.includes("onay-metni-onayi"), JSON.stringify(yb));
  const a = await istek(env, "/foto/acik");
  ol("A2 /foto/acik -> acik:false", a.kod === 200 && a.v && a.v.acik === false, JSON.stringify(a.v));
  const o = await istek(env, "/foto/onizleme", { govde: onizlemeGovde() });
  ol("A3 /foto/onizleme -> 503 kapali, saglayiciya istek YOK", o.kod === 503 && protoSayisi() === 0, o.kod);
  const c = await foto.fotoUretimTuru(envKur(d1, r2, { URETIM_API_ANAHTAR: "" }), Date.now(), null);
  ol("A4 anahtarsiz cron D1'e dokunmadan ATLAR", c.atlandi === "yapilandirma", JSON.stringify(c));
  const yolsuz = envKur(d1, r2, { URETIM_TUR_PLAKET: "" });
  ol("A5 plaket tur yolu ortam degiskeni yoksa yapilandirma eksik 'tur-yolu-plaket' + cron ATLAR",
     foto.yapilandirma(yolsuz).eksik.includes("tur-yolu-plaket") &&
     (await foto.fotoUretimTuru(yolsuz, Date.now(), null)).atlandi === "yapilandirma",
     JSON.stringify(foto.yapilandirma(yolsuz).eksik));
}

console.log("P) TUR LISTESI — tek tur PLAKET (Okan 5 Eki 21:4x; anahtarlik/magnet SUNULMAZ)");
{
  ol("P1 veri dosyasinda sunulan tur sayisi 1 ve kodu 'plaket'",
     VERI.turler.length === 1 && VERI.turler[0].kod === "plaket", JSON.stringify(VERI.turler.map((t) => t.kod)));
  ol("P2 sunucu tur tablosu yalniz plaket (anahtarlik/magnet/figur 0)",
     JSON.stringify(Object.keys(foto.TUR_ORTAM)) === '["plaket"]', JSON.stringify(Object.keys(foto.TUR_ORTAM)));
  ol("P3 saglayici tur yolu kodda DEGIL, ortam degiskeninden (deger dizesi 'URETIM_' ile baslar)",
     Object.values(foto.TUR_ORTAM).every((v) => /^URETIM_TUR_[A-Z]+$/.test(v)), JSON.stringify(foto.TUR_ORTAM));
}

// Bolumu ac: onay onayli + ONCE baski fotografi EKSIK bir ornek (gercek ornek SAYILMAZ).
VERI.onay_onayli = true;
VERI.ornekler.push({ tur: "plaket", olcu_mm: 120, foto: "https://media.pruvo3d.com/y-foto.webp",
  onizleme: "https://media.pruvo3d.com/y-oniz.webp", baski: "", not: "baski fotografi YOK" });

console.log("B) FIYAT KABI");
{
  const a = await istek(env, "/foto/acik");
  ol("B1 fiyat tablosu bos -> acik:false (tur sunulmaz)", a.v && a.v.acik === false, JSON.stringify(a.v));
  const y1 = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 100, fiyat_kurus: 34900 }, basliklar: YONET });
  const y2 = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 150, fiyat_kurus: 49900 }, basliklar: YONET });
  const yetkisiz = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 120, fiyat_kurus: 1 } });
  ol("B2 panel fiyat yazar (anahtarli 200, anahtarsiz 404)", y1.kod === 200 && y2.kod === 200 && yetkisiz.kod === 404,
     y1.kod + "/" + y2.kod + "/" + yetkisiz.kod);
  const a1 = await istek(env, "/foto/acik");
  ol("B4 baski fotografi eksik ornek SAYILMAZ -> fiyat olsa da acik:false (gercek ornek 0)",
     a1.v && a1.v.acik === false, JSON.stringify(a1.v));
  VERI.ornekler.push({ tur: "plaket", olcu_mm: 100, foto: "https://media.pruvo3d.com/x-foto.webp",
    onizleme: "https://media.pruvo3d.com/x-oniz.webp", baski: "https://media.pruvo3d.com/x-baski.webp", not: "t" });
  const a2 = await istek(env, "/foto/acik");
  const turler = (a2.v && a2.v.turler) || [];
  ol("B3 acik:true; plaket 100 mm 34900 sunulur", a2.v && a2.v.acik === true &&
     turler.some((t) => t.kod === "plaket" && t.olculer.some((o) => o.mm === 100 && o.fiyat_kurus === 34900)), JSON.stringify(a2.v));
  ol("P4 /foto/acik sunulan tur sayisi 1 (plaket)", turler.length === 1 && turler[0].kod === "plaket",
     JSON.stringify(turler.map((t) => t.kod)));
  const kotu = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 5, fiyat_kurus: 100 }, basliklar: YONET });
  const kotu2 = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 40, fiyat_kurus: 100 }, basliklar: YONET });
  ol("B5 aralik disi olcu (5, 40 mm) fiyat tablosuna YAZILAMAZ", kotu.kod === 400 && kotu2.kod === 400, kotu.kod + "/" + kotu2.kod);
  const red = [];
  for (const t of ["anahtarlik", "magnet", "figur"]) {
    const r = await istek(env, "/yonet/foto-fiyat", { govde: { tur: t, olcu_mm: 100, fiyat_kurus: 100 }, basliklar: YONET });
    if (r.kod === 400 && r.v && r.v.hata === "gecersiz-tur") { red.push(t); }
  }
  ol("P5 panel fiyat: anahtarlik/magnet/figur satiri YAZILAMAZ (3/3 gecersiz-tur)", red.length === 3, red.join(","));
  const tablo = await d1.prepare("SELECT COUNT(*) AS n FROM foto_fiyat WHERE tur <> 'plaket'").first();
  ol("P5b fiyat tablosunda plaket disi satir 0", tablo.n === 0, tablo.n);
  const oz = await istek(env, "/yonet/foto-ozet", { basliklar: YONET });
  ol("P6 panel ozeti sunulan turleri sunucudan verir: yalniz plaket (panel tur listesi elle yazilmaz)",
     oz.v && JSON.stringify(oz.v.sunulan_turler.map((t) => t.kod)) === '["plaket"]' &&
     oz.v.olcu_en_az === foto.OLCU_MM_EN_AZ && oz.v.ayak_plaket_basi === 1, JSON.stringify(oz.v && oz.v.sunulan_turler));
}

console.log("C/F) ONIZLEME + ONAY + GORSEL");
let isNo;
{
  const once = protoSayisi();
  const r1 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ aktarim_onay: false }) });
  const r2_ = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ onay_surum: "eski" }) });
  const r3 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ gorsel: SAHTE_GORSEL }) });
  const r4 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ olcu_mm: 55 }) });
  const r5 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "magnet", olcu_mm: 100 }) });
  const r6 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "anahtarlik", olcu_mm: 100 }) });
  ol("F1 aktarim onayi yok -> 400 onay-yok", r1.kod === 400 && r1.v.hata === "onay-yok", JSON.stringify(r1.v));
  ol("F2 eski onay surumu -> 409", r2_.kod === 409, r2_.kod);
  ol("F3 sihirli bayti tutmayan gorsel -> 400 gorsel-gecersiz", r3.kod === 400 && r3.v.hata === "gorsel-gecersiz", JSON.stringify(r3.v));
  ol("F4 tabloda olmayan olcu -> 400", r4.kod === 400 && r4.v.hata === "gecersiz-olcu", JSON.stringify(r4.v));
  ol("F5 sunulmayan tur magnet -> 400 tur-kapali", r5.kod === 400 && r5.v.hata === "tur-kapali", JSON.stringify(r5.v));
  ol("P7 sunulmayan tur anahtarlik -> 400 tur-kapali", r6.kod === 400 && r6.v.hata === "tur-kapali", JSON.stringify(r6.v));
  ol("F6 reddedilen isteklerin hicbiri saglayiciya GITMEDI", protoSayisi() === once, protoSayisi() - once);

  const ok = await istek(env, "/foto/onizleme", { govde: onizlemeGovde() });
  isNo = ok.v && ok.v.is;
  ol("C1 gecerli istek -> 200 + 32 hex is anahtari", ok.kod === 200 && /^[a-f0-9]{32}$/.test(isNo || ""), JSON.stringify(ok.v));
  ol("C2 saglayiciya tur oneki + urun yoluyla TEK onizleme istegi", protoSayisi() === once + 1 &&
     P.cagri.includes("POST /tur-onek/tur-plaket/v1/prototype"), P.cagri.slice(-3).join(" | "));
  const d0 = await istek(env, "/foto/durum?is=" + isNo);
  ol("C3 ilk yoklama: suruyor", d0.v && d0.v.asama === "onizleme", JSON.stringify(d0.v));
  const yoklamaOnce = P.cagri.length;
  await istek(env, "/foto/durum?is=" + isNo);
  ol("C4 2,5 sn icindeki ikinci yoklama saglayiciya GITMEZ", P.cagri.length === yoklamaOnce, P.cagri.length - yoklamaOnce);
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(isNo).run();
  const d1r = await istek(env, "/foto/durum?is=" + isNo);
  ol("C5 hazir: gorsel BIZIM ucumuzdan (saglayici adresi tarayiciya verilmez)",
     d1r.v && d1r.v.asama === "hazir" && d1r.v.gorsel === "/api/shop/foto/gorsel?is=" + isNo, JSON.stringify(d1r.v));
  const g = await istek(env, "/foto/gorsel?is=" + isNo);
  const bayt = new Uint8Array(await g.r.arrayBuffer());
  ol("C6 /foto/gorsel onizlemeyi ozel kovadan sunar", g.kod === 200 && bayt.length === PNG.length, g.kod + "/" + bayt.length);
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(isNo).run();
  await istek(env, "/foto/durum?is=" + isNo);
  const k = await d1.prepare("SELECT COUNT(*) AS n, SUM(kredi) AS t FROM foto_kredi WHERE is_no = ?").bind(isNo).first();
  ol("C7 onizleme kredisi defterde TEK satir (6)", k.n === 1 && k.t === 6, JSON.stringify(k));
  const yok = await istek(env, "/foto/gorsel?is=" + "0".repeat(32));
  ol("C8 bilinmeyen is anahtari -> 404", yok.kod === 404, yok.kod);
}

console.log("D) ZIYARETCI SINIRI (sinir+1 RED)");
{
  const ip = "203.0.113.9";
  const sinir = VERI.sinir_ziyaretci_24s;
  const kodlar = [];
  for (let i = 0; i < sinir; i++) { kodlar.push((await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() })).kod); }
  const once = protoSayisi();
  const fazla = await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() });
  ol("D1 ilk " + sinir + " istek 200", kodlar.every((k) => k === 200), kodlar.join(","));
  ol("D2 " + (sinir + 1) + ". istek 429 onizleme-siniri ve saglayiciya GITMEZ",
     fazla.kod === 429 && fazla.v.hata === "onizleme-siniri" && protoSayisi() === once, fazla.kod + "/" + JSON.stringify(fazla.v));
  const baska = await istek(env, "/foto/onizleme", { ip: "203.0.113.10", govde: onizlemeGovde() });
  ol("D3 baska ziyaretci etkilenmez", baska.kod === 200, baska.kod);
  const ham = await d1.prepare("SELECT COUNT(*) AS n FROM foto_isler WHERE ziyaretci LIKE '%203.0.113%'").first();
  ol("D4 ham IP veritabanina YAZILMAZ", ham.n === 0, ham.n);
}

console.log("E) BOT KAPISI (fail-closed)");
for (const [mod, ad] of [["red", "red"], ["ag", "ag hatasi"]]) {
  P.turnstile = mod;
  const once = protoSayisi();
  const r = await istek(env, "/foto/onizleme", { ip: "192.0.2." + (mod === "red" ? 1 : 2), govde: onizlemeGovde() });
  ol("E dogrulayici " + ad + " -> 403, saglayiciya gitmez", r.kod === 403 && protoSayisi() === once, r.kod);
}
P.turnstile = "ok";
{
  const r = await istek(env, "/foto/onizleme", { ip: "192.0.2.3", govde: onizlemeGovde({ turnstile_token: "" }) });
  ol("E jeton bos -> 403", r.kod === 403, r.kod);
}

console.log("H) /baslat FOTO KALEMI");
const musteri = { ad: "Deneme Musteri", tel: "05000000000", eposta: "deneme@ornek.test", adres: "Deneme mahallesi 1", sehir: "Ankara" };
let siparisNo;
{
  const once = P.iyzico.length;
  const h = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "havale", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1 }] } });
  ol("H1 havale -> 400 foto-havale-yok", h.kod === 400 && h.v.hata === "foto-havale-yok", JSON.stringify(h.v));
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1, fiyat_kurus: 1 }] } });
  siparisNo = b.v && b.v.no;
  const iy = P.iyzico[P.iyzico.length - 1] || {};
  ol("H2 kart -> 200, iyzico tutari SUNUCU tablosundan (349,00 + 250,00 kargo)",
     b.kod === 200 && P.iyzico.length === once + 1 && iy.price === "599.00", JSON.stringify(b.v) + " price=" + iy.price);
  const s = await d1.prepare("SELECT durum, urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(siparisNo).first();
  const kalem = s && JSON.parse(s.urunler)[0];
  ol("H3 siparis 'bekliyor', kalem foto_is/tur(plaket)/olcu + foto_ayak 1 tasir", s && s.durum === "bekliyor" && s.tutar_kurus === 34900 &&
     kalem.foto_is === isNo && kalem.foto_tur === "plaket" && kalem.olcu_mm === 100 && kalem.foto_ayak === 1, JSON.stringify(s));
  const eski = await istek(env, "/foto/onizleme", { ip: "198.51.100.77", govde: onizlemeGovde() });
  await d1.prepare("UPDATE foto_isler SET asama = 'hazir', hazir_tarih = '2020-01-01T00:00:00.000Z' WHERE is_no = ?").bind(eski.v.is).run();
  const e = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: eski.v.is, olcu_mm: 100, adet: 1 }] } });
  ol("H4 suresi dolmus onizleme -> 400", e.kod === 400 && e.v.hata === "foto-onizleme-suresi-doldu", JSON.stringify(e.v));
  const yok = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: "f".repeat(32), olcu_mm: 100, adet: 1 }] } });
  ol("H5 olmayan onizleme -> 400", yok.kod === 400 && yok.v.hata === "foto-onizleme-yok", JSON.stringify(yok.v));
}

console.log("I) URETIM ZINCIRI");
const cron = async () => modul.scheduled({ cron: "*/5 * * * *", scheduledTime: Date.now() }, env, ctx);
{
  await cron();
  const bos = await d1.prepare("SELECT COUNT(*) AS n FROM foto_uretim").first();
  ol("I1 'bekliyor' siparis uretime GIRMEZ (odeme dogrulanmadan kredi harcanmaz)", bos.n === 0, bos.n);
  await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(siparisNo).run();
  for (let i = 0; i < 4; i++) { await cron(); }
  const u = await d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(siparisNo).first();
  ol("I2 dort turda zincir 'hazir'", u && u.asama === "hazir", JSON.stringify(u));
  const op = (P.sonBuild && P.sonBuild.options) || {};
  ol("I3 model adimina olcu mm ile gidildi", op.size_mm === 100, JSON.stringify(P.sonBuild));
  ol("I3b plaket geometrisi: kabartma + taban kalinligi sabit, kapali duz sirt (delme yok)",
     op.relief_height_mm === foto.PLAKET_KABARTMA_MM && op.base_thickness_mm === foto.PLAKET_TABAN_MM &&
     op.has_closed_back === true && op.badge_shape === foto.PLAKET_SEKIL, JSON.stringify(op));
  ol("I4 renk adimi 4 renk + bambu", P.sonRenk && P.sonRenk.max_colors === 4 && P.sonRenk.printer_brand === "bambu", JSON.stringify(P.sonRenk));
  const k3 = r2.m.get("foto/" + siparisNo + "/0/model.3mf");
  ol("I5 3MF + GLB BIZIM ozel kovada", k3 && k3.bayt.length === UCMF.length && r2.m.has("foto/" + siparisNo + "/0/model.glb"), [...r2.m.keys()].join(","));
  const kr = await d1.prepare("SELECT COALESCE(SUM(kredi),0) AS t FROM foto_kredi WHERE siparis_no = ? OR (adim = 'onizleme' AND is_no = ?)").bind(siparisNo, isNo).first();
  ol("I6 siparisin kredi kaydi 46 (6 onizleme + 30 model + 0 analiz + 10 renk)", kr.t === 46, kr.t);
  ol("I7 HAZIR bildirimi Telegram'a bir kez", P.telegram.filter((t) => t.includes("HAZIR") && t.includes(siparisNo)).length === 1, P.telegram.length);
  const l = await istek(env, "/yonet/liste", { basliklar: YONET });
  const sip = l.v && l.v.siparisler.find((x) => x.siparis_no === siparisNo);
  const f = sip && sip.kalemler[0].foto;
  ol("I8 panel listesi kalemin yaninda 3MF/GLB baglantisi", f && f.asama === "hazir" && f.dosyalar && /bicim=3mf/.test(f.dosyalar["3mf"]), JSON.stringify(f));
  ol("I8b panelde AYAK: kalem ayak 1 + baski notunda 'AYAK: 1 adet' (uretimde unutulmasin)",
     f && f.ayak === 1 && /AYAK: 1 adet/.test(sip.kalemler[0].baski_oneri || ""), sip && sip.kalemler[0].baski_oneri);
  const ind = await istek(env, f.dosyalar["3mf"].replace("/api/shop", ""), { basliklar: YONET });
  const indBayt = new Uint8Array(await ind.r.arrayBuffer());
  ol("I9 panelden 3MF indirilir (anahtarli), anahtarsiz 404", ind.kod === 200 && indBayt.length === UCMF.length &&
     /attachment/.test(ind.r.headers.get("Content-Disposition") || "") &&
     (await istek(env, f.dosyalar["3mf"].replace("/api/shop", ""))).kod === 404, ind.kod);
  const once = P.cagri.length;
  await cron();
  ol("I10 hazir satir tekrar islenmez (saglayiciya yeni istek yok)", P.cagri.length === once, P.cagri.slice(once).join(","));
}

console.log("J) ANALIZ KIRMIZI");
let siparis2;
{
  const ok = await istek(env, "/foto/onizleme", { ip: "198.51.100.88", govde: onizlemeGovde() });
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
  await istek(env, "/foto/durum?is=" + ok.v.is);
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
  await istek(env, "/foto/durum?is=" + ok.v.is);
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: ok.v.is, olcu_mm: 100, adet: 2 }] } });
  siparis2 = b.v && b.v.no;
  await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(siparis2).run();
  P.analiz = "error";
  const renkOnce = P.cagri.filter((c) => c === "POST /v1/print/multi-color").length;
  for (let i = 0; i < 4; i++) { await cron(); }
  const u = await d1.prepare("SELECT asama, sebep, analiz FROM foto_uretim WHERE siparis_no = ?").bind(siparis2).first();
  ol("J1 analiz kirmizi -> 'elle' + sebep", u && u.asama === "elle" && u.sebep === "analiz-kirmizi", JSON.stringify(u));
  ol("J2 renk adimi KOSMADI", P.cagri.filter((c) => c === "POST /v1/print/multi-color").length === renkOnce, "");
  ol("J3 ELLE bildirimi Telegram'a bir kez", P.telegram.filter((t) => t.includes("ELLE") && t.includes(siparis2)).length === 1, "");
  P.analiz = "healthy";
  const l = await istek(env, "/yonet/liste", { basliklar: YONET });
  const sip = l.v && l.v.siparisler.find((x) => x.siparis_no === siparis2);
  ol("J4 adet 2 -> panel notu 'AYAK: 2 adet' (plaket basina 1)",
     sip && /AYAK: 2 adet/.test(sip.kalemler[0].baski_oneri || ""), sip && sip.kalemler[0].baski_oneri);
}

console.log("G) HAVUZ ESIGI");
{
  P.bakiye = 100;
  await d1.prepare("UPDATE foto_ayar SET guncel = 0 WHERE anahtar = 'bakiye'").run();
  const once = P.telegram.length;
  const a = await istek(env, "/foto/acik");
  const o = await istek(env, "/foto/onizleme", { ip: "198.51.100.99", govde: onizlemeGovde() });
  ol("G1 bakiye esik altinda -> /acik false + onizleme 503", a.v.acik === false && o.kod === 503, a.v.acik + "/" + o.kod);
  ol("G2 Okan'a TEK bildirim (iki istek, bir mesaj)", P.telegram.length === once + 1 && /KAPANDI/.test(P.telegram[once]), P.telegram.length - once);
  P.bakiye = 1000;
  await d1.prepare("UPDATE foto_ayar SET guncel = 0 WHERE anahtar = 'bakiye'").run();
  const a2 = await istek(env, "/foto/acik");
  ol("G3 kredi gelince bolum kendiliginden acilir", a2.v.acik === true, JSON.stringify(a2.v.acik));
}

console.log("M) PANEL OZETI");
{
  const o = await istek(env, "/yonet/foto-ozet", { basliklar: YONET });
  const t = o.v && o.v.turler.find((x) => x.tur === "plaket");
  ol("M1 tur basina kalem 2 / hazir 1 / elle 1", t && t.kalem === 2 && t.hazir === 1 && t.elle === 1, JSON.stringify(t));
  ol("M2 aylik kredi sayilir (>= 46)", o.v.kredi.bu_ay >= 46, JSON.stringify(o.v.kredi));
  ol("M3 ozet anahtarsiz 404", (await istek(env, "/yonet/foto-ozet")).kod === 404, "");
}

console.log("Q) SUNULMAYAN TUR — sunucu reddi (eski/elle yazilmis kayit uzerinden)");
{
  const simdiIso = new Date().toISOString();
  const isA = "a".repeat(32);
  await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'anahtarlik', 100, 'z', ?, 'hazir', 'gorev-eski-0001', ?)")
    .bind(isA, simdiIso, simdiIso).run();
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isA, olcu_mm: 100, adet: 1 }] } });
  ol("Q1 anahtarlik onizlemesinden /baslat -> 400 foto-kapali (odeme baslamaz)", b.kod === 400 && b.v.hata === "foto-kapali", JSON.stringify(b.v));
  await d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES ('PR-TEST-MAGNET', ?, 'odendi', 1, ?)")
    .bind(simdiIso, JSON.stringify([{ id: "ozel-foto-magnet", foto_is: isA, foto_tur: "magnet", olcu_mm: 100 }])).run();
  await d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-TEST-ANAHT', 0, ?, 'anahtarlik', 100, 'build-baslat', ?, '2000-01-01T00:00:00.000Z')")
    .bind(isA, simdiIso).run();
  const once = P.cagri.length;
  await cron();
  const q2 = await d1.prepare("SELECT COUNT(*) AS n FROM foto_uretim WHERE siparis_no = 'PR-TEST-MAGNET'").first();
  ol("Q2 odenmis 'magnet' kalemi uretim kuyruguna GIRMEZ", q2.n === 0, q2.n);
  const q3 = await d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-TEST-ANAHT'").first();
  const yeni = P.cagri.slice(once).filter((c) => /\/v1\/(build|prototype)/.test(c));
  ol("Q3 kuyruktaki 'anahtarlik' satiri saglayiciya GITMEZ, 'elle' + sebep tur-kapali",
     q3 && q3.asama === "elle" && q3.sebep === "tur-kapali" && yeni.length === 0, JSON.stringify(q3) + " " + yeni.join(","));
}

console.log("K) MARKASIZ (calisma agacinda)");
{
  // Aranan dizgeler ROT13 tutulur: bu dosyanin kendisi aramaya takilmasin (git grep 0 kalsin).
  const rot = (s) => s.replace(/[a-z]/g, (c) => String.fromCharCode((c.charCodeAt(0) - 97 + 13) % 26 + 97));
  // 🔴 `git grep --untracked` KULLANILMAZ: olculdu (5 Eki 2026, git 2.x) — bu bayrakla IZLENEN
  // dosyadaki bilinen bir gecisi BULMADI (rc=1), bayraksiz hali buldu; nobetci kor yesil
  // veriyordu. Dosya kumesi git'ten alinir (izlenen + izlenmeyen-ama-yok-sayilmayan) ve
  // icerik burada okunur — "0 dosya" iddiasi taranan dosya SAYISIYLA birlikte basilir.
  let dosyalar = [];
  try {
    const z = (a) => execFileSync("git", ["-C", KOK, "ls-files", "-z", ...a], { encoding: "utf8" }).split("\0").filter(Boolean);
    dosyalar = [...new Set([...z([]), ...z(["--others", "--exclude-standard"])])];
  } catch (e) { dosyalar = []; }
  ol("K taranacak dosya kumesi bos DEGIL (bos kume sessiz yesil olurdu)", dosyalar.length > 100, dosyalar.length);
  for (const [ad, desen] of [["saglayici adi", rot("zrful")], ["anahtar oneki", rot("zfl_")],
                             ["saglayici tur yolu (plaket)", rot("sevqtr-zntarg")],
                             ["saglayici urun ailesi", rot("perngvir-yno")]]) {
    const isabet = [];
    for (const rel of dosyalar) {
      let metin;
      try { metin = fs.readFileSync(path.join(KOK, rel), "utf8"); } catch (e) { continue; }
      if (metin.toLowerCase().includes(desen)) { isabet.push(rel); }
    }
    ol("K " + ad + " calisma agacinda 0 dosya (" + dosyalar.length + " dosya tarandi)", isabet.length === 0,
       isabet.slice(0, 5).join(", "));
  }
  // Bu genel kelime katalog arama araclarinda URUN anahtar sozcugu olarak gecer (saglayiciyla
  // ilgisiz); yalniz fotograftan uretim dosyalarinda 0 olmali.
  const fotoDosyalari = ["shop/src/foto.js", "foto-uretim.js", "foto-uretim-veri.js", "shop/wrangler.toml",
    "shop/src/yonet.js", "shop/src/index.js", "tools/d1-sema.sql", "tools/foto-uretim-bolum-test.py"];
  const eskiTur = fotoDosyalari.filter((rel) => {
    const m = fs.readFileSync(path.join(KOK, rel), "utf8").toLowerCase();
    return m.includes(rot("xrlpunva")) || m.includes(rot("sevqtr"));
  });
  ol("K eski tur yollari foto dosyalarinda 0 (" + fotoDosyalari.length + " dosya)", eskiTur.length === 0, eskiTur.join(","));
  const kaynak = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
  ol("K foto.js'te saglayici host'u yok (tek https sabiti bot dogrulayici)",
     (kaynak.match(/https:\/\/[a-z0-9.-]+/gi) || []).every((h) => h === "https://challenges.cloudflare.com"),
     (kaynak.match(/https:\/\/[a-z0-9.-]+/gi) || []).join(","));
}

console.log("L) DRIFT");
{
  const toml = fs.readFileSync(path.join(SHOP, "wrangler.toml"), "utf8");
  const idx = fs.readFileSync(path.join(SHOP, "src", "index.js"), "utf8");
  const cronSatiri = /^crons\s*=\s*\[(.*)\]/m.exec(toml);
  const idxCron = /const FOTO_CRON = "([^"]+)"/.exec(idx);
  ol("L1 wrangler.toml crons foto dizesini tasiyor = index.js FOTO_CRON",
     cronSatiri && idxCron && cronSatiri[1].includes('"' + idxCron[1] + '"'), cronSatiri && cronSatiri[1]);
  ol("L2 FOTO_RATE_LIMIT binding beyani VAR", /name\s*=\s*"FOTO_RATE_LIMIT"/.test(toml), "");
  const bin = { ...env }; delete bin.FOTO_RATE_LIMIT;
  const r = await istek(bin, "/foto/onizleme", { ip: "198.51.100.200", govde: onizlemeGovde() });
  ol("L3 binding yoksa onizleme 429 (fail-closed)", r.kod === 429, r.kod);
}

// ================================================================ S) EKRAN (tek turde tur adimi)
// Bolum dosyasi (foto-uretim.js) KUCUK bir sahte DOM'da GERCEKTEN calistirilir; /foto/acik
// yaniti sahte fetch'ten gelir. Sayilan sey cizilen DOM'dur (metin aramasi degil).
// POZITIF KONTROL: iki turlu yanitta tur radyo dugmesi 2 cizilmeli — sayac kor degil.

function sahteBelge() {
  class Metin {
    constructor(t) { this.nodeType = 3; this.metin = String(t); this.parentNode = null; this.childNodes = []; }
    get textContent() { return this.metin; }
  }
  class Oge {
    constructor(etiket) {
      this.tagName = String(etiket).toUpperCase(); this.nodeType = 1; this.childNodes = []; this.parentNode = null;
      this.ozn = {}; this.className = ""; this.hidden = false; this.style = {};
      const o = this;
      this.classList = {
        contains: (c) => o.className.split(/\s+/).includes(c),
        add: (c) => { if (!o.classList.contains(c)) { o.className = (o.className + " " + c).trim(); } },
        remove: (c) => { o.className = o.className.split(/\s+/).filter((x) => x && x !== c).join(" "); },
      };
    }
    get firstChild() { return this.childNodes[0] || null; }
    appendChild(c) { if (c.parentNode) { c.parentNode.removeChild(c); } this.childNodes.push(c); c.parentNode = this; return c; }
    insertBefore(c, ref) {
      if (c.parentNode) { c.parentNode.removeChild(c); }
      const i = this.childNodes.indexOf(ref);
      this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, c); c.parentNode = this; return c;
    }
    removeChild(c) { const i = this.childNodes.indexOf(c); if (i >= 0) { this.childNodes.splice(i, 1); } c.parentNode = null; return c; }
    remove() { if (this.parentNode) { this.parentNode.removeChild(this); } }
    setAttribute(k, v) { this.ozn[k] = String(v); if (k === "hidden") { this.hidden = true; } }
    getAttribute(k) { return k in this.ozn ? this.ozn[k] : null; }
    removeAttribute(k) { delete this.ozn[k]; if (k === "hidden") { this.hidden = false; } }
    addEventListener() {}
    set textContent(v) { this.childNodes = [new Metin(v)]; }
    get textContent() { return this.childNodes.map((c) => c.textContent).join(""); }
    *agac() { for (const c of this.childNodes) { if (c.nodeType === 1) { yield c; yield* c.agac(); } } }
    querySelector(s) {
      for (const n of this.agac()) {
        if (s.startsWith(".") ? n.classList.contains(s.slice(1)) : n.tagName === s.toUpperCase()) { return n; }
      }
      return null;
    }
  }
  const head = new Oge("head");
  const body = new Oge("body");
  const bolum = new Oge("section"); bolum.id = "fotoUretim"; bolum.setAttribute("hidden", "");
  body.appendChild(bolum);
  const document = {
    readyState: "complete", head, body,
    createElement: (e) => new Oge(e),
    createTextNode: (t) => new Metin(t),
    getElementById: (id) => { for (const n of [...head.agac(), ...body.agac()]) { if (n.id === id) { return n; } } return null; },
    querySelector: () => null,
    addEventListener: () => {},
  };
  return { document, bolum };
}

async function ekranKos(kaynak, fotoVeri, acikYanit, kayit, durumYanit) {
  const { document, bolum } = sahteBelge();
  const kok = {
    document, PRUVO_FOTO: fotoVeri, setTimeout, clearTimeout, setInterval, clearInterval, console,
    PRUVO_SECENEK: { kargoKurus: () => 25000, kurusMetni: (k) => (k / 100).toFixed(2) + " TL" },
    turnstile: { render: () => 1, remove() {}, reset() {} },
    sessionStorage: { getItem: (k) => (k === "pruvo_foto_is" && kayit ? JSON.stringify(kayit) : null), setItem() {}, removeItem() {} },
    location: { href: "https://pruvo3d.com/" },
    fetch: async (u) => ({ ok: true, status: 200, json: async () => (String(u).includes("/foto/durum") ? durumYanit : acikYanit) }),
  };
  kok.window = kok;
  vm.runInNewContext(kaynak, kok, { filename: "foto-uretim.js" });
  for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
  const dugum = [...bolum.agac()];
  const radyo = (ad) => dugum.filter((n) => n.tagName === "INPUT" && n.name === ad).length;
  const adim2 = dugum.filter((n) => n.classList.contains("foto-uretim-adim") && n.getAttribute("data-no") === "2")
    .map((n) => n.textContent)[0] || "";
  const turGrubu = dugum.filter((n) => n.classList.contains("foto-uretim-form-grup"))[0] || null;
  return { gorunur: !bolum.hidden, tur: radyo("foto-tur"), olcu: radyo("foto-olcu"), olcuS3: radyo("foto-olcu-s3"), adim2,
           turGrubuGizli: !!turGrubu && turGrubu.hidden === true };
}

console.log("S) EKRAN — tek turde tur secimi adimi gorunmez (sahte DOM'da gercek kosum)");
const EKRAN_KAYNAK = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
const acikTek = { acik: true, turler: [{ kod: "plaket", ad: "Kabartma plaket", aciklama: "x", ornek_sayisi: 1,
  olculer: [{ mm: 100, fiyat_kurus: 34900 }, { mm: 150, fiyat_kurus: 49900 }] }] };
const ikiTurVeri = { ...VERI, turler: [...VERI.turler, { kod: "ikinci", ad: "Ikinci", aciklama: "y" }],
  ornekler: [...VERI.ornekler, { tur: "ikinci", olcu_mm: 100, foto: "f", onizleme: "o", baski: "b" }] };
ikiTurVeri.ornekSayisi = (t) => ikiTurVeri.ornekler.filter((o) => o.tur === t && o.foto && o.onizleme && o.baski).length;
const acikIki = { acik: true, turler: [...acikTek.turler, { kod: "ikinci", ad: "Ikinci", aciklama: "y", ornek_sayisi: 1,
  olculer: [{ mm: 100, fiyat_kurus: 1000 }] }] };
let ekranTek, ekranIki;
{
  ekranTek = await ekranKos(EKRAN_KAYNAK, VERI, acikTek);
  ekranIki = await ekranKos(EKRAN_KAYNAK, ikiTurVeri, acikIki);
  ol("S0 pozitif kontrol: iki turde tur radyo dugmesi 2 + adim 'Tur ve olcu'",
     ekranIki.gorunur && ekranIki.tur === 2 && /Tür ve ölçü/.test(ekranIki.adim2), JSON.stringify(ekranIki));
  ol("S1 bolum cizildi ve olcu adimi var (plaket 2 olcu radyosu) — bos cizim sessiz yesil olmasin",
     ekranTek.gorunur && ekranTek.olcu === 2, JSON.stringify(ekranTek));
  ol("S2 tek turde tur radyo dugmesi 0 + tur grubu gizli", ekranTek.tur === 0 && ekranTek.turGrubuGizli, JSON.stringify(ekranTek));
  ol("S3 tek turde adim cubugu 'Olcu' der ('Tur' kelimesi yok)",
     /^2\. Ölçü$/.test(ekranTek.adim2), ekranTek.adim2);
  const mutTur = EKRAN_KAYNAK.replace(
    "    if (S.acikVeri.turler.length === 1) {\n      S.tur = S.acikVeri.turler[0].kod;\n      S.alanTur.hidden = true;\n      return;\n    }\n", "");
  const mt = mutTur === EKRAN_KAYNAK ? null : await ekranKos(mutTur, VERI, acikTek);
  ol("S-M1 mutant (tek tur dali silindi) -> S2 KIRMIZI (tur radyosu 1)", !!mt && mt.tur === 1, JSON.stringify(mt));
  const mutAdim = EKRAN_KAYNAK.replace('F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"', '"Tür ve ölçü"');
  const ma = mutAdim === EKRAN_KAYNAK ? null : await ekranKos(mutAdim, VERI, acikTek);
  ol("S-M2 mutant (adim etiketi sabit) -> S3 KIRMIZI", !!ma && !/^2\. Ölçü$/.test(ma.adim2), JSON.stringify(ma));
  // 5 Eki 2026 olculen hata: olcu radyosu etikete eklenmiyordu (musteri olcu SECEMIYORDU).
  const mutOlcu = EKRAN_KAYNAK.replace("ek(lbl, inp, \" \");", "ek(lbl, \" \");");
  const mo = mutOlcu === EKRAN_KAYNAK ? null : await ekranKos(mutOlcu, VERI, acikTek);
  ol("S-M3 mutant (olcu radyosu eklenmez) -> S1 KIRMIZI (olcu radyosu 0)", !!mo && mo.olcu === 0, JSON.stringify(mo));
  // Onizleme hazir donusu (S3): olcu degistirme radyolari da cizilmeli (ayni hata orada da vardi).
  const kayit = { is: "b".repeat(32), tur: "plaket", olcu: 100 };
  const hazir = { asama: "hazir", tur: "plaket", olcu_mm: 100, gorsel: "/api/shop/foto/gorsel?is=" + "b".repeat(32) };
  const s3 = await ekranKos(EKRAN_KAYNAK, VERI, acikTek, kayit, hazir);
  ol("S4 onizleme sonrasi (S3) olcu degistirme radyosu 2 (plaket 2 olcu)", s3.olcuS3 === 2, JSON.stringify(s3));
  const son = EKRAN_KAYNAK.lastIndexOf("ek(lbl, inp, \" \");");
  const mutS3 = son > EKRAN_KAYNAK.indexOf("ek(lbl, inp, \" \");")
    ? EKRAN_KAYNAK.slice(0, son) + "ek(lbl, \" \");" + EKRAN_KAYNAK.slice(son + "ek(lbl, inp, \" \");".length) : null;
  const m3 = mutS3 ? await ekranKos(mutS3, VERI, acikTek, kayit, hazir) : null;
  ol("S-M4 mutant (S3 olcu radyosu eklenmez) -> S4 KIRMIZI", !!m3 && m3.olcuS3 === 0, JSON.stringify(m3));
}

// ================================================================ MUTANTLAR

console.log("MUTANTLAR (gecici kopya; calisma agacina yazilmaz)");
const GECICI = path.join(SHOP, "foto-test-tmp-" + process.pid);
process.on("exit", () => { fs.rmSync(GECICI, { recursive: true, force: true }); });
const ASIL = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
let mutantNo = 0;

async function mutantModul(capa, yerine) {
  if (ASIL.split(capa).length - 1 !== 1) { return null; }
  fs.mkdirSync(GECICI, { recursive: true });
  const dosya = path.join(GECICI, "foto-" + (++mutantNo) + ".js");
  fs.writeFileSync(dosya, ASIL.replace(capa, yerine));
  return import(url.pathToFileURL(dosya).href);
}

/** Mutanta karsi uc dar senaryo; her biri temiz bir SQLite ile. Donus: {D, E, J} gecti mi. */
async function darSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES ('plaket', 100, 34900, 'x')").run();
  const cag = async (yol, govde, ip) => {
    const r = await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, { method: "POST",
      headers: { "CF-Connecting-IP": ip, "Content-Type": "application/json" }, body: JSON.stringify(govde) }),
      e2, new URL("https://pruvo3d.com/api/shop" + yol), yol, null);
    return r.status;
  };
  const sonuc = {};
  const kodlar = [];
  for (let i = 0; i <= VERI.sinir_ziyaretci_24s; i++) { kodlar.push(await cag("/foto/onizleme", onizlemeGovde(), "10.0.0.1")); }
  sonuc.D = kodlar[kodlar.length - 1] === 429;
  P.turnstile = "red";
  sonuc.E = (await cag("/foto/onizleme", onizlemeGovde(), "10.0.0.2")) === 403;
  P.turnstile = "ok";
  const is = "c".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-9999', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  // A: odeme kalemi plaket basina ayak tasir (uretimde unutulmasin).
  const fs_ = await fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: 100, adet: 1 }, Date.now());
  sonuc.A = !!fs_.satir && fs_.satir.foto_ayak === 1 && /ayak: 1/.test(fs_.satir.parametre_detay);
  await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES ('PR-TEST-MUT', ?, 'odendi', 1, ?)")
    .bind(new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100 }])).run();
  P.analiz = "error";
  for (let i = 0; i < 4; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
  P.analiz = "healthy";
  const u = await k.d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = 'PR-TEST-MUT'").first();
  sonuc.J = !!u && u.asama === "elle";
  // T: sunulmayan tur — panel fiyat reddi + kuyruktaki satir saglayiciya gitmeden 'elle'.
  const pf = await fm.panelFotoFiyat(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tur: "anahtarlik", olcu_mm: 100, fiyat_kurus: 100 }) }), e2, Date.now());
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-TEST-T', 0, ?, 'anahtarlik', 100, 'build-baslat', ?, '2000-01-01T00:00:00.000Z')")
    .bind(is, new Date().toISOString()).run();
  await fm.fotoUretimTuru(e2, Date.now(), null);
  const t = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-TEST-T'").first();
  sonuc.T = pf.status === 400 && !!t && t.sebep === "tur-kapali";
  k.kapat();
  return sonuc;
}

const MUTANTLAR = [
  ["M1 SINIR", "if (sayi.kisi >= VERI.sinir_ziyaretci_24s) {", "if (false) {", "D"],
  ["M2 BOT", "if (!(await botDogrula(request, env, g.turnstile_token))) {", "if (false) {", "E"],
  ["M3 ANALIZ", "if (p.status !== \"healthy\" && p.status !== \"warning\") {", "if (false) {", "J"],
  ["M4 ANAHTARLIK GERI ACILDI", "export const TUR_ORTAM = { plaket: \"URETIM_TUR_PLAKET\" };",
   "export const TUR_ORTAM = { plaket: \"URETIM_TUR_PLAKET\", anahtarlik: \"URETIM_TUR_PLAKET\" };", "T"],
  ["M5 AYAK DUSTU", "      foto_ayak: AYAK_PLAKET_BASI,\n", "", "A"],
  ["K0 KONTROL", "console.log(\"FOTO_URETIM kuyruga=\"", "console.log(\"FOTO_URETIM  kuyruga=\"", null],
];
for (const [ad, capa, yerine, olmeli] of MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await darSenaryolar(fm);
  if (olmeli) {
    ol(ad + " -> " + olmeli + " KIRMIZI yanar (digerleri yesil)",
       s[olmeli] === false && Object.keys(s).filter((x) => x !== olmeli).every((x) => s[x] === true), JSON.stringify(s));
  } else {
    ol(ad + " -> hicbir senaryo kirmizi yanmaz", Object.values(s).length === 5 && Object.values(s).every((x) => x === true), JSON.stringify(s));
  }
}

kopru.kapat();
await Promise.allSettled(ctx.bekleyen);
console.log(kirmizi ? "\n❌ " + kirmizi + " iddia KIRMIZI" : "\n✅ HEPSI GECTI");
process.exit(kirmizi ? 1 : 0);
