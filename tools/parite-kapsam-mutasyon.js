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
 *
 * ══ 21 Eyl 2026 — KOR NOBET ONARIMI (olculdu) ══════════════════════════════════════
 * ONCESI: kopyalanacak dosyalar ELLE tutulan bir listedeydi. 6 Eyl'de
 * `parite-marka-sinifi.js` yeni bir bagimlilik kazandi (`marka-kanon-uret.py` ->
 * `d1-sync.py` -> `git_ortami`/`arama`/`veri_kok`/... derin zincir); liste bayatladi ve
 * POZITIF KONTROL DAHIL her kosum rc=3 (OLCULEMEDI) verdi. Nobet yine de "KIRMIZI"
 * yazdigi icin 15 gun boyunca "bilinen kirmizi" sanildi — oysa HICBIR SEY olculmuyordu
 * ([[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]]).
 *
 * ONARIM IKI BACAKLI (tek dosyaya ad eklemek AYNI kusuru bir sonraki bagimlilikta
 * yeniden uretirdi):
 *   (1) LISTE KALKTI, KOPYA TURETILIYOR: `tools/` agacinin TAMAMI kopyalanir
 *       (`__pycache__`/`.pyc` haric — bytecode tuzagi acik kalmasin). Yeni bir
 *       bagimlilik — JS, PY, veri, ne olursa — kendiliginden kopyaya girer.
 *   (2) BAYATLIK ARTIK OLCULUYOR: POZITIF KONTROL rc!=0 ise nobet KIRMIZI DEMEZ;
 *       `SONUC: NOBET KOR ⚪ OLCULEMEDI` der, SEBEBI basar, cikis 3 verir ve mutant
 *       hukmu KURMAZ. Ustune `KORLUK ON-TESTI` kolu, kapinin gercekten kostugu bir
 *       bagimliligi kopyadan SILIP nobetin bunu KOR diye gordugunu olcer; capalar
 *       kaynaktan TURETILIR (JS require kapanisi + `path.join(__dirname, "*.py")`),
 *       elle yazilmaz.
 * 🔴 Bu dosya CI'da KOSMAZ (tools/ci-kapsam-test.py muafiyeti, R_YAVAS) — cikis 3
 * hicbir yayin kapisini durdurmaz; mimar kolu olarak elle kosulur.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const TOOLS = __dirname;
const KOK = path.dirname(TOOLS);
const KAPI = "parite-kapsam-test.js";

const EKSIK = 1;        // kapinin "kapsam eksik" isareti
const TAM = 0;
const OLCULEMEDI = 3;   // kapinin "iddia kurulamadi" isareti (KIRMIZI DEGIL)

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

/**
 * 🔴 TURETILMIS KOPYA — ELLE LISTE YOKTUR.
 * `tools/` agacinin TAMAMI kopyalanir; boylece kopyalanan bir modul YENI bir bagimlilik
 * (js/py/veri) kazandiginda kopya kendiliginden onu da tasir. Elle tutulan liste tam da
 * burada sessizce bayatlamisti ([[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]]).
 * `__pycache__`/`*.pyc` DISARIDA BIRAKILIR: kopya dizininin ikinci isi bytecode onbellegi
 * tuzagini kapatmaktir ([[mutasyon-bytecode-onbellegi]]).
 * OLCULDU (21 Eyl, uretim agaci): 25 MB / 723 giris -> ~0,27 sn/kopya.
 */
// Sahte kokte YENIDEN URETILMEYEN girisler: `.git` baglanirsa kopyadaki git komutlari
// GERCEK depoda kosar; `tools` zaten kopyanin kendisidir; `.claude` worktree/oturum
// defteridir. Geri kalan TUM kok girisleri TURETILEREK baglanir (ls ile okunur) —
// kok duzeyinde yeni bir bagimlilik cikarsa kendiliginden gelir.
const KOK_HARIC = new Set(["tools", ".git", ".claude"]);

function kopyaKur() {
  const dizin = fs.mkdtempSync(path.join(os.tmpdir(), "parite-kapsam-mut-"));
  // 🔴 KOPYA, DEPO KOKU SEKLINDE kurulur: <tmp>/kok/tools/... Cunku kopyalanan python
  // govdesi (marka-kanon-uret.py -> d1-sync.py -> veri_kok.cozumle) KOK'u `__file__`den
  // turetir: duz `<tmp>/tools-icerigi` duzeninde KOK=<tmp> olur ve `index.html` bulunamaz.
  // Bu, elle listenin arkasinda duran IKINCI kor noktaydi (21 Eyl, olculdu): liste
  // tamamlansa bile kapi hala rc=3 verirdi.
  const kok = path.join(dizin, "kok");
  fs.mkdirSync(kok);
  fs.cpSync(TOOLS, path.join(kok, "tools"), {
    recursive: true,
    filter: (kaynak) =>
      !/(^|[/\\])(__pycache__|node_modules|\.git)([/\\]|$)/.test(kaynak) &&
      !kaynak.endsWith(".pyc"),
  });
  // Kok girisleri SEMBOLIK baglanir (urunler.json TEK BASINA 32 MB — 16 mutant x kopya
  // yarim GB'a cikardi). Kapi SALT OKURDUR; yine de gercek katalogun bozulmadigi
  // `katalogDamgasi()` ile kosum basinda/sonunda OLCULUR ([[urunler-guard-katmani]]).
  for (const g of fs.readdirSync(KOK)) {
    if (KOK_HARIC.has(g) || g.startsWith(".olcum-")) continue;
    try { fs.symlinkSync(path.join(KOK, g), path.join(kok, g)); } catch (e) { /* yok say */ }
  }
  return path.join(kok, "tools");
}

/**
 * Kopyayi kaldirir. `dizin` TOOLS kopyasidir; silinmesi gereken mkdtemp KOKUDUR
 * (<tmp>/parite-kapsam-mut-X/kok/tools -> <tmp>/parite-kapsam-mut-X).
 * 🔴 Kok girisleri SEMBOLIK BAGDIR; `rmSync` bagi siler, HEDEFI izlemez.
 */
function temizle(dizin) {
  fs.rmSync(path.dirname(path.dirname(dizin)), { recursive: true, force: true });
}

/** Gercek katalogun kosum boyunca DEGISMEDIGINI olcen ucuz damga (boyut + mtime ns). */
function katalogDamgasi() {
  try {
    const s = fs.statSync(path.join(KOK, "urunler.json"), { bigint: true });
    return s.size + ":" + s.mtimeNs;
  } catch (e) { return "YOK"; }
}

/**
 * Kapinin JS REQUIRE KAPANISI — `KAPI`den baslayip `require("./x")` kenarlarini yurur.
 * Capa turetmek icindir; kopyalama artik buna BAGLI DEGIL (tum agac kopyalaniyor).
 * @returns {Set<string>} tools/ altindaki dosya adlari
 */
function jsKapanisi() {
  const gorulen = new Set();
  const kuyruk = [KAPI];
  while (kuyruk.length) {
    const d = kuyruk.pop();
    if (gorulen.has(d)) continue;
    gorulen.add(d);
    let src;
    try { src = fs.readFileSync(path.join(TOOLS, d), "utf8"); } catch (e) { continue; }
    const re = /require\(\s*"\.\/([^"]+)"\s*\)/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      const ad = /\.[a-z]+$/.test(m[1]) ? m[1] : m[1] + ".js";
      kuyruk.push(ad);
    }
  }
  return gorulen;
}

/**
 * KORLUK CAPALARI — kopyadan silindiginde kapinin "OLCULEMEDI" demesi BEKLENEN dosyalar.
 * KAYNAKTAN TURETILIR: JS kapanisinin kendisi + o modullerin `path.join(__dirname, "*.py")`
 * ile kosturdugu yardimcilar. Elle yazilmadigi icin bir yeniden adlandirma capayi
 * sessizce bosa dusuremez ([[capa-komsuya-nisanlanirsa-yabanci-degisiklik-kopartir]]).
 */
function korlukCapalari() {
  const kapanis = jsKapanisi();
  const capalar = new Set();
  for (const d of kapanis) {
    if (d !== KAPI) capalar.add(d);          // silinen JS modul -> require patlar
    let src;
    try { src = fs.readFileSync(path.join(TOOLS, d), "utf8"); } catch (e) { continue; }
    const re = /path\.join\(\s*__dirname\s*,\s*"([^"]+\.(?:py|sh|mjs))"\s*\)/g;
    let m;
    while ((m = re.exec(src)) !== null) capalar.add(m[1]);
  }
  return { kapanis, capalar: Array.from(capalar).sort() };
}

/** Cikti icinden korlugun SEBEBINI ayikla (ad ADIYLA raporlansin, "kirmizi" demek yetmez). */
function korlukSebebi(cikti) {
  const satirlar = cikti.split("\n").filter((s) =>
    /TURETILEMEDI|MODULE_NOT_FOUND|Cannot find module|No such file|can't open file|ModuleNotFoundError|OLCULEMEDI/.test(s));
  return satirlar.length ? satirlar.slice(0, 6) : cikti.split("\n").slice(-8);
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
  const damgaBas = katalogDamgasi();   // sahte kok SEMBOLIK baglar -> gercek katalog SABIT kalmali

  // ── POZITIF KONTROL: mutasyonsuz kopya YESIL olmali ──────────────────────────────
  // 🔴 BASARISIZSA NOBET "KIRMIZI" DEGIL "KOR"DUR. Eskiden burasi ariza listesine bir
  // satir atip mutantlari yine de kosuyordu: hepsi rc=3 ile duser, "1/11 oldu" yazar ve
  // cikis 1 ile "bilinen kirmizi" sanilirdi. Olculmeyen ile olculup dusen AYNI isarete
  // binmisti — ayrimi bu blok kurar ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
  {
    const dizin = kopyaKur();
    const r = kapiyiKos(dizin);
    const ok = r.rc === TAM;
    console.log("\n▶ POZITIF KONTROL (mutasyonsuz kopya)  -> rc=%d %s", r.rc, ok ? "✅" : "❌");
    if (!ok) {
      console.log("\n" + "═".repeat(78));
      console.log("SONUC: NOBET KOR ⚪ — OLCULEMEDI (cikis %d, KIRMIZI DEGIL)", OLCULEMEDI);
      console.log("MUTANT_KIRMIZI=OLCULEMEDI");
      console.log("KOR_SEBEP: mutasyonsuz kopya bile kapiyi kosturamiyor (rc=%d). Mutant " +
        "hukmu KURULMADI — asagidaki satirlar 'yakalandi' DEGIL, 'hic kosmadi' demektir:",
        r.rc);
      for (const s of korlukSebebi(r.cikti)) console.log("   • " + s.trim());
      console.log("   ↳ KOPYA DIZINI: tools/ agacinin tamami kopyalanir; bir bagimlilik " +
        "hala disarida kaliyorsa ADI yukarida gecer.");
      temizle(dizin);
      return process.exit(OLCULEMEDI);
    }
    temizle(dizin);
  }

  // ── KORLUK ON-TESTI: nobet KOR oldugunu FARK EDIYOR mu? ──────────────────────────
  // Kopyadan bir bagimlilik BILEREK silinir; kapi OLCULEMEDI (3) demeli. rc=1 gelirse
  // eksik bagimlilik "kapsam eksik" isaretiyle KARISIYOR demektir — bu ariza sinifi
  // korlugu geri getirirdi, o yuzden KIRMIZI sayilir. rc=0 gelen capa kapinin kostugu
  // yolda DEGILDIR (bilgi satiri, ariza degil).
  {
    const { kapanis, capalar } = korlukCapalari();
    console.log("\n" + "─".repeat(78));
    console.log("KORLUK ON-TESTI — capalar KAYNAKTAN turetildi (JS kapanisi=%d dosya, " +
      "capa=%d)", kapanis.size, capalar.length);
    console.log("   TURETILEN_CAPALAR: " + capalar.join(", "));
    let goren = 0;
    for (const c of capalar) {
      const dizin = kopyaKur();
      const yol = path.join(dizin, c);
      if (!fs.existsSync(yol)) {
        arizalar.push("KORLUK ON-TESTI capasi KOPYADA YOK: " + c + " (kopya turetimi bozuk)");
        console.log("   ❌ " + c.padEnd(28) + "kopyada YOK — kopya turetimi bozuk");
        temizle(dizin);
        continue;
      }
      fs.rmSync(yol, { force: true });
      const r = kapiyiKos(dizin);
      temizle(dizin);
      if (r.rc === OLCULEMEDI) {
        goren++;
        console.log("   ✅ " + c.padEnd(28) + "silindi -> rc=3 KOR gorundu");
      } else if (r.rc === TAM) {
        console.log("   ·  " + c.padEnd(28) + "silindi -> rc=0 (kapinin kostugu yolda DEGIL)");
      } else {
        arizalar.push("KORLUK AYRIMI BOZUK: " + c + " silinince rc=" + r.rc +
          " (eksik bagimlilik 'kapsam eksik' isaretiyle karisiyor)");
        console.log("   ❌ " + c.padEnd(28) + "silindi -> rc=" + r.rc + " (EKSIK isaretiyle KARISIYOR)");
      }
    }
    if (!goren) {
      arizalar.push("KORLUK ON-TESTI: hicbir capa silindiginde kapi OLCULEMEDI demedi — " +
        "korluk dedektoru OLCULEMEDI");
      console.log("   ❌ hicbir capa korluk uretmedi — dedektor OLCULEMEDI");
    }
    console.log("KORLUK_GORULDU=%d/%d", goren, capalar.length);
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
      temizle(dizin);
      continue;
    }
    const r = kapiyiKos(dizin);
    temizle(dizin);

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
    else {
      // rc=3 beklenmedik yerde OLCULEMEDI demektir: mutant OLMEDI, kapi KOSAMADI.
      const niye = r.rc === OLCULEMEDI ? " [OLCULEMEDI — oldurulmedi, kosulamadi]"
        : r.rc === TAM ? " [HAYATTA KALDI — nobetsiz mutant]" : "";
      arizalar.push(m.ad + " -> rc=" + r.rc + " (beklenen " + bek + ")" + niye);
    }
    console.log("\n▶ %s\n   rc=%d (beklenen %d) %s", m.ad, r.rc, bek,
      ok ? "✅ KIRMIZI yakti"
        : r.rc === OLCULEMEDI ? "⚪ OLCULEMEDI (oldurulmedi)" : "❌ KACTI");
    if (!ok) console.log(r.cikti.split("\n").slice(-10).join("\n"));
  }

  console.log("\n" + "═".repeat(78));
  console.log("OLDURUCU: %d/%d isaret sartiyla oldu | KONTROL: %d/%d yesil kaldi",
    oldu, denenen, kontrolGecen, kontrolToplam);
  console.log("MUTANT_KIRMIZI=%d/%d", oldu, denenen);
  if (katalogDamgasi() !== damgaBas) {
    arizalar.push("KATALOG DAMGASI DEGISTI: gercek urunler.json kosum sirasinda " +
      "yazildi (sahte kok sembolik bagi salt-okur olmaliydi)");
    console.log("KATALOG_DOKUNULMADI=HAYIR ❌");
  } else {
    console.log("KATALOG_DOKUNULMADI=EVET");
  }
  if (arizalar.length) {
    console.log("SONUC: NOBET KIRMIZI ❌");
    for (const a of arizalar) console.log("   • " + a);
    return process.exit(1);
  }
  console.log("SONUC: NOBET YESIL ✅ — kapi olculdu, anlatilmadi");
  return process.exit(0);
}

if (require.main === module) main();
