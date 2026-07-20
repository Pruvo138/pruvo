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
 *   1) RED: gercek bir CAPI token'i / GA4 api_secret'i ASAGIDA SAYILAN kaynaklardan birinde
 *      gorulurse test BASLAMAZ (bunlar olmadan hicbir olay gonderilemez — asil tehlike
 *      anahtarlardir).
 *   2) OVERRIDE: her kosuda piksel/mulk kimlikleri sahte test degerleriyle EZILIR, boylece
 *      1. katman bir sekilde asilsa bile istek gercek piksele DEGIL, gecersiz bir kimlige
 *      gider (Meta 400 doner, veri kirlenmez).
 *
 * ✅ 1. KATMANIN TARADIGI KAYNAKLAR (tam liste — fazlasini IDDIA ETME):
 *      - process.env (kabul.js'i kosturan kabuk)
 *      - shop/.dev.vars
 *      - shop/.env
 *      - shop/.env.local
 *   `.env`/`.env.local` NEDEN DAHIL: wrangler 4.112'de `getCloudflareLoadDevVarsFromDotEnv`
 *   varsayilani TRUE — `.dev.vars` YOKSA `.env`/`.env.local` SECRET olarak worker'a yuklenir
 *   ("Using secrets defined in .env"). Ustelik kok `.gitignore` `.env*` yok saydigi icin sirri
 *   koymanin "dogal gorunen" yeri tam orasidir. Kapi wrangler'in ONCELIK sirasini TAKLIT ETMEZ:
 *   dosyalardan HANGISINDE gorurse gorsun REDDEDER (fail-closed; precedence tahmini yapmayiz).
 *
 * 🚫 TARANMAYAN (bilerek — bu kapi bunlari COZMEZ):
 *      - `wrangler secret put` ile UZAK worker'a basilmis secret'lar (yerel --local kosuda
 *        yuklenmez; canli deploy zaten Okan kapisinda).
 *      - shop/ DISINDAKI .env dosyalari (wrangler dev cwd=shop ile kosar).
 *      - wrangler'in ILERIDE ekleyebilecegi yeni bir degisken kaynagi — surum yukseltmesinde
 *        bu liste GOZDEN GECIRILMELI.
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

// wrangler dev'in worker'a degisken/secret yukleyebilecegi shop/ ALTINDAKI dosyalar.
// SIRA ONEMLI DEGIL: precedence taklit edilmez, hangisinde gorursek reddederiz (fail-closed).
const TARANAN_DOSYALAR = [".dev.vars", ".env", ".env.local"];

/**
 * @param {{wranglerToml?: string, dosyalar?: object, devVars?: string|null, ortam?: object}} girdi
 *   dosyalar: { ".dev.vars": icerik|null, ".env": icerik|null, ".env.local": icerik|null }
 *   devVars : eski cagri bicimi — ".dev.vars" ile ayni anlama gelir (geriye donuk uyum).
 * @returns {{ok: boolean, sebepler: string[], degiskenler: object, gercekPiksel: string,
 *            taranan: string[]}}
 */
function olcumKapisi(girdi) {
  const g = girdi || {};
  const ortam = g.ortam || {};
  const sebepler = [];

  // Dosya haritasi: yeni bicim (dosyalar) + eski bicim (devVars) birlestirilir.
  const dosyalar = Object.assign({}, g.dosyalar || {});
  if (g.devVars != null && dosyalar[".dev.vars"] == null) { dosyalar[".dev.vars"] = g.devVars; }

  // 1) Gercek anahtar var mi? (ortam degiskeni + shop/ altindaki TUM degisken dosyalari)
  for (const ad of TEHLIKELI_ANAHTARLAR) {
    if (String(ortam[ad] || "").trim()) {
      sebepler.push("ortam degiskeni " + ad + " TANIMLI — yerel test gercek hedefe olay " +
        "gonderebilir. Testten once bu degiskeni kaldir.");
    }
    for (const dosyaAdi of TARANAN_DOSYALAR) {
      if (devVarsDegeri(dosyalar[dosyaAdi], ad)) {
        sebepler.push("shop/" + dosyaAdi + " icinde " + ad + " TANIMLI — wrangler dev bunu " +
          "worker'a yukler (.env/.env.local dahil: 'Using secrets defined in .env') ve kabul " +
          "testi GERCEK hedefe sahte Purchase basar. Satiri yorumla (#) ya da sil.");
      }
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

  return { ok: sebepler.length === 0, sebepler, degiskenler, gercekPiksel,
           taranan: TARANAN_DOSYALAR.slice() };
}

module.exports = { olcumKapisi, TEST_PIKSEL, TEST_GA4_MULK, TARANAN_DOSYALAR,
                   tomlDegeri, devVarsDegeri };
