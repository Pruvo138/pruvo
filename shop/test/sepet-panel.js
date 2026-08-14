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

// index.html'in sepet/arama inline <script> blogu (src'li script degil). ICERIK IMZASI
// ("cartLines") ile ortak robust yardimciyla ayiklanir. ESKIDEN: lastIndexOf("<script>",
// cartAnchor) ile geriye en yakin acilis araniyordu; index.html'de bir JS YORUMU icinde
// gecen "<script>" metni capayi kaydirip testi SyntaxError'la olduruyordu (ayni sinif,
// vitrin-kabul.js'te 4fdfa9b7'de giderilmisti). Artik tek kaynak: tools/html-blok-ayikla.js.
const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));
const SCRIPT = inlineScriptBul(INDEX, "cartLines");
if (!SCRIPT) {
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
    // Gercek tarayicida document.cookie DAIMA string'dir (cerez yoksa ""). Odeme aninda
    // PRUVO_ATIF.topla() (reklam atif kimlikleri) bunu cerez()'le OKUR; stub'ta eksikse
    // undefined.match(...) atar, odemeBaslat try/catch'i yutar, /baslat istegi HIC gitmezdi
    // (test 9 boyle kaliyordu — f287602 atif okumasini ekledi, stub guncellenmedi). Yalniz
    // OKUMA var (index.html'de document.cookie'ye yazma yok) -> bos string yeterli.
    cookie: "",
  };
  return { belge, kimlikler };
}

// ---------------------------------------------------------------- senaryo kosucusu

function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

/**
 * Edge kart ozeti — tools/build.py kart_ozeti() ile AYNI alan kumesi. Canliya SADIK olmasi
 * onemli: edge modunda tarayiciya urunler.json INMEZ, sepet paneli YALNIZ bu daraltilmis
 * karti gorur (or. "konfigur" alani kartta YOKTUR -> konfigur satirini bilmenin tek canli
 * ekseni localStorage'daki satir bayragidir; test 10-13 bu gercegi kosar).
 */
function kartOzeti(p) {
  const k = {
    id: p.id, baslik: p.baslik || "", kategori: p.kategori || "", marka: p.marka || [],
    fiyat: p.fiyat || "", gorsel: (p.gorseller || [null])[0],
    parametrik: !!p.parametrik, aciklama: (p.aciklama || "").slice(0, 200),
  };
  // `tur`: YALNIZ tam "fiziksel" degeri basilir (canli kart_ozeti ile AYNI kural).
  // Bu alan hem FIYAT (malzeme/renk carpanini 1,00'e sabitler) hem SINIF BEYANI
  // (cayma hakki metni) yolunu surer; aynadan dusmesi edge modunda ikisini birden
  // sessizce bozardi -> test 15 bu ekseni kosar.
  if (p.tur === "fiziksel") { k.tur = "fiziksel"; }
  return k;
}

/**
 * index.html scriptini verilen sepet/katalogla calistirir; sayfa "/?sepet=1" ile acilmis
 * gibi davranir (fetch -> render -> openCart). Dondurdukleri: eleman erisimi + fetch izi.
 *
 * 🔴 EDGE MODU (index.html EDGE_KATALOG = true — CANLI hal): acilis ozet.json'u ceker,
 * urunler.json INMEZ; sepetteki eksik urunler /katalog?ids= ile TAMAMLANIR. Sahte fetch bu
 * yuzden URL'e gore YONLENDIRIR (eskiden her istege urunler.json govdesi donuyordu; edge
 * bayragi acildiktan sonra ".ok" kontrolu yuzunden acilis "HTTP undefined" ile patliyor,
 * dosyadaki 9 nobetci de ALTYAPI HATASI verip HIC kosmuyordu — olu nobetci, 30 Tem).
 *   ayar.sepet        localStorage'a yazilacak sepet dizisi
 *   ayar.katalog      katalogda YAYINDA olan urunler (ozet.json "yeni" + /katalog cevabi)
 *   ayar.tazeKatalog  (istege bagli) /katalog?ids= tazeleme cevabinin havuzu
 *   ayar.fetchHata    "reddet" | "parse" -> TUM katalog uclari (ozet + /katalog + /ara) duser
 *   ayar.prova        (istege bagli) POST /api/shop/fiyat sahtesi:
 *                       fonksiyon(kalem) -> {ok, govde} | {ag:true} | {cop:true} | {sessiz:true}
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
      const u = String(url);
      fetchIzi.push({ url: u, opts: opts || {} });
      const katalog = ayar.katalog || [];
      const cevap = (govde, ok = true, durum = 200) => Promise.resolve({
        ok, status: durum,
        json: () => Promise.resolve(JSON.parse(JSON.stringify(govde))),
      });
      const katalogUcu = u.indexOf("ozet.json") !== -1 || u.indexOf("urunler.json") !== -1 ||
        u.indexOf("/katalog") !== -1 || u.indexOf("/ara") !== -1;

      // ayar.fetchHata: KATALOG uclari duser — musteride ag/onbellek aksamasi.
      //   "reddet" -> fetch promise reject; "parse" -> yanit gelir ama json() cozulmez (404 govde).
      if (ayar.fetchHata && katalogUcu) {
        if (ayar.fetchHata === "parse") {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.reject(new SyntaxError("Unexpected token < in JSON")),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }

      // POST /api/shop/fiyat — konfigur odenebilirlik provasi (ayar.prova ile sekillenir).
      if (u.indexOf("/fiyat") !== -1) {
        const kalem = (JSON.parse((opts && opts.body) || "{}").sepet || [])[0] || {};
        const p = typeof ayar.prova === "function" ? ayar.prova(kalem) : { ok: false };
        if (p.ag) { return Promise.reject(new TypeError("Failed to fetch")); }
        if (p.sessiz) { return new Promise(() => {}); }          // hic cevap gelmez (zaman asimi)
        if (p.cop) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.reject(new SyntaxError("Unexpected token < in JSON")),
          });
        }
        return cevap(p.govde || {}, p.ok !== false, p.durum || (p.ok === false ? 400 : 200));
      }
      // POST /api/shop/baslat — test 9 yalniz ISTEGI inceler; cevap notr 400.
      if (u.indexOf("/baslat") !== -1) { return cevap({ hata: "test-baslat" }, false, 400); }

      // Firsat tazelemesi: sepetteki eksik id'ler (/katalog?ids=a,b) — havuz tazeKatalog.
      if (u.indexOf("ids=") !== -1) {
        const istenen = decodeURIComponent(u.split("ids=")[1] || "").split(",");
        const havuz = ayar.tazeKatalog || [];
        return cevap({ urunler: havuz.filter((p) => istenen.indexOf(p.id) !== -1).map(kartOzeti) });
      }
      if (u.indexOf("ozet.json") !== -1) {
        return cevap({
          surum: 1, toplam: katalog.length, kategoriler: {}, markalar: {},
          parametrik: katalog.filter((p) => p.parametrik).map(kartOzeti),
          yeni: katalog.map(kartOzeti),
        });
      }
      if (u.indexOf("/katalog") !== -1 || u.indexOf("/ara") !== -1) {
        return cevap({ urunler: katalog.map(kartOzeti), toplam: katalog.length });
      }
      if (u.indexOf("urunler.json") !== -1) { return cevap(katalog); }
      return cevap({});
    },
    console: { log() {}, error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
    alert() {},
    navigator: {},
    URLSearchParams,
    /* ayar.hizliZamanAsimi: uzun (>=1 sn) zamanlayicilar HEMEN kosar — provanin 8 sn'lik
       zaman asimi kolunu testte 8 sn beklemeden kanitlamak icin. Kisa timer'lar (debounce,
       isitHaystack) DOKUNULMAZ; bayrak kapaliyken davranis birebir gercek setTimeout. */
    setTimeout: (fn, ms, ...a) => setTimeout(fn, (ayar.hizliZamanAsimi && ms >= 1000) ? 0 : ms, ...a),
    clearTimeout,
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
  // EDGE: tazeleme 5-15 MB katalogu DEGIL yalniz eksik id'leri ceker (/katalog?ids=).
  const acilis = s.fetchIzi.filter((f) => f.url.indexOf("ozet.json") !== -1);
  const tazeleme = s.fetchIzi.filter((f) => f.url.indexOf("ids=") !== -1);
  if (acilis.length !== 1) {
    hatalar.push("ozet.json " + acilis.length + " kez cekildi (1 olmali)");
  }
  if (tazeleme.length !== 1) {
    hatalar.push("firsat tazelemesi " + tazeleme.length + " kez atildi (1 olmali)");
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
      pay.textContent !== "Havale/EFT veya Kartla Güvenle Öde") {
    hatalar.push("odeme butonu: disabled=" + pay.disabled + " class='" + pay.className +
      "' metin='" + pay.textContent + "'");
  }
  if (s.el("cartKayipNot").style.display === "block") {
    hatalar.push("normal sepette kayip aciklamasi gorunuyor");
  }
  if (!s.el("cartOrder").href) { hatalar.push("WhatsApp href'i yok"); }
  const tazeleme = s.fetchIzi.filter((f) => f.url.indexOf("ids=") !== -1);
  if (tazeleme.length !== 0) {
    hatalar.push("normal sepette gereksiz katalog tazelemesi (" + tazeleme.length + " fetch)");
  }
  // Normal (konfigursuz) urunde ODENEBILIRLIK PROVASI da ATILMAZ — /fiyat ucuna kor istek yok.
  const prova = s.fetchIzi.filter((f) => f.url.indexOf("/fiyat") !== -1);
  if (prova.length !== 0) {
    hatalar.push("konfigursuz sepette " + prova.length + " adet /fiyat provasi atildi (0 olmali)");
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
  // Gorunur musteri uyarisi: EDGE modunda katalog ucu dusunce durum satiri (edgeDurum)
  // "Katalog baglantisi kurulamadi …" der (EDGE_YEDEK_MESAJ) — sayfa bos/beyaz kalmaz.
  const uyari = s.metin("edgeDurum");
  if (uyari.indexOf("Katalog bağlantısı kurulamadı") === -1) {
    hatalar.push("gorunur musteri uyarisi yok (edgeDurum: '" + uyari.trim() + "')");
  }
  if (s.el("edgeDurum").style.display !== "flex") {
    hatalar.push("uyari elemani gizli (edgeDurum display '" + s.el("edgeDurum").style.display + "')");
  }
  // Katalog yok -> gecerli satir yok -> odeme + WhatsApp kilitli, gereksiz 2. fetch atilmadi
  if (s.el("cartPay").disabled !== true) { hatalar.push("katalog yokken odeme acik"); }
  if (s.el("cartOrder").className.indexOf("disabled") === -1) {
    hatalar.push("katalog yokken WhatsApp butonu aktif");
  }
  const acilis = s.fetchIzi.filter((f) => f.url.indexOf("ozet.json") !== -1);
  const tazeleme = s.fetchIzi.filter((f) => f.url.indexOf("ids=") !== -1);
  if (acilis.length !== 1) {
    hatalar.push("acilista ozet.json " + acilis.length + " kez cekildi (1 olmali)");
  }
  if (tazeleme.length !== 0) {
    hatalar.push("ana fetch dustugu halde firsat tazelemesi atesLENDI (" + tazeleme.length + ")");
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

// ================================================================ KONFIGUR ODENEBILIRLIK
/* 10-14 — "bundle'da yok" penceresi (canli olcum, 30 Tem).
   SORUN: urunler.json'a konfigur alanli urun eklenince site onu ODENEBILIR sayiyordu; Worker
   ise konfigur haritasini kendi BUNDLE'indan okuyor (deploy ELLE) -> deploy'a kadar musteri
   sepete atiyor, ODEME FORMUNU DOLDURUYOR ve en sonda /baslat'in 400'une carpiyordu.
   COZUM: sepet gorunumu kurulurken kart yolu CANLI Worker'a sorulur (POST /api/shop/fiyat —
   yan etkisiz prova). 200 -> acik; 4xx/5xx/ag/zaman asimi/cop govde -> KAPALI (fail-closed).
   Bu bes nobetci fix'siz index.html'de KIRMIZI yanar (olculdu: 10/12/13 kirmizi). */

const KONFIGUR_URUN = {
  id: "yarasa-serit-dekoratif-figur", kategori: "Skan Art", marka: [],
  baslik: "Yarasa Heykeli Serit Dekoratif Figur", aciklama: "test", fiyat: "500 TL",
  gorseller: [],
};
/** Konfiguratorun (konfigur.js satiraYaz) yazdigi sepet satiri — konfigur:true + boy. */
function konfigurSatiri(boyMm, kurus) {
  return {
    id: KONFIGUR_URUN.id, malzeme: "PLA", renk: "Siyah", renk_ozel: "", adet: 1,
    konfigur: true, parametreler: { boy_mm: boyMm },
    parametre_detay: "Boy: " + (boyMm / 10) + " cm",
    hacim_mm3: 90000, parametrik_fiyat_kurus: kurus,
  };
}
/** Worker 200 cevabi (prova) — /fiyat'in gercek beyaz-liste govdesi. */
function provaAcik(kalem) {
  return { ok: true, govde: {
    prova: true,
    satirlar: [{ id: kalem.id, adet: kalem.adet, birim_kurus: 150000, tutar_kurus: 150000 }],
    urun_kurus: 150000, kargo_kurus: 25000, tahsilat_kurus: 175000, tutar: "1.750,00 TL",
    net_kurus: 145833, kdv_kurus: 29167, kdv_yuzde: 20,
  } };
}
/** Worker 400 cevabi — urun bundle'da YOK (ya da konfigur kanali kapali). */
function provaKapali(kalem) {
  return { ok: false, durum: 400,
           govde: { hata: "konfigur-urun", id: kalem.id,
                    mesaj: "Ölçüye özel ürünler için WhatsApp'tan teklif alın." } };
}

/** 10 — KAPALI URUN: bundle'da olmayan konfigur urunu -> kart yolu KAPALI, WhatsApp gorunur,
 *  musteri odeme formunu ACAMAZ (form doldurma duvarina hic gitmez). */
async function test10KonfigurKapali() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [konfigurSatiri(300, 150000)],
    katalog: [KONFIGUR_URUN],
    prova: provaKapali,
  });

  const pay = s.el("cartPay");
  if (pay.disabled !== true) { hatalar.push("kart yolu ACIK (buton disabled degil)"); }
  if (pay.className.indexOf("disabled") === -1) { hatalar.push("odeme butonunda .disabled sinifi yok"); }
  if (String(pay.textContent).indexOf("WhatsApp") === -1) {
    hatalar.push("buton metni WhatsApp'a yonlendirmiyor: '" + pay.textContent + "'");
  }
  // Musteri ODEME FORMUNU ACAMAZ — asil kayip buydu (form dolduruluyor, en sonda 400).
  pay.onclick();
  if (s.el("odemeForm").style.display === "block") {
    hatalar.push("kart yolu kapaliyken odeme formu ACILDI (musteri formu dolduruyor)");
  }
  // WhatsApp kanali yasiyor + hangi urun oldugu ADIYLA sepette yaziyor
  if (s.el("cartOrder").className.indexOf("disabled") !== -1) {
    hatalar.push("WhatsApp butonu pasif (tek kanal kapandi)");
  }
  const not = s.el("cartKonfigurNot");
  if (not.style.display !== "block") { hatalar.push("sepette konfigur uyarisi gorunmuyor"); }
  if (String(not.textContent).indexOf(KONFIGUR_URUN.baslik) === -1) {
    hatalar.push("uyari urunu ADIYLA soylemiyor: '" + not.textContent + "'");
  }
  // Satirin kendi altinda uyari + o urune ozel WhatsApp linki
  const satirMetni = s.metin("cartItems");
  if (satirMetni.indexOf("kartla ödenemiyor") === -1) {
    hatalar.push("satir altinda 'kartla ödenemiyor' uyarisi yok");
  }
  if (satirMetni.indexOf("WhatsApp'tan sor") === -1) {
    hatalar.push("satira ozel WhatsApp linki yok");
  }
  // TEK prova istegi, dogru uc + dogru govde (fiyat/hacim SIZMAZ)
  const prova = s.fetchIzi.filter((f) => f.url.indexOf("/fiyat") !== -1);
  if (prova.length !== 1) { hatalar.push(prova.length + " prova istegi (1 olmali)"); }
  else {
    if (prova[0].url.indexOf("/api/shop/fiyat") === -1) {
      hatalar.push("prova yanlis uca gitti: " + prova[0].url);
    }
    if ((prova[0].opts.method || "").toUpperCase() !== "POST") { hatalar.push("prova POST degil"); }
    const kalem = (JSON.parse(prova[0].opts.body).sepet || [])[0] || {};
    if (!kalem.parametreler || kalem.parametreler.boy_mm !== 300) {
      hatalar.push("prova kaleminde boy_mm yok: " + JSON.stringify(kalem));
    }
    if (kalem.parametrik_fiyat_kurus != null || kalem.hacim_mm3 != null) {
      hatalar.push("prova istemci fiyat/hacim GONDERIYOR (sunucu hesabi ilkesi)");
    }
  }
  rapor("10 kapali konfigur urunu (bundle'da yok) -> kart yolu KAPALI", hatalar,
    "buton kilitli + form acilmadi + urun adiyla uyari + satir WhatsApp linki; 1 prova istegi");
}

/** 11 — ACIK URUN: bundle'da OLAN konfigur urunu -> kart yolu ACIK, davranis bugunkuyle ayni. */
async function test11KonfigurAcik() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [konfigurSatiri(300, 150000)],
    katalog: [KONFIGUR_URUN],
    prova: provaAcik,
  });
  const pay = s.el("cartPay");
  if (pay.disabled !== false) { hatalar.push("prova 200 dondu ama kart yolu KAPALI"); }
  if (pay.className !== "cart-pay-btn") { hatalar.push("buton sinifi '" + pay.className + "'"); }
  if (pay.textContent !== "Havale/EFT veya Kartla Güvenle Öde") {
    hatalar.push("buton metni '" + pay.textContent + "'");
  }
  if (s.el("cartKonfigurNot").style.display === "block") {
    hatalar.push("acik urunde 'kartla odenemiyor' uyarisi gorunuyor");
  }
  if (s.metin("cartItems").indexOf("kartla ödenemiyor") !== -1) {
    hatalar.push("acik urunde satir uyarisi cikti");
  }
  // Odeme formu ACILABILIR (musteri normal akista)
  pay.onclick();
  if (s.el("odemeForm").style.display !== "block") {
    hatalar.push("acik urunde odeme formu acilmadi");
  }
  const prova = s.fetchIzi.filter((f) => f.url.indexOf("/fiyat") !== -1);
  if (prova.length !== 1) { hatalar.push(prova.length + " prova istegi (1 olmali)"); }
  rapor("11 acik konfigur urunu -> kart yolu ACIK (bugunku davranis)", hatalar,
    "buton aktif + uyari yok + odeme formu acildi; 1 prova istegi");
}

/** 12 — FAIL-CLOSED FIKSTURLERI: ag hatasi / zaman asimi / cop govde -> kart yolu KAPALI.
 *  Belirsizlik "odenebilir" SAYILMAZ (sunucu kapisi son soz, ama musteri erken bilgilenir). */
async function test12FailClosed() {
  const hatalar = [];
  const fiksturler = [
    ["ag hatasi", { ag: true }, {}],
    ["zaman asimi", { sessiz: true }, { hizliZamanAsimi: true }],
    ["cop govde", { cop: true }, {}],
    ["200 ama beklenmedik govde", { ok: true, govde: { merhaba: "dunya" } }, {}],
    ["429 hiz siniri", { ok: false, durum: 429, govde: { hata: "cok-istek" } }, {}],
    // HTTP durumu ile govde CELISIRSE durum kazanir (araya giren vekil/onbellek eski bir
    // basarili govdeyi 4xx ile dondurebilir; mutasyon M8 bu iddiayi olduruyordu).
    ["400 ama gecerli gorunen govde",
     { ok: false, durum: 400, govde: { prova: true, tahsilat_kurus: 175000 } }, {}],
  ];
  for (const [ad, cevap, ek] of fiksturler) {
    const s = await sayfaKur(Object.assign({
      sepet: [konfigurSatiri(300, 150000)],
      katalog: [KONFIGUR_URUN],
      prova: () => cevap,
    }, ek));
    const pay = s.el("cartPay");
    if (pay.disabled !== true) { hatalar.push(ad + ": kart yolu ACIK kaldi (fail-OPEN!)"); }
    pay.onclick();
    if (s.el("odemeForm").style.display === "block") {
      hatalar.push(ad + ": odeme formu acildi");
    }
    if (s.el("cartOrder").className.indexOf("disabled") !== -1) {
      hatalar.push(ad + ": WhatsApp kanali da kapandi (musterinin cikisi yok)");
    }
  }
  /* CEVAP GELMEDEN (bekliyor) — en sinsi hal: prova ucusta iken varsayilan "odenebilir"
     olsaydi musteri o ilk saniyelerde forma girer, doldurur ve sunucu 400'une carpardi.
     Bu yuzden BASLANGIC durumu da KAPALI ve buton "kontrol ediliyor" der.
     (Mutasyon M2: provaSonucu varsayilanini "acik" yapmak -> BU iddia kirmizi yanar.) */
  const b = await sayfaKur({
    sepet: [konfigurSatiri(300, 150000)],
    katalog: [KONFIGUR_URUN],
    prova: () => ({ sessiz: true }),        // cevap HIC gelmez, zaman asimi da dolmaz
  });
  const bPay = b.el("cartPay");
  if (bPay.disabled !== true) { hatalar.push("cevap gelmeden kart yolu ACIK (fail-open baslangic)"); }
  if (String(bPay.textContent).indexOf("kontrol ediliyor") === -1) {
    hatalar.push("bekleme metni yok: '" + bPay.textContent + "'");
  }
  bPay.onclick();
  if (b.el("odemeForm").style.display === "block") {
    hatalar.push("cevap gelmeden odeme formu acildi");
  }
  if (b.metin("cartItems").indexOf("kontrol ediliyor") === -1) {
    hatalar.push("satirda 'kontrol ediliyor' bilgisi yok");
  }
  rapor("12 fail-closed (bekliyor/ag/zaman asimi/cop govde/beklenmedik 200/429/celiskili 400)", hatalar,
    (fiksturler.length + 1) + " fikstur: hepsinde kart yolu KAPALI, WhatsApp acik");
}

/** 13 — KARISIK SEPET: odenebilir normal urun + kapali konfigur urunu.
 *  Sunucu sepeti ATOMIK reddediyor (sepetiFiyatla ilk hatali kalemde doner) ve o kapi
 *  gevsetilmiyor -> kismi tahsilat YOK. Bunun yerine musteri SEPETTE, ODEME FORMUNA
 *  GIRMEDEN once hangi satirin kartla alinamadigini ADIYLA gorur, cikis yolu yazilir ve
 *  satiri carpiyla cikarinca kalan urunler KARTLA odenebilir hale gelir. */
async function test13KarisikSepet() {
  const hatalar = [];
  const s = await sayfaKur({
    sepet: [{ id: "gercek-urun", malzeme: "PETG", renk: "Siyah", adet: 1 },
            konfigurSatiri(300, 150000)],
    katalog: [GERCEK, KONFIGUR_URUN],
    prova: provaKapali,
  });
  if (s.satirlar().length !== 2) { hatalar.push("panelde " + s.satirlar().length + " satir (2 olmali)"); }
  if (s.el("cartPay").disabled !== true) { hatalar.push("kapali kalem varken kart yolu ACIK"); }
  const not = String(s.el("cartKonfigurNot").textContent);
  if (not.indexOf(KONFIGUR_URUN.baslik) === -1) {
    hatalar.push("uyari kapali urunu adiyla soylemiyor: '" + not + "'");
  }
  if (not.indexOf("çıkarabilir") === -1) {
    hatalar.push("karisik sepette cikis yolu anlatilmiyor: '" + not + "'");
  }
  if (not.indexOf(GERCEK.baslik) !== -1) {
    hatalar.push("odenebilir urun de kapali gibi gosterilmis");
  }
  // Yalniz KONFIGUR satirinda uyari var (normal satirda yok)
  const uyariliSatir = Array.from(s.satirlar()).filter(
    (r) => govdeMetni(r).indexOf("kartla ödenemiyor") !== -1);
  if (uyariliSatir.length !== 1) {
    hatalar.push(uyariliSatir.length + " satirda 'kartla ödenemiyor' uyarisi (1 olmali)");
  }
  // Kapali satiri carpiyla cikar -> kalan urun KARTLA odenebilir
  const carpi = (uyariliSatir[0] && uyariliSatir[0].children || [])
    .filter((c) => c.tagName === "BUTTON").pop();
  if (!carpi) { hatalar.push("kapali satirda kaldirma carpisi yok"); }
  else {
    carpi.onclick();
    if (s.el("cartPay").disabled !== false) {
      hatalar.push("kapali satir cikarilinca kalan urun HALA odenemiyor");
    }
    if (s.el("cartKonfigurNot").style.display === "block") {
      hatalar.push("satir cikinca uyari duruyor");
    }
  }
  rapor("13 karisik sepet: kapali kalem adiyla ayrilir, cikarinca kalan odenir", hatalar,
    "uyari yalniz konfigur satirinda; carpi sonrasi kart yolu acildi");
}

/** 14 — ISTEK SAYISI OLCUMU (hiz siniri: /fiyat ucunda native binding, 60/dk). Kor istek YOK:
 *  yalniz konfigur satirlari, satir basina EN FAZLA BIR istek; yeniden render 0 istek. */
async function test14IstekSayisi() {
  const hatalar = [];
  // 5 kalemlik sepet: 3 normal (konfigursuz) + 2 FARKLI konfigur satiri (ayni urun, ayri boy).
  const NORMAL2 = Object.assign({}, GERCEK, { id: "gercek-2", baslik: "Test Gercek 2" });
  const NORMAL3 = Object.assign({}, GERCEK, { id: "gercek-3", baslik: "Test Gercek 3" });
  const s = await sayfaKur({
    sepet: [
      { id: "gercek-urun", malzeme: "PLA", renk: "Siyah", adet: 1 },
      { id: "gercek-2", malzeme: "PLA", renk: "Siyah", adet: 1 },
      { id: "gercek-3", malzeme: "PLA", renk: "Siyah", adet: 2 },
      konfigurSatiri(300, 150000),
      konfigurSatiri(200, 90000),
    ],
    katalog: [GERCEK, NORMAL2, NORMAL3, KONFIGUR_URUN],
    prova: provaAcik,
  });
  const sayi = () => s.fetchIzi.filter((f) => f.url.indexOf("/fiyat") !== -1).length;
  const ilk = sayi();
  if (ilk !== 2) {
    hatalar.push("N=5 kalemlik sepette " + ilk + " prova istegi (2 olmali: FARKLI konfigur satiri sayisi)");
  }
  // Panel yeniden cizilince (adet degisimi + panel yeniden acilis) ONBELLEK devrede: 0 yeni istek.
  const adetArti = Array.from(s.satirlar())
    .map((r) => (r.children[1] && r.children[1].children || []))
    .map((kids) => kids.filter((c) => c.className === "cart-adet")[0])
    .filter(Boolean)[0];
  const arti = adetArti && adetArti.children.filter((c) => c.textContent === "+")[0];
  if (!arti || typeof arti.onclick !== "function") {
    // Yeniden render GERCEKTEN olmazsa "0 ek istek" iddiasi bos yere yesil yanar.
    hatalar.push("adet '+' butonu bulunamadi -> yeniden render tetiklenemedi (iddia bos)");
  } else {
    arti.onclick();                         // adetDegistir -> renderCartPanel (tam yeniden cizim)
  }
  s.el("cartFab").onclick && s.el("cartFab").onclick();
  await bekle(20);
  if (s.satirlar().length !== 5) {
    hatalar.push("yeniden render sonrasi " + s.satirlar().length + " satir (5 olmali)");
  }
  if (sayi() !== ilk) {
    hatalar.push("yeniden render " + (sayi() - ilk) + " EK istek attirdi (onbellek calismiyor)");
  }
  // Ayni id'nin FARKLI boyu ayri satirdir -> ayri prova (fiyat/gecerlilik boya bagli).
  const idler = s.fetchIzi.filter((f) => f.url.indexOf("/fiyat") !== -1)
    .map((f) => (JSON.parse(f.opts.body).sepet[0].parametreler || {}).boy_mm).sort();
  if (JSON.stringify(idler) !== JSON.stringify([200, 300])) {
    hatalar.push("provalar boy basina ayrismamis: " + JSON.stringify(idler));
  }
  rapor("14 istek sayisi olcumu (hiz siniri)", hatalar,
    "N=5 sepet / K=2 farkli konfigur satiri -> 2 istek; yeniden render -> 0 ek istek");
}

/** 15 — SINIF BEYANI (tuketici hukuku): odeme ekraninin metni sepetin SINIFINA gore
 *  yaziliyor mu? Bu test GREP DEGIL, GERCEK KOSUM: index.html'in kendi
 *  odemeYontemTazele() / havaleEkraniGoster() fonksiyonlari node:vm icinde cagrilir ve
 *  sahte DOM'daki metin okunur. Beklenen degerler secenekler.js BEYAN TEK KAYNAGINDAN
 *  gelir (elle kopya yok) — cumle degisirse test degil, kaynak degisir.
 *
 *  Neden onemli: hazir/stok urunde 14 gunluk cayma hakki ISLER; ekran "uretim baslar"
 *  derse musteriye ozel uretim teyidi verilmis olur (ters yonde ihlal). Hepsi ozel
 *  uretim olan sepette ise metin BUGUNKU haliyle kalmali (regresyon). */
async function test15SinifBeyani() {
  const hatalar = [];
  const B = SECENEK.BEYAN;
  const FIZIKSEL = { id: "hazir-urun", kategori: "Marin", marka: [], baslik: "Hazir Mal",
    aciklama: "test", fiyat: "1000 TL", gorseller: [], tur: "fiziksel" };
  const satir = (id) => ({ id: id, malzeme: "PLA", renk: "Siyah", adet: 1 });

  // Satir-ici betik bir IIFE'dir; ic fonksiyonlar disaridan CAGIRILAMAZ. Tetik GERCEK
  // kullanici yolu: "Kartla Guvenli Ode" -> odemeFormuGoster(true) -> odemeYontemTazele().
  async function olc(sepet, katalog) {
    const s = await sayfaKur({ sepet: sepet, katalog: katalog });
    s.el("cartPay").onclick();
    if (s.el("odemeForm").style.display !== "block") {
      throw new Error("odeme formu acilmadi — beyan yuzeyi olculemedi");
    }
    return { s: s, havale: s.el("yasalHavale").textContent,
             cayma: s.el("yasalCayma").textContent };
  }

  // (a) hepsi OZEL uretim -> bugunku metin AYNEN, cayma satiri BOS
  const a = await olc([satir(GERCEK.id)], [GERCEK]);
  if (a.havale !== B.ODEME_HAVALE_OZEL) {
    hatalar.push("ozel sepet havale metni degismis: " + JSON.stringify(a.havale.slice(0, 60)));
  }
  if (a.cayma !== "") { hatalar.push("ozel sepette cayma satiri BOS degil: " + a.cayma); }

  // (b) hepsi HAZIR -> uretim dili YOK + 14 gunluk cayma hakki YAZILI
  const b = await olc([satir(FIZIKSEL.id)], [FIZIKSEL]);
  if (b.havale !== B.ODEME_HAVALE_HAZIR) {
    hatalar.push("hazir sepet havale metni sinifli degil: " + JSON.stringify(b.havale.slice(0, 60)));
  }
  if (/üretim|üretil/i.test(b.havale + " " + b.cayma)) {
    hatalar.push("hazir sepette URETIM DILI sizdi: " + b.havale + " | " + b.cayma);
  }
  if (b.cayma !== B.CAYMA_HAZIR) { hatalar.push("hazir sepette cayma beyani yok: " + b.cayma); }

  // (c) KARMA sepet -> iki sinif da soyleniyor
  const c = await olc([satir(GERCEK.id), satir(FIZIKSEL.id)], [GERCEK, FIZIKSEL]);
  if (c.havale !== B.ODEME_HAVALE_KARMA) { hatalar.push("karma sepet havale metni: " + c.havale); }
  if (c.cayma !== B.CAYMA_KARMA) { hatalar.push("karma sepet cayma metni: " + c.cayma); }

  // (d) `tur` EDGE KARTINDAN GECIYOR MU? Edge modunda tarayiciya katalog INMEZ; sepet
  //     paneli urunu YALNIZ kart ozetinden gorur. Alan aynadan duserse sinif sessizce
  //     "ozel"e doner ve (b) yesil YANAMAZ — bu satir o bagi acikca kaydeder.
  if (kartOzeti(FIZIKSEL).tur !== "fiziksel") {
    hatalar.push("edge kart ozeti `tur` tasimiyor — sinif beyani edge modunda olur");
  }

  // NOT (kapsam): havale SONUC kutusu (hvBeyan) ve katalogda bulunamayan satirin
  // fail-closed sinifi bu harness'tan tetiklenemez (biri gercek /baslat cevabi ister,
  // digerinde odeme yolu zaten KILITLIDIR). O iki eksen cayma beyani kapisinda
  // (D5 fail-closed + D6 kablo) olculur.

  rapor("15 sinif beyani (odeme ekrani, gercek DOM kosumu)", hatalar,
    "ozel=bugunku metin · hazir=uretim dili yok + 14 gun · karma=iki sinif · edge kart `tur` tasiyor");
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
  await test10KonfigurKapali();
  await test11KonfigurAcik();
  await test12FailClosed();
  await test13KarisikSepet();
  await test14IstekSayisi();
  await test15SinifBeyani();
  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi" +
    (kalan ? "" : " — HEPSI YESIL ✅"));
  process.exit(kalan ? 1 : 0);
}

main().catch((e) => {
  console.error("\nTEST ALTYAPI HATASI:", e && e.stack || e);
  process.exit(1);
});
