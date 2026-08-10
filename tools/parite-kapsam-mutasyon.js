#!/usr/bin/env node
"use strict";
/**
 * KAPSAM KAPISININ MUTASYON NOBETI — tools/parite-kapsam-test.js GERCEKTEN kirmizi yakiyor mu?
 *
 *   node tools/parite-kapsam-mutasyon.js          # tum mutantlar
 *   node tools/parite-kapsam-mutasyon.js 3        # yalniz 3. mutant (teshis)
 *
 * NEDEN VAR: "kapi yazildi, yesil yaniyor" bir KANIT DEGILDIR — anlatilan batarya da
 * kanit degildir, surucu REPODA DURMALIDIR ([[mutasyon-kaniti-yeniden-uretilebilir]]).
 * Kabul cikis kodunun sifir olmasi degil, HER OLDURUCU MUTANTIN BEKLENEN ISARETLE
 * (rc=1 EKSIK, rc=3 DEGIL) dusmesi ve HER KONTROL MUTANTININ YESIL KALMASIDIR
 * ([[beyan-edilmis-survivor]]: ayirt edici olmayan mutant iddia degildir).
 *
 * 🔴 GERCEK DEPOYA MUTASYON UYGULANMAZ: her mutant icin AYRI gecici dizin kurulur,
 * dosyalar oraya KOPYALANIR, mutasyon KOPYAYA yazilir. Ayri dizin ayni zamanda
 * bytecode/onbellek tuzagini da kapatir ([[mutasyon-bytecode-onbellegi]]).
 *
 * 🔴 KATALOG + index.html GERCEK AGACTAN gelir (PARITE_URUNLER / PARITE_INDEX_KOK):
 * gecici dizinde ikisi de yoktur; verilmezse TUM mutantlar OLCULEMEDI (3) ile duser ve
 * "yakalandi" sanilirdi — halbuki hicbir sey olculmemis olurdu.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const TOOLS = __dirname;
const KOK = path.dirname(TOOLS);
const KAPI = "parite-kapsam-test.js";
// Kopyalanacak yerel bagimliliklar — biri unutulursa mutantlar MODULE_NOT_FOUND ile
// coker ve "yakalandi" gorunurdu ([[kardes-fikstur-yeni-kanca-adiminda-kirilir]]).
const DOSYALAR = [KAPI, "parite-marka-sinifi.js", "parite-test.js", "parite-ege.js",
  "parite-ortak.js", "index-arama-referansi.js", "ege-marka-referansi.js"];

const EKSIK = 1;        // kapinin "kapsam eksik" isareti
const TAM = 0;

/**
 * Her mutant: `dosya` icinde `ara` metnini `yaz` ile BIR KEZ degistirir.
 * `ara` bulunamazsa mutant ANLAMSIZDIR -> nobet KIRMIZI yanar (kod degisti, nobet bayat).
 * `kontrol: true` -> davranisi DEGISTIRMEYEN mutant, kapi YESIL kalmali.
 */
const MUTANTLAR = [
  {
    ad: "M1 SITE korpusundan bir SINIF UYESI dusuruldu (cekirdek kirpildi)",
    dosya: "parite-test.js",
    ara: '  const cekirdek = sinifsiz ? [] : SINIF.cekirdekSorgular(PRODUCTS, "site").sorgular;',
    yaz: '  const cekirdek = sinifsiz ? [] : SINIF.cekirdekSorgular(PRODUCTS, "site")' +
      ".sorgular.slice(3);",
  },
  {
    ad: "M2 EGE korpusundan bir SINIF UYESI dusuruldu",
    dosya: "parite-ege.js",
    ara: '  const cekirdek = sinifsiz ? [] : SINIF.cekirdekSorgular(PRODUCTS, "ege").sorgular;',
    yaz: '  const cekirdek = sinifsiz ? [] : SINIF.cekirdekSorgular(PRODUCTS, "ege")' +
      ".sorgular.slice(1);",
  },
  {
    ad: "M3 GERILEME: sinif cekirdegi komple kalkti (eski orneklemeye donuldu)",
    dosya: "parite-test.js",
    ara: '  const cekirdek = sinifsiz ? [] : SINIF.cekirdekSorgular(PRODUCTS, "site").sorgular;',
    yaz: "  const cekirdek = [];",
  },
  {
    ad: "M4 KIRPMA CEKIRDEGE DOKUNUR OLDU (hedef verilince sinif uyeleri dusuyor)",
    dosya: "parite-test.js",
    ara: "  const kalan = hedef ? Math.max(0, hedef - cekirdek.length) : sorgular.length;\n" +
      "  return cekirdek.concat(sorgular.slice(0, kalan));",
    yaz: "  const hepsi = cekirdek.concat(sorgular);\n" +
      "  return hedef ? hepsi.slice(0, hedef) : hepsi;",
  },
  {
    ad: "M5 KONTROL DEGERLERI korpustan dusuruldu (yanlis-pozitif nobeti kalkti)",
    dosya: "parite-marka-sinifi.js",
    ara: "  const degerler = S.uyeler.concat(S.kontrolDegerleri);",
    yaz: "  const degerler = S.uyeler.slice();",
  },
  {
    ad: "M6 SERBEST METIN ekseni dusuruldu (yalniz `marka=` kaldi)",
    dosya: "parite-marka-sinifi.js",
    ara: '      cikti.push({ q: v, kat: "Tümü", marka: "Tümü" });',
    yaz: "      /* serbest metin ekseni dusuruldu */",
  },
  {
    ad: "M7 EGE `marka=` sorgusunun q'su BOSALDI (uc 400 doner, eksen olculmez)",
    dosya: "parite-marka-sinifi.js",
    ara: "      cikti.push({ q: S.katla(v), marka: v });",
    yaz: '      cikti.push({ q: "", marka: v });',
  },
  {
    ad: "M8 KONTROL TABANI 10'dan 1'e cekildi (kapi kendi esigini gevsetiyor)",
    dosya: "parite-marka-sinifi.js",
    ara: "const KONTROL_ASGARI = 10;",
    yaz: "const KONTROL_ASGARI = 1;",
  },
  {
    ad: "M9 KONTROL CAPALARI defteri BOSALTILDI (Astra H/Focus ST/Golf 4/Land Rover)",
    dosya: "parite-marka-sinifi.js",
    ara: 'const KONTROL_CAPALARI = ["Astra H", "Focus ST", "Golf 4", "Land Rover"];',
    yaz: "const KONTROL_CAPALARI = [];",
  },
  {
    ad: "M10 SINIF UYELIGI TERSINE DONDU (markaKatla yargisi yok sayildi)",
    dosya: "parite-marka-sinifi.js",
    ara: "  for (const v of evren) { (R.markaKatla(v) !== v ? uyeler : kontroller).push(v); }",
    yaz: "  for (const v of evren) { kontroller.push(v); }",
    // Sinif BOSALIR -> kapi 'kapsam iddiasi kurulamaz' der: rc=3 (OLCULEMEDI), 0 DEGIL.
    beklenen: 3,
  },
  {
    ad: "M11 SIRALAMA kalkti (kapsam yine KATALOG SIRASINA baglandi)",
    dosya: "parite-marka-sinifi.js",
    ara: "  uyeler.sort();\n  kontroller.sort();",
    yaz: "  uyeler.splice(6);\n  kontroller.sort();",
  },

  // ══ KONTROL MUTANTLARI — YESIL KALMALI ════════════════════════════════════════════
  // 🔴 SART: kontrol yoksa DAIMA-KIRMIZI bir kapi butun oldurucuLERI "yakalar" ve
  // ayirt edilemez ([[beyan-edilmis-survivor]] / [[fikstur-degeri-mutasyon-koru]]).
  {
    ad: "K1 KONTROL: parite-test.js karistirma carpani degisti (SIRA farkli, KUME ayni)",
    kontrol: true,
    dosya: "parite-test.js",
    ara: "    const j = (i * 2654435761) % (i + 1);",
    yaz: "    const j = (i * 2246822519) % (i + 1);",
  },
  {
    ad: "K2 KONTROL: davranis degistirmeyen yeniden adlandirma (sinif modulu)",
    kontrol: true,
    dosya: "parite-marka-sinifi.js",
    ara: "  const cikti = [];",
    yaz: "  const cikti = [];   // ad degismedi, yalniz yorum eklendi",
  },
  {
    ad: "K3 KONTROL: kimsenin okumadigi ILGISIZ alan eklendi",
    kontrol: true,
    dosya: "parite-marka-sinifi.js",
    ara: "    evren: evren.length,",
    yaz: "    evren: evren.length,\n    olculmeyenIlgisizAlan: 0,",
  },
  {
    ad: "K4 KONTROL: ege korpusunun serbest-metin adimindaki ornek sayisi degisti",
    kontrol: true,
    dosya: "parite-ege.js",
    ara: "  for (const w of kelimeler.slice(0, 300)) ekle(w);",
    yaz: "  for (const w of kelimeler.slice(0, 280)) ekle(w);",
  },
];

function kopyaKur() {
  const dizin = fs.mkdtempSync(path.join(os.tmpdir(), "parite-kapsam-mut-"));
  for (const d of DOSYALAR) fs.copyFileSync(path.join(TOOLS, d), path.join(dizin, d));
  return dizin;
}

function uygula(dizin, m) {
  const yol = path.join(dizin, m.dosya);
  const src = fs.readFileSync(yol, "utf8");
  const i = src.indexOf(m.ara);
  if (i === -1) {
    return "CAPA TUTMADI: " + m.dosya + " icinde aranan metin YOK (nobet BAYAT). " +
      JSON.stringify(m.ara.slice(0, 70));
  }
  if (src.indexOf(m.ara, i + 1) !== -1) {
    return "CAPA COKLU: " + m.dosya + " icinde aranan metin BIRDEN COK gecti";
  }
  fs.writeFileSync(yol, src.slice(0, i) + m.yaz + src.slice(i + m.ara.length));
  return null;
}

function kapiyiKos(dizin) {
  const p = spawnSync(process.execPath, [path.join(dizin, KAPI)], {
    encoding: "utf8",
    cwd: os.tmpdir(),
    timeout: 300000,
    env: Object.assign({}, process.env, {
      PARITE_URUNLER: path.join(KOK, "urunler.json"),
      PARITE_INDEX_KOK: KOK,
    }),
  });
  return { rc: p.status === null ? 124 : p.status, cikti: (p.stdout || "") + (p.stderr || "") };
}

function main() {
  const yalniz = parseInt(process.argv[2] || "", 10);
  console.log("═".repeat(78));
  console.log("KAPSAM KAPISI MUTASYON NOBETI — %d mutant + 1 pozitif kontrol (ag YOK)",
    MUTANTLAR.length);
  console.log("═".repeat(78));

  const arizalar = [];

  // ── POZITIF KONTROL: mutasyonsuz kopya YESIL olmali ──────────────────────────────
  // Olmazsa butun "yakalandi" hukumleri anlamsizdir (her sey kirmizi yanan bir kapi).
  {
    const dizin = kopyaKur();
    const r = kapiyiKos(dizin);
    const ok = r.rc === TAM;
    console.log("\n▶ POZITIF KONTROL (mutasyonsuz kopya)  -> rc=%d %s", r.rc, ok ? "✅" : "❌");
    if (!ok) {
      arizalar.push("POZITIF KONTROL rc=" + r.rc + " (0 bekleniyordu) — nobet OLCEMEZ");
      console.log(r.cikti.split("\n").slice(-14).join("\n"));
    }
    fs.rmSync(dizin, { recursive: true, force: true });
  }

  let oldu = 0, denenen = 0, kontrolGecen = 0, kontrolToplam = 0;
  for (let i = 0; i < MUTANTLAR.length; i++) {
    const m = MUTANTLAR[i];
    if (Number.isFinite(yalniz) && yalniz !== i + 1) continue;
    const dizin = kopyaKur();
    const hata = uygula(dizin, m);
    if (hata) {
      arizalar.push(m.ad + " -> " + hata);
      console.log("\n▶ %s\n   ❌ %s", m.ad, hata);
      fs.rmSync(dizin, { recursive: true, force: true });
      continue;
    }
    const r = kapiyiKos(dizin);
    fs.rmSync(dizin, { recursive: true, force: true });

    if (m.kontrol) {
      kontrolToplam++;
      const ok = r.rc === TAM;
      if (ok) kontrolGecen++;
      else arizalar.push(m.ad + " -> rc=" + r.rc + " (KONTROL mutanti YESIL kalmaliydi)");
      console.log("\n▶ %s\n   rc=%d %s", m.ad, r.rc, ok ? "✅ YESIL kaldi" : "❌ ASIRI HASSAS");
      continue;
    }

    denenen++;
    const bek = Number.isFinite(m.beklenen) ? m.beklenen : EKSIK;
    // 🔴 ISARET SARTI: "sifir-disi" yetmez. Cokme/olculemedi de sifir-disidir ve
    // kapiyi yakalamis GIBI gosterirdi ([[mutasyon-kaniti-yeniden-uretilebilir]]).
    const ok = r.rc === bek;
    if (ok) oldu++;
    else arizalar.push(m.ad + " -> rc=" + r.rc + " (beklenen " + bek + ")");
    console.log("\n▶ %s\n   rc=%d (beklenen %d) %s", m.ad, r.rc, bek,
      ok ? "✅ KIRMIZI yakti" : "❌ KACTI");
    if (!ok) console.log(r.cikti.split("\n").slice(-10).join("\n"));
  }

  console.log("\n" + "═".repeat(78));
  console.log("OLDURUCU: %d/%d isaret sartiyla oldu | KONTROL: %d/%d yesil kaldi",
    oldu, denenen, kontrolGecen, kontrolToplam);
  console.log("MUTANT_KIRMIZI=%d/%d", oldu, denenen);
  if (arizalar.length) {
    console.log("SONUC: NOBET KIRMIZI ❌");
    for (const a of arizalar) console.log("   • " + a);
    return process.exit(1);
  }
  console.log("SONUC: NOBET YESIL ✅ — kapi olculdu, anlatilmadi");
  return process.exit(0);
}

if (require.main === module) main();
