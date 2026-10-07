#!/usr/bin/env node
/**
 * FOTO FIYAT — TEK FORMUL kabul testi (Okan 7 Eki 15:4x: "fiyat bu ürünlerin tamamında aynı per cm/100tl
 * fiyatlistesi yazmayın ... hangisi uzunsa ona göre belirlenir"). PARA sinifi: hata SESSIZ olur (yanlis
 * formul canliya cikarsa siparis normal akar, fiyat yanlis tahsil edilir). Eski tablo ureteci
 * (tools/foto-fiyat-uret.py + testi) EMEKLI: fiyat tablosu yok, formul foto-uretim-veri.js VERI.fiyatKurus.
 *
 *   node shop/test/foto-fiyat-formul.mjs
 *
 *   F1 FORMUL      : manifestteki HER kategori × 3 olcu (en_az · orta · en_cok) -> fiyat_kurus = mm × 1000
 *                    (kategori farki YOK); sayi manifestten (uydurma yok), tablo stdout'a basilir
 *   F2 RED         : aralik disi (en_az − adim, en_cok + adim), adim disi, tam sayi olmayan olcu -> null;
 *                    bilinmeyen formul adi -> null (tur fiyatsiz kalir, sunulmaz)
 *   F3 BASLANGIC   : "₺N'dan itibaren" = en_az formulu (sürgünün ilk duragi = en_az)
 *   F4 TEK KAYNAK  : sunucu (shop/src/foto.js acikTurler) her olcuyu VERI.fiyatKurus ile ayni tutarda verir;
 *                    istemci (foto-uretim.js) fiyati F.fiyatKurus/F.fiyatSatiri'dan alir, kendi katsayisi YOK;
 *                    `foto_fiyat` tablo atfi shop/src/*.js + foto-uretim*.js'te 0
 *   F5 ANAHTAR     : acilis anahtari okunamaz / bos -> acik tur 0 (fail-closed)
 * MUTANTLAR (veri dosyasinin BELLEKTEKI kopyasi / foto.js'in GECICI kopyasi; agaca yazim YOK):
 *   FM1 formul ×100 · FM2 en_az yerine en_cok · FM3 adim izgarasi silindi · FM4 anahtar fail-open
 *   -> hedef grup KIRMIZI; FM0 (yalniz yorum) -> hicbiri. Olcu EKSENI (X/Y'ye bakan olcum) mutanti
 *   shop/test/foto-uretim.mjs OZ-M1'de (sentetik 3MF orada).
 * CIKIS: 0 yesil · 1 kirmizi. Son satir `SURVIVOR=<n>`.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const SHOP = path.join(KOK, "shop");
const VERI_YOL = path.join(KOK, "foto-uretim-veri.js");
const VERI_KAYNAK = fs.readFileSync(VERI_YOL, "utf8");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

/** Veri dosyasini (ya da mutantini) ayri vm baglaminda yukler. */
function veriYukle(kaynak) {
  const k = {};
  vm.runInNewContext(kaynak, k, { filename: "foto-uretim-veri.js" });
  return k.PRUVO_FOTO;
}

/** Formul senaryolari: V = veri nesnesi. Donus {F1, F2, F3, sayi, tablo}. */
function formulSenaryolar(V) {
  const s = { F1: true, F2: true, F3: true, sayi: 0, gecen: 0, tablo: [] };
  for (const t of V.turler) {
    const a = t.olcu_mm || {};
    const sec = V.olcuSecenekleri(t.kod);
    const orta = sec.length ? sec[Math.floor((sec.length - 1) / 2)] : null;
    const satir = { kod: t.kod, olculer: [] };
    for (const mm of [a.en_az, orta, a.en_cok]) {
      s.sayi++;
      const k = V.fiyatKurus(t.kod, mm);
      const dogru = Number.isInteger(mm) && k === mm * 1000;
      if (dogru) { s.gecen++; } else { s.F1 = false; }
      satir.olculer.push({ mm, kurus: k, metin: V.fiyatSatiri(t.kod, mm), dogru });
    }
    s.tablo.push(satir);
    const adim = (t.fiyat || {}).adim_mm;
    const disarida = [a.en_az - adim, a.en_cok + adim, a.en_az + 0.5].concat(adim > 1 ? [a.en_az + 1] : []);
    if (disarida.some((mm) => V.fiyatKurus(t.kod, mm) !== null)) { s.F2 = false; }
    // Baslangic fiyati: sürgünün ilk duragi en_az, fiyati en_az × 1000.
    if (sec[0] !== a.en_az || V.fiyatKurus(t.kod, sec[0]) !== a.en_az * 1000) { s.F3 = false; }
  }
  if (s.sayi === 0) { s.F1 = false; }
  return s;
}

console.log("F1-F3) TEK FORMUL — fiyat_kurus = en uzun boyut (mm) × 1000, kategori farki YOK");
const VERI = veriYukle(VERI_KAYNAK);
const fs1 = formulSenaryolar(VERI);
const kategori = VERI.turler.length;
for (const t of fs1.tablo) {
  console.log("     " + t.kod.padEnd(8) + " " + t.olculer.map((o) => (o.metin || (o.mm + " mm → ?")) + (o.dogru ? "" : " ✗")).join(" · "));
}
ol("F1 formul " + fs1.gecen + "/" + fs1.sayi + " (manifestte " + kategori + " kategori × 3 olcu)", fs1.F1 && fs1.gecen === kategori * 3, "");
ol("F2 aralik disi / adim disi / kesirli olcu -> fiyat YOK (null)", fs1.F2, "");
ol("F3 baslangic fiyati (₺N'dan itibaren) = en_az formulu, sürgü ilk duragi en_az", fs1.F3, "");
{
  const bilinmeyen = veriYukle(VERI_KAYNAK.replace('fiyat: { formul: "mm_x_10tl", adim_mm: 10 },\n        // Okan kararı 7 Eki 2026: plaket',
    'fiyat: { formul: "mm_x_99tl", adim_mm: 10 },\n        // Okan kararı 7 Eki 2026: plaket'));
  ol("F2b bilinmeyen formul adi -> fiyat null (plaket sunulmaz), diger turler etkilenmez",
     bilinmeyen.fiyatKurus("plaket", 120) === null && bilinmeyen.fiyatKurus("litofan", 120) === 120000, "");
  ol("F2c TR bicim: 120 mm → 1.200 TL · 1234567 kurus → 12.345,67 TL",
     VERI.fiyatSatiri("plaket", 120) === "120 mm → 1.200 TL" && VERI.tlMetni(1234567) === "12.345,67 TL", VERI.fiyatSatiri("plaket", 120));
}

console.log("F4) TEK KAYNAK — sunucu = istemci = VERI.fiyatKurus; tablo atfi 0");
const foto = await import(url.pathToFileURL(path.join(SHOP, "src", "foto.js")).href);
async function sunucuSenaryo(fm) {
  const hepsi = new Set(globalThis.PRUVO_FOTO.turler.map((t) => t.kod));
  const turler = fm.acikTurler(hepsi);
  let n = 0, ayni = 0;
  for (const t of turler) {
    for (const o of t.olculer) { n++; if (o.fiyat_kurus === VERI.fiyatKurus(t.kod, o.mm) && o.fiyat_kurus === o.mm * 1000) { ayni++; } }
  }
  const okunamaz = await fm.acikAnahtari({ KATALOG: { prepare() { throw new Error("D1_ERROR: no such table: foto_acik"); } } });
  const bos = await fm.acikAnahtari({ KATALOG: { prepare() { return { all: async () => ({ results: [] }) }; } } });
  return { SUNUCU: turler.length > 0 && n > 0 && n === ayni, n, ayni, turSayisi: turler.length,
           ANAHTAR: okunamaz.size === 0 && bos.size === 0 && fm.acikTurler(okunamaz).length === 0 && fm.acikTurler(bos).length === 0 };
}
const ss = await sunucuSenaryo(foto);
ol("F4a sunucu acikTurler: " + ss.ayni + "/" + ss.n + " olcu fiyati VERI.fiyatKurus ile AYNI (" + ss.turSayisi + " tur)", ss.SUNUCU, JSON.stringify(ss));
const ISTEMCI = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
ol("F4b istemci fiyati TEK formulden: F.fiyatSatiri (sürgü) + F.fiyatKurus (toplam, vitrin); kendi katsayisi yok",
   /F\.fiyatSatiri\(nt\.kod/.test(ISTEMCI) && /F\.fiyatKurus\(nt\.kod, S\.olcu\)/.test(ISTEMCI) &&
   /F\.fiyatKurus\(t\.kod, t\.olcu_mm\.en_az\)/.test(ISTEMCI) && !/VITRIN_TL_MM|fiyat_kurus/.test(ISTEMCI), "");
const tabloAtfi = [...fs.readdirSync(path.join(SHOP, "src")).filter((d) => d.endsWith(".js")).map((d) => path.join(SHOP, "src", d)),
  path.join(KOK, "foto-uretim.js"), VERI_YOL].map((y) => ({ y: path.relative(KOK, y), n: (fs.readFileSync(y, "utf8").match(/foto_fiyat/g) || []).length }))
  .filter((x) => x.n > 0);
ol("F4c `foto_fiyat` tablo atfi shop/src/*.js + foto-uretim*.js'te 0", tabloAtfi.length === 0, JSON.stringify(tabloAtfi));
console.log("F5) ACILIS ANAHTARI — okunamaz / bos -> acik tur 0 (fail-closed)");
ol("F5 anahtar okunamaz ya da bos -> acik tur 0", ss.ANAHTAR, "");

// ================================================================ MUTANTLAR
console.log("MUTANTLAR (bellekteki veri kopyasi / gecici foto.js kopyasi; calisma agacina yazilmaz)");
let survivor = 0;
const VERI_MUTANTLAR = [
  ["FM0 KONTROL (yorum)", "// Formül adı -> mm başına kuruş.", "// Formül  adı -> mm başına kuruş.", []],
  ["FM1 FORMUL ×100", "VERI.FIYAT_FORMULLERI = { mm_x_10tl: 1000 };", "VERI.FIYAT_FORMULLERI = { mm_x_10tl: 100000 };", ["F1", "F3"]],
  ["FM2 EN_AZ YERINE EN_COK", "return { en_az: t.olcu_mm.en_az, en_cok: t.olcu_mm.en_cok };",
   "return { en_az: t.olcu_mm.en_cok, en_cok: t.olcu_mm.en_cok };", ["F1", "F3"]],
  ["FM3 ADIM IZGARASI SILINDI", "return (mm - a.en_az) % adim === 0 || mm === a.en_cok;", "return true;", ["F2"]],
];
for (const [ad, capa, yerine, olmeli] of VERI_MUTANTLAR) {
  if (VERI_KAYNAK.split(capa).length !== 2) { ol(ad + " capa bulundu (tek)", false, capa); continue; }
  const s = formulSenaryolar(veriYukle(VERI_KAYNAK.replace(capa, yerine)));
  const kir = ["F1", "F2", "F3"].filter((x) => s[x] !== true);
  const tam = JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort());
  if (olmeli.length && !kir.length) { survivor++; }
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", tam, JSON.stringify(kir));
}
const GECICI = path.join(SHOP, "foto-fiyat-test-tmp-" + process.pid);
process.on("exit", () => { fs.rmSync(GECICI, { recursive: true, force: true }); });
const FOTO_ASIL = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
const FOTO_MUTANTLAR = [
  ["FM4 ANAHTAR FAIL-OPEN (okunamazsa hepsi acik)", "    return new Set();\n  }\n}",
   "    return new Set(VERI.turler.map((t) => t.kod));\n  }\n}", "ANAHTAR"],
  ["FM5 SUNUCU KENDI KATSAYISI (×100)", ".map((mm) => ({ mm, fiyat_kurus: VERI.fiyatKurus(t.kod, mm) }))",
   ".map((mm) => ({ mm, fiyat_kurus: mm * 100 }))", "SUNUCU"],
];
for (const [ad, capa, yerine, hedef] of FOTO_MUTANTLAR) {
  if (FOTO_ASIL.split(capa).length !== 2) { ol(ad + " capa bulundu (tek)", false, capa); continue; }
  fs.mkdirSync(GECICI, { recursive: true });
  const dosya = path.join(GECICI, "foto-" + hedef + ".js");
  // Goreli import ("../../foto-uretim-veri.js") gecici dizinden de KOK'e cozulsun diye mutlak yola cevrilir.
  fs.writeFileSync(dosya, FOTO_ASIL.replace(capa, yerine).replace('import "../../foto-uretim-veri.js";',
    "import " + JSON.stringify(url.pathToFileURL(VERI_YOL).href) + ";")
    .replace(/from "\.\/([a-z-]+\.js)"/g, (m, d) => "from " + JSON.stringify(url.pathToFileURL(path.join(SHOP, "src", d)).href)));
  const fm = await import(url.pathToFileURL(dosya).href);
  const s = await sunucuSenaryo(fm);
  if (s[hedef] === true) { survivor++; }
  ol(ad + " -> " + hedef + " KIRMIZI", s[hedef] === false, JSON.stringify({ SUNUCU: s.SUNUCU, ANAHTAR: s.ANAHTAR }));
}

console.log((kirmizi ? "❌ KIRMIZI: " + kirmizi : "✅ HEPSI GECTI") + " · SURVIVOR=" + survivor);
console.log("SURVIVOR=" + survivor);
process.exit(kirmizi ? 1 : 0);
