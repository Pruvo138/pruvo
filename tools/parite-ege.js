#!/usr/bin/env node
/**
 * PARITE TESTI — /ara?mod=ege, Ege'nin BUGUNKU aramasiyla (urunAra) birebir ayni mi?
 *
 *   node tools/parite-ege.js            # ~1100 sorgu
 *   node tools/parite-ege.js 200        # daha az sorgu (hizli)
 *
 * NEDEN VAR: Ege bugun tum katalogu Worker BELLEGINE cekip orada ariyor (katalogHazir +
 * katalogIndeksle). ~20-25k urunde bu 128 MB limitini asar ve BOT KOMPLE DURUR. Cozum
 * aramayi D1'e almak; ama Ege'nin aramasi sitenin aramasi DEGIL (es anlamlilar, Turkce ek
 * kirpma, baslik/govde skoru). Oldugu gibi /ara'ya baglansaydi arama kalitesi DUSERDU.
 * Bu test "yeni yol, eskisiyle ayni sonucu veriyor mu" sorusunu OLCEREK cevaplar.
 *
 * ZAMANLAMA (Okan sordu, 15 Tem — "sonra yapsak kalite yine dusmez mi?"): dusus zamana
 * degil /ara'nin ne yaptigina bagli; ertelemek engellemez. Ama BUGUN yapmanin sebebi su:
 * urunAra hala calisiyor, yani REFERANS var. Bot 128 MB'i asip durduktan sonra referans da
 * olur; kaybedilen kalite OLCULEMEDEN kabul edilmis olurdu.
 *
 * REFERANS = GERCEK KOD, kopya DEGIL: bot'un index.js'i oldugu gibi okunup gecici bir .mjs
 * olarak ice aktarilir (dosyada package.json/"type":"module" yok, o yuzden uzanti hilesi).
 * Elle kopyalasaydik kod degisince test sessizce ESKI davranisi dogrulamaya devam ederdi.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { pathToFileURL } = require("url");

const UC = process.env.ARA_UC || "https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara";
const URUNLER = "/Users/okan/dev/pruvo/urunler.json";
const BOT = "/Users/okan/dev/pruvo-bot/worker/src/index.js";
const LIMIT = 1000;      // /ara azami limiti; ustu sorgularda ilk 1000 + toplam karsilastirilir
const ESZAMAN = 6;

// Bot'un gercek arama kodunu ice aktar (kaynak dosyaya DOKUNMADAN).
async function egeKodu() {
  if (!fs.existsSync(BOT)) {
    console.error("Bot kaynagi yok: " + BOT + "\n(pruvo-bot deposu ~/dev/pruvo-bot'ta olmali.)");
    process.exit(2);
  }
  const kaynak = fs.readFileSync(BOT, "utf8");
  const gecici = path.join(os.tmpdir(), "pruvo-ege-ref-" + process.pid + ".mjs");
  fs.writeFileSync(gecici, kaynak + "\nexport { katalogIndeksle, urunAra, sorguKavramlari, nrm };\n");
  try {
    const M = await import(pathToFileURL(gecici).href);
    for (const ad of ["katalogIndeksle", "urunAra", "sorguKavramlari", "nrm"]) {
      if (typeof M[ad] !== "function") {
        console.error("index.js'te " + ad + "() bulunamadi — yeniden adlandirildi mi? Test durdu.");
        process.exit(2);
      }
    }
    return M;
  } finally {
    fs.unlinkSync(gecici);
  }
}

function sorgulariUret(EGE, PRODUCTS, hedef) {
  const sorgular = [];
  const ekle = (q) => sorgular.push(q);
  const nrm = EGE.nrm;

  const markalar = [...new Set(PRODUCTS.flatMap((p) => p.marka || []))];
  const sayac = new Map();
  for (const p of PRODUCTS) {
    for (const w of nrm(p.baslik || "").split(" ")) {
      if (w.length >= 2) sayac.set(w, (sayac.get(w) || 0) + 1);
    }
  }
  const kelimeler = [...sayac.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0]);

  // 1) Tek kelime (sik -> nadir)
  for (const w of kelimeler.slice(0, 300)) ekle(w);
  // 2) Markalar
  for (const m of markalar.slice(0, 120)) ekle(m);

  // 3) ES ANLAMLI GRUPLAR — Ege'ye ozel, sitede YOK. Her uye tek tek.
  const sinonim = [
    "vw", "volkswagen", "mercedes", "benz", "chevrolet", "chevy",
    "oto", "otomobil", "araba", "arac", "conta", "oring", "sizdirmazlik",
    "pervane", "fan", "cark", "impeller", "braket", "tutucu", "ayak", "mesnet",
    "disli", "gear", "rulman", "bearing", "kayis", "triger",
  ];
  for (const w of sinonim) { ekle(w); ekle(w + " kirildi"); ekle("audi " + w); }

  // 4) TURKCE EK KIRPMA — asil kirilma noktasi (kok esitligi + cift yonlu onek).
  const ekler = ["m", "si", "sı", "i", "ler", "lar", "leri", "lari", "nin", "im", "imiz", "lerimiz", "de", "den", "yle"];
  for (let i = 0; i < 220; i++) {
    const w = kelimeler[i % 90];
    ekle(w + ekler[i % ekler.length]);
  }
  // Onekler (w >= 4 && sorgu w ile basliyor): "perva" ⊂ "pervane"
  for (let i = 0; i < 60; i++) {
    const w = kelimeler[i % 60];
    if (w.length >= 5) ekle(w.slice(0, 4));
    if (w.length >= 6) ekle(w.slice(0, 5));
  }

  // 5) Gercek musteri cumleleri (durak kelimeler + ek + coklu kavram)
  const cumleler = [
    "menteşem kırıldı", "menteşesi kırıldı", "contam aşındı", "conta lazım",
    "pervane fiyatı ne kadar", "vw golf far", "volkswagen golf farı",
    "audi a4 kapı kolu kırıldı", "buzdolabı rafı kırıldı", "o-ring arıyorum",
    "araba için braket", "oto conta", "dişli çarkı lazım", "rulman var mı",
    "merhaba", "ne kadar", "fiyat", "iyi günler", "selam",              // TAMAMI durak -> 0 kavram
    "bana bir adet menteşe lazım", "şu contadan istiyorum",
  ];
  for (const q of cumleler) ekle(q);

  // 6) KENAR DURUMLAR
  const kenar = [
    "menteşe", "MENTEŞE", "Menteşe", "MENTEŞEM",   // Turkce buyuk/kucuk (İ/I tuzagi)
    "ıspanak", "Işık", "İzmir", "IŞIK",
    "çğöşüâî", "ÇĞÖŞÜ",                            // â/î: nrm bunlari BOSLUGA atar (JS de oyle)
    "vw", "a4", "x5", "e46",                       // 2 harfli (yalnizca tam kelime eslesir)
    "a", "b", "1",                                 // tek harf -> kavram olmaz (>=2 sarti)
    "o-ring", "o ring", "o_ring", "o.ring",        // alfanumerik olmayan -> bosluk
    "%", "_", "a%b", "'", "' OR 1=1 --",           // joker / enjeksiyon (bind ile gecmeli)
    "audi   a4", "  bosluk  ",
    "yokboylebirsey12345",
    "menteşe menteşe menteşe",                     // tekrarli token (tek kez skorlanmali)
  ];
  for (const q of kenar) ekle(q);

  for (let i = sorgular.length - 1; i > 0; i--) {
    const j = (i * 2654435761) % (i + 1);
    [sorgular[i], sorgular[j]] = [sorgular[j], sorgular[i]];
  }
  return hedef ? sorgular.slice(0, hedef) : sorgular;
}

// Her calisma icin benzersiz — asagiya bak.
const NONCE = Date.now().toString(36) + "-" + process.pid;

async function araSor(q) {
  const u = new URL(UC);
  u.searchParams.set("q", q);
  u.searchParams.set("mod", "ege");
  u.searchParams.set("limit", String(LIMIT));
  // ONBELLEK KIRICI — SART. /ara yanitlari "cache-control: public, max-age=60" ile doner ve
  // Cloudflare edge'i ISTEK'teki "cache-control: no-cache"i YOK SAYAR. Bu olmadan test
  // Worker'i degil CDN'i olcer: bir kez hatali surum deploy edilirse onun cevabi 60 sn
  // onbellekte kalir, duzeltilmis surumde test HALA kirmizi yanar (ya da tersi — bozuk kod
  // eski dogru cevapla YESIL yanar, asil tehlike bu). Gercekten yasandi (15 Tem):
  // q=kapagisi tek basina 1113 donerken testte 1055 dondu; fark cache anahtariydi (limit=1
  // vs limit=1000). Uc bilinmeyen parametreyi yok sayar, sonuc degismez.
  u.searchParams.set("_nonce", NONCE);
  const r = await fetch(u);
  if (!r.ok && r.status !== 400) throw new Error("HTTP " + r.status);
  return await r.json();
}

async function main() {
  const EGE = await egeKodu();
  const PRODUCTS = JSON.parse(fs.readFileSync(URUNLER, "utf8"));
  const idx = EGE.katalogIndeksle(PRODUCTS);

  const hedef = parseInt(process.argv[2], 10);
  const sorgular = sorgulariUret(EGE, PRODUCTS, Number.isFinite(hedef) ? hedef : 0);
  console.log("Ege parite testi: %d sorgu | %d urun | uc: %s\n", sorgular.length, PRODUCTS.length, UC);

  let gecti = 0, kaldi = 0;
  const hatalar = [];
  let sirada = 0;

  async function isci() {
    while (sirada < sorgular.length) {
      const q = sorgular[sirada++];

      // BEKLENEN = Ege'nin gercek kodu, TUM eslesmeler (sirali).
      const bek = EGE.urunAra(idx, q, Infinity);
      const bekIds = bek.map((u) => u.id);

      let g;
      try { g = await araSor(q); } catch (e) {
        kaldi++; hatalar.push({ q, sebep: "istek hatasi: " + e.message }); continue;
      }

      // Bos sorgu (kavram cikmayan) -> uc 400 dondurebilir; beklenen de bos olmali.
      const alinan = (g.urunler || []).map((u) => u.id);
      const toplam = g.toplam || 0;

      if (toplam !== bekIds.length) {
        kaldi++;
        hatalar.push({ q, sebep: `sayi: /ara=${toplam} ege=${bekIds.length}` });
        continue;
      }
      const bekKirpik = bekIds.slice(0, LIMIT);
      const ilk = alinan.findIndex((id, i) => id !== bekKirpik[i]);
      if (ilk !== -1 || alinan.length !== bekKirpik.length) {
        kaldi++;
        hatalar.push({ q, sebep: ilk !== -1
          ? `sira/icerik ${ilk}. sirada: /ara=${alinan[ilk]} ege=${bekKirpik[ilk]}`
          : `uzunluk: /ara=${alinan.length} ege=${bekKirpik.length}` });
        continue;
      }
      gecti++;
    }
  }

  await Promise.all(Array.from({ length: ESZAMAN }, isci));

  console.log("GECTI: %d | KALDI: %d", gecti, kaldi);
  if (hatalar.length) {
    console.log("\nIlk %d fark:", Math.min(20, hatalar.length));
    for (const h of hatalar.slice(0, 20)) console.log("  q=%j -> %s", h.q, h.sebep);
  }
  process.exit(kaldi ? 1 : 0);
}

main();
