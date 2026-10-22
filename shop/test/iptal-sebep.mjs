#!/usr/bin/env node
/**
 * PRUVO shop — IPTAL SEBEP KODU KABUL KAPISI (22 Eki 2026).
 *
 *   node shop/test/iptal-sebep.mjs
 *
 * OLCUGU HUKUM: panelden iptal edilen siparisin sebebi MAKINE-OKUNUR kod olarak
 * durum_gecmisi'nin `s` alanina yazilir. Sebepsiz iptal 400 'iptal-sebebi-gerekli',
 * kume disi kod 400 'bilinmeyen-iptal-sebebi' — IKISINDE DE D1'E YAZMA 0.
 * Iptal disi hedeflerde `sebep` YOK SAYILIR. Terk süpürmesinin `s:"terk"` izi degismez.
 *
 * NASIL (iki eksen, bilerek ayri):
 *   SUNUCU ekseni : shop/src/yonet.js DOGRUDAN import edilir, GERCEK `yonet()` router'i
 *                   sahte Request/env ile cagrilir (siparis-durum-secici.mjs deseni).
 *                   Olculen sey ucun KENDISIDIR; saf fonksiyonun kopyasi DEGIL.
 *   PANEL ekseni  : sayfa JS'i HAM KAYNAK olarak cekilip vm'de kosturulur
 *                   (siparis-durum-secici.mjs ⑦ deseni). KOPYA YAZILMAZ; `durumDegis`
 *                   DAHAHA sahte `document`/`api` ile GERCEKTEN cagrilir (statik regex
 *                   degil) — "kutu bosken istek gitmez" ancak boyle olculur.
 *
 * 🔴 SEBEP DE DOGRULANIR: 400 gormek YETMEZ. Her negatif iddia KODU + `hata` ALANINI +
 * D1 YAZMA SAYACINI ayri ayri iddia eder; ayrica 5 gecerli sebebin HER BIRI icin izin
 * `s` alani okunur (200 gormek de yetmez — yazilan sey yanlis kod olabilirdi).
 *
 * 🔴 OLCULEN KUME SUNUCUNUN KENDISINDEN gelir: panelin bastigi <option> kumesi,
 * `/liste`nin verdigi `iptal_sebepleri` ile ve `IPTAL_SEBEPLERI` sabitiyle karsilastirilir.
 * Panele elle yazilmis ikinci bir sebep listesi olsaydi bu uc kume ayrilirdi ve kapi
 * sessizce gecerdi ([[ayni-alan-iki-hukum-biri-sessiz]]).
 *
 * 🔴 MUTANTLAR GECICI KOPYA UZERINDE: canli shop/src/yonet.js'e DOKUNULMAZ. Kip, tmp
 * dizinine yonet.js'in kardes dosyalarini SYMLINK'leyip mutantli kopyayi oraya yazar,
 * sonra bu testi `PRUVO_YONET_KAYNAK` ile kendine karsi kosturur (PRUVO_MUTANT=1 ile
 * batarya ATLANIR — yoksa sonsuz dongu).
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (kaynak capasi bulunamadi).
 */

// ---- JSON IMPORT KOPRUSU (test altyapisi; uretim kodunu ETKILEMEZ) -------------
// Gerekce birebir siparis-durum-secici.mjs: yonet.js -> semalar.js -> jenerator/urunler/
// *.json zinciri import attribute'suz alir; ciplak node duser.
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) { return { ...r, importAttributes: { type: 'json' } }; }" +
  "  return r; }"));
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const req = createRequire(import.meta.url);
req(path.join(BURASI, "..", "..", "secenekler.js"));

const MUTANT_KIP = process.env.PRUVO_MUTANT === "1";
const KAYNAK_YOL = process.env.PRUVO_YONET_KAYNAK || path.join(BURASI, "..", "src", "yonet.js");
const KAYNAK = fs.readFileSync(KAYNAK_YOL, "utf8");
const yonetMod = await import(url.pathToFileURL(KAYNAK_YOL).href);
const { yonet } = yonetMod;
const { gecmiseEkle } = yonetMod;
const { IPTAL_SEBEPLERI } = yonetMod;

let gecen = 0, kalan = 0;
const olen = new Set();
function ol(etiket, ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + etiket + " " + ad); }
  else {
    kalan++; olen.add(etiket);
    console.log("  ❌ " + etiket + " " + ad + (detay ? " — " + detay : ""));
  }
}
const YONET_ANAHTAR = "y".repeat(48);
const ctxSahte = { waitUntil() {} };

// ---------------------------------------------------------------- D1 taklidi
/** env.yazmalar = BASARIYLA kosan INSERT/UPDATE kayitlari {sql, args}. */
function mockEnv(siparis, listeSatirlari) {
  const yazmalar = [];
  return {
    yazmalar,
    YONET_ANAHTAR,
    SITE_URL: "https://ornek-site.test",
    KATALOG: {
      prepare(sql) {
        const kayit = { sql, args: [] };
        const calistir = async (kip) => {
          if (/^\s*(INSERT|UPDATE)/i.test(sql)) {
            yazmalar.push(kayit);
            return { meta: { changes: 1 } };
          }
          if (/FROM urunler/.test(sql)) { return { results: [] }; }
          if (/FROM urun_kaynak/.test(sql)) { return { results: [] }; }
          if (/^SELECT siparis_no, tarih, durum, durum_gecmisi/.test(sql)) {
            return siparis || null;
          }
          if (kip === "all") { return { results: listeSatirlari || [] }; }
          return null;
        };
        return {
          bind(...args) { kayit.args = args; return this; },
          async run() { return calistir("run"); },
          async all() { return calistir("all"); },
          async first() { return calistir("first"); },
        };
      },
    },
  };
}

/** BICIMI taklit eden fikstur — gercek musteri verisi/telefon/adres DEGIL. */
function satir(durum, ekstra) {
  return {
    siparis_no: "PR-TEST-000001", tarih: "2026-08-20T10:00:00Z", durum: durum,
    durum_gecmisi: JSON.stringify([{ d: durum, z: "2026-08-20T10:00:00Z" }]),
    urunler: JSON.stringify([]), tutar_kurus: 125000, kargo_kurus: 9000, kdv_kurus: 22500,
    odeme_yontemi: "kart", atif: "", kanal: "site",
    musteri_ad: "Ornek Musteri", musteri_eposta: "", musteri_adres: "Ornek Mah. 1",
    kargo_firma: null, kargo_kodu: null,
    ...(ekstra || {}),
  };
}

function istek(govde) {
  return {
    method: "POST",
    headers: { get: (h) => (h === "X-Yonet-Anahtar" ? YONET_ANAHTAR : null) },
    json: async () => govde,
  };
}

/**
 * POST /yonet/durum — GERCEK router uzerinden.
 * `satirEkstra`: siparis SATIRINA eklenecek alanlar (ozellikle durum_gecmisi).
 * `govdeEkstra`: ISTEK GOVDESINE eklenecek alanlar (ozellikle sebep).
 */
async function durumCagir(mevcut, hedef, satirEkstra, govdeEkstra) {
  const env = mockEnv(satir(mevcut, satirEkstra));
  const c = await yonet(istek({ siparis_no: "PR-TEST-000001", durum: hedef, ...(govdeEkstra || {}) }),
                        env, new URL("https://ornek-site.test/api/shop/yonet/durum"),
                        ctxSahte, "/durum", undefined);
  let govde = null;
  try { govde = await c.json(); } catch (e) { govde = null; }
  return { kod: c.status, govde: govde, env: env };
}

/** UPDATE siparisler'a yazilan YENI durum_gecmisi'nin son kaydi (yoksa null). */
function sonKayit(r) {
  const up = r.env.yazmalar.find((y) => /^UPDATE siparisler/.test(y.sql));
  if (!up) { return null; }
  const gecmisArg = up.args.find((a) => typeof a === "string" && /"d":"/.test(a));
  if (!gecmisArg) { return null; }
  try { return JSON.parse(gecmisArg).slice(-1)[0]; } catch (e) { return null; }
}
function yazmaSayisi(r) {
  return r.env.yazmalar.filter((y) => /^UPDATE siparisler/.test(y.sql)).length;
}

/** Kaynaktan [baslangic, bitis) dilimi. Capa yoksa null (fail-loud). */
function dilimAl(metin, baslangic, bitis) {
  const b = metin.indexOf(baslangic);
  const s = b >= 0 ? metin.indexOf(bitis, b + baslangic.length) : -1;
  return (b >= 0 && s > b) ? metin.slice(b, s) : null;
}
function sablonCoz(s) { return s.replace(/\\\\/g, "\\"); }

// ================================================================ ① SEBEPSIZ IPTAL
console.log("\n① sebepsiz iptal — 400 'iptal-sebebi-gerekli' + D1 YAZMA 0 (fail-closed)");
{
  for (const eksik of [undefined, "", "   "]) {
    const r = await durumCagir("uretimde", "iptal", null,
      eksik === undefined ? {} : { sebep: eksik });
    const et = eksik === undefined ? "alan hic yok" : JSON.stringify(eksik);
    ol("①", "sebep " + et + " -> 400 'iptal-sebebi-gerekli'",
      r.kod === 400 && r.govde && r.govde.hata === "iptal-sebebi-gerekli",
      "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
    ol("①a", "sebep " + et + " -> D1'e YAZMA 0 (satir DEGISMEDI)",
      yazmaSayisi(r) === 0, "yazma=" + yazmaSayisi(r));
  }
  // POZITIF KONTROL: red ucun bozuklugu DEGIL — ayni hedef, gecerli sebeple 200.
  const p = await durumCagir("uretimde", "iptal", null, { sebep: "stok" });
  ol("①k", "AYNI hedef, gecerli sebeple 200 (pozitif kontrol)",
    p.kod === 200 && p.govde && p.govde.durum === "iptal",
    "kod=" + p.kod + " govde=" + JSON.stringify(p.govde));
}

// ================================================================ ② KUME DISI SEBEP
console.log("\n② bilinmeyen sebep kodu — 400 'bilinmeyen-iptal-sebebi' + D1 YAZMA 0");
{
  for (const bozuk of ["bilinmiyor", "Musteri-Odemedi", "IPTAL", "terk", "iptal", "odemedi"]) {
    const r = await durumCagir("uretimde", "iptal", null, { sebep: bozuk });
    ol("②", "'" + bozuk + "' -> 400 'bilinmeyen-iptal-sebebi'",
      r.kod === 400 && r.govde && r.govde.hata === "bilinmeyen-iptal-sebebi",
      "kod=" + r.kod + " govde=" + JSON.stringify(r.govde));
    ol("②a", "'" + bozuk + "' -> D1'e YAZMA 0 (kume disi kod satiri degistirmez)",
      yazmaSayisi(r) === 0, "yazma=" + yazmaSayisi(r));
  }
  ol("②b", "'terk' panelden GONDERILEMEZ (cron izi elle yazilamaz)",
    !IPTAL_SEBEPLERI.includes("terk"), "kume=" + JSON.stringify(IPTAL_SEBEPLERI));
  // Bosluk NORMALIZASYONU acikca beyan edilir: uc girdiyi kirpar, sonra kumeye bakar.
  // Boylece " musteri-odemedi " bir kod DEGIL, kodun kirpilmisl halidir ve iz TEMIZ kod
  // olarak yazilir; yalnizca bosluk ("   ") zorunluluk kirisina takilir (①).
  const n = await durumCagir("uretimde", "iptal", null, { sebep: "  musteri-odemedi  " });
  const nKayit = sonKayit(n);
  ol("②c", "kenar bosluk kirpilir ve iz TEMIZ kod olarak yazilir (iz ' kirpikli olmaz)",
    n.kod === 200 && nKayit && nKayit.s === "musteri-odemedi",
    "kod=" + n.kod + " kayit=" + JSON.stringify(nKayit));
}

// ================================================================ ③ GECERLI SEBEPLER
console.log("\n③ 5 gecerli sebebin HER BIRI -> 200 ve iz `s` = o kod");
{
  ol("③kume", "IPTAL_SEBEPLERI tam olarak 5 kod (beyan edilen kume)",
    Array.isArray(IPTAL_SEBEPLERI) && IPTAL_SEBEPLERI.length === 5 &&
    IPTAL_SEBEPLERI.join(",") === "musteri-odemedi,musteri-vazgecti,dosya-gecikme,stok,diger",
    "kume=" + JSON.stringify(IPTAL_SEBEPLERI));
  let sapan = [];
  for (const sebep of IPTAL_SEBEPLERI) {
    const r = await durumCagir("bekliyor", "iptal", null, { sebep: sebep });
    const kayit = sonKayit(r);
    if (!(r.kod === 200 && r.govde && r.govde.durum === "iptal" && kayit &&
          kayit.d === "iptal" && kayit.s === sebep)) {
      sapan.push(sebep + "=" + r.kod + "/" + JSON.stringify(kayit));
    }
  }
  ol("③", "5/5 sebep 200 + iz {\"d\":\"iptal\",\"s\":\"<kod>\"}", sapan.length === 0, sapan.join(" | "));
  // Iz GERCEKTEN kalici mi: gecmis kirpma/ozet icinde kaybolmaz.
  const r = await durumCagir("bekliyor", "iptal", {
    durum_gecmisi: JSON.stringify([{ d: "odendi", z: "2026-08-20T09:00:00Z" }]),
  }, { sebep: "dosya-gecikme" });
  const kayit = sonKayit(r);
  ol("③a", "iz ONCEKI kayitlari ezmez (gecmis listesi olarak birikir)",
    !!kayit && kayit.s === "dosya-gecikme", "kayit=" + JSON.stringify(kayit));
  // 🔴 KART AKISI IZI KORUNUR: 'odendi' olcum izi ('o':1) iptal kaydinin yaninda KALIR.
  const olcumlu = await durumCagir("odendi", "iptal", {
    durum_gecmisi: JSON.stringify([{ d: "odendi", z: "2026-08-20T09:00:00Z", o: 1 }]),
  }, { sebep: "musteri-vazgecti" });
  const oKayit = sonKayit(olcumlu);
  ol("③b", "iptal kaydi olcum izini ('o':1) SILMIYOR (satir satiri bozulmaz)",
    !!oKayit && oKayit.s === "musteri-vazgecti", "kayit=" + JSON.stringify(oKayit));
}

// ================================================================ ④ IPTAL DISI HEDEF
console.log("\n④ iptal disi hedeflerde sebep YOK SAYILIR (iz degismez, kapali degildir)");
{
  for (const hedef of ["uretimde", "tamamlandi", "kargolandi"]) {
    for (const sebep of ["musteri-vazgecti", "terk", "bilinmiyor"]) {
      const satirEkstra = hedef === "kargolandi" ? null : null;
      const r = await durumCagir("bekliyor", hedef, satirEkstra, { sebep: sebep });
      const kayit = sonKayit(r);
      // 'bekliyor' -> 'odendi' 400 'odeme-durumu-elle-setlenemez' verir; o da YAZMA 0'dir.
      const yazdi = yazmaSayisi(r) === 1;
      const bekleniyor = r.kod === 200
        ? (yazdi && kayit && kayit.d === hedef && kayit.s === undefined)
        : (yazmaSayisi(r) === 0);
      ol("④", "'" + hedef + "' + sebep '" + sebep + "' -> " +
        (r.kod === 200 ? "200 ve iz `s` YOK" : "kapalı gecis 400 " + (r.govde && r.govde.hata)),
        bekleniyor,
        "kod=" + r.kod + " kayit=" + JSON.stringify(kayit));
    }
  }
  // Sebepsiz iptal-disi gecis HICBIR SEY DEGISTIRMIYOR (regresyon: eski davranis).
  const r = await durumCagir("bekliyor", "uretimde");
  ol("④a", "iptal disi hedef sebepsiz de 200 (kapı yalnız 'iptal'i etkiler)",
    r.kod === 200 && sonKayit(r) && sonKayit(r).d === "uretimde" &&
    sonKayit(r).s === undefined, "kod=" + r.kod);
}

// ================================================================ ⑤ TERK SUPURMESI
console.log("\n⑤ terk supurmesi izi (`s:\"terk\"`) ETKILENMEZ");
{
  // (a) D1 yazma yolu: gecmiseEkle ayni bicimi yazmaya devam eder.
  const g = JSON.parse(gecmiseEkle("[]", "iptal", { sebep: "terk" }));
  const son = g.slice(-1)[0];
  ol("⑤", "gecmiseEkle(...,'iptal',{sebep:'terk'}) -> s='terk'",
    son && son.d === "iptal" && son.s === "terk", "kayit=" + JSON.stringify(son));
  // (b) Uretici degismedi: index.js'teki terk kolu AYNI cagriyi yapmaya devam ediyor.
  const indexKaynak = fs.readFileSync(path.join(BURASI, "..", "src", "index.js"), "utf8");
  ol("⑤a", "shop/src/index.js terk kolu hala gecmiseEkle(..., 'iptal', { sebep: TERK_SEBEP })",
    /gecmiseEkle\(s\.durum_gecmisi, "iptal", \{ sebep: TERK_SEBEP \}\)/.test(indexKaynak),
    "cagri bulunamadi");
  // (c) 'terk' panel kumesinde DEGIL (uretici ile secicinin kumesi karismaz).
  ol("⑤b", "IPTAL_SEBEPLERI 'terk' ICERMIYOR (cron izi secim kumesine karismaz)",
    !IPTAL_SEBEPLERI.includes("terk"), "kume=" + JSON.stringify(IPTAL_SEBEPLERI));
}

// ---------------------------------------------------------------- PANEL ekseni
const panelKaynak = sablonCoz(dilimAl(KAYNAK, "function esc(s){", "async function yukle(){") || "");
if (!panelKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (sayfa JS blogu) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
const panel = { document: null };
vm.createContext(panel);
vm.runInContext(panelKaynak, panel, { filename: "yonet-sayfa.js" });
// 🔴 `durumDegis` ilk dilimde DEGILDIR: `yukle()` onun ONUNDE gelir. Ikinci dilim AYRI
// alinir ve AYNI baglama kosturulur (kopya yazilmaz, kaynaktan okunur).
const durumDegisKaynak = sablonCoz(dilimAl(KAYNAK, "async function durumDegis(", "async function kargoGonder(") || "");
if (!durumDegisKaynak) {
  console.error("KAYNAK CAPASI BULUNAMADI (durumDegis) — yonet.js yapisi degisti mi?");
  process.exit(3);
}
vm.runInContext(durumDegisKaynak, panel, { filename: "yonet-sayfa-durumdegis.js" });
const kartHtml = panel.kartHtml;
if (typeof kartHtml !== "function" || typeof panel.durumDegis !== "function") {
  console.error("SAYFA FONKSIYONU CEKILEMEDI (kartHtml/durumDegis) — OLCULEMEDI");
  process.exit(3);
}

/** GET /yonet/liste -> sunucunun verdigi siparis (iptal_sebepleri dahil). null = OLCULEMEDI. */
async function listeSiparis(mevcut) {
  const env = mockEnv(satir(mevcut), [satir(mevcut)]);
  const c = await yonet(
    { method: "GET",
      headers: { get: (h) => (h === "X-Yonet-Anahtar" ? YONET_ANAHTAR : null) } },
    env, new URL("https://ornek-site.test/api/shop/yonet/liste"), ctxSahte, "/liste", undefined);
  if (c.status !== 200) { return null; }
  const g = await c.json();
  return (g.siparisler || [])[0] || null;
}

function kartFikstur(mevcut, izinli, sebepler, gecmis) {
  return {
    siparis_no: "PR-TEST-" + mevcut, tarih: "2026-08-20T10:00:00Z", durum: mevcut,
    kanal: "site", dis_no: "", odeme_yontemi: "kart",
    tutar_kurus: 125000, kargo_kurus: 9000, kdv_kurus: 22500,
    kargo_firma: "", kargo_kodu: "", durum_gecmisi: gecmis || [],
    izinli_gecisler: izinli, iptal_sebepleri: sebepler || [],
    musteri: { ad: "Ornek Musteri", tel: "0500 000 00 00", eposta: "ornek@ornek.invalid",
               adres: "Ornek Mah. 1" },
    kalemler: [], musteri_notu: "", yazdir_komut: "python3 tools/yazdir.py PR-TEST",
  };
}

function sebepSecenekleri(html) {
  const blok = dilimAl(html, '<select id="is-', "</select>") || "";
  const out = [];
  const re = /<option value="([^"]*)"/g;
  let m;
  while ((m = re.exec(blok)) !== null) { out.push(m[1]); }
  return out;
}
function ozetSatiri(html) {
  return dilimAl(html, '<summary class="ust">', "</summary>") || "";
}

console.log("\n⑥ panel — iptal secilince 5 sebep ZORUNLU, secilmeden istek GITMEZ");
{
  const s = await listeSiparis("uretimde");
  if (!s) {
    console.error("/liste OLCULEMEDI");
    process.exit(3);
  }
  ol("⑥", "/liste sunucu kumesini `iptal_sebepleri` olarak GONDERIYOR",
    Array.isArray(s.iptal_sebepleri) && s.iptal_sebepleri.join(",") === IPTAL_SEBEPLERI.join(","),
    JSON.stringify(s.iptal_sebepleri));
  const html = kartHtml(kartFikstur("uretimde", s.izinli_gecisler, s.iptal_sebepleri));
  const opts = sebepSecenekleri(html);
  ol("⑥a", "panelin bastigi 5 <option> == sunucunun IPTAL_SEBEPLERI kumesi (ayni sirada)",
    opts.length === IPTAL_SEBEPLERI.length + 1 && opts.slice(1).join(",") === IPTAL_SEBEPLERI.join(","),
    "opts=" + JSON.stringify(opts));
  ol("⑥b", "ilk option BOS (hicbir sebep varsayilan secilmiyor)",
    opts.length > 0 && opts[0] === "", "opts=" + JSON.stringify(opts));
  // Iptal secilemiyorsa kutu BASILMAZ (her kartta 'sebep sec' istemiyoruz).
  const iptalsiz = kartHtml(kartFikstur("iptal", ["uretimde"], s.iptal_sebepleri));
  ol("⑥c", "'iptal' secilemiyorken sebep kutu BASILMAZ",
    sebepSecenekleri(iptalsiz).length === 0 && !/id="is-/.test(iptalsiz), "-");
  // Kaynak ekseni: panele elle yazilmis ikinci sebep listesi YOK.
  const sebepBlok = dilimAl(panelKaynak, " var iptalSebepForm=", " var sebepRozet=") || "";
  if (!sebepBlok) {
    console.error("KAYNAK CAPASI BULUNAMADI (sebep kutusu) — kartHtml yapisi degisti mi?");
    process.exit(3);
  }
  ol("⑥d", "sebep <option> uretimi TEK kaynaktan: s.iptal_sebepleri (elle liste YOK)",
    /s\.iptal_sebepleri\|\|\[\]/.test(sebepBlok) &&
    !(sebepBlok.match(/"(musteri-odemedi|musteri-vazgecti|dosya-gecikme|stok|diger)"/g) || []).length,
    sebepBlok.trim().slice(0, 160));
}

/** ⑦ davranis ekseni: durumDegis'i sahte document/api ile GERCEKTEN cagirir. */
console.log("\n⑦ panel davranisi — sebep secilmeden /durum istegi GITMEZ");
{
  function panelCagir(secili, hedef) {
    const cagrilar = [];
    const uyarilar = [];
    panel.document = { getElementById: () => ({ value: secili }) };
    panel.api = async (yol, sec) => { cagrilar.push({ yol: yol, sec: sec }); return { kod: 200, govde: { ok: true } }; };
    panel.alert = (m) => { uyarilar.push(m); };
    panel.confirm = () => true;
    panel.yukle = async () => {};
    return panel.durumDegis("PR-TEST-uretimde", hedef).then(() => {
      const govde = cagrilar.length && cagrilar[0].sec
        ? JSON.parse(cagrilar[0].sec.body) : null;
      return { cagri: cagrilar, govde: govde, uyarilar: uyarilar };
    });
  }
  const bos = await panelCagir("", "iptal");
  ol("⑦", "sebep BOSKEN /durum istegi GONDERILMEZ (0 cagri)",
    bos.cagri.length === 0, "cagri=" + bos.cagri.length + " uyari=" + bos.uyarilar.join("|"));
  ol("⑦a", "bos secimde kullaniciya durulur (sessizce hicbir sey olmaz)",
    bos.uyarilar.length === 1 && /seç/.test(bos.uyarilar[0]), bos.uyarilar.join("|"));
  const dolu = await panelCagir("stok", "iptal");
  ol("⑦b", "sebep secilince /durum'a 1 istek + govde.sebep = 'stok'",
    dolu.cagri.length === 1 && dolu.govde && dolu.govde.sebep === "stok" &&
    dolu.govde.durum === "iptal" && dolu.govde.siparis_no === "PR-TEST-uretimde",
    JSON.stringify(dolu.govde));
  const diger = await panelCagir("stok", "tamamlandi");
  ol("⑦c", "iptal disi hedefte govde.sebep ALANI HIC GONDERILMEZ",
    diger.cagri.length === 1 && diger.govde && diger.govde.durum === "tamamlandi" &&
    !("sebep" in diger.govde), JSON.stringify(diger.govde));
}

/** ⑧ panel listesi: iptal satirinin yaninda sebep kodu. */
console.log("\n⑧ panel listesi — iptal satirinda sebep kodu gorunur");
{
  const s = await listeSiparis("iptal");
  const temel = kartFikstur("iptal", ["uretimde"], IPTAL_SEBEPLERI);
  const terki = kartHtml({ ...temel, durum_gecmisi: [{ d: "iptal", z: "2026-10-22T04:10:00Z", s: "terk" }] });
  const stoklu = kartHtml({ ...temel, durum_gecmisi: [{ d: "iptal", z: "2026-10-22T05:00:00Z", s: "stok" }] });
  const sebepsiz = kartHtml({ ...temel, durum_gecmisi: [{ d: "iptal", z: "2026-10-22T05:00:00Z" }] });
  ol("⑧", "iptal satirinda 'Sebep: stok' gorunur (ozet satirinda)",
    /Sebep: stok/.test(ozetSatiri(stoklu)), ozetSatiri(stoklu));
  ol("⑧a", "terk satiri 'Sebep: terk' gosterir (cron izi panelde de okunur)",
    /Sebep: terk/.test(ozetSatiri(terki)), ozetSatiri(terki));
  ol("⑧b", "sebepsiz eski iptal 'Sebep: —' gosterir (UYDURMA YOK)",
    /Sebep: —/.test(ozetSatiri(sebepsiz)), ozetSatiri(sebepsiz));
  ol("⑧c", "iptal olmayan satirda sebep rozeti BASILMAZ",
    !/Sebep:/.test(ozetSatiri(kartHtml(kartFikstur("uretimde", ["tamamlandi"], IPTAL_SEBEPLERI)))),
    "-");
  ol("⑧d", "/liste 'iptal' satirinda `durum_gecmisi` son iptal kaydinin `s` alanini TASIYOR",
    !!s && Array.isArray(s.durum_gecmisi) && s.durum_gecmisi.every((k) => !("sebep" in k)),
    JSON.stringify(s && s.durum_gecmisi));
}

// ================================================================ ⑨ MUTANTLAR
// (a) hedef kol: mutantin OLDURMESI gereken iddia(lar) gercekten kirmizi yandi mi?
// (b) yan eksen: yasamasi gerekenler yesil kaldi mi? (mutant IZOLE mi?)
if (MUTANT_KIP) {
  // Bu kosumun amaci zaten mutant: kendi bataryasini KURMAZ (dongu).
  console.log("\nMUTANT KIPI — batarya atlandi");
} else {
  console.log("\n⑨ mutasyon bataryasi (gecici kopya — canli yonet.js'E DOKUNULMAZ)");
  const { spawnSync } = await import("node:child_process");
  const MUTANTLAR = [
    { kim: "M1_ZORUNLULUK",
      aciklama: "sebep bos/eksik kontrolu KALDIRILIR",
      eski: '    if (!sebep) { return yjson({ hata: "iptal-sebebi-gerekli" }, 400); }',
      yeni: '    if (false) { return yjson({ hata: "iptal-sebebi-gerekli" }, 400); }',
      // ⚠️ ①a (D1 yazma 0) BILerek listeye DEGIL: zorunluluk kaldirilinca bos sebep yine
      // kume kapisina takilir, yani SATIR YINE DEGISMEZ — ①'in KENDISI (hata kodu) kirilir.
      // Buradaki asil bulgu: iki katman birbirinin YERINI TUTMAZ ([[katman-tek-basina-yetmez]]).
      oldurur: ["①"] },
    { kim: "M2_KUME",
      aciklama: "kume uyeligi kontrolu KALDIRILIR",
      eski: "    if (!IPTAL_SEBEPLERI.includes(sebep)) {",
      yeni: "    if (false) {",
      oldurur: ["②", "②a"] },
    { kim: "M3_GECMIS",
      aciklama: "sebep gecmiseEkle'ye GECIRILMEZ (iz `s` hic yazilmaz)",
      eski: "{ olcumDenendi: olcumTetikle, sebep }",
      yeni: "{ olcumDenendi: olcumTetikle }",
      // ③ + izi okuyan ②c/③a/③b — mutant izi tamamen SILDIGI icin hepsi kirmizilandir.
      // "Yan etki" degil, ayni kapi: hepsi ayni yazma satirini okuyor.
      oldurur: ["③", "②c", "③a", "③b"] },
  ];
  // Capa disiplini: dayanak metin kaynakta TEKIL olmali (sessiz atlama YOK).
  let bayat = [];
  for (const m of MUTANTLAR) {
    const adet = KAYNAK.split(m.eski).length - 1;
    if (adet !== 1) { bayat.push(m.kim + "=" + adet + " kez"); }
  }
  if (bayat.length) {
    ol("⑨c", "mutant dayanak metinleri kaynakta TEKIL (harness bayat degil)", false, bayat.join(","));
  } else {
    ol("⑨c", "mutant dayanak metinleri kaynakta TEKIL (harness bayat degil)", true);
    const gecici = fs.mkdtempSync(path.join(os.tmpdir(), "iptal-sebep-mutant-"));
    try {
      // Ayna: repo kokundeki girisler, shop/ ve shop/src/ SYMLINK'lenir; yalnizca
      // mutantli yonet.js GERCEK dosya olarak yazilir (kardesleri cozumlesin diye).
      const kok = path.resolve(BURASI, "..", "..");
      for (const ad of fs.readdirSync(kok)) {
        if (ad === "shop" || ad === ".git") { continue; }
        fs.symlinkSync(path.join(kok, ad), path.join(gecici, ad));
      }
      fs.mkdirSync(path.join(gecici, "shop"));
      for (const ad of fs.readdirSync(path.join(kok, "shop"))) {
        if (ad === "src") { continue; }
        fs.symlinkSync(path.join(kok, "shop", ad), path.join(gecici, "shop", ad));
      }
      fs.mkdirSync(path.join(gecici, "shop", "src"));
      for (const ad of fs.readdirSync(path.join(kok, "shop", "src"))) {
        if (ad === "yonet.js") { continue; }
        fs.symlinkSync(path.join(kok, "shop", "src", ad), path.join(gecici, "shop", "src", ad));
      }
      for (const m of MUTANTLAR) {
        const mutantYol = path.join(gecici, "shop", "src", "yonet-mutant-" + m.kim + ".js");
        fs.writeFileSync(mutantYol, KAYNAK.replace(m.eski, m.yeni));
        const p = spawnSync(process.execPath, [path.join(kok, "shop", "test", "iptal-sebep.mjs")], {
          cwd: kok,
          env: { ...process.env, PRUVO_YONET_KAYNAK: mutantYol, PRUVO_MUTANT: "1" },
          encoding: "utf8",
        });
        const cikti = (p.stdout || "") + (p.stderr || "");
        const olenMutant = new Set();
        const mo = /OLEN_IDDIALAR=(.*)/.exec(cikti);
        if (mo && mo[1].trim() && mo[1].trim() !== "-") {
          mo[1].trim().split(",").forEach((x) => olenMutant.add(x.trim()));
        }
        const kacti = m.oldurur.filter((e) => !olenMutant.has(e));
        const rcBilgi = p.error ? "SPAWN_HATA:" + p.error.message
          : (p.signal ? "SIGNAL:" + p.signal : "rc=" + p.returncode);
        if (p.error || p.signal || cikti.indexOf("OLCULEMEDI") >= 0) {
          // Mutant kosusu HIC BIR SEY OLCEMEDI: kirmizi yanmamis sayilir (fail-loud).
          ol("⑨-" + m.kim, "mutant kosumu SAGLIKLI sonlandi", false, rcBilgi);
        }
        ol("⑨-" + m.kim, "hedef kol KIRMIZI yandi (" + m.aciklama + ")",
          kacti.length === 0, "KACTI: " + (kacti.join(",") || "-") + " | " + rcBilgi);
        // Yan eksen: mutant izOLE olmali (hedef disi bir iddia KIRILIRSA hata degil,
        // mutantin yan etkisidir — fail-closed: raporda gorunur).
        const yan = [...olenMutant].filter((e) => !m.oldurur.includes(e));
        ol("⑨-" + m.kim + "/yan", "yalnizca hedef iddia(lar) olu (mutant IZOLE)",
          yan.length === 0, "yan etki: " + (yan.join(",") || "-"));
      }
    } finally {
      fs.rmSync(gecici, { recursive: true, force: true });
    }
  }
}

// ================================================================ SONUC
console.log("\nTOPLAM: " + (gecen + kalan) + " iddia | GECEN " + gecen + " | KALAN " + kalan);
console.log("OLEN_IDDIALAR=" + (olen.size ? [...olen].sort().join(",") : "-"));
console.log("=== SONUC: " + gecen + " gecti / " + kalan + " kaldi ===");
process.exit(kalan === 0 ? 0 : 1);