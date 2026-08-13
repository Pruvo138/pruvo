#!/usr/bin/env node
/**
 * PRUVO shop — YONETIM PANELI: URETICI KAYNAK LINKI + ACILIR/KAPANIR SIPARIS KARTI.
 *
 *   node shop/test/panel-kaynak.mjs
 *
 * NEDEN wrangler'siz: olculen davranis SAF yuzeylerdedir — (1) `kaynakLinkSuz()` Worker
 * suzgeci, (2) panelin `kaynakLinkHtml()/satirHtml()/kartHtml()` render'i. Ikisi de
 * shop/src/yonet.js'ten HAM KAYNAK olarak cekilip vm'de kosturulur; KOPYA YAZILMAZ
 * (kopya yazilsaydi kaynak degistiginde test yesil kalir, iddia sessizce olurdu).
 * Desen kardesi: shop/test/uretim-kaynak.mjs — ayni dilimleme gerekcesi orada yazili.
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek musteri verisi, gercek tedarikci adresi ve gercek
 * tasarimci adi bu dosyaya YAZILMAZ. Fikstur yalnizca BICIMI taklit eder
 * ([[nobetci-fikstur-sekli]] · [[nobetci-kendi-dosyasinda-sizinti]]).
 *
 * ONCE-KIRMIZI KANITI: `python3 tools/panel-kaynak-mutasyon.py` (gecici AYNAYA uygular;
 * calisma agacina yazmaz). Oldurucu mutantlar: bos string basma (V2), <details> yerine
 * <div> (V5), kalem nesnesine `tasarimci` ekleme (V7).
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (kaynak capasi bulunamadi).
 */

import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
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
/** SAYFA_HTML bir sablon dizesidir: `\\'` tarayiciya `\'` gider — vm icin cozulur. */
function sablonCoz(s) { return s.replace(/\\\\/g, "\\"); }

// ---------------------------------------------------------------- A) WORKER SUZGECI
console.log("A) kaynakLinkSuz() — Worker tarafi fail-closed suzgec");
const suzgecKaynak = dilimAl(KAYNAK, "export function kaynakLinkSuz(", "function yjson(");
if (!suzgecKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (kaynakLinkSuz) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
const suzgecCtx = {};
vm.createContext(suzgecCtx);
vm.runInContext(suzgecKaynak.replace(/^export /gm, ""), suzgecCtx, { filename: "yonet-suzgec.js" });
const kaynakLinkSuz = suzgecCtx.kaynakLinkSuz;
ol("V0  kaynakLinkSuz disa acildi", typeof kaynakLinkSuz === "function");

const LINK_OK = "https://ornek-platform.invalid/model/12345";
ol("V0a https:// adres GECER", kaynakLinkSuz(LINK_OK) === LINK_OK);
ol("V0b http:// · javascript: · data: · bagil yol · bos → BOS DONER (fail-closed)",
  kaynakLinkSuz("http://ornek-platform.invalid/x") === "" &&
  kaynakLinkSuz("javascript:alert(1)") === "" &&
  kaynakLinkSuz("data:text/html,<script>alert(1)</script>") === "" &&
  kaynakLinkSuz("/model/12345") === "" &&
  kaynakLinkSuz("") === "");
ol("V0c null/undefined/sayi/nesne → BOS DONER (patlamaz)",
  kaynakLinkSuz(null) === "" && kaynakLinkSuz(undefined) === "" &&
  kaynakLinkSuz(42) === "" && kaynakLinkSuz({ link: LINK_OK }) === "");

// ---------------------------------------------------------------- B) PANEL RENDER
console.log("B) panel render — GERCEK esc()/kaynakLinkHtml()/satirHtml()/kartHtml()");
const panelKaynak = sablonCoz(dilimAl(KAYNAK, "function esc(s){", "async function yukle(){") || "");
const panel = { document: null };
let satirHtml = null, kartHtml = null, kaynakLinkHtml = null;
if (!panelKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (sayfa JS blogu) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
vm.createContext(panel);
vm.runInContext(panelKaynak, panel, { filename: "yonet-sayfa.js" });
satirHtml = panel.satirHtml; kartHtml = panel.kartHtml; kaynakLinkHtml = panel.kaynakLinkHtml;
if (typeof satirHtml !== "function" || typeof kartHtml !== "function" ||
    typeof kaynakLinkHtml !== "function") {
  console.error("SAYFA FONKSIYONLARI CEKILEMEDI (satirHtml/kartHtml/kaynakLinkHtml) — OLCULEMEDI");
  process.exit(3);
}

const kalemTaban = {
  kalem: 0, id: "ornek-parca", baslik: "Örnek Parça", malzeme: "PETG", renk: "Siyah",
  adet: 1, parametrik: false, parametre_detay: "", baski_oneri: "PETG siyah, 0.16 mm.",
  uretim_kaynaklari: [], urun_url: "https://pruvo3d.com/urun/ornek-parca/",
};
const sLinkli = satirHtml("PR-TEST-1", { ...kalemTaban, kaynak_link: LINK_OK });
const sLinksiz = satirHtml("PR-TEST-2", { ...kalemTaban, kaynak_link: "" });

// VAKA 1 — link DOLU → tiklanabilir <a>
ol("V1  link DOLU → tiklanabilir <a href=...> baglanti VAR",
  sLinksiz !== sLinkli &&
  sLinkli.indexOf('<a class="indir" href="' + LINK_OK + '"') > 0,
  sLinkli.slice(0, 400));
ol("V1a baglanti YENI SEKMEDE acilir (target=_blank rel=noopener)",
  /href="https:\/\/ornek-platform\.invalid\/model\/12345"[^>]*target="_blank" rel="noopener"/
    .test(sLinkli));
ol("V1b 'Üretici kaynağı' satiri panelde BASILIYOR",
  sLinkli.indexOf("Üretici kaynağı") > 0 && sLinksiz.indexOf("Üretici kaynağı") > 0);

// VAKA 2 — link YOK → ACIK metin (SESSIZ BOSLUK YASAK)
ol("V2  link YOK → 'kaynak kaydı yok' metni VAR (bos DEGIL)",
  sLinksiz.indexOf("kaynak kaydı yok") > 0, sLinksiz.slice(0, 400));
ol("V2a link YOKKEN <a ...> baglantisi URETILMEZ",
  kaynakLinkHtml({ kaynak_link: "" }).indexOf("<a") < 0,
  kaynakLinkHtml({ kaynak_link: "" }));
ol("V2b alan HIC YOKSA da (undefined) 'kaynak kaydı yok' yazar",
  kaynakLinkHtml({}).indexOf("kaynak kaydı yok") > 0 &&
  kaynakLinkHtml(undefined).indexOf("kaynak kaydı yok") > 0);

// VAKA 3 — https disi / bozuk deger → 2. vakaya duser, HAM DEGER SIZMAZ
const BOZUK = "javascript:alert('sizinti-testi')";
const sBozuk = satirHtml("PR-TEST-3", { ...kalemTaban, kaynak_link: BOZUK });
ol("V3  'javascript:' degeri → 'kaynak kaydı yok' (2. vakaya duser)",
  sBozuk.indexOf("kaynak kaydı yok") > 0 && sBozuk.indexOf("<a class=\"indir\" href=\"j") < 0);
ol("V3a HAM DEGER HTML'e HIC SIZMIYOR (ne href'te ne metinde)",
  sBozuk.indexOf("javascript:") < 0 && sBozuk.indexOf("sizinti-testi") < 0,
  sBozuk.slice(0, 400));
const sGoreli = satirHtml("PR-TEST-4", { ...kalemTaban, kaynak_link: "//ornek.invalid/x" });
ol("V3b protokolsuz '//host' degeri de BASILMAZ (protocol-relative kacisi)",
  sGoreli.indexOf("kaynak kaydı yok") > 0 && sGoreli.indexOf("ornek.invalid") < 0);

// VAKA 4 — HTML kacisi (XSS regresyonu)
const XSS = 'https://ornek.invalid/x"><script>alert(1)</script><img src=x onerror=alert(2)>';
const sXss = satirHtml("PR-TEST-5", { ...kalemTaban, kaynak_link: XSS });
ol("V4  link icindeki \"/</> karakterleri ESCAPE edilir (ham <script> YOK)",
  !/<script>|<img /i.test(sXss) && /&lt;script&gt;/.test(sXss), sXss.slice(0, 400));
ol("V4a href ATTRIBUTU tirnakla kirilamiyor (&quot; kacisi var)",
  sXss.indexOf('href="https://ornek.invalid/x&quot;&gt;') > 0, sXss.slice(0, 400));

// VAKA 5 — <details> + odendi ACIK / digerleri KAPALI
const musteri = {
  ad: "Ornek Musteri", tel: "0500 000 00 00",
  eposta: "ornek@ornek.invalid", adres: "Ornek Mah. Ornek Sk. No 1",
};
function siparis(durum) {
  return {
    siparis_no: "PR-TEST-" + durum, tarih: "2026-08-13T10:00:00Z", durum: durum,
    kanal: "site", dis_no: "", odeme_yontemi: "kart",
    tutar_kurus: 125000, kargo_kurus: 9000, kdv_kurus: 22500,
    kargo_firma: "", kargo_kodu: "", durum_gecmisi: [], izinli_gecisler: ["uretimde"],
    musteri: musteri, kalemler: [{ ...kalemTaban, kaynak_link: LINK_OK }],
    yazdir_komut: "python3 tools/yazdir.py PR-TEST",
  };
}
const kOdendi = kartHtml(siparis("odendi"));
const kUretimde = kartHtml(siparis("uretimde"));
const kTamam = kartHtml(siparis("tamamlandi"));
ol("V5  kart <details> ile sariliyor (duz <div> DEGIL)",
  kOdendi.indexOf("<details") === 0 && kUretimde.indexOf("<details") === 0 &&
  /<\/details>$/.test(kUretimde), kUretimde.slice(0, 120));
ol("V5a <summary> satiri VAR", kUretimde.indexOf("<summary") > 0);
ol("V5b durumu 'odendi' olan kart ACIK dogar (open)",
  /^<details class="kart" open/.test(kOdendi), kOdendi.slice(0, 80));
ol("V5c diger durumlar KAPALI dogar (open YOK)",
  kUretimde.indexOf(" open") < 0 && kTamam.indexOf(" open") < 0,
  kUretimde.slice(0, 80));
ol("V5d kapali baslikta siparis no · durum rozeti · tarih · tutar · kalem sayisi VAR",
  (() => {
    const oz = dilimAl(kUretimde, "<summary", "</summary>") || "";
    return oz.indexOf("PR-TEST-uretimde") > 0 && oz.indexOf('class="rozet uretimde"') > 0 &&
      oz.indexOf("2026-08-13 10:00") > 0 && oz.indexOf("1.250,00 TL") > 0 &&
      oz.indexOf("1 kalem") > 0;
  })(), dilimAl(kUretimde, "<summary", "</summary>") || "(summary yok)");

// 🔴 OLCULEN TUZAK (13 Agu, bu isin ILK kosumunda GERCEKLESTI): SAYFA_HTML bir SABLON
// DIZESIDIR — icine yazilan TEK bir backtick sablonu ERKEN KAPATIR ve yonet.js modulu
// ARTIK IMPORT EDILEMEZ. Bu testin dilimleme yontemi o hatayi GORMEZ (ham metin okur,
// modulu yuklemez): kirmizi yalnizca kardes testlerde (olcum.mjs/kabul.js) yandi.
// Iddia o kor noktayi kapatir — sablon govdesinde backtick SIFIR olmali.
ol("V5e SAYFA_HTML sablon govdesinde backtick YOK (sablonu erken kapatirdi)",
  (() => {
    const govde = dilimAl(KAYNAK, "const SAYFA_HTML = `", "\n</script></body></html>`");
    return typeof govde === "string" && govde.slice("const SAYFA_HTML = `".length)
      .indexOf("`") < 0;
  })());

// VAKA 6 — kapali baslikta MUSTERI VERISI GECMEZ
const ozet = dilimAl(kUretimde, "<summary", "</summary>") || "";
ol("V6  kapali <summary> icinde musteri adi/telefon/e-posta/adres GECMIYOR",
  ozet.indexOf(musteri.ad) < 0 && ozet.indexOf(musteri.tel) < 0 &&
  ozet.indexOf(musteri.eposta) < 0 && ozet.indexOf(musteri.adres) < 0, ozet);
ol("V6a musteri verisi kart ACILINCA govdede GORUNUYOR (kaybolmadi)",
  kUretimde.indexOf(musteri.ad) > 0 && kUretimde.indexOf(musteri.tel) > 0 &&
  kUretimde.indexOf(musteri.eposta) > 0 && kUretimde.indexOf(musteri.adres) > 0);
ol("V6b lazy: kart ILK acildiginda kartAc() cagriliyor + kutu data-parca tasiyor",
  kUretimde.indexOf('ontoggle="kartAc(this)"') > 0 && kUretimde.indexOf('data-parca="1"') > 0);
ol("V6c lazy TEKRARI: kartAc 'yuklendi' damgasi tutuyor (ikinci acilis yeniden CEKMEZ)",
  /function kartAc\(el\)\{[\s\S]*?el\.dataset\.yuklendi[\s\S]*?el\.dataset\.yuklendi="1"/
    .test(sablonCoz(KAYNAK)));
ol("V6d `open` dogan kartlar icin toggle ELLE tetikleniyor (yukle sonunda)",
  KAYNAK.indexOf('details.kart[open]') > 0);

// VAKA 7 — 🔴 GIZLILIK: ticari alanlar panele SIZMAZ
console.log("C) 🔒 gizlilik kapilari");
const TICARI = ["tasarimci", "uyelik", "lisans", "alis_fiyati"];
const tumPanel = kOdendi + kUretimde + sLinkli + sLinksiz + sBozuk + sXss;
ol("V7  uretilen panel HTML'inde tasarimci/uyelik/lisans/alis_fiyati GECMIYOR",
  TICARI.every((a) => tumPanel.toLowerCase().indexOf(a) < 0),
  TICARI.filter((a) => tumPanel.toLowerCase().indexOf(a) >= 0).join(","));
// Kalem nesnesini URETEN Worker kolu da olculur: alan oraya eklenirse render'a da duser.
const listeKolu = dilimAl(KAYNAK, "const kayit = {", "kayit.uretim_kaynaklari =") || "";
ol("V7a Worker kalem nesnesi ticari alan TASIMIYOR (kaynagindan olculdu)",
  !!listeKolu && TICARI.every((a) => listeKolu.indexOf(a + ":") < 0),
  TICARI.filter((a) => listeKolu.indexOf(a + ":") >= 0).join(","));
ol("V7b kalem nesnesi `kaynak_link` alanini TASIYOR (yalniz link)",
  listeKolu.indexOf("kaynak_link:") > 0);
ol("V7c D1'den YALNIZ id+link cekiliyor (SELECT genisletilmedi)",
  KAYNAK.indexOf("SELECT id, link FROM urun_kaynak") > 0 &&
  (KAYNAK.match(/FROM urun_kaynak/g) || []).length === 1,
  String((KAYNAK.match(/FROM urun_kaynak/g) || []).length));

// VAKA 8 — 🔴 G2 KAPISI: musteriye donen yollar urun_kaynak'a SORGU ATMAZ
const TARANAN = [
  ["shop/src", ".js"], ["worker-iyzico-webhook", ".js"], ["onizleme", ".js"],
];
const deyen = [];
for (const [dizin, uzanti] of TARANAN) {
  const tam = path.join(KOK, dizin);
  let girdiler = [];
  try { girdiler = fs.readdirSync(tam); } catch (e) { girdiler = []; }
  for (const ad of girdiler) {
    if (!ad.endsWith(uzanti)) { continue; }
    let icerik = "";
    try { icerik = fs.readFileSync(path.join(tam, ad), "utf8"); } catch (e) { continue; }
    if (icerik.indexOf("urun_kaynak") >= 0) { deyen.push(dizin + "/" + ad); }
  }
}
ol("V8  `urun_kaynak` tablosuna DEGEN TEK dosya shop/src/yonet.js (yonetim ucu)",
  deyen.length === 1 && deyen[0] === "shop/src/yonet.js", "degen=" + JSON.stringify(deyen));
ol("V8a musteriye donen uc (shop/src/index.js) tabloya HIC dokunmuyor",
  fs.readFileSync(path.join(KOK, "shop", "src", "index.js"), "utf8")
    .indexOf("urun_kaynak") < 0);
// 🔴 G1: `urunler` tablosunu EGE (WhatsApp botu) okuyor. Kaynak/tedarikci sinifindan
// bir kolon oraya eklenirse bot musteriye tedarikci linki sizdirabilir. Bu iddia,
// KOLON ADLARINI d1-sema.sql'den AYIKLAYIP olcer (alt-dize taramasi degil: `marka_
// uyelikleri` gibi mesru bir ad "uyelik" alt-dizesiyle yanlis kirmizi yakardi).
const SEMA_SQL = fs.readFileSync(path.join(KOK, "tools", "d1-sema.sql"), "utf8");
const urunlerBlok = dilimAl(SEMA_SQL, "CREATE TABLE IF NOT EXISTS urunler (", "\n);") || "";
const urunlerKolonlari = urunlerBlok.split("\n")
  .map((r) => (r.match(/^\s{2}([A-Za-z_][A-Za-z0-9_]*)\s+(TEXT|INTEGER|REAL|BLOB|NUMERIC)\b/) || [])[1])
  .filter(Boolean);
const YASAK_KOLON = ["link", "kaynak", "tasarimci", "uyelik", "alis_fiyati", "kaynak_link"];
ol("V8b `urunler` tablosuna kaynak/link/tasarimci/uyelik kolonu EKLENMEDI (Ege okuyor)",
  urunlerKolonlari.length > 10 &&
  !urunlerKolonlari.some((k) => YASAK_KOLON.indexOf(k) >= 0),
  "kolon=" + urunlerKolonlari.length + " ihlal=" +
  urunlerKolonlari.filter((k) => YASAK_KOLON.indexOf(k) >= 0).join(","));
ol("V8c sorgu TOPLU (kalem basina sorgu ATILMIYOR): tek IN (...) cagrisi",
  KAYNAK.indexOf("WHERE id IN (\" + yertut + \")\").bind(...idler).all()") > 0 ||
  /urun_kaynak WHERE id IN \(" \+ yertut \+ "\)/.test(KAYNAK));
ol("V8d tablo YOKSA panel duser degil BOS gecer (tabloMerdiveni fail-soft)",
  KAYNAK.indexOf("async function tabloMerdiveni(") > 0 &&
  /no such table/i.test(KAYNAK));

// ---------------------------------------------------------------- D) REGRESYON
console.log("D) regresyon — mevcut panel davranislari");
ol("V9  kalem basligi hala urun sayfasina linkli",
  /<a href="https:\/\/pruvo3d\.com\/urun\/ornek-parca\/" target="_blank" rel="noopener">/
    .test(sLinkli));
ol("V9a 'Üretim dosyası (Drive)' blogu duruyor (kaynak yoksa 'kaynak yok')",
  sLinkli.indexOf("Üretim dosyası (Drive)") > 0 && sLinkli.indexOf("kaynak yok") > 0);
ol("V9b 'Üretim dosyaları' butonu + parcalar() cagrisi duruyor",
  sLinkli.indexOf("Üretim dosyaları") > 0 && sLinkli.indexOf("parcalar(") > 0);
ol("V9c durum gecis dugmeleri + 'Yerel komut kopyala' kartta duruyor",
  kUretimde.indexOf("durumDegis(") > 0 && kUretimde.indexOf("Yerel komut kopyala") > 0);
const KOL_TABANI = 10, CD_TABANI = 2;
const kolSayisi = (KAYNAK.match(/altYol === "/g) || []).length;
ol("V9d YETKI YUZEYI GENISLEMEDI: yonlendirici kolu " + KOL_TABANI + " (yeni uc yok)",
  kolSayisi === KOL_TABANI, "kol=" + kolSayisi);
const cdSayisi = (KAYNAK.match(/Content-Disposition/g) || []).length;
ol("V9e yeni indirme/proxy/zip akisi yok (Content-Disposition " + CD_TABANI + ")",
  cdSayisi === CD_TABANI, "cd=" + cdSayisi);

console.log("");
console.log("TOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
process.exit(kalan === 0 ? 0 : 1);
