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

  // SEMA BICIMI FAIL-CLOSED (2026-07-31, OLCULDU): `sema.parametreler` yok/dizi degilse
  // eski kod `sema.parametreler.map` ile TypeError FIRLATIYORDU -> istisna Worker'in
  // fetch kolundan disari cikip 500 uretiyor, `if (ph.hata)` dali HIC KOSMUYOR, yani
  // musteri fail-closed 400 + "WhatsApp'tan teklif alin" mesajini GORMUYORDU. Para
  // acisindan yine tahsilat YOKTU (hesap iyzico'dan ONCE patliyor) ama sinif belirsiz bir
  // COKMEYDI. Artik ayni sinifa (acik hata kodu -> 400 -> WhatsApp) iner.
  // DAR: yalnizca bugun ZATEN patlayan bicimleri yakalar, gecerli semayi etkilemez.
  if (!Array.isArray(sema.parametreler)) { return { hata: "sema-bozuk" }; }

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

  /* HACIM DOGRULAMA KAPISI (para, 2026-07-31 — bkz. secenekler.js
     HACIM_DOGRULANMIS_AILELER blogu). Ailenin hacim formulu GERCEK geometriye
     (OpenSCAD render) karsi olculup %3 sinirini gecmediyse tutar URETILMEZ.

     HACIM HESABINDAN ONCE: guvenmedigimiz bir formulu kosturmanin anlami yok, ayrica
     boyle bir ailede hacim hesabi kendi icinde de patlayabilir ve musteri "hacim
     hesaplanamadi" gibi ALAKASIZ bir tani gorurdu. Kapi burada olunca sebep tektir.

     Kapinin KENDISI parametrikFiyatKurus'un ICINDE (tek kaynak, front ile AYNI kod) —
     burasi ek bir kopya DEGIL, yalnizca musteriye DOGRU MESAJI goturen acik hata kodu.
     Tanisal ayrim onemli: "fiyat girilmemis" (taban-fiyat-yok) ile "fiyat GUVENILMEZ"
     ayni sey degildir. */
  if (!secenek.hacimDogrulanmisMi(sema.hacimFormulu)) {
    return { hata: "hacim-dogrulanmamis" };
  }

  const hacimMm3 = KONF.hacimMm3(sema, p, HACIM);
  if (hacimMm3 == null) { return { hata: "hacim-hesaplanamadi" }; }

  let birimKurus = secenek.parametrikFiyatKurus(
    sema.hacimFormulu, sema.tabanFiyatTL, sema.tabanHacimMm3, hacimMm3,
    kalem.malzeme, kalem.renk);
  // tabanFiyatTL null (bugun 18/18) -> fiyat yok -> odeme akisina giremez.
  if (birimKurus == null || !(birimKurus > 0)) { return { hata: "taban-fiyat-yok" }; }

  // 2-RENK YAZI EK UCRETI (cerceve): yazi dolu VE yazi_renk cerceve renginden farkli ise
  // ayri govde uretimi (AMS 2 filaman) icin ek ucret. Boyut/3x tavanin DISINDA: hacme girmez,
  // clamp'ten SONRA eklenir (tavan yaziyi icermez). yazi param olmayan urunlerde (p.yazi
  // undefined) veya yazi_renk yoksa/esitse tetiklenmez -> diger sari aileleri etkilemez.
  //
  // TUTAR BURADA YAZILI DEGIL: secenekler.js IKI_RENK_EK_KURUS (TEK KAYNAK) — front
  // (jenerator/konfigurator.js) AYNI degeri okur. 2026-07-29 itibariyle 0 = TAHSIL EDILMEZ
  // (olcum: yazi uretilen STL'e girmiyor, uc render SHA-256 birebir ayni -> karsiligi yok).
  // Ikinci bir sabit BIRAKMA: iki taraf ayrisirsa gosterilen != tahsil edilen olur.
  const ikiRenk = p.yazi && kalem.yazi_renk && kalem.yazi_renk !== kalem.renk;
  let detay = KONF.detayMetni(sema, p);
  if (ikiRenk) {
    // 2-renk basilabilirlik: kabartma yazi mevcut alt kenara oturur (Caption_Fit=existing),
    // kenar dar ise yazi sigmaz/SCAD assert atar. Dar kenarda 2-renk siparisini REDDET.
    // min kenar 10 mm (KaaN render: production floor; 9mm stem 0.69mm<nozul kirilgan, 10mm 0.89mm robust).
    const IKI_RENK_MIN_KENAR = 10;
    if (!(kalem.parametreler.kenar_genisligi >= IKI_RENK_MIN_KENAR)) {
      return { hata: "iki-renk-kenar-dar", enAz: IKI_RENK_MIN_KENAR };
    }
    // FAIL-CLOSED: sabit bundle'a gelmemisse (bozuk/eski secenekler.js) NaN fiyat tahsil
    // etmektense kalemi reddet — sessiz yanlis tutar, acik hatadan daha pahalidir.
    const ekKurus = secenek.IKI_RENK_EK_KURUS;
    if (typeof ekKurus !== "number" || !isFinite(ekKurus) || ekKurus < 0) {
      return { hata: "iki-renk-ucret-tanimsiz" };
    }
    birimKurus += ekKurus;
    detay += secenek.ikiRenkDetayEki(kalem.yazi_renk);
  }

  return {
    birimKurus: birimKurus,
    hacimMm3: hacimMm3,
    detay: detay,
    parametreler: p,
  };
}
