#!/usr/bin/env node
/**
 * PRUVO shop — YONETIM PANELI "URUNLER" SEKMESI (T1) kabul testi.
 *
 *   node shop/test/urunler-panel.mjs
 *
 * NE OLCER (wrangler/ag/D1 YOK — wa-siparis.mjs deseni, env.KATALOG mock):
 *   A. YETKI: 4 yeni uc yonetim anahtarinin ARKASINDA; EGE_ANAHTAR HICBIRINI acamaz
 *      (en az yetki), secret'siz kurulumda 404 (varlik sizmasi yok), cerez de acar.
 *   B. KUYRUK YAZIMI: gecerli deger hal='beklemede' satir olur; ayni (urun, alan)
 *      bekleyen satiri YENISI degistirir (INSERT cogaltmaz); beyaz liste disi alan,
 *      bozuk fiyat bicimi, parametrik urunde fiyat, olmayan urun, bicimsiz id,
 *      kontrol karakteri REDDEDILIR ve kuyruga TEK BAYT yazilmaz.
 *   C. IPTAL: yalniz hal='beklemede' satir silinir (islendi/hata gecmisi silinemez).
 *   D. FAIL-CLOSED SEMA: panel_ustyazim tablosu yoksa YAZMA 503 doner ("kaydedildi"
 *      yalani imkansiz); OKUMA ekrana "tablo yok"u ACIKCA tasir (sessiz bosluk degil).
 *   E. TETIK: GH_DISPATCH_TOKEN tanimsizsa DISARI HIC istek cikmaz; tanimliysa
 *      repository_dispatch ctx.waitUntil ile gider (yanit bekletilmez).
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek urun/tedarikci/musteri verisi yazilmaz.
 * Tabana isleme bu dosyanin MENZILI DISIDIR — o eksen tools/panel-uygulayici.py
 * --kendini-test bataryasinda olculur (28 vaka + 2 mutant); iki test ayni iddiayi
 * iki yerde OLCMEZ: burasi worker yuzeyi, orasi uygulayici.
 */
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) { return { ...r, importAttributes: { type: 'json' } }; }" +
  "  return r; }"));
import { createRequire } from "node:module";
import path from "node:path";
const req = createRequire(import.meta.url);
req(path.join(path.dirname(new URL(import.meta.url).pathname), "..", "..", "secenekler.js"));

const { yonet } = await import("../src/yonet.js");

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

const YONET_ANAHTAR = "y".repeat(48);
const EGE_ANAHTAR = "e".repeat(48);

// ---------------------------------------------------------------- D1 mock
// panel_ustyazim icin DURUM TASIYAN taklit: UPDATE/INSERT/DELETE gercek satir
// listesi uzerinde calisir ki "yenisi eskisinin yerine gecer" / "yalniz beklemede
// silinir" iddialari SQL metnine degil DAVRANISA baglansin.
function mockEnv(secenek) {
  secenek = secenek || {};
  const kuyruk = (secenek.kuyruk || []).map((s) => ({ ...s }));
  let sonId = kuyruk.reduce((m, s) => Math.max(m, s.id || 0), 0);
  const urunler = secenek.urunler || [
    { id: "test-urun-a", baslik: "Test Urun A", fiyat: "200 TL", aciklama: "aciklama a",
      kategori: "Ofis", parametrik: 0, gorsel: "https://media.pruvo3d.com/urunler/ta-1.jpg", seq: 2 },
    { id: "test-urun-b", baslik: "Test Urun B", fiyat: "300 TL", aciklama: "aciklama b",
      kategori: "Ev", parametrik: 0, gorsel: "", seq: 1 },
    { id: "test-parametrik", baslik: "Test Parametrik", fiyat: "", aciklama: "olcuye ozel",
      kategori: "Jeneratör", parametrik: 1, gorsel: "", seq: 3 },
  ];
  const env = {
    kuyruk,
    YONET_ANAHTAR: secenek.yonetAnahtar === null ? undefined : YONET_ANAHTAR,
    EGE_ANAHTAR,
    SITE_URL: "https://ornek-site.test",
    GH_DISPATCH_TOKEN: secenek.ghToken || undefined,
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (secenek.tabloYok && /panel_ustyazim/.test(sql)) {
            throw new Error("D1_ERROR: no such table: panel_ustyazim");
          }
          const a = kayit.args;
          if (/FROM urunler WHERE id = \?/.test(sql)) {
            return urunler.find((u) => u.id === a[0]) || null;
          }
          if (/FROM urunler WHERE id LIKE/.test(sql)) {
            const d = String(a[0]).replace(/^%|%$/g, "").replace(/\\(.)/g, "$1");
            return { results: urunler.filter((u) => u.id.includes(d) || u.baslik.includes(d))
              .slice(0, a[2]) };
          }
          if (/FROM urunler ORDER BY seq DESC/.test(sql)) {
            return { results: urunler.slice().sort((x, y) => y.seq - x.seq).slice(0, a[0]) };
          }
          if (/FROM panel_ustyazim\s+WHERE hal = 'beklemede' AND urun_id IN/.test(sql)) {
            return { results: kuyruk.filter((s) => s.hal === "beklemede" && a.includes(s.urun_id)) };
          }
          if (/FROM panel_ustyazim ORDER BY id DESC/.test(sql)) {
            return { results: kuyruk.slice().sort((x, y) => y.id - x.id).slice(0, 100) };
          }
          if (/^UPDATE panel_ustyazim SET deger = \?/.test(sql)) {
            let n = 0;
            for (const s of kuyruk) {
              if (s.urun_id === a[2] && s.alan === a[3] && s.hal === "beklemede") {
                s.deger = a[0]; s.ts = a[1]; s.yazan = "panel"; n++;
              }
            }
            return { meta: { changes: n } };
          }
          if (/^INSERT INTO panel_ustyazim/.test(sql)) {
            sonId++;
            kuyruk.push({ id: sonId, urun_id: a[0], alan: a[1], deger: a[2],
                          yazan: "panel", ts: a[3], hal: "beklemede" });
            return { meta: { changes: 1 } };
          }
          if (/^DELETE FROM panel_ustyazim WHERE id = \? AND hal = 'beklemede'/.test(sql)) {
            const i = kuyruk.findIndex((s) => s.id === a[0] && s.hal === "beklemede");
            if (i >= 0) { kuyruk.splice(i, 1); return { meta: { changes: 1 } }; }
            return { meta: { changes: 0 } };
          }
          throw new Error("mock: beklenmeyen SQL: " + sql);
        };
        return {
          bind(...args) { kayit.args = args; return this; },
          async run() { return calistir("run"); },
          async all() { return calistir("all"); },
          async first() { return calistir("first"); },
        };
      },
    },
  };
  return env;
}

function istek(govde, baslik, method) {
  const H = baslik || {};
  return {
    method: method || "POST",
    headers: { get: (h) => (H[h] !== undefined ? H[h] : null) },
    json: async () => {
      if (govde === "BOZUK") { throw new Error("gecersiz json"); }
      return govde;
    },
  };
}
function ctxYap() {
  const isler = [];
  return { isler, waitUntil(p) { isler.push(p); } };
}
async function cagir(env, altYol, secenek) {
  secenek = secenek || {};
  const u = new URL("https://ornek-site.test/api/shop/yonet" + altYol + (secenek.sorgu || ""));
  const c = secenek.ctx || ctxYap();
  const y = await yonet(istek(secenek.govde, secenek.baslik ||
    { "X-Yonet-Anahtar": YONET_ANAHTAR }, secenek.method || (secenek.govde ? "POST" : "GET")),
    env, u, c, altYol, undefined);
  let govde = null;
  try { govde = JSON.parse(await y.text()); } catch (e) { govde = null; }
  return { kod: y.status, govde, ctx: c };
}

// ---------------------------------------------------------------- A. YETKI
console.log("A. YETKI (4 yeni uc yonetim anahtari arkasinda; EGE acamaz)");
{
  const UCLAR = [["/urunler", "GET", undefined],
                 ["/urunler-kuyruk", "GET", undefined],
                 ["/urunler-ustyazim", "POST", { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" }],
                 ["/urunler-ustyazim-sil", "POST", { id: 1 }]];
  for (const [yol, m, govde] of UCLAR) {
    const r1 = await cagir(mockEnv(), yol, { baslik: {}, method: m, govde });
    ol("A1 anahtarsiz " + m + " " + yol + " -> 404", r1.kod === 404, "kod=" + r1.kod);
    const r2 = await cagir(mockEnv(), yol,
      { baslik: { "X-Ege-Anahtar": EGE_ANAHTAR }, method: m, govde });
    ol("A2 EGE anahtariyla " + yol + " -> 404 (en az yetki)", r2.kod === 404, "kod=" + r2.kod);
    const r3 = await cagir(mockEnv({ yonetAnahtar: null }), yol,
      { baslik: { "X-Yonet-Anahtar": YONET_ANAHTAR }, method: m, govde });
    ol("A3 secret'siz kurulumda " + yol + " -> 404 (ozellik kapali)", r3.kod === 404);
  }
  const r4 = await cagir(mockEnv(), "/urunler");
  ol("A4 yonetim anahtariyla GET /urunler -> 200", r4.kod === 200, "kod=" + r4.kod);
  const r5 = await cagir(mockEnv(), "/urunler",
    { baslik: { "Cookie": "pruvo_yonet=" + YONET_ANAHTAR } });
  ol("A5 HttpOnly cerezle de acilir", r5.kod === 200, "kod=" + r5.kod);
}

// ---------------------------------------------------------------- B. KUYRUK YAZIMI
console.log("B. KUYRUK YAZIMI (beyaz liste + bicim + parametrik + cogaltmama)");
{
  const env = mockEnv();
  const r = await cagir(env, "/urunler-ustyazim",
    { govde: { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" } });
  ol("B1a gecerli fiyat -> 200 hal=beklemede", r.kod === 200 && r.govde.hal === "beklemede",
     JSON.stringify(r.govde));
  ol("B1b kuyrukta TEK satir, deger/alan dogru", env.kuyruk.length === 1 &&
     env.kuyruk[0].deger === "500 TL" && env.kuyruk[0].alan === "fiyat" &&
     env.kuyruk[0].hal === "beklemede" && !!env.kuyruk[0].ts, JSON.stringify(env.kuyruk));
  const r2 = await cagir(env, "/urunler-ustyazim",
    { govde: { urun_id: "test-urun-a", alan: "fiyat", deger: "550 TL" } });
  ol("B2 ayni (urun, alan) yeniden -> yenisi ESKISININ YERINE (satir sayisi 1 kalir)",
     r2.kod === 200 && env.kuyruk.length === 1 && env.kuyruk[0].deger === "550 TL",
     JSON.stringify(env.kuyruk));
}
{
  const RED = [
    ["B3 beyaz liste disi alan (kategori)", { urun_id: "test-urun-a", alan: "kategori", deger: "Ev" }, 400],
    ["B3b beyaz liste disi alan (uyelik — gizli duzlem kuyruga giremez)",
     { urun_id: "test-urun-a", alan: "uyelik", deger: "x" }, 400],
    ["B4a fiyat bicimi: TL'siz", { urun_id: "test-urun-a", alan: "fiyat", deger: "500" }, 400],
    ["B4b fiyat bicimi: kucuk tl", { urun_id: "test-urun-a", alan: "fiyat", deger: "500 tl" }, 400],
    ["B4c fiyat bicimi: 0 ile baslar", { urun_id: "test-urun-a", alan: "fiyat", deger: "0 TL" }, 400],
    ["B4d fiyat bicimi: ondalik", { urun_id: "test-urun-a", alan: "fiyat", deger: "500.00 TL" }, 400],
    ["B5 parametrik urunde fiyat", { urun_id: "test-parametrik", alan: "fiyat", deger: "500 TL" }, 400],
    ["B6 olmayan urun", { urun_id: "boyle-urun-yok", alan: "fiyat", deger: "500 TL" }, 404],
    ["B7a bicimsiz id (buyuk harf)", { urun_id: "Test-Urun", alan: "fiyat", deger: "500 TL" }, 400],
    ["B7b bicimsiz id (yol)", { urun_id: "../etc", alan: "fiyat", deger: "500 TL" }, 400],
    ["B8a baslikta satir sonu", { urun_id: "test-urun-a", alan: "baslik", deger: "a\nb" }, 400],
    ["B8b kontrol karakteri", { urun_id: "test-urun-a", alan: "baslik", deger: "a\u0007b" }, 400],
    ["B8c bos deger", { urun_id: "test-urun-a", alan: "baslik", deger: "   " }, 400],
    ["B8d deger metin degil", { urun_id: "test-urun-a", alan: "fiyat", deger: 500 }, 400],
    ["B8e tavan asimi", { urun_id: "test-urun-a", alan: "baslik", deger: "x".repeat(201) }, 400],
    ["B9 bozuk govde", "BOZUK", 400],
  ];
  for (const [ad, govde, kod] of RED) {
    const env = mockEnv();
    const r = await cagir(env, "/urunler-ustyazim", { govde });
    ol(ad + " -> " + kod + " + kuyruga sifir yazim",
       r.kod === kod && env.kuyruk.length === 0,
       "kod=" + r.kod + " kuyruk=" + env.kuyruk.length);
  }
  const env2 = mockEnv();
  const r = await cagir(env2, "/urunler-ustyazim",
    { govde: { urun_id: "test-urun-a", alan: "aciklama", deger: "satir 1\nsatir 2" } });
  ol("B10 aciklamada coklu satir MESRU", r.kod === 200 && env2.kuyruk.length === 1);
}

// ---------------------------------------------------------------- C. IPTAL
console.log("C. IPTAL (yalniz beklemede silinir)");
{
  const env = mockEnv({ kuyruk: [
    { id: 7, urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL", yazan: "panel",
      ts: "2026-08-30T00:00:00Z", hal: "beklemede" },
    { id: 8, urun_id: "test-urun-b", alan: "fiyat", deger: "400 TL", yazan: "panel",
      ts: "2026-08-30T00:00:00Z", hal: "islendi" },
  ] });
  const r1 = await cagir(env, "/urunler-ustyazim-sil", { govde: { id: 7 } });
  ol("C1 beklemede satir silinir", r1.kod === 200 && env.kuyruk.length === 1);
  const r2 = await cagir(env, "/urunler-ustyazim-sil", { govde: { id: 8 } });
  ol("C2 islendi satir SILINEMEZ (gecmis kayittir) -> 409",
     r2.kod === 409 && env.kuyruk.length === 1, "kod=" + r2.kod);
  const r3 = await cagir(env, "/urunler-ustyazim-sil", { govde: { id: "abc" } });
  ol("C3 bozuk id -> 400", r3.kod === 400);
}

// ---------------------------------------------------------------- D. LISTE + SEMA
console.log("D. LISTE/KUYRUK + fail-closed sema");
{
  const env = mockEnv({ kuyruk: [
    { id: 3, urun_id: "test-urun-a", alan: "fiyat", deger: "999 TL", yazan: "panel",
      ts: "2026-08-30T00:00:00Z", hal: "beklemede" }] });
  const r = await cagir(env, "/urunler");
  ol("D1a liste 200 + urunler dolu + kuyruk_tablosu=true",
     r.kod === 200 && r.govde.urunler.length === 3 && r.govde.kuyruk_tablosu === true);
  ol("D1b bekleyen ustyazim karta tasinir",
     r.govde.bekleyen["test-urun-a"] && r.govde.bekleyen["test-urun-a"].fiyat.deger === "999 TL",
     JSON.stringify(r.govde.bekleyen));
  const r2 = await cagir(env, "/urunler", { sorgu: "?q=urun-b" });
  ol("D1c arama daraltir", r2.kod === 200 && r2.govde.urunler.length === 1 &&
     r2.govde.urunler[0].id === "test-urun-b", JSON.stringify(r2.govde.urunler));
  const r3 = await cagir(env, "/urunler-kuyruk");
  ol("D2 kuyruk gorunumu satirlari doner", r3.kod === 200 && r3.govde.satirlar.length === 1 &&
     r3.govde.tablo_yok === false);
}
{
  const env = mockEnv({ tabloYok: true });
  const r1 = await cagir(env, "/urunler");
  ol("D3a tablo yokken OKUMA 200 + kuyruk_tablosu=false (ekran ACIKCA yazar)",
     r1.kod === 200 && r1.govde.kuyruk_tablosu === false, "kod=" + r1.kod);
  const r2 = await cagir(env, "/urunler-kuyruk");
  ol("D3b tablo yokken kuyruk gorunumu tablo_yok=true", r2.kod === 200 && r2.govde.tablo_yok === true);
  const r3 = await cagir(env, "/urunler-ustyazim",
    { govde: { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" } });
  ol("D3c tablo yokken YAZMA 503 (fail-closed: 'kaydedildi' yalani imkansiz)",
     r3.kod === 503, "kod=" + r3.kod);
  const r4 = await cagir(env, "/urunler-ustyazim-sil", { govde: { id: 1 } });
  ol("D3d tablo yokken SILME 503", r4.kod === 503, "kod=" + r4.kod);
}

// ---------------------------------------------------------------- E. TETIK
console.log("E. repository_dispatch tetigi (opsiyonel, en-iyi-caba)");
{
  const eskiFetch = globalThis.fetch;
  const cagrilar = [];
  globalThis.fetch = (adres, sec) => { cagrilar.push({ adres, sec }); return Promise.resolve({ ok: true }); };
  try {
    const env1 = mockEnv();
    const r1 = await cagir(env1, "/urunler-ustyazim",
      { govde: { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" } });
    ol("E1 token TANIMSIZ -> disari SIFIR istek, yazim yine 200",
       r1.kod === 200 && cagrilar.length === 0 && r1.ctx.isler.length === 0,
       "fetch=" + cagrilar.length);
    const env2 = mockEnv({ ghToken: "t".repeat(20) });
    const r2 = await cagir(env2, "/urunler-ustyazim",
      { govde: { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" } });
    await Promise.all(r2.ctx.isler);
    const d = cagrilar[0];
    ol("E2a token TANIMLI -> repository_dispatch waitUntil ile gider",
       r2.kod === 200 && r2.ctx.isler.length === 1 && cagrilar.length === 1,
       "fetch=" + cagrilar.length);
    ol("E2b hedef github /dispatches + event_type=panel-ustyazim",
       d && /api\.github\.com\/repos\/.+\/dispatches$/.test(d.adres) &&
       JSON.parse(d.sec.body).event_type === "panel-ustyazim",
       d && d.adres);
    ol("E2c anahtar govdede DEGIL baslikta", d && !String(d.sec.body).includes("t".repeat(20)) &&
       d.sec.headers.Authorization === "Bearer " + "t".repeat(20));
  } finally {
    globalThis.fetch = eskiFetch;
  }
}

console.log("");
console.log("TOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
process.exit(kalan === 0 ? 0 : 1);
