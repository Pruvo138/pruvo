/**
 * Parametrik ("olcuye ozel") kalemin SUNUCU-TARAFI yeniden hesabi.
 *
 * KIRMIZI CIZGI: istemcinin gonderdigi hacim (`hacim_mm3`) ve fiyat (`parametrik_fiyat_kurus`)
 * OKUNMAZ. Worker semayi kendi bundle'indan alir, parametreleri min/max/adim'a gore dogrular,
 * hacmi jenerator/hacim.js ile KENDI hesaplar, fiyati secenekler.js kuraliyla KENDI cikarir.
 * Istemci "hacim 1 mm3, fiyat 1 kurus" gonderse de sonuc degismez.
 *
 * TEK KAYNAK: dogrulama + hacim + fiyat fonksiyonlari sitenin yukledigi dosyalarin AYNISI
 * (jenerator/konfigurator.js saf cekirdegi + jenerator/hacim.js + /secenekler.js) — kopya YOK.
 *
 * DURUM: PARAMETRIK_ODEME_ACIK (secenekler.js) bugun KAPALI -> baslat() bu kalemleri
 * reddetmeye devam eder (kabul testi 5). Bu modul altyapidir; kabul testi 9 dogrular.
 */

import KONF from "../../jenerator/konfigurator.js";
import HACIM from "../../jenerator/hacim.js";

/**
 * Kalemi sunucuda yeniden hesaplar. Sema DISARIDAN verilir (semalar.js aramasi index.js'te):
 * bu dosya JSON import'u icermez -> kabul testi 9 onu dogrudan node'a yukleyip sinayabilir.
 * @returns {{hata: string}} veya {{birimKurus, hacimMm3, detay, parametreler}}
 */
export function parametrikHesapla(kalem, secenek, sema) {
  if (!sema) { return { hata: "sema-yok" }; }

  const p = kalem.parametreler;
  if (!p || typeof p !== "object" || Array.isArray(p)) { return { hata: "parametre-yok" }; }

  // Semada TANIMSIZ anahtar gonderilmisse reddet: sessizce yok saymak, musterinin girdigi
  // bir olcunun hesaba girmedigi anlamina gelirdi.
  const tanimli = new Set(sema.parametreler.map((x) => x.ad));
  for (const ad of Object.keys(p)) {
    if (!tanimli.has(ad)) { return { hata: "bilinmeyen-parametre", alan: ad }; }
  }

  // min/max/adim + tip dogrulamasi — sitedeki ile AYNI fonksiyon (KONF.dogrula).
  const sonuc = KONF.dogrula(sema, p);
  if (!sonuc.gecerli) {
    return { hata: "parametre-araligi", alanlar: Object.keys(sonuc.hatalar || {}) };
  }

  const hacimMm3 = KONF.hacimMm3(sema, p, HACIM);
  if (hacimMm3 == null) { return { hata: "hacim-hesaplanamadi" }; }

  const birimKurus = secenek.parametrikFiyatKurus(
    sema.tabanFiyatTL, sema.tabanHacimMm3, hacimMm3, kalem.malzeme, kalem.renk);
  // tabanFiyatTL null (bugun 18/18) -> fiyat yok -> odeme akisina giremez.
  if (birimKurus == null || !(birimKurus > 0)) { return { hata: "taban-fiyat-yok" }; }

  return {
    birimKurus: birimKurus,
    hacimMm3: hacimMm3,
    detay: KONF.detayMetni(sema, p),
    parametreler: p,
  };
}
