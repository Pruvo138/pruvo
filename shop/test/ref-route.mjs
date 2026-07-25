#!/usr/bin/env node
/**
 * PRUVO shop — POST /api/shop/ref BIRIM TESTLERI (OCI #1: wa.me lead REF->click-id kalicilik).
 * Is paketi: /Users/okan/dev/pruvo-pazarlama/.muhendis-oci-ref-gclid-gorevi.md
 *
 *   node shop/test/ref-route.mjs
 *
 * ref.js'i DOGRUDAN import eder (wrangler'siz, hizli). env.KATALOG mock'lanip INSERT
 * parametreleri yakalanir. Kapsam:
 *  - Gecerli paid beacon -> 204 + TEK INSERT OR IGNORE, dogru parametreler (ref, gclid,
 *    gbraid/wbraid null, grup, src, ts, created_at=sayi).
 *  - Organik (click-id yok) -> 204 + INSERT YOK.
 *  - Bozuk ref -> 204 + INSERT YOK.
 *  - Buyuk gclid (>512) reddedilir -> tek click-id oydu -> INSERT YOK; tam 512 kabul.
 *  - gbraid/wbraid yolu -> INSERT'e girer, gclid null.
 *  - Gecersiz grup/src/ts ATILIR (null) ama kayit yazilir (ref + click-id gecerli).
 *  - Non-POST / parse hatasi -> 204 + INSERT YOK.
 *  - D1 yazma hatasi -> yine 204 (fire-and-forget), akis bozulmaz.
 *  - IP RATE-LIMIT (D1 kota koruma): binding mock'lanir -> cap altinda 204+INSERT; cap ustunde
 *    204+INSERT YOK (validasyonun ONUNDE); limiter exception -> fail-open; binding yok -> fail-open.
 *
 * ONCE-KIRMIZI (elle kanitlanabilir): ref.js'te click-id zorunlulugu kaldirilirsa "organik"
 * kirmizi; INSERT OR IGNORE -> INSERT yapilirsa SQL literal testi kirmizi; 204 -> 200 yapilirsa
 * tum statu testleri kirmizi; rate-limit kapisi kaldirilirsa "ratelimit ustunde: INSERT YOK" kirmizi.
 */

import { refDogrula, refKaydet } from "../src/ref.js";

let gecen = 0, kalan = 0;
function ol(ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ " + ad); }
  else { kalan++; console.log("  ❌ " + ad + (detay ? " — " + detay : "")); }
}

const GECERLI_REF = "REF:GS-BYP-AB12";

function mockEnv(opts) {
  opts = opts || {};
  const inserts = [];
  const env = {
    inserts,
    KATALOG: {
      prepare(sql) {
        return {
          bind(...args) {
            return {
              async run() {
                if (opts.patlat) { throw new Error("D1 down"); }
                inserts.push({ sql, args });
                return { meta: { changes: 1 } };
              },
            };
          },
        };
      },
    },
  };
  // opts.limiter: yoksa binding TANIMSIZ (fail-open, mevcut deploy). "izin" -> success:true
  // (cap altinda), "engel" -> success:false (cap asildi), "patlat" -> limiter exception (fail-open).
  if (opts.limiter) {
    env.REF_RATE_LIMIT = {
      calls: [],
      async limit(arg) {
        this.calls.push(arg);
        if (opts.limiter === "patlat") { throw new Error("limiter down"); }
        return { success: opts.limiter !== "engel" };
      },
    };
  }
  return env;
}

function istek(govde, method) {
  return { method: method || "POST", json: async () => govde };
}
// Rate-limit testleri icin CF-Connecting-IP tasiyan istek (limiter key'i IP olmali).
function istekIp(govde, ip) {
  return { method: "POST", json: async () => govde,
           headers: { get: (h) => (h === "CF-Connecting-IP" ? ip : null) } };
}
function bozukIstek() {
  return { method: "POST", json: async () => { throw new Error("gecersiz json"); } };
}
// Origin/Referer basligi tasiyan istek (organik/OG origin-guard testleri). undefined -> baslik yok.
// headers.get case-insensitive (gercek CF Headers gibi).
function istekOrigin(govde, origin, referer) {
  const H = { origin: origin, referer: referer };
  return { method: "POST", json: async () => govde,
           headers: { get: (h) => { const k = String(h).toLowerCase();
             return (k in H && H[k] !== undefined) ? H[k] : null; } } };
}
// PK(ref) benzetimli env: INSERT OR IGNORE gibi ilk ref kazanir, ikinci ayni ref IGNORE (dedup).
function mockEnvDedup() {
  const rows = new Map();
  const inserts = [];
  const env = {
    rows,
    inserts,
    KATALOG: {
      prepare(sql) {
        return {
          bind(...args) {
            return {
              async run() {
                inserts.push({ sql, args });
                const ref = args[0];
                if (!rows.has(ref)) { rows.set(ref, args); }   // ilk kazanir
                return { meta: { changes: rows.size } };
              },
            };
          },
        };
      },
    },
  };
  return env;
}

// ---- 1) refDogrula saf: gecerli / gecersiz ----
{
  const k = refDogrula({ ref: GECERLI_REF, gclid: "CLICK123", grup: "BYP", src: "GS", ts: 1690000000000 });
  ol("refDogrula gecerli kayit doner", k && k.ref === GECERLI_REF && k.gclid === "CLICK123" &&
    k.gbraid === null && k.wbraid === null && k.grup === "BYP" && k.src === "GS" && k.ts === 1690000000000,
    JSON.stringify(k));
  ol("refDogrula bozuk ref -> null", refDogrula({ ref: "REF:xx", gclid: "C" }) === null);
  ol("refDogrula click-id yok -> null", refDogrula({ ref: GECERLI_REF }) === null);
  ol("refDogrula gecersiz govde -> null", refDogrula(null) === null && refDogrula([]) === null &&
    refDogrula("x") === null);
}

// ---- 2) Gecerli paid beacon -> 204 + tek INSERT, dogru parametreler ----
{
  const env = mockEnv();
  const res = await refKaydet(istek({
    ref: GECERLI_REF, gclid: "CLICK123", grup: "BYP", src: "GS", ts: 1690000000000,
  }), env);
  ol("paid: 204 doner", res.status === 204);
  ol("paid: govdesiz (204)", res.body === null);
  ol("paid: tek INSERT", env.inserts.length === 1, "insert=" + env.inserts.length);
  const a = env.inserts[0] ? env.inserts[0].args : [];
  ol("paid: INSERT OR IGNORE + tablo adi", env.inserts[0] &&
    /INSERT OR IGNORE INTO reklam_ref_gclid/.test(env.inserts[0].sql), env.inserts[0] && env.inserts[0].sql);
  ol("paid: parametreler (ref,gclid,gbraid,wbraid,grup,src,ts)",
    a[0] === GECERLI_REF && a[1] === "CLICK123" && a[2] === null && a[3] === null &&
    a[4] === "BYP" && a[5] === "GS" && a[6] === 1690000000000, JSON.stringify(a));
  ol("paid: created_at sunucu sayisi", typeof a[7] === "number" && a[7] > 0, String(a[7]));
}

// ---- 3) Organik (click-id yok) -> 204 + INSERT YOK ----
{
  const env = mockEnv();
  const res = await refKaydet(istek({ ref: GECERLI_REF, grup: "BYP", src: "GS", ts: 1 }), env);
  ol("organik: 204", res.status === 204);
  ol("organik: INSERT YOK", env.inserts.length === 0, "insert=" + env.inserts.length);
}

// ---- 4) Bozuk ref -> 204 + INSERT YOK ----
{
  const env = mockEnv();
  const res = await refKaydet(istek({ ref: "REF:gs-byp-ab12", gclid: "C" }), env); // kucuk harf
  ol("bozuk ref: 204", res.status === 204);
  ol("bozuk ref: INSERT YOK", env.inserts.length === 0);
  const env2 = mockEnv();
  await refKaydet(istek({ ref: "MERHABA " + GECERLI_REF, gclid: "C" }), env2); // onek kir
  ol("ref cop onekli: INSERT YOK", env2.inserts.length === 0);
}

// ---- 5) Buyuk gclid (>512) reddedilir; tam 512 kabul ----
{
  const env = mockEnv();
  await refKaydet(istek({ ref: GECERLI_REF, gclid: "A".repeat(513) }), env);
  ol("gclid 513: reddedilir (INSERT YOK)", env.inserts.length === 0, "insert=" + env.inserts.length);
  const env2 = mockEnv();
  await refKaydet(istek({ ref: GECERLI_REF, gclid: "A".repeat(512) }), env2);
  ol("gclid 512: kabul (1 INSERT, tam deger)",
    env2.inserts.length === 1 && env2.inserts[0].args[1].length === 512);
}

// ---- 6) gbraid/wbraid yolu -> INSERT, gclid null ----
{
  const env = mockEnv();
  await refKaydet(istek({ ref: GECERLI_REF, gbraid: "GB123", wbraid: "WB456", grup: "DIS", src: "GS", ts: 2 }), env);
  const a = env.inserts[0] ? env.inserts[0].args : [];
  ol("gbraid/wbraid: 1 INSERT", env.inserts.length === 1);
  ol("gbraid/wbraid: gclid null, gbraid/wbraid yazilir",
    a[1] === null && a[2] === "GB123" && a[3] === "WB456", JSON.stringify(a));
}

// ---- 7) Gecersiz grup/src/ts ATILIR (null) ama kayit yazilir ----
{
  const env = mockEnv();
  await refKaydet(istek({ ref: GECERLI_REF, gclid: "C", grup: "cok-uzun", src: "abc", ts: "yaz" }), env);
  const a = env.inserts[0] ? env.inserts[0].args : [];
  ol("sanitize: kayit yazilir (ref+click-id gecerli)", env.inserts.length === 1);
  ol("sanitize: gecersiz grup/src/ts -> null", a[4] === null && a[5] === null && a[6] === null,
    JSON.stringify(a));
}

// ---- 8) Non-POST / parse hatasi -> 204 + INSERT YOK ----
{
  const env = mockEnv();
  const res = await refKaydet(istek({ ref: GECERLI_REF, gclid: "C" }, "GET"), env);
  ol("GET: 204 + INSERT YOK", res.status === 204 && env.inserts.length === 0);
  const env2 = mockEnv();
  const res2 = await refKaydet(bozukIstek(), env2);
  ol("parse hatasi: 204 + INSERT YOK", res2.status === 204 && env2.inserts.length === 0);
}

// ---- 9) D1 yazma hatasi -> yine 204 (fire-and-forget) ----
{
  const env = mockEnv({ patlat: true });
  const oncekiHata = console.error;
  console.error = () => {}; // beklenen hata logunu bastir
  const res = await refKaydet(istek({ ref: GECERLI_REF, gclid: "C" }), env);
  console.error = oncekiHata;
  ol("D1 hatasi: yine 204", res.status === 204);
}

// ---- 10) Rate-limit (IP soft-cap, D1 kota koruma): cap ALTINDA -> 204+INSERT; USTUNDE -> 204+INSERT YOK ----
{
  // Cap ALTINDA (limiter success:true): normal akis, gecerli kayit D1'e yazilir.
  const envAlt = mockEnv({ limiter: "izin" });
  const rAlt = await refKaydet(istekIp({ ref: GECERLI_REF, gclid: "CLICK123" }, "1.2.3.4"), envAlt);
  ol("ratelimit altinda: 204", rAlt.status === 204);
  ol("ratelimit altinda: INSERT var", envAlt.inserts.length === 1, "insert=" + envAlt.inserts.length);
  ol("ratelimit altinda: limiter IP anahtariyla cagrildi",
    envAlt.REF_RATE_LIMIT.calls.length === 1 && envAlt.REF_RATE_LIMIT.calls[0].key === "1.2.3.4",
    JSON.stringify(envAlt.REF_RATE_LIMIT.calls));

  // Cap USTUNDE (limiter success:false): D1'e YAZILMAZ (kota korunur), yine 204 (davranis degismez).
  const envUst = mockEnv({ limiter: "engel" });
  const rUst = await refKaydet(istekIp({ ref: GECERLI_REF, gclid: "CLICK123" }, "1.2.3.4"), envUst);
  ol("ratelimit ustunde: 204 (davranis/bilgi sizmaz)", rUst.status === 204);
  ol("ratelimit ustunde: INSERT YOK (D1 kotasi korunur)", envUst.inserts.length === 0,
    "insert=" + envUst.inserts.length);

  // Rate-limit VALIDASYONUN ONUNDE: cap asilinca gecerli kayit BILE yazilmaz (yukarida goruldu);
  // demek ki refDogrula'ya varmadan kesiliyor.

  // Limiter EXCEPTION -> fail-open: beacon bloklanmaz, gecerli kayit yine yazilir, 204.
  const envPat = mockEnv({ limiter: "patlat" });
  const oncekiHata = console.error;
  console.error = () => {};
  const rPat = await refKaydet(istekIp({ ref: GECERLI_REF, gclid: "CLICK123" }, "1.2.3.4"), envPat);
  console.error = oncekiHata;
  ol("ratelimit limiter hatasi: fail-open (204 + INSERT var)",
    rPat.status === 204 && envPat.inserts.length === 1, "insert=" + envPat.inserts.length);

  // Binding YOK (mevcut deploy / yerel) -> limiter atlanir, normal akis (fail-open).
  const envYok = mockEnv();
  const rYok = await refKaydet(istekIp({ ref: GECERLI_REF, gclid: "CLICK123" }, "1.2.3.4"), envYok);
  ol("ratelimit binding yok: normal akis (204 + INSERT)",
    rYok.status === 204 && envYok.inserts.length === 1, "insert=" + envYok.inserts.length);
}

// ---- 11) ORGANIK (src=OG, click-id yok) — refDogrula saf ----
{
  const k = refDogrula({ ref: "REF:OG-G0-AB12", src: "OG", grup: "G0", ts: 7 });
  ol("refDogrula OG: kabul + click-id NULL",
    k && k.ref === "REF:OG-G0-AB12" && k.gclid === null && k.gbraid === null && k.wbraid === null &&
    k.src === "OG" && k.grup === "G0" && k.ts === 7, JSON.stringify(k));
  ol("refDogrula src=OG ama ref GS onekli -> null (tutarsiz)",
    refDogrula({ ref: "REF:GS-G0-AB12", src: "OG" }) === null);
  ol("refDogrula ref OG-onekli ama src eksik -> null (eski davranis)",
    refDogrula({ ref: "REF:OG-G0-AB12" }) === null);
}

// ---- 12) OG + dogru origin -> 204 + INSERT (src=OG, click-id NULL) ----
{
  const env = mockEnv();
  const res = await refKaydet(
    istekOrigin({ ref: "REF:OG-G0-AB12", src: "OG", grup: "G0", ts: 7 }, "https://pruvo3d.com"), env);
  ol("OG dogru origin: 204", res.status === 204);
  ol("OG dogru origin: tek INSERT", env.inserts.length === 1, "insert=" + env.inserts.length);
  const a = env.inserts[0] ? env.inserts[0].args : [];
  ol("OG dogru origin: src=OG + click-id NULL + grup/ts",
    a[0] === "REF:OG-G0-AB12" && a[1] === null && a[2] === null && a[3] === null &&
    a[4] === "G0" && a[5] === "OG" && a[6] === 7 && typeof a[7] === "number", JSON.stringify(a));
  const env2 = mockEnv();
  await refKaydet(istekOrigin({ ref: "REF:OG-G0-CD34", src: "OG" }, "https://www.pruvo3d.com"), env2);
  ol("OG www origin: INSERT", env2.inserts.length === 1);
  const env3 = mockEnv();
  await refKaydet(
    istekOrigin({ ref: "REF:OG-G0-EF56", src: "OG" }, undefined, "https://pruvo3d.com/urun/x/"), env3);
  ol("OG Origin yok ama Referer pruvo: INSERT (fallback)", env3.inserts.length === 1);
}

// ---- 13) OG + YANLIS/EKSIK origin -> 403 + INSERT YOK (anti-abuse) ----
{
  const env = mockEnv();
  const res = await refKaydet(
    istekOrigin({ ref: "REF:OG-G0-AB12", src: "OG" }, "https://evil.example.com"), env);
  ol("OG yanlis origin: 403", res.status === 403, "status=" + res.status);
  ol("OG yanlis origin: INSERT YOK", env.inserts.length === 0, "insert=" + env.inserts.length);
  const env2 = mockEnv();
  const res2 = await refKaydet(istekOrigin({ ref: "REF:OG-G0-AB12", src: "OG" }), env2); // baslik yok
  ol("OG origin/referer yok (fail-closed): 403 + INSERT YOK",
    res2.status === 403 && env2.inserts.length === 0, "status=" + res2.status + " insert=" + env2.inserts.length);
  // Referer yanlis, Origin yok -> 403.
  const env3 = mockEnv();
  const res3 = await refKaydet(
    istekOrigin({ ref: "REF:OG-G0-AB12", src: "OG" }, undefined, "https://evil.example.com/x"), env3);
  ol("OG yanlis Referer: 403 + INSERT YOK", res3.status === 403 && env3.inserts.length === 0);
}

// ---- 14) OG + bozuk format -> 204 + INSERT YOK (dogru origin olsa BILE) ----
{
  const env = mockEnv();
  const res = await refKaydet(
    istekOrigin({ ref: "REF:OG-G0-ab12", src: "OG" }, "https://pruvo3d.com"), env); // kucuk harf rnd
  ol("OG bozuk format: 204 (dogrula eledi)", res.status === 204, "status=" + res.status);
  ol("OG bozuk format: INSERT YOK", env.inserts.length === 0);
}

// ---- 15) PAID + yanlis/eksik origin -> ESKI davranis (204 + INSERT); guard paid'e DOKUNMAZ ----
{
  const env = mockEnv();
  const res = await refKaydet(istekOrigin(
    { ref: GECERLI_REF, gclid: "CLICK123", grup: "BYP", src: "GS", ts: 9 }, "https://evil.example.com"), env);
  ol("paid yanlis origin: 204 (degismez)", res.status === 204);
  ol("paid yanlis origin: INSERT var (guard paid'e dokunmaz)", env.inserts.length === 1,
    "insert=" + env.inserts.length);
  const env2 = mockEnv();
  await refKaydet(istek({ ref: GECERLI_REF, gclid: "CLICK123" }), env2); // header'siz (mevcut istek)
  ol("paid header'siz: INSERT var (regresyon yok)", env2.inserts.length === 1);
}

// ---- 16) OG dedup: ayni ref 2x -> tek satir (INSERT OR IGNORE PK) ----
{
  const env = mockEnvDedup();
  const go = { ref: "REF:OG-G0-DD99", src: "OG", grup: "G0", ts: 5 };
  await refKaydet(istekOrigin(go, "https://pruvo3d.com"), env);
  await refKaydet(istekOrigin(go, "https://pruvo3d.com"), env);
  ol("OG dedup: 2 POST -> 1 satir", env.rows.size === 1, "rows=" + env.rows.size);
  ol("OG dedup: her iki SQL INSERT OR IGNORE",
    env.inserts.length === 2 && env.inserts.every((x) => /INSERT OR IGNORE INTO reklam_ref_gclid/.test(x.sql)));
}

console.log((kalan ? "\nFAIL " : "\nPASS ") + gecen + "/" + (gecen + kalan));
if (kalan) { process.exit(1); }
