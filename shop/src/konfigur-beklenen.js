/**
 * KONFIGUR BEKLENTI KAPISI — "bu urun konfiguratorlu OLMALI" sinyali (D1 alanlarindan).
 *
 * NEDEN VAR (sessiz eksik tahsilat penceresi):
 *   Bir urunun konfiguratorlu oldugunu Worker YALNIZCA bundle'daki KONFIGURLAR haritasindan
 *   bilir (D1'de "konfigur" alani YOK; urun D1'de parametrik=0 + sabit fiyatli gorunur).
 *   Katalog D1'e otomatik senkronlanir (tools/d1-sync.py, push hook'u), Worker deploy'u ise
 *   ELLE yapilir -> "D1'de VAR, Worker bundle'inda YOK" penceresi YAPISAL olarak acik.
 *   O pencerede index.js'in kollari sirayla: KONFIGURLAR.has=false -> u.parametrik=0 ->
 *   SABIT katalog fiyati. Yani konfiguratorde 1.500 TL olan 30 cm'lik urun 500 TL'ye satilirdi
 *   ve HICBIR uyari cikmazdi (musteri gercek bedelin ~%33'unu oder).
 *
 * SINYAL: D1'den ZATEN cekilen alanlar (yeni kolon/sema DEGISIKLIGI YOK):
 *   1) kategori === "Skan Art" — konfigurator serisinin KENDINE AIT gizli kategorisi.
 *      Bu kategoride konfiguratorsuz urun YOKTUR (kategori seriyle birlikte dogdu; katalogda
 *      "Skan Art" = 13 urun = KONFIGURLAR'daki 13 urun, birebir).
 *   2) id soneki "-serit-dekoratif-figur" — serinin id kalibi (13/13). Kategori yanlis
 *      girilse bile (or. "Dekorasyon") kalem yine kapiya takilir; iki eksen birbirini yedekler.
 *   3) kategori "Figür" / "Fidget" — dogrusal fiyatli konfigur serisi (18 Eki).
 *
 * FAIL-CLOSED: sinyal dogru ama harita bos ise fiyat HESAPLANMAZ -> gorunur 400
 * ("konfigur-urun" + WhatsApp yonlendirmesi; index.js'te zaten var olan cevabin AYNISI).
 * Yanlis-pozitifin bedeli = o kalem WhatsApp'a duser (siparis kaybi); yanlis-negatifin bedeli
 * = sessiz eksik tahsilat. Okan kurali: siparis kaybetmek yanlis tahsilattan iyidir.
 *
 * BAKIM: yeni konfigurator serisi BASKA bir kategoriyle/id kalibiyla gelirse buraya eklenir;
 * eklenmezse davranis BUGUNKU haliyle ayni kalir (regresyon yok), yalniz o yeni seri icin
 * pencere yeniden acilir -> yeni seri eklerken bu dosya da guncellenmeli.
 */

/** Konfigurator serisinin kendine ait (nav'da gizli) kategorisi. */
export const KONFIGUR_KATEGORI = "Skan Art";

/** Dogrusal fiyatli konfigur serisi (Okan 18 Eki: Figur + Fidget 6-25 cm, 100 TL/cm). Bu iki
 *  kategoride konfiguratorsuz urun YOKTUR (kategoriler seriyle dogdu; 18 Eki 7/7 konfigurlu).
 *  Eklenmeseydi D1 `konfigur` kolonu kacan bir Figur, 25 cm'lik 2.500 TL siparisi sabit
 *  "600 TL"den tahsil ederdi (sessiz eksik tahsilat). */
export const DOGRUSAL_KONFIGUR_KATEGORILERI = Object.freeze(["Figür", "Fidget"]);

/** Konfigurator serisinin id kalibi (13/13 urun bu sonekle biter). */
export const KONFIGUR_ID_SONEKI = "-serit-dekoratif-figur";

/**
 * Urun (D1 satiri) konfiguratorlu OLMALI mi? Yalniz D1'den okunan alanlara bakar.
 * @param {{id?: string, kategori?: string}} u
 * @returns {boolean}
 */
export function konfigurBeklenirMi(u) {
  if (!u || typeof u !== "object") { return false; }
  const kategori = typeof u.kategori === "string" ? u.kategori.trim() : "";
  const id = typeof u.id === "string" ? u.id : "";
  return kategori === KONFIGUR_KATEGORI || id.endsWith(KONFIGUR_ID_SONEKI) ||
    DOGRUSAL_KONFIGUR_KATEGORILERI.includes(kategori);
}

export default konfigurBeklenirMi;
