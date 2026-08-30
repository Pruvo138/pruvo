#!/usr/bin/env node
/**
 * PRUVO shop — TERK EDILMIS 'bekliyor' SUPURMESI KABUL KAPISI (K3xx, 30 Agu 2026).
 *
 *   node shop/test/terk-supurme.mjs
 *
 * OLCTUGU HUKUM (mimar karari 30 Agu 2026): kart akisinda `bekliyor` satiri ODEMEDEN ONCE
 * yazilir; musteri odeme sayfasini terk ederse satir sonsuza kadar `bekliyor` kalir ve
 * panelde gercek is bekleyen siparislerden AYIRT EDILEMEZ. Bunlari kapatan bir kol EKLENDI —
 * ama **KOR IPTAL YASAK**: her satir iyzico `retrieve` ile, `/donus` ile AYNI fonksiyondan
 * (`odemeHukmu`) DOGRULANIR. Kor iptal, odemis ama callback'i dusmemis musterinin parasini
 * gorunmez yapardi; bu evin "sessiz hata" sinifinin tam merkezi.
 *
 *   (a) ESIK       : 24 SAATTEN YENI 'bekliyor' -> DOKUNULMAZ (hic retrieve bile edilmez)
 *   (b) KURTARMA   : eski + retrieve 'odendi'   -> durum 'odendi' ve Purchase **BIR KEZ**
 *   (c) TERK       : eski + retrieve odenmemis  -> 'iptal' + gecmiste makine-okunur {"s":"terk"}
 *   (d) FAIL-CLOSED: eski + retrieve HATA       -> **DEGISMEDI** (yazma YOK), sayac ulasilamadi
 *   (e) HAVALE     : 'havale-bekliyor' eski olsa da DOKUNULMAZ (adi 'bekliyor' ile BITIYOR)
 *   (f) DOKUNULMAZ : 'odendi' / 'iptal' / 'uretimde' / 'incele' / 'basarisiz' -> DOKUNULMAZ
 *   (g) IDEMPOTENS : ayni supurme ikinci kez kosunca `degisen = 0`
 *   (h) YARIS      : musteri callback'i ile supurme AYNI satirda -> Purchase yine **BIR KEZ**
 *   (i) UYUSMAZLIK : para VAR ama tutar tutmuyor -> 'incele' (ASLA 'iptal') + Telegram
 *   (j) TEK SABIT  : esik tek yerde (TERK_ESIK_SAAT) + wrangler.toml'da [triggers] crons VAR
 *
 * NASIL (shop/test/olcum.mjs + havale-onay.mjs deseni — kopya uretim kodu YAZILMAZ):
 *   GERCEK `shop/src/index.js` import edilir ve **GERCEK `scheduled()` kolu** cagrilir; yani
 *   cron kablolamasi da olculur (kol hic bagli degilse bu dosya kirmizi yanar).
 *   D1 SAHTEDIR ama SQL'i YORUMLAR: WHERE/SET/ORDER BY/LIMIT kaynaktaki dizgeden okunur.
 *   Kisaltilmis bir taklit, tam da olcmek istedigimiz kosullari (durum beyaz listesi, CAS,
 *   esik karsilastirmasi) gorunmez yapardi.
 *   iyzico + Meta + GA4 + Telegram: `globalThis.fetch` STUB'lanir; GERCEK AG ISTEGI YOK.
 *
 * 🔴 FIKSTUR UYDURMADIR: gercek musteri verisi/telefon/adres/token bu dosyaya YAZILMAZ.
 * 🔴 CANLI D1'E DOKUNMAZ: hicbir wrangler/uzak cagri yoktur.
 *
 * ONCE-KIRMIZI KANITI (mutantlar, tools/terk-supurme-mutasyon.py — gecici AYNAYA uygulanir,
 * calisma agacina YAZMAZ):
 *   M1 HAVALE : SELECT beyaz listesi 'havale-bekliyor'u da alir -> (e) OLUR
 *   M2 KOR    : fail-closed dusurulur, retrieve hatasinda IPTAL edilir -> (d) OLUR
 *   M3 ESIK   : TERK_ESIK_SAAT 0'a duser (yeni satirlari da yakar)   -> (a) OLUR
 *   M4 IDEM   : 'odendi' CAS kosulu (durum <> 'odendi') kalkar       -> (h) OLUR
 *   K0 KONTROL: ilgisiz kol (tur tavani sayisi) degisir              -> HICBIRI OLMEZ
 *
 * CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (modul yuklenemedi).
 */

// ---- JSON IMPORT KOPRUSU (test altyapisi; uretim kodunu ETKILEMEZ) -------------
// Gerekce birebir shop/test/olcum.mjs'teki gibidir: index.js -> ../config.json ve
// semalar.js -> jenerator/urunler/*.json zinciri import attribute'suz alir; ciplak node
// duser. `module.register` (async loader hook) Node v20.6+'ta VAR -> CI'daki Node 20'de de
// kosar (surum dali BILEREK YOK).
import { register } from "node:module";
register("data:text/javascript," + encodeURIComponent(
  "export async function resolve(s, c, next) {" +
  "  const r = await next(s, c);" +
  "  if (r.url.endsWith('.json')) {" +
  "    return { ...r, format: 'json', importAttributes: { type: 'json' } }; }" +
  "  return r; }"));

import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const BURASI = path.dirname(url.fileURLToPath(import.meta.url));
const KOK = path.join(BURASI, "..", "..");
const req = createRequire(import.meta.url);
req(path.join(KOK, "secenekler.js"));

// Mutasyon harness'i gecici AYNAYA yazar ve bu degiskenle hedef gosterir.
const KAYNAK_YOL = process.env.PRUVO_INDEX_KAYNAK || path.join(BURASI, "..", "src", "index.js");
const TOML_YOL = process.env.PRUVO_SHOP_TOML || path.join(BURASI, "..", "wrangler.toml");

let MODUL = null;
let MODUL_HATA = "";
try {
  MODUL = await import(url.pathToFileURL(KAYNAK_YOL).href);
} catch (e) {
  MODUL_HATA = "index.js import: " + ((e && e.message) || e);
}
if (!MODUL) {
  console.error("❌ OLCULEMEDI — " + MODUL_HATA);
  process.exit(3);
}

let gecen = 0, kalan = 0;
const olen = new Set();
function ol(etiket, ad, kosul, detay) {
  if (kosul) { gecen++; console.log("  ✅ (" + etiket + ") " + ad); }
  else {
    kalan++; olen.add(etiket);
    console.log("  ❌ (" + etiket + ") " + ad + (detay ? " — " + detay : ""));
  }
}

// ================================================================ SAHTE D1 (SQL YORUMLAR)
//
// Kaynaktaki SQL dizgesini OKUR: `?` yer tutuculari soldan saga bind argumanlarina eslenir,
// WHERE `AND`/`OR` ile birlesen `<kolon> <op> <deger>` atomlarindan degerlendirilir, UPDATE'in
// SET listesi ve SELECT'in ORDER BY/LIMIT'i uygulanir. Kaynaktan bir kosul DUSERSE (mutant)
// burada da DUSER -> ilgili iddia kirmizi yanar. Kisaltma YAPILMAZ.

function isaretle(sql, arg) {
  // Her `?`'i sirayla «i» isaretine cevir; boylece atom degerlendirmesi konumdan bagimsiz olur.
  let i = 0;
  const isaretli = sql.replace(/\?/g, () => "«" + (i++) + "»");
  return { isaretli, coz: (jeton) => {
    const m = /^«(\d+)»$/.exec(jeton);
    if (m) { return arg[Number(m[1])]; }
    const l = /^'([^']*)'$/.exec(jeton);
    if (l) { return l[1]; }
    const n = Number(jeton);
    return Number.isNaN(n) ? jeton : n;
  } };
}

function ustDuzeydeBol(metin, ayirac) {
  const parcalar = [];
  let derinlik = 0, son = 0;
  for (let i = 0; i < metin.length; i++) {
    const k = metin[i];
    if (k === "(") { derinlik++; }
    else if (k === ")") { derinlik--; }
    else if (derinlik === 0 && metin.startsWith(ayirac, i)) {
      parcalar.push(metin.slice(son, i));
      i += ayirac.length - 1;
      son = i + 1;
    }
  }
  parcalar.push(metin.slice(son));
  return parcalar.map((p) => p.trim()).filter((p) => p.length);
}

/** Bir ifadeyi SARAN parantezleri soyar (icteki gruplama parantezlerine DOKUNMAZ). */
function parantezSoy(metin) {
  let a = metin.trim();
  while (a.startsWith("(") && a.endsWith(")")) {
    let derinlik = 0, sarici = true;
    for (let i = 0; i < a.length; i++) {
      if (a[i] === "(") { derinlik++; }
      else if (a[i] === ")") {
        derinlik--;
        if (derinlik === 0 && i < a.length - 1) { sarici = false; break; }
      }
    }
    if (!sarici) { break; }
    a = a.slice(1, -1).trim();
  }
  return a;
}

function atomDegerlendir(atom, satir, coz) {
  const a = parantezSoy(atom);
  const m = /^(\w+)\s*(<>|!=|>=|<=|=|<|>|LIKE)\s*(.+)$/i.exec(a);
  if (!m) { throw new Error("sahte D1: cozulemeyen WHERE atomu: " + atom); }
  const kolon = m[1];
  const op = m[2].toUpperCase();
  const beklenen = coz(m[3].trim());
  const gercek = satir[kolon];
  if (op === "=") { return gercek === beklenen; }
  if (op === "<>" || op === "!=") { return gercek !== beklenen; }
  if (op === "<") { return gercek < beklenen; }
  if (op === ">") { return gercek > beklenen; }
  if (op === "<=") { return gercek <= beklenen; }
  if (op === ">=") { return gercek >= beklenen; }
  if (op === "LIKE") {
    const kalip = new RegExp("^" + String(beklenen)
      .replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/%/g, ".*").replace(/_/g, ".") + "$");
    return kalip.test(String(gercek));
  }
  throw new Error("sahte D1: bilinmeyen operator: " + op);
}

function whereDegerlendir(whereMetni, satir, coz) {
  if (!whereMetni.trim()) { return true; }
  return ustDuzeydeBol(whereMetni, " AND ").every((ve) =>
    ustDuzeydeBol(parantezSoy(ve), " OR ").some((veya) => atomDegerlendir(veya, satir, coz)));
}

function bolumCek(sql, bas, sonlar) {
  const i = sql.toUpperCase().indexOf(bas.toUpperCase());
  if (i < 0) { return ""; }
  let son = sql.length;
  for (const s of sonlar) {
    const j = sql.toUpperCase().indexOf(s.toUpperCase(), i + bas.length);
    if (j >= 0 && j < son) { son = j; }
  }
  return sql.slice(i + bas.length, son);
}

function sahteD1(satirlar) {
  const izler = [];   // { tip, sql, satir, deger }
  return {
    izler,
    satirlar,
    prepare(sql) {
      return {
        bind(...arg) {
          const { isaretli, coz } = isaretle(sql, arg);
          const bas = isaretli.trim().slice(0, 6).toUpperCase();
          const where = bolumCek(isaretli, " WHERE ", [" ORDER BY ", " LIMIT "]);
          const eslesenler = () => satirlar.filter((s) => whereDegerlendir(where, s, coz));
          return {
            async first() {
              const e = eslesenler();
              return e.length ? { ...e[0] } : null;
            },
            async all() {
              let e = eslesenler();
              const sira = bolumCek(isaretli, " ORDER BY ", [" LIMIT "]).trim();
              if (sira) {
                const [kolon, yon] = sira.split(/\s+/);
                e = e.slice().sort((x, y) => (x[kolon] < y[kolon] ? -1 : x[kolon] > y[kolon] ? 1 : 0));
                if ((yon || "ASC").toUpperCase() === "DESC") { e.reverse(); }
              }
              const limit = bolumCek(isaretli, " LIMIT ", []).trim();
              if (limit) { e = e.slice(0, Number(coz(limit))); }
              return { results: e.map((s) => ({ ...s })), success: true };
            },
            async run() {
              if (bas !== "UPDATE") { return { meta: { changes: 0 } }; }
              const setKismi = bolumCek(isaretli, " SET ", [" WHERE "]);
              const atamalar = ustDuzeydeBol(setKismi, ",").map((p) => {
                const m = /^(\w+)\s*=\s*(.+)$/.exec(p.trim());
                return { kolon: m[1], deger: coz(m[2].trim()) };
              });
              const e = eslesenler();
              for (const s of e) {
                const deger = {};
                for (const a of atamalar) { s[a.kolon] = a.deger; deger[a.kolon] = a.deger; }
                izler.push({ tip: "UPDATE", sql: sql, siparis_no: s.siparis_no, deger });
              }
              return { meta: { changes: e.length } };
            },
          };
        },
      };
    },
  };
}

// ================================================================ FIKSTURLER (UYDURMA)

const SAAT = 3600 * 1000;
const SIMDI = Date.parse("2026-08-30T12:00:00.000Z");

// 682,90 TL tahsilat = 432,90 urun + 250,00 kargo (olcum.mjs ile ayni sayilar).
const URUN_KURUS = 43290, KARGO_KURUS = 25000, KDV_KURUS = 11381;
const PAID = "682.9";

function satirYap(no, durum, yasSaat, ek) {
  return Object.assign({
    siparis_no: no,
    token: "uydurma-token-" + no,
    tarih: new Date(SIMDI - yasSaat * SAAT).toISOString(),
    durum: durum,
    durum_gecmisi: "",
    tutar_kurus: URUN_KURUS, kargo_kurus: KARGO_KURUS, kdv_kurus: KDV_KURUS,
    odeme_yontemi: "kart",
    iyzico_odeme_id: null,
    urunler: JSON.stringify([
      { id: "uydurma-parca", baslik: "Uydurma Parça", kategori: "Tamirat",
        adet: 2, birim_kurus: 21645, tutar_kurus: URUN_KURUS },
    ]),
    // fbp VAR -> Meta riza kapisi acik (Purchase gercekten POST edilir, sayilabilir).
    atif: JSON.stringify({ ga_client_id: "1.1", fbp: "fb.1.1.uydurma", fbc: "fb.1.1.uydurma" }),
    musteri_ad: "Test Musteri", musteri_tel: "05000000000",
    musteri_eposta: "test@ornek.invalid", musteri_adres: "Ornek Mah. No:1",
    musteri_notu: "",
  }, ek || {});
}

const ENV_TABAN = {
  IYZICO_BASE_URL: "https://iyzico-mock.invalid",
  IYZICO_API_KEY: "uydurma-api", IYZICO_SECRET_KEY: "uydurma-secret",
  SITE_URL: "https://pruvo3d.invalid",
  TELEGRAM_TOKEN: "uydurma-telegram", TELEGRAM_CHAT: "0",
  TELEGRAM_API: "https://telegram-mock.invalid",
  META_PIXEL_ID: "1", META_CAPI_TOKEN: "uydurma-capi",
  GA4_MEASUREMENT_ID: "G-UYDURMA", GA4_API_SECRET: "uydurma-ga4",
  BILDIRIM_EPOSTA: "",              // e-posta kolu sessiz kalsin (RESEND_API_KEY de yok)
};

/** iyzico retrieve cevaplari — TEK yerde, senaryolar buradan secilir. */
const DETAY = {
  odendi: (no) => ({ status: "success", paymentStatus: "SUCCESS", paidPrice: PAID,
                     conversationId: no, basketId: no, paymentId: "PAY-" + no }),
  odenmemis: () => ({ status: "success", paymentStatus: "FAILURE", paidPrice: "0" }),
  altyapiHatasi: () => ({ status: "failure", errorCode: "1001", errorMessage: "uydurma hata" }),
  tutarsiz: (no) => ({ status: "success", paymentStatus: "SUCCESS", paidPrice: "1.00",
                       conversationId: no, basketId: no, paymentId: "PAY-" + no }),
};

/**
 * Kosum ortami: sahte D1 + STUB fetch (iyzico/Meta/GA4/Telegram) + ctx.
 * `detayCoz(token)` -> hangi satira hangi retrieve cevabinin donecegini belirler.
 */
function ortamKur(satirlar, detayCoz) {
  const db = sahteD1(satirlar);
  const cagrilar = [];
  const eskiFetch = globalThis.fetch;
  globalThis.fetch = async (u, opt) => {
    const adres = String(u);
    let govde = null;
    try { govde = opt && opt.body ? JSON.parse(opt.body) : null; } catch (e) { govde = null; }
    cagrilar.push({ url: adres, govde });
    if (adres.indexOf("iyzico-mock") >= 0) {
      const t = govde && govde.token;
      return { status: 200, text: async () => JSON.stringify(detayCoz(t)) };
    }
    return { status: 200, text: async () => "{\"events_received\":1}",
             json: async () => ({ events_received: 1 }) };
  };
  const bekleyenler = [];
  const ctx = { waitUntil(p) { bekleyenler.push(Promise.resolve(p).catch(() => {})); } };
  const env = { ...ENV_TABAN, KATALOG: db };
  return {
    db, env, ctx, cagrilar,
    async bitir() {
      await Promise.all(bekleyenler);
      globalThis.fetch = eskiFetch;
    },
    purchaseSayisi() {
      return cagrilar.filter((c) => c.url.indexOf("graph.facebook.com") >= 0 ||
                                    c.url.indexOf("google-analytics.com") >= 0).length;
    },
    metaSayisi() { return cagrilar.filter((c) => c.url.indexOf("graph.facebook.com") >= 0).length; },
    retrieveSayisi() { return cagrilar.filter((c) => c.url.indexOf("iyzico-mock") >= 0).length; },
    /** Bu TOKEN icin iyzico'ya HIC gidildi mi? — "dokunulmazlik"in en erken kanitidir:
     *  satirin durumu degismese bile, SECILMIS olmak kapsam ihlalidir. */
    retrieveDenendiMi(token) {
      return cagrilar.some((c) => c.url.indexOf("iyzico-mock") >= 0 &&
                                  c.govde && c.govde.token === token);
    },
    telegramSayisi() { return cagrilar.filter((c) => c.url.indexOf("telegram-mock") >= 0).length; },
  };
}

function bul(satirlar, no) { return satirlar.find((s) => s.siparis_no === no); }

function gecmisKayitlari(satir) {
  try { return JSON.parse(satir.durum_gecmisi || "[]") || []; } catch (e) { return []; }
}

// ================================================================ 1) ANA SUPURME TURU
//
// Tek turda TUM siniflar birlikte kosar: supurme satirlari BIRLIKTE gordugunde de dogru
// ayirmali (tek tek verilen fikstur, beyaz liste hatasini gizleyebilirdi).

console.log("\n--- 1) ANA TUR: esik + kurtarma + terk + fail-closed + dokunulmazlar ---");
{
  const satirlar = [
    satirYap("PR-TEST-A-YENI", "bekliyor", 1),                  // (a) 1 SAATLIK
    satirYap("PR-TEST-B-ODENDI", "bekliyor", 30),               // (b) 30 SAATLIK, odenmis
    satirYap("PR-TEST-C-TERK", "bekliyor", 30),                 // (c) 30 SAATLIK, odenmemis
    satirYap("PR-TEST-D-HATA", "bekliyor", 30),                 // (d) 30 SAATLIK, retrieve HATA
    satirYap("PR-TEST-E-HAVALE", "havale-bekliyor", 200),       // (e) 200 SAATLIK havale
    satirYap("PR-TEST-F1-ODENDI", "odendi", 200),               // (f)
    satirYap("PR-TEST-F2-IPTAL", "iptal", 200),                 // (f)
    satirYap("PR-TEST-F3-URETIM", "uretimde", 200),             // (f)
    satirYap("PR-TEST-F4-INCELE", "incele", 200),               // (f)
    satirYap("PR-TEST-F5-BASARISIZ", "basarisiz", 200),         // (f)
  ];
  const oncekiDurumlar = new Map(satirlar.map((s) => [s.siparis_no, s.durum]));
  const o = ortamKur(satirlar, (token) => {
    if (String(token).indexOf("B-ODENDI") >= 0) { return DETAY.odendi("PR-TEST-B-ODENDI"); }
    if (String(token).indexOf("C-TERK") >= 0) { return DETAY.odenmemis(); }
    if (String(token).indexOf("D-HATA") >= 0) { return DETAY.altyapiHatasi(); }
    // 🔴 KAPSAM DISI satirlar icin BILEREK "odenmemis" donulur: kapsam genislerse satir
    // yalnizca SECILMEKLE kalmaz, IPTAL'e giderdi. "altyapi hatasi" dondurmek fail-closed
    // kolu sayesinde hasari GIZLERDI ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]] sinifi).
    return DETAY.odenmemis();
  });

  await MODUL.default.scheduled({ scheduledTime: SIMDI }, o.env, o.ctx);
  await o.bitir();

  // (a) ESIK
  const a = bul(satirlar, "PR-TEST-A-YENI");
  ol("a", "24 saatten YENI 'bekliyor' DOKUNULMADI", a.durum === "bekliyor", "durum=" + a.durum);
  ol("a", "YENI satirin token'i icin retrieve HIC DENENMEDI (secilmedi bile)",
    !o.retrieveDenendiMi(a.token), "retrieve-toplam=" + o.retrieveSayisi());

  // (b) PARA KURTARMA
  const b = bul(satirlar, "PR-TEST-B-ODENDI");
  ol("b", "eski + retrieve ODENDI -> durum 'odendi'", b.durum === "odendi", "durum=" + b.durum);
  ol("b", "iyzico odeme id kaydedildi", b.iyzico_odeme_id === "PAY-PR-TEST-B-ODENDI",
    String(b.iyzico_odeme_id));
  ol("b", "Purchase olcumu BIR KEZ gitti (Meta 1)", o.metaSayisi() === 1,
    "meta=" + o.metaSayisi());
  ol("b", "gecmiste 'odendi' + olcum izi {\"o\":1} var",
    gecmisKayitlari(b).some((k) => k.d === "odendi" && k.o === 1),
    b.durum_gecmisi);

  // (c) TERK
  const c = bul(satirlar, "PR-TEST-C-TERK");
  ol("c", "eski + retrieve ODENMEMIS -> durum 'iptal'", c.durum === "iptal", "durum=" + c.durum);
  ol("c", "gecmiste MAKINE-OKUNUR sebep {\"d\":\"iptal\",\"s\":\"terk\"}",
    gecmisKayitlari(c).some((k) => k.d === "iptal" && k.s === "terk"), c.durum_gecmisi);
  ol("c", "terk iptalinde Purchase GITMEDI (toplam olcum POST'u yalniz b'nin)",
    o.purchaseSayisi() === 2, "olcum-post=" + o.purchaseSayisi());

  // (d) FAIL-CLOSED
  const d = bul(satirlar, "PR-TEST-D-HATA");
  ol("d", "retrieve ULASILAMADI -> durum DEGISMEDI ('bekliyor')",
    d.durum === "bekliyor", "durum=" + d.durum);
  ol("d", "retrieve ULASILAMADI -> gecmise de YAZILMADI", d.durum_gecmisi === "", d.durum_gecmisi);
  ol("d", "retrieve hatasi olan satira HIC UPDATE gitmedi",
    !db_izVar(o.db, "PR-TEST-D-HATA"), "izler=" + JSON.stringify(o.db.izler.map((i) => i.siparis_no)));

  // (e) HAVALE — 'bekliyor' ile BITEN ad tuzagi
  const e = bul(satirlar, "PR-TEST-E-HAVALE");
  ol("e", "200 saatlik 'havale-bekliyor' DOKUNULMADI", e.durum === "havale-bekliyor",
    "durum=" + e.durum);
  ol("e", "'havale-bekliyor' satirina HIC UPDATE gitmedi", !db_izVar(o.db, "PR-TEST-E-HAVALE"));
  ol("e", "'havale-bekliyor' token'i icin retrieve BILE DENENMEDI (kapsam disi)",
    !o.retrieveDenendiMi(e.token), "retrieve-toplam=" + o.retrieveSayisi());

  // (f) DIGER DOKUNULMAZLAR
  for (const no of ["PR-TEST-F1-ODENDI", "PR-TEST-F2-IPTAL", "PR-TEST-F3-URETIM",
                    "PR-TEST-F4-INCELE", "PR-TEST-F5-BASARISIZ"]) {
    const s = bul(satirlar, no);
    ol("f", no + " DOKUNULMADI", s.durum === oncekiDurumlar.get(no), "durum=" + s.durum);
    ol("f", no + " icin retrieve BILE DENENMEDI", !o.retrieveDenendiMi(s.token));
  }

  // (g) IDEMPOTENS — ikinci tur
  const o2 = ortamKur(satirlar, () => DETAY.altyapiHatasi());
  await MODUL.default.scheduled({ scheduledTime: SIMDI }, o2.env, o2.ctx);
  await o2.bitir();
  ol("g", "ikinci tur: 'odendi'/'iptal' olan satirlar artik SECILMIYOR (yalniz D kaldi)",
    o2.retrieveSayisi() === 1, "retrieve=" + o2.retrieveSayisi());
  ol("g", "ikinci turda hicbir UPDATE yazilmadi (degisen=0)",
    o2.db.izler.length === 0, JSON.stringify(o2.db.izler.map((i) => i.siparis_no)));
  ol("g", "ikinci turda Purchase TEKRARLANMADI", o2.purchaseSayisi() === 0,
    "olcum-post=" + o2.purchaseSayisi());
}

function db_izVar(db, no) { return db.izler.some((i) => i.siparis_no === no); }

// ================================================================ 2) SAYAC SOZLESMESI

console.log("\n--- 2) SAYAC: terkSupur() donusu ---");
{
  const satirlar = [
    satirYap("PR-TEST-S1", "bekliyor", 30),
    satirYap("PR-TEST-S2", "bekliyor", 30),
    satirYap("PR-TEST-S3", "bekliyor", 30),
    satirYap("PR-TEST-S4", "bekliyor", 1),
    satirYap("PR-TEST-S5", "havale-bekliyor", 30),
  ];
  const o = ortamKur(satirlar, (t) => {
    if (String(t).indexOf("S1") >= 0) { return DETAY.odendi("PR-TEST-S1"); }
    if (String(t).indexOf("S2") >= 0) { return DETAY.odenmemis(); }
    return DETAY.altyapiHatasi();
  });
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();
  ol("s", "bakilan = 3 (yalniz eski 'bekliyor')", r.bakilan === 3, JSON.stringify(r));
  ol("s", "odendi = 1", r.odendi === 1, JSON.stringify(r));
  ol("s", "iptal = 1", r.iptal === 1, JSON.stringify(r));
  ol("s", "ulasilamadi = 1", r.ulasilamadi === 1, JSON.stringify(r));
  ol("s", "degisen = 2 (odendi + iptal)", r.degisen === 2, JSON.stringify(r));
  ol("s", "esik_saat sayaca RAPORLANIR", r.esik_saat === MODUL.TERK_ESIK_SAAT, JSON.stringify(r));
  // 🔒 GIZLILIK: sayac Cloudflare Logs'a basilir. Metin tasiyan TEK alan `esik` (ISO damgasi);
  // geri kalan HER alan SAYIDIR. Boylece ad/tel/eposta/adres/token/siparis_no yapisal olarak
  // giremez — "PII kelimesi arama" degil, ALAN TIPI kapisi.
  const metinAlanlar = Object.entries(r).filter(([, v]) => typeof v !== "number").map(([k]) => k);
  ol("s", "sayacin metin tasiyan TEK alani 'esik' (kalan hepsi SAYI)",
    JSON.stringify(metinAlanlar) === JSON.stringify(["esik"]), JSON.stringify(metinAlanlar));
  ol("s", "'esik' salt ISO damgasidir (kisisel veri tasiyamaz)",
    /^\d{4}-\d{2}-\d{2}T[\d:.]+Z$/.test(r.esik), String(r.esik));

  // Ikinci tur AYNI ortamda: degisen = 0 (mimarin ④ maddesi, sayac ekseninden)
  const o2 = ortamKur(satirlar, () => DETAY.altyapiHatasi());
  const r2 = await MODUL.terkSupur(o2.env, o2.ctx, SIMDI);
  await o2.bitir();
  ol("g", "ikinci supurmede degisen = 0", r2.degisen === 0, JSON.stringify(r2));
}

// ================================================================ 3) YARIS: callback + cron
//
// M4 hedefi. Musteri callback'i ile cron supurmesi AYNI satirda kosar; Purchase yalniz
// BIR KEZ gitmelidir. Koruma `odemeHukmu`nun CAS'idir (UPDATE ... AND durum <> 'odendi').

console.log("\n--- 3) YARIS: /donus callback'i ile supurme AYNI satirda ---");
{
  const no = "PR-TEST-YARIS";
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.odendi(no));

  // Once musteri callback'i (gercek /donus yolu), sonra cron turu.
  const istek = new Request("https://pruvo3d.invalid/api/shop/donus", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": "203.0.113.9",
               "User-Agent": "UydurmaTarayici/1" },
    body: JSON.stringify({ token: satirlar[0].token }),
  });
  await MODUL.default.fetch(istek, o.env, o.ctx);
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();

  ol("h", "callback sonrasi durum 'odendi'", satirlar[0].durum === "odendi", satirlar[0].durum);
  ol("h", "supurme o satiri ARTIK SECMEDI (bakilan=0)", r.bakilan === 0, JSON.stringify(r));
  ol("h", "Purchase TOPLAM BIR KEZ gitti (Meta 1)", o.metaSayisi() === 1,
    "meta=" + o.metaSayisi());
  ol("h", "gecmiste TEK 'odendi' kaydi var",
    gecmisKayitlari(satirlar[0]).filter((k) => k.d === "odendi").length === 1,
    satirlar[0].durum_gecmisi);
}

// TERS SIRA: once cron, sonra callback. Ayni garanti.
{
  const no = "PR-TEST-YARIS2";
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.odendi(no));
  await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  const istek = new Request("https://pruvo3d.invalid/api/shop/donus", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: satirlar[0].token }),
  });
  const cevap = await MODUL.default.fetch(istek, o.env, o.ctx);
  await o.bitir();
  ol("h", "ters sira: durum 'odendi'", satirlar[0].durum === "odendi", satirlar[0].durum);
  ol("h", "ters sira: Purchase yine BIR KEZ (Meta 1)", o.metaSayisi() === 1,
    "meta=" + o.metaSayisi());
  ol("h", "ters sira: gec kalan callback bilet VERMEZ (idempotent donus)",
    String(cevap.headers.get("Location") || "").indexOf("bilet=") < 0,
    String(cevap.headers.get("Location") || ""));
}

// ================================================================ 4) UYUSMAZLIK: iptal DEGIL

console.log("\n--- 4) UYUSMAZLIK: para VAR, tutar tutmuyor -> 'incele' (ASLA 'iptal') ---");
{
  const no = "PR-TEST-UYUSMAZ";
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.tutarsiz(no));
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();
  ol("i", "tutar uyusmazliginda durum 'incele'", satirlar[0].durum === "incele", satirlar[0].durum);
  ol("i", "🔴 ASLA 'iptal' degil", satirlar[0].durum !== "iptal", satirlar[0].durum);
  ol("i", "sayacta incele=1, iptal=0", r.incele === 1 && r.iptal === 0, JSON.stringify(r));
  ol("i", "Telegram uyarisi GITTI", o.telegramSayisi() === 1, "tg=" + o.telegramSayisi());
  ol("i", "tutar guvenilmezken Purchase GITMEDI", o.purchaseSayisi() === 0,
    "olcum-post=" + o.purchaseSayisi());
}

// ================================================================ 5) TOKENSIZ SATIR

console.log("\n--- 5) TOKENSIZ eski 'bekliyor' -> fail-closed ---");
{
  const satirlar = [satirYap("PR-TEST-TOKENSIZ", "bekliyor", 30, { token: null })];
  const o = ortamKur(satirlar, () => DETAY.odenmemis());
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();
  ol("d", "token YOKSA dogrulama yapilamaz -> DOKUNULMAZ",
    satirlar[0].durum === "bekliyor", satirlar[0].durum);
  ol("d", "tokensiz sayaci artar, iptal=0", r.tokensiz === 1 && r.iptal === 0, JSON.stringify(r));
  ol("d", "tokensiz satir icin retrieve DENENMEDI", o.retrieveSayisi() === 0);
}

// ================================================================ 6) TEK SABIT + CRON KABLOSU

console.log("\n--- 6) TEK SABIT + cron kablolamasi ---");
{
  const kaynak = fs.readFileSync(KAYNAK_YOL, "utf8");
  ol("j", "esik DISA ACIK TEK SABIT (TERK_ESIK_SAAT)",
    typeof MODUL.TERK_ESIK_SAAT === "number" && MODUL.TERK_ESIK_SAAT > 0,
    String(MODUL.TERK_ESIK_SAAT));
  // "koda serpme" yasagi: esik SAYISI yalniz sabitin TANIMINDA gecmeli; supurme govdesi
  // sabiti ADIYLA okumali. `24` sayisinin `* 3600 * 1000` gibi bir hesapta ikinci kez
  // gorunmesi tam da yasaklanan sey olurdu.
  const esikTanimi = new RegExp("TERK_ESIK_SAAT\\s*=\\s*" + MODUL.TERK_ESIK_SAAT + "\\s*;");
  ol("j", "esik sabiti kaynakta TANIMLI", esikTanimi.test(kaynak));
  const govde = kaynak.slice(kaynak.indexOf("export async function terkSupur"));
  ol("j", "supurme govdesi esigi ADIYLA okur (sayi GOMULU DEGIL)",
    govde.indexOf("TERK_ESIK_SAAT") >= 0 &&
    !new RegExp("[^_a-zA-Z0-9]" + MODUL.TERK_ESIK_SAAT + "\\s*\\*").test(govde));
  ol("j", "'havale-bekliyor' supurme govdesinde HEDEF olarak GECMEZ",
    !/durum\s*=\s*'havale-bekliyor'/.test(govde) &&
    govde.indexOf("\"havale-bekliyor\"") < 0);
  ol("j", "scheduled (cron) kolu BAGLI", typeof MODUL.default.scheduled === "function");

  const toml = fs.readFileSync(TOML_YOL, "utf8");
  ol("j", "wrangler.toml'da [triggers] blogu VAR", /^\s*\[triggers\]\s*$/m.test(toml));
  const cronSatiri = /^\s*crons\s*=\s*\[([^\]]*)\]/m.exec(toml);
  ol("j", "crons listesi TANIMLI ve BOS DEGIL", !!cronSatiri && cronSatiri[1].trim().length > 0,
    cronSatiri ? cronSatiri[1] : "yok");
  // Siklik DUSUK tutulmali: dakikalik cron D1 yazma kotasini bosuna yakar.
  ol("j", "cron siklıgı dakikalik DEGIL (ilk alan '*' degil)",
    !!cronSatiri && !/["']\s*\*\s+/.test(cronSatiri[1]), cronSatiri ? cronSatiri[1] : "yok");
}

// ================================================================ SONUC

console.log("\n=== SONUC: " + gecen + " gecti / " + kalan + " kaldi ===");
console.log("OLEN_IDDIALAR=" + (olen.size ? [...olen].sort().join(",") : "-"));
process.exit(kalan ? 1 : 0);
