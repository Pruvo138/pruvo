#!/usr/bin/env node
/* KALIBRASYON SENKRON TESTI — canli jenerator/hacim.js vs olcuye gore
   uretec v2 kalibre referanslari (konektor + braket + disli) + yeni sari
   aileler 1. dalga (adaptor + kutu + kavanoz, 2026-07-17).

   Uc katman:
   1) DONDURULMUS STL REFERANSI (her yerde kosar, openscad gerekmez):
      kalibrasyon-referans.json'daki gercek OpenSCAD STL hacimlerine karsi
      canli hacim.js kapali-formu, sapma <= %3. Ayrica urunler/<id>.json
      tabanHacimMm3 == fn(varsayilan) (%0.1).
   3) DONDURULMUS KALIBRASYON KAYNAGI (her yerde kosar, DIS KAYNAK ISTEMEZ):
      kaynak-referans.json — kapsamdaki ailelerin deterministik sema
      izgarasindaki hacimleri, KALIBRASYON KAYNAGINDAN uretilmis (hacim.js'ten
      DEGIL). Canli hacim.js bunlardan %0,01'den fazla saparsa KIRMIZI.
      KAPSAM DAR ve BEYANLI: yalniz `motor=pruvo` olan ve bugun kaynakla
      birebir ortusen aileler girer; kalan her aile fiksturdeki
      `disi_birakilan` tablosunda GEREKCE + OLCULEN SAPMA ile durur ve
      ikisinde de olmayan bir aile OLCULEMEDI (rc 2) yakar.
   2) DOGRULAMA KAYNAGI SENKRONU (dizin varsa): kardes ev
      dogrulama/test/aileler/*.js v2 kalibre fonksiyonlari ile canli
      fonksiyonlar deterministik sema gridinde birebir (<= %0.5)
      karsilastirilir — el kopyasi surüklenirse burasi kirmizi yanar.

   🔴 NEDEN 3. KATMAN VAR (olculdu 3 Agu 2026, bu depoda):
   `yay` ailesine konan +%5 TAHSILAT mutanti (hacim x1,05 -> musteriden fazla
   para) kardes ev VARKEN 26 kontrolu kirmizi yakiyordu; kardes ev YOKKEN
   (yani CI fresh checkout'unda) TAM YESIL geciyordu — cunku `yay` 1. katmanin
   dondurulmus STL referanslarinda YOK, yalniz 2. katmandaydi ve 2. katman dizin
   yoksa SESSIZCE atlaniyor. Ayni mutant deploy.yml'in `build` + `serit-b`
   islerindeki 134 kosulabilir adimin HICBIRINDE de kirmizi yakmiyordu.
   3. katman o hukmu depoya DONDURUR: dis kaynak olmadan da olculur.
   Fikstur ureteci: jenerator/test/kaynak-referans-uret.js (ELLE kosulur).

   Kirmizi kaniti (senkron oncesi kodda kosum):
     git show <eski>:jenerator/hacim.js > /tmp/eski-hacim.js
     PRUVO_HACIM_YOL=/tmp/eski-hacim.js node jenerator/test/kalibrasyon-senkron.js

   Mutasyon turu (kapinin KENDI ayirt ediciligi; canli agaca YAZMAZ):
     node jenerator/test/kalibrasyon-senkron.js --mutasyon
*/
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const vm = require("vm");

const TEST_DIR = __dirname;
const SINIR_YUZDE = 3.0;
const SENKRON_YUZDE = 0.5;
const TABAN_TOLERANS = 0.001;
// 3. katman toleransi. YANLIS-POZITIF RISKI OLCULDU (3 Agu 2026), tahmin edilmedi:
// fikstur node v25.8.1 ile uretildi, CI node 20 kosuyor. Motor farkinin ust siniri
// TAMAMEN FARKLI bir motorda (JavaScriptCore, macOS sistem jsc) olculdu: 12 ailenin
// 300 setinde EN KOTU sapma %1,85e-14 — bu toleransin 5,4e11 KATI altinda. Yani
// surum/motor gurultusu bu kapiyi kirmizi yakamaz. Ust yonde ise tolerans, olculen
// +%5 tahsilat mutantinin 1/500'u -> mutant KESIN yakalanir.
const KAYNAK_YUZDE = 0.01;

if (process.argv.indexOf("--mutasyon") >= 0) {
  mutasyonTuru();
} else {
  process.exit(kapi());
}

// =========================================================================
function kapi() {
  const hacimYol = process.env.PRUVO_HACIM_YOL ||
    path.join(TEST_DIR, "..", "hacim.js");
  const HACIM = require(path.resolve(hacimYol));
  console.log("hacim.js: " + hacimYol);

  let kirmizi = 0;
  let iddia = 0;

  function kontrol(ok, satir) {
    iddia++;
    console.log("  [" + (ok ? "OK " : "SAP") + "] " + satir);
    if (!ok) kirmizi++;
  }

  // ---------- 1) dondurulmus STL referansi ----------
  const REF = JSON.parse(fs.readFileSync(
    path.join(TEST_DIR, "kalibrasyon-referans.json"), "utf8"));
  console.log("\n== 1) dondurulmus STL referanslari (sinir <=%" +
    SINIR_YUZDE + ") ==");
  for (const aile of Object.keys(REF.aileler)) {
    const veri = REF.aileler[aile];
    const fn = HACIM[veri.fonksiyon];
    if (typeof fn !== "function") {
      kontrol(false, aile + ": hacim.js'te '" + veri.fonksiyon + "' yok");
      continue;
    }
    let enKotu = 0;
    veri.setler.forEach(function (s, i) {
      const js = fn(s.parametreler);
      const sapma = Math.abs(js - s.referansMm3) / s.referansMm3 * 100;
      if (sapma > enKotu) enKotu = sapma;
      if (sapma > SINIR_YUZDE) {
        kontrol(false, aile + " set" + i + " js=" + js.toFixed(1) +
          " referans=" + s.referansMm3.toFixed(1) +
          " sapma=%" + sapma.toFixed(2) + "  (" +
          JSON.stringify(s.parametreler) + ")");
      }
    });
    kontrol(enKotu <= SINIR_YUZDE, aile + ": " + veri.setler.length +
      " set, en kotu sapma %" + enKotu.toFixed(2));

    // tabanHacimMm3 tutarliligi
    const sema = JSON.parse(fs.readFileSync(path.join(
      TEST_DIR, "..", "urunler", veri.urunId + ".json"), "utf8"));
    const varsayilan = {};
    sema.parametreler.forEach(function (p) { varsayilan[p.ad] = p.varsayilan; });
    const taban = fn(varsayilan);
    const fark = Math.abs(taban - sema.tabanHacimMm3) / sema.tabanHacimMm3;
    kontrol(fark <= TABAN_TOLERANS, aile + ": tabanHacimMm3=" +
      sema.tabanHacimMm3.toFixed(1) + " fn(varsayilan)=" + taban.toFixed(1));
  }

  // ---------- 3) dondurulmus KALIBRASYON KAYNAGI referansi ----------
  // FAIL-CLOSED: fikstur yoksa/bozuksa ya da bir aile eksikse OLCULEMEDI (rc 2).
  // "Dosya yok -> atla" yazimi tam da bu kapinin KAPATTIGI delik olurdu.
  console.log("\n== 3) dondurulmus kalibrasyon kaynagi (sinir <=%" +
    KAYNAK_YUZDE + ") ==");
  const kaynakYol = path.join(TEST_DIR, "kaynak-referans.json");
  if (!fs.existsSync(kaynakYol)) {
    console.log("OLCULEMEDI: " + kaynakYol + " YOK — bu bir YESIL DEGILDIR. " +
      "Uret: node jenerator/test/kaynak-referans-uret.js --yaz");
    return 2;
  }
  let KAYNAK;
  try {
    KAYNAK = JSON.parse(fs.readFileSync(kaynakYol, "utf8"));
  } catch (e) {
    console.log("OLCULEMEDI: kaynak-referans.json ayristirilamadi: " + e.message);
    return 2;
  }
  const kaynakAileler = Object.keys(KAYNAK.aileler || {}).sort();
  const disi = KAYNAK.disi_birakilan || {};
  // KAPSAM NOBETI: esleme/ altindaki her aile YA kapsamda YA DA gerekcesi +
  // OLCULEN sapmasi yazili "disi_birakilan" listesinde olmali. Ikisinde de
  // olmayan aile SESSIZCE olcumsuz kalirdi -> OLCULEMEDI (rc 2).
  const eslemeAileler = fs.readdirSync(path.join(TEST_DIR, "esleme"))
    .filter(function (f) { return f.endsWith(".json"); })
    .map(function (f) { return f.slice(0, -5); }).sort();
  const beyansiz = eslemeAileler.filter(function (a) {
    return kaynakAileler.indexOf(a) < 0 && !disi[a];
  });
  const gerekcesiz = Object.keys(disi).filter(function (a) {
    return !disi[a].sebep ||
      typeof disi[a].olculen_en_kotu_sapma_yuzde !== "number";
  });
  if (beyansiz.length || gerekcesiz.length || !kaynakAileler.length) {
    console.log("OLCULEMEDI: beyansiz aile(ler): " +
      (beyansiz.join(", ") || "-") + " · gerekcesiz disi birakma: " +
      (gerekcesiz.join(", ") || "-") +
      (kaynakAileler.length ? "" : " · KAPSAM BOS") +
      " — fikstur BAYAT. Uret: node jenerator/test/kaynak-referans-uret.js --yaz");
    return 2;
  }
  kontrol(true, "kapsam: esleme " + eslemeAileler.length + " aile = " +
    kaynakAileler.length + " kapsamda + " + Object.keys(disi).length +
    " gerekceli disi, beyansiz 0");
  Object.keys(disi).sort().forEach(function (a) {
    console.log("  [DISI] " + a + " (%" +
      disi[a].olculen_en_kotu_sapma_yuzde + ", " +
      disi[a].tolerans_asan_set + ") " + disi[a].sebep);
  });
  let kaynakSet = 0;
  for (const aile of kaynakAileler) {
    const veri = KAYNAK.aileler[aile];
    const fn = HACIM[veri.fonksiyon];
    if (typeof fn !== "function") {
      kontrol(false, aile + ": hacim.js'te '" + veri.fonksiyon + "' YOK");
      continue;
    }
    let enKotu = 0;
    let gecersiz = 0;
    veri.setler.forEach(function (s, i) {
      const js = fn(s.p);
      if (!isFinite(js) || js <= 0) {
        gecersiz++;
        kontrol(false, aile + " set" + i + ": hacim GECERSIZ (" + js + ") — " +
          JSON.stringify(s.p));
        return;
      }
      const sapma = Math.abs(js - s.hacimMm3) / s.hacimMm3 * 100;
      if (sapma > enKotu) enKotu = sapma;
      if (sapma > KAYNAK_YUZDE) {
        kontrol(false, aile + " set" + i + " canli=" + js.toFixed(3) +
          " kaynak=" + s.hacimMm3.toFixed(3) + " sapma=%" + sapma.toFixed(4) +
          "  (" + JSON.stringify(s.p) + ")");
      }
    });
    kaynakSet += veri.setler.length;
    kontrol(gecersiz === 0 && enKotu <= KAYNAK_YUZDE, aile + ": " +
      veri.setler.length + " set, en kotu sapma %" + enKotu.toFixed(4));
    const tabanFark = Math.abs(fn(tabanSeti(veri)) - veri.taban_hacim_mm3) /
      veri.taban_hacim_mm3 * 100;
    kontrol(tabanFark <= KAYNAK_YUZDE, aile + ": taban hacmi kaynakla %" +
      tabanFark.toFixed(4));
  }
  console.log("  3. katman: " + kaynakAileler.length + " aile / " +
    kaynakSet + " set (fikstur " + KAYNAK.uretildi + ")");

  function tabanSeti(veri) {
    const sema = JSON.parse(fs.readFileSync(path.join(
      TEST_DIR, "..", "urunler", veri.urunId + ".json"), "utf8"));
    const varsayilan = {};
    sema.parametreler.forEach(function (p) { varsayilan[p.ad] = p.varsayilan; });
    return varsayilan;
  }

  // ---------- 2) dogrulama kaynagi senkronu ----------
  const dogrulamaDir = process.env.PRUVO_DOGRULAMA_DIR ||
    path.join(process.env.HOME || "", "dev", "pruvo-jenerator", "dogrulama");
  console.log("\n== 2) dogrulama kaynagi senkronu (" + dogrulamaDir + ") ==");
  if (!fs.existsSync(dogrulamaDir)) {
    console.log("  [ATLA] dogrulama dizini yok — katman 2 kosulamadi " +
      "(mimar makinesinde kosun). 🔴 Bu bir YESIL DEGILDIR; ailelerin hacim " +
      "hukmunu CI'da 3. katman verir.");
  } else {
    // deterministik LCG — tekrar uretilebilir sema-grid setleri
    let tohum = 424242;
    function rasgele() {
      tohum = (tohum * 1103515245 + 12345) % 2147483648;
      return tohum / 2147483648;
    }
    function setUret(sema) {
      const s = {};
      sema.parametreler.forEach(function (p) {
        if (p.tip === "sayi") {
          const adim = p.adim || 1;
          const n = Math.round((p.max - p.min) / adim);
          s[p.ad] = Math.round((p.min + Math.floor(rasgele() * (n + 1)) *
            adim) * 1e6) / 1e6;
        } else if (p.tip === "secim") {
          const secenekler = p.secenekler.map(function (x) {
            return typeof x === "object" ? x.deger : x;
          });
          s[p.ad] = secenekler[Math.floor(rasgele() * secenekler.length)];
        } else {
          s[p.ad] = p.varsayilan || "";
        }
      });
      return s;
    }
    // jeton/kase/cetvel: metin-bagimli hacim senkronu (kaynak repo 0e766f9,
    // 2026-07-23) — aile dosyalari bayt-ozdes tutulur; kayma = sessiz fiyat hatasi.
    // yay (3 Agu 2026): kalibrasyon kaynagi 16-gen bant + kose bindirme modelini
    // tasirken bu depodaki kopya eski (240 ornek + faz kaymali) surumde KALMISTI;
    // yay bu listede olmadigi icin ayrisma HICBIR kapiyi yakmadi ve uretimde
    // ucgen kolunda %3.80'e varan EKSIK hacim (eksik tahsilat) uretti. Listeye
    // eklendi: aile dosyasi kaynaktan tekrar ayrisirsa burasi kirmizi yanar.
    ["konektor", "braket", "adaptor", "kutu", "kavanoz",
     "jeton", "kase", "cetvel", "toka", "cerceve", "yay"].forEach(function (aile) {
      const kaynakDosya = path.join(dogrulamaDir, "test", "aileler",
        aile + ".js");
      if (!fs.existsSync(kaynakDosya)) {
        kontrol(false, aile + ": dogrulama kaynak dosyasi yok: " + kaynakDosya);
        return;
      }
      const sandbox = { Math: Math };
      vm.runInNewContext(fs.readFileSync(kaynakDosya, "utf8") +
        "\n;__fn = " + aile + ";", sandbox);
      const refFn = sandbox.__fn;
      const esleme = JSON.parse(fs.readFileSync(path.join(
        TEST_DIR, "esleme", aile + ".json"), "utf8"));
      const sema = JSON.parse(fs.readFileSync(path.join(
        TEST_DIR, "..", "urunler", esleme.urunId + ".json"), "utf8"));
      let enKotu = 0;
      for (let i = 0; i < 25; i++) {
        const s = setUret(sema);
        const canli = HACIM[aile](s);
        const ref = refFn(s);
        const sapma = Math.abs(canli - ref) / ref * 100;
        if (sapma > enKotu) enKotu = sapma;
        if (sapma > SENKRON_YUZDE) {
          kontrol(false, aile + " set" + i + " canli=" + canli.toFixed(1) +
            " dogrulama=" + ref.toFixed(1) + " sapma=%" + sapma.toFixed(3) +
            " (" + JSON.stringify(s) + ")");
        }
      }
      kontrol(enKotu <= SENKRON_YUZDE, aile +
        ": 25 sette dogrulama kaynagi ile en kotu fark %" + enKotu.toFixed(3));
      // dogrulama urun semasindaki taban hacimle de karsilastir
      const dogUrun = path.join(dogrulamaDir, "urunler", esleme.urunId + ".json");
      if (fs.existsSync(dogUrun)) {
        const dSema = JSON.parse(fs.readFileSync(dogUrun, "utf8"));
        const fark = Math.abs(dSema.tabanHacimMm3 - sema.tabanHacimMm3) /
          dSema.tabanHacimMm3;
        kontrol(fark <= TABAN_TOLERANS, aile + ": tabanHacimMm3 canli=" +
          sema.tabanHacimMm3.toFixed(1) + " dogrulama=" +
          dSema.tabanHacimMm3.toFixed(1));
      }
    });
  }

  console.log("IDDIA: " + iddia + " SAP: " + kirmizi);
  console.log(kirmizi ? "\nKIRMIZI: " + kirmizi + " kontrol" : "\nYESIL");
  return kirmizi ? 1 : 0;
}

// =========================================================================
// MUTASYON TURU — kapinin AYIRT EDICILIGI. Mutant KOPYAYA uygulanir; canli
// hacim.js'in sha256'si bas/son AYNI olmali (yoksa tur GECERSIZ sayilir).
// Kabul olcutu CIKIS KODU DEGIL: her kosumda OLCULEN IDDIA SAYISI temelle
// AYNI olmali (cokme kirmiziyla karismasin) + isaret sarti (oldurucu KIRMIZI,
// kontrol YESIL) saglanmali.
function mutasyonTuru() {
  const crypto = require("crypto");
  const { spawnSync } = require("child_process");
  const canliYol = path.join(TEST_DIR, "..", "hacim.js");
  const govde = fs.readFileSync(canliYol, "utf8");
  const basSha = crypto.createHash("sha256").update(govde).digest("hex");

  function carp(aile, k) {
    const capa = "\n  function " + aile + "(p) {";
    const n = govde.split(capa).length - 1;
    if (n !== 1) {
      throw new Error("CAPA TEK DEGIL (" + n + "): " + aile);
    }
    return govde.replace(capa, "\n  function " + aile + "(p) { return __m_" +
      aile + "(p) * " + k + "; }\n  function __m_" + aile + "(p) {");
  }

  const MUTANTLAR = [
    // --- OLDURUCU (KIRMIZI beklenir) ---
    ["yay +%5 tahsilat (OLCULEN ACIK KALEM; 1. katmanda YOK)",
     carp("yay", 1.05), true],
    ["konektor +%5 tahsilat (1. katmanda VAR — kontrol ekseni)",
     carp("konektor", 1.05), true],
    ["cerceve +%5 tahsilat (1. katmanda YOK)", carp("cerceve", 1.05), true],
    ["toka +%5 tahsilat (1. katmanda YOK)", carp("toka", 1.05), true],
    ["yay +%0,05 (tolerans USTU ince sapma)", carp("yay", 1.0005), true],
    // --- KONTROL (YESIL beklenir; yoksa 'kirmizi yaniyor' gurultudur) ---
    ["KONTROL: yalniz yorum satiri",
     govde.replace("  // === AILE: yay ===",
       "  // kontrol mutanti — davranis degismez\n  // === AILE: yay ==="), false],
    ["KONTROL: yalniz bos satir", govde.replace("\n  function yay(p) {",
      "\n\n  function yay(p) {"), false],
    ["KONTROL: tolerans ALTI sapma (+%0,001)", carp("yay", 1.00001), false],
  ];

  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "kalib-mut-"));
  const ortakOrtam = Object.assign({}, process.env, {
    // CI ile AYNI kosul: kardes ev YOK -> 2. katman atlanir. Boylece oldurmeyi
    // 1./3. katmanlarin yaptigi KANITLANIR (kardes eve yaslanmis olmayiz).
    PRUVO_DOGRULAMA_DIR: path.join(gecici, "yok-boyle-dizin")
  });

  function kos(hacimGovdesi, etiket) {
    const yol = path.join(gecici, "hacim-" + etiket + ".js");
    fs.writeFileSync(yol, hacimGovdesi);
    const ortam = Object.assign({}, ortakOrtam, { PRUVO_HACIM_YOL: yol });
    const r = spawnSync(process.execPath, [__filename],
      { env: ortam, encoding: "utf8" });
    const m = /IDDIA: (\d+) SAP: (\d+)/.exec(r.stdout || "");
    return {
      rc: r.status,
      iddia: m ? Number(m[1]) : null,
      sap: m ? Number(m[2]) : null
    };
  }

  console.log("MUTASYON TURU — kalibrasyon senkron kapisi");
  const temel = kos(govde, "temel");
  let basarisiz = [];
  if (temel.rc !== 0 || temel.iddia === null || temel.sap !== 0) {
    basarisiz.push("TEMEL YESIL DEGIL: rc=" + temel.rc + " iddia=" +
      temel.iddia + " sap=" + temel.sap);
  }
  console.log("  temel: rc=" + temel.rc + " iddia=" + temel.iddia +
    " sap=" + temel.sap);

  MUTANTLAR.forEach(function (m, i) {
    const ad = m[0], kaynak = m[1], oldurucu = m[2];
    if (kaynak === govde) {
      basarisiz.push("MUTANT " + i + " KAYNAGI DEGISMEDI (capa tutmadi): " + ad);
      return;
    }
    const r = kos(kaynak, "m" + i);
    const beklenenIsaret = oldurucu ? (r.rc === 1 && r.sap > 0)
      : (r.rc === 0 && r.sap === 0);
    // COKME NOBETI: cikis kodu TEK BASINA kanit degildir — cokme (rc 2 / node
    // istisnasi) de "sifir disi" doner. Kosumun SONUNA kadar gittigi OLCULEN
    // IDDIA SAYISI ile kanitlanir: satir hic basilmadiysa (iddia === null)
    // kosum yarida kalmistir. Oldurucu mutantta iddia sayisi ARTAR (her sapan
    // set kendi satirini ekler), o yuzden alt sinir temeldir; kontrol mutantinda
    // hicbir sey degismemeli -> TAM ESITLIK aranir.
    const sayiTamam = r.iddia !== null &&
      (oldurucu ? r.iddia >= temel.iddia : r.iddia === temel.iddia);
    if (!beklenenIsaret || !sayiTamam) {
      basarisiz.push((oldurucu ? "OLDURUCU" : "KONTROL") + " mutant '" + ad +
        "' BEKLENTIYI KARSILAMADI: rc=" + r.rc + " sap=" + r.sap +
        " iddia=" + r.iddia + " (temel iddia=" + temel.iddia + ")");
    }
    console.log("  [" + (beklenenIsaret && sayiTamam ? "OK " : "SAP") + "] " +
      (oldurucu ? "OLDURUCU" : "KONTROL ") + " rc=" + r.rc + " sap=" +
      String(r.sap).padStart(3) + " iddia=" + r.iddia + "  " + ad);
  });

  // --- FAIL-CLOSED EKSENI: "OLCULEMEDI" YESIL SAYILMAMALI -------------------
  // Bu kapinin VAR OLMA SEBEBI, olculemeyen bir eksenin sessizce yesil
  // sayilmasiydi (kardes ev yoksa 2. katman ATLA -> yay mutanti gecti). Ayni
  // hatayi 3. katmanda tekrarlamadigimiz BURADA KANITLANIR: fikstur yoksa ya
  // da bir aile beyansiz kaldiysa kapi rc 2 (OLCULEMEDI) vermeli, 0 DEGIL.
  // Knob eklemeden olculur: jenerator/ agaci gecici dizine KOPYALANIR ve
  // KOPYADAKI kapi kosturulur (canli agac okunmaz bile).
  function kosKopya(donustur, etiket) {
    const hedef = path.join(gecici, "agac-" + etiket);
    fs.cpSync(path.join(TEST_DIR, ".."), hedef, {
      recursive: true,
      // calisma artiklarini (.openscad-yerel/, kilit dosyalari) tasima
      filter: function (k) { return path.basename(k).charAt(0) !== "."; }
    });
    const fikstur = path.join(hedef, "test", "kaynak-referans.json");
    donustur(fikstur);
    const r = spawnSync(process.execPath,
      [path.join(hedef, "test", "kalibrasyon-senkron.js")],
      { env: ortakOrtam, encoding: "utf8" });
    const m = /IDDIA: (\d+) SAP: (\d+)/.exec(r.stdout || "");
    return { rc: r.status, iddia: m ? Number(m[1]) : null };
  }

  const FAIL_CLOSED = [
    ["fikstur SILINDI -> OLCULEMEDI (rc 2)", function (yol) {
      fs.rmSync(yol);
    }, 2],
    ["bir aile fiksturden BEYANSIZ dusuruldu -> OLCULEMEDI (rc 2)",
     function (yol) {
       const d = JSON.parse(fs.readFileSync(yol, "utf8"));
       delete d.aileler.yay;   // ne kapsamda ne `disi_birakilan`da
       fs.writeFileSync(yol, JSON.stringify(d));
     }, 2],
    ["KONTROL: agac aynen kopyalandi -> YESIL (rc 0)", function () {}, 0],
  ];
  FAIL_CLOSED.forEach(function (f, i) {
    const r = kosKopya(f[1], "f" + i);
    const bekleniyor = f[2];
    const ok = r.rc === bekleniyor &&
      (bekleniyor === 0 ? r.iddia === temel.iddia : r.iddia === null);
    if (!ok) {
      basarisiz.push("FAIL-CLOSED vakasi '" + f[0] + "' KARSILANMADI: rc=" +
        r.rc + " (beklenen " + bekleniyor + ") iddia=" + r.iddia);
    }
    console.log("  [" + (ok ? "OK " : "SAP") + "] FAIL-CLOSED rc=" + r.rc +
      " iddia=" + r.iddia + "  " + f[0]);
  });
  if (FAIL_CLOSED.length < 3) {
    basarisiz.push("FAIL-CLOSED TABANI DUSTU: " + FAIL_CLOSED.length + " (taban 3)");
  }

  fs.rmSync(gecici, { recursive: true, force: true });
  const sonSha = crypto.createHash("sha256")
    .update(fs.readFileSync(canliYol, "utf8")).digest("hex");
  if (sonSha !== basSha) {
    basarisiz.push("CANLI AGAC DEGISTI (mutant kopyaya uygulanmadi): " +
      basSha.slice(0, 12) + " -> " + sonSha.slice(0, 12));
  }
  console.log("  canli hacim.js sha256 bas==son: " + (sonSha === basSha));
  const oldurucuSayisi = MUTANTLAR.filter(function (m) { return m[2]; }).length;
  const kontrolSayisi = MUTANTLAR.length - oldurucuSayisi;
  console.log("  olculen: " + oldurucuSayisi + " oldurucu + " + kontrolSayisi +
    " kontrol mutant, temel iddia " + temel.iddia);
  if (oldurucuSayisi < 5 || kontrolSayisi < 3) {
    basarisiz.push("MUTANT TABANI DUSTU: " + oldurucuSayisi + " oldurucu / " +
      kontrolSayisi + " kontrol (taban 5/3) — batarya bosaltilamaz.");
  }
  if (basarisiz.length) {
    basarisiz.forEach(function (s) { console.log("  ❌ " + s); });
    console.log("\nKIRMIZI: " + basarisiz.length + " sorun");
    process.exit(1);
  }
  console.log("\nYESIL");
  process.exit(0);
}
