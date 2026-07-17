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
 *    parametrik urunler, banner bu gorunumde YOK.
 *  4 KART FIYATI: sari kartta "X TL'den başlayan" — X, jenerator/urunler/<id>.json
 *    tabanFiyatTL'sinden (TEK KAYNAK, elle kopya yok; bicim secenekler.js kurusMetni).
 *    Harita yuklenmemisse (build calismamis) eski "Ölçüye özel fiyat" fallback'i.
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

// index.html'in SON inline <script> blogu (vitrin/arama/sepet kodu).
const scriptBasi = INDEX.lastIndexOf("<script>");
const scriptSonu = INDEX.indexOf("</script>", scriptBasi);
const SCRIPT = INDEX.slice(scriptBasi + "<script>".length, scriptSonu);
if (!SCRIPT.includes("renderGrid")) {
  throw new Error("index.html inline scripti bulunamadi (yapi degisti mi?)");
}

// ---- TEK KAYNAK: jenerator/urunler/*.json semalarindan taban fiyat haritasi ----
const URUNLER = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
const PARAMETRIK = URUNLER.filter((u) => u.parametrik);
const SEMA_DIR = path.join(KOK, "jenerator", "urunler");
const TABAN = {};       // id -> tabanFiyatTL (null olanlar haritaya GIRMEZ — fallback yolu)
const TABANSIZ = [];    // yargi listesi: semasi olmayan ya da tabanFiyatTL null sari urunler
for (const u of PARAMETRIK) {
  const yol = path.join(SEMA_DIR, u.id + ".json");
  if (!fs.existsSync(yol)) { TABANSIZ.push(u.id + " (SEMA YOK)"); continue; }
  const sema = JSON.parse(fs.readFileSync(yol, "utf8"));
  if (sema.tabanFiyatTL == null) { TABANSIZ.push(u.id + " (tabanFiyatTL null)"); continue; }
  TABAN[u.id] = sema.tabanFiyatTL;
}
function beklenenKartMetni(id) {
  return (id in TABAN)
    ? SECENEK.kurusMetni(Math.round(TABAN[id] * 100)) + "'den başlayan"
    : "Ölçüye özel fiyat";
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

/**
 * index.html scriptini verilen URL/haritayla calistirir.
 *   ayar.search       location.search (or. "?kategori=Jeneratör")
 *   ayar.tabanHarita  window.PRUVO_TABAN_FIYATLAR (yoksa hic tanimlanmaz — 404 fallback'i)
 */
async function sayfaKur(ayar) {
  const { belge } = belgeKur();
  const konsolHatalari = [];
  const ctx = {
    document: belge,
    location: { hash: "", search: ayar.search || "", pathname: "/", href: "", replace() {} },
    history: { replaceState() {} },
    localStorage: {
      getItem: () => null, setItem: () => {}, removeItem: () => {},
    },
    fetch(url) {
      return Promise.resolve({
        json: () => Promise.resolve(JSON.parse(JSON.stringify(URUNLER))),
      });
    },
    console: { log() {}, error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
    alert() {},
    navigator: {},
    URLSearchParams,
    setTimeout, clearTimeout,
    Math,   // shuffle Math.random kullanir
  };
  ctx.window = ctx;
  if (ayar.tabanHarita) { ctx.PRUVO_TABAN_FIYATLAR = ayar.tabanHarita; }
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
  };
}

// Karttan (baslik, fiyat metni, parametrik-rozet) uclusu cikar.
function kartBilgi(card) {
  const baslik = sinifla(card, "card-title")[0];
  const fiyat = sinifla(card, "card-price")[0];
  const rozet = sinifla(card, "card-badge")[0];
  return {
    baslik: baslik ? baslik.textContent : "",
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
  for (const b of s.el("cats").children) { etiketler.push(b.textContent); }
  if (etiketler.indexOf("Jeneratör") !== -1) { hatalar.push("nav'da 'Jeneratör' GORUNUYOR"); }
  const beklenen = ["Tümü", "Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev",
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
  if (s.el("sectionTitle").textContent !== "Jeneratör Ürünleri") {
    hatalar.push("baslik '" + s.el("sectionTitle").textContent + "' (beklenen 'Jeneratör Ürünleri')");
  }
  const kartlar = s.kartlar();
  if (kartlar.length !== PARAMETRIK.length) {
    hatalar.push("gridde " + kartlar.length + " kart (beklenen " + PARAMETRIK.length + ")");
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
  const s = await sayfaKur({ search: "?kategori=Jenerat%C3%B6r", tabanHarita: TABAN });
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
  if (!href || decodeURIComponent(href[1]).indexOf("kategori=Jeneratör") === -1) {
    hatalar.push("banner linki ?kategori=Jeneratör'e gitmiyor: " + (href ? href[1] : "yok"));
  }
  if (INDEX.indexOf("PRUVO Jeneratör ile sana özel parça tasarla") === -1) {
    hatalar.push("banner metni (HTML overlay) yok");
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

/** 6 — VITRIN: ana sayfa ilk 4 kart sari (mevcut davranis KALIR) */
async function test6Vitrin() {
  const hatalar = [];
  const s = await sayfaKur({ tabanHarita: TABAN });
  const kartlar = s.kartlar();
  if (kartlar.length < 4) { hatalar.push("ana sayfada " + kartlar.length + " kart"); }
  for (let i = 0; i < Math.min(4, kartlar.length); i++) {
    const k = kartBilgi(kartlar[i]);
    if (!k.parametrik) { hatalar.push((i + 1) + ". kart sari degil: " + k.baslik); }
  }
  rapor("6 vitrin: ilk 4 kart sari", hatalar, "ilk 4 kart parametrik rozetli");
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
  } catch (e) {
    hatalar.push("uretim kosusu: " + (e && e.message || e));
  }
  rapor("7 uretim: taban-fiyatlar.js semalarla birebir", hatalar,
    Object.keys(TABAN).length + " id, degerler birebir");
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
