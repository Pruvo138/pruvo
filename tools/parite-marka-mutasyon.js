#!/usr/bin/env node
"use strict";
/**
 * MUTASYON SURUCUSU — marka adi sorgusu ekseni GERCEK ihlali yakiyor mu?
 *
 *   node tools/parite-marka-ekseni.js --kendini-test     (bu dosyayi cagirir)
 *   node tools/parite-marka-mutasyon.js                  (dogrudan)
 *
 * Olculen kapi: tools/parite-marka-ekseni.js
 *
 * NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
 * ([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu repoda durur, AG/wrangler'a
 * DOKUNMAZ (her sey fikstur), ve kabul CIKIS KODU degil OLCULEN IMZA'dir:
 *   OZET yuzey=<..> olculen=<n> gecti=<n> ayrisan=<n> kalem=<n> olculemedi=<n>
 * Cokme (imza HIC basilmadi) "kirmizi" SAYILMAZ, ayrica raporlanir — yoksa cokerek
 * "kirmizi" gorunen bir mutant, gercekte olculmemis bir ekseni kanit diye yutturur.
 *
 * ── BATARYA IKI YONLU ─────────────────────────────────────────────────────────────
 * OLDURUCU: ekseni bozan degisiklik IMZAYI beklenen yonde DEGISTIRMELI.
 * KONTROL : davranisi degistirmeyen degisiklik IMZAYI AYNEN BIRAKMALI. Kontrol yoksa
 *           "daima kirmizi" bir eksen butun oldurucileri gecer -> ayirt edilemez
 *           ([[beyan-edilmis-survivor]]).
 * Ayrica GECIS SONRASI fikstur (F_SONRASI) tabanda YESIL yanmali: tek yonlu kurulmus bir
 * eksen gecisten sonra sonsuza kadar kirmizi kalirdi ve kimse fark etmezdi.
 *
 * CAPA DISIPLINI: her mutant capasinin kaynak dosyada BEKLENEN SAYIDA gecmesi SART.
 * Gecmezse sonuc "YESIL" degil "CAPA-YOK"tur (uygulanamayan mutantin yesil sayilmasi
 * bataryayi sessizce kor ederdi).
 *
 * NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac DEGISMEZ). Depo koku gecici bir
 * dizine symlink'lenir; `tools/` GERCEK dizin olarak kurulup icindeki her dosya
 * symlink edilir, mutasyona ugrayan TEK dosya gercek (mutantlanmis) kopyayla degistirilir.
 */

const cp = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const TOOLS = __dirname;
const KOK = path.dirname(TOOLS);
const EKSEN = "parite-marka-ekseni.js";

// ── FIKSTURLER ────────────────────────────────────────────────────────────────────
// Evren BILEREK gercek vakalardan secildi: Haval/MAN (alt-dize gurultusunun olculdugu
// markalar), Opel/Vauxhall (alias — ucun ayni kumeyi dondurmesi gereken cift).
const EVREN = ["Haval", "MAN", "Opel", "Vauxhall"];
const KUME = {
  Haval: ["hv-1", "hv-2"],
  MAN: ["mn-1", "mn-2", "mn-3", "mn-4"],
  Opel: ["op-1", "op-2", "op-3", "op-4", "op-5"],
  Vauxhall: ["op-1", "op-2", "op-3", "op-4", "op-5"],   // alias -> Opel'in TAM kumesi
};
const PENCERE = require("./parite-marka-ekseni.js").PENCERE;

function kopya(o) { return JSON.parse(JSON.stringify(o)); }

/** Uc cevabi kaliplayici. `karistir`: Ege gibi skorla siralanmis (kume ayni, sira ayri). */
function ucCevap(idler, karistir) {
  const l = idler.slice();
  if (karistir) l.reverse();
  return { toplam: idler.length, urunler: l };
}

/** F_SONRASI — GECIS SONRASI dunya: uc, kolonu okuyor. Taban YESIL olmali. */
function fSonrasi() {
  const site = {}, ege = {};
  for (const m of EVREN) { site[m] = ucCevap(KUME[m], false); ege[m] = ucCevap(KUME[m], true); }
  return { evren: EVREN, d1: kopya(KUME), capraz: kopya(KUME), uc: { site, ege } };
}

/** F_ONCESI — BUGUNKU uc: serbest-metin ALT-DIZE. Taban KIRMIZI olmali. */
function fOncesi() {
  const f = fSonrasi();
  // "Havalandirma" -> Haval · "Mandali"/"manuel" -> MAN · "Vauxhall" alt-dize hicbir
  // baslikta gecmez -> alakasiz kucuk kume. Opel alt-dize fazlasi ("Opel Astra" disi).
  f.uc.site.Haval = { toplam: 5, urunler: ["hv-1", "hv-2", "havalandirma-1", "havalandirma-2", "havalandirma-3"] };
  f.uc.site.MAN = { toplam: 9, urunler: ["mn-1", "mn-2", "mn-3", "mn-4", "mandal-1", "mandal-2", "manuel-1", "manuel-2", "manuel-3"] };
  f.uc.site.Opel = { toplam: 6, urunler: ["op-1", "op-2", "op-3", "op-4", "op-5", "opel-anahtarlik"] };
  f.uc.site.Vauxhall = { toplam: 0, urunler: [] };
  for (const m of EVREN) f.uc.ege[m] = kopya(f.uc.site[m]);
  return f;
}

/** F_BOS — evren BOS. "0 ayrisma" YESIL SAYILMAMALI (fail-closed). */
function fBos() { return { evren: [], d1: {}, capraz: {}, uc: { site: {}, ege: {} } }; }

/** F_KAYMA — kolon (D1) ile deponun kanonik govdesi AYRISMIS (senkron/yayin penceresi).
 *  Uc kolonla BIREBIR: capraz kapisi kalkarsa YESIL yanar, tabanda OLCULEMEDI olmali. */
function fKayma() {
  return {
    evren: ["Opel"],
    d1: { Opel: ["op-1", "op-2", "op-3"] },
    capraz: { Opel: ["op-1", "op-2"] },
    uc: { site: { Opel: ucCevap(["op-1", "op-2", "op-3"]) },
          ege: { Opel: ucCevap(["op-1", "op-2", "op-3"], true) } },
  };
}

/** F_PENCERE — kume PENCERE'yi ASIYOR. Uc dogru pencereyi + dogru toplami donuyor. */
function fPencere() {
  const idler = Array.from({ length: PENCERE + 7 }, (_, i) => "fd-" + String(i).padStart(5, "0"));
  return {
    evren: ["Ford"], d1: { Ford: idler }, capraz: { Ford: idler },
    uc: { site: { Ford: { toplam: idler.length, urunler: idler.slice() } },
          ege: { Ford: { toplam: idler.length, urunler: idler.slice() } } },
  };
}

/** F_SIRA — kume DOGRU, SIRA yanlis. site yuzeyinde KIRMIZI, ege yuzeyinde YESIL. */
function fSira() {
  const ids = ["op-1", "op-2", "op-3"];
  return {
    evren: ["Opel"], d1: { Opel: ids }, capraz: { Opel: ids },
    uc: { site: { Opel: { toplam: 3, urunler: ["op-3", "op-1", "op-2"] } },
          ege: { Opel: { toplam: 3, urunler: ["op-3", "op-1", "op-2"] } } },
  };
}

const FIKSTURLER = {
  F_SONRASI: fSonrasi, F_ONCESI: fOncesi, F_BOS: fBos,
  F_KAYMA: fKayma, F_PENCERE: fPencere, F_SIRA: fSira,
};

// ── MUTANTLAR ─────────────────────────────────────────────────────────────────────
// (ad, eski, yeni, kere, fikstur, yuzey, tur, kanit)
//   kere  : capanin kaynakta gecmesi GEREKEN sayi (uyusmazsa CAPA-YOK)
//   tur   : "OLDURUCU" (imza DEGISMELI) | "KONTROL" (imza AYNEN KALMALI)
const MUTANTLAR = [
  // ── OLDURUCU: evrenin TURETILMISLIGI ────────────────────────────────────────────
  {
    ad: "OLDURUCU O2 EVRENI ELLE LISTEYE CEVIR (turetim yerine sabit dizi)",
    kanit: "elle liste CURUR: yeni marka gelince eksiktir, silinen marka orada kalir. " +
      "Capraz kaynak (depo kanonik govdesi) bunu YAKALAMALI.",
    eski: "  const satirlar = fikstur ? fikstur.evrenSatirlari() : d1Sorgu(EVREN_SQL);\n" +
      "  const degerler = satirlar.map((r) => r.m).filter((v) => typeof v === \"string\" && v);",
    yeni: "  const degerler = [\"Haval\", \"MAN\", \"Opel\", \"Havalandirma\"];",
    kere: 1, fikstur: "F_SONRASI", yuzey: "site", tur: "OLDURUCU",
  },
  {
    ad: "OLDURUCU O3 KOLONU BIRLESIMLE OKU (marka_arama ∪ marka)",
    kanit: "`marka_arama` TEK BASINA okunur; ham `marka[]` evreni model kodlariyla dolu " +
      "(E46, 106, 190E...) — birlesim ekseni gurultuye bogar. Nobetci fail-closed dusurmeli.",
    eski: "  \"SELECT DISTINCT je.value AS m FROM urunler u, json_each(u.marka_arama) je \" +\n" +
      "  \"WHERE u.yayinda = 1 ORDER BY je.value\";",
    yeni: "  \"SELECT DISTINCT je.value AS m FROM urunler u, json_each(u.marka_arama) je \" +\n" +
      "  \"WHERE u.yayinda = 1 UNION SELECT DISTINCT je2.value AS m FROM urunler u2, \" +\n" +
      "  \"json_each(u2.marka) je2 WHERE u2.yayinda = 1 ORDER BY 1\";",
    kere: 1, fikstur: "F_SONRASI", yuzey: "site", tur: "OLDURUCU",
  },
  // ── OLDURUCU: fail-closed yonu ──────────────────────────────────────────────────
  {
    ad: "OLDURUCU O4 BOS EVRENI YESIL SAY (fail-open)",
    kanit: "\"hicbir marka bulamadim\" bir parite KANITI degildir; yesil verirse eksen " +
      "kaynagi koptugu gun sessizce susar.",
    eski: "    if (!s.olculen) {", yeni: "    if (false) {",
    kere: 1, fikstur: "F_BOS", yuzey: "site", tur: "OLDURUCU",
  },
  {
    ad: "OLDURUCU O5 CAPRAZ KAPISINI KAPAT (kolon≠depo sessizce gecsin)",
    kanit: "kolon bayatsa/ayrismissa hukum VERILEMEZ; kapi kalkinca bayat kolon " +
      "\"parite\" diye yesil yanar ([[yayin-penceresi-taslak-satir]]).",
    eski: "      if (eksik || caprazKume.size !== bekIds.length) {",
    yeni: "      if (false && (eksik || caprazKume.size !== bekIds.length)) {",
    kere: 1, fikstur: "F_KAYMA", yuzey: "site", tur: "OLDURUCU",
  },
  // ── OLDURUCU: pencere (kabul araligi ≠ kiyas araligi) ───────────────────────────
  {
    ad: "OLDURUCU O6a KIYAS ARALIGINI DARALT (pencereKirp PENCERE-1)",
    kanit: "kabul araligi genis, kiyas araligi dar olursa pencerenin son satirindaki " +
      "ayrisma sessizce yesil gecer ([[kabul-araligi-karsilastirma-araligi]]).",
    eski: "function pencereKirp(ids) { return ids.slice(0, PENCERE); }",
    yeni: "function pencereKirp(ids) { return ids.slice(0, PENCERE - 1); }",
    kere: 1, fikstur: "F_PENCERE", yuzey: "ege", tur: "OLDURUCU",
  },
  {
    ad: "OLDURUCU O6b KABUL ARALIGINI DARALT (uca giden limit PENCERE-1)",
    kanit: "ayni ayrismanin TERS yonu: uca dar pencere sorulup genis referansla " +
      "kiyaslanirsa eksen kendi kendini yaniltir.",
    eski: "  const limit = PENCERE;", yeni: "  const limit = PENCERE - 1;",
    kere: 1, fikstur: "F_PENCERE", yuzey: "ege", tur: "OLDURUCU",
  },
  // ── OLDURUCU: sira iddiasi ──────────────────────────────────────────────────────
  {
    ad: "OLDURUCU O7 SITE YUZEYINDE SIRA IDDIASINI DUSUR",
    kanit: "site yuzeyinde uc `ORDER BY seq DESC` doner; sira iddiasi dusunce katalog " +
      "sirasi bozulmasi olculmez olur.",
    eski: "  const sirali = yuzey === \"site\";", yeni: "  const sirali = false;",
    kere: 1, fikstur: "F_SIRA", yuzey: "site", tur: "OLDURUCU",
  },
  // ── KONTROL: davranis DEGISMEZ -> imza AYNEN kalmali ────────────────────────────
  {
    ad: "KONTROL K1 EVRENIN SIRASI DEGISTI (ayni kume, ters sira)",
    kanit: "eksen marka evreninin SIRASINA bagli OLMAMALI; bagliysa her D1 ORDER BY " +
      "degisikligi sahte kirmizi uretir.",
    eski: "  return { degerler, sql: EVREN_SQL, kaynak: fikstur ? \"fikstur\" : \"d1\" };",
    yeni: "  return { degerler: degerler.slice().reverse(), sql: EVREN_SQL, " +
      "kaynak: fikstur ? \"fikstur\" : \"d1\" };",
    kere: 1, fikstur: "F_SONRASI", yuzey: "site", tur: "KONTROL",
  },
  {
    ad: "KONTROL K2 DAVRANIS DEGISTIRMEYEN YENIDEN ADLANDIRMA (bekPencere -> refDilim)",
    kanit: "yeniden adlandirma kirmizi yakiyorsa eksen kod METNINE capalanmis demektir, " +
      "davranisa degil.",
    eski: "bekPencere", yeni: "refDilim", kere: 3,
    fikstur: "F_SONRASI", yuzey: "site", tur: "KONTROL",
  },
  {
    ad: "KONTROL K3 ILGISIZ KOLON (KUME_SQL'e u.kategori eklendi)",
    kanit: "nobetci `json_each` KOLONUNU olcer, SELECT listesinin genisligini DEGIL; " +
      "her ek kolona kirmizi yakan nobetci gurultudur, nobetci degildir.",
    eski: "  \"SELECT je.value AS m, u.id AS id FROM urunler u, json_each(u.marka_arama) je \" +",
    yeni: "  \"SELECT je.value AS m, u.id AS id, u.kategori AS kategori FROM urunler u, " +
      "json_each(u.marka_arama) je \" +",
    kere: 1, fikstur: "F_SONRASI", yuzey: "site", tur: "KONTROL",
  },
];

// ── KOSUM ALTYAPISI ───────────────────────────────────────────────────────────────

/** Depo kokunu symlink aynasina kur; `tools` GERCEK dizin olur (tek dosya degistirilebilsin). */
function aynaKur(hedef) {
  fs.mkdirSync(hedef, { recursive: true });
  for (const ad of fs.readdirSync(KOK)) {
    if (ad === "tools") continue;
    fs.symlinkSync(path.join(KOK, ad), path.join(hedef, ad));
  }
  const t = path.join(hedef, "tools");
  fs.mkdirSync(t);
  for (const ad of fs.readdirSync(TOOLS)) fs.symlinkSync(path.join(TOOLS, ad), path.join(t, ad));
  return t;
}

/** Ekseni kostur; doner: { kod, imza|null, cikti }. imza null => COKME (kirmizi SAYILMAZ). */
function kostur({ aynaTools, fiksturYolu, yuzey }) {
  const p = cp.spawnSync("node", [path.join(aynaTools, EKSEN), "--yuzey=" + yuzey], {
    encoding: "utf8", timeout: 120000,
    env: Object.assign({}, process.env, { PARITE_MARKA_FIKSTUR: fiksturYolu }),
  });
  const cikti = (p.stdout || "") + (p.stderr || "");
  const m = cikti.match(/^OZET yuzey=(\S+) olculen=(\d+) gecti=(\d+) ayrisan=(\d+) kalem=(\d+) olculemedi=(\d+)$/m);
  if (!m) return { kod: p.status, imza: null, cikti };
  return {
    kod: p.status,
    imza: { yuzey: m[1], olculen: +m[2], gecti: +m[3], ayrisan: +m[4], kalem: +m[5], olculemedi: +m[6] },
    cikti,
  };
}

function imzaMetni(r) {
  if (!r.imza) return "COKME (imza basilmadi, rc=" + r.kod + ")";
  const i = r.imza;
  return "rc=" + r.kod + " olculen=" + i.olculen + " gecti=" + i.gecti +
    " ayrisan=" + i.ayrisan + " olculemedi=" + i.olculemedi;
}

/** Iki kosum "ayni hukum" mu? (kalem sayisi teshis, hukum DEGIL -> disarida) */
function ayniImza(a, b) {
  if (!a.imza || !b.imza) return false;
  return a.kod === b.kod && a.imza.olculen === b.imza.olculen && a.imza.gecti === b.imza.gecti &&
    a.imza.ayrisan === b.imza.ayrisan && a.imza.olculemedi === b.imza.olculemedi;
}

function yesilMi(r) {
  return !!r.imza && r.kod === 0 && r.imza.ayrisan === 0 && r.imza.olculen > 0 &&
    r.imza.gecti === r.imza.olculen && r.imza.olculemedi === 0;
}

function main() {
  const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-marka-mutasyon-"));
  const fikDizin = path.join(gecici, "fikstur");
  fs.mkdirSync(fikDizin);
  const fikYol = {};
  for (const ad of Object.keys(FIKSTURLER)) {
    fikYol[ad] = path.join(fikDizin, ad + ".json");
    fs.writeFileSync(fikYol[ad], JSON.stringify(FIKSTURLER[ad]()));
  }
  const aynaTools = aynaKur(path.join(gecici, "ayna"));
  const kaynak = fs.readFileSync(path.join(TOOLS, EKSEN), "utf8");

  let basarisiz = 0, sapan = 0, cokme = 0;
  const oldurucu = { toplam: 0, kirmizi: 0 };
  const kontrol = { toplam: 0, yesil: 0 };

  console.log("MUTASYON BATARYASI — %s\nayna: %s\n", EKSEN, aynaTools);

  // ── A) TABAN OLCUMLERI (fikstur davranisi; mutasyon YOK) ────────────────────────
  console.log("── A) TABAN (mutasyonsuz) ─────────────────────────────────────────────");
  const taban = {};
  const tabanIddialar = [
    ["F_SONRASI", "site", "GECIS SONRASI FIKSTUR YESIL YANMALI (tek yonlu eksen tuzagi)",
      (r) => yesilMi(r)],
    ["F_SONRASI", "ege", "GECIS SONRASI FIKSTUR YESIL YANMALI (ege yuzeyi, kume iddiasi)",
      (r) => yesilMi(r)],
    ["F_ONCESI", "site", "OLDURUCU O1: UC ESKI DAVRANISTA -> KIRMIZI (ayrisan=4)",
      (r) => !!r.imza && r.kod === 1 && r.imza.ayrisan === 4],
    ["F_ONCESI", "ege", "OLDURUCU O1: UC ESKI DAVRANISTA -> KIRMIZI (ege yuzeyi)",
      (r) => !!r.imza && r.kod === 1 && r.imza.ayrisan === 4],
    ["F_BOS", "site", "BOS EVREN -> OLCULEMEDI (fail-closed; ASLA yesil)",
      (r) => !!r.imza && r.kod === 3 && r.imza.olculen === 0],
    ["F_KAYMA", "site", "KOLON≠DEPO -> OLCULEMEDI (kirmizi DEGIL, yesil DEGIL)",
      (r) => !!r.imza && r.kod === 3 && r.imza.olculen === 0 && r.imza.olculemedi === 1],
    ["F_PENCERE", "ege", "PENCERE ASAN MARKA -> YESIL (dogru pencere + dogru toplam)",
      (r) => yesilMi(r)],
    ["F_PENCERE", "site", "PENCERE ASAN MARKA -> YESIL (sirali dal)", (r) => yesilMi(r)],
    ["F_SIRA", "site", "SIRA BOZUK -> site yuzeyi KIRMIZI",
      (r) => !!r.imza && r.kod === 1 && r.imza.ayrisan === 1],
    ["F_SIRA", "ege", "SIRA BOZUK -> ege yuzeyi YESIL (sira iddiasi YOK)", (r) => yesilMi(r)],
  ];
  for (const [fik, yuzey, iddia, kosul] of tabanIddialar) {
    const r = kostur({ aynaTools, fiksturYolu: fikYol[fik], yuzey });
    taban[fik + "/" + yuzey] = r;
    if (!r.imza) cokme++;
    const ok = kosul(r);
    if (!ok) basarisiz++;
    // NOT: console.log %-14s gibi genislik belirtecini DESTEKLEMEZ (Node util.format);
    // hizalama padEnd ile yapilir, yoksa cikti "%-14s" diye BASILIR.
    console.log("  " + (ok ? "✅" : "❌") + " " + fik.padEnd(10) + " " + yuzey.padEnd(5) +
      " " + iddia + "\n      " + imzaMetni(r));
    if (!ok) console.log(r.cikti.split("\n").slice(-25).join("\n"));
  }

  // ── B) MUTANTLAR ────────────────────────────────────────────────────────────────
  console.log("\n── B) MUTANTLAR ───────────────────────────────────────────────────────");
  const hedef = path.join(aynaTools, EKSEN);
  for (const mut of MUTANTLAR) {
    const kereBulunan = kaynak.split(mut.eski).length - 1;
    if (kereBulunan !== mut.kere) {
      console.log("  ⛔ CAPA-YOK  %s\n      capa %d kez beklendi, %d bulundu",
        mut.ad, mut.kere, kereBulunan);
      basarisiz++;
      continue;
    }
    const mutantli = kaynak.split(mut.eski).join(mut.yeni);
    fs.rmSync(hedef, { force: true });
    fs.writeFileSync(hedef, mutantli);
    const r = kostur({ aynaTools, fiksturYolu: fikYol[mut.fikstur], yuzey: mut.yuzey });
    fs.rmSync(hedef, { force: true });
    fs.symlinkSync(path.join(TOOLS, EKSEN), hedef);

    const t = taban[mut.fikstur + "/" + mut.yuzey];
    if (!t) { console.log("  ⛔ TABAN YOK: %s/%s", mut.fikstur, mut.yuzey); basarisiz++; continue; }
    if (!r.imza) cokme++;

    if (mut.tur === "OLDURUCU") {
      oldurucu.toplam++;
      // OLDURULDU = imza tabandan FARKLI. Cokme oldurme SAYILMAZ (imza basilmadi).
      const oldu = !!r.imza && !ayniImza(r, t);
      if (oldu) oldurucu.kirmizi++; else { basarisiz++; sapan++; }
      console.log("  %s %s\n      taban: %s\n      mutant: %s\n      gerekce: %s",
        oldu ? "✅ OLDURULDU" : "❌ HAYATTA", mut.ad, imzaMetni(t), imzaMetni(r), mut.kanit);
      if (!oldu) console.log(r.cikti.split("\n").slice(-25).join("\n"));
    } else {
      kontrol.toplam++;
      const ayni = ayniImza(r, t);
      if (ayni) kontrol.yesil++; else { basarisiz++; sapan++; }
      console.log("  %s %s\n      taban: %s\n      mutant: %s\n      gerekce: %s",
        ayni ? "✅ YESIL KALDI" : "❌ SAPTI", mut.ad, imzaMetni(t), imzaMetni(r), mut.kanit);
      if (!ayni) console.log(r.cikti.split("\n").slice(-25).join("\n"));
    }
  }

  console.log("\n── OZET ───────────────────────────────────────────────────────────────");
  console.log("TABAN IDDIA      : %d (hepsi gecmeli)", tabanIddialar.length);
  console.log("OLDURUCU         : %d/%d KIRMIZI", oldurucu.kirmizi, oldurucu.toplam);
  console.log("KONTROL          : %d/%d YESIL", kontrol.yesil, kontrol.toplam);
  console.log("SAPAN            : %d", sapan);
  console.log("COKME            : %d (kirmiziyla KARISTIRILMAZ)", cokme);
  console.log("BATARYA_OZET oldurucu=%d/%d kontrol=%d/%d sapan=%d cokme=%d basarisiz=%d",
    oldurucu.kirmizi, oldurucu.toplam, kontrol.yesil, kontrol.toplam, sapan, cokme, basarisiz);
  fs.rmSync(gecici, { recursive: true, force: true });

  if (basarisiz) {
    console.log("\nSONUC: BATARYA KIRMIZI ❌ (%d basarisiz iddia)", basarisiz);
    process.exit(1);
  }
  console.log("\nSONUC: BATARYA TEMIZ ✅ (oldurucilerin hepsi kirmizi, kontrollerin hepsi yesil)");
  process.exit(0);
}

module.exports = { main, MUTANTLAR, FIKSTURLER };

if (require.main === module) main();
