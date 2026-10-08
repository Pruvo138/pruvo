/**
 * ONIZLEME SURUMU (FOTO-DUZEN-d, 7 Eki 2026) — `pruvo-shop`un canliyi etkilemeyen surumu.
 *
 * Yukleme: `npx wrangler versions upload -c shop/wrangler.onizleme.toml --preview-alias ...`
 * (DEPLOY YOK — aktif dagitim degismez). Ayni worker adi -> secret'lar degersiz devralinir;
 * D1/R2 onizlemeye ozel (canli D1/kovaya baglanti YOK). Bu modul iki seyi tek yerde tutar:
 *
 *  1) ODEME ZORLA KAPALI: `ONIZLEME === "1"` iken odeme/sepet uclari 503 doner; iyzico'ya
 *     hicbir istek gitmez (devralinan iyzico anahtari onizlemede KULLANILAMAZ).
 *  2) BOT DOGRULAMA ALANI: Turnstile hostname listesi canli iki alan adidir. Onizleme alani
 *     YALNIZ `ONIZLEME === "1"` VE `ONIZLEME_HOST` doluyken eklenir -> canlida (ikisi de bos)
 *     davranis AYNEN; biri tek basina listeyi GENISLETMEZ.
 *
 * Kabul: shop/test/onizleme-kapisi.mjs (mutantlar dahil).
 */

const CANLI_HOSTLAR = ["pruvo3d.com", "www.pruvo3d.com"];

// Onizlemede 503 donen yollar (/api/shop oneki atilmis): odeme baslatma, iyzico donusu,
// satin alma olcum kapisi ve sepet fiyat provasi (onizleme D1'inde katalog yok).
export const ONIZLEME_KAPALI_YOLLAR = ["/baslat", "/donus", "/olcum-donus", "/fiyat"];

export function onizlemeMi(env) {
  return !!env && String(env.ONIZLEME || "") === "1";
}

export function onizlemeOdemeKapali(env, yol) {
  return onizlemeMi(env) && ONIZLEME_KAPALI_YOLLAR.includes(yol);
}

/** Turnstile `hostname` alani kabul edilir mi (canli iki alan + yalniz onizlemede onizleme alani). */
export function turnstileHostKabul(env, hostname) {
  const h = String(hostname || "");
  if (CANLI_HOSTLAR.includes(h)) { return true; }
  const ek = onizlemeMi(env) ? String(env.ONIZLEME_HOST || "").trim() : "";
  return ek !== "" && h === ek;
}
