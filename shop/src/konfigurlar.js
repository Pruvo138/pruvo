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
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// at-bustu-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const atBustu = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 267.47 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// yeleli-at-bustu-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const yeleliAtBustu = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 152.83 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// balina-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const balina = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 213.12 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// sonsuzluk-halkasi-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const sonsuzlukHalkasi = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 221.9 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// sonsuzluk-dugumu-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const sonsuzlukDugumu = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 133.94 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// at-silueti-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const atSilueti = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 41.75 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// yaprak-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const yaprak = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 33.57 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// geyik-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const geyik = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 55.68 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// at-figuru-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const atFiguru = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 269.34 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// gozu-bagli-baykus-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const gozuBagliBaykus = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 1, Siyah: 0, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 346.49 },
  fiyatCapalari: [[60, 500], [300, 2500]],
  malzemeler: [
    { ad: "PLA", katsayi: 1.0 },
    { ad: "PETG", katsayi: 1.3 },
    { ad: "ASA", katsayi: 1.6 },
  ],
  varsayilanMalzeme: "PLA",
};

// boga-serit-dekoratif-figur (urunler.json 'konfigur' alaninin BIREBIR kopyasi).
const bogaSeritFigur = {
  renkler: ["Siyah", "Beyaz", "Gri"],
  renkGorselIndeks: { Gri: 0, Siyah: 1, Beyaz: 2 },
  boyutMm: { min: 60, max: 300, adim: 10, varsayilan: 150, etiket: "Yükseklik" },
  hacim: { refYukseklikMm: 150, refHacimCm3: 77.27 },
  fiyatCapalari: [[60, 500], [300, 2500]],
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
  ["at-bustu-serit-dekoratif-figur", atBustu],
  ["yeleli-at-bustu-serit-dekoratif-figur", yeleliAtBustu],
  ["balina-serit-dekoratif-figur", balina],
  ["sonsuzluk-halkasi-serit-dekoratif-figur", sonsuzlukHalkasi],
  ["sonsuzluk-dugumu-serit-dekoratif-figur", sonsuzlukDugumu],
  ["at-silueti-serit-dekoratif-figur", atSilueti],
  ["yaprak-serit-dekoratif-figur", yaprak],
  ["geyik-serit-dekoratif-figur", geyik],
  ["at-figuru-serit-dekoratif-figur", atFiguru],
  ["gozu-bagli-baykus-serit-dekoratif-figur", gozuBagliBaykus],
  ["boga-serit-dekoratif-figur", bogaSeritFigur],
]);

export default KONFIGURLAR;
