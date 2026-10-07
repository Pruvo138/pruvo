#!/usr/bin/env node
/**
 * PRUVO shop — 2D KONSEPT kabul kapisi (Okan 7 Eki 14:5x: "görsel eklendikten sonra müşteri görselle
 * ilgili nasıl birşey istediğini anlatan not yazabilmeli ve 2d sonuç buna göre çıkmalı").
 *
 *   node shop/test/foto-konsept.mjs
 *
 * PARA + KISISEL VERI sinifi: hata SESSIZ olur (sinir kacarsa kredi yanar, not sizarsa saglayiciya gider).
 * OLCTUGU HUKUMLER (kod: shop/src/foto.js "uc: /foto/konsept"; sabitler manifest VERI.konsept):
 *   K1 AKIS        : foto + not -> saglayicinin gorsel+metin -> gorsel ucu (model manifestten, prompt =
 *                    sabit cerceve + not) -> yoklama -> gorsel OZEL kovada, bizim ucumuzdan sunulur;
 *                    kredi defterine BIR kez
 *   K2 DENEME      : ayni is (oturum) icinde 3 konsept; 4. istek 429 ve saglayiciya GITMEZ
 *   K3 BOT         : jeton yok -> 400 (saglayici 0, dogrulayici 0); jeton red -> 403
 *   K4 ANAHTAR     : tur kapali (foto_acik bos) -> saglayiciya 0 cagri; tablo yok -> 503 + 0 cagri
 *   K5 TAVAN       : gunluk kredi tavani doluysa 429 + 0 cagri; ziyaretci 24 s siniri 429 + 0 cagri
 *   K6 GIRDI       : "Bunu kullan" -> /foto/onizleme {konsept}: 3D isteginin image_url'i KONSEPT gorseli
 *                    (foto degil); konsept is_no'ya baglanir
 *   K7 ORNEK       : musteri konsept-durum/konsept-gorsel ornek konseptini GOSTERMEZ (404); musteri
 *                    onizlemesi ornek konseptini girdi alamaz; panel ornek kolu ziyaretci sinirsiz
 *   K8 KISISEL VERI: notta e-posta / telefon -> 400 ve saglayiciya GITMEDI
 *   K9 SAKLAMA     : 3 gunden eski konsept gorseli silinir (onizleme temizligiyle AYNI kural)
 * MUTANTLAR (foto.js'in GECICI kopyasi; calisma agacina yazim YOK): her biri hedef senaryoyu KIRMIZI
 *   yakar; KM0 (yalniz yorum) hicbirini.
 * NASIL: D1 = GERCEK SQLite (tools/d1-sema.sql, shop/test/ortak/sqlite-koprusu.py). Saglayici, bot
 *   dogrulayici, dosya indirme `globalThis.fetch` sahtesidir; beklenmeyen HER adres hata atar ->
 *   GERCEK AG ISTEGI 0. Sahte saglayicinin cagri kaydi son satirda basilir (KANIT).
 * CIKIS: 0 yesil · 1 kirmizi · 3 OLCULEMEDI. Son satirlar `SAHTE_SAGLAYICI_CAGRI=<n> GERCEK_AG=0` ve `SURVIVOR=<n>`.
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import readline from "node:readline";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const SHOP = path.join(BURASI, "..");

let kirmizi = 0;
const ol = (ad, kosul, ek) => {
  if (kosul) { console.log("  ✅ " + ad); } else { kirmizi++; console.log("  ❌ " + ad + (ek ? " — " + ek : "")); }
};

// ---------------------------------------------------------------- gercek SQLite koprusu

function koprukur() {
  const p = spawn("python3", [path.join(BURASI, "ortak", "sqlite-koprusu.py")], { stdio: ["pipe", "pipe", "inherit"] });
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
const kopruler = [];
async function yeniDb() {
  const k = koprukur();
  kopruler.push(k);
  const ilk = await k.hazir;
  if (!ilk || !ilk.hazir) { console.log("OLCULEMEDI: SQLite koprusu kurulamadi"); process.exit(3); }
  return k.d1;
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

// ---------------------------------------------------------------- sahte ag

const TABAN = "https://saglayici.test/openapi";
const PNG_BAS = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
const FOTO = Uint8Array.from([...PNG_BAS, ...new Array(4096).fill(3)]);
// Konsept gorseli fotodan AYIRT EDILIR (farkli dolgu) -> 3D girdisinin hangisi oldugu baytla olculur.
const KONSEPT_PNG = Uint8Array.from([...PNG_BAS, ...new Array(5000).fill(9)]);
const ONIZ_PNG = Uint8Array.from([...PNG_BAS, ...new Array(64).fill(7)]);
const GORSEL = "data:image/png;base64," + Buffer.from(FOTO).toString("base64");
const KONSEPT_URI = "data:image/png;base64," + Buffer.from(KONSEPT_PNG).toString("base64");

const P = { cagri: [], konseptGovde: [], protoGovde: [], turnstile: "ok", gercekAg: 0, konseptDurum: new Map() };
let sayac = 0;
const yeniId = () => "gorev-" + String(++sayac).padStart(4, "0") + "-kkkk";
const yanit = (v, kod) => new Response(JSON.stringify(v), { status: kod || 200, headers: { "Content-Type": "application/json" } });

globalThis.fetch = async function sahteFetch(hedef, init) {
  const u = String(hedef && hedef.url ? hedef.url : hedef);
  const yontem = (init && init.method) || "GET";
  if (u.startsWith(TABAN)) {
    const yol = u.slice(TABAN.length);
    P.cagri.push(yontem + " " + yol);
    if (yol === "/v1/balance") { return yanit({ balance: 1000 }); }
    let m;
    if (yontem === "POST" && yol === "/v1/image-to-image") {
      const g = JSON.parse(init.body);
      P.konseptGovde.push(g);
      const id = yeniId(); P.konseptDurum.set(id, 0); return yanit({ result: id });
    }
    if ((m = /^\/v1\/image-to-image\/(.+)$/.exec(yol))) {
      const n = (P.konseptDurum.get(m[1]) || 0) + 1; P.konseptDurum.set(m[1], n);
      return n < 2 ? yanit({ id: m[1], status: "IN_PROGRESS", progress: 50 })
        : yanit({ id: m[1], status: "SUCCEEDED", consumed_credits: 3, image_urls: ["https://dosya.test/konsept.png?Expires=1"] });
    }
    if (yontem === "POST" && /^\/tur-onek\/tur-plaket\/v1\/prototype$/.test(yol)) {
      P.protoGovde.push(JSON.parse(init.body));
      return yanit({ result: yeniId() });
    }
    return yanit({ message: "bilinmeyen" }, 404);
  }
  if (u.startsWith("https://dosya.test/konsept.png")) {
    return new Response(KONSEPT_PNG, { headers: { "Content-Type": "image/png", "Content-Length": String(KONSEPT_PNG.length) } });
  }
  if (u.startsWith("https://dosya.test/onizleme.png")) { return new Response(ONIZ_PNG, { headers: { "Content-Type": "image/png" } }); }
  if (u.includes("challenges.cloudflare.com/turnstile")) {
    P.cagri.push("TURNSTILE");
    return yanit(P.turnstile === "ok" ? { success: true, hostname: "pruvo3d.com" } : { success: false });
  }
  P.gercekAg++;
  throw new Error("TESTTE BEKLENMEYEN AG ISTEGI: " + u);
};

const limiter = () => ({ limit: async () => ({ success: true }) });
function envKur(d1, r2, ek) {
  return {
    KATALOG: d1, OZEL_DOSYA: r2, TURNSTILE_SECRET: "ts", YONET_ANAHTAR: "yonet-test-anahtari",
    FOTO_RATE_LIMIT: limiter(),
    URETIM_API_TABAN: TABAN, URETIM_TUR_ONEK: "tur-onek", URETIM_TUR_PLAKET: "tur-plaket", URETIM_API_ANAHTAR: "sahte-anahtar",
    ...(ek || {}),
  };
}

let foto;
try {
  foto = await import(url.pathToFileURL(path.join(SHOP, "src", "foto.js")).href);
} catch (e) {
  console.log("OLCULEMEDI: foto.js yuklenemedi — " + ((e && e.stack) || e));
  process.exit(3);
}
const VERI = globalThis.PRUVO_FOTO;
const KS = VERI.konsept;

/** Bir modulun (fm: foto.js ya da mutanti) uclarina istek. Donus {kod, v}. */
async function cagir(fm, env, yol, o) {
  o = o || {};
  const basliklar = { "CF-Connecting-IP": o.ip || "198.51.100.7" };
  if (o.govde) { basliklar["Content-Type"] = "application/json"; }
  const req = new Request("https://pruvo3d.com/api/shop" + yol, { method: o.govde ? "POST" : "GET",
    headers: basliklar, body: o.govde ? JSON.stringify(o.govde) : undefined });
  const u = new URL(req.url);
  let r;
  try {
  if (o.panel === "konsept") { r = await fm.panelOrnekKonsept(req, env, Date.now(), null); }
  else if (o.panel === "durum") { r = await fm.panelOrnekKonseptDurum(env, u, Date.now()); }
  else if (o.panel === "gorsel") { r = await fm.panelOrnekKonseptGorsel(env, u); }
  else if (o.panel === "onizleme") { r = await fm.panelOrnekOnizleme(req, env, Date.now(), null); }
  else { r = await fm.fotoUclari(req, env, u, yol.split("?")[0], null); }
  } catch (e) {
    return { kod: 500, v: { hata: "istisna: " + ((e && e.message) || e) }, r: null };
  }
  let v = null;
  if ((r.headers.get("Content-Type") || "").includes("json")) { try { v = await r.json(); } catch (e) { v = null; } }
  return { kod: r.status, v, r };
}
const konseptGovde = (ek) => ({ tur: "plaket", gorsel: GORSEL, not: "şapkalı olsun", hak_onay: true,
  aktarim_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton", ...(ek || {}) });
const konseptCagri = () => P.cagri.filter((c) => c === "POST /v1/image-to-image").length;

/** Temiz ortam: yeni SQLite + R2, plaket acilis anahtari ACIK. */
async function ortam(acik) {
  const d1 = await yeniDb();
  if (acik !== false) { await d1.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run(); }
  return envKur(d1, r2Kur());
}
/** Konsepti 'hazir'a getirir (yoklama araligini CAS sutunuyla sifirlayarak). */
async function hazirla(fm, env, no, panel) {
  let d = null;
  for (let i = 0; i < 4; i++) {
    await env.KATALOG.prepare("UPDATE foto_konsept SET son_kontrol = 0 WHERE konsept_no = ?").bind(no).run();
    d = await cagir(fm, env, (panel ? "/x" : "/foto/konsept-durum") + "?konsept=" + no, panel ? { panel: "durum" } : {});
    if (d.v && d.v.asama === "hazir") { break; }
  }
  return d;
}

// ================================================================ SENARYOLAR (fm = modul ya da mutant)

async function senaryolar(fm) {
  const s = {};
  // K1 AKIS + K6 GIRDI
  {
    const env = await ortam();
    const once = konseptCagri();
    const k = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde() });
    const g = P.konseptGovde[P.konseptGovde.length - 1] || {};
    const d = k.v && k.v.konsept ? await hazirla(fm, env, k.v.konsept) : null;
    const gr = d && d.v && d.v.gorsel ? await cagir(fm, env, d.v.gorsel.replace("/api/shop", "")) : null;
    const grBayt = gr && gr.kod === 200 ? new Uint8Array(await gr.r.arrayBuffer()) : null;
    const kredi = await env.KATALOG.prepare("SELECT COUNT(*) AS n, SUM(kredi) AS k FROM foto_kredi WHERE adim = 'konsept'").first();
    s.K1 = k.kod === 200 && konseptCagri() === once + 1 && g.ai_model === KS.model &&
      Array.isArray(g.reference_image_urls) && g.reference_image_urls[0] === GORSEL &&
      g.prompt === foto.konseptPromptu("şapkalı olsun") && g.prompt.startsWith(foto.KONSEPT_CERCEVE) &&
      !!d && d.v.asama === "hazir" && !/dosya\.test/.test(JSON.stringify(d.v)) &&
      !!grBayt && Buffer.from(grBayt).equals(Buffer.from(KONSEPT_PNG)) &&
      env.OZEL_DOSYA.m.has(foto.konseptAnahtari(k.v.konsept)) && kredi.n === 1 && kredi.k === 3;
    s.K1_ayrinti = JSON.stringify({ kod: k.kod, v: k.v, d: d && d.v, kredi });
    // K6: "Bunu kullan" -> 3D onizleme isteginin girdisi konsept (istemci fotoyu da gondermis olsa bile)
    const protoOnce = P.protoGovde.length;
    const o = await cagir(fm, env, "/foto/onizleme", { govde: { tur: "plaket", olcu_mm: 100, konsept: k.v && k.v.konsept,
      gorsel: GORSEL, hak_onay: true, aktarim_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton" } });
    const pg = P.protoGovde[P.protoGovde.length - 1] || {};
    const bag = o.v && o.v.is ? await env.KATALOG.prepare("SELECT is_no FROM foto_konsept WHERE konsept_no = ?").bind(k.v.konsept).first() : null;
    s.K6 = o.kod === 200 && P.protoGovde.length === protoOnce + 1 && pg.image_url === KONSEPT_URI &&
      pg.image_url !== GORSEL && !!bag && bag.is_no === o.v.is;
    s.K6_ayrinti = JSON.stringify({ kod: o.kod, v: o.v, girdiKonsept: pg.image_url === KONSEPT_URI });
    // K6b: hazir olmayan / bilinmeyen konsept -> 400, saglayiciya 0
    const p2 = P.protoGovde.length;
    const x = await cagir(fm, env, "/foto/onizleme", { govde: { tur: "plaket", olcu_mm: 100, konsept: "f".repeat(32),
      hak_onay: true, aktarim_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton" } });
    s.K6b = x.kod === 400 && x.v && x.v.hata === "konsept-gecersiz" && P.protoGovde.length === p2;
  }
  // K2 DENEME: ayni oturumda 3 -> 4. istek 429, saglayiciya gitmez
  {
    const env = await ortam();
    const once = konseptCagri();
    const ilk = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde(), ip: "10.1.0.1" });
    const ot = ilk.v && ilk.v.oturum;
    const iki = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ oturum: ot, not: "çizgi film tarzı" }), ip: "10.1.0.1" });
    const uc = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ oturum: ot, not: "sadece baş" }), ip: "10.1.0.1" });
    const ara = konseptCagri();
    const dort = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ oturum: ot }), ip: "10.1.0.1" });
    s.K2 = ilk.kod === 200 && iki.kod === 200 && uc.kod === 200 && ilk.v.kalan === 2 && uc.v.kalan === 0 &&
      ara === once + 3 && dort.kod === 429 && dort.v && dort.v.hata === "konsept-hakki-bitti" && konseptCagri() === ara;
    s.K2_ayrinti = JSON.stringify([ilk.kod, iki.kod, uc.kod, dort.kod, dort.v]);
  }
  // K3 BOT
  {
    const env = await ortam();
    const once = P.cagri.length;
    const yok = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ turnstile_token: "" }), ip: "10.2.0.1" });
    const yok2 = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ turnstile_token: undefined }), ip: "10.2.0.1" });
    const sifir = P.cagri.length === once;
    P.turnstile = "red";
    const red = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde(), ip: "10.2.0.2" });
    P.turnstile = "ok";
    s.K3 = yok.kod === 400 && yok.v.hata === "bot-jetonu-yok" && yok2.kod === 400 && sifir &&
      red.kod === 403 && !P.cagri.slice(once).includes("POST /v1/image-to-image");
    s.K3_ayrinti = JSON.stringify([yok.kod, yok.v, yok2.kod, red.kod, P.cagri.slice(once)]);
  }
  // K4 ANAHTAR: tur kapali -> 0 cagri; tablo yok -> 503 + 0 cagri
  {
    const env = await ortam(false);
    const once = P.cagri.length;
    const k = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde(), ip: "10.3.0.1" });
    s.K4 = k.kod === 400 && k.v.hata === "tur-kapali" && P.cagri.length === once;
    const env2 = await ortam();
    await env2.KATALOG.prepare("DROP TABLE foto_konsept").run();
    const once2 = P.cagri.length;
    const t = await cagir(fm, env2, "/foto/konsept", { govde: konseptGovde(), ip: "10.3.0.2" });
    s.K4b = t.kod === 503 && P.cagri.length === once2;
    // Yapilandirma eksik (anahtar yok) -> 503 + 0 cagri
    const env3 = await ortam();
    env3.URETIM_API_ANAHTAR = "";
    const once3 = P.cagri.length;
    const a = await cagir(fm, env3, "/foto/konsept", { govde: konseptGovde(), ip: "10.3.0.3" });
    s.K4c = a.kod === 503 && P.cagri.length === once3;
    s.K4_ayrinti = JSON.stringify([k.kod, k.v, t.kod, a.kod]);
  }
  // K5 TAVAN: gunluk kredi tavani (baska ziyaretcilerin denemeleri) + ziyaretci 24 s siniri
  {
    const env = await ortam();
    const dolu = Math.floor(KS.gunluk_kredi_tavani / KS.kredi_tahmini);
    const simdi = new Date().toISOString();
    for (let i = 0; i < dolu; i++) {
      await env.KATALOG.prepare("INSERT INTO foto_konsept (konsept_no, oturum, tur, ziyaretci, tarih, asama) VALUES (?, ?, 'plaket', ?, ?, 'hazir')")
        .bind(String(i).padStart(32, "a"), String(i).padStart(32, "b"), "z" + i, simdi).run();
    }
    // Ornek konseptleri tavani YEMEZ (panel): bir ornek satiri eklense de sayi degismez.
    await env.KATALOG.prepare("INSERT INTO foto_konsept (konsept_no, oturum, tur, ziyaretci, tarih, asama) VALUES (?, ?, 'plaket', 'ornek', ?, 'hazir')")
      .bind("e".repeat(32), "e".repeat(32), simdi).run();
    const once = P.cagri.length;
    const t = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde(), ip: "10.4.0.1" });
    s.K5 = t.kod === 429 && t.v && t.v.hata === "konsept-gunluk-tavan" && P.cagri.length === once;
    // Bir eksik (tavanin altinda) -> gecer: tavan "dolu" sayisinda, bir eksiginde DEGIL.
    await env.KATALOG.prepare("DELETE FROM foto_konsept WHERE konsept_no = ?").bind(String(0).padStart(32, "a")).run();
    const g = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde(), ip: "10.4.0.1" });
    s.K5_sinirda = g.kod === 200;
    // Ziyaretci 24 s siniri (farkli oturumlarla): sinir+1. istek 429, saglayiciya gitmez
    const env2 = await ortam();
    const kodlar = [];
    for (let i = 0; i < KS.sinir_ziyaretci_24s; i++) {
      kodlar.push((await cagir(fm, env2, "/foto/konsept", { govde: konseptGovde(), ip: "10.4.0.2" })).kod);
    }
    const ara = P.cagri.length;
    const fazla = await cagir(fm, env2, "/foto/konsept", { govde: konseptGovde(), ip: "10.4.0.2" });
    const fazlaSifir = P.cagri.length === ara;
    const baska = await cagir(fm, env2, "/foto/konsept", { govde: konseptGovde(), ip: "10.4.0.3" });
    s.K5b = kodlar.every((k) => k === 200) && fazla.kod === 429 && fazla.v.hata === "konsept-siniri" &&
      fazlaSifir && baska.kod === 200;
    s.K5_ayrinti = JSON.stringify({ tavan: [t.kod, t.v], sinirda: g.kod, kodlar, fazla: fazla.kod, baska: baska.kod });
  }
  // K7 ORNEK: musteri ucu ornek konseptini gostermez; panel kolu ziyaretci sinirsiz
  {
    const env = await ortam(false);   // ornek kolu acilis anahtarina bagli DEGIL (panel ornegi acilistan once)
    const kodlar = [];
    let son = null;
    for (let i = 0; i < KS.sinir_ziyaretci_24s + 2; i++) {
      son = await cagir(fm, env, "", { panel: "konsept", govde: { gorsel: GORSEL, not: "çizgi film tarzı" } });
      kodlar.push(son.kod);
    }
    const no = son.v && son.v.konsept;
    await env.KATALOG.prepare("UPDATE foto_konsept SET son_kontrol = 0").run();
    let pd = null;
    for (let i = 0; i < 3; i++) {
      await env.KATALOG.prepare("UPDATE foto_konsept SET son_kontrol = 0 WHERE konsept_no = ?").bind(no).run();
      pd = await cagir(fm, env, "/x?konsept=" + no, { panel: "durum" });
      if (pd.v && pd.v.asama === "hazir") { break; }
    }
    const md = await cagir(fm, env, "/foto/konsept-durum?konsept=" + no);
    const mg = await cagir(fm, env, "/foto/konsept-gorsel?konsept=" + no);
    const pg = await cagir(fm, env, "/x?konsept=" + no, { panel: "gorsel" });
    await env.KATALOG.prepare("INSERT INTO foto_acik (tur, acik, guncel) VALUES ('plaket', 1, 'x')").run();
    const p0 = P.protoGovde.length;
    const mo = await cagir(fm, env, "/foto/onizleme", { govde: { tur: "plaket", olcu_mm: 100, konsept: no,
      hak_onay: true, aktarim_onay: true, onay_surum: VERI.onay_surum, turnstile_token: "jeton" }, ip: "10.5.0.9" });
    const po = await cagir(fm, env, "", { panel: "onizleme", govde: { olcu_mm: 100, konsept: no } });
    const ppg = P.protoGovde[P.protoGovde.length - 1] || {};
    s.K7 = md.kod === 404 && mg.kod === 404 && pd && pd.v.asama === "hazir" && pg.kod === 200;
    s.K7_musteri_onizleme = mo.kod === 400 && P.protoGovde.length === p0 + 1 && po.kod === 200 && ppg.image_url === KONSEPT_URI;
    s.K7_sinirsiz = kodlar.every((k) => k === 200);
    s.K7_ayrinti = JSON.stringify({ kodlar, pd: pd && pd.v, md: md.kod, mg: mg.kod, pg: pg.kod, mo: mo.kod, po: po.kod });
  }
  // K8 KISISEL VERI: notta e-posta / telefon -> 400, saglayiciya gitmez
  {
    const env = await ortam();
    const once = P.cagri.length;
    const govdeOnce = P.konseptGovde.length;
    const e = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ not: "bana yaz okan@ornek.com şapkalı" }), ip: "10.6.0.1" });
    const t = await cagir(fm, env, "/foto/konsept", { govde: konseptGovde({ not: "ara 0 545 138 65 26" }), ip: "10.6.0.1" });
    const gitti = P.konseptGovde.slice(govdeOnce).some((g) => /@|545 138/.test(String(g.prompt)));
    s.K8 = e.kod === 400 && e.v.hata === "not-kisisel-veri" && t.kod === 400 && P.cagri.length === once && !gitti;
    s.K8_ayrinti = JSON.stringify([e.kod, e.v, t.kod, P.cagri.slice(once), gitti]);
  }
  // K9 SAKLAMA: 3 gunden eski konsept gorseli silinir; siparise donen (foto_uretim) KORUNUR
  {
    // Saglayici yapilandirmasi YOKKEN de saklama kurali kosar (cron'un yapilandirma-eksik kolu).
    const env = await ortam();
    env.URETIM_API_ANAHTAR = "";
    const eski = new Date(Date.now() - 73 * 3600 * 1000).toISOString();
    for (const [no, isNo] of [["1".repeat(32), ""], ["2".repeat(32), "9".repeat(32)]]) {
      await env.KATALOG.prepare("INSERT INTO foto_konsept (konsept_no, oturum, tur, ziyaretci, tarih, asama, is_no) VALUES (?, ?, 'plaket', 'z', ?, 'hazir', ?)")
        .bind(no, no, eski, isNo).run();
      await env.OZEL_DOSYA.put(foto.konseptAnahtari(no), KONSEPT_PNG, {});
    }
    await env.KATALOG.prepare("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel) VALUES ('PR-K9', 0, ?, 'plaket', 100, 'build', 'x', 'x')")
      .bind("9".repeat(32)).run();
    await fm.fotoUretimTuru(env, Date.now(), null);
    const a = await env.KATALOG.prepare("SELECT asama FROM foto_konsept WHERE konsept_no = ?").bind("1".repeat(32)).first();
    const b = await env.KATALOG.prepare("SELECT asama FROM foto_konsept WHERE konsept_no = ?").bind("2".repeat(32)).first();
    s.K9 = a.asama === "silindi" && !env.OZEL_DOSYA.m.has(foto.konseptAnahtari("1".repeat(32))) &&
      b.asama === "hazir" && env.OZEL_DOSYA.m.has(foto.konseptAnahtari("2".repeat(32)));
    s.K9_ayrinti = JSON.stringify([a, b]);
  }
  return s;
}

// ================================================================ ANA KOSUM

console.log("K) 2D KONSEPT — gercek modul");
const S = await senaryolar(foto);
ol("K1 akis: model manifestten, prompt = cerceve + not, foto referans, gorsel ozel kovadan bizim ucumuzla, kredi 1 kez", S.K1, S.K1_ayrinti);
ol("K2 ayni is icinde 3 konsept; 4. istek 429 konsept-hakki-bitti ve saglayiciya GITMEZ", S.K2, S.K2_ayrinti);
ol("K3 bot jetonu yok -> 400 (saglayici 0, dogrulayici 0); jeton red -> 403", S.K3, S.K3_ayrinti);
ol("K4 tur kapali (foto_acik bos) -> 400 tur-kapali + saglayiciya 0 cagri", S.K4, S.K4_ayrinti);
ol("K4b foto_konsept tablosu yok -> 503 + saglayiciya 0 cagri (fail-closed)", S.K4b, S.K4_ayrinti);
ol("K4c saglayici anahtari yok -> 503 + 0 cagri", S.K4c, S.K4_ayrinti);
ol("K5 gunluk kredi tavani dolu -> 429 konsept-gunluk-tavan + 0 cagri (ornek satiri saymaz)", S.K5, S.K5_ayrinti);
ol("K5 tavanin bir altinda -> 200 (sinir tam tavanda)", S.K5_sinirda, S.K5_ayrinti);
ol("K5b ziyaretci 24 s siniri: sinir+1. istek 429, baska ziyaretci etkilenmez", S.K5b, S.K5_ayrinti);
ol("K6 'Bunu kullan' -> 3D isteginin girdisi KONSEPT gorseli (foto degil), konsept is_no'ya baglandi", S.K6, S.K6_ayrinti);
ol("K6b bilinmeyen/hazir olmayan konsept -> 400 konsept-gecersiz, saglayiciya 0", S.K6b);
ol("K7 musteri konsept-durum + konsept-gorsel ORNEK konseptini gostermez (404); panel gosterir", S.K7, S.K7_ayrinti);
ol("K7 musteri onizlemesi ornek konseptini girdi alamaz (400); panel ornek onizlemesi alir", S.K7_musteri_onizleme, S.K7_ayrinti);
ol("K7 panel ornek kolu ziyaretci sinirsiz (sinir+2 istek 200)", S.K7_sinirsiz, S.K7_ayrinti);
ol("K8 notta e-posta/telefon -> 400 not-kisisel-veri, saglayiciya GITMEDI", S.K8, S.K8_ayrinti);
ol("K9 3 gunden eski konsept gorseli silinir, siparise donen korunur", S.K9, S.K9_ayrinti);
ol("KT tek kaynak: model + sinirlar manifestte; foto.js'te model adi / sayi sabiti YOK",
   (() => {
     const kaynak = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
     return !kaynak.includes(JSON.stringify(KS.model)) && foto.konseptAyarGecerli() && KS.deneme_is_basi === 3;
   })());

// ================================================================ MUTANTLAR

console.log("MUTANTLAR (gecici kopya; calisma agacina yazilmaz)");
const GECICI = path.join(SHOP, "foto-konsept-test-tmp-" + process.pid);
process.on("exit", () => { fs.rmSync(GECICI, { recursive: true, force: true }); });
const ASIL = fs.readFileSync(path.join(SHOP, "src", "foto.js"), "utf8");
let mutantNo = 0;
async function mutantModul(capa, yerine) {
  if (ASIL.split(capa).length - 1 !== 1) { return null; }
  fs.mkdirSync(GECICI, { recursive: true });
  const dosya = path.join(GECICI, "foto-" + (++mutantNo) + ".js");
  // Gecici kopya shop/<gecici>/ altinda: goreli import (../../foto-uretim-veri.js) src/ ile AYNI derinlikte.
  fs.writeFileSync(dosya, ASIL.replace(capa, yerine));
  return import(url.pathToFileURL(dosya).href);
}
const ANA = ["K1", "K2", "K3", "K4", "K4b", "K4c", "K5", "K5_sinirda", "K5b", "K6", "K6b", "K7", "K7_musteri_onizleme", "K7_sinirsiz", "K8", "K9"];
const MUTANTLAR = [
  ["KM1 is basi deneme siniri silindi", "if (sayi.oturum >= KONSEPT.deneme_is_basi) {", "if (false) {", ["K2"]],
  ["KM2 bot jetonu varlik kontrolu silindi", "if (!ornek && (typeof g.turnstile_token !== \"string\" || !g.turnstile_token.trim())) {", "if (false) {", ["K3"]],
  ["KM3 acilis anahtari atlandi (tur kapaliyken cagri)", "const t = acikTurler(await acikAnahtari(env)).find((x) => x.kod === g.tur && saglayiciTuru(x.kod));",
    "const t = saglayiciTuru(g.tur) ? { kod: g.tur } : null;", ["K4"]],
  ["KM4 gunluk kredi tavani silindi", "if ((sayi.genel + 1) * KONSEPT.kredi_tahmini > KONSEPT.gunluk_kredi_tavani) {", "if (false) {", ["K5"]],
  ["KM5 3D girdisi konsept yerine foto", "const gorsel = g.konsept !== undefined ? await konseptGirdisi(env, g.konsept, tur.kod, false) : gorselCoz(g.gorsel);",
    "const gorsel = gorselCoz(g.gorsel);", ["K6"]],
  ["KM6 musteri durum ucu ornek ayrimi silindi", "if (!k || ornekMi(k) !== !!ornek) { return fjson({ hata: \"bulunamadi\" }, 404); }",
    "if (!k) { return fjson({ hata: \"bulunamadi\" }, 404); }", ["K7"]],
  ["KM7 nota kisisel veri denetimi atlandi", "const nt = uretimNotuDogrula(g.not);\n  if (!nt.ok) { return fjson({ hata: nt.hata }, 400); }\n  if (!ornek) {",
    "const nt = { ok: true, deger: String(g.not || \"\") };\n  if (!ornek) {", ["K8"]],
  ["KM8 ziyaretci 24 s siniri silindi", "if (sayi.kisi >= KONSEPT.sinir_ziyaretci_24s) {", "if (false) {", ["K5b"]],
  ["KM9 konsept temizligi baglanmadi", "return silinen + await konseptTemizle(env, simdi);", "return silinen;", ["K9"]],
  ["KM10 tablo okunamazsa fail-open", "    // Sayilamayan sinir = KAPALI (tablo yok dahil): saglayiciya istek 0.\n    return fjson({ hata: \"kapali\" }, 503);",
    "    sayi = { oturum: 0, oturumOrnek: 0, kisi: 0, genel: 0 };", ["K4b"]],
  ["KM0 KONTROL (yalniz yorum)", "// Ornek konseptleri (panel) musterinin gunluk kredi tavanini YEMEZ.", "// (yorum degisti)", []],
];
let survivor = 0;
for (const [ad, capa, yerine, beklenen] of MUTANTLAR) {
  const fm = await mutantModul(capa, yerine);
  if (!fm) { ol(ad + " capa bulundu", false, "capa kayip/coklu: " + capa.slice(0, 70)); survivor++; continue; }
  const m = await senaryolar(fm);
  const kirmizilar = ANA.filter((k) => m[k] !== true);
  const tuttu = beklenen.length ? beklenen.every((b) => kirmizilar.includes(b)) : kirmizilar.length === 0;
  if (!tuttu) { survivor++; }
  ol(ad + " -> KIRMIZI " + JSON.stringify(kirmizilar) + " (beklenen " + JSON.stringify(beklenen) + ")", tuttu);
}

for (const k of kopruler) { k.kapat(); }
console.log("");
console.log(kirmizi === 0 ? "✅ HEPSI GECTI" : "❌ " + kirmizi + " iddia KIRMIZI");
console.log("SAHTE_SAGLAYICI_CAGRI=" + P.cagri.filter((c) => c !== "TURNSTILE").length + " GERCEK_AG=" + P.gercekAg);
console.log("SURVIVOR=" + survivor);
process.exit(kirmizi === 0 && P.gercekAg === 0 ? 0 : 1);
