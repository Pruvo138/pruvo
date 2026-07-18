/**
 * pruvo-shop — REKLAM ROI OLCUMU: sunucu-tarafi "Purchase" olayi.
 * Is paketi: /Users/okan/dev/pruvo-pazarlama/reklam-roi-sistemi.md §1 (Faz 0).
 *
 * NEDEN SUNUCUDA: iyzico hosted/redirect akisinda musteri "tesekkur sayfasina" HIC DONMEYEBILIR
 * (uygulamayi kapatir, ag koparir). Tarayici pikseline guvenilirse satis OLCULEMEZ. Bu yuzden
 * Purchase olayi iyzico retrieve DOGRULAMASI OK dondugu AN (index.js donus() idempotent kapanis)
 * firlatilir. TEK kaynak olaydan iki hedefe (Meta CAPI + GA4 Measurement Protocol) AYNI event_id
 * ile gider (tarayici pikseli eklendiginde dedup: event_id = siparis_no).
 *
 * KIRMIZI CIZGILER:
 *  - currency ZORUNLU "TRY". Gonderilmezse Meta degeri USD sayar, ROAS'i ~30x sisirir (spec §3).
 *  - value = GERCEK tahsilat (urun + kargo), kurus tamsayisindan TRY'ye (float toplama YOK).
 *  - PII YOK (v1): email/telefon (hash'li bile) GONDERILMEZ — KVKK/riza Okan/hukuk (spec §6).
 *    Sadece value / order_id / atif-kimlikleri (GA client_id, Meta fbp/fbc) / UTM.
 *  - SIPARIS AKISINI BOZMA: her hedef kendi try/catch'inde; secret yoksa sessiz no-op; POST
 *    hatasi/timeout siparis onayini ETKILEMEZ (fire-and-forget, ctx.waitUntil).
 *  - Secret yoksa NO-OP: token/olcum anahtari tanimli degilse o hedef sessizce atlanir (kod
 *    merge olur, canliyi bozmaz; Okan secret basinca canlanir — Telegram-token-yoksa deseni gibi).
 *
 * Google Ads dONusumu ayrica KOD ISTEMEZ: GA4-import ile alinir (config tarafi HocA/ArTisT).
 * Native tag EKLENMEZ (cift sayim).
 */

const META_API_SURUM = "v21.0";

/** Kurus tamsayisini TRY ondalik SAYIYA cevirir (GA4/Meta sayi bekler, string DEGIL):
 *  43290 -> 432.9. Tamsayi aritmetigi — toFixed/float toplama kayan-nokta kaydirir. */
export function kurusTRY(kurus) {
  const k = Math.round(Number(kurus) || 0);
  return k / 100;
}

/** Siparis kaydindaki (D1) atif JSON'unu GUVENLI coz. Bos/bozuksa {} — asla patlamaz. */
export function atifCoz(siparis) {
  if (!siparis || !siparis.atif) return {};
  try {
    const a = JSON.parse(siparis.atif);
    return (a && typeof a === "object" && !Array.isArray(a)) ? a : {};
  } catch (e) {
    return {};
  }
}

/**
 * KANONIK satin-alma olayi — iki hedefin de tek kaynagi.
 *  - value      : GERCEK tahsilat (tutar_kurus + kargo_kurus) TRY'ye
 *  - currency   : ZORUNLU "TRY"
 *  - order_id / transaction_id / event_id : siparis_no (event_id = dedup anahtari)
 *  - items[]    : D1 urunler JSON'undan (id, ad, adet, birim TRY, kategori)
 */
export function satinAlmaOlayi(siparis) {
  const tahsilatKurus = (Number(siparis.tutar_kurus) || 0) + (Number(siparis.kargo_kurus) || 0);
  let satirlar = [];
  try { satirlar = JSON.parse(siparis.urunler) || []; } catch (e) { satirlar = []; }
  if (!Array.isArray(satirlar)) { satirlar = []; }
  const items = satirlar.map((s) => ({
    item_id: String(s.id || ""),
    item_name: String(s.baslik || ""),
    quantity: Number(s.adet) || 1,
    price: kurusTRY(s.birim_kurus || 0),
    item_category: String(s.kategori || ""),
  }));
  return {
    event_id: siparis.siparis_no,
    order_id: siparis.siparis_no,
    transaction_id: siparis.siparis_no,
    value: kurusTRY(tahsilatKurus),
    currency: "TRY",
    items: items,
  };
}

// ---------------------------------------------------------------- Meta CAPI

/** Meta Conversions API govdesi (PURE — fetch yok; test bunu dogrudan sinar). */
export function metaGovdesi(env, olay, atif) {
  const user_data = {};
  if (atif.fbp) { user_data.fbp = atif.fbp; }
  if (atif.fbc) { user_data.fbc = atif.fbc; }
  const veri = {
    event_name: "Purchase",
    event_time: Math.floor(Date.now() / 1000),
    action_source: "website",
    event_id: olay.event_id,                 // tarayici pikseliyle dedup anahtari
    user_data: user_data,                    // fbp/fbc (varsa) — Meta zorunlu obje; PII YOK
    custom_data: {
      currency: olay.currency,               // ZORUNLU TRY
      value: olay.value,
      order_id: olay.order_id,
      content_type: "product",
      content_ids: olay.items.map((i) => i.item_id),
      contents: olay.items.map((i) => ({ id: i.item_id, quantity: i.quantity, item_price: i.price })),
    },
  };
  if (env && env.SITE_URL) { veri.event_source_url = env.SITE_URL; }
  const govde = { data: [veri] };
  // Test Events sekmesinde dogrulama icin (Okan canli kabul): env verilirse dahil edilir.
  if (env && env.META_TEST_EVENT_CODE) { govde.test_event_code = env.META_TEST_EVENT_CODE; }
  return govde;
}

/** Meta CAPI'ye Purchase gonder. Secret/pixel yoksa sessiz no-op. fetchFn test icin enjekte edilir. */
export async function metaGonder(env, olay, atif, fetchFn) {
  const pixel = env && (env.META_PIXEL_ID || "");
  const token = env && (env.META_CAPI_TOKEN || "");
  if (!pixel || !token) { return { hedef: "meta", atlandi: "secret-yok" }; }
  const f = fetchFn || fetch;
  const url = "https://graph.facebook.com/" + META_API_SURUM + "/" + pixel +
    "/events?access_token=" + encodeURIComponent(token);
  const c = await f(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metaGovdesi(env, olay, atif)),
  });
  return { hedef: "meta", kod: c && c.status };
}

// ---------------------------------------------------------------- GA4 Measurement Protocol

/** GA4 MP govdesi (PURE). client_id atif icin ZORUNLU: gercek _ga client_id yoksa siparis_no
 *  tabanli sabit uydurulur (ciroyu yine de kaydet; sadece OTURUM atfi duser). */
export function ga4Govdesi(env, olay, atif) {
  const params = {
    transaction_id: olay.transaction_id,
    value: olay.value,
    currency: olay.currency,                 // ZORUNLU TRY
    items: olay.items.map((i) => ({
      item_id: i.item_id,
      item_name: i.item_name,
      quantity: i.quantity,
      price: i.price,
      item_category: i.item_category,
    })),
  };
  if (atif.utm_source) { params.source = atif.utm_source; }
  if (atif.utm_medium) { params.medium = atif.utm_medium; }
  if (atif.utm_campaign) { params.campaign = atif.utm_campaign; }
  if (atif.utm_id) { params.campaign_id = atif.utm_id; }
  // DebugView'da gorunmesi icin (Okan canli kabul): env GA4_DEBUG=1 ise.
  if (env && env.GA4_DEBUG) { params.debug_mode = 1; }
  const client_id = atif.ga_client_id || (olay.order_id + ".0");
  return { client_id: client_id, events: [{ name: "purchase", params: params }] };
}

/** GA4 MP'ye purchase gonder. measurement_id + api_secret yoksa sessiz no-op. */
export async function ga4Gonder(env, olay, atif, fetchFn) {
  const mid = env && (env.GA4_MEASUREMENT_ID || "");
  const gizli = env && (env.GA4_API_SECRET || "");
  if (!mid || !gizli) { return { hedef: "ga4", atlandi: "secret-yok" }; }
  const f = fetchFn || fetch;
  const taban = (env && env.GA4_DEBUG)
    ? "https://www.google-analytics.com/debug/mp/collect"
    : "https://www.google-analytics.com/mp/collect";
  const url = taban + "?measurement_id=" + encodeURIComponent(mid) +
    "&api_secret=" + encodeURIComponent(gizli);
  const c = await f(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ga4Govdesi(env, olay, atif)),
  });
  return { hedef: "ga4", kod: c && c.status };
}

// ---------------------------------------------------------------- orkestrasyon

/** Bir hedefi calistir; hata FIRLATMAZ (siparis akisini bozmaz) — yakalar, loglar, doner. */
async function guvenli(fn) {
  try { return await fn(); }
  catch (e) { console.error("olcum hedefi hata:", e && e.stack || e); return { hata: String(e) }; }
}

/**
 * Purchase olayini iki hedefe FIRE-AND-FORGET gonder. ctx.waitUntil ile arka planda kosar;
 * yanit/musteri akisi BLOKLANMAZ. Her hedef guvenli() icinde — biri patlasa digeri + siparis
 * onayi ETKILENMEZ. Test icin: donen promise await edilebilir, ctx sahte olabilir.
 */
export function olcumGonder(env, ctx, siparis, fetchFn) {
  const olay = satinAlmaOlayi(siparis);
  const atif = atifCoz(siparis);
  const p = Promise.all([
    guvenli(() => metaGonder(env, olay, atif, fetchFn)),
    guvenli(() => ga4Gonder(env, olay, atif, fetchFn)),
  ]);
  if (ctx && typeof ctx.waitUntil === "function") { ctx.waitUntil(p); }
  return p;
}

export default olcumGonder;
