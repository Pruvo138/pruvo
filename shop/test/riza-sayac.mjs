#!/usr/bin/env node
/**
 * PRUVO shop — POST /api/shop/riza BIRIM TESTLERI (kimliksiz riza sayaci, src/riza-sayac.js).
 *
 *   node shop/test/riza-sayac.mjs
 *
 * riza-sayac.js'i DOGRUDAN import eder (wrangler'siz, AG YOK). env.KATALOG sahtesi UPSERT'i gercekten
 * uygular (PRIMARY KEY gun+karar -> n), istek sahtesi OKUNAN baslik adlarini sayar.
 *  V1 kabul 3 POST -> n=3 · V2 ret yazilir · V3 kapat yazilir (3 karar 3 ayri satir) ·
 *  V4 bilinmeyen karar "evet" -> 204, D1 0 · V5 k yok / sayi / dizi -> 204, D1 0 ·
 *  V6 buyuk harf "KABUL" -> 204, D1 0 (beyaz liste birebir) · V7 yanlis Origin -> 403, D1 0 ·
 *  V8 Origin+Referer yok -> 403, D1 0 · V9 yalniz izinli Referer -> yazilir ·
 *  V10 limiter binding yok -> 204, D1 0 · V11 limiter patlar / success:false -> 204, D1 0 ·
 *  V12 baglanan parametrelerde, okunan basliklarda ve tablo kolonlarinda IP/UA/cerez YOK ·
 *  V13 istemci `gun` alani yok sayilir (sunucu UTC gunu) · V14 GET / bozuk JSON -> 204, D1 0.
 * MUTANT (riza-sayac.js'in izole kopyasi shop/test/ icinde gecici dosya, sonunda silinir):
 *  M1 origin guard kalkar -> [V7,V8] · M2 karar beyaz listesi kalkar -> [V4,V6] ·
 *  M3 gun istemciden -> [V13] · M4 IP basligi bind'e baglanir -> [V12].
 */

import { readFileSync, writeFileSync, unlinkSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BURA = dirname(fileURLToPath(import.meta.url));
const KAYNAK_YOL = join(BURA, "..", "src", "riza-sayac.js");
const SEMA_YOL = join(BURA, "..", "..", "tools", "d1-sema.sql");
const IP = "203.0.113.78", UA = "UA-RZ-7Q", CEREZ = "_ga=GA1.RZ-9K";

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
                const k = args.slice(0, 2).join("|");
                satirlar.set(k, (satirlar.get(k) || 0) + 1);
                return { meta: { changes: 1 } };
              },
            };
          },
        };
      },
    },
  };
  if (opts.limiter === "patlar") {
    env.RIZA_RATE_LIMIT = { async limit() { throw new Error("limiter yok"); } };
  } else if (opts.limiter === "dolu") {
    env.RIZA_RATE_LIMIT = { async limit() { return { success: false }; } };
  } else if (opts.limiter !== false) {
    env.RIZA_RATE_LIMIT = { async limit() { return { success: true }; } };
  }
  return env;
}

function istek(govde, basliklar, yontem) {
  const b = {};
  for (const [k, v] of Object.entries(basliklar || {})) { b[k.toLowerCase()] = v; }
  const okunan = [];
  return {
    okunan,
    method: yontem || "POST",
    headers: { get(k) { okunan.push(String(k).toLowerCase()); return k.toLowerCase() in b ? b[k.toLowerCase()] : null; } },
    async json() { if (govde === "BOZUK") { throw new SyntaxError("bozuk"); } return govde; },
  };
}
const DOGRU = { Origin: "https://pruvo3d.com" };
const SQL_RE = /^INSERT INTO riza_sayac\(gun,karar,n\) VALUES\(\?,\?,1\) ON CONFLICT\(gun,karar\) DO UPDATE SET n=n\+1$/;

async function vakalar(rizaKaydet) {
  const s = {}, iz = {};
  const bugun = () => new Date().toISOString().slice(0, 10);
  {
    const env = mockEnv();
    const st = [];
    for (let i = 0; i < 3; i++) { st.push((await rizaKaydet(istek({ k: "kabul" }, DOGRU), env)).status); }
    iz.V1 = { st, satir: [...env.satirlar] };
    s.V1 = st.every((x) => x === 204) && env.satirlar.size === 1 && env.satirlar.get(bugun() + "|kabul") === 3 &&
      env.cagrilar.every((c) => SQL_RE.test(c.sql));
  }
  {
    const env = mockEnv();
    const r = await rizaKaydet(istek({ k: "ret" }, DOGRU), env);
    iz.V2 = { st: r.status, satir: [...env.satirlar] };
    s.V2 = r.status === 204 && env.satirlar.size === 1 && env.satirlar.get(bugun() + "|ret") === 1;
  }
  {
    const env = mockEnv();
    const st = [];
    for (const k of ["kapat", "kabul", "ret", "kapat"]) { st.push((await rizaKaydet(istek({ k }, DOGRU), env)).status); }
    iz.V3 = { st, satir: [...env.satirlar] };
    s.V3 = st.every((x) => x === 204) && env.satirlar.size === 3 && env.satirlar.get(bugun() + "|kapat") === 2 &&
      env.satirlar.get(bugun() + "|kabul") === 1 && env.satirlar.get(bugun() + "|ret") === 1;
  }
  {
    const env = mockEnv();
    const r = await rizaKaydet(istek({ k: "evet" }, DOGRU), env);
    iz.V4 = { st: r.status, d1: env.cagrilar.length };
    s.V4 = r.status === 204 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const st = [];
    for (const g of [{}, { k: 1 }, { k: ["kabul"] }, ["kabul"], null]) { st.push((await rizaKaydet(istek(g, DOGRU), env)).status); }
    iz.V5 = { st, d1: env.cagrilar.length };
    s.V5 = st.every((x) => x === 204) && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const r = await rizaKaydet(istek({ k: "KABUL" }, DOGRU), env);
    iz.V6 = { st: r.status, d1: env.cagrilar.length };
    s.V6 = r.status === 204 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const r = await rizaKaydet(istek({ k: "kabul" }, { Origin: "https://evil.example.com", Referer: "https://pruvo3d.com/" }), env);
    iz.V7 = { st: r.status, d1: env.cagrilar.length };
    s.V7 = r.status === 403 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const r = await rizaKaydet(istek({ k: "kabul" }, {}), env);
    iz.V8 = { st: r.status, d1: env.cagrilar.length };
    s.V8 = r.status === 403 && env.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const r = await rizaKaydet(istek({ k: "ret" }, { Referer: "https://www.pruvo3d.com/sss/" }), env);
    iz.V9 = { st: r.status, satir: [...env.satirlar] };
    s.V9 = r.status === 204 && env.satirlar.get(bugun() + "|ret") === 1;
  }
  {
    const env = mockEnv({ limiter: false });
    const r = await rizaKaydet(istek({ k: "kabul" }, DOGRU), env);
    iz.V10 = { st: r.status, d1: env.cagrilar.length };
    s.V10 = r.status === 204 && env.cagrilar.length === 0;
  }
  {
    const e1 = mockEnv({ limiter: "patlar" }), e2 = mockEnv({ limiter: "dolu" });
    const r1 = await rizaKaydet(istek({ k: "kabul" }, DOGRU), e1);
    const r2 = await rizaKaydet(istek({ k: "ret" }, DOGRU), e2);
    iz.V11 = { st: [r1.status, r2.status], d1: [e1.cagrilar.length, e2.cagrilar.length] };
    s.V11 = r1.status === 204 && r2.status === 204 && e1.cagrilar.length === 0 && e2.cagrilar.length === 0;
  }
  {
    const env = mockEnv();
    const rq = istek({ k: "kabul" }, { ...DOGRU, "CF-Connecting-IP": IP, "User-Agent": UA, Cookie: CEREZ, "X-Forwarded-For": IP });
    await rizaKaydet(rq, env);
    const ham = JSON.stringify(env.cagrilar);
    const sema = readFileSync(SEMA_YOL, "utf8").match(/CREATE TABLE IF NOT EXISTS riza_sayac \(([^;]*)\);/);
    // PRIMARY KEY (...) cumlesi ayiklanir; kalan her virgullu parca bir kolon tanimi (ilk kelime = ad).
    const kolonlar = sema ? sema[1].replace(/,\s*PRIMARY KEY\s*\([^)]*\)/, "").split(",").map((x) => x.trim().split(/\s+/)[0]) : [];
    const yasak = /ip|agent|ua$|^ua|cookie|cerez|ref|url/i;
    iz.V12 = { okunan: rq.okunan, kolonlar, args: env.cagrilar.map((c) => c.args) };
    s.V12 = env.cagrilar.length === 1 && env.cagrilar[0].args.length === 2 &&
      ![IP, UA, CEREZ].some((x) => ham.includes(x)) &&
      rq.okunan.every((k) => k === "origin" || k === "referer") &&
      JSON.stringify(kolonlar) === JSON.stringify(["gun", "karar", "n"]) &&
      kolonlar.every((k) => !yasak.test(k));
  }
  {
    const env = mockEnv();
    await rizaKaydet(istek({ k: "kabul", gun: "1999-01-01" }, DOGRU), env);
    const a = env.cagrilar[0] && env.cagrilar[0].args;
    iz.V13 = { args: a };
    s.V13 = !!a && a[0] === bugun() && !JSON.stringify(a).includes("1999");
  }
  {
    const env = mockEnv();
    const r1 = await rizaKaydet(istek({ k: "kabul" }, DOGRU, "GET"), env);
    const r2 = await rizaKaydet(istek("BOZUK", DOGRU), env);
    iz.V14 = { st: [r1.status, r2.status], d1: env.cagrilar.length };
    s.V14 = r1.status === 204 && r2.status === 204 && env.cagrilar.length === 0;
  }
  Object.defineProperty(s, "iz", { value: iz, enumerable: false });
  return s;
}

const ADLAR = {
  V1: "kabul 3 POST -> n=3",
  V2: "ret yazilir",
  V3: "kapat yazilir (3 karar 3 ayri satir)",
  V4: "bilinmeyen karar 'evet' -> 204, D1 cagrisi 0",
  V5: "k yok / sayi / dizi / null govde -> 204, D1 cagrisi 0",
  V6: "'KABUL' (buyuk harf) -> 204, D1 cagrisi 0",
  V7: "yanlis Origin -> 403, D1 cagrisi 0",
  V8: "Origin + Referer yok -> 403, D1 cagrisi 0",
  V9: "yalniz izinli Referer -> yazilir",
  V10: "rate-limit binding yok -> 204, D1 cagrisi 0",
  V11: "limiter patlar / cap dolu -> 204, D1 cagrisi 0",
  V12: "parametre/baslik/kolonlarda IP-UA-cerez YOK",
  V13: "istemci gun alani yok sayilir (sunucu UTC gunu)",
  V14: "GET / bozuk JSON -> 204, D1 cagrisi 0",
};
const VAKALAR = Object.keys(ADLAR);

const { rizaKaydet } = await import(pathToFileURL(KAYNAK_YOL).href);
const s = await vakalar(rizaKaydet);
let gecen = 0;
for (const v of VAKALAR) {
  if (s[v] === true) { gecen++; console.log("  ✅ " + v + " " + ADLAR[v]); }
  else { console.log("  ❌ " + v + " " + ADLAR[v] + " — " + JSON.stringify(s.iz[v])); }
}
console.log(gecen + "/" + VAKALAR.length);

const KAYNAK = readFileSync(KAYNAK_YOL, "utf8");
const MUTANTLAR = [
  ["M1 origin guard kalkti", "  if (!originIzinli(request, env)) { return reddet(); }\n", "", ["V7", "V8"]],
  ["M2 karar beyaz listesi kalkti", "return KARARLAR.has(k) ? k : null;", "return k || null;", ["V4", "V6"]],
  ["M3 gun istemciden", "const gun = new Date().toISOString().slice(0, 10);",
    "const gun = (govde && govde.gun) || new Date().toISOString().slice(0, 10);", ["V13"]],
  ["M4 IP basligi bind'e baglandi", ".bind(gun, karar)",
    ".bind(gun, karar, request.headers.get(\"CF-Connecting-IP\"))", ["V12"]],
];
let mGecen = 0, survivor = 0;
for (let i = 0; i < MUTANTLAR.length; i++) {
  const [ad, capa, yerine, olmeli] = MUTANTLAR[i];
  if (KAYNAK.split(capa).length - 1 !== 1) { console.log("  ❌ " + ad + " capa bulunamadi"); survivor++; continue; }
  const yol = join(BURA, ".riza-mutant-" + process.pid + "-" + i + ".mjs");
  let kir = null;
  try {
    writeFileSync(yol, KAYNAK.replace(capa, yerine));
    const m = await import(pathToFileURL(yol).href);
    const r = await vakalar(m.rizaKaydet);
    kir = VAKALAR.filter((v) => r[v] !== true);
  } finally {
    if (existsSync(yol)) { unlinkSync(yol); }
  }
  if (!kir || kir.length === 0) { survivor++; }
  const tamam = JSON.stringify(kir) === JSON.stringify(olmeli);
  if (tamam) { mGecen++; }
  console.log("  " + (tamam ? "✅ " : "❌ ") + ad + " -> KIRMIZI " + JSON.stringify(kir) + " (beklenen " + JSON.stringify(olmeli) + ")");
}
console.log("MUTANT " + mGecen + "/" + MUTANTLAR.length + " SURVIVOR=" + survivor);

process.exit(gecen === VAKALAR.length && mGecen === MUTANTLAR.length && survivor === 0 ? 0 : 1);
