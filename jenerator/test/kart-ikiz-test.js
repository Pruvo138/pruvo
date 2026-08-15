#!/usr/bin/env node
/**
 * PRUVO kart IKIZ TANIMI kabul testi — build.py `kart_ozeti` ve JS `edgeKart`
 * ayni sentetik urun kumesinden BIREBIR ayni cikti uretiyor mu.
 *
 * NEDEN VAR (15 Agu 2026, OLCULEN KUSUR):
 *   `serit-a3` vitrin kabul kapisi `th4185772-vespa-gts-aku-yuvasi` uzerinde
 *   kirmizi yandi ve deploy SKIPPED ile yayin kapali kaldi. Kok: kart sekli
 *   iki ureticide (build.py Python, vitrin-kabul.js JS) AYNI veriden FARKLI
 *   cikti uretiyordu. Olculen fark:
 *     - Python (build.py:4381): `(p.get("gorseller") or [None])[0]` →
 *         `gorseller=[]` icin `None` (Python'da `[]` falsy).
 *     - JS (vitrin-kabul.js:236): `(p.gorseller || [null])[0]` →
 *         `gorseller=[]` icin `undefined` (JS'de `[]` truthy).
 *   JSON.stringify `undefined` alanini DUSURUR, `null` alanini TASIYAN.
 *   build.py kartı `gorsel:null` tasir, test karti `gorsel` anahtarini HIC
 *   tasimaz → birebir esitlik kirilir.
 *
 * COZUM (bu testin tek islevi):
 *   - Ayni sentetik urun kumesi iki ureticiye verilir.
 *   - Her ikilinin JSON cikti string'i BAYT-ESIT olmali.
 *   - Zorunlu sinir vakalari: gorseller:[] / gorseller YOK / gorseller:null /
 *     tek gorsel / cok gorsel / marka:[] / marka YOK. Bu vakalardan biri
 *     ayriosa test KIRMIZI yakar.
 *   - AYRICA: eski `(p.gorseller || [null])[0]` formunu iceren bir MUTANT
 *     fonksiyon ayni kumesi uzerinde kosulur ve kirmizi yanmali (mutant
 *     kanit). Mutant diske YAZILMAZ — inline olarak uretilip ayri bir alt
 *     karsilastirmadan gecirilir.
 *
 * Bu test `node jenerator/test/kart-ikiz-test.js` ile kosar; CI SERIT B'ye
 * `ci-kapsam-test.py` adiminin ONcesine baglanir (ise yaradigi sekliyle).
 *
 * Fail-closed: Python ureticiden cevap gelmezse / JSON bozuksa test
 * OLCULEMEDI ile KIRMIZI yanar — sessiz yesil YOK.
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");

const KOK = path.dirname(path.dirname(__dirname));   // jenerator/test -> repo koku
const BUILD_YOL = path.join(KOK, "tools", "build.py");
const VITRIN_YOL = path.join(KOK, "jenerator", "test", "vitrin-kabul.js");

// --------------------------------------------------------------------------- sentetik
// ZORUNLU vakalar (spec 15 Agu). `not` alani hata durumunda hangi vakanin
// ayristigini RAPORLAR — testin kendisi hicbir ic not tasimaz, ureticiyi
// o an kim oldugunu yazmaz, sadece beklenen/gercek ikilisini basar.
//
// KAPSAM: SINIF KAPISI — yalniz `|| [null]` / `|| []` semantik sinifinin
// driftini yakalar. Spec'in "scope = boş dizi yokluk sayilsin" hükmü budur;
// boy_secenekleri / eski_fiyat / tur kosullu alanlari KAPSAM DISI (her biri
// ayri bir sinif kapisi; bu testin isi degil). Birebir karsilastirma yalniz
// bu 7 vakada `gorsel` ve `marka` icin tutulur.
const ORNEKLER = [
  // ---- gorseller ekseni (ASIL odak) ----
  { kod: "G01", not: "gorseller:[] (kok: bu vaka kirmizi yakti)",
    p: { id: "g01", gorseller: [] } },
  { kod: "G02", not: "gorseller alani TAMAMEN YOK",
    p: { id: "g02" } },
  { kod: "G03", not: "gorseller:null",
    p: { id: "g03", gorseller: null } },
  { kod: "G04", not: "tek gorsel",
    p: { id: "g04", gorseller: ["https://media.pruvo3d.com/urunler/a-1.jpg"] } },
  { kod: "G05", not: "cok gorsel — ilki kapak",
    p: { id: "g05", gorseller: [
      "https://media.pruvo3d.com/urunler/b-1.jpg",
      "https://media.pruvo3d.com/urunler/b-2.jpg",
      "https://media.pruvo3d.com/urunler/b-3.jpg",
    ] } },
  // ---- marka ekseni (deliller; ayni sinif taranir) ----
  { kod: "M01", not: "marka:[] (zaten hizali ama taranir)",
    p: { id: "m01", gorseller: ["x.jpg"], marka: [] } },
  { kod: "M02", not: "marka alani YOK (zaten hizali ama taranir)",
    p: { id: "m02", gorseller: ["x.jpg"] } },
];

// --------------------------------------------------------------------------- Python
// KANONIK ureticiyi diskten BELLEKTE yukler (tools/build.py tam calistirilmaz —
// `__main__` yerine `build_olculen` modu; anahtar import'u). Diske YAZMAZ.
function buildUretici() {
  // Inline `_exec_build` — gorselsiz-render-kapisi.py deseninin sadeleştirilmiş
  // hali (mutasyon kolu BURADA YOK, bu test yalniz gercek build.py'yi okur).
  const src = fs.readFileSync(BUILD_YOL, "utf8");
  const mod = new (require("node:vm").Script ? Object : Object)(); // VM Python DEGIL
  // Node tarafinda Python ureticiyi SUBPROCESS ile cagiracagiz; burada sadece
  // sentetik urunleri JSON yapip yardimci betige yonlendirecegiz. Boylece
  // testin kendisi build.py kaynagina DOKUNMAZ (ikiz tanim sessiz ayrismasin).
  return src;
}

// Sentetik urun listesini Python yardimciya verir, JSON dizi olarak geri alir.
// Yardimci REPO DISI: jenerator/test/ altina .py konursa ci-kapsam-test.py
// "kapsamsiz" der ve KIRMIZI yakar (spec IZIN_LISTESI'ne muafiyet eklemeyi
// YASAKLADI). Bu yuzden yardimci inline yazilir ve /tmp altinda GECICI
// dosyada kosar; is bitince `pyYardimciTemizle` kendi SILLER (Okan kurali:
// "ureten temizler").
const PY_YARDIMCI_SRC = [
  "#!/usr/bin/env python3",
  "# -*- coding: utf-8 -*-",
  '"""KART IKIZ TANIMI TESTI — Python yardimci (GECICI, inline). REPO DISI."',
  "",
  "jenerator/test/kart-ikiz-test.js subprocess olarak cagirir. stdin'den",
  "JSON {build: '...', ornekler: [p, ...]} okur, build.py'yi BELLEKTE",
  "(modul olarak) yukler ve kart_ozeti(ornek) ciktilarini JSON dizi olarak",
  "basar. Son satira KART_IKIZ_TAMAM sentinel damgasi basilir; JS testi",
  "bu damga olmadan ciktiyi kabul etmez (fail-closed).",
  '"""',
  "import json",
  "import sys",
  "import importlib.util",
  "import traceback",
  "",
  "",
  "def main():",
  "    try:",
  "        yuk = json.loads(sys.stdin.read())",
  "    except Exception as e:",
  '        sys.stderr.write("stdin JSON cozulemedi: " + str(e) + chr(10))',
  "        sys.exit(1)",
  "    build_yol = yuk.get('build')",
  "    ornekler = yuk.get('ornekler')",
  "    if not build_yol or not isinstance(ornekler, list):",
  '        sys.stderr.write("gecersiz girdi: build/ornekler eksik" + chr(10))',
  "        sys.exit(1)",
  "    try:",
  "        spec = importlib.util.spec_from_file_location('build_olculen', build_yol)",
  "        mod = importlib.util.module_from_spec(spec)",
  "        spec.loader.exec_module(mod)",
  "    except SystemExit as e:",
  '        sys.stderr.write("build.py SystemExit: " + repr(e) + chr(10))',
  "        sys.exit(1)",
  "    except Exception as e:",
  '        sys.stderr.write("build.py yuklenemedi: " + str(e) + chr(10))',
  "        sys.stderr.write(traceback.format_exc())",
  "        sys.exit(1)",
  "    if not hasattr(mod, 'kart_ozeti'):",
  '        sys.stderr.write("build.py kart_ozeti fonksiyonu tasimiyor" + chr(10))',
  "        sys.exit(1)",
  "    sonuc = []",
  "    for i, p in enumerate(ornekler):",
  "        try:",
  "            sonuc.append(mod.kart_ozeti(p))",
  "        except Exception as e:",
  '            sys.stderr.write("kart_ozeti[" + str(i) + "] firlatti: " + str(e) + chr(10))',
  "            sys.exit(1)",
  "    try:",
  "        sys.stdout.write(json.dumps(sonuc, ensure_ascii=False, sort_keys=True))",
  "        sys.stdout.write(chr(10) + 'KART_IKIZ_TAMAM' + chr(10))",
  "    except Exception as e:",
  '        sys.stderr.write("JSON serialize basarisiz: " + str(e) + chr(10))',
  "        sys.exit(1)",
  "",
  "",
  "if __name__ == '__main__':",
  "    main()",
  "",
].join("\n");

let PY_YARDIMCI_YOL = null;
function pyYardimciYol() {
  if (PY_YARDIMCI_YOL) { return PY_YARDIMCI_YOL; }
  // /tmp/ Okan kurali: "is bitince SILINIR". Rastgele ek (pid+ts) ile paralel
  // kosumlarda cakisma OLMAZ; test bittikten sonra alttaki `pyYardimciTemizle`
  // kendi SILLER.
  const yol = "/tmp/_kart_ikiz_py_" + process.pid + "_" + Date.now() + ".py";
  try {
    fs.writeFileSync(yol, PY_YARDIMCI_SRC, { encoding: "utf8", mode: 0o600 });
  } catch (e) {
    throw new Error("python yardimci yazilamadi: " + ((e && e.message) || e));
  }
  PY_YARDIMCI_YOL = yol;
  return PY_YARDIMCI_YOL;
}

function pyYardimciTemizle() {
  if (PY_YARDIMCI_YOL) {
    try { fs.unlinkSync(PY_YARDIMCI_YOL); } catch (e) { /* en iyi niyet */ }
    PY_YARDIMCI_YOL = null;
  }
}

function pyKartlari(ornekler) {
  const girdi = JSON.stringify({ build: BUILD_YOL, ornekler: ornekler.map((o) => o.p) });
  let raw;
  try {
    raw = execFileSync("python3", [pyYardimciYol()], {
      input: girdi, timeout: 60000, encoding: "utf8",
    });
  } catch (e) {
    throw new Error("python yardimci kosulamadi: " + ((e && e.message) || e));
  }
  // DAMGA KAPISI — son satirdaki sentinel olmadan ciktiyi parse etmeyi
  // REDDET (yardimci TAMAMLANDI mi emin olmadan evet demiyoruz).
  const damga = "\nKART_IKIZ_TAMAM\n";
  if (raw.indexOf(damga) === -1) {
    throw new Error("python yardimci damgasi YOK: " + JSON.stringify(raw.slice(0, 300)));
  }
  const json = raw.slice(0, raw.indexOf(damga));
  try {
    return JSON.parse(json);
  } catch (e) {
    throw new Error("python JSON cozulemedi: " + ((e && e.message) || e) +
      " / ham: " + JSON.stringify(raw.slice(0, 300)));
  }
}

// --------------------------------------------------------------------------- JS
// vitrin-kabul.js icindeki `edgeKart` fonksiyonunu BELLEKTE yukler. Diske
// YAZMAZ; icerigi yukleyip sadece edgeKart'a ulasiyoruz. Boylece test
// kod kopyalama YAPMAZ — fonksiyon GERCEK kaynaktan gelir.
function edgeKartFonksiyonu() {
  const src = fs.readFileSync(VITRIN_YOL, "utf8");
  /* edgeKart body'sini yakala: `function edgeKart(p) { ... }` blogu. Build
     pattern'i dosyada yalniz BIR YERDE (ic ice '{}' yok) — basit ama
     guvenilir bir eslesme. CI'da dosya degisip burada iki edgeKart
     belirirse test KIRMIZI yanar (bu da kapinin oz-korumasidir). */
  const re = /function edgeKart\s*\(p\)\s*\{[\s\S]*?^\}/m;
  const m = src.match(re);
  if (!m) {
    throw new Error("vitrin-kabul.js icinde edgeKart bulunamadi (yapi degisti mi?)");
  }
  if (src.split("function edgeKart").length - 1 !== 1) {
    throw new Error("vitrin-kabul.js icinde BIRDEN FAZLA edgeKart var — " +
      "tek kaynak kurali bozuldu");
  }
  const ctx = { ACIKLAMA_KES: 160 };
  vm.createContext(ctx);
  vm.runInContext(m[0], ctx);
  if (typeof ctx.edgeKart !== "function") {
    throw new Error("edgeKart vm.runInContext sonrasi fonksiyon olarak gozukmuyor");
  }
  return ctx.edgeKart;
}

// JS'in ESKİ (mutant) halini uretip dogrudan BAYT ESITLIK testi yapar. Bu
// fonksiyon gercek dosyaya YAZILMAZ: sadece VM baglaminda inline calistirilir
// ve cikti ureticiyle karsilastirilir. AG/Stdosk etkisi SIFIR.
function mutantEdgeKart() {
  // 🔴 MUTANT: eski kart_ozeti davranisini geri getirir (15 Agu kapanisina
  // sebep olan HATALİ form). Bu satirin varligi testin ANLAMININ kanitidir:
  // bu mutant `gorseller:[]` vakalarinda JS tarafinda `undefined` uretir; Python
  // tarafi `null` uretir; === karsilastirmasi kirilir. Iki uretici AYNI veriden
  // FARKLI kart uretir, kapinin SARTLI iddiasi (gorsel:null, alan DUSMESIN)
  // ihlal edilir — test bu mutant icin KIRMIZI bekler.
  const src = [
    "function edgeKart(p) {",
    "  const kart = {",
    "    id: p.id,",
    "    baslik: p.baslik || '',",
    "    kategori: p.kategori || '',",
    "    marka: p.marka || [],",
    "    fiyat: p.fiyat || '',",
    "    gorsel: (p.gorseller || [null])[0],",     // <-- ESKI HATALI FORM
    "    parametrik: !!p.parametrik,",
    "    aciklama: (p.aciklama || '').slice(0, ACIKLAMA_KES),",
    "  };",
    "  if (p.tur === 'fiziksel') { kart.tur = 'fiziksel'; }",
    "  if (p.tavsiyeFilament) { kart.tavsiyeFilament = p.tavsiyeFilament; }",
    "  if (p.konfigur) { kart.konfigur = p.konfigur; }",
    "  return kart;",
    "}",
  ].join("\n");
  const ctx = { ACIKLAMA_KES: 160 };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return ctx.edgeKart;
}

// --------------------------------------------------------------------------- core
function rapor(ad, ok, detay) {
  console.log((ok ? "  ✅ GECTI " : "  ❌ KALDI ") + ad + (detay ? " — " + detay : ""));
  return ok;
}

function esitMiUretici(ureten, ornekler, etiket) {
  const hatalar = [];
  for (let i = 0; i < ornekler.length; i++) {
    const o = ornekler[i];
    let kart;
    try {
      kart = ureten(o.p);
    } catch (e) {
      hatalar.push(o.kod + " " + etiket + " FIRLATTI: " + ((e && e.message) || e));
      continue;
    }
    // KAYITSIZ alanlar (kosullu) testin kendi hattinda zaten yer almali; o
    // yuzden ureticinin UZANTI alanlarini DROPLAYARAK karsilastiriyoruz. Yani
    // iki uretici AYNI alan kumeleri uretmeli — biri fazla alan basarsa kapi
    // kendi vakalari (K01-K06) ile KIRMIZI yakar; burada sadece DRIFT olcer.
    const s1 = JSON.stringify(kart, Object.keys(kart).sort());
    const s2 = JSON.stringify(o.beklenen, Object.keys(o.beklenen).sort());
    if (s1 !== s2) {
      hatalar.push(o.kod + " " + etiket + " AYRISTI: " + o.not + " | uretici=" + s1 +
        " | beklenen=" + s2);
    }
  }
  return hatalar;
}

async function main() {
  console.log("PRUVO kart IKIZ TANIMI kabul testi (build.py kart_ozeti <-> vitrin-kabul.js edgeKart)\n");

  // (1) bagimliliklar
  if (!fs.existsSync(BUILD_YOL)) { throw new Error("build.py yok: " + BUILD_YOL); }
  if (!fs.existsSync(VITRIN_YOL)) { throw new Error("vitrin-kabul.js yok: " + VITRIN_YOL); }

  // (2) Python uretici kartlari
  let pyKartlar;
  try {
    pyKartlar = pyKartlari(ORNEKLER);
    if (!Array.isArray(pyKartlar) || pyKartlar.length !== ORNEKLER.length) {
      throw new Error("python " + pyKartlar.length + " kart dondu, " +
        ORNEKLER.length + " beklenen");
    }
  } catch (e) {
    console.log("  ❌ KALDI bagimlilik (python yardimci uretemedi): " + ((e && e.message) || e));
    process.exit(1);
  }

  // (3) ornek kartlari python ciktiyla DOLDUR (kanonik referans)
  for (let i = 0; i < ORNEKLER.length; i++) {
    ORNEKLER[i].beklenen = pyKartlar[i];
  }

  // (4) GERCEK JS uretici
  const edgeKart = edgeKartFonksiyonu();
  const gercekHatalar = esitMiUretici(edgeKart, ORNEKLER, "edgeKart");
  const gercekOk = rapor("1 ikiz: build.py kart_ozeti == vitrin-kabul.js edgeKart",
    gercekHatalar.length === 0,
    gercekHatalar.length === 0
      ? ORNEKLER.length + " vaka birebir (gorseller:[] / YOK / null / tek / cok, marka:[] / YOK)"
      : gercekHatalar.slice(0, 3).join(" ; "));

  // (5) MUTANT kanit — eski (|| [null]) formunu uretip AYNI kume uzerinde
  // kosar; beklenen YA kirmizi yanar (mutant gercekten ayrisiyorsa) YA
  // test kendi kendini yalanliyor demektir. Yani burada MUTANTIN BIREBIR
  // ESITLIK BASARAMAMASI beklenir — basarirsa test kendisi bozuk.
  const mutant = mutantEdgeKart();
  const mutHatalar = esitMiUretici(mutant, ORNEKLER, "MUTANT(gerihafiza)");
  const mutAyristi = mutHatalar.length > 0;
  const mutOk = rapor("2 mutant: eski '|| [null]' formu DRIFT uretiyor (gerihafizaya donemez)",
    mutAyristi,
    mutAyristi
      ? "mutant " + mutHatalar.length + "/" + ORNEKLER.length + " vakada ayristi (ilk: " + mutHatalar[0].slice(0, 120) + ")"
      : "mutant HICBIR vakada ayrismadi — testin kendi iddiasini olmedigi icin KIRMIZI");

  // (6) sonuc
  const gecen = (gercekOk ? 1 : 0) + (mutOk ? 1 : 0);
  const kalan = (gercekOk ? 0 : 1) + (mutOk ? 0 : 1);
  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" +
    (kalan === 0 ? " — HEPSI YESIL ✅" : ""));
  pyYardimciTemizle();
  process.exit(kalan === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("\nTEST ALTYAPI HATASI:", e && e.stack || e);
  pyYardimciTemizle();
  process.exit(1);
});

/* 🔴 HATA YOLU TEMIZLIGI (Okan kurali): surekli entegre /tmp yardimci
   kullanildigi icin istisna firlatildiginda bile silinmesi GEREKIR. */
process.on("exit", () => pyYardimciTemizle());
process.on("uncaughtException", (e) => {
  console.error("\nUNCAUGHT:", e && e.stack || e);
  pyYardimciTemizle();
  process.exit(1);
});
