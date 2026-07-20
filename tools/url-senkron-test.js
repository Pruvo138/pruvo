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
 *     adımlı kanıt RAPOR-MIMARA.md'de; bu test regresyon bekçisidir.)
 */

const fs = require("fs");
const path = require("path");

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

if (m) {
  // activeCat/activeBrand/query + history/location kapalı değişkenlerini sararak çalıştır
  function urlUret(kat, marka, ara) {
    let sonUrl = null;
    const sandbox = new Function(
      "activeCat", "activeBrand", "query", "history", "location", "URLSearchParams",
      m[0] + "; syncUrl();"
    );
    sandbox(kat, marka, ara,
      { replaceState: (a, b, url) => { sonUrl = url; } },
      { pathname: "/" }, URLSearchParams);
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
}

/* ── 2) KABLOLAMA: tetik noktaları syncUrl çağırıyor mu? ───────────────── */
console.log("2) kablolama (statik — handler'lar syncUrl'a bağlı mı?)");

// marka çipi onclick bloğu: "activeBrand = m;" atamasıyla başlayan b.onclick
// fonksiyonu (tek satır ya da çok satır fark etmez) syncUrl() içermeli.
const cipSatir = INDEX.match(/b\.onclick = function\(\)\{\s*activeBrand = m;[\s\S]*?\n\s*\};/);
kontrol("marka çipi tıkı syncUrl çağırıyor",
  cipSatir && cipSatir[0].indexOf("syncUrl()") !== -1);

// kategori onclick bloğu: activeCat = c; ile renderCats arasında
const katBlok = INDEX.match(/activeCat = c;[\s\S]*?renderCats\(\);/);
kontrol("kategori tıkı syncUrl çağırıyor",
  katBlok && katBlok[0].indexOf("syncUrl()") !== -1);
kontrol('kategori "Tümü" TAM SIFIRLAMA: markayı sıfırlıyor',
  katBlok && /c === "Tümü"[\s\S]*?activeBrand = "Tümü"/.test(katBlok[0]));
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
