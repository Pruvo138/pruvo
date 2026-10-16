#!/usr/bin/env node
/**
 * PRUVO shop — POST /api/shop/inis BIRIM TESTLERI (riza bagimsiz reklam inis sayaci, src/inis.js).
 *
 *   node shop/test/inis-sayac.mjs
 *
 * inis.js'i DOGRUDAN import eder (wrangler'siz, AG YOK). env.KATALOG sahtesi UPSERT'i gercekten
 * uygular (PRIMARY KEY gun+kaynak+kampanya -> n), istek sahtesi OKUNAN baslik adlarini sayar.
 *  V1 ayni (kaynak,kampanya) 3 POST -> n=3 · V2 yanlis Origin -> 403, D1 0 · V3 Origin+Referer yok
 *  -> 403, D1 0 · V4 binding yok -> 204, D1 0 · V5 kaynak "EvilX" -> "diger", kampanya "-" ·
 *  V6 kampanya 200 karakter -> "-" · V7 baglanan parametrelerde, okunan basliklarda ve tablo
 *  kolonlarinda IP/UA/cerez YOK · V8 istemci `gun` alani yok sayilir (sunucu UTC gunu).
 * MUTANT (inis.js'in izole kopyasi shop/test/ icinde gecici dosya, sonunda silinir):
 *  M1 IP basligi bind'e baglanir -> [V7] · M2 origin guard kalkar -> [V2,V3] · M3 beyaz liste kalkar -> [V5].
 */

import { readFileSync, writeFileSync, unlinkSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURA = dirname(fileURLToPath(import.meta.url));
const KAYNAK_YOL = join(BURA, "..", "src", "inis.js");
const SEMA_YOL = join(BURA, "..", "..", "tools", "d1-sema.sql");
const IP = "203.0.113.77", UA = "UA-IZ-7Q", CEREZ = "_ga=GA1.IZ-9K";

function mockEnv(opts) {
  opts = opts || {};
  const cagrilar = [], satirlar = new Map();
  const env = {
    cagrilar, satirlar,
    KATALOG: {
      prepare(sql) {
        cagrilar.push({ sql, args: null });
        const kayit = cagrilar[cagrilar.length - 1];
        return {
          bind(...args) {
            kayit.args = args;
            return {
              async run() {
                const k = args.slice(0, 3).join("|");
                satirlar.set(k, (satirlar.get(k) || 0) + 1);
                return { meta: { changes: 1 } };
              },
            };
          },
        };
      },
    },
  };
  if (opts.limiter !== false) {
    env.INIS_RATE_LIMIT = { async limit() { return { success: true }; } };
  }
  return env;
}

function istek(govde, basliklar) {
  const b = {};
  for (const [k, v] of Object.entries(basliklar || {})) { b[k.toLowerCase()] = v; }
  const okunan = [];
  return {
    okunan,
    method: "POST",
    headers: { get(k) { okunan.push(String(k).toLowerCase()); return k.toLowerCase() in b ? b[k.toLowerCase()] : null; } },
    async json() { return govde; },
  };
}
const DOGRU = { Origin: "https://pruvo3d.com" };

async function vakalar(inisKaydet) {
  const s = {}, iz = {};
  {
    const env = mockEnv();
    const st = [];
    for (let i = 0; i < 3; i++) { st.push((await inisKaydet(istek({ s: "google", c: "foto-ekim" }, DOGRU), env)).status); }
    const gun = new Date().toISOString().slice(0, 10);
    iz.V1 = { st, satir: [...env.satirlar] };
    s.V1 = st.every((x) => x === 204) && env.satirlar.size === 1 && env.satirlar.get(gun + "|google|foto-ekim") === 3 &&
      env.cagrilar.every((c) => /^INSERT INTO inis_sayac\(gun,kaynak,kampanya,n\) VALUES\(\?,\?,\?,1\) ON CONFLICT\(gun,kaynak,kampanya\) DO UPDATE SET n=n\+1$/.test(c.sql));
  }
  {
    const env = mockEnv();
    const r = await inisKaydet(istek({ s: "google", c: "x" }, { Origin: "https://evil.example.com", Referer: "https://pruvo3d.com/" }), env);
    iz.V2 = { st: r.status, d1: env.cagrilar.length };
    s.V2 = r.status === 403 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const r = await inisKaydet(istek({ s: "google", c: "x" }, {}), env);
    iz.V3 = { st: r.status, d1: env.cagrilar.length };
    s.V3 = r.status === 403 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv({ limiter: false });
    const r = await inisKaydet(istek({ s: "google", c: "x" }, DOGRU), env);
    iz.V4 = { st: r.status, d1: env.cagrilar.length };
    s.V4 = r.status === 204 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const r = await inisKaydet(istek({ s: "EvilX", c: "kampanya1" }, DOGRU), env);
    const a = env.cagrilar[0] && env.cagrilar[0].args;
    iz.V5 = { st: r.status, args: a };
    s.V5 = r.status === 204 && !!a && a[1] === "diger" && a[2] === "-";
  }
  {
    const env = mockEnv();
    const r = await inisKaydet(istek({ s: "Google", c: "a".repeat(200) }, DOGRU), env);
    const a = env.cagrilar[0] && env.cagrilar[0].args;
    iz.V6 = { st: r.status, args: a && [a[0], a[1], String(a[2]).slice(0, 10)] };
    s.V6 = r.status === 204 && !!a && a[1] === "google" && a[2] === "-";
  }
  {
    const env = mockEnv();
    const rq = istek({ s: "google", c: "k" }, { ...DOGRU, "CF-Connecting-IP": IP, "User-Agent": UA, Cookie: CEREZ, "X-Forwarded-For": IP });
    await inisKaydet(rq, env);
    const ham = JSON.stringify(env.cagrilar);
    const sema = readFileSync(SEMA_YOL, "utf8").match(/CREATE TABLE IF NOT EXISTS inis_sayac \(([^;]*)\);/);
    // PRIMARY KEY (...) cumlesi ayiklanir; kalan her virgullu parca bir kolon tanimi (ilk kelime = ad).
    const kolonlar = sema ? sema[1].replace(/,\s*PRIMARY KEY\s*\([^)]*\)/, "").split(",").map((x) => x.trim().split(/\s+/)[0]) : [];
    const yasak = /ip|agent|ua$|^ua|cookie|cerez|ref|url/i;
    iz.V7 = { okunan: rq.okunan, kolonlar, args: env.cagrilar.map((c) => c.args) };
    s.V7 = env.cagrilar.length === 1 && env.cagrilar[0].args.length === 3 &&
      ![IP, UA, CEREZ].some((x) => ham.includes(x)) &&
      rq.okunan.every((k) => k === "origin" || k === "referer") &&
      JSON.stringify(kolonlar) === JSON.stringify(["gun", "kaynak", "kampanya", "n"]) &&
      kolonlar.every((k) => !yasak.test(k));
  }
  {
    const env = mockEnv();
    await inisKaydet(istek({ s: "google", c: "k", gun: "1999-01-01" }, DOGRU), env);
    const a = env.cagrilar[0] && env.cagrilar[0].args;
    iz.V8 = { args: a };
    s.V8 = !!a && a[0] === new Date().toISOString().slice(0, 10) && !JSON.stringify(a).includes("1999");
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}

const ADLAR = {
  V1: "ayni (kaynak,kampanya) 3 POST -> n=3",
  V2: "yanlis Origin -> 403, D1 cagrisi 0",
  V3: "Origin + Referer yok -> 403, D1 cagrisi 0",
  V4: "rate-limit binding yok -> 204, D1 cagrisi 0",
  V5: "kaynak EvilX -> diger, kampanya -",
  V6: "kampanya 200 karakter -> -",
  V7: "parametre/baslik/kolonlarda IP-UA-cerez YOK",
  V8: "istemci gun alani yok sayilir (sunucu UTC gunu)",
};
const VAKALAR = Object.keys(ADLAR);

const { inisKaydet } = await import(pathToFileURL(KAYNAK_YOL).href);
const s = await vakalar(inisKaydet);
let gecen = 0;
for (const v of VAKALAR) {
  if (s[v] === true) { gecen++; console.log("  ✅ " + v + " " + ADLAR[v]); }
  else { console.log("  ❌ " + v + " " + ADLAR[v] + " — " + JSON.stringify(s.iz[v])); }
}
console.log(gecen + "/" + VAKALAR.length);

const KAYNAK = readFileSync(KAYNAK_YOL, "utf8");
const MUTANTLAR = [
  ["M1 IP basligi bind'e baglandi", ".bind(gun, kaynak, kampanya)",
    ".bind(gun, kaynak, kampanya, request.headers.get(\"CF-Connecting-IP\"))", ["V7"]],
  ["M2 origin guard kalkti", "  if (!originIzinli(request, env)) { return reddet(); }\n", "", ["V2", "V3"]],
  ["M3 beyaz liste kalkti", "const kaynak = KAYNAKLAR.has(s) ? s : \"diger\";", "const kaynak = s || \"diger\";", ["V5"]],
];
let mGecen = 0;
for (let i = 0; i < MUTANTLAR.length; i++) {
  const [ad, capa, yerine, olmeli] = MUTANTLAR[i];
  if (KAYNAK.split(capa).length - 1 !== 1) { console.log("  ❌ " + ad + " capa bulunamadi"); continue; }
  const yol = join(BURA, ".inis-mutant-" + process.pid + "-" + i + ".mjs");
  let kir = null;
  try {
    writeFileSync(yol, KAYNAK.replace(capa, yerine));
    const m = await import(pathToFileURL(yol).href);
    const r = await vakalar(m.inisKaydet);
    kir = VAKALAR.filter((v) => r[v] !== true);
  } finally {
    if (existsSync(yol)) { unlinkSync(yol); }
  }
  const tamam = JSON.stringify(kir) === JSON.stringify(olmeli);
  if (tamam) { mGecen++; }
  console.log("  " + (tamam ? "✅ " : "❌ ") + ad + " -> KIRMIZI " + JSON.stringify(kir) + " (beklenen " + JSON.stringify(olmeli) + ")");
}
console.log("MUTANT " + mGecen + "/" + MUTANTLAR.length);

process.exit(gecen === VAKALAR.length && mGecen === MUTANTLAR.length ? 0 : 1);
