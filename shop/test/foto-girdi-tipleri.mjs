#!/usr/bin/env node
/**
 * PRUVO shop — ses/konum/tarih PARAMETRE/GİRDİ TİPLERİ kabul kapısı
 * (BaBa 8 Eki 2026 00:3x hüküm 1(e), kraL `kral/foto-duzen`).
 *
 *   node shop/test/foto-girdi-tipleri.mjs
 *
 * KAPSAM: VERI.GIRDI_TURLERI ses/konum/tarih `acik:true`, VERI.FORM_TIPLERI true, ve
 * VERI.parametreDogrula'nın her tip için doğru çalışması — istemci (foto-uretim.js) ve
 * sunucu (shop/src/foto.js → VERI.parametreDogrula) AYNI FONKSİYONU çağırır.
 *
 * Test fikstürü: KENDİ sahte türlerini tanımlar (manifest DEĞİŞMEZ); her türde tek form
 * alanı vardır, böylece "bu alan için bu parametre" izole doğrulanır.
 *
 * OLCULEN KURALLAR:
 *   S  ses genlik dizisi: uzunluk 64..4000, her eleman sonlu sayı 0..1
 *      ✓ 64 / 4000 / 1 eleman
 *      ✗ 63 / 4001 / eleman -0.001 / 1.000001 / NaN / dizi-değil
 *   K  konum: enlem -90..90, boylam -180..180; ikisi sonlu sayı
 *      ✓ 0/0 (deniz) / 90/-180 (kutup) / -90/180
 *      ✗ 90.000001 / -90.000001 / -180.000001 / enlem olmayan / boylam Infinity
 *   T  tarih: "YYYY-AA-GG" takvim geçerli, yıl 1900..2100
 *      ✓ 2024-02-29 (artık yıl) / 1900-01-01 / 2100-12-31
 *      ✗ 2023-02-29 (artık yıl DEĞİL) / 2024-02-30 / 2024-13-01 / 2101-01-01 / 2024/02/29
 *   TS tarih + saat: SS:DD + utc_ofset_saat -12..14
 *      ✓ 12:30 +3 / 00:00 +0 / 23:59 -12
 *      ✗ saat 25:00 / utc 15 / utc -13 / saat:true ise dize
 *   G  GIRDI_TURLERI ses/konum/tarih `acik:true` (3/3); FORM_TIPLERI true (3/3)
 *      grep: `ses: { acik: true }` 1 kez (konum/tarih aynı)
 *   FS foto-uretim.js: ses yolunda FormData yok (ses dosyası sunucuya GİTMEZ; yalnız dizi)
 *
 * MUTANTLAR (geçici bellek kopyasına uygulanır, çalışma ağacına YAZMAZ):
 *   M-SES1 : ses dizi uzunluk denetimi silindi
 *   M-SES2 : ses eleman aralık denetimi silindi
 *   M-KON1 : konum enlem denetimi silindi
 *   M-KON2 : konum boylam denetimi silindi
 *   M-TRH1 : tarih takvim geçersiz kabul edilmedi
 *   M-SAAT1: saat format denetimi silindi
 *   M0     : yalnızca yorum → HİÇBİRİ OLMAZ (kontrol)
 *
 * CIKIS: 0 yeşil · 1 kırmızı · 3 OLCULEMEDİ.
 */

import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

// ---- VERI modülünü bağımsız ortamda kur ----
function veriKur(kaynakMetni) {
  const ctx = vm.createContext({ console });
  vm.runInContext(kaynakMetni, ctx, { filename: "foto-uretim-veri.js" });
  return ctx.PRUVO_FOTO;
}

// HER ALAN İÇİN TEK form alanlı sahte tür — izole doğrulama için.
const sahteTur = (kod, form) => ({
  kod, ad: "sahte " + kod, motor: "D", uretec: "test",
  olcu_mm: { en_az: 80, en_cok: 200 },
  fiyat: { formul: "mm_x_10tl", adim_mm: 10 },
  form, girdi: []
});

// 64 / 4000 / 1 / 63 / 4001 elemanlı örnek diziler (0..1).
function dizi(n) { const a = new Array(n); for (let i = 0; i < n; i++) { a[i] = i / (n || 1); } return a; }

// ------------------------------------------------------------- ana kosum
console.log("G) GIRDI_TURLERI ses/konum/tarih `acik:true` + FORM_TIPLERI true");
const KAYNAK = fs.readFileSync(path.join(KOK, "foto-uretim-veri.js"), "utf8");
let VERI = veriKur(KAYNAK);
ol("G1 GIRDI_TURLERI.ses.acik === true",     VERI.GIRDI_TURLERI.ses.acik === true, JSON.stringify(VERI.GIRDI_TURLERI.ses));
ol("G1b GIRDI_TURLERI.konum.acik === true",  VERI.GIRDI_TURLERI.konum.acik === true, JSON.stringify(VERI.GIRDI_TURLERI.konum));
ol("G1c GIRDI_TURLERI.tarih.acik === true",  VERI.GIRDI_TURLERI.tarih.acik === true, JSON.stringify(VERI.GIRDI_TURLERI.tarih));
ol("G2 FORM_TIPLERI ses/konum/tarih = true", VERI.FORM_TIPLERI.ses === true && VERI.FORM_TIPLERI.konum === true && VERI.FORM_TIPLERI.tarih === true,
   JSON.stringify(VERI.FORM_TIPLERI));
const eslesme = (KAYNAK.match(/ses:\s*\{\s*acik:\s*true\s*\}/g) || []).length;
const konumEs = (KAYNAK.match(/konum:\s*\{\s*acik:\s*true\s*\}/g) || []).length;
const tarihEs = (KAYNAK.match(/tarih:\s*\{\s*acik:\s*true\s*\}/g) || []).length;
ol("G3 `ses: { acik: true }` 1 kez",  eslesme === 1,  eslesme + " kez");
ol("G3b `konum: { acik: true }` 1 kez", konumEs === 1, konumEs + " kez");
ol("G3c `tarih: { acik: true }` 1 kez", tarihEs === 1, tarihEs + " kez");

const fotoKaynak = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
const formDataSatirlari = fotoKaynak.split("\n").filter((s) => /FormData/.test(s));
ol("FS foto-uretim.js'de FormData yok (ses dosyası sunucuya GİTMEZ)", formDataSatirlari.length === 0,
   formDataSatirlari.length + " satır: " + formDataSatirlari.map((x) => x.trim()).join(" | "));

console.log("S) SES (genlik dizisi: 64..4000 eleman, her biri sonlu 0..1)");
{
  const t = sahteTur("ses-test", { alan: { tip: "ses", etiket: "Ses" } });
  VERI.turler.push(t);
  ol("S1 64 eleman ✓",  VERI.parametreDogrula(t.kod, { alan: dizi(64) }).ok === true,  JSON.stringify(VERI.parametreDogrula(t.kod, { alan: dizi(64) })));
  ol("S2 4000 eleman ✓", VERI.parametreDogrula(t.kod, { alan: dizi(4000) }).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, { alan: dizi(4000) })));
  const s63 = dizi(63);  ol("S3 63 eleman ✗",  VERI.parametreDogrula(t.kod, { alan: s63 }).ok === false && VERI.parametreDogrula(t.kod, { alan: s63 }).hata === "parametre-ses", JSON.stringify(VERI.parametreDogrula(t.kod, { alan: s63 })));
  const s4001 = dizi(4001); ol("S4 4001 eleman ✗", VERI.parametreDogrula(t.kod, { alan: s4001 }).ok === false && VERI.parametreDogrula(t.kod, { alan: s4001 }).hata === "parametre-ses", JSON.stringify(VERI.parametreDogrula(t.kod, { alan: s4001 })));
  const neg = dizi(64); neg[10] = -0.001;
  ol("S5 eleman -0.001 ✗", VERI.parametreDogrula(t.kod, { alan: neg }).ok === false && VERI.parametreDogrula(t.kod, { alan: neg }).hata === "parametre-ses", JSON.stringify(VERI.parametreDogrula(t.kod, { alan: neg })));
  const ust = dizi(64); ust[10] = 1.000001;
  ol("S6 eleman 1.000001 ✗", VERI.parametreDogrula(t.kod, { alan: ust }).ok === false && VERI.parametreDogrula(t.kod, { alan: ust }).hata === "parametre-ses", JSON.stringify(VERI.parametreDogrula(t.kod, { alan: ust })));
  const nan = dizi(64); nan[10] = NaN;
  ol("S7 eleman NaN ✗", VERI.parametreDogrula(t.kod, { alan: nan }).ok === false && VERI.parametreDogrula(t.kod, { alan: nan }).hata === "parametre-ses", JSON.stringify(VERI.parametreDogrula(t.kod, { alan: nan })));
  ol("S8 dizi-değil ✗", VERI.parametreDogrula(t.kod, { alan: "ses" }).ok === false && VERI.parametreDogrula(t.kod, { alan: "ses" }).hata === "parametre-ses", JSON.stringify(VERI.parametreDogrula(t.kod, { alan: "ses" })));
}

console.log("K) KONUM (enlem -90..90, boylam -180..180)");
{
  const t = sahteTur("konum-test", { alan: { tip: "konum", etiket: "Konum" } });
  VERI.turler.push(t);
  ol("K1 0/0 (deniz) ✓", VERI.parametreDogrula(t.kod, { alan: { enlem: 0, boylam: 0 } }).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, { alan: { enlem: 0, boylam: 0 } })));
  ol("K2 90/-180 (kutup) ✓", VERI.parametreDogrula(t.kod, { alan: { enlem: 90, boylam: -180 } }).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, { alan: { enlem: 90, boylam: -180 } })));
  ol("K3 -90/180 ✓", VERI.parametreDogrula(t.kod, { alan: { enlem: -90, boylam: 180 } }).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, { alan: { enlem: -90, boylam: 180 } })));
  const e1 = { alan: { enlem: 90.000001, boylam: 0 } }; ol("K4 90.000001 ✗", VERI.parametreDogrula(t.kod, e1).ok === false && VERI.parametreDogrula(t.kod, e1).hata === "parametre-konum", JSON.stringify(VERI.parametreDogrula(t.kod, e1)));
  const e2 = { alan: { enlem: -90.000001, boylam: 0 } }; ol("K5 -90.000001 ✗", VERI.parametreDogrula(t.kod, e2).ok === false && VERI.parametreDogrula(t.kod, e2).hata === "parametre-konum", JSON.stringify(VERI.parametreDogrula(t.kod, e2)));
  const e3 = { alan: { enlem: 0, boylam: -180.000001 } }; ol("K6 -180.000001 ✗", VERI.parametreDogrula(t.kod, e3).ok === false && VERI.parametreDogrula(t.kod, e3).hata === "parametre-konum", JSON.stringify(VERI.parametreDogrula(t.kod, e3)));
  const e4 = { alan: { enlem: "x", boylam: 0 } }; ol("K7 enlem olmayan ✗", VERI.parametreDogrula(t.kod, e4).ok === false && VERI.parametreDogrula(t.kod, e4).hata === "parametre-konum", JSON.stringify(VERI.parametreDogrula(t.kod, e4)));
  const e5 = { alan: { enlem: 0, boylam: Infinity } }; ol("K8 boylam Infinity ✗", VERI.parametreDogrula(t.kod, e5).ok === false && VERI.parametreDogrula(t.kod, e5).hata === "parametre-konum", JSON.stringify(VERI.parametreDogrula(t.kod, e5)));
}

console.log("T) TARIH (YYYY-AA-GG, 1900..2100, takvim geçerli)");
{
  const t = sahteTur("tarih-test", { alan: { tip: "tarih", etiket: "Tarih" } });
  VERI.turler.push(t);
  const g1 = { alan: "2024-02-29" }; ol("T1 2024-02-29 (artık yıl) ✓", VERI.parametreDogrula(t.kod, g1).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, g1)));
  const g2 = { alan: "1900-01-01" }; ol("T2 1900-01-01 ✓", VERI.parametreDogrula(t.kod, g2).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, g2)));
  const g3 = { alan: "2100-12-31" }; ol("T3 2100-12-31 ✓", VERI.parametreDogrula(t.kod, g3).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, g3)));
  const x1 = { alan: "2023-02-29" }; ol("T4 2023-02-29 (artık yıl DEĞİL) ✗", VERI.parametreDogrula(t.kod, x1).ok === false && VERI.parametreDogrula(t.kod, x1).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x1)));
  const x2 = { alan: "2024-02-30" }; ol("T5 2024-02-30 ✗", VERI.parametreDogrula(t.kod, x2).ok === false && VERI.parametreDogrula(t.kod, x2).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x2)));
  const x3 = { alan: "2024-13-01" }; ol("T6 2024-13-01 ✗", VERI.parametreDogrula(t.kod, x3).ok === false && VERI.parametreDogrula(t.kod, x3).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x3)));
  const x4 = { alan: "2101-01-01" }; ol("T7 2101-01-01 ✗", VERI.parametreDogrula(t.kod, x4).ok === false && VERI.parametreDogrula(t.kod, x4).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x4)));
  const x5 = { alan: "2024/02/29" }; ol("T8 bicim bozuk ✗", VERI.parametreDogrula(t.kod, x5).ok === false && VERI.parametreDogrula(t.kod, x5).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x5)));
}

console.log("TS) TARIH + SAAT (saat:true ise SS:DD + utc_ofset_saat -12..14)");
{
  const t = sahteTur("ts-test", { alan: { tip: "tarih", etiket: "Tarih saat", saat: true } });
  VERI.turler.push(t);
  const g1 = { alan: { tarih: "2026-10-08", saat: "12:30", utc_ofset_saat: 3 } };
  ol("TS1 12:30 +3 ✓", VERI.parametreDogrula(t.kod, g1).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, g1)));
  const g2 = { alan: { tarih: "2026-10-08", saat: "00:00", utc_ofset_saat: 0 } };
  ol("TS2 00:00 +0 ✓", VERI.parametreDogrula(t.kod, g2).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, g2)));
  const g3 = { alan: { tarih: "2026-10-08", saat: "23:59", utc_ofset_saat: -12 } };
  ol("TS3 23:59 -12 ✓", VERI.parametreDogrula(t.kod, g3).ok === true, JSON.stringify(VERI.parametreDogrula(t.kod, g3)));
  const x1 = { alan: { tarih: "2026-10-08", saat: "25:00", utc_ofset_saat: 3 } };
  ol("TS4 25:00 ✗", VERI.parametreDogrula(t.kod, x1).ok === false && VERI.parametreDogrula(t.kod, x1).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x1)));
  const x2 = { alan: { tarih: "2026-10-08", saat: "12:00", utc_ofset_saat: 15 } };
  ol("TS5 utc_ofset_saat 15 ✗", VERI.parametreDogrula(t.kod, x2).ok === false && VERI.parametreDogrula(t.kod, x2).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x2)));
  const x3 = { alan: { tarih: "2026-10-08", saat: "12:00", utc_ofset_saat: -13 } };
  ol("TS6 utc_ofset_saat -13 ✗", VERI.parametreDogrula(t.kod, x3).ok === false && VERI.parametreDogrula(t.kod, x3).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x3)));
  const x4 = { alan: "2026-10-08" };
  ol("TS7 saat:true ise dize kabul edilmez ✗", VERI.parametreDogrula(t.kod, x4).ok === false && VERI.parametreDogrula(t.kod, x4).hata === "parametre-tarih", JSON.stringify(VERI.parametreDogrula(t.kod, x4)));
}

// ---------------------------------------------------------------- MUTANTLAR
console.log("MUTANTLAR (geçici bellek kopyası; çalışma ağacına YAZMAZ)");

// BLOK-bazlı mutasyon: belirli bir başlangıç satırıyla eşleşen if/for/while bloğunu kaldırır.
// Başlangıçtan sonraki satırlar küme parantezi sayımıyla kapanana dek kaldırılır.
// Eğer `tekSatir` true ise başlangıç satırıyla birlikte TEK satırda biten `return ...;` formundaysa
// `return ...;` satırını da kaldırır.
function blokCikar(kaynak, baslangicDeseni) {
  const satirlar = kaynak.split("\n");
  const sonuc = [];
  let iceride = false, sayac = 0;
  for (const s of satirlar) {
    if (!iceride) {
      if (s.indexOf(baslangicDeseni) >= 0) {
        iceride = true;
        // Başlangıç satırı kendisi bir kapanış içeriyorsa (örn. `if (...) { return ... }`)
        // tek satırlık ifade — yine de küme parantezi sayımı yapılır.
        for (const c of s) { if (c === "{") { sayac++; } else if (c === "}") { sayac--; } }
        if (sayac <= 0) { iceride = false; sayac = 0; }
        continue;
      }
      sonuc.push(s);
    } else {
      for (const c of s) { if (c === "{") { sayac++; } else if (c === "}") { sayac--; } }
      if (sayac <= 0) { iceride = false; sayac = 0; }
    }
  }
  return sonuc.join("\n");
}
// Tek satırlık ifadeyi kaldır (regex test içeren if'ler için).
function satirCikar(kaynak, hedef) {
  const satirlar = kaynak.split("\n");
  return satirlar.filter((s) => s.indexOf(hedef) < 0).join("\n");
}

const KIRMIZI_SEN_SES_UZUNLUK = [
  ["S3 63 eleman",   { fail: true,  v: () => dizi(63) }],
  ["S4 4001 eleman", { fail: true,  v: () => dizi(4001) }],
  ["S1 64 eleman",   { fail: false, v: () => dizi(64) }]
];
const KIRMIZI_SEN_SES_ELEMAN = [
  ["S5 -0.001",  { fail: true,  v: () => { const a = dizi(64); a[10] = -0.001; return a; } }],
  ["S6 1.000001",{ fail: true,  v: () => { const a = dizi(64); a[10] = 1.000001; return a; } }],
  ["S1 64 eleman",{ fail: false, v: () => dizi(64) }]
];
const KIRMIZI_SEN_KONUM_ENLEM = [
  ["K4 90.000001", { fail: true,  v: () => ({ enlem: 90.000001, boylam: 0 }) }],
  ["K1 0/0",       { fail: false, v: () => ({ enlem: 0, boylam: 0 }) }]
];
const KIRMIZI_SEN_KONUM_BOYLAM = [
  ["K6 -180.000001", { fail: true,  v: () => ({ enlem: 0, boylam: -180.000001 }) }],
  ["K2 90/-180",     { fail: false, v: () => ({ enlem: 90, boylam: -180 }) }]
];
const KIRMIZI_SEN_TARIH_TAKVIM = [
  ["T4 2023-02-29", { fail: true,  v: () => "2023-02-29" }],
  ["T5 2024-02-30", { fail: true,  v: () => "2024-02-30" }],
  ["T1 2024-02-29", { fail: false, v: () => "2024-02-29" }]
];
const KIRMIZI_SEN_SAAT = [
  ["TS4 25:00",  { fail: true,  v: () => ({ tarih: "2026-10-08", saat: "25:00", utc_ofset_saat: 3 }) }],
  ["TS1 12:30",  { fail: false, v: () => ({ tarih: "2026-10-08", saat: "12:30", utc_ofset_saat: 3 }) }]
];

function mutantKos(etiket, kaynakMutasyonu, tip, senaryolar) {
  const yeniKaynak = kaynakMutasyonu(KAYNAK);
  const v = veriKur(yeniKaynak);
  const t = sahteTur("mtest-" + etiket.replace(/[^a-z0-9]/gi, ""), { alan: { tip: tip, etiket: tip, ...(tip === "tarih" ? { saat: false } : {}) } });
  v.turler.push(t);
  // Beklenti: mutasyon, "fail:true" senaryolarını YANLIŞLIKLA kabul eder hale getirir
  // (yani gerçekKirmizi = mutantın bozduğu fail:true senaryoları).
  // "fail:false" (geçerli) senaryoları mutasyondan etkilenmemeli — mutant bunları da bozarsa
  // beklenenden fazla kırmızı çıkar (o da KIRMIZI sayılır).
  const gercekKirmizi = [];
  for (const [ad, sen] of senaryolar) {
    const sonuc = v.parametreDogrula(t.kod, { alan: sen.v() });
    const isFail = sen.fail ? sonuc.ok === false : sonuc.ok === true;
    if (!isFail) { gercekKirmizi.push(ad); }
  }
  const failTrular = senaryolar.filter(([, sen]) => sen.fail).map(([ad]) => ad);
  // Test geçerli: TÜM fail:true senaryolar mutantla bozuldu VE fail:false senaryolar BOZULMADI.
  const tumFailTrularBozuldu = failTrular.every((ad) => gercekKirmizi.includes(ad));
  const baskaKirildi = gercekKirmizi.some((ad) => !failTrular.includes(ad));
  ol(etiket + " -> mutant KIRMIZI [" + gercekKirmizi.join(",") + "] (fail:true=" + failTrular.length + ", ek=" + (baskaKirildi ? "1" : "0") + ")",
     tumFailTrularBozuldu && !baskaKirildi, JSON.stringify(gercekKirmizi));
}

mutantKos("M-SES1 uzunluk denetimi silindi",   (k) => blokCikar(k, "if (v.length < 64 || v.length > 4000)"), "ses",   KIRMIZI_SEN_SES_UZUNLUK);
mutantKos("M-SES2 eleman aralık denetimi silindi", (k) => blokCikar(k, "if (typeof v[g] !== \"number\""), "ses",   KIRMIZI_SEN_SES_ELEMAN);
mutantKos("M-KON1 enlem denetimi silindi",      (k) => blokCikar(k, "if (typeof v.enlem !== \"number\""), "konum", KIRMIZI_SEN_KONUM_ENLEM);
mutantKos("M-KON2 boylam denetimi silindi",     (k) => blokCikar(k, "if (typeof v.boylam !== \"number\""), "konum", KIRMIZI_SEN_KONUM_BOYLAM);
mutantKos("M-TRH1 takvim geçersiz kabul edilmedi", (k) => blokCikar(k, "if (d.getUTCFullYear() !== y"), "tarih", KIRMIZI_SEN_TARIH_TAKVIM);

// SAAT mutantı: saat format denetimi (regex test) kaldırılır.
// Bu denetim `if (typeof satStr !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(satStr))` satırında
// tek satırlık ifade olduğu için satirCikar yeterli.
mutantKos("M-SAAT1 saat format denetimi silindi",
  (k) => satirCikar(k, "if (typeof satStr !== \"string\" || !/^([01]\\d|2[0-3]):[0-5]\\d$/.test(satStr))"),
  "tarih",
  [
    ["TS4 25:00", { fail: true,  v: () => ({ tarih: "2026-10-08", saat: "25:00", utc_ofset_saat: 3 }) }],
    ["TS1 12:30", { fail: false, v: () => ({ tarih: "2026-10-08", saat: "12:30", utc_ofset_saat: 3 }) }]
  ]
);

// M0 kontrol: kaynak mutasyonsuz → tüm senaryolar gerçek sonuçlarına uyuyor (hiçbiri KIRMIZI olmaz).
console.log("M0 KONTROL (yalnız yorum) — kaynak mutasyonsuz, senaryolar beklenen sonuçlarıyla eşleşmeli");
{
  let v = VERI; // orijinal VERI zaten yüklü
  // `saat` senaryoları için ayrı tür (saat:true).
  const kontrolSenaryolari = [
    ["S3 63 eleman", "ses",   { saat: false }, () => dizi(63), true],
    ["S5 -0.001", "ses",      { saat: false }, () => { const a = dizi(64); a[10] = -0.001; return a; }, true],
    ["K4 90.000001", "konum", { saat: false }, () => ({ enlem: 90.000001, boylam: 0 }), true],
    ["T4 2023-02-29", "tarih", { saat: false }, () => "2023-02-29", true],
    ["T5 2024-02-30", "tarih", { saat: false }, () => "2024-02-30", true],
    ["TS4 25:00", "tarih", { saat: true }, () => ({ tarih: "2026-10-08", saat: "25:00", utc_ofset_saat: 3 }), true]
  ];
  const uymayanlar = [];
  for (const [ad, tip, semaEk, vFn, fail] of kontrolSenaryolari) {
    const t = sahteTur("m0-" + ad.replace(/[^a-z0-9]/gi, ""), { alan: { tip: tip, etiket: tip, ...semaEk } });
    v.turler.push(t);
    const sonuc = v.parametreDogrula(t.kod, { alan: vFn() });
    const isFail = fail ? sonuc.ok === false : sonuc.ok === true;
    if (!isFail) { uymayanlar.push(ad); }
  }
  ol("M0 KONTROL (yalnız yorum) -> KIRMIZI []",
     uymayanlar.length === 0, JSON.stringify(uymayanlar));
}

// ---------------------------------------------------------------- SURVIVOR
const survivor = kirmizi === 0 ? 0 : 1;
console.log("\n" + (kirmizi === 0 ? "✅ HEPSI GECTI · SURVIVOR=0" : "❌ KIRMIZI=" + kirmizi + " · SURVIVOR=" + survivor));
process.exit(kirmizi === 0 ? 0 : 1);