#!/usr/bin/env node
/**
 * PRUVO shop — URETIM DOSYASI ADI: KARAKTER KUMESI EKSENI (birim testleri).
 *
 *   node shop/test/stl-dosya-adi.mjs
 *
 * NEDEN VAR (olculmus kalem, Okan bildirdi 2 Eyl): panel STL yukleyicisi Turkce
 * karakterli dosya adini REDDEDIYORDU — `shop/src/yonet.js` `STL_DOSYA_ADI_RX`
 * salt-ASCII idi, `i`(noktasiz)/`s`(cedilla)/`g`(yumusak) sinifin disinda kaliyordu.
 *
 * 🔴 BU BIR TEKIL YAMA DEGIL, SINIF TESTIDIR. Adin karakter kumesi ekseninde
 * BIRDEN COK okuyucu var; yalniz birini duzeltmek arizayi TASIR
 * ([[tuketici-yazilirken-tum-okuyucular-sayilir]]). Sayilan okuyucular:
 *   R1  stlDosyaAdiGecersiz  -> stlYukle + stlCikar   (yukleme/cikarma kapisi)
 *   R2  stlIndir "Savunma 1" -> indirme + R2 liste karsilastirmasi
 *   R3  URETIM_DOSYA_RX      -> uretim notundan dosya ADINI cikarir (panel etiketi)
 * R3 ASCII kalsaydi ad SESSIZCE KIRPILIRDI ("...kilavuz-ara.stl" -> "lavuz-ara.stl"),
 * yani panel YANLIS dosya adi gosterirdi; bu duzlemde yanlis dosya = pahali uretim
 * hatasi. O yuzden R3 de bu bataryada olculur.
 *
 * 🔴 NFC EKSENI: macOS dosya adlarini NFD verir (yumusak g = g + U+0306). Birlesik
 * isaret \p{M} sinifindadir, \p{L} DEGILDIR. Normalize edilmezse ayni ad hem
 * reddedilir hem de IKI FARKLI R2 anahtari uretir (yuklenen dosya listede
 * gorunmez). D vakalari tam bunu olcer.
 *
 * NEDEN wrangler'siz: olculen davranis SAF yuzeydedir; yonet.js'ten HAM KAYNAK
 * olarak dilimlenip vm'de kosturulur, KOPYA YAZILMAZ (kopya yazilsaydi kaynak
 * degistiginde test yesil kalir ve iddia sessizce olurdu — `uretim-kaynak.mjs`
 * ayni kararla ayni deseni tasiyor).
 *
 * ONCE-KIRMIZI KANITI: mutasyon surucusu `tools/stl-dosya-adi-mutasyon.py`
 * (gecici AYNAYA uygular; calisma agacina YAZMAZ). Mutantlarin hepsi OLDURULMELI.
 */

import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KAYNAK_YOL = process.env.PRUVO_YONET_KAYNAK || path.join(BURASI, "..", "src", "yonet.js");
const KAYNAK = fs.readFileSync(KAYNAK_YOL, "utf8");

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

/** Kaynaktan [baslangic, bitis) dilimi. Capalar bulunamazsa null (fail-loud). */
function dilimAl(metin, baslangic, bitis) {
  const b = metin.indexOf(baslangic);
  const s = b >= 0 ? metin.indexOf(bitis, b + baslangic.length) : -1;
  return (b >= 0 && s > b) ? metin.slice(b, s) : null;
}

function capaYoksaDus(dilim, ad) {
  if (dilim === null) {
    console.error("KAYNAK CAPASI BULUNAMADI (" + ad + ") — yonet.js yapisi degisti mi?");
    process.exit(3);
  }
  return dilim;
}

// ------------------------------------------------------------------ KAYNAK DILIMI
// R1, stlAdiNormal'i CAGIRIR -> ikisi AYNI baglama kurulur.
const normalizerKaynak = capaYoksaDus(
  dilimAl(KAYNAK, "const IZINLI_UZANTI =", "/** Urunun R2'deki parca dosyalari"),
  "IZINLI_UZANTI + stlAdiNormal");
const dogrulayiciKaynak = capaYoksaDus(
  dilimAl(KAYNAK, "const STL_DOSYA_ADI_RX =", "/** POST /yonet/stl-yukle"),
  "STL_DOSYA_ADI_RX + stlDosyaAdiGecersiz");
const notAyristiriciKaynak = capaYoksaDus(
  dilimAl(KAYNAK, "const URETIM_DOSYA_RX =", "\n"),
  "URETIM_DOSYA_RX");

// `const` bildirimleri vm baglaminin GLOBAL NESNESINE dusmez (yalniz `function`/`var`
// duser) — regex'i disari almak icin acikca yaziyoruz. Bu satirlar OLCULEN kaynagin
// PARCASI DEGIL, yalnizca kopru.
const KOPRU = "\nglobalThis.__URETIM_DOSYA_RX = URETIM_DOSYA_RX;" +
  "\nglobalThis.__STL_DOSYA_ADI_RX = STL_DOSYA_ADI_RX;\n";

const kutu = {};
vm.createContext(kutu);
vm.runInContext(normalizerKaynak + "\n" + dogrulayiciKaynak + "\n" + notAyristiriciKaynak + KOPRU,
  kutu, { filename: "yonet-stl-ad.js" });

const stlDosyaAdiGecersiz = kutu.stlDosyaAdiGecersiz;
const stlAdiNormal = kutu.stlAdiNormal;
const URETIM_DOSYA_RX = kutu.__URETIM_DOSYA_RX;

// 🔴 `instanceof RegExp` KULLANILMAZ: vm baglami AYRI bir realm'dir, oradaki RegExp
// bu realm'in RegExp'i DEGILDIR ve kontrol her zaman false doner (sahte "capa kaydi").
const regexMi = (x) => Object.prototype.toString.call(x) === "[object RegExp]";

if (typeof stlDosyaAdiGecersiz !== "function" || typeof stlAdiNormal !== "function" ||
    !regexMi(URETIM_DOSYA_RX)) {
  console.error("DILIM KOSTU AMA SEMBOLLER GELMEDI — capalar kaydi mi?");
  process.exit(3);
}

const gecerli = (ad) => stlDosyaAdiGecersiz(ad) === false;

// Turkce harfler BILEREK kod noktasiyla yazildi: bu dosyanin kendi kodlamasi bozulsa
// bile vaka NE OLCTUGUNU kaybetmesin (ve NFC/NFD ayrimi gozle gorunur olsun).
const I_NOKTASIZ = "ı";        // i (noktasiz)
const G_YUMUSAK_NFC = "ğ";     // g (yumusak) — TEK kod noktasi
const G_YUMUSAK_NFD = "ğ";    // g + COMBINING BREVE — macOS'un verdigi bicim
const S_CEDILLA = "ş";         // s (cedilla)
const S_BUYUK_CEDILLA = "Ş";   // S (cedilla)

console.log("\nA) POZITIF — Turkce/Unicode ad GECMELI");
{
  const okanVakasi = "crf-zincir-k" + I_NOKTASIZ + "lavuz-ara.STL";
  ol("A1 Okan'in bildirdigi ad gecer: " + okanVakasi, gecerli(okanVakasi));
  ol("A2 NFC Turkce ad gecer (yumusak g + noktasiz i)",
    gecerli("ba" + G_YUMUSAK_NFC + "lant" + I_NOKTASIZ + "-braketi.stl"));
  ol("A3 bosluk + buyuk Turkce harf gecer",
    gecerli(S_BUYUK_CEDILLA + "aft K" + I_NOKTASIZ + "lavuzu 2.3mf"));
  ol("A4 alt cizgi + cedillali s gecer", gecerli("di" + S_CEDILLA + "li_alt_cizgi.stl"));
  ol("A5 REGRESYON: duz ASCII ad hala gecer", gecerli("pruvo-braket-v2.stl"));
  ol("A6 REGRESYON: .3mf uzantisi hala gecer", gecerli("kapak.3mf"));
  ol("A7 REGRESYON: buyuk harfli uzanti (.STL) hala gecer", gecerli("KAPAK.STL"));
  ol("A8 tavan sinirindaki Turkce ad gecer (181 karakter)",
    gecerli("a".repeat(173) + I_NOKTASIZ.repeat(4) + ".stl"));
}

console.log("\nB) NEGATIF — SAVUNMA DARALMADI (alfabe genisledi, kapi genislemedi)");
{
  const red = (ad, etiket) => ol(etiket, stlDosyaAdiGecersiz(ad) === true, "KABUL EDILDI");
  red("../gizli.stl", "B1 ust-dizin (..) REDDEDILIR");
  red("alt/dizin.stl", "B2 ayirac (/) REDDEDILIR");
  red("alt\\dizin.stl", "B3 ters ayirac REDDEDILIR");
  red("k" + I_NOKTASIZ + "d/../../gizli.stl", "B4 Turkce harfli traversal REDDEDILIR");
  red(".gizli.stl", "B5 bastaki nokta REDDEDILIR");
  red("-basta-tire.stl", "B6 bastaki tire REDDEDILIR");
  red(" bosluk.stl", "B7 bastaki bosluk REDDEDILIR");
  red("dosya.txt", "B8 uzanti disi (.txt) REDDEDILIR");
  red("dosya.stl.exe", "B9 uzanti sonda degil (.stl.exe) REDDEDILIR");
  red("dosya\"tirnak.stl", "B10 cift tirnak REDDEDILIR (Content-Disposition ekseni)");
  red("dosya\nsatir.stl", "B11 satir sonu REDDEDILIR");
  red("dosya\u0000bos.stl", "B12 NUL REDDEDILIR");
  red("dosya%2e%2e.stl", "B13 yuzde (kodlanmis traversal) REDDEDILIR");
  red("dosya:kolon.stl", "B14 iki nokta REDDEDILIR");
  red("dosya?sorgu.stl", "B15 soru isareti REDDEDILIR");
  red("", "B16 bos ad REDDEDILIR");
  red("a".repeat(200) + ".stl", "B17 tavan asan ad (200+) REDDEDILIR");
  red("\u0306baslangicta-birlesik.stl", "B18 birlesik isaretle BASLAYAN ad REDDEDILIR");
  red("dosya{suslu}.stl", "B19 susli parantez REDDEDILIR (`u` bayragi dusmus mu?)");
  red("dosya\u0007zil.stl", "B20 kontrol karakteri (BEL) REDDEDILIR");
}

console.log("\nC) R3 — NOT AYRISTIRICI ADI KIRPMAZ (yanlis dosya adi = pahali uretim hatasi)");
{
  const cikar = (metin) => {
    const rx = new RegExp(URETIM_DOSYA_RX.source, URETIM_DOSYA_RX.flags);
    const bulunan = [];
    let m;
    while ((m = rx.exec(metin)) !== null) { bulunan.push(m[1]); }
    return bulunan;
  };
  const ad = "crf-zincir-k" + I_NOKTASIZ + "lavuz-ara.stl";
  const c1 = cikar("KANONIK " + ad + " Drive file Id: abcdefghijklmnop");
  ol("C1 Turkce adin TAMAMI cikar (kirpilmaz): " + JSON.stringify(c1),
    c1.length === 1 && c1[0] === ad, "beklenen [" + ad + "]");
  ol("C2 KIRPMA IZI YOK — 'lavuz-ara.stl' parcasi TEK BASINA donmez",
    !c1.includes("lavuz-ara.stl"));
  const c3 = cikar("YEDEK pruvo-braket-v2.stl");
  ol("C3 REGRESYON: ASCII ad hala cikar", c3.length === 1 && c3[0] === "pruvo-braket-v2.stl");
  const c4 = cikar("notta hic uretim dosyasi yok, yalniz metin");
  ol("C4 REGRESYON: eslesme yoksa bos liste", c4.length === 0);
}

console.log("\nD) NFC EKSENI — AYNI AD, TEK ANAHTAR (macOS NFD tuzagi)");
{
  const nfc = "ba" + G_YUMUSAK_NFC + "lant" + I_NOKTASIZ + ".stl";
  const nfd = "ba" + G_YUMUSAK_NFD + "lant" + I_NOKTASIZ + ".stl";
  ol("D0 vaka gercekten NFD (ham dizgeler FARKLI)", nfc !== nfd,
    "fikstur cokmus — iki vaka ayni dizge");
  ol("D1 NFD ad (macOS'un verdigi bicim) KABUL EDILIR", gecerli(nfd));
  ol("D2 NFD ile NFC AYNI kanonik ada duser (tek R2 anahtari)",
    stlAdiNormal(nfd) === stlAdiNormal(nfc),
    JSON.stringify(stlAdiNormal(nfd)) + " != " + JSON.stringify(stlAdiNormal(nfc)));
  ol("D3 normalize idempotent (iki kez uygulamak degistirmez)",
    stlAdiNormal(stlAdiNormal(nfd)) === stlAdiNormal(nfd));
  ol("D4 dizge olmayan girdi bos ada duser (tip savunmasi)",
    stlAdiNormal(null) === "" && stlAdiNormal(undefined) === "" && stlAdiNormal(7) === "");
}

console.log("\nF) SINIFIN KENDISI — katman maskesi olmadan (mutant M-B3 buradan olur)");
{
  // 🔴 NEDEN AYRI BOLUM: `stlDosyaAdiGecersiz` ayirac icin AYRICA `includes("/")`
  // bakar. Bu KATMAN iyi bir savunma ama regex'in KENDISI bozuldugunda (or. `/`
  // sinifa eklendiginde) fonksiyon YINE red verir -> mutant SESSIZCE KACAR. Olculdu
  // (3 Eyl, once-kirmizi kosumu): sinifa `/` eklenmis mutant 42/0 YESIL geciyordu.
  // Burada sinif DOGRUDAN sinanir; boylece "alfabe genisledi" ile "kapi genisledi"
  // ayri ayri olculur ([[artik-yuzey-mutant-dedektorunu-korlestirir]]).
  const RX = kutu.__STL_DOSYA_ADI_RX;
  if (!regexMi(RX)) {
    console.error("STL_DOSYA_ADI_RX KOPRUDEN GELMEDI — capa kaydi mi?");
    process.exit(3);
  }
  const rxRed = (ad, etiket) => ol(etiket, RX.test(ad) === false, "SINIF KABUL ETTI");
  rxRed("alt/dizin.stl", "F1 SINIF ayiraci (/) KAPSAMAZ");
  rxRed("alt\\dizin.stl", "F2 SINIF ters ayiraci KAPSAMAZ");
  rxRed("dosya:kolon.stl", "F3 SINIF iki noktayi KAPSAMAZ");
  rxRed("dosya%2e.stl", "F4 SINIF yuzdeyi KAPSAMAZ");
  rxRed("dosya\u0000bos.stl", "F5 SINIF NUL'u KAPSAMAZ");
  rxRed("dosya?sorgu.stl", "F6 SINIF soru isaretini KAPSAMAZ");
  rxRed("dosya#capa.stl", "F7 SINIF diyezi KAPSAMAZ");
  rxRed(".gizli.stl", "F8 SINIF bastaki noktayi KAPSAMAZ (bas capasi duruyor)");
  ol("F9 SINIF Turkce harfi KAPSAR (alfabe gercekten genis)",
    RX.test("k" + I_NOKTASIZ + "lavuz.stl") === true);
  ol("F10 SINIF `u` bayragi tasir (kod-noktasi kipi)", RX.flags.includes("u"));
}

console.log("\nE) OKUYUCU ENVANTERI — normalizasyon TUM giris noktalarinda duruyor mu?");
{
  // Kaynak-duzeyi invaryant: bir giris noktasi normalizasyonu birakirsa yukleme (NFC)
  // ile indirme (ham) AYRISIR ve dosya "yuklendi ama listede yok" olur. Bu iddia
  // davranisla olculemez (canli R2 baglantisi ister), kaynakla olculur.
  const girisler = [
    ["stlIndir", '  const dosyaParam = stlAdiNormal(url.searchParams.get("dosya") || "");'],
    ["stlYukle", '  const dosya = stlAdiNormal(url.searchParams.get("dosya") || "");'],
    ["stlCikar", '  const dosya = stlAdiNormal(typeof (govde && govde.dosya) === "string"'],
    ["stlDosyaAdiGecersiz", "  const dosya = stlAdiNormal(ham);"],
  ];
  for (const [ad, capa] of girisler) {
    ol("E:" + ad + " adi kanonik bicime cevirerek okuyor", KAYNAK.includes(capa),
      "capa kaynakta YOK: " + capa);
  }
  // Anahtar, DOGRULANAN ad uzerinden kurulmali (dogrulanan dizge = yazilan dizge).
  ol("E:anahtar dogrulanan addan kurulur",
    KAYNAK.includes('const anahtar = "stl/" + uid + "/" + dosya;'));
}

console.log("\n----------------------------------------------------------------------");
console.log("SONUC: gecen=" + gecen + " kalan=" + kalan);
if (kalan > 0) {
  console.log("🔴 KIRMIZI — dosya adi ekseni tutmuyor.");
  process.exit(1);
}
console.log("✅ YESIL — Unicode ad gecer, savunma daralmadi, kanonik bicim tek.");
process.exit(0);
