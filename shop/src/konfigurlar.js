/**
 * Konfigur ("dekor konfiguratoru") urunlerinin sunucu-tarafi kopyasi — Worker bundle'ina
 * ELLE bakimli statik harita (semalar.js emsali).
 *
 * NEDEN ELLE LISTE: konfigur verisi urunler.json ICINDE (urunun "konfigur" alani) yasar; tum
 * urunler.json'u Worker bundle'ina katmak (~yuz binlerce satir) script boyutunu patlatir.
 * Bu yuzden yalniz konfigur objeleri BURAYA elle kopyalanir. BAYATLAMA KORUMASI: kabul testi
 * "konfigurlar-guard", bu haritanin urunler.json'daki "konfigur" alanlariyla BIREBIR
 * ortustugunu VE tum konfigur urunlerini kapsadigini dogrular — yeni konfigur urunu eklenip
 * burasi guncellenmezse (ya da deger kaydirilirsa) test KIRMIZI yanar (sessizce "konfigur yok
 * -> sabit-fiyat kolu" davranisina dusmez; bu, boy/malzemeye gore fiyati YOK SAYMAK olurdu).
 *
 * Konfigur verisi public (matematik + aralik + renk/malzeme); sir icermez.
 */

// kurt-heykeli-serit-dekoratif-figur (urunler.json "konfigur" alaninin BIREBIR kopyasi).
const kurtHeykeli = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 1899.739, refHacimCm3: 239222.8 },
  fiyatCapalari: [[60, 150], [300, 1300]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// Anahtar urunler.json'daki kebab-id ile eslesir; eslesmezse index.js konfigur kolu bu urunu
// GORMEZ (KONFIGURLAR.has=false) ve urun sabit-fiyat koluna duser -> guard bunu yakalar.
export const KONFIGURLAR = new Map([
  ["kurt-heykeli-serit-dekoratif-figur", kurtHeykeli],
]);

export default KONFIGURLAR;
