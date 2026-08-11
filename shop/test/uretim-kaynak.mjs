#!/usr/bin/env node
/**
 * PRUVO shop — SIPARIS PANELI SUNUM KAPISI (birim testleri):
 *   A/B/C  uretim dosyasi DRIVE BAGLANTISI (ayristirma + render + regresyon),
 *   D      baski notunun KATLANMASI (details/summary; 11 Agu 2026, Okan istegi),
 *   E      URETICININ KAYNAK LINKI (mekanizma; alan bugun D1'de YOK — bkz. yonet.js).
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
 * (gecici AYNAYA uygular; calisma agacina yazmaz). Spec'in istedigi kontrol mutantlari:
 *   M1  bos kaynak listesini SESSIZ gec            -> K28 kirmizi,
 *   M11 Drive blogunu KATLAMANIN ICINE al          -> K48/K49 kirmizi,
 *   M12 katlamayi varsayilan ACIK yap              -> K44 kirmizi,
 *   M13 kaynak linki yokken SESSIZ gec             -> K64/K65/K66 kirmizi,
 *   M14 "olculemedi"yi "yok" diye beyan et         -> K65 kirmizi.
 * M9/M10/M19/M20 NOTR mutantlaridir ve YESIL kalmak zorundadir.
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
// `g` BAYRAGI ZORUNLU: blokta ARTIK BIRDEN COK `export` var (driveKaynaklari +
// kaynakBaglantisi). Bayraksiz hali yalnizca ILKINI soker ve vm "Unexpected token
// 'export'" ile PATLAR — yani sessiz degil, gurultulu bir hata (ilk kosumda oldu).
vm.runInContext(ayristiriciKaynak.replace(/^export /gm, ""), ayristirici,
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
const KOL_TABANI = 10, CD_TABANI = 2;
const kolSayisi = (KAYNAK.match(/altYol === "/g) || []).length;
ol("K40 YETKI YUZEYI GENISLEMEDI: yonlendirici kolu " + KOL_TABANI + " (yeni uc yok)",
  kolSayisi === KOL_TABANI, "kol=" + kolSayisi);
const cdSayisi = (KAYNAK.match(/Content-Disposition/g) || []).length;
ol("K41 yeni indirme/proxy/zip akisi yok (Content-Disposition " + CD_TABANI + ")",
  cdSayisi === CD_TABANI, "cd=" + cdSayisi);

// ------------------------------------------------- D) BASKI NOTU KATLAMASI (IS A)
// Okan'in istegi: "bu bölüm açılır kapanır olmalı, çok uzun olunca sayfayı dolduruyor."
// 🔴 KAPSAM SOZLESMESI: katlanan YALNIZ uzun aciklama metnidir. Drive baglantilari ve
// sinif etiketleri (ozellikle "ARSIVDE — BASILMAZ") katlamanin DISINDA kalir — uretimde
// ILK bakilacak sey onlardir ve tiklama arkasina saklanamazlar.
console.log("D) baski notu katlamasi — details/summary (IS A)");

/** `<details ...>` ile eslesen ILK blogun ICI (kapali etikete kadar). */
function detaysIci(html) {
  const b = html.indexOf("<details");
  const s = b >= 0 ? html.indexOf("</details>", b) : -1;
  return (b >= 0 && s > b) ? html.slice(b, s) : "";
}
const katliIc = detaysIci(dolu);

ol("K43 baski notu <details>/<summary> ile KATLANDI",
  /<details class="baski"><summary>/.test(dolu), dolu.slice(0, 200));
ol("K44 VARSAYILAN KAPALI: <details> etiketinde `open` YOK",
  katliIc !== "" && !/^<details[^>]*\bopen\b/.test(katliIc),
  katliIc.slice(0, 120));
ol("K45 tam not katlamanin ICINDE (metin kaybolmadi)",
  katliIc.indexOf("ESKI SURUMLER ARSIVDE") > 0 &&
  katliIc.indexOf("Iki parca tek plakada") > 0, katliIc.length + " karakter");

const ozetIci = (dolu.match(/<summary>([\s\S]*?)<\/summary>/) || [])[1] || "";
ol("K46 ozet KISA (<=95 karakter) ve tam nottan kisa — kapaliyken satiri doldurmuyor",
  ozetIci.length > 0 && ozetIci.length <= 95 && ozetIci.length < NOT_TAM.length,
  "ozet=" + ozetIci.length + " tam=" + NOT_TAM.length);
ol("K47 ozet BOS DEGIL (tiklanacak baslik var)", ozetIci.trim().length > 3, ozetIci);

// 🔴 KONTROL MUTANTININ HEDEFI (M11/M12): baglantilari/etiketleri katlamanin ICINE alan
// surum bu iddiayi KIRMIZI yakmali.
ol("K48 KATLAMANIN DISINDA: Drive baglanti blogu (.kaynak/.kdosya) <details> icinde DEGIL",
  katliIc.indexOf('class="kaynak"') < 0 && katliIc.indexOf('class="kdosya') < 0 &&
  katliIc.indexOf('class="sinif') < 0 && katliIc.indexOf("drive.google.com") < 0,
  katliIc.slice(0, 200));
ol("K49 KATLAMANIN DISINDA: sinif etiketleri (Kanonik/Yedek/BASILMAZ rozetleri) gorunur",
  dolu.indexOf("</details>") > 0 &&
  dolu.indexOf('class="kaynak"') > dolu.indexOf("</details>") &&
  dolu.indexOf('class="sinif arsiv"') > dolu.indexOf("</details>"),
  "details_son=" + dolu.indexOf("</details>") + " kaynak=" + dolu.indexOf('class="kaynak"'));
ol("K50 HARICI KUTUPHANE/CDN YOK: sayfada <script src=/<link rel=stylesheet/cdn yok",
  !/<script[^>]+src=/i.test(KAYNAK) && !/<link[^>]+stylesheet/i.test(KAYNAK) &&
  !/cdn\./i.test(KAYNAK));
const bosNot = satirHtml
  ? satirHtml("PR-TEST-4", { ...kalemTaban, baski_oneri: "", uretim_kaynaklari: [] })
  : "";
ol("K51 not BOSKEN de ozet ACIK bir sey yaziyor (bos summary yok)",
  bosNot.indexOf("baskı notu yok") > 0, bosNot.slice(0, 200));
const zararliNot = satirHtml
  ? satirHtml("PR-TEST-5", { ...kalemTaban, uretim_kaynaklari: [],
      baski_oneri: "<script>alert(1)</script> uzun not " + "x".repeat(200) })
  : "";
ol("K52 katlanan metin ve ozet KACISLANIYOR (details icine ham HTML sizmiyor)",
  !/<script>/i.test(zararliNot) && /&lt;script&gt;/.test(zararliNot),
  zararliNot.slice(0, 200));

// --------------------------------------------- E) URETICININ KAYNAK LINKI (IS B)
// 🔴 FIKSTURLER UYDURMADIR: gercek kaynak adresi tasarimci adi tasir ve bu dosyaya
// (repoya, commit'e, log'a) YAZILAMAZ. `example.invalid` IANA'nin rezerve ettigi,
// asla cozulmeyen alan adidir.
console.log("E) ureticinin kaynak linki — kaynakBaglantisi() + panel (IS B)");
const kaynakBaglantisi = ayristirici.kaynakBaglantisi;
const ORNEK_URL = "https://ornek-platform.example.invalid/model/12345-ornek-parca";

ol("K53 kaynakBaglantisi() disa acildi", typeof kaynakBaglantisi === "function");
const kbVar = kaynakBaglantisi ? kaynakBaglantisi(ORNEK_URL, true) : {};
ol("K54 gecerli https adresi -> sebep='var', url AYNEN korunur",
  kbVar.sebep === "var" && kbVar.url === ORNEK_URL, JSON.stringify(kbVar));
ol("K55 host ayiklanir (ekranda YALNIZ host yazacak — tam adres href'te kalir)",
  kbVar.host === "ornek-platform.example.invalid", kbVar.host);
ol("K56 'www.' onegi duser",
  kaynakBaglantisi("https://www.ornek.example.invalid/x", true).host === "ornek.example.invalid");

// 🔴 UC DEGERLI SEBEP: "yok" (kolon var, deger bos) ile "olculemedi" (kolon YOK) AYRI.
ol("K57 kolon YOKKEN (alanVar!==true) sebep='olculemedi' — 'yok' DEGIL",
  kaynakBaglantisi(undefined, false).sebep === "olculemedi" &&
  kaynakBaglantisi(ORNEK_URL, false).sebep === "olculemedi" &&
  kaynakBaglantisi(ORNEK_URL).sebep === "olculemedi",
  JSON.stringify(kaynakBaglantisi(ORNEK_URL, false)));
ol("K58 kolon VARKEN bos deger -> sebep='yok' (olculemedi ile karismaz)",
  kaynakBaglantisi("", true).sebep === "yok" &&
  kaynakBaglantisi("   ", true).sebep === "yok" &&
  kaynakBaglantisi(null, true).sebep === "yok");

const kotuler = [
  "javascript:alert(1)", "http://ornek.example.invalid/x", "//ornek.example.invalid/x",
  'https://ornek.example.invalid/x" onmouseover="y', "https://ornek.example.invalid/a b",
  "https://ornek.example.invalid/<script>", "data:text/html,x", "https://",
  // 🔴 KONTROL KARAKTERI AYRI EKSEN: kanonik URL regex'i bunlari ELEMEZ (yol kisminda
  // yalniz bosluk/tirnak/aci parantez/ters bolu yasak) — tek bekci ayri `if`tir.
  // Kacis dizisiyle yazilir: HAM bayt dosyaya girerse dosya "binary" olur ve grep
  // tabanli nobetciler onu SESSIZCE atlar.
  "https://ornek.example.invalid/\u0000x",
  "https://ornek.example.invalid/\u001Fx",
  "https://ornek.example.invalid/\u007Fx",
];
const kotuSonuc = kaynakBaglantisi ? kotuler.map((x) => kaynakBaglantisi(x, true)) : [];
ol("K59 GUVENLIK: javascript:/http:/tirnak/bosluk/kontrol karakteri -> 'gecersiz', url BOS",
  kotuSonuc.length === kotuler.length &&
  kotuSonuc.every((x) => x.sebep === "gecersiz" && x.url === ""),
  JSON.stringify(kotuSonuc.map((x) => x.sebep)));
/**
 * KOD SATIRLARI (tam satirlik yorum/JSDoc govdesi ATILIR). Blok ici `//` ile kesmek
 * yasak: kaynakta "https://..." dizeleri var, naif yorum sokme onlari BUDAR ve iddia
 * sessizce zayiflar. Kural bu yuzden DAR: yalnizca satirin TAMAMI yorumsa atilir —
 * kod satirindaki her `uyelik` gecisi YAKALANIR.
 */
function kodSatirlari(metin) {
  return metin.split("\n")
    .filter((s) => !/^\s*(\/\/|\/\*|\*)/.test(s))
    .join("\n");
}
const KOD = kodSatirlari(KAYNAK);
ol("K60 GIZLILIK: KOD'da 'uyelik' HIC gecmiyor (uyelik panelde de GOSTERILMEZ)",
  !/uyelik/i.test(KOD),
  "gecen satir: " + (KOD.split("\n").filter((s) => /uyelik/i.test(s))[0] || ""));
ol("K69 GIZLILIK: kodda gercek platform alan adi GOMULU degil (fikstur/uydurma disinda)",
  !/thingiverse|printables|makerworld|cgtrader|cults3d|myminifactory/i.test(KOD),
  "gecen satir: " + (KOD.split("\n")
    .filter((s) => /thingiverse|printables|makerworld|cgtrader|cults3d/i.test(s))[0] || ""));

const kaynakli = satirHtml ? satirHtml("PR-TEST-6", {
  ...kalemTaban, uretim_kaynaklari: [], kaynak: kbVar }) : "";
ol("K61 panel: kaynak linki TIKLANABILIR (target=_blank rel=noopener)",
  new RegExp('<a class="indir" href="' + ORNEK_URL + '" target="_blank" rel="noopener">')
    .test(kaynakli), kaynakli.slice(0, 400));
ol("K62 panel: gorunur METIN yalniz HOST — adres yolu (tasarimci izi) ekrana YAZILMAZ",
  kaynakli.indexOf(">ornek-platform.example.invalid — kaynak sayfası</a>") > 0 &&
  kaynakli.split("12345-ornek-parca").length === 2,
  kaynakli.slice(0, 400));
ol("K63 kaynak satiri KATLAMANIN DISINDA (</details>'ten SONRA)",
  kaynakli.indexOf('class="kaynaklink"') > kaynakli.indexOf("</details>") &&
  detaysIci(kaynakli).indexOf("kaynaklink") < 0);

// 🔴 SESSIZ BOSLUK YASAK — kontrol mutantlarinin hedefi (M13/M14).
const kaynakYok = satirHtml ? satirHtml("PR-TEST-7", {
  ...kalemTaban, uretim_kaynaklari: [], kaynak: { url: "", host: "", sebep: "yok" } }) : "";
const kaynakOlculemedi = satirHtml ? satirHtml("PR-TEST-8", {
  ...kalemTaban, uretim_kaynaklari: [],
  kaynak: { url: "", host: "", sebep: "olculemedi" } }) : "";
const kaynakGecersiz = satirHtml ? satirHtml("PR-TEST-9", {
  ...kalemTaban, uretim_kaynaklari: [],
  kaynak: { url: "", host: "", sebep: "gecersiz" } }) : "";
ol("K64 link YOKKEN panel 'kaynak linki yok' YAZIYOR (bos hucre YOK)",
  kaynakYok.indexOf("kaynak linki yok") > 0, kaynakYok.slice(0, 300));
ol("K65 OLCULEMEDI ayri cumle — 'kaynak linki yok' demiyor",
  kaynakOlculemedi.indexOf("ÖLÇÜLEMEDİ") > 0 &&
  kaynakOlculemedi.indexOf("kaynak linki yok") < 0, kaynakOlculemedi.slice(0, 300));
ol("K66 gecersiz deger: sebep yaziliyor ve HREF URETILMIYOR",
  kaynakGecersiz.indexOf("geçersiz") > 0 &&
  kaynakGecersiz.split('class="kaynaklink"')[1].indexOf("<a ") < 0,
  kaynakGecersiz.slice(0, 300));
ol("K67 `kaynak` alani HIC YOKKEN (eski kayit) patlamiyor + ÖLÇÜLEMEDİ yaziyor",
  dolu.indexOf("ÖLÇÜLEMEDİ") > 0);
const kaynakZararli = satirHtml ? satirHtml("PR-TEST-10", {
  ...kalemTaban, uretim_kaynaklari: [],
  kaynak: { url: 'https://x/"><script>alert(1)</script>',
            host: "<img src=x onerror=alert(2)>", sebep: "var" } }) : "";
ol("K68 XSS: kaynak url/host HAM HTML olarak SIZMIYOR",
  !/<script>|<img /i.test(kaynakZararli) && /&lt;script&gt;/.test(kaynakZararli),
  kaynakZararli.slice(0, 300));

console.log("");
console.log("TOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
process.exit(kalan === 0 ? 0 : 1);
