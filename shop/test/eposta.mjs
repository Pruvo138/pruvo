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

import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { onayEpostasiHtml, kargoEpostasiHtml } from "../src/eposta.js";

const SITE = "https://pruvo3d.com";
let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

// Ortak dokum/siparis (onayEpostasiHtml imzasi: siparis, satirlar, dokum, havale)
const SIPARIS = { siparis_no: "PR-260717-120000-ABC", musteri_ad: "Test Musteri",
  musteri_adres: "Test Mah. No:1 / Mugla",
  musteri_notu: "<img src=x onerror=alert(1)>\nTeslimden önce arayın" };
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

// ---- 6) MUSTERI NOTU: yalniz satici kopyasi + kacisli HTML ----
{
  const musteri = onayEpostasiHtml(SIPARIS, [RESIMLI], DOKUM, false, false);
  const satici = onayEpostasiHtml(SIPARIS, [RESIMLI], DOKUM, false, true);
  ol("6a musteri kopyasinda not YOK", !musteri.includes("Teslimden önce arayın"));
  ol("6b satici kopyasinda ham <img YOK", !satici.includes("<img src=x"));
  ol("6c satici kopyasinda kacisli not VAR",
    satici.includes("&lt;img src=x onerror=alert(1)&gt;") &&
    satici.includes("Teslimden önce arayın"));
}

// ---- 7) FOTO KALEMI: OKAN (satici) KOPYASI is_no + girdiler + onizleme LINKI; MUSTERI KOPYASI BAYT-AYNI ----
// (Okan 13 Eki 21:0x) Bilgi foto.js saticiFotoBilgileri'nden gelir; burada o yapinin sablona basilisi olculur.
const FOTO_KALEM = { id: "ozel-foto-plaket", baslik: "Fotoğrafından özel üretim — Kabartma plaket (100 mm, ayaklı)",
  gorsel: "", malzeme: "PLA", renk: "Beyaz", adet: 1, tutar_kurus: 100000, foto_is: "5".repeat(32),
  foto_tur: "plaket", olcu_mm: 100, parametre_detay: "100 mm · tek renk · ayak: 1" };
const GORSEL_LINKI = "https://pruvo3d.com/api/shop/yonet/foto-dosya?siparis_no=PR-260717-120000-ABC&kalem=0&bicim=onizleme";
const FOTO_BILGI = [{ kalem: 0, is_no: "5".repeat(32), tur: "plaket", olcu_mm: 100, cesit: "figur", alt_tur: "pet",
  uretim_notu: "<script>alert(1)</script> & 'kenar' yuvarlak", malzeme: "PLA", renk: "Beyaz", gorsel: GORSEL_LINKI,
  onay_gerekli: true, onay_yonergesi: "Panel → Siparişler → bu kalemde \"Onayla (3D üret)\" (POST /yonet/foto/siparis-onayla)",
  ornek_no: "", cift_zincir_notu: "", okunamadi: false }];
const FOTO_BILGI_CIFT = [{ ...FOTO_BILGI[0], ornek_no: "ORNEK-555555555555",
  cift_zincir_notu: "bu iş için zaten üretim var: ORNEK-555555555555" }];
function fotoSenaryolar(onay) {
  const s = {};
  const yalin = onay(SIPARIS, [FOTO_KALEM], DOKUM, false, false);
  const bilgili = onay(SIPARIS, [FOTO_KALEM], DOKUM, false, false, FOTO_BILGI);
  const ciftli = onay(SIPARIS, [FOTO_KALEM], DOKUM, false, false, FOTO_BILGI_CIFT);
  // E1 musteri: bilgi verilse de cikti bilgisizle BAYT-AYNI; gorsel/link/is_no/not/onay ucu 0.
  s.E1 = yalin === bilgili && yalin === ciftli && yalin === onay(SIPARIS, [FOTO_KALEM], DOKUM, false) &&
    !bilgili.includes("5".repeat(32)) && !bilgili.includes("foto-dosya") && !bilgili.includes("<img") &&
    !bilgili.includes("siparis-onayla") && !bilgili.includes("kenar") && !bilgili.includes("ORNEK-");
  const satici = onay(SIPARIS, [FOTO_KALEM], DOKUM, false, true, FOTO_BILGI);
  // E2 Okan: is_no + tur/olcu/cesit/alt tur + not (KACISLI) + gorsel LINKI (img DEGIL) + onay yonergesi.
  s.E2 = satici.includes("<code>" + "5".repeat(32) + "</code>") && satici.includes("figur / pet") &&
    satici.includes("100 mm") && satici.includes("PLA / Beyaz") &&
    satici.includes("&lt;script&gt;alert(1)&lt;/script&gt; &amp; &#39;kenar&#39; yuvarlak") && !satici.includes("<script>") &&
    satici.includes("href='" + GORSEL_LINKI.replace(/&/g, "&amp;") + "'") && !satici.includes("<img") &&
    satici.includes("POST /yonet/foto/siparis-onayla") && satici.includes("okan_onay: true") &&
    !satici.includes("zaten üretim var");
  const saticiCift = onay(SIPARIS, [FOTO_KALEM], DOKUM, false, true, FOTO_BILGI_CIFT);
  s.E3 = saticiCift.includes("⚠️ bu iş için zaten üretim var: ORNEK-555555555555") && satici !== saticiCift;
  return s;
}
{
  const s = fotoSenaryolar(onayEpostasiHtml);
  ol("E1 musteri kopyasi foto kaleminde gorsel/link/is_no/not 0 ve bilgiyle BAYT-AYNI", s.E1);
  ol("E2 Okan kopyasi is_no + cesit/alt tur + olcu + malzeme/renk + not KACISLI + gorsel LINKI + onay yonergesi", s.E2);
  ol("E3 Okan kopyasi cift zincir notu (bu iş için zaten üretim var: ORNEK-…)", s.E3);
}

// ---- 8) MUTANT (izole kopya; calisma agacina yazilmaz): Okan blogu musteri kopyasina da basilir -> E1 KIRMIZI ----
{
  const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
  const GECICI = path.join(BURASI, "..", "eposta-test-tmp-" + process.pid);  // ../../secenekler.js cozulsun diye shop/<x>/
  process.on("exit", () => { fs.rmSync(GECICI, { recursive: true, force: true }); });
  const ASIL = fs.readFileSync(path.join(BURASI, "..", "src", "eposta.js"), "utf8");
  const MUTANTLAR = [
    ["E-M3 OKAN BLOGU MUSTERI KOPYASINA DA BASILIR",
     "(satici && Array.isArray(fotoBilgi) && fotoBilgi.length ? saticiFotoBlogu(fotoBilgi) : \"\")",
     "(Array.isArray(fotoBilgi) && fotoBilgi.length ? saticiFotoBlogu(fotoBilgi) : \"\")", ["E1"]],
    ["E-MK KONTROL", "Musteri kopyasina BASILMAZ (cagiran", "Musteri kopyasina  BASILMAZ (cagiran", []],
  ];
  let n = 0;
  for (const [ad, capa, yerine, olmeli] of MUTANTLAR) {
    if (ASIL.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, "capa kayip/coklu"); continue; }
    fs.mkdirSync(GECICI, { recursive: true });
    const dosya = path.join(GECICI, "eposta-" + (++n) + ".js");
    fs.writeFileSync(dosya, ASIL.replace(capa, yerine));
    const m = await import(url.pathToFileURL(dosya).href);
    const s = fotoSenaryolar(m.onayEpostasiHtml);
    const kirmizi = Object.keys(s).filter((x) => s[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli), JSON.stringify(kirmizi));
  }
}

console.log("S) SADE CERCEVE (Okan 14 Eki 12:5x: sehir satiri + WhatsApp kapanis satiri e-postadan CIKTI)");
{
  // Musteri metni (satir icerigi) bilerek sehir/WhatsApp TASIMAZ: olculen yalniz cercevenin urettigi metin.
  const temiz = { ...SIPARIS, musteri_adres: "Test Mah. No:1" };
  const sablonlar = [
    ["onay musteri", onayEpostasiHtml(temiz, [RESIMLI], DOKUM, false)],
    ["onay havale", onayEpostasiHtml(temiz, [RESIMLI], DOKUM, true)],
    ["onay satici", onayEpostasiHtml(temiz, [RESIMLI], DOKUM, false, true)],
    ["kargo", kargoEpostasiHtml(temiz, [RESIMLI], "Yurtici", "123")],
  ];
  for (const [ad, h] of sablonlar) {
    ol("S " + ad + ": sehir adi YOK", !/Fethiye/i.test(h));
    ol("S " + ad + ": WhatsApp kapanis satiri/baglantisi YOK", !/Sorularınız için|wa\.me|ulaşabilirsiniz/.test(h));
    ol("S " + ad + ": marka satiri DURUR", h.includes(">Endüstriyel Parça Üretimi</p>"));
  }
}

console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" + (kalan ? "" : " — HEPSI YESIL ✅"));
process.exit(kalan ? 1 : 0);
