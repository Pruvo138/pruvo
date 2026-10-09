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
// K3d (9 Eki): anahtarlık artık sayılan örneği VAR (TeKiN render'ı eklendi) → VERI'de tut; A/B
// ölçümleri yalnız plaket/yapboz/bust/figur'un geçici silindiği temiz varsayımı kullanır.
VERI.ornekler.push(...VERI_ORNEKLERI.filter((o) => o.tur === "anahtarlik"));
console.log("A) KAPALI-VARSAYILAN (plaket/yapboz/bust/figur ornek 0; anahtarlik ornegi VAR)");
{
  const y = foto.yapilandirma(env);
  // K3d (9 Eki TeKiN): anahtarlık artık sayılan örneği VAR → gercek-ornek eksik DEĞİL; yapilandirma
  // onaylı + ortam tam ise HAZIR. Onay eksigi yalniz onaysizken listelenir.
  ol("A1 anahtarlık ornegi VAR -> yapilandirma HAZIR (onay eksigi yalniz onaysizken listelenir)",
     y.hazir && !y.eksik.includes("gercek-ornek") &&
       y.eksik.includes("onay-metni-onayi") === (VERI.onay_onayli !== true), JSON.stringify(y));
  // A1b: onay kapisi veri dosyasinin bugunku halinden BAGIMSIZ olculur (onaysiz -> eksik).
  const onayOnce = VERI.onay_onayli;
  VERI.onay_onayli = false;
  const yb = foto.yapilandirma(env);
  VERI.onay_onayli = onayOnce;
  ol("A1b onay bayragi kapali -> eksik listesinde onay-metni-onayi VAR, hazir DEGIL",
     !yb.hazir && yb.eksik.includes("onay-metni-onayi"), JSON.stringify(yb));
  const a = await istek(env, "/foto/acik");
  ol("A2 /foto/acik -> acik:false (panel anahtari yok)", a.kod === 200 && a.v && a.v.acik === false, JSON.stringify(a.v));
  const o = await istek(env, "/foto/onizleme", { govde: onizlemeGovde() });
  // K3d (9 Eki TeKiN): yapilandirma HAZIR (anahtarlık ornegi) -> 503 "kapali" yerine 400 "tur-kapali"
  // (plaket panel anahtari yok).
  ol("A3 /foto/onizleme -> 400 tur-kapali (yapilandirma HAZIR, panel anahtari yok), saglayiciya istek YOK",
     o.kod === 400 && o.v.hata === "tur-kapali" && protoSayisi() === 0, o.kod);
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

/**
 * K3d ORNEK SARTI MUTANTI (9 Eki, TeKiN render'i): anahtarligin sayilan ornegi YOKMUS gibi
 * (VERI.ornekSayisi bellekte yamalanir; sunucu ve test AYNI VERI nesnesini okur). fn yamali dunyada
 * kosar, yama finally'de geri alinir. Donus { uygulandi: yama tuttu mu (ornekSayisi("anahtarlik") === 0),
 * sonuc: fn'in donusu }.
 */
async function ornekSartiKapali(fn) {
  const asil = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" ? 0 : asil(kod));
  try {
    return { uygulandi: VERI.ornekSayisi("anahtarlik") === 0, sonuc: await fn() };
  } finally {
    VERI.ornekSayisi = asil;
  }
}

console.log("P) TUR LISTESI — plaket + figur; magnet SUNULMAZ; anahtarlik KAYITLI + sayilan ornegi 1 (9 Eki TeKiN)");
{
  // 6 Eki (kategori kaydi): tek-tur sozlesmesi yerine "metal gerektiren tur 0 + plaket VAR".
  // 8 Eki (saglayici kopru-15): FIGÜR saglayici kolunda IKINCI tur olarak eklendi.
  // K3d (Okan 8 Eki 22:5x + 9 Eki 01:4x): anahtarlik programin 5. turu -> KAYDI VAR. 9 Eki (TeKiN
  // render'i): sayilan ornegi 1 -> /acik'te VAR, panel acilis anahtari acilinca gorunur. Magnet
  // icin 5 Eki kurali AYNEN (kayit 0).
  const p1 = () => VERI.turler.some((t) => t.kod === "plaket") && VERI.turler.some((t) => t.kod === "figur") &&
    VERI.turler.some((t) => t.kod === "anahtarlik") && VERI.ornekSayisi("anahtarlik") === 1 &&
    !VERI.turler.some((t) => t.kod === "magnet");
  ol("P1 veri dosyasinda plaket + figur + anahtarlik kaydi VAR, anahtarligin sayilan ornegi 1, magnet kaydi 0",
     p1(), JSON.stringify({ kodlar: VERI.turler.map((t) => t.kod), anahtarlik_ornek: VERI.ornekSayisi("anahtarlik") }));
  const m = await ornekSartiKapali(async () => p1());
  ol("P1-M ornek sarti kapali (anahtarlik ornegi sayilmaz) -> P1 KIRMIZI", m.uygulandi && m.sonuc === false, JSON.stringify(m));
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
  // 8 Eki: figur artik gecerli bir tur (acilis anahtari ile); magnet kaydi YOK -> panel 400 gecersiz-tur.
  // K3d (9 Eki TeKiN): anahtarlik KAYITLI + sayilan ornegi 1 -> panel anahtari acilinca /acik'te VAR,
  // kapatilinca KAYBOLUR.
  const mg = await istek(env, "/yonet/foto-acik", { govde: { tur: "magnet", acik: true }, basliklar: YONET });
  const anahtarlikAcik = async () => {
    const y = await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik", acik: true }, basliklar: YONET });
    const a = await istek(env, "/foto/acik");
    const acikKodlar = ((a.v && a.v.turler) || []).map((t) => t.kod);
    const k = await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik", acik: false }, basliklar: YONET });
    const a2 = await istek(env, "/foto/acik");
    const kapaliKodlar = ((a2.v && a2.v.turler) || []).map((t) => t.kod);
    return { yaz: y.kod, kapat: k.kod, acikKodlar, kapaliKodlar, acikta: acikKodlar.includes("anahtarlik"), kapali: !kapaliKodlar.includes("anahtarlik") };
  };
  const p5 = await anahtarlikAcik();
  ol("P5 panel acilis: magnet 400 gecersiz-tur; anahtarlik ORNEKLI -> anahtar acilinca /acik'te VAR, kapatilinca YOK (plaket acik kalir)",
     mg.kod === 400 && mg.v && mg.v.hata === "gecersiz-tur" && p5.yaz === 200 && p5.kapat === 200 &&
       p5.acikta && p5.kapali && p5.acikKodlar.includes("plaket") && p5.kapaliKodlar.includes("plaket"),
     JSON.stringify({ magnet: mg.v, p5 }));
  const p5m = await ornekSartiKapali(anahtarlikAcik);
  ol("P5-M ornek sarti kapali -> ORNEKLI anahtarlik /acik'te YOK (P5 KIRMIZI)",
     p5m.uygulandi && p5m.sonuc.acikta === false, JSON.stringify(p5m));
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
  // K3d (9 Eki TeKiN): iddia DALA GORE. Anahtarlik D kolu (uretec onizlemeli) + sayilan ornegi 1 ->
  // turHazir gecer; panel anahtari yoksa 400 `tur-kapali` (acikAnahtari bossa). Orneksiz tur ise
  // 503 `kapali` (P7-M mutant). M kolunda kapali/olmayan tur 400 `tur-kapali` (F5 magnet = olmayan
  // tur; P7b figur = kayitli ama acilis anahtari YOK).
  const r7b = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "figur", olcu_mm: 100 }) });
  ol("P7 D kolu ornekli tur anahtarlik (panel anahtari yok) -> 400 tur-kapali (uretc onizlemeli yol)",
     r6.kod === 400 && r6.v.hata === "tur-kapali", JSON.stringify(r6));
  ol("P7b M kolu kapali tur figur (acilis anahtari yok) -> 400 tur-kapali", r7b.kod === 400 && r7b.v.hata === "tur-kapali", JSON.stringify(r7b));
  const p7m = await ornekSartiKapali(() => istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "anahtarlik", olcu_mm: 100 }) }));
  ol("P7-M ornek sarti kapali -> anahtarlik turHazir tutmaz, 503 kapali (P7 KIRMIZI)",
     p7m.uygulandi && p7m.sonuc.kod === 503 && p7m.sonuc.v.hata === "kapali", JSON.stringify(p7m));
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
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1, fiyat_kurus: 1, renkli: true, renkler: ["Beyaz", "Siyah"] }] } });
  siparisNo = b.v && b.v.no;
  const iy = P.iyzico[P.iyzico.length - 1] || {};
  ol("H2 kart -> 200, iyzico tutari SUNUCU FORMULUNDEN (100 mm x 10 TL = 1.000 × Renkli 1,15 = 1.150,00 + 250,00 kargo); istemci fiyat_kurus OKUNMAZ",
     b.kod === 200 && P.iyzico.length === once + 1 && iy.price === "1400.00", JSON.stringify(b.v) + " price=" + iy.price);
  const s = await d1.prepare("SELECT durum, urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(siparisNo).first();
  const kalem = s && JSON.parse(s.urunler)[0];
  ol("H3 siparis 'bekliyor', kalem foto_is/tur(plaket)/olcu + foto_ayak 1 + foto_renkler [Beyaz,Siyah] tasir", s && s.durum === "bekliyor" &&
     s.tutar_kurus === 115000 && kalem.foto_is === isNo && kalem.foto_tur === "plaket" && kalem.olcu_mm === 100 && kalem.foto_ayak === 1 &&
     JSON.stringify(kalem.foto_renkler) === '["Beyaz","Siyah"]' && kalem.renk === "Beyaz, Siyah" &&
     /2 renkli yorumu · Renkli \(\+%15\)/.test(kalem.parametre_detay) && kalem.malzeme === "PLA" && kalem.foto_renkli === true, JSON.stringify(s));
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
  // K3d: anahtarlik artik uretec onizlemeli D turu -> /baslat YALNIZ koşucunun 'onizleme-hazir' isine baglanir;
  // eski ('hazir') onizleme 400 foto-onizleme-yok (RED, odeme baslamaz).
  ol("Q1 orneksiz anahtarligin eski ('hazir') onizlemesinden /baslat -> 400 foto-onizleme-yok (odeme baslamaz)",
     b.kod === 400 && b.v.hata === "foto-onizleme-yok", JSON.stringify(b.v));
  // Q1b (9 Eki TeKiN): anahtarlik ORNEKLI (ornekSayisi=1). Ornekli + 'onizleme-hazir' + panel acik ->
  // turHazir gecer, acikAnahtari VAR, olcu araliktaysa (30..80) 200/odeme; aralik disinda 400 gecersiz-olcu.
  // Mutant (ornek sarti kapali -> ornekSayisi=0) reddi 400 foto-kapali'ya CEVIRIR.
  const isB = "b".repeat(32);
  await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'anahtarlik', 100, 'z', ?, 'onizleme-hazir', 'gorev-eski-002', ?)")
    .bind(isB, simdiIso, simdiIso).run();
  const q1b = async () => {
    await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik", acik: true }, basliklar: YONET });
    const r = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: isB, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }] } });
    await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik", acik: false }, basliklar: YONET });
    return { kod: r.kod, hata: r.v && r.v.hata };
  };
  const b2 = await q1b();
  ol("Q1b ornekli anahtarligin 'onizleme-hazir' isinden /baslat (anahtar acik, olcu aralik disi) -> 400 gecersiz-olcu",
     b2.kod === 400 && b2.hata === "gecersiz-olcu", JSON.stringify(b2));
  const q1m = await ornekSartiKapali(q1b);
  ol("Q1-M ornek sarti kapali -> orneksiz anahtarlik /baslat reddi foto-kapali OLUR (Q1b KIRMIZI)",
     q1m.uygulandi && q1m.sonuc.hata === "foto-kapali", JSON.stringify(q1m));
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

// Bolum kodunun fetch geri cagrisinda firlayan istisna (yakalanmamis Promise reddi) testi COKERTMEZ, SAYILIR:
// her kayit hangi kaynakla kosuldugunu tasir; temiz kaynakta (EKRAN_KAYNAK) asenkron istisna 0 olmali (dosya sonu).
const ASENKRON_ISTISNA = [];
let SON_EKRAN_TEMIZ = false;
process.on("unhandledRejection", (e) => { ASENKRON_ISTISNA.push({ temiz: SON_EKRAN_TEMIZ, e: String((e && e.stack) || e).slice(0, 300) }); });

async function ekranKos(kaynak, fotoVeri, acikYanit, kayit, durumYanit, ek) {
  const { document, bolum } = sahteBelge();
  ek = ek || {};
  SON_EKRAN_TEMIZ = typeof EKRAN_KAYNAK === "string" && kaynak === EKRAN_KAYNAK;
  // ek.gorselSahte: tarayicinin FileReader/Image/canvas zinciri (kucultGorsel) sahte DOM'da yok; saplama
  // dosyayi 100x100 gorsel sayar ve sabit bir JPEG data URL'i dondurur (istek govdesi olculebilsin).
  const gorselSahte = ek.gorselSahte ? {
    FileReader: class { readAsDataURL() { this.onload({ target: { result: "data:image/png;base64,AAAA" } }); } },
    Image: class { set src(v) { this.width = 100; this.height = 100; this.onload(); } },
  } : {};
  if (ek.gorselSahte) {
    const yarat = document.createElement;
    document.createElement = (e) => {
      const n = yarat(e);
      if (String(e).toLowerCase() === "canvas") { n.getContext = () => ({ drawImage() {} }); n.toDataURL = () => "data:image/jpeg;base64,SAHTE"; }
      return n;
    };
  }
  // 13:5x: kayit.tur gelirse sessionStorage'da TÜR SEÇIMI olarak da yaz (galeri otomatik seçer).
  const ssTur = kayit && kayit.tur ? kayit.tur : null;
  const istekler = [], araliklar = [], yoklamalar = [];
  // ek.ilkDurumBos: TD türetilmiş eksen senaryosu (S.olcu = kayit.olcu gerekir → kayit'te is olmalı).
  // İlk /foto/durum çağrısı "not ok" döner → sayfa S1'de kalır (form çizilir); POST sonrası yoklama
  // gerçek durumu okur.
  let ilkDurumAtlandi = false;
  const kok = {
    document, PRUVO_FOTO: fotoVeri, setTimeout, clearTimeout, console, ...gorselSahte,
    // ek.zamanlayici: yoklama araligi OLCULUR, gercek zamanlayici kurulmaz (test 5 sn beklemez).
    // Yoklama islevi saklanir: DOM vakasi yoklamayi ELLE tetikler (durum yaniti adim adim degisir).
    setInterval: ek.zamanlayici ? (fn, ms) => { araliklar.push(ms); yoklamalar.push(fn); return 0; } : setInterval,
    clearInterval: ek.zamanlayici ? () => {} : clearInterval,
    PRUVO_SECENEK: { kargoKurus: () => 25000, kurusMetni: (k) => (k / 100).toFixed(2) + " TL" },
    // ek.sepet (dizi): sitenin sepet kapısı (index.html window.pruvoSepeteFotoEkle) taklidi — kalemler diziye
    // GERÇEKTEN yazılır; "sepet kalemi 0" iddiası bu diziden ölçülür (etiketten değil).
    ...(Array.isArray(ek.sepet) ? { pruvoSepeteFotoEkle: (satir) => { ek.sepet.push(satir); return true; } } : {}),
    turnstile: { render: (k, o) => { if (ek.turnstileOto && o && typeof o.callback === "function") { o.callback("t-jeton"); } return 1; },
                 remove() {}, reset() {} },
    // Durumlu sessionStorage (K3b2): kayit + tur seçimiyle başlar; setItem/removeItem gerçekten yazar/siler
    // (İptal'in seçim temizliği ölçülebilsin).
    sessionStorage: (() => {
      const m = new Map();
      if (kayit) { m.set("pruvo_foto_is", JSON.stringify(kayit)); }
      if (ssTur) { m.set("pruvo_foto_tur", ssTur); }
      return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: (k) => { m.delete(k); } };
    })(),
    location: { href: "https://pruvo3d.com/" },
    fetch: async (u, init) => {
      if (init && init.method === "POST") {
        istekler.push({ u: String(u), govde: JSON.parse(init.body) });
        // ek.postKod: TUR-B ① — 429/503 gövdeli yanıt (varsayılan 200).
        const kod_ = ek.postKod || 200;
        return { ok: kod_ < 300, status: kod_, json: async () => ek.postYanit || {} };
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
  // ek.kart: ① kartina (data-kart) tik — K3b'de ②/③ formu kart seciminden sonra cizilir. Tikta firlayan
  // istisna SAYILIR (sonuc.istisna), testi cokertmez.
  let istisna = 0, istisnaMetni = "";
  if (ek.kart) {
    const kart = [...bolum.agac()].find((n) => n.classList.contains("foto-uretim-kart") && n.getAttribute("data-kart") === ek.kart);
    if (kart) { try { kart.tetikle("click"); } catch (e) { istisna++; istisnaMetni = String(e && e.message); } }
  }
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
  Object.defineProperty(sonuc, "istisna", { value: istisna, enumerable: false });
  Object.defineProperty(sonuc, "istisnaMetni", { value: istisnaMetni, enumerable: false });
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

console.log("S) EKRAN — ③ olcu surgusu + tek yukleme alani (sahte DOM'da gercek kosum; K3b: kart tiki ile)");
const EKRAN_KAYNAK = fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8");
const acikTek = { acik: true, turler: [{ kod: "plaket", ad: "Kabartma plaket", aciklama: "x", ornek_sayisi: 1,
  olculer: [{ mm: 100, fiyat_kurus: 34900 }, { mm: 150, fiyat_kurus: 49900 }] }] };
let ekranTek;
{
  // K3b (Okan 9 Eki 01:0x/01:4x): tek kutu, 4 pencere. Kart tiki ① → ② ; ölçü sürgüsü ③'te, tek yükleme alanı ②'de.
  // S0 pozitif kontrol: tur radyo 0 + iç çubuk (data-no="2") 0 + kutu başlığında 4 pencere adı (gösterge).
  ekranTek = await ekranKos(EKRAN_KAYNAK, VERI, acikTek, null, null, { kart: "plaket" });
  const gostergeEtiketleri = [...ekranTek.bolum.agac()]
    .filter((n) => n.classList.contains("foto-uretim-gosterge-ad")).map((n) => n.textContent);
  ol("S0 pozitif kontrol: tur radyo 0 + ic adim cubugu 0 + gosterge 4 etiket 'Tür seç'/'Resim yükle'/'Renk, boyut ve malzeme'/'Önizleme ve onay' (K3b: tek kutu 4 pencere)",
     ekranTek.gorunur && ekranTek.tur === 0 && ekranTek.adim2 === "" &&
     JSON.stringify(gostergeEtiketleri) === JSON.stringify(["Tür seç", "Resim yükle", "Renk, boyut ve malzeme", "Önizleme ve onay"]),
     JSON.stringify({ ...ekranTek, gosterge: gostergeEtiketleri }));
  ol("S1 kart tiki sonrasi ③ olcu SURGUSU 1 + '100 mm → 1.000 TL'; kaydirinca '150 mm → 1.500 TL'; fiyat listesi satiri 0",
     ekranTek.surgu === 1 && ekranTek.olcu === 1 && ekranTek.surguFiyat[0] === "100 mm → 1.000 TL" &&
     ekranTek.kaydir === "150 mm → 1.500 TL" && ekranTek.listeSatiri === 0, JSON.stringify(ekranTek));
  ol("S2 tur radyo dugmesi 0 (ayrı seçici yok; tür seçimi ① kartından)", ekranTek.tur === 0, JSON.stringify(ekranTek));
  const icCubuk = [...ekranTek.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-adim")).length;
  ol("S3 ic adim cubugu DOM'DA 0 (K2b: cizAdimlar kaldirildi; adim gostergesi kutu basliginda)",
     ekranTek.adim2 === "" && icCubuk === 0, JSON.stringify({ adim2: ekranTek.adim2, icCubuk }));
  // 5 Eki 2026 olculen hata: olcu secici eklenmiyordu (musteri olcu SECEMIYORDU) — surgu icin ayni kapi.
  const mutOlcu = EKRAN_KAYNAK.split("    kap.appendChild(surgu);\n").length === 2
    ? EKRAN_KAYNAK.replace("    kap.appendChild(surgu);\n", "") : EKRAN_KAYNAK;
  const mo = mutOlcu === EKRAN_KAYNAK ? null : await ekranKos(mutOlcu, VERI, acikTek, null, null, { kart: "plaket" });
  ol("S-M3 mutant (olcu surgusu eklenmez) -> S1 KIRMIZI (surgu 0)", !!mo && mo.olcu === 0 && mo.surgu === 0, JSON.stringify(mo));
  // Fiyat yazisi formulden degil sabit katsayidan (×100 hatasi) -> S1 KIRMIZI.
  const mutFiyat = EKRAN_KAYNAK.replace('var yazi = el("p", "foto-uretim-surgu-fiyat", F.fiyatSatiri(nt.kod, S.olcu));',
    'var yazi = el("p", "foto-uretim-surgu-fiyat", S.olcu + " mm → " + F.tlMetni(S.olcu * 100));');
  const mf = mutFiyat === EKRAN_KAYNAK ? null : await ekranKos(mutFiyat, VERI, acikTek, null, null, { kart: "plaket" });
  ol("S-M5 mutant (surgu fiyati mm x 1 TL) -> S1 KIRMIZI", !!mf && mf.surguFiyat[0] !== "100 mm → 1.000 TL", JSON.stringify(mf && mf.surguFiyat));
  // Onizleme hazir donusu (S3, oturumdan): ④ acik; ③ olcu SURGUSU da cizilmis olmali (geri donulunce secilebilir).
  const kayit = { is: "b".repeat(32), tur: "plaket", olcu: 100 };
  const hazir = { asama: "hazir", tur: "plaket", olcu_mm: 100, gorsel: "/api/shop/foto/gorsel?is=" + "b".repeat(32) };
  const s3 = await ekranKos(EKRAN_KAYNAK, VERI, acikTek, kayit, hazir);
  const p4 = [...s3.bolum.agac()].find((n) => n.id === "foto-pencere-4");
  ol("S4 onizleme sonrasi (S3, oturumdan) ④ gorunur + ③ olcu SURGUSU 1 + '100 mm → 1.000 TL', fiyat listesi satiri 0",
     !!p4 && p4.hidden === false && s3.olcu === 1 && s3.surguFiyat.includes("100 mm → 1.000 TL") && s3.listeSatiri === 0, JSON.stringify(s3));
  const mutS3Capa = "        if (S.tur && seciliTurBul()) cizForm();\n        durumSorgula(kayit.is, true);";
  const mutS3 = EKRAN_KAYNAK.split(mutS3Capa).length === 2 ? EKRAN_KAYNAK.replace(mutS3Capa, "        durumSorgula(kayit.is, true);") : null;
  const m3 = mutS3 ? await ekranKos(mutS3, VERI, acikTek, kayit, hazir) : null;
  ol("S-M4 mutant (oturumdan donuste ②/③ formu cizilmez) -> S4 KIRMIZI (surgu 0)", !!m3 && m3.olcu === 0, JSON.stringify(m3));

  // S5 TEK YUKLEME ALANI (Okan 7 Eki 21:5x): sayfada tek dosya girdisi ② kutusunda; tiklayip secmek
  // (change) ve kutuya birakmak (drop) AYNI sonucu verir: kutuda dosya adi + not alani acilir (S.dosya dolu).
  // Yanlis tur / >15 MB kutuda tek hata satiri, S.dosya bos kalir (not alani gizli).
  const yukle = async (kaynak, yol, f) => {
    const e = await ekranKos(kaynak, VERI, acikTek, null, null, { kart: "plaket" });
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
  ol("S5a sayfada dosya girdisi TAM 1 (② kutusunda), acik, capture YOK; formda 'Fotoğraf (JPEG' etiketi 0; kabul yazisi kutunun altinda",
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
  // K3b2: silinen 'logo' turu yerine kalan D turu yapboz (ayni uretec olcu sozlesmesi).
  // K3d: olcu yapbozun KAYITLI alt sinirindan (manifest) — sabit 60 mm yapboz araliginin disina dustu.
  const L = VERI.olcuAraligi("yapboz").en_az;
  const oj = (z) => ({ sozlesme: 1, kategori: "yapboz", uzun_kenar_mm: L, kutu_mm: { x: L, y: Math.round(L * 2 / 3), z }, renk_sayisi: 1, sizdirmaz: true });
  sonuc.URETEC = fm.uretecOlcuDogrula(oj(2 * L), { tur: "yapboz", olcu_mm: L }) === "uzun-kenar-tolerans" &&
    fm.uretecOlcuDogrula(oj(5), { tur: "yapboz", olcu_mm: L }) === "";
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
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('figur', 1, 'x')").run();
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
    // IZINSIZ (K3b2, litofansiz): figur'un izni yalniz "baski"ya daraltilir; figur'un RENDER kaydi SAYILMAZ ->
    // acilis anahtari figur icin acik olsa da /foto/acik yalniz plaket (izin disi kanit turu ACMAZ).
    const f = asil.find((o) => o && o.kanit === "render" && o.tur === "figur") || {};
    const tf = V.turBul("figur"), izf = tf.ornek_kanit_izni;
    tf.ornek_kanit_izni = ["baski"];
    V.ornekler.splice(0, V.ornekler.length, r, f);
    s.IZINSIZ = f.tur === "figur" && V.ornekSayisi("figur") === 0 && (await acik()) === "plaket";
    tf.ornek_kanit_izni = izf;
    V.ornekler.splice(0, V.ornekler.length, r);
    const t = V.turBul("plaket"), iz = t.ornek_kanit_izni;
    delete t.ornek_kanit_izni;
    s.IZINYOK = V.ornekSayisi("plaket") === 0 && (await acik()) === "";
    t.ornek_kanit_izni = iz;
    V.ornekler.splice(0, V.ornekler.length, { ...r, render: "" });
    s.EKSIK = V.ornekSayisi("plaket") === 0 && (await acik()) === "";
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
  ol("RO0b kanit izni: plaket [baski,render] · litofan kalkti (K3a: 15 tur silindi)",
     JSON.stringify(V.turBul("plaket").ornek_kanit_izni) === '["baski","render"]' &&
       V.turBul("litofan") === null, "");
  const lr = [];
  const s = await renderSenaryolar(V);
  ol("RO1 render kaydi plaketi ACAR: /foto/acik -> plaket, turHazir hazir", s.ACAR, JSON.stringify(s));
  ol("RO2 izin disi kanit ACMAZ: izni yalniz 'baski' olan figur'un render kaydi 0 sayilir · /foto/acik yalniz plaket", s.IZINSIZ, JSON.stringify(s));
  ol("RO3 turde ornek_kanit_izni yoksa render kaydi SAYILMAZ (fail-closed)", s.IZINYOK, JSON.stringify(s));
  ol("RO4 render gorseli bos render kaydi SAYILMAZ", s.EKSIK, JSON.stringify(s));
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
       Object.keys(m).length === 4 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m));
  }
}

// 13:4x (kopru-15) MİMAR BULGUSU: dürüstlük testleri GERÇEK iddia: her render kartında "önizleme/render"
// etiketi VAR ve "gerçek fotoğraf"/"Gerçek örnekler" iddiası 0 · baskı kaydı kartı "basılmış ürün" der ·
// türün ornek_notu (render dürüstlük cümlesi) AYNEN görünür. K3b: ızgara + büyütme penceresi KALKTI (Okan
// 01:0x) → kart ① penceresinde, ornek_notu ② dürüstlük kutusunda (kart seçilince).
console.log("ES) EKRAN — ① kart: render 'önizleme/render', baski 'basılmış ürün', 'gerçek fotoğraf'/'Gerçek örnekler' 0; ② ornek_notu AYNEN");
{
  const sinifli = (kok, c) => [...kok.agac()].filter((n) => n.classList.contains(c));
  const CUMLE_P = "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, tam kopyası değildir.";
  const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] });
  const yol = async (kaynak, V) => {
    const e = await ekranKos(kaynak, V, { acik: true, turler: [tur("plaket", "Kabartma plaket")] });
    const kart = sinifli(e.bolum, "foto-uretim-kart").find((k) => k.getAttribute("data-tur") === "plaket");
    const etiket = kart && (sinifli(kart, "foto-uretim-kart-etiket")[0] || { textContent: null }).textContent;
    const once = e.bolum.textContent;
    if (kart) { kart.tetikle("click"); }
    const d = sinifli(e.bolum, "foto-uretim-durustluk")[0];
    const not = d && d.childNodes[1] ? d.childNodes[1].textContent : null;
    const eski = ["foto-uretim-buyuk-kart", "foto-uretim-isik", "foto-uretim-galeri-kucuk", "foto-uretim-ornek-grup"]
      .some((c) => sinifli(e.bolum.parentNode, c).length > 0);
    return { kart: !!kart, etiket, not, metin: once + " " + e.bolum.textContent, eski };
  };
  const esDene = async (kaynak) => {
    const Va = veriYukle(VERI_KAYNAK);
    Va.ornekler.splice(0, Va.ornekler.length, ...Va.ornekler.filter((o) => o.tur === "plaket"));
    const R = await yol(kaynak, Va);
    const Vb = veriYukle(VERI_KAYNAK);
    Vb.ornekler.splice(0, Vb.ornekler.length, { tur: "plaket", kanit: "baski", olcu_mm: 100, foto: "https://media.pruvo3d.com/b-f.webp",
      onizleme: "https://media.pruvo3d.com/b-o.webp", baski: "https://media.pruvo3d.com/b-b.webp", not: "t" });
    const B = await yol(kaynak, Vb);
    const kirmizi = [];
    if (R.etiket !== "önizleme/render") kirmizi.push("ETIKET_RENDER");
    if (B.etiket !== "basılmış ürün") kirmizi.push("ETIKET_BASKI");
    if (/Gerçek örnek/.test(R.metin + B.metin)) kirmizi.push("BASLIK_GERCEK_ORNEK");
    if (/gerçek fotoğraf/i.test(R.metin)) kirmizi.push("RENDER_GERCEK_FOTOGRAF");
    if (/gerçek fotoğraf/i.test(B.metin) || /Basılmış ürün \(gerçek fotoğraf\)/.test(B.metin)) kirmizi.push("BASKI_GERCEK_FOTOGRAF");
    if (R.not !== CUMLE_P) kirmizi.push("ORNEK_NOTU");
    // Render dürüstlük cümlesi baskı kaydına (basılmış ürünün kendisi) YAZILMAZ.
    if (B.not !== "") kirmizi.push("BASKI_NOTU");
    if (R.eski || B.eski) kirmizi.push("BUYUK_KART");
    return { kirmizi, R, B };
  };
  const s = await esDene(EKRAN_KAYNAK);
  ol("ES1 render kaydi: kartta etiket 'önizleme/render', 'gerçek fotoğraf' 0, 'Gerçek örnekler' 0; ②'de ornek_notu AYNEN; buyuk kart/isik/izgara 0",
     s.kirmizi.length === 0, JSON.stringify(s));
  ol("ES2 baski kaydi: kartta etiket 'basılmış ürün'; 'Basılmış ürün (gerçek fotoğraf)' 0; render cumlesi baskiya yazilmaz",
     s.kirmizi.length === 0, JSON.stringify(s));
  const ES_MUT = [
    ["ES-M1 baski kart etiketi 'gerçek fotoğraf' yapildi", 'it.kanit === "render" ? "önizleme/render" : "basılmış ürün"',
     'it.kanit === "render" ? "önizleme/render" : "gerçek fotoğraf"', ["BASKI_GERCEK_FOTOGRAF", "ETIKET_BASKI"]],
    ["ES-M2 ornek_notu ②'ye yazilmadi", 'S.ornekNotP.textContent = it && it.kanit === "render" ? it.tur.ornek_notu || "" : "";',
     'S.ornekNotP.textContent = "";', ["ORNEK_NOTU"]],
    ["ES-M3 render sarti kalkti (render cumlesi baskiya yazilir)", 'S.ornekNotP.textContent = it && it.kanit === "render" ? it.tur.ornek_notu || "" : "";',
     'S.ornekNotP.textContent = it ? it.tur.ornek_notu || "" : "";', ["BASKI_NOTU"]],
    ["ES-MK KONTROL (yorum)", "  function kartOrnegi(t) {", "  // kontrol\n  function kartOrnegi(t) {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of ES_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await esDene(EKRAN_KAYNAK.replace(capa, yerine));
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
       JSON.stringify(m.kirmizi.slice().sort()) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m.kirmizi));
  }
}

console.log("FM) FORM ALANLARI + ONIZLEMESIZ D TURU (gercek bust kaydi: sayi + bool alanlari; ureteç kuyrugu)");
{
  const SONRA = "Önizleme, üretim dosyasıyla birlikte hazırlanır; birkaç dakika sürebilir.";
  // K3b2: sentetik girdi türü (isimlik, foto'suz) silinen tür evreniydi → GERÇEK bust kaydı (D/R kolu, foto-1,
  // form (Okan 9 Eki 20:2x): rolyef_yuksekligi_mm sayi -> SÜRGÜ + ters bool -> DÜĞME; "Boyut" (uzun_kenar_mm, Ölçü
  // sürgüsü zaten veriyor) ve "İki renk" (Renkli seçilince otomatik) KALKTI. parametreDogrula çağrıları sayılır.
  const sentetik = (kaynakVeri) => {
    const V = veriYukle(kaynakVeri);
    const asil = V.parametreDogrula;
    V.cagri = [];
    V.parametreDogrula = function (kod, p) { const d = asil(kod, p); V.cagri.push({ kod, p: JSON.stringify(p), d }); return d; };
    return V;
  };
  const acikTur = (V, kod) => ({ kod, ad: V.turBul(kod).ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri(kod).map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus(kod, mm) })) });
  const VARSAYILAN = JSON.stringify({ rolyef_yuksekligi_mm: 3, ters: false });
  const KABARTMA_ACIKLAMA = "Yüzün yüzeyden ne kadar dışarı çıkacağı; yüksek değer daha belirgin, daha kırılgan.";
  const TERS_ACIKLAMA = "Açıkken görüntü yüzeye kabartma yerine içe oyulur (kalıp/damga görünümü).";
  const senaryo = async (kaynak, veriKaynak = VERI_KAYNAK) => {
    const s = {};
    const V = sentetik(veriKaynak);
    const acikB = { acik: true, turler: [acikTur(V, "bust")] };
    const e = await ekranKos(kaynak, V, acikB, null, null, { kart: "bust" });
    const d = () => [...e.bolum.agac()];
    const id = (x) => d().find((n) => n.id === x) || null;
    const p3 = id("foto-pencere-3");
    const ry = id("foto-param-rolyef_yuksekligi_mm"), te = id("foto-param-ters");
    // Kabartma: sürgü (aralık/adım/varsayılan form kaydından) · Ters: role="switch" düğmesi, varsayılan KAPALI ·
    // Boyut + İki renk alanı YOK.
    s.ALANLAR = !!(ry && te && p3) && [ry, te].every((n) => [...p3.agac()].includes(n)) &&
      ry.type === "range" && ry.min === "1" && ry.max === "8" && ry.step === "0.5" && ry.value === "3" &&
      te.tagName === "BUTTON" && te.getAttribute("role") === "switch" && te.getAttribute("aria-checked") === "false" &&
      !id("foto-param-uzun_kenar_mm") && !id("foto-param-iki_renk");
    // V1-V4 (③ penceresi içinde sayılır): sayı kutusu 0 · sürgü 2 (Ölçü + Kabartma) · onay kutusu 0 / düğme 1 ·
    // "İki renk" metni 0.
    const p3n = p3 ? [...p3.agac()] : [];
    s.V1_NUMBER_0 = !!p3 && p3n.filter((n) => n.tagName === "INPUT" && n.type === "number").length === 0;
    s.V2_RANGE_2 = !!p3 && JSON.stringify(p3n.filter((n) => n.tagName === "INPUT" && n.type === "range").map((n) => n.id).sort()) ===
      JSON.stringify(["foto-olcu", "foto-param-rolyef_yuksekligi_mm"]);
    s.V3_DUGME = !!p3 && p3n.filter((n) => n.tagName === "INPUT" && n.type === "checkbox").length === 0 &&
      p3n.filter((n) => n.getAttribute("role") === "switch").length === 1;
    s.V4_IKI_RENK_0 = !!p3 && !p3.textContent.includes("İki renk");
    s.ACIKLAMA = [KABARTMA_ACIKLAMA, TERS_ACIKLAMA].every((m) => p3n.some((n) => n.tagName === "P" && n.textContent === m));
    // AYNI FONKSIYON: hata metni VERI.parametreDogrula dönüşünden (aralık dışı 300 → "Değer izinli aralığın dışında.");
    // 120'ye çekilince ok + gövde şemaya uygun + hata gizli. ③'te geçersiz form varken "İleri" PASİF.
    const hataP = () => d().find((n) => n.classList.contains("foto-uretim-ayrinti") && n.textContent === "Değer izinli aralığın dışında.");
    let ara = null, son = null, ileriPasif = false;
    if (ry) {
      // ③'e geç: ② dosya + parça kapısı "Hayır" → İleri.
      const ileri = id("foto-ileri"), dosya = id("foto-dosya");
      if (dosya) { dosya.files = [{ name: "yuz.jpg", type: "image/jpeg", size: 4096 }]; dosya.tetikle("change"); }
      const hy0 = id("foto-uyum-hayir"); if (hy0) { hy0.tetikle("click"); }
      if (ileri) { ileri.tetikle("click"); }
      const ucuncude = (d().find((n) => n.classList.contains("foto-uretim-gosterge-adim") && n.classList.contains("aktif")) || { getAttribute: () => "" }).getAttribute("data-no") === "3";
      ry.value = "9"; ry.tetikle("input"); ara = V.cagri[V.cagri.length - 1];
      const pasif300 = !!ileri && ileri.disabled === true;
      const gorundu = !!hataP() && hataP().hidden === false;
      ry.value = "3"; ry.tetikle("input"); son = V.cagri[V.cagri.length - 1];
      ileriPasif = ucuncude && pasif300 && !!ileri && ileri.disabled === false;
      s.AYNI_FONKSIYON = V.cagri.length > 0 && V.cagri.every((c) => c.kod === "bust") && !!ara && ara.d.hata === "parametre-aralik" &&
        gorundu && !!son && son.d.ok === true && son.p === VARSAYILAN && !hataP();
    } else { s.AYNI_FONKSIYON = false; }
    s.ILERI_FORM = ileriPasif;
    // CANLI DEĞER: sürgünün yanında seçili değer "<n> mm" (ondalık virgülle); kaydırınca güncellenir.
    const ryYazi = () => (ry && ry.parentNode ? ry.parentNode.childNodes[ry.parentNode.childNodes.indexOf(ry) + 1] : null);
    const y3 = ryYazi() ? ryYazi().textContent : "";
    let y4 = "", y35 = "";
    if (ry) { ry.value = "4"; ry.tetikle("input"); y4 = ryYazi().textContent; ry.value = "3.5"; ry.tetikle("input"); y35 = ryYazi().textContent;
      ry.value = "3"; ry.tetikle("input"); }
    s.CANLI_DEGER = y3 === "3 mm" && y4 === "4 mm" && y35 === "3,5 mm";
    // BOOL: tip "bool" -> aç/kapa düğmesi (label for=id, etiket manifestten), varsayılan manifestten (false);
    // tıklanınca aria-checked "true" + gövdede JSON true (dize DEĞİL) ve doğrulama ok.
    const teEtiket = d().find((n) => n.tagName === "LABEL" && n.getAttribute("for") === "foto-param-ters");
    let teSon = null;
    if (te) { te.tetikle("click"); teSon = V.cagri[V.cagri.length - 1]; }
    s.BOOL = !!te && te.getAttribute("aria-checked") === "true" && !!teEtiket && teEtiket.textContent === "Ters (negatif)" &&
      !!teSon && teSon.d.ok === true && JSON.parse(teSon.p).ters === true;
    if (te) { te.tetikle("click"); }
    // ONIZLEMESIZ D (④): örnek render + SONRA metni; tuval yok; önizleme düğmesi kapalı.
    const sonra = d().find((n) => n.tagName === "P" && n.textContent === SONRA);
    const kap = sonra ? sonra.parentNode : null;
    const btn = id("foto-onizle-buton");
    s.ONIZLEMESIZ = !!kap && kap.hidden === false && [...kap.agac()].some((n) => n.tagName === "IMG" && /bust-1-render\.webp$/.test(n.src)) &&
      !d().some((n) => n.tagName === "CANVAS") && !!btn && btn.disabled === true;
    // TEK ONAY KUTUSU (taslak-2, 7 Eki 20:5x): ④'te GORUNUR; eski iki kutu 0.
    const tekKutu = (dd) => {
      const k_ = dd.find((n) => n.id === "foto-aydinlatma-onay");
      const det = dd.find((n) => n.tagName === "DETAILS" && n.classList.contains("foto-uretim-aydinlatma"));
      const sira = det && k_ ? dd.indexOf(k_) > dd.indexOf(det) : false;   // kutu metnin ALTINDA
      return !!k_ && k_.type === "checkbox" && !!k_.parentNode && k_.parentNode.hidden !== true && sira &&
        k_.parentNode.textContent.trim() === "Aydınlatma metnini okudum, onaylıyorum." &&
        !dd.some((n) => n.id === "foto-hak" || n.id === "foto-aktarim");
    };
    s.TEK_KUTU_FORM = tekKutu(d());
    // URETEC ONIZLEME: foto + parça kapısı "Hayır" + doğrulama → düğme kutu işaretlenince ACILIR; tıklanınca
    // /foto/onizleme'ye gövde (tur + gorsel + parametreler + secim) gider, yoklama aralığı 5 sn.
    const V2 = sentetik(veriKaynak);
    const e2 = await ekranKos(kaynak, V2, { acik: true, turler: [acikTur(V2, "bust")] }, null, { asama: "bekliyor" },
      { kart: "bust", turnstileOto: true, zamanlayici: true, gorselSahte: true, postYanit: { is: "a".repeat(32), kalan: 2 } });
    const d2 = () => [...e2.bolum.agac()];
    const id2 = (x) => d2().find((n) => n.id === x) || null;
    const dos = id2("foto-dosya");
    if (dos) { dos.files = [{ name: "yuz.jpg", type: "image/jpeg", size: 4096 }]; dos.tetikle("change"); }
    // Madde 1 (Okan 8 Eki 14:1x): tarif ZORUNLU — fikstür temiz tarifi doldurur (iddia/mutant hedefi değişmez).
    const ta2 = id2("foto-not");
    if (ta2) { ta2.value = "deniz manzarası"; ta2.tetikle("input"); }
    const hy = id2("foto-uyum-hayir");
    if (hy) { hy.tetikle("click"); }
    const btn2 = id2("foto-onizle-buton");
    const kapali = !!btn2 && btn2.disabled === true;
    const on2 = id2("foto-aydinlatma-onay");
    if (on2) { on2.checked = true; on2.tetikle("change"); }
    s.KUTU_SART = kapali && !!btn2 && btn2.disabled === false;
    const acildi = !!btn2 && btn2.disabled === false && btn2.textContent === "Önizleme oluştur";
    if (btn2) { btn2.tetikle("click"); }
    for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
    const p0 = e2.istekler[0] || { govde: {} };
    s.KUYRUK = acildi && e2.istekler.length === 1 && p0.u === "/api/shop/foto/onizleme" &&
      p0.govde.tur === "bust" && p0.govde.aydinlatma_onay === true && p0.govde.onay_surum === V2.onay_surum &&
      !("hak_onay" in p0.govde) && !("aktarim_onay" in p0.govde) && p0.govde.turnstile_token === "t-jeton" &&
      p0.govde.gorsel === "data:image/jpeg;base64,SAHTE" &&
      JSON.stringify(p0.govde.parametreler) === VARSAYILAN &&
      JSON.stringify(p0.govde.secim) === JSON.stringify({ govde_malzeme: "PLA" }) &&
      e2.araliklar.includes(5000) && !e2.araliklar.includes(3000);
    // PLAKET: form {} -> alan yok, SONRA metni yok.
    const p = await ekranKos(kaynak, sentetik(VERI_KAYNAK), { acik: true, turler: [acikTur(V, "plaket")] }, null, null, { kart: "plaket" });
    const dp = [...p.bolum.agac()];
    s.PLAKET = !dp.some((n) => String(n.id || "").startsWith("foto-param-")) && !dp.some((n) => n.textContent === SONRA && n.tagName === "P");
    s.TEK_KUTU_PLAKET = tekKutu(dp);
    Object.defineProperty(s, "iz", { value: { govde: p0.govde, istek: e2.istekler.length, araliklar: e2.araliklar, istisna: e.istisnaMetni }, enumerable: false });
    return s;
  };
  const s0 = await senaryo(EKRAN_KAYNAK);
  ol("FM1 form alanlari manifestten (③): kabartma surgu(1–8, adim 0,5, varsayilan 3) · ters dugme (kapali) · Boyut/İki renk 0",
    s0.ALANLAR, JSON.stringify(s0));
  ol("V1 bust ③ input[type=number] 0", s0.V1_NUMBER_0, JSON.stringify(s0));
  ol("V2 bust ③ input[type=range] 2 (Ölçü + Kabartma)", s0.V2_RANGE_2, JSON.stringify(s0));
  ol("V3 bust ③ checkbox 0 / role=switch 1", s0.V3_DUGME, JSON.stringify(s0));
  ol("V4 bust ③ 'İki renk' metni 0", s0.V4_IKI_RENK_0, JSON.stringify(s0));
  ol("FM1c kabartma canli deger '3 mm' (varsayilan) -> kaydirinca '4 mm' / '3,5 mm'", s0.CANLI_DEGER, JSON.stringify(s0));
  ol("FM1d kabartma + ters aciklamalari birebir alan altinda", s0.ACIKLAMA, JSON.stringify(s0));
  ol("FM2 istemci dogrulamasi = VERI.parametreDogrula (aralik disi hata metni ondan; 120'de ok + govde semaya uygun)", s0.AYNI_FONKSIYON, JSON.stringify(s0));
  ol("FM2b ③'te gecersiz form varken 'İleri' PASIF, gecerli olunca acik", s0.ILERI_FORM, JSON.stringify(s0));
  ol("FM3 onizlemesiz D turu (④): ornek render + '" + SONRA + "' · tuval 0 · buton kapali", s0.ONIZLEMESIZ, JSON.stringify(s0));
  ol("FM1b bool alan: aç/kapa dugmesi (etiketli, varsayilan kapali) · tiklaninca govdede ters:true (boolean) + dogrulama ok", s0.BOOL, JSON.stringify(s0));
  ol("FM4 plaket (form {}): parametre alani 0, onizleme-sonra metni 0", s0.PLAKET, JSON.stringify(s0));
  ol("FM5 onizlemesiz D: buton onay+dogrulamayla ACILIR -> /foto/onizleme kuyrugu (gorsel + parametre + secim), yoklama 5 sn",
     s0.KUYRUK, JSON.stringify([s0, s0.iz]));
  ol("FM6 TEK onay kutusu 'foto-aydinlatma-onay' aydinlatma metninin ALTINDA, D turunde ve plakette GORUNUR; eski 2 kutu 0",
    s0.TEK_KUTU_FORM && s0.TEK_KUTU_PLAKET, JSON.stringify(s0));
  ol("FM7 kutu isaretsizken 'Önizleme oluştur' DISABLED, isaretlenince acilir; govdede aydinlatma_onay + surum (eski alan 0)",
    s0.KUTU_SART && s0.KUYRUK, JSON.stringify(s0));
  const FM_MUT = [
    ["FM-M1 istemci kendi dogrulamasi (her sey gecerli)", "return F.parametreDogrula(S.tur, parametreGovde());", "return { ok: true };", ["AYNI_FONKSIYON", "BOOL", "ILERI_FORM"]],
    ["FM-M2 onizleme-sonra metni dustu", "S.alanOnizlemeSonra.appendChild(el(\"p\", \"foto-uretim-ayrinti\", ONIZLEME_SONRA));", "", ["ONIZLEMESIZ"]],
    ["FM-M4 uretec onizleme yonlendirmesi silindi (saglayici yoluna duser)",
     "    if (!!(F && F.kolu && F.kolu(S.tur) === \"deterministik\")) { uretecOnizle(); return; }\n", "", ["KUYRUK"]],
    ["FM-M5 uretec yoklama araligi plaketinki", "var aralik = uretec ? URETEC_YOKLAMA_MS : YOKLAMA_MS;", "var aralik = YOKLAMA_MS;", ["KUYRUK"]],
    ["FM-M6 buton kutusuz acilir (S1 kapisi silindi)",
     // TUR-B ①: S1 kosullari s1Sebep sirasinda (kapi ile cumle TEK kaynak) -> onay kosulu oradan silinir.
     "      [!S.aydinlatmaOnay, S1_SEBEP.onay],",
     "      [false, S1_SEBEP.onay],", ["KUTU_SART"]],
    ["FM-M7 aydinlatma metni dustu (kutu metinsiz kalir)", "    S.alanOnay.appendChild(det);\n\n", "", ["TEK_KUTU_FORM", "TEK_KUTU_PLAKET"]],
    ["FM-M8 govdeye onay alani girmedi", "aydinlatma_onay: !!S.aydinlatmaOnay, onay_surum: F.onay_surum,", "onay_surum: F.onay_surum,", ["KUYRUK"]],
    ["FM-M9 bool degeri dize olarak yazilir", "S.parametre[a] = S.parametre[a] !== true;", "S.parametre[a] = String(S.parametre[a] !== true);", ["BOOL"]],
    ["M1 sayi yine number cizilir", "g.type = \"range\"; g.min = String(sema.min);", "g.type = \"number\"; g.min = String(sema.min);",
     ["ALANLAR", "V1_NUMBER_0", "V2_RANGE_2"]],
    ["FM-M11 malzeme secimi govdeye girmez", "      if (S.secim) govde.secim = S.secim;\n", "", ["KUYRUK"]],
    ["FM-MK kontrol (yorum)", "// FORM ALANLARI — türün", "// form alanlari — turun", []],
  ];
  for (const [ad, capa, yerine, olmeli] of FM_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await senaryo(EKRAN_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m));
  }
  // M2 (VERİ mutantı, bellek kopyası): büst kaydına "İki renk" kutusu geri gelir -> V4 KIRMIZI.
  const FM_VERI_MUT = [
    ["M2 iki_renk kutusu geri gelir", "          ters: {\n            tip: \"bool\",",
     "          iki_renk: { tip: \"bool\", etiket: \"İki renk\", varsayilan: false },\n          ters: {\n            tip: \"bool\",",
     ["ALANLAR", "AYNI_FONKSIYON", "KUYRUK", "V3_DUGME", "V4_IKI_RENK_0"]],
  ];
  for (const [ad, capa, yerine, olmeli] of FM_VERI_MUT) {
    if (VERI_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await senaryo(EKRAN_KAYNAK, VERI_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m));
  }
  // V6 FİYAT DEĞİŞMEZ (form alanı kalkması fiyata dokunmaz): 120 mm PLA 1.200 · Renkli 1.380 · Renkli+PETG 1.794 TL.
  const VF = veriYukle(VERI_KAYNAK);
  const v6 = [VF.fiyatKurus("bust", 120, { renkli: false, malzeme: "PLA" }), VF.fiyatKurus("bust", 120, { renkli: true, malzeme: "PLA" }),
    VF.fiyatKurus("bust", 120, { renkli: true, malzeme: "PETG" })];
  ol("V6 bust 120 mm fiyat: PLA 1.200 · Renkli 1.380 · Renkli+PETG 1.794 TL (renk tavani 2)",
    JSON.stringify(v6) === JSON.stringify([120000, 138000, 179400]) && VF.renkTavani("bust") === 2, JSON.stringify(v6));
  // V8 TÜM TÜRLERDE FORM KURALI: başka türde (yapboz, gerçek kayıt + bellekte bir bool alanı) sayi -> sürgü + canlı
  // değer, bool -> düğme; ③'te sayı kutusu ve onay kutusu 0.
  const v8 = async (kaynak) => {
    const V8 = sentetik(VERI_KAYNAK);
    const yt = V8.turBul("yapboz");
    yt.form = Object.assign({}, yt.form, { v8_bool: { tip: "bool", etiket: "V8", varsayilan: true } });
    const e8 = await ekranKos(kaynak, V8, { acik: true, turler: [acikTur(V8, "yapboz")] }, null, null, { kart: "yapboz" });
    const d8 = [...e8.bolum.agac()];
    const p3 = d8.find((n) => n.id === "foto-pencere-3");
    const n3 = p3 ? [...p3.agac()] : [];
    // form_sunum alanı (uzun_kenar_mm, tohum) ③'te ÇİZİLMEZ (V-B); kural çizilen sayi alanlarına.
    const sayilar = Object.keys(yt.form).filter((a) => yt.form[a].tip === "sayi" && !(yt.form_sunum && a in yt.form_sunum));
    const sw = n3.find((n) => n.id === "foto-param-v8_bool");
    return sayilar.length > 0 && sayilar.every((a) => {
      const g = n3.find((n) => n.id === "foto-param-" + a);
      const sonra = g && g.parentNode ? g.parentNode.childNodes[g.parentNode.childNodes.indexOf(g) + 1] : null;
      return !!g && g.type === "range" && !!sonra && sonra.classList.contains("foto-uretim-surgu-deger") && /\d/.test(sonra.textContent);
    }) && !!sw && sw.tagName === "BUTTON" && sw.getAttribute("role") === "switch" && sw.getAttribute("aria-checked") === "true" &&
      !n3.some((n) => n.tagName === "INPUT" && (n.type === "number" || n.type === "checkbox"));
  };
  ol("V8 baska tur (yapboz): sayi -> surgu + canli deger · bool -> role=switch (varsayilan acik) · number/checkbox 0",
    await v8(EKRAN_KAYNAK) === true, "");
  ol("V8-M1 sayi yine number cizilir -> V8 KIRMIZI",
    await v8(EKRAN_KAYNAK.replace("g.type = \"range\"; g.min = String(sema.min);", "g.type = \"number\"; g.min = String(sema.min);")) === false, "");
  // V-A BÜST ③ ArTisT CÜMLELERİ (b25b2804, AYNEN): Renk / Ölçü / Malzeme altında + dürüstlük = tür notu #4; YALNIZ büstte.
  const A_RENK = "Siyah, Beyaz ya da Gri seçersen büst tek renk olur; Renkli seçersen renkler fotoğrafından otomatik seçilir (büstte en çok 2 renk).";
  const A_OLCU = "Büstün en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.";
  const A_MALZEME = "PLA ev içi kullanım içindir; PETG dış mekân ve genel amaçlı kullanım için daha yüksek sıcaklığa dayanır (+%30).";
  const A_NOT = "Siyah, Beyaz ya da Gri seçilirse büst tek renktir; Renkli seçilirse taban + kabartma olmak üzere en çok 2 renk fotoğraftan otomatik belirlenir.";
  const A_HEPSI = [A_RENK, A_OLCU, A_MALZEME, A_NOT];
  // V-B YAPBOZ ③ (BaBa 9 Eki 20:38): Uzun kenar + Tohum ekranda YOK (değer Ölçü sürgüsü / varsayılan) · satır/sütun
  // sürgü + canlı "N adet" · kabartma yönü 2 Türkçe etiket (value aynen) · gövdede uzun_kenar_mm = Ölçü, tohum tam sayı.
  const vab = async (kaynak, veriKaynak = VERI_KAYNAK) => {
    const s = {};
    const metinSay = (dd, m) => dd.filter((n) => n.tagName === "P" && n.textContent === m).length;
    const VA = sentetik(veriKaynak);
    const eb = await ekranKos(kaynak, VA, { acik: true, turler: [acikTur(VA, "bust")] }, null, null, { kart: "bust" });
    const db = [...eb.bolum.agac()];
    const p3b = db.find((n) => n.id === "foto-pencere-3"), p2b = db.find((n) => n.id === "foto-pencere-2");
    const n3b = p3b ? [...p3b.agac()] : [], n2b = p2b ? [...p2b.agac()] : [];
    s.VA_BUST = [A_RENK, A_OLCU, A_MALZEME].every((m) => metinSay(n3b, m) === 1) && metinSay(n2b, A_NOT) === 1;
    s.VA_DIGER = true;
    // TUR-A: plaket + yapboz Malzeme cümlesi = büstün Malzeme cümlesi AYNEN (METİN KAYNAĞI "büstteki cümle aynen");
    // renk/ölçü ve tür notu #4 farklıdır. Anahtarlik'te alan_aciklamalari yok, hiçbiri görünmemeli.
    const DIGER_BEKLENEN = { plaket: [A_RENK, A_OLCU, A_NOT], yapboz: [A_RENK, A_OLCU, A_NOT], anahtarlik: A_HEPSI };
    for (const kod of ["plaket", "yapboz", "anahtarlik"]) {
      const Vd = sentetik(veriKaynak);
      const ed = await ekranKos(kaynak, Vd, { acik: true, turler: [acikTur(Vd, kod)] }, null, null, { kart: kod });
      const dd = [...ed.bolum.agac()];
      if (!dd.some((n) => n.id === "foto-olcu") || DIGER_BEKLENEN[kod].some((m) => metinSay(dd, m) > 0)) s.VA_DIGER = false;
    }
    const VB = sentetik(veriKaynak);
    const ac = acikTur(VB, "yapboz");
    const e = await ekranKos(kaynak, VB, { acik: true, turler: [ac] }, null, null, { kart: "yapboz" });
    const d = () => [...e.bolum.agac()];
    const id = (x) => d().find((n) => n.id === x) || null;
    const p3 = id("foto-pencere-3");
    const n3 = p3 ? [...p3.agac()] : [];
    s.VB1_NUMBER_0 = !!p3 && n3.filter((n) => n.tagName === "INPUT" && n.type === "number").length === 0;
    s.VB2_RANGE_3 = !!p3 && JSON.stringify(n3.filter((n) => n.tagName === "INPUT" && n.type === "range").map((n) => n.id).sort()) ===
      JSON.stringify(["foto-olcu", "foto-param-satir", "foto-param-sutun"]);
    const yazi = (g) => (g && g.parentNode ? g.parentNode.childNodes[g.parentNode.childNodes.indexOf(g) + 1] : null);
    const sa = id("foto-param-satir"), su = id("foto-param-sutun");
    const once = [yazi(sa), yazi(su)].map((n) => (n ? n.textContent : ""));
    let sonra = "";
    if (sa) { sa.value = "5"; sa.tetikle("input"); sonra = yazi(sa) ? yazi(sa).textContent : ""; }
    s.VB2_CANLI = !!sa && !!su && sa.min === "3" && sa.max === "8" && sa.step === "1" && su.min === "3" && su.max === "8" &&
      JSON.stringify(once) === JSON.stringify(["3 adet", "4 adet"]) && sonra === "5 adet";
    const sec = id("foto-param-kabartma_yon");
    const ops = sec ? [...sec.agac()].filter((n) => n.tagName === "OPTION") : [];
    s.VB4_YON = ops.length === 2 && JSON.stringify(ops.map((o) => o.textContent)) === JSON.stringify(["Açık tonlar yüksek", "Koyu tonlar yüksek"]) &&
      JSON.stringify(ops.map((o) => o.value)) === JSON.stringify(["acik_yuksek", "koyu_yuksek"]);
    // Ölçü sürgüsünü 170 mm'ye çek, sonra form doğrulamasını tetikle: gövde (VERI.parametreDogrula'ya giden) okunur.
    const ol_ = id("foto-olcu"), sira = ac.olculer.findIndex((o) => o.mm === 170);
    if (ol_ && sira >= 0) { ol_.value = String(sira); ol_.tetikle("input"); }
    if (sa) { sa.value = "4"; sa.tetikle("input"); }
    const son = VB.cagri.filter((c) => c.kod === "yapboz").pop();
    const p = son ? JSON.parse(son.p) : {};
    s.VB3_TOHUM = !d().some((n) => /Tohum/.test(n.textContent || "") && (n.tagName === "LABEL" || n.tagName === "P")) &&
      !id("foto-param-tohum") && Number.isInteger(p.tohum) && p.tohum >= 0 && p.tohum <= 2147483647;
    s.VB5_UZUN_KENAR = sira >= 0 && !id("foto-param-uzun_kenar_mm") && !d().some((n) => n.tagName === "LABEL" && /Uzun kenar/.test(n.textContent)) &&
      p.uzun_kenar_mm === 170 && !!son && son.d.ok === true && p.satir === 4;
    // Fiyat değişmez: yapboz 100 mm PLA 1.000 TL.
    s.VB_FIYAT = VB.fiyatKurus("yapboz", 100, { renkli: false, malzeme: "PLA" }) === 100000;
    Object.defineProperty(s, "iz", { value: { p, once, sonra, istisna: e.istisnaMetni }, enumerable: false });
    return s;
  };
  const sv = await vab(EKRAN_KAYNAK);
  ol("V-A bust ③ Renk/Ölçü/Malzeme ArTisT cümleleri + tür notu #4 birebir (1×)", sv.VA_BUST, JSON.stringify(sv));
  ol("V-A2 plaket/yapboz/anahtarlik: büst cümleleri 0", sv.VA_DIGER, JSON.stringify(sv));
  ol("V-B1 yapboz ③ input[type=number] 0", sv.VB1_NUMBER_0, JSON.stringify(sv));
  ol("V-B2 yapboz ③ input[type=range] 3 (Ölçü + satır + sütun)", sv.VB2_RANGE_3, JSON.stringify(sv));
  ol("V-B2b satır/sütun 3..8 adım 1, canlı '3 adet'/'4 adet' -> kaydırınca '5 adet'", sv.VB2_CANLI, JSON.stringify([sv, sv.iz]));
  ol("V-B3 'Tohum' metni 0 · gövdede tohum tam sayı 0..2147483647", sv.VB3_TOHUM, JSON.stringify([sv, sv.iz]));
  ol("V-B4 kabartma yönü 2 Türkçe etiket, value aynen", sv.VB4_YON, JSON.stringify(sv));
  ol("V-B5 'Uzun kenar' alanı 0 · gövdede uzun_kenar_mm = Ölçü sürgüsü (170) + doğrulama ok", sv.VB5_UZUN_KENAR, JSON.stringify([sv, sv.iz]));
  ol("V-B fiyat değişmez: yapboz 100 mm PLA 1.000 TL", sv.VB_FIYAT, JSON.stringify(sv));
  const VAB_MUT = [
    ["M-A ArTisT cümlesi başka türde de çıkar", "ekran",
     "var t = F && typeof F.turBul === \"function\" ? F.turBul(kod) : null;\n    var m = t && t.alan_aciklamalari",
     "var t = F && typeof F.turBul === \"function\" ? F.turBul(\"bust\") : null;\n    var m = t && t.alan_aciklamalari", ["VA_DIGER"]],
    ["M-B1 tohum yine görünür", "veri", "          tohum: { deger: \"varsayilan\" }\n", "", ["VB2_RANGE_3", "VB3_TOHUM"]],
    ["M-B2js uzun_kenar_mm sabit 150 gider", "veri",
     "if (fs.deger === \"olcu\") { return typeof olcu === \"number\" && isFinite(olcu) ? olcu : undefined; }",
     "if (fs.deger === \"olcu\") { return 150; }", ["VB5_UZUN_KENAR"]],
    ["M-B4 kabartma yönü ham kod", "ekran", "var op = el(\"option\", null, etMap && etMap[k] ? etMap[k] : k);",
     "var op = el(\"option\", null, k);", ["VB4_YON"]],
    ["M-VAB-K kontrol (yorum)", "ekran", "// ③ ortak alan (renk/olcu/malzeme) altındaki", "// ortak alan altindaki", []],
  ];
  for (const [ad, hedef, capa, yerine, olmeli] of VAB_MUT) {
    const kay = hedef === "ekran" ? EKRAN_KAYNAK : VERI_KAYNAK;
    if (kay.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = hedef === "ekran" ? await vab(EKRAN_KAYNAK.replace(capa, yerine)) : await vab(EKRAN_KAYNAK, VERI_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m));
  }
}

// ================================================================ AN — ANAHTARLIK ② YAZI (9 Eki)
// Okan ekranı 9 Eki ("foto ekle çalışmıyor"): ② ölü "Foto ekle" + yazı alanı YOK + "İleri" girdisiz AÇIK + dürüstlük
// cümlesi 2×. Yeni kural: ② girdilerden EN AZ BİRİ (VERI.girdiYeterli, sunucuyla aynı); metin girdili türün yazı alanı
// ②'de; fotoğraf almayan türde foto kutusu çizilmez; ② dürüstlük cümlesi 1×.
{
  console.log("AN) ANAHTARLIK ② — yazı alanı ②'de, İleri girdisiz KAPALI, foto kutusu ölü çizilmez, dürüstlük 1×");
  const senaryo = async (kaynak) => {
    const s = {};
    const V = veriYukle(VERI_KAYNAK);
    const an = V.turBul("anahtarlik");
    const acikA = { acik: true, turler: [{ kod: "anahtarlik", ad: an.ad, aciklama: "x", ornek_sayisi: 1,
      olculer: V.olcuSecenekleri("anahtarlik").map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus("anahtarlik", mm) })) }] };
    const e = await ekranKos(kaynak, V, acikA, null, null, { kart: "anahtarlik" });
    const d = () => [...e.bolum.agac()];
    const id = (x) => d().find((n) => n.id === x) || null;
    const p2 = id("foto-pencere-2"), ta = id("foto-param-satirlar"), ileri = id("foto-ileri"), yazi = id("foto-yazi");
    const kutu = id("foto-yukle-kutu");
    s.YAZI_IKIDE = !!(p2 && ta && yazi) && ta.tagName === "TEXTAREA" && [...p2.agac()].includes(ta) && yazi.hidden === false;
    s.FOTO_KUTU_GIZLI = !!kutu && kutu.hidden === true;
    s.ILERI_BOS_KAPALI = !!ileri && ileri.hidden === false && ileri.disabled === true;
    const yaz = (v) => { if (ta) { ta.value = v; ta.tetikle("input"); } };
    yaz("Ayşe");
    s.ILERI_YAZI_ACIK = !!ileri && ileri.disabled === false;
    yaz("");
    s.ILERI_SILINCE_KAPALI = !!ileri && ileri.disabled === true;
    yaz("x".repeat(41));
    const hata = d().find((n) => n.tagName === "P" && n.classList.contains("foto-uretim-ayrinti") && !n.hidden &&
      n.textContent === "Bu alanları kontrol et." && p2 && [...p2.agac()].includes(n));
    s.YAZI_HATA = !!ileri && ileri.disabled === true && !!hata;
    const durust = p2 ? [...p2.agac()].filter((n) => n.tagName === "P" && n.textContent === an.durustluk).length : -1;
    s.DURUST_TEK = durust === 1 && an.ornek_notu !== an.durustluk;
    Object.defineProperty(s, "iz", { value: { durust, istisna: e.istisnaMetni }, enumerable: false });
    return s;
  };
  const s0 = await senaryo(EKRAN_KAYNAK);
  ol("AN1 anahtarlık yazı alanı (textarea satirlar) ② ekranında, #foto-yazi görünür", s0.YAZI_IKIDE, JSON.stringify(s0));
  ol("AN2 fotoğraf almayan türde ② foto kutusu çizilmez (ölü 'Foto ekle' 0)", s0.FOTO_KUTU_GIZLI, JSON.stringify(s0));
  ol("AN3 ② yazı boşken 'İleri' KAPALI", s0.ILERI_BOS_KAPALI, JSON.stringify(s0));
  ol("AN4 ② yazı 'Ayşe' girilince 'İleri' AÇIK", s0.ILERI_YAZI_ACIK, JSON.stringify(s0));
  ol("AN5 ② yazı silinince 'İleri' yeniden KAPALI", s0.ILERI_SILINCE_KAPALI, JSON.stringify(s0));
  ol("AN6 ② 41 karakter: 'İleri' KAPALI + ② hata satırı 'Bu alanları kontrol et.'", s0.YAZI_HATA, JSON.stringify(s0));
  ol("AN7 ② dürüstlük cümlesi TAM 1× (ornek_notu ayrı cümle)", s0.DURUST_TEK, JSON.stringify([s0, s0.iz]));
  const AN_MUT = [
    ["AN-M1 ② İleri girdisiz açık kalır (girdiYeterli kapısı silindi)",
     'F.girdiYeterli(S.tur, { foto: !!S.dosya, parametreler: parametreGovde() }) === ""', "true",
     ["ILERI_BOS_KAPALI", "ILERI_SILINCE_KAPALI", "YAZI_HATA"]],
    ["AN-M2 metin alanı ②'ye çizilmez (③'te kalır)", "var hedefKap = S.alanYazi && metinGirdisi() &&", "var hedefKap = false &&",
     ["YAZI_IKIDE"]],
    ["AN-MK kontrol (yorum)", "// ② YAZI (anahtarlık 9 Eki): metin girdili", "// ② yazi (anahtarlik 9 Eki): metin girdili", []],
  ];
  for (const [ad, capa, yerine, olmeli] of AN_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await senaryo(EKRAN_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m));
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

// Okan 9 Eki (R1): bolge basina renk secicisi KALKTI — renk TEK secim (3 ana renk / Renkli), tum bolgeler o renk.
// Eski RKU1/RKU2 (pasif bolgenin seçicisi gizli) bu emirle konusuz kaldi; pasif bolgenin ucretlenmemesi/uretilmemesi
// sunucuda RKK2/RKK3'te olculmeye DEVAM eder.
console.log("RKU) BOLGELI TUR EKRANDA — tek renk secicisi (3 ana renk), bolge basina secici YOK, form alanlari yerinde (Okan 9 Eki)");
{
  // K3b2: kart evreni sabit (KARTLAR) → sentetik tür seçilemez. Koşullu bölge deseni GERÇEK yapboz kaydına
  // (bellekteki veri kopyasında) eklenir: taban Var/Yok + taban rengi yalnız "Var"da · başlık dolu -> yazı.
  const sentetikR = (kaynakVeri) => {
    const V = veriYukle(kaynakVeri);
    // K3d: yapboz PALET turu; koşullu bolge deseni palet alanlari SILINMIS kopyaya konur.
    delete V.turBul("yapboz").renk_secimi; delete V.turBul("yapboz").palet_bolgeleri;
    Object.assign(V.turBul("yapboz"), {
      renk_bolgeleri: [{ kod: "taban", ad: "Taban", renkler: ["Beyaz", "Siyah"] },
                       { kod: "logo", ad: "Logo", renkler: ["Siyah", "Beyaz"] },
                       { kod: "yazi", ad: "Yazı", renkler: ["Kırmızı", "Beyaz"] }],
      renk_kosul: { taban: [{ alan: "taban", degerler: ["Var"] }], yazi: [{ alan: "baslik", dolu: true }] },
      form: { taban: { tip: "secim", etiket: "Taban", secenekler: ["Yok", "Var"] }, baslik: { tip: "secim", etiket: "Baslik", secenekler: ["", "Ada"] } },
      fiyat: { formul: "mm_x_10tl", adim_mm: 10, taban_tl: 600, renk_tavani: 3 } });
    return V;
  };
  const acikR = { acik: true, turler: [{ kod: "yapboz", ad: "Yapboz", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  const rku = async (kaynak) => {
    const s = {};
    const e = await ekranKos(kaynak, sentetikR(VERI_KAYNAK), acikR, null, null, { kart: "yapboz" });
    const d = () => [...e.bolum.agac()];
    const bolgeGrubu = d().filter((n) => n.getAttribute && n.getAttribute("data-renk-bolge")).length;
    const radyo = d().filter((n) => n.tagName === "INPUT" && n.name === "foto-renk").map((n) => n.value);
    const sec = d().find((n) => n.id === "foto-param-taban"), bas = d().find((n) => n.id === "foto-param-baslik");
    s.ILK = !!sec && !!bas && bolgeGrubu === 0 && JSON.stringify(radyo) === '["Siyah","Beyaz","Gri"]';
    return s;
  };
  const s = await rku(EKRAN_KAYNAK);
  ol("RKU1 bolgeli tur: bolge basina renk secicisi 0 · tek renk secicisi [Siyah,Beyaz,Gri] · form alanlari (taban/baslik) yerinde", s.ILK === true, JSON.stringify(s));
  const m = await rku(EKRAN_KAYNAK.replace("    var secenek = F.ANA_RENKLER.slice();", "    var secenek = F.PLA_RENKLERI.slice();"));
  ol("RKU-M1 ana renk yerine 9 renk listesi -> RKU KIRMIZI", m.ILK === false, JSON.stringify(m));
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
  // K3d: anahtarlik artik KAYITLI (programin 5. turu) -> kayitsiz tur nobetcisi magnet (5 Eki kurali AYNEN).
  const pf = await fm.panelFotoAcik(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tur: "magnet", acik: true }) }), e2, Date.now());
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-TEST-T', 0, ?, 'magnet', 100, 'build-baslat', ?, '2000-01-01T00:00:00.000Z')")
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
  ["M1 SINIR", "if (!makine && sayi.kisi >= VERI.sinir_ziyaretci_24s) {", "if (false) {", "D"],
  ["M2 BOT", "if (!(await botDogrula(request, env, g.turnstile_token))) {", "if (false) {", "E"],
  ["M3 ANALIZ", "if (onarimGerekli(p)) {", "if (false) {", "J"],
  // Tur uyeligi MANIFESTTEN (motor M + ortam eslemesi); kapi silinince manifestte olmayan tur acilir.
  ["M4 MAGNET ACILDI (manifest kapisi silindi)", "VERI.kolu(kod) === \"saglayici\" &&\n    Object.prototype.hasOwnProperty.call(TUR_ORTAM, kod);",
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
  const fiyatla = (renkler, ek) => fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: 100, adet: 1, ...(renkler === undefined ? {} : { renkler }), ...(ek || {}) }, Date.now());
  const birim = async (renkler, ek) => { const r = await fiyatla(renkler, ek); return r.satir ? r.satir.birim_kurus : null; };
  const red = async (renkler, ek, hata) => { const r = await fiyatla(renkler, ek); return r.kod === 400 && !!r.hata && r.hata.hata === (hata || "gecersiz-renk"); };
  const s = {};
  const R = { renkli: true };
  // FIYAT (Okan 9 Eki): ana renk = taban (100 mm -> 1.000 TL) · Renkli ×1,15 (renk ADEDINDEN bagimsiz) · PETG ×1,30.
  s.FIYAT = (await birim(["Beyaz"])) === 100000 && (await birim(["Siyah"])) === 100000 && (await birim(["Gri"], { renkli: false })) === 100000 &&
            (await birim(["Beyaz", "Siyah"], R)) === 115000 && (await birim(["Beyaz", "Siyah", "Gri", "Mavi"], R)) === 115000 &&
            (await birim(["Mavi"], R)) === 115000 && (await birim(["Gri"], { malzeme: "PETG" })) === 130000 &&
            (await birim(["Beyaz", "Lacivert"], { renkli: true, malzeme: "PETG" })) === 149500;
  // ANA2: ana renkte 2. renk ne ucretlenir ne uretilir -> RED; ana renkte palet disi (Mavi) -> RED.
  s.ANA2 = (await red(["Beyaz", "Siyah"])) && (await red(["Beyaz", "Siyah"], { renkli: false })) && (await red(["Mavi"]));
  // BES: 5. renk hem kalem cozumunde hem fiyatlamada RED.
  const bes = ["Beyaz", "Siyah", "Gri", "Mavi", "Sarı"];
  const coz = fm.fotoKalemCoz({ foto_is: is, olcu_mm: 100, adet: 1, renkler: bes, renkli: true });
  s.BES = coz.hata === "gecersiz-renk" && (await red(bes, R));
  // BOZUK: renksiz / bos / paletten olmayan / tekrarli -> 400 gecersiz-renk; bilinmeyen renkli/malzeme -> RED
  // (kalem cozumu + fiyatlama; ASA/ABS foto programinda YOK).
  s.BOZUK = (await red(undefined)) && (await red([])) && (await red(["Mor"], R)) && (await red(["Beyaz", "Beyaz"], R)) &&
            fm.fotoKalemCoz({ foto_is: is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], renkli: "evet" }).hata === "gecersiz-renk" &&
            fm.fotoKalemCoz({ foto_is: is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], malzeme: "ASA" }).hata === "gecersiz-malzeme" &&
            fm.fotoKalemCoz({ foto_is: is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], malzeme: "ABS" }).hata === "gecersiz-malzeme" &&
            (await red(["Beyaz"], { malzeme: "ABS" }, "gecersiz-malzeme")) && (await red(["Beyaz"], { malzeme: "pla" }, "gecersiz-malzeme"));
  // ISTEMCI: kalemin tutar alanlari OKUNMAZ (kalem cozumu tasimaz, fiyatlama yok sayar).
  const ic = fm.fotoKalemCoz({ foto_is: is, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], fiyat_kurus: 1, birim_kurus: 1, tutar_kurus: 1, gosterim_kurus: 1 });
  s.ISTEMCI = !!ic.kalem && !["fiyat_kurus", "birim_kurus", "tutar_kurus", "gosterim_kurus"].some((a) => a in ic.kalem) &&
              (await birim(["Beyaz"], { fiyat_kurus: 1, birim_kurus: 1 })) === 100000;
  // KAYIT: satir renkleri + Renkli/PETG kalemi + malzeme tasir.
  const r2 = await fiyatla(["Beyaz", "Lacivert", "Kırmızı"], { renkli: true, malzeme: "PETG" });
  s.KAYIT = !!r2.satir && r2.satir.birim_kurus === 149500 && r2.satir.tutar_kurus === 149500 && r2.satir.malzeme === "PETG" &&
            JSON.stringify(r2.satir.foto_renkler) === '["Beyaz","Lacivert","Kırmızı"]' && r2.satir.foto_renkli === true &&
            r2.satir.renk === "Beyaz, Lacivert, Kırmızı" && /3 renkli yorumu · Renkli \(\+%15\) · PETG \(\+%30\)/.test(r2.satir.parametre_detay) &&
            !/ek renk/.test(r2.satir.parametre_detay);
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

console.log("K1) 2D KONSEPT YOK (Okan 9 Eki: \"bunu tamamen sil\") — uclar 404, /acik konsept alani yok, kaynakta 0");
{
  const KONSEPT_UCLARI = [
    ["/foto/konsept", { govde: onizlemeGovde() }],
    ["/foto/konsept-durum?konsept=" + "a".repeat(32), {}],
    ["/foto/konsept-gorsel?konsept=" + "a".repeat(32), {}],
    ["/yonet/foto/ornek-konsept", { govde: onizlemeGovde(), basliklar: YONET }],
    ["/yonet/foto/ornek-konsept-durum?konsept=" + "a".repeat(32), { basliklar: YONET }],
    ["/yonet/foto/ornek-konsept-gorsel?konsept=" + "a".repeat(32), { basliklar: YONET }],
  ];
  const kodlar = [];
  for (const [y, o] of KONSEPT_UCLARI) { kodlar.push((await istek(env, y, o)).kod); }
  ol("K1a 6 konsept ucu (musteri 3 + panel 3, anahtarli) 404", kodlar.every((k) => k === 404), kodlar.join(","));
  const ac = await istek(env, "/foto/acik");
  ol("K1b /foto/acik yanitinda `konsept` alani YOK", !!ac.v && !Object.prototype.hasOwnProperty.call(ac.v, "konsept"),
     ac.v ? Object.keys(ac.v).join(",") : "yanit-yok");
  const say = (k) => (k.match(/konsept/gi) || []).length;
  const veriK = fs.readFileSync(path.join(KOK, "foto-uretim-veri.js"), "utf8");
  ol("K1c 'konsept' kaynakta 0 (foto-uretim.js · foto-uretim-veri.js · shop/src/foto.js)",
     say(fs.readFileSync(path.join(KOK, "foto-uretim.js"), "utf8")) === 0 && say(veriK) === 0 && say(fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8")) === 0, "");
  // MUTANT: konsept ucu geri gelir -> K1a KIRMIZI olmali.
  const kmCapa = '  if (yol === "/foto/acik" && m === "GET") { return acikUcu(env, simdi, telegram); }\n';
  const km = await mutantModul(kmCapa, kmCapa + '  if (yol === "/foto/konsept" && m === "POST") { return fjson({ konsept: "x" }, 200); }\n');
  let kmKod = -1;
  if (km) {
    const r = await km.fotoUclari(new Request("https://pruvo3d.com/api/shop/foto/konsept", { method: "POST",
      headers: { "CF-Connecting-IP": "198.51.100.7", "Content-Type": "application/json" }, body: JSON.stringify(onizlemeGovde()) }),
      env, new URL("https://pruvo3d.com/api/shop/foto/konsept"), "/foto/konsept", null);
    kmKod = r.status;
  }
  ol("M-K1 konsept ucu geri gelirse 404 DEGIL (K1a KIRMIZI yanar)", km !== null && kmKod !== 404,
     km ? "mutant_kod=" + kmKod : "MUTANT_UYGULANMADI");
}

console.log("RK) RENK + MALZEME — 3 ana renk (tek renk) ya da Renkli +%15 · PLA / PETG +%30; renk adimi siparisin renk sayisiyla (Okan 9 Eki)");
{
  const s = await renkSenaryolar(foto);
  ol("RK1 plaket 100 mm: ana renk 1.000 · Renkli (2 ya da 4 renk) 1.150 · PETG 1.300 · Renkli+PETG 1.495 TL", s.FIYAT === true, JSON.stringify(s));
  ol("RK1b ana renkte 2. renk / palet disi renk -> 400 gecersiz-renk (ucretlenmez, uretilmez)", s.ANA2 === true, JSON.stringify(s));
  ol("RK1c istemci tutar alanlari kalem cozumunde YOK + fiyatlamada OKUNMAZ", s.ISTEMCI === true, JSON.stringify(s));
  ol("RK2 5. renk -> kalem cozumu + fiyatlama 400 gecersiz-renk", s.BES === true, JSON.stringify(s));
  ol("RK3 renksiz / bos / paletten olmayan / tekrarli -> 400 gecersiz-renk · renkli \"evet\" RED · ASA/ABS/pla -> gecersiz-malzeme", s.BOZUK === true, JSON.stringify(s));
  ol("RK4 satir foto_renkler + renk metni + 'Renkli (+%15) · PETG (+%30)' + malzeme PETG tasir (ek renk kalemi YOK)", s.KAYIT === true, JSON.stringify(s));
  ol("RK5 odenen 3 renkli siparis -> foto_uretim.renk_sayisi 3 + renk adimi max_colors 3", s.MAXC === true, JSON.stringify(s));
  ol("RK6 renk kaydi yok -> 'elle' renk-sayisi-yok, renk adimi cagrisi 0 (4'e DUSMEZ)", s.SIFIR === true, JSON.stringify(s));
}
// Okan 9 Eki: Renkli/PETG carpani sunucuda duserse · istemci fiyati okunursa · ana renkte 2. renk kabul edilirse KIRMIZI.
const BIRIM_CAPA = "  const birim = VERI.fiyatKurus(tur.kod, mm, { renkli: rs.renkli, malzeme: malz });";
const RK_MUTANTLAR = [
  ["RK-M1 RENKLI CARPANI SUNUCUDA DUSTU", BIRIM_CAPA, "  const birim = VERI.fiyatKurus(tur.kod, mm, { renkli: false, malzeme: malz });", ["FIYAT", "KAYIT"]],
  ["RK-M1b PETG CARPANI SUNUCUDA DUSTU", BIRIM_CAPA, "  const birim = VERI.fiyatKurus(tur.kod, mm, { renkli: rs.renkli, malzeme: \"PLA\" });", ["FIYAT", "KAYIT"]],
  ["RK-M5 ISTEMCI FIYATI OKUNUR", BIRIM_CAPA, BIRIM_CAPA.replace("const birim = ", "const birim = k.fiyat_kurus || "), ["ISTEMCI"]],
  ["RK-M6 ANA RENKTE 2. RENK KABUL", "  if (!renkli && n !== 1) { return null; }\n", "", ["ANA2"]],
  ["RK-M2 RENK SAYISI YOKSA 4'E DUSER (fail-open)",
   "if (!(Number.isInteger(n) && n >= 1 && n <= 4)) { return elleDusur(env, u, \"renk-sayisi-yok\", ozet, simdi, telegram); }",
   "if (!(Number.isInteger(n) && n >= 1 && n <= 4)) { u.renk_sayisi = 4; return renkBaslat(env, u, ozet, simdi, telegram); }", ["SIFIR"]],
  ["RK-M3 PALET DENETIMI SILINDI", "!r.every((x) => izinli.includes(x))", "false", ["ANA2", "BOZUK"]],
  ["RK-M4 max_colors SABIT 4", "{ model_url: glb, max_colors: n, printer_brand: \"bambu\" }",
   "{ model_url: glb, max_colors: 4, printer_brand: \"bambu\" }", ["MAXC"]],
  ["RK-MK KONTROL", "// Renkler kalemden (palet); birim", "// Renkler  kalemden (palet); birim", []],
];
for (const [ad, capa, yerine, olmeli] of RK_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await renkSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 8 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
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
  const yb = VERI.turBul("yapboz");
  // K3d: yapboz artik PALET turu (renk_secimi + palet_bolgeleri); desen yamasinda palet alanlari SILINIR
  // (yoksa renk sayimi palet koluna gider), finally'de asil degerleriyle geri konur.
  const YB_ALANLAR = ["renk_bolgeleri", "renk_kosul", "fiyat", "renk_secimi", "palet_bolgeleri"];
  const ybAsil = Object.fromEntries(YB_ALANLAR.map((a) => [a, yb[a]]));
  const desenKoy = (d) => {
    delete yb.renk_secimi; delete yb.palet_bolgeleri;
    Object.assign(yb, d, { fiyat: { ...ybAsil.fiyat, renk_tavani: 3 } });
  };
  try {
    for (const t of ["plaket", "figur", "bust", "yapboz"]) {
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
    const R = { renkli: true };
    s.TAVAN = red(await fiyatla(isP, { ...R, renkler: P5 })) && red(await fiyatla(isF, { ...R, renkler: P5 })) &&
              red(await fiyatla(isB, { ...R, renkler: P5.slice(0, 3), secim: malzeme("bust") })) &&
              (await fiyatla(isP, { ...R, renkler: P5.slice(0, 4) })).satir?.birim_kurus === 115000 &&
              (await fiyatla(isB, { ...R, renkler: P5.slice(0, 2), secim: malzeme("bust") })).satir?.birim_kurus === 115000;
    // K3b2: logo/ses türleri silindi → koşullu bölge desenleri GERÇEK yapboz kaydına (global VERI, geçici; finally'de
    // geri alınır) uygulanır — sunucunun koşullu bölge kodu AYNI.
    // LOGO deseni: taban "Yok" iken farkli taban rengi +0 ve satir/uretim seciminde YOK; taban "Var" iken +100.
    desenKoy({ renk_bolgeleri: [{ kod: "taban", ad: "Taban", renkler: ["Beyaz", "Siyah"] }, { kod: "logo", ad: "Logo", renkler: ["Siyah", "Beyaz"] }],
      renk_kosul: { taban: [{ alan: "taban", degerler: ["Var"] }] } });
    // Okan 9 Eki: ana renkte AKTIF bolgeler tek renk; pasif bolgenin farkli rengi ne sayilir ne uretilir.
    const lsec = { ...malzeme("yapboz"), taban_renk: "Siyah", logo_renk: "Beyaz" };
    const lYok = await fiyatla(await isKur("yapboz", { taban: "Yok" }), { secim: lsec });
    const lVar = await fiyatla(await isKur("yapboz", { taban: "Var" }), { secim: lsec });
    const lVarR = await fiyatla(await isKur("yapboz", { taban: "Var" }), { ...R, secim: lsec });
    s.LOGO = !!lYok.satir && lYok.satir.birim_kurus === 100000 && !("taban_renk" in lYok.satir.foto_secim) &&
             !/Taban: .*Siyah/.test(lYok.satir.renk) && red(lVar) && !!lVarR.satir && lVarR.satir.birim_kurus === 115000 &&
             lVarR.satir.foto_secim.taban_renk === "Siyah";
    // SES deseni: baslik bos -> yazi rengi sayilmaz (2 renk); baslik dolu -> 3 renk. Girdi okunamazsa koşullu bolge PASIF.
    desenKoy({ renk_bolgeleri: [{ kod: "plaka", ad: "Plaka", renkler: ["Beyaz", "Siyah"] }, { kod: "cubuk", ad: "Çubuk", renkler: ["Siyah", "Beyaz"] },
      { kod: "yazi", ad: "Yazı", renkler: ["Kırmızı", "Beyaz"] }], renk_kosul: { yazi: [{ alan: "baslik", dolu: true }] } });
    const ssec = { ...malzeme("yapboz"), plaka_renk: "Beyaz", cubuk_renk: "Beyaz", yazi_renk: "Kırmızı" };
    const sBos = await fiyatla(await isKur("yapboz", { baslik: "" }), { secim: ssec });
    const sDolu = await fiyatla(await isKur("yapboz", { baslik: "Ada" }), { secim: ssec });
    const sDoluR = await fiyatla(await isKur("yapboz", { baslik: "Ada" }), { ...R, secim: ssec });
    const sYok = await fiyatla(await isKur("yapboz", null), { secim: ssec });
    s.SES = !!sBos.satir && sBos.satir.birim_kurus === 100000 && red(sDolu) && !!sDoluR.satir && sDoluR.satir.birim_kurus === 115000 &&
            sDoluR.satir.foto_secim.yazi_renk === "Kırmızı" && !!sYok.satir && sYok.satir.birim_kurus === 100000;
    // BUST: odenen 2 palet rengi uretec girdisinde taban/rolyef bolgelerine sirayla.
    const g2 = fm.uretecGirdiJson("PR-RKK", { kalem: 0, tur: "bust", olcu_mm: 100, secim: {}, renkler: ["Lacivert", "Kırmızı"] });
    const g1 = fm.uretecGirdiJson("PR-RKK", { kalem: 0, tur: "bust", olcu_mm: 100, secim: {}, renkler: ["Gri"] });
    s.BUST = JSON.stringify(g2.renkler) === '{"taban":"Lacivert","rolyef":"Kırmızı"}' &&
             JSON.stringify(g1.renkler) === '{"taban":"Gri"}';
  } finally {
    for (const a of YB_ALANLAR) { if (ybAsil[a] === undefined) { delete yb[a]; } else { yb[a] = ybAsil[a]; } }
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  return s;
}

console.log("RKK) RENK TAVANI + KOSULLU BOLGE + PALET ESLEMESI — odenen her renk uretime bagli (BaBa 8 Eki 15:5x)");
{
  const s = await renkKosulSenaryolar(foto);
  ol("RKK1 Renkli: plaket 5 / figur 5 / bust 3 renk -> 400 gecersiz-renk · tavan icinde plaket 4 = bust 2 = 1.150 TL (renk adedi fiyatsiz)",
     s.TAVAN === true, JSON.stringify(s));
  ol("RKK2 kosullu taban (logo deseni, yapboz kaydinda) 'Yok' -> farkli taban rengi sayilmaz, secimde YOK, ana renk 1.000 TL · 'Var' ana renkte 2 renk RED · Renkli 1.150 TL", s.LOGO === true, JSON.stringify(s));
  ol("RKK3 kosullu yazi (ses deseni, yapboz kaydinda) baslik bos -> ana renk 1.000 · dolu ana renkte RED, Renkli 1.150 · girdi okunamazsa koşullu bolge pasif (fail-closed)",
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
  // K3b2: koordinat/rolyef silindi → içeriğe bağlı alt sınır kolu GERÇEK yapboz kaydında (global VERI, geçici
  // `olcu_min_dinamik`, finally'de geri) · sabit taban vakası GERÇEK bust (taban 60).
  const yb = VERI.turBul("yapboz"), ybDin = yb.olcu_min_dinamik;
  yb.olcu_min_dinamik = true;
  try {
    for (const t of ["yapboz", "bust"]) {
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
    // K3d: yapboz PALET turu -> renkler `renkler`den (Okan 9 Eki: 2 renk = Renkli, ×1,15); palet disi tur renksiz.
    const renkler = (tur) => (VERI.renkPaleti(tur) ? { renkli: true, renkler: ["Beyaz", "Siyah"] } : {});
    const fiyatla = async (is, tur, mm) => fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: mm, adet: 1, secim: secim(tur), ...renkler(tur) }, Date.now());
    const isK = await isKur("yapboz", { min_mm: 152.4 });
    const alt = await fiyatla(isK, "yapboz", 150);
    s.ALT = alt.kod === 400 && alt.hata.hata === "olcu-min" && alt.hata.min_mm === 160 && /en az 160 mm/.test(alt.hata.mesaj);
    const ust = await fiyatla(isK, "yapboz", 160);
    s.UST = !!ust.satir && ust.satir.birim_kurus === VERI.fiyatKurus("yapboz", 160, { renkli: true }) &&
            ust.satir.foto_renkler.length === 2 && ust.satir.birim_kurus === 184000;
    const yok = await fiyatla(await isKur("yapboz", null), "yapboz", 160);
    s.YOK = yok.kod === 400 && yok.hata.hata === "foto-onizleme-yok";
    const sab = await fiyatla(await isKur("bust", {}), "bust", 10);
    s.SABIT = sab.kod === 400 && sab.hata.hata === "gecersiz-olcu" && VERI.olcuAraligi("bust").en_az === 60;
  } finally {
    if (ybDin === undefined) { delete yb.olcu_min_dinamik; } else { yb.olcu_min_dinamik = ybDin; }
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  return s;
}

console.log("DMIN) DINAMIK ALT SINIR — icerige bagli turde onizlemenin olctugu min'in alti 400; sabit turde taban (BaBa 14:3x)");
{
  const s = await dinamikMinSenaryolar(foto);
  ol("DMIN1 icerige bagli tur (yapboz kaydi, dinamik min) min 152,4 mm -> 150 mm siparis 400 olcu-min 'en az 160 mm' (adima yuvarli)", s.ALT === true, JSON.stringify(s));
  ol("DMIN2 icerige bagli tur 160 mm -> fiyatlanir (160 mm x 10 TL × Renkli 1,15 = 1.840 TL)", s.UST === true, JSON.stringify(s));
  ol("DMIN3 onizlemede min olcumu yok -> 400 foto-onizleme-yok (fail-closed)", s.YOK === true, JSON.stringify(s));
  ol("DMIN4 sabit tur bust (taban 60) 10 mm -> 400 gecersiz-olcu", s.SABIT === true, JSON.stringify(s));
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
    renk_sayisi: 2, renkli: true, malzeme: "PLA", onizleme_ref: "/api/shop/foto/gorsel?is=" + is, atif: { utm_source: "test" }, adet: 1, ...(ek || {}) });
  const sip = (sepet) => ({ sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart",
    musteri, turnstile_token: "j", sepet });
  const siparis = async (no) => no
    ? await k.d1.prepare("SELECT tutar_kurus, urunler FROM siparisler WHERE siparis_no = ?").bind(no).first() : null;
  const s = {};
  const iyF = P.iyzico.length;
  const f = await cag("/baslat", sip([kalem({ gosterim_kurus: 1, fiyat_kurus: 1, tutar_kurus: 1, birim_kurus: 1 })]));
  const fs1 = await siparis(f.v && f.v.no);
  const fk = fs1 ? JSON.parse(fs1.urunler)[0] : null;
  s.F = f.kod === 200 && P.iyzico.length === iyF + 1 && !!fs1 && fs1.tutar_kurus === 115000 && fk.birim_kurus === 115000 &&
        (P.iyzico[P.iyzico.length - 1] || {}).price === "1400.00";
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
        fotoK.tutar_kurus === 115000 && fotoK.adet === 1 && ks.tutar_kurus === fotoK.tutar_kurus + katK.tutar_kurus;
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
  ol("SP1 istemci fiyat alanlari (1 kurus) YOK SAYILIR -> tutar 1.150,00 (100 mm × Renkli 1,15), iyzico 1400.00", s.F, JSON.stringify(s));
  ol("SP2 kalem turu onizleme kaydiyla uyusmaz -> 400 foto-tur-uyusmaz", s.T, JSON.stringify(s));
  ol("SP3 renk_sayisi sunucu sayimiyla uyusmaz -> 400 renk-sayisi-uyusmaz", s.R, JSON.stringify(s));
  ol("SP4 karma sepet (katalog + foto) TEK odeme, foto adet 1, toplam = kalemler", s.K, JSON.stringify(s));
  ol("SP5 odeme onayinda foto_uretim kuyrugu (is/tur/olcu/renk_sayisi kalemden)", s.Q, JSON.stringify(s));
}
const SP_MUTANTLAR = [
  ["SPM1 ISTEMCI FIYATI OKUNUR", [
    ["foto.js", "  return { kalem: { foto_is: isNo, olcu_mm: olcu, adet,", "  return { kalem: { ...k, foto_is: isNo, olcu_mm: olcu, adet,"],
    ["foto.js", "  const birim = VERI.fiyatKurus(tur.kod, mm, { renkli: rs.renkli, malzeme: malz });",
                "  const birim = k.gosterim_kurus || VERI.fiyatKurus(tur.kod, mm, { renkli: rs.renkli, malzeme: malz });"]], ["F"]],
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
// (sayfa-3adim K2b — parça kapısı + B2 tek + İptal hatası + iç çubuk + mutantlar). K3b2: kart evreni sabit
// (KARTLAR) → sentetik foto türü yerine GERÇEK plaket kartı (foto-1, sağlayıcı kolu); girdi türü (sentetik-g)
// ve M-ADIM2 vakaları SİLİNDİ (K3a: tüm türler foto; ② başlığı türe göre değişmez).
// ÖLÇÜM: ret cümlesi birebir · 5 kelime DUR · 5 tasarım geçer · foto soru çıkar 3/3 + Evet/Hayır/cevapsız ·
//         DUR'da 0 istek · İptal→yeni tür ② dolu · B2 sayısı 1 · iç çubuk 0
console.log("K2b) UYUM KAPISI + B2 TEK + İPTAL + MUTANTLAR");
const ORTAK_RET = "Fotoğraftan parça ya da yedek parça üretmiyoruz.";
const acikGercekTur = (V, kod) => ({ kod, ad: V.turBul(kod).ad, aciklama: "x", ornek_sayisi: 1,
  olculer: V.olcuSecenekleri(kod).map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus(kod, mm) })) });
const acikGercek = (V, kodlar) => ({ acik: true, turler: kodlar.map((k) => acikGercekTur(V, k)) });
{
  // Sayfa metni (ArTisT c35a848d) ortak ret cümlesi = kaynaktaki A_METIN_BIREBIR (TEK KAYNAK, birebir).
  const METIN_DOSYA = path.join(KOK, "..", "pruvo-pazarlama", "icerik", "foto-ozel-uretim-sayfa-metni.md");
  const metinRet = fs.existsSync(METIN_DOSYA)
    ? ((fs.readFileSync(METIN_DOSYA, "utf8").split("## Ortak ret cümlesi")[1] || "").split("\n").map((x) => x.trim()).filter(Boolean)[1] || "")
    : ORTAK_RET;
  const fotoAcik = { acik: true, turler: [{ kod: "plaket", ad: "Kabartma plaket", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  // K2b fikstür biçimi AYNEN: /acik türü TAM manifest kaydı (girdi dahil). K3c: uyumKontrol girdiyi MANIFESTTEN
  // (F.turBul) okur — CANLI /acik biçimi (`fotoAcik`, girdi YOK) ile de soru çıkmalı (K2b-C vakaları + M-UYUM-CANLI).
  const fotoAcikTam = { acik: true, turler: [{ ...veriYukle(VERI_KAYNAK).turBul("plaket"), ornek_sayisi: 1, olculer: [{ mm: 100, fiyat_kurus: 100000 }] }] };
  const kelimeDUR = ["annemin parçası", "telefonumun yedeği", "kırıldı", "mekanizması bozuldu", "orijinal dişlisi"];
  const tasarimGecer = ["annemin portresi", "köpeğim Pamuk", "logo", "deniz manzarası", "düğün tarihi"];
  // Ortak: plaket kartı (oturumdan seçili) → ② "Nasıl olsun?" yaz → (Evet/Hayır) → uyum paneli oku.
  const uyumSonucBul = async (kaynak, tarif, cevap, acik) => {
    const V = veriYukle(VERI_KAYNAK);
    const kayit = { is: "a".repeat(32), tur: "plaket", olcu: 100 };
    const e = await ekranKos(kaynak, V, acik || fotoAcikTam, kayit, undefined, { turnstileOto: true, kart: "plaket" });
    const dd = () => [...e.bolum.agac()];
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta && tarif != null) { ta.value = tarif; ta.tetikle("input"); }
    if (cevap === true) { const evet = dd().find((n) => n.id === "foto-uyum-evet"); if (evet) evet.tetikle("click"); }
    else if (cevap === false) { const hayir = dd().find((n) => n.id === "foto-uyum-hayir"); if (hayir) hayir.tetikle("click"); }
    const soruBaslik = dd().find((n) => n.classList && n.classList.contains("foto-uretim-uyum-baslik") && n.textContent === "Tasarım mı, parça mı?");
    const aMetin = dd().find((n) => n.classList && n.classList.contains("foto-uretim-uyum-metin"));
    return { soruVar: !!soruBaslik, aMetin: aMetin ? aMetin.textContent : null, ekran: e };
  };

  let dur5 = 0;
  for (const t of kelimeDUR) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, t, undefined);
    if (r.aMetin && r.aMetin.indexOf("Fotoğraftan parça ya da yedek parça üretmiyoruz") === 0 && !r.soruVar) dur5++;
  }
  ol("K2b-1 parça kelime vakası 5/5 uygun_degil (ortak ret cümlesi)", dur5 === 5, "basarili=" + dur5);
  let gecer5 = 0;
  for (const t of tasarimGecer) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, t, false);  // Hayır
    if (!r.aMetin && !r.soruVar) gecer5++;
  }
  ol("K2b-2 tasarım tarifi 5/5 geçer (Hayır → uyum OK)", gecer5 === 5, "basarili=" + gecer5);
  // Okan 9 Eki "bunu sil": foto türlerindeki "Tasarım mı, parça mı?" kapalı sorusu KALDIRILDI.
  // Soru HİÇBİR durumda çıkmaz (tam manifest + CANLI /acik biçimi); tasarım tarifi cevapsız GEÇER,
  // parça kelimesi yine DUR (ret cümlesi). Soru geri eklenirse K2b-3/C3 KIRMIZI.
  const soruVakalari = ["annemin portresi", "logo", "deniz manzarası"];
  let soruYok = 0;
  for (const t of soruVakalari) {
    const r = await uyumSonucBul(EKRAN_KAYNAK, t, undefined);
    if (!r.soruVar && !r.aMetin) soruYok++;
  }
  ol("K2b-3 foto türünde soru ÇIKMAZ 3/3 (cevapsız tasarım tarifi geçer, Okan 9 Eki)", soruYok === 3, "basarili=" + soruYok);
  const kelimeRet = await uyumSonucBul(EKRAN_KAYNAK, "kırıldı", undefined);
  ol("K2b-4 parça kelimesi→DUR 1/1 (soru yok, ret cümlesi)",
     !!kelimeRet.aMetin && kelimeRet.aMetin.indexOf("Fotoğraftan parça") === 0 && !kelimeRet.soruVar,
     JSON.stringify({ aMetin: kelimeRet.aMetin, soruVar: kelimeRet.soruVar }));
  const soruDugme = [...(await uyumSonucBul(EKRAN_KAYNAK, "logo", undefined)).ekran.bolum.agac()]
    .filter((n) => n.id === "foto-uyum-evet" || n.id === "foto-uyum-hayir").length;
  ol("K2b-6 Evet/Hayır düğmesi DOM'da 0", soruDugme === 0, "adet=" + soruDugme);
  // K2b-C (K3c): CANLI /acik biçimi (girdi alanı YOK) — soru yine 0/3 · parça kelimesi DUR.
  let canliN = 0;
  for (const t of soruVakalari) { const r = await uyumSonucBul(EKRAN_KAYNAK, t, undefined, fotoAcik); if (!r.soruVar && !r.aMetin) canliN++; }
  ol("K2b-C3 CANLI /acik (girdi yok) foto türünde soru ÇIKMAZ 3/3", canliN === 3, "basarili=" + canliN);
  const canliRet = await uyumSonucBul(EKRAN_KAYNAK, "kırıldı", undefined, fotoAcik);
  ol("K2b-C4 CANLI /acik parça kelimesi→DUR 1/1", !!canliRet.aMetin && canliRet.aMetin.indexOf("Fotoğraftan parça") === 0 && !canliRet.soruVar,
     JSON.stringify({ aMetin: canliRet.aMetin, soruVar: canliRet.soruVar }));
  // 7) DUR vakalarında 2D/önizleme isteği 0.
  const fetchSayac = async (kaynak, uretimMetni, cevap) => {
    const V = veriYukle(VERI_KAYNAK);
    const kayit = { is: "c".repeat(32), tur: "plaket", olcu: 100 };
    const e = await ekranKos(kaynak, V, fotoAcikTam, kayit, undefined, { turnstileOto: true, zamanlayici: true, kart: "plaket" });
    const dd = () => [...e.bolum.agac()];
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta) { ta.value = uretimMetni; ta.tetikle("input"); }
    if (cevap === true) { const ev = dd().find((n) => n.id === "foto-uyum-evet"); if (ev) ev.tetikle("click"); }
    const btn = dd().find((n) => n.id === "foto-onizle-buton");
    if (btn) btn.tetikle("click");
    const on = dd().find((n) => n.id === "foto-aydinlatma-onay");
    if (on && !on.checked) { on.checked = true; on.tetikle("change"); }
    if (btn && !btn.disabled) btn.tetikle("click");
    return e.istekler.length;
  };
  const kelimeIstek = await fetchSayac(EKRAN_KAYNAK, "kırıldı", undefined);
  ol("K2b-7 DUR vakasında (uygun_degil) 2D/önizleme isteği 0",
     kelimeIstek === 0, JSON.stringify({ kelimeIstek }));
  // 9) Ret cümlesi birebir: uygun_degil'de metin TAM sayfa metnindeki ortak ret cümlesi.
  ol("K2b-9 ret cümlesi birebir (sayfa metni 'Ortak ret cümlesi' = kaynaktaki A_METIN_BIREBIR)",
     kelimeRet.aMetin === ORTAK_RET && metinRet === ORTAK_RET, JSON.stringify({ aMetin: kelimeRet.aMetin, metinRet }));
  // 10) B2 checkbox: S1'de 0 (TEK B2 yalnız ④ S3'te).
  const eS1 = await ekranKos(EKRAN_KAYNAK, veriYukle(VERI_KAYNAK), fotoAcik, null, null, { kart: "plaket" });
  const b2S1 = [...eS1.bolum.agac()].filter((n) => n.tagName === "INPUT" && n.type === "checkbox" && /^foto-b2-onay/.test(n.id));
  ol("K2b-10 B2 checkbox sayısı 1 (S1'de 0; ④ S3'te 'foto-b2-onay' = TEK)", b2S1.length === 0, "adet=" + b2S1.length);
  const icCubuk = [...eS1.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-adim")).length;
  ol("K2b-11 eski iç çubuk DOM sayısı 0 (cizAdimlar kaldırıldı)", icCubuk === 0, "adet=" + icCubuk);
  // 12) İptal→yeni tür ② dolu 1/1: ④ S3 → İptal → ① → başka kart (büst) → ② görünür + yükleme kutusu + not + uyum.
  const iptalAcik = acikGercek(veriYukle(VERI_KAYNAK), ["plaket", "bust"]);
  const iptalDene = async (kaynak) => {
    const e = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), iptalAcik,
      { is: "d".repeat(32), tur: "plaket", olcu: 100 },
      { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
      { turnstileOto: true, zamanlayici: true });
    const btn = [...e.bolum.agac()].find((n) => n.id === "foto-iptal-btn");
    if (btn) btn.tetikle("click");
    const kart = [...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-kart") && n.getAttribute("data-kart") === "bust");
    if (kart) kart.tetikle("click");
    const p2 = [...e.bolum.agac()].find((n) => n.id === "foto-pencere-2");
    const ic = p2 ? [...p2.agac()] : [];
    return { iptal: !!btn, kart: !!kart, p2Acik: !!p2 && p2.hidden === false,
      yukle: ic.some((n) => n.id === "foto-yukle-kutu"), not: ic.some((n) => n.id === "foto-not-alani"), uyum: ic.some((n) => n.id === "foto-uyum") };
  };
  const ip = await iptalDene(EKRAN_KAYNAK);
  ol("K2b-12 İptal→yeni tür ② dolu 1/1 (② görünür + yükleme kutusu + not alanı + uyum paneli DOM'da)",
     ip.iptal && ip.kart && ip.p2Acik && ip.yukle && ip.not && ip.uyum, JSON.stringify(ip));

  // ---- MUTANTLAR (her biri tek başına KIRMIZI; "uygulandı mı" denetimli) + kontrol. ----
  // M-SERIT: gösterge etiketi "Tür seç" → başka metin ⇒ S0'ın beklediği etiket kümesi bozulur.
  const mSeritCapa = '{ no: "①", ad: "Tür seç"';
  const mSeritUyg = EKRAN_KAYNAK.split(mSeritCapa).length - 1 === 1;
  const mSeritEkran = mSeritUyg ? await ekranKos(EKRAN_KAYNAK.replace(mSeritCapa, '{ no: "①", ad: "Baslangic"'), VERI, fotoAcik) : null;
  const mSeritEtiket = mSeritEkran && [...mSeritEkran.bolum.agac()].find((n) => n.classList.contains("foto-uretim-gosterge-ad") && n.textContent === "Baslangic");
  ol("M-SERIT gosterge etiketi 'Tür seç' → başka metin ⇒ gösterge KIRMIZI (S0 etiket kümesi tutmaz)", !!mSeritEtiket,
     mSeritUyg ? "bulundu=" + !!mSeritEtiket : "MUTANT_UYGULANMADI");

  // M-B2: sipBtnKapaliMi'den `!S.b2Onay ||` silinir ⇒ B2 yokken sipBtn AÇIK.
  const mB2Capa = "function sipBtnKapaliMi(nt) {\n    return !S.aydinlatmaOnay || !S.b2Onay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);\n  }";
  const mB2Yerine = "function sipBtnKapaliMi(nt) {\n    return !S.aydinlatmaOnay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null);\n  }";
  const mB2SplitCount = EKRAN_KAYNAK.split(mB2Capa).length - 1;
  const _onaySurum = veriYukle(VERI_KAYNAK).onay_surum;
  const sepetDene = async (kaynak, b2) => {
    const e = await ekranKos(kaynak, VERI, fotoAcik,
      { is: "e".repeat(32), tur: "plaket", olcu: 100, onay: _onaySurum },
      { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
      { turnstileOto: true, zamanlayici: true });
    const inp = [...e.bolum.agac()].find((n) => n.id === "foto-b2-onay");
    if (inp) { inp.checked = b2; inp.tetikle("change"); }
    const sip = [...e.bolum.agac()].find((n) => n.id === "foto-sip-btn");
    return sip ? sip.disabled : null;
  };
  const mB2 = mB2SplitCount === 1 ? await sepetDene(EKRAN_KAYNAK.split(mB2Capa).join(mB2Yerine), false) : null;
  ol("M-B2 disabled formülünden '!S.b2Onay ||' silinir ⇒ B2 yokken sipBtn AÇIK (KIRMIZI)", mB2 === false,
     mB2SplitCount === 1 ? "disabled=" + mB2 : "MUTANT_UYGULANMADI capa_sayisi=" + mB2SplitCount);

  // M-KAPI-B: kelime listesi boşaltılır ⇒ parça kelimesi geçer (DUR olmaz).
  const mKBCapa = 'var UYUM_KOKLER = ["parca", "parcas", "parcasi", "parcay", "parcayi", "parcam", "parcan", "parcalar", "parcalari", "parcalarin", "parcasin", "parcasini", "yedek", "yedegi", "yedekle", "yedekleri", "yedeklerin", "yedekten", "kirik", "kirigi", "kirdi", "kirildi", "kirilmis", "kirilir", "kiriklar", "kiriklari", "kayip", "kaybi", "kaybol", "kayboldu", "kaybolan", "kayipoldu", "kayipolmus", "mekanizma", "mekanizmasi", "mekanizmayi", "mekanizmalar", "mekanizmalari", "mekanizmada", "mekanizmadan", "disli", "dislisi", "disliyi", "disliler", "dislileri", "dislilerin", "dislide", "disliden", "kilit", "kilidi", "kilide", "kilitler", "kilitleri", "kilitlerin", "kilitten", "klips", "klipsi", "klipsler", "klipsleri", "klipslerin", "klipsten", "yuva", "yuvasi", "yuvayi", "yuvalar", "yuvalari", "yuvalarin", "yuvada", "yuvadan", "orijinal", "orijinali", "orijinale", "orijinalden", "orijinalinde", "aynisi", "aynisini", "aynilar", "aynilari", "aynisindan"];';
  const mKBSplitCount = EKRAN_KAYNAK.split(mKBCapa).length - 1;
  const mKBekran = mKBSplitCount === 1 ? await uyumSonucBul(EKRAN_KAYNAK.split(mKBCapa).join("var UYUM_KOKLER = [];"), "kırıldı", undefined) : null;
  ol("M-KAPI-B kelime listesi boşaltılır ⇒ parça kelimesi GEÇER (ret cümlesi yok = KIRMIZI)",
     !!mKBekran && !mKBekran.aMetin,
     mKBSplitCount === 1 ? JSON.stringify({ soruVar: mKBekran.soruVar, aMetin: mKBekran.aMetin }) : "MUTANT_UYGULANMADI capa_sayisi=" + mKBSplitCount);

  // M-KAPI-SIRA: kapı kontrolü 2D isteğinden SONRAYA ⇒ "kırıldı" + Evet'te POST 1 (kontrolde 0).
  const mKSCapa = "    var uyum = uyumKontrol(S.tur, S.uretimNotu);\n    if (uyum !== \"uygun\") {\n      cizUyum();\n      guncelleS1Buton();\n      return;\n    }";
  const mKSHazirlaCapa = "    var jeton = S.captchaToken1;\n    adimKoy(\"S2\", \"Fotoğrafın yükleniyor…\", false);\n    kucultGorsel(S.dosya, function (err, dataUrl) {";
  const mKSMutantUygulandi = EKRAN_KAYNAK.split(mKSCapa).length - 1 === 1 && EKRAN_KAYNAK.split(mKSHazirlaCapa).length - 1 === 1;
  const mKSsrc = mKSMutantUygulandi
    ? EKRAN_KAYNAK.split(mKSCapa).join("    // M-KAPI-SIRA mutant: gate kaldırıldı (POST'tan sonra)")
      .split(mKSHazirlaCapa).join("    var jeton = S.captchaToken1;\n    adimKoy(\"S2\", \"Fotoğrafın yükleniyor…\", false);\n    (function (cb) { cb(null, \"data:image/jpeg;base64,xxx\"); })(function (err, dataUrl) { // M-KAPI-SIRA mutant")
    : EKRAN_KAYNAK;
  const mKSHazirla = async (kaynak, uretimMetni, cevap) => {
    const V = veriYukle(VERI_KAYNAK);
    const kayit = { is: "1".repeat(32), tur: "plaket", olcu: 100, onay: _onaySurum };
    const e = await ekranKos(kaynak, V, fotoAcikTam, kayit, undefined, { turnstileOto: true, zamanlayici: true, kart: "plaket" });
    const dd = () => [...e.bolum.agac()];
    const dosyaInp = dd().find((n) => n.id === "foto-dosya");
    if (dosyaInp) { dosyaInp.files = [{ name: "x.jpg", type: "image/jpeg", size: 1024 }]; dosyaInp.tetikle("change"); }
    const ta = dd().find((n) => n.id === "foto-not");
    if (ta) { ta.value = uretimMetni; ta.tetikle("input"); }
    if (cevap === true) { const ev = dd().find((n) => n.id === "foto-uyum-evet"); if (ev) ev.tetikle("click"); }
    // Düğme zorla açılır (guncelleS1Buton uyum OK değilken kapatır; mutantta kapı kalkınca POST'a gidebilsin).
    const btn = dd().find((n) => n.id === "foto-onizle-buton");
    if (btn) { btn.disabled = false; btn.tetikle("click"); }
    return e.istekler.length;
  };
  const mKSKontrol = await mKSHazirla(EKRAN_KAYNAK, "kırıldı", true);
  const mKSistek = mKSMutantUygulandi ? await mKSHazirla(mKSsrc, "kırıldı", true) : -1;
  ol("M-KAPI-SIRA kapı kontrolü önizleme isteğinden SONRAYA ⇒ parça kabulünde POST KIRMIZI (1 istek)",
     mKSKontrol === 0 && mKSistek === 1, "kontrol=" + mKSKontrol + " mutant=" + mKSistek);

  // M-IPTAL: İptal ② çocuklarını silerse ⇒ İptal→yeni tür ② BOŞ.
  const mIPTALCapa = "      turSecimiKayitTemizle();\n      if (S.ornekBlok) ornekCiz(";
  const mIPTALUyg = EKRAN_KAYNAK.split(mIPTALCapa).length - 1 === 1;
  const mIP = mIPTALUyg ? await iptalDene(EKRAN_KAYNAK.replace(mIPTALCapa,
    "      turSecimiKayitTemizle();\n      var p2Mut = document.getElementById(\"foto-pencere-2\");\n      if (p2Mut) { while (p2Mut.firstChild) p2Mut.removeChild(p2Mut.firstChild); }\n      if (S.ornekBlok) ornekCiz(")) : null;
  ol("M-IPTAL İptal ② çocuklarını silerse ⇒ İptal→yeni tür ② BOŞ (yükleme/not/uyum yok)",
     !!mIP && !mIP.yukle && !mIP.not && !mIP.uyum, mIPTALUyg ? JSON.stringify(mIP) : "MUTANT_UYGULANMADI");

  // M-IPTAL-FULL (9 Eki onizleme-duzeltme MUTANT-2)
  // sepeteDe=true: İptal yerine B2 + "Sepete ekle" tıklanır — sepet kancasının CANLI olduğunu (kalem
  // gerçekten yazılabiliyor) kanıtlar; yoksa "sepet 0" iddiası ölü kancada da yeşil yanardı.
  const iptalFullDene2 = async (kaynak, sepeteDe) => {
    const sepet = [];
    const e2 = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), acikGercek(veriYukle(VERI_KAYNAK), ["plaket", "bust"]),
      { is: "f".repeat(32), tur: "plaket", olcu: 100, onay: veriYukle(VERI_KAYNAK).onay_surum },
      { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
      { turnstileOto: true, zamanlayici: true, sepet });
    if (sepeteDe) {
      const b2 = [...e2.bolum.agac()].find((n) => n.id === "foto-b2-onay");
      if (b2) { b2.checked = true; b2.tetikle("change"); }
      const sip = [...e2.bolum.agac()].find((n) => n.id === "foto-sip-btn");
      if (sip) sip.tetikle("click");
      return { sepetKalem: sepet.length };
    }
    const btn2 = [...e2.bolum.agac()].find((n) => n.id === "foto-iptal-btn");
    if (btn2) btn2.tetikle("click");
    const kartlar2 = [...e2.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-kart"));
    const secili2 = kartlar2.filter((k) => k.getAttribute("aria-pressed") === "true");
    const p1 = [...e2.bolum.agac()].find((n) => n.id === "foto-pencere-1");
    return { iptal: !!btn2, adim1: p1 ? p1.hidden === false : false, seciliKart: secili2.length, sepetKalem: sepet.length };
  };
  const ipCanli = await iptalFullDene2(EKRAN_KAYNAK, true);
  ol("M-IPTAL-FULL sepet kancasi CANLI (B2 + 'Sepete ekle' ⇒ sepet kalemi 1)", ipCanli.sepetKalem === 1, JSON.stringify(ipCanli));
  const ipKontrol = await iptalFullDene2(EKRAN_KAYNAK);
  ol("M-IPTAL-FULL kontrol İptal → ① + sepet 0 + tür boş (3/3)",
     ipKontrol.iptal && ipKontrol.adim1 && ipKontrol.seciliKart === 0 && ipKontrol.sepetKalem === 0,
     JSON.stringify(ipKontrol));
  // capa: iptalBtn'daki S.tur=null + S.kartKod=null iki satırı (unique — başka yerde aynısı yok);
  // mutant: bu iki satır SİLİNİR → ornekCiz'in kartVurgula'sı S.kartKod hâlâ plaket'i gördüğü için
  // plaket kartına aria-pressed="true" verir → seciliKart !== 0. Sırf S.tur = null silmek yetmez
  // (kartVurgula S.kartKod'a bakar, S.tur'a değil), o yüzden ikisini birlikte silmek şart.
  const mIFCapa = "S.tur = null;\n      S.kartKod = null;";
  const mIFCount = EKRAN_KAYNAK.split(mIFCapa).length - 1;
  const mIFMutant = mIFCount === 1 ? await iptalFullDene2(EKRAN_KAYNAK.split(mIFCapa).join("// S.tur = null; // S.kartKod = null; // MUTANT")) : null;
  ol("M-IPTAL-FULL mutant İptal sıfırlaması silinince ⇒ tür boş KIRMIZI",
     mIFCount === 1 && !!mIFMutant && mIFMutant.seciliKart !== 0,
     mIFCount === 1 ? JSON.stringify(mIFMutant) : "MUTANT_UYGULANMADI capa_sayisi=" + mIFCount);

  // M-TARIF (9 Eki onizleme-duzeltme MUTANT-1)
  // Tarif gate'ini yalnız başına test edebilmek için diğer tüm kapıları (soru=Hayır / dosya / aydinlatma /
  // captcha / tur / olcu / form doğrula) YEŞİL yaparız. Tek değişken notZorunlu: not BOŞ bırakılır →
  // kontrol disabled=true (notZorunlu=false); mutantta notZorunlu=true yapılınca disabled=false
  // (gate kalktı, düğme açıldı). K2b: soru cevapsızken uyumOK=false → düğme hep kapalı; kontrol bile
  // geçmez. "Hayır" tıklanır ki foto türünde "belirsiz" kapısı geçsin.
  const tarifDene2 = async (kaynak) => {
    const V = veriYukle(VERI_KAYNAK);
    const e3 = await ekranKos(kaynak, V, acikGercek(V, ["plaket"]),
      undefined, undefined, { turnstileOto: true, zamanlayici: true, kart: "plaket" });
    const dd3 = [...e3.bolum.agac()];
    // Soru "belirsiz" → uyumOK=false, düğme hep kapalı. foto-uyum-hayir tıklanır.
    const hyr = dd3.find((n) => n.id === "foto-uyum-hayir");
    if (hyr) hyr.tetikle("click");
    const dosyaInp3 = dd3.find((n) => n.id === "foto-dosya");
    if (dosyaInp3) { dosyaInp3.files = [{ name: "x.jpg", type: "image/jpeg", size: 1024 }]; dosyaInp3.tetikle("change"); }
    const onay3 = dd3.find((n) => n.id === "foto-aydinlatma-onay");
    if (onay3) { onay3.checked = true; onay3.tetikle("change"); }
    const btn3 = dd3.find((n) => n.id === "foto-onizle-buton");
    return btn3 ? btn3.disabled : null;
  };
  const tarifKontrol = await tarifDene2(EKRAN_KAYNAK);
  ol("M-TARIF kontrol not boş + onaylı ⇒ onizle disabled=true", tarifKontrol === true, "disabled=" + tarifKontrol);
  // capa: guncelleS1Buton içindeki notZorunlu satırı (unique); mutant: değeri true yapar →
  // not boşken bile onizle AÇIK. Sırf satırı yorum yapmak yetmez (undefined && x = undefined,
  // yine falsy → buton yine disabled; JS sessiz hata sınıfı).
  // TUR-B ①: not kosulu s1Sebep sirasinda (guncelleS1Buton TEK kaynaktan okur).
  const mTCapa = "[!notIstegeBagli(S.tur) && !((S.uretimNotu || \"\").trim()), S1_SEBEP.not],";
  const mTCount = EKRAN_KAYNAK.split(mTCapa).length - 1;
  const mTNot = mTCount === 1 ? await tarifDene2(EKRAN_KAYNAK.split(mTCapa).join("[false, S1_SEBEP.not],")) : null;
  ol("M-TARIF mutant notZorunlu=true ⇒ not boşken onizle AÇIK (KIRMIZI)",
     mTCount === 1 && mTNot === false,
     mTCount === 1 ? "disabled=" + mTNot : "MUTANT_UYGULANMADI capa_sayisi=" + mTCount);

  // M3) METİN/UI İDDİALARI (9 Eki onizleme-duzeltme · 7 iddia) — kaynak + ekrandan TÜRETİLİR, kaynakta
  // kalan yorum/sabitten ölçülmez (yorum "birebir" YOK sayılır: kod sözleşmesi metni). Ölçüm iki
  // yüzeyden: (a) kaynak metni kullanıcıya İNEN kısım (render metin); (b) ekran DOM metni.
  console.log("M3) METİN/UI — 9 Eki onizleme-duzeltme 7 metin iddiası (kaynak + DOM)");
  {
    const V = veriYukle(VERI_KAYNAK);
    const veriKaynak = fs.readFileSync(path.join(KOK, "foto-uretim-veri.js"), "utf8");
    const kaynak = EKRAN_KAYNAK;
    // (a) Kaynak metin: tüm fonksiyon/YORUM metni — "birebir" YORUMDA serbest, metinde yasak.
    // Sırf kullanıcıya inen cümleleri saymak için foto-uretim.js dosyasında KULLANICI METNİ şu:
    //   - doldurS1Onay içindeki VERI.onay.aydinlatma maddeleri (foto-uretim-veri.js)
    //   - "Nasıl olsun?" etiketi (madde 1)
    //   - "Üretim notu zorunlu" ipucu (madde 1)
    //   - yapboz dürüstlük cümlesi (madde 3)
    //   - kabartma yönü etiket (madde 6)
    //   - anahtarlık kart etiketi "Anahtarlık — yakında" (madde 4)
    // KOLAY ÖLÇÜM: dosyada 'birebir aynısı' geçen TEK kullanıcı yüzeyi (yorum/JS-string tüm metin)
    // 0 olmalı; "tam kopyası" en az 1 kez (plaket + figür aydinlatma + ana yorum).
    const birebirAynisi = (kaynak.match(/birebir aynısı değildir/g) || []).length;
    const tamKopyasi = (kaynak.match(/tam kopyası değildir/g) || []).length;
    ol("M3-1 'birebir aynısı değildir' kaynakta 0 (madde 8)", birebirAynisi === 0, "birebir=" + birebirAynisi + " tam_kopyasi=" + tamKopyasi);
    ol("M3-2 'tam kopyası değildir' kaynakta ≥1 (plaket + figür aydinlatma + ana yorum)", tamKopyasi >= 1, "tam_kopyasi=" + tamKopyasi);
    // (c) "isteğe bağlı" KULLANICI METNİNDE 0 (madde 1: etiket "Nasıl olsun?", "isteğe bağlı" SİLİNDİ).
    // DOM'dan ölçülür — kaynakta yorumlar "isteğe bağlı" içerebilir;
    // ölçümün amacı kullanıcının GÖRDÜĞÜ metin. plaket kart seçilir → ② "Nasıl olsun?" etiketi.
    const eI = await ekranKos(EKRAN_KAYNAK, V, acikGercek(V, ["plaket"]), undefined, undefined, { turnstileOto: true, zamanlayici: true, kart: "plaket" });
    const agacI = [...eI.bolum.agac()];
    const notLbl = agacI.find((n) => n.tagName === "LABEL" && n.getAttribute("for") === "foto-not");
    const notLblMetni = notLbl ? notLbl.textContent : "(yok)";
    const istegeBagliDom = (eI.bolum.textContent.match(/isteğe bağlı/g) || []).length;
    ol("M3-3 'Nasıl olsun?' etiketi 'isteğe bağlı' içermez (madde 1) — label='" + notLblMetni + "', DOM eşleşme=" + istegeBagliDom,
       notLblMetni === "Nasıl olsun?" && istegeBagliDom === 0,
       "label=" + notLblMetni + " dom=" + istegeBagliDom);
    // (d) "insan yüzünde benzerlik" kaynakta 0 (madde 5: hayvan figürü açıklamasından çıkarıldı).
    // Yorumda eski bağlam kalabilir (foto-uretim-veri.js:165'te yorum); kullanıcı metni 0 olmalı.
    const insanYuzu = (kaynak.match(/insan yüzünde benzerlik/g) || []).length;
    ol("M3-4 'insan yüzünde benzerlik' kaynakta 0 (madde 5 — hayvan kartında yasak)", insanYuzu === 0, "insan_yuzu=" + insanYuzu);
    // (e) "acik_yuksek" ham değer kodu KULLANICI METNİNDE 0 (madde 6: etiket KODDAN TÜRETİLİR).
    // KUBAR_ETIKET_MAP sözlüğünde değer kodu AYNEN kalır (köprü manifest şeması); burada ölçülen
    // select option label DOM'da (kullanıcı görür) "Açık tonlar yüksek" olmalı, "acik_yuksek" değil.
    // kaynakta option.value = "acik_yuksek" kalır; ölçüm select'in option.textContent'ındadır.
    // Bu test DOM render'ı bekler; kabartma_yon'u olan bir tür (yapboz) seçilir.
    const eY = await ekranKos(EKRAN_KAYNAK, V, acikGercek(V, ["yapboz"]), undefined, undefined, { turnstileOto: true, zamanlayici: true, kart: "yapboz" });
    // yapboz kart tıklanır → ②/③ formu çizilir; kabartma_yon option metni:
    const opts = [...eY.bolum.agac()].filter((n) => n.tagName === "OPTION" && n.parentNode && n.parentNode.id && n.parentNode.id.indexOf("kabartma_yon") >= 0);
    const optMetinleri = opts.map((o) => o.textContent);
    const hamAcikYuksek = optMetinleri.some((m) => /acik_yuksek|koyu_yuksek/.test(m));
    const acikYuksekEtiket = optMetinleri.some((m) => /Açık tonlar yüksek/.test(m));
    const koyuYuksekEtiket = optMetinleri.some((m) => /Koyu tonlar yüksek/.test(m));
    ol("M3-5 kabartma_yon option metni kullanıcıya 'Açık tonlar yüksek' / 'Koyu tonlar yüksek' (madde 6, ham kod 0)",
       !hamAcikYuksek && acikYuksekEtiket && koyuYuksekEtiket,
       "ham=" + hamAcikYuksek + " acik=" + acikYuksekEtiket + " koyu=" + koyuYuksekEtiket + " opts=" + JSON.stringify(optMetinleri));
    // (f) Yapboz dürüstlük cümlesi AYNEN (madde 3 + TUR-A ⑤ güncelleme).
    const yapbozCumlesi = "Her yapboz parçası tek renktir. Siyah, Beyaz ya da Gri seçersen tüm parçalar o renk olur; Renkli seçersen parça renkleri fotoğrafından otomatik belirlenir (en çok 4 renk).";
    const yapbozVar = veriKaynak.includes(yapbozCumlesi);
    ol("M3-6 yapboz dürüstlük cümlesi '" + yapbozCumlesi + "' VERI'de aynen (madde 3 + TUR-A ⑤)", yapbozVar, "bulundu=" + yapbozVar);
    // (g) Gizlilik cümlesi ④'te 1 (madde 7). VERI'de ONCE ve SONRA 1 kez; ekranda da 1 kez.
    // (g.1) VERI'de aydinlatma içinde "Gizlilik Politikası" geçen madde sayısı 1.
    const gizlilikMaddeSayisi = (veriKaynak.match(/Gizlilik Politikası/g) || []).length;
    ol("M3-7 'Gizlilik Politikası' VERI'de tam 1 kez (madde 7, ④ aydinlatma TEK cümle)", gizlilikMaddeSayisi === 1, "sayi=" + gizlilikMaddeSayisi);
    // (g.2) Ekran ④'te de aynı cümle 1 kez görünür.
    // ④'ü göstermek için plaket kart seçili + dosya + aydinlatma onayı + soru Hayır.
    const eG = await ekranKos(EKRAN_KAYNAK, V, acikGercek(V, ["plaket"]), undefined, undefined, { turnstileOto: true, zamanlayici: true, kart: "plaket" });
    const agacG = [...eG.bolum.agac()];
    const hyrG = agacG.find((n) => n.id === "foto-uyum-hayir"); if (hyrG) hyrG.tetikle("click");
    const dInpG = agacG.find((n) => n.id === "foto-dosya");
    if (dInpG) { dInpG.files = [{ name: "x.jpg", type: "image/jpeg", size: 1024 }]; dInpG.tetikle("change"); }
    const onayG = agacG.find((n) => n.id === "foto-aydinlatma-onay");
    if (onayG) { onayG.checked = true; onayG.tetikle("change"); }
    // ④'ü açmak için sahte önizleme → pratik değil; bunun yerine doldurS1Onay çağrısının DOM'da
    // aydinlatma detayini açıp sayalım. Madde 7 metni: "Kişisel verilerinle ilgili haklar ve başvuru
    // yolu için Gizlilik Politikası sayfasına bakabilirsin." Bu, aydinlatma <details> içinde TEK.
    const aydinlatmaBlok = agacG.find((n) => n.classList && n.classList.contains("foto-uretim-aydinlatma"));
    const aydinlatmaMetni = aydinlatmaBlok ? aydinlatmaBlok.textContent : "";
    const gizlilikEkranda = (aydinlatmaMetni.match(/Gizlilik Politikası/g) || []).length;
    ol("M3-8 ④ aydinlatma DOM'unda 'Gizlilik Politikası' tam 1 kez (madde 7)",
       gizlilikEkranda === 1, "ekran=" + gizlilikEkranda);
    // (h) Anahtarlık kartı 1 ve AÇIK (madde 4, 9 Eki TeKiN render'ı) — 4 DORT + 1 anahtarlık orneği 1 ⇒ kart
    // tıpkı diğerleri gibi AÇIK (Yakında DEVRE DIŞI davranışı YALNIZ orneği olmayan YENİ tür için).
    const eA = await ekranKos(EKRAN_KAYNAK, V, acikGercek(V, ["plaket", "figur", "yapboz", "bust", "anahtarlik"]), undefined, undefined, { turnstileOto: true, zamanlayici: true });
    const kartlarA = [...eA.bolum.agac()].filter((n) => n.classList && n.classList.contains("foto-uretim-kart"));
    const anahtarlikKart = kartlarA.find((k) => k.getAttribute("data-kart") === "anahtarlik");
    const anahtarlikVar = !!anahtarlikKart;
    const anahtarlikDisabled = anahtarlikKart ? (anahtarlikKart.disabled === true && anahtarlikKart.getAttribute("aria-disabled") === "true") : false;
    ol("M3-9 anahtarlık kartı var VE AÇIK (ornek=1, ornek=0 olsaydı Yakında DEVRE DIŞI)",
       anahtarlikVar && !anahtarlikDisabled, "var=" + anahtarlikVar + " disabled=" + anahtarlikDisabled);
  }

  // K2b-fin2: düz "aynı" → uygun; "aynısı/aynisini/aynisindan" → uygun_degil.
  const ayniDuzGecer = ["annemle aynı gün doğduk", "ayni gun batimi resmine benzer", "aynı boyutta bir tasarım istiyorum"];
  let ayniDuzGecti = 0;
  for (const tarif of ayniDuzGecer) { const r = await uyumSonucBul(EKRAN_KAYNAK, tarif, false); if (!r.soruVar && !r.aMetin) ayniDuzGecti++; }
  const aynisiDUR = ["bunun aynısı", "aynisini istiyorum", "aynisindan alabilir miyim"];
  let aynisiKaldi = 0;
  for (const tarif of aynisiDUR) { const r = await uyumSonucBul(EKRAN_KAYNAK, tarif, false); if (r.aMetin) aynisiKaldi++; }
  ol("K2b-fin2 düz 'aynı' → uygun (3/3), 'aynısı/aynisini/aynisindan' → uygun_degil (3/3) KIRMIZI",
     ayniDuzGecti === ayniDuzGecer.length && aynisiKaldi === aynisiDUR.length,
     "duz=" + ayniDuzGecti + "/" + ayniDuzGecer.length + " aynisi=" + aynisiKaldi + "/" + aynisiDUR.length);
  // K0 kontrol: yorum değişikliği ⇒ hiçbiri değişmedi.
  const k0src = EKRAN_KAYNAK.replace("/* ============== UYUM PANELİ ==============", "/* K0 kontrol yorumu ============== UYUM PANELİ ==============");
  const k0DUR = await uyumSonucBul(k0src, "kırıldı", undefined);
  ol("K-K0 kontrol yorum değişikliği ⇒ KIRMIZI kümesi []", k0src !== EKRAN_KAYNAK && k0DUR.aMetin === ORTAK_RET, "aMetin=" + k0DUR.aMetin);
}

// ================================================================ K3b — TEK KUTU, 4 PENCERE (Okan 9 Eki 01:0x + 01:4x)
// #fotoUretim içinde TEK kutu (kutu dışı öğe 0) · ① kartlar KARTLAR tablosundan (yalnız /acik türleri; bugün 5:
// anahtarlık /acik'te yok) · aynı anda TEK pencere · ① seçimsiz İleri pasif · insan + hayvan_model → figur ·
// insan'da büst yönlendirmesi · ③ fiyat 3 vaka + renk tavanı 2 + sürgü tabanı 2 + malzeme N/N · ④ tiksiz
// "Sepete ekle" kapalı · İptal → ① · REGRESYON: taze bölümde plaket DIŞI kartın İLK tıkı → istisna 0 + ② dolu +
// dürüstlük o türün. Mutantlar: M-TEKKUTU · M-TEKPENCERE · M-KART · M-INSAN · M-FORMKORUMA + kontrol.
console.log("K3b) TEK KUTU 4 PENCERE — kartlar · tek pencere · Geri/İleri · ③ fiyat/renk/sürgü/malzeme · regresyon + mutantlar");
{
  const DORT = ["plaket", "figur", "yapboz", "bust"];
  const sinifli = (kok, c) => [...kok.agac()].filter((n) => n.classList.contains(c));
  const byId = (kok, x) => (kok ? [...kok.agac()].find((n) => n.id === x) : null) || null;
  const gorunurPencere = (b) => sinifli(b, "foto-uretim-pencere").filter((p) => p.hidden !== true).length;
  // Aktif pencere gösterge üzerinden okunur (görünürlük TEKPENCERE'de ayrıca sayılır).
  const aktif = (b) => sinifli(b, "foto-uretim-gosterge-adim").filter((li) => li.classList.contains("aktif")).map((li) => li.getAttribute("data-no")).join(",");
  const durustMetni = (b) => { const d = sinifli(byId(b, "foto-pencere-2") || b, "foto-uretim-durustluk")[0]; return d && d.childNodes[0] ? d.childNodes[0].textContent : null; };
  const yeniEkran = async (kaynak, kodlar, kayit, durum, ek) => {
    const V = veriYukle(VERI_KAYNAK);
    const e = await ekranKos(kaynak, V, acikGercek(V, kodlar), kayit, durum, ek);
    e.V = V; e.ist = 0;
    e.tik = (kod) => {
      const k = sinifli(e.bolum, "foto-uretim-kart").find((n) => n.getAttribute("data-kart") === kod);
      if (!k) return false;
      try { k.tetikle("click"); } catch (er) { e.ist++; }
      return true;
    };
    e.dugme = (x) => { const n = byId(e.bolum, x); if (n) { try { n.tetikle("click"); } catch (er) { e.ist++; } } return n; };
    return e;
  };

  // A) Düzen + gezinti (gerçek veri: /acik 4 tür).
  const duzen = async (kaynak) => {
    const s = {};
    const e = await yeniEkran(kaynak, DORT);
    const b = e.bolum, V = e.V, pen = [gorunurPencere(b)];
    const govde = b.parentNode;
    const kutuDisi = () => (b.childNodes.length - 1) + (govde.childNodes.length - 1);
    const tekKutu0 = b.childNodes.length === 1 && b.childNodes[0].classList.contains("foto-uretim-kutu") && kutuDisi() === 0;
    const p1 = byId(b, "foto-pencere-1"), kartlar = sinifli(b, "foto-uretim-kart");
    const kartIci = new Set(kartlar.flatMap((k) => [k, ...k.agac()]));
    const p1Disi = p1 ? [...p1.agac()].filter((n) => !kartIci.has(n) && !n.classList.contains("foto-uretim-kartlar")).length : -1;
    s.KART = JSON.stringify(kartlar.map((k) => k.getAttribute("data-kart"))) === JSON.stringify(["insan", "hayvan_model", "plaket", "bust", "yapboz"]) &&
      p1Disi === 0 && (p1 ? [...p1.agac()] : []).filter((n) => n.tagName === "INPUT" && n.type === "file").length === 0 &&
      kartlar.every((k) => [...k.agac()].some((n) => n.tagName === "IMG") && sinifli(k, "foto-uretim-kart-ad").length === 1);
    const ileri = byId(b, "foto-ileri"), geri = byId(b, "foto-geri");
    s.ILERI = aktif(b) === "1" && !!ileri && ileri.disabled === true && !!geri && geri.hidden === true;
    e.tik("insan"); pen.push(gorunurPencere(b));
    const insanAktif = aktif(b), insanD = durustMetni(b), insanY = !!byId(b, "foto-bust-yonlendir");
    e.tik("plaket"); pen.push(gorunurPencere(b));
    e.tik("hayvan_model"); pen.push(gorunurPencere(b));
    const hayvanD = durustMetni(b), hayvanY = !!byId(b, "foto-bust-yonlendir");
    const figurD = V.turBul("figur").durustluk;
    s.INSAN = insanAktif === "2" && insanD === figurD && hayvanD === figurD && V.turBul("plaket").durustluk !== figurD;
    e.tik("insan");
    e.dugme("foto-bust-yonlendir"); pen.push(gorunurPencere(b));
    s.YONLENDIRME = insanY && !hayvanY && aktif(b) === "1";
    // Gezinti (canlı biçimli /acik): büst → ② (dosya yok: İleri pasif) → dosya + parça tarifi "kırıldı" (kapı
    // uygun_degil: pasif + ret cümlesi) → tarif temiz (açık) → ③ → ④ (İleri gizli) → Geri ③.
    e.tik("bust"); pen.push(gorunurPencere(b));
    const pasifDosyasiz = ileri.disabled === true;
    const dos = byId(b, "foto-dosya");
    if (dos) { dos.files = [{ name: "a.jpg", type: "image/jpeg", size: 2048 }]; dos.tetikle("change"); }
    const ta = byId(b, "foto-not");
    if (ta) { ta.value = "kırıldı"; ta.tetikle("input"); }
    const ret = sinifli(b, "foto-uretim-uyum-metin")[0];
    const pasifSoru = ileri.disabled === true && !!ret && ret.textContent === ORTAK_RET;
    if (ta) { ta.value = "deniz manzarası"; ta.tetikle("input"); }
    e.dugme("foto-uyum-hayir");
    const acik2 = ileri.disabled === false;
    e.dugme("foto-ileri"); pen.push(gorunurPencere(b)); const a3 = aktif(b);
    e.dugme("foto-ileri"); pen.push(gorunurPencere(b)); const a4 = aktif(b), gizli4 = ileri.hidden === true, geri4 = geri.hidden === false;
    e.dugme("foto-geri"); pen.push(gorunurPencere(b)); const a3b = aktif(b);
    s.GEZINTI = pasifDosyasiz && pasifSoru && acik2 && a3 === "3" && a4 === "4" && gizli4 && geri4 && a3b === "3";
    s.TEKPENCERE = pen.length === 9 && pen.every((n) => n === 1);
    s.TEKKUTU = tekKutu0 && kutuDisi() === 0;
    s.ISTISNA_YOK = e.ist === 0;
    Object.defineProperty(s, "iz", { value: { pen, insanAktif, a3, a4, a3b, kutuDisi: kutuDisi(), p1Disi, kart: kartlar.map((k) => k.getAttribute("data-kart")) }, enumerable: false });
    return s;
  };

  // B) ③ Renk, boyut ve malzeme — canlı fiyat 3 vaka · renk tavanı 2 · sürgü tabanı 2 · malzeme N/N.
  const ucuncu = async (kaynak) => {
    const s = {};
    const surgu = (b) => [...b.agac()].find((n) => n.tagName === "INPUT" && n.type === "range");
    const kaydir = (b, i) => { const g = surgu(b); if (g) { g.value = String(i); g.tetikle("input"); } };
    const fiyat = (b) => (byId(b, "foto-canli-fiyat") || { textContent: null }).textContent;
    const surguYazi = (b) => (sinifli(b, "foto-uretim-surgu-fiyat")[0] || { textContent: null }).textContent;
    // Okan 9 Eki: renk TEK seçim (Siyah · Beyaz · Gri · Renkli (+%15)); Renkli yalnız fotoğraftan renk çıkınca.
    const kutular = (b) => [...b.agac()].filter((n) => n.tagName === "INPUT" && n.name === "foto-renk");
    const renkSec = (b, r) => { const k = kutular(b).find((n) => n.value === r); if (k && !k.disabled) { k.checked = true; k.tetikle("change"); } };
    const kartlar = (b) => [...b.agac()].filter((n) => n.tagName === "BUTTON" && n.getAttribute && n.getAttribute("data-malzeme"));
    const kartSec = (b, m) => { const k = kartlar(b).find((n) => n.getAttribute("data-malzeme") === m); if (k) { k.tetikle("click"); } };
    const kartMetni = (n) => [...n.agac()].map((x) => x.textContent || "").filter(Boolean);
    const eP = await yeniEkran(kaynak, ["plaket"], null, null, { kart: "plaket" });
    const P = eP.bolum, mmP = eP.V.olcuSecenekleri("plaket");
    kaydir(P, 0); const tabanP = surguYazi(P);
    kaydir(P, mmP.indexOf(30)); const f30 = fiyat(P);
    kaydir(P, mmP.indexOf(100)); const f100 = fiyat(P);
    renkSec(P, "Siyah"); const f100r3 = fiyat(P);
    kartSec(P, "PETG"); const f100petg = fiyat(P);
    kartSec(P, "PLA");
    s.FIYAT = f30 === "Fiyat: 600 TL" && f100 === "Fiyat: 1.000 TL" && f100r3 === "Fiyat: 1.000 TL" && f100petg === "Fiyat: 1.300 TL" &&
      fiyat(P) === "Fiyat: 1.000 TL";
    const eB = await yeniEkran(kaynak, ["bust"], null, null, { kart: "bust" });
    const B = eB.bolum;
    kaydir(B, 0); const tabanB = surguYazi(B);
    // RENK: fotoğrafsız ekranda tam 3 ana renk (Renkli YOK), varsayılan Beyaz, tek seçim; renk adedi kutusu/ek renk metni YOK.
    const renkDegerleri = (b) => kutular(b).map((n) => n.value);
    const pDeg = renkDegerleri(P), bDeg = renkDegerleri(B);
    const varsayilanB = (kutular(B).find((n) => n.checked) || {}).value;
    s.RENK = JSON.stringify(pDeg) === '["Siyah","Beyaz","Gri"]' && JSON.stringify(bDeg) === '["Siyah","Beyaz","Gri"]' &&
      kutular(B).every((n) => n.type === "radio") && varsayilanB === "Beyaz" &&
      kutular(P).filter((n) => n.checked).length === 1 && (kutular(P).find((n) => n.checked) || {}).value === "Siyah" &&
      !/\bek renk|Renkler \(1/.test(kaynak);
    s.TABAN = tabanP === "10 mm → 600 TL" && tabanB === "60 mm → 600 TL" && !!surgu(P) && surgu(P).min === "0";
    const eY = await yeniEkran(kaynak, ["yapboz"], null, null, { kart: "yapboz" });
    const Y = eY.bolum;
    kaydir(Y, eY.V.olcuSecenekleri("yapboz").indexOf(100));
    const yOnce = fiyat(Y);
    // MALZEME (2. resim): HER türde iki kart PLA/PETG (ASA/ABS YOK); kart = sıcaklık / ad / kullanım / o malzemeyle
    // canlı fiyat; varsayılan PLA seçili; PETG tıkı fiyatı ×1,30 yapar.
    const kartKod = (b) => kartlar(b).map((n) => n.getAttribute("data-malzeme"));
    const yMalzeme = kartKod(Y), bMalzeme = kartKod(B), pMalzeme = kartKod(P);
    const yKart = kartlar(Y).map(kartMetni);
    const ySecili = (kartlar(Y).find((n) => n.getAttribute("aria-checked") === "true") || { getAttribute: () => null }).getAttribute("data-malzeme");
    kartSec(Y, "PETG");
    const yPetgSecili = (kartlar(Y).find((n) => n.getAttribute("aria-checked") === "true") || { getAttribute: () => null }).getAttribute("data-malzeme");
    const pGrup = byId(P, "foto-malzeme");
    s.MALZEME = JSON.stringify(yMalzeme) === '["PLA","PETG"]' && JSON.stringify(bMalzeme) === '["PLA","PETG"]' &&
      JSON.stringify(pMalzeme) === '["PLA","PETG"]' && !!pGrup && pGrup.hidden === false &&
      JSON.stringify(yKart) === JSON.stringify([["~55-60°C", "PLA", "Ev içi", "1.000 TL"], ["~70-75°C", "PETG", "Dış mekân / genel amaçlı", "1.300 TL"]]) &&
      ySecili === "PLA" && yPetgSecili === "PETG" && yOnce === "Fiyat: 1.000 TL" && fiyat(Y) === "Fiyat: 1.300 TL" &&
      ![...Y.agac(), ...B.agac(), ...P.agac()].some((n) => /^(ASA|ABS)$/.test(n.value || n.textContent || ""));
    Object.defineProperty(s, "iz", { value: { f30, f100, f100r3, f100petg, tabanP, tabanB, pDeg, bDeg, varsayilanB, yMalzeme, bMalzeme, pMalzeme, yKart, ySecili, yPetgSecili, yOnce, ySon: fiyat(Y) }, enumerable: false });
    return s;
  };

  // C) ④ sepet kapısı + İptal → ①.
  const dorduncu = async (kaynak) => {
    const s = {};
    const hazir = { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" };
    const e = await yeniEkran(kaynak, ["plaket"], { is: "f".repeat(32), tur: "plaket", olcu: 100 }, hazir, { turnstileOto: true, zamanlayici: true });
    const b = e.bolum;
    const sip = () => byId(b, "foto-sip-btn");
    const tiksiz = !!sip() && sip().disabled === true && aktif(b) === "4";
    const b2 = byId(b, "foto-b2-onay");
    if (b2) { b2.checked = true; b2.tetikle("change"); }
    const yalnizB2 = !!sip() && sip().disabled === true;   // aydınlatma onayı yok (oturum onayı eski/yok)
    s.SEPET = tiksiz && yalnizB2;
    e.dugme("foto-iptal-btn");
    const ileri = byId(b, "foto-ileri");
    s.IPTAL = aktif(b) === "1" && sinifli(b, "foto-uretim-kart").filter((k) => k.classList.contains("secili")).length === 0 &&
      !!ileri && ileri.disabled === true && !sip() && gorunurPencere(b) === 1;
    return s;
  };

  // D) REGRESYON: taze bölüm, plaket DIŞI kartın İLK tıkı → istisna 0 + ② dolu + dürüstlük o türün.
  const regresyon = async (kaynak) => {
    let tamam = 0;
    const iz = [];
    for (const kod of ["insan", "hayvan_model", "bust", "yapboz"]) {
      const e = await yeniEkran(kaynak, DORT);
      const bulundu = e.tik(kod);
      const p2 = byId(e.bolum, "foto-pencere-2");
      const dolu = !!p2 && p2.hidden !== true && !!byId(p2, "foto-yukle-kutu") && !!byId(p2, "foto-not-alani") && !!byId(p2, "foto-uyum");
      const tur = kod === "insan" || kod === "hayvan_model" ? "figur" : kod;
      const d = durustMetni(e.bolum);
      if (bulundu && e.ist === 0 && dolu && d === e.V.turBul(tur).durustluk) tamam++;
      iz.push({ kod, ist: e.ist, dolu });
    }
    const s = { REGRESYON: tamam === 4 };
    Object.defineProperty(s, "iz", { value: iz, enumerable: false });
    return s;
  };

  // E) ① kart sayısı = /acik: anahtarlık /acik'te + VERI'de sayılan örneği 1 (9 Eki TeKiN) → 5 kart
  // (4 DORT + anahtarlık, tıpkı diğerleri AÇIK). Yalnız plaket açıkken 1 kart. "Yakında" kart 0 (örnek
  // 0 olsaydı 1 DEVRE DIŞI olurdu; madde 4: artık YALNIZ örneği olmayan YENİ tür için).
  const acikSayisi = async (kaynak) => {
    const V = veriYukle(VERI_KAYNAK);
    const ac = acikGercek(V, DORT);
    ac.turler.push({ kod: "anahtarlik", ad: "Anahtarlık", aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 60, fiyat_kurus: 60000 }] });
    const e1 = await ekranKos(kaynak, V, ac);
    const e2 = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), acikGercek(V, ["plaket"]));
    const n1 = sinifli(e1.bolum, "foto-uretim-kart").length, n2 = sinifli(e2.bolum, "foto-uretim-kart").length;
    const devreDisiSayisi = sinifli(e1.bolum, "foto-uretim-kart").filter((k) => k.getAttribute("aria-disabled") === "true").length;
    // e1'de 6 kart (insan + hayvan_model + plaket + bust + yapboz + anahtarlık = 6; anahtarlık /acik'te
    // VAR, ornek=1, AÇIK). e2'de yalnız plaket → 1 kart, devre dışı 0. Yakında kart 0 (hepsi ornekli).
    const s = { ACIK_SAYISI: n1 === 6 && n2 === 1 && devreDisiSayisi === 0 };
    Object.defineProperty(s, "iz", { value: { n1, n2, devreDisiSayisi }, enumerable: false });
    return s;
  };

  const hepsi = async (kaynak) => ({ ...(await duzen(kaynak)), ...(await ucuncu(kaynak)), ...(await dorduncu(kaynak)),
    ...(await regresyon(kaynak)), ...(await acikSayisi(kaynak)) });
  const d0 = await duzen(EKRAN_KAYNAK), u0 = await ucuncu(EKRAN_KAYNAK), c0 = await dorduncu(EKRAN_KAYNAK);
  const r0 = await regresyon(EKRAN_KAYNAK), a0 = await acikSayisi(EKRAN_KAYNAK);
  console.log("  ℹ K3b sayilar: kutu_disi_oge=" + d0.iz.kutuDisi + " gorunur_pencere(9 adim)=" + JSON.stringify(d0.iz.pen) +
    " kart=" + d0.iz.kart.length + " p1_kart_disi_oge=" + d0.iz.p1Disi);
  ol("K3b-1 #fotoUretim cocuk sayisi 1 (tek kutu) + kutu disi oge 0 (bastan sona; govdede bolum disi oge 0)", d0.TEKKUTU, JSON.stringify([d0, d0.iz]));
  ol("K3b-2 ① kart = KARTLAR ∩ /acik: 5/5 (insan · hayvan_model · plaket · bust · yapboz); ① icinde dosya girdisi 0, kart disi oge 0", d0.KART, JSON.stringify(d0.iz));
  ol("K3b-3 ① kart sayisi /acik'e bagli: 4 DORT + anahtarlık orneği 1 ⇒ 5 kart (AÇIK), Yakında 0; yalnız plaket açıkken 1 kart", a0.ACIK_SAYISI, JSON.stringify(a0));
  ol("K3b-4 ayni anda gorunen pencere 1 (9 adimin hepsinde)", d0.TEKPENCERE, JSON.stringify(d0.iz.pen));
  ol("K3b-5 ① secimsiz 'İleri' pasif + 'Geri' gizli", d0.ILERI, JSON.stringify(d0));
  ol("K3b-6 insan + hayvan_model ikisi de tur figur secer (② durustluk figur'un) ve ②'ye gecer", d0.INSAN, JSON.stringify(d0.iz));
  ol("K3b-7 insan kartinda büst yönlendirmesi 1/1 (hayvan_model'de 0); tik ①'e döner", d0.YONLENDIRME, JSON.stringify(d0));
  ol("K3b-8 gezinti: ② dosyasiz ve parca tarifinde (ret cumlesi) İleri pasif, temiz tarifle acik → ③ → ④ (İleri gizli, Geri var) → Geri ③", d0.GEZINTI, JSON.stringify(d0.iz));
  ol("K3b-9 ③ canli fiyat: 30 mm → 600 TL (taban) · 100 mm → 1.000 TL · Siyah (ana renk) → 1.000 TL · PETG → 1.300 TL · PLA'ya donus 1.000 TL", u0.FIYAT, JSON.stringify(u0.iz));
  ol("K3b-10 ③ renk: fotografsiz ekranda tam 3 ana renk radyo (Siyah,Beyaz,Gri; Renkli YOK), varsayilan Beyaz, tek secim; ek renk metni 0", u0.RENK, JSON.stringify(u0.iz));
  ol("K3b-11 ③ surgu tabani 2 vaka: plaket ilk deger '10 mm → 600 TL' · bust '60 mm → 600 TL'", u0.TABAN, JSON.stringify(u0.iz));
  ol("K3b-12 ③ malzeme kartlari HER turde [PLA,PETG] (yapboz · bust · plaket; ASA/ABS 0); kart metni 2. resim AYNEN + canli fiyat 1.000/1.300 TL; varsayilan PLA; PETG tiki ×1,30", u0.MALZEME, JSON.stringify(u0.iz));
  ol("K3b-13 ④ tiksiz 'Sepete ekle' disabled (yalniz B2 ile de kapali)", c0.SEPET, JSON.stringify(c0));
  ol("K3b-14 İptal → ① (secili kart 0, İleri pasif, sepet paneli yok, tek pencere)", c0.IPTAL, JSON.stringify(c0));
  ol("K3b-15 REGRESYON taze bolum, plaket DISI kartin ilk tiki → istisna 0 + ② dolu + durustluk o turun (4/4)", r0.REGRESYON, JSON.stringify(r0.iz));
  ol("K3b-16 kart tiklarinda istisna 0", d0.ISTISNA_YOK, JSON.stringify(d0));
  const ESKI = ["foto-uretim-serit", "foto-uretim-vitrin", "foto-uretim-isik", "foto-uretim-galeri-kucuk", "foto-uretim-buyuk",
    "foto-uretim-fiyat", "foto-uretim-yakinda", "foto-uretim-polaroid", "vitrinGuncelle", "isikAc", "S.fiyatEl", "S.olcuAltEl", "YER_TUTUCU", "'dan itibaren"];
  const eskiVar = ESKI.filter((x) => EKRAN_KAYNAK.includes(x));
  ol("K3b-17 eski serit/vitrin/lightbox/izgara sinif ve kod adlari kaynakta 0", eskiVar.length === 0, JSON.stringify(eskiVar));
  ol("K3b-18 mobil: ≤640 px kartlar 2 sutun + gosterge 2x2 kurali kaynakta (375 px tarayici olcumu mimarda)",
     /@media \(max-width:640px\)\{"[\s\S]{0,160}?\.foto-uretim-kartlar\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)[\s\S]{0,160}?\.foto-uretim-gosterge\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/.test(EKRAN_KAYNAK), "");
  // MUTANTLAR — her biri yalnız kendi koşucusuyla; beklenen kırmızı kümesi TAM (null/no-op YASAK: çapa tam 1 kez).
  const K3B_MUT = [
    ["M-TEKKUTU kutu disina oge eklendi", "    bolum.appendChild(kutu);\n    pencereGit(1);",
     "    bolum.appendChild(kutu);\n    bolum.appendChild(el(\"p\", \"foto-uretim-ayrinti\", \"\"));\n    pencereGit(1);", duzen, ["TEKKUTU"]],
    ["M-TEKPENCERE ① penceresi hep gorunur (iki pencere)", "S.pencereler[i].hidden = (i + 1) !== n;",
     "S.pencereler[i].hidden = (i + 1) !== n && i !== 0;", duzen, ["TEKPENCERE"]],
    ["M-KART KARTLAR'dan hayvan_model satiri silindi", "    { kod: \"hayvan_model\", tur: \"figur\", alt: \"hayvan_model\", ad: \"Hayvan ve model figürü\",\n      ret: \"Figür için tek hayvan, araç ya da oyuncağın net fotoğrafı gerekir.\" },\n",
     "", duzen, ["KART", "INSAN"]],
    ["M-INSAN insan karti figur yerine plaket secer", "{ kod: \"insan\", tur: \"figur\", alt: \"insan\"",
     "{ kod: \"insan\", tur: \"plaket\", alt: \"insan\"", duzen, ["INSAN"]],
    ["M-FORMKORUMA kart seciciden form-cizilmedi korumasi kalkti", "      if (S.alanOlcu) {\n        doldurS1Olcu();",
     "      {\n        doldurS1Olcu();", regresyon, ["REGRESYON"]],
    // Okan 9 Eki: Renkli fotoğrafsız akışta görünürse RENK KIRMIZI · PETG kartı fiyatı çarpansız okursa MALZEME KIRMIZI.
    ["M-RENKLI-FOTOSUZ Renkli fotografsiz akista gorunur", "return !!F.renkliSecilebilir(kod) && !!(S.fotoRenkleri && S.fotoRenkleri.length);",
     "return true;", ucuncu, ["RENK"]],
    ["M-MALZEME-KART kart fiyati malzemesiz", "var sec = { renkli: renkliMi(), malzeme: kod };", "var sec = { renkli: renkliMi() };", ucuncu, ["MALZEME"]],
    ["K3b-MK KONTROL (yorum)", "  function kartVurgula() {", "  // kontrol\n  function kartVurgula() {", hepsi, []],
  ];
  for (const [ad, capa, yerine, kosucu, olmeli] of K3B_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu (mutant uygulandi)", false, "capa kayip/coklu: " + capa.slice(0, 60)); continue; }
    const m = await kosucu(EKRAN_KAYNAK.replace(capa, yerine));
    const kirmizi = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kirmizi) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kirmizi));
  }
}

// ---------------------------------------------------------------- TUR-B (10 Eki) ① sebep cümlesi + hak · ② makine anahtarı
// ① "Önizleme oluştur" KAPALIYKEN altında TEK cümle (ilk eksik koşul, sıra: not · foto · onay · doğrulama · hak · program);
// hepsi tamken düğme AÇIK + cümle GİZLİ. "Bugün N/<sınır>": N sunucu yanıtından, sınır VERI'den (3 YAZILMAZ).
const SEBEP = {
  not: "Önce \"Nasıl olsun?\" kısmına kısa bir not yaz.",
  foto: "Önce fotoğrafını yükle.",
  onay: "Aydınlatma metnini okuyup onay kutusunu işaretle.",
  dogrulama: "Güvenlik doğrulaması bekleniyor.",
  hak: "Bugünkü önizleme hakkın doldu; yarın yenilenir.",
  program: "Önizleme şu an kapalı; biraz sonra yeniden dene.",
};
async function sebepEkrani(kaynak, a) {
  const V = veriYukle(VERI_KAYNAK);
  const acik = { acik: true, turler: [{ kod: "plaket", ad: V.turBul("plaket").ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri("plaket").map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus("plaket", mm) })) }] };
  const e = await ekranKos(kaynak, V, acik, null, { asama: "bekliyor" }, { kart: "plaket", turnstileOto: !a.dogrulamaYok,
    zamanlayici: true, gorselSahte: true, postKod: a.postKod, postYanit: a.postYanit });
  const id = (x) => [...e.bolum.agac()].find((n) => n.id === x) || null;
  const f = id("foto-dosya");
  if (f && !a.fotoYok) { f.files = [{ name: "yuz.jpg", type: "image/jpeg", size: 4096 }]; f.tetikle("change"); }
  const t = id("foto-not");
  if (t && !a.notYok) { t.value = "deniz manzarası"; t.tetikle("input"); }
  const hy = id("foto-uyum-hayir");
  if (hy) { hy.tetikle("click"); }
  const o = id("foto-aydinlatma-onay");
  if (o && !a.onayYok) { o.checked = true; o.tetikle("change"); }
  if (a.postKod) {
    const b0 = id("foto-onizle-buton");
    if (b0) { b0.tetikle("click"); }
    for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
  }
  const b = id("foto-onizle-buton"), sb = id("foto-onizle-sebep"), hk = id("foto-onizle-hak");
  return { kapali: !!b && b.disabled === true, acik: !!b && b.disabled === false,
           sebep: sb && sb.hidden !== true ? sb.textContent : "", gizli: !!sb && sb.hidden === true && sb.textContent === "",
           hak: hk ? hk.textContent : "", istek: e.istekler.length };
}
async function sebepSenaryolar(kaynak) {
  const s = {}, iz = {};
  const tek = async (ad, a, beklenen) => {
    const r = await sebepEkrani(kaynak, a);
    iz[ad] = r;
    return r.kapali && r.sebep === beklenen;
  };
  s.V1_NOT = await tek("not", { notYok: true }, SEBEP.not);
  s.V1_FOTO = await tek("foto", { fotoYok: true }, SEBEP.foto);
  s.V1_ONAY = await tek("onay", { onayYok: true }, SEBEP.onay);
  s.V1_DOGRULAMA = await tek("dogrulama", { dogrulamaYok: true }, SEBEP.dogrulama);
  s.V1_HAK = await tek("hak", { postKod: 429, postYanit: { hata: "onizleme-siniri", sinir: VERI.sinir_ziyaretci_24s } }, SEBEP.hak);
  s.V1_PROGRAM = await tek("program", { postKod: 503, postYanit: { hata: "kapali" } }, SEBEP.program);
  const tam = await sebepEkrani(kaynak, {});
  iz.tam = tam;
  s.V1_TAM = tam.acik && tam.gizli && tam.sebep === "";
  // SIRA: birden çok koşul eksikken İLK eksik yazılır (tek eksik vakaları sırayı ölçemez).
  const hepsi = await sebepEkrani(kaynak, { notYok: true, fotoYok: true, onayYok: true, dogrulamaYok: true });
  const notlu = await sebepEkrani(kaynak, { fotoYok: true, onayYok: true, dogrulamaYok: true });
  iz.sira = [hepsi.sebep, notlu.sebep];
  s.V1_SIRA = hepsi.kapali && hepsi.sebep === SEBEP.not && notlu.kapali && notlu.sebep === SEBEP.foto;
  // V2: 429 sonrası S1'de "Bugün 0/<sınır>" görünür; yanıt gelmeden sayı UYDURULMAZ (günlük sınır cümlesi).
  s.V2_HAK = iz.hak.hak === "Bugün 0/" + VERI.sinir_ziyaretci_24s + " önizleme hakkın kaldı." &&
    tam.hak === "Günde en çok " + VERI.sinir_ziyaretci_24s + " önizleme hakkın var.";
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TB) TUR-B ① SEBEP CÜMLESİ + Bugün N/" + VERI.sinir_ziyaretci_24s);
{
  const s = await sebepSenaryolar(EKRAN_KAYNAK);
  ol("V1 not boş -> \"" + SEBEP.not + "\"", s.V1_NOT, JSON.stringify(s.iz.not));
  ol("V1 fotoğraf yok -> \"" + SEBEP.foto + "\"", s.V1_FOTO, JSON.stringify(s.iz.foto));
  ol("V1 aydınlatma onayı yok -> \"" + SEBEP.onay + "\"", s.V1_ONAY, JSON.stringify(s.iz.onay));
  ol("V1 doğrulama yok -> \"" + SEBEP.dogrulama + "\"", s.V1_DOGRULAMA, JSON.stringify(s.iz.dogrulama));
  ol("V1 429 onizleme-siniri -> \"" + SEBEP.hak + "\"", s.V1_HAK, JSON.stringify(s.iz.hak));
  ol("V1 503 kapali -> \"" + SEBEP.program + "\"", s.V1_PROGRAM, JSON.stringify(s.iz.program));
  ol("V1 hepsi tam -> düğme AÇIK, sebep cümlesi 0 (gizli)", s.V1_TAM, JSON.stringify(s.iz.tam));
  ol("V1 sıra: çok eksikte İLK eksik (not; not varken foto)", s.V1_SIRA, JSON.stringify(s.iz.sira));
  ol("V2 \"Bugün 0/" + VERI.sinir_ziyaretci_24s + "\" 429 sonrası görünür; yanıtsız sayı uydurulmaz", s.V2_HAK, JSON.stringify([s.iz.hak.hak, s.iz.tam.hak]));
  const TB_MUT = [
    ["M1 sebep sırası ters", "for (var i = 0; i < sira.length; i++) { if (sira[i][0]) return sira[i][1]; }",
     "for (var i = sira.length - 1; i >= 0; i--) { if (sira[i][0]) return sira[i][1]; }", ["V1_SIRA"]],
    ["TB-K0 KONTROL (yorum)", "  function s1Sebep() {", "  // kontrol\n  function s1Sebep() {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of TB_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa.slice(0, 60)); continue; }
    const m = await sebepSenaryolar(EKRAN_KAYNAK.replace(capa, yerine));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ② GEÇERLİ X-Onizleme-Makine (ONIZLEME=1) ziyaretçi/IP sayacına YAZMAZ, sınırla REDDEDİLMEZ; geçersiz/boş = sayılır.
async function makineSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur(), { ONIZLEME: "1", ONIZLEME_MAKINE_ANAHTARI: "makine-test-anahtari" });
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  const cag = async (ip, anahtar) => {
    const h = { "CF-Connecting-IP": ip, "Content-Type": "application/json" };
    if (anahtar !== undefined) { h["X-Onizleme-Makine"] = anahtar; }
    const r = await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop/foto/onizleme", { method: "POST", headers: h,
      body: JSON.stringify(onizlemeGovde()) }), e2, new URL("https://pruvo3d.com/api/shop/foto/onizleme"), "/foto/onizleme", null);
    return r.status;
  };
  const sayac = async (ip) => ((await k.d1.prepare("SELECT COUNT(*) AS n FROM foto_isler WHERE ziyaretci = ?")
    .bind(await fm.ziyaretciOzeti(e2, ip)).first()) || {}).n;
  const s = {}, iz = {};
  const once = await sayac("10.0.3.1");
  const k3 = [];
  for (let i = 0; i < 5; i++) { k3.push(await cag("10.0.3.1", "makine-test-anahtari")); }
  const sonra = await sayac("10.0.3.1");
  iz.V3 = { k3, once, sonra };
  s.V3 = k3.every((x) => x === 200) && once === 0 && sonra === 0;
  const sinir = VERI.sinir_ziyaretci_24s;
  const k4 = [];
  for (let i = 0; i <= sinir; i++) { k4.push(await cag("10.0.4.1", "yanlis-anahtar")); }
  const bos = await cag("10.0.4.1", "");
  const n4 = await sayac("10.0.4.1");
  iz.V4 = { k4, bos, n4 };
  s.V4 = k4.slice(0, sinir).every((x) => x === 200) && k4[sinir] === 429 && bos === 429 && n4 === sinir;
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TB) TUR-B ② MAKINE ANAHTARI ziyaretci sayacina yazilmaz");
{
  const s = await makineSenaryolar(foto);
  ol("V3 gecerli makine anahtarli 5 ardisik istek -> hepsi 200, IP sayaci 0 -> 0", s.V3, JSON.stringify(s.iz.V3));
  ol("V4 gecersiz/bos anahtar -> sayilir, sinirda (" + VERI.sinir_ziyaretci_24s + ") 429", s.V4, JSON.stringify(s.iz.V4));
  const MK_MUT = [
    ["M2 anahtar kontrolu atlandi (her baslik muaf)", "  return onizlemeMakinesiMi(request, env);\n", "  return true;\n", ["V4"]],
    ["M3 muafiyet kaldirildi", "  if (!request.headers.get(\"X-Onizleme-Makine\")) { return false; }\n", "  return false;\n", ["V3"]],
    ["MK-K0 KONTROL (yorum)", "async function makineIstegi(request, env) {\n", "// kontrol\nasync function makineIstegi(request, env) {\n", []],
  ];
  for (const [ad, capa, yerine, olmeli] of MK_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await makineSenaryolar(fm);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-B2 (10 Eki) Okan 01:3x "büstte not zorunlu olmasın"
// Büst: boş not düğmeyi KAPATMAZ, sebep listesinde "not" YOK, ② cümlesi "İsteğe bağlı…" (ArTisT); diğer türlerde AYNEN.
// ④ ayrı uyarı satırı YOK: ① sebep cümlesi (not sırada İLK) aynı bilgiyi düğmenin altında verir. Ters ilk durum KAPALI.
const B2_NOT_ESKI = "Üretim notu zorunlu; boşsa önizleme oluşturulamaz.";
const B2_NOT_BUST = "İsteğe bağlı: kısa bir not ekleyebilirsin.";
async function b2Ekran(kaynak, kod, kart) {
  const V = veriYukle(VERI_KAYNAK);
  const acik = { acik: true, turler: [{ kod, ad: V.turBul(kod).ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri(kod).map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus(kod, mm) })) }] };
  const e = await ekranKos(kaynak, V, acik, null, { asama: "bekliyor" }, { kart: kart || kod, turnstileOto: true,
    zamanlayici: true, gorselSahte: true });
  const id = (x) => [...e.bolum.agac()].find((n) => n.id === x) || null;
  const ters0 = id("foto-param-ters");
  const ters = ters0 ? { aria: ters0.getAttribute("aria-checked"), metin: ters0.textContent } : null;
  const f = id("foto-dosya");
  if (f) { f.files = [{ name: "yuz.jpg", type: "image/jpeg", size: 4096 }]; f.tetikle("change"); }
  const hy = id("foto-uyum-hayir");
  if (hy) { hy.tetikle("click"); }
  const o = id("foto-aydinlatma-onay");
  if (o) { o.checked = true; o.tetikle("change"); }
  const na = id("foto-not-alani");
  const notMetin = na ? [...na.agac()].filter((n) => n.tagName === "P").map((n) => n.textContent) : [];
  const b = id("foto-onizle-buton"), sb = id("foto-onizle-sebep");
  return { acik: !!b && b.disabled === false, kapali: !!b && b.disabled === true,
           sebep: sb && sb.hidden !== true ? sb.textContent : "", notMetin, ters, notBos: !(id("foto-not") || {}).value };
}
async function b2Senaryolar(kaynak) {
  const s = {}, iz = {};
  const bu = await b2Ekran(kaynak, "bust"), fi = await b2Ekran(kaynak, "figur", "insan");
  iz.bust = bu; iz.figur = fi;
  s.V1 = bu.notBos && bu.acik && bu.sebep === "";
  s.V2 = fi.notBos && fi.kapali && fi.sebep === SEBEP.not;
  s.V5 = bu.notMetin.includes(B2_NOT_BUST) && !bu.notMetin.includes(B2_NOT_ESKI) &&
    fi.notMetin.includes(B2_NOT_ESKI) && !fi.notMetin.includes(B2_NOT_BUST);
  s.V6 = VERI.turBul("bust").form.ters.varsayilan === false && !!bu.ters && bu.ters.aria === "false" && bu.ters.metin === "Kapalı";
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("B2) TUR-B2 büstte not İSTEĞE BAĞLI (istemci) + Ters ilk durum");
{
  const s = await b2Senaryolar(EKRAN_KAYNAK);
  ol("V1 büst + foto + onay + doğrulama, not BOŞ -> düğme AÇIK, sebep satırı yok", s.V1, JSON.stringify(s.iz.bust));
  ol("V2 figür aynı durumda not BOŞ -> KAPALI + \"" + SEBEP.not + "\"", s.V2, JSON.stringify(s.iz.figur));
  ol("V5 ② cümlesi: büst \"" + B2_NOT_BUST + "\" · figür eski cümle", s.V5, JSON.stringify([s.iz.bust.notMetin, s.iz.figur.notMetin]));
  ol("V6 Ters varsayılan false + ③ düğmesi aria-checked=false \"Kapalı\" başlar", s.V6, JSON.stringify(s.iz.bust.ters));
  const B2_MUT = [
    ["M1 büst muafiyeti istemciden kaldırıldı", "  var NOT_ISTEGE_BAGLI_TURLER = [\"bust\"];", "  var NOT_ISTEGE_BAGLI_TURLER = [];", ["V1", "V5"]],
    ["M1b muafiyet yalnız sebep sırasından silindi", "[!notIstegeBagli(S.tur) && !((S.uretimNotu", "[!((S.uretimNotu", ["V1"]],
    ["M2 muafiyet tüm türlere yayıldı", "function notIstegeBagli(kod) { return NOT_ISTEGE_BAGLI_TURLER.indexOf(kod) >= 0; }",
     "function notIstegeBagli(kod) { return true; }", ["V2", "V5"]],
    ["M5 ② cümlesi türden bağımsız eski", "kap.appendChild(el(\"p\", \"foto-uretim-ayrinti\", notIstegeBagli(S.tur) ?",
     "kap.appendChild(el(\"p\", \"foto-uretim-ayrinti\", false ?", ["V5"]],
    ["M6 Ters ilk durum açık", "S.parametre[a] = sema.varsayilan === true;", "S.parametre[a] = true;", ["V6"]],
    ["B2-K0 KONTROL (yorum)", "  function s1Sebep() {", "  // kontrol\n  function s1Sebep() {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of B2_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa.slice(0, 60)); continue; }
    const m = await b2Senaryolar(EKRAN_KAYNAK.replace(capa, yerine));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// Sunucu: büst (üreteç önizleme ucu) boş/yok not -> 400 DEĞİL (not "" sayılır); dolu notun doğrulaması AYNEN.
// Sağlayıcı/kredi SAHTE (P), üreteç kolu sağlayıcıya hiç gitmez. Plaket boş not: ÖLÇÜM satırı (sunucuda boş-not reddi
// bu turdan önce de YOKTU — uretimNotuDogrula boşu "" sayar; yeni ret kuralı bu turda EKLENMEDİ).
async function b2SunucuSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('bust', 1, 'x'), ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (govde) => {
    const h = { "CF-Connecting-IP": "10.0.9." + (++ipNo), "Content-Type": "application/json" };
    const r = await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop/foto/onizleme", { method: "POST", headers: h,
      body: JSON.stringify(govde) }), e2, new URL("https://pruvo3d.com/api/shop/foto/onizleme"), "/foto/onizleme", null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, hata: v && v.hata };
  };
  const bust = (ek) => onizlemeGovde({ tur: "bust", parametreler: { rolyef_yuksekligi_mm: 3, ters: false },
    secim: { govde_malzeme: "PLA" }, ...(ek || {}) });
  const s = {}, iz = {};
  // Test VERI'sinde büst örneği sayılmıyor (turHazir "gercek-ornek"): örnek şartı bu vakanın ekseni DEĞİL,
  // yalnız bu senaryo süresince bellekte 1 sayılır, finally'de geri alınır.
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "bust" ? 1 : asilOrnek(kod));
  try {
  iz.bos = await cag(bust({ not: "" }));
  iz.bosluk = await cag(bust({ not: "   " }));
  iz.yok = await cag(bust());
  iz.dolu = await cag(bust({ not: "deniz manzarası" }));
  iz.tel = await cag(bust({ not: "ara 0555 123 45 67" }));
  iz.plaketBos = await cag(onizlemeGovde({ not: "" }));
  } finally { VERI.ornekSayisi = asilOrnek; }
  s.V3 = [iz.bos, iz.bosluk, iz.yok, iz.dolu].every((x) => x.kod === 200) && iz.tel.kod === 400 && iz.tel.hata === "not-kisisel-veri";
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("B2) TUR-B2 sunucu büst boş not");
{
  const s = await b2SunucuSenaryolar(foto);
  ol("V3 sunucu: büst boş/boşluk/yok not -> 200 (400 DEĞİL); dolu not 200, telefonlu not 400 not-kisisel-veri", s.V3, JSON.stringify(s.iz));
  console.log("  ÖLÇÜM V4 plaket boş not -> " + JSON.stringify(s.iz.plaketBos) + " (sunucuda boş-not reddi yok; kapı istemcide)");
  const B2S_MUT = [
    ["M3 sunucu boş notu reddeder (büst muafiyeti yok)", "  if (x === undefined || x === null) { return { ok: true, deger: \"\" }; }\n",
     "  if (x === undefined || x === null || (typeof x === \"string\" && !x.trim())) { return { ok: false, hata: \"not-bos\" }; }\n", ["V3"]],
    ["B2S-K0 KONTROL (yorum)", "export function uretimNotuDogrula(x) {\n", "// kontrol\nexport function uretimNotuDogrula(x) {\n", []],
  ];
  for (const [ad, capa, yerine, olmeli] of B2S_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await b2SunucuSenaryolar(fm);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-A (10 Eki) metin maddeleri ④⑤⑥⑦⑩ — görünür metin (yapı/fiyat/köprü DOKUNMAZ)
// ④ ArTisT etiketi bekleyen (METİN KAYNAĞI'nda Türkçe karşılık YOK; UYDURMA yasak).
// ⑤ Yapboz ② dürüstlük cümlesi (ArTisT 10 Eki, birebir).
// ⑥ Plaket + yapboz ③ alan açıklamaları (ArTisT 10 Eki, yalnız o türde; büst cümleleri değişmez).
// ⑦ Büst kart açıklaması "(ters/iki renk opsiyonel)" → "(ters opsiyonel)".
// ⑩ "kabartma yorumu" ifadesi kaldır (veri + ekran; deterministik-olmayan dalın yedek metni + aydınlatma).
const A_YAPBOZ_DURUSTLUK = "Her yapboz parçası tek renktir. Siyah, Beyaz ya da Gri seçersen tüm parçalar o renk olur; Renkli seçersen parça renkleri fotoğrafından otomatik belirlenir (en çok 4 renk).";
const A_PLAKET_RENK = "Siyah, Beyaz ya da Gri seçersen plaket tek renk olur; Renkli seçersen renkler fotoğrafından otomatik seçilir (en çok 4 renk).";
const A_PLAKET_OLCU = "Plaketin en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.";
const A_YAPBOZ_RENK = "Siyah, Beyaz ya da Gri seçersen tüm parçalar o renk olur; Renkli seçersen parça renkleri fotoğrafından otomatik belirlenir (en çok 4 renk).";
const A_YAPBOZ_OLCU = "Yapbozun en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.";
const A_MALZEME_PAYLASIK = "PLA ev içi kullanım içindir; PETG dış mekân ve genel amaçlı kullanım için daha yüksek sıcaklığa dayanır (+%30).";
const A_YAPBOZ_SATIR = "Yapbozun dikey kaç parçaya bölüneceği.";
const A_YAPBOZ_SUTUN = "Yapbozun yatay kaç parçaya bölüneceği.";
const A_YAPBOZ_KABARTMA = "Fotoğrafın hangi tonlarının daha çok kabaracağını belirler.";
const A_BUST_ACIKLAMA_YENI = "Fotoğraftan kabartma büst/madalyon (ters opsiyonel).";
const A_BUST_ACIKLAMA_ESKI = "Fotoğraftan kabartma büst/madalyon (ters/iki renk opsiyonel).";
const A_BUST_RENK = "Siyah, Beyaz ya da Gri seçersen büst tek renk olur; Renkli seçersen renkler fotoğrafından otomatik seçilir (büstte en çok 2 renk).";
const A_BUST_OLCU = "Büstün en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.";

async function aEkranAgac(kaynak, veriKaynak, kod) {
  const V = veriYukle(veriKaynak);
  const e = await ekranKos(kaynak, V, { acik: true, turler: [{ kod, ad: V.turBul(kod).ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri(kod).map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus(kod, mm) })) }] }, null, null, { kart: kod });
  return [...e.bolum.agac()];
}
async function aOlc(kaynakE, kaynakV) {
  const ddY = await aEkranAgac(kaynakE, kaynakV, "yapboz");
  const p2y = ddY.find((n) => n.id === "foto-pencere-2");
  const v1 = p2y ? [...p2y.agac()].filter((n) => n.tagName === "P" && n.textContent === A_YAPBOZ_DURUSTLUK).length === 1 : false;
  const ddP = await aEkranAgac(kaynakE, kaynakV, "plaket");
  const p3p = ddP.find((n) => n.id === "foto-pencere-3");
  const ddP3 = p3p ? [...p3p.agac()] : [];
  const v2 = [A_PLAKET_RENK, A_PLAKET_OLCU, A_MALZEME_PAYLASIK].every((m) =>
    ddP3.filter((n) => n.tagName === "P" && n.textContent === m).length === 1);
  const p3y = ddY.find((n) => n.id === "foto-pencere-3");
  const ddY3p = p3y ? [...p3y.agac()] : [];
  const v3 = [A_YAPBOZ_RENK, A_YAPBOZ_OLCU, A_MALZEME_PAYLASIK, A_YAPBOZ_SATIR, A_YAPBOZ_SUTUN, A_YAPBOZ_KABARTMA]
    .every((m) => ddY3p.filter((n) => n.tagName === "P" && n.textContent === m).length === 1);
  const v4 = ![A_BUST_RENK, A_BUST_OLCU].some((m) =>
    ddP3.some((n) => n.tagName === "P" && n.textContent === m) ||
    ddY3p.some((n) => n.tagName === "P" && n.textContent === m));
  const v5 = kaynakV.includes(A_BUST_ACIKLAMA_YENI) && !kaynakV.includes(A_BUST_ACIKLAMA_ESKI);
  const v6 = !kaynakE.includes("kabartma yorumu") && !kaynakV.includes("kabartma yorumu");
  return { V1: v1, V2: v2, V3: v3, V4: v4, V5: v5, V6: v6 };
}
console.log("A) TUR-A metin maddeleri ④⑤⑥⑦⑩");
{
  const s0 = await aOlc(EKRAN_KAYNAK, VERI_KAYNAK);
  ol("V1 yapboz ② dürüstlük cümlesi birebir (TUR-A ⑤)", s0.V1, "");
  ol("V2 plaket ③'te 3 cümle (renk/ölçü/malzeme) AYNEN; malzeme = büstün malzeme AYNEN (TUR-A ⑥)", s0.V2, "");
  ol("V3 yapboz ③'te 6 cümle (renk/ölçü/malzeme + satır/sütun/kabartma yönü) AYNEN (TUR-A ⑥)", s0.V3, "");
  ol("V4 plaket/yapboz ③'te büst-specific renk/ölçü cümleleri YOK (TUR-A ⑥ yalnız o türde)", s0.V4, "");
  ol("V5 büst kart aciklama '(ters opsiyonel)' VAR, '(ters/iki renk opsiyonel)' YOK (TUR-A ⑦)", s0.V5, "");
  ol("V6 'kabartma yorumu' EKRAN + VERI'de 0 (TUR-A ⑩)", s0.V6, "");

  // ---- MUTANTLAR (her biri tek başına KIRMIZI) ----
  const A_MUT = [
    ["M1 yapboz dürüstlük eski", VERI_KAYNAK, A_YAPBOZ_DURUSTLUK,
     "Her yapboz parçası tek renktir; renkler seçtiğin seçeneğe göre belirlenir.", ["V1"]],
    ["M2 plaket alan_aciklamalari silindi", VERI_KAYNAK,
     '        alan_aciklamalari: {\n          renk: "Siyah, Beyaz ya da Gri seçersen plaket tek renk',
     '        eski_aciklama_yok: {\n          renk: "Siyah, Beyaz ya da Gri seçersen plaket tek renk', ["V2"]],
    ["M3 yapboz alan_aciklamalari silindi", VERI_KAYNAK,
     '        alan_aciklamalari: {\n          renk: "Siyah, Beyaz ya da Gri seçersen tüm parçalar',
     '        eski_aciklama_yok: {\n          renk: "Siyah, Beyaz ya da Gri seçersen tüm parçalar', ["V3"]],
    ["M4 yapboz form satir aciklama silindi", VERI_KAYNAK,
     '            aciklama: "Yapbozun dikey kaç parçaya bölüneceği.",\n',
     '', ["V3"]],
    ["M5 yapboz form sutun aciklama silindi", VERI_KAYNAK,
     '            aciklama: "Yapbozun yatay kaç parçaya bölüneceği.",\n',
     '', ["V3"]],
    ["M6 yapboz form kabartma_yon aciklama silindi", VERI_KAYNAK,
     '            aciklama: "Fotoğrafın hangi tonlarının daha çok kabaracağını belirler.",\n',
     '', ["V3"]],
    ["M7 büst kart aciklama eski geri geldi", VERI_KAYNAK, A_BUST_ACIKLAMA_YENI, A_BUST_ACIKLAMA_ESKI, ["V5"]],
    ["M8 VERI'de 'kabartma yorumu olarak' geri geldi", VERI_KAYNAK,
     'olarak üretilir; tam kopyası değildir, küçük yazı ve ince ',
     'kabartma yorumu olarak üretilir; tam kopyası değildir, küçük yazı ve ince ', ["V6"]],
    ["M9 ekranda 'kabartma yorumu olur' geri geldi", EKRAN_KAYNAK,
     "ürün bunun seçtiğin renk sayısında olur; tam kopyası değildir.",
     "ürün bunun seçtiğin renk sayısında (1–4) kabartma yorumu olur; tam kopyası değildir.", ["V6"]],
    ["A-K0 KONTROL (yorum)", VERI_KAYNAK, "    // TÜRLER — açılışta TEK tür: kabartma PLAKET", "    // TÜRLER — açılışta TEK tür: kabartma PLAKET (kontrol)", []],
  ];
  for (const [ad, kaynak, capa, yerine, olmeli] of A_MUT) {
    if (kaynak.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa.slice(0, 60)); continue; }
    const mutant = kaynak.replace(capa, yerine);
    const kayEkr = (kaynak === EKRAN_KAYNAK) ? mutant : EKRAN_KAYNAK;
    const kayVer = (kaynak === VERI_KAYNAK) ? mutant : VERI_KAYNAK;
    const sM = await aOlc(kayEkr, kayVer);
    const kir = Object.keys(sM).filter((x) => sM[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-C2a (10 Eki) anahtarlık ÇEŞİT — sunucu, figür kapısı KAPALI
// Çeşidin kalıcı yeri D1 foto_isler.cesit; müşteri ucu kapalı çeşidi `cesit-yakinda` ile AÇIKÇA reddeder.
const C2A_YAZI = { satirlar: ["Ayşe"], yazi_tipi: "script", hizalama: "orta", genislik_mm: 45,
  anahtarlik_kulak_konum: "sol-ust", kontur_tasma_mm: 1.5 };
async function c2aSunucuSenaryolar(fm, veriYama) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik', 1, 'x'), ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (yol, govde) => {
    const h = { "CF-Connecting-IP": "10.0.7." + (++ipNo), "Content-Type": "application/json" };
    const u = "https://pruvo3d.com/api/shop" + yol;
    const r = await fm.fotoUclari(new Request(u, govde ? { method: "POST", headers: h, body: JSON.stringify(govde) } : { headers: h }),
      e2, new URL(u), yol.split("?")[0], null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const ah = (ek) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: 45, gorsel: undefined, parametreler: C2A_YAZI,
    secim: { plaka_renk: "Beyaz", yazi_renk: "Siyah", govde_malzeme: "PLA" }, ...(ek || {}) });
  const satir = async (is) => (await k.d1.prepare("SELECT cesit, asama FROM foto_isler WHERE is_no = ?").bind(is || "").first());
  const s = {}, iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" ? 1 : asilOrnek(kod));
  const geri = typeof veriYama === "function" ? veriYama() : null;
  const proto0 = protoSayisi();
  try {
    iz.figur = await cag("/foto/onizleme", ah({ cesit: "figur", gorsel: GORSEL, parametreler: undefined }));
    iz.xyz = await cag("/foto/onizleme", ah({ cesit: "xyz" }));
    iz.plaketCesit = await cag("/foto/onizleme", onizlemeGovde({ cesit: "yazi" }));
    iz.dogrudan = fm.girdiGovdeDogrula("anahtarlik", { cesit: "xyz", parametreler: C2A_YAZI });
    iz.yok = await cag("/foto/onizleme", ah());
    iz.yazi = await cag("/foto/onizleme", ah({ cesit: "yazi" }));
    iz.yokSatir = await satir(iz.yok.v && iz.yok.v.is);
    iz.yaziSatir = await satir(iz.yazi.v && iz.yazi.v.is);
    iz.yokDurum = await cag("/foto/durum?is=" + (iz.yok.v && iz.yok.v.is));
    // ESKİ SATIR (göç öncesi yazılmış: cesit sütunu INSERT'te YOK -> DEFAULT '') = yazı kolu.
    const eski = "c2a0" + "e".repeat(28);
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, 'anahtarlik', 45, 'z', ?, 'uretec-onizleme')")
      .bind(eski, new Date().toISOString()).run();
    iz.eskiSatir = await satir(eski);
    iz.eskiDurum = await cag("/foto/durum?is=" + eski);
    iz.proto = protoSayisi() - proto0;
  } finally { VERI.ornekSayisi = asilOrnek; if (geri) { geri(); } }
  s.V1 = iz.figur.kod === 400 && iz.figur.v && iz.figur.v.hata === "cesit-yakinda";
  s.V2 = iz.xyz.kod === 400 && iz.xyz.v && iz.xyz.v.hata === "gecersiz-cesit" && iz.plaketCesit.kod === 400 &&
    iz.plaketCesit.v && iz.plaketCesit.v.hata === "gecersiz-cesit" && iz.dogrudan === "gecersiz-cesit";
  s.V3 = iz.yok.kod === 200 && iz.yazi.kod === 200 && !!iz.yokSatir && iz.yokSatir.asama === "uretec-onizleme" &&
    iz.yokDurum.kod === 200 && iz.yokDurum.v && iz.yokDurum.v.asama === "bekliyor" && iz.proto === 0;
  s.V4 = !!iz.yokSatir && iz.yokSatir.cesit === "yazi" && !!iz.yaziSatir && iz.yaziSatir.cesit === "yazi";
  s.V8 = !!iz.eskiSatir && iz.eskiSatir.cesit === "" && iz.eskiDurum.kod === 200 && iz.eskiDurum.v &&
    iz.eskiDurum.v.asama === "bekliyor" && iz.proto === 0;
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("C2a) TUR-C2a anahtarlık çeşit — sunucu (figür kapısı KAPALI)");
{
  ol("C2a VERI: anahtarlık çeşitleri [yazi,figur], varsayılan yazi, figür acik:false",
     JSON.stringify(VERI.cesitler.anahtarlik.secenekler.map((x) => [x.kod, x.acik])) === '[["yazi",true],["figur",false]]' &&
     VERI.cesitler.anahtarlik.varsayilan === "yazi" && VERI.cesitCoz("anahtarlik") === "yazi" && VERI.cesitCoz("plaket") === "",
     JSON.stringify(VERI.cesitler));
  const s = await c2aSunucuSenaryolar(foto);
  ol("V1 cesit=figur (acik:false) -> 400 cesit-yakinda", s.V1, JSON.stringify(s.iz.figur));
  ol("V2 cesit=xyz -> 400 gecersiz-cesit (+ çeşitsiz plakette dolu cesit + girdiGovdeDogrula doğrudan)", s.V2,
     JSON.stringify([s.iz.xyz, s.iz.plaketCesit, s.iz.dogrudan]));
  ol("V3 cesit yok/'yazi' -> 200 uretec kolu, durum 'bekliyor', sağlayıcı çağrısı 0", s.V3,
     JSON.stringify([s.iz.yok, s.iz.yazi, s.iz.yokDurum, s.iz.proto]));
  ol("V4 D1 foto_isler.cesit yazıldı ('yazi')", s.V4, JSON.stringify([s.iz.yokSatir, s.iz.yaziSatir]));
  ol("V8 eski satır (cesit '') -> yazı kolu (durum 'bekliyor')", s.V8, JSON.stringify([s.iz.eskiSatir, s.iz.eskiDurum]));
  const C2A_MUT = [
    ["M1 kapı kontrolü düştü", "  if (!VERI.cesitAcik(turKod, cz)) { return \"cesit-yakinda\"; }\n", "", null, ["V1"]],
    // M2 kapalı küme açıldı (bellek kopyası: VERI.cesitCoz küme dışını da kabul eder).
    ["M2 kapalı küme açıldı (VERI.cesitCoz bellek)", null, null, () => {
      const a = VERI.cesitCoz;
      VERI.cesitCoz = (kod, c) => (c === undefined ? a(kod, c) : c);
      return () => { VERI.cesitCoz = a; };
    }, ["V2"]],
    ["C2a-K0 KONTROL (yorum)", "export function cesitKapisi(turKod, c) {\n", "// kontrol\nexport function cesitKapisi(turKod, c) {\n", null, []],
  ];
  for (const [ad, capa, yerine, yama, olmeli] of C2A_MUT) {
    const fm = capa === null ? foto : await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await c2aSunucuSenaryolar(fm, yama);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

await new Promise((c) => setTimeout(c, 0));
ol("ASENKRON temiz kaynakta (EKRAN_KAYNAK) yakalanmamis istisna 0",
   ASENKRON_ISTISNA.filter((x) => x.temiz).length === 0, JSON.stringify(ASENKRON_ISTISNA.filter((x) => x.temiz).slice(0, 3)));

kopru.kapat();
await Promise.allSettled(ctx.bekleyen);
console.log(kirmizi ? "\n❌ " + kirmizi + " iddia KIRMIZI" : "\n✅ HEPSI GECTI");
process.exit(kirmizi ? 1 : 0);
