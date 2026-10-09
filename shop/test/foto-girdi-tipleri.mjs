#!/usr/bin/env node
/**
 * PRUVO shop — PARAMETRE/GİRDİ TİPLERİ kabul kapısı (VERI.parametreDogrula — istemci foto-uretim.js ve
 * sunucu shop/src/foto.js girdiGovdeDogrula AYNI FONKSİYONU çağırır).
 *
 *   node shop/test/foto-girdi-tipleri.mjs
 *
 * K3c (sayfa-3adim, 9 Eki 2026): K3a ses/konum/tarih türlerini ve parametreDogrula dallarını sildi → bu
 * kapının S/K/T/TS vakaları ve M-SES/M-KON/M-TRH/M-SAAT mutantları ölü koda bakıyordu (dosya TypeError ile
 * düşüyordu); SİLİNDİ. Yerine METİN dalı (anahtarlık `satirlar`: liste, 1..satir_max satır, ≤ max karakter).
 *
 * Test fikstürü: KENDİ sahte türlerini tanımlar (manifest DEĞİŞMEZ); her türde tek form alanı vardır,
 * böylece "bu alan için bu parametre" izole doğrulanır. Gerçek manifest satırları ayrıca ölçülür.
 *
 * OLCULEN KURALLAR:
 *   G  GIRDI_TURLERI.metin `acik:true` · FORM_TIPLERI.metin true · anahtarlık girdisi ["metin"]
 *   MT metin (liste:true, satir_max 3, max 40, zorunlu):
 *      ✓ 1 / 2 / 3 satır · 40 karakter
 *      ✗ 4 satır · 41 karakter · boş dizi · boşluk öğe · alan yok · kontrol karakteri (BEL, \n, U+202E)
 *        · dizi değil ("Ay") · öğe sayı
 *      zorunlu:false → [] / yok kabul (çıktıya GİRMEZ) · liste değil → tek dize aynı kurallar
 *      şema bozuk (max yok · satir_max yok · liste dize) → HER değer RED
 *      bilinmeyen tip → parametre-yakinda · şema dışı anahtar → sema-disi-parametre
 *   B  bool: YALNIZ true/false
 *   KS koşullu alan + adım ızgarası
 *
 * MUTANTLAR (geçici bellek kopyasına uygulanır, çalışma ağacına YAZMAZ; her biri "uygulandı mı" denetimli,
 * hedef KIRMIZI kümesi TAM eşleşmeli — fazlası da eksiği de KIRMIZI):
 *   M-MET1 satir_max denetimi silindi · M-MET2 FORM_TIPLERI denetimi gevşetildi (bilinmeyen tip kabul)
 *   M-MET3 kontrol karakteri denetimi silindi · M-MET4 trim denetimi silindi · M-MET5 max denetimi silindi
 *   M-MET6 dizi denetimi silindi · M-MET7 FORM_TIPLERI'nden metin düştü · M-SOZ1 köprü sözlüğünde bilinmeyen
 *   tip --denetle'den geçer (tools/kopru-manifest-uret.py kopyası) · M-BOOL1/2 · M-KOSUL1-3 · M-ADIM1/2
 *   M0 kontrol: yalnız yorum → KIRMIZI []
 *
 * CIKIS: 0 yeşil · 1 kırmızı.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";
import { spawnSync } from "node:child_process";

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
  fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
  form, girdi: []
});
let sayac = 0;
const turEkle = (v, form) => { const t = sahteTur("t" + (sayac++), form); v.turler.push(t); return t.kod; };

const KAYNAK = fs.readFileSync(path.join(KOK, "foto-uretim-veri.js"), "utf8");
const VERI = veriKur(KAYNAK);

// ------------------------------------------------------------- G: girdi/form tipleri
console.log("G) GIRDI_TURLERI.metin + FORM_TIPLERI.metin");
ol("G1 GIRDI_TURLERI.metin.acik === true", !!VERI.GIRDI_TURLERI.metin && VERI.GIRDI_TURLERI.metin.acik === true,
   JSON.stringify(VERI.GIRDI_TURLERI));
ol("G2 FORM_TIPLERI.metin === true", VERI.FORM_TIPLERI.metin === true, JSON.stringify(VERI.FORM_TIPLERI));
const an = VERI.turBul("anahtarlik");
ol("G3 manifest anahtarlik girdi [\"metin\"] + satirlar {metin, liste, satir_max 3, max 40, zorunlu}",
   !!an && JSON.stringify(an.girdi) === '["metin"]' && an.form.satirlar.tip === "metin" && an.form.satirlar.liste === true &&
   an.form.satirlar.satir_max === 3 && an.form.satirlar.max === 40 && an.form.satirlar.zorunlu === true,
   JSON.stringify(an && an.form.satirlar));

// ------------------------------------------------------------- MT: metin vakaları
// Her vaka: [kimlik, form-alanı-şeması, gönderilen parametreler (alan anahtarı "a"), beklenen]
// beklenen: { ok:true, deger:<a'nın çıktısı | undefined = çıktıda yok> } | { ok:false, hata }
const LISTE = { tip: "metin", etiket: "Yazı", liste: true, satir_max: 3, max: 40, zorunlu: true };
const TEK = { tip: "metin", etiket: "Yazı", max: 10, zorunlu: true };
const SECIK = { tip: "metin", etiket: "Yazı", liste: true, satir_max: 3, max: 40, zorunlu: false };
const RED = { ok: false, hata: "parametre-metin" };
const MT_VAKA = [
  ["MT1", "1 satır ✓", LISTE, { a: ["Ayşe"] }, { ok: true, deger: ["Ayşe"] }],
  ["MT2", "2 satır ✓", LISTE, { a: ["Ayşe", "Ali"] }, { ok: true, deger: ["Ayşe", "Ali"] }],
  ["MT3", "3 satır ✓", LISTE, { a: ["a", "b", "c"] }, { ok: true, deger: ["a", "b", "c"] }],
  ["MT3b", "40 karakter ✓", LISTE, { a: ["x".repeat(40)] }, { ok: true, deger: ["x".repeat(40)] }],
  ["MT4", "4 satır ✗", LISTE, { a: ["a", "b", "c", "d"] }, RED],
  ["MT5", "41 karakter ✗", LISTE, { a: ["x".repeat(41)] }, RED],
  ["MT6", "boş dizi ✗", LISTE, { a: [] }, RED],
  ["MT6b", "boşluk öğe ✗", LISTE, { a: ["Ayşe", "   "] }, RED],
  ["MT6c", "alan yok (zorunlu) ✗", LISTE, {}, RED],
  ["MT7", "kontrol BEL ✗", LISTE, { a: ["a\u0007b"] }, RED],
  ["MT7b", "satır sonu öğede ✗", LISTE, { a: ["a\nb"] }, RED],
  ["MT7c", "yön geçersiz kılma U+202E ✗", LISTE, { a: ["a‮b"] }, RED],
  ["MT8", "dizi değil (\"Ay\") ✗", LISTE, { a: "Ay" }, RED],
  ["MT8b", "öğe sayı ✗", LISTE, { a: [5] }, RED],
  ["MT9", "zorunlu:false [] → kabul, çıktıda yok", SECIK, { a: [] }, { ok: true, deger: undefined }],
  ["MT9b", "zorunlu:false alan yok → kabul", SECIK, {}, { ok: true, deger: undefined }],
  ["MT9c", "zorunlu:false dolu → kurallar", SECIK, { a: ["x".repeat(41)] }, RED],
  ["MT10", "liste değil: tek dize ✓", TEK, { a: "PRUVO" }, { ok: true, deger: "PRUVO" }],
  ["MT10b", "liste değil: dizi ✗", TEK, { a: ["PRUVO"] }, RED],
  ["MT10c", "liste değil: 11 karakter ✗", TEK, { a: "x".repeat(11) }, RED],
  ["MT10d", "liste değil: satır sonu ✗", TEK, { a: "a\nb" }, RED],
  ["MT11", "şema max yok → RED", { tip: "metin", liste: true, satir_max: 3, zorunlu: true }, { a: ["a"] }, RED],
  ["MT11b", "şema satir_max yok → RED", { tip: "metin", liste: true, max: 40, zorunlu: true }, { a: ["a"] }, RED],
  ["MT11c", "şema liste dize → RED", { tip: "metin", liste: "evet", satir_max: 3, max: 40, zorunlu: true }, { a: ["a"] }, RED],
  ["MT12", "bilinmeyen tip → parametre-yakinda", { tip: "renk_liste", uzunluk_max: 4 }, { a: ["#FFFFFF"] },
    { ok: false, hata: "parametre-yakinda" }],
  ["MT13", "şema dışı anahtar → sema-disi-parametre", LISTE, { a: ["a"], b: 1 }, { ok: false, hata: "sema-disi-parametre" }]
];
function metinKos(v) {
  const kotu = [];
  for (const [id, , sema, p, b] of MT_VAKA) {
    const kod = turEkle(v, { a: sema });
    let r;
    try { r = v.parametreDogrula(kod, p); } catch (e) { kotu.push(id); continue; }  // istisna = fail-closed DEĞİL
    const uy = b.ok
      ? r.ok === true && JSON.stringify(r.deger.a) === JSON.stringify(b.deger) && (b.deger !== undefined || !("a" in r.deger))
      : r.ok === false && r.hata === b.hata;
    if (!uy) { kotu.push(id); }
  }
  return kotu;
}
console.log("MT) METİN (liste: 1..satir_max satır, ≤ max karakter, kontrol karakteri yok — FAIL-CLOSED)");
{
  const kotu = metinKos(VERI);
  for (const [id, ad] of MT_VAKA) { ol(id + " " + ad, !kotu.includes(id)); }
  // Çıktı girdinin KOPYASI (sonradan değiştirilen girdi doğrulanmış değeri bozmaz).
  const kod = turEkle(VERI, { a: LISTE });
  const g = ["Ayşe"], r = VERI.parametreDogrula(kod, { a: g });
  g.push("x", "y", "z");
  ol("MT14 çıktı dizisi girdinin kopyası", r.ok && r.deger.a.length === 1, JSON.stringify(r));
  // Gerçek manifest: anahtarlık örnek girdisi (köprü kaydı ornek.girdi) sunucudan geçer.
  const ornek = {};
  for (const [a, s] of Object.entries(an.form)) { ornek[a] = s.ornek !== undefined ? s.ornek : s.varsayilan; }
  const ro = VERI.parametreDogrula("anahtarlik", ornek);
  ol("MT15 manifest anahtarlik örnek parametreleri → ok", ro.ok === true, JSON.stringify(ro));
  const r4 = VERI.parametreDogrula("anahtarlik", { ...ornek, satirlar: ["a", "b", "c", "d"] });
  ol("MT16 manifest anahtarlik 4 satır → parametre-metin", r4.ok === false && r4.hata === "parametre-metin", JSON.stringify(r4));
}

// ------------------------------------------------------------- B: bool
console.log("B) BOOL (kopru-15 sözlük: YALNIZ true/false; dize/sayı/null RED)");
{
  ol("B0 FORM_TIPLERI.bool === true", VERI.FORM_TIPLERI.bool === true, JSON.stringify(VERI.FORM_TIPLERI));
  const kod = turEkle(VERI, { alan: { tip: "bool", etiket: "Kapak", varsayilan: false } });
  const d = (v) => VERI.parametreDogrula(kod, { alan: v });
  ol("B1 true ✓ (deger true)", d(true).ok === true && d(true).deger.alan === true, JSON.stringify(d(true)));
  ol("B2 false ✓ (deger false)", d(false).ok === true && d(false).deger.alan === false, JSON.stringify(d(false)));
  for (const [ad, v] of [["B3 \"true\"", "true"], ["B4 \"1\"", "1"], ["B5 1", 1], ["B6 0", 0], ["B7 null", null], ["B8 \"false\"", "false"]]) {
    ol(ad + " ✗ parametre-bool", d(v).ok === false && d(v).hata === "parametre-bool", JSON.stringify(d(v)));
  }
  ol("B9 alan yok ✗ parametre-bool", VERI.parametreDogrula(kod, {}).hata === "parametre-bool", JSON.stringify(VERI.parametreDogrula(kod, {})));
  const bt = VERI.turBul("bust");
  ol("B10 bust.ters tip bool", !!bt && bt.form.ters && bt.form.ters.tip === "bool", JSON.stringify(bt && bt.form.ters));
}

// ------------------------------------------------------------- KS: koşul + adım
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
  const kod = turEkle(v, KOSUL_FORM);
  const k = [];
  for (const [ad, p, b] of KOSUL_VAKA) {
    const r = v.parametreDogrula(kod, p);
    const uy = b.ok ? (r.ok === true && Object.keys(r.deger).sort().join(",") === b.anahtar) : (r.ok === false && r.hata === b.hata);
    if (!uy) { k.push(ad.split(" ")[0]); }
  }
  return k;
}
console.log("KS) KOSUL + ADIM (kopru-15 DILIM-2)");
{
  const k = kosulKos(VERI);
  for (const [ad] of KOSUL_VAKA) { ol(ad, !k.includes(ad.split(" ")[0])); }
  // Gerçek manifest: köprü yapboz örnek parametreleri (kayıt ornek.girdi) GEÇERLİ.
  const yp = { uzun_kenar_mm: 150, satir: 3, sutun: 4, tohum: 1, kabartma_yon: "acik_yuksek" };
  const r = VERI.parametreDogrula("yapboz", yp);
  ol("KS9 manifest yapboz köprü örneği -> ok", r.ok === true, JSON.stringify(r));
}

// ---------------------------------------------------------------- MUTANTLAR
console.log("MUTANTLAR (geçici bellek kopyası; çalışma ağacına YAZMAZ)");
// Mutant: çapa kaynakta TAM 1 kez olmalı (uygulandı mı), sonra koşucunun KIRMIZI kümesi hedefe TAM eşit olmalı.
function mutant(etiket, eski, yeni, kos, hedef) {
  const n = KAYNAK.split(eski).length - 1;
  if (n !== 1) { ol(etiket + " MUTANT_UYGULANMADI capa " + n + " kez", false); return; }
  const k = kos(veriKur(KAYNAK.replace(eski, yeni)));
  ol(etiket + " -> KIRMIZI [" + k.join(",") + "]", k.join(",") === hedef.join(","), "hedef=" + hedef.join(","));
}
mutant("M-MET1 satir_max denetimi silindi", "if (v.length < 1 || v.length > sema.satir_max)", "if (v.length < 1)",
  metinKos, ["MT4"]);
mutant("M-MET2 FORM_TIPLERI denetimi gevşetildi (bilinmeyen tip kabul)",
  "      if (VERI.FORM_TIPLERI[sema.tip] !== true) { return { ok: false, hata: \"parametre-yakinda\" }; }\n", "",
  metinKos, ["MT12"]);
mutant("M-MET3 kontrol karakteri denetimi silindi", " && !METIN_KONTROL.test(x)", "", metinKos, ["MT7", "MT7b", "MT7c", "MT10d"]);
mutant("M-MET4 trim denetimi silindi", "x.trim().length > 0", "x.length > 0", metinKos, ["MT6b"]);
mutant("M-MET5 max denetimi silindi", " && x.length <= max", "", metinKos, ["MT5", "MT9c", "MT10c"]);
mutant("M-MET6 dizi denetimi silindi", " || !Array.isArray(v)) { return", ") { return", metinKos, ["MT6c", "MT8"]);
mutant("M-MET7 FORM_TIPLERI'nden metin düştü", "secim: true, metin: true, bool: true", "secim: true, bool: true",
  // metin tipi hiç tanınmaz -> HER metin vakası parametre-yakinda (RED vakaları da beklenen hata kodunu kaybeder);
  // yalnız bilinmeyen tip (MT12) ve şema dışı anahtar (MT13, tip denetiminden ÖNCE) etkilenmez.
  metinKos, MT_VAKA.map((x) => x[0]).filter((id) => id !== "MT12" && id !== "MT13"));
mutant("M-BOOL1 bool true/false denetimi silindi",
  "        if (v !== true && v !== false) { return { ok: false, hata: \"parametre-bool\" }; }\n", "",
  (v) => {
    const kod = turEkle(v, { alan: { tip: "bool" } });
    return [["B3", "true"], ["B5", 1], ["B7", null], ["B1", true], ["B2", false]]
      .filter(([, x]) => (v.parametreDogrula(kod, { alan: x }).ok === true) !== (x === true || x === false)).map(([id]) => id);
  }, ["B3", "B5", "B7"]);
mutant("M-BOOL2 FORM_TIPLERI'nden bool düştü", "metin: true, bool: true };", "metin: true };",
  (v) => { const kod = turEkle(v, { alan: { tip: "bool" } }); return v.parametreDogrula(kod, { alan: true }).ok ? [] : ["B1"]; }, ["B1"]);
mutant("M-KOSUL1 kosul denetimi silindi (her alan zorunlu)",
  "      if (!VERI.alanAktif(form, a, p)) {\n        if (Object.prototype.hasOwnProperty.call(p, a)) { return { ok: false, hata: \"sema-disi-parametre\" }; }\n        continue;\n      }\n",
  "", kosulKos, ["KS1", "KS2", "KS5", "KS6", "KS7", "KS8"]);
mutant("M-KOSUL2 kosul degeri bakilmaz (yalniz alan varligi)",
  " ||\n          c.degerler.indexOf(p[c.alan]) < 0) { return false; }", ") { return false; }", kosulKos, ["KS1", "KS2", "KS5", "KS6", "KS7", "KS8"]);
mutant("M-KOSUL3 gonderilen kosulsuz alan sessizce yutulur",
  "        if (Object.prototype.hasOwnProperty.call(p, a)) { return { ok: false, hata: \"sema-disi-parametre\" }; }\n", "", kosulKos, ["KS2", "KS5"]);
mutant("M-ADIM1 tolerans 1e-9 (enlem kayan nokta)", "Math.abs(k - Math.round(k)) > 1e-6", "Math.abs(k - Math.round(k)) > 1e-9", kosulKos, ["KS1"]);
mutant("M-ADIM2 tolerans 0.5 (izgara disi kabul)", "Math.abs(k - Math.round(k)) > 1e-6", "Math.abs(k - Math.round(k)) > 0.5", kosulKos, ["KS7", "KS8"]);
mutant("M0 KONTROL (yalnız yorum)", "  VERI.parametreDogrula = function (kod, p) {", "  // kontrol\n  VERI.parametreDogrula = function (kod, p) {",
  (v) => metinKos(v).concat(kosulKos(v)), []);

// M-SOZ1: köprü sözlüğü (tools/kopru-manifest-uret.py) bilinmeyen tipi --denetle'de adıyla KIRMIZI yakar; araç
// kopyasında tip denetimi silinirse bu satır kaybolmalı (geçici dizin; finally'de silinir).
{
  const ARAC = path.join(KOK, "tools", "kopru-manifest-uret.py");
  const CAPA = "    if tip not in BILINEN_TIP:\n";
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "girdi-tipleri-soz-"));
  try {
    const kayit = path.join(d, "kayit.json");
    fs.writeFileSync(kayit, JSON.stringify({ kayitlar: [{ kod: "x", uretec: "x_uret", girdi_tipi: ["foto"],
      parametreler: [{ ad: "a", tip: "renk_dizi" }], olcek: { min_mm: 10, max_mm: 100, adim_mm: 10 } }] }));
    const kos = (arac) => {
      const p = spawnSync("python3", [arac, "--denetle", "--kayit", kayit, "--manifest", path.join(KOK, "foto-uretim-veri.js")],
        { encoding: "utf8" });
      return { rc: p.status, yakti: /^KIRMIZI bilinmeyen-tip:x\.a=renk_dizi$/m.test(p.stdout || "") };
    };
    const asil = kos(ARAC);
    ol("SOZ0 sözlükte olmayan tip --denetle'de KIRMIZI (bilinmeyen-tip:x.a=renk_dizi, rc 1)", asil.rc === 1 && asil.yakti, JSON.stringify(asil));
    const kaynak = fs.readFileSync(ARAC, "utf8");
    const n = kaynak.split(CAPA).length - 1;
    if (n !== 1) {
      ol("M-SOZ1 MUTANT_UYGULANMADI capa " + n + " kez", false);
    } else {
      const mut = path.join(d, "arac.py");
      fs.writeFileSync(mut, kaynak.replace(CAPA, "    if False:\n"));
      const m = kos(mut);
      ol("M-SOZ1 sözlük tip denetimi silindi -> bilinmeyen-tip satırı KAYBOLUR (SOZ0 KIRMIZI)", m.yakti === false, JSON.stringify(m));
    }
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------- SONUC
console.log("\n" + (kirmizi === 0 ? "✅ HEPSI GECTI · SURVIVOR=0" : "❌ KIRMIZI=" + kirmizi));
process.exit(kirmizi === 0 ? 0 : 1);
