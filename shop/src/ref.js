/**
 * pruvo-shop — wa.me lead REF -> click-id kalicilik ucu (OCI #1).
 *
 * Landing modulu (attribution-ref.js) paid oturumda REF:GS-<GRUP>-<RND4> uretir ve tiklama
 * click-id'lerini (gclid/gbraid/wbraid) YALNIZ localStorage'da tutar. wa.me-lead sunucuya
 * bugune dek yalniz REF'i tasiyordu -> click-id musterinin tarayicisinda kalip kayboluyordu,
 * o lead icin sonraki OCI feed'i (offline conversion import) IMKANSIZDI. Bu uc, lead aninda
 * gonderilen beacon'i alip REF->click-id eslemesini KATALOG D1'de (reklam_ref_gclid) kalici kilar.
 *
 * KIRMIZI CIZGILER:
 *  - click-id URL param DEGIL, POST GOVDESINDE gelir (guvenlik).
 *  - Auth yok (public beacon). Savunma = IP basina RATE-LIMIT + SIKI regex + uzunluk siniri
 *    + INSERT OR IGNORE.
 *  - HER ZAMAN 204 No Content (govdesiz) — bilgi sizdirma yok; beacon yaniti okumaz.
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
  // Organik (hicbir click-id yok) -> loglanmaz.
  if (!gclid && !gbraid && !wbraid) { return null; }

  const grup = (typeof govde.grup === "string" && GRUP_RE.test(govde.grup)) ? govde.grup : null;
  const src = (typeof govde.src === "string" && SRC_RE.test(govde.src)) ? govde.src : null;
  const ts = Number.isFinite(govde.ts) ? govde.ts : null;

  return { ref, gclid, gbraid, wbraid, grup, src, ts };
}

/** 204 No Content (govdesiz). Her donusu bu — statu tek bit bilgi bile sizdirmaz. */
function bosCevap() {
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
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
