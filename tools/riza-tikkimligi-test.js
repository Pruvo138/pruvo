#!/usr/bin/env node
/**
 * KABUL TESTI — RIZASIZ TIKLAMA KIMLIGI SIZINTISI (KVKK).
 *
 *   node tools/riza-tikkimligi-test.js
 *
 * Neyi kanitlar (mimar karari, 20 Tem):
 *   1) Riza YOKKEN URL'deki tiklama kimligi (fbclid / gclid / gbraid / wbraid) HICBIR depoya
 *      yazilmaz. Anahtar adi TAHMIN EDILMEZ: tum localStorage + sessionStorage + document.cookie
 *      alt-dize taranir; ham deger nerede olursa olsun yakalanir.
 *   2) Riza VARKEN eskisi gibi saklanir ve olcum/attribution akisi bozulmaz.
 *   3) Riza SONRADAN verilirse (banner "Kabul Et") sayfa yenilenmeden yakalanir.
 *   4) Riza GERI CEKILIRSE saklanmis tiklama kimligi SILINIR.
 *   5) GERIYE DONUK: rizasiz tarayicida onceden yazilmis deger, kod ilk kez kosunca silinir.
 *
 * Kapsam iki dosya: index.html (PRUVO_ATIF -> fbclid/fbc) + attribution-ref.js (gclid/gbraid/
 * wbraid; urun + statik sayfalara build.py inline basar).
 *
 * NEDEN ELDE YAZILMIS MINI-DOM: repoda npm bagimliligi YOK (parite testleri + faz3-bayrak.js de
 * saf Node) ve is paketi yeni kutuphane yasakliyor. Kaynak GERCEK dosyalardan cikarilir (kopya
 * degil) -> index.html/attribution-ref.js degisince test onlari okur.
 */

"use strict";

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const KOK = path.dirname(__dirname);
const INDEX = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const REF_JS = fs.readFileSync(path.join(KOK, "attribution-ref.js"), "utf8");
const GIZ = fs.readFileSync(path.join(KOK, "gizlilik", "index.html"), "utf8");
const BUILD_PY = fs.readFileSync(path.join(KOK, "tools", "build.py"), "utf8");

let passed = 0;
const hatalar = [];

function assert(kosul, mesaj) {
  if (!kosul) { throw new Error(mesaj); }
}

function senaryo(ad, fn) {
  try {
    fn();
    passed += 1;
    console.log("  ok  " + ad);
  } catch (error) {
    hatalar.push(ad + ": " + error.message);
    console.error("FAIL " + ad + ": " + error.message);
  }
}

// ─── index.html'den calisan kod parcalarini CIKAR (kopya tutma) ───────────────
function dilim(metin, baslangicIsareti, bitisIsareti, ad) {
  const i = metin.indexOf(baslangicIsareti);
  assert(i !== -1, ad + ": baslangic isareti bulunamadi -> " + baslangicIsareti);
  const j = metin.indexOf(bitisIsareti, i);
  assert(j !== -1, ad + ": bitis isareti bulunamadi -> " + bitisIsareti);
  return metin.slice(i, j);
}

const ATIF_SRC = dilim(INDEX, "var PRUVO_ATIF = (function(){",
                       "\n  function placeholder(txt){", "PRUVO_ATIF");
assert(ATIF_SRC.indexOf("window.pruvoAtifRiza") !== -1,
       "PRUVO_ATIF dilimi window.pruvoAtifRiza kancasini icermiyor");
assert(ATIF_SRC.indexOf("pruvo_onay_analitik") !== -1,
       "PRUVO_ATIF dilimi riza anahtarini icermiyor (kapi yok!)");

// Cerez banner'i: <div id="pruvo-cerez-onay"> sonrasindaki ilk <script> blogu.
function bannerCikar(html, ad) {
  const d = html.indexOf('id="pruvo-cerez-onay"');
  assert(d !== -1, ad + ": banner div bulunamadi");
  const s = html.indexOf("<script>", d);
  const e = html.indexOf("</script>", s);
  assert(s !== -1 && e !== -1, ad + ": banner script blogu bulunamadi");
  const src = html.slice(s + "<script>".length, e);
  assert(src.indexOf("pco-kabul") !== -1, ad + ": banner dilimi yanlis blogu aldi");
  return src;
}
const BANNER_SRC = bannerCikar(INDEX, "index.html");
const GIZ_BANNER_SRC = bannerCikar(GIZ, "gizlilik/index.html");
assert(GIZ.indexOf('id="pco-degistir"') !== -1,
       "gizlilik sayfasinda riza geri alma dugmesi (#pco-degistir) YOK");

// ─── mini ortam ──────────────────────────────────────────────────────────────
function Depo(baslangic) {
  this.data = Object.assign({}, baslangic || {});
}
Depo.prototype.getItem = function (k) {
  return Object.prototype.hasOwnProperty.call(this.data, k) ? this.data[k] : null;
};
Depo.prototype.setItem = function (k, v) { this.data[k] = String(v); };
Depo.prototype.removeItem = function (k) { delete this.data[k]; };

function Oge(id) {
  this.id = id; this.hidden = false; this.dinleyici = {};
  this.addEventListener = (ad, fn) => { this.dinleyici[ad] = fn; };
  this.focus = () => {};
  this.checked = false;
}

/**
 * Cerez kavanozu: `document.cookie = "..."` tarayicidaki gibi TEK cerezi ekler/gunceller,
 * gecmis tarihli expires/max-age ise SILER (duz string olsa silme testi anlamsiz olurdu).
 */
function Kavanoz(baslangic) {
  this.map = {};
  String(baslangic || "").split(";").forEach((p) => {
    const t = p.trim();
    const i = t.indexOf("=");
    if (i > 0) { this.map[t.slice(0, i).trim()] = t.slice(i + 1); }
  });
}
Kavanoz.prototype.metin = function () {
  return Object.keys(this.map).map((k) => k + "=" + this.map[k]).join("; ");
};
Kavanoz.prototype.yaz = function (s) {
  const parcalar = String(s).split(";");
  const i = parcalar[0].indexOf("=");
  if (i <= 0) { return; }
  const ad = parcalar[0].slice(0, i).trim();
  const deger = parcalar[0].slice(i + 1);
  let silme = false;
  for (let j = 1; j < parcalar.length; j++) {
    const o = parcalar[j].trim();
    const kucuk = o.toLowerCase();
    if (kucuk.indexOf("max-age=") === 0 && Number(kucuk.slice(8)) <= 0) { silme = true; }
    if (kucuk.indexOf("expires=") === 0) {
      const t = Date.parse(o.slice(8));
      if (!isNaN(t) && t <= Date.now()) { silme = true; }
    }
  }
  if (silme) { delete this.map[ad]; } else { this.map[ad] = deger; }
};

/** Kavanozu `document.cookie` get/set'ine bagli bir belge nesnesine cevirir. */
function belgeYap(kavanoz, ekler) {
  const belge = Object.assign({ readyState: "complete" }, ekler || {});
  Object.defineProperty(belge, "cookie", {
    get: () => kavanoz.metin(),
    set: (v) => kavanoz.yaz(v),
    enumerable: true
  });
  return belge;
}

function tikla(oge) {
  assert(typeof oge.dinleyici.click === "function", oge.id + " click dinleyicisi yok");
  oge.dinleyici.click({});
}

/**
 * index.html'in atif katmanini (istege bagli olarak banner'i da) tek bir sayfa yuklemesi
 * gibi calistirir. depo paylasilabilir -> "sonraki sayfa yuklemesi" simule edilir.
 */
function sayfa(opts) {
  opts = opts || {};
  const depo = opts.depo || new Depo();
  if (opts.onay) { depo.setItem("pruvo_onay_analitik", opts.onay); }
  const oturum = opts.oturum || new Depo();
  const ogeler = {
    "pruvo-cerez-onay": new Oge("pruvo-cerez-onay"),
    "pco-kabul": new Oge("pco-kabul"),
    "pco-ret": new Oge("pco-ret")
  };
  const kavanoz = opts.kavanoz || new Kavanoz(opts.cookie || "");
  const ctx = {
    window: {},
    document: belgeYap(kavanoz, { getElementById: (id) => ogeler[id] || null }),
    localStorage: depo,
    sessionStorage: oturum,
    location: { search: opts.search || "", hostname: "pruvo3d.com",
                href: "https://pruvo3d.com/" + (opts.search || "") },
    URL: URL,
    URLSearchParams: URLSearchParams,
    Date: Date,
    JSON: JSON,
    String: String,
    console: opts.konsol || console
  };
  ctx.window.localStorage = depo;
  vm.runInNewContext(ATIF_SRC + "\n;window.__ATIF = PRUVO_ATIF;", ctx,
                     { filename: "index.html#PRUVO_ATIF" });
  if (opts.banner) {
    vm.runInNewContext(BANNER_SRC, ctx, { filename: "index.html#banner" });
  }
  return { ctx, depo, oturum, ogeler, kavanoz,
           atif: ctx.window.__ATIF,
           riza: ctx.window.pruvoAtifRiza };
}

/**
 * gizlilik/ sayfasinin YAYINDAKI hâli gibi kosar: build.py bu sayfaya attribution-ref.js'i
 * inline basiyor (isaretli blok) -> once GUNCEL modul, sonra sayfanin kendi banner script'i.
 * PRUVO_ATIF bu sayfada YOK (yalniz ana sayfada) — geri alma yolunun ana sayfaya ugramadan da
 * calismasi gerektigi gercek kosul.
 */
function gizlilikSayfa(opts) {
  opts = opts || {};
  const depo = opts.depo || new Depo();
  if (opts.onay) { depo.setItem("pruvo_onay_analitik", opts.onay); }
  const oturum = opts.oturum || new Depo();
  const kavanoz = opts.kavanoz || new Kavanoz(opts.cookie || "");
  const ogeler = {
    "pruvo-cerez-onay": new Oge("pruvo-cerez-onay"),
    "pco-kabul": new Oge("pco-kabul"),
    "pco-ret": new Oge("pco-ret"),
    "pco-degistir": new Oge("pco-degistir")
  };
  const baglantilar = (opts.linkler || []).map((h) => new Baglanti(h));
  const dinleyiciler = {};
  const beacons = [];
  let cagri = 0;
  const metaBaslatildi = [];
  const ctx = {
    window: { pruvoMetaBaslat: () => { metaBaslatildi.push(1); } },
    document: belgeYap(kavanoz, {
      getElementById: (id) => ogeler[id] || null,
      querySelectorAll: () => baglantilar,
      addEventListener: (ad, fn) => { dinleyiciler[ad] = fn; }
    }),
    localStorage: depo,
    sessionStorage: oturum,
    location: { search: opts.search || "", hostname: "pruvo3d.com",
                href: "https://pruvo3d.com/gizlilik/" + (opts.search || "") },
    navigator: {
      sendBeacon: (url, blob) => {
        beacons.push({ url, body: blob && blob.parts && blob.parts[0] });
        return true;
      }
    },
    Blob: function (parts, o) { this.parts = parts; this.type = (o && o.type) || ""; },
    crypto: { getRandomValues: (b) => {
      cagri += 1;
      for (let i = 0; i < b.length; i++) { b[i] = (cagri * 17 + i * 53) % 256; }
      return b;
    } },
    URL: URL, URLSearchParams: URLSearchParams, Uint8Array: Uint8Array,
    Date: Date, JSON: JSON, String: String, console: console
  };
  vm.runInNewContext(REF_JS, ctx, { filename: "attribution-ref.js (gizlilik inline)" });
  vm.runInNewContext(GIZ_BANNER_SRC, ctx, { filename: "gizlilik/index.html#banner" });
  return { ctx, depo, oturum, ogeler, kavanoz, beacons, metaBaslatildi,
           banner: ogeler["pruvo-cerez-onay"],
           tikla: (i) => dinleyiciler.click({ target: baglantilar[i || 0] }) };
}

/** attribution-ref.js'i tek sayfa yuklemesi gibi calistirir (REF + gclid katmani). */
function Baglanti(href) {
  this.attrs = { href: href }; this.tagName = "A"; this.parentNode = null;
}
Baglanti.prototype.getAttribute = function (n) { return this.attrs[n] || null; };
Baglanti.prototype.setAttribute = function (n, v) { this.attrs[n] = String(v); };

function refSayfa(opts) {
  opts = opts || {};
  const depo = opts.depo || new Depo();
  if (opts.onay) { depo.setItem("pruvo_onay_analitik", opts.onay); }
  const oturum = opts.oturum || new Depo();
  const baglantilar = (opts.linkler || []).map((h) => new Baglanti(h));
  const dinleyiciler = {};
  const beacons = [];
  let cagri = 0;
  const ctx = {
    window: {},
    document: {
      readyState: "complete",
      cookie: opts.cookie || "",
      querySelectorAll: () => baglantilar,
      addEventListener: (ad, fn) => { dinleyiciler[ad] = fn; }
    },
    localStorage: depo,
    sessionStorage: oturum,
    location: { search: opts.search || "",
                href: "https://pruvo3d.com/" + (opts.search || "") },
    navigator: {
      sendBeacon: (url, blob) => {
        beacons.push({ url, body: blob && blob.parts && blob.parts[0] });
        return true;
      }
    },
    Blob: function (parts, o) { this.parts = parts; this.type = (o && o.type) || ""; },
    crypto: { getRandomValues: (b) => {
      cagri += 1;
      for (let i = 0; i < b.length; i++) { b[i] = (cagri * 17 + i * 53) % 256; }
      return b;
    } },
    URL: URL,
    URLSearchParams: URLSearchParams,
    Uint8Array: Uint8Array,
    Date: Date,
    JSON: JSON,
    String: String
  };
  vm.runInNewContext(REF_JS, ctx, { filename: "attribution-ref.js" });
  return { ctx, depo, oturum, baglantilar, beacons, dinleyiciler,
           ref: () => ctx.window.pruvoRef(),
           riza: ctx.window.pruvoRefRiza,
           tikla: (i) => dinleyiciler.click({ target: baglantilar[i || 0] }) };
}

/**
 * TUM istemci depolarini (localStorage + sessionStorage + cookie) tarar ve ham degeri
 * ALT-DIZE olarak arar. Anahtar adi tahmin edilmez -> kod yeni bir anahtara yazsa da yakalanir.
 */
function depodaGecenler(sonuc, deger) {
  const bulunan = [];
  const tara = (depo, etiket) => {
    Object.keys(depo.data).forEach((k) => {
      if (String(k).indexOf(deger) !== -1) { bulunan.push(etiket + " anahtar:" + k); }
      if (String(depo.data[k]).indexOf(deger) !== -1) {
        bulunan.push(etiket + "[" + k + "]=" + depo.data[k]);
      }
    });
  };
  tara(sonuc.depo, "localStorage");
  tara(sonuc.oturum, "sessionStorage");
  const cerez = (sonuc.ctx && sonuc.ctx.document && sonuc.ctx.document.cookie) || "";
  if (cerez.indexOf(deger) !== -1) { bulunan.push("cookie=" + cerez); }
  return bulunan;
}

function yok(sonuc, deger, mesaj) {
  const bulunan = depodaGecenler(sonuc, deger);
  assert(bulunan.length === 0, mesaj + " -> SIZDI: " + bulunan.join(" | "));
}

function var_(sonuc, deger, mesaj) {
  assert(depodaGecenler(sonuc, deger).length > 0, mesaj + " -> saklanmadi");
}

// ═══════════════════════════════════════════════════════════════════════════
console.log("\n── A) index.html · PRUVO_ATIF (fbclid -> fbc) ──");

senaryo("A1 riza YOK + ?fbclid=ABC -> hicbir depoda ABC yok", () => {
  const s = sayfa({ search: "?fbclid=ABC" });
  yok(s, "ABC", "riza yokken fbclid saklandi");
  assert(s.atif.topla().fbc === undefined, "topla() rizasiz fbc dondurdu");
});

senaryo("A1b riza 'ret' + ?fbclid=ABC&utm_source=meta -> ABC yok, UTM korunur", () => {
  const s = sayfa({ search: "?fbclid=ABC&utm_source=meta", onay: "ret" });
  yok(s, "ABC", "riza 'ret' iken fbclid saklandi");
  assert(s.atif.topla().utm_source === "meta", "UTM (kampanya etiketi) kayboldu");
});

senaryo("A2 riza VAR + ?fbclid=ABC -> saklanir, akis bozulmaz", () => {
  const s = sayfa({ search: "?fbclid=ABC&utm_source=meta&utm_campaign=yaz",
                    onay: "kabul", cookie: "_fbp=fb.1.9.9; _ga=GA1.1.111.222" });
  var_(s, "ABC", "rizali fbclid");
  const kayit = JSON.parse(s.depo.getItem("pruvo_atif"));
  assert(/^fb\.1\.\d+\.ABC$/.test(kayit.fbc), "fbc bicimi bozuldu: " + kayit.fbc);
  const c = s.atif.topla();
  assert(c.fbc === kayit.fbc, "topla() fbc dondurmedi");
  assert(c.utm_source === "meta" && c.utm_campaign === "yaz", "topla() UTM dondurmedi");
  assert(c.fbp === "fb.1.9.9", "topla() fbp dondurmedi");
  assert(c.ga_client_id === "111.222", "topla() ga_client_id dondurmedi: " + c.ga_client_id);
});

senaryo("A3 banner: Reddet -> saklanmaz; sonra Kabul -> o andan itibaren saklanir", () => {
  // 1. yukleme: secim yok, banner cikar, ziyaretci Reddet'e basar.
  const depo = new Depo();
  const red = sayfa({ search: "?fbclid=ABC", depo, banner: true });
  assert(red.ogeler["pruvo-cerez-onay"].hidden === false, "banner gorunmedi");
  tikla(red.ogeler["pco-ret"]);
  assert(depo.getItem("pruvo_onay_analitik") === "ret", "ret yazilmadi");
  yok(red, "ABC", "Reddet'ten sonra fbclid saklandi");

  // Ayni oturumda riza 'kabul'e donerse (banner/tercih yuzeyi) -> yenileme YOK, hemen yakalanir.
  depo.setItem("pruvo_onay_analitik", "kabul");
  red.riza();
  var_(red, "ABC", "riza sonradan verilince fbclid");

  // Taze ziyaretci, banner'dan dogrudan Kabul: sayfa yuklenirken saklanmadi, tik aninda saklanir.
  const s = sayfa({ search: "?fbclid=XYZ", banner: true });
  yok(s, "XYZ", "banner acikken (secim yokken) fbclid saklandi");
  tikla(s.ogeler["pco-kabul"]);
  assert(s.depo.getItem("pruvo_onay_analitik") === "kabul", "kabul yazilmadi");
  var_(s, "XYZ", "banner Kabul tikindan sonra fbclid");
});

senaryo("A4 riza geri cekilince saklanmis tiklama kimligi SILINIR", () => {
  const s = sayfa({ search: "?fbclid=ABC&utm_source=meta", onay: "kabul" });
  var_(s, "ABC", "on kosul: rizali kayit");
  s.depo.setItem("pruvo_onay_analitik", "ret");   // riza geri cekildi
  s.riza();
  yok(s, "ABC", "riza geri cekilince fbclid silinmedi");
  assert(s.atif.topla().fbc === undefined, "topla() geri cekilmis rizada fbc dondurdu");
  assert(s.atif.topla().utm_source === "meta", "UTM gereksiz yere silindi");
});

senaryo("A5 geriye donuk: rizasiz tarayicidaki ESKI deger kod kosunca silinir", () => {
  const eski = new Depo({ pruvo_atif: JSON.stringify({ fbc: "fb.1.111.ABC", utm_source: "meta" }) });
  const s = sayfa({ search: "", depo: eski });          // URL'de parametre YOK
  yok(s, "ABC", "geriye donuk temizlik calismadi");
  assert(JSON.parse(s.depo.getItem("pruvo_atif")).utm_source === "meta", "UTM kayboldu");
});

senaryo("A5b geriye donuk: yalniz tiklama kimligi varsa anahtar tamamen kalkar", () => {
  const eski = new Depo({ pruvo_atif: JSON.stringify({ fbc: "fb.1.111.ABC" }) });
  const s = sayfa({ search: "", depo: eski });
  yok(s, "ABC", "geriye donuk temizlik calismadi");
  assert(s.depo.getItem("pruvo_atif") === null, "bos kayit birakildi");
});

senaryo("A6 topla(): riza yokken _fbc/_fbp/_ga cerezleri sunucuya GITMEZ", () => {
  const s = sayfa({ search: "", onay: "ret",
                    cookie: "_fbc=fb.1.7.CEREZID; _fbp=fb.1.9.9; _ga=GA1.1.111.222" });
  const c = s.atif.topla();
  assert(c.fbc === undefined && c.fbp === undefined && c.ga_client_id === undefined,
         "rizasiz kimlik alanlari sunucuya gidiyor: " + JSON.stringify(c));
});

console.log("\n── B) attribution-ref.js · gclid/gbraid/wbraid ──");

const WA = "https://wa.me/905451386526?text=Merhaba";

senaryo("B1 riza YOK + ?gclid=SIZ -> hicbir depoda SIZ yok (REF akisi calisir)", () => {
  const s = refSayfa({ search: "?gclid=SIZ&pg=BYP", linkler: [WA] });
  yok(s, "SIZ", "riza yokken gclid saklandi");
  assert(/^REF:GS-BYP-[A-Z0-9]{4}$/.test(s.ref()), "REF uretilmedi: " + s.ref());
  const mesaj = new URL(s.baglantilar[0].getAttribute("href")).searchParams.get("text");
  assert(mesaj.indexOf(s.ref()) !== -1, "wa.me linki REF ile zenginlestirilmedi: " + mesaj);
  s.tikla(0);
  assert(s.beacons.length === 0, "rizasiz beacon gonderildi");
});

senaryo("B1b riza YOK + ?gbraid/?wbraid -> saklanmaz", () => {
  const s = refSayfa({ search: "?gbraid=GBSIZ&wbraid=WBSIZ&pg=DIS" });
  yok(s, "GBSIZ", "riza yokken gbraid saklandi");
  yok(s, "WBSIZ", "riza yokken wbraid saklandi");
});

senaryo("B2 riza VAR + ?gclid=X -> eskisi gibi saklanir ve lead gider", () => {
  const s = refSayfa({ search: "?gclid=XKLIK&pg=BYP", onay: "kabul", linkler: [WA] });
  var_(s, "XKLIK", "rizali gclid");
  s.tikla(0);
  assert(s.beacons.length === 1, "rizali lead gonderilmedi");
  assert(JSON.parse(s.beacons[0].body).gclid === "XKLIK", "lead payload gclid yanlis");
});

senaryo("B3 geriye donuk: rizasiz tarayicidaki ESKI gclid kod kosunca silinir", () => {
  const eski = new Depo({ pruvo_ref: JSON.stringify({
    ref: "REF:GS-BYP-AB12", gclid: "ESKISIZ", grup: "BYP", src: "GS", ts: Date.now()
  }) });
  const s = refSayfa({ search: "", depo: eski });
  yok(s, "ESKISIZ", "geriye donuk temizlik calismadi");
  assert(s.ref() === "REF:GS-BYP-AB12", "REF kayboldu (WhatsApp akisi bozuldu)");
});

senaryo("B4 riza geri cekilince saklanmis gclid SILINIR", () => {
  const s = refSayfa({ search: "?gclid=XKLIK&pg=BYP", onay: "kabul" });
  var_(s, "XKLIK", "on kosul: rizali kayit");
  s.depo.setItem("pruvo_onay_analitik", "ret");
  s.riza();
  yok(s, "XKLIK", "riza geri cekilince gclid silinmedi");
  assert(s.ref() === JSON.parse(s.depo.getItem("pruvo_ref")).ref, "REF kayboldu");
});

senaryo("B5 riza sonradan verilirse: yenileme olmadan yakalanir + lead gider", () => {
  const s = refSayfa({ search: "?gclid=SONRA&pg=BYP", linkler: [WA] });
  yok(s, "SONRA", "riza yokken saklandi");
  s.depo.setItem("pruvo_onay_analitik", "kabul");   // ziyaretci Kabul'e basti
  s.riza();
  var_(s, "SONRA", "riza sonradan verilince gclid");
  s.tikla(0);
  assert(s.beacons.length === 1, "riza sonrasi lead gitmedi");
  assert(JSON.parse(s.beacons[0].body).gclid === "SONRA", "lead payload gclid yanlis");
});

senaryo("B6 sayfalar arasi: rizasiz landing sonrasi organik sayfada da sizinti yok", () => {
  const depo = new Depo();
  refSayfa({ search: "?gclid=SIZ&pg=NUM", depo });
  const ikinci = refSayfa({ search: "", depo });
  yok(ikinci, "SIZ", "ikinci sayfada gclid sizdi");
  assert(/^REF:GS-NUM-[A-Z0-9]{4}$/.test(ikinci.ref()), "REF sayfalar arasi tasinmadi");
});

console.log("\n── C) gizlilik/ · \"Çerez tercihimi değiştir\" (rızayı geri alma) ──");

senaryo("C0 drift kapisi: tiklama-kimligi alan listeleri iki dosyada AYNI", () => {
  const a = INDEX.match(/var TIK_ALANLARI = (\[[^\]]*\]);/);
  const b = REF_JS.match(/var ATIF_CLICK_FIELDS = (\[[^\]]*\]);/);
  assert(a, "index.html'de TIK_ALANLARI bulunamadi");
  assert(b, "attribution-ref.js'te ATIF_CLICK_FIELDS bulunamadi");
  const ia = JSON.parse(a[1]);
  const ib = JSON.parse(b[1]);
  assert(JSON.stringify(ia.slice().sort()) === JSON.stringify(ib.slice().sort()),
         "listeler ayristi (biri temizlemedigi alani birakir):\n  index.html      = " +
         JSON.stringify(ia) + "\n  attribution-ref = " + JSON.stringify(ib));
});

senaryo("C6 drift kapisi: gizlilik banner'i riza kancalarini build.py ile ayni cagiriyor", () => {
  const banner = BUILD_PY.slice(BUILD_PY.indexOf("GA_BANNER_SNIPPET"));
  ["pruvoMetaBaslat", "pruvoRefRiza"].forEach((kanca) => {
    assert(banner.indexOf(kanca) !== -1, "build.py banner snippet'inde " + kanca + " yok");
    assert(GIZ_BANNER_SRC.indexOf(kanca) !== -1,
           "gizlilik banner'i " + kanca + " cagirmiyor (uretilen sayfalardan sapti)");
  });
});

senaryo("C7 metin<->davranis: dugme ile aydinlatma metni birbirini tutuyor", () => {
  // KVKK: aydinlatma metni gercegi EKSIK anlatmamali. Iki yon de kilitli ->
  //   dugme var ama metin sussa   -> metin yalan (geri alma yolu gizli kalir)
  //   metin soz eder ama dugme yok -> metin yalan (olmayan yolu tarif eder)
  const ETIKET = "Çerez tercihimi değiştir";
  const dugmeVar = GIZ.indexOf('id="pco-degistir"') !== -1;
  // Dugme blogunu (ve yanindaki aciklama cumlesini) cikar -> geriye YASAL METIN kalir.
  const blokBas = GIZ.indexOf('<p class="pco-tercih">');
  let metin = GIZ;
  if (blokBas !== -1) {
    const blokSon = GIZ.indexOf("</p>", blokBas);
    assert(blokSon !== -1, "pco-tercih blogu kapanmiyor");
    metin = GIZ.slice(0, blokBas) + GIZ.slice(blokSon + "</p>".length);
  }
  const metindeVar = metin.indexOf(ETIKET) !== -1;
  assert(dugmeVar === metindeVar,
         "metin<->davranis ayristi: dugme " + (dugmeVar ? "VAR" : "YOK") +
         ", yasal metinde soz " + (metindeVar ? "VAR" : "YOK"));
  if (!dugmeVar) { return; }
  // Ibare DOGRU maddede olmali: "Nasil reddedilir / geri alinir".
  const i = metin.indexOf("Nasıl reddedilir");
  assert(i !== -1, "'Nasıl reddedilir / geri alınır' maddesi bulunamadi");
  const madde = metin.slice(metin.lastIndexOf("<li>", i), metin.indexOf("</li>", i));
  assert(madde.indexOf(ETIKET) !== -1,
         "ibare 'Nasıl reddedilir / geri alınır' maddesinde DEGIL (baska yere yazilmis)");
  // Marka dili kapisi: yasal sayfada "3D baski" ve sehir adi GECMEZ.
  [/3D bask/i, /Fethiye/i, /Göcek/i].forEach((k) => {
    assert(!k.test(madde), "eklenen ibare marka dili kuralini ihlal ediyor: " + k);
  });
});

senaryo("C1 dugme: saklanmis tiklama kimlikleri + analiz cerezleri FIILEN siliniyor", () => {
  const depo = new Depo({
    pruvo_onay_analitik: "kabul",
    pruvo_atif: JSON.stringify({ fbc: "fb.1.111.SIZFB", utm_source: "meta" }),
    pruvo_ref: JSON.stringify({ ref: "REF:GS-BYP-AB12", gclid: "SIZGC",
                                grup: "BYP", src: "GS", ts: Date.now() })
  });
  const s = gizlilikSayfa({ depo,
    cookie: "_fbc=fb.1.7.SIZCE; _fbp=fb.1.9.9; _ga=GA1.1.111.222; _ga_ABC=GS1.1.z; sepet=3" });
  var_(s, "SIZFB", "on kosul: pruvo_atif fbc");
  var_(s, "SIZGC", "on kosul: pruvo_ref gclid");
  var_(s, "SIZCE", "on kosul: _fbc cerezi");

  tikla(s.ogeler["pco-degistir"]);

  yok(s, "SIZFB", "dugme pruvo_atif fbc'yi silmedi");
  yok(s, "SIZGC", "dugme pruvo_ref gclid'i silmedi");
  yok(s, "SIZCE", "dugme _fbc cerezini silmedi");
  assert(s.kavanoz.map._fbp === undefined, "_fbp cerezi silinmedi");
  assert(s.kavanoz.map._ga === undefined, "_ga cerezi silinmedi");
  assert(s.kavanoz.map._ga_ABC === undefined, "_ga_* konteyner cerezi silinmedi");
  assert(s.kavanoz.map.sepet === "3", "ilgisiz cerez (sepet) silindi");
  assert(JSON.parse(s.depo.getItem("pruvo_atif")).utm_source === "meta",
         "UTM (kampanya etiketi) gereksiz yere silindi");
});

senaryo("C2 dugme: cerez bandi yeniden gorunuyor", () => {
  const s = gizlilikSayfa({ onay: "kabul" });
  assert(s.banner.hidden === true, "secim varken banner gorunur kalmis (on kosul)");
  tikla(s.ogeler["pco-degistir"]);
  assert(s.banner.hidden === false, "dugmeden sonra banner yeniden gorunmedi");
});

senaryo("C3 dugme sonrasi secim yapilmazsa riza YOK sayilir (fail-closed)", () => {
  const depo = new Depo({ pruvo_onay_analitik: "kabul" });
  const s = gizlilikSayfa({ depo });
  tikla(s.ogeler["pco-degistir"]);
  assert(depo.getItem("pruvo_onay_analitik") === null,
         "secim sifirlanmadi (deger: " + depo.getItem("pruvo_onay_analitik") + ")");
  // Ziyaretci hicbir sey secmeden gezmeye devam ediyor -> yeni reklam tiki SAKLANMAZ.
  yok(sayfa({ search: "?fbclid=YENI", depo }), "YENI",
      "dugme sonrasi (secimsiz) fbclid saklandi");
  yok(refSayfa({ search: "?gclid=YENIG&pg=BYP", depo }), "YENIG",
      "dugme sonrasi (secimsiz) gclid saklandi");
});

senaryo("C4 dugme sonrasi tekrar 'Kabul Et' -> akis normale doner", () => {
  const depo = new Depo({ pruvo_onay_analitik: "ret" });
  const s = gizlilikSayfa({ depo });
  tikla(s.ogeler["pco-degistir"]);
  tikla(s.ogeler["pco-kabul"]);
  assert(depo.getItem("pruvo_onay_analitik") === "kabul", "kabul yazilmadi");
  assert(s.banner.hidden === true, "kabul sonrasi banner gizlenmedi");
  assert(s.metaBaslatildi.length === 1,
         "kabul aninda Meta pikseli baslatilmadi: " + s.metaBaslatildi.length);
  const yeni = refSayfa({ search: "?gclid=DONDU&pg=BYP", depo, linkler: [WA] });
  var_(yeni, "DONDU", "kabul sonrasi gclid");
  yeni.tikla(0);
  assert(yeni.beacons.length === 1, "kabul sonrasi lead gitmedi");
});

senaryo("C5 banner gorunurlugu TEK kaynak: yalniz sakli riza degerinden turer", () => {
  assert(gizlilikSayfa({}).banner.hidden === false, "secimsizken banner gizli");
  assert(gizlilikSayfa({ onay: "kabul" }).banner.hidden === true, "kabul iken banner gorunur");
  const s = gizlilikSayfa({ onay: "ret" });
  assert(s.banner.hidden === true, "ret iken banner gorunur");
  tikla(s.ogeler["pco-degistir"]);
  assert(s.banner.hidden === false, "dugme sonrasi banner gizli");
  tikla(s.ogeler["pco-ret"]);
  assert(s.banner.hidden === true, "Reddet sonrasi banner gizlenmedi");
});

console.log("\n── D) ölçüm çerezleri · \"geçmişte bir kez rıza\" kapısı ──");

senaryo("D0 drift kapisi: olcum cerez kalibi iki dosyada AYNI", () => {
  const a = INDEX.match(/var OLCUM_CEREZ_KALIBI = (\/.*\/);/);
  const b = REF_JS.match(/var OLCUM_CEREZ_KALIBI = (\/.*\/);/);
  assert(a, "index.html'de OLCUM_CEREZ_KALIBI yok");
  assert(b, "attribution-ref.js'te OLCUM_CEREZ_KALIBI yok");
  assert(a[1] === b[1], "kaliplar ayristi:\n  index.html      = " + a[1] +
                        "\n  attribution-ref = " + b[1]);
});

senaryo("D0b tum riza yuzeyleri 'Reddet'te katmanlari uyariyor", () => {
  // Reddet cerezleri silmiyorsa "gecmiste bir kez riza" kapisi acik kalir -> her banner
  // (uretilen sayfalar + elle korunan 4 yasal sayfa) ayni kancayi cagirmali.
  const yuzeyler = [
    ["tools/build.py", BUILD_PY.slice(BUILD_PY.indexOf("GA_BANNER_SNIPPET"))],
    ["index.html", BANNER_SRC],
    ["gizlilik/index.html", GIZ_BANNER_SRC]
  ];
  ["hakkimizda", "iletisim", "sss"].forEach((slug) => {
    const html = fs.readFileSync(path.join(KOK, slug, "index.html"), "utf8");
    yuzeyler.push([slug + "/index.html", bannerCikar(html, slug)]);
  });
  yuzeyler.forEach(([ad, src]) => {
    const i = src.indexOf('ret.addEventListener');
    assert(i !== -1, ad + ": Reddet dinleyicisi bulunamadi");
    const govde = src.slice(i, i + 400);
    assert(/pruvoRefRiza|rizaYayinla|pruvoAtifRiza/.test(govde),
           ad + ": 'Reddet' riza degisimini hicbir katmana duyurmuyor (cerezler kalir)");
  });
});

senaryo("D1 Kabul -> _fbp yazildi -> Reddet: cerez SILINIR, topla() artik gondermez", () => {
  const kavanoz = new Kavanoz("_fbp=fb.1.9.FBPSIZ; _fbc=fb.1.7.FBCSIZ; _ga=GA1.1.GASIZ.222");
  const s = sayfa({ search: "", depo: new Depo({ pruvo_onay_analitik: "kabul" }),
                    kavanoz, banner: true });
  // On kosul: riza varken topla() kimlikleri DONDURUYOR.
  const oncesi = JSON.stringify(s.atif.topla());
  assert(oncesi.indexOf("FBPSIZ") !== -1 && oncesi.indexOf("FBCSIZ") !== -1 &&
         oncesi.indexOf("GASIZ") !== -1, "on kosul: rizali topla() kimlik dondurmedi: " + oncesi);

  // Ziyaretci fikrini degistirdi: banner'i tekrar acip Reddet'e basiyor (rizayi geri cekme).
  s.depo.removeItem("pruvo_onay_analitik");
  s.riza();
  s.depo.setItem("pruvo_onay_analitik", "ret");
  s.riza();

  yok(s, "FBPSIZ", "_fbp cerezi silinmedi");
  yok(s, "FBCSIZ", "_fbc cerezi silinmedi");
  yok(s, "GASIZ", "_ga cerezi silinmedi");
  const sonrasi = JSON.stringify(s.atif.topla());
  ["FBPSIZ", "FBCSIZ", "GASIZ"].forEach((ham) => {
    assert(sonrasi.indexOf(ham) === -1,
           "topla() geri cekilmis rizada hâlâ kimlik gonderiyor (" + ham + "): " + sonrasi);
  });
});

senaryo("D2 riza YOKken ESKI _fbp cerezi duruyorsa topla() yine GONDERMEZ (kapi geri acilmaz)", () => {
  const kavanoz = new Kavanoz("_fbp=fb.1.9.ESKIFBP; _fbc=fb.1.7.ESKIFBC; _ga=GA1.1.ESKIGA.222");
  const s = sayfa({ search: "", onay: "ret", kavanoz });
  const payload = JSON.stringify(s.atif.topla());
  ["ESKIFBP", "ESKIFBC", "ESKIGA"].forEach((ham) => {
    assert(payload.indexOf(ham) === -1,
           "rizasiz payload'da ham kimlik var (" + ham + "): " + payload);
  });
  // Ustelik cerezin kendisi de sayfa yuklenirken silinmis olmali.
  yok(s, "ESKIFBP", "rizasiz sayfa yuklemesinde _fbp temizlenmedi");
});

senaryo("D3 'Çerez tercihimi değiştir' -> cerez + depo temiz -> sonra Kabul: akis normale doner", () => {
  const depo = new Depo({
    pruvo_onay_analitik: "kabul",
    pruvo_atif: JSON.stringify({ fbc: "fb.1.111.ATIFSIZ", utm_source: "meta" })
  });
  const kavanoz = new Kavanoz("_fbp=fb.1.9.DFBP; _fbc=fb.1.7.DFBC; _ga=GA1.1.DGA.222");
  const g = gizlilikSayfa({ depo, kavanoz });
  tikla(g.ogeler["pco-degistir"]);
  ["ATIFSIZ", "DFBP", "DFBC", "DGA"].forEach((ham) => {
    yok(g, ham, "dugme sonrasi kalinti (" + ham + ")");
  });
  assert(depo.getItem("pruvo_onay_analitik") === null, "secim sifirlanmadi");

  tikla(g.ogeler["pco-kabul"]);
  assert(depo.getItem("pruvo_onay_analitik") === "kabul", "tekrar kabul yazilmadi");
  // Yeni ziyaret: piksel yeni cerez yaziyor, topla() yeniden gonderiyor.
  const yeni = sayfa({ search: "?fbclid=YENIFB", depo,
                       kavanoz: new Kavanoz("_fbp=fb.1.9.YENIFBP") });
  const payload = JSON.stringify(yeni.atif.topla());
  assert(payload.indexOf("YENIFBP") !== -1, "kabul sonrasi fbp gonderilmiyor: " + payload);
  assert(payload.indexOf("YENIFB") !== -1, "kabul sonrasi fbc gonderilmiyor: " + payload);
});

senaryo("D4 silinemeyen cerez SESSIZ gecilmez (konsola uyari)", () => {
  // Silmeye direnen kavanoz (HttpOnly / farkli path benzeri): uyari dusmezse test kirmizi.
  const inatci = new Kavanoz("_fbp=fb.1.9.INATCI");
  inatci.yaz = function () {};   // silme istegini yut
  const uyarilar = [];
  const konsol = { warn: (...a) => uyarilar.push(a.join(" ")), log() {}, error() {} };
  const s = sayfa({ search: "", onay: "ret", kavanoz: inatci, konsol });
  s.riza();
  assert(uyarilar.length > 0, "silinemeyen cerez icin uyari dusmedi (sessiz gecildi)");
  assert(uyarilar.join(" ").indexOf("_fbp") !== -1,
         "uyari silinemeyen cerezin adini icermiyor: " + uyarilar.join(" "));
});

senaryo("D5 SILINEMEYEN cerez varken bile topla() rizasiz kimlik GONDERMEZ", () => {
  // Kritik: cerez silme ile topla() kapisi BIRBIRINDEN BAGIMSIZ olmali. Silme calisirsa
  // eksik kapiyi maskeler; gercekte HttpOnly / farkli path / farkli alan cerezi silinemez.
  // Bu senaryo silmeyi devre disi birakip YALNIZ kapiyi olcer.
  const inatci = new Kavanoz("_fbp=fb.1.9.KAPIFBP; _fbc=fb.1.7.KAPIFBC; _ga=GA1.1.KAPIGA.222");
  inatci.yaz = function () {};   // silme istegini yut
  const konsol = { warn() {}, log() {}, error() {} };
  const s = sayfa({ search: "", onay: "ret", kavanoz: inatci, konsol });
  assert(inatci.metin().indexOf("KAPIFBP") !== -1, "on kosul: cerez silinmemis olmali");
  const payload = JSON.stringify(s.atif.topla());
  ["KAPIFBP", "KAPIFBC", "KAPIGA"].forEach((ham) => {
    assert(payload.indexOf(ham) === -1,
           "silinemeyen cerez topla() kapisini geri acti (" + ham + "): " + payload);
  });
});

senaryo("D6 rizasiz SAYFA YUKLEMESI (urun/yasal sayfa) olcum cerezlerini temizler", () => {
  // Ziyaretci hicbir dugmeye basmiyor; sadece gezinmesi bile eski cerezleri dusurmeli
  // (riza gecmiste geri cekilmis ya da hic verilmemis olabilir).
  const kavanoz = new Kavanoz("_fbp=fb.1.9.GEZFBP; _ga=GA1.1.GEZGA.222; sepet=3");
  const g = gizlilikSayfa({ onay: "ret", kavanoz });
  yok(g, "GEZFBP", "sayfa yuklemesinde _fbp temizlenmedi");
  yok(g, "GEZGA", "sayfa yuklemesinde _ga temizlenmedi");
  assert(g.kavanoz.map.sepet === "3", "ilgisiz cerez (sepet) silindi");
});

// ═══════════════════════════════════════════════════════════════════════════
const toplam = passed + hatalar.length;
if (hatalar.length) {
  console.error("\nFAIL " + passed + "/" + toplam);
  process.exit(1);
}
console.log("\nPASS " + passed + "/" + toplam);
