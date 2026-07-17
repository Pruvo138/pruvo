#!/usr/bin/env node
/**
 * PRUVO SEPET PANELI kabul testleri (mimar paketi, 17 Tem gece — "kayip sepet satiri").
 *
 *   node shop/test/sepet-panel.js
 *
 * SORUN (canli, 17 Tem): index.html cartLines() sepetteki satirin id'sini PRODUCTS'ta
 * bulamazsa (musterinin urunler.json kopyasi BAYAT ya da urun katalogdan SILINMIS) satiri
 * .filter(Boolean) ile SESSIZCE eliyordu: rozet "1", panel bos, genel toplam 0,00 TL,
 * "Kartla Guvenli Ode" aktif GORUNUYordu.
 *
 * NASIL: index.html'in inline scripti + secenekler.js, node:vm icinde minimal bir DOM
 * takliti (asagida `eleman`/`belgeKur`) ve sahte fetch/localStorage ile GERCEKTEN
 * calistirilir — kod kopyalanmaz, canli dosyanin kendisi sinanir. Panel render'inin
 * urettigi eleman agaci uzerinde iddialar kosulur.
 *
 * Beklenen davranis (mimar karari):
 *  1 kayip satir panelde GORUNUR ("Urun bilgisi yuklenemedi" + secim ozeti + fiyat "—"
 *    + kaldirma carpisi), odeme butonu DISABLED, tek satirlik aciklama gorunur.
 *  2 gercek bos sepette "Sepetiniz bos" + odeme/WhatsApp butonlari pasif.
 *  3 rozet = panel satir sayisi (kayip dahil) — celiski yok.
 *  4 panel acilisinda katalog-disi id varsa urunler.json BIR KEZ tazelenir (firsat
 *    duzeltmesi); urun gelirse satir normallesir.
 *  5 katalogda OLAN id'lerle normal akis DEGISMEMIS (regresyon).
 */

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const KOK = path.dirname(path.dirname(__dirname));   // shop/test -> repo koku
const INDEX = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const SECENEK_SRC = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");

// Beklenen tutarlar TEK KAYNAKTAN (secenekler.js) turetilir — kabul.js ile ayni desen.
require(path.join(KOK, "secenekler.js"));
const SECENEK = globalThis.PRUVO_SECENEK;
if (!SECENEK) { throw new Error("secenekler.js yuklenemedi"); }

// index.html'in SON inline <script> blogu (sepet/arama kodu). src'li script degil.
const scriptBasi = INDEX.lastIndexOf("<script>");
const scriptSonu = INDEX.indexOf("</script>", scriptBasi);
const SCRIPT = INDEX.slice(scriptBasi + "<script>".length, scriptSonu);
if (!SCRIPT.includes("cartLines")) {
  throw new Error("index.html inline sepet scripti bulunamadi (yapi degisti mi?)");
}

// ---------------------------------------------------------------- minimal DOM takliti

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

// Agactaki tum metin (textContent + innerHTML) — iddialar icin.
function govdeMetni(el) {
  let s = (el.textContent || "") + " " + (el.innerHTML || "");
  for (const c of el.children) { s += " " + govdeMetni(c); }
  return s;
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
  return { belge, kimlikler };
}

// ---------------------------------------------------------------- senaryo kosucusu

function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

/**
 * index.html scriptini verilen sepet/katalogla calistirir; sayfa "/?sepet=1" ile acilmis
 * gibi davranir (fetch -> render -> openCart). Dondurdukleri: eleman erisimi + fetch izi.
 *   ayar.sepet        localStorage'a yazilacak sepet dizisi
 *   ayar.katalog      ilk fetch("urunler.json") cevabi
 *   ayar.tazeKatalog  (istege bagli) IKINCI ve sonraki fetch cevabi (tazeleme senaryosu)
 */
async function sayfaKur(ayar) {
  const { belge } = belgeKur();
  const fetchIzi = [];
  const konsolHatalari = [];

  const depo = { pruvo_sepet: JSON.stringify(ayar.sepet || []) };
  const ctx = {
    document: belge,
    location: { hash: "", search: "?sepet=1", pathname: "/", href: "", replace() {} },
    history: { replaceState() {} },
    localStorage: {
      getItem: (k) => (k in depo ? depo[k] : null),
      setItem: (k, v) => { depo[k] = String(v); },
      removeItem: (k) => { delete depo[k]; },
    },
    fetch(url, opts) {
      fetchIzi.push({ url: String(url), opts: opts || {} });
      const veri = (fetchIzi.length >= 2 && ayar.tazeKatalog) ? ayar.tazeKatalog : ayar.katalog;
      return Promise.resolve({ json: () => Promise.resolve(JSON.parse(JSON.stringify(veri))) });
    },
    console: { log() {}, error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
    alert() {},
    navigator: {},
    URLSearchParams,
    setTimeout, clearTimeout,
    /* URL-senkron paketi (yukari-cik oku) window.addEventListener("scroll") +
       scrollTo cagiriyor — sahte pencerede no-op karsiliklari olsun. */
    addEventListener() {}, removeEventListener() {},
    scrollTo() {}, scrollY: 0, innerHeight: 720,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SECENEK_SRC, ctx, { filename: "secenekler.js" });
  vm.runInContext(SCRIPT, ctx, { filename: "index-inline.js" });
  // fetch zinciri + (varsa) tazeleme fetch'i + isitHaystack setTimeout turlari bosalsin
  await bekle(30); await bekle(30);
  if (konsolHatalari.length) {
    throw new Error("sayfa scripti hata basti (DOM takliti eksik olabilir): " +
      konsolHatalari.join(" | "));
  }
  return {
    el: (id) => belge.getElementById(id),
    satirlar: () => belge.getElementById("cartItems").children,
    metin: (id) => govdeMetni(belge.getElementById(id)),
    fetchIzi,
    depo,
  };
}

// ---------------------------------------------------------------- veri + rapor

const GERCEK = {
  id: "gercek-urun", kategori: "Otomobil", marka: ["Audi"],
  baslik: "Test Gercek Urun", aciklama: "test", fiyat: "850 TL", gorseller: [],
};
const KATALOG = [GERCEK];
const KAYIP_SATIR = { id: "hayalet-urun", malzeme: "PETG", renk: "Siyah", adet: 1 };

let gecen = 0, kalan = 0;
function rapor(ad, hatalar, detay) {
  const ok = hatalar.length === 0;
  ok ? gecen++ : kalan++;
  console.log((ok ? "  ✅ GECTI " : "  ❌ KALDI ") + ad +
    (ok ? (detay ? " — " + detay : "") : " — " + hatalar.join(" ; ")));
}

// ---------------------------------------------------------------- testler

/** 1 — kayip satir GORUNUR + odeme kilitli + aciklama + rozet tutarli */
async function test1KayipSatir() {
  const hatalar = [];
  const s = await sayfaKur({ sepet: [KAYIP_SATIR], katalog: KATALOG });

  const satirlar = s.satirlar();
  if (satirlar.length !== 1) {
    hatalar.push("panelde " + satirlar.length + " satir (1 olmali — satir SESSIZCE elendi)");
  }
  const panelMetni = s.metin("cartItems");
  if (panelMetni.indexOf("Ürün bilgisi yüklenemedi") === -1) {
    hatalar.push("'Ürün bilgisi yüklenemedi' basligi yok");
  }
  if (panelMetni.indexOf("Sepetiniz boş") !== -1) {
    hatalar.push("panel 'Sepetiniz boş' diyor (satir varken)");
  }
  if (panelMetni.indexOf("PETG") === -1) { hatalar.push("malzeme/renk ozeti yok"); }
  if (panelMetni.indexOf("—") === -1) { hatalar.push("fiyat alani '—' degil"); }

  const pay = s.el("cartPay");
  if (pay.disabled !== true) { hatalar.push("odeme butonu disabled DEGIL"); }
  if (pay.className.indexOf("disabled") === -1) { hatalar.push("odeme butonunda .disabled sinifi yok"); }
  if (s.el("cartKayipNot").style.display !== "block") {
    hatalar.push("kayip aciklama satiri gorunmuyor (cartKayipNot)");
  }
  // Rozet = panel satir sayisi (celiski yok)
  const rozet = s.el("cartCount").textContent;
  if (String(rozet) !== String(satirlar.length) || String(rozet) !== "1") {
    hatalar.push("rozet=" + rozet + " panel=" + satirlar.length + " (ikisi de 1 olmali)");
  }
  // Kayip satir toplamlara girmez: parasal satirlar gizli, WhatsApp pasif (gecerli satir yok)
  if (s.el("cartAraRow").style.display === "flex") { hatalar.push("kayip satir ara toplami acti"); }
  if (s.el("cartOrder").className.indexOf("disabled") === -1) {
    hatalar.push("tum satirlar kayipken WhatsApp butonu aktif");
  }
  // Carpiyla kaldirilabilir -> gercek bos sepet durumuna doner
  const carpi = (satirlar[0] && satirlar[0].children || [])
    .filter((c) => c.tagName === "BUTTON").pop();
  if (!carpi || typeof carpi.onclick !== "function") {
    hatalar.push("kayip satirda kaldirma carpisi yok");
  } else {
    carpi.onclick();
    if (s.metin("cartItems").indexOf("Sepetiniz boş") === -1 ||
        String(s.el("cartCount").textContent) !== "0") {
      hatalar.push("carpi kayip satiri kaldirmadi (panel/rozet)");
    }
    if (JSON.parse(s.depo.pruvo_sepet).length !== 0) {
      hatalar.push("carpi localStorage'daki satiri silmedi");
    }
  }
  rapor("1 kayip satir gorunur + odeme kilitli", hatalar,
    "satir GORUNDU, fiyat '—', buton disabled, rozet=panel=1, carpi calisti");
}

/** 2 — gercek bos sepet: butonlar pasif (0,00 TL + aktif buton VAKASI) */
async function test2BosSepet() {
  const hatalar = [];
  const s = await sayfaKur({ sepet: [], katalog: KATALOG });
  if (s.metin("cartItems").indexOf("Sepetiniz boş") === -1) {
    hatalar.push("'Sepetiniz boş' gorunmuyor");
  }
  const pay = s.el("cartPay");
  if (pay.disabled !== true) { hatalar.push("bos sepette odeme butonu disabled DEGIL"); }
  if (pay.className.indexOf("disabled") === -1) { hatalar.push("bos sepette .disabled sinifi yok"); }
  if (s.el("cartOrder").className.indexOf("disabled") === -1) {
    hatalar.push("bos sepette WhatsApp butonu pasif degil");
  }
  if (String(s.el("cartCount").textContent) !== "0") {
    hatalar.push("rozet " + s.el("cartCount").textContent + " (0 olmali)");
  }
  // HTML varsayilani da guvenli olmali: panel ilk render'dan ONCE gorunse bile buton pasif.
  const varsayilan = /<button id="cartPay"[^>]*\bdisabled\b/.test(INDEX);
  if (!varsayilan) { hatalar.push("HTML'de cartPay varsayilan olarak disabled degil"); }
  rapor("2 bos sepet butonlari pasif", hatalar,
    "Sepetiniz bos + odeme/WhatsApp pasif + HTML varsayilani disabled");
}

/** 3 — firsat duzeltmesi: panel acilisinda katalog tazelenir, urun gelirse satir normallesir */
async function test3Tazeleme() {
  const hatalar = [];
  const YENI = Object.assign({}, GERCEK, { id: "yeni-urun", baslik: "Yeni Eklenen Urun" });
  const s = await sayfaKur({
    sepet: [{ id: "yeni-urun", malzeme: "PLA", renk: "Siyah", adet: 1 }],
    katalog: KATALOG,                    // bayat kopya: yeni-urun YOK
    tazeKatalog: KATALOG.concat([YENI]), // tazeleme cevabi: geldi
  });
  const jsonFetchleri = s.fetchIzi.filter((f) => f.url.indexOf("urunler.json") !== -1);
  if (jsonFetchleri.length !== 2) {
    hatalar.push("urunler.json " + jsonFetchleri.length + " kez cekildi (2 olmali: acilis + tazeleme)");
  }
  const panelMetni = s.metin("cartItems");
  if (panelMetni.indexOf("Yeni Eklenen Urun") === -1) {
    hatalar.push("tazeleme sonrasi urun basligi gelmedi");
  }
  if (panelMetni.indexOf("Ürün bilgisi yüklenemedi") !== -1) {
    hatalar.push("urun geldigi halde kayip satir duruyor");
  }
  if (s.el("cartPay").disabled !== false) { hatalar.push("urun geldigi halde odeme acilmadi"); }
  rapor("3 firsat duzeltmesi (katalog tazeleme)", hatalar,
    "2. fetch atildi, satir normallesti, odeme acildi");
}

/** 4 — karisik sepet: gercek satir + kayip satir birlikte */
async function test4KarisikSepet() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [{ id: "gercek-urun", malzeme: "PETG", renk: "Siyah", adet: 1 }, KAYIP_SATIR],
    katalog: KATALOG,
  });
  if (s.satirlar().length !== 2) {
    hatalar.push("panelde " + s.satirlar().length + " satir (2 olmali)");
  }
  // Toplam yalniz GERCEK satirdan: 850 x PETG (tek kaynak secenekler.js) — kayip dahil edilmez
  const urun = SECENEK.hesaplaFiyatKurus(850, "PETG", "Siyah", 0);
  if (s.el("cartAra").textContent !== SECENEK.kurusMetni(urun)) {
    hatalar.push("ara toplam '" + s.el("cartAra").textContent + "' (beklenen " +
      SECENEK.kurusMetni(urun) + " — kayip satir toplama girmis olabilir)");
  }
  const genel = SECENEK.kurusMetni(urun + SECENEK.kargoKurus(urun));
  if (s.el("cartTotal").textContent !== genel) {
    hatalar.push("genel toplam '" + s.el("cartTotal").textContent + "' (beklenen " + genel + ")");
  }
  if (s.el("cartPay").disabled !== true) { hatalar.push("kayip satir varken odeme acik"); }
  if (s.el("cartKayipNot").style.display !== "block") { hatalar.push("aciklama satiri yok"); }
  // WhatsApp yasar ama metne yalniz gercek urun girer
  const wa = decodeURIComponent(s.el("cartOrder").href || "");
  if (wa.indexOf("Test Gercek Urun") === -1) { hatalar.push("WhatsApp metninde gercek urun yok"); }
  if (wa.indexOf("hayalet") !== -1) { hatalar.push("WhatsApp metnine kayip satir sizdi"); }
  rapor("4 karisik sepet (gercek + kayip)", hatalar,
    "2 satir, toplam yalniz gercekten, odeme kilitli, WhatsApp'a kayip sizmadi");
}

/** 5 — regresyon: katalogda olan id'lerle normal akis DEGISMEMIS */
async function test5NormalAkis() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [{ id: "gercek-urun", malzeme: "PETG", renk: "Siyah", adet: 2 }],
    katalog: KATALOG,
  });
  const panelMetni = s.metin("cartItems");
  if (s.satirlar().length !== 1 || panelMetni.indexOf("Test Gercek Urun") === -1) {
    hatalar.push("normal satir render'i bozuldu");
  }
  const birim = SECENEK.hesaplaFiyatKurus(850, "PETG", "Siyah", 0);
  const ara = birim * 2;
  if (s.el("cartAra").textContent !== SECENEK.kurusMetni(ara)) {
    hatalar.push("ara toplam '" + s.el("cartAra").textContent + "' != " + SECENEK.kurusMetni(ara));
  }
  const genel = SECENEK.kurusMetni(ara + SECENEK.kargoKurus(ara));
  if (s.el("cartTotal").textContent !== genel) {
    hatalar.push("genel toplam '" + s.el("cartTotal").textContent + "' != " + genel);
  }
  const pay = s.el("cartPay");
  if (pay.disabled !== false || pay.className !== "cart-pay-btn" ||
      pay.textContent !== "Kartla Güvenli Öde") {
    hatalar.push("odeme butonu: disabled=" + pay.disabled + " class='" + pay.className +
      "' metin='" + pay.textContent + "'");
  }
  if (s.el("cartKayipNot").style.display === "block") {
    hatalar.push("normal sepette kayip aciklamasi gorunuyor");
  }
  if (!s.el("cartOrder").href) { hatalar.push("WhatsApp href'i yok"); }
  const jsonFetchleri = s.fetchIzi.filter((f) => f.url.indexOf("urunler.json") !== -1);
  if (jsonFetchleri.length !== 1) {
    hatalar.push("normal sepette gereksiz katalog tazelemesi (" + jsonFetchleri.length + " fetch)");
  }
  rapor("5 normal akis regresyonu", hatalar,
    "satir + toplam (" + genel + ") + aktif odeme aynen; gereksiz fetch yok");
}

// ---------------------------------------------------------------- akis

async function main() {
  console.log("PRUVO sepet paneli kabul testleri (index.html inline scripti node:vm'de)\n");
  await test1KayipSatir();
  await test2BosSepet();
  await test3Tazeleme();
  await test4KarisikSepet();
  await test5NormalAkis();
  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" +
    (kalan ? "" : " — HEPSI YESIL ✅"));
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => {
  console.error("\nTEST ALTYAPI HATASI:", e && e.stack || e);
  process.exit(1);
});
