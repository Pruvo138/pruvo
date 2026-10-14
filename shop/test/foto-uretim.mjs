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
 *   I URETIM ZINCIRI    : 'bekliyor' siparis uretime GIRMEZ; 'odendi' -> 'onay-bekliyor' -> (Okan onayi,
 *                         SO bolumu) -> model -> analiz -> 4 renk -> 3MF+GLB ozel kovada -> panelde
 *                         indirilebilir; kredi 46
 *   SO OKAN ONAYI       : odenen saglayici kalemi onaysiz saglayiciya GITMEZ; siparis-onayla (okan_onay:true)
 *                         -> build-baslat; 70 sa -> elle; 48/66 sa TEK hatirlatma; ornek-uret bayraksiz 403
 *   OE OKAN E-POSTASI   : acilis / 48-66 sa hatirlatma / 70 sa sure doldu Okan'a (YALNIZ BILDIRIM_EPOSTA) TEK
 *                         e-posta; hata -> isaret artmaz, sonraki tur yeniden; OE-M1..M3 KIRMIZI, OE-MK hicbiri
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
 *   ES                  : bolumde ① kart kanıt etiketi render/baski kartlarında ÇİZİLMEZ (Okan 14 Eki 18:5x
 *                         "bunları sil"); "Örnek görsel (bilgisayar çizimi)" / "basılmış ürün" metinleri
 *                         ① kart bölgesinde 0; "Örnek yakında" (ornek-yok) + "yakında" (devre dışı) etiketleri
 *                         AYNEN durur; ② ornek_notu AYNEN, "gerçek fotoğraf" 0 (ES-M1 ekran mutantı KIRMIZI)
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
 *   OA-M1/OA-M2: okan_onay bayrak kontrolu silinir -> V2+V3 OLUR · indirme kosulu tum islere acilir
 *               -> V5 OLUR; OA-MK (yalniz yorum) -> HICBIRI OLMEZ
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
    async head(k) { const x = m.get(k); return x ? { httpMetadata: x.httpMetadata } : null; },
    async delete(k) { m.delete(k); },
    async list() { return { objects: [] }; },
  };
}

// ---------------------------------------------------------------- sahte ag (saglayici + digerleri)

const TABAN = "https://saglayici.test/openapi";
const PNG = Uint8Array.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ...new Array(64).fill(7)]);
// ④ GRI: saglayicinin alfa kucuk resmi (konsept PNG'den AYIRT edilebilir bayt).
const GRI_PNG = Uint8Array.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ...new Array(64).fill(128)]);
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
  // OKAN ONAY E-POSTASI: sahte Resend ucuna giden HER deneme {to, subject, html, kod}; epostaKod != 2xx -> hata.
  eposta: [], epostaKod: 200,
  // 6 MODEL V6-4: /v1/prototype istek govdeleri (figur alt turu istemi `prompt` olculur).
  protoGovde: [],
  protoDurum: new Map(),
  // ONARIM: analiz sonucu modele gore (onarilmis+dokulu model ayri sonuc verebilir).
  analizOnarim: null, analizModel: new Map(), onarimKod: 0,
  // A) WARNING+METRIK KUSUR: warning durumunda override metrik (figur ornegi).
  //    { degenerate_faces: 316227 } → status 'warning' + metrik kusurlu.
  //    { noMetrics: true } → status 'warning' + metrics alani YOK.
  analizMetrik: null,
  // ④ GRI: image-to-3d istek govdeleri · gorev yoklama sayaci · sonuc ('SUCCEEDED'|'FAILED') · POST hata kodu ·
  // alfa kucuk resmi yok (gorselsiz bitti).
  griGovde: [], griDurum: new Map(), griSonuc: "SUCCEEDED", griKod: 0, griAlfaYok: false,
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
    if (yontem === "POST" && /^\/tur-onek\/tur-(plaket|figur)\/v1\/prototype$/.test(yol)) {
      const g = JSON.parse(init.body);
      P.protoGovde.push(g);
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
    // ④ GRI: dokusuz image-to-3d (taban + /v1/image-to-3d; tur oneki YOK). 2. yoklamada biter, 5 kredi.
    if (yontem === "POST" && yol === "/v1/image-to-3d") {
      P.griGovde.push(JSON.parse(init.body));
      if (P.griKod) { return yanit({ message: "x" }, P.griKod); }
      const id = yeniId(); P.griDurum.set(id, 0); return yanit({ result: id });
    }
    if ((m = /^\/v1\/image-to-3d\/(.+)$/.exec(yol))) {
      const n = (P.griDurum.get(m[1]) || 0) + 1; P.griDurum.set(m[1], n);
      if (n < 2) { return yanit({ id: m[1], status: "IN_PROGRESS", progress: 50 }); }
      if (P.griSonuc === "FAILED") { return yanit({ id: m[1], status: "FAILED", consumed_credits: 0, task_error: { message: "x" } }); }
      return yanit({ id: m[1], status: "SUCCEEDED", consumed_credits: 5, thumbnail_url: "https://dosya.test/kucuk.png?Expires=1",
                     ...(P.griAlfaYok ? {} : { alpha_thumbnail_url: "https://dosya.test/gri.png?Expires=1" }),
                     model_urls: { glb: "https://dosya.test/gri-model.glb?Expires=1" } });
    }
    return yanit({ message: "bilinmeyen" }, 404);
  }
  if (u.startsWith("https://dosya.test/gri.png")) { return new Response(GRI_PNG, { headers: { "Content-Type": "image/png", "Content-Length": String(GRI_PNG.length) } }); }
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
  if (u.startsWith("https://resend.test/emails")) {
    const g = JSON.parse(init.body);
    P.eposta.push({ to: g.to, subject: g.subject, html: g.html, kod: P.epostaKod });
    return P.epostaKod < 300 ? yanit({ id: "e-" + P.eposta.length }) : yanit({ message: "sahte hata" }, P.epostaKod);
  }
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
/** Okan onay e-postasi ortami (sahte Resend; alici YALNIZ BILDIRIM_EPOSTA olmali). */
const OKAN_EPOSTA = "okan-bildirim@ornek.test";
const OKAN_EPOSTA_ENV = { RESEND_API_KEY: "re-sahte", RESEND_URL: "https://resend.test", BILDIRIM_EPOSTA: OKAN_EPOSTA };

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

/** 'onay-bekliyor' satirlarin HEPSINI panel onay ucuyla (okan_onay:true) onaylar; onaylanan sayisi. */
async function okanOnaylar(fm, e, db) {
  const r = await db.prepare("SELECT siparis_no, kalem FROM foto_uretim WHERE asama = 'onay-bekliyor'").all();
  let n = 0;
  for (const x of (r.results || [])) {
    const y = await fm.panelSiparisOnayla(new Request("https://pruvo3d.com/x", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ siparis_no: x.siparis_no, kalem: x.kalem, okan_onay: true }) }), e, Date.now(), null);
    if (y.status === 200) { n++; }
  }
  return n;
}
/** Bir cron turu; onay bekleyen satir onaylandiysa tur AYNEN tekrarlanir (onay oncesi tek tura esdeger). */
async function turVeOnay(fm, e, db) {
  await fm.fotoUretimTuru(e, Date.now(), null);
  if (await okanOnaylar(fm, e, db)) { await fm.fotoUretimTuru(e, Date.now(), null); }
}

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
    // 11 Eki: anahtarlık–figür render kaydı eklendi -> sayılan örnek 2 (yazı + figür çeşidi).
    VERI.turler.some((t) => t.kod === "anahtarlik") && VERI.ornekSayisi("anahtarlik") === 2 &&
    !VERI.turler.some((t) => t.kod === "magnet");
  ol("P1 veri dosyasinda plaket + figur + anahtarlik kaydi VAR, anahtarligin sayilan ornegi 2 (yazi + figur), magnet kaydi 0",
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
  ol("B3 acik:true; plaket olculeri FORMULDEN (100 mm = 100000 kurus, her olcu max(60000, mm x 1000), 60..300 adim 10)",
     a2.v && a2.v.acik === true && !!pl && pl.olculer.length === 25 &&
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
    const y = await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik_yazi", acik: true }, basliklar: YONET });
    const a = await istek(env, "/foto/acik");
    const acikKodlar = ((a.v && a.v.turler) || []).map((t) => t.kod);
    const k = await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik_yazi", acik: false }, basliklar: YONET });
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
  // tur; P7b figur = kayitli ama acilis anahtari YOK). 6 MODEL (10 Eki): modelli turde (anahtarlik/figur) kapali
  // modelin reddi MODEL KAPISINDAN gelir: 400 `model-kapali` (tur-kapali'dan once). P7-M orneksiz 503'u model
  // ACIKKEN olcer (anahtarlik_yazi panelden acilir/kapatilir).
  const r7b = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "figur", olcu_mm: 100 }) });
  ol("P7 D kolu ornekli tur anahtarlik (panel anahtari yok) -> 400 model-kapali (uretc onizlemeli yol)",
     r6.kod === 400 && r6.v.hata === "model-kapali", JSON.stringify(r6));
  ol("P7b M kolu kapali tur figur (acilis anahtari yok) -> 400 model-kapali", r7b.kod === 400 && r7b.v.hata === "model-kapali", JSON.stringify(r7b));
  const p7m = await ornekSartiKapali(async () => {
    await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik_yazi", acik: true }, basliklar: YONET });
    const r = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "anahtarlik", olcu_mm: 100 }) });
    await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik_yazi", acik: false }, basliklar: YONET });
    return r;
  });
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
const cronHam = async () => modul.scheduled({ cron: "*/5 * * * *", scheduledTime: Date.now() }, env, ctx);
// OKAN ONAYI (13 Eki 21:0x): odenen saglayici kalemi 'onay-bekliyor'da bekler; zincirin geri kalanini olcen
// senaryolarda onay panel ucuyla verilir ve AYNI tur yeniden kosar (tur sayisi onay oncesiyle esdeger).
// Onaysiz davranis SO bolumunde (S1..S6) ham turla olculur.
const cron = async () => { await cronHam(); if (await okanOnaylar(foto, env, d1)) { await cronHam(); } };
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
  // turHazir gecer, acikAnahtari VAR, olcu araliktaysa (30..300) 200/odeme; aralik disinda (305) 400 gecersiz-olcu.
  // Mutant (ornek sarti kapali -> ornekSayisi=0) reddi 400 foto-kapali'ya CEVIRIR.
  const isB = "b".repeat(32);
  await d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'anahtarlik', 305, 'z', ?, 'onizleme-hazir', 'gorev-eski-002', ?)")
    .bind(isB, simdiIso, simdiIso).run();
  const q1b = async () => {
    await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik_yazi", acik: true }, basliklar: YONET });
    const r = await istek(env, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: isB, olcu_mm: 305, adet: 1, renkler: ["Beyaz"] }] } });
    await istek(env, "/yonet/foto-acik", { govde: { tur: "anahtarlik_yazi", acik: false }, basliklar: YONET });
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
  const um = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: musteriIs, okan_onay: true }, basliklar: YONET });
  const hazirDegil = await d1.prepare("SELECT is_no FROM foto_isler WHERE ziyaretci = ? AND asama = 'onizleme' AND gorev != '' LIMIT 1")
    .bind(foto.ORNEK_ZIYARETCI).first();
  const uh = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: hazirDegil && hazirDegil.is_no, okan_onay: true }, basliklar: YONET });
  ol("O8 musteri isi ornek-uret'te 404 · hazir olmayan ornek 409", um.kod === 404 && uh.kod === 409, um.kod + "/" + uh.kod);
  const u1 = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: ornekIs, okan_onay: true }, basliklar: YONET });
  const u2 = await istek(env, "/yonet/foto/ornek-uret", { govde: { is: ornekIs, okan_onay: true }, basliklar: YONET });
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
  // O12b ALT TUR (6 model prova): panel ornek ucu `alt_tur`u musteri ucuyla AYNI cozer -> saglayici istemi
  // (insan/pet/model); alt tursuz istekte prompt alani YOK; gecersiz alt tur 400 + saglayiciya istek 0.
  const altIstem = async (alt) => {
    const p0 = P.protoGovde.length, c0 = protoSayisi();
    const r = await istek(env, "/yonet/foto/ornek-onizleme", { govde: { gorsel: GORSEL, tur: "figur",
      olcu_mm: VERI.olcuBaslangic("figur"), ...(alt === undefined ? {} : { alt_tur: alt }) }, basliklar: YONET });
    const g = P.protoGovde.slice(p0);
    return { kod: r.kod, hata: r.v && r.v.hata, cagri: protoSayisi() - c0,
      prompt: g.length === 1 ? (Object.prototype.hasOwnProperty.call(g[0], "prompt") ? g[0].prompt : "ALAN-YOK") : null };
  };
  const ai = { insan: await altIstem("insan"), pet: await altIstem("pet"), model: await altIstem("model"),
    yok: await altIstem(undefined), gecersiz: await altIstem("bust") };
  ol("O12b panel ornek alt_tur: insan/pet/model -> istem FIGUR_ALT_ISTEM ile ayni · alt tursuz prompt YOK · gecersiz 400 (saglayici 0)",
     ["insan", "pet", "model"].every((k) => ai[k].kod === 200 && ai[k].cagri === 1 && ai[k].prompt === foto.FIGUR_ALT_ISTEM[k]) &&
     ai.yok.kod === 200 && ai.yok.prompt === "ALAN-YOK" &&
     ai.gecersiz.kod === 400 && ai.gecersiz.hata === "gecersiz-alt-tur" && ai.gecersiz.cagri === 0, JSON.stringify(ai));
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
    // ek.evt (14 Eki RNH): dinleyiciye iletkeninici özellikler (pointerType vb.) — mevcut çağrılar
    // (ek.evt olmadan) bayt-aynı ({target: this}) çalışır; geriye uyumlu.
    tetikle(tip, evt) { for (const fn of ((this.dinle || {})[tip] || [])) { fn(Object.assign({ target: this }, evt || {})); } }
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
  // 6 MODEL: büst/yapboz kartı istemcide HİÇ çizilmez (KARTLAR'da yok). Bu türlerin form/fiyat/ölçü iddiaları
  // ölçülmeye devam etsin diye kart YALNIZ test içinde enjekte edilir (ek.kart bust|yapboz ya da ek.enjekte
  // listesi); enjekte satır eski KARTLAR satırının AYNISIDIR. Ürün kaynağı değişmez (V6-1 enjekte ETMEDEN ölçer).
  // 6 MODEL (model düzeyinde açıklık): sahte /acik yanıtı `modeller` TAŞIMIYORSA koşum takımı sunucunun "tür açık ->
  // türün TÜM modelleri açık" halini varsayar (eski vakalar tür-düzeyinde yazıldı; ölçtükleri kart/form ekseni değişmez).
  // `modeller` açıkça verilen vaka (MA-*) istemcinin model kapısını ölçer; ek.modellerYok -> alan HİÇ yok (fail-closed).
  if (acikYanit && Array.isArray(acikYanit.turler) && !("modeller" in acikYanit) && !ek.modellerYok) {
    const kodlar = acikYanit.turler.map((t) => t.kod);
    const MODEL_TURU = { anahtarlik_yazi: "anahtarlik", insan: "figur", pet: "figur", plaket: "plaket",
                         anahtarlik_figur: "anahtarlik", model: "figur" };
    acikYanit = { ...acikYanit, modeller: [...Object.keys(MODEL_TURU).filter((m) => kodlar.includes(MODEL_TURU[m])),
                                             ...kodlar.filter((k) => !Object.values(MODEL_TURU).includes(k))] };
  }
  const ENJEKTE_KART = {
    bust: '{ kod: "bust", tur: "bust", alt: null, ad: "Büst", ret: "Büst için yüzü net görünen bir portre fotoğrafı gerekir." }',
    yapboz: '{ kod: "yapboz", tur: "yapboz", alt: null, ad: "Yapboz", ret: "Yapboz için açık-koyu tonları belirgin, yüksek çözünürlüklü fotoğraf gerekir." }',
  };
  const enjekte = [...new Set([...(ek.enjekte || []), ...(ENJEKTE_KART[ek.kart] ? [ek.kart] : [])])];
  if (enjekte.length && kaynak.includes("var KARTLAR = [")) {
    kaynak = kaynak.replace("var KARTLAR = [", "var KARTLAR = [" + enjekte.map((k) => ENJEKTE_KART[k]).join(", ") + ",");
  }
  // ek.gorselSahte: tarayicinin FileReader/Image/canvas zinciri (kucultGorsel) sahte DOM'da yok; saplama
  // dosyayi 100x100 gorsel sayar ve sabit bir JPEG data URL'i dondurur (istek govdesi olculebilsin).
  const gorselSahte = ek.gorselSahte ? {
    FileReader: class { readAsDataURL() { this.onload({ target: { result: "data:image/png;base64,AAAA" } }); } },
    Image: class { set src(v) { this.width = 100; this.height = 100; this.onload(); } },
  } : {};
  // ek.paletSahte (FR): tarayicinin Image + canvas OKUMA zinciri; paletleGoster'in indirgenmis kopyasi FR_PALETLI
  // olur -> ④ img.src'den "palete indirgendi mi" olculur (sahte DOM'da Image yokken paletleGoster kaynagi AYNEN verir).
  // ek.pikselUret(w, h) (EL): tuvalin okuduğu pikseller (sentetik figür); ek.dogalBoy: sağlayıcı görselinin boyu.
  if (ek.paletSahte) {
    const boy = ek.dogalBoy || 2;
    gorselSahte.Image = class { set src(v) { this.naturalWidth = boy; this.naturalHeight = boy; this.onload(); } };
    const yarat = document.createElement;
    document.createElement = (e) => {
      const n = yarat(e);
      if (String(e).toLowerCase() === "canvas") {
        n.getContext = () => ({ drawImage() {}, putImageData() {},
          getImageData: (x, y, w, h) => ({ data: ek.pikselUret ? ek.pikselUret(w, h) : new Uint8ClampedArray(w * h * 4).fill(200) }) });
        n.toDataURL = () => FR_PALETLI;
      }
      return n;
    };
  }
  if (ek.gorselSahte) {
    const yarat = document.createElement;
    document.createElement = (e) => {
      const n = yarat(e);
      if (String(e).toLowerCase() === "canvas") { n.getContext = () => ({ drawImage() {} }); n.toDataURL = () => "data:image/jpeg;base64,SAHTE"; }
      return n;
    };
  }
  // ek.fotoPiksel(w, h) (RN, ④ tek renk): ③ fotoğraftan renk çıkarımı (URL + Image + canvas getImageData) çalışır ->
  // Renkli seçilebilir (sahte DOM'da URL yokken fotoRenkleri boş kalır, Renkli hiç sunulmazdı).
  if (ek.fotoPiksel) {
    gorselSahte.URL = { createObjectURL: () => "blob:sahte", revokeObjectURL() {} };
    const yarat2 = document.createElement;
    document.createElement = (e) => {
      const n = yarat2(e);
      if (String(e).toLowerCase() === "canvas") {
        n.getContext = () => ({ drawImage() {}, getImageData: (x, y, w, h) => ({ data: ek.fotoPiksel(w, h) }) });
        n.toDataURL = () => "data:image/jpeg;base64,SAHTE";
      }
      return n;
    };
  }
  // 13:5x: kayit.tur gelirse sessionStorage'da TÜR SEÇIMI olarak da yaz (galeri otomatik seçer).
  // ek.ssTur: oturum deposundaki tür/kart kodu elle (6 MODEL V6-5: eski `hayvan_model` kodu).
  const ssTur = ek.ssTur || (kayit && kayit.tur ? kayit.tur : null);
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
        // TUR-A3: ek.postAgHatasi -> fetch reddi (ağ hatası) · ek.postGovdesiz -> json() reddi (gövdesiz yanıt).
        if (ek.postAgHatasi) { throw new Error("ag-hatasi"); }
        const kod_ = ek.postKod || 200;
        return { ok: kod_ < 300, status: kod_, json: async () => { if (ek.postGovdesiz) { throw new Error("govdesiz"); } return ek.postYanit || {}; } };
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
  // 6 MODEL (Okan 10 Eki): eski kart kodlari TEK yerde yeni kartlara eslenir — `anahtarlik` -> `anahtarlik_yazi`
  // (figur cesidi testleri ek.kart: "anahtarlik_figur" verir), `hayvan_model` -> `pet`.
  const KART_ESLE = { anahtarlik: "anahtarlik_yazi", hayvan_model: "pet" };
  if (ek.kart) {
    const kartKod = KART_ESLE[ek.kart] || ek.kart;
    const kart = [...bolum.agac()].find((n) => n.classList.contains("foto-uretim-kart") && n.getAttribute("data-kart") === kartKod);
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
  // ek.kaydir === false: sürgü kaydırılmaz (RY: ④ fiyatı ile sepet ölçüsü aynı ekran durumundan ölçülür).
  if (surguler[0] && ek.kaydir !== false) { surguler[0].value = surguler[0].max; surguler[0].tetikle("input"); sonuc.kaydir = fiyatYazilari()[0] || ""; }
  // DOM koku sayilmayan alan (JSON.stringify'a girmez; FM senaryolari dugumleri dogrudan okur).
  Object.defineProperty(sonuc, "bolum", { value: bolum, enumerable: false });
  Object.defineProperty(sonuc, "istekler", { value: istekler, enumerable: false });
  Object.defineProperty(sonuc, "araliklar", { value: araliklar, enumerable: false });
  Object.defineProperty(sonuc, "yoklamalar", { value: yoklamalar, enumerable: false });
  Object.defineProperty(sonuc, "istisna", { value: istisna, enumerable: false });
  Object.defineProperty(sonuc, "istisnaMetni", { value: istisnaMetni, enumerable: false });
  Object.defineProperty(sonuc, "ss", { value: kok.sessionStorage, enumerable: false });
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
  // KAPALI GİZLİ (Okan 10 Eki: "çalışmayan işi neden canlıya aldın"): program kapalı / tür listesi boşken bölüm ana
  // sayfada GÖRÜNMEZ (index.html `hidden` varsayılanı korunur); yalnız açık + ≥1 tür dönünce açılır.
  const kgKapali = await ekranKos(EKRAN_KAYNAK, VERI, { acik: false, turler: [] }, null, null, {});
  const kgBos = await ekranKos(EKRAN_KAYNAK, VERI, { acik: true, turler: [] }, null, null, {});
  ol("KG1 program kapali (/acik acik:false) -> bolum GIZLI kalir", kgKapali.gorunur === false, JSON.stringify({ gorunur: kgKapali.gorunur }));
  ol("KG2 acik ama tur listesi bos -> bolum GIZLI kalir", kgBos.gorunur === false, JSON.stringify({ gorunur: kgBos.gorunur }));
  ol("KG3 acik + 1 tur -> bolum GORUNUR (S0 ekrani)", ekranTek.gorunur === true, JSON.stringify({ gorunur: ekranTek.gorunur }));
  const kgMutKaynak = EKRAN_KAYNAK.replace("    cizYukleniyor();\n    acikYukle();",
    "    bolum.removeAttribute(\"hidden\");\n    cizYukleniyor();\n    acikYukle();");
  const kgMut = kgMutKaynak !== EKRAN_KAYNAK
    ? await ekranKos(kgMutKaynak, VERI, { acik: false, turler: [] }, null, null, {}) : null;
  ol("KG-M1 bolum /acik beklemeden acilir (eski davranis) -> KG1 KIRMIZI yakalanir",
     !!kgMut && kgMut.gorunur === true, JSON.stringify({ capa: kgMutKaynak !== EKRAN_KAYNAK, gorunur: kgMut && kgMut.gorunur }));
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
    for (let i = 0; i < 10; i++) { await turVeOnay(fm, e2, k.d1); }
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

// ================================================================ AH — ANAHTARLIK ÖLÇÜ 30–300, AÇILIŞ 60 (Okan 10 Eki 15:2x)
// "anahtarlıkta boyut ... min 30mm - max 300mm" + netleştirme "60'tan başlasın, 30–300 aralık" (yazı VE figür çeşidi).
// Köprü aralığı yalnız DARALTILIR (kopru-manifest-uret PRUVO_ARALIK): tür en_cok = min(300, köprü yazı 300) = 300 (TeKiN 2f13d23);
// figür çeşidi aralığı köprüden TÜRER (foto_kolu.olcu_en_az = max(30, köprü figür kolu min 30) = 30; olcu_en_cok = min(300,
// figur_kulak yatay çıplak 291,6, kulak dahil 300) = 291 -> adım 5 ile sürgü 30..290). Sahte köprü 300 kopyasında (VO5S) figür tavanı 300. Beklenen sayılar BAĞIMSIZ.
// KULAK_TABAN: figür çeşidi tabanı (köprü figür kolu min_mm 30; bağımsız sabit, kayıttan okunmaz).
const AH_MM = 60, KULAK_TAVAN_YAMA = 70, KULAK_TAVAN_USTU = 75, KULAK_TABAN = 30, KULAK_TAVAN = 291;
function kulakTavanYama(V) {
  const c = V.cesitKaydi("anahtarlik", "figur"), a = c ? c.olcu_en_cok : undefined;
  if (c) { c.olcu_en_cok = KULAK_TAVAN_YAMA; }
  return () => { if (c) { c.olcu_en_cok = a; } };
}
// 6 MODEL (Okan 10 Eki): anahtarlık çeşidi ② düğmesiyle DEĞİL ① kartıyla seçilir ("Anahtarlık – yazı" = anahtarlik_yazi,
// "Anahtarlık – figür" = anahtarlik_figur). Kart bulunup tıklandıysa true.
function cesitKartTikla(bolum, cesit) {
  const k = [...bolum.agac()].find((n) => n.classList.contains("foto-uretim-kart") && n.getAttribute("data-kart") === "anahtarlik_" + cesit);
  if (k) { k.tetikle("click"); }
  return !!k;
}
// İstemci: anahtarlık kartı (yazı çeşidi açılış) -> figür çeşidi ②→④; açılış sürgü satırları, sürgü (en büyük konuma
// çekilir), ③ pencere cümlesi, ④ "Örnek" görselleri, giden istek ve (ek.postKod) ret mesajı ölçülür.
async function ahFigurBosIstemci(V, kaynak, ek2) {
  const acikA = { acik: true, turler: [{ kod: "anahtarlik", ad: V.turBul("anahtarlik").ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri("anahtarlik").map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus("anahtarlik", mm) })) }] };
  const e = await ekranKos(kaynak || EKRAN_KAYNAK, V, acikA, null, null,
    Object.assign({ kart: "anahtarlik", gorselSahte: true, turnstileOto: true }, ek2 || {}));
  const d = () => [...e.bolum.agac()];
  const id = (x) => d().find((n) => n.id === x) || null;
  const sinif = (c) => d().filter((n) => String(n.className || "").split(" ").indexOf(c) >= 0);
  const ornek = () => sinif("foto-uretim-ornek-gorsel").map((n) => n.src);
  const r = {};
  // Açılış sürgü satırı: ekranKos sürgüyü max'a çekmeden ÖNCE okuduğu fiyat yazıları (e.surguFiyat).
  r.acilisYazi = (e.surguFiyat || [])[0] || "";
  r.ornekYazi = ornek();
  // Figür çeşidi = "Anahtarlık – figür" kartı (② çeşit düğmesi YOK).
  r.dugme = cesitKartTikla(e.bolum, "figur");
  const dosya = id("foto-dosya");
  if (dosya) { dosya.files = [{ name: "kedi.jpg", type: "image/jpeg", size: 4096 }]; dosya.tetikle("change"); }
  const ileri = id("foto-ileri");
  r.ileri2 = !!ileri && ileri.disabled === false;
  if (ileri) { ileri.tetikle("click"); }
  const p3 = id("foto-pencere-3");
  r.pencere3 = (sinif("foto-uretim-pencere-aciklama")[0] || {}).textContent || "";
  const surgu = id("foto-olcu");
  r.surgu = !!surgu;
  r.surguMax = surgu ? Number(surgu.max) : -1;
  r.acilisFigur = (sinif("foto-uretim-surgu-fiyat")[0] || {}).textContent || "";
  if (surgu && !(ek2 && ek2.surguAcilista)) { surgu.value = surgu.max; surgu.tetikle("input"); surgu.tetikle("change"); }
  r.bosNot = p3 ? [...p3.agac()].some((n) => n.tagName === "P" && n.textContent === "Bu tür için ölçü seçeneği yok.") : false;
  r.ileri3 = !!ileri && ileri.disabled === false;
  if (ileri) { ileri.tetikle("click"); }
  r.ornekFigur = ornek();
  const on = id("foto-aydinlatma-onay");
  if (on) { on.checked = true; on.tetikle("change"); }
  const btn = id("foto-onizle-buton");
  r.btnAcik = !!btn && btn.disabled === false;
  if (btn) { btn.tetikle("click"); }
  for (let i = 0; i < 5; i++) { await new Promise((c) => setTimeout(c, 0)); }
  r.istek = e.istekler.filter((x) => /\/foto\/onizleme$/.test(x.u))
    .map((x) => ({ olcu: x.govde.olcu_mm, cesit: x.govde.secim && x.govde.secim.cesit }));
  r.mesaj = d().map((n) => n.textContent || "").filter((t) => /hazırlanamıyor|Seçtiğin ölçü/.test(t) && t.length < 200);
  r.istisna = e.istisna + ":" + e.istisnaMetni;
  return r;
}
// ahSenaryo(V): V'nin fonksiyonlari sunucunun global VERI'sine gecici takilir (mutant da sunucudan olculur).
async function ahSenaryo(V, kaynak) {
  const ad = ["turBul", "olcuAraligi", "olcuGecerli", "olcuSecenekleri", "fiyatKurus", "ornekSayisi", "cesitKaydi"];
  const yedek = {};
  for (const a of ad) { yedek[a] = VERI[a]; VERI[a] = a === "ornekSayisi" ? (() => 1) : V[a]; }
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x'), ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (govde) => {
    const h = { "CF-Connecting-IP": "10.0.13." + (++ipNo), "Content-Type": "application/json" };
    const u = "https://pruvo3d.com/api/shop/foto/onizleme";
    const r = await foto.fotoUclari(new Request(u, { method: "POST", headers: h, body: JSON.stringify(govde) }),
      e2, new URL(u), "/foto/onizleme", null);
    let v = null; try { v = await r.json(); } catch (er) { v = null; }
    return { kod: r.status, hata: v && v.hata ? v.hata : "" };
  };
  const secim = { plaka_renk: "Beyaz", yazi_renk: "Siyah", govde_malzeme: "PLA" };
  const yazi = (mm) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: mm, gorsel: undefined, cesit: "yazi", secim,
    parametreler: { satirlar: ["Ayşe"], yazi_tipi: "script", hizalama: "orta", genislik_mm: AH_MM,
      anahtarlik_kulak_konum: "sol-ust", kontur_tasma_mm: 1.5 } });
  const figur = (mm) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: mm, gorsel: GORSEL, parametreler: undefined,
    cesit: "figur", secim });
  const s = {}, iz = {};
  try {
    const a = VERI.olcuAraligi("anahtarlik") || {};
    const g_ = (mm) => VERI.olcuGecerli("anahtarlik", mm);
    s.VO1 = a.en_az === 30 && a.en_cok === 300 && g_(30) && g_(35) && g_(60) && g_(80) && g_(300) &&
      !g_(29) && !g_(25) && !g_(301);
    // VO2: açılış 60 (veri) + istemci yazı ve figür sürgüsü 60'ta açılır; diğer türlerde açılış = en_az AYNEN.
    iz.acilis = ["anahtarlik", "figur", "plaket", "bust", "yapboz"].map((t) => V.olcuBaslangic(t));
    s.VO3 = VERI.fiyatKurus("anahtarlik", 30) === 60000 && VERI.fiyatKurus("anahtarlik", 55) === 60000 &&
      VERI.fiyatKurus("anahtarlik", 60) === 60000 && VERI.fiyatKurus("anahtarlik", 80) === 80000 &&
      VERI.fiyatKurus("anahtarlik", 300) === 300000;
    // VO4: sunucu yazı çeşidi önizleme ucu (29/25 RED, 30/60 kabul) + üreteç çıktı ölçü kapısı (aralık dışı).
    const oj = (L) => ({ sozlesme: 1, kategori: "anahtarlik", uzun_kenar_mm: L, kutu_mm: { x: L, y: L / 2, z: 4 }, renk_sayisi: 2, sizdirmaz: true });
    iz.y29 = await cag(yazi(29)); iz.y25 = await cag(yazi(25)); iz.y30 = await cag(yazi(30)); iz.y60 = await cag(yazi(60));
    iz.u29 = foto.uretecOlcuDogrula(oj(29), { tur: "anahtarlik", olcu_mm: 29 });
    iz.u30 = foto.uretecOlcuDogrula(oj(30), { tur: "anahtarlik", olcu_mm: 30 });
    s.VO4 = iz.y29.kod === 400 && iz.y29.hata === "gecersiz-olcu" && iz.y25.kod === 400 && iz.y25.hata === "gecersiz-olcu" &&
      iz.y30.kod === 200 && iz.y60.kod === 200 && iz.u29 === "olcu-aralik-disi" && iz.u30 !== "olcu-aralik-disi";
    // VA4: ③ yazı alanı (kulak dahil uzun kenar) = tür aralığı; varsayılan/örnek = açılış 60.
    const g = ((V.turBul("anahtarlik") || {}).form || {}).genislik_mm || {};
    iz.alan = { min: g.min, max: g.max, varsayilan: g.varsayilan, ornek: g.ornek };
    s.VA4 = g.min === 30 && g.min === a.en_az && g.max === a.en_cok && g.varsayilan === 60 && g.ornek === 60;
    // VB1: figür sürgüsü 30..290 (köprü figür kolu min 30 .. çıplak tavan 291; adım 5 -> 53 konum), en büyük 290 gider.
    // VB2: sunucu figür çeşidi 30/60/290 kabul; 29 (köprü kol tabanı 30 altı) + 295/300 (tavan 291 üstü) -> 400, sağlayıcı 0.
    const ck = VERI.cesitKaydi("anahtarlik", "figur") || {};
    iz.tavan = ck.olcu_en_cok;
    iz.ist = await ahFigurBosIstemci(V, kaynak);
    iz.f30 = await cag(figur(30)); iz.f60 = await cag(figur(60)); iz.f70 = await cag(figur(290));
    const p0 = protoSayisi();
    iz.f29 = await cag(figur(29)); iz.f75 = await cag(figur(295)); iz.f80 = await cag(figur(300));
    iz.proto = protoSayisi() - p0;
    s.VO2 = JSON.stringify(iz.acilis) === "[60,60,60,60,100]" && iz.ist.acilisYazi === "60 mm → 600 TL" &&
      iz.ist.acilisFigur === "60 mm → 600 TL";
    s.VA5 = ck.acik === true && ck.olcu_en_cok >= a.en_az && iz.ist.istisna === "0:" && iz.ist.surgu === true &&
      iz.ist.bosNot === false && iz.ist.btnAcik === true && iz.ist.istek.length === 1 && iz.ist.istek[0].cesit === "figur";
    s.VB1 = iz.ist.surguMax === 52 && iz.ist.istek.length === 1 && iz.ist.istek[0].olcu === 290;
    s.VB2 = iz.f30.kod === 200 && iz.f29.kod === 400 && iz.f29.hata === "gecersiz-olcu" && iz.f60.kod === 200 && iz.f70.kod === 200 && iz.f75.kod === 400 &&
      iz.f75.hata === "gecersiz-olcu" && iz.f80.kod === 400 && iz.f80.hata === "gecersiz-olcu" && iz.proto === 0;
    // VO5: figür çeşidi tavanı köprüden türeyen kol tavanı (foto_kolu.olcu_en_cok) — bugün 291.
    const fk = (V.turBul("anahtarlik") || {}).foto_kolu || {};
    s.VO5 = ck.olcu_en_cok === fk.olcu_en_cok && ck.olcu_en_cok === KULAK_TAVAN;
    // VO6: ④ "Örnek" çeşide göre — yazı çeşidinde yazı örneği 1, figür çeşidinde (11 Eki render kaydı) figür örneği 1.
    s.VO6 = JSON.stringify(iz.ist.ornekYazi) === '["https://media.pruvo3d.com/foto/ornek/anahtarlik-1-render.webp"]' &&
      JSON.stringify(iz.ist.ornekFigur) === '["https://media.pruvo3d.com/foto/ornek/anahtarlik-figur-hilal-2-render.webp"]';
    // VO7 (renk = palet dilimi, BaBa 16:0x 2a): Renkli çeşit başına (yazı: fotoğrafsız -> YOK · figür: köprü kolu
    // renk_modu tek|palet -> VAR · figür türü: var) + figür anahtarlık ③ cümlesi Renkli'yi ANAR.
    iz.renkli = { yazi: V.renkliSecilebilir("anahtarlik", "yazi"), figur: V.renkliSecilebilir("anahtarlik", "figur"),
      figur_turu: V.renkliSecilebilir("figur") };
    s.VO7 = iz.renkli.yazi === false && iz.renkli.figur === true && iz.renkli.figur_turu === true &&
      iz.ist.pencere3.indexOf("Renk: Siyah, Beyaz, Gri ya da Renkli (+%15;") === 0;
  } finally {
    for (const a of ad) { VERI[a] = yedek[a]; }
    k.kapat();
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("AH) ANAHTARLIK OLCU 30–300 (kopru 300), ACILIS 60 (Okan 10 Eki 15:2x) + ornek/Renkli/ret cumlesi");
{
  const s = await ahSenaryo(veriYukle(VERI_KAYNAK));
  ol("VO1 anahtarlik araligi en_az 30 · en_cok 300 = min(300, kopru 300) (30/35/60/80/300 gecerli; 29/25/301 gecersiz)", s.VO1, "");
  ol("VO2 surgu acilisi 60 (veri anahtarlik 60; figur/plaket/bust/yapboz = en_az 60/60/60/100) + istemci yazi ve figur '60 mm → 600 TL'",
     s.VO2, JSON.stringify([s.iz.acilis, s.iz.ist.acilisYazi, s.iz.ist.acilisFigur]));
  ol("VO3 anahtarlik 30/55/60/80/300 mm = 600/600/600/800/3000 TL (taban 600 30..60 araliginda)", s.VO3, "");
  ol("VO4 sunucu yazi cesidi 29/25 mm -> 400 gecersiz-olcu, 30/60 mm -> 200; uretec olcu kapisi 29 aralik disi, 30 icinde",
     s.VO4, JSON.stringify([s.iz.y29, s.iz.y25, s.iz.y30, s.iz.y60, s.iz.u29, s.iz.u30]));
  ol("VA4 yazi alani genislik_mm min 30 = tur en_az (max 300 = en_cok, varsayilan/ornek 60)", s.VA4, JSON.stringify(s.iz.alan));
  ol("VA5 figur cesidi bos aralik YOK (tavan " + s.iz.tavan + " >= 30): istemci istisna 0, surgu VAR, 'olcu secenegi yok' notu 0, onizleme istegi gider",
     s.VA5, JSON.stringify(s.iz.ist));
  ol("VB1 figur cesidi surgusu 30..290: 53 konum (kopru kol tabani 30, tavan 291; 295/300 sunulmaz), en buyuk konum 290 gider", s.VB1, JSON.stringify(s.iz.ist));
  ol("VB2 sunucu figur cesidi 30/60/290 kabul; 29 (kopru kol tabani 30 alti) ve 295/300 (tavan 291 ustu) -> 400 gecersiz-olcu, saglayici 0", s.VB2,
     JSON.stringify([s.iz.f29, s.iz.f30, s.iz.f60, s.iz.f70, s.iz.f75, s.iz.f80, s.iz.proto]));
  ol("VO5 figur cesidi tavani = kopruden tureyen foto_kolu.olcu_en_cok (291)", s.VO5, String(s.iz.tavan));
  ol("VO6 ④ Ornek cesside gore: yazi cesidinde yazi ornegi 1, figur cesidinde figur ornegi 1", s.VO6,
     JSON.stringify([s.iz.ist.ornekYazi, s.iz.ist.ornekFigur]));
  ol("VO7 Renkli cesit basina (yazi yok · figur VAR [kopru renk_modu palet] · figur turu var) + figur anahtarlik ③ cumlesi Renkli'yi anar",
     s.VO7, JSON.stringify([s.iz.renkli, s.iz.ist.pencere3]));
  // KÖPRÜ 300 GERÇEK (TeKiN 2f13d23): VO1S/VO3S gerçek veride; VO5S figür tavanı sahte köprü 300 kopyasında (elle sabit yok —
  // kopru-manifest-uret-test R-OK2'de üretecin kendisiyle de ölçülür).
  const capaA = "olcu_mm: { en_az: 30, en_cok: 300, baslangic: 60 },", capaF = "olcu_en_cok: 291,\n";
  const V3 = veriYukle(VERI_KAYNAK);
  const V5S = VERI_KAYNAK.split(capaF).length === 2 ? veriYukle(VERI_KAYNAK.replace(capaF, "olcu_en_cok: 300,\n")) : null;
  ol("VO1S kopru 300 (gercek): araligi 30..300 (300 gecerli, 301/29 gecersiz)", !!V3 && V3.olcuGecerli("anahtarlik", 300) &&
     !V3.olcuGecerli("anahtarlik", 301) && !V3.olcuGecerli("anahtarlik", 29) && V3.olcuGecerli("anahtarlik", 30), "");
  ol("VO3S kopru 300 (gercek): 30/60/300 mm = 600/600/3000 TL", !!V3 && V3.fiyatKurus("anahtarlik", 30) === 60000 &&
     V3.fiyatKurus("anahtarlik", 60) === 60000 && V3.fiyatKurus("anahtarlik", 300) === 300000, "");
  ol("VO5S sahte kopru 300: figur cesidi tavani 300 (elle sabit yok)", !!V5S && V5S.cesitKaydi("anahtarlik", "figur").olcu_en_cok === 300, "");
  // VO9: sunucu 400 gecersiz-olcu / olcu-aralik-disi -> genel cümle DEĞİL ölçü cümlesi (aralık sürgüden: figür 30–290).
  const V9 = veriYukle(VERI_KAYNAK);
  const r9 = await ahFigurBosIstemci(V9, null, { postKod: 400, postYanit: { hata: "gecersiz-olcu" } });
  const r9b = await ahFigurBosIstemci(V9, null, { postKod: 400, postYanit: { hata: "olcu-aralik-disi" } });
  const olcuCumle = "Seçtiğin ölçü bu ürün için sunulmuyor; ölçüyü 30–290 mm arasında seçip tekrar dene.";
  ol("VO9 400 gecersiz-olcu / olcu-aralik-disi -> olcu cumlesi (genel 'hazirlanamiyor' 0)",
     JSON.stringify(r9.mesaj) === JSON.stringify([olcuCumle]) && JSON.stringify(r9b.mesaj) === JSON.stringify([olcuCumle]),
     JSON.stringify([r9.mesaj, r9b.mesaj]));
  const H = ["VO1", "VO2", "VO3", "VO4", "VA4", "VA5", "VB1", "VB2", "VO5", "VO6", "VO7"];
  const mk = async (ad_, capa, yeni, bek, kaynakMu) => {
    const ks = kaynakMu ? EKRAN_KAYNAK : VERI_KAYNAK;
    const m = ks.split(capa).length === 2 ? (kaynakMu ? await ahSenaryo(veriYukle(VERI_KAYNAK), ks.replace(capa, yeni))
      : await ahSenaryo(veriYukle(ks.replace(capa, yeni)))) : null;
    const kir = m ? H.filter((x) => m[x] !== true) : null;
    ol(ad_ + " -> KIRMIZI tam olarak " + JSON.stringify(bek), JSON.stringify(kir) === JSON.stringify(bek), JSON.stringify(kir));
  };
  // MUTANTLAR (kopyada): en_az 60'a geri · açılış alanı yok · figür kol tavanı 80 · örnek seçimi çeşitsiz.
  await mk("AHM mutant anahtarlik en_az 60'a geri", capaA, "olcu_mm: { en_az: 60, en_cok: 300, baslangic: 60 },",
    ["VO1", "VO3", "VO4", "VA4", "VB1", "VB2"]); // figür çeşidi tür tabanının altına inemez
  await mk("AAM mutant acilis alani yok (baslangic silindi)", capaA, "olcu_mm: { en_az: 30, en_cok: 300 },", ["VO2"]);
  // VBM: figür kol tavanı eski 72'ye döner (köprü tazelenmemiş) -> sürgü/sunucu/tavan KIRMIZI.
  await mk("VBM mutant figur kol tavani 72'ye geri", capaF, "olcu_en_cok: 72,\n", ["VB1", "VB2", "VO5"]);
  await mk("AOM mutant ornek secimi cesitsiz", '(o.cesit || "") === cz && ', "", ["VO6"], true);
}

// ================================================================ PL — PLAKET OLCU ALT SINIRI 60 (Okan 10 Eki ~13:4x)
// "plaket de 60 mm olsun": plaket olcu_mm.en_az 60 (en_cok 300 aynen); foto.js OLCU_MM_EN_AZ 60 (manifest plaket ile
// AYNI). Sunucu araligi kayittan TURETIR; istemci surgusu sunucunun olculer dizisinden. V-TABLO: tum turlerin alt/ust
// sinirlari tek vakada. Beklenen sayilar BAGIMSIZ (kayittan okunmaz).
async function plSenaryo(V) {
  const ad = ["turBul", "olcuAraligi", "olcuGecerli", "olcuSecenekleri", "fiyatKurus", "ornekSayisi", "cesitKaydi"];
  const yedek = {};
  for (const a of ad) { yedek[a] = VERI[a]; VERI[a] = a === "ornekSayisi" ? (() => 1) : V[a]; }
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (govde) => {
    const h = { "CF-Connecting-IP": "10.0.14." + (++ipNo), "Content-Type": "application/json" };
    const u = "https://pruvo3d.com/api/shop/foto/onizleme";
    const r = await foto.fotoUclari(new Request(u, { method: "POST", headers: h, body: JSON.stringify(govde) }),
      e2, new URL(u), "/foto/onizleme", null);
    let v = null; try { v = await r.json(); } catch (er) { v = null; }
    return { kod: r.status, hata: v && v.hata ? v.hata : "" };
  };
  const s = {}, iz = {};
  try {
    const a = VERI.olcuAraligi("plaket") || {};
    s.VP1 = a.en_az === 60 && a.en_cok === 300 && VERI.olcuGecerli("plaket", 60) && VERI.olcuGecerli("plaket", 70) &&
      VERI.olcuGecerli("plaket", 300) && !VERI.olcuGecerli("plaket", 59) && !VERI.olcuGecerli("plaket", 50) &&
      !VERI.olcuGecerli("plaket", 10);
    s.VP2 = VERI.fiyatKurus("plaket", 60) === 60000 && VERI.fiyatKurus("plaket", 300) === 300000;
    // VP3: sunucu onizleme ucu (59/50 -> 400 gecersiz-olcu, 60 -> 200) + uretec cikti olcu kapisi (aralik disi).
    const oj = (L) => ({ sozlesme: 1, kategori: "plaket", uzun_kenar_mm: L, kutu_mm: { x: L, y: L, z: 4 }, renk_sayisi: 1, sizdirmaz: true });
    iz.p59 = await cag(onizlemeGovde({ olcu_mm: 59 })); iz.p50 = await cag(onizlemeGovde({ olcu_mm: 50 }));
    iz.p60 = await cag(onizlemeGovde({ olcu_mm: 60 }));
    iz.u59 = foto.uretecOlcuDogrula(oj(59), { tur: "plaket", olcu_mm: 59 });
    iz.u50 = foto.uretecOlcuDogrula(oj(50), { tur: "plaket", olcu_mm: 50 });
    s.VP3 = iz.p59.kod === 400 && iz.p59.hata === "gecersiz-olcu" && iz.p50.kod === 400 && iz.p50.hata === "gecersiz-olcu" &&
      iz.p60.kod === 200 && iz.u59 === "olcu-aralik-disi" && iz.u50 === "olcu-aralik-disi";
    // VP4: istemci surgusu = /foto/acik plaket olculer dizisi (olcuSurgusu nt.olculer[0]'dan baslar) + surgu yazisi.
    const nt = foto.acikTurler(new Set(["plaket"])).find((t) => t.kod === "plaket");
    iz.ilk = nt && nt.olculer[0] ? nt.olculer[0] : null;
    iz.yazi = iz.ilk ? V.fiyatSatiri("plaket", iz.ilk.mm) : "";
    s.VP4 = !!iz.ilk && iz.ilk.mm === 60 && iz.ilk.fiyat_kurus === 60000 && iz.yazi === "60 mm → 600 TL" &&
      foto.OLCU_MM_EN_AZ === 60;
    // V-TABLO: figur zarfi 41..300 (model basina, 22:3x) · plaket 60 · bust 60 · anahtarlik 30 (Okan 10 Eki 15:2x) · yapboz 100 (ust: 200/300/250/300/280).
    const ar = (t) => { const x = VERI.olcuAraligi(t) || {}; return [x.en_az, x.en_cok]; };
    iz.tablo = { figur: ar("figur"), plaket: ar("plaket"), bust: ar("bust"), anahtarlik: ar("anahtarlik"), yapboz: ar("yapboz") };
    s.VTABLO = JSON.stringify(iz.tablo) ===
      '{"figur":[41,300],"plaket":[60,300],"bust":[60,250],"anahtarlik":[30,300],"yapboz":[100,280]}';
  } finally {
    for (const a of ad) { VERI[a] = yedek[a]; }
    k.kapat();
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("PL) PLAKET OLCU ALT SINIRI 60 mm (Okan 10 Eki ~13:4x) + tum turlerin olcu tablosu");
{
  const s = await plSenaryo(veriYukle(VERI_KAYNAK));
  ol("VP1 plaket araligi en_az 60 · en_cok 300 (60/70/300 gecerli; 59/50/10 gecersiz)", s.VP1, "");
  ol("VP2 plaket 60 mm = 600 TL (300 mm = 3.000 TL)", s.VP2, "");
  ol("VP3 sunucu plaket 59/50 mm -> 400 gecersiz-olcu, 60 mm -> 200; uretec olcu kapisi 59/50 aralik disi",
     s.VP3, JSON.stringify([s.iz.p59, s.iz.p50, s.iz.p60, s.iz.u59, s.iz.u50]));
  ol("VP4 surgu ilk deger plaket '60 mm → 600 TL' (OLCU_MM_EN_AZ 60)", s.VP4, JSON.stringify([s.iz.ilk, s.iz.yazi]));
  ol("V-TABLO figur 60 · plaket 60 · bust 60 · anahtarlik 30 · yapboz 100 (ust 200/300/250/300/280 aynen)", s.VTABLO, JSON.stringify(s.iz.tablo));
  // MUTANT (kopyada): plaket en_az 10'a geri -> VP1/VP3/VP4 KIRMIZI (+V-TABLO).
  const capa = 'olcu_mm: { en_az: 60, en_cok: 300 },';
  const m = VERI_KAYNAK.split(capa).length === 2
    ? await plSenaryo(veriYukle(VERI_KAYNAK.replace(capa, "olcu_mm: { en_az: 10, en_cok: 300 },"))) : null;
  const kir = m ? ["VP1", "VP2", "VP3", "VP4", "VTABLO"].filter((x) => m[x] !== true) : null;
  ol("PLM mutant plaket en_az 10 -> KIRMIZI tam olarak [VP1,VP3,VP4,VTABLO]", JSON.stringify(kir) === '["VP1","VP3","VP4","VTABLO"]', JSON.stringify(kir));
}
/**
 * Veri nesnesi V (dosya ya da mutant) ile sunucu kapisi: foto.js ornek sayisini V'den okur.
 * Temiz SQLite'ta plaket + litofan 120 mm fiyat satiri VAR. Donus: her senaryo tuttu mu.
 */
async function renderSenaryolar(V) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('insan', 1, 'x'), ('pet', 1, 'x'), ('model', 1, 'x')").run();
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
       /^https:\/\/media\.pruvo3d\.com\/foto\/ornek\/kart-plaket-2\.webp$/.test(r[0].onizleme) &&
       /^https:\/\/media\.pruvo3d\.com\/foto\/ornek\/kart-plaket-2\.webp$/.test(r[0].render), JSON.stringify(r));
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

// 14 Eki 18:5x (Okan, aynen "bunları sil"): ① kart kanıt etiketi kartta ÇİZİLMEZ; ornekli kart için span YOK,
// "Örnek görsel (bilgisayar çizimi)" / "basılmış ürün" metinleri ① kart bölgesinde 0 · "yakında" (devre dışı)
// + "Örnek yakında" (ornek-yok) etiketleri AYNEN durur · ② ornek_notu AYNEN, "gerçek fotoğraf" 0.
// K3b: ızgara + büyütme penceresi KALKTI (Okan 01:0x) → kart ① penceresinde, ornek_notu ② dürüstlük
// kutusunda (kart seçilince). C2 (10 Eki): gerçek plaket ornek_notu "" (② TEK cümle, VM2) -> MEKANİZMA burada
// bellek yamasıyla (plaket ornek_notu = CUMLE_P) ölçülür.
console.log("ES) EKRAN — ① kart: render/baski kanıt etiketi YOK, metin 0; ornek-yok/devre-dışı AYNEN; 'gerçek fotoğraf' 0; ② ornek_notu AYNEN");
{
  const sinifli = (kok, c) => [...kok.agac()].filter((n) => n.classList.contains(c));
  const CUMLE_P = "TEST render notu: üretim dosyasının görüntüsüdür (bellek yaması; mekanizma ölçümü).";
  const notYama = (V) => { const t = V.turBul("plaket"); if (t) { t.ornek_notu = CUMLE_P; } return V; };
  const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] });
  // opts.turler: açık tür listesi (varsayılan: [plaket]); opts.hedefKart: tıklanacak kart kodu (data-kart).
  const yol = async (kaynak, V, opts = {}) => {
    const turler = opts.turler || [tur("plaket", "Kabartma plaket")];
    const hedefKart = opts.hedefKart || null;
    const e = await ekranKos(kaynak, V, { acik: true, turler });
    const kartlar = [...sinifli(e.bolum, "foto-uretim-kart")];
    const kart = hedefKart ? kartlar.find((k) => k.getAttribute("data-kart") === hedefKart) : kartlar[0];
    const etiketSpan = kart ? sinifli(kart, "foto-uretim-kart-etiket")[0] : null;
    const etiket = etiketSpan ? etiketSpan.textContent : null;
    const once = e.bolum.textContent;
    if (kart) { kart.tetikle("click"); }
    const d = sinifli(e.bolum, "foto-uretim-durustluk")[0];
    const not = d && d.childNodes[1] ? d.childNodes[1].textContent : null;
    const eski = ["foto-uretim-buyuk-kart", "foto-uretim-isik", "foto-uretim-galeri-kucuk", "foto-uretim-ornek-grup"]
      .some((c) => sinifli(e.bolum.parentNode, c).length > 0);
    return {
      kart: !!kart, etiket, etiketVar: !!etiketSpan, not,
      metin: once + " " + e.bolum.textContent, eski,
      kartlar: kartlar.map((k) => ({
        kod: k.getAttribute("data-kart"),
        etiket: (sinifli(k, "foto-uretim-kart-etiket")[0] || { textContent: null }).textContent,
      })),
    };
  };
  const esDene = async (kaynak) => {
    const Va = notYama(veriYukle(VERI_KAYNAK));
    Va.ornekler.splice(0, Va.ornekler.length, ...Va.ornekler.filter((o) => o.tur === "plaket"));
    const R = await yol(kaynak, Va);
    const Vb = notYama(veriYukle(VERI_KAYNAK));
    Vb.ornekler.splice(0, Vb.ornekler.length, { tur: "plaket", kanit: "baski", olcu_mm: 100, foto: "https://media.pruvo3d.com/b-f.webp",
      onizleme: "https://media.pruvo3d.com/b-o.webp", baski: "https://media.pruvo3d.com/b-b.webp", not: "t" });
    const B = await yol(kaynak, Vb);
    // Y: anahtarlik tür açık; yalnız anahtarlik_yazi orneki var → anahtarlik_figur kart kanit="ornek-yok"
    // ("Örnek yakında" etiketi). ① kart kanıt etiketi YOK iddiası burada da görünür (yazi kart render orneği).
    const Vc = notYama(veriYukle(VERI_KAYNAK));
    Vc.ornekler.splice(0, Vc.ornekler.length, ...Vc.ornekler.filter((o) => o.tur === "anahtarlik" && o.cesit === "yazi"));
    const Y = await yol(kaynak, Vc, { turler: [tur("anahtarlik", "Anahtarlık")], hedefKart: "anahtarlik_yazi" });
    const kirmizi = [];
    // ① kart kanıt etiketi: ornekli kartlarda span YOK (render, baski, ornekli kart dahil).
    if (R.etiketVar) kirmizi.push("ETIKET_RENDER_VAR");
    if (B.etiketVar) kirmizi.push("ETIKET_BASKI_VAR");
    const yaziKart = Y.kartlar.find((k) => k.kod === "anahtarlik_yazi");      // ornekli (render)
    const figurKart = Y.kartlar.find((k) => k.kod === "anahtarlik_figur");    // ornek-yok
    if (yaziKart && yaziKart.etiket !== null) kirmizi.push("ETIKET_ANAHTARLIK_VAR");
    // ① kart bölgesi metninde "Örnek görsel (bilgisayar çizimi)" / "basılmış ürün" 0.
    if (/Örnek görsel \(bilgisayar çizimi\)/.test(R.metin)) kirmizi.push("METIN_RENDER");
    if (/basılmış ürün/.test(B.metin)) kirmizi.push("METIN_BASKI");
    if (/Örnek görsel \(bilgisayar çizimi\)/.test(Y.metin)) kirmizi.push("METIN_RENDER_Y");
    if (/basılmış ürün/.test(Y.metin)) kirmizi.push("METIN_BASKI_Y");
    // ornek-yok davranışı AYNEN: "Örnek yakında" etiketi VAR.
    if (!figurKart || figurKart.etiket !== "Örnek yakında") kirmizi.push("ORNEK_YOK_ETIKET");
    // eski iddialar korunur.
    if (/Gerçek örnek/.test(R.metin + B.metin)) kirmizi.push("BASLIK_GERCEK_ORNEK");
    if (/gerçek fotoğraf/i.test(R.metin)) kirmizi.push("RENDER_GERCEK_FOTOGRAF");
    if (/gerçek fotoğraf/i.test(B.metin) || /Basılmış ürün \(gerçek fotoğraf\)/.test(B.metin)) kirmizi.push("BASKI_GERCEK_FOTOGRAF");
    if (R.not !== CUMLE_P) kirmizi.push("ORNEK_NOTU");
    // Render dürüstlük cümlesi baskı kaydına YAZILMAZ.
    if (B.not !== "") kirmizi.push("BASKI_NOTU");
    if (R.eski || B.eski) kirmizi.push("BUYUK_KART");
    return { kirmizi, R, B, Y };
  };
  const s = await esDene(EKRAN_KAYNAK);
  ol("ES1 render kaydi: kartta kanit etiketi span YOK, 'Örnek görsel (bilgisayar çizimi)' metni 0, 'Gerçek örnekler' 0; ②'de ornek_notu AYNEN; buyuk kart/isik/izgara 0",
     s.kirmizi.length === 0, JSON.stringify(s));
  ol("ES2 baski kaydi: kartta kanit etiketi span YOK, 'basılmış ürün' metni 0; 'Basılmış ürün (gerçek fotoğraf)' 0; render cumlesi baskiya yazilmaz",
     s.kirmizi.length === 0, JSON.stringify(s));
  ol("ES3 ornek-yok kart ('Örnek yakında') AYNEN + ornekli kart span YOK (anahtarlik yazi render, anahtarlik figur ornek-yok)",
     s.Y.kartlar.some((k) => k.etiket === "Örnek yakında") && s.Y.kartlar.some((k) => k.etiket === null),
     JSON.stringify(s.Y.kartlar));
  const ES_MUT = [
    // ES-M1: ornekli kart için span geri konursa ETIKET_RENDER_VAR + ETIKET_BASKI_VAR + ETIKET_ANAHTARLIK_VAR
    // tetiklenir (her devre'de span eklenir, render/baski/yazi kartlarında artık etiket VAR).
    ["ES-M1 ① kart kanit etiketi geri kondu (ornekli kart icin span eklendi)",
     'if (devreDisi || it.kanit === "ornek-yok") {',
     'if (true) {',
     ["ETIKET_RENDER_VAR", "ETIKET_BASKI_VAR", "ETIKET_ANAHTARLIK_VAR"]],
    ["ES-M2 ornek_notu ②'ye yazilmadi", 'S.ornekNotP.textContent = it && it.kanit === "render" ? it.tur.ornek_notu || "" : "";',
     'S.ornekNotP.textContent = "";', ["ORNEK_NOTU"]],
    ["ES-M3 render sarti kalkti (render cumlesi baskiya yazilir)", 'S.ornekNotP.textContent = it && it.kanit === "render" ? it.tur.ornek_notu || "" : "";',
     'S.ornekNotP.textContent = it ? it.tur.ornek_notu || "" : "";', ["BASKI_NOTU"]],
    ["ES-MK KONTROL (yorum)", "  function kartOrnegi(t, cesit, alt) {", "  // kontrol\n  function kartOrnegi(t, cesit, alt) {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of ES_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await esDene(EKRAN_KAYNAK.replace(capa, yerine));
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
       JSON.stringify(m.kirmizi.slice().sort()) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(m.kirmizi));
  }
}

// KA) ① KART KUCUK RESMI (Okan 14 Eki 16:1x): anahtarlik_figur kartinda ornek.render yerine kart alani cizilir;
// alt metni kart_alt; diger 5 kart bayt-esit ayni (degisiklik ONCESI deger).
console.log("KA) KART KUCUK RESMI — anahtarlik_figur: kart URL + 'Anahtarlık – figür örneği' alt; diger 5 kart eski render/baski/''");
{
  const KART_URL = "https://media.pruvo3d.com/foto/ornek/anahtarlik-figur-kart.webp";
  const KART_ALT = "Anahtarlık – figür örneği";
  // Diger 5 kart icin ONCESI deger: ornek.render / ornek.baski + alt = "" — kayit VERI_KAYNAK'tan (degisiklik
  // ONCESI = "hilal-2-render.webp" + ""). Bu degerler kart yapisinin (ornekCiz'in `kart ||` fallback'i) birebir
  // davranmasinin kanitidir: figur_figur kartinda `kart` URL gorulurse yalniz bu kod yolu secmis demektir.
  const DIGER_BEKLENEN = {
    anahtarlik_yazi: { src: "https://media.pruvo3d.com/foto/ornek/anahtarlik-1-render.webp", alt: "" },
    insan:           { src: "https://media.pruvo3d.com/foto/ornek/kart-insan-2.webp", alt: "" },
    pet:             { src: "https://media.pruvo3d.com/foto/ornek/kart-pet-1.webp", alt: "" },
    plaket:          { src: "https://media.pruvo3d.com/foto/ornek/kart-plaket-2.webp", alt: "" },
    model:           { src: "https://media.pruvo3d.com/foto/ornek/kart-model-1.webp", alt: "" },
  };
  const kartBul = (bolum, kod) => [...bolum.agac()].filter((n) => n.tagName === "BUTTON" && n.getAttribute("data-kart") === kod)[0] || null;
  const imgBul = (kart) => kart ? [...kart.agac()].find((n) => n.tagName === "IMG") || null : null;
  const kartKos = async (kaynak) => {
    const V = veriYukle(VERI_KAYNAK);
    const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] });
    const e = await ekranKos(kaynak, V, { acik: true, turler: [tur("plaket", "Plaket"), tur("figur", "Figür"), tur("anahtarlik", "Anahtarlık")] });
    const figurKart = kartBul(e.bolum, "anahtarlik_figur");
    const figurImg = imgBul(figurKart);
    // foto-uretim.js `im.src = ...` / `im.alt = ...` ile PROPERTY atar (setAttribute değil); sahte DOM'da
    // JS özelliği olarak okunmalı.
    const figur = { kartVar: !!figurKart, src: figurImg && figurImg.src, alt: figurImg && figurImg.alt };
    const diger = {};
    for (const kod of Object.keys(DIGER_BEKLENEN)) {
      const k = kartBul(e.bolum, kod);
      const im = imgBul(k);
      diger[kod] = { kartVar: !!k, src: im && im.src, alt: im && im.alt };
    }
    return { figur, diger };
  };
  const s = await kartKos(EKRAN_KAYNAK);
  ol("KA1 anahtarlik_figur karti VAR, img.src = kart URL, img.alt = '" + KART_ALT + "'",
     s.figur.kartVar && s.figur.src === KART_URL && s.figur.alt === KART_ALT,
     JSON.stringify(s.figur));
  const digerKirmizi = [];
  for (const kod of Object.keys(DIGER_BEKLENEN)) {
    const b = DIGER_BEKLENEN[kod];
    const r = s.diger[kod];
    if (!r.kartVar || r.src !== b.src || r.alt !== b.alt) { digerKirmizi.push(kod + ":" + JSON.stringify(r)); }
  }
  ol("KA2 diger 5 kart (yazi/insan/pet/plaket/model) src/alt bayt-esit ayni",
     digerKirmizi.length === 0, digerKirmizi.join(" | "));
  // MUTANT: `it.ornek.kart ||` fallback'i SILINIR -> anahtarlik_figur eski render URL'ine doner, KA1 KIRMIZI.
  const kaCapa = "im.src = it.ornek.kart || (it.kanit === \"render\" ? it.ornek.render : it.kanit === \"yakinda\" ? \"\" : it.ornek.baski);";
  const kaYerine = "im.src = (it.kanit === \"render\" ? it.ornek.render : it.kanit === \"yakinda\" ? \"\" : it.ornek.baski);";
  const kaMu = EKRAN_KAYNAK.split(kaCapa).length === 2 ? await kartKos(EKRAN_KAYNAK.replace(kaCapa, kaYerine)) : null;
  ol("KA-M1 mutant (it.ornek.kart || fallback kaldirildi) -> KA1 KIRMIZI (figur eski render'a doner)",
     !!kaMu && (kaMu.figur.src !== KART_URL || kaMu.figur.alt !== KART_ALT),
     JSON.stringify(kaMu && kaMu.figur));
}

console.log("IL) ① 'İleri' YOK (Okan 14 Eki 20:4x 'ileri butonunu sil'): ①'de foto-ileri gizli; kart tıklaması ②'ye geçer, ②'de İleri görünür");
{
  const ilKos = async (kaynak) => {
    const V = veriYukle(VERI_KAYNAK);
    const tur = (kod, ad) => ({ kod, ad, aciklama: "x", ornek_sayisi: 1, olculer: [{ mm: 120, fiyat_kurus: 44900 }] });
    const e = await ekranKos(kaynak, V, { acik: true, turler: [tur("plaket", "Plaket"), tur("figur", "Figür"), tur("anahtarlik", "Anahtarlık")] });
    const d = () => [...e.bolum.agac()];
    const id = (x) => d().find((n) => n.id === x) || null;
    const ileri = id("foto-ileri"), p1 = id("foto-pencere-1"), p2 = id("foto-pencere-2");
    const r = { ileriVar: !!ileri, ileriGizli1: !!ileri && ileri.hidden === true, p1Acik1: !!p1 && p1.hidden === false };
    const kart = d().filter((n) => n.tagName === "BUTTON" && n.getAttribute("data-kart") === "plaket")[0] || null;
    r.kartVar = !!kart;
    if (kart) kart.tetikle("click");
    r.p1Gizli2 = !!p1 && p1.hidden === true;
    r.p2Acik2 = !!p2 && p2.hidden === false;
    r.ileriGorunur2 = !!ileri && ileri.hidden === false;
    return r;
  };
  const s = await ilKos(EKRAN_KAYNAK);
  ol("IL1 ①'de foto-ileri GİZLİ (buton DOM'da durur, ②/③ için)", s.ileriVar && s.ileriGizli1 && s.p1Acik1, JSON.stringify(s));
  ol("IL2 kart tıklaması ②'ye geçer (① gizli, ② açık) ve ②'de İleri GÖRÜNÜR", s.kartVar && s.p1Gizli2 && s.p2Acik2 && s.ileriGorunur2, JSON.stringify(s));
  // MUTANT 1: ①'de gizleme geri alınır -> IL1 KIRMIZI.
  const c1 = "S.ileriBtn.hidden = S.pencere === 1 || S.pencere === 4;";
  const m1 = EKRAN_KAYNAK.split(c1).length === 2 ? await ilKos(EKRAN_KAYNAK.replace(c1, "S.ileriBtn.hidden = S.pencere === 4;")) : null;
  ol("IL-M1 mutant (① gizleme kaldırıldı) -> IL1 KIRMIZI", !!m1 && !m1.ileriGizli1, JSON.stringify(m1));
  // MUTANT 2: galeriSec sonundaki ②'ye geçiş silinir -> müşteri ①'de kalır (İleri de yok) -> IL2 KIRMIZI.
  const c2 = "if (S.adim === \"S1\") cizS1();\n    pencereGit(2);";
  const m2 = EKRAN_KAYNAK.split(c2).length === 2 ? await ilKos(EKRAN_KAYNAK.replace(c2, "if (S.adim === \"S1\") cizS1();")) : null;
  ol("IL-M2 mutant (kart tıklaması ②'ye geçmiyor) -> IL2 KIRMIZI", !!m2 && !(m2.p1Gizli2 && m2.p2Acik2), JSON.stringify(m2));
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
    s.ONIZLEMESIZ = !!kap && kap.hidden === false && [...kap.agac()].some((n) => n.tagName === "IMG" && /bust-2-render\.webp$/.test(n.src)) &&
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
    // R4 (RENK-ONIZLEME 10 Eki): palet turunun ③ renk secimi onizleme govdesinde (varsayilan ana renk Beyaz, Renkli degil).
    s.R4_RENK_GOVDE = e2.istekler.length === 1 && JSON.stringify(p0.govde.renkler) === '["Beyaz"]' && p0.govde.renkli === false;
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
  ol("R4 palet turu (bust) onizleme govdesinde renk alani: renkler [Beyaz] + renkli false", s0.R4_RENK_GOVDE, JSON.stringify(s0.iz.govde));
  ol("FM6 TEK onay kutusu 'foto-aydinlatma-onay' aydinlatma metninin ALTINDA, D turunde ve plakette GORUNUR; eski 2 kutu 0",
    s0.TEK_KUTU_FORM && s0.TEK_KUTU_PLAKET, JSON.stringify(s0));
  ol("FM7 kutu isaretsizken 'Önizleme oluştur' DISABLED, isaretlenince acilir; govdede aydinlatma_onay + surum (eski alan 0)",
    s0.KUTU_SART && s0.KUYRUK, JSON.stringify(s0));
  const FM_MUT = [
    ["FM-M1 istemci kendi dogrulamasi (her sey gecerli)", "return F.parametreDogrula(S.tur, parametreGovde());", "return { ok: true };", ["AYNI_FONKSIYON", "BOOL", "ILERI_FORM"]],
    ["FM-M2 onizleme-sonra metni dustu", "S.alanOnizlemeSonra.appendChild(el(\"p\", \"foto-uretim-ayrinti\", ONIZLEME_SONRA));", "", ["ONIZLEMESIZ"]],
    ["FM-M4 uretec onizleme yonlendirmesi silindi (saglayici yoluna duser)",
     // Saglayici yolunun govdesinde palet renkleri yok -> R4 de KIRMIZI (renk alani yalniz uretec govdesinde).
     "    if (!!(F && F.kolu && F.kolu(S.tur) === \"deterministik\")) { uretecOnizle(); return; }\n", "", ["KUYRUK", "R4_RENK_GOVDE"]],
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
    ["MR4 palet renkleri onizleme govdesine girmez",
     "      if (F.renkPaleti(S.tur)) { govde.renkler = paletRenkleri(S.tur); govde.renkli = renkliMi(); }\n", "", ["R4_RENK_GOVDE"]],
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
    // renk/ölçü ve tür notu #4 farklıdır. Anahtarlik'te yalnız kendi Ölçü cümlesi (C2); büst cümleleri görünmemeli.
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
     'F.girdiYeterli(S.tur, { foto: !!S.dosya, parametreler: parametreGovde(), cesit: cesitliTur() ? seciliCesit() : undefined }) === ""', "true",
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
  const m = await rku(EKRAN_KAYNAK.replace("    var secenek = (mr || F.ANA_RENKLER).slice();", "    var secenek = (mr || F.PLA_RENKLERI).slice();"));
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
  for (let i = 0; i < 8; i++) { await turVeOnay(fm, e2, k.d1); }
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
  ["M1 SINIR", "if (!muaf && ziyaretciSiniriVar(env) && sayi.kisi >= VERI.sinir_ziyaretci_24s) {", "if (false) {", "D"],
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
    for (let i = 0; i < 10; i++) { await turVeOnay(fm, e2, k.d1); }
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
    for (let i = 0; i < 14; i++) { await turVeOnay(fm, e2, k.d1); }
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
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is, okan_onay: true }) }), e2, Date.now(), null)).status;
  s.URET = (await uret(mus)) === 404 && (await uret(orn)) === 200;
  k.kapat();
  return s;
}
const GUNLUK_TAVAN = foto.GUNLUK_ONIZLEME_TAVANI;
const ORNEK_MUTANTLAR = [
  ["OM1 SEPET RED DALI SILINDI", "  if (ornekMi(is)) { return { hata: { hata: \"foto-onizleme-yok\" }, kod: 400 }; }\n", "", "SEPET"],
  ["OM2 DURUM RED DALI SILINDI",
   "  if (ornekMi(is)) { return fjson({ hata: \"bulunamadi\" }, 404); }\n  if (uretecOnizlemeIsi(is)) { return uretecDurumYaniti",
   "  if (uretecOnizlemeIsi(is)) { return uretecDurumYaniti", "DURUM"],
  ["OM3 GORSEL RED DALI SILINDI",
   "  if (ornekMi(is)) { return fjson({ hata: \"bulunamadi\" }, 404); }\n  // Uretec onizlemesi",
   "  // Uretec onizlemesi", "GORSEL"],
  ["OM4 TAVAN ORNEGI SAYAR", "WHERE tarih >= ? AND ziyaretci != ?\"", "WHERE tarih >= ? AND ? IS NOT NULL\"", "SINIR"],
  ["OM5 DOSYA ORNEK ISARETI DUSTU", "AND (i.ziyaretci = ? OR substr(u.is_no, 1, 12) = ?)\"",
   "AND (? IS NOT NULL OR ? IS NOT NULL)\"", "DOSYA"],
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

// ================================================================ OA — OKAN ONAYLI URETIM (13 Eki, para)

/**
 * POST /yonet/foto/onayli-uret {is, okan_onay:true}: ORNEK OLMAYAN hazir onizlemenin 3D zinciri, Okan onayiyla.
 * Donus {V1..V5} gecti mi (temiz SQLite; D1 cagrisi + saglayici cagrisi sayilir).
 *   V1 onay true + hazir musteri isi -> 200, ORNEK-<is ilk 12> satiri 1 ('build-baslat', renk tavani), siparis 0,
 *      Telegram onay satiri 1
 *   V2 onay YOK -> 403 okan-onayi-yok, D1 cagrisi 0, saglayici cagrisi 0
 *   V3 onay "true" (string) -> 403, D1 cagrisi 0
 *   V4 70 sa asimi -> 409 onizleme-suresi-doldu, satir 0
 *   V5 onayli isin 3MF'i panelden 200 · ORNEK- onekli ama ILGISIZ musteri isine bagli satir hala 404
 */
async function onayliSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  let d1Cagri = 0;
  const d1s = { prepare(sql) { d1Cagri++; return k.d1.prepare(sql); } };
  const r2b = r2Kur();
  const e2 = envKur(d1s, r2b);
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  const simdi = Date.now(), iso = new Date(simdi).toISOString();
  const eskiIso = new Date(simdi - (fm.ONIZLEME_KURULUM_SINIRI_SAAT + 1) * 3600000).toISOString();
  const onay = "c".repeat(32), red = "a".repeat(32), eski = "f".repeat(32);
  for (const [no, t] of [[onay, iso], [red, iso], [eski, eskiIso]]) {
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, '0123456789abcdef', ?, 'hazir', 'gorev-proto-7777', ?)")
      .bind(no, t, t).run();
  }
  const tg = [];
  const tgFn = async (_e, m) => { tg.push(m); };
  const uret = async (govde) => {
    const r = await fm.panelOnayliUret(new Request("https://pruvo3d.com/x", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e2, simdi, tgFn);
    return { kod: r.status, v: await r.json() };
  };
  const satir = async (is) => (await k.d1.prepare("SELECT siparis_no, asama, renk_sayisi FROM foto_uretim WHERE is_no = ?").bind(is).all()).results;
  const s = {}, ayrinti = {};
  // V2/V3 ONCE: temiz dunyada D1 + saglayici cagrisi sifir olmali.
  let d0 = d1Cagri, p0 = P.cagri.length;
  const v2 = await uret({ is: red });
  ayrinti.V2 = { kod: v2.kod, v: v2.v, d1: d1Cagri - d0, saglayici: P.cagri.length - p0 };
  s.V2 = v2.kod === 403 && v2.v.hata === "okan-onayi-yok" && d1Cagri - d0 === 0 && P.cagri.length - p0 === 0 &&
    (await satir(red)).length === 0;
  d0 = d1Cagri; p0 = P.cagri.length;
  const v3 = await uret({ is: red, okan_onay: "true" });
  ayrinti.V3 = { kod: v3.kod, d1: d1Cagri - d0, saglayici: P.cagri.length - p0 };
  s.V3 = v3.kod === 403 && v3.v.hata === "okan-onayi-yok" && d1Cagri - d0 === 0 && P.cagri.length - p0 === 0 &&
    (await satir(red)).length === 0;
  const v1 = await uret({ is: onay, okan_onay: true });
  const no = fm.ORNEK_SIPARIS_ONEK + onay.slice(0, 12);
  const sv1 = await satir(onay);
  const sip = await k.d1.prepare("SELECT COUNT(*) AS n FROM siparisler").first();
  ayrinti.V1 = { kod: v1.kod, v: v1.v, satir: sv1, siparis: sip.n, tg: tg.filter((m) => m.includes(no)).length };
  s.V1 = v1.kod === 200 && v1.v.siparis_no === no && v1.v.yeni === true && sv1.length === 1 &&
    sv1[0].siparis_no === no && sv1[0].siparis_no.startsWith("ORNEK-") && sv1[0].asama === "build-baslat" &&
    sv1[0].renk_sayisi === (VERI.renkTavani("plaket") || 4) && sip.n === 0 &&
    tg.filter((m) => m.includes(no) && m.includes("ONAYLI")).length === 1;
  const v4 = await uret({ is: eski, okan_onay: true });
  ayrinti.V4 = { kod: v4.kod, v: v4.v };
  s.V4 = v4.kod === 409 && v4.v.hata === "onizleme-suresi-doldu" && (await satir(eski)).length === 0;
  // V5: onayli satir 'hazir' + 3MF kovada -> indirilir; ilgisiz musteri isine bagli ORNEK- satiri 404.
  await k.d1.prepare("UPDATE foto_uretim SET asama = 'hazir' WHERE siparis_no = ?").bind(no).run();
  await r2b.put("foto/" + no + "/0/model.3mf", UCMF, {});
  const ilgisiz = "ORNEK-ilgisiz00001";
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES (?, 0, ?, 'plaket', 100, 'hazir', ?, ?)")
    .bind(ilgisiz, red, iso, iso).run();
  await r2b.put("foto/" + ilgisiz + "/0/model.3mf", UCMF, {});
  const dosya = async (n) => (await fm.panelFotoDosya(e2, new URL("https://pruvo3d.com/x?siparis_no=" + n + "&kalem=0&bicim=3mf"))).status;
  const d5a = await dosya(no), d5b = await dosya(ilgisiz);
  ayrinti.V5 = { onayli: d5a, ilgisiz: d5b };
  s.V5 = d5a === 200 && d5b === 404;
  k.kapat();
  return { s, ayrinti };
}
console.log("OA) OKAN ONAYLI URETIM (ornek disi hazir is, okan_onay:true)");
{
  const { s, ayrinti } = await onayliSenaryolar(foto);
  ol("V1 okan_onay:true + hazir ornek-disi is -> 200, foto_uretim satiri 1 (ORNEK-<is ilk 12>, build-baslat, renk tavani), siparis 0, Telegram onay 1",
     s.V1, JSON.stringify(ayrinti.V1));
  ol("V2 okan_onay YOK -> 403 okan-onayi-yok, D1 cagrisi 0, saglayici cagrisi 0", s.V2, JSON.stringify(ayrinti.V2));
  ol("V3 okan_onay:\"true\" (string) -> 403, D1 cagrisi 0", s.V3, JSON.stringify(ayrinti.V3));
  ol("V4 70 sa asimi -> 409 onizleme-suresi-doldu, satir 0", s.V4, JSON.stringify(ayrinti.V4));
  ol("V5 onayli isin 3MF'i 200 · ilgisiz musteri isine bagli ORNEK- satiri 404", s.V5, JSON.stringify(ayrinti.V5));
  // Rota: panel anahtarinin ARKASINDA (anahtarsiz 404); anahtarli + onaysiz 403.
  const rAnahtarsiz = await istek(env, "/yonet/foto/onayli-uret", { govde: { is: "c".repeat(32), okan_onay: true } });
  const rOnaysiz = await istek(env, "/yonet/foto/onayli-uret", { govde: { is: "c".repeat(32) }, basliklar: YONET });
  ol("V6 rota: anahtarsiz 404 · anahtarli+onaysiz 403 okan-onayi-yok",
     rAnahtarsiz.kod === 404 && rOnaysiz.kod === 403 && rOnaysiz.v && rOnaysiz.v.hata === "okan-onayi-yok",
     rAnahtarsiz.kod + "/" + rOnaysiz.kod);
}
const ONAYLI_MUTANTLAR = [
  ["OA-M1 BAYRAK KONTROLU SILINDI",
   "  if (!g || g.okan_onay !== true) { return fjson({ hata: \"okan-onayi-yok\" }, 403); }\n", "", ["V2", "V3"]],
  ["OA-M2 INDIRME KOSULU TUM ISLERE ACILDI", "AND (i.ziyaretci = ? OR substr(u.is_no, 1, 12) = ?)\"",
   "AND (? IS NOT NULL OR ? IS NOT NULL)\"", ["V5"]],
  ["OA-MK KONTROL", "Onay kaydi: semada sutun yok", "Onay kaydi:  semada sutun yok", []],
];
for (const [ad, capa, yerine, olmeli] of ONAYLI_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const { s } = await onayliSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 5 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s));
}

// ================================================================ SO — SIPARIS KALEMI OKAN ONAYI (13 Eki 21:0x, para)

/**
 * Odenen siparisin saglayici foto kalemi 'onay-bekliyor' acilir; 3D build YALNIZ POST /yonet/foto/siparis-onayla
 * (okan_onay:true) ile. Temiz SQLite; D1 + saglayici cagrisi sayilir. Donus {s, ayrinti}:
 *   S1 odenen siparis -> satir 'onay-bekliyor', 2 cron turunda saglayici cagrisi 0, "ONAYI BEKLİYOR" Telegram 1
 *   S2 onay ucu okan_onay:true -> 200 build-baslat (Telegram "OKAN ONAYLADI no/kalem"), 2. onay 409, yok 404;
 *      sonraki tur build POST 1, govdede input_task_id = onizleme gorevi
 *   S3 bayraksiz / "true" (string) -> 403, D1 cagrisi 0, saglayici 0, satir hala 'onay-bekliyor'
 *   S4 70 sa asan onizleme: cron 'elle' (onizleme-suresi-doldu, Telegram) · ucta 409 onizleme-suresi-doldu
 *   S5 hatirlatma: 48 sa esiginde TEK, 66 sa esiginde TEK (tekrar turlarinda yeni Telegram yok)
 *   S6 panelOrnekUret bayraksiz / "true" -> 403 + D1 0 + satir 0; okan_onay:true -> 200
 *   E3 ayni is icin ORNEK- satiri varken siparis satiri yine 'onay-bekliyor' + Telegram'da cift zincir notu +
 *      saticiFotoBilgileri ornek_no/notu; E2V Okan bilgisi is_no + uretim_notu + panel gorsel linki (anahtar YOK)
 */
async function siparisOnaySenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  let d1Cagri = 0;
  const d1s = { prepare(sql) { d1Cagri++; return k.d1.prepare(sql); } };
  const r2b = r2Kur();
  const e2 = envKur(d1s, r2b, OKAN_EPOSTA_ENV);
  const simdi = Date.now(), iso = new Date(simdi).toISOString();
  const saatOnce = (h) => new Date(simdi - h * 3600000).toISOString();
  const A = "5".repeat(32), B = "6".repeat(32), C = "7".repeat(32), D = "8".repeat(32), E = "9".repeat(32),
    O = "4".repeat(32);
  const NOT = "<b>kalın</b> & 'tırnak' çerçeve";
  for (const [is, yas, ziy, not] of [[A, 0, "0123456789abcdef", NOT], [B, fm.ONIZLEME_KURULUM_SINIRI_SAAT + 1, "0123456789abcdef", ""],
    [C, 1, "0123456789abcdef", ""], [D, fm.ONIZLEME_KURULUM_SINIRI_SAAT + 1, "0123456789abcdef", ""],
    [E, 0, "0123456789abcdef", ""], [O, 0, fm.ORNEK_ZIYARETCI, ""]]) {
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, uretim_notu)" +
      " VALUES (?, 'plaket', 100, ?, ?, 'hazir', ?, ?, ?)").bind(is, ziy, saatOnce(yas), "gorev-so-" + is.slice(0, 1), saatOnce(yas), not).run();
  }
  const kalemOf = (is) => [{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100, foto_renkler: ["Beyaz"],
    malzeme: "PLA", renk: "Beyaz" }];
  for (const [no, is] of [["PR-SO-A", A], ["PR-SO-B", B], ["PR-SO-C", C], ["PR-SO-E", E]]) {
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, iso, JSON.stringify(kalemOf(is))).run();
  }
  // E'nin ORNEK zinciri zaten uretilmis (hazir) — cron onu islemez.
  const ornekE = fm.ORNEK_SIPARIS_ONEK + E.slice(0, 12);
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES (?, 0, ?, 'plaket', 100, 'hazir', ?, ?)")
    .bind(ornekE, E, iso, iso).run();
  // D: onay bekleyen ama onizlemesi 70 sa'i asmis satir (cron'dan ONCE ucta 409).
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-SO-D', 0, ?, 'plaket', 100, 'onay-bekliyor', ?, ?)")
    .bind(D, iso, iso).run();
  const tg = [];
  const tgFn = async (_e, m) => { tg.push(m); };
  const onay = async (govde) => {
    const r = await fm.panelSiparisOnayla(new Request("https://pruvo3d.com/x", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e2, Date.now(), tgFn);
    return { kod: r.status, v: await r.json() };
  };
  const satir = async (no) => k.d1.prepare("SELECT asama, sebep, deneme FROM foto_uretim WHERE siparis_no = ? AND kalem = 0").bind(no).first();
  const tgSay = (parca, no) => tg.filter((m) => m.includes(parca) && m.includes(no)).length;
  const tur = async () => fm.fotoUretimTuru(e2, Date.now(), tgFn);
  const s = {}, ayrinti = {};

  const d4 = await onay({ siparis_no: "PR-SO-D", kalem: 0, okan_onay: true });
  const p0 = P.cagri.length;
  await tur(); await tur();
  const sA = await satir("PR-SO-A");
  ayrinti.S1 = { satir: sA, saglayici: P.cagri.slice(p0), tg: tgSay("OKAN ONAYI BEKLİYOR: PR-SO-A", "PR-SO-A") };
  s.S1 = !!sA && sA.asama === "onay-bekliyor" && P.cagri.length === p0 && ayrinti.S1.tg === 1;

  let d0 = d1Cagri, q0 = P.cagri.length;
  const s3a = await onay({ siparis_no: "PR-SO-A", kalem: 0 });
  const s3b = await onay({ siparis_no: "PR-SO-A", kalem: 0, okan_onay: "true" });
  const sA3 = await satir("PR-SO-A");
  // satir() sayilmayan k.d1'den okur -> fark yalniz uctan gelir.
  ayrinti.S3 = { a: s3a, b: s3b, d1: d1Cagri - d0, saglayici: P.cagri.length - q0, asama: sA3 && sA3.asama };
  s.S3 = s3a.kod === 403 && s3b.kod === 403 && s3a.v.hata === "okan-onayi-yok" && s3b.v.hata === "okan-onayi-yok" &&
    d1Cagri - d0 === 0 && P.cagri.length === q0 && !!sA3 && sA3.asama === "onay-bekliyor";

  const sB = await satir("PR-SO-B"), sD = await satir("PR-SO-D");
  const b4 = await onay({ siparis_no: "PR-SO-B", kalem: 0, okan_onay: true });
  ayrinti.S4 = { B: sB, D: sD, d4, b4, tg: tgSay("ELLE BAKILACAK", "PR-SO-B") };
  s.S4 = !!sB && sB.asama === "elle" && sB.sebep === "onizleme-suresi-doldu" && ayrinti.S4.tg === 1 &&
    d4.kod === 409 && d4.v.hata === "onizleme-suresi-doldu" && b4.kod === 409 && b4.v.hata === "onay-beklemiyor";

  // C taze acildi (acilis e-postasi); 48 sa esigi -> TEK hatirlatma, 66 sa esigi -> TEK hatirlatma.
  await k.d1.prepare("UPDATE foto_isler SET hazir_tarih = ? WHERE is_no = ?").bind(saatOnce(49), C).run();
  await tur(); await tur();
  const h1 = tgSay("hatırlatma", "PR-SO-C"), c1 = await satir("PR-SO-C");
  await k.d1.prepare("UPDATE foto_isler SET hazir_tarih = ? WHERE is_no = ?").bind(saatOnce(67), C).run();
  await tur(); await tur();
  const h2 = tgSay("hatırlatma", "PR-SO-C"), c2 = await satir("PR-SO-C");
  ayrinti.S5 = { h1, c1, h2, c2, A: tgSay("hatırlatma", "PR-SO-A") };
  s.S5 = h1 === 1 && c1 && c1.deneme === 1 && c1.asama === "onay-bekliyor" && h2 === 2 && c2 && c2.deneme === 2 &&
    c2.asama === "onay-bekliyor" && ayrinti.S5.A === 0;

  const sE = await satir("PR-SO-E");
  const bilgiE = await fm.saticiFotoBilgileri(e2, "PR-SO-E", kalemOf(E));
  const notluTg = tg.filter((m) => m.includes("PR-SO-E") && m.includes("bu iş için zaten üretim var: " + ornekE)).length;
  ayrinti.E3 = { satir: sE, tg: notluTg, bilgi: bilgiE };
  s.E3 = !!sE && sE.asama === "onay-bekliyor" && notluTg === 1 && bilgiE.length === 1 && bilgiE[0].ornek_no === ornekE &&
    bilgiE[0].cift_zincir_notu === "bu iş için zaten üretim var: " + ornekE;
  const bilgiA = await fm.saticiFotoBilgileri(e2, "PR-SO-A", kalemOf(A));
  const bA = bilgiA[0] || {};
  ayrinti.E2V = bilgiA;
  s.E2V = bilgiA.length === 1 && bA.is_no === A && bA.uretim_notu === NOT && bA.onay_gerekli === true && bA.ornek_no === "" &&
    bA.gorsel === "https://pruvo3d.com/api/shop/yonet/foto-dosya?siparis_no=PR-SO-A&kalem=0&bicim=onizleme" &&
    !bA.gorsel.includes(e2.YONET_ANAHTAR) && bA.malzeme === "PLA" && bA.renk === "Beyaz";

  const b0 = P.cagri.filter((c) => /\/v1\/build$/.test(c)).length;
  const s2 = await onay({ siparis_no: "PR-SO-A", kalem: 0, okan_onay: true });
  const sA2 = await satir("PR-SO-A");
  const s2b = await onay({ siparis_no: "PR-SO-A", kalem: 0, okan_onay: true });
  const s2c = await onay({ siparis_no: "PR-SO-Z", kalem: 0, okan_onay: true });
  P.sonBuild = null;
  await tur();
  const b1 = P.cagri.filter((c) => /\/v1\/build$/.test(c)).length;
  ayrinti.S2 = { s2, asama: sA2 && sA2.asama, s2b: s2b.kod, s2c: s2c.kod, build: b1 - b0, govde: P.sonBuild,
                 tg: tgSay("OKAN ONAYLADI PR-SO-A/0", "PR-SO-A") };
  s.S2 = s2.kod === 200 && s2.v.asama === "build-baslat" && !!sA2 && sA2.asama === "build-baslat" && s2b.kod === 409 &&
    s2c.kod === 404 && b1 - b0 === 1 && !!P.sonBuild && P.sonBuild.input_task_id === "gorev-so-5" && ayrinti.S2.tg === 1;

  d0 = d1Cagri; q0 = P.cagri.length;
  const ornekUret = async (govde) => (await fm.panelOrnekUret(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e2, Date.now(), null));
  const o1 = await ornekUret({ is: O }), o2 = await ornekUret({ is: O, okan_onay: "true" });
  const od1 = d1Cagri - d0, osag = P.cagri.length - q0;
  const oSatir0 = (await k.d1.prepare("SELECT COUNT(*) AS n FROM foto_uretim WHERE is_no = ?").bind(O).first()).n;
  const o3 = await ornekUret({ is: O, okan_onay: true });
  const oSatir1 = (await k.d1.prepare("SELECT COUNT(*) AS n FROM foto_uretim WHERE is_no = ?").bind(O).first()).n;
  ayrinti.S6 = { o1: o1.status, o2: o2.status, d1: od1, saglayici: osag, oSatir0, o3: o3.status, oSatir1 };
  s.S6 = o1.status === 403 && o2.status === 403 && od1 === 0 && osag === 0 && oSatir0 === 0 && o3.status === 200 && oSatir1 === 1;
  k.kapat();
  return { s, ayrinti };
}
console.log("SO) SIPARIS KALEMI OKAN ONAYI (onay-bekliyor -> siparis-onayla -> build-baslat)");
{
  const { s, ayrinti } = await siparisOnaySenaryolar(foto);
  ol("S1 odenen siparis -> 'onay-bekliyor', 2 cron turunda saglayici cagrisi 0, ONAYI BEKLİYOR Telegram 1", s.S1, JSON.stringify(ayrinti.S1));
  ol("S2 okan_onay:true -> 200 build-baslat + 'OKAN ONAYLADI no/kalem' · 2. onay 409 · yok 404 · sonraki tur build POST 1, input_task_id = onizleme gorevi",
     s.S2, JSON.stringify(ayrinti.S2));
  ol("S3 bayraksiz / \"true\" -> 403, D1 cagrisi 0, saglayici 0, satir onay-bekliyor", s.S3, JSON.stringify(ayrinti.S3));
  ol("S4 70 sa asan onay-bekliyor -> cron 'elle' onizleme-suresi-doldu (Telegram 1) · ucta 409", s.S4, JSON.stringify(ayrinti.S4));
  ol("S5 hatirlatma 48 sa TEK + 66 sa TEK (tekrar turunda yeni Telegram yok, deneme 1 -> 2)", s.S5, JSON.stringify(ayrinti.S5));
  ol("S6 panelOrnekUret bayraksiz / \"true\" -> 403 + D1 0 + satir 0 · okan_onay:true -> 200", s.S6, JSON.stringify(ayrinti.S6));
  ol("E3 ORNEK zinciri varken siparis satiri yine onay-bekliyor + Telegram cift zincir notu + Okan bilgisinde ornek_no",
     s.E3, JSON.stringify(ayrinti.E3));
  ol("E2V Okan bilgisi: is_no + uretim_notu + panel onizleme linki (anahtar URL'de YOK) + malzeme/renk", s.E2V, JSON.stringify(ayrinti.E2V));
  // Rota: panel anahtarinin ARKASINDA (anahtarsiz 404) · anahtarli+bayraksiz 403 · MAKINE_UCLARI DISI.
  const rAnahtarsiz = await istek(env, "/yonet/foto/siparis-onayla", { govde: { siparis_no: "PR-SO-A", kalem: 0, okan_onay: true } });
  const rOnaysiz = await istek(env, "/yonet/foto/siparis-onayla", { govde: { siparis_no: "PR-SO-A", kalem: 0 }, basliklar: YONET });
  const yonetKaynak = fs.readFileSync(path.join(SHOP, "src", "yonet.js"), "utf8");
  const makine = /const MAKINE_UCLARI = \[([^\]]*)\]/.exec(yonetKaynak);
  ol("S7 rota: anahtarsiz 404 · anahtarli+bayraksiz 403 · MAKINE_UCLARI'nda siparis-onayla YOK",
     rAnahtarsiz.kod === 404 && rOnaysiz.kod === 403 && !!makine && !makine[1].includes("siparis-onayla"),
     rAnahtarsiz.kod + "/" + rOnaysiz.kod);
}
const SIPARIS_ONAY_MUTANTLAR = [
  ["SO-M1 ODENEN KALEM YINE build-baslat", "det ? \"uretec-bekliyor\" : ONAY_BEKLIYOR,", "det ? \"uretec-bekliyor\" : \"build-baslat\",",
   ["E3", "S1", "S2", "S3", "S5"]],
  ["SO-M2 ONAY UCUNDA BAYRAK KONTROLU SILINDI",
   "  if (!g || g.okan_onay !== true) { return fjson({ hata: \"okan-onayi-yok\", yol: \"siparis\" }, 403); }\n", "", ["S2", "S3"]],
  ["SO-MK KONTROL", "// Deterministik kol (uretec) saglayici kredisi harcamaz", "// Deterministik  kol (uretec) saglayici kredisi harcamaz", []],
];
for (const [ad, capa, yerine, olmeli] of SIPARIS_ONAY_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const { s } = await siparisOnaySenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 8 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kirmizilar));
}

// ================================================================ OE — OKAN ONAY E-POSTASI (Okan Telegram KULLANMIYOR, 13 Eki)

/**
 * onay-bekliyor olaylari Okan'a E-POSTA (alici YALNIZ BILDIRIM_EPOSTA; musteri e-postasi 0). Temiz SQLite; sahte Resend.
 *   T1 odenen foto siparisi -> Okan e-postasi 1 (alici BILDIRIM_EPOSTA, govdede is_no + "Onayla (3D üret)" + kalan sure),
 *      musteri e-postasi 0; ikinci tur ek e-posta 0
 *   T2 48 sa -> hatirlatma e-postasi 1, ayni tur tekrar -> 0 ek (deneme 1)
 *   T3 66 sa -> hatirlatma e-postasi 1 daha, tekrar -> 0 ek (deneme 2)
 *   T4 70 sa asimi -> 'elle' + "süre doldu" e-postasi 1, tekrar -> 0 ek
 *   T5 gonderim hatasi -> isaret ARTMAZ (deneme / acilis / sure-doldu), asama ilerlemesi bozulmaz (onay-bekliyor acilir,
 *      70 sa satiri 'elle'ye duser), Telegram uyari olay basina 1; sonraki basarili turda HER olay TEK e-posta
 *   T6 "Nasıl olsun?" notu govdede HTML KACISLI (ham etiket 0)
 */
async function onayEpostaSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur(), OKAN_EPOSTA_ENV);
  const simdi = Date.now();
  const saatOnce = (h) => new Date(simdi - h * 3600000).toISOString();
  const NOT = "<script>x</script> & 'tırnak' <b>kalın</b>";
  const N = { A: "a1".repeat(16), C: "c1".repeat(16), B: "b1".repeat(16), G: "d1".repeat(16), H: "e1".repeat(16), I: "f1".repeat(16) };
  const isEkle = async (is, yas, not) => k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih," +
    " uretim_notu) VALUES (?, 'plaket', 100, '0123456789abcdef', ?, 'hazir', ?, ?, ?)").bind(is, saatOnce(yas), "gorev-oe-" + is.slice(0, 2),
    saatOnce(yas), not || "").run();
  const sipEkle = async (no, is) => k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler, musteri_eposta)" +
    " VALUES (?, ?, 'odendi', 1, ?, 'musteri@ornek.test')").bind(no, new Date(simdi).toISOString(), JSON.stringify([{ id: "ozel-foto-plaket",
    foto_is: is, foto_tur: "plaket", olcu_mm: 100, foto_renkler: ["Beyaz"], malzeme: "PLA", renk: "Beyaz" }])).run();
  const yasla = async (is, h) => k.d1.prepare("UPDATE foto_isler SET hazir_tarih = ? WHERE is_no = ?").bind(saatOnce(h), is).run();
  for (const [ad, yas, not] of [["A", 0, NOT], ["C", 0, ""], ["B", 0, ""], ["I", 0, ""]]) { await isEkle(N[ad], yas, not); await sipEkle("PR-OE-" + ad, N[ad]); }
  const tg = [];
  const tgFn = async (_e, m) => { tg.push(m); };
  const tur = async () => fm.fotoUretimTuru(e2, Date.now(), tgFn);
  const satir = async (no) => k.d1.prepare("SELECT asama, sebep, deneme FROM foto_uretim WHERE siparis_no = ? AND kalem = 0").bind(no).first();
  const ep0 = P.eposta.length;
  const ep = () => P.eposta.slice(ep0);
  const gitti = (parca, no) => ep().filter((m) => m.kod < 300 && m.subject.includes(parca) && m.subject.includes(no + "/0")).length;
  const s = {}, ayrinti = {};

  await tur();
  const t1a = gitti("3D üretim onayı bekliyor", "PR-OE-A");
  await tur();
  const mA = ep().filter((m) => m.subject.includes("PR-OE-A/0"));
  const mA0 = mA[0] || { html: "", to: [] };
  const musteri = ep().filter((m) => JSON.stringify(m.to) !== JSON.stringify([OKAN_EPOSTA])).length;
  ayrinti.T1 = { t1a, n: mA.length, to: mA0.to, konu: mA0.subject, musteri, hepsi: ep().map((m) => m.subject) };
  s.T1 = t1a === 1 && mA.length === 1 && JSON.stringify(mA0.to) === JSON.stringify([OKAN_EPOSTA]) && musteri === 0 &&
    mA0.subject === "3D üretim onayı bekliyor: PR-OE-A/0" && mA0.html.includes(N.A) && mA0.html.includes("Onayla (3D üret)") &&
    /Kalan süre:<\/b> (69|70) sa/.test(mA0.html) && ep().filter((m) => m.subject.includes("Hatırlatma")).length === 0;
  ayrinti.T6 = mA0.html.slice(mA0.html.indexOf("Nasıl olsun?"), mA0.html.indexOf("Nasıl olsun?") + 200);
  s.T6 = mA0.html.includes("&lt;script&gt;x&lt;/script&gt; &amp; &#39;tırnak&#39; &lt;b&gt;kalın&lt;/b&gt;") &&
    !mA0.html.includes("<script>") && !mA0.html.includes("<b>kalın</b>");

  await yasla(N.C, 49); await tur();
  const t2a = gitti("Hatırlatma (49 sa)", "PR-OE-C");
  await tur();
  const t2b = ep().filter((m) => m.subject.startsWith("Hatırlatma") && m.subject.includes("PR-OE-C/0")).length, c2 = await satir("PR-OE-C");
  ayrinti.T2 = { t2a, t2b, c2 };
  s.T2 = t2a === 1 && t2b === 1 && !!c2 && c2.deneme === 1 && c2.asama === "onay-bekliyor";

  await yasla(N.C, 67); await tur();
  const t3a = gitti("Hatırlatma (67 sa)", "PR-OE-C");
  await tur();
  const t3b = ep().filter((m) => m.subject.startsWith("Hatırlatma") && m.subject.includes("PR-OE-C/0")).length, c3 = await satir("PR-OE-C");
  ayrinti.T3 = { t3a, t3b, c3 };
  s.T3 = t3a === 1 && t3b === 2 && !!c3 && c3.deneme === 2 && c3.asama === "onay-bekliyor";

  await yasla(N.B, fm.ONIZLEME_KURULUM_SINIRI_SAAT + 1); await tur();
  const t4a = gitti("onay süresi doldu", "PR-OE-B");
  await tur();
  const t4b = gitti("onay süresi doldu", "PR-OE-B"), b4 = await satir("PR-OE-B");
  ayrinti.T4 = { t4a, t4b, b4 };
  s.T4 = t4a === 1 && t4b === 1 && !!b4 && b4.asama === "elle" && b4.sebep === "onizleme-suresi-doldu";

  // T5: hata penceresi — G yeni acilir (acilis e-postasi), H 70 sa'i asar (sure doldu), I 48 sa esigine girer (hatirlatma).
  // H once BASARILI acilir (acilis e-postasi gitti); G hata penceresinde ILK kez acilir.
  await isEkle(N.H, 0, ""); await sipEkle("PR-OE-H", N.H); await tur();
  await isEkle(N.G, 0, ""); await sipEkle("PR-OE-G", N.G);
  await yasla(N.H, fm.ONIZLEME_KURULUM_SINIRI_SAAT + 1); await yasla(N.I, 49);
  const tg0 = tg.length, h0 = ep().length;
  P.epostaKod = 500;
  try { await tur(); await tur(); } finally { P.epostaKod = 200; }
  const hataAn = { G: await satir("PR-OE-G"), H: await satir("PR-OE-H"), I: await satir("PR-OE-I"),
    deneme: ep().slice(h0).length, uyari: tg.slice(tg0).filter((m) => m.includes("Okan e-postası gönderilemedi")).length };
  await tur();
  const sonra = { G: gitti("3D üretim onayı bekliyor", "PR-OE-G"), H: gitti("onay süresi doldu", "PR-OE-H"),
    I: gitti("Hatırlatma (49 sa)", "PR-OE-I"), Is: await satir("PR-OE-I") };
  await tur();
  const tekrar = { G: gitti("3D üretim onayı bekliyor", "PR-OE-G"), H: gitti("onay süresi doldu", "PR-OE-H"),
    I: ep().filter((m) => m.kod < 300 && m.subject.startsWith("Hatırlatma") && m.subject.includes("PR-OE-I/0")).length };
  ayrinti.T5 = { hataAn, sonra, tekrar };
  s.T5 = !!hataAn.G && hataAn.G.asama === "onay-bekliyor" && !!hataAn.H && hataAn.H.asama === "elle" &&
    hataAn.H.sebep === "onizleme-suresi-doldu" && !!hataAn.I && hataAn.I.deneme === 0 && hataAn.I.asama === "onay-bekliyor" &&
    hataAn.deneme === 6 && hataAn.uyari === 3 &&
    sonra.G === 1 && sonra.H === 1 && sonra.I === 1 && !!sonra.Is && sonra.Is.deneme === 1 &&
    tekrar.G === 1 && tekrar.H === 1 && tekrar.I === 1;
  k.kapat();
  return { s, ayrinti };
}
console.log("OE) OKAN ONAY E-POSTASI (acilis · 48/66 sa hatirlatma · 70 sa sure doldu · hata -> yeniden deneme)");
{
  const { s, ayrinti } = await onayEpostaSenaryolar(foto);
  ol("T1 odenen foto siparisi -> Okan e-postasi 1 (alici BILDIRIM_EPOSTA, is_no + \"Onayla (3D üret)\" + kalan sure), musteri e-postasi 0",
     s.T1, JSON.stringify(ayrinti.T1));
  ol("T2 48 sa -> hatirlatma e-postasi 1, tekrar tur 0 ek (deneme 1)", s.T2, JSON.stringify(ayrinti.T2));
  ol("T3 66 sa -> hatirlatma e-postasi 1, tekrar tur 0 ek (deneme 2)", s.T3, JSON.stringify(ayrinti.T3));
  ol("T4 70 sa asimi -> 'elle' + \"süre doldu\" e-postasi 1, tekrar 0 ek", s.T4, JSON.stringify(ayrinti.T4));
  ol("T5 gonderim hatasi -> isaret artmaz, asama bozulmaz, Telegram uyari olay basina 1; sonraki tur TEK e-posta",
     s.T5, JSON.stringify(ayrinti.T5));
  ol("T6 \"Nasıl olsun?\" notu govdede HTML KACISLI", s.T6, JSON.stringify(ayrinti.T6));
}
/**
 * OB) OKAN BILDIRIM SINIFI (13 Eki — Okan Telegram KULLANMIYOR): EYLEM/GOZ Telegram satirlari ayni metinle Okan'a
 * (YALNIZ BILDIRIM_EPOSTA) e-posta da gider (eposta.js okanaBildir). Temiz SQLite; sahte Resend.
 *   B4 kredi havuzu KAPANDI -> "[PRUVO EYLEM]" e-postasi 1; ayni durum 2. tur 0 ek; ayni gun acilip tekrar kapanir
 *      (salinim) -> Telegram 2. satir VAR, e-posta 0 ek (anahtar tekrari onler)
 *   B5 elleDusur (onizleme-yok) -> EYLEM e-postasi 1, Telegram satiri AYNEN
 *   B6 GOZ (panel siparis-onayla "OKAN ONAYLADI") -> "[PRUVO GÖZ]" e-postasi 1
 *   B7 Resend 500 -> akis bozulmaz (asama 'elle'), dongu yok (olay basina TEK deneme, ek Telegram 0),
 *      /yonet/foto-ozet `bildirim_son_hata` kaydi; epostaAkisi hatasi da ayni kayda (ikinci e-posta denemesi 0)
 *   B8 onay-bekliyor olayi hala TEK e-posta (onay e-postasi 1, "[PRUVO" e-postasi 0); 70 sa sure-doldu "[PRUVO" 0
 *   B9 butun bu e-postalarda musteri adresine 0
 */
async function okanBildirimSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur(), OKAN_EPOSTA_ENV);
  const em = await import(url.pathToFileURL(path.join(SHOP, "src", "eposta.js")).href);
  const T0 = Date.parse("2026-10-13T08:00:00.000Z");
  const iso = (t) => new Date(t).toISOString();
  const tg = [];
  const tgFn = async (_e, m) => { tg.push(m); };
  const ep0 = P.eposta.length;
  const ep = () => P.eposta.slice(ep0);
  const okan = (onek, parca) => ep().filter((m) => m.kod < 300 && m.subject.startsWith(onek) && m.subject.includes(parca)).length;
  const ayar = (a, d, t) => k.d1.prepare("INSERT INTO foto_ayar (anahtar, deger, guncel) VALUES (?, ?, ?)" +
    " ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger, guncel = excluded.guncel").bind(a, String(d), t).run();
  const s = {}, a = {};

  // B4 — havuz kapandi / ayni durum / ayni gun salinim
  await ayar("bakiye", 0, T0); await fm.havuzHukmu(e2, T0, tgFn);
  const b4a = okan("[PRUVO EYLEM]", "kredi havuzu");
  await fm.havuzHukmu(e2, T0 + 1000, tgFn);
  const b4b = okan("[PRUVO EYLEM]", "kredi havuzu");
  await ayar("bakiye", 100000, T0 + 2000); await fm.havuzHukmu(e2, T0 + 2000, tgFn);
  await ayar("bakiye", 0, T0 + 3000); await fm.havuzHukmu(e2, T0 + 3000, tgFn);
  const b4c = okan("[PRUVO EYLEM]", "kredi havuzu"), b4tg = tg.filter((m) => m.includes("bölümü KAPANDI")).length;
  a.B4 = { b4a, b4b, b4c, b4tg };
  s.B4 = b4a === 1 && b4b === 1 && b4c === 1 && b4tg === 2;

  // B5 — elleDusur (onizleme-yok): onay bekleyen satirin onizlemesi hazir degil
  const satirEkle = async (no, is) => {
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, 'plaket', 100," +
      " '0123456789abcdef', ?, 'onizleme')").bind(is, iso(Date.now())).run();
    await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)" +
      " VALUES (?, 0, ?, 'plaket', 100, 'onay-bekliyor', ?, ?)").bind(no, is, iso(Date.now()), iso(Date.now())).run();
  };
  await satirEkle("PR-OB-E", "e5".repeat(16));
  const tg5 = tg.length;
  await fm.fotoUretimTuru(e2, Date.now(), tgFn);
  const e5 = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-OB-E'").first();
  const b5 = okan("[PRUVO EYLEM]", "PR-OB-E/0"), b5tg = tg.slice(tg5).filter((m) => m.includes("ELLE BAKILACAK: PR-OB-E")).length;
  const m5 = ep().find((m) => m.subject.includes("PR-OB-E/0")) || { html: "", to: [] };
  a.B5 = { e5, b5, b5tg, konu: m5.subject };
  s.B5 = !!e5 && e5.asama === "elle" && e5.sebep === "onizleme-yok" && b5 === 1 && b5tg === 1 &&
    m5.html.includes("ELLE BAKILACAK: PR-OB-E kalem 0") && JSON.stringify(m5.to) === JSON.stringify([OKAN_EPOSTA]);

  // B6 + B8 — odenen foto siparisi -> onay-bekliyor (onay e-postasi TEK) -> panel onayi (GOZ e-postasi 1)
  const isG = "a6".repeat(16);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih)" +
    " VALUES (?, 'plaket', 100, '0123456789abcdef', ?, 'hazir', 'gorev-ob', ?)").bind(isG, iso(Date.now()), iso(Date.now())).run();
  await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler, musteri_eposta)" +
    " VALUES ('PR-OB-G', ?, 'odendi', 1, ?, 'musteri@ornek.test')").bind(iso(Date.now()), JSON.stringify([{ id: "ozel-foto-plaket",
    foto_is: isG, foto_tur: "plaket", olcu_mm: 100, foto_renkler: ["Beyaz"], malzeme: "PLA", renk: "Beyaz" }])).run();
  await fm.fotoUretimTuru(e2, Date.now(), tgFn); await fm.fotoUretimTuru(e2, Date.now(), tgFn);
  const b8 = { onay: ep().filter((m) => m.subject.includes("PR-OB-G/0") && m.subject.includes("onayı bekliyor")).length,
               pruvo: ep().filter((m) => m.subject.startsWith("[PRUVO") && m.subject.includes("PR-OB-G")).length,
               tg: tg.filter((m) => m.includes("OKAN ONAYI BEKLİYOR: PR-OB-G")).length };
  const y6 = await fm.panelSiparisOnayla(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ siparis_no: "PR-OB-G", kalem: 0, okan_onay: true }) }), e2, Date.now(), tgFn);
  const b6 = okan("[PRUVO GÖZ]", "PR-OB-G/0"), b6tg = tg.filter((m) => m.includes("OKAN ONAYLADI PR-OB-G/0")).length;
  a.B6 = { kod: y6.status, b6, b6tg }; a.B8 = b8;
  s.B6 = y6.status === 200 && b6 === 1 && b6tg === 1;
  s.B8 = b8.onay === 1 && b8.pruvo === 0;

  // B7 — Resend 500: akis bozulmaz, dongu yok, panel kaydi
  await satirEkle("PR-OB-H", "b7".repeat(16));
  const h0 = ep().length, tg7 = tg.length;
  P.epostaKod = 500;
  let firladi = "";
  try { await fm.fotoUretimTuru(e2, Date.now(), tgFn); } catch (e) { firladi = String((e && e.message) || e); }
  finally { P.epostaKod = 200; }
  const h7 = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-OB-H'").first();
  const deneme7 = ep().slice(h0).filter((m) => m.subject.includes("PR-OB-H")).length;
  const tgEk7 = tg.slice(tg7).length;
  const oz = await istek(e2, "/yonet/foto-ozet", { basliklar: YONET });
  const bh = oz.v && oz.v.bildirim_son_hata;
  P.epostaKod = 500;
  const tgA = [], h1 = ep().length;
  try { await em.epostaAkisi(e2, async (_e, m) => { tgA.push(m); }, "PR-OB-AKIS",
    [{ kime: OKAN_EPOSTA, konu: "x", html: "<p>x</p>", etiket: "satici" }]); } catch (e) { firladi += " akis:" + e.message; }
  finally { P.epostaKod = 200; }
  const oz2 = await istek(e2, "/yonet/foto-ozet", { basliklar: YONET });
  const bh2 = oz2.v && oz2.v.bildirim_son_hata;
  a.B7 = { firladi, h7, deneme7, tgEk7, bh, akisDeneme: ep().slice(h1).length, tgA: tgA.length, bh2 };
  s.B7 = !firladi && !!h7 && h7.asama === "elle" && deneme7 === 1 && tgEk7 === 1 &&
    !!bh && /PR-OB-H/.test(bh.kaynak) && /resend-500/.test(bh.hata) &&
    a.B7.akisDeneme === 1 && tgA.length === 1 && !!bh2 && /PR-OB-AKIS/.test(bh2.kaynak) && /resend-500/.test(bh2.hata);

  // B9 — bu senaryodaki HICBIR e-posta musteri adresine gitmedi
  const musteri = ep().filter((m) => JSON.stringify(m.to) !== JSON.stringify([OKAN_EPOSTA])).length;
  a.B9 = { musteri, toplam: ep().length };
  s.B9 = musteri === 0 && ep().length > 0;
  k.kapat();
  return { s, a };
}
console.log("OB) OKAN BILDIRIM SINIFI (EYLEM/GOZ Telegram -> Okan e-postasi; tekrar onleme; kanal hatasi panel kaydi)");
{
  const { s, a } = await okanBildirimSenaryolar(foto);
  ol("OB-B4 kredi havuzu KAPANDI -> EYLEM e-postasi 1; ayni durum 2. tur 0 ek; ayni gun salinim 0 ek (Telegram 2)", s.B4, JSON.stringify(a.B4));
  ol("OB-B5 elleDusur (onizleme-yok) -> EYLEM e-postasi 1 (alici BILDIRIM_EPOSTA), Telegram AYNEN", s.B5, JSON.stringify(a.B5));
  ol("OB-B6 GOZ (panel siparis-onayla) -> \"[PRUVO GÖZ]\" e-postasi 1", s.B6, JSON.stringify(a.B6));
  ol("OB-B7 Resend 500 -> akis bozulmaz, olay basina TEK deneme, ek Telegram 0; panel bildirim_son_hata (okanaBildir + epostaAkisi)",
     s.B7, JSON.stringify(a.B7));
  ol("OB-B8 onay-bekliyor olayi TEK e-posta (onay e-postasi 1, \"[PRUVO\" 0)", s.B8, JSON.stringify(a.B8));
  ol("OB-B9 Okan bildirimlerinde musteri adresine e-posta 0", s.B9, JSON.stringify(a.B9));
}
const ONAY_EPOSTA_MUTANTLAR = [
  ["OE-M1 ACILIS E-POSTASI CAGRISI KALKTI", "const gitti = await okanEpostasi(env, acAnahtar, acildi, ac, simdi, telegram);",
   "const gitti = false;", ["T1", "T2", "T3", "T5", "T6"]],
  ["OE-M2 HATIRLATMA E-POSTASI KALKTI (yalniz Telegram)",
   "const gitti = await okanEpostasi(env, anahtar, await ayarOku(env, anahtar), hat, simdi, telegram);", "const gitti = true;",
   ["T2", "T3", "T5"]],
  ["OE-M3 ISARET GONDERIMDEN ONCE ARTAR",
   "      const gitti = await okanEpostasi(env, anahtar, await ayarOku(env, anahtar), hat, simdi, telegram);",
   "      await hatirlatmaIsaretle(env, u, once, hedef);\n      const gitti = await okanEpostasi(env, anahtar, await ayarOku(env, anahtar), hat, simdi, telegram);",
   ["T5"]],
  ["OE-MK KONTROL", "// E-posta asagidaki sure-doldu turunda", "// E-posta  asagidaki sure-doldu turunda", []],
];
for (const [ad, capa, yerine, olmeli] of ONAY_EPOSTA_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const { s } = await onayEpostaSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 6 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kirmizilar));
}

const OLCEK_MUTANTLAR = [
  ["OM-A OLCU KAPISI ATLANDI", "const olc = await ucmfOlcekle(ucmf.tampon, VERI.olcekHedefMm(u.olcu_mm));",
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
    for (let i = 0; i < 8; i++) { await turVeOnay(fm, e2, k.d1); }
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
      // 6 MODEL: figur turu model koduyla acilir (tur satiri tek basina acmaz); is satiri alt_tur 'insan' tasir.
      for (const a of (t === "figur" ? ["insan"] : [t])) {
        await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, 'x')").bind(a).run();
      }
    }
    let no = 0;
    const isKur = async (tur, parametreler) => {
      const is = (++no).toString(16).padStart(32, "a");
      const asama = fm.uretecOnizlemeTuru(tur) ? "onizleme-hazir" : "hazir";
      await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, ?, 100, 'z', ?, ?, 'gorev-rkk', ?)")
        .bind(is, tur, new Date().toISOString(), asama, new Date().toISOString()).run();
      if (tur === "figur") { await k.d1.prepare("UPDATE foto_isler SET alt_tur = 'insan' WHERE is_no = ?").bind(is).run(); }
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

/**
 * RENK-ONIZLEME (Okan 10 Eki): ③'te secilen palet renkleri /foto/onizleme girdi.json'unda bolgelere sirayla
 * (uretecGirdiJson ile AYNI esleme) — vaka: bust Renkli "Ahşap, Beyaz" onizlemesi `renkler:{}` ile TEK renk basildi.
 * R1 bust Renkli 2 renk -> {taban, rolyef} · R2 bust Gri -> {taban:"Gri"} · R3 yapboz Renkli 4 -> renk1..4 ·
 * KURAL bozuk renk 400 (ana renkte 2 renk / tavan asimi / palet disi), eski istemci (alan yok) 200 + {}.
 */
async function onizlemeRenkSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const r2 = r2Kur();
  const yazilan = new Map(), asilPut = r2.put;
  r2.put = async (a, v, o) => { if (typeof v === "string") { yazilan.set(a, v); } return asilPut(a, v, o); };
  const e2 = envKur(k.d1, r2);
  const yedek = VERI.ornekler.splice(0);
  const s = {};
  let ipNo = 0;
  const varsayilan = (tur) => {
    const p = {}, f = VERI.turBul(tur).form || {};
    for (const a of Object.keys(f)) { if (f[a].varsayilan !== undefined) { p[a] = f[a].varsayilan; } }
    return p;
  };
  const malzeme = (tur) => {
    const m = {}, mb = VERI.turBul(tur).malzemeler || {};
    for (const b of Object.keys(mb)) { m[b + "_malzeme"] = mb[b][0]; }
    return m;
  };
  const onizle = async (tur, olcu, ek) => {
    const govde = { ...onizlemeGovde({ tur, olcu_mm: olcu, parametreler: varsayilan(tur), secim: malzeme(tur) }), ...ek };
    const u = "https://pruvo3d.com/api/shop/foto/onizleme";
    const r = await fm.fotoUclari(new Request(u, { method: "POST", body: JSON.stringify(govde),
      headers: { "CF-Connecting-IP": "10.0.7." + (++ipNo), "Content-Type": "application/json" } }), e2, new URL(u), "/foto/onizleme", null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    const gj = v && v.is ? yazilan.get("foto-uretec-onizleme/" + v.is + "/girdi.json") : null;
    return { kod: r.status, hata: v && v.hata, renkler: gj ? JSON.parse(gj).renkler : null };
  };
  const esit = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const iz = {};
  try {
    for (const t of ["bust", "yapboz"]) {
      VERI.ornekler.push({ tur: t, kanit: "render", olcu_mm: 120, onizleme: "https://media.pruvo3d.com/ro-o.webp",
                           render: "https://media.pruvo3d.com/ro-r.webp", not: "t" });
      await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, 'x')").bind(t).run();
    }
    iz.r1 = await onizle("bust", 110, { renkler: ["Ahşap", "Beyaz"], renkli: true });
    iz.r2 = await onizle("bust", 110, { renkler: ["Gri"], renkli: false });
    iz.r3 = await onizle("yapboz", 150, { renkler: ["Lacivert", "Kırmızı", "Sarı", "Beyaz"], renkli: true });
    iz.anaIki = await onizle("bust", 110, { renkler: ["Gri", "Beyaz"], renkli: false });
    iz.tavan = await onizle("bust", 110, { renkler: ["Gri", "Beyaz", "Mavi"], renkli: true });
    iz.disi = await onizle("bust", 110, { renkler: ["Mor"], renkli: true });
    iz.eski = await onizle("bust", 110, {});
    s.R1 = iz.r1.kod === 200 && esit(iz.r1.renkler, { taban: "Ahşap", rolyef: "Beyaz" });
    s.R2 = iz.r2.kod === 200 && esit(iz.r2.renkler, { taban: "Gri" });
    s.R3 = iz.r3.kod === 200 && esit(iz.r3.renkler, { renk1: "Lacivert", renk2: "Kırmızı", renk3: "Sarı", renk4: "Beyaz" });
    s.KURAL = [iz.anaIki, iz.tavan, iz.disi].every((x) => x.kod === 400 && x.hata === "gecersiz-renk") &&
              iz.eski.kod === 200 && esit(iz.eski.renkler, {});
  } finally {
    VERI.ornekler.splice(0, VERI.ornekler.length, ...yedek);
    k.kapat();
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}

console.log("RO) RENK-ONIZLEME — secilen palet renkleri onizleme girdisinde (Okan 10 Eki vaka bde591a7)");
{
  const s = await onizlemeRenkSenaryolar(foto);
  ol("R1 bust Renkli [Ahşap, Beyaz] -> onizleme girdi.json renkler {taban, rolyef} (2 renk)", s.R1 === true, JSON.stringify(s.iz.r1));
  ol("R2 bust Gri -> onizleme girdi.json renkler {taban: Gri} (1 renk)", s.R2 === true, JSON.stringify(s.iz.r2));
  ol("R3 yapboz Renkli 4 renk -> renk1..renk4 sirayla", s.R3 === true, JSON.stringify(s.iz.r3));
  ol("R-KURAL ana renkte 2 renk / tavan asimi / palet disi -> 400 gecersiz-renk · renk alani yok (eski istemci) -> 200 {}",
     s.KURAL === true, JSON.stringify([s.iz.anaIki, s.iz.tavan, s.iz.disi, s.iz.eski]));
}
const RO_MUTANTLAR = [
  ["MR1 KOPAN HALKA GERI: onizleme girdisi yalniz bolge secimi", "renkler: { ...paletRenk, ...sc.renk }, malzemeler: sc.malzeme,",
   "renkler: sc.renk, malzemeler: sc.malzeme,", ["R1", "R2", "R3"]],
  ["MR2 renk kurali atlandi", "    if (!rs) { return fjson({ hata: \"gecersiz-renk\" }, 400); }\n    paletRenk",
   "    if (!rs) { paletRenk = {}; }\n    else paletRenk", ["KURAL"]],
  ["MR-K KONTROL (yorum)", "// PALET RENKLERI (RENK-ONIZLEME", "// PALET  RENKLERI (RENK-ONIZLEME", []],
];
for (const [ad, capa, yerine, olmeli] of RO_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await onizlemeRenkSenaryolar(fm);
  const kirmizilar = Object.keys(s).filter((x) => s[x] !== true).sort();
  ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]",
     Object.keys(s).length === 4 && JSON.stringify(kirmizilar) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(s.iz));
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
  // 12) İptal→yeni tür ② dolu 1/1: ④ S3 → İptal → ① → başka kart (insan figürü; 6 model, büst kartı yok) → ② görünür +
  // yükleme kutusu + not + uyum.
  const iptalAcik = acikGercek(veriYukle(VERI_KAYNAK), ["plaket", "figur"]);
  const iptalDene = async (kaynak) => {
    const e = await ekranKos(kaynak, veriYukle(VERI_KAYNAK), iptalAcik,
      { is: "d".repeat(32), tur: "plaket", olcu: 100 },
      { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
      { turnstileOto: true, zamanlayici: true });
    const btn = [...e.bolum.agac()].find((n) => n.id === "foto-iptal-btn");
    if (btn) btn.tetikle("click");
    const kart = [...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-kart") && n.getAttribute("data-kart") === "insan");
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
  const mB2Capa = "function sipBtnKapaliMi(nt) {\n    return !S.aydinlatmaOnay || !S.b2Onay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null) ||\n      onizlemeSuresiDoldu();\n  }";
  const mB2Yerine = "function sipBtnKapaliMi(nt) {\n    return !S.aydinlatmaOnay || !!(nt && F.olcuTuretilmis(nt.kod) && S.fiyatKurus == null) ||\n      onizlemeSuresiDoldu();\n  }";
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

  // SÜRE KAPISI (BaBa 14 Eki): geçerlilik geçmişse "Sepete ekle" disabled + metin birebir; tik kapısı açamaz;
  // sepeteEkle girişinde ikinci kapı (buton zorla açılıp tıklansa da sepet 0). Gelecekte: buton tik kapısına bağlı.
  const SURE_METIN = "Önizlemenin süresi doldu; yeni önizleme gerekiyor.";
  const sureDene = async (kaynak, bitis, b2, zorlaTikla) => {
    const sepet = [];
    const e = await ekranKos(kaynak, VERI, fotoAcik,
      { is: "9".repeat(32), tur: "plaket", olcu: 100, onay: _onaySurum },
      { asama: "hazir", tur: "plaket", olcu_mm: 100, fiyat_kurus: 100000, gecerlilik_bitis: bitis },
      { turnstileOto: true, zamanlayici: true, sepet });
    const d = () => [...e.bolum.agac()];
    const inp = d().find((n) => n.id === "foto-b2-onay");
    if (inp) { inp.checked = b2; inp.tetikle("change"); }
    const sip = d().find((n) => n.id === "foto-sip-btn");
    const r = { sip: !!sip, disabled: sip ? sip.disabled : null,
                metin: d().filter((n) => n.tagName === "P" && n.textContent === SURE_METIN).length };
    if (zorlaTikla && sip) { sip.disabled = false; sip.tetikle("click"); }
    r.sepet = sepet.length;
    return r;
  };
  const GECMIS = "2020-01-01T00:00:00.000Z", GELECEK = "2099-01-01T00:00:00.000Z";
  const sureHepsi = async (kaynak) => {
    const a = await sureDene(kaynak, GECMIS, true, false);
    const b0 = await sureDene(kaynak, GELECEK, false, false);
    const b1 = await sureDene(kaynak, GELECEK, true, false);
    const c = await sureDene(kaynak, GECMIS, true, true);
    const c0 = await sureDene(kaynak, GELECEK, true, true);
    const v = {
      SD1: a.sip && a.disabled === true && a.metin === 1,
      SD2: b0.disabled === true && b1.disabled === false && b0.metin === 0 && b1.metin === 0,
      SD3: c.sepet === 0 && c0.sepet === 1,
    };
    Object.defineProperty(v, "iz", { value: { a, b0, b1, c, c0 }, enumerable: false });
    return v;
  };
  const sd = await sureHepsi(EKRAN_KAYNAK);
  ol("SD1 geçerlilik geçmiş + B2 tikli -> 'Sepete ekle' disabled + metin birebir 1× (tik kapısı AÇAMAZ)", sd.SD1, JSON.stringify(sd.iz.a));
  ol("SD2 geçerlilik gelecekte -> buton tik kapısına bağlı (B2 yok: disabled · B2 tikli: açık) · süre metni 0", sd.SD2,
     JSON.stringify([sd.iz.b0, sd.iz.b1]));
  ol("SD3 çift kapı: süre geçmişken buton zorla açılıp tıklansa da sepet 0 (gelecekte kontrol: sepet 1)", sd.SD3,
     JSON.stringify([sd.iz.c, sd.iz.c0]));
  const SD_MUT = [
    ["M-SURE-YOK süre kontrolü silinir (onizlemeSuresiDoldu hep false)",
     "    if (!S.gecerlilik) return false;\n    var bitis = Date.parse(S.gecerlilik);\n    return isFinite(bitis) && Date.now() > bitis;\n",
     "    return false;\n", ["SD1", "SD3"]],
    ["M-SURE-BUTON süre kapısı buton formülünden silinir", " ||\n      onizlemeSuresiDoldu();\n  }", ";\n  }", ["SD1"]],
    ["M-SURE-SEPET sepeteEkle girişindeki ikinci kapı silinir",
     "    if (onizlemeSuresiDoldu()) {\n      adimKoy(\"S3\", SURE_DOLDU_METNI, true); return;\n    }\n", "", ["SD3"]],
    ["M-SURE-K0 KONTROL (yorum)", "  // Çift kapı: buton açık kalmışken", "  // Çift  kapı: buton açık kalmışken", []],
  ];
  for (const [ad, capa, yerine, olmeli] of SD_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await sureHepsi(EKRAN_KAYNAK.replace(capa, yerine));
    const kir = ["SD1", "SD2", "SD3"].filter((x) => m[x] !== true);
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }

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
  // Okan 10 Eki 12:5x "not yazma zorunluluğunu kaldır": not boş + onaylı ⇒ düğme AÇIK.
  ol("M-TARIF kontrol not boş + onaylı ⇒ onizle disabled=false (not isteğe bağlı)", tarifKontrol === false, "disabled=" + tarifKontrol);
  // capa: guncelleS1Buton içindeki notZorunlu satırı (unique); mutant: değeri true yapar →
  // not boşken bile onizle AÇIK. Sırf satırı yorum yapmak yetmez (undefined && x = undefined,
  // yine falsy → buton yine disabled; JS sessiz hata sınıfı).
  // TUR-B ①: not kosulu s1Sebep sirasinda (guncelleS1Buton TEK kaynaktan okur).
  // Mutant: s1Sebep'e not satırı geri konur ⇒ not boşken düğme KAPALI (kontrol KIRMIZI olur).
  const mTCapa = "      [!S.aydinlatmaOnay, S1_SEBEP.onay],\n";
  const mTCount = EKRAN_KAYNAK.split(mTCapa).length - 1;
  const mTNot = mTCount === 1 ? await tarifDene2(EKRAN_KAYNAK.split(mTCapa).join("      [fotoGerekir() && !((S.uretimNotu || \"\").trim()), \"Önce \\\"Nasıl olsun?\\\" kısmına kısa bir not yaz.\"],\n" + mTCapa)) : null;
  ol("M-TARIF mutant not satırı geri ⇒ not boşken onizle KAPALI (kontrol KIRMIZI)",
     mTCount === 1 && mTNot === true,
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
    const anahtarlikKart = kartlarA.find((k) => k.getAttribute("data-kart") === "anahtarlik_yazi");
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
// #fotoUretim içinde TEK kutu (kutu dışı öğe 0) · ① kartlar KARTLAR tablosundan (yalnız /acik türleri; 6 MODEL:
// büst/yapboz /acik'te olsa da kart 0) · aynı anda TEK pencere · ① seçimsiz İleri pasif · insan + pet → figur ·
// büst yönlendirmesi 0 (Okan 10 Eki: büst kapsam dışı) · ③ fiyat 3 vaka + renk tavanı 2 + sürgü tabanı 2 + malzeme N/N · ④ tiksiz
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
    s.KART = JSON.stringify(kartlar.map((k) => k.getAttribute("data-kart"))) === JSON.stringify(["insan", "pet", "plaket", "model"]) &&
      p1Disi === 0 && (p1 ? [...p1.agac()] : []).filter((n) => n.tagName === "INPUT" && n.type === "file").length === 0 &&
      // Görsel alanı: img YA DA örneksiz kartın nötr yer tutucusu (A4: boş src'li img kırık simge çizer).
      kartlar.every((k) => [...k.agac()].some((n) => n.tagName === "IMG" || (n.classList && n.classList.contains("foto-uretim-kart-yer"))) &&
        sinifli(k, "foto-uretim-kart-ad").length === 1);
    const ileri = byId(b, "foto-ileri"), geri = byId(b, "foto-geri");
    s.ILERI = aktif(b) === "1" && !!ileri && ileri.disabled === true && !!geri && geri.hidden === true;
    e.tik("insan"); pen.push(gorunurPencere(b));
    const insanAktif = aktif(b), insanD = durustMetni(b), insanY = !!byId(b, "foto-bust-yonlendir");
    e.tik("plaket"); pen.push(gorunurPencere(b));
    e.tik("pet"); pen.push(gorunurPencere(b));
    const hayvanD = durustMetni(b), hayvanY = !!byId(b, "foto-bust-yonlendir");
    const figurD = V.turBul("figur").durustluk;
    s.INSAN = insanAktif === "2" && insanD === figurD && hayvanD === figurD && V.turBul("plaket").durustluk !== figurD;
    e.tik("insan");
    e.dugme("foto-bust-yonlendir"); pen.push(gorunurPencere(b));
    // 6 MODEL: büst kapsam dışı -> "Portre için Büst" yönlendirmesi HİÇBİR kartta yok (insan 0, pet 0, düğme 0).
    s.YONLENDIRME = !insanY && !hayvanY && !byId(b, "foto-bust-yonlendir");
    // Gezinti (canlı biçimli /acik): model figür → ② (dosya yok: İleri pasif) → dosya + parça tarifi "kırıldı" (kapı
    // uygun_degil: pasif + ret cümlesi) → tarif temiz (açık) → ③ → ④ (İleri gizli) → Geri ③.
    e.tik("model"); pen.push(gorunurPencere(b));
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
    kaydir(P, mmP.indexOf(60)); const f60 = fiyat(P);
    kaydir(P, mmP.indexOf(100)); const f100 = fiyat(P);
    renkSec(P, "Siyah"); const f100r3 = fiyat(P);
    kartSec(P, "PETG"); const f100petg = fiyat(P);
    kartSec(P, "PLA");
    s.FIYAT = f60 === "Fiyat: 600 TL" && f100 === "Fiyat: 1.000 TL" && f100r3 === "Fiyat: 1.000 TL" && f100petg === "Fiyat: 1.300 TL" &&
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
    s.TABAN = tabanP === "60 mm → 600 TL" && tabanB === "60 mm → 600 TL" && !!surgu(P) && surgu(P).min === "0";
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
    Object.defineProperty(s, "iz", { value: { f60, f100, f100r3, f100petg, tabanP, tabanB, pDeg, bDeg, varsayilanB, yMalzeme, bMalzeme, pMalzeme, yKart, ySecili, yPetgSecili, yOnce, ySon: fiyat(Y) }, enumerable: false });
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
    for (const kod of ["insan", "pet", "model", "anahtarlik_figur"]) {
      const e = await yeniEkran(kaynak, [...DORT, "anahtarlik"]);
      const bulundu = e.tik(kod);
      const p2 = byId(e.bolum, "foto-pencere-2");
      const dolu = !!p2 && p2.hidden !== true && !!byId(p2, "foto-yukle-kutu") && !!byId(p2, "foto-not-alani") && !!byId(p2, "foto-uyum");
      const tur = kod === "anahtarlik_figur" ? "anahtarlik" : "figur";
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
    // e1'de 6 kart (6 MODEL: anahtarlık yazı + insan + pet + plaket + anahtarlık figür + model = 6; büst/yapboz
    // /acik'te olsa da 0; anahtarlık /acik'te VAR, AÇIK). e2'de yalnız plaket → 1 kart, devre dışı 0. Yakında kart 0 (hepsi ornekli).
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
  ol("K3b-2 ① kart = KARTLAR ∩ /acik: 4/4 (insan · pet · plaket · model; büst/yapboz açık ama 0); ① icinde dosya girdisi 0, kart disi oge 0", d0.KART, JSON.stringify(d0.iz));
  ol("K3b-3 ① kart sayisi /acik'e bagli: 4 DORT + anahtarlık ⇒ 6 kart (AÇIK), Yakında 0; yalnız plaket açıkken 1 kart", a0.ACIK_SAYISI, JSON.stringify(a0));
  ol("K3b-4 ayni anda gorunen pencere 1 (9 adimin hepsinde)", d0.TEKPENCERE, JSON.stringify(d0.iz.pen));
  ol("K3b-5 ① secimsiz 'İleri' pasif + 'Geri' gizli", d0.ILERI, JSON.stringify(d0));
  ol("K3b-6 insan + pet ikisi de tur figur secer (② durustluk figur'un) ve ②'ye gecer", d0.INSAN, JSON.stringify(d0.iz));
  ol("K3b-7 büst yönlendirmesi 0 (insan 0 · pet 0; büst kapsam dışı)", d0.YONLENDIRME, JSON.stringify(d0));
  ol("K3b-8 gezinti (model figür): ② dosyasiz ve parca tarifinde (ret cumlesi) İleri pasif, temiz tarifle acik → ③ → ④ (İleri gizli, Geri var) → Geri ③", d0.GEZINTI, JSON.stringify(d0.iz));
  ol("K3b-9 ③ canli fiyat: 60 mm → 600 TL (taban) · 100 mm → 1.000 TL · Siyah (ana renk) → 1.000 TL · PETG → 1.300 TL · PLA'ya donus 1.000 TL", u0.FIYAT, JSON.stringify(u0.iz));
  ol("K3b-10 ③ renk: fotografsiz ekranda tam 3 ana renk radyo (Siyah,Beyaz,Gri; Renkli YOK), varsayilan Beyaz, tek secim; ek renk metni 0", u0.RENK, JSON.stringify(u0.iz));
  ol("K3b-11 ③ surgu tabani 2 vaka: plaket ilk deger '60 mm → 600 TL' · bust '60 mm → 600 TL'", u0.TABAN, JSON.stringify(u0.iz));
  ol("K3b-12 ③ malzeme kartlari HER turde [PLA,PETG] (yapboz · bust · plaket; ASA/ABS 0); kart metni 2. resim AYNEN + canli fiyat 1.000/1.300 TL; varsayilan PLA; PETG tiki ×1,30", u0.MALZEME, JSON.stringify(u0.iz));
  ol("K3b-13 ④ tiksiz 'Sepete ekle' disabled (yalniz B2 ile de kapali)", c0.SEPET, JSON.stringify(c0));
  ol("K3b-14 İptal → ① (secili kart 0, İleri pasif, sepet paneli yok, tek pencere)", c0.IPTAL, JSON.stringify(c0));
  ol("K3b-15 REGRESYON taze bolum, plaket DISI kartin ilk tiki (insan · pet · model · anahtarlık figür) → istisna 0 + ② dolu + durustluk o turun (4/4)", r0.REGRESYON, JSON.stringify(r0.iz));
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
    ["M-KART KARTLAR'dan pet satiri silindi", "    { kod: \"pet\", tur: \"figur\", alt: \"pet\", ad: \"Pet figürü (ayakta)\",\n      ret: \"Pet figürü için tek hayvanın ayakta, tam boy görünen net fotoğrafı gerekir.\" },\n",
     "", duzen, ["KART", "INSAN"]],
    ["M-INSAN insan karti figur yerine plaket secer", "{ kod: \"insan\", tur: \"figur\", alt: \"insan\"",
     "{ kod: \"insan\", tur: \"plaket\", alt: \"insan\"", duzen, ["INSAN"]],
    ["M-FORMKORUMA kart seciciden form-cizilmedi korumasi kalkti", "      if (S.alanOlcu) {\n        doldurS1Olcu();",
     "      {\n        doldurS1Olcu();", regresyon, ["REGRESYON"]],
    // Okan 9 Eki: Renkli fotoğrafsız akışta görünürse RENK KIRMIZI · PETG kartı fiyatı çarpansız okursa MALZEME KIRMIZI.
    ["M-RENKLI-FOTOSUZ Renkli fotografsiz akista gorunur", "return !!renkliTurde(kod) && !!(S.fotoRenkleri && S.fotoRenkleri.length) && !malzemeRenkListesi(kod);",
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
// ① "Önizleme oluştur" KAPALIYKEN altında TEK cümle (ilk eksik koşul, sıra — TUR-A4: foto · yazı ·
// onay · doğrulama · hak · program; not satırı Okan 10 Eki 12:5x ile KALKTI; ArTisT sayfa metni AYNEN); hepsi tamken düğme AÇIK + cümle GİZLİ.
// "Son 24 saatte kalan önizleme hakkın: N/<sınır>": N sunucu yanıtından, sınır VERI'den (3 YAZILMAZ);
// "Bugün" YASAK. yazı cümlesi YALNIZ anahtarlık + yazı çeşidi + yazı boşken (F.girdiYeterli aynı kapı).
const SEBEP = {
  foto: "Önce fotoğrafını yükle.",
  yazi: "Önce anahtarlığa yazılacak yazıyı gir.",
  onay: "Aydınlatma metnini okuyup onay kutusunu işaretle.",
  dogrulama: "Güvenlik doğrulaması bekleniyor.",
  hak: "Önizleme hakkın doldu; ilk hakkın 24 saat içinde yeniden açılır.",
  program: "Fotoğraftan sipariş şu an kapalı.",
};
async function sebepEkrani(kaynak, a) {
  const V = veriYukle(VERI_KAYNAK);
  const kod = a && a.kod ? a.kod : "plaket";
  const acik = { acik: true, turler: [{ kod, ad: V.turBul(kod).ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri(kod).map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus(kod, mm) })) }] };
  if (a.sinirsiz) { acik.ziyaretci_siniri = false; }
  const e = await ekranKos(kaynak, V, acik, null, { asama: "bekliyor" }, { kart: kod, turnstileOto: !a.dogrulamaYok,
    zamanlayici: true, gorselSahte: true, postKod: a.postKod, postYanit: a.postYanit,
    postAgHatasi: a.postAgHatasi, postGovdesiz: a.postGovdesiz });
  const id = (x) => [...e.bolum.agac()].find((n) => n.id === x) || null;
  const f = id("foto-dosya");
  if (f && !a.fotoYok) { f.files = [{ name: "yuz.jpg", type: "image/jpeg", size: 4096 }]; f.tetikle("change"); }
  const t = id("foto-not");
  if (t && !a.notYok) { t.value = "deniz manzarası"; t.tetikle("input"); }
  const hy = id("foto-uyum-hayir");
  if (hy) { hy.tetikle("click"); }
  const o = id("foto-aydinlatma-onay");
  if (o && !a.onayYok) { o.checked = true; o.tetikle("change"); }
  if (a.postKod || a.postAgHatasi) {
    const b0 = id("foto-onizle-buton");
    if (b0) { b0.tetikle("click"); }
    for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
  }
  const b = id("foto-onizle-buton"), sb = id("foto-onizle-sebep"), hk = id("foto-onizle-hak");
  return { kapali: !!b && b.disabled === true, acik: !!b && b.disabled === false,
           sebep: sb && sb.hidden !== true ? sb.textContent : "", gizli: !!sb && sb.hidden === true && sb.textContent === "",
           hak: hk ? hk.textContent : "", hakGizli: hk ? hk.hidden === true : null, istek: e.istekler.length,
           durum: ([...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-durum")) || { textContent: "" }).textContent };
}
async function sebepSenaryolar(kaynak) {
  const s = {}, iz = {};
  const tek = async (ad, a, beklenen) => {
    const r = await sebepEkrani(kaynak, a);
    iz[ad] = r;
    return r.kapali && r.sebep === beklenen;
  };
  // Okan 10 Eki 12:5x: not boş düğmeyi KAPATMAZ (sebep listesinde "not" yok).
  iz.not = await sebepEkrani(kaynak, { notYok: true });
  s.V1_NOT = iz.not.acik && iz.not.gizli;
  s.V1_FOTO = await tek("foto", { fotoYok: true }, SEBEP.foto);
  s.V1_YAZI = await tek("yazi", { kod: "anahtarlik", fotoYok: true, notYok: true }, SEBEP.yazi);
  s.V1_ONAY = await tek("onay", { onayYok: true }, SEBEP.onay);
  s.V1_DOGRULAMA = await tek("dogrulama", { dogrulamaYok: true }, SEBEP.dogrulama);
  s.V1_HAK = await tek("hak", { postKod: 429, postYanit: { hata: "onizleme-siniri", sinir: VERI.sinir_ziyaretci_24s } }, SEBEP.hak);
  s.V1_PROGRAM = await tek("program", { postKod: 503, postYanit: { hata: "kapali" } }, SEBEP.program);
  const tam = await sebepEkrani(kaynak, {});
  iz.tam = tam;
  s.V1_TAM = tam.acik && tam.gizli && tam.sebep === "";
  // SIRA (TUR-A4 + 12:5x): foto · yazı · onay · doğrulama · hak · program (not satırı YOK).
  //   notlu   = foto VAR + not boş + onay yok + doğrulama yok → foto skip · yazi skip · onay fires → SEBEP.onay.
  //   fotosuz = foto YOK + not var  + onay yok + doğrulama yok → foto fires → SEBEP.foto.
  const notlu = await sebepEkrani(kaynak, { notYok: true, onayYok: true, dogrulamaYok: true });
  const fotosuz = await sebepEkrani(kaynak, { fotoYok: true, onayYok: true, dogrulamaYok: true });
  iz.sira = [notlu.sebep, fotosuz.sebep];
  s.V1_SIRA = notlu.kapali && notlu.sebep === SEBEP.onay && fotosuz.kapali && fotosuz.sebep === SEBEP.foto;
  // V2: 429 sonrası S1'de sayaç sunucudan gelen N ile görünür; yanıt gelmeden sayı UYDURULMAZ (sınır cümlesi).
  // Sayaç biçimi ArTisT'ten (ArTisT 10 Eki, birebir): "Son 24 saatte kalan önizleme hakkın: N/3.".
  s.V2_HAK = iz.hak.hak === "Son 24 saatte kalan önizleme hakkın: 0/" + VERI.sinir_ziyaretci_24s + "." &&
    tam.hak === "Son 24 saatte en çok " + VERI.sinir_ziyaretci_24s + " önizleme hakkın var.";
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TB) TUR-A2 SEBEP CÜMLESİ + Son 24 saat N/" + VERI.sinir_ziyaretci_24s);
{
  const s = await sebepSenaryolar(EKRAN_KAYNAK);
  ol("V1 not boş -> düğme AÇIK, sebep cümlesi yok (not isteğe bağlı)", s.V1_NOT, JSON.stringify(s.iz.not));
  ol("V1 fotoğraf yok -> \"" + SEBEP.foto + "\"", s.V1_FOTO, JSON.stringify(s.iz.foto));
  ol("V1 anahtarlık + yazı çeşidi + yazı boş -> \"" + SEBEP.yazi + "\"", s.V1_YAZI, JSON.stringify(s.iz.yazi));
  ol("V1 aydınlatma onayı yok -> \"" + SEBEP.onay + "\"", s.V1_ONAY, JSON.stringify(s.iz.onay));
  ol("V1 doğrulama yok -> \"" + SEBEP.dogrulama + "\"", s.V1_DOGRULAMA, JSON.stringify(s.iz.dogrulama));
  ol("V1 429 onizleme-siniri -> \"" + SEBEP.hak + "\"", s.V1_HAK, JSON.stringify(s.iz.hak));
  ol("V1 503 kapali -> \"" + SEBEP.program + "\"", s.V1_PROGRAM, JSON.stringify(s.iz.program));
  ol("V1 hepsi tam -> düğme AÇIK, sebep cümlesi 0 (gizli)", s.V1_TAM, JSON.stringify(s.iz.tam));
  ol("V1 sıra: foto VAR+not boş+onay yok -> onay (not satırı yok), foto YOK -> foto", s.V1_SIRA, JSON.stringify(s.iz.sira));
  ol("V2 sayaç \"Son 24 saatte kalan önizleme hakkın: 0/" + VERI.sinir_ziyaretci_24s + ".\" 429 sonrası görünür; yanıtsız sayı uydurulmaz",
    s.V2_HAK, JSON.stringify([s.iz.hak.hak, s.iz.tam.hak]));
  const TB_MUT = [
    ["M1 sebep sırası ters", "for (var i = 0; i < sira.length; i++) { if (sira[i][0]) return sira[i][1]; }",
     "for (var i = sira.length - 1; i >= 0; i--) { if (sira[i][0]) return sira[i][1]; }", ["V1_SIRA"]],
    ["M2 eski 'Bugünkü/yarın' sebep hak cümlesi geri geldi",
     "hak: \"Önizleme hakkın doldu; ilk hakkın 24 saat içinde yeniden açılır.\",",
     "hak: \"Bugünkü önizleme hakkın doldu; yarın yenilenir.\",", ["V1_HAK"]],
    ["M3 eski 'biraz sonra' program kapalı geri geldi",
     "program: \"Fotoğraftan sipariş şu an kapalı.\"",
     "program: \"Önizleme şu an kapalı; biraz sonra yeniden dene.\"", ["V1_PROGRAM"]],
    ["M4 sayaç biçimi 'Bugün N/3' geri geldi (ArTisT)",
     "\"Son 24 saatte kalan önizleme hakkın: \" + S.kalanHak + \"/\" + F.sinir_ziyaretci_24s + \".\"",
     "\"Bugün \" + S.kalanHak + \"/\" + F.sinir_ziyaretci_24s + \" önizleme hakkın kaldı.\"", ["V2_HAK"]],
    ["M5 yazı cümlesi sıradan düştü",
     "      [cesitliTur() && seciliCesit() === \"yazi\" &&",
     "      [false,", ["V1_YAZI"]],
    ["TB-K0 KONTROL (yorum)", "  function s1Sebep() {", "  // kontrol\n  function s1Sebep() {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of TB_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa.slice(0, 60)); continue; }
    const m = await sebepSenaryolar(EKRAN_KAYNAK.replace(capa, yerine));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-A3 (10 Eki, BaBa 05:02) 503 "kapali" bildirimi
// İki önizleme işleyicisi (sağlayıcı kolu = plaket/M · üreteç kolu = büst/D): 503 `kapali` -> S1 bildirimi AYNEN
// "Fotoğraftan sipariş şu an kapalı." ve "biraz sonra" 0. Gerileme: ağ hatası + gövdesiz yanıt yine "biraz sonra".
const KAPALI_BILDIRIM = "Fotoğraftan sipariş şu an kapalı.";
async function kapaliBildirimSenaryolar(kaynak) {
  const s = {}, iz = {};
  const kos = async (ad, a) => { const r = await sebepEkrani(kaynak, a); iz[ad] = { durum: r.durum, istek: r.istek }; return r; };
  for (const [kol, kod] of [["SAG", "plaket"], ["URE", "bust"]]) {
    const k = await kos("p503_" + kol, { kod, postKod: 503, postYanit: { hata: "kapali" } });
    s["P503_" + kol] = k.istek === 1 && k.durum === KAPALI_BILDIRIM && !k.durum.includes("biraz sonra");
    const ag = await kos("ag_" + kol, { kod, postAgHatasi: true });
    s["AG_" + kol] = ag.istek === 1 && ag.durum.includes("biraz sonra yeniden dene") && ag.durum !== KAPALI_BILDIRIM;
    const gv = await kos("govdesiz_" + kol, { kod, postKod: 502, postGovdesiz: true });
    s["GOVDESIZ_" + kol] = gv.istek === 1 && gv.durum.includes("biraz sonra yeniden dene") && gv.durum !== KAPALI_BILDIRIM;
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TA3) TUR-A3 503 kapali BİLDİRİMİ — iki önizleme işleyicisi");
{
  const s = await kapaliBildirimSenaryolar(EKRAN_KAYNAK);
  for (const [kol, ad] of [["SAG", "sağlayıcı kolu (plaket)"], ["URE", "üreteç kolu (büst)"]]) {
    ol("A3 " + ad + " 503 kapali -> \"" + KAPALI_BILDIRIM + "\", \"biraz sonra\" 0", s["P503_" + kol], JSON.stringify(s.iz["p503_" + kol]));
    ol("A3 " + ad + " ağ hatası -> \"biraz sonra yeniden dene\" (gerileme)", s["AG_" + kol], JSON.stringify(s.iz["ag_" + kol]));
    ol("A3 " + ad + " gövdesiz 502 -> \"biraz sonra yeniden dene\" (gerileme)", s["GOVDESIZ_" + kol], JSON.stringify(s.iz["govdesiz_" + kol]));
  }
  const A3_MUT = [
    ["MA1 sağlayıcı kolu 503 dalı silindi",
     "        if (kod === 503 && veri && veri.hata === \"kapali\") { adimKoy(\"S1\", \"Fotoğraftan sipariş şu an kapalı.\", true); return; }\n        adimKoy(\"S1\", \"Şu an önizleme üretilemiyor,",
     "        adimKoy(\"S1\", \"Şu an önizleme üretilemiyor,", ["P503_SAG"]],
    ["MA2 üreteç kolu 503 dalı silindi",
     "        if (kod === 503 && veri && veri.hata === \"kapali\") { adimKoy(\"S1\", \"Fotoğraftan sipariş şu an kapalı.\", true); return; }\n        adimKoy(\"S1\", \"Şu an önizleme hazırlanamıyor,",
     "        adimKoy(\"S1\", \"Şu an önizleme hazırlanamıyor,", ["P503_URE"]],
    ["MA-K0 KONTROL (yorum)", "  function hakYanitiIsle(kod, veri) {", "  // kontrol\n  function hakYanitiIsle(kod, veri) {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of A3_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa.slice(0, 60)); continue; }
    const m = await kapaliBildirimSenaryolar(EKRAN_KAYNAK.replace(capa, yerine));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-A4 (10 Eki, BaBa 06:3x) sebep sırası = ekran sırası · 429 metni tek kaynak · insan kartına dürüst yer tutucu
// (a) 429 onizleme-siniri dalında sabit "Bugünkü ... Yarın ..." metinleri SİLİNDİ; yerine S1_SEBEP.hak
//     (değişkenin kendisi, metin kopyası değil). Kaynakta "Yarın yeniden deneyebilirsin" / "Bugünkü önizleme" 0.
// (b) s1Sebep() sira dizisi ekran sırasına: foto · yazı · onay · doğrulama · hak · program (not 12:5x ile kalktı).
//     S1_SEBEP METİNLERİ + koşul ifadeleri aynen; yalnız SIRA.
// (c) 11 Eki (TeKiN insan render'ı): KARTLAR.insan `ornek:false` KALKTI; kart KENDİ alt türünün örneğini gösterir
//     (kart-insan-2.webp), pet kartı kedi örneğini (kart-pet-1.webp) — alt-duyarlı kartOrnegi. Kart AKTİF.
const A4_ORNEK_YAKINDA = "Örnek yakında";
async function a4Kartlar(kaynak) {
  const V = veriYukle(VERI_KAYNAK);
  const DORT_ACIK = acikGercek(V, ["plaket", "figur", "yapboz", "bust"]);
  const e = await ekranKos(kaynak, V, DORT_ACIK);
  const kartlar = [...e.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-kart"));
  const insan = kartlar.find((k) => k.getAttribute("data-kart") === "insan") || null;
  const hayvan = kartlar.find((k) => k.getAttribute("data-kart") === "pet") || null;
  const insanImg = insan && [...insan.agac()].find((n) => n.tagName === "IMG") || null;
  const hayvanImg = hayvan && [...hayvan.agac()].find((n) => n.tagName === "IMG") || null;
  return { insan, hayvan, insanImg, hayvanImg, kartlar };
}
async function a4Senaryolar(kaynak) {
  const s = {}, iz = {};
  // V1 figür fotoğrafsız + not boş → foto cümlesi (yeni sıra: foto önce).
  const r1 = await sebepEkrani(kaynak, { kod: "figur", notYok: true, fotoYok: true });
  iz.r1 = r1; s.V1 = r1.kapali && r1.sebep === SEBEP.foto;
  // V2 fotoğraf var + not boş → düğme AÇIK, sebep yok (Okan 10 Eki 12:5x: not isteğe bağlı).
  const r2 = await sebepEkrani(kaynak, { kod: "plaket", notYok: true });
  iz.r2 = r2; s.V2 = r2.acik && r2.gizli;
  // V3 büst fotoğrafsız → foto cümlesi.
  const r3 = await sebepEkrani(kaynak, { kod: "bust", fotoYok: true });
  iz.r3 = r3; s.V3 = r3.kapali && r3.sebep === SEBEP.foto;
  // V4 anahtarlık + yazı çeşidi boş → yazı cümlesi.
  const r4 = await sebepEkrani(kaynak, { kod: "anahtarlik", fotoYok: true, notYok: true });
  iz.r4 = r4; s.V4 = r4.kapali && r4.sebep === SEBEP.yazi;
  // V5 hepsi tamam + onay yok → onay cümlesi.
  const r5 = await sebepEkrani(kaynak, { kod: "plaket", onayYok: true });
  iz.r5 = r5; s.V5 = r5.kapali && r5.sebep === SEBEP.onay;
  // V6 kalanHak 0 → hak cümlesi (sunucu 429 sonrası S.kalanHak=0 ile s1Sebep'ten hak).
  const r6 = await sebepEkrani(kaynak, { kod: "plaket", postKod: 429, postYanit: { hata: "onizleme-siniri", sinir: VERI.sinir_ziyaretci_24s } });
  iz.r6 = r6; s.V6 = r6.kapali && r6.sebep === SEBEP.hak;
  // V7 429 onizleme-siniri yanıtı sonrası ekranda SEBEP.hak metni (adimKoy("S1", S1_SEBEP.hak, true)).
  s.V7 = r6.durum === SEBEP.hak;
  // V8 insan kartı: KENDİ render'ı (kart-insan-2.webp; pet'in kedi örneği DEĞİL), not disabled, "Örnek yakında" YOK.
  // pet kartı kart-pet-1.webp gösterir.
  const kk = await a4Kartlar(kaynak);
  iz.kart = kk;
  // Sahte DOM'da img.src bir öznitelik DEĞİL property (Oge.setAttribute çağrısı yok); doğrudan property okunur.
  // disabled da property — atanmamışsa undefined; === false yerine !== true (DEVRE DIŞI yapılmamış) kullanılır.
  const insanSrc = kk.insanImg ? kk.insanImg.src : null;
  const hayvanSrc = kk.hayvanImg ? kk.hayvanImg.src : null;
  s.V8 = !!kk.insan && !!kk.hayvan && insanSrc === "https://media.pruvo3d.com/foto/ornek/kart-insan-2.webp" &&
    hayvanSrc === "https://media.pruvo3d.com/foto/ornek/kart-pet-1.webp" &&
    kk.insan.disabled !== true && kk.insan.textContent.indexOf(A4_ORNEK_YAKINDA) < 0;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TA4) TUR-A4 sebep sırası + 429 tek kaynak + insan kartı dürüst yer tutucu");
{
  const s = await a4Senaryolar(EKRAN_KAYNAK);
  ol("A4 V1 figür fotoğrafsız + not boş -> foto cümlesi (yeni sıra: foto önce)", s.V1, JSON.stringify(s.iz.r1));
  ol("A4 V2 fotoğraf var + not boş -> düğme AÇIK (not isteğe bağlı)", s.V2, JSON.stringify(s.iz.r2));
  ol("A4 V3 büst fotoğrafsız -> foto cümlesi", s.V3, JSON.stringify(s.iz.r3));
  ol("A4 V4 anahtarlık + yazı çeşidi boş -> yazı cümlesi", s.V4, JSON.stringify(s.iz.r4));
  ol("A4 V5 hepsi tamam + onay yok -> onay cümlesi", s.V5, JSON.stringify(s.iz.r5));
  ol("A4 V6 kalanHak 0 -> hak cümlesi (429 sonrası)", s.V6, JSON.stringify(s.iz.r6));
  ol("A4 V7 429 onizleme-siniri -> ekranda SEBEP.hak (adimKoy S1_SEBEP.hak)", s.V7, JSON.stringify(s.iz.r6 && s.iz.r6.durum));
  ol("A4 V8 insan kartı kart-insan-2 (pet = kart-pet-1), not disabled, \"Örnek yakında\" yok", s.V8,
     JSON.stringify({ insan: !!(s.iz.kart && s.iz.kart.insan), insanSrc: s.iz.kart && s.iz.kart.insanImg && s.iz.kart.insanImg.src,
       hayvanSrc: s.iz.kart && s.iz.kart.hayvanImg && s.iz.kart.hayvanImg.src,
       insanDisabled: s.iz.kart && s.iz.kart.insan && s.iz.kart.insan.disabled,
       insanTxt: s.iz.kart && s.iz.kart.insan && s.iz.kart.insan.textContent.slice(0, 80) }));
  const A4_MUT = [
    // M1: not satırı foto'nun ÖNÜNE geri kondu; V1 figür+fotoYok+notYok not döner, V2 plaket not boş KAPANIR.
    ["M1 not satırı foto'nun önüne geri kondu",
     "      [fotoGerekir() && !S.dosya, S1_SEBEP.foto],\n",
     "      [fotoGerekir() && !((S.uretimNotu || \"\").trim()), \"Önce \\\"Nasıl olsun?\\\" kısmına kısa bir not yaz.\"],\n      [fotoGerekir() && !S.dosya, S1_SEBEP.foto],\n",
     ["V1", "V2"]],
    // M2: kartOrnegi alt koşulu silindi → insan kartına türün İLK figür örneği (kedi, figur-1) düşer, V8 KIRMIZI.
    ["M2 kartOrnegi alt koşulu silindi",
     "(!alt || o.alt === alt) && ",
     "",
     ["V8"]],
    ["A4-K0 KONTROL (yorum)", "  function s1Sebep() {", "  // kontrol\n  function s1Sebep() {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of A4_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa.slice(0, 60)); continue; }
    const m = await a4Senaryolar(EKRAN_KAYNAK.replace(capa, yerine));
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
  // BaBa 10 Eki 12:5x: ONIZLEME=1'de 24 sa / N hak kapisi KAPALI -> gecersiz/bos anahtar SAYILIR (sayac yazilir)
  // ama sinirla REDDEDILMEZ (429 yok). Canli davranis V9'da (onizleme-siniri) olculur.
  s.V4 = k4.every((x) => x === 200) && bos === 200 && n4 === sinir + 2;
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TB) TUR-B ② MAKINE ANAHTARI ziyaretci sayacina yazilmaz");
{
  const s = await makineSenaryolar(foto);
  ol("V3 gecerli makine anahtarli 5 ardisik istek -> hepsi 200, IP sayaci 0 -> 0", s.V3, JSON.stringify(s.iz.V3));
  ol("V4 gecersiz/bos anahtar -> sayilir (sayac " + (VERI.sinir_ziyaretci_24s + 2) + "), onizleme ortaminda 429 YOK", s.V4, JSON.stringify(s.iz.V4));
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

// ---------------------------------------------------------------- SAHİP (Okan 15 Eki 01:0x) yönetim anahtarlı tarayıcı
// "ön izleme hakkını bizim browser için yükselt, biz platform sahibiyiz": CANLI env'de (ONIZLEME yok) geçerli panel
// çerezi (`pruvo_yonet`) ya da X-Yonet-Anahtar taşıyan istek ziyaretçi 24 sa / N hak sınırından MUAF; yanıtta `kalan`
// alanı YOK (istemci düğmeyi kilitlemez). Geçersiz çerez = sıradan ziyaretçi (sinir+1'inci istek 429).
async function sahipSenaryolar(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
  const cag = async (ip, ek) => {
    const h = { "CF-Connecting-IP": ip, "Content-Type": "application/json", ...(ek || {}) };
    const r = await fm.fotoUclari(new Request("https://pruvo3d.com/api/shop/foto/onizleme", { method: "POST", headers: h,
      body: JSON.stringify(onizlemeGovde()) }), e2, new URL("https://pruvo3d.com/api/shop/foto/onizleme"), "/foto/onizleme", null);
    return { kod: r.status, v: await r.json() };
  };
  const sayac = async (ip) => ((await k.d1.prepare("SELECT COUNT(*) AS n FROM foto_isler WHERE ziyaretci = ?")
    .bind(await fm.ziyaretciOzeti(e2, ip)).first()) || {}).n;
  const sinir = VERI.sinir_ziyaretci_24s;
  const s = {}, iz = {};
  const c1 = [];
  for (let i = 0; i < sinir + 2; i++) { c1.push(await cag("10.0.7.1", { Cookie: "a=1; pruvo_yonet=yonet-test-anahtari" })); }
  iz.S1 = { kod: c1.map((x) => x.kod), kalan: c1.map((x) => x.v.kalan), ip: await sayac("10.0.7.1") };
  s.S1 = c1.every((x) => x.kod === 200 && !("kalan" in x.v)) && iz.S1.ip === 0;
  const c2 = [];
  for (let i = 0; i <= sinir; i++) { c2.push((await cag("10.0.7.2", { Cookie: "pruvo_yonet=yanlis" })).kod); }
  iz.S2 = c2;
  s.S2 = c2.slice(0, sinir).every((x) => x === 200) && c2[sinir] === 429;
  const c3 = [];
  for (let i = 0; i < sinir + 1; i++) { c3.push((await cag("10.0.7.3", { "X-Yonet-Anahtar": "yonet-test-anahtari" })).kod); }
  iz.S3 = c3;
  s.S3 = c3.every((x) => x === 200);
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("SA) SAHİP — yönetim anahtarlı tarayıcı ziyaretçi sınırından muaf (canlı env)");
{
  const s = await sahipSenaryolar(foto);
  ol("S1 geçerli panel çerezi -> sinir+2 istek hepsi 200, yanıtta kalan YOK, IP sayacı 0", s.S1, JSON.stringify(s.iz.S1));
  ol("S2 geçersiz çerez -> sıradan ziyaretçi, sinir+1'inci istek 429", s.S2, JSON.stringify(s.iz.S2));
  ol("S3 geçerli X-Yonet-Anahtar -> sinir+1 istek hepsi 200", s.S3, JSON.stringify(s.iz.S3));
  const SA_MUT = [
    ["SM1 anahtar kontrolü atlandı (her çerez muaf)", "  return yonetimSahibiMi(request, env);\n", "  return true;\n", ["S2"]],
    ["SM2 sahip muafiyeti kaldırıldı", "  if (await sahipIstegi(request, env)) { return SAHIP_ZIYARETCI; }\n", "", ["S1", "S3"]],
    ["SM3 muaf yanıtta kalan hak basılır", "return ziyaretciSiniriVar(env) && !muaf ? {", "return ziyaretciSiniriVar(env) ? {", ["S1"]],
    ["SA-K0 KONTROL (yorum)", "async function sahipIstegi(request, env) {\n", "// kontrol\nasync function sahipIstegi(request, env) {\n", []],
  ];
  for (const [ad, capa, yerine, olmeli] of SA_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await sahipSenaryolar(fm);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-C (10 Eki, BaBa 12:5x) önizleme ortamında 24 sa / N hak kapısı KAPALI
// Üç çağrı yeri (/foto/onizleme M kolu · /foto/onizleme üreteç kolu · /foto/litofan) aynı ziyaretçiden sinir+1 istek.
// Canlı env (ONIZLEME yok): sinir+1'inci istek 429 onizleme-siniri. Önizleme env (ONIZLEME=1): 429 YOK, yanıtta
// kalan hak alanı YOK, /foto/acik ziyaretci_siniri=false. Kalan masraf kapıları (KREDI_TAVAN · Turnstile ·
// GUNLUK_ONIZLEME_TAVANI) bu turda DEĞİŞMEDİ.
async function hakSiniriSenaryo(fm, ek) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur(), ek);
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x'), ('bust', 1, 'x')").run();
  const cag = async (yol, govde, ip) => {
    const u = "https://pruvo3d.com/api/shop" + yol;
    const h = { "CF-Connecting-IP": ip, "Content-Type": "application/json" };
    const r = await fm.fotoUclari(new Request(u, govde ? { method: "POST", headers: h, body: JSON.stringify(govde) } : { headers: h }),
      e2, new URL(u), yol, null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, hata: v && v.hata, kalanVar: !!v && "kalan" in v, v };
  };
  const bust = onizlemeGovde({ tur: "bust", parametreler: { rolyef_yuksekligi_mm: 3, ters: false }, secim: { govde_malzeme: "PLA" } });
  // Litofan ucu yalniz PNG kalinlik haritasi alir: 200x150 IHDR'li PNG basligi (pngBoyut olcer) + gorselCoz alt boyu icin dolgu.
  const ihdr = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52, 0, 0, 0, 200, 0, 0, 0, 150,
    8, 0, 0, 0, 0, 0, 0, 0, 0, ...new Array(4096).fill(0)];
  const harita = { ...bust, gorsel: "data:image/png;base64," + Buffer.from(ihdr).toString("base64") };
  const YERLER = { m_kolu: ["/foto/onizleme", onizlemeGovde()], uretec: ["/foto/onizleme", bust], litofan: ["/foto/litofan", harita] };
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = () => 1;
  const r = {};
  try {
    let n = 0;
    for (const [ad, [yol, govde]] of Object.entries(YERLER)) {
      const ip = "10.0.20." + (++n), dizi = [];
      for (let i = 0; i <= VERI.sinir_ziyaretci_24s; i++) { dizi.push(await cag(yol, govde, ip)); }
      r[ad] = dizi;
    }
    const a = await cag("/foto/acik", null, "10.0.20.99");
    r.acik = a.v ? a.v.ziyaretci_siniri : undefined;
  } finally { VERI.ornekSayisi = asilOrnek; k.kapat(); }
  return r;
}
async function hakSiniriSenaryolar(fm) {
  const s = {}, iz = {};
  const N = VERI.sinir_ziyaretci_24s;
  iz.canli = await hakSiniriSenaryo(fm);
  iz.onizleme = await hakSiniriSenaryo(fm, { ONIZLEME: "1" });
  const yerler = ["m_kolu", "uretec", "litofan"];
  s.V9 = yerler.every((y) => iz.canli[y].slice(0, N).every((x) => x.kod === 200 && x.kalanVar) &&
    iz.canli[y][N].kod === 429 && iz.canli[y][N].hata === "onizleme-siniri") && iz.canli.acik === true;
  s.V10 = yerler.every((y) => iz.onizleme[y].every((x) => x.kod === 200 && !x.kalanVar)) && iz.onizleme.acik === false;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("TC) TUR-C önizleme ortamında 24 sa / " + VERI.sinir_ziyaretci_24s + " hak kapısı KAPALI (canlıda AYNEN)");
{
  const s = await hakSiniriSenaryolar(foto);
  const oz = (e) => JSON.stringify(Object.fromEntries(Object.entries(s.iz[e]).map(([a, d]) =>
    [a, Array.isArray(d) ? d.map((x) => x.kod + (x.hata ? ":" + x.hata : "") + (x.kalanVar ? "+k" : "")) : d])));
  ol("V9 canlı env (ONIZLEME yok) 3 yerde " + (VERI.sinir_ziyaretci_24s + 1) + ". istek -> 429 onizleme-siniri; kalan hak yanıtta", s.V9, oz("canli"));
  // İstemci: /foto/acik ziyaretci_siniri=false (önizleme) -> hak satırı GİZLİ; alan yoksa (canlı) GÖRÜNÜR.
  const hOn = await sebepEkrani(EKRAN_KAYNAK, { sinirsiz: true }), hCanli = await sebepEkrani(EKRAN_KAYNAK, {});
  ol("V10b istemci önizlemede hak satırı GİZLİ, canlıda görünür", hOn.hakGizli === true && hCanli.hakGizli === false && hOn.acik,
     JSON.stringify([hOn.hakGizli, hCanli.hakGizli, hOn.acik]));
  ol("V10 önizleme env (ONIZLEME=1) 3 yerde " + (VERI.sinir_ziyaretci_24s + 1) + ". istek -> 429 DEĞİL (200); kalan alanı yok; ziyaretci_siniri=false", s.V10, oz("onizleme"));
  const TC_MUT = [
    ["M1 bayrak koşulu ters", "  return !onizlemeMi(env);\n", "  return onizlemeMi(env);\n", ["V10", "V9"]],
    ["TC-K0 KONTROL (yorum)", "function ziyaretciSiniriVar(env) {\n", "// kontrol\nfunction ziyaretciSiniriVar(env) {\n", []],
  ];
  for (const [ad, capa, yerine, olmeli] of TC_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await hakSiniriSenaryolar(fm);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.slice().sort().join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-B2 (10 Eki) not İSTEĞE BAĞLI — Okan 12:5x "not yazma zorunluluğunu kaldır"
// (01:3x yalnız büstteydi; 12:5x HER türe.) Boş not düğmeyi KAPATMAZ, ① sebep listesinde "not" YOK, ② cümlesi
// "İsteğe bağlı…" (ArTisT) her türde; eski "zorunlu" cümlesi 0. Ters ilk durum KAPALI (değişmedi).
const B2_NOT_ESKI = "Üretim notu zorunlu; boşsa önizleme oluşturulamaz.";
const B2_NOT_ISTEGE = "İsteğe bağlı: kısa bir not ekleyebilirsin.";
const B2_SEBEP_NOT_ESKI = "Önce \"Nasıl olsun?\" kısmına kısa bir not yaz.";
// 6 tür: plaket · figür (insan kartı) · yapboz · büst · anahtarlık yazı çeşidi · anahtarlık figür çeşidi.
const B2_TURLER = [["plaket"], ["figur", "insan"], ["yapboz"], ["bust"], ["anahtarlik", "anahtarlik", "yazi"],
  ["anahtarlik", "anahtarlik", "figur"]];
async function b2Ekran(kaynak, kod, kart, cesit) {
  const V = veriYukle(VERI_KAYNAK);
  const acik = { acik: true, turler: [{ kod, ad: V.turBul(kod).ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri(kod).map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus(kod, mm) })) }] };
  const e = await ekranKos(kaynak, V, acik, null, { asama: "bekliyor" }, { kart: kart || kod, turnstileOto: true,
    zamanlayici: true, gorselSahte: true });
  const id = (x) => [...e.bolum.agac()].find((n) => n.id === x) || null;
  if (cesit) {
    cesitKartTikla(e.bolum, cesit);
  }
  const ters0 = id("foto-param-ters");
  const ters = ters0 ? { aria: ters0.getAttribute("aria-checked"), metin: ters0.textContent } : null;
  const f = id("foto-dosya");
  if (f && cesit !== "yazi") { f.files = [{ name: "yuz.jpg", type: "image/jpeg", size: 4096 }]; f.tetikle("change"); }
  const y = id("foto-yazi");
  if (cesit === "yazi") {
    // Yazı çeşidi: yazı alanı doldurulur (yazı cümlesi bu vakanın ekseni değil); not alanı bu çeşitte çizilmez.
    const ta = id("foto-param-satirlar");
    if (ta) { ta.value = "Ayşe"; ta.tetikle("input"); }
  }
  const hy = id("foto-uyum-hayir");
  if (hy) { hy.tetikle("click"); }
  const o = id("foto-aydinlatma-onay");
  if (o) { o.checked = true; o.tetikle("change"); }
  const na = id("foto-not-alani");
  const notMetin = na ? [...na.agac()].filter((n) => n.tagName === "P").map((n) => n.textContent) : [];
  const b = id("foto-onizle-buton"), sb = id("foto-onizle-sebep");
  return { acik: !!b && b.disabled === false, kapali: !!b && b.disabled === true, yazi: !!y,
           sebep: sb && sb.hidden !== true ? sb.textContent : "", notMetin, ters, notBos: !(id("foto-not") || {}).value };
}
async function b2Senaryolar(kaynak) {
  const s = {}, iz = {};
  for (const [kod, kart, cesit] of B2_TURLER) { iz[kod + (cesit ? "-" + cesit : "")] = await b2Ekran(kaynak, kod, kart, cesit); }
  const hep = Object.values(iz);
  // V6: her türde not BOŞ + foto/yazı + onay + doğrulama -> sebep listesinde "not" YOK (cümle eski not cümlesi değil).
  s.V6 = hep.length === 6 && hep.every((r) => r.notBos && r.sebep !== B2_SEBEP_NOT_ESKI && !/not yaz/.test(r.sebep));
  // V6b: fotoğraflı 5 durumda (yazı çeşidi hariç) düğme AÇIK, sebep satırı yok.
  s.V6b = Object.keys(iz).filter((k) => k !== "anahtarlik-yazi").every((k) => iz[k].acik && iz[k].sebep === "");
  // V5: ② cümlesi fotoğraflı her türde "İsteğe bağlı…", eski "zorunlu" cümlesi HİÇBİR türde yok.
  s.V5 = Object.keys(iz).filter((k) => k !== "anahtarlik-yazi").every((k) => iz[k].notMetin.includes(B2_NOT_ISTEGE)) &&
    hep.every((r) => !r.notMetin.includes(B2_NOT_ESKI));
  s.TERS = VERI.turBul("bust").form.ters.varsayilan === false && !!iz.bust.ters && iz.bust.ters.aria === "false" && iz.bust.ters.metin === "Kapalı";
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("B2) TUR-B2 not HER türde İSTEĞE BAĞLI (istemci, Okan 10 Eki 12:5x) + Ters ilk durum");
{
  const s = await b2Senaryolar(EKRAN_KAYNAK);
  const oz = (k) => JSON.stringify(Object.fromEntries(Object.entries(s.iz).map(([a, r]) => [a, r[k]])));
  ol("V6 6 türde not BOŞ -> ① sebep listesinde \"not\" YOK", s.V6, oz("sebep"));
  ol("V6b fotoğraflı 5 durumda not BOŞ -> düğme AÇIK, sebep satırı yok", s.V6b, oz("acik"));
  ol("V5b ② cümlesi her fotoğraflı türde \"" + B2_NOT_ISTEGE + "\" · \"zorunlu\" cümlesi 0", s.V5, oz("notMetin"));
  ol("TERS Ters varsayılan false + ③ düğmesi aria-checked=false \"Kapalı\" başlar", s.TERS, JSON.stringify(s.iz.bust.ters));
  const B2_MUT = [
    // Spec B MUTANT: s1Sebep'e not satırı geri konur -> V6 KIRMIZI (fotoğraflı türlerde düğme de kapanır -> V6b).
    ["M1 s1Sebep'e not satırı geri kondu", "      [!S.aydinlatmaOnay, S1_SEBEP.onay],\n",
     "      [fotoGerekir() && !((S.uretimNotu || \"\").trim()), " + JSON.stringify(B2_SEBEP_NOT_ESKI) + "],\n      [!S.aydinlatmaOnay, S1_SEBEP.onay],\n",
     ["V6", "V6b"]],
    ["M5 ② cümlesi eski zorunlu cümleye döndü", "kap.appendChild(el(\"p\", \"foto-uretim-ayrinti\", \"İsteğe bağlı: kısa bir not ekleyebilirsin.\"));",
     "kap.appendChild(el(\"p\", \"foto-uretim-ayrinti\", \"Üretim notu zorunlu; boşsa önizleme oluşturulamaz.\"));", ["V5"]],
    ["M6 Ters ilk durum açık", "S.parametre[a] = sema.varsayilan === true;", "S.parametre[a] = true;", ["TERS"]],
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
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('bust', 1, 'x'), ('plaket', 1, 'x'), " +
    "('insan', 1, 'x'), ('pet', 1, 'x'), ('model', 1, 'x'), ('yapboz', 1, 'x'), ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (govde) => {
    const h = { "CF-Connecting-IP": "10.0." + (9 + (ipNo >> 8)) + "." + ((++ipNo) & 255), "Content-Type": "application/json" };
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
  // V7/V8 (Okan 10 Eki 12:5x "not yazma zorunluluğunu kaldır"): 6 türde boş not -> 400 DEĞİL, dolu notla AYNI kod;
  // M kolu (sağlayıcı) prototip istemi boş notta "undefined"/"null" taşımaz. Örnek şartı yine bellekte 1.
  const asilFetch = globalThis.fetch, istemler = [];
  globalThis.fetch = (h, i) => {
    if (i && i.method === "POST" && /\/v1\/prototype$/.test(String(h && h.url ? h.url : h))) { istemler.push(String(i.body)); }
    return asilFetch(h, i);
  };
  VERI.ornekSayisi = () => 1;
  const ahSecim = { plaka_renk: "Beyaz", yazi_renk: "Siyah", govde_malzeme: "PLA" };
  const ALTI = {
    plaket: (ek) => onizlemeGovde(ek),
    figur: (ek) => onizlemeGovde({ tur: "figur", olcu_mm: 100, alt_tur: "insan", ...ek }),
    yapboz: (ek) => onizlemeGovde({ tur: "yapboz", olcu_mm: 150, parametreler: { uzun_kenar_mm: 150, satir: 3, sutun: 4,
      tohum: 1, kabartma_yon: "acik_yuksek" }, secim: { govde_malzeme: "PLA" }, ...ek }),
    bust: (ek) => bust(ek),
    "anahtarlik-yazi": (ek) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, gorsel: undefined, cesit: "yazi", secim: ahSecim,
      parametreler: { satirlar: ["Ayşe"], yazi_tipi: "script", hizalama: "orta", genislik_mm: AH_MM,
        anahtarlik_kulak_konum: "sol-ust", kontur_tasma_mm: 1.5 }, ...ek }),
    "anahtarlik-figur": (ek) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, cesit: "figur", secim: ahSecim, ...ek }),
  };
  iz.alti = {};
  const kulakGeri = kulakTavanYama(VERI);
  try {
    for (const [ad, g] of Object.entries(ALTI)) {
      const once = istemler.length;
      const bos = await cag(g({ not: "" })), yok = await cag(g({})), dolu = await cag(g({ not: "deniz manzarası" }));
      iz.alti[ad] = { bos, yok, dolu, istem: istemler.slice(once) };
    }
  } finally { globalThis.fetch = asilFetch; VERI.ornekSayisi = (kod) => (kod === "bust" ? 1 : asilOrnek(kod)); kulakGeri(); }
  s.V7 = Object.keys(iz.alti).length === 6 && Object.values(iz.alti).every((r) =>
    r.bos.kod !== 400 && r.yok.kod !== 400 && r.bos.kod === r.dolu.kod && r.yok.kod === r.dolu.kod && r.dolu.kod === 200);
  const mIstem = ["plaket", "figur"].map((a) => iz.alti[a].istem).flat();
  iz.mIstem = mIstem;
  s.V8 = mIstem.length >= 6 && mIstem.every((b) => !/undefined|null/.test(b));
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
  ol("V3 sunucu: büst boş/boşluk/yok not -> 200 (400 DEĞİL); dolu not 200, telefonlu not 400 not-kisisel-veri", s.V3,
     JSON.stringify({ bos: s.iz.bos, bosluk: s.iz.bosluk, yok: s.iz.yok, dolu: s.iz.dolu, tel: s.iz.tel }));
  ol("V7 sunucu: 6 türde boş/yok not önizleme -> 400 DEĞİL, dolu notla AYNI kod (200)", s.V7,
     JSON.stringify(Object.fromEntries(Object.entries(s.iz.alti).map(([a, r]) => [a, [r.bos.kod, r.yok.kod, r.dolu.kod, r.bos.hata || r.dolu.hata]]))));
  ol("V8 M kolu (plaket+figür) prototip istemi boş notta \"undefined\"/\"null\" 0", s.V8, JSON.stringify(s.iz.mIstem.slice(0, 2)));
  console.log("  ÖLÇÜM V4 plaket boş not -> " + JSON.stringify(s.iz.plaketBos) + " (sunucuda boş-not reddi yok; kapı istemcide)");
  const B2S_MUT = [
    ["M3 sunucu boş notu reddeder (büst muafiyeti yok)", "  if (x === undefined || x === null) { return { ok: true, deger: \"\" }; }\n",
     "  if (x === undefined || x === null || (typeof x === \"string\" && !x.trim())) { return { ok: false, hata: \"not-bos\" }; }\n",
     // V8 de düşer: boş notlu istek sağlayıcıya hiç gitmez -> ölçülecek istem 0 (V8 istem sayısı >= 6 ister).
     ["V3", "V7", "V8"]],
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
const C2A_YAZI = { satirlar: ["Ayşe"], yazi_tipi: "script", hizalama: "orta", genislik_mm: AH_MM,
  anahtarlik_kulak_konum: "sol-ust", kontur_tasma_mm: 1.5 };
async function c2aSunucuSenaryolar(fm, veriYama) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x'), ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (yol, govde) => {
    const h = { "CF-Connecting-IP": "10.0.7." + (++ipNo), "Content-Type": "application/json" };
    const u = "https://pruvo3d.com/api/shop" + yol;
    const r = await fm.fotoUclari(new Request(u, govde ? { method: "POST", headers: h, body: JSON.stringify(govde) } : { headers: h }),
      e2, new URL(u), yol.split("?")[0], null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const ah = (ek) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, gorsel: undefined, parametreler: C2A_YAZI,
    secim: { plaka_renk: "Beyaz", yazi_renk: "Siyah", govde_malzeme: "PLA" }, ...(ek || {}) });
  const satir = async (is) => (await k.d1.prepare("SELECT cesit, asama FROM foto_isler WHERE is_no = ?").bind(is || "").first());
  const s = {}, iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" ? 1 : asilOrnek(kod));
  const geri = typeof veriYama === "function" ? veriYama() : null;
  let proto0 = protoSayisi();
  try {
    // V1 (TUR-C2b): VERI'de figür AÇIK; kapalı-kapı davranışı bellek yamasıyla (acik:false) ölçülür.
    const fk = VERI.cesitKaydi("anahtarlik", "figur"), fkAcik = fk ? fk.acik : undefined;
    if (fk) { fk.acik = false; }
    try { iz.figur = await cag("/foto/onizleme", ah({ cesit: "figur", gorsel: GORSEL, parametreler: undefined })); }
    finally { if (fk) { fk.acik = fkAcik; } }
    iz.xyz = await cag("/foto/onizleme", ah({ cesit: "xyz" }));
    iz.plaketCesit = await cag("/foto/onizleme", onizlemeGovde({ cesit: "yazi" }));
    iz.dogrudan = fm.girdiGovdeDogrula("anahtarlik", { cesit: "xyz", parametreler: C2A_YAZI });
    iz.figurProto = protoSayisi() - proto0;
    proto0 = protoSayisi();
    iz.yok = await cag("/foto/onizleme", ah());
    iz.yazi = await cag("/foto/onizleme", ah({ cesit: "yazi" }));
    iz.yokSatir = await satir(iz.yok.v && iz.yok.v.is);
    iz.yaziSatir = await satir(iz.yazi.v && iz.yazi.v.is);
    iz.yokDurum = await cag("/foto/durum?is=" + (iz.yok.v && iz.yok.v.is));
    // ESKİ SATIR (göç öncesi yazılmış: cesit sütunu INSERT'te YOK -> DEFAULT '') = yazı kolu.
    const eski = "c2a0" + "e".repeat(28);
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, 'anahtarlik', 60, 'z', ?, 'uretec-onizleme')")
      .bind(eski, new Date().toISOString()).run();
    iz.eskiSatir = await satir(eski);
    iz.eskiDurum = await cag("/foto/durum?is=" + eski);
    iz.proto = protoSayisi() - proto0;
  } finally { VERI.ornekSayisi = asilOrnek; if (geri) { geri(); } }
  s.V1 = iz.figur.kod === 400 && iz.figur.v && iz.figur.v.hata === "cesit-yakinda" && iz.figurProto === 0;
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
console.log("C2a) TUR-C2a anahtarlık çeşit — sunucu (V1 figür kapısı bellek yamasıyla KAPALI; TUR-C2b VERI AÇIK)");
{
  ol("C2a VERI: anahtarlık çeşitleri [yazi,figur], varsayılan yazi, figür acik:true (TUR-C2b kapı AÇIK)",
     JSON.stringify(VERI.cesitler.anahtarlik.secenekler.map((x) => [x.kod, x.acik])) === '[["yazi",true],["figur",true]]' &&
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

// ---------------------------------------------------------------- TUR-C2a-2 (10 Eki) figurKolu dallanma noktalari
// figurKolu(is) = is.cesit === "figur" (ACIK alan). Figur satiri (dogrudan INSERT; panel/acik bypass'i YOK) durum,
// gorsel, fiyat ve kuyrukta saglayici koluna gider; V9 musteri figur yolu (bellek acik:true) saglayiciya + girdi.json'a.
async function c2a2Senaryolar(fm, veriYama) {
  const k = koprukur(); await k.hazir;
  const r2 = r2Kur();
  // Sahte kova dizgiyi bayta cevirmez: dizgi yazimlari (girdi.json) ayrica tutulur.
  const yazilan = new Map(), asilPut = r2.put;
  r2.put = async (a, v, o) => { if (typeof v === "string") { yazilan.set(a, v); } return asilPut(a, v, o); };
  const e2 = envKur(k.d1, r2);
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x'), ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (yol, govde) => {
    const h = { "CF-Connecting-IP": "10.0.9." + (++ipNo), "Content-Type": "application/json" };
    const u = "https://pruvo3d.com/api/shop" + yol;
    const r = await fm.fotoUclari(new Request(u, govde ? { method: "POST", headers: h, body: JSON.stringify(govde) } : { headers: h }),
      e2, new URL(u), yol.split("?")[0], null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const s = {}, iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" || kod === "figur" ? 1 : asilOrnek(kod));
  const fs0 = VERI.cesitKaydi("anahtarlik", "figur"), fs0Acik = fs0 ? fs0.acik : undefined;
  const kulakGeri = kulakTavanYama(VERI);
  const geri = typeof veriYama === "function" ? veriYama() : null;
  const iso = new Date().toISOString();
  const fig = "c2a2" + "f".repeat(28), fig2 = "c2a2" + "b".repeat(28), no = "PR-C2A2-FIGUR";
  const ekle = (is, asama, gorev) => k.d1.prepare(
    "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, son_kontrol, cesit)" +
    " VALUES (?, 'anahtarlik', 60, 'z', ?, ?, ?, ?, 0, 'figur')").bind(is, iso, asama, gorev, iso).run();
  try {
    await ekle(fig, "onizleme", "gorev-c2a2-figur");
    await ekle(fig2, "hazir", "gorev-c2a2-hazir");
    // DURUM: saglayici GET (figur yolu)
    let c0 = P.cagri.length;
    iz.durum = await cag("/foto/durum?is=" + fig);
    iz.durumCagri = P.cagri.slice(c0).filter((x) => !/balance|TURNSTILE/.test(x));
    // GORSEL: foto-onizleme/<is>.png (uretec dizini DEGIL)
    await r2.put("foto-onizleme/" + fig2 + ".png", new Uint8Array([137, 80, 78, 71]), { httpMetadata: { contentType: "image/png" } });
    iz.gorsel = (await cag("/foto/gorsel?is=" + fig2)).kod;
    // FIYAT: deterministikSatir'e GITMEZ; birim anahtarligin bugunku formulu AYNEN
    const fk = await fm.fotoKalemFiyatla(e2, { foto_is: fig2, olcu_mm: AH_MM, adet: 1, renkler: ["Beyaz"] }, Date.now());
    iz.fiyat = fk.satir ? { id: fk.satir.id, birim: fk.satir.birim_kurus, renkli: fk.satir.foto_renkli,
      malzeme: fk.satir.malzeme, secim: fk.satir.foto_secim === undefined ? "yok" : "var" } : fk;
    s.V5fiyat = !!fk.satir && fk.satir.foto_secim === undefined && fk.satir.foto_tur === "anahtarlik" &&
      fk.satir.birim_kurus === VERI.fiyatKurus("anahtarlik", AH_MM, { renkli: fk.satir.foto_renkli, malzeme: fk.satir.malzeme });
    // KUYRUK: odenen figur kalemi build-baslat ile girer, zincir figur yolundan build baslatir
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, iso, JSON.stringify([{ id: "ozel-foto-anahtarlik", foto_is: fig2, foto_tur: "anahtarlik", olcu_mm: AH_MM,
        foto_renkler: ["Beyaz"] }])).run();
    c0 = P.cagri.length;
    await turVeOnay(fm, e2, k.d1);
    iz.kuyrukCagri = P.cagri.slice(c0).filter((x) => /build/.test(x));
    iz.kuyruk = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    // V9 MUSTERI FIGUR YOLU (bellek acik:true): saglayici prototipi figur yolundan + satir cesit='figur' + girdi.json
    if (fs0) { fs0.acik = true; }
    const fg = (ek) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, gorsel: GORSEL, parametreler: undefined,
      cesit: "figur", ...(ek || {}) });
    iz.v9param = await cag("/foto/onizleme", fg({ parametreler: C2A_YAZI }));
    iz.v9buyuk = await cag("/foto/onizleme", fg({ olcu_mm: KULAK_TAVAN_USTU }));
    c0 = P.cagri.length;
    iz.v9 = await cag("/foto/onizleme", fg());
    iz.v9cagri = P.cagri.slice(c0).filter((x) => /prototype/.test(x));
    const sat = await k.d1.prepare("SELECT is_no, cesit FROM foto_isler WHERE cesit = 'figur' AND is_no NOT LIKE 'c2a2%'").first();
    iz.v9satir = sat;
    const gj = sat ? yazilan.get("foto-uretec-onizleme/" + sat.is_no + "/girdi.json") : null;
    iz.v9girdi = gj ? JSON.parse(gj) : null;
  } finally {
    if (fs0) { fs0.acik = fs0Acik; }
    VERI.ornekSayisi = asilOrnek; if (geri) { geri(); }
    kulakGeri();
  }
  s.V5 = iz.durumCagri.includes("GET /tur-onek/tur-figur/v1/prototype/gorev-c2a2-figur") && iz.gorsel === 200 &&
    s.V5fiyat && !!iz.kuyruk && iz.kuyruk.asama !== "uretec-bekliyor" &&
    iz.kuyrukCagri.includes("POST /tur-onek/tur-figur/v1/build");
  delete s.V5fiyat;
  s.V9 = iz.v9param.kod === 400 && iz.v9param.v && iz.v9param.v.hata === "sema-disi-parametre" &&
    iz.v9buyuk.kod === 400 && iz.v9buyuk.v && iz.v9buyuk.v.hata === "gecersiz-olcu" &&
    iz.v9cagri.includes("POST /tur-onek/tur-figur/v1/prototype") && !!iz.v9satir && !!iz.v9girdi &&
    iz.v9girdi.cesit === "figur" && iz.v9girdi.uretec === "figur_kulak" && iz.v9girdi.kategori === "anahtarlik";
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}

console.log("C2a-2) TUR-C2a-2 figurKolu dallanma noktaları (figür kapısı KAPALI)");
{
  const s = await c2a2Senaryolar(foto);
  ol("V5 figurKolu satırı: durum sağlayıcı GET (figür yolu) · görsel foto-onizleme · fiyat deterministikSatir DIŞI (formül AYNEN) · kuyruk build-baslat",
     s.V5, JSON.stringify([s.iz.durumCagri, s.iz.gorsel, s.iz.fiyat, s.iz.kuyruk, s.iz.kuyrukCagri]));
  ol("V9 müşteri figür yolu (bellek acik:true, tavan 70): parametre -> sema-disi-parametre, 75 mm -> gecersiz-olcu, prototip figür yolu + D1 cesit + girdi.json",
     s.V9, JSON.stringify([s.iz.v9param, s.iz.v9buyuk, s.iz.v9, s.iz.v9cagri, s.iz.v9satir, s.iz.v9girdi]));
  const hepsi = async (fm) => ({ ...(await c2aSunucuSenaryolar(fm)), ...(await c2a2Senaryolar(fm)) });
  const C2A2_MUT = [
    ["M3 figurKolu hep false", "return !!is && is.cesit === \"figur\"; }", "return false; }", ["V5", "V9"]],
    ["M4 figurKolu hep true", "return !!is && is.cesit === \"figur\"; }", "return !!is; }", ["V3", "V4", "V8"]],
    ["C2a2-K0 KONTROL (yorum)", "export function figurKolu(is) {", "// kontrol\nexport function figurKolu(is) {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of C2A2_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = await hepsi(fm);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- TUR-C2b (10 Eki) anahtarlık 2 çeşit AÇILIŞ
// İstemci (6 MODEL, Okan 10 Eki): çeşidi ① KARTI sabitler ("Anahtarlık – yazı" / "Anahtarlık – figür"); ② çeşit düğmesi 0;
// figür kartı -> Foto ekle AÇIK + yazı alanı gizli; seçim `govde.secim.cesit`. ③ etiketleri pazarlama tablosu AYNEN.
// Sunucu: figür kapısı AÇIK (VERI acik:true) -> /foto/onizleme figür sağlayıcı yolu (secim.cesit ya da cesit).
// Kart adları + kart başına ret cümlesi (6 MODEL KARTLAR tablosu; beklenen metin BAĞIMSIZ yazılır).
const C2B_KART = [["anahtarlik_yazi", "Anahtarlık – yazı"], ["anahtarlik_figur", "Anahtarlık – figür"]];
const C2B_RET = { yazi: "Anahtarlık için kısa bir yazı gerekir.", figur: "Anahtarlık için net bir fotoğraf gerekir." };
// Pazarlama sayfa metni "Anahtarlık ③ seçenek etiketleri" tablosu (value -> görünen etiket) AYNEN. "Kulak konumu"
// seçicisi ÇIKTI (Okan 8 Eki 23:0x kulak sol üst SABİT; BaBa 13 Eki 11:4x) -> ③'te görünen 2 seçim alanı, 5 seçenek.
const C2B_ETIKET = {
  yazi_tipi: { "sans-kalin": "Kalın düz harfler", "script": "El yazısı" },
  hizalama: { "sol": "Sol", "orta": "Orta", "sag": "Sağ" } };
const C2B_FIGUR_ETIKET = { tepe: "Başın arkası (üst)", sirt: "Başın arkası (ense)" };
const C2B_BUST = "https://media.pruvo3d.com/foto/ornek/bust-2-render.webp";

async function c2bIstemci(kaynak, veriYama) {
  const s = {}, iz = {};
  // Bir çeşitle ①→④ akışı: ② girdi, İleri, ③, İleri, ④ onay + önizleme isteği gövdesi.
  const akis = async (cesit) => {
    const V = veriYukle(VERI_KAYNAK);
    kulakTavanYama(V);
    if (typeof veriYama === "function") { veriYama(V); }
    const an = V.turBul("anahtarlik");
    const acikA = { acik: true, turler: [{ kod: "anahtarlik", ad: an.ad, aciklama: "x", ornek_sayisi: 1,
      olculer: V.olcuSecenekleri("anahtarlik").map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus("anahtarlik", mm) })) }] };
    const e = await ekranKos(kaynak, V, acikA, null, null, { kart: "anahtarlik_" + cesit, gorselSahte: true, turnstileOto: true });
    const d = () => [...e.bolum.agac()];
    const id = (x) => d().find((n) => n.id === x) || null;
    const r = { istisna: e.istisna + ":" + e.istisnaMetni };
    r.kartlar = d().filter((n) => n.classList.contains("foto-uretim-kart") && /^anahtarlik/.test(n.getAttribute("data-kart") || ""))
      .map((k) => [k.getAttribute("data-kart"), ([...k.agac()].find((n) => n.classList.contains("foto-uretim-kart-ad")) || {}).textContent]);
    const p2 = id("foto-pencere-2"), kap = id("foto-cesit");
    const dugmeler = () => d().filter((n) => n.tagName === "BUTTON" && n.getAttribute("data-cesit"));
    const db = dugmeler();
    r.dugme = db.map((b) => [b.getAttribute("data-cesit"), b.textContent, b.getAttribute("aria-pressed")]);
    r.cumle = kap ? [...kap.agac()].filter((n) => n.tagName === "P").map((n) => n.textContent) : [];
    r.basta = !!p2 && !!kap && kap.hidden === false && p2.childNodes.find((n) => n.nodeType === 1) === kap;
    const kutuDurum = () => { const k = id("foto-yukle-kutu"), inp = id("foto-dosya"), y = id("foto-yazi");
      return { kutu: k ? k.hidden : null, girdiKapali: inp ? inp.disabled : null, yazi: y ? y.hidden : null }; };
    r.ilk = kutuDurum();
    const ileri = id("foto-ileri");
    if (cesit === "figur") {
      const fb = db.find((b) => b.getAttribute("data-cesit") === "figur");
      if (fb) { fb.tetikle("click"); }
      r.figurDugme = dugmeler().map((b) => [b.getAttribute("data-cesit"), b.getAttribute("aria-pressed")]);
      r.sonra = kutuDurum();
      r.ileriFotosuz = !!ileri && ileri.disabled;
      const dosya = id("foto-dosya");
      if (dosya) { dosya.files = [{ name: "kedi.jpg", type: "image/jpeg", size: 4096 }]; dosya.tetikle("change"); }
      const not = id("foto-not");
      if (not) { not.value = "Kedimin figürü"; not.tetikle("input"); }
    } else {
      const ta = id("foto-param-satirlar");
      if (ta) { ta.value = "Ayşe"; ta.tetikle("input"); }
    }
    r.ret = p2 ? [...p2.agac()].filter((n) => n.classList.contains("foto-uretim-kart-ret") && !n.hidden).map((n) => n.textContent) : [];
    r.ileri2 = !!ileri && ileri.disabled === false;
    if (ileri) { ileri.tetikle("click"); }
    const p3 = id("foto-pencere-3");
    const sec = p3 ? [...p3.agac()].filter((n) => n.tagName === "SELECT") : [];
    r.secenek = sec.map((g) => [g.id, g.hidden || (g.parentNode && g.parentNode.hidden),
      g.childNodes.filter((o) => o.tagName === "OPTION").map((o) => [o.value, o.textContent])]);
    r.form = p3 ? [...p3.agac()].filter((n) => n.id && /^foto-param-/.test(n.id)).length : -1;
    const surgu = id("foto-olcu");
    r.olcuMax = surgu ? acikA.turler[0].olculer.filter((o) => cesit !== "figur" || (o.mm <= KULAK_TAVAN_YAMA && o.mm >= KULAK_TABAN)).length - 1 === Number(surgu.max) : false;
    r.ileri3 = !!ileri && ileri.disabled === false;
    if (ileri) { ileri.tetikle("click"); }
    const on = id("foto-aydinlatma-onay");
    if (on) { on.checked = true; on.tetikle("change"); }
    const btn = id("foto-onizle-buton");
    r.btnAcik = !!btn && btn.disabled === false;
    if (btn) { btn.tetikle("click"); }
    for (let i = 0; i < 5; i++) { await new Promise((c) => setTimeout(c, 0)); }
    const ist = e.istekler.filter((x) => /\/foto\/onizleme$/.test(x.u)).map((x) => x.govde);
    r.govde = ist.length === 1 ? { cesit: ist[0].secim && ist[0].secim.cesit, gorsel: ist[0].gorsel !== undefined,
      parametreler: ist[0].parametreler === undefined ? "yok" : ist[0].parametreler, olcu: ist[0].olcu_mm } : ist.length;
    return r;
  };
  const y = await akis("yazi"), f = await akis("figur");
  iz.y = y; iz.f = f;
  // V1 (6 MODEL): ① iki ayrı anahtarlık kartı (ad birebir) · ② çeşit düğmesi 0 (iki kartta da) · çeşit kartla sabit.
  s.V1 = JSON.stringify(y.kartlar) === JSON.stringify(C2B_KART) && JSON.stringify(f.kartlar) === JSON.stringify(C2B_KART) &&
    y.dugme.length === 0 && f.dugme.length === 0 && y.basta === false && f.basta === false &&
    !!y.govde && y.govde.cesit === "yazi" && !!f.govde && f.govde.cesit === "figur";
  s.V2 = y.ilk.kutu === true && y.ilk.yazi === false;
  s.V3 = f.sonra.kutu === false && f.sonra.girdiKapali === false && f.sonra.yazi === true &&
    JSON.stringify(f.figurDugme) === "[]";
  s.V4 = y.ileri2 && y.ileri3 && y.btnAcik && f.ileri2 && f.ileri3 && f.btnAcik && f.form === 0 && f.olcuMax && y.olcuMax &&
    !!y.govde && y.govde.cesit === "yazi" && y.govde.gorsel === false && JSON.stringify(y.govde.parametreler.satirlar) === '["Ayşe"]' &&
    !!f.govde && f.govde.cesit === "figur" && f.govde.gorsel === true && f.govde.parametreler === "yok" && f.govde.olcu <= KULAK_TAVAN_YAMA;
  s.V8 = JSON.stringify(y.ret) === JSON.stringify([C2B_RET.yazi]) && JSON.stringify(f.ret) === JSON.stringify([C2B_RET.figur]);
  s.V9i = f.ileriFotosuz === true;
  // V11: ③ seçim alanlarında görünen metin tablodaki Türkçe etiket (5; kulak seçicisi 0), value ham slug AYNEN; ham slug metni 0.
  // +2: figür kulak konumu `tepe`/`sirt` etiketleri haritada (bölüm kaynağındaki KUBAR_ETIKET_MAP okunur).
  const gorunen = y.secenek.filter((x) => !x[1]);
  const beklenen = Object.keys(C2B_ETIKET).map((a) => ["foto-param-" + a, false, Object.entries(C2B_ETIKET[a])]);
  const hamSlug = gorunen.reduce((t, x) => t + x[2].filter((o) => o[0] === o[1]).length, 0);
  let harita = null;
  const hm = /\n  var KUBAR_ETIKET_MAP = (\{[\s\S]*?\n  \});/.exec(kaynak);
  try { harita = hm ? vm.runInNewContext("(" + hm[1] + ")") : null; } catch (er) { harita = null; }
  // Harita alan kavramıyla tutulur (anahtarlik_kulak_konum -> kulak_konum, bölüm etiketHaritasi önek atar).
  const figurEt = harita && harita.kulak_konum ? { tepe: harita.kulak_konum.tepe, sirt: harita.kulak_konum.sirt } : null;
  iz.v11 = { gorunen, hamSlug, figurEt };
  s.V11 = JSON.stringify(gorunen) === JSON.stringify(beklenen) && hamSlug === 0 &&
    gorunen.reduce((t, x) => t + x[2].length, 0) === 5 && JSON.stringify(figurEt) === JSON.stringify(C2B_FIGUR_ETIKET);
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}

async function c2bSunucu(fm, veriYama) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x'), ('plaket', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (yol, govde) => {
    const h = { "CF-Connecting-IP": "10.0.11." + (++ipNo), "Content-Type": "application/json" };
    const u = "https://pruvo3d.com/api/shop" + yol;
    const r = await fm.fotoUclari(new Request(u, { method: "POST", headers: h, body: JSON.stringify(govde) }),
      e2, new URL(u), yol, null);
    let v = null; try { v = await r.json(); } catch (e) { v = null; }
    return { kod: r.status, v };
  };
  const s = {}, iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" || kod === "figur" ? 1 : asilOrnek(kod));
  const kulakGeri = kulakTavanYama(VERI);
  const geri = typeof veriYama === "function" ? veriYama(VERI) : null;
  const renk = { plaka_renk: "Beyaz", yazi_renk: "Siyah", govde_malzeme: "PLA" };
  const fg = (ek) => onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, gorsel: GORSEL, parametreler: undefined, ...(ek || {}) });
  try {
    let c0 = P.cagri.length;
    iz.secimFigur = await cag("/foto/onizleme", fg({ secim: { ...renk, cesit: "figur" } }));
    iz.secimCagri = P.cagri.slice(c0).filter((x) => /prototype/.test(x));
    c0 = P.cagri.length;
    iz.ustFigur = await cag("/foto/onizleme", fg({ cesit: "figur" }));
    iz.ustCagri = P.cagri.slice(c0).filter((x) => /prototype/.test(x));
    iz.satir = iz.secimFigur.v && iz.secimFigur.v.is ?
      await k.d1.prepare("SELECT cesit FROM foto_isler WHERE is_no = ?").bind(iz.secimFigur.v.is).first() : null;
    iz.celiski = await cag("/foto/onizleme", fg({ cesit: "yazi", secim: { ...renk, cesit: "figur" } }));
    c0 = P.cagri.length;
    iz.fotosuz = await cag("/foto/onizleme", fg({ gorsel: undefined, secim: { ...renk, cesit: "figur" } }));
    iz.fotosuzCagri = P.cagri.slice(c0).filter((x) => /prototype/.test(x)).length;
  } finally { VERI.ornekSayisi = asilOrnek; if (geri) { geri(); } kulakGeri(); }
  s.V10 = iz.secimFigur.kod === 200 && iz.secimCagri.includes("POST /tur-onek/tur-figur/v1/prototype") &&
    iz.ustFigur.kod === 200 && iz.ustCagri.includes("POST /tur-onek/tur-figur/v1/prototype") &&
    !!iz.satir && iz.satir.cesit === "figur" &&
    iz.celiski.kod === 400 && !!iz.celiski.v && iz.celiski.v.hata === "gecersiz-cesit";
  s.V9s = iz.fotosuz.kod === 400 && !!iz.fotosuz.v && iz.fotosuz.v.hata === "girdi-eksik" && iz.fotosuzCagri === 0;
  const bust = (veriYukle(VERI_KAYNAK).ornekler || []).filter((o) => o.tur === "bust");
  iz.bust = bust;
  s.V12 = bust.length === 1 && bust[0].onizleme === C2B_BUST && bust[0].render === C2B_BUST;
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}

console.log("C2b) TUR-C2b anahtarlık 2 çeşit AÇILIŞ — istemci düğmeleri + figür kapısı AÇIK + ③ etiketler + büst örneği");
{
  const hepsi = async (kaynak, fm, yama) => {
    const i = await c2bIstemci(kaynak, yama), v = await c2bSunucu(fm, yama);
    const s = { V1: i.V1, V2: i.V2, V3: i.V3, V4: i.V4, V8: i.V8, V9: i.V9i && v.V9s, V10: v.V10, V11: i.V11, V12: v.V12 };
    Object.defineProperty(s, "iz", { value: { ...i.iz, ...v.iz }, enumerable: false });
    return s;
  };
  const s = await hepsi(EKRAN_KAYNAK, foto, null);
  ol("V1 ① iki anahtarlık kartı ('Anahtarlık – yazı' / 'Anahtarlık – figür'), ② çeşit düğmesi 0, çeşit kartla sabit (istek yazi/figur)",
     s.V1, JSON.stringify([s.iz.y.kartlar, s.iz.y.dugme, s.iz.f.dugme, s.iz.y.basta, s.iz.y.istisna]));
  ol("V2 yazı: Foto ekle kutusu gizli, yazı alanı görünür", s.V2, JSON.stringify(s.iz.y.ilk));
  ol("V3 figür kartı: Foto ekle AÇIK (kutu görünür, girdi açık), yazı alanı gizli, çeşit düğmesi 0", s.V3,
     JSON.stringify([s.iz.f.sonra, s.iz.f.figurDugme]));
  ol("V4 anahtarlık ①–④ iki çeşitle: İleri/önizleme açık, istek secim.cesit; figür foto+parametresiz+≤70 mm (bellek tavanı), ③ formu yok",
     s.V4, JSON.stringify([s.iz.y.govde, s.iz.f.govde, [s.iz.y.ileri2, s.iz.y.ileri3, s.iz.y.btnAcik, s.iz.y.olcuMax],
       [s.iz.f.ileri2, s.iz.f.ileri3, s.iz.f.btnAcik, s.iz.f.form, s.iz.f.olcuMax]]));
  ol("V8 ret cümlesi kart başına AYNEN (1×): yazı kartı yazı, figür kartı fotoğraf", s.V8, JSON.stringify([s.iz.y.ret, s.iz.f.ret]));
  ol("V9 figür + foto yok: istemci İleri KAPALI + sunucu 400 girdi-eksik (sağlayıcı 0)", s.V9,
     JSON.stringify([s.iz.f.ileriFotosuz, s.iz.fotosuz, s.iz.fotosuzCagri]));
  ol("V10 kapı AÇIK: secim.cesit=figur ve cesit=figur -> 200 sağlayıcı figür yolu, D1 cesit figur; çelişen çeşit -> 400",
     s.V10, JSON.stringify([s.iz.secimFigur, s.iz.secimCagri, s.iz.ustFigur, s.iz.ustCagri, s.iz.satir, s.iz.celiski]));
  ol("V11 ③ etiketler: Türkçe 5 · kulak seçici 0 (value aynen, ham slug metni 0) + figür tepe/sirt 2", s.V11, JSON.stringify(s.iz.v11));
  ol("V12 büst örnek görseli bust-2 (önizleme + render)", s.V12, JSON.stringify(s.iz.bust));
  const kapaliYama = (V) => { const c = V.cesitKaydi("anahtarlik", "figur"), a = c.acik; c.acik = false; return () => { c.acik = a; }; };
  const C2B_MUT = [
    ["M1 kart çeşidi sabitlemez (② çeşit düğmesi geri gelir)", "e", "    kap.hidden = liste.length < 2 || !!(kart && kart.kart.cesit);\n",
     "    kap.hidden = liste.length < 2;\n", null, ["V1", "V3"]],
    ["M2 figürde Foto ekle kapalı (çeşit girdisi yok sayılır)", "e", "    var t = litofanKaydi(), g = girdiListesi();\n",
     "    var t = litofanKaydi(), g = t ? t.girdi : null;\n", null, ["V3", "V4"]],
    ["M7 etiket haritası boş", "e", "  var KUBAR_ETIKET_MAP = {\n", "  var KUBAR_ETIKET_MAP = {}, KUBAR_ESKI = {\n", null, ["V11"]],
    ["M8 kapı kapalı kalır (VERI acik:false, bellek)", null, null, null, kapaliYama, ["V1", "V3", "V4", "V8", "V9", "V10"]],
    ["C2b-K0 KONTROL (yorum)", "e", "  function cizCesit() {\n", "  // kontrol\n  function cizCesit() {\n", null, []],
  ];
  for (const [ad, hedef, capa, yerine, yama, olmeli] of C2B_MUT) {
    if (capa !== null && EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await hepsi(capa === null ? EKRAN_KAYNAK : EKRAN_KAYNAK.replace(capa, yerine), foto, yama);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ④ HAZIRLAYICI SAĞLIĞI (10 Eki 2026): üreteç işi "sırada" (/foto/durum asama bekliyor) iken sunucunun
// `hazirlayici_yas_sn` alanı null ya da > 600 ise "sırada" cümlesinin altında TEK satır; ≤ 600 ve diğer aşamalarda YOK.
// E1 yaş 900 -> VAR · E2 yaş 60 -> YOK · E3 yaş null -> VAR · E4 hazır aşaması + yaş 900 -> YOK (S3 çizildi).
// Mutant ME1: eşik karşılaştırması kalkar (hep göster) -> tam olarak [E2] KIRMIZI.
{
  const HZ_METIN = "Önizleme hazırlayıcısı şu an çevrimdışı; ekibe haber verildi.";
  const hzIs = "d".repeat(32);
  const hzKos = async (kaynak, durum) => {
    const V = veriYukle(VERI_KAYNAK);
    const e = await ekranKos(kaynak, V, acikGercek(V, ["yapboz"]), { is: hzIs, tur: "yapboz", olcu: 150 }, durum,
                             { zamanlayici: true });
    const d = [...e.bolum.agac()];
    return { satir: d.filter((n) => n.tagName === "P" && n.textContent === HZ_METIN).length,
             sirada: d.filter((n) => n.tagName === "P" && /^Önizlemen sırada;/.test(n.textContent)).length,
             s3: d.filter((n) => n.classList.contains("foto-uretim-onizleme-img")).length };
  };
  const hzHazir = { asama: "hazir", tur: "yapboz", olcu_mm: 150, gorsel: "/api/shop/foto/gorsel?is=" + hzIs,
                    gecerlilik_bitis: "2026-10-11T00:00:00.000Z", hazirlayici_yas_sn: 900 };
  const hzHepsi = async (kaynak) => {
    const e1 = await hzKos(kaynak, { asama: "bekliyor", hazirlayici_yas_sn: 900 });
    const e2 = await hzKos(kaynak, { asama: "bekliyor", hazirlayici_yas_sn: 60 });
    const e3 = await hzKos(kaynak, { asama: "bekliyor", hazirlayici_yas_sn: null });
    const e4 = await hzKos(kaynak, hzHazir);
    const r = { E1: e1.sirada === 1 && e1.satir === 1, E2: e2.sirada === 1 && e2.satir === 0,
                E3: e3.sirada === 1 && e3.satir === 1, E4: e4.s3 === 1 && e4.sirada === 0 && e4.satir === 0 };
    Object.defineProperty(r, "iz", { value: [e1, e2, e3, e4], enumerable: false });
    return r;
  };
  const hz = await hzHepsi(EKRAN_KAYNAK);
  ol("E1 ④ sırada + hazirlayici_yas_sn 900 -> çevrimdışı satırı VAR (1×)", hz.E1, JSON.stringify(hz.iz[0]));
  ol("E2 ④ sırada + hazirlayici_yas_sn 60 -> satır YOK", hz.E2, JSON.stringify(hz.iz[1]));
  ol("E3 ④ sırada + hazirlayici_yas_sn null (damga yok) -> satır VAR", hz.E3, JSON.stringify(hz.iz[2]));
  ol("E4 hazır aşaması + yaş 900 -> satır YOK (S3 çizildi)", hz.E4, JSON.stringify(hz.iz[3]));
  ol("E5 çevrimdışı metni foto-uretim.js'te TEK yerde", EKRAN_KAYNAK.split(HZ_METIN).length - 1 === 1,
     EKRAN_KAYNAK.split(HZ_METIN).length - 1);
  // SUNUCU (D0/D1): /foto/durum "bekliyor" yanıtı hazirlayici_yas_sn taşır — damga yok -> null; koşucu damgası
  // 900 sn önce -> 900 (±2). Alan kümesi yalnız {asama, hazirlayici_yas_sn} (mevcut alan değişmez).
  {
    const k = koprukur(); await k.hazir;
    const e2 = envKur(k.d1, r2Kur());
    const isNo = "e".repeat(32);
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama) VALUES (?, 'yapboz', 150, 'z', ?, 'uretec-onizleme')")
      .bind(isNo, new Date().toISOString()).run();
    const durum = async () => {
      const u = "https://pruvo3d.com/api/shop/foto/durum?is=" + isNo;
      const r = await foto.fotoUclari(new Request(u, { headers: { "CF-Connecting-IP": "10.0.9.1" } }), e2, new URL(u), "/foto/durum", null);
      let v = null; try { v = await r.json(); } catch (e) { v = null; }
      return { kod: r.status, v };
    };
    const d0 = await durum();
    const t = Date.now() - 900000;
    await k.d1.prepare("INSERT INTO foto_ayar (anahtar, deger, guncel) VALUES ('kosucu_son_tik', ?, ?)")
      .bind(new Date(t).toISOString(), t).run();
    const d1r = await durum();
    k.kapat();
    ol("D0 /foto/durum bekliyor + damga yok -> hazirlayici_yas_sn null", d0.kod === 200 && !!d0.v &&
       d0.v.asama === "bekliyor" && d0.v.hazirlayici_yas_sn === null, JSON.stringify(d0));
    ol("D1 /foto/durum bekliyor + damga 900 sn önce -> hazirlayici_yas_sn 900 (±2), alanlar {asama, hazirlayici_yas_sn}",
       d1r.kod === 200 && !!d1r.v && d1r.v.asama === "bekliyor" && Math.abs(d1r.v.hazirlayici_yas_sn - 900) <= 2 &&
       Object.keys(d1r.v).sort().join(",") === "asama,hazirlayici_yas_sn", JSON.stringify(d1r));
  }
  const meCapa = '    return y === null || (typeof y === "number" && y > HAZIRLAYICI_YAS_TAVAN_SN);\n';
  if (EKRAN_KAYNAK.split(meCapa).length - 1 !== 1) { ol("ME1 capa bulundu", false, meCapa); } else {
    const m = await hzHepsi(EKRAN_KAYNAK.replace(meCapa, "    return true;\n"));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol("ME1 mutant (eşik karşılaştırması kalkar, hep göster) -> KIRMIZI tam olarak [E2]",
       JSON.stringify(kir) === JSON.stringify(["E2"]), JSON.stringify(kir));
  }
}

// ================================================================ C2 — ② TEK dürüstlük cümlesi + anahtarlık ③ Ölçü
// BaBa 10 Eki 14:0x + ArTisT sayfa metni (pruvo-pazarlama blob 24b6b59b) AYNEN. Figür (insan + hayvan) ve plaket ②
// kutusunda TEK cümle = `durustluk`; eski ikinci cümle ekranda 0 (`ornek_notu: ""`, alan DURUR -> render kart kapısı
// `typeof t.ornek_notu === "string"` kartları korur). Anahtarlık ③ Ölçü cümlesi iki çeşitte. Beklenen metinler BAĞIMSIZ.
const C2_FIGUR = "Önizleme fotoğrafının stilize bir yorumudur; basılmış figür en çok 4 renkli, sadeleştirilmiş bir hâlidir ve tam kopyası değildir (küçük ayrıntılar sadeleşir).";
const C2_PLAKET = "Önizleme fotoğrafının stilize bir yorumudur; basılmış plaket en çok 4 renkli, kabartmalı ve sadeleştirilmiş bir hâlidir, tam kopyası değildir (küçük yazı ve ince ayrıntılar sadeleşir).";
const C2_ESKI = "Önizleme ve üretim dosyasının görüntüsüdür;";
const C2_OLCU = "Anahtarlığın kulakçık dahil en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.";
// 17. okuma (ArTisT, KraL 12 Eki): figür çeşidinde halka gömülü olduğundan ölçü cümlesi ÇEŞİDE ÖZEL ("halka dahil");
// tür düzeyindeki "kulakçık dahil" cümlesi yalnız yazı çeşidi içindir (kulakçık orada durur).
const C2_OLCU_FIGUR = "Anahtarlığın, başın arkasındaki halka dahil en uzun boyutudur; fiyat bu ölçüye göre canlı hesaplanır.";
// VM4 beklenen ① kart listesi — 6 MODEL (Okan 10 Eki, sıra + kod): [data-kart, görsel dosyası | null, "Örnek yakında"].
// Kart başına yalnız KENDİ örneği (11 Eki: TeKiN 3 render'ı; alt-duyarlı kartOrnegi): 6/6 kartta görsel,
// "Örnek yakında" 0. Büst/yapboz /acik'te olsa da kart 0. 14 Eki 16:1x: anahtarlik_figur kartında kart alanı
// (renkli tasarım) öncelik alır — ornek.render YERINE kart URL'si gösterilir.
const C2_KARTLAR = JSON.stringify([["anahtarlik_yazi", "anahtarlik-1-render.webp", false], ["insan", "kart-insan-2.webp", false],
  ["pet", "kart-pet-1.webp", false], ["plaket", "kart-plaket-2.webp", false],
  ["anahtarlik_figur", "anahtarlik-figur-kart.webp", false], ["model", "kart-model-1.webp", false]]);
async function c2Senaryo(ekranKaynak, veriKaynak) {
  const s = {}, iz = {};
  const kod6 = ["plaket", "figur", "yapboz", "bust", "anahtarlik"];
  const kartla = async (kart) => {
    const V = veriYukle(veriKaynak);
    const e = await ekranKos(ekranKaynak, V, acikGercek(V, kod6), null, null, { kart });
    const d = [...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-durustluk"));
    return { e, cumle: d ? d.childNodes.filter((n) => n.tagName === "P" && !n.hidden && n.textContent).map((n) => n.textContent) : null,
      eski: e.bolum.textContent.indexOf(C2_ESKI) >= 0 };
  };
  iz.insan = await kartla("insan"); iz.hayvan = await kartla("hayvan_model"); iz.plaket = await kartla("plaket");
  const tek = (x, c) => JSON.stringify(x.cumle) === JSON.stringify([c]) && x.eski === false;
  s.VM1 = tek(iz.insan, C2_FIGUR) && tek(iz.hayvan, C2_FIGUR);
  s.VM2 = tek(iz.plaket, C2_PLAKET);
  // VM3: anahtarlık ③ Ölçü cümlesi yazı çeşidinde 1× (tür: "kulakçık dahil"), figür çeşidinde YENİ 1× (çeşit:
  // "halka dahil"); yazı çeşidi cümlesi figürde 0× olmalı (foto-uretim.js alanAciklamasi çeşit alanına öncelik verir).
  const an = await kartla("anahtarlik");
  const sayC2 = () => [...an.e.bolum.agac()].filter((n) => n.tagName === "P" && n.textContent === C2_OLCU).length;
  const sayC2F = () => [...an.e.bolum.agac()].filter((n) => n.tagName === "P" && n.textContent === C2_OLCU_FIGUR).length;
  iz.olcuYazi = sayC2();
  const fb = cesitKartTikla(an.e.bolum, "figur");
  iz.olcuFigur = fb ? sayC2() : -1;
  iz.olcuFigurYeni = fb ? sayC2F() : -1;
  s.VM3 = iz.olcuYazi === 1 && iz.olcuFigur === 0 && iz.olcuFigurYeni === 1;
  // VM4: ① kart sayısı/görselleri C2 öncesiyle AYNI (render kartları kaybolmaz).
  const V = veriYukle(veriKaynak);
  const e = await ekranKos(ekranKaynak, V, acikGercek(V, kod6));
  iz.kartlar = JSON.stringify([...e.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-kart")).map((k) => {
    const img = [...k.agac()].find((n) => n.tagName === "IMG");
    return [k.getAttribute("data-kart"), img && img.src ? img.src.split("/").pop() : null, k.textContent.indexOf("Örnek yakında") >= 0];
  }));
  s.VM4 = iz.kartlar === C2_KARTLAR;
  iz.insan = iz.insan.cumle; iz.hayvan = iz.hayvan.cumle; iz.plaket = iz.plaket.cumle;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("C2) ② TEK dürüstlük cümlesi (figür + plaket) + anahtarlık ③ Ölçü cümlesi + ① kartlar aynen");
{
  const s = await c2Senaryo(EKRAN_KAYNAK, VERI_KAYNAK);
  ol("VM1 iki figür kartı (insan + hayvan) ② dürüstlük cümlesi TEK (ArTisT), eski ikinci cümle 0", s.VM1,
     JSON.stringify([s.iz.insan, s.iz.hayvan]));
  ol("VM2 plaket ② dürüstlük cümlesi TEK (ArTisT), eski ikinci cümle 0", s.VM2, JSON.stringify(s.iz.plaket));
  ol("VM3 anahtarlık ③ yazı çeşidinde 'kulakçık dahil' 1×; figür çeşidinde 'halka dahil' 1× (yazı cümlesi 0×)", s.VM3,
     JSON.stringify([s.iz.olcuYazi, s.iz.olcuFigur, s.iz.olcuFigurYeni]));
  ol("VM4 ① 6 kart + görselleri (6/6 kendi render'ı, 'Örnek yakında' 0, büst/yapboz 0)", s.VM4,
     s.iz.kartlar);
  const C2_MUT = [
    ["VM-M1 eski ikinci cümle geri (figür ornek_notu)", "veri", 'küçük ayrıntılar sadeleşir).",\n        ornek_notu: ""',
     'küçük ayrıntılar sadeleşir).",\n        ornek_notu: "Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun sadeleştirilmiş hâlidir, tam kopyası değildir."',
     ["VM1"]],
    ["VM-M2 kart kapısı eski doğruluk sınamasına döndü (render örnekleri yer tutucuya düşer)", "ekran",
     '(F.ornekKaniti(o) !== "render" || typeof t.ornek_notu === "string")', '(F.ornekKaniti(o) !== "render" || t.ornek_notu)',
     // 6 MODEL: örneği geçersiz kart kaybolmaz, "Örnek yakında" yer tutucusuna düşer -> kart görselleri (VM4) KIRMIZI.
     ["VM4"]],
    ["VM-M3 anahtarlık ③ Ölçü cümlesi silindi", "veri",
     '        alan_aciklamalari: {\n          olcu: "Anahtarlığın kulakçık dahil', '        alan_aciklamalari_x: {\n          olcu: "Anahtarlığın kulakçık dahil',
     ["VM3"]],
  ];
  for (const [ad, hedef, capa, yerine, olmeli] of C2_MUT) {
    const kaynak = hedef === "veri" ? VERI_KAYNAK : EKRAN_KAYNAK;
    if (kaynak.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = hedef === "veri" ? await c2Senaryo(EKRAN_KAYNAK, VERI_KAYNAK.replace(capa, yerine))
      : await c2Senaryo(EKRAN_KAYNAK.replace(capa, yerine), VERI_KAYNAK);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ================================================================ FK — FOTO KART GÖRSELLERİ (11 Eki, BaBa 02:03 hüküm 2)
// ArTisT 13. okuma BULGU 2: insan · model · anahtarlık–figür kartları boş kutu. TeKiN 3 render'ı (R2, sha kutuda) kartlara
// bağlandı; kartOrnegi ALT türü ayırır (insan kartına kedi düşmez). Beklenen dosya adları BAĞIMSIZ yazılır.
const FK_BEKLENEN = { anahtarlik_yazi: "anahtarlik-1-render.webp", insan: "kart-insan-2.webp", pet: "kart-pet-1.webp",
  model: "kart-model-1.webp", anahtarlik_figur: "anahtarlik-figur-kart.webp" };
async function fkSenaryo(ekranKaynak, veriKaynak) {
  const s = {}, iz = {};
  const V = veriYukle(veriKaynak);
  const e = await ekranKos(ekranKaynak, V, acikGercek(V, ["plaket", "figur", "yapboz", "bust", "anahtarlik"]));
  const kart = {};
  for (const k of [...e.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-kart"))) {
    const img = [...k.agac()].find((n) => n.tagName === "IMG");
    kart[k.getAttribute("data-kart")] = { src: img && img.src ? img.src.split("/").pop() : null,
      yer: [...k.agac()].some((n) => n.classList && n.classList.contains("foto-uretim-kart-yer")) };
  }
  iz.kart = kart;
  const dogru = (kod) => !!kart[kod] && kart[kod].src === FK_BEKLENEN[kod] && kart[kod].yer === false;
  s.FK_INSAN = dogru("insan");
  s.FK_PET = dogru("pet");
  s.FK_MODEL = dogru("model");
  s.FK_AN_FIGUR = dogru("anahtarlik_figur");
  s.FK_AN_YAZI = dogru("anahtarlik_yazi");
  // FK_FAIL: `alt` bilinmeyen değer / modelsiz türde / metin değil -> SAYILMAZ; alan yok -> sayılır (türü açar).
  const r = { kanit: "render", onizleme: "https://media.pruvo3d.com/x.webp", render: "https://media.pruvo3d.com/x.webp" };
  iz.fail = { robot: V.ornekGecerli(Object.assign({ tur: "figur", alt: "robot" }, r)),
    bos: V.ornekGecerli(Object.assign({ tur: "figur", alt: "" }, r)),
    nul: V.ornekGecerli(Object.assign({ tur: "figur", alt: null }, r)),
    proto: V.ornekGecerli(Object.assign({ tur: "figur", alt: "toString" }, r)),
    modelsiz: V.ornekGecerli(Object.assign({ tur: "anahtarlik", cesit: "figur", alt: "pet" }, r)),
    yok: V.ornekGecerli(Object.assign({ tur: "figur" }, r)), insan: V.ornekGecerli(Object.assign({ tur: "figur", alt: "insan" }, r)) };
  s.FK_FAIL = iz.fail.robot === false && iz.fail.bos === false && iz.fail.nul === false && iz.fail.proto === false &&
    iz.fail.modelsiz === false && iz.fail.yok === true && iz.fail.insan === true;
  // FK_SAYI: sunucunun tür sayımı (ornekSayisi; /acik + turHazir bunu okur) — figur 3 · anahtarlik 2 · plaket 1; alt alanı
  // kayıtlardan silinse figur sayımı AYNI (geçerli alt sayımı DEĞİŞTİRMEZ, yalnız kart eşleştirmesini).
  const Valtsiz = veriYukle(veriKaynak.replace(/\n {8}alt: "(?:pet|insan|model)",/g, ""));
  iz.sayi = { figur: V.ornekSayisi("figur"), anahtarlik: V.ornekSayisi("anahtarlik"), plaket: V.ornekSayisi("plaket"),
    figur_altsiz: Valtsiz.ornekSayisi("figur") };
  s.FK_SAYI = iz.sayi.figur === 3 && iz.sayi.anahtarlik === 2 && iz.sayi.plaket === 1 && iz.sayi.figur_altsiz === 3;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("FK) FOTO KART GÖRSELLERİ — alt-duyarlı örnek eşleştirme (insan/pet/model/anahtarlık figür/yazı) + alt fail-closed");
{
  const s = await fkSenaryo(EKRAN_KAYNAK, VERI_KAYNAK);
  ol("FK_INSAN insan kartı -> kart-insan-2 (kedi DEĞİL), yer tutucu 0", s.FK_INSAN, JSON.stringify(s.iz.kart.insan));
  ol("FK_PET pet kartı -> kedi örneği kart-pet-1", s.FK_PET, JSON.stringify(s.iz.kart.pet));
  ol("FK_MODEL model kartı -> kart-model-1 (logosuz)", s.FK_MODEL, JSON.stringify(s.iz.kart.model));
  ol("FK_AN_FIGUR anahtarlık–figür kartı -> anahtarlik-figur-hilal-2-render", s.FK_AN_FIGUR, JSON.stringify(s.iz.kart.anahtarlik_figur));
  ol("FK_AN_YAZI anahtarlık–yazı kartı -> mevcut yazı örneği anahtarlik-1-render", s.FK_AN_YAZI, JSON.stringify(s.iz.kart.anahtarlik_yazi));
  ol("FK_FAIL ornekGecerli alt: robot/''/null/toString/modelsiz tür -> SAYILMAZ; alan yok + insan -> sayılır", s.FK_FAIL, JSON.stringify(s.iz.fail));
  ol("FK_SAYI sunucu tür sayımı figur 3 · anahtarlik 2 · plaket 1; alt alanları silinse figur yine 3", s.FK_SAYI, JSON.stringify(s.iz.sayi));
  const FK_MUT = [
    ["FKM1 kartOrnegi alt koşulu silindi", "ekran", "(!alt || o.alt === alt) && ", "", ["FK_INSAN", "FK_MODEL"]],
    ["FKM2 kart alt türü kartOrnegi'ne geçmez", "ekran", "      var o = kartOrnegi(t, k.cesit, k.alt);\n",
     "      var o = kartOrnegi(t, k.cesit);\n", ["FK_INSAN", "FK_MODEL"]],
    ["FKM3 kedi kaydının alt:\"pet\" alanı silindi", "veri", '        alt: "pet",\n', "", ["FK_PET"]],
    ["FKM4 ornekGecerli alt kontrolü silindi", "veri",
     "    if (o.alt !== undefined && !(t && t.olcu_modelleri && typeof o.alt === \"string\" &&\n",
     "    if (false && !(t && t.olcu_modelleri && typeof o.alt === \"string\" &&\n", ["FK_FAIL"]],
    ["FKM5 ornekGecerli alt kontrolü hasOwnProperty yerine `in`", "veri",
     "        Object.prototype.hasOwnProperty.call(t.olcu_modelleri, o.alt))) { return false; }\n",
     "        (o.alt in t.olcu_modelleri))) { return false; }\n", ["FK_FAIL"]],
    ["FK-MK KONTROL (yorum)", "ekran", "  function kartOrnegi(t, cesit, alt) {", "  // kontrol\n  function kartOrnegi(t, cesit, alt) {", []],
  ];
  for (const [ad, hedef, capa, yerine, olmeli] of FK_MUT) {
    const kaynak = hedef === "veri" ? VERI_KAYNAK : EKRAN_KAYNAK;
    if (kaynak.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = hedef === "veri" ? await fkSenaryo(EKRAN_KAYNAK, VERI_KAYNAK.replace(capa, yerine))
      : await fkSenaryo(EKRAN_KAYNAK.replace(capa, yerine), VERI_KAYNAK);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- 6 MODEL (Okan 10 Eki ~16:3x) — V6-1..7 + 3 MUTANT
// "1- Anahtarlık – yazı 2- insan ayakta duran figür 3- pet ayakta duran figür 4- Kabartma plaket 5- Anahtarlık – figür
// 6- Model figür. sadece bunları yapalım." Beklenen kart kodları/adları BAĞIMSIZ yazılır (kaynaktan okunmaz).
const V6_KODLAR = ["anahtarlik_yazi", "insan", "pet", "plaket", "anahtarlik_figur", "model"];
const V6_ADLAR = ["Anahtarlık – yazı", "İnsan figürü (ayakta)", "Pet figürü (ayakta)", "Kabartma plaket", "Anahtarlık – figür", "Model figür"];
const V6_TUM = ["plaket", "figur", "yapboz", "bust", "anahtarlik"];
const V6_YASAK_ISTEM = /3d ?bask|heykel|mermer/i;
// Kart -> ②/③/④ akışı -> /foto/onizleme istek gövdesi (yalnız istemci; sağlayıcı yok).
async function v6Istek(kaynak, kart) {
  const V = veriYukle(VERI_KAYNAK);
  const e = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null, { kart, gorselSahte: true, turnstileOto: true });
  const d = () => [...e.bolum.agac()];
  const id = (x) => d().find((n) => n.id === x) || null;
  if (kart === "anahtarlik_yazi") {
    const ta = id("foto-param-satirlar");
    if (ta) { ta.value = "Ayşe"; ta.tetikle("input"); }
  } else {
    const dosya = id("foto-dosya");
    if (dosya) { dosya.files = [{ name: "a.jpg", type: "image/jpeg", size: 4096 }]; dosya.tetikle("change"); }
    const hayir = id("foto-uyum-hayir");
    if (hayir && !hayir.hidden) { hayir.tetikle("click"); }
  }
  const ileri = id("foto-ileri");
  if (ileri) { ileri.tetikle("click"); ileri.tetikle("click"); }
  const on = id("foto-aydinlatma-onay");
  if (on) { on.checked = true; on.tetikle("change"); }
  const btn = id("foto-onizle-buton");
  if (btn) { btn.tetikle("click"); }
  for (let i = 0; i < 5; i++) { await new Promise((c) => setTimeout(c, 0)); }
  const g = e.istekler.filter((x) => /\/foto\/onizleme$/.test(x.u)).map((x) => x.govde);
  return g.length === 1 ? { tur: g[0].tur, alt_tur: g[0].alt_tur === undefined ? "yok" : g[0].alt_tur,
    cesit: (g[0].secim && g[0].secim.cesit) || g[0].cesit || "yok" } : { adet: g.length, istisna: e.istisna + ":" + e.istisnaMetni };
}
async function v6Istemci(kaynak) {
  const s = {}, iz = {};
  const V = veriYukle(VERI_KAYNAK);
  const kartlarOku = (b) => [...b.agac()].filter((n) => n.classList.contains("foto-uretim-kart"));
  const adOku = (k) => ([...k.agac()].find((n) => n.classList.contains("foto-uretim-kart-ad")) || {}).textContent;
  const birinci = (b) => ([...b.agac()].find((n) => n.classList.contains("foto-uretim-pencere-aciklama")) || {}).textContent;
  // V6-1: büst + yapboz /acik'te AÇIK (D1 açık olsa bile) -> 6 kart, sıra + adlar birebir, büst/yapboz kartı 0.
  const e = await ekranKos(kaynak, V, acikGercek(V, V6_TUM));
  const k6 = kartlarOku(e.bolum);
  iz.kod = k6.map((k) => k.getAttribute("data-kart")); iz.ad = k6.map(adOku);
  s.V6_1 = JSON.stringify(iz.kod) === JSON.stringify(V6_KODLAR) && JSON.stringify(iz.ad) === JSON.stringify(V6_ADLAR) &&
    !iz.kod.some((k) => k === "bust" || k === "yapboz");
  // V6-2: ① cümlesi açık kartlardan (6 kart / fikstür 3 kart: yalnız anahtarlık + plaket açık).
  iz.c6 = birinci(e.bolum);
  const e3 = await ekranKos(kaynak, V, acikGercek(V, ["anahtarlik", "plaket"]));
  iz.c3 = birinci(e3.bolum);
  s.V6_2 = iz.c6 === "6 seçenekten birini seç: Anahtarlık – yazı, İnsan figürü (ayakta), Pet figürü (ayakta), Kabartma plaket, " +
    "Anahtarlık – figür ya da Model figür." && iz.c3 === "3 seçenekten birini seç: Anahtarlık – yazı, Kabartma plaket ya da Anahtarlık – figür.";
  // V6-3: kart -> istek (tür + alt tür + çeşit).
  iz.istek = {};
  for (const k of V6_KODLAR) { iz.istek[k] = await v6Istek(kaynak, k); }
  const bek = { anahtarlik_yazi: { tur: "anahtarlik", alt_tur: "yok", cesit: "yazi" }, insan: { tur: "figur", alt_tur: "insan", cesit: "yok" },
    pet: { tur: "figur", alt_tur: "pet", cesit: "yok" }, plaket: { tur: "plaket", alt_tur: "yok", cesit: "yok" },
    anahtarlik_figur: { tur: "anahtarlik", alt_tur: "yok", cesit: "figur" }, model: { tur: "figur", alt_tur: "model", cesit: "yok" } };
  s.V6_3 = JSON.stringify(iz.istek) === JSON.stringify(bek);
  // V6-5 (istemci): eski `hayvan_model` oturum kodu + eski iş kaydı (alt_tur hayvan_model) -> çökmez, pet kartı seçili.
  const eE = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null, { ssTur: "hayvan_model" });
  const eK = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), { is: "e".repeat(32), tur: "figur", olcu: 100, alt_tur: "hayvan_model" },
    { asama: "bekliyor" }, { zamanlayici: true });
  const secili = (x) => kartlarOku(x.bolum).filter((k) => k.classList.contains("secili")).map((k) => k.getAttribute("data-kart"));
  iz.eski = { oturum: secili(eE), kayit: secili(eK), istisna: eE.istisna + eK.istisna };
  s.V6_5i = JSON.stringify(iz.eski.oturum) === '["pet"]' && JSON.stringify(iz.eski.kayit) === '["pet"]' && iz.eski.istisna === 0;
  // V6-6: DOM metninde (① + insan ② + pet ②) "büst" / "yapboz" / "Portre için" 0.
  const eI = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null, { kart: "insan" });
  const eP = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null, { kart: "pet" });
  const yasak = (b) => (b.textContent.match(/büst|yapboz|portre için/gi) || []).length;
  iz.dom = [yasak(e.bolum), yasak(eI.bolum), yasak(eP.bolum), eI.istisna + eP.istisna];
  s.V6_6 = JSON.stringify(iz.dom) === "[0,0,0,0]";
  // V6-7 (BaBa 22:3x; eski "figür 60–200" iddiası MODEL BAŞINA): figür zarfı 41–300 · insan 41–105 · pet 60–136 · model
  // 60–300 · plaket 60–300 · anahtarlık 30–köprü tavanı AYNEN (beklenen sayılar BAĞIMSIZ). İstemci sürgüsü kartın modeline
  // süzülür: açılış 60 mm, en uç (sürgü max) insan 105 · pet 136 · model 300 — fiyat satırı sürgüden okunur.
  const eM = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null, { kart: "model" });
  const ar = (k) => { const a = V.olcuAraligi(k); return a ? [a.en_az, a.en_cok] : null; };
  const ma = (m) => { const a = V.modelOlcuAraligi("figur", m); return a ? [a.en_az, a.en_cok] : null; };
  iz.aralik = { figur: ar("figur"), insan: ma("insan"), pet: ma("pet"), model: ma("model"), plaket: ar("plaket"),
                anahtarlik: ar("anahtarlik") };
  iz.surgu = { insan: [eI.surguFiyat[0], eI.kaydir], pet: [eP.surguFiyat[0], eP.kaydir], model: [eM.surguFiyat[0], eM.kaydir] };
  s.V6_7 = JSON.stringify(iz.aralik) ===
      '{"figur":[41,300],"insan":[41,105],"pet":[60,136],"model":[60,300],"plaket":[60,300],"anahtarlik":[30,300]}' &&
    JSON.stringify(iz.surgu) === '{"insan":["60 mm → 600 TL","105 mm → 1.050 TL"],"pet":["60 mm → 600 TL","136 mm → 1.360 TL"],' +
      '"model":["60 mm → 600 TL","300 mm → 3.000 TL"]}' &&
    V.fiyatKurus("figur", 60) === 60000 && V.fiyatKurus("plaket", 300) === 300000 && V.fiyatKurus("anahtarlik", 30) === 60000;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
// Sunucu: /foto/onizleme figür alt türü -> sağlayıcı `prompt` (tek yer FIGUR_ALT_ISTEM); eski hayvan_model -> pet.
async function v6Sunucu(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('insan', 1, 'x'), ('pet', 1, 'x'), ('model', 1, 'x')").run();
  let ipNo = 0;
  const cag = async (govde) => {
    const u = "https://pruvo3d.com/api/shop/foto/onizleme";
    const r = await fm.fotoUclari(new Request(u, { method: "POST", headers: { "CF-Connecting-IP": "10.0.66." + (++ipNo),
      "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e2, new URL(u), "/foto/onizleme", null);
    let v = null; try { v = await r.json(); } catch (er) { v = null; }
    return { kod: r.status, v };
  };
  const s = {}, iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "figur" ? 1 : asilOrnek(kod));
  const olcu = VERI.olcuBaslangic("figur");
  const istem = async (alt) => {
    const p0 = P.protoGovde.length, c0 = protoSayisi();
    const r = await cag(onizlemeGovde({ tur: "figur", olcu_mm: olcu, ...(alt === undefined ? {} : { alt_tur: alt }) }));
    const g = P.protoGovde.slice(p0);
    return { kod: r.kod, hata: r.v && r.v.hata, cagri: protoSayisi() - c0,
      prompt: g.length === 1 ? (Object.prototype.hasOwnProperty.call(g[0], "prompt") ? g[0].prompt : "ALAN-YOK") : null };
  };
  try {
    iz.insan = await istem("insan"); iz.pet = await istem("pet"); iz.model = await istem("model");
    iz.eski = await istem("hayvan_model"); iz.yok = await istem(undefined); iz.gecersiz = await istem("bust");
  } finally { VERI.ornekSayisi = asilOrnek; }
  const ok = (x) => x.kod === 200 && x.cagri === 1 && typeof x.prompt === "string" && x.prompt !== "ALAN-YOK";
  s.V6_4 = ok(iz.insan) && ok(iz.pet) && ok(iz.model) &&
    /ayakta/i.test(iz.insan.prompt) && /ayakta/i.test(iz.pet.prompt) && !/ayakta/i.test(iz.model.prompt) &&
    /tek kişi/.test(iz.insan.prompt) && /tek hayvan/.test(iz.pet.prompt) &&
    ![iz.insan, iz.pet, iz.model].some((x) => V6_YASAK_ISTEM.test(x.prompt)) &&
    // 6 MODEL: alt tursuz figur istegi hicbir modele cozulmez -> 400 model-kapali, saglayici 0 (fail-closed).
    iz.yok.kod === 400 && iz.yok.hata === "model-kapali" && iz.yok.cagri === 0 &&
    iz.gecersiz.kod === 400 && iz.gecersiz.hata === "gecersiz-alt-tur" && iz.gecersiz.cagri === 0;
  s.V6_5s = ok(iz.eski) && iz.eski.prompt === iz.pet.prompt;
  k.kapat();
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("V6) 6 MODEL — ① kartlar · ① cümlesi · kart→istek · sunucu istemi · eski hayvan_model · büst/yapboz 0 · aralıklar");
{
  const hepsi = async (kaynak, fm) => {
    const i = await v6Istemci(kaynak), v = await v6Sunucu(fm);
    const s = { V6_1: i.V6_1, V6_2: i.V6_2, V6_3: i.V6_3, V6_4: v.V6_4, V6_5: i.V6_5i && v.V6_5s, V6_6: i.V6_6, V6_7: i.V6_7 };
    Object.defineProperty(s, "iz", { value: { ...i.iz, sunucu: v.iz }, enumerable: false });
    return s;
  };
  const s = await hepsi(EKRAN_KAYNAK, foto);
  const z = s.iz;
  ol("V6-1 ① 6 kart, Okan sırası + adları birebir; büst/yapboz /acik'te AÇIK iken kart 0", s.V6_1, JSON.stringify([z.kod, z.ad]));
  ol("V6-2 ① cümlesi açık kartlardan: 6 kart '6 seçenekten …' (adlar) · fikstür 3 kart '3 seçenekten …'", s.V6_2, JSON.stringify([z.c6, z.c3]));
  ol("V6-3 kart → istek: insan/pet/model → figur + alt_tur · anahtarlık yazı/figür → anahtarlik + çeşit · plaket → plaket", s.V6_3,
     JSON.stringify(z.istek));
  ol("V6-4 sunucu istemi alt türe göre: 'ayakta' insan+pet VAR, model YOK · yasak kelime 0 · alt türsüz istek 400 model-kapali · geçersiz alt tür 400 (sağlayıcı 0)",
     s.V6_4, JSON.stringify(z.sunucu));
  ol("V6-5 eski hayvan_model: oturum kodu + iş kaydı → pet kartı (istisna 0) · sunucu hayvan_model → pet istemi", s.V6_5,
     JSON.stringify([z.eski, z.sunucu.eski]));
  ol("V6-6 DOM metninde 'büst' / 'yapboz' / 'Portre için' 0 (① + insan ② + pet ②)", s.V6_6, JSON.stringify(z.dom));
  ol("V6-7 aralıklar MODEL BAŞINA: figür zarfı 41–300 · insan 41–105 · pet 60–136 · model 60–300 · plaket 60–300 · anahtarlık 30–300 (köprü) · istemci sürgüsü açılış 60, uç 105/136/300", s.V6_7, JSON.stringify([z.aralik, z.surgu]));
  const V6_MUT = [
    ["V6-M1 alt tür eşlemesi pet -> hayvan_model'e döner", "e", '{ kod: "pet", tur: "figur", alt: "pet",',
     // kart alt türü kayıttaki (pet) alt türle de çelişir -> kayıttan pet kartı geri yüklenemez (V6_5); sürgü modelin
     // ölçü satırını bulamaz (hayvan_model olcu_modelleri'nde YOK) -> pet sürgüsü boş (V6_7, 22:3x).
     '{ kod: "pet", tur: "figur", alt: "hayvan_model",', ["V6_3", "V6_5", "V6_7"]],
    ["V6-M2 ① cümlesi sabite döner", "e", "    if (n === 1) return birinciAciklama();\n",
     "    if (n === 1) return \"6 seçenekten birini seç: Anahtarlık – yazı, İnsan figürü (ayakta), Pet figürü (ayakta), Kabartma plaket, Anahtarlık – figür ya da Model figür.\";\n",
     ["V6_2"]],
    ["V6-M3 büst kartı koşulsuz çizilir", "e", "  var KARTLAR = [\n",
     "  var KARTLAR = [\n    { kod: \"bust\", tur: \"bust\", alt: null, ad: \"Büst\", ret: \"Büst için yüzü net görünen bir portre fotoğrafı gerekir.\" },\n",
     ["V6_1", "V6_2", "V6_6"]],
    ["V6-K0 KONTROL (yorum)", "e", "  function birinciAciklama() {\n", "  // kontrol\n  function birinciAciklama() {\n", []],
  ];
  for (const [ad, hedef, capa, yerine, olmeli] of V6_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await hepsi(EKRAN_KAYNAK.replace(capa, yerine), foto);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- MD) MODEL DUZEYINDE ACIKLIK (6 model, 10 Eki)
// Ücretli prova: uçtan uca YALNIZ anahtarlik_yazi + plaket geçti -> canlıda yalnız onlar. D1 foto_acik MODEL kodu taşır;
// eski tür satırı (figur/anahtarlik) tek başına HİÇBİR kartı açmaz; sunucu kapalı modelde 400 model-kapali (sağlayıcı 0);
// panel örnek ucu kapalı modelde de çalışır; sipariş kapısı önizlemeden sonra kapanan modeli bağlamaz.
const MD_GOC = fs.readFileSync(path.join(SHOP, "..", "tools", "d1-goc", "2026-10-10-foto-model-acik.sql"), "utf8");
async function mdSenaryo(fm, kaynak) {
  const s = {}, iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = () => 1;
  const ahSecim = { plaka_renk: "Beyaz", yazi_renk: "Siyah", govde_malzeme: "PLA" };
  const kurulum = async (kodlar) => {
    const k = koprukur(); await k.hazir;
    const e = envKur(k.d1, r2Kur());
    for (const t of kodlar) { await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, 'x')").bind(t).run(); }
    return { k, e };
  };
  let ip = 0;
  const uc = async (e, yol, govde) => {
    const u = "https://pruvo3d.com/api/shop" + yol;
    const r = await fm.fotoUclari(new Request(u, govde ? { method: "POST", headers: { "CF-Connecting-IP": "10.0.88." + (++ip),
      "Content-Type": "application/json" }, body: JSON.stringify(govde) } : { headers: { "CF-Connecting-IP": "10.0.89." + (++ip) } }),
      e, new URL(u), yol, null);
    let v = null; try { v = await r.json(); } catch (er) { v = null; }
    return { kod: r.status, v };
  };
  const figur = (alt) => onizlemeGovde({ tur: "figur", olcu_mm: VERI.olcuBaslangic("figur"), alt_tur: alt });
  const ahFigur = () => onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, cesit: "figur", secim: ahSecim });
  const proto = async (f) => { const c0 = protoSayisi(); const r = await f(); return { kod: r.kod, hata: r.v && r.v.hata, cagri: protoSayisi() - c0 }; };
  const V = veriYukle(VERI_KAYNAK);
  const kartlar = (b) => [...b.agac()].filter((n) => n.classList.contains("foto-uretim-kart")).map((n) => n.getAttribute("data-kart"));
  const birinci = (b) => ([...b.agac()].find((n) => n.classList.contains("foto-uretim-pencere-aciklama")) || {}).textContent || "";
  try {
    // MD1: yalnız plaket + anahtarlik_yazi açık -> sunucu /acik modeller tam o ikisi; istemci ① 2 kart, "2 seçenekten…".
    const a = await kurulum(["plaket", "anahtarlik_yazi"]);
    const ac = await uc(a.e, "/foto/acik");
    iz.acik1 = { turler: ((ac.v && ac.v.turler) || []).map((t) => t.kod).sort(), modeller: ac.v && ac.v.modeller };
    const e1 = await ekranKos(kaynak, V, ac.v);
    iz.kart1 = kartlar(e1.bolum); iz.c1 = birinci(e1.bolum);
    s.MD1 = JSON.stringify(iz.acik1.modeller) === '["anahtarlik_yazi","plaket"]' &&
      JSON.stringify(iz.kart1) === '["anahtarlik_yazi","plaket"]' && iz.c1.startsWith("2 seçenekten") &&
      !iz.kart1.some((k) => ["anahtarlik_figur", "insan", "pet", "model"].includes(k)) && e1.istisna === 0;
    // MD2: kapalı model sunucuda 400 model-kapali, sağlayıcı 0 — tür AÇIKKEN de (insan açık / pet kapalı;
    // anahtarlik_yazi açık / anahtarlik_figur kapalı). Kontrol: açık insan 200, sağlayıcı 1.
    const b = await kurulum(["plaket", "anahtarlik_yazi", "insan"]);
    iz.ma2 = { pet: await proto(() => uc(b.e, "/foto/onizleme", figur("pet"))),
               ahFigur: await proto(() => uc(b.e, "/foto/onizleme", ahFigur())),
               insan: await proto(() => uc(b.e, "/foto/onizleme", figur("insan"))) };
    s.MD2 = iz.ma2.pet.kod === 400 && iz.ma2.pet.hata === "model-kapali" && iz.ma2.pet.cagri === 0 &&
      iz.ma2.ahFigur.kod === 400 && iz.ma2.ahFigur.hata === "model-kapali" && iz.ma2.ahFigur.cagri === 0 &&
      iz.ma2.insan.kod === 200 && iz.ma2.insan.cagri === 1;
    // MD3: eski tür satırları ('figur', 'anahtarlik') tek başına -> /acik tür 0 + model 0, kart 0, önizleme 400 sağlayıcı 0.
    const c = await kurulum(["figur", "anahtarlik"]);
    const ac3 = await uc(c.e, "/foto/acik");
    const e3 = await ekranKos(kaynak, V, ac3.v);
    iz.ma3 = { turler: ((ac3.v && ac3.v.turler) || []).map((t) => t.kod), modeller: ac3.v && ac3.v.modeller, kart: kartlar(e3.bolum),
               insan: await proto(() => uc(c.e, "/foto/onizleme", figur("insan"))),
               yazi: await proto(() => uc(c.e, "/foto/onizleme", onizlemeGovde({ tur: "anahtarlik", olcu_mm: AH_MM, cesit: "yazi" }))) };
    s.MD3 = iz.ma3.turler.length === 0 && JSON.stringify(iz.ma3.modeller) === "[]" && iz.ma3.kart.length === 0 &&
      iz.ma3.insan.kod === 400 && iz.ma3.insan.cagri === 0 && iz.ma3.yazi.kod === 400 && iz.ma3.yazi.cagri === 0;
    // MD4: panel örnek ucu kapalı modelde (pet; D1 yalnız plaket) ÇALIŞIR: 200 + sağlayıcı 1.
    const u4 = "https://pruvo3d.com/api/shop/yonet/foto/ornek-onizleme";
    const p0 = protoSayisi();
    const r4 = await fm.panelOrnekOnizleme(new Request(u4, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gorsel: GORSEL, olcu_mm: 100, tur: "figur", alt_tur: "pet" }) }), a.e, Date.now(), null);
    let v4 = null; try { v4 = await r4.json(); } catch (er) { v4 = null; }
    iz.ma4 = { kod: r4.status, is: !!(v4 && v4.is), cagri: protoSayisi() - p0 };
    s.MD4 = iz.ma4.kod === 200 && iz.ma4.is && iz.ma4.cagri === 1;
    // MD5: sipariş kapısı — hazır figür işi alt_tur 'pet' (pet kapalı) -> model-kapali; 'insan' (açık) -> satır.
    const iso = new Date().toISOString();
    const isKur = async (no, alt) => {
      await b.k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, alt_tur)" +
        " VALUES (?, 'figur', 100, 'z', ?, 'hazir', ?, ?, ?)").bind(no, iso, "gorev-ma-" + alt, iso, alt).run();
      return fm.fotoKalemFiyatla(b.e, { foto_is: no, olcu_mm: 100, adet: 1, renkler: ["Beyaz"] }, Date.now());
    };
    const fPet = await isKur("ma5p" + "0".repeat(28), "pet"), fIns = await isKur("ma5i" + "0".repeat(28), "insan");
    iz.ma5 = { pet: fPet.hata || "satir", insan: fIns.hata || (fIns.satir ? "satir" : null) };
    s.MD5 = !!fPet.hata && fPet.hata.hata === "model-kapali" && !!fIns.satir;
    // MD6: göç SQL (tools/d1-goc/2026-10-10-foto-model-acik.sql) — eski anahtarlik+figur+plaket+bust -> anahtarlik_yazi,
    // bust, plaket (figür modeli AÇILMAZ); iki kez koşulunca aynı sonuç.
    const g = await kurulum(["anahtarlik", "figur", "plaket", "bust"]);
    const kos = async () => { for (const q of MD_GOC.split("\n").filter((l) => !l.startsWith("--")).join("\n").split(";").map((x) => x.trim()).filter(Boolean)) { await g.k.d1.prepare(q).run(); } };
    await kos();
    const r6a = (await g.k.d1.prepare("SELECT tur FROM foto_acik WHERE acik = 1 ORDER BY tur").all()).results.map((x) => x.tur);
    await kos();
    const r6b = (await g.k.d1.prepare("SELECT tur FROM foto_acik WHERE acik = 1 ORDER BY tur").all()).results.map((x) => x.tur);
    iz.ma6 = [r6a, r6b];
    s.MD6 = JSON.stringify(r6a) === '["anahtarlik_yazi","bust","plaket"]' && JSON.stringify(r6b) === JSON.stringify(r6a);
    // MD7: panel açma ucu model kodu alır; modelli türün eski tür kodu 400 gecersiz-tur.
    const pa = async (tur) => (await fm.panelFotoAcik(new Request("https://pruvo3d.com/x", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur, acik: true }) }), a.e, Date.now())).status;
    iz.ma7 = { pet: await pa("pet"), anahtarlik_figur: await pa("anahtarlik_figur"), figur: await pa("figur"),
               anahtarlik: await pa("anahtarlik"), bust: await pa("bust") };
    s.MD7 = JSON.stringify(iz.ma7) === '{"pet":200,"anahtarlik_figur":200,"figur":400,"anahtarlik":400,"bust":200}';
    for (const x of [a, b, c, g]) { x.k.kapat(); }
  } finally { VERI.ornekSayisi = asilOrnek; }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("MD) MODEL DÜZEYİNDE AÇIKLIK — D1 foto_acik model kodu · sunucu model kapısı · /acik modeller · eski tür satırı 0 · panel örnek · göç SQL");
{
  const s = await mdSenaryo(foto, EKRAN_KAYNAK);
  const z = s.iz;
  ol("MD1 yalnız plaket + anahtarlik_yazi açık -> /acik modeller 2 · ① 2 kart, '2 seçenekten…' · anahtarlık–figür/insan/pet/model kartı 0", s.MD1,
     JSON.stringify([z.acik1, z.kart1, z.c1]));
  ol("MD2 kapalı model (pet / anahtarlik_figur) tür açıkken de 400 model-kapali, sağlayıcı 0 · açık insan 200 sağlayıcı 1", s.MD2, JSON.stringify(z.ma2));
  ol("MD3 eski tür satırı (figur/anahtarlik) tek başına: /acik tür 0 + model 0 · kart 0 · önizleme 400 sağlayıcı 0", s.MD3, JSON.stringify(z.ma3));
  ol("MD4 panel örnek ucu kapalı modelde (pet) çalışır: 200 + sağlayıcı 1", s.MD4, JSON.stringify(z.ma4));
  ol("MD5 sipariş kapısı: hazır figür işi alt_tur pet (kapalı) -> model-kapali · insan (açık) -> satır", s.MD5, JSON.stringify(z.ma5));
  ol("MD6 göç SQL: anahtarlik+figur+plaket+bust -> anahtarlik_yazi+bust+plaket (figür modeli açılmaz) · ikinci koşum aynı", s.MD6, JSON.stringify(z.ma6));
  ol("MD7 panel açma: pet/anahtarlik_figur/bust 200 · eski figur/anahtarlik 400", s.MD7, JSON.stringify(z.ma7));
  const MD_SUNUCU = [
    ["M-MD-SUNUCU sunucu model kapısı kalktı", "    if (!modelAcik(await acikAnahtari(env), g.tur, VERI.cesitCoz(g.tur, g.cesit), at)) {",
     "    if (false) {", ["MD2"]],
    ["M-MD-TUR tür satırı tüm modelleri açar", '    return new Set((r.results || []).map((x) => x.tur).filter((k) => typeof k === "string"));',
     '    return new Set((r.results || []).flatMap((x) => [x.tur, ...MODELLER.filter((m) => m.tur === x.tur).map((m) => m.kod)]).filter((k) => typeof k === "string"));',
     ["MD3"]],
    ["M-MD-SIPARIS sipariş model kapısı kalktı", '  if (!modelAcik(acik, is.tur, is.cesit || "", isAlt)) {', "  if (false) {", ["MD5"]],
    ["M-MD-K0 KONTROL (yorum)", "export function modelliTur(tur) {", "// kontrol\nexport function modelliTur(tur) {", []],
  ];
  for (const [ad, capa, yerine, olmeli] of MD_SUNUCU) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await mdSenaryo(fm, EKRAN_KAYNAK);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
  const capaI = "      if (modeller.indexOf(k.kod) < 0) continue;\n";
  if (EKRAN_KAYNAK.split(capaI).length - 1 !== 1) { ol("M-MD-ISTEMCI capa bulundu", false, capaI); } else {
    const m = await mdSenaryo(foto, EKRAN_KAYNAK.replace(capaI, ""));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol("M-MD-ISTEMCI istemci kart model kontrolü kalktı -> KIRMIZI tam olarak [MD1]", JSON.stringify(kir) === '["MD1"]', JSON.stringify(kir));
  }
}

// ================================================================ FG — FİGÜR ÖLÇÜSÜ MODEL BAŞINA (BaBa 10 Eki 22:3x)
// Eski tek aralık (60–200) yerine figur kaydı `olcu_modelleri` (TEK kaynak): insan 41–105 · pet 60–136 · model 60–300
// (tavan = TeKiN figur_denge max_guvenli_mm aşağı — pet 11 Eki 792ac60: 136,5 -> 136; insan tabanı min_guvenli_mm 40,7
// yukarı); zarf 41–300, açılış 60. Pet SINIR vakası: 136 GEÇER (sürgü ucu) · 137 RED (hiçbir ızgarada yok -> 400).
// Beklenen sayılar BAĞIMSIZ (kayıttan okunmaz). Sunucu önizleme ucu + sipariş kapısı modelin dışını 400 gecersiz-olcu
// ile reddeder: her model alt/üst sınır (OK) + dışı (RED). RED değerlerinden ızgaradakiler (insan 110 · pet 50/140 ·
// model 50) yalnız MODEL kontrolüyle düşer (fiyat formülü zarfa açık) — sunucu kontrolü kalkınca KIRMIZI yananlar onlar.
const FG_SINIR = { insan: [41, 105], pet: [60, 136], model: [60, 300] };
const FG_RED = { insan: [40, 110], pet: [50, 59, 137, 140], model: [50, 59, 310] };
async function fgSenaryo(fm, V) {
  const s = {}, iz = {};
  const ad = ["turBul", "olcuAraligi", "olcuGecerli", "olcuSecenekleri", "fiyatKurus", "olcuBaslangic", "modelOlcuAraligi",
              "modelOlcuSecenekleri", "modelOlcuGecerli"];
  const yedek = {};
  for (const a of ad) { yedek[a] = VERI[a]; VERI[a] = V[a]; }
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = () => 1;
  const k = koprukur(); await k.hazir;
  const e = envKur(k.d1, r2Kur());
  let ip = 0;
  try {
    for (const t of ["insan", "pet", "model"]) { await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES (?, 1, 'x')").bind(t).run(); }
    const a = VERI.olcuAraligi("figur") || {};
    iz.zarf = [a.en_az, a.en_cok, VERI.olcuBaslangic("figur")];
    iz.model = {};
    for (const m of Object.keys(FG_SINIR)) { const x = VERI.modelOlcuAraligi("figur", m) || {}; iz.model[m] = [x.en_az, x.en_cok]; }
    s.FG1 = JSON.stringify(iz.zarf) === "[41,300,60]" && JSON.stringify(iz.model) === JSON.stringify(FG_SINIR) &&
      VERI.modelOlcuAraligi("figur", "") === null && VERI.modelOlcuAraligi("figur", "hayvan_model") === null;
    s.FG2 = VERI.fiyatKurus("figur", 41) === 60000 && VERI.fiyatKurus("figur", 105) === 105000 &&
      VERI.fiyatKurus("figur", 136) === 136000 && VERI.fiyatKurus("figur", 137) === null &&
      VERI.fiyatKurus("figur", 138) === null && VERI.fiyatKurus("figur", 300) === 300000 && VERI.fiyatKurus("figur", 299) === null;
    // Sunucu önizleme ucu (müşteri): sınır OK -> 200 sağlayıcı 1 · dışı -> 400 gecersiz-olcu sağlayıcı 0.
    const uc = async (govde) => {
      const u = "https://pruvo3d.com/api/shop/foto/onizleme";
      const c0 = protoSayisi();
      const r = await fm.fotoUclari(new Request(u, { method: "POST", headers: { "CF-Connecting-IP": "10.0.77." + (++ip),
        "Content-Type": "application/json" }, body: JSON.stringify(govde) }), e, new URL(u), "/foto/onizleme", null);
      let v = null; try { v = await r.json(); } catch (er) { v = null; }
      return r.status + (r.status === 200 ? "" : ":" + (v && v.hata)) + "/" + (protoSayisi() - c0);
    };
    iz.onz = {};
    for (const m of Object.keys(FG_SINIR)) {
      for (const mm of FG_SINIR[m].concat(FG_RED[m])) { iz.onz[m + mm] = await uc(onizlemeGovde({ tur: "figur", olcu_mm: mm, alt_tur: m })); }
    }
    s.FG3 = Object.keys(FG_SINIR).every((m) => FG_SINIR[m].every((mm) => iz.onz[m + mm] === "200/1") &&
      FG_RED[m].every((mm) => iz.onz[m + mm] === "400:gecersiz-olcu/0"));
    // Sipariş kapısı (fotoKalemFiyatla): hazır figür işi (alt tür kayıtta) + sepet ölçüsü -> sınır satır · dışı 400.
    const iso = new Date().toISOString();
    iz.sip = {};
    let n = 0;
    for (const m of Object.keys(FG_SINIR)) {
      for (const mm of FG_SINIR[m].concat(FG_RED[m])) {
        const no = "fg" + String(++n).padStart(30, "0");
        await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, alt_tur)" +
          " VALUES (?, 'figur', 60, 'z', ?, 'hazir', ?, ?, ?)").bind(no, iso, "gorev-" + no, iso, m).run();
        const f = await fm.fotoKalemFiyatla(e, { foto_is: no, olcu_mm: mm, adet: 1, renkler: ["Beyaz"] }, Date.now());
        iz.sip[m + mm] = f.satir ? "satir" : f.kod + ":" + (f.hata && f.hata.hata);
      }
    }
    s.FG4 = Object.keys(FG_SINIR).every((m) => FG_SINIR[m].every((mm) => iz.sip[m + mm] === "satir") &&
      FG_RED[m].every((mm) => iz.sip[m + mm] === "400:gecersiz-olcu"));
    // Üreteç ölçü doğrulaması tür zarfını kullanır: 40 aralık dışı, 41 aralıkta.
    const oj = (L) => ({ sozlesme: 1, kategori: "figur", uzun_kenar_mm: L, kutu_mm: { x: L, y: L, z: L }, renk_sayisi: 1, sizdirmaz: true });
    iz.ur = [fm.uretecOlcuDogrula(oj(40), { tur: "figur", olcu_mm: 40 }), fm.uretecOlcuDogrula(oj(41), { tur: "figur", olcu_mm: 41 })];
    s.FG5 = iz.ur[0] === "olcu-aralik-disi" && iz.ur[1] !== "olcu-aralik-disi";
  } finally {
    for (const a of ad) { VERI[a] = yedek[a]; }
    VERI.ornekSayisi = asilOrnek;
    k.kapat();
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("FG) FİGÜR ÖLÇÜSÜ MODEL BAŞINA — insan 41–105 · pet 60–136 · model 60–300 (BaBa 22:3x; figur_denge max_guvenli_mm)");
{
  const s = await fgSenaryo(foto, veriYukle(VERI_KAYNAK));
  const z = s.iz;
  ol("FG1 figür zarfı 41–300, açılış 60 · insan 41–105 · pet 60–136 · model 60–300 · alt türsüz/eski kod -> null", s.FG1, JSON.stringify([z.zarf, z.model]));
  ol("FG2 fiyat: 41 -> 600 TL (taban) · 105/136/300 -> 1.050/1.360/3.000 TL · ızgara dışı 137/138 (eski pet tavanı)/299 -> null", s.FG2, "");
  ol("FG3 sunucu önizleme: her model alt/üst sınır 200 (sağlayıcı 1) · dışı (insan 40/110 · pet 50/59/137/140 · model 50/59/310) 400 gecersiz-olcu (sağlayıcı 0)", s.FG3, JSON.stringify(z.onz));
  ol("FG4 sipariş kapısı: her model alt/üst sınır satır · dışı 400 gecersiz-olcu", s.FG4, JSON.stringify(z.sip));
  ol("FG5 üreteç ölçü doğrulaması figür zarfı: 40 olcu-aralik-disi · 41 aralıkta", s.FG5, JSON.stringify(z.ur));
  const FG_MUT = [
    ["M-FG-ONIZLEME sunucu önizleme model ölçü kontrolü kalktı", "  if (!VERI.modelOlcuGecerli(tur.kod, altTur, olcu)) { return fjson({ hata: \"gecersiz-olcu\" }, 400); }",
     "  if (false) { return null; }", ["FG3"]],
    ["M-FG-SIPARIS sipariş kapısı model ölçü kontrolü kalktı", "  if (!VERI.modelOlcuGecerli(tur.kod, isAlt, mm)) { return { hata: { hata: \"gecersiz-olcu\" }, kod: 400 }; }",
     "  if (false) { return null; }", ["FG4"]],
  ];
  for (const [ad, capa, yerine, olmeli] of FG_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await fgSenaryo(fm, veriYukle(VERI_KAYNAK));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
  // VERİ mutantı (bellek kopyası): insan tavanı 105 -> 200 (eski tek aralık) -> FG1 + FG3 + FG4 KIRMIZI; 105 hiçbir
  // modelin ızgarasında kalmaz (insan 100/110) -> fiyatı null (FG2).
  const capaV = "          insan: { en_az: 41, en_cok: 105 },";
  const mv = VERI_KAYNAK.split(capaV).length === 2
    ? await fgSenaryo(foto, veriYukle(VERI_KAYNAK.replace(capaV, "          insan: { en_az: 41, en_cok: 200 },"))) : null;
  const kirV = mv ? Object.keys(mv).filter((x) => mv[x] !== true).sort() : null;
  ol("M-FG-VERI insan tavanı 200 -> KIRMIZI tam olarak [FG1,FG2,FG3,FG4]", JSON.stringify(kirV) === '["FG1","FG2","FG3","FG4"]', JSON.stringify(kirV));
  // VERİ mutantı: pet tavanı 136 -> 138 (10 Eki eski ölçüm, 11 Eki 792ac60 GEÇERSİZ) -> 136 hiçbir ızgarada kalmaz
  // (pet 130/138, model 130/140): FG1 aralık · FG2 136 fiyatı null + 138 fiyatlanır · FG3/FG4 pet 136 sınırı 400.
  const capaP = "          pet: { en_az: 60, en_cok: 136 },";
  const mp = VERI_KAYNAK.split(capaP).length === 2
    ? await fgSenaryo(foto, veriYukle(VERI_KAYNAK.replace(capaP, "          pet: { en_az: 60, en_cok: 138 },"))) : null;
  const kirP = mp ? Object.keys(mp).filter((x) => mp[x] !== true).sort() : null;
  ol("M-FG-PET pet tavanı 138 (eski) -> KIRMIZI tam olarak [FG1,FG2,FG3,FG4]", JSON.stringify(kirP) === '["FG1","FG2","FG3","FG4"]', JSON.stringify(kirP));
}

// ================================================================ DZ — ANAHTARLIK–FİGÜR ② DÜRÜSTLÜK CÜMLESİ (ArTisT 874b2a85)
// ② dürüstlük kutusu: Anahtarlık – figür kartında stilize-yorum cümlesi (çeşit paragrafı) VAR (beklenen metin BAĞIMSIZ,
// pazarlama metni AYNEN), Anahtarlık – yazı kartında YOK; türün kendi notu (halka/zincir) iki kartta da AYNEN (ilk
// paragraf); insan figüründe çeşit paragrafı YOK (figür TEK cümle). Örnek notu paragrafı bu vakanın ekseni DEĞİL.
const DZ_CUMLE = "Önizleme fotoğrafının stilize bir yorumudur; basılmış anahtarlık en çok 4 renkli, sadeleştirilmiş bir hâlidir ve tam kopyası değildir (küçük ayrıntılar sadeleşir).";
const DZ_HALKA = "Metal halka ve zincir dahil değildir; zincir ya da halka takılan kulakçıklı plastik gövde (delik Ø 3,5–4 mm).";
async function dzSenaryo(kaynak, V) {
  const s = {}, iz = {};
  const kutu = async (kart) => {
    const e = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null, { kart });
    const d = [...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-durustluk"));
    const c = d ? [...d.agac()].find((n) => n.classList.contains("foto-uretim-durustluk-cesit")) : null;
    return d && d.childNodes[0] ? [d.childNodes[0].textContent, c && !c.hidden ? c.textContent : ""] : null;
  };
  iz.figur = await kutu("anahtarlik_figur");
  iz.yazi = await kutu("anahtarlik");
  iz.insan = await kutu("insan");
  s.DZ1 = JSON.stringify(iz.figur) === JSON.stringify([DZ_HALKA, DZ_CUMLE]);
  s.DZ2 = JSON.stringify(iz.yazi) === JSON.stringify([DZ_HALKA, ""]);
  s.DZ3 = Array.isArray(iz.insan) && iz.insan[0] === (V.turBul("figur") || {}).durustluk && iz.insan[1] === "";
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("DZ) ANAHTARLIK–FİGÜR ② DÜRÜSTLÜK CÜMLESİ (ArTisT 874b2a85; yazı çeşidinde YOK)");
{
  const V = veriYukle(VERI_KAYNAK);
  const s = await dzSenaryo(EKRAN_KAYNAK, V);
  ol("DZ1 anahtarlık–figür ② kutusu: halka notu + stilize-yorum cümlesi (ArTisT AYNEN)", s.DZ1, JSON.stringify(s.iz.figur));
  ol("DZ2 anahtarlık–yazı ② kutusu: YALNIZ halka notu (stilize cümle YOK)", s.DZ2, JSON.stringify(s.iz.yazi));
  ol("DZ3 insan figürü ② kutusu TEK cümle (türün durustluk'u)", s.DZ3, JSON.stringify(s.iz.insan));
  // MUTANT: çeşit paragrafı basılmazsa DZ1 KIRMIZI; çeşit kaydı yerine tür kaydı okunursa (yazıda da basılır) DZ2.
  const capaI = '      S.durustCesitP.textContent = ck && ck.durustluk ? ck.durustluk : "";\n';
  const capaV = '          durustluk: "' + DZ_CUMLE + '",\n';
  const mI = EKRAN_KAYNAK.split(capaI).length === 2 ? await dzSenaryo(EKRAN_KAYNAK.replace(capaI, '      S.durustCesitP.textContent = "";\n'), V) : null;
  const mY = EKRAN_KAYNAK.split(capaI).length === 2
    ? await dzSenaryo(EKRAN_KAYNAK.replace(capaI, "      S.durustCesitP.textContent = " + JSON.stringify(DZ_CUMLE) + ";\n"), V) : null;
  const mV = VERI_KAYNAK.split(capaV).length === 2 ? await dzSenaryo(EKRAN_KAYNAK, veriYukle(VERI_KAYNAK.replace(capaV, ""))) : null;
  const kir = (m) => (m ? Object.keys(m).filter((x) => m[x] !== true).sort() : null);
  ol("M-DZ-ISTEMCI çeşit cümlesi basılmaz -> KIRMIZI tam olarak [DZ1]", JSON.stringify(kir(mI)) === '["DZ1"]', JSON.stringify(kir(mI)));
  ol("M-DZ-HER-CESIT cümle yazı çeşidine de basılır -> KIRMIZI tam olarak [DZ2,DZ3]", JSON.stringify(kir(mY)) === '["DZ2","DZ3"]', JSON.stringify(kir(mY)));
  ol("M-DZ-VERI çeşit kaydında cümle yok -> KIRMIZI tam olarak [DZ1]", JSON.stringify(kir(mV)) === '["DZ1"]', JSON.stringify(kir(mV)));
}

await new Promise((c) => setTimeout(c, 0));
ol("ASENKRON temiz kaynakta (EKRAN_KAYNAK) yakalanmamis istisna 0",
   ASENKRON_ISTISNA.filter((x) => x.temiz).length === 0, JSON.stringify(ASENKRON_ISTISNA.filter((x) => x.temiz).slice(0, 3)));

kopru.kapat();
await Promise.allSettled(ctx.bekleyen);
// ---------------------------------------------------------------- RENK = PALET A (BaBa 16:0x 2a, 10 Eki)
// Figür anahtarlıkta Renkli: köprü kolu renk_modu tek|palet -> VERI.cesitPaleti; fiyat farkı palet/figür türüyle AYNI
// mekanizma (VERI.secimliKurus, RENKLI_EK_YUZDE); sunucu satırı foto_renk_modu (palet | tek; alan yoksa koşucu tek).
async function rpaSenaryo(renkModuFn) {
  const asil = VERI.renkModu, asilOrnek = VERI.ornekSayisi;
  if (renkModuFn) { VERI.renkModu = renkModuFn; }
  // Tür hazırlığı örnek ister (c2a2 ile AYNI geçici yama; finally'de geri).
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" || kod === "figur" ? 1 : asilOrnek(kod));
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x')").run();
  const iso = new Date().toISOString(), fig = "rpa0" + "f".repeat(28);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, son_kontrol, cesit)" +
    " VALUES (?, 'anahtarlik', 60, 'z', ?, 'hazir', 'gorev-rpa', ?, 0, 'figur')").bind(fig, iso, iso).run();
  const s = {}, iz = {};
  try {
    const fiyatla = (ek) => foto.fotoKalemFiyatla(e2, { foto_is: fig, olcu_mm: AH_MM, adet: 1, ...ek }, Date.now());
    const R3 = ["Kırmızı", "Mavi", "Beyaz"];
    const fr = await fiyatla({ renkli: true, renkler: R3 });
    const f5 = await fiyatla({ renkli: true, renkler: ["Kırmızı", "Mavi", "Beyaz", "Siyah", "Sarı"] });
    const ft = await fiyatla({ renkler: ["Beyaz"] });
    const formul = Math.round(VERI.fiyatKurus("anahtarlik", AH_MM) * (100 + VERI.RENKLI_EK_YUZDE) / 100);
    iz.renkli = fr.satir ? { birim: fr.satir.birim_kurus, mod: fr.satir.foto_renk_modu, renkler: fr.satir.foto_renkler } : fr;
    iz.bes = f5.kod; iz.tek = ft.satir ? { birim: ft.satir.birim_kurus, mod: ft.satir.foto_renk_modu } : ft;
    iz.formul = formul;
    // RA1: figür + Renkli fiyatı = formül (60 mm: 600 TL × 1,15 = 690 TL), renkler kalemden, mod palet; 5 renk -> 400.
    s.RA1 = !!fr.satir && formul === 69000 && fr.satir.birim_kurus === formul &&
      fr.satir.birim_kurus === VERI.fiyatKurus("anahtarlik", AH_MM, { renkli: true, malzeme: "PLA" }) &&
      fr.satir.foto_renk_modu === "palet" && JSON.stringify(fr.satir.foto_renkler) === JSON.stringify(R3) && f5.kod === 400;
    // RA2: yazı çeşidinde Renkli YOK (radyo = renkliSunulur -> F.renkliSecilebilir AYNI fonksiyon), mod hep tek.
    s.RA2 = VERI.renkliSecilebilir("anahtarlik", "yazi") === false && VERI.cesitPaleti("anahtarlik", "yazi") === false &&
      VERI.renkModu("anahtarlik", "yazi", true) === "tek" && VERI.renkliSecilebilir("anahtarlik", "figur") === true;
    // RA3: tek renk figür (renkli alanı yok = eski sipariş biçimi) -> mod tek, fiyat ana renk (600 TL).
    s.RA3 = !!ft.satir && ft.satir.foto_renk_modu === "tek" && ft.satir.birim_kurus === 60000 &&
      VERI.renkModu("anahtarlik", "figur", undefined) === "tek";
  } finally {
    VERI.renkModu = asil; VERI.ornekSayisi = asilOrnek;
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("RPA) RENK = PALET A — figur anahtarlikta Renkli (kopru renk_modu), fiyat formulu, foto_renk_modu");
{
  const s = await rpaSenaryo(null);
  ol("RA1 figur + Renkli 60 mm = formul (600 TL x 1,15 = 690 TL; VERI.secimliKurus), renkler kalemden, foto_renk_modu palet; 5 renk 400",
     s.RA1, JSON.stringify(s.iz));
  ol("RA2 yazi cesidinde Renkli 0 (renkliSecilebilir yazi false, cesitPaleti false, mod tek); figur cesidinde var", s.RA2, "");
  ol("RA3 eski siparis bicimi (renkli yok) -> foto_renk_modu tek, 600 TL", s.RA3, JSON.stringify(s.iz.tek));
  const capa = 'return renkli === true && VERI.cesitPaleti(kod, cesit) ? "palet" : "tek";';
  const RPA_MUT = [
    ["RPA-M1 varsayilan palet'e doner (renkli yoksa palet)", 'return renkli !== false && VERI.cesitPaleti(kod, cesit) ? "palet" : "tek";', ["RA3"]],
    ["RPA-K0 KONTROL (ayni govde)", capa, []],
  ];
  for (const [ad, yerine, olmeli] of RPA_MUT) {
    if (VERI_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const V = veriYukle(VERI_KAYNAK.replace(capa, yerine));
    const m = await rpaSenaryo(V.renkModu);
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---------------------------------------------------------------- RY: RENKLİ SEÇİMİ OTURUM YENİLEMEDE KORUNUR (PARA)
// FotoOnizleme bulgusu (11 Eki): sayfa yenilenince oturum kaydındaki Renkli renkleri S.fotoRenkleri'ne yüklenir, ama
// form çizimindeki fotoRenkCikar(null) onları SIFIRLIYORDU -> renk seçici Beyaz'a döner, +%15 Renkli farkı SESSİZCE
// düşerdi. RY1 Renkli radyosu seçili · RY2 sepet satırı renkli + kayıttaki renkler + gösterim = Renkli formülü ·
// RY3 sunucunun kendi hesabı (fotoKalemFiyatla) = sepet gösterimi = Renkli formülü · RY4 KONTROL: Beyaz kaydı Beyaz kalır.
async function rySenaryo(kaynak) {
  const V = veriYukle(VERI_KAYNAK), IS = "a0" + "e".repeat(30), R3 = ["Kırmızı", "Mavi", "Beyaz"];
  const yukle = async (renkSecim, renkler) => {
    const sepet = [];
    const e = await ekranKos(kaynak, V, acikGercek(V, V6_TUM),
      { is: IS, tur: "anahtarlik", cesit: "figur", olcu: AH_MM, renk_secim: renkSecim, ...(renkler ? { renkler } : {}),
        malzeme: "PLA", onay: V.onay_surum },
      { asama: "hazir", tur: "anahtarlik", olcu_mm: AH_MM, gorsel: "/api/shop/foto/gorsel?is=" + IS,
        gecerlilik_bitis: "2099-01-01T00:00:00.000Z" },
      { turnstileOto: true, paletSahte: true, kaydir: false, sepet });
    const d = [...e.bolum.agac()];
    const radyo = d.find((n) => n.tagName === "INPUT" && n.name === "foto-renk" && n.checked);
    const b2 = d.find((n) => n.id === "foto-b2-onay");
    if (b2) { b2.checked = true; b2.tetikle("change"); }
    const sip = [...e.bolum.agac()].find((n) => n.id === "foto-sip-btn");
    if (sip) { sip.tetikle("click"); }
    return { renk: radyo ? radyo.value : null, satir: sepet[0] || null };
  };
  const s = {}, iz = {};
  const rk = await yukle("Renkli", R3), bz = await yukle("Beyaz", null);
  const renkliFormul = V.fiyatKurus("anahtarlik", AH_MM, { renkli: true, malzeme: "PLA" });
  const tekFormul = V.fiyatKurus("anahtarlik", AH_MM, { renkli: false, malzeme: "PLA" });
  iz.renkli = { renk: rk.renk, renkli: rk.satir && rk.satir.renkli, renkler: rk.satir && rk.satir.renkler,
                gosterim: rk.satir && rk.satir.gosterim_kurus, renkliFormul };
  iz.beyaz = { renk: bz.renk, renkli: bz.satir && bz.satir.renkli, gosterim: bz.satir && bz.satir.gosterim_kurus, tekFormul };
  s.RY1 = rk.renk === "Renkli";
  s.RY2 = !!rk.satir && rk.satir.renkli === true && JSON.stringify(rk.satir.renkler) === JSON.stringify(R3) &&
    renkliFormul === 69000 && rk.satir.gosterim_kurus === renkliFormul;
  // RY3: sunucu fiyatı kendisi hesaplar (gösterim /baslat'a gitmez) -> aynı kalemle sunucu birim fiyatı = gösterim.
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" || kod === "figur" ? 1 : asilOrnek(kod));
  const k = koprukur(); await k.hazir;
  try {
    const e2 = envKur(k.d1, r2Kur()), iso = new Date().toISOString();
    await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_figur', 1, 'x')").run();
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, son_kontrol, cesit)" +
      " VALUES (?, 'anahtarlik', ?, 'z', ?, 'hazir', 'gorev-ry', ?, 0, 'figur')").bind(IS, AH_MM, iso, iso).run();
    const sv = rk.satir ? await foto.fotoKalemFiyatla(e2, { foto_is: IS, olcu_mm: rk.satir.olcu_mm, adet: 1, renkli: rk.satir.renkli,
      renkler: rk.satir.renkler, malzeme: rk.satir.malzeme }, Date.now()) : null;
    iz.sunucu = sv && sv.satir ? sv.satir.birim_kurus : sv;
    s.RY3 = !!(sv && sv.satir) && sv.satir.birim_kurus === rk.satir.gosterim_kurus && sv.satir.birim_kurus === renkliFormul;
  } finally {
    VERI.ornekSayisi = asilOrnek; k.kapat();
  }
  s.RY4 = bz.renk === "Beyaz" && !!bz.satir && bz.satir.renkli === false && bz.satir.gosterim_kurus === tekFormul;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("RY) RENKLİ SEÇİMİ OTURUM YENİLEMEDE KORUNUR — fiyat +%15 sessizce düşmez; sunucu tutarı = istemci");
{
  const s = await rySenaryo(EKRAN_KAYNAK);
  ol("RY1 yenileme sonrası Renkli radyosu seçili", s.RY1, JSON.stringify(s.iz.renkli));
  ol("RY2 sepet satırı renkli + kayıttaki renkler + gösterim = Renkli formülü (690 TL)", s.RY2, JSON.stringify(s.iz.renkli));
  ol("RY3 sunucu birim fiyatı (kendi hesabı) = sepet gösterimi = Renkli formülü", s.RY3, JSON.stringify(s.iz));
  ol("RY4 KONTROL Beyaz kaydı Beyaz kalır (renkli false, 600 TL)", s.RY4, JSON.stringify(s.iz.beyaz));
  const capa = "          S.fotoRenkDosya = null;\n";
  const RY_MUT = [
    ["M-RY-SIFIR fotoRenkCikar(null) kayıttaki renkleri sıfırlar (eski kusur)", capa, "", ["RY1", "RY2", "RY3"]],
    ["M-RY-K0 KONTROL (aynı gövde)", capa, capa, []],
  ];
  for (const [ad, c, yerine, olmeli] of RY_MUT) {
    if (EKRAN_KAYNAK.split(c).length - 1 !== 1) { ol(ad + " capa bulundu", false, c); continue; }
    const m = await rySenaryo(EKRAN_KAYNAK.replace(c, yerine));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir) + " " + JSON.stringify(m.iz));
  }
}

// ---------------------------------------------------------------- SIM: ④ 4 RENK SİMÜLASYONU (Okan 11 Eki 16:0x)
// VERI.dortRenkSimule: sağlayıcının dokulu görseli piksel piksel palete boyanmaz (benekli gri-bej poster), BÖLGE
// tabanlı sadeleştirilir (yumuşatma · L'yi az ağırlıklandıran OKLab mesafesi + gölge bandı birleştirme · mod/adacık
// süzgeci · büyütme + ince kontur). Bölge sayımı VERI.simulasyonBolgeleri (aynı adımlar, küçük ölçek; 96 px'te 1:1).
// G gölgeli TEK renk yüzey (yumuşak gölge + sert düşen gölge ×0,3 + doku) -> TEK bölge, Mavi
// B 4 renk bloklu görsel (gölge + doku) -> 4 bölge, her blok kendi renginde, sınırlar yerinde
// A adacık: 4×4 benekler SİLİNİR, 10×10 blok KALIR (eşik opak alanın %0,15'i)
// T saydam piksel bayt bayt AYNEN; opak piksel yalnız palet rengi ya da onun kontur koyusu
// Y tek ana renk (Beyaz): r = g = b, gölge düzeyleri kalır (≥ 8), doku/benek bastırılır (komşu farkı < girdinin yarısı)
// N bilinmeyen renk / boş palet / boyut uyuşmazlığı -> null, piksel değişmez
// E ④ çizimi F.dortRenkSimule (eski paleteIndirge/paletleGoster YOK); plaket kolu da simülasyon
const SIM_W = 96;
function simLin(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function simSrgb(v) {
  const c = v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(Math.max(v, 0), 1 / 2.4) - 0.055;
  return Math.max(0, Math.min(255, Math.round(c * 255)));
}
function simHex(V, ad) { const h = V.RENK_HEX[ad].replace("#", ""); return [0, 2, 4].map((j) => parseInt(h.slice(j, j + 2), 16)); }
function simGorsel(V, renkFn) {
  let s = 12345;
  const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  const p = new Uint8ClampedArray(SIM_W * SIM_W * 4);
  for (let y = 0; y < SIM_W; y++) {
    for (let x = 0; x < SIM_W; x++) {
      const i = (y * SIM_W + x) * 4, [ad, golge] = renkFn(x, y), c = simHex(V, ad), doku = 1 + 0.12 * (rnd() - 0.5);
      for (let j = 0; j < 3; j++) { p[i + j] = simSrgb(simLin(c[j]) * golge * doku); }
      p[i + 3] = 255;
    }
  }
  return p;
}
function simBilesen(et, w, h) {   // 4-komşulu bileşenler: [{renk, n}]
  const gor = new Int8Array(et.length), b = [];
  for (let s = 0; s < et.length; s++) {
    if (et[s] < 0 || gor[s]) { continue; }
    let n = 0; const st = [s]; gor[s] = 1;
    while (st.length) {
      const q = st.pop(); n++;
      const x = q % w, y = (q / w) | 0;
      for (const r of [x > 0 ? q - 1 : -1, x < w - 1 ? q + 1 : -1, y > 0 ? q - w : -1, y < h - 1 ? q + w : -1]) {
        if (r >= 0 && !gor[r] && et[r] === et[s]) { gor[r] = 1; st.push(r); }
      }
    }
    b.push({ renk: et[s], n });
  }
  return b;
}
function simSenaryo(V) {
  const s = {}, iz = {}, W = SIM_W;
  // G: Mavi yüzey; soldan sağa yumuşak gölge 0,55..1, alt üçte birde sert düşen gölge ×0,3, %12 doku.
  const PG = ["Mavi", "Lacivert", "Beyaz", "Kırmızı"];
  const G = simGorsel(V, (x, y) => ["Mavi", (0.55 + 0.45 * x / (W - 1)) * (y >= 64 ? 0.3 : 1)]);
  const bg = V.simulasyonBolgeleri(G, W, W, PG), kg = bg ? simBilesen(bg.et, bg.sw, bg.sh) : [];
  iz.G = kg.map((b) => PG[b.renk] + ":" + b.n);
  s.G = !!bg && bg.olc === 1 && kg.length === 1 && PG[kg[0].renk] === "Mavi";
  // B: 4 blok (sol üst Kırmızı · sağ üst Mavi · sol alt Sarı · sağ alt Beyaz), gölge 0,8..1 + doku.
  const PB = ["Beyaz", "Sarı", "Mavi", "Kırmızı"], blok = (x, y) => (y < 48 ? (x < 48 ? "Kırmızı" : "Mavi") : (x < 48 ? "Sarı" : "Beyaz"));
  const B = simGorsel(V, (x, y) => [blok(x, y), 0.8 + 0.2 * (x + y) / (2 * W - 2)]);
  const bb = V.simulasyonBolgeleri(B, W, W, PB), kb = bb ? simBilesen(bb.et, bb.sw, bb.sh) : [];
  let icHata = 0;
  for (let y = 0; bb && y < W; y++) {
    for (let x = 0; x < W; x++) {
      if (Math.abs(x - 47.5) < 3 || Math.abs(y - 47.5) < 3) { continue; }
      if (PB[bb.et[y * W + x]] !== blok(x, y)) { icHata++; }
    }
  }
  const et = (x, y) => PB[bb.et[y * W + x]];
  iz.B = { bilesen: kb.map((b) => PB[b.renk] + ":" + b.n), icHata };
  s.B = !!bb && kb.length === 4 && new Set(kb.map((b) => b.renk)).size === 4 && icHata === 0 &&
    et(47, 20) === "Kırmızı" && et(48, 20) === "Mavi" && et(20, 47) === "Kırmızı" && et(20, 48) === "Sarı";
  // A: Mavi zemin; üst yarıda 16 adet 4×4 Kırmızı benek; sağ altta 10×10 Kırmızı blok.
  const PA = ["Mavi", "Kırmızı"];
  const benek = (x, y) => y < 48 && x >= 8 && x < 88 && (x - 8) % 20 < 4 && y >= 8 && (y - 8) % 12 < 4;
  const A = simGorsel(V, (x, y) => [benek(x, y) || (x >= 60 && x < 70 && y >= 60 && y < 70) ? "Kırmızı" : "Mavi", 1]);
  const ba = V.simulasyonBolgeleri(A, W, W, PA), ka = ba ? simBilesen(ba.et, ba.sw, ba.sh) : [];
  let ustKirmizi = 0, blokKirmizi = 0;
  for (let y = 0; ba && y < W; y++) {
    for (let x = 0; x < W; x++) {
      if (PA[ba.et[y * W + x]] !== "Kırmızı") { continue; }
      if (y < 48) { ustKirmizi++; } else if (x >= 58 && x < 72 && y >= 58 && y < 72) { blokKirmizi++; }
    }
  }
  const adacik = ka.filter((b) => b.n < W * W * 0.005).reduce((t, b) => t + b.n, 0) / (W * W);
  iz.A = { bilesen: ka.map((b) => PA[b.renk] + ":" + b.n), ustKirmizi, blokKirmizi, adacik };
  s.A = !!ba && ustKirmizi === 0 && blokKirmizi >= 80 && ka.length === 2 && adacik === 0;
  // T: A'nın sol 6 sütunu saydam (rastgele RGB), bir sütun yarı saydam alfa 100.
  const Tg = A.slice();
  for (let y = 0; y < W; y++) {
    for (let x = 0; x < 7; x++) { const i = (y * W + x) * 4; Tg[i] = 13; Tg[i + 1] = 77 + y; Tg[i + 2] = 201; Tg[i + 3] = x === 6 ? 100 : 0; }
  }
  const T0 = Tg.slice(), Tr = V.dortRenkSimule(Tg, W, W, PA);
  const izin = new Set();
  for (const ad of PA) { const c = simHex(V, ad); izin.add(c.join(",")); izin.add(c.map((v) => Math.round(v * 0.62)).join(",")); }
  let saydamFark = 0, yabanci = 0;
  for (let i = 0; i < Tg.length; i += 4) {
    if (T0[i + 3] < 128) { if (Tg[i] !== T0[i] || Tg[i + 1] !== T0[i + 1] || Tg[i + 2] !== T0[i + 2] || Tg[i + 3] !== T0[i + 3]) { saydamFark++; } continue; }
    if (!izin.has(Tg[i] + "," + Tg[i + 1] + "," + Tg[i + 2])) { yabanci++; }
  }
  iz.T = { saydamFark, yabanci };
  s.T = Tr === Tg && saydamFark === 0 && yabanci === 0;
  // Y: G görseli Beyaz tek renk -> gri ölçek.
  const Y = G.slice(), Yr = V.dortRenkSimule(Y, W, W, ["Beyaz"]);
  let renkli = 0, dGir = 0, dCik = 0, nd = 0; const duzey = new Set();
  const luma = (p, i) => 0.299 * p[i] + 0.587 * p[i + 1] + 0.114 * p[i + 2];
  for (let y = 0; y < W; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      if (Y[i] !== Y[i + 1] || Y[i + 1] !== Y[i + 2]) { renkli++; }
      duzey.add(Y[i]);
      if (x < W - 1 && y !== 63 && y !== 64) { dGir += Math.abs(luma(G, i) - luma(G, i + 4)); dCik += Math.abs(Y[i] - Y[i + 4]); nd++; }
    }
  }
  iz.Y = { renkli, duzey: duzey.size, dGir: +(dGir / nd).toFixed(2), dCik: +(dCik / nd).toFixed(2) };
  s.Y = Yr === Y && renkli === 0 && duzey.size >= 8 && dCik < dGir / 2;
  // N: geçersiz girdi -> null, piksel değişmez.
  const Nn = A.slice();
  s.N = V.dortRenkSimule(Nn, W, W, ["Mor"]) === null && V.dortRenkSimule(Nn, W, W, []) === null &&
    V.dortRenkSimule(Nn, W + 1, W, PA) === null && V.dortRenkSimule(Nn, 0, W, PA) === null &&
    Nn.every((v, i) => v === A[i]);
  // BU (bölge bütünlüğü, KraL-Foto4Renk-2): tek yüzey, rengi Mavi ile Lacivert'in (doğrusal) TAM ortası; soldan sağa
  // yumuşak gölge 0,35..1 + doku -> ışıklı yanı Mavi'ye, gölgesi Lacivert'e daha yakın. Hücre hücre palete boyama
  // yüzeyi ikiye böler (müşteri paletinde saçın yarısı Siyah yarısı Ahşap olması); bölge-önce: TEK bileşen, TEK renk.
  const PBU = ["Mavi", "Lacivert", "Beyaz", "Kırmızı"], hm = simHex(V, "Mavi"), hl = simHex(V, "Lacivert");
  const orta = [0, 1, 2].map((j) => simSrgb((simLin(hm[j]) + simLin(hl[j])) / 2));
  const BUg = simGorselRgb((x) => [orta, 0.35 + 0.65 * x / (W - 1)]);
  const bbu = V.simulasyonBolgeleri(BUg, W, W, PBU), kbu = bbu ? simBilesen(bbu.et, bbu.sw, bbu.sh) : [];
  iz.BU = kbu.map((b) => PBU[b.renk] + ":" + b.n);
  s.BU = !!bbu && kbu.length === 1 && kbu[0].n === W * W;
  // KK (kontrast koruma): üstte koyu kahve (saç), altta açık ten; ikisi de en yakın Ahşap'a düşer (aynı renk = saç
  // kaybolur). Belirgin farklı iki büyük komşu bölge -> FARKLI renk, her biri tek parça.
  const PKK = ["Beyaz", "Ahşap", "Mavi", "Lacivert"];
  const KKg = simGorselRgb((x, y) => [y < 40 ? [110, 85, 70] : [222, 184, 152], 0.85 + 0.15 * x / (W - 1)]);
  const bkk = V.simulasyonBolgeleri(KKg, W, W, PKK), kkk = bkk ? simBilesen(bkk.et, bkk.sw, bkk.sh) : [];
  const ust = bkk ? PKK[bkk.et[20 * W + 48]] : "", alt = bkk ? PKK[bkk.et[70 * W + 48]] : "";
  iz.KK = { bilesen: kkk.map((b) => PKK[b.renk] + ":" + b.n), ust, alt };
  s.KK = !!bkk && kkk.length === 2 && ust !== alt && alt === "Ahşap";
  // LT (ton önceliği): açık mavi gömlek (120,160,210) -> Mavi (açıklığı Ahşap'a yakın olsa da tonu mavi).
  const PLT = ["Mavi", "Ahşap", "Siyah"];
  const blt = V.simulasyonBolgeleri(simGorselRgb(() => [[120, 160, 210], 1]), W, W, PLT);
  iz.LT = blt ? PLT[blt.et[48 * W + 48]] : null;
  s.LT = !!blt && blt.et.every((e) => PLT[e] === "Mavi");
  // S (siluet parlaması): saydam zemin üstünde Kırmızı disk (yarıçap 40), kenarında 3 px açık parlama halkası ->
  // halka gövdeye katılır (kenar şeridi); Beyaz hücre kalmaz.
  const PS = ["Kırmızı", "Beyaz", "Siyah"];
  const Sg = simGorselRgb((x, y) => {
    const r = Math.hypot(x - 47.5, y - 47.5);
    return [r >= 37 ? [240, 214, 214] : simHex(V, "Kırmızı"), 1, r < 40 ? 255 : 0];
  });
  const bs = V.simulasyonBolgeleri(Sg, W, W, PS);
  const sBeyaz = bs ? bs.et.filter((e) => PS[e] === "Beyaz").length : -1, sOpak = bs ? bs.et.filter((e) => e >= 0).length : 0;
  iz.S = { sBeyaz, sOpak };
  s.S = !!bs && sOpak > 4000 && sBeyaz === 0;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
function simGorselRgb(fn, w = SIM_W, h = SIM_W) {   // fn(x, y) -> [[r,g,b], gölge, alfa=255]; %12 doku
  let s = 777;
  const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  const p = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4, [c, golge, alfa] = fn(x, y), doku = 1 + 0.12 * (rnd() - 0.5);
      for (let j = 0; j < 3; j++) { p[i + j] = simSrgb(simLin(c[j]) * golge * doku); }
      p[i + 3] = alfa === undefined ? 255 : alfa;
    }
  }
  return p;
}
// CZ İNCE AYRINTI (KraL-Foto4Renk-2): 384 px (küçültme ×2: 2 px çizgi 1 hücreye ortalanır, mod süzgeci siler) düz Ahşap
// yüzey + 2 px koyu yatay çizgi (120 px, ağız) + 4×4 koyu benek. Çizgi KORUNUR (≥ %90'ı Ahşap'tan koyu palet rengi /
// kontur), benek SİLİNİR (hepsi Ahşap). Palet Ahşap·Siyah·Mavi.
function czSenaryo(V) {
  const s = {}, iz = {}, W = 384, PC = ["Ahşap", "Siyah", "Mavi"], ah = simHex(V, "Ahşap"), koyu = [62, 40, 30];
  const cizgi = (x, y) => y >= 150 && y < 152 && x >= 130 && x < 250, benek = (x, y) => x >= 300 && x < 304 && y >= 300 && y < 304;
  const g = simGorselRgb((x, y) => [cizgi(x, y) || benek(x, y) ? koyu : ah, 1], W, W);
  const r = V.dortRenkSimule(g, W, W, PC);
  const renkAd = (i) => { for (const a of PC) { const c = simHex(V, a); if (g[i] === c[0] && g[i + 1] === c[1] && g[i + 2] === c[2]) return a; } return "kontur"; };
  let cizgiKoyu = 0, cizgiTop = 0, benekAhsap = 0;
  for (let y = 0; y < W; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      if (cizgi(x, y)) { cizgiTop++; if (renkAd(i) !== "Ahşap") { cizgiKoyu++; } }
      if (benek(x, y) && renkAd(i) === "Ahşap") { benekAhsap++; }
    }
  }
  iz.L = { cizgiKoyu, cizgiTop, ornek: r ? renkAd((151 * W + 190) * 4) : null };
  iz.B = { benekAhsap };
  s.L = !!r && cizgiKoyu >= cizgiTop * 0.9;
  s.B = !!r && benekAhsap === 16;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
// Mutant -> beklenen KIRMIZI kümesi (bağımsız sabit; ölçülüp çivilendi). L (KraL-FotoPalet): bölge rengi artık prEsle
// (ton kapısı) ile seçilir; simMesafe L ağırlığı yalnız yedek + kontrast yolunda -> LT açık maviyi ton kapısı da korur
// (PR bölümünde M-PR-SIM-PR: prEsle kalkınca SP kırmızı). L mutantı artık hiçbir vakayı düşürmez — ÖLÇÜLDÜ, [] çivili.
const SIM_MUT_BEKLENEN = { ADACIK: ["S"], L: [], BOLGE: ["BU", "G", "KK"], KONTRAST: ["KK"], KAPALI: ["T"], GRI: ["Y"], K0: [] };
console.log("SIM) ④ 4 RENK SİMÜLASYONU — bölge tabanlı (VERI.dortRenkSimule); figür render-yok kolu + plaket");
{
  const s = simSenaryo(veriYukle(VERI_KAYNAK));
  ol("SIM-G gölgeli tek renk yüzey (yumuşak + sert gölge + doku) -> TEK bölge (Mavi)", s.G, JSON.stringify(s.iz.G));
  ol("SIM-B 4 renk bloklu görsel -> 4 bölge, bloklar kendi renginde, sınırlar yerinde", s.B, JSON.stringify(s.iz.B));
  ol("SIM-A adacık: 4×4 benekler silinir, 10×10 blok kalır (adacık oranı 0)", s.A, JSON.stringify(s.iz.A));
  ol("SIM-T saydam piksel AYNEN; opak piksel yalnız palet rengi / kontur koyusu", s.T, JSON.stringify(s.iz.T));
  ol("SIM-Y tek ana renk -> gri ölçek, gölge kalır, doku bastırılır", s.Y, JSON.stringify(s.iz.Y));
  ol("SIM-N geçersiz palet / boyut -> null, piksel değişmez", s.N, "");
  ol("SIM-BU bölge bütünlüğü: iki palet renginin tam ortasında, gölgeli tek yüzey -> TEK bileşen, TEK renk", s.BU, JSON.stringify(s.iz.BU));
  ol("SIM-KK kontrast koruma: koyu saç + açık ten (ikisi de en yakın Ahşap) -> farklı renk, ten Ahşap", s.KK, JSON.stringify(s.iz.KK));
  ol("SIM-LT ton önceliği: açık mavi yüzey -> Mavi (Ahşap değil)", s.LT, JSON.stringify(s.iz.LT));
  ol("SIM-S siluet parlaması halkası gövdeye katılır (Beyaz hücre 0)", s.S, JSON.stringify(s.iz.S));
  // Okan 12 Eki ("birebir aynı çıktı"): istemci ④'ü yeniden BOYAMAZ; dortRenkSimule yalnız veri tarafında kalır.
  ol("SIM-E ④ istemcide simülasyon YOK (dortRenkSimule/simuleGoster çağrılmaz); eski paleteIndirge/paletleGoster YOK",
     !/dortRenkSimule|simuleGoster|toDataURL\("image\/png"\)/.test(EKRAN_KAYNAK) &&
     !/paleteIndirge|paletleGoster/.test(EKRAN_KAYNAK) && !/paleteIndirge/.test(VERI_KAYNAK), "");
  const SIM_BOLGE_CAPA = "    for (k = 0; k < n; k++) { et[k] = B.bol[k] < 0 ? -1 : renk[B.bol[k]]; }\n";
  const SIM_MUT = [
    ["M-SIM-ADACIK mod/adacık süzgeci kalktı", "    simAdacik(et, sw, sh, P.length, B.opak);\n", "", "ADACIK"],
    ["M-SIM-L L ağırlığı ton ile eşit (bölge ataması)", "SIM_L_AGIRLIK = 0.3,", "SIM_L_AGIRLIK = 1,", "L"],
    // Bölge-önce adımı kalkar: her hücre kendi tonuyla en yakın palet rengine (Foto4Renk-1 öncesi hücre boyaması).
    ["M-SIM-BOLGE bölge-önce adımı kalktı (hücre hücre palet)", SIM_BOLGE_CAPA,
     "    for (k = 0; k < n; k++) { if (B.bol[k] < 0) { et[k] = -1; continue; } var e1 = 0; for (j = 1; j < np; j++) { " +
     "if (simMesafe(F.L[k], F.U[k], F.V[k], P[j][0], P[j][1], P[j][2]) < simMesafe(F.L[k], F.U[k], F.V[k], P[e1][0], P[e1][1], P[e1][2])) { e1 = j; } } et[k] = e1; }\n",
     "BOLGE"],
    ["M-SIM-KONTRAST kontrast koruma kalktı", "    simKontrastKoru(B, sw, sh, top, D, np, renk);\n", "", "KONTRAST"],
    ["M-SIM-KAPALI renkli kol piksel AYNEN",
     "    return simBuyut(piksel, w, h, k0, simEtiketle(k0, rgb, renkler), rgb, simCizgi(piksel, w, h, rgb));\n",
     "    return piksel;\n", "KAPALI"],
    ["M-SIM-GRI tek renk kolu kapalı", "    if (renkler.length === 1 && VERI.ANA_RENKLER.indexOf(renkler[0]) >= 0) {",
     "    if (false) {", "GRI"],
    ["M-SIM-K0 KONTROL (aynı gövde)", "SIM_L_AGIRLIK = 0.3,", "SIM_L_AGIRLIK = 0.3,", "K0"],
  ].map(([ad, capa, yerine, anahtar]) => [ad, capa, yerine, SIM_MUT_BEKLENEN[anahtar]]);
  for (const [ad, capa, yerine, olmeli] of SIM_MUT) {
    if (VERI_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = simSenaryo(veriYukle(VERI_KAYNAK.replace(capa, yerine)));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir) + " " + JSON.stringify(m.iz));
  }
}

console.log("CZ) ④ simülasyon İNCE AYRINTI — koyu ince çizgi (ağız/kaş) korunur, 4×4 benek silinir");
{
  const c = czSenaryo(veriYukle(VERI_KAYNAK));
  ol("CZ-L 2 px koyu çizgi korunur (≥ %90 koyu palet rengi / kontur)", c.L, JSON.stringify(c.iz.L));
  ol("CZ-B 4×4 koyu benek çizgi sayılmaz, silinir (16/16 Ahşap)", c.B, JSON.stringify(c.iz.B));
  const CZ_MUT = [
    ["M-CZ-YOK çizgi koruması kalktı", "simBuyut(piksel, w, h, k0, simEtiketle(k0, rgb, renkler), rgb, simCizgi(piksel, w, h, rgb));",
     "simBuyut(piksel, w, h, k0, simEtiketle(k0, rgb, renkler), rgb, null);", ["L"]],
    ["M-CZ-BENEK çizgi biçim süzgeci kalktı (her koyu leke çizgi)",
     "cizgi = uzun >= SIM_CIZGI_BOY * r && ust / uzun <= 2 * r + 1;", "cizgi = true;", ["B"]],
    ["M-CZ-K0 KONTROL (aynı gövde)", "SIM_CIZGI_BOY = 5,", "SIM_CIZGI_BOY = 5,", []],
  ];
  for (const [ad, capa, yerine, olmeli] of CZ_MUT) {
    if (VERI_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = czSenaryo(veriYukle(VERI_KAYNAK.replace(capa, yerine)));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir) + " " + JSON.stringify(m.iz));
  }
}

// ---------------------------------------------------------------- PR: OTOMATİK PALET (KraL-FotoPalet 11 Eki)
// Okan'ın iki gerçek denemesinde VERI.fotoRenkleri `Ahşap,Lacivert,Siyah,Gri` / `Gri,Lacivert,Ahşap,Yeşil` seçti: koyu
// saç yarı Siyah yarı Gri, denim Gri, gözler kayıp. Fikstürler KODLA üretilir (gerçek kişi / gerçek görsel YOK): gölgeli
// sentetik figür (koyu kahve saç · ten · #4a6a8f denim, ışıklı yanı solgun · koyu göz) + tek yüzeyler. Her kural için
// bir mutant: kural kalkınca TAM OLARAK beklenen vaka kümesi kırmızı (ölçülüp çivilendi).
const PR_W = 128;
function prGorsel(fn, w = PR_W, h = PR_W) {          // fn(x, y) -> null (saydam) | [[r,g,b], gölge]; %10 doku
  let s = 4242;
  const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  const p = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4, v = fn(x, y), doku = 1 + 0.1 * (rnd() - 0.5);
      if (!v) { continue; }
      for (let j = 0; j < 3; j++) { p[i + j] = simSrgb(simLin(v[0][j]) * v[1] * doku); }
      p[i + 3] = 255;
    }
  }
  return p;
}
// zemin "saydam" | "beyaz" (opak, kenara bağlı); tisort: ceketin ortasında beyaz şerit (zemine/kenara DEĞMEZ).
const PR_RENK = { sac: [58, 42, 34], ten: [226, 190, 160], denim: [74, 106, 143], tisort: [238, 238, 236], goz: [30, 22, 20] };
function prFigur(zemin, tisort) {
  return prGorsel((x, y) => {
    const ix = (x - 64) / 64, isik = 0.55 + 0.7 * x / (PR_W - 1);
    const kafa = Math.hypot((x - 64) / 30, (y - 40) / 30) <= 1, yuz = Math.hypot((x - 64) / 21, (y - 46) / 22) <= 1;
    const goz = Math.hypot((x - 55) / 3, (y - 44) / 3) <= 1 || Math.hypot((x - 73) / 3, (y - 44) / 3) <= 1;
    const govde = y >= 72 && y < 118 && Math.abs(ix) <= 0.55, el = y >= 104 && y < 116 && Math.abs(ix) > 0.55 && Math.abs(ix) <= 0.68;
    if (goz) { return [PR_RENK.goz, 1]; }
    if (yuz) { return [PR_RENK.ten, 0.9 + 0.2 * x / (PR_W - 1)]; }
    if (kafa) { return [PR_RENK.sac, 0.7 + 0.8 * x / (PR_W - 1)]; }
    if (govde) { return tisort && Math.abs(x - 64) < 7 && y >= 76 && y < 112 ? [PR_RENK.tisort, 0.92] : [PR_RENK.denim, isik]; }
    if (el) { return [PR_RENK.ten, 0.95]; }
    return zemin === "beyaz" ? [[246, 246, 244], 1] : null;
  });
}
const prYuzey = (rgb, a, b) => prGorsel((x, y) => (x >= 16 && x < 112 && y >= 16 && y < 112 ? [rgb, a + (b - a) * (x - 16) / 95] : null));
// Aynı ton iki parça (üst ışıklı, alt gölgeli, arada ince koyu kıvrım) — pet kafa/gövde.
const prIkiParca = (rgb, ust, alt) => prGorsel((x, y) => {
  if (x < 24 || x >= 104 || y < 8 || y >= 120) { return null; }
  if (y >= 58 && y < 61) { return [rgb, 0.45]; }
  return [rgb, y < 58 ? ust : alt];
});
function prSenaryo(V) {
  const s = {}, iz = {}, pal = (p) => V.fotoRenkleri(p, 4, PR_W, PR_W);
  const F1 = pal(prFigur("saydam", false)), F2 = pal(prFigur("beyaz", false)), F3 = pal(prFigur("beyaz", true));
  iz.F = F1; iz.B = F2; iz.I = F3;
  const iyi = (p) => p.includes("Siyah") && p.includes("Ahşap") && (p.includes("Mavi") || p.includes("Lacivert")) &&
    !p.includes("Gri") && !p.includes("Yeşil");
  s.F = iyi(F1);
  s.B = iyi(F2) && !F2.includes("Beyaz");
  s.I = iyi(F3) && F3.includes("Beyaz");
  iz.DL = pal(prYuzey([120, 140, 165], 0.95, 1.1)); s.DL = JSON.stringify(iz.DL) === '["Mavi"]';
  iz.G = pal(prYuzey([138, 138, 138], 0.9, 1.1)); s.G = JSON.stringify(iz.G) === '["Gri"]';
  iz.S = pal(prYuzey([92, 92, 94], 0.85, 1.25)); s.S = JSON.stringify(iz.S) === '["Siyah"]';
  iz.K = pal(prYuzey([112, 80, 58], 0.85, 1.15)); s.K = JSON.stringify(iz.K) === '["Siyah"]';
  iz.Y = pal(prYuzey([120, 108, 40], 0.9, 1.1)); s.Y = JSON.stringify(iz.Y) === '["Sarı"]';
  iz.BR = pal(prIkiParca([230, 120, 45], 1.08, 0.86)); s.BR = iz.BR.length === 1;
  // Simülasyon (seçili palet): bölge rengi prEsle (SP) · kurallı aday çok uzaksa en-yakın yedek (SU) · aynı yüzey tek renk (SB).
  const et = (p, palet) => { const b = V.simulasyonBolgeleri(p, PR_W, PR_W, palet); return b ? [...new Set([...b.et].filter((e) => e >= 0).map((e) => palet[e]))] : null; };
  iz.SP = et(prYuzey([110, 110, 112], 0.9, 1.1), ["Siyah", "Ahşap", "Mavi"]); s.SP = JSON.stringify(iz.SP) === '["Siyah"]';
  iz.SU = et(prYuzey([238, 238, 236], 0.92, 1), ["Siyah", "Ahşap", "Mavi", "Lacivert"]); s.SU = JSON.stringify(iz.SU) === '["Ahşap"]';
  const P3 = ["Kırmızı", "Sarı", "Siyah"], br = V.simulasyonBolgeleri(prIkiParca([230, 120, 45], 1.08, 0.86), PR_W, PR_W, P3);
  iz.SB = br ? [P3[br.et[30 * PR_W + 64]], P3[br.et[90 * PR_W + 64]]] : null; s.SB = !!iz.SB && iz.SB[0] === iz.SB[1];
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("PR) OTOMATİK PALET — sentetik figür: denim Mavi|Lacivert, koyu saç Siyah, ten Ahşap; Gri/Yeşil yok; zemin sayılmaz");
{
  const s = prSenaryo(veriYukle(VERI_KAYNAK));
  ol("PR-F saydam zeminli figür -> Siyah ∧ Ahşap ∧ (Mavi|Lacivert), Gri/Yeşil YOK", s.F, JSON.stringify(s.iz.F));
  ol("PR-B kenara bağlı opak beyaz zemin palete GİRMEZ (Beyaz yok), figür renkleri aynı", s.B, JSON.stringify(s.iz.B));
  ol("PR-I iç beyaz tişört (kenara değmez) KALIR -> Beyaz paletde", s.I, JSON.stringify(s.iz.I));
  ol("PR-DL ışıklı solgun denim (120,140,165) -> [Mavi] (Gri değil)", s.DL, JSON.stringify(s.iz.DL));
  ol("PR-G gerçek nötr gri yüzey -> [Gri] (Gri kapısının pozitif kontrolü)", s.G, JSON.stringify(s.iz.G));
  ol("PR-S siyah plastik renderi (L≈0,45 nötr) -> [Siyah] (aydınlatma payı)", s.S, JSON.stringify(s.iz.S));
  ol("PR-K orta kahve saç (112,80,58) -> [Siyah] (Kırmızı değil; kahve kuralı)", s.K, JSON.stringify(s.iz.K));
  ol("PR-Y koyu hardal (120,108,40) -> [Sarı] (Yeşil değil; ton kapısı)", s.Y, JSON.stringify(s.iz.Y));
  ol("PR-BR aynı ton iki parça (ışık farkı) -> TEK renk", s.BR, JSON.stringify(s.iz.BR));
  ol("PR-SP simülasyon: koyu nötr yüzey, palet Siyah·Ahşap·Mavi -> Siyah (prEsle)", s.SP, JSON.stringify(s.iz.SP));
  ol("PR-SU simülasyon: beyaz yüzey, Beyaz'sız palet -> Ahşap (Siyah değil; yedek)", s.SU, JSON.stringify(s.iz.SU));
  ol("PR-SB simülasyon: aynı ton iki parça -> iki parça AYNI renk", s.SB, JSON.stringify(s.iz.SB));
  const PR_MUT = [
    ["M-PR-ARKA kenara bağlı arka plan silinmez", "    prArkaSil(k0);\n", "", ["B"]],
    ["M-PR-KOPRU arka plan kenar bağı yok (her açık nötr silinir)",
     "        if ((x === 0 || y === 0 || x === sw - 1 || y === sh - 1) && uygun(k)) { gor[k] = 1; yigin.push(k); }",
     "        if (uygun(k)) { gor[k] = 1; yigin.push(k); }", ["I"]],
    ["M-PR-GRI ara nötr (Gri) kroma kapısı kalktı", "      if (p.ara && C >= PR_GRI_C) { return Infinity; }\n", "", ["DL"]],
    ["M-PR-PAY aydınlatma payı kalktı (nötr hedef = filament L)",
     "      p.hedef = hi > lo ? PR_NOTR_ALT + (p.L - lo) / (hi - lo) * (PR_NOTR_UST - PR_NOTR_ALT) : p.L;", "      p.hedef = p.L;", ["S", "SP"]],
    ["M-PR-KAHVE kahve kuralı kalktı", " || (kahve && p.C >= PR_KAHVE_C)) { return Infinity; }", ") { return Infinity; }", ["B", "F", "I", "K"]],
    ["M-PR-TON ton kapısı kalktı", "C < PR_C_MIN || cos < Math.cos(PR_TON_MAX * Math.PI / 180) ||", "C < PR_C_MIN ||", ["Y"]],
    ["M-PR-BIRLIK aynı yüzey birliği kalktı (palet)", "    prBirlik(bol, renk, P);\n", "", ["BR"]],
    ["M-PR-BOLGE bölge oyu yerine hücre oyu (palet)", "    var B = simKaynakBolge(k0, simOznitelik(k0, SIM_L_TABAN)), top",
     "    var B = (function () { var b = new Int32Array(k0.sw * k0.sh).fill(-1), o = 0; for (var q = 0; q < b.length; q++) { " +
     "if (k0.say[q]) { b[q] = q; o++; } } return { bol: b, nr: b.length, opak: o }; })(), top", ["BR"]],
    ["M-PR-SIM-PR simülasyon prEsle yerine simMesafe", "      bol.push(q); rk.push(pe >= 0 && pd[0] <= PR_UZAK ? pe : en);\n",
     "      bol.push(q); rk.push(en);\n", ["SP"]],
    ["M-PR-SIM-UZAK simülasyon yedeği kalktı", "rk.push(pe >= 0 && pd[0] <= PR_UZAK ? pe : en);", "rk.push(pe >= 0 ? pe : en);", ["SU"]],
    ["M-PR-SIM-BIRLIK simülasyonda aynı yüzey birliği kalktı", "    prBirlik(bol, rk, PP);\n", "", ["SB"]],
    ["M-PR-K0 KONTROL (aynı gövde)", "    prBirlik(bol, rk, PP);\n", "    prBirlik(bol, rk, PP);\n", []],
  ];
  for (const [ad, capa, yerine, olmeli] of PR_MUT) {
    if (VERI_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = prSenaryo(veriYukle(VERI_KAYNAK.replace(capa, yerine)));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir) + " " + JSON.stringify(m.iz));
  }
}

// ---------------------------------------------------------------- EL: ④ PALET — ③'TEKİ PALET SİPARİŞE GİDER, ④ YENİDEN BOYAMAZ
// Okan 12 Eki ("birebir aynı çıktı"): ④ görseli sağlayıcının görseli AYNEN; ④'te palet türetme/düzenleyici YOK.
// ③'te seçilen Renkli paleti (fotoğraftan) siparişe giden `renkler`dir (oturum kaydı + sepet), yenilemede kaybolmaz;
// sepet kalemi sunucunun renk kuralını (renkSayimi: tekrarsız, PLA_RENKLERI, tavan) geçer; Renkli +%15 SABİT.
// Ekran sahte DOM'da GERÇEKTEN koşar; sağlayıcı görseli = prFigur.
const EL_IS = "e1" + "a".repeat(30), EL_MM = 100;
const EL_HAZIR = { asama: "hazir", tur: "figur", olcu_mm: EL_MM, gorsel: "/api/shop/foto/gorsel?is=" + EL_IS,
                   gecerlilik_bitis: "2099-01-01T00:00:00.000Z" };
async function elEkran(kaynak, V, kayit) {
  const sepet = [], sim = [];
  const Vs = Object.assign({}, V, { dortRenkSimule: (p, w, h, r) => { sim.push(r.slice()); return V.dortRenkSimule(p, w, h, r); } });
  const pFig = prFigur("saydam", false);
  const e = await ekranKos(kaynak, Vs, acikGercek(V, V6_TUM),
    { is: EL_IS, tur: "figur", alt_tur: "insan", olcu: EL_MM, renk_secim: "Renkli", malzeme: "PLA", onay: V.onay_surum, ...kayit },
    EL_HAZIR, { turnstileOto: true, paletSahte: true, kaydir: false, sepet, dogalBoy: PR_W,
                pikselUret: (w, h) => (w === PR_W && h === PR_W ? pFig.slice() : new Uint8ClampedArray(w * h * 4)) });
  const d = () => [...e.bolum.agac()];
  const yuva = () => d().filter((n) => n.tagName === "SELECT" && n.getAttribute("data-palet-yuva") !== null).length;
  const src = () => (d().find((n) => n.classList.contains("foto-uretim-onizleme-img")) || { src: null }).src;
  const kayitOku = () => { try { return JSON.parse(e.ss.getItem("pruvo_foto_is")); } catch (x) { return null; } };
  const sepeteEkle = () => {
    const b2 = d().find((n) => n.id === "foto-b2-onay");
    if (b2) { b2.checked = true; b2.tetikle("change"); }
    const sip = d().find((n) => n.id === "foto-sip-btn");
    if (sip) { sip.tetikle("click"); }
    return sepet[sepet.length - 1] || null;
  };
  return { yuva, src, kayitOku, sepeteEkle, sim };
}
// Sunucu renkSayimi palet kuralı (shop/src/foto.js; aynı VERI): Renkli, dolu, tekrarsız, PLA_RENKLERI içinde, tavan altında.
const elSunucuKabul = (V, k) => !!k && k.renkli === true && Array.isArray(k.renkler) && k.renkler.length > 0 &&
  new Set(k.renkler).size === k.renkler.length && k.renkler.every((x) => V.PLA_RENKLERI.includes(x)) &&
  k.renkler.length <= V.renkTavani("figur") && V.renkliSecilebilir("figur") === true;
async function elSenaryo(kaynak, V) {
  const s = {}, iz = {}, P3 = ["Beyaz", "Gri"];
  const renkliFormul = V.fiyatKurus("figur", EL_MM, { renkli: true, malzeme: "PLA" });
  const tekFormul = V.fiyatKurus("figur", EL_MM, { renkli: false, malzeme: "PLA" });
  // EL1: ③ paleti ("foto") ④'te TÜRETİLMEZ; ④'te düzenleyici YOK, simülasyon YOK, görsel sağlayıcınınki AYNEN.
  const a = await elEkran(kaynak, V, { renkler: P3, renk_kaynak: "foto" });
  const k1 = a.kayitOku();
  iz.EL1 = { yuva: a.yuva(), sim: a.sim.length, src: a.src(), kayit: k1 && [k1.renkler, k1.renk_kaynak] };
  s.EL1 = a.yuva() === 0 && a.sim.length === 0 && a.src() === EL_HAZIR.gorsel &&
    !!k1 && JSON.stringify(k1.renkler) === JSON.stringify(P3) && k1.renk_kaynak === "foto";
  // EL2: Renkli sepet kalemi ③ paletini taşır (renkler · renk_sayisi · renkli · gosterim_kurus) ve sunucu kuralını geçer.
  const sat = a.sepeteEkle();
  iz.EL2 = { satir: sat && [sat.renkler, sat.renk_sayisi, sat.renkli, sat.gosterim_kurus], renkliFormul,
             sunucu: elSunucuKabul(V, sat), src: a.src(), sim: a.sim.length };
  s.EL2 = !!sat && JSON.stringify(sat.renkler) === JSON.stringify(P3) && sat.renk_sayisi === P3.length && sat.renkli === true &&
    sat.gosterim_kurus === renkliFormul && elSunucuKabul(V, sat) && a.src() === EL_HAZIR.gorsel && a.sim.length === 0;
  // EL5: yenileme — kayıt "elle" -> sepet kayıttaki palet; ④ görseli yine AYNEN.
  const X = ["Kırmızı", "Beyaz", "Lacivert"], b = await elEkran(kaynak, V, { renkler: X, renk_kaynak: "elle" });
  const satb = b.sepeteEkle();
  iz.EL5 = { satir: satb && satb.renkler, src: b.src(), sim: b.sim.length };
  s.EL5 = !!satb && JSON.stringify(satb.renkler) === JSON.stringify(X) && elSunucuKabul(V, satb) &&
    b.src() === EL_HAZIR.gorsel && b.sim.length === 0;
  // EL6: Renkli = tek renk × 1,15 SABİT (VERI) ve figür ④ özeti ile sepet AYNI formül.
  iz.EL6 = { renkliFormul, tekFormul };
  s.EL6 = renkliFormul === Math.round(tekFormul * 1.15) && renkliFormul > tekFormul;
  // EL7: alanı olmayan ESKİ kayıt -> sepet kayıttaki palet.
  const c = await elEkran(kaynak, V, { renkler: P3 });
  const satc = c.sepeteEkle();
  iz.EL7 = satc && satc.renkler;
  s.EL7 = !!satc && JSON.stringify(satc.renkler) === JSON.stringify(P3) && elSunucuKabul(V, satc);
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
console.log("EL) ④ PALET — ③ paleti siparişe gider (kayıt + sepet + yenileme, sunucu kuralı); ④ yeniden boyamaz; fiyat sabit");
{
  const V = veriYukle(VERI_KAYNAK), s = await elSenaryo(EKRAN_KAYNAK, V);
  ol("EL1 ③ paleti ('foto') ④'te türetilmez; ④ düzenleyici 0, simülasyon 0, img.src = sağlayıcı görseli", s.EL1, JSON.stringify(s.iz.EL1));
  ol("EL2 Renkli sepet kalemi ③ paletini taşır (renkler/renk_sayisi/renkli/gosterim_kurus), sunucu renk kuralı geçer", s.EL2, JSON.stringify(s.iz.EL2));
  ol("EL5 yenileme: 'elle' kayıt -> sepet kayıttaki palet; ④ görseli AYNEN", s.EL5, JSON.stringify(s.iz.EL5));
  ol("EL6 Renkli = tek renk × 1,15 (renk adedinden bağımsız)", s.EL6, JSON.stringify(s.iz.EL6));
  ol("EL7 alanı olmayan eski kayıt -> sepet kayıttaki palet", s.EL7, JSON.stringify(s.iz.EL7));
  const EL_BOYA = "        else img.src = S.gorsel;\n";
  const EL_MUT = [
    // Çağrı yeri ④'ü yeniden tuvale boyar (simuleGoster'in yaptığı: dortRenkSimule + toDataURL) -> EL1/EL2/EL5 KIRMIZI.
    ["M-EL-BOYAMA ④ figür görseli yeniden boyanır", "E", EL_BOYA,
     "        else { var tv = document.createElement(\"canvas\"), tx = tv.getContext(\"2d\"), td = tx.getImageData(0, 0, 2, 2);\n" +
     // dataURL literal: tuval saplamasının toDataURL'i FR_PALETLI'ye bağlı, o sabit bu bloktan SONRA tanımlı (TDZ).
     "          try { F.dortRenkSimule(td.data, 2, 2, paletRenkleri(S.tur)); } catch (x) {} img.src = \"data:image/png;base64,BOYALI\"; }\n",
     ["EL1", "EL2", "EL5"]],
    ["M-EL-FIYAT Renkli farkı %30", "V", "  VERI.RENKLI_EK_YUZDE = 15;\n", "  VERI.RENKLI_EK_YUZDE = 30;\n", ["EL6"]],
    ["M-EL-K0 KONTROL (aynı gövde)", "E", EL_BOYA, EL_BOYA, []],
  ];
  for (const [ad, hedef, capa, yerine, olmeli] of EL_MUT) {
    const asil = hedef === "E" ? EKRAN_KAYNAK : VERI_KAYNAK;
    if (asil.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = hedef === "E" ? await elSenaryo(EKRAN_KAYNAK.replace(capa, yerine), V)
      : await elSenaryo(EKRAN_KAYNAK, veriYukle(VERI_KAYNAK.replace(capa, yerine)));
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir) + " " + JSON.stringify(m.iz));
  }
}
// ---------------------------------------------------------------- FR: ④ FİGÜR = RENDER varsa O, yoksa SAĞLAYICI GÖRSELİ AYNEN
// Okan 12 Eki ("birebir aynı çıktı"): figür (insan · pet · model) + anahtarlık–figür ④ görseli:
// sunucu /durum `render` verdiyse img.src = O adres AYNEN; vermediyse sağlayıcı görseli AYNEN + "renkler basılacak
// figürü göstermez". Tek renk / Renkli fark etmez; simülasyon (VERI.dortRenkSimule) istemcide ÇAĞRILMAZ, ④'te palet
// düzenleyici YOK. Plaket: sağlayıcı görseli AYNEN, figür notu YOK.
const FR_PALETLI = "data:image/png;base64,PALETLI";
const FR_IS = "f".repeat(32), FR_GORSEL = "/api/shop/foto/gorsel?is=" + FR_IS, FR_RENDER = FR_GORSEL + "&gorunum=render";
const FR_UST = "Önizleme — ürün bunun seçtiğin renk sayısında olur; tam kopyası değildir.";
async function frEkran(kaynak, V, kayit, render, simNull) {
  const hazir = { asama: "hazir", tur: kayit.tur, olcu_mm: kayit.olcu, gorsel: FR_GORSEL,
                  gecerlilik_bitis: "2099-01-01T00:00:00.000Z", ...(render ? { render: FR_RENDER } : {}) };
  // Casus: simülasyon çağrı sayısı (her kolda 0 olmalı); simNull -> tarayıcıda simülasyon başarısız.
  let cagri = 0;
  const Vs = Object.assign({}, V, { dortRenkSimule: (...a) => { cagri++; return simNull ? null : V.dortRenkSimule(...a); } });
  const e = await ekranKos(kaynak, Vs, acikGercek(V, V6_TUM), { is: FR_IS, ...kayit }, hazir, { paletSahte: true });
  const d = [...e.bolum.agac()];
  const img = d.find((n) => n.classList.contains("foto-uretim-onizleme-img"));
  const not = d.find((n) => n.classList.contains("foto-uretim-gorunum-notu"));
  return { src: img ? img.src : null, not: not ? not.textContent : null, cagri,
           yuva: d.filter((n) => n.tagName === "SELECT" && n.getAttribute("data-palet-yuva") !== null).length,
           ust: d.some((n) => n.tagName === "P" && n.textContent === FR_UST) };
}
async function frSenaryo(kaynak, V) {
  const s = {}, iz = {};
  const INSAN = { tur: "figur", alt_tur: "insan", olcu: 100 };
  const AF = { tur: "anahtarlik", cesit: "figur", olcu: 60 };
  iz.insanR = await frEkran(kaynak, V, INSAN, true);
  iz.insan = await frEkran(kaynak, V, INSAN, false);
  iz.afR = await frEkran(kaynak, V, AF, true);
  iz.af = await frEkran(kaynak, V, AF, false);
  iz.plaket = await frEkran(kaynak, V, { tur: "plaket", olcu: 100 }, true);
  iz.renkli = await frEkran(kaynak, V, { ...INSAN, renk_secim: "Renkli", malzeme: "PLA", renkler: ["Beyaz", "Gri"], renk_kaynak: "foto" }, false);
  // Cümle LİTERAL: VERI boşalsa da ekranda aranır.
  const ornek = "Örnek görünüm — renkler basılacak figürü göstermez.";
  const cumle = (x) => typeof x === "string" && /yaklaşık görünümü/.test(x) && /tam kopyası değildir/.test(x) && !/3D|baskı/i.test(x);
  s.FR0 = cumle(V.FIGUR_SIMULASYON_TEK) && cumle(V.FIGUR_SIMULASYON_RENKLI) &&
    /renkler basılacak figürü göstermez/.test(V.FIGUR_ORNEK_NOTU || "");
  s.FR1 = iz.insanR.src === FR_RENDER && iz.insanR.cagri === 0;     // render varken O; simülasyon ÇAĞRILMAZ
  s.FR2 = iz.insanR.not === V.FIGUR_RENDER_NOTU && !iz.insanR.ust;
  s.FR3 = iz.insan.src === FR_GORSEL && iz.insan.cagri === 0;        // render yok: sağlayıcı görseli AYNEN
  s.FR4 = iz.insan.not === ornek && !iz.insan.ust;                   // ... ve "renkler basılacak figürü göstermez"
  s.FR5 = /en çok 4 renk/.test(V.FIGUR_SIMULASYON_RENKLI || "") && /tek renk/.test(V.FIGUR_SIMULASYON_TEK || "");
  s.FR6 = iz.afR.src === FR_RENDER && iz.afR.not === V.FIGUR_RENDER_NOTU && iz.afR.cagri === 0;
  s.FR7 = iz.af.src === FR_GORSEL && iz.af.not === ornek && iz.af.cagri === 0;
  s.FR8 = iz.plaket.src === FR_GORSEL && iz.plaket.cagri === 0 && iz.plaket.not === null && iz.plaket.ust;   // plaket: AYNEN
  // Renkli (palet seçili) render yok: görsel yine AYNEN, ④'te palet düzenleyici YOK.
  s.FR9 = iz.renkli.src === FR_GORSEL && iz.renkli.cagri === 0 && iz.renkli.yuva === 0 && iz.renkli.not === ornek;
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
async function frSunucu(fm) {
  const k = koprukur(); await k.hazir;
  const r2b = r2Kur();
  const e2 = envKur(k.d1, r2b);
  const simdi = new Date().toISOString(), eski = new Date(Date.now() - 100 * 3600 * 1000).toISOString();
  const IS = { insan: "1".repeat(32), af: "2".repeat(32), plaket: "3".repeat(32), sil: "4".repeat(32) };
  const satir = async (no, tur, cesit, alt, tarih) => k.d1.prepare(
    "INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, cesit, alt_tur)" +
    " VALUES (?, ?, 100, 'z', ?, 'hazir', 'gorev-fr', ?, ?, ?)").bind(no, tur, tarih, tarih, cesit, alt).run();
  await satir(IS.insan, "figur", "", "insan", simdi);
  await satir(IS.af, "anahtarlik", "figur", "", simdi);
  await satir(IS.plaket, "plaket", "", "", simdi);
  await satir(IS.sil, "figur", "", "pet", eski);
  const WEBP = { httpMetadata: { contentType: "image/webp" } };
  for (const no of [IS.insan, IS.plaket, IS.sil]) { await r2b.put("foto-onizleme/" + no + "-render.webp", PNG, WEBP); }
  for (const no of Object.values(IS)) { await r2b.put("foto-onizleme/" + no + ".png", PNG, {}); }
  const cag = async (yol) => fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, {
    method: "GET", headers: { "CF-Connecting-IP": "10.0.9.7" } }), e2, new URL("https://pruvo3d.com/api/shop" + yol),
    yol.split("?")[0], null);
  const durum = async (no) => { try { return await (await cag("/foto/durum?is=" + no)).json(); } catch (e) { return null; } };
  const s = {};
  const di = await durum(IS.insan), da = await durum(IS.af), dp = await durum(IS.plaket);
  s.SR1 = !!di && di.asama === "hazir" && di.render === "/api/shop/foto/gorsel?is=" + IS.insan + "&gorunum=render";
  s.SR2 = !!da && da.asama === "hazir" && !("render" in da);       // render yok -> alan YOK (uydurulmuş adres yok)
  s.SR3 = !!dp && dp.asama === "hazir" && !("render" in dp);       // plaket render kolu DEĞİL
  const gr = await cag("/foto/gorsel?is=" + IS.insan + "&gorunum=render");
  s.SR4 = gr.status === 200 && gr.headers.get("Content-Type") === "image/webp";
  s.SR5 = (await cag("/foto/gorsel?is=" + IS.plaket + "&gorunum=render")).status === 404;
  await fm.fotoUretimTuru(envKur(k.d1, r2b, { URETIM_API_ANAHTAR: "" }), Date.now(), null);
  s.SR6 = !r2b.m.has("foto-onizleme/" + IS.sil + "-render.webp") && !r2b.m.has("foto-onizleme/" + IS.sil + ".png") &&
    r2b.m.has("foto-onizleme/" + IS.insan + "-render.webp");      // 3 gün saklama: render önizlemeyle BİRLİKTE silinir
  k.kapat();
  return s;
}
console.log("FR) ④ FİGÜR — render varsa O, yoksa sağlayıcı görseli AYNEN + cümle (simülasyon yok); plaket AYNEN");
{
  const V = veriYukle(VERI_KAYNAK);
  const s = await frSenaryo(EKRAN_KAYNAK, V);
  ol("FR0 VERI simülasyon cümleleri 'yaklaşık görünümü … tam kopyası değildir' + geri düşüş cümlesi", s.FR0, V.FIGUR_SIMULASYON_TEK);
  ol("FR1 insan + render -> img.src = render adresi, simülasyon ÇAĞRILMAZ", s.FR1, JSON.stringify(s.iz.insanR));
  ol("FR2 insan + render -> görünüm notu = FIGUR_RENDER_NOTU, üst 'Önizleme —' cümlesi YOK", s.FR2, JSON.stringify(s.iz.insanR));
  ol("FR3 insan render YOK -> img.src = sağlayıcı görseli AYNEN (simülasyon 0)", s.FR3, JSON.stringify(s.iz.insan));
  ol("FR4 insan render YOK -> 'renkler basılacak figürü göstermez' cümlesi", s.FR4, JSON.stringify(s.iz.insan));
  ol("FR5 VERI: Renkli \"en çok 4 renk\" · tek \"tek renk\"", s.FR5, V.FIGUR_SIMULASYON_RENKLI + " | " + V.FIGUR_SIMULASYON_TEK);
  ol("FR6 anahtarlık–figür + render -> render + render notu, simülasyon ÇAĞRILMAZ", s.FR6, JSON.stringify(s.iz.afR));
  ol("FR7 anahtarlık–figür render YOK -> sağlayıcı görseli AYNEN + cümle", s.FR7, JSON.stringify(s.iz.af));
  ol("FR8 plaket -> sağlayıcı görseli AYNEN, figür notu YOK, üst cümle VAR", s.FR8, JSON.stringify(s.iz.plaket));
  ol("FR9 Renkli render YOK -> görsel AYNEN, ④ palet düzenleyici YOK", s.FR9, JSON.stringify(s.iz.renkli));
  const kir = (m) => (m ? Object.keys(m).filter((x) => m[x] !== true).sort() : null);
  const C_SRC = "        if (S.render) img.src = S.render;\n        else img.src = S.gorsel;\n";
  const C_FIG = "        else img.src = S.gorsel;\n";
  const C_PLK = "        img.src = S.gorsel;\n";
  const C_NOT = "        S.alan.appendChild(not);\n";
  const C_GNOT = "    return S.render ? F.FIGUR_RENDER_NOTU : F.FIGUR_ORNEK_NOTU;\n";
  // simuleGoster'in yaptığı: kaynak görsel tuvale çizilir, dortRenkSimule ile boyanır, dataURL ④'e yazılır.
  const BOYA = "{ var tv = document.createElement(\"canvas\"), tx = tv.getContext(\"2d\"), td = tx.getImageData(0, 0, 2, 2); " +
    "F.dortRenkSimule(td.data, 2, 2, [anaRenk()]); img.src = tv.toDataURL(\"image/png\"); }\n";
  const C_VNOT = '  VERI.FIGUR_SIMULASYON_TEK = "Önizleme: figürün seçtiğin tek renkle yaklaşık görünümü; " +\n' +
    '    "basılan figür sadeleştirilmiş hâlidir, tam kopyası değildir.";\n';
  const FR_MUT = [
    ["M-FR-RENDER-YOK render adresi yok sayılır", "E", C_SRC, "        img.src = S.gorsel;\n", ["FR1", "FR6"]],
    ["M-FR-FIG-BOYAMA figür çağrı yeri ④'ü yeniden boyar (simülasyon geri)", "E", C_FIG, "        else " + BOYA,
     ["FR3", "FR7", "FR9"]],
    ["M-FR-PLK-BOYAMA plaket çağrı yeri ④'ü yeniden boyar (simülasyon geri)", "E", C_PLK, "        " + BOYA, ["FR8"]],
    ["M-FR-CUMLE-YOK görünüm notu basılmaz", "E", C_NOT, "", ["FR2", "FR4", "FR6", "FR7", "FR9"]],
    ["M-FR-SIM-CUMLE render yokken simülasyon cümlesi", "E", C_GNOT,
     "    return S.render ? F.FIGUR_RENDER_NOTU : F.FIGUR_SIMULASYON_TEK;\n", ["FR4", "FR7", "FR9"]],
    ["M-FR-VERI-CUMLE simülasyon cümlesi boş", "V", C_VNOT, '  VERI.FIGUR_SIMULASYON_TEK = "";\n', ["FR0", "FR5"]],
    ["M-FR-K0 KONTROL (aynı gövde)", "E", C_SRC, C_SRC, []],
  ];
  for (const [ad, hedef, capa, yerine, olmeli] of FR_MUT) {
    const asil = hedef === "E" ? EKRAN_KAYNAK : VERI_KAYNAK;
    if (asil.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = hedef === "E" ? await frSenaryo(EKRAN_KAYNAK.replace(capa, yerine), V)
      : await frSenaryo(EKRAN_KAYNAK, veriYukle(VERI_KAYNAK.replace(capa, yerine)));
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir(m)) === JSON.stringify(olmeli), JSON.stringify(kir(m)));
  }
  const ss = await frSunucu(foto);
  ol("SR1 /durum insan + R2 render -> render adresi (gorunum=render)", ss.SR1, JSON.stringify(ss));
  ol("SR2 /durum anahtarlık–figür render YOK -> render alanı YOK", ss.SR2, JSON.stringify(ss));
  ol("SR3 /durum plaket (R2'de render olsa da) -> render alanı YOK", ss.SR3, JSON.stringify(ss));
  ol("SR4 /gorsel?gorunum=render insan -> 200 image/webp", ss.SR4, JSON.stringify(ss));
  ol("SR5 /gorsel?gorunum=render plaket -> 404", ss.SR5, JSON.stringify(ss));
  ol("SR6 3 gün temizliği render'ı önizlemeyle BİRLİKTE siler (taze iş kalır)", ss.SR6, JSON.stringify(ss));
  const SR_MUT = [
    ["M-SR-RENDERVAR hiç render bildirilmez",
     '  if (!is || is.asama !== "hazir" || !renderKolu(is) || !env.OZEL_DOSYA) { return false; }\n', "  return false;\n", ["SR1"]],
    ["M-SR-GORSEL-KOL kapısı kalktı (plaket render'ı sunulur)",
     "    return renderKolu(is) ? onizlemeGorseli(", "    return true ? onizlemeGorseli(", ["SR5"]],
    ["M-SR-KOL figür türü render kolundan düşer",
     '(figurKolu(is) || (is.tur === "figur" && !is.cesit))', "figurKolu(is)", ["SR1", "SR4", "SR6"]],
    ["M-SR-SIL temizlik render'ı silmez",
     "    if (renderKolu(s)) { await env.OZEL_DOSYA.delete(onizlemeRenderAnahtari(s.is_no)); }\n", "", ["SR6"]],
  ];
  for (const [ad, capa, yerine, olmeli] of SR_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await frSunucu(fm);
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir(m)) === JSON.stringify(olmeli), JSON.stringify(kir(m)));
  }
}

/**
 * AKR) ANAHTARLIK–YAZI İKİ RENK (Okan 12 Eki, aynen "anahtarlıkta tek renk seçimi olmaz zaten minimum 2 renk olmalı").
 * ③'te Yazı rengi + Taban rengi (VERI.ANA_RENKLER), varsayılan taban Siyah + yazı Beyaz; çift üreteç kontrast eşiğinin
 * altındaysa ③'te `kontrast` metni + ileri pasif; sunucu renkSayimi aynı hükümle (VERI.bolgeRenkHukmu) kabul/ret; fiyat
 * renk adedinden bağımsız. ③'te TEK ölçü kontrolü (`form_sunum.genislik_mm` = Ölçü sürgüsü).
 *   AKR-VK kontrast metriği = üreteç (pruvo-jenerator jeneratorler/foto/isimlik_uret.py kontrast_orani, KONTRAST_MIN 3.0)
 *   AKR-V1 6 farklı çift -> ④ önizleme gövdesi {yazi, plaka} doğru + sunucu kabul (6/6)
 *   AKR-V2 3 aynı çift -> ③ kontrast metni + ileri pasif + istek 0 + sunucu 400 (3/3)
 *   AKR-V3 varsayılan {yazi: Beyaz, plaka: Siyah} (veri + ③ işaretli seçim)
 *   AKR-V4 ANA_RENKLER dışı (Kırmızı) -> hüküm "renk" + sunucu 400
 *   AKR-V5 figür çeşidi + kayıtsız tür -> eski davranış (tek seçici; tüm bölgeler aynı; 2 renk 400)
 *   AKR-V6 60 mm PLA birim önce = sonra (önce: HEAD 8e14e156 ölçümü 60000 kuruş)
 *   AKR-V7 formSunumDegeri genislik_mm = olcu · gövdede genislik_mm = olcu_mm
 *   AKR-DOM ③ anahtarlık–yazı renk seçici 2 + ölçü kontrolü 1 · anahtarlık–figür renk seçici 1
 * BaBa 13 Eki 11:4x (Okan canlı ekran görüntüsü) + ArTisT 19. okuma:
 *   AKR-V8 ③ TEK ölçü kontrolünün etiketi "Uzun kenar (kulak dahil)" (ayrı "Ölçü" etiketi 0) · figür çeşidi + yapboz AYNEN
 *   AKR-V9 "Kulak konumu" seçicisi 0 (DOM'da alan da metin de yok) · ④ gövdede kulak "sol-ust" (sabit, 6/6)
 *   AKR-V10 metinler BİREBİR (bağımsız yazılmış sabitler): ③ yardım cümlesi · kontrast uyarısı (veri + ③ DOM) ·
 *           etiketler "Yazı rengi" / "Taban rengi" (veri + ③ legend sırası)
 *   AKR-V11 beyaz yazı / siyah taban (varsayılan): uyarı 0 + ileri açık + önizleme isteği 1
 * MUTANT (kopyada): sunucu kontrast hükmü kalkar -> V2 · istemci tek seçiciye döner -> DOM (+ seçime bağlı vakalar) ·
 *   kontrast metin eşlemesi bozulur -> V2,V10 · kulak seçici geri gelir -> V9 · sürgü etiketi bayrağı kalkar -> V8.
 */
// ArTisT 19. okuma (kutu 13 Eki 11:5x) — kaynaktan OKUNMAZ, birebir yazılır.
const AKR_METIN = {
  renk: "Yazı için bir, taban için bir renk seç; ikisi birbirinden belirgin olmalı ki yazı net okunsun.",
  kontrast: "Yazı ve taban rengi birbirine çok yakın; yazı okunmaz. Farklı bir renk seç.",
  etiket: ["Yazı rengi", "Taban rengi"], olcu: "Uzun kenar (kulak dahil)" };
// Üreteçle ölçülen 9 çift (python3, isimlik_uret.kontrast_orani; RENK_HEX Siyah #1A1A1A · Beyaz #F2F2F2 · Gri #818184).
const AKR_URETEC = { "Siyah/Siyah": 1, "Siyah/Beyaz": 15.5466, "Siyah/Gri": 4.481, "Beyaz/Siyah": 15.5466, "Beyaz/Beyaz": 1,
  "Beyaz/Gri": 3.4695, "Gri/Siyah": 4.481, "Gri/Beyaz": 3.4695, "Gri/Gri": 1 };
const AKR_ONCE_KURUS = 60000;
const akrCiftler = () => VERI.ANA_RENKLER.flatMap((y) => VERI.ANA_RENKLER.map((p) => ({ yazi: y, plaka: p })));
const akrSinif = (n, c) => String(n.className || "").split(" ").indexOf(c) >= 0;
async function akrEkran(kaynak, V, kart) {
  const acikA = { acik: true, turler: [{ kod: "anahtarlik", ad: V.turBul("anahtarlik").ad, aciklama: "x", ornek_sayisi: 1,
    olculer: V.olcuSecenekleri("anahtarlik").map((mm) => ({ mm, fiyat_kurus: V.fiyatKurus("anahtarlik", mm) })) }] };
  const e = await ekranKos(kaynak, V, acikA, null, null, { kart, gorselSahte: true, turnstileOto: true });
  const d = () => [...e.bolum.agac()];
  const id = (x) => d().find((n) => n.id === x) || null;
  const p3 = () => { const p = id("foto-pencere-3"); return p ? [...p.agac()] : []; };
  return { e, d, id, p3 };
}
// ③ ölçümü: renk seçici (fieldset) sayısı, ölçü kontrolü (sürgü + "Uzun kenar" sayı alanı) sayısı.
function akrUc(p3) {
  const surgu = p3.find((n) => n.tagName === "INPUT" && n.id === "foto-olcu") || null;
  return { renkSecici: p3.filter((n) => n.tagName === "FIELDSET" && akrSinif(n, "foto-uretim-renk-secim")).length,
    olcuKontrol: p3.filter((n) => n.tagName === "INPUT" && (n.id === "foto-olcu" || n.id === "foto-param-genislik_mm")).length,
    // ③ ölçü etiketleri: form etiketi olup "ölçü"/"Uzun kenar" geçen metinler (ayrı "Ölçü" etiketi = çift kontrol izi)
    olcuEtiket: p3.filter((n) => akrSinif(n, "foto-uretim-form-etiket") && n.tagName !== "LEGEND" &&
      /ölçü|Ölçü|Uzun kenar/.test(n.textContent)).map((n) => n.textContent),
    surguAria: surgu ? surgu.getAttribute("aria-label") : null,
    legend: p3.filter((n) => n.tagName === "LEGEND").map((n) => n.textContent),
    yardim: p3.filter((n) => akrSinif(n, "foto-uretim-ayrinti") && n.textContent === AKR_METIN.renk).length };
}
async function akrIstemciCift(kaynak, V, cift) {
  const { e, d, id, p3 } = await akrEkran(kaynak, V, "anahtarlik_yazi");
  const r = { istisna: e.istisna + ":" + e.istisnaMetni };
  const ta = id("foto-param-satirlar");
  if (ta) { ta.value = "Ayşe"; ta.tetikle("input"); }
  const ileri = id("foto-ileri");
  if (ileri) { ileri.tetikle("click"); }
  Object.assign(r, akrUc(p3()));
  const isaretli = (b) => (p3().find((n) => n.tagName === "INPUT" && n.name === "foto-renk-" + b && n.checked) || {}).value || null;
  r.varsayilan = { yazi: isaretli("yazi"), plaka: isaretli("plaka") };
  for (const b of ["yazi", "plaka"]) {
    const k = p3().find((n) => n.tagName === "INPUT" && n.name === "foto-renk-" + b && n.value === cift[b]);
    if (k) { k.checked = true; k.tetikle("change"); }
  }
  r.uyari = p3().filter((n) => n.id === "foto-renk-kontrast" && n.textContent === VERI.URETEC_RED_METIN.kontrast).length;
  r.uyariBirebir = p3().filter((n) => n.id === "foto-renk-kontrast" && n.textContent === AKR_METIN.kontrast).length;
  // Kulak konumu seçicisi: alan (id) ya da "Kulak konumu" metni bölümün HERHANGİ bir yerinde (② + ③).
  r.kulakSecici = d().filter((n) => n.id === "foto-param-anahtarlik_kulak_konum" ||
    (n.textContent === "Kulak konumu" && !(n.children && n.children.length))).length;
  r.ileriAcik = !!ileri && ileri.disabled === false;
  if (ileri) { ileri.tetikle("click"); }
  const on = id("foto-aydinlatma-onay");
  if (on) { on.checked = true; on.tetikle("change"); }
  const btn = id("foto-onizle-buton");
  if (btn) { btn.tetikle("click"); }
  for (let i = 0; i < 5; i++) { await new Promise((c) => setTimeout(c, 0)); }
  const ist = e.istekler.filter((x) => /\/foto\/onizleme$/.test(x.u)).map((x) => x.govde);
  r.istek = ist.length;
  r.secim = ist.length === 1 && ist[0].secim ? { yazi: ist[0].secim.yazi_renk, plaka: ist[0].secim.plaka_renk } : null;
  r.genislik = ist.length === 1 && ist[0].parametreler ? ist[0].parametreler.genislik_mm : null;
  r.kulak = ist.length === 1 && ist[0].parametreler ? ist[0].parametreler.anahtarlik_kulak_konum : null;
  r.olcu = ist.length === 1 ? ist[0].olcu_mm : null;
  return r;
}
async function akrIstemci(kaynak, veriKaynak) {
  const V = veriYukle(veriKaynak || VERI_KAYNAK), iz = {};
  for (const c of akrCiftler()) { iz[c.yazi + "/" + c.plaka] = await akrIstemciCift(kaynak, V, c); }
  // Başka çeşit: anahtarlık–figür kartı (fotoğraf) -> ③ tek renk seçici (eski yol AYNEN).
  const f = await akrEkran(kaynak, V, "anahtarlik");
  cesitKartTikla(f.e.bolum, "figur");
  const dosya = f.id("foto-dosya");
  if (dosya) { dosya.files = [{ name: "kedi.jpg", type: "image/jpeg", size: 4096 }]; dosya.tetikle("change"); }
  const fi = f.id("foto-ileri");
  if (fi) { fi.tetikle("click"); }
  iz.figur = Object.assign(akrUc(f.p3()), { radyo: f.p3().filter((n) => n.tagName === "INPUT" && n.name === "foto-renk").length });
  iz.veri = { metin: V.URETEC_RED_METIN.kontrast,
    acik: (V.turBul("anahtarlik").alan_aciklamalari || {}).renk, et: V.turBul("anahtarlik").bolge_renk_secimi.etiketler,
    yapboz: ((V.turBul("yapboz") || {}).form_sunum || {}).uzun_kenar_mm || null };
  return iz;
}
async function akrSunucu(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x')").run();
  const iz = {};
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = (kod) => (kod === "anahtarlik" ? 1 : asilOrnek(kod));
  const kayit = VERI.turBul("anahtarlik"), brs = kayit.bolge_renk_secimi;
  let no = 0;
  const isKur = async () => {
    const is = "a8" + (++no).toString(16).padStart(30, "0"), iso = new Date().toISOString();
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, cesit) VALUES (?, 'anahtarlik', 60, 'z', ?, 'onizleme-hazir', 'gorev-akr', ?, 'yazi')")
      .bind(is, iso, iso).run();
    return is;
  };
  const fiyatla = async (yazi, plaka) => {
    const n = new Set([yazi, plaka]).size;
    const r = await fm.fotoKalemFiyatla(e2, { foto_is: await isKur(), olcu_mm: AH_MM, adet: 1, renkli: false, malzeme: "PLA",
      secim: { plaka_renk: plaka, yazi_renk: yazi, govde_malzeme: "PLA" }, renk_sayisi: n }, Date.now());
    return r.satir ? r.satir.birim_kurus : (r.kod + ":" + (r.hata && r.hata.hata));
  };
  try {
    iz.cift = {};
    for (const c of akrCiftler()) { iz.cift[c.yazi + "/" + c.plaka] = await fiyatla(c.yazi, c.plaka); }
    iz.kirmizi = [await fiyatla("Kırmızı", "Siyah"), await fiyatla("Beyaz", "Kırmızı")];
    // Kayıtsız tür (bellek yaması: alan silinir) -> eski kural: tüm bölgeler aynı renk kabul, iki renk 400.
    delete kayit.bolge_renk_secimi;
    iz.kayitsiz = { tek: await fiyatla("Beyaz", "Beyaz"), iki: await fiyatla("Beyaz", "Siyah") };
  } finally { VERI.ornekSayisi = asilOrnek; kayit.bolge_renk_secimi = brs; k.kapat(); }
  return iz;
}
console.log("AKR) ANAHTARLIK–YAZI iki renk (Yazı rengi + Taban rengi), ③'te kontrast uyarısı + tek ölçü kontrolü");
{
  const farkli = akrCiftler().filter((c) => c.yazi !== c.plaka).map((c) => c.yazi + "/" + c.plaka);
  const ayni = akrCiftler().filter((c) => c.yazi === c.plaka).map((c) => c.yazi + "/" + c.plaka);
  // VK: JS metriği üreteç tablosuyla (4 hane) eşit + eşik = üreteç KONTRAST_MIN; üreteç kaynağı makinedeyse sabitleri de.
  const brs = VERI.turBul("anahtarlik").bolge_renk_secimi;
  const vkFark = akrCiftler().filter((c) => {
    const o = VERI.kontrastOrani(c.yazi, c.plaka);
    return !(typeof o === "number" && Math.abs(o - AKR_URETEC[c.yazi + "/" + c.plaka]) < 5e-5);
  });
  const uretecDosya = path.join(process.env.HOME || "/", "dev", "pruvo-jenerator", "jeneratorler", "foto", "isimlik_uret.py");
  let uretecEsik = null;
  if (fs.existsSync(uretecDosya)) {
    const m = /^KONTRAST_MIN = ([0-9.]+)$/m.exec(fs.readFileSync(uretecDosya, "utf8"));
    uretecEsik = m ? Number(m[1]) : NaN;
  }
  console.log("  AKR 9 çift (yazı/taban -> oran): " + akrCiftler().map((c) => c.yazi + "/" + c.plaka + "=" +
    VERI.kontrastOrani(c.yazi, c.plaka).toFixed(4)).join(" · ") + " · eşik " + brs.kontrast_esigi +
    " · üreteç kaynağı " + (uretecEsik === null ? "makinede YOK (sabit tablo)" : "KONTRAST_MIN=" + uretecEsik));
  ol("AKR-VK kontrast metriği = üreteç (9/9 çift, eşik 3.0" + (uretecEsik === null ? "" : " = üreteç " + uretecEsik) + ")",
     vkFark.length === 0 && brs.kontrast_esigi === 3.0 && (uretecEsik === null || uretecEsik === brs.kontrast_esigi),
     JSON.stringify([vkFark, uretecEsik]));
  const akr = async (kaynak, fm, veriKaynak) => {
    const i = await akrIstemci(kaynak, veriKaynak), v = await akrSunucu(fm), s = {};
    s.V1 = farkli.every((x) => { const [y, p] = x.split("/"), r = i[x];
      return r.uyari === 0 && r.ileriAcik && r.istek === 1 && !!r.secim && r.secim.yazi === y && r.secim.plaka === p &&
        v.cift[x] === AKR_ONCE_KURUS; });
    s.V2 = ayni.every((x) => i[x].uyari === 1 && !i[x].ileriAcik && i[x].istek === 0 && v.cift[x] === "400:gecersiz-renk") &&
      ayni.every((x) => VERI.bolgeRenkHukmu("anahtarlik", { yazi: x.split("/")[0], plaka: x.split("/")[1] }) === "kontrast");
    s.V3 = JSON.stringify(brs.varsayilan) === '{"yazi":"Beyaz","plaka":"Siyah"}' &&
      akrCiftler().every((c) => { const d = i[c.yazi + "/" + c.plaka].varsayilan; return d.yazi === "Beyaz" && d.plaka === "Siyah"; });
    s.V4 = v.kirmizi.every((x) => x === "400:gecersiz-renk") &&
      VERI.bolgeRenkHukmu("anahtarlik", { yazi: "Kırmızı", plaka: "Siyah" }) === "renk";
    s.V5 = VERI.bolgeRenkSecimi("anahtarlik", "figur") === null && VERI.bolgeRenkSecimi("plaket") === null &&
      i.figur.renkSecici === 1 && i.figur.radyo >= 3 && v.kayitsiz.tek === AKR_ONCE_KURUS && v.kayitsiz.iki === "400:gecersiz-renk";
    s.V6 = VERI.fiyatKurus("anahtarlik", AH_MM, { renkli: false, malzeme: "PLA" }) === AKR_ONCE_KURUS &&
      farkli.every((x) => v.cift[x] === AKR_ONCE_KURUS);
    s.V7 = VERI.formSunumDegeri("anahtarlik", "genislik_mm", 75) === 75 &&
      farkli.every((x) => typeof i[x].olcu === "number" && i[x].genislik === i[x].olcu);
    s.DOM = akrCiftler().every((c) => { const r = i[c.yazi + "/" + c.plaka]; return r.renkSecici === 2 && r.olcuKontrol === 1; }) &&
      i.figur.renkSecici === 1;
    const hepsi = akrCiftler().map((c) => i[c.yazi + "/" + c.plaka]);
    s.V8 = hepsi.every((r) => JSON.stringify(r.olcuEtiket) === JSON.stringify([AKR_METIN.olcu]) && r.olcuKontrol === 1 &&
      r.surguAria === AKR_METIN.olcu + " (mm)") && i.figur.olcuEtiket.length === 1 && i.figur.olcuEtiket[0] !== AKR_METIN.olcu &&
      i.figur.surguAria === "Ölçü — en uzun boyut (mm)" && !!i.veri.yapboz && i.veri.yapboz.surgu_etiketi === undefined;
    s.V9 = hepsi.every((r) => r.kulakSecici === 0) && farkli.every((x) => i[x].kulak === "sol-ust");
    s.V10 = i.veri.metin === AKR_METIN.kontrast && i.veri.acik === AKR_METIN.renk &&
      JSON.stringify([i.veri.et.yazi, i.veri.et.plaka]) === JSON.stringify(AKR_METIN.etiket) &&
      hepsi.every((r) => JSON.stringify(r.legend) === JSON.stringify(AKR_METIN.etiket) && r.yardim === 1) &&
      ayni.every((x) => i[x].uyariBirebir === 1) && farkli.every((x) => i[x].uyariBirebir === 0);
    s.V11 = i["Beyaz/Siyah"].uyari === 0 && i["Beyaz/Siyah"].uyariBirebir === 0 && i["Beyaz/Siyah"].ileriAcik &&
      i["Beyaz/Siyah"].istek === 1;
    Object.defineProperty(s, "iz", { value: { i, v }, enumerable: false });
    return s;
  };
  const s = await akr(EKRAN_KAYNAK, foto);
  const { i, v } = s.iz;
  const say = (l, f) => l.filter(f).length;
  ol("AKR-V1 6 farklı çift -> ④ gövde {yazi, plaka} doğru + sunucu kabul (" +
     say(farkli, (x) => i[x].istek === 1 && v.cift[x] === AKR_ONCE_KURUS) + "/6)", s.V1,
     JSON.stringify(farkli.map((x) => [x, i[x].secim, i[x].uyari, i[x].ileriAcik, v.cift[x], i[x].istisna])));
  ol("AKR-V2 3 aynı çift -> ③ kontrast metni + ileri pasif + istek 0 + sunucu 400 (" +
     say(ayni, (x) => i[x].uyari === 1 && !i[x].ileriAcik && v.cift[x] === "400:gecersiz-renk") + "/3)", s.V2,
     JSON.stringify(ayni.map((x) => [x, i[x].uyari, i[x].ileriAcik, i[x].istek, v.cift[x]])));
  ol("AKR-V3 varsayılan yazı Beyaz + taban Siyah (veri + ③ işaretli)", s.V3, JSON.stringify(i["Siyah/Siyah"].varsayilan));
  ol("AKR-V4 ANA_RENKLER dışı (Kırmızı) -> 400 (2/2) + hüküm 'renk'", s.V4, JSON.stringify(v.kirmizi));
  ol("AKR-V5 figür çeşidi + kayıtsız tür -> eski davranış (③ tek seçici, aynı renk kabul, 2 renk 400)", s.V5,
     JSON.stringify([i.figur, v.kayitsiz]));
  ol("AKR-V6 60 mm PLA birim önce " + AKR_ONCE_KURUS + " = sonra " + VERI.fiyatKurus("anahtarlik", AH_MM, { renkli: false, malzeme: "PLA" }) +
     " kuruş (sunucu 6 çift aynı)", s.V6, JSON.stringify(farkli.map((x) => v.cift[x])));
  ol("AKR-V7 genislik_mm = olcu (formSunumDegeri + ④ gövde)", s.V7, JSON.stringify(farkli.map((x) => [i[x].genislik, i[x].olcu])));
  ol("AKR-DOM ③ anahtarlık–yazı renk seçici " + i["Beyaz/Siyah"].renkSecici + " · ölçü kontrolü " + i["Beyaz/Siyah"].olcuKontrol +
     " · anahtarlık–figür renk seçici " + i.figur.renkSecici, s.DOM,
     JSON.stringify(akrCiftler().map((c) => { const r = i[c.yazi + "/" + c.plaka]; return [r.renkSecici, r.olcuKontrol]; }).concat([i.figur])));
  const bs = i["Beyaz/Siyah"];
  ol("AKR-V8 ③ tek ölçü kontrolü etiketi '" + AKR_METIN.olcu + "' (ölçü etiketleri " + JSON.stringify(bs.olcuEtiket) +
     ") · figür + yapboz AYNEN", s.V8, JSON.stringify([bs.olcuEtiket, bs.surguAria, i.figur.olcuEtiket, i.figur.surguAria, i.veri.yapboz]));
  ol("AKR-V9 kulak seçici " + akrCiftler().reduce((t, c) => t + i[c.yazi + "/" + c.plaka].kulakSecici, 0) +
     " · ④ gövdede kulak sol-ust " + farkli.filter((x) => i[x].kulak === "sol-ust").length + "/6", s.V9,
     JSON.stringify(farkli.map((x) => [i[x].kulakSecici, i[x].kulak])));
  ol("AKR-V10 ArTisT metinleri birebir (yardım · kontrast uyarısı · Yazı rengi/Taban rengi)", s.V10,
     JSON.stringify([i.veri, bs.legend, bs.yardim, ayni.map((x) => i[x].uyariBirebir)]));
  ol("AKR-V11 Beyaz yazı / Siyah taban: uyarı 0 + ileri açık + önizleme isteği 1", s.V11,
     JSON.stringify([bs.uyari, bs.uyariBirebir, bs.ileriAcik, bs.istek]));
  const kir = (m) => Object.keys(m).filter((x) => m[x] !== true).sort();
  const AKR_MUT = [
    ["AKR-M1 sunucu kontrast hükmü kalkar (aynı çift kabul)", "sunucu",
     "return VERI.bolgeRenkHukmu(turKod, aktif, cesit) === \"\" && n <= tavan", "return n <= tavan", ["V2"]],
    ["AKR-M2 istemci tek seçiciye döner (iki seçici çizilmez)", "ekran",
     "    if (bk && !renkliSunulur(nt.kod)) return bolgeRenkSecici(nt, bk, degisti);\n", "", ["DOM", "V1", "V2", "V3", "V10"]],
    ["AKR-M3 kontrast metin eşlemesi bozulur (anahtar kayar -> genel metin)", "veri",
     "      \"kontrast\": \"Yazı ve taban rengi", "      \"kontrast-x\": \"Yazı ve taban rengi", ["V10", "V2"]],
    ["AKR-M4 kulak seçici geri gelir (form_sunum kulak satırı kalkar)", "veri",
     "          anahtarlik_kulak_konum: { deger: \"varsayilan\" }\n", "", ["V9"]],
    ["AKR-M5 sürgü etiket bayrağı kalkar ('Ölçü' etiketi geri gelir)", "veri",
     "genislik_mm: { deger: \"olcu\", surgu_etiketi: true }", "genislik_mm: { deger: \"olcu\" }", ["V8"]],
  ];
  let akrMut = 0;
  for (const [ad, hedef, capa, yerine, olmeli] of AKR_MUT) {
    let m = null;
    if (hedef === "ekran") {
      if (EKRAN_KAYNAK.split(capa).length - 1 === 1) { m = await akr(EKRAN_KAYNAK.replace(capa, yerine), foto); }
    } else if (hedef === "veri") {
      if (VERI_KAYNAK.split(capa).length - 1 === 1) { m = await akr(EKRAN_KAYNAK, foto, VERI_KAYNAK.replace(capa, yerine)); }
    } else {
      const fm = await mutantModul(capa, yerine);
      if (fm) { m = await akr(EKRAN_KAYNAK, fm); }
    }
    if (!m) { ol(ad + " çapa bulundu", false, capa); continue; }
    const tut = JSON.stringify(kir(m)) === JSON.stringify(olmeli.slice().sort());
    if (tut) { akrMut++; }
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", tut, JSON.stringify(kir(m)));
  }
  console.log("  AKR MUTANT " + akrMut + "/" + AKR_MUT.length);
}

// ================================================================ TPU — anahtarlık TPU (+%55, tek renk Beyaz), Okan 13 Eki
/**
 * Okan 13 Eki 23:1x "anahtarlıklara tpu da ekle fiyatını ayarla" + 23:2x "yazı anahtarlıkta da tpu olmalı" + BaBa 23:3x
 * TPU renk listesi ["Beyaz"] (VERİ: anahtarlik.malzeme_renkleri). Sunucu (fotoKalemFiyatla) vakaları, temiz SQLite:
 *   TA  (a) yazı + figür çeşidi TPU fiyatı = round(taban × 1,55) = VERI.fiyatKurus(.., {malzeme:"TPU"}) (istemci formülü),
 *           satır malzeme TPU + " · TPU (+%55)"
 *   TB  (b) TPU + Renkli -> 400 (figür çeşidi palet + yazı çeşidi)
 *   TC  (c) TPU + Beyaz dışı renk (yazı Siyah/Beyaz, Siyah/Siyah, figür ["Siyah"]) -> 400
 *   TD  (d) bust / plaket TPU -> 400 gecersiz-malzeme (mesaj "PLA, PETG ya da TPU"); figür türünde VERI.turMalzemeleri TPU'suz
 *   TE  (e) girdi.json (uretecGirdiJson) malzeme "TPU" (PLA'da "PLA")
 */
async function tpuSunucu(fm) {
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = () => 1;
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur());
  await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('anahtarlik_yazi', 1, 'x'), ('anahtarlik_figur', 1, 'x'), " +
    "('bust', 1, 'x'), ('plaket', 1, 'x')").run();
  let no = 0;
  const isKur = async (tur, mm, asama, cesit) => {
    const is = "7b" + (++no).toString(16).padStart(30, "0"), iso = new Date().toISOString();
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih, son_kontrol, cesit)" +
      " VALUES (?, ?, ?, 'z', ?, ?, 'gorev-tpu', ?, 0, ?)").bind(is, tur, mm, iso, asama, iso, cesit).run();
    return is;
  };
  const sonuc = (r) => (r.satir ? r.satir : r.kod + ":" + (r.hata && r.hata.hata));
  const yazi = async (malz, yaziR, plakaR, ek) => sonuc(await fm.fotoKalemFiyatla(e2, { foto_is: await isKur("anahtarlik", AH_MM, "onizleme-hazir", "yazi"),
    olcu_mm: AH_MM, adet: 1, renkli: false, malzeme: malz, secim: { plaka_renk: plakaR, yazi_renk: yaziR, govde_malzeme: malz },
    renk_sayisi: new Set([yaziR, plakaR]).size, ...(ek || {}) }, Date.now()));
  const figur = async (ek) => sonuc(await fm.fotoKalemFiyatla(e2, { foto_is: await isKur("anahtarlik", AH_MM, "hazir", "figur"),
    olcu_mm: AH_MM, adet: 1, ...ek }, Date.now()));
  const s = {}, iz = {};
  try {
    const formul = VERI.fiyatKurus("anahtarlik", AH_MM, { renkli: false, malzeme: "TPU" });
    const ya = await yazi("TPU", "Beyaz", "Beyaz"), fa = await figur({ malzeme: "TPU", renkler: ["Beyaz"] });
    iz.a = { formul, yazi: ya.birim_kurus || ya, figur: fa.birim_kurus || fa, detay: ya.parametre_detay };
    s.TA = formul === Math.round(VERI.fiyatKurus("anahtarlik", AH_MM) * 1.55) && formul === 93000 &&
      ya.birim_kurus === formul && ya.malzeme === "TPU" && / · TPU \(\+%55\)/.test(ya.parametre_detay || "") &&
      fa.birim_kurus === formul && fa.malzeme === "TPU" && / · TPU \(\+%55\)/.test(fa.parametre_detay || "");
    iz.b = [await figur({ malzeme: "TPU", renkli: true, renkler: ["Beyaz"] }), await yazi("TPU", "Beyaz", "Beyaz", { renkli: true }),
      await figur({ malzeme: "PLA", renkli: true, renkler: ["Beyaz"] })];
    s.TB = iz.b[0] === "400:gecersiz-renk" && iz.b[1] === "400:gecersiz-renk" && !!iz.b[2].birim_kurus;
    iz.c = [await yazi("TPU", "Siyah", "Beyaz"), await yazi("TPU", "Siyah", "Siyah"), await figur({ malzeme: "TPU", renkler: ["Siyah"] }),
      await yazi("PLA", "Siyah", "Beyaz")];
    s.TC = iz.c.slice(0, 3).every((x) => typeof x === "string" && /^400:gecersiz-(renk|secim)$/.test(x)) && !!iz.c[3].birim_kurus;
    const bust = await isKur("bust", 100, "onizleme-hazir", ""), plaket = await isKur("plaket", 100, "hazir", "");
    const bRed = await fm.fotoKalemFiyatla(e2, { foto_is: bust, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], malzeme: "TPU", secim: { govde_malzeme: "TPU" } }, Date.now());
    const pRed = await fm.fotoKalemFiyatla(e2, { foto_is: plaket, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], malzeme: "TPU" }, Date.now());
    const pOk = await fm.fotoKalemFiyatla(e2, { foto_is: plaket, olcu_mm: 100, adet: 1, renkler: ["Beyaz"], malzeme: "PETG" }, Date.now());
    iz.d = [sonuc(bRed), sonuc(pRed), bRed.hata && bRed.hata.mesaj, VERI.turMalzemeleri("figur")];
    s.TD = bRed.kod === 400 && bRed.hata.hata === "gecersiz-malzeme" && pRed.kod === 400 && pRed.hata.hata === "gecersiz-malzeme" &&
      bRed.hata.mesaj === "Malzeme seçimi geçersiz (PLA, PETG ya da TPU)." && !!pOk.satir &&
      ["plaket", "figur", "yapboz", "bust"].every((t) => VERI.turMalzemeleri(t).indexOf("TPU") < 0);
    const gT = fm.uretecGirdiJson("PR-TPU", { kalem: 0, tur: "anahtarlik", olcu_mm: AH_MM, secim: { govde_malzeme: "TPU", plaka_renk: "Beyaz", yazi_renk: "Beyaz" } });
    const gP = fm.uretecGirdiJson("PR-TPU", { kalem: 0, tur: "anahtarlik", olcu_mm: AH_MM, secim: { govde_malzeme: "PLA", plaka_renk: "Siyah", yazi_renk: "Beyaz" } });
    iz.e = [gT.malzeme, gP.malzeme, gT.malzemeler];
    s.TE = gT.malzeme === "TPU" && gP.malzeme === "PLA" && JSON.stringify(gT.malzemeler) === '{"govde":"TPU"}';
  } finally { VERI.ornekSayisi = asilOrnek; k.kapat(); }
  return { s, iz };
}
console.log("TPU) ANAHTARLIK TPU — +%55 (FILAMENT_FARK), tek renk Beyaz, TPU+Renkli 400, başka türde TPU 400, girdi.json malzeme");
{
  const { s, iz } = await tpuSunucu(foto);
  ol("TPU-a yazı + figür çeşidi TPU 60 mm = round(600 TL × 1,55) = 930 TL = VERI.fiyatKurus(TPU) (istemci=sunucu) · ' · TPU (+%55)'", s.TA === true, JSON.stringify(iz.a));
  ol("TPU-b TPU + Renkli -> 400 gecersiz-renk (figür palet + yazı); PLA + Renkli figür geçer", s.TB === true, JSON.stringify(iz.b));
  ol("TPU-c TPU + Siyah (yazı Siyah/Beyaz · Siyah/Siyah · figür Siyah) -> 400; PLA Siyah/Beyaz geçer", s.TC === true, JSON.stringify(iz.c));
  ol("TPU-d bust / plaket TPU -> 400 gecersiz-malzeme 'PLA, PETG ya da TPU' · figür/yapboz/bust/plaket turMalzemeleri TPU'suz", s.TD === true, JSON.stringify(iz.d));
  ol("TPU-e girdi.json malzeme TPU (PLA'da PLA) + malzemeler.govde", s.TE === true, JSON.stringify(iz.e));
  // MUTANTLAR (gecici foto.js kopyasi, canli govde DEGIL): M1 TPU'ya %30 uygulanir · M2 TPU+Renkli gecer -> KIRMIZI.
  const TPU_MUT = [
    ["TPU-M1 TPU'ya %30 uygulanir (sunucu)", "  const birim = rs ? VERI.fiyatKurus(tur.kod, olcu.mm, { renkli: rs.renkli, malzeme: malz }) : null;",
     "  const birim = rs ? VERI.fiyatKurus(tur.kod, olcu.mm, { renkli: rs.renkli, malzeme: malz === \"TPU\" ? \"PETG\" : malz }) : null;", ["TA"]],
    ["TPU-M2 TPU + Renkli gecer", "  if (mr && (renkli || (Array.isArray(k.renkler)", "  if (mr && (false || (Array.isArray(k.renkler)", ["TB"]],
    ["TPU-MK KONTROL (yorum)", "/** Satir detayindaki fiyat secimi:", "/**  Satir detayindaki fiyat secimi:", []],
  ];
  for (const [ad, capa, yerine, olmeli] of TPU_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
    const m = (await tpuSunucu(fm)).s;
    const kir = Object.keys(m).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", Object.keys(m).length === 5 && JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ================================================================ RN) ④ TEK RENK ÖNİZLEMESİ — GRİ MODEL GÖRSELİ (Okan 14 Eki 12:58/12:59)
// Tek renk (Siyah/Beyaz/Gri) seçen müşterinin önizlemesi hazır olunca Worker AYNI işin konsept görseliyle sağlayıcının
// image-to-3d ucunu DOKUSUZ açar (gövde sabit, model ORTAMDAN, kalıp `-6-lite`), alfa küçük resmi R2 `<is>-gri.png`'ye
// iner, ④ gri görsel + "Görsel örnektir" cümlesi. Renkli'de HER ŞEY AYNEN; renk değişimi yeni çağrı açmaz; secret yok /
// kalıp dışı -> 0 çağrı + eski davranış; tavan dolu -> 0 çağrı + Okan e-postası; sipariş build'i KENDİSİ kurar
// (14 Eki 03:0x önizleme build'i + Mac renk çizimi ④'ten ÇIKTI; eski RN1-RN10 vakaları GR'ye çevrildi).
//   SUNUCU GR1-GR13 + RN11/RN12 (gerçek SQLite + sahte sağlayıcı/R2) · İSTEMCİ RNE/RNH (sahte DOM) · MUTANTLAR (kopyada).
const RN_CUMLE = "Önizleme seçtiğin renkte çizildi; ürün bu renkte üretilir.";   // üreteç kolu — kaynaktan OKUNMAZ
const RN_HAZIRLANIYOR = "Renk önizlemesi hazırlanıyor…";
const GRI_CUMLE = (renk) => "Görsel örnektir — ürün seçtiğiniz tek renkte (" + renk + ") üretilir.";   // Okan 14 Eki — kaynaktan OKUNMAZ
const GRI_MODEL_TEST = "sahte-6-lite";   // kalıba uyan SAHTE ad (gerçek model adı repoda YOK)
const GRI_ENV = { ...OKAN_EPOSTA_ENV, URETIM_GRI_MODEL: GRI_MODEL_TEST };
const GRI_GOVDE_ANAHTAR = "ai_model,alpha_thumbnail,enable_pbr,image_url,should_texture,target_formats";
const griPostSay = () => P.cagri.filter((c) => c === "POST /v1/image-to-3d").length;
const rnBuildSay = () => P.cagri.filter((c) => /^POST .*\/v1\/build$/.test(c)).length;
async function grSunucu(fm) {
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = () => 1;
  const k = koprukur(); await k.hazir;
  const r2b = r2Kur();
  const e2 = envKur(k.d1, r2b, GRI_ENV);
  const s = {}, iz = {};
  try {
    await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x'), ('insan', 1, 'x')").run();
    let ip = 0;
    const cagE = async (e, yol, govde) => fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, {
      method: govde ? "POST" : "GET",
      headers: { "CF-Connecting-IP": "10.77.0." + (++ip), ...(govde ? { "Content-Type": "application/json" } : {}) },
      body: govde ? JSON.stringify(govde) : undefined }), e, new URL("https://pruvo3d.com/api/shop" + yol), yol.split("?")[0], null);
    const cag = (yol, govde) => cagE(e2, yol, govde);
    const js = async (r) => { try { return { kod: r.status, ...(await r.json()) }; } catch (e) { return { kod: r.status }; } };
    const sifirla = async (no) => {
      await k.d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(no).run();
      await k.d1.prepare("UPDATE foto_renk_onizleme SET son_kontrol = 0 WHERE is_no = ?").bind(no).run();
    };
    const durumE = async (e, no) => { await sifirla(no); return js(await cagE(e, "/foto/durum?is=" + no)); };
    const durum = (no) => durumE(e2, no);
    const renkPost = async (no, renk) => js(await cag("/foto/renk", { is: no, renk }));
    const satir = async (no) => k.d1.prepare("SELECT renk, asama, build_gorev, build_olcu, hata FROM foto_renk_onizleme" +
      " WHERE is_no = ?").bind(no).first();
    const onizleE = async (e, ek) => js(await cagE(e, "/foto/onizleme", onizlemeGovde(ek)));
    const onizle = (ek) => onizleE(e2, ek);
    // Hazıra kadar: 1 prototip sürüyor · 2 prototip hazır + gri çağrısı · 3 gri sürüyor · 4 gri bitti.
    const hazirlaE = async (e, no, n) => { let d = null; for (let i = 0; i < (n || 4); i++) { d = await durumE(e, no); } return d; };
    const hazirla = (no, n) => hazirlaE(e2, no, n);
    const kredi = async (no, adim) => (await k.d1.prepare("SELECT adim, siparis_no, gorev, kredi FROM foto_kredi WHERE is_no = ? AND adim = ?")
      .bind(no, adim).all()).results;
    const renderBekleyen = async () => (await k.d1.prepare("SELECT COUNT(*) AS n FROM foto_renk_onizleme WHERE asama = 'render-bekliyor'").first()).n;
    const KONSEPT_URI = "data:image/png;base64," + Buffer.from(PNG).toString("base64");

    // GR1: tek renk Beyaz -> prototip hazır olunca TAM 1 image-to-3d POST · gövde SABİT (dokusuz, model ortamdan,
    // texture_prompt YOK, giriş = R2 konsept görseli data URI) · build 0 · satır 'gri' (gri: önekli görev).
    const g0 = griPostSay(), b0 = rnBuildSay(), pg0 = P.griGovde.length, p0 = P.protoGovde.length;
    const o1 = await onizle({ renk: "Beyaz" });
    const ilk = await durum(o1.is);
    const d1b = await durum(o1.is);
    const r1 = await satir(o1.is);
    const gv = P.griGovde.slice(pg0);
    const gorev1 = ((await k.d1.prepare("SELECT gorev FROM foto_isler WHERE is_no = ?").bind(o1.is).first()) || {}).gorev;
    const g1 = gv[0] || {};
    iz.GR1 = { o1: o1.kod, ilk: ilk.asama, d1b, r1, post: griPostSay() - g0, build: rnBuildSay() - b0,
      govde: gv.map((g) => ({ ...g, image_url: String(g.image_url).slice(0, 40) })),
      proto: P.protoGovde.slice(p0).map((g) => Object.keys(g).sort().join(",")) };
    s.GR1 = o1.kod === 200 && ilk.asama === "onizleme" && d1b.asama === "hazir" && d1b.onizleme_renk === "Beyaz" &&
      d1b.onizleme_renk_durum === "hazirlaniyor" && !("onizleme_renk_url" in d1b) &&
      iz.GR1.post === 1 && gv.length === 1 && iz.GR1.build === 0 &&
      Object.keys(g1).sort().join(",") === GRI_GOVDE_ANAHTAR && g1.should_texture === false && g1.enable_pbr === false &&
      g1.alpha_thumbnail === true && JSON.stringify(g1.target_formats) === '["glb"]' && g1.ai_model === GRI_MODEL_TEST &&
      !("texture_prompt" in g1) && g1.image_url === KONSEPT_URI &&
      !!r1 && r1.asama === "gri" && r1.build_gorev.startsWith("gri:") && r1.build_gorev.length > 4 &&
      // Prototip isteği renkten BAĞIMSIZ (sağlayıcıya renk/istem GİTMEZ).
      iz.GR1.proto.length === 1 && iz.GR1.proto[0] === "image_url,name,remove_background";

    // GR2: görev biter -> alfa küçük resmi R2 `<is>-gri.png` · durum hazir + gorunum=gri url + gorunum alanı + sağlayıcı
    // url · görsel 200 (gri bayt) · kredi 'gri' 5 (siparişsiz) · çağrı hâlâ 1 · Mac kuyruğu 0 · GLB yok · eski ?renk= 404.
    const d1c = await durum(o1.is);
    const d1d = await durum(o1.is);
    const d1e = await durum(o1.is);
    const gg = await cag("/foto/gorsel?is=" + o1.is + "&gorunum=gri");
    const ggBayt = gg.status === 200 ? new Uint8Array(await gg.arrayBuffer()) : null;
    const gEski = await cag("/foto/gorsel?is=" + o1.is + "&renk=Beyaz");
    const kr1 = await kredi(o1.is, "gri");
    const GU1 = "/api/shop/foto/gorsel?is=" + o1.is + "&gorunum=gri";
    iz.GR2 = { d1c, d1d, gg: gg.status, tip: gg.headers.get("Content-Type"), gEski: gEski.status, kr1, r: await satir(o1.is),
      post: griPostSay() - g0, render: await renderBekleyen(), glb: r2b.m.has("foto-onizleme/" + o1.is + "-model.glb") };
    s.GR2 = d1c.onizleme_renk_durum === "hazirlaniyor" && d1d.asama === "hazir" && d1d.onizleme_renk_durum === "hazir" &&
      d1d.onizleme_renk === "Beyaz" && d1d.onizleme_renk_url === GU1 && d1d.onizleme_renk_gorunum === "gri" &&
      d1d.onizleme_saglayici_url === "/api/shop/foto/gorsel?is=" + o1.is && d1d.gorsel === "/api/shop/foto/gorsel?is=" + o1.is &&
      d1e.onizleme_renk_durum === "hazir" && d1e.onizleme_renk_url === GU1 &&
      gg.status === 200 && gg.headers.get("Content-Type") === "image/png" && !!ggBayt && Buffer.from(ggBayt).equals(Buffer.from(GRI_PNG)) &&
      gEski.status === 404 && kr1.length === 1 && kr1[0].kredi === 5 && kr1[0].siparis_no === "" &&
      !!iz.GR2.r && iz.GR2.r.asama === "gri-hazir" && iz.GR2.post === 1 && iz.GR2.render === 0 && iz.GR2.glb === false;

    // GR8 (panel): 24 sa'te 1 gri çağrı -> kredi tahmini 11 (5 gri + 6 prototip) · tavan 30 · gri açık · süren 0 ·
    // build alanı YOK; secret'siz ortamda gri_acik false (özellik kapalı panelde görünür).
    const oz = await (await fm.panelFotoOzet(e2, Date.now())).json();
    const ozKapali = await (await fm.panelFotoOzet(envKur(k.d1, r2b), Date.now())).json();
    iz.GR8 = { ro: oz.renk_onizleme, kapali: ozKapali.renk_onizleme };
    s.GR8 = !!oz.renk_onizleme && oz.renk_onizleme.kurulu === true && oz.renk_onizleme.gri_acik === true &&
      oz.renk_onizleme.son_24s_gri === 1 && oz.renk_onizleme.kredi_tahmini === 11 && oz.renk_onizleme.kredi_gri === 5 &&
      oz.renk_onizleme.kredi_prototip === 6 && oz.renk_onizleme.tavan === 30 && oz.renk_onizleme.gri_suren === 0 &&
      !("kredi_build" in oz.renk_onizleme) && !!ozKapali.renk_onizleme && ozKapali.renk_onizleme.gri_acik === false;

    // GR3: Renkli (renk alanı YOK) -> satır 0 · image-to-3d 0 · build 0 · yanıtta renk alanı 0 · prototip gövdesi AYNI.
    const g3 = griPostSay(), b3 = rnBuildSay(), p3 = P.protoGovde.length;
    const o2 = await onizle();
    const d2 = await hazirla(o2.is);
    iz.GR3 = { d2, r: await satir(o2.is), post: griPostSay() - g3, b: rnBuildSay() - b3,
      proto: P.protoGovde.slice(p3).map((g) => Object.keys(g).sort().join(",")) };
    s.GR3 = d2.asama === "hazir" && !("onizleme_renk" in d2) && !("onizleme_renk_durum" in d2) && !("onizleme_renk_url" in d2) &&
      !("onizleme_renk_gorunum" in d2) && iz.GR3.r === null && iz.GR3.post === 0 && iz.GR3.b === 0 &&
      iz.GR3.proto[0] === iz.GR1.proto[0];

    // GR4: renk değişimi (Beyaz -> Siyah -> Gri) -> YENİ ÇAĞRI 0 · aynı gri görsel · renk adı değişir · satır gri-hazir ·
    // /foto/renk Renkli 400 · bilinmeyen iş 404.
    const g4 = griPostSay();
    const c1 = await renkPost(o1.is, "Siyah");
    const d4a = await durum(o1.is);
    const c2 = await renkPost(o1.is, "Gri");
    const d4b = await durum(o1.is);
    const r4 = await satir(o1.is);
    const c3 = await renkPost(o1.is, "Renkli");
    const c4 = await renkPost("9".repeat(32), "Beyaz");
    iz.GR4 = { c1, d4a, c2, d4b, r4, c3: c3.kod, c4: c4.kod, post: griPostSay() - g4 };
    s.GR4 = c1.kod === 200 && c1.onizleme_renk === "Siyah" && c1.onizleme_renk_durum === "hazir" && c1.onizleme_renk_url === GU1 &&
      d4a.onizleme_renk === "Siyah" && d4a.onizleme_renk_durum === "hazir" && d4a.onizleme_renk_url === GU1 &&
      c2.onizleme_renk === "Gri" && c2.onizleme_renk_url === GU1 && d4b.onizleme_renk === "Gri" && d4b.onizleme_renk_durum === "hazir" &&
      !!r4 && r4.asama === "gri-hazir" && r4.renk === "Gri" && iz.GR4.post === 0 && c3.kod === 400 && c4.kod === 404;

    // GR5: model secret YOK / kalıp DIŞI (tam sürüm `-6` = 30 kr · büyük harf · ek · kısa ad · başka sürüm) ->
    // image-to-3d 0 · build 0 · satır 0 · yanıt eski (renk alanı YOK) · /foto/renk 503 kapali.
    const KAPALI_MODELLER = [undefined, "", "abcdef-6", "ABCDEF-6-lite", "abcdef-6-lite-x", "ab-6-lite", "abcdef-5-lite"];
    iz.GR5 = [];
    let gr5 = true;
    for (const m of KAPALI_MODELLER) {
      const e5 = envKur(k.d1, r2b, { ...OKAN_EPOSTA_ENV, URETIM_GRI_MODEL: m });
      const g5 = griPostSay(), b5 = rnBuildSay();
      const o = await onizleE(e5, { renk: "Beyaz" });
      const d = await hazirlaE(e5, o.is);
      const rp = await cagE(e5, "/foto/renk", { is: o.is, renk: "Gri" });
      const r = await satir(o.is);
      const x = { m: m === undefined ? "YOK" : m, kod: o.kod, d: d.asama, alan: "onizleme_renk" in d, post: griPostSay() - g5,
        b: rnBuildSay() - b5, r: r && r.asama, rp: rp.status };
      iz.GR5.push(x);
      gr5 = gr5 && x.kod === 200 && x.d === "hazir" && !x.alan && x.post === 0 && x.b === 0 && r === null && x.rp === 503;
    }
    s.GR5 = gr5;

    // GR6: tavan dolu (foto_ayar renk_onizleme_tavan = mevcut sayı) -> image-to-3d 0 · asama 'tavan' · 'yok' · Okan'a
    // E-POSTA 1 (ikinci istekte ve renk değişiminden sonraki denemede tekrar YOK) · e-posta "~11 kredi (6 prototip + 5 gri model)".
    const n6 = (await (await fm.panelFotoOzet(e2, Date.now())).json()).renk_onizleme.son_24s_gri;
    await k.d1.prepare("INSERT INTO foto_ayar (anahtar, deger, guncel) VALUES ('renk_onizleme_tavan', ?, 0)").bind(String(n6)).run();
    const g6 = griPostSay(), e6 = P.eposta.length;
    const o4 = await onizle({ renk: "Siyah" });
    const d6a = await hazirla(o4.is);
    const o5 = await onizle({ renk: "Beyaz" });
    const d6b = await hazirla(o5.is);
    await renkPost(o4.is, "Gri");
    const d6c = await durum(o4.is);
    const ep = P.eposta.slice(e6).filter((x) => /tavanı doldu/.test(x.subject || ""));
    iz.GR6 = { n6, d6a, d6b, d6c, r4: await satir(o4.is), post: griPostSay() - g6, ep: ep.map((x) => [x.to, x.subject]),
      metin: ep.length ? JSON.stringify(ep[0]).includes("~11 kredi (6 prototip + 5 gri model)") : false };
    s.GR6 = n6 >= 1 && d6a.asama === "hazir" && d6a.onizleme_renk_durum === "yok" && d6b.onizleme_renk_durum === "yok" &&
      d6c.onizleme_renk_durum === "yok" && iz.GR6.post === 0 &&
      !!iz.GR6.r4 && iz.GR6.r4.asama === "tavan" && iz.GR6.r4.hata === "tavan" && iz.GR6.r4.build_gorev === "" &&
      ep.length === 1 && JSON.stringify(ep[0].to).includes(OKAN_EPOSTA) && iz.GR6.metin === true;
    await k.d1.prepare("DELETE FROM foto_ayar WHERE anahtar = 'renk_onizleme_tavan'").run();

    // GR7: sipariş -> gri önizleme BUILD DEĞİLDİR: zincir build'i KENDİSİ kurar (POST build 1, input = aynı prototip,
    // zincir başı gri görevi DEĞİL) · sipariş başına kredi + build sayısı = önizlemesi Renkli alınmış siparişle AYNI.
    const siparis = async (no, olcu, renk) => {
      const b = await istek(e2, "/baslat", { govde: { sozlesme_onay: true, aydinlatma_onay: true, onay_surum: VERI.onay_surum,
        odeme: "kart", musteri, turnstile_token: "j", sepet: [{ foto_is: no, olcu_mm: olcu, adet: 1, renkler: [renk] }] } });
      if (b.kod === 200) { await k.d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(b.v.no).run(); }
      return b.v && b.v.no;
    };
    const zincirSur = async (no) => {
      for (let i = 0; i < 14; i++) {
        await fm.fotoUretimTuru(e2, Date.now(), null);
        await okanOnaylar(fm, e2, k.d1);
        const u = await k.d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
        if (u && (u.asama === "onarim-bekliyor" || u.asama === "elle")) { break; }
      }
      return k.d1.prepare("SELECT asama, sebep, build_gorev FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    };
    const sipKredi = async (no) => k.d1.prepare("SELECT COALESCE(SUM(kredi), 0) AS n, COUNT(*) AS c FROM foto_kredi WHERE siparis_no = ?")
      .bind(no).first();
    const b7 = rnBuildSay();
    const s7 = await siparis(o1.is, 100, "Gri");
    const u7 = s7 ? await zincirSur(s7) : null;
    const b7d = rnBuildSay() - b7, sb7 = P.sonBuild;
    const b8 = rnBuildSay();
    const s8 = await siparis(o2.is, 100, "Gri");
    const u8 = s8 ? await zincirSur(s8) : null;
    const b8d = rnBuildSay() - b8;
    const kr7 = await sipKredi(s7), kr8 = await sipKredi(s8);
    const r7 = await satir(o1.is);
    // Figür build'i ölçüsüzdür (plaket ölçü kapısı gri satırı ZATEN eler): gri görev figür siparişinde de build SAYILMAZ.
    const onbFigur = await fm.onizlemeBuildi(e2, { is_no: o1.is, tur: "figur", olcu_mm: 100 });
    const onbPlaket = await fm.onizlemeBuildi(e2, { is_no: o1.is, tur: "plaket", olcu_mm: 0 });
    iz.GR7 = { s7, u7, b7d, s8, u8, b8d, kr7, kr8, inp: sb7 && sb7.input_task_id, gorev1, gri: r7 && r7.build_gorev, onbFigur, onbPlaket };
    s.GR7 = !!s7 && !!s8 && !!u7 && !!u8 && u7.asama === u8.asama && b7d === 1 && b8d === 1 && !!sb7 &&
      sb7.input_task_id === gorev1 && !u7.build_gorev.startsWith("gri:") && !!r7 && u7.build_gorev.split("~")[0] !== r7.build_gorev &&
      !!kr7 && !!kr8 && kr7.n === kr8.n && kr7.c === kr8.c && kr7.n > 0 && onbFigur === "" && onbPlaket === "";

    // GR9: 3 gün temizliği gri görseli (+ eski yol GLB + renk çizimleri) önizlemeyle BİRLİKTE siler (taze iş kalır).
    const eski = "e".repeat(32), eskiIso = new Date(Date.now() - 100 * 3600 * 1000).toISOString();
    await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'g', ?)")
      .bind(eski, eskiIso, eskiIso).run();
    const EKLER = ["-gri.png", "-model.glb", "-Beyaz.png", "-Gri.png", ".png"];
    for (const a of EKLER) { await r2b.put("foto-onizleme/" + eski + a, PNG, {}); }
    await fm.fotoUretimTuru(envKur(k.d1, r2b, { URETIM_API_ANAHTAR: "" }), Date.now(), null);
    iz.GR9 = EKLER.map((a) => r2b.m.has("foto-onizleme/" + eski + a));
    s.GR9 = iz.GR9.every((x) => x === false) && r2b.m.has("foto-onizleme/" + o1.is + "-gri.png");

    // GR10 (cron): müşteri ayrıldı — başlamış gri görevini cron yoklar (görsel iner, kredi deftere; YENİ çağrı yok) ·
    // eski yol 'build' satırı: kredi 'build' deftere + 'build-bitti' (GLB inmez, Mac kuyruğu 0) · ④'te eski satır 'yok'.
    const g10 = griPostSay(), b10 = rnBuildSay();
    const o6 = await onizle({ renk: "Gri" });
    await durum(o6.is); await durum(o6.is);
    const r10a = await satir(o6.is);
    await k.d1.prepare("UPDATE foto_renk_onizleme SET asama = 'build', build_gorev = 'gorev-eski-build-aaaa', build_olcu = 100," +
      " hata = '' WHERE is_no = ?").bind(o5.is).run();
    for (let i = 0; i < 3; i++) {
      await k.d1.prepare("UPDATE foto_renk_onizleme SET son_kontrol = 0").run();
      await fm.fotoUretimTuru(e2, Date.now(), null);
    }
    const r10b = await satir(o6.is), r10e = await satir(o5.is);
    const kr10 = await kredi(o6.is, "gri"), kre = await kredi(o5.is, "build");
    const dE = await durum(o5.is);
    iz.GR10 = { r10a, r10b, r10e, kr10, kre, post: griPostSay() - g10, b: rnBuildSay() - b10, dE,
      gri: r2b.m.has("foto-onizleme/" + o6.is + "-gri.png"), glb: r2b.m.has("foto-onizleme/" + o5.is + "-model.glb"),
      render: await renderBekleyen() };
    s.GR10 = !!r10a && r10a.asama === "gri" && !!r10b && r10b.asama === "gri-hazir" && iz.GR10.gri &&
      kr10.length === 1 && kr10[0].kredi === 5 && iz.GR10.post === 1 && iz.GR10.b === 0 &&
      !!r10e && r10e.asama === "build-bitti" && kre.length === 1 && kre[0].kredi === 30 && iz.GR10.glb === false &&
      iz.GR10.render === 0 && dE.asama === "hazir" && dE.onizleme_renk_durum === "yok" && !("onizleme_renk_url" in dE);

    // GR13: eski yolun GERÇEK build'i (o5, 100 mm) siparişte YENİDEN SATIN ALINMAZ (POST build 0, zincir başı aynı
    // görev, kredi 'build' tek satır) — gri satırdan farklı olarak.
    const b13 = rnBuildSay();
    const s13 = await siparis(o5.is, 100, "Beyaz");
    const u13 = s13 ? await zincirSur(s13) : null;
    const kr13 = await k.d1.prepare("SELECT COUNT(*) AS n FROM foto_kredi WHERE adim = 'build' AND gorev = 'gorev-eski-build-aaaa'").first();
    iz.GR13 = { s13, u13, b: rnBuildSay() - b13, kr13 };
    s.GR13 = !!u13 && iz.GR13.b === 0 && u13.build_gorev.split("~")[0] === "gorev-eski-build-aaaa" && kr13.n === 1;

    // GR11: gri görevi DÜŞTÜ -> 'basarisiz' gri-basarisiz · ④ 'yok' · kredi deftere · renk değişimi YENİDEN DENEMEZ.
    // Görselsiz bitti (alfa yok) -> 'basarisiz' gri-gorsel-yok (sonsuz yoklama YOK). Çağrı toplam 2 (iş başına 1).
    P.griSonuc = "FAILED";
    const g11 = griPostSay();
    const o7 = await onizle({ renk: "Beyaz" });
    const d11a = await hazirla(o7.is);
    const r11a = await satir(o7.is);
    await renkPost(o7.is, "Siyah");
    const d11b = await durum(o7.is);
    const kr11 = await kredi(o7.is, "gri");
    P.griSonuc = "SUCCEEDED"; P.griAlfaYok = true;
    const o8 = await onizle({ renk: "Gri" });
    const d11c = await hazirla(o8.is);
    const r11c = await satir(o8.is);
    P.griAlfaYok = false;
    iz.GR11 = { d11a, r11a, d11b, kr11, d11c, r11c, post: griPostSay() - g11 };
    s.GR11 = d11a.asama === "hazir" && d11a.onizleme_renk_durum === "yok" && !!r11a && r11a.asama === "basarisiz" &&
      r11a.hata === "gri-basarisiz" && d11b.onizleme_renk_durum === "yok" && d11b.onizleme_renk === "Siyah" && kr11.length === 1 &&
      d11c.onizleme_renk_durum === "yok" && !!r11c && r11c.asama === "basarisiz" && r11c.hata === "gri-gorsel-yok" &&
      iz.GR11.post === 2;
  } finally { P.griSonuc = "SUCCEEDED"; P.griAlfaYok = false; VERI.ornekSayisi = asilOrnek; k.kapat(); }
  return { s, iz };
}
// RN11: tablo YOK (göç uygulanmadı; model secret'i VAR) -> fail-closed eski davranış: tek renk isteği 200, yanıtta renk
// alanı 0, image-to-3d 0, build 0, /foto/renk 503 kapali, panel kurulu:false.
async function rnTablosuz(fm) {
  const asilOrnek = VERI.ornekSayisi;
  VERI.ornekSayisi = () => 1;
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur(), GRI_ENV);
  try {
    await k.d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
    await k.d1.prepare("DROP TABLE foto_renk_onizleme").run();
    const cag = async (yol, govde) => fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, {
      method: govde ? "POST" : "GET", headers: { "CF-Connecting-IP": "10.78.0.1", ...(govde ? { "Content-Type": "application/json" } : {}) },
      body: govde ? JSON.stringify(govde) : undefined }), e2, new URL("https://pruvo3d.com/api/shop" + yol), yol.split("?")[0], null);
    const b0 = rnBuildSay(), g0 = griPostSay();
    const o = await (await cag("/foto/onizleme", onizlemeGovde({ renk: "Beyaz" }))).json();
    let d = null;
    for (let i = 0; i < 4; i++) {
      await k.d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(o.is).run();
      d = await (await cag("/foto/durum?is=" + o.is)).json();
    }
    const rp = await cag("/foto/renk", { is: o.is, renk: "Gri" });
    const oz = await (await fm.panelFotoOzet(e2, Date.now())).json();
    const b = rnBuildSay() - b0, g = griPostSay() - g0;
    return { ok: !!o.is && d.asama === "hazir" && !("onizleme_renk" in d) && b === 0 && g === 0 && rp.status === 503 &&
      oz.renk_onizleme && oz.renk_onizleme.kurulu === false, iz: { d, b, g, rp: rp.status, oz: oz.renk_onizleme } };
  } finally { VERI.ornekSayisi = asilOrnek; k.kapat(); }
}
// RN12: ÜRETEÇ TÜRÜ (büst · yapboz · anahtarlık–yazı; Okan 14 Eki 03:5x "tüm 6 modülde"): koşucu önizleme modelini
// seçilen renk(ler)de çizdiyse (<dizin>/renk.png) /durum aynı veri sözleşmesi (onizleme_renk "" · hazir · gorunum=renk ·
// sağlayıcı/üreteç görseli alternatif) + görsel 200; çizim yoksa alan 0; sağlayıcı işinde gorunum=renk 404.
async function rnUretec(fm) {
  const k = koprukur(); await k.hazir;
  const r2b = r2Kur();
  const e2 = envKur(k.d1, r2b);
  try {
    const iso = new Date().toISOString(), A = "a1".repeat(16), B = "b1".repeat(16), C = "c1".repeat(16);
    for (const [no, tur] of [[A, "bust"], [B, "bust"], [C, "plaket"]]) {
      await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, ?, 120, 'z', ?, ?, 'g', ?)")
        .bind(no, tur, iso, tur === "plaket" ? "hazir" : "onizleme-hazir", iso).run();
    }
    await r2b.put("foto-uretec-onizleme/" + A + "/renk.png", PNG, { httpMetadata: { contentType: "image/png" } });
    await r2b.put("foto-uretec-onizleme/" + A + "/onizleme.png", PNG, {});
    const cag = async (yol) => fm.fotoUclari(new Request("https://pruvo3d.com/api/shop" + yol, { method: "GET",
      headers: { "CF-Connecting-IP": "10.79.0.1" } }), e2, new URL("https://pruvo3d.com/api/shop" + yol), yol.split("?")[0], null);
    const da = await (await cag("/foto/durum?is=" + A)).json(), db = await (await cag("/foto/durum?is=" + B)).json();
    const ga = await cag("/foto/gorsel?is=" + A + "&gorunum=renk"), gc = await cag("/foto/gorsel?is=" + C + "&gorunum=renk");
    const iz = { da, db, ga: ga.status, gc: gc.status };
    return { ok: da.asama === "hazir" && da.onizleme_renk === "" && da.onizleme_renk_durum === "hazir" &&
      da.onizleme_renk_url === "/api/shop/foto/gorsel?is=" + A + "&gorunum=renk" &&
      da.onizleme_saglayici_url === "/api/shop/foto/gorsel?is=" + A && db.asama === "hazir" && !("onizleme_renk_durum" in db) &&
      ga.status === 200 && gc.status === 404, iz };
  } finally { k.kapat(); }
}
console.log("RN) ④ TEK RENK ÖNİZLEMESİ — gri model görseli (dokusuz, 5 kr), Renkli AYNEN, renk değişimi çağrısız, secret/kalıp kapısı, tavan, sipariş build'i kendisi kurar (Okan 14 Eki 12:58)");
const GR_ADLAR = {
  GR1: "GR1 tek renk -> prototip hazır olunca TAM 1 image-to-3d POST · gövde sabit (should_texture false · enable_pbr false · alpha_thumbnail · glb · model ortamdan · texture_prompt YOK · giriş = konsept data URI) · build 0",
  GR2: "GR2 görev bitti -> R2 <is>-gri.png · durum hazir + gorunum=gri url + onizleme_renk_gorunum gri + sağlayıcı url · görsel 200 · kredi 'gri' 5 · çağrı hâlâ 1 · Mac kuyruğu 0 · GLB yok · ?renk= 404",
  GR8: "GR8 panel foto-ozet: son 24 sa 1 çağrı · kredi tahmini 11 (5 gri + 6 prototip) · tavan 30 · gri açık · build alanı yok · secret'siz ortamda gri_acik false",
  GR3: "GR3 Renkli (renk alanı yok) -> satır 0 · image-to-3d 0 · build 0 · yanıtta renk alanı 0 · prototip gövdesi tek renkle AYNI",
  GR4: "GR4 renk değişimi Beyaz->Siyah->Gri -> YENİ ÇAĞRI 0 · aynı gri görsel · renk adı değişir · /foto/renk Renkli 400 · bilinmeyen iş 404",
  GR5: "GR5 model secret yok / kalıp dışı (abcdef-6 = 30 kr · büyük harf · ek · kısa · -5-lite) -> image-to-3d 0 · build 0 · satır 0 · ④ eski (renk alanı 0) · /foto/renk 503",
  GR6: "GR6 tavan dolu -> image-to-3d 0 · asama 'tavan' · 'yok' · Okan'a E-POSTA 1 (tekrar YOK) · metin ~11 kredi (6 prototip + 5 gri model)",
  GR7: "GR7 sipariş -> gri önizleme build DEĞİL: zincir build'i kendisi kurar (POST build 1, input = aynı prototip) · sipariş kredisi = Renkli önizlemeli siparişle AYNI",
  GR9: "GR9 3 gün temizliği gri görseli (+ eski GLB + renk çizimleri) önizlemeyle birlikte siler (taze iş kalır)",
  GR10: "GR10 cron: müşteri ayrılınca gri görevi yoklanır (görsel + kredi 'gri', yeni çağrı 0) · eski 'build' satırı kredi 'build' + build-bitti (GLB yok, Mac kuyruğu 0) · ④ 'yok'",
  GR13: "GR13 eski yolun gerçek build'i siparişte YENİDEN SATIN ALINMAZ (POST build 0, zincir başı aynı görev, kredi 'build' tek satır)",
  GR11: "GR11 gri DÜŞTÜ -> basarisiz + 'yok' + kredi deftere · renk değişimi yeniden denemez · görselsiz bitti -> basarisiz gri-gorsel-yok · çağrı iş başına 1",
};
{
  const { s, iz } = await grSunucu(foto);
  for (const a of Object.keys(GR_ADLAR)) { ol(GR_ADLAR[a], s[a] === true, JSON.stringify(iz[a]).slice(0, 900)); }
  const t = await rnTablosuz(foto);
  ol("RN11 tablo YOK (göç öncesi, secret VAR) -> eski davranış: renk alanı 0 · image-to-3d 0 · build 0 · /foto/renk 503 · panel kurulu:false", t.ok, JSON.stringify(t.iz));
  const u12 = await rnUretec(foto);
  ol("RN12 üreteç türü renk.png -> /durum onizleme_renk_durum hazir + gorunum=renk url + alternatif · görsel 200 · çizimsiz alan 0 · plaket gorunum=renk 404",
     u12.ok, JSON.stringify(u12.iz).slice(0, 700));
  // MUTANTLAR (gecici foto.js kopyasi; calisma agaci DEGISMEZ): her biri TAM OLARAK beklenen vakayi KIRMIZI yakar.
  const GR_MUT = [
    ["M-GR-DOKU gri gövdede doku AÇIK (should_texture true)",
     "export const GRI_GOVDE = Object.freeze({ should_texture: false,", "export const GRI_GOVDE = Object.freeze({ should_texture: true,", ["GR1"]],
    ["M-GR-KALIP model kalıbı gevşek (tam sürüm -6 = 30 kr da kabul)",
     "const GRI_MODEL_KALIBI = /^[a-z]{3,12}-6-lite$/;", "const GRI_MODEL_KALIBI = /^[a-z]{3,12}-6(-lite)?$/;", ["GR5"]],
    ["M-GR-RENKLI Renkli önizlemede de gri çağrı açılır",
     "  if (g.renk !== undefined && renkOnizlemeIsi({ tur: tur.kod, cesit, ziyaretci }) && griModel(env)) {\n    try { await renkIste(env, isNo, g.renk, simdi); }",
     "  if (renkOnizlemeIsi({ tur: tur.kod, cesit, ziyaretci }) && griModel(env)) {\n    try { await renkIste(env, isNo, g.renk || \"Beyaz\", simdi); }",
     ["GR3"]],
    ["M-GR-RENK-DEGISIM renk değişiminde yeniden gri çağrı",
     "  const yeni = s.asama === \"tavan\" ? \"bekliyor\" : s.asama;", "  const yeni = \"bekliyor\";", ["GR4", "GR11"]],
    ["M-GR-ONB sipariş gri görevini build sanar (zincir build kurmaz)",
     "!s.build_gorev || griGorevi(s.build_gorev) ||", "!s.build_gorev ||", ["GR7"]],
    ["M-GR-IKINCI-BUILD sipariş eski yolun build'ini yeniden satın alır",
     "    if (onb) { return asamaYaz(env, u, \"build\", { build_gorev: onb }, simdi); }\n", "", ["GR13"]],
    ["M-GR-TAVAN tavan kontrolü kalkar", "  if (sayi >= tavan) {\n", "  if (false) {\n", ["GR6"]],
    ["M-GR-K0 KONTROL (yorum)", "/** Gri model gorselinin R2 anahtari", "/**  Gri model gorselinin R2 anahtari", []],
  ];
  for (const [ad, capa, yerine, olmeli] of GR_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa.slice(0, 80)); continue; }
    const m = (await grSunucu(fm)).s;
    const kir = Object.keys(GR_ADLAR).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli.slice().sort()), JSON.stringify(kir));
  }
}

// ---- KR) KREDİ 11 (Okan 14 Eki 12:58): tek renk önizleme = 6 prototip + 5 gri model; panel tahmini n x 11.
async function krSenaryo(fm) {
  const k = koprukur(); await k.hazir;
  const e2 = envKur(k.d1, r2Kur(), GRI_ENV);
  try {
    const oku = async () => (await (await fm.panelFotoOzet(e2, Date.now())).json()).renk_onizleme;
    const o0 = await oku();
    const t = new Date().toISOString();
    for (const [no, renk] of [["1", "Siyah"], ["2", "Beyaz"], ["3", "Gri"]]) {
      await k.d1.prepare("INSERT INTO foto_renk_onizleme (is_no, renk, asama, build_gorev, build_olcu, tarih, son_kontrol, hata, guncel)" +
        " VALUES (?, ?, 'gri-hazir', ?, 0, ?, 0, '', 0)").bind(no.repeat(32), renk, "gri:gorev-kr-" + no, t).run();
    }
    const o3 = await oku();
    return { KR0: o0.kurulu === true && o0.son_24s_gri === 0 && o0.kredi_tahmini === 0 && o0.kredi_gri === 0 && o0.kredi_prototip === 0,
             KR3: o3.son_24s_gri === 3 && o3.kredi_tahmini === 33 && o3.kredi_gri === 15 && o3.kredi_prototip === 18 &&
               o3.tavan === 30,
             iz: { o0, o3 } };
  } finally { k.kapat(); }
}
{
  const kr = await krSenaryo(foto);
  ol("KR0 panel: n=0 gri çağrı -> kredi tahmini 0 (gri 0 + prototip 0)", kr.KR0, JSON.stringify(kr.iz.o0));
  ol("KR3 panel: n=3 -> kredi tahmini 33 (gri 15 + prototip 18) · tavan 30 DEĞİŞMEZ", kr.KR3, JSON.stringify(kr.iz.o3));
  ol("KR-SABIT RENK_ONIZLEME_KREDI_TAHMINI 11 = 6 prototip + 5 gri · build sabiti YOK · tavan 30", foto.RENK_ONIZLEME_KREDI_TAHMINI === 11 &&
     foto.RENK_PROTOTIP_KREDI_TAHMINI === 6 && foto.RENK_GRI_KREDI_TAHMINI === 5 && foto.RENK_BUILD_KREDI_TAHMINI === undefined &&
     foto.RENK_ONIZLEME_TAVAN_VARSAYILAN === 30,
     [foto.RENK_ONIZLEME_KREDI_TAHMINI, foto.RENK_PROTOTIP_KREDI_TAHMINI, foto.RENK_GRI_KREDI_TAHMINI, foto.RENK_BUILD_KREDI_TAHMINI].join(","));
  const KR_MUT = [
    ["M-KR-11-6 önizleme kredisi 11 -> 6 (gri payı düşer)",
     "export const RENK_ONIZLEME_KREDI_TAHMINI = RENK_PROTOTIP_KREDI_TAHMINI + RENK_GRI_KREDI_TAHMINI;",
     "export const RENK_ONIZLEME_KREDI_TAHMINI = RENK_PROTOTIP_KREDI_TAHMINI;", ["KR3"]],
    ["M-KR-K0 KONTROL (yorum)", "/** Tek renk onizlemesi basina toplam kredi tahmini", "/**  Tek renk onizlemesi basina toplam kredi tahmini", []],
  ];
  for (const [ad, capa, yerine, olmeli] of KR_MUT) {
    const fm = await mutantModul(capa, yerine);
    if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa.slice(0, 80)); continue; }
    const m = await krSenaryo(fm);
    const kir = ["KR0", "KR3"].filter((x) => m[x] !== true);
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

// ---- İSTEMCİ (sahte DOM): ④ görseli + cümle + S2 bekleme + renk değişimi + istek gövdesi
const RN_IS = "c".repeat(32), RN_GORSEL = "/api/shop/foto/gorsel?is=" + RN_IS;
const rnHazir = (tur, ek) => ({ asama: "hazir", tur, olcu_mm: 100, gorsel: RN_GORSEL, gecerlilik_bitis: "2099-01-01T00:00:00.000Z", ...(ek || {}) });
function rnOku(e) {
  const d = [...e.bolum.agac()];
  const img = d.filter((n) => n.classList.contains("foto-uretim-onizleme-img"));
  return { src: img.map((n) => n.src), alt: img.map((n) => n.getAttribute("data-onizleme-saglayici-url")),
    altMetin: img.map((n) => n.alt),
    cumle: d.filter((n) => n.tagName === "P" && n.textContent === RN_CUMLE).length,
    // ④ GRİ cümlesi: "Görsel örnektir" ile başlayan HER paragraf (metin birebir ayrıca ölçülür).
    gri: d.filter((n) => n.tagName === "P" && /^Görsel örnektir/.test(n.textContent || "")).map((n) => n.textContent),
    hazirlaniyor: d.filter((n) => n.tagName === "P" && n.textContent === RN_HAZIRLANIYOR).length,
    ust: d.filter((n) => n.tagName === "P" && n.textContent === FR_UST).length,
    sepet: d.filter((n) => n.id === "foto-sip-btn").length,
    renkPost: e.istekler.filter((x) => /\/foto\/renk$/.test(x.u)).map((x) => x.govde) };
}
const rnBekle = async () => { for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); } };
// Fotoğraf pikselleri: ortada kırmızı blok, kenar beyaz (③ fotoğraftan renk çıkarımı Renkli'yi açar).
const rnPiksel = (w, h) => {
  const a = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4, ic = x > w / 4 && x < 3 * w / 4 && y > h / 4 && y < 3 * h / 4;
      a[i] = ic ? 200 : 255; a[i + 1] = ic ? 30 : 255; a[i + 2] = ic ? 30 : 255; a[i + 3] = 255;
    }
  }
  return a;
};
async function rnIstek(kaynak, V, kart, renk) {
  const e = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), null, null,
    { kart, gorselSahte: true, turnstileOto: true, fotoPiksel: rnPiksel, zamanlayici: true });
  const d = () => [...e.bolum.agac()];
  const id = (x) => d().find((n) => n.id === x) || null;
  const dosya = id("foto-dosya");
  if (dosya) { dosya.files = [{ name: "a.jpg", type: "image/jpeg", size: 4096 }]; dosya.tetikle("change"); }
  await rnBekle();
  const hayir = id("foto-uyum-hayir");
  if (hayir && !hayir.hidden) { hayir.tetikle("click"); }
  const ileri = id("foto-ileri");
  if (ileri) { ileri.tetikle("click"); }
  const r = d().find((n) => n.tagName === "INPUT" && n.name === "foto-renk" && n.value === renk);
  if (r) { r.checked = true; r.tetikle("change"); }
  const ileri2 = id("foto-ileri");
  if (ileri2) { ileri2.tetikle("click"); }
  const on = id("foto-aydinlatma-onay");
  if (on) { on.checked = true; on.tetikle("change"); }
  const btn = id("foto-onizle-buton");
  if (btn) { btn.tetikle("click"); }
  await rnBekle();
  const g = e.istekler.filter((x) => /\/foto\/onizleme$/.test(x.u)).map((x) => x.govde);
  return { secildi: !!r, adet: g.length, renk: g.length === 1 ? (Object.prototype.hasOwnProperty.call(g[0], "renk") ? g[0].renk : "ALAN-YOK") : null };
}
async function rnIstemci(kaynak, V) {
  const s = {}, iz = {};
  const kayit = (tur, renk, ek) => ({ is: RN_IS, tur, olcu: 100, renk_secim: renk, malzeme: "PLA", ...(ek || {}) });
  // Sunucunun gri sözleşmesi (foto.js renkYanitAlanlari): gorunum=gri adresi + onizleme_renk_gorunum "gri".
  const GU = RN_GORSEL + "&gorunum=gri";
  const griHazir = (renk, ek) => rnHazir("plaket", { onizleme_renk: renk, onizleme_renk_durum: "hazir", onizleme_renk_url: GU,
    onizleme_renk_gorunum: "gri", onizleme_saglayici_url: RN_GORSEL, ...(ek || {}) });
  // RNE1: tek renk + gri hazır -> img = gri görsel · GRİ cümle BİREBİR "(Beyaz)" · eski renk cümlesi 0 · üst 'Önizleme —'
  // cümlesi YOK · /foto/renk 0 · sepet 1 · hover verisi = sağlayıcı görseli.
  const e1 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayit("plaket", "Beyaz"), griHazir("Beyaz"), { zamanlayici: true });
  iz.RNE1 = rnOku(e1);
  s.RNE1 = JSON.stringify(iz.RNE1.src) === JSON.stringify([GU]) &&
    JSON.stringify(iz.RNE1.gri) === JSON.stringify([GRI_CUMLE("Beyaz")]) && iz.RNE1.gri[0] === "Görsel örnektir — ürün seçtiğiniz tek renkte (Beyaz) üretilir." &&
    iz.RNE1.cumle === 0 && iz.RNE1.ust === 0 && iz.RNE1.renkPost.length === 0 && iz.RNE1.sepet === 1 &&
    JSON.stringify(iz.RNE1.altMetin) === JSON.stringify(["Önizleme — tek renk örnek görsel"]) &&
    JSON.stringify(iz.RNE1.alt) === JSON.stringify([RN_GORSEL]);
  // RNE2: çizim hazırlanıyor -> S2 "Renk önizlemesi hazırlanıyor…" + SAĞLAYICI görseli (boş görsel YOK) · sepet 0 · yoklama.
  const e2 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayit("plaket", "Beyaz"),
    rnHazir("plaket", { onizleme_renk: "Beyaz", onizleme_renk_durum: "hazirlaniyor" }), { zamanlayici: true });
  iz.RNE2 = { ...rnOku(e2), yoklama: e2.yoklamalar.length };
  s.RNE2 = iz.RNE2.hazirlaniyor === 1 && JSON.stringify(iz.RNE2.src) === JSON.stringify([RN_GORSEL]) && iz.RNE2.sepet === 0 &&
    iz.RNE2.cumle === 0 && iz.RNE2.yoklama >= 1 && iz.RNE2.renkPost.length === 0;
  // RNE3: Renkli (önizleme renk alanı yok) -> sağlayıcı görseli AYNEN + üst cümle · RN_CUMLE 0 · /foto/renk 0.
  const e3 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM),
    kayit("plaket", "Renkli", { renkler: ["Kırmızı", "Beyaz"], renk_kaynak: "foto" }), rnHazir("plaket"), { zamanlayici: true });
  iz.RNE3 = rnOku(e3);
  s.RNE3 = JSON.stringify(iz.RNE3.src) === JSON.stringify([RN_GORSEL]) && iz.RNE3.ust === 1 && iz.RNE3.cumle === 0 &&
    iz.RNE3.gri.length === 0 && iz.RNE3.renkPost.length === 0;
  // RNE4: sunucu 'yok' (tavan/hata/gecikme) -> eski davranış: sağlayıcı görseli + üst cümle, RN_CUMLE 0, istek 0.
  const e4 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayit("plaket", "Gri"),
    rnHazir("plaket", { onizleme_renk: "Gri", onizleme_renk_durum: "yok" }), { zamanlayici: true });
  iz.RNE4 = rnOku(e4);
  s.RNE4 = JSON.stringify(iz.RNE4.src) === JSON.stringify([RN_GORSEL]) && iz.RNE4.ust === 1 && iz.RNE4.cumle === 0 &&
    iz.RNE4.gri.length === 0 && iz.RNE4.renkPost.length === 0;
  // ③'e dönüp başka tek renk seç, ④'e gel (RNE5 · RNE9 ortak).
  const renkDegistir = async (e, renk) => {
    const d = () => [...e.bolum.agac()];
    const geri = d().find((n) => n.id === "foto-geri");
    if (geri) { geri.tetikle("click"); }
    const r = d().find((n) => n.tagName === "INPUT" && n.name === "foto-renk" && n.value === renk);
    if (r) { r.checked = true; r.tetikle("change"); }
    const ileri = d().find((n) => n.id === "foto-ileri");
    if (ileri) { ileri.tetikle("click"); }
    await rnBekle();
    return { geri: !!geri, secildi: !!r };
  };
  // RNE5: ④'te Beyaz GRİ görseli varken ③'e dönüp Gri seç, ④'e gel -> AYNI gri görsel + cümlede "(Gri)" ANINDA (bekleme
  // ekranı YOK) · sunucuya /foto/renk {is, Gri} TEK bildirim (arka planda; yanıtı BEKLENMEZ — sahte yanıt bilerek
  // 'hazirlaniyor': kısa yol yanıtı yok sayar, bekleme ekranına düşen sürüm KIRMIZI yanar).
  const e5 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayit("plaket", "Beyaz"), griHazir("Beyaz"),
    { zamanlayici: true, postYanit: rnHazir("plaket", { onizleme_renk: "Gri", onizleme_renk_durum: "hazirlaniyor" }) });
  const k5 = await renkDegistir(e5, "Gri");
  iz.RNE5 = { ...rnOku(e5), ...k5 };
  s.RNE5 = iz.RNE5.renkPost.length === 1 && iz.RNE5.renkPost[0].is === RN_IS && iz.RNE5.renkPost[0].renk === "Gri" &&
    iz.RNE5.hazirlaniyor === 0 && JSON.stringify(iz.RNE5.src) === JSON.stringify([GU]) &&
    JSON.stringify(iz.RNE5.gri) === JSON.stringify([GRI_CUMLE("Gri")]) && iz.RNE5.cumle === 0;
  // RNE9: gri görsel henüz HAZIRLANIRKEN renk değişirse -> /foto/renk {is, Siyah} TEK istek + S2 bekleme (cümle 0).
  const e9 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayit("plaket", "Beyaz"),
    rnHazir("plaket", { onizleme_renk: "Beyaz", onizleme_renk_durum: "hazirlaniyor" }),
    { zamanlayici: true, postYanit: rnHazir("plaket", { onizleme_renk: "Siyah", onizleme_renk_durum: "hazirlaniyor" }) });
  const k9 = await renkDegistir(e9, "Siyah");
  iz.RNE9 = { ...rnOku(e9), ...k9 };
  s.RNE9 = iz.RNE9.renkPost.length === 1 && iz.RNE9.renkPost[0].renk === "Siyah" && iz.RNE9.hazirlaniyor === 1 &&
    iz.RNE9.gri.length === 0 && iz.RNE9.cumle === 0;
  // RNE6: istek gövdesi -> tek renk plaket {renk: Beyaz} · insan figürü {renk: Gri} · Renkli'de alan YOK.
  iz.RNE6 = { beyaz: await rnIstek(kaynak, V, "plaket", "Beyaz"), insan: await rnIstek(kaynak, V, "insan", "Gri"),
    renkli: await rnIstek(kaynak, V, "plaket", "Renkli") };
  s.RNE6 = iz.RNE6.beyaz.adet === 1 && iz.RNE6.beyaz.renk === "Beyaz" && iz.RNE6.insan.renk === "Gri" &&
    iz.RNE6.renkli.secildi && iz.RNE6.renkli.adet === 1 && iz.RNE6.renkli.renk === "ALAN-YOK";
  // RNE7: önizleme Renkli alındı, oturumda tek renk (Siyah) -> /foto/renk TEK kez (sunucu kabul etmezse döngü YOK).
  const e7 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayit("plaket", "Siyah"), rnHazir("plaket"),
    { zamanlayici: true, postYanit: rnHazir("plaket") });
  for (const f of e7.yoklamalar) { f(); }
  await rnBekle();
  iz.RNE7 = rnOku(e7);
  s.RNE7 = iz.RNE7.renkPost.length === 1 && iz.RNE7.renkPost[0].renk === "Siyah" &&
    JSON.stringify(iz.RNE7.src) === JSON.stringify([RN_GORSEL]) && iz.RNE7.cumle === 0 && iz.RNE7.gri.length === 0;
  // RNE8: üreteç türü (anahtarlık–yazı) çizim hazır -> ④ = gorunum=renk çizimi + renk cümlesi · /foto/renk 0 (renk
  // önizlemenin kendi girdisi).
  const UR = RN_GORSEL + "&gorunum=renk";
  const e8 = await ekranKos(kaynak, V, acikGercek(V, V6_TUM), { is: RN_IS, tur: "anahtarlik", cesit: "yazi", olcu: 60 },
    rnHazir("anahtarlik", { olcu_mm: 60, onizleme_renk: "", onizleme_renk_durum: "hazir", onizleme_renk_url: UR,
      onizleme_saglayici_url: RN_GORSEL }), { zamanlayici: true });
  iz.RNE8 = rnOku(e8);
  s.RNE8 = JSON.stringify(iz.RNE8.src) === JSON.stringify([UR]) && iz.RNE8.cumle === 1 && iz.RNE8.renkPost.length === 0 &&
    iz.RNE8.gri.length === 0 && JSON.stringify(iz.RNE8.alt) === JSON.stringify([RN_GORSEL]);
  // === RNH (14 Eki 03:5x): fare/dokunma/klavye ile sağlayıcının renkli görseline geçiş (sade cep 3 kolu) ===
  const nhImg = (e) => [...e.bolum.agac()].find((n) => n.classList.contains("foto-uretim-onizleme-img"));
  const nhIpucu = (e) => [...e.bolum.agac()].filter((n) => n.classList.contains("foto-uretim-renk-ipucu"));
  const nhDinle = (img) => ["contextmenu", "pointerenter", "pointerleave", "pointerdown", "pointerup", "pointercancel", "focus", "blur"]
    .reduce((t, tip) => t + ((img.dinle || {})[tip] || []).length, 0);
  const nhKos = (kaynak, V, kayitArg, durumArg, ek) => ekranKos(kaynak, V, acikGercek(V, V6_TUM), kayitArg, durumArg, Object.assign({ zamanlayici: true }, ek || {}));

  // RNH1: fare pointerenter (mouse) → src = S.gorsel · alt = "Önizleme — fotoğraftaki renkli hâli"; pointerleave →
  // src = renk çizimi · alt = kuruluş alt'ı; sınıf foto-uretim-renk-degis + tabIndex=0 + 8 dinleyici.
  const nh1 = await nhKos(kaynak, V, kayit("plaket", "Beyaz"),
    griHazir("Beyaz"));
  const nh1Img = nhImg(nh1);
  const nh1Alt0 = nh1Img.alt;
  nh1Img.tetikle("pointerenter", { pointerType: "mouse" });
  const nh1Enter = { src: nh1Img.src, alt: nh1Img.alt };
  nh1Img.tetikle("pointerleave");
  const nh1Leave = { src: nh1Img.src, alt: nh1Img.alt };
  iz.RNH = { hasClass: nh1Img.classList.contains("foto-uretim-renk-degis"), tabIndex: nh1Img.tabIndex,
    src0: nh1Img.src, alt0: nh1Alt0, enter: nh1Enter, leave: nh1Leave, dinle: nhDinle(nh1Img),
    ipucu: nhIpucu(nh1).map((n) => n.textContent) };
  iz.RNH1 = iz.RNH;
  s.RNH1 = iz.RNH.hasClass === true && iz.RNH.tabIndex === 0 &&
    iz.RNH.src0 === GU &&
    iz.RNH.enter.src === RN_GORSEL && iz.RNH.enter.alt === "Önizleme — fotoğraftaki renkli hâli" &&
    iz.RNH.leave.src === GU && iz.RNH.leave.alt === iz.RNH.alt0 &&
    iz.RNH.dinle === 8 && iz.RNH.ipucu.length === 1 &&
    iz.RNH.ipucu[0] === "Fotoğraftaki renkli hâlini görmek için görselin üstüne gel ya da basılı tut.";

  // RNH2: dokunmatik/kalem pointerdown (touch) → src = S.gorsel; pointerup → src = renk çizimi;
  // pointercancel → src = renk çizimi. (mouse pointerenter aynı dinleyiciyi ateşler ama pointerType filtresi
  // nedeniyle renkliGoster tetiklenmez — fare için RNH1'e bırakıldı.)
  const nh2 = await nhKos(kaynak, V, kayit("plaket", "Beyaz"),
    griHazir("Beyaz"));
  const nh2Img = nhImg(nh2);
  nh2Img.tetikle("pointerdown", { pointerType: "touch" });
  const nh2Down = { src: nh2Img.src, alt: nh2Img.alt };
  nh2Img.tetikle("pointerup");
  const nh2Up = { src: nh2Img.src, alt: nh2Img.alt };
  nh2Img.tetikle("pointerdown", { pointerType: "pen" });
  const nh2Pen = { src: nh2Img.src, alt: nh2Img.alt };
  nh2Img.tetikle("pointercancel");
  const nh2Cancel = { src: nh2Img.src, alt: nh2Img.alt };
  // mouse pointerdown filtreye takılır — renkliGoster tetiklenmez (görsel cizim adresinde).
  nh2Img.tetikle("pointerdown", { pointerType: "mouse" });
  const nh2Mouse = { src: nh2Img.src, alt: nh2Img.alt };
  iz.RNH2 = { down: nh2Down, up: nh2Up, pen: nh2Pen, cancel: nh2Cancel, mouse: nh2Mouse };
  s.RNH2 = nh2Down.src === RN_GORSEL && nh2Up.src === GU &&
    nh2Pen.src === RN_GORSEL && nh2Cancel.src === GU &&
    nh2Mouse.src === GU;

  // RNH3: focus → src = S.gorsel; blur → src = renk çizimi.
  const nh3 = await nhKos(kaynak, V, kayit("plaket", "Beyaz"),
    griHazir("Beyaz"));
  const nh3Img = nhImg(nh3);
  nh3Img.tetikle("focus");
  const nh3F = { src: nh3Img.src, alt: nh3Img.alt };
  nh3Img.tetikle("blur");
  const nh3B = { src: nh3Img.src, alt: nh3Img.alt };
  iz.RNH3 = { focus: nh3F, blur: nh3B };
  s.RNH3 = nh3F.src === RN_GORSEL && nh3F.alt === "Önizleme — fotoğraftaki renkli hâli" &&
    nh3B.src === GU && nh3B.alt !== "Önizleme — fotoğraftaki renkli hâli";

  // RNH4: S.gorsel boşuken → dinleyici 0, ipucu yok, src = renk çizimi (RN_GORSEL boş, onizleme_saglayici_url YOK).
  const nh4 = await nhKos(kaynak, V, kayit("plaket", "Beyaz"),
    rnHazir("plaket", { gorsel: "", onizleme_renk: "Beyaz", onizleme_renk_durum: "hazir", onizleme_renk_url: GU, onizleme_renk_gorunum: "gri" }));
  const nh4Img = nhImg(nh4);
  iz.RNH4 = { src: nh4Img.src, hasClass: nh4Img.classList.contains("foto-uretim-renk-degis"),
    tabIndex: nh4Img.tabIndex, dinle: nhDinle(nh4Img), ipucu: nhIpucu(nh4).length };
  // S.gorsel boş: listener yok, ipucu yok, sınıf yok, tabIndex atanmadı (sahte DOM'da undefined). Görsel hâlâ
  // renk çizimi (S.renkSunucu.gorsel — server tek renkli çizimi vermiş).
  s.RNH4 = nh4Img.src === GU && nh4Img.classList.contains("foto-uretim-renk-degis") === false &&
    nhDinle(nh4Img) === 0 && nhIpucu(nh4).length === 0;

  // RNH5: Renkli seçili (renkCiz = false) → dinleyici 0, ipucu yok; src = sağlayıcı görseli (RN_GORSEL).
  const nh5 = await nhKos(kaynak, V,
    kayit("plaket", "Renkli", { renkler: ["Kırmızı", "Beyaz"], renk_kaynak: "foto" }), rnHazir("plaket"));
  const nh5Img = nhImg(nh5);
  iz.RNH5 = { src: nh5Img.src, dinle: nhDinle(nh5Img), ipucu: nhIpucu(nh5).length,
    hasClass: nh5Img.classList.contains("foto-uretim-renk-degis") };
  s.RNH5 = nh5Img.src === RN_GORSEL && nhDinle(nh5Img) === 0 && nhIpucu(nh5).length === 0 &&
    nh5Img.classList.contains("foto-uretim-renk-degis") === false;

  // RNH7: üreteç türü (anahtarlık–yazı, fotoğraf YOK) → "fotoğraftaki" ipucu ÇİZİLMEZ · alt metinde boş renk adı yok ·
  // alternatif (üretecin düz görünümü) yine üstüne gelince gelir, alt = "düz görünüm".
  const nh7Img = nhImg(e8);
  const nh7Alt0 = nh7Img.alt;
  nh7Img.tetikle("pointerenter", { pointerType: "mouse" });
  const nh7Enter = { src: nh7Img.src, alt: nh7Img.alt };
  nh7Img.tetikle("pointerleave", { pointerType: "mouse" });
  iz.RNH7 = { ipucu: nhIpucu(e8).length, alt0: nh7Alt0, enter: nh7Enter, src: nh7Img.src };
  s.RNH7 = nhIpucu(e8).length === 0 && nh7Alt0 === "Önizleme — seçilen renklerde çizim" &&
    nh7Enter.src === RN_GORSEL && nh7Enter.alt === "Önizleme — düz görünüm" && nh7Img.src === UR;

  // RNH6: ipucu metni birebir + RENK_CUMLESI birebir + sıra (cümle önce, ipucu sonra; aynı).
  const nh6 = await nhKos(kaynak, V, kayit("plaket", "Beyaz"),
    griHazir("Beyaz"));
  const nh6D = [...nh6.bolum.agac()];
  const nh6CumleP = nh6D.find((n) => n.tagName === "P" && n.textContent === GRI_CUMLE("Beyaz"));
  const nh6IpucuP = nh6D.find((n) => n.classList.contains("foto-uretim-renk-ipucu"));
  iz.RNH6 = { cumleMetni: nh6CumleP && nh6CumleP.textContent, ipucuMetni: nh6IpucuP && nh6IpucuP.textContent,
    cumleOnce: nh6CumleP && nh6IpucuP ? nh6CumleP.parentNode.childNodes.indexOf(nh6CumleP) : -1,
    ipucuSonra: nh6CumleP && nh6IpucuP ? nh6CumleP.parentNode.childNodes.indexOf(nh6IpucuP) : -1 };
  s.RNH6 = nh6CumleP && nh6IpucuP &&
    iz.RNH6.cumleMetni === GRI_CUMLE("Beyaz") && iz.RNH6.ipucuMetni === "Fotoğraftaki renkli hâlini görmek için görselin üstüne gel ya da basılı tut." &&
    nh6CumleP.parentNode.childNodes.indexOf(nh6CumleP) < nh6CumleP.parentNode.childNodes.indexOf(nh6IpucuP);
  // Yukarıdaki "cümle önce, ipucu sonra" DOM kardeş sırasıdır; ek olarak ipucu tag'i <p> olmalı.
  if (s.RNH6 && nh6IpucuP.tagName !== "P") { s.RNH6 = false; iz.RNH6.tagHatasi = nh6IpucuP.tagName; }

  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}
{
  const V = veriYukle(VERI_KAYNAK);
  const s = await rnIstemci(EKRAN_KAYNAK, V);
  const ADLAR = {
    RNE1: "RNE1 tek renk + gri hazır -> ④ görseli = gri görsel · '" + GRI_CUMLE("Beyaz") + "' BİREBİR · eski renk cümlesi 0 · üst cümle 0 · /foto/renk 0",
    RNE2: "RNE2 gri hazırlanıyor -> S2 '" + RN_HAZIRLANIYOR + "' + sağlayıcı görseli (boş görsel yok) · Sepete ekle 0 · yoklama",
    RNE3: "RNE3 Renkli -> sağlayıcı görseli AYNEN + bugünkü cümle · gri cümle 0 · renk cümlesi 0 · /foto/renk 0",
    RNE4: "RNE4 sunucu 'yok' (tavan/hata/gecikme/özellik kapalı) -> eski davranış (sağlayıcı görseli + bugünkü cümle) · gri cümle 0",
    RNE5: "RNE5 gri hazırken ③'e dönüp Gri -> aynı gri görsel + '(Gri)' cümlesi ANINDA (bekleme 0) · /foto/renk {is, Gri} TEK bildirim",
    RNE9: "RNE9 gri hazırlanırken ③'e dönüp Siyah -> /foto/renk {is, Siyah} TEK istek + S2 bekleme · cümle 0",
    RNE6: "RNE6 önizleme gövdesi: tek renk plaket renk=Beyaz · insan renk=Gri · Renkli'de renk alanı YOK",
    RNE7: "RNE7 Renkli alınmış önizleme + oturumda Siyah -> /foto/renk TEK kez, kabul edilmezse eski davranış (döngü yok)",
    RNE8: "RNE8 üreteç türü (anahtarlık–yazı) çizim hazır -> ④ gorunum=renk çizimi + renk cümlesi + alternatif verisi · /foto/renk 0",
    RNH1: "RNH1 fare pointerenter(mouse) → src = S.gorsel · alt = 'fotoğraftaki renkli hâli'; pointerleave → renk çizimi (KIRMIZ); sınıf + tabIndex=0 + 8 dinleyici + 1 ipucu",
    RNH2: "RNH2 dokunmatik/kalem pointerdown → S.gorsel; pointerup · pointercancel → cizim; mouse pointerdown filtreye takılır (dokunmatik akış)",
    RNH3: "RNH3 focus → S.gorsel; blur → cizim",
    RNH4: "RNH4 S.gorsel boş → dinleyici 0 · ipucu yok · sınıf yok · src = renk çizimi",
    RNH5: "RNH5 Renkli seçili (renkCiz=false) → dinleyici 0 · ipucu yok · src = sağlayıcı görseli",
    RNH6: "RNH6 ipucu metni birebir + GRİ cümle birebir + DOM sırası (cümle önce, ipucu sonra)",
    RNH7: "RNH7 üreteç türü (fotoğraf yok) → 'fotoğraftaki' ipucu 0 · alt 'seçilen renklerde çizim' · üstünde düz görünüm → geri",
  };
  for (const a of Object.keys(ADLAR)) { ol(ADLAR[a], s[a] === true, JSON.stringify(s.iz[a]).slice(0, 700)); }
  const RNE_MUT = [
    ["M-RNE-RENKLI Renkli'de de renk istenir", "  function renkHedefi() { return renkOnizlemeKolu() && !renkliMi() ? anaRenk() : \"\"; }",
     "  function renkHedefi() { return renkOnizlemeKolu() ? anaRenk() : \"\"; }", ["RNE3", "RNE6"]],
    ["M-RNE-CIZIM-YOK çizim adresi yok sayılır", "        img.src = S.renkSunucu.gorsel;\n", "        img.src = S.gorsel;\n", ["RNE1", "RNE5", "RNE8", "RNH4"]],
    ["M-RNE-CUMLE görsel altı cümle hiç basılmaz",
     "        S.alan.appendChild(el(\"p\", \"foto-uretim-ayrinti foto-uretim-renk-notu\",\n          griGorunum ? griCumlesi(S.renkSunucu.renk) : RENK_CUMLESI));\n",
     "", ["RNE1", "RNE5", "RNE8", "RNH6"]],
    ["M-RNE-GRI-CUMLE gri cümlesi silindi (eski çizim cümlesi basılır)",
     "          griGorunum ? griCumlesi(S.renkSunucu.renk) : RENK_CUMLESI));", "          RENK_CUMLESI));", ["RNE1", "RNE5", "RNH6"]],
    ["M-RNE-GRI-RENKADI cümlede renk adı sabit (seçilen renk yazılmaz)",
     "  function griCumlesi(renk) { return GRI_CUMLESI.replace(\"{renk}\", renk); }",
     "  function griCumlesi(renk) { return GRI_CUMLESI.replace(\"{renk}\", \"Beyaz\"); }", ["RNE5"]],
    ["M-RNE-GRI-BEKLE gri hazırken renk değişiminde bekleme ekranı + yeni istek",
     "    if (S.renkSunucu && S.renkSunucu.gorunum === \"gri\" && S.renkSunucu.durum === \"hazir\" && S.renkSunucu.gorsel) {",
     "    if (false) {", ["RNE5"]],
    ["M-RNE-K0 KONTROL (aynı gövde)", "  var RENK_URL = \"/api/shop/foto/renk\";\n", "  var RENK_URL = \"/api/shop/foto/renk\";\n", []],
  ];
  for (const [ad, capa, yerine, olmeli] of RNE_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await rnIstemci(EKRAN_KAYNAK.replace(capa, yerine), V);
    const kir = Object.keys(ADLAR).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
  const RNH_MUT = [
    ["M-RNH-LEAVE pointerleave geri döndürmüyor (cizimGoster no-op) -> RNH1+RNH2+RNH3 KIRMIZI (hepsi cizimGoster'ı paylaşır)",
     "var renkDegisCizimGoster = function () { img.src = renkDegisCizim; img.alt = renkDegisAltCizim; };",
     "var renkDegisCizimGoster = function () {};",
     ["RNH1", "RNH2", "RNH3", "RNH7"]],
    ["M-RNH-BOSKEN-DINLE S.gorsel boşken de dinleyici kuruluyor -> RNH4 KIRMIZI",
     "if (renkCiz && S.renkSunucu && S.gorsel) {",
     "if (renkCiz && S.renkSunucu) {",
     ["RNH4"]],
    ["M-RNH-RENKLI-DINLE dinleyiciler renkCiz dışında da kuruluyor -> RNH5 KIRMIZI",
     "if (renkCiz && S.renkSunucu && S.gorsel) {",
     "if (S.gorsel) {",
     ["RNH5"]],
    ["M-RNH-URETEC-IPUCU üreteç kolunda da 'fotoğraftaki' ipucu çiziliyor -> RNH7 KIRMIZI",
     "if (renkDegisFotoKolu) S.alan.appendChild(el(\"p\", \"foto-uretim-ayrinti foto-uretim-renk-ipucu\", RENK_IPUCU));",
     "S.alan.appendChild(el(\"p\", \"foto-uretim-ayrinti foto-uretim-renk-ipucu\", RENK_IPUCU));",
     ["RNH7"]],
    ["M-RNH-K0 KONTROL (yorum)", "  // ④ HOVER ALTERNATİF (Okan 14 Eki 03:5x): fareyle", "  // ④ HOVER ALTERNATİF (Okan 14 Eki 03:5x): fareyle", []],
  ];
  for (const [ad, capa, yerine, olmeli] of RNH_MUT) {
    if (EKRAN_KAYNAK.split(capa).length - 1 !== 1) { ol(ad + " capa bulundu", false, capa); continue; }
    const m = await rnIstemci(EKRAN_KAYNAK.replace(capa, yerine), V);
    const kir = Object.keys(ADLAR).filter((x) => m[x] !== true).sort();
    ol(ad + " -> KIRMIZI tam olarak [" + olmeli.join(",") + "]", JSON.stringify(kir) === JSON.stringify(olmeli), JSON.stringify(kir));
  }
}

console.log(kirmizi ? "\n❌ " + kirmizi + " iddia KIRMIZI" : "\n✅ HEPSI GECTI");
process.exit(kirmizi ? 1 : 0);
