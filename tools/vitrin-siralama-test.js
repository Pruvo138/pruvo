#!/usr/bin/env node
/**
 * PRUVO — ANA SAYFA VITRIN HIYERARSISI KABUL TESTI (Okan kurali, 31 Tem 2026)
 *
 *   node tools/vitrin-siralama-test.js
 *
 * KURAL (Okan): "ana sayfanin ilk 4'lu sirasi jenerator urunlere, sonraki 20 4'lu sirasi
 * marin urunlere, sonraki 20 4'lu sirasi otomobile, geri kalani tum kategorilere ayrilsin.
 * tum ana sayfa urunleri her sayfa yenilenmesinde kendi hiyerarsisi icinde random
 * siralansin." MIMAR YORUMU (karara baglandi): "4'lu sira" = SABIT KART SAYISI (DOM satiri
 * degil; grid responsive) -> slot 0-3 Jenerator · 4-83 Marin · 84-163 Otomobil · 164+
 * KARISIK tek havuz. Rastgelelik YALNIZ filtresiz ana vitrinde. Urun ELENMEZ.
 *
 * NEDEN BU TEST VAR (hatanin SESSIZLIGI): ana sayfa kartlari ziyaretciye DORT ayri
 * besleme yolundan gelebiliyor —
 *   (1) ozet.json ilk boyamasi          (edgeYukle sayfa 1, aga hic cikmadan)
 *   (2) ozet.json inmezse Worker /katalog?sayfa=1 cevabi
 *   (3) Worker duserse edgeYedek havuzu
 *   (4) EDGE_KATALOG=false yolunda HOME_ORDER (bayrak geri alinirsa)
 * Kural yollardan yalnizca birine konsaydi vitrin bazi ziyaretcide dogru, bazisinda
 * yanlis gorunur ve KIMSE FARK ETMEZDI. Bu test dort yolu da AYRI AYRI olcer.
 *
 * IKI EKSEN:
 *   ISTEMCI EKSENI — index.html vitrinSirala(liste, seed): blok duzenini kurar, her blogu
 *     KENDI ICINDE seed'li karistirir. Seed sayfa yuklemesinde BIR KEZ uretilir ve
 *     sayfalama boyunca SABIT kalir.
 *   DERLEME EKSENI — tools/build.py render_ozet(): SIRALAMAZ, yalnizca blok HAVUZLARINI
 *     ozet.json'a yazar (sirayi derlemede sabitlemek "her yenilemede random"i oldururdu).
 *
 * NASIL: index.html'in inline scripti node:vm icinde minimal DOM + URL-duyarli sahte
 * fetch ile GERCEKTEN calistirilir (jenerator/test/vitrin-kabul.js ve
 * shop/test/sepet-panel.js deseni). Kod KOPYALANMAZ — canli dosyanin kendisi kosar.
 * ozet.json da KOPYA kuralla degil GERCEK build.py ile uretilir.
 *
 * ⚠️ FIKSTUR, CANLI KATALOG DEGIL: her iddia SENTETIK fikstur uzerinde olculur ve
 * fiksturun BOS OLMADIGI ayrica kanitlanir (karsi-olcumler). Canli katalog yalnizca
 * uctan uca iddiada (son test) kullanilir.
 *
 * ⚠️ BAGIMSIZ CAPA: blok duzeni (kategori + adet) index.html'den OKUNMAZ, burada ELLE
 * sabittir (SLOT_DUZEN). Iki taraf ayni kaynaktan okusaydi kural sessizce degistirilebilir
 * ve test yine yesil yanardi ([[kapi-anchor-coupling-ikilemi]]). Kural degisirse bu dosya
 * KIRMIZI yanar ve elle onay ister.
 *
 * NE IDDIA EDILMEZ: arama SEMANTIGI (tek kaynak tools/parite-test.js + parite-ege.js),
 * Worker/D1'in kendi sirasi (pruvo-bot duzlemi), SEO/sitemap, ozet.json BAYT BUTCESI
 * (tools/faz3-yuk.js).
 *
 * MUTASYON KANITI:  node tools/vitrin-siralama-test.js --index /gecici/mutant-index.html
 *                   node tools/vitrin-siralama-test.js --build tools/mutant-build.py
 * Bayraklar YALNIZ hangi index.html / hangi build.py'nin OLCULDUGUNU degistirir
 * (varsayilan: gercek dosyalar); hicbir iddiayi gevsetmez.
 * (--build ile verilen kopya tools/ icinde durmali: build.py kardes modullerini ve
 * ROOT'u kendi konumundan turetiyor. build.py kurali HER ZAMAN gercek index.html'den
 * okur; --index yalnizca ISTEMCI kolunu mutasyonlar.)
 */

"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");
const { spawnSync } = require("node:child_process");

const KOK = path.dirname(__dirname);
function _bayrak(ad, varsayilan) {
  const i = process.argv.indexOf(ad);
  return i !== -1 && process.argv[i + 1] ? path.resolve(process.argv[i + 1]) : varsayilan;
}
const INDEX_YOL = _bayrak("--index", path.join(KOK, "index.html"));
const BUILD_YOL = _bayrak("--build", path.join(KOK, "tools", "build.py"));
const INDEX = fs.readFileSync(INDEX_YOL, "utf8");
const SECENEK_SRC = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");

const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));
const SCRIPT = inlineScriptBul(INDEX, "renderGrid");
if (!SCRIPT) {
  console.error("OLCULEMEDI: index.html inline scripti (imza 'renderGrid') bulunamadi — " +
    "sayfa yapisi degismis olabilir. Test OLCUM YAPAMAZ.");
  process.exit(2);
}

// 🔴 BAGIMSIZ CAPA — index.html'den okunmaz (yukaridaki gerekce).
const SLOT_DUZEN = [
  { kategori: "Jeneratör", adet: 4 },
  { kategori: "Marin", adet: 80 },
  { kategori: "Otomobil", adet: 80 },
];
const ON_TOPLAM = SLOT_DUZEN.reduce((t, b) => t + b.adet, 0);   // 164
// Eski kuralin (31 Tem sabahi) korudugu deger: bu uc kategori vitrinin BASINDA olmaz.
// Yeni kural onu YUTUYOR (ilk 164 slot zaten Jenerator/Marin/Otomobil) — ama deger
// KAYBOLMASIN diye AYRI iddiayla olculur.
const GERI_KATEGORILER = ["Ev", "Dekorasyon", "Ofis"];

const EDGE_UC = (INDEX.match(/var\s+EDGE_UC\s*=\s*"([^"]+)"/) || [])[1];
const PAGE_SIZE = Number((INDEX.match(/var\s+PAGE_SIZE\s*=\s*(\d+)/) || [])[1]);
if (!EDGE_UC || !PAGE_SIZE) {
  console.error("OLCULEMEDI: index.html'de EDGE_UC / PAGE_SIZE bulunamadi.");
  process.exit(2);
}
/** slot indeksi -> beklenen blok kategorisi (164+ = null, karisik) */
function slotKategorisi(i) {
  let alt = 0;
  for (const b of SLOT_DUZEN) {
    if (i < alt + b.adet) { return b.kategori; }
    alt += b.adet;
  }
  return null;
}
const geriMi = (k) => GERI_KATEGORILER.indexOf(k) !== -1;

// ------------------------------------------------------------------ minimal DOM taklidi
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

function sinifla(el, cls, sonuc) {
  sonuc = sonuc || [];
  if ((el.className || "").split(/\s+/).indexOf(cls) !== -1) { sonuc.push(el); }
  for (const c of el.children) { sinifla(c, cls, sonuc); }
  return sonuc;
}
function hrefBul(el, sonuc) {
  sonuc = sonuc || [];
  if (el.href) { sonuc.push(el.href); }
  for (const c of el.children) { hrefBul(c, sonuc); }
  return sonuc;
}
function belgeKur() {
  const kimlikler = new Map();
  const seciciler = new Map();
  return {
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
}
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

// --------------------------------------------------------------------------- fiksturler
/** urunler.json objesi -> ozet/Worker kart sekli (build.py kart_ozeti ile ayni alanlar). */
function kart(p) {
  return {
    id: p.id, baslik: p.baslik || "", kategori: p.kategori || "", marka: p.marka || [],
    fiyat: p.fiyat || "", gorsel: (p.gorseller || [null])[0],
    parametrik: !!p.parametrik, aciklama: (p.aciklama || "").slice(0, 160),
  };
}
let _no = 0;
function urun(kategori, ek) {
  const i = _no++;
  return Object.assign({
    id: "fx-" + i + "-" + kategori.toLocaleLowerCase("tr").replace(/[^a-z]/g, ""),
    kategori, marka: [], baslik: "Fikstur urun " + i + " " + kategori,
    aciklama: "Fikstur aciklama " + i, fiyat: "100 TL",
    gorseller: ["https://media.pruvo3d.com/urunler/fx-" + i + ".jpg"],
  }, ek || {});
}
function coklu(liste, kategori, adet, ek) {
  for (let n = 0; n < adet; n++) { liste.push(urun(kategori, ek)); }
  return liste;
}
const JEN = { parametrik: true, fiyat: "" };

/** FIKSTUR A — ANA fikstur: her blok TAM dolabilecek stok + ham katalogun BASI "kirli"
 *  (Ev/Dekorasyon/Ofis en yeni urunler; kural olmasaydi vitrinin basinda olurlardi). */
function fiksturA() {
  const l = [];
  coklu(l, "Ev", 20); coklu(l, "Dekorasyon", 15); coklu(l, "Ofis", 15);   // ham bas = kirli
  coklu(l, "Marin", 105);
  coklu(l, "Otomobil", 105);
  coklu(l, "Tamirat", 10); coklu(l, "Elektronik", 10); coklu(l, "Kamera", 5);
  coklu(l, "Jeneratör", 5, JEN);
  return l;
}

/** FIKSTUR B — YETERSIZ STOK: Marin blogu (80 slot) icin katalogda 20 urun var.
 *  Yuklu liste ON_TOPLAM'dan UZUN olmali ki "yanlis alarm" korumasi devreye girmesin.
 *
 *  ⚠️ BOYUT DUGMELERINDEN BAGIMSIZ OLMALI (9 Agu 2026, olculdu): edge modunda yuklu liste
 *  = ozet havuzlari + ozet.yeni, yani parametrik stogu + min(Marin stok, havuz) +
 *  min(Otomobil stok, havuz) + OZET_YENI. Jeneratör 4 iken bu toplam havuz=100'de 172,
 *  havuz=92'de TAM 164 (= ON_TOPLAM), havuz=90'da 162 oluyordu; yani fikstur havuz=100'e
 *  8 kalemlik payla civilenmisti ve ozet.json'u kuculten HER ayar (havuz DUSURME ya da
 *  OZET_YENI dusurme) bu testi "yetersiz=false" ile KIRMIZI yakiyordu — olculen sey
 *  yetersiz-stok alarmi degil, fiksturun tesadufen esigi asmasiydi.
 *  Parametrik stok TEK kapsiz kalemdir (havuz:0 = "tamami"), bu yuzden pay ORADAN verilir:
 *  40 ile toplam havuz=48'e kadar ON_TOPLAM'in ustunde kalir. Blok adedi 4 oldugu icin
 *  on bloga yine 4 Jeneratör girer (12a'nin ilk-4 iddiasi DEGISMEZ), kalani kuyruga gider. */
function fiksturB() {
  const l = [];
  coklu(l, "Tamirat", 60);          // ham bas -> ozet.yeni bunlardan
  coklu(l, "Marin", 20);            // 80 slot icin YETERSIZ
  coklu(l, "Otomobil", 200);
  coklu(l, "Jeneratör", 40, JEN);   // kapsiz havuz -> yuklu liste ON_TOPLAM'i AYARDAN BAGIMSIZ asar
  return l;
}

/** FIKSTUR C — bayrak-kapali (HOME_ORDER) yolu: tum katalog istemcide, blok stogu tam. */
function fiksturC() {
  const l = [];
  coklu(l, "Ev", 10); coklu(l, "Dekorasyon", 8); coklu(l, "Ofis", 8);
  coklu(l, "Marin", 90);
  coklu(l, "Otomobil", 90);
  coklu(l, "Bisiklet", 10); coklu(l, "Bahçe", 10);
  coklu(l, "Jeneratör", 6, JEN);
  return l;
}

/** FIKSTUR D — SAYFA DEVAMLILIGI: ozet havuzu katalogun TAMAMINI kapsamaz (Worker
 *  yuruyusu sart) ve blok kategorileri ham katalogun HER YERINE serpistirilmistir
 *  (Worker sayfalari ozet havuzuyla CAKISIR -> tekillestirme kaybi GERCEKTEN olusur;
 *  telafi olmazsa "her tiklamada +PAGE_SIZE" iddiasi KIRMIZI yanar). */
function fiksturD() {
  const l = [];
  const dolgu = ["Tamirat", "Elektronik", "Kamera", "Bahçe"];
  for (let i = 0; i < 120; i++) {
    if (i % 6 === 0) { l.push(urun("Marin")); }
    else if (i % 6 === 1) { l.push(urun("Otomobil")); }
    else if (i === 5 || i === 41 || i === 77 || i === 113) { l.push(urun("Jeneratör", JEN)); }
    else { l.push(urun(dolgu[i % dolgu.length])); }
  }
  return l;
}

// --------------------------------------------------- GERCEK build.py ile ozet uretimi
// Derleme ekseni GERCEK kodla olculur: kural JS'e KOPYALANMAZ (ikinci kopya, iki tarafin
// sessizce ayrismasi demekti). build.py --sadece-ozet --katalog/--cikti ile gecici
// dizine yazar; depodaki ozet.json'a DOKUNULMAZ.
const GECICI = fs.mkdtempSync(path.join(os.tmpdir(), "pruvo-vitrin-"));
let _ozetNo = 0;

/** urunler dizisi (ya da hazir bir katalog dosyasi yolu) -> { ozet, cikti, bayt } */
function ozetBuild(kaynak) {
  const no = ++_ozetNo;
  let katalogYol = kaynak;
  if (Array.isArray(kaynak)) {
    katalogYol = path.join(GECICI, "katalog-" + no + ".json");
    fs.writeFileSync(katalogYol, JSON.stringify(kaynak), "utf8");
  }
  const ciktiYol = path.join(GECICI, "ozet-" + no + ".json");
  const r = spawnSync("python3",
    [BUILD_YOL, "--sadece-ozet", "--katalog", katalogYol, "--cikti", ciktiYol],
    { encoding: "utf8" });
  if (r.error) {
    throw new Error("OLCULEMEDI: build.py calistirilamadi: " + r.error.message);
  }
  if (r.status !== 0) {
    throw new Error("OLCULEMEDI: build.py --sadece-ozet exit " + r.status + " -> " +
      String(r.stderr || "").slice(-400));
  }
  if (!fs.existsSync(ciktiYol)) {
    throw new Error("OLCULEMEDI: build.py ozet yazmadi -> " + ciktiYol);
  }
  return { ozet: JSON.parse(fs.readFileSync(ciktiYol, "utf8")),
    cikti: String(r.stdout || ""), bayt: fs.statSync(ciktiYol).size };
}

/** index.html'in edgeHavuz() ile AYNI havuzu (kart dizisi) — beklenen degeri hesaplamak
 *  icin. Sira BURADA onemli degil (id kumesi ve blok uyeligi olculur). */
function havuzKartlari(ozet) {
  const out = [];
  for (const b of SLOT_DUZEN) {
    const h = (b.kategori === "Jeneratör")
      ? (ozet.parametrik || []) : ((ozet.bloklar || {})[b.kategori] || []);
    out.push.apply(out, h);
  }
  out.push.apply(out, ozet.yeni || []);
  const gorulen = new Set(), tekil = [];
  for (const k of out) { if (!gorulen.has(k.id)) { gorulen.add(k.id); tekil.push(k); } }
  return tekil;
}

// -------------------------------------------------------------------- sahte edge ucu
function cevap(veri, kod) {
  kod = kod || 200;
  return { ok: kod >= 200 && kod < 300, status: kod,
    json: () => Promise.resolve(JSON.parse(JSON.stringify(veri))) };
}
function ucKatalog(urunler, p) {
  const ids = p.get("ids");
  if (ids) {
    const kume = new Set(ids.split(","));
    return { urunler: urunler.filter((u) => kume.has(u.id)).map(kart) };
  }
  const kat = p.get("kategori");
  const sayfa = Math.max(1, Number(p.get("sayfa") || 1));
  const boy = Math.max(1, Number(p.get("boy") || PAGE_SIZE));
  let liste = urunler;
  if (kat) { liste = liste.filter((u) => u.kategori === kat); }
  return { toplam: liste.length,
    urunler: liste.slice((sayfa - 1) * boy, sayfa * boy).map(kart) };
}
function ucAra(urunler, p) {
  const q = (p.get("q") || "").toLocaleLowerCase("tr");
  const limit = Math.max(1, Number(p.get("limit") || PAGE_SIZE));
  const liste = urunler.filter((u) => (u.baslik || "").toLocaleLowerCase("tr").indexOf(q) !== -1);
  return { toplam: liste.length, urunler: liste.slice(0, limit).map(kart) };
}

/**
 * index.html scriptini fikstur veriyle calistirir.
 *   ayar.urunler    fikstur katalogu (ozet GERCEK build.py ile uretilir)
 *   ayar.ozet       hazir ozet.json icerigi (verilirse build cagrilmaz)
 *   ayar.seed       VITRIN_SEED'i sabitle (deterministik olcum)
 *   ayar.search     location.search
 *   ayar.ozetDusur  true ise ozet.json 404 doner (Worker beslemeli yol)
 *   ayar.ucDusur    true ise /katalog + /ara 500 doner (edgeYedek yolu)
 *   ayar.bayrak     "kapali" ise EDGE_KATALOG=false kolunu kosar
 *   ayar.kuralsiz   true ise siralayici cagrilari BELLEKTEKI KOPYADA devre disi (karsi-olcum)
 */
async function sayfaKur(ayar) {
  const urunler = ayar.urunler || [];
  const OZET = ayar.ozet || ozetBuild(urunler).ozet;
  const belge = belgeKur();
  const hatalar = [], uyarilar = [], istekler = [];
  const durum = { ucDusur: !!ayar.ucDusur };
  let kaynak = SCRIPT;
  if (ayar.bayrak === "kapali") {
    const yeni = kaynak.replace(/var\s+EDGE_KATALOG\s*=\s*true\s*;/, "var EDGE_KATALOG = false;");
    if (yeni === kaynak) {
      throw new Error("OLCULEMEDI: EDGE_KATALOG bayragi kaynakta bulunamadi " +
        "(bayrak-kapali yolu kosulamadi)");
    }
    kaynak = yeni;
  }
  // KARSI-OLCUM ("kuralsiz"): siralayici cagrilari BELLEKTEKI KOPYADA devre disi birakilir —
  // fiksturun BOS OLMADIGINI kanitlamak icin. Canli dosyaya DOKUNULMAZ. Capalar
  // bulunamazsa OLCULEMEDI (fail-closed).
  if (ayar.kuralsiz) {
    const capalar = [
      ["cizilecek = vitrinSirala(edgeListe, VITRIN_SEED).slice(0, edgeGoster);",
        "cizilecek = edgeListe.slice(0, edgeGoster);"],
      ["if(anaGorunum){ list = vitrinSirala(list, VITRIN_SEED); }",
        "if(false){ list = vitrinSirala(list, VITRIN_SEED); }"],
    ];
    for (const [eski, yeni] of capalar) {
      if (kaynak.indexOf(eski) === -1) {
        throw new Error("OLCULEMEDI: siralayici cagri capasi bulunamadi -> " + eski);
      }
      kaynak = kaynak.replace(eski, yeni);
    }
  }
  const ctx = {
    document: belge,
    location: { hash: "", search: ayar.search || "", pathname: "/", href: "", replace() {} },
    history: { replaceState() {} },
    localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    fetch(url) {
      const ham = String(url);
      istekler.push(ham);
      if (ham.indexOf("ozet.json") === 0) {
        return Promise.resolve(ayar.ozetDusur ? cevap({}, 404) : cevap(OZET));
      }
      if (ham.indexOf("urunler.json") === 0) { return Promise.resolve(cevap(urunler)); }
      if (ham.indexOf(EDGE_UC) === 0) {
        if (durum.ucDusur) { return Promise.resolve(cevap({ hata: "sentetik ariza" }, 500)); }
        const u = new URL(ham);
        if (u.pathname === "/katalog") { return Promise.resolve(cevap(ucKatalog(urunler, u.searchParams))); }
        if (u.pathname === "/ara") { return Promise.resolve(cevap(ucAra(urunler, u.searchParams))); }
      }
      return Promise.resolve(cevap({ hata: "taklit edilmemis istek: " + ham }, 404));
    },
    console: {
      log() {},
      warn(...a) { uyarilar.push(a.map(String).join(" ")); },
      error(...a) { hatalar.push(a.map(String).join(" ")); },
    },
    alert() {}, navigator: {}, URLSearchParams, setTimeout, clearTimeout, Math,
    addEventListener() {}, removeEventListener() {},
    scrollTo() {}, scrollY: 0, innerHeight: 720,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SECENEK_SRC, ctx, { filename: "secenekler.js" });
  vm.runInContext(kaynak, ctx, { filename: "index-inline.js" });
  // SEED ENJEKSIYONU: script senkron kismi bitti, fetch .then'leri henuz KOSMADI
  // (mikrogorev kuyrugu bu is parcasinin sonunda bosalir) -> ilk boyama enjekte edilen
  // seed'le olur. Fail-closed: seed degiskeni yoksa olcum yapilmis SAYILMAZ.
  if (!ctx.PRUVO_VITRIN || typeof ctx.PRUVO_VITRIN.sirala !== "function" ||
      typeof ctx.PRUVO_VITRIN.seedKur !== "function") {
    throw new Error("OLCULEMEDI: window.PRUVO_VITRIN tani yuzeyi YOK — seed enjekte " +
      "edilemez, siralayici disaridan olculemez (index.html IIFE icinde).");
  }
  if (ayar.seed !== undefined) { ctx.PRUVO_VITRIN.seedKur(ayar.seed); }
  const BEKLENEN_HATA = [/ozet\.json yuklenemedi/, /katalog\/arama alinamadi/];
  function hatalariDenetle() {
    const beklenmeyen = hatalar.filter((h) => !BEKLENEN_HATA.some((r) => r.test(h)));
    if (beklenmeyen.length) {
      throw new Error("OLCULEMEDI: sayfa scripti BEKLENMEYEN hata basti: " +
        beklenmeyen.join(" | "));
    }
  }
  function oku() {
    hatalariDenetle();
    const grid = belge.getElementById("grid");
    const kartlar = grid.children.map((c) => ({
      kategori: (sinifla(c, "card-cat")[0] || {}).textContent || "",
      id: (hrefBul(c)[0] || "").replace(/^\/urun\/|\/$/g, ""),
    }));
    if (!kartlar.length) {
      throw new Error("OLCULEMEDI: gridde HIC kart yok (fikstur/besleme kurulamadi)");
    }
    const btn = belge.getElementById("loadMoreWrap").children[0];
    return {
      kartlar,
      sapma: ctx.PRUVO_VITRIN_SAPMA || null,
      seed: ctx.PRUVO_VITRIN.seedAl(),
      uyarilar: uyarilar.slice(),
      sayimMetni: belge.getElementById("resultCount").textContent,
      butonMetni: btn ? btn.textContent : "",
      dahaVar: !!btn,
      baslik: belge.getElementById("sectionTitle").textContent,
      istekler: istekler.slice(),
    };
  }

  for (let i = 0; i < 10; i++) { await bekle(15); }
  hatalariDenetle();

  const s = oku();
  s.oku = oku;
  s.ctx = ctx;
  s.ucDusur = (v) => { durum.ucDusur = !!v; };
  /** "Daha fazla goster" butonunu GERCEKTEN tiklar (loadMoreWrap'taki tek buton). */
  s.dahaFazla = async () => {
    const btn = belge.getElementById("loadMoreWrap").children[0];
    if (!btn || typeof btn.onclick !== "function") {
      throw new Error("OLCULEMEDI: 'Daha fazla goster' butonu YOK (dahaVar hesabi degismis?)");
    }
    btn.onclick();
    for (let i = 0; i < 12; i++) { await bekle(15); }
    return oku();
  };
  return s;
}

/** "Daha fazla goster"i enAz kart cizilene (ya da buton kaybolana) kadar tiklar. */
async function genislet(s, enAz, maxTik) {
  let son = s.oku();
  let tik = 0;
  const limit = maxTik || 40;
  while (son.kartlar.length < enAz && son.dahaVar && tik < limit) {
    son = await s.dahaFazla();
    tik++;
  }
  son.tik = tik;
  return son;
}

// ------------------------------------------------------- IDDIA DENETCILERI (saf fonksiyon)
// Her denetci hem GERCEK ciktiya (POZITIF vaka) hem SENTETIK BOZUK ciktiya (NEGATIF vaka)
// uygulanir. Negatif vakada hata URETMEYEN denetci OLU IDDIA sayilir -> test KIRMIZI.

/** A: BLOK UYELIGI — slot 0-3 Jenerator, 4-83 Marin, 84-163 Otomobil (stok yeterken). */
function denetA(kartlar) {
  const h = [];
  const bakilan = Math.min(kartlar.length, ON_TOPLAM);
  for (let i = 0; i < bakilan; i++) {
    const bek = slotKategorisi(i);
    if (bek && kartlar[i].kategori !== bek) {
      h.push("slot " + i + " = " + kartlar[i].kategori + " (beklenen " + bek + ")");
      if (h.length >= 4) { break; }
    }
  }
  if (bakilan < ON_TOPLAM) {
    h.push("yalniz " + bakilan + " kart cizildi (" + ON_TOPLAM + " slot olculemedi)");
  }
  return h;
}
/** H: ilk ON_TOPLAM slotta Ev/Dekorasyon/Ofis YOK (eski kuralin korudugu deger). */
function denetH(kartlar) {
  const h = [];
  kartlar.slice(0, ON_TOPLAM).forEach((k, i) => {
    if (geriMi(k.kategori)) { h.push("slot " + i + " = " + k.kategori); }
  });
  return h.slice(0, 4);
}
/** C: cizim ham listenin PERMUTASYONU (kart sayisi + id kumesi ayni). */
function denetC(kartlar, hamIdler) {
  const h = [];
  if (kartlar.length !== hamIdler.length) {
    h.push("kart sayisi " + kartlar.length + " (ham " + hamIdler.length + ")");
  }
  const a = kartlar.map((k) => k.id).slice().sort().join("|");
  const b = hamIdler.slice().sort().join("|");
  if (a !== b) { h.push("id kumesi ham listeden FARKLI (eleme/ekleme var)"); }
  const idler = kartlar.map((k) => k.id);
  if (new Set(idler).size !== idler.length) { h.push("MUKERRER kart var"); }
  return h;
}
/** D: verilen cizim, beklenen sirayla BIREBIR ayni (kategori/arama gorunumu degismedi). */
function denetD(kartlar, beklenenIdler) {
  const a = kartlar.map((k) => k.id).join("|");
  const b = beklenenIdler.join("|");
  return a === b ? [] : ["sira/kume degismis: " + a.slice(0, 120) + " != " + b.slice(0, 120)];
}
/** E: yetersiz stok hali OLCULUP BASILMIS olmali. */
function denetE(sapma, uyarilar, beklenenYetersiz) {
  const h = [];
  if (!sapma) { return ["sapma olcumu YOK (window.PRUVO_VITRIN_SAPMA tanimlanmamis)"]; }
  if (!!sapma.yetersiz !== beklenenYetersiz) {
    h.push("sapma.yetersiz=" + sapma.yetersiz + " (beklenen " + beklenenYetersiz + ")");
  }
  if (beklenenYetersiz && !uyarilar.some((u) => u.indexOf("vitrin-sapma") !== -1)) {
    h.push("yetersiz stok SESSIZ gecti (konsola vitrin-sapma yazilmadi)");
  }
  if (!beklenenYetersiz && uyarilar.some((u) => u.indexOf("vitrin-sapma") !== -1)) {
    h.push("yanlis alarm: sapma yokken vitrin-sapma basildi");
  }
  return h;
}
/** P: iki sira BIREBIR ayni mi (seed determinizmi icin). */
function denetP(a, b) {
  return a.join("|") === b.join("|") ? []
    : ["ayni seed FARKLI sira uretti (deterministik degil)"];
}
/** R: iki sira FARKLI mi (rastgelelik CANLI mi). */
function denetR(a, b) {
  return a.join("|") !== b.join("|") ? []
    : ["farkli seed AYNI sirayi uretti — rastgelelik OLU"];
}

// ------------------------------------------------------------------------------ raporlama
let gecen = 0, kalan = 0;
function rapor(ad, hatalar, detay) {
  const ok = hatalar.length === 0;
  ok ? gecen++ : kalan++;
  console.log((ok ? "  ✅ GECTI " : "  ❌ KALDI ") + ad +
    (ok ? (detay ? " — " + detay : "")
        : " — " + hatalar.slice(0, 4).join(" ; ")));
}
/** NEGATIF vaka: denetci bozuk girdide hata URETMELI; uretmezse iddia OLU. */
function negatif(ad, hatalar) {
  const ok = hatalar.length > 0;
  ok ? gecen++ : kalan++;
  console.log((ok ? "  ✅ GECTI " : "  ❌ KALDI ") + "[NEGATIF] " + ad +
    (ok ? " — bozuk girdi YAKALANDI" : " — OLU IDDIA: bozuk girdi yakalanmadi"));
}

// ---------------------------------------------------------------------------------- testler
async function main() {
  console.log("PRUVO ana sayfa vitrin hiyerarsisi kabulu — slot duzeni " +
    SLOT_DUZEN.map((b) => b.adet + " " + b.kategori).join(" · ") + " · gerisi karisik");
  console.log("olculen index.html: " + INDEX_YOL);
  console.log("olculen build.py  : " + BUILD_YOL + "\n");

  // ---- 0: TEK KAYNAK + sabitler
  {
    const h = [];
    const bildirim = INDEX.match(/var\s+VITRIN_BLOKLAR\s*=\s*(\[[\s\S]*?\])\s*;/g) || [];
    if (bildirim.length !== 1) {
      h.push("VITRIN_BLOKLAR bildirimi " + bildirim.length + " kez (TEK olmali)");
    } else {
      let bloklar = null;
      try {
        bloklar = JSON.parse(bildirim[0].replace(/^[^[]*/, "").replace(/\s*;\s*$/, ""));
      } catch (e) { h.push("VITRIN_BLOKLAR okunamadi: " + e.message); }
      if (bloklar) {
        const ozet = bloklar.map((b) => b.kategori + ":" + b.adet).join("|");
        const bek = SLOT_DUZEN.map((b) => b.kategori + ":" + b.adet).join("|");
        if (ozet !== bek) { h.push("blok duzeni '" + ozet + "' != capa '" + bek + "'"); }
        const kats = JSON.parse((INDEX.match(/var\s+CATEGORIES\s*=\s*(\[[^\]]*\])\s*;/) || [])[1]);
        const gizli = JSON.parse((INDEX.match(/var\s+GIZLI_KATEGORILER\s*=\s*(\[[^\]]*\])\s*;/) || [])[1]);
        for (const b of bloklar) {
          if (kats.indexOf(b.kategori) === -1 && gizli.indexOf(b.kategori) === -1) {
            h.push("'" + b.kategori + "' ne CATEGORIES ne GIZLI_KATEGORILER'de");
          }
          if (b.kaynak !== "parametrik" && !(b.havuz > b.adet)) {
            h.push(b.kategori + " havuzu (" + b.havuz + ") adetten (" + b.adet +
              ") buyuk DEGIL — yenilemede hep ayni urunler gelir");
          }
        }
      }
    }
    // Eski kural kalintisi kalmadi (yeni kural onu yuttu; iki kural yan yana durmasin)
    if (/var\s+VITRIN_ON_SLOT\s*=/.test(INDEX)) { h.push("eski VITRIN_ON_SLOT hala tanimli"); }
    if (/var\s+VITRIN_GERI_KATEGORILER\s*=/.test(INDEX)) {
      h.push("eski VITRIN_GERI_KATEGORILER hala tanimli");
    }
    rapor("0 tek kaynak: VITRIN_BLOKLAR tek bildirim, capayla birebir, kategoriler tanimli",
      h, "on blok " + ON_TOPLAM + " slot");
  }

  const A = fiksturA();
  const ozetA = ozetBuild(A).ozet;
  const havuzA = havuzKartlari(ozetA);

  // ---- 1: ozet.json yolu (ziyaretcinin GORDUGU ana yol)
  const s1 = await sayfaKur({ urunler: A, ozet: ozetA, seed: 20260731 });
  const g1 = await genislet(s1, ON_TOPLAM);
  rapor("1a ozet.json yolu: BLOK UYELIGI (slot 0-3 Jeneratör · 4-83 Marin · 84-163 Otomobil)",
    denetA(g1.kartlar), g1.kartlar.length + " kart / " + g1.tik + " tiklama");
  rapor("1b ozet.json yolu: ilk " + ON_TOPLAM + " slotta Ev/Dekorasyon/Ofis YOK",
    denetH(g1.kartlar), "eski kuralin korudugu deger");
  {
    const h = [];
    const beklenen = String(A.length) + " ürün";
    if (s1.sayimMetni !== beklenen) {
      h.push("resultCount '" + s1.sayimMetni + "' (beklenen '" + beklenen + "')");
    }
    rapor("1c katalog toplami DEGISMEDI (resultCount)", h, s1.sayimMetni);
  }
  {
    // PERMUTASYON saf fonksiyon uzerinde: vitrinSirala havuzu ELEMEZ / UYDURMAZ / TEKRARLAMAZ.
    const cikti = s1.ctx.PRUVO_VITRIN.sirala(havuzA, 12345);
    rapor("1d vitrinSirala PERMUTASYON: eleme/uydurma/mukerrer YOK",
      denetC(cikti, havuzA.map((k) => k.id)), havuzA.length + " kart havuz");
  }
  {
    // FIKSTUR BOS DEGIL: kural devre disi birakilinca ilk 164 slot blok duzenine UYMAZ.
    const kuralsiz = await sayfaKur({ urunler: A, ozet: ozetA, kuralsiz: true, seed: 7 });
    const gk = await genislet(kuralsiz, ON_TOPLAM);
    const bozuk = denetA(gk.kartlar).length;
    rapor("1e fikstur bos degil: KURALSIZ cizimde blok duzeni BOZUK",
      bozuk === 0 ? ["FIKSTUR BOS: kuralsiz cizim de blok duzenine uyuyor — iddia vacuous"] : [],
      bozuk + " sapma");
  }

  // ---- 2: NEGATIF vakalar — denetciler bozuk ciktida KIRMIZI yanmali
  {
    negatif("A denetcisi: blok duzeni TERS cevrilmis cizim",
      denetA(g1.kartlar.slice().reverse()));
    negatif("A denetcisi: tek slot kaymis cizim (Marin 80->79 mutantinin izi)",
      denetA(g1.kartlar.slice(0, 3).concat(g1.kartlar.slice(4))));
    negatif("H denetcisi: ilk 164'e Ev sizmis cizim",
      denetH([{ kategori: "Ev", id: "x" }].concat(g1.kartlar)));
    negatif("C denetcisi: kart sayisi degismis cikti",
      denetC(g1.kartlar.slice(1), g1.kartlar.map((k) => k.id)));
    negatif("C denetcisi: MUKERRER kart",
      denetC(g1.kartlar.concat([g1.kartlar[0]]), g1.kartlar.map((k) => k.id).concat([g1.kartlar[0].id])));
    negatif("D denetcisi: sirasi bozulmus kategori gorunumu",
      denetD(g1.kartlar.slice().reverse(), g1.kartlar.map((k) => k.id)));
    negatif("E denetcisi: yetersiz stok olcumu YOKKEN", denetE(null, [], false));
    negatif("E denetcisi: yetersiz stok SESSIZ gecmis", denetE({ yetersiz: true }, [], true));
    negatif("P denetcisi: farkli iki sira 'ayni' sayilmasin", denetP(["a", "b"], ["b", "a"]));
    negatif("R denetcisi: ayni iki sira 'farkli' sayilmasin", denetR(["a", "b"], ["a", "b"]));
  }

  // ---- 3: SEED DETERMINIZMI — ayni seed AYNI sira (idempotent olcum)
  {
    const c1 = s1.ctx.PRUVO_VITRIN.sirala(havuzA, 424242).map((k) => k.id);
    const c2 = s1.ctx.PRUVO_VITRIN.sirala(havuzA, 424242).map((k) => k.id);
    rapor("3a seed determinizmi: ayni seed -> ayni sira", denetP(c1, c2), c1.length + " kart");
    // DOM uzerinde de: ayni seed'le iki AYRI sayfa yuklemesi ayni vitrini vermeli
    const a = await sayfaKur({ urunler: A, ozet: ozetA, seed: 99 });
    const b = await sayfaKur({ urunler: A, ozet: ozetA, seed: 99 });
    rapor("3b seed determinizmi (DOM): ayni seed'li iki yukleme ayni vitrin",
      denetP(a.kartlar.map((k) => k.id), b.kartlar.map((k) => k.id)),
      a.kartlar.length + " kart");
  }

  // ---- 4: RASTGELELIK CANLI — farkli seed FARKLI sira (bu eksen olmadan "hepsini sabit
  //         birak" mutasyonu YESIL gecerdi)
  {
    const c1 = s1.ctx.PRUVO_VITRIN.sirala(havuzA, 1).map((k) => k.id);
    const c2 = s1.ctx.PRUVO_VITRIN.sirala(havuzA, 2).map((k) => k.id);
    rapor("4a rastgelelik CANLI: farkli seed -> farkli sira", denetR(c1, c2));
    // Blok ICI karisiyor mu (yalniz kuyruk karisip on blok sabit kalmasin)
    const on1 = c1.slice(0, ON_TOPLAM).join("|");
    const on2 = c2.slice(0, ON_TOPLAM).join("|");
    rapor("4b rastgelelik BLOK ICINDE: on blok da seed'e gore degisiyor",
      on1 !== on2 ? [] : ["on blok (ilk " + ON_TOPLAM + " slot) iki seed'de AYNI — blok ici karisim OLU"]);
    // Seed ENJEKTE EDILEBILIR: seed verilmezse VITRIN_SEED kullanilir ve o da degisir
    const x = await sayfaKur({ urunler: A, ozet: ozetA });
    const y = await sayfaKur({ urunler: A, ozet: ozetA });
    rapor("4c seed sayfa yuklemesi basina URETILIYOR (iki yukleme farkli vitrin)",
      denetR(x.kartlar.map((k) => k.id), y.kartlar.map((k) => k.id)),
      "seed " + x.seed + " vs " + y.seed);
  }

  // ---- 5: SEED SABITLIGI — sayfalama boyunca seed DEGISMEZ, cizili sira YENIDEN DIZILMEZ
  {
    const s = await sayfaKur({ urunler: A, ozet: ozetA, seed: 555 });
    const ilk = s.kartlar.map((k) => k.id);
    const seedIlk = s.seed;
    const h = [];
    let son = s.oku();
    for (let t = 0; t < 5 && son.dahaVar; t++) {
      son = await s.dahaFazla();
      const yeni = son.kartlar.map((k) => k.id);
      if (yeni.slice(0, ilk.length).join("|") !== ilk.join("|")) {
        h.push("tik " + (t + 1) + ": ekranda duran ilk " + ilk.length +
          " kart YENIDEN DIZILDI (seed sayfalama boyunca sabit degil)");
        break;
      }
    }
    if (son.seed !== seedIlk) { h.push("VITRIN_SEED degisti: " + seedIlk + " -> " + son.seed); }
    rapor("5 seed sabitligi: sayfalama boyunca sira ONEKI korunuyor + seed degismiyor", h,
      son.kartlar.length + " karta kadar genisletildi");
  }

  // ---- 6: SAYFA DEVAMLILIGI (mevcut hatanin onarimi)
  {
    const D = fiksturD();
    const s = await sayfaKur({ urunler: D, seed: 31 });
    const h = [];
    // (i) Worker yuruyusu sayfa 1'den baslar — hicbir sayfa ATLANMAZ
    let son = s.oku();
    const cizim = [son.kartlar.length];
    let tik = 0;
    while (son.dahaVar && tik < 40) {
      const oncekiSayi = son.kartlar.length;
      son = await s.dahaFazla();
      tik++;
      cizim.push(son.kartlar.length);
      // (ii) her tiklama tam bir SAYFA kadar buyutmeli (tekillestirme kaybi TELAFI edilir)
      const beklenen = Math.min(oncekiSayi + PAGE_SIZE, D.length);
      if (son.kartlar.length !== beklenen) {
        h.push("tik " + tik + ": " + oncekiSayi + " -> " + son.kartlar.length +
          " (beklenen " + beklenen + ") — tekillestirme kaybi TELAFI EDILMEDI");
        break;
      }
    }
    const katalogSayfa1 = (son.istekler || []).filter((u) => u.indexOf(EDGE_UC + "/katalog") === 0);
    if (katalogSayfa1.length === 0) {
      h.push("Worker'a HIC gidilmedi — fikstur ozet havuzuyla tukenmis (iddia vacuous)");
    } else {
      const ilkSayfa = new URL(katalogSayfa1[0]).searchParams.get("sayfa");
      if (ilkSayfa !== "1") {
        h.push("Worker yuruyusu sayfa " + ilkSayfa + "'den basladi (beklenen 1) — " +
          "sayfa 1'deki urunler zincirde HIC gosterilmez");
      }
    }
    // (iii) zincir sonunda HICBIR urun atlanmamis, mukerrer yok
    h.push.apply(h, denetC(son.kartlar, D.map((u) => u.id)));
    // (iv) sayac GERCEK kalanla eslesiyor
    if (son.dahaVar) { h.push("zincir " + tik + " tiklamada bitmedi (buton hala var)"); }
    if (son.sayimMetni !== String(D.length) + " ürün") {
      h.push("resultCount '" + son.sayimMetni + "'");
    }
    rapor("6a sayfa devamliligi: zincirde HICBIR urun atlanmiyor + Worker sayfa 1'den basliyor",
      h, son.kartlar.length + "/" + D.length + " kart, " + tik + " tiklama, cizim " +
      cizim.slice(0, 6).join("->") + "...");

    // 6b — buton sayaci GERCEK kalani gosteriyor (ara adimda olculur)
    {
      const s2 = await sayfaKur({ urunler: D, seed: 31 });
      const ilk = s2.oku();
      const h2 = [];
      const kalanSayi = D.length - ilk.kartlar.length;
      if (ilk.butonMetni.indexOf(String(kalanSayi) + " ürün daha") === -1) {
        h2.push("buton '" + ilk.butonMetni + "' (beklenen " + kalanSayi + " ürün daha)");
      }
      const ikinci = await s2.dahaFazla();
      const kalan2 = D.length - ikinci.kartlar.length;
      if (ikinci.dahaVar && ikinci.butonMetni.indexOf(String(kalan2) + " ürün daha") === -1) {
        h2.push("2. tik butonu '" + ikinci.butonMetni + "' (beklenen " + kalan2 + " ürün daha)");
      }
      rapor("6b 'N ürün daha' sayaci GERCEK kalanla esit", h2, ilk.butonMetni);
    }
  }

  // ---- 7: Worker beslemeli yol (ozet.json inmedi) — kural BURADA da gecerli.
  // ⚠️ SINIR (bilincli): ozet.json inmezse blok HAVUZU YOKTUR; kartlar Worker'dan ham
  // sirayla sayfa sayfa gelir. Blok ancak stogu YUKLENDIKCE dolar (eksik blok kisalir —
  // kuralin kendisi). O yuzden bu yolda iddia "TUM katalog yuklendikten sonra blok duzeni
  // dogru" seklinde olculur; ilk sayfalarda vitrinin eksik olmasi KURALA UYGUNDUR.
  {
    const s = await sayfaKur({ urunler: A, ozet: ozetA, ozetDusur: true, seed: 77 });
    const g = await genislet(s, A.length, 60);
    const h = denetA(g.kartlar);
    if (g.kartlar.length < A.length) {
      h.push("katalog tam yuklenmedi: " + g.kartlar.length + "/" + A.length);
    }
    const katalogIstek = (g.istekler || []).filter((u) => u.indexOf(EDGE_UC + "/katalog") === 0);
    if (!katalogIstek.length) { h.push("Worker'a HIC gidilmedi (iddia vacuous)"); }
    rapor("7 Worker /katalog yolu (ozet 404): katalog yuklendikce blok duzeni GECERLI", h,
      g.kartlar.length + " kart / " + g.tik + " tiklama / " + katalogIstek.length + " /katalog istegi");
  }

  // ---- 8: edgeYedek yolu (ozet.json indi, sonra Worker dustu)
  {
    const s = await sayfaKur({ urunler: A, ozet: ozetA, seed: 88 });
    s.ucDusur(true);
    let son = await s.dahaFazla();
    for (let t = 0; t < 8 && son.kartlar.length < ON_TOPLAM && son.dahaVar; t++) {
      son = await s.dahaFazla();
    }
    rapor("8 edgeYedek yolu (Worker 500): blok duzeni GECERLI", denetA(son.kartlar),
      son.kartlar.length + " kart (yedek havuz)");
  }

  // ---- 9: EDGE_KATALOG=false yolu (bayrak geri alinirsa)
  {
    const C = fiksturC();
    const s = await sayfaKur({ urunler: C, bayrak: "kapali", seed: 909 });
    const g = await genislet(s, ON_TOPLAM);
    const h = denetA(g.kartlar);
    h.push.apply(h, denetH(g.kartlar));
    rapor("9a bayrak-kapali (HOME_ORDER) yolu: blok duzeni + ilk 164'te Ev/Dek/Ofis yok", h,
      g.kartlar.length + " kart / " + g.tik + " tiklama");

    const kuralsiz = await sayfaKur({ urunler: C, bayrak: "kapali", kuralsiz: true, seed: 909 });
    const gk = await genislet(kuralsiz, ON_TOPLAM);
    const bozuk = denetA(gk.kartlar).length;
    rapor("9b fikstur bos degil: kuralsiz HOME_ORDER blok duzenine UYMUYOR",
      bozuk === 0 ? ["FIKSTUR BOS: kuralsiz cizim de uyuyor — iddia vacuous"] : [],
      bozuk + " sapma");
  }

  // ---- 10: KATEGORI GORUNUMU DEGISMEDI (?kategori=Ev)
  {
    const beklenen = A.filter((u) => u.kategori === "Ev").slice(0, PAGE_SIZE).map((u) => u.id);
    const s = await sayfaKur({ urunler: A, ozet: ozetA, search: "?kategori=Ev", seed: 4 });
    const h = denetD(s.kartlar, beklenen);
    if (s.baslik !== "Ev Ürünleri") { h.push("baslik '" + s.baslik + "'"); }
    if (s.kartlar.some((k) => k.kategori !== "Ev")) { h.push("Ev disi urun sizdi"); }
    if (beklenen.length === 0) { h.push("fikstur bos: Ev urunu yok"); }
    rapor("10a kategori gorunumu (?kategori=Ev) ETKILENMEDI (rastgelelik UYGULANMAZ)", h,
      s.kartlar.length + " Ev karti");
    // Karsi-olcum: farkli seed'le AYNI sira gelmeli (kategori gorunumu seed'e duyarsiz)
    const s2 = await sayfaKur({ urunler: A, ozet: ozetA, search: "?kategori=Ev", seed: 999999 });
    rapor("10b kategori gorunumu SEED'E DUYARSIZ",
      denetP(s.kartlar.map((k) => k.id), s2.kartlar.map((k) => k.id)));
  }

  // ---- 11: ARAMA SONUCLARI DEGISMEDI
  {
    const q = "Fikstur urun 4";
    const bek = A.filter((u) => (u.baslik || "").toLocaleLowerCase("tr")
      .indexOf(q.toLocaleLowerCase("tr")) !== -1).slice(0, PAGE_SIZE).map((u) => u.id);
    const s = await sayfaKur({ urunler: A, ozet: ozetA, search: "?ara=" + encodeURIComponent(q), seed: 5 });
    const h = denetD(s.kartlar, bek);
    if (bek.length === 0) { h.push("fikstur bos: arama hic sonuc dondurmuyor"); }
    rapor("11a arama gorunumu ETKILENMEDI (rastgelelik UYGULANMAZ)", h, s.kartlar.length + " sonuc");
    const s2 = await sayfaKur({ urunler: A, ozet: ozetA, search: "?ara=" + encodeURIComponent(q), seed: 888888 });
    rapor("11b arama gorunumu SEED'E DUYARSIZ",
      denetP(s.kartlar.map((k) => k.id), s2.kartlar.map((k) => k.id)));
  }

  // ---- 12: YETERSIZ STOK — bosluk YOK, sapma OLCULUP BASILDI, yanlis alarm YOK
  {
    const B = fiksturB();
    const s = await sayfaKur({ urunler: B, seed: 12 });
    const h = denetE(s.sapma, s.uyarilar, true);
    if (s.kartlar.length !== PAGE_SIZE) {
      h.push("bosluk birakilmis: " + s.kartlar.length + " kart (beklenen " + PAGE_SIZE + ")");
    }
    const marin = (s.sapma && s.sapma.bloklar || []).filter((b) => b.kategori === "Marin")[0];
    if (!marin) { h.push("sapma.bloklar'da Marin kaydi yok"); }
    else if (marin.uygun !== 20) { h.push("Marin uygun=" + marin.uygun + " (beklenen 20)"); }
    // Blok kisaldi ama SONRAKI blok BOSLUK BIRAKMADAN devam etti (liste sikisti)
    const g = await genislet(s, ON_TOPLAM);
    const bosluk = g.kartlar.filter((k) => !k.id).length;
    if (bosluk) { h.push(bosluk + " bos/placeholder kart cizilmis"); }
    const ilk4 = g.kartlar.slice(0, 4).every((k) => k.kategori === "Jeneratör");
    const sonraki = g.kartlar.slice(4, 24).every((k) => k.kategori === "Marin");
    if (!ilk4 || !sonraki) {
      h.push("kisalan blokta duzen bozuldu (ilk4 Jeneratör=" + ilk4 + ", 4-23 Marin=" + sonraki + ")");
    }
    rapor("12a yetersiz stok: blok KISALDI, bosluk YOK, sapma OLCULDU ve BASILDI", h,
      s.sapma ? (s.sapma.bloklar || []).map((b) => b.kategori + " " + b.uygun + "/" + b.adet).join(", ") : "-");
    rapor("12b normal fiksturde YANLIS ALARM yok", denetE(s1.sapma, s1.uyarilar, false),
      s1.sapma ? "yetersiz=" + s1.sapma.yetersiz : "-");
  }

  // ---- 13: DERLEME EKSENI — build.py HAVUZ uretir, SIRALAMAZ
  {
    const b = ozetBuild(A);
    const h = [];
    // (a) havuz sekli + boyu index.html kuralindan geliyor (TEK KAYNAK paritesi)
    const kural = JSON.parse((INDEX.match(/var\s+VITRIN_BLOKLAR\s*=\s*(\[[\s\S]*?\])\s*;/) || [])[1]);
    for (const k of kural) {
      const stok = A.filter((u) => (u.kategori || "") === k.kategori).length;
      const bek = k.havuz ? Math.min(k.havuz, stok) : stok;
      const uretilen = (k.kaynak === "parametrik")
        ? (b.ozet.parametrik || []) : ((b.ozet.bloklar || {})[k.kategori] || []);
      if (uretilen.length !== bek) {
        h.push(k.kategori + " havuzu " + uretilen.length + " kart (beklenen " + bek + ")");
      }
      if (uretilen.some((c) => c.kategori !== k.kategori)) {
        h.push(k.kategori + " havuzuna baska kategori sizdi");
      }
    }
    // (b) ozet.vitrin capasi bagimsiz capa ile ayni (kural sessizce degistirilemesin)
    const sap = (b.ozet.vitrin && b.ozet.vitrin.bloklar) || [];
    const sapOzet = sap.map((x) => x.kategori + ":" + x.adet).join("|");
    const bekOzet = SLOT_DUZEN.map((x) => x.kategori + ":" + x.adet).join("|");
    if (sapOzet !== bekOzet) { h.push("ozet.vitrin '" + sapOzet + "' != capa '" + bekOzet + "'"); }
    rapor("13a build.py: blok havuzlari index.html kuralindan uretiliyor", h,
      Object.keys(b.ozet.bloklar || {}).map((k) => k + " " + b.ozet.bloklar[k].length).join(", ") +
      " | parametrik " + (b.ozet.parametrik || []).length + " | " + b.bayt + " bayt");

    // (c) build.py SIRALAMIYOR: ozet.yeni katalogun HAM basi (derlemede sira sabitlenirse
    //     "her yenilemede random" olur — bu iddia onu yakalar)
    rapor("13b build.py SIRALAMIYOR: ozet.yeni ham katalog basi",
      denetD(b.ozet.yeni || [], A.slice(0, (b.ozet.yeni || []).length).map((u) => u.id)),
      (b.ozet.yeni || []).length + " kayit");

    // (d) ETKISIZ-TEKRARLI: ayni katalog -> BAYT BAYT ayni ozet
    const b2 = ozetBuild(A);
    rapor("13c build.py ETKISIZ-TEKRARLI: ayni katalog ayni ozet",
      JSON.stringify(b.ozet) === JSON.stringify(b2.ozet) ? []
        : ["iki kosum FARKLI ozet uretti (derlemede rastgelelik var)"],
      b.bayt + " vs " + b2.bayt + " bayt");

    // (e) derleme tarafi yetersiz stogu SESSIZ GECMEZ
    const bb = ozetBuild(fiksturB());
    const h2 = [];
    if (!bb.ozet.vitrin || bb.ozet.vitrin.yetersiz !== true) {
      h2.push("ozet.vitrin.yetersiz=" + (bb.ozet.vitrin && bb.ozet.vitrin.yetersiz));
    }
    if (bb.cikti.indexOf("vitrin-sapma") === -1) {
      h2.push("yetersiz stok SESSIZ gecti (build gunlugune vitrin-sapma yazilmadi)");
    }
    if (b.cikti.indexOf("vitrin-sapma") !== -1) {
      h2.push("yanlis alarm: normal fiksturde build gunlugune vitrin-sapma basildi");
    }
    if (b.ozet.vitrin && b.ozet.vitrin.yetersiz !== false) {
      h2.push("yanlis alarm: ozet.vitrin.yetersiz=" + b.ozet.vitrin.yetersiz);
    }
    rapor("13d derleme yetersiz stok: ozet'e yazildi ve BASILDI + yanlis alarm yok", h2);
  }

  // ---- 14: CANLI KATALOG — UCTAN UCA (gercek urunler.json -> gercek build.py -> gercek
  // index.html). Veri durumuna DEGIL, ziyaretcinin gordugu SIRAYA bakar.
  {
    const h = [];
    const yol = path.join(KOK, "urunler.json");
    let bilgi = "";
    if (!fs.existsSync(yol)) {
      h.push("OLCULEMEDI: urunler.json yok");
    } else {
      const b = ozetBuild(yol);
      const urunler = JSON.parse(fs.readFileSync(yol, "utf8"));
      const s = await sayfaKur({ urunler, ozet: b.ozet, seed: 20260731 });
      const g = await genislet(s, ON_TOPLAM);
      h.push.apply(h, denetA(g.kartlar));
      h.push.apply(h, denetH(g.kartlar));
      if (b.ozet.vitrin && b.ozet.vitrin.yetersiz && b.cikti.indexOf("vitrin-sapma") === -1) {
        h.push("CANLI yetersiz stok SESSIZ gecti");
      }
      // rastgelelik CANLI veriyle de yasiyor mu
      const c1 = s.ctx.PRUVO_VITRIN.sirala(havuzKartlari(b.ozet), 1).map((k) => k.id);
      const c2 = s.ctx.PRUVO_VITRIN.sirala(havuzKartlari(b.ozet), 2).map((k) => k.id);
      h.push.apply(h, denetR(c1, c2));
      bilgi = g.kartlar.length + " kart / " + g.tik + " tiklama | katalog " + b.ozet.toplam +
        " | ozet " + b.bayt + " bayt | sapma.yetersiz=" +
        (b.ozet.vitrin ? b.ozet.vitrin.yetersiz : "?");
    }
    rapor("14 CANLI uctan uca: gercek katalogda blok duzeni + rastgelelik", h, bilgi);
  }

  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi");
  process.exit(kalan === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("OLCULEMEDI / ALTYAPI HATASI: " + ((e && e.stack) || e));
  process.exit(2);
});
