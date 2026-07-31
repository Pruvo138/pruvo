#!/usr/bin/env node
/**
 * PRUVO — ANA SAYFA VITRIN SIRALAMA KABUL TESTI (Okan kurali, 31 Tem 2026)
 *
 *   node tools/vitrin-siralama-test.js
 *
 * KURAL (Okan): "Ev, Dekorasyon, Ofis kategorilerine eklenen urunler ana sayfada ilk 20
 * siradan sonra gosterilsin." Yorum: ana sayfanin ILK 20 KARTINDA bu uc kategoriden urun
 * BULUNMAZ; 21. siradan itibaren normal sekilde gorunurler. Urun ELENMEZ, geri itilir.
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
 * NASIL: index.html'in inline scripti node:vm icinde minimal DOM + URL-duyarli sahte
 * fetch ile GERCEKTEN calistirilir (jenerator/test/vitrin-kabul.js ve
 * shop/test/sepet-panel.js deseni). Kod KOPYALANMAZ — canli dosyanin kendisi kosar.
 *
 * ⚠️ FIKSTUR, CANLI KATALOG DEGIL: bugunku urunler.json'da hedef kategorilerden
 * (Ev 59, Dekorasyon 7, Ofis 4 / 15.210) ilk 28 kartta HIC urun YOK — canli veriyle
 * yazilan bir iddia BOS (vacuous) olurdu ve kural bozulsa bile yesil yanardi. O yuzden
 * her iddia SENTETIK fikstur uzerinde olculur ve fiksturun BOS OLMADIGI ayrica
 * kanitlanir (test 1'in "ham sira" karsi-olcumu).
 *
 * ⚠️ BAGIMSIZ CAPA: hedef kategori adlari ve slot sayisi index.html'den OKUNMAZ, burada
 * ELLE sabittir. Iki taraf ayni kaynaktan okusaydi kural sessizce degistirilebilir ve
 * test yine yesil yanardi ([[kapi-anchor-coupling-ikilemi]]). Kural degisirse bu dosya
 * KIRMIZI yanar ve elle onay ister.
 *
 * NE IDDIA EDILMEZ: arama SEMANTIGI (tek kaynak tools/parite-test.js + parite-ege.js),
 * Worker/D1'in kendi sirasi (pruvo-bot duzlemi), SEO/sitemap.
 *
 * MUTASYON KANITI:  node tools/vitrin-siralama-test.js --index /gecici/mutant-index.html
 * Bayrak YALNIZ hangi index.html'in OLCULDUGUNU degistirir (varsayilan: gercek dosya);
 * hicbir iddiayi gevsetmez. Boylece kural KOPYA uzerinde bozulup her iddianin KIRMIZI
 * yandigi, canli dosyaya DOKUNMADAN kanitlanir.
 */

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const KOK = path.dirname(__dirname);
// --index <yol>: YALNIZ mutasyon kaniti icin (hangi index.html olculecek). Varsayilan
// GERCEK dosya; bayrak hicbir iddiayi gevsetmez.
const _ix = process.argv.indexOf("--index");
const INDEX_YOL = _ix !== -1 && process.argv[_ix + 1]
  ? path.resolve(process.argv[_ix + 1]) : path.join(KOK, "index.html");
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
const HEDEF = ["Ev", "Dekorasyon", "Ofis"];
const SLOT = 20;

const EDGE_UC = (INDEX.match(/var\s+EDGE_UC\s*=\s*"([^"]+)"/) || [])[1];
const PAGE_SIZE = Number((INDEX.match(/var\s+PAGE_SIZE\s*=\s*(\d+)/) || [])[1]);
if (!EDGE_UC || !PAGE_SIZE) {
  console.error("OLCULEMEDI: index.html'de EDGE_UC / PAGE_SIZE bulunamadi.");
  process.exit(2);
}
const hedefMi = (k) => HEDEF.indexOf(k) !== -1;

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
function urun(i, kategori, ek) {
  return Object.assign({
    id: "fx-" + i + "-" + kategori.toLocaleLowerCase("tr").replace(/[^a-z]/g, ""),
    kategori, marka: [], baslik: "Fikstur urun " + i + " " + kategori,
    aciklama: "Fikstur aciklama " + i, fiyat: "100 TL",
    gorseller: ["https://media.pruvo3d.com/urunler/fx-" + i + ".jpg"],
  }, ek || {});
}
function ozetUret(urunler) {
  const kategoriler = {}, markalar = {};
  for (const p of urunler) {
    kategoriler[p.kategori] = (kategoriler[p.kategori] || 0) + 1;
    markalar[p.kategori] = markalar[p.kategori] || {};
  }
  return {
    surum: 1, uretim: "2026-07-31", toplam: urunler.length,
    kategoriler, markalar,
    parametrik: urunler.filter((p) => p.parametrik).map(kart),
    yeni: urunler.slice(0, 48).map(kart),
  };
}

/** FIKSTUR A — "kirli vitrin": hedef kategoriler ham siranin ILK 20 SLOTUNDA, ama
 *  YETERSIZ STOK hali OLUSMADAN (o hal ayri fikstur B'de olculur).
 *
 *  ⚠️ PENCERE HESABI (olculdu): en DAR yuklu pencere Worker beslemeli yol —
 *  ozet.json inmezse /katalog?sayfa=1&boy=24 yalnizca 24 kart getirir (sari vitrinin
 *  4 karti YOK). Ilk 20 slotu hedef-disi doldurabilmek icin bu 24'luk pencerede en
 *  fazla 4 hedef urun olabilir. Fikstur 3 tane koyar (indeks 0,2,4 -> ham cizimde
 *  1.,3.,5. / ozet yolunda 5.,7.,9. slot) + pencere DISINDA 2 tane (30, 40) daha.
 */
function fiksturA() {
  const doldur = ["Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat",
    "Elektronik", "Kamera", "Bahçe", "Oyun/Hobi"];
  const liste = [];
  for (let i = 0; i < 48; i++) {
    if (i < 6 && i % 2 === 0) { liste.push(urun(i, HEDEF[i % HEDEF.length])); }
    else if (i === 30 || i === 40) { liste.push(urun(i, HEDEF[i % HEDEF.length])); }
    else { liste.push(urun(i, doldur[i % doldur.length])); }
  }
  for (let i = 48; i < 52; i++) {
    liste.push(urun(i, "Jeneratör", { parametrik: true, fiyat: "" }));
  }
  return liste;
}

/** FIKSTUR C — bayrak-kapali (HOME_ORDER) yolu icin. HOME_ORDER "her kategoriden birer
 *  sira (4 urun)" kurdugu icin hedef kategoriler ancak ONCEKI kategoriler AZ urunluyse
 *  ilk 20 slota girer (CATEGORIES sirasi: Marin, Otomobil, Motosiklet, Bisiklet, Tamirat,
 *  EV, OFIS, ...). Olculdu: fikstur A ile bu yol VACUOUS'tu — sirali dolgu zaten ilk 20'yi
 *  hedef-disi dolduruyordu ve kural kaldirilinca test yine YESIL yaniyordu (M2 sag kaldi).
 *  Burada ilk bes kategoriye 2'ser urun konur -> Ev satiri 15. slottan baslar. */
function fiksturC() {
  const liste = [];
  let i = 0;
  const ekle = (kategori, adet, ek) => {
    for (let n = 0; n < adet; n++) { liste.push(urun(i++, kategori, ek)); }
  };
  ekle("Marin", 2); ekle("Otomobil", 2); ekle("Motosiklet", 2);
  ekle("Bisiklet", 2); ekle("Tamirat", 2);
  ekle("Ev", 4); ekle("Ofis", 3);
  ekle("Elektronik", 4); ekle("Kamera", 4); ekle("Bahçe", 4);
  ekle("Dekorasyon", 3); ekle("Oyun/Hobi", 4);
  ekle("Jeneratör", 4, { parametrik: true, fiyat: "" });
  return liste;
}

/** FIKSTUR B — YETERSIZ STOK: yuklu pencerede 20'den az hedef-disi urun. */
function fiksturB() {
  const liste = [];
  for (let i = 0; i < 30; i++) {
    liste.push(urun(i, i < 5 ? "Marin" : HEDEF[i % HEDEF.length]));
  }
  // hedef-disi 5 urun ilk 5 sirada; kalan 25 hepsi hedef kategoride
  return liste;
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
 *   ayar.urunler    fikstur katalogu
 *   ayar.search     location.search
 *   ayar.ozetDusur  true ise ozet.json 404 doner (Worker beslemeli yol)
 *   ayar.ucDusur    true ise /katalog + /ara 500 doner (edgeYedek yolu)
 *   ayar.bayrak     "kapali" ise EDGE_KATALOG=false kolunu kosar
 *
 * Donen nesne: kartlari OKUR (oku()), "Daha fazla goster"i TIKLAR (dahaFazla()) ve
 * Worker'i CALISIRKEN dusurur (ucDusur(true)) — edgeYedek yolu ancak boyle uyanir.
 */
async function sayfaKur(ayar) {
  const urunler = ayar.urunler;
  const OZET = ozetUret(urunler);
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
  // fiksturun BOS OLMADIGINI (kural olmasaydi ilk 20'de hedef VAR) kanitlamak icin.
  // Canli dosyaya DOKUNULMAZ. Capalar bulunamazsa OLCULEMEDI (fail-closed): kural
  // sokulmusse bu kol sessizce "kuralsizla ayni" diye yesil yanamaz.
  if (ayar.kuralsiz) {
    const capalar = [
      ["cizilecek = anaGorunum ? vitrinSirala(edgeListe) : edgeListe;", "cizilecek = edgeListe;"],
      ["if(anaGorunum){ list = vitrinSirala(list); }", "if(false){ list = vitrinSirala(list); }"],
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
  // ZARIF BOZULMA senaryolarinda index.html BILEREK console.error basar (ozet.json 404 /
  // Worker 500). O metinler BEKLENIR; BASKA her console.error olcumu GECERSIZ kilar
  // (sessiz yesil olmasin) -> OLCULEMEDI ile patlar.
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
    return {
      kartlar,
      sapma: ctx.PRUVO_VITRIN_SAPMA || null,
      uyarilar: uyarilar.slice(),
      sayimMetni: belge.getElementById("resultCount").textContent,
      baslik: belge.getElementById("sectionTitle").textContent,
      istekler: istekler.slice(),
    };
  }

  for (let i = 0; i < 10; i++) { await bekle(15); }
  hatalariDenetle();

  const s = oku();
  s.oku = oku;
  s.ucDusur = (v) => { durum.ucDusur = !!v; };
  /** "Daha fazla goster" butonunu GERCEKTEN tiklar (loadMoreWrap'taki tek buton). */
  s.dahaFazla = async () => {
    const btn = belge.getElementById("loadMoreWrap").children[0];
    if (!btn || typeof btn.onclick !== "function") {
      throw new Error("OLCULEMEDI: 'Daha fazla goster' butonu YOK (dahaVar hesabi degismis?)");
    }
    btn.onclick();
    for (let i = 0; i < 10; i++) { await bekle(15); }
    return oku();
  };
  return s;
}

// ------------------------------------------------------- IDDIA DENETCILERI (saf fonksiyon)
// Her denetci hem GERCEK ciktiya (POZITIF vaka) hem SENTETIK BOZUK ciktiya (NEGATIF vaka)
// uygulanir. Negatif vakada hata URETMEYEN denetci OLU IDDIA sayilir -> test KIRMIZI.

/** A: ilk SLOT kartta hedef kategori 0 olmali. */
function denetA(kartlar) {
  const h = [];
  kartlar.slice(0, SLOT).forEach((k, i) => {
    if (hedefMi(k.kategori)) { h.push("slot " + (i + 1) + " = " + k.kategori); }
  });
  return h;
}
/** B: hedef kategoriler ELENMEMIS — ham listede varsa cizimde 21+ arasinda GORUNMELI. */
function denetB(kartlar, hamKategoriler) {
  const hamHedef = hamKategoriler.filter(hedefMi).length;
  if (hamHedef === 0) { return ["kontrol edilemez: ham listede hic hedef kategori yok"]; }
  const geride = kartlar.slice(SLOT).filter((k) => hedefMi(k.kategori)).length;
  return geride === hamHedef ? []
    : ["21+ arasinda hedef kategori " + geride + " (beklenen " + hamHedef + ") — urun ELENMIS"];
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
  return h;
}
/** F: KARARLILIK — siralayici yalnizca hedefleri geri iter, BASKA HICBIR SEYI karistirmaz:
 *  hedef-disi urunlerin kendi arasindaki goreli sirasi ve hedeflerin kendi arasindaki
 *  goreli sirasi ham beslemeyle AYNI kalir. (Kural "urunler kaldirilmiyor, yalniz vitrin
 *  sirasi degisiyor" -> en yeni urun ilk sirada kalmali.) */
function denetF(kartlar, ham) {
  const h = [];
  const hedefIdler = new Set(ham.filter((k) => hedefMi(k.kategori)).map((k) => k.id));
  const hamKume = new Set(ham.map((k) => k.id));
  const suz = (idler, hedefMiIstenen) =>
    idler.filter((id) => hedefIdler.has(id) === hedefMiIstenen).join("|");
  // Referansta OLMAYAN kartlar (sari vitrin: edgeVitrin havuzdan RASTGELE 4 secer)
  // kararlilik olcumunun disinda tutulur — o rastgelelik bugunku KASITLI davranis.
  const cizim = kartlar.map((k) => k.id).filter((id) => hamKume.has(id));
  const hamIdler = ham.map((k) => k.id);
  if (suz(cizim, false) !== suz(hamIdler, false)) {
    h.push("hedef-DISI urunlerin goreli sirasi DEGISTI (kararsiz siralama)");
  }
  if (suz(cizim, true) !== suz(hamIdler, true)) {
    h.push("hedef urunlerin goreli sirasi DEGISTI");
  }
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
  console.log("PRUVO ana sayfa vitrin siralama kabulu — hedef " + JSON.stringify(HEDEF) +
    ", ilk " + SLOT + " slot");
  console.log("olculen index.html: " + INDEX_YOL);

  const A = fiksturA();
  const ozetA = ozetUret(A);

  // ---- 0: TEK KAYNAK + sabitler (kural koda tek yerde yazilmis mi)
  {
    const h = [];
    const bildirim = INDEX.match(/var\s+VITRIN_GERI_KATEGORILER\s*=\s*(\[[^\]]*\])\s*;/g) || [];
    if (bildirim.length !== 1) {
      h.push("VITRIN_GERI_KATEGORILER bildirimi " + bildirim.length + " kez (TEK olmali)");
    } else {
      let adlar = null;
      try { adlar = JSON.parse(bildirim[0].replace(/^[^[]*/, "").replace(/\s*;\s*$/, "")); }
      catch (e) { h.push("VITRIN_GERI_KATEGORILER okunamadi: " + e.message); }
      if (adlar) {
        if (adlar.slice().sort().join("|") !== HEDEF.slice().sort().join("|")) {
          h.push("kategori listesi " + JSON.stringify(adlar) + " != " + JSON.stringify(HEDEF));
        }
        const kats = JSON.parse((INDEX.match(/var\s+CATEGORIES\s*=\s*(\[[^\]]*\])\s*;/) || [])[1]);
        for (const a of adlar) {
          if (kats.indexOf(a) === -1) { h.push("'" + a + "' CATEGORIES'te YOK"); }
        }
      }
    }
    const slot = Number((INDEX.match(/var\s+VITRIN_ON_SLOT\s*=\s*(\d+)\s*;/) || [])[1]);
    if (slot !== SLOT) { h.push("VITRIN_ON_SLOT=" + slot + " (beklenen " + SLOT + ")"); }
    // ikinci kopya avi: uc adin BIRLIKTE gectigi baska bir dizi literali olmasin
    const kopya = (INDEX.match(/\[\s*"Ev"\s*,\s*"Dekorasyon"\s*,\s*"Ofis"\s*\]/g) || []).length;
    if (kopya !== 1) { h.push("hedef kategori literali " + kopya + " kez (TEK kopya olmali)"); }
    rapor("0 tek kaynak: VITRIN_GERI_KATEGORILER tek bildirim, CATEGORIES ile tutarli", h,
      "slot=" + slot);
  }

  // ---- 1: ozet.json yolu (ziyaretcinin GORDUGU ana yol) — ilk 20'de hedef 0
  const hamA = [].concat(ozetA.parametrik.slice(0, 4), ozetA.yeni.slice(0, PAGE_SIZE));
  const hamKatA = hamA.map((k) => k.kategori);
  const hamIdA = hamA.map((k) => k.id);
  const hamIlk20Hedef = hamKatA.slice(0, SLOT).filter(hedefMi).length;
  {
    const h = [];
    if (hamIlk20Hedef === 0) {
      h.push("FIKSTUR BOS: ham sirada ilk " + SLOT + " slotta zaten hedef yok — iddia vacuous");
    }
    rapor("1a fikstur bos degil: kuralsiz cizimde ilk 20'de hedef kategori VAR", h,
      hamIlk20Hedef + " adet");
  }
  const s1 = await sayfaKur({ urunler: A });
  rapor("1b ozet.json yolu: ilk " + SLOT + " slotta hedef kategori 0", denetA(s1.kartlar),
    s1.kartlar.length + " kart cizildi");
  rapor("1c ozet.json yolu: hedef urunler 21+ arasinda GORUNUYOR (elenmemis)",
    denetB(s1.kartlar, hamKatA),
    s1.kartlar.slice(SLOT).filter((k) => hedefMi(k.kategori)).length + " adet 21+ arasinda");
  rapor("1d ozet.json yolu: cizim ham listenin permutasyonu (eleme yok)",
    denetC(s1.kartlar, hamIdA), s1.kartlar.length + " kart");
  // Kararlilik, ozet.json'un DETERMINISTIK bolumu (yeni listesi) uzerinde olculur.
  rapor("1f ozet.json yolu: KARARLI — hedef-disi urunlerin goreli sirasi korundu",
    denetF(s1.kartlar, ozetA.yeni.slice(0, PAGE_SIZE)));
  {
    const h = [];
    const beklenen = String(A.length) + " ürün";
    if (s1.sayimMetni !== beklenen) {
      h.push("resultCount '" + s1.sayimMetni + "' (beklenen '" + beklenen + "')");
    }
    rapor("1e katalog toplami DEGISMEDI", h, s1.sayimMetni);
  }

  // ---- 2: NEGATIF vakalar — denetciler bozuk ciktida KIRMIZI yanmali
  {
    const bozukA = hamA.map((k) => ({ kategori: k.kategori, id: k.id })); // kuralsiz ham sira
    negatif("A denetcisi: kuralsiz ham sirada hedef ilk 20'de", denetA(bozukA));
    const elenmis = s1.kartlar.filter((k) => !hedefMi(k.kategori));
    negatif("B denetcisi: hedefler tamamen ELENMIS cikti", denetB(elenmis, hamKatA));
    negatif("C denetcisi: kart sayisi degismis cikti", denetC(s1.kartlar.slice(1), hamIdA));
    negatif("D denetcisi: sirasi bozulmus kategori gorunumu",
      denetD(s1.kartlar.slice().reverse(), s1.kartlar.map((k) => k.id)));
    negatif("E denetcisi: yetersiz stok olcumu YOKKEN", denetE(null, [], false));
    negatif("E denetcisi: yetersiz stok SESSIZ gecmis",
      denetE({ yetersiz: true }, [], true));
    negatif("F denetcisi: goreli sirasi TERS cevrilmis cizim",
      denetF(s1.kartlar.slice().reverse(), hamA));
  }

  // ---- 3: Worker beslemeli yol (ozet.json inmedi) — kural BURADA da gecerli
  {
    const s = await sayfaKur({ urunler: A, ozetDusur: true });
    const ham = A.slice(0, PAGE_SIZE).map(kart);
    const h = denetA(s.kartlar);
    const geride = s.kartlar.slice(SLOT).filter((k) => hedefMi(k.kategori)).length;
    if (geride === 0) { h.push("21+ arasinda hedef YOK (Worker yolunda elenmis olabilir)"); }
    rapor("3a Worker /katalog yolu: ilk " + SLOT + " slotta hedef 0, 21+ dolu", h,
      s.kartlar.length + " kart, 21+ hedef " + geride);
    rapor("3b Worker /katalog yolu: permutasyon (eleme yok) + KARARLI",
      denetC(s.kartlar, ham.map((k) => k.id)).concat(denetF(s.kartlar, ham)));
  }

  // ---- 4: edgeYedek yolu (ozet.json indi, sonra Worker dustu) — kural BURADA da gecerli.
  // ANA SAYFADA edgeYedek ancak "Daha fazla goster" ile uyanir (ilk boyama aga cikmaz):
  // buton GERCEKTEN tiklanir, Worker 500 doner, sayfa ozet havuzuna duser.
  {
    const s = await sayfaKur({ urunler: A });
    s.ucDusur(true);
    const y = await s.dahaFazla();
    const h = denetA(y.kartlar);
    const geride = y.kartlar.slice(SLOT).filter((k) => hedefMi(k.kategori)).length;
    if (geride === 0) { h.push("21+ arasinda hedef YOK (yedek havuzda elenmis olabilir)"); }
    rapor("4 edgeYedek yolu (Worker 500): ilk " + SLOT + " slotta hedef 0, 21+ dolu", h,
      y.kartlar.length + " kart, 21+ hedef " + geride);
  }

  // ---- 5: EDGE_KATALOG=false yolu (bayrak geri alinirsa) — kural BURADA da gecerli.
  // HOME_ORDER kategori-siralari kurdugu icin hedef urunler dogal olarak 24. karttan
  // SONRAYA dusebilir; "elenmedi" iddiasi sayfa BUYUTULEREK (daha fazla goster) olculur.
  {
    const C = fiksturC();
    // 5a — FIKSTUR BOS DEGIL (karsi-olcum): kural DEVRE DISI birakilmis bir KOPYADA
    // hedefler HOME_ORDER'in ilk 20'sine giriyor mu? Bu olcum olmadan M2 mutanti
    // ("bayrak-kapali kolda siralayici cagrilmiyor") SAG KALIYORDU: fikstur A'da sirali
    // kategori dolgusu ilk 20'yi zaten hedef-disi dolduruyor, iddia VACUOUS oluyordu.
    const kuralsiz = await sayfaKur({ urunler: C, bayrak: "kapali", kuralsiz: true });
    const kirli = kuralsiz.kartlar.slice(0, SLOT).filter((k) => hedefMi(k.kategori)).length;
    rapor("5a fikstur bos degil: kuralsiz HOME_ORDER'da ilk 20'de hedef VAR",
      kirli === 0 ? ["FIKSTUR BOS: kuralsiz cizimde de ilk 20'de hedef yok — iddia vacuous"] : [],
      kirli + " adet");

    const s = await sayfaKur({ urunler: C, bayrak: "kapali" });
    const h = denetA(s.kartlar);
    const g = await s.dahaFazla();
    h.push.apply(h, denetA(g.kartlar));
    const geride = g.kartlar.slice(SLOT).filter((k) => hedefMi(k.kategori)).length;
    const hepsi = C.filter((u) => hedefMi(u.kategori)).length;
    if (geride !== hepsi) {
      h.push("21+ arasinda hedef " + geride + " (beklenen " + hepsi + ") — ELENMIS");
    }
    rapor("5b bayrak-kapali (HOME_ORDER) yolu: ilk " + SLOT + " slotta hedef 0, 21+ dolu", h,
      g.kartlar.length + " kart, 21+ hedef " + geride + "/" + hepsi);
  }

  // ---- 6: KATEGORI GORUNUMU DEGISMEDI (?kategori=Ev)
  {
    const beklenen = A.filter((u) => u.kategori === "Ev").slice(0, PAGE_SIZE).map((u) => u.id);
    const s = await sayfaKur({ urunler: A, search: "?kategori=Ev" });
    const h = denetD(s.kartlar, beklenen);
    if (s.baslik !== "Ev Ürünleri") { h.push("baslik '" + s.baslik + "'"); }
    if (s.kartlar.some((k) => !hedefMi(k.kategori))) { h.push("Ev disi urun sizdi"); }
    rapor("6 kategori gorunumu (?kategori=Ev) ETKILENMEDI", h, s.kartlar.length + " Ev karti");
  }

  // ---- 7: ARAMA SONUCLARI DEGISMEDI
  {
    const q = "Fikstur urun 4";   // 4 (Dekorasyon) + 40..47 -> hedef kategori SONUCLARDA var
    const beklenen = A.filter((u) => (u.baslik || "").toLocaleLowerCase("tr")
      .indexOf(q.toLocaleLowerCase("tr")) !== -1).slice(0, PAGE_SIZE).map((u) => u.id);
    const s = await sayfaKur({ urunler: A, search: "?ara=" + encodeURIComponent(q) });
    const h = denetD(s.kartlar, beklenen);
    if (beklenen.length === 0) { h.push("fikstur bos: arama hic sonuc dondurmuyor"); }
    if (!beklenen.some((id) => hedefMi(A.find((u) => u.id === id).kategori))) {
      h.push("fikstur zayif: arama sonucunda hic hedef kategori yok");
    }
    rapor("7 arama gorunumu ETKILENMEDI (hedef kategoriler sonuclarda, sirasi bozulmadan)", h,
      s.kartlar.length + " sonuc");
  }

  // ---- 8: YETERSIZ STOK — bosluk YOK, sapma OLCULUP BASILDI
  {
    const B = fiksturB();
    const s = await sayfaKur({ urunler: B });
    const h = denetE(s.sapma, s.uyarilar, true);
    if (s.kartlar.length !== Math.min(B.length, PAGE_SIZE)) {
      h.push("bosluk birakilmis: " + s.kartlar.length + " kart (beklenen " +
        Math.min(B.length, PAGE_SIZE) + ")");
    }
    if (s.sapma && s.sapma.uygun !== 5) {
      h.push("sapma.uygun=" + s.sapma.uygun + " (beklenen 5)");
    }
    rapor("8a yetersiz stok: bosluk YOK + sapma OLCULDU ve BASILDI", h,
      s.sapma ? ("uygun " + s.sapma.uygun + "/" + s.sapma.slot + ", liste " + s.sapma.liste) : "-");
    rapor("8b normal fiksturde YANLIS ALARM yok", denetE(s1.sapma, s1.uyarilar, false),
      s1.sapma ? ("uygun " + s1.sapma.uygun + "/" + s1.sapma.slot) : "-");
  }

  // ---- 9: CANLI KATALOG OLCUMU (bilgi + sessiz sapma nobeti)
  {
    const h = [];
    const yol = path.join(KOK, "urunler.json");
    let bilgi = "";
    if (!fs.existsSync(yol)) {
      h.push("OLCULEMEDI: urunler.json yok");
    } else {
      const canli = JSON.parse(fs.readFileSync(yol, "utf8"));
      const param = canli.filter((u) => u.parametrik).length;
      const pencere = canli.slice(0, PAGE_SIZE);
      const uygun = pencere.filter((u) => !hedefMi(u.kategori)).length + Math.min(param, 4);
      bilgi = "ilk " + PAGE_SIZE + " urunde hedef " +
        pencere.filter((u) => hedefMi(u.kategori)).length +
        ", pencerede hedef-disi " + uygun;
      if (uygun < SLOT) {
        h.push("CANLI YETERSIZ STOK: yuklu pencerede hedef-disi " + uygun + " < " + SLOT +
          " — ilk 20'nin bir kismi hedef kategoriyle dolacak (kural sinirinda)");
      }
    }
    rapor("9 canli katalog: yuklu pencerede yeterli hedef-disi urun var", h, bilgi);
  }

  console.log("\nSONUC: " + gecen + " gecti, " + kalan + " kaldi");
  process.exit(kalan === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("OLCULEMEDI / ALTYAPI HATASI: " + ((e && e.stack) || e));
  process.exit(2);
});
