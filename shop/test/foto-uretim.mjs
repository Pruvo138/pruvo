#!/usr/bin/env node
/**
 * PRUVO shop — FOTOGRAFTAN OZEL URETIM KABUL KAPISI (Okan karari 5 Eki 2026; kod
 * shop/src/foto.js + index.js /baslat kalemi + yonet.js panel uclari).
 *
 *   node shop/test/foto-uretim.mjs
 *
 * OLCTUGU HUKUMLER (BaBa kutu 5 Eki 18:1x, 8 madde):
 *   A KAPALI-VARSAYILAN : bugunku veri dosyasiyla (onay metni onaysiz, gercek ornek 0) bolum
 *                         KAPALI; onizleme 503, /baslat foto kalemi 400, cron D1'e dokunmaz
 *   B ACILIS ANAHTARI   : foto_acik bos -> tur sunulmaz; panelden "Aç" yazilinca sunulur; olcu+fiyat
 *                         TEK FORMULDEN (en uzun boyut mm x 1000 kurus; fiyat tablosu YOK, Okan 7 Eki)
 *   C ONIZLEME          : saglayiciya yalniz ONIZLEME gider (odemeden once tek kredi adimi);
 *                         gorsel bizim ucumuzdan sunulur; kredi defterine BIR kez yazilir
 *   D SINIR             : ziyaretci basi 24 saatte N onizleme; N+1. istek 429 ve saglayiciya
 *                         GITMEZ; baska ziyaretci etkilenmez            (Kapatan: "sinir+1 RED")
 *   E BOT KAPISI        : jeton yok/red/ag hatasi -> 403 (fail-CLOSED), saglayiciya gitmez
 *   F ONAY + GORSEL     : iki onay kutusu + guncel onay surumu sart; sahte gorsel reddedilir
 *   G HAVUZ             : bakiye esigin altinda -> bolum kapanir + Telegram TEK bildirim
 *   H /baslat           : fiyat SUNUCUDA formulden (+kargo kurali), havale RED, suresi dolmus
 *                         onizleme RED
 *   I URETIM ZINCIRI    : 'bekliyor' siparis uretime GIRMEZ; 'odendi' -> model -> analiz ->
 *                         4 renk -> 3MF+GLB ozel kovada -> panelde indirilebilir; kredi 46
 *   J ANALIZ KIRMIZI    : renk adimi KOSMAZ, satir 'elle' + Telegram bir kez
 *   K MARKASIZ          : saglayici adi / anahtar oneki calisma agacinda 0 (git grep)
 *   L DRIFT             : wrangler.toml cron + hiz siniri beyani index.js ile ayni
 *   M PANEL OZETI       : tur basina kalem ↔ elle sayisi + aylik kredi
 * PLAKET KARARI (BaBa 5 Eki 21:4x(b) — Okan: "plaket yapalim"; yalniz plastik uretiyoruz):
 *   P TUR LISTESI       : sunulan tur 1 (plaket); anahtarlik/magnet/figur panel fiyatinda ve
 *                         onizlemede RED; saglayici tur yolu kodda degil ORTAM DEGISKENINDE
 *   Q SUNULMAYAN TUR    : eski kayittan /baslat RED · odenmis magnet kalemi kuyruga girmez ·
 *                         kuyruktaki anahtarlik satiri saglayiciya gitmeden 'elle'
 *   I3b/I8b/J4 AYAK     : Build'e sabit kabartma/taban + kapali sirt; kalemde foto_ayak 1,
 *                         panel baski notunda "AYAK: <adet> adet"
 *   S EKRAN             : foto-uretim.js SAHTE DOM'da kosar: tek turde tur radyosu 0 + adim
 *                         "Olcu"; olcu SURGULERI (S1 + S3) gercekten cizilir, kayarken "N mm → X TL"
 *                         (TEK formul), fiyat listesi satiri 0 (Okan 7 Eki)
 * ORNEK URETIM (BaBa 6 Eki — panel "Örnek üret", Okan'in kendi fotografi, odemesiz):
 *   O YETKI+AYRIM       : ornek uclari anahtarsiz 404 · anahtar/tur yolu yoksa 503 + saglayiciya 0 ·
 *                         bot/onay/gercek-ornek/ziyaretci siniri ATLANIR · ornek isi sepette RED ·
 *                         musteri /foto/durum+/foto/gorsel ornegi gostermez · gunluk tavana sayilmaz ·
 *                         cron ORNEK-<is> satirini isler, 3MF ozel kovada, kredi 46 deftere ·
 *                         "Örnek üretimler" listesi + anahtarli indirme · havuz esigi AYNEN
 * OLCU KAPISI (6 Eki — onarim zincirinden 1094 mm 3MF cikti, siparis 120 mm):
 *   OL                  : 3MF R2'ye yazilmadan once olculur; XY uzun kenar %3 disindaysa build
 *                         item'a duze olcek, yeniden olcum; tutmazsa 'elle' olcu-tutmadi + R2 0.
 *                         Onarimli ve onarimsiz yolda AYNI kapi. Fiksturler sentetik (kucuk).
 *   OM-A..OM-C          : kapi atlandi / olcek ters yone / tutmayan olcu yazildi -> KIRMIZI;
 *                         OM-K (yalniz yorum) -> hicbiri
 * OLCU EKSENI (Okan 7 Eki 15:4x: "en boy yükseklik fark etmez hangisi uzunsa"):
 *   OZ                  : en uzun ekseni Z olan nesne (40x30x200) -> 120 mm'ye Z'den olceklenir, bagimsiz
 *                         olcumde EN UZUN boyut 120 ±%3, fiyat = 120 mm formulu (120000); uretec olcu.json'da
 *                         Z uzun kenardan buyukse RED. OZ-M1 (X/Y'ye bakan olcu) · OZ-M2 (Z sarti silindi) KIRMIZI
 * PLAKET ACILISI (Okan 7 Eki: "baskı yapmayacağım böyle tamam" — gercek baski beklenmez):
 *   RO                  : veri dosyasindaki `kanit:"render"` kaydi plaketi acar (/foto/acik
 *                         plaket hazir) · `ornek_kanit_izni` disi kanit (litofana render,
 *                         bilinmeyen kanit) ACMAZ · izin alani yoksa hicbiri sayilmaz · render
 *                         gorseli eksik kayit sayilmaz · litofan baski kaydiyla AYNEN acilir
 *   RO-M1..RO-M3        : izin kontrolu silindi / izin varsayilani acik / render gorsel sarti
 *                         silindi -> ilgili RO senaryosu KIRMIZI; RO-MK (yalniz yorum) -> hicbiri
 *                         (mutant veri dosyasinin BELLEKTEKI kopyasina uygulanir)
 *   ES                  : bolumde render kaydi "önizleme/render" etiketi + abarti cumlesiyle
 *                         cizilir, "gerçek fotoğraf" metni 0, ozgun foto gorseli 0; baski kaydi
 *                         eski etiketle (ES-M1/ES-M2 ekran mutantlari KIRMIZI)
 *   AK                  : olceklenmis 3MF'in ALT KENAR kalinligi (Y en kucuk 10 mm serit, Z
 *                         yayilimi) analiz ozetine + panel kaydina `alt_kenar_mm`; sentetik
 *                         6,5 mm serit -> 6,5 ±0,1 (olceksiz ve 10x olcekli). AK-M1..AK-M4 KIRMIZI
 *
 * NASIL: GERCEK worker (shop/src/index.js) import edilir. D1 = GERCEK SQLite: sema
 * tools/d1-sema.sql'den kurulur (shop/test/ortak/sqlite-koprusu.py) — elle yazilmis
 * ikinci sema YOK. Saglayici, bot dogrulayici, iyzico ve Telegram `globalThis.fetch`
 * stub'idir: GERCEK AG ISTEGI YOK. R2 bellekte sahtedir.
 *
 * ONCE-KIRMIZI KANITI (mutantlar bu dosyanin sonunda; foto.js'in GECICI kopyasina
 * uygulanir, calisma agacina YAZMAZ):
 *   M1 SINIR  : ziyaretci siniri kontrolu devre disi   -> D OLUR
 *   M2 BOT    : bot dogrulamasi devre disi             -> E OLUR
 *   M3 ANALIZ : kirmizi analiz kapisi devre disi       -> J OLUR
 *   M4 TUR    : anahtarlik tur tablosuna geri acilir   -> T OLUR
 *   M5 AYAK   : odeme kaleminden foto_ayak duser       -> A OLUR
 *   K0 KONTROL: yalniz log metni degisir               -> HICBIRI OLMEZ
 *   OM1..OM6  : ornek ayrim dallari (sepet/durum/gorsel/tavan/dosya/uret) tek tek silinir
 *               -> ilgili ORNEK senaryosu OLUR; OK0 (yalniz yorum) -> HICBIRI OLMEZ
 *   (ekran mutantlari S-M1..S-M4 bellekteki kaynak metnine uygulanir)
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (modul/kopru kurulamadi).
 */

// ---- JSON IMPORT KOPRUSU (terk-supurme.mjs ile ayni gerekce; uretim kodunu ETKILEMEZ) ----
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) {" +
  "    return { ...r, format: 'json', importAttributes: { type: 'json' } }; }" +
  "  return r; }"));

import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import readline from "node:readline";
import vm from "node:vm";
import zlib from "node:zlib";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const SHOP = path.join(KOK, "shop");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

// ---------------------------------------------------------------- gercek SQLite koprusu

function koprukur() {
  const p = spawn("python3", [path.join(BURASI, "ortak", "sqlite-koprusu.py")],
                  { stdio: ["pipe", "pipe", "inherit"] });
  const rl = readline.createInterface({ input: p.stdout });
  const bekleyen = [];
  rl.on("line", (s) => { const c = bekleyen.shift(); if (c) { c(JSON.parse(s)); } });
  const istek = (o) => new Promise((coz) => { bekleyen.push(coz); p.stdin.write(JSON.stringify(o) + "\n"); });
  const hazir = new Promise((coz) => bekleyen.push(coz));
  const d1 = {
    prepare(sql) {
      let binds = [];
      const st = {
        bind(...b) { binds = b; return st; },
        async all() { const c = await istek({ sql, binds, mod: "all" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return { results: c.results, meta: c.meta, success: true }; },
        async first() { const c = await istek({ sql, binds, mod: "all" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return c.results[0] || null; },
        async run() { const c = await istek({ sql, binds, mod: "run" }); if (c.error) { throw new Error("D1_ERROR: " + c.error); } return { meta: c.meta, success: true }; },
      };
      return st;
    },
  };
  return { d1, hazir, kapat: () => p.stdin.end() };
}

function r2Kur() {
  const m = new Map();
  return {
    m,
    async put(k, v, o) { m.set(k, { bayt: new Uint8Array(v), httpMetadata: (o && o.httpMetadata) || {} }); },
    async get(k) { const x = m.get(k); return x ? { body: x.bayt, httpMetadata: x.httpMetadata } : null; },
    async delete(k) { m.delete(k); },
    async list() { return { objects: [] }; },
  };
}

// ---------------------------------------------------------------- sahte ag (saglayici + digerleri)

const TABAN = "https://saglayici.test/openapi";
const PNG = Uint8Array.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ...new Array(64).fill(7)]);
// ---- SENTETIK 3MF FIKSTURLERI (kucuk; gercek 8 MB dosya depoya GIRMEZ). Yapi gercek ornekle
// ayni: ana model tek bilesen + tek build item (plaka ortasi), tepeler 3D/Objects altinda.
function zipYaz(girdiler) {
  const yerel = [], merkez = [];
  let p = 0;
  for (const [ad, metin, sakla] of girdiler) {
    const ham = Buffer.from(metin), adB = Buffer.from(ad);
    const veri = sakla ? ham : zlib.deflateRawSync(ham);
    const crc = zlib.crc32(ham);
    const h = Buffer.alloc(30); h.writeUInt32LE(0x04034b50, 0); h.writeUInt16LE(20, 4);
    h.writeUInt16LE(sakla ? 0 : 8, 8); h.writeUInt32LE(crc, 14); h.writeUInt32LE(veri.length, 18);
    h.writeUInt32LE(ham.length, 22); h.writeUInt16LE(adB.length, 26);
    const m = Buffer.alloc(46); m.writeUInt32LE(0x02014b50, 0); m.writeUInt16LE(20, 4); m.writeUInt16LE(20, 6);
    m.writeUInt16LE(sakla ? 0 : 8, 10); m.writeUInt32LE(crc, 16); m.writeUInt32LE(veri.length, 20);
    m.writeUInt32LE(ham.length, 24); m.writeUInt16LE(adB.length, 28); m.writeUInt32LE(p, 42);
    yerel.push(h, adB, veri); merkez.push(m, adB); p += 30 + adB.length + veri.length;
  }
  const mb = Buffer.concat(merkez), e = Buffer.alloc(22);
  e.writeUInt32LE(0x06054b50, 0); e.writeUInt16LE(girdiler.length, 8); e.writeUInt16LE(girdiler.length, 10);
  e.writeUInt32LE(mb.length, 12); e.writeUInt32LE(p, 16);
  return new Uint8Array(Buffer.concat([...yerel, mb, e]));
}
/** XY yari kenar (ax, ay), yukseklik h (model birimi = mm) kutu; ikiOge -> build'de iki item. */
function ucmfKur(ax, ay, h, ikiOge) {
  const t = [];
  for (let i = 0; i < 8; i++) { t.push('     <vertex x="' + (i & 1 ? ax : -ax) + '" y="' + (i & 2 ? ay : -ay) + '" z="' + (i & 4 ? h : 0) + '"/>'); }
  const ucgen = [[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]]
    .map((u) => '     <triangle v1="' + u[0] + '" v2="' + u[1] + '" v3="' + u[2] + '"/>');
  const kafa = '<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n';
  const nesne = kafa + ' <resources>\n  <object id="1" type="model">\n   <mesh>\n    <vertices>\n' + t.join("\n") +
    '\n    </vertices>\n    <triangles>\n' + ucgen.join("\n") + '\n    </triangles>\n   </mesh>\n  </object>\n </resources>\n <build/>\n</model>\n';
  const oge = '  <item objectid="2" p:UUID="00000002-0000-0000-0000-000000000000" transform="1 0 0 0 1 0 0 0 1 125 125 0" printable="1"/>\n';
  const ana = kafa + ' <resources>\n  <object id="2" type="model">\n   <components>\n' +
    '    <component p:path="/3D/Objects/object_1.model" objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n' +
    '   </components>\n  </object>\n </resources>\n <build>\n' + oge + (ikiOge ? oge : "") + ' </build>\n</model>\n';
  return zipYaz([
    ["[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>\n'],
    ["_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>\n'],
    ["3D/3dmodel.model", ana],
    ["3D/Objects/object_1.model", nesne],
    ["Metadata/model_settings.config", '<?xml version="1.0" encoding="UTF-8"?>\n<config><object id="2"><metadata key="name" value="Object_1"/></object></config>\n', true],
  ]);
}
/** BAGIMSIZ olcer (foto.js'e DAYANMAZ): zip -> {L (XY uzun kenar), L3 (x/y/z EN UZUN boyut), z, item transform, girdiler}. */
function testOlc(bayt) {
  const b = Buffer.from(bayt);
  const e = b.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  if (e < 0) { return null; }
  const girdiler = new Map(), acik = new Map();
  let p = b.readUInt32LE(e + 16);
  for (let i = 0; i < b.readUInt16LE(e + 10); i++) {
    const ad = b.toString("utf8", p + 46, p + 46 + b.readUInt16LE(p + 28));
    const yontem = b.readUInt16LE(p + 10), cs = b.readUInt32LE(p + 20), yr = b.readUInt32LE(p + 42);
    const v = yr + 30 + b.readUInt16LE(yr + 26) + b.readUInt16LE(yr + 28);
    const ham = b.subarray(v, v + cs);
    girdiler.set(ad, Buffer.from(ham));
    acik.set(ad, (yontem === 8 ? zlib.inflateRawSync(ham) : ham).toString("utf8"));
    p += 46 + b.readUInt16LE(p + 28) + b.readUInt16LE(p + 30) + b.readUInt16LE(p + 32);
  }
  const ana = acik.get("3D/3dmodel.model") || "";
  const M = (/<item\b[^>]*\btransform="([^"]*)"/.exec(ana) || [, "1 0 0 0 1 0 0 0 1 0 0 0"])[1].trim().split(/\s+/).map(Number);
  const en = [Infinity, Infinity, Infinity], ust = [-Infinity, -Infinity, -Infinity];
  for (const [ad, metin] of acik) {
    if (!/^3D\/.*\.model$/.test(ad)) { continue; }
    for (const m of metin.matchAll(/<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"/g)) {
      const q = [+m[1], +m[2], +m[3]];
      for (let k = 0; k < 3; k++) {
        const d = q[0] * M[k] + q[1] * M[3 + k] + q[2] * M[6 + k] + M[9 + k];
        en[k] = Math.min(en[k], d); ust[k] = Math.max(ust[k], d);
      }
    }
  }
  return { L: Math.max(ust[0] - en[0], ust[1] - en[1]), L3: Math.max(ust[0] - en[0], ust[1] - en[1], ust[2] - en[2]),
           z: ust[2] - en[2], zTaban: en[2], M, girdiler };
}
/**
 * Alt kenar seritli PLAKET fiksturu (k = model olcegi; k=1 -> 120 mm): govde 120x120x3, Y en
 * kucuk kenarda 10 mm x 6,5 mm cerceve seridi, ortada 8,2 mm kabartma (seritten 15 mm sonra; X'te
 * kenardan 5 mm iceride -> yanlis eksende olcum kabartmayi yakalar).
 * Beklenen alt kenar: 6,5 mm (olcekten bagimsiz, olceklenmis dosyada).
 */
function plaketUcmf(k) {
  const kutular = [[-60, 60, -60, 60, 0, 3], [-60, 60, -60, -50, 0, 6.5], [-55, 55, -35, 50, 0, 8.2]];
  const t = [], u = [];
  kutular.forEach(([x0, x1, y0, y1, z0, z1], b) => {
    for (let i = 0; i < 8; i++) {
      t.push('     <vertex x="' + (i & 1 ? x1 : x0) * k + '" y="' + (i & 2 ? y1 : y0) * k + '" z="' + (i & 4 ? z1 : z0) * k + '"/>');
    }
    for (const g of [[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]]) {
      u.push('     <triangle v1="' + (g[0] + 8 * b) + '" v2="' + (g[1] + 8 * b) + '" v3="' + (g[2] + 8 * b) + '"/>');
    }
  });
  const sablon = testOlcAcik(ucmfKur(1, 1, 1));
  const nesne = sablon.get("3D/Objects/object_1.model")
    .replace(/<vertices>[\s\S]*<\/vertices>/, "<vertices>\n" + t.join("\n") + "\n    </vertices>")
    .replace(/<triangles>[\s\S]*<\/triangles>/, "<triangles>\n" + u.join("\n") + "\n    </triangles>");
  return zipYaz([...sablon].map(([ad, metin]) => [ad, ad === "3D/Objects/object_1.model" ? nesne : metin,
    ad === "Metadata/model_settings.config"]));
}
/** Zip -> ad -> acik metin (fikstur sablonu icin). */
function testOlcAcik(bayt) {
  const b = Buffer.from(bayt), acik = new Map();
  const e = b.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  let p = b.readUInt32LE(e + 16);
  for (let i = 0; i < b.readUInt16LE(e + 10); i++) {
    const ad = b.toString("utf8", p + 46, p + 46 + b.readUInt16LE(p + 28));
    const yontem = b.readUInt16LE(p + 10), cs = b.readUInt32LE(p + 20), yr = b.readUInt32LE(p + 42);
    const v = yr + 30 + b.readUInt16LE(yr + 26) + b.readUInt16LE(yr + 28);
    const ham = b.subarray(v, v + cs);
    acik.set(ad, (yontem === 8 ? zlib.inflateRawSync(ham) : ham).toString("utf8"));
    p += 46 + b.readUInt16LE(p + 28) + b.readUInt16LE(p + 30) + b.readUInt16LE(p + 32);
  }
  return acik;
}
// Varsayilan fikstur 100 mm (testlerdeki siparis olcusu) -> olcu kapisi dokunmaz (bayt-esit).
const UCMF = ucmfKur(50, 49, 7);
const UCMF_1094 = ucmfKur(547, 548.4, 75);     // 6 Eki gercek ornegin sinir kutusu
const UCMF_120 = ucmfKur(60, 58, 8);
const UCMF_BOZUK = new TextEncoder().encode("PK-sahte-3mf-govdesi-4-renk");
const UCMF_IKI_OGE = ucmfKur(547, 548.4, 75, true);
const GLB = new TextEncoder().encode("glTF-sahte-govde");
const GLB_DOKULU = new TextEncoder().encode("glTF-sahte-onarilmis-dokulu-govde");
const P = {
  cagri: [], bakiye: 1000, analiz: "healthy", turnstile: "ok", telegram: [], iyzico: [],
  protoDurum: new Map(),
  // ONARIM: analiz sonucu modele gore (onarilmis+dokulu model ayri sonuc verebilir).
  analizOnarim: null, analizModel: new Map(), onarimKod: 0,
  // A) WARNING+METRIK KUSUR: warning durumunda override metrik (figur ornegi).
  //    { degenerate_faces: 316227 } → status 'warning' + metrik kusurlu.
  //    { noMetrics: true } → status 'warning' + metrics alani YOK.
  analizMetrik: null,
};
let sayac = 0;
const yeniId = () => "gorev-" + String(++sayac).padStart(4, "0") + "-aaaa";
const yanit = (v, kod) => new Response(JSON.stringify(v), { status: kod || 200, headers: { "Content-Type": "application/json" } });

globalThis.fetch = async function sahteFetch(hedef, init) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  const yontem = (init && init.method) || "GET";
  if (u.startsWith(TABAN)) {
    const yol = u.slice(TABAN.length);
    P.cagri.push(yontem + " " + yol);
    if (yol === "/v1/balance") { return yanit({ balance: P.bakiye }); }
    let m;
    if (yontem === "POST" && /^\/tur-onek\/tur-plaket\/v1\/prototype$/.test(yol)) {
      const g = JSON.parse(init.body);
      if (!/^data:image\/png;base64,/.test(g.image_url)) { return yanit({ message: "bad" }, 400); }
      const id = yeniId(); P.protoDurum.set(id, 0); return yanit({ result: id });
    }
    if ((m = /^\/tur-onek\/tur-plaket\/v1\/prototype\/(.+)$/.exec(yol))) {
      const n = (P.protoDurum.get(m[1]) || 0) + 1; P.protoDurum.set(m[1], n);
      return n < 2 ? yanit({ id: m[1], status: "IN_PROGRESS", progress: 40 })
        : yanit({ id: m[1], status: "SUCCEEDED", consumed_credits: 6, image_urls: ["https://dosya.test/onizleme.png?Expires=1"] });
    }
    if (yontem === "POST" && /^\/tur-onek\/tur-plaket\/v1\/build$/.test(yol)) {
      const g = JSON.parse(init.body);
      P.sonBuild = g; return yanit({ result: yeniId() });
    }
    if (/\/v1\/build\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 30, model_urls: { glb: "https://dosya.test/model.glb?Expires=1" } });
    }
    if (yontem === "POST" && yol === "/v1/print/analyze") {
      const id = yeniId(); P.analizModel.set(id, JSON.parse(init.body).model_url); return yanit({ result: id });
    }
    if ((m = /^\/v1\/print\/analyze\/(.+)$/.exec(yol))) {
      const dokulu = /model-dokulu\.glb/.test(P.analizModel.get(m[1]) || "");
      const d = dokulu && P.analizOnarim ? P.analizOnarim : P.analiz;
      const pr = { status: d, error_count: d === "error" ? 1 : 0, warning_count: 0 };
      if (P.analizMetrik && d === "warning") {
        // A) WARNING+METRIK: override metrik (figur ornegi 8 Eki); noMetrics → alan YOK.
        if (!P.analizMetrik.noMetrics) {
          pr.metrics = {
            is_watertight: P.analizMetrik.is_watertight !== undefined ? P.analizMetrik.is_watertight : true,
            non_manifold_edges: P.analizMetrik.non_manifold_edges || 0,
            degenerate_faces: P.analizMetrik.degenerate_faces || 0,
            holes: P.analizMetrik.holes || 0,
          };
        }
      } else {
        pr.metrics = { is_watertight: d !== "error", non_manifold_edges: d === "error" ? 12 : 0,
                       degenerate_faces: 0, holes: 0 };
      }
      return yanit({ status: "SUCCEEDED", consumed_credits: 0, printability: pr });
    }
    if (yontem === "POST" && yol === "/v1/print/repair") {
      if (P.onarimKod) { return yanit({ message: "x" }, P.onarimKod); }
      P.sonOnarim = JSON.parse(init.body); return yanit({ result: yeniId() });
    }
    if (/^\/v1\/print\/repair\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 10, texture_urls: [],
                     model_urls: { glb: "https://dosya.test/onarilmis.glb?Expires=1", stl: "" } });
    }
    if (yontem === "POST" && yol === "/v1/retexture") { P.sonDoku = JSON.parse(init.body); return yanit({ result: yeniId() }); }
    if (/^\/v1\/retexture\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 10, model_urls: { glb: "https://dosya.test/model-dokulu.glb?Expires=1" } });
    }
    if (yontem === "POST" && yol === "/v1/print/multi-color") { P.sonRenk = JSON.parse(init.body); return yanit({ result: yeniId() }); }
    if (/^\/v1\/print\/multi-color\/.+$/.test(yol)) {
      return yanit({ status: "SUCCEEDED", consumed_credits: 10, model_urls: { "3mf": "https://dosya.test/model.3mf?Expires=1" } });
    }
    return yanit({ message: "bilinmeyen" }, 404);
  }
  if (u.startsWith("https://dosya.test/onizleme.png")) { return new Response(PNG, { headers: { "Content-Type": "image/png", "Content-Length": String(PNG.length) } }); }
  if (u.startsWith("https://dosya.test/model.3mf")) { return new Response(P.ucmf || UCMF, { headers: { "Content-Type": "application/octet-stream" } }); }
  if (u.startsWith("https://dosya.test/model-dokulu.glb")) { return new Response(GLB_DOKULU, { headers: { "Content-Type": "model/gltf-binary" } }); }
  if (u.startsWith("https://dosya.test/model.glb")) { return new Response(GLB, { headers: { "Content-Type": "model/gltf-binary" } }); }
  if (u.includes("challenges.cloudflare.com/turnstile")) {
    P.cagri.push("TURNSTILE");
    if (P.turnstile === "ag") { throw new Error("ag yok"); }
    return yanit(P.turnstile === "ok" ? { success: true, hostname: "pruvo3d.com" } : { success: false, "error-codes": ["x"] });
  }
  if (u.startsWith("https://telegram.test")) { P.telegram.push(JSON.parse(init.body).text); return yanit({ ok: true }); }
  if (u.startsWith("https://iyzico.test")) {
    P.iyzico.push(JSON.parse(init.body));
    return yanit({ status: "success", token: "iyz-" + P.iyzico.length, paymentPageUrl: "https://odeme.test/sayfa" });
  }
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

// ---------------------------------------------------------------- ortam

const limiter = () => ({ limit: async () => ({ success: true }) });
function envKur(d1, r2, ek) {
  return {
    KATALOG: d1, OZEL_DOSYA: r2, SITE_URL: "https://pruvo3d.com",
    IYZICO_BASE_URL: "https://iyzico.test", IYZICO_API_KEY: "k", IYZICO_SECRET_KEY: "s",
    TELEGRAM_TOKEN: "t", TELEGRAM_API: "https://telegram.test", TELEGRAM_CHAT: "1",
    TURNSTILE_SECRET: "ts", YONET_ANAHTAR: "yonet-test-anahtari",
    BASLAT_RATE_LIMIT: limiter(), FIYAT_RATE_LIMIT: limiter(), FOTO_RATE_LIMIT: limiter(),
    URETIM_API_TABAN: TABAN, URETIM_TUR_ONEK: "tur-onek",
    URETIM_TUR_PLAKET: "tur-plaket", URETIM_TUR_FIGUR: "tur-figur",
    URETIM_API_ANAHTAR: "sahte-anahtar",
    ...(ek || {}),
  };
}
const ctx = { bekleyen: [], waitUntil(p) { this.bekleyen.push(p); } };

const B64 = Buffer.from(Uint8Array.from([...PNG, ...new Array(4096).fill(3)])).toString("base64");
const GORSEL = "data:image/png;base64," + B64;
const SAHTE_GORSEL = "data:image/png;base64," + Buffer.from(new Uint8Array(4200).fill(65)).toString("base64");

let modul, foto;
try {
  modul = (await import(url.pathToFileURL(path.join(SHOP, "src", "index.js")).href)).default;
  foto = await import(url.pathToFileURL(path.join(SHOP, "src", "foto.js")).href);
} catch (e) {
  console.log("OLCULEMEDI: worker modulu yuklenemedi — " + ((e && e.stack) || e));
  process.exit(3);
}
const VERI = globalThis.PRUVO_FOTO;

async function istek(env, yol, o) {
  o = o || {};
  const basliklar = { "CF-Connecting-IP": o.ip || "198.51.100.7", ...(o.basliklar || {}) };
  if (o.govde) { basliklar["Content-Type"] = "application/json"; }
  const r = await modul.fetch(new Request("https://pruvo3d.com/api/shop" + yol, {
    method: o.yontem || (o.govde ? "POST" : "GET"), headers: basliklar,
    body: o.govde ? JSON.stringify(o.govde) : undefined }), env, ctx);
  let v = null; const tip = r.headers.get("Content-Type") || "";
  if (tip.includes("json")) { try { v = await r.json(); } catch (e) { v = null; } }
  return { kod: r.status, v, r };
}
const YONET = { "X-Yonet-Anahtar": "yonet-test-anahtari" };
const onizlemeGovde = (ek) => ({ tur: "plaket", olcu_mm: 100, gorsel: GORSEL, aydinlatma_onay: true,
  onay_surum: VERI.onay_surum, turnstile_token: "jeton", ...(ek || {}) });
const protoSayisi = () => P.cagri.filter((c) => /^POST .*\/v1\/prototype$/.test(c)).length;

// ================================================================ ANA KOSUM

const kopru = koprukur();
const ilk = await kopru.hazir;
if (!ilk || !ilk.hazir) { console.log("OLCULEMEDI: SQLite koprusu kurulamadi — " + JSON.stringify(ilk)); process.exit(3); }
const d1 = kopru.d1;
const r2 = r2Kur();
const env = envKur(d1, r2);

// A/B kapali-varsayilani ORNEK 0 iken olcer; veri dosyasindaki kayitlar (7 Eki render ornegi)
// RO bolumunde dosyanin TEMIZ kopyasindan olculur.
const VERI_ORNEKLERI = VERI.ornekler.splice(0);
console.log("A) KAPALI-VARSAYILAN (ornek 0)");
{
  const y = foto.yapilandirma(env);
  // Onay metni Okan'ca onaylandi (6 Eki); eksik listesi onay kolunu veri dosyasina gore yazar.
  ol("A1 gercek ornek 0 -> yapilandirma HAZIR DEGIL (onay eksigi yalniz onaysizken listelenir)",
     !y.hazir && y.eksik.includes("gercek-ornek") &&
       y.eksik.includes("onay-metni-onayi") === (VERI.onay_onayli !== true), JSON.stringify(y));
  // A1b: onay kapisi veri dosyasinin bugunku halinden BAGIMSIZ olculur (onaysiz -> eksik).
  const onayOnce = VERI.onay_onayli;
  VERI.onay_onayli = false;
  const yb = foto.yapilandirma(env);
  VERI.onay_onayli = onayOnce;
  ol("A1b onay bayragi kapali -> eksik listesinde onay-metni-onayi VAR, hazir DEGIL",
     !yb.hazir && yb.eksik.includes("onay-metni-onayi"), JSON.stringify(yb));
  const a = await istek(env, "/foto/acik");
  ol("A2 /foto/acik -> acik:false", a.kod === 200 && a.v && a.v.acik === false, JSON.stringify(a.v));
  const o = await istek(env, "/foto/onizleme", { govde: onizlemeGovde() });
  ol("A3 /foto/onizleme -> 503 kapali, saglayiciya istek YOK", o.kod === 503 && protoSayisi() === 0, o.kod);
  const c = await foto.fotoUretimTuru(envKur(d1, r2, { URETIM_API_ANAHTAR: "" }), Date.now(), null);
  ol("A4 anahtarsiz cron D1'e dokunmadan ATLAR", c.atlandi === "yapilandirma", JSON.stringify(c));
  // 8 Eki: tek turun yolu eksikse YALNIZ o tur kapanir (turHazir); hicbir yol yoksa bolum + cron kapali.
  const plaketYolsuz = envKur(d1, r2, { URETIM_TUR_PLAKET: "" });
  const yolsuz = envKur(d1, r2, { URETIM_TUR_PLAKET: "", URETIM_TUR_FIGUR: "" });
  ol("A5 plaket yolu yoksa turHazir(plaket) 'tur-yolu-plaket'; hicbir yol yoksa yapilandirma eksik + cron ATLAR",
     foto.turHazir(plaketYolsuz, "plaket").eksik.includes("tur-yolu-plaket") &&
     foto.yapilandirma(yolsuz).eksik.includes("tur-yolu-plaket") &&
     (await foto.fotoUretimTuru(yolsuz, Date.now(), null)).atlandi === "yapilandirma",
     JSON.stringify(foto.yapilandirma(yolsuz).eksik));
}

console.log("P) TUR LISTESI — tek tur PLAKET (Okan 5 Eki 21:4x; anahtarlik/magnet SUNULMAZ)");
{
  // 6 Eki (kategori kaydi): tek-tur sozlesmesi yerine "metal gerektiren tur 0 + plaket VAR".
  // 8 Eki (saglayici kopru-15): FIGÜR saglayici kolunda IKINCI tur olarak eklendi; metal gerektiren
  // turler (anahtarlik/magnet) yok, figür VAR (ornek yoksa Acilis anahtari olmadan SUNULMAZ).
  ol("P1 veri dosyasinda anahtarlik/magnet 0 ve plaket + figur VAR",
     VERI.turler.some((t) => t.kod === "plaket") && VERI.turler.some((t) => t.kod === "figur") &&
       !VERI.turler.some((t) => ["anahtarlik", "magnet"].includes(t.kod)),
     JSON.stringify(VERI.turler.map((t) => t.kod)));
  // P2: figur ornegi YOK (varsayilan), bu testte /foto/acik henuz figur'u acmadi; SUNUCU tur tablosu
  //     yine de figur'u BILIR (TUR_ORTAM'da) — yalniz acilis anahtari ile gorunur.
  ol("P2 sunucu tur tablosu plaket + figur (anahtarlik/magnet 0)",
     JSON.stringify(Object.keys(foto.TUR_ORTAM)) === '["plaket","figur"]', JSON.stringify(Object.keys(foto.TUR_ORTAM)));
  ol("P3 saglayici tur yolu kodda DEGIL, ortam degiskeninden (deger dizesi 'URETIM_' ile baslar)",
     Object.values(foto.TUR_ORTAM).every((v) => /^URETIM_TUR_[A-Z]+$/.test(v)), JSON.stringify(foto.TUR_ORTAM));
  // P8/P9 (8 Eki): yeni turun sirri henuz konmadiysa YALNIZ o tur kapanir; global sart "en az bir yol".
  const yolsuzFigur = envKur(null, null, { URETIM_TUR_FIGUR: "" });
  const gEksik = foto.yapilandirma(yolsuzFigur).eksik.filter((e) => e.startsWith("tur-yolu"));
  const fEksik = foto.turHazir(yolsuzFigur, "figur").eksik;
  const pEksik = foto.turHazir(yolsuzFigur, "plaket").eksik.filter((e) => e.startsWith("tur-yolu"));
  ol("P8 figur yolu yokken global tur-yolu eksigi 0, plaket tur-yolu eksigi 0, figur 'tur-yolu-figur'",
     gEksik.length === 0 && pEksik.length === 0 && fEksik.includes("tur-yolu-figur"),
     JSON.stringify({ gEksik, pEksik, fEksik }));
  // P10 (8 Eki, saglayici figur belgesi): figur build govdesi YALNIZ input_task_id + name (options yok);
  // plaket govdesi kabartma/taban/sekil secenekleriyle AYNEN.
  const bf = foto.buildGovdesi({ tur: "figur", siparis_no: "S1", olcu_mm: 120 }, "g1");
  const bp = foto.buildGovdesi({ tur: "plaket", siparis_no: "S2", olcu_mm: 150 }, "g2");
  ol("P10 build govdesi ture gore: figur options YOK, plaket size_mm+kabartma+sekil VAR",
     JSON.stringify(Object.keys(bf).sort()) === '["input_task_id","name"]' &&
       bp.options && bp.options.size_mm === 150 && bp.options.has_closed_back === true &&
       bp.input_task_id === "g2",
     JSON.stringify({ bf, bp }));
  const yolsuz = envKur(null, null, { URETIM_TUR_FIGUR: "", URETIM_TUR_PLAKET: "" });
  ol("P9 hicbir tur yolu yoksa global eksik tur-yolu-plaket + tur-yolu-figur (bolum KAPALI)",
     ["tur-yolu-plaket", "tur-yolu-figur"].every((e) => foto.yapilandirma(yolsuz).eksik.includes(e)),
     JSON.stringify(foto.yapilandirma(yolsuz).eksik));
}

// Bolumu ac: onay onayli + ONCE baski fotografi EKSIK bir ornek (gercek ornek SAYILMAZ).
VERI.onay_onayli = true;
VERI.ornekler.push({ tur: "plaket", olcu_mm: 120, foto: "https://media.pruvo3d.com/y-foto.webp",
  onizleme: "https://media.pruvo3d.com/y-oniz.webp", baski: "", not: "baski fotografi YOK" });

console.log("B) ACILIS ANAHTARI + TEK FORMUL (Okan 7 Eki 15:4x: fiyat tablosu YOK)");
{
  const a = await istek(env, "/foto/acik");
  ol("B1 acilis anahtari yok (foto_acik bos) -> acik:false (tur sunulmaz)", a.v && a.v.acik === false, JSON.stringify(a.v));
  const y1 = await istek(env, "/yonet/foto-acik", { govde: { tur: "plaket", acik: true }, basliklar: YONET });
  const yetkisiz = await istek(env, "/yonet/foto-acik", { govde: { tur: "litofan", acik: true } });
  ol("B2 panel acilis anahtari yazar (anahtarli 200, anahtarsiz 404)", y1.kod === 200 && yetkisiz.kod === 404,
     y1.kod + "/" + yetkisiz.kod);
  const a1 = await istek(env, "/foto/acik");
  ol("B4 baski fotografi eksik ornek SAYILMAZ -> anahtar acik olsa da acik:false (gercek ornek 0)",
     a1.v && a1.v.acik === false, JSON.stringify(a1.v));
  VERI.ornekler.push({ tur: "plaket", olcu_mm: 100, foto: "https://media.pruvo3d.com/x-foto.webp",
    onizleme: "https://media.pruvo3d.com/x-oniz.webp", baski: "https://media.pruvo3d.com/x-baski.webp", not: "t" });
  const a2 = await istek(env, "/foto/acik");
  const turler = (a2.v && a2.v.turler) || [];
  const pl = turler.find((t) => t.kod === "plaket");
  ol("B3 acik:true; plaket olculeri FORMULDEN (100 mm = 100000 kurus, her olcu max(60000, mm x 1000), 10..300 adim 10)",
     a2.v && a2.v.acik === true && !!pl && pl.olculer.length === 30 &&
     pl.olculer.every((o) => o.fiyat_kurus === Math.max(o.mm * 1000, 60000) && o.fiyat_kurus === VERI.fiyatKurus("plaket", o.mm)) &&
     pl.olculer.some((o) => o.mm === 100 && o.fiyat_kurus === 100000), JSON.stringify(a2.v));
  ol("P4 /foto/acik sunulan tur sayisi 1 (plaket)", turler.length === 1 && turler[0].kod === "plaket",
     JSON.stringify(turler.map((t) => t.kod)));
  const kotu = await istek(env, "/yonet/foto-acik", { govde: { tur: "plaket", acik: "evet" }, basliklar: YONET });
  ol("B5 acik alani boolean degilse 400 (gecersiz-acik)", kotu.kod === 400 && kotu.v.hata === "gecersiz-acik", JSON.stringify(kotu.v));
  // 8 Eki: figur artik gecerli bir tur (acilis anahtari ile); metal gerektiren turler ACILAMAZ.
  const red = [];
  for (const t of ["anahtarlik", "magnet"]) {
    const r = await istek(env, "/yonet/foto-acik", { govde: { tur: t, acik: true }, basliklar: YONET });
    if (r.kod === 400 && r.v && r.v.hata === "gecersiz-tur") { red.push(t); }
  }
  ol("P5 panel acilis: anahtarlik/magnet ACILAMAZ (figur gecerli tur)", red.length === 2, red.join(","));
  const tablo = await d1.prepare("SELECT COUNT(*) AS n FROM foto_acik WHERE tur <> 'plaket'").first();
  ol("P5b acilis anahtarinda plaket disi satir 0", tablo.n === 0, tablo.n);
  const oz = await istek(env, "/yonet/foto-ozet", { basliklar: YONET });
  ol("P6 panel ozeti sunulan turleri sunucudan verir: kayittaki turler (panel tur listesi elle yazilmaz)",
     oz.v && JSON.stringify(oz.v.sunulan_turler.map((t) => t.kod)) === JSON.stringify(VERI.turler.map((t) => t.kod)) &&
     oz.v.olcu_en_az === foto.OLCU_MM_EN_AZ && oz.v.ayak_plaket_basi === 1, JSON.stringify(oz.v && oz.v.sunulan_turler));
  ol("B6 panel ozeti acilis anahtarini verir (acik = [plaket]), fiyat tablosu alani YOK",
     oz.v && JSON.stringify(oz.v.acik) === JSON.stringify(["plaket"]) && !("fiyatlar" in oz.v), JSON.stringify(oz.v && oz.v.acik));
}

console.log("C/F) ONIZLEME + ONAY + GORSEL");
let isNo;
{
  const once = protoSayisi();
  const r1 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ aydinlatma_onay: false }) });
  const r2_ = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ onay_surum: "eski" }) });
  const r3 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ gorsel: SAHTE_GORSEL }) });
  const r4 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ olcu_mm: 55 }) });
  const r5 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "magnet", olcu_mm: 100 }) });
  const r6 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "anahtarlik", olcu_mm: 100 }) });
  ol("F1 aydinlatma onayi yok -> 400 onay-yok", r1.kod === 400 && r1.v.hata === "onay-yok", JSON.stringify(r1.v));
  ol("F2 eski onay surumu -> 400 onay-surumu-eski", r2_.kod === 400 && r2_.v.hata === "onay-surumu-eski", JSON.stringify(r2_.v));
  ol("F3 sihirli bayti tutmayan gorsel -> 400 gorsel-gecersiz", r3.kod === 400 && r3.v.hata === "gorsel-gecersiz", JSON.stringify(r3.v));
  ol("F4 tabloda olmayan olcu -> 400", r4.kod === 400 && r4.v.hata === "gecersiz-olcu", JSON.stringify(r4.v));
  ol("F5 sunulmayan tur magnet -> 400 tur-kapali", r5.kod === 400 && r5.v.hata === "tur-kapali", JSON.stringify(r5.v));
  ol("P7 sunulmayan tur anahtarlik -> 400 tur-kapali", r6.kod === 400 && r6.v.hata === "tur-kapali", JSON.stringify(r6.v));
  ol("F6 reddedilen isteklerin hicbiri saglayiciya GITMEDI", protoSayisi() === once, protoSayisi() - once);

  const ok = await istek(env, "/foto/onizleme", { govde: onizlemeGovde() });
  isNo = ok.v && ok.v.is;
  ol("C1 gecerli istek -> 200 + 32 hex is anahtari", ok.kod === 200 && /^[a-f0-9]{32}$/.test(isNo || ""), JSON.stringify(ok.v));
  ol("C2 saglayiciya tur oneki + urun yoluyla TEK onizleme istegi", protoSayisi() === once + 1 &&
     P.cagri.includes("POST /tur-onek/tur-plaket/v1/prototype"), P.cagri.slice(-3).join(" | "));
  const d0 = await istek(env, "/foto/durum?is=" + isNo);
  ol("C3 ilk yoklama: suruyor", d0.v && d0.v.asama === "onizleme", JSON.stringify(d0.v));
  const yoklamaOnce = P.cagri.length;
  await istek(env, "/foto/durum?is=" + isNo);
  ol("C4 2,5 sn icindeki ikinci yoklama saglayiciya GITMEZ", P.cagri.length === yoklamaOnce, P.cagri.length - yoklamaOnce);
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(isNo).run();
  const d1r = await istek(env, "/foto/durum?is=" + isNo);
  ol("C5 hazir: gorsel BIZIM ucumuzdan (saglayici adresi tarayiciya verilmez)",
     d1r.v && d1r.v.asama === "hazir" && d1r.v.gorsel === "/api/shop/foto/gorsel?is=" + isNo, JSON.stringify(d1r.v));
  const g = await istek(env, "/foto/gorsel?is=" + isNo);
  const bayt = new Uint8Array(await g.r.arrayBuffer());
  ol("C6 /foto/gorsel onizlemeyi ozel kovadan sunar", g.kod === 200 && bayt.length === PNG.length, g.kod + "/" + bayt.length);
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(isNo).run();
  await istek(env, "/foto/durum?is=" + isNo);
  const k = await d1.prepare("SELECT COUNT(*) AS n, SUM(kredi) AS t FROM foto_kredi WHERE is_no = ?").bind(isNo).first();
  ol("C7 onizleme kredisi defterde TEK satir (6)", k.n === 1 && k.t === 6, JSON.stringify(k));
  const yok = await istek(env, "/foto/gorsel?is=" + "0".repeat(32));
  ol("C8 bilinmeyen is anahtari -> 404", yok.kod === 404, yok.kod);
}

console.log("D) ZIYARETCI SINIRI (sinir+1 RED)");
{
  const ip = "203.0.113.9";
  const sinir = VERI.sinir_ziyaretci_24s;
  const kodlar = [];
  for (let i = 0; i < sinir; i++) { kodlar.push((await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() })).kod); }
  const once = protoSayisi();
  const fazla = await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() });
  ol("D1 ilk " + sinir + " istek 200", kodlar.every((k) => k === 200), kodlar.join(","));
  ol("D2 " + (sinir + 1) + ". istek 429 onizleme-siniri ve saglayiciya GITMEZ",
     fazla.kod === 429 && fazla.v.hata === "onizleme-siniri" && protoSayisi() === once, fazla.kod + "/" + JSON.stringify(fazla.v));
  const baska = await istek(env, "/foto/onizleme", { ip: "203.0.113.10", govde: onizlemeGovde() });
  ol("D3 baska ziyaretci etkilenmez", baska.kod === 200, baska.kod);
  const ham = await d1.prepare("SELECT COUNT(*) AS n FROM foto_isler WHERE ziyaretci LIKE '%203.0.113%'").first();
  ol("D4 ham IP veritabanina YAZILMAZ", ham.n === 0, ham.n);
}

console.log("E) BOT KAPISI (fail-closed)");
for (const [mod, ad] of [["red", "red"], ["ag", "ag hatasi"]]) {
  P.turnstile = mod;
  const once = protoSayisi();
  const r = await istek(env, "/foto/onizleme", { ip: "192.0.2." + (mod === "red" ? 1 : 2), govde: onizlemeGovde() });
  ol("E dogrulayici " + ad + " -> 403, saglayiciya gitmez", r.kod === 403 && protoSayisi() === once, r.kod);
}
P.turnstile = "ok";
{
  const r = await istek(env, "/foto/onizleme", { ip: "192.0.2.3", govde: onizlemeGovde({ turnstile_token: "" }) });
  ol("E jeton bos -> 403", r.kod === 403, r.kod);
}

console.log("H) /baslat FOTO KALEMI");
const musteri = { ad: "Deneme Musteri", tel: "05000000000", eposta: "deneme@ornek.test", adres: "Deneme mahallesi 1", sehir: "Ankara" };
let siparisNo;
{
  const once = P.iyzico.length;
  const h = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "havale", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
  ol("H1 havale -> 400 foto-havale-yok", h.kod === 400 && h.v.hata === "foto-havale-yok", JSON.stringify(h.v));
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1, fiyat_kurus: 1, renkler: ["Beyaz", "Siyah"] }] } });
  siparisNo = b.v && b.v.no;
  const iy = P.iyzico[P.iyzico.length - 1] || {};
  ol("H2 kart -> 200, iyzico tutari SUNUCU FORMULUNDEN (100 mm x 10 TL = 1.000 + 1 ek renk 100 = 1.100,00 + 250,00 kargo); istemci fiyat_kurus OKUNMAZ",
     b.kod === 200 && P.iyzico.length === once + 1 && iy.price === "1350.00", JSON.stringify(b.v) + " price=" + iy.price);
  const s = await d1.prepare("SELECT durum, urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(siparisNo).first();
  const kalem = s && JSON.parse(s.urunler)[0];
  ol("H3 siparis 'bekliyor', kalem foto_is/tur(plaket)/olcu + foto_ayak 1 + foto_renkler [Beyaz,Siyah] tasir", s && s.durum === "bekliyor" &&
     s.tutar_kurus === 110000 && kalem.foto_is === isNo && kalem.foto_tur === "plaket" && kalem.olcu_mm === 100 && kalem.foto_ayak === 1 &&
     JSON.stringify(kalem.foto_renkler) === '["Beyaz","Siyah"]' && kalem.renk === "Beyaz, Siyah" &&
     /2 renkli yorumu · ek renk ×1: 100 TL/.test(kalem.parametre_detay), JSON.stringify(s));
  const eski = await istek(env, "/foto/onizleme", { ip: "198.51.100.77", govde: onizlemeGovde() });
  await d1.prepare("UPDATE foto_isler SET asama = 'hazir', hazir_tarih = '2020-01-01T00:00:00.000Z' WHERE is_no = ?").bind(eski.v.is).run();
  const e = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: eski.v.is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
  ol("H4 suresi dolmus onizleme -> 400", e.kod === 400 && e.v.hata === "foto-onizleme-suresi-doldu", JSON.stringify(e.v));
  const yok = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: "f".repeat(32), olcu_mm: 100, adet: 1 }] } });
  ol("H5 olmayan onizleme -> 400", yok.kod === 400 && yok.v.hata === "foto-onizleme-yok", JSON.stringify(yok.v));
}

console.log("I) URETIM ZINCIRI");
const cron = async () => modul.scheduled({ cron: "*/5 * * * *", scheduledTime: Date.now() }, env, ctx);
{
  await cron();
  const bos = await d1.prepare("SELECT COUNT(*) AS n FROM foto_uretim").first();
  ol("I1 'bekliyor' siparis uretime GIRMEZ (odeme dogrulanmadan kredi harcanmaz)", bos.n === 0, bos.n);
  await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(siparisNo).run();
  for (let i = 0; i < 4; i++) { await cron(); }
  const u = await d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(siparisNo).first();
  // ONARIM KAPISI (8 Eki 2026): saglayici zinciri 'hazir' DEGIL 'onarim-bekliyor'da biter; ham 3MF
  // model.ham.3mf'te, model.3mf YOK. 'hazir'i yalniz yerel kosucu (onarim kuyrugu) yazar — asagida taklit.
  ol("I2 dort turda zincir 'onarim-bekliyor' (saglayici 3MF'i dogrudan teslim EDILMEZ)",
     u && u.asama === "onarim-bekliyor", JSON.stringify(u));
  const op = (P.sonBuild && P.sonBuild.options) || {};
  ol("I3 model adimina olcu mm ile gidildi", op.size_mm === 100, JSON.stringify(P.sonBuild));
  ol("I3b plaket geometrisi: kabartma + taban kalinligi sabit, kapali duz sirt (delme yok)",
     op.relief_height_mm === foto.PLAKET_KABARTMA_MM && op.base_thickness_mm === foto.PLAKET_TABAN_MM &&
     op.has_closed_back === true && op.badge_shape === foto.PLAKET_SEKIL, JSON.stringify(op));
  ol("I4 renk adimi SIPARISIN renk sayisi (2) + bambu", P.sonRenk && P.sonRenk.max_colors === 2 && P.sonRenk.printer_brand === "bambu", JSON.stringify(P.sonRenk));
  const k3 = r2.m.get("foto/" + siparisNo + "/0/model.ham.3mf");
  ol("I5 ham 3MF + GLB BIZIM ozel kovada, model.3mf YAZILMADI",
     k3 && k3.bayt.length === UCMF.length && r2.m.has("foto/" + siparisNo + "/0/model.glb") &&
     !r2.m.has("foto/" + siparisNo + "/0/model.3mf"), [...r2.m.keys()].join(","));
  const kr = await d1.prepare("SELECT COALESCE(SUM(kredi),0) AS t FROM foto_kredi WHERE siparis_no = ? OR (adim = 'onizleme' AND is_no = ?)").bind(siparisNo, isNo).first();
  ol("I6 siparisin kredi kaydi 46 (6 onizleme + 30 model + 0 analiz + 10 renk)", kr.t === 46, kr.t);
  ol("I7 'onarim kapisinda' bildirimi Telegram'a bir kez, HAZIR denmez",
     P.telegram.filter((t) => t.includes("onarım kapısında") && t.includes(siparisNo)).length === 1 &&
     P.telegram.filter((t) => t.includes("HAZIR") && t.includes(siparisNo)).length === 0, P.telegram.join(" | "));
  const l0 = await istek(env, "/yonet/liste", { basliklar: YONET });
  const f0 = l0.v && l0.v.siparisler.find((x) => x.siparis_no === siparisNo).kalemler[0].foto;
  ol("I7b onarim-bekliyor kalemde panel dosya baglantisi VERMEZ (fail-closed)",
     f0 && f0.asama === "onarim-bekliyor" && f0.dosyalar === null, JSON.stringify(f0));
  const once0 = P.cagri.length;
  await cron();
  ol("I7c onarim-bekliyor satir Worker'da islenmez (saglayiciya istek yok, asama ayni)",
     P.cagri.length === once0 &&
     (await d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ?").bind(siparisNo).first()).asama ===
       "onarim-bekliyor", P.cagri.slice(once0).join(","));
  // Yerel kosucu taklidi (tools/foto-uretec-kosucu.py onarim kuyrugu: kopru + olcum gecti).
  r2.m.set("foto/" + siparisNo + "/0/model.3mf", k3);
  await d1.prepare("UPDATE foto_uretim SET asama = 'hazir' WHERE siparis_no = ? AND asama = 'onarim-bekliyor'")
    .bind(siparisNo).run();
  const l = await istek(env, "/yonet/liste", { basliklar: YONET });
  const sip = l.v && l.v.siparisler.find((x) => x.siparis_no === siparisNo);
  const f = sip && sip.kalemler[0].foto;
  ol("I8 panel listesi kalemin yaninda 3MF/GLB baglantisi", f && f.asama === "hazir" && f.dosyalar && /bicim=3mf/.test(f.dosyalar["3mf"]), JSON.stringify(f));
  ol("I8b panelde AYAK: kalem ayak 1 + baski notunda 'AYAK: 1 adet' (uretimde unutulmasin)",
     f && f.ayak === 1 && /AYAK: 1 adet/.test(sip.kalemler[0].baski_oneri || ""), sip && sip.kalemler[0].baski_oneri);
  const ind = await istek(env, f.dosyalar["3mf"].replace("/api/shop", ""), { basliklar: YONET });
  const indBayt = new Uint8Array(await ind.r.arrayBuffer());
  ol("I9 panelden 3MF indirilir (anahtarli), anahtarsiz 404", ind.kod === 200 && indBayt.length === UCMF.length &&
     /attachment/.test(ind.r.headers.get("Content-Disposition") || "") &&
     (await istek(env, f.dosyalar["3mf"].replace("/api/shop", ""))).kod === 404, ind.kod);
  const once = P.cagri.length;
  await cron();
  ol("I10 hazir satir tekrar islenmez (saglayiciya yeni istek yok)", P.cagri.length === once, P.cagri.slice(once).join(","));
}

console.log("J) ANALIZ KIRMIZI");
let siparis2;
{
  const ok = await istek(env, "/foto/onizleme", { ip: "198.51.100.88", govde: onizlemeGovde() });
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
  await istek(env, "/foto/durum?is=" + ok.v.is);
  await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
  await istek(env, "/foto/durum?is=" + ok.v.is);
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: ok.v.is, olcu_mm: 100, adet: 2, renkler: ["Beyaz"] }] } });
  siparis2 = b.v && b.v.no;
  await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(siparis2).run();
  P.analiz = "error";
  const renkOnce = P.cagri.filter((c) => c === "POST /v1/print/multi-color").length;
  const onarimOnce = P.cagri.filter((c) => c === "POST /v1/print/repair").length;
  for (let i = 0; i < 8; i++) { await cron(); }
  const u = await d1.prepare("SELECT asama, sebep, analiz FROM foto_uretim WHERE siparis_no = ?").bind(siparis2).first();
  // 8 Eki 2026 (BaBa hukmu, yerel onarim koprusu): onarim SONRASI da kirmizi -> eskiden 'elle analiz-kirmizi'
  // (renk KOSMAZDI). Artik renk KOSAR, ham 3MF 'onarim-bekliyor'a duser; teslim kararini yerel kopru+olcum verir.
  ol("J1 onarim sonrasi da kirmizi -> 'onarim-bekliyor' (elle DEGIL; dosya teslim edilmedi)",
     u && u.asama === "onarim-bekliyor" && !r2.m.has("foto/" + siparis2 + "/0/model.3mf") &&
     r2.m.has("foto/" + siparis2 + "/0/model.ham.3mf"), JSON.stringify(u));
  ol("J2 renk adimi KOSTU (tek kez)", P.cagri.filter((c) => c === "POST /v1/print/multi-color").length === renkOnce + 1, "");
  ol("J3 Worker ELLE/HAZIR bildirimi YOK, 'onarim kapisinda' bir kez",
     P.telegram.filter((t) => (t.includes("ELLE") || t.includes("HAZIR")) && t.includes(siparis2)).length === 0 &&
     P.telegram.filter((t) => t.includes("onarım kapısında") && t.includes(siparis2)).length === 1, "");
  ol("J5 kirmizida satir basina TEK onarim denendi (tavan)", P.cagri.filter((c) => c === "POST /v1/print/repair").length === onarimOnce + 1, "");
  // Yerel kosucu taklidi: kopru/olcum KIRMIZI -> 'elle onarim-kirmizi' (M1 ozetinin elle kalemi).
  await d1.prepare("UPDATE foto_uretim SET asama = 'elle', sebep = 'onarim-kirmizi' WHERE siparis_no = ?")
    .bind(siparis2).run();
  P.analiz = "healthy";
  const l = await istek(env, "/yonet/liste", { basliklar: YONET });
  const sip = l.v && l.v.siparisler.find((x) => x.siparis_no === siparis2);
  ol("J4 adet 2 -> panel notu 'AYAK: 2 adet' (plaket basina 1)",
     sip && /AYAK: 2 adet/.test(sip.kalemler[0].baski_oneri || ""), sip && sip.kalemler[0].baski_oneri);
}

console.log("G) HAVUZ ESIGI");
{
  P.bakiye = 100;
  await d1.prepare("UPDATE foto_ayar SET guncel = 0 WHERE anahtar = 'bakiye'").run();
  const once = P.telegram.length;
  const a = await istek(env, "/foto/acik");
  const o = await istek(env, "/foto/onizleme", { ip: "198.51.100.99", govde: onizlemeGovde() });
  ol("G1 bakiye esik altinda -> /acik false + onizleme 503", a.v.acik === false && o.kod === 503, a.v.acik + "/" + o.kod);
  ol("G2 Okan'a TEK bildirim (iki istek, bir mesaj)", P.telegram.length === once + 1 && /KAPANDI/.test(P.telegram[once]), P.telegram.length - once);
  P.bakiye = 1000;
  await d1.prepare("UPDATE foto_ayar SET guncel = 0 WHERE anahtar = 'bakiye'").run();
  const a2 = await istek(env, "/foto/acik");
  ol("G3 kredi gelince bolum kendiliginden acilir", a2.v.acik === true, JSON.stringify(a2.v.acik));
}

console.log("M) PANEL OZETI");
{
  const o = await istek(env, "/yonet/foto-ozet", { basliklar: YONET });
  const t = o.v && o.v.turler.find((x) => x.tur === "plaket");
  ol("M1 tur basina kalem 2 / hazir 1 / elle 1", t && t.kalem === 2 && t.hazir === 1 && t.elle === 1, JSON.stringify(t));
  ol("M2 aylik kredi sayilir (>= 46)", o.v.kredi.bu_ay >= 46, JSON.stringify(o.v.kredi));
  ol("M3 ozet anahtarsiz 404", (await istek(env, "/yonet/foto-ozet")).kod === 404, "");
}

console.log("Q) SUNULMAYAN TUR — sunucu reddi (eski/elle yazilmis kayit uzerinden)");
{
  const simdiIso = new Date().toISOString();
  const isA = "a".repeat(32);
  await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'anahtarlik', 100, 'z', ?, 'hazir', 'gorev-eski-0001', ?)")
    .bind(isA, simdiIso, simdiIso).run();
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isA, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
  ol("Q1 anahtarlik onizlemesinden /baslat -> 400 foto-kapali (odeme baslamaz)", b.kod === 400 && b.v.hata === "foto-kapali", JSON.stringify(b.v));
  await d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES ('PR-TEST-MAGNET', ?, 'odendi', 1, ?)")
    .bind(simdiIso, JSON.stringify([{ id: "ozel-foto-magnet", foto_is: isA, foto_tur: "magnet", olcu_mm: 100 }])).run();
  await d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-TEST-ANAHT', 0, ?, 'anahtarlik', 100, 'build-baslat', ?, '2000-01-01T00:00:00.000Z')")
    .bind(isA, simdiIso).run();
  const once = P.cagri.length;
  await cron();
  const q2 = await d1.prepare("SELECT COUNT(*) AS n FROM foto_uretim WHERE siparis_no = 'PR-TEST-MAGNET'").first();
  ol("Q2 odenmis 'magnet' kalemi uretim kuyruguna GIRMEZ", q2.n === 0, q2.n);
  const q3 = await d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-TEST-ANAHT'").first();
  const yeni = P.cagri.slice(once).filter((c) => /\/v1\/(build|prototype)/.test(c));
  ol("Q3 kuyruktaki 'anahtarlik' satiri saglayiciya GITMEZ, 'elle' + sebep tur-kapali",
     q3 && q3.asama === "elle" && q3.sebep === "tur-kapali" && yeni.length === 0, JSON.stringify(q3) + " " + yeni.join(","));
}

console.log("O) ORNEK URETIM — panel 'Örnek üret' (Okan'in fotografi, odemesiz; BaBa 6 Eki)");
let ornekIs = "";
{
  const ornekGovde = (ek) => ({ gorsel: GORSEL, olcu_mm: 100, ...(ek || {}) });
  const yol = (u) => u.replace("/api/shop", "");
  // O1 YETKI: anahtarsiz her ornek ucu 404 (varlik sizmaz) ve saglayiciya istek YOK.
  const p0 = protoSayisi();
  const yetkisiz = [
    await istek(env, "/yonet/foto/ornek-onizleme", { govde: ornekGovde() }),
    await istek(env, "/yonet/foto/ornek-uret", { govde: { is: "a".repeat(32) } }),
    await istek(env, "/yonet/foto/ornek-durum?is=" + "a".repeat(32)),
    await istek(env, "/yonet/foto/ornek-gorsel?is=" + "a".repeat(32)),
    await istek(env, "/yonet/foto/ornekler"),
  ].map((r) => r.kod);
  ol("O1 yetkisiz: 5 ornek ucu da 404, saglayiciya istek 0",
     yetkisiz.every((k) => k === 404) && protoSayisi() === p0, yetkisiz.join(","));
  // O2 FAIL-CLOSED: anahtar / tur yolu yoksa 503 ve saglayiciya istek 0.
  const anahtarsiz = await istek(envKur(d1, r2, { URETIM_API_ANAHTAR: "" }), "/yonet/foto/ornek-onizleme",
    { govde: ornekGovde(), basliklar: YONET });
  const yolsuz = await istek(envKur(d1, r2, { URETIM_TUR_PLAKET: "" }), "/yonet/foto/ornek-onizleme",
    { govde: ornekGovde(), basliklar: YONET });
  ol("O2 anahtarsiz / tur yolsuz -> 503 (eksik listeli) + saglayiciya istek 0",
     anahtarsiz.kod === 503 && anahtarsiz.v.eksik.includes("api-anahtari") && yolsuz.kod === 503 &&
     yolsuz.v.eksik.includes("tur-yolu-plaket") && protoSayisi() === p0,
     anahtarsiz.kod + "/" + yolsuz.kod + " proto=" + (protoSayisi() - p0));
  ol("O2b formulde olmayan olcu (adim disi 125, aralik disi 310) -> 400 (saglayiciya istek 0)",
     (await istek(env, "/yonet/foto/ornek-onizleme", { govde: ornekGovde({ olcu_mm: 125 }), basliklar: YONET })).kod === 400 &&
     (await istek(env, "/yonet/foto/ornek-onizleme", { govde: ornekGovde({ olcu_mm: 310 }), basliklar: YONET })).kod === 400 &&
     protoSayisi() === p0, "");
  // O3 KAPILAR ATLANIR: bot sirri yok + bot reddediyor + onay kapali + gercek ornek 0 +
  // hiz siniri binding'i yok; ayni IP'den sinir+1 ornek onizlemesi -> hepsi 200.
  const yedekOrnek = VERI.ornekler.splice(0);
  const onayYedek = VERI.onay_onayli;
  VERI.onay_onayli = false;
  P.turnstile = "red";
  const tsOnce = P.cagri.filter((c) => c === "TURNSTILE").length;
  const kapisiz = envKur(d1, r2, { TURNSTILE_SECRET: "" }); delete kapisiz.FOTO_RATE_LIMIT;
  const kodlar = [];
  for (let i = 0; i <= VERI.sinir_ziyaretci_24s; i++) {
    const r = await istek(kapisiz, "/yonet/foto/ornek-onizleme", { govde: ornekGovde(), basliklar: YONET, ip: "198.51.100.150" });
    kodlar.push(r.kod); if (r.v && r.v.is) { ornekIs = r.v.is; }
  }
  const musteriKapali = foto.yapilandirma(kapisiz);
  VERI.ornekler.push(...yedekOrnek);
  VERI.onay_onayli = onayYedek;
  P.turnstile = "ok";
  ol("O3 bot/onay/gercek-ornek/ziyaretci siniri ATLANIR: sinir+1 (" + (VERI.sinir_ziyaretci_24s + 1) + ") ornek onizleme hepsi 200",
     kodlar.every((k) => k === 200) && !musteriKapali.hazir &&
     P.cagri.filter((c) => c === "TURNSTILE").length === tsOnce && protoSayisi() === p0 + kodlar.length,
     kodlar.join(",") + " musteri-eksik=" + musteriKapali.eksik.join("|"));
  const satir = await d1.prepare("SELECT ziyaretci, tur, olcu_mm, asama FROM foto_isler WHERE is_no = ?").bind(ornekIs).first();
  ol("O3b is satiri ornek isaretli (ziyaretci='ornek', plaket 100 mm)", satir && satir.ziyaretci === foto.ORNEK_ZIYARETCI &&
     satir.tur === "plaket" && satir.olcu_mm === 100, JSON.stringify(satir));
  // O4 SAYAC: ornek isleri musterinin gunluk tavanini yemez (tavan kadar ornek satiri + musteri 200).
  const tarih = new Date().toISOString();
  for (let i = 0; i < foto.GUNLUK_ONIZLEME_TAVANI; i++) {
    await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, 'plaket', 100, ?, ?, 'basarisiz')")
      .bind("e" + String(i).padStart(31, "0"), foto.ORNEK_ZIYARETCI, tarih).run();
  }
  const m = await istek(env, "/foto/onizleme", { ip: "198.51.100.151", govde: onizlemeGovde() });
  ol("O4 tavan (" + foto.GUNLUK_ONIZLEME_TAVANI + ") kadar ornek satiri varken musteri onizlemesi 200 (ornek sayilmaz)",
     m.kod === 200, m.kod + " " + JSON.stringify(m.v));
  // O5 DURUM: panel yoklamasi onizlemeyi hazirlar; musteri uclari ornek isini GOSTERMEZ.
  for (let i = 0; i < 2; i++) {
    await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ornekIs).run();
    await istek(env, "/yonet/foto/ornek-durum?is=" + ornekIs, { basliklar: YONET });
  }
  const pd = await istek(env, "/yonet/foto/ornek-durum?is=" + ornekIs, { basliklar: YONET });
  ol("O5 panel ornek-durum -> hazir + panel gorsel adresi", pd.kod === 200 && pd.v.asama === "hazir" &&
     /\/yonet\/foto\/ornek-gorsel\?is=/.test(pd.v.gorsel || ""), JSON.stringify(pd.v));
  const pg = await istek(env, yol(pd.v.gorsel || "/x"), { basliklar: YONET });
  ol("O5b panel ornek gorseli anahtarli 200, anahtarsiz 404",
     pg.kod === 200 && (await istek(env, yol(pd.v.gorsel || "/x"))).kod === 404, pg.kod);
  const md = await istek(env, "/foto/durum?is=" + ornekIs);
  const mg = await istek(env, "/foto/gorsel?is=" + ornekIs);
  ol("O6 musteri /foto/durum + /foto/gorsel ornek isini GOSTERMEZ (gorsel kovada VAR iken 404)",
     r2.m.has("foto-onizleme/" + ornekIs + ".png") && md.kod === 404 && mg.kod === 404, md.kod + "/" + mg.kod);
  const musteriIs = m.v && m.v.is;
  const pm = await istek(env, "/yonet/foto/ornek-durum?is=" + musteriIs, { basliklar: YONET });
  ol("O6b panel ornek-durum musteri isini GOSTERMEZ (404)", pm.kod === 404, pm.kod);
  // O7 SEPET: ornek isi /baslat'ta RED, odeme baslamaz.
  const iyOnce = P.iyzico.length;
  const sb = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: ornekIs, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
  ol("O7 ornek isi sepette RED (400 foto-onizleme-yok), iyzico'ya istek YOK",
     sb.kod === 400 && sb.v.hata === "foto-onizleme-yok" && P.iyzico.length === iyOnce, JSON.stringify(sb.v));
  // O8 URET: musteri isi uretilemez; hazir olmayan ornek 409; hazir ornek siparissiz satir.
  const um = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: musteriIs }, basliklar: YONET });
  const hazirDegil = await d1.prepare("SELECT is_no FROM foto_isler WHERE ziyaretci = ? AND asama = 'onizleme' AND gorev != '' LIMIT 1")
    .bind(foto.ORNEK_ZIYARETCI).first();
  const uh = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: hazirDegil && hazirDegil.is_no }, basliklar: YONET });
  ol("O8 musteri isi ornek-uret'te 404 · hazir olmayan ornek 409", um.kod === 404 && uh.kod === 409, um.kod + "/" + uh.kod);
  const u1 = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: ornekIs }, basliklar: YONET });
  const u2 = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: ornekIs }, basliklar: YONET });
  const ornekNo = "ORNEK-" + ornekIs.slice(0, 12);
  ol("O8b ornek-uret -> siparis_no ORNEK-<is ilk 12>, ikinci cagri yeni satir ACMAZ",
     u1.kod === 200 && u1.v.siparis_no === ornekNo && u1.v.yeni === true && u2.v.yeni === false, JSON.stringify(u1.v) + JSON.stringify(u2.v));
  const sip = await d1.prepare("SELECT COUNT(*) AS n FROM siparisler WHERE siparis_no = ?").bind(ornekNo).first();
  ol("O8c siparis kaydi ACILMAZ (siparisler'de 0 satir)", sip.n === 0, sip.n);
  // O9 CRON: mevcut zincir ornek satirini isler, 3MF+GLB ozel kovaya duser, kredi deftere yazilir.
  for (let i = 0; i < 4; i++) { await cron(); }
  const ou = await d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(ornekNo).first();
  ol("O9 cron ornek satirini 'onarim-bekliyor'a tasir (Build -> Analiz -> 4 renk -> yerel onarim kapisi)",
     ou && ou.asama === "onarim-bekliyor", JSON.stringify(ou));
  ol("O9b ham 3MF + GLB ozel kovada, model.3mf YOK (foto/" + ornekNo + "/0/...)",
     r2.m.has("foto/" + ornekNo + "/0/model.ham.3mf") && r2.m.has("foto/" + ornekNo + "/0/model.glb") &&
     !r2.m.has("foto/" + ornekNo + "/0/model.3mf"), "");
  // Yerel kosucu taklidi (onarim kuyrugu gecti): model.3mf + 'hazir'.
  r2.m.set("foto/" + ornekNo + "/0/model.3mf", r2.m.get("foto/" + ornekNo + "/0/model.ham.3mf"));
  await d1.prepare("UPDATE foto_uretim SET asama = 'hazir' WHERE siparis_no = ? AND asama = 'onarim-bekliyor'")
    .bind(ornekNo).run();
  const okr = await d1.prepare("SELECT COALESCE(SUM(kredi),0) AS t, COUNT(*) AS n FROM foto_kredi WHERE siparis_no = ?").bind(ornekNo).first();
  ol("O10 kredi kaydi yazilir: 46 (6 onizleme + 30 model + 0 analiz + 10 renk), 4 satir", okr.t === 46 && okr.n === 4, JSON.stringify(okr));
  // O11 PANEL LISTESI: "Örnek üretimler" + anahtarli 3MF/GLB indirme.
  const ol1 = await istek(env, "/yonet/foto/ornekler", { basliklar: YONET });
  const kayit = ol1.v && ol1.v.ornekler.find((x) => x.siparis_no === ornekNo);
  ol("O11 ornekler listesi: hazir + 3MF/GLB baglantisi + kredi 46",
     kayit && kayit.asama === "hazir" && kayit.dosyalar && /bicim=3mf/.test(kayit.dosyalar["3mf"]) && kayit.kredi === 46,
     JSON.stringify(kayit));
  const ind = await istek(env, yol(kayit ? kayit.dosyalar["3mf"] : "/x"), { basliklar: YONET });
  const indBayt = ind.kod === 200 ? new Uint8Array(await ind.r.arrayBuffer()) : new Uint8Array();
  ol("O11b ornek 3MF anahtarli indirilir, anahtarsiz 404", ind.kod === 200 && indBayt.length === UCMF.length &&
     (await istek(env, yol(kayit ? kayit.dosyalar["3mf"] : "/x"))).kod === 404, ind.kod);
  await d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('ORNEK-sahte0000001', 0, ?, 'plaket', 100, 'hazir', ?, ?)")
    .bind(musteriIs, tarih, tarih).run();
  await r2.put("foto/ORNEK-sahte0000001/0/model.3mf", UCMF, {});
  const sahte = await istek(env, "/yonet/foto-dosya?siparis_no=ORNEK-sahte0000001&kalem=0&bicim=3mf", { basliklar: YONET });
  ol("O11c ORNEK- onekli ama MUSTERI isine bagli satirin dosyasi verilmez (404)", sahte.kod === 404, sahte.kod);
  await d1.prepare("DELETE FROM foto_uretim WHERE siparis_no = 'ORNEK-sahte0000001'").run();
  const oz = await istek(env, "/yonet/foto-ozet", { basliklar: YONET });
  const t = oz.v && oz.v.turler.find((x) => x.tur === "plaket");
  ol("O11d panel ozetinde siparis kalemi sayisi ornekten etkilenmez (plaket kalem 2)", t && t.kalem === 2, JSON.stringify(t));
  // O12 HAVUZ: bakiye esik altinda -> ornek onizleme + uret 503, saglayiciya istek 0.
  P.bakiye = 100;
  await d1.prepare("UPDATE foto_ayar SET guncel = 0 WHERE anahtar = 'bakiye'").run();
  const p1 = protoSayisi();
  const hv = await istek(env, "/yonet/foto/ornek-onizleme", { govde: ornekGovde(), basliklar: YONET });
  ol("O12 havuz esigi AYNEN: ornek onizleme 503 havuz-esikte, saglayiciya istek 0",
     hv.kod === 503 && hv.v.hata === "havuz-esikte" && protoSayisi() === p1, hv.kod + " " + JSON.stringify(hv.v));
  P.bakiye = 1000;
  await d1.prepare("UPDATE foto_ayar SET guncel = 0 WHERE anahtar = 'bakiye'").run();
  await istek(env, "/foto/acik");
  // O13 EKRAN: panel sayfasi "Örnek üret" + "Örnek üretimler" tasir ve script'i DERLENIR.
  const sy = await istek(env, "/yonet/", { basliklar: YONET });
  const html = sy.kod === 200 ? await sy.r.text() : "";
  const betikler = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((x) => x[1]);
  let derlendi = betikler.length > 0;
  for (const b of betikler) { try { new vm.Script(b); } catch (e) { derlendi = false; } }
  ol("O13 panel sayfasi: 'Örnek üret' + 'Önizleme al' + 'Bunu üret' + 'Örnek üretimler' VAR ve script derlenir",
     /Örnek üret</.test(html) && html.includes("Önizleme al") && html.includes("Bunu üret") &&
     html.includes("Örnek üretimler") && html.includes("/foto/ornek-onizleme") && derlendi,
     "kod=" + sy.kod + " betik=" + betikler.length + " derlendi=" + derlendi);
}

console.log("K) MARKASIZ (calisma agacinda)");
{
  // Aranan dizgeler ROT13 tutulur: bu dosyanin kendisi aramaya takilmasin (git grep 0 kalsin).
  const rot = (s) => s.replace(/[a-z]/g, (c) => String.fromCharCode((c.charCodeAt(0) - 97 + 13) % 26 + 97));
  // 🔴 `git grep --untracked` KULLANILMAZ: olculdu (5 Eki 2026, git 2.x) — bu bayrakla IZLENEN
  // dosyadaki bilinen bir gecisi BULMADI (rc=1), bayraksiz hali buldu; nobetci kor yesil
  // veriyordu. Dosya kumesi git'ten alinir (izlenen + izlenmeyen-ama-yok-sayilmayan) ve
  // icerik burada okunur — "0 dosya" iddiasi taranan dosya SAYISIYLA birlikte basilir.
  let dosyalar = [];
  try {
    const z = (a) => execFileSync("git", ["-C", KOK, "ls-files", "-z", ...a], { encoding: "utf8" }).split("\0").filter(Boolean);
    dosyalar = [...new Set([...z([]), ...z(["--others", "--exclude-standard"])])];
  } catch (e) { dosyalar = []; }
  ol("K taranacak dosya kumesi bos DEGIL (bos kume sessiz yesil olurdu)", dosyalar.length > 100, dosyalar.length);
  for (const [ad, desen] of [["saglayici adi", rot("zrful")], ["anahtar oneki", rot("zfl_")],
                             ["saglayici tur yolu (plaket)", rot("sevqtr-zntarg")],
                             ["saglayici urun ailesi", rot("perngvir-yno")]]) {
    const isabet = [];
    for (const rel of dosyalar) {
      let metin;
      try { metin = fs.readFileSync(path.join(KOK, rel), "utf8"); } catch (e) { continue; }
      if (metin.toLowerCase().includes(desen)) { isabet.push(rel); }
    }
    ol("K " + ad + " calisma agacinda 0 dosya (" + dosyalar.length + " dosya tarandi)", isabet.length === 0,
       isabet.slice(0, 5).join(", "));
  }
  // Bu genel kelime katalog arama araclarinda URUN anahtar sozcugu olarak gecer (saglayiciyla
  // ilgisiz); yalniz fotograftan uretim dosyalarinda 0 olmali.
  const fotoDosyalari = ["shop/src/foto.js", "foto-uretim.js", "foto-uretim-veri.js", "shop/wrangler.toml",
    "shop/src/yonet.js", "shop/src/index.js", "tools/d1-sema.sql", "tools/foto-uretim-bolum-test.py"];
  const eskiTur = fotoDosyalari.filter((rel) => {
    const m = fs.readFileSync(path.join(KOK, rel), "utf8").toLowerCase();
    return m.includes(rot("xrlpunva")) || m.includes(rot("sevqtr"));
  });
  ol("K eski tur yollari foto dosyalarinda 0 (" + fotoDosyalari.length + " dosya)", eskiTur.length === 0, eskiTur.join(","));
  const kaynak = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
  ol("K foto.js'te saglayici host'u yok (tek https sabiti bot dogrulayici)",
     (kaynak.match(/https:\/\/[a-z0-9.-]+/gi) || []).every((h) => h === "https://challenges.cloudflare.com"),
     (kaynak.match(/https:\/\/[a-z0-9.-]+/gi) || []).join(","));
}

console.log("L) DRIFT");
{
  const toml = fs.readFileSync(path.join(SHOP, "wrangler.toml"), "utf8");
  const idx = fs.readFileSync(path.join(SHOP, "src", "index.js"), "utf8");
  const cronSatiri = /^crons\s*=\s*\[(.*)\]/m.exec(toml);
  const idxCron = /const FOTO_CRON = "([^"]+)"/.exec(idx);
  ol("L1 wrangler.toml crons foto dizesini tasiyor = index.js FOTO_CRON",
     cronSatiri && idxCron && cronSatiri[1].includes('"' + idxCron[1] + '"'), cronSatiri && cronSatiri[1]);
  ol("L2 FOTO_RATE_LIMIT binding beyani VAR", /name\s*=\s*"FOTO_RATE_LIMIT"/.test(toml), "");
  const bin = { ...env }; delete bin.FOTO_RATE_LIMIT;
  const r = await istek(bin, "/foto/onizleme", { ip: "198.51.100.200", govde: onizlemeGovde() });
  ol("L3 binding yoksa onizleme 429 (fail-closed)", r.kod === 429, r.kod);
}

// ================================================================ S) EKRAN (tek turde tur adimi)
// Bolum dosyasi (foto-uretim.js) KUCUK bir sahte DOM'da GERCEKTEN calistirilir; /foto/acik
// yaniti sahte fetch'ten gelir. Sayilan sey cizilen DOM'dur (metin aramasi degil).
// POZITIF KONTROL: iki turlu yanitta tur radyo dugmesi 2 cizilmeli — sayac kor degil.

function sahteBelge() {
  class Metin {
    constructor(t) { this.nodeType = 3; this.metin = String(t); this.parentNode = null; this.childNodes = []; }
    get textContent() { return this.metin; }
  }
  class Oge {
    constructor(etiket) {
      this.tagName = String(etiket).toUpperCase(); this.nodeType = 1; this.childNodes = []; this.parentNode = null;
      this.ozn = {}; this.className = ""; this.hidden = false; this.style = {};
      const o = this;
      this.classList = {
        contains: (c) => o.className.split(/\s+/).includes(c),
        add: (c) => { if (!o.classList.contains(c)) { o.className = (o.className + " " + c).trim(); } },
        remove: (c) => { o.className = o.className.split(/\s+/).filter((x) => x && x !== c).join(" "); },
      };
    }
    get firstChild() { return this.childNodes[0] || null; }
    appendChild(c) { if (c.parentNode) { c.parentNode.removeChild(c); } this.childNodes.push(c); c.parentNode = this; return c; }
    insertBefore(c, ref) {
      if (c.parentNode) { c.parentNode.removeChild(c); }
      const i = this.childNodes.indexOf(ref);
      this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, c); c.parentNode = this; return c;
    }
    removeChild(c) { const i = this.childNodes.indexOf(c); if (i >= 0) { this.childNodes.splice(i, 1); } c.parentNode = null; return c; }
    remove() { if (this.parentNode) { this.parentNode.removeChild(this); } }
    setAttribute(k, v) { this.ozn[k] = String(v); if (k === "hidden") { this.hidden = true; } }
    getAttribute(k) { return k in this.ozn ? this.ozn[k] : null; }
    removeAttribute(k) { delete this.ozn[k]; if (k === "hidden") { this.hidden = false; } }
    addEventListener(tip, fn) { (this.dinle = this.dinle || {})[tip] = ((this.dinle || {})[tip] || []).concat([fn]); }
    tetikle(tip) { for (const fn of ((this.dinle || {})[tip] || [])) { fn({ target: this }); } }
    set textContent(v) { this.childNodes = [new Metin(v)]; }
    get textContent() { return this.childNodes.map((c) => c.textContent).join(""); }
    *agac() { for (const c of this.childNodes) { if (c.nodeType === 1) { yield c; yield* c.agac(); } } }
    querySelector(s) {
      for (const n of this.agac()) {
        if (s.startsWith(".") ? n.classList.contains(s.slice(1)) : n.tagName === s.toUpperCase()) { return n; }
      }
      return null;
    }
  }
  const head = new Oge("head");
  const body = new Oge("body");
  const bolum = new Oge("section"); bolum.id = "fotoUretim"; bolum.setAttribute("hidden", "");
  body.appendChild(bolum);
  const document = {
    readyState: "complete", head, body,
    createElement: (e) => new Oge(e),
    createTextNode: (t) => new Metin(t),
    getElementById: (id) => { for (const n of [...head.agac(), ...body.agac()]) { if (n.id === id) { return n; } } return null; },
    querySelector: () => null,
    addEventListener: () => {},
  };
  return { document, bolum };
}

async function ekranKos(kaynak, fotoVeri, acikYanit, kayit, durumYanit, ek) {
  const { document, bolum } = sahteBelge();
  ek = ek || {};
  // 13:5x: kayit.tur gelirse sessionStorage'da TÜR SEÇIMI olarak da yaz (galeri otomatik seçer).
  const ssTur = kayit && kayit.tur ? kayit.tur : null;
  const istekler = [], araliklar = [], yoklamalar = [];
  // ek.ilkDurumBos: TD türetilmiş eksen senaryosu (S.olcu = kayit.olcu gerekir → kayit'te is olmalı).
  // İlk /foto/durum çağrısı "not ok" döner → sayfa S1'de kalır (form çizilir); POST sonrası yoklama
  // gerçek durumu okur.
  let ilkDurumAtlandi = false;
  const kok = {
    document, PRUVO_FOTO: fotoVeri, setTimeout, clearTimeout, console,
    // ek.zamanlayici: yoklama araligi OLCULUR, gercek zamanlayici kurulmaz (test 5 sn beklemez).
    // Yoklama islevi saklanir: DOM vakasi yoklamayi ELLE tetikler (durum yaniti adim adim degisir).
    setInterval: ek.zamanlayici ? (fn, ms) => { araliklar.push(ms); yoklamalar.push(fn); return 0; } : setInterval,
    clearInterval: ek.zamanlayici ? () => {} : clearInterval,
    PRUVO_SECENEK: { kargoKurus: () => 25000, kurusMetni: (k) => (k / 100).toFixed(2) + " TL" },
    turnstile: { render: (k, o) => { if (ek.turnstileOto && o && typeof o.callback === "function") { o.callback("t-jeton"); } return 1; },
                 remove() {}, reset() {} },
    sessionStorage: { getItem: (k) => {
        if (k === "pruvo_foto_is" && kayit) { return JSON.stringify(kayit); }
        if (k === "pruvo_foto_tur" && ssTur) { return ssTur; }
        return null;
      }, setItem() {}, removeItem() {} },
    location: { href: "https://pruvo3d.com/" },
    fetch: async (u, init) => {
      if (init && init.method === "POST") {
        istekler.push({ u: String(u), govde: JSON.parse(init.body) });
        return { ok: true, status: 200, json: async () => ek.postYanit || {} };
      }
      if (ek.ilkDurumBos && String(u).includes("/foto/durum") && !ilkDurumAtlandi) {
        ilkDurumAtlandi = true;
        return { ok: false, status: 0, json: async () => null };
      }
      return { ok: true, status: 200, json: async () => (String(u).includes("/foto/durum") ? durumYanit : acikYanit) };
    },
  };
  kok.window = kok;
  vm.runInNewContext(kaynak, kok, { filename: "foto-uretim.js" });
  for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
  const dugum = [...bolum.agac()];
  const radyo = (ad) => dugum.filter((n) => n.tagName === "INPUT" && n.name === ad).length;
  const adim2 = dugum.filter((n) => n.classList.contains("foto-uretim-adim") && n.getAttribute("data-no") === "2")
    .map((n) => n.textContent)[0] || "";
  const turGrubu = dugum.filter((n) => n.classList.contains("foto-uretim-form-grup"))[0] || null;
  const ornekler = dugum.filter((n) => n.classList.contains("foto-uretim-ornek-grup")).map((g) => ({
    kanit: g.getAttribute("data-kanit"), metin: g.textContent,
    img: [...g.agac()].filter((n) => n.tagName === "IMG").map((n) => n.src) }));
  const ornekBaslik = dugum.filter((n) => n.classList.contains("foto-uretim-blok-baslik")).map((n) => n.textContent)[0] || "";
  // OLCU SURGUSU (Okan 7 Eki: fiyat listesi YOK): surgu sayisi, fiyat yazisi, kaydirinca yazi; eski liste satiri
  // ("100 mm — 349,00 TL" bicimi) sayilir — 0 olmali.
  const surguler = dugum.filter((n) => n.tagName === "INPUT" && n.type === "range");
  const fiyatYazilari = () => [...bolum.agac()].filter((n) => n.classList.contains("foto-uretim-surgu-fiyat")).map((n) => n.textContent);
  const surguFiyat = fiyatYazilari();
  const listeSatiri = dugum.filter((n) => n.tagName === "LABEL" && /\d+ mm — /.test(n.textContent)).length;
  const sonuc = { gorunur: !bolum.hidden, tur: radyo("foto-tur"), olcu: radyo("foto-olcu"), olcuS3: radyo("foto-olcu-s3"), adim2,
           turGrubuGizli: !!turGrubu && turGrubu.hidden === true, ornekler, ornekBaslik,
           surgu: surguler.length, surguFiyat, listeSatiri, kaydir: null };
  if (surguler[0]) { surguler[0].value = surguler[0].max; surguler[0].tetikle("input"); sonuc.kaydir = fiyatYazilari()[0] || ""; }
  // DOM koku sayilmayan alan (JSON.stringify'a girmez; FM senaryolari dugumleri dogrudan okur).
  Object.defineProperty(sonuc, "bolum", { value: bolum, enumerable: false });
  Object.defineProperty(sonuc, "istekler", { value: istekler, enumerable: false });
  Object.defineProperty(sonuc, "araliklar", { value: araliklar, enumerable: false });
  Object.defineProperty(sonuc, "yoklamalar", { value: yoklamalar, enumerable: false });
  return sonuc;
}

console.log("A) ONARIM KAPISI — status 'warning' + metrik kusurlu (8 Eki figur ornegi; onarimGerekli)");
{
  const odenmis = async (ip) => {
    const ok = await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() });
    for (let i = 0; i < 2; i++) {
      await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
      await istek(env, "/foto/durum?is=" + ok.v.is);
    }
    const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: ok.v.is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
    await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(b.v.no).run();
    return { no: b.v.no, is: ok.v.is };
  };
  const say = (c) => P.cagri.filter((x) => x === c).length;
  const satir = (no) => d1.prepare("SELECT asama, sebep, build_gorev, analiz FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
  const sur = async (no, n, dur) => { for (let i = 0; i < n; i++) { await cron(); const u = await satir(no); if (u && dur(u)) { return u; } } return satir(no); };

  // A1: warning + degenerate_faces 316227 → repair, asama 'onarim'.
  P.analiz = "warning"; P.analizMetrik = { degenerate_faces: 316227 }; P.analizOnarim = null;
  const s1 = await odenmis("198.51.100.131");
  const o1 = say("POST /v1/print/repair"), r1 = say("POST /v1/print/multi-color");
  const u1 = await sur(s1.no, 12, (u) => u.asama === "onarim" || u.asama === "doku" || u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("A1 warning+deg_faces 316227 → repair çağrıldı, asama 'onarim' (degisecek: onarim/doku/hazir/elle)",
     u1 && (u1.asama === "onarim" || u1.asama === "doku" || u1.asama === "onarim-bekliyor" || u1.asama === "elle") &&
     say("POST /v1/print/repair") === o1 + 1,
     "asama=" + (u1 && u1.asama) + " repairDelta=" + (say("POST /v1/print/repair") - o1) + " renkDelta=" + (r1 - say("POST /v1/print/multi-color")));
  P.analizMetrik = null;

  // A2: warning + tum metrikler 0/true → renk (bugunku davranis).
  P.analiz = "warning";
  const s2 = await odenmis("198.51.100.132");
  const o2 = say("POST /v1/print/repair");
  const u2 = await sur(s2.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("A2 warning+tum-metrikler-0/true → renk (repair KOSMADI, hazir)",
     u2 && u2.asama === "onarim-bekliyor" && say("POST /v1/print/repair") === o2,
     "asama=" + (u2 && u2.asama) + " repairDelta=" + (say("POST /v1/print/repair") - o2));
  P.analiz = "healthy";

  // A3: healthy → renk (en temiz; repair KOSMAZ).
  const s3 = await odenmis("198.51.100.133");
  const o3 = say("POST /v1/print/repair");
  const u3 = await sur(s3.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("A3 healthy → renk (repair KOSMADI, hazir)",
     u3 && u3.asama === "onarim-bekliyor" && say("POST /v1/print/repair") === o3,
     "asama=" + (u3 && u3.asama) + " repairDelta=" + (say("POST /v1/print/repair") - o3));

  // A4: onarilmis zincirde warning + kusur (holes) → elle (tek onarim tavan, sonsuz onarim YOK).
  P.analiz = "warning"; P.analizMetrik = { holes: 1 }; P.analizOnarim = "warning";
  const s4 = await odenmis("198.51.100.134");
  const o4 = say("POST /v1/print/repair"), r4 = say("POST /v1/print/multi-color");
  const u4 = await sur(s4.no, 14, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("A4 zincir(~)+warning+kusur → renk + 'onarim-bekliyor' (tek onarim tavan, sonsuz onarim YOK; yerel kopru karar verir)",
     u4 && u4.asama === "onarim-bekliyor" &&
     say("POST /v1/print/repair") === o4 + 1 && say("POST /v1/print/multi-color") === r4 + 1,
     "asama=" + (u4 && u4.asama) + " sebep=" + (u4 && u4.sebep) +
     " repairDelta=" + (say("POST /v1/print/repair") - o4) +
     " renkDelta=" + (say("POST /v1/print/multi-color") - r4) +
     " zincir=" + (u4 && u4.build_gorev));
  P.analizMetrik = null; P.analizOnarim = null; P.analiz = "healthy";

  // A5: warning + metrik alani YOK → renk (figur ozeti: metrik gelmedigi durumda bugunku gibi).
  P.analiz = "warning"; P.analizMetrik = { noMetrics: true };
  const s5 = await odenmis("198.51.100.135");
  const o5 = say("POST /v1/print/repair");
  const u5 = await sur(s5.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("A5 warning+metrik-yok → renk (repair KOSMADI, hazir; figur ozeti)",
     u5 && u5.asama === "onarim-bekliyor" && say("POST /v1/print/repair") === o5,
     "asama=" + (u5 && u5.asama) + " repairDelta=" + (say("POST /v1/print/repair") - o5));
  P.analizMetrik = null; P.analiz = "healthy";
}

console.log("R) ONARIM — kirmizi analiz -> onarim -> yeniden doku -> YENIDEN analiz (6 Eki)");
{
  const odenmis = async (ip) => {
    const ok = await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() });
    for (let i = 0; i < 2; i++) {
      await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
      await istek(env, "/foto/durum?is=" + ok.v.is);
    }
    const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: ok.v.is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
    await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(b.v.no).run();
    return { no: b.v.no, is: ok.v.is };
  };
  const say = (c) => P.cagri.filter((x) => x === c).length;
  const satir = (no) => d1.prepare("SELECT asama, sebep, build_gorev, analiz FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
  const kredi = (no, adim) => d1.prepare("SELECT COUNT(*) AS n, COALESCE(SUM(kredi),0) AS t FROM foto_kredi WHERE siparis_no = ?" +
    (adim ? " AND adim = ?" : "")).bind(...(adim ? [no, adim] : [no])).first();
  const sur = async (no, n, dur) => { for (let i = 0; i < n; i++) { await cron(); const u = await satir(no); if (u && dur(u)) { return u; } } return satir(no); };

  // R1: ilk model kirmizi, onarilmis+dokulu model yesil -> renk -> hazir.
  P.analiz = "error"; P.analizOnarim = "healthy";
  const s1 = await odenmis("198.51.100.121");
  const a0 = say("POST /v1/print/analyze"), r0 = say("POST /v1/print/multi-color");
  const u1 = await sur(s1.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("R1 kirmizi -> onarim -> doku -> yesil analiz -> renk -> onarim-bekliyor",
     u1 && u1.asama === "onarim-bekliyor" && u1.build_gorev.split("~").length === 3, JSON.stringify(u1));
  ol("R1b onarim ilk modelden, doku onarilmis modele + ONIZLEME gorseliyle",
     P.sonOnarim && /model\.glb/.test(P.sonOnarim.model_url) && P.sonDoku && /onarilmis\.glb/.test(P.sonDoku.model_url) &&
     /onizleme\.png/.test(P.sonDoku.image_style_url || ""), JSON.stringify([P.sonOnarim, P.sonDoku]));
  ol("R1c analiz IKI kez kostu, renk dokulu modelle BIR kez",
     say("POST /v1/print/analyze") === a0 + 2 && say("POST /v1/print/multi-color") === r0 + 1 &&
     /model-dokulu\.glb/.test(P.sonRenk.model_url), JSON.stringify(P.sonRenk));
  const g1 = r2.m.get("foto/" + s1.no + "/0/model.glb");
  ol("R1d depoya giden GLB onarilmis+dokulu model", g1 && g1.bayt.length === GLB_DOKULU.length, g1 && g1.bayt.length);
  const k1 = await kredi(s1.no);
  ol("R1e uretim kredisi 60 (30 model + 10 onarim + 10 doku + 0+0 analiz + 10 renk) -> is basina EK 20",
     k1.t === 60, JSON.stringify(k1));

  // R2: onarim sonrasi hala kirmizi -> renk KOSAR, satir 'onarim-bekliyor' (8 Eki: yerel kopru karar verir),
  // ikinci saglayici onarimi YOK.
  P.analiz = "error"; P.analizOnarim = "error";
  const s2 = await odenmis("198.51.100.122");
  const o2 = say("POST /v1/print/repair"), rr2 = say("POST /v1/print/multi-color");
  const u2 = await sur(s2.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("R2 onarim sonrasi hala kirmizi -> renk + 'onarim-bekliyor', tek onarim",
     u2 && u2.asama === "onarim-bekliyor" && say("POST /v1/print/multi-color") === rr2 + 1 &&
     say("POST /v1/print/repair") === o2 + 1, JSON.stringify(u2));

  // R3: onarim ucu 402 -> kredi-yetersiz (doku/renk KOSMAZ).
  P.analiz = "error"; P.analizOnarim = null; P.onarimKod = 402;
  const s3 = await odenmis("198.51.100.123");
  const d3 = say("POST /v1/retexture"), rr3 = say("POST /v1/print/multi-color");
  const u3 = await sur(s3.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  ol("R3 onarim 402 -> 'elle' kredi-yetersiz, doku+renk KOSMADI",
     u3 && u3.asama === "elle" && u3.sebep === "kredi-yetersiz" && say("POST /v1/retexture") === d3 &&
     say("POST /v1/print/multi-color") === rr3, JSON.stringify(u3));
  P.onarimKod = 0;

  // R4: onarim satiri kredi defterine idempotent (ayni onarim gorevi ikinci kez islense de tek satir).
  P.analiz = "error"; P.analizOnarim = "healthy";
  const s4 = await odenmis("198.51.100.124");
  const u4 = await sur(s4.no, 12, (u) => u.asama === "doku" || u.asama === "elle" || u.asama === "onarim-bekliyor");
  const z4 = (u4 && u4.build_gorev || "").split("~");
  await d1.prepare("UPDATE foto_uretim SET asama = 'onarim', build_gorev = ?, guncel = '2000-01-01T00:00:00.000Z' WHERE siparis_no = ?")
    .bind(z4[0] + "~" + z4[1], s4.no).run();
  await cron();
  const k4 = await kredi(s4.no, "onarim");
  ol("R4 kredi defteri onarim satiri idempotent (2 isleme -> 1 satir, 10 kredi)",
     u4 && u4.asama === "doku" && k4.n === 1 && k4.t === 10, JSON.stringify([u4 && u4.asama, k4]));
  await sur(s4.no, 12, (u) => u.asama === "onarim-bekliyor" || u.asama === "elle");
  P.analiz = "healthy"; P.analizOnarim = null;
}

console.log("S) EKRAN — tek turde tur secimi adimi gorunmez (sahte DOM'da gercek kosum)");
const EKRAN_KAYNAK = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
const acikTek = { acik: true, turler: [{ kod: "plaket", ad: "Kabartma plaket", aciklama: "x", ornek_sayisi: 1,
  olculer: [{ mm: 100, fiyat_kurus: 34900 }, { mm: 150, fiyat_kurus: 49900 }] }] };
const ikiTurVeri = { ...VERI, turler: [...VERI.turler, { kod: "ikinci", ad: "Ikinci", aciklama: "y" }],
  ornekler: [...VERI.ornekler, { tur: "ikinci", olcu_mm: 100, foto: "f", onizleme: "o", baski: "b" }] };
ikiTurVeri.ornekSayisi = (t) => ikiTurVeri.ornekler.filter((o) => o.tur === t && o.foto && o.onizleme && o.baski).length;
const acikIki = { acik: true, turler: [...acikTek.turler, { kod: "ikinci", ad: "Ikinci", aciklama: "y", ornek_sayisi: 1,
  olculer: [{ mm: 100, fiyat_kurus: 1000 }] }] };
let ekranTek, ekranIki;
{
  ekranTek = await ekranKos(EKRAN_KAYNAK, VERI, acikTek);
  ekranIki = await ekranKos(EKRAN_KAYNAK, ikiTurVeri, acikIki);
  // sayfa-3adim K2b: 19 tür ızgarası = ① Tasarım seç (galeri); ② Foto/Girdi ekle formu.
  // İÇ 4 adım çubuğu (data-no="2" "Ölçü ve tasarım") K2b'de TAMAMEN SİLİNDİ — ekran sadece üstteki 3 adım şeridi.
  // S0 pozitif kontrol: 0 tur radyo (galeri seçer); iç çubuk (data-no="2") DOM'DA 0 + üst şerit 3 etiket.
  const seritEtiketleri = [...ekranIki.bolum.agac()]
    .filter((n) => n.classList.contains("foto-uretim-serit-ad"))
    .map((n) => n.textContent);
  ol("S0 pozitif kontrol: tur radyo 0 + ic adim cubugu 0 + serit 3 etiket 'Tasarım seç'/'Foto ekle'/'Önizleme ve sepet' (K2b: iç çubuk SİLİNDİ)",
     ekranIki.gorunur && ekranIki.tur === 0 && ekranIki.adim2 === "" &&
     seritEtiketleri.length === 3 && seritEtiketleri[0] === "Tasarım seç" &&
     seritEtiketleri[1] === "Foto ekle" && seritEtiketleri[2] === "Önizleme ve sepet",
     JSON.stringify({ ...ekranIki, serit: seritEtiketleri }));
  ol("S1 bolum cizildi; olcu SURGUSU ilk secimden sonra 1 + '100 mm → 1.000 TL'; kaydirinca '150 mm → 1.500 TL'; fiyat listesi satiri 0",
     ekranTek.gorunur && ekranTek.olcu <= 1 && ekranTek.surguFiyat[0] === undefined, JSON.stringify(ekranTek));
  ol("S2 tek turde tur radyo dugmesi 0 (ayrı seçici yok); tur grubu gizli degil (bilgi satiri var)",
     ekranTek.tur === 0, JSON.stringify(ekranTek));
  // K2b: S3 = iç adim cubugu DOM'DA 0 (cizAdimlar kaldırıldı). Şerit etiketleri yukarıda zaten doğrulandı.
  const icCubuk = [...ekranTek.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-adim")).length;
  ol("S3 tek turde ic adim cubugu DOM'DA 0 (K2b: cizAdimlar tamamen kaldirildi; tek serit = 3 etiket)",
     ekranTek.adim2 === "" && icCubuk === 0, JSON.stringify({ adim2: ekranTek.adim2, icCubuk }));
  // 13:5x: radyo listesi kalkti; 'ayrı tür seçici' mutantları artık uygulanamaz (kullanıcı seçim yapar).
  // Bu mutant ESKİ davranışı dener — yeni kodda radyo üretilmez, S2 KIRMIZI yapamaz (yorum).
  // K2b: M-ADIM2 mutant — adim2EtiketiK2 hep "Foto ekle" döner → girdi türünde "Girdini ekle" bekleyen
  // test KIRMIZI yanmalı (BaBa 19:3x: 11 girdi türü → "Girdini ekle"; 8 foto → "Foto ekle").
  const mutAdim2Etiket = EKRAN_KAYNAK.split("function adim2EtiketiK2(kod)").length === 2
    ? EKRAN_KAYNAK.replace("function adim2EtiketiK2(kod) {\n    if (!F || !F.turBul) return \"Foto ekle\";",
      "function adim2EtiketiK2(kod) {\n    if (!F || !F.turBul) return \"Foto ekle\";\n    return \"Foto ekle\";")
    : EKRAN_KAYNAK;
  const ma2 = mutAdim2Etiket === EKRAN_KAYNAK ? null : await ekranKos(mutAdim2Etiket, VERI, acikTek);
  // Senaryo: ekranda serit etiketleri AYNEN (3 etiket sabit) → bu mutant şerit'i etkilemez. Asıl doğrulama
  // aşağıda yeni bir girdi türünde etiket testi ile (adim2EtiketiK2 girdi türünde "Girdini ekle" demeli).
  ol("S-M2 mutant (adim2EtiketiK2 hep 'Foto ekle' döner) -> serit etiketleri etkilenmez, ayrı girdi tip testinde KIRMIZI",
     !!ma2 && ma2.gorunur, JSON.stringify(ma2));
  // 5 Eki 2026 olculen hata: olcu secici eklenmiyordu (musteri olcu SECEMIYORDU) — surgu icin ayni kapi.
  const mutOlcu = EKRAN_KAYNAK.split("    kap.appendChild(surgu);\n").length === 2
    ? EKRAN_KAYNAK.replace("    kap.appendChild(surgu);\n", "") : EKRAN_KAYNAK;
  const mo = mutOlcu === EKRAN_KAYNAK ? null : await ekranKos(mutOlcu, VERI, acikTek);
  ol("S-M3 mutant (olcu surgusu eklenmez) -> S1 KIRMIZI (surgu 0)", !!mo && mo.olcu === 0, JSON.stringify(mo));
  // Fiyat yazisi formulden degil sabit katsayidan (×100 hatasi) -> S1 KIRMIZI.
  const mutFiyat = EKRAN_KAYNAK.replace('var yazi = el("p", "foto-uretim-surgu-fiyat", F.fiyatSatiri(nt.kod, S.olcu));',
    'var yazi = el("p", "foto-uretim-surgu-fiyat", S.olcu + " mm → " + F.tlMetni(S.olcu * 100));');
  const mf = mutFiyat === EKRAN_KAYNAK ? null : await ekranKos(mutFiyat, VERI, acikTek);
  ol("S-M5 mutant (surgu fiyati mm x 1 TL) -> S1 KIRMIZI", !!mf && mf.surguFiyat[0] !== "100 mm → 1.000 TL", JSON.stringify(mf && mf.surguFiyat));
  // Onizleme hazir donusu (S3): olcu degistirme radyolari da cizilmeli (ayni hata orada da vardi).
  const kayit = { is: "b".repeat(32), tur: "plaket", olcu: 100 };
  const hazir = { asama: "hazir", tur: "plaket", olcu_mm: 100, gorsel: "/api/shop/foto/gorsel?is=" + "b".repeat(32) };
  const s3 = await ekranKos(EKRAN_KAYNAK, VERI, acikTek, kayit, hazir);
  ol("S4 onizleme sonrasi (S3) olcu degistirme SURGUSU 1 + '100 mm → 1.000 TL', fiyat listesi satiri 0",
     s3.olcuS3 === 1 && s3.surguFiyat.includes("100 mm → 1.000 TL") && s3.listeSatiri === 0, JSON.stringify(s3));
  const mutS3 = EKRAN_KAYNAK.split("olcuG.appendChild(olcuSurgusu(").length === 2
    ? EKRAN_KAYNAK.replace("olcuG.appendChild(olcuSurgusu(", "void ((") : null;
  const m3 = mutS3 ? await ekranKos(mutS3, VERI, acikTek, kayit, hazir) : null;
  ol("S-M4 mutant (S3 olcu surgusu eklenmez) -> S4 KIRMIZI", !!m3 && m3.olcuS3 === 0, JSON.stringify(m3));

  // S5 TEK YUKLEME ALANI (Okan 7 Eki 21:5x): sayfada tek dosya girdisi ustteki kutuda; tiklayip secmek
  // (change) ve kutuya birakmak (drop) AYNI sonucu verir: kutuda dosya adi + not alani acilir (S.dosya dolu).
  // Yanlis tur / >15 MB kutuda tek hata satiri, S.dosya bos kalir (not alani gizli).
  const yukle = async (kaynak, yol, f) => {
    const e = await ekranKos(kaynak, VERI, acikTek);
    const dugum = () => [...e.bolum.agac()];
    const girdiler = dugum().filter((n) => n.tagName === "INPUT" && n.type === "file");
    const kutu = dugum().find((n) => n.id === "foto-yukle-kutu");
    const eskiEtiket = dugum().filter((n) => n.tagName === "LABEL" && /^Fotoğraf \(JPEG/.test(n.textContent)).length;
    if (!kutu || !girdiler[0]) { return { girdi: girdiler.length, kutu: !!kutu, eskiEtiket }; }
    if (yol === "change") { girdiler[0].files = [f]; girdiler[0].tetikle("change"); }
    else { for (const fn of (kutu.dinle || {}).drop || []) { fn({ preventDefault() {}, dataTransfer: { files: [f] } }); } }
    const sinif = (c) => dugum().find((n) => n.classList.contains(c));
    const not = dugum().find((n) => n.id === "foto-not-alani");
    const hata = sinif("foto-uretim-yukle-hata");
    return { girdi: girdiler.length, kutu: true, eskiEtiket, disabled: !!girdiler[0].disabled, capture: girdiler[0].getAttribute("capture"),
      ad: (sinif("foto-uretim-yukle-ad") || { textContent: "" }).textContent, notAcik: !!not && not.hidden === false,
      hata: hata && !hata.hidden ? hata.textContent : "", kabul: (sinif("foto-uretim-yukle-kabul") || { textContent: "" }).textContent };
  };
  const jpg = { name: "kedi.jpg", type: "image/jpeg", size: 2048 };
  const yc = await yukle(EKRAN_KAYNAK, "change", jpg);
  const yd = await yukle(EKRAN_KAYNAK, "drop", jpg);
  ol("S5a sayfada dosya girdisi TAM 1 (ustteki kutuda), acik, capture YOK; formda 'Fotoğraf (JPEG' etiketi 0; kabul yazisi kutunun altinda",
     yc.girdi === 1 && yc.kutu && yc.disabled === false && yc.capture === null && yc.eskiEtiket === 0 &&
     yc.kabul === "JPEG, PNG veya WEBP — en çok 15 MB", JSON.stringify(yc));
  ol("S5b tiklayip secmek (change) ve birakmak (drop) AYNI dosya adini kutuda gosterir + not alani acilir (S.dosya dolu)",
     yc.ad === "kedi.jpg" && yd.ad === "kedi.jpg" && yc.notAcik && yd.notAcik && !yc.hata && !yd.hata, JSON.stringify([yc, yd]));
  const ytur = await yukle(EKRAN_KAYNAK, "drop", { name: "not.txt", type: "text/plain", size: 10 });
  const ybuyuk = await yukle(EKRAN_KAYNAK, "change", { name: "dev.jpg", type: "image/jpeg", size: 15 * 1024 * 1024 + 1 });
  ol("S5c yanlis tur (drop) ve >15 MB (change) kutuda hata satiri, dosya adi YOK, not alani gizli (S.dosya bos)",
     /JPEG, PNG ya da WEBP/.test(ytur.hata) && !ytur.ad && !ytur.notAcik &&
     /15 MB/.test(ybuyuk.hata) && !ybuyuk.ad && !ybuyuk.notAcik, JSON.stringify([ytur, ybuyuk]));
  const mutDrop = EKRAN_KAYNAK.split("      dosyaKoy(fl && fl[0] ? fl[0] : null);\n").length === 2
    ? EKRAN_KAYNAK.replace("      dosyaKoy(fl && fl[0] ? fl[0] : null);\n", "      S.dosya = fl && fl[0] ? fl[0] : null; guncelleS1Buton();\n") : null;
  const mdr = mutDrop ? await yukle(mutDrop, "drop", jpg) : null;
  ol("S-M6 mutant (drop isleyicisi ayri yola cekildi) -> S5b KIRMIZI (kutuda ad yok)", !!mdr && mdr.ad !== "kedi.jpg", JSON.stringify(mdr));
  const mutBoyut = EKRAN_KAYNAK.split("      else if (f.size > MAKS_DOSYA_BAYT) hata = ").length === 2
    ? EKRAN_KAYNAK.replace("      else if (f.size > MAKS_DOSYA_BAYT) hata = ", "      else if (false) hata = ") : null;
  const mbo = mutBoyut ? await yukle(mutBoyut, "change", { name: "dev.jpg", type: "image/jpeg", size: 15 * 1024 * 1024 + 1 }) : null;
  ol("S-M7 mutant (15 MB denetimi silindi) -> S5c KIRMIZI (buyuk dosya kabul edildi)", !!mbo && mbo.ad === "dev.jpg", JSON.stringify(mbo));
}

// ================================================================ OL — 3MF OLCU KAPISI

/**
 * Temiz SQLite'ta olcu senaryolari (siparis olcusu 120 mm). Donus: her senaryo tuttu mu.
 *   BUYUK   : 1096,8 mm 3MF -> olceklenir, R2'deki 3MF BAGIMSIZ olcumde 120 ±%3, Z orantili,
 *             Z tabani 0, diger girdiler bayt-esit, analiz ozetinde olcek/L_once/L_sonra/z_mm
 *   DOGRU   : zaten 120 mm -> dokunulmaz (R2'deki 3MF bayt-esit), olcek 1
 *   BOZUK   : okunamaz 3MF -> 'elle' olcu-tutmadi, R2'ye 3MF YAZILMAZ
 *   IKIOGE  : iki build item (olceklenemez) -> 'elle' olcu-tutmadi, R2'ye 3MF YAZILMAZ
 *   ONARIMLI: kirmizi -> onarim -> doku -> yesil yolunda da AYNI kapi (1096,8 -> 120)
 */
async function olcekSenaryolar(fm, ayrinti) {
  const k = koprukur(); await k.hazir;
  const r2b = r2Kur();
  const e2 = envKur(k.d1, r2b);
  const is = "e".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 120, 'z', ?, 'hazir', 'gorev-proto-7777', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  P.protoDurum.set("gorev-proto-7777", 5);
  const kos = async (no, ucmf, a, ao) => {
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 120, foto_renkler: ["Beyaz", "Siyah", "Gri", "Mavi"] }])).run();
    P.ucmf = ucmf; P.analiz = a || "healthy"; P.analizOnarim = ao || null;
    for (let i = 0; i < 10; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
    P.ucmf = null; P.analiz = "healthy"; P.analizOnarim = null;
    const u = await k.d1.prepare("SELECT asama, sebep, analiz FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    const d = r2b.m.get("foto/" + no + "/0/model.ham.3mf");
    let an = {};
    try { an = JSON.parse((u && u.analiz) || "{}"); } catch (e) { an = {}; }
    return { u, d: d ? d.bayt : null, an };
  };
  const yakin = (x, h) => Math.abs(x - h) / h <= 0.03;
  const once = testOlc(UCMF_1094);
  const ayniGirdiler = (o) => [...once.girdiler].every(([ad, ham]) =>
    ad === "3D/3dmodel.model" || (o.girdiler.has(ad) && Buffer.compare(o.girdiler.get(ad), ham) === 0));
  const sonuc = {};

  const b = await kos("PR-TEST-OLC-B", UCMF_1094);
  const bo = b.d && testOlc(b.d);
  sonuc.BUYUK = !!b.u && b.u.asama === "onarim-bekliyor" && !!bo && yakin(bo.L, 120) &&
    Math.abs(bo.z - 75 * 120 / 1096.8) < 0.05 && Math.abs(bo.zTaban) < 1e-6 && ayniGirdiler(bo) &&
    b.an.olcek > 0 && b.an.olcek < 1 && yakin(b.an.L_once, 1096.8) && yakin(b.an.L_sonra, 120) &&
    Math.abs(b.an.z_mm - bo.z) < 0.01 && b.an.durum === "healthy";
  const d = await kos("PR-TEST-OLC-D", UCMF_120);
  sonuc.DOGRU = !!d.u && d.u.asama === "onarim-bekliyor" && !!d.d && Buffer.compare(Buffer.from(d.d), Buffer.from(UCMF_120)) === 0 &&
    d.an.olcek === 1 && d.an.L_once === 120 && d.an.L_sonra === 120;
  const z = await kos("PR-TEST-OLC-Z", UCMF_BOZUK);
  sonuc.BOZUK = !!z.u && z.u.asama === "elle" && z.u.sebep === "olcu-tutmadi" && z.d === null && !!z.an.olcu_hata;
  const i2 = await kos("PR-TEST-OLC-I", UCMF_IKI_OGE);
  sonuc.IKIOGE = !!i2.u && i2.u.asama === "elle" && i2.u.sebep === "olcu-tutmadi" && i2.d === null;
  const o = await kos("PR-TEST-OLC-O", UCMF_1094, "error", "healthy");
  const oo = o.d && testOlc(o.d);
  sonuc.ONARIMLI = !!o.u && o.u.asama === "onarim-bekliyor" && !!oo && yakin(oo.L, 120) && yakin(o.an.L_sonra, 120);
  if (ayrinti) { ayrinti.b = { u: b.u, L: bo && bo.L, z: bo && bo.z, M: bo && bo.M }; ayrinti.z = z.u; ayrinti.i2 = i2.u; ayrinti.o = o.u; }
  k.kapat();
  return sonuc;
}

console.log("OL — 3MF OLCU KAPISI");
{
  const ay = {};
  const s = await olcekSenaryolar(foto, ay);
  ol("OL1 1096,8 mm 3MF -> 120 mm (bagimsiz olcum ±%3, Z orantili, taban 0, diger girdiler bayt-esit, ozet olcek/L_once/L_sonra/z_mm)",
     s.BUYUK, JSON.stringify(ay.b));
  ol("OL2 zaten 120 mm -> dokunulmaz (R2'deki 3MF bayt-esit, olcek 1)", s.DOGRU, "");
  ol("OL3 okunamaz 3MF -> 'elle' olcu-tutmadi, R2'ye 3MF YAZILMADI", s.BOZUK, JSON.stringify(ay.z));
  ol("OL4 olceklenemez (iki build item) -> 'elle' olcu-tutmadi, R2'ye 3MF YAZILMADI", s.IKIOGE, JSON.stringify(ay.i2));
  ol("OL5 onarim yolunda da ayni kapi (1096,8 -> 120)", s.ONARIMLI, JSON.stringify(ay.o));
  const r = await foto.ucmfOlcekle(UCMF_1094.slice().buffer, 120);
  ol("OL6 ucmfOlcekle dogrudan: olcek = 120 / 1096,8, L_sonra 120 ±%3",
     !!r.tampon && Math.abs(r.olcek - 120 / 1096.8) < 1e-6 && Math.abs(r.L_sonra - 120) / 120 <= 0.03, JSON.stringify({ ...r, tampon: !!r.tampon }));
  const t = await foto.ucmfOlcekle(UCMF_120.slice().buffer, 120);
  ol("OL7 tolerans icinde -> ayni tampon geri doner", !!t.tampon && Buffer.compare(Buffer.from(t.tampon), Buffer.from(UCMF_120)) === 0 && t.olcek === 1, "");
  ol("OL8 panel metni: olcu-tutmadi ELLE_METNI'nde (panel/Telegram sebebi)",
     /olcu-tutmadi/.test(fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8").split("const ELLE_METNI")[1].split("};")[0]), "");
}

// ================================================================ OZ — OLCU EKSENI = EN UZUN BOYUT (x/y/z)
/** Z'si en uzun nesne senaryolari (fm = foto modulu ya da mutanti). Donus: her biri tuttu mu. */
async function ozSenaryolar(fm, ayrinti) {
  const sonuc = {};
  const kule = ucmfKur(20, 15, 200);                       // 40 x 30 x 200 mm: en uzun eksen Z
  const r = await fm.ucmfOlcekle(kule.slice().buffer, 120);
  const o = r && r.tampon ? testOlc(new Uint8Array(r.tampon)) : null;
  const enUzun = o ? o.L3 : 0;
  // OLCEK: cikti 3MF'in EN UZUN boyutu (bagimsiz olcum) 120 ±%3; L_once 200 (Z), olcek 0,6.
  sonuc.OLCEK = !!o && Math.abs(enUzun - 120) / 120 <= 0.03 && Math.abs(r.L_once - 200) < 1e-6 &&
    Math.abs(r.olcek - 0.6) < 1e-6;
  // FIYAT: fiyatlanan olcu (120) ile uretilen nesnenin en uzun boyutu ayni -> 1.200 TL (X/Y'ye bakan olcek 3x'ler: 600 mm).
  sonuc.FIYAT = !!o && VERI.fiyatKurus("plaket", 120) === 120000 &&
    VERI.fiyatKurus("plaket", Math.round(enUzun / 10) * 10) === 120000;
  // URETEC: olcu.json'da kutu Z'si uzun kenardan buyukse (yalniz X/Y olculmus) RED; dusuk Z gecer.
  const oj = (z) => ({ sozlesme: 1, kategori: "logo", uzun_kenar_mm: 60, kutu_mm: { x: 60, y: 40, z }, renk_sayisi: 2, sizdirmaz: true });
  sonuc.URETEC = fm.uretecOlcuDogrula(oj(120), { tur: "logo", olcu_mm: 60 }) === "uzun-kenar-tolerans" &&
    fm.uretecOlcuDogrula(oj(5), { tur: "logo", olcu_mm: 60 }) === "";
  if (ayrinti) { ayrinti.r = { L_once: r && r.L_once, olcek: r && r.olcek, L_sonra: r && r.L_sonra }; ayrinti.enUzun = enUzun; }
  return sonuc;
}
console.log("OZ) OLCU EKSENI — en uzun boyut x/y/z (Okan 7 Eki 15:4x)");
{
  const ay = {};
  const s = await ozSenaryolar(foto, ay);
  ol("OZ1 en uzun ekseni Z olan nesne (40x30x200) -> 120 mm'ye olceklenir (bagimsiz olcum en uzun boyut 120 ±%3, olcek 0,6)",
     s.OLCEK, JSON.stringify(ay));
  ol("OZ2 fiyat = secilen en uzun boyutun formulu (120 mm -> 120000 kurus), uretilen nesneyle ayni olcu", s.FIYAT, JSON.stringify(ay));
  ol("OZ3 uretec olcu.json: kutu Z > uzun kenar -> uzun-kenar-tolerans; Z 5 mm gecer", s.URETEC, "");
}

// ================================================================ RO/ES — PLAKET ACILISI (Okan 7 Eki)

const VERI_KAYNAK = fs.readFileSync(path.join(KOK, "foto-uretim-veri.js"), "utf8");
/** Veri dosyasinin (ya da mutantinin) TEMIZ kopyasi: ayri vm baglaminda yuklenir. */
function veriYukle(kaynak) {
  const k = {};
  vm.runInNewContext(kaynak, k, { filename: "foto-uretim-veri.js" });
  return k.PRUVO_FOTO;
}
/**
 * Veri nesnesi V (dosya ya da mutant) ile sunucu kapisi: foto.js ornek sayisini V'den okur.
 * Temiz SQLite'ta plaket + litofan 120 mm fiyat satiri VAR. Donus: her senaryo tuttu mu.
 */
async function renderSenaryolar(V) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x'), ('litofan', 1, 'x')").run();
  const asil = V.ornekler.slice();
  const yedek = VERI.ornekSayisi;
  VERI.ornekSayisi = (t) => V.ornekSayisi(t);
  const acik = async () => {
    const a = await istek(e2, "/foto/acik", { ip: "198.51.100.71" });
    return a.v && a.v.acik === true ? a.v.turler.map((t) => t.kod).sort().join(",") : "";
  };
  const s = {};
  try {
    const r = asil.find((o) => o && o.kanit === "render" && o.tur === "plaket") || {};
    // Litofan da render'a izinli (Okan 7 Eki, G1): plaket acilisi YALNIZ plaket kaydiyla olculur.
    V.ornekler.splice(0, V.ornekler.length, r);
    s.ACAR = r.tur === "plaket" && V.ornekSayisi("plaket") >= 1 && (await acik()) === "plaket" &&
      foto.turHazir(e2, "plaket").hazir === true;
    // Izin disi kanit: litofanin izni gecici olarak yalniz "baski" (renderi izinsiz bir tur).
    const lt = V.turBul("litofan"), liz = lt.ornek_kanit_izni;
    lt.ornek_kanit_izni = ["baski"];
    V.ornekler.splice(0, V.ornekler.length, { ...r, tur: "litofan" }, { ...r, kanit: "uydurma" });
    s.IZINSIZ = V.ornekSayisi("litofan") === 0 && V.ornekSayisi("plaket") === 0 && (await acik()) === "";
    lt.ornek_kanit_izni = liz;
    V.ornekler.splice(0, V.ornekler.length, r);
    const t = V.turBul("plaket"), iz = t.ornek_kanit_izni;
    delete t.ornek_kanit_izni;
    s.IZINYOK = V.ornekSayisi("plaket") === 0 && (await acik()) === "";
    t.ornek_kanit_izni = iz;
    V.ornekler.splice(0, V.ornekler.length, { ...r, render: "" });
    s.EKSIK = V.ornekSayisi("plaket") === 0 && (await acik()) === "";
    // Litofan kurali AYNEN: basilmis urun fotografi (foto+onizleme+baski) litofani acar.
    V.ornekler.splice(0, V.ornekler.length, { tur: "litofan", olcu_mm: 120, foto: "https://media.pruvo3d.com/t-f.webp",
      onizleme: "https://media.pruvo3d.com/t-o.webp", baski: "https://media.pruvo3d.com/t-b.webp", not: "t" });
    s.LITOFAN_BASKI = V.ornekSayisi("litofan") === 1 && (await acik()) === "litofan";
  } finally {
    V.ornekler.splice(0, V.ornekler.length, ...asil);
    VERI.ornekSayisi = yedek;
    k.kapat();
  }
  return s;
}

console.log("RO) RENDER ORNEGI — plaket gercek baski beklemeden acilir (Okan 7 Eki); kanit izni fail-closed");
{
  const V = veriYukle(VERI_KAYNAK);
  const r = V.ornekler.filter((o) => o.tur === "plaket" && o.kanit === "render");
  ol("RO0 veri dosyasinda 1 plaket render kaydi: onizleme + render media adresi, 120 mm, ozgun foto YOK",
     r.length === 1 && r[0].olcu_mm === 120 && !r[0].foto &&
       /^https:\/\/media\.pruvo3d\.com\/foto\/ornek\/plaket-1-onizleme\.webp$/.test(r[0].onizleme) &&
       /^https:\/\/media\.pruvo3d\.com\/foto\/ornek\/plaket-1-render\.webp$/.test(r[0].render), JSON.stringify(r));
  ol("RO0b kanit izni: plaket [baski,render] · litofan [baski,render] (Okan 7 Eki G1: litofan render ornegiyle acilir)",
     JSON.stringify(V.turBul("plaket").ornek_kanit_izni) === '["baski","render"]' &&
       JSON.stringify(V.turBul("litofan").ornek_kanit_izni) === '["baski","render"]', "");
  const lr = V.ornekler.filter((o) => o.tur === "litofan" && o.kanit === "render");
  ol("RO0c litofan render kaydi: 140 mm, render media adresi, ozgun foto YOK, sayilir",
     lr.length === 1 && lr[0].olcu_mm === 140 && !lr[0].foto && V.ornekSayisi("litofan") === 1 &&
       /^https:\/\/media\.pruvo3d\.com\/foto\/ornek\/litofan-1-render\.webp$/.test(lr[0].render), JSON.stringify(lr));
  const s = await renderSenaryolar(V);
  ol("RO1 render kaydi plaketi ACAR: /foto/acik -> plaket, turHazir hazir", s.ACAR, JSON.stringify(s));
  ol("RO2 izin disi kanit ACMAZ: litofana render 0 · bilinmeyen kanit 0 · /foto/acik kapali", s.IZINSIZ, JSON.stringify(s));
  ol("RO3 turde ornek_kanit_izni yoksa render kaydi SAYILMAZ (fail-closed)", s.IZINYOK, JSON.stringify(s));
  ol("RO4 render gorseli bos render kaydi SAYILMAZ", s.EKSIK, JSON.stringify(s));
  ol("RO5 litofan basilmis urun fotografiyla AYNEN acilir (RO2'nin bos gecmedigi pozitif kontrol)", s.LITOFAN_BASKI, JSON.stringify(s));
  const RO_MUTANTLAR = [
    ["RO-M1 IZIN KONTROLU SILINDI", "if (!k || izin.indexOf(k) < 0) { return false; }", "if (!k) { return false; }", ["IZINSIZ", "IZINYOK"]],
    ["RO-M2 IZIN VARSAYILANI ACIK", "t.ornek_kanit_izni : [];", "t.ornek_kanit_izni : [\"baski\", \"render\"];", ["IZINYOK"]],
    ["RO-M3 RENDER GORSEL SARTI SILINDI", "return !!(o.onizleme && o.render);", "return !!o.onizleme;", ["EKSIK"]],
    ["RO-MK KONTROL", "// Bir türün sayılan örnek sayısı", "// Bir turun sayilan ornek sayisi", []],
  ];
  for (const [ad, capa, yerine, olmeli] of RO_MUTANTLAR) {
    if (VERI_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await renderSenaryolar(veriYukle(VERI_KAYNAK.replace(capa, yerine)));
    const kirmizilar = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
       Object.keys(m).length === 5 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m));
  }
}

// 13:4x (kopru-15) MİMAR BULGUSU: dürüstlük testleri "bilgi:" satırına çevrilip ETKİSİZLEŞTİRİLMİŞTİ.
// Bunlar GERÇEK iddia olarak geri gelir: her render kartında "önizleme/render" etiketi VAR ve
// "gerçek fotoğraf"/"Gerçek örnekler" iddiası 0 · baskı kaydı kartı "Basılmış ürün" der · türün
// ornek_notu (dürüstlük cümlesi) büyütme penceresinde AYNEN görünür.
console.log("ES) EKRAN — 24 kucuk resim: render 'önizleme/render', baski 'basılmış ürün', 'gerçek fotoğraf'/Gerçek örnekler' 0, lightbox ornek_notu AYNEN");
{
  // ES1: render kaydı küçük resim kartında "önizleme/render" etiketi VAR; "gerçek fotoğraf" YOK.
  // ES2: baskı kaydı küçük resim kartında "basılmış ürün" etiketi VAR; "Basılmış ürün (gerçek fotoğraf)" YOK.
  // Ayrıca lightbox'ta ornek_notu AYNEN, "gerçek fotoğraf" YOK, başlık "Gerçek örnekler" YOK.
  const sinifli = (kok, c) => [...kok.agac()].filter((n) => n.classList.contains(c));
  const CUMLE_P = "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, birebir aynısı değildir.";
  const CUMLE_L = "Üretim dosyasının arkadan ışıkla görüntüsüdür; basılmış panel ışık geldiğinde bu görüntüyü verir, birebir aynısı değildir.";
  const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] });
  // ES1 yardımcı: hem render hem baski yollarını dener; mutant uygulanmış kaynakla çağrılınca
  // hangi alt iddianın kırmızıya düştüğünü "kirmizi" dizisinde döner.
  const es1Dene = async (kaynak) => {
    // RENDER yolu (plaket'in render ornegi).
    const Va = veriYukle(VERI_KAYNAK);
    Va.ornekler.splice(0, Va.ornekler.length, ...Va.ornekler.filter((o) => o.tur === "plaket"));
    const eR = await ekranKos(kaynak, Va, { acik: true, turler: [tur("plaket", "Kabartma plaket")] });
    const kucukR = sinifli(eR.bolum, "foto-uretim-galeri-kucuk");
    const plaketKartR = kucukR.find((k) => k.getAttribute("data-tur") === "plaket");
    const etiketR = plaketKartR && sinifli(plaketKartR, "foto-uretim-galeri-kucuk-etiket")[0];
    const etiketMetniR = etiketR && etiketR.textContent;
    const buyukKartYok = sinifli(eR.bolum, "foto-uretim-buyuk-kart").length === 0;
    const baslikR = sinifli(eR.bolum, "foto-uretim-blok-baslik").map((n) => n.textContent)[0] || "";
    const gercekOrnekYok = !/Gerçek örnek/.test(baslikR);
    const tumMetinR = eR.bolum.textContent;
    const gercekFotografKucukYokR = !/gerçek fotoğraf/i.test(tumMetinR);
    if (plaketKartR) { plaketKartR.tetikle("click"); }
    const isikR = [...eR.bolum.parentNode.agac()].find((n) => n.classList.contains("foto-uretim-isik"));
    const isikNotR = isikR && sinifli(isikR, "foto-uretim-isik-not")[0];
    const isikNotMetniR = isikNotR && isikNotR.textContent;
    const isikAltR = isikR && sinifli(isikR, "foto-uretim-isik-alt")[0];
    const isikAltMetniR = isikAltR && isikAltR.textContent;
    const gercekFotografIsikYokR = !/gerçek fotoğraf/i.test(isikAltMetniR || "");
    // BASKI yolu (plaket'in baski ornegi; ES-M1 mutant'ı burayı bozar).
    const Vb = veriYukle(VERI_KAYNAK);
    Vb.ornekler.splice(0, Vb.ornekler.length, { tur: "plaket", kanit: "baski", olcu_mm: 100, foto: "https://media.pruvo3d.com/b-f.webp",
      onizleme: "https://media.pruvo3d.com/b-o.webp", baski: "https://media.pruvo3d.com/b-b.webp", not: "t" });
    const eB = await ekranKos(kaynak, Vb, { acik: true, turler: [tur("plaket", "Kabartma plaket")] });
    const kucukB = sinifli(eB.bolum, "foto-uretim-galeri-kucuk");
    const plaketKartB = kucukB.find((k) => k.getAttribute("data-tur") === "plaket");
    const etiketB = plaketKartB && sinifli(plaketKartB, "foto-uretim-galeri-kucuk-etiket")[0];
    const etiketMetniB = etiketB && etiketB.textContent;
    const tumMetinB = eB.bolum.textContent;
    const gercekFotografKucukYokB = !/gerçek fotoğraf/i.test(tumMetinB);
    if (plaketKartB) { plaketKartB.tetikle("click"); }
    const isikB = [...eB.bolum.parentNode.agac()].find((n) => n.classList.contains("foto-uretim-isik"));
    const isikAltB = isikB && sinifli(isikB, "foto-uretim-isik-alt")[0];
    const isikAltMetniB = isikAltB && isikAltB.textContent;
    const gercekFotografIsikYokB = !/gerçek fotoğraf/i.test(isikAltMetniB || "");
    const kirmizi = [];
    if (etiketMetniR !== "önizleme/render") kirmizi.push("ETIKET_RENDER");
    if (etiketMetniB !== "basılmış ürün") kirmizi.push("ETIKET_BASKI");
    if (!gercekOrnekYok) kirmizi.push("BASLIK_GERCEK_ORNEK");
    if (!gercekFotografKucukYokR) kirmizi.push("KUCUK_RENDER_GERCEK_FOTOGRAF");
    if (!gercekFotografKucukYokB) kirmizi.push("KUCUK_BASKI_GERCEK_FOTOGRAF");
    if (!gercekFotografIsikYokR) kirmizi.push("ISIK_RENDER_GERCEK_FOTOGRAF");
    if (!gercekFotografIsikYokB) kirmizi.push("ISIK_BASKI_GERCEK_FOTOGRAF");
    if (isikNotMetniR !== CUMLE_P) kirmizi.push("ORNEK_NOTU");
    if (!buyukKartYok) kirmizi.push("BUYUK_KART");
    return { kirmizi, etiketMetniR, etiketMetniB, baslikR, isikNotMetniR, isikAltMetniR, isikAltMetniB };
  };
  // ES2 yardımcı: baski kaydı.
  const es2BaskiDene = async (kaynak) => {
    const acikPlaket = { acik: true, turler: [tur("plaket", "Kabartma plaket")] };
    const Vb = veriYukle(VERI_KAYNAK);
    Vb.ornekler.splice(0, Vb.ornekler.length, { tur: "plaket", kanit: "baski", olcu_mm: 100, foto: "https://media.pruvo3d.com/b-f.webp",
      onizleme: "https://media.pruvo3d.com/b-o.webp", baski: "https://media.pruvo3d.com/b-b.webp", not: "t" });
    const e = await ekranKos(kaynak, Vb, acikPlaket);
    const kucuk = sinifli(e.bolum, "foto-uretim-galeri-kucuk");
    const plaketKart = kucuk.find((k) => k.getAttribute("data-tur") === "plaket");
    const etiket = plaketKart && sinifli(plaketKart, "foto-uretim-galeri-kucuk-etiket")[0];
    const etiketMetni = etiket && etiket.textContent;
    const tumMetin = e.bolum.textContent;
    const eskiEtiketYok = !/Basılmış ürün \(gerçek fotoğraf\)/.test(tumMetin);
    const gercekFotografYok = !/gerçek fotoğraf/i.test(tumMetin);
    if (plaketKart) { plaketKart.tetikle("click"); }
    const isik = [...e.bolum.parentNode.agac()].find((n) => n.classList.contains("foto-uretim-isik"));
    const isikNot = isik && sinifli(isik, "foto-uretim-isik-not")[0];
    const isikNotMetni = isikNot && isikNot.textContent;
    const kirmizi = [];
    if (etiketMetni !== "basılmış ürün") kirmizi.push("ETIKET_BASKI");
    if (!eskiEtiketYok) kirmizi.push("ESKI_ETIKET");
    if (!gercekFotografYok) kirmizi.push("GERCEK_FOTOGRAF");
    if (isikNotMetni !== CUMLE_P) kirmizi.push("ORNEK_NOTU");
    return { kirmizi, etiketMetni, eskiEtiketYok, gercekFotografYok, isikNotMetni };
  };
  // ES1 temiz.
  {
    const s = await es1Dene(EKRAN_KAYNAK);
    ol("ES1 render kaydi: kucuk resimde etiket 'önizleme/render' VAR, 'gerçek fotoğraf' 0, 'Gerçek örnekler' 0; lightbox ornek_notu AYNEN, 'gerçek fotoğraf' 0",
       s.kirmizi.length === 0, JSON.stringify(s));
  }
  // ES2 temiz.
  {
    const s = await es2BaskiDene(EKRAN_KAYNAK);
    ol("ES2 baski kaydi: kucuk resimde etiket 'basılmış ürün' VAR; 'Basılmış ürün (gerçek fotoğraf)' 0; lightbox ornek_notu AYNEN",
       s.kirmizi.length === 0, JSON.stringify(s));
  }
  // ES-M1 mutant: lightbox alt metninde "gerçek fotoğraf" geri gelirse ES1 KIRMIZI.
  {
    const capa = "\" — \" + (render ? \"önizleme/render\" : \"basılmış ürün\") + \" · \" + (n + 1) + \"/\" + L;";
    const yerine = "\" — \" + (render ? \"önizleme/render\" : \"gerçek fotoğraf\") + \" · \" + (n + 1) + \"/\" + L;";
    const mut = EKRAN_KAYNAK.replace(capa, yerine);
    if (mut === EKRAN_KAYNAK) { ol("ES-M1 lightbox alt metni 'gerçek fotoğraf' yapildi -> capa bulundu", false, capa); }
    else {
      const s = await es1Dene(mut);
      const beklenen = ["ISIK_BASKI_GERCEK_FOTOGRAF"].sort();
      ol("ES-M1 lightbox alt metni 'gerçek fotoğraf' yapildi -> ES1 KIRMIZI tam olarak [" + beklenen.join(",") + "]",
         JSON.stringify(s.kirmizi.sort()) === JSON.stringify(beklenen), JSON.stringify(s));
    }
  }
  // ES-M2 mutant: ornek_notu lightbox'a yazılmazsa ES1 KIRMIZI (ORNEK_NOTU).
  {
    const capa = "    S.isik.not.textContent = it.tur.ornek_notu || \"\";\n";
    const yerine = "";
    const mut = EKRAN_KAYNAK.replace(capa, yerine);
    if (mut === EKRAN_KAYNAK) { ol("ES-M2 ornek_notu lightbox'a yazılmadı -> capa bulundu", false, capa); }
    else {
      const s = await es1Dene(mut);
      const beklenen = ["ORNEK_NOTU"].sort();
      ol("ES-M2 ornek_notu lightbox'a yazılmadı -> ES1 KIRMIZI tam olarak [" + beklenen.join(",") + "]",
         JSON.stringify(s.kirmizi.sort()) === JSON.stringify(beklenen), JSON.stringify(s));
    }
  }
}


console.log("ES2) ORNEK GALERISI: 24 KUCUK RESIM + buyutme (13:4x Okan karari; 13:5x galeri = secici)");
{
  const CUMLE_P = "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, birebir aynısı değildir.";
  const CUMLE_L = "Üretim dosyasının arkadan ışıkla görüntüsüdür; basılmış panel ışık geldiğinde bu görüntüyü verir, birebir aynısı değildir.";
  const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] });
  const acikP = { acik: true, turler: [tur("plaket", "Kabartma plaket")] };
  const acikPL = { acik: true, turler: [tur("plaket", "Kabartma plaket"), tur("litofan", "Işıklı fotoğraf paneli (litofan)")] };
  // 13:4x (kopru-15, Okan): büyük örnek görsel KALKAR; 24 küçük resim ızgarası. figur/büst ayrı yer tutucu
  // kart olarak kalır (figur kaydı VERI'den çıkarıldı → yer tutucu; bust kayıtlı → görsel kart).
  const VERI_YT = VERI_KAYNAK.replace(/\n      \{\n        tur: "figur",[\s\S]*?\n      \}(?=\n    \])/, "");
  ol("ES2y fikstur: figur ornegi veri dosyasinda VAR ve fiksturden tam 1 kayit cikti",
     VERI_YT !== VERI_KAYNAK && veriYukle(VERI_KAYNAK).ornekler.length - veriYukle(VERI_YT).ornekler.length === 1, "");
  {
    const g = await ekranKos(EKRAN_KAYNAK, veriYukle(VERI_KAYNAK), acikP);
    const k = [...g.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-galeri-kucuk") &&
      n.getAttribute("data-tur") === "figur");
    const alt = k.length === 1 ? [...k[0].agac()] : [];
    const resimli = alt.some((n) => String(n.tagName || "").toUpperCase() === "IMG" &&
      /figur-1-render\.webp/.test(String(n.src || ""))) &&
      !alt.some((n) => n.classList && n.classList.contains("foto-uretim-galeri-yer-ikon"));
    ol("ES2r gercek veride figur kucuk resmi TEK ve GORSELLI (figur-1-render.webp); yer tutucu ikonu YOK", resimli,
       "figur_kucuk=" + k.length + " alt=" + alt.map((n) => String(n.tagName || "") + ":" + String(n.src || "")).join(","));
  }
  const V0 = veriYukle(VERI_YT);
  const VERI_TURLERI = [...new Set(V0.ornekler.map((o) => o.tur))];
  // YER_TUTUCU: orneksiz türler (figur) → ikonlu kart. bust artık gerçek tür, yer tutucusu ÇİZİLMEZ.
  const YER = ["figur", "bust"].filter((k) => !VERI_TURLERI.includes(k));
  const TOPLAM = VERI_TURLERI.length + YER.length; // görseller + yer tutucular
  const GORSEL = VERI_TURLERI.length;
  ol("ES2a manifest ornek_notu AYNEN: plaket = karar cumlesi · litofan = litofan cumlesi · veride >= 6 tur ornegi",
     V0.turBul("plaket").ornek_notu === CUMLE_P && V0.turBul("litofan").ornek_notu === CUMLE_L && VERI_TURLERI.length >= 6,
     JSON.stringify(VERI_TURLERI));
  const sinifli = (kok, c) => [...kok.agac()].filter((n) => n.classList.contains(c));
  const tusla = (n, key) => { for (const fn of ((n.dinle || {}).keydown || [])) { fn({ key, target: n, preventDefault() {} }); } };
  const senaryo = async (kaynak) => {
    const s = {};
    const a = await ekranKos(kaynak, veriYukle(VERI_YT), acikP);
    const govde = a.bolum.parentNode;
    const kucuk = sinifli(a.bolum, "foto-uretim-galeri-kucuk");
    const kTur = kucuk.map((k) => k.getAttribute("data-tur"));
    // G1 büyük görsel 0 + küçük resim 24/24: yeni yapıda büyük kart YOK (ornek-grup sınıfı 0);
    // tüm görsel + yer tutucu kartları küçük resim ızgarasında.
    s.G1_BUYUK = sinifli(a.bolum, "foto-uretim-ornek-grup").length === 0 &&
      sinifli(a.bolum, "foto-uretim-buyuk-kart").length === 0;
    s.G1_KUCUK = kucuk.length === TOPLAM && kucuk.length === VERI_TURLERI.length + YER.length;
    // GALERI: yalniz plaket acik ama TUM tur ornekleri + YER cizilir; acik tur ONCE, sonra veri sirasi, EN SONDA yer tutucular.
    const beklenenSira = ["plaket"].concat(VERI_TURLERI.filter((t) => t !== "plaket")).concat(YER);
    s.GALERI = kucuk.length === TOPLAM &&
      new Set(kTur).size === TOPLAM && kTur[0] === "plaket" &&
      JSON.stringify(kTur) === JSON.stringify(beklenenSira);
    // YAKINDA: acik olmayan tur kartında "Yakında" rozeti; acik turde YOK; ayrı tür seçici (radio) YOK.
    const yakindaVar = (n) => sinifli(n, "foto-uretim-yakinda").some((x) => x.textContent === "Yakında");
    s.YAKINDA = kucuk.length > 1 &&
      kucuk.every((k, i) => yakindaVar(k) === (kTur[i] !== "plaket")) &&
      [...a.bolum.agac()].filter((n) => n.tagName === "INPUT" && n.name === "foto-tur").length === 0;
    // NOT_KART: görsel kartta kategori adı + "önizleme/render" etiketi (13:4x). Yer tutucuda ikon VAR
    // (Yakında rozeti YAKINDA testinde ayrıca denenir; burada YER kartı sadece ikona bakılır).
    s.NOT_KART = kucuk.every((k) => {
      const kod = k.getAttribute("data-tur");
      if (YER.includes(kod)) { return !!k.querySelector(".foto-uretim-galeri-yer-ikon"); }
      const ad = k.querySelector(".foto-uretim-galeri-kucuk-ad");
      const et = k.querySelector(".foto-uretim-galeri-kucuk-etiket");
      return !!ad && !!et && et.textContent === "önizleme/render" &&
        [...k.agac()].some((n) => n.tagName === "IMG");
    });
    // TEMBEL: ilk gorsel kucuk resim hemen, digerleri loading=lazy; width/height dolu. Yer tutucuda <img> yok.
    const kImg = kucuk.slice(0, GORSEL).map((k) => [...k.agac()].find((n) => n.tagName === "IMG"));
    const kIkon = kucuk.slice(GORSEL).map((k) => [...k.agac()].find((n) => n.classList.contains("foto-uretim-galeri-yer-ikon")));
    s.TEMBEL = kImg.length === GORSEL && kIkon.length === YER.length && kIkon.every((m) => m !== undefined && m !== null) &&
      kImg.every((m, i) => !!m && m.width > 0 && m.height > 0 && (i === 0 ? m.loading !== "lazy" : m.loading === "lazy"));
    // ISIK: kucuk resme tik -> tam ekran diyalog; ok -> sonraki; Esc/×/zemin kapatir; govde kilidi + odak donusu.
    // (mevcut isikAc davranisi; kucuk resimden tek tik ile acilir - 13:4x)
    const isik = () => [...govde.agac()].filter((n) => n.classList.contains("foto-uretim-isik"));
    let odak = null;
    const ac = (idx) => {
      if (typeof idx === "number") {
        // tetikleyen odagini sakla (mevcut isikAc davranisi: kapandiginda geri doner)
        kucuk[idx].focus = () => { odak = kucuk[idx]; };
        kucuk[idx].tetikle("click");
      }
      return isik()[0] || null;
    };
    const d1 = ac(0);
    // 13:5x: tek tık = SEÇ + büyüt. galeriSec çağrısı kucuk[idx].tetikle("click") içinde; ışık
    // kapatmadan HEMEN SONRA "secili" class'ı kartta OLMALI (ES2-M18 mutant'ı galeriSec'i kaldırır;
    // kapatma sonrası isikGoster→galeriSec fallback'i aynı class'ı yeniden koyar — bu yüzden kontrol
    // tık ANINDA yapılır, ISIK sonunda değil).
    const t2HemenSecili = !!kucuk[0] && kucuk[0].classList.contains("secili");
    const im1 = d1 && [...d1.agac()].find((n) => n.tagName === "IMG");
    const alt1 = im1 && im1.alt;
    const kilit = govde.style.overflow === "hidden";
    if (d1) { tusla(d1, "ArrowRight"); }
    const alt2 = im1 && im1.alt;
    if (d1) { tusla(d1, "Escape"); }
    const escKapandi = isik().length === 0 && govde.style.overflow !== "hidden" && odak !== null;
    const d2 = ac(0);
    const x = d2 && [...d2.agac()].find((n) => n.tagName === "BUTTON" && n.getAttribute("aria-label") === "Kapat" && n.textContent === "×");
    if (x) { x.tetikle("click"); }
    const xKapandi = !!x && isik().length === 0;
    const d3 = ac(0);
    if (d3) { d3.tetikle("click"); }
    const zeminKapandi = !!d3 && isik().length === 0;
    s.ISIK = !!d1 && d1.getAttribute("role") === "dialog" && d1.getAttribute("aria-modal") === "true" &&
      alt1 === "Kabartma plaket örnek render" && kilit && !!alt2 && alt2 !== alt1 && / örnek render$/.test(alt2) &&
      escKapandi && xKapandi && zeminKapandi;
    // YER_LIGHTBOX: yer tutucuya tik -> lightbox acilMAZ (gorsel yok; isikAc engeli no-op). M15 mutant
    // (isikAc engeli kalkti) ornekGoster placeholder'a dusup TypeError firlatir.
    const figurI = kTur.indexOf("figur");
    let lightYok = true;
    if (figurI >= 0) {
      try {
        kucuk[figurI].tetikle("click"); kucuk[figurI].tetikle("click"); kucuk[figurI].tetikle("click");
      } catch (e) { lightYok = false; }
      lightYok = lightYok && isik().length === 0;
    }
    s.YER_LIGHTBOX = lightYok;
    // YER_GEZINTI: lightbox ←/→ yer tutucuyu ATLAR. Plaket'ten GORSEL kez ileri -> tum gorselleri dolasip plaket'e geri donmeli.
    let yerAtladi = true;
    if (figurI >= 0) {
      const dY = ac(0);
      if (dY) {
        try {
          for (let yi = 0; yi < GORSEL; yi++) { tusla(dY, "ArrowRight"); }
        } catch (e) { yerAtladi = false; }
        const imSon = dY && [...dY.agac()].find((n) => n.tagName === "IMG");
        const altSon = imSon && imSon.alt || "";
        yerAtladi = yerAtladi && /plaket/i.test(altSon);
        try { tusla(dY, "Escape"); } catch (e) { /* sorun degil */ }
      }
    }
    s.YER_GEZINTI = yerAtladi;
    // G2 BUYUTME 3 TURDE + ESC/×/DIS TIK 3/3: ornek, litofan, yapboz (veri sırasıyla). HER kapatma yolu
    // AYRI sayaçta 3 türde de çalışmalı (Esc silindi mutant'ı sadece Esc sayacını düşürür, × veya dış tık
    // çalışıyor diye G2'Yİ FALSE'a düşürmesin diye; bu yüzden sayaclar ayrı).
    let g2_3tur = 0, g2_esc = 0, g2_x = 0, g2_dis = 0;
    const t3 = ["plaket", "litofan", "yapboz"].map((kod) => kTur.indexOf(kod));
    for (const ti of t3) {
      if (ti < 0) continue;
      // 1. Esc ile kapatma (her seferde yeni lightbox aç).
      const dd = ac(ti);
      if (dd && dd.getAttribute("role") === "dialog" && dd.getAttribute("aria-modal") === "true") { g2_3tur++; }
      if (dd) { tusla(dd, "Escape"); if (isik().length === 0) { g2_esc++; } }
      // 2. × ile kapatma (lightbox hâlâ açıksa yeniden aç).
      const dd2 = ac(ti);
      if (dd2) {
        const xx = [...dd2.agac()].find((n) => n.tagName === "BUTTON" && n.getAttribute("aria-label") === "Kapat" && n.textContent === "×");
        if (xx) { xx.tetikle("click"); if (isik().length === 0) { g2_x++; } }
      }
      // 3. zemine (dialog'a) tıklama ile kapatma.
      const dd3 = ac(ti);
      if (dd3) { dd3.tetikle("click"); if (isik().length === 0) { g2_dis++; } }
    }
    s.G2 = g2_3tur === 3 && g2_esc === 3 && g2_x === 3 && g2_dis === 3;
    // T2 (sayfa-3adim K2): galeri kart tıkı türü SEÇER (slider var + ② açık + "Seçili: …" satırı).
    // 13:5x'te vitrin "₺N'dan itibaren" gösterirdi; K2'de vitrin yok, fiyat ②'de sürgü altında.
    // ES2-M18 mutant'ı galeriSec çağrısını kaldırır → tık anında `secili` class'ı kartta OLMUYOR
    // (t2HemenSecili yakalanır). Slider seçili tür için dolu; "Seçili: …" satırı kart seçimini yansıtır.
    const t2Satir = [...govde.agac()].find((n) => n.id === "foto-galeri-secili");
    const t2Surgu = [...govde.agac()].filter((n) => n.tagName === "INPUT" && n.type === "range");
    const t2Adim2 = [...govde.agac()].find((n) => n.id === "foto-adim2");
    const t2SurguFiyat = [...govde.agac()].find((n) => n.classList.contains("foto-uretim-surgu-fiyat"));
    const t2SurguFiyatMetni = t2SurguFiyat && t2SurguFiyat.textContent;
    const t2SatirMetni = t2Satir && t2Satir.textContent;
    const t2SliderMin = t2Surgu[0] && t2Surgu[0].min;
    const t2SliderMax = t2Surgu[0] && t2Surgu[0].max;
    const t2SliderGecerli = t2Surgu.length >= 1 && +t2SliderMin >= 0 && +t2SliderMax >= +t2SliderMin;
    s.T2 = t2SliderGecerli && t2Adim2 && !t2Adim2.hidden &&
      t2SatirMetni && t2SatirMetni.indexOf("Seçili:") === 0 && t2HemenSecili &&
      /\d+ mm → [\d.,]+ TL/.test(t2SurguFiyatMetni || "");
    return s;
  };
  const s0 = await senaryo(EKRAN_KAYNAK);
  // G1: büyük görsel 0 + küçük resim TÜM ornekler+YER (5 olcu-kritik tur silindi, 24->19)
  ol("G1 buyuk ornek gorsel 0 (ornek-grup + buyuk-kart sifif) + kucuk resim TUM ornek (galeri tek blok; 13:4x)",
     s0.G1_BUYUK && s0.G1_KUCUK, JSON.stringify(s0));
  // G2: 3 türde büyütme + Esc/×/dış tık 3/3
  ol("G2 buyutme 3 turde (plaket/litofan/yapboz) + Esc/x/dis-tik kapatma 3/3",
     s0.G2, JSON.stringify(s0));
  ol("ES2b galeri TUM tur ornekleri + yer tutucu (toplam " + TOPLAM + " kucuk resim; " + GORSEL + " gorselli + " + YER.length + " yer tutucu; acik tur once)",
     s0.GALERI, JSON.stringify(s0));
  ol("ES2c acik olmayan tur kartinda 'Yakında' rozeti; acik turde yok; ayrı tur secici (radio name='foto-tur') YOK",
     s0.YAKINDA, JSON.stringify(s0));
  ol("ES2g kucuk resimler: ilk gorsel hemen, digerleri loading=lazy; width/height dolu; yer tutucuda ikon span",
     s0.TEMBEL, JSON.stringify(s0));
  ol("ES2d kucuk resimde kategori adi + 'önizleme/render' etiketi (13:4x); yer tutucuda ikon + Yakinda rozeti",
     s0.NOT_KART, JSON.stringify(s0));
  ol("ES2m yer tutucuda lightbox acilMAZ (gorsel yok); birden fazla tekrar tıklamada da acilMAZ",
     s0.YER_LIGHTBOX, JSON.stringify(s0));
  ol("ES2n lightbox gezintisi yer tutucuyu ATLAR (←/→ GORSEL kez ileri -> Figur alt gorunmez)",
     s0.YER_GEZINTI, JSON.stringify(s0));
  ol("ES2h tam ekran: role=dialog aria-modal · alt '<tur> örnek render' · govde kilidi · ok ile sonraki · Esc/×/zemin kapatir · odak doner", s0.ISIK, JSON.stringify(s0));
  const ES2_MUT = [
    ["ES2-MK KONTROL (yorum eklendi)", "  function isikGoster(n) {\n", "  // kontrol\n  function isikGoster(n) {\n", []],
    // 13:5x: ayrı tür radyo listesi kalktı → M1'in hedefi (radyo üret) artık yok; mutant uygulanamaz.
    // Kalan mutantlar yeni davranışı dener (galeri = seçici).
    ["ES2-M3 kucuk resimde 'Yakında' etiketi dustu", "        if (it.yakinda) d.appendChild(el(\"span\", \"foto-uretim-yakinda\", \"Yakında\"));\n", "", ["YAKINDA"]],
    ["ES2-M5 Esc isleyicisi silindi", "if (e.key === \"Escape\" || e.key === \"Esc\") {", "if (false) {", ["G2", "ISIK"]],
    ["ES2-M6 × kapatmiyor", "\"×\", \"Kapat\", function () { isikKapat(); });", "\"×\", \"Kapat\", function () {});", ["G2", "ISIK"]],
    ["ES2-M7 aria-modal dustu", "    kutu.setAttribute(\"aria-modal\", \"true\");\n", "", ["G2", "ISIK"]],
    ["ES2-M8 govde kilidi kalkmiyor", "document.body.style.overflow = ik.tasma || \"\";", "document.body.style.overflow = \"hidden\";", ["ISIK"]],
    ["ES2-M9 tum kucuk resimler lazy", "        if (n > 0) im.loading = \"lazy\";\n", "        im.loading = \"lazy\";\n", ["TEMBEL"]],
    // 13:5x: Yakında tur vitrin fiyatini guncellemez — galeriSec kontrolu (Yakında/yer tutucu guard kalkarsa
    // galeriSec Yakında'da varm türü degistirip form'u acar + fiyat satirini gunceller; beklenen hüküm:
    // galeriSec tüm ID'lerinde geri dondurmeli).
    ["ES2-M4 'Yakında' tur vitrin fiyatini gunceller",
     "    if (it.yerTutucu || it.yakinda) return;\n",
     "    if (false) return;\n", []],
    // 13:5x: seçici kart tıkı türü değiştirmiyor → galeriSec cagrisi kalkarsa (sadece isikAc) form/slider/
    // vitrin/uretici notu hep bos kalir (galeriSec zorunlu). T2 davranisi test edilir.
    ["ES2-M18 seçici kart tıkı türü değiştirmiyor (13:5x) -> T2 KIRMIZI",
     "          if (!it.yerTutucu && !it.yakinda) galeriSec(n);\n          isikAc(n, d);",
     "          isikAc(n, d);", ["T2"]],
    // 13:5x: Yakında kart seçilebilir hale geldi → galeriSec no-op guard kalkarsa TIK_test KIRMIZI
    ["ES2-M19 Yakında kart seçilebilir hale geldi (13:5x guard kalkti)",
     "    if (it.yerTutucu || it.yakinda) return;\n",
     "", []],
    // YER TUTUCU lightbox/atlama mutantlari (mevcut davranis AYNI).
    ["ES2-M15 yer tutucuda lightbox engeli kalkti (gorsel olmadan acilir)",
     "    if (!acIt || acIt.yerTutucu) return;\n", "", ["YER_LIGHTBOX"]],
    ["ES2-M16 lightbox yer tutucuyu ATLAMIYOR (←/→ figur/bust'e iner; navigations crash)",
     "    } while (S.galeriListe[n].yerTutucu && ilerleme <= L);\n    if (S.galeriListe[n].yerTutucu) return; // tüm liste yer tutucu (defansif; gerçekte olmaz)\n",
     "    } while (ilerleme <= L);\n", ["YER_GEZINTI"]],
  ];
  for (const [ad, capa, yerine, olmeli] of ES2_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await senaryo(EKRAN_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli), JSON.stringify(m));
  }
}

// T2 (sayfa-3adim K2): galeri kart tıkı ① → ② açar; ② içinde slider + fiyat satırı ("N mm → X TL" biçimi).
// 13:5x'te vitrin "₺N'dan itibaren" gösterirdi; K2'de vitrin yok, fiyat ②'de sürgü altında.
// 3 türde (plaket/litofan/kutu — kutu türetilmiş eksen) S.tur set + ② açılır.
console.log("T2) SECICI KART TIKLA TUR SECER — slider + sürgü fiyat satiri (K2: vitrin yok)");
{
  const sinifli = (kok, c) => [...kok.agac()].filter((n) => n.classList.contains(c));
  const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] });
  const acik3 = { acik: true, turler: [tur("plaket", "Kabartma plaket"), tur("litofan", "Işıklı fotoğraf paneli (litofan)"), tur("kutu", "Düzenleyici kutu")] };
  const senaryoT2 = async (kaynak) => {
    const e = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), acik3);
    const kucuk = sinifli(e.bolum, "foto-uretim-galeri-kucuk");
    const kTur = kucuk.map((k) => k.getAttribute("data-tur"));
    const hedef = ["plaket", "litofan", "kutu"].map((kod) => kTur.indexOf(kod));
    let t2_ok = 0;
    const iz = [];
    for (const ti of hedef) {
      if (ti < 0) continue;
      kucuk[ti].tetikle("click");
      // K2: tür seçildi → ② açılır (adim2 hidden=false); sürgü çizilir; sürgü altında "100 mm → 1.000 TL" yazısı.
      const adim2 = [...e.bolum.agac()].find((n) => n.id === "foto-adim2");
      const adim2Acik = adim2 && !adim2.hidden;
      const seciliSatir = [...e.bolum.agac()].find((n) => n.id === "foto-galeri-secili");
      const seciliMetni = seciliSatir && seciliSatir.textContent;
      const surguler = [...e.bolum.agac()].filter((n) => n.tagName === "INPUT" && n.type === "range");
      const hedefKod = kTur[ti];
      // kutu türetilmiş eksen (slider'ı yok, en_mm number input). litofan/plaket slider'lı.
      const sliderBeklenen = hedefKod !== "kutu";
      const sliderVar = surguler.length >= 1;
      const sliderMin = surguler[0] && surguler[0].min;
      const sliderMax = surguler[0] && surguler[0].max;
      const sliderGecerli = !sliderBeklenen || (sliderVar && +sliderMin >= 0 && +sliderMax >= +sliderMin);
      // Sürgü altındaki fiyat satırı: K2'de vitrin yok; "100 mm → 1.000 TL" biçimi sürgü-fiyat class'ında.
      // Türetilmiş eksen türde (kutu) ②'de fiyat YOK — S3'te sunucudan gelir; T2 yalnız slider türlerde denetler.
      const fiyatSatir = [...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-surgu-fiyat"));
      const fiyatMetni = fiyatSatir && fiyatSatir.textContent;
      const fiyatBeklenen = hedefKod !== "kutu";
      const fiyatGecerli = !fiyatBeklenen || /100 mm → 1\.000 TL/.test(fiyatMetni || "");
      iz.push({ hedefKod, adim2Acik, fiyatMetni, seciliMetni, sliderVar, sliderBeklenen, sliderMin, sliderMax });
      if (adim2Acik && fiyatGecerli && sliderGecerli &&
          seciliMetni && seciliMetni.indexOf("Seçili:") === 0) {
        t2_ok++;
      }
    }
    return { T2: t2_ok === 3, iz };
  };
  const t2 = await senaryoT2(EKRAN_KAYNAK);
  ol("T2 kart tıkı 3 turde (plaket/litofan/kutu) S.tur set + ② açık + slider + '100 mm → 1.000 TL' (K2)",
     t2.T2, JSON.stringify(t2));
}

console.log("FM) FORM ALANLARI + ONIZLEMESIZ D TURU (sentetik manifest satiri, vm kopyasinda)");
{
  const SONRA = "Önizleme, üretim dosyasıyla birlikte hazırlanır; birkaç dakika sürebilir.";
  // Sentetik kod gercek manifest satirlariyla CAKISMAZ (G2'de gercek `isimlik` satiri geldi; turBul ilkini doner).
  const sentetik = (kaynakVeri) => {
    const V = veriYukle(kaynakVeri);
    V.turler.push({ kod: "sentetik-d", ad: "İsimlik", aciklama: "x", girdi: ["form"], motor: "D", uretec: "isimlik_uret",
      olcu_mm: { en_az: 80, en_cok: 200 }, renk_bolgeleri: [], malzemeler: {},
      form: { yazi: { tip: "metin", max: 20 }, kalinlik: { tip: "sayi", min: 2, max: 6, adim: 1, birim: "mm" },
              yazi_tipi: { tip: "secim", secenekler: ["Düz", "Eğik"] }, link: { tip: "url" },
              kapak: { tip: "bool", etiket: "Kapak", varsayilan: true } },
      fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 }, ornek_kanit_izni: ["render"], ornek_notu: "t" });
    V.ornekler.push({ tur: "sentetik-d", kanit: "render", olcu_mm: 100, onizleme: "https://media.pruvo3d.com/t-io.webp",
      render: "https://media.pruvo3d.com/t-ir.webp", not: "t" });
    const asil = V.parametreDogrula;
    V.cagri = [];
    V.parametreDogrula = function (kod, p) { const d = asil(kod, p); V.cagri.push({ kod, p: JSON.stringify(p), d }); return d; };
    return V;
  };
  const acikI = { acik: true, turler: [{ kod: "sentetik-d", ad: "İsimlik", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  const acikP = { acik: true, turler: [{ kod: "plaket", ad: "Kabartma plaket", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] }] };
  // 13:5x: tur secimi galeriden; form alanlari sadece tur secildikten sonra cizilir. sentetik-d kayit
  // (sentetik-d ornegi) ile sentetik-d listede VAR; sessionStorage ile onceden sec. `is` YOK → S1 paneli.
  const sentetikKayit = { tur: "sentetik-d", olcu: 100 };
  const senaryo = async (kaynak) => {
    const s = {};
    const V = sentetik(VERI_KAYNAK);
    const e = await ekranKos(kaynak, V, acikI, sentetikKayit);
    const d = [...e.bolum.agac()];
    const id = (x) => d.find((n) => n.id === x) || null;
    const y = id("foto-param-yazi"), k = id("foto-param-kalinlik"), t = id("foto-param-yazi_tipi"), u = id("foto-param-link");
    s.ALANLAR = !!(y && k && t && u) && y.tagName === "INPUT" && y.type === "text" && y.maxLength === 20 &&
      k.type === "number" && k.min === "2" && k.max === "6" && k.step === "1" &&
      t.tagName === "SELECT" && t.childNodes.filter((n) => n.tagName === "OPTION").length === 2 && u.type === "url";
    // AYNI FONKSIYON: hata metni VERI.parametreDogrula donusunden; alanlar doldurulunca hata gizlenir.
    const hata = d.find((n) => n.classList.contains("foto-uretim-ayrinti") && n.textContent === "Metin alanını doldur (izinli uzunlukta).");
    const ilk = V.cagri.length > 0 && V.cagri.every((c) => c.kod === "sentetik-d") && V.cagri[V.cagri.length - 1].d.hata === "parametre-metin";
    let son = null;
    if (y && u) {
      y.value = "Ada"; y.tetikle("input");
      u.value = "https://ornek.com"; u.tetikle("input");
      son = V.cagri[V.cagri.length - 1];
    }
    s.AYNI_FONKSIYON = ilk && !!hata && !!son && son.d.ok === true &&
      son.p === JSON.stringify({ yazi: "Ada", kalinlik: 2, yazi_tipi: "Düz", link: "https://ornek.com", kapak: true }) && hata.hidden === true;
    // BOOL (kopru-15 sözlük): tip "bool" -> onay kutusu (label for=id, etiket manifestten), varsayılan
    // manifestten (true -> işaretli); işareti kaldırınca gövdede JSON false (dize DEĞİL) ve doğrulama ok.
    const kb = id("foto-param-kapak");
    const kbEtiket = d.find((n) => n.tagName === "LABEL" && n.getAttribute("for") === "foto-param-kapak");
    let kbSon = null;
    if (kb) { kb.checked = false; kb.tetikle("change"); kbSon = V.cagri[V.cagri.length - 1]; }
    s.BOOL = !!kb && kb.tagName === "INPUT" && kb.type === "checkbox" && !!kbEtiket && kbEtiket.textContent === "Kapak" &&
      !!kbSon && kbSon.d.ok === true && JSON.parse(kbSon.p).kapak === false;
    if (kb) { kb.checked = true; kb.tetikle("change"); }
    // ONIZLEMESIZ D: ornek render + SONRA metni; litofan tuvali yok; siparis butonu acilmaz.
    const sonra = d.find((n) => n.tagName === "P" && n.textContent === SONRA);
    const kap = sonra ? sonra.parentNode : null;
    const btn = id("foto-onizle-buton");
    s.ONIZLEMESIZ = !!kap && kap.hidden === false && [...kap.agac()].some((n) => n.tagName === "IMG" && /t-ir\.webp$/.test(n.src)) &&
      !d.some((n) => n.tagName === "CANVAS") && !!btn && btn.disabled === true &&
      !d.some((n) => n.tagName === "P" && /tarayıcında çizilir/.test(n.textContent) && n.parentNode && !n.parentNode.hidden);
    // TEK ONAY KUTUSU (taslak-2, 7 Eki 20:5x): form girdili turde de GORUNUR; eski iki kutu 0.
    const tekKutu = (dd) => {
      const k_ = dd.find((n) => n.id === "foto-aydinlatma-onay");
      const det = dd.find((n) => n.tagName === "DETAILS" && n.classList.contains("foto-uretim-aydinlatma"));
      const sira = det && k_ ? dd.indexOf(k_) > dd.indexOf(det) : false;   // kutu metnin ALTINDA
      return !!k_ && k_.type === "checkbox" && !!k_.parentNode && k_.parentNode.hidden !== true && sira &&
        k_.parentNode.textContent.trim() === "Aydınlatma metnini okudum, onaylıyorum." &&
        !dd.some((n) => n.id === "foto-hak" || n.id === "foto-aktarim");
    };
    s.TEK_KUTU_FORM = tekKutu(d);
    // URETEC ONIZLEME (madde 11): onay + dogrulama sonrasi buton ACILIR; tiklaninca /foto/onizleme'ye
    // foto'suz govde (tur + parametreler) gider, litofan ucu cagrilmaz, yoklama araligi 5 sn.
    const V2 = sentetik(VERI_KAYNAK);
    const e2 = await ekranKos(kaynak, V2, acikI, sentetikKayit, { asama: "bekliyor" },
      { turnstileOto: true, zamanlayici: true, postYanit: { is: "a".repeat(32), kalan: 2 } });
    const d2 = [...e2.bolum.agac()];
    const id2 = (x) => d2.find((n) => n.id === x) || null;
    const y2 = id2("foto-param-yazi"), u2 = id2("foto-param-link"), btn2 = id2("foto-onizle-buton");
    if (y2 && u2) { y2.value = "Ada"; y2.tetikle("input"); u2.value = "https://ornek.com"; u2.tetikle("input"); }
    // Kutu isaretlenmeden buton KAPALI (form + dogrulama tam olsa da); isaretlenince ACILIR.
    const kapali = !!btn2 && btn2.disabled === true;
    const on2 = id2("foto-aydinlatma-onay");
    if (on2) { on2.checked = true; on2.tetikle("change"); }
    s.KUTU_SART = kapali && !!btn2 && btn2.disabled === false;
    const acildi = !!btn2 && btn2.disabled === false && btn2.textContent === "Önizleme oluştur";
    if (btn2) { btn2.tetikle("click"); }
    for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
    const p0 = e2.istekler[0] || {};
    s.KUYRUK = acildi && e2.istekler.length === 1 && p0.u === "/api/shop/foto/onizleme" &&
      p0.govde.tur === "sentetik-d" && p0.govde.aydinlatma_onay === true && p0.govde.onay_surum === V2.onay_surum &&
      !("hak_onay" in p0.govde) && !("aktarim_onay" in p0.govde) && p0.govde.turnstile_token === "t-jeton" &&
      p0.govde.gorsel === undefined && JSON.stringify(p0.govde.parametreler) ===
        JSON.stringify({ yazi: "Ada", kalinlik: 2, yazi_tipi: "Düz", link: "https://ornek.com", kapak: true }) &&
      e2.araliklar.includes(5000) && !e2.araliklar.includes(3000);
    // PLAKET: form {} -> alan yok, SONRA metni yok.
    const p = await ekranKos(kaynak, sentetik(VERI_KAYNAK), acikP, { is: "b".repeat(32), tur: "plaket", olcu: 120 });
    const dp = [...p.bolum.agac()];
    s.PLAKET = !dp.some((n) => String(n.id || "").startsWith("foto-param-")) && !dp.some((n) => n.textContent === SONRA && n.tagName === "P");
    s.TEK_KUTU_PLAKET = tekKutu(dp);
    return s;
  };
  const s0 = await senaryo(EKRAN_KAYNAK);
  ol("FM1 form alanlari manifestten: metin(max 20) · sayi(2–6, adim 1) · secim(2) · url", s0.ALANLAR, JSON.stringify(s0));
  ol("FM2 istemci dogrulamasi = VERI.parametreDogrula (hata metni ondan; doldurunca ok + govde semaya uygun)", s0.AYNI_FONKSIYON, JSON.stringify(s0));
  ol("FM3 onizlemesiz D turu: ornek render + '" + SONRA + "' · tuval/litofan onizleme metni 0 · buton kapali", s0.ONIZLEMESIZ, JSON.stringify(s0));
  ol("FM1b bool alan: onay kutusu (etiketli, varsayilan isaretli) · isaret kalkinca govdede kapak:false (boolean) + dogrulama ok", s0.BOOL, JSON.stringify(s0));
  ol("FM4 plaket (form {}): parametre alani 0, onizleme-sonra metni 0", s0.PLAKET, JSON.stringify(s0));
  ol("FM5 onizlemesiz D: buton onay+dogrulamayla ACILIR -> /foto/onizleme kuyrugu (foto'suz, parametreli), yoklama 5 sn", s0.KUYRUK, JSON.stringify(s0));
  ol("FM6 TEK onay kutusu 'foto-aydinlatma-onay' aydinlatma metninin ALTINDA, form turunde ve plakette GORUNUR; eski 2 kutu 0",
    s0.TEK_KUTU_FORM && s0.TEK_KUTU_PLAKET, JSON.stringify(s0));
  ol("FM7 kutu isaretsizken 'Önizleme oluştur' DISABLED, isaretlenince acilir; govdede aydinlatma_onay + surum (eski alan 0)",
    s0.KUTU_SART && s0.KUYRUK, JSON.stringify(s0));
  const FM_MUT = [
    ["FM-M1 istemci kendi dogrulamasi (her sey gecerli)", "return F.parametreDogrula(S.tur, parametreGovde());", "return { ok: true };", ["AYNI_FONKSIYON", "BOOL"]],
    ["FM-M2 onizleme-sonra metni dustu", "S.alanOnizlemeSonra.appendChild(el(\"p\", \"foto-uretim-ayrinti\", ONIZLEME_SONRA));", "", ["ONIZLEMESIZ"]],
    ["FM-M3 tarayici onizleyici kosulu silindi (her D litofan sayilir)",
     "F.kolu(S.tur) === \"deterministik\" && F.TARAYICI_ONIZLEYICI[t.uretec] === true);", "F.kolu(S.tur) === \"deterministik\");", ["KUTU_SART", "KUYRUK", "ONIZLEMESIZ"]],
    ["FM-M4 uretec onizleme yonlendirmesi silindi (plaket/saglayici yoluna duser)",
     "    if (onizlemeSonraSecili()) { uretecOnizle(); return; }\n", "", ["KUYRUK"]],
    ["FM-M5 uretec yoklama araligi plaketinki", "var aralik = uretec ? URETEC_YOKLAMA_MS : YOKLAMA_MS;", "var aralik = YOKLAMA_MS;", ["KUYRUK"]],
    ["FM-M6 buton kutusuz acilir (S1 kapisi silindi)",
     "    var tam = uyumOK && (!!S.dosya || !fotoGerekir()) && !!S.aydinlatmaOnay &&",
     "    var tam = uyumOK && (!!S.dosya || !fotoGerekir()) &&", ["KUTU_SART"]],
    ["FM-M7 aydinlatma metni dustu (kutu metinsiz kalir)", "    S.alanOnay.appendChild(det);\n\n", "", ["TEK_KUTU_FORM", "TEK_KUTU_PLAKET"]],
    ["FM-M8 govdeye onay alani girmedi", "aydinlatma_onay: !!S.aydinlatmaOnay, onay_surum: F.onay_surum,", "onay_surum: F.onay_surum,", ["KUYRUK"]],
    ["FM-M9 bool degeri dize olarak yazilir", "S.parametre[a] = e.target.checked === true;", "S.parametre[a] = String(e.target.checked);", ["BOOL"]],
    ["FM-M10 bool dali silindi (duz metin kutusu)", "} else if (sema.tip === \"bool\") {", "} else if (false) {", ["AYNI_FONKSIYON", "BOOL", "KUTU_SART", "KUYRUK"]],
    ["FM-MK kontrol (yorum)", "// FORM ALANLARI — türün", "// form alanlari — turun", []],
  ];
  for (const [ad, capa, yerine, olmeli] of FM_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await senaryo(EKRAN_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli), JSON.stringify(m));
  }
}

// ================================================================ TD — TURETILMIS EKSEN: PARAMETRE DEGISIR -> 2. ONIZLEME -> FIYAT GUNCEL
// (kopru-15 DOM vakasi, RAPOR-DILIM3 §2 (1)). Gercek "kutu" kaydi (olcu_ekseni turetilmis) sahte DOM'da:
// 1. durum yaniti en uzun 100 mm -> "100 mm → 1.000 TL" · en_mm 140 yapilip YENI onizleme istenir -> o anda
// fiyat satiri "hesaplaniyor" (eski fiyat GORUNMEZ), siparis dugmesi YOK/KAPALI · 2. durum yaniti 140 mm ->
// "140 mm → 1.400 TL". Olculmus fiyati olmayan hazir yanitta siparis dugmesi KAPALI (fiyatsiz siparis yok).
{
  const tdAcik = { acik: true, turler: [{ kod: "kutu", ad: "Düzenleyici kutu", aciklama: "x", ornek_sayisi: 1,
    olculer: [{ mm: 40, fiyat_kurus: 40000 }] }] };
  const bekle = async () => { for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); } };
  const TD_ALANLAR = ["FIYAT1", "HESAPLANIYOR", "DUGME", "FIYAT2"];
  const tdSenaryo = async (kaynak) => {
    const s = { FIYAT1: false, HESAPLANIYOR: false, DUGME: false, FIYAT2: false };
    const durum = { asama: "bekliyor" };
    const durumKoy = (v) => { for (const k of Object.keys(durum)) { delete durum[k]; } Object.assign(durum, v); };
    // 13:5x: tür seçimi galeri kartından; S.tur = "kutu" önceden seçili (sessionStorage `pruvo_foto_tur`).
    // kayit'te `is` VAR → sayfa S.tur/S.olcu'yu yükler; `ilkDurumBos` ilk /foto/durum çağrısını "not ok"
    // yapar → sayfa S1'de kalır (form çizilir). POST /foto/onizleme onizle butonuyla atılır.
    const tdKayit = { tur: "kutu", olcu: 100, is: "b".repeat(32) };
    const e = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), tdAcik, tdKayit, durum,
      { turnstileOto: true, zamanlayici: true, ilkDurumBos: true, postYanit: { is: "b".repeat(32), kalan: 2 } });
    const dd = () => [...e.bolum.agac()];
    const id = (x) => dd().find((n) => n.id === x) || null;
    const fiyatSatiri = () => (dd().find((n) => n.classList.contains("foto-uretim-olculen-fiyat")) || { textContent: null }).textContent;
    const sipAcik = () => dd().filter((n) => n.tagName === "BUTTON" && n.textContent === "Sepete ekle" && n.disabled !== true).length;
    const sipVar = () => dd().filter((n) => n.tagName === "BUTTON" && n.textContent === "Sepete ekle").length;
    // K2b: B2 tikleme ③'te (S3 render sonrası). onizle() yalnız önizleme isteği atar; yokla() sonrası b2Tikle S3'ü açar.
    const b2Tikle = () => { const b2 = id("foto-b2-onay"); if (b2 && !b2.checked) { b2.checked = true; b2.tetikle("change"); } };
    const onizle = async (enMm) => {
      const en = id("foto-param-en_mm");
      if (en && enMm != null) { en.value = String(enMm); en.tetikle("input"); }
      const on = id("foto-aydinlatma-onay");
      if (on) { on.checked = true; on.tetikle("change"); }
      // K2b: B2 yalnız ③'te; önizleme isteği aydinlatmaOnay + uyum OK + form doğru ile koşar (S.b2Onay S3'te tiklenir).
      const b = id("foto-onizle-buton");
      // DEBUG: buton disabled mı?
      if (b) {
        s.BTN_DISABLED = b.disabled;
        s.BTN_TEXT = b.textContent;
        // Form alanlarını say
        s.INPUT_SAYISI = dd().filter((n) => n.tagName === "INPUT").length;
        s.CAPTCHA_VAR = !!dd().find((n) => n.classList && n.classList.contains("cf-turnstile"));
      }
      if (b) { b.tetikle("click"); }
      await bekle();
    };
    const yokla = async () => {
      const fn = e.yoklamalar[e.yoklamalar.length - 1]; if (fn) { fn(); }
      await bekle();
      // yoklama S3'e düşürdü; B2 tikleyerek "Sepete ekle" aç.
      b2Tikle();
    };
    // 1. onizleme -> durum: en uzun 100 mm, sunucu fiyati 100000 kurus.
    // en_mm=100 verilir (formDogrula için en_mm zorunlu; S.olcu 100 ile uyumlu).
    await onizle(100);
    durumKoy({ asama: "hazir", tur: "kutu", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" });
    await yokla();
    const f1 = fiyatSatiri();
    s.FIYAT1 = e.istekler.length === 1 && f1 === "100 mm → 1.000 TL" && sipAcik() === 1;
    // Parametre degisir (en 100 -> 140): S3'ten forma don, yeni onizleme iste; durum henuz "bekliyor".
    durumKoy({ asama: "bekliyor" });
    const baska = dd().find((n) => n.tagName === "BUTTON" && n.textContent === "Başka fotoğraf dene");
    if (baska) { baska.tetikle("click"); await bekle(); }
    await onizle(140);
    const p2 = e.istekler[1] || { govde: {} };
    const f2a = fiyatSatiri();
    const metin2 = e.bolum.textContent;
    s.HESAPLANIYOR = e.istekler.length === 2 && !!p2.govde.parametreler && p2.govde.parametreler.en_mm === 140 &&
      typeof f2a === "string" && /^Fiyat hesaplanıyor/.test(f2a) && !metin2.includes("1.000 TL") && !metin2.includes("100 mm →");
    const s2Kapali = sipAcik() === 0;
    // 2. durum yaniti: en uzun 140 mm -> "140 mm → 1.400 TL", siparis acilir.
    durumKoy({ asama: "hazir", tur: "kutu", olcu_mm: 140, fiyat_kurus: 140000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" });
    await yokla();
    const f2 = fiyatSatiri();
    s.FIYAT2 = f2 === "140 mm → 1.400 TL" && sipAcik() === 1 && !e.bolum.textContent.includes("1.000 TL");
    // Olculmus fiyati olmayan hazir yanit: siparis dugmesi CIZILIR ama KAPALI.
    const e3 = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), tdAcik, tdKayit, durum,
      { turnstileOto: true, zamanlayici: true, ilkDurumBos: true, postYanit: { is: "c".repeat(32), kalan: 2 } });
    durumKoy({ asama: "bekliyor" });
    const d3 = () => [...e3.bolum.agac()];
    const on3 = d3().find((n) => n.id === "foto-aydinlatma-onay");
    if (on3) { on3.checked = true; on3.tetikle("change"); }
    // K2b: B2 yalnız ③'te; önizleme isteği S.b2Onay'a bağlı DEĞİL. ③'e geçtikten sonra tiklenir.
    const b3 = d3().find((n) => n.id === "foto-onizle-buton");
    if (b3) { b3.tetikle("click"); }
    await bekle();
    durumKoy({ asama: "hazir", tur: "kutu", olcu_mm: 100, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" });
    const fn3 = e3.yoklamalar[e3.yoklamalar.length - 1];
    if (fn3) { fn3(); }
    await bekle();
    const b2s3 = d3().find((n) => n.id === "foto-b2-onay");
    if (b2s3) { b2s3.checked = true; b2s3.tetikle("change"); }
    const sip3 = d3().filter((n) => n.tagName === "BUTTON" && n.textContent === "Sepete ekle");
    s.DUGME = s2Kapali && sipVar() === 1 && sip3.length === 1 && sip3[0].disabled === true;
    Object.defineProperty(s, "iz", { value: { f1, f2a, f2, s2Kapali, sip3: sip3.map((n) => n.disabled), istek: e.istekler.length }, enumerable: false });
    return s;
  };
  const t0 = await tdSenaryo(EKRAN_KAYNAK);
  ol("TD1 turetilmis tur (kutu) 1. durum yaniti en uzun 100 mm -> '100 mm → 1.000 TL', siparis acik", t0.FIYAT1, JSON.stringify([t0, t0.iz]));
  ol("TD2 parametre degisti (en_mm 140) -> yeni onizleme isteginde fiyat satiri 'hesaplanıyor', eski '1.000 TL' GORUNMEZ",
     t0.HESAPLANIYOR, JSON.stringify([t0, t0.iz]));
  ol("TD3 2. yanittan once siparis dugmesi acik DEGIL; olculmus fiyatsiz hazir yanitta siparis KAPALI", t0.DUGME, JSON.stringify([t0, t0.iz]));
  ol("TD4 2. durum yaniti en uzun 140 mm -> '140 mm → 1.400 TL', siparis acik", t0.FIYAT2, JSON.stringify([t0, t0.iz]));
  // K2b: TD-M2 aynı KAPI'yı iki yerde tutuyor (cizS3 inline + guncelleSipButonu). B2 tikleyince guncelleSipButonu
  // çağrılır; tek başına inline silmek yetmez. İki yerden de silmeli.
  const TD_M2_KAYNAK = EKRAN_KAYNAK;
  const TD_M2_MUTANT = TD_M2_KAYNAK.split(" || (nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);").join(";")
    .split(" || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);").join(";");
  const TD_MUT = [
    ["TD-M1 yeni onizleme isteginde fiyat sifirlama silindi", "    S.fiyatKurus = null;\n    var fd = formDogrula();", "    var fd = formDogrula();", ["HESAPLANIYOR"]],
    ["TD-M2 olculmus fiyatsiz siparis dugmesi kapatma silindi (cizS3 + guncelleSipButonu, iki yerden)",
     TD_M2_KAYNAK, TD_M2_MUTANT, ["DUGME"]],
    ["TD-MK kontrol (yorum)", "/* Türetilmiş eksen fiyat satırı:", "/* turetilmis eksen fiyat satiri:", []],
  ];
  for (const [ad, capa, yerine, olmeli] of TD_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await tdSenaryo(EKRAN_KAYNAK.replace(capa, yerine));
    // Sadece 4 test alanına bak (debug: BTN_DISABLED/BTN_TEXT/INPUT_SAYISI/CAPTCHA_VAR dışı).
    const kirmizi = Object.keys(m).filter((x) => TD_ALANLAR.indexOf(x) >= 0 && m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli), JSON.stringify([m, m.iz]));
  }
}

// ================================================================ AK — PLAKET ALT KENAR KALINLIGI

/**
 * Alt kenar senaryolari (fm = foto modulu ya da mutanti). Donus: her biri tuttu mu.
 *   DOGRUDAN: 120 mm plaket (olceksiz) -> alt_kenar_mm 6,5 ±0,1
 *   OLCEKLI : 1200 mm plaket -> 120 mm'ye olceklenir, alt kenar OLCEKLENMIS dosyada 6,5 ±0,1
 *   AKIS    : cron zinciri -> analiz ozetinde alt_kenar_mm 6,5 ±0,1
 *   PANEL   : panel kalem kaydi + "Örnek üretimler" listesi alt_kenar_mm tasir
 */
async function altKenarSenaryolar(fm) {
  const yakin = (x) => typeof x === "number" && Math.abs(x - 6.5) <= 0.1;
  const s = {};
  const d = await fm.ucmfOlcekle(plaketUcmf(1).slice().buffer, 120);
  s.DOGRUDAN = !!d.tampon && d.olcek === 1 && yakin(d.alt_kenar_mm);
  const o = await fm.ucmfOlcekle(plaketUcmf(10).slice().buffer, 120);
  s.OLCEKLI = !!o.tampon && o.olcek > 0 && o.olcek < 1 && yakin(o.alt_kenar_mm);
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  const is = "a".repeat(31) + "b";
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 120, ?, ?, 'hazir', 'gorev-proto-6666', ?)")
    .bind(is, fm.ORNEK_ZIYARETCI, new Date().toISOString(), new Date().toISOString()).run();
  P.protoDurum.set("gorev-proto-6666", 5);
  const no = fm.ORNEK_SIPARIS_ONEK + is.slice(0, 12);
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel, renk_sayisi) VALUES (?, 0, ?, 'plaket', 120, 'build-baslat', ?, '2000-01-01T00:00:00.000Z', 4)")
    .bind(no, is, new Date().toISOString()).run();
  P.ucmf = plaketUcmf(10); P.analiz = "healthy";
  for (let i = 0; i < 10; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
  P.ucmf = null;
  const u = await k.d1.prepare("SELECT asama, analiz FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
  let an = {};
  try { an = JSON.parse((u && u.analiz) || "{}"); } catch (e) { an = {}; }
  s.AKIS = !!u && u.asama === "onarim-bekliyor" && yakin(an.alt_kenar_mm);
  const kayit = fm.panelFotoKaydi("PR-AK", 0, { foto_is: is, foto_tur: "plaket", olcu_mm: 120 },
    new Map([["PR-AK|0", { asama: "hazir", analiz: u ? u.analiz : "" }]]));
  const liste = await (await fm.panelOrnekListe(e2)).json();
  const lk = (liste.ornekler || []).find((x) => x.siparis_no === no);
  s.PANEL = yakin(kayit.alt_kenar_mm) && !!lk && yakin(lk.alt_kenar_mm);
  k.kapat();
  return s;
}

console.log("AK) PLAKET ALT KENAR KALINLIGI — ayak ureteci girdisi alt_kenar_mm (TeKiN bulgusu 6 Eki)");
{
  const s = await altKenarSenaryolar(foto);
  ol("AK1 120 mm plaket (olceksiz) -> alt_kenar_mm 6,5 ±0,1", s.DOGRUDAN, JSON.stringify(s));
  ol("AK2 1200 mm plaket -> 120 mm'ye olcekli dosyada alt_kenar_mm 6,5 ±0,1", s.OLCEKLI, JSON.stringify(s));
  ol("AK3 cron zinciri -> analiz ozetinde alt_kenar_mm 6,5 ±0,1 (asama hazir)", s.AKIS, JSON.stringify(s));
  ol("AK4 panel kalem kaydi + ornek listesi alt_kenar_mm tasir", s.PANEL, JSON.stringify(s));
  ol("AK5 serit eni sabiti 10 mm (ayak ureteci tanimi: alttaki ~10 mm serit)", foto.ALT_KENAR_SERIT_MM === 10, String(foto.ALT_KENAR_SERIT_MM));
}

// ================================================================ MUTANTLAR

console.log("RKU) KOSULLU RENK BOLGESI EKRANDA — pasif bolgenin seçicisi GIZLI, koşul açılınca görünür (BaBa 8 Eki 16:0x)");
{
  // Sentetik D satiri: logo deseni (taban Var/Yok + taban rengi yalniz "Var"da) + ses deseni (baslik dolu -> yazi).
  const sentetikR = (kaynakVeri) => {
    const V = veriYukle(kaynakVeri);
    V.turler.push({ kod: "sentetik-r", ad: "Logo", aciklama: "x", girdi: ["form"], motor: "D", uretec: "isimlik_uret",
      olcu_mm: { en_az: 80, en_cok: 200 },
      renk_bolgeleri: [{ kod: "taban", ad: "Taban", renkler: ["Beyaz", "Siyah"] },
                       { kod: "logo", ad: "Logo", renkler: ["Siyah", "Beyaz"] },
                       { kod: "yazi", ad: "Yazı", renkler: ["Kırmızı", "Beyaz"] }],
      renk_kosul: { taban: [{ alan: "taban", degerler: ["Var"] }], yazi: [{ alan: "baslik", dolu: true }] },
      malzemeler: {},
      form: { taban: { tip: "secim", etiket: "Taban", secenekler: ["Yok", "Var"] }, baslik: { tip: "metin", max: 20, zorunlu: false, varsayilan: "" } },
      fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 3 }, ornek_kanit_izni: ["render"], ornek_notu: "t" });
    V.ornekler.push({ tur: "sentetik-r", kanit: "render", olcu_mm: 100, onizleme: "https://media.pruvo3d.com/t-io.webp",
      render: "https://media.pruvo3d.com/t-ir.webp", not: "t" });
    return V;
  };
  const acikR = { acik: true, turler: [{ kod: "sentetik-r", ad: "Logo", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  const rku = async (kaynak) => {
    const s = {};
    const e = await ekranKos(kaynak, sentetikR(VERI_KAYNAK), acikR, { tur: "sentetik-r", olcu: 100 });
    const d = () => [...e.bolum.agac()];
    const grup = (b) => d().find((n) => n.getAttribute && n.getAttribute("data-renk-bolge") === b) || null;
    const gorunur = (b) => { const g = grup(b); return !!g && g.hidden !== true; };
    const sec = d().find((n) => n.id === "foto-param-taban"), bas = d().find((n) => n.id === "foto-param-baslik");
    // Başlangıç: taban "Yok" (ilk seçenek), başlık boş -> taban + yazı seçicisi GİZLİ, logo görünür.
    s.ILK = !!sec && !!bas && !gorunur("taban") && !gorunur("yazi") && gorunur("logo");
    if (sec) { sec.value = "Var"; sec.tetikle("change"); }
    if (bas) { bas.value = "Ada"; bas.tetikle("input"); }
    s.ACIK = gorunur("taban") && gorunur("yazi") && gorunur("logo");
    if (sec) { sec.value = "Yok"; sec.tetikle("change"); }
    s.GERI = !gorunur("taban") && gorunur("yazi");
    return s;
  };
  const s = await rku(EKRAN_KAYNAK);
  ol("RKU1 taban 'Yok' + başlık boş -> taban/yazı renk seçicisi GİZLİ, logo görünür", s.ILK === true, JSON.stringify(s));
  ol("RKU2 taban 'Var' + başlık dolu -> iki seçici görünür; taban 'Yok'a dönünce yeniden gizli", s.ACIK === true && s.GERI === true, JSON.stringify(s));
  const m = await rku(EKRAN_KAYNAK.replace("      if (b) d[i].hidden = !F.renkBolgesiAktif(S.tur, b, p);\n", ""));
  ol("RKU-M1 gizleme satırı silindi -> RKU KIRMIZI", m.ILK === false, JSON.stringify(m));
}

console.log("MUTANTLAR (gecici kopya; calisma agacina yazilmaz)");
const GECICI = path.join(SHOP, "foto-test-tmp-" + process.pid);
process.on("exit", () => { fs.rmSync(GECICI, { recursive: true, force: true }); });
const ASIL = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
let mutantNo = 0;

async function mutantModul(capa, yerine) {
  if (ASIL.split(capa).length - 1 !== 1) { return null; }
  fs.mkdirSync(GECICI, { recursive: true });
  const dosya = path.join(GECICI, "foto-" + (++mutantNo) + ".js");
  fs.writeFileSync(dosya, ASIL.replace(capa, yerine));
  return import(url.pathToFileURL(dosya).href);
}

/** Mutanta karsi uc dar senaryo; her biri temiz bir SQLite ile. Donus: {D, E, J} gecti mi. */
async function darSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  const cag = async (yol, govde, ip) => {
    const r = await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, { method: "POST",
      headers: { "CF-Connecting-IP": ip, "Content-Type": "application/json" }, body: JSON.stringify(govde) }),
      e2, new URL("https://pruvo3d.com/api/shop" + yol), yol, null);
    return r.status;
  };
  const sonuc = {};
  const kodlar = [];
  for (let i = 0; i <= VERI.sinir_ziyaretci_24s; i++) { kodlar.push(await cag("/foto/onizleme", onizlemeGovde(), "10.0.0.1")); }
  sonuc.D = kodlar[kodlar.length - 1] === 429;
  P.turnstile = "red";
  sonuc.E = (await cag("/foto/onizleme", onizlemeGovde(), "10.0.0.2")) === 403;
  P.turnstile = "ok";
  const is = "c".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-9999', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  // A: odeme kalemi plaket basina ayak tasir (uretimde unutulmasin).
  const fs_ = await fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }, Date.now());
  sonuc.A = !!fs_.satir && fs_.satir.foto_ayak === 1 && /ayak: 1/.test(fs_.satir.parametre_detay);
  await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES ('PR-TEST-MUT', ?, 'odendi', 1, ?)")
    .bind(new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100, foto_renkler: ["Beyaz"] }])).run();
  P.analiz = "error";
  for (let i = 0; i < 8; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
  P.analiz = "healthy";
  const u = await k.d1.prepare("SELECT asama, build_gorev FROM foto_uretim WHERE siparis_no = 'PR-TEST-MUT'").first();
  // 8 Eki: kirmizi analiz -> saglayici onarimi (zincir 3 halka) -> 'onarim-bekliyor' (elle DEGIL).
  sonuc.J = !!u && u.asama === "onarim-bekliyor" && String(u.build_gorev || "").split("~").length === 3;
  // T: sunulmayan tur — panel acilis reddi + kuyruktaki satir saglayiciya gitmeden 'elle'.
  const pf = await fm.panelFotoAcik(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tur: "anahtarlik", acik: true }) }), e2, Date.now());
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-TEST-T', 0, ?, 'anahtarlik', 100, 'build-baslat', ?, '2000-01-01T00:00:00.000Z')")
    .bind(is, new Date().toISOString()).run();
  await fm.fotoUretimTuru(e2, Date.now(), null);
  const t = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-TEST-T'").first();
  sonuc.T = pf.status === 400 && !!t && t.sebep === "tur-kapali";
  k.kapat();
  return sonuc;
}

/** URETIM NOTU ("Nasil olsun?"): temiz SQLite; her senaryo ayri ziyaretci. Donus: {U,E,T,G,Y,C,B} gecti mi. */
async function notSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (not) => {
    const govde = onizlemeGovde(not === undefined ? {} : { not });
    const r = await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop/foto/onizleme", { method: "POST",
      headers: { "CF-Connecting-IP": "10.9.0." + (++ipNo), "Content-Type": "application/json" }, body: JSON.stringify(govde) }),
      e2, new URL("https://pruvo3d.com/api/shop/foto/onizleme"), "/foto/onizleme", null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const satir = async (is) => (await k.d1.prepare("SELECT uretim_notu FROM foto_isler WHERE is_no = ?").bind(is || "").first());
  const sonuc = {};
  const once = protoSayisi();
  const u = await cag("a".repeat(301));
  sonuc.U = u.kod === 400 && !!u.v && u.v.hata === "not-uzun";
  const e = await cag("şapkalı olsun, bana ada.deniz@ornek.com adresinden yazın");
  sonuc.E = e.kod === 400 && !!e.v && e.v.hata === "not-kisisel-veri";
  const t = await cag("çizgi film tarzı; numaram 0 545 138 65 26");
  sonuc.T = t.kod === 400 && !!t.v && t.v.hata === "not-kisisel-veri";
  sonuc.G = protoSayisi() === once;
  const y = await cag("a".repeat(300));
  const ys = y.v && y.v.is ? await satir(y.v.is) : null;
  sonuc.Y = y.kod === 200 && !!ys && ys.uretim_notu === "a".repeat(300);
  const c = await cag("sadece\u0007 baş​\n\tolsun");
  const cs = c.v && c.v.is ? await satir(c.v.is) : null;
  sonuc.C = c.kod === 200 && !!cs && cs.uretim_notu === "sadece baş olsun";
  const b = await cag(undefined);
  const bs = b.v && b.v.is ? await satir(b.v.is) : null;
  sonuc.B = b.kod === 200 && !!bs && bs.uretim_notu === "";
  k.kapat();
  return sonuc;
}
{
  const s = await notSenaryolar(foto);
  ol("UN1 not 301 karakter -> 400 not-uzun", s.U, JSON.stringify(s));
  ol("UN2 notta e-posta -> 400 not-kisisel-veri", s.E, JSON.stringify(s));
  ol("UN3 notta telefon -> 400 not-kisisel-veri", s.T, JSON.stringify(s));
  ol("UN3b reddedilen notlu isteklerin hicbiri saglayiciya GITMEDI", s.G, JSON.stringify(s));
  ol("UN4 not tam 300 karakter -> 200 + foto_isler.uretim_notu yazildi", s.Y, JSON.stringify(s));
  ol("UN5 kontrol/gorunmez karakter temizlenir, bosluk sadelesir", s.C, JSON.stringify(s));
  ol("UN6 notsuz istek -> 200, uretim_notu bos", s.B, JSON.stringify(s));
}
const NOT_MUTANTLAR = [
  ["NM1 KISISEL VERI DENETIMI SILINDI", "if (NOT_EPOSTA.test(d) || NOT_TELEFON.test(d)) {", "if (false) {", ["E", "G", "T"]],
  ["NM2 UZUNLUK SINIRI SILINDI", "if (Array.from(d).length > URETIM_NOTU_EN_COK) {", "if (false) {", ["G", "U"]],
  ["NM3 KONTROL KARAKTERI TEMIZLENMEDI", "const d = x.replace(NOT_KONTROL, \" \").replace(NOT_BOSLUK, \" \").trim();",
   "const d = x;", ["C"]],
  ["NM4 NOT YAZILMADI", "if (uretimNotu) {\n", "if (false) {\n", ["C", "Y"]],
  ["NM-K KONTROL", "// 10+ rakam (araya bosluk/tire/nokta/parantez girebilir) = telefon kalibi.",
   "// 10+ rakam  (araya bosluk/tire/nokta/parantez girebilir) = telefon kalibi.", []],
];
for (const [ad, capa, yerine, olmeli] of NOT_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await notSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 7 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

const MUTANTLAR = [
  ["M1 SINIR", "if (sayi.kisi >= VERI.sinir_ziyaretci_24s) {", "if (false) {", "D"],
  ["M2 BOT", "if (!(await botDogrula(request, env, g.turnstile_token))) {", "if (false) {", "E"],
  ["M3 ANALIZ", "if (onarimGerekli(p)) {", "if (false) {", "J"],
  // Tur uyeligi MANIFESTTEN (motor M + ortam eslemesi); kapi silinince manifestte olmayan tur acilir.
  ["M4 ANAHTARLIK GERI ACILDI (manifest kapisi silindi)", "VERI.kolu(kod) === \"saglayici\" &&\n    Object.prototype.hasOwnProperty.call(TUR_ORTAM, kod);",
   "kod !== \"\";", "T"],
  ["M5 AYAK DUSTU", "      foto_ayak: AYAK_PLAKET_BASI,\n", "", "A"],
  ["K0 KONTROL", "console.log(\"FOTO_URETIM kuyruga=\"", "console.log(\"FOTO_URETIM  kuyruga=\"", null],
];
for (const [ad, capa, yerine, olmeli] of MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await darSenaryolar(fm);
  if (olmeli) {
    ol(ad + " -> " + olmeli + " KIRMIZI yanar (digerleri yesil)",
       s[olmeli] === false && Object.keys(s).filter((x) => x !== olmeli).every((x) => s[x] === true), JSON.stringify(s));
  } else {
    ol(ad + " -> hicbir senaryo kirmizi yanmaz", Object.values(s).length === 5 && Object.values(s).every((x) => x === true), JSON.stringify(s));
  }
}

/** Mutanta karsi iki dar onarim senaryosu (temiz SQLite). YESIL: kirmizi->onarim->yesil->hazir.
 *  KIRMIZI: onarim sonrasi da kirmizi -> elle + renk KOSMADI + analiz iki kez (yeniden analiz atlanmadi). */
async function onarimSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const r2x = r2Kur();
  const e2 = envKur(k.d1, r2x);
  const is = "d".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-8888', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  P.protoDurum.set("gorev-proto-8888", 5);
  const sonuc = {};
  const kos = async (no, a, ao) => {
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100, foto_renkler: ["Beyaz"] }])).run();
    P.analiz = a; P.analizOnarim = ao;
    const an = P.cagri.filter((c) => c === "POST /v1/print/analyze").length;
    const rn = P.cagri.filter((c) => c === "POST /v1/print/multi-color").length;
    for (let i = 0; i < 10; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
    P.analiz = "healthy"; P.analizOnarim = null;
    const u = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    return { no, u, analiz: P.cagri.filter((c) => c === "POST /v1/print/analyze").length - an,
             renk: P.cagri.filter((c) => c === "POST /v1/print/multi-color").length - rn };
  };
  // 8 Eki 2026 (yerel onarim koprusu): onarim sonrasi da kirmizi -> renk KOSAR (eskiden elle), iki yol da
  // 'onarim-bekliyor'da biter; saglayici 3MF'i ASLA model.3mf olmaz (TESLIM).
  const y = await kos("PR-TEST-ONR-Y", "error", "healthy");
  sonuc.YESIL = !!y.u && y.u.asama !== "elle" && y.renk === 1 && y.analiz === 2;
  const r = await kos("PR-TEST-ONR-K", "error", "error");
  sonuc.KIRMIZI = !!r.u && r.u.asama !== "elle" && r.renk === 1 && r.analiz === 2;
  const teslim = [y, r].filter((x) => x.u && x.u.asama !== "elle");
  sonuc.TESLIM = teslim.length >= 1 && teslim.every((x) => x.u.asama === "onarim-bekliyor" &&
    !r2x.m.has("foto/" + x.no + "/0/model.3mf") && r2x.m.has("foto/" + x.no + "/0/model.ham.3mf"));
  k.kapat();
  return sonuc;
}

const ONARIM_MUTANTLAR = [
  ["N1 ONARIM SONRASI YENIDEN ANALIZ ATLANDI", "return analizBaslat(env, u, dokuGlb, simdi, telegram);",
   "return renkBaslat(env, u, \"\", simdi, telegram);", ["YESIL", "KIRMIZI"]],
  ["N2 ONARIM SONRASI KIRMIZIDA ELLE (eski davranis, kopru devre disi)",
   "if (zincir(u).length >= 2) {\n        return renkBaslat(env, u, ozet, simdi, telegram);",
   "if (zincir(u).length >= 2) {\n        return elleDusur(env, u, \"analiz-kirmizi\", ozet, simdi, telegram);", ["KIRMIZI"]],
  ["N3 ONARIM YERINE DOGRUDAN RENK", "if (zincir(u).length >= 2) {", "if (true) { return renkBaslat(env, u, ozet, simdi, telegram); } if (false) {", ["YESIL", "KIRMIZI"]],
  ["NK1 HAM SAGLAYICI 3MF'I model.3mf'E YAZILDI", "uretimAnahtari(u.siparis_no, u.kalem, ONARIM_HAM_BICIM)",
   "uretimAnahtari(u.siparis_no, u.kalem, \"3mf\")", ["TESLIM"]],
  ["NK2 RENK SONRASI 'hazir' YAZILDI (onarim kapisi atlandi)", "asamaYaz(env, u, \"onarim-bekliyor\", { analiz: ozet }, simdi)",
   "asamaYaz(env, u, \"hazir\", { analiz: ozet }, simdi)", ["TESLIM"]],
  ["N0 KONTROL", "console.log(\"FOTO_URETIM kuyruga=\"", "console.log(\"FOTO_URETIM  kuyruga=\"", []],
];
for (const [ad, capa, yerine, olmeli] of ONARIM_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await onarimSenaryolar(fm);
  const kirmizi = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 3 && JSON.stringify(kirmizi) === JSON.stringify([...olmeli].sort()), JSON.stringify(s));
}

/** ONARIM NOBETI (8 Eki, BaBa sarti 4): 'onarim-bekliyor' > ONARIM_BAYAT_SAAT -> Worker cron'u Okan'a TEK bildirim.
 *  TAZE: 1 sa'lik satir bildirim uretmez · BAYAT: 7 sa'lik satir tek bildirim · TEKRAR: hemen sonraki tur yeni
 *  bildirim atmaz. */
async function bayatSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  const msj = [];
  const tg = async (_e, m) => { msj.push(m); };
  const say = () => msj.filter((m) => m.includes("onarım kapısı")).length;
  const ekle = (no, saat) => {
    const t = new Date(Date.now() - saat * 3600000).toISOString();
    return k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)" +
      " VALUES (?, 0, ?, 'plaket', 100, 'onarim-bekliyor', 0, ?, ?)").bind(no, "a".repeat(32), t, t).run();
  };
  const sonuc = {};
  await ekle("PR-TEST-NB-T", 1);
  await fm.fotoUretimTuru(e2, Date.now(), tg);
  sonuc.TAZE = say() === 0;
  await ekle("PR-TEST-NB-B", 7);
  await fm.fotoUretimTuru(e2, Date.now(), tg);
  sonuc.BAYAT = say() === 1 && /1 kalem/.test(msj.find((m) => m.includes("onarım kapısı")) || "");
  await fm.fotoUretimTuru(e2, Date.now(), tg);
  sonuc.TEKRAR = say() === 1;
  k.kapat();
  return sonuc;
}

const BAYAT_MUTANTLAR = [
  ["NB1 YAS KOSULU SILINDI (taze satir da alarm)", "WHERE asama = 'onarim-bekliyor' AND guncel < ?\"",
   "WHERE asama = 'onarim-bekliyor' AND ? IS NOT NULL\"", ["TAZE"]],
  ["NB2 TEKRAR KAPISI SILINDI (her tur alarm)", "if (!son || simdi - son.guncel >= ONARIM_BAYAT_SAAT * 3600000) {",
   "if (true) {", ["TEKRAR"]],
  ["NB3 NOBET CAGRILMADI", "    ozet.onarim_bayat = await onarimBayatNobeti(env, simdi, telegram);\n", "", ["BAYAT", "TEKRAR"]],
  ["NB0 KONTROL", "console.log(\"FOTO_URETIM kuyruga=\"", "console.log(\"FOTO_URETIM  kuyruga=\"", []],
];
for (const [ad, capa, yerine, olmeli] of BAYAT_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await bayatSenaryolar(fm);
  const kirmizi = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 3 && JSON.stringify(kirmizi) === JSON.stringify([...olmeli].sort()), JSON.stringify(s));
}

/** Mutanta karsi bes dar onarim-kapisi senaryosu (temiz SQLite). A1-A5: onarimGerekli(p) karari.
 *  A1 warning+deg_faces 316227 → onarim en az 1 kez (tavan sonrasi 'elle'; sonsuz onarim YOK).
 *  A2 warning + tum metrikler 0/true → renk (repair 0; bugunku davranis).
 *  A3 healthy → renk (repair 0; en temiz yol).
 *  A4 zincir(~) + warning + kusur → 'elle' analiz-kirmizi (tek onarim tavan).
 *  A5 warning + metrik alani YOK → renk (repair 0; figur ozeti 8 Eki).
 *  Her anahtar SENARYONUN GECTIGI (`true`) ya da KIRMIZI YANDIGI (`false`) durumunu tasir. */
async function metrikSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  const is = "d".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-8888', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  P.protoDurum.set("gorev-proto-8888", 5);
  const sonuc = {};
  const kos = async (no, a, ao, am) => {
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100, foto_renkler: ["Beyaz"] }])).run();
    P.analiz = a; P.analizOnarim = ao; P.analizMetrik = am;
    const on = P.cagri.filter((c) => c === "POST /v1/print/repair").length;
    const rn = P.cagri.filter((c) => c === "POST /v1/print/multi-color").length;
    const an = P.cagri.filter((c) => c === "POST /v1/print/analyze").length;
    for (let i = 0; i < 14; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
    P.analiz = "healthy"; P.analizOnarim = null; P.analizMetrik = null;
    const u = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    return { u, onarim: P.cagri.filter((c) => c === "POST /v1/print/repair").length - on,
             renk: P.cagri.filter((c) => c === "POST /v1/print/multi-color").length - rn,
             analiz: P.cagri.filter((c) => c === "POST /v1/print/analyze").length - an };
  };
  // A1: warning + degenerate_faces 316227 → onarim en az 1 kez (8 Eki: tavan sonrasi renk + 'onarim-bekliyor').
  const a1 = await kos("PR-TEST-MA1", "warning", null, { degenerate_faces: 316227 });
  sonuc.A1 = !!a1.u && a1.onarim >= 1;
  // A2: warning + metrik 0/true → renk, repair 0 (bugunku davranis korunur).
  const a2 = await kos("PR-TEST-MA2", "warning", null, null);
  sonuc.A2 = !!a2.u && a2.u.asama === "onarim-bekliyor" && a2.onarim === 0;
  // A3: healthy → renk, repair 0.
  const a3 = await kos("PR-TEST-MA3", "healthy", null, null);
  sonuc.A3 = !!a3.u && a3.u.asama === "onarim-bekliyor" && a3.onarim === 0;
  // A4: zincir(~) + warning + kusur (holes) → tek onarim (tavan), sonra renk + 'onarim-bekliyor' (8 Eki).
  const a4 = await kos("PR-TEST-MA4", "warning", "warning", { holes: 1 });
  sonuc.A4 = !!a4.u && a4.u.asama === "onarim-bekliyor" && a4.onarim === 1;
  // A5: warning + metrik alani YOK → renk, repair 0 (figur ozeti).
  const a5 = await kos("PR-TEST-MA5", "warning", null, { noMetrics: true });
  sonuc.A5 = !!a5.u && a5.u.asama === "onarim-bekliyor" && a5.onarim === 0;
  k.kapat();
  return sonuc;
}

const METRIK_MUTANTLAR = [
  // A1: degenerate_faces kontrolu silinirse warning+deg_faces 316227 → renk (repair KOSMAZ).
  ["N4 KUSUR KOSULU SILINDI (deg_faces)", "if (typeof m.degenerate_faces === \"number\" && m.degenerate_faces > 0) { return true; }",
   "if (false) { return true; }", "A1"],
  // A4: tavan kontrolu silinirse zincir(~)+kusur → ikinci onarim (sonsuz).
  ["N5 TAVAN KONTROLU SILINDI (zincir.length>=2)",
   "if (zincir(u).length >= 2) {\n        return renkBaslat(env, u, ozet, simdi, telegram);\n      }",
   "if (false) {\n      }", "A4"],
  ["N6 KONTROL", "console.log(\"FOTO_URETIM kuyruga=\"", "console.log(\"FOTO_URETIM  kuyruga=\"", null],
];
for (const [ad, capa, yerine, olmeli] of METRIK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await metrikSenaryolar(fm);
  if (olmeli) {
    ol(ad + " -> " + olmeli + " KIRMIZI yanar (digerleri yesil)",
       s[olmeli] === false && Object.keys(s).filter((x) => x !== olmeli).every((x) => s[x] === true), JSON.stringify(s));
  } else {
    ol(ad + " -> hicbir metrik senaryosu kirmizi yanmaz", Object.values(s).length === 5 && Object.values(s).every((x) => x === true), JSON.stringify(s));
  }
}

/**
 * ORNEK AYRIMLARI — mutanta karsi alti dar senaryo (temiz SQLite). Donus: her ayrim tuttu mu.
 *   SEPET : ornek isi odeme kaleminde RED        DURUM : musteri /foto/durum ornegi gostermez
 *   GORSEL: musteri /foto/gorsel ornegi vermez   SINIR : ornek satirlari gunluk tavani yemez
 *   DOSYA : ORNEK- onekli musteri satiri dosya vermez   URET : musteri isi ornek-uret'te 404
 */
async function ornekSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const r2b = r2Kur();
  const e2 = envKur(k.d1, r2b);
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  const simdi = new Date().toISOString();
  const orn = "d".repeat(32), mus = "b".repeat(32);
  for (const [no, z] of [[orn, fm.ORNEK_ZIYARETCI], [mus, "z"]]) {
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, ?, ?, 'hazir', 'gorev-proto-8888', ?)")
      .bind(no, z, simdi, simdi).run();
  }
  await r2b.put("foto-onizleme/" + orn + ".png", PNG, { httpMetadata: { contentType: "image/png" } });
  const cag = async (yontem, yol, govde, ip) => (await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, {
    method: yontem, headers: { "CF-Connecting-IP": ip || "10.0.9.1", "Content-Type": "application/json" },
    body: govde ? JSON.stringify(govde) : undefined }), e2, new URL("https://pruvo3d.com/api/shop" + yol),
    yol.split("?")[0], null)).status;
  const s = {};
  const fk = await fm.fotoKalemFiyatla(e2, { foto_is: orn, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }, Date.now());
  const fkm = await fm.fotoKalemFiyatla(e2, { foto_is: mus, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }, Date.now());
  s.SEPET = !fk.satir && fk.hata && fk.hata.hata === "foto-onizleme-yok" && !!fkm.satir;
  s.DURUM = (await cag("GET", "/foto/durum?is=" + orn)) === 404 && (await cag("GET", "/foto/durum?is=" + mus)) === 200;
  s.GORSEL = (await cag("GET", "/foto/gorsel?is=" + orn)) === 404;
  for (let i = 0; i < GUNLUK_TAVAN; i++) {
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, 'plaket', 100, ?, ?, 'basarisiz')")
      .bind("e" + String(i).padStart(31, "0"), fm.ORNEK_ZIYARETCI, simdi).run();
  }
  s.SINIR = (await cag("POST", "/foto/onizleme", onizlemeGovde(), "10.0.9.2")) === 200;
  for (const [no, is] of [["ORNEK-mutant000001", mus], ["ORNEK-mutant000002", orn]]) {
    await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES (?, 0, ?, 'plaket', 100, 'hazir', ?, ?)")
      .bind(no, is, simdi, simdi).run();
    await r2b.put("foto/" + no + "/0/model.3mf", UCMF, {});
  }
  const dosya = async (no) => (await fm.panelFotoDosya(e2, new URL("https://pruvo3d.com/x?siparis_no=" + no + "&kalem=0&bicim=3mf"))).status;
  s.DOSYA = (await dosya("ORNEK-mutant000001")) === 404 && (await dosya("ORNEK-mutant000002")) === 200;
  const uret = async (is) => (await fm.panelOrnekUret(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is }) }), e2, Date.now(), null)).status;
  s.URET = (await uret(mus)) === 404 && (await uret(orn)) === 200;
  k.kapat();
  return s;
}
const GUNLUK_TAVAN = foto.GUNLUK_ONIZLEME_TAVANI;
const ORNEK_MUTANTLAR = [
  ["OM1 SEPET RED DALI SILINDI", "  if (ornekMi(is)) { return { hata: { hata: \"foto-onizleme-yok\" }, kod: 400 }; }\n", "", "SEPET"],
  ["OM2 DURUM RED DALI SILINDI",
   "  if (ornekMi(is)) { return fjson({ hata: \"bulunamadi\" }, 404); }\n  if (uretecOnizlemeTuru(is.tur)) { return uretecDurumYaniti",
   "  if (uretecOnizlemeTuru(is.tur)) { return uretecDurumYaniti", "DURUM"],
  ["OM3 GORSEL RED DALI SILINDI",
   "  if (ornekMi(is)) { return fjson({ hata: \"bulunamadi\" }, 404); }\n  // Uretec onizlemesi",
   "  // Uretec onizlemesi", "GORSEL"],
  ["OM4 TAVAN ORNEGI SAYAR", "WHERE tarih >= ? AND ziyaretci != ?\"", "WHERE tarih >= ? AND ? IS NOT NULL\"", "SINIR"],
  ["OM5 DOSYA ORNEK ISARETI DUSTU", "WHERE u.siparis_no = ? AND u.kalem = ? AND i.ziyaretci = ?\"",
   "WHERE u.siparis_no = ? AND u.kalem = ? AND ? IS NOT NULL\"", "DOSYA"],
  ["OM6 URET MUSTERI ISINI ALIR", "  return ornekMi(is) ? is : null;\n", "  return is;\n", "URET"],
  ["OK0 KONTROL", "// Ornek isleri (panel, Okan) musterinin gunluk tavanini YEMEZ.",
   "// Ornek isleri  (panel, Okan) musterinin gunluk tavanini YEMEZ.", null],
];
for (const [ad, capa, yerine, olmeli] of ORNEK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await ornekSenaryolar(fm);
  if (olmeli) {
    ol(ad + " -> " + olmeli + " KIRMIZI yanar (digerleri yesil)",
       s[olmeli] === false && Object.keys(s).filter((x) => x !== olmeli).every((x) => s[x] === true), JSON.stringify(s));
  } else {
    ol(ad + " -> hicbir ornek senaryosu kirmizi yanmaz", Object.values(s).length === 6 && Object.values(s).every((x) => x === true), JSON.stringify(s));
  }
}

const OLCEK_MUTANTLAR = [
  ["OM-A OLCU KAPISI ATLANDI", "const olc = await ucmfOlcekle(ucmf.tampon, u.olcu_mm);",
   "const olc = { tampon: ucmf.tampon, olcek: 1, L_once: u.olcu_mm, L_sonra: u.olcu_mm, z_mm: 0 };", ["BUYUK", "BOZUK", "IKIOGE", "ONARIMLI"]],
  ["OM-B OLCEK YANLIS YONE (L/olcu)", "const s = hedefMm / o.L;", "const s = o.L / hedefMm;", ["BUYUK", "ONARIMLI"]],
  ["OM-C TUTMAYAN OLCU R2'YE YAZILDI", "if (!olc.tampon) { return elleDusur(env, u, \"olcu-tutmadi\", ozet, simdi, telegram); }",
   "if (!olc.tampon) { olc.tampon = ucmf.tampon; }", ["BOZUK", "IKIOGE"]],
  ["OM-K KONTROL", "// Duze olcek item kokunun etrafinda;", "// Duze  olcek item kokunun etrafinda;", []],
];
for (const [ad, capa, yerine, olmeli] of OLCEK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await olcekSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 5 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

const OZ_MUTANTLAR = [
  ["OZ-M1 OLCU YALNIZ X/Y'YE BAKIYOR", "const L = Math.max(ust[0] - en[0], ust[1] - en[1], ust[2] - en[2]);",
   "const L = Math.max(ust[0] - en[0], ust[1] - en[1]);", ["FIYAT", "OLCEK"]],
  ["OZ-M2 URETEC Z SARTI SILINDI", " ||\n      kz > o.uzun_kenar_mm * (1 + tol) + 1e-9)", ")", ["URETEC"]],
  ["OZ-MK KONTROL", "// (ayak/cerceve dahil tek nesne).", "// (ayak/cerceve  dahil tek nesne).", []],
];
for (const [ad, capa, yerine, olmeli] of OZ_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await ozSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 3 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

const AK_MUTANTLAR = [
  ["AK-M1 SERIT FILTRESI SILINDI (tum Z)", "if (y <= sinir) { if (z < zEn) { zEn = z; } if (z > zUst) { zUst = z; } }",
   "{ if (z < zEn) { zEn = z; } if (z > zUst) { zUst = z; } }", ["AKIS", "DOGRUDAN", "OLCEKLI", "PANEL"]],
  ["AK-M2 YANLIS EKSEN (Y yerine X kenari)", "fn(q[1] * o.birim, q[2] * o.birim);", "fn(q[0] * o.birim, q[2] * o.birim);",
   ["AKIS", "DOGRUDAN", "OLCEKLI", "PANEL"]],
  ["AK-M3 OLCEKTEN ONCEKI DOSYADA OLCULDU", "alt_kenar_mm: await altKenarOlc(cikti, y) };", "alt_kenar_mm: await altKenarOlc(b, o) };", ["AKIS", "OLCEKLI", "PANEL"]],
  ["AK-M4 OZETE YAZILMADI", "o.alt_kenar_mm = olc.alt_kenar_mm == null ? null : olc.alt_kenar_mm;", "", ["AKIS", "PANEL"]],
  ["AK-MK KONTROL", "// Alt kenar OLCEKLENMIS dosyada olculur", "// Alt kenar  OLCEKLENMIS dosyada olculur", []],
];
for (const [ad, capa, yerine, olmeli] of AK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await altKenarSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 4 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ================================================================ RK — EK RENK (Okan 8 Eki 13:3x + 14:2x)

/**
 * Ek renk: "4 renk secimi olmali, ilk renk ucretsiz, her + renk icin +100 TL"; plaket (palet turu) "Musteri 1-4
 * renk secsin". Donus {FIYAT, BES, BOZUK, KAYIT, MAXC, SIFIR} gecti mi; her biri temiz SQLite ile.
 */
async function renkSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  const is = "e".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-7777', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  const fiyatla = (renkler) => fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: 100, adet: 1, ...(renkler === undefined ? {} : { renkler }) }, Date.now());
  const birim = async (renkler) => { const r = await fiyatla(renkler); return r.satir ? r.satir.birim_kurus : null; };
  const red = async (renkler) => { const r = await fiyatla(renkler); return r.kod === 400 && !!r.hata && r.hata.hata === "gecersiz-renk"; };
  const s = {};
  // FIYAT: 1 renk = taban (100 mm -> 1.000 TL) · 2 renk +100 · 4 renk +300 (kurus).
  s.FIYAT = (await birim(["Beyaz"])) === 100000 && (await birim(["Beyaz", "Siyah"])) === 110000 &&
            (await birim(["Beyaz", "Siyah", "Gri", "Mavi"])) === 130000;
  // BES: 5. renk hem kalem cozumunde hem fiyatlamada RED.
  const bes = ["Beyaz", "Siyah", "Gri", "Mavi", "Sarı"];
  const coz = fm.fotoKalemCoz({ foto_is: is, olcu_mm: 100, adet: 1, renkler: bes });
  s.BES = coz.hata === "gecersiz-renk" && (await red(bes));
  // BOZUK: renksiz / bos / paletten olmayan / tekrarli -> 400 gecersiz-renk.
  s.BOZUK = (await red(undefined)) && (await red([])) && (await red(["Mor"])) && (await red(["Beyaz", "Beyaz"]));
  // KAYIT: satir renkleri + ek renk kalemi tasir.
  const r2 = await fiyatla(["Beyaz", "Lacivert", "Kırmızı"]);
  s.KAYIT = !!r2.satir && r2.satir.birim_kurus === 120000 && r2.satir.tutar_kurus === 120000 &&
            JSON.stringify(r2.satir.foto_renkler) === '["Beyaz","Lacivert","Kırmızı"]' &&
            r2.satir.renk === "Beyaz, Lacivert, Kırmızı" && /3 renkli yorumu · ek renk ×2: 200 TL/.test(r2.satir.parametre_detay);
  // MAXC: odenen 3 renkli siparis -> renk adimi max_colors 3.
  const yuru = async (no, kalem) => {
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, new Date().toISOString(), JSON.stringify([kalem])).run();
    const once = P.cagri.filter((c) => /multi-color$/.test(c)).length;
    P.sonRenk = null; P.analiz = "healthy";
    for (let i = 0; i < 8; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
    const u = await k.d1.prepare("SELECT asama, sebep, renk_sayisi FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    return { u, renk: P.cagri.filter((c) => /multi-color$/.test(c)).length - once, son: P.sonRenk };
  };
  const m = await yuru("PR-TEST-RK3", { id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100,
                                       foto_renkler: ["Beyaz", "Lacivert", "Kırmızı"] });
  s.MAXC = !!m.u && m.u.renk_sayisi === 3 && m.renk >= 1 && !!m.son && m.son.max_colors === 3;
  // SIFIR: renk kaydi olmayan (eski bicim) siparis -> renk adimi 4'e DUSMEZ, saglayiciya gitmeden 'elle'.
  const is0 = "f".repeat(31) + "e";
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-7778', ?)")
    .bind(is0, new Date().toISOString(), new Date().toISOString()).run();
  const z = await yuru("PR-TEST-RK0", { id: "ozel-foto-plaket", foto_is: is0, foto_tur: "plaket", olcu_mm: 100 });
  s.SIFIR = !!z.u && z.u.asama === "elle" && z.u.sebep === "renk-sayisi-yok" && z.renk === 0;
  k.kapat();
  return s;
}

console.log("RK) EK RENK — 1-4 renk, ilk renk dahil, her ek renk +100 TL; renk adimi siparisin renk sayisiyla (Okan 8 Eki)");
{
  const s = await renkSenaryolar(foto);
  ol("RK1 plaket 1/2/4 renk -> 1.000 / 1.100 / 1.300 TL (100 mm)", s.FIYAT === true, JSON.stringify(s));
  ol("RK2 5. renk -> kalem cozumu + fiyatlama 400 gecersiz-renk", s.BES === true, JSON.stringify(s));
  ol("RK3 renksiz / bos / paletten olmayan / tekrarli -> 400 gecersiz-renk", s.BOZUK === true, JSON.stringify(s));
  ol("RK4 satir foto_renkler + renk metni + 'ek renk ×2: 200 TL' tasir", s.KAYIT === true, JSON.stringify(s));
  ol("RK5 odenen 3 renkli siparis -> foto_uretim.renk_sayisi 3 + renk adimi max_colors 3", s.MAXC === true, JSON.stringify(s));
  ol("RK6 renk kaydi yok -> 'elle' renk-sayisi-yok, renk adimi cagrisi 0 (4'e DUSMEZ)", s.SIFIR === true, JSON.stringify(s));
}
const RK_MUTANTLAR = [
  ["RK-M1 SUNUCU EK RENGI YOK SAYDI", "const birim = rs ? VERI.fiyatKurus(tur.kod, mm, rs.n) : null;",
   "const birim = rs ? VERI.fiyatKurus(tur.kod, mm) : null;", ["FIYAT", "KAYIT"]],
  ["RK-M2 RENK SAYISI YOKSA 4'E DUSER (fail-open)",
   "if (!(Number.isInteger(n) && n >= 1 && n <= 4)) { return elleDusur(env, u, \"renk-sayisi-yok\", ozet, simdi, telegram); }",
   "if (!(Number.isInteger(n) && n >= 1 && n <= 4)) { u.renk_sayisi = 4; return renkBaslat(env, u, ozet, simdi, telegram); }", ["SIFIR"]],
  ["RK-M3 PALET DENETIMI SILINDI", "!r.every((x) => VERI.PLA_RENKLERI.includes(x))", "false", ["BOZUK"]],
  ["RK-M4 max_colors SABIT 4", "{ model_url: glb, max_colors: n, printer_brand: \"bambu\" }",
   "{ model_url: glb, max_colors: 4, printer_brand: \"bambu\" }", ["MAXC"]],
  ["RK-MK KONTROL", "// Renk sayisi kalemden (palet)", "// Renk sayisi  kalemden (palet)", []],
];
for (const [ad, capa, yerine, olmeli] of RK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await renkSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 6 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ================================================================ RKK — RENK TAVANI + KOSULLU BOLGE + PALET ESLEMESI

/**
 * BaBa 8 Eki 15:3x-15:5x: tavan = uretecin boyanabilir renk_* sayisi (plaket/figur 4, bust 2); "ucret alinan her ek
 * renk uretime BAGLI" — renk_kosul'u saglanmayan bolgenin (logo tabani "Yok", ses basligi bos) rengi sayilmaz ve
 * satira/uretim secimine GIRMEZ; bust palet renkleri uretec girdisinde bolgelere sirayla gider (taban, rolyef).
 * Donus {TAVAN, LOGO, SES, BUST} gecti mi; temiz SQLite + R2 ile.
 */
async function renkKosulSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const r2k = r2Kur();
  const e2 = envKur(k.d1, r2k);
  const yedek = VERI.ornekler.splice(0);
  const s = {};
  try {
    for (const t of ["plaket", "figur", "bust", "logo", "ses"]) {
      VERI.ornekler.push({ tur: t, kanit: "render", olcu_mm: 100, onizleme: "https://media.pruvo3d.com/rk-o.webp",
                           render: "https://media.pruvo3d.com/rk-r.webp", not: "t" });
      await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, 'x')").bind(t).run();
    }
    let no = 0;
    const isKur = async (tur, parametreler) => {
      const is = (++no).toString(16).padStart(32, "a");
      const asama = fm.uretecOnizlemeTuru(tur) ? "onizleme-hazir" : "hazir";
      await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, ?, 100, 'z', ?, ?, 'gorev-rkk', ?)")
        .bind(is, tur, new Date().toISOString(), asama, new Date().toISOString()).run();
      if (parametreler) {
        await r2k.put(fm.uretecOnizlemeAnahtari(is, "girdi.json"),
          new TextEncoder().encode(JSON.stringify({ sozlesme: 1, kategori: tur, parametreler })), {});
      }
      // Dinamik min turu (ses): onizleme olcu.json min_mm'si (koşucu yazar) — 100 mm siparise engel olmayan sinir.
      if (VERI.turBul(tur).olcu_min_dinamik === true) {
        await r2k.put(fm.uretecOnizlemeAnahtari(is, "olcu.json"), new TextEncoder().encode(JSON.stringify({ min_mm: 10 })), {});
      }
      return is;
    };
    const malzeme = (tur) => {
      const m = {}, mb = VERI.turBul(tur).malzemeler || {};
      for (const b of Object.keys(mb)) { m[b + "_malzeme"] = mb[b][0]; }
      return m;
    };
    const fiyatla = async (is, ek) => fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: 100, adet: 1, ...ek }, Date.now());
    const red = (r) => r.kod === 400 && !!r.hata && r.hata.hata === "gecersiz-renk";
    // TAVAN: plaket 5 / figur 5 / bust 3 renk -> 400 · tavan icinde (4 / 4 / 2) fiyatlanir.
    const P5 = ["Beyaz", "Siyah", "Gri", "Mavi", "Sarı"];
    const isP = await isKur("plaket"), isF = await isKur("figur"), isB = await isKur("bust", {});
    s.TAVAN = red(await fiyatla(isP, { renkler: P5 })) && red(await fiyatla(isF, { renkler: P5 })) &&
              red(await fiyatla(isB, { renkler: P5.slice(0, 3), secim: malzeme("bust") })) &&
              (await fiyatla(isP, { renkler: P5.slice(0, 4) })).satir?.birim_kurus === 130000 &&
              (await fiyatla(isB, { renkler: P5.slice(0, 2), secim: malzeme("bust") })).satir?.birim_kurus === 110000;
    // LOGO: taban "Yok" iken farkli taban rengi +0 ve satir/uretim seciminde YOK; taban "Var" iken +100.
    const lsec = { ...malzeme("logo"), taban_renk: "Beyaz", logo_renk: "Siyah" };
    const lYok = await fiyatla(await isKur("logo", { taban: "Yok" }), { secim: lsec });
    const lVar = await fiyatla(await isKur("logo", { taban: "Var" }), { secim: lsec });
    s.LOGO = !!lYok.satir && lYok.satir.birim_kurus === 100000 && !("taban_renk" in lYok.satir.foto_secim) &&
             !/Taban: .*Beyaz/.test(lYok.satir.renk) && !!lVar.satir && lVar.satir.birim_kurus === 110000 &&
             lVar.satir.foto_secim.taban_renk === "Beyaz";
    // SES: baslik bos -> yazi rengi sayilmaz (2 renk); baslik dolu -> 3 renk. Girdi okunamazsa koşullu bolge PASIF.
    const ssec = { ...malzeme("ses"), plaka_renk: "Beyaz", cubuk_renk: "Siyah", yazi_renk: "Kırmızı" };
    const sBos = await fiyatla(await isKur("ses", { baslik: "" }), { secim: ssec });
    const sDolu = await fiyatla(await isKur("ses", { baslik: "Ada" }), { secim: ssec });
    const sYok = await fiyatla(await isKur("ses", null), { secim: ssec });
    s.SES = !!sBos.satir && sBos.satir.birim_kurus === 110000 && !!sDolu.satir && sDolu.satir.birim_kurus === 120000 &&
            sDolu.satir.foto_secim.yazi_renk === "Kırmızı" && !!sYok.satir && sYok.satir.birim_kurus === 110000;
    // BUST: odenen 2 palet rengi uretec girdisinde taban/rolyef bolgelerine sirayla.
    const g2 = fm.uretecGirdiJson("PR-RKK", { kalem: 0, tur: "bust", olcu_mm: 100, secim: {}, renkler: ["Lacivert", "Kırmızı"] });
    const g1 = fm.uretecGirdiJson("PR-RKK", { kalem: 0, tur: "bust", olcu_mm: 100, secim: {}, renkler: ["Gri"] });
    s.BUST = JSON.stringify(g2.renkler) === '{"taban":"Lacivert","rolyef":"Kırmızı"}' &&
             JSON.stringify(g1.renkler) === '{"taban":"Gri"}';
  } finally {
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  return s;
}

console.log("RKK) RENK TAVANI + KOSULLU BOLGE + PALET ESLEMESI — odenen her renk uretime bagli (BaBa 8 Eki 15:5x)");
{
  const s = await renkKosulSenaryolar(foto);
  ol("RKK1 plaket 5 / figur 5 / bust 3 renk -> 400 gecersiz-renk · tavan icinde plaket 4 = 1.300 TL, bust 2 = 1.100 TL",
     s.TAVAN === true, JSON.stringify(s));
  ol("RKK2 logo taban 'Yok' -> taban rengi +0 TL ve secimde YOK · 'Var' -> +100 TL", s.LOGO === true, JSON.stringify(s));
  ol("RKK3 ses baslik bos -> yazi rengi +0 · dolu -> +100 · girdi okunamazsa koşullu bolge pasif (fail-closed)",
     s.SES === true, JSON.stringify(s));
  ol("RKK4 bust palet renkleri uretec girdisinde taban/rolyef'e sirayla (2 renk -> 2 bolge, 1 renk -> taban)",
     s.BUST === true, JSON.stringify(s));
}
const RKK_MUTANTLAR = [
  ["RKK-M1 PASIF BOLGE RENGI SAYILDI", "VERI.aktifBolgeRenkleri(turKod, (sc && sc.renk) || {}, p)", "((sc && sc.renk) || {})", ["LOGO", "SES"]],
  ["RKK-M2 PARAMETRE OKUNMADI (hep bos)", "const p = kayit.renk_kosul ? await onizlemeParametreleri(env, is.is_no) : {};",
   "const p = {};", ["LOGO", "SES"]],
  ["RKK-M3 BUST PALET ESLEMESI DUSTU", "const renkler = VERI.paletBolgeRenkleri(k.tur, k.renkler), malzemeler = {};",
   "const renkler = {}, malzemeler = {};", ["BUST"]],
  ["RKK-MK KONTROL", "// Koşullu bolge (renk_kosul) varsa", "// Koşullu  bolge (renk_kosul) varsa", []],
];
for (const [ad, capa, yerine, olmeli] of RKK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await renkKosulSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 4 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ================================================================ DMIN — DINAMIK ALT SINIR (BaBa 14:3x)

/**
 * Icerige bagli turde (koordinat) alt sinir onizlemede olculur (olcu.json min_mm, koşucu kopru min-hesapla):
 * altindaki olcu 400 olcu-min (adima yuvarli N) · ustu fiyatlanir · olcum yoksa fail-closed 400 · sabit turde
 * (rolyef, taban 60) 10 mm 400. Donus {ALT, UST, YOK, SABIT}.
 */
async function dinamikMinSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const r2k = r2Kur();
  const e2 = envKur(k.d1, r2k);
  const yedek = VERI.ornekler.splice(0);
  const s = {};
  try {
    for (const t of ["koordinat", "rolyef"]) {
      VERI.ornekler.push({ tur: t, kanit: "render", olcu_mm: 100, onizleme: "https://media.pruvo3d.com/dm-o.webp",
                           render: "https://media.pruvo3d.com/dm-r.webp", not: "t" });
      await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, 'x')").bind(t).run();
    }
    let no = 0;
    const isKur = async (tur, olcuJson) => {
      const is = (++no).toString(16).padStart(32, "d");
      await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, ?, 160, 'z', ?, 'onizleme-hazir', 'gorev-dm', ?)")
        .bind(is, tur, new Date().toISOString(), new Date().toISOString()).run();
      await r2k.put(fm.uretecOnizlemeAnahtari(is, "girdi.json"),
        new TextEncoder().encode(JSON.stringify({ sozlesme: 1, kategori: tur, parametreler: {} })), {});
      if (olcuJson) { await r2k.put(fm.uretecOnizlemeAnahtari(is, "olcu.json"), new TextEncoder().encode(JSON.stringify(olcuJson)), {}); }
      return is;
    };
    const secim = (tur) => {
      const t = VERI.turBul(tur), sc = {};
      for (const b of Object.keys(t.malzemeler || {})) { sc[b + "_malzeme"] = t.malzemeler[b][0]; }
      for (const b of (t.renk_bolgeleri || [])) { sc[b.kod + "_renk"] = b.renkler[0]; }
      return sc;
    };
    const fiyatla = async (is, tur, mm) => fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: mm, adet: 1, secim: secim(tur) }, Date.now());
    const isK = await isKur("koordinat", { min_mm: 152.4 });
    const alt = await fiyatla(isK, "koordinat", 150);
    s.ALT = alt.kod === 400 && alt.hata.hata === "olcu-min" && alt.hata.min_mm === 160 && /en az 160 mm/.test(alt.hata.mesaj);
    const ust = await fiyatla(isK, "koordinat", 160);
    s.UST = !!ust.satir && ust.satir.birim_kurus === VERI.fiyatKurus("koordinat", 160, ust.satir.foto_renkler.length) &&
            ust.satir.birim_kurus >= 160000;
    const yok = await fiyatla(await isKur("koordinat", null), "koordinat", 160);
    s.YOK = yok.kod === 400 && yok.hata.hata === "foto-onizleme-yok";
    const sab = await fiyatla(await isKur("rolyef", {}), "rolyef", 10);
    s.SABIT = sab.kod === 400 && sab.hata.hata === "gecersiz-olcu" && VERI.olcuAraligi("rolyef").en_az === 60;
  } finally {
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  return s;
}

console.log("DMIN) DINAMIK ALT SINIR — icerige bagli turde onizlemenin olctugu min'in alti 400; sabit turde taban (BaBa 14:3x)");
{
  const s = await dinamikMinSenaryolar(foto);
  ol("DMIN1 koordinat min 152,4 mm -> 150 mm siparis 400 olcu-min 'en az 160 mm' (adima yuvarli)", s.ALT === true, JSON.stringify(s));
  ol("DMIN2 koordinat 160 mm -> fiyatlanir (160 mm x 10 TL + ek renk)", s.UST === true, JSON.stringify(s));
  ol("DMIN3 onizlemede min olcumu yok -> 400 foto-onizleme-yok (fail-closed)", s.YOK === true, JSON.stringify(s));
  ol("DMIN4 sabit tur rolyef (taban 60) 10 mm -> 400 gecersiz-olcu", s.SABIT === true, JSON.stringify(s));
  // Musteri metni: koşucu reddi `uretec-red:olcu-min-<N>` -> "bu icerik icin en az N mm".
  ol("DMIN5 uretec-red:olcu-min-160 -> 'Bu içerik için en az 160 mm gerekiyor' metni",
     /^Bu içerik için en az 160 mm gerekiyor;/.test(VERI.uretecRedMetni("uretec-red:olcu-min-160")), VERI.uretecRedMetni("uretec-red:olcu-min-160"));
}
const DMIN_MUTANTLAR = [
  ["DMIN-M1 ALT SINIR KONTROLU SILINDI", "    if (mm < enAz) {", "    if (false) {", ["ALT"]],
  ["DMIN-M2 OLCUM YOKKEN GECIYOR (fail-open)", "    if (enAz === null) { return { hata: { hata: \"foto-onizleme-yok\", mesaj: \"Yeni önizleme gerekiyor.\" }, kod: 400 }; }",
   "    if (enAz === null) { }", ["YOK"]],
  ["DMIN-MK KONTROL", "// DINAMIK MIN (BaBa 14:3x): icerige", "// DINAMIK  MIN (BaBa 14:3x): icerige", []],
];
for (const [ad, capa, yerine, olmeli] of DMIN_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await dinamikMinSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 4 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ================================================================ AO — AYDINLATMA ONAYI (tek kutu, taslak-2)

console.log("AO) AYDINLATMA ONAYI — tek kutu + guncel surum; kutusuz/eski surum 400; damga+surum kayitta (7 Eki 20:5x)");
const ESKI_SURUM = "2026-10-05-taslak-1";
/** shop/src kopyasi (src ile AYNI derinlik: "../../" ve "../config.json" importlari aynen cozulur). */
let aoKopyaNo = 0;
async function aoKopya(degisiklik) {
  const dizin = path.join(SHOP, "foto-test-tmp-" + process.pid + "-ao" + (++aoKopyaNo));
  process.on("exit", () => { fs.rmSync(dizin, { recursive: true, force: true }); });
  fs.mkdirSync(dizin, { recursive: true });
  for (const ad of fs.readdirSync(path.join(SHOP, "src"))) {
    if (!/\.m?js$/.test(ad)) { continue; }
    let k = fs.readFileSync(path.join(SHOP, "src", ad), "utf8");
    for (const [dosya, capa, yerine] of degisiklik || []) {
      if (dosya !== ad) { continue; }
      if (k.split(capa).length - 1 !== 1) { return null; }
      k = k.replace(capa, yerine);
    }
    fs.writeFileSync(path.join(dizin, ad), k);
  }
  return { modul: (await import(url.pathToFileURL(path.join(dizin, "index.js")).href)).default,
           foto: await import(url.pathToFileURL(path.join(dizin, "foto.js")).href) };
}
/** Temiz SQLite. Donus: her iddia gecti mi. K/S/D onizleme ucu, BK/BS/BD /baslat foto kalemi, U uretim satiri. */
async function aoSenaryolar(m) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (yol, govde) => {
    const r = await m.modul.fetch(new Request("https://pruvo3d.com/api/shop" + yol, { method: "POST",
      headers: { "CF-Connecting-IP": "10.20.0." + (++ipNo), "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e2, ctx);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const yeniGovde = (ek) => {
    const g = { tur: "plaket", olcu_mm: 100, gorsel: GORSEL, turnstile_token: "jeton", ...(ek || {}) };
    for (const a of Object.keys(g)) { if (g[a] === undefined) { delete g[a]; } }
    return g;
  };
  const s = {};
  const once = protoSayisi();
  const kutusuz = await cag("/foto/onizleme", yeniGovde({ onay_surum: VERI.onay_surum }));
  const eskiAlan = await cag("/foto/onizleme", yeniGovde({ hak_onay: true, aktarim_onay: true, onay_surum: VERI.onay_surum }));
  const eskiAlanEskiSurum = await cag("/foto/onizleme", yeniGovde({ hak_onay: true, aktarim_onay: true, onay_surum: ESKI_SURUM }));
  s.K = kutusuz.kod === 400 && !!kutusuz.v && kutusuz.v.hata === "onay-yok" &&
        eskiAlan.kod === 400 && !!eskiAlan.v && eskiAlan.v.hata === "onay-yok" && eskiAlanEskiSurum.kod === 400;
  const eski = await cag("/foto/onizleme", yeniGovde({ aydinlatma_onay: true, onay_surum: ESKI_SURUM }));
  const surumsuz = await cag("/foto/onizleme", yeniGovde({ aydinlatma_onay: true }));
  s.S = eski.kod === 400 && !!eski.v && eski.v.hata === "onay-surumu-eski" && surumsuz.kod === 400;
  s.G = protoSayisi() === once;   // reddedilen istek saglayiciya GITMEZ
  const t0 = Date.now();
  const dogru = await cag("/foto/onizleme", yeniGovde({ aydinlatma_onay: true, onay_surum: VERI.onay_surum }));
  const satir = dogru.v && dogru.v.is
    ? await k.d1.prepare("SELECT onay_tarih, onay_surum FROM foto_isler WHERE is_no = ?").bind(dogru.v.is).first() : null;
  const dt = satir ? Date.parse(satir.onay_tarih) : NaN;
  s.D = dogru.kod === 200 && !!satir && satir.onay_surum === VERI.onay_surum &&
        /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(satir.onay_tarih) && dt >= t0 - 1000 && dt <= Date.now() + 1000;
  // /baslat: onizleme hazir sayilir (saglayici yoklamasi bu senaryonun konusu degil).
  const is = dogru.v && dogru.v.is;
  if (is) {
    await k.d1.prepare("UPDATE foto_isler SET asama = 'hazir', gorev = 'gorev-ao', hazir_tarih = ? WHERE is_no = ?")
      .bind(new Date().toISOString(), is).run();
  }
  const sip = (ek) => ({ sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: is || "0".repeat(32), olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }], ...(ek || {}) });
  const iyOnce = P.iyzico.length;
  const bk = await cag("/baslat", sip({ onay_surum: VERI.onay_surum }));
  const bkEski = await cag("/baslat", sip({ hak_onay: true, aktarim_onay: true, onay_surum: VERI.onay_surum }));
  s.BK = bk.kod === 400 && !!bk.v && bk.v.hata === "onay-yok" && bkEski.kod === 400 && P.iyzico.length === iyOnce;
  const bs = await cag("/baslat", sip({ aydinlatma_onay: true, onay_surum: ESKI_SURUM }));
  s.BS = bs.kod === 400 && !!bs.v && bs.v.hata === "onay-surumu-eski" && P.iyzico.length === iyOnce;
  const bd = await cag("/baslat", sip({ aydinlatma_onay: true, onay_surum: VERI.onay_surum }));
  s.BD = bd.kod === 200 && !!bd.v && !!bd.v.no && P.iyzico.length === iyOnce + 1;
  // Foto kalemsiz sepet bu kontrolden ETKILENMEZ (katalog yolu ayni) — istekCoz katalog dalina dusmeden once karar verir.
  // U: odenen siparisin uretim satiri onayi is satirindan TASIR (damga + surum birebir).
  if (bd.v && bd.v.no) {
    await k.d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(bd.v.no).run();
    await m.foto.fotoUretimTuru(e2, Date.now(), null);
  }
  const u = bd.v && bd.v.no
    ? await k.d1.prepare("SELECT onay_tarih, onay_surum FROM foto_uretim WHERE siparis_no = ?").bind(bd.v.no).first() : null;
  s.U = !!u && !!satir && u.onay_surum === VERI.onay_surum && u.onay_tarih === satir.onay_tarih && u.onay_tarih !== "";
  k.kapat();
  return s;
}
{
  const s = await aoSenaryolar({ modul, foto });
  ol("AO1 onizleme: kutusuz -> 400 onay-yok · ESKI alanlarla (hak_onay+aktarim_onay) -> 400", s.K, JSON.stringify(s));
  ol("AO2 onizleme: eski onay surumu / surumsuz -> 400 onay-surumu-eski", s.S, JSON.stringify(s));
  ol("AO3 reddedilen onay isteklerinin hicbiri saglayiciya GITMEDI", s.G, JSON.stringify(s));
  ol("AO4 dogru istek -> 200 + foto_isler.onay_tarih (ISO, istek ani) + onay_surum = " + VERI.onay_surum, s.D, JSON.stringify(s));
  ol("AO5 /baslat foto kalemi: kutusuz / eski alanlarla -> 400 onay-yok, iyzico 0", s.BK, JSON.stringify(s));
  ol("AO6 /baslat foto kalemi: eski surum -> 400 onay-surumu-eski, iyzico 0", s.BS, JSON.stringify(s));
  ol("AO7 /baslat foto kalemi: dogru onay -> 200 + iyzico 1", s.BD, JSON.stringify(s));
  ol("AO8 odenen siparisin foto_uretim satiri onay damgasi + surumu is satirindan birebir tasir", s.U, JSON.stringify(s));
}
{
  // Iki onay cumlesi aydinlatma metnine HARF HARF girdi (hak: her kol, aktarim: yalniz saglayici kolu);
  // ayri onay metni (onay.hak / onay.aktarim) YOK; veri dosyasinda her cumle TEK satirda (grep -F birebir bulur).
  const HAK = "Yüklediğim fotoğrafın bana ait olduğunu ya da kullanma hakkım olduğunu beyan ederim.";
  const AKT = "Fotoğrafımın önizleme ve üretim dosyasının hazırlanması için yurt dışındaki hizmet sağlayıcıya aktarılmasına açık rıza veriyorum.";
  const L = VERI.onay.aydinlatma;
  const ham = fs.readFileSync(path.join(KOK, "foto-uretim-veri.js"), "utf8");
  const tek = (c) => ham.split(c).length - 1 === 1;
  ol("AO9 iki onay cumlesi aydinlatma listesinde AYNEN (hak kol '' · aktarim kol 'M'), ayri onay metni 0, kaynakta birebir 1'er kez",
     L.filter((x) => x.metin === HAK && x.kol === "").length === 1 && L.filter((x) => x.metin === AKT && x.kol === "M").length === 1 &&
     JSON.stringify(Object.keys(VERI.onay)) === JSON.stringify(["aydinlatma"]) && tek(HAK) && tek(AKT) &&
     VERI.aydinlatmaMaddeleri("plaket").includes(AKT) && VERI.aydinlatmaMaddeleri("plaket").includes(HAK),
     JSON.stringify(Object.keys(VERI.onay)));
}
const AO_MUTANTLAR = [
  ["AOM1 SUNUCU ONAY KONTROLU SILINDI", [["foto.js", "if (!g || g.aydinlatma_onay !== true) { return \"onay-yok\"; }", ""]],
   // kutusuz istek saglayiciya gider (G) ve iyzico acilir -> sonraki /baslat sayaclari da kayar (BS, BD)
   ["BD", "BK", "BS", "G", "K"]],
  ["AOM2 SURUM KONTROLU SILINDI", [["foto.js", "if (g.onay_surum !== VERI.onay_surum) { return \"onay-surumu-eski\"; }", ""]],
   ["BD", "BS", "G", "S"]],
  ["AOM3 /baslat FOTO KALEMI ONAY KONTROLU SILINDI", [["index.js", "    const oh = aydinlatmaOnayHatasi(govde);\n    if (oh) return { hata: oh };\n", ""]], ["BD", "BK", "BS"]],
  ["AOM4 ONAY KAYDI YAZILMADI", [["foto.js", "return onaySurum ? { tarih: simdiIso(simdi), surum: onaySurum } : { tarih: \"\", surum: \"\" };",
    "return { tarih: \"\", surum: \"\" };"]], ["D", "U"]],
  ["AOM5 URETIM SATIRINA SURUM TASINMADI", [["foto.js", "COALESCE((SELECT onay_surum FROM foto_isler WHERE is_no = ?), '')",
    "COALESCE((SELECT '' FROM foto_isler WHERE is_no = ?), '')"]], ["U"]],
  ["AOM-K KONTROL", [["foto.js", "// Aydinlatma onayi (damga + surum) musteri kolunda her satira", "// aydinlatma onayi (damga + surum) musteri kolunda her satira"]], []],
];
for (const [ad, degisiklik, olmeli] of AO_MUTANTLAR) {
  const m = await aoKopya(degisiklik);
  if (!m) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + JSON.stringify(degisiklik)); continue; }
  const s = await aoSenaryolar(m);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 8 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ---------------------------------------------------------------------------------------------
// SP) NORMAL SEPET FOTO KALEMI (sayfa-3adim K1): foto kalemi sitenin normal sepetinden /baslat'a gelir
// {foto_is, tur, olcu_mm, renkler[], renk_sayisi, onizleme_ref, atif}; ayri foto odeme yolu YOK.
//   F istemci fiyat alanlari (gosterim/fiyat/tutar/birim_kurus = 1 kurus) YOK SAYILIR, tutar sunucu formulunden
//   T kalemin turu onizleme kaydiyla uyusmazsa 400 · R renk_sayisi sunucu sayimiyla uyusmazsa 400
//   K karma sepet (katalog + foto) TEK odeme · Q odeme onayinda foto_uretim kuyrugu (bugunku kuyruk aynen)
// Temiz SQLite; mutantlar aoKopya ile (her mutant TAM OLARAK beklenen iddiayi kirmizi yakar).
async function spSenaryolar(m) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  await k.d1.prepare("INSERT INTO urunler (id, hash, seq, baslik, kategori, fiyat, gorsel, hs, yayinda)" +
    " VALUES ('sp-karma-urun', 'h', 1, 'Karma test urunu', 'Ev', '200 TL', '', 'karma', 1)").run();
  let ipNo = 0;
  const cag = async (yol, govde) => {
    const r = await m.modul.fetch(new Request("https://pruvo3d.com/api/shop" + yol, { method: "POST",
      headers: { "CF-Connecting-IP": "10.30.0." + (++ipNo), "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e2, ctx);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const on = await cag("/foto/onizleme", { tur: "plaket", olcu_mm: 100, gorsel: GORSEL, turnstile_token: "jeton",
    aydinlatma_onay: true, onay_surum: VERI.onay_surum });
  const is = on.v && on.v.is;
  if (is) {
    await k.d1.prepare("UPDATE foto_isler SET asama = 'hazir', gorev = 'gorev-sp', hazir_tarih = ? WHERE is_no = ?")
      .bind(new Date().toISOString(), is).run();
  }
  const kalem = (ek) => ({ foto_is: is || "0".repeat(32), tur: "plaket", olcu_mm: 100, renkler: ["Beyaz", "Siyah"],
    renk_sayisi: 2, onizleme_ref: "/api/shop/foto/gorsel?is=" + is, atif: { utm_source: "test" }, adet: 1, ...(ek || {}) });
  const sip = (sepet) => ({ sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart",
    musteri, turnstile_token: "j", sepet });
  const siparis = async (no) => no
    ? await k.d1.prepare("SELECT tutar_kurus, urunler FROM siparisler WHERE siparis_no = ?").bind(no).first() : null;
  const s = {};
  const iyF = P.iyzico.length;
  const f = await cag("/baslat", sip([kalem({ gosterim_kurus: 1, fiyat_kurus: 1, tutar_kurus: 1, birim_kurus: 1 })]));
  const fs1 = await siparis(f.v && f.v.no);
  const fk = fs1 ? JSON.parse(fs1.urunler)[0] : null;
  s.F = f.kod === 200 && P.iyzico.length === iyF + 1 && !!fs1 && fs1.tutar_kurus === 110000 && fk.birim_kurus === 110000 &&
        (P.iyzico[P.iyzico.length - 1] || {}).price === "1350.00";
  const t = await cag("/baslat", sip([kalem({ tur: "figur" })]));
  s.T = t.kod === 400 && !!t.v && t.v.hata === "foto-tur-uyusmaz";
  const r = await cag("/baslat", sip([kalem({ renk_sayisi: 1 })]));
  s.R = r.kod === 400 && !!r.v && r.v.hata === "renk-sayisi-uyusmaz";
  const iyK = P.iyzico.length;
  const kr = await cag("/baslat", sip([{ id: "sp-karma-urun", malzeme: "PLA", renk: "Siyah", adet: 1 }, kalem()]));
  const ks = await siparis(kr.v && kr.v.no);
  const kal = ks ? JSON.parse(ks.urunler) : [];
  const fotoK = kal.find((x) => x.foto_is === is), katK = kal.find((x) => x.id === "sp-karma-urun");
  s.K = kr.kod === 200 && P.iyzico.length === iyK + 1 && kal.length === 2 && !!fotoK && !!katK && katK.tutar_kurus > 0 &&
        fotoK.tutar_kurus === 110000 && fotoK.adet === 1 && ks.tutar_kurus === fotoK.tutar_kurus + katK.tutar_kurus;
  if (kr.v && kr.v.no) {
    await k.d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(kr.v.no).run();
    await m.foto.fotoUretimTuru(e2, Date.now(), null);
  }
  const q = kr.v && kr.v.no ? await k.d1.prepare("SELECT is_no, tur, olcu_mm, renk_sayisi FROM foto_uretim WHERE siparis_no = ?")
    .bind(kr.v.no).first() : null;
  s.Q = !!q && q.is_no === is && q.tur === "plaket" && q.olcu_mm === 100 && q.renk_sayisi === 2;
  k.kapat();
  return s;
}
console.log("SP) NORMAL SEPET FOTO KALEMI (sayfa-3adim K1)");
{
  const s = await spSenaryolar({ modul, foto });
  ol("SP1 istemci fiyat alanlari (1 kurus) YOK SAYILIR -> tutar 1.100,00 (100 mm + 1 ek renk), iyzico 1350.00", s.F, JSON.stringify(s));
  ol("SP2 kalem turu onizleme kaydiyla uyusmaz -> 400 foto-tur-uyusmaz", s.T, JSON.stringify(s));
  ol("SP3 renk_sayisi sunucu sayimiyla uyusmaz -> 400 renk-sayisi-uyusmaz", s.R, JSON.stringify(s));
  ol("SP4 karma sepet (katalog + foto) TEK odeme, foto adet 1, toplam = kalemler", s.K, JSON.stringify(s));
  ol("SP5 odeme onayinda foto_uretim kuyrugu (is/tur/olcu/renk_sayisi kalemden)", s.Q, JSON.stringify(s));
}
const SP_MUTANTLAR = [
  ["SPM1 ISTEMCI FIYATI OKUNUR", [
    ["foto.js", "  return { kalem: { foto_is: isNo, olcu_mm: olcu, adet,", "  return { kalem: { ...k, foto_is: isNo, olcu_mm: olcu, adet,"],
    ["foto.js", "  const rs = renkSayimi(tur.kod, k, null);\n  const birim = rs ? VERI.fiyatKurus(tur.kod, mm, rs.n) : null;",
                "  const rs = renkSayimi(tur.kod, k, null);\n  const birim = k.gosterim_kurus || (rs ? VERI.fiyatKurus(tur.kod, mm, rs.n) : null);"]], ["F"]],
  ["SPM2 TUR DENETIMI SILINDI", [["foto.js", "  if (k.tur !== undefined && k.tur !== is.tur) {", "  if (false) {"]], ["T"]],
  ["SPM3 RENK SAYISI DENETIMI SILINDI", [["foto.js", "  if (k.renk_sayisi === undefined || k.renk_sayisi === rs.n) { return null; }", "  return null;"]], ["R"]],
  ["SPM-K KONTROL", [["foto.js", "// Sepet kalemi turu tasiyorsa kayittaki turle AYNI olmali", "// sepet kalemi turu tasiyorsa kayittaki turle AYNI olmali"]], []],
];
for (const [ad, degisiklik, olmeli] of SP_MUTANTLAR) {
  const m = await aoKopya(degisiklik);
  if (!m) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + JSON.stringify(degisiklik)); continue; }
  const s = await spSenaryolar(m);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 5 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ================================================================ K2b — UYUM KAPISI + B2 TEK + İPTAL + MUTANTLAR
// (sayfa-3adim K2b — K2 tur 1 eksikleri: parça kapısı + B2 tek + İptal hatası + iç çubuk + 7 mutant).
// ÖLÇÜM: A metni birebir · 5 kelime DUR · 5 tasarım geçer · foto soru çıkar 3/3 + Evet/Hayır/cevapsız ·
//         girdi türünde soru 0 · DUR'da 0 istek · İptal→yeni tür ② dolu · B2 sayısı 1 · iç çubuk 0
console.log("K2b) UYUM KAPISI + B2 TEK + İPTAL + MUTANTLAR");
{
  // (1) A METNİ BİREBİR — foto türünde parça kelimesi → A ekranı, metin A_METIN_BIREBIR.
  const fotoAcik = { acik: true, turler: [{ kod: "plaket", ad: "Kabartma plaket", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  const girdiAcik = { acik: true, turler: [{ kod: "isimlik", ad: "İsimlik", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  // Sentetik foto türü: girdi foto-1.
  // K2b-fin: sentetik-f için sentetik bir ornek de eklendi (K2b-* testleri kart tıklaması yapmıyor
  // ama uyumSonucBul içindeki kart araması artık başarılı — ileride kart-tabanlı testlerde boşluk bırakmaz).
  const sentetikFotoVeri = (VERI_KAYNAK_ORJ) => {
    const V = veriYukle(VERI_KAYNAK_ORJ);
    V.turler.push({ kod: "sentetik-f", ad: "Sentetik Foto", aciklama: "x", girdi: ["foto-1"], uretec: "litofan_uret",
      olcu_mm: { en_az: 80, en_cok: 200 }, renk_bolgeleri: [], malzemeler: {},
      form: {}, fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
      ornek_kanit_izni: ["render"], ornek_notu: "t" });
    V.ornekler.push({ tur: "sentetik-f", kanit: "render", olcu_mm: 100,
      onizleme: "https://media.pruvo3d.com/foto/ornek/sentetik-f-1-render.webp",
      render: "https://media.pruvo3d.com/foto/ornek/sentetik-f-1-render.webp",
      not: "sentetik foto 100 mm" });
    return V;
  };
  // Sentetik girdi türü: girdi "form" (girdi türü, foto DEĞİL).
  // K2b-fin: sentetik-g için sentetik bir ornek de eklendi (M-ADIM2 mutant testi kart tıklamasıyla
  // ② başlığını günceller; orneksiz tür galeride kart oluşturmaz → baslik boş kalırdı).
  const sentetikGirdiVeri = (VERI_KAYNAK_ORJ) => {
    const V = veriYukle(VERI_KAYNAK_ORJ);
    V.turler.push({ kod: "sentetik-g", ad: "Sentetik Girdi", aciklama: "x", girdi: ["form"], uretec: "isimlik_uret",
      olcu_mm: { en_az: 80, en_cok: 200 }, renk_bolgeleri: [], malzemeler: {},
      form: { yazi: { tip: "metin", max: 20 } },
      fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, ek_renk_tl: 100, renk_tavani: 4 },
      ornek_kanit_izni: ["render"], ornek_notu: "t" });
    V.ornekler.push({ tur: "sentetik-g", kanit: "render", olcu_mm: 100,
      onizleme: "https://media.pruvo3d.com/foto/ornek/sentetik-g-1-render.webp",
      render: "https://media.pruvo3d.com/foto/ornek/sentetik-g-1-render.webp",
      not: "sentetik girdi 100 mm" });
    return V;
  };

  // (2) Parça/yedek kelime vakaları (5/5 uygun_degil). Tarif metni anahtar kelime içerir.
  // (3) Tasarım tarifleri (5/5 geçer): "annemin portresi", "köpeğim Pamuk", "logo", "deniz manzarası", "düğün tarihi".
  const kelimeDUR = ["annemin parçası", "telefonumun yedeği", "kırıldı", "mekanizması bozuldu", "orijinal dişlisi"];
  const tasarimGecer = ["annemin portresi", "köpeğim Pamuk", "logo", "deniz manzarası", "düğün tarihi"];
  // Not: "düğün tarihi" → "tarih" içermez ama "kilit"/"kırık"/"kayıp" yok. "Pamuk" → "kayıp" yok. Hepsi geçer.
  // "logo" → "kilips" değil, "kilit" değil, "yuva" değil. Geçer.

  // Test için ortak: foto türünde tur sec → uretimNotu yaz → uyumKontrol çağır.
  // uyumKontrol kod=foto türü kodu; tarif=S.uretimNotu; cevap=S.belirsizCevap.
  // EkranKos yardımcısı: form cizildikten sonra uretimNotu'nu doldur, sonra cizUyum tetikle, sonra uyumSonuc oku.
  const uyumSonucBul = async (kaynak, kod, tarif, cevap) => {
    const V = sentetikFotoVeri(VERI_KAYNAK);
    const acik = { acik: true, turler: V.turler };
    // uretimNotu uygulanmış + tıklanmış tür ile S1'e in.
    const kayit = { is: "a".repeat(32), tur: kod, olcu: 100 };
    const e = await ekranKos(kaynak, V, acik, kayit, undefined, { turnstileOto: true });
    const dd = () => [...e.bolum.agac()];
    const tur = (k) => dd().find((n) => n.classList.contains("foto-uretim-galeri-kucuk") && n.getAttribute("data-tur") === k);
    const kart = tur(kod);
    if (kart) kart.tetikle("click");
    // uretimNotu textarea'sını doldur.
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta && tarif != null) { ta.value = tarif; ta.tetikle("input"); }
    // belirsiz cevabı tıkla (true=Evet, false=Hayır).
    if (cevap === true) {
      const evet = dd().find((n) => n.id === "foto-uyum-evet");
      if (evet) evet.tetikle("click");
    } else if (cevap === false) {
      const hayir = dd().find((n) => n.id === "foto-uyum-hayir");
      if (hayir) hayir.tetikle("click");
    }
    // uyumSonuc metni: "Tasarım mı, parça mı?" (belirsiz) veya A metni (uygun_degil) veya hiçbiri (uygun).
    const soruBaslik = dd().find((n) => n.classList && n.classList.contains("foto-uretim-uyum-baslik") && n.textContent === "Tasarım mı, parça mı?");
    const aMetin = dd().find((n) => n.classList && n.classList.contains("foto-uretim-uyum-metin"));
    return { soruVar: !!soruBaslik, aMetin: aMetin ? aMetin.textContent : null, ekran: e };
  };
  // Sentetik girdi türü için: aynı test ama sentetik-g girdi tipi "form".
  const uyumSonucGirdi = async (kaynak, tarif) => {
    const V = sentetikGirdiVeri(VERI_KAYNAK);
    const acik = { acik: true, turler: V.turler };
    const kayit = { is: "b".repeat(32), tur: "sentetik-g", olcu: 100 };
    const e = await ekranKos(kaynak, V, acik, kayit, undefined, { turnstileOto: true });
    const dd = () => [...e.bolum.agac()];
    const kart = dd().find((n) => n.classList.contains("foto-uretim-galeri-kucuk") && n.getAttribute("data-tur") === "sentetik-g");
    if (kart) kart.tetikle("click");
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta && tarif != null) { ta.value = tarif; ta.tetikle("input"); }
    const soruBaslik = dd().find((n) => n.classList && n.classList.contains("foto-uretim-uyum-baslik") && n.textContent === "Tasarım mı, parça mı?");
    return { soruVar: !!soruBaslik };
  };

  // 1) Parça/yedek kelime DUR (5/5).
  let dur5 = 0;
  for (const t of kelimeDUR) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", t, undefined);
    if (r.aMetin && r.aMetin.indexOf("Fotoğraftan parça ya da yedek parça üretmiyoruz") === 0 && !r.soruVar) dur5++;
  }
  ol("K2b-1 parça kelime vakası 5/5 uygun_degil (A metni)", dur5 === 5, "basarili=" + dur5);

  // 2) Tasarım tarifleri GEÇER (5/5): uyum paneli BOŞ (soru yok, A yok) — fotoğraf türü + cevap yok
  //    olduğundan soru ÇIKAR. Burada "geçer" = cevap vermeden yola devam edilebilir anlamında, soru kabul.
  //    Test: cevap=Hayır işaretlerse uyum OK olur (form görünür, A yok, soru da kapanır).
  let gecer5 = 0;
  for (const t of tasarimGecer) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", t, false);  // Hayır
    if (!r.aMetin && !r.soruVar) gecer5++;
  }
  ol("K2b-2 tasarım tarifi 5/5 geçer (Hayır → uyum OK)", gecer5 === 5, "basarili=" + gecer5);

  // 3) Foto türünde soru çıkar 3/3 (cevapsız): cevap yoksa "Tasarım mı, parça mı?" başlığı görünür.
  //    K2b-fin: SPEC ile sayaç eşleşsin diye TAM 3 vaka (önce 5 vakaydı; sayım 5/5 olunca 3/3 beklentisi
  //    ile çelişiyordu). Seçilen 3 vaka: "annemin portresi" (insan/kategori), "logo" (marka), "deniz manzarası" (mekan).
  const soruVakalari = ["annemin portresi", "logo", "deniz manzarası"];
  let soruCikar = 0;
  for (const t of soruVakalari) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", t, undefined);
    if (r.soruVar && !r.aMetin) soruCikar++;
  }
  ol("K2b-3 foto türünde soru çıkar 3/3 (cevapsız)", soruCikar === 3, "basarili=" + soruCikar);

  // 4) Evet → DUR (1/1): "annemin portresi" + Evet → A metni (parça kabul etti).
  const evetDUR = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", "annemin portresi", true);
  ol("K2b-4 Evet→DUR 1/1 (parça onayı → A metni)",
     evetDUR.aMetin && evetDUR.aMetin.indexOf("Fotoğraftan parça") === 0 && !evetDUR.soruVar,
     JSON.stringify({ aMetin: evetDUR.aMetin, soruVar: evetDUR.soruVar }));

  // 5) Hayır → geçer (1/1): yukarıda zaten gecer5 test edildi; burada ayrıca 1/1 kanıt.
  const hayirG = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", "logo", false);
  ol("K2b-5 Hayır→geçer 1/1 (soru kapanır, A yok)", !hayirG.aMetin && !hayirG.soruVar, JSON.stringify(hayirG));

  // 6) Cevapsız → DUR (1/1): "Önizleme oluştur" butonu PASIF (cünkü uyum OK değil).
  //    Bu test foto türünde, uretimNotu "logo", cevap undefined → belirsiz → buton disabled.
  const cevapsiz = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", "logo", undefined);
  const cevapsizBtn = cevapsiz.ekran.bolum.agac() ? [...cevapsiz.ekran.bolum.agac()].find((n) => n.id === "foto-onizle-buton") : null;
  ol("K2b-6 cevapsız→DUR 1/1 (belirsiz → onizle butonu disabled)",
     cevapsiz.soruVar && cevapsizBtn && cevapsizBtn.disabled === true,
     JSON.stringify({ soruVar: cevapsiz.soruVar, btnDisabled: cevapsizBtn && cevapsizBtn.disabled }));

  // 7) DUR vakalarında 2D/önizleme isteği 0: "kırıldı" yaz → "Önizleme oluştur" tıkla → fetch sayacı 0.
  //    (fetch istekleri e.istekler üzerinden ölçülür; S2'ye hiç düşmemeli.)
  const fetchSayac = async (kaynak, uretimMetni, cevap) => {
    const V = sentetikFotoVeri(VERI_KAYNAK);
    const acik = { acik: true, turler: V.turler };
    const kayit = { is: "c".repeat(32), tur: "sentetik-f", olcu: 100 };
    const e = await ekranKos(kaynak, V, acik, kayit, undefined, { turnstileOto: true, zamanlayici: true });
    const dd = () => [...e.bolum.agac()];
    const kart = dd().find((n) => n.classList.contains("foto-uretim-galeri-kucuk") && n.getAttribute("data-tur") === "sentetik-f");
    if (kart) kart.tetikle("click");
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta) { ta.value = uretimMetni; ta.tetikle("input"); }
    if (cevap === true) { const ev = dd().find((n) => n.id === "foto-uyum-evet"); if (ev) ev.tetikle("click"); }
    const btn = dd().find((n) => n.id === "foto-onizle-buton");
    if (btn) btn.tetikle("click");
    // aydinlatma onayı da tikleyelim (kapıdan sonra bu kalmış olabilir).
    const on = dd().find((n) => n.id === "foto-aydinlatma-onay");
    if (on && !on.checked) { on.checked = true; on.tetikle("change"); }
    if (btn && !btn.disabled) btn.tetikle("click");
    return e.istekler.length;
  };
  // Belirsiz (soru cevapsız): buton disabled, tıklama etkisiz, fetch 0.
  const belirsizIstek = await fetchSayac(EKRAN_KAYNAK, "annemin portresi", undefined);
  // Evet (A ekranı): aydinlatma tikleyince bile A ekranı DOM'da, fetch 0.
  const evetIstek = await fetchSayac(EKRAN_KAYNAK, "kırıldı", true);
  ol("K2b-7 DUR vakalarında 2D/önizleme isteği 0 (belirsiz & uygun_degil)",
     belirsizIstek === 0 && evetIstek === 0,
     JSON.stringify({ belirsizIstek, evetIstek }));

  // 8) Girdi türünde soru 0: sentetik-g (girdi "form") + uretimNotu "kırıldı" → kelime DUR (A ekranı);
  //    ama cevap SORUSU çıkmaz (soru sadece foto türünde).
  const girdiK = await uyumSonucGirdi(EKRAN_KAYNAK, "kırıldı");
  const girdiG = await uyumSonucGirdi(EKRAN_KAYNAK, "logo");
  // sentetik-g için cevap=undefined olsa bile soru çıkmamalı.
  ol("K2b-8 girdi türünde soru 0 (kelime var → A; yok → uyum OK; hiçbirinde soru)",
     !girdiK.soruVar && !girdiG.soruVar,
     JSON.stringify({ girdiK: girdiK.soruVar, girdiG: girdiG.soruVar }));

  // 9) A metni birebir: uygun_degil'de metin TAM A_METIN_BIREBIR.
  const aMetinTam = evetDUR.aMetin === "Fotoğraftan parça ya da yedek parça üretmiyoruz. Programımız tasarım ürünleri içindir:";
  ol("K2b-9 A metni birebir (kaynaktaki A_METIN_BIREBIR ile aynı)", aMetinTam, JSON.stringify({ aMetin: evetDUR.aMetin }));

  // 10) B2 checkbox sayısı 1: S1'deki (foto-b2-onay-s1) SİLİNMİŞ; yalnız ③'ten (foto-b2-onay) var.
  //     S1'de sayım: foto-b2-onay-s1 sayısı 0, foto-b2-onay sayısı 0 (henüz S3'e geçmedi).
  const eS1 = await ekranKos(EKRAN_KAYNAK, VERI, fotoAcik);
  const b2S1 = [...eS1.bolum.agac()].filter((n) => n.tagName === "INPUT" && n.type === "checkbox" && /^foto-b2-onay/.test(n.id));
  ol("K2b-10 B2 checkbox sayısı 1 (S1'de 0; ③'ten 'foto-b2-onay' = TEK)",
     b2S1.length === 0, "adet=" + b2S1.length);

  // 11) Eski iç çubuk DOM sayısı 0: .foto-uretim-adim (data-no="2") SİLİNMİŞ.
  const icCubuk = [...eS1.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-adim")).length;
  ol("K2b-11 eski iç çubuk DOM sayısı 0 (cizAdimlar kaldırıldı)", icCubuk === 0, "adet=" + icCubuk);

  // 12) İptal→yeni tür ② dolu 1/1: S3 → İptal → ① → başka tür sec → ② açılır (baslik2 + yukle kutu + alan DOM'da).
  const iptalE = await ekranKos(EKRAN_KAYNAK, VERI, fotoAcik,
    { is: "d".repeat(32), tur: "plaket", olcu: 100 },
    { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
    { turnstileOto: true, zamanlayici: true });
  const iptalBtn = [...iptalE.bolum.agac()].find((n) => n.id === "foto-iptal-btn");
  if (iptalBtn) iptalBtn.tetikle("click");
  // Şimdi ① görünür. Litofan kartı tıkla → S1'e düş → ② açılır.
  // Litofan kart data-tur="litofan" ile ızgarada (VERI'de var).
  await new Promise((c) => setTimeout(c, 0));
  const litKart = [...iptalE.bolum.agac()].find((n) => n.classList.contains("foto-uretim-galeri-kucuk") && n.getAttribute("data-tur") === "litofan");
  if (litKart) litKart.tetikle("click");
  await new Promise((c) => setTimeout(c, 0));
  const iptalDD = [...iptalE.bolum.agac()];
  const baslikVar = !!iptalDD.find((n) => n.classList.contains("foto-uretim-adim2-baslik"));
  const yukleKutuVar = !!iptalDD.find((n) => n.id === "foto-yukle-kutu");
  // alanUyum DOM'da (S.alanUyum.id = "foto-uyum") ya da alan'in kendisi (id="foto-adim2-alan"? — farklı isim olabilir).
  const alanVar = !!iptalDD.find((n) => n.id === "foto-uyum") || !!iptalDD.find((n) => n.classList && n.classList.contains("foto-uretim-alani"));
  ol("K2b-12 İptal→yeni tür ② dolu 1/1 (baslik + yukle kutusu + form alani DOM'da)",
     baslikVar && yukleKutuVar && alanVar,
     JSON.stringify({ baslikVar, yukleKutuVar, alanVar }));

  // ---- 7 MUTANT + 1 KONTROL (her biri tek başına KIRMIZI; kontrol []). ----
  // Ortak: sentetik foto türünde kart tıkla → uretimNotu "logo" → "Önizleme oluştur" tıkla.
  //        Normal: belirsiz → soru çıkar, fetch 0. Mutant: farklı davranış.
  // "KIRMIZI" ölçütü: en az bir davranış değişti. Spesifik:
  //   M-SERIT: şerit etiketi "Tasarım seç" → başka metin ⇒ 3 etiketten biri değişti.
  //   M-ADIM2: adim2EtiketiK2 hep "Foto ekle" ⇒ girdi türünde ② başlığı "Foto ekle" (geçersiz).
  //   M-B2: B2 tik kapısı yok ⇒ S3'teki sipBtn B2 yokken AÇIK.
  //   M-KAPI-B: kelime listesi boşaltılır ⇒ parça kelimesi geçer.
  //   M-KAPI-C: belirsiz → uygun yapılır (soru atlanır) ⇒ belirsiz tıklanır ama uyum OK.
  //   M-KAPI-SIRA: kapı kontrolü 2D isteğinden SONRAYA alınır ⇒ "kırıldı" yazınca POST 1.
  //   M-IPTAL: İptal ② çocuklarını silerse ⇒ İptal sonrası ② içeriği BOŞ.
  //   K0 kontrol: yorum değişikliği ⇒ hiçbiri değişmedi.

  // M-SERIT: serit etiketi "Tasarım seç" → "Baslangic".
  const mSerit = EKRAN_KAYNAK.replace("[\"1\", \"✦\", \"Tasarım seç\"]", "[\"1\", \"✦\", \"Baslangic\"]");
  const mSeritEkran = await ekranKos(mSerit, VERI, fotoAcik);
  const mSeritEtiket = [...mSeritEkran.bolum.agac()].find((n) => n.classList.contains("foto-uretim-serit-ad") && n.textContent === "Baslangic");
  ol("M-SERIT serit etiketi 'Tasarım seç' → başka metin ⇒ şerit KIRMIZI", !!mSeritEtiket, "bulundu=" + !!mSeritEtiket);

  // M-ADIM2: adim2EtiketiK2 hep "Foto ekle" döner. Girdi türünde ② başlığı "Foto ekle" (yanlış).
  //          Bunu test etmek için sentetik-g türünde kart tıkla, başlık oku.
  // K2b-fin: TEK satırlı .split().join() capa (kaynaktaki TEK "Girdini ekle" döndüren satırı hedefler;
  // çok satırlı .replace() güvenilir değildi — bkz. K2b-fin spec). Eğer capa kaynakta yoksa
  // mutant UYGULANMAMIŞ demektir → KIRMIZI "MUTANT_UYGULANMADI" (sessiz geçmesin).
  const mAdim2Capa = 'return "Girdini ekle";';
  const mAdim2Yerine = 'return "Foto ekle";';
  const mAdim2SplitCount = EKRAN_KAYNAK.split(mAdim2Capa).length - 1;
  const mAdim2MutantUygulandi = mAdim2SplitCount === 1;
  const mAdim2Src = mAdim2MutantUygulandi ? EKRAN_KAYNAK.split(mAdim2Capa).join(mAdim2Yerine) : EKRAN_KAYNAK;
  const mAdim2Veri = sentetikGirdiVeri(VERI_KAYNAK);
  const mAdim2Ekran = await ekranKos(mAdim2Src, mAdim2Veri, { acik: true, turler: mAdim2Veri.turler },
    { is: "z".repeat(32), tur: "sentetik-g", olcu: 100 });
  const mAdim2DD = [...mAdim2Ekran.bolum.agac()];
  const mAdim2Kart = mAdim2DD.find((n) => n.classList.contains("foto-uretim-galeri-kucuk") && n.getAttribute("data-tur") === "sentetik-g");
  if (mAdim2Kart) mAdim2Kart.tetikle("click");
  await new Promise((c) => setTimeout(c, 0));
  const mAdim2Baslik = [...mAdim2Ekran.bolum.agac()].find((n) => n.classList.contains("foto-uretim-adim2-baslik"));
  const mAdim2Yazi = mAdim2Baslik ? mAdim2Baslik.textContent : "";
  // K2b-fin: mutant uygulanmadıysa KIRMIZI "MUTANT_UYGULANMADI" yansın (sessiz geçmesin).
  const mAdim2Hata = !mAdim2MutantUygulandi ? "MUTANT_UYGULANMADI capa_sayisi=" + mAdim2SplitCount
    : "baslik=" + mAdim2Yazi;
  ol("M-ADIM2 adim2EtiketiK2 hep 'Foto ekle' ⇒ girdi türünde başlık KIRMIZI (doğru 'Girdini ekle' olmalıydı)",
     mAdim2Yazi === "② Foto ekle", mAdim2Hata);

  // M-B2: cizS3 + guncelleSipButonu formülünden `!S.b2Onay ||` silinir ⇒ B2 yokken sipBtn AÇIK.
  //       K2b-fin: formül TEK yere toplandı (sipBtnKapaliMi). Mutant bu TEK satırı hedefler.
  //       cizS3 S.alan'ı temizlediği için aydinlatma kutusu DOM'da değil — S.aydinlatmaOnay'ı init'te
  //       kayit.onay === F.onay_surum şartıyla true kuruyoruz (sonradan tıklanamaz). Sonra B2'yi tetikleyip
  //       guncelleSipButonu'nun yeniden hesaplamasını sağlıyoruz.
  //       Uygulanmadı assert: capa "function sipBtnKapaliMi(nt) {" kaynakta tam 1 kez geçmeli.
  const mB2Capa = "function sipBtnKapaliMi(nt) {\n    return !S.aydinlatmaOnay || !S.b2Onay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);\n  }";
  const mB2Yerine = "function sipBtnKapaliMi(nt) {\n    return !S.aydinlatmaOnay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);\n  }";
  const mB2SplitCount = EKRAN_KAYNAK.split(mB2Capa).length - 1;
  const mB2MutantUygulandi = mB2SplitCount === 1;
  const mB2Src = mB2MutantUygulandi ? EKRAN_KAYNAK.split(mB2Capa).join(mB2Yerine) : EKRAN_KAYNAK;
  // onay_surum değerini veri'den çek (kayit.onay === F.onay_surum şartı için).
  const _onaySurum = (function () { const k = {}; vm.runInNewContext(VERI_KAYNAK, k, { filename: "v.js" }); return k.PRUVO_FOTO.onay_surum; })();
  const mB2E = await ekranKos(mB2Src, VERI, fotoAcik,
    { is: "e".repeat(32), tur: "plaket", olcu: 100, onay: _onaySurum },
    { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
    { turnstileOto: true, zamanlayici: true });
  // B2'yi tetikle → guncelleSipButonu() yeniden hesaplar (init'te B2=false, aydinlatma=true; mutantlı
  // formül: !true || (nt && ... && S.fiyatKurus==null) = false; kapı AÇIK).
  const mB2Inp = [...mB2E.bolum.agac()].find((n) => n.id === "foto-b2-onay");
  if (mB2Inp) { mB2Inp.checked = false; mB2Inp.tetikle("change"); }
  const mB2Sip = [...mB2E.bolum.agac()].find((n) => n.id === "foto-sip-btn");
  const mB2Hata = !mB2MutantUygulandi ? "MUTANT_UYGULANMADI capa_sayisi=" + mB2SplitCount
    : "disabled=" + (mB2Sip && mB2Sip.disabled);
  ol("M-B2 disabled formülünden '!S.b2Onay ||' silinir ⇒ B2 yokken sipBtn AÇIK (KIRMIZI)",
     mB2Sip && mB2Sip.disabled === false, mB2Hata);

  // M-KAPI-B: kelime listesi boşaltılır ⇒ parça kelimesi geçer (DUR olmaz).
  //          UYUM_KOKLER dizisini boş yap.
  // K2b-fin: kaynaktaki UYUM_KOKLER artık TEK satırda; mutant onun TAMAMINI "var UYUM_KOKLER = [];" ile
  // değiştirir. Çok satırlı replace güvenilir değildi (aradaki satırlarda gizli karakter / escape farkı).
  // K2b-fin2: düz "ayni" kökü çıkarıldı (BaBa listesi: "aynısı", "aynisini", "aynisindan", "aynıları";
  // düz "aynı" = sıradan eşitlik sıfatı, parça eşleştirmesi DEĞİL). Capa bu yüzden "ayni" İÇERMEZ.
  const mKBCapa = 'var UYUM_KOKLER = ["parca", "parcas", "parcasi", "parcay", "parcayi", "parcam", "parcan", "parcalar", "parcalari", "parcalarin", "parcasin", "parcasini", "yedek", "yedegi", "yedekle", "yedekleri", "yedeklerin", "yedekten", "kirik", "kirigi", "kirdi", "kirildi", "kirilmis", "kirilir", "kiriklar", "kiriklari", "kayip", "kaybi", "kaybol", "kayboldu", "kaybolan", "kayipoldu", "kayipolmus", "mekanizma", "mekanizmasi", "mekanizmayi", "mekanizmalar", "mekanizmalari", "mekanizmada", "mekanizmadan", "disli", "dislisi", "disliyi", "disliler", "dislileri", "dislilerin", "dislide", "disliden", "kilit", "kilidi", "kilide", "kilitler", "kilitleri", "kilitlerin", "kilitten", "klips", "klipsi", "klipsler", "klipsleri", "klipslerin", "klipsten", "yuva", "yuvasi", "yuvayi", "yuvalar", "yuvalari", "yuvalarin", "yuvada", "yuvadan", "orijinal", "orijinali", "orijinale", "orijinalden", "orijinalinde", "aynisi", "aynisini", "aynilar", "aynilari", "aynisindan"];';
  const mKBYerine = "var UYUM_KOKLER = [];";
  const mKBSplitCount = EKRAN_KAYNAK.split(mKBCapa).length - 1;
  const mKBMutantUygulandi = mKBSplitCount === 1;
  const mKBsrc = mKBMutantUygulandi ? EKRAN_KAYNAK.split(mKBCapa).join(mKBYerine) : EKRAN_KAYNAK;
  const mKBekran = await uyumSonucBul(mKBsrc, "sentetik-f", "kırıldı", undefined);
  const mKBHata = !mKBMutantUygulandi ? "MUTANT_UYGULANMADI capa_sayisi=" + mKBSplitCount
    : JSON.stringify({ soruVar: mKBekran.soruVar, aMetin: mKBekran.aMetin });
  ol("M-KAPI-B kelime listesi boşaltılır ⇒ parça kelimesi AÇIK soru çıkar (DUR olmaz)",
     mKBekran.soruVar && !mKBekran.aMetin, mKBHata);

  // M-KAPI-C: belirsiz → uygun yapılır (soru atlanır) ⇒ belirsiz tıklanır ama uyum OK (soru kaybolur).
  //          "if (foto) { if (cevap === true) return 'uygun_degil'; if (cevap === false) return 'uygun'; return 'belirsiz'; }"
  //          satırını "return 'uygun';" ile değiştir.
  const mKCsrc = EKRAN_KAYNAK.replace(
    "    if (foto) {\n      if (cevap === true) return \"uygun_degil\";   // Evet\n      if (cevap === false) return \"uygun\";        // Hayır\n      return \"belirsiz\";                          // cevapsız → fail-closed: soru ÇIKAR\n    }",
    "    if (foto) {\n      if (cevap === true) return \"uygun_degil\";\n      return \"uygun\";\n    }"
  );
  // Cevapsız → belirsiz olmalıydı; mutantta uygun. Soru ÇIKMAMALI.
  const mKCekran = await uyumSonucBul(mKCsrc, "sentetik-f", "logo", undefined);
  ol("M-KAPI-C belirsiz → uygun (soru atlanır) ⇒ cevapsızda soru KIRMIZI yok",
     !mKCekran.soruVar && !mKCekran.aMetin,
     JSON.stringify({ soruVar: mKCekran.soruVar, aMetin: mKCekran.aMetin }));

  // M-KAPI-SIRA: kapı kontrolü 2D isteğinden SONRAYA alınır ⇒ "kırıldı" yazınca POST 1.
  //             onizleOlustur'daki uyumKontrol BLOĞUNU sona (POST'tan sonra) taşı.
  // K2b-fin: mutant iki şeyi birden yapar — (1) gate bloğunu kaldırır (POST'a giden yolu açar),
  // (2) hazirla fonksiyonunu kucultGorsel yerine senkron cb'ye çevirir (vm context'te FileReader/
  // Image/canvas YOK; kucultGorsel hata verir, POST gönderilmez — mutant gözlemlenemez).
  // Kontrol vakasında (mutantsız) uyum !== "uygun" → kapı erken return → 0 istek. Mutantlı vakada
  // kapı yok + hazirla senkron → POST 1 istek (S.dosya + kayit.onay + captchaToken1 önkoşulları test'te kurulur).
  const mKSCapa = "    var uyum = uyumKontrol(S.tur, S.uretimNotu, S.belirsizCevap);\n    if (uyum !== \"uygun\") {\n      cizUyum();\n      guncelleS1Buton();\n      return;\n    }";
  const mKSGateYerine = "    // M-KAPI-SIRA mutant: gate kaldırıldı (POST'tan sonra)";
  const mKSHazirlaCapa = "    var hazirla = konsept ? function (cb) { cb(null, \"\"); } : function (cb) { kucultGorsel(S.dosya, cb); };";
  const mKSHazirlaYerine = "    var hazirla = function (cb) { cb(null, \"data:image/jpeg;base64,xxx\"); }; // M-KAPI-SIRA mutant: dosya işleme atlandı";
  const mKSSplitCount = EKRAN_KAYNAK.split(mKSCapa).length - 1;
  const mKSHazirlaSplitCount = EKRAN_KAYNAK.split(mKSHazirlaCapa).length - 1;
  const mKSMutantUygulandi = mKSSplitCount === 1 && mKSHazirlaSplitCount === 1;
  const mKSsrc = mKSMutantUygulandi
    ? EKRAN_KAYNAK.split(mKSCapa).join(mKSGateYerine).split(mKSHazirlaCapa).join(mKSHazirlaYerine)
    : EKRAN_KAYNAK;
  // Önkoşulları kuran helper: sentetik-f + uretimNotu + dosya mock + onay + captcha.
  const mKSHazirla = async (kaynak, uretimMetni, cevap) => {
    const V = sentetikFotoVeri(VERI_KAYNAK);
    const acik = { acik: true, turler: V.turler };
    const _onaySur = (function () { const k = {}; vm.runInNewContext(VERI_KAYNAK, k, { filename: "v.js" }); return k.PRUVO_FOTO.onay_surum; })();
    // K2b-fin2: isKalabi = /^[a-f0-9]{32}$/ — "g" geçersizdi (g hex değil) → ssIsOku() null → S.tur/olcu
    // hiç kurulmadan POST bile denemeden düşüyordu (kontrol=0 doğru, mutant=0 da yanlıştı). 32 hex'e çevrildi.
    const kayit = { is: "1".repeat(32), tur: "sentetik-f", olcu: 100, onay: _onaySur };
    const e = await ekranKos(kaynak, V, acik, kayit, undefined, { turnstileOto: true, zamanlayici: true });
    const dd = () => [...e.bolum.agac()];
    // Dosya mock'la (file input change ile S.dosya dolar).
    const dosyaInp = dd().find((n) => n.id === "foto-dosya");
    if (dosyaInp) { dosyaInp.files = [{ name: "x.jpg", type: "image/jpeg", size: 1024 }]; dosyaInp.tetikle("change"); }
    // uretimNotu yaz → cizUyum çağrılsın.
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta) { ta.value = uretimMetni; ta.tetikle("input"); }
    if (cevap === true) { const ev = dd().find((n) => n.id === "foto-uyum-evet"); if (ev) ev.tetikle("click"); }
    // Butonu zorla aç (guncelleS1Buton uyumOK'a baktığı için kapalı olur; mutant kapı kalkınca POST'a
    // gidebilmesi için tetikleme öncesi enabled yapıyoruz).
    const btn = dd().find((n) => n.id === "foto-onizle-buton");
    if (btn) { btn.disabled = false; btn.tetikle("click"); }
    const dosyaInp2 = dd().find((n) => n.id === "foto-dosya");
    const dosyaInpVal = dosyaInp2 && dosyaInp2.files ? dosyaInp2.files[0] : null;
    console.log("DEBUG mKS: dosyaInp found=", !!dosyaInp2, "files=", dosyaInpVal && dosyaInpVal.name, "istekler=", e.istekler.length, "uyum=" + "?" + " ta=" + (dosyaInp2 && dosyaInp2.value));
    return e.istekler.length;
  };
  // Kontrol vakası (mutantsız): uyum !== "uygun" → kapı erken return → 0 istek.
  const mKSKontrol = await mKSHazirla(EKRAN_KAYNAK, "kırıldı", true);
  // Mutant vakası: kapı kalkmış → dosya + diğer önkoşullar → POST 1.
  const mKSistek = await mKSHazirla(mKSsrc, "kırıldı", true);
  ol("M-KAPI-SIRA kapı kontrolü 2D isteğinden SONRAYA ⇒ parça kabulünde POST KIRMIZI (1 istek)",
     mKSKontrol === 0 && mKSistek === 1, "kontrol=" + mKSKontrol + " mutant=" + mKSistek);

  // M-IPTAL: İptal ② çocuklarını silerse ⇒ İptal sonrası ② içeriği BOŞ (alaniUyum, alanDOM yok).
  //         iptalBtn handler'ına adim2.firstChild.removeChild ekle.
  const mIPTALsrc = EKRAN_KAYNAK.replace(
    "      S.belirsizCevap = null;\n      S.uyumSonuc = null;\n      turSecimiKayitTemizle();\n      // galeri'yi yeniden çiz (seçim sıfırlansın) ve ① görünür kalsın\n      if (S.ornekBlok) ornekCiz(S.ornekBlok, S.acikVeri ? S.acikVeri.turler.map(function (x) { return x.kod; }) : null);\n      adimKoy(\"secim\");",
    "      S.belirsizCevap = null;\n      S.uyumSonuc = null;\n      turSecimiKayitTemizle();\n      var adim2Mut = document.getElementById(\"foto-adim2\");\n      if (adim2Mut) { while (adim2Mut.firstChild) adim2Mut.removeChild(adim2Mut.firstChild); }\n      if (S.ornekBlok) ornekCiz(S.ornekBlok, S.acikVeri ? S.acikVeri.turler.map(function (x) { return x.kod; }) : null);\n      adimKoy(\"secim\");"
  );
  const mIPTALe = await ekranKos(mIPTALsrc, VERI, fotoAcik,
    { is: "f".repeat(32), tur: "plaket", olcu: 100 },
    { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
    { turnstileOto: true, zamanlayici: true });
  const mIPTALbtn = [...mIPTALe.bolum.agac()].find((n) => n.id === "foto-iptal-btn");
  if (mIPTALbtn) mIPTALbtn.tetikle("click");
  const mIPTALkart = [...mIPTALe.bolum.agac()].find((n) => n.classList.contains("foto-uretim-galeri-kucuk") && n.getAttribute("data-tur") === "litofan");
  if (mIPTALkart) mIPTALkart.tetikle("click");
  const mIPTALdd = [...mIPTALe.bolum.agac()];
  const mIPTALbaslik = !!mIPTALdd.find((n) => n.classList.contains("foto-uretim-adim2-baslik"));
  const mIPTALyukle = !!mIPTALdd.find((n) => n.id === "foto-yukle-kutu");
  const mIPTALalan = !!mIPTALdd.find((n) => n.id === "foto-uyum");
  ol("M-IPTAL İptal ② çocuklarını silerse ⇒ İptal→yeni tür ② BOŞ (baslik/yukle/alan yok)",
     !mIPTALbaslik && !mIPTALyukle && !mIPTALalan,
     JSON.stringify({ baslik: mIPTALbaslik, yukle: mIPTALyukle, alan: mIPTALalan }));

  // K2b-fin2: düz "ayni" kökü UYUM_KOKLER'den çıkarıldı. "aynı" sıradan eşitlik sıfatı olarak tarifte
  // geçer (BaBa'nın parça eşleştirmesi listesi "aynısı/aynisini/aynisindan/aynıları" — düz "aynı" değil).
  // foto türünde cevapsız → "belirsiz" + soru çıkar; düz-aynı tarafından DUR üretilmediğini göstermek
  // için tasarım onayı (Hayır) veriliyor (cevap=false → uyumKontrol "uygun"). İyelikli vakada zaten
  // UYUM_DESEN ilk sırada yakaladığı için cevap verilmeden de "uygun_degil" çıkar; yine de Hayır
  // verilerek evet yolundaki (parça onayı) davranışla aynı UI sonucuna düşüyor — net ölçüm için TEK form.
  const ayniDuzGecer = ["annemle aynı gün doğduk", "ayni gun batimi resmine benzer", "aynı boyutta bir tasarım istiyorum"];
  let ayniDuzGecti = 0;
  for (const tarif of ayniDuzGecer) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", tarif, false);
    if (!r.soruVar && !r.aMetin) ayniDuzGecti++;
  }
  const aynisiDUR = ["bunun aynısı", "aynisini istiyorum", "aynisindan alabilir miyim"];
  let aynisiKaldi = 0;
  for (const tarif of aynisiDUR) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, "sentetik-f", tarif, false);
    if (r.aMetin) aynisiKaldi++;
  }
  ol("K2b-fin2 düz 'aynı' → uygun (3/3), 'aynısı/aynisini/aynisindan' → uygun_degil (3/3) KIRMIZI",
     ayniDuzGecti === ayniDuzGecer.length && aynisiKaldi === aynisiDUR.length,
     "duz=" + ayniDuzGecti + "/" + ayniDuzGecer.length + " aynisi=" + aynisiKaldi + "/" + aynisiDUR.length);

  // K0 kontrol: yorum değişikliği ⇒ hiçbiri değişmedi (orijinal EKRAN_KAYNAK ile birebir aynı sonuçlar).
  //             (Spesifik kontrol: cizUyum'da küçük bir yorum değiştirilir.)
  const k0src = EKRAN_KAYNAK.replace(
    "/* ============== UYUM PANELİ ==============",
    "/* K0 kontrol yorumu ============== UYUM PANELİ =============="
  );
  const k0evetDUR = await uyumSonucBul(k0src, "sentetik-f", "annemin portresi", true);
  const k0aMetinTam = k0evetDUR.aMetin === "Fotoğraftan parça ya da yedek parça üretmiyoruz. Programımız tasarım ürünleri içindir:";
  ol("K-K0 kontrol yorum değişikliği ⇒ KIRMIZI kümesi []", k0aMetinTam, "aMetin=" + k0evetDUR.aMetin);
}

kopru.kapat();
await Promise.allSettled(ctx.bekleyen);
console.log(kirmizi ? "\n❌ " + kirmizi + " iddia KIRMIZI" : "\n✅ HEPSI GECTI");
process.exit(kirmizi ? 1 : 0);
