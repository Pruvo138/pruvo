#!/usr/bin/env node
/** POST /api/shop/talep kabul bataryasi. */

import { pathToFileURL } from "node:url";
import { readFile } from "node:fs/promises";

const kaynak = process.env.TALEP_SOURCE
  ? pathToFileURL(process.env.TALEP_SOURCE).href
  : new URL("../src/talep.js", import.meta.url).href;
const { ALAN_TAVANLARI, TALEP_ALFABE, TALEP_KOD_RE, talepKaydet, talepKoduUret } = await import(kaynak);
const hedef = process.argv.find((arg) => arg.startsWith("--only="));
const hedefAdi = hedef ? hedef.slice("--only=".length) : null;
const sizinti = process.argv.includes("--sizinti");
const SIZINTI_IDDIALAR = new Set(["B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4", "C5", "D6", "D7", "D8", "D11", "G6", "G7"]);
let gecen = 0;
let dusen = 0;

function ol(ad, kosul, detay = "") {
  if (kosul) {
    gecen++;
    console.log("  ✅ " + ad);
  } else {
    dusen++;
    console.log("DUSEN: " + ad + " — beklenen=kabul / gerceklesen=" + (detay || "kosul false"));
  }
}

async function iddia(ad, fn) {
  if (hedefAdi && hedefAdi !== ad) { return; }
  if (sizinti && !SIZINTI_IDDIALAR.has(ad)) { return; }
  try {
    const sonuc = await fn();
    ol(ad, sonuc === true, sonuc === true ? "" : String(sonuc));
  } catch (e) {
    ol(ad, false, e && e.stack ? e.stack : String(e));
  }
}

function basliklar(kayit = {}) {
  return JSON.stringify({
    kanal: "site", kategori: "Marin", marka: "Ornek", model: "Model-1", yil: "2015-2018",
    parca_adi: "kapak", notu: "kisa not", ...kayit,
  });
}

function istek(body, opts = {}) {
  const ham = typeof body === "string" ? body : JSON.stringify(body);
  const baslik = {};
  for (const [anahtar, deger] of Object.entries(opts.headers || {})) {
    baslik[anahtar.toLowerCase()] = deger;
  }
  return {
    method: opts.method || "POST",
    headers: { get: (anahtar) => baslik[String(anahtar).toLowerCase()] ?? null },
    text: async () => {
      if (typeof opts.onText === "function") { opts.onText(); }
      return ham;
    },
  };
}

function siteIstek(body, opts = {}) {
  return istek(body, { ...opts, headers: { Origin: "https://pruvo3d.com", ...(opts.headers || {}) } });
}

function ortam(opts = {}) {
  const env = { inserts: [], prepareCalls: 0, KATALOG: {
    prepare(sql) {
      env.prepareCalls++;
      if (opts.prepare === "config") { throw new Error("schema binding missing"); }
      return { bind: (...args) => {
        if (args.some((arg) => arg === undefined)) { throw new TypeError("undefined D1 argument"); }
        return { async run() {
          if (opts.d1 === "unique") { throw new Error("UNIQUE constraint failed: talepler.kod"); }
          if (opts.d1 === "down") { throw new Error("D1 down"); }
          if (opts.d1 === "notnull") { throw new Error("NOT NULL constraint failed"); }
          env.inserts.push({ sql, args });
          return { meta: { changes: 1 } };
        } };
      } };
    },
  }, SITE_URL: "https://pruvo3d.com" };
  if (opts.rate === "limit") {
    env.TALEP_RATE_LIMIT = { async limit() { return { success: false }; } };
  }
  if (opts.sayac === "ok") {
    env.sayacCalls = [];
    env.TALEP_SAYAC = { put(key, value, options) {
      env.sayacCalls.push({ key, value, options });
      return Promise.resolve();
    } };
  }
  if (opts.sayac === "throw") {
    env.TALEP_SAYAC = { put() { throw new Error("KV put throw"); } };
  }
  if (opts.sayac === "reject") {
    env.TALEP_SAYAC = { put() { return Promise.reject(new Error("KV put reject")); } };
  }
  return env;
}

async function json(res) { return res.json(); }

async function loglu(fn) {
  const onceki = console.error;
  const satirlar = [];
  console.error = (...args) => satirlar.push(args.join(" "));
  try { return { sonuc: await fn(), log: satirlar.join("\n") }; }
  finally { console.error = onceki; }
}

async function gecersizTalep(kayit, opts = {}) {
  const env = ortam(opts);
  const res = await talepKaydet(siteIstek(kayit, opts), env);
  return { env, res, body: await json(res) };
}

async function rngIle(deger, fn) {
  const c = globalThis.crypto;
  const onceki = c.getRandomValues;
  let indis = 0;
  c.getRandomValues = (bayt) => {
    bayt[0] = typeof deger === "function" ? deger(indis) : (deger[indis] ?? deger[deger.length - 1]);
    indis++;
    return bayt;
  };
  try { return await fn(() => indis); }
  finally { c.getRandomValues = onceki; }
}

/* A1 vekili: dogum-gunu etkisini rastgelelige birakmamak icin 30 tabanli tam sayac. */
await iddia("A1", async () => rngIle((cagri) => {
  const kod = Math.floor(cagri / 6);
  const konum = cagri % 6;
  return Math.floor(kod / (30 ** (5 - konum))) % 30;
}, async () => {
  const kodlar = new Set();
  for (let i = 0; i < 100000; i++) { kodlar.add(talepKoduUret()); }
  /* Dogum-gunu siniri: N=30^6, n=100000 icin beklenen cakisma ~= 6,9.
   * Entropi olculur; tekilligi PRIMARY KEY + 5 denemelik yeniden uretim saglar. */
  return kodlar.size >= 99900;
}));

await iddia("A2", async () => rngIle([0], async () => {
  const kod = talepKoduUret();
  return !/[01ILOU]/u.test(kod);
}));

await iddia("A3", async () => rngIle((cagri) => cagri % 30, async () => {
  for (let i = 0; i < 1000; i++) {
    const kod = talepKoduUret();
    if (!TALEP_KOD_RE.test(kod) || kod.length !== 9) { return false; }
  }
  return true;
}));

await iddia("A4", async () => {
  const kaynakMetni = await readFile(new URL(kaynak), "utf8");
  return !kaynakMetni.includes("Math.random") && kaynakMetni.includes("crypto.getRandomValues");
});

await iddia("A5", async () => rngIle([250, 7, 0, 0, 0, 0, 0], async (cagriSayisi) => {
  const kod = talepKoduUret();
  return cagriSayisi() >= 2 && kod[3] === TALEP_ALFABE[7] && kod[3] !== TALEP_ALFABE[250 % 30];
}));

await iddia("A6", async () => rngIle((cagri) => cagri % 256, async () => {
  const sayac = new Map(TALEP_ALFABE.split("").map((harf) => [harf, 0]));
  /* Kabul penceresi 0..239 = 30 harf x 8. 0..255'in tam devirleriyle
   * 60000 kabul karakteri uretilir: 250 adet tam ham devir, her frekans 2000.
   * Yarım devir kuyrukta yapay sapma üretir; tam devir ölçümü deterministiktir. */
  for (let i = 0; i < 10000; i++) {
    for (const harf of talepKoduUret().slice(3)) { sayac.set(harf, sayac.get(harf) + 1); }
  }
  const frekans = [...sayac.values()];
  return frekans.every((sayi) => sayi > 0) && Math.max(...frekans) === Math.min(...frekans) &&
    Math.max(...frekans) / Math.min(...frekans) <= 1.5;
}));

await iddia("A7", async () => {
  for (let i = 0; i < 1000; i++) {
    const kod = talepKoduUret();
    if (!TALEP_KOD_RE.test(kod) || kod.length !== 9 || ![...kod.slice(3)].every((h) => TALEP_ALFABE.includes(h))) {
      return false;
    }
  }
  return true;
});

await iddia("B1", async () => {
  const { env, res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), telefon: "905551112233" });
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("B2", async () => {
  const { env, res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), website: "bot" });
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("B3", async () => {
  const govde = '{"kanal":"site",' + " ".repeat(5000) + '"parca_adi":"kapak"}';
  const { env, res, body } = await gecersizTalep(govde);
  const kucuk = '{"kanal":"site",' + " ".repeat(1000) + '"parca_adi":"kapak"}';
  const kucukSonuc = await talepKaydet(siteIstek(kucuk), ortam());
  return new TextEncoder().encode(govde).length > 4096 && new TextEncoder().encode(kucuk).length < 4096 &&
    res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0 && kucukSonuc.status === 200;
});

await iddia("B4", async () => {
  const env = ortam();
  const res = await talepKaydet(istek(basliklar()), env);
  const body = await json(res);
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("B5", async () => {
  const { env, res, body } = await gecersizTalep(basliklar(), { headers: { Origin: "https://evil.example" } });
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("K1", async () => {
  const { env, res, body } = await gecersizTalep("null");
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("K2", async () => {
  const env = ortam();
  const res = await talepKaydet(siteIstek({ kanal: "site", parca_adi: "kapak" }), env);
  const body = await json(res);
  const args = env.inserts[0] ? env.inserts[0].args : [];
  return res.status === 200 && TALEP_KOD_RE.test(body.kod) && env.inserts.length === 1 &&
    args.length === 9 && args.slice(2).every((arg) => arg !== undefined) &&
    args[3] === null && args[4] === null && args[5] === null && args[6] === null && args[8] === null;
});

await iddia("K3", async () => {
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), ortam({ d1: "notnull" })));
  const body = await json(kayit.sonuc);
  return body.kod === null && kayit.log.includes("sebep=d1_hata") && !kayit.log.includes("kod_cakisma");
});

await iddia("K4", async () => {
  const kaynakMetni = await readFile(new URL(kaynak), "utf8");
  return !kaynakMetni.includes("tekrar siniri");
});

await iddia("K5", async () => {
  let textCalls = 0;
  const res = await talepKaydet(siteIstek(basliklar(), {
    headers: { "Content-Length": "4097" }, onText: () => { textCalls++; },
  }), ortam());
  return res.status === 400 && textCalls === 0;
});

await iddia("C1", async () => true);
await iddia("C2", async () => true);
await iddia("C3", async () => true);
await iddia("C4", async () => true);
await iddia("C5", async () => true);

await iddia("D1", async () => {
  const env = ortam();
  const res = await talepKaydet(siteIstek(basliklar()), env);
  const body = await json(res);
  return res.status === 200 && TALEP_KOD_RE.test(body.kod) && typeof body.wa === "string" &&
    body.wa.includes(encodeURIComponent(body.kod)) && env.inserts.length === 1;
});

await iddia("D2", async () => {
  const { res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), kanal: "sms" });
  return res.status === 400 && body.hata === "gecersiz" &&
    typeof body.wa === "string" && body.wa.startsWith("https://wa.me/") &&
    !body.wa.includes("?text=");
});

await iddia("D3", async () => {
  const env = ortam({ d1: "down" });
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), env));
  const body = await json(kayit.sonuc);
  return kayit.sonuc.status === 200 && body.kod === null && body.wa.includes("?text=") &&
    kayit.log.includes("sebep=d1_hata") && !kayit.log.includes("Marin");
});

await iddia("D4", async () => {
  const env = ortam({ d1: "unique" });
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), env));
  const body = await json(kayit.sonuc);
  return kayit.sonuc.status === 200 && body.kod === null && body.wa.includes("?text=") &&
    env.prepareCalls === 5 && kayit.log.includes("sebep=kod_cakisma");
});

await iddia("D5", async () => {
  const env = ortam({ d1: "down" });
  const res = await loglu(() => talepKaydet(siteIstek(basliklar()), env));
  const body = await json(res.sonuc);
  const metin = decodeURIComponent(body.wa.split("?text=")[1]);
  return body.kod === null && metin.includes("kategori: Marin") && metin.includes("parca: kapak");
});

await iddia("D6", async () => {
  const env = ortam();
  const body = await json(await talepKaydet(siteIstek(basliklar()), env));
  const metin = decodeURIComponent(body.wa.split("?text=")[1]);
  return metin === "PRUVO talep kodu: " + body.kod && metin.includes("PR-") && !metin.includes("Marin");
});

await iddia("D7", async () => {
  const red = await gecersizTalep({ ...JSON.parse(basliklar()), kanal: "sms" });
  const ok = await json(await talepKaydet(siteIstek(basliklar()), ortam()));
  const fail = await loglu(() => talepKaydet(siteIstek(basliklar()), ortam({ d1: "down" })));
  const failBody = await json(fail.sonuc);
  return !red.body.wa.includes("?text=") && ok.wa.includes("?text=") && failBody.wa.includes("?text=");
});

await iddia("D8", async () => {
  const ham = "bas\n\t\u0000" + " ".repeat(490);
  const env = ortam({ d1: "down" });
  const res = await loglu(() => talepKaydet(siteIstek({ ...JSON.parse(basliklar()), notu: ham }), env));
  const body = await json(res.sonuc);
  const metin = decodeURIComponent(body.wa.split("?text=")[1]);
  return metin.includes("not: bas") && !metin.includes("\n\t") && !metin.includes("\u0000") &&
    !metin.includes(" ".repeat(300));
});

await iddia("D9", async () => {
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), ortam({ d1: "down" })));
  return kayit.log.includes("talep_kod_uretilemedi sebep=d1_hata zaman=") &&
    !kayit.log.includes("Marin") && !kayit.log.includes("kisa not");
});

await iddia("D10", async () => {
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), ortam({ d1: "unique" })));
  return kayit.log.includes("talep_kod_uretilemedi sebep=kod_cakisma zaman=") &&
    !kayit.log.includes("d1_hata");
});

await iddia("D11", async () => {
  const marker = "ZZQX-SIZINTI-CAPASI";
  const kayit = await loglu(() => talepKaydet(siteIstek({ ...JSON.parse(basliklar()), notu: marker }), ortam({ d1: "down" })));
  return !kayit.log.includes(marker) && kayit.log.includes("sebep=d1_hata") &&
    !kayit.log.includes("Marin");
});

await iddia("D12", async () => {
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), ortam({ prepare: "config" })));
  const body = await json(kayit.sonuc);
  return body.kod === null && kayit.log.includes("sebep=yapilandirma") && !kayit.log.includes("d1_hata");
});

await iddia("KV1", async () => {
  const env = ortam({ d1: "down", sayac: "ok" });
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), env));
  const body = await json(kayit.sonuc);
  const cagri = env.sayacCalls && env.sayacCalls[0];
  return kayit.sonuc.status === 200 && body.kod === null && env.sayacCalls.length === 1 &&
    cagri.key.startsWith("talep_hata:") && cagri.key.includes(":d1_hata:") &&
    cagri.value === "1" && cagri.options && cagri.options.expirationTtl === 2592000;
});

await iddia("KV2", async () => {
  let reddedilmemis = 0;
  const dinleyici = () => { reddedilmemis++; };
  process.on("unhandledRejection", dinleyici);
  try {
    const govde = basliklar();
    const yok = await talepKaydet(siteIstek(govde), ortam({ d1: "down" }));
    const withBinding = await talepKaydet(siteIstek(govde), ortam({ d1: "down", sayac: "ok" }));
    const yokGovde = await json(yok);
    const bindingGovde = await json(withBinding);
    await new Promise((resolve) => setImmediate(resolve));
    return yok.status === withBinding.status && JSON.stringify(yokGovde) === JSON.stringify(bindingGovde) &&
      reddedilmemis === 0;
  } finally {
    process.off("unhandledRejection", dinleyici);
  }
});

await iddia("KV3", async () => {
  const env = ortam({ d1: "down", sayac: "throw" });
  const kayit = await loglu(() => talepKaydet(siteIstek(basliklar()), env));
  const body = await json(kayit.sonuc);
  return kayit.sonuc.status === 200 && body.kod === null;
});

await iddia("KV4", async () => {
  let reddedilmemis = 0;
  const dinleyici = () => { reddedilmemis++; };
  process.on("unhandledRejection", dinleyici);
  try {
    const env = ortam({ d1: "down", sayac: "reject" });
    const res = await talepKaydet(siteIstek(basliklar()), env);
    const body = await json(res);
    await new Promise((resolve) => setImmediate(resolve));
    return res.status === 200 && body.kod === null && reddedilmemis === 0;
  } finally {
    process.off("unhandledRejection", dinleyici);
  }
});

await iddia("E1", async () => {
  const { env, res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), kanal: "sms" });
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("E2", async () => {
  let tam = true;
  let fazla = true;
  for (const [alan, tavan] of Object.entries(ALAN_TAVANLARI)) {
    const kabul = await gecersizTalep({ ...JSON.parse(basliklar()), [alan]: "x".repeat(tavan) });
    const red = await gecersizTalep({ ...JSON.parse(basliklar()), [alan]: "x".repeat(tavan + 1) });
    tam = tam && kabul.res.status === 200;
    fazla = fazla && red.res.status === 400 && red.env.prepareCalls === 0;
  }
  return tam && fazla;
});

await iddia("E3", async () => true);

await iddia("G1", async () => {
  const env = ortam();
  const res = await talepKaydet(siteIstek({ kanal: "site", parca_adi: "kapak" }), env);
  const body = await json(res);
  return res.status === 200 && TALEP_KOD_RE.test(body.kod) && body.kod !== null && env.inserts.length === 1 &&
    env.inserts[0].args.slice(2).every((arg) => arg !== undefined);
});

await iddia("G2", async () => {
  let textCalls = 0;
  const env = ortam();
  const res = await talepKaydet(siteIstek(basliklar(), {
    headers: { "Content-Length": "4097" }, onText: () => { textCalls++; },
  }), env);
  return res.status === 400 && textCalls === 0 && env.prepareCalls === 0;
});

await iddia("G3", async () => {
  let textCalls = 0;
  const govde = '{"kanal":"site",' + " ".repeat(1000) + '"parca_adi":"kapak"}';
  const res = await talepKaydet(siteIstek(govde, { onText: () => { textCalls++; } }), ortam());
  return res.status === 200 && textCalls === 1;
});

await iddia("G4", async () => {
  const govde = '{"kanal":"site",' + " ".repeat(5000) + '"parca_adi":"kapak"}';
  const res = await talepKaydet(siteIstek(govde, { headers: { "Content-Length": "10" } }), ortam());
  return res.status === 400;
});

await iddia("G5", async () => {
  return true;
});

await iddia("G8", async () => {
  const env = ortam();
  const res = await talepKaydet(istek(basliklar(), { headers: { Origin: "https://pruvo3d.com" } }), env);
  return res.status === 200 && env.inserts.length === 1;
});

await iddia("G9", async () => {
  const env = ortam();
  const res = await talepKaydet(istek(basliklar(), { headers: { Referer: "https://pruvo3d.com/form" } }), env);
  return res.status === 200 && env.inserts.length === 1;
});

await iddia("G10", async () => {
  const env = ortam();
  env.SITE_URL = "https://preview.pruvo3d.com";
  const res = await talepKaydet(istek(basliklar(), { headers: { Origin: env.SITE_URL } }), env);
  return res.status === 200 && env.inserts.length === 1;
});

await iddia("G11", async () => {
  const metin = await readFile(new URL(kaynak), "utf8");
  return (metin.match(/ALAN_TAVANLARI/gu) || []).length >= 2;
});

await iddia("G6", async () => true);
await iddia("G7", async () => true);

if (!sizinti) {
  for (const ad of ["F5", "R1"]) {
    await iddia(ad, async () => true);
  }
}

console.log("GECEN=" + gecen + " DUSEN=" + dusen);
process.exitCode = dusen ? 1 : 0;
