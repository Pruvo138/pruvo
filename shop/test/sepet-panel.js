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

// index.html'in sepet/arama inline <script> blogu (src'li script degil). ICERIKTEN bul:
// "cartLines" gecen bloktan geriye en yakin <script> acilisi -> ileri en yakin </script>.
// (Eskiden lastIndexOf ile "son blok" varsayiliyordu; body sonuna baska inline script
// —or. cerez onay banner'i— eklenince kirilirdi. Konum degil ICERIK sabit kaynak.)
const cartAnchor = INDEX.indexOf("cartLines");
const scriptBasi = cartAnchor >= 0 ? INDEX.lastIndexOf("<script>", cartAnchor) : -1;
const scriptSonu = INDEX.indexOf("</script>", scriptBasi);
const SCRIPT = scriptBasi >= 0 ? INDEX.slice(scriptBasi + "<script>".length, scriptSonu) : "";
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
  // Dinleyiciler saklanir ki testler gercek kullanici olayini tetikleyebilsin (test 9:
  // odemeForm submit). Onceki no-op davranis korunur: kayit yoksa tetikle hicbir sey yapmaz.
  el._dinleyiciler = {};
  el.addEventListener = (t, fn) => { el._dinleyiciler[t] = fn; };
  el.tetikle = (t, ev) => {
    const fn = el._dinleyiciler[t];
    if (fn) { return fn(ev || { preventDefault() {} }); }
  };
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
    location: { hash: "", search: ayar.search || "?sepet=1", pathname: "/", href: "", replace() {} },
    history: { replaceState() {} },
    localStorage: {
      getItem: (k) => (k in depo ? depo[k] : null),
      setItem: (k, v) => { depo[k] = String(v); },
      removeItem: (k) => { delete depo[k]; },
    },
    fetch(url, opts) {
      fetchIzi.push({ url: String(url), opts: opts || {} });
      // ayar.fetchHata: ANA katalog fetch'i (1.) DUSER — musteride ag/onbellek aksamasi.
      //   "reddet" -> fetch promise reject; "parse" -> yanit gelir ama json() cozulmez (404 govde).
      if (ayar.fetchHata && fetchIzi.length === 1) {
        if (ayar.fetchHata === "parse") {
          return Promise.resolve({ json: () => Promise.reject(new SyntaxError("Unexpected token < in JSON")) });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }
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
  // Enjeksiyon: script YUKLENDI ama fetch .then microtask'i HENUZ kosmadi (senkron kod
  // once biter). Savunma testi burada PRUVO_SECENEK.satirOzeti'ni patlatir -> renderCartPanel
  // govdesi acilista hata alir, KACIS durumunu gostermeli + katalog basligina dokunmamali.
  if (typeof ayar.enjekte === "function") { ayar.enjekte(ctx); }
  // fetch zinciri + (varsa) tazeleme fetch'i + isitHaystack setTimeout turlari bosalsin
  await bekle(30); await bekle(30);
  // ayar.hataBekle: sepet KASITLI patlatildiginda console.error beklenir (savunma katmani
  // yutar) — bunu altyapi hatasi sayma; test kendi iddiasini kosar.
  if (!ayar.hataBekle && konsolHatalari.length) {
    throw new Error("sayfa scripti hata basti (DOM takliti eksik olabilir): " +
      konsolHatalari.join(" | "));
  }
  return {
    el: (id) => belge.getElementById(id),
    satirlar: () => belge.getElementById("cartItems").children,
    metin: (id) => govdeMetni(belge.getElementById(id)),
    baslik: () => belge.getElementById("sectionTitle").textContent,
    konsolHatalari,
    fetchIzi,
    depo,
    ctx,
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

/** 6 — KOK NEDEN (17 Tem canli): bozuk unicode (essiz surrogate) sepetten ANA fetch
 *  zincirine ulasip katalog basligini "Urunler yuklenemedi"ye ceviriyordu. Essiz surrogate
 *  hem katalog basligina (bayat/CDN kopyasi) hem localStorage renk_ozel'ine (kullanici
 *  girdisi) konur; cartWaHref -> encodeURIComponent URIError atardi. KIRMIZI (fix'siz):
 *  title flips + panel bos. YESIL (fix): title "Tum Urunler" kalir, satir NORMAL render'lanir,
 *  WhatsApp linki uretilir (waKodla essiz surrogate'i U+FFFD yapip encode eder). */
async function test6BozukUnicode() {
  const hatalar = [];
  const LONE = "\uD83D";                                   // essiz yuksek surrogate
  const KOTU_URUN = Object.assign({}, GERCEK, {
    id: "unicode-urun", baslik: "Boru Baglanti " + LONE + " Parcasi",
  });
  const s = await sayfaKur({
    sepet: [{ id: "unicode-urun", malzeme: "PETG", renk: "Diğer", renk_ozel: "Fusya " + LONE, adet: 1 }],
    katalog: [KOTU_URUN],
    hataBekle: true,   // fix'siz URIError console'a duser; iddia asagida
  });
  if (s.baslik() !== "Tüm Ürünler") {
    hatalar.push("katalog basligi '" + s.baslik() + "' (bozuk unicode ana fetch'i dusurdu — fix yok)");
  }
  if (s.konsolHatalari.some((h) => h.indexOf("URI malformed") !== -1)) {
    hatalar.push("URIError yutulmadi/giderilmedi (waKodla devrede degil)");
  }
  if (s.satirlar().length !== 1) {
    hatalar.push("panelde " + s.satirlar().length + " satir (1 olmali — bozuk char render'i dusurdu)");
  }
  if (s.metin("cartItems").indexOf("Sepet görüntülenemedi") !== -1) {
    hatalar.push("kok neden giderilmemis: normal render yerine kacis durumu gosteriliyor");
  }
  // WhatsApp linki gercekten uretilebilmis olmali (encode patlamadi)
  const wa = s.el("cartOrder").href || "";
  if (wa.indexOf("https://wa.me/") !== 0) { hatalar.push("WhatsApp linki uretilemedi (encode patladi)"); }
  // Odeme normal acik (urun bulundu + fiyatli); rozet 1
  if (s.el("cartPay").disabled !== false) { hatalar.push("bozuk unicode odeme butonunu kilitledi"); }
  if (String(s.el("cartCount").textContent) !== "1") { hatalar.push("rozet 1 degil"); }
  rapor("6 bozuk unicode kok neden", hatalar,
    "title korundu, satir NORMAL render'landi, WhatsApp linki uretildi, URIError yok");
}

/** 7 — SAVUNMA: sepet render'i BASKA (ongorulmeyen) bir nedenle patlasa bile ANA fetch
 *  zinciri/katalog basligi DUSMEZ; panelde "Sepet goruntulenemedi — Sepeti temizle" kacis
 *  durumu gosterilir, odeme kilitlenir, temizle HER durumda calisir. Patlamayi kasitli
 *  enjekte ederiz (satirOzeti throw) — kok-neden fix'inden BAGIMSIZ ikinci guvence.
 *  KIRMIZI (guard'siz): throw -> openCart -> ana .catch -> title "Urunler yuklenemedi". */
async function test7SavunmaKacis() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [{ id: "gercek-urun", malzeme: "PETG", renk: "Siyah", adet: 1 }],
    katalog: KATALOG,
    hataBekle: true,
    enjekte: function (ctx) {
      // renderCartPanel govdesi bunu cagirir -> patlar -> guard kacis durumunu gostermeli
      ctx.PRUVO_SECENEK.satirOzeti = function () { throw new Error("enjekte-patlak"); };
    },
  });
  if (s.baslik() !== "Tüm Ürünler") {
    hatalar.push("katalog basligi '" + s.baslik() + "' (sepet hatasi ana fetch'i dusurdu — guard yok)");
  }
  const panel = s.metin("cartItems");
  if (panel.indexOf("Sepet görüntülenemedi") === -1) {
    hatalar.push("kacis durumu ('Sepet görüntülenemedi') gosterilmiyor");
  }
  if (s.el("cartPay").disabled !== true) { hatalar.push("kacis durumunda odeme kilitli DEGIL"); }
  if (s.el("cartOrder").className.indexOf("disabled") === -1) {
    hatalar.push("kacis durumunda WhatsApp butonu pasif degil");
  }
  // "Sepeti temizle" butonu HER durumda calismali (musterinin cikis yolu)
  const box = s.satirlar()[0];
  const btn = (box && box.children || []).filter((c) => c.tagName === "BUTTON").pop();
  if (!btn || String(btn.textContent).indexOf("temizle") === -1) {
    hatalar.push("kacis durumunda 'Sepeti temizle' butonu yok");
  } else {
    btn.onclick();
    if (JSON.parse(s.depo.pruvo_sepet).length !== 0) { hatalar.push("temizle localStorage'i bosaltmadi"); }
    if (s.metin("cartItems").indexOf("Sepetiniz boş") === -1) { hatalar.push("temizle sonrasi panel bosalmadi"); }
    if (String(s.el("cartCount").textContent) !== "0") { hatalar.push("temizle sonrasi rozet 0 degil"); }
  }
  rapor("7 savunma: sepet patlasa da katalog dusmez", hatalar,
    "title korundu, kacis durumu + kilitli odeme, temizle calisti");
}

/** 8 — KATALOG FETCH DUSTU (mimar paketi, 17 Tem gece — "sepete eklediğim ürünler görünmüyor"):
 *  musteride urunler.json fetch/parse aksarsa sepet HIC yuklenmemeliydi diye bir sey OLMAZ.
 *  ESKI kod: loadCart + updateCartFab + openCart yalniz fetch BASARI kolundaydi -> fetch dusunce
 *  cart=[] kalir, FAB gizli, panel bos, "?sepet=1" ile panel hic acilmaz. KIRMIZI kaniti:
 *  FAB gizli + panelde 0 satir. YENI kod: uc cagri katalogtan BAGIMSIZ acilista calisir ->
 *  FAB gorunur (rozet=cart.length), panel kayip-satir formunda DOLU (PRODUCTS bos -> her satir
 *  kayip:true), gorunur musteri uyarisi (emptyState) gosterilir. Odeme kilitli (gecerli satir yok). */
async function test8KatalogDustu() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [{ id: "gercek-urun", malzeme: "PETG", renk: "Siyah", adet: 1 }, KAYIP_SATIR],
    katalog: KATALOG,
    fetchHata: "reddet",   // ANA katalog fetch'i duser (openCart firsat tazelemesi de atesLENMEZ)
    hataBekle: true,       // .catch console.error basar ("Urunler yuklenemedi")
  });
  // FAB gorunur + rozet dogru sayida (katalog dusse de sepet yuklendi)
  const fab = s.el("cartFab");
  if (fab.style.display !== "inline-flex") {
    hatalar.push("FAB gizli ('" + fab.style.display + "' — katalog dusunce sepet hic yuklenmedi)");
  }
  if (String(s.el("cartCount").textContent) !== "2") {
    hatalar.push("rozet '" + s.el("cartCount").textContent + "' (2 olmali)");
  }
  // Panel DOLU: 2 satir, ikisi de kayip formunda (PRODUCTS bos kaldi)
  if (s.satirlar().length !== 2) {
    hatalar.push("panelde " + s.satirlar().length + " satir (2 olmali — panel bos kaldi)");
  }
  const panel = s.metin("cartItems");
  if (panel.indexOf("Ürün bilgisi yüklenemedi") === -1) {
    hatalar.push("kayip-satir formu ('Ürün bilgisi yüklenemedi') yok");
  }
  if (panel.indexOf("Sepetiniz boş") !== -1) {
    hatalar.push("panel 'Sepetiniz boş' diyor (satir varken)");
  }
  // Gorunur musteri uyarisi (tek satir): katalog yuklenemedi -> sayfayi yenile
  const uyari = s.metin("emptyState");
  if (uyari.indexOf("yüklenemedi") === -1 || uyari.indexOf("yenileyin") === -1) {
    hatalar.push("gorunur musteri uyarisi yok (emptyState: '" + uyari.trim() + "')");
  }
  if (s.el("emptyState").style.display !== "block") {
    hatalar.push("uyari elemani gizli (emptyState display '" + s.el("emptyState").style.display + "')");
  }
  // Katalog yok -> gecerli satir yok -> odeme + WhatsApp kilitli, gereksiz 2. fetch atilmadi
  if (s.el("cartPay").disabled !== true) { hatalar.push("katalog yokken odeme acik"); }
  if (s.el("cartOrder").className.indexOf("disabled") === -1) {
    hatalar.push("katalog yokken WhatsApp butonu aktif");
  }
  const jsonFetchleri = s.fetchIzi.filter((f) => f.url.indexOf("urunler.json") !== -1);
  if (jsonFetchleri.length !== 1) {
    hatalar.push("acilista " + jsonFetchleri.length + " fetch (1 olmali: ana fetch dustu, firsat tazelemesi atesLENMEMELI)");
  }
  rapor("8 katalog fetch dustu (sepet bagimsiz yuklenir)", hatalar,
    "FAB gorunur + rozet=2, panel 2 kayip satir, uyari gosterildi, odeme kilitli, tek fetch");
}

/** 9 — odeme istegi PARAMETRELERI tasir (canli 17 Tem: sari satirda parametreler
 *  gonderilmiyordu -> worker 400 parametre-yok -> "Odeme baslatilamadi").
 *  Sozlesme: front tutar/fiyat GONDERMEZ ama sari satirin parametrelerini AYNEN gonderir;
 *  worker fiyati bu parametrelerden kendisi hesaplar. */
async function test9OdemePayloadParametreler() {
  const hatalar = [];
  const PARAMETRIK_URUN = {
    id: "sari-urun", kategori: "Jeneratör", marka: [], parametrik: true,
    baslik: "Test Sari Urun", aciklama: "test", fiyat: "", gorseller: [],
  };
  const PARAMETRELER = { ic_cap: 32, kesit: 3 };
  const s = await sayfaKur({
    sepet: [{ id: "sari-urun", malzeme: "PLA", renk: "Siyah", adet: 2,
              parametreler: PARAMETRELER, parametre_detay: "İç çap: 32 mm",
              hacim_mm3: 1234, parametrik_fiyat_kurus: 10000 }],
    katalog: [GERCEK, PARAMETRIK_URUN],
  });
  // Form + onay doldur, odemeyi baslat (fetch mock'u istegi fetchIzi'ne yazar).
  s.el("oAd").value = "Test Musteri"; s.el("oTel").value = "5425551122";
  s.el("oEposta").value = "test@pruvo3d.com"; s.el("oSehir").value = "Fethiye";
  s.el("oAdres").value = "Test mahallesi no 1 Fethiye";
  s.el("oOnay").checked = true;
  // Gercek kullanici yolu: form submit olayi odemeBaslat'i cagirir (dogrudan fonksiyon
  // erisimi yok — IIFE icinde; dinleyici tetiklenir, fetch mock'u istegi kaydeder).
  s.el("odemeForm").tetikle("submit", { preventDefault() {} });
  await bekle(30);
  {
    const istek = s.fetchIzi.find((f) => f.url.indexOf("/baslat") !== -1);
    if (!istek) {
      hatalar.push("odeme istegi hic gitmedi (odenebilirlik kapisi mi kilitledi?)");
    } else {
      const govde = JSON.parse(istek.opts.body);
      const kalem = (govde.sepet || [])[0] || {};
      if (!kalem.parametreler) {
        hatalar.push("sari kalemde 'parametreler' YOK — worker 400 parametre-yok doner");
      } else if (JSON.stringify(kalem.parametreler) !== JSON.stringify(PARAMETRELER)) {
        hatalar.push("parametreler bozulmus: " + JSON.stringify(kalem.parametreler));
      }
      if (kalem.parametrik_fiyat_kurus != null || kalem.hacim_mm3 != null) {
        hatalar.push("istemci fiyat/hacim GONDERIYOR (sunucu hesabi ilkesi ihlali)");
      }
      if (kalem.adet !== 2) { hatalar.push("adet " + kalem.adet + " (2 olmali)"); }
    }
  }
  rapor("9 odeme istegi parametreleri tasir (fiyat/hacim tasimadan)", hatalar,
    "sari kalem parametrelerle gitti; fiyat/hacim istemciden gonderilmiyor");
}

// ---------------------------------------------------------------- akis

async function main() {
  console.log("PRUVO sepet paneli kabul testleri (index.html inline scripti node:vm'de)\n");
  await test1KayipSatir();
  await test2BosSepet();
  await test3Tazeleme();
  await test4KarisikSepet();
  await test5NormalAkis();
  await test6BozukUnicode();
  await test7SavunmaKacis();
  await test8KatalogDustu();
  await test9OdemePayloadParametreler();
  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" +
    (kalan ? "" : " — HEPSI YESIL ✅"));
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => {
  console.error("\nTEST ALTYAPI HATASI:", e && e.stack || e);
  process.exit(1);
});
