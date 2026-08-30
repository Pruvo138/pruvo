/**
 * KANAL / ATIF SINIFLANDIRMASI — TEK KAYNAK (saf; I/O yok, ortam yok).
 *
 * IKI tuketici vardir ve IKISI DE BURAYI cagirir:
 *   1) Panel  — shop/src/yonet.js `/liste` her siparise `kaynak.sinif` yazar, panel onu
 *               OLDUGU GIBI basar (kart HTML'inde elle yazilmis ikinci etiket listesi YOK).
 *   2) Rapor  — tools/kanal-kirilimi.py kovalari BU dosyayi `node` ile cagirarak doldurur;
 *               Python tarafinda ikinci bir sozluk/esik/kova listesi YAZILMAZ.
 * Gerekce: ayni alanin hukmu iki yere elle yazilinca biri gunceellenir, oteki SESSIZCE
 * eski kalir — panel "organik" derken rapor ayni siparisi "ucretli" sayar ve kimse gormez
 * ([[ayni-alan-iki-hukum-biri-sessiz]]). Bu dosyayi bozan mutant IKI kabul testini birden
 * kirmizi yakmalidir; tek testi yakiyorsa tek kaynak FIILEN yoktur.
 *
 * 🔴 DORT KOVA — UCUNCU/DORDUNCU SINIF YUTULMAZ ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
 * "site mi degil mi" gibi iki kovali bir yuklem, tanimadigi her seyi varsayilan kovaya iter
 * ve o kovanin sayisini SAHTE buyutur. Burada:
 *   - `site-ucretli`  : site siparisi + ucretli tiklama isareti (REF:GS-… / utm_id / paid medium)
 *   - `site-organik`  : site siparisi + ucretli OLMAYAN bir kaynak isareti (REF:OG-… / utm_*)
 *   - `whatsapp`      : Ege kanali (tarayicidan gecmez; atif BILEREK bostur)
 *   - `atif-yok`      : site siparisi ama SINIFLANACAK isaret YOK — AYRI kova, adiyla gorunur.
 *                       Bunu sessizce `site-organik`e katlamak raporun TAMAMINI yalan yapar:
 *                       organik ROI, olculmemis trafikle sisirilmis olur.
 *   - `null`          : OLCULEMEDI (kanal yok / bilinmeyen kanal) — kova DEGIL, hukumsuzluk.
 *                       Cagiran bunu fail-CLOSED ele alir; "kolon yok, demek ki hepsi site"
 *                       CIKARIMI YASAKTIR.
 *
 * 🔒 GIZLILIK: bu dosya `ga_client_id` / `fbp` / `fbc` alanlarina HIC BAKMAZ. Onlar kisiye
 * baglanan reklam-eslestirme kimlikleridir; sinifa katkilari YOK, okunmalari da gereksiz.
 * Ekrana/rapora tasinmamalari icin ayrica `kaynakOzeti` suzgeci vardir (yonet.js).
 */

export const KOVA_SITE_UCRETLI = "site-ucretli";
export const KOVA_SITE_ORGANIK = "site-organik";
export const KOVA_WHATSAPP = "whatsapp";
export const KOVA_ATIF_YOK = "atif-yok";

/** Kanal kolonunun bilinen degerleri (yonet.js KANAL_SITE / WA_KANAL ile ayni dizeler). */
const KANAL_SITE = "site";
const KANAL_WHATSAPP = "whatsapp";

/**
 * Rapor/panel SIRASI — kovalar DAIMA bu sirada ve TAMAMI basilir (sayisi 0 olsa bile).
 * Bos kovayi gizlemek, "bu sinif hic olusmadi" ile "bu sinifi hic olcmedim"i ayni
 * ekrana cokertir.
 */
export const KOVALAR = [KOVA_SITE_UCRETLI, KOVA_SITE_ORGANIK, KOVA_WHATSAPP, KOVA_ATIF_YOK];

/** Panelde/raporda basilan Turkce etiket — TEK KAYNAK (ikinci sozluk YOK). */
export const KOVA_ETIKET = {
  [KOVA_SITE_UCRETLI]: "site · ücretli",
  [KOVA_SITE_ORGANIK]: "site · organik",
  [KOVA_WHATSAPP]: "WhatsApp (Ege)",
  [KOVA_ATIF_YOK]: "atıf yok / sınıflanamaz",
};

/** Bir siparis SINIFLANAMADIGINDA panelde/raporda gecen dil. `/liste`'nin uretici-kaynak
 *  kolunda ZATEN kullanilan kalibin AYNISI — ikinci sozluk acilmaz. */
export const KAYNAK_YOK_METNI = "kaynak kaydı yok";

/** UCRETLI TIKLAMA medium'lari. Google/Meta'nin standart paid medium'lari; liste
 *  BUYUMEYE ACIK ama TEK yerdedir. Kucuk harfe indirilmis deger ile karsilastirilir. */
const UCRETLI_MEDIUM = new Set([
  "cpc", "ppc", "paidsearch", "paid", "cpm", "cpv", "cpa", "display", "retargeting",
]);

function metin(v) {
  return typeof v === "string" ? v.trim() : "";
}

/**
 * ATIF gövdesi ucretli tiklama isareti tasiyor mu?
 * 🔴 REF ONCELIKLIDIR: `REF:GS-…` bizim KENDI halkamizin ucretli kolu (ref.js src="GS"),
 * `REF:OG-…` organik kolu. utm_* musteri linkinden gelir ve kirletilebilir; REF sunucu
 * tarafinda kalibiyla dogrulanmistir.
 */
function ucretliMi(a) {
  const ref = metin(a.ref);
  if (ref.indexOf("REF:GS-") === 0) { return true; }
  if (ref.indexOf("REF:OG-") === 0) { return false; }
  // utm_id Google Ads'in kampanya kimligidir; organik linkte olusmaz.
  if (metin(a.utm_id)) { return true; }
  return UCRETLI_MEDIUM.has(metin(a.utm_medium).toLowerCase());
}

/** ATIF gövdesinde SINIFLANABILIR bir kaynak isareti var mi?
 *  (fbp/fbc/ga_client_id BILEREK sayilmaz: kisiyi tanirlar, kaynagi soylemezler.) */
function isaretVarMi(a) {
  return !!(metin(a.ref) || metin(a.utm_source) || metin(a.utm_medium) ||
            metin(a.utm_campaign) || metin(a.utm_id));
}

/**
 * SIPARIS -> KOVA. Doner: KOVALAR'dan biri, ya da `null` = OLCULEMEDI.
 *
 * @param {{kanal?: any, atif?: any}} s  `atif` ya cozulmus nesne ya JSON dizesi olabilir
 *   (panel cozulmus verir, rapor D1'den ham dize okur) — ikisini de BURASI normalize eder
 *   ki iki tarafta iki ayri cozucu olusmasin.
 */
export function kanalSinifi(s) {
  const kanal = metin(s && s.kanal);
  // 🔴 Kanal bilinmiyorsa hukum YOK. Bos dize / kolon yok / TANIMADIGIMIZ bir kanal
  // (yarin eklenecek "instagram" gibi) hepsi buraya duser ve `null` doner. Bunlari
  // "site" saymak, iki kovali siniflamanin ta kendisidir.
  if (kanal !== KANAL_SITE && kanal !== KANAL_WHATSAPP) { return null; }
  // WhatsApp: tarayicidan gecmedigi icin atif BILEREK bostur (yonet.js waSiparis).
  // Burada atif'a BAKILMAZ — dolu gelse bile kanal hukmu onceliklidir.
  if (kanal === KANAL_WHATSAPP) { return KOVA_WHATSAPP; }
  const a = atifCoz(s && s.atif);
  if (!isaretVarMi(a)) { return KOVA_ATIF_YOK; }
  return ucretliMi(a) ? KOVA_SITE_UCRETLI : KOVA_SITE_ORGANIK;
}

/**
 * `atif` -> duz nesne. Dize ise JSON cozulur; bozuksa `{}` (fail-soft: siniflanamaz
 * kovasina duser, hukum uydurulmaz). Dizi/nesne-disi de `{}`.
 */
export function atifCoz(atif) {
  let a = atif;
  if (typeof a === "string") {
    try { a = JSON.parse(a); } catch (e) { return {}; }
  }
  if (!a || typeof a !== "object" || Array.isArray(a)) { return {}; }
  return a;
}

/**
 * PANELE/RAPORA CIKACAK ATIF ALANLARI — BEYAZ LISTE (suzgec, kara liste DEGIL).
 *
 * 🔴 `ga_client_id`, `fbp`, `fbc` BU LISTEDE YOKTUR ve OLMAYACAKTIR. Gerekce:
 * bunlar kisiye baglanan reklam-eslestirme KIMLIKLERIDIR (GA4 istemci kimligi, Meta
 * tarayici/tiklama cerezi). Okan'in operasyonunda hicbir isleri yoktur — siparisi hangi
 * kampanyanin getirdigini `utm_*` + `ref` zaten soyler. Ekrana tasinmalari yalnizca
 * gizlilik yuzeyini buyutur: panel omuz-ustu okunur, ekran goruntusu paylasilir, JSON
 * yaniti tarayici gecmisinde/loglarda kalir. Meta CAPI govdesi bunlari D1'den KENDI
 * okur (index.js donus akisi) — panel yolundan gecmeleri GEREKMEZ.
 * 🔴 BEYAZ LISTE OLMASI SART: yarin `atif`a yeni bir kimlik alani eklenirse kara liste
 * onu sessizce gecirirdi; beyaz liste tanimadigini DUSURUR.
 */
export const ATIF_GORUNUR_ALANLAR = ["utm_source", "utm_medium", "utm_campaign", "utm_id", "ref"];

/**
 * Siparis satiri -> panelin/raporun basacagi KAYNAK OZETI. Suzgec BURADADIR (sunucu
 * tarafi): gizli alanlar tarayiciya HIC ulasmaz, istemci suzgecine guvenilmez.
 *
 * @param {{kanal?: any, atif?: any}} s
 * @param {{grup?: string, src?: string}} [reklam]  `reklam_ref_gclid` satiri (varsa).
 *   🔒 Yalniz `grup` + `src` alinir; `gclid`/`gbraid`/`wbraid` TIKLAMA KIMLIKLERIDIR ve
 *   fbp/fbc ile AYNI sinifta oldugu icin BURAYA GIRMEZ.
 */
export function kaynakOzeti(s, reklam) {
  const sinif = kanalSinifi(s);
  const a = atifCoz(s && s.atif);
  const alanlar = {};
  for (const ad of ATIF_GORUNUR_ALANLAR) {
    const v = metin(a[ad]);
    if (v) { alanlar[ad] = v; }
  }
  const ozet = {
    sinif: sinif,
    // Etiket SUNUCUDA turetilir; panel HTML'i kova->etiket eslemesini TEKRAR YAZMAZ.
    etiket: sinif ? KOVA_ETIKET[sinif] : KAYNAK_YOK_METNI,
    // 🔴 "kaynak kaydı yok" dili VERIYLE BIRLIKTE tasinir — panel HTML'i onu kendi
    // govdesinde TEKRAR YAZMAZ. Neden bu yol: panel kodu SAYFA_HTML sablon dizesinin
    // icinde yasar ve o bolgeye sunucu degeri `${...}` ile enjekte EDILEMEZ (sayfa JS'ini
    // olcen bataryalar kaynagi ham metinden dilimliyor; interpolasyon dilimi ayristirilamaz
    // yapar — 30 Agu'da 3 komsu batarya boyle kirmizi yandi). Alan basina birkac bayt,
    // karsiliginda ikinci sozluk YOK.
    yok: KAYNAK_YOK_METNI,
    kanal: metin(s && s.kanal),
    atif: alanlar,
  };
  const grup = metin(reklam && reklam.grup);
  const src = metin(reklam && reklam.src);
  if (grup) { ozet.grup = grup; }
  if (src) { ozet.src = src; }
  return ozet;
}
