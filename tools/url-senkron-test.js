#!/usr/bin/env node
/**
 * URL SENKRON TESTİ — kategori/marka/arama değişince URL paramları görünümle
 * senkron mu? (Okan, 17 Tem: "Tümü"ye basınca URL temizlenmiyordu, yenileyince
 * eski marka/kategori geri geliyordu.)
 *
 *   node tools/url-senkron-test.js
 *
 * İKİ KATMAN:
 *  1) DAVRANIŞ: index.html'deki syncUrl() fonksiyonu ayıklanıp sahte
 *     history/location ile çalıştırılır — ürettiği URL sözleşmesi sınanır.
 *  2) KABLOLAMA: syncUrl'un dört tetik noktasına (kategori tıkı, marka çipi,
 *     arama yazımı, arama temizleme) gerçekten bağlı olduğu ve kategori
 *     "Tümü"nün TAM SIFIRLAMA yaptığı (marka + arama + URL temiz) statik
 *     olarak doğrulanır. (Bu repo'da DOM test kütüphanesi yok — tarayıcı
 *     adımlı kanıt mühendis raporunda; bu test regresyon bekçisidir.)
 */

const fs = require("fs");
const path = require("path");
const { gorunurKategoriOneki } = require("./ortak-index-esleme.js");

const INDEX = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

let hata = 0;
let toplam = 0;
function kontrol(ad, kosul, detay) {
  toplam++;
  if (kosul) { console.log("  ✅ " + ad); }
  else { hata++; console.log("  ❌ " + ad + (detay ? "  → " + detay : "")); }
}

/* ── 1) DAVRANIŞ: syncUrl'u ayıkla, sahte ortamda çalıştır ─────────────── */
console.log("1) syncUrl davranışı (ayıklanmış fonksiyon, sahte history/location)");
const m = INDEX.match(/function syncUrl\(\)\{[\s\S]*?\n  \}/);
kontrol("index.html'de syncUrl() tanımlı", !!m);

/* 🔴 syncUrl 11 Ağu'da GÖRÜNEN kategori etiketine uzandı (iç seri adı adres çubuğunda
   görünmesin diye): `?kategori=` artık gorunurKategori(activeCat) yazıyor. Bağımlılık
   STUB'LANMAZ — index.html'deki GERÇEK tablo + fonksiyon ayıklanıp sandbox gövdesinin
   başına konur; böylece bu test eşlemenin kendisini de ölçer (stub olsaydı eşleme
   bozulunca yeşil kalırdı). Ayıklanamazsa FAIL-CLOSED kırmızı.
   Çapa ORTAK kaynaktan gelir (tools/ortak-index-esleme.js): AYNI ayıklama kardeş test
   tools/reklam-url-test.js'te de gerekiyor ve aynı gün orada da ReferenceError'la
   çöktü — ikinci kopya tutulmaz. */
const ONEK_HAM = gorunurKategoriOneki(INDEX);
kontrol("index.html'den KATEGORI_GORUNUR + gorunurKategori ayıklandı", ONEK_HAM !== null);
const ONEK = ONEK_HAM === null ? "" : ONEK_HAM;

if (m) {
  // activeCat/activeAlt/activeBrand/query + history/location kapalı değişkenlerini sararak
  // çalıştır. 🔴 Sandbox'ın sağladığı değişken kümesi index.html'deki syncUrl gövdesiyle
  // AYRIŞABİLİR (ölçüldü: alt kategori çipi eklendiğinde syncUrl `activeAlt`e uzandı, bu
  // harness onu tanımıyordu → ham ReferenceError ile ÇÖKTÜ). Çökme, kırmızı iddiadan ayırt
  // edilemez; bu yüzden çağrı sarılır ve eksik değişken ADIYLA kırmızı bir iddia olur.
  let harnessHatasi = null;
  function urlUret(kat, marka, ara, alt, model) {
    let sonUrl = null;
    const sandbox = new Function(
      "activeCat", "activeAlt", "activeBrand", "activeModel", "query", "history", "location",
      "URLSearchParams",
      ONEK + m[0] + "; syncUrl();"
    );
    try {
      sandbox(kat, alt === undefined ? "Tümü" : alt, marka,
        model === undefined ? "Tümü" : model, ara,
        { replaceState: (a, b, url) => { sonUrl = url; } },
        { pathname: "/" }, URLSearchParams);
    } catch (e) {
      if (harnessHatasi === null) harnessHatasi = String(e && e.message ? e.message : e);
      return "<HARNESS HATASI: " + harnessHatasi + ">";
    }
    return sonUrl;
  }
  kontrol('hepsi "Tümü"+boş arama → URL param TAŞIMAZ (salt pathname)',
    urlUret("Tümü", "Tümü", "") === "/", "çıktı: " + urlUret("Tümü", "Tümü", ""));
  kontrol("kategori seçili → ?kategori= yazılır",
    urlUret("Marin", "Tümü", "") === "/?kategori=Marin",
    "çıktı: " + urlUret("Marin", "Tümü", ""));
  kontrol("kategori+marka → ikisi de yazılır",
    urlUret("Marin", "Beneteau", "") === "/?kategori=Marin&marka=Beneteau",
    "çıktı: " + urlUret("Marin", "Beneteau", ""));
  kontrol('marka "Tümü" → marka paramı DÜŞER, kategori KALIR',
    urlUret("Marin", "Tümü", "") === "/?kategori=Marin");
  kontrol("arama → ?ara= yazılır (kırpılmış)",
    urlUret("Tümü", "Tümü", "  jant  ") === "/?ara=jant",
    "çıktı: " + urlUret("Tümü", "Tümü", "  jant  "));

  // alt kategori çipi (grup filtresi) — syncUrl'un dördüncü ekseni
  kontrol("alt kategori seçili → ?altkategori= yazılır (kategoriyle birlikte)",
    urlUret("Marin", "Tümü", "", "Bujiler") === "/?kategori=Marin&altkategori=Bujiler",
    "çıktı: " + urlUret("Marin", "Tümü", "", "Bujiler"));
  kontrol('alt kategori "Tümü" → altkategori paramı DÜŞER, kategori KALIR',
    urlUret("Marin", "Tümü", "", "Tümü") === "/?kategori=Marin",
    "çıktı: " + urlUret("Marin", "Tümü", "", "Tümü"));
  kontrol("alt kategori + marka + arama birlikte yazılır",
    urlUret("Marin", "Beneteau", "jant", "Bujiler") ===
      "/?kategori=Marin&altkategori=Bujiler&marka=Beneteau&ara=jant",
    "çıktı: " + urlUret("Marin", "Beneteau", "jant", "Bujiler"));

  // model çipi (marka İÇİNDEKİ daraltma) — syncUrl'un beşinci ekseni
  kontrol("model seçili → ?model= yazılır (markayla birlikte)",
    urlUret("Otomobil", "BMW", "", "Tümü", "E46") === "/?kategori=Otomobil&marka=BMW&model=E46",
    "çıktı: " + urlUret("Otomobil", "BMW", "", "Tümü", "E46"));
  kontrol('model "Tümü" → model paramı DÜŞER, marka KALIR',
    urlUret("Otomobil", "BMW", "", "Tümü", "Tümü") === "/?kategori=Otomobil&marka=BMW",
    "çıktı: " + urlUret("Otomobil", "BMW", "", "Tümü", "Tümü"));
  kontrol("beş eksen birlikte yazılır (kategori+grup+marka+model+arama)",
    urlUret("Otomobil", "BMW", "jant", "Aydınlatma", "E46") ===
      "/?kategori=Otomobil&altkategori=Ayd%C4%B1nlatma&marka=BMW&model=E46&ara=jant",
    "çıktı: " + urlUret("Otomobil", "BMW", "jant", "Aydınlatma", "E46"));

  // ÇÖKME ≠ KIRMIZI: harness eksik değişkenle patladıysa bunu ADIYLA söyle
  kontrol("harness sağlam (syncUrl'un kapalı değişkenleri sandbox'ta tanımlı)",
    harnessHatasi === null,
    harnessHatasi === null ? "" :
      "syncUrl sahte ortamda çalışmadı → " + harnessHatasi +
      "  (index.html'de syncUrl yeni bir dış değişkene uzandı; bu testteki " +
      "new Function(...) parametre listesine ve urlUret'e ekle)");
}

/* ── 2) KABLOLAMA: tetik noktaları syncUrl çağırıyor mu? ───────────────── */
console.log("2) kablolama (statik — handler'lar syncUrl'a bağlı mı?)");

// marka çipi onclick bloğu: gövdesinde "activeBrand = m;" ataması geçen b.onclick
// fonksiyonu syncUrl() içermeli. (Blok artık atamadan ÖNCE model sıfırlaması da taşıyor —
// çapraz daralma paketi, 2 Ağu; çapa bu yüzden "başlayan" değil "içeren" olarak ölçülür.)
const cipSatir = INDEX.match(/b\.onclick = function\(\)\{[\s\S]*?activeBrand = m;[\s\S]*?\n\s*\};/);
kontrol("marka çipi tıkı syncUrl çağırıyor",
  cipSatir && cipSatir[0].indexOf("syncUrl()") !== -1);
kontrol("marka çipi tıkı seçili MODELİ düşürüyor (marka değişince model geçersiz)",
  cipSatir && /activeModel = "Tümü"/.test(cipSatir[0]));

// kategori onclick bloğu: activeCat = c; ile renderCats arasında
const katBlok = INDEX.match(/activeCat = c;[\s\S]*?renderCats\(\);/);
kontrol("kategori tıkı syncUrl çağırıyor",
  katBlok && katBlok[0].indexOf("syncUrl()") !== -1);
kontrol('kategori "Tümü" TAM SIFIRLAMA: markayı sıfırlıyor',
  katBlok && /c === "Tümü"[\s\S]*?activeBrand = "Tümü"/.test(katBlok[0]));
kontrol('kategori "Tümü" TAM SIFIRLAMA: modeli sıfırlıyor',
  katBlok && /c === "Tümü"[\s\S]*?activeModel = "Tümü"/.test(katBlok[0]));
kontrol('kategori "Tümü" TAM SIFIRLAMA: arama kutusunu/query temizliyor',
  katBlok && /c === "Tümü"[\s\S]*?query = ""/.test(katBlok[0]) &&
  /c === "Tümü"[\s\S]*?searchEl\.value = ""/.test(katBlok[0]));
kontrol('kategori "Tümü" sayfa başına dönüyor (scrollTo)',
  katBlok && /c === "Tümü"[\s\S]*?scrollTo/.test(katBlok[0]));

// arama input handler'ı (searchEl.addEventListener("input", ...) bloğu)
const araBlok = INDEX.match(/searchEl\.addEventListener\("input"[\s\S]*?\}\);/);
kontrol("arama yazımı URL'yi senkronluyor (syncUrl)",
  araBlok && araBlok[0].indexOf("syncUrl") !== -1);

// arama temizleme (clearEl.onclick bloğu)
const temizBlok = INDEX.match(/clearEl\.onclick = function\(\)\{[\s\S]*?\};/);
kontrol("arama temizleme URL'yi senkronluyor (syncUrl)",
  temizBlok && temizBlok[0].indexOf("syncUrl") !== -1);

/* ── 3) YUKARI ÇIK OKU: eleman + davranış + FAB çakışma önlemi ─────────── */
console.log("3) yukarı çık oku");
kontrol("topBtn elemanı var", /id="topBtn"/.test(INDEX));
kontrol("kaydırma eşiğiyle görünürlük (scroll dinleyici + show sınıfı)",
  /addEventListener\("scroll"[\s\S]{0,200}topBtn/.test(INDEX) ||
  /topBtn[\s\S]{0,300}addEventListener\("scroll"/.test(INDEX));
kontrol("tıklayınca yumuşak kaydırmayla başa dönüş",
  /topBtn\.onclick[\s\S]{0,120}scrollTo\(\{top:0, behavior:"smooth"\}\)/.test(INDEX));
kontrol("sepet FAB görünürken ok yukarı kayıyor (fab-var kuralı)",
  /body\.fab-var \.top-btn\{bottom:/.test(INDEX) &&
  /classList\.toggle\("fab-var", cart\.length > 0\)/.test(INDEX));

console.log(hata === 0
  ? "\nSONUÇ: ✅ " + toplam + "/" + toplam + " iddia geçti"
  : "\nSONUÇ: ❌ " + (toplam - hata) + "/" + toplam + " geçti, " + hata + " hata");
process.exit(hata === 0 ? 0 : 1);
