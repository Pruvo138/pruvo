#!/usr/bin/env node
/**
 * MUTASYON BATARYASI — `tools/reklam-url-test.js` CAPA EKSENI.
 *
 *   node tools/reklam-url-capa-mutasyon.js
 *
 * NEDEN VAR (olculdu 6 Eyl 2026, cip KraL-Tamirci-6Eyl):
 * `reklam-url-test.js` GA head blogunu KOMSU etikete bagli bir capayla kesiyordu
 * ("</script>\n<script async"). `fc76b775` (5 Eyl, LCP gec-yukleme) o komsuyu
 * kaldirinca capa COKTU ve `dilim()` MODUL DUZEYINDE firladi: surec 7 senaryodan
 * sonra oldu, ALTTAKI 6 RIZA (KVKK Consent Mode v2) senaryosu 5 Eyl'den 6 Eyl'e
 * kadar HIC KOSMADI. Adim CI'da kirmiziydi — ama kirmizinin ARKASINDAKI olcum
 * yoktu; "capa cokmesi arkasindaki capalari gizler" sinifi.
 *
 * NE OLCULUR: onarimin KENDISI (kanonik ayiklayici + tembel capa + civilenmis
 * senaryo sayaci) GERCEKTEN isiriyor mu. Her mutant CANLI degil AYNA (gecici
 * kopya) uzerinde uygulanir; canli agac hic degismez ve kosum sonunda sha256 ile
 * dogrulanir.
 *
 * HUKUM: her OLDURUCU mutant KIRMIZI (rc=1) yanmali VE beklenen jetonu basmali;
 * KONTROL mutanti YESIL (rc=0) kalmali. Aksi halde bu batarya hicbir sey olcmuyor.
 */

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

const KOK = path.dirname(__dirname);
const TEST = path.join(KOK, "tools", "reklam-url-test.js");
const INDEX = path.join(KOK, "index.html");
const YARDIMCILAR = ["ortak-index-esleme.js", "html-blok-ayikla.js"];

function sha(p) {
  return crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
}

/** Canli agacin BIREBIR kopyasini gecici dizine kurar; mutant ORADA uygulanir. */
function ayna() {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-capa-mut-"));
  fs.mkdirSync(path.join(d, "tools"));
  fs.copyFileSync(INDEX, path.join(d, "index.html"));
  fs.copyFileSync(TEST, path.join(d, "tools", "reklam-url-test.js"));
  YARDIMCILAR.forEach((y) =>
    fs.copyFileSync(path.join(KOK, "tools", y), path.join(d, "tools", y)));
  return d;
}

/** Aynada bir dosyada TAM BIR KEZ eslesen dizgeyi degistirir; eslesmezse capa bayat. */
function yamala(dizin, gorece, eski, yeni) {
  const p = path.join(dizin, gorece);
  const s = fs.readFileSync(p, "utf8");
  const parcalar = s.split(eski);
  if (parcalar.length !== 2) {
    throw new Error("CAPA BAYAT: " + gorece + " icinde dayanak TAM BIR KEZ eslesmedi " +
                    "(bulunan=" + (parcalar.length - 1) + "): " + JSON.stringify(eski.slice(0, 70)));
  }
  fs.writeFileSync(p, parcalar.join(yeni));
}

/** Aynada TUM eslesmeleri degistirir; adet BEKLENEN sayida degilse capa bayat. */
function yamalaTum(dizin, gorece, eski, yeni, beklenenAdet) {
  const p = path.join(dizin, gorece);
  const s = fs.readFileSync(p, "utf8");
  const parcalar = s.split(eski);
  if (parcalar.length - 1 !== beklenenAdet) {
    throw new Error("CAPA BAYAT: " + gorece + " icinde dayanak " + beklenenAdet +
                    " kez beklenirken " + (parcalar.length - 1) + " kez eslesti: " +
                    JSON.stringify(eski.slice(0, 70)));
  }
  fs.writeFileSync(p, parcalar.join(yeni));
}

function kos(dizin) {
  const r = spawnSync(process.execPath, [path.join(dizin, "tools", "reklam-url-test.js")],
                      { encoding: "utf8" });
  return { rc: r.status, cikti: (r.stdout || "") + (r.stderr || "") };
}

// ─── MUTANTLAR ───────────────────────────────────────────────────────────────
const MUTANTLAR = [
  {
    ad: "K0 KONTROL — mutasyonsuz ayna",
    beklenen: "YESIL",
    jeton: "SONUC: YESIL",
    uygula: () => {}
  },
  {
    ad: "M1 GA head KOMSU capasina geri donduruldu (fc76b775 oncesi kirilgan hal)",
    beklenen: "KIRMIZI",
    jeton: "CAPA COKTU [GA head]",
    // Kanonik ayiklayici SOKULUR, yerine COKMUS komsu-etiket capasi konur.
    uygula: (d) => yamala(d, "tools/reklam-url-test.js",
      'const GA_JS = blokCapa("GA head", "window.dataLayer = window.dataLayer");',
      'const GA_JS = capa("GA head", () => dilim(INDEX,\n' +
      '  "  window.dataLayer = window.dataLayer || [];",\n' +
      '  "</script>\\n<script async", "GA head"));')
  },
  {
    ad: "M2 GA head imzasi index.html'de bozuldu (blok GERCEKTEN yok)",
    beklenen: "KIRMIZI",
    jeton: "CAPA COKTU [GA head]",
    uygula: (d) => yamala(d, "index.html",
      "  window.dataLayer = window.dataLayer || [];",
      "  window.dataLayerXX = window.dataLayerXX || [];")
  },
  {
    ad: "M3 riza bandi imzasi index.html'de bozuldu (TEMBEL kol: olcum SURER)",
    beklenen: "KIRMIZI",
    // AYIRT EDICI EKSEN — M5 ile AYNI index.html mutasyonu, TEK fark tembellik:
    // burada senaryolar KOSAR, cokme ADIYLA raporlanir ve OZET basilir.
    jeton: "CAPA COKTU [riza bandi]",
    jetonlar: ["SONUC: KIRMIZI", "ok  1 ?gclid", "ok  6 korunan liste"],
    // 🔴 ALT DIZE TUZAGI: "pco-kabul" -> "pco-kabulXX" YETMEZ; yeni ad eskisini ALT
    // DIZE olarak icerir, imza yine eslesir ve mutant hic dogmaz (olculdu).
    uygula: (d) => yamalaTum(d, "index.html", "pco-kabul", "pcoXXkabul", 4)
  },
  {
    ad: "M4 bir RIZA senaryosu SESSIZCE silindi (sayac isiriyor mu)",
    beklenen: "KIRMIZI",
    jeton: "SENARYO SAYACI",
    uygula: (d) => yamala(d, "tools/reklam-url-test.js",
      'senaryo("12 RET diyene tekrar SORULMAZ (yanlis-pozitif ekseni)", () => {',
      'if (false) senaryo("12 RET diyene tekrar SORULMAZ (yanlis-pozitif ekseni)", () => {')
  },
  {
    ad: "M5 TEMBELLIK SOKULDU — M3 ile ayni bozulma, ama olcum OLUR (korumanin ta kendisi)",
    beklenen: "KIRMIZI",
    jeton: "CAPA COKTU [riza bandi]",
    // 🔴 BU MUTANT KORUMAYI TANIMLAR: tembellik sokulunce surec ozete VARAMAZ —
    // "SONUC:" satiri HIC basilmaz, yani senaryolarin HICBIRI olculmez. Onarim
    // oncesi 6 Eyl'de canlida gorulen hal budur (7 senaryo kostu, 6'si olculmedi).
    jetonYok: ["SONUC:", "ok  7 ILK YUKLEME"],
    uygula: (d) => {
      // Capalar TAM ESKI YERINDE (tanim aninda) cozulur = tembellik sokuldu.
      yamala(d, "tools/reklam-url-test.js",
        'const BANNER_JS = blokCapa("riza bandi", "pco-kabul");',
        'const BANNER_JS = blokCapa("riza bandi", "pco-kabul");\n' +
        "/* MUTANT: tembellik SOKULDU — capalar tanim aninda cozulur (eski hal). */\n" +
        "GA_JS(); BANNER_JS();");
      yamalaTum(d, "index.html", "pco-kabul", "pcoXXkabul", 4);
    }
  }
];

// ─── KOSUM ───────────────────────────────────────────────────────────────────
const oncekiTest = sha(TEST);
const oncekiIndex = sha(INDEX);

console.log("REKLAM URL — CAPA EKSENI MUTASYON BATARYASI");
console.log("-".repeat(70));

let dusen = 0;
MUTANTLAR.forEach((m) => {
  const d = ayna();
  let hukum;
  let ayrinti = "";
  try {
    m.uygula(d);
    const r = kos(d);
    const kirmizi = r.rc !== 0;
    const bekleniyorKirmizi = m.beklenen === "KIRMIZI";
    const gerekli = [m.jeton].concat(m.jetonlar || []);
    const eksik = gerekli.filter((j) => r.cikti.indexOf(j) === -1);
    const sizan = (m.jetonYok || []).filter((j) => r.cikti.indexOf(j) !== -1);
    if (kirmizi === bekleniyorKirmizi && eksik.length === 0 && sizan.length === 0) {
      hukum = bekleniyorKirmizi ? "OLDU" : "YESIL";
    } else {
      hukum = "KACTI";
      ayrinti = " rc=" + r.rc +
                (eksik.length ? " EKSIK_JETON=" + JSON.stringify(eksik) : "") +
                (sizan.length ? " OLMAMASI_GEREKEN_JETON=" + JSON.stringify(sizan) : "");
    }
  } catch (e) {
    hukum = "OLCULEMEDI";
    ayrinti = " " + e.message;
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
  if (hukum !== "OLDU" && hukum !== "YESIL") { dusen += 1; }
  const isaret = (hukum === "OLDU" || hukum === "YESIL") ? "[OK]  " : "[FAIL]";
  console.log(isaret + " " + m.ad + "\n         beklenen=" + m.beklenen +
              " · HUKUM=" + hukum + ayrinti);
});

console.log("-".repeat(70));
const temiz = sha(TEST) === oncekiTest && sha(INDEX) === oncekiIndex;
console.log("CANLI AGAC sha256 once==sonra: " + temiz +
            "  (mutantlar YALNIZ aynada kosar)");
if (!temiz) {
  console.error("SONUC: KIRMIZI ❌ — mutasyon CANLI dosyaya sizdi");
  process.exit(1);
}
if (dusen) {
  console.error("SONUC: KIRMIZI ❌ — " + dusen + " mutant kacti/olculemedi: " +
                "capa korumasi ISIRMIYOR");
  process.exit(1);
}
console.log("SONUC: YESIL ✅ — " + (MUTANTLAR.length - 1) +
            " oldurucu mutant KIRMIZI yandi + 1 KONTROL YESIL kaldi.");
