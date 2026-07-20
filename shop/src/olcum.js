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
 *    ISTISNA (20 Tem, mimar karari): IP + User-Agent Meta'ya gonderilir AMA YALNIZCA `fbp`
 *    varsa — fbp riza kapisindan gecmis pikselden dogar, yani riza KANITIDIR. AYNI kapi
 *    `fbc` icin de gecerlidir (tiklama kimligi de rizasiz cikmaz). Gerekce, kapsam ve
 *    kapinin DISINDA kalanlar: metaGovdesi(). Havale akisinda IP/UA HIC gonderilmez.
 *  - LOG GIZLILIK KAPISI: her hedefin yaniti loglanir (sessiz yutma YOK) ama log yalniz
 *    beyaz listeli teknik alanlari tasir — token/URL/PII ASLA. Bkz. olcumLog() + LOG_ALANLARI.
 *  - SIPARIS AKISINI BOZMA: her hedef kendi try/catch'inde; secret yoksa sessiz no-op; POST
 *    hatasi/timeout siparis onayini ETKILEMEZ (fire-and-forget, ctx.waitUntil).
 *  - Secret yoksa NO-OP: token/olcum anahtari tanimli degilse o hedef sessizce atlanir (kod
 *    merge olur, canliyi bozmaz; Okan secret basinca canlanir — Telegram-token-yoksa deseni gibi).
 *
 * Google Ads dONusumu ayrica KOD ISTEMEZ: GA4-import ile alinir (config tarafi HocA/ArTisT).
 * Native tag EKLENMEZ (cift sayim).
 */

const META_API_SURUM = "v21.0";

/** Meta CAPI geriye-donuk penceresi: event_time'i 7 GUNDEN eski olay REDDEDILIR
 *  (Meta belgesi: "event_time can be up to 7 days before you send"). Bu sinirdan eski
 *  olayi gondermek bos yere kota yakar + Events Manager'da hata birakir -> atlanir + loglanir. */
const META_GERIYE_PENCERE_SN = 7 * 24 * 3600;

/** GA4 Measurement Protocol: timestamp_micros yalniz SON 72 SAAT icin kabul edilir; daha
 *  eskisi verilirse olay DUSURULUR. Eski olayda damga GONDERILMEZ (GA4 "simdi" sayar —
 *  ciro kaydi korunur, yalnizca saat kayar; ciroyu tamamen kaybetmekten iyidir). */
const GA4_DAMGA_PENCERE_SN = 72 * 3600;

// ---------------------------------------------------------------- LOG (gizlilik kapili)

/**
 * 🔒 LOG GIZLILIK KAPISI — bu fonksiyondan GECMEYEN hicbir sey loglanmaz.
 *
 * NEDEN VAR: 20 Tem dogrulamasinda "olay Meta'ya gitti mi?" sorusu GERIYE DONUK
 * CEVAPLANAMADI — CAPI/GA4 yaniti hicbir yere yazilmiyordu, HTTP 400 bile sessizce
 * yutuluyordu (fetch 4xx'te throw ETMEZ). Artik her hedef icin tek satir iz birakilir
 * (wrangler.toml [observability] enabled = true -> Cloudflare Logs'ta gorunur).
 *
 * 🚫 ASLA LOGLANMAZ (KVKK + sir sizintisi):
 *   - Kisisel veri: e-posta, telefon, ad, adres, TAM IP, User-Agent, fbp/fbc degerleri.
 *   - Sir: META_CAPI_TOKEN / GA4_API_SECRET / Authorization basligi / ISTEK URL'i
 *     (URL access_token ve api_secret ICERIR — bu yuzden url ASLA log alanina konmaz).
 *   - Gonderdigimiz govde (user_data icerir).
 * ✅ YALNIZ SUNLAR: siparis no (=event_id), olay adi, hedef, HTTP kodu, Meta'nin teknik
 *   yanit alanlari (events_received / fbtrace_id / messages), atlama sebebi, hata metni.
 *
 * Alan beyaz listesi makine olarak uygulanir (asagidaki LOG_ALANLARI) — yeni alan eklemek
 * isteyen once bu listeye eklemek zorunda, yani gizlilik karari BILEREK verilir.
 */
const LOG_ALANLARI = [
  "olay",            // "Purchase"
  "hedef",           // "meta" | "ga4"
  "siparis_no",      // = event_id (dedup anahtari; kisisel veri DEGIL)
  "kod",             // HTTP durum kodu
  "ok",              // true/false
  "events_received", // Meta teknik yanit
  "fbtrace_id",      // Meta teknik yanit (destek talebinde istenir)
  "mesajlar",        // Meta "messages" dizisi (uyari metinleri)
  "govde",           // hedefin YANIT govdesi (bizim gonderdigimiz DEGIL), kirpilmis
  "atlandi",         // atlama sebebi (secret-yok / user_data-bos / pencere-disi / zaten-denendi)
  "hata",            // istisna metni
  "yas_sn",          // olayin yasi (saniye) — pencere kararinin gerekcesi
  "kaynak",          // "kart" | "havale" (hangi akistan tetiklendi)
];

/** Sir kalintisi maskele (savunma katmani — normalde govdede token OLMAZ, yine de). */
function sirMaskele(s) {
  return String(s || "")
    .replace(/access_token=[^&"\s]+/gi, "access_token=***")
    .replace(/api_secret=[^&"\s]+/gi, "api_secret=***");
}

/** Beyaz liste disindaki her alani DUSUREREK tek satir JSON log basar. */
export function olcumLog(kayit, hataMi) {
  const temiz = {};
  for (const k of LOG_ALANLARI) {
    if (kayit && kayit[k] !== undefined && kayit[k] !== null && kayit[k] !== "") {
      temiz[k] = kayit[k];
    }
  }
  const satir = "olcum " + sirMaskele(JSON.stringify(temiz));
  if (hataMi) { console.error(satir); } else { console.log(satir); }
  return satir;
}

/** Yanit govdesini GUVENLI oku: yoksa/patlasa "" doner, 300 karakterde kirpilir.
 *  (Hedefin KENDI yaniti — bizim PII'miz degil; yine de sir maskesinden gecer.) */
async function yanitOzeti(c) {
  if (!c || typeof c.text !== "function") { return ""; }
  try {
    const t = await c.text();
    return sirMaskele(String(t || "")).slice(0, 300);
  } catch (e) { return ""; }
}

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

/**
 * Meta Conversions API govdesi (PURE — fetch yok; test bunu dogrudan sinar).
 *
 * istemci (opsiyonel) = { ip, ua } — MUSTERININ istegindeki CF-Connecting-IP + User-Agent.
 *
 * 🔒 MIMAR KURALI — META'YA GIDEN user_data'nin TAMAMI `fbp` KAPISINA BAGLI (gevsetilmez):
 *   `_fbp` cerezi SADECE riza kapisindan gecmis tarayici pikselinden dogar. Yani fbp'nin
 *   VARLIGI = o ziyaretcinin olcume riza verdiginin kanitidir. fbp YOKSA riza kaniti da
 *   yoktur -> Meta'ya HICBIR kimlik/kisisel veri aktarilmaz. Bu, "server-side gonderiyoruz,
 *   tarayici rizasi beni baglamaz" hatasina karsi kasitli fren.
 *
 * ✅ KAPININ ARKASINDA (fbp yoksa HICBIRI gitmez):
 *      fbp · fbc (tiklama kimligi) · client_ip_address · client_user_agent
 *   ⚠️ `fbc` 20 Tem'e kadar kapisizdi: fbclid rizasiz da Meta'ya ulasabiliyordu (mimar
 *   denetimi). Artik fbp yoksa fbc de GITMEZ; sonuc olarak user_data BOS kalir ve
 *   metaGonder() olayi hic gondermez.
 *
 * 🚫 BU KAPININ KAPSAMI DISINDA (bilerek — burada COZULMUYOR, yanlis guven vermesin):
 *   1) GA4 MP yolu: `ga_client_id` (_ga cerezi) + UTM parametreleri bu kapiya TABI DEGIL;
 *      ga4Govdesi() onlari fbp'den bagimsiz gonderir.
 *   2) ATIF YAKALAMA tarafi: index.html'deki PRUVO_ATIF fbclid'i riza kontrolu OLMADAN
 *      localStorage'a yaziyor, /baslat da onu D1 `atif` kolonuna kaydediyor. Yani "toplama"
 *      hala acik; bu fonksiyon yalnizca META'YA CIKISI kapatir. Toplama tarafinin
 *      duzeltilmesi AYRI is (mimar sirasinda) — bu dosyada cozulmus SAYILMAZ.
 *
 * ⚠️ HAVALE AKISI: /yonet ekranindan onaylanan havale siparisinde istek OKAN'IN
 *   tarayicisindan gelir -> oradaki IP/UA MUSTERIYE AIT DEGIL. Bu yuzden yonet.js istemci
 *   GECIRMEZ (yanlis kisiyi eslestirmek, hic eslestirmemekten kotudur).
 */
export function metaGovdesi(env, olay, atif, istemci) {
  const user_data = {};
  // TEK KAPI: fbp yoksa asagidaki blogun TAMAMI atlanir -> user_data bos kalir.
  if (atif.fbp) {
    user_data.fbp = atif.fbp;
    if (atif.fbc) { user_data.fbc = atif.fbc; }
    if (istemci) {
      if (istemci.ip) { user_data.client_ip_address = String(istemci.ip); }
      if (istemci.ua) { user_data.client_user_agent = String(istemci.ua); }
    }
  }
  const veri = {
    event_name: "Purchase",
    // Gercek odeme ani (verilmisse); yoksa "simdi". Havalede odeme ani siparis tarihidir.
    event_time: Number(olay.event_time) > 0
      ? Math.floor(Number(olay.event_time))
      : Math.floor(Date.now() / 1000),
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

/** Olayin yasi (saniye). event_time yoksa 0 (= "simdi"). */
export function olayYasi(olay, simdi) {
  const t = Number(olay && olay.event_time);
  if (!(t > 0)) { return 0; }
  const n = Math.floor((simdi || Date.now()) / 1000);
  return n - Math.floor(t);
}

/**
 * Meta CAPI'ye Purchase gonder. Secret/pixel yoksa sessiz no-op.
 * fetchFn + istemci({ip,ua}) test/akis icin enjekte edilir.
 * HER SONUC LOGLANIR (basari tek satir, hata ayrintili) — sessiz yutma YOK.
 */
export async function metaGonder(env, olay, atif, fetchFn, istemci, kaynak) {
  const pixel = env && (env.META_PIXEL_ID || "");
  const token = env && (env.META_CAPI_TOKEN || "");
  const taban = { olay: "Purchase", hedef: "meta", siparis_no: olay.event_id, kaynak: kaynak };
  if (!pixel || !token) {
    // Sessiz DEGIL: secret basilmadigi icin olcum yok — geriye donuk gorunur olmali.
    olcumLog({ ...taban, atlandi: "secret-yok" });
    return { hedef: "meta", atlandi: "secret-yok" };
  }

  // Geriye-donuk pencere: 7 gunden eski olayi Meta reddeder -> gonderme, ama IZ BIRAK.
  const yas = olayYasi(olay);
  if (yas > META_GERIYE_PENCERE_SN) {
    olcumLog({ ...taban, atlandi: "pencere-disi", yas_sn: yas }, true);
    return { hedef: "meta", atlandi: "pencere-disi", yas_sn: yas };
  }

  const govde = metaGovdesi(env, olay, atif, istemci);
  const ud = (govde.data[0] && govde.data[0].user_data) || {};
  if (Object.keys(ud).length === 0) {
    // Buraya DUSMENIN tek sebebi: `fbp` yok (= riza kaniti yok) -> metaGovdesi() kapisi
    // fbp/fbc/IP/UA'nin hepsini tuttu. Yani bu dal AYNI ZAMANDA gizlilik kurali calisiyor
    // demektir; olayin gitmemesi ISTENEN sonuctur, ariza degil.
    // KARAR (gerekce, mimar acigi 2): user_data TAMAMEN bos olay Meta tarafindan ZATEN
    // reddedilir (error 100 / subcode 2804003: en az bir musteri parametresi zorunlu).
    // Gondermek = garanti 400 + bos kota + Events Manager'da kirmizi gurultu; DAHASI
    // "gitti sanip" yanlis guven verir. Bu yuzden GONDERMIYORUZ — ama SESSIZCE degil:
    // atlama loglanir, boylece "bu siparisin Purchase'i neden yok?" sorusu cevaplanabilir.
    // (Eslesmeyi duzeltmenin dogru yolu riza kapisindan gecen tarayici pikselidir; fbp
    // dogunca hem fbp hem IP/UA gider. GA4 bundan ETKILENMEZ — client_id fallback'i var.)
    olcumLog({ ...taban, atlandi: "user_data-bos" }, true);
    return { hedef: "meta", atlandi: "user_data-bos" };
  }

  const f = fetchFn || fetch;
  // ⚠️ url access_token ICERIR -> hicbir log alanina KONMAZ (LOG_ALANLARI'nda "url" yok).
  const url = "https://graph.facebook.com/" + META_API_SURUM + "/" + pixel +
    "/events?access_token=" + encodeURIComponent(token);
  const c = await f(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(govde),
  });
  const kod = c && c.status;
  const ok = kod >= 200 && kod < 300;
  const ham = await yanitOzeti(c);
  let coz = null;
  try { coz = ham ? JSON.parse(ham) : null; } catch (e) { coz = null; }
  const sonuc = { hedef: "meta", kod: kod, ok: ok };
  if (coz && coz.events_received !== undefined) { sonuc.events_received = coz.events_received; }
  if (coz && coz.fbtrace_id) { sonuc.fbtrace_id = coz.fbtrace_id; }
  if (ok) {
    // Basari: TEK SATIR, kisa (log sismesin).
    olcumLog({ ...taban, kod: kod, ok: true,
               events_received: sonuc.events_received, fbtrace_id: sonuc.fbtrace_id });
  } else {
    // 🔴 Onceden BURASI SESSIZDI (fetch 4xx'te throw etmez) — artik hata govdesi loglanir.
    sonuc.govde = ham;
    olcumLog({ ...taban, kod: kod, ok: false, govde: ham,
               fbtrace_id: (coz && coz.error && coz.error.fbtrace_id) || sonuc.fbtrace_id }, true);
  }
  return sonuc;
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
  const g = { client_id: client_id, events: [{ name: "purchase", params: params }] };
  // Gercek odeme ani: GA4 timestamp_micros'u YALNIZ son 72 saat icin kabul eder; daha
  // eskisinde olay DUSER -> damgayi koymayiz (GA4 "simdi" sayar, ciro yine kaydedilir).
  const yas = olayYasi(olay);
  if (Number(olay.event_time) > 0 && yas <= GA4_DAMGA_PENCERE_SN) {
    g.timestamp_micros = String(Math.floor(Number(olay.event_time)) * 1000000);
  }
  return g;
}

/** GA4 MP'ye purchase gonder. measurement_id + api_secret yoksa sessiz no-op.
 *  Yanit LOGLANIR (MP normalde 204 doner; DebugView modunda validationMessages gelir). */
export async function ga4Gonder(env, olay, atif, fetchFn, kaynak) {
  const mid = env && (env.GA4_MEASUREMENT_ID || "");
  const gizli = env && (env.GA4_API_SECRET || "");
  const taban_log = { olay: "Purchase", hedef: "ga4", siparis_no: olay.transaction_id,
                      kaynak: kaynak };
  if (!mid || !gizli) {
    olcumLog({ ...taban_log, atlandi: "secret-yok" });
    return { hedef: "ga4", atlandi: "secret-yok" };
  }
  const f = fetchFn || fetch;
  const taban = (env && env.GA4_DEBUG)
    ? "https://www.google-analytics.com/debug/mp/collect"
    : "https://www.google-analytics.com/mp/collect";
  // ⚠️ url api_secret ICERIR -> loglanmaz.
  const url = taban + "?measurement_id=" + encodeURIComponent(mid) +
    "&api_secret=" + encodeURIComponent(gizli);
  const c = await f(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ga4Govdesi(env, olay, atif)),
  });
  const kod = c && c.status;
  const ok = kod >= 200 && kod < 300;
  const sonuc = { hedef: "ga4", kod: kod, ok: ok };
  if (ok) {
    // MP 2xx = "kabul edildi" (icerik dogrulamasi yapmaz) — tek satir iz yeterli.
    // DebugView modunda govde validationMessages tasir, o da yazilir.
    const ham = (env && env.GA4_DEBUG) ? await yanitOzeti(c) : "";
    olcumLog({ ...taban_log, kod: kod, ok: true, govde: ham });
  } else {
    sonuc.govde = await yanitOzeti(c);
    olcumLog({ ...taban_log, kod: kod, ok: false, govde: sonuc.govde }, true);
  }
  return sonuc;
}

// ---------------------------------------------------------------- orkestrasyon

/** Bir hedefi calistir; hata FIRLATMAZ (siparis akisini bozmaz) — yakalar, loglar, doner.
 *  Log gizlilik kapisindan gecer (istisna metni disinda kisisel veri tasimaz). */
async function guvenli(fn, taban) {
  try { return await fn(); }
  catch (e) {
    const metin = String((e && e.message) || e);
    olcumLog({ ...(taban || {}), hata: metin }, true);
    return { ...(taban || {}), hata: metin };
  }
}

/**
 * Purchase olayini iki hedefe FIRE-AND-FORGET gonder. ctx.waitUntil ile arka planda kosar;
 * yanit/musteri akisi BLOKLANMAZ. Her hedef guvenli() icinde — biri patlasa digeri + siparis
 * onayi ETKILENMEZ. Test icin: donen promise await edilebilir, ctx sahte olabilir.
 *
 * secenek (opsiyonel):
 *   - istemci   : {ip, ua} MUSTERININ istegi (kart akisi). Havalede VERILMEZ — bkz metaGovdesi.
 *   - event_time: gercek odeme ani (saniye). Verilmezse "simdi".
 *   - kaynak    : "kart" | "havale" (yalniz log etiketi).
 */
export function olcumGonder(env, ctx, siparis, fetchFn, secenek) {
  const s = secenek || {};
  const olay = satinAlmaOlayi(siparis);
  if (Number(s.event_time) > 0) { olay.event_time = Math.floor(Number(s.event_time)); }
  const atif = atifCoz(siparis);
  const p = Promise.all([
    guvenli(() => metaGonder(env, olay, atif, fetchFn, s.istemci, s.kaynak),
      { olay: "Purchase", hedef: "meta", siparis_no: olay.event_id, kaynak: s.kaynak }),
    guvenli(() => ga4Gonder(env, olay, atif, fetchFn, s.kaynak),
      { olay: "Purchase", hedef: "ga4", siparis_no: olay.event_id, kaynak: s.kaynak }),
  ]);
  if (ctx && typeof ctx.waitUntil === "function") { ctx.waitUntil(p); }
  return p;
}

export default olcumGonder;
