#!/usr/bin/env node
/**
 * PRUVO shop — YONETIM PANELI "URUNLER" SEKMESI (T1 + T2) kabul testi.
 *
 *   node shop/test/urunler-panel.mjs
 *
 * NE OLCER (wrangler/ag/D1 YOK — wa-siparis.mjs deseni, env.KATALOG mock):
 *   A. YETKI: 10 uc (T1: 4 + T2: 6) yonetim anahtarinin ARKASINDA; EGE_ANAHTAR
 *      HICBIRINI acamaz (en az yetki), secret'siz kurulumda 404, cerez de acar.
 *   B. KUYRUK YAZIMI: gecerli deger hal='beklemede' satir olur; ayni (urun, alan)
 *      bekleyen satiri YENISI degistirir (INSERT cogaltmaz); beyaz liste disi alan,
 *      bozuk fiyat bicimi, parametrik urunde fiyat, olmayan urun, bicimsiz id,
 *      kontrol karakteri REDDEDILIR ve kuyruga TEK BAYT yazilmaz.
 *   C. IPTAL: yalniz hal='beklemede' satir silinir (islendi/hata gecmisi silinemez).
 *   D. FAIL-CLOSED SEMA: panel_ustyazim tablosu yoksa YAZMA 503 doner ("kaydedildi"
 *      yalani imkansiz); OKUMA ekrana "tablo yok"u ACIKCA tasir (sessiz bosluk degil).
 *   E. TETIK: GH_DISPATCH_TOKEN tanimsizsa DISARI HIC istek cikmaz; tanimliysa
 *      repository_dispatch ctx.waitUntil ile gider (yanit bekletilmez).
 *   F. (T2) gorseller USTYAZIMI: JSON dizi + onek + tekil + tavan erken uyarisi;
 *      RED'de kuyruga tek bayt yazilmaz.
 *   G. (T2) /urun-gorseller: CANLI tabandan (urunler.json dilim-parse) liste;
 *      okunamayan taban 502 (sessiz bos liste YOK); bekleyen ustyazim yansir.
 *   H. (T2) /gorsel-yukle: icerik-hash anahtar; AYNI icerik ikinci kez PUT URETMEZ
 *      (mevcut anahtar EZILMEZ); tur dosya imzasindan; MEDYA binding yoksa 503.
 *   I. (T2) /stl-yukle: var olan ada 409 (EZILMEZ); ayirac/uzanti savunmasi.
 *   J. (T2) /stl-cikar: arsiv kopyasi TEYIT edilmeden orijinal SILINMEZ.
 *   K. (T2) kaynak link: yalniz gizli D1 (panel_kaynak); panel satiri sync'i
 *      GOLGELER, link='' cikarildi; https disi RED; tablo yoksa 503.
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek urun/tedarikci/musteri verisi yazilmaz.
 * Tabana isleme bu dosyanin MENZILI DISIDIR — o eksen tools/panel-uygulayici.py
 * --kendini-test bataryasinda olculur (38 vaka + 3 mutant); iki test ayni iddiayi
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
// R2 mock — DURUM TASIYAN: head/put/get/delete/list gercek Map uzerinde calisir,
// cagri sayaclari "PUT hic atilmadi" gibi EZILMEZLIK iddialarini davranisa baglar.
function r2Mock(baslangic) {
  const depo = new Map();
  for (const [k, boyut] of (baslangic || [])) {
    depo.set(k, { boyut, govde: "x".repeat(boyut) });
  }
  const sayac = { put: 0, sil: 0 };
  const boyutOl = (g) => (g && g.byteLength !== undefined) ? g.byteLength
    : (typeof g === "string" ? g.length : (g && g.boyut) || 0);
  return {
    depo, sayac,
    async head(k) { const o = depo.get(k); return o ? { size: o.boyut } : null; },
    async get(k) {
      const o = depo.get(k);
      return o ? { body: o.govde, size: o.boyut } : null;
    },
    async put(k, govde, sec) {
      sayac.put++;
      depo.set(k, { boyut: boyutOl(govde), govde,
                    tip: sec && sec.httpMetadata && sec.httpMetadata.contentType });
    },
    async delete(k) { sayac.sil++; depo.delete(k); },
    async list(sec) {
      const on = (sec && sec.prefix) || "";
      return { objects: [...depo.keys()].filter((k) => k.startsWith(on))
        .map((k) => ({ key: k, size: depo.get(k).boyut })) };
    },
  };
}

function mockEnv(secenek) {
  secenek = secenek || {};
  const kuyruk = (secenek.kuyruk || []).map((s) => ({ ...s }));
  const panelKaynak = new Map(secenek.panelKaynak || []);
  const urunKaynak = new Map(secenek.urunKaynak || []);
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
    kuyruk, panelKaynak, urunKaynak,
    YONET_ANAHTAR: secenek.yonetAnahtar === null ? undefined : YONET_ANAHTAR,
    EGE_ANAHTAR,
    SITE_URL: "https://ornek-site.test",
    GH_DISPATCH_TOKEN: secenek.ghToken || undefined,
    OZEL_DOSYA: secenek.ozel === null ? undefined : (secenek.ozel || r2Mock()),
    MEDYA: secenek.medya === null ? undefined : (secenek.medya || r2Mock()),
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (secenek.tabloYok && /panel_ustyazim/.test(sql)) {
            throw new Error("D1_ERROR: no such table: panel_ustyazim");
          }
          if (secenek.kaynakTabloYok && /panel_kaynak/.test(sql)) {
            throw new Error("D1_ERROR: no such table: panel_kaynak");
          }
          const a = kayit.args;
          if (/FROM panel_ustyazim WHERE hal = 'beklemede' AND urun_id = \? AND alan = 'gorseller'/.test(sql)) {
            return kuyruk.find((s) => s.hal === "beklemede" && s.urun_id === a[0] &&
                                      s.alan === "gorseller") || null;
          }
          if (/FROM panel_kaynak WHERE id = \?/.test(sql)) {
            return panelKaynak.has(a[0]) ? { id: a[0], link: panelKaynak.get(a[0]) } : null;
          }
          if (/FROM urun_kaynak WHERE id = \?/.test(sql)) {
            return urunKaynak.has(a[0]) ? { id: a[0], link: urunKaynak.get(a[0]) } : null;
          }
          if (/^INSERT INTO panel_kaynak/.test(sql)) {
            panelKaynak.set(a[0], a[1]);
            return { meta: { changes: 1 } };
          }
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
  const ham = govde instanceof ArrayBuffer;
  return {
    method: method || "POST",
    headers: { get: (h) => (H[h] !== undefined ? H[h] : null) },
    body: ham ? govde : null,
    arrayBuffer: async () => (ham ? govde : new ArrayBuffer(0)),
    json: async () => {
      if (govde === "BOZUK" || ham) { throw new Error("gecersiz json"); }
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
console.log("A. YETKI (T1+T2 10 uc yonetim anahtari arkasinda; EGE acamaz)");
{
  const UCLAR = [["/urunler", "GET", undefined],
                 ["/urunler-kuyruk", "GET", undefined],
                 ["/urunler-ustyazim", "POST", { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" }],
                 ["/urunler-ustyazim-sil", "POST", { id: 1 }],
                 ["/urun-gorseller", "GET", undefined],
                 ["/gorsel-yukle", "POST", new Uint8Array([0xff, 0xd8, 0xff, 1]).buffer],
                 ["/stl-yukle", "POST", new Uint8Array([1, 2, 3]).buffer],
                 ["/stl-cikar", "POST", { id: "test-urun-a", dosya: "a.stl" }],
                 ["/urun-kaynak", "GET", undefined],
                 ["/kaynak-yaz", "POST", { id: "test-urun-a", link: "https://ornek.test/x" }]];
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

// ---------------------------------------------------------------- F. GORSELLER USTYAZIMI
console.log("F. gorseller ustyazimi (JSON dizi + onek + tekil; RED'de sifir yazim)");
{
  const M = "https://media.pruvo3d.com/urunler/";
  const env = mockEnv();
  const r = await cagir(env, "/urunler-ustyazim",
    { govde: { urun_id: "test-urun-a", alan: "gorseller",
               deger: JSON.stringify([M + "ta-2.jpg", M + "ta-1.jpg"]) } });
  ol("F1 gecerli liste -> 200 hal=beklemede + kuyrukta TEK satir",
     r.kod === 200 && env.kuyruk.length === 1 && env.kuyruk[0].alan === "gorseller",
     JSON.stringify(r.govde));
  const RED = [
    ["F2 bozuk JSON", "bozuk ["],
    ["F3 dizi degil", JSON.stringify({ a: 1 })],
    ["F4 bos liste (urun silme yolu yok)", "[]"],
    ["F5 onek disi adres", JSON.stringify(["https://kotu.example/x.jpg"])],
    ["F6 tekrarli oge", JSON.stringify([M + "a.jpg", M + "a.jpg"])],
    ["F7 sayi tavani (25 oge)", JSON.stringify(
      Array.from({ length: 25 }, (x, i) => M + "g" + i + ".jpg"))],
  ];
  for (const [ad, deger] of RED) {
    const e2 = mockEnv();
    const r2 = await cagir(e2, "/urunler-ustyazim",
      { govde: { urun_id: "test-urun-a", alan: "gorseller", deger } });
    ol(ad + " -> 400 + kuyruga sifir yazim", r2.kod === 400 && e2.kuyruk.length === 0,
       "kod=" + r2.kod + " " + JSON.stringify(r2.govde));
  }
}

// ---------------------------------------------------------------- G. /urun-gorseller
console.log("G. /urun-gorseller (CANLI tabandan dilim-parse; okunamayan taban 502)");
{
  const M = "https://media.pruvo3d.com/urunler/";
  const TABAN = JSON.stringify([
    { id: "test-urun-a", kategori: "Ofis",
      gorseller: [M + "ta-1.jpg", M + "ta-2.jpg"] },
    { id: "test-urun-b", kategori: "Ev", gorseller: [] },
  ], null, 2);
  const eskiFetch = globalThis.fetch;
  globalThis.fetch = async (adres) => {
    if (String(adres).endsWith("/urunler.json")) {
      return { ok: true, status: 200, text: async () => TABAN };
    }
    throw new Error("beklenmeyen fetch: " + adres);
  };
  try {
    const r1 = await cagir(mockEnv(), "/urun-gorseller", { sorgu: "?id=test-urun-a" });
    ol("G1 tabandaki tam liste doner", r1.kod === 200 &&
       JSON.stringify(r1.govde.gorseller) === JSON.stringify([M + "ta-1.jpg", M + "ta-2.jpg"]),
       JSON.stringify(r1.govde));
    const env2 = mockEnv({ kuyruk: [{ id: 5, urun_id: "test-urun-a", alan: "gorseller",
      deger: JSON.stringify([M + "ta-2.jpg"]), yazan: "panel",
      ts: "2026-08-30T00:00:00Z", hal: "beklemede" }] });
    const r2 = await cagir(env2, "/urun-gorseller", { sorgu: "?id=test-urun-a" });
    ol("G2 bekleyen gorsel ustyazimi yanita yansir",
       r2.kod === 200 && r2.govde.bekleyen && r2.govde.bekleyen.id === 5,
       JSON.stringify(r2.govde));
    const r3 = await cagir(mockEnv(), "/urun-gorseller", { sorgu: "?id=tabanda-olmayan" });
    ol("G3 tabanda olmayan urun -> 404", r3.kod === 404, "kod=" + r3.kod);
    globalThis.fetch = async () => ({ ok: false, status: 503, text: async () => "" });
    const r4 = await cagir(mockEnv(), "/urun-gorseller", { sorgu: "?id=test-urun-a" });
    ol("G4 taban okunamadi -> 502 (sessiz bos liste YOK)", r4.kod === 502 &&
       r4.govde.hata === "taban-okunamadi", JSON.stringify(r4.govde));
    globalThis.fetch = async () => ({ ok: true, status: 200,
      text: async () => "{tek-satir-bozuk-bicim \"id\": \"test-urun-a\"}" });
    const r5 = await cagir(mockEnv(), "/urun-gorseller", { sorgu: "?id=test-urun-a" });
    ol("G5 dilimlenemeyen bicim -> 502/404 fail-loud (200 bos liste DEGIL)",
       (r5.kod === 502 || r5.kod === 404) && !(r5.govde && r5.govde.gorseller),
       "kod=" + r5.kod);
  } finally {
    globalThis.fetch = eskiFetch;
  }
}

// ---------------------------------------------------------------- H. /gorsel-yukle
console.log("H. /gorsel-yukle (icerik-hash; ayni icerik ikinci PUT uretmez; imza)");
{
  const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3, 4]).buffer;
  const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 5, 6]).buffer;
  const medya = r2Mock();
  const env = mockEnv({ medya });
  const r1 = await cagir(env, "/gorsel-yukle", { sorgu: "?id=test-urun-a", govde: JPEG });
  ol("H1 JPEG yuklenir; adres icerik-hash'li panel- anahtari",
     r1.kod === 200 && /^https:\/\/media\.pruvo3d\.com\/urunler\/panel-[0-9a-f]{20}\.jpg$/
       .test(r1.govde.url) && medya.sayac.put === 1,
     JSON.stringify(r1.govde));
  const r2 = await cagir(env, "/gorsel-yukle", { sorgu: "?id=test-urun-a", govde: JPEG });
  ol("H2 AYNI icerik ikinci kez -> ayni adres + PUT SAYISI ARTMADI (ezilmez)",
     r2.kod === 200 && r2.govde.url === r1.govde.url && r2.govde.zaten_vardi === true &&
     medya.sayac.put === 1, "put=" + medya.sayac.put);
  const r3 = await cagir(env, "/gorsel-yukle", { sorgu: "?id=test-urun-a", govde: PNG });
  ol("H3 PNG imzasi .png uzantisi alir", r3.kod === 200 && /\.png$/.test(r3.govde.url),
     JSON.stringify(r3.govde));
  const r4 = await cagir(env, "/gorsel-yukle", { sorgu: "?id=test-urun-a",
    govde: new Uint8Array([0x47, 0x49, 0x46, 0x38]).buffer });
  ol("H4 taninmayan imza (GIF) -> 400", r4.kod === 400, "kod=" + r4.kod);
  const r5 = await cagir(env, "/gorsel-yukle", { sorgu: "?id=test-urun-a",
    govde: new ArrayBuffer(0) });
  ol("H5 bos govde -> 400", r5.kod === 400, "kod=" + r5.kod);
  const r6 = await cagir(mockEnv({ medya: null }), "/gorsel-yukle",
    { sorgu: "?id=test-urun-a", govde: JPEG });
  ol("H6 MEDYA binding yok -> 503 (fail-closed)", r6.kod === 503, "kod=" + r6.kod);
  const r7 = await cagir(env, "/gorsel-yukle", { sorgu: "?id=BOZUK_ID", govde: JPEG });
  ol("H7 bicimsiz id -> 400", r7.kod === 400, "kod=" + r7.kod);
}

// ---------------------------------------------------------------- I. /stl-yukle
console.log("I. /stl-yukle (var olan ada 409; ayirac/uzanti savunmasi)");
{
  const GOVDE = new Uint8Array([1, 2, 3, 4, 5]).buffer;
  const ozel = r2Mock([["stl/test-urun-a/mevcut.stl", 100]]);
  const env = mockEnv({ ozel });
  const r1 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=yeni.stl", govde: GOVDE });
  ol("I1 yeni ad yuklenir (stl/<id>/<dosya>)", r1.kod === 200 &&
     ozel.depo.has("stl/test-urun-a/yeni.stl"), JSON.stringify(r1.govde));
  const putOnce = ozel.sayac.put;
  const r2 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=mevcut.stl", govde: GOVDE });
  ol("I2 VAR OLAN ad -> 409 + PUT hic atilmadi (mevcut anahtar EZILMEZ)",
     r2.kod === 409 && ozel.sayac.put === putOnce &&
     ozel.depo.get("stl/test-urun-a/mevcut.stl").boyut === 100,
     "kod=" + r2.kod + " put=" + ozel.sayac.put);
  for (const [ad, dosya] of [["I3 ust-dizin", "..%2Fkacak.stl"], ["I4 uzanti", "kotu.exe"],
                             ["I5 ayirac", "a%2Fb.stl"]]) {
    const r = await cagir(env, "/stl-yukle",
      { sorgu: "?id=test-urun-a&dosya=" + dosya, govde: GOVDE });
    ol(ad + " -> 400", r.kod === 400, "kod=" + r.kod);
  }
  const r6 = await cagir(mockEnv({ ozel: null }), "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=y.stl", govde: GOVDE });
  ol("I6 OZEL_DOSYA binding yok -> 503", r6.kod === 503, "kod=" + r6.kod);
}

// ---------------------------------------------------------------- J. /stl-cikar
console.log("J. /stl-cikar (arsiv kopyasi teyitsiz orijinal SILINMEZ)");
{
  const ozel = r2Mock([["stl/test-urun-a/parca.stl", 42]]);
  const env = mockEnv({ ozel });
  const r1 = await cagir(env, "/stl-cikar",
    { govde: { id: "test-urun-a", dosya: "parca.stl" } });
  const arsivAnahtar = [...ozel.depo.keys()].find((k) => k.startsWith("arsiv/stl/test-urun-a/"));
  ol("J1 cikarma: orijinal listeden duser, arsiv kopyasi durur",
     r1.kod === 200 && !ozel.depo.has("stl/test-urun-a/parca.stl") &&
     !!arsivAnahtar && /-parca\.stl$/.test(arsivAnahtar), JSON.stringify(r1.govde));
  const r2 = await cagir(env, "/stl-cikar",
    { govde: { id: "test-urun-a", dosya: "olmayan.stl" } });
  ol("J2 listede olmayan dosya -> 404 + silme yok", r2.kod === 404 && ozel.sayac.sil === 1,
     "kod=" + r2.kod);
  // Teyit-dusme kolu: put arsiv kopyasini SESSIZCE bozar (boyut farkli) ->
  // uc 502 doner ve orijinal YERINDE kalir (veri kaybi yolu kapali).
  const bozukOzel = r2Mock([["stl/test-urun-a/parca2.stl", 42]]);
  const gercekPut = bozukOzel.put.bind(bozukOzel);
  bozukOzel.put = async (k, g, s) => { await gercekPut(k, "KISA", s); };
  const env3 = mockEnv({ ozel: bozukOzel });
  const r3 = await cagir(env3, "/stl-cikar",
    { govde: { id: "test-urun-a", dosya: "parca2.stl" } });
  ol("J3 arsiv teyidi dusunce 502 + orijinal SILINMEDI",
     r3.kod === 502 && bozukOzel.depo.has("stl/test-urun-a/parca2.stl") &&
     bozukOzel.sayac.sil === 0, "kod=" + r3.kod + " sil=" + bozukOzel.sayac.sil);
}

// ---------------------------------------------------------------- K. KAYNAK LINK
console.log("K. kaynak link (gizli D1; panel golgeler; https disi RED)");
{
  const env = mockEnv({ urunKaynak: [["test-urun-a", "https://tedarikci.example/u"]] });
  const r1 = await cagir(env, "/urun-kaynak", { sorgu: "?id=test-urun-a" });
  ol("K1 yalniz sync kaydi -> link sync'ten, duzlem=sync",
     r1.kod === 200 && r1.govde.link === "https://tedarikci.example/u" &&
     r1.govde.duzlem === "sync", JSON.stringify(r1.govde));
  const r2 = await cagir(env, "/kaynak-yaz",
    { govde: { id: "test-urun-a", link: "https://panel.example/yeni" } });
  const r2b = await cagir(env, "/urun-kaynak", { sorgu: "?id=test-urun-a" });
  ol("K2 panel yazimi sync'i GOLGELER (panel_kaynak'a, urun_kaynak'a DEGIL)",
     r2.kod === 200 && r2b.govde.link === "https://panel.example/yeni" &&
     r2b.govde.duzlem === "panel" &&
     env.urunKaynak.get("test-urun-a") === "https://tedarikci.example/u",
     JSON.stringify(r2b.govde));
  const r3 = await cagir(env, "/kaynak-yaz", { govde: { id: "test-urun-a", link: "" } });
  const r3b = await cagir(env, "/urun-kaynak", { sorgu: "?id=test-urun-a" });
  ol("K3 link='' = cikarildi golgesi (sync linki de listeden duser)",
     r3.kod === 200 && r3.govde.cikarildi === true && r3b.govde.link === "" &&
     r3b.govde.cikarildi === true, JSON.stringify(r3b.govde));
  const RED = [["K4 http (sifresiz)", "http://x.example/a"],
               ["K5 javascript sema", "javascript:alert(1)"],
               ["K6 tirnakli", "https://x.example/\"a"],
               ["K7 bosluklu", "https://x.example/a b"]];
  for (const [ad, link] of RED) {
    const e = mockEnv();
    const r = await cagir(e, "/kaynak-yaz", { govde: { id: "test-urun-a", link } });
    ol(ad + " -> 400 + yazim yok", r.kod === 400 && e.panelKaynak.size === 0,
       "kod=" + r.kod);
  }
  const r8 = await cagir(mockEnv(), "/kaynak-yaz",
    { govde: { id: "boyle-urun-yok", link: "https://x.example/a" } });
  ol("K8 katalogda olmayan urun -> 404", r8.kod === 404, "kod=" + r8.kod);
  const r9 = await cagir(mockEnv({ kaynakTabloYok: true }), "/kaynak-yaz",
    { govde: { id: "test-urun-a", link: "https://x.example/a" } });
  ol("K9 panel_kaynak tablosu yok -> YAZMA 503 (fail-closed)", r9.kod === 503,
     "kod=" + r9.kod);
  const r10 = await cagir(mockEnv({ kaynakTabloYok: true }), "/urun-kaynak",
    { sorgu: "?id=test-urun-a" });
  ol("K10 tablo yokken OKUMA 200 link bos (merdiven urun_kaynak'a duser)",
     r10.kod === 200 && r10.govde.link === "", JSON.stringify(r10.govde));
}

// ---------------------------------------------------------------- L. SAYFA SCRIPT'I
console.log("L. panel sayfa script'i DERLENIR (sablon kacis hatasi tum paneli kirar)");
{
  const y = await yonet(istek(undefined, { "X-Yonet-Anahtar": YONET_ANAHTAR }, "GET"),
    mockEnv(), new URL("https://ornek-site.test/api/shop/yonet/"), ctxYap(), "/", undefined);
  const html = await y.text();
  const m = html.match(/<script>([\s\S]*)<\/script>/);
  let derlendi = false, hata = "";
  try { new Function(m ? m[1] : "kirik("); derlendi = true; } catch (e) { hata = String(e); }
  ol("L1 sayfa 200 + <script> blogu var", y.status === 200 && !!m);
  ol("L2 script SOZDIZIMSEL derlenir (new Function)", derlendi, hata);
  const KABLOLAR = ["urunKartAc", "gorselKaydetUI", "gorselYukleUI", "gorselCikarUI",
                    "stlYukleUI", "stlCikarUI", "kaynakKaydetUI", "kaynakCikarUI"];
  ol("L3 T2 ekran kablolari sayfada (8 fonksiyon)",
     m && KABLOLAR.every((f) => m[1].indexOf("function " + f) >= 0),
     m ? KABLOLAR.filter((f) => m[1].indexOf("function " + f) < 0).join(",") : "script yok");
}

console.log("");
console.log("TOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
process.exit(kalan === 0 ? 0 : 1);
