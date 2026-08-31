/**
 * iyzico HMACSHA256 (IYZWSv2) istemcisi — Checkout Form initialize + retrieve.
 *
 * Imza semasi (docs.iyzico.com > HMACSHA256 Auth):
 *   signature = hex( HMACSHA256( randomKey + uri.path + requestBody, secretKey ) )
 *   Authorization: IYZWSv2 base64("apiKey:" + apiKey + "&randomKey:" + rnd + "&signature:" + sig)
 *
 * Model HOSTED/REDIRECT: initialize cevabindaki paymentPageUrl'e musteri YONLENDIRILIR,
 * kart bilgisi iyzico'da girilir (3DS dahil). Sitede kart formu YOK — kirmizi cizgi.
 */

const INIT_YOL = "/payment/iyzipos/checkoutform/initialize/auth/ecom";
const DETAY_YOL = "/payment/iyzipos/checkoutform/auth/ecom/detail";

function hex(buf) {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function istek(env, yol, govde) {
  const beden = JSON.stringify(govde);
  const rnd = Date.now() + "" + Math.floor(100000 + Math.random() * 900000);
  const kodla = new TextEncoder();
  const anahtar = await crypto.subtle.importKey(
    "raw", kodla.encode(env.IYZICO_SECRET_KEY),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const imza = hex(await crypto.subtle.sign("HMAC", anahtar, kodla.encode(rnd + yol + beden)));
  const yetki = "IYZWSv2 " + btoa("apiKey:" + env.IYZICO_API_KEY + "&randomKey:" + rnd + "&signature:" + imza);

  const c = await fetch(env.IYZICO_BASE_URL + yol, {
    method: "POST",
    headers: { "Authorization": yetki, "x-iyzi-rnd": rnd, "Content-Type": "application/json" },
    body: beden,
  });
  const metin = await c.text();
  try {
    return JSON.parse(metin);
  } catch (e) {
    // iyzico her zaman JSON doner; donmuyorsa altyapi hatasi — status'la birlikte yukari tasi.
    return { status: "failure", errorCode: "HTTP-" + c.status, errorMessage: metin.slice(0, 300) };
  }
}

/** Hata metninde token'i maskelemeden ONCE istenen ASGARI uzunluk. Kisa/bos bir "gizle"
 *  degeriyle `split` yapmak metni parcalar (bos dizge her karakteri boler) ya da yaygin bir
 *  alt-dizeyi kor ederdi; boyle bir deger maskelenmeden GECER (metin zaten kirpilir). */
const MASKE_ASGARI = 8;

/** Hata metninin log tavani. iyzico'nun ham 4xx govdesi 300 karaktere kadar gelebilir;
 *  logda teshis icin gereken bas kisimdir, tamami degil. */
const METIN_TAVANI = 200;

/**
 * 🔴 RETRIEVE HATA KIMLIGI — TEK KAYNAK (K356, 31 Agu 2026).
 *
 * `istek()` iyzico'nun basarisiz cevabini `{ status:"failure", errorCode, errorMessage }`
 * seklinde yukari tasir (JSON parse edilemezse de AYNI sekli uydurur: "HTTP-<kod>").
 * Bu iki yardimci o seklin TEK okuyucusudur; cagiran yerde `det.errorCode` diye elle
 * okumak ikinci bir hukum acardi.
 *
 * 🔴 "YOK" BILEREK BIR DEGERDIR: `det` null/bos ya da alan bossa sessiz bos satir basmak,
 * bu kolun varolus sebebini (NEDEN ulasilamadi?) cevapsiz birakirdi — "alan yoktu" ile
 * "satir hic basilmadi" ayni goruntuye coker.
 */
export function hataKodu(det) {
  const k = det && det.errorCode;
  return (k === undefined || k === null || k === "") ? "YOK" : String(k);
}

/**
 * Hata METNI — `hataKodu` ile ayni "YOK" sozlesmesi + IKI GIZLILIK KAPISI:
 *   ① TOKEN MASKESI: JSON parse edilemeyen cevapta `errorMessage` iyzico'nun HAM govdesidir
 *      ve istegimizi ECHO edebilir; istegin icinde odeme token'i vardir. `gizle` verilirse
 *      metinden CIKARILIR. (Kart verisi bize hic ugramaz — sitede kart formu YOK.)
 *   ② KIRPMA: teshis icin bas kisim yeter; siniri asan kuyruk loga girmez.
 * Musteri alanlari (ad/tel/eposta/adres) buraya YAPISAL OLARAK giremez: girdi yalniz
 * iyzico'nun kendi cevabidir, D1 satiri DEGIL.
 */
export function hataMetni(det, gizle) {
  const m = det && det.errorMessage;
  if (m === undefined || m === null || m === "") { return "YOK"; }
  let s = String(m);
  const g = String(gizle == null ? "" : gizle);
  if (g.length >= MASKE_ASGARI) { s = s.split(g).join("***"); }
  return s.slice(0, METIN_TAVANI);
}

export function cfBaslat(env, govde) {
  return istek(env, INIT_YOL, govde);
}

export function cfDetay(env, token) {
  return istek(env, DETAY_YOL, { locale: "tr", token: token });
}
