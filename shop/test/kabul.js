#!/usr/bin/env node
/**
 * PRUVO shop KABUL TESTLERI (tools/paket-shop-odeme.md 7 madde + tools/paket-shop-kargo.md:
 * 10 kargo, 11 retrieve-incele, 12 siparis numarasi, 13 havale/eft, 14 kdv, 15 sozlesme onayi).
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
const vm = require("node:vm");

const SHOP = path.dirname(__dirname);            // .../shop
const KOK = path.dirname(SHOP);                  // repo koku
// Portlar env ile ezilebilir: ayni makinede ESZAMANLI iki oturum/worktree kabul testi
// kosarsa (16 Tem'de yasandi) varsayilan portlar cakisir — EADDRINUSE.
const WORKER_PORT = Number(process.env.KABUL_WORKER_PORT || 8799);
const MOCK_PORT = Number(process.env.KABUL_MOCK_PORT || 8798);
const WORKER_UC = "http://127.0.0.1:" + WORKER_PORT + "/api/shop";
const TEST_API_KEY = "test-api-key";
const TEST_SECRET = "test-secret-key";
// Havale/EFT (paket-shop-kargo.md kalem 6): IBAN+unvan TEK yerden (worker env/secret).
// Gercek degerler deploy'da girilir; testte sahte degerler --var ile verilir.
const TEST_IBAN = "TR000000000000000000000001";
const TEST_UNVAN = "TEST UNVAN LTD. STI.";
// Siparis yonetimi paketi (tools/paket-siparis-yonetimi.md) test anahtarlari.
const TEST_YONET = "test-yonet-anahtar-abc123";
const TEST_RESEND_KEY = "test-resend-key";
const TEST_IC = "test-ic-derle-anahtar";
const TEST_BILDIRIM = "info@pruvo3d.com";
// KDV (kalem 8, Okan KESIN %20): beklentiler SPEC'ten SABIT — oran yanlis degistirilirse
// test yakalasin. net = brut/(1+oran) kurusta; net+KDV=brut BIREBIR (fark KDV'ye yedirilir).
const KDV_YUZDE_SPEC = 20;
function specKdv(brutKurus) {
  const net = Math.round(brutKurus * 100 / (100 + KDV_YUZDE_SPEC));
  return { net: net, kdv: brutKurus - net };
}

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
        bas: cevap.headers,
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
  detayZorlaHata: false, // true -> retrieve ALTYAPI hatasi doner (1001 senaryosu, test 11)
  epostalar: [],        // Resend /emails govdeleri {to, subject, html, from} (siparis yonetimi)
  icDerle: [],          // /api/onizleme/ic-derle istekleri {anahtar, aile} (parametrik STL)
};

function mockBaslat() {
  const sunucu = http.createServer((req, res) => {
    let govde = "";
    req.on("data", (c) => { govde += c; });
    req.on("end", () => {
      res.setHeader("Content-Type", "application/json");

      if (req.url === "/_detayhata/ac" || req.url === "/_detayhata/kapat") { // test yardimcisi
        mockDurum.detayZorlaHata = req.url.endsWith("/ac");
        res.end(JSON.stringify({ detayZorlaHata: mockDurum.detayZorlaHata }));
        return;
      }
      if (req.url === "/_durum") {   // test yardimcisi
        res.end(JSON.stringify({
          initSayisi: mockDurum.initler.length,
          sonInit: mockDurum.initler[mockDurum.initler.length - 1] || null,
          sonToken: [...mockDurum.tokenlar.keys()].pop() || null,
          telegramSayisi: mockDurum.telegram.length,
          sonTelegram: mockDurum.telegram[mockDurum.telegram.length - 1] || null,
          telegramlar: mockDurum.telegram,
          imzaHatasi: mockDurum.imzaHatasi,
          epostaSayisi: mockDurum.epostalar.length,
          epostalar: mockDurum.epostalar,
          sonEposta: mockDurum.epostalar[mockDurum.epostalar.length - 1] || null,
          icDerleSayisi: mockDurum.icDerle.length,
          sonIcDerle: mockDurum.icDerle[mockDurum.icDerle.length - 1] || null,
        }));
        return;
      }
      if (/^\/bot/.test(req.url) && req.url.endsWith("/sendMessage")) {
        mockDurum.telegram.push(JSON.parse(govde || "{}"));
        res.end(JSON.stringify({ ok: true }));
        return;
      }
      // Resend mock (siparis yonetimi Faz 2) — worker RESEND_URL bunu gosterir.
      if (req.url === "/emails") {
        let g = {};
        try { g = JSON.parse(govde || "{}"); } catch (e) { /* bos */ }
        mockDurum.epostalar.push({
          to: g.to, subject: g.subject, html: g.html, from: g.from,
          auth: req.headers["authorization"] || "",
        });
        res.end(JSON.stringify({ id: "mock-email-" + mockDurum.epostalar.length }));
        return;
      }
      // onizleme ic-derle mock (parametrik STL) — worker ONIZLEME_TABAN bunu gosterir.
      // Ham (gzip'siz) binary STL doner; shop yonetim /stl bunu stream eder.
      if (req.url === "/api/onizleme/ic-derle") {
        let g = {};
        try { g = JSON.parse(govde || "{}"); } catch (e) { /* bos */ }
        mockDurum.icDerle.push({ anahtar: req.headers["x-ic-anahtar"] || "", aile: g.aile });
        const stl = Buffer.concat([Buffer.alloc(84, 0), Buffer.from("MOCKSTL-" + (g.aile || ""))]);
        res.setHeader("Content-Type", "application/octet-stream");
        res.end(stl);
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
        if (mockDurum.detayZorlaHata) {
          // 16 Tem canli bulgusunun birebiri: canli anahtar + sandbox URL -> 1001.
          res.end(JSON.stringify({ status: "failure", errorCode: "1001",
            errorMessage: "api bilgileri bulunamadi" }));
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
    "('test-urun-333','h6',6,'Test Urun 333 TL','Ev','[]','333 TL',0,''), " +
    // test 10 (kargo) icin kurusu tutturan fiyatlar: 103 PETG+'Diger' = 15398,5 -> 15399 kurus
    // (…,99 biten tek dogal yol: tamsayi TL fiyatlar 100'un, katsayilar 5'in katinda kurus
    // uretir), 99 PETG+'Diger' = 14800,5 -> 14801 kurus (…,01 icin ayni oyun).
    "('test-kargo-103','h7',7,'Test Kargo 103 TL','Ev','[]','103 TL',0,''), " +
    "('test-kargo-2346','h8',8,'Test Kargo 2346 TL','Ev','[]','2.346 TL',0,''), " +
    "('test-kargo-2500','h9',9,'Test Kargo 2500 TL','Ev','[]','2.500 TL',0,''), " +
    "('test-kargo-99','h10',10,'Test Kargo 99 TL','Ev','[]','99 TL',0,''), " +
    "('test-kargo-2352','h11',11,'Test Kargo 2352 TL','Ev','[]','2.352 TL',0,''), " +
    // test 14 (KDV) spec ornegi: 75 PLA + kargo 250 = brut 325,00 -> net 270,83 + KDV 54,17
    "('test-kdv-75','h12',12,'Test KDV 75 TL','Ev','[]','75 TL',0,''), " +
    // test 5 (parametrik kanal ACIK): id'si GERCEK semayla eslesen sari urun — sunucu
    // SEMALAR.get(id) ile bulur, fiyati kendisi hesaplar (taban fiyat semadan, 100 TL o-ring).
    "('olcuye-ozel-oring-conta','h13',13,'Test Oring (semali sari)','Jeneratör','[]','',1,'');"
  );
  // test 24 (e-posta link + kapak resmi): gorsel kolonu DOLU / BOS(NULL) / enjekte-baslik.
  // Ayri INSERT (gorsel kolonu ile) — ustteki buyuk INSERT'e dokunmadan. XSS urununde baslikta
  // <script> + tirnak var: e-postada KACISLI cikmali. XSS urunun gorseli YOK (img sayisi 1 kalsin).
  wranglerD1(
    "INSERT INTO urunler (id,hash,seq,baslik,kategori,marka,fiyat,parametrik,hs,gorsel) VALUES " +
    "('test-resim-var','h20',20,'Test Resimli Urun','Ev','[]','100 TL',0,''," +
      "'https://media.pruvo3d.com/urunler/test-resim-var-1.jpg'), " +
    "('test-resim-yok','h21',21,'Test Resimsiz Urun','Ev','[]','100 TL',0,'',NULL), " +
    "('test-eposta-xss','h22',22,'Zararlı <script>alert(''x'')</script> \"Baslik\"'," +
      "'Ev','[]','100 TL',0,'',NULL);"
  );
}

// Yerel R2 taklidi (siparis yonetimi /stl ucu): wrangler dev --local, r2 binding'ini
// .wrangler/state altinda simule eder; ayni state'e --local put ile fixture konur.
// d1Kur() .wrangler'i sildigi icin ONDAN SONRA cagrilir.
// COK-PARCA duzeni (mimar duzeltme turu): anahtar stl/<urun-id>/<parca>.stl —
// test-urun-a TEK parca (normalize klasor), test-urun-b IKI parca, test-urun-100 dosyasiz.
const R2_PARCALAR = [
  ["stl/test-urun-a/test-urun-a.stl", "R2TESTSTL test-urun-a uretim dosyasi"],
  ["stl/test-urun-b/govde.stl", "R2TESTSTL b govde parcasi"],
  ["stl/test-urun-b/kapak.stl", "R2TESTSTL b kapak parcasi"],
];
function r2Kur() {
  const dosya = path.join(SHOP, ".test-stl-fixture.stl");
  for (const [anahtar, icerik] of R2_PARCALAR) {
    fs.writeFileSync(dosya, icerik);
    const p = spawnSync("npx", ["--yes", "wrangler@4", "r2", "object", "put",
      "pruvo-ozel/" + anahtar, "--file", dosya, "--local"],
      { cwd: SHOP, encoding: "utf8" });
    if (p.status !== 0) {
      fs.unlinkSync(dosya);
      throw new Error("yerel R2 fixture kurulamadi (" + anahtar + "):\n" +
        ((p.stdout || "") + (p.stderr || "")).slice(-1000));
    }
  }
  fs.unlinkSync(dosya);
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
  // 404 govdesi de dogrulanir ("bulunamadi"): port BASKA bir surecte kaldiysa (16 Tem'de
  // yasandi — ayni portta yabanci bir python sunucusu vardi) onun 404'u worker sanilip
  // tum testler anlamsiz 404'le dusuyordu; simdi erken ve anlasilir patlar.
  for (let i = 0; i < 120; i++) {
    await bekle(1000);
    try {
      const r = await istekHam("GET", WORKER_UC + "/_saglik");
      if (r.kod === 404 && r.metin.includes("bulunamadi")) { return; }
      if (r.kod === 404) {
        throw new Error("port " + WORKER_PORT + " BASKA bir surecte (404 govdesi worker'in " +
          "degil: " + r.metin.slice(0, 120) + ") — KABUL_WORKER_PORT ile bos port sec");
      }
      if (r.kod === 500) {
        throw new Error("worker ayakta ama modul yuklenemiyor (secenekler.js import?):\n" +
          workerLog.slice(-2000));
      }
    } catch (e) {
      if (String(e.message).includes("modul yuklenemiyor") ||
          String(e.message).includes("BASKA bir surecte")) { throw e; }
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
  // sozlesme_onay varsayilan TRUE (kalem 9 sunucu zorunlulugu — tum eski testler onayli
  // musteri gibi davranir); onaysiz senaryo icin ekstra={sozlesme_onay: undefined} gecilir
  // (JSON.stringify undefined alani atar -> alan hic gitmez).
  return istekJson("POST", WORKER_UC + "/baslat",
    Object.assign({ musteri: MUSTERI, sepet, sozlesme_onay: true }, ekstra || {}));
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
  // NOT: katsayi URUN KALEMININ fiyatinda sinanir (basketItems[0].price) — init.price artik
  // TAHSILAT (urun + varsa kargo; 2.500 TL alti sepette +250,00). Kargonun kendisi test 10'da.
  const urunKalemi = (init) => ((init || {}).basketItems || [])
    .filter((b) => b.id !== "gonderim")[0] || {};
  for (const malzeme of Object.keys(SPEC)) {
    const c = await baslatIstek([{ id: "test-urun-100", malzeme: malzeme, renk: "Siyah", adet: 1 }]);
    const init = (await mockOku()).sonInit;
    const p = c.kod === 200 && init ? urunKalemi(init).price : "HATA/" + c.kod;
    olculen[malzeme] = p;
    if (p !== SPEC[malzeme]) {
      hatalar.push(malzeme + ": " + p + " (olmasi gereken " + SPEC[malzeme] + ")");
    }
  }

  // Kusurat + ADET: 333 x 1.30 = 432,90 (yuvarlama YOK); x3 = 1.298,70 (ara yuvarlama da yok —
  // yuvarlansaydi 1.299,00 olurdu).
  const ck = await baslatIstek([{ id: "test-urun-333", malzeme: "PETG", renk: "Siyah", adet: 3 }]);
  const kusurat = ck.kod === 200 ? urunKalemi((await mockOku()).sonInit).price : "HATA/" + ck.kod;
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
  const digerFiyat = cd.kod === 200 ? urunKalemi((await mockOku()).sonInit).price : "HATA/" + cd.kod;
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
  const p99 = c99.kod === 200 ? urunKalemi((await mockOku()).sonInit).price : "HATA/" + c99.kod;
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
  // Taban fiyat semadan bagimsiz sabitlenir (100 TL): gercek deger degisse de
  // testin bekledigi 18400 kurus sabiti gecerli kalsin.
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
  // Taban fiyati NULL sema (sari fiyat paketiyle gercek semalar doldu; red yolu
  // sentetik null ile sinanir — vida da dolarsa test bozulmasin).
  const r3 = PAR.parametrikHesapla({ id: sema.id, malzeme: "PLA", renk: "Siyah",
    parametreler: vd, adet: 1 }, SECENEK, Object.assign({}, sema, { tabanFiyatTL: null }));
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

  rapor("9 parametrik altyapi (kanal ACIK; hesap tek kaynak sunucuda)", hatalar.length === 0,
    "sema kapsami " + listelenen.size + "/" + dizin.size + "; sunucu yeniden hesap=" +
    (sonuc.hata ? "HATA" : kurusMetin(sonuc.birimKurus) + " (istemcinin sahte hacim=1/fiyat=1 " +
     "YOK SAYILDI, konfiguratorle birebir)") + "; red yollari: aralik/bilinmeyen/taban-yok/" +
    "parametresiz OK; bundle dry-run=" + (dryOk ? "kuruldu" : "PATLADI") +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 10 — KARGO KURALI (Okan, 16 Tem — KESIN; tools/paket-shop-kargo.md).
 *  Beklenen degerler SPEC'ten SABIT (secenekler.js'ten TURETILMEZ — kural yanlis
 *  degistirilirse test yakalasin): urun toplami < 2.500,00 TL -> kargo 250,00 TL;
 *  >= 2.500,00 TL (tam 2.500 DAHIL) -> kargo 0. Kargo iyzico'ya AYRI kalem, D1'e
 *  kargo_kurus kolonu; istemcinin yolladigi kargo/tutar alanlari YOK SAYILIR. */
async function test10Kargo() {
  const hatalar = [];

  // (a) 2.499,99 TL urun toplami -> kargo 250,00, tahsilat 2.749,99 (kurus birebir).
  //     Istemci sahte kargo/tutar da yollar (spec d) -> yok sayilmali.
  //     2346 PLA (234600) + 103 PETG 'Diger' (15398,5 -> 15399) = 249999 kurus.
  const ca = await baslatIstek(
    [{ id: "test-kargo-2346", malzeme: "PLA", renk: "Siyah", adet: 1, kargo: 0, tutar: 1 },
     { id: "test-kargo-103", malzeme: "PETG", renk: "Diğer", renk_ozel: "mor", adet: 1 }],
    { kargo: 0, kargo_kurus: 0, tutar: 1, toplam: 1 });
  const ia = ca.kod === 200 ? (await mockOku()).sonInit : null;
  const aFiyat = ia ? ia.price : "HATA/" + ca.kod;
  const aPaid = ia ? ia.paidPrice : "?";
  if (aFiyat !== "2749.99" || aPaid !== "2749.99") {
    hatalar.push("2.499,99'luk sepet tahsilati: " + aFiyat + "/" + aPaid +
      " (olmasi gereken 2749.99 — kargo 250,00 eklenmiyor ya da istemcinin kargo:0'i kazandi)");
  }
  // Kargo iyzico'ya AYRI kalem gider; basketItems toplami = price kurali mock'ta da sinaniyor.
  const aKargoKalem = ia ? (ia.basketItems || []).filter((b) => b.id === "gonderim") : [];
  if (aKargoKalem.length !== 1 || (aKargoKalem[0] || {}).price !== "250.00") {
    hatalar.push("kargo kalemi iyzico sepetinde yok/yanlis: " + JSON.stringify(aKargoKalem));
  }
  // (e) D1: urun toplami ve kargo AYRI kolonlarda, kurusuyla.
  const aSatir = d1Sorgu("SELECT tutar_kurus, kargo_kurus FROM siparisler WHERE siparis_no = '" +
    ((ca.govde || {}).no || "-") + "'")[0] || {};
  if (aSatir.tutar_kurus !== 249999 || aSatir.kargo_kurus !== 25000) {
    hatalar.push("D1 (a): " + JSON.stringify(aSatir) +
      " (olmasi gereken tutar_kurus=249999, kargo_kurus=25000)");
  }

  // (b) TAM 2.500,00 TL -> kargo 0 (sinir DAHIL bedava).
  const cb = await baslatIstek([{ id: "test-kargo-2500", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const ib = cb.kod === 200 ? (await mockOku()).sonInit : null;
  const bFiyat = ib ? ib.price : "HATA/" + cb.kod;
  if (bFiyat !== "2500.00") {
    hatalar.push("tam 2.500 sepeti: " + bFiyat + " (olmasi gereken 2500.00 — sinir DAHIL bedava)");
  }
  if (ib && (ib.basketItems || []).some((b) => b.id === "gonderim")) {
    hatalar.push("tam 2.500'de iyzico sepetine kargo kalemi girdi");
  }
  const bSatir = d1Sorgu("SELECT tutar_kurus, kargo_kurus FROM siparisler WHERE siparis_no = '" +
    ((cb.govde || {}).no || "-") + "'")[0] || {};
  if (bSatir.tutar_kurus !== 250000 || bSatir.kargo_kurus !== 0) {
    hatalar.push("D1 (b): " + JSON.stringify(bSatir) +
      " (olmasi gereken tutar_kurus=250000, kargo_kurus=0)");
  }

  // (c) 2.500,01 TL -> kargo 0. 2352 PLA (235200) + 99 PETG 'Diger' (14800,5 -> 14801) = 250001.
  const cc = await baslatIstek(
    [{ id: "test-kargo-2352", malzeme: "PLA", renk: "Siyah", adet: 1 },
     { id: "test-kargo-99", malzeme: "PETG", renk: "Diğer", renk_ozel: "mor", adet: 1 }]);
  const ic = cc.kod === 200 ? (await mockOku()).sonInit : null;
  const cFiyat = ic ? ic.price : "HATA/" + cc.kod;
  if (cFiyat !== "2500.01") {
    hatalar.push("2.500,01'lik sepet: " + cFiyat + " (olmasi gereken 2500.01, kargosuz)");
  }

  // (d-devam) 2.500 ALTI sepette istemci "kargom bedava/tutarim yuksek" der -> sunucu kazanir.
  const cd = await baslatIstek(
    [{ id: "test-urun-333", malzeme: "PETG", renk: "Siyah", adet: 1, kargo_kurus: 0 }],
    { kargo: "bedava", kargo_kurus: 0, tutar: 999999 });
  const idd = cd.kod === 200 ? (await mockOku()).sonInit : null;
  const dFiyat = idd ? idd.price : "HATA/" + cd.kod;
  // 333 x 1.30 = 432,90 + kargo 250,00 = 682,90
  if (dFiyat !== "682.90") {
    hatalar.push("kucuk sepette istemci kargo alanlari: " + dFiyat +
      " (olmasi gereken 682.90 — sunucu degeri kazanmali)");
  }

  rapor("10 kargo kurali", hatalar.length === 0,
    "2.499,99 -> tahsilat " + aFiyat + " (kargo kalemi " +
    ((aKargoKalem[0] || {}).price || "YOK") + ", D1 " + JSON.stringify(aSatir) +
    "); tam 2.500 -> " + bFiyat + " (D1 " + JSON.stringify(bSatir) +
    "); 2.500,01 -> " + cFiyat + "; sahte istemci kargo/tutar -> " + dFiyat +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 11 — RETRIEVE ALTYAPI HATASI (DEVAM.md bulgusu, 16 Tem; mimar atadi).
 *  /donus'ta retrieve CEVAP VEREMEZSE (status:failure — or. 1001 anahtar/URL uyusmazligi)
 *  odemenin gercek durumu BILINMEZ: siparis 'basarisiz' DEGIL 'incele' olmali + Telegram
 *  uyarisi gitmeli (parasi cekilmis musteri sessizce dusmesin). Retrieve duzelince ayni
 *  token 'odendi'ye ilerleyebilmeli. */
async function test11RetrieveHatasi() {
  const hatalar = [];
  const c = await baslatIstek([{ id: "test-urun-a", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  if (c.kod !== 200) {
    return rapor("11 retrieve altyapi hatasi", false, "baslat: " + c.kod);
  }
  const token = (await mockOku()).sonToken;
  const tgOnce = (await mockOku()).telegramSayisi;

  await istekJson("GET", "http://127.0.0.1:" + MOCK_PORT + "/_detayhata/ac");
  const d1c = await donusIstek(token);
  const s1 = d1Sorgu("SELECT durum FROM siparisler WHERE token = '" + token + "'")[0] || {};
  const m1 = await mockOku();
  if (s1.durum !== "incele") {
    hatalar.push("retrieve hatasinda durum '" + s1.durum + "' (olmasi gereken 'incele')");
  }
  if (d1c.kod !== 303 || !d1c.yer.includes("siparis=hata")) {
    hatalar.push("musteri yonlendirmesi: " + d1c.kod + " " + d1c.yer);
  }
  const uyari = m1.telegramSayisi === tgOnce + 1 &&
    String((m1.sonTelegram || {}).text || "").includes("RETRIEVE HATASI");
  if (!uyari) {
    hatalar.push("Telegram uyarisi gitmedi/yanlis (sayi " + tgOnce + "->" + m1.telegramSayisi + ")");
  }

  // Duzelme: retrieve tekrar cevap verirse ayni token 'odendi'ye ILERLEYEBILMELI.
  await istekJson("GET", "http://127.0.0.1:" + MOCK_PORT + "/_detayhata/kapat");
  await donusIstek(token);
  const s2 = d1Sorgu("SELECT durum FROM siparisler WHERE token = '" + token + "'")[0] || {};
  if (s2.durum !== "odendi") {
    hatalar.push("duzelen retrieve sonrasi durum '" + s2.durum + "' (olmasi gereken 'odendi')");
  }

  rapor("11 retrieve altyapi hatasi", hatalar.length === 0,
    "1001 -> durum=" + s1.durum + ", yonlendirme=" + d1c.yer.split("?")[1] +
    ", Telegram uyarisi=" + (uyari ? "gitti" : "YOK") +
    "; retrieve duzelince -> " + s2.durum +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 12 — SIPARIS NUMARASI (kalem 5, zorunlu tum siparislerde): Ege/Sheet ailesiyle ayni
 *  desen PR-yyMMdd-HHmmss + ayni-saniye carpismasina karsi kisa sonek; sunucuda uretilir,
 *  iyzico conversationId/basketId ile eslesir, musteri donusunde ve Telegram'da gorunur. */
async function test12SiparisNo() {
  const hatalar = [];
  const FORMAT = /^PR-[0-9]{6}-[0-9]{6}-[A-Z0-9]{3,6}$/;

  // Ayni saniyede iki siparis -> iki FARKLI numara (carpisma testi)
  const [c1, c2] = await Promise.all([
    baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }]),
    baslatIstek([{ id: "test-urun-100", malzeme: "PETG", renk: "Siyah", adet: 1 }]),
  ]);
  const n1 = (c1.govde || {}).no || "", n2 = (c2.govde || {}).no || "";
  if (!FORMAT.test(n1) || !FORMAT.test(n2)) {
    hatalar.push("format: '" + n1 + "' / '" + n2 + "' (beklenen PR-yyMMdd-HHmmss-SONEK)");
  }
  if (!n1 || n1 === n2) { hatalar.push("ayni saniyede AYNI numara: " + n1); }

  // conversationId + basketId eslesmesi — sirali tek istek (sonInit kesin bu siparisin)
  const c3 = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const n3 = (c3.govde || {}).no || "";
  const i3 = (await mockOku()).sonInit || {};
  if (!n3 || i3.conversationId !== n3 || i3.basketId !== n3) {
    hatalar.push("conversationId/basketId eslesmesi: no=" + n3 + " conv=" + i3.conversationId +
      " basket=" + i3.basketId);
  }

  // Musteri donus sayfasi (siparis=ok&no=...) + Telegram bildiriminde numara
  const t3 = (await mockOku()).sonToken;
  const d3 = await donusIstek(t3);
  await bekle(300);   // telegram ctx.waitUntil ile gider
  const m3 = await mockOku();
  const tgMetin = String((m3.sonTelegram || {}).text || "");
  if (d3.kod !== 303 || d3.yer.indexOf("no=" + encodeURIComponent(n3)) === -1) {
    hatalar.push("donus sayfasinda numara yok: " + d3.kod + " -> " + d3.yer);
  }
  if (tgMetin.indexOf(n3) === -1) {
    hatalar.push("telegram bildiriminde numara yok: " + tgMetin.slice(0, 100));
  }

  rapor("12 siparis numarasi", hatalar.length === 0,
    "ayni saniye: " + n1 + " / " + n2 + "; conversationId eslesti (" + n3 +
    "); donus=" + d3.yer +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 13 — HAVALE/EFT (kalem 6): siparis D1'e 'havale-bekliyor' + dogru kargo + dogru toplam;
 *  musteri ekranindaki TAM tutar = D1'deki tahsilat (tutar_kurus + kargo_kurus) BIREBIR;
 *  iyzico oturumu ACILMAZ; Telegram'a "HAVALE BEKLENIYOR" duser ama 'odeme geldi' DEMEZ;
 *  durum istemciden DEGISTIRILEMEZ (negatif); onay = KURULUM.md'deki wrangler komutu. */
async function test13Havale() {
  const hatalar = [];
  const once = await mockOku();

  // urun 100,00 TL -> kargo kurali havalede de AYNEN: +250,00 -> odenecek TAM tutar 350,00
  const c = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1,
    tutar: 1 }], { odeme: "havale", tutar: 1, toplam: 1 });
  const g = c.govde || {};
  if (c.kod !== 200 || g.havale !== true || g.url) {
    hatalar.push("havale cevabi: " + c.kod + " " + JSON.stringify(g).slice(0, 160) +
      " (havale:true beklenir, iyzico url'i BEKLENMEZ)");
  }
  if (g.iban !== TEST_IBAN || g.unvan !== TEST_UNVAN) {
    hatalar.push("iban/unvan tek kaynaktan gelmedi: " + g.iban + " / " + g.unvan);
  }
  if (g.tutar_kurus !== 35000 || g.tutar !== "350,00 TL") {
    hatalar.push("musteri ekrani tutari: " + g.tutar_kurus + " / " + g.tutar +
      " (olmasi gereken 35000 / 350,00 TL — kargo dahil TAM tutar)");
  }

  const satir = g.no ? d1Sorgu("SELECT durum, tutar_kurus, kargo_kurus, odeme_yontemi, token " +
    "FROM siparisler WHERE siparis_no = '" + g.no + "'")[0] : null;
  if (!satir || satir.durum !== "havale-bekliyor" || satir.odeme_yontemi !== "havale") {
    hatalar.push("D1 durumu: " + JSON.stringify(satir || null) + " (havale-bekliyor olmali)");
  }
  // Konvansiyon (devir notu): tutar_kurus = URUN toplami, kargo ayri; tahsilat = toplam.
  if (satir && (satir.tutar_kurus !== 10000 || satir.kargo_kurus !== 25000)) {
    hatalar.push("D1 tutar/kargo: " + JSON.stringify(satir) + " (10000/25000 olmali)");
  }
  if (satir && g.tutar_kurus !== satir.tutar_kurus + satir.kargo_kurus) {
    hatalar.push("EKRAN != D1 tahsilati: " + g.tutar_kurus + " != " +
      (satir.tutar_kurus + satir.kargo_kurus));
  }

  await bekle(300);
  const m = await mockOku();
  if (m.initSayisi !== once.initSayisi) {
    hatalar.push("havalede iyzico oturumu ACILDI (" + once.initSayisi + "->" + m.initSayisi + ")");
  }
  const tg = String((m.sonTelegram || {}).text || "");
  if (m.telegramSayisi === once.telegramSayisi || tg.indexOf("HAVALE BEKLENIYOR") === -1 ||
      tg.indexOf(g.no || "YOK") === -1 || tg.indexOf("350,00 TL") === -1) {
    hatalar.push("telegram HAVALE bildirimi eksik/yanlis: " + tg.slice(0, 140));
  }
  if (/odendi|YENI SIPARIS/i.test(tg)) {
    hatalar.push("para gorulmeden 'odeme geldi' tonunda bildirim atildi: " + tg.slice(0, 100));
  }

  // NEGATIF: istemcinin erisebildigi hicbir uc havale siparisini 'odendi' YAPAMAZ.
  // (Havale satirinin token'i NULL -> /donus onu hicbir token'la bulamaz; uydurma token 404.)
  const neg = await donusIstek("uydurma-havale-onay-denemesi");
  const s2 = g.no ? d1Sorgu("SELECT durum FROM siparisler WHERE siparis_no = '" + g.no + "'")[0]
    : null;
  const m2 = await mockOku();
  if (neg.kod !== 404 || !s2 || s2.durum !== "havale-bekliyor") {
    hatalar.push("negatif test: donus=" + neg.kod + " durum=" + JSON.stringify(s2) +
      " (404 / havale-bekliyor kalmali)");
  }
  if (m2.telegramSayisi !== m.telegramSayisi) { hatalar.push("negatif test: ek bildirim atildi"); }

  // ONAY YOLU: shop/KURULUM.md'de belgelenen wrangler d1 komutunun SQL'i (Okan dekontu
  // gorunce) — durum ancak BU yoldan 'odendi' olur.
  wranglerD1("UPDATE siparisler SET durum='odendi' " +
    "WHERE siparis_no='" + g.no + "' AND durum='havale-bekliyor'");
  const s3 = g.no ? d1Sorgu("SELECT durum FROM siparisler WHERE siparis_no = '" + g.no + "'")[0]
    : null;
  if (!s3 || s3.durum !== "odendi") {
    hatalar.push("onay komutu calismadi: " + JSON.stringify(s3));
  }

  rapor("13 havale/eft", hatalar.length === 0,
    "no=" + (g.no || "?") + " ekran=" + g.tutar + " D1=" + JSON.stringify(satir || null) +
    "; iyzico oturumu acilmadi; telegram=HAVALE BEKLENIYOR; negatif=degistirilemedi; " +
    "onay komutu -> odendi" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 14 — KDV AYRISTIRMASI (kalem 8; Okan KESIN %20). Tahsilat DEGISMEZ — yalniz dokum +
 *  kayit. net = brut/(1+oran) kurusta; net + KDV = brut BIREBIR (fark KDV'ye yedirilir);
 *  dokum KARGO DAHIL genel toplam uzerinden. D1'e kdv_kurus; donus sayfasina dokum. */
async function test14Kdv() {
  const hatalar = [];

  // (a) SPEC ornegi: 75 PLA (7500) + kargo 25000 = brut 32500 -> net 27083 + KDV 5417.
  const bek = specKdv(32500);
  if (bek.net !== 27083 || bek.kdv !== 5417) {
    hatalar.push("spec ornegi hesap: " + JSON.stringify(bek) + " (27083/5417 olmali)");
  }
  const ca = await baslatIstek([{ id: "test-kdv-75", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const ia = ca.kod === 200 ? (await mockOku()).sonInit : null;
  if (!ia || ia.price !== "325.00") {
    hatalar.push("tahsilat degisti: " + (ia ? ia.price : "HATA/" + ca.kod) +
      " (325.00 kalmali — KDV yalniz dokum)");
  }
  const da = (ca.govde || {}).no ? d1Sorgu("SELECT tutar_kurus, kargo_kurus, kdv_kurus " +
    "FROM siparisler WHERE siparis_no = '" + ca.govde.no + "'")[0] : null;
  if (!da || da.kdv_kurus !== 5417) {
    hatalar.push("D1 kdv_kurus: " + JSON.stringify(da || null) + " (5417 olmali)");
  }
  if (da && da.tutar_kurus + da.kargo_kurus !== 32500) {
    hatalar.push("D1 brut bozuldu: " + JSON.stringify(da));
  }

  // Donus sayfasi dokumu: yonlendirmede tutar+kdv paramlari (istemci dokumu bunlardan basar).
  const ta = (await mockOku()).sonToken;
  const dn = await donusIstek(ta);
  if (dn.kod !== 303 || dn.yer.indexOf("t=32500") === -1 || dn.yer.indexOf("kdv=5417") === -1) {
    hatalar.push("donus dokum paramlari yok: " + dn.yer);
  }

  // (b) kargosuz senaryo: 2.500,00 (tam esik, kargo 0) -> net 208333 + KDV 41667 = 250000.
  const cb = await baslatIstek([{ id: "test-kargo-2500", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const db = (cb.govde || {}).no ? d1Sorgu("SELECT tutar_kurus, kargo_kurus, kdv_kurus " +
    "FROM siparisler WHERE siparis_no = '" + cb.govde.no + "'")[0] : null;
  const bekB = specKdv(250000);
  if (!db || db.kdv_kurus !== bekB.kdv || db.tutar_kurus + db.kargo_kurus !== 250000) {
    hatalar.push("kargosuz: " + JSON.stringify(db || null) + " (kdv " + bekB.kdv + " olmali)");
  }

  // (c) havale cevabinda dokum alanlari (musteri ekrani ayni rakamlari gosterir)
  const cc = await baslatIstek([{ id: "test-kdv-75", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    { odeme: "havale" });
  const gc = cc.govde || {};
  if (gc.kdv_kurus !== 5417 || gc.net_kurus !== 27083) {
    hatalar.push("havale cevabi dokum: kdv=" + gc.kdv_kurus + " net=" + gc.net_kurus +
      " (5417/27083 olmali)");
  }

  rapor("14 kdv ayristirmasi", hatalar.length === 0,
    "325,00 brut -> D1 " + JSON.stringify(da || null) + " (net+kdv=brut birebir); " +
    "donus paramlari: " + (dn ? dn.yer.split("?")[1] : "?") + "; kargosuz kdv=" +
    ((db || {}).kdv_kurus) + "; havale dokumu net=" + gc.net_kurus + "/kdv=" + gc.kdv_kurus +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 15 — SOZLESME ONAYI (kalem 9, yasal): /baslat'ta onay alani yoksa 400 (sunucu zorunlu,
 *  istemci kutusu yetmez); onayli istekte D1'e sozlesme_onay ZAMAN DAMGASI (ispat kaydi).
 *  Kart VE havale ayni /baslat'tan gectigi icin denetim ikisini de kapsar. */
async function test15SozlesmeOnayi() {
  const hatalar = [];
  const onceInit = (await mockOku()).initSayisi;
  const onceSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;

  // Onaysiz (alan hic yok) -> 400; siparis olusmaz, iyzico oturumu acilmaz.
  const c1 = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    { sozlesme_onay: undefined });
  // 'true' disinda her deger de RED (istemci kodu bozulursa sessizce onayli sayilmasin).
  const c2 = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    { sozlesme_onay: "evet" });
  const sonraInit = (await mockOku()).initSayisi;
  const sonraSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  if (c1.kod !== 400 || c1.govde.hata !== "sozlesme-onay-yok") {
    hatalar.push("onaysiz istek: " + c1.kod + "/" + c1.govde.hata + " (400/sozlesme-onay-yok olmali)");
  }
  if (c2.kod !== 400) { hatalar.push("onay='evet' (true degil): " + c2.kod + " (400 olmali)"); }
  if (sonraInit !== onceInit || sonraSiparis !== onceSiparis) {
    hatalar.push("onaysiz istekte iyzico/siparis olustu (" + onceInit + "->" + sonraInit +
      ", " + onceSiparis + "->" + sonraSiparis + ")");
  }

  // Onayli (kart) -> D1'de ISO zaman damgasi. Havale yolu icin de ayni kolon (test 13 kaydi).
  const c3 = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const s3 = (c3.govde || {}).no ? d1Sorgu("SELECT sozlesme_onay FROM siparisler " +
    "WHERE siparis_no = '" + c3.govde.no + "'")[0] : null;
  const DAMGA = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
  if (!s3 || !DAMGA.test(String(s3.sozlesme_onay || ""))) {
    hatalar.push("onayli istekte damga yok: " + JSON.stringify(s3 || null));
  }
  const sHavale = d1Sorgu("SELECT sozlesme_onay FROM siparisler WHERE odeme_yontemi='havale' " +
    "ORDER BY id DESC LIMIT 1")[0];
  if (!sHavale || !DAMGA.test(String(sHavale.sozlesme_onay || ""))) {
    hatalar.push("havale siparisinde damga yok: " + JSON.stringify(sHavale || null));
  }

  rapor("15 sozlesme onayi", hatalar.length === 0,
    "onaysiz=" + c1.kod + "/" + (c1.govde || {}).hata + ", 'evet'=" + c2.kod +
    " (siparis/iyzico olusmadi); onayli damga=" + JSON.stringify((s3 || {}).sozlesme_onay) +
    "; havale damga=" + JSON.stringify((sHavale || {}).sozlesme_onay) +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

async function test5Parametrik() {
  /* KANAL ACIK (mimar karari + Okan onayi, 17 Tem): SEMALI sari urun kartla odenebilir
     (fiyat sunucudan — birim dogrulugunu test 9 kanitlar); SEMASIZ parametrik ve fiyatsiz
     urun WhatsApp'a yonlenmeye devam eder, red yollari iyzico oturumu ACMAZ. */
  const onceInit = (await mockOku()).initSayisi;
  const onceSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  const c1 = await baslatIstek([{ id: "test-parametrik", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const c2 = await baslatIstek([{ id: "test-fiyatsiz", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const araInit = (await mockOku()).initSayisi;
  const araSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  // Semali sari urun: gecerli parametre seti (konfigurator varsayilanlari) + istemcinin
  // SAHTE hacim/fiyati -> KABUL edilmeli; sunucu sahte alanlari yok sayar (test 9b).
  const KONF5 = require(path.join(KOK, "jenerator", "konfigurator.js"));
  const oringSema = JSON.parse(fs.readFileSync(
    path.join(KOK, "jenerator", "urunler", "olcuye-ozel-oring-conta.json"), "utf8"));
  const kalem = { id: "olcuye-ozel-oring-conta", malzeme: "PLA", renk: "Siyah", adet: 1,
    parametreler: KONF5.varsayilanDegerler(oringSema), hacim_mm3: 1, parametrik_fiyat_kurus: 1 };
  const c4 = await baslatIstek([kalem]);
  const c3 = await baslatIstek([
    { id: "test-urun-a", malzeme: "PLA", renk: "Siyah", adet: 1 }, kalem]); // karisik sepet de KABUL
  const sonInit = (await mockOku()).initSayisi;
  const sonSiparis = d1Sorgu("SELECT COUNT(*) AS n FROM siparisler")[0].n;
  const ok = c1.kod === 400 && c1.govde.hata === "parametrik-urun" &&
    c2.kod === 400 && c2.govde.hata === "fiyatsiz-urun" &&
    araInit === onceInit && araSiparis === onceSiparis &&
    c4.kod === 200 && c3.kod === 200 &&
    sonInit === araInit + 2 && sonSiparis === araSiparis + 2;
  rapor("5 parametrik kanal (semali KABUL, semasiz/fiyatsiz RED)", ok,
    "semasiz=" + c1.kod + "/" + (c1.govde || {}).hata + ", fiyatsiz=" + c2.kod + "/" +
    (c2.govde || {}).hata + ", semali=" + c4.kod + ", karisik=" + c3.kod +
    "; iyzico oturumu: redlerde ACILMADI (" + onceInit + "->" + araInit +
    "), kabullerde +2 (" + araInit + "->" + sonInit + ")");
}

/** 16 — CALLBACK TUTAR UYUSMAZLIGI: musteri gorunumu (mimar paketi kalem 1).
 *  iyzico'da odeme BASARILI ama tahsilat bizim kayitla uyusmuyor -> siparis 'incele' +
 *  Telegram TUTARSIZLIK (bunlara DOKUNULMADI). ESKI kod musteriye HAM 409 JSON donuyordu;
 *  musteri iyzico'dan donerken TARAYICIDADIR -> artik siteye 303 redirect (siparis=hata),
 *  retrieve-altyapi-hatasi koluyla AYNI desen. */
async function test16CallbackTutarUyusmazligi() {
  const hatalar = [];
  const c = await baslatIstek([{ id: "test-urun-a", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  if (c.kod !== 200) { return rapor("16 callback tutar uyusmazligi", false, "baslat: " + c.kod); }
  const no = c.govde.no;
  const token = (await mockOku()).sonToken;
  const tgOnce = (await mockOku()).telegramSayisi;

  // Kayitli tahsilati bozarak yapay uyusmazlik yarat (iyzico paidPrice degismedi):
  // beklenenTahsilat = tutar_kurus + kargo -> retrieve'in dondugu tutarla artik tutmaz.
  wranglerD1("UPDATE siparisler SET tutar_kurus = tutar_kurus + 100 WHERE siparis_no = '" + no + "'");

  const d = await donusIstek(token);
  const s = d1Sorgu("SELECT durum FROM siparisler WHERE siparis_no = '" + no + "'")[0] || {};
  const m = await mockOku();

  // (a) ESKI KIRMIZI KANIT: eski kod 409 JSON (Location'siz) donerdi; artik 303 + Location
  //     SITEYE (env.SITE_URL — retrieve-hata koluyla ayni; harness'te worker origin'ine coz).
  //     Mutlak URL + siparis=hata + no: ham JSON degil, siteye tam yonlendirme.
  if (d.kod !== 303) { hatalar.push("HTTP " + d.kod + " (303 redirect olmali, 409 JSON DEGIL)"); }
  if (!/^https?:\/\//.test(d.yer) || d.yer.indexOf("siparis=hata") === -1) {
    hatalar.push("Location siteye tam yonlendirme degil: " + d.yer);
  }
  if (d.yer.indexOf("no=" + encodeURIComponent(no)) === -1) {
    hatalar.push("Location'da siparis no yok: " + d.yer);
  }
  // (b) durum/Telegram DAVRANISI KORUNDU (mimar: dokunma) — 'incele' + TUTARSIZLIK uyarisi.
  if (s.durum !== "incele") { hatalar.push("durum '" + s.durum + "' (incele olmali)"); }
  const uyari = m.telegramSayisi === tgOnce + 1 &&
    String((m.sonTelegram || {}).text || "").includes("TUTARSIZLIK");
  if (!uyari) { hatalar.push("Telegram TUTARSIZLIK uyarisi gitmedi (" + tgOnce + "->" +
    m.telegramSayisi + ")"); }

  rapor("16 callback tutar uyusmazligi", hatalar.length === 0,
    "HTTP " + d.kod + " -> " + d.yer + "; durum=" + s.durum + "; Telegram uyarisi=" +
    (uyari ? "gitti" : "YOK") + (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 17 — PARAMETRIK SATIR AYIRT EDILEBILIRLIGI (mimar paketi kalem 2): ayni sari urun FARKLI
 *  olculerle iki satir -> iyzico'ya giden basketItems'ta 2 BENZERSIZ id + adlarda olcu ozeti;
 *  Telegram bildiriminde iki satir birbirinden ayirt edilebilir. */
async function test17ParametrikSatirAyirt() {
  const hatalar = [];
  const KONF = require(path.join(KOK, "jenerator", "konfigurator.js"));
  const sema = JSON.parse(fs.readFileSync(
    path.join(KOK, "jenerator", "urunler", "olcuye-ozel-oring-conta.json"), "utf8"));
  const vd = KONF.varsayilanDegerler(sema);
  const set1 = Object.assign({}, vd, { ic_cap: 30 });   // farkli ic cap -> farkli olcu/fiyat
  const set2 = Object.assign({}, vd, { ic_cap: 40 });
  const detay1 = KONF.detayMetni(sema, set1);
  const detay2 = KONF.detayMetni(sema, set2);

  const c = await baslatIstek([
    { id: "olcuye-ozel-oring-conta", malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: set1 },
    { id: "olcuye-ozel-oring-conta", malzeme: "PLA", renk: "Siyah", adet: 1, parametreler: set2 },
  ]);
  if (c.kod !== 200) {
    return rapor("17 parametrik satir ayirt", false,
      "baslat: " + c.kod + " " + JSON.stringify(c.govde));
  }
  const init = (await mockOku()).sonInit;
  const urunKalem = (init.basketItems || []).filter((b) => b.id !== "gonderim");

  // (a) iki BENZERSIZ id (ayni urun id'si tekrar edince #1/#2 son eki)
  const idler = urunKalem.map((b) => b.id);
  if (idler.length !== 2 || new Set(idler).size !== 2) {
    hatalar.push("basketItems id benzersiz degil: " + JSON.stringify(idler));
  }
  if (!idler.every((x) => x.indexOf("olcuye-ozel-oring-conta#") === 0)) {
    hatalar.push("id son eki (#1/#2) yok: " + JSON.stringify(idler));
  }
  // (b) adlarda olcu ozeti + iki ad birbirinden FARKLI
  const ad1 = (urunKalem[0] || {}).name || "", ad2 = (urunKalem[1] || {}).name || "";
  if (!ad1.includes(detay1.slice(0, 60)) || !ad2.includes(detay2.slice(0, 60))) {
    hatalar.push("adlarda olcu ozeti yok: [" + ad1 + "] / [" + ad2 + "]");
  }
  if (ad1 === ad2) { hatalar.push("iki satir adi AYNI: " + ad1); }

  // (c) Telegram bildiriminde iki satir ayirt edilebilir (odeme SUCCESS -> siparisMesaji)
  const token = (await mockOku()).sonToken;
  const d = await donusIstek(token);
  await bekle(300);
  const tg = String(((await mockOku()).sonTelegram || {}).text || "");
  if (d.kod !== 303) { hatalar.push("donus HTTP " + d.kod); }
  if (!tg.includes(detay1) || !tg.includes(detay2)) {
    hatalar.push("Telegram'da iki olcu detayi ayirt edilemiyor: " + tg.slice(0, 200));
  }

  rapor("17 parametrik satir ayirt", hatalar.length === 0,
    "basketItems id=" + JSON.stringify(idler) + "; adlar ayri=" + (ad1 !== ad2) +
    "; Telegram iki detay=" + (tg.includes(detay1) && tg.includes(detay2)) +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

// ---------------------------------------------------------------- SIPARIS YONETIMI
// (tools/paket-siparis-yonetimi.md kabul 1-4 + 7; ONCE-KIRMIZI: bu testler uclar yokken
// 404/eksik-kolon ile kirmizi yanar — kanit icin src'siz kosum RAPOR-MIMARA.md'de.)

async function yonetIstek(yontem, altYol, govdeObj, anahtar) {
  const basliklar = {};
  if (anahtar !== null) { basliklar["X-Yonet-Anahtar"] = anahtar === undefined ? TEST_YONET : anahtar; }
  if (govdeObj) { basliklar["Content-Type"] = "application/json"; }
  const c = await istekHam(yontem, WORKER_UC + "/yonet" + altYol, basliklar,
    govdeObj ? JSON.stringify(govdeObj) : null);
  let j = {};
  try { j = JSON.parse(c.metin); } catch (e) { /* HTML/binary yanit */ }
  return { kod: c.kod, govde: j, metin: c.metin, bas: c.bas };
}

/** 18 — YONETIM YETKISI (kabul 1): anahtarsiz/yanlis anahtar -> 404 (varlik sizmasin);
 *  dogru anahtar -> sayfa HTML + liste JSON (onceki testlerin fixture siparisleriyle). */
async function test18YonetimYetkisi() {
  const hatalar = [];
  // anahtarsiz (baslik hic yok) + yanlis anahtar -> 404, gövde jenerik
  const c1 = await yonetIstek("GET", "/liste", null, null);
  const c2 = await yonetIstek("GET", "/liste", null, "yanlis-anahtar");
  const c3 = await yonetIstek("GET", "/", null, null);
  for (const [ad, c] of [["anahtarsiz liste", c1], ["yanlis anahtar", c2], ["anahtarsiz sayfa", c3]]) {
    if (c.kod !== 404) { hatalar.push(ad + ": " + c.kod + " (404 olmali)"); }
    if ((c.metin || "").includes(TEST_YONET)) { hatalar.push(ad + ": anahtar yanita sizdi"); }
  }
  // dogru anahtar (query parametresiyle de) -> liste JSON
  const c4 = await yonetIstek("GET", "/liste", null, undefined);
  if (c4.kod !== 200 || !Array.isArray(c4.govde.siparisler) || c4.govde.siparisler.length < 1) {
    hatalar.push("dogru anahtar liste: " + c4.kod + " " + JSON.stringify(c4.govde).slice(0, 120));
  }
  const ilk = (c4.govde.siparisler || [])[0] || {};
  if (!ilk.siparis_no || !ilk.musteri || !Array.isArray(ilk.kalemler)) {
    hatalar.push("liste satiri eksik alan: " + JSON.stringify(ilk).slice(0, 160));
  }
  const ilkKalem = (ilk.kalemler || [])[0];
  if (ilkKalem && !ilkKalem.baski_oneri) {
    hatalar.push("baski fisi onerisi yok: " + JSON.stringify(ilkKalem).slice(0, 160));
  }
  // sayfa HTML (query anahtariyla — telefon kullanimi)
  const c5 = await istekHam("GET", WORKER_UC + "/yonet?anahtar=" + TEST_YONET);
  if (c5.kod !== 200 || !/Sipariş Yönetimi/.test(c5.metin)) {
    hatalar.push("yonetim sayfasi: " + c5.kod);
  }
  // durum suzgeci
  const c6 = await yonetIstek("GET", "/liste?durum=havale-bekliyor", null, undefined);
  const hepsiHavale = (c6.govde.siparisler || []).every((s) => s.durum === "havale-bekliyor");
  if (c6.kod !== 200 || !hepsiHavale) { hatalar.push("durum suzgeci calismadi"); }
  rapor("18 yonetim yetkisi", hatalar.length === 0,
    "anahtarsiz/yanlis/sayfa=404; dogru anahtar liste=" + (c4.govde.siparisler || []).length +
    " siparis; sayfa HTML ok; suzgec ok" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 19 — DURUM MAKINESI (kabul 2): izinli gecisler yesil; izinsiz 400; 'kargolandi'ya
 *  /durum'dan GECILMEZ (tek yol /kargo); durum_gecmisi ayni satira islenir. */
async function test19DurumMakinesi() {
  const hatalar = [];
  // Taze havale siparisi (havale-bekliyor fixture'i)
  const c = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    { odeme: "havale" });
  const no = (c.govde || {}).no;
  if (!no) { return rapor("19 durum makinesi", false, "havale baslat: " + c.kod); }

  // izinsiz: havale-bekliyor -> uretimde (once odendi olmali)
  const g1 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "uretimde" });
  if (g1.kod !== 400 || g1.govde.hata !== "gecersiz-gecis") {
    hatalar.push("havale-bekliyor->uretimde: " + g1.kod + "/" + g1.govde.hata + " (400 olmali)");
  }
  // izinli zincir: havale-bekliyor -> odendi -> uretimde
  const g2 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "odendi" });
  const g3 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "uretimde" });
  if (g2.kod !== 200 || g3.kod !== 200) {
    hatalar.push("izinli zincir: odendi=" + g2.kod + " uretimde=" + g3.kod);
  }
  // 'kargolandi' /durum'dan REDDEDILIR (takip kodsuz kargolandi olusmasin)
  const g4 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "kargolandi" });
  if (g4.kod !== 400 || g4.govde.hata !== "kargo-ucunu-kullan") {
    hatalar.push("/durum'dan kargolandi: " + g4.kod + "/" + g4.govde.hata);
  }
  // bilinmeyen durum + bilinmeyen siparis
  const g5 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "ucuyor" });
  if (g5.kod !== 400 || g5.govde.hata !== "bilinmeyen-durum") {
    hatalar.push("bilinmeyen durum: " + g5.kod + "/" + g5.govde.hata);
  }
  const g6 = await yonetIstek("POST", "/durum", { siparis_no: "PR-000000-000000-YOK", durum: "iptal" });
  if (g6.kod !== 404) { hatalar.push("bilinmeyen siparis: " + g6.kod + " (404 olmali)"); }
  // geriye gecis izinsiz: uretimde -> odendi
  const g7 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "odendi" });
  if (g7.kod !== 400) { hatalar.push("uretimde->odendi: " + g7.kod + " (400 olmali)"); }
  // D1 dogrulama + durum_gecmisi izi
  const s = d1Sorgu("SELECT durum, durum_gecmisi FROM siparisler WHERE siparis_no = '" + no + "'")[0] || {};
  let gecmis = [];
  try { gecmis = JSON.parse(s.durum_gecmisi || "[]"); } catch (e) { gecmis = []; }
  if (s.durum !== "uretimde" || gecmis.length !== 2 ||
      gecmis[0].d !== "odendi" || gecmis[1].d !== "uretimde" || !gecmis[1].z) {
    hatalar.push("D1/gecmis: " + JSON.stringify(s).slice(0, 160));
  }
  // her durum -> iptal (ikinci taze siparis uzerinde: bekliyor -> iptal)
  const c2 = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const no2 = (c2.govde || {}).no;
  const g8 = await yonetIstek("POST", "/durum", { siparis_no: no2, durum: "iptal" });
  const s2 = d1Sorgu("SELECT durum FROM siparisler WHERE siparis_no = '" + no2 + "'")[0] || {};
  if (g8.kod !== 200 || s2.durum !== "iptal") {
    hatalar.push("bekliyor->iptal: " + g8.kod + "/" + s2.durum);
  }
  // iptal -> iptal reddedilir
  const g9 = await yonetIstek("POST", "/durum", { siparis_no: no2, durum: "iptal" });
  if (g9.kod !== 400) { hatalar.push("iptal->iptal: " + g9.kod + " (400 olmali)"); }
  rapor("19 durum makinesi", hatalar.length === 0,
    "izinli zincir havale-bekliyor->odendi->uretimde OK; kargolandi /durum'dan RED; " +
    "izinsiz/bilinmeyen RED; gecmis=" + JSON.stringify(gecmis) +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
  return no; // test 20 bu 'uretimde' siparisi kargolar
}

/** 20 — KARGO UCU (kabul 3): D1'de kargo_kodu/kargo_firma + durum 'kargolandi' + MOCK
 *  Resend'e e-posta (kime=musteri, govdede takip kodu). */
async function test20Kargo(no) {
  const hatalar = [];
  if (!no) { return rapor("20 kargo ucu", false, "test 19 siparis veremedi"); }
  const onceE = (await mockOku()).epostaSayisi;
  // eksik alanlar reddedilir
  const k1 = await yonetIstek("POST", "/kargo", { siparis_no: no, kargo_firma: "", kargo_kodu: "X" });
  if (k1.kod !== 400) { hatalar.push("bos firma: " + k1.kod); }
  // gecerli kargo
  const k2 = await yonetIstek("POST", "/kargo",
    { siparis_no: no, kargo_firma: "Yurtiçi Kargo", kargo_kodu: "YK123456789TR" });
  if (k2.kod !== 200) { hatalar.push("kargo ucu: " + k2.kod + " " + JSON.stringify(k2.govde)); }
  const s = d1Sorgu("SELECT durum, kargo_firma, kargo_kodu FROM siparisler " +
    "WHERE siparis_no = '" + no + "'")[0] || {};
  if (s.durum !== "kargolandi" || s.kargo_firma !== "Yurtiçi Kargo" ||
      s.kargo_kodu !== "YK123456789TR") {
    hatalar.push("D1: " + JSON.stringify(s));
  }
  await bekle(400); // e-posta ctx.waitUntil ile
  const m = await mockOku();
  const yeni = (m.epostalar || []).slice(onceE);
  const musteriE = yeni.find((e) => (e.to || []).includes(MUSTERI.eposta));
  if (!musteriE) { hatalar.push("musteri kargo e-postasi gitmedi (delta=" + yeni.length + ")"); }
  else {
    if (!(musteriE.html || "").includes("YK123456789TR")) { hatalar.push("e-postada takip kodu yok"); }
    if (!(musteriE.html || "").includes("Yurtiçi Kargo")) { hatalar.push("e-postada firma yok"); }
    if (!(musteriE.subject || "").includes(no)) { hatalar.push("e-posta konusunda siparis no yok"); }
    if ((musteriE.auth || "") !== "Bearer " + TEST_RESEND_KEY) { hatalar.push("Resend yetkisi yanlis"); }
  }
  // kargolandi -> tamamlandi (zincirin sonu)
  const g = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "tamamlandi" });
  if (g.kod !== 200) { hatalar.push("kargolandi->tamamlandi: " + g.kod); }
  // tamamlandi -> odendi izinsiz (spec ornegi)
  const g2 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "odendi" });
  if (g2.kod !== 400) { hatalar.push("tamamlandi->odendi: " + g2.kod + " (400 olmali)"); }
  rapor("20 kargo ucu", hatalar.length === 0,
    "D1 " + JSON.stringify(s) + "; musteri e-postasi takip koduyla gitti; " +
    "tamamlandi zinciri OK; tamamlandi->odendi RED" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 21 — E-POSTA TETIGI (kabul 4): mock callback 'odendi' akisinda 2 e-posta
 *  (musteri + BILDIRIM_EPOSTA); havale baslatmada da 2; icerik dokum + adres tasir;
 *  idempotens: ayni token 2. kez -> e-posta TEKRARLANMAZ. */
async function test21EpostaTetigi() {
  const hatalar = [];
  // (a) kart akisi: baslat -> callback -> 'odendi' -> 2 e-posta
  const onceE = (await mockOku()).epostaSayisi;
  const c = await baslatIstek([{ id: "test-kdv-75", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const no = (c.govde || {}).no;
  const token = (await mockOku()).sonToken;
  await donusIstek(token);
  await bekle(400);
  const m1 = await mockOku();
  const yeniA = (m1.epostalar || []).slice(onceE);
  const musteriE = yeniA.find((e) => (e.to || []).includes(MUSTERI.eposta));
  const saticiE = yeniA.find((e) => (e.to || []).includes(TEST_BILDIRIM));
  if (yeniA.length !== 2 || !musteriE || !saticiE) {
    hatalar.push("odendi akisi e-posta: " + yeniA.length + " (2 olmali; musteri=" +
      !!musteriE + " satici=" + !!saticiE + ")");
  }
  if (musteriE) {
    const h = musteriE.html || "";
    // dokum: 75 PLA = 75,00 + kargo 250,00 = 325,00; KDV 54,17; adres; siparis no; WhatsApp
    for (const bekleP of [no, "75,00 TL", "250,00 TL", "325,00 TL", "54,17 TL",
                          MUSTERI.adres, "wa.me/905451386526"]) {
      if (!h.includes(bekleP)) { hatalar.push("onay e-postasinda eksik: " + bekleP); }
    }
    if (/3D\s*bask/i.test(h)) { hatalar.push("e-postada '3D baski' gecti (yasak ifade)"); }
    if ((musteriE.from || "") !== "PRUVO <siparis@pruvo3d.com>") {
      hatalar.push("gonderen: " + musteriE.from);
    }
  }
  // idempotens: ayni token 2. kez -> yeni e-posta YOK
  await donusIstek(token);
  await bekle(400);
  const m2 = await mockOku();
  if (m2.epostaSayisi !== m1.epostaSayisi) {
    hatalar.push("tekrar callback'te e-posta tekrarlandi (" + m1.epostaSayisi + "->" +
      m2.epostaSayisi + ")");
  }
  // (b) havale baslatmada da onay e-postasi (2 adet, 'havale' tonu)
  const onceH = m2.epostaSayisi;
  await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    { odeme: "havale" });
  await bekle(400);
  const m3 = await mockOku();
  const yeniH = (m3.epostalar || []).slice(onceH);
  const havaleE = yeniH.find((e) => (e.to || []).includes(MUSTERI.eposta));
  if (yeniH.length !== 2 || !havaleE) {
    hatalar.push("havale akisi e-posta: " + yeniH.length + " (2 olmali)");
  }
  if (havaleE && !/[Hh]avale/.test(havaleE.html || "")) {
    hatalar.push("havale e-postasinda havale notu yok");
  }
  if (havaleE && /Ödemeniz alındı/.test(havaleE.html || "")) {
    hatalar.push("havale e-postasi 'odeme alindi' tonunda (para henuz gorulmedi)");
  }
  rapor("21 e-posta tetigi", hatalar.length === 0,
    "odendi: musteri+" + TEST_BILDIRIM + " 2 e-posta (dokum+adres+no); tekrar callback'te " +
    "tekrarlanmadi; havale: 2 e-posta, dogru ton" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 22 — STL INDIRME, COK-PARCA (kabul 7 + mimar duzeltme turu): normal urunde parca
 *  listesi ucu (stl-liste) + tek tek parca indirme (id+dosya; listede olmayan/traversal
 *  404); dosyasiz urunde acik "yok" notu; sari satirda derleyici ciktisi DEGISMEDI;
 *  anahtarsiz -> 404; zip YOK. */
async function test22Stl() {
  const hatalar = [];
  // Fixture siparisi: tek parcali (a) + iki parcali (b) + dosyasiz (100) + sari (oring)
  const KONF = require(path.join(KOK, "jenerator", "konfigurator.js"));
  const sema = JSON.parse(fs.readFileSync(
    path.join(KOK, "jenerator", "urunler", "olcuye-ozel-oring-conta.json"), "utf8"));
  const c = await baslatIstek([
    { id: "test-urun-a", malzeme: "PLA", renk: "Siyah", adet: 1 },
    { id: "test-urun-b", malzeme: "PLA", renk: "Siyah", adet: 1 },
    { id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 },
    { id: "olcuye-ozel-oring-conta", malzeme: "PLA", renk: "Siyah", adet: 1,
      parametreler: KONF.varsayilanDegerler(sema) },
  ]);
  const no = (c.govde || {}).no;
  if (!no) { return rapor("22 stl indirme (cok-parca)", false, "baslat: " + c.kod + " " + JSON.stringify(c.govde)); }

  // anahtarsiz -> 404 (iki uc da)
  const s0a = await yonetIstek("GET", "/stl-liste?id=test-urun-b", null, null);
  const s0b = await yonetIstek("GET", "/stl?id=test-urun-b&dosya=govde.stl", null, null);
  if (s0a.kod !== 404 || s0b.kod !== 404) {
    hatalar.push("anahtarsiz stl-liste/stl: " + s0a.kod + "/" + s0b.kod);
  }
  // (a) parca listesi: b -> 2 parca (adlar+boyut), a -> 1 parca, 100 -> bos + "yok" notu
  const l1 = await yonetIstek("GET", "/stl-liste?id=test-urun-b");
  const adlar = ((l1.govde || {}).parcalar || []).map((p) => p.dosya).sort();
  if (l1.kod !== 200 || adlar.join(",") !== "govde.stl,kapak.stl") {
    hatalar.push("b parca listesi: " + l1.kod + " " + JSON.stringify(l1.govde).slice(0, 120));
  }
  if (((l1.govde || {}).parcalar || []).some((p) => !(p.boyut > 0))) {
    hatalar.push("parca boyutlari yok: " + JSON.stringify(l1.govde));
  }
  const l2 = await yonetIstek("GET", "/stl-liste?id=test-urun-a");
  if (l2.kod !== 200 || ((l2.govde || {}).parcalar || []).length !== 1) {
    hatalar.push("a parca listesi: " + JSON.stringify(l2.govde).slice(0, 120));
  }
  const l3 = await yonetIstek("GET", "/stl-liste?id=test-urun-100");
  if (l3.kod !== 200 || ((l3.govde || {}).parcalar || []).length !== 0 ||
      !(l3.govde.not || "").includes("test-urun-100")) {
    hatalar.push("dosyasiz urun listesi/notu: " + JSON.stringify(l3.govde).slice(0, 160));
  }
  // (b) tek parca indirme + Content-Disposition (siparis_no verilirse one eklenir)
  const s1 = await yonetIstek("GET", "/stl?id=test-urun-b&dosya=kapak.stl&siparis_no=" + no);
  const cd1 = ((s1.bas || {})["content-disposition"]) || "";
  if (s1.kod !== 200 || s1.metin !== "R2TESTSTL b kapak parcasi") {
    hatalar.push("parca indirme: " + s1.kod + " icerik=" + JSON.stringify(s1.metin.slice(0, 40)));
  }
  if (!cd1.includes(no + "-kapak.stl")) { hatalar.push("Content-Disposition: " + cd1); }
  const s1b = await yonetIstek("GET", "/stl?id=test-urun-a&dosya=test-urun-a.stl");
  const cd1b = ((s1b.bas || {})["content-disposition"]) || "";
  if (s1b.kod !== 200 || !cd1b.includes("test-urun-a.stl")) {
    hatalar.push("tek parcali indirme: " + s1b.kod + " " + cd1b);
  }
  // (c) dosya adi dogrulamasi: listede olmayan ad + path traversal -> 404 (govde sizmaz)
  const k1 = await yonetIstek("GET", "/stl?id=test-urun-b&dosya=olmayan.stl");
  const k2 = await yonetIstek("GET", "/stl?id=test-urun-b&dosya=..%2Ftest-urun-a%2Ftest-urun-a.stl");
  const k3 = await yonetIstek("GET", "/stl?id=test-urun-b&dosya=" +
    encodeURIComponent("../../urunler/x.jpg"));
  if (k1.kod !== 404 || k2.kod !== 404 || k3.kod !== 404) {
    hatalar.push("dogrulama: olmayan=" + k1.kod + " traversal=" + k2.kod + "/" + k3.kod +
      " (hepsi 404 olmali)");
  }
  if ((k2.metin || "").includes("R2TESTSTL")) { hatalar.push("traversal icerik SIZDI"); }
  // (d) sari satir DEGISMEDI: kalem yolu derleyici ciktisi + IC anahtari
  const onceIc = (await mockOku()).icDerleSayisi;
  const s3 = await yonetIstek("GET", "/stl?siparis_no=" + no + "&kalem=3");
  const cd3 = ((s3.bas || {})["content-disposition"]) || "";
  const mIc = await mockOku();
  if (s3.kod !== 200 || !s3.metin.includes("MOCKSTL-olcuye-ozel-oring-conta")) {
    hatalar.push("sari stl: " + s3.kod + " icerik=" + JSON.stringify(s3.metin.slice(84, 130)));
  }
  if (!cd3.includes(no + "-olcuye-ozel-oring-conta.stl")) { hatalar.push("sari Content-Disposition: " + cd3); }
  if (mIc.icDerleSayisi !== onceIc + 1 || (mIc.sonIcDerle || {}).anahtar !== TEST_IC) {
    hatalar.push("ic-derle cagrisi/anahtari: " + JSON.stringify(mIc.sonIcDerle));
  }
  // (e) normal kaleme kalem-yolu artik parca listesine yonlendirir (400), bilinmeyen kalem 404
  const s4 = await yonetIstek("GET", "/stl?siparis_no=" + no + "&kalem=0");
  if (s4.kod !== 400 || s4.govde.hata !== "parca-listesi-kullan") {
    hatalar.push("normal kaleme kalem-yolu: " + s4.kod + "/" + (s4.govde || {}).hata +
      " (400/parca-listesi-kullan olmali)");
  }
  const s5 = await yonetIstek("GET", "/stl?siparis_no=" + no + "&kalem=9");
  if (s5.kod !== 404) { hatalar.push("bilinmeyen kalem: " + s5.kod); }
  rapor("22 stl indirme (cok-parca)", hatalar.length === 0,
    "liste b=" + adlar.join("+") + ", a=1 parca, dosyasiz=bos+not; indirme CD=" + cd1 +
    "; olmayan/traversal=404; sari=derleyici (" + cd3 + ", IC anahtarli); anahtarsiz=404" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 24 — URUN KODU + LINK (mimar mikro paketi, kalem basligi urun sayfasina tiklanabilir
 *  link + "Urun kodu" satiri). ONCE-KIRMIZI: eski satirHtml urun_url/"Urun kodu" uretmiyordu
 *  -> asagidaki kontroller kod degismeden kirmizi yanar (kanit: RAPOR-MIMARA.md).
 *  (a) /liste JSON'da kalemde urun_url = SITE_URL + /urun/<id>/ ;
 *  (b) sayfadan (deploy edilecek GERCEK kaynak, kopya DEGIL) esc()+satirHtml() cekilip
 *      vm'de calistirilir: normal kalemde href+target=_blank+rel=noopener+"Urun kodu: <id>"
 *      var; sahte id/baslik'a <script>/<img> soksan HAM sizmiyor (esc() kaciyor). */
async function test24UrunKoduLinki() {
  const hatalar = [];
  const c = await baslatIstek([{ id: "test-urun-a", malzeme: "PLA", renk: "Siyah", adet: 1 }]);
  const no = (c.govde || {}).no;
  if (!no) { return rapor("24 urun kodu linki", false, "baslat: " + c.kod + " " + JSON.stringify(c.govde)); }

  // (a) /liste JSON: urun_url dogru mu (test kurulumunda SITE_URL "https://pruvo3d.com")
  const l = await yonetIstek("GET", "/liste");
  const siparis = (l.govde.siparisler || []).find((s) => s.siparis_no === no);
  const kalem = siparis && siparis.kalemler && siparis.kalemler[0];
  const beklenenUrl = "https://pruvo3d.com/urun/test-urun-a/";
  if (!kalem || kalem.urun_url !== beklenenUrl) {
    hatalar.push("/liste urun_url: " + JSON.stringify(kalem && kalem.urun_url) +
      " (beklenen " + beklenenUrl + ")");
  }

  // (b) sayfadaki GERCEK esc()/satirHtml() kaynagini cek (kopya yazmiyoruz — deploy
  //     edilen kod sinanir), vm'de calistir.
  const sayfa = await istekHam("GET", WORKER_UC + "/yonet?anahtar=" + TEST_YONET);
  const dilimAl = (baslangic, bitis) => {
    const b = sayfa.metin.indexOf(baslangic);
    const s = b >= 0 ? sayfa.metin.indexOf(bitis, b) : -1;
    return (b >= 0 && s > b) ? sayfa.metin.slice(b, s) : null;
  };
  const escKaynak = dilimAl("function esc(s){", "function tl(k){");
  const satirKaynak = dilimAl("function satirHtml(no,k){", "function boyutMetni(b){");
  if (!escKaynak || !satirKaynak) {
    hatalar.push("sayfa kaynaginda esc/satirHtml bulunamadi (sayfa yapisi degisti mi?)");
  } else {
    const baglam = {};
    vm.createContext(baglam);
    vm.runInContext(escKaynak + "\n" + satirKaynak, baglam, { filename: "yonet-sayfa.js" });
    if (typeof baglam.satirHtml !== "function") {
      hatalar.push("satirHtml vm'de tanimlanamadi");
    } else {
      const normal = baglam.satirHtml("PR-TEST-1", {
        kalem: 0, id: "test-urun-a", baslik: "Test Ürün A", malzeme: "PLA", renk: "Siyah",
        adet: 1, parametrik: false, parametre_detay: "", baski_oneri: "Genel öneri",
        urun_url: beklenenUrl,
      });
      if (!/<a href="https:\/\/pruvo3d\.com\/urun\/test-urun-a\/" target="_blank" rel="noopener">Test Ürün A<\/a>/
          .test(normal)) {
        hatalar.push("normal kalem: href/target=_blank/rel=noopener eksik -> " + normal.slice(0, 220));
      }
      if (!/Ürün kodu: test-urun-a/.test(normal)) {
        hatalar.push("normal kalem: 'Ürün kodu' satiri yok -> " + normal.slice(0, 220));
      }
      // Sahte (zararli) id/baslik: esc() kacirmazsa HAM <script>/<img ...> HTML'e sizar.
      const zararli = baglam.satirHtml("PR-TEST-2", {
        kalem: 1, id: "<script>alert(1)</script>", baslik: "<img src=x onerror=alert(2)>",
        malzeme: "PLA", renk: "Siyah", adet: 1, parametrik: false, parametre_detay: "",
        baski_oneri: "x", urun_url: "https://pruvo3d.com/urun/<script>alert(1)</script>/",
      });
      if (/<script>|<img /i.test(zararli)) {
        hatalar.push("KACIS YOK — HAM HTML SIZDI: " + zararli.slice(0, 220));
      }
      if (!/&lt;script&gt;/.test(zararli)) {
        hatalar.push("sahte id/baslik kacislanmadi (esc() calismiyor olabilir)");
      }
    }
  }
  rapor("24 urun kodu linki", hatalar.length === 0,
    "/liste urun_url=" + beklenenUrl + "; gercek satirHtml -> normal kalemde " +
    "href+target=_blank+rel=noopener+'Ürün kodu:' var; sahte id/baslik kacislaniyor" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

/** 23 — ANAHTARSIZ KURULUM (kabul 4b + 1b): worker YONET_ANAHTAR'siz + RESEND_API_KEY'siz
 *  yeniden baslar -> dogru anahtar bile 404 (ozellik kapali); havale siparisi YINE olusur
 *  + Telegram'a "e-posta gonderilemedi (anahtar yok)" duser (SESSIZ ATLAMA YOK). */
async function test24EpostaLinkResim() {
  const hatalar = [];
  const RURL = "https://media.pruvo3d.com/urunler/test-resim-var-1.jpg";
  const onceE = (await mockOku()).epostaSayisi;
  // Sepet: resimli + resimsiz + enjekte-baslikli (hepsi kart akisi)
  const c = await baslatIstek([
    { id: "test-resim-var", malzeme: "PLA", renk: "Siyah", adet: 1 },
    { id: "test-resim-yok", malzeme: "PLA", renk: "Siyah", adet: 1 },
    { id: "test-eposta-xss", malzeme: "PLA", renk: "Siyah", adet: 1 },
  ]);
  const no = (c.govde || {}).no;
  if (c.kod !== 200 || !no) {
    return rapor("24 e-posta link+resim", false, "baslat: " + c.kod + " " + JSON.stringify(c.govde));
  }
  // (index.js CARRY) D1 siparis urunler JSON'unda gorsel tasindi mi? (resimli=URL, resimsiz=bos)
  const row = d1Sorgu("SELECT urunler FROM siparisler WHERE siparis_no = '" + no + "'")[0] || {};
  let db = [];
  try { db = JSON.parse(row.urunler) || []; } catch (e) { /* bos */ }
  const rv = db.find((s) => s.id === "test-resim-var") || {};
  const ry = db.find((s) => s.id === "test-resim-yok") || {};
  if (rv.gorsel !== RURL) { hatalar.push("D1 urunler JSON gorsel tasinmadi: " + JSON.stringify(rv.gorsel)); }
  if (ry.gorsel !== "") { hatalar.push("resimsiz kalemde gorsel bos degil: " + JSON.stringify(ry.gorsel)); }

  // Odeme -> onay e-postasi (musteri + satici kopyasi AYNI sablon)
  const token = (await mockOku()).sonToken;
  await donusIstek(token);
  await bekle(400);
  const m1 = await mockOku();
  const yeni = (m1.epostalar || []).slice(onceE);
  const musteriE = yeni.find((e) => (e.to || []).includes(MUSTERI.eposta));
  const saticiE = yeni.find((e) => (e.to || []).includes(TEST_BILDIRIM));
  if (!musteriE || !saticiE) {
    hatalar.push("onay e-postasi eksik (musteri=" + !!musteriE + " satici=" + !!saticiE + ")");
  }
  for (const [ad, e] of [["musteri", musteriE], ["satici", saticiE]]) {
    if (!e) { continue; }
    const h = e.html || "";
    if (!h.includes("href='https://pruvo3d.com/urun/test-resim-var/'")) { hatalar.push(ad + ": resimli link yok"); }
    if (!h.includes("href='https://pruvo3d.com/urun/test-resim-yok/'")) { hatalar.push(ad + ": resimsiz link yok"); }
    if (!h.includes("<img src='" + RURL + "'")) { hatalar.push(ad + ": resimli kalemde img yok"); }
    // resimsiz + xss kaleminde gorsel yok -> TAM 1 img (yalniz resimli)
    const imgN = (h.match(/<img /g) || []).length;
    if (imgN !== 1) { hatalar.push(ad + ": img sayisi " + imgN + " (1 olmali; resimsiz kalemde img basmamali)"); }
    if (h.includes("<script>")) { hatalar.push(ad + ": ham <script> sizdi (XSS)"); }
    if (!h.includes("&lt;script&gt;")) { hatalar.push(ad + ": kacisli &lt;script&gt; yok"); }
  }

  // Kargo e-postasi da link+resim tasir (odendi -> uretimde -> kargolandi)
  const g1 = await yonetIstek("POST", "/durum", { siparis_no: no, durum: "uretimde" });
  if (g1.kod !== 200) { hatalar.push("odendi->uretimde: " + g1.kod + " " + JSON.stringify(g1.govde)); }
  const onceK = (await mockOku()).epostaSayisi;
  const g2 = await yonetIstek("POST", "/kargo",
    { siparis_no: no, kargo_firma: "Aras Kargo", kargo_kodu: "AR24LINKTR" });
  if (g2.kod !== 200) { hatalar.push("kargo ucu: " + g2.kod + " " + JSON.stringify(g2.govde)); }
  await bekle(400);
  const kargoE = ((await mockOku()).epostalar || []).slice(onceK)
    .find((e) => (e.to || []).includes(MUSTERI.eposta));
  if (!kargoE) { hatalar.push("kargo e-postasi gitmedi"); }
  else {
    const h = kargoE.html || "";
    if (!h.includes("href='https://pruvo3d.com/urun/test-resim-var/'")) { hatalar.push("kargo: resimli link yok"); }
    if (!h.includes("<img src='" + RURL + "'")) { hatalar.push("kargo: img yok"); }
    if (!h.includes("AR24LINKTR")) { hatalar.push("kargo: takip kodu yok"); }
  }
  rapor("24 e-posta link+resim", hatalar.length === 0,
    "D1 gorsel tasindi (resimli=URL, resimsiz=bos); onay musteri+satici link+img (resimsiz kalem img YOK); " +
    "enjekte baslik kacisli; kargo e-postasi link+img" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
}

async function test23AnahtarsizKurulum() {
  const hatalar = [];
  workerDurdur();
  await bekle(1500);
  await workerBaslat({
    IYZICO_BASE_URL: "http://127.0.0.1:" + MOCK_PORT,
    IYZICO_API_KEY: TEST_API_KEY,
    IYZICO_SECRET_KEY: TEST_SECRET,
    TELEGRAM_API: "http://127.0.0.1:" + MOCK_PORT,
    TELEGRAM_TOKEN: "0000:test",
    SITE_URL: "https://pruvo3d.com",
    HAVALE_IBAN: TEST_IBAN,
    HAVALE_UNVAN: TEST_UNVAN,
    BILDIRIM_EPOSTA: TEST_BILDIRIM,
    // BILEREK YOK: YONET_ANAHTAR (yonetim kapali) + RESEND_API_KEY/RESEND_URL (e-posta yok)
  });
  // (a) yonetim: dogru anahtar bile 404 (secret tanimsiz -> ozellik kapali, varlik sizmasin)
  const y = await yonetIstek("GET", "/liste");
  if (y.kod !== 404) { hatalar.push("secret'siz yonetim: " + y.kod + " (404 olmali)"); }
  // (b) e-posta anahtari yokken siparis akisi BOZULMAZ + Telegram uyarisi
  const onceTg = (await mockOku()).telegramSayisi;
  const onceE = (await mockOku()).epostaSayisi;
  const c = await baslatIstek([{ id: "test-urun-100", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    { odeme: "havale" });
  const no = (c.govde || {}).no;
  const s = no ? d1Sorgu("SELECT durum FROM siparisler WHERE siparis_no = '" + no + "'")[0] : null;
  if (c.kod !== 200 || !s || s.durum !== "havale-bekliyor") {
    hatalar.push("anahtar yokken siparis akisi bozuldu: " + c.kod + " " + JSON.stringify(s));
  }
  await bekle(500);
  const m = await mockOku();
  const tgDelta = m.telegramSayisi - onceTg;
  // havale bildirimi (1) + e-posta uyarisi (1) = 2 telegram; sira deterministik DEGIL
  // (ikisi de ctx.waitUntil) -> yeni mesajlarin HERHANGI birinde uyari aranir.
  const yeniTg = (m.telegramlar || []).slice(onceTg).map((t) => String(t.text || ""));
  const uyariVar = tgDelta >= 2 &&
    yeniTg.some((t) => t.includes("e-posta gönderilemedi (anahtar yok)"));
  if (!uyariVar) {
    hatalar.push("Telegram e-posta uyarisi yok (delta=" + tgDelta + ", yeni=" +
      yeniTg.map((t) => t.slice(0, 40)).join(" || ") + ")");
  }
  if (m.epostaSayisi !== onceE) { hatalar.push("anahtar yokken Resend'e istek gitti"); }
  rapor("23 anahtarsiz kurulum", hatalar.length === 0,
    "YONET_ANAHTAR'siz yonetim=404; RESEND_API_KEY'siz havale siparisi olustu (" +
    (s || {}).durum + ") + Telegram 'anahtar yok' uyarisi; Resend'e istek gitmedi" +
    (hatalar.length ? " | HATA: " + hatalar.join(" ; ") : ""));
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
    // Siparis yonetimi paketi (kabul 5): yeni secret adlari repoya DEGER olarak yazilmasin.
    // Test dosyasindaki "test-..." on ekli sahte degerler asagida muaf tutulur.
    ["(YONET_ANAHTAR|RESEND_API_KEY|IC_DERLE_ANAHTAR)[\"' ]*[:=][\"' ]*[A-Za-z0-9+/=-]{10,}",
     "yonetim/e-posta anahtari"],
  ];
  const bulunan = [];
  for (const [desen, ad] of desenler) {
    // -I: ikili dosyalari atla, --untracked: ignore'lanmamis yeni dosyalar da dahil.
    const g = spawnSync("git", ["-C", KOK, "grep", "-nIE", "--untracked", desen],
      { encoding: "utf8" });
    // exit 0 = eslesme VAR (sizinti), 1 = yok (temiz), >1 = git hatasi
    if (g.status === 0) {
      for (const satir of g.stdout.split("\n").filter(Boolean)) {
        // Sablon dosyasindaki "sandbox-XXXX" gibi degersiz ornekler sizinti degil;
        // kabul testinin kendi sahte anahtarlari (test-... on eki) de degil.
        if (/\.dev\.vars\.example/.test(satir) || /sandbox-X+/.test(satir)) { continue; }
        if (/(YONET_ANAHTAR|RESEND_API_KEY|IC_DERLE_ANAHTAR)["' ]*[:=]["' ]*test-/.test(satir)) { continue; }
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
    ? "repo geneli " + dosyalar.length + " dosya tarandi (" + desenler.length +
      " desen), sizinti yok; .dev.vars " +
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
  // 1.105,00 < 2.500 -> kargo 250,00; iyzico sayfasinda gorunecek tahsilat = urun + kargo.
  const bekKargo = SECENEK.kargoKurus ? SECENEK.kargoKurus(bek) : 0;
  console.log("Siparis no:", c.govde.no, "— beklenen tutar: " + kurusMetin(bek) +
    " TL (850 x PETG, secenekler.js) + kargo " + kurusMetin(bekKargo) +
    " TL = tahsilat " + kurusMetin(bek + bekKargo) + " TL");
  console.log("1) Su sayfayi acip iyzico TEST kartiyla ode (docs.iyzico.com/ek-bilgiler/test-kartlari):");
  console.log("   " + c.govde.url);
  console.log("2) Odeme sonrasi iyzico seni bu makinedeki callback'e yonlendirir;");
  console.log("   script D1'de 'odendi' satirini gorunce kaniti basar. Bekliyor (en cok 10 dk)...");
  for (let i = 0; i < 300; i++) {
    await bekle(2000);
    const s = d1Sorgu("SELECT siparis_no, durum, tutar_kurus, kargo_kurus, iyzico_odeme_id " +
      "FROM siparisler WHERE siparis_no = '" + c.govde.no + "'")[0];
    if (s && s.durum === "odendi") {
      // 'odendi' gormek YETMEZ: tahsil edilen tutar sunucu hesabiyla birebir mi, odeme id
      // gercekten geldi mi, bildirim atildi mi — hepsi kanit olmali.
      const m = await mockOku();
      const sorunlar = [];
      if (s.tutar_kurus !== bek) {
        sorunlar.push("D1 tutar " + s.tutar_kurus + " != beklenen " + bek);
      }
      if (s.kargo_kurus !== bekKargo) {
        sorunlar.push("D1 kargo " + s.kargo_kurus + " != beklenen " + bekKargo);
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
  r2Kur();   // yerel R2 fixture'i (test 22 — yonetim /stl)
  const mock = await mockBaslat();
  await workerBaslat({
    IYZICO_BASE_URL: "http://127.0.0.1:" + MOCK_PORT,
    IYZICO_API_KEY: TEST_API_KEY,
    IYZICO_SECRET_KEY: TEST_SECRET,
    TELEGRAM_API: "http://127.0.0.1:" + MOCK_PORT,
    TELEGRAM_TOKEN: "0000:test",
    SITE_URL: "https://pruvo3d.com",
    // Havale/EFT (test 13): canlida wrangler secret'tan gelir, testte sahte deger.
    HAVALE_IBAN: TEST_IBAN,
    HAVALE_UNVAN: TEST_UNVAN,
    // Siparis yonetimi paketi: yonetim anahtari + Resend mock + ic-derle mock.
    YONET_ANAHTAR: TEST_YONET,
    RESEND_URL: "http://127.0.0.1:" + MOCK_PORT,
    RESEND_API_KEY: TEST_RESEND_KEY,
    BILDIRIM_EPOSTA: TEST_BILDIRIM,
    ONIZLEME_TABAN: "http://127.0.0.1:" + MOCK_PORT,
    IC_DERLE_ANAHTAR: TEST_IC,
  });

  try {
    const siparisNo = await test1FiyatButunlugu();
    await test2SahteCallback();
    let token = null;
    if (siparisNo) { token = await test4mUctanUcaMock(siparisNo); }
    else { rapor("4m uctan uca (mock iyzico)", false, "test 1 basarisiz oldugu icin kosulamadi"); }
    if (token) { await test3Idempotens(siparisNo, token); }
    else { rapor("3 idempotens", false, "token alinamadi"); }
    // 8/10, mock'un sonInit/sonToken durumunu tazeledigi icin 1/4m/3'ten SONRA kosar.
    await test8KatsayiDogrulugu();
    await test10Kargo();
    await test11RetrieveHatasi();
    await test12SiparisNo();
    await test13Havale();
    await test14Kdv();
    await test15SozlesmeOnayi();
    await test5Parametrik();
    await test9ParametrikAltyapi();
    await test16CallbackTutarUyusmazligi();
    await test17ParametrikSatirAyirt();
    // Siparis yonetimi paketi (18-23). 23 worker'i ANAHTARSIZ yeniden baslatir —
    // bu yuzden HTTP'ye dokunan diger tum testlerden SONRA kosar.
    await test18YonetimYetkisi();
    const uretimdeNo = await test19DurumMakinesi();
    await test20Kargo(uretimdeNo);
    await test21EpostaTetigi();
    await test22Stl();
    await test24UrunKoduLinki();
    await test24EpostaLinkResim();
    await test23AnahtarsizKurulum();
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
