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
 * K358 (31 Agu 2026) — UCUNCU SINIF. Yukaridaki (c) kolu CANLIDA HIC KOSMADI: `odemeHukmu`
 * IKI KOVALIYDI ve iyzico CEVAP VERDIGI halde (`status:"failure"` + dolu `errorCode`) hukum
 * fail-closed 'altyapi-hatasi' kovasina dusuyordu (canli olcum: 5/5 `ulasilamadi`, dagilim
 * 5122x3 / 10057 / 10054, `degisen=0`). Uc yeni eksen:
 *   (k) KESIN-BAS.  : KAPALI kumedeki kod (5122/10054/10057) -> 'iptal' + {"s":"terk"}
 *   (q) EMNIYET     : 🔴 kume DISINDA kalan HER SEY fail-closed — bilinmeyen kod, bos kod,
 *                     taninmayan `status`, `det` yoklugu. Kor iptal YASAK; islerin kalbi bu.
 *   (r) IKINCI TUK. : `/donus` (canli musteri yolu) da AYNI yuklemi kullanir — kesin-basarisiz
 *                     'basarisiz' yazar ve Telegram GITMEZ; gercek altyapi hatasi ve
 *                     `uyusmazlik` kollari AYNEN 'incele' + Telegram olarak durur.
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
  // K358: iyzico CEVAP VERDI ve basarisizligi KENDISI beyan etti; kod KAPALI kumede.
  kesinBasarisiz: (kod) => ({ status: "failure", errorCode: kod,
                              errorMessage: "uydurma iyzico basarisiz cevabi" }),
  // Kume DISI ama ayni sekilde "cevap veren failure": kor iptal edilmemeli.
  bilinmeyenKod: () => ({ status: "failure", errorCode: "9999",
                          errorMessage: "uydurma bilinmeyen hata" }),
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
  // SUNUCU LOGU YAKALAMA (K356): uretim kodunun Cloudflare Logs'a BASTIGI satirlar.
  // TEE'dir, yutma DEGIL — test kendi ciktisini basmaya devam eder; yutulsaydi bu dosyanin
  // kendi ✅/❌ satirlari da kaybolurdu.
  const satirLoglari = [];
  const eskiLog = console.log, eskiHata = console.error;
  console.log = (...a) => { satirLoglari.push(a.join(" ")); eskiLog(...a); };
  console.error = (...a) => { satirLoglari.push(a.join(" ")); eskiHata(...a); };
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
      console.log = eskiLog; console.error = eskiHata;
    },
    /** Uretim kodunun bastigi TUM log satirlari (test kendi ✅/❌ satirlarini da yazar —
     *  onlar `bitir()`den SONRA basildigi icin bu diziye girmez). */
    loglar() { return satirLoglari.slice(); },
    /** `olcum {...}` satirlari, JSON'u COZULMUS halde. Bicim bozuksa `bozuk:true` doner —
     *  "parse edilemedi" ile "alan yok" ayni goruntuye cokmesin. */
    olcumKayitlari() {
      return satirLoglari.filter((s) => s.startsWith("olcum ")).map((s) => {
        try { return JSON.parse(s.slice("olcum ".length)); }
        catch (e) { return { bozuk: true, ham: s }; }
      });
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

// ================================================================ 7) (n) NEDEN LOGU
//
// K356 (mimar emri 31 Agu 2026): cron supurmesi UC ardisik turda `degisen=0` verdi, aged
// 'bekliyor' satirlari icin acilan TEK kol 'altyapi-hatasi' oldu ve fail-closed oldugu icin
// HICBIR SEY yazmadi. `odemeHukmu` retrieve cevabini `det` olarak ELDE TUTUYOR ama loga
// yazmiyordu -> "iyzico checkout token omru esikten KISA (yapisal)" ile "gecici iyzico
// arizasi" AYIRT EDILEMIYOR. 5 siparis / 4.160 TL bu ayrimin arkasinda bekliyor.
//
// 🔴 OLCUT DAVRANISTIR, DIZGE DEGIL: iddialar uretim kodunun GERCEKTEN BASTIGI satiri
// (yakalanan console ciktisi) okur; kaynakta "errorCode" kelimesi ARANMAZ — o, kolu hic
// kosmadan yesil yakan bir dizge testi olurdu ([[n2b-kapisi-dizge-olcer]]).

console.log("\n--- 7) (n) NEDEN LOGU: retrieve hatasinda errorCode + errorMessage ---");
{
  const no = "PR-TEST-NEDEN";
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.altyapiHatasi());
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();

  const kayitlar = o.olcumKayitlari();
  const hata = kayitlar.find((k) => k.atlandi === "retrieve-hatasi");
  ol("n", "retrieve hatasinda 'retrieve-hatasi' olcum satiri BASILDI", !!hata,
    "olcum-satiri=" + kayitlar.length);
  ol("n", "satirin bicimi BOZULMADI (tek satir JSON, parse edildi)",
    !!hata && hata.bozuk !== true, JSON.stringify(hata));
  ol("n", "🔴 errorCode LOGLANDI ve iyzico'nun DONDURDUGU kod (1001)",
    !!hata && String(hata.errorCode) === "1001", String(hata && hata.errorCode));
  ol("n", "🔴 errorMessage LOGLANDI ve iyzico'nun DONDURDUGU metin",
    !!hata && String(hata.errorMessage) === "uydurma hata", String(hata && hata.errorMessage));
  ol("n", "🔴 siparis_no AYNI satirda (hangi siparis oldugu okunur)",
    !!hata && hata.siparis_no === no, String(hata && hata.siparis_no));
  ol("n", "sayac hala fail-closed: ulasilamadi=1, degisen=0", r.ulasilamadi === 1 && r.degisen === 0,
    JSON.stringify(r));
  ol("n", "🔴 IKINCI LOG BICIMI ACILMADI: uretimin bastigi her satir bilinen bir etiketle "
    + "baslar (olcum / terk-supurme / terk supurmesi)",
    o.loglar().every((s) => s.startsWith("olcum ") || s.startsWith("terk-supurme ") ||
                            s.startsWith("terk supurmesi ")),
    JSON.stringify(o.loglar().filter((s) => !s.startsWith("olcum ") &&
      !s.startsWith("terk-supurme ") && !s.startsWith("terk supurmesi "))));
  ol("n", "sayac satiri (terk-supurme {...}) YERINDE DURUYOR — ikinci bicim onun YERINI ALMADI",
    o.loglar().some((s) => s.startsWith("terk-supurme ")));
}

// `det` BOSKEN de satir BASILIR — sessiz bos satir yasak. Ucu de AYRI hal:
//   (1) errorCode/errorMessage alanlari BOS, (2) govde bos nesne, (3) alanlar HIC YOK.
// Ucu de tek bir varsayilan kovaya ("YOK") DUSER ama satirin KENDISI kaybolmaz — "alan
// yoktu" ile "kol hic kosmadi" ayni goruntuye cokmesin ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
{
  const haller = [
    ["bos-degerler", { status: "failure", errorCode: "", errorMessage: "" }],
    ["bos-govde", { status: "failure" }],
    ["status-yok", {}],
  ];
  for (const [ad, det] of haller) {
    const no = "PR-TEST-BOSDET-" + ad;
    const satirlar = [satirYap(no, "bekliyor", 30)];
    const o = ortamKur(satirlar, () => det);
    const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
    await o.bitir();
    const hata = o.olcumKayitlari().find((k) => k.atlandi === "retrieve-hatasi");
    ol("n", "det=" + ad + ": satir yine BASILDI (sessiz bosluk YOK)", !!hata,
      JSON.stringify(o.loglar()));
    ol("n", "det=" + ad + ": errorCode='YOK' (bicim bozulmadi, alan DUSMEDI)",
      !!hata && hata.errorCode === "YOK", String(hata && hata.errorCode));
    ol("n", "det=" + ad + ": errorMessage='YOK'",
      !!hata && hata.errorMessage === "YOK", String(hata && hata.errorMessage));
    ol("n", "det=" + ad + ": siparis_no yine YERINDE", !!hata && hata.siparis_no === no);
    ol("n", "det=" + ad + ": fail-closed korundu (ulasilamadi=1, yazma YOK)",
      r.ulasilamadi === 1 && o.db.izler.length === 0, JSON.stringify(r));
  }
}

// GURULTU KAPISI: basarili/odenmis turda bu kol HIC basmamali.
{
  const no = "PR-TEST-SESSIZ";
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.odendi(no));
  await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();
  const kayitlar = o.olcumKayitlari();
  ol("n", "🔴 ODENMIS turda 'retrieve-hatasi' satiri BASILMADI",
    !kayitlar.some((k) => k.atlandi === "retrieve-hatasi"), JSON.stringify(kayitlar));
  ol("n", "🔴 ODENMIS turda HICBIR satirda errorCode/errorMessage GECMEZ (gurultu yok)",
    !kayitlar.some((k) => "errorCode" in k || "errorMessage" in k), JSON.stringify(kayitlar));
}

// ================================================================ 8) (p) GIZLILIK — NEGATIF
//
// 🔴 Bu kol hata logu ciktisinda YEDI+BIR adin HIC gecmedigini AYRI AYRI arar. Fikstur
// bilerek AYIRT EDICI degerler tasir: "1.1" gibi kisa bir deger sahte-yesil verirdi
// (baska bir sayinin icinde gecebilirdi) — negatif iddia, ARANAN degerin ciktida
// gecebilecegi bir bicimde kurulmazsa hicbir sey olcmez.

console.log("\n--- 8) (p) GIZLILIK: hata logunda kisisel kolon / atif kimligi / token YOK ---");
{
  const no = "PR-TEST-GIZLILIK";
  const PII = {
    musteri_ad: "PIIADXQ-Ayse Yilmaz",
    musteri_tel: "PIITELXQ-05321234567",
    musteri_eposta: "PIIEPOSTAXQ@ornek.invalid",
    musteri_adres: "PIIADRESXQ Cumhuriyet Mah. 12/3",
    musteri_notu: "PIINOTXQ kapida teslim",
    atif: JSON.stringify({ ga_client_id: "PIIGAXQ-9.9", fbp: "PIIFBPXQ.fb.1", fbc: "PIIFBCXQ.fb.1" }),
    token: "PIITOKENXQ-uydurma-odeme-token-0123456789",
  };
  const satirlar = [satirYap(no, "bekliyor", 30, PII)];
  // iyzico HAM govdeyi echo ediyor gibi davran: errorMessage'in ICINE token'i koy.
  // `istek()` JSON parse edemedigi cevapta tam da bunu yapar (metin.slice(0,300)).
  const o = ortamKur(satirlar, (t) => ({
    status: "failure", errorCode: "HTTP-400",
    errorMessage: 'Bad Request: {"locale":"tr","token":"' + t + '"}',
  }));
  await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();

  const cikti = o.loglar().join("\n");
  ol("p", "hata satiri GERCEKTEN basildi (negatif iddia BOS ciktida sahte-yesil vermesin)",
    o.olcumKayitlari().some((k) => k.atlandi === "retrieve-hatasi"), cikti);

  // SEKIZ AD, AYRI AYRI (spec'in yedisi + `musteri_notu`; superset BILEREK).
  const YASAKLI = [
    ["musteri_ad", PII.musteri_ad],
    ["musteri_tel", PII.musteri_tel],
    ["musteri_eposta", PII.musteri_eposta],
    ["musteri_adres", PII.musteri_adres],
    ["musteri_notu", PII.musteri_notu],
    ["fbp", "PIIFBPXQ.fb.1"],
    ["fbc", "PIIFBCXQ.fb.1"],
    ["ga_client_id", "PIIGAXQ-9.9"],
    ["token", PII.token],
  ];
  for (const [ad, deger] of YASAKLI) {
    ol("p", "🔒 " + ad + " degeri hata logunda HIC GECMEZ",
      cikti.indexOf(deger) < 0,
      cikti.slice(Math.max(0, cikti.indexOf(deger) - 60), cikti.indexOf(deger) + 60));
  }
  // Ayirt edici damganin KENDISI de hicbir yerde olmamali (alan adi degisse de yakalar).
  ol("p", "🔒 fikstur PII damgasi ('XQ') ciktinin HICBIR YERINDE yok",
    cikti.indexOf("XQ") < 0, cikti.slice(0, 400));
  // Token maskesi GERCEKTEN calisti mi — yoksa yukaridaki 'token yok' iddiasi, satirin
  // hic basilmamis olmasindan da yesil yanabilirdi.
  const h = o.olcumKayitlari().find((k) => k.atlandi === "retrieve-hatasi");
  ol("p", "errorMessage YAZILDI ama token'in yerinde maske var",
    !!h && String(h.errorMessage).indexOf("***") >= 0, String(h && h.errorMessage));
  ol("p", "errorCode teknik kod olarak GECTI (HTTP-400)",
    !!h && h.errorCode === "HTTP-400", String(h && h.errorCode));
}

// ================================================================ 9) (k) KESIN-BASARISIZ: POZITIF
//
// K358 (mimar emri 31 Agu 2026): `odemeHukmu` IKI KOVALIYDI; iyzico CEVAP VERDIGI halde
// (`status:"failure"` + dolu `errorCode`) hukum 'altyapi-hatasi' kovasina dusuyor, o kova
// fail-closed oldugu icin terk supurmesinin ZATEN VAR OLAN `iptal` kolu HIC KOSMUYORDU
// (canli olcum: 5/5 `ulasilamadi`, dagilim 5122x3 / 10057 / 10054, `degisen=0`).
// Burada UCUNCU SINIF ADIYLA olculur: KAPALI kumedeki kod -> 'iptal' + {"s":"terk"}.

console.log("\n--- 9) (k) KESIN-BASARISIZ kod -> 'iptal' (kapali kumenin UC uyesi) ---");
for (const kod of ["5122", "10054", "10057"]) {
  const no = "PR-TEST-KESIN-" + kod;
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.kesinBasarisiz(kod));
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();

  const s = satirlar[0];
  ol("k", kod + ": iyzico 'failure' beyan etti + kod KAPALI kumede -> durum 'iptal'",
    s.durum === "iptal", "durum=" + s.durum);
  ol("k", kod + ": gecmiste MAKINE-OKUNUR sebep {\"d\":\"iptal\",\"s\":\"terk\"}",
    gecmisKayitlari(s).some((x) => x.d === "iptal" && x.s === "terk"), s.durum_gecmisi);
  ol("k", kod + ": sayac iptal=1, ulasilamadi=0, degisen=1",
    r.iptal === 1 && r.ulasilamadi === 0 && r.degisen === 1, JSON.stringify(r));
  ol("k", kod + ": tahsilat YOK -> Purchase GITMEDI", o.purchaseSayisi() === 0,
    "olcum-post=" + o.purchaseSayisi());
  ol("k", kod + ": Telegram gurultusu YOK", o.telegramSayisi() === 0,
    "tg=" + o.telegramSayisi());

  // OLCUM IZI — iki hal logda BIRBIRINE KARISMAMALI: `atlandi` dizgesi AYRI olmali.
  const kayitlar = o.olcumKayitlari();
  const kesin = kayitlar.find((x) => x.atlandi === "kesin-basarisiz");
  ol("k", kod + ": olcum satirinda atlandi='kesin-basarisiz'", !!kesin,
    JSON.stringify(kayitlar));
  ol("k", kod + ": 🔴 'retrieve-hatasi' dizgesi KULLANILMADI (iki hal ayirt edilebilir)",
    !kayitlar.some((x) => x.atlandi === "retrieve-hatasi"), JSON.stringify(kayitlar));
  ol("k", kod + ": errorCode iyzico'nun DONDURDUGU kod olarak loglandi",
    !!kesin && String(kesin.errorCode) === kod, String(kesin && kesin.errorCode));
  ol("k", kod + ": siparis_no AYNI satirda", !!kesin && kesin.siparis_no === no,
    String(kesin && kesin.siparis_no));
  ol("k", kod + ": bicim BOZULMADI (tek satir JSON, ikinci etiket ACILMADI)",
    !!kesin && kesin.bozuk !== true &&
    o.loglar().every((x) => x.startsWith("olcum ") || x.startsWith("terk-supurme ") ||
                            x.startsWith("terk supurmesi ")),
    JSON.stringify(o.loglar()));
}

// KARISIK TUR: uc kesin kod + bir BILINMEYEN kod + `det` YOK bir arada. Tek tek verilen
// fikstur, siniflarin BIRLIKTE gorulunce ayrisip ayrismadigini gizlerdi (bu dosyanin 1.
// bolumundeki ayni gerekce).
{
  const satirlar = [
    satirYap("PR-TEST-KARISIK-5122", "bekliyor", 30),
    satirYap("PR-TEST-KARISIK-10054", "bekliyor", 30),
    satirYap("PR-TEST-KARISIK-10057", "bekliyor", 30),
    satirYap("PR-TEST-KARISIK-9999", "bekliyor", 30),     // BILINMEYEN -> fail-closed
    satirYap("PR-TEST-KARISIK-DETYOK", "bekliyor", 30),   // retrieve `null` -> fail-closed
  ];
  const o = ortamKur(satirlar, (t) => {
    const s = String(t);
    if (s.indexOf("KARISIK-5122") >= 0) { return DETAY.kesinBasarisiz("5122"); }
    if (s.indexOf("KARISIK-10054") >= 0) { return DETAY.kesinBasarisiz("10054"); }
    if (s.indexOf("KARISIK-10057") >= 0) { return DETAY.kesinBasarisiz("10057"); }
    if (s.indexOf("KARISIK-9999") >= 0) { return DETAY.bilinmeyenKod(); }
    return null;   // JSON "null" -> istek() `null` dondurur = det YOK
  });
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();
  ol("k", "karisik tur: iptal=3 (yalniz kapali kumenin uyeleri)", r.iptal === 3,
    JSON.stringify(r));
  ol("k", "karisik tur: ulasilamadi=2 (bilinmeyen kod + det yok)", r.ulasilamadi === 2,
    JSON.stringify(r));
  ol("k", "karisik tur: degisen=3", r.degisen === 3, JSON.stringify(r));
  ol("q", "karisik tur: BILINMEYEN kod satiri 'bekliyor' KALDI",
    bul(satirlar, "PR-TEST-KARISIK-9999").durum === "bekliyor",
    bul(satirlar, "PR-TEST-KARISIK-9999").durum);
  ol("q", "karisik tur: det YOK satiri 'bekliyor' KALDI",
    bul(satirlar, "PR-TEST-KARISIK-DETYOK").durum === "bekliyor",
    bul(satirlar, "PR-TEST-KARISIK-DETYOK").durum);
  ol("q", "karisik tur: fail-closed satirlara HIC UPDATE gitmedi",
    !db_izVar(o.db, "PR-TEST-KARISIK-9999") && !db_izVar(o.db, "PR-TEST-KARISIK-DETYOK"),
    JSON.stringify(o.db.izler.map((i) => i.siparis_no)));
}

// ================================================================ 10) (q) EMNIYET: FAIL-CLOSED
//
// 🔴 ISIN KALBI. Kume KAPALIDIR: "basarisiz gorunen her cevap" iptal edilmez. Yeni/bilinmeyen
// bir iyzico kodu, bos kod, taninmayan `status` ve `det` yoklugu ESKI fail-closed yolunda
// KALIR — kor iptal parayi gorunmez yapar ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]],
// [[yeni-hal-cozucunun-varsayilan-kovasina-duser]]: yeni bir HAL, cozucunun varsayilan
// kovasina dusup SAHTE YESIL uretmemeli).
//
// 🔴 KOD TEK BASINA YETMEZ: son iki vaka kumede OLAN bir kodu, iyzico'nun "failure" beyani
// OLMADAN tasir. Bunlar taninmayan bir govdeden de gelebilir -> fail-closed.

console.log("\n--- 10) (q) EMNIYET: kapali kume DISINDA kalan her sey FAIL-CLOSED ---");
{
  const HALLER = [
    ["bilinmeyen-kod", DETAY.bilinmeyenKod()],
    ["bos-kod", { status: "failure", errorCode: "", errorMessage: "" }],
    ["kod-alani-yok", { status: "failure" }],
    ["det-yok", null],
    ["status-yok-kod-kumede", { errorCode: "5122", errorMessage: "uydurma" }],
    ["status-baska-kod-kumede", { status: "pending", errorCode: "5122", errorMessage: "uydurma" }],
  ];
  for (const [ad, det] of HALLER) {
    const no = "PR-TEST-FAILCLOSED-" + ad;
    const satirlar = [satirYap(no, "bekliyor", 30)];
    const o = ortamKur(satirlar, () => det);
    const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
    await o.bitir();

    ol("q", ad + ": durum DEGISMEDI ('bekliyor')", satirlar[0].durum === "bekliyor",
      "durum=" + satirlar[0].durum);
    ol("q", ad + ": 🔴 D1'e HIC YAZILMADI (UPDATE sayisi 0)", o.db.izler.length === 0,
      JSON.stringify(o.db.izler.map((i) => i.siparis_no)));
    ol("q", ad + ": sayac ulasilamadi=1, iptal=0, degisen=0",
      r.ulasilamadi === 1 && r.iptal === 0 && r.degisen === 0, JSON.stringify(r));
    ol("q", ad + ": gecmise de yazilmadi", satirlar[0].durum_gecmisi === "",
      satirlar[0].durum_gecmisi);
    const kayitlar = o.olcumKayitlari();
    ol("q", ad + ": olcum satiri 'retrieve-hatasi' (kesin-basarisiz DEGIL)",
      kayitlar.some((x) => x.atlandi === "retrieve-hatasi") &&
      !kayitlar.some((x) => x.atlandi === "kesin-basarisiz"), JSON.stringify(kayitlar));
  }
}

// ODENMIS KOL BOZULMADI: yeni sinif, 'odendi' para-kurtarma kolunun ONUNE gecmemeli.
{
  const no = "PR-TEST-ODENDI-BOZULMADI";
  const satirlar = [satirYap(no, "bekliyor", 30)];
  const o = ortamKur(satirlar, () => DETAY.odendi(no));
  const r = await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();
  ol("q", "status='success' + paymentStatus='SUCCESS' -> durum 'odendi' (kol BOZULMADI)",
    satirlar[0].durum === "odendi", satirlar[0].durum);
  ol("q", "odendi kolunda iptal=0, odendi=1", r.iptal === 0 && r.odendi === 1,
    JSON.stringify(r));
  ol("q", "odendi turunda 'kesin-basarisiz' satiri BASILMADI (gurultu yok)",
    !o.olcumKayitlari().some((x) => x.atlandi === "kesin-basarisiz"),
    JSON.stringify(o.olcumKayitlari()));
}

// 🔒 GIZLILIK — YENI KOLDA DA AYNI KAPI. Yeni bir log cagrisi acilmadigi icin ayni beyaz
// liste + token maskesi gecerlidir; ama bu CIKARIM DEGIL, OLCUM olmali (kol ayri bir
// dizgeyle basiyor: "kesin-basarisiz").
{
  const no = "PR-TEST-KESIN-GIZLILIK";
  const PII = {
    musteri_ad: "PIIADXQ-Ayse Yilmaz",
    musteri_tel: "PIITELXQ-05321234567",
    musteri_eposta: "PIIEPOSTAXQ@ornek.invalid",
    musteri_adres: "PIIADRESXQ Cumhuriyet Mah. 12/3",
    musteri_notu: "PIINOTXQ kapida teslim",
    atif: JSON.stringify({ ga_client_id: "PIIGAXQ-9.9", fbp: "PIIFBPXQ.fb.1", fbc: "PIIFBCXQ.fb.1" }),
    token: "PIITOKENXQ-uydurma-odeme-token-0123456789",
  };
  const satirlar = [satirYap(no, "bekliyor", 30, PII)];
  // Kesin-basarisiz cevap, ham govdeyi ECHO ediyor gibi: token metnin ICINDE.
  const o = ortamKur(satirlar, (t) => ({
    status: "failure", errorCode: "5122",
    errorMessage: 'Odeme bulunamadi: {"locale":"tr","token":"' + t + '"}',
  }));
  await MODUL.terkSupur(o.env, o.ctx, SIMDI);
  await o.bitir();

  const cikti = o.loglar().join("\n");
  const h = o.olcumKayitlari().find((x) => x.atlandi === "kesin-basarisiz");
  ol("p", "kesin-basarisiz satiri GERCEKTEN basildi (negatif iddia sahte-yesil vermesin)",
    !!h, cikti);
  ol("p", "🔒 kesin-basarisiz kolunda fikstur PII damgasi ('XQ') ciktinin HICBIR YERINDE yok",
    cikti.indexOf("XQ") < 0, cikti.slice(0, 400));
  ol("p", "🔒 kesin-basarisiz kolunda token'in yerinde MASKE var",
    !!h && String(h.errorMessage).indexOf("***") >= 0, String(h && h.errorMessage));
  ol("p", "kesin-basarisiz kolunda errorCode teknik kod olarak GECTI",
    !!h && h.errorCode === "5122", String(h && h.errorCode));
}

// ================================================================ 11) (r) IKINCI TUKETICI
//
// [[tuketici-yazilirken-tum-okuyucular-sayilir]]: `odemeHukmu` IKI yerden cagrilir. Yeni
// sinif CANLI MUSTERI YOLUNU da (`/donus`) degistirir ve bu KASITLIDIR — kart reddi insan
// incelemesi gerektirmez, 'incele' + Telegram yalnizca gurultu uretiyordu. Sessiz bir yan
// etki DEGIL, ADIYLA olculen bir eksendir. Gercek altyapi hatasi kolu AYNEN durur.

console.log("\n--- 11) (r) IKINCI TUKETICI: /donus callback'i (canli musteri yolu) ---");
async function donusKos(no, det) {
  const satirlar = [satirYap(no, "bekliyor", 1)];
  const o = ortamKur(satirlar, () => det);
  const istek = new Request("https://pruvo3d.invalid/api/shop/donus", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: satirlar[0].token }),
  });
  await MODUL.default.fetch(istek, o.env, o.ctx);
  await o.bitir();
  return { satir: satirlar[0], o };
}

for (const kod of ["5122", "10054", "10057"]) {
  const { satir, o } = await donusKos("PR-TEST-DONUS-KESIN-" + kod, DETAY.kesinBasarisiz(kod));
  ol("r", kod + ": /donus KESIN-BASARISIZ -> durum 'basarisiz'", satir.durum === "basarisiz",
    "durum=" + satir.durum);
  ol("r", kod + ": 🔴 'incele' DEGIL (insan incelemesine dusurulmez)", satir.durum !== "incele",
    "durum=" + satir.durum);
  ol("r", kod + ": Telegram GITMEDI (kart reddi gurultusu kesildi)", o.telegramSayisi() === 0,
    "tg=" + o.telegramSayisi());
  ol("r", kod + ": Purchase GITMEDI", o.purchaseSayisi() === 0,
    "olcum-post=" + o.purchaseSayisi());
  ol("r", kod + ": olcum satirinda atlandi='kesin-basarisiz'",
    o.olcumKayitlari().some((x) => x.atlandi === "kesin-basarisiz"),
    JSON.stringify(o.olcumKayitlari()));
}

// GERCEK ALTYAPI HATASI + BILINMEYEN KOD: eski kol AYNEN durur ('incele' + Telegram).
for (const [ad, det] of [["altyapi-1001", DETAY.altyapiHatasi()],
                         ["bilinmeyen-9999", DETAY.bilinmeyenKod()]]) {
  const { satir, o } = await donusKos("PR-TEST-DONUS-" + ad, det);
  ol("r", ad + ": /donus 'incele' YAZDI (fail-closed kol AYNEN duruyor)",
    satir.durum === "incele", "durum=" + satir.durum);
  ol("r", ad + ": 🔴 ASLA 'basarisiz' degil (odeme durumu BILINMIYOR)",
    satir.durum !== "basarisiz", "durum=" + satir.durum);
  ol("r", ad + ": Telegram uyarisi HALA GIDIYOR", o.telegramSayisi() === 1,
    "tg=" + o.telegramSayisi());
  ol("r", ad + ": olcum satiri 'retrieve-hatasi' (kesin-basarisiz DEGIL)",
    o.olcumKayitlari().some((x) => x.atlandi === "retrieve-hatasi") &&
    !o.olcumKayitlari().some((x) => x.atlandi === "kesin-basarisiz"),
    JSON.stringify(o.olcumKayitlari()));
}

// UYUSMAZLIK kolu (para ORTADA) /donus'ta da BOZULMADI: asla 'basarisiz'/'iptal'.
{
  const no = "PR-TEST-DONUS-UYUSMAZ";
  const { satir, o } = await donusKos(no, DETAY.tutarsiz(no));
  ol("r", "uyusmazlik: /donus 'incele' YAZDI (para ORTADA)", satir.durum === "incele",
    "durum=" + satir.durum);
  ol("r", "uyusmazlik: 🔴 ne 'basarisiz' ne 'iptal'",
    satir.durum !== "basarisiz" && satir.durum !== "iptal", "durum=" + satir.durum);
  ol("r", "uyusmazlik: Telegram uyarisi GITTI", o.telegramSayisi() === 1,
    "tg=" + o.telegramSayisi());
}

// ================================================================ 12) (k) KAPALI KUME TEK KAYNAK
//
// Kume ve yuklem TEK dosyada (shop/src/iyzico.js) ve DISA ACIK olmali: ikinci bir sozluk
// ya da `det.errorCode` ile elle karsilastirma, sessizce ayrisan ikinci bir hukum acardi
// ([[ayni-alan-iki-hukum-biri-sessiz]]). Olcut DAVRANISTIR: yuklem GERCEKTEN cagrilir.

console.log("\n--- 12) (k) KAPALI KUME + TEK YUKLEM: tek kaynak ---");
{
  const IYZ = await import(url.pathToFileURL(
    path.join(path.dirname(KAYNAK_YOL), "iyzico.js")).href);
  ol("k", "kume DISA ACIK ve DONDURULMUS (Object.freeze)",
    Array.isArray(IYZ.IYZICO_KESIN_BASARISIZ) && Object.isFrozen(IYZ.IYZICO_KESIN_BASARISIZ),
    JSON.stringify(IYZ.IYZICO_KESIN_BASARISIZ));
  ol("k", "kume BOS DEGIL ve uyeleri dizge",
    IYZ.IYZICO_KESIN_BASARISIZ.length > 0 &&
    IYZ.IYZICO_KESIN_BASARISIZ.every((x) => typeof x === "string" && x.length > 0),
    JSON.stringify(IYZ.IYZICO_KESIN_BASARISIZ));
  ol("k", "yuklem: kumedeki her uye 'failure' beyaniyla TRUE",
    IYZ.IYZICO_KESIN_BASARISIZ.every((kod) =>
      IYZ.kesinBasarisizMi({ status: "failure", errorCode: kod }) === true),
    JSON.stringify(IYZ.IYZICO_KESIN_BASARISIZ));
  ol("q", "yuklem: det YOK -> false", IYZ.kesinBasarisizMi(null) === false);
  ol("q", "yuklem: status 'failure' DEGIL -> false (kod kumede olsa bile)",
    IYZ.kesinBasarisizMi({ errorCode: "5122" }) === false &&
    IYZ.kesinBasarisizMi({ status: "pending", errorCode: "5122" }) === false);
  ol("q", "yuklem: bilinmeyen/bos kod -> false",
    IYZ.kesinBasarisizMi({ status: "failure", errorCode: "9999" }) === false &&
    IYZ.kesinBasarisizMi({ status: "failure", errorCode: "" }) === false &&
    IYZ.kesinBasarisizMi({ status: "failure" }) === false);
  // Kume KAPALI: "YOK" sozlesme degeri uye OLAMAZ (bos kod kor iptale donusurdu).
  ol("q", "kume 'YOK' sozlesme degerini ICERMEZ",
    IYZ.IYZICO_KESIN_BASARISIZ.indexOf("YOK") < 0,
    JSON.stringify(IYZ.IYZICO_KESIN_BASARISIZ));
}

// ================================================================ SONUC

console.log("\n=== SONUC: " + gecen + " gecti / " + kalan + " kaldi ===");
console.log("OLEN_IDDIALAR=" + (olen.size ? [...olen].sort().join(",") : "-"));
process.exit(kalan ? 1 : 0);
