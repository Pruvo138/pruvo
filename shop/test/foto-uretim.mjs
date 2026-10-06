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
 *   B FIYAT KABI        : fiyat tablosu bos -> tur sunulmaz; panelden satir yazilinca sunulur
 *   C ONIZLEME          : saglayiciya yalniz ONIZLEME gider (odemeden once tek kredi adimi);
 *                         gorsel bizim ucumuzdan sunulur; kredi defterine BIR kez yazilir
 *   D SINIR             : ziyaretci basi 24 saatte N onizleme; N+1. istek 429 ve saglayiciya
 *                         GITMEZ; baska ziyaretci etkilenmez            (Kapatan: "sinir+1 RED")
 *   E BOT KAPISI        : jeton yok/red/ag hatasi -> 403 (fail-CLOSED), saglayiciya gitmez
 *   F ONAY + GORSEL     : iki onay kutusu + guncel onay surumu sart; sahte gorsel reddedilir
 *   G HAVUZ             : bakiye esigin altinda -> bolum kapanir + Telegram TEK bildirim
 *   H /baslat           : fiyat SUNUCUDA tablodan (+kargo kurali), havale RED, suresi dolmus
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
 *                         "Olcu"; olcu radyolari (S1 + S3) gercekten cizilir (5 Eki olculen hata)
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
/** BAGIMSIZ olcer (foto.js'e DAYANMAZ): zip -> {L (XY uzun kenar), z, item transform, girdiler: ad -> ham sikistirilmis bayt}. */
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
  return { L: Math.max(ust[0] - en[0], ust[1] - en[1]), z: ust[2] - en[2], zTaban: en[2], M, girdiler };
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
      return yanit({ status: "SUCCEEDED", consumed_credits: 0,
        printability: { status: d, error_count: d === "error" ? 1 : 0, warning_count: 0,
                        metrics: { is_watertight: d !== "error", non_manifold_edges: d === "error" ? 12 : 0 } } });
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
    URETIM_API_TABAN: TABAN, URETIM_TUR_ONEK: "tur-onek", URETIM_TUR_PLAKET: "tur-plaket", URETIM_API_ANAHTAR: "sahte-anahtar",
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
const onizlemeGovde = (ek) => ({ tur: "plaket", olcu_mm: 100, gorsel: GORSEL, hak_onay: true,
  aktarim_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton", ...(ek || {}) });
const protoSayisi = () => P.cagri.filter((c) => /^POST .*\/v1\/prototype$/.test(c)).length;

// ================================================================ ANA KOSUM

const kopru = koprukur();
const ilk = await kopru.hazir;
if (!ilk || !ilk.hazir) { console.log("OLCULEMEDI: SQLite koprusu kurulamadi — " + JSON.stringify(ilk)); process.exit(3); }
const d1 = kopru.d1;
const r2 = r2Kur();
const env = envKur(d1, r2);

console.log("A) KAPALI-VARSAYILAN (bugunku veri dosyasi)");
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
  const yolsuz = envKur(d1, r2, { URETIM_TUR_PLAKET: "" });
  ol("A5 plaket tur yolu ortam degiskeni yoksa yapilandirma eksik 'tur-yolu-plaket' + cron ATLAR",
     foto.yapilandirma(yolsuz).eksik.includes("tur-yolu-plaket") &&
     (await foto.fotoUretimTuru(yolsuz, Date.now(), null)).atlandi === "yapilandirma",
     JSON.stringify(foto.yapilandirma(yolsuz).eksik));
}

console.log("P) TUR LISTESI — tek tur PLAKET (Okan 5 Eki 21:4x; anahtarlik/magnet SUNULMAZ)");
{
  ol("P1 veri dosyasinda sunulan tur sayisi 1 ve kodu 'plaket'",
     VERI.turler.length === 1 && VERI.turler[0].kod === "plaket", JSON.stringify(VERI.turler.map((t) => t.kod)));
  ol("P2 sunucu tur tablosu yalniz plaket (anahtarlik/magnet/figur 0)",
     JSON.stringify(Object.keys(foto.TUR_ORTAM)) === '["plaket"]', JSON.stringify(Object.keys(foto.TUR_ORTAM)));
  ol("P3 saglayici tur yolu kodda DEGIL, ortam degiskeninden (deger dizesi 'URETIM_' ile baslar)",
     Object.values(foto.TUR_ORTAM).every((v) => /^URETIM_TUR_[A-Z]+$/.test(v)), JSON.stringify(foto.TUR_ORTAM));
}

// Bolumu ac: onay onayli + ONCE baski fotografi EKSIK bir ornek (gercek ornek SAYILMAZ).
VERI.onay_onayli = true;
VERI.ornekler.push({ tur: "plaket", olcu_mm: 120, foto: "https://media.pruvo3d.com/y-foto.webp",
  onizleme: "https://media.pruvo3d.com/y-oniz.webp", baski: "", not: "baski fotografi YOK" });

console.log("B) FIYAT KABI");
{
  const a = await istek(env, "/foto/acik");
  ol("B1 fiyat tablosu bos -> acik:false (tur sunulmaz)", a.v && a.v.acik === false, JSON.stringify(a.v));
  const y1 = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 100, fiyat_kurus: 34900 }, basliklar: YONET });
  const y2 = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 150, fiyat_kurus: 49900 }, basliklar: YONET });
  const yetkisiz = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 120, fiyat_kurus: 1 } });
  ol("B2 panel fiyat yazar (anahtarli 200, anahtarsiz 404)", y1.kod === 200 && y2.kod === 200 && yetkisiz.kod === 404,
     y1.kod + "/" + y2.kod + "/" + yetkisiz.kod);
  const a1 = await istek(env, "/foto/acik");
  ol("B4 baski fotografi eksik ornek SAYILMAZ -> fiyat olsa da acik:false (gercek ornek 0)",
     a1.v && a1.v.acik === false, JSON.stringify(a1.v));
  VERI.ornekler.push({ tur: "plaket", olcu_mm: 100, foto: "https://media.pruvo3d.com/x-foto.webp",
    onizleme: "https://media.pruvo3d.com/x-oniz.webp", baski: "https://media.pruvo3d.com/x-baski.webp", not: "t" });
  const a2 = await istek(env, "/foto/acik");
  const turler = (a2.v && a2.v.turler) || [];
  ol("B3 acik:true; plaket 100 mm 34900 sunulur", a2.v && a2.v.acik === true &&
     turler.some((t) => t.kod === "plaket" && t.olculer.some((o) => o.mm === 100 && o.fiyat_kurus === 34900)), JSON.stringify(a2.v));
  ol("P4 /foto/acik sunulan tur sayisi 1 (plaket)", turler.length === 1 && turler[0].kod === "plaket",
     JSON.stringify(turler.map((t) => t.kod)));
  const kotu = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 5, fiyat_kurus: 100 }, basliklar: YONET });
  const kotu2 = await istek(env, "/yonet/foto-fiyat", { govde: { tur: "plaket", olcu_mm: 40, fiyat_kurus: 100 }, basliklar: YONET });
  ol("B5 aralik disi olcu (5, 40 mm) fiyat tablosuna YAZILAMAZ", kotu.kod === 400 && kotu2.kod === 400, kotu.kod + "/" + kotu2.kod);
  const red = [];
  for (const t of ["anahtarlik", "magnet", "figur"]) {
    const r = await istek(env, "/yonet/foto-fiyat", { govde: { tur: t, olcu_mm: 100, fiyat_kurus: 100 }, basliklar: YONET });
    if (r.kod === 400 && r.v && r.v.hata === "gecersiz-tur") { red.push(t); }
  }
  ol("P5 panel fiyat: anahtarlik/magnet/figur satiri YAZILAMAZ (3/3 gecersiz-tur)", red.length === 3, red.join(","));
  const tablo = await d1.prepare("SELECT COUNT(*) AS n FROM foto_fiyat WHERE tur <> 'plaket'").first();
  ol("P5b fiyat tablosunda plaket disi satir 0", tablo.n === 0, tablo.n);
  const oz = await istek(env, "/yonet/foto-ozet", { basliklar: YONET });
  ol("P6 panel ozeti sunulan turleri sunucudan verir: yalniz plaket (panel tur listesi elle yazilmaz)",
     oz.v && JSON.stringify(oz.v.sunulan_turler.map((t) => t.kod)) === '["plaket"]' &&
     oz.v.olcu_en_az === foto.OLCU_MM_EN_AZ && oz.v.ayak_plaket_basi === 1, JSON.stringify(oz.v && oz.v.sunulan_turler));
}

console.log("C/F) ONIZLEME + ONAY + GORSEL");
let isNo;
{
  const once = protoSayisi();
  const r1 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ aktarim_onay: false }) });
  const r2_ = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ onay_surum: "eski" }) });
  const r3 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ gorsel: SAHTE_GORSEL }) });
  const r4 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ olcu_mm: 55 }) });
  const r5 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "magnet", olcu_mm: 100 }) });
  const r6 = await istek(env, "/foto/onizleme", { govde: onizlemeGovde({ tur: "anahtarlik", olcu_mm: 100 }) });
  ol("F1 aktarim onayi yok -> 400 onay-yok", r1.kod === 400 && r1.v.hata === "onay-yok", JSON.stringify(r1.v));
  ol("F2 eski onay surumu -> 409", r2_.kod === 409, r2_.kod);
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
  const h = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "havale", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1 }] } });
  ol("H1 havale -> 400 foto-havale-yok", h.kod === 400 && h.v.hata === "foto-havale-yok", JSON.stringify(h.v));
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isNo, olcu_mm: 100, adet: 1, fiyat_kurus: 1 }] } });
  siparisNo = b.v && b.v.no;
  const iy = P.iyzico[P.iyzico.length - 1] || {};
  ol("H2 kart -> 200, iyzico tutari SUNUCU tablosundan (349,00 + 250,00 kargo)",
     b.kod === 200 && P.iyzico.length === once + 1 && iy.price === "599.00", JSON.stringify(b.v) + " price=" + iy.price);
  const s = await d1.prepare("SELECT durum, urunler, tutar_kurus FROM siparisler WHERE siparis_no = ?").bind(siparisNo).first();
  const kalem = s && JSON.parse(s.urunler)[0];
  ol("H3 siparis 'bekliyor', kalem foto_is/tur(plaket)/olcu + foto_ayak 1 tasir", s && s.durum === "bekliyor" && s.tutar_kurus === 34900 &&
     kalem.foto_is === isNo && kalem.foto_tur === "plaket" && kalem.olcu_mm === 100 && kalem.foto_ayak === 1, JSON.stringify(s));
  const eski = await istek(env, "/foto/onizleme", { ip: "198.51.100.77", govde: onizlemeGovde() });
  await d1.prepare("UPDATE foto_isler SET asama = 'hazir', hazir_tarih = '2020-01-01T00:00:00.000Z' WHERE is_no = ?").bind(eski.v.is).run();
  const e = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: eski.v.is, olcu_mm: 100, adet: 1 }] } });
  ol("H4 suresi dolmus onizleme -> 400", e.kod === 400 && e.v.hata === "foto-onizleme-suresi-doldu", JSON.stringify(e.v));
  const yok = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
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
  ol("I2 dort turda zincir 'hazir'", u && u.asama === "hazir", JSON.stringify(u));
  const op = (P.sonBuild && P.sonBuild.options) || {};
  ol("I3 model adimina olcu mm ile gidildi", op.size_mm === 100, JSON.stringify(P.sonBuild));
  ol("I3b plaket geometrisi: kabartma + taban kalinligi sabit, kapali duz sirt (delme yok)",
     op.relief_height_mm === foto.PLAKET_KABARTMA_MM && op.base_thickness_mm === foto.PLAKET_TABAN_MM &&
     op.has_closed_back === true && op.badge_shape === foto.PLAKET_SEKIL, JSON.stringify(op));
  ol("I4 renk adimi 4 renk + bambu", P.sonRenk && P.sonRenk.max_colors === 4 && P.sonRenk.printer_brand === "bambu", JSON.stringify(P.sonRenk));
  const k3 = r2.m.get("foto/" + siparisNo + "/0/model.3mf");
  ol("I5 3MF + GLB BIZIM ozel kovada", k3 && k3.bayt.length === UCMF.length && r2.m.has("foto/" + siparisNo + "/0/model.glb"), [...r2.m.keys()].join(","));
  const kr = await d1.prepare("SELECT COALESCE(SUM(kredi),0) AS t FROM foto_kredi WHERE siparis_no = ? OR (adim = 'onizleme' AND is_no = ?)").bind(siparisNo, isNo).first();
  ol("I6 siparisin kredi kaydi 46 (6 onizleme + 30 model + 0 analiz + 10 renk)", kr.t === 46, kr.t);
  ol("I7 HAZIR bildirimi Telegram'a bir kez", P.telegram.filter((t) => t.includes("HAZIR") && t.includes(siparisNo)).length === 1, P.telegram.length);
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
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: ok.v.is, olcu_mm: 100, adet: 2 }] } });
  siparis2 = b.v && b.v.no;
  await d1.prepare("UPDATE siparisler SET durum = 'odendi' WHERE siparis_no = ?").bind(siparis2).run();
  P.analiz = "error";
  const renkOnce = P.cagri.filter((c) => c === "POST /v1/print/multi-color").length;
  const onarimOnce = P.cagri.filter((c) => c === "POST /v1/print/repair").length;
  for (let i = 0; i < 8; i++) { await cron(); }
  const u = await d1.prepare("SELECT asama, sebep, analiz FROM foto_uretim WHERE siparis_no = ?").bind(siparis2).first();
  ol("J1 analiz kirmizi -> 'elle' + sebep", u && u.asama === "elle" && u.sebep === "analiz-kirmizi", JSON.stringify(u));
  ol("J2 renk adimi KOSMADI", P.cagri.filter((c) => c === "POST /v1/print/multi-color").length === renkOnce, "");
  ol("J3 ELLE bildirimi Telegram'a bir kez", P.telegram.filter((t) => t.includes("ELLE") && t.includes(siparis2)).length === 1, "");
  ol("J5 kirmizida satir basina TEK onarim denendi (tavan)", P.cagri.filter((c) => c === "POST /v1/print/repair").length === onarimOnce + 1, "");
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
  const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: isA, olcu_mm: 100, adet: 1 }] } });
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
  ol("O2b fiyat tablosunda olmayan olcu -> 400 (saglayiciya istek 0)",
     (await istek(env, "/yonet/foto/ornek-onizleme", { govde: ornekGovde({ olcu_mm: 120 }), basliklar: YONET })).kod === 400 &&
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
  const sb = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
    sepet: [{ foto_is: ornekIs, olcu_mm: 100, adet: 1 }] } });
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
  ol("O9 cron ornek satirini 'hazir'a tasir (Build -> Analiz -> 4 renk)", ou && ou.asama === "hazir", JSON.stringify(ou));
  ol("O9b 3MF + GLB ozel kovada (foto/" + ornekNo + "/0/...)",
     r2.m.has("foto/" + ornekNo + "/0/model.3mf") && r2.m.has("foto/" + ornekNo + "/0/model.glb"), "");
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
    addEventListener() {}
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

async function ekranKos(kaynak, fotoVeri, acikYanit, kayit, durumYanit) {
  const { document, bolum } = sahteBelge();
  const kok = {
    document, PRUVO_FOTO: fotoVeri, setTimeout, clearTimeout, setInterval, clearInterval, console,
    PRUVO_SECENEK: { kargoKurus: () => 25000, kurusMetni: (k) => (k / 100).toFixed(2) + " TL" },
    turnstile: { render: () => 1, remove() {}, reset() {} },
    sessionStorage: { getItem: (k) => (k === "pruvo_foto_is" && kayit ? JSON.stringify(kayit) : null), setItem() {}, removeItem() {} },
    location: { href: "https://pruvo3d.com/" },
    fetch: async (u) => ({ ok: true, status: 200, json: async () => (String(u).includes("/foto/durum") ? durumYanit : acikYanit) }),
  };
  kok.window = kok;
  vm.runInNewContext(kaynak, kok, { filename: "foto-uretim.js" });
  for (let i = 0; i < 10; i++) { await new Promise((c) => setTimeout(c, 0)); }
  const dugum = [...bolum.agac()];
  const radyo = (ad) => dugum.filter((n) => n.tagName === "INPUT" && n.name === ad).length;
  const adim2 = dugum.filter((n) => n.classList.contains("foto-uretim-adim") && n.getAttribute("data-no") === "2")
    .map((n) => n.textContent)[0] || "";
  const turGrubu = dugum.filter((n) => n.classList.contains("foto-uretim-form-grup"))[0] || null;
  return { gorunur: !bolum.hidden, tur: radyo("foto-tur"), olcu: radyo("foto-olcu"), olcuS3: radyo("foto-olcu-s3"), adim2,
           turGrubuGizli: !!turGrubu && turGrubu.hidden === true };
}

console.log("R) ONARIM — kirmizi analiz -> onarim -> yeniden doku -> YENIDEN analiz (6 Eki)");
{
  const odenmis = async (ip) => {
    const ok = await istek(env, "/foto/onizleme", { ip, govde: onizlemeGovde() });
    for (let i = 0; i < 2; i++) {
      await d1.prepare("UPDATE foto_isler SET son_kontrol = 0 WHERE is_no = ?").bind(ok.v.is).run();
      await istek(env, "/foto/durum?is=" + ok.v.is);
    }
    const b = await istek(env, "/baslat", { govde: { sozlesme_onay: true, odeme: "kart", musteri, turnstile_token: "j",
      sepet: [{ foto_is: ok.v.is, olcu_mm: 100, adet: 1 }] } });
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
  const u1 = await sur(s1.no, 12, (u) => u.asama === "hazir" || u.asama === "elle");
  ol("R1 kirmizi -> onarim -> doku -> yesil analiz -> renk -> HAZIR",
     u1 && u1.asama === "hazir" && u1.build_gorev.split("~").length === 3, JSON.stringify(u1));
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

  // R2: onarim sonrasi hala kirmizi -> elle, renk KOSMAZ, ikinci onarim YOK.
  P.analiz = "error"; P.analizOnarim = "error";
  const s2 = await odenmis("198.51.100.122");
  const o2 = say("POST /v1/print/repair"), rr2 = say("POST /v1/print/multi-color");
  const u2 = await sur(s2.no, 12, (u) => u.asama === "hazir" || u.asama === "elle");
  ol("R2 onarim sonrasi hala kirmizi -> 'elle' analiz-kirmizi, renk KOSMADI, tek onarim",
     u2 && u2.asama === "elle" && u2.sebep === "analiz-kirmizi" && say("POST /v1/print/multi-color") === rr2 &&
     say("POST /v1/print/repair") === o2 + 1, JSON.stringify(u2));

  // R3: onarim ucu 402 -> kredi-yetersiz (doku/renk KOSMAZ).
  P.analiz = "error"; P.analizOnarim = null; P.onarimKod = 402;
  const s3 = await odenmis("198.51.100.123");
  const d3 = say("POST /v1/retexture"), rr3 = say("POST /v1/print/multi-color");
  const u3 = await sur(s3.no, 12, (u) => u.asama === "hazir" || u.asama === "elle");
  ol("R3 onarim 402 -> 'elle' kredi-yetersiz, doku+renk KOSMADI",
     u3 && u3.asama === "elle" && u3.sebep === "kredi-yetersiz" && say("POST /v1/retexture") === d3 &&
     say("POST /v1/print/multi-color") === rr3, JSON.stringify(u3));
  P.onarimKod = 0;

  // R4: onarim satiri kredi defterine idempotent (ayni onarim gorevi ikinci kez islense de tek satir).
  P.analiz = "error"; P.analizOnarim = "healthy";
  const s4 = await odenmis("198.51.100.124");
  const u4 = await sur(s4.no, 12, (u) => u.asama === "doku" || u.asama === "elle" || u.asama === "hazir");
  const z4 = (u4 && u4.build_gorev || "").split("~");
  await d1.prepare("UPDATE foto_uretim SET asama = 'onarim', build_gorev = ?, guncel = '2000-01-01T00:00:00.000Z' WHERE siparis_no = ?")
    .bind(z4[0] + "~" + z4[1], s4.no).run();
  await cron();
  const k4 = await kredi(s4.no, "onarim");
  ol("R4 kredi defteri onarim satiri idempotent (2 isleme -> 1 satir, 10 kredi)",
     u4 && u4.asama === "doku" && k4.n === 1 && k4.t === 10, JSON.stringify([u4 && u4.asama, k4]));
  await sur(s4.no, 12, (u) => u.asama === "hazir" || u.asama === "elle");
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
  ol("S0 pozitif kontrol: iki turde tur radyo dugmesi 2 + adim 'Tur ve olcu'",
     ekranIki.gorunur && ekranIki.tur === 2 && /Tür ve ölçü/.test(ekranIki.adim2), JSON.stringify(ekranIki));
  ol("S1 bolum cizildi ve olcu adimi var (plaket 2 olcu radyosu) — bos cizim sessiz yesil olmasin",
     ekranTek.gorunur && ekranTek.olcu === 2, JSON.stringify(ekranTek));
  ol("S2 tek turde tur radyo dugmesi 0 + tur grubu gizli", ekranTek.tur === 0 && ekranTek.turGrubuGizli, JSON.stringify(ekranTek));
  ol("S3 tek turde adim cubugu 'Olcu' der ('Tur' kelimesi yok)",
     /^2\. Ölçü$/.test(ekranTek.adim2), ekranTek.adim2);
  const mutTur = EKRAN_KAYNAK.replace(
    "    if (S.acikVeri.turler.length === 1) {\n      S.tur = S.acikVeri.turler[0].kod;\n      S.alanTur.hidden = true;\n      return;\n    }\n", "");
  const mt = mutTur === EKRAN_KAYNAK ? null : await ekranKos(mutTur, VERI, acikTek);
  ol("S-M1 mutant (tek tur dali silindi) -> S2 KIRMIZI (tur radyosu 1)", !!mt && mt.tur === 1, JSON.stringify(mt));
  const mutAdim = EKRAN_KAYNAK.replace('F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"', '"Tür ve ölçü"');
  const ma = mutAdim === EKRAN_KAYNAK ? null : await ekranKos(mutAdim, VERI, acikTek);
  ol("S-M2 mutant (adim etiketi sabit) -> S3 KIRMIZI", !!ma && !/^2\. Ölçü$/.test(ma.adim2), JSON.stringify(ma));
  // 5 Eki 2026 olculen hata: olcu radyosu etikete eklenmiyordu (musteri olcu SECEMIYORDU).
  const mutOlcu = EKRAN_KAYNAK.replace("ek(lbl, inp, \" \");", "ek(lbl, \" \");");
  const mo = mutOlcu === EKRAN_KAYNAK ? null : await ekranKos(mutOlcu, VERI, acikTek);
  ol("S-M3 mutant (olcu radyosu eklenmez) -> S1 KIRMIZI (olcu radyosu 0)", !!mo && mo.olcu === 0, JSON.stringify(mo));
  // Onizleme hazir donusu (S3): olcu degistirme radyolari da cizilmeli (ayni hata orada da vardi).
  const kayit = { is: "b".repeat(32), tur: "plaket", olcu: 100 };
  const hazir = { asama: "hazir", tur: "plaket", olcu_mm: 100, gorsel: "/api/shop/foto/gorsel?is=" + "b".repeat(32) };
  const s3 = await ekranKos(EKRAN_KAYNAK, VERI, acikTek, kayit, hazir);
  ol("S4 onizleme sonrasi (S3) olcu degistirme radyosu 2 (plaket 2 olcu)", s3.olcuS3 === 2, JSON.stringify(s3));
  const son = EKRAN_KAYNAK.lastIndexOf("ek(lbl, inp, \" \");");
  const mutS3 = son > EKRAN_KAYNAK.indexOf("ek(lbl, inp, \" \");")
    ? EKRAN_KAYNAK.slice(0, son) + "ek(lbl, \" \");" + EKRAN_KAYNAK.slice(son + "ek(lbl, inp, \" \");".length) : null;
  const m3 = mutS3 ? await ekranKos(mutS3, VERI, acikTek, kayit, hazir) : null;
  ol("S-M4 mutant (S3 olcu radyosu eklenmez) -> S4 KIRMIZI", !!m3 && m3.olcuS3 === 0, JSON.stringify(m3));
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
      .bind(no, new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 120 }])).run();
    P.ucmf = ucmf; P.analiz = a || "healthy"; P.analizOnarim = ao || null;
    for (let i = 0; i < 10; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
    P.ucmf = null; P.analiz = "healthy"; P.analizOnarim = null;
    const u = await k.d1.prepare("SELECT asama, sebep, analiz FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    const d = r2b.m.get("foto/" + no + "/0/model.3mf");
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
  sonuc.BUYUK = !!b.u && b.u.asama === "hazir" && !!bo && yakin(bo.L, 120) &&
    Math.abs(bo.z - 75 * 120 / 1096.8) < 0.05 && Math.abs(bo.zTaban) < 1e-6 && ayniGirdiler(bo) &&
    b.an.olcek > 0 && b.an.olcek < 1 && yakin(b.an.L_once, 1096.8) && yakin(b.an.L_sonra, 120) &&
    Math.abs(b.an.z_mm - bo.z) < 0.01 && b.an.durum === "healthy";
  const d = await kos("PR-TEST-OLC-D", UCMF_120);
  sonuc.DOGRU = !!d.u && d.u.asama === "hazir" && !!d.d && Buffer.compare(Buffer.from(d.d), Buffer.from(UCMF_120)) === 0 &&
    d.an.olcek === 1 && d.an.L_once === 120 && d.an.L_sonra === 120;
  const z = await kos("PR-TEST-OLC-Z", UCMF_BOZUK);
  sonuc.BOZUK = !!z.u && z.u.asama === "elle" && z.u.sebep === "olcu-tutmadi" && z.d === null && !!z.an.olcu_hata;
  const i2 = await kos("PR-TEST-OLC-I", UCMF_IKI_OGE);
  sonuc.IKIOGE = !!i2.u && i2.u.asama === "elle" && i2.u.sebep === "olcu-tutmadi" && i2.d === null;
  const o = await kos("PR-TEST-OLC-O", UCMF_1094, "error", "healthy");
  const oo = o.d && testOlc(o.d);
  sonuc.ONARIMLI = !!o.u && o.u.asama === "hazir" && !!oo && yakin(oo.L, 120) && yakin(o.an.L_sonra, 120);
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

// ================================================================ MUTANTLAR

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
  await k.d1.prepare("INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES ('plaket', 100, 34900, 'x')").run();
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
  const fs_ = await fm.fotoKalemFiyatla(e2, { foto_is: is, olcu_mm: 100, adet: 1 }, Date.now());
  sonuc.A = !!fs_.satir && fs_.satir.foto_ayak === 1 && /ayak: 1/.test(fs_.satir.parametre_detay);
  await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES ('PR-TEST-MUT', ?, 'odendi', 1, ?)")
    .bind(new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100 }])).run();
  P.analiz = "error";
  for (let i = 0; i < 8; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
  P.analiz = "healthy";
  const u = await k.d1.prepare("SELECT asama FROM foto_uretim WHERE siparis_no = 'PR-TEST-MUT'").first();
  sonuc.J = !!u && u.asama === "elle";
  // T: sunulmayan tur — panel fiyat reddi + kuyruktaki satir saglayiciya gitmeden 'elle'.
  const pf = await fm.panelFotoFiyat(new Request("https://pruvo3d.com/x", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tur: "anahtarlik", olcu_mm: 100, fiyat_kurus: 100 }) }), e2, Date.now());
  await k.d1.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-TEST-T', 0, ?, 'anahtarlik', 100, 'build-baslat', ?, '2000-01-01T00:00:00.000Z')")
    .bind(is, new Date().toISOString()).run();
  await fm.fotoUretimTuru(e2, Date.now(), null);
  const t = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = 'PR-TEST-T'").first();
  sonuc.T = pf.status === 400 && !!t && t.sebep === "tur-kapali";
  k.kapat();
  return sonuc;
}

const MUTANTLAR = [
  ["M1 SINIR", "if (sayi.kisi >= VERI.sinir_ziyaretci_24s) {", "if (false) {", "D"],
  ["M2 BOT", "if (!(await botDogrula(request, env, g.turnstile_token))) {", "if (false) {", "E"],
  ["M3 ANALIZ", "if (p.status !== \"healthy\" && p.status !== \"warning\") {", "if (false) {", "J"],
  ["M4 ANAHTARLIK GERI ACILDI", "export const TUR_ORTAM = { plaket: \"URETIM_TUR_PLAKET\" };",
   "export const TUR_ORTAM = { plaket: \"URETIM_TUR_PLAKET\", anahtarlik: \"URETIM_TUR_PLAKET\" };", "T"],
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
  const e2 = envKur(k.d1, r2Kur());
  const is = "d".repeat(32);
  await k.d1.prepare("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev, hazir_tarih) VALUES (?, 'plaket', 100, 'z', ?, 'hazir', 'gorev-proto-8888', ?)")
    .bind(is, new Date().toISOString(), new Date().toISOString()).run();
  P.protoDurum.set("gorev-proto-8888", 5);
  const sonuc = {};
  const kos = async (no, a, ao) => {
    await k.d1.prepare("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?, ?, 'odendi', 1, ?)")
      .bind(no, new Date().toISOString(), JSON.stringify([{ id: "ozel-foto-plaket", foto_is: is, foto_tur: "plaket", olcu_mm: 100 }])).run();
    P.analiz = a; P.analizOnarim = ao;
    const an = P.cagri.filter((c) => c === "POST /v1/print/analyze").length;
    const rn = P.cagri.filter((c) => c === "POST /v1/print/multi-color").length;
    for (let i = 0; i < 10; i++) { await fm.fotoUretimTuru(e2, Date.now(), null); }
    P.analiz = "healthy"; P.analizOnarim = null;
    const u = await k.d1.prepare("SELECT asama, sebep FROM foto_uretim WHERE siparis_no = ?").bind(no).first();
    return { u, analiz: P.cagri.filter((c) => c === "POST /v1/print/analyze").length - an,
             renk: P.cagri.filter((c) => c === "POST /v1/print/multi-color").length - rn };
  };
  const y = await kos("PR-TEST-ONR-Y", "error", "healthy");
  sonuc.YESIL = !!y.u && y.u.asama === "hazir" && y.renk === 1;
  const r = await kos("PR-TEST-ONR-K", "error", "error");
  sonuc.KIRMIZI = !!r.u && r.u.asama === "elle" && r.u.sebep === "analiz-kirmizi" && r.renk === 0 && r.analiz === 2;
  k.kapat();
  return sonuc;
}

const ONARIM_MUTANTLAR = [
  ["N1 ONARIM SONRASI YENIDEN ANALIZ ATLANDI", "return analizBaslat(env, u, dokuGlb, simdi, telegram);",
   "return renkBaslat(env, u, \"\", simdi, telegram);", "KIRMIZI"],
  ["N2 ONARIM SONRASI KIRMIZIDA RENK KOSTU", "return elleDusur(env, u, \"analiz-kirmizi\", ozet, simdi, telegram);",
   "return renkBaslat(env, u, ozet, simdi, telegram);", "KIRMIZI"],
  ["N3 ONARIM YERINE DOGRUDAN RENK", "if (zincir(u).length >= 2) {", "if (true) { return renkBaslat(env, u, ozet, simdi, telegram); } if (false) {", "KIRMIZI"],
  ["N0 KONTROL", "console.log(\"FOTO_URETIM kuyruga=\"", "console.log(\"FOTO_URETIM  kuyruga=\"", null],
];
for (const [ad, capa, yerine, olmeli] of ONARIM_MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa); continue; }
  const s = await onarimSenaryolar(fm);
  if (olmeli) {
    ol(ad + " -> " + olmeli + " KIRMIZI yanar (digerleri yesil)",
       s[olmeli] === false && Object.keys(s).filter((x) => x !== olmeli).every((x) => s[x] === true), JSON.stringify(s));
  } else {
    ol(ad + " -> hicbir onarim senaryosu kirmizi yanmaz", Object.values(s).length === 2 && Object.values(s).every((x) => x === true), JSON.stringify(s));
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
  await k.d1.prepare("INSERT INTO foto_fiyat (tur, olcu_mm, fiyat_kurus, guncel) VALUES ('plaket', 100, 34900, 'x')").run();
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
  const fk = await fm.fotoKalemFiyatla(e2, { foto_is: orn, olcu_mm: 100, adet: 1 }, Date.now());
  const fkm = await fm.fotoKalemFiyatla(e2, { foto_is: mus, olcu_mm: 100, adet: 1 }, Date.now());
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
   "  if (ornekMi(is)) { return fjson({ hata: \"bulunamadi\" }, 404); }\n  return onizlemeIlerle(",
   "  return onizlemeIlerle(", "DURUM"],
  ["OM3 GORSEL RED DALI SILINDI",
   "  if (ornekMi(is)) { return fjson({ hata: \"bulunamadi\" }, 404); }\n  return onizlemeGorseli(env, isNo);",
   "  return onizlemeGorseli(env, isNo);", "GORSEL"],
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

kopru.kapat();
await Promise.allSettled(ctx.bekleyen);
console.log(kirmizi ? "\n❌ " + kirmizi + " iddia KIRMIZI" : "\n✅ HEPSI GECTI");
process.exit(kirmizi ? 1 : 0);
