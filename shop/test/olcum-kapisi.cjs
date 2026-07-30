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

// ---------------------------------------------------------------------------
// CIPLAK KOSUM KOLU — `node shop/test/olcum-kapisi.cjs`
// ---------------------------------------------------------------------------
// 🔴 30 TEM — NEDEN EKLENDI (olculdu): bu dosya SAF MODULDU (`module.exports` var,
// `require.main` kolu YOK). `node shop/test/olcum-kapisi.cjs` rc=0 veriyordu ve SIFIR
// IDDIA kosuyordu — shop/.dev.vars'a SAHTE bir META_CAPI_TOKEN konsa bile rc=0. Tek
// tuketicisi shop/test/kabul.js, o da wrangler dev istedigi icin hicbir yerde kosmuyor.
// Yani "yerel test GERCEK Meta pikseline sahte Purchase basmasin" fail-closed kapisi
// FIILEN yoktu; ci-kapsam izin listesindeki gerekcesi de (R_AYRI, "o projenin CI
// hattinda kosulur") OLCULEREK YANLIS bulundu — boyle bir hat yok.
//
// IKI BOLUM (ikisi de agsiz, dosya YAZMAZ, wrangler/docker/secret ISTEMEZ):
//   A) OZ-NOBET — kapinin KARAR MANTIGI sentetik girdilerle olculur. Bu, kapi
//      etkisizlestirildiginde (or. TEHLIKELI_ANAHTARLAR bosaltilinca, bir dosya
//      TARANAN_DOSYALAR'dan dusurulunce, override gercek kimlige esitlenince) KIRMIZI
//      yanar. shop/test/olcum.mjs T21 ayni mantigi ayri bir surecten olcer; burada
//      SURECTEN BAGIMSIZ ikinci bir olcum kalir (iki adim birden olmeden koruma dusmez).
//   B) GERCEK DURUM — bu makinedeki gercek process.env + shop/{.dev.vars,.env,.env.local}
//      + shop/wrangler.toml okunur. Gercek bir CAPI token'i / GA4 api_secret'i gorurse
//      KIRMIZI (fail-closed): kabul testi kosmadan once yayin durur. CI fresh checkout'ta
//      bu dosyalar YOKTUR -> B bolumunun anlamli iddiasi wrangler.toml AKIL SAGLAMIDIR
//      (override degerleri GERCEK piksel/mulk kimliklerinden farkli olmak ZORUNDA);
//      o dosya IZLENIYOR, yani CI'da da GERCEKTEN olculur.
if (require.main === module) {
  const fs = require("fs");
  const path = require("path");
  const SHOP = path.join(__dirname, "..");

  let gecti = 0;
  const hatalar = [];
  function iddia(ad, ok, ayrinti) {
    if (ok) { gecti += 1; console.log("  ok   " + ad); return; }
    hatalar.push(ad + (ayrinti ? "  — " + ayrinti : ""));
    console.log("  FAIL " + ad + (ayrinti ? "  — " + ayrinti : ""));
  }

  const TOML = 'META_PIXEL_ID = "111111111"\nGA4_MEASUREMENT_ID = "G-GERCEK"\n';

  console.log("── A) OZ-NOBET: kapinin karar mantigi (sentetik girdi) ──");
  // A1 sozlesme: kapi hangi anahtarlari/dosyalari izliyor (etkisizlestirme kanaryasi)
  iddia("A1 TEHLIKELI_ANAHTARLAR bos DEGIL", TEHLIKELI_ANAHTARLAR.length > 0);
  for (const ad of ["META_CAPI_TOKEN", "GA4_API_SECRET"]) {
    iddia("A1 izlenen anahtar: " + ad, TEHLIKELI_ANAHTARLAR.indexOf(ad) !== -1);
  }
  for (const d of [".dev.vars", ".env", ".env.local"]) {
    iddia("A1 taranan dosya: " + d, TARANAN_DOSYALAR.indexOf(d) !== -1);
  }

  // A2 temiz girdi -> GECER (kapi "hep kirmizi" degil)
  const temiz = olcumKapisi({ wranglerToml: TOML, dosyalar: {}, ortam: {} });
  iddia("A2 temiz girdi ok=true", temiz.ok === true, temiz.sebepler.join(" | "));
  iddia("A2 override piksel gercek kimlik DEGIL",
        temiz.degiskenler.META_PIXEL_ID === TEST_PIKSEL &&
        temiz.degiskenler.META_PIXEL_ID !== "111111111");
  iddia("A2 override GA4 mulku gercek mulk DEGIL",
        temiz.degiskenler.GA4_MEASUREMENT_ID === TEST_GA4_MULK &&
        temiz.degiskenler.GA4_MEASUREMENT_ID !== "G-GERCEK");

  // A3 her anahtar x her kaynak -> REDDEDER (2 x 4 = 8 iddia)
  for (const ad of TEHLIKELI_ANAHTARLAR) {
    const o = olcumKapisi({ wranglerToml: TOML, dosyalar: {},
                            ortam: { [ad]: "sahte-jeton-degeri" } });
    iddia("A3 ortam degiskeni " + ad + " -> RED", o.ok === false);
    for (const dosyaAdi of TARANAN_DOSYALAR) {
      const r = olcumKapisi({ wranglerToml: TOML, ortam: {},
                              dosyalar: { [dosyaAdi]: ad + "=sahte-jeton-degeri\n" } });
      iddia("A3 shop/" + dosyaAdi + " icinde " + ad + " -> RED", r.ok === false);
    }
  }

  // A4 yanlis-pozitif kenarlari: yorumlu / bos deger olay GONDEREMEZ -> GECER
  const yorumlu = olcumKapisi({ wranglerToml: TOML, ortam: {},
                                dosyalar: { ".dev.vars": "# META_CAPI_TOKEN=x\n" } });
  iddia("A4 YORUMLU satir RED DEGIL (sahte-kirmizi yok)", yorumlu.ok === true,
        yorumlu.sebepler.join(" | "));
  const bos = olcumKapisi({ wranglerToml: TOML, ortam: {},
                            dosyalar: { ".dev.vars": "META_CAPI_TOKEN=\n" } });
  iddia("A4 BOS deger RED DEGIL", bos.ok === true, bos.sebepler.join(" | "));
  const baskaAd = olcumKapisi({ wranglerToml: TOML, ortam: {},
                                dosyalar: { ".dev.vars": "META_CAPI_TOKEN_YEDEK=x\n" } });
  iddia("A4 BENZER ADLI baska anahtar RED DEGIL", baskaAd.ok === true,
        baskaAd.sebepler.join(" | "));

  // A5 akil saglami: override GERCEK kimlige esitse kapi islevsizdir -> RED
  const cakisan = olcumKapisi({
    wranglerToml: 'META_PIXEL_ID = "' + TEST_PIKSEL + '"\n', dosyalar: {}, ortam: {} });
  iddia("A5 override == gercek piksel -> RED", cakisan.ok === false);
  const cakisanMulk = olcumKapisi({
    wranglerToml: 'GA4_MEASUREMENT_ID = "' + TEST_GA4_MULK + '"\n', dosyalar: {}, ortam: {} });
  iddia("A5 override == gercek GA4 mulku -> RED", cakisanMulk.ok === false);

  // A6 eski cagri bicimi (devVars) hala .dev.vars anlamina geliyor (geriye donuk uyum)
  const eskiBicim = olcumKapisi({ wranglerToml: TOML, ortam: {},
                                  devVars: "META_CAPI_TOKEN=x\n" });
  iddia("A6 eski `devVars` cagri bicimi -> RED", eskiBicim.ok === false);

  console.log("\n── B) GERCEK DURUM: bu makinedeki env + shop/ dosyalari + wrangler.toml ──");
  function oku(p) { try { return fs.readFileSync(p, "utf8"); } catch (e) { return null; } }
  const gercekDosyalar = {};
  const gorulen = [];
  for (const dosyaAdi of TARANAN_DOSYALAR) {
    const icerik = oku(path.join(SHOP, dosyaAdi));
    gercekDosyalar[dosyaAdi] = icerik;
    if (icerik !== null) { gorulen.push(dosyaAdi); }
  }
  console.log("  taranan dosyalar : " + TARANAN_DOSYALAR.join(", ") +
              "   (bulunan: " + (gorulen.join(", ") || "yok") + ")");
  const gercekToml = oku(path.join(SHOP, "wrangler.toml"));
  iddia("B1 shop/wrangler.toml okunabildi (kapinin akil saglami olculebilsin)",
        gercekToml !== null);
  const canli = olcumKapisi({ wranglerToml: gercekToml || "", dosyalar: gercekDosyalar,
                              ortam: process.env });
  // Sebep metinleri ANAHTAR ADINI icerir, DEGERINI ICERMEZ -> loga sir basilmaz.
  iddia("B2 gercek CAPI token'i / GA4 api_secret'i GORUNMUYOR", canli.ok === true,
        canli.sebepler.join(" | "));
  iddia("B3 wrangler.toml'daki GERCEK piksel ID'si override ile CAKISMIYOR",
        !canli.gercekPiksel || canli.gercekPiksel !== canli.degiskenler.META_PIXEL_ID,
        "gercek=" + (canli.gercekPiksel || "-"));

  console.log("\n" + "=".repeat(66));
  if (hatalar.length) {
    console.log("SONUC: KIRMIZI ❌  — " + gecti + " gecti, " + hatalar.length + " kirmizi");
    for (const h of hatalar) { console.log("  - " + h); }
    process.exit(1);
  }
  console.log("SONUC: YESIL ✅  — " + gecti + " iddia gecti");
}
