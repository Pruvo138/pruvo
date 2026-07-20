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
const BANNER_SRC = (function () {
  const d = INDEX.indexOf('id="pruvo-cerez-onay"');
  assert(d !== -1, "banner div bulunamadi");
  const s = INDEX.indexOf("<script>", d);
  const e = INDEX.indexOf("</script>", s);
  assert(s !== -1 && e !== -1, "banner script blogu bulunamadi");
  return INDEX.slice(s + "<script>".length, e);
})();
assert(BANNER_SRC.indexOf("pco-kabul") !== -1, "banner dilimi yanlis blogu aldi");

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
  const ctx = {
    window: {},
    document: {
      cookie: opts.cookie || "",
      getElementById: (id) => ogeler[id] || null
    },
    localStorage: depo,
    sessionStorage: oturum,
    location: { search: opts.search || "",
                href: "https://pruvo3d.com/" + (opts.search || "") },
    URL: URL,
    URLSearchParams: URLSearchParams,
    Date: Date,
    JSON: JSON,
    String: String,
    console: console
  };
  ctx.window.localStorage = depo;
  vm.runInNewContext(ATIF_SRC + "\n;window.__ATIF = PRUVO_ATIF;", ctx,
                     { filename: "index.html#PRUVO_ATIF" });
  if (opts.banner) {
    vm.runInNewContext(BANNER_SRC, ctx, { filename: "index.html#banner" });
  }
  return { ctx, depo, oturum, ogeler,
           atif: ctx.window.__ATIF,
           riza: ctx.window.pruvoAtifRiza };
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

// ═══════════════════════════════════════════════════════════════════════════
const toplam = passed + hatalar.length;
if (hatalar.length) {
  console.error("\nFAIL " + passed + "/" + toplam);
  process.exit(1);
}
console.log("\nPASS " + passed + "/" + toplam);
