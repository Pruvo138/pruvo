/**
 * Konfigur ("dekor konfiguratoru") kaleminin SUNUCU-TARAFI yeniden hesabi.
 *
 * KIRMIZI CIZGI (parametrik.js ikizi): istemcinin gonderdigi hacim (`hacim_mm3`) ve fiyat
 * (`parametrik_fiyat_kurus`) OKUNMAZ (index.js istekCoz'da zaten atilir; burada da hic
 * dokunulmaz). Worker konfigur objesini KENDI bundle'indan (konfigurlar.js) alir, boyu
 * [min,max]+adim'a KIRPAR, malzeme katsayisini konfigur.malzemeler LISTESINDEN okur
 * (istemcinin yolladigi katsayi ASLA okunmaz), fiyati /konfigur.js cekirdegiyle KENDI
 * cikarir. Istemci "boy 100000 mm, katsayi 0,01, fiyat 1 kurus" gonderse de sonuc degismez.
 *
 * TEK KAYNAK — KOPYA YOK: boyDuzelt/hacimMm3/fiyatModeli/fiyatKurus fonksiyonlari sitenin
 * yukledigi /konfigur.js dosyasinin AYNISI (PRUVO_KONFIGUR cekirdegi). Bu dosya JSON
 * import'u icermez -> kabul testi konfigurHesapla'yi dogrudan node'a yukleyip sinayabilir;
 * konfigur objesi DISARIDAN verilir (KONFIGURLAR aramasi index.js'te).
 *
 * DURUM: SECENEK.KONFIGUR_ODEME_ACIK (secenekler.js) ile ACIK. Kapatilirsa index.js konfigur
 * kolu kalemi WhatsApp'a yonlendirir (kabul testi (e)).
 */

import KONF from "../../konfigur.js";

/**
 * Konfigur kalemini sunucuda yeniden hesaplar. Konfigur objesi DISARIDAN verilir.
 * @returns {{hata: string}} veya {{birimKurus, parametreler, detay, hacimMm3}}
 */
export function konfigurHesapla(kalem, secenek, konfigur) {
  if (!konfigur || !konfigur.boyutMm || !konfigur.malzemeler) { return { hata: "konfigur-yok" }; }

  // BOY: istemciden alinir AMA boyDuzelt ile [min,max]+adim'a kirpilir. Istemci 100000 mm
  // yollarsa max'e iner, negatif -> min, NaN/adim-disi -> kurala oturur. KIRPILMIS boy kullanilir;
  // ham boy fiyata GIRMEZ (boyDuzelt daima sema araligi icinde gecerli bir deger dondurur).
  const p = kalem.parametreler;
  const hamBoy = (p && typeof p === "object" && !Array.isArray(p)) ? p.boy_mm : undefined;
  const boyMm = KONF.boyDuzelt(konfigur, hamBoy);

  // MALZEME: kalem.malzeme konfigur.malzemeler icindeki bir ad OLMALI; katsayi O LISTEDEN
  // alinir (istemcinin yolladigi katsayi ASLA okunmaz). Listede yoksa REDDET (guvenli taraf:
  // istekCoz malzemeyi genel FILAMENT listesine gore gecirebilir ama konfigur yalniz kendi
  // malzemelerini fiyatlandirir).
  const mal = konfigur.malzemeler.find((m) => m && m.ad === kalem.malzeme);
  if (!mal || !(typeof mal.katsayi === "number" && isFinite(mal.katsayi) && mal.katsayi > 0)) {
    return { hata: "gecersiz-malzeme" };
  }

  const birimKurus = KONF.fiyatKurus(konfigur, boyMm, mal.katsayi);
  if (birimKurus == null || !(birimKurus > 0)) { return { hata: "konfigur-fiyat-yok" }; }

  // parametre_detay /konfigur.js satiraYaz ile BIREBIR ayni bicim (boy cm, virgullu).
  const etiket = (konfigur.boyutMm.etiket || "Boy");
  return {
    birimKurus: birimKurus,
    parametreler: { boy_mm: boyMm },
    detay: etiket + ": " + String(boyMm / 10).replace(".", ",") + " cm",
    hacimMm3: KONF.hacimMm3(konfigur, boyMm),
  };
}
