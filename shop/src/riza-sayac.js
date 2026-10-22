/**
 * pruvo-shop — KIMLIKSIZ RIZA SAYACI (POST /api/shop/riza).
 *
 * KVKK riza bandinda verilen kararin (kabul / ret / kapat) GUNLUK TOPLAMINI sayar: bandin gercekte
 * ne kadar rizasizlik urettigi GA4'ten olculemez (reddeden GA4'e hic gorunmez). Bu uc yalniz
 * (sunucu UTC gunu, karar) ikilisini SAYAR; kisisel veri SIFIR oldugu icin riza kapisi gerekmez.
 * Istemci kolu: riza bandi kaydet() — karar localStorage'a YAZILDIKTAN sonra TEK sendBeacon {k}.
 *
 * KIRMIZI CIZGILER (src/inis.js deseni BIREBIR):
 *  - IP / UA / cerez / ref / tam URL OKUNMAZ, SAKLANMAZ, LOGLANMAZ. Tek okunan istek basliklari
 *    Origin ve Referer'dir — yalniz HOST'u izin kumesine karsi denetlenir, hicbir yere yazilmaz.
 *  - gun = SUNUCU UTC tarihi; istemcinin gonderdigi tarih/alan OKUNMAZ (govdeden yalniz k).
 *  - Karar BEYAZ LISTE: "kabul" | "ret" | "kapat". Disindaki her deger -> 204, D1'e YAZILMAZ
 *    (inis'teki "diger" kovasi yok: bilinmeyen karar sayilmaz, satir uzayi 3 ile sinirli).
 *  - ORIGIN GUARD (ref.js / inis.js ile ayni mantik): Origin (yoksa Referer) host'u bizim alan
 *    adimiz olmali; yanlis ya da ikisi de yok -> 403, D1'e gidilmez.
 *  - RATE LIMIT env.RIZA_RATE_LIMIT (AYRI namespace, shop/wrangler.toml). IP okunmadigi icin anahtar
 *    karardir. FAIL-CLOSED-SESSIZ: binding yok / limiter patladi / cap asildi -> 204, D1'e YAZILMAZ.
 *  - Basari ve sessiz red AYNI cevap: 204 (govdesiz). Tek istisna yanlis origin -> 403.
 *
 * Saf (index.js'ten bagimsiz, importsuz) tutulur ki wrangler'siz birim-test edilebilsin
 * (shop/test/riza-sayac.mjs).
 */

const KARARLAR = new Set(["kabul", "ret", "kapat"]);

function bosCevap() {
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}

function reddet() {
  return new Response(null, { status: 403, headers: { "Cache-Control": "no-store" } });
}

// ---- ORIGIN GUARD — shop/src/inis.js ile BIREBIR mantik (kopya; inis.js degistirilmez) ----
function birHost(deger) {
  if (typeof deger !== "string" || !deger) { return null; }
  try { return new URL(deger).host.toLowerCase(); } catch (e) { return null; }
}

function izinliHostlar(env) {
  const set = new Set(["pruvo3d.com", "www.pruvo3d.com"]);
  const h = birHost(env && env.SITE_URL);   // staging/workers.dev icin KENDI config'imiz
  if (h) { set.add(h); }
  return set;
}

/** Origin (yoksa Referer) host'u izinli mi? Ikisi de yok -> FAIL-CLOSED (false). */
function originIzinli(request, env) {
  const h = request && request.headers;
  if (!h || typeof h.get !== "function") { return false; }
  const izin = izinliHostlar(env);
  const origin = birHost(h.get("Origin"));
  if (origin) { return izin.has(origin); }
  const referer = birHost(h.get("Referer"));
  if (referer) { return izin.has(referer); }
  return false;
}

/** Govde {k} -> karar ya da null. Govdenin baska hicbir alani (or. gun) OKUNMAZ. */
export function rizaDogrula(govde) {
  const g = (govde && typeof govde === "object" && !Array.isArray(govde)) ? govde : {};
  const k = typeof g.k === "string" ? g.k : "";
  return KARARLAR.has(k) ? k : null;
}

/** Limiter izin verdi mi? Binding yoksa (rizaKaydet onceden eler) ya da patlarsa false. */
async function kotaIzinli(rl, karar) {
  try {
    const sonuc = await rl.limit({ key: "riza:" + karar });
    return !!(sonuc && sonuc.success === true);
  } catch (e) {
    return false;                                              // fail-closed-sessiz
  }
}

export async function rizaKaydet(request, env) {
  if (request.method !== "POST") { return bosCevap(); }

  // ORIGIN GUARD: yanlis/eksik origin -> 403, D1'e HIC gidilmez.
  if (!originIzinli(request, env)) { return reddet(); }

  // RATE LIMIT binding'i yoksa (yerel / henuz deploy edilmemis) D1'e gidilmez: fail-closed-sessiz.
  const rl = env && env.RIZA_RATE_LIMIT;
  if (!rl || typeof rl.limit !== "function") { return bosCevap(); }

  let govde;
  try {
    govde = await request.json();
  } catch (e) {
    return bosCevap();
  }

  const karar = rizaDogrula(govde);
  if (karar === null) { return bosCevap(); }                 // beyaz liste disi -> yazilmaz
  if (!(await kotaIzinli(rl, karar))) { return bosCevap(); }

  const gun = new Date().toISOString().slice(0, 10);          // SUNUCU UTC gunu
  try {
    await env.KATALOG.prepare(
      "INSERT INTO riza_sayac(gun,karar,n) VALUES(?,?,1)" +
      " ON CONFLICT(gun,karar) DO UPDATE SET n=n+1"
    ).bind(gun, karar).run();
  } catch (e) {
    // Istek verisi LOGLANMAZ; yalniz hata metni.
    console.error("riza_sayac yazilamadi:", (e && e.message) || String(e));
  }

  return bosCevap();
}
