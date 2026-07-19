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
 * ONCE-KIRMIZI (elle kanitlandi):
 *  - olcum.js'te currency "TRY" -> "USD" yapilinca T1/T5/T7 KIRMIZI.
 *  - metaGonder/ga4Gonder'daki "secret yoksa return" satiri silinince (no-op bozulunca) T9/T10 KIRMIZI.
 */

import {
  satinAlmaOlayi, metaGovdesi, ga4Govdesi, metaGonder, ga4Gonder, olcumGonder, kurusTRY,
} from "../src/olcum.js";

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

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

const testler = [test9, test10, test11, test12, test13];
for (const t of testler) { await t(); }

console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" + (kalan ? "" : " — HEPSI YESIL ✅"));
process.exit(kalan ? 1 : 0);
