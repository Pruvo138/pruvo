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

console.log((kalan ? "\nFAIL " : "\nPASS ") + gecen + "/" + (gecen + kalan));
if (kalan) { process.exit(1); }
