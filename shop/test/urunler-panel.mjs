#!/usr/bin/env node
/**
 * PRUVO shop — YONETIM PANELI "URUNLER" SEKMESI (T1 + T2) kabul testi.
 *
 *   node shop/test/urunler-panel.mjs
 *
 * NE OLCER (wrangler/ag/D1 YOK — wa-siparis.mjs deseni, env.KATALOG mock):
 *   A. YETKI: 11 uc (T1: 4 + T2: 6 + sil: 1) yonetim anahtarinin ARKASINDA;
 *      EGE_ANAHTAR HICBIRINI acamaz (en az yetki), secret'siz kurulumda 404,
 *      cerez de acar.
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
 *   M. TEKIL SILME (/urun-sil, Okan emri 2 Eyl): cift onay (onay=id birebir) +
 *      zorunlu gerekce; kuyruga alan='sil' yazilir; /urunler-ustyazim alan='sil'
 *      KABUL ETMEZ; STL parcalari kuyruktan ONCE arsiv-teyitli tasinir (teyit
 *      dusmezse silme kuyruklanmaz); RED'lerde kuyruga sifir yazim.
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek urun/tedarikci/musteri verisi yazilmaz.
 * Tabana isleme bu dosyanin MENZILI DISIDIR — o eksen tools/panel-uygulayici.py
 * --kendini-test bataryasinda olculur (51 vaka + 5 mutant); iki test ayni iddiayi
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
  // secenek.yonet: I-M mutant bataryasi ayni cagri yolunu MUTANT modulle kosar.
  const y = await (secenek.yonet || yonet)(istek(secenek.govde, secenek.baslik ||
    { "X-Yonet-Anahtar": YONET_ANAHTAR }, secenek.method || (secenek.govde ? "POST" : "GET")),
    env, u, c, altYol, undefined);
  let govde = null;
  try { govde = JSON.parse(await y.text()); } catch (e) { govde = null; }
  return { kod: y.status, govde, ctx: c };
}

// ---------------------------------------------------------------- A. YETKI
console.log("A. YETKI (T1+T2+sil 11 uc yonetim anahtari arkasinda; EGE acamaz)");
{
  const UCLAR = [["/urunler", "GET", undefined],
                 ["/urunler-kuyruk", "GET", undefined],
                 ["/urunler-ustyazim", "POST", { urun_id: "test-urun-a", alan: "fiyat", deger: "500 TL" }],
                 ["/urunler-ustyazim-sil", "POST", { id: 1 }],
                 ["/urun-sil", "POST", { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "x" }],
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

  // --- Okan kalemi (2 Eyl): uzanti harf-duyarsiz + Turkce->ASCII normalize; GUVENLIK AYNEN
  const r7 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=X.STL", govde: GOVDE });
  ol("I7 buyuk harf uzanti X.STL gecer; R2 anahtari kucuk uzantili (X.stl), X.STL YOK",
     r7.kod === 200 && r7.govde.dosya === "X.stl" && ozel.depo.has("stl/test-urun-a/X.stl") &&
     !ozel.depo.has("stl/test-urun-a/X.STL"), JSON.stringify(r7.govde));
  const r8 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent("kılavuz-ı-ğ.stl"), govde: GOVDE });
  ol("I8 Turkce ad ASCII'ye normalize (kılavuz-ı-ğ.stl -> kilavuz-i-g.stl), tum anahtarlar ASCII",
     r8.kod === 200 && r8.govde.dosya === "kilavuz-i-g.stl" &&
     ozel.depo.has("stl/test-urun-a/kilavuz-i-g.stl") &&
     [...ozel.depo.keys()].every((k) => /^[ -~]*$/.test(k)), JSON.stringify(r8.govde));
  const r9 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent("crf-zincir-kılavuz-ara.STL"), govde: GOVDE });
  ol("I9 Okan'in vakasi crf-zincir-kılavuz-ara.STL -> crf-zincir-kilavuz-ara.stl (200)",
     r9.kod === 200 && r9.govde.dosya === "crf-zincir-kilavuz-ara.stl" &&
     ozel.depo.has("stl/test-urun-a/crf-zincir-kilavuz-ara.stl"), JSON.stringify(r9.govde));
  // macOS NFD girdisi: ğ = g+U+0306, ş = s+U+0327, İ = I+U+0307 (birlesik isaret) + bosluk + buyuk Turkce
  const NFD = "g" + String.fromCharCode(0x306) + "s" + String.fromCharCode(0x327) + " I" +
    String.fromCharCode(0x307) + "ş  ÇÖÜ.3MF";
  const r10 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent(NFD), govde: GOVDE });
  ol("I10 NFD (macOS) + bosluk + buyuk Turkce + .3MF -> gs-Is-COU.3mf",
     r10.kod === 200 && r10.govde.dosya === "gs-Is-COU.3mf" &&
     ozel.depo.has("stl/test-urun-a/gs-Is-COU.3mf"), JSON.stringify(r10.govde));
  const putIki = ozel.sayac.put;
  const r11 = await cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent("kılavuz-i-ğ.STL"), govde: GOVDE });
  ol("I11 normalize SONRASI cakisma (kılavuz-i-ğ.STL -> kilavuz-i-g.stl VAR) -> 409, PUT yok",
     r11.kod === 409 && ozel.sayac.put === putIki, "kod=" + r11.kod + " put=" + ozel.sayac.put);
  // GUVENLIK AYNEN — her RED 400 + hangi kuralin vurdugu (kural) + tek bayt yazilmaz
  for (const [ad, dosya, kural] of [
      ["I12 ust-dizin ..%2Fx.stl", "..%2Fx.stl", "ust-dizin"],
      ["I13 ayirac a%2Fb.stl", "a%2Fb.stl", "ayirac"],
      ["I14 ters ayirac a%5Cb.stl", "a%5Cb.stl", "ayirac"],
      ["I15 uzanti x.exe", "x.exe", "uzanti"],
      ["I16 uzantisiz Turkce ad", encodeURIComponent("kılavuz"), "uzanti"],
      ["I17 bos ad .stl", ".stl", "bos-ad"],
      ["I18 bos dosya adi", "", "bos-ad"],
      ["I19 kontrol karakteri (BEL)", encodeURIComponent("a" + String.fromCharCode(7) + "b.stl"),
       "kontrol-karakteri"],
      ["I20 yalniz sembol (euro).stl -> bos ad", "%E2%82%AC.stl", "bos-ad"]]) {
    const r = await cagir(env, "/stl-yukle",
      { sorgu: "?id=test-urun-a&dosya=" + dosya, govde: GOVDE });
    ol(ad + " -> 400 kural=" + kural,
       r.kod === 400 && !!r.govde && r.govde.kural === kural && /gecersiz dosya adi/.test(r.govde.hata),
       "kod=" + r.kod + " " + JSON.stringify(r.govde));
  }
  ol("I21 RED vakalari R2'ye TEK anahtar yazmadi", ozel.sayac.put === putIki, "put=" + ozel.sayac.put);
}

// ---------------------------------------------------------------- I-M. MUTANT
console.log("I-M. /stl-yukle mutantlari (normalize / ayirac / uzanti kolu — capa yoksa KIRMIZI)");
{
  const fs = await import("node:fs");
  const os = await import("node:os");
  const { pathToFileURL } = await import("node:url");
  const GOVDE = new Uint8Array([1, 2, 3]).buffer;
  const SRC = path.join(path.dirname(new URL(import.meta.url).pathname), "..", "src");
  const KAYNAK = fs.readFileSync(path.join(SRC, "yonet.js"), "utf8");
  // Mutant, shop/src'nin gecici AYNASINDA kosar: kardes moduller symlink (gercek yola
  // cozulur), yalniz yonet.js mutant kopyadir. Depo dosyasina YAZILMAZ; dizin sonda SILINIR.
  async function mutantYukle(etiket, kaynak) {
    const kok = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-stl-mutant-"));
    const src = path.join(kok, "shop", "src");
    fs.mkdirSync(src, { recursive: true });
    for (const ad of fs.readdirSync(SRC)) {
      if (ad !== "yonet.js") { fs.symlinkSync(path.join(SRC, ad), path.join(src, ad)); }
    }
    fs.writeFileSync(path.join(src, "yonet.js"), kaynak);
    try {
      const m = await import(pathToFileURL(path.join(src, "yonet.js")).href + "?m=" + etiket);
      return { yonet: m.yonet, driveKaynaklari: m.driveKaynaklari, kok };
    } catch (e) { return { hata: String(e), kok }; }
  }
  const TR = encodeURIComponent("kılavuz-ı-ğ.stl");
  const capaSil = (kaynak, capa, yeni) =>
    (kaynak.split(capa).length === 2) ? kaynak.replace(capa, yeni) : null;
  const MUTANTLAR = [
    { ad: "KONTROL (mutasyonsuz ayna)", uygula: (k) => k, vaka: [TR, "a%2Fb.stl", "X.STL"],
      beklenen: "ayna canli: Turkce 200 kilavuz-i-g.stl · ayirac 400 · X.STL 200 X.stl",
      olcu: (r) => r[0].kod === 200 && r[0].govde.dosya === "kilavuz-i-g.stl" &&
        r[1].kod === 400 && r[1].govde.kural === "ayirac" &&
        r[2].kod === 200 && r[2].govde.dosya === "X.stl" },
    { ad: "IM1 normalize kolu (Turkce->ASCII) KALDIRILDI", vaka: [TR],
      uygula: (k) => capaSil(k, 'TR_ASCII[c] || "-"', "c"),
      beklenen: "Turkce vaka artik 200/kilavuz-i-g.stl DEGIL -> I8 KIRMIZI yakalar",
      olcu: (r) => !(r[0].kod === 200 && r[0].govde.dosya === "kilavuz-i-g.stl") },
    { ad: "IM2 ayirac/ust-dizin ON-KONTROLU KALDIRILDI (2 CAPA:ayirac satiri)",
      vaka: ["a%2Fb.stl", "..%2Fx.stl"],
      uygula: (k) => (k.match(/^.*CAPA:ayirac.*\n/gm) || []).length === 2
        ? k.replace(/^.*CAPA:ayirac.*\n/gm, "") : null,
      beklenen: "RED vakalari YESILE DONMEZ (son kapi 400 tutar) + kural atfi degisti -> I12/I13 KIRMIZI",
      olcu: (r) => r[0].kod === 400 && r[0].govde.kural !== "ayirac" &&
        r[1].kod === 400 && r[1].govde.kural !== "ust-dizin" },
    { ad: "IM3 uzanti kucuk-harf kolu KALDIRILDI", vaka: ["X.STL"],
      uygula: (k) => capaSil(k, "uzM[0].toLowerCase()", "uzM[0]"),
      beklenen: "X.STL anahtari artik X.stl DEGIL -> I7 KIRMIZI yakalar",
      olcu: (r) => !(r[0].kod === 200 && r[0].govde.dosya === "X.stl") },
    // BaBa ek kabulu (3 Eyl): NFC adimi + R3 (uretim notu) kanonik etiketi hedef-kol mutantlari
    { ad: "IM4 NFC adimi KALDIRILDI (macOS NFD ekseni)",
      vaka: [encodeURIComponent("bag" + String.fromCharCode(0x306) + "lanti.stl")],
      uygula: (k) => capaSil(k, 'ham.normalize("NFC")', "ham"),
      beklenen: "NFD vaka artik baglanti.stl DEGIL -> I-K D1 KIRMIZI yakalar",
      olcu: (r) => !(r[0].kod === 200 && r[0].govde.dosya === "baglanti.stl") },
    { ad: "IM5 R3 URETIM_DOSYA_RX salt-ASCII sinifa GERI DONDU", vaka: [],
      not: "KANONIK crf-zincir-kılavuz-ara.stl Drive file Id: abcdefghijklmnopqrstuv",
      uygula: (k) => capaSil(k, "/([\\p{L}\\p{N}][\\p{L}\\p{N}\\p{M}._-]*\\.(?:stl|3mf))/giu",
                             "/([A-Za-z0-9][A-Za-z0-9._-]*\\.(?:stl|3mf))/gi"),
      beklenen: "Turkce ad KIRPILIR (lavuz-ara.stl) -> I-K C1/C2 KIRMIZI yakalar",
      olcu: (r, o, n) => !(n && n.length === 1 && n[0].dosya === "crf-zincir-kilavuz-ara.stl") },
    { ad: "IM6 R3 kanonik etiket KALDIRILDI (ham ad doner)", vaka: [],
      not: "KANONIK crf-zincir-kılavuz-ara.stl Drive file Id: abcdefghijklmnopqrstuv",
      uygula: (k) => capaSil(k, "return n.hata ? ham : n.ad;", "return ham;"),
      beklenen: "etiket ham Turkce kalir -> I-K C1 KIRMIZI yakalar",
      olcu: (r, o, n) => !(n && n.length === 1 && n[0].dosya === "crf-zincir-kilavuz-ara.stl") },
  ];
  for (const m of MUTANTLAR) {
    const kaynak = m.uygula(KAYNAK);
    if (kaynak === null) { ol(m.ad + " — CAPA YOK/COK, mutant uygulanamadi", false); continue; }
    if (!m.ad.startsWith("KONTROL") && kaynak === KAYNAK) {
      ol(m.ad + " — mutant kaynagi degistirmedi", false); continue;
    }
    const mut = await mutantYukle(m.ad.slice(0, 3), kaynak);
    if (mut.hata) {
      fs.rmSync(mut.kok, { recursive: true, force: true });
      ol(m.ad + " — mutant yuklenemedi", false, mut.hata); continue;
    }
    const ozel = r2Mock();
    const env = mockEnv({ ozel });
    const sonuc = [];
    for (const v of m.vaka) {
      sonuc.push(await cagir(env, "/stl-yukle",
        { sorgu: "?id=test-urun-a&dosya=" + v, govde: GOVDE, yonet: mut.yonet }));
    }
    const notCikti = m.not ? mut.driveKaynaklari(m.not) : null;
    fs.rmSync(mut.kok, { recursive: true, force: true });
    ol(m.ad + " -> " + m.beklenen, m.olcu(sonuc, ozel, notCikti),
       sonuc.map((r) => r.kod + " " + JSON.stringify(r.govde)).join(" | ") +
       (notCikti ? " not=" + JSON.stringify(notCikti) : ""));
    ol(m.ad + " gecici ayna SILINDI", !fs.existsSync(mut.kok), mut.kok);
  }
}

// ---------------------------------------------------------------- I-K. KANONIK AD, UC OKUYUCU
console.log("I-K. kanonik dosya adi UC OKUYUCUDA (yukleme / uretim-notu R3 / indirme+cikarma) — " +
  "Tamirci bataryasindan tasindi (678fdbfd), ASCII-kanonik tasarimla");
{
  const fsK = await import("node:fs");
  const { driveKaynaklari } = await import("../src/yonet.js");
  const KAYNAK_K = fsK.readFileSync(
    path.join(path.dirname(new URL(import.meta.url).pathname), "..", "src", "yonet.js"), "utf8");
  const GOVDE = new Uint8Array([9, 9, 9]).buffer;
  // Turkce harfler BILEREK kod noktasiyla: NFC/NFD ayrimi gozle gorunsun, kodlama bozulsa da vaka kalsin.
  const I_NOKTASIZ = "ı", G_NFC = "ğ", G_NFD = "g" + String.fromCharCode(0x306);
  const S_CED = "ş", S_BUYUK = "Ş";
  const yukle = (env, ad) => cagir(env, "/stl-yukle",
    { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent(ad), govde: GOVDE });
  const ID = "abcdefghijklmnopqrstuv";   // uydurma, >=16 base64url
  // A) POZITIF — Turkce/Unicode ad GECER, anahtar kanonik ASCII
  {
    const ozel = r2Mock(); const env = mockEnv({ ozel });
    const A = [
      ["A1 Okan vakasi", "crf-zincir-k" + I_NOKTASIZ + "lavuz-ara.STL", "crf-zincir-kilavuz-ara.stl"],
      ["A2 NFC yumusak g + noktasiz i", "ba" + G_NFC + "lant" + I_NOKTASIZ + "-braketi.stl", "baglanti-braketi.stl"],
      ["A3 bosluk + buyuk Turkce", S_BUYUK + "aft K" + I_NOKTASIZ + "lavuzu 2.3mf", "Saft-Kilavuzu-2.3mf"],
      ["A4 alt cizgi + cedilla", "di" + S_CED + "li_alt_cizgi.stl", "disli_alt_cizgi.stl"],
      ["A5 REGRESYON duz ASCII", "pruvo-braket-v2.stl", "pruvo-braket-v2.stl"],
      ["A6 REGRESYON .3mf", "kapak.3mf", "kapak.3mf"],
      ["A7 buyuk uzanti govde korunur", "KAPAK.STL", "KAPAK.stl"],
      ["A8 tavan sinirinda Turkce (181)", "a".repeat(173) + I_NOKTASIZ.repeat(4) + ".stl",
       "a".repeat(173) + "iiii.stl"],
      ["A9 bastaki tire slug'da duser", "-basta-tire.stl", "basta-tire.stl"],
      ["A10 bastaki bosluk slug'da duser", " bosluk.stl", "bosluk.stl"],
      ["A11 bastaki yalniz birlesik isaret duser", String.fromCharCode(0x306) + "baslangic.stl", "baslangic.stl"],
    ];
    for (const [ad, ham, kanonik] of A) {
      const r = await yukle(env, ham);
      ol("I-K " + ad + " -> 200 " + kanonik,
         r.kod === 200 && r.govde.dosya === kanonik && ozel.depo.has("stl/test-urun-a/" + kanonik),
         r.kod + " " + JSON.stringify(r.govde));
    }
    ol("I-K A12 tum anahtarlar yazdirilabilir ASCII",
       [...ozel.depo.keys()].every((k) => /^[ -~]*$/.test(k)));
  }
  // B) NEGATIF — savunma DARALMADI (alfabe kanonikle genisledi, kapi genislemedi), kural adiyla
  {
    const ozel = r2Mock(); const env = mockEnv({ ozel });
    const B = [
      ["B1 ust-dizin", "../gizli.stl", "ust-dizin"],
      ["B2 ayirac", "alt/dizin.stl", "ayirac"],
      ["B3 ters ayirac", "alt\\dizin.stl", "ayirac"],
      ["B4 Turkce harfli traversal", "k" + I_NOKTASIZ + "d/../../gizli.stl", "ust-dizin"],
      ["B5 bastaki nokta", ".gizli.stl", "karakter"],
      ["B8 uzanti disi (.txt)", "dosya.txt", "uzanti"],
      ["B9 uzanti sonda degil (.stl.exe)", "dosya.stl.exe", "uzanti"],
      ["B10 cift tirnak (Content-Disposition ekseni)", "dosya\"tirnak.stl", "karakter"],
      ["B11 satir sonu", "dosya\nsatir.stl", "kontrol-karakteri"],
      ["B12 NUL", "dosya" + String.fromCharCode(0) + "bos.stl", "kontrol-karakteri"],
      ["B13 yuzde (kodlanmis traversal, ham %)", "dosya%2e%2e.stl", "karakter"],
      ["B14 iki nokta", "dosya:kolon.stl", "karakter"],
      ["B15 soru isareti", "dosya?sorgu.stl", "karakter"],
      ["B16 bos ad", "", "bos-ad"],
      ["B17 tavan asan ad (200+)", "a".repeat(200) + ".stl", "uzunluk"],
      ["B19 suslu parantez", "dosya{suslu}.stl", "karakter"],
      ["B20 kontrol karakteri (BEL)", "dosya" + String.fromCharCode(7) + "zil.stl", "kontrol-karakteri"],
    ];
    for (const [ad, ham, kural] of B) {
      const r = await yukle(env, ham);
      ol("I-K " + ad + " -> 400 kural=" + kural,
         r.kod === 400 && !!r.govde && r.govde.kural === kural, r.kod + " " + JSON.stringify(r.govde));
    }
    ol("I-K B21 RED'lerde R2'ye sifir PUT", ozel.sayac.put === 0, "put=" + ozel.sayac.put);
  }
  // C) R3 — uretim notu ayristirici Turkce adi KIRPMAZ, etiket KANONIK (yanlis dosya = pahali hata)
  {
    const ad = "crf-zincir-k" + I_NOKTASIZ + "lavuz-ara.stl";
    const c1 = driveKaynaklari("KANONIK " + ad + " Drive file Id: " + ID);
    ol("I-K C1 Turkce ad TAM ve KANONIK cikar (crf-zincir-kilavuz-ara.stl)",
       c1.length === 1 && c1[0].dosya === "crf-zincir-kilavuz-ara.stl", JSON.stringify(c1));
    ol("I-K C2 kirpma izi YOK (lavuz-ara.stl degil)", !c1.some((c) => c.dosya === "lavuz-ara.stl"));
    const c3 = driveKaynaklari("YEDEK pruvo-braket-v2.stl Drive file Id: " + ID);
    ol("I-K C3 REGRESYON ASCII ad aynen", c3.length === 1 && c3[0].dosya === "pruvo-braket-v2.stl",
       JSON.stringify(c3));
    ol("I-K C4 REGRESYON eslesme yoksa bos liste",
       driveKaynaklari("notta hic uretim dosyasi yok, yalniz metin").length === 0);
    const c5 = driveKaynaklari("KANONIK ba" + G_NFD + "lant" + I_NOKTASIZ + ".stl Drive file Id: " + ID);
    ol("I-K C5 NFD notta (macOS yapistirma) ad TAM + kanonik baglanti.stl",
       c5.length === 1 && c5[0].dosya === "baglanti.stl", JSON.stringify(c5));
    const c6 = driveKaynaklari("KANONIK KAPAK.STL Drive file Id: " + ID);
    ol("I-K C6 buyuk uzanti etikette kucuk (KAPAK.stl) — R2 anahtariyla AYNI ad",
       c6.length === 1 && c6[0].dosya === "KAPAK.stl", JSON.stringify(c6));
  }
  // D) NFC EKSENI — ayni ad TEK anahtar; indirme/cikarma da ayni kanonik fonksiyonla cozer
  {
    const ozel = r2Mock(); const env = mockEnv({ ozel });
    const nfc = "ba" + G_NFC + "lant" + I_NOKTASIZ + ".stl";
    const nfd = "ba" + G_NFD + "lant" + I_NOKTASIZ + ".stl";
    ol("I-K D0 fikstur gercekten NFD (ham dizgeler FARKLI)", nfc !== nfd);
    const d1 = await yukle(env, nfd);
    ol("I-K D1 NFD ad KABUL + kanonik baglanti.stl", d1.kod === 200 && d1.govde.dosya === "baglanti.stl",
       JSON.stringify(d1.govde));
    const d2 = await yukle(env, nfc);
    ol("I-K D2 NFC ayni ad -> AYNI anahtar -> 409 (tek anahtar, HEAD 1)",
       d2.kod === 409 && ozel.depo.size === 1, d2.kod + " depo=" + ozel.depo.size);
    const g1 = await cagir(env, "/stl", { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent(nfd) });
    ol("I-K D3 GET /stl NFD adla kanonik anahtari BULUR (200)", g1.kod === 200, "kod=" + g1.kod);
    const g2 = await cagir(env, "/stl", { sorgu: "?id=test-urun-a&dosya=BAGLANTI.STL" });
    ol("I-K D4 GET /stl farkli govde harfi (BAGLANTI.stl YOK) -> 404", g2.kod === 404, "kod=" + g2.kod);
    const g3 = await cagir(env, "/stl", { sorgu: "?id=test-urun-a&dosya=..%2Fbaglanti.stl" });
    ol("I-K D5 GET /stl ust-dizin -> 404 (savunma 1)", g3.kod === 404, "kod=" + g3.kod);
    ozel.depo.set("stl/test-urun-a/eski parca.stl", { boyut: 3, govde: "xxx" });
    const g4 = await cagir(env, "/stl", { sorgu: "?id=test-urun-a&dosya=" + encodeURIComponent("eski parca.stl") });
    ol("I-K D6 ESKI bosluklu anahtar HAM adla hala iner (geriye uyum)", g4.kod === 200, "kod=" + g4.kod);
    const c1 = await cagir(env, "/stl-cikar", { govde: { id: "test-urun-a", dosya: nfc } });
    ol("I-K D7 /stl-cikar NFC adla kanonik anahtari arsive tasir",
       c1.kod === 200 && !ozel.depo.has("stl/test-urun-a/baglanti.stl") &&
       /-baglanti\.stl$/.test(c1.govde.arsiv), c1.kod + " " + JSON.stringify(c1.govde));
  }
  // E) OKUYUCU ENVANTERI (kaynak duzeyi) — uc okuyucu AYNI kanonik fonksiyonu cagiriyor mu?
  {
    const girisler = [
      ["stlYukle", 'const norm = stlDosyaAdiNormalize(url.searchParams.get("dosya") || "");'],
      ["driveKaynaklari (R3)", "ad: uretimDosyaEtiketi(md[1])"],
      ["stlIndir", "const adlar = stlDosyaAdiAdaylari(dosyaParam);"],
      ["stlCikar", "const adlar = stlDosyaAdiAdaylari(dosya);"],
      ["anahtar dogrulanan/kanonik addan", 'const anahtar = "stl/" + uid + "/" + dosya;'],
    ];
    for (const [ad, capa] of girisler) {
      ol("I-K E:" + ad + " kanonik fonksiyonu cagiriyor", KAYNAK_K.includes(capa), "capa YOK: " + capa);
    }
  }
  // F) SINIFIN KENDISI — son kapi ASCII KALDI (alfabe kanonikle genisledi, KAPI genislemedi)
  {
    ol("I-K F1 STL_DOSYA_ADI_RX ASCII sinif, degismedi",
       KAYNAK_K.includes("const STL_DOSYA_ADI_RX = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,180}$/;"));
    ol("I-K F2 URETIM_DOSYA_RX Unicode (u bayragi) — not ayristirici kirpmaz",
       /const URETIM_DOSYA_RX = \/.*\/giu;/.test(KAYNAK_K));
    ol("I-K F3 kanonik blok DRIVE_TABAN altinda (uretim-kaynak.mjs vm dilimi tasir)",
       KAYNAK_K.indexOf("function stlDosyaAdiNormalize") > KAYNAK_K.indexOf("const DRIVE_TABAN =") &&
       KAYNAK_K.indexOf("function stlDosyaAdiNormalize") < KAYNAK_K.indexOf("// ---- anahtar ---"));
  }
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

// ---------------------------------------------------------------- M. TEKIL SILME
console.log("M. /urun-sil (cift onay + gerekce; alan='sil' kuyrugu; STL arsiv-teyitli)");
{
  const env = mockEnv();
  const r1 = await cagir(env, "/urun-sil",
    { govde: { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "telif riski" } });
  ol("M1 gecerli sil -> 200 + kuyrukta TEK satir alan='sil' deger=gerekce",
     r1.kod === 200 && r1.govde.hal === "beklemede" && env.kuyruk.length === 1 &&
     env.kuyruk[0].alan === "sil" && env.kuyruk[0].deger === "telif riski" &&
     env.kuyruk[0].hal === "beklemede", JSON.stringify(env.kuyruk));
  const r2 = await cagir(env, "/urun-sil",
    { govde: { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "yeni gerekce" } });
  ol("M2 bekleyen sil yeniden -> yenisi eskisinin YERINE (satir sayisi 1 kalir)",
     r2.kod === 200 && env.kuyruk.length === 1 && env.kuyruk[0].deger === "yeni gerekce",
     JSON.stringify(env.kuyruk));
}
{
  const RED = [
    ["M3 onay eksik", { urun_id: "test-urun-a", gerekce: "x" }, 400],
    ["M4 onay id ile eslesmiyor (cift onayin sunucu ayagi)",
     { urun_id: "test-urun-a", onay: "test-urun-b", gerekce: "x" }, 400],
    ["M5 gerekce bos", { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "  " }, 400],
    ["M6 gerekce tavan asimi (201)",
     { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "g".repeat(201) }, 400],
    ["M7 gerekce kontrol karakteri",
     { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "a\u0007b" }, 400],
    ["M8 bicimsiz id", { urun_id: "Kotu_Id", onay: "Kotu_Id", gerekce: "x" }, 400],
    ["M9 olmayan urun", { urun_id: "boyle-urun-yok", onay: "boyle-urun-yok", gerekce: "x" }, 404],
    ["M10 bozuk govde", "BOZUK", 400],
  ];
  for (const [ad, govde, kod] of RED) {
    const env = mockEnv();
    const r = await cagir(env, "/urun-sil", { govde });
    ol(ad + " -> " + kod + " + kuyruga sifir yazim",
       r.kod === kod && env.kuyruk.length === 0,
       "kod=" + r.kod + " kuyruk=" + env.kuyruk.length);
  }
  // Silme yalniz cift-onayli uctan: /urunler-ustyazim alan='sil' KABUL ETMEZ.
  const e2 = mockEnv();
  const r = await cagir(e2, "/urunler-ustyazim",
    { govde: { urun_id: "test-urun-a", alan: "sil", deger: "gerekce" } });
  ol("M11 /urunler-ustyazim alan='sil' -> 400 (silme yalniz /urun-sil'den)",
     r.kod === 400 && e2.kuyruk.length === 0, "kod=" + r.kod);
}
{
  // STL parcalari kuyruk yazimindan ONCE arsiv-teyitli tasinir (stlCikar deseni).
  const ozel = r2Mock([["stl/test-urun-a/parca.stl", 42], ["stl/test-urun-a/kapak.3mf", 7]]);
  const env = mockEnv({ ozel });
  const r1 = await cagir(env, "/urun-sil",
    { govde: { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "kobay" } });
  const arsivler = [...ozel.depo.keys()].filter((k) => k.startsWith("arsiv/stl/test-urun-a/"));
  ol("M12 STL parcalari arsive tasindi + kuyruk yazildi",
     r1.kod === 200 && r1.govde.stl_arsivlenen === 2 && arsivler.length === 2 &&
     !ozel.depo.has("stl/test-urun-a/parca.stl") &&
     !ozel.depo.has("stl/test-urun-a/kapak.3mf") && env.kuyruk.length === 1,
     JSON.stringify({ kod: r1.kod, govde: r1.govde, arsivler }));
  // Teyit-dusme kolu (J3 deseni): arsiv kopyasi bozuk -> 502 + kuyruga SIFIR yazim
  // + orijinal YERINDE.
  const bozuk = r2Mock([["stl/test-urun-b/p.stl", 42]]);
  const gercekPut = bozuk.put.bind(bozuk);
  bozuk.put = async (k, g, s) => { await gercekPut(k, "KISA", s); };
  const env2 = mockEnv({ ozel: bozuk });
  const r2 = await cagir(env2, "/urun-sil",
    { govde: { urun_id: "test-urun-b", onay: "test-urun-b", gerekce: "kobay" } });
  ol("M13 arsiv teyidi dusunce 502 + kuyruga sifir yazim + orijinal yerinde",
     r2.kod === 502 && env2.kuyruk.length === 0 &&
     bozuk.depo.has("stl/test-urun-b/p.stl") && bozuk.sayac.sil === 0,
     "kod=" + r2.kod + " kuyruk=" + env2.kuyruk.length);
  const env3 = mockEnv({ ozel: null });
  const r3 = await cagir(env3, "/urun-sil",
    { govde: { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "kobay" } });
  ol("M14 OZEL_DOSYA binding yok -> 503 (STL varligi OLCULEMEZ, fail-closed)",
     r3.kod === 503 && env3.kuyruk.length === 0, "kod=" + r3.kod);
  const env4 = mockEnv({ tabloYok: true });
  const r4 = await cagir(env4, "/urun-sil",
    { govde: { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "kobay" } });
  ol("M15 kuyruk tablosu yok -> YAZMA 503 (fail-closed)", r4.kod === 503, "kod=" + r4.kod);
  // Tetik: sil de uygulayiciyi durtukler (E2 deseni; ayni uygulayiciTetikle kolu).
  const eskiFetch = globalThis.fetch;
  const cagrilar = [];
  globalThis.fetch = (adres, sec) => { cagrilar.push(adres); return Promise.resolve({ ok: true }); };
  try {
    const env5 = mockEnv({ ghToken: "t".repeat(20) });
    const r5 = await cagir(env5, "/urun-sil",
      { govde: { urun_id: "test-urun-a", onay: "test-urun-a", gerekce: "kobay" } });
    await Promise.all(r5.ctx.isler);
    ol("M16 sil de repository_dispatch tetigini durtukler",
       r5.kod === 200 && cagrilar.length === 1, "fetch=" + cagrilar.length);
  } finally { globalThis.fetch = eskiFetch; }
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
                    "stlYukleUI", "stlCikarUI", "kaynakKaydetUI", "kaynakCikarUI",
                    "urunSil"];
  ol("L3 T2+sil ekran kablolari sayfada (9 fonksiyon)",
     m && KABLOLAR.every((f) => m[1].indexOf("function " + f) >= 0),
     m ? KABLOLAR.filter((f) => m[1].indexOf("function " + f) < 0).join(",") : "script yok");
}

// ------------------------------------------------- N. KUYRUK IKI YUZEY (katlama)
// Okan emri 6 Eyl: BEKLEYEN disarida (is orada), BITEN katlanir <details>'e,
// VARSAYILAN KAPALI, yalniz son 12. Bu blok sayfa script'ini SAHTE DOM + SAHTE
// fetch ile GERCEKTEN kosturur — "script derleniyor" (L2) bunu OLCMEZ.
console.log("N. kuyruk iki yuzey: bekleyen DISARIDA, biten KAPALI <details> (son 12)");
{
  const y = await yonet(istek(undefined, { "X-Yonet-Anahtar": YONET_ANAHTAR }, "GET"),
    mockEnv(), new URL("https://ornek-site.test/api/shop/yonet/"), ctxYap(), "/", undefined);
  const kod = (await y.text()).match(/<script>([\s\S]*)<\/script>/)[1];

  const domYap = () => {
    const kutular = new Map();
    return {
      kutular,
      getElementById(id) {
        if (!kutular.has(id)) {
          kutular.set(id, { innerHTML: "", value: "", hidden: false, className: "",
                            style: {}, files: [], querySelectorAll: () => [],
                            setAttribute() {}, getAttribute() { return null; } });
        }
        return kutular.get(id);
      },
    };
  };
  const fetchYap = (satirlar) => async (adres) => ({
    status: 200,
    json: async () => (String(adres).indexOf("/urunler-kuyruk") >= 0
      ? { satirlar, tablo_yok: false }
      : { siparisler: [], urunler: [], bekleyen: {}, kuyruk_tablosu: true }),
  });
  // id DESC gelir (sunucu ORDER BY id DESC): en yeni BASTA.
  const satirYap = (no, hal) => ({ id: 1000 - no, urun_id: hal + "-" + String(no).padStart(2, "0"),
    alan: "fiyat", deger: "500 TL", yazan: "panel", ts: "2026-09-06T12:00:00Z",
    hal, islendi_ts: null, islendi_commit: null, sebep: hal === "hata" ? "FIYAT_BICIMI" : null });

  const kosVe = async (satirlar) => {
    const dom = domYap();
    const disari = new Function("document", "fetch", "alert", "confirm",
      kod + "\nreturn {kuyrukYukle:kuyrukYukle};")(
      dom, fetchYap(satirlar), () => {}, () => true);
    await disari.kuyrukYukle();
    return dom.getElementById("kuyrukKutu").innerHTML;
  };

  // 2 bekleyen + 30 islendi + 3 hata (biten = 33, gosterilecek = 12)
  const karisik = [];
  karisik.push(satirYap(1, "beklemede"), satirYap(2, "beklemede"));
  for (let i = 1; i <= 3; i++) { karisik.push(satirYap(i, "hata")); }
  for (let i = 4; i <= 33; i++) { karisik.push(satirYap(i, "islendi")); }

  const h = await kosVe(karisik);
  const detayYeri = h.indexOf("<details");
  const ilkSatir = h.indexOf('class="satir"');

  ol("N1 bekleyen satirlar <details> DISINDA cizilir",
     ilkSatir >= 0 && detayYeri > ilkSatir &&
     h.slice(0, detayYeri).indexOf("beklemede-01") >= 0 &&
     h.slice(0, detayYeri).indexOf("beklemede-02") >= 0,
     "detay=" + detayYeri + " ilkSatir=" + ilkSatir);
  ol("N2 <details> VARSAYILAN KAPALI (open niteligi YOK)",
     detayYeri >= 0 && !/<details[^>]*\sopen/.test(h), h.slice(detayYeri, detayYeri + 60));
  ol("N3 biten kovasindan YALNIZ 12 satir cizilir (2 bekleyen + 12 = 14)",
     (h.match(/class="satir"/g) || []).length === 14,
     "satir=" + (h.match(/class="satir"/g) || []).length);
  ol("N4 gosterilen 12 EN YENI biten (hata-01..islendi-12 var, 13 YOK)",
     h.indexOf("hata-01") >= 0 && h.indexOf("islendi-12") >= 0 && h.indexOf("islendi-13") < 0);
  ol("N5 'hata' hali kapali baslikta SAYIYLA yanar (ucuncu sinif yutulmaz)",
     h.indexOf(">3 hata<") >= 0 && h.indexOf("Biten (son 12 / 33)") >= 0);
  ol("N6 Iptal dugmesi YALNIZ bekleyen satirlarda (2 tane)",
     (h.match(/kuyrukIptal\(/g) || []).length === 2,
     "iptal=" + (h.match(/kuyrukIptal\(/g) || []).length);

  // Bekleyen YOKKEN: sessiz bosluk YASAK — kutu ACIKCA "yok" der.
  const h2 = await kosVe([satirYap(4, "islendi"), satirYap(5, "islendi")]);
  ol("N7 bekleyen yoksa ACIKCA yazilir + Iptal dugmesi hic yok",
     h2.indexOf("Bekleyen üst yazım yok") >= 0 && h2.indexOf("kuyrukIptal(") < 0);
  ol("N8 biten 12'den azken baslik gercek sayiyi tasir (son 2 / 2)",
     h2.indexOf("Biten (son 2 / 2)") >= 0 && !/<details[^>]*\sopen/.test(h2));
}

console.log("");
console.log("TOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
process.exit(kalan === 0 ? 0 : 1);
