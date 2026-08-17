#!/usr/bin/env node
"use strict";
// ============================================================================
// MARKA SORGUSU — CANLI JS YÜKLEM TESTİ  (node tools/marka-sorgusu-js-test.js)
// ----------------------------------------------------------------------------
// NEDEN VAR (ölçüldü, 17 Ağu 2026 — K133 kabul kırmızısı): marka çipi ile marka
// sayfası aynı gövdeden (`markaSorgusuEsler`) beslensin diye index.html'de DÖRT
// çağrı noktası değiştirildi, ama bu değişikliği ÖLÇEN hiçbir test yoktu. Kardeş
// testler (marka-limit-test.js, marka-uyelik-test.py) yüklemi KENDİ İÇİNE
// KOPYALIYOR: index.html'deki gövde bozulsa da onlar YEŞİL kalır. Yani mutantlar
// (`:4389` ham üyeliğe geri döndürüldü · uzun-önce kuralı etkisizleştirildi)
// hayatta kalıyordu — "kabul = çalıştırılabilir test" ilkesi fiilen boştu.
//
// NASIL ÖLÇER — KOPYA MANTIK YOK: index.html'in KENDİ kaynağından `norm()`
// başlangıcı ile `--- MARKA SORGUSU SON ---` marker'ı arasındaki blok AYIKLANIR
// ve node `vm`'inde GERÇEKTEN koşturulur. İddialar o gerçek fonksiyonlara sorulur.
// Blok bulunamazsa "yeşil" DENMEZ → OLCULEMEDI + exit 2 (fail-loud).
//
// NE KİLİTLER (her madde POZİTİF + NEGATİF):
//   A. BAŞLIK KOLU (poz): `marka[]` üyeliği OLMAYAN ama başlığında markayı TAM
//      KELİME anan ürün, o markanın sorgusunda ÇIKAR. (K133 tabanı: `Rover` 0/82,
//      `V-Strom` 0/19 — müşteri çipe basınca ürünü kaybediyordu.)
//   B. UZUN-ÖNCE (neg): "Land Rover ..." başlıklı ürün, tekil `Rover` sorgusuna
//      SIZMAZ — bigram tutunca tekil marka ÜRETİLMEZ (5 Ağu: kuralsız 80 kalem sızar).
//   C. ÜYELİK KOLU (poz/neg): `marka[]` üyeliği tek başına yeter; ilgisiz ürün
//      hiçbir kolla eşleşmez (fail-closed yön korunur).
//   D. TEK GÖVDE İNVARYANTI (kaynak ekseni): marka süzme yollarında HAM
//      `markaUyeMi(` çağrısı KALMAZ — tek meşru çağrı `markaSorgusuEsler` gövdesinin
//      İÇİNDEDİR. Biri bir çağrı noktasını ham üyeliğe geri döndürürse test KIRMIZI.
//
// Çalıştır:  node tools/marka-sorgusu-js-test.js     (0 geçti · 1 kaldı · 2 ölçülemedi)
// Mutasyon kanıtı: node tools/marka-sorgusu-js-mutasyon.js
// ============================================================================
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.dirname(__dirname);
const INDEX = process.env.PRUVO_INDEX_YOLU || path.join(ROOT, "index.html");

const FAILS = [];

function kontrol(ad, kosul) {
  if (kosul) {
    console.log("  PASS  " + ad);
  } else {
    FAILS.push(ad);
    console.log("  FAIL  " + ad);
  }
}

function olculemedi(sebep) {
  console.log("\nSONUC: OLCULEMEDI ❓  " + sebep);
  process.exit(2);
}

// --- 1) BLOĞU AYIKLA (kopya tutulmaz; kaynak index.html'in kendisidir) --------
if (!fs.existsSync(INDEX)) {
  olculemedi("index.html bulunamadi: " + INDEX);
}
const satirlar = fs.readFileSync(INDEX, "utf8").split("\n");

const basAdaylari = [];
const sonAdaylari = [];
satirlar.forEach(function (s, i) {
  if (/^\s*function norm\(/.test(s)) { basAdaylari.push(i); }
  if (s.indexOf("--- MARKA SORGUSU SON ---") !== -1) { sonAdaylari.push(i); }
});
if (basAdaylari.length !== 1) {
  olculemedi("`function norm(` capasi " + basAdaylari.length + " kez gecti (tam 1 bekleniyor)");
}
if (sonAdaylari.length !== 1) {
  olculemedi("`--- MARKA SORGUSU SON ---` marker'i " + sonAdaylari.length + " kez gecti (tam 1 bekleniyor)");
}
const bas = basAdaylari[0];
const son = sonAdaylari[0];
if (son <= bas) {
  olculemedi("marker sirasi bozuk: bas=" + (bas + 1) + " son=" + (son + 1));
}
const blok = satirlar.slice(bas, son + 1).join("\n");

// --- 2) GERÇEK KOŞTUR (stub yalnız blok DIŞI bagimliliklar icin) -------------
// cipIndeks(): index.html'de window.PRUVO_CIP_INDEKS'ten okur. Testte fikstür
// indeksi veririz — çip evreni markaları (TANINMIS listede olmayanlar) da ölçülsün.
const FIKSTUR_CIP_INDEKS = { kat: { Marin: { Sierra: 3, Teleflex: 2 } } };
const kutu = {
  console: console,
  cipIndeks: function () { return FIKSTUR_CIP_INDEKS; },
  window: {},
  document: { getElementById: function () { return null; } }
};
try {
  vm.runInNewContext(blok, kutu, { filename: "index.html#marka-sorgusu", timeout: 5000 });
} catch (e) {
  olculemedi("ayiklanan blok kosturulamadi: " + e.message);
}
const esler = kutu.markaSorgusuEsler;
const uyeMi = kutu.markaUyeMi;
const katla = kutu.markaKatla;
if (typeof esler !== "function" || typeof uyeMi !== "function" || typeof katla !== "function") {
  olculemedi("markaSorgusuEsler / markaUyeMi / markaKatla ayiklanan blokta tanimli degil");
}

// --- 3) İDDİALAR — gerçek gövdeye sorulur ------------------------------------
console.log("MARKA SORGUSU — CANLI JS YUKLEM TESTI");
console.log("  kaynak: " + INDEX + " (satir " + (bas + 1) + "-" + (son + 1) + ")");

function urun(o) { return Object.assign({ marka: [], baslik: "", aciklama: "" }, o); }

// A. BAŞLIK KOLU — üyelik YOK, başlıkta tam kelime VAR → EŞLEŞİR
kontrol("A1 uyeliksiz ama baslikta tam kelime → eslesir (Rover 0/82 sinifi)",
  esler(urun({ baslik: "Rover 75 Bagaj Kilit Kolu" }), katla("Rover")) === true);
kontrol("A2 uyeliksiz, baslikta ALT-DIZE (tam kelime DEGIL) → eslesMEZ",
  esler(urun({ baslik: "Roverline muhafaza plakasi" }), katla("Rover")) === false);
kontrol("A3 baslik kolu cip evreni markasinda da calisir (Sierra)",
  esler(urun({ baslik: "Sierra kablo baglanti pulu" }), katla("Sierra")) === true);

// B. UZUN-ÖNCE — bigram tutunca tekil marka ÜRETİLMEZ
kontrol("B1 'Land Rover ...' basligi tekil Rover sorgusuna SIZMAZ",
  esler(urun({ baslik: "Land Rover Discovery Kapi Kolu" }), katla("Rover")) === false);
kontrol("B2 ayni urun KENDI markasinin sorgusunda CIKAR (Land Rover)",
  esler(urun({ baslik: "Land Rover Discovery Kapi Kolu" }), katla("Land Rover")) === true);

// C. ÜYELİK KOLU + fail-closed
kontrol("C1 uyelik tek basina yeter (baslikta marka gecmese de)",
  esler(urun({ marka: ["Land Rover"], baslik: "Disc 3 kapi kolu" }), katla("Land Rover")) === true);
kontrol("C2 uyelik onek kuralindan katlanir ('Volvo Penta' urunu → Volvo)",
  esler(urun({ marka: ["Volvo Penta"], baslik: "Deniz motoru rakoru" }), katla("Volvo")) === true);
kontrol("C3 ilgisiz urun hicbir kolla eslesMEZ",
  esler(urun({ marka: ["Bosch"], baslik: "Jant kapagi klipsi" }), katla("Rover")) === false);

// D. TEK GÖVDE İNVARYANTI — süzme yollarında ham `markaUyeMi(` kalmaz
// Meşru geçiş yerleri: tanım satırı + `markaSorgusuEsler` gövdesindeki TEK çağrı.
const hamCagrilar = [];
satirlar.forEach(function (s, i) {
  if (s.indexOf("markaUyeMi(") === -1) { return; }
  if (/^\s*function markaUyeMi\(/.test(s)) { return; }          // tanım
  if (s.indexOf("return markaUyeMi(p, hedefMarka) ||") !== -1) { return; } // tek gövde
  if (/^\s*\/\//.test(s)) { return; }                             // yorum
  hamCagrilar.push((i + 1) + ": " + s.trim());
});
kontrol("D1 suzme yollarinda HAM markaUyeMi cagrisi YOK (bulunan: " +
  hamCagrilar.length + (hamCagrilar.length ? " → " + hamCagrilar.join(" | ") : "") + ")",
  hamCagrilar.length === 0);

// D2: dört çağrı noktasının hepsi tek gövdeden geçiyor mu (pozitif sayaç)
let govdeCagri = 0;
satirlar.forEach(function (s) {
  if (/^\s*\/\//.test(s)) { return; }
  if (/^\s*function markaSorgusuEsler\(/.test(s)) { return; }
  if (s.indexOf("markaSorgusuEsler(") !== -1) { govdeCagri += 1; }
});
kontrol("D2 markaSorgusuEsler cagri noktasi >= 4 (olculen: " + govdeCagri + ")", govdeCagri >= 4);

// --- 4) HÜKÜM ---------------------------------------------------------------
console.log("");
console.log("GECEN=" + (10 - FAILS.length) + "/10  HAM_UYELIK_CAGRISI=" + hamCagrilar.length +
  "  GOVDE_CAGRI=" + govdeCagri);
if (FAILS.length) {
  console.log("SONUC: KALDI ❌  (" + FAILS.length + ")");
  FAILS.forEach(function (f) { console.log("  - " + f); });
  process.exit(1);
}
console.log("SONUC: GECTI ✅");
process.exit(0);
