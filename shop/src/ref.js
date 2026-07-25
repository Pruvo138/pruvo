/**
 * pruvo-shop — wa.me lead REF -> click-id kalicilik ucu (OCI #1).
 *
 * Landing modulu (attribution-ref.js) paid oturumda REF:GS-<GRUP>-<RND4> uretir ve tiklama
 * click-id'lerini (gclid/gbraid/wbraid) YALNIZ localStorage'da tutar. wa.me-lead sunucuya
 * bugune dek yalniz REF'i tasiyordu -> click-id musterinin tarayicisinda kalip kayboluyordu,
 * o lead icin sonraki OCI feed'i (offline conversion import) IMKANSIZDI. Bu uc, lead aninda
 * gonderilen beacon'i alip REF->click-id eslemesini KATALOG D1'de (reklam_ref_gclid) kalici kilar.
 *
 * ORGANIK YOL (src=OG): landing modulu artik arama-motoru referrer'li (click-id'siz) oturumlarda
 * da REF uretir -> REF:OG-<GRUP>-<RND4>, src="OG". Bu uc onlari da loglar (click-id kolonlari
 * NULL). ArTisT'in organik ROI halkasini kapatir. OG kaydinda PII (click-id) YOKTUR; sinif olarak
 * paid REF ile ayni (ref+grup+src+ts). Organik uc AUTH'suz + click-id'siz oldugundan spam yuzeyi
 * paid'den GENIS -> EK savunma: ORIGIN GUARD (istegin Origin/Referer host'u bizim alan adimiz
 * olmali; degilse 403, D1'e gitmez).
 *
 * KIRMIZI CIZGILER:
 *  - click-id URL param DEGIL, POST GOVDESINDE gelir (guvenlik).
 *  - Auth yok (public beacon). Savunma (paid) = IP basina RATE-LIMIT + SIKI regex + uzunluk
 *    siniri + INSERT OR IGNORE. Organik (OG) = ustune ORIGIN GUARD.
 *  - 204 No Content (govdesiz) VARSAYILAN — bilgi sizdirma yok; beacon yaniti okumaz. TEK
 *    istisna: organik (OG) yolda yanlis/eksik origin -> 403 (abuse reddi; paid yol hep 204).
 *  - first-write-wins: REF PRIMARY KEY, INSERT OR IGNORE -> ayni REF ikinci kez gelirse dokunulmaz.
 *
 * IP RATE-LIMIT (kota koruma): INSERT OR IGNORE yalniz AYNI ref'i tekilleştirir; saldirgan
 * sinirsiz FARKLI gecerli-format REF POST'layarak PAYLASILAN pruvo-katalog D1'inin gunluk
 * yazma kotasini (Ege / d1-sync ile ortak) tuketebilir. Cozum: IP basina soft-cap (native
 * Cloudflare rate limiting binding env.REF_RATE_LIMIT — EK D1 YAZMASI YOK; kota sorununu
 * kota harcayarak cozmez). Cap asilinca D1'e HIC gidilmez, yine 204 (davranis/bilgi sizmaz).
 * Rate-limit validasyonun ONUNDE calisir. Binding tanimsizsa (yerel test / henuz deploy
 * edilmemis) sessizce atlanir = fail-open: mevcut davranis korunur, kod merge canliyi bozmaz.
 *
 * Saf (index.js'ten bagimsiz) tutulur ki wrangler'siz birim-test edilebilsin (shop/test/ref-route.mjs).
 */

// Landing kanonigiyle BIREBIR (attribution-ref.js REF_RE). Uymazsa yazilmaz.
const REF_RE = /^REF:[A-Z]{2}-[A-Z0-9]{2,4}-[A-Z0-9]{4}$/;
const GRUP_RE = /^[A-Z0-9]{2,4}$/;
const SRC_RE = /^[A-Z]{2}$/;
const CLICK_ID_ENCOK = 512;

/** click-id (gclid/gbraid/wbraid) temizle: string + 1..512 uzunluk -> deger, aksi -> null.
 *  Icerik opak (Google formati); regex ile daraltilmaz, yalniz tip + uzunluk. Asiri uzun
 *  deger KIRPILMAZ (kirpik click-id Google'da eslesmez, cop olurdu) -> reddedilir (null). */
function clickId(v) {
  if (typeof v !== "string") { return null; }
  if (v.length < 1 || v.length > CLICK_ID_ENCOK) { return null; }
  return v;
}

/**
 * Beacon govdesini dogrula + sanitize. Yazilabilir kayit -> {ref, gclid, gbraid, wbraid, grup,
 * src, ts}; yazilmamasi gereken (bozuk ref / click-id yok / gecersiz govde) -> null.
 * grup/src/ts gecersizse ATILIR (null) ama kayit reddedilmez; ref ve >=1 click-id ZORUNLU.
 */
export function refDogrula(govde) {
  if (!govde || typeof govde !== "object" || Array.isArray(govde)) { return null; }
  const ref = typeof govde.ref === "string" ? govde.ref : "";
  if (!REF_RE.test(ref)) { return null; }

  const gclid = clickId(govde.gclid);
  const gbraid = clickId(govde.gbraid);
  const wbraid = clickId(govde.wbraid);

  const grup = (typeof govde.grup === "string" && GRUP_RE.test(govde.grup)) ? govde.grup : null;
  const src = (typeof govde.src === "string" && SRC_RE.test(govde.src)) ? govde.src : null;
  const ts = Number.isFinite(govde.ts) ? govde.ts : null;

  // Click-id YOK: eskiden dogrudan reddediliyordu. YENI: yalniz GERCEK ORGANIK (src TAM "OG" +
  // ref "REF:OG-" onekli — REF_RE zaten yukarida gecti) kayit KABUL, click-id kolonlari NULL.
  // src/ref tutarsizsa (or. paid kaynak koduyla gelip click-id'siz kalmis, ya da ref OG-onekli
  // ama src eksik) eski davranis: loglanmaz (null). Anti-abuse origin guard'i refKaydet'te.
  if (!gclid && !gbraid && !wbraid) {
    if (src === "OG" && ref.indexOf("REF:OG-") === 0) {
      return { ref, gclid: null, gbraid: null, wbraid: null, grup, src, ts };
    }
    return null;
  }

  return { ref, gclid, gbraid, wbraid, grup, src, ts };
}

/** 204 No Content (govdesiz). Paid yol + gecerli organik: statu tek bit bilgi bile sizdirmaz. */
function bosCevap() {
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}

/** 403 (govdesiz) — YALNIZ organik (OG) yolda yanlis/eksik origin (abuse reddi). */
function reddet() {
  return new Response(null, { status: 403, headers: { "Cache-Control": "no-store" } });
}

// ---- ANTI-ABUSE: ORIGIN GUARD (yalniz organik/OG yol) -----------------------
// Organik uc AUTH'suz + click-id'siz kabul eder -> paid'e gore GENIS spam yuzeyi. Ek savunma:
// istegin Origin (yoksa Referer) host'u BIZIM alan adimiz olmali. sendBeacon POST her modern
// tarayicida Origin tasir (Fetch spec: GET/HEAD disi istekte Origin ZORUNLU) -> gercek beacon
// gecer; baska origin'den (ya da origin'siz curl/bot) gelen OG POST 403 alir (D1'e ulasmaz).
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

/** Origin (yoksa Referer) host'u izinli mi? Ikisi de yok -> FAIL-CLOSED (false): organik icin
 *  kaynak kaniti ZORUNLU. Paid yolda CAGRILMAZ -> paid davranisi birebir korunur. */
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

/**
 * POST /api/shop/ref handler. Yalniz POST; application/json govde parse (hata -> 204).
 * Gecerli kayit -> KATALOG D1'e INSERT OR IGNORE (created_at = sunucu Date.now()). Yazma
 * hatasi yutulur (fire-and-forget: beacon'i bloklamaz). HER durumda 204 doner.
 */
/**
 * IP basina soft-cap (D1 kota koruma). Native Cloudflare rate limiting binding
 * (env.REF_RATE_LIMIT) EK D1 YAZMASI YAPMAZ; cap asilinca true doner -> cagiran D1'e gitmeden
 * 204 verir. Binding tanimsizsa (yerel test / henuz deploy edilmemis) false = fail-open. Limiter
 * kendisi patlarsa da fail-open: beacon bloklanmaz (attribution best-effort), yuksek sesli log.
 */
async function kotaAsildi(request, env) {
  const rl = env && env.REF_RATE_LIMIT;
  if (!rl || typeof rl.limit !== "function") { return false; }   // binding yok -> fail-open
  const ip = (request.headers && typeof request.headers.get === "function"
    ? request.headers.get("CF-Connecting-IP") : "") || "yok";
  try {
    const sonuc = await rl.limit({ key: ip });
    return !(sonuc && sonuc.success);                            // success !== true -> cap asildi
  } catch (e) {
    console.error("ref rate-limit hatasi (fail-open):", (e && e.stack) || e);
    return false;                                               // limiter patlarsa beacon'i bloklama
  }
}

export async function refKaydet(request, env) {
  if (request.method !== "POST") { return bosCevap(); }

  // RATE-LIMIT validasyonun ONUNDE: cap asilinca D1'e HIC gidilmez, yine 204 (davranis degismez).
  if (await kotaAsildi(request, env)) { return bosCevap(); }

  let govde;
  try {
    govde = await request.json();
  } catch (e) {
    return bosCevap();
  }

  const kayit = refDogrula(govde);
  if (!kayit) { return bosCevap(); }

  // ANTI-ABUSE: organik (OG) yol AUTH'suz + click-id'siz -> ORIGIN GUARD ZORUNLU. Yanlis/eksik
  // origin -> 403 (D1'e HIC gidilmez). Paid yol (>=1 click-id) DEGISMEZ: guard cagrilmaz, 204.
  if (kayit.src === "OG" && !originIzinli(request, env)) { return reddet(); }

  try {
    await env.KATALOG.prepare(
      "INSERT OR IGNORE INTO reklam_ref_gclid" +
      " (ref, gclid, gbraid, wbraid, grup, src, ts, created_at)" +
      " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
      kayit.ref, kayit.gclid, kayit.gbraid, kayit.wbraid,
      kayit.grup, kayit.src, kayit.ts, Date.now()
    ).run();
  } catch (e) {
    // click-id kacsa bile beacon 204 doner; hata gorunur log'a.
    console.error("reklam_ref_gclid yazilamadi:", (e && e.stack) || e);
  }

  return bosCevap();
}
