#!/usr/bin/env node
/**
 * PRUVO "Jeneratör" GIZLI KATEGORI + SARI KART FIYATI + BANNER kabul testleri
 * (mimar paketi, 17 Tem gece — Okan kararı: 4 kalem).
 *
 *   node jenerator/test/vitrin-kabul.js
 *
 * NE SINANIR (kabul kriterleri birebir):
 *  1 VERI: urunler.json'daki TUM parametrik urunlerin kategorisi "Jeneratör".
 *  2 NAV: ana sayfa kategori menusunde "Jeneratör" YOK (gizli kategori) ama 12 gorunur
 *    kategori + "Tümü" tam.
 *  3 LINK: ?kategori=Jeneratör calisir — baslik "Jeneratör Ürünleri", gridde SADECE
 *    parametrik urunler, banner bu gorunumde YOK. Kaynak, ozet.json'daki ayrik
 *    `parametrik` havuzudur; ayni kategori etiketli genel parcalar sizamaz.
 *  4 KART FIYATI: sari kartta "X TL'den başlayan" — X, jenerator/urunler/<id>.json
 *    tabanFiyatTL'sinden (TEK KAYNAK, elle kopya yok; bicim secenekler.js kurusMetni).
 *    Harita yuklenmemisse (build calismamis) eski "Ölçüye özel fiyat" fallback'i.
 *    SATISA KAPALI ailede (hacim dogrulamasindan gecmemis — secenekler.js
 *    hacimDogrulanmisMi) kart SAYISAL TUTAR BASMAZ: urun sayfasiyla AYNI cumleyi
 *    gosterir (2026-08-04'te olculen canli kusur; tutar hic hesaplanmiyor, sepet
 *    sunucuda 400 ile reddediliyordu).
 *  5 BANNER: ana sayfa gorunumunde VAR (?kategori=Jeneratör'e link verir), arama
 *    gorunumunde YOK.
 *  6 VITRIN: ana sayfanin ilk 4 karti sari (parametrik) — mevcut davranis KALIR.
 *  7 URETIM: `python3 tools/build.py --sadece-taban` taban-fiyatlar.js uretir ve icerigi
 *    semalardaki tabanFiyatTL ile BIREBIR ayni (deploy'un yayina koydugu artefakt).
 *
 * NASIL: index.html'in inline scripti + secenekler.js node:vm icinde minimal DOM
 * taklitiyle GERCEKTEN calistirilir (shop/test/sepet-panel.js deseni) — kod kopyalanmaz,
 * canli dosyanin kendisi sinanir.
 */

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");

const KOK = path.dirname(path.dirname(__dirname));   // jenerator/test -> repo koku
const INDEX = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const SECENEK_SRC = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");

require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }

// Vitrin/arama/sepet kodunu taşıyan inline script. Sayfanın sonuna çerez gibi başka bir
// inline script eklenmesi kabulü bozmamalı; davranış imzasıyla ("renderGrid") seçilir.
// Ayıklama tek kaynaktan (tools/html-blok-ayikla.js) — sepet-panel.js ile ortak.
const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));
const SCRIPT = inlineScriptBul(INDEX, "renderGrid");
if (!SCRIPT) {
  throw new Error("index.html inline scripti bulunamadi (yapi degisti mi?)");
}

// ---- FAZ 3 / EDGE MODU BAGIMLILIGI (30 Tem — kalici kirmizi onarimi) --------------
// index.html'de `var EDGE_KATALOG = true` (FAZ 3 bayragi ACIK). Bayrak acikken acilis
// `acilisEdge()` yolundan gider ve IKI seyi ister:
//   1) uretilmis `ozet.json` artefakti      (fetch("ozet.json"), r.ok kapili)
//   2) Worker `/katalog` + `/ara` cevabi    (EDGE_UC, r.ok kapili)
// Bu test bayrak KAPALIYKEN yazilmisti: sahte fetch yalniz `{ json }` donduruyordu,
// `ok`/`status` yoktu -> sayfa "HTTP undefined" basip console.error'a dusuyor, test
// ALTYAPI HATASI ile oluyordu (7 testten 6'si HIC kosmuyordu, aylardir kirmizi).
//
// COZUM (bagimliligi test KENDI KURAR — ag/sunucu YOK):
//   - ozet.json'u `tools/build.py --sadece-ozet` URETIR (sekil TEK KAYNAK: render_ozet;
//     test kendi kopyasini hesaplamaz). Bkz. test 8: uretilen kart sekli ile testin
//     edge kart projeksiyonu BIREBIR karsilastirilir -> build.py degisirse KIRMIZI.
//   - /katalog + /ara icin TASIMA (transport) taklidi: urunler.json'dan mekanik filtre.
//     ⚠️ ARAMA SEMANTIGI BURADA SINANMAZ (o `tools/parite-test.js` + `tools/parite-ege.js`
//     isi). Buradaki iddia: vitrin DOGRU UCA DOGRU PARAMETREYLE gidiyor ve donen karti
//     dogru ciziyor mu. Taklit gercekten daha musamahali degil: yanlis kategori
//     istenirse yanlis kumeyi doner ve test KIRMIZI yanar (test 3/9).
//   - Tanimsiz her URL 404 -> sayfa console.error basar -> test patlar (SESSIZ YESIL YOK).
const EDGE_UC = (INDEX.match(/var\s+EDGE_UC\s*=\s*"([^"]+)"/) || [])[1];
if (!EDGE_UC) { throw new Error("index.html'de EDGE_UC bulunamadi (yapi degisti mi?)"); }
const PAGE_SIZE = Number((INDEX.match(/var\s+PAGE_SIZE\s*=\s*(\d+)/) || [])[1]);
if (!PAGE_SIZE) { throw new Error("index.html'de PAGE_SIZE bulunamadi (yapi degisti mi?)"); }
const EDGE_KATALOG = /var\s+EDGE_KATALOG\s*=\s*true\s*;/.test(INDEX);

// ozet.json'u SIMDI uret (deploy'un yayina koydugu artefaktin aynisi). Fail-closed:
// uretilemezse test "atlamaz", burada patlar.
const OZET_YOL = path.join(KOK, "ozet.json");
const BUILD_YOL = path.join(KOK, "tools", "build.py");
// (1) BAYRAK VARLIK KAPISI — cagirmadan ONCE. Iki sebep:
//   a) bayrak yoksa build.py TAM BUILD'e duser: 14k urun sayfasi + sitemap + feed yazar VE
//      elle korunan dort yasal sayfayi yeniden damgalar. Bir kabul testinin yan etkisi bu
//      olamaz (30 Tem'de mutasyon turunda BASIMIZA GELDI, dort yasal sayfa kirlendi).
//   b) sessiz yesil onlemi: bayrak dusunce testin "eski ozet.json'la devam etmesi" yasak.
// ⚠️ ALT DIZE DEGIL TAM JETON: ilk yazimda `indexOf("--sadece-ozet")` vardi ve V5
// mutasyonu ("--sadece-ozet-YOK") bu kontrolu ALT DIZE olarak GECIYORDU.
if (fs.readFileSync(BUILD_YOL, "utf8").indexOf('"--sadece-ozet"') === -1) {
  throw new Error("build.py'de \"--sadece-ozet\" bayragi YOK — ozet.json uretilemez " +
    "(tam build TETIKLENMEDI: 14k sayfa + yasal sayfa damgasi yan etkisi olurdu)");
}
// (2) BAYAT ARTEFAKT SILINIR — yeniden uretilmediyse asagidaki kapilar patlar.
//     (V5 mutasyonu: diskte kalan bayat ozet.json'la test YESIL yaniyordu.)
try { fs.unlinkSync(OZET_YOL); } catch (e) { if (e.code !== "ENOENT") { throw e; } }
let ozetCikti = "";
try {
  ozetCikti = String(execFileSync("python3", [BUILD_YOL, "--sadece-ozet"],
    { cwd: KOK, timeout: 120000 }));
} catch (e) {
  throw new Error("ozet.json uretilemedi (build.py --sadece-ozet): " + ((e && e.message) || e));
}
// (3) DAMGA KAPISI — ASIL fail-closed nobetci. `--sadece-ozet` kolu bu satiri basar; bayrak
//     cozulmezse build.py TAM BUILD'e duser, o kol bu damgayi BASMAZ (baska metin basar) ve
//     ozet.json'u yan urun olarak yine yazar. Sadece "dosya var mi" baksaydik test, istemedigi
//     14k-sayfalik tam build'i kosmus olur ve YESIL yanardi (V5 mutasyonu bunu kanitladi).
if (!/^OK: ozet\.json uretildi/m.test(ozetCikti)) {
  throw new Error("build.py --sadece-ozet beklenen damgayi BASMADI (tam build'e dusmus " +
    "olabilir) — bagimlilik dogrulanamadi, test OLCUM YAPAMAZ. Cikti: " +
    JSON.stringify(ozetCikti.slice(0, 300)));
}
if (!fs.existsSync(OZET_YOL)) {
  throw new Error("build.py --sadece-ozet kosdu ama ozet.json ORTAYA CIKMADI — " +
    "bagimlilik kurulamadi, test OLCUM YAPAMAZ (sessizce yesil SAYILMAZ)");
}
const OZET = JSON.parse(fs.readFileSync(OZET_YOL, "utf8"));

// ---- TEK KAYNAK: jenerator/urunler/*.json semalarindan taban fiyat haritasi ----
const URUNLER = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
const PARAMETRIK = URUNLER.filter((u) => u.parametrik);
const SEMA_DIR = path.join(KOK, "jenerator", "urunler");
const TABAN = {};       // id -> tabanFiyatTL (null olanlar haritaya GIRMEZ — fallback yolu)
const TABANSIZ = [];    // yargi listesi: semasi olmayan ya da tabanFiyatTL null sari urunler
const KAPALI = {};      // id -> 1: SATISA KAPALI (hacmi dogrulanmamis) aile
/* SATIS KAPISI (2026-08-04): hacmi dogrulanmamis ailede parametrikFiyatKurus null doner ve
   Worker sepeti 400 `hacim-dogrulanmamis` ile reddeder -> kart SAYISAL TUTAR BASAMAZ; taban
   fiyati DOLU olsa bile haritaya girmez. Karar secenekler.js'in KENDI fonksiyonundan
   (hacimDogrulanmisMi) gelir — bu dosyaya aile listesi KOPYALANMAZ. */
for (const u of PARAMETRIK) {
  const yol = path.join(SEMA_DIR, u.id + ".json");
  if (!fs.existsSync(yol)) { TABANSIZ.push(u.id + " (SEMA YOK)"); continue; }
  const sema = JSON.parse(fs.readFileSync(yol, "utf8"));
  if (!SECENEK.hacimDogrulanmisMi(sema.hacimFormulu)) { KAPALI[u.id] = 1; continue; }
  if (sema.tabanFiyatTL == null) { TABANSIZ.push(u.id + " (tabanFiyatTL null)"); continue; }
  TABAN[u.id] = sema.tabanFiyatTL;
}
/* Fiyat URETILEMEYEN urunde gosterilen cumle — secenekler.js'in `kurus == null` dalindan
   GERCEKTEN cagrilarak alinir (elle ikinci kopya yazilmaz; urun sayfasi da ayni cumleyi basar). */
const FIYATSIZ_METIN = SECENEK.satirOzeti(
  null, { parametreler: {}, parametrik_fiyat_kurus: null, adet: 1 }).fiyatMetni;
function beklenenKartMetni(id) {
  if (id in TABAN) { return SECENEK.kurusMetni(Math.round(TABAN[id] * 100)) + "'den başlayan"; }
  return (id in KAPALI) ? FIYATSIZ_METIN : "Ölçüye özel fiyat";
}

// ------------------------------------------------------------- minimal DOM takliti
// (shop/test/sepet-panel.js deseninin vitrine uyarlanmis hali)

function eleman(tag) {
  const el = {
    tagName: String(tag || "div").toUpperCase(),
    children: [], parentNode: null,
    style: {}, dataset: {}, attrs: {},
    className: "", textContent: "",
    disabled: false, checked: false, value: "", href: "",
    onclick: null, onerror: null,
  };
  let html = "";
  Object.defineProperty(el, "innerHTML", {
    get() { return html; },
    set(v) { html = String(v); el.children.length = 0; },
  });
  el.classList = {
    add(c) { if (!this.contains(c)) { el.className = (el.className + " " + c).trim(); } },
    remove(c) { el.className = el.className.split(/\s+/).filter((x) => x !== c).join(" "); },
    contains(c) { return el.className.split(/\s+/).indexOf(c) !== -1; },
    toggle(c) { this.contains(c) ? this.remove(c) : this.add(c); },
  };
  el.appendChild = (c) => { el.children.push(c); c.parentNode = el; return c; };
  el.removeChild = (c) => { el.children = el.children.filter((x) => x !== c); };
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); };
  el.removeAttribute = (k) => { delete el.attrs[k]; if (k === "href") { el.href = ""; } };
  el.getAttribute = (k) => (k in el.attrs ? el.attrs[k] : null);
  el.addEventListener = () => {};
  el.focus = () => {};
  el.scrollIntoView = () => {};
  el.querySelector = () => null;
  el.querySelectorAll = () => [];
  return el;
}

// Agacta className'i verilen sinifi iceren TUM elemanlar (kart fiyatlarini bulmak icin).
function sinifla(el, cls, sonuc) {
  sonuc = sonuc || [];
  if ((el.className || "").split(/\s+/).indexOf(cls) !== -1) { sonuc.push(el); }
  for (const c of el.children) { sinifla(c, cls, sonuc); }
  return sonuc;
}

function belgeKur() {
  const kimlikler = new Map();
  const seciciler = new Map();
  const belge = {
    getElementById(id) {
      if (!kimlikler.has(id)) { const e = eleman("div"); e.id = id; kimlikler.set(id, e); }
      return kimlikler.get(id);
    },
    createElement: (tag) => eleman(tag),
    querySelector(sel) {
      if (!seciciler.has(sel)) { seciciler.set(sel, eleman("div")); }
      return seciciler.get(sel);
    },
    body: eleman("body"),
    execCommand: () => true,
  };
  return { belge };
}

function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

// --------------------------------------------------- edge tasima taklidi (sunucusuz)

// 🔴 BAGIMSIZ CAPA — bu sayi build.py'DEN OKUNMAZ, BILEREK ELLE SABIT.
// Ilk yazimda `OZET_ACIKLAMA_KES` build.py kaynagindan regex'le okunuyordu. Mutasyon
// olcumu (V3, 30 Tem) bunun nobetciyi OLDURDUGUNU kanitladi: build.py'de 160 -> 120
// yapildiginda hem uretilen ozet.json hem testin beklentisi AYNI ANDA kayiyor, iki taraf
// da ayni yonde hareket ettigi icin test 9/0 YESIL yaniyordu (anchor-coupling tuzagi).
// Sinir bir IKI TARAFLI SOZLESME: build.py kart_ozeti ile Worker'in KART_ALANLARI
// substr(aciklama,1,160)'i BIREBIR ayni olmali (build.py'deki kendi notu). O yuzden
// degisiklik SESSIZ olmamali — burayi kirmizi yakip elle onay istemeli.
const ACIKLAMA_KES = 160;

/** urunler.json objesi -> Worker/ozet kart sekli (build.py kart_ozeti'nin aynisi).
 *  Bu projeksiyonun build.py ile BIREBIR oldugu test 8'de OLCULUR (drift = kirmizi).
 *
 *  IKIZ-TANIM DRIFT DUZELTMESI (15 Agu): JS `[]` truthy, Python `[]` falsy; hizalanmazsa
 *  bos dizili alanlar (gorseller) uc tarafta biri `null`, digeri `undefined` doner ve
 *  JSON.stringify sonunda DOSYA DUSURULUR — kart sekli sessizce ayrisir. taradigim
 *  `|| [null]` / `|| []` kaliplari:
 *    - `gorsel: (p.gorseller || [null])[0]`  → DUZELTILDI (bos dizi hâlâ `[null]`).
 *    - `marka: p.marka || []`               → ZATEN HIZALI (her iki dil `[]` uretir). */
function edgeKart(p) {
  const kart = {
    id: p.id,
    baslik: p.baslik || "",
    kategori: p.kategori || "",
    marka: p.marka || [],
    fiyat: p.fiyat || "",
    gorsel: (p.gorseller && p.gorseller.length ? p.gorseller : [null])[0],
    parametrik: !!p.parametrik,
    aciklama: (p.aciklama || "").slice(0, ACIKLAMA_KES),
  };
  // TICARI HAL (1 Agu): sepet paneli edge modunda fiyati BU karttan hesaplar; secenekler.js
  // satirOzeti `urun.tur`u okuyup fiziksel urunde malzeme/renk carpanini 1,00'e sabitler.
  // Alan KOSULLU basilir (build.py kart_ozeti ile ayni kural): yalniz TAM "fiziksel";
  // ALAN YOK = ozel uretim (3D). Kapsam nobetcisi AYRI bir kapida ve ALAN LISTESI
  // ekseninde: tools/edge-kart-kapisi.py (buradaki izdusum yalniz "taklit == gercek" der).
  if (p.tur === "fiziksel") { kart.tur = "fiziksel"; }
  // ON-SECILI MALZEME + OLCUYE OZEL KOL (11 Agu): secenekler.js onSecimMalzeme()
  // `urun.tavsiyeFilament`i on-secer, `urun.konfigur` tasiyan urunde on-secimi HIC
  // uygulamaz; ikisi de sepet tutarini surer. build.py kart_ozeti ile AYNI kural:
  // deger tasimayan urunde alan HIC yazilmaz, tasiyanda BIREBIR kopyalanir.
  if (p.tavsiyeFilament) { kart.tavsiyeFilament = p.tavsiyeFilament; }
  if (p.konfigur) { kart.konfigur = p.konfigur; }
  // BOY VARYANTI (17 Agu / K164): sepet fiyatini surer (secenekler.js boyFarki); build.py
  // kart_ozeti ile ayni kural — deger tasimayan urunde alan HIC yazilmaz, tasiyanda
  // BIREBIR kopyalanir. Bu satir duserse tools/edge-kart-kapisi.py KIRMIZI yanar (drift).
  if (p.boy_secenekleri) { kart.boy_secenekleri = p.boy_secenekleri; }
  return kart;
}

function cevap(veri, kod) {
  kod = kod || 200;
  return {
    ok: kod >= 200 && kod < 300,
    status: kod,
    json: () => Promise.resolve(JSON.parse(JSON.stringify(veri))),
  };
}

/** /katalog: kategori/marka filtresi + sayfa/boy dilimi; sira = urunler.json DIZI sirasi
 *  (D1 "ORDER BY seq DESC" varsayimi — tools/faz3-sayfalama.js o varsayimi ayrica olcer). */
function ucKatalog(p) {
  const ids = p.get("ids");
  if (ids) {
    const kume = new Set(ids.split(","));
    return { urunler: URUNLER.filter((u) => kume.has(u.id)).map(edgeKart) };
  }
  const kat = p.get("kategori");
  const mar = p.get("marka");
  const sayfa = Math.max(1, Number(p.get("sayfa") || 1));
  const boy = Math.max(1, Number(p.get("boy") || PAGE_SIZE));
  let liste = URUNLER;
  if (kat) { liste = liste.filter((u) => u.kategori === kat); }
  if (mar) { liste = liste.filter((u) => (u.marka || []).indexOf(mar) !== -1); }
  return {
    toplam: liste.length,
    urunler: liste.slice((sayfa - 1) * boy, sayfa * boy).map(edgeKart),
  };
}

/** /ara: TASIMA taklidi — basit baslik icerme. Arama SEMANTIGI burada iddia EDILMEZ
 *  (tek kaynak: tools/parite-test.js + tools/parite-ege.js). */
function ucAra(p) {
  const q = (p.get("q") || "").toLocaleLowerCase("tr");
  const limit = Math.max(1, Number(p.get("limit") || PAGE_SIZE));
  const liste = URUNLER.filter((u) =>
    (u.baslik || "").toLocaleLowerCase("tr").indexOf(q) !== -1);
  return { toplam: liste.length, urunler: liste.slice(0, limit).map(edgeKart) };
}

/**
 * index.html scriptini verilen URL/haritayla calistirir.
 *   ayar.search       location.search (or. "?kategori=Jeneratör")
 *   ayar.tabanHarita  window.PRUVO_TABAN_FIYATLAR (yoksa hic tanimlanmaz — 404 fallback'i)
 *   ayar.seed         vitrin tohumunu SABITLER (deterministik olcum; asagidaki nota bak)
 */
async function sayfaKur(ayar) {
  const { belge } = belgeKur();
  const konsolHatalari = [];
  const istekler = [];              // sahte fetch'e dusen TUM URL'ler (sirayla)
  const ctx = {
    document: belge,
    location: { hash: "", search: ayar.search || "", pathname: "/", href: "", replace() {} },
    history: { replaceState() {} },
    localStorage: {
      getItem: () => null, setItem: () => {}, removeItem: () => {},
    },
    /* URL-DUYARLI sahte fetch. `ok`/`status` TASIR (index.html iki fetch'te de
       `if(!r.ok) throw new Error("HTTP " + r.status)` kapisi kullaniyor — eski taklit
       bu alanlari tasimadigi icin sayfa "HTTP undefined" basiyordu).
       Her istek `istekler`e yazilir; testler HANGI UCA HANGI PARAMETREYLE gidildigini
       iddia eder (test 9). Tanimsiz URL 404 -> sayfa console.error basar -> test patlar. */
    fetch(url) {
      const ham = String(url);
      istekler.push(ham);
      if (ham === "ozet.json" || ham.indexOf("ozet.json") === 0) { return Promise.resolve(cevap(OZET)); }
      // bayrak KAPALI yolu (acilisYerel) da calisabilsin — geri donus yolu test edilebilir kalsin
      if (ham.indexOf("urunler.json") === 0) { return Promise.resolve(cevap(URUNLER)); }
      if (ham.indexOf(EDGE_UC) === 0) {
        const u = new URL(ham);
        if (u.pathname === "/katalog") { return Promise.resolve(cevap(ucKatalog(u.searchParams))); }
        if (u.pathname === "/ara") { return Promise.resolve(cevap(ucAra(u.searchParams))); }
      }
      return Promise.resolve(cevap({ hata: "taklit edilmemis istek: " + ham }, 404));
    },
    console: { log() {}, error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
    alert() {},
    navigator: {},
    URLSearchParams,
    setTimeout, clearTimeout,
    Math,   // shuffle Math.random kullanir
    /* URL-senkron paketi (yukari-cik oku) window.addEventListener("scroll") +
       scrollTo cagiriyor — sahte pencerede no-op karsiliklari (sepet-panel.js ile ayni). */
    addEventListener() {}, removeEventListener() {},
    scrollTo() {}, scrollY: 0, innerHeight: 720,
  };
  ctx.window = ctx;
  /* TOHUM ENJEKSIYONU — YALNIZ OLCUM TARAFINDA. index.html acilista
     `VITRIN_SEED = Math.floor(Math.random() * 4294967296)` uretir; burada vm baglaminin
     Math'i sabit `random`li bir turevle degistirilir. URETIM KODUNA TEK SATIR EKLENMEZ:
     canlida vitrin her yenilemede yine farkli sirada gelir (bu bir URUN karari, testin
     isi degil). r = seed / 2^32 tam olarak temsil edilebilir (2'nin kuvveti bolen), yani
     floor(r * 2^32) === seed BIREBIR doner; testin kendisi bunu ayrica DOGRULAR. */
  if (ayar.seed !== undefined) {
    const oran = (ayar.seed >>> 0) / 4294967296;
    const sabitMath = Object.create(Math);
    sabitMath.random = () => oran;
    ctx.Math = sabitMath;
  }
  if (ayar.tabanHarita) { ctx.PRUVO_TABAN_FIYATLAR = ayar.tabanHarita; }
  /* Satisa kapali aile isareti + fiyatsiz cumle: taban-fiyatlar.js'in AYNI dosyada
     yayina koydugu iki global. Verilmezse sayfa "artefakt inmemis" halini yasar
     (kart eski fallback metnine duser) — o yol da test ediliyor. */
  if (ayar.kapaliHarita) {
    ctx.PRUVO_SATIS_KAPALI = ayar.kapaliHarita;
    ctx.PRUVO_FIYATSIZ_METIN = FIYATSIZ_METIN;
  }
  vm.createContext(ctx);
  vm.runInContext(SECENEK_SRC, ctx, { filename: "secenekler.js" });
  vm.runInContext(SCRIPT, ctx, { filename: "index-inline.js" });
  // fetch zinciri + isitHaystack setTimeout turlari bosalsin (buyuk katalog: birkac tur)
  for (let i = 0; i < 8; i++) { await bekle(15); }
  if (konsolHatalari.length) {
    throw new Error("sayfa scripti hata basti: " + konsolHatalari.join(" | "));
  }
  return {
    el: (id) => belge.getElementById(id),
    kartlar: () => belge.getElementById("grid").children,
    istekler: () => istekler.slice(),
    // Sayfanin KENDI `window`u: tani yuzeyi (PRUVO_VITRIN) buradan okunur, boylece
    // vitrin blok duzeni bu dosyaya KOPYALANMAZ.
    pencere: () => ctx,
  };
}

// Karttan (baslik, kategori, fiyat metni, parametrik-rozet) cikar. `kategori` ZIYARETCININ
// GORDUGU degerdir (kartCiz `card-cat`e p.kategori'yi basar) — katalogdan ikinci kez
// turetmeye gerek yok, kart-baslik esleme tablosu da ACILMAZ.
/* 🔴 GORUNEN ETIKET <-> IC AD (11 Agu). Gizli serinin ic adi artik musteriye gorunen
   yuzeylerde (kart rozeti, bolum basligi, banner linki) GECMIYOR; yerine gorunur etiket
   basiliyor. VERI ic adi tasimaya devam ediyor (urunler.json, ozet.json havuzlari,
   PRUVO_VITRIN.bloklar). Bu kapinin karsilastirdigi iki taraf bu yuzden AYRI DILDE:
   sol taraf GORUNEN metin, sag taraf VERI. Ceviri tablosu index.html'den AYIKLANIR —
   ikinci kopya TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]); tablo cozulemezse ceviri KIMLIKTIR
   (eski davranis) ve bu hal asagida ACIKCA olculur, sessiz yastik DEGILDIR. */
/* Capalar BOSLUGA TOLERANSLI: bicimlendirme degil YAPI olculur. Dar `= ` beklentisi,
   davranisi degistirmeyen bir bosluk duzenlemesinde tabloyu "cozulemedi" sayip kapiyi
   KIRMIZI yakiyordu (kontrol mutanti E5 ile olculdu) — yanlis-pozitif, bu depoda
   TUM EKIBIN yayinini durduran sinif. */
function _indexTablosu(ad) {
  const re = new RegExp("var\\s+" + ad + "\\s*=\\s*(\\{[^;]*\\})\\s*;");
  const m = INDEX.match(re);
  if (!m) { return null; }
  try { return JSON.parse(m[1]); } catch (e) { return null; }
}
const KATEGORI_ALIAS = _indexTablosu("KATEGORI_ALIAS");
const KATEGORI_GORUNUR = _indexTablosu("KATEGORI_GORUNUR");
/** GORUNEN etiket -> IC ad (kart rozeti/baslik gibi gorunen metni VERI diline cevirir). */
function icKategori(etiket) {
  const t = KATEGORI_ALIAS || {};
  return Object.prototype.hasOwnProperty.call(t, etiket) ? t[etiket] : etiket;
}
/** IC ad -> MUSTERIYE GORUNEN etiket (beklenen gorunen metni VERIDEN turetir). */
function gorunurKategori(ic) {
  const t = KATEGORI_GORUNUR || {};
  return Object.prototype.hasOwnProperty.call(t, ic) ? t[ic] : ic;
}

function kartBilgi(card) {
  const baslik = sinifla(card, "card-title")[0];
  const kategori = sinifla(card, "card-cat")[0];
  const fiyat = sinifla(card, "card-price")[0];
  const rozet = sinifla(card, "card-badge")[0];
  return {
    baslik: baslik ? baslik.textContent : "",
    kategori: kategori ? kategori.textContent : "",
    fiyat: fiyat ? fiyat.textContent : "",
    parametrik: !!rozet,
  };
}

let gecen = 0, kalan = 0;
function rapor(ad, hatalar, detay) {
  const ok = hatalar.length === 0;
  ok ? gecen++ : kalan++;
  console.log((ok ? "  ✅ GECTI " : "  ❌ KALDI ") + ad +
    (ok ? (detay ? " — " + detay : "") : " — " + hatalar.slice(0, 4).join(" ; ") +
     (hatalar.length > 4 ? " ; (+" + (hatalar.length - 4) + " hata daha)" : "")));
}

// ------------------------------------------------------------------------ testler

/** 1 — VERI: tum parametrik urunler "Jeneratör" kategorisinde */
function test1Veri() {
  const hatalar = [];
  if (PARAMETRIK.length === 0) { hatalar.push("urunler.json'da hic parametrik urun yok"); }
  for (const u of PARAMETRIK) {
    if (u.kategori !== "Jeneratör") {
      hatalar.push(u.id + " kategorisi '" + u.kategori + "' (Jeneratör olmali)");
    }
  }
  rapor("1 veri: " + PARAMETRIK.length + " parametrik urun kategori=Jeneratör", hatalar,
    PARAMETRIK.length + " urun");
}

/** 2 — NAV: kategori menusunde Jeneratör YOK, gorunur liste tam */
async function test2Nav() {
  const hatalar = [];
  const s = await sayfaKur({});
  const etiketler = [];
  for (const b of s.el("cats").children) {
    etiketler.push(b.textContent || b.attrs["aria-label"] || b.title || "");
  }
  if (etiketler.indexOf("Jeneratör") !== -1) { hatalar.push("nav'da 'Jeneratör' GORUNUYOR"); }
  const beklenen = ["Tüm ürünler", "Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev",
    "Ofis", "Elektronik", "Kamera", "Bahçe", "Dekorasyon", "Oyun/Hobi"];
  for (const k of beklenen) {
    if (etiketler.indexOf(k) === -1) { hatalar.push("nav'da '" + k + "' eksik"); }
  }
  if (etiketler.length !== beklenen.length) {
    hatalar.push("nav " + etiketler.length + " oge (beklenen " + beklenen.length + "): " +
      etiketler.join(","));
  }
  rapor("2 nav: Jeneratör gizli, 12 kategori + Tümü tam", hatalar,
    etiketler.length + " nav ogesi, Jeneratör yok");
}

/** 3 — LINK: ?kategori=Jeneratör gorunumu calisir; banner bu gorunumde YOK */
async function test3JeneratorGorunumu() {
  const hatalar = [];
  const s = await sayfaKur({ search: "?kategori=Jenerat%C3%B6r", tabanHarita: TABAN });
  /* CEVIRI TABLOSU OKUNDU MU — sessiz yastik nobeti. Tablo cozulemezse yukaridaki iki
     yardimci KIMLIGE duser ve bu testin (3/5/6) tamami "ic ad = gorunen ad" varsayimina
     geri doner; o hal SESSIZCE yesil yanardi. Tablonun VARLIGI ayri iddiadir; ICERIGI
     (hangi seri cevriliyor) bilerek iddia EDILMEZ — seri adi publike acilirsa esleme
     mesru olarak bosalir ve burasi yalanci kirmizi vermemeli. */
  if (KATEGORI_ALIAS === null) { hatalar.push("index.html'de KATEGORI_ALIAS cozulemedi"); }
  if (KATEGORI_GORUNUR === null) { hatalar.push("index.html'de KATEGORI_GORUNUR cozulemedi"); }
  /* Derin link IC adla gelmeye devam eder (eski linkler yasar) ama BASLIK musteriye
     gorunen etiketi tasir — beklenti bu yuzden VERIDEN turetilir, elle yazilmaz. */
  const beklenenBaslik = gorunurKategori("Jeneratör") + " Ürünleri";
  if (s.el("sectionTitle").textContent !== beklenenBaslik) {
    hatalar.push("baslik '" + s.el("sectionTitle").textContent +
      "' (beklenen '" + beklenenBaslik + "')");
  }
  const kartlar = s.kartlar();
  // Ilk sayfa IKI modda da PAGE_SIZE ile sinirli (edge: /katalog boy=PAGE_SIZE; yerel:
  // slice(0, shown) ve shown=PAGE_SIZE). Sari seri PAGE_SIZE'i asarsa bu sayi kirpilir —
  // o yuzden beklenti min() ile yazilir, TOPLAM ise resultCount'tan ayrica dogrulanir.
  const beklenenKart = Math.min(PARAMETRIK.length, PAGE_SIZE);
  if (kartlar.length !== beklenenKart) {
    hatalar.push("gridde " + kartlar.length + " kart (beklenen " + beklenenKart + ")");
  }
  if (s.el("resultCount").textContent !== PARAMETRIK.length + " ürün") {
    hatalar.push("toplam sayaci '" + s.el("resultCount").textContent +
      "' (beklenen '" + PARAMETRIK.length + " ürün')");
  }
  for (const c of kartlar) {
    const k = kartBilgi(c);
    if (!k.parametrik) { hatalar.push("parametrik olmayan kart sizdi: " + k.baslik); }
  }
  if (s.el("jenBanner").style.display !== "none") {
    hatalar.push("banner kategori gorunumunde gizlenmedi (display='" +
      s.el("jenBanner").style.display + "')");
  }
  rapor("3 ?kategori=Jeneratör gorunumu + banner gizli", hatalar,
    kartlar.length + " sari kart, baslik dogru, banner yok");
}

/** 4 — KART FIYATI: sema tabaniyla birebir; harita yokken fallback */
async function test4KartFiyati() {
  const hatalar = [];
  const s = await sayfaKur({
    search: "?kategori=Jenerat%C3%B6r", tabanHarita: TABAN, kapaliHarita: KAPALI });
  const idyeBaslik = {};
  for (const u of PARAMETRIK) { idyeBaslik[u.baslik] = u.id; }
  let dogru = 0;
  for (const c of s.kartlar()) {
    const k = kartBilgi(c);
    const id = idyeBaslik[k.baslik];
    if (!id) { hatalar.push("kart basligi katalogda yok: " + k.baslik); continue; }
    const beklenen = beklenenKartMetni(id);
    if (k.fiyat !== beklenen) {
      hatalar.push(id + " karti '" + k.fiyat + "' (beklenen '" + beklenen + "')");
    } else { dogru++; }
  }
  // Spec ornekleri sabitle: o-ring 100 TL, adaptor 150 TL
  if (TABAN["olcuye-ozel-oring-conta"] === 100 &&
      beklenenKartMetni("olcuye-ozel-oring-conta") !== "100,00 TL'den başlayan") {
    hatalar.push("o-ring beklenen metin bicimi bozuk");
  }
  /* SATIS KAPISI — POZITIF + NEGATIF eksen ayni gorunumde olculur: kapali ailenin
     kartinda SAYISAL TL olmamali ve aciklayici cumle olmali; kapi bosa kosmasin diye
     en az 1 kapali kart gorulmus olmali. */
  let kapaliGorulen = 0;
  for (const c of s.kartlar()) {
    const k = kartBilgi(c);
    const id = idyeBaslik[k.baslik];
    if (!id || !(id in KAPALI)) { continue; }
    kapaliGorulen++;
    if (/\d[\d.]*,\d\d\s*TL/.test(k.fiyat)) {
      hatalar.push("SATISA KAPALI " + id + " kartinda sayisal tutar var: '" + k.fiyat + "'");
    }
    if (k.fiyat !== FIYATSIZ_METIN) {
      hatalar.push("SATISA KAPALI " + id + " kartinda aciklayici cumle yok: '" + k.fiyat + "'");
    }
  }
  if (Object.keys(KAPALI).length > 0 && kapaliGorulen === 0) {
    hatalar.push("kapali aile ekseni BOS kostu (hic kapali kart olculmedi)");
  }
  // Fallback: harita yuklenmemis sayfada (build calismamis / 404) eski metin
  const f = await sayfaKur({ search: "?kategori=Jenerat%C3%B6r" });
  for (const c of f.kartlar()) {
    const k = kartBilgi(c);
    if (k.fiyat !== "Ölçüye özel fiyat") {
      hatalar.push("harita yokken fallback bozuk: '" + k.fiyat + "'"); break;
    }
  }
  rapor("4 kart fiyati semayla birebir + fallback", hatalar,
    dogru + " kart dogru ('" + beklenenKartMetni("olcuye-ozel-oring-conta") + "' vb.)");
}

/** 5 — BANNER: ana sayfada VAR + dogru link; arama gorunumunde YOK */
async function test5Banner() {
  const hatalar = [];
  // Banner MARKUP'i gercek HTML'de olmali (sahte DOM getElementById'i oto-uretir,
  // o yuzden markup'i kaynaktan dogruluyoruz).
  if (!/id="jenBanner"/.test(INDEX)) { hatalar.push("index.html'de jenBanner markup'i yok"); }
  const href = INDEX.match(/id="jenBanner"[^>]*href="([^"]*)"/);
  /* YAZMA YONU (11 Agu): derin linke IC ad degil GORUNEN etiket yazilir — ic seri adi
     adres cubuguna da dusmesin. Beklenti bu yuzden ceviri tablosundan TURETILIR; boylece
     etiket degisirse kapi kendiliginden yeni etikete bakar, ama link BASKA bir kategoriye
     kayarsa (ya da hic yoksa) KIRMIZI yanar. */
  const beklenenKat = gorunurKategori("Jeneratör");
  if (!href || decodeURIComponent(href[1]).indexOf("kategori=" + beklenenKat) === -1) {
    hatalar.push("banner linki ?kategori=" + beklenenKat + "'e gitmiyor: " +
      (href ? href[1] : "yok"));
  }
  // OVERLAY METNI: iddia YAPISAL, pazarlama CUMLESI DEGIL.
  // 30 Tem olcumu: eskiden buraya sabit cumle ("PRUVO Jeneratör ile sana özel parça
  // tasarla") gomulmustu. Metin o zamandan beri "Ölçüne özel parça tasarla"ya donmus
  // (pazarlama kopyasi + gizli seri dili degisti) -> iddia BAYAT. Kopyayi test etmek iki
  // yonden yanlis: (1) her kopya guncellemesi yalanci kirmizi uretir, (2) kopya ArTisT'in
  // duzlemi, bu testin degil. Korunan gercek degismez: banner ANCHOR'unun ICINDE gorunur
  // bir metin overlay'i var — BOS OLMAYAN baslik + tiklama cagrisi. Overlay blogu silinir
  // ya da baslik bosalirsa test KIRMIZI yanar.
  const anchorBas = INDEX.indexOf('id="jenBanner"');
  const anchorSon = anchorBas === -1 ? -1 : INDEX.indexOf("</a>", anchorBas);
  const anchor = anchorBas === -1 ? "" : INDEX.slice(anchorBas, anchorSon);
  if (anchor.indexOf("jen-banner-text") === -1) {
    hatalar.push("banner overlay blogu (jen-banner-text) anchor icinde yok");
  }
  const bTitle = anchor.match(/class="jen-banner-title"[^>]*>([^<]*)</);
  if (!bTitle || bTitle[1].trim() === "") {
    hatalar.push("banner overlay basligi (jen-banner-title) yok/bos: " +
      (bTitle ? JSON.stringify(bTitle[1]) : "hic yok"));
  }
  if (anchor.indexOf("jen-banner-btn") === -1) {
    hatalar.push("banner tiklama cagrisi (jen-banner-btn) yok");
  }
  const ana = await sayfaKur({});
  if (ana.el("jenBanner").style.display === "none") {
    hatalar.push("banner ana sayfada gizli");
  }
  const arama = await sayfaKur({ search: "?ara=vida" });
  if (arama.el("jenBanner").style.display !== "none") {
    hatalar.push("banner arama gorunumunde duruyor");
  }
  const kat = await sayfaKur({ search: "?kategori=Tamirat" });
  if (kat.el("jenBanner").style.display !== "none") {
    hatalar.push("banner kategori gorunumunde duruyor");
  }
  rapor("5 banner: ana sayfada var, arama/kategori gorunumunde yok", hatalar,
    "markup + link + gorunum kurali dogru");
}

/* SABIT TOHUM LISTESI — tek "sansli tohum" secmek kiraz-toplama olurdu; iddia bu listenin
   TAMAMINDA aranir, bir tohumda bile dusen iddia KIRMIZI yakar. Liste deterministik
   uretilir (altin oran adimi, 32-bit sarmali) — dosyaya elle sayi dizilmez. */
const VITRIN_SEEDLER = [];
for (let i = 0; i < 32; i++) { VITRIN_SEEDLER.push(((i + 1) * 0x9E3779B1) >>> 0); }

/* ON BLOK KIRLILIK TAVANI — DONMUS, otomatik gevsemez.
   On blok KATEGORI ile tanimli ("Jeneratör"), sari seri ise `parametrik` bayragiyla.
   Ikisi ayrisabilir: bugun ozet.json havuzlarindaki Jeneratör kartlarinin 1'i
   (honda-gx390-egzoz-flansi — gercek bir jenerator yedek parcasi, parametrik DEGIL)
   sari degil. Tavan bu olculen halden dogar; ikinci bir kirletici gelirse kapi KIRMIZI
   yanar ve karar MIMARINDIR (veri mi duzelir, blok uyeligi mi `parametrik`e baglanir).
   Havuzdan dogan bir esik yazilsaydi kapi kendini SESSIZCE gevsetirdi. */
const ON_BLOK_KIRLILIK_TAVANI = 1;

/** 6 — VITRIN: ana sayfanin ilk `adet` slotu ON BLOK'tan gelir (deterministik tohum suprumu).
 *
 * 🔴 ESKI HALI KARARSIZDI — OLCULDU (5 Agu 2026, degismemis main, 25 ardisik kosum:
 * 21 YESIL / 4 KIRMIZI). Iddia "ana sayfanin ilk 4 karti PARAMETRIK" idi; vitrin sirasi
 * sayfa yuklemesi basina uretilen `VITRIN_SEED = Math.random()` ile her kosumda degisiyor
 * ve parametrik OLMAYAN tek Jeneratör karti 4 slottan birine 4/24 = %16,7 ihtimalle
 * dusuyordu. Kapi `continue-on-error`suz oldugu icin TUM EKIBIN yayini rastgele duruyordu.
 * "Ilk 4 kart sari" HICBIR ZAMAN invaryant DEGILDI; yesil yandigi kosumlarda kapi
 * gercek bir sey degil, YAZI-TURA olcuyordu.
 *
 * ONARIM (mimar hukmu: iddiayi zayiflatma, OLCUMU determinist yap):
 *  (a) TOHUM ENJEKTE EDILIR (sayfaKur ayar.seed) — URETIM DAVRANISI DEGISMEZ, index.html'e
 *      tek satir eklenmedi; canlida rastgelelik AYNEN durur.
 *  (b) Enjeksiyonun TUTTUGU once dogrulanir: tutmasaydi olcum yine rastgele olur ve
 *      "deterministik" iddiasi SESSIZCE yalan olurdu.
 *  (c) Iddia gercek invaryanta baglanir: ilk `adet` slot ON BLOGUN uyesidir. Blok tanimi
 *      (kategori + adet) sayfanin KENDI `window.PRUVO_VITRIN.bloklar`indan okunur — bu
 *      dosyaya kopyalanmaz ([[ikiz-tanim-sessiz-ayrisma]]).
 *  (d) Sari serinin on bloktan dusme riski SESSIZ GECMEZ: havuz kirliligi sayiyla basilir,
 *      donmus tavan asilirsa kirmizi yanar.
 * KORELME KONTROLU: onarim gercek alarmi da susturmus olabilirdi
 * ([[duzeltme-fail-open-cevirebilir]]) — tools/vitrin-kabul-mutasyon.js sari seriyi on
 * bloktan dusuren gercek gerilemeleri uygular ve bu testin HALA kirmizi yandigini olcer.
 */
async function test6Vitrin() {
  const hatalar = [];
  const ilk = await sayfaKur({ tabanHarita: TABAN, seed: VITRIN_SEEDLER[0] });
  const vitrin = ilk.pencere().PRUVO_VITRIN;
  const ilkKartlar = ilk.kartlar();
  const undefinedId = ilkKartlar.filter((card) => {
    const ana = sinifla(card, "card-main")[0];
    return !ana || /\/undefined\/?$/.test(ana.href || "");
  }).length;
  if (undefinedId) {
    hatalar.push("canli index tuketicisi " + undefinedId + " undefined id'li kart cizdi");
  }
  if (!vitrin || !vitrin.bloklar || !vitrin.bloklar.length ||
      typeof vitrin.seedAl !== "function" || typeof vitrin.ozetAl !== "function") {
    rapor("6 vitrin: ilk slotlar on bloktan (deterministik tohum suprumu)",
      ["window.PRUVO_VITRIN tani yuzeyi okunamadi (bloklar/seedAl/ozetAl yok) " +
       "— OLCUM YAPILAMADI"]);
    return;
  }
  const onBlok = vitrin.bloklar[0];
  const adet = onBlok.adet;
  /* 🔴 CAPA — blok tanimini sayfadan OKUMANIN BEDELI: beklenti kaynakla birlikte kayarsa
     "on blogu tamamen kaldir" mutanti da YESIL gecerdi (anchor-coupling,
     [[anahat-referans-tautolojisi]]). Bu iki satir kaymayan sozlesmedir: ilk blok SARI
     SERININ blogudur (`kaynak:"parametrik"`) ve EN AZ BIR slotu vardir. */
  if (onBlok.kaynak !== "parametrik") {
    hatalar.push("ON BLOK sari seriye ait DEGIL: kaynak='" + onBlok.kaynak +
      "' (beklenen 'parametrik') — vitrinin ilk slotlari sari seriden alinmis");
  }
  if (!(adet >= 1)) {
    hatalar.push("ON BLOK slot adedi " + adet + " — sari seri vitrinden fiilen kalkmis " +
      "(0 slot iddiayi da BOSA dusururdu)");
  }
  // (b) ENJEKSIYON FIILEN TUTTU MU
  if (vitrin.seedAl() !== VITRIN_SEEDLER[0]) {
    hatalar.push("tohum enjeksiyonu TUTMADI: seedAl()=" + vitrin.seedAl() +
      " (beklenen " + VITRIN_SEEDLER[0] + ") — olcum DETERMINIST DEGIL");
  }

  // (d) ON BLOK HAVUZU — ana sayfanin yukledigi liste ozet.json havuzlarindan gelir.
  // Ham ozet.json v2 kartlari sıralı dizidir. Alan sözleşmesini burada ikinci kez
  // yorumlamak yerine canli sayfanin ozetAc() tüketicisinden geçmiş kartlar okunur.
  const canliOzet = vitrin.ozetAl();
  const gorulen = new Set();
  const onHavuz = [];
  for (const anahtar of Object.keys(canliOzet || {})) {
    const v = canliOzet[anahtar];
    const listeler = Array.isArray(v) ? [v]
      : (v && typeof v === "object" ? Object.keys(v).map((k) => v[k]) : []);
    for (const liste of listeler) {
      if (!Array.isArray(liste)) { continue; }
      for (const c of liste) {
        if (!c || !c.id || gorulen.has(c.id)) { continue; }
        gorulen.add(c.id);
        if ((c.kategori || "") === onBlok.kategori) { onHavuz.push(c); }
      }
    }
  }
  const kirli = onHavuz.filter((c) => !c.parametrik);
  if (onHavuz.length < adet) {
    hatalar.push("on blok havuzu " + onHavuz.length + " kart, slot " + adet +
      " — blok KISALIR, ilk slotlar baska bloktan dolar");
  }
  if (kirli.length > ON_BLOK_KIRLILIK_TAVANI) {
    hatalar.push("on blok havuzunda " + kirli.length + " parametrik OLMAYAN kart (donmus " +
      "tavan " + ON_BLOK_KIRLILIK_TAVANI + "): " +
      kirli.slice(0, 5).map((c) => c.id).join(", ") + " — sari seri on bloktan dusebilir");
  }

  // (c) TOHUM SUPRUMU: her sabit tohumda ilk `adet` slot ON BLOGUN uyesi mi?
  let enAzSari = adet, enKotuTohum = null;
  for (const s of VITRIN_SEEDLER) {
    const sayfa = await sayfaKur({ tabanHarita: TABAN, seed: s });
    const kartlar = sayfa.kartlar();
    if (kartlar.length < adet) {
      hatalar.push("tohum " + s + ": ana sayfada " + kartlar.length + " kart (< " + adet + ")");
      continue;
    }
    let sari = 0;
    for (let i = 0; i < adet; i++) {
      const k = kartBilgi(kartlar[i]);
      /* Kart rozeti GORUNEN etiketi tasir, blok tanimi (PRUVO_VITRIN.bloklar) VERI adini —
         kiyas TEK dile indirilir. Ceviri yalnizca ADI degistirir: baska bir kategoriden
         gelen kart hala ON BLOK DISI sayilir. */
      if (icKategori(k.kategori) !== onBlok.kategori) {
        hatalar.push("tohum " + s + ": " + (i + 1) + ". slot ON BLOK DISI ('" + k.kategori +
          "' != '" + onBlok.kategori + "'): " + k.baslik);
      }
      if (k.parametrik) { sari++; }
    }
    if (sari < enAzSari) { enAzSari = sari; enKotuTohum = s; }
  }
  rapor("6 vitrin: ilk " + adet + " slot ON BLOK '" + onBlok.kategori + "' (" +
    VITRIN_SEEDLER.length + " sabit tohum)", hatalar,
    VITRIN_SEEDLER.length + " tohum x " + adet + " slot; havuz " + onHavuz.length +
    " kart / " + kirli.length + " parametrik degil (tavan " + ON_BLOK_KIRLILIK_TAVANI +
    "); index cizilen " + ilkKartlar.length + " / undefined id " + undefinedId +
    "; en kotu tohumda (" + enKotuTohum + ") " + enAzSari + "/" + adet + " sari");
}

/** 7 — URETIM: build.py --sadece-taban ciktisi semalarla birebir */
function test7Uretim() {
  const hatalar = [];
  const buildSrc = fs.readFileSync(path.join(KOK, "tools", "build.py"), "utf8");
  if (buildSrc.indexOf("--sadece-taban") === -1) {
    hatalar.push("build.py'de --sadece-taban yok (tam build tetiklememek icin kosulmadi)");
    rapor("7 uretim: taban-fiyatlar.js semalarla birebir", hatalar);
    return;
  }
  try {
    execFileSync("python3", [path.join(KOK, "tools", "build.py"), "--sadece-taban"],
      { cwd: KOK, timeout: 60000 });
    const js = fs.readFileSync(path.join(KOK, "taban-fiyatlar.js"), "utf8");
    const m = js.match(/window\.PRUVO_TABAN_FIYATLAR\s*=\s*(\{[\s\S]*?\});/);
    if (!m) { throw new Error("taban-fiyatlar.js bicimi cozulmedi"); }
    const uretilen = JSON.parse(m[1]);
    const beklenenIdler = Object.keys(TABAN).sort();
    const uretilenIdler = Object.keys(uretilen).sort();
    if (JSON.stringify(beklenenIdler) !== JSON.stringify(uretilenIdler)) {
      hatalar.push("id kumesi farkli: uretilen " + uretilenIdler.length +
        " / beklenen " + beklenenIdler.length);
    }
    for (const id of beklenenIdler) {
      if (uretilen[id] !== TABAN[id]) {
        hatalar.push(id + ": uretilen " + uretilen[id] + " != sema " + TABAN[id]);
      }
    }
    /* SATIS KAPISI artefakti: kapali ailenin id'si haritada HIC olmamali (sayi tasiyicisi
       burasi), kapali kume + fiyatsiz cumle ise yayina koyulmus olmali. */
    for (const id of Object.keys(KAPALI)) {
      if (id in uretilen) {
        hatalar.push("SATISA KAPALI " + id + " taban haritasinda: " + uretilen[id]);
      }
    }
    const mk = js.match(/window\.PRUVO_SATIS_KAPALI\s*=\s*(\{[\s\S]*?\});/);
    const mf = js.match(/window\.PRUVO_FIYATSIZ_METIN\s*=\s*("(?:[^"\\]|\\.)*");/);
    if (!mk) { hatalar.push("taban-fiyatlar.js PRUVO_SATIS_KAPALI basmiyor"); }
    else {
      const uretilenKapali = Object.keys(JSON.parse(mk[1])).sort();
      if (JSON.stringify(uretilenKapali) !== JSON.stringify(Object.keys(KAPALI).sort())) {
        hatalar.push("kapali kume ayristi: uretilen " + JSON.stringify(uretilenKapali) +
          " != beklenen " + JSON.stringify(Object.keys(KAPALI).sort()));
      }
    }
    if (!mf) { hatalar.push("taban-fiyatlar.js PRUVO_FIYATSIZ_METIN basmiyor"); }
    else if (JSON.parse(mf[1]) !== FIYATSIZ_METIN) {
      hatalar.push("fiyatsiz cumle ayristi: " + mf[1] + " != " + JSON.stringify(FIYATSIZ_METIN));
    }
  } catch (e) {
    hatalar.push("uretim kosusu: " + (e && e.message || e));
  }
  rapor("7 uretim: taban-fiyatlar.js semalarla birebir", hatalar,
    Object.keys(TABAN).length + " id, degerler birebir");
}

/** 8 — KART SEKLI SOZLESMESI: testin edge kart projeksiyonu build.py kart_ozeti ile BIREBIR.
 *  NEDEN: /katalog + /ara taklidi kartlari edgeKart() ile uretiyor. O projeksiyon build.py'den
 *  ayrisirsa taklit, GERCEKTE olmayan bir kart sekliyle test yapmis olur (sahte nobetci).
 *  Burada uretilen ozet.json'un GERCEK kartlariyla karsilastirilarak baglaniyor: build.py
 *  kart_ozeti degisir de bu dosya degismezse test KIRMIZI yanar. */
async function test8KartSekli() {
  const hatalar = [];
  const idye = {};
  for (const u of URUNLER) { idye[u.id] = u; }
  // Kart alanlarını ham taşıma dizisinden bu test AÇMAZ. index.html'in üretimdeki
  // ozetAc() tüketicisi tek kanonik `kartAlanlari` sözlüğünü okuyup sözleşme
  // şeklini kurar; test o gerçek çıktıyı bağımsız edgeKart orakiliyle kıyaslar.
  const sayfa = await sayfaKur({ tabanHarita: TABAN });
  const vitrin = sayfa.pencere().PRUVO_VITRIN;
  const canliOzet = vitrin && typeof vitrin.ozetAl === "function" ? vitrin.ozetAl() : null;
  if (!canliOzet) {
    rapor("8 edge kart sekli build.py kart_ozeti ile birebir",
      ["index.html canli ozet tuketicisi okunamadi — OLCUM YAPILAMADI"]);
    return;
  }
  const ornekler = (canliOzet.yeni || []).concat(canliOzet.parametrik || []);
  if (ornekler.length === 0) { hatalar.push("ozet.json'da karsilastirilacak kart YOK"); }
  let karsilastirilan = 0;
  for (const gercek of ornekler) {
    const p = idye[gercek.id];
    if (!p) { hatalar.push("ozet karti urunler.json'da yok: " + gercek.id); continue; }
    const benim = edgeKart(p);
    if (JSON.stringify(benim) !== JSON.stringify(gercek)) {
      hatalar.push(gercek.id + " kart sekli ayristi: test=" + JSON.stringify(benim) +
        " build.py=" + JSON.stringify(gercek));
      break;    // ilk ayrisma yeter (cikti sismesin)
    }
    karsilastirilan++;
  }
  rapor("8 edge kart sekli build.py kart_ozeti ile birebir", hatalar,
    karsilastirilan + " kart birebir (aciklama kesme " + ACIKLAMA_KES + ")");
}

/** 9 — EDGE SOZLESMESI: hangi uca hangi parametreyle gidiliyor + ana sayfada AGA CIKMAMA.
 *  Bu, taklit fetch'in "her seye yesil der" olmadiginin kaniti: vitrin yanlis uca ya da
 *  yanlis parametreyle giderse burasi KIRMIZI yanar. */
async function test9EdgeSozlesmesi() {
  const hatalar = [];
  if (!EDGE_KATALOG) {
    // Bayrak KAPALIYSA edge yolu hic kosmaz; bunu SESSIZ gecmiyoruz, acikca yaziyoruz.
    rapor("9 edge uc sozlesmesi", ["EDGE_KATALOG=false — OLCULEMEDI (edge yolu kosmuyor); " +
      "bayrak acilinca bu iddia otomatik geri gelir"]);
    return;
  }
  // (a) ANA SAYFA: ozet.json yeter, Worker'a istek YOK (index.html:2360 iddiasi).
  const ana = await sayfaKur({ tabanHarita: TABAN });
  const anaIstek = ana.istekler();
  if (anaIstek.length !== 1 || anaIstek[0].indexOf("ozet.json") !== 0) {
    hatalar.push("ana sayfa istekleri beklenen ['ozet.json'] degil: " + JSON.stringify(anaIstek));
  }
  // (b) GIZLI SARI SERI: ozet.json'daki ayrik parametrik havuz yeter; kategori adini
  // paylasan parametrik olmayan urunleri /katalog'dan istemek sessizce sizdirirdi.
  const kat = await sayfaKur({ search: "?kategori=Jenerat%C3%B6r", tabanHarita: TABAN });
  const katalogIstek = kat.istekler().filter((u) => u.indexOf(EDGE_UC + "/katalog") === 0);
  if (katalogIstek.length !== 0 || kat.istekler().length !== 1 ||
      kat.istekler()[0].indexOf("ozet.json") !== 0) {
    hatalar.push("Jeneratör gorunumu yalniz ozet.json kullanmadi: " +
      JSON.stringify(kat.istekler()));
  }
  // (c) ARAMA GORUNUMU: /ara + q + limit (sayfa DEGIL — parite ucunun imzasi)
  const ara = await sayfaKur({ search: "?ara=vida", tabanHarita: TABAN });
  const araIstek = ara.istekler().filter((u) => u.indexOf(EDGE_UC + "/ara") === 0);
  if (araIstek.length !== 1) {
    hatalar.push("/ara istegi " + araIstek.length + " (beklenen 1): " + JSON.stringify(ara.istekler()));
  } else {
    const p = new URL(araIstek[0]).searchParams;
    if (p.get("q") !== "vida") { hatalar.push("q param '" + p.get("q") + "'"); }
    if (p.get("limit") !== String(PAGE_SIZE)) { hatalar.push("limit param '" + p.get("limit") + "'"); }
  }
  rapor("9 edge uc/parametre sozlesmesi + ana sayfa aga CIKMIYOR", hatalar,
    "ana sayfa + sari seri ozet.json, arama /ara");
}

// -------------------------------------------------------------------------- akis

async function main() {
  console.log("PRUVO Jeneratör vitrin kabul testleri (index.html inline scripti node:vm'de)\n");
  test1Veri();
  await test2Nav();
  await test3JeneratorGorunumu();
  await test4KartFiyati();
  await test5Banner();
  await test6Vitrin();
  test7Uretim();
  await test8KartSekli();
  await test9EdgeSozlesmesi();
  if (TABANSIZ.length) {
    console.log("\n  ⚠️ YARGI LISTESI (fiyat karari Okan'in — FIYAT UYDURULMADI):");
    for (const t of TABANSIZ) { console.log("     - " + t); }
  } else {
    console.log("\n  ℹ️ Fiyatsiz sari denetimi: " + PARAMETRIK.length +
      " parametrik urunun HEPSINDE tabanFiyatTL dolu.");
  }
  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" +
    (kalan ? "" : " — HEPSI YESIL ✅"));
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => {
  console.error("\nTEST ALTYAPI HATASI:", e && e.stack || e);
  process.exit(1);
});
