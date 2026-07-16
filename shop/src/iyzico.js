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

export function cfBaslat(env, govde) {
  return istek(env, INIT_YOL, govde);
}

export function cfDetay(env, token) {
  return istek(env, DETAY_YOL, { locale: "tr", token: token });
}
