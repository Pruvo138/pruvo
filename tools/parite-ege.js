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
 *
 * 🔴 REFERANS IKI GOVDEDEN OLUSUR (06 Agu 2026) — cunku UC de iki daldan olusur:
 *   SERBEST METIN : bot'un `urunAra`si (asagida, degismedi).
 *   MARKA ADI     : `?q=<marka>` 05 Agu'da `marka_arama` UYELIGINE baglandi. `urunAra` o
 *                   kurali TASIMAZ (bot deposunda 1 tanim / 0 cagri yeri = OLU KOD), yani
 *                   tek basina referans olarak birakilmasi testin KENDISINI bayatlatti:
 *                   38/848 kirmizi, TAMAMI marka sorgusu, yon daima "referans FAZLA sayar".
 *                   Marka dali artik tools/ege-marka-referansi.js'ten gelir; orada da ikinci
 *                   bir yuklem YAZILMAZ, iki uretim govdesi KOSTURULUR (d1-sync.py
 *                   marka_arama_haritasi + ucun kendi markaSorguKanonu'su).
 *                   Kurulamazsa OLCULEMEDI (cikis 3), sessiz yesil DEGIL.
 *
 * ⚠️ CIKIS KODLARI: TEK KAYNAK -> tools/parite-ortak.js dosya basindaki "CIKIS KODU
 *   SOZLESMESI" blogu (burada IKINCI TABLO YAZILMAZ). Ozet: 0 parite · 1 aciklanamayan
 *   ayrisim · 2 test kosulamadi (bot kaynagi/fonksiyonu yok) · 3 OLCULEMEDI.
 *   Yonetici ilke: 1 > 3 > 0; hicbir ariza yolu 0 uretemez.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { pathToFileURL } = require("url");
const ortak = require("./parite-ortak.js");
const markaRef = require("./ege-marka-referansi.js");

const UC = process.env.ARA_UC || "https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara";
// 🔴 KATALOG YOLU = BU CHECKOUT (mutlak yol DEGIL). Eskiden /Users/okan/dev/pruvo/urunler.json
// sabitti; bir worktree'de kosarken parite-test.js checkout'un katalogunu, bu test ANA
// deponun katalogunu okuyordu -> iki test AYNI anda FARKLI katalog olcuyor, biri kirmizi
// biri yesil yaniyordu (olculdu 27 Tem). Artik ikisi de path.dirname(__dirname).
const KOK = path.dirname(__dirname);
const URUNLER = process.env.PARITE_URUNLER || path.join(KOK, "urunler.json");
// Bot AYRI depodur (kardes klasor, bu checkout'un icinde DEGIL) -> mutlak kalir; worktree'den
// kosulurken de ana bot deposu okunur. PARITE_BOT ile gecilebilir (fikstur/kabul testi).
const BOT = process.env.PARITE_BOT || "/Users/okan/dev/pruvo-bot/worker/src/index.js";
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
  // markaSorguKanonu = UCUN KENDI marka yargisi (olu kod DEGIL, canli dalin ta kendisi).
  // Marka referansi onu sahte bir D1 uzerinde CALISTIRIR; norm/aksan/ayirac kanonu ve
  // cakisma davranisi bu govdeden gelir, kopyalanmaz.
  fs.writeFileSync(gecici, kaynak +
    "\nexport { katalogIndeksle, urunAra, sorguKavramlari, nrm, markaSorguKanonu };\n");
  try {
    const M = await import(pathToFileURL(gecici).href);
    for (const ad of ["katalogIndeksle", "urunAra", "sorguKavramlari", "nrm",
      "markaSorguKanonu"]) {
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
const NONCE = ortak.nonceUret();
const SAYAC = ortak.sayacYeni();

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
  // UA: WAF varsayilan urllib UA'sina 403 verir; 403/429 "ayrisma" DEGIL "olculemedi"
  // olarak yukari atilir (ortak.WafHatasi). 400 = kavram cikmayan sorgu -> normal.
  const { durum, govde } = await ortak.canliGetir(u.toString(), SAYAC, ortak.DENEME);
  if (durum >= 500) throw new Error("HTTP " + durum);
  return govde;
}

async function main() {
  // ── MARKA ADI SORGUSU EKSENI — EGE YUZEYI (opsiyonel, VARSAYILAN KAPALI) ─────────
  // Bu test Ege'nin BUGUNKU aramasini (urunAra) referans alir; marka adiyla yapilan
  // sorgunun `marka_arama` kolonuna baglanmasi AYRI bir iddiadir ve burada OLCULMEZ.
  // Marka ekseni o iddiayi olcer (kume paritesi; Ege skorla siraladigi icin SIRA iddiasi
  // YOK) ve uc gecmeden once KIRMIZI yanar — beklenen. Bloklayan seride DEGIL; govde TEK:
  // tools/parite-marka-ekseni.js.  node tools/parite-ege.js --marka-ekseni [--ornek=N]
  // NOT: bot kaynagi (egeKodu) bu yolda GEREKMEZ -> kontrol EN BASTA.
  if (process.argv.includes("--marka-ekseni")) {
    return process.exit(await require("./parite-marka-ekseni.js").calistirCLI({ yuzey: "ege" }));
  }

  const EGE = await egeKodu();
  const PRODUCTS = JSON.parse(fs.readFileSync(URUNLER, "utf8"));
  const idx = EGE.katalogIndeksle(PRODUCTS);
  const YEREL_IDLER = [...new Set(PRODUCTS.map((p) => p.id))];
  const YEREL_ID_KUME = new Set(YEREL_IDLER);

  const hedef = parseInt(process.argv[2], 10);
  const sorgular = sorgulariUret(EGE, PRODUCTS, Number.isFinite(hedef) ? hedef : 0);
  const OLCULEMEDI = [];
  console.log("Ege parite testi: %d sorgu | %d urun (%s) | uc: %s",
    sorgular.length, PRODUCTS.length, URUNLER, UC);
  console.log("ISTEK BUTCESI: sorgu(%d) + on-kosul(1) [+ sayilar ayriysa supurme " +
    "min(ceil(%d/%d), tavan %d) = %d parti] | zaman asimi %d ms/istek, deneme %d\n",
    sorgular.length, YEREL_IDLER.length, ortak.IDS_PARTI, ortak.SUPURME_TAVANI,
    Math.min(Math.ceil(YEREL_IDLER.length / ortak.IDS_PARTI), ortak.SUPURME_TAVANI),
    ortak.ZAMAN_ASIMI_MS, ortak.DENEME);

  // Sessiz baypas olmasin: test-only env verildiyse HEM stdout HEM stderr'e (A15).
  const fikstur = ortak.fiksturNotu();
  if (fikstur) {
    console.log("⚠️ " + fikstur);
    console.error("⚠️ " + fikstur);
    OLCULEMEDI.push(fikstur);
  }

  const t0 = Date.now();

  // ── ON-KOSUL: checkout katalogu CANLI ile ayni mi? (parite-test.js ile AYNI kural) ──
  let onKosul;
  try {
    onKosul = await ortak.onKosulOlc({ uc: UC, yerelIdler: YEREL_IDLER, sayac: SAYAC, nonce: NONCE });
  } catch (e) {
    if (e && e.olcum) {
      OLCULEMEDI.push(ortak.olcumNotu(e, "ege"));
      OLCULEMEDI.push("on-kosul basarisiz -> 0/" + sorgular.length + " sorgu olculdu");
      return process.exit(ortak.sonucYaz({
        etiket: "ege", gecti: 0, atlandi: 0, hatalar: [], onKosul: null,
        sayac: SAYAC, sn: ((Date.now() - t0) / 1000).toFixed(1),
        fazlaKume: null, olculemedi: OLCULEMEDI,
      }));
    }
    throw e;
  }
  for (const n of onKosul.notlar) console.log("  " + n);

  if (onKosul.kirmizi) {
    console.log("\nSONUC: PARITE YOK ❌ — %s", onKosul.kirmizi);
    console.log("   (Bu yon katalog farkiyla ACIKLANAMAZ: site gosterir, Ege GOREMEZ.)");
    console.log("canli istek: %d", SAYAC.istek);
    return process.exit(ortak.CIKIS_KIRMIZI);
  }

  // ── MARKA REFERANSI — on-kosul KIRMIZISINDAN SONRA kurulur ────────────────────
  // 🔴 SIRA HUKUMDUR (1 > 3 > 0): once kurulsaydi, referans kurulamadiginda on-kosulun
  // KIRMIZI hukmu OLCULEMEDI'ye (3) donusur, yani ariza bulunmus kirmiziyi SILERDI.
  // Taslak id kaniti on-kosuldan gelir, o yuzden daha erkene de alinamaz.
  // 🔴 FAIL-CLOSED: kurulamazsa sorgular OLCULMEZ. Eski (serbest metin) referansla devam
  // etmek "bayat referans" kusurunu geri getirir; marka sorgularinda KIRMIZI yakip gercek
  // gerilemeyi gurultuye gomerdi.
  let MARKA;
  try {
    MARKA = await markaRef.markaReferansi({
      EGE, urunler: PRODUCTS, urunlerYolu: URUNLER, taslakKume: onKosul.taslakIdler,
    });
    console.log("  marka referansi: %d marka / %d kalem (kaynak: d1-sync.marka_arama_haritasi" +
      " + ucun markaSorguKanonu'su)", MARKA.evrenBoyu, MARKA.kalem);
  } catch (e) {
    OLCULEMEDI.push(ortak.olcumNotu(e, "ege"));
    OLCULEMEDI.push("marka referansi KURULAMADI -> 0/" + sorgular.length + " sorgu olculdu");
    return process.exit(ortak.sonucYaz({
      etiket: "ege", gecti: 0, atlandi: 0, hatalar: [], onKosul,
      sayac: SAYAC, sn: ((Date.now() - t0) / 1000).toFixed(1),
      fazlaKume: null, olculemedi: OLCULEMEDI,
    }));
  }

  let gecti = 0;
  const hatalar = [];
  const fazlaKume = new Set();
  let sirada = 0;
  let olcumArizasi = null;
  // Pencere ucun ilan ettigi toplami KAPSAMAYAN sorgu sayisi (durustluk kapisi —
  // parite-test.js ile AYNI kural; aciklamasi tools/parite-ortak.js siniflandir()'da).
  let olculemeyenPencere = 0;

  async function isci() {
    while (sirada < sorgular.length && !olcumArizasi) {
      const q = sorgular[sirada++];

      // BEKLENEN = UCUN GECTIGI DALIN yerel karsiligi, TUM eslesmeler (sirali).
      //  · marka adi sorgusu -> `marka_arama` uyeligi, katalog sirasi (uc: seq DESC,
      //    skor SABIT 3 -> sira SAF seq DESC, yani iddia SIRA ekseninde de gecerlidir).
      //  · degilse           -> serbest metin (urunAra), eskisi gibi.
      // Dal secimi UCUN KENDI yargisidir (markaSorguKanonu); burada "marka mi" diye
      // ikinci bir karar YAZILMAZ.
      let bekIds;
      try {
        const markaDeger = await MARKA.kanon(q);
        bekIds = markaDeger
          ? MARKA.kume(markaDeger).slice()
          : EGE.urunAra(idx, q, Infinity).map((u) => u.id);
      } catch (e) {
        olcumArizasi = olcumArizasi || Object.assign(e, { olcum: true });
        return;
      }

      let g;
      try { g = await araSor(q); } catch (e) {
        if (e && e.olcum) { olcumArizasi = olcumArizasi || e; return; }
        hatalar.push({ q, sinif: ortak.SINIF_ACIKLANAMAYAN, sebep: "istek hatasi: " + e.message });
        continue;
      }

      // Bos sorgu (kavram cikmayan) -> uc 400 dondurebilir; beklenen de bos olmali.
      const k = ortak.siniflandir({
        bekIds,
        alinan: (g.urunler || []).map((u) => u.id),
        toplam: g.toplam || 0,
        limit: LIMIT,
        yerelIdKume: YEREL_ID_KUME,
        gecikmeModu: onKosul.gecikmeModu,
        // Kanitlanmis TASLAK id'ler yerel beklentiden DUSULUR (parite-test.js ile AYNI
        // kural; gerekcesi tools/parite-ortak.js siniflandir()'da).
        taslakKume: onKosul.taslakIdler,
      });
      for (const id of k.fazla) fazlaKume.add(id);
      if (!k.kesin) olculemeyenPencere++;
      if (k.sinif === ortak.SINIF_GECTI) { gecti++; continue; }
      hatalar.push({ q, sinif: k.sinif, sebep: k.sebep });
    }
  }

  await Promise.all(Array.from({ length: ESZAMAN }, isci));
  const sn = ((Date.now() - t0) / 1000).toFixed(1);

  // 🔴 KOK SEBEP ONARIMI: ariza cikis VERMEZ, NOT olur; karar sonucYaz'da (1 > 3 > 0).
  if (olcumArizasi) {
    OLCULEMEDI.push(ortak.olcumNotu(olcumArizasi, "ege"));
    OLCULEMEDI.push("kosum ERKEN DURDU: " + (gecti + hatalar.length) + "/" +
      sorgular.length + " sorgu olculdu");
  }

  const t = ortak.fazlalikTeshis(fazlaKume, onKosul.acik);
  if (t.kirmizi) {
    hatalar.push({ q: "(kosum geneli)", sinif: ortak.SINIF_ACIKLANAMAYAN, sebep: t.kirmizi });
  }

  const kod = ortak.sonucYaz({
    etiket: "ege", gecti, atlandi: 0, hatalar, onKosul, sayac: SAYAC, sn, fazlaKume,
    olculemedi: OLCULEMEDI, olculemeyenPencere,
  });
  if (kod === ortak.CIKIS_GECTI) {
    console.log("\nSONUC: BIREBIR PARITE ✅ (%d sorgu, Ege kodu ile ayni)", gecti);
  }
  if (kod === ortak.CIKIS_OLCULEMEDI && fikstur && !hatalar.length) {
    console.log("\nFIKSTUR: BIREBIR ESLESTI (%d sorgu) — cikis 0 VERILMEZ (fikstur modu)", gecti);
  }
  return process.exit(kod);
}

// Fikstur (tools/parite-fikstur.js) sahte Ege ucunu GERCEK bot koduyla kurar diye
// egeKodu() disa veriliyor. require.main kapisi: import etmek testi KOSTURMAZ.
module.exports = { egeKodu, sorgulariUret, BOT, URUNLER, LIMIT };

if (require.main === module) main();
