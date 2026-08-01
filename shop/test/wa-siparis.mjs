#!/usr/bin/env node
/**
 * PRUVO shop — POST /api/shop/yonet/wa-siparis KABUL TESTLERI (WhatsApp/Ege kanali).
 *
 *   node shop/test/wa-siparis.mjs
 *
 * yonet.js'i DOGRUDAN import eder (wrangler/ag/D1 ISTEMEZ — ref-route.mjs deseni).
 * env.KATALOG mock'lanir; SQL + bind parametreleri yakalanip iddia edilir.
 *
 * KAPSAM (kabul kapisi):
 *   A. YETKI      — anahtarsiz 404, yanlis anahtar 404, EGE_ANAHTAR yalniz BU ucu acar
 *                   (/liste, /durum, /kargo, /stl onunla 404), YONET_ANAHTAR da calisir.
 *   B. YAZMA      — gecerli siparis INSERT olur: siparis_no PR-yyMMdd-HHmmss-XXX,
 *                   kanal='whatsapp', dis_no yazilir, token NULL, durum kurallara uyar.
 *   C. DOGRULAMA  — zorunlu alan eksik/bozuksa 400 + ALAN ADLI hata, INSERT YOK.
 *   D. GORUNURLUK — /liste ayni satiri dondurur: kanal + dis_no + urun linki + WhatsApp
 *                   baski notu (uydurma malzeme onerisi YOK).
 *   E. GERIYE UYUM— (1) kanal/dis_no kolonu YOKKEN /liste ve /durum bugunku gibi calisir
 *                   (kolon merdiveni), (2) YAZMA o halde FAIL-CLOSED 503 verir,
 *                   (3) SITE siparisinde olcum kapisi ACIK kalir (regresyon yok),
 *                   (4) WhatsApp siparisinde 'odendi' gecisi olcum TETIKLEMEZ.
 *   F. IDEMPOTENS — ayni dis_no ikinci kez -> yeni INSERT YOK, mevcut numara doner.
 *
 * ONCE-KIRMIZI (elle kanitlanabilir mutasyonlar):
 *   - yonet.js'te EGE_ANAHTAR kolu /liste'ye de aciliyor yapilirsa -> A kirmizi.
 *   - INSERT'ten `kanal` dusurulurse -> B/D kirmizi.
 *   - waSiparis'te `durum` beyaz listesi kaldirilirsa -> C kirmizi.
 *   - durumDegistir'deki KANAL kapisi silinirse -> E(4) kirmizi.
 *   - kolonMerdiveni kaldirilirsa -> E(1) kirmizi.
 */

// ---- JSON IMPORT KOPRUSU (test altyapisi, uretim kodunu ETKILEMEZ) -------------
// yonet.js -> semalar.js -> jenerator/urunler/*.json zinciri, JSON'lari import
// ATTRIBUTE'suz alir (`with { type: "json" }` YOK). wrangler/esbuild bunu sorunsuz
// bundle'lar; CIPLAK NODE ise ERR_IMPORT_ATTRIBUTE_MISSING ile duser. semalar.js
// URETILMIS bir dosyadir (tools/sema-bundle-kapisi.py --yaz) — elle degistirilemez.
// Cozum: yalniz BU testin surecinde calisan bir resolve kancasi attribute'u ekler.
// Kanca data: URL olarak gomulur — shop/test/ altinda ikinci bir dosya acilsaydi
// tools/ci-kapsam-test.py onu "kosulmayan kabul testi" sayip CI'yi kirmizi yakardi.
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) { return { ...r, importAttributes: { type: 'json' } }; }" +
  "  return r; }"));
// KDV/adet kurallari TEK KAYNAK: /secenekler.js (IIFE, globalThis.PRUVO_SECENEK'e yazar).
// Worker'da bunu giris dosyasi (index.js) import eder; testte yonet.js'i TEK BASINA
// yukledigimiz icin ayni yan etkiyi burada uretiriz — yoksa KDV dokumu sessizce 0 kalir
// ve test uretimden FARKLI bir davranisi olcerdi.
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

/**
 * Basit D1 taklidi. secenek:
 *   kolonYok   : true -> kanal/dis_no gecen HER sorgu "no such column: kanal" firlatir
 *   listeSatir : /liste SELECT'inin dondurecegi satir(lar)
 *   siparis    : siparisGetir SELECT'inin dondurecegi satir
 *   disNoKayit : dis_no aramasinin dondurecegi satir (idempotens testi)
 */
function mockEnv(secenek) {
  secenek = secenek || {};
  const sorgular = [];   // {sql, args}
  const yazmalar = [];   // yalniz INSERT/UPDATE
  const env = {
    sorgular, yazmalar,
    YONET_ANAHTAR: secenek.yonetAnahtar === null ? undefined : YONET_ANAHTAR,
    EGE_ANAHTAR: secenek.egeAnahtar === false ? undefined : EGE_ANAHTAR,
    SITE_URL: "https://ornek-site.test",
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (secenek.kolonYok && /\bkanal\b|\bdis_no\b/.test(sql)) {
            throw new Error("D1_ERROR: no such column: kanal");
          }
          sorgular.push(kayit);
          if (/^\s*(INSERT|UPDATE)/i.test(sql)) { yazmalar.push(kayit); }
          if (/FROM siparisler WHERE siparis_no = \?$/.test(sql) ||
              /SELECT 1 AS v FROM siparisler/.test(sql)) {
            // numara benzersizlik on-kontrolu -> daima bos (numara uretilebilsin)
            if (/SELECT 1 AS v/.test(sql)) { return null; }
          }
          if (/WHERE kanal = \? AND dis_no = \?/.test(sql)) {
            return secenek.disNoKayit || null;
          }
          // Baski/parametrik zenginlestirme sorgusu (liste): katalog kaydi YOK varsayimi.
          if (/FROM urunler/.test(sql)) { return { results: [] }; }
          if (/^SELECT siparis_no, tarih, durum, durum_gecmisi/.test(sql)) {
            return secenek.siparis || null;
          }
          if (kip === "all") { return { results: secenek.listeSatir || [] }; }
          if (/^INSERT|^UPDATE/i.test(sql)) { return { meta: { changes: 1 } }; }
          return null;
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
const URL_BOS = new URL("https://ornek-site.test/api/shop/yonet/wa-siparis");
const ctxSahte = { waitUntil() {} };

function egeBaslik() { return { "X-Ege-Anahtar": EGE_ANAHTAR }; }
function yonetBaslik() { return { "X-Yonet-Anahtar": YONET_ANAHTAR }; }

const GECERLI = {
  dis_no: "PR-260801-110139",
  musteri: { ad: "Test Müşteri", tel: "05451386526", adres: "Örnek Mah. 1/2 Fethiye/Muğla" },
  odeme: "havale",
  urunler: [
    { ad: "Kırık kapı kolu (özel üretim)", link: "https://ornek-site.test/urun/ozel-kol/",
      adet: 2, tutar_kurus: 90000 },
  ],
};

async function cagir(govde, baslik, env, altYol, method) {
  return yonet(istek(govde, baslik, method), env, URL_BOS,
               ctxSahte, altYol || "/wa-siparis", undefined);
}

// ---------------------------------------------------------------- A. YETKI

async function setA() {
  console.log("\nA. YETKI (en az yetki + varlik sizmasi)");
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, {}, env);
    ol("anahtarsiz -> 404", c.status === 404, "kod=" + c.status);
    ol("anahtarsiz -> D1'e yazma YOK", env.yazmalar.length === 0);
  }
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, { "X-Ege-Anahtar": "x".repeat(48) }, env);
    ol("yanlis Ege anahtari -> 404", c.status === 404, "kod=" + c.status);
  }
  {
    const env = mockEnv({ egeAnahtar: false });
    const c = await cagir(GECERLI, egeBaslik(), env);
    ol("EGE_ANAHTAR secret'i tanimsiz -> 404 (fail-closed)", c.status === 404);
  }
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, egeBaslik(), env);
    ol("gecerli Ege anahtari -> 201", c.status === 201, "kod=" + c.status);
  }
  {
    const env = mockEnv();
    const c = await cagir(GECERLI, yonetBaslik(), env);
    ol("yonetim anahtari da calisir -> 201", c.status === 201, "kod=" + c.status);
  }
  // EN AZ YETKI: Ege anahtari BASKA hicbir ucu acmaz.
  for (const [yol, yontem] of [["/liste", "GET"], ["/durum", "POST"], ["/kargo", "POST"],
                               ["/stl", "GET"], ["/", "GET"], ["/stl-liste", "GET"]]) {
    const env = mockEnv();
    const c = await yonet(istek({}, egeBaslik(), yontem), env,
                          new URL("https://ornek-site.test/api/shop/yonet" + yol),
                          ctxSahte, yol, undefined);
    ol("Ege anahtari " + yol + " (" + yontem + ") ucunu ACMAZ -> 404", c.status === 404,
       "kod=" + c.status);
  }
  {
    // GET /wa-siparis: yalniz POST kabul -> Ege anahtariyla bile 404.
    const env = mockEnv();
    const c = await yonet(istek({}, egeBaslik(), "GET"), env, URL_BOS, ctxSahte,
                          "/wa-siparis", undefined);
    ol("GET /wa-siparis -> 404 (yalniz POST)", c.status === 404, "kod=" + c.status);
  }
}

// ---------------------------------------------------------------- B. YAZMA

const NO_KALIBI = /^PR-\d{6}-\d{6}-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{3}$/;

async function setB() {
  console.log("\nB. YAZMA (siparis kaydi + ID semasi)");
  const env = mockEnv();
  const c = await cagir(GECERLI, egeBaslik(), env);
  const govde = JSON.parse(await c.text());
  ol("201 + ok:true", c.status === 201 && govde.ok === true);
  ol("siparis_no PANEL semasinda (PR-yyMMdd-HHmmss-XXX)", NO_KALIBI.test(govde.siparis_no),
     govde.siparis_no);
  ol("Ege'nin kendi numarasi siparis_no OLARAK ALINMADI",
     govde.siparis_no !== GECERLI.dis_no);
  ol("dis_no yanitta korunur", govde.dis_no === "PR-260801-110139");
  ol("kanal yanitta 'whatsapp'", govde.kanal === "whatsapp");

  const ins = env.yazmalar.filter((y) => /^INSERT INTO siparisler/.test(y.sql));
  ol("TEK INSERT", ins.length === 1, "adet=" + ins.length);
  const sql = ins[0] ? ins[0].sql : "";
  const args = ins[0] ? ins[0].args : [];
  ol("INSERT kanal + dis_no kolonlarini tasir", /kanal, dis_no\)/.test(sql));
  ol("token NULL yazilir (iyzico donusu bu satiri bulamaz)", /\(\?, NULL, /.test(sql));
  ol("bind: kanal='whatsapp'", args.includes("whatsapp"));
  ol("bind: dis_no", args.includes("PR-260801-110139"));
  ol("bind: durum varsayilani 'havale-bekliyor'", args[2] === "havale-bekliyor");
  ol("bind: odeme_yontemi='havale'", args[6] === "havale");
  ol("bind: tutar kalemlerden toplanir (90000)", args[3] === 90000);
  ol("bind: KDV dokumu hesaplanir (0 DEGIL)", args[5] > 0, "kdv=" + args[5]);
  ol("bind: musteri ad/tel/adres", args[8] === "Test Müşteri" &&
     args[9] === "05451386526" && args[11].startsWith("Örnek Mah."));
  ol("bind: eposta verilmediyse ''", args[10] === "");
  const satirlar = JSON.parse(args[7]);
  ol("kalem katalog id'sini LINKTEN turetir", satirlar[0].id === "ozel-kol", satirlar[0].id);
  ol("kalem linki satirda saklanir", satirlar[0].url === GECERLI.urunler[0].link);
  ol("kalem kanal isareti tasir", satirlar[0].kanal === "whatsapp");
  ol("kalem malzeme/renk BOS (uydurma beyan yok)",
     satirlar[0].malzeme === "" && satirlar[0].renk === "");
  const gecmis = JSON.parse(args[12]);
  ol("durum gecmisi ilk kaydi yazilir", Array.isArray(gecmis) && gecmis[0].d === "havale-bekliyor");

  // 'odendi' de yazilabilir; kargolandi/tamamlandi YAZILAMAZ.
  {
    const e2 = mockEnv();
    const c2 = await cagir({ ...GECERLI, dis_no: "", durum: "odendi" }, egeBaslik(), e2);
    ol("durum='odendi' kabul", c2.status === 201, "kod=" + c2.status);
  }
  {
    const e3 = mockEnv();
    const c3 = await cagir({ ...GECERLI, durum: "kargolandi" }, egeBaslik(), e3);
    ol("durum='kargolandi' RED (takip kodsuz kargo damgasi uretilemez)", c3.status === 400);
    ol("red edilen istekte INSERT YOK", e3.yazmalar.length === 0);
  }
  // Link YOKSA sentetik id "wa-" onekli olur (katalog id'siyle carpismaz).
  {
    const e4 = mockEnv();
    await cagir({ ...GECERLI, dis_no: "",
                  urunler: [{ ad: "Bulaşık makinesi sepet tekerleği", adet: 1 }] },
                egeBaslik(), e4);
    const s = JSON.parse(e4.yazmalar[0].args[7]);
    ol("linksiz kalem id'si 'wa-' onekli", s[0].id.startsWith("wa-"), s[0].id);
    ol("sentetik id yalniz [a-z0-9-]", /^[a-z0-9-]+$/.test(s[0].id), s[0].id);
  }
}

// ---------------------------------------------------------------- C. DOGRULAMA

async function setC() {
  console.log("\nC. DOGRULAMA (zorunlu alan / bicim)");
  const durumlar = [
    ["bozuk JSON", "BOZUK", "gecersiz-json"],
    ["musteri adi yok", { ...GECERLI, musteri: { tel: "05451386526", adres: "Adres 1" } }, "musteri-ad"],
    ["telefon kisa", { ...GECERLI, musteri: { ...GECERLI.musteri, tel: "0545" } }, "musteri-tel"],
    ["adres yok", { ...GECERLI, musteri: { ad: "Ad Soyad", tel: "05451386526" } }, "musteri-adres"],
    ["eposta bozuk", { ...GECERLI, musteri: { ...GECERLI.musteri, eposta: "abc-def" } }, "musteri-eposta"],
    ["odeme yontemi yok", { ...GECERLI, odeme: undefined }, "gecersiz-odeme"],
    ["odeme yontemi taninmiyor", { ...GECERLI, odeme: "kripto" }, "gecersiz-odeme"],
    ["urun listesi bos", { ...GECERLI, urunler: [] }, "gecersiz-urunler"],
    ["urun adi yok", { ...GECERLI, urunler: [{ adet: 1 }] }, "urun-ad"],
    ["urun linki https degil", { ...GECERLI, urunler: [{ ad: "Parça", link: "javascript:alert(1)" }] }, "urun-link"],
    ["adet 0", { ...GECERLI, urunler: [{ ad: "Parça", adet: 0 }] }, "urun-adet"],
    ["adet 100", { ...GECERLI, urunler: [{ ad: "Parça", adet: 100 }] }, "urun-adet"],
    ["tutar ondalikli (kurus tamsayi degil)", { ...GECERLI, tutar_kurus: 12.5 }, "gecersiz-tutar"],
    ["tutar negatif", { ...GECERLI, tutar_kurus: -1 }, "gecersiz-tutar"],
    ["dis_no bicimsiz", { ...GECERLI, dis_no: "PR 260801 / 110139" }, "gecersiz-dis-no"],
    ["durum beyaz liste disi", { ...GECERLI, durum: "tamamlandi" }, "gecersiz-durum"],
  ];
  for (const [ad, govde, beklenen] of durumlar) {
    const env = mockEnv();
    const c = await cagir(govde, egeBaslik(), env);
    const j = JSON.parse(await c.text());
    ol(ad + " -> 400 " + beklenen, c.status === 400 && j.hata === beklenen,
       "kod=" + c.status + " hata=" + j.hata);
    ol(ad + " -> INSERT YOK", env.yazmalar.length === 0);
  }
  // Tutar OPSIYONEL: hic tutar yoksa da siparis acilir (Okan elle fiyatlandirir).
  {
    const env = mockEnv();
    const c = await cagir({ ...GECERLI, dis_no: "", tutar_kurus: undefined,
                            urunler: [{ ad: "Ölçüye özel parça" }] }, egeBaslik(), env);
    ol("tutar BOS -> 201 (fiyat sonra elle girilir)", c.status === 201, "kod=" + c.status);
    ol("tutar BOS -> tutar_kurus 0 yazilir", env.yazmalar[0].args[3] === 0);
  }
}

// ---------------------------------------------------------------- D. GORUNURLUK

async function setD() {
  console.log("\nD. GORUNURLUK (/liste ayni kaydi dondurur)");
  const satir = {
    id: 7, siparis_no: "PR-260801-110200-ABC", tarih: "2026-08-01T11:02:00.000Z",
    durum: "havale-bekliyor", tutar_kurus: 90000, kargo_kurus: 0, kdv_kurus: 15000,
    odeme_yontemi: "havale", kargo_firma: "", kargo_kodu: "", durum_gecmisi: "[]",
    musteri_ad: "Test Müşteri", musteri_tel: "05451386526", musteri_eposta: "",
    musteri_adres: "Örnek Mah. 1/2",
    kanal: "whatsapp", dis_no: "PR-260801-110139",
    urunler: JSON.stringify([{ id: "wa-ozel-parca", baslik: "Kırık kapı kolu",
      malzeme: "", renk: "", adet: 2, kanal: "whatsapp",
      url: "https://ornek-site.test/urun/ozel-kol/" }]),
  };
  const env = mockEnv({ listeSatir: [satir] });
  const c = await yonet(istek(null, yonetBaslik(), "GET"), env,
                        new URL("https://ornek-site.test/api/shop/yonet/liste"),
                        ctxSahte, "/liste", undefined);
  const j = JSON.parse(await c.text());
  const s = j.siparisler[0];
  ol("/liste 200", c.status === 200);
  ol("kanal alani doner", s.kanal === "whatsapp");
  ol("dis_no alani doner", s.dis_no === "PR-260801-110139");
  ol("kalem urun_url'i KALEM LINKI olur", s.kalemler[0].urun_url ===
     "https://ornek-site.test/urun/ozel-kol/", s.kalemler[0].urun_url);
  ol("baski notu WhatsApp'a ozel (uydurma malzeme onerisi YOK)",
     /WhatsApp siparişi/.test(s.kalemler[0].baski_oneri) &&
     !/doluluk/.test(s.kalemler[0].baski_oneri), s.kalemler[0].baski_oneri);

  // SITE siparisi: kanal 'site' + link yok -> bugunku davranis (urun sayfasi linki).
  const siteSatir = { ...satir, kanal: "site", dis_no: "",
    urunler: JSON.stringify([{ id: "kapi-kolu", baslik: "Kapı kolu", malzeme: "PETG",
      renk: "Siyah", adet: 1 }]) };
  const env2 = mockEnv({ listeSatir: [siteSatir] });
  const c2 = await yonet(istek(null, yonetBaslik(), "GET"), env2,
                         new URL("https://ornek-site.test/api/shop/yonet/liste"),
                         ctxSahte, "/liste", undefined);
  const s2 = JSON.parse(await c2.text()).siparisler[0];
  ol("SITE siparisi urun_url'i DEGISMEDI",
     s2.kalemler[0].urun_url === "https://ornek-site.test/urun/kapi-kolu/",
     s2.kalemler[0].urun_url);
  ol("SITE siparisi baski onerisi DEGISMEDI (PETG fallback)",
     /PETG|doluluk/.test(s2.kalemler[0].baski_oneri), s2.kalemler[0].baski_oneri);
}

// ---------------------------------------------------------------- E. GERIYE UYUM

async function setE() {
  console.log("\nE. GERIYE UYUM (goc kosmadan once + site akisi regresyonu)");
  // (1) kanal/dis_no kolonu YOKKEN /liste calismaya devam eder (kolon merdiveni).
  {
    const satir = {
      id: 3, siparis_no: "PR-260731-101010-XYZ", tarih: "2026-07-31T10:10:10.000Z",
      durum: "odendi", tutar_kurus: 50000, kargo_kurus: 25000, kdv_kurus: 12500,
      odeme_yontemi: "kart", kargo_firma: "", kargo_kodu: "", durum_gecmisi: "[]",
      musteri_ad: "A", musteri_tel: "0", musteri_eposta: "", musteri_adres: "B",
      urunler: JSON.stringify([{ id: "kapi-kolu", baslik: "Kapı kolu", malzeme: "PLA",
        renk: "Beyaz", adet: 1 }]),
    };
    const env = mockEnv({ kolonYok: true, listeSatir: [satir] });
    const c = await yonet(istek(null, yonetBaslik(), "GET"), env,
                          new URL("https://ornek-site.test/api/shop/yonet/liste"),
                          ctxSahte, "/liste", undefined);
    const j = JSON.parse(await c.text());
    ol("kolon YOKKEN /liste 200 (panel dusmuyor)", c.status === 200, "kod=" + c.status);
    ol("kolon YOKKEN kanal 'site' varsayilanina duser", j.siparisler[0].kanal === "site");
    ol("kolon YOKKEN dis_no ''", j.siparisler[0].dis_no === "");
  }
  // (2) kolon YOKKEN yazma FAIL-CLOSED (sessizce kanalsiz kayit acilmaz).
  {
    const env = mockEnv({ kolonYok: true });
    const c = await cagir(GECERLI, egeBaslik(), env);
    const j = JSON.parse(await c.text());
    ol("kolon YOKKEN /wa-siparis 503", c.status === 503, "kod=" + c.status);
    ol("kolon YOKKEN hata 'sema-goc-gerekli'", j.hata === "sema-goc-gerekli");
    ol("kolon YOKKEN INSERT YOK", env.yazmalar.length === 0);
  }
  // (3) SITE siparisinde 'havale-bekliyor' -> 'odendi' olcumu HALA tetiklenir.
  {
    const env = mockEnv({ siparis: { siparis_no: "PR-1", durum: "havale-bekliyor",
      durum_gecmisi: "[]", urunler: "[]", tutar_kurus: 1000, kargo_kurus: 0, kdv_kurus: 0,
      odeme_yontemi: "havale", atif: "", tarih: "2026-08-01T00:00:00.000Z",
      musteri_ad: "A", musteri_eposta: "", musteri_adres: "B", kanal: "site" } });
    const c = await yonet(istek({ siparis_no: "PR-1", durum: "odendi" }, yonetBaslik(), "POST"),
                          env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                          ctxSahte, "/durum", undefined);
    ol("SITE: odendi gecisi 200", c.status === 200, "kod=" + c.status);
    const upd = env.yazmalar.find((y) => /^UPDATE siparisler SET durum/.test(y.sql));
    ol("SITE: olcum izi {\"o\":1} YAZILIR (regresyon yok)",
       !!upd && /"o":1/.test(upd.args[1]), upd && upd.args[1]);
  }
  // (4) WHATSAPP siparisinde ayni gecis olcum TETIKLEMEZ.
  {
    const env = mockEnv({ siparis: { siparis_no: "PR-2", durum: "havale-bekliyor",
      durum_gecmisi: "[]", urunler: "[]", tutar_kurus: 1000, kargo_kurus: 0, kdv_kurus: 0,
      odeme_yontemi: "havale", atif: "", tarih: "2026-08-01T00:00:00.000Z",
      musteri_ad: "A", musteri_eposta: "", musteri_adres: "B", kanal: "whatsapp" } });
    const c = await yonet(istek({ siparis_no: "PR-2", durum: "odendi" }, yonetBaslik(), "POST"),
                          env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                          ctxSahte, "/durum", undefined);
    ol("WHATSAPP: odendi gecisi yine 200 (durum ilerler)", c.status === 200, "kod=" + c.status);
    const upd = env.yazmalar.find((y) => /^UPDATE siparisler SET durum/.test(y.sql));
    ol("WHATSAPP: olcum izi {\"o\":1} YAZILMAZ (GA4/Meta'ya gitmez)",
       !!upd && !/"o":1/.test(upd.args[1]), upd && upd.args[1]);
  }
  // (5) kanal kolonu YOKKEN /durum bugunku gibi olcer (merdiven -> kapi ACIK).
  {
    const env = mockEnv({ kolonYok: true, siparis: { siparis_no: "PR-3",
      durum: "havale-bekliyor", durum_gecmisi: "[]", urunler: "[]", tutar_kurus: 1000,
      kargo_kurus: 0, kdv_kurus: 0, odeme_yontemi: "havale", atif: "",
      tarih: "2026-08-01T00:00:00.000Z", musteri_ad: "A", musteri_eposta: "",
      musteri_adres: "B" } });
    const c = await yonet(istek({ siparis_no: "PR-3", durum: "odendi" }, yonetBaslik(), "POST"),
                          env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                          ctxSahte, "/durum", undefined);
    const upd = env.yazmalar.find((y) => /^UPDATE siparisler SET durum/.test(y.sql));
    ol("kolon YOKKEN /durum 200 + olcum izi yazilir", c.status === 200 &&
       !!upd && /"o":1/.test(upd.args[1]), "kod=" + c.status);
  }
}

// ---------------------------------------------------------------- F. IDEMPOTENS

async function setF() {
  console.log("\nF. IDEMPOTENS (Ege yeniden denerse ikiz siparis olusmaz)");
  const env = mockEnv({ disNoKayit: { siparis_no: "PR-260801-110200-ABC",
                                      durum: "havale-bekliyor" } });
  const c = await cagir(GECERLI, egeBaslik(), env);
  const j = JSON.parse(await c.text());
  ol("ayni dis_no -> 200 (201 DEGIL)", c.status === 200, "kod=" + c.status);
  ol("mevcut siparis numarasi doner", j.siparis_no === "PR-260801-110200-ABC");
  ol("tekrar isareti", j.tekrar === true);
  ol("ikinci INSERT YOK", env.yazmalar.length === 0, "yazma=" + env.yazmalar.length);

  // dis_no VERILMEZSE idempotens aranmaz (her cagri yeni siparis) — bilincli davranis.
  const env2 = mockEnv({ disNoKayit: { siparis_no: "X", durum: "odendi" } });
  const c2 = await cagir({ ...GECERLI, dis_no: undefined }, egeBaslik(), env2);
  ol("dis_no yoksa yeni siparis acilir (201)", c2.status === 201, "kod=" + c2.status);
}

// ---------------------------------------------------------------- kosum

(async () => {
  console.log("PRUVO shop — /api/shop/yonet/wa-siparis kabul testleri");
  await setA();
  await setB();
  await setC();
  await setD();
  await setE();
  await setF();
  console.log("\n" + (kalan === 0 ? "✅ HEPSI GECTI" : "❌ KIRMIZI") +
              " — gecen: " + gecen + ", kalan: " + kalan);
  process.exit(kalan === 0 ? 0 : 1);
})();
