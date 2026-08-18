#!/usr/bin/env node
/** POST /api/shop/talep davranis testi. */

import { pathToFileURL } from "node:url";

const kaynak = process.env.TALEP_SOURCE
  ? pathToFileURL(process.env.TALEP_SOURCE).href
  : "../src/talep.js";
const { ALAN_TAVANLARI, TALEP_KOD_RE, talepKaydet, talepKoduUret } = await import(kaynak);

const hedef = process.argv.find((arg) => arg.startsWith("--only="));
const hedefAdi = hedef ? hedef.slice("--only=".length) : null;
const sizinti = process.argv.includes("--sizinti");
let gecen = 0;
let dusen = 0;

function ol(ad, kosul, detay = "") {
  if (kosul) {
    gecen++;
    console.log("  ✅ " + ad);
  } else {
    dusen++;
    console.log("  ❌ " + ad + (detay ? " — " + detay : ""));
  }
}

async function iddia(ad, fn) {
  if (hedefAdi && hedefAdi !== ad) { return; }
  try {
    const sonuc = await fn();
    ol(ad, sonuc === true, sonuc === true ? "" : String(sonuc));
  } catch (e) {
    ol(ad, false, e && e.stack ? e.stack : String(e));
  }
}

function basliklar(kayit = {}) {
  const girdi = { kanal: "site", kategori: "Marin", parca_adi: "kapak", ...kayit };
  return JSON.stringify(girdi);
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
    text: async () => ham,
  };
}

function siteIstek(body, opts = {}) {
  return istek(body, { ...opts, headers: { Origin: "https://pruvo3d.com", ...(opts.headers || {}) } });
}

function ortam(opts = {}) {
  const env = { inserts: [], prepareCalls: 0, KATALOG: {
    prepare(sql) {
      env.prepareCalls++;
      return { bind: (...args) => ({
        async run() {
          if (opts.d1 === "unique") { throw new Error("UNIQUE constraint failed: talepler.kod"); }
          if (opts.d1 === "down") { throw new Error("D1 down"); }
          env.inserts.push({ sql, args });
          return { meta: { changes: 1 } };
        },
      }) };
    },
  }, SITE_URL: "https://pruvo3d.com" };
  if (opts.rate === "limit") {
    env.TALEP_RATE_LIMIT = { async limit() { return { success: false }; } };
  }
  return env;
}

function json(res) { return res.json(); }

async function beklenenHataSessiz(fn) {
  const onceki = console.error;
  console.error = () => {};
  try { return await fn(); } finally { console.error = onceki; }
}

async function gecersizTalep(kayit, opts = {}) {
  const env = ortam();
  const res = await talepKaydet(siteIstek(kayit, opts), env);
  return { env, res, body: await json(res) };
}

// Savunma sirasi: allow-list, honeypot, bayt tavanı, origin guard.
await iddia("B1", async () => {
  const { env, res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), telefon: "905551112233" });
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("B2", async () => {
  const { env, res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), website: "bot" });
  return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
});

await iddia("B3", async () => {
  const govde = basliklar({ notu: "ş".repeat(2100) });
  const { env, res, body } = await gecersizTalep(govde);
  return new TextEncoder().encode(govde).length > 4096 && govde.length < 4096 &&
    res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
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

if (!sizinti) {
  await iddia("D1", async () => {
    const env = ortam();
    const res = await talepKaydet(siteIstek(basliklar()), env);
    const body = await json(res);
    return res.status === 200 && TALEP_KOD_RE.test(body.kod) &&
      typeof body.wa === "string" && body.wa.includes("https://wa.me/") &&
      body.wa.includes(encodeURIComponent(body.kod)) && env.inserts.length === 1;
  });

  await iddia("D2", async () => {
    const { res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), kanal: "sms" });
    return res.status === 400 && JSON.stringify(body) === JSON.stringify({
      hata: "gecersiz", wa: "https://wa.me/905451386526",
    });
  });

  await iddia("D3", async () => {
    const env = ortam({ d1: "down" });
    const res = await beklenenHataSessiz(() => talepKaydet(siteIstek(basliklar()), env));
    const body = await json(res);
    return res.status === 200 && body.kod === null && body.wa === "https://wa.me/905451386526";
  });

  await iddia("D4", async () => {
    const env = ortam({ d1: "unique" });
    const res = await beklenenHataSessiz(() => talepKaydet(siteIstek(basliklar()), env));
    const body = await json(res);
    return res.status === 200 && body.kod === null && body.wa === "https://wa.me/905451386526" &&
      env.prepareCalls === 5;
  });

  await iddia("E1", async () => {
    const { env, res, body } = await gecersizTalep({ ...JSON.parse(basliklar()), kanal: "sms" });
    return res.status === 400 && body.hata === "gecersiz" && env.prepareCalls === 0;
  });

  await iddia("E2", async () => {
    const alanlar = Object.entries(ALAN_TAVANLARI);
    let tam = true;
    let fazla = true;
    for (const [alan, tavan] of alanlar) {
      const kabul = await gecersizTalep({ ...JSON.parse(basliklar()), [alan]: "x".repeat(tavan) });
      const red = await gecersizTalep({ ...JSON.parse(basliklar()), [alan]: "x".repeat(tavan + 1) });
      tam = tam && kabul.res.status === 200;
      fazla = fazla && red.res.status === 400 && red.env.prepareCalls === 0;
    }
    return tam && fazla;
  });
}

console.log("GECEN=" + gecen + " DUSEN=" + dusen);
process.exitCode = dusen ? 1 : 0;
