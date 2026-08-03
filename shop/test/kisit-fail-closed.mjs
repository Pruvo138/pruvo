#!/usr/bin/env node
/**
 * SEMA `kisitlar` x SIPARIS/ODEME YOLU — FAIL-CLOSED KABUL TESTI.
 *
 *   node shop/test/kisit-fail-closed.mjs                 # kabul bataryasi (deploy.yml'de BLOKLAYICI)
 *   node shop/test/kisit-fail-closed.mjs --kendini-test  # mutasyon bataryasi (nobetci olu mu?)
 *
 * SORULAN SORU (2026-08-03 olcumu): sema `kisitlar` bloklari — kosullu URETILEBILIRLIK
 * kurallari — SIPARIS/ODEME yolunda UYGULANIYOR MU? Cevap: iyi bicimli kural icin EVET
 * (`parametrikHesapla` -> `KONF.dogrula` zincirinde; canli /api/shop/fiyat ucunda vida
 * civata M3 `parametre-araligi` ile reddediliyor). AMA taninmayan/okunamayan bir kisit
 * kaydi SESSIZCE ATLANIYORDU ve ayni yol FIYAT URETIYORDU (olculdu: 10.000 ve 29.116
 * kurus). Kisit bir uretilebilirlik kapisidir: "olculemedi" ile "gecerli" AYNI SEY DEGIL.
 *
 * KAPSAM — bu test PARA yolunun kendisini kosar: shop/src/parametrik.js (Worker'in
 * shippen dosyasi) + jenerator/konfigurator.js + jenerator/hacim.js + secenekler.js.
 * OFFLINE: ag YOK, wrangler YOK, D1 YOK, siparis YOK, depo dosyasi YAZILMAZ
 * (mutantlar isletim sistemi gecici dizinine kopyalanir, kaynak sha256'si bas/son
 * karsilastirilir).
 *
 * 🔴 ALLOWLIST BELLEKTE ACILIR: kisitli iki aile (rulman/vida) bugun satis
 * allowlist'inde (secenekler.js HACIM_DOGRULANMIS_AILELER) DEGIL — o yuzden kisit
 * ekseni onlarda dogrudan olculemez ("hacim-dogrulanmamis" once doner). Test
 * allowlist'i YALNIZ BELLEKTE gecici acar, kosum sonunda geri alir ve geri
 * alindigini AYRI BIR IDDIA ile olcer. Dosya DEGISMEZ; rulman satisa ACILMAZ.
 *
 * 🔴 IDDIA SAYISI BU YORUMA YAZILMAZ — betik son satirda kendisi basar (bayat sayi
 * kosumun neyi olctugu hakkinda yanlis guven verir; bu depoda olculdu).
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const SHOP = path.dirname(BURASI);
const KOK = path.dirname(SHOP);
const SEMA_DIZIN = path.join(KOK, "jenerator", "urunler");
const require = createRequire(import.meta.url);
const KENDINI_TEST = process.argv.includes("--kendini-test");

const KAYNAKLAR = [
  path.join(KOK, "jenerator", "konfigurator.js"),
  path.join(KOK, "jenerator", "hacim.js"),
  path.join(KOK, "shop", "src", "parametrik.js"),
  path.join(KOK, "secenekler.js"),
];
const sha = (f) => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");
const shaHepsi = () => KAYNAKLAR.map((f) => path.basename(f) + "=" + sha(f).slice(0, 12)).join(" ");
const SHA_BAS = shaHepsi();

require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi — fiyat kurali tek kaynagi yok"); }
const KONF = require(path.join(KOK, "jenerator", "konfigurator.js"));

const ALLOW = SECENEK.HACIM_DOGRULANMIS_AILELER;
const ALLOW_ORJ = Object.keys(ALLOW).slice().sort();

const semaOku = (dosya) => JSON.parse(fs.readFileSync(path.join(SEMA_DIZIN, dosya), "utf8"));
const semaKopya = (dosya) => JSON.parse(JSON.stringify(semaOku(dosya)));
const S_RULMAN = "olcuye-ozel-rulman.json";
const S_VIDA = "olcuye-ozel-vida-civata-somun-pul.json";
const S_KUTU = "olcuye-ozel-kutu-organizer.json";

// Kisitin REDDETTIGI ve KABUL ETTIGI setler (iki yonlu olcum — tek yon olu nobetcidir).
// rulman/makara: alt sinir = 0,31667 x (dis_cap - ic_cap) = 12,67 mm.
const RUL_RED = { ic_cap: 5, dis_cap: 45, genislik: 5, eleman: "makara", bosluk: 0.15, flans: "yok" };
const RUL_KAB = { ic_cap: 5, dis_cap: 45, genislik: 13, eleman: "makara", bosluk: 0.15, flans: "yok" };
const RUL_VAR = { ic_cap: 10, dis_cap: 30, genislik: 9, eleman: "bilya", bosluk: 0.15, flans: "yok" };
const VID_RED = { urun_tipi: "civata", cap: 3, boy: 20, tolerans: 0.2 };
const VID_KAB = { urun_tipi: "civata", cap: 6, boy: 20, tolerans: 0.2 };
const VID_PUL = { urun_tipi: "pul", cap: 3, boy: 20, tolerans: 0.2 };

// ---------------------------------------------------------------- mutant agaclari
// Mutant = kaynak dosyanin metin donusumu; DEPO DEGISMEZ, kopya isletim sistemi
// gecici dizinine yazilir. parametrik.js "../../jenerator/..." ile import ettigi icin
// gecici agac AYNI DERINLIGI korur.
const GECICI_KOK = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-kisit-"));
function mutantAgac(ad, donusum) {
  const dizin = path.join(GECICI_KOK, ad);
  fs.mkdirSync(path.join(dizin, "jenerator"), { recursive: true });
  fs.mkdirSync(path.join(dizin, "shop", "src"), { recursive: true });
  const ham = fs.readFileSync(path.join(KOK, "jenerator", "konfigurator.js"), "utf8");
  const yeni = donusum(ham);
  if (ad !== "M00-taban" && yeni === ham) {
    throw new Error("MUTASYON ETKISIZ (desen tutmadi): " + ad);
  }
  fs.writeFileSync(path.join(dizin, "jenerator", "konfigurator.js"), yeni);
  fs.copyFileSync(path.join(KOK, "jenerator", "hacim.js"), path.join(dizin, "jenerator", "hacim.js"));
  fs.copyFileSync(path.join(KOK, "shop", "src", "parametrik.js"),
                  path.join(dizin, "shop", "src", "parametrik.js"));
  return path.join(dizin, "shop", "src", "parametrik.js");
}
function temizle() {
  try { fs.rmSync(GECICI_KOK, { recursive: true, force: true }); } catch (e) { /* yok say */ }
}
process.on("exit", temizle);

// ---------------------------------------------------------------- iddia bataryasi
function batarya(PAR) {
  const iddialar = [];
  const iddia = (ad, gecti, olcum) => iddialar.push({ ad, gecti: !!gecti, olcum: String(olcum) });

  const hesap = (sema, parametreler) => {
    const kalem = { id: sema.id, malzeme: "PLA", renk: "Siyah", adet: 1,
                    parametreler, hacim_mm3: 1, parametrik_fiyat_kurus: 1 };
    try { return PAR.parametrikHesapla(kalem, SECENEK, sema); }
    catch (e) { return { hata: "ISTISNA:" + (e && e.message) }; }
  };
  const kurus = (r) => (r && r.birimKurus != null ? r.birimKurus : null);
  const ozet = (r) => (r.hata ? "hata=" + r.hata : "kurus=" + r.birimKurus);

  const rulman = semaKopya(S_RULMAN), vida = semaKopya(S_VIDA), kutu = semaKopya(S_KUTU);

  // --- allowlist GECICI acilir (BELLEKTE; secenekler.js DEGISMEZ) ---
  ALLOW.rulman = 0.0;
  ALLOW.vida = 0.0;

  const a1 = hesap(rulman, RUL_RED);
  iddia("A1 kisidin REDDETTIGI set (rulman/makara g=5 < 12,67) fiyat URETMEZ",
        kurus(a1) === null && a1.hata === "parametre-araligi", ozet(a1));
  const a2 = hesap(rulman, RUL_KAB);
  iddia("A2 KONTROL ayni ailede kisidin KABUL ettigi set (g=13) fiyat URETIR",
        kurus(a2) > 0, ozet(a2));
  const a3 = hesap(rulman, RUL_VAR);
  iddia("A3 KONTROL rulman varsayilan seti (bilya g=9) fiyat URETIR", kurus(a3) > 0, ozet(a3));
  const a4 = hesap(vida, VID_RED);
  iddia("A4 kisidin REDDETTIGI set (vida civata M3 < M5) fiyat URETMEZ",
        kurus(a4) === null && a4.hata === "parametre-araligi", ozet(a4));
  const a5 = hesap(vida, VID_KAB);
  iddia("A5 KONTROL vida civata M6 fiyat URETIR", kurus(a5) > 0, ozet(a5));
  const a6 = hesap(vida, VID_PUL);
  iddia("A6 KONTROL `eger` SECICIDIR — vida PUL M3'te kisit uygulanmaz, fiyat URETIR",
        kurus(a6) > 0, ozet(a6));
  const a7 = hesap(kutu, KONF.varsayilanDegerler(kutu));
  iddia("A7 KONTROL kisitsiz aile (kutu) etkilenmez, fiyat URETIR", kurus(a7) > 0, ozet(a7));

  // --- FAIL-CLOSED: kisit OKUNAMIYORSA fiyat URETILMEZ ---
  const fc = (ad, sema, degerler) => {
    const r = hesap(sema, degerler);
    iddia(ad, kurus(r) === null, ozet(r));
    return r;
  };
  const s1 = semaKopya(S_VIDA); s1.kisitlar = { 0: vida.kisitlar[0] };
  const f1 = fc("F1 FAIL-CLOSED `kisitlar` DIZI DEGIL -> fiyat YOK", s1, VID_RED);
  const s2 = semaKopya(S_VIDA); s2.kisitlar[0].min = "5";
  fc("F2 FAIL-CLOSED kisit `min` TANINMAYAN bicimde (metin) -> fiyat YOK", s2, VID_RED);
  const s3 = semaKopya(S_RULMAN); s3.kisitlar[0].min.terimler = { olmayan_parametre: 1 };
  fc("F3 FAIL-CLOSED `terimler` semada OLMAYAN parametreye bakiyor -> fiyat YOK", s3, RUL_RED);
  const s4 = semaKopya(S_VIDA); delete s4.kisitlar[0].parametre;
  fc("F4 FAIL-CLOSED kisit `parametre` alani YOK -> fiyat YOK", s4, VID_RED);
  const s5 = semaKopya(S_VIDA); s5.kisitlar[0] = "M5";
  fc("F5 FAIL-CLOSED kisit kaydi OBJE DEGIL -> fiyat YOK", s5, VID_RED);
  const s6 = semaKopya(S_VIDA); s6.kisitlar[0].parametre = "urun_tipi";
  fc("F6 FAIL-CLOSED kisit SAYISAL OLMAYAN parametreye baglanmis (kiyas NaN) -> fiyat YOK",
     s6, VID_RED);
  const s7 = semaKopya(S_RULMAN); s7.kisitlar[0].min.terimler.dis_cap = "0,3";
  fc("F7 FAIL-CLOSED `terimler` katsayisi SAYI DEGIL -> fiyat YOK", s7, RUL_RED);
  const s8 = semaKopya(S_VIDA); delete s8.parametreler;
  fc("F8 FAIL-CLOSED (mevcut kol) sema `parametreler` yok -> fiyat YOK", s8, VID_RED);
  const s10 = semaKopya(S_VIDA); s10.kisitlar[0].eger = "civata";
  fc("F10 FAIL-CLOSED `eger` bozuk (metin) — kayit hicbir sette uygulanmazdi -> fiyat YOK",
     s10, VID_RED);

  iddia("F9 TANISAL AYRIM: bicim hatasi `kisit-okunamadi` doner (`parametre-araligi` DEGIL)",
        f1.hata === "kisit-okunamadi", "hata=" + f1.hata);

  // --- MUSTERI METNI: worker'in DONDURDUGU kod index.html HATA_METNI'nde karsiligini
  //     bulmali. Kod UYDURULMAZ, yukaridaki olcumden (f1.hata) gelir; girdi yoksa musteri
  //     jenerik "Odeme baslatilamadi" gorur ve odemesi basarisiz sanir. Marka kurallari da
  //     olculur (baski/basim/3D ailesi + sehir adi YOK, WhatsApp yonlendirmesi VAR).
  const HTML = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
  const kod = f1.hata;
  const satir = new RegExp('"' + kod + '":\\s*"([^"]*)"').exec(HTML);
  const metin = satir ? satir[1] : "";
  const YASAK_MARKA = /(bask[ıi]|bas[ıi]m|3\s*-?\s*D)/i;
  const YASAK_SEHIR = /(Fethiye|Göcek|Muğla|Mugla)/i;
  const metinSorun = [];
  if (!satir) { metinSorun.push("HATA_METNI'nde '" + kod + "' anahtari YOK (jenerik metne duser)"); }
  if (satir && !/WhatsApp/.test(metin)) { metinSorun.push("musteriye ne yapacagini soylemiyor"); }
  if (YASAK_MARKA.test(metin)) { metinSorun.push("MARKA IHLALI: baski/basim/3D"); }
  if (YASAK_SEHIR.test(metin)) { metinSorun.push("MARKA IHLALI: sehir adi"); }
  if (metin && metin === (new RegExp('"parametre-araligi":\\s*"([^"]*)"').exec(HTML) || [])[1]) {
    metinSorun.push("`parametre-araligi` ile AYNI metin (tanisal ayrim yuzeye cikmiyor)");
  }
  iddia("F11 MUSTERI METNI: `" + kod + "` icin ozel metin VAR, marka-temiz, WhatsApp'a yonlendiriyor",
        metinSorun.length === 0,
        (satir ? '"' + metin + '"' : "GIRDI YOK") +
        (metinSorun.length ? " | " + metinSorun.join(" ; ") : ""));

  // --- REPO SEMALARI: kisitlar hem BICIMSEL hem DEGER duzeyinde okunabilir olmali
  //     (bozuk kural YAYINA CIKMAZ). Olcum, uretimde kosan fonksiyonun KENDISIYLE
  //     yapilir: varsayilan sette `__kisit` hatasi cikarsa kural okunamiyor demektir.
  const semaDosyalari = fs.readdirSync(SEMA_DIZIN).filter((f) => f.endsWith(".json")).sort();
  const taninmayan = [];
  let kisitKaydi = 0;
  semaDosyalari.forEach((f) => {
    const s = semaOku(f);
    if (s.kisitlar === undefined) { return; }
    if (!Array.isArray(s.kisitlar)) { taninmayan.push(s.id + ":dizi-degil"); return; }
    s.kisitlar.forEach((ks, i) => {
      kisitKaydi++;
      if (!KONF.kisitTanindiMi(ks)) { taninmayan.push(s.id + "#" + i + ":bicim"); }
    });
    // Deger duzeyi: her kisidin `eger` kolunu TETIKLEYEN bir set kurulur (varsayilan +
    // eger degerleri) ve alt sinirin gercekten hesaplanabildigi olculur.
    s.kisitlar.forEach((ks, i) => {
      if (!ks || typeof ks !== "object" || !ks.eger || typeof ks.eger !== "object") { return; }
      const d = Object.assign(KONF.varsayilanDegerler(s), ks.eger);
      const h = KONF.dogrula(s, d).hatalar || {};
      if (h[KONF.KISIT_ALANI]) { taninmayan.push(s.id + "#" + i + ":olculemedi"); }
    });
  });
  iddia("A8 REPO SEMALARI: her kisit kaydi OKUNABILIR (bicim + alt sinir hesaplanabilir)",
        taninmayan.length === 0,
        semaDosyalari.length + " sema / " + kisitKaydi + " kisit kaydi, okunamayan=" +
        (taninmayan.length ? taninmayan.join(",") : "0"));

  // --- SATISTAKI AILELER: varsayilan parametrede kurus imzasi (yanlis-pozitif kapisi) ---
  const imza = [];
  semaDosyalari.forEach((f) => {
    const s = semaOku(f);
    if (!ALLOW_ORJ.includes(s.hacimFormulu)) { return; }   // rulman/vida ORJINAL listede yok
    const r = hesap(s, KONF.varsayilanDegerler(s));
    imza.push(s.hacimFormulu + "=" + (r.hata ? "HATA:" + r.hata : r.birimKurus));
  });
  iddia("A9 SATISTAKI AILELER: hepsi varsayilan parametrede POZITIF kurus uretir",
        imza.length === ALLOW_ORJ.length && imza.every((x) => !x.includes("HATA")),
        imza.length + "/" + ALLOW_ORJ.length + " aile | " + imza.join(" "));

  // --- allowlist geri alinir ---
  delete ALLOW.rulman;
  delete ALLOW.vida;
  iddia("A10 BUTUNLUK: bellekteki gecici allowlist acmasi GERI ALINDI",
        JSON.stringify(Object.keys(ALLOW).slice().sort()) === JSON.stringify(ALLOW_ORJ),
        Object.keys(ALLOW).length + " aile");

  return { iddialar, imza: imza.join(" ") };
}

// ---------------------------------------------------------------- mutantlar
// OLDURUCU = kaldirilinca BELIRTILEN iddialarin KIRMIZI yanmasi SART (kol canli mi?).
// KONTROL  = kolu bozmayan degisiklik; HICBIR iddia kirmizi yanmamali (yanlis-pozitif kapisi).
const MUTANTLAR = [
  { ad: "M00-taban", sinif: "TABAN", bekle: [], d: (s) => s },
  { ad: "M01-kisit-dongusu-yok", sinif: "OLDURUCU", bekle: ["A1", "A4"],
    d: (s) => s.replace(/\n    for \(var k = 0; k < \(kisitlar \|\| \[\]\)\.length; k\+\+\) \{[\s\S]*?\n    \}\n(?=    return \{ gecerli)/, "\n") },
  { ad: "M02-dongu-hic-donmez", sinif: "OLDURUCU", bekle: ["A1", "A4"],
    d: (s) => s.replace("k < (kisitlar || []).length", "k < 0") },
  { ad: "M03-tolerans-sisirildi", sinif: "OLDURUCU", bekle: ["A1", "A4"],
    d: (s) => s.replace("var KISIT_TOLERANS = 1e-6;", "var KISIT_TOLERANS = 1e9;") },
  { ad: "M04-gecerli-false-silindi", sinif: "OLDURUCU", bekle: ["A1", "A4"],
    d: (s) => s.replace("        hatalar[ks.parametre] = kisitMesaji(ks, altSinir);\n        gecerli = false;",
                        "        hatalar[ks.parametre] = kisitMesaji(ks, altSinir);") },
  // YAPISAL tanima kolu — TEK BASINA yakaladigi eksen: bozuk `eger` (kayit hicbir sette
  // uygulanmazdi). Diger F iddialari OLCULEMEDI koluyla ORTAK, o yuzden burada iddia
  // EDILMEZ ([[beyan-edilmis-survivor]]: ayirt edici mutant yoksa eksen ayri iddia olmaz).
  { ad: "M05-tanima-daima-evet", sinif: "OLDURUCU", bekle: ["F10"],
    d: (s) => s.replace("  function kisitTanindiMi(ks) {",
                        "  function kisitTanindiMi(ks) {\n    if (ks) { return true; }") },
  { ad: "M06-dizi-degil-kolu-yok", sinif: "OLDURUCU", bekle: ["F1", "F9"],
    d: (s) => s.replace("kisitlar !== undefined && kisitlar !== null && !Array.isArray(kisitlar)",
                        "false") },
  // OLCULEMEDI kolu — TEK BASINA yakaladigi eksenler: alt sinir hesaplanamiyor (F3) ve
  // kiyas degeri NaN (F6). Ikisi de yapisal tanimayi GECEN kayitlardir.
  { ad: "M07-olculemedi-kolu-yok", sinif: "OLDURUCU", bekle: ["F3", "F6"],
    d: (s) => s.replace("      if (altSinir == null || isNaN(kv)) {", "      if (false) {") },
  { ad: "M09-mesaj-degisti", sinif: "KONTROL", bekle: [],
    d: (s) => s.replace('var m = ks.mesaj || "En az {min} olmalı";',
                        'var m = ks.mesaj || "ALAKASIZ MUTASYON";') },
  { ad: "M10-tolerans-daraldi", sinif: "KONTROL", bekle: [],
    d: (s) => s.replace("var KISIT_TOLERANS = 1e-6;", "var KISIT_TOLERANS = 1e-9;") },
  { ad: "M11-bicim-mesaji-degisti", sinif: "KONTROL", bekle: [],
    d: (s) => s.replace('var KISIT_BICIM_MESAJI = "Ürün kısıt tanımı okunamadı";',
                        'var KISIT_BICIM_MESAJI = "ALAKASIZ KONTROL METNI";') },
];

// ---------------------------------------------------------------- kosum
const cikti = [];
let rc = 0;

if (!KENDINI_TEST) {
  const PAR = await import(pathToFileURL(path.join(SHOP, "src", "parametrik.js")).href);
  const { iddialar, imza } = batarya(PAR);
  const kirmizi = iddialar.filter((i) => !i.gecti);
  iddialar.forEach((i) => cikti.push("  " + (i.gecti ? "✅" : "❌") + " " + i.ad + "  ->  " + i.olcum));
  cikti.push("");
  cikti.push("SATIS IMZASI: " + imza);
  cikti.push("IDDIA SAYISI: " + iddialar.length + " · KIRMIZI: " + kirmizi.length);
  rc = kirmizi.length ? 1 : 0;
} else {
  let toplamIddia = 0, tabanIddia = null, tabanImza = null, hataliMutant = 0;
  for (const m of MUTANTLAR) {
    const PAR = await import(pathToFileURL(mutantAgac(m.ad, m.d)).href);
    const { iddialar, imza } = batarya(PAR);
    toplamIddia += iddialar.length;
    if (tabanIddia === null) { tabanIddia = iddialar.length; tabanImza = imza; }
    const kirmizi = iddialar.filter((i) => !i.gecti).map((i) => i.ad.split(" ")[0]);
    const sorunlar = [];
    // ISARET SARTI: iddia SAYISI her mutantta ayni olmali (cokme kirmiziyla karisir).
    if (iddialar.length !== tabanIddia) {
      sorunlar.push("iddia sayisi kaydi " + iddialar.length + " != " + tabanIddia);
    }
    if (m.sinif === "TABAN" && kirmizi.length) { sorunlar.push("TABAN kirmizi: " + kirmizi.join(",")); }
    if (m.sinif === "KONTROL" && kirmizi.length) {
      sorunlar.push("KONTROL mutanti kirmizi yakti (yanlis-pozitif): " + kirmizi.join(","));
    }
    if (m.sinif === "OLDURUCU") {
      const eksik = m.bekle.filter((b) => !kirmizi.includes(b));
      if (eksik.length) { sorunlar.push("OLU IDDIA — kol bozuldu ama yesil kaldi: " + eksik.join(",")); }
    }
    // Satis imzasi HICBIR mutantta kaymamali: bu kol satistaki ailelere DOKUNMUYOR.
    if (imza !== tabanImza) { sorunlar.push("satis kurus imzasi kaydi"); }
    if (sorunlar.length) { hataliMutant++; rc = 1; }
    cikti.push((sorunlar.length ? "❌ " : "✅ ") + m.sinif.padEnd(8) + " " + m.ad.padEnd(28) +
               " KIRMIZI=[" + kirmizi.join(",") + "]" +
               (sorunlar.length ? "  <-- " + sorunlar.join(" ; ") : ""));
  }
  cikti.push("");
  cikti.push("SATIS IMZASI (tum mutantlarda AYNI): " + tabanImza);
  cikti.push("MUTANT SAYISI: " + MUTANTLAR.length +
             " (oldurucu " + MUTANTLAR.filter((m) => m.sinif === "OLDURUCU").length +
             " · kontrol " + MUTANTLAR.filter((m) => m.sinif === "KONTROL").length +
             " · taban 1) · BEYANINA UYMAYAN: " + hataliMutant);
  cikti.push("IDDIA SAYISI: " + tabanIddia + " (mutant basina, SABIT) · TOPLAM: " + toplamIddia);
}

const SHA_SON = shaHepsi();
if (SHA_BAS !== SHA_SON) {
  cikti.push("❌ KAYNAK BUTUNLUGU BOZULDU: " + SHA_BAS + "  ->  " + SHA_SON);
  rc = 1;
} else {
  cikti.push("KAYNAK BUTUNLUGU sha256 bas==son: EVET (" + SHA_BAS + ")");
}

console.log(cikti.join("\n"));
console.log(rc === 0 ? "✅ HEPSI GECTI" : "❌ KALDI");
process.exit(rc);
