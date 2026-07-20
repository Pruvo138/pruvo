#!/usr/bin/env node
/**
 * PRUVO shop — REKLAM ROI OLCUMU BIRIM TESTLERI (server-side Purchase event).
 * Is paketi: /Users/okan/dev/pruvo-pazarlama/reklam-roi-sistemi.md §1 (Faz 0).
 *
 *   node shop/test/olcum.mjs
 *
 * olcum.js'i DOGRUDAN import eder (worker/wrangler'siz, hizli). Kapsam:
 *  - satinAlmaOlayi: currency="TRY" (KRITIK — yoksa Meta USD sayar ~30x sisme), value=GERCEK
 *    tahsilat (urun+kargo, kurus->TRY), event_id=order_id=transaction_id=siparis_no (dedup), items.
 *  - Meta CAPI + GA4 MP govdeleri: TRY + value + event_id/transaction_id + items + atif (fbp/fbc/
 *    client_id/utm) dogru yerlere.
 *  - SECRET-YOKSA-NO-OP: token/anahtar yoksa hedef sessizce atlanir, fetch HIC cagrilmaz.
 *  - POST-HATASI-SIPARISI-BOZMAZ: fetch patlasa/timeout verse olcumGonder FIRLATMAZ, promise COZULUR.
 *
 * 20 TEM EKI — mimar dogrulama turunda bulunan 3 acik (T14-T20):
 *  - ACIK 1 (sessiz hata): Meta/GA4 yaniti hicbir yere yazilmiyordu; fetch 4xx'te THROW
 *    ETMEZ -> HTTP 400 sessizce yutuluyordu. T15: 400 loglaniyor (kod + hata govdesi +
 *    fbtrace_id + siparis no), basari da tek satir. T20: logda token/PII YOK (negatif test).
 *  - ACIK 2 (eslesme kalitesi): IP/UA hic gonderilmiyordu. T14: fbp VARSA gonderilir,
 *    fbp YOKSA gonderilmez (riza kurali). T16: user_data bos kalirsa Meta'ya gonderilmez
 *    + loglanir (Meta zaten error 100/2804003 ile reddederdi), GA4 etkilenmez.
 *  - ACIK 3 (havale cirosu): havale 'odendi'de HIC Purchase gitmiyordu. T18: yonet.js
 *    /durum -> Purchase, event_id = siparis_no, event_time = gercek odeme ani, Okan'in
 *    IP/UA'si GITMEZ. T19: idempotens (tek olay). T17: 7 gunluk pencere disi -> atla + logla.
 *
 * 20 TEM 2. TUR — mimar kabul denetiminin istedigi duzeltmeler (T21-T24 + T14 eki):
 *  - fbc ARTIK KAPIDA: fbp yoksa fbc de gitmez (T14e/14e2/14e3). Denetci zinciri: index.html
 *    fbclid'i rizasiz localStorage'a yaziyordu -> "Reddet"e basmis ziyaretcinin tiklama
 *    kimligi Meta'ya ulasabiliyordu. Yakalama tarafi AYRI is; burada CIKIS kapatildi.
 *  - T21: kabul.js olcum kapisi (shop/test/olcum-kapisi.cjs) — yerel test GERCEK piksele
 *    basamaz; gercek CAPI token'i/GA4 secret'i gorulurse test KOSMAYI REDDEDER.
 *  - T22: index.js KART yolunun IP/UA kablolamasi uctan uca (sahte D1 + sahte iyzico +
 *    sahte Meta). Kablolama koparsa kirmizi — onceden hicbir test bunu tutmuyordu.
 *  - T23: sirMaskele'nin KENDISI (yanit govdesinde token gecerse maskeleniyor mu).
 *  - T24: GERCEK eszamanlilik — mandalli sahte D1 ile iki es zamanli 'odendi'; CAS
 *    kalkarsa cift Purchase gider ve blok kirmizi yanar.
 *
 * 20 TEM 3. TUR — dogrulayicilarin buldugu 4 acik:
 *  - T25 (🔴 YUKSEK): BASARISIZ odemede Purchase gitmedigini koruyan test YOKTU. Taban kod
 *    dogruydu ama `det.paymentStatus === "SUCCESS"` kapisi gevserse karti REDDEDILEN musteri
 *    icin GERCEK TUTARLI SAHTE Purchase gider ve paket yesil kalirdi. Artik kart reddi /
 *    3DS-bekleyen / alan-eksik / kucuk-harf 'success' / retrieve-hatasi / tutar-uyusmazligi
 *    icin 0 POST + `atlandi` logu sinaniyor (+ olumlu kontrol 25p).
 *  - T21 eki: fail-closed kapi `.env` ve `.env.local`'a KORDU. wrangler 4.112 `.dev.vars`
 *    yoksa bunlari SECRET olarak yukluyor; kok .gitignore `.env*` yok saydigi icin sirri
 *    koymanin "dogal" yeri tam orasi. Kapi artik uc dosyayi da tariyor (precedence TAKLIT
 *    EDILMEZ — hangisinde gorurse reddeder).
 *  - T24f (nobetci): mandal devre disi kalirsa istekler SIRALANIR, tek Purchase gider ve
 *    "cift ciro yok" diyen 24c/24d mutasyondan bagimsiz yesil kalirdi (para iddialari sessizce
 *    nobetten duserdi). 24f yaris penceresinin GERCEKTEN acildigini ayrica sinar; pencere
 *    kapanirsa ADI DOGRU olan bir test kirmizi yanar.
 *  - Belgeler: kapi kapsami artik "her yol" degil, TARANAN + TARANMAYAN kaynaklar tek tek yazili.
 *
 * ONCE-KIRMIZI (elle kanitlandi — her duzeltme tek tek geri alinip olculdu):
 *  - olcum.js'te currency "TRY" -> "USD" yapilinca T1/T5/T7 KIRMIZI.
 *  - metaGonder/ga4Gonder'daki "secret yoksa return" satiri silinince (no-op bozulunca) T9/T10 KIRMIZI.
 *  - metaGovdesi'ndeki `atif.fbp &&` riza sarti silinince -> 3 KIRMIZI (14c/14d/14f).
 *  - metaGonder'daki hata olcumLog'u silinince -> 5 KIRMIZI (15b-15f).
 *  - yonet.js havaleOlcumu() cagrisi silinince -> 10 KIRMIZI (18b-18m).
 *  - yonet.js olcumDenendiMi() kontrolu silinince -> 2 KIRMIZI (19e/19f).
 *  - LOG_ALANLARI beyaz listesine token alani eklenince -> 1 KIRMIZI (20b).
 *  - fbc kapi disina alininca (eski davranis) -> 3 KIRMIZI (14e/14e2/14e3).
 *  - olcum-kapisi TEHLIKELI_ANAHTARLAR bosaltilinca -> 4 KIRMIZI (21f-21i).
 *  - test piksel override'i GERCEK piksele esitlenince -> 5 KIRMIZI (21a/21c/21e/21j/21k).
 *  - index.js kart yolu istemci{ip,ua} kablolamasi koparilinca -> 2 KIRMIZI (22d/22e).
 *  - sirMaskele govdesi etkisizlestirilince -> 3 KIRMIZI (23a/23b/23d).
 *  - yonet.js UPDATE'inden "AND durum = ?" (CAS) silinince -> 5 KIRMIZI (24a/24b/24c/24d/24g).
 *  - index.js'te `paymentStatus === "SUCCESS"` -> `true` yapilinca -> 8 KIRMIZI (25a-25i).
 *  - ayni karsilastirma buyuk/kucuk harf DUYARSIZ yapilinca -> 1 KIRMIZI (25i).
 *  - kapi TARANAN_DOSYALAR'dan ".env" cikarilinca -> 4 KIRMIZI (21l/21m/21p/21r).
 *  - ".env.local" cikarilinca -> 3 KIRMIZI (21n/21o/21r); ikisi birden -> 6 KIRMIZI.
 *  - yaris penceresi kapatilinca (okumalar sirlanir) -> 24f + 24b KIRMIZI. (Mandal esigini
 *    2->1 yapmak DAVRANIS KORUYUCUDUR: pencere yine acilir, CAS silinince 24c/24d yine
 *    kirmizi yanar — olculdu, "yakalanmadi" sanilmasin.)
 */

import * as nodeModule from "node:module";
import {
  satinAlmaOlayi, metaGovdesi, ga4Govdesi, metaGonder, ga4Gonder, olcumGonder, kurusTRY,
} from "../src/olcum.js";
// kabul.js'in kullandigi FAIL-CLOSED olcum kapisi (CJS) — burada birim testi yapilir (T21).
import kapiModulu from "./olcum-kapisi.cjs";
const { olcumKapisi } = kapiModulu;

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

/** Konsol ciktisini YAKALA (log gizlilik testleri + "hata yutulmuyor" testi icin).
 *  console.log/error gecici olarak degistirilir; satirlar dizi olarak doner. */
async function logYakala(fn) {
  const satirlar = [];
  const l = console.log, e = console.error;
  console.log = (...a) => { satirlar.push({ akis: "log", metin: a.join(" ") }); };
  console.error = (...a) => { satirlar.push({ akis: "error", metin: a.join(" ") }); };
  try { await fn(); } finally { console.log = l; console.error = e; }
  return satirlar;
}
function logMetni(satirlar) { return satirlar.map((s) => s.metin).join("\n"); }

// Ornek siparis: urun 432,90 TL + kargo 250,00 TL = tahsilat 682,90 TL.
const SIPARIS = {
  siparis_no: "PR-260718-120000-ABC",
  tutar_kurus: 43290,
  kargo_kurus: 25000,
  urunler: JSON.stringify([
    { id: "audi-yakit-kapagi", baslik: "Audi Yakıt Kapağı", kategori: "Otomobil",
      adet: 2, birim_kurus: 21645, tutar_kurus: 43290 },
  ]),
  atif: JSON.stringify({
    ga_client_id: "1234567890.1690000000", fbp: "fb.1.1690.pixel", fbc: "fb.1.1690.click",
    utm_source: "google", utm_medium: "cpc", utm_campaign: "kirik-parca", utm_id: "17999",
  }),
};
const BEKLENEN_DEGER = 682.9;   // (43290 + 25000) / 100

function sahteFetch() {
  const cagrilar = [];
  const f = async (url, opt) => {
    cagrilar.push({ url: url, govde: opt && opt.body ? JSON.parse(opt.body) : null });
    return { status: 200 };
  };
  f.cagrilar = cagrilar;
  return f;
}
async function patlayanFetch() { throw new Error("ag hatasi (timeout)"); }

// ---- 1) KANONIK OLAY: currency=TRY (kritik), value=gercek tahsilat, dedup kimlikleri ----
{
  const o = satinAlmaOlayi(SIPARIS);
  ol("1a currency === 'TRY' (KRITIK)", o.currency === "TRY", "currency=" + o.currency);
  ol("1b value === gercek tahsilat (urun+kargo)", o.value === BEKLENEN_DEGER, "value=" + o.value);
  ol("1c event_id === siparis_no (dedup)", o.event_id === SIPARIS.siparis_no);
  ol("1d order_id === transaction_id === event_id",
    o.order_id === o.event_id && o.transaction_id === o.event_id);
}

// ---- 2) ITEMS: sepet kalemleri dogru (id, ad, adet, birim TRY, kategori) ----
{
  const o = satinAlmaOlayi(SIPARIS);
  ol("2a tek kalem", o.items.length === 1, "n=" + o.items.length);
  const it = o.items[0] || {};
  ol("2b item_id", it.item_id === "audi-yakit-kapagi");
  ol("2c quantity", it.quantity === 2, "q=" + it.quantity);
  ol("2d birim price TRY (21645 -> 216.45)", it.price === 216.45, "price=" + it.price);
  ol("2e item_category", it.item_category === "Otomobil");
}

// ---- 3) KURUS -> TRY: tamsayi aritmetigi, float toplamasi degil ----
{
  ol("3a 43290 -> 432.9", kurusTRY(43290) === 432.9);
  ol("3b 0 -> 0", kurusTRY(0) === 0);
  ol("3c 5 -> 0.05", kurusTRY(5) === 0.05);
}

// ---- 4) BOZUK/EKSIK VERI: patlamaz, makul deger ----
{
  const o = satinAlmaOlayi({ siparis_no: "PR-X", tutar_kurus: 10000, urunler: "bozuk-json{" });
  ol("4a bozuk urunler -> bos items (cokme yok)", Array.isArray(o.items) && o.items.length === 0);
  ol("4b kargo yoksa value = urun tutari", o.value === 100);
  ol("4c currency yine TRY", o.currency === "TRY");
}

// ---- 5) META GOVDESI: Purchase + TRY + value + event_id + fbp/fbc + contents ----
{
  const olay = satinAlmaOlayi(SIPARIS);
  const atif = JSON.parse(SIPARIS.atif);
  const g = metaGovdesi({ SITE_URL: "https://pruvo3d.com" }, olay, atif);
  const d = g.data[0];
  ol("5a event_name Purchase", d.event_name === "Purchase");
  ol("5b custom_data.currency === 'TRY'", d.custom_data.currency === "TRY");
  ol("5c custom_data.value === tahsilat", d.custom_data.value === BEKLENEN_DEGER);
  ol("5d event_id === siparis_no (piksel dedup)", d.event_id === SIPARIS.siparis_no);
  ol("5e user_data.fbp + fbc atif'ten", d.user_data.fbp === "fb.1.1690.pixel" && d.user_data.fbc === "fb.1.1690.click");
  ol("5f content_ids urun id", (d.custom_data.content_ids || []).indexOf("audi-yakit-kapagi") >= 0);
  ol("5g contents item_price TRY", (d.custom_data.contents[0] || {}).item_price === 216.45);
}

// ---- 6) META TEST EVENT CODE: env verilince govdeye girer (Okan canli kabul) ----
{
  const olay = satinAlmaOlayi(SIPARIS);
  const g = metaGovdesi({ META_TEST_EVENT_CODE: "TEST123" }, olay, {});
  ol("6a test_event_code env'den", g.test_event_code === "TEST123");
  const g2 = metaGovdesi({}, olay, {});
  ol("6b env yoksa test_event_code YOK", !("test_event_code" in g2));
}

// ---- 7) GA4 GOVDESI: purchase + TRY + transaction_id + client_id + items + utm ----
{
  const olay = satinAlmaOlayi(SIPARIS);
  const atif = JSON.parse(SIPARIS.atif);
  const g = ga4Govdesi({}, olay, atif);
  ol("7a client_id === gercek _ga client_id (atif)", g.client_id === "1234567890.1690000000");
  const ev = g.events[0];
  ol("7b event name purchase", ev.name === "purchase");
  ol("7c params.currency === 'TRY'", ev.params.currency === "TRY");
  ol("7d params.value === tahsilat", ev.params.value === BEKLENEN_DEGER);
  ol("7e transaction_id === siparis_no", ev.params.transaction_id === SIPARIS.siparis_no);
  ol("7f items dolu", (ev.params.items || []).length === 1);
  ol("7g utm -> source/medium/campaign", ev.params.source === "google" &&
    ev.params.medium === "cpc" && ev.params.campaign === "kirik-parca");
}

// ---- 8) GA4 client_id FALLBACK: gercek _ga yoksa siparis_no tabanli (ciro yine kaydedilir) ----
{
  const olay = satinAlmaOlayi({ ...SIPARIS, atif: "" });
  const g = ga4Govdesi({}, olay, {});
  ol("8a client_id fallback = order_id + '.0'", g.client_id === SIPARIS.siparis_no + ".0");
}

// ---- 9) SECRET-YOKSA-NO-OP (Meta): token/pixel yoksa fetch HIC cagrilmaz ----
async function test9() {
  const olay = satinAlmaOlayi(SIPARIS);
  const f = sahteFetch();
  const r1 = await metaGonder({}, olay, {}, f);                                  // hic env yok
  const r2 = await metaGonder({ META_PIXEL_ID: "123" }, olay, {}, f);            // token eksik
  const r3 = await metaGonder({ META_CAPI_TOKEN: "tok" }, olay, {}, f);          // pixel eksik
  ol("9a env yok -> atlandi", r1.atlandi === "secret-yok");
  ol("9b pixel var token yok -> atlandi", r2.atlandi === "secret-yok");
  ol("9c token var pixel yok -> atlandi", r3.atlandi === "secret-yok");
  ol("9d fetch HIC cagrilmadi (no-op)", f.cagrilar.length === 0, "cagri=" + f.cagrilar.length);
}

// ---- 10) SECRET-YOKSA-NO-OP (GA4): measurement_id/api_secret yoksa fetch cagrilmaz ----
async function test10() {
  const olay = satinAlmaOlayi(SIPARIS);
  const f = sahteFetch();
  const r1 = await ga4Gonder({}, olay, {}, f);
  const r2 = await ga4Gonder({ GA4_MEASUREMENT_ID: "G-X" }, olay, {}, f);        // secret eksik
  ol("10a env yok -> atlandi", r1.atlandi === "secret-yok");
  ol("10b mid var secret yok -> atlandi", r2.atlandi === "secret-yok");
  ol("10c fetch HIC cagrilmadi (no-op)", f.cagrilar.length === 0, "cagri=" + f.cagrilar.length);
}

// ---- 11) SECRET VARSA: gercekten POST edilir, dogru URL + TRY govde ----
async function test11() {
  const olay = satinAlmaOlayi(SIPARIS);
  const atif = JSON.parse(SIPARIS.atif);
  const fm = sahteFetch();
  await metaGonder({ META_PIXEL_ID: "2150216885710153", META_CAPI_TOKEN: "TOK" }, olay, atif, fm);
  ol("11a Meta 1 POST", fm.cagrilar.length === 1, "cagri=" + fm.cagrilar.length);
  ol("11b Meta URL pixel + access_token", (fm.cagrilar[0] || {}).url &&
    fm.cagrilar[0].url.indexOf("2150216885710153/events") >= 0 &&
    fm.cagrilar[0].url.indexOf("access_token=TOK") >= 0);
  ol("11c Meta govde currency TRY", (((fm.cagrilar[0] || {}).govde || {}).data[0]).custom_data.currency === "TRY");

  const fg = sahteFetch();
  await ga4Gonder({ GA4_MEASUREMENT_ID: "G-ABC", GA4_API_SECRET: "SEC" }, olay, atif, fg);
  ol("11d GA4 1 POST", fg.cagrilar.length === 1, "cagri=" + fg.cagrilar.length);
  ol("11e GA4 URL mid + api_secret", (fg.cagrilar[0] || {}).url &&
    fg.cagrilar[0].url.indexOf("measurement_id=G-ABC") >= 0 &&
    fg.cagrilar[0].url.indexOf("api_secret=SEC") >= 0);
  ol("11f GA4 govde currency TRY", (((fg.cagrilar[0] || {}).govde || {}).events[0]).params.currency === "TRY");
}

// ---- 12) POST-HATASI-SIPARISI-BOZMAZ: fetch patlasa olcumGonder FIRLATMAZ, promise COZULUR ----
async function test12() {
  const env = { META_PIXEL_ID: "1", META_CAPI_TOKEN: "t", GA4_MEASUREMENT_ID: "G", GA4_API_SECRET: "s" };
  let waitUntilCagrildi = false;
  const ctx = { waitUntil: function(p){ waitUntilCagrildi = true; return p; } };
  let firlatti = false, p;
  try { p = olcumGonder(env, ctx, SIPARIS, patlayanFetch); }
  catch (e) { firlatti = true; }
  ol("12a olcumGonder SENKRON firlatmaz", firlatti === false);
  ol("12b ctx.waitUntil cagrildi (fire-and-forget)", waitUntilCagrildi === true);
  let cozuldu = false;
  try { const r = await p; cozuldu = Array.isArray(r) && r.every((x) => x && x.hata); }
  catch (e) { cozuldu = false; }
  ol("12c promise COZULDU (reject DEGIL), her hedef hata yakaladi", cozuldu === true);
}

// ---- 13) BASARILI AKIS: env dolu + saglam fetch -> her iki hedefe POST, ctx.waitUntil ----
async function test13() {
  const env = { META_PIXEL_ID: "2150216885710153", META_CAPI_TOKEN: "t",
                GA4_MEASUREMENT_ID: "G-ABC", GA4_API_SECRET: "s", SITE_URL: "https://pruvo3d.com" };
  const f = sahteFetch();
  const ctx = { waitUntil: function(){} };
  await olcumGonder(env, ctx, SIPARIS, f);
  ol("13a iki hedefe de POST (Meta + GA4)", f.cagrilar.length === 2, "cagri=" + f.cagrilar.length);
  const trler = f.cagrilar.map((c) => JSON.stringify(c.govde).indexOf("\"currency\":\"TRY\"") >= 0);
  ol("13b iki govdede de currency TRY", trler.every(Boolean));
}

// ================================================================================
// MIMAR ACIKLARI 1-2-3 (20 Tem dogrulama turu) — asagidaki testler bunlari kapatir.
// ================================================================================

const ENV_TAM = {
  META_PIXEL_ID: "2150216885710153", META_CAPI_TOKEN: "GIZLI-CAPI-TOKEN-ABC123",
  GA4_MEASUREMENT_ID: "G-5V53CQMSCE", GA4_API_SECRET: "GIZLI-GA4-SECRET-XYZ789",
  SITE_URL: "https://pruvo3d.com",
};
const ISTEMCI = { ip: "203.0.113.77", ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5)" };

/** Belirli HTTP kodu + govde donduren sahte fetch (yanit govdesi loglama testleri icin). */
function kodluFetch(kod, govdeMetni) {
  const cagrilar = [];
  const f = async (url, opt) => {
    cagrilar.push({ url: url, govde: opt && opt.body ? JSON.parse(opt.body) : null });
    return { status: kod, text: async () => govdeMetni };
  };
  f.cagrilar = cagrilar;
  return f;
}

// ---- 14) ACIK 2 — IP/UA GIZLILIK KURALI: yalniz fbp VARSA gonderilir ----
async function test14() {
  const olay = satinAlmaOlayi(SIPARIS);

  // fbp VAR -> IP + UA gider (rizali ziyaretci; eslesme kalitesi yukselir).
  const g1 = metaGovdesi({}, olay, { fbp: "fb.1.1690.pixel" }, ISTEMCI).data[0];
  ol("14a fbp VARKEN client_ip_address gonderiliyor",
    g1.user_data.client_ip_address === ISTEMCI.ip, "ip=" + g1.user_data.client_ip_address);
  ol("14b fbp VARKEN client_user_agent gonderiliyor",
    g1.user_data.client_user_agent === ISTEMCI.ua);

  // fbp VARKEN fbc de gider (riza kapisi ACIK).
  const g1b = metaGovdesi({}, olay, { fbp: "fb.1.1690.pixel", fbc: "fb.1.1690.click" }).data[0];
  ol("14b2 fbp VARKEN fbc gonderiliyor", g1b.user_data.fbc === "fb.1.1690.click");

  // fbp YOK (yalniz fbc var) -> HICBIRI gitmez. Riza kaniti fbp'dir; fbc tek basina yetmez.
  // ⚠️ MIMAR KARARI (20 Tem): fbc de AYNI kapiya bagli — "Reddet"e basmis reklam
  // ziyaretcisinin tiklama kimligi (fbclid) Meta'ya ULASMAMALI.
  const g2 = metaGovdesi({}, olay, { fbc: "fb.1.1690.click" }, ISTEMCI).data[0];
  ol("14c fbp YOKKEN client_ip_address GONDERILMIYOR (gizlilik kurali)",
    !("client_ip_address" in g2.user_data), JSON.stringify(g2.user_data));
  ol("14d fbp YOKKEN client_user_agent GONDERILMIYOR (gizlilik kurali)",
    !("client_user_agent" in g2.user_data));
  ol("14e fbp YOKKEN fbc de GONDERILMIYOR (rizasiz tiklama kimligi cikmaz)",
    !("fbc" in g2.user_data), JSON.stringify(g2.user_data));
  ol("14e2 fbp YOKKEN user_data TAMAMEN bos (tek kapi)",
    Object.keys(g2.user_data).length === 0, JSON.stringify(g2.user_data));

  // Uctan uca: fbp'siz + fbc'li siparis Meta'ya HIC gitmemeli (user_data bos -> atlanir).
  const fbcSiparis = { ...SIPARIS, atif: JSON.stringify({ fbc: "fb.1.1690.click",
    ga_client_id: "1.2", utm_source: "facebook" }) };
  const fFbc = kodluFetch(200, "{\"events_received\":1}");
  await logYakala(() => olcumGonder(ENV_TAM, null, fbcSiparis, fFbc, { istemci: ISTEMCI }));
  ol("14e3 uctan uca: fbp'siz/fbc'li sipariste Meta'ya POST YOK",
    fFbc.cagrilar.filter((c) => String(c.url).indexOf("graph.facebook.com") >= 0).length === 0,
    "cagri=" + fFbc.cagrilar.length);

  // Atif tamamen bos -> user_data BOS kalir, IP/UA sizmaz.
  const g3 = metaGovdesi({}, olay, {}, ISTEMCI).data[0];
  ol("14f atif bos -> user_data TAMAMEN bos (IP/UA sizmaz)",
    Object.keys(g3.user_data).length === 0, JSON.stringify(g3.user_data));

  // istemci hic verilmezse (havale akisi) fbp olsa da IP/UA yok.
  const g4 = metaGovdesi({}, olay, { fbp: "fb.1.1690.pixel" }).data[0];
  ol("14g istemci verilmezse IP/UA yok (havale akisi)",
    !("client_ip_address" in g4.user_data) && !("client_user_agent" in g4.user_data));

  // Uctan uca: olcumGonder -> gercekten POST edilen govdede IP/UA var mi?
  const f = kodluFetch(200, "{\"events_received\":1,\"fbtrace_id\":\"AbC\"}");
  await logYakala(() => olcumGonder(ENV_TAM, null, SIPARIS, f, { istemci: ISTEMCI, kaynak: "kart" }));
  const meta = f.cagrilar.find((c) => String(c.url).indexOf("graph.facebook.com") >= 0);
  ol("14h uctan uca: POST edilen Meta govdesinde IP+UA var",
    !!meta && meta.govde.data[0].user_data.client_ip_address === ISTEMCI.ip &&
    meta.govde.data[0].user_data.client_user_agent === ISTEMCI.ua);
}

// ---- 15) ACIK 1 — META 400 SESSIZCE YUTULMUYOR (fetch 4xx'te throw ETMEZ) ----
async function test15() {
  const olay = satinAlmaOlayi(SIPARIS);
  const atif = JSON.parse(SIPARIS.atif);
  const hataGovde = "{\"error\":{\"message\":\"Invalid parameter\",\"code\":100," +
    "\"error_subcode\":2804003,\"fbtrace_id\":\"AzXyTraceHATA\"}}";
  const f = kodluFetch(400, hataGovde);
  let sonuc;
  const satirlar = await logYakala(async () => {
    sonuc = await metaGonder(ENV_TAM, olay, atif, f, ISTEMCI, "kart");
  });
  const metin = logMetni(satirlar);
  ol("15a 400 -> ok:false donuyor (sessiz basari YOK)", sonuc.ok === false && sonuc.kod === 400,
    JSON.stringify(sonuc));
  ol("15b hata LOGLANDI (console.error)", satirlar.some((s) => s.akis === "error"),
    "satir=" + satirlar.length);
  ol("15c logda HTTP kodu var", metin.indexOf("\"kod\":400") >= 0, metin);
  ol("15d logda Meta hata govdesi var (teshis edilebilir)",
    metin.indexOf("2804003") >= 0);
  ol("15e logda fbtrace_id var (Meta destek talebi icin)",
    metin.indexOf("AzXyTraceHATA") >= 0);
  ol("15f logda event_id (=siparis_no) var — hangi siparis oldugu belli",
    metin.indexOf(SIPARIS.siparis_no) >= 0);

  // Basari yolu: TEK satir, kisa, console.log (error DEGIL).
  const f2 = kodluFetch(200, "{\"events_received\":1,\"messages\":[],\"fbtrace_id\":\"AbCiyi\"}");
  const s2 = await logYakala(async () => {
    await metaGonder(ENV_TAM, olay, atif, f2, ISTEMCI, "kart");
  });
  ol("15g basari da loglanir (tek satir)", s2.length === 1, "satir=" + s2.length);
  ol("15h basari logunda events_received var", logMetni(s2).indexOf("\"events_received\":1") >= 0);
  ol("15i basari console.error DEGIL", s2[0] && s2[0].akis === "log");

  // GA4 hata yolu da sessiz degil.
  const f3 = kodluFetch(500, "sunucu hatasi");
  const s3 = await logYakala(async () => { await ga4Gonder(ENV_TAM, olay, atif, f3, "kart"); });
  ol("15j GA4 hatasi da LOGLANIR", s3.some((s) => s.akis === "error" &&
    s.metin.indexOf("\"kod\":500") >= 0), logMetni(s3));
}

// ---- 16) ACIK 2 — user_data TAMAMEN BOSSA Meta'ya gonderilmez ama LOGLANIR ----
async function test16() {
  const bosAtifSiparis = { ...SIPARIS, atif: "" };
  const f = kodluFetch(200, "{\"events_received\":1}");
  let sonuc;
  const satirlar = await logYakala(async () => {
    sonuc = await olcumGonder(ENV_TAM, null, bosAtifSiparis, f, { kaynak: "kart" });
  });
  const metaCagri = f.cagrilar.filter((c) => String(c.url).indexOf("graph.facebook.com") >= 0);
  const ga4Cagri = f.cagrilar.filter((c) => String(c.url).indexOf("google-analytics.com") >= 0);
  ol("16a user_data bos -> Meta'ya POST YOK", metaCagri.length === 0, "cagri=" + metaCagri.length);
  ol("16b atlama SESSIZ degil (loglandi)",
    logMetni(satirlar).indexOf("user_data-bos") >= 0, logMetni(satirlar));
  ol("16c GA4 bundan ETKILENMEZ (client_id fallback) -> POST edildi", ga4Cagri.length === 1);
  ol("16d sonuc dizisinde atlandi sebebi", (sonuc[0] || {}).atlandi === "user_data-bos");
}

// ---- 17) ACIK 3 — event_time + 7 GUNLUK GERIYE-DONUK PENCERE ----
async function test17() {
  const simdi = Math.floor(Date.now() / 1000);
  const olay = satinAlmaOlayi(SIPARIS);
  const atif = JSON.parse(SIPARIS.atif);

  // Pencere ICI (2 saat once): event_time govdeye GERCEK odeme ani olarak girer.
  const yakin = simdi - 7200;
  const g = metaGovdesi({}, { ...olay, event_time: yakin }, atif).data[0];
  ol("17a event_time verilince govdeye AYNEN girer (gercek odeme ani)",
    g.event_time === yakin, "event_time=" + g.event_time);
  const g0 = metaGovdesi({}, olay, atif).data[0];
  ol("17b event_time verilmezse 'simdi'", Math.abs(g0.event_time - simdi) <= 5);

  // Pencere DISI (10 gun once): Meta'ya GONDERILMEZ + LOGLANIR; GA4 yine gonderilir.
  const eski = simdi - 10 * 24 * 3600;
  const f = kodluFetch(200, "{\"events_received\":1}");
  let sonuc;
  const satirlar = await logYakala(async () => {
    sonuc = await olcumGonder(ENV_TAM, null, SIPARIS, f, { event_time: eski, kaynak: "havale" });
  });
  const metaCagri = f.cagrilar.filter((c) => String(c.url).indexOf("graph.facebook.com") >= 0);
  const ga4Cagri = f.cagrilar.filter((c) => String(c.url).indexOf("google-analytics.com") >= 0);
  ol("17c 7 gunden eski olay Meta'ya GONDERILMEZ", metaCagri.length === 0);
  ol("17d atlama LOGLANIR (pencere-disi)",
    logMetni(satirlar).indexOf("pencere-disi") >= 0, logMetni(satirlar));
  ol("17e sonucta yas_sn raporlanir", (sonuc[0] || {}).yas_sn > 7 * 24 * 3600);
  ol("17f GA4'e yine gonderilir (ciro kaybolmasin)", ga4Cagri.length === 1);
  ol("17g GA4 eski olayda timestamp_micros KOYMAZ (72 saat siniri)",
    !("timestamp_micros" in ((ga4Cagri[0] || {}).govde || {})));

  // GA4 yakin olayda gercek damgayi koyar.
  const g4 = ga4Govdesi({}, { ...olay, event_time: yakin }, atif);
  ol("17h GA4 yakin olayda timestamp_micros = gercek an",
    g4.timestamp_micros === String(yakin * 1000000), "ts=" + g4.timestamp_micros);
}

// ---- 18-19) ACIK 3 — HAVALE AKISI: yonet.js /durum 'odendi' -> Purchase + IDEMPOTENS ----
// yonet.js semalari JSON olarak STATIK import eder (worker/esbuild deseni). Node ESM'de
// JSON import'u "with { type: 'json' }" ister -> resolve hook'u ile ekleniyor (agdan
// bagimsiz, wrangler gerektirmez). registerHooks Node >= 22.15'te var.
let yonetModulu = null;
if (typeof nodeModule.registerHooks === "function") {
  nodeModule.registerHooks({
    resolve(specifier, context, next) {
      const r = next(specifier, context);
      if (r.url.endsWith(".json")) {
        return { ...r, format: "json", importAttributes: { type: "json" } };
      }
      return r;
    },
  });
  yonetModulu = await import("../src/yonet.js");
}

const ANAHTAR = "test-yonet-anahtari";

/** Tek satirlik sahte D1: SELECT (first) + CAS UPDATE (run). */
function sahteD1(satir) {
  const iz = { guncelleme: [] };
  const db = {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async first() { return arg[0] === satir.siparis_no ? { ...satir } : null; },
            async run() {
              // UPDATE ... SET durum=?, durum_gecmisi=? WHERE siparis_no=? AND durum=?
              const [hedef, gecmis, no, mevcut] = arg;
              if (no !== satir.siparis_no || satir.durum !== mevcut) {
                return { meta: { changes: 0 } };           // CAS kaybetti
              }
              satir.durum = hedef; satir.durum_gecmisi = gecmis;
              iz.guncelleme.push({ hedef, gecmis });
              return { meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
  return { db, iz };
}

function havaleSatiri(ekle) {
  return {
    siparis_no: "PR-260720-021133-HAV",
    tarih: new Date(Date.now() - 3600 * 1000).toISOString(),  // 1 saat once (pencere ICI)
    durum: "havale-bekliyor",
    durum_gecmisi: "",
    odeme_yontemi: "havale",
    tutar_kurus: 43290,
    kargo_kurus: 25000,
    urunler: SIPARIS.urunler,
    atif: SIPARIS.atif,
    kdv_kurus: 11381,
    musteri_ad: "Test Musteri",
    musteri_eposta: "musteri@ornek.com",
    musteri_adres: "Ornek Mah. 1 Sk. No:1",
    ...(ekle || {}),
  };
}

/** /api/shop/yonet/durum cagrisi (gercek Request/URL nesneleriyle). */
async function durumCagir(env, siparisNo, hedefDurum, ctx) {
  const adres = "https://pruvo3d.com/api/shop/yonet/durum";
  const request = new Request(adres, {
    method: "POST",
    headers: { "X-Yonet-Anahtar": ANAHTAR, "Content-Type": "application/json",
               "CF-Connecting-IP": "198.51.100.9", "User-Agent": "OkanYonetimTarayici/1.0" },
    body: JSON.stringify({ siparis_no: siparisNo, durum: hedefDurum }),
  });
  const c = await yonetModulu.yonet(request, env, new URL(adres), ctx, "/durum", async () => {});
  return { kod: c.status, govde: await c.json() };
}

async function test18() {
  if (!yonetModulu) {
    ol("18 HAVALE AKISI (yonet.js yuklenemedi — Node >= 22.15 gerekli)", false,
      "node " + process.version);
    return;
  }
  const satir = havaleSatiri();
  const { db } = sahteD1(satir);
  const f = kodluFetch(200, "{\"events_received\":1,\"fbtrace_id\":\"AbCHavale\"}");
  const eskiFetch = globalThis.fetch;
  globalThis.fetch = f;                                   // AG ISTEGI YOK — stub
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  const env = { ...ENV_TAM, YONET_ANAHTAR: ANAHTAR, KATALOG: db };

  let r;
  const satirlar = await logYakala(async () => {
    r = await durumCagir(env, satir.siparis_no, "odendi", ctx);
    await Promise.all(bekleyen);
  });
  globalThis.fetch = eskiFetch;

  ol("18a havale-bekliyor -> odendi 200", r.kod === 200 && r.govde.durum === "odendi",
    JSON.stringify(r));
  const metaCagri = f.cagrilar.filter((c) => String(c.url).indexOf("graph.facebook.com") >= 0);
  const ga4Cagri = f.cagrilar.filter((c) => String(c.url).indexOf("google-analytics.com") >= 0);
  ol("18b HAVALE Purchase Meta'ya GONDERILDI (onceden HIC gitmiyordu)",
    metaCagri.length === 1, "cagri=" + metaCagri.length);
  ol("18c HAVALE Purchase GA4'e GONDERILDI", ga4Cagri.length === 1);
  // Savunmali: cagri hic yapilmadiysa test COKMEZ, kirmizi yanar (once-kirmizi turunda onemli).
  const BOS = { data: [{ user_data: {}, custom_data: {} }] };
  const d = ((metaCagri[0] || {}).govde || BOS).data[0];
  ol("18d event_id === siparis_no (kart akisiyla AYNI dedup anahtari)",
    d.event_id === satir.siparis_no, "event_id=" + d.event_id);
  ol("18e event_name Purchase + currency TRY",
    d.event_name === "Purchase" && d.custom_data.currency === "TRY");
  ol("18f value = urun + kargo (682.9)", d.custom_data.value === 682.9,
    "value=" + d.custom_data.value);
  ol("18g GA4 transaction_id === siparis_no",
    (((ga4Cagri[0] || {}).govde || { events: [{ params: {} }] })
      .events[0].params.transaction_id) === satir.siparis_no);
  ol("18h event_time = GERCEK odeme ani (siparis tarihi, 'simdi' degil)",
    Math.abs(d.event_time - Math.floor(Date.parse(satir.tarih) / 1000)) <= 1,
    "event_time=" + d.event_time);
  // 🔒 GIZLILIK: yonetim istegi OKAN'in tarayicisindan gelir -> IP/UA MUSTERIYE AIT DEGIL.
  ol("18i havalede Okan'in IP'si Meta'ya GITMEZ",
    !("client_ip_address" in d.user_data), JSON.stringify(d.user_data));
  ol("18j havalede Okan'in User-Agent'i Meta'ya GITMEZ",
    !("client_user_agent" in d.user_data));
  ol("18k musterinin rizali fbp/fbc'si yine gider (atif kaydindan)",
    d.user_data.fbp === "fb.1.1690.pixel");
  ol("18l durum_gecmisi'ne olcum izi ('o':1) yazildi",
    (JSON.parse(satir.durum_gecmisi)[0] || {}).o === 1, satir.durum_gecmisi);
  ol("18m log kaynagi 'havale'", logMetni(satirlar).indexOf("\"kaynak\":\"havale\"") >= 0);
}

async function test19() {
  if (!yonetModulu) {
    ol("19 IDEMPOTENS (yonet.js yuklenemedi — Node >= 22.15 gerekli)", false,
      "node " + process.version);
    return;
  }
  // --- 19.1: ayni siparis IKI KEZ 'odendi' -> Purchase yalniz BIR KEZ ---
  const satir = havaleSatiri();
  const { db } = sahteD1(satir);
  const f = kodluFetch(200, "{\"events_received\":1}");
  const eskiFetch = globalThis.fetch;
  globalThis.fetch = f;
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  const env = { ...ENV_TAM, YONET_ANAHTAR: ANAHTAR, KATALOG: db };

  let r1, r2;
  await logYakala(async () => {
    r1 = await durumCagir(env, satir.siparis_no, "odendi", ctx);
    r2 = await durumCagir(env, satir.siparis_no, "odendi", ctx);   // ELLE ikinci kez
    await Promise.all(bekleyen);
  });
  const metaCagri = f.cagrilar.filter((c) => String(c.url).indexOf("graph.facebook.com") >= 0);
  ol("19a ilk 'odendi' 200", r1.kod === 200);
  ol("19b ikinci 'odendi' REDDEDILDI (durum makinesi)", r2.kod === 400, JSON.stringify(r2));
  ol("19c Purchase TEK KEZ gonderildi (Meta)", metaCagri.length === 1,
    "cagri=" + metaCagri.length);

  // --- 19.2: olcum izi VAR ama durum elle 'havale-bekliyor'a dondurulmus (ham SQL) ---
  // Durum makinesi bu kez gecise IZIN VERIR; ikinci savunma (durum_gecmisi "o":1) tutmali.
  const satir2 = havaleSatiri({
    siparis_no: "PR-260720-021133-IZL",
    durum_gecmisi: JSON.stringify([{ d: "odendi", z: new Date().toISOString(), o: 1 }]),
  });
  const d2 = sahteD1(satir2);
  const f2 = kodluFetch(200, "{\"events_received\":1}");
  globalThis.fetch = f2;
  const bekleyen2 = [];
  const ctx2 = { waitUntil: (p) => bekleyen2.push(p) };
  const env2 = { ...ENV_TAM, YONET_ANAHTAR: ANAHTAR, KATALOG: d2.db };
  let r3;
  const satirlar2 = await logYakala(async () => {
    r3 = await durumCagir(env2, satir2.siparis_no, "odendi", ctx2);
    await Promise.all(bekleyen2);
  });
  globalThis.fetch = eskiFetch;
  ol("19d durum degisimi yine calisir (200)", r3.kod === 200, JSON.stringify(r3));
  ol("19e olcum izi varsa Purchase TEKRARLANMAZ", f2.cagrilar.length === 0,
    "cagri=" + f2.cagrilar.length);
  // Not: iz "DENENDI" demek, "Meta aldi" demek DEGIL (gecmiseEkle notu) — log da oyle der.
  ol("19f tekrar atlamasi LOGLANIR (sessiz degil)",
    logMetni(satirlar2).indexOf("zaten-denendi") >= 0, logMetni(satirlar2));
}

// ---- 20) LOG GIZLILIK NEGATIF TESTI: token / Authorization / PII loga GECMEZ ----
async function test20() {
  // PII dolu siparis + gizli token'li env: hicbiri loga sizmamali.
  const piiSiparis = {
    ...SIPARIS,
    musteri_ad: "Ayse Yilmaz",
    musteri_eposta: "ayse.yilmaz@ornekmusteri.com",
    musteri_tel: "05551234567",
    musteri_adres: "Ornek Mah. Deneme Sk. No:5 Daire:3",
  };
  const hataGovde = "{\"error\":{\"message\":\"Invalid parameter\",\"fbtrace_id\":\"Az9\"}}";
  const f = kodluFetch(400, hataGovde);
  const satirlar = await logYakala(async () => {
    await olcumGonder(ENV_TAM, null, piiSiparis, f, { istemci: ISTEMCI, kaynak: "kart" });
  });
  const metin = logMetni(satirlar);
  ol("20a log BOS DEGIL (aksi halde test anlamsiz)", metin.length > 0);
  ol("20b META_CAPI_TOKEN logda YOK", metin.indexOf("GIZLI-CAPI-TOKEN-ABC123") < 0, metin);
  ol("20c GA4_API_SECRET logda YOK", metin.indexOf("GIZLI-GA4-SECRET-XYZ789") < 0, metin);
  ol("20d 'access_token' ham degeri logda YOK", metin.indexOf("access_token=GIZLI") < 0);
  ol("20e 'Authorization' logda YOK", metin.toLowerCase().indexOf("authorization") < 0);
  ol("20f e-posta logda YOK", metin.indexOf("ayse.yilmaz@ornekmusteri.com") < 0);
  ol("20g telefon logda YOK", metin.indexOf("05551234567") < 0);
  ol("20h musteri adi logda YOK", metin.indexOf("Ayse Yilmaz") < 0);
  ol("20i adres logda YOK", metin.indexOf("Deneme Sk") < 0);
  ol("20j IP logda YOK", metin.indexOf(ISTEMCI.ip) < 0);
  ol("20k User-Agent logda YOK", metin.indexOf("iPhone") < 0);
  ol("20l fbp/fbc degeri logda YOK", metin.indexOf("fb.1.1690.pixel") < 0);
  ol("20m istek URL'i logda YOK (access_token tasir)",
    metin.indexOf("graph.facebook.com") < 0 && metin.indexOf("google-analytics.com") < 0);
  ol("20n buna karsin TESHIS bilgisi VAR (siparis no + kod + fbtrace)",
    metin.indexOf(SIPARIS.siparis_no) >= 0 && metin.indexOf("\"kod\":400") >= 0 &&
    metin.indexOf("Az9") >= 0);
}

// ---- 21) OLCUM TEST KAPISI: yerel test GERCEK piksele/mulke basamaz (fail-closed) ----
async function test21() {
  const TOML = "[vars]\nMETA_PIXEL_ID = \"2150216885710153\"\n" +
    "GA4_MEASUREMENT_ID = \"G-5V53CQMSCE\"\nSITE_URL = \"https://pruvo3d.com\"\n";

  // Temiz ortam: kapi ACIK ama kimlikler EZILIR (gercek piksel ASLA kullanilmaz).
  const t = olcumKapisi({ wranglerToml: TOML, devVars: null, ortam: {} });
  ol("21a temiz ortamda kapi gecirir", t.ok === true, JSON.stringify(t.sebepler));
  ol("21b gercek piksel wrangler.toml'dan okundu", t.gercekPiksel === "2150216885710153");
  ol("21c override piksel GERCEK piksel DEGIL",
    t.degiskenler.META_PIXEL_ID !== "2150216885710153", t.degiskenler.META_PIXEL_ID);
  ol("21d override GA4 mulku GERCEK mulk DEGIL",
    t.degiskenler.GA4_MEASUREMENT_ID !== "G-5V53CQMSCE");
  ol("21e override piksel gecersiz bicimde (kazara istek gercek mulke denk gelmesin)",
    !/^\d+$/.test(t.degiskenler.META_PIXEL_ID), t.degiskenler.META_PIXEL_ID);

  // .dev.vars'ta GERCEK CAPI token'i -> test KOSMAYI REDDEDER (sessiz atlama YOK).
  const r1 = olcumKapisi({ wranglerToml: TOML,
    devVars: "IYZICO_API_KEY=sandbox-abc\nMETA_CAPI_TOKEN=EAAG-gercek-token\n", ortam: {} });
  ol("21f .dev.vars'ta META_CAPI_TOKEN -> RED", r1.ok === false);
  ol("21g red sebebi anlasilir (.dev.vars + anahtar adi)",
    r1.sebepler.join(" ").indexOf("META_CAPI_TOKEN") >= 0 &&
    r1.sebepler.join(" ").indexOf(".dev.vars") >= 0, JSON.stringify(r1.sebepler));

  const r2 = olcumKapisi({ wranglerToml: TOML,
    devVars: "GA4_API_SECRET=gercek-secret\n", ortam: {} });
  ol("21h .dev.vars'ta GA4_API_SECRET -> RED", r2.ok === false);

  const r3 = olcumKapisi({ wranglerToml: TOML, devVars: null,
    ortam: { META_CAPI_TOKEN: "EAAG-gercek" } });
  ol("21i ortam degiskeninde CAPI token -> RED", r3.ok === false);

  // YORUMLU satir tehlike DEGIL (yanlis alarm testi kilitlemesin).
  const r4 = olcumKapisi({ wranglerToml: TOML,
    devVars: "# META_CAPI_TOKEN=eski-deger\nIYZICO_API_KEY=sandbox-abc\n", ortam: {} });
  ol("21j yorumlanmis (#) token satiri RED DEGIL", r4.ok === true, JSON.stringify(r4.sebepler));

  // Bos deger de tehlike degil.
  const r5 = olcumKapisi({ wranglerToml: TOML, devVars: "META_CAPI_TOKEN=\n", ortam: {} });
  ol("21k bos degerli token satiri RED DEGIL", r5.ok === true);

  // --- .env / .env.local KOR NOKTASI (mimar denetimi 3. tur) ---------------------
  // wrangler 4.112: `.dev.vars` YOKSA `.env`/`.env.local` SECRET olarak yuklenir
  // ("Using secrets defined in .env"). Kok .gitignore `.env*` yok saydigi icin sirri
  // koymanin "dogal gorunen" yeri tam orasi -> kapi oraya da bakmali.
  const e1 = olcumKapisi({ wranglerToml: TOML, ortam: {},
    dosyalar: { ".dev.vars": null, ".env": "META_CAPI_TOKEN=EAAG-gercek-token\n" } });
  ol("21l .env icinde META_CAPI_TOKEN -> RED", e1.ok === false, JSON.stringify(e1.sebepler));
  ol("21m red sebebi .env dosyasini ADIYLA soyluyor",
    e1.sebepler.join(" ").indexOf("shop/.env") >= 0, JSON.stringify(e1.sebepler));

  const e2 = olcumKapisi({ wranglerToml: TOML, ortam: {},
    dosyalar: { ".env.local": "GA4_API_SECRET=gercek-secret\n" } });
  ol("21n .env.local icinde GA4_API_SECRET -> RED", e2.ok === false);
  ol("21o red sebebi .env.local dosyasini ADIYLA soyluyor",
    e2.sebepler.join(" ").indexOf("shop/.env.local") >= 0, JSON.stringify(e2.sebepler));

  // .dev.vars VARKEN bile .env taranir (wrangler onceligi TAKLIT EDILMEZ — fail-closed).
  const e3 = olcumKapisi({ wranglerToml: TOML, ortam: {},
    dosyalar: { ".dev.vars": "IYZICO_API_KEY=sandbox\n", ".env": "META_CAPI_TOKEN=EAAG\n" } });
  ol("21p .dev.vars varken bile .env RED ettirir (precedence tahmini yok)", e3.ok === false);

  // Uc dosya da temizse gecer + taranan liste raporlanir (belge/kod tutarliligi).
  const e4 = olcumKapisi({ wranglerToml: TOML, ortam: {},
    dosyalar: { ".dev.vars": "IYZICO_API_KEY=sandbox\n", ".env": "FOO=bar\n",
                ".env.local": "# bos\n" } });
  ol("21q uc dosya da temizse kapi gecirir", e4.ok === true, JSON.stringify(e4.sebepler));
  ol("21r kapi taradigi dosyalari RAPORLUYOR (.dev.vars + .env + .env.local)",
    JSON.stringify(e4.taranan) === JSON.stringify([".dev.vars", ".env", ".env.local"]),
    JSON.stringify(e4.taranan));
}

// ---- 22) ACIK 2 KABLOLAMASI: KART akisinda IP/UA gercekten Meta govdesine ulasiyor ----
// index.js'in donus() akisi UCTAN UCA kosturulur (sahte D1 + sahte iyzico + sahte Meta).
// Mutasyon duyarli: index.js'teki `istemci` kablolamasi koparilirsa bu blok KIRMIZI yanar.
let indexModulu = null;
if (yonetModulu) { indexModulu = await import("../src/index.js"); }

const KART_IP = "203.0.113.44";
const KART_UA = "Mozilla/5.0 (Linux; Android 14) MusteriTarayici/9";

/**
 * KART AKISI KOSTURUCU — index.js'in donus() yolunu UCTAN UCA calistirir.
 * Sahte D1 + sahte iyzico retrieve + sahte Meta/GA4; GERCEK AG ISTEGI YOK.
 * secenek.detay = iyzico retrieve cevabi (basarili/basarisiz senaryolari buradan verilir).
 */
async function kartAkisiKostur(secenek) {
  const s = secenek || {};
  const TOKEN = "iyzico-token-" + (s.no || "0001");
  const satir = {
    siparis_no: "PR-260720-0315-" + (s.no || "KRT"),
    durum: "bekliyor",
    tutar_kurus: 43290, kargo_kurus: 25000, kdv_kurus: 11381,
    urunler: SIPARIS.urunler,
    atif: SIPARIS.atif,                       // fbp VAR -> riza kapisi acik
    musteri_ad: "Kart Musteri", musteri_tel: "05551112233",
    musteri_eposta: "kart@ornekmusteri.com", musteri_adres: "Ornek Mah. No:2",
  };
  // Sahte D1: SELECT token ile satiri verir; durum UPDATE'leri SQL'e gore islenir.
  const db = {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async first() { return arg[0] === TOKEN ? { ...satir } : null; },
            async run() {
              const m = /SET durum = '([a-z-]+)'/.exec(sql);
              if (m && satir.durum !== m[1]) { satir.durum = m[1]; return { meta: { changes: 1 } }; }
              return { meta: { changes: 0 } };
            },
          };
        },
      };
    },
  };
  // Varsayilan: basarili odeme, tutar birebir (682.90 = 432.90 urun + 250.00 kargo).
  const detay = Object.assign({
    status: "success", paymentStatus: "SUCCESS", paidPrice: "682.9",
    conversationId: satir.siparis_no, basketId: satir.siparis_no, paymentId: "PAY-1",
  }, s.detay || {});
  const cagrilar = [];
  const stub = async (url, opt) => {
    const u = String(url);
    cagrilar.push({ url: u, govde: opt && opt.body ? JSON.parse(opt.body) : null });
    if (u.indexOf("iyzico-mock") >= 0) {
      return { status: 200, text: async () => JSON.stringify(detay) };
    }
    return { status: 200, text: async () => "{\"events_received\":1}" };
  };
  const eskiFetch = globalThis.fetch;
  globalThis.fetch = stub;
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  const env = {
    ...ENV_TAM,
    KATALOG: db,
    IYZICO_BASE_URL: "https://iyzico-mock.local",
    IYZICO_API_KEY: "test-api-key", IYZICO_SECRET_KEY: "test-secret",
    // TELEGRAM_TOKEN + RESEND_API_KEY BILEREK YOK -> o yollar no-op.
  };
  const istek = new Request("https://pruvo3d.com/api/shop/donus", {
    method: "POST",
    headers: { "Content-Type": "application/json",
               "CF-Connecting-IP": KART_IP, "User-Agent": KART_UA },
    body: JSON.stringify({ token: TOKEN }),
  });
  let cevap;
  const loglar = await logYakala(async () => {
    cevap = await indexModulu.default.fetch(istek, env, ctx);
    await Promise.all(bekleyen);
  });
  globalThis.fetch = eskiFetch;
  const suz = (parca) => cagrilar.filter((c) => c.url.indexOf(parca) >= 0);
  return { cevap, cagrilar, satir, loglar, log: logMetni(loglar),
           meta: suz("graph.facebook.com"), ga4: suz("google-analytics.com") };
}

async function test22() {
  if (!indexModulu) {
    ol("22 KART AKISI KABLOLAMASI (index.js yuklenemedi — Node >= 22.15 gerekli)", false,
      "node " + process.version);
    return;
  }
  const MUSTERI_IP = KART_IP;
  const MUSTERI_UA = KART_UA;
  const r = await kartAkisiKostur({ no: "KRT" });
  const { cevap, satir, meta } = r;

  ol("22a kart akisi tamamlandi (musteri siteye yonlendirildi)",
    cevap && cevap.status === 303, "kod=" + (cevap && cevap.status));
  ol("22b siparis 'odendi'ye gecti", satir.durum === "odendi");
  ol("22c Meta'ya Purchase gonderildi", meta.length === 1, "cagri=" + meta.length);
  const ud = (((meta[0] || {}).govde || { data: [{ user_data: {} }] }).data[0]).user_data;
  // ⬇️ ACIK 2'nin TUM IS DEGERI BU IKI SATIRDA: index.js kablolamasi koparsa kirmizi.
  ol("22d KART yolunda client_ip_address MUSTERININ IP'si olarak gövdeye ULASTI",
    ud.client_ip_address === MUSTERI_IP, "ip=" + ud.client_ip_address);
  ol("22e KART yolunda client_user_agent MUSTERININ UA'si olarak gövdeye ULASTI",
    ud.client_user_agent === MUSTERI_UA, "ua=" + ud.client_user_agent);
  ol("22f event_id === siparis_no",
    (((meta[0] || {}).govde || { data: [{}] }).data[0]).event_id === satir.siparis_no);
}

// ---- 23) sirMaskele ETKIN Mi? (hedefin YANIT govdesinde token gecerse maskelenmeli) ----
// 20. blok govdede token OLMAYAN bir yanit kullaniyordu -> maskeleme olu olsa da yesil
// kaliyordu (denetci mutasyonu). Bu blok maskelemenin KENDISINI sinar.
async function test23() {
  const olay = satinAlmaOlayi(SIPARIS);
  const atif = JSON.parse(SIPARIS.atif);
  // Meta kimlik hatalarinda token'i yanit metnine yansitabiliyor — gercekci senaryo.
  const sizanGovde = "{\"error\":{\"message\":\"Invalid OAuth access_token=" +
    ENV_TAM.META_CAPI_TOKEN + " for this pixel\",\"fbtrace_id\":\"AzMask\"}}";
  const f = kodluFetch(400, sizanGovde);
  const satirlar = await logYakala(async () => {
    await metaGonder(ENV_TAM, olay, atif, f, ISTEMCI, "kart");
  });
  const metin = logMetni(satirlar);
  ol("23a yanit govdesinde token GECSE BILE ham token loga yazilmaz",
    metin.indexOf(ENV_TAM.META_CAPI_TOKEN) < 0, metin);
  ol("23b maskeleme izi var (access_token=***)", metin.indexOf("access_token=***") >= 0, metin);
  ol("23c maskeleme teshisi OLDURMEDI (fbtrace_id hala okunuyor)",
    metin.indexOf("AzMask") >= 0);

  // GA4 tarafi: api_secret sizarsa o da maskelenir.
  const sizanGa4 = "gecersiz istek: api_secret=" + ENV_TAM.GA4_API_SECRET + " reddedildi";
  const f2 = kodluFetch(400, sizanGa4);
  const s2 = await logYakala(async () => { await ga4Gonder(ENV_TAM, olay, atif, f2, "kart"); });
  ol("23d GA4 yanitindaki api_secret de maskelenir",
    logMetni(s2).indexOf(ENV_TAM.GA4_API_SECRET) < 0 &&
    logMetni(s2).indexOf("api_secret=***") >= 0, logMetni(s2));
}

// ---- 24) ESZAMANLILIK (gercek yaris): iki es zamanli 'odendi' -> TEK Purchase ----
// Sahte D1 okuma GECIKMELI: iki istek de eski durumu okur, sonra ikisi de CAS dener.
// Koruyan sey CAS'tir (UPDATE ... WHERE durum = <okunan>); bu blok onu kilitler.
async function test24() {
  if (!yonetModulu) {
    ol("24 ESZAMANLILIK (yonet.js yuklenemedi — Node >= 22.15 gerekli)", false,
      "node " + process.version);
    return;
  }
  const satir = havaleSatiri({ siparis_no: "PR-260720-031600-YRS" });

  // MANDAL (latch): iki istek de OKUMAYI bitirmeden hicbiri YAZAMAZ. Gercek yaris penceresi
  // budur — sadece setTimeout ile beklemek yetmiyordu (biri digerinden once yazip bitiriyor,
  // kaybeden CAS'a hic ugramadan durum makinesine takiliyordu; yani CAS SINANMIYORDU).
  //
  // ⚠️ MANDAL KENDINI DOGRULAR (mimar denetimi 3. tur): mandal devre disi kalirsa istekler
  // SIRALANIR, tek Purchase gider ve "cift ciro yok" diyen 24c/24d mutasyondan BAGIMSIZ
  // olarak yesil kalirdi — yani para iddialari sessizce nobetten duserdi. Bu yuzden asagida
  // 24f, yaris penceresinin GERCEKTEN acildigini (iki okumanin da ESKI durumu gordugunu)
  // ayrica sinar. Mandal bozulursa 24f KIRMIZI yanar; sessiz zayiflama yolu kapali.
  let gelenOkuyucu = 0;
  let bekleyenOkuyucu = [];
  let mandalSayiylaAcildi = false;               // true: 2 okuyucu geldi · false: zaman asimi
  const okunanDurumlar = [];                    // her SELECT'in GORDUGU durum
  async function okumaMandali() {
    gelenOkuyucu++;
    if (gelenOkuyucu >= 2) {
      mandalSayiylaAcildi = true;
      bekleyenOkuyucu.forEach((c) => c());
      bekleyenOkuyucu = [];
      return;
    }
    await Promise.race([
      new Promise((c) => bekleyenOkuyucu.push(c)),
      new Promise((c) => setTimeout(c, 2000)),          // asilma emniyeti
    ]);
  }

  const db = {
    prepare(sql) {
      return {
        bind(...arg) {
          return {
            async first() {
              await okumaMandali();                     // ⬅️ iki istek de ESKI durumu okur
              if (arg[0] !== satir.siparis_no) { return null; }
              okunanDurumlar.push(satir.durum);         // yaris penceresi kaniti
              return { ...satir };
            },
            async run() {
              const [hedef, gecmis, no, mevcut] = arg;
              if (no !== satir.siparis_no) { return { meta: { changes: 0 } }; }
              // SQL'i AYNEN taklit et: kosul kaynak koddan KALKARSA burada da kalkar ->
              // iki yazar da kazanir -> cift Purchase -> 24c KIRMIZI (mutasyon duyarli).
              const casVar = sql.indexOf("AND durum = ?") >= 0;
              if (casVar && satir.durum !== mevcut) { return { meta: { changes: 0 } }; }
              satir.durum = hedef; satir.durum_gecmisi = gecmis;
              return { meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
  const f = kodluFetch(200, "{\"events_received\":1}");
  const eskiFetch = globalThis.fetch;
  globalThis.fetch = f;
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  const env = { ...ENV_TAM, YONET_ANAHTAR: ANAHTAR, KATALOG: db };

  let sonuclar;
  await logYakala(async () => {
    sonuclar = await Promise.all([                     // ⬅️ GERCEK eszamanlilik
      durumCagir(env, satir.siparis_no, "odendi", ctx),
      durumCagir(env, satir.siparis_no, "odendi", ctx),
    ]);
    await Promise.all(bekleyen);
  });
  globalThis.fetch = eskiFetch;

  const basarili = sonuclar.filter((r) => r.kod === 200);
  const catisan = sonuclar.filter((r) => r.kod === 409);
  const metaCagri = f.cagrilar.filter((c) => String(c.url).indexOf("graph.facebook.com") >= 0);
  const ga4Cagri = f.cagrilar.filter((c) => String(c.url).indexOf("google-analytics.com") >= 0);
  // ⬇️ NOBETCI: yaris penceresi gercekten acildi mi? Bu KIRMIZIYSA 24c/24d'nin yesilligi
  // ANLAMSIZDIR (istekler sirlanmis, CAS hic sinanmamis olur). Once bunu oku.
  const eskiOkuma = okunanDurumlar.filter((d) => d === "havale-bekliyor").length;
  ol("24f YARIS PENCERESI ACILDI: iki okuma da yazmadan ONCE eski durumu gordu",
    eskiOkuma === 2 && mandalSayiylaAcildi === true,
    "eski-okuma=" + eskiOkuma + " okumalar=" + JSON.stringify(okunanDurumlar) +
    " mandal-sayiyla=" + mandalSayiylaAcildi);

  ol("24a yarista TEK istek kazandi (200)", basarili.length === 1,
    JSON.stringify(sonuclar.map((r) => r.kod)));
  ol("24b kaybeden 409 'durum-degismis' aldi (sessiz basari YOK)",
    catisan.length === 1 && (catisan[0].govde || {}).hata === "durum-degismis",
    JSON.stringify(catisan));
  // 24c/24d = PARA IDDIALARI. 24f sayesinde bunlar kendi baslarina mutasyon duyarli:
  // CAS silinirse iki yazar da kazanir -> iki Purchase -> ikisi de KIRMIZI.
  ol("24c Meta'ya TEK Purchase gitti (cift ciro yok)", metaCagri.length === 1,
    "cagri=" + metaCagri.length);
  ol("24d GA4'e TEK purchase gitti", ga4Cagri.length === 1, "cagri=" + ga4Cagri.length);
  ol("24e durum 'odendi'de kaldi", satir.durum === "odendi");
  // Ayni siparis icin BIRDEN COK event_id uretilmedigi de dogrulanir (dedup anahtari tek).
  const olayKimlikleri = new Set(metaCagri.map((c) => (c.govde.data[0] || {}).event_id));
  ol("24g gonderilen Purchase sayisi = 1 ve event_id tek (cift ciro imzasi yok)",
    olayKimlikleri.size === 1 && metaCagri.length === 1,
    "kimlikler=" + JSON.stringify([...olayKimlikleri]));
}

// ---- 25) 🔴 BASARISIZ/SUPHELI ODEMEDE PURCHASE GITMEZ (negatif kapi testleri) ----
// Bu paketin ONLEMEYE calistigi zararin ta kendisi: karti REDDEDILEN musteri icin
// Meta+GA4'e GERCEK TUTARLI SAHTE Purchase gitmesi -> Okan'in reklam butcesi yanlis ogrenir.
// Taban kod dogruydu ama `det.paymentStatus === "SUCCESS"` kapisini KORUYAN TEST YOKTU;
// kapi gevserse paket yesil kalirdi. Artik kalmiyor.
async function test25() {
  if (!indexModulu) {
    ol("25 BASARISIZ ODEME NEGATIF TESTLERI (index.js yuklenemedi — Node >= 22.15)", false,
      "node " + process.version);
    return;
  }

  // (a) Kart REDDI: paymentStatus FAILURE — tutar birebir DOGRU (tek engel bu kapi).
  const red = await kartAkisiKostur({ no: "RED", detay: { paymentStatus: "FAILURE" } });
  ol("25a kart reddinde Meta'ya 0 POST", red.meta.length === 0, "cagri=" + red.meta.length);
  ol("25b kart reddinde GA4'e 0 POST", red.ga4.length === 0, "cagri=" + red.ga4.length);
  ol("25c siparis 'basarisiz' oldu ('odendi' DEGIL)", red.satir.durum === "basarisiz",
    "durum=" + red.satir.durum);
  ol("25d atlama LOGLANDI (odeme-basarisiz) — sessiz bosluk yok",
    red.log.indexOf("odeme-basarisiz") >= 0, red.log);
  ol("25e log satirinda siparis no var (hangi siparis belli)",
    red.log.indexOf(red.satir.siparis_no) >= 0);

  // (b) 3DS'te yarim kalmis / bekleyen odeme.
  const bekleyen = await kartAkisiKostur({ no: "3DS", detay: { paymentStatus: "INIT_THREEDS" } });
  ol("25f bekleyen (INIT_THREEDS) odemede Meta+GA4'e 0 POST",
    bekleyen.meta.length === 0 && bekleyen.ga4.length === 0,
    "meta=" + bekleyen.meta.length + " ga4=" + bekleyen.ga4.length);
  ol("25g bekleyen odemede siparis 'odendi' OLMADI", bekleyen.satir.durum !== "odendi");

  // (c) paymentStatus HIC YOK (alan eksik) -> gonderilmez.
  const eksik = await kartAkisiKostur({ no: "EKS", detay: { paymentStatus: undefined } });
  ol("25h paymentStatus eksikse Meta+GA4'e 0 POST",
    eksik.meta.length === 0 && eksik.ga4.length === 0);

  // (d) Kucuk harfli "success" KABUL EDILMEZ (tam esitlik; gevsetilmis karsilastirma tuzagi).
  const kucuk = await kartAkisiKostur({ no: "KCK", detay: { paymentStatus: "success" } });
  ol("25i kucuk harfli 'success' Purchase URETMEZ (tam esitlik)",
    kucuk.meta.length === 0 && kucuk.ga4.length === 0,
    "meta=" + kucuk.meta.length + " ga4=" + kucuk.ga4.length);

  // (e) retrieve ALTYAPI HATASI (status success degil): odeme durumu BILINMIYOR -> gonderilmez.
  const altyapi = await kartAkisiKostur({ no: "ALT",
    detay: { status: "failure", errorCode: "1001", errorMessage: "imza" } });
  ol("25j retrieve altyapi hatasinda Meta+GA4'e 0 POST",
    altyapi.meta.length === 0 && altyapi.ga4.length === 0);
  ol("25k siparis 'incele'ye dustu", altyapi.satir.durum === "incele",
    "durum=" + altyapi.satir.durum);
  ol("25l atlama LOGLANDI (retrieve-hatasi)", altyapi.log.indexOf("retrieve-hatasi") >= 0);

  // (f) Odeme BASARILI ama TUTAR UYUSMUYOR: ciro guvenilmez -> Purchase gitmez ('incele').
  const tutar = await kartAkisiKostur({ no: "TUT", detay: { paidPrice: "1.00" } });
  ol("25m tutar uyusmazliginda Meta+GA4'e 0 POST",
    tutar.meta.length === 0 && tutar.ga4.length === 0,
    "meta=" + tutar.meta.length + " ga4=" + tutar.ga4.length);
  ol("25n siparis 'incele'ye dustu", tutar.satir.durum === "incele");
  ol("25o atlama LOGLANDI (tutar-uyusmazligi)",
    tutar.log.indexOf("tutar-uyusmazligi") >= 0, tutar.log);

  // (g) OLUMLU KONTROL: ayni kosturucu basarili odemede GERCEKTEN gonderiyor
  //     (yukaridaki "0 POST" iddialari kosturucu bozuk oldugu icin degil, kapi calistigi icin).
  const iyi = await kartAkisiKostur({ no: "IYI" });
  ol("25p olumlu kontrol: basarili odemede Meta 1 + GA4 1 POST",
    iyi.meta.length === 1 && iyi.ga4.length === 1,
    "meta=" + iyi.meta.length + " ga4=" + iyi.ga4.length);
}

const testler = [test9, test10, test11, test12, test13,
                 test14, test15, test16, test17, test18, test19, test20,
                 test21, test22, test23, test24, test25];
for (const t of testler) { await t(); }

console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" + (kalan ? "" : " — HEPSI YESIL ✅"));
process.exit(kalan ? 1 : 0);
