#!/usr/bin/env node
/**
 * PRUVO shop — E-POSTA SABLONU BIRIM TESTLERI (siparis e-postalarina urun linki + kapak resmi).
 *
 *   node shop/test/eposta.mjs
 *
 * eposta.js'i DOGRUDAN import eder (worker'siz, hizli). Uc sablonun UCU de tek satir ureticisi
 * (satirTablosu) kullaniyor: onay (musteri kopyasi), onay (satici kopyasi = ayni fonksiyon) ve
 * kargo. Bu yuzden satirTablosu'nu onayEpostasiHtml + kargoEpostasiHtml uzerinden sinamak
 * ucunu birden kapsar. Kabul (tools/paket): (a) href=/urun/<id>/ link, (b) gorsel dolu kalemde
 * <img src=<gorsel>>, (c) gorsel BOS/eksik kalemde img YOK ama link VAR (cokme yok),
 * (d) satici kopyasi da link/resim, (e) baslik/id/gorsel'e enjekte edilen <script>/tirnak KACISLI.
 *
 * ONCE-KIRMIZI: eski eposta.js'te (link/img yokken) bu testler KIRMIZI yanar.
 */

import { onayEpostasiHtml, kargoEpostasiHtml } from "../src/eposta.js";

const SITE = "https://pruvo3d.com";
let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

// Ortak dokum/siparis (onayEpostasiHtml imzasi: siparis, satirlar, dokum, havale)
const SIPARIS = { siparis_no: "PR-260717-120000-ABC", musteri_ad: "Test Musteri",
  musteri_adres: "Test Mah. No:1 / Mugla" };
const DOKUM = { tutarKurus: 20000, kargoKurus: 25000, kdvKurus: 7500, tahsilatKurus: 45000 };

// Kapak resmi OLAN kalem + resmi OLMAYAN (bos) kalem + resmi tanimSIZ (eski siparis) kalem.
const RESIMLI = { id: "audi-yakit-kapagi", baslik: "Audi Yakıt Kapağı", gorsel:
  "https://media.pruvo3d.com/urunler/audi-yakit-kapagi-1.jpg",
  malzeme: "PLA", renk: "Siyah", adet: 2, tutar_kurus: 20000 };
const RESIMSIZ = { id: "vw-klips", baslik: "VW Klips", gorsel: "",
  malzeme: "PETG", renk: "Beyaz", adet: 1, tutar_kurus: 12000 };
const RESIM_TANIMSIZ = { id: "eski-siparis-parca", baslik: "Eski Sipariş Parça",
  malzeme: "PLA", renk: "Siyah", adet: 1, tutar_kurus: 5000 }; // gorsel alani HIC yok

// ---- 1) LINK: her kalem basligi /urun/<id>/ linki ----
{
  const h = onayEpostasiHtml(SIPARIS, [RESIMLI, RESIMSIZ], DOKUM, false);
  ol("1a resimli kalem linki", h.includes("href='" + SITE + "/urun/audi-yakit-kapagi/'"), h.slice(0, 0));
  ol("1b resimsiz kalem linki", h.includes("href='" + SITE + "/urun/vw-klips/'"));
  ol("1c baslik link metni", h.includes(">Audi Yakıt Kapağı</a>"));
}

// ---- 2) RESIM: gorsel dolu kalemde <img src=<gorsel>> ----
{
  const h = onayEpostasiHtml(SIPARIS, [RESIMLI], DOKUM, false);
  ol("2a img src gorsel", h.includes("<img src='https://media.pruvo3d.com/urunler/audi-yakit-kapagi-1.jpg'"));
  ol("2b img width 56", /<img [^>]*width='56'/.test(h));
}

// ---- 3) GRACEFUL: gorsel BOS/eksik kalemde img YOK ama link VAR, cokme yok ----
{
  // Sepette hem resimli hem resimsiz: TAM 1 img olmali (yalniz resimli), 2 link olmali.
  const h = onayEpostasiHtml(SIPARIS, [RESIMLI, RESIMSIZ, RESIM_TANIMSIZ], DOKUM, false);
  const imgSayisi = (h.match(/<img /g) || []).length;
  const linkSayisi = (h.match(/\/urun\//g) || []).length;
  ol("3a tam 1 img (yalniz resimli kalem)", imgSayisi === 1, "img=" + imgSayisi);
  ol("3b 3 kalem 3 link", linkSayisi === 3, "link=" + linkSayisi);
  ol("3c resimsiz kalem linki yine var", h.includes("/urun/vw-klips/"));
  ol("3d eksik-gorsel kalem linki var (cokme yok)", h.includes("/urun/eski-siparis-parca/"));
}

// ---- 4) SATICI KOPYASI + KARGO ayni tabloyu kullanir (link+resim) ----
{
  // onayEpostasiHtml musteri+satici KOPYASININ ikisinde de kullaniliyor (index.js) — cikti ayni.
  // Kargo e-postasi da satirTablosu uzerinden link+resim tasimali.
  const hk = kargoEpostasiHtml(SIPARIS, [RESIMLI, RESIMSIZ], "Yurtiçi Kargo", "YK123TR");
  ol("4a kargo e-posta link", hk.includes("href='" + SITE + "/urun/audi-yakit-kapagi/'"));
  ol("4b kargo e-posta img", hk.includes("<img src='https://media.pruvo3d.com/urunler/audi-yakit-kapagi-1.jpg'"));
  ol("4c kargo takip kodu duruyor", hk.includes("YK123TR"));
}

// ---- 5) XSS: baslik/id/gorsel'e enjekte edilen <script>/tirnak KACISLI ----
{
  const KOTU = {
    id: "kotu'\"><script>alert(1)</script>",
    baslik: "Zararlı <script>alert('xss')</script> Başlık",
    gorsel: "https://e/x.jpg' onerror='alert(1)",
    malzeme: "PLA", renk: "Siyah", adet: 1, tutar_kurus: 1000,
  };
  const h = onayEpostasiHtml(SIPARIS, [KOTU], DOKUM, false);
  ol("5a ham <script> YOK (kacisli)", !h.includes("<script>"), "ham script sizdi");
  ol("5b kacisli &lt;script&gt; VAR", h.includes("&lt;script&gt;"));
  ol("5c gorsel attribute kirilmadi (ham ' onerror=' YOK)", !/[^&]' onerror='/.test(h),
    "attribute tirnagi kirildi");
  ol("5d kacisli onerror (&#39;) VAR", h.includes("onerror=&#39;") || h.includes("&#39; onerror=&#39;"));
  // Cokme yok: HTML uretildi ve cerceve tamamlandi.
  ol("5e cerceve tamam (cokme yok)", h.includes("</div>") && h.includes("PRUVO"));
}

console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" + (kalan ? "" : " — HEPSI YESIL ✅"));
process.exit(kalan ? 1 : 0);
