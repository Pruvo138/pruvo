/**
 * pruvo-shop — RIZA BAGIMSIZ reklam INIS sayaci (POST /api/shop/inis).
 *
 * GA4 riza vermeyen ziyaretciyi gormez -> reklam inislerinin bir kismi olcum disinda kalir. Bu uc
 * yalniz (sunucu UTC gunu, kaynak, kampanya) uclusunu SAYAR; kisisel veri SIFIR oldugu icin riza
 * kapisi gerekmez. Istemci kolu: foto-uretim.js (utm_source'lu acilista oturum basina TEK beacon).
 *
 * KIRMIZI CIZGILER:
 *  - IP / UA / cerez / ref / tam URL OKUNMAZ, SAKLANMAZ, LOGLANMAZ. Tek okunan istek basliklari
 *    Origin ve Referer'dir — yalniz HOST'u izin kumesine karsi denetlenir, hicbir yere yazilmaz.
 *  - gun = SUNUCU UTC tarihi; istemcinin gonderdigi tarih/alan OKUNMAZ (govdeden yalniz s, c).
 *  - Kardinalite tavani: kaynak BEYAZ LISTE disindaysa "diger"; kampanya kalibi tutmuyorsa ya da
 *    kaynak "diger" ise "-". Boylece satir uzayi saldirgan girdisiyle sinirsiz buyumez.
 *  - ORIGIN GUARD (ref.js ile ayni mantik): Origin (yoksa Referer) host'u bizim alan adimiz olmali;
 *    yanlis ya da ikisi de yok -> 403, D1'e gidilmez.
 *  - RATE LIMIT env.INIS_RATE_LIMIT (AYRI namespace, shop/wrangler.toml). IP okunmadigi icin anahtar
 *    beyaz listeli kaynaktir. FAIL-CLOSED-SESSIZ: binding yok / limiter patladi / cap asildi -> 204,
 *    D1'e YAZILMAZ (sayac en-iyi-caba bir olcumdur; eksik sayim, sinirsiz yazimdan ucuzdur).
 *  - Basari ve sessiz red AYNI cevap: 204 (govdesiz). Tek istisna yanlis origin -> 403.
 *
 * Saf (index.js'ten bagimsiz, importsuz) tutulur ki wrangler'siz birim-test edilebilsin
 * (shop/test/inis-sayac.mjs).
 */

const KAYNAKLAR = new Set([
  "google", "bing", "chatgpt.com", "perplexity", "copilot", "facebook", "fb", "instagram", "ig",
  "meta", "tiktok", "youtube", "pinterest", "email", "whatsapp",
]);
const KAMPANYA_RE = /^[a-z0-9._-]{1,48}$/;

function bosCevap() {
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}

function reddet() {
  return new Response(null, { status: 403, headers: { "Cache-Control": "no-store" } });
}

// ---- ORIGIN GUARD — shop/src/ref.js ile BIREBIR mantik (kopya; ref.js degistirilmez) ----
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

/** Govde {s, c} -> {kaynak, kampanya}. Govdenin baska hicbir alani (or. gun) OKUNMAZ. */
export function inisDogrula(govde) {
  const g = (govde && typeof govde === "object" && !Array.isArray(govde)) ? govde : {};
  const s = typeof g.s === "string" ? g.s.toLowerCase() : "";
  const c = typeof g.c === "string" ? g.c.toLowerCase() : "";
  const kaynak = KAYNAKLAR.has(s) ? s : "diger";
  const kampanya = (kaynak !== "diger" && KAMPANYA_RE.test(c)) ? c : "-";
  return { kaynak, kampanya };
}

/** Limiter izin verdi mi? Binding yoksa (inisKaydet onceden eler) ya da patlarsa false. */
async function kotaIzinli(rl, kaynak) {
  try {
    const sonuc = await rl.limit({ key: "inis:" + kaynak });
    return !!(sonuc && sonuc.success === true);
  } catch (e) {
    return false;                                              // fail-closed-sessiz
  }
}

export async function inisKaydet(request, env) {
  if (request.method !== "POST") { return bosCevap(); }

  // ORIGIN GUARD: yanlis/eksik origin -> 403, D1'e HIC gidilmez.
  if (!originIzinli(request, env)) { return reddet(); }

  // RATE LIMIT binding'i yoksa (yerel / henuz deploy edilmemis) D1'e gidilmez: fail-closed-sessiz.
  const rl = env && env.INIS_RATE_LIMIT;
  if (!rl || typeof rl.limit !== "function") { return bosCevap(); }

  let govde;
  try {
    govde = await request.json();
  } catch (e) {
    return bosCevap();
  }

  const { kaynak, kampanya } = inisDogrula(govde);
  if (!(await kotaIzinli(rl, kaynak))) { return bosCevap(); }

  const gun = new Date().toISOString().slice(0, 10);          // SUNUCU UTC gunu
  try {
    await env.KATALOG.prepare(
      "INSERT INTO inis_sayac(gun,kaynak,kampanya,n) VALUES(?,?,?,1)" +
      " ON CONFLICT(gun,kaynak,kampanya) DO UPDATE SET n=n+1"
    ).bind(gun, kaynak, kampanya).run();
  } catch (e) {
    // Istek verisi LOGLANMAZ; yalniz hata metni.
    console.error("inis_sayac yazilamadi:", (e && e.message) || String(e));
  }

  return bosCevap();
}
