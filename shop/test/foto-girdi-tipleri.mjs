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
  fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600 },
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

console.log("B) BOOL (kopru-15 sözlük: YALNIZ true/false; dize/sayı/null RED)");
{
  ol("B0 FORM_TIPLERI.bool === true", VERI.FORM_TIPLERI.bool === true, JSON.stringify(VERI.FORM_TIPLERI));
  const t = sahteTur("bool-test", { alan: { tip: "bool", etiket: "Kapak", varsayilan: false } });
  VERI.turler.push(t);
  const d = (v) => VERI.parametreDogrula(t.kod, { alan: v });
  ol("B1 true ✓ (deger true)", d(true).ok === true && d(true).deger.alan === true, JSON.stringify(d(true)));
  ol("B2 false ✓ (deger false)", d(false).ok === true && d(false).deger.alan === false, JSON.stringify(d(false)));
  for (const [ad, v] of [["B3 \"true\"", "true"], ["B4 \"1\"", "1"], ["B5 1", 1], ["B6 0", 0], ["B7 null", null], ["B8 \"false\"", "false"]]) {
    ol(ad + " ✗ parametre-bool", d(v).ok === false && d(v).hata === "parametre-bool", JSON.stringify(d(v)));
  }
  ol("B9 alan yok ✗ parametre-bool", VERI.parametreDogrula(t.kod, {}).hata === "parametre-bool", JSON.stringify(VERI.parametreDogrula(t.kod, {})));
  // Gerçek manifest: G4a türlerinin bool alanı (kutu.kapak / adaptor.flans / kapak.topuz) "parametre-yakinda" DEĞİL.
  for (const [kod, alan] of [["kutu", "kapak"], ["adaptor", "flans"], ["kapak", "topuz"]]) {
    const tt = VERI.turBul(kod);
    ol("B10 " + kod + "." + alan + " tip bool", !!tt && tt.form[alan] && tt.form[alan].tip === "bool", kod);
  }
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

const KIRMIZI_SEN_BOOL = [
  ["B3 \"true\"", { fail: true,  v: () => "true" }],
  ["B5 1",        { fail: true,  v: () => 1 }],
  ["B7 null",     { fail: true,  v: () => null }],
  ["B1 true",     { fail: false, v: () => true }],
  ["B2 false",    { fail: false, v: () => false }]
];
// BOOL mutantı: true/false denetimi silinir -> dize/sayı/null kabul edilir.
mutantKos("M-BOOL1 bool true/false denetimi silindi",
  (k) => satirCikar(k, "if (v !== true && v !== false) { return { ok: false, hata: \"parametre-bool\" }; }"), "bool", KIRMIZI_SEN_BOOL);
// BOOL mutantı 2: FORM_TIPLERI'nden bool düşer -> geçerli true/false da "parametre-yakinda" (geçerliler KIRMIZI).
{
  const v = veriKur(KAYNAK.replace(", bool: true };", " };"));
  const t = sahteTur("mtest-bool2", { alan: { tip: "bool", etiket: "b" } });
  v.turler.push(t);
  const r = v.parametreDogrula(t.kod, { alan: true });
  ol("M-BOOL2 FORM_TIPLERI.bool dustu -> true KIRMIZI (parametre-yakinda)", r.ok === false && r.hata === "parametre-yakinda", JSON.stringify(r));
}

// KOSUL (kopru-15 DILIM-2): koşulu sağlanmayan alan çıktıya GİRMEZ, gönderilirse sema-disi-parametre;
// sağlanan alan ZORUNLU; adım ızgarası kayıttaki adıma göre (enlem/boylam 0.000001: 40.15-(-90) /1e-6 kayan
// nokta hatası 1.5e-8 > 1e-9 — Uludağ örneği; KS1 bunu ölçer).
const KOSUL_FORM = {
  mod: { tip: "secim", secenekler: ["pul", "burc", "adaptor"] },
  kademe_mm: { tip: "sayi", min: 6, max: 150, adim: 0.01, kosul: [{ alan: "mod", degerler: ["adaptor"] }] },
  flans: { tip: "bool", kosul: [{ alan: "mod", degerler: ["burc", "adaptor"] }] },
  flans_cap_mm: { tip: "sayi", min: 8, max: 150, adim: 0.01,
    kosul: [{ alan: "mod", degerler: ["burc", "adaptor"] }, { alan: "flans", degerler: [true] }] },
  duvar_mm: { tip: "sayi", min: 1.2, max: 4, adim: 0.01 },
  enlem: { tip: "sayi", min: -90, max: 90, adim: 0.000001 }
};
const KOSUL_VAKA = [
  ["KS1 burc, kosulsuz alan yok -> ok, cikti yalniz aktif", { mod: "burc", flans: false, duvar_mm: 1.6, enlem: 40.15 },
    { ok: true, anahtar: "duvar_mm,enlem,flans,mod" }],
  ["KS2 burc + kademe (kosul mod=adaptor) -> sema-disi", { mod: "burc", flans: false, kademe_mm: 14, duvar_mm: 1.6, enlem: 0 },
    { ok: false, hata: "sema-disi-parametre" }],
  ["KS3 adaptor, kademe EKSIK (aktif=zorunlu) -> aralik", { mod: "adaptor", flans: false, duvar_mm: 1.6, enlem: 0 },
    { ok: false, hata: "parametre-aralik" }],
  ["KS4 adaptor + flans=true + kademe + flans_cap -> ok", { mod: "adaptor", flans: true, kademe_mm: 14, flans_cap_mm: 30, duvar_mm: 4, enlem: -90 },
    { ok: true, anahtar: "duvar_mm,enlem,flans,flans_cap_mm,kademe_mm,mod" }],
  ["KS5 pul + flans (kosul mod) -> sema-disi", { mod: "pul", flans: true, duvar_mm: 1.6, enlem: 0 },
    { ok: false, hata: "sema-disi-parametre" }],
  ["KS6 pul (zincir: flans yok -> flans_cap yok) -> ok", { mod: "pul", duvar_mm: 1.6, enlem: 0 },
    { ok: true, anahtar: "duvar_mm,enlem,mod" }],
  ["KS7 adim 0.01: 1.605 izgara disi -> adim", { mod: "pul", duvar_mm: 1.605, enlem: 0 },
    { ok: false, hata: "parametre-adim" }],
  ["KS8 adim 0.000001: 41.0082005 izgara disi -> adim", { mod: "pul", duvar_mm: 1.6, enlem: 41.0082005 },
    { ok: false, hata: "parametre-adim" }]
];
function kosulKos(v) {
  const t = sahteTur("kosul-" + Math.random().toString(36).slice(2), KOSUL_FORM);
  v.turler.push(t);
  const kirmizi = [];
  for (const [ad, p, b] of KOSUL_VAKA) {
    const r = v.parametreDogrula(t.kod, p);
    const uy = b.ok ? (r.ok === true && Object.keys(r.deger).sort().join(",") === b.anahtar) : (r.ok === false && r.hata === b.hata);
    if (!uy) { kirmizi.push(ad.split(" ")[0]); }
  }
  return kirmizi;
}
console.log("KS) KOSUL + ADIM (kopru-15 DILIM-2)");
{
  const k = kosulKos(veriKur(KAYNAK));
  for (const [ad] of KOSUL_VAKA) { ol(ad, !k.includes(ad.split(" ")[0])); }
  // Gercek manifest: G4a turlerinin TeKiN varsayilanlari (duvar 1.6, gecme 0.3 ...) GECERLI, kosulsuz alan yok.
  const G4A = {
    kutu: { en_mm: 100, boy_mm: 60, yukseklik_mm: 40, bolme_x: 2, bolme_y: 2, duvar_mm: 1.6, taban_mm: 1.6, kose_yaricap_mm: 3, kapak: false },
    adaptor: { mod: "burc", ic_cap_mm: 10, dis_cap_mm: 20, yukseklik_mm: 15, flans: false }
  };
  for (const kod of Object.keys(G4A)) {
    const r = VERI.parametreDogrula(kod, G4A[kod]);
    ol("KS9 manifest " + kod + " TeKiN varsayilanlari -> ok", r.ok === true, JSON.stringify(r));
  }
  const r2 = VERI.parametreDogrula("adaptor", Object.assign({ kademe_cap_mm: 14 }, G4A.adaptor));
  ol("KS10 manifest adaptor burc + kademe_cap_mm -> sema-disi", r2.ok === false && r2.hata === "sema-disi-parametre", JSON.stringify(r2));
}
// KOSUL mutantlari: hedef KIRMIZI kumesi TAM eslesmeli (fazlasi da eksigi de KIRMIZI).
function kosulMutant(etiket, eski, yeni, hedef) {
  const n = KAYNAK.split(eski).length - 1;
  if (n !== 1) { ol(etiket + " capa " + n + " kez", false); return; }
  const k = kosulKos(veriKur(KAYNAK.replace(eski, yeni)));
  ol(etiket + " -> KIRMIZI [" + k.join(",") + "]", k.join(",") === hedef.join(","), "hedef=" + hedef.join(","));
}
kosulMutant("M-KOSUL1 kosul denetimi silindi (her alan zorunlu)",
  "      if (!VERI.alanAktif(form, a, p)) {\n        if (Object.prototype.hasOwnProperty.call(p, a)) { return { ok: false, hata: \"sema-disi-parametre\" }; }\n        continue;\n      }\n",
  "", ["KS1", "KS2", "KS5", "KS6", "KS7", "KS8"]);
kosulMutant("M-KOSUL2 kosul degeri bakilmaz (yalniz alan varligi)",
  " ||\n          c.degerler.indexOf(p[c.alan]) < 0) { return false; }", ") { return false; }", ["KS1", "KS2", "KS5", "KS6", "KS7", "KS8"]);
kosulMutant("M-KOSUL3 gonderilen kosulsuz alan sessizce yutulur",
  "        if (Object.prototype.hasOwnProperty.call(p, a)) { return { ok: false, hata: \"sema-disi-parametre\" }; }\n", "", ["KS2", "KS5"]);
kosulMutant("M-ADIM1 tolerans 1e-9 (enlem kayan nokta)", "Math.abs(k - Math.round(k)) > 1e-6", "Math.abs(k - Math.round(k)) > 1e-9", ["KS1"]);
kosulMutant("M-ADIM2 tolerans 0.5 (izgara disi kabul)", "Math.abs(k - Math.round(k)) > 1e-6", "Math.abs(k - Math.round(k)) > 0.5", ["KS7", "KS8"]);

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