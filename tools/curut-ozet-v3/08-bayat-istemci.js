#!/usr/bin/env node
/**
 * CURUTME 08 — EKSEN 8: "bos kart 0, fiyat/beyan sapmasi 0, 223 kapak yer tutucuya duser"
 * iddiasi BAGIMSIZ olarak yeniden uretilir — ve iddianin EKSIK biraktigi kalem aranir.
 *
 * Yontem: GERCEK katalog + GERCEK build.py (v2 ve v3) + 11 Agu BAYAT cozucusu (dondurulmus
 * kopya, kabul testindekiyle AYNI yuklem) + CANLI cozucu. Sayilar burada TEKRAR uretilir,
 * kabul testinin ciktisindan KOPYALANMAZ.
 *
 * Ek eksen (iddiada YOK): index.html `edgeHavuz()` ana vitrin beslemesini
 * `bloklar + parametrik + OZET.yeni` olarak kurar ve `edgeYedek()` (Worker'a ulasilamazsa
 * calisan yedek ARAMA havuzu) AYNI havuzu kullanir. Bayat istemci v3'te `yeni` anahtarini
 * GORMEZ -> kuyruk BOSALIR. Bu kaybin TEKILLESTIRILMIS (havuzlarda zaten olmayan) buyuklugu
 * asagida sayilir.
 */
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const KOK = path.dirname(path.dirname(__dirname));
const BUILD = path.join(KOK, "tools", "build.py");
const ozetAcCanli = require(path.join(KOK, "tools", "ozet-ac-ayikla.js")).ozetAcAl();
const GEC = fs.mkdtempSync(path.join(os.tmpdir(), "curut-bayat-"));
const KATALOG = path.join(KOK, "urunler.json");

/* 11 Agu 2026 index.html `ozetAc` (v2 cozucusu) — DONDURULMUS. */
function bayatAc(d) {
  var alanlar = (d && d.kartAlanlari) || [];
  if (!alanlar.length) { return d; }
  function kartAc(k) {
    if (Object.prototype.toString.call(k) !== "[object Array]") { return k; }
    var out = {};
    k.forEach(function (deger, i) {
      if (i < alanlar.length && (i < 8 || deger !== null)) { out[alanlar[i]] = deger; }
    });
    return out;
  }
  d.parametrik = (d.parametrik || []).map(kartAc);
  Object.keys(d.bloklar || {}).forEach(function (kat) {
    d.bloklar[kat] = (d.bloklar[kat] || []).map(kartAc);
  });
  d.yeni = (d.yeni || []).map(kartAc);
  return d;
}

function uret(surum) {
  const cik = path.join(GEC, "ozet-v" + surum + ".json");
  const r = spawnSync("python3", [BUILD, "--sadece-ozet", "--katalog", KATALOG,
    "--cikti", cik, "--ozet-surum", String(surum)], { encoding: "utf8" });
  if (r.status !== 0) { throw new Error("build rc=" + r.status); }
  const ham = fs.readFileSync(cik, "utf8");
  return { ham, bayt: Buffer.byteLength(ham, "utf8") };
}

const urunler = JSON.parse(fs.readFileSync(KATALOG, "utf8"));
const kaynakById = new Map(urunler.map((p) => [p.id, p]));

const v2 = uret(2);
const v3 = uret(3);
console.log("=== CURUTME 08 — bayat istemci penceresi (bagimsiz yeniden uretim)\n");
console.log("katalog %d urun | v2 %d B | v3 %d B | kazanc %d B (%%%s)",
  urunler.length, v2.bayt, v3.bayt, v2.bayt - v3.bayt,
  (100 * (v2.bayt - v3.bayt) / v2.bayt).toFixed(1));

function kartlar(a) {
  return []
    .concat(a.parametrik || [])
    .concat(Object.keys(a.bloklar || {}).reduce((t, k) => t.concat(a.bloklar[k]), []))
    .concat(a.yeni || []);
}

function olc(etiket, acik) {
  const ks = kartlar(acik);
  const bos = ks.filter((k) => !k || typeof k !== "object" || !k.id).length;
  const kisaKapak = ks.filter((k) => k && typeof k.gorsel === "string" && k.gorsel
    && k.gorsel.indexOf("://") === -1).length;
  const sapan = ks.filter((k) => {
    const p = kaynakById.get(k && k.id);
    if (!p) { return true; }
    const bekFiyat = p.fiyat || "";
    const bekTur = p.tur === "fiziksel" ? "fiziksel" : "";
    const bekTf = p.tavsiyeFilament || "";
    return (k.fiyat || "") !== bekFiyat || (k.tur || "") !== bekTur
      || (k.tavsiyeFilament || "") !== bekTf
      || JSON.stringify(k.konfigur || null) !== JSON.stringify(p.konfigur || null);
  }).length;
  console.log("  " + etiket.padEnd(30) + " toplam kart " + ks.length
    + " | bos kart " + bos + " | fiyat/beyan sapmasi " + sapan
    + " | kapagi KISA kalan " + kisaKapak
    + " | `yeni` kuyrugu " + (acik.yeni || []).length);
  return { ks, bos, sapan, kisaKapak, yeni: (acik.yeni || []).length };
}

const tazeV3 = olc("TAZE istemci + v3", ozetAcCanli(JSON.parse(v3.ham)));
const tazeV2 = olc("TAZE istemci + v2", ozetAcCanli(JSON.parse(v2.ham)));
const bayatV2 = olc("BAYAT (11 Agu) istemci + v2", bayatAc(JSON.parse(v2.ham)));
const bayatV3 = olc("BAYAT (11 Agu) istemci + v3", bayatAc(JSON.parse(v3.ham)));

console.log("\nIDDIA KONTROLU (build.py yorumu + paket FAZ 2b):");
console.log("  'bos kart cizmez'            -> bayat+v3 bos kart = %d  %s",
  bayatV3.bos, bayatV3.bos === 0 ? "✔ DOGRU" : "✘ YANLIS");
console.log("  'fiyat/beyan bozulmaz'       -> bayat+v3 sapma   = %d  %s",
  bayatV3.sapan, bayatV3.sapan === 0 ? "✔ DOGRU" : "✘ YANLIS");
console.log("  '223 kartin kapagi duser'    -> olculen          = %d  %s",
  bayatV3.kisaKapak, bayatV3.kisaKapak === 223 ? "✔ TUTUYOR"
    : "⚠ SAPMA (iddia 223, olculen " + bayatV3.kisaKapak + ")");

// --- IDDIADA YOK: `yeni` kuyrugunun tamamen kaybi
const havuzIdV3 = new Set([]
  .concat(bayatV3.ks.filter((k) => k && k.id).map((k) => k.id)));
const yeniIdler = (bayatAc(JSON.parse(v2.ham)).yeni || []).map((k) => k.id);
const tekilKayip = yeniIdler.filter((id) => !havuzIdV3.has(id));
console.log("\nIDDIADA GECMEYEN KALEM — bayat istemcide `yeni` kuyrugu:");
console.log("  bayat+v2 `yeni` = %d kart · bayat+v3 `yeni` = %d kart (TAMAMEN BOSALIYOR)",
  bayatV2.yeni, bayatV3.yeni);
console.log("  bu kartlarin %d tanesi bloklar/parametrik havuzlarinda DA YOK -> "
  + "ana vitrin beslemesinden (edgeHavuz) ve Worker'siz YEDEK ARAMA havuzundan "
  + "(edgeYedek) TEKIL olarak duser", tekilKayip.length);
console.log("  ornek dusen id: %s", tekilKayip.slice(0, 3).join(", ") || "(yok)");
// DRIFT EKSENI: bugun kayip 0 cikiyorsa bunun SEBEBI, en yeni 48 urunun HEPSININ havuzlu
// kategoride (Marin/Otomobil/parametrik) olmasidir. Yarin havuzsuz bir kategoriye dusen
// yeni urun, bayat istemcide TEKIL kayba doner. Bugunku dagilimi say.
const havuzluKat = new Set(["Marin", "Otomobil", "Jeneratör"]);
const enYeni48 = urunler.slice(0, 48);
const havuzsuz = enYeni48.filter((p) => !havuzluKat.has(p.kategori || "")
  && !p.parametrik);
console.log("  DRIFT: en yeni 48 urunun %d tanesi HAVUZSUZ kategoride (bugun) -> "
  + "bu sayi >0 oldugu gun bayat istemcinin TEKIL kaybi da >0 olur", havuzsuz.length);
console.log("  en yeni 48'in kategori dagilimi: %j",
  enYeni48.reduce((t, p) => { t[p.kategori] = (t[p.kategori] || 0) + 1; return t; }, {}));
console.log("  toplam cizilebilir kart: bayat+v2 %d -> bayat+v3 %d (fark %d)",
  bayatV2.ks.length, bayatV3.ks.length, bayatV2.ks.length - bayatV3.ks.length);

fs.rmSync(GEC, { recursive: true, force: true });
