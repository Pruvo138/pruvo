#!/usr/bin/env node
/**
 * PRUVO shop KABUL TESTLERI (tools/paket-shop-odeme.md, 7 madde).
 *
 *   node shop/test/kabul.js             # 1,2,3,4m,5,6,7 — mock iyzico + YEREL D1 + gercek worker
 *   node shop/test/kabul.js --sandbox   # 4  — GERCEK iyzico sandbox'i (shop/.dev.vars anahtarlari)
 *   node shop/test/kabul.js --paritesiz # 7'yi (parite regresyonlari) atla — hizli gelistirme turu
 *
 * NASIL: worker'in KENDISI (shop/src) `wrangler dev --local`de kosturulur; iyzico ve Telegram
 * bu dosyanin icindeki mock HTTP sunucusuna yonlendirilir (IYZICO_BASE_URL/TELEGRAM_API
 * ortam degiskenleri). Mock, IYZWSv2 imzasini kendi de hesaplayip DOGRULAR — yani HMAC
 * imzalama kodu da sinanir. D1 yerel kopyasina gercek sema (tools/d1-sema.sql) kurulur.
 *
 * Test 4'un iki bicimi var:
 *   4m (varsayilan): ayni akis mock iyzico ile UCTAN UCA (baslat -> token -> callback ->
 *       retrieve -> D1 satiri + Telegram bildirimi). Kod yolunun tamamini kapsar.
 *   4  (--sandbox):  gercek sandbox. Script odeme sayfasi URL'ini basar; iyzico test karti
 *       elle girilir (5528790000000008 12/30 123), donuste worker retrieve ile dogrular;
 *       script D1'de 'odendi' satirini gorunce KANIT (odeme id + satir) basar.
 */

"use strict";

const { spawn, spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const SHOP = path.dirname(__dirname);            // .../shop
const KOK = path.dirname(SHOP);                  // repo koku
const WORKER_PORT = 8799;
const MOCK_PORT = 8798;
const WORKER_UC = "http://127.0.0.1:" + WORKER_PORT + "/api/shop";
const TEST_API_KEY = "test-api-key";
const TEST_SECRET = "test-secret-key";

const SANDBOX = process.argv.includes("--sandbox");
const PARITESIZ = process.argv.includes("--paritesiz");

const AYAR = JSON.parse(fs.readFileSync(path.join(SHOP, "config.json"), "utf8"));
// Test 1'in beklentisi TEK KAYNAKTAN (/secenekler.js) turetilir: worker'in fiyat kurali
// degisirse test onunla birlikte kayar ama iyzico'ya giden tutar/D1 zinciri yine sinanir.
// Test 8 ise beklenen degerleri SPEC'ten SABIT tutar (asagida) — kaymayi orasi yakalar.
require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }

function beklenenKurus(fiyatMetni, malzeme, renk, adet, kategori) {
  return SECENEK.satirOzeti(
    { kategori: kategori || "Otomobil", fiyat: fiyatMetni, parametrik: false, boy_secenekleri: [] },
    { id: "x", malzeme: malzeme, renk: renk || "Siyah", renk_ozel: renk === "Diğer" ? "mor" : "",
      boy_etiket: null, adet: adet || 1 }).kurus;
}
function kurusMetin(kurus) {
  return Math.floor(kurus / 100) + "." + String(kurus % 100).padStart(2, "0");
}

// ---------------------------------------------------------------- ufak yardimcilar

let gecen = 0, kalan = 0;
const sonuclar = [];
function rapor(ad, ok, detay) {
  sonuclar.push({ ad, ok, detay });
  if (ok) { gecen++; } else { kalan++; }
  console.log((ok ? "  ✅ GECTI " : "  ❌ KALDI ") + ad + (detay ? " — " + detay : ""));
}
function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

// fetch DEGIL node:http, keep-alive KAPALI (agent:false): undici'nin soket geri kullanimi,
// workerd bagantiyi kapatinca ECONNRESET yarisi uretiyordu (ilk kosuda olculdu).
function istekHam(yontem, url, basliklar, govde) {
  return new Promise((coz, reddet) => {
    const u = new URL(url);
    const istek = http.request({
      hostname: u.hostname, port: u.port, path: u.pathname + u.search,
      method: yontem, headers: basliklar || {}, agent: false,
    }, (cevap) => {
      let veri = "";
      cevap.on("data", (c) => { veri += c; });
      cevap.on("end", () => coz({
        kod: cevap.statusCode,
        yer: cevap.headers["location"] || "",
        metin: veri,
      }));
    });
    istek.on("error", reddet);
    if (govde) { istek.write(govde); }
    istek.end();
  });
}
async function istekJson(yontem, url, govdeObj) {
  const c = await istekHam(yontem, url,
    govdeObj ? { "Content-Type": "application/json" } : {},
    govdeObj ? JSON.stringify(govdeObj) : null);
  let j = {};
  try { j = JSON.parse(c.metin); } catch (e) { /* JSON olmayan cevap */ }
  return { kod: c.kod, yer: c.yer, govde: j };
}

function wranglerD1(sql) {
  // Yerel D1'e SQL — wrangler.toml'daki binding uzerinden (cwd=shop). JSON cikti parse edilir.
  const p = spawnSync("npx", ["--yes", "wrangler@4", "d1", "execute", "pruvo-katalog",
    "--local", "--json", "--command", sql], { cwd: SHOP, encoding: "utf8" });
  const ham = (p.stdout || "") + (p.stderr || "");
  const i = (p.stdout || "").indexOf("[");
  if (p.status !== 0 || i === -1) {
    throw new Error("wrangler d1 execute basarisiz:\n" + ham.slice(-1500));
  }
  return JSON.parse(p.stdout.slice(i));
}
function d1Sorgu(sql) {
  const r = wranglerD1(sql);
  return (r[0] && r[0].results) || [];
}

// ---------------------------------------------------------------- mock iyzico + telegram

const mockDurum = {
  initler: [],          // initialize istek govdeleri (dogrulanan)
  tokenlar: new Map(),  // token -> {paidPrice, price, conversationId, basketId}
  telegram: [],         // sendMessage govdeleri
  imzaHatasi: 0,
};

function mockBaslat() {
  const sunucu = http.createServer((req, res) => {
    let govde = "";
    req.on("data", (c) => { govde += c; });
    req.on("end", () => {
      res.setHeader("Content-Type", "application/json");

      if (req.url === "/_durum") {   // test yardimcisi
        res.end(JSON.stringify({
          initSayisi: mockDurum.initler.length,
          sonInit: mockDurum.initler[mockDurum.initler.length - 1] || null,
          sonToken: [...mockDurum.tokenlar.keys()].pop() || null,
          telegramSayisi: mockDurum.telegram.length,
          sonTelegram: mockDurum.telegram[mockDurum.telegram.length - 1] || null,
          imzaHatasi: mockDurum.imzaHatasi,
        }));
        return;
      }
      if (/^\/bot/.test(req.url) && req.url.endsWith("/sendMessage")) {
        mockDurum.telegram.push(JSON.parse(govde || "{}"));
        res.end(JSON.stringify({ ok: true }));
        return;
      }
      if (req.url === "/payment/iyzipos/checkoutform/initialize/auth/ecom") {
        // IYZWSv2 imzasini BIZ de hesaplayip dogrula (worker'in HMAC kodunun testi)
        if (!imzaGecerli(req, govde)) {
          mockDurum.imzaHatasi++;
          res.statusCode = 401;
          res.end(JSON.stringify({ status: "failure", errorMessage: "imza gecersiz" }));
          return;
        }
        const b = JSON.parse(govde);
        const sepetToplam = (b.basketItems || [])
          .reduce((t, k) => t + parseFloat(k.price), 0);
        if (Math.abs(sepetToplam - parseFloat(b.price)) > 0.009) {
          res.statusCode = 400;
          res.end(JSON.stringify({ status: "failure", errorMessage: "basketItems toplami != price" }));
          return;
        }
        const token = "mocktoken-" + (mockDurum.initler.length + 1) + "-" +
          crypto.randomBytes(6).toString("hex");
        mockDurum.initler.push(b);
        mockDurum.tokenlar.set(token, {
          paidPrice: parseFloat(b.paidPrice), price: parseFloat(b.price),
          conversationId: b.conversationId, basketId: b.basketId,
        });
        res.end(JSON.stringify({
          status: "success", token,
          paymentPageUrl: "http://127.0.0.1:" + MOCK_PORT + "/odeme/" + token,
          conversationId: b.conversationId,
        }));
        return;
      }
      if (req.url === "/payment/iyzipos/checkoutform/auth/ecom/detail") {
        if (!imzaGecerli(req, govde)) {
          mockDurum.imzaHatasi++;
          res.statusCode = 401;
          res.end(JSON.stringify({ status: "failure", errorMessage: "imza gecersiz" }));
          return;
        }
        const b = JSON.parse(govde);
        const kayit = mockDurum.tokenlar.get(b.token);
        if (!kayit) {
          res.end(JSON.stringify({ status: "failure", errorCode: "5001",
            errorMessage: "token bulunamadi" }));
          return;
        }
        res.end(JSON.stringify({
          status: "success", paymentStatus: "SUCCESS",
          paymentId: "MOCKPAY-" + b.token.slice(-6),
          paidPrice: kayit.paidPrice, price: kayit.price,
          conversationId: kayit.conversationId, basketId: kayit.basketId,
          fraudStatus: 1,
        }));
        return;
      }
      res.statusCode = 404;
      res.end(JSON.stringify({ hata: "mock bilinmeyen yol: " + req.url }));
    });
  });
  return new Promise((coz) => sunucu.listen(MOCK_PORT, "127.0.0.1", () => coz(sunucu)));
}

function imzaGecerli(req, govde) {
  const yetki = req.headers["authorization"] || "";
  if (!yetki.startsWith("IYZWSv2 ")) { return false; }
  const coz = Buffer.from(yetki.slice(8), "base64").toString("utf8");
  const m = /^apiKey:(.+)&randomKey:(.+)&signature:([0-9a-f]+)$/.exec(coz);
  if (!m || m[1] !== TEST_API_KEY) { return false; }
  const beklenen = crypto.createHmac("sha256", TEST_SECRET)
    .update(m[2] + req.url + govde).digest("hex");
  return m[3] === beklenen;
}

// ---------------------------------------------------------------- yerel D1 kurulum

function d1Kur() {
  // Deterministik test: eski yerel durum silinir, gercek sema + test urunleri kurulur.
  fs.rmSync(path.join(SHOP, ".wrangler"), { recursive: true, force: true });
  const semaYol = path.join(KOK, "tools", "d1-sema.sql");
  const p = spawnSync("npx", ["--yes", "wrangler@4", "d1", "execute", "pruvo-katalog",
    "--local", "--file", semaYol], { cwd: SHOP, encoding: "utf8" });
  if (p.status !== 0) {
    throw new Error("sema kurulamadi:\n" + ((p.stdout || "") + (p.stderr || "")).slice(-1500));
  }
  wranglerD1(
    "INSERT INTO urunler (id,hash,seq,baslik,kategori,marka,fiyat,parametrik,hs) VALUES " +
    "('test-urun-a','h1',1,'Test Urun A (kalici)','Marin','[]','850 TL',0,''), " +
    "('test-urun-b','h2',2,'Test Urun B (binlik)','Otomobil','[]','1.250 TL',0,''), " +
    "('test-parametrik','h3',3,'Test Olcuye Ozel','Tamirat','[]','',1,''), " +
    "('test-fiyatsiz','h4',4,'Test Fiyatsiz','Ev','[]','',0,''), " +
    // test 8 icin: 100 TL (katsayi tablosu birebir) ve 333 TL (spec'teki kusurat ornegi)
    "('test-urun-100','h5',5,'Test Urun 100 TL','Ev','[]','100 TL',0,''), " +
    "('test-urun-333','h6',6,'Test Urun 333 TL','Ev','[]','333 TL',0,'');"
  );
}

// ---------------------------------------------------------------- worker'i kostur

let workerSurec = null;
let workerLog = "";
async function workerBaslat(ekstraVar) {
  const args = ["--yes", "wrangler@4", "dev", "--local", "--port", String(WORKER_PORT)];
  for (const [k, v] of Object.entries(ekstraVar)) { args.push("--var", k + ":" + v); }
  workerSurec = spawn("npx", args, { cwd: SHOP, stdio: ["ignore", "pipe", "pipe"] });
  workerSurec.stdout.on("data", (c) => { workerLog += c; });
  workerSurec.stderr.on("data", (c) => { workerLog += c; });
  // Saglik yoklamasi: bilinmeyen uc -> 404 JSON. Worker AYAKTA ama secenekler.js import'u
  // patlamissa fetch() 500 doner (modul yuklenemez) — o yuzden 404 bekleniyor, "cevap veriyor"
  // degil: bozuk bundle'i ayakta sanip testleri anlamsiz hatalarla dusurmesin.
  for (let i = 0; i < 120; i++) {
    await bekle(1000);
    try {
      const r = await istekHam("GET", WORKER_UC + "/_saglik");
      if (r.kod === 404) { return; }
      if (r.kod === 500) {
        throw new Error("worker ayakta ama modul yuklenemiyor (secenekler.js import?):\n" +
          workerLog.slice(-2000));
      }
    } catch (e) {
      if (String(e.message).includes("modul yuklenemiyor")) { throw e; }
    }
    if (workerSurec.exitCode !== null) { break; }
  }
  throw new Error("wrangler dev ayaga kalkmadi:\n" + workerLog.slice(-2000));
}
function workerDurdur() {
  if (workerSurec && workerSurec.exitCode === null) { workerSurec.kill("SIGTERM"); }
}

// ---------------------------------------------------------------- ortak istekler

const MUSTERI = { ad: "Test Musteri", tel: "05321234567", eposta: "test@pruvo3d.com",
  adres: "Test Mah. Deneme Sok. No:1 D:2", sehir: "Mugla", tckn: "" };

async function baslatIstek(sepet, ekstra) {
  return istekJson("POST", WORKER_UC + "/baslat",
    Object.assign({ musteri: MUSTERI, sepet }, ekstra || {}));
}
async function donusIstek(token) {
  return istekHam("POST", WORKER_UC + "/donus",
    { "Content-Type": "application/x-www-form-urlencoded" },
    new URLSearchParams({ token }).toString());
}
async function mockOku() {
  return (await istekJson("GET", "http://127.0.0.1:" + MOCK_PORT + "/_durum")).govde;
}

// ---------------------------------------------------------------- TESTLER (mock)

async function test1FiyatButunlugu() {
  // Istemci 1 TL'lik sahte tutar(lar) gonderir -> worker D1 fiyati x katsayi x adet hesaplar.
  // TPU kalemi .5 SINIRINA denk gelir (850 x 1.55 = 1317,50): yuvarlama YOK, kurus korunur.
  const toplamKurus = beklenenKurus("850 TL", "PETG", "Siyah", 2) +
    beklenenKurus("1.250 TL", "PLA", "Siyah", 1) +
    beklenenKurus("850 TL", "TPU", "Siyah", 1);
  const beklenen = kurusMetin(toplamKurus);
  const c = await baslatIstek(
    [{ id: "test-urun-a", malzeme: "PETG", renk: "Siyah", adet: 2, tutar: 1, fiyat: 1 },
     { id: "test-urun-b", malzeme: "PLA", renk: "Siyah", adet: 1, tutar: 1 },
     { id: "test-urun-a", malzeme: "TPU", renk: "Siyah", adet: 1, tutar: 1 }],
    { tutar: 1, toplam: 1, paidPrice: 1 });
  if (c.kod !== 200 || !c.govde.url || !c.govde.no) {
    return rapor("1 fiyat butunlugu", false, "baslat cevabi: " + c.kod + " " + JSON.stringify(c.govde));
  }
  const m = await mockOku();
  const init = m.sonInit;
  // Tutar METIN olarak da dogrulanir ("1317.5" degil "1317.50" gitmeli) — iyzico kurus bekler.
  const satirlar = d1Sorgu("SELECT tutar_kurus, durum FROM siparisler WHERE siparis_no = '" +
    c.govde.no + "'");
  // basketItems price toplami = price (iyzico kurali; tutmazsa oturum canlida reddedilir)
  const kalemToplam = (init.basketItems || [])
    .reduce((t, b) => t + Math.round(parseFloat(b.price) * 100), 0);
  const ok = init.price === beklenen && init.paidPrice === beklenen &&
    init.price !== "1" && satirlar.length === 1 &&
    satirlar[0].tutar_kurus === toplamKurus && satirlar[0].durum === "bekliyor" &&
    kalemToplam === toplamKurus && m.imzaHatasi === 0;
  rapor("1 fiyat butunlugu", ok,
    "iyzico oturum tutari=" + init.price + " (beklenen " + beklenen +
    ", istemcinin yolladigi sahte tutar=1 YOK SAYILDI); kalem toplami=" +
    kurusMetin(kalemToplam) + "; D1 satiri=" + JSON.stringify(satirlar[0] || null));
  return c.govde.no;
}

async function test2SahteCallback() {
  const once = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  const c = await donusIstek("uydurma-token-deneme-123");
  const sonra = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  const odendi = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler WHERE durum='odendi'")[0].n;
  const ok = c.kod === 404 && once === sonra && odendi === 0;
  rapor("2 sahte callback reddi", ok,
    "HTTP " + c.kod + " (beklenen 404); siparis sayisi " + once + "->" + sonra +
    "; odendi=" + odendi);
}

async function test4mUctanUcaMock(siparisNo) {
  const m = await mockOku();
  const token = m.sonToken;
  const c = await donusIstek(token);
  const satir = d1Sorgu("SELECT durum, iyzico_odeme_id, tutar_kurus FROM siparisler " +
    "WHERE siparis_no = '" + siparisNo + "'")[0] || {};
  const m2 = await mockOku();
  const ok = c.kod === 303 && c.yer.includes("siparis=ok") && c.yer.includes(siparisNo) &&
    satir.durum === "odendi" && String(satir.iyzico_odeme_id || "").startsWith("MOCKPAY-") &&
    m2.telegramSayisi === 1 &&
    String((m2.sonTelegram || {}).text || "").includes(siparisNo);
  rapor("4m uctan uca (mock iyzico)", ok,
    "callback 303->" + c.yer + "; D1: " + JSON.stringify(satir) +
    "; telegram bildirimi=" + m2.telegramSayisi);
  return token;
}

async function test3Idempotens(siparisNo, token) {
  const c = await donusIstek(token);          // AYNI token IKINCI kez
  const sayi = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler WHERE token = '" + token + "'")[0].n;
  const m = await mockOku();
  const ok = c.kod === 303 && sayi === 1 && m.telegramSayisi === 1;
  rapor("3 idempotens", ok,
    "ayni token 2. kez islendi: siparis kaydi=" + sayi + " (beklenen 1), " +
    "telegram bildirimi=" + m.telegramSayisi + " (beklenen 1, tekrarlanmadi)");
}

/** 8 — KATSAYI DOGRULUGU (Okan uyarisi: baska oturumlar yanlis hesapladi).
 *  Beklenen degerler SPEC'ten SABIT yazilir (secenekler.js'ten TURETILMEZ): katsayi tablosu
 *  yanlis degistirilirse test bunu yakalamali, sessizce yeni degeri onaylamamali. */
async function test8KatsayiDogrulugu() {
  // Spec: 100 TL'lik urun -> PLA 100 / PETG 130 / TPU 155 / ASA 160.
  // ABS ve Karbon Katkili KALDIRILDI (Okan, 16 Tem — 1ca4aab): muhendislik malzemeleri
  // WhatsApp kanalindan gider; asagida REDDEDILDIKLERI ayrica sinanir.
  const SPEC = { "PLA": "100.00", "PETG": "130.00", "TPU": "155.00", "ASA": "160.00" };
  const hatalar = [];
  const olculen = {};
  for (const malzeme of Object.keys(SPEC)) {
    const c = await baslatIstek([{ id: "test-urun-100", malzeme: malzeme, renk: "Siyah", adet: 1 }]);
    const init = (await mockOku()).sonInit;
    const p = c.kod === 200 && init ? init.price : "HATA/" + c.kod;
    olculen[malzeme] = p;
    if (p !== SPEC[malzeme]) {
      hatalar.push(malzeme + ": " + p + " (olmasi gereken " + SPEC[malzeme] + ")");
    }
  }

  // Kusurat + ADET: 333 x 1.30 = 432,90 (yuvarlama YOK); x3 = 1.298,70 (ara yuvarlama da yok —
  // yuvarlansaydi 1.299,00 olurdu).
  const ck = await baslatIstek([{ id: "test-urun-333", malzeme: "PETG", renk: "Siyah", adet: 3 }]);
  const kusurat = ck.kod === 200 ? (await mockOku()).sonInit.price : "HATA/" + ck.kod;
  if (kusurat !== "1298.70") { hatalar.push("333x1.30x3: " + kusurat + " (olmasi gereken 1298.70)"); }
  const sK = d1Sorgu("SELECT tutar_kurus FROM siparisler WHERE siparis_no = '" +
    (ck.govde || {}).no + "'")[0];
  if (!sK || sK.tutar_kurus !== 129870) {
    hatalar.push("D1 tutar_kurus: " + JSON.stringify(sK) + " (olmasi gereken 129870)");
  }

  // "Diger" renk +%15 katsayidan SONRA (Okan, 16 Tem): 333 -> PETG 432,90 -> x1.15 = 497,835
  // -> 497,84 (yarim kurus tahsil edilemez). Sira ters olsaydi 333x1.15=382,95 -> x1.30 = ayni
  // sonuc verir; bu yuzden sira testi ADET'le birlestirilmez, D1 kurusu birebir sinanir.
  const cd = await baslatIstek([{ id: "test-urun-333", malzeme: "PETG", renk: "Diğer",
                                  renk_ozel: "mor", adet: 1 }]);
  const digerFiyat = cd.kod === 200 ? (await mockOku()).sonInit.price : "HATA/" + cd.kod;
  if (digerFiyat !== "497.84") {
    hatalar.push("333 PETG 'Diger': " + digerFiyat + " (olmasi gereken 497.84)");
  }
  // "Diger" secilip renk metni bos gelirse REDDEDILIR (uretim ne basacagini bilemez)
  const cbos = await baslatIstek([{ id: "test-urun-333", malzeme: "PETG", renk: "Diğer", adet: 1 }]);
  if (cbos.kod !== 400) { hatalar.push("'Diger' + bos renk metni: " + cbos.kod + " (400 olmali)"); }

  // KALDIRILAN MALZEMELER (Okan, 16 Tem): ABS / Karbon Katkili artik secenek DEGIL ->
  // istemci elle gonderse bile Worker REDDETMELI (malzeme listesi secenekler.js'ten okunur,
  // ikinci kopya yok). Sessizce PLA fiyatina dusup ABS tahsil etmek OLMAZ.
  const kaldirilan = [];
  for (const m of ["ABS", "Karbon Katkılı"]) {
    const r = await baslatIstek([{ id: "test-urun-100", malzeme: m, renk: "Siyah", adet: 1 }]);
    kaldirilan.push(m + "->" + r.kod + "/" + (r.govde.hata || "?"));
    if (r.kod !== 400 || r.govde.hata !== "gecersiz-malzeme") {
      hatalar.push("kaldirilan malzeme " + m + " reddedilmedi: " + r.kod + " " +
                   JSON.stringify(r.govde));
    }
  }

  // ADET ARALIGI (1-99): aralik disi SESSIZCE kirpilmaz, REDDEDILIR
  const cAdet = [];
  for (const a of [0, 100, 2.5, -3]) {
    const r = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: a }]);
    cAdet.push(a + "->" + r.kod);
    if (r.kod !== 400) { hatalar.push("adet " + a + ": " + r.kod + " (400 olmali)"); }
  }
  // 99 gecerli sinir — kabul edilmeli
  const c99 = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 99 }]);
  const p99 = c99.kod === 200 ? (await mockOku()).sonInit.price : "HATA/" + c99.kod;
  if (p99 !== "9900.00") { hatalar.push("adet 99: " + p99 + " (olmasi gereken 9900.00)"); }

  rapor("8 katsayi dogrulugu", hatalar.length === 0,
    "100 TL urun -> " + Object.keys(olculen).map((k) => k + " " + olculen[k]).join(" / ") +
    "; 333x1.30x3 = " + kusurat + " (D1 kurus=" + (sK ? sK.tutar_kurus : "?") + ")" +
    "; 'Diger' renk = " + digerFiyat + "; kaldirilan: " + kaldirilan.join(" ") +
    "; adet reddi: " + cAdet.join(" ") + "; adet 99 = " + p99 +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 9 — PARAMETRIK ALTYAPI (sari seri sunucu-tarafi yeniden hesabi).
 *  Kanal bugun KAPALI (SECENEK.PARAMETRIK_ODEME_ACIK=false; taban fiyatlar 18/18 null) — o
 *  yuzden test 5 HTTP'de "reddedildi"yi sinar; bu test ise ACILDIGINDA calisacak KODU sinar:
 *   a) semalar.js <-> jenerator/urunler/ birebir (yeni sema eklenip liste guncellenmezse
 *      sessizce "sema yok -> red"e dusmesin),
 *   b) sunucu hesabi istemcinin gonderdigi hacim/fiyati YOK SAYAR ve konfiguratorun
 *      fiyatiyla birebir ayni cikar; aralik/bilinmeyen parametre reddedilir,
 *   c) worker bundle'i JSON semalar + hacim.js + konfigurator.js ile GERCEKTEN kurulabiliyor
 *      (dry-run deploy) — import zinciri ancak canliya cikarken patlamasin. */
async function test9ParametrikAltyapi() {
  const hatalar = [];

  // (a) sema kapsami — semalar.js'teki import yollari ile dizin birebir mi?
  const semaKaynak = fs.readFileSync(path.join(SHOP, "src", "semalar.js"), "utf8");
  const listelenen = new Set(
    [...semaKaynak.matchAll(/jenerator\/urunler\/([a-z0-9-]+)\.json/g)].map((m) => m[1]));
  const dizin = new Set(fs.readdirSync(path.join(KOK, "jenerator", "urunler"))
    .filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5)));
  const eksik = [...dizin].filter((x) => !listelenen.has(x));
  const fazla = [...listelenen].filter((x) => !dizin.has(x));
  if (eksik.length) { hatalar.push("semalar.js'te EKSIK: " + eksik.join(",")); }
  if (fazla.length) { hatalar.push("semalar.js'te FAZLA (dosya yok): " + fazla.join(",")); }

  // (b) sunucu yeniden hesabi — shop/src/parametrik.js'i DOGRUDAN yukle (shippen dosya).
  const PAR = await import("file://" + path.join(SHOP, "src", "parametrik.js"));
  const sema = JSON.parse(fs.readFileSync(
    path.join(KOK, "jenerator", "urunler", "olcuye-ozel-oring-conta.json"), "utf8"));
  const KONF = require(path.join(KOK, "jenerator", "konfigurator.js"));
  const HACIM = require(path.join(KOK, "jenerator", "hacim.js"));
  const vd = KONF.varsayilanDegerler(sema);
  // Taban fiyat bugun null; acildiginda 100 TL girilmis gibi dene.
  const denemeSema = Object.assign({}, sema, { tabanFiyatTL: 100 });

  // Istemci SAHTE hacim + SAHTE fiyat gonderir -> sunucu ikisini de yok saymali.
  const sonuc = PAR.parametrikHesapla(
    { id: sema.id, malzeme: "ASA", renk: "Diğer", renk_ozel: "mor", adet: 2,
      parametreler: vd, hacim_mm3: 1, parametrik_fiyat_kurus: 1 },
    SECENEK, denemeSema);
  const beklenenBirim = KONF.fiyatKurus(denemeSema, vd, "ASA", "Diğer",
    { secenek: SECENEK, hacim: HACIM });
  if (sonuc.hata) { hatalar.push("gecerli set reddedildi: " + sonuc.hata); }
  else {
    if (sonuc.birimKurus !== beklenenBirim) {
      hatalar.push("sunucu birim " + sonuc.birimKurus + " != konfigurator " + beklenenBirim);
    }
    if (sonuc.birimKurus === 1 || sonuc.hacimMm3 === 1) {
      hatalar.push("istemcinin sahte hacim/fiyati KULLANILDI");
    }
    // varsayilanlarda hacim = tabanHacim -> ASA(1.60) x Diger(1.15) x 100 TL = 184,00 TL
    if (sonuc.birimKurus !== 18400) {
      hatalar.push("beklenen 18400 kurus (100x1.60x1.15), gelen " + sonuc.birimKurus);
    }
  }
  // Aralik disi / bilinmeyen parametre / taban fiyatsiz -> RED
  const p1 = Object.keys(vd)[0];
  const araliksiz = Object.assign({}, vd); araliksiz[p1] = 99999;
  const r1 = PAR.parametrikHesapla({ id: sema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: araliksiz, adet: 1 }, SECENEK, denemeSema);
  if (r1.hata !== "parametre-araligi") { hatalar.push("aralik disi: " + JSON.stringify(r1)); }
  const bilinmeyen = Object.assign({ sinsi_alan: 5 }, vd);
  const r2 = PAR.parametrikHesapla({ id: sema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: bilinmeyen, adet: 1 }, SECENEK, denemeSema);
  if (r2.hata !== "bilinmeyen-parametre") { hatalar.push("bilinmeyen param: " + JSON.stringify(r2)); }
  const r3 = PAR.parametrikHesapla({ id: sema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: vd, adet: 1 }, SECENEK, sema);   // gercek sema: tabanFiyatTL null
  if (r3.hata !== "taban-fiyat-yok") { hatalar.push("taban fiyatsiz: " + JSON.stringify(r3)); }
  const r4 = PAR.parametrikHesapla({ id: sema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: null, adet: 1 }, SECENEK, denemeSema);
  if (r4.hata !== "parametre-yok") { hatalar.push("parametresiz: " + JSON.stringify(r4)); }

  // (c) bundle gercekten kuruluyor mu? (JSON import + konfigurator/hacim zinciri)
  const dry = spawnSync("npx", ["--yes", "wrangler@4", "deploy", "--dry-run",
    "--outdir", path.join(SHOP, ".wrangler", "dry")], { cwd: SHOP, encoding: "utf8" });
  const dryOk = dry.status === 0;
  if (!dryOk) {
    hatalar.push("wrangler dry-run BASARISIZ: " + ((dry.stderr || "") + (dry.stdout || "")).slice(-400));
  }

  rapor("9 parametrik altyapi (kanal KAPALI, kod hazir)", hatalar.length === 0,
    "sema kapsami " + listelenen.size + "/" + dizin.size + "; sunucu yeniden hesap=" +
    (sonuc.hata ? "HATA" : kurusMetin(sonuc.birimKurus) + " (istemcinin sahte hacim=1/fiyat=1 " +
     "YOK SAYILDI, konfiguratorle birebir)") + "; red yollari: aralik/bilinmeyen/taban-yok/" +
    "parametresiz OK; bundle dry-run=" + (dryOk ? "kuruldu" : "PATLADI") +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

async function test5Parametrik() {
  const onceInit = (await mockOku()).initSayisi;
  const onceSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  const c1 = await baslatIstek([{ id: "test-parametrik", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const c2 = await baslatIstek([{ id: "test-fiyatsiz", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const c3 = await baslatIstek([
    { id: "test-urun-a", malzeme: "PLA", renk: "Siyah", adet: 1 },
    { id: "test-parametrik", malzeme: "PLA", renk: "Siyah", adet: 1 }]);   // karisik sepet de RED
  const sonraInit = (await mockOku()).initSayisi;
  const sonraSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  const ok = c1.kod === 400 && c1.govde.hata === "parametrik-urun" &&
    c2.kod === 400 && c2.govde.hata === "fiyatsiz-urun" &&
    c3.kod === 400 && c3.govde.hata === "parametrik-urun" &&
    onceInit === sonraInit && onceSiparis === sonraSiparis;
  rapor("5 parametrik dislama", ok,
    "parametrik=" + c1.kod + "/" + c1.govde.hata + ", fiyatsiz=" + c2.kod + "/" + c2.govde.hata +
    ", karisik=" + c3.kod + "; iyzico oturumu ACILMADI (" + onceInit + "->" + sonraInit + ")");
}

function test6SirTaramasi() {
  // Repoya GIRECEK her sey taranir (izlenen + ignore-disi yeni dosyalar) — sadece shop/ degil:
  // anahtar yanlislikla DEVAM.md'ye, bir dokumana ya da teste de dusebilir. Repo PUBLIC.
  // git grep kullanilir (C hizinda; 7k urunluk urunler.json'i node'da okumaya gerek yok).
  const desenler = [
    ["sandbox-[A-Za-z0-9]{10,}", "iyzico sandbox anahtari"],
    ["[0-9]{8,10}:[A-Za-z0-9_-]{35}", "telegram bot token'i"],
    ["(api[_-]?key|secret[_-]?key)[\"' ]*[:=][\"' ]*[A-Za-z0-9+/=]{20,}", "gomulu anahtar"],
    ["BEGIN [A-Z ]*PRIVATE KEY", "ozel anahtar"],
  ];
  const bulunan = [];
  for (const [desen, ad] of desenler) {
    // -I: ikili dosyalari atla, --untracked: ignore'lanmamis yeni dosyalar da dahil.
    const g = spawnSync("git", ["-C", KOK, "grep", "-nIE", "--untracked", desen],
      { encoding: "utf8" });
    // exit 0 = eslesme VAR (sizinti), 1 = yok (temiz), >1 = git hatasi
    if (g.status === 0) {
      for (const satir of g.stdout.split("\n").filter(Boolean)) {
        // Sablon dosyasindaki "sandbox-XXXX" gibi degersiz ornekler sizinti degil.
        if (/\.dev\.vars\.example/.test(satir) || /sandbox-X+/.test(satir)) { continue; }
        bulunan.push(ad + ": " + satir.slice(0, 90));
      }
    } else if (g.status > 1) {
      bulunan.push("git grep hatasi: " + (g.stderr || "").slice(0, 120));
    }
  }
  // .dev.vars git'in gordugu listeye HIC girmemeli (ignore'da olmali)
  const p = spawnSync("git", ["-C", KOK, "ls-files", "--cached", "--others",
    "--exclude-standard"], { encoding: "utf8" });
  const dosyalar = p.stdout.split("\n").filter(Boolean);
  const devVars = dosyalar.filter((d) => /\.dev\.vars$/.test(d));
  // Anahtarlar GERCEKTEN diskte mi? (yoksa test "temiz" der ama aslinda hicbir sey aramamistir)
  const anahtarDosyasi = fs.existsSync(path.join(SHOP, ".dev.vars"));
  const ok = bulunan.length === 0 && devVars.length === 0 && dosyalar.length > 0;
  rapor("6 sir taramasi", ok, ok
    ? "repo geneli " + dosyalar.length + " dosya tarandi (4 desen), sizinti yok; .dev.vars " +
      (anahtarDosyasi ? "diskte VAR ama" : "yok;") + " git'e girmiyor"
    : "SIZINTI: " + bulunan.join(" | ") + " " + devVars.join(";"));
}

function test7Parite() {
  if (PARITESIZ) {
    rapor("7 parite regresyonlari", true, "--paritesiz ile ATLANDI (rapor icin tam kostur)");
    return;
  }
  // Arama koduna dokunulmadi ama D1'e sema eklendi -> canli /ara pariteleri yesil kalmali.
  const s1 = spawnSync("node", [path.join(KOK, "tools", "parite-test.js"), "300"],
    { cwd: KOK, encoding: "utf8" });
  const s2 = spawnSync("node", [path.join(KOK, "tools", "parite-ege.js")],
    { cwd: KOK, encoding: "utf8" });
  const ok = s1.status === 0 && s2.status === 0;
  const kuyruk = (c) => ((c.stdout || "") + (c.stderr || "")).trim().split("\n").slice(-2).join(" | ");
  rapor("7 parite regresyonlari", ok, "site: " + kuyruk(s1) + " || ege: " + kuyruk(s2));
}

// ---------------------------------------------------------------- TEST 4 (gercek sandbox)

async function testSandbox() {
  const devVars = path.join(SHOP, ".dev.vars");
  if (!fs.existsSync(devVars)) {
    console.log("\nBLOKE: shop/.dev.vars yok. iyzico sandbox anahtarlarini");
    console.log("  https://sandbox-merchant.iyzipay.com > Ayarlar > API Anahtarlari'ndan alip");
    console.log("  shop/.dev.vars.example sablonuyla shop/.dev.vars'a yaz, sonra tekrar kostur.");
    process.exit(2);
  }
  d1Kur();
  // .dev.vars'i wrangler dev kendisi okur; sadece Telegram'i mock'a alalim ki bildirim izlensin
  await mockBaslat();
  await workerBaslat({ TELEGRAM_API: "http://127.0.0.1:" + MOCK_PORT,
                       TELEGRAM_TOKEN: "0000:test" });
  const c = await baslatIstek([{ id: "test-urun-a", malzeme: "PETG", renk: "Siyah", adet: 1 }]);
  if (c.kod !== 200 || !c.govde.url) {
    console.log("SANDBOX baslat HATASI:", c.kod, JSON.stringify(c.govde));
    process.exit(1);
  }
  console.log("\n== SANDBOX UCTAN UCA ==");
  const bek = beklenenKurus("850 TL", "PETG", "Siyah", 1);
  console.log("Siparis no:", c.govde.no, "— beklenen tutar: " + kurusMetin(bek) +
    " TL (850 x PETG, secenekler.js)");
  console.log("1) Su sayfayi acip iyzico TEST kartiyla ode (docs.iyzico.com/ek-bilgiler/test-kartlari):");
  console.log("   " + c.govde.url);
  console.log("2) Odeme sonrasi iyzico seni bu makinedeki callback'e yonlendirir;");
  console.log("   script D1'de 'odendi' satirini gorunce kaniti basar. Bekliyor (en cok 10 dk)...");
  for (let i = 0; i < 300; i++) {
    await bekle(2000);
    const s = d1Sorgu("SELECT siparis_no, durum, tutar_kurus, iyzico_odeme_id FROM siparisler " +
      "WHERE siparis_no = '" + c.govde.no + "'")[0];
    if (s && s.durum === "odendi") {
      // 'odendi' gormek YETMEZ: tahsil edilen tutar sunucu hesabiyla birebir mi, odeme id
      // gercekten geldi mi, bildirim atildi mi — hepsi kanit olmali.
      const m = await mockOku();
      const sorunlar = [];
      if (s.tutar_kurus !== bek) {
        sorunlar.push("D1 tutar " + s.tutar_kurus + " != beklenen " + bek);
      }
      if (!s.iyzico_odeme_id) { sorunlar.push("iyzico odeme id BOS"); }
      if (m.telegramSayisi !== 1) { sorunlar.push("telegram bildirimi=" + m.telegramSayisi); }
      if (sorunlar.length) {
        console.log("\n❌ Odeme 'odendi' ama KANIT EKSIK: " + sorunlar.join("; "));
        console.log("   D1 satiri: " + JSON.stringify(s));
        workerDurdur();
        process.exit(1);
      }
      console.log("\n✅ SANDBOX KANITI — iyzico odeme id: " + s.iyzico_odeme_id);
      console.log("   D1 satiri: " + JSON.stringify(s) + " (tutar sunucu hesabiyla birebir)");
      console.log("   Telegram bildirimi (mock'a dustu): " + m.telegramSayisi);
      workerDurdur();
      process.exit(0);
    }
    if (s && (s.durum === "basarisiz" || s.durum === "incele")) {
      console.log("\n❌ Odeme '" + s.durum + "' durumunda: " + JSON.stringify(s));
      workerDurdur();
      process.exit(1);
    }
  }
  console.log("\n❌ Zaman asimi: odeme tamamlanmadi.");
  workerDurdur();
  process.exit(1);
}

// ---------------------------------------------------------------- akis

async function main() {
  if (SANDBOX) { return testSandbox(); }

  console.log("PRUVO shop kabul testleri (mock iyzico + yerel D1)\n");
  d1Kur();
  const mock = await mockBaslat();
  await workerBaslat({
    IYZICO_BASE_URL: "http://127.0.0.1:" + MOCK_PORT,
    IYZICO_API_KEY: TEST_API_KEY,
    IYZICO_SECRET_KEY: TEST_SECRET,
    TELEGRAM_API: "http://127.0.0.1:" + MOCK_PORT,
    TELEGRAM_TOKEN: "0000:test",
    SITE_URL: "https://pruvo3d.com",
  });

  try {
    const siparisNo = await test1FiyatButunlugu();
    await test2SahteCallback();
    let token = null;
    if (siparisNo) { token = await test4mUctanUcaMock(siparisNo); }
    else { rapor("4m uctan uca (mock iyzico)", false, "test 1 basarisiz oldugu icin kosulamadi"); }
    if (token) { await test3Idempotens(siparisNo, token); }
    else { rapor("3 idempotens", false, "token alinamadi"); }
    // 8, mock'un sonInit/sonToken durumunu tazeledigi icin 1/4m/3'ten SONRA kosar.
    await test8KatsayiDogrulugu();
    await test5Parametrik();
    await test9ParametrikAltyapi();
    test6SirTaramasi();
    test7Parite();
  } finally {
    workerDurdur();
    mock.close();
  }

  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" +
    (kalan ? "" : " — HEPSI YESIL ✅"));
  console.log("(Gercek sandbox uctan uca icin: node shop/test/kabul.js --sandbox)");
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => {
  console.error("\nTEST ALTYAPI HATASI:", e && e.stack || e);
  if (e && e.cause) { console.error("SEBEP:", e.cause); }
  console.error("\n-- wrangler dev log kuyrugu --\n" + workerLog.slice(-3000));
  workerDurdur();
  process.exit(1);
});
