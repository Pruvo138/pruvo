/**
 * OLCUM TEST KAPISI — yerel testin GERCEK Meta pikseline / GA4 mulkune basmasini onler.
 *
 * NEDEN VAR (mimar denetimi, 20 Tem): `kabul.js` worker'i `wrangler dev --local` ile
 * kosturur ve `wrangler.toml`'daki [vars] degerleri OLDUGU GIBI yuklenir — orada GERCEK
 * piksel ID'si (META_PIXEL_ID) ve GERCEK GA4 measurement ID'si var. Bugun zarar yok, cunku
 * CAPI token'i/GA4 api_secret'i yok -> olcum.js no-op'a duser. AMA Okan bir gun `.dev.vars`'a
 * `META_CAPI_TOKEN` koyarsa (yerel gelistirme icin gayet makul), kabul testi tek kosuda
 * GERCEK piksele DUZINELERCE SAHTE Purchase basar: reklam optimizasyonu bozulur, Okan'in
 * butcesi yanlis ogrenir, veri geri alinamaz.
 *
 * TASARIM: FAIL-CLOSED. Suphede test KOSMAZ. Sessiz atlama YOK — gurultulu hata verir,
 * cunku sessiz atlama tam da korumasi gereken riski gorunmez kilardi.
 *
 * IKI KATMAN:
 *   1) RED: gercek bir CAPI token'i / GA4 api_secret'i ortamda ya da .dev.vars'ta gorulurse
 *      test BASLAMAZ (bunlar olmadan hicbir olay gonderilemez — asil tehlike anahtarlardir).
 *   2) OVERRIDE: her kosuda piksel/mulk kimlikleri sahte test degerleriyle EZILIR, boylece
 *      1. katman bir sekilde asilsa bile istek gercek piksele DEGIL, gecersiz bir kimlige
 *      gider (Meta 400 doner, veri kirlenmez).
 *
 * Saf fonksiyon (I/O yok) — hem kabul.js kullanir hem birim testi (olcum.mjs T21) sinar.
 */

"use strict";

// Sahte kimlikler BILEREK gecersiz bicimde: Meta piksel ID'si tamamen rakamdir, GA4
// measurement ID'si "G-" + alfanumeriktir. Kazayla istek cikarsa hicbir GERCEK mulke
// denk gelmez, hedefte 400/404 olur.
const TEST_PIKSEL = "TEST-PIKSEL-KABUL";
const TEST_GA4_MULK = "G-TESTKABUL";

/** wrangler.toml'dan bir [vars] degerini cek ("AD = \"deger\""). Yoksa "". */
function tomlDegeri(toml, ad) {
  const m = new RegExp("^\\s*" + ad + "\\s*=\\s*\"([^\"]*)\"", "m").exec(String(toml || ""));
  return m ? m[1] : "";
}

/** .dev.vars / env dosyasindan anahtar oku; YORUM satirlari (#) ve bos deger sayilmaz. */
function devVarsDegeri(metin, ad) {
  const satirlar = String(metin || "").split(/\r?\n/);
  for (const ham of satirlar) {
    const s = ham.trim();
    if (!s || s.startsWith("#")) { continue; }
    const esit = s.indexOf("=");
    if (esit < 0) { continue; }
    if (s.slice(0, esit).trim() !== ad) { continue; }
    let d = s.slice(esit + 1).trim();
    if ((d.startsWith("\"") && d.endsWith("\"")) || (d.startsWith("'") && d.endsWith("'"))) {
      d = d.slice(1, -1);
    }
    if (d) { return d; }
  }
  return "";
}

// Bunlardan BIRI bile varsa gercek olay GONDERILEBILIR -> test kosmaz.
const TEHLIKELI_ANAHTARLAR = ["META_CAPI_TOKEN", "GA4_API_SECRET"];

/**
 * @param {{wranglerToml?: string, devVars?: string|null, ortam?: object}} girdi
 * @returns {{ok: boolean, sebepler: string[], degiskenler: object, gercekPiksel: string}}
 */
function olcumKapisi(girdi) {
  const g = girdi || {};
  const ortam = g.ortam || {};
  const sebepler = [];

  // 1) Gercek anahtar var mi? (ortam degiskeni ya da shop/.dev.vars)
  for (const ad of TEHLIKELI_ANAHTARLAR) {
    if (String(ortam[ad] || "").trim()) {
      sebepler.push("ortam degiskeni " + ad + " TANIMLI — yerel test gercek hedefe olay " +
        "gonderebilir. Testten once bu degiskeni kaldir.");
    }
    if (devVarsDegeri(g.devVars, ad)) {
      sebepler.push("shop/.dev.vars icinde " + ad + " TANIMLI — wrangler dev bunu worker'a " +
        "yukler ve kabul testi GERCEK hedefe sahte Purchase basar. Satiri yorumla (#) ya da sil.");
    }
  }

  // 2) Override degerleri: her kosuda gercek kimlikler EZILIR.
  const gercekPiksel = tomlDegeri(g.wranglerToml, "META_PIXEL_ID");
  const gercekMulk = tomlDegeri(g.wranglerToml, "GA4_MEASUREMENT_ID");
  const degiskenler = { META_PIXEL_ID: TEST_PIKSEL, GA4_MEASUREMENT_ID: TEST_GA4_MULK };

  // 3) Akil saglami: override GERCEK kimlige esitse kapi islevsizdir -> RED.
  if (gercekPiksel && degiskenler.META_PIXEL_ID === gercekPiksel) {
    sebepler.push("test piksel ID'si GERCEK piksel ID'sine esit — override islevsiz.");
  }
  if (gercekMulk && degiskenler.GA4_MEASUREMENT_ID === gercekMulk) {
    sebepler.push("test GA4 mulku GERCEK mulke esit — override islevsiz.");
  }

  return { ok: sebepler.length === 0, sebepler, degiskenler, gercekPiksel };
}

module.exports = { olcumKapisi, TEST_PIKSEL, TEST_GA4_MULK, tomlDegeri, devVarsDegeri };
