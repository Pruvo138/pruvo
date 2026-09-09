#!/usr/bin/env node
/**
 * KATEGORI PANEL BASLIGINDAKI URUN SAYISI — DAVRANIS KOSUMU (kabul testinin ICRA KOLU).
 *
 *   node tools/kat-sayisi-kosum.js --kok <agac> --indeks <json|YOK> [--index-html <yol>]
 *
 * BU DOSYA TEK BASINA BIR KAPI DEGILDIR: olctugunu JSON olarak stdout'a basar, HUKMU
 * tools/kat-sayisi-test.py verir (CI girisi odur). Adi bilerek "-test.js" DEGIL —
 * tools/ci-kapsam-test.py kesfi ikinci bir CI girisi beklemesin (emsal: cip-indeks-kosum.js).
 *
 * NASIL OLCER: index.html'in GERCEK inline scripti node:vm icinde, minimal DOM taklidiyle
 * CALISTIRILIR (kod KOPYALANMAZ). `renderKatPanelleri()` scriptin TEPE SEVIYESINDE, ag
 * beklemeden senkron cagrilir; bu yuzden panel DOM'u script govdesi biter bitmez hazirdir
 * ve sahte fetch'in bir sey DONDURMESI gerekmez.
 *
 * INDEKS UYDURULMAZ: `--indeks` ile verilen JSON, Python yargicinin GERCEK ureteci
 * (tools/cip-indeks.py) gercek katalog uzerinde kosturup yazdigi dosyadir. `--indeks YOK`
 * ise `window.PRUVO_CIP_INDEKS` HIC tanimlanmaz — yayin oncesi/indekssiz hal (fail-closed
 * kolunun tabani).
 *
 * 🔴 BASLIK METNI COCUKLARDAN TOPLANIR (`metinTum`): taklit DOM'da `textContent` DUZ bir
 * ozelliktir, gercek DOM gibi alt agaci TOPLAMAZ. Sayi AYRI bir <span>'e yaziliyor
 * (index.html: kat-panel-sayi), dolayisiyla yalniz `el.textContent` okunsaydi kosum sayiyi
 * HIC GORMEZ ve "sayi basilmadi" diye YANLIS YESIL/KIRMIZI verirdi.
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function arg(ad, varsayilan) {
  const i = process.argv.indexOf("--" + ad);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : varsayilan;
}
const KOK = path.resolve(arg("kok", path.dirname(__dirname)));
const INDEX_YOLU = arg("index-html", path.join(KOK, "index.html"));
const INDEKS_ARG = arg("indeks", "YOK");

const INDEX_METIN = fs.readFileSync(INDEX_YOLU, "utf8");
const SECENEK_SRC = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));

const SCRIPT = inlineScriptBul(INDEX_METIN, "renderKatPanelleri");
if (!SCRIPT) {
  throw new Error("index.html'de renderKatPanelleri iceren inline script bulunamadi");
}

// ---------------------------------------------------------------- DOM taklidi
function eleman(tag) {
  const el = {
    tagName: String(tag || "div").toUpperCase(),
    children: [], parentNode: null, style: {}, dataset: {}, attrs: {},
    className: "", textContent: "", disabled: false, checked: false, value: "", href: "",
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
  el._dinleyiciler = {};
  el.addEventListener = (t, fn) => { el._dinleyiciler[t] = fn; };
  el.focus = () => {};
  el.scrollIntoView = () => {};
  el.querySelector = () => null;
  el.querySelectorAll = () => [];
  return el;
}

/** Gercek DOM `textContent` semantigi: dugumun kendi metni + TUM alt agacin metni. */
function metinTum(el) {
  if (!el) { return ""; }
  return String(el.textContent || "") + (el.children || []).map(metinTum).join("");
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
    createDocumentFragment: () => eleman("fragment"),
    querySelector(sel) {
      if (!seciciler.has(sel)) { seciciler.set(sel, eleman("div")); }
      return seciciler.get(sel);
    },
    querySelectorAll: () => [],
    addEventListener() {},
    body: eleman("body"),
    documentElement: eleman("html"),
    execCommand: () => true,
    readyState: "complete",
    cookie: "",
    title: "",
  };
}

// ---------------------------------------------------------------- kosum
function kos() {
  const belge = belgeKur();
  const konum = { hash: "", search: "", pathname: "/", href: "https://pruvo3d.com/",
                  replace() {}, assign() {} };
  const depo = {};
  const konsolHatalari = [];
  const ctx = {
    document: belge,
    location: konum,
    history: { replaceState() {}, pushState() {} },
    localStorage: {
      getItem: (k) => (k in depo ? depo[k] : null),
      setItem: (k, v) => { depo[k] = String(v); },
      removeItem: (k) => { delete depo[k]; },
    },
    sessionStorage: {
      getItem: () => null, setItem() {}, removeItem() {},
    },
    // Ag ASLA cevap vermez: `renderKatPanelleri` ag beklemez, panel senkron cizilir.
    // Cozulmeyen soz, "sayi fetch'ten geliyor olmasin" tuzagini da KAPATIR — sayi
    // gercekten gomulu indeksten geliyorsa bu kosumda gorunur, ag'dan geliyorsa GORUNMEZ.
    fetch() { return new Promise(function () {}); },
    console: { log() {}, warn() {}, info() {}, debug() {},
               error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
    alert() {},
    navigator: { userAgent: "node", language: "tr" },
    screen: { width: 1280, height: 800 },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    URL, URLSearchParams, Intl, IntersectionObserver: function () {
      this.observe = function () {}; this.unobserve = function () {};
      this.disconnect = function () {};
    },
    setTimeout, clearTimeout, setInterval, clearInterval,
    requestAnimationFrame: (f) => setTimeout(f, 0),
    requestIdleCallback: (f) => setTimeout(f, 0),
    addEventListener() {}, removeEventListener() {},
    scrollTo() {}, scrollY: 0, innerWidth: 1280, innerHeight: 720,
    devicePixelRatio: 1,
    dataLayer: [],
    gtag() {},
  };
  ctx.window = ctx;
  ctx.self = ctx;
  ctx.globalThis = ctx;
  if (INDEKS_ARG !== "YOK") {
    ctx.PRUVO_CIP_INDEKS = JSON.parse(fs.readFileSync(INDEKS_ARG, "utf8"));
  }
  vm.createContext(ctx);
  vm.runInContext(SECENEK_SRC, ctx, { filename: "secenekler.js" });

  let hata = null;
  try {
    vm.runInContext(SCRIPT, ctx, { filename: "index-inline.js" });
  } catch (e) {
    hata = String((e && e.stack) || e);
  }

  // PANELLER: her `section.kat-panel`in ILK cocugu baslik <a>'sidir (index.html sirasi).
  const kutu = belge.getElementById("katPanels");
  const basliklar = (kutu.children || []).map((bolum) => {
    const bas = (bolum.children || [])[0] || null;
    // SINIF TAM ESITLIKLE aranir, alt-dize ile DEGIL: "kat-panel-sayi-x" gibi bir kayma
    // alt-dize suzgecinden GECER ve sayiyi CSS kancasindan kopardigi halde yesil kalirdi
    // (o sinif olmadan sayi 46px basliğin punto/harf araligiyla cizilir -> mobilde kirilir).
    const sayi = ((bas && bas.children) || [])
      .filter((c) => String(c.className) === "kat-panel-sayi");
    return {
      sinif: bas ? String(bas.className) : null,
      metin: metinTum(bas),
      adMetni: bas ? String(bas.textContent || "") : null,   // sayi ogesi HARIC
      sayiOgesi: sayi.length === 1 ? String(sayi[0].textContent) : null,
      sayiOgeAdedi: sayi.length,
      href: bas ? String(bas.href || "") : null,
    };
  });
  return { hata, konsolHatalari, panelSayisi: kutu.children.length, basliklar };
}

process.stdout.write(JSON.stringify(kos(), null, 1) + "\n");
