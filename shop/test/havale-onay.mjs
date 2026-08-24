#!/usr/bin/env node
/**
 * PRUVO shop — K284 HAVALE ONAY UCU KABUL KAPISI.
 *
 *   node shop/test/havale-onay.mjs
 *
 * OLCTUGU HUKUM (Okan karari 24 Agu 2026): 'havale-bekliyor' -> 'odendi' gecisi AYRI ve
 * DAR bir uctan (`POST /yonet/havale-onay`) ve YALNIZ DEKONT REFERANSIYLA yapilir —
 * /kargo ucunun BIREBIR KARDESI. K252'nin TAHSILAT YALANI ilkesi KORUNUR: /durum ucundan
 * ayni gecis HALA 400 doner.
 *
 *   (a) referanssiz/bos referans          -> 400 + KENDI hata kodu ('dekont-ref'), YAZMA YOK
 *   (b) 'havale-bekliyor' DISINDAN        -> 400 'gecersiz-gecis', YAZMA YOK
 *   (c) basarili onay                     -> durum='odendi', referans D1'de, gecmiste 'odendi'
 *   (d) OLCUM GITTI                       -> Purchase, kaynak="havale", event_id=siparis_no
 *   (e) IDEMPOTENS                        -> ayni cagri iki kez: ikincide olcum TEKRAR GITMEZ
 *   (f) 🔴 NEGATIF KONTROL (ilkeyi koruyan kol): /durum'dan 'havale-bekliyor' -> 'odendi'
 *       HALA 400 'odeme-durumu-elle-setlenemez'. BU VAKA SILINIRSE KABUL GECERSIZDIR.
 *   (h) SEMA PARITESI                     -> kolon hem d1-sema.sql'de hem GOC_KOLON_SIPARIS'te
 *   (i) GIZLILIK                          -> dekont_ref log'a / hata metnine / yanita GIRMEZ
 *   (j) PANEL                             -> form YALNIZ 'havale-bekliyor' kartinda; durum
 *                                            secicisi HALA `izinli_gecisler`ten TURER
 *
 * NASIL (siparis-durum-secici.mjs deseni — kopya kod YAZILMAZ):
 *   SUNUCU ekseni : shop/src/yonet.js DOGRUDAN import edilir, GERCEK `yonet()` router'i
 *                   DURUM TUTAN sahte D1 ile cagrilir. (e) icin durum tutmak SART: durumsuz
 *                   fikstur "ikinci cagri" diye ayni baslangici bir daha olcerdi, yani
 *                   idempotens iddiasi TAUTOLOJI olurdu.
 *   OLCUM ekseni  : gercek `fetch` STUB'lanir; Meta/GA4 govdesi UCTAN UCA okunur (log
 *                   satirina degil, GERCEKTEN POST EDILEN govdeye bakilir).
 *   PANEL ekseni  : sayfa JS'i HAM KAYNAK olarak cekilip vm'de kosturulur; KOPYA YAZILMAZ.
 *
 * 🔴 SEBEP DE DOGRULANIR: 400 gormek YETMEZ ([[sahte-bagimlilik-sekli-negatif-blogu-
 * kutsar]]). Her negatif iddia hem KODU hem `hata` ALANINI hem de D1'e YAZILMADIGINI
 * ayri ayri iddia eder; her negatif blok bir POZITIF KONTROLLE eslesir (red, ucun
 * bozuklugundan degil KURALDAN gelsin).
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek musteri verisi/telefon/adres/dekont bu dosyaya YAZILMAZ.
 *
 * ONCE-KIRMIZI KANITI (mutantlar, tools/havale-onay-mutasyon.py — gecici AYNAYA uygulanir,
 * calisma agacina YAZMAZ):
 *   M1 OLCUM   : havaleOlcumu() cagrisi dusurulur      -> (d) OLUR, (a)(b)(c)(f) YASAR
 *   M2 DELIL   : bos referans reddi kaldirilir         -> (a) OLUR, (c)(f) YASAR
 *   M3 GENIS   : havaleGecisiGecerli hep true doner    -> (b) OLUR, (a)(f) YASAR
 *   M4 ILKE    : /durum'un odeme ekseni reddi acilir   -> (f) OLUR, (a)(c) YASAR
 *   M5 PANEL   : havale formu HER kartta basilir       -> (j) OLUR, (a)(c) YASAR
 *   K0 KONTROL : ilgisiz kol (rozet rengi) bozulur     -> HICBIRI OLMEZ
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (kaynak capasi bulunamadi).
 */

// ---- JSON IMPORT KOPRUSU (test altyapisi; uretim kodunu ETKILEMEZ) -------------
// Gerekce birebir shop/test/siparis-durum-secici.mjs'teki gibidir: yonet.js -> semalar.js
// -> jenerator/urunler/*.json zinciri import attribute'suz alir; ciplak node duser.
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) { return { ...r, importAttributes: { type: 'json' } }; }" +
  "  return r; }"));
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const req = createRequire(import.meta.url);
req(path.join(KOK, "secenekler.js"));

// Mutasyon harness'i gecici AYNAYA yazar ve bu degiskenle hedef gosterir.
const KAYNAK_YOL = process.env.PRUVO_YONET_KAYNAK || path.join(BURASI, "..", "src", "yonet.js");
const KAYNAK = fs.readFileSync(KAYNAK_YOL, "utf8");
const { yonet } = await import(url.pathToFileURL(KAYNAK_YOL).href);

let gecen = 0, kalan = 0;
const olen = new Set();            // KIRMIZI yanan iddia etiketleri (mutant atfi icin)
function ol(etiket, ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ (" + etiket + ") " + ad); }
  else {
    kalan++; olen.add(etiket);
    console.log("  ❌ (" + etiket + ") " + ad + (detay ? " — " + detay : ""));
  }
}

const YONET_ANAHTAR = "y".repeat(48);
const SIPARIS_NO = "PR-TEST-000284";
// 🔒 UYDURMA referans — gercek bir dekont numarasi DEGIL.
const REF = "TEST-DEKONT-REF-0001";

// Olcum secret'leri UYDURMADIR; log sizinti iddiasinda da bu dizeler aranir.
const ENV_OLCUM = {
  META_PIXEL_ID: "1000000000000001", META_CAPI_TOKEN: "UYDURMA-CAPI-TOKEN",
  GA4_MEASUREMENT_ID: "G-UYDURMA1", GA4_API_SECRET: "UYDURMA-GA4-SECRET",
  SITE_URL: "https://ornek-site.test",
};

// ---------------------------------------------------------------- fikstur
/** BICIMI taklit eden siparis satiri — gercek veri DEGIL. */
function satir(durum, ekstra) {
  return {
    siparis_no: SIPARIS_NO,
    // 1 saat once: Meta'nin 7 gunluk geriye-donuk penceresi ICINDE (olay atlanmasin).
    tarih: new Date(Date.now() - 3600 * 1000).toISOString(),
    durum: durum,
    durum_gecmisi: JSON.stringify([{ d: durum, z: "2026-08-24T10:00:00Z" }]),
    urunler: JSON.stringify([
      { id: "ornek-parca", baslik: "Ornek Parca", adet: 1,
        birim_kurus: 43290, tutar_kurus: 43290 },
    ]),
    tutar_kurus: 43290, kargo_kurus: 25000, kdv_kurus: 11381,
    odeme_yontemi: "havale",
    // fbp VAR -> Meta riza kapisi acik (user_data bos kalmaz, olay GERCEKTEN gider).
    atif: JSON.stringify({ ga_client_id: "1.2", fbp: "fb.1.1690.uydurma" }),
    kanal: "site",
    musteri_ad: "Ornek Musteri", musteri_eposta: "", musteri_adres: "Ornek Mah. 1",
    kargo_firma: null, kargo_kodu: null, havale_dekont_ref: "",
    ...(ekstra || {}),
  };
}

/**
 * DURUM TUTAN sahte D1.
 *  `env.satir`    : canli satir (UPDATE'ler BUNU degistirir -> (e) gercek olcum olur).
 *  `env.yazmalar` : BASARIYLA kosan INSERT/UPDATE kayitlari {sql, args}.
 *  `kolonVar=false` : `havale_dekont_ref` kolonu YOK -> UPDATE "no such column" atar
 *                     (sema-goc penceresi; uc fail-closed 503 dondurmeli).
 */
function mockEnv(baslangic, secenek) {
  const s = secenek || {};
  const kolonVar = s.kolonVar !== false;
  const yazmalar = [];
  const durumu = { ...baslangic };
  const env = {
    yazmalar,
    satir: durumu,
    YONET_ANAHTAR,
    ...ENV_OLCUM,
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (/^\s*UPDATE siparisler/.test(sql)) {
            if (/havale_dekont_ref/.test(sql) && !kolonVar) {
              throw new Error("D1_ERROR: no such column: havale_dekont_ref");
            }
            const a = kayit.args;
            // Ortak kuyruk: ... WHERE siparis_no = ? AND durum = ?  (CAS)
            const beklenen = a[a.length - 1];
            if (durumu.durum !== beklenen) { return { meta: { changes: 0 } }; }
            if (/SET durum = 'odendi', havale_dekont_ref = \?, durum_gecmisi = \?/.test(sql)) {
              durumu.durum = "odendi";
              durumu.havale_dekont_ref = a[0];
              durumu.durum_gecmisi = a[1];
            } else if (/SET durum = \?, durum_gecmisi = \?/.test(sql)) {
              durumu.durum = a[0];
              durumu.durum_gecmisi = a[1];
            }
            yazmalar.push(kayit);
            return { meta: { changes: 1 } };
          }
          if (/^\s*INSERT/i.test(sql)) { yazmalar.push(kayit); return { meta: { changes: 1 } }; }
          if (/FROM urunler/.test(sql)) { return { results: [] }; }
          if (/FROM urun_kaynak/.test(sql)) { return { results: [] }; }
          if (/^SELECT siparis_no, tarih, durum, durum_gecmisi/.test(sql)) {
            return { ...durumu };
          }
          if (kip === "all") { return { results: [{ ...durumu }] }; }
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

function istek(govde) {
  return {
    method: "POST",
    headers: { get: (h) => (h === "X-Yonet-Anahtar" ? YONET_ANAHTAR : null) },
    json: async () => govde,
  };
}

/** Konsol ciktisini YAKALA (gizlilik + "olcum atlandi" izleri icin). */
async function logYakala(fn) {
  const satirlar = [];
  const l = console.log, e = console.error, w = console.warn;
  console.log = (...a) => { satirlar.push(a.join(" ")); };
  console.error = (...a) => { satirlar.push(a.join(" ")); };
  console.warn = (...a) => { satirlar.push(a.join(" ")); };
  try { await fn(); } finally { console.log = l; console.error = e; console.warn = w; }
  return satirlar;
}

/** Cagrilan URL + govdeyi kaydeden fetch stub (AG ISTEGI YOK). */
function sahteFetch() {
  const cagrilar = [];
  const f = async (adres, opt) => {
    cagrilar.push({ url: String(adres), govde: opt && opt.body ? JSON.parse(opt.body) : null });
    return { status: 200, text: async () => "{\"events_received\":1}" };
  };
  f.cagrilar = cagrilar;
  return f;
}

/**
 * POST /yonet/havale-onay — GERCEK router uzerinden, olcum kablosu CANLI.
 * Doner {kod, govde, env, cagrilar, loglar}.
 */
async function onayCagir(env, govde) {
  const eskiFetch = globalThis.fetch;
  const f = sahteFetch();
  globalThis.fetch = f;
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  let c = null;
  const loglar = await logYakala(async () => {
    c = await yonet(istek(govde), env,
      new URL("https://ornek-site.test/api/shop/yonet/havale-onay"),
      ctx, "/havale-onay", undefined);
    await Promise.all(bekleyen);
  });
  globalThis.fetch = eskiFetch;
  let cevap = null;
  try { cevap = await c.json(); } catch (e) { cevap = null; }
  return { kod: c.status, govde: cevap, env: env, cagrilar: f.cagrilar, loglar: loglar };
}

/** POST /yonet/durum — negatif kontrol kolu (f) icin. */
async function durumCagir(env, hedef) {
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  const c = await yonet(istek({ siparis_no: SIPARIS_NO, durum: hedef }), env,
    new URL("https://ornek-site.test/api/shop/yonet/durum"), ctx, "/durum", undefined);
  await Promise.all(bekleyen);
  let cevap = null;
  try { cevap = await c.json(); } catch (e) { cevap = null; }
  return { kod: c.status, govde: cevap, env: env };
}

const metaCagrilari = (c) => c.filter((x) => x.url.indexOf("graph.facebook.com") >= 0);
const ga4Cagrilari = (c) => c.filter((x) => x.url.indexOf("google-analytics.com") >= 0);

// ============================================================ (a) DELIL ZORUNLU
console.log("\n(a) DELIL ZORUNLU — referanssiz/bos/asiri uzun referans REDDEDILIR");
{
  const vakalar = [
    ["dekont_ref alani YOK", { siparis_no: SIPARIS_NO }],
    ["dekont_ref bos dize", { siparis_no: SIPARIS_NO, dekont_ref: "" }],
    ["dekont_ref yalniz bosluk", { siparis_no: SIPARIS_NO, dekont_ref: "   " }],
    ["dekont_ref 81 karakter (tavan 80)", { siparis_no: SIPARIS_NO, dekont_ref: "R".repeat(81) }],
    ["dekont_ref sayi (metin degil)", { siparis_no: SIPARIS_NO, dekont_ref: 12345 }],
  ];
  for (const [ad, govde] of vakalar) {
    const env = mockEnv(satir("havale-bekliyor"));
    const r = await onayCagir(env, govde);
    ol("a", ad + " -> 400 'dekont-ref'",
      r.kod === 400 && r.govde && r.govde.hata === "dekont-ref",
      "kod=" + r.kod + " hata=" + (r.govde && r.govde.hata));
    ol("a", ad + " -> D1'e YAZMA YOK, durum 'havale-bekliyor' KALDI",
      r.env.yazmalar.length === 0 && r.env.satir.durum === "havale-bekliyor",
      "yazma=" + r.env.yazmalar.length + " durum=" + r.env.satir.durum);
  }
  // POZITIF KONTROL: red ucun bozuklugundan DEGIL, referans SARTINDAN geliyor —
  // AYNI siparis, AYNI uc, referans VERILINCE 200.
  const envP = mockEnv(satir("havale-bekliyor"));
  const p = await onayCagir(envP, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  ol("a", "POZITIF KONTROL: referans VERILINCE ayni uc 200 doner (uc saglam)",
    p.kod === 200 && p.govde && p.govde.ok === true, "kod=" + p.kod);
  // SEMA FAIL-CLOSED: kolon yoksa REFERANSSIZ yazmak yerine 503 (yazma YOK).
  const envK = mockEnv(satir("havale-bekliyor"), { kolonVar: false });
  const k = await onayCagir(envK, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  ol("a", "kolon YOKKEN 503 'sema-goc-gerekli' + YAZMA YOK (referanssiz odendi OLUSMAZ)",
    k.kod === 503 && k.govde && k.govde.hata === "sema-goc-gerekli" &&
    envK.yazmalar.length === 0 && envK.satir.durum === "havale-bekliyor",
    "kod=" + k.kod + " durum=" + envK.satir.durum);
}

// ============================================================ (b) DAR GECIS
console.log("\n(b) DAR GECIS — 'havale-bekliyor' DISINDAKI her mevcut durumdan 400");
{
  const digerleri = ["bekliyor", "odendi", "basarisiz", "incele",
                     "uretimde", "kargolandi", "tamamlandi", "iptal"];
  for (const mevcut of digerleri) {
    const env = mockEnv(satir(mevcut));
    const r = await onayCagir(env, { siparis_no: SIPARIS_NO, dekont_ref: REF });
    ol("b", "'" + mevcut + "' -> 400 'gecersiz-gecis' (mevcut+hedef gorunur)",
      r.kod === 400 && r.govde && r.govde.hata === "gecersiz-gecis" &&
      r.govde.mevcut === mevcut && r.govde.hedef === "odendi",
      "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
    ol("b", "'" + mevcut + "' -> D1'e YAZMA YOK",
      env.yazmalar.length === 0 && env.satir.durum === mevcut,
      "yazma=" + env.yazmalar.length);
  }
  // Var olmayan siparis: 404 (varlik sizintisi acilmaz, /kargo ile AYNI davranis).
  const envY = mockEnv(satir("havale-bekliyor"));
  envY.KATALOG.prepare = ((eski) => (sql) => {
    const p = eski(sql);
    if (/^SELECT siparis_no, tarih, durum, durum_gecmisi/.test(sql)) {
      return { bind() { return this; }, async first() { return null; },
               async run() { return { meta: { changes: 0 } }; },
               async all() { return { results: [] }; } };
    }
    return p;
  })(envY.KATALOG.prepare);
  const y = await onayCagir(envY, { siparis_no: "PR-YOK-000000", dekont_ref: REF });
  ol("b", "var olmayan siparis -> 404 'siparis-yok'",
    y.kod === 404 && y.govde && y.govde.hata === "siparis-yok", "kod=" + y.kod);
  // Opsiyonel `tutar` beyani: yanlis tutar YAZDIRMAZ, dogru tutar gecirir.
  const envT = mockEnv(satir("havale-bekliyor"));
  const t = await onayCagir(envT, { siparis_no: SIPARIS_NO, dekont_ref: REF, tutar: 1 });
  ol("b", "yanlis `tutar` beyani -> 400 'tutar-uyusmuyor' + YAZMA YOK",
    t.kod === 400 && t.govde && t.govde.hata === "tutar-uyusmuyor" &&
    envT.yazmalar.length === 0, "kod=" + t.kod + " hata=" + (t.govde && t.govde.hata));
  const envT2 = mockEnv(satir("havale-bekliyor"));
  const t2 = await onayCagir(envT2,
    { siparis_no: SIPARIS_NO, dekont_ref: REF, tutar: 43290 + 25000 });
  ol("b", "DOGRU `tutar` beyani (urun+kargo kurus) -> 200 (para alani DEGISMEZ)",
    t2.kod === 200 && envT2.satir.tutar_kurus === 43290 && envT2.satir.kargo_kurus === 25000,
    "kod=" + t2.kod);
}

// ============================================================ (c) BASARILI ONAY
console.log("\n(c) BASARILI ONAY — durum 'odendi', referans D1'de, gecmiste 'odendi'");
let basarili = null;
{
  const env = mockEnv(satir("havale-bekliyor"));
  const r = await onayCagir(env, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  basarili = r;
  ol("c", "200 + {ok:true, durum:'odendi'}",
    r.kod === 200 && r.govde && r.govde.ok === true && r.govde.durum === "odendi",
    "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
  const up = env.yazmalar.find((y) => /^UPDATE siparisler/.test(y.sql));
  ol("c", "TEK bir UPDATE siparisler kostu", !!up && env.yazmalar.length === 1,
    "yazma=" + env.yazmalar.length);
  ol("c", "UPDATE 'havale_dekont_ref = ?' kolonunu YAZIYOR",
    !!up && /havale_dekont_ref = \?/.test(up.sql), up ? up.sql : "(UPDATE yok)");
  ol("c", "CAS korunuyor: UPDATE ... WHERE siparis_no = ? AND durum = ?",
    !!up && /WHERE siparis_no = \? AND durum = \?/.test(up.sql), up ? up.sql : "-");
  ol("c", "D1 satirinda durum='odendi' ve referans SAKLANDI",
    env.satir.durum === "odendi" && env.satir.havale_dekont_ref === REF,
    "durum=" + env.satir.durum);
  let gecmis = [];
  try { gecmis = JSON.parse(env.satir.durum_gecmisi) || []; } catch (e) { gecmis = []; }
  ol("c", "durum_gecmisi'nde 'odendi' GORUNUYOR",
    gecmis.some((g) => g.d === "odendi"), env.satir.durum_gecmisi);
  ol("c", "durum_gecmisi'ne olcum izi ('o':1) yazildi (3. idempotens katmani)",
    gecmis.slice(-1)[0] && gecmis.slice(-1)[0].o === 1, env.satir.durum_gecmisi);
  ol("c", "kargo kolonlarina DOKUNULMUYOR",
    !!up && !/kargo_kodu/.test(up.sql) && !/kargo_firma/.test(up.sql),
    up ? up.sql : "-");
}

// ============================================================ (d) OLCUM GITTI
console.log("\n(d) OLCUM GITTI — Purchase, kaynak='havale', event_id=siparis_no");
{
  const meta = metaCagrilari(basarili.cagrilar);
  const ga4 = ga4Cagrilari(basarili.cagrilar);
  ol("d", "Meta CAPI'ye Purchase GONDERILDI (tam 1 cagri)", meta.length === 1,
    "cagri=" + meta.length);
  ol("d", "GA4'e Purchase GONDERILDI (tam 1 cagri)", ga4.length === 1,
    "cagri=" + ga4.length);
  const BOS = { data: [{ user_data: {}, custom_data: {} }] };
  const d = ((meta[0] || {}).govde || BOS).data[0];
  ol("d", "event_id === siparis_no (kart akisiyla AYNI dedup anahtari)",
    d.event_id === SIPARIS_NO, "event_id=" + d.event_id);
  ol("d", "event_name 'Purchase' + currency TRY + value = urun+kargo (682.9)",
    d.event_name === "Purchase" && d.custom_data.currency === "TRY" &&
    d.custom_data.value === 682.9, JSON.stringify(d.custom_data));
  const g4 = ((ga4[0] || {}).govde || { events: [{ params: {} }] }).events[0].params;
  ol("d", "GA4 transaction_id === siparis_no", g4.transaction_id === SIPARIS_NO,
    "transaction_id=" + g4.transaction_id);
  const metin = basarili.loglar.join("\n");
  ol("d", "olcumLog satirinda kaynak='havale'", metin.indexOf("\"kaynak\":\"havale\"") >= 0,
    metin);
  ol("d", "olcumLog satirinda siparis_no (=event_id) var",
    metin.indexOf("\"siparis_no\":\"" + SIPARIS_NO + "\"") >= 0, metin);
  // 🔒 Havalede istek OKAN'in tarayicisindan gelir -> IP/UA MUSTERIYE AIT DEGIL.
  ol("d", "Okan'in IP/UA'si Meta'ya GITMEZ (havale kolu istemci TASIMAZ)",
    !("client_ip_address" in d.user_data) && !("client_user_agent" in d.user_data),
    JSON.stringify(d.user_data));
  // KANAL KAPISI: WhatsApp siparisi olcume GIRMEZ (site ROI raporu sismesin).
  const envW = mockEnv(satir("havale-bekliyor", { kanal: "whatsapp" }));
  const w = await onayCagir(envW, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  ol("d", "kanal='whatsapp' -> gecis 200 ama olcum GITMEZ + 'site-disi-kanal' loglanir",
    w.kod === 200 && envW.satir.durum === "odendi" &&
    metaCagrilari(w.cagrilar).length === 0 && ga4Cagrilari(w.cagrilar).length === 0 &&
    w.loglar.join("\n").indexOf("site-disi-kanal") >= 0,
    "kod=" + w.kod + " meta=" + metaCagrilari(w.cagrilar).length);
}

// ============================================================ (e) IDEMPOTENS
console.log("\n(e) IDEMPOTENS — ayni cagri iki kez: ikincide olcum TEKRAR GITMEZ");
{
  const env = mockEnv(satir("havale-bekliyor"));
  const bir = await onayCagir(env, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  const iki = await onayCagir(env, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  ol("e", "1. cagri 200 ve olcum GITTI (taban)",
    bir.kod === 200 && metaCagrilari(bir.cagrilar).length === 1, "kod=" + bir.kod);
  ol("e", "2. cagri 400 'gecersiz-gecis' (durum artik 'odendi')",
    iki.kod === 400 && iki.govde && iki.govde.hata === "gecersiz-gecis",
    "kod=" + iki.kod + " hata=" + (iki.govde && iki.govde.hata));
  ol("e", "2. cagrida Meta/GA4'e HICBIR istek GITMEDI",
    metaCagrilari(iki.cagrilar).length === 0 && ga4Cagrilari(iki.cagrilar).length === 0,
    "meta=" + metaCagrilari(iki.cagrilar).length);
  ol("e", "2. cagrida IKINCI bir UPDATE kosmadi (toplam 1 yazma)",
    env.yazmalar.length === 1, "yazma=" + env.yazmalar.length);

  // 3. KATMAN AYRI OLCULUR: 'havale-bekliyor' satirinda ZATEN olcum izi varsa gecis
  // yapilir ama Purchase TEKRARLANMAZ (CAS/durum makinesi bu turda devrede DEGIL).
  const envIz = mockEnv(satir("havale-bekliyor", {
    durum_gecmisi: JSON.stringify([{ d: "odendi", z: "2026-08-24T09:00:00Z", o: 1 },
                                   { d: "havale-bekliyor", z: "2026-08-24T09:30:00Z" }]),
  }));
  const izli = await onayCagir(envIz, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  ol("e", "kalici iz ('o':1) VARSA gecis 200 ama Purchase GITMEZ",
    izli.kod === 200 && envIz.satir.durum === "odendi" &&
    metaCagrilari(izli.cagrilar).length === 0 && ga4Cagrilari(izli.cagrilar).length === 0,
    "kod=" + izli.kod + " meta=" + metaCagrilari(izli.cagrilar).length);
  ol("e", "atlama SESSIZ DEGIL: 'zaten-denendi' loglanir",
    izli.loglar.join("\n").indexOf("zaten-denendi") >= 0, izli.loglar.join("\n"));
  let gIz = [];
  try { gIz = JSON.parse(envIz.satir.durum_gecmisi) || []; } catch (e) { gIz = []; }
  ol("e", "iz turunda YENI bir 'o':1 izi YAZILMAZ",
    gIz.slice(-1)[0] && gIz.slice(-1)[0].d === "odendi" && gIz.slice(-1)[0].o !== 1,
    JSON.stringify(gIz.slice(-1)[0]));
}

// ============================================================ (f) NEGATIF KONTROL
console.log("\n(f) 🔴 NEGATIF KONTROL — /durum'dan 'havale-bekliyor' -> 'odendi' HALA 400");
{
  const env = mockEnv(satir("havale-bekliyor"));
  const r = await durumCagir(env, "odendi");
  ol("f", "/durum 'havale-bekliyor' -> 'odendi' = 400 'odeme-durumu-elle-setlenemez'",
    r.kod === 400 && r.govde && r.govde.hata === "odeme-durumu-elle-setlenemez",
    "kod=" + r.kod + " hata=" + (r.govde && r.govde.hata));
  ol("f", "/durum reddinde D1'e YAZMA YOK, durum 'havale-bekliyor' KALDI",
    env.yazmalar.length === 0 && env.satir.durum === "havale-bekliyor",
    "yazma=" + env.yazmalar.length + " durum=" + env.satir.durum);
  // Diger odeme durumlari da /durum'dan KAPALI kalmali (K252 ekseni butun olarak durur).
  for (const hedef of ["bekliyor", "basarisiz", "incele", "havale-bekliyor"]) {
    const e2 = mockEnv(satir("uretimde"));
    const x = await durumCagir(e2, hedef);
    ol("f", "/durum 'uretimde' -> '" + hedef + "' = 400 (odeme ekseni elle setlenemez)",
      x.kod === 400 && x.govde && x.govde.hata === "odeme-durumu-elle-setlenemez",
      "kod=" + x.kod + " hata=" + (x.govde && x.govde.hata));
  }
  // GERI ALMA ISTISNASI DOKUNULMADI: {uretimde,kargolandi,tamamlandi} -> 'odendi' 200.
  for (const mevcut of ["uretimde", "kargolandi", "tamamlandi"]) {
    const e3 = mockEnv(satir(mevcut));
    const x = await durumCagir(e3, "odendi");
    ol("f", "ODENDI_GERI_ALMA korunuyor: '" + mevcut + "' -> 'odendi' = 200",
      x.kod === 200 && x.govde && x.govde.durum === "odendi", "kod=" + x.kod);
  }
}

// ============================================================ (h) SEMA PARITESI
console.log("\n(h) SEMA PARITESI — kolon d1-sema.sql'de VE GOC_KOLON_SIPARIS'te");
{
  const KOLON = "havale_dekont_ref";
  const semaYol = path.join(KOK, "tools", "d1-sema.sql");
  const syncYol = path.join(KOK, "tools", "d1-sync.py");
  let sema = "", sync = "";
  try { sema = fs.readFileSync(semaYol, "utf8"); } catch (e) { sema = ""; }
  try { sync = fs.readFileSync(syncYol, "utf8"); } catch (e) { sync = ""; }
  const b = sema.indexOf("CREATE TABLE IF NOT EXISTS siparisler (");
  const son = b >= 0 ? sema.indexOf("\n);", b) : -1;
  if (b < 0 || son < 0) {
    console.error("KAYNAK CAPASI BULUNAMADI (d1-sema.sql siparisler DDL) — OLCULEMEDI");
    process.exit(3);
  }
  const ddl = sema.slice(b, son);
  ol("h", "d1-sema.sql CREATE TABLE siparisler kolonu TASIYOR (DEFAULT '')",
    new RegExp(KOLON + "\\s+TEXT NOT NULL DEFAULT ''").test(ddl), "-");
  const gb = sync.indexOf("GOC_KOLON_SIPARIS = [");
  const gs = gb >= 0 ? sync.indexOf("\n]", gb) : -1;
  if (gb < 0 || gs < 0) {
    console.error("KAYNAK CAPASI BULUNAMADI (d1-sync.py GOC_KOLON_SIPARIS) — OLCULEMEDI");
    process.exit(3);
  }
  const gocBlok = sync.slice(gb, gs);
  // 🔴 IKI KAYNAK TEK GERCEK: kolon YALNIZ CREATE'te olursa CANLIDA HIC OLUSMAZ (tablo
  // zaten var -> CREATE atlanir), yani uc kalici 503 verirdi.
  ol("h", "d1-sync.py GOC_KOLON_SIPARIS ayni kolonu AYNI tanimla TASIYOR",
    new RegExp("\\(\"" + KOLON + "\", \"TEXT NOT NULL DEFAULT ''\"\\)").test(gocBlok), "-");
  // Kolon uzerinde d1-sema.sql'de INDEKS OLMAMALI (goc sirasi tuzagi — 1 Agu 2026).
  const indeksSatirlari = sema.split("\n").filter(
    (l) => /CREATE .*INDEX/i.test(l) && l.indexOf(KOLON) >= 0);
  ol("h", "d1-sema.sql bu kolon uzerinde INDEKS TANIMLAMIYOR (--sema tikanmasin)",
    indeksSatirlari.length === 0, indeksSatirlari.join(" | "));
}

// ============================================================ (i) GIZLILIK
console.log("\n(i) GIZLILIK — dekont referansi log'a / hata metnine / yanita GIRMEZ");
{
  const metin = basarili.loglar.join("\n");
  ol("i", "basarili onayin HICBIR log satirinda referans GECMIYOR",
    metin.indexOf(REF) < 0, "-");
  ol("i", "basarili onay YANITINDA referans YOK",
    JSON.stringify(basarili.govde).indexOf(REF) < 0, JSON.stringify(basarili.govde));
  ol("i", "Meta/GA4 govdesinde referans GECMIYOR (olcum yuku finansal veri tasimaz)",
    JSON.stringify(basarili.cagrilar).indexOf(REF) < 0, "-");
  // Cok uzun referans reddinde de deger yankilanmamali.
  const envU = mockEnv(satir("havale-bekliyor"));
  const uzun = "Z".repeat(200);
  const u = await onayCagir(envU, { siparis_no: SIPARIS_NO, dekont_ref: uzun });
  ol("i", "RED yanitinda/loglarinda gonderilen referans YANKILANMIYOR",
    JSON.stringify(u.govde).indexOf(uzun) < 0 && u.loglar.join("\n").indexOf(uzun) < 0,
    JSON.stringify(u.govde));
  // Sema-goc penceresinde de sizinti olmamali (o kol console.error yaziyor).
  const envK = mockEnv(satir("havale-bekliyor"), { kolonVar: false });
  const k = await onayCagir(envK, { siparis_no: SIPARIS_NO, dekont_ref: REF });
  ol("i", "503 sema-goc kolunda da referans loglanmiyor",
    k.loglar.join("\n").indexOf(REF) < 0 && JSON.stringify(k.govde).indexOf(REF) < 0, "-");
  ol("i", "olcum secret'leri loga SIZMIYOR",
    metin.indexOf(ENV_OLCUM.META_CAPI_TOKEN) < 0 &&
    metin.indexOf(ENV_OLCUM.GA4_API_SECRET) < 0, "-");
}

// ============================================================ (j) PANEL
console.log("\n(j) PANEL — form YALNIZ 'havale-bekliyor' kartinda; secici HALA TURETILIR");

/** Kaynaktan [baslangic, bitis) dilimi. Capa yoksa null (fail-loud). */
function dilimAl(metin, baslangic, bitis) {
  const b = metin.indexOf(baslangic);
  const s = b >= 0 ? metin.indexOf(bitis, b + baslangic.length) : -1;
  return (b >= 0 && s > b) ? metin.slice(b, s) : null;
}
function sablonCoz(s) { return s.replace(/\\\\/g, "\\"); }

{
  const panelKaynak = sablonCoz(dilimAl(KAYNAK, "function esc(s){", "async function yukle(){") || "");
  if (!panelKaynak) {
    console.error("KAYNAK CAPASI BULUNAMADI (sayfa JS blogu) — yonet.js yapisi degisti mi?");
    process.exit(3);
  }
  const panel = { document: null };
  vm.createContext(panel);
  vm.runInContext(panelKaynak, panel, { filename: "yonet-sayfa.js" });
  const kartHtml = panel.kartHtml;
  if (typeof kartHtml !== "function") {
    console.error("SAYFA FONKSIYONU CEKILEMEDI (kartHtml) — OLCULEMEDI");
    process.exit(3);
  }
  function kartFikstur(mevcut, izinli) {
    return {
      siparis_no: "PR-TEST-" + mevcut, tarih: "2026-08-24T10:00:00Z", durum: mevcut,
      kanal: "site", dis_no: "", odeme_yontemi: "havale",
      tutar_kurus: 43290, kargo_kurus: 25000, kdv_kurus: 11381,
      kargo_firma: "", kargo_kodu: "", durum_gecmisi: [], izinli_gecisler: izinli || [],
      musteri: { ad: "Ornek Musteri", tel: "0500 000 00 00",
                 eposta: "ornek@ornek.invalid", adres: "Ornek Mah. 1" },
      kalemler: [], musteri_notu: "", yazdir_komut: "python3 tools/yazdir.py PR-TEST",
    };
  }
  const TUM = ["bekliyor", "odendi", "basarisiz", "incele", "havale-bekliyor",
               "uretimde", "kargolandi", "tamamlandi", "iptal"];
  const formlu = TUM.filter((d) => /havaleOnayla\(/.test(kartHtml(kartFikstur(d))));
  ol("j", "havale onay formu YALNIZ 'havale-bekliyor' kartinda basiliyor",
    formlu.length === 1 && formlu[0] === "havale-bekliyor", "formlu=" + formlu.join(","));
  const hb = kartHtml(kartFikstur("havale-bekliyor"));
  ol("j", "formda dekont/referans girdisi + onay butonu VAR",
    /<input id="hd-/.test(hb) && /Havale onayla/.test(hb), "-");
  ol("j", "kargo formu 'havale-bekliyor' kartinda basilmiyor (iki form karismiyor)",
    !/Kargolandı olarak işaretle/.test(hb), "-");
  ol("j", "kargo formu 'uretimde' kartinda AYNEN duruyor (regresyon yok)",
    /Kargolandı olarak işaretle/.test(kartHtml(kartFikstur("uretimde"))), "-");
  // 🔴 IKINCI DURUM LISTESI YASAGI (K252 ⑦b ile AYNI eksen): secenek uretimi
  // DEGISMEDI — havale formu o blogun DISINDA yasar.
  const secenekBlok = dilimAl(panelKaynak, " var secenekler=", " var eylem=") || "";
  if (!secenekBlok) {
    console.error("KAYNAK CAPASI BULUNAMADI (secenek uretimi) — kartHtml yapisi degisti mi?");
    process.exit(3);
  }
  const durumLiterali = (secenekBlok.match(
    /"(bekliyor|odendi|basarisiz|incele|havale-bekliyor|uretimde|kargolandi|tamamlandi|iptal)"/g) || []);
  ol("j", "secenek uretiminde ELLE yazilmis durum literali YOK (kume HALA TURETILIR)",
    durumLiterali.length === 0, "literaller=" + durumLiterali.join(","));
  ol("j", "secenek uretiminin TEK kaynagi `s.izinli_gecisler`",
    /s\.izinli_gecisler\.map\(/.test(secenekBlok) && !/concat\(|\[\s*"/.test(secenekBlok),
    secenekBlok.trim().slice(0, 160));
  // Panelin uce gonderdigi yol + gizlilik: referans yanittan OKUNMUYOR.
  const gonderici = dilimAl(KAYNAK, "async function havaleOnayla(no){", "\nfunction komutKopyala");
  ol("j", "istemci `/havale-onay` ucuna `dekont_ref` ile POST ediyor",
    !!gonderici && /api\("\/havale-onay"/.test(gonderici) && /dekont_ref:/.test(gonderici),
    gonderici ? gonderici.slice(0, 200) : "(capa yok)");
  ol("j", "kart HTML'i sunucudan gelen bir referans DEGERINI BASMIYOR",
    !/dekont/i.test(hb.replace(/id="hd-[^"]*"/g, "").replace(/havaleOnayla\([^)]*\)/g, "")
      .replace(/placeholder="[^"]*"/g, "")), "-");
}

// ================================================================ SONUC
console.log("\nTOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
console.log("OLEN_IDDIALAR=" + (olen.size ? [...olen].sort().join(",") : "-"));
process.exit(kalan === 0 ? 0 : 1);
