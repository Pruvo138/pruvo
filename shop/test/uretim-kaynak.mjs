#!/usr/bin/env node
/**
 * PRUVO shop — SIPARIS PANELINDE URETIM DOSYASI DRIVE BAGLANTISI (birim testleri).
 *
 *   node shop/test/uretim-kaynak.mjs
 *
 * NEDEN wrangler'siz: olculen davranis iki SAF yuzeydedir — (1) `driveKaynaklari()`
 * metin ayristirmasi, (2) panelin `kaynakHtml()/satirHtml()` render'i. Ikisi de
 * shop/src/yonet.js'ten HAM KAYNAK olarak cekilip vm'de kosturulur; KOPYA YAZILMAZ
 * (deploy edilen kodun ta kendisi sinanir — kopya yazilsaydi kaynak degistiginde test
 * yesil kalir ve iddia sessizce olurdu). yonet.js dogrudan `import` EDILEMIYOR: bagimli
 * modul zinciri JSON import attribute'u istiyor ve duz node'da ERR_IMPORT_ATTRIBUTE_MISSING
 * veriyor — dilimleme bu yuzden secildi, kolaylik icin degil.
 *
 * 🔴 FIKSTUR UYDURMADIR. Gercek uretim notu tedarikci/tasarimci izi tasir; bu dosyaya
 * musteri verisi de gercek fileId de YAZILMAZ. Fikstur yalnizca gercek notun BICIMINI
 * taklit eder (bkz. [[nobetci-fikstur-sekli]]).
 *
 * ONCE-KIRMIZI KANITI: mutasyon surucusu `tools/uretim-kaynak-mutasyon.py`
 * (gecici AYNAYA uygular; calisma agacina yazmaz). Kontrol mutanti M3 = "bos listeyi
 * SESSIZ gec" — bu testin K17 iddiasini KIRMIZI yakmak ZORUNDA.
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

// ---------------------------------------------------------------- A) AYRISTIRICI
const ayristiriciKaynak = dilimAl(KAYNAK, "const DRIVE_TABAN =", "// ---- anahtar ---");
if (!ayristiriciKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (driveKaynaklari blogu) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
const ayristirici = {};
vm.createContext(ayristirici);
vm.runInContext(ayristiriciKaynak.replace(/^export /m, ""), ayristirici,
  { filename: "yonet-ayristirici.js" });
const driveKaynaklari = ayristirici.driveKaynaklari;

// UYDURMA fileId'ler (base64url, gercek Drive kaydiyla ILGISI YOK).
// ⚠️ BILEREK sinif kelimesi ICERMEZLER ("kanonik"/"yedek" gecen bir id, ayni zamanda
// sinif isareti gibi okunur mu? Bu tuzak ilk kosumda GERCEKTEN yakalandi ve ayristiriciya
// "isaret fileId govdesine dusuyorsa sayma" kapisi eklendi — K42 o kapiyi olcer.)
const ID_KANONIK = "1AaBbCcDdEeFfGgHh0011223344";
const ID_YEDEK = "9ZzYyXxWwVvUuTt_-5566778899";

// Gercek notun BICIMINI taklit eden uydurma uretim notu.
const NOT_TAM =
  "Kanonik baski dosyasi (v3, YAN YATIK): pruvo-ozel/stl/ornek-parca/ornek-parca-v3.3mf " +
  "(R2 OZEL) + Drive fileId " + ID_KANONIK + ". Iki parca tek plakada. " +
  "DIKEY YEDEK: ornek-parca-v3-dikey.3mf (Drive fileId " + ID_YEDEK + "), 23 dk. " +
  "ESKI SURUMLER ARSIVDE, BASILMAZ: v2-yan/v2 ve v1 (ilk takmada kirilir).";

console.log("A) driveKaynaklari() — metin ayristirmasi");
const r = typeof driveKaynaklari === "function" ? driveKaynaklari(NOT_TAM) : null;
ol("K1  fonksiyon disa acildi + 3 kayit uretti (kanonik + yedek + arsiv uyarisi)",
  Array.isArray(r) && r.length === 3, "gelen=" + JSON.stringify(r));

const bagli = (r || []).filter((x) => x.url);
ol("K2  baglantili kayit sayisi = 2", bagli.length === 2, "gelen=" + bagli.length);
ol("K3  1. kayit sinif='kanonik'", bagli[0] && bagli[0].sinif === "kanonik",
  bagli[0] && bagli[0].sinif);
ol("K4  1. kayit url = drive.google.com/file/d/<id>/view",
  bagli[0] && bagli[0].url === "https://drive.google.com/file/d/" + ID_KANONIK + "/view",
  bagli[0] && bagli[0].url);
ol("K5  1. kayit dosya adi kanonik .3mf", bagli[0] && bagli[0].dosya === "ornek-parca-v3.3mf",
  bagli[0] && bagli[0].dosya);
ol("K6  2. kayit sinif='yedek'", bagli[1] && bagli[1].sinif === "yedek", bagli[1] && bagli[1].sinif);
ol("K7  2. kayit dosya adi DIKEY yedek dosyasi",
  bagli[1] && bagli[1].dosya === "ornek-parca-v3-dikey.3mf", bagli[1] && bagli[1].dosya);
ol("K8  2. kayit url YEDEK id'sini tasiyor (kanonikle karismadi)",
  bagli[1] && bagli[1].url.indexOf(ID_YEDEK) > 0 && bagli[1].url.indexOf(ID_KANONIK) < 0,
  bagli[1] && bagli[1].url);

const arsiv = (r || []).find((x) => x.sinif === "arsiv");
ol("K9  FAIL-LOUD: fileId'siz 'ARSIVDE, BASILMAZ' isareti YINE kayit uretti",
  !!arsiv, "arsiv kaydi=" + JSON.stringify(arsiv));
ol("K10 arsiv kaydinin url'i BOS (baglanti uretilemedi, sessizce atlanmadi)",
  !!arsiv && arsiv.url === "" && arsiv.file_id === "", arsiv && arsiv.url);
ol("K11 arsiv kaydi basilmaz=true (en pahali uretim hatasi isaretli)",
  !!arsiv && arsiv.basilmaz === true, arsiv && String(arsiv.basilmaz));
ol("K12 kanonik/yedek basilmaz=false", bagli.every((x) => x.basilmaz === false));

ol("K13 fileId'siz duz not -> BOS dizi (uydurma baglanti YOK)",
  JSON.stringify(driveKaynaklari("PETG siyah, 0.16 mm katman, %40 gyroid.")) === "[]");
ol("K14 bos/undefined/sayi girdi -> BOS dizi (patlamaz)",
  JSON.stringify(driveKaynaklari("")) === "[]" &&
  JSON.stringify(driveKaynaklari(undefined)) === "[]" &&
  JSON.stringify(driveKaynaklari(42)) === "[]");

const belirsiz = driveKaynaklari("Uretim dosyasi ornek.3mf, Drive fileId " + ID_KANONIK + ".");
ol("K15 sinif isareti YOKSA 'belirsiz' — sessiz 'kanonik' VARSAYIMI YOK",
  belirsiz.length === 1 && belirsiz[0].sinif === "belirsiz" && !!belirsiz[0].url,
  JSON.stringify(belirsiz));

const tekrar = driveKaynaklari(
  "Kanonik: a.3mf Drive fileId " + ID_KANONIK + " ... tekrar Drive fileId " + ID_KANONIK + ".");
ol("K16 ayni fileId iki kez gecse TEK satir", tekrar.filter((x) => x.url).length === 1,
  JSON.stringify(tekrar));

const zararliId = driveKaynaklari(
  'Kanonik: x.3mf Drive fileId javascript:alert(1)" onmouseover="x');
ol("K17 zararli/gecersiz fileId href'e GECMEZ (regex kapisi)",
  zararliId.every((x) => x.url === ""), JSON.stringify(zararliId));

const varyant = driveKaynaklari(
  "Kanonik a.3mf Drive fileID: " + ID_KANONIK + " ; yedek b.3mf Drive file_id = " + ID_YEDEK);
ol("K18 'fileID:' ve 'file_id =' yazim varyantlari da yakalanir",
  varyant.filter((x) => x.url).length === 2, JSON.stringify(varyant.map((x) => x.file_id)));

ol("K19 ayristirici SAF: kaynak blogunda env/request/fetch/D1 gecmiyor",
  !/\benv\b|\brequest\b|\bfetch\(|KATALOG/.test(ayristiriciKaynak));

// Drive id'si rastgele base64url'dur; icinde "yedek" gecmesi onu YEDEK yapmaz.
const idIcindeIsaret = driveKaynaklari(
  "Kanonik: a.3mf Drive fileId 1AaByedekCcDdEeFfGgHh00112233.");
ol("K42 fileId GOVDESINDEKI 'yedek' dizisi sinif isareti SAYILMAZ",
  idIcindeIsaret.length === 1 && idIcindeIsaret[0].sinif === "kanonik",
  JSON.stringify(idIcindeIsaret));

// ---------------------------------------------------------------- B) PANEL RENDER
console.log("B) panel render — GERCEK esc()/kaynakHtml()/satirHtml() (kopya DEGIL)");
/**
 * SAYFA_HTML bir SABLON DIZESIDIR: dosyada `\\'` yazan sey tarayiciya `\'` olarak gider.
 * Kaynagi dosyadan okudugumuz icin bu kacislari SOKMEK zorundayiz — sokmezsek vm
 * "Unexpected string" ile patlar (ilk kosumda oldu). kabul.js ayni fonksiyonlari CANLI
 * worker'in DONDURDUGU sayfadan cekiyor, orada kacislar zaten cozulmus oluyor; bu test
 * wrangler'siz kostugu icin donusumu kendisi yapar. Baska bir sey degistirmez.
 */
function sablonCoz(s) { return s.replace(/\\\\/g, "\\"); }
const escKaynak = sablonCoz(dilimAl(KAYNAK, "function esc(s){", "function tl(k){") || "");
const renderKaynak = sablonCoz(
  dilimAl(KAYNAK, "function kaynakHtml(k){", "function boyutMetni(b){") || "");
const panel = {};
let satirHtml = null, kaynakHtml = null;
if (!escKaynak || !renderKaynak) {
  ol("K20 sayfa kaynagindan esc/kaynakHtml/satirHtml cekildi", false, "capa bulunamadi");
} else {
  vm.createContext(panel);
  vm.runInContext(escKaynak + "\n" + renderKaynak, panel, { filename: "yonet-sayfa.js" });
  satirHtml = panel.satirHtml; kaynakHtml = panel.kaynakHtml;
  ol("K20 sayfa kaynagindan esc/kaynakHtml/satirHtml cekildi",
    typeof satirHtml === "function" && typeof kaynakHtml === "function");
}

const kalemTaban = {
  kalem: 0, id: "ornek-parca", baslik: "Örnek Parça", malzeme: "PETG", renk: "Siyah",
  adet: 1, parametrik: false, parametre_detay: "", baski_oneri: NOT_TAM,
  urun_url: "https://pruvo3d.com/urun/ornek-parca/",
};
const dolu = satirHtml ? satirHtml("PR-TEST-1", { ...kalemTaban, uretim_kaynaklari: r }) : "";
const bos = satirHtml
  ? satirHtml("PR-TEST-2", { ...kalemTaban, baski_oneri: "PETG siyah.", uretim_kaynaklari: [] })
  : "";

ol("K21 baglanti TIKLANABILIR: href=gercek Drive adresi",
  dolu.indexOf('href="https://drive.google.com/file/d/' + ID_KANONIK + '/view"') > 0,
  dolu.slice(0, 300));
ol("K22 yeni sekmede acilir: target=\"_blank\" rel=\"noopener\"",
  /<a class="indir" href="https:\/\/drive\.google\.com\/file\/d\/[^"]+" target="_blank" rel="noopener">/
    .test(dolu));
ol("K23 HER dosya AYRI satir (3 kayit -> 3 kdosya blogu)",
  (dolu.match(/class="kdosya/g) || []).length === 3,
  String((dolu.match(/class="kdosya/g) || []).length));
ol("K24 kanonik/yedek/arsiv AYRIMI ekranda gorunur (3 sinif etiketi de basildi)",
  dolu.indexOf("Kanonik") > 0 && dolu.indexOf("Yedek") > 0 && dolu.indexOf("BASILMAZ") > 0);
ol("K25 arsiv satiri KENDI sinifiyla isaretli (kanonikle ayni gorunmez)",
  dolu.indexOf('class="kdosya arsiv"') > 0 && dolu.indexOf('class="sinif arsiv"') > 0);
ol("K26 baglantisiz kayit 'bağlantı üretilemedi' yaziyor (bos hucre YOK)",
  dolu.indexOf("bağlantı üretilemedi") > 0);
ol("K27 dosya adi ekranda (hangi dosya oldugu belli)",
  dolu.indexOf("ornek-parca-v3.3mf") > 0 && dolu.indexOf("ornek-parca-v3-dikey.3mf") > 0);

// 🔴 KONTROL MUTANTININ HEDEFI: bos listede SESSIZ gecen surum bu iddiayi kirmizi yakar.
ol("K28 SESSIZ BOSLUK YASAK: kaynak yokken panel 'kaynak yok' yaziyor",
  bos.indexOf("kaynak yok") > 0, bos.slice(0, 300));
ol("K29 kaynak yokken de blok BASILIYOR (satir tamamen kaybolmuyor)",
  bos.indexOf("Üretim dosyası (Drive)") > 0);

const zararli = kaynakHtml ? kaynakHtml({ uretim_kaynaklari: [{
  sinif: '"><script>alert(1)</script>', etiket: "<img src=x onerror=alert(2)>",
  dosya: "<script>alert(3)</script>", file_id: "x", url: 'https://x/"><script>alert(4)</script>',
}] }) : "";
ol("K30 XSS: sinif/etiket/dosya/url HAM HTML olarak SIZMIYOR",
  !/<script>|<img /i.test(zararli) && /&lt;script&gt;/.test(zararli), zararli.slice(0, 200));

// ---------------------------------------------------------------- C) REGRESYON
console.log("C) regresyon — mevcut panel davranislari");
ol("K31 kalem basligi hala urun sayfasina linkli (target=_blank rel=noopener)",
  /<a href="https:\/\/pruvo3d\.com\/urun\/ornek-parca\/" target="_blank" rel="noopener">/.test(dolu));
ol("K32 'Ürün kodu: <id>' satiri duruyor", dolu.indexOf("Ürün kodu: ornek-parca") > 0);
ol("K33 baski onerisi blogu duruyor", dolu.indexOf("🖨️") > 0);
ol("K34 normal kalemde 'Üretim dosyaları' butonu + parcalar() cagrisi duruyor",
  dolu.indexOf("Üretim dosyaları") > 0 && dolu.indexOf("parcalar(") > 0);
const parametrik = satirHtml
  ? satirHtml("PR-TEST-3", { ...kalemTaban, parametrik: true, uretim_kaynaklari: [] })
  : "";
ol("K35 parametrik kalemde 'STL üret + indir' baglantisi duruyor",
  parametrik.indexOf("STL üret + indir") > 0 &&
  parametrik.indexOf("/api/shop/yonet/stl?siparis_no=") > 0);
ol("K36 'Kargolandı olarak işaretle' + kargoGonder duruyor",
  KAYNAK.indexOf("Kargolandı olarak işaretle") > 0 && KAYNAK.indexOf("async function kargoGonder(") > 0);
ol("K37 'Yerel komut kopyala' + komutKopyala duruyor",
  KAYNAK.indexOf("Yerel komut kopyala") > 0 && KAYNAK.indexOf("function komutKopyala(") > 0);
ol("K38 durum gecisi (durumDegis + POST /durum) duruyor",
  KAYNAK.indexOf("async function durumDegis(") > 0 && KAYNAK.indexOf('api("/durum"') > 0);
ol("K39 stl-liste/stl indirme yollari DEGISMEDI",
  KAYNAK.indexOf('altYol === "/stl" && m === "GET"') > 0 &&
  KAYNAK.indexOf('altYol === "/stl-liste" && m === "GET"') > 0);

// YETKI YUZEYI: yeni uc EKLENMEDI. Sayilar bu isten ONCEKI HEAD'de OLCULDU
// (git show HEAD:shop/src/yonet.js -> altYol kolu 10, Content-Disposition 2);
// tahmin DEGIL. Artarsa yeni bir yetkili uc ya da yeni bir dosya akisi acilmis demektir.
// 30 Agu 2026 (T1, Okan emri — manuel shop paneli): ara donemde eklenen kollarla
// birlikte olculen taban 11'di; "Urunler" sekmesi 4 uc ekledi (GET /urunler,
// GET /urunler-kuyruk, POST /urunler-ustyazim, POST /urunler-ustyazim-sil — hepsi
// yonetim anahtari arkasinda, EGE_ANAHTAR acamaz; kurallari shop/test/urunler-panel.mjs)
// -> taban BILEREK ve TARIHLI olarak 15. panel-kaynak.mjs V9d ayni sayiyi olcer.
const KOL_TABANI = 15, CD_TABANI = 2;
const kolSayisi = (KAYNAK.match(/altYol === "/g) || []).length;
ol("K40 YETKI YUZEYI GENISLEMEDI: yonlendirici kolu " + KOL_TABANI + " (yeni uc yok)",
  kolSayisi === KOL_TABANI, "kol=" + kolSayisi);
const cdSayisi = (KAYNAK.match(/Content-Disposition/g) || []).length;
ol("K41 yeni indirme/proxy/zip akisi yok (Content-Disposition " + CD_TABANI + ")",
  cdSayisi === CD_TABANI, "cd=" + cdSayisi);

console.log("");
console.log("TOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
process.exit(kalan === 0 ? 0 : 1);
