/**
 * pruvo-shop — anahtar korumali SIPARIS YONETIMI (siparis yonetimi paketi, Faz 1).
 *
 * Uclar (shop worker'a takili; site route'u pruvo3d.com/api/shop/yonet*):
 *   GET  /api/shop/yonet            -> tek dosyalik yonetim SAYFASI (inline HTML/CSS/JS)
 *   GET  /api/shop/yonet/liste      -> JSON siparis listesi (son 50; ?durum= ile suzme)
 *   POST /api/shop/yonet/durum      -> {siparis_no, durum} durum makinesi (izinli gecisler)
 *   POST /api/shop/yonet/kargo      -> {siparis_no, kargo_firma, kargo_kodu} -> 'kargolandi' + e-posta
 *   POST (K284) havale kanit endpoint -> {siparis_no, dekont_ref, tutar?} -> 'odendi' + Purchase olcumu
 *   GET  /api/shop/yonet/stl        -> uretim dosyasi indir (parametrik: derleyici; normal: R2)
 *   POST /api/shop/yonet/wa-siparis -> WhatsApp (Ege) kanalindan gelen siparisi panele yazar
 *
 * KIRMIZI CIZGILER (tools/paket-siparis-yonetimi.md):
 *  - Erisim: X-Yonet-Anahtar basligi (makine istemcileri) YA DA `pruvo_yonet` HttpOnly cerezi
 *    (tarayici; POST /yonet sifre kutusundan kurulur). ❌ `?anahtar=` SORGU PARAMETRESI YOK —
 *    tam URL erisim loglarina/tarayici gecmisine/Referer basligina yaziliyordu (sessiz sizinti).
 *    Anahtar YOK/YANLIS -> /yonet GET'te sifre kutusu, diger uclarda 404 (varligi sizmasin).
 *    YONET_ANAHTAR secret tanimli DEGILSE tum /yonet* 404 (ozellik kapali; form bile yok).
 *  - Anahtar loglara/HATA metnine YAZILMAZ. PII yalniz anahtarli yanitta. CORS yok (same-origin).
 *  - Gizli kaynak bilgisi (tedarikci/link) sayfaya/JSON'a GIRMEZ.
 *  - 'kargolandi'ya SADECE /kargo ucundan gecilir (takip kodu zorunlu) — tek yol.
 *  - 🔴 K284 (24 Agu 2026): 'havale-bekliyor' -> 'odendi' SADECE /havale-onay ucundan gecilir
 *    (DEKONT REFERANSI zorunlu) — /kargo ile BIREBIR AYNI SINIF. /durum bu gecisi HALA
 *    400 'odeme-durumu-elle-setlenemez' ile reddeder (K252 tahsilat yalani ilkesi KORUNUR);
 *    nasil takip kodsuz 'kargolandi' yazilamiyorsa, referanssiz 'odendi' de yazilamaz.
 *  - 🔴 K252 (20 Agu 2026): /durum'da OPERASYON ekseni ('uretimde' · 'tamamlandi' · 'iptal')
 *    her durumdan SERBEST ve GERI ALINABILIR; ODEME durumlari ELLE SETLENEMEZ (tahsilat
 *    yalani kapisi), tek istisna 'odendi'ye geri alma. Kural TEK KAYNAK: durumUcuKarari().
 *  - 'odendi'ye gecis REKLAM OLCUMU tetikler: Purchase, event_id = siparis_no
 *    (kart akisiyla ayni dedup anahtari). IDEMPOTENS uc katmanli — bkz. durumDegistir().
 *    ⚠️ Bu uctan GECMEYEN bir yedek yol kullanilirsa olcum de gitmez; teyidin normal yolu
 *    YONETIM SAYFASIDIR (yedek yolun adimlari git-disi isletme arsivindedir).
 */

import { SEMALAR } from "./semalar.js";
import { yeniSiparisNo } from "./siparis-no.js";
import { KONFIGURLAR } from "./konfigurlar.js";
import { golgeRaporu } from "./konfigur-golge.js";
import {
  epostaAkisi, onayEpostasiHtml, kargoEpostasiHtml,
} from "./eposta.js";
import { olcumGonder, olcumLog } from "./olcum.js";
// KANAL + REKLAM ATFI siniflamasi TEK KAYNAK (panel etiketi ile
// tools/kanal-kirilim-raporu.py kovasi AYNI fonksiyondan turer; ikinci sozluk YOK).
import { KANAL_SITE, WA_KANAL, kaynakOzeti } from "./kanal-sinif.mjs";

// ---- durum makinesi -----------------------------------------------------------
// 🔴 K252 (Okan karari, 20 Agu 2026 — tools/paket-siparis-durum-secici.md).
// ONCEKI HAL: `IZINLI` sirali ilerleme tablosuydu (odendi->uretimde->kargolandi->
// tamamlandi). 'uretimde'den cikisin TEK kapisi 'kargolandi' oldugu ve o da takip
// kodu istedigi icin KARGOSUZ TAMAMLAMA ULASILAMAZDI; yanlis isaretleme de geri
// alinamiyordu. Yeni hal uc eksene ayrilir:
//
//  (A) OPERASYON ekseni  — panelden SERBEST secilir, GERI ALINABILIR.
//  (B) 'kargolandi'      — ISTISNA, DEGISMEDI: /durum bu hedefi REDDEDER; tek yol
//                          firma+kod isteyen /kargo ucudur. Guvence korunur:
//                          TAKIP KODSUZ 'kargolandi' SATIRI OLUSAMAZ.
//  (C) ODEME ekseni      — elle setlenemez (elle 'odendi' = TAHSILAT YALANI).
//                          TEK istisna GERI ALMA: siparis zaten odenmisken
//                          operasyona alinmissa 'odendi'ye donulebilir.
//
// 🔴 IKIZ TABLO YOK: hem `POST /yonet/durum` ucu hem panelin sundugu secenek kumesi
// AYNI `durumUcuKarari()` fonksiyonundan TUREN tek karardir. Panele elle yazilmis
// ikinci bir liste, sessizce ayrisan ikinci bir hukum olurdu
// ([[ayni-alan-iki-hukum-biri-sessiz]]).
const TUM_DURUMLAR = new Set([
  "bekliyor", "odendi", "basarisiz", "incele", "havale-bekliyor",
  "uretimde", "kargolandi", "tamamlandi", "iptal",
]);

// (A) Operasyon ekseni: her mevcut durumdan secilebilir, geri alma DAHIL
// ('tamamlandi' -> 'uretimde' GECERLIDIR). 'iptal' de operasyondur ama ayri
// islenir (kendi uzerine gecis yok + panelde onay kutusu var).
const OPERASYON_DURUMLARI = ["uretimde", "tamamlandi"];

// (C) Odeme ekseni: bunlari ODEME SISTEMI yazar (iyzico donusu, havale onayi).
// Elle setlenmeleri tahsilat yalani uretir -> /durum ucundan REDDEDILIR.
const ODEME_DURUMLARI = ["bekliyor", "basarisiz", "havale-bekliyor", "incele", "odendi"];

// (C) TEK ISTISNA — 'odendi'ye GERI ALMA. Bu durumlardaki bir siparis zaten
// odenmisti (operasyona ancak odendikten sonra girer), dolayisiyla 'odendi'ye
// donmek YALAN URETMEZ; yanlis ilerletmeyi geri alir.
const ODENDI_GERI_ALMA = ["uretimde", "kargolandi", "tamamlandi"];

// Paneldeki is akisi sirasi. Liste sorgusu en yeni N siparisi secmeye devam eder;
// bu sira YALNIZ tarayicidaki goruntu katmaninda uygulanir.
const PANEL_GRUP_SIRASI = [
  "incele", "havale-bekliyor", "odendi", "uretimde", "kargolandi",
  "tamamlandi", "iptal", "bekliyor", "basarisiz",
];

/**
 * 🔴 TEK KAYNAK — `POST /yonet/durum` ucunun KABUL KARARI.
 * Saftir (I/O yok, yan etki yok): ayni girdi -> ayni karar. Ucun kendisi de,
 * panelin sundugu secenek kumesi de (bkz. `izinliHedefler`) BUNU cagirir.
 *
 * Doner: { ok: true } | { ok: false, hata: "<kod>" }
 * Hata kodlari yanit govdesine AYNEN gider — sebep GORUNUR olsun diye ayri
 * ayridir ("400" tek basina hangi kuralin reddettigini soylemez).
 */
function durumUcuKarari(mevcut, hedef) {
  if (!TUM_DURUMLAR.has(hedef)) { return { ok: false, hata: "bilinmeyen-durum" }; }
  // (B) 'kargolandi' — takip kodsuz kargolandi satiri OLUSAMAZ; /kargo ucu sart.
  if (hedef === "kargolandi") { return { ok: false, hata: "kargo-ucunu-kullan" }; }
  // Kendi uzerine gecis anlamsizdir; ayrica 'odendi'->'odendi' reddi, kart akisinin
  // Purchase olcumunu bu uctan TEKRARLATMAMA garantisinin 1. katmanidir
  // (bkz. durumDegistir icindeki uc katmanli idempotens notu).
  if (hedef === mevcut) { return { ok: false, hata: "gecersiz-gecis" }; }
  if (hedef === "iptal") { return { ok: true }; }                  // her durumdan iptal
  if (OPERASYON_DURUMLARI.includes(hedef)) { return { ok: true }; } // (A) serbest + geri alma
  // (C) Odeme ekseni: elle setlenemez. TEK istisna 'odendi'ye geri alma.
  if (hedef === "odendi" && ODENDI_GERI_ALMA.includes(mevcut)) { return { ok: true }; }
  if (ODEME_DURUMLARI.includes(hedef)) {
    return { ok: false, hata: "odeme-durumu-elle-setlenemez" };
  }
  return { ok: false, hata: "gecersiz-gecis" };
}

/**
 * Panelin sunacagi secenek kumesi — TURETILIR, elle YAZILMAZ.
 * `TUM_DURUMLAR` uzerinden `durumUcuKarari` ile suzulur; yani panelde gorunen her
 * secenek, ucun O AN kabul ettigi bir hedeftir. 'kargolandi' burada dogal olarak
 * ELENIR (uc onu reddeder) — panelde ayrica elle filtrelenmesine gerek YOKTUR.
 */
function izinliHedefler(mevcut) {
  return [...TUM_DURUMLAR].filter((h) => durumUcuKarari(mevcut, h).ok);
}

/**
 * `/kargo` ucunun gecis kurali — AYRI ve DAR tutulur (bilerek): 'kargolandi'
 * yalnizca uretimdeki bir siparise, firma+kod verildiginde yazilir. Bu kol K252'de
 * DEGISMEDI; operasyon ekseninin serbestligi buraya TASINMAZ.
 */
function kargoGecisiGecerli(mevcut) {
  return mevcut === "uretimde";
}

/**
 * `/havale-onay` ucunun gecis kurali — `kargoGecisiGecerli` ile BIREBIR AYNI SINIF
 * (K284, Okan karari 24 Agu 2026): AYRI ve DAR bir uc, tek bir mevcut durumdan tek bir
 * hedefe. 'odendi'ye SADECE 'havale-bekliyor'dan ve SADECE dekont referansi verildiginde
 * gecilir.
 *
 * 🔴 `durumUcuKarari()` KORUNDU: /durum kanit-siz 'odendi' gecisini 400 ile engelliyor.
 * /havale-onay (K284) tek ayri kanit kapisi; referanssiz tahsilat yine imkansiz.
 * K252 tahsilat yalani sagiyor; `ODENDI_GERI_ALMA` listesine dokunulmadi.
 */
function havaleGecisiGecerli(mevcut) {
  return mevcut === "havale-bekliyor";
}

// Dekont referansi uzunluk tavani — kargo firma/kodu ile AYNI (80). Bos deger REDDEDILIR:
// referanssiz 'odendi' tam da bu ucun yasakladigi seydir.
const DEKONT_REF_ENCOK = 80;

// ---- malzeme bazli baski fallback (filament rehberi degerleri; UYDURMA YOK) ---
// Kaynak: tools/paket-filament-rehberi.md isi dayanimi araliklari + gizli kayitlardaki
// ortak duvar/doluluk deseni ("wall line count 6-8, %15 infill"). Genel BASLANGIC onerisi;
// urune ozel oneri gizli .urun-kaynaklari.json'dan D1 baski kolonuna gelir (o varsa bu kullanilmaz).
const BASKI_FALLBACK = {
  "PLA": "Genel öneri: 0.2 mm katman · %15 doluluk · 4-5 duvar hattı · ısı dayanımı ~55-60°C (iç mekân).",
  "PETG": "Genel öneri: 0.2 mm katman · %15-20 doluluk · 4-6 duvar hattı · ısı dayanımı ~70-75°C (genel amaçlı).",
  "ASA": "Genel öneri: 0.2 mm katman · %20 doluluk · 5-6 duvar hattı · ısı dayanımı ~90-95°C (UV/su, dış mekân).",
  // ABS satisa 14 Agu'da geri acildi (kategori sizgeciyle). Metin BETIMSELDIR — fiyat/katsayi
  // TASIMAZ (para yolu secenekler.js FILAMENT_FARK'tir, panel metni oradan beslenmez).
  "ABS": "Genel öneri: 0.2 mm katman · %20 doluluk · 5-6 duvar hattı · ısı dayanımı ~95-100°C (ısınan ortam); doğrudan güneş altında uzun süreli kullanımda ASA daha iyidir.",
  "TPU": "Genel öneri: 0.2 mm katman · %15 doluluk · 3-4 duvar hattı · esnek; yavaş baskı önerilir.",
};

function baskiOnerisi(satir, d1Baski, sema) {
  // HAZIR TICARI MAL (satirda `tur:"fiziksel"`): BASKI YOK. Baski onerisi basmak — hatta
  // "Malzemeye uygun genel baskı ayarlarıyla üretilir." demek — bir boya kutusunu URETIYORMUS
  // gibi gosterir. Kosul TAM dize; `tur` yok/taninmaz ise bugunku kollar aynen isler.
  if (satir && satir.tur === "fiziksel") {
    return "Hazır ticari ürün — 3D baskı YOK, stoktan gönderilir.";
  }
  if (d1Baski && d1Baski.trim() && d1Baski.trim() !== "-") { return d1Baski.trim(); }
  if (sema && (sema.baski || sema.baskiIpucu)) { return sema.baski || sema.baskiIpucu; }
  // WHATSAPP KANALI (Ege): kalemin malzemesi/rengi ve olcusu sohbette konusulur, siparis
  // ucuna beyan olarak GELMEZ. Katalog kaydi varsa yukaridaki kollar zaten onu bastirdi;
  // buraya dusen kalem katalog disi ozel parcadir. Malzeme fallback'i basmak UYDURMA
  // olurdu ("%15 doluluk" diye bir karar verilmedi) -> nereye bakilacagi soylenir.
  if (satir && satir.kanal === WA_KANAL) {
    return "WhatsApp siparişi — üretim detayı müşteri sohbetinde (Ege) kayıtlı; " +
      "malzeme/ölçü beyanı bu uçtan gelmez.";
  }
  return BASKI_FALLBACK[satir.malzeme] || "Malzemeye uygun genel baskı ayarlarıyla üretilir.";
}

// ---- URETIM DOSYASI KAYNAKLARI (Drive baglantisi) -----------------------------
/**
 * 🔴 OLCULEN GERCEK (11 Agu 2026 — kod yazmadan ONCE olculdu, spec 1. adim):
 * Drive `fileId` degerleri YAPISAL BIR ALANDA DURMUYOR. Ne `siparisler` tablosunda
 * ne `urunler` tablosunda bir `drive`/`fileId` kolonu var; siparis kaydinda da yok.
 * Tek tasiyicilari, gizli `.urun-kaynaklari.json`'daki `baski` alaninin SERBEST
 * METNIDIR (o metin d1-sync ile D1 `urunler.baski` kolonuna gecer ve panelde zaten
 * "🖨️ baski onerisi" satiri olarak BASILIR — yani fileId bugun de EKRANDA, sadece
 * TIKLANAMAZ halde). Olcum: 25.971 kayitlik gizli dosyada `Drive fileId` etiketi
 * gecen kayit sayisi = 1, o kayitta cozulen fileId = 2. `drive.google` URL'i tum
 * kayitlarda 0 kez geciyor.
 *
 * DAYANIKLILIK SONUCU: bu ayristirma METIN AYRISTIRMASIDIR, alan okuma DEGIL. Not
 * bicimi degisirse baglanti SESSIZCE kaybolabilir — bu yuzden asagidaki sozlesme
 * FAIL-LOUD: sinif isareti (kanonik/yedek/arsiv) bulunup da fileId bulunamazsa kayit
 * `fileId:""` ile YINE DONER ve panel "baglanti uretilemedi" diye ACIKCA yazar.
 * Bos dizi donmesi = "notta hicbir kaynak isareti yok" demektir ve panel onu da
 * ACIKCA yazar. Bosluk birakmak, dosyanin OLMADIGINI degil OLCULEMEDIGINI gizlerdi.
 *
 * KALICI COZUM (KAPSAM DISI, mimara not): fileId'nin gizli kayitta YAPISAL bir alana
 * (`uretim_dosyalari: [{dosya, sinif, drive_file_id}]`) tasinmasi. O gun bu fonksiyon
 * yalnizca yedek yol olur; bugun TEK yoldur.
 */

/** Drive dosya adresi — TEK KAYNAK (ikizlenirse panel ile JSON sessizce ayrisir). */
const DRIVE_TABAN = "https://drive.google.com/file/d/";

// ---- DOSYA ADI KANONIK BICIMI (Okan kalemi 2 Eyl + BaBa hukmu 3 Eyl 2026) ------------
// Vaka: `crf-zincir-kılavuz-ara.STL` panelde "gecersiz dosya adi" ile dustu. Iki kusur:
//   ① uzanti: kabul harf-DUYARSIZ (.stl/.STL/.3mf/.3MF), R2 anahtarinda KUCUK harfe iner
//      (tools/stl-r2-yukle.py de uz.lower() yapar — iki yol ayni anahtari uretir);
//   ② Turkce/ASCII-disi: ı→i ğ→g ş→s ç→c ö→o ü→u İ→I (buyukleri de), diger ASCII-disi
//      → "-", bosluk → "-", ardisik "-" teklenir, bas/son "-" kirpilir; govde harfinin
//      buyuk/kucugu KORUNUR (yalniz uzanti kucultulur). R2 anahtari ASCII KALIR.
// 🔴 GUVENLIK KOLU GEVSEMEZ: ayirac (/ \), ust-dizin (..), kontrol karakteri, bos ad,
// uzantisiz ad HAM girdide (normalize'den ONCE) kural ADIYLA reddedilir; normalize
// SONRASI ad yine stlDosyaAdiGecersiz'den (mevcut son kapi, ASCII sinif) gecer.
// macOS dosya adini NFD verir (ğ = g + U+0306; birlesik isaret) → ONCE NFC, yoksa
// harita eslesmez ve ayni ad iki farkli anahtar uretirdi.
// 🔴 TEK KANONIK FONKSIYON, UC OKUYUCU (BaBa): R1 stlYukle (anahtar + 409) · R3
// driveKaynaklari (uretim notundaki ad — Turkce ad KIRPILMAZ, kanonik etiket) ·
// stlIndir/stlCikar liste karsilastirmasi (stlDosyaAdiAdaylari). Birini birakmak
// "yuklendi ama listede yok" / "panel yanlis dosya adi gosteriyor" sinifini acar.
// Bu blok BILEREK DRIVE_TABAN'in altinda: uretim-kaynak.mjs kaynak dilimi
// (DRIVE_TABAN .. "---- anahtar") bu fonksiyonlari da tasimali.
// Mutant capalari (urunler-panel.mjs I-M): TR_ASCII kolu · ayirac capali 2 satir ·
// toLowerCase · normalize("NFC") · URETIM_DOSYA_RX sinifi · uretimDosyaEtiketi donusu.
const IZINLI_UZANTI = /\.(stl|3mf)$/i;
const STL_DOSYA_ADI_RX = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,180}$/;

function stlDosyaAdiGecersiz(dosya) {
  return dosya.includes("/") || dosya.includes("\\") || dosya.includes("..") ||
    !IZINLI_UZANTI.test(dosya) || !STL_DOSYA_ADI_RX.test(dosya);
}

const TR_ASCII = { "ı": "i", "ğ": "g", "ş": "s", "ç": "c", "ö": "o", "ü": "u", "İ": "I",
                   "Ğ": "G", "Ş": "S", "Ç": "C", "Ö": "O", "Ü": "U" };

function kontrolKarakteriVar(s) {
  for (let i = 0; i < s.length; i++) {
    const k = s.charCodeAt(i);
    if (k < 32 || k === 127) { return true; }
  }
  return false;
}

/** -> {ad} (kanonik: ASCII, kucuk uzanti; R2 anahtarina giren ad) ya da {hata, kural}. */
function stlDosyaAdiNormalize(ham) {
  const s = typeof ham === "string" ? ham.normalize("NFC") : "";
  if (!s) { return { hata: "bos dosya adi", kural: "bos-ad" }; }
  if (kontrolKarakteriVar(s)) { return { hata: "kontrol karakteri yasak", kural: "kontrol-karakteri" }; }
  if (s.includes("..")) { return { hata: "ust-dizin (..) yasak", kural: "ust-dizin" }; } // CAPA:ayirac
  if (s.includes("/") || s.includes("\\")) { return { hata: "ayirac (/ veya \\) yasak", kural: "ayirac" }; } // CAPA:ayirac
  const uzM = IZINLI_UZANTI.exec(s);
  if (!uzM) { return { hata: "uzanti yalniz .stl/.3mf", kural: "uzanti" }; }
  const uzanti = uzM[0].toLowerCase();                          // ① .STL -> .stl
  // [^ -~] = yazdirilabilir ASCII disi (kontrol karakteri yukarida elendi -> kalan ASCII-disi)
  const kok = s.slice(0, s.length - uzanti.length)
    .replace(/[^ -~]/g, (c) => TR_ASCII[c] || "-")               // ② Turkce -> ASCII
    .replace(/\s+/g, "-").replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  if (!kok) { return { hata: "bos ad (yalniz uzanti)", kural: "bos-ad" }; }
  const ad = kok + uzanti;
  if (ad.length > 181) { return { hata: "ad cok uzun (tavan 181 karakter)", kural: "uzunluk" }; }
  if (stlDosyaAdiGecersiz(ad)) {                                 // son kapi: mevcut savunma AYNEN
    const yasak = ad.replace(/[A-Za-z0-9._-]/g, "");
    return { hata: yasak ? "izinsiz karakter: " + yasak.slice(0, 8)
                         : "ad harf/rakamla baslamali", kural: "karakter" };
  }
  return { ad: ad };
}

/** Liste karsilastirmasinda (indirme/cikarma) denenecek adlar: [kanonik] (+ HAM ad, eski
 *  anahtar duzenine — or. bosluklu ad — uyuyorsa). Ikisi de gecersizse [] -> cagiran 404. */
function stlDosyaAdiAdaylari(ham) {
  const adlar = [];
  const n = stlDosyaAdiNormalize(ham);
  if (!n.hata) { adlar.push(n.ad); }
  if (ham && !stlDosyaAdiGecersiz(ham) && !adlar.includes(ham)) { adlar.push(ham); }
  return adlar;
}

/** Uretim notundaki dosya ADI etiketi (R3): kanonik bicim; kanoniklesemeyen ad (or.
 *  `a..b.stl`) OLDUGU GIBI doner — etiket esc() ile basilir, href'e GIRMEZ. */
function uretimDosyaEtiketi(ham) {
  const n = stlDosyaAdiNormalize(ham);
  return n.hata ? ham : n.ad;
}

/**
 * fileId dilbilgisi. Google Drive id'si base64url alfabesindedir; uzunluk sinirini
 * DAR tutuyoruz (>=16) ki not icindeki siradan kelimeler yanlislikla id sayilmasin.
 * ⚠️ Bu regex ayni zamanda GUVENLIK KAPISIDIR: yakalanan deger href'e girer, yani
 * tirnak/bosluk/`javascript:` tasiyan bir dizi buradan GECEMEZ.
 */
const DRIVE_ID_RX = /Drive\s*file[ _-]?Id\s*[:=]?\s*([A-Za-z0-9_-]{16,200})/gi;

/** Uretim dosyasi adi (yalniz .stl/.3mf) — baglantinin NE oldugunu soyler.
 *  🔴 Sinif UNICODE (harf/rakam/birlesik isaret): insan notu Turkce yazar; salt-ASCII
 *  sinif `crf-zincir-kılavuz-ara.stl`i `lavuz-ara.stl` diye KIRPIYORDU (yanlis dosya adi
 *  = pahali uretim hatasi). Yakalanan ad uretimDosyaEtiketi() ile KANONIK basilir. */
const URETIM_DOSYA_RX = /([\p{L}\p{N}][\p{L}\p{N}\p{M}._-]*\.(?:stl|3mf))/giu;

/**
 * SINIF ISARETLERI — sira ONEMLI: metinde bir fileId'den ONCE gelen EN YAKIN isaret
 * o dosyanin sinifini belirler. `arsiv` EN TEHLIKELI sinif (yanlis dosyanin basilmasi
 * = pahali uretim hatasi), o yuzden ayri bir `basilmaz` bayragi tasir.
 */
const SINIF_ISARET = [
  { sinif: "arsiv", etiket: "ARŞİVDE — BASILMAZ", basilmaz: true,
    rx: /AR[SŞ][Iİ]VDE|BAS[Iİ]LMAZ|ESK[Iİ]\s+S[UÜ]R[UÜ]M/gi },
  { sinif: "yedek", etiket: "Yedek", basilmaz: false,
    rx: /YEDEK/gi },
  { sinif: "kanonik", etiket: "Kanonik — basılacak dosya", basilmaz: false,
    rx: /KANON[Iİ]K/gi },
];

/** Sinifi bilinmeyen kayit — SESSIZ "kanonik" VARSAYIMI YOK (yanlis dosya basilir). */
const SINIF_BELIRSIZ = { sinif: "belirsiz", etiket: "Sınıf belirsiz — nota bak", basilmaz: false };

/**
 * Uretim notundan (serbest metin) Drive kaynak listesi uretir.
 *
 * @param {string} metin — panelde basilan baski onerisinin AYNISI (ikiz kaynak YOK).
 * @returns {Array<{sinif,etiket,basilmaz,dosya,file_id,url}>}
 *   - `url` BOS ise: sinif isareti var ama fileId yok -> panel "baglanti uretilemedi" yazar.
 *   - Dizi BOS ise: notta hicbir kaynak/sinif isareti yok -> panel "kaynak yok" yazar.
 * Saf fonksiyon: istek/ortam gormez, yan etkisi yoktur (birim testi dogrudan cagirir).
 */
export function driveKaynaklari(metin) {
  // NFC: macOS'tan yapistirilan notta `ğ` = g + U+0306 olabilir; konumlar (konum/son)
  // hep bu NFC metin uzerinden olculur, karisik kaynak yok.
  const t = typeof metin === "string" ? metin.normalize("NFC") : "";
  if (!t) { return []; }

  // 1) Once fileId'ler: konumlari ve KAPLADIKLARI ARALIK. Aralik gerekli, cunku Drive
  //    id'si rastgele base64url'dur ve icinde "yedek"/"kanonik" gibi bir dizi GECEBILIR;
  //    o eslesme bir SINIF ISARETI degildir ve sayilirsa dosya YANLIS siniflanir.
  const idler = [];
  const rxId = new RegExp(DRIVE_ID_RX.source, DRIVE_ID_RX.flags);
  let mi;
  while ((mi = rxId.exec(t)) !== null) {
    idler.push({ konum: mi.index, son: mi.index + mi[0].length, id: mi[1] });
  }
  const idIcinde = (k) => idler.some((x) => k >= x.konum && k < x.son);

  // 2) Sinif isaretlerinin KONUMLARI (fileId govdesine dusenler ELENIR).
  const isaretler = [];
  for (const s of SINIF_ISARET) {
    const rx = new RegExp(s.rx.source, s.rx.flags);
    let m;
    while ((m = rx.exec(t)) !== null) {
      if (!idIcinde(m.index)) {
        isaretler.push({ konum: m.index, sinif: s.sinif, etiket: s.etiket, basilmaz: s.basilmaz });
      }
      if (m.index === rx.lastIndex) { rx.lastIndex++; }   // sifir uzunluk kilidi
    }
  }
  isaretler.sort((a, b) => a.konum - b.konum);

  const dosyalar = [];
  const rxD = new RegExp(URETIM_DOSYA_RX.source, URETIM_DOSYA_RX.flags);
  let md;
  while ((md = rxD.exec(t)) !== null) {
    dosyalar.push({ konum: md.index, ad: uretimDosyaEtiketi(md[1]) });
  }

  /** fileId'den ONCE gelen EN YAKIN isaret (yoksa BELIRSIZ — sessiz varsayim YOK). */
  const sinifiBul = (konum) => {
    let secili = null;
    for (const i of isaretler) { if (i.konum <= konum) { secili = i; } else { break; } }
    return secili || SINIF_BELIRSIZ;
  };
  /** fileId'den ONCE gelen EN YAKIN .stl/.3mf adi (yoksa ""). */
  const dosyaBul = (konum) => {
    let ad = "";
    for (const d of dosyalar) { if (d.konum <= konum) { ad = d.ad; } else { break; } }
    return ad;
  };

  // 3) Birlesim: her fileId, KENDINDEN ONCEKI en yakin isaretin sinifini alir.
  const cikti = [];
  const gorulen = new Set();
  for (const x of idler) {
    if (gorulen.has(x.id)) { continue; }            // ayni id iki kez yazilmissa tek satir
    gorulen.add(x.id);
    const s = sinifiBul(x.konum);
    cikti.push({
      sinif: s.sinif, etiket: s.etiket, basilmaz: s.basilmaz,
      dosya: dosyaBul(x.konum), file_id: x.id, url: DRIVE_TABAN + x.id + "/view",
    });
  }

  // 4) 🔴 FAIL-LOUD: fileId'i OLMAYAN sinif isaretleri de DONER. "ESKI SURUMLER ARSIVDE,
  //    BASILMAZ" gibi bir uyari notta VARSA ama baglantisi yoksa, panelin o satiri HIC
  //    gostermemesi Okan'a "arsiv surumu yok" der — oysa VAR ve BASILMAMALI. Bir isaretin
  //    "bolgesi" = kendisinden sonraki ILK isarete kadar; o bolgede fileId yoksa kayit
  //    baglantisiz doner.
  for (let i = 0; i < isaretler.length; i++) {
    const bas = isaretler[i].konum;
    const son = i + 1 < isaretler.length ? isaretler[i + 1].konum : t.length;
    if (idler.some((x) => x.konum >= bas && x.konum < son)) { continue; }
    if (cikti.some((c) => c.sinif === isaretler[i].sinif && !c.url)) { continue; }
    cikti.push({
      sinif: isaretler[i].sinif, etiket: isaretler[i].etiket, basilmaz: isaretler[i].basilmaz,
      dosya: "", file_id: "", url: "",
    });
  }
  return cikti;
}

// ---- anahtar ------------------------------------------------------------------

/**
 * Sabit-zamanli string esitligi (erken donus zamanlama sizintisini onler).
 *
 * 🔴 FAIL-CLOSED PRIMITIF: taraflardan biri string DEGILSE ya da BOS ise DAIMA false.
 * Eski hali `String(a || "")` ile ikisini de `""`ye cevirir ve `sabitEsit("", undefined)`
 * icin **true** donerdi. Tek basina zararsiz gorunur; ama `env.YONET_ANAHTAR` tanimsizken
 * bos sifreyle giris = YETKI demekti. O gun korumayi tutan sey yalnizca CAGRI SIRASIYDI
 * (yonet() secret'i once kontrol ediyordu). Koruma cagri sirasina birakilmaz — primitifin
 * KENDISI kapali olmali. (Olculdu: curutucunun "secret kapisini giris POST'undan sonraya
 * al" mutanti, bu satir duzelmeden bos sifreye 200 + yetki veriyordu.)
 *
 * 🔴 TUR SAYISI IKINCI ARGUMANDAN BAGIMSIZ (5 Agu 2026 onarimi). Karsilastirma uzunluk
 * esitsizliginde ARTIK ERKEN DONMEZ. Onceki halde esit olmayan uzunlukta HIC tur
 * calismiyordu; yani calisan tur sayisi "verilen deger ikinci argumanla ayni uzunlukta
 * mi" sorusunun CEVABIYDI ve bu uc anahtarsiz cagriya aciktir (olculdu: ayni verilen
 * deger icin 8 tur / 0 tur). Bugun tur sayisi `max(TABAN, |a|, |b|)`; uzunluk farki
 * DALLANMAZ, tek bir sayiya (`fark`) katlanir. Ikinci argumanin uzunlugu TABAN'i
 * asmadigi surece tur sayisi ondan hic etkilenmez — sinir kodda SABITTIR, yorumda degil.
 * Nobetci: shop/test/kabul.js C21e + tools/yonet-cerez-mutasyon.py M27.
 */
const SABIT_ESIT_TABAN_TUR = 256;

/**
 * Calistirilan tur SAYACI — OLCUM YUZEYI, davranisin parcasi DEGIL. Yukaridaki iddia
 * ("tur sayisi ikinci argumana bakmaz") duvar saatiyle olculseydi CI'da gurultulu ve
 * yanlis-kirmizi olurdu; sayac onu DETERMINISTIK olcturur. Yetki karari bu degere
 * HICBIR yerde bakmaz.
 */
export const SABIT_ESIT_OLCUM = { tur: 0 };

export function sabitEsit(a, b) {
  if (typeof a !== "string" || typeof b !== "string") { return false; }
  if (a.length === 0 || b.length === 0) { return false; }
  const turSayisi = Math.max(SABIT_ESIT_TABAN_TUR, a.length, b.length);
  let fark = a.length ^ b.length;
  let tur = 0;
  for (let i = 0; i < turSayisi; i++) {
    fark |= a.charCodeAt(i % a.length) ^ b.charCodeAt(i % b.length);
    tur++;
  }
  SABIT_ESIT_OLCUM.tur += tur;
  return fark === 0;
}

// ---- oturum cerezi ------------------------------------------------------------
// TEK KAYNAK: ad/omur/bayraklar asagidaki uc sabitten turer. Ikizlenirse ("pruvo_yonet"
// bir yerde, "pruvo-yonet" baska yerde) kapi SESSIZCE ayrisir.

const CEREZ_ADI = "pruvo_yonet";
const CEREZ_OMUR_SN = 12 * 60 * 60;   // 12 saat
/**
 * Bayraklarin hepsi ZORUNLU:
 *  HttpOnly        — sayfa JS'i okuyamaz (XSS anahtari calamaz),
 *  Secure          — yalniz TLS uzerinde gider,
 *  SameSite=Strict — capraz-siteden gelen gezinmede GONDERILMEZ (Referer/CSRF ekseni kapali),
 *  Path=/          — hem /api/shop/yonet paneli hem /api/shop/yonet/stl indirmeleri kapsanir.
 */
const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Strict; Path=/";

/** Oturum cerezini KURAN Set-Cookie dizesi (saf: yan etkisi yok, istek gormez). */
export function yonetCereziKur(anahtar) {
  return CEREZ_ADI + "=" + encodeURIComponent(anahtar == null ? "" : String(anahtar)) +
    "; " + CEREZ_BAYRAK + "; Max-Age=" + CEREZ_OMUR_SN;
}

/** Oturum cerezini SILEN Set-Cookie dizesi (cikis; ayni bayraklar, Max-Age=0). */
export function yonetCereziSil() {
  return CEREZ_ADI + "=; " + CEREZ_BAYRAK + "; Max-Age=0";
}

/**
 * Istekteki yonetim cerezinin DEGERI (yoksa ""). Cerez ADI TAM esitlenir.
 * ⚠️ `cookieBasligi.includes(anahtar)` gibi naive bir arama, `baska=pruvo_yonet=<anahtar>`
 * seklinde BASKA bir cerezin DEGERI icine gomulen anahtari da gecerli sayardi; ayni sekilde
 * `pruvo_yonet_x=<anahtar>` yakin-iskasini da. Ad esitligi bu iki yolu da kapatir.
 */
export function yonetCereziOku(request) {
  const ham = (request && request.headers && request.headers.get("Cookie")) || "";
  if (!ham) { return ""; }
  for (const parca of ham.split(";")) {
    const esit = parca.indexOf("=");
    if (esit < 0) { continue; }
    if (parca.slice(0, esit).trim() !== CEREZ_ADI) { continue; }
    let deger = parca.slice(esit + 1).trim();
    if (deger.length >= 2 && deger.charAt(0) === '"' &&
        deger.charAt(deger.length - 1) === '"') {
      deger = deger.slice(1, -1);
    }
    try { return decodeURIComponent(deger); } catch (e) { return deger; }
  }
  return "";
}

/**
 * Anahtar gecerli mi? Secret tanimsizsa DAIMA false (ozellik kapali; 404).
 * IKI TASIYICI: `X-Yonet-Anahtar` basligi (tools/yazdir.py + makine istemcileri) ve
 * `pruvo_yonet` HttpOnly cerezi (tarayici — cerez hem fetch'te hem <a href> gezinmesinde
 * kendiliginden gider; sorgu parametresinin var olma sebebi buydu, cerez onu IKAME EDER).
 * ❌ `url.searchParams.get("anahtar")` KALDIRILDI (sizinti). `url` imzada DURUYOR ama
 * yetki icin OKUNMUYOR — cagri yerleri degismesin diye.
 */
function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {
    return true;
  }
  return sabitEsit(yonetCereziOku(request), env.YONET_ANAHTAR);
}

/**
 * EGE (WhatsApp botu) ANAHTARI — YALNIZ /wa-siparis ucunu acar. EN AZ YETKI:
 * Ege AYRI bir worker'dir (pruvo-bot deposu, ayri secret seti). Ona YONET_ANAHTAR'i
 * vermek panelin TAMAMINI acardi: butun siparislerin PII'si (/liste), durum degistirme,
 * iptal, uretim dosyasi indirme. Bir siparis YAZMAK icin bunlarin hicbiri gerekmiyor.
 * Bu yuzden ayri, TEK UCA yetkili bir secret tanimlanir:
 *     npx wrangler secret put EGE_ANAHTAR
 * Tanimli DEGILSE bu kol tamamen kapalidir (fail-closed) ve /wa-siparis yalnizca
 * YONET_ANAHTAR ile calisir — yani "acik uc" hicbir konfigurasyonda olusmaz.
 *
 * 🔴 YALNIZ BASLIK (`X-Ege-Anahtar`) — QUERY PARAM YOLU KAPALI. Onceden `?ege_anahtar=`
 * de kabul ediliyordu; bu anahtari Cloudflare erisim loglarina, referrer'a ve proxy
 * kayitlarina DUZ METIN olarak dusuruyordu (URL'ler loglanir, basliklar loglanmaz).
 * Uc yalnizca sunucudan-sunucuya cagrilir (Ege worker'i), yani tarayici adres cubugu
 * gibi baslik konulamayan bir cagiran YOKTUR -> param yolunun mesru kullanicisi yok.
 * `url` parametresi bilerek okunmuyor; imzadan da dusuruldu ki geri gelmesin.
 */
function egeAnahtarGecerli(request, env) {
  if (!env.EGE_ANAHTAR) { return false; }
  const verilen = request.headers.get("X-Ege-Anahtar") || "";
  return sabitEsit(verilen, env.EGE_ANAHTAR);
}

// ---- yanit yardimcilari (CORS YOK — yonetim same-origin) ----------------------

// ---- KANAL ayraci -------------------------------------------------------------
// 🔴 KANAL_SITE / WA_KANAL burada TANIMLI DEGIL, ./kanal-sinif.mjs'ten IMPORT edilir
// (yukari bak). Daha once bu iki sabit burada elle yaziliydi; kanal kirilim raporu
// da ayni iki degeri kendi tarafinda tanimlayacak olsaydi iki kopya sessizce
// ayrisabilirdi ([[ayni-alan-iki-hukum-biri-sessiz]]). Tek kaynak: kanal-sinif.mjs.

/**
 * OPSIYONEL KOLON MERDIVENI (index.js sepetiFiyatla'daki desenin AYNISI).
 *
 * `kanal`/`dis_no` kolonlari canli D1'de ancak `python3 tools/d1-sync.py --sema` kosunca
 * olusur. Kolonlu bir SELECT o ALTER'dan ONCE "no such column" ile PATLAR. Bu sarmalayici
 * OKUMA yollarini (liste, siparisGetir) o pencerede AYAKTA tutar: kolonlu sorgu patlarsa
 * AYNI sorgu kolonsuz tekrarlanir, alanlar undefined kalir ve cagiran bugunku davranisina
 * duser. Yani panelin GET/render tarafi goc kosmadan da BOZULMAZ.
 * ⚠️ YAZMA yolunda (/wa-siparis) KULLANILMAZ: orada fail-CLOSED 503 doner — kanal ayraci
 * OLMADAN yazilan bir WhatsApp siparisi panelde SITE siparisi gibi gorunurdu (sessiz hata).
 * Yalniz "no such column" yutulur; baska her hata (D1 down, bind hatasi) YUKARI FIRLAR.
 */
async function kolonMerdiveni(kolonlu, kolonsuz) {
  try {
    return await kolonlu();
  } catch (e) {
    if (!/no such column/i.test(String((e && e.message) || e))) { throw e; }
    return await kolonsuz();
  }
}

/**
 * TABLO MERDIVENI — `urun_kaynak` OPSIYONELDIR (bkz. kolonMerdiveni gerekcesi).
 *
 * Tablo canli D1'de ancak `python3 tools/d1-kaynak-sync.py --sema` kosunca olusur;
 * o ana kadar SELECT "no such table" ile PATLAR ve TUM panel listesi 500 donerdi.
 * Yalniz "no such table" yutulur -> alan bos kalir, panel "kaynak kaydı yok" YAZAR
 * (sessiz bosluk DEGIL). Baska her hata (D1 down, bind hatasi) YUKARI FIRLAR.
 */
async function tabloMerdiveni(tablolu, tablosuz) {
  try {
    return await tablolu();
  } catch (e) {
    if (!/no such table/i.test(String((e && e.message) || e))) { throw e; }
    return await tablosuz();
  }
}

/**
 * URETICI KAYNAK LINKI SUZGECI (SAF — testler burayi dogrudan cagirir).
 *
 * 🔒 GIZLILIK: bu deger yalniz YONETIM panelinde gorunur; `urun_kaynak` tablosunu
 * musteriye donen hicbir yol (site/shop/Ege) sorgulamaz. Tabloya YALNIZ `link` tasinir —
 * tasarimci/uyelik/lisans/alis fiyati TASINMAZ (sizma yuzeyi buyutulmez).
 *
 * FAIL-CLOSED: yalniz `https://` ile baslayan mutlak adres gecer. `javascript:`, `data:`,
 * bagil yol ya da tirnak tasiyan bozuk deger BOS DONER -> panel "kaynak kaydı yok" yazar
 * ve HAM DEGER HTML'e HIC girmez (esc() ikinci savunma olarak yine uygulanir).
 */
export function kaynakLinkSuz(deger) {
  return (typeof deger === "string" && /^https:\/\//i.test(deger)) ? deger : "";
}

function yjson(veri, kod) {
  return new Response(JSON.stringify(veri), {
    status: kod || 200,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
function yon404() { return yjson({ hata: "bulunamadi" }, 404); }

// ---- /liste -------------------------------------------------------------------

async function liste(env, url) {
  const durum = url.searchParams.get("durum") || "";
  const limit = Math.min(200, Math.max(1, parseInt(url.searchParams.get("limit") || "50", 10) || 50));
  // Ana siteye kalici urun sayfasi linki (yonetim ekraninda kalem basligi buraya tiklanir).
  const siteUrl = ((env && env.SITE_URL) || "https://pruvo3d.com").replace(/\/$/, "");
  const TABAN =
    "SELECT id, siparis_no, tarih, durum, tutar_kurus, kargo_kurus, kdv_kurus, odeme_yontemi," +
    " urunler, kargo_firma, kargo_kodu, durum_gecmisi," +
    // `atif` (reklam atfi JSON): panelin "Kaynak" satiri buradan turer. Kolon GOC
    // KOLONU DEGIL — d1-sync GOC_KOLON_SIPARIS'te DEFAULT '' ile tanimli, yani
    // siparisler tablosu varsa bu kolon da vardir (merdiven gerekmez).
    // 🔒 HAM DEGER PANELE GITMEZ: asagida kaynakOzeti() beyaz-listeden gecirir —
    // ga_client_id/fbp/fbc /liste JSON'una HIC girmez (bkz. kanal-sinif.mjs gizlilik).
    " atif," +
    " musteri_ad, musteri_tel, musteri_eposta, musteri_adres, musteri_notu";
  // kanal/dis_no OPSIYONEL (goc kosmadiysa yok) -> merdiven; yoksa alanlar undefined kalir
  // ve asagida 'site'/'' varsayilanina duser (bugunku ekranin AYNISI).
  const kur = (alanlar) => {
    const secim = alanlar + " FROM siparisler";
    return durum
      ? env.KATALOG.prepare(secim + " WHERE durum = ? ORDER BY id DESC LIMIT ?").bind(durum, limit)
      : env.KATALOG.prepare(secim + " ORDER BY id DESC LIMIT ?").bind(limit);
  };
  const sonuc = await kolonMerdiveni(
    () => kur(TABAN + ", kanal, dis_no").all(),
    () => kur(TABAN).all());
  const satirlar = sonuc.results || [];

  // Satir urun id'lerinin D1 baski/parametrik kayitlarini topla (baski fisi zenginlestirme).
  const idKume = new Set();
  const cozulmus = satirlar.map((s) => {
    let urunler = [];
    try { urunler = JSON.parse(s.urunler) || []; } catch (e) { urunler = []; }
    for (const k of urunler) { if (k && k.id) { idKume.add(k.id); } }
    return { satir: s, urunler };
  });
  const baskiMap = new Map();
  if (idKume.size) {
    const idler = [...idKume];
    const yertut = idler.map(() => "?").join(",");
    const ur = await env.KATALOG.prepare(
      "SELECT id, baski, parametrik FROM urunler WHERE id IN (" + yertut + ")"
    ).bind(...idler).all();
    for (const u of (ur.results || [])) { baskiMap.set(u.id, u); }
  }

  // URETICI KAYNAK LINKI — AYRI tablo (`urun_kaynak`), TEK toplu sorgu (kalem basina
  // sorgu ATILMAZ: 50 siparislik listede N+1 olurdu). Tablo/satir yoksa alan bos kalir.
  // 🔒 Bu tabloyu YALNIZ bu yonetim ucu okur; `urunler` tablosuna kaynak kolonu EKLENMEDI
  // cunku o tabloyu Ege (WhatsApp botu) okuyor — tedarikci linki musteriye sizardi.
  const kaynakMap = new Map();
  if (idKume.size) {
    const idler = [...idKume];
    const yertut = idler.map(() => "?").join(",");
    const kr = await tabloMerdiveni(
      () => env.KATALOG.prepare(
        "SELECT id, link FROM urun_kaynak WHERE id IN (" + yertut + ")").bind(...idler).all(),
      () => ({ results: [] }));
    for (const x of (kr.results || [])) { kaynakMap.set(x.id, x.link); }
    // T2 — panel-dogumlu kaynak (panel_kaynak) SYNC degerini GOLGELER: satir varsa o
    // kazanir; link='' (cikarildi) suzgecten bos doner ve ekran "kaynak kaydı yok" yazar.
    const pr = await tabloMerdiveni(
      () => env.KATALOG.prepare(
        "SELECT id, link FROM panel_kaynak WHERE id IN (" + yertut + ")").bind(...idler).all(),
      () => ({ results: [] }));
    for (const x of (pr.results || [])) { kaynakMap.set(x.id, x.link); }
  }

  const cikti = cozulmus.map(({ satir: s, urunler }) => {
    const kalemler = urunler.map((k, i) => {
      const ur = baskiMap.get(k.id) || {};
      const sema = SEMALAR.get(k.id);
      const parametrik = !!(k.parametreler || ur.parametrik);
      const kayit = {
        kalem: i,
        id: k.id,
        baslik: k.baslik || "",
        malzeme: k.malzeme || "",
        renk: k.renk_ozel || k.renk || "",
        // Hazir ticari mal isareti — beyan alanlari BOS oldugunda "veri kayip" mi yoksa
        // "secim yok" mu oldugunu ekran bu alandan bilir (bkz. baskiOnerisi + satir cizici).
        tur: k.tur === "fiziksel" ? "fiziksel" : "",
        adet: k.adet || 1,
        parametrik: parametrik,
        parametre_detay: k.parametre_detay || "",
        baski_oneri: baskiOnerisi(k, ur.baski, sema),
        // URETIM DOSYASI KAYNAKLARI (Drive). Ayristirma girdisi, panelde basilan
        // metnin TA KENDISIDIR (asagida ayrica hesaplanmaz) — ikiz kaynak olsaydi
        // not degistiginde ekran ile baglanti sessizce ayrisirdi.
        uretim_kaynaklari: [],
        // Yonetim ekraninda kalem basligi buraya tiklanir (urun sayfasi, ana site).
        // WhatsApp kaleminde kalemin KENDI linki (k.url) varsa O kullanilir: o kalem
        // katalog id'siyle gelmeyebilir, /urun/<id>/ adresi 404 olurdu. Link YAZILIRKEN
        // dogrulanir (yalniz https://); burada ikinci savunma olarak yine suzulur.
        urun_url: (typeof k.url === "string" && /^https:\/\//i.test(k.url))
          ? k.url
          : siteUrl + "/urun/" + encodeURIComponent(k.id || "") + "/",
        // URETICI KAYNAGI (platform sayfasi) — YALNIZ link. Tasarimci/uyelik/lisans/alis
        // fiyati BILINCLI OLARAK TASINMAZ; link zaten kaynaga goturur.
        kaynak_link: kaynakLinkSuz(kaynakMap.get(k.id)),
      };
      kayit.uretim_kaynaklari = driveKaynaklari(kayit.baski_oneri);
      // Yerel yazdir.py + tarayici indirme uclari (anahtar sayfa URL'inden eklenir).
      if (parametrik) {
        // Sari: siparisteki parametrelerle derleyiciden uretim.
        kayit.stl_ucu = "/api/shop/yonet/stl?siparis_no=" +
          encodeURIComponent(s.siparis_no) + "&kalem=" + i;
      } else {
        // Normal: COK-PARCA — once liste, sonra parca basina /stl?id=&dosya=.
        kayit.stl_liste_ucu = "/api/shop/yonet/stl-liste?id=" + encodeURIComponent(k.id);
      }
      return kayit;
    });
    let gecmis = [];
    try { gecmis = JSON.parse(s.durum_gecmisi) || []; } catch (e) { gecmis = []; }
    return {
      siparis_no: s.siparis_no,
      tarih: s.tarih,
      durum: s.durum,
      // KANAL: kolon yoksa (goc oncesi) ya da bos gelirse 'site' — mevcut satirlarin
      // TAMAMI site siparisidir, ekran bugunku gibi rozet basmaz.
      kanal: s.kanal || KANAL_SITE,
      // 🔴 KAYNAK OZETI (kanal + reklam atfi) — kartin "Kaynak" satiri. HAM `s.kanal`
      // verilir, YUKARIDAKI 'site' VARSAYILANI UYGULANMADAN: varsayilan uygulansaydi
      // "kolon yok" hali "site" halinden ayirt edilemez olurdu ve ekran olculmemis bir
      // seyi olculmus gibi gosterirdi. Ozet zaten kendi icinde "kanal ölçülemedi" der.
      // Siniflama TARAYICIDA DEGIL BURADA yapilir: panel karar vermez, karari basar.
      kaynak: kaynakOzeti(s.kanal, s.atif),
      // Ege'nin KENDI numarasi (PR-yyMMdd-HHmmss, sonek YOK) — Sheet kaydiyla eslesme icin.
      // Panel ID'si ile KARISTIRILMAZ: panelin siparis_no'su yine bu tabloda uretilir.
      dis_no: s.dis_no || "",
      odeme_yontemi: s.odeme_yontemi,
      tutar_kurus: s.tutar_kurus,
      kargo_kurus: s.kargo_kurus,
      kdv_kurus: s.kdv_kurus,
      kargo_firma: s.kargo_firma || "",
      kargo_kodu: s.kargo_kodu || "",
      durum_gecmisi: gecmis,
      // 🔴 TURETILMIS KUME (K252) — panel bunu OLDUGU GIBI basar. Elle yazilmis
      // ikinci liste YOK: kaynak `durumUcuKarari`, yani ucun kendi kabul kumesi.
      izinli_gecisler: izinliHedefler(s.durum),
      musteri: { ad: s.musteri_ad, tel: s.musteri_tel, eposta: s.musteri_eposta,
                 adres: s.musteri_adres },
      musteri_notu: s.musteri_notu || "",
      kalemler: kalemler,
      // Yerel araç (Faz 2) komutu — sayfadaki "kopyala" düğmesi bunu panoya yazar.
      yazdir_komut: "python3 tools/yazdir.py " + s.siparis_no,
    };
  });
  return yjson({ siparisler: cikti }, 200);
}

// ---- durum gecmisi yardimci ---------------------------------------------------

/**
 * Durum gecmisine tek kayit dusurur. TEK KAYNAK: kart akisi (index.js donus()) da BUNU
 * cagirir — iki akis ayni iz bicimini uretsin diye (ikinci kopya YOK; bicim ayrisirsa
 * tools/olculmemis-siparis.py sessizce yanlislanirdi).
 */
export function gecmiseEkle(mevcutJson, hedef, ekstra) {
  let g = [];
  try { g = JSON.parse(mevcutJson) || []; } catch (e) { g = []; }
  if (!Array.isArray(g)) { g = []; }
  const kayit = { d: hedef, z: new Date().toISOString() };
  // "o": 1 -> bu geciste Purchase olcumu DENENDI (tetiklendi). Idempotens izi; asagida okunur.
  // ⚠️ ANLAMI "DENENDI", "ULASTI" DEGIL: iz, gonderim SONUCUNDAN once (ayni atomik UPDATE
  // icinde) yazilir; olcum fire-and-forget'tir. Meta 400 dondurse, ag koparsa, secret
  // tanimsiz olsa bile iz "1" kalir. Teshis icin izin varligina DEGIL, Cloudflare Logs'taki
  // `olcum {...}` satirina bakilir (orada kod/events_received/fbtrace_id var).
  if (ekstra && ekstra.olcumDenendi) { kayit.o = 1; }
  // "pb" -> TARAYICI PURCHASE BILETI (shop/src/olcum-bilet.js). Tek kullanimliktir: donus
  // sayfasi bunu sunucuya gosterip yaktirmadan Purchase ATMAZ. AYNI atomik UPDATE icinde
  // yazilir (olcum izi "o" ile AYNI gerekce: ikinci UPDATE yaris penceresi acardi).
  // ⚠️ Bilet yalniz gecis GERCEKTEN olduysa (changes > 0) D1'e iner; cagiran, changes=0
  // halinde bileti donus URL'sine KOYMAMALIDIR — yoksa idempotent 2. callback tarayiciya
  // yakilabilir bilet verir ve mukerrer koruma coker.
  if (ekstra && ekstra.pikselBileti) { kayit.pb = String(ekstra.pikselBileti); }
  // "s" -> MAKINE-OKUNUR SEBEP. Bugunku tek uretici cron terk supurmesidir ("terk"):
  // musterinin acip terk ettigi odeme sayfasinin siparis satiri, iyzico `retrieve` ile
  // ODENMEDIGI DOGRULANDIKTAN sonra 'iptal'e cekilir. Sebep olmadan bu satirlar musterinin
  // vazgectigi gercek siparislerden AYIRT EDILEMEZDI (panel/rapor ikisini ayni gosterirdi).
  if (ekstra && ekstra.sebep) { kayit.s = String(ekstra.sebep); }
  g.push(kayit);
  if (g.length > 50) { g = g.slice(-50); } // sinirla (same-row buyumesin)
  return JSON.stringify(g);
}

/**
 * Bu siparis icin Purchase olcumu DAHA ONCE bu uctan DENENDI mi? (durum_gecmisi izi)
 * "Denendi" = gonderim tetiklendi; ULASTIGINI GARANTI ETMEZ (bkz. gecmiseEkle notu).
 * Amaci yalnizca TEKRARI onlemek — "Meta aldi" teshisi icin KULLANILMAZ.
 * Not: gecmis 50 kayitta kirpilir; pratikte bir siparis 50 durum degisimi yasamaz.
 * Kirpilma olsa bile gecis CAS'tir (asagi bak): ayni anda iki istek gelse yalniz biri
 * changes>0 alir. ⚠️ K252'den sonra 'odendi' hedefi GERI ALMA yoluyla da kabul edildigi
 * icin "tekrar zaten mumkun degil" DEMEK ARTIK DOGRU DEGIL — tekrari asil durduran
 * BU IZDIR, o yuzden 50 kayit kirpilmasi bir risk penceresidir.
 */
function olcumDenendiMi(gecmisJson) {
  let g = [];
  try { g = JSON.parse(gecmisJson) || []; } catch (e) { g = []; }
  if (!Array.isArray(g)) { return false; }
  return g.some((k) => k && k.o === 1);
}

async function siparisGetir(env, siparisNo) {
  const TABAN =
    "SELECT siparis_no, tarih, durum, durum_gecmisi, urunler, tutar_kurus, kargo_kurus," +
    " kdv_kurus, odeme_yontemi, atif," +
    " musteri_ad, musteri_eposta, musteri_adres";
  const kur = (alanlar) => env.KATALOG.prepare(
    alanlar + " FROM siparisler WHERE siparis_no = ?").bind(siparisNo);
  // `kanal` opsiyoneldir (goc kosmadiysa yok): merdiven. Kolon yoksa s.kanal undefined
  // kalir -> asagidaki olcum kapisi bugunku gibi ACIK olur (davranis degismez).
  return kolonMerdiveni(
    () => kur(TABAN + ", kanal").first(),
    () => kur(TABAN).first());
}

/** ISO tarihi -> saniye damgasi. Bozuk/bossa 0 (cagiran "simdi"ye duser). */
function isoSaniye(iso) {
  const t = Date.parse(String(iso || ""));
  return Number.isFinite(t) ? Math.floor(t / 1000) : 0;
}

// ---- /durum -------------------------------------------------------------------

/**
 * HAVALE CIROSU OLCUMU (mimar acigi 3).
 *
 * NEDEN: havale ile odenen siparis /donus akisindan GECMEZ (iyzico yok) -> daha once
 * hicbir Purchase olayi gitmiyordu. Sonuc: havale cirosu Meta'da ve GA4'te YOKTU; Meta
 * "bu reklam satmiyor" diye YANLIS ogreniyordu (kart-disi ciro gorunmez).
 *
 * DEDUP: event_id = siparis_no — kart akisiyla AYNI anahtar (olcum.js satinAlmaOlayi).
 *
 * 🔒 IP/UA GONDERILMEZ (bilincli): bu istek OKAN'IN yonetim tarayicisindan gelir; buradaki
 * IP/UA musteriye ait DEGILDIR. Yanlis kisiyi eslestirmek, hic eslestirmemekten kotudur.
 * (Musterinin rizali fbp/fbc'si atif kaydindan zaten gider — /baslat'ta yakalanmisti.)
 *
 * event_time = SIPARIS TARIHI (odemenin gercek ani; havalede musteri parayi siparis
 * gunu gonderir, Okan dekontu sonra gorur). Meta'nin 7 gunluk geriye-donuk penceresini
 * asan olayi olcum.js atlar + loglar.
 */
function havaleOlcumu(env, ctx, s) {
  const zaman = isoSaniye(s.tarih);
  return olcumGonder(env, ctx, s, undefined, {
    kaynak: "havale",
    event_time: zaman > 0 ? zaman : Math.floor(Date.now() / 1000),
    // istemci YOK — yukaridaki gerekce.
  });
}

/**
 * 🔴 PURCHASE OLCUM KARARI — TEK KAYNAK (saf; I/O yok).
 * `durumDegistir` (/durum geri alma kolu) ve `havaleOnay` (/havale-onay) AYNI kurali
 * kullanir. K284'e kadar bu kural yalniz durumDegistir govdesinde yaziliydi; ikinci uc
 * acilirken KOPYALANSAYDI iki hukum sessizce ayrisirdi ([[ayni-alan-iki-hukum-biri-sessiz]])
 * — or. kanal kapisi bir uctan kaldirilsa oteki uc onu sessizce uygulamaya devam ederdi.
 *
 * Doner: { siteKanali, olcumluGecis, zatenDenendi, olcumTetikle }
 *  - siteKanali   : KANAL kapisi (WhatsApp cirosu site ROI raporunu sismesin).
 *                   `kanal` kolonu yoksa (goc kosmadi) undefined -> kapi ACIK (geriye uyum).
 *  - zatenDenendi : durum_gecmisi'ndeki KALICI IZ ("o":1) — 3. idempotens katmani.
 */
function olcumKarari(s, hedef) {
  const siteKanali = !s.kanal || s.kanal === KANAL_SITE;
  const olcumluGecis = (hedef === "odendi") && siteKanali;
  const zatenDenendi = olcumDenendiMi(s.durum_gecmisi);
  return { siteKanali, olcumluGecis, zatenDenendi,
           olcumTetikle: olcumluGecis && !zatenDenendi };
}

async function durumDegistir(request, env, ctx) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  const siparisNo = govde && typeof govde.siparis_no === "string" ? govde.siparis_no : "";
  const hedef = govde && typeof govde.durum === "string" ? govde.durum : "";
  if (!siparisNo || !hedef) { return yjson({ hata: "eksik-alan" }, 400); }
  if (!TUM_DURUMLAR.has(hedef)) { return yjson({ hata: "bilinmeyen-durum" }, 400); }
  // 🔴 'kargolandi' REDDI BURADA DEGIL, `durumUcuKarari()` icindedir — TEK KAYNAK.
  // Onceki turda burada AYRICA bir erken `return` vardi ve kural IKI YERDE yaziliydi;
  // M1 (darlik) mutanti bu yuzden KACTI: `durumUcuKarari` icindeki reddi oldurmek
  // davranisi degistirmiyordu, cunku erken return hala 400 basiyordu. Yani ikiz kural
  // kabul testini KOR ediyordu ([[ayni-alan-iki-hukum-biri-sessiz]]).
  // ⚠️ Sira degisti: artik siparis ONCE okunur, yani var olmayan numara icin
  // 'kargolandi' hedefi de 404 'siparis-yok' doner — diger TUM hedeflerle AYNI
  // davranis (varlik sizintisi ACILMAZ, tam tersine tutarli hale gelir).
  const s = await siparisGetir(env, siparisNo);
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  // 🔴 TEK KAYNAK: panelin sundugu kume de AYNI fonksiyondan turer (izinliHedefler).
  const karar = durumUcuKarari(s.durum, hedef);
  if (!karar.ok) {
    return yjson({ hata: karar.hata, mevcut: s.durum, hedef: hedef }, 400);
  }
  // --- Purchase olcumu karari (yalniz 'odendi'ye gecis) --------------------------
  // IDEMPOTENS — UC KATMAN, hicbirine TEK basina guvenilmez:
  //  1) DURUM MAKINESI: K252'den sonra 'odendi' hedefi YALNIZ GERI ALMA olarak
  //     {uretimde, kargolandi, tamamlandi}'dan kabul edilir (odeme ekseninin diger
  //     durumlarindan 400); kendi uzerine gecis ('odendi'->'odendi') GECERSIZDIR (400)
  //     -> kart akisinin gonderdigi olay buradan DOGRUDAN tekrarlanamaz.
  //     ⚠️ K252 (20 Agu 2026) bu katmani TEK BASINA yeterli olmaktan cikardi: geri
  //     alma yolu 'odendi'->'uretimde'->'odendi' turunu MUMKUN kilar. O turda ikinci
  //     Purchase'i durduran 3. KATMANDIR (kalici iz) ve o iz kart akisinda da
  //     yaziliyor (shop/src/index.js donus(): gecmiseEkle(..., {olcumDenendi:true}))
  //     — yani kart siparisi operasyona alinip geri dondurulse bile `zatenDenendi`
  //     DOGRU cikar ve olcum TEKRARLANMAZ.
  //  2) CAS (compare-and-swap): UPDATE ... WHERE durum = <okunan durum>. Iki es zamanli
  //     istek gelse yalniz BIRI changes>0 alir; olcum yalniz o daldan tetiklenir.
  //  3) KALICI IZ: durum_gecmisi'ne {"o":1} yazilir; ayni UPDATE icinde (atomik).
  //     Iz varsa bir daha DENENMEZ — elle iki kez 'odendi' denenirse de tek olay.
  //     ⚠️ Iz "denendi" demek, "Meta aldi" DEMEK DEGIL (bkz. gecmiseEkle/olcumDenendiMi).
  // Meta event_id ile ayrica dedup yapar; o DORDUNCU ag, tek savunma DEGIL.
  //
  // 🔴 DORDUNCU KAPI — KANAL (1 Agu 2026, WhatsApp siparis ucu): reklam olcumu SITE
  // siparisleri icindir. WhatsApp siparisi tarayicidan gecmez -> `atif` BOSTUR: Meta
  // zaten atlar (user_data-bos) ama GA4 fallback client_id (siparis_no + ".0") ile
  // Purchase'i YINE GONDERIRDI. Sonuc: web disi ciro GA4'te "direct" satis gibi gorunur
  // ve site ROI raporunu sisirir. Bu yuzden kanal 'site' DEGILSE olcum tetiklenmez;
  // atlama SESSIZ DEGIL, olcumLog ile gorunur yazilir.
  // GERIYE UYUM: `kanal` kolonu yoksa (goc kosmadi) s.kanal undefined -> kapi ACIK kalir;
  // mevcut satirlarin hepsi ALTER'dan sonra DEFAULT 'site' alir. Yani site akisinda
  // davranis DEGISMEZ.
  const { siteKanali, olcumluGecis, zatenDenendi, olcumTetikle } = olcumKarari(s, hedef);

  const yeniGecmis = gecmiseEkle(s.durum_gecmisi, hedef, { olcumDenendi: olcumTetikle });
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = ?, durum_gecmisi = ? WHERE siparis_no = ? AND durum = ?"
  ).bind(hedef, yeniGecmis, siparisNo, s.durum).run();
  if (!(g.meta && g.meta.changes > 0)) {
    return yjson({ hata: "durum-degismis", mevcut: s.durum }, 409);
  }

  if (olcumluGecis && zatenDenendi) {
    // Sessiz atlama YOK: "bu siparisin ikinci Purchase'i nerede?" sorusu cevaplanabilsin.
    olcumLog({ olay: "Purchase", siparis_no: siparisNo, kaynak: "havale",
               atlandi: "zaten-denendi" });
  }
  if (hedef === "odendi" && !siteKanali) {
    // Kanal kapisi (yukari bak). Gecis BASARIYLA yapildiktan sonra loglanir — 409'da
    // yanlis bir "atlandi" satiri uretmeyelim.
    olcumLog({ olay: "Purchase", siparis_no: siparisNo, kaynak: String(s.kanal),
               atlandi: "site-disi-kanal" });
  }
  if (olcumTetikle && g.meta.changes > 0) {
    // Fire-and-forget (ctx.waitUntil olcum.js icinde): olcum hatasi durum degisimini
    // ETKILEMEZ — durum D1'de zaten kalici olarak degisti.
    havaleOlcumu(env, ctx, { ...s, durum: hedef });
  }
  return yjson({ ok: true, siparis_no: siparisNo, durum: hedef }, 200);
}

// ---- /kargo -------------------------------------------------------------------

async function kargo(request, env, ctx, telegram) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  const siparisNo = govde && typeof govde.siparis_no === "string" ? govde.siparis_no : "";
  const firma = govde && typeof govde.kargo_firma === "string" ? govde.kargo_firma.trim() : "";
  const kod = govde && typeof govde.kargo_kodu === "string" ? govde.kargo_kodu.trim() : "";
  if (!siparisNo) { return yjson({ hata: "eksik-alan" }, 400); }
  if (!firma || firma.length > 80) { return yjson({ hata: "kargo-firma" }, 400); }
  if (!kod || kod.length > 80) { return yjson({ hata: "kargo-kodu" }, 400); }

  const s = await siparisGetir(env, siparisNo);
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  if (!kargoGecisiGecerli(s.durum)) {
    return yjson({ hata: "gecersiz-gecis", mevcut: s.durum, hedef: "kargolandi" }, 400);
  }
  const yeniGecmis = gecmiseEkle(s.durum_gecmisi, "kargolandi");
  const g = await env.KATALOG.prepare(
    "UPDATE siparisler SET durum = 'kargolandi', kargo_firma = ?, kargo_kodu = ?," +
    " durum_gecmisi = ? WHERE siparis_no = ? AND durum = ?"
  ).bind(firma, kod, yeniGecmis, siparisNo, s.durum).run();
  if (!(g.meta && g.meta.changes > 0)) {
    return yjson({ hata: "durum-degismis", mevcut: s.durum }, 409);
  }

  // Kargo e-postasi (tetik 2) — ctx.waitUntil: yanit bloklanmaz, hata siparisi dusurmez.
  let satirlar = [];
  try { satirlar = JSON.parse(s.urunler) || []; } catch (e) { satirlar = []; }
  if (s.musteri_eposta) {
    const html = kargoEpostasiHtml(s, satirlar, firma, kod);
    ctx.waitUntil(epostaAkisi(env, telegram, siparisNo, [
      { kime: s.musteri_eposta, konu: "Siparişiniz kargoda — " + siparisNo,
        html: html, etiket: "müşteri-kargo" },
    ]));
  }
  return yjson({ ok: true, siparis_no: siparisNo, durum: "kargolandi",
                 kargo_firma: firma, kargo_kodu: kod }, 200);
}

// ---- /havale-onay ---------------------------------------------------------------

/**
 * POST /api/shop/yonet/havale-onay — {siparis_no, dekont_ref, tutar?}
 *
 * 🔴 K284 (Okan karari, 24 Agu 2026). OLCULEN BOSLUK (K283): K252'den sonra
 * 'havale-bekliyor' -> 'odendi' gecisi worker'in HICBIR ucundan yapilamiyordu
 * (/donus havale satirini token NULL oldugu icin bulamaz · /durum kapisi 400 verir ·
 * /wa-siparis INSERT'tir, gecis degil · cron eli yok). Geriye yalnizca worker DISI ham
 * SQL kaliyordu ve o yol `havaleOlcumu()`ye HIC ugramadigi icin havale cirosu Meta/GA4'te
 * GORUNMUYORDU.
 *
 * COZUM /kargo ucunun BIREBIR KARDESIDIR: nasil takip kodsuz 'kargolandi' yazilamiyorsa,
 * DEKONT REFERANSSIZ 'odendi' de yazilamaz. Yani kapi GEVSEMEDI, delil sarti degisti.
 *
 * KIRMIZI CIZGILER
 *  - `durumUcuKarari()` DOKUNULMADI: /durum'dan 'havale-bekliyor' -> 'odendi' HALA 400.
 *    Bu uc AYRI ve DARDIR (tek mevcut durum, tek hedef, zorunlu delil).
 *  - 🔒 `dekont_ref` FINANSAL VERIDIR: log'a, hata metnine, yanit govdesine ve /liste
 *    JSON'una GIRMEZ. Yalnizca D1 satirina yazilir. (Bu yuzden asagidaki sema-goc
 *    log satiri da referansi TASIMAZ.)
 *  - `tutar` OPSIYONELDIR ve YALNIZ DOGRULAMA icindir: KURUS tamsayisi olarak verilirse
 *    tahsilat toplamiyla (tutar_kurus + kargo_kurus) BIREBIR esitligi aranir, esit degilse
 *    400. HICBIR para alanini DEGISTIRMEZ — sunucu-tarafi fiyat tek kaynaktir.
 *  - SEMA FAIL-CLOSED: `havale_dekont_ref` kolonu yoksa 503 doner ve HICBIR SEY YAZILMAZ.
 *    Okuma yollarindaki `kolonMerdiveni` deseni burada BILEREK KULLANILMAZ — kolonsuz bir
 *    UPDATE 'odendi'yi REFERANSSIZ yazardi, yani ucun tek varlik sebebini yok ederdi
 *    (/wa-siparis'teki kanal kolonu kararinin AYNISI).
 *  - Purchase olcumu NORMAL koldan gider: `olcumKarari()` (TEK KAYNAK) + `havaleOlcumu()`,
 *    event_id = siparis_no, uc katmanli idempotens (durum makinesi + CAS + kalici iz)
 *    AYNEN korunur.
 */
async function havaleOnay(request, env, ctx) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  const siparisNo = govde && typeof govde.siparis_no === "string" ? govde.siparis_no : "";
  const ref = govde && typeof govde.dekont_ref === "string" ? govde.dekont_ref.trim() : "";
  if (!siparisNo) { return yjson({ hata: "eksik-alan" }, 400); }
  // 🔴 KENDI HATA KODU: "400" tek basina hangi kuralin reddettigini soylemez (/kargo'daki
  // 'kargo-kodu' ile ayni sozlesme). Hata metni referansin KENDISINI TASIMAZ.
  if (!ref || ref.length > DEKONT_REF_ENCOK) { return yjson({ hata: "dekont-ref" }, 400); }

  // Opsiyonel tutar BEYANI (kurus). Verilmezse dogrulama yapilmaz; verilirse tamsayi olmali.
  let tutarBeyani = null;
  if (govde && govde.tutar !== undefined && govde.tutar !== null && govde.tutar !== "") {
    const t = Number(govde.tutar);
    if (!Number.isInteger(t) || t < 0) { return yjson({ hata: "gecersiz-tutar" }, 400); }
    tutarBeyani = t;
  }

  const s = await siparisGetir(env, siparisNo);
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  if (!havaleGecisiGecerli(s.durum)) {
    return yjson({ hata: "gecersiz-gecis", mevcut: s.durum, hedef: "odendi" }, 400);
  }
  if (tutarBeyani !== null) {
    const tahsilat = (Number(s.tutar_kurus) || 0) + (Number(s.kargo_kurus) || 0);
    if (tutarBeyani !== tahsilat) {
      return yjson({ hata: "tutar-uyusmuyor", beklenen_kurus: tahsilat }, 400);
    }
  }

  // 🔴 OLCUM KARARI TEK KAYNAKTAN (durumDegistir ile AYNI fonksiyon) — kopya kural YOK.
  const karar = olcumKarari(s, "odendi");
  const yeniGecmis = gecmiseEkle(s.durum_gecmisi, "odendi",
                                 { olcumDenendi: karar.olcumTetikle });
  let g;
  try {
    // CAS (2. idempotens katmani): WHERE ... AND durum = <okunan durum>. Iki es zamanli
    // onay gelse yalniz BIRI changes>0 alir; olcum yalniz o daldan tetiklenir.
    g = await env.KATALOG.prepare(
      "UPDATE siparisler SET durum = 'odendi', havale_dekont_ref = ?, durum_gecmisi = ?" +
      " WHERE siparis_no = ? AND durum = ?"
    ).bind(ref, yeniGecmis, siparisNo, s.durum).run();
  } catch (e) {
    if (!/no such column/i.test(String((e && e.message) || e))) { throw e; }
    // Sema goc etmemis: SESSIZCE referanssiz yazmak YERINE gurultulu 503 (fail-closed).
    console.error("havale-onay: D1 semasinda havale_dekont_ref kolonu YOK -> onay " +
                  "reddedildi (coz: python3 tools/d1-sync.py --sema)");
    return yjson({ hata: "sema-goc-gerekli",
                   not: "siparisler.havale_dekont_ref kolonu yok; " +
                        "python3 tools/d1-sync.py --sema calistirilmali" }, 503);
  }
  if (!(g.meta && g.meta.changes > 0)) {
    return yjson({ hata: "durum-degismis", mevcut: s.durum }, 409);
  }

  if (karar.olcumluGecis && karar.zatenDenendi) {
    // Sessiz atlama YOK: "bu siparisin ikinci Purchase'i nerede?" cevaplanabilsin.
    olcumLog({ olay: "Purchase", siparis_no: siparisNo, kaynak: "havale",
               atlandi: "zaten-denendi" });
  }
  if (!karar.siteKanali) {
    olcumLog({ olay: "Purchase", siparis_no: siparisNo, kaynak: String(s.kanal),
               atlandi: "site-disi-kanal" });
  }
  if (karar.olcumTetikle) {
    // Fire-and-forget (ctx.waitUntil olcum.js icinde): olcum hatasi onayi ETKILEMEZ.
    havaleOlcumu(env, ctx, { ...s, durum: "odendi" });
  }
  // 🔒 dekont_ref YANITTA YOK (finansal veri).
  return yjson({ ok: true, siparis_no: siparisNo, durum: "odendi" }, 200);
}

// ---- /wa-siparis (WhatsApp / Ege kanali) --------------------------------------

/**
 * POST /api/shop/yonet/wa-siparis — Ege'nin (WhatsApp botu, AYRI depo/worker) kapattigi
 * siparisi AYNI panele yazar. Okan tek yerden takip etsin diye (Okan talebi, 1 Agu 2026).
 *
 * KIRMIZI CIZGILER
 *  - ID SEMASI BURADA URETILIR: siparis_no = PR-yyMMdd-HHmmss-XXX (siparis-no.js, kart/havale
 *    akisiyla AYNI uretec). Ege'nin KENDI numarasi (sonek YOK) siparis_no OLARAK ALINMAZ —
 *    iki sema karisirdi; o numara `dis_no` kolonunda MUTABAKAT ANAHTARI olarak durur.
 *  - PARA: bu uc TAHSILAT YAPMAZ. iyzico'ya gitmez, fiyat HESAPLAMAZ, katalog fiyatina
 *    BAKMAZ. `tutar_kurus` cagirandan gelir ve BOS/0 kalabilir (Okan cogu WhatsApp isini
 *    elle fiyatlandirir) — sunucu-tarafi fiyat kurali SITE akisinin kirmizi cizgisidir ve
 *    orada AYNEN durur, buraya TASINMAZ.
 *  - DURUM: yalniz 'havale-bekliyor' (varsayilan, "odeme bekleniyor") ya da 'odendi'
 *    yazilabilir. Uretim/kargo/tamamlandi gecisleri PANELDEN yapilir (durum makinesi
 *    degismedi) -> bu uc kargolandi/tamamlandi damgasi URETEMEZ.
 *  - IDEMPOTENS: `dis_no` verilirse ayni dis_no ile ikinci cagri YENI siparis ACMAZ,
 *    mevcut kaydi doner ({tekrar:true}). Ege'nin agi kopup yeniden denemesi Okan'in
 *    panelinde ikiz siparis olusturmasin.
 *  - E-POSTA/TELEGRAM GONDERMEZ: musteri zaten WhatsApp'ta konusuyor, ikinci bir kanaldan
 *    "siparisiniz alindi" mesaji cift bildirim olur. (Bilincli kapsam karari.)
 *  - REKLAM OLCUMU TETIKLEMEZ (ne burada ne panelde 'odendi' geciste — durumDegistir'deki
 *    KANAL kapisi). Gerekce orada yazili.
 */

/** Bosluk kirpilmis metin; uzunluk araligi disindaysa null (index.js metin() ile ayni sozlesme). */
function waMetin(v, enAz, enCok) {
  const s = typeof v === "string" ? v.trim() : "";
  return s.length >= enAz && s.length <= enCok ? s : null;
}

/** Tamsayi kurus alani: verilmemisse 0, gecersizse null (cagiran 400 doner). */
function waKurus(v) {
  if (v === undefined || v === null || v === "") { return 0; }
  if (!Number.isInteger(v) || v < 0 || v > 100000000) { return null; }
  return v;
}

/** Urun linkinden katalog id'si: https://<host>/urun/<id>/ -> "<id>". Eslesmezse "". */
function waLinktenId(link) {
  const m = /^https:\/\/[^/]+\/urun\/([a-z0-9-]{1,120})\/?$/i.exec(String(link || ""));
  return m ? m[1].toLowerCase() : "";
}

/** Katalog disi kalem icin GUVENLI sentetik id: "wa-" + baslik slug'i.
 *  "wa-" oneki ZORUNLU: sentetik id GERCEK bir katalog id'sine denk gelirse panel o urunun
 *  baski notunu ve R2 dosyalarini bu kaleme yapistirirdi (yanlis uretim dosyasi = pahali
 *  hata). Onek carpismayi yapisal olarak imkansiz kilar. */
function waSentetikId(baslik) {
  const TR = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u" };
  const slug = String(baslik || "").toLowerCase()
    .replace(/[çğıöşüâîû]/g, (c) => TR[c] || c)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
  return "wa-" + (slug || "parca");
}

/**
 * Bir hatanin TUM metnini topla: D1 gercek sebebi bazen `cause` zincirinde tasir
 * (workerd `Error: D1_ERROR: ...` sarar). Yalniz `e.message`e bakmak kirilgan.
 */
function waHataMetni(e) {
  const parcalar = [];
  let k = e;
  for (let i = 0; i < 5 && k; i++) {
    if (typeof k === "string") { parcalar.push(k); break; }
    if (k.message) { parcalar.push(String(k.message)); }
    if (k.cause && k.cause !== k) { k = k.cause; } else { break; }
  }
  if (!parcalar.length) { parcalar.push(String(e)); }
  return parcalar.join(" | ");
}

/**
 * Hata bir SQLite/D1 KISITLAMA ihlali mi (UNIQUE dahil)?
 * ⚠️ Bu kontrol TEK BASINA bir sey KARARLASTIRMAZ — cagiran taraf ayrica satirin
 * gercekten var oldugunu SELECT ile dogrular. Bu yuzden genis tutulabilir: yanlis
 * pozitif bir sonraki adimda elenir, yanlis negatif ise gercek bir yaris durumunu
 * 500'e dusururdu. (Fail-safe yon: genis eslesme + kanit zorunlulugu.)
 */
function waKisitlamaIhlali(e) {
  const metin = waHataMetni(e);
  return /UNIQUE constraint failed/i.test(metin) ||
         /constraint failed/i.test(metin) ||
         /SQLITE_CONSTRAINT/i.test(metin);
}

/** (kanal, dis_no) ciftiyle mevcut siparis satiri; yoksa null.
 *  `musteri_tel` DE cekilir: idempotens yanitini vermeden once satirin AYNI musteriye
 *  ait oldugu dogrulanir (bkz. waMevcutYaniti). */
async function waMevcutSiparis(env, disNo) {
  return env.KATALOG.prepare(
    "SELECT siparis_no, durum, musteri_tel FROM siparisler WHERE kanal = ? AND dis_no = ?"
  ).bind(WA_KANAL, disNo).first();
}

/**
 * Mevcut satir bulundugunda verilecek yanit — TEK yerde: hem on-SELECT hem yaris kolu
 * bunu cagirir.
 *
 * 🔴 CAPRAZ-MUSTERI SAVUNMASI. Idempotens anahtari yalniz `dis_no`; Ege'nin numara bicimi
 * (`PR-yyMMdd-HHmmss`, SANIYE cozunurluklu, sonek YOK) iki FARKLI musterinin ayni saniyede
 * ayni numarayi uretmesini dusuk ama SIFIR OLMAYAN bir ihtimal birakiyor. O halde eski
 * davranis, ikinci musteriye BASKA BIR MUSTERININ siparis numarasini `tekrar:true` ile
 * dondururdu ve ikinci siparis D1'e HIC yazilmazdi — sessiz siparis kaybi + PII karisimi.
 * Bu yuzden satirin telefonu gelen telefonla eslesmiyorsa idempotent yanit VERILMEZ,
 * gurultulu `409 dis-no-cakismasi` doner (Ege yeni bir dis_no ile tekrar dener).
 * ⚠️ FAIL-CLOSED: telefon okunamiyorsa (bos/eksik) da 409. Bu uc yazdigi HER satira
 * dogrulanmis (10-15 haneli) bir telefon koyar, yani bos telefon bu kanalda olusamaz;
 * "dogrulayamadim" halini tekrar sayip siparis kaybetmektense gurultu yapmak dogru yon.
 * KALICI COZUM Ege tarafinda (dis_no'ya sonek/rastgele parca) — bu KAPSAM DISI, burasi
 * savunma hattidir.
 */
function waMevcutYaniti(satir, disNo, tel) {
  if (String((satir && satir.musteri_tel) || "") !== tel) {
    console.error("wa-siparis: dis_no CAKISMASI — ayni dis_no BASKA musteri telefonuyla " +
                  "geldi, idempotent yanit VERILMEDI (dis_no=" + disNo + ")");
    return yjson({ hata: "dis-no-cakismasi",
                   not: "Bu dis_no BASKA bir musterinin siparisine ait. Idempotens " +
                        "anahtari musteriye gore kapsamlanir; yeni bir dis_no ile gonder." },
                 409);
  }
  return yjson({ ok: true, tekrar: true, siparis_no: satir.siparis_no,
                 durum: satir.durum, kanal: WA_KANAL, dis_no: disNo }, 200);
}

/** Kalem dizisini coz. Hata -> {hata}; basari -> {satirlar, kalemToplamKurus}. */
function waKalemleriCoz(urunler) {
  const SECENEK = globalThis.PRUVO_SECENEK;
  const enAzAdet = (SECENEK && SECENEK.ADET_EN_AZ) || 1;
  const enCokAdet = (SECENEK && SECENEK.ADET_EN_COK) || 99;
  if (!Array.isArray(urunler) || urunler.length < 1 || urunler.length > 20) {
    return { hata: "gecersiz-urunler" };
  }
  const satirlar = [];
  let toplam = 0;
  for (const u of urunler) {
    if (!u || typeof u !== "object") { return { hata: "gecersiz-urun" }; }
    const ad = waMetin(u.ad, 2, 200);
    if (!ad) { return { hata: "urun-ad" }; }
    // Link OPSIYONEL ama verildiyse SADECE https:// kabul edilir: bu deger yonetim
    // sayfasinda href olarak basilir -> javascript:/data: semasi yolu kapali kalsin.
    let link = "";
    if (u.link !== undefined && u.link !== null && u.link !== "") {
      link = waMetin(u.link, 12, 300) || "";
      if (!link || !/^https:\/\//i.test(link)) { return { hata: "urun-link" }; }
    }
    const adet = (u.adet === undefined || u.adet === null) ? 1 : u.adet;
    if (!Number.isInteger(adet) || adet < enAzAdet || adet > enCokAdet) {
      return { hata: "urun-adet" };
    }
    const tutar = waKurus(u.tutar_kurus);
    if (tutar === null) { return { hata: "urun-tutar" }; }
    toplam += tutar;
    const id = waLinktenId(link) || waSentetikId(ad);
    // Satir bicimi SITE akisiyla AYNI anahtarlari tasir (liste() ve yazdir.py bunu okur).
    // malzeme/renk BOS: WhatsApp'ta beyan sohbette kalir, uydurulmaz (bkz. baskiOnerisi).
    satirlar.push({
      id: id, baslik: ad, malzeme: "", renk: "", renk_ozel: "",
      adet: adet, birim_kurus: adet > 0 ? Math.floor(tutar / adet) : tutar,
      tutar_kurus: tutar,
      kanal: WA_KANAL,
      ...(link ? { url: link } : {}),
    });
  }
  return { satirlar, kalemToplamKurus: toplam };
}

export async function waSiparis(request, env) {
  let govde;
  try { govde = await request.json(); } catch (e) { return yjson({ hata: "gecersiz-json" }, 400); }
  if (!govde || typeof govde !== "object") { return yjson({ hata: "gecersiz-istek" }, 400); }

  // --- musteri (ad + tel + adres ZORUNLU; eposta opsiyonel — WhatsApp'ta cogu zaman yok) ---
  const m = govde.musteri || {};
  const ad = waMetin(m.ad, 2, 120);
  if (!ad) { return yjson({ hata: "musteri-ad" }, 400); }
  const tel = (typeof m.tel === "string" ? m.tel : "").replace(/[^0-9]/g, "");
  if (tel.length < 10 || tel.length > 15) { return yjson({ hata: "musteri-tel" }, 400); }
  const adres = waMetin(m.adres, 5, 500);
  if (!adres) { return yjson({ hata: "musteri-adres" }, 400); }
  let eposta = "";
  if (m.eposta !== undefined && m.eposta !== null && m.eposta !== "") {
    eposta = waMetin(m.eposta, 6, 200) || "";
    if (!eposta || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(eposta)) {
      return yjson({ hata: "musteri-eposta" }, 400);
    }
  }

  // --- odeme yontemi: sessiz varsayilan YOK (site akisindaki kural burada da gecerli) ---
  const odeme = govde.odeme;
  if (odeme !== "kart" && odeme !== "havale") { return yjson({ hata: "gecersiz-odeme" }, 400); }

  // --- durum: yalniz iki deger; varsayilan 'havale-bekliyor' (= odeme bekleniyor) ---
  const durum = (govde.durum === undefined || govde.durum === null || govde.durum === "")
    ? "havale-bekliyor" : govde.durum;
  if (durum !== "havale-bekliyor" && durum !== "odendi") {
    return yjson({ hata: "gecersiz-durum" }, 400);
  }

  // --- kalemler ---
  const kc = waKalemleriCoz(govde.urunler);
  if (kc.hata) { return yjson({ hata: kc.hata }, 400); }
  const { satirlar, kalemToplamKurus } = kc;

  // --- tutar: govdeden gelen toplam, yoksa kalem toplamlari (ikisi de 0 olabilir) ---
  const tutarAlani = waKurus(govde.tutar_kurus);
  if (tutarAlani === null) { return yjson({ hata: "gecersiz-tutar" }, 400); }
  const tutarKurus = tutarAlani > 0 ? tutarAlani : kalemToplamKurus;
  const kargoKurus = waKurus(govde.kargo_kurus);
  if (kargoKurus === null) { return yjson({ hata: "gecersiz-kargo" }, 400); }
  // KDV dokumu: oran TEK KAYNAK secenekler.js (index.js ile ayni fonksiyon). Tutar 0 ise
  // dokum de 0'dir — "bilinmiyor" demek, sifir KDV beyani DEGIL (fiyat sonra elle girilir).
  const SECENEK = globalThis.PRUVO_SECENEK;
  const kdvKurus = (SECENEK && typeof SECENEK.kdvAyristir === "function")
    ? SECENEK.kdvAyristir(tutarKurus + kargoKurus).kdvKurus : 0;

  // --- dis_no (Ege'nin kendi numarasi) — idempotens anahtari, ZORUNLU ------------
  // 🔴 OPSIYONEL DEGIL. Once opsiyoneldi ve bu, idempotensi ISTEGE BAGLI kiliyordu:
  // dis_no'suz cagrida hicbir tekillik anahtari olmadigi icin Ege'nin agi kopup yeniden
  // denemesi (ya da bir dongu/webhook tekrari) SINIRSIZ mukerrer siparis aciyordu —
  // olculdu: dis_no'suz 4 cagri = 4 INSERT, 4 ayri siparis numarasi, 0 idempotens SELECT.
  // Kismi UNIQUE indeks (`WHERE dis_no <> ''`) de bu satirlari kapsamadigi icin veri
  // tabani da durduramiyordu. Panelde ikiz siparis = yanlis uretim + yanlis tahsilat.
  // ⚠️ SITE kanali DOKUNULMADI: `kanal='site'` satirlari dis_no='' ile coklu kalmaya
  // devam eder (kismi indeks aynen duruyor); sikilastirma YALNIZ bu ucun girdisinde.
  if (govde.dis_no === undefined || govde.dis_no === null || govde.dis_no === "") {
    return yjson({ hata: "dis-no-yok",
                   not: "dis_no ZORUNLU: idempotens anahtari (Ege'nin kendi siparis " +
                        "numarasi). Ayni deger tekrar gonderilirse yeni siparis acilmaz." },
                 400);
  }
  const disNo = waMetin(govde.dis_no, 3, 40) || "";
  if (!disNo || !/^[A-Za-z0-9_-]{3,40}$/.test(disNo)) {
    return yjson({ hata: "gecersiz-dis-no" }, 400);
  }

  // --- SEMA KAPISI (FAIL-CLOSED) + IDEMPOTENS + YAZMA ---------------------------
  // `kanal`/`dis_no` kolonlari canli D1'de ancak `python3 tools/d1-sync.py --sema` kosunca
  // olusur. Kolonsuz bir INSERT teknik olarak calisirdi ama kayit panelde SITE siparisi
  // gibi gorunurdu (kanal rozeti yok, olcum kapisi devre disi) — sessiz ve geri donusu
  // zahmetli bir hata. Bu yuzden OKUMA yollarinin aksine burada FAIL-CLOSED: kolon yoksa
  // hicbir sey yazilmaz, gurultulu 503 + ne yapilacagi doner.
  try {
    // IDEMPOTENS: ayni dis_no ile ikinci cagri yeni siparis ACMAZ (Ege'nin agi kopup
    // yeniden denemesi Okan'in panelinde ikiz siparis olusturmasin). dis_no ZORUNLU
    // oldugundan bu SELECT her cagri icin kosar (atlanabilir bir kol kalmadi).
    const varOlan = await waMevcutSiparis(env, disNo);
    if (varOlan) { return waMevcutYaniti(varOlan, disNo, tel); }

    const siparisNo = await yeniSiparisNo(env);
    const simdi = new Date().toISOString();
    // token NULL: /donus bu satiri HICBIR iyzico token'iyla bulamaz (havale akisiyla ayni
    // koruma) -> WhatsApp siparisinin durumu istemciden degistirilemez.
    await env.KATALOG.prepare(
      "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus," +
      " kdv_kurus, odeme_yontemi, sozlesme_onay, urunler, filament, renk," +
      " musteri_ad, musteri_tel, musteri_eposta, musteri_adres, musteri_notu, atif, durum_gecmisi," +
      " kanal, dis_no)" +
      " VALUES (?, NULL, ?, ?, ?, ?, ?, ?, '', ?, '', '', ?, ?, ?, ?, '', '', ?, ?, ?)"
    ).bind(
      siparisNo, simdi, durum, tutarKurus, kargoKurus, kdvKurus, odeme,
      JSON.stringify(satirlar),
      ad, tel, eposta, adres,
      gecmiseEkle("", durum), WA_KANAL, disNo
    ).run();

    return yjson({ ok: true, siparis_no: siparisNo, durum: durum, kanal: WA_KANAL,
                   dis_no: disNo, tutar_kurus: tutarKurus, kargo_kurus: kargoKurus,
                   kdv_kurus: kdvKurus }, 201);
  } catch (e) {
    if (!/no such column/i.test(waHataMetni(e))) {
      // --- YARIS DURUMU (TOCTOU) --------------------------------------------------
      // Yukaridaki idempotens SELECT'i ile INSERT arasinda BASKA bir cagri ayni dis_no
      // ile yazmis olabilir (Ege paralel iki deneme yaparsa). O halde kismi UNIQUE
      // indeks (siparisler_kanal_dis_no) INSERT'i reddeder ve buraya bir D1 hatasi
      // duser. ONCEDEN: hic yakalanmiyordu -> index.js'in genel catch'i 500
      // `sunucu-hatasi` donuyordu; oysa BEYAN EDILEN sozlesme 200 {tekrar:true}.
      // Ege 500 gorunce yeniden dener -> tekrar 500 -> siparis panele yazilmis
      // oldugu halde bot "yazilamadi" sanir (sessiz hata).
      // GUVENLIK: 200'e cevirme KOSULLU — hatanin kisitlama kokenli oldugunu string'e
      // BAGLI OLARAK degil, ikinci bir SELECT ile KANITLIYORUZ. Satir gercekten varsa
      // idempotent yanit dogrudur; yoksa hata AYNEN yeniden firlatilir (500 kalir).
      if (waKisitlamaIhlali(e)) {
        let yarisSatiri = null;
        try { yarisSatiri = await waMevcutSiparis(env, disNo); } catch (e2) { yarisSatiri = null; }
        if (yarisSatiri) {
          console.warn("wa-siparis: yaris durumu — ayni dis_no es zamanli yazildi " +
                       "(dis_no=" + disNo + ")");
          // Yaris kolunda da CAPRAZ-MUSTERI kontrolu gecerli: rakip satir baska bir
          // musteriye aitse 200 degil 409 doner (bkz. waMevcutYaniti).
          return waMevcutYaniti(yarisSatiri, disNo, tel);
        }
      }
      throw e;
    }
    console.error("wa-siparis: D1 semasinda kanal/dis_no kolonu YOK -> yazma reddedildi " +
                  "(coz: python3 tools/d1-sync.py --sema)");
    return yjson({ hata: "sema-goc-gerekli",
                   not: "siparisler.kanal / siparisler.dis_no kolonlari yok; " +
                        "python3 tools/d1-sync.py --sema calistirilmali" }, 503);
  }
}

// ---- /stl + /stl-liste (COK-PARCA tasarimi — mimar duzeltme turu) ---------------
// R2 duzeni: stl/<urun-id>/<parca-adi> (bir urunun BIRDEN COK parca dosyasi olabilir —
// norm bu; tools/stl-r2-yukle.py tek adlilari da stl/<id>/<id>.stl'e normalize eder).
// ZIP YOK: 280 MB'lik dosyalar var, worker'da sikistirma yapilmaz — parcalar tek tek iner.

function tirnaksiz(s) { return String(s || "").replace(/["\r\n]/g, ""); }

// IZINLI_UZANTI -> "DOSYA ADI KANONIK BICIMI" blogu (DRIVE_TABAN'in altinda).

/** Urunun R2'deki parca dosyalari: [{dosya, boyut}]. */
async function parcalariListele(env, urunId) {
  const liste = await env.OZEL_DOSYA.list({ prefix: "stl/" + urunId + "/" });
  return (liste.objects || []).map((o) => ({
    dosya: o.key.slice(("stl/" + urunId + "/").length),
    boyut: o.size,
  })).filter((p) => p.dosya);
}

/** GET /yonet/stl-liste?id= -> {id, parcalar:[{dosya,boyut}], not?} */
async function stlListe(env, url) {
  const urunId = url.searchParams.get("id") || "";
  if (!/^[a-z0-9-]{1,120}$/.test(urunId)) { return yjson({ hata: "gecersiz-id" }, 400); }
  if (!env.OZEL_DOSYA) { return yjson({ hata: "r2-baglanti-yok" }, 503); }
  const parcalar = await parcalariListele(env, urunId);
  const govde = { id: urunId, parcalar: parcalar };
  if (!parcalar.length) {
    govde.not = "dosya R2 stl/ prefix'inde yok — stl/ klasörü / Drive / gizli kaynak " +
      "kaydına bak (id: " + urunId + ")";
  }
  return yjson(govde, 200);
}

/** GET /yonet/stl?id=&dosya=[&siparis_no=]  -> tek parca stream (normal urun)
 *  GET /yonet/stl?siparis_no=&kalem=N       -> SARI satir: derleyiciden uret (DEGISMEDI)
 *  Dosya adi dogrulamasi: R2 listesinde OLMAYAN ad 404 (path traversal yolu yok). */
async function stlIndir(env, url) {
  const siparisNo = url.searchParams.get("siparis_no") || "";
  const idParam = url.searchParams.get("id") || "";
  const dosyaParam = url.searchParams.get("dosya") || "";

  // --- Normal urun parcasi: id + dosya ---
  if (idParam && dosyaParam) {
    if (!/^[a-z0-9-]{1,120}$/.test(idParam)) { return yjson({ hata: "gecersiz-id" }, 400); }
    if (!env.OZEL_DOSYA) { return yjson({ hata: "r2-baglanti-yok" }, 503); }
    // Savunma 1: ayirac/ust-dizin icermesin; uzanti .stl|.3mf olsun — yuklemeyle AYNI
    // kanonik fonksiyon (Turkce/NFD/.STL ad ayni anahtara duser; eski bosluklu ad da denenir).
    const adlar = stlDosyaAdiAdaylari(dosyaParam);
    if (!adlar.length) { return yjson({ hata: "dosya-yok" }, 404); }
    // Savunma 2 (spec): LISTEDE olmayan ad 404 — anahtar dogrudan kurulup GET edilmez.
    const parcalar = await parcalariListele(env, idParam);
    const parca = parcalar.find((p) => adlar.includes(p.dosya));
    if (!parca) {
      return yjson({
        hata: "dosya-yok",
        not: "dosya R2 stl/" + idParam + "/ altinda yok — stl/ klasörü / Drive / gizli " +
          "kaynak kaydına bak (id: " + idParam + ")",
      }, 404);
    }
    const nesne = await env.OZEL_DOSYA.get("stl/" + idParam + "/" + parca.dosya);
    if (!nesne) { return yjson({ hata: "dosya-yok" }, 404); }
    const indirmeAdi = (siparisNo ? tirnaksiz(siparisNo) + "-" : "") + tirnaksiz(parca.dosya);
    return new Response(nesne.body, {
      status: 200,
      headers: {
        "Content-Type": /\.3mf$/i.test(parca.dosya) ? "model/3mf" : "application/octet-stream",
        "Content-Disposition": "attachment; filename=\"" + indirmeAdi + "\"",
        "Cache-Control": "no-store",
      },
    });
  }

  // --- Siparis kalemi yolu (sari uretim; normal kalem parca listesine yonlendirilir) ---
  const kalemStr = url.searchParams.get("kalem");
  const s = await env.KATALOG.prepare(
    "SELECT siparis_no, urunler FROM siparisler WHERE siparis_no = ?"
  ).bind(siparisNo).first();
  if (!s) { return yjson({ hata: "siparis-yok" }, 404); }
  let satirlar = [];
  try { satirlar = JSON.parse(s.urunler) || []; } catch (e) { satirlar = []; }
  let satir = null;
  if (kalemStr != null && kalemStr !== "") {
    const i = parseInt(kalemStr, 10);
    satir = (Number.isInteger(i) && i >= 0) ? satirlar[i] || null : null;
  }
  if (!satir) { return yjson({ hata: "kalem-yok" }, 404); }
  const urunId = satir.id;

  // Parametrik (sari): onizleme derleyicisinden URET (anahtar korumali ic uc; musteri
  // kotasini yemez, gzip'siz ham STL). Onizleme worker'i ayni zone'dan cagrilir.
  if (satir.parametreler && SEMALAR.has(urunId)) {
    const taban = (env.ONIZLEME_TABAN || env.SITE_URL || "https://pruvo3d.com").replace(/\/$/, "");
    // 2-RENK (COK GOVDELI) SIPARIS: satirda `yazi_renk` varsa urun IKI govde olarak
    // basilir (AMS 2 filaman). Her govde AYRI indirilir:
    //   ...&parca=govde  -> yazisiz cerceve kabugu
    //   ...&parca=yazi   -> yalniz kabartma yazi
    // `parca` VERILMEZSE bugunku TEK STL (birlesik govde) aynen doner — var olan
    // yonetim baglantilari kirilmaz. Degerin GECERLILIGINI onizleme worker'i
    // fail-closed dogrular (liste disi deger 400 `gecersiz-parca`).
    const parcaParam = url.searchParams.get("parca");
    const istekGovdesi = { aile: urunId, parametreler: satir.parametreler };
    if (parcaParam) { istekGovdesi.parca = parcaParam; }
    let c;
    try {
      c = await fetch(taban + "/api/onizleme/ic-derle", {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Ic-Anahtar": env.IC_DERLE_ANAHTAR || "" },
        body: JSON.stringify(istekGovdesi),
      });
    } catch (e) {
      return yjson({ hata: "derleyici-ulasilamiyor" }, 502);
    }
    if (c.status !== 200) {
      let h = "derleme-hatasi";
      try { h = ((await c.json()) || {}).hata || h; } catch (e) { /* jenerik */ }
      return yjson({ hata: h }, c.status < 500 ? c.status : 502);
    }
    return new Response(c.body, {
      status: 200,
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": "attachment; filename=\"" +
          tirnaksiz(siparisNo + "-" + urunId + (parcaParam ? "-" + parcaParam : "")) +
          ".stl\"",
        "Cache-Control": "no-store",
      },
    });
  }

  // Normal kalem: parca listesi ucu kullanilir (bir urunun birden cok dosyasi olabilir).
  return yjson({ hata: "parca-listesi-kullan",
                 stl_liste_ucu: "/api/shop/yonet/stl-liste?id=" + urunId }, 400);
}

// ---- yonetim sayfasi (tek dosya, inline) --------------------------------------

function sayfa() {
  return new Response(SAYFA_HTML, {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

// ---- giris kapisi (sifre kutusu) ----------------------------------------------

/**
 * Yetkisiz `GET /yonet` VE yanlis/bos anahtarli `POST /yonet` icin BIREBIR AYNI yanit.
 * ⚠️ AYIRT EDICI MESAJ YOK ("anahtar yanlis" DEMEZ): "varligi sizmasin" kurali burada da
 * gecerli — yanlis deneme ile hic denememis ziyaretci ayni kodu, ayni govdeyi, ayni
 * basliklari gorur (Set-Cookie de YOK). Ekranda siparis/PII/panel govdesi YOKTUR.
 * Form eylemi istegin KENDI yolundan turer (sorgu dizesi TASINMAZ).
 */
function girisEkrani(url) {
  const yol = String((url && url.pathname) || "/api/shop/yonet").replace(/[&<>"']/g, "");
  // 🔴 IKAME FONKSIYON — dize DEGIL. `String.replace`'in IKAME DIZESI `$&`, `$\``, `$'`,
  // `$$` desenlerini yorumlar; backtick yukaridaki [&<>"'] suzgecinden GECER ve `$\``
  // eslesmeden ONCEKI tum HTML'i action niteligine kopyalar (olculdu: 967 -> 1762 bayt).
  // Fonksiyon ikamesinde bu desenler yorumlanmaz — `yol` HARFI HARFINE basilir.
  // (Bugun yonlendirici `yol === "/yonet"` TAM esitligi dayattigi icin erisilemezdi; ama
  // rota bir gun on-ek eslesmesine cevrilirse dogrudan enjeksiyon olurdu. Suzgec tek
  // basina sahte guvenceydi.)
  return new Response(GIRIS_HTML.replace("__EYLEM__", () => yol), {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

// ---- giris hiz siniri (worker-ici; Cloudflare binding'i GEREKTIRMEZ) ----------
// NEDEN GEREKLI: panel eskiden anahtarsiz 404'tu, artik 200 sifre formu donuyor — ucun
// VARLIGI kesfedilebilir. Anahtar tek ve paylasilan bir sir; kaba kuvvete karsi tek katman
// bu. (Takas bilincli: anahtarin erisim loglarinda/Referer'da durmasindan cok daha ucuz.)
// ⚠️ DURUSTCE SINIRI: sayac ISOLATE BASINA tutulur. Cloudflare istegi baska bir isolate'a
// dusurebilir, dolayisiyla bu MUTLAK bir tavan DEGIL — ucuz bir yavaslatici. Kalici/global
// tavan Rate Limiting binding'i ister; mimar bu turda kapsam disi tuttu.
const GIRIS_PENCERE_MS = 60 * 1000;
const GIRIS_TAVAN = 5;              // pencere basina BASARISIZ deneme
const GIRIS_GECIKME_MS = 250;       // her basarisiz/bloke denemede sabit bekleme
const GIRIS_GOVDE_SINIRI = 1024;    // bayt — sifre formu icin fazlasiyla yeterli
let girisSayac = { pencereBas: 0, adet: 0 };

function bekle(ms) { return new Promise((coz) => setTimeout(coz, ms)); }

/**
 * Pencere doldu mu (esik asildi mi)? Pencere gecmisse sayac sifirlanir.
 * Sayac isolate basina tutulur; GARANTILI bir ust sinir DEGILDIR (bkz. yukaridaki not).
 */
function girisBlokeMi(simdi) {
  if (simdi - girisSayac.pencereBas > GIRIS_PENCERE_MS) {
    girisSayac = { pencereBas: simdi, adet: 0 };
  }
  return girisSayac.adet >= GIRIS_TAVAN;
}

/**
 * Istek govdesini SINIRLI okur. Sinir asilirsa null (fail-closed) — `request.formData()`
 * govde boyutuna UST SINIR KOYMAZ; anahtarsiz bir uca sinirsiz ayristirma yaptirmayiz.
 * Yalniz `application/x-www-form-urlencoded` ayristirilir (form bunu yollar); multipart
 * yuzeyi bilerek ACILMAZ.
 */
async function girisGovdesi(request) {
  const bildirilen = parseInt(request.headers.get("Content-Length") || "", 10);
  if (Number.isFinite(bildirilen) && bildirilen > GIRIS_GOVDE_SINIRI) { return null; }
  if (!request.body) { return ""; }
  const okuyucu = request.body.getReader();
  const parcalar = [];
  let toplam = 0;
  for (;;) {
    const { done, value } = await okuyucu.read();
    if (done) { break; }
    toplam += value.byteLength;
    // Content-Length YALAN soyleyebilir / hic olmayabilir (chunked): gercek bayt sayilir.
    if (toplam > GIRIS_GOVDE_SINIRI) { try { await okuyucu.cancel(); } catch (e) {} return null; }
    parcalar.push(value);
  }
  const hepsi = new Uint8Array(toplam);
  let ofs = 0;
  for (const p of parcalar) { hepsi.set(p, ofs); ofs += p.byteLength; }
  return new TextDecoder().decode(hepsi);
}

/**
 * POST /yonet — sifre kutusundan gelen anahtar. Anahtar istek GOVDESINDE gider; GET
 * DEGIL, cunku GET onu sorgu dizesine yazardi = kapatmaya calistigimiz sizintinin ta
 * kendisi. Dogruysa HttpOnly cerez kurulur + panele 302 (Location'da sorgu YOK).
 *
 * FAIL-CLOSED KOLLARI — hepsi AYNI giris ekranini doner (ayirt edilemez):
 *   secret yok -> 404 · tavan asildi -> form · govde buyuk/bozuk/bos -> form · yanlis -> form.
 * Anahtar loga/yanita/hata metnine YAZILMAZ.
 */
// `export` DAVRANISI DEGISTIRMEZ: yalnizca OLCULEBILIRLIK — kendi kapisi yonet()
// uzerinden gecmeden, IZOLE cagrilabilsin diye disa acildi (kabul.js C22a).
export async function girisYap(request, url, env) {
  // 🔴 KENDI KAPISI (savunma derinligi): yonet() de secret'i basta kontrol eder — ama
  // koruma CAGRI SIRASINA birakilmaz. Sira degisirse bu uc anahtarsiz cerez kuruluma
  // yetki verirdi. Kapi burada TEKRARLANIR.
  // OLCULDU (mutasyon, --yonet-cerez): iki kapi ARTIK AYRI AYRI olculuyor. Bu satir TEK
  // BASINA silinince C22a (kod) + C22e (govde) kirmizi yanar; yonet()'in ust kapisi TEK
  // BASINA silinince C15b/C15c + C22b/C22c kirmizi yanar ve C15a YESIL kalir — ozellik-kapali
  // POST o zaman BU satira duser, yani savunma derinligi calisir. Once bu satirin tek basina
  // silinmesi alt kumeyi YESIL birakiyordu (eski C22 iki kapinin VEYA'sini olcuyordu).
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();
  if (girisBlokeMi(simdi)) {
    // Tavan asildi: sifre HIC BAKILMADAN reddedilir (dogru sifre de). Yanit, hic
    // denememis ziyaretcininkiyle BIREBIR ayni — "bloke oldun" bile denmez.
    await bekle(GIRIS_GECIKME_MS);
    return girisEkrani(url);
  }
  const metin = await girisGovdesi(request);
  const verilen = metin === null ? "" :
    String(new URLSearchParams(metin).get("sifre") || "");
  if (!sabitEsit(verilen, env.YONET_ANAHTAR)) {
    girisSayac.adet++;
    await bekle(GIRIS_GECIKME_MS);
    return girisEkrani(url);
  }
  girisSayac = { pencereBas: simdi, adet: 0 };   // basarili giris sayaci sifirlar
  return new Response(null, {
    status: 302,
    headers: {
      "Location": String((url && url.pathname) || "/api/shop/yonet"),
      "Set-Cookie": yonetCereziKur(env.YONET_ANAHTAR),
      "Cache-Control": "no-store",
    },
  });
}

// ---- giris (index.js buraya yonlendirir) --------------------------------------

// ---- /konfigur-golge (FAZ 3 KONTROL KIPI) -------------------------------------

/**
 * GET /yonet/konfigur-golge — "D1'deki konfigur semasi Worker bundle'iyla AYNI mi?"
 *
 * 🔴 SALT OKUMA: tek bir SELECT; D1'e YAZMAZ, siparis/olcum/e-posta/iyzico TETIKLEMEZ,
 * musteriye giden hicbir davranisi degistirmez. Yalnizca FAZ 4 (cevirme) kararinin girdisi
 * olan sayiyi gorunur kilar: `fark_kurus_toplam` 0 ise iki kaynak ayni parayi uretiyor.
 *
 * Anahtar korumasi /yonet* ile AYNI (anahtar yok/yanlis -> 404). Konfigur verisi zaten
 * public (matematik + aralik + renk/malzeme; sir icermez) ama uc yine de gizli tutulur —
 * ic teshis yuzeyi genisletilmez.
 *
 * KOLON YOKSA (--sema henuz kosmadi) SELECT duser -> 200 + durum "kolon-yok" doner
 * (500 DEGIL: bu bir rapor ucu, kendisi kirmizi yanmamali; teshis metni acik yazilir).
 */
async function konfigurGolge(env, url) {
  const SECENEK = globalThis.PRUVO_SECENEK;
  if (!SECENEK) { return yjson({ hata: "secenekler-yok" }, 500); }
  const bundleIdler = [...KONFIGURLAR.keys()];
  const yertut = bundleIdler.map(() => "?").join(",") || "''";
  let satirlar = [];
  try {
    // IKI YON: (a) D1'de konfigur DOLU olan her satir (bundle'da olmayanlar = acik pencere),
    // (b) bundle'daki her id (D1'de bos/eksik olanlar = senkron kacmis). Tek sorgu.
    const r = await env.KATALOG.prepare(
      "SELECT id, kategori, konfigur FROM urunler WHERE konfigur <> '' OR id IN (" +
      yertut + ")").bind(...bundleIdler).all();
    satirlar = r.results || [];
  } catch (e) {
    return yjson({
      durum: "kolon-yok",
      teshis: "D1'de `konfigur` kolonu okunamadi: " + (e && e.message || String(e)),
      coz: "python3 tools/d1-sync.py --sema   (additive ALTER; sonra python3 tools/d1-sync.py)",
      bundle_urun: bundleIdler.length,
    }, 200);
  }
  const ornekBoy = parseInt(url.searchParams.get("boy") || "0", 10);
  const ornekler = ornekBoy > 0 ? [[ornekBoy, url.searchParams.get("malzeme") || "PLA"]] : null;
  const rapor = golgeRaporu(KONFIGURLAR, satirlar, SECENEK, ornekler);
  return yjson({
    durum: rapor.fark_kurus_toplam === 0 && rapor.kayitlar.length === 0 ? "parite" : "ayrisim",
    bundle_urun: bundleIdler.length,
    d1_konfigurlu_satir: satirlar.filter((s) => s.konfigur).length,
    ozet: rapor.ozet,
    fark_kurus_toplam: rapor.fark_kurus_toplam,
    kayitlar: rapor.kayitlar,
    not: "GOLGE MODU: tahsilat HALA bundle'dan hesaplanir; bu uc yalniz olcer.",
  }, 200);
}

// ═══════════════ URUNLER SEKMESI — panel_ustyazim YAZMA KUYRUGU (T1) ═══════════════
// TASARIM (mimar hakem hukmu, 29 Agu 2026): panel urunler.json'a ASLA yazmaz. Kaydet =
// D1 `panel_ustyazim` tablosuna hal='beklemede' SATIR (yazma KUYRUGU). Tabana isleyen
// TEK kol CI uygulayicisidir (tools/panel-uygulayici.py); fiyat/JSON-LD bir sonraki
// Build & deploy'da TABANDAN dogar — panel bunu kullaniciya ACIKCA soyler. Beyaz
// listenin OTORITESI uygulayicidadir; buradaki es kontrol erken-uyaridir, ayrisirsa
// satir uygulayicida hal='hata'+sebep olur (sessiz kaybolmaz). Kaynak link / uyelik /
// STL yeri gibi gizli alanlar bu kuyruga HIC girmez.
// TEKIL SILME (2 Eyl 2026): alan='sil' satiri da AYNI kuyruktan akar ama YALNIZ
// /urun-sil ucundan yazilir (cift onay + gerekce); /urunler-ustyazim beyaz listesi
// onu KABUL ETMEZ (asagida USTYAZIM_ALANLAR — silme, alan duzenlemesine sizamaz).
const USTYAZIM_ALANLAR = new Set(["fiyat", "baslik", "aciklama", "gorseller"]);
const USTYAZIM_DEGER_TAVAN = { fiyat: 20, baslik: 200, aciklama: 4000, gorseller: 4000 };
// Katalog fiyat sozlesmesi "N TL" (uygulayicidaki FIYAT_BICIMI ile es).
const FIYAT_BICIM_RX = /^[1-9][0-9]{0,5} TL$/;
// FIYAT GIRDI NORMALIZASYONU (Okan emri, 6 Eyl 2026): "sayfada/panelde noktalamaya izin
// verme, kurus miktari YUKARI yuvarlansin (200.1 -> 201 TL), TUM urunler icin".
// Neden giriste: katalogdaki 616 kayit "250.0 TL" bicimindeydi ve noktayi binlik ayraci
// sanan okuyucular (feed_price / price_number / secenekler.js fiyatSayisi) tutari ON KAT
// buyutuyordu — sepet/odeme dahil. Kural OKUMA tarafinda yuvarlamakla kapatilamaz: o
// zaman bozuk deger kayitta yasar ve hangi tutarin ilan edildigi kayittan okunamaz.
// Python ikizi: tools/arama.py fiyat_yukari_yuvarla (kabul testi ayni vaka tablosu).
const FIYAT_GIRDI_RX = /^\s*((?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+))(?:[.,]([0-9]{1,2}))?\s*(?:TL|TRY|₺)?(?:\s*\([^()]{1,40}\)|\/[^\s\/]{1,20})?\s*$/i;
function fiyatYukariYuvarla(ham) {
  if (typeof ham !== "string") { return null; }
  const m = FIYAT_GIRDI_RX.exec(ham.trim());
  if (!m) { return null; }
  let tam = parseInt(m[1].replace(/\./g, ""), 10);
  if (!(tam >= 0)) { return null; }
  // Kurus VARSA yukari yuvarla: "200.1" = 200 TL 10 kurus -> 201 TL.
  if (m[2] && parseInt(m[2].padEnd(2, "0"), 10) > 0) { tam += 1; }
  return tam > 0 ? tam + " TL" : null;
}
const URUN_ID_RX = /^[a-z0-9-]{1,200}$/;
// T2 — gorsel listesi ustyazimi. Deger JSON DIZI metnidir (tam liste; cikarma =
// listeden dusurulmus TAM listenin ustyazimi, R2 nesnesi SILINMEZ). Otorite yine
// uygulayicida (tools/panel-uygulayici.py gorsel_listesi_sebebi) — burasi erken uyari.
const GORSEL_ONEK = "https://media.pruvo3d.com/";
const GORSEL_SAYI_TAVANI = 24;
function gorselListesiSebebi(deger) {
  let liste;
  try { liste = JSON.parse(deger); } catch (e) { return "gorseller JSON dizi olmali"; }
  if (!Array.isArray(liste) || !liste.length) {
    return "gorsel listesi bos olamaz (en az 1 gorsel kalir; urun silme ayri uctan: Sil (arsive))";
  }
  if (liste.length > GORSEL_SAYI_TAVANI) {
    return "gorsel sayisi tavani " + GORSEL_SAYI_TAVANI;
  }
  const gorulen = new Set();
  for (const u of liste) {
    if (typeof u !== "string" || !u.startsWith(GORSEL_ONEK)) {
      return "her gorsel " + GORSEL_ONEK + " ile baslamali";
    }
    if (/[\s"'<>\\]/.test(u)) { return "gorsel adresinde gecersiz karakter"; }
    if (gorulen.has(u)) { return "ayni gorsel listede iki kez"; }
    gorulen.add(u);
  }
  return null;
}

function likeKacisla(s) {
  return String(s || "").replace(/[\\%_]/g, (m) => "\\" + m);
}

/** panel_ustyazim'a dokunan cagrilar icin tablo merdiveni: tablo yoksa OKUMA bos
 *  doner (ekran "sema kosulmamis" YAZAR — sessiz bosluk degil), YAZMA 503 doner
 *  (fail-closed: kuyruga yazilamayan kayit "kaydedildi" gorunemez). */
function tabloYokMu(e) {
  return /no such table/i.test(String((e && e.message) || e));
}

async function panelUrunListe(env, url) {
  const q = (url.searchParams.get("q") || "").trim().slice(0, 80);
  const limit = Math.min(100, Math.max(1, parseInt(url.searchParams.get("limit") || "30", 10) || 30));
  const SECIM = "SELECT id, baslik, fiyat, aciklama, kategori, parametrik, gorsel FROM urunler";
  const sorgu = q
    ? env.KATALOG.prepare(SECIM + " WHERE id LIKE ? ESCAPE '\\' OR baslik LIKE ? ESCAPE '\\'" +
        " ORDER BY seq DESC LIMIT ?")
        .bind("%" + likeKacisla(q) + "%", "%" + likeKacisla(q) + "%", limit)
    : env.KATALOG.prepare(SECIM + " ORDER BY seq DESC LIMIT ?").bind(limit);
  const r = await sorgu.all();
  const urunler = r.results || [];
  // Listelenen urunlerin BEKLEYEN ustyazimlari (kart "kuyrukta bekliyor" gosterir).
  let bekleyen = {};
  let kuyrukTablosu = true;
  if (urunler.length) {
    const idler = urunler.map((u) => u.id);
    const yertut = idler.map(() => "?").join(",");
    const b = await tabloMerdiveni(
      () => env.KATALOG.prepare(
        "SELECT id, urun_id, alan, deger, ts FROM panel_ustyazim" +
        " WHERE hal = 'beklemede' AND urun_id IN (" + yertut + ")").bind(...idler).all(),
      () => { kuyrukTablosu = false; return { results: [] }; });
    for (const s of (b.results || [])) {
      (bekleyen[s.urun_id] = bekleyen[s.urun_id] || {})[s.alan] =
        { id: s.id, deger: s.deger, ts: s.ts };
    }
  }
  return yjson({ urunler, bekleyen, kuyruk_tablosu: kuyrukTablosu }, 200);
}

async function panelKuyruk(env) {
  const r = await tabloMerdiveni(
    () => env.KATALOG.prepare(
      "SELECT id, urun_id, alan, deger, yazan, ts, hal, islendi_ts, islendi_commit, sebep" +
      " FROM panel_ustyazim ORDER BY id DESC LIMIT 100").all(),
    () => null);
  if (r === null) { return yjson({ satirlar: [], tablo_yok: true }, 200); }
  return yjson({ satirlar: r.results || [], tablo_yok: false }, 200);
}

async function panelUstyazimYaz(request, env, ctx) {
  let govde;
  try { govde = await request.json(); } catch (e) {
    return yjson({ hata: "gecersiz istek govdesi" }, 400);
  }
  const uid = typeof (govde && govde.urun_id) === "string" ? govde.urun_id.trim() : "";
  const alan = typeof (govde && govde.alan) === "string" ? govde.alan : "";
  let deger = typeof (govde && govde.deger) === "string" ? govde.deger : null;
  if (!URUN_ID_RX.test(uid)) { return yjson({ hata: "urun_id bicimsiz" }, 400); }
  if (!USTYAZIM_ALANLAR.has(alan)) {
    return yjson({ hata: "alan beyaz liste disi (fiyat | baslik | aciklama)" }, 400);
  }
  if (deger === null) { return yjson({ hata: "deger metin olmali" }, 400); }
  deger = deger.replace(/\r\n?/g, "\n").trim();
  if (!deger) { return yjson({ hata: "deger bos" }, 400); }
  if (deger.length > USTYAZIM_DEGER_TAVAN[alan]) {
    return yjson({ hata: "deger cok uzun (tavan " + USTYAZIM_DEGER_TAVAN[alan] + ")" }, 400);
  }
  const satirsiz = alan === "aciklama" ? deger.replace(/\n/g, "") : deger;
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(satirsiz) ||
      (alan !== "aciklama" && deger.indexOf("\n") >= 0)) {
    return yjson({ hata: "deger kontrol karakteri tasiyor" }, 400);
  }
  // FIYAT GIRIS KAPISI (Okan, 6 Eyl): noktalamaya IZIN YOK, kurus YUKARI yuvarlanir.
  // Normalize ONCE kosar -> "200.1 TL" 400 ile geri donmez, "201 TL" olarak kaydedilir;
  // ardindan kanonik bicim yine de ZORLANIR (normalize cozemediyse deger degismeden
  // gelir ve asagidaki test onu reddeder -> fail-closed, sessiz kabul YOK).
  if (alan === "fiyat") {
    const yuvarlanmis = fiyatYukariYuvarla(deger);
    if (yuvarlanmis !== null) { deger = yuvarlanmis; }
    if (!FIYAT_BICIM_RX.test(deger)) {
      return yjson({ hata: "fiyat bicimi \"500 TL\" olmali (yalniz tam sayi + TL)" }, 400);
    }
  }
  if (alan === "gorseller") {
    const sebep = gorselListesiSebebi(deger);
    if (sebep) { return yjson({ hata: sebep }, 400); }
  }
  const ur = await env.KATALOG.prepare(
    "SELECT id, parametrik FROM urunler WHERE id = ?").bind(uid).first();
  if (!ur) { return yjson({ hata: "urun katalogda yok" }, 404); }
  if (alan === "fiyat" && ur.parametrik) {
    // Sari seri sozlesmesi: fiyat BOS kalir, taban fiyat semadan basilir.
    return yjson({ hata: "parametrik (sari) urunde fiyat degistirilemez — taban fiyat semadan gelir" }, 400);
  }
  const kuyrukHata = await kuyrugaYaz(env, uid, alan, deger);
  if (kuyrukHata) { return kuyrukHata; }
  uygulayiciTetikle(env, ctx);
  // `deger` normalize EDILMIS olabilir (fiyat yuvarlama) — cagirana KAYDEDILEN degeri
  // don, girdigini degil: panel "201 TL" yazdigimizi gostersin, sessizce sapmasin.
  return yjson({ tamam: true, urun_id: uid, alan: alan, deger: deger,
                 hal: "beklemede" }, 200);
}

/** Kuyruga hal='beklemede' satir yaz — panelUstyazimYaz ve panelUrunSil'in ORTAK tek
 *  yazim yolu. Ayni (urun, alan) icin bekleyen satir varsa YENISI ONUN YERINE GECER
 *  (kuyruk sisirilmez); yoksa INSERT. islendi/hata satirlarina DOKUNULMAZ (gecmis
 *  kayittir). Tablo yoksa 503 Response doner (fail-closed: "kaydedildi" yalani
 *  imkansiz); basarida null. */
async function kuyrugaYaz(env, uid, alan, deger) {
  const ts = new Date().toISOString();
  try {
    const g = await env.KATALOG.prepare(
      "UPDATE panel_ustyazim SET deger = ?, ts = ?, yazan = 'panel'" +
      " WHERE urun_id = ? AND alan = ? AND hal = 'beklemede'").bind(deger, ts, uid, alan).run();
    const degisen = (g && g.meta && g.meta.changes) || 0;
    if (!degisen) {
      await env.KATALOG.prepare(
        "INSERT INTO panel_ustyazim (urun_id, alan, deger, yazan, ts, hal)" +
        " VALUES (?, ?, ?, 'panel', ?, 'beklemede')").bind(uid, alan, deger, ts).run();
    }
  } catch (e) {
    if (tabloYokMu(e)) { return yjson({ hata: "kuyruk tablosu yok — sema kosulmamis" }, 503); }
    throw e;
  }
  return null;
}

// TEKIL URUN SILME — "Sil (arsive)" (Okan emri 2 Eyl 2026 + BaBa cercevesi (1)-(5)).
// T2'nin "urun silme yolu YOK" kisitini Okan'in bu emri TEKIL manuel silme olarak
// kaldirdi; TOPLU silme ucu BILEREK ACILMADI (tek istek = tek urun; okan-hukmu-
// urun-silinmez toplu duzlemde gecerli kalir).
//  · Silme de fiyat/gorsel gibi KUYRUKTAN akar: alan='sil', deger=GEREKCE. Tabana
//    isleyen tek kol yine CI uygulayicisidir (duzelt.py --toplu {"id","sil"} yolu +
//    arsiv/urunler-arsiv.json kaydi) — ikinci yazim yolu YOK.
//  · CIFT ONAYIN SUNUCU AYAGI: `onay` alani urun id'sini BIREBIR tekrarlamak zorunda
//    (UI zaten yazdirtir; sunucu istemciye guvenmez). Yanlis tik tek basina bir
//    musteri-gorunur urunu dusuremez.
//  · R2 GORSELLERI SILINMEZ (mevcut kural). STL parcalari kuyruga yazmadan ONCE
//    stlCikar'in arsiv-teyitli tasima desenine BIREBIR uyarak arsiv/stl/'e tasinir;
//    teyit dusmezse silme kuyruga YAZILMAZ (fail-closed, veri kaybi yolu yok).
//  · GEREKCE yalniz D1 kuyruk satirinda + yerel guard logunda yasar; PUBLIC repoya
//    (arsiv dosyasi, commit mesaji) ISLENMEZ — tedarikci/kisi adi sizamasin.
//  · `gizli` alanindan AYRI kavram: gizle = yayindan dusur (kayit tabanda kalir),
//    sil = kaydi tabandan arsive tasi (geri yukleme: tools/urun-geri-yukle.py).
const SIL_GEREKCE_TAVANI = 200;

async function panelUrunSil(request, env, ctx) {
  let govde;
  try { govde = await request.json(); } catch (e) {
    return yjson({ hata: "gecersiz istek govdesi" }, 400);
  }
  const uid = typeof (govde && govde.urun_id) === "string" ? govde.urun_id.trim() : "";
  const onay = typeof (govde && govde.onay) === "string" ? govde.onay.trim() : "";
  const gerekce = typeof (govde && govde.gerekce) === "string" ? govde.gerekce.trim() : "";
  if (!URUN_ID_RX.test(uid)) { return yjson({ hata: "urun_id bicimsiz" }, 400); }
  if (onay !== uid) {
    return yjson({ hata: "onay, urun id'siyle birebir ayni olmali (cift onay)" }, 400);
  }
  if (!gerekce) { return yjson({ hata: "gerekce bos olamaz" }, 400); }
  if (gerekce.length > SIL_GEREKCE_TAVANI) {
    return yjson({ hata: "gerekce cok uzun (tavan " + SIL_GEREKCE_TAVANI + ")" }, 400);
  }
  if (/[\u0000-\u001f]/.test(gerekce)) {
    return yjson({ hata: "gerekce kontrol karakteri/satir sonu tasiyamaz" }, 400);
  }
  const ur = await env.KATALOG.prepare(
    "SELECT id FROM urunler WHERE id = ?").bind(uid).first();
  if (!ur) { return yjson({ hata: "urun katalogda yok" }, 404); }
  // STL parcalari ONCE arsive: binding yoksa parcalarin VARLIGI OLCULEMEZ ->
  // fail-closed 503 (arsivlenmemis STL birakma yolu acilmaz).
  if (!env.OZEL_DOSYA) {
    return yjson({ hata: "r2-baglanti-yok — STL arsivlenemeden silme kuyruklanmaz" }, 503);
  }
  const parcalar = await parcalariListele(env, uid);
  const ts0 = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
  let tasinan = 0;
  for (const parca of parcalar) {
    const anahtar = "stl/" + uid + "/" + parca.dosya;
    const nesne = await env.OZEL_DOSYA.get(anahtar);
    if (!nesne) { continue; } // listeyle yaris: dosya bu arada dusmus, tasinacak sey yok
    const arsiv = "arsiv/stl/" + uid + "/" + ts0 + "-" + parca.dosya;
    await env.OZEL_DOSYA.put(arsiv, nesne.body);
    const teyit = await env.OZEL_DOSYA.head(arsiv);
    if (!teyit || teyit.size !== parca.boyut) {
      return yjson({ hata: "arsiv-kopyasi-teyit-edilemedi — orijinaller SILINMEDI, " +
                     "silme kuyruga YAZILMADI (tasinan=" + tasinan + ")" }, 502);
    }
    await env.OZEL_DOSYA.delete(anahtar);
    tasinan++;
  }
  const kuyrukHata = await kuyrugaYaz(env, uid, "sil", gerekce);
  if (kuyrukHata) { return kuyrukHata; }
  uygulayiciTetikle(env, ctx);
  return yjson({ tamam: true, urun_id: uid, alan: "sil", hal: "beklemede",
                 stl_arsivlenen: tasinan }, 200);
}

async function panelUstyazimSil(request, env) {
  let govde;
  try { govde = await request.json(); } catch (e) {
    return yjson({ hata: "gecersiz istek govdesi" }, 400);
  }
  const id = parseInt(govde && govde.id, 10);
  if (!Number.isInteger(id) || id <= 0) { return yjson({ hata: "id gecersiz" }, 400); }
  try {
    // YALNIZ beklemede satir iptal edilir: islendi kaydi tabana COKMUS gecmistir,
    // hata kaydi teshis izidir — ikisi de silinmez.
    const g = await env.KATALOG.prepare(
      "DELETE FROM panel_ustyazim WHERE id = ? AND hal = 'beklemede'").bind(id).run();
    const silinen = (g && g.meta && g.meta.changes) || 0;
    if (!silinen) { return yjson({ hata: "satir beklemede degil ya da yok" }, 409); }
  } catch (e) {
    if (tabloYokMu(e)) { return yjson({ hata: "kuyruk tablosu yok — sema kosulmamis" }, 503); }
    throw e;
  }
  return yjson({ tamam: true, silinen: 1 }, 200);
}

/** Kuyruga satir dusunce CI uygulayicisini repository_dispatch ile durt. OPSIYONEL:
 *  GH_DISPATCH_TOKEN secret'i tanimli degilse SESSIZCE atlanir (cron/elle kol kapsar)
 *  — META_CAPI_TOKEN deseni: kod merge olur, canliyi bozmaz, Okan secret basinca
 *  canlanir. Hata da yutulur: kuyruk kaydi ZATEN basarili, tetik en-iyi-cabadir. */
function uygulayiciTetikle(env, ctx) {
  if (!env.GH_DISPATCH_TOKEN || !ctx || typeof ctx.waitUntil !== "function") { return; }
  const depo = env.GH_DEPO || "Pruvo138/pruvo";
  ctx.waitUntil(fetch("https://api.github.com/repos/" + depo + "/dispatches", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + env.GH_DISPATCH_TOKEN,
      "Accept": "application/vnd.github+json",
      "User-Agent": "pruvo-shop-panel",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ event_type: "panel-ustyazim" }),
  }).catch(() => {}));
}

// ═══════════════ URUNLER SEKMESI T2 — gorsel + STL + kaynak link ═══════════════
// TASARIM (BaBa cercevesi 30 Agu 2026, T1 hakem modeli AYNEN):
//  · GORSEL listesi GORUNURLUGE giden degisikliktir -> kuyruk->uygulayici->taban TEK
//    yoldan iner (alan='gorseller', deger=TAM listenin JSON'u). Panel tabana YAZMAZ.
//    Mevcut listeyi panel CANLI urunler.json'dan okur — taban TEK okuma kaynagi KALIR;
//    D1'e kopya gorsel-listesi kolonu ACILMADI (ikinci kopya = sessiz ayrisma sinifi).
//  · GORSEL yukleme R2'ye icerik-hash anahtarla gider; PUT'tan once head — mevcut
//    anahtar ASLA ezilmez. "Cikarma" = listeden dusurulmus TAM listenin ustyazimi;
//    R2 nesnesi SILINMEZ (hicbir gorsel-silme ucu YOK).
//  · STL: mevcut OZEL_DOSYA binding + /stl uclari duzleminde yukle/cikar. Yukleme
//    head-once (var olan ad 409). Cikarma = arsiv-teyitli tasima: arsiv/stl/... kopyasi
//    head ile dogrulanmadan orijinal SILINMEZ (fail-closed; veri kaybolmaz, liste duser).
//  · KAYNAK LINK yalniz GIZLI D1 duzleminde (panel_kaynak) yasar; tabana ve public
//    hicbir yuzeye ISLENMEZ (tedarikci gizliligi). urun_kaynak'a YAZILMAZ —
//    d1-kaynak-sync oradaki yabanci satiri SILERDI (sema dosyasindaki gerekce).

/** GET /yonet/urun-gorseller?id= -> {id, gorseller, bekleyen} — CANLI tabandan.
 *  urunler.json buyuk (5-15 MB) oldugu icin TAM JSON.parse YAPILMAZ: tools/duzelt.py
 *  `_atomic_write` (json.dump indent=2) sozlesmesiyle urun blogu dilimlenir — urun
 *  acilisi "\n  {", kapanisi "\n  }", alanlar 4 bosluk girintide. Dilim parse
 *  EDILEMEZSE 502 taban-bicimi doner (sessiz bos liste YOK — fail-loud). */
async function urunGorseller(env, url) {
  const uid = url.searchParams.get("id") || "";
  if (!URUN_ID_RX.test(uid)) { return yjson({ hata: "gecersiz-id" }, 400); }
  const taban = ((env && env.SITE_URL) || "https://pruvo3d.com").replace(/\/$/, "");
  let metin;
  try {
    const c = await fetch(taban + "/urunler.json", {
      headers: { "Cache-Control": "no-cache" },
      cf: { cacheTtl: 0, cacheEverything: false },
    });
    if (!c.ok) { return yjson({ hata: "taban-okunamadi", kod: c.status }, 502); }
    metin = await c.text();
  } catch (e) {
    return yjson({ hata: "taban-okunamadi" }, 502);
  }
  // Igne 4-bosluk girintili "id" alanidir: aciklama METNI icindeki ham '"id":' bu
  // desene uyamaz (JSON dizesinde ham satir sonu olamaz, ic nesneler daha derindedir).
  const igne = "\n    \"id\": " + JSON.stringify(uid);
  const i = metin.indexOf(igne);
  if (i < 0) { return yjson({ hata: "urun-tabanda-yok" }, 404); }
  const bas = metin.lastIndexOf("\n  {", i);
  const son = metin.indexOf("\n  }", i);
  if (bas < 0 || son < 0) { return yjson({ hata: "taban-bicimi" }, 502); }
  let urun;
  try { urun = JSON.parse(metin.slice(bas + 1, son + 4)); } catch (e) {
    return yjson({ hata: "taban-bicimi" }, 502);
  }
  let bekleyen = null;
  const b = await tabloMerdiveni(
    () => env.KATALOG.prepare(
      "SELECT id, deger, ts FROM panel_ustyazim WHERE hal = 'beklemede'" +
      " AND urun_id = ? AND alan = 'gorseller'").bind(uid).first(),
    () => null);
  if (b) { bekleyen = { id: b.id, deger: b.deger, ts: b.ts }; }
  return yjson({ id: uid, gorseller: urun.gorseller || [], bekleyen: bekleyen }, 200);
}

// Gorsel yukleme: govde ham dosya baytlaridir. Tur DOSYA IMZASINDAN okunur
// (Content-Type basligina guvenilmez); katalog normu jpg (88953/89008), png azinlik.
const GORSEL_BOYUT_TAVANI = 8 * 1024 * 1024;

/** POST /yonet/gorsel-yukle?id= -> {tamam, url, zaten_vardi} */
async function gorselYukle(request, env, url) {
  const uid = url.searchParams.get("id") || "";
  if (!URUN_ID_RX.test(uid)) { return yjson({ hata: "gecersiz-id" }, 400); }
  if (!env.MEDYA) {
    return yjson({ hata: "medya-r2-baglanti-yok — MEDYA binding'li deploy gerekli" }, 503);
  }
  const bayt = await request.arrayBuffer();
  if (!bayt.byteLength) { return yjson({ hata: "bos govde" }, 400); }
  if (bayt.byteLength > GORSEL_BOYUT_TAVANI) {
    return yjson({ hata: "boyut tavani 8 MB" }, 400);
  }
  const b = new Uint8Array(bayt);
  let uzanti = null, tip = null;
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) { uzanti = "jpg"; tip = "image/jpeg"; }
  else if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) {
    uzanti = "png"; tip = "image/png";
  } else {
    return yjson({ hata: "yalniz JPEG/PNG (tur dosya imzasindan okunur)" }, 400);
  }
  const ozet = await crypto.subtle.digest("SHA-256", bayt);
  const hex = [...new Uint8Array(ozet)].map((x) => x.toString(16).padStart(2, "0")).join("");
  // ICERIK-HASH ANAHTAR: ayni icerik ayni anahtara duser; farkli icerik farkli
  // anahtara — mevcut bir anahtarin USTUNE farkli baytlar YAZILAMAZ (yapisal).
  // head-once yine de uygulanir: var olan anahtara PUT HIC atilmaz.
  const anahtar = "urunler/panel-" + hex.slice(0, 20) + "." + uzanti;
  const mevcut = await env.MEDYA.head(anahtar);
  if (!mevcut) {
    await env.MEDYA.put(anahtar, bayt, { httpMetadata: { contentType: tip } });
    const teyit = await env.MEDYA.head(anahtar);
    if (!teyit) { return yjson({ hata: "r2-yazim-teyit-edilemedi" }, 502); }
  }
  const medyaTaban = ((env && env.MEDYA_TABAN) || "https://media.pruvo3d.com")
    .replace(/\/$/, "");
  return yjson({ tamam: true, url: medyaTaban + "/" + anahtar,
                 zaten_vardi: !!mevcut }, 200);
}

// STL yukleme/cikarma — stlIndir'in savunma duzeni AYNEN (ayirac/ust-dizin yok,
// yalniz .stl/.3mf). 280 MB'lik dosyalar var (bkz. /stl yorumu) -> govde belege
// ALINMAZ, stream PUT edilir; tavan Content-Length'ten olculur.
const STL_BOYUT_TAVANI = 300 * 1024 * 1024;
// STL_DOSYA_ADI_RX / stlDosyaAdiGecersiz / stlDosyaAdiNormalize -> "DOSYA ADI KANONIK
// BICIMI" blogu (DRIVE_TABAN'in altinda): UC okuyucu ayni fonksiyonu cagirir.

/** POST /yonet/stl-yukle?id=&dosya= (govde=ham dosya) -> {tamam, dosya, boyut}
 *  `dosya` yanitta NORMALIZE edilmis addir (R2 anahtarindaki ad); ekran onu gosterir. */
async function stlYukle(request, env, url) {
  const uid = url.searchParams.get("id") || "";
  if (!/^[a-z0-9-]{1,120}$/.test(uid)) { return yjson({ hata: "gecersiz-id" }, 400); }
  if (!env.OZEL_DOSYA) { return yjson({ hata: "r2-baglanti-yok" }, 503); }
  const norm = stlDosyaAdiNormalize(url.searchParams.get("dosya") || "");
  if (norm.hata) {
    return yjson({ hata: "gecersiz dosya adi: " + norm.hata, kural: norm.kural }, 400);
  }
  const dosya = norm.ad;
  const boy = parseInt(request.headers.get("Content-Length") || "0", 10);
  if (boy > STL_BOYUT_TAVANI) { return yjson({ hata: "boyut tavani 300 MB" }, 400); }
  const anahtar = "stl/" + uid + "/" + dosya;
  const mevcut = await env.OZEL_DOSYA.head(anahtar);
  if (mevcut) {
    return yjson({ hata: "dosya zaten var — mevcut anahtar EZILMEZ; farkli ad kullanin",
                   dosya: dosya }, 409);
  }
  await env.OZEL_DOSYA.put(anahtar, request.body);
  const teyit = await env.OZEL_DOSYA.head(anahtar);
  if (!teyit) { return yjson({ hata: "r2-yazim-teyit-edilemedi" }, 502); }
  return yjson({ tamam: true, dosya: dosya, boyut: teyit.size }, 200);
}

/** POST /yonet/stl-cikar {id, dosya} -> {tamam, arsiv} — arsiv-teyitli tasima.
 *  Kopya (arsiv/stl/<id>/<ts>-<dosya>) head ile boyut dahil DOGRULANMADAN orijinal
 *  SILINMEZ: teyit dusmezse dosya YERINDE kalir ve uc 502 doner (veri kaybi yolu yok). */
async function stlCikar(request, env) {
  let govde;
  try { govde = await request.json(); } catch (e) {
    return yjson({ hata: "gecersiz istek govdesi" }, 400);
  }
  const uid = typeof (govde && govde.id) === "string" ? govde.id.trim() : "";
  const dosya = typeof (govde && govde.dosya) === "string" ? govde.dosya : "";
  if (!/^[a-z0-9-]{1,120}$/.test(uid)) { return yjson({ hata: "gecersiz-id" }, 400); }
  if (!env.OZEL_DOSYA) { return yjson({ hata: "r2-baglanti-yok" }, 503); }
  const adlar = stlDosyaAdiAdaylari(dosya);          // kanonik (+ eski duzen ham ad)
  if (!adlar.length) { return yjson({ hata: "dosya-yok" }, 404); }
  // stlIndir savunma 2 deseni: LISTEDE olmayan ad 404.
  const parcalar = await parcalariListele(env, uid);
  const parca = parcalar.find((p) => adlar.includes(p.dosya));
  if (!parca) { return yjson({ hata: "dosya-yok" }, 404); }
  const anahtar = "stl/" + uid + "/" + parca.dosya;
  const nesne = await env.OZEL_DOSYA.get(anahtar);
  if (!nesne) { return yjson({ hata: "dosya-yok" }, 404); }
  const ts = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
  const arsiv = "arsiv/stl/" + uid + "/" + ts + "-" + parca.dosya;
  await env.OZEL_DOSYA.put(arsiv, nesne.body);
  const teyit = await env.OZEL_DOSYA.head(arsiv);
  if (!teyit || teyit.size !== parca.boyut) {
    return yjson({ hata: "arsiv-kopyasi-teyit-edilemedi — orijinal SILINMEDI" }, 502);
  }
  await env.OZEL_DOSYA.delete(anahtar);
  return yjson({ tamam: true, arsiv: arsiv }, 200);
}

// Kaynak link — gizli duzlem. Okuma birlesimi: panel_kaynak satiri VARSA o kazanir
// (link='' = cikarildi golgesi), yoksa urun_kaynak (d1-kaynak-sync duzlemi). Iki deger
// de kaynakLinkSuz'dan gecer (https disi/bozuk deger panele HIC cikmaz).
const KAYNAK_LINK_TAVANI = 500;

/** GET /yonet/urun-kaynak?id= -> {link, duzlem, cikarildi} */
async function urunKaynak(env, url) {
  const uid = url.searchParams.get("id") || "";
  if (!URUN_ID_RX.test(uid)) { return yjson({ hata: "gecersiz-id" }, 400); }
  const p = await tabloMerdiveni(
    () => env.KATALOG.prepare(
      "SELECT id, link FROM panel_kaynak WHERE id = ?").bind(uid).first(),
    () => null);
  if (p) {
    return yjson({ link: kaynakLinkSuz(p.link), duzlem: "panel",
                   cikarildi: !p.link }, 200);
  }
  const s = await tabloMerdiveni(
    () => env.KATALOG.prepare(
      "SELECT id, link FROM urun_kaynak WHERE id = ?").bind(uid).first(),
    () => null);
  return yjson({ link: kaynakLinkSuz(s && s.link), duzlem: s ? "sync" : "",
                 cikarildi: false }, 200);
}

/** POST /yonet/kaynak-yaz {id, link} — link https://... = ekle/ust yazim;
 *  link "" = cikar (golge satir; sync linkini de listeden dusurur). */
async function kaynakYaz(request, env) {
  let govde;
  try { govde = await request.json(); } catch (e) {
    return yjson({ hata: "gecersiz istek govdesi" }, 400);
  }
  const uid = typeof (govde && govde.id) === "string" ? govde.id.trim() : "";
  const link = typeof (govde && govde.link) === "string" ? govde.link.trim() : null;
  if (!URUN_ID_RX.test(uid)) { return yjson({ hata: "urun_id bicimsiz" }, 400); }
  if (link === null) {
    return yjson({ hata: "link metin olmali (cikarma icin bos dize)" }, 400);
  }
  if (link.length > KAYNAK_LINK_TAVANI) { return yjson({ hata: "link cok uzun" }, 400); }
  if (link && (!/^https:\/\//i.test(link) || /[\s"'<>\\]/.test(link) ||
      /[\u0000-\u001f]/.test(link))) {
    return yjson({ hata: "link https:// ile baslamali (bosluk/tirnak tasiyamaz)" }, 400);
  }
  const ur = await env.KATALOG.prepare(
    "SELECT id FROM urunler WHERE id = ?").bind(uid).first();
  if (!ur) { return yjson({ hata: "urun katalogda yok" }, 404); }
  try {
    await env.KATALOG.prepare(
      "INSERT INTO panel_kaynak (id, link, ts) VALUES (?, ?, ?)" +
      " ON CONFLICT(id) DO UPDATE SET link = excluded.link, ts = excluded.ts")
      .bind(uid, link, new Date().toISOString()).run();
  } catch (e) {
    if (tabloYokMu(e)) {
      return yjson({ hata: "panel_kaynak tablosu yok — sema kosulmamis" }, 503);
    }
    throw e;
  }
  return yjson({ tamam: true, cikarildi: !link }, 200);
}

/**
 * /yonet* yonlendirici. altYol = "/", "/liste", "/durum", "/kargo", "/havale-onay", "/stl",
 * "/konfigur-golge".
 * KAPI SIRASI (fail-closed):
 *   1. YONET_ANAHTAR secret YOK -> her sey 404 (ozellik kapali; giris formu BILE yok),
 *   2. POST /wa-siparis -> Ege ucu (yonetim anahtari YA DA EGE_ANAHTAR),
 *   3. POST /yonet -> giris kapisi (sifre kutusu; dogruysa cerez + 302),
 *   4. anahtar yok/yanlis -> GET /yonet'te sifre kutusu, DIGER her ucta 404 (varlik sizmasin),
 *   5. yetkili -> normal yonlendirme.
 *
 * 🔴 1. ADIM NEDEN 2.'DEN ONCE: `YONET_ANAHTAR` yoksa ozellik KAPALIDIR ve kapali
 * ozelligin altinda YAZMA yolu da acik kalamaz -> `/wa-siparis` bu kapinin ARKASINDADIR,
 * yani EGE_ANAHTAR tek basina siparis YAZDIRAMAZ. Ters sira, ayarlanmamis bir secret'in
 * arkasinda acik bir yazma ucu birakirdi (sessiz-hata sinifi). Nobetci:
 * `shop/test/wa-siparis.mjs` "OZELLIK KAPALI:" iddialari; ayirt edici mutant (kapiyi
 * /wa-siparis blogunun ARKASINA tasir) -> `tools/wa-yetki-mutasyon.py` M2.
 *
 * ⚠️ Bu yorumu fonksiyon GOVDESINE tasima: `tools/yonet-cerez-mutasyon.py`in 6 mutanti
 * imza satirini gate satirina BITISIK varsayan capalar kullaniyor; araya satir girerse
 * o harness BAYAT duser ve 25 mutantin hepsi olcusuz kalir.
 *
 * telegram: index.js'in telegram fonksiyonu.
 */
export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;
  // WHATSAPP SIPARIS UCU — IKI anahtardan biri yeter: yonetim anahtari (Okan) ya da
  // yalnizca bu uca yetkili EGE_ANAHTAR (bkz. egeAnahtarGecerli). Ikisi de yok/yanlissa
  // /yonet* ile AYNI davranis: 404 (ucun varligi sizmaz). EGE_ANAHTAR yalnizca BU kolda
  // okunur -> /liste, /durum, /kargo, /havale-onay, /stl onunla ACILMAZ; giris ekranini
  // da ACMAZ (havale onayi TAHSILAT damgasidir: yalniz yonetim anahtari yazabilir).
  if (altYol === "/wa-siparis" && m === "POST") {
    if (!anahtarGecerli(request, url, env) && !egeAnahtarGecerli(request, env)) {
      return yon404();
    }
    return waSiparis(request, env);
  }
  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }
  if (!anahtarGecerli(request, url, env)) {
    return (altYol === "/" && m === "GET") ? girisEkrani(url) : yon404();
  }
  if (altYol === "/" && m === "GET") { return sayfa(); }
  if (altYol === "/liste" && m === "GET") { return liste(env, url); }
  if (altYol === "/durum" && m === "POST") { return durumDegistir(request, env, ctx); }
  if (altYol === "/kargo" && m === "POST") { return kargo(request, env, ctx, telegram); }
  // K284 — havale onayi: /kargo ile AYNI SINIF ayri/dar uc (dekont referansi ZORUNLU).
  if (altYol === "/havale-onay" && m === "POST") { return havaleOnay(request, env, ctx); }
  if (altYol === "/stl" && m === "GET") { return stlIndir(env, url); }
  if (altYol === "/stl-liste" && m === "GET") { return stlListe(env, url); }
  // FAZ 3 kontrol kipi — SALT OKUMA (yazma/yan etki YOK).
  if (altYol === "/konfigur-golge" && m === "GET") { return konfigurGolge(env, url); }
  // URUNLER SEKMESI (T1) — hepsi yonetim anahtarinin ARKASINDA. EGE_ANAHTAR bu
  // uclari ACAMAZ: o anahtar yalniz yukaridaki /wa-siparis kolunda okunur.
  if (altYol === "/urunler" && m === "GET") { return panelUrunListe(env, url); }
  if (altYol === "/urunler-kuyruk" && m === "GET") { return panelKuyruk(env); }
  if (altYol === "/urunler-ustyazim" && m === "POST") { return panelUstyazimYaz(request, env, ctx); }
  if (altYol === "/urunler-ustyazim-sil" && m === "POST") { return panelUstyazimSil(request, env); }
  // TEKIL urun silme (Okan emri 2 Eyl) — ayni kapinin ARKASINDA, cift onayli.
  if (altYol === "/urun-sil" && m === "POST") { return panelUrunSil(request, env, ctx); }
  // URUNLER SEKMESI (T2) — gorsel + STL + kaynak link; ayni kapinin ARKASINDA.
  if (altYol === "/urun-gorseller" && m === "GET") { return urunGorseller(env, url); }
  if (altYol === "/gorsel-yukle" && m === "POST") { return gorselYukle(request, env, url); }
  if (altYol === "/stl-yukle" && m === "POST") { return stlYukle(request, env, url); }
  if (altYol === "/stl-cikar" && m === "POST") { return stlCikar(request, env); }
  if (altYol === "/urun-kaynak" && m === "GET") { return urunKaynak(env, url); }
  if (altYol === "/kaynak-yaz" && m === "POST") { return kaynakYaz(request, env); }
  return yon404();
}

// Giris ekrani: TEK sifre alani. Siparis/PII/panel govdesi/JS YOK; baslikta "Sipariş
// Yönetimi" gibi ne oldugunu soyleyen bir ipucu da YOK. `__EYLEM__` istegin kendi
// yoluyla degistirilir (girisEkrani); anahtar POST GOVDESINDE gider, sorgu dizesinde DEGIL.
const GIRIS_HTML = `<!doctype html><html lang="tr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>PRUVO</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%2312294d'/><text x='50' y='55' font-family='Arial,Helvetica,sans-serif' font-size='72' font-weight='800' fill='%23f59e0b' text-anchor='middle' dominant-baseline='central'>P</text></svg>">
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
 background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#1f2937}
form{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:22px;
 display:flex;flex-direction:column;gap:12px;min-width:260px}
h1{font-size:18px;margin:0;color:#12294d}
input{font-size:16px;padding:9px 10px;border:1px solid #e5e7eb;border-radius:6px}
button{font-size:16px;padding:9px 10px;border:0;border-radius:6px;background:#12294d;
 color:#fff;cursor:pointer}
</style></head><body>
<form method="post" action="__EYLEM__">
 <h1>PRUVO</h1>
 <input type="password" name="sifre" autocomplete="current-password" autofocus>
 <button type="submit">Gir</button>
</form>
</body></html>`;

// Sayfa HTML en altta (okunurluk): mobil uyumlu, lacivert/gri, harici kutuphane YOK.
const SAYFA_HTML = `<!doctype html><html lang="tr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>PRUVO — Sipariş Yönetimi</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%2312294d'/><text x='50' y='55' font-family='Arial,Helvetica,sans-serif' font-size='72' font-weight='800' fill='%23f59e0b' text-anchor='middle' dominant-baseline='central'>P</text></svg>">
<style>
:root{--lacivert:#12294d;--gri:#f3f4f6;--kenar:#e5e7eb;--kirmizi:#b91c1c;--sari:#f59e0b}
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--gri);color:#1f2937;font-size:15px}
header{background:var(--lacivert);color:#fff;padding:12px 16px;position:sticky;top:0;z-index:5;
 display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
header h1{font-size:18px;margin:0}
header .araclar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
select,button,input{font-size:15px;padding:7px 10px;border:1px solid var(--kenar);border-radius:6px}
button{background:var(--lacivert);color:#fff;border:0;cursor:pointer}
button.sil{background:var(--kirmizi)}
button.ikincil{background:#6b7280}
main{padding:12px;max-width:960px;margin:0 auto}
.kart{background:#fff;border:1px solid var(--kenar);border-radius:10px;padding:14px;margin:0 0 14px}
.ust{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center}
/* ACILIR/KAPANIR KART: kapali baslikta YALNIZ no/durum/tarih/tutar/kalem sayisi durur —
   musteri adi/telefon/adres/e-posta acilinca gorunur (omuz-ustu gizliligi). */
summary.ust{cursor:pointer;list-style:none;user-select:none}
summary.ust::-webkit-details-marker{display:none}
summary.ust::after{content:"▸";color:#6b7280;font-size:14px}
details[open]>summary.ust::after{content:"▾"}
.no{font-weight:bold;font-size:16px;color:var(--lacivert)}
.rozet{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:bold;
 background:#e5edff;color:var(--lacivert)}
.rozet.kargolandi{background:#dbeafe;color:#1e40af}
.rozet.tamamlandi{background:#dcfce7;color:#166534}
.rozet.iptal{background:#fee2e2;color:#991b1b}
.rozet.havale-bekliyor{background:#fef9c3;color:#854d0e}
.rozet.incele{background:#ffedd5;color:#9a3412}
.rozet.odendi{background:#e0e7ff;color:#3730a3}
.rozet.uretimde{background:#ede9fe;color:#5b21b6}
.rozet.bekliyor{background:#f3f4f6;color:#4b5563}
.rozet.basarisiz{background:#fce7f3;color:#9d174d}
/* URUNLER SEKMESI (T1) — kuyruk halleri + sekme cubugu + duzenleme formu */
.rozet.beklemede{background:#fef9c3;color:#854d0e}
.rozet.islendi{background:#dcfce7;color:#166534}
.rozet.hata{background:#fee2e2;color:#991b1b}
.sekmeler{display:flex;gap:6px}
.sekme{background:transparent;color:#fff;border:1px solid #ffffff55;border-radius:6px;cursor:pointer}
.sekme.aktif{background:#fff;color:var(--lacivert);font-weight:bold}
.alan-form{display:flex;flex-direction:column;gap:8px;margin-top:8px}
.alan-form label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:#374151}
/* URUNLER SEKMESI (T2) — gorsel seridi + STL + kaynak link bolumleri */
.t2bolum{border-top:1px dashed var(--kenar);margin-top:10px;padding-top:8px;font-size:13px}
.t2bolum h4{margin:0 0 6px;font-size:13px;color:var(--lacivert)}
.gserit{display:flex;flex-wrap:wrap;gap:8px}
.gkutu{display:flex;flex-direction:column;align-items:center;gap:2px}
.gkutu img{width:72px;height:72px;object-fit:cover;border-radius:6px;border:1px solid var(--kenar)}
.gkutu .sil{font-size:11px;padding:1px 6px}
.alan-form input,.alan-form textarea{font-family:inherit;font-size:15px;padding:7px 10px;
 border:1px solid var(--kenar);border-radius:6px}
.siparis-grubu{margin:0 0 20px}
.grup-baslik{display:block;margin:0 0 9px;padding:7px 12px;border-radius:8px;font-size:15px}
/* KANAL rozeti — yalniz site DISI kanalda basilir (WhatsApp/Ege). Site siparisinde
   ekran bugunku gibi kalir (rozet HIC olusmaz). */
.rozet.kanal{background:#dcfce7;color:#14532d}
.mus{font-size:14px;color:#374151;margin:8px 0}
.satir{border:1px solid var(--kenar);border-radius:8px;padding:10px;margin:8px 0;background:#fafafa}
.filrenk{font-size:17px;font-weight:bold;color:var(--lacivert)}
.filrenk .renk{color:#b45309}
.baski{font-size:13px;color:#374151;background:#fff7ed;border-left:3px solid var(--sari);
 padding:6px 8px;margin:6px 0;border-radius:4px}
.eylemler{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.kargoform{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.durumsecici{display:flex;gap:6px;align-items:center}
.kucuk{font-size:12px;color:#6b7280}
.hata{color:var(--kirmizi)}
a.indir{display:inline-block;padding:6px 10px;background:#374151;color:#fff;border-radius:6px;
 text-decoration:none;font-size:13px}
.yok{font-size:12px;color:#92400e;background:#fef3c7;padding:4px 8px;border-radius:4px}
/* URETIM DOSYASI KAYNAKLARI (Drive). Sinif GORSEL olarak da ayrilir: yanlis dosyanin
   basilmasi en pahali uretim hatasidir, "ARSIVDE — BASILMAZ" satiri kirmizi/uzeri
   cizili durur ve kanonik satirla KARISTIRILAMAZ. */
.kaynak{font-size:13px;color:#374151;background:#f8fafc;border-left:3px solid var(--lacivert);
 padding:6px 8px;margin:6px 0;border-radius:4px}
.kdosya{margin:3px 0}
.sinif{display:inline-block;min-width:170px;font-size:12px}
.sinif.kanonik{color:#166534}
.sinif.yedek{color:#1e40af}
.sinif.arsiv{color:var(--kirmizi)}
.sinif.belirsiz{color:#92400e}
.kdosya.arsiv a.indir{background:var(--kirmizi);text-decoration:line-through}
.gecmis{font-size:12px;color:#6b7280;margin-top:6px}
</style></head><body>
<header>
 <h1>PRUVO Yönetim</h1>
 <nav class="sekmeler">
  <button id="sekmeSiparis" class="sekme aktif">Siparişler</button>
  <button id="sekmeUrun" class="sekme">Ürünler</button>
 </nav>
 <div class="araclar" id="siparisAraclar">
  <select id="durumSuzgec">
   <option value="">Tümü</option>
   <option value="odendi">Ödendi</option>
   <option value="havale-bekliyor">Havale bekliyor</option>
   <option value="uretimde">Üretimde</option>
   <option value="kargolandi">Kargolandı</option>
   <option value="tamamlandi">Tamamlandı</option>
   <option value="incele">İncele</option>
   <option value="iptal">İptal</option>
  </select>
  <button id="yenile">Yenile</button>
 </div>
</header>
<main id="liste"><p>Yükleniyor…</p></main>
<main id="urunler" hidden>
 <div class="kart">
  <div class="ust">
   <input id="urunAra" placeholder="Ürün ara (id ya da başlık)" style="flex:1;min-width:180px">
   <button id="urunAraBtn">Ara</button>
  </div>
  <p class="kucuk">Kaydet <b>kuyruğa</b> yazar; değişiklik uygulayıcı işleyip site yeniden
  yayınlanınca canlıya çıkar (dakikalar). Parametrik (sarı) üründe fiyat değiştirilemez.
  Ürün silme TEKİLDİR: karttaki "Sil (arşive)" kuyruğa yazar; taban kaydı arşive taşınır
  (geri getirilebilir), R2 görselleri silinmez. Gizle ile karışmaz: gizli ürün tabanda kalır.</p>
 </div>
 <section id="kuyrukKutu"></section>
 <section id="urunListe"></section>
</main>
<script>
var PANEL_TUM_DURUMLAR=${JSON.stringify([...TUM_DURUMLAR])};
var PANEL_GRUP_SIRASI=${JSON.stringify(PANEL_GRUP_SIRASI)};
function esc(s){s=(s==null?"":""+s);return s.replace(/&/g,"&amp;").replace(/</g,"&lt;")
 .replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function tl(k){k=Math.max(0,Math.floor(+k||0));var t=Math.floor(k/100),ku=(""+(k%100)).padStart(2,"0");
 return (""+t).replace(/\\B(?=(\\d{3})+(?!\\d))/g,".")+","+ku+" TL";}
async function api(yol,secenek){
 // Kimlik HttpOnly cerezden gelir; sayfa JS'i anahtari GORMEZ (okuyamaz da).
 secenek=secenek||{};secenek.credentials="same-origin";
 var c=await fetch("/api/shop/yonet"+yol,secenek);
 var v=null;try{v=await c.json();}catch(e){}
 return {kod:c.status,govde:v};
}
function durumRozet(d){return '<span class="rozet '+esc(d)+'">'+esc(d)+'</span>';}
// URETIM DOSYASI KAYNAKLARI — her dosya AYRI satir, sinif etiketiyle, TIKLANABILIR
// (yeni sekme). 🔴 SESSIZ BOSLUK YASAK: liste bossa "kaynak yok", baglantisi olmayan
// sinif isareti varsa "baglanti uretilemedi" ACIKCA yazilir. Bos birakmak, dosyanin
// OLMADIGINI degil OLCULEMEDIGINI gizlerdi.
function kaynakHtml(k){
 var d=(k&&k.uretim_kaynaklari)||[];
 if(!d.length){
  return '<span class="yok">kaynak yok — üretim notunda Drive bağlantısı (fileId) geçmiyor</span>';
 }
 return d.map(function(x){
  var sinif=esc(x.sinif||"belirsiz");
  var et='<span class="sinif '+sinif+'">'+esc(x.etiket||"Sınıf belirsiz")+'</span> ';
  var ad=x.dosya?esc(x.dosya):"(dosya adı notta yok)";
  if(!x.url){
   return '<div class="kdosya '+sinif+'">'+et+ad+
    ' <span class="yok">bağlantı üretilemedi — notta fileId yok</span></div>';
  }
  return '<div class="kdosya '+sinif+'">'+et+
   '<a class="indir" href="'+esc(x.url)+'" target="_blank" rel="noopener">'+ad+'</a></div>';
 }).join("");
}
// URETICI KAYNAGI (platform urun sayfasi). 🔴 SESSIZ BOSLUK YASAK: kayit yoksa
// "kaynak kaydı yok" ACIKCA yazilir — bos birakmak "kaynak YOK"u degil "OLCULEMEDI"yi
// gizlerdi. Suzgec Worker tarafinda da uygulanir (kaynakLinkSuz); buradaki ikinci
// savunmadir: https disi / bozuk deger href'e GECMEZ, ham deger de basilmaz.
// ⚠️ REGEX KACISLAMASI: bu kod SAYFA_HTML sablon dizesinin ICINDE yasar; sablon
// "\/" -> "/" indirdigi icin regex KAYNAKTA "\\/" diye yazilir (yoksa sunulan
// sayfada "/^https:///" olur, "//" yorum baslatir ve TUM script derlenmez).
function kaynakLinkHtml(k){
 var u=k&&k.kaynak_link;
 if(!(typeof u==="string"&&/^https:\\/\\//i.test(u))){
  return '<span class="yok">kaynak kaydı yok</span>';
 }
 return '<a class="indir" href="'+esc(u)+'" title="'+esc(u)+
  '" target="_blank" rel="noopener">kaynak sayfası</a>';
}
function satirHtml(no,k){
 var indir;
 if(k.parametrik){
  // Anahtar URL'e GOMULMEZ: gezinme de cerezi tasir (SameSite=Strict, Path=/).
  indir='<a class="indir" href="/api/shop/yonet/stl?siparis_no='+encodeURIComponent(no)+
   '&kalem='+k.kalem+'">STL üret + indir</a>';
 }else{
  // COK-PARCA: dugme parca listesini ceker, parcalar tek tek indirilir (zip yok).
  var kutuId='parca-'+no+'-'+k.kalem;
  // data-parca: kart ILK acildiginda kartAc() bu kutuyu bir kez doldurur (lazy).
  // Dugme MANUEL YENILEME olarak KALIR (liste bayatlarsa tekrar cekilir).
  indir='<button class="ikincil" onclick="parcalar(\\''+esc(no)+'\\',\\''+esc(k.id)+
   '\\',\\''+kutuId+'\\')">Üretim dosyaları</button>'+
   '<span id="'+kutuId+'" data-parca="1" data-no="'+esc(no)+'" data-id="'+esc(k.id)+'"></span>';
 }
 var baslikLink=k.urun_url?
  '<a href="'+esc(k.urun_url)+'" target="_blank" rel="noopener">'+esc(k.baslik)+'</a>':
  esc(k.baslik);
 // Beyan (malzeme · renk) YALNIZ varsa basilir; fiziksel kalemde " · " gibi yarim bir satir
 // yerine "Hazır ürün" yazar — ekran kaydin ne oldugunu SOYLER, bosluk birakmaz.
 var filrenk=(k.malzeme||k.renk)?
  esc(k.malzeme)+' · <span class="renk">'+esc(k.renk)+'</span>':
  (k.tur==='fiziksel'?'Hazır ürün':'');
 return '<div class="satir">'+
  '<div class="filrenk">'+filrenk+' × '+esc(k.adet)+'</div>'+
  '<div>'+baslikLink+(k.parametre_detay?' <span class="kucuk">['+esc(k.parametre_detay)+']</span>':'')+'</div>'+
  '<div class="kucuk">Ürün kodu: '+esc(k.id)+'</div>'+
  '<div class="baski">🖨️ '+esc(k.baski_oneri)+'</div>'+
  '<div class="kaynak">📁 Üretim dosyası (Drive): '+kaynakHtml(k)+'</div>'+
  '<div class="kaynak">🔗 Üretici kaynağı: '+kaynakLinkHtml(k)+'</div>'+
  indir+
  '</div>';
}
function boyutMetni(b){
 if(!(b>0))return "";
 if(b>=1048576)return " ("+(b/1048576).toFixed(1)+" MB)";
 if(b>=1024)return " ("+Math.round(b/1024)+" KB)";
 return " ("+b+" B)";
}
async function parcalar(no,id,kutuId){
 var kutu=document.getElementById(kutuId);
 kutu.innerHTML=' yükleniyor…';
 var r=await api("/stl-liste?id="+encodeURIComponent(id));
 if(r.kod!==200){kutu.innerHTML=' <span class="hata">liste alınamadı ('+r.kod+')</span>';return;}
 var p=(r.govde&&r.govde.parcalar)||[];
 if(!p.length){
  kutu.innerHTML=' <span class="yok">'+esc((r.govde&&r.govde.not)||"dosya yok")+'</span>';
  return;
 }
 kutu.innerHTML=" "+p.map(function(x){
  return '<a class="indir" style="margin:2px 4px 2px 0" href="/api/shop/yonet/stl?id='+
   encodeURIComponent(id)+'&dosya='+encodeURIComponent(x.dosya)+
   '&siparis_no='+encodeURIComponent(no)+'">'+
   esc(x.dosya)+esc(boyutMetni(x.boyut))+'</a>';
 }).join("");
}
/* KAYNAK SATIRI — siparis hangi kanaldan/hangi reklamdan geldi.
 * 🔴 BURADA SINIFLAMA YOK: s.kaynak alani sunucuda shop/src/kanal-sinif.mjs
 * kaynakOzeti() ile uretilir; bu fonksiyon YALNIZCA BASAR. Tarayiciya ikinci bir
 * kural yazilsaydi, rapor ile ekran ayni siparis icin farkli sey soylerdi.
 * 🔒 ga_client_id / fbp / fbc BURAYA GELMEZ — /liste JSON'unda zaten YOKLAR
 * (kaynakOzeti beyaz-listesi). Gerekce: kanal-sinif.mjs gizlilik blogu.
 * SESSIZ BOSLUK YASAK: atif yoksa "kaynak kaydı yok" ACIKCA yazilir (kaynakLinkHtml
 * ile AYNI dil; ikinci sozluk acilmaz) — bos hucre "kaynak YOK"u "OLCULEMEDI"den
 * ayirt ettirmezdi.
 * ⚠️ BU YORUM SAYFA_HTML SABLON DIZESININ ICINDE YASAR: buraya tek bir backtick
 * girerse sablon ERKEN KAPANIR ve yonet.js modulu ARTIK IMPORT EDILEMEZ. (Bu is
 * sirasinda GERCEKLESTI: "node --check yonet.js" YESIL kaldi — .js dosyasi
 * CommonJS olarak ayristirildigi icin gormedi; kirmizi yalnizca kardes testlerde
 * yandi. Kod ornegi yazarken tirnak kullan, backtick DEGIL.) */
function kaynakSatiriHtml(s){
 var k=s&&s.kaynak;
 if(!k){return '';}
 var parcalar=[];
 if(k.utm_source){parcalar.push('kaynak: '+esc(k.utm_source));}
 if(k.utm_medium){parcalar.push('ortam: '+esc(k.utm_medium));}
 if(k.utm_campaign){parcalar.push('kampanya: '+esc(k.utm_campaign));}
 if(k.utm_id){parcalar.push('utm_id: '+esc(k.utm_id));}
 if(k.ref){parcalar.push('ref: '+esc(k.ref));}
 if(k.grup){parcalar.push('grup: '+esc(k.grup));}
 if(k.src){parcalar.push('src: '+esc(k.src));}
 var govde=parcalar.length?parcalar.join(' · ')
  :'<span class="yok">kaynak kaydı yok</span>';
 return '<div class="kucuk kaynak-atif">📣 Kaynak: <b>'+esc(k.etiket||k.kova||'')+
  '</b> <span class="kucuk">('+esc(k.sebep||'')+')</span> — '+govde+'</div>';
}
function kartHtml(s){
 var kalem=s.kalemler.map(function(k){return satirHtml(s.siparis_no,k);}).join("");
 // 🔴 SUNUCU TEK KAYNAK (K252): secenekler s.izinli_gecisler'ten OLDUGU GIBI turer.
 // ⚠️ BU BLOK SAYFA_HTML sablon dizesinin ICINDEDIR — yorumlarda BACKTICK KULLANMA,
 // sablonu kapatir ve yonet.js sozdizimi hatasina duser (bu turda olculdu).
 // Panelde elle yazilmis ikinci durum listesi YOKTUR; suzme/ekleme de YAPILMAZ —
 // aksi halde uc bir durumu reddederken panel onu sunmaya devam edebilirdi
 // ([[ayni-alan-iki-hukum-biri-sessiz]]). 'kargolandi' burada zaten GECMEZ, cunku
 // /durum ucu onu reddeder ve kume ucun kararindan turer; kargo yolu ASAGIDAKI
 // firma+kod formudur.
 var secenekler=s.izinli_gecisler.map(function(d){
  return '<option value="'+esc(d)+'">'+esc(d)+'</option>';
 }).join("");
 // Ayri 'iptal' butonu YERINDE KALIR (onay kutulu hizli yol); seciciye de dusen
 // 'iptal' AYNI durumDegis() cagrisina gider, yani onay kutusu ikisinde de calisir.
 var eylem=s.izinli_gecisler.indexOf("iptal")>=0
  ? '<button class="sil" onclick="durumDegis(\\''+s.siparis_no+'\\',\\'iptal\\')">iptal</button>'
  : "";
 var durumSecici=secenekler
  ? '<div class="durumsecici"><select id="dd-'+s.siparis_no+'">'+secenekler+'</select>'+
    '<button onclick="durumUygula(\\''+s.siparis_no+'\\')">Uygula</button></div>'
  : '<div class="durumsecici"><span class="yok">uygulanabilir durum yok</span></div>';
 var kargoForm="";
 if(s.durum==="uretimde"){
  kargoForm='<div class="kargoform">'+
   '<input id="kf-'+s.siparis_no+'" placeholder="Kargo firması">'+
   '<input id="kk-'+s.siparis_no+'" placeholder="Takip kodu">'+
   '<button onclick="kargoGonder(\\''+s.siparis_no+'\\')">Kargolandı olarak işaretle</button></div>';
 }
 // K284 — HAVALE ONAY FORMU: kargo formunun BIREBIR KARDESI. Yalniz 'havale-bekliyor'
 // kartinda basilir; dekont/referans BOS birakilirsa uc 400 doner (istemci de erken uyarir).
 // 🔒 Referans YALNIZ bu kutuya YAZILIR — sunucudan GERI OKUNMAZ, kartta GOSTERILMEZ
 // (finansal veri; /liste JSON'una da girmez).
 var havaleForm="";
 if(s.durum==="havale-bekliyor"){
  havaleForm='<div class="kargoform">'+
   '<input id="hd-'+s.siparis_no+'" placeholder="Dekont/referans">'+
   '<button onclick="havaleOnayla(\\''+s.siparis_no+'\\')">Havale onayla</button></div>';
 }
 var kargoBilgi=s.kargo_kodu?'<div class="kucuk">Kargo: '+esc(s.kargo_firma)+' — '+esc(s.kargo_kodu)+'</div>':'';
 var gecmis=(s.durum_gecmisi||[]).map(function(g){return esc(g.d)+" ("+esc((g.z||"").slice(0,16).replace("T"," "))+")";}).join(" → ");
 // KANAL rozeti + Ege'nin kendi numarasi: yalniz site DISI siparislerde basilir.
 // Site siparisinde (kanal yok ya da "site") kart bugunku HALIYLE kalir.
 var kanalRozet=(s.kanal&&s.kanal!=="site")?'<span class="rozet kanal">'+esc(s.kanal)+'</span>':'';
 var disNo=s.dis_no?'<div class="kucuk">Ege sipariş no: '+esc(s.dis_no)+'</div>':'';
 var musteriNotu=s.musteri_notu?'<div class="kucuk" style="white-space:pre-wrap"><b>Not:</b> '+
  esc(s.musteri_notu)+'</div>':'';
 // 🔒 KAPALI BASLIK (summary) OMUZ-USTU GIZLILIGI: siparis no · durum · kanal · tarih ·
 // toplam · kalem sayisi. Musteri adi/telefon/e-posta/adres BURAYA GIRMEZ — onlar
 // yalnizca kart ACILINCA (govdede) gorunur.
 var ozet='<summary class="ust"><span class="no">'+esc(s.siparis_no)+'</span>'+
  durumRozet(s.durum)+kanalRozet+
  '<span class="kucuk">'+esc((s.tarih||"").slice(0,16).replace("T"," "))+'</span>'+
  '<span class="kucuk">'+tl(s.tutar_kurus)+' · '+(s.kalemler||[]).length+' kalem</span>'+
  '</summary>';
 // VARSAYILAN KAPALI; tek istisna 'odendi' — is kuyrugu odur, acik dogar.
 var acik=s.durum==="odendi"?" open":"";
 return '<details class="kart"'+acik+' ontoggle="kartAc(this)">'+ozet+
  '<div class="kucuk">'+esc(s.odeme_yontemi)+'</div>'+
  kaynakSatiriHtml(s)+
  disNo+
  '<div class="mus"><b>'+esc(s.musteri.ad)+'</b> · '+esc(s.musteri.tel)+'<br>'+esc(s.musteri.adres)+
   ' · '+esc(s.musteri.eposta)+'</div>'+
  musteriNotu+
  '<div class="kucuk">Toplam '+tl(s.tutar_kurus)+' + kargo '+tl(s.kargo_kurus)+
   ' · KDV '+tl(s.kdv_kurus)+'</div>'+
  kalem+kargoBilgi+
  '<div class="eylemler">'+durumSecici+eylem+
   '<button class="ikincil" onclick="komutKopyala(\\''+esc(s.yazdir_komut)+'\\')">Yerel komut kopyala</button>'+
  '</div>'+kargoForm+havaleForm+
  (gecmis?'<div class="gecmis">Geçmiş: '+gecmis+'</div>':'')+
  '</details>';
}
function durumKapsamiTam(tumDurumlar,grupSirasi){
 var sira=new Set(grupSirasi);
 return tumDurumlar.every(function(d){return sira.has(d);});
}
function siparisGruplariHtml(siparisler){
 if(!durumKapsamiTam(PANEL_TUM_DURUMLAR,PANEL_GRUP_SIRASI)){
  console.error("Panel grup sirasi TUM_DURUMLAR kapsaminda eksik");
 }
 var bilinen=new Set(PANEL_GRUP_SIRASI),html="";
 PANEL_GRUP_SIRASI.forEach(function(durum){
  var grup=siparisler.filter(function(s){return s.durum===durum;});
  if(!grup.length)return;
  html+='<section class="siparis-grubu" data-durum="'+esc(durum)+'">'+
   '<h2 class="grup-baslik rozet '+esc(durum)+'">'+esc(durum)+
   ' <span class="grup-sayi">('+esc(grup.length)+')</span></h2>'+
   grup.map(kartHtml).join("")+'</section>';
 });
 var diger=siparisler.filter(function(s){return !bilinen.has(s.durum);});
 if(diger.length){
  html+='<section class="siparis-grubu" data-durum="diger">'+
   '<h2 class="grup-baslik rozet">diğer <span class="grup-sayi">('+
   esc(diger.length)+')</span></h2>'+diger.map(kartHtml).join("")+'</section>';
 }
 return html;
}
/**
 * KART ILK ACILDIGINDA uretim dosyasi listesini bir kez cek (lazy).
 * Kapali kartlar R2/D1'e HIC dokunmaz; ikinci acilista da yeniden CEKMEZ
 * (data-yuklendi damgasi). Kapanip acilma tekrar istek uretmez.
 */
function kartAc(el){
 if(!el||!el.open||el.dataset.yuklendi)return;
 el.dataset.yuklendi="1";
 var kutular=el.querySelectorAll("[data-parca]");
 for(var i=0;i<kutular.length;i++){
  var x=kutular[i];
  parcalar(x.getAttribute("data-no"),x.getAttribute("data-id"),x.id);
 }
}
async function yukle(){
 var d=document.getElementById("durumSuzgec").value;
 var m=document.getElementById("liste");
 m.innerHTML="<p>Yükleniyor…</p>";
 var r=await api("/liste"+(d?"?durum="+encodeURIComponent(d):""));
 if(r.kod!==200){m.innerHTML='<p class="hata">Liste alınamadı ('+r.kod+
  '). Oturum düşmüş olabilir — sayfayı yenileyin.</p>';return;}
 var s=r.govde.siparisler||[];
 if(!s.length){m.innerHTML="<p>Sipariş yok.</p>";return;}
 m.innerHTML=siparisGruplariHtml(s);
 // open ile DOGAN kartlarda (odendi) tarayici 'toggle' olayini ATESLEMEZ —
 // lazy yukleme onlarda sessizce olmezdi. Render sonrasi elle tetiklenir.
 var acik=m.querySelectorAll("details.kart[open]");
 for(var i=0;i<acik.length;i++){kartAc(acik[i]);}
}
// SIPARIS BASINA DURUM SECICI (K252). Secilen deger ZATEN sunucunun kabul kumesinden
// gelir (kart render'i izinli_gecisler'ten uretti); yine de karar SUNUCUNUNDUR —
// istemci yalnizca istegi tasir, 400'u da oldugu gibi gosterir.
async function durumUygula(no){
 var el=document.getElementById("dd-"+no);
 if(!el||!el.value)return;
 durumDegis(no,el.value);
}
async function durumDegis(no,d){
 if(d==="iptal"&&!confirm("Sipariş iptal edilsin mi?"))return;
 var r=await api("/durum",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({siparis_no:no,durum:d})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));}
 yukle();
}
async function kargoGonder(no){
 var f=document.getElementById("kf-"+no).value.trim(),k=document.getElementById("kk-"+no).value.trim();
 if(!f||!k){alert("Firma ve takip kodu gerekli.");return;}
 var r=await api("/kargo",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({siparis_no:no,kargo_firma:f,kargo_kodu:k})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));}
 yukle();
}
// K284 — HAVALE ONAYI. kargoGonder'in BIREBIR KARDESI: ayri/dar uc + zorunlu delil.
// 🔒 Referans yalniz istekte tasinir; yanitta DONMEZ, ekrana YAZILMAZ, alert'e girmez.
async function havaleOnayla(no){
 var d=document.getElementById("hd-"+no).value.trim();
 if(!d){alert("Dekont/referans gerekli.");return;}
 var r=await api("/havale-onay",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({siparis_no:no,dekont_ref:d})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));}
 yukle();
}
function komutKopyala(t){navigator.clipboard&&navigator.clipboard.writeText(t);
 alert("Panoya kopyalandı:\\n"+t);}
// ---- URUNLER SEKMESI (T1) — kuyruk gorunumu + duzenleme -----------------------
// Kaydet SITEYI DEGISTIRMEZ: /urunler-ustyazim kuyruga hal='beklemede' satir yazar;
// tabana isleyen tek kol CI uygulayicisidir. Ekran bunu acikca soyler.
var urunVeri={};
function sekmeSec(u){
 document.getElementById("liste").hidden=u;
 document.getElementById("urunler").hidden=!u;
 document.getElementById("sekmeSiparis").className="sekme"+(u?"":" aktif");
 document.getElementById("sekmeUrun").className="sekme"+(u?" aktif":"");
 document.getElementById("siparisAraclar").style.display=u?"none":"flex";
 if(u){urunYukle();}
}
async function urunYukle(){
 var q=document.getElementById("urunAra").value.trim();
 var kutu=document.getElementById("urunListe");
 kutu.innerHTML="<p>Yükleniyor…</p>";
 var r=await api("/urunler"+(q?"?q="+encodeURIComponent(q):""));
 if(r.kod!==200){kutu.innerHTML='<p class="hata">Liste alınamadı ('+r.kod+
  '). Oturum düşmüş olabilir — sayfayı yenileyin.</p>';return;}
 urunVeri={};
 var u=(r.govde&&r.govde.urunler)||[];
 var bek=(r.govde&&r.govde.bekleyen)||{};
 var html=(r.govde&&r.govde.kuyruk_tablosu===false)?
  '<p class="yok">Kuyruk tablosu yok — şema koşulmamış; Kaydet çalışmaz.</p>':"";
 if(!u.length){kutu.innerHTML=html+"<p>Ürün bulunamadı.</p>";kuyrukYukle();return;}
 html+=u.map(function(x){
  urunVeri[x.id]={fiyat:x.fiyat||"",baslik:x.baslik||"",aciklama:x.aciklama||"",
   parametrik:!!x.parametrik};
  var b=bek[x.id]||{};
  var bekNot=Object.keys(b).length?
   '<div class="yok">Kuyrukta bekleyen üst yazım: '+Object.keys(b).map(esc).join(", ")+'</div>':"";
  var gorsel=x.gorsel?'<img src="'+esc(x.gorsel)+'" alt="" loading="lazy" '+
   'style="width:44px;height:44px;object-fit:cover;border-radius:6px">':"";
  var fiyatAlan=x.parametrik?
   '<label>Fiyat <input id="uf-'+esc(x.id)+'" disabled placeholder="parametrik — taban fiyat şemadan"></label>':
   '<label>Fiyat <input id="uf-'+esc(x.id)+'" value="'+esc(x.fiyat||"")+'" placeholder="örn. 500 TL"></label>';
  return '<details class="kart" data-uid="'+esc(x.id)+'" ontoggle="urunKartAc(this)">'+
   '<summary class="ust">'+gorsel+'<span class="no">'+esc(x.baslik)+'</span>'+
   '<span class="kucuk">'+esc(x.id)+'</span>'+
   '<span class="rozet">'+esc(x.fiyat||(x.parametrik?"parametrik":"fiyat yok"))+'</span></summary>'+
   bekNot+
   '<div class="alan-form">'+fiyatAlan+
   '<label>Başlık <input id="ub-'+esc(x.id)+'" value="'+esc(x.baslik||"")+'"></label>'+
   '<label>Açıklama <textarea id="ua-'+esc(x.id)+'" rows="5">'+esc(x.aciklama||"")+'</textarea></label>'+
   '<div class="eylemler"><button onclick="urunKaydet(\\''+esc(x.id)+'\\')">Kaydet (kuyruğa)</button>'+
   '<button class="sil" onclick="urunSil(\\''+esc(x.id)+'\\')">Sil (arşive)</button></div>'+
   '</div>'+
   '<div class="t2bolum" id="ug-'+esc(x.id)+'"><span class="kucuk">Görseller yükleniyor…</span></div>'+
   '<div class="t2bolum" id="us-'+esc(x.id)+'"></div>'+
   '<div class="t2bolum" id="uk-'+esc(x.id)+'"></div>'+
   '</details>';
 }).join("");
 kutu.innerHTML=html;
 kuyrukYukle();
}
async function urunKaydet(id){
 var t=urunVeri[id];if(!t)return;
 var alanlar=[["fiyat",document.getElementById("uf-"+id)],
  ["baslik",document.getElementById("ub-"+id)],
  ["aciklama",document.getElementById("ua-"+id)]];
 var isler=[];
 for(var i=0;i<alanlar.length;i++){
  var ad=alanlar[i][0],el=alanlar[i][1];
  if(!el||el.disabled)continue;
  var deger=(ad==="aciklama")?el.value.replace(/\\r\\n?/g,"\\n").trim():el.value.trim();
  if(deger===t[ad])continue;
  if(!deger){alert(ad+" boş bırakılamaz (silme yok).");return;}
  if(ad==="fiyat"&&!new RegExp("^[1-9][0-9]{0,5} TL$").test(deger)){
   alert('Fiyat biçimi "500 TL" olmalı (yalnız tam sayı + TL).');return;}
  isler.push([ad,deger]);
 }
 if(!isler.length){alert("Değişiklik yok.");return;}
 for(var j=0;j<isler.length;j++){
  var r=await api("/urunler-ustyazim",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({urun_id:id,alan:isler[j][0],deger:isler[j][1]})});
  if(r.kod!==200){alert("Olmadı ("+isler[j][0]+"): "+(r.govde&&r.govde.hata||r.kod));return;}
 }
 alert(isler.length+" alan kuyruğa yazıldı. Uygulayıcı işleyip site yeniden yayınlanınca canlıya çıkar.");
 urunYukle();
}
// TEKIL SILME — cift onay: urun id'si AYNEN yazdirilir (yanlis tik bir musteri-gorunur
// urunu dusurmesin), gerekce zorunlu. Kuyruga alan='sil' yazilir; taban kaydi arsive
// tasinir (yok edilmez), R2 gorselleri silinmez, STL'ler arsiv/stl/'e tasinir.
// "gizli"den AYRI kavramdir (gizle=yayindan dusur, sil=tabandan arsive tasi).
async function urunSil(id){
 var onay=prompt("ÜRÜN SİLME (arşive taşıma) — canlıdan düşer, arşivden geri getirilebilir.\\n"+
  "Onay için ürün id'sini AYNEN yazın:\\n"+id);
 if(onay===null)return;
 if(onay.trim()!==id){alert("Onay, id ile birebir aynı değil — silme kuyruğa YAZILMADI.");return;}
 var gerekce=prompt("Kısa gerekçe (yalnız kuyruk kaydında kalır; siteye/repoya çıkmaz):");
 if(gerekce===null)return;
 gerekce=gerekce.trim();
 if(!gerekce){alert("Gerekçe boş olamaz — silme kuyruğa YAZILMADI.");return;}
 var r=await api("/urun-sil",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({urun_id:id,onay:onay.trim(),gerekce:gerekce})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));return;}
 alert("Silme kuyruğa yazıldı"+(r.govde&&r.govde.stl_arsivlenen?
  " (arşive taşınan STL: "+r.govde.stl_arsivlenen+")":"")+
  ". Uygulayıcı işleyince taban kaydı arşive taşınır; site yayınlanınca canlıdan düşer.");
 urunYukle();
}
async function kuyrukYukle(){
 var kutu=document.getElementById("kuyrukKutu");
 var r=await api("/urunler-kuyruk");
 if(r.kod!==200){kutu.innerHTML='<p class="hata">Kuyruk alınamadı ('+r.kod+')</p>';return;}
 if(r.govde&&r.govde.tablo_yok){
  kutu.innerHTML='<div class="kart"><p class="yok">Kuyruk tablosu yok — şema koşulmamış.</p></div>';return;}
 var s=(r.govde&&r.govde.satirlar)||[];
 if(!s.length){kutu.innerHTML='<div class="kart"><p class="kucuk">Kuyruk boş.</p></div>';return;}
 kutu.innerHTML='<div class="kart"><b>Kuyruk (son '+s.length+')</b>'+s.map(function(x){
  var iptal=x.hal==="beklemede"?
   ' <button class="sil" onclick="kuyrukIptal('+(+x.id)+')">İptal</button>':"";
  var sebep=x.sebep?' <span class="kucuk">'+esc(x.sebep)+'</span>':"";
  return '<div class="satir"><span class="rozet '+esc(x.hal)+'">'+esc(x.hal)+'</span> '+
   '<b>'+esc(x.urun_id)+'</b> · '+esc(x.alan)+' → '+esc((x.deger||"").slice(0,80))+sebep+
   ' <span class="kucuk">'+esc((x.ts||"").slice(0,16).replace("T"," "))+'</span>'+iptal+'</div>';
 }).join("")+'</div>';
}
async function kuyrukIptal(id){
 if(!confirm("Bekleyen üst yazım iptal edilsin mi?"))return;
 var r=await api("/urunler-ustyazim-sil",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id:id})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));}
 urunYukle();
}
// ---- URUNLER SEKMESI (T2) — gorsel / STL / kaynak link ------------------------
// GORSEL degisikligi KUYRUK yoluyla tabana iner (dakikalar). STL ve kaynak link
// tabana INMEZ: STL R2'de, kaynak link GIZLI D1'de yasar — ikisi ANINDA etkilidir.
// Ekran bu farki her bolumun kendi notunda soyler.
var urunGorselDurum={};
async function apiHam(yol,govde){
 var c=await fetch("/api/shop/yonet"+yol,{method:"POST",credentials:"same-origin",body:govde});
 var v=null;try{v=await c.json();}catch(e){}
 return {kod:c.status,govde:v};
}
function urunKartAc(el){
 if(!el||!el.open||el.dataset.t2yuklendi)return;
 el.dataset.t2yuklendi="1";
 var id=el.getAttribute("data-uid");
 gorselCek(id);stlCek(id);kaynakCek(id);
}
async function gorselCek(id){
 var kutu=document.getElementById("ug-"+id);if(!kutu)return;
 var r=await api("/urun-gorseller?id="+encodeURIComponent(id));
 if(r.kod!==200){kutu.innerHTML='<span class="hata">Görsel listesi alınamadı ('+
  esc((r.govde&&r.govde.hata)||r.kod)+') — sessiz boşluk değil, taban okunamadı.</span>';return;}
 var liste=(r.govde&&r.govde.gorseller)||[];
 var bek=r.govde&&r.govde.bekleyen;
 if(bek){try{liste=JSON.parse(bek.deger)||liste;}catch(e){}}
 urunGorselDurum[id]={liste:liste.slice(),bekleyen:!!bek};
 gorselCiz(id);
}
function gorselCiz(id){
 var kutu=document.getElementById("ug-"+id);if(!kutu)return;
 var d=urunGorselDurum[id];
 var h='<h4>🖼️ Görseller ('+d.liste.length+')</h4>';
 if(d.bekleyen){h+='<div class="yok">Kuyrukta bekleyen görsel üst yazımı var — aşağıdaki liste onu gösterir.</div>';}
 h+='<div class="gserit">'+d.liste.map(function(u,i){
  return '<span class="gkutu"><img src="'+esc(u)+'" alt="" loading="lazy">'+
   '<button class="sil" onclick="gorselCikarUI(\\''+esc(id)+'\\','+i+')">çıkar</button></span>';
 }).join("")+'</div>';
 h+='<div class="eylemler" style="margin-top:6px">'+
  '<input type="file" id="gf-'+esc(id)+'" accept="image/jpeg,image/png">'+
  '<button class="ikincil" onclick="gorselYukleUI(\\''+esc(id)+'\\')">Yükle + listeye ekle</button>'+
  '<button onclick="gorselKaydetUI(\\''+esc(id)+'\\')">Görselleri kaydet (kuyruğa)</button></div>'+
  '<div class="kucuk">Kaydet kuyruğa yazar; uygulayıcı işleyip site yayınlanınca canlıya çıkar. '+
  'Çıkarma listeden düşürür, R2 dosyası silinmez. En az 1 görsel kalır.</div>';
 kutu.innerHTML=h;
}
function gorselCikarUI(id,i){
 var d=urunGorselDurum[id];if(!d)return;
 if(d.liste.length<=1){alert("En az 1 görsel kalmalı (ürün silme ayrı: Sil (arşive)).");return;}
 d.liste.splice(i,1);gorselCiz(id);
}
async function gorselYukleUI(id){
 var inp=document.getElementById("gf-"+id);
 if(!inp||!inp.files||!inp.files.length){alert("Önce dosya seçin (JPEG/PNG).");return;}
 var r=await apiHam("/gorsel-yukle?id="+encodeURIComponent(id),inp.files[0]);
 if(r.kod!==200){alert("Yüklenemedi: "+(r.govde&&r.govde.hata||r.kod));return;}
 var d=urunGorselDurum[id];
 if(d.liste.indexOf(r.govde.url)>=0){alert("Bu görsel zaten listede (aynı içerik = aynı adres).");return;}
 d.liste.push(r.govde.url);gorselCiz(id);
 alert("Yüklendi ve listeye eklendi. Kalıcı olması için \\"Görselleri kaydet\\" ile kuyruğa yazın.");
}
async function gorselKaydetUI(id){
 var d=urunGorselDurum[id];if(!d)return;
 var r=await api("/urunler-ustyazim",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({urun_id:id,alan:"gorseller",deger:JSON.stringify(d.liste)})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));return;}
 alert("Görsel listesi kuyruğa yazıldı. Uygulayıcı işleyip site yayınlanınca canlıya çıkar.");
 kuyrukYukle();gorselCek(id);
}
async function stlCek(id){
 var kutu=document.getElementById("us-"+id);if(!kutu)return;
 kutu.innerHTML='<h4>🧱 Baskı dosyaları</h4> yükleniyor…';
 var r=await api("/stl-liste?id="+encodeURIComponent(id));
 var h='<h4>🧱 Baskı dosyaları</h4>';
 if(r.kod!==200){kutu.innerHTML=h+'<span class="hata">liste alınamadı ('+r.kod+')</span>';return;}
 var p=(r.govde&&r.govde.parcalar)||[];
 if(!p.length){h+='<div class="yok">'+esc((r.govde&&r.govde.not)||"dosya yok")+'</div>';}
 else{h+=p.map(function(x){
  return '<div class="satir"><a class="indir" href="/api/shop/yonet/stl?id='+
   encodeURIComponent(id)+'&dosya='+encodeURIComponent(x.dosya)+'">'+esc(x.dosya)+
   esc(boyutMetni(x.boyut))+'</a> <button class="sil" onclick="stlCikarUI(\\''+esc(id)+
   '\\',\\''+esc(x.dosya)+'\\')">çıkar</button></div>';
 }).join("");}
 h+='<div class="eylemler" style="margin-top:6px">'+
  '<input type="file" id="sf-'+esc(id)+'" accept=".stl,.3mf">'+
  '<button class="ikincil" onclick="stlYukleUI(\\''+esc(id)+'\\')">STL/3MF yükle</button></div>'+
  '<div class="kucuk">Yükleme/çıkarma ANINDA etkilidir (R2, kuyruk yok). Mevcut adın üstüne '+
  'yazılamaz; çıkarma dosyayı arşive taşır, kalıcı silme yok.</div>';
 kutu.innerHTML=h;
}
async function stlYukleUI(id){
 var inp=document.getElementById("sf-"+id);
 if(!inp||!inp.files||!inp.files.length){alert("Önce dosya seçin (.stl/.3mf).");return;}
 var f=inp.files[0];
 var r=await apiHam("/stl-yukle?id="+encodeURIComponent(id)+
  "&dosya="+encodeURIComponent(f.name),f);
 if(r.kod!==200){alert("Yüklenemedi: "+(r.govde&&r.govde.hata||r.kod));return;}
 var ad=r.govde&&r.govde.dosya||f.name;
 alert("Yüklendi: "+ad+(ad!==f.name?" (dosya adı normalize edildi; seçilen: "+f.name+")":""));stlCek(id);
}
async function stlCikarUI(id,dosya){
 if(!confirm("Baskı dosyası listeden çıkarılsın mı? (Arşive taşınır, kalıcı silme yok.)"))return;
 var r=await api("/stl-cikar",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id:id,dosya:dosya})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));return;}
 stlCek(id);
}
async function kaynakCek(id){
 var kutu=document.getElementById("uk-"+id);if(!kutu)return;
 var r=await api("/urun-kaynak?id="+encodeURIComponent(id));
 var h='<h4>🔗 Üretici kaynağı (gizli — siteye çıkmaz)</h4>';
 if(r.kod!==200){kutu.innerHTML=h+'<span class="hata">okunamadı ('+r.kod+')</span>';return;}
 var u=r.govde&&r.govde.link;
 if(u&&/^https:\\/\\//i.test(u)){
  h+='<div><a class="indir" href="'+esc(u)+'" target="_blank" rel="noopener">kaynak sayfası</a>'+
   ' <span class="kucuk">('+esc(r.govde.duzlem==="panel"?"panelden":"kaynak kaydından")+')</span></div>';
 }else if(r.govde&&r.govde.cikarildi){h+='<div class="yok">kaynak panelden çıkarıldı</div>';}
 else{h+='<div class="yok">kaynak kaydı yok</div>';}
 h+='<div class="eylemler" style="margin-top:6px">'+
  '<input id="kl-'+esc(id)+'" placeholder="https://..." style="flex:1;min-width:220px">'+
  '<button onclick="kaynakKaydetUI(\\''+esc(id)+'\\')">Kaydet</button>'+
  '<button class="sil" onclick="kaynakCikarUI(\\''+esc(id)+'\\')">Çıkar</button></div>'+
  '<div class="kucuk">Yalnız gizli yönetim kaydında tutulur; ürün sayfasına, kataloğa ve '+
  'Ege\\'ye HİÇ çıkmaz. Kaydet/çıkar ANINDA etkilidir.</div>';
 kutu.innerHTML=h;
}
async function kaynakKaydetUI(id){
 var el=document.getElementById("kl-"+id);
 var u=(el&&el.value||"").trim();
 if(!u){alert("Link boş — çıkarmak için Çıkar düğmesini kullanın.");return;}
 var r=await api("/kaynak-yaz",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id:id,link:u})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));return;}
 kaynakCek(id);
}
async function kaynakCikarUI(id){
 if(!confirm("Kaynak link listeden çıkarılsın mı?"))return;
 var r=await api("/kaynak-yaz",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id:id,link:""})});
 if(r.kod!==200){alert("Olmadı: "+(r.govde&&r.govde.hata||r.kod));return;}
 kaynakCek(id);
}
document.getElementById("yenile").onclick=yukle;
document.getElementById("durumSuzgec").onchange=yukle;
document.getElementById("sekmeSiparis").onclick=function(){sekmeSec(false);};
document.getElementById("sekmeUrun").onclick=function(){sekmeSec(true);};
document.getElementById("urunAraBtn").onclick=urunYukle;
document.getElementById("urunAra").onkeydown=function(e){if(e.key==="Enter"){urunYukle();}};
yukle();
</script></body></html>`;
