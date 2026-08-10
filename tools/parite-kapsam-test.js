#!/usr/bin/env node
"use strict";
/**
 * KAPSAM KAPISI — marka katlama sinifi parite korpuslarinda `marka=` EKSENINDE OLCULUYOR MU?
 *
 *   node tools/parite-kapsam-test.js
 *
 * NE OLCER (kapi, arama SEMANTIGI DEGIL):
 *   1. Sinif uye sayisi `markaKatla`dan TURETILIR ve BASILIR (elle liste YOK, sabit YOK).
 *   2. tools/parite-test.js korpusunda `marka=` ekseninde kac sinif uyesi VAR.
 *   3. tools/parite-ege.js  korpusunda `marka=` ekseninde kac sinif uyesi VAR.
 *   4. KONTROL degerleri (markaKatla(V) === V) korpusta BOZULMADAN duruyor mu
 *      (capalar: Astra H · Focus ST · Golf 4 · Land Rover, + asgari 10 deger).
 *   5. Kapsam KATALOG SIRASINDAN BAGIMSIZ mi: katalog dizisi yeniden siralaninca
 *      olculen `marka=` yuzeyi DEGISMEMELI (bu, kapatilan asil kusurdur).
 *   6. `hedef` (sorgu sayisi) argumani sinif cekirdegini KIRPMAMALI.
 *
 * ⚠️ CIKIS KODLARI — hicbir ariza yolu 0 uretmez, yonetici ilke 1 > 3 > 0:
 *   0  kapsam TAM
 *   1  EKSIK (sinif uyesi / kontrol degeri korpusta yok, ya da kapsam siraya bagli)
 *   3  OLCULEMEDI (referans kurulamadi · katalog yok · bot deposu yok -> ege ekseni)
 *
 * 🔴 EGE EKSENI BOT DEPOSUNA BAGLIDIR: tools/parite-ege.js korpus ureteci bot'un `nrm`
 * fonksiyonunu kullanir; ~/dev/pruvo-bot AYRI bir checkout'tur ve CI runner'inda YOKTUR.
 * O halde ege ekseni OLCULEMEDI'dir (3) — sahte YESIL degil. Site ekseni bot ISTEMEZ ve
 * her halukarda olculur; site ekseninde eksik varsa hukum 1'dir (1 > 3).
 */

const fs = require("fs");
const path = require("path");

const TOOLS = __dirname;
const KOK = path.dirname(TOOLS);
const URUNLER_YOLU = process.env.PARITE_URUNLER || path.join(KOK, "urunler.json");

const CIKIS_TAM = 0;
const CIKIS_EKSIK = 1;
const CIKIS_OLCULEMEDI = 3;

const SINIF = require("./parite-marka-sinifi.js");

// 🔴 SPEC ESIKLERI KAPININ KENDI DEFTERINDE DURUR — modulun sabitine BAGLANMAZ.
// Gerekce (olculdu): esik yalniz `SINIF.KONTROL_ASGARI`den okunsaydi, o sabiti 10'dan
// 1'e cekmek hem korpusu hem kapiyi ayni anda gevsetir ve kapi YESIL kalirdi
// ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]] sinifi: kapi kendi korlugunde).
// Bunlar KABUL SARTIDIR (spec 2b), sinif UYELIK defteri DEGILDIR — uyelik markaKatla'dan
// turer ve burada ASLA listelenmez.
const SPEC_KONTROL_ASGARI = 10;
const SPEC_CAPALAR = ["Astra H", "Focus ST", "Golf 4", "Land Rover"];

const eksikler = [];
const olculemedi = [];
let iddia = 0;

function iddiaEt(gecti, metin) {
  iddia++;
  console.log("  " + (gecti ? "✅" : "❌") + " " + metin);
  if (!gecti) eksikler.push(metin);
}

/** Korpustaki `marka=` ekseninde GECEN marka degerleri (site: {q,kat,marka}). */
function siteMarkaEkseni(sorgular) {
  const k = new Set();
  for (const s of sorgular) {
    if (s && s.marka && s.marka !== "Tümü") k.add(s.marka);
  }
  return k;
}

/** Korpustaki `marka=` ekseninde GECEN marka degerleri (ege: string | {q,marka}). */
function egeMarkaEkseni(sorgular, ogeCoz) {
  const k = new Set();
  for (const s of sorgular) {
    const o = ogeCoz(s);
    if (o.marka) k.add(o.marka);
  }
  return k;
}

function eksikListe(beklenen, bulunan) {
  return beklenen.filter((v) => !bulunan.has(v));
}

async function main() {
  console.log("═".repeat(78));
  console.log("PARITE KAPSAM KAPISI — marka katlama sinifi `marka=` ekseninde olculuyor mu?");
  console.log("═".repeat(78));

  // ── 0) KATALOG + SINIF (fail-closed) ─────────────────────────────────────────────
  let PRODUCTS;
  try {
    PRODUCTS = JSON.parse(fs.readFileSync(URUNLER_YOLU, "utf8"));
  } catch (e) {
    olculemedi.push("katalog OKUNAMADI (" + URUNLER_YOLU + "): " + (e && e.message));
    return bitir();
  }
  let S;
  try {
    S = SINIF.markaSinifi(PRODUCTS);
  } catch (e) {
    olculemedi.push("marka katlama sinifi TURETILEMEDI: " + (e && e.message));
    return bitir();
  }

  console.log("\nkatalog: %d urun | tekil marka degeri: %d", PRODUCTS.length, S.evren);
  console.log("SINIF_UYE (markaKatla(V) !== V, markaKatla'dan TURETILDI): %d", S.uyeler.length);
  console.log("KONTROL (markaKatla(V) === V): %d deger | korpus capasi: %d",
    S.kontroller.length, S.kontrolDegerleri.length);

  // "Sinif bos" bir kapsam KANITI DEGIL: hicbir sey olculmeden yesil yanardi.
  if (!S.uyeler.length) {
    olculemedi.push("sinif BOS (0 uye) — kapsam iddiasi kurulamaz");
    return bitir();
  }

  // ── 1) KONTROL CAPALARI BAYAT MI? ────────────────────────────────────────────────
  // Capa bir gun KATLANIR hale gelirse (yani sinifa gecerse) yanlis-pozitif nobeti
  // sessizce olur. Fail-closed: kapi bunu ADIYLA soyler.
  console.log("\n[1] KONTROL CAPALARI (markaKatla(V) === V olmali, katalogda BULUNMALI)");
  const evrenKume = new Set(S.uyeler.concat(S.kontroller));
  for (const capa of SPEC_CAPALAR) {
    const katlanan = S.uyeler.indexOf(capa) !== -1;
    iddiaEt(evrenKume.has(capa) && !katlanan,
      "capa " + JSON.stringify(capa) + ": katalogda=" + evrenKume.has(capa) +
      " katlaniyor=" + katlanan + " (katlaniyorsa CAPA BAYAT)");
  }
  // Modulun capa defteri SPEC capalarini KAPSAMALI: bosaltilirsa korpus onlari tasimaz
  // ve kontrol ayagi sessizce yok olurdu.
  const capaEksik = SPEC_CAPALAR.filter((v) => SINIF.KONTROL_CAPALARI.indexOf(v) === -1);
  iddiaEt(!capaEksik.length, "parite-marka-sinifi.KONTROL_CAPALARI spec capalarini tasiyor" +
    (capaEksik.length ? " -> EKSIK: " + JSON.stringify(capaEksik) : ""));
  iddiaEt(SINIF.KONTROL_ASGARI >= SPEC_KONTROL_ASGARI,
    "modul kontrol tabani >= " + SPEC_KONTROL_ASGARI + " (KONTROL_ASGARI=" +
    SINIF.KONTROL_ASGARI + ")");
  iddiaEt(S.kontrolDegerleri.length >= SPEC_KONTROL_ASGARI,
    "korpus kontrol degeri >= " + SPEC_KONTROL_ASGARI + " (bulunan: " +
    S.kontrolDegerleri.length + ")");

  // ── 2) SITE KORPUSU ──────────────────────────────────────────────────────────────
  console.log("\n[2] tools/parite-test.js korpusu — `marka=` ekseni");
  let siteKorpus;
  try {
    siteKorpus = require("./parite-test.js").sorgulariUret(0, PRODUCTS);
  } catch (e) {
    olculemedi.push("site korpusu URETILEMEDI: " + (e && e.message));
    return bitir();
  }
  const siteEksen = siteMarkaEkseni(siteKorpus);
  const siteEksikUye = eksikListe(S.uyeler, siteEksen);
  const siteBulunan = S.uyeler.length - siteEksikUye.length;
  console.log("  korpus: %d sorgu | `marka=` ekseninde %d ayri deger", siteKorpus.length,
    siteEksen.size);
  console.log("  KORPUS_SITE = %d/%d sinif uyesi", siteBulunan, S.uyeler.length);
  iddiaEt(!siteEksikUye.length, "site korpusunda EKSIK sinif uyesi yok" +
    (siteEksikUye.length ? " -> EKSIK: " + JSON.stringify(siteEksikUye.slice(0, 12)) : ""));
  const siteEksikKontrol = eksikListe(S.kontrolDegerleri, siteEksen);
  iddiaEt(!siteEksikKontrol.length, "site korpusunda KONTROL degerleri bozulmadan duruyor" +
    (siteEksikKontrol.length ? " -> EKSIK: " + JSON.stringify(siteEksikKontrol) : ""));
  // Serbest metin ekseni de spec sarti (hem `marka=` hem `q`).
  const siteSerbest = new Set(siteKorpus.filter((s) => s.marka === "Tümü").map((s) => s.q));
  const serbestEksik = eksikListe(S.uyeler, siteSerbest);
  iddiaEt(!serbestEksik.length, "site korpusunda sinif uyeleri SERBEST METIN `q` olarak da var" +
    (serbestEksik.length ? " -> EKSIK: " + JSON.stringify(serbestEksik.slice(0, 12)) : ""));

  // ── 3) KATALOG SIRASINDAN BAGIMSIZLIK ────────────────────────────────────────────
  // Kapatilan asil kusur buydu: kapsam `markalar.slice(0,150)` / `markalar[i % ...]`
  // ile SIRAYA bagliydi; bir urun partisi diziyi itince alarm kendiliginde yesile
  // donebiliyordu. Katalogu deterministik olarak TERSINE cevirip ayni yuzeyi olceriz.
  console.log("\n[3] Kapsam KATALOG SIRASINDAN bagimsiz mi? (katalog ters cevrildi)");
  const ters = PRODUCTS.slice().reverse();
  let tersEksen;
  try {
    tersEksen = siteMarkaEkseni(require("./parite-test.js").sorgulariUret(0, ters));
  } catch (e) {
    olculemedi.push("ters siralamali korpus URETILEMEDI: " + (e && e.message));
    return bitir();
  }
  const tersEksik = eksikListe(S.uyeler, tersEksen);
  console.log("  ters katalogda `marka=` ekseninde %d/%d sinif uyesi",
    S.uyeler.length - tersEksik.length, S.uyeler.length);
  iddiaEt(!tersEksik.length, "ters siralamada da TUM sinif uyeleri olculuyor" +
    (tersEksik.length ? " -> DUSEN: " + JSON.stringify(tersEksik.slice(0, 12)) : ""));

  // ── 4) `hedef` KIRPMASI CEKIRDEGE DOKUNMUYOR ─────────────────────────────────────
  console.log("\n[4] `hedef` (sorgu sayisi) argumani sinif cekirdegini KIRPIYOR mu?");
  let kirpik;
  try {
    kirpik = siteMarkaEkseni(require("./parite-test.js").sorgulariUret(10, PRODUCTS));
  } catch (e) {
    olculemedi.push("kirpik korpus URETILEMEDI: " + (e && e.message));
    return bitir();
  }
  const kirpikEksik = eksikListe(S.uyeler, kirpik);
  iddiaEt(!kirpikEksik.length, "hedef=10 verildiginde bile sinif uyeleri KIRPILMADI" +
    (kirpikEksik.length ? " -> DUSEN: " + kirpikEksik.length : ""));

  // ── 5) EGE KORPUSU (bot deposuna bagli -> yoksa OLCULEMEDI) ──────────────────────
  console.log("\n[5] tools/parite-ege.js korpusu — `marka=` ekseni");
  const EGE_MOD = require("./parite-ege.js");
  let egeBulunan = null;
  if (!fs.existsSync(EGE_MOD.BOT)) {
    olculemedi.push("bot kaynagi YOK (" + EGE_MOD.BOT + ") -> ege korpusu OLCULEMEDI");
    console.log("  ⚪ OLCULEMEDI: " + olculemedi[olculemedi.length - 1]);
  } else {
    try {
      const EGE = await EGE_MOD.egeKodu();
      const egeKorpus = EGE_MOD.sorgulariUret(EGE, PRODUCTS, 0);
      const egeEksen = egeMarkaEkseni(egeKorpus, EGE_MOD.ogeCoz);
      const egeEksikUye = eksikListe(S.uyeler, egeEksen);
      egeBulunan = S.uyeler.length - egeEksikUye.length;
      console.log("  korpus: %d sorgu | `marka=` ekseninde %d ayri deger",
        egeKorpus.length, egeEksen.size);
      console.log("  KORPUS_EGE = %d/%d sinif uyesi", egeBulunan, S.uyeler.length);
      iddiaEt(!egeEksikUye.length, "ege korpusunda EKSIK sinif uyesi yok" +
        (egeEksikUye.length ? " -> EKSIK: " + JSON.stringify(egeEksikUye.slice(0, 12)) : ""));
      const egeEksikKontrol = eksikListe(S.kontrolDegerleri, egeEksen);
      iddiaEt(!egeEksikKontrol.length, "ege korpusunda KONTROL degerleri bozulmadan duruyor" +
        (egeEksikKontrol.length ? " -> EKSIK: " + JSON.stringify(egeEksikKontrol) : ""));
      // mod=ege BOS q'yu 400 ile reddeder: marka ekseninin q'su DOLU olmali.
      const bosQ = egeKorpus.map(EGE_MOD.ogeCoz)
        .filter((o) => o.marka && !String(o.q || "").trim()).length;
      iddiaEt(bosQ === 0, "ege `marka=` sorgularinin hepsinde `q` DOLU (mod=ege bos q'yu " +
        "400 ile reddeder) — bos: " + bosQ);
    } catch (e) {
      olculemedi.push("ege korpusu URETILEMEDI: " + (e && e.message));
      console.log("  ⚪ OLCULEMEDI: " + olculemedi[olculemedi.length - 1]);
    }
  }

  // ── OZET (makine okunabilir) ─────────────────────────────────────────────────────
  console.log("\n" + "-".repeat(78));
  console.log("SINIF_UYE=%d", S.uyeler.length);
  console.log("KORPUS_SITE=%d", siteBulunan);
  console.log("KORPUS_EGE=%s", egeBulunan === null ? "OLCULEMEDI" : egeBulunan);
  console.log("IDDIA=%d", iddia);
  return bitir();
}

function bitir() {
  console.log("-".repeat(78));
  if (eksikler.length) {
    console.log("SONUC: KAPSAM EKSIK ❌ (%d iddia dustu) — cikis 1", eksikler.length);
    for (const m of eksikler) console.log("   • " + m);
    if (olculemedi.length) {
      console.log("   ⚠️ ayrica OLCUM ARIZASI var, ama EKSIK KAZANIR (1 > 3 > 0):");
      for (const m of olculemedi) console.log("      ⚪ " + m);
    }
    return process.exit(CIKIS_EKSIK);
  }
  if (olculemedi.length) {
    console.log("SONUC: ÖLÇÜLEMEDİ ⚪ — kapsam BELGELENMEDI (cikis 3, KIRMIZI DEGIL)");
    for (const m of olculemedi) console.log("   • " + m);
    return process.exit(CIKIS_OLCULEMEDI);
  }
  console.log("SONUC: KAPSAM TAM ✅ (%d iddia) — cikis 0", iddia);
  return process.exit(CIKIS_TAM);
}

module.exports = { CIKIS_TAM, CIKIS_EKSIK, CIKIS_OLCULEMEDI };

if (require.main === module) {
  main().catch((e) => {
    // Beklenmeyen istisna 0 URETEMEZ: ariza kendi biriminde raporlanir.
    console.log("\n⚪ BEKLENMEYEN ISTISNA: " + (e && e.stack || e));
    olculemedi.push("beklenmeyen istisna: " + (e && e.message));
    bitir();
  });
}
