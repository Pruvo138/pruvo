#!/usr/bin/env node
/**
 * KABUL TESTI — REKLAM TIKLAMA KIMLIGININ SAYFALAR ARASI KORUNMASI.
 *
 *   node tools/reklam-url-test.js
 *
 * NEDEN VAR (olculdu, 8 Agu 2026): index.html'deki syncUrl() her filtre/arama
 * degisiminde sorgu dizesini SIFIRDAN kurup history.replaceState ile basiyordu; kurdugu
 * kume yalnizca kategori/altkategori/marka/model/ara idi. Sonuc: `?gclid=…` ile gelen
 * ziyaretci ilk cipe dokundugu an tiklama kimligi URL'den SILINIYORDU. gtag.js `async`
 * yuklendigi icin bu bir YARIS — silinme olcumden ONCE olabiliyordu; url_passthrough
 * (Consent Mode v2) rizasiz tasima yapsa bile tasiyacak bir deger kalmiyordu.
 *
 * NE KANITLANIR (davranissal, DOM/URL semantigi ile):
 *   1) `?gclid=X` ile acilan sayfada bir FILTREYE dokunulunca gclid URL'de KALIR.
 *   2) Sekiz reklam parametresinin (gclid/gbraid/wbraid + bes utm) hepsi korunur.
 *   3) Reklam parametresi YOKKEN davranis DEGISMEZ (temiz URL, sahte "?" yok).
 *   4) Filtre adiyla cakisma: filtre KAZANIR, parametre MUKERRER yazilmaz.
 *   5) KAPSAM DISCIPLINI (yanlis-pozitif ekseni): reklamla ilgisi olmayan bir parametre
 *      (`?foo=bar`, `?sayfa=3`) KORUNMAZ — syncUrl "her seyi tasi"ya donmemistir.
 *   6) TEK KANONIK KAYNAK: korunan liste PRUVO_ATIF.urlKorunan()'dan gelir; syncUrl
 *      govdesinde IKINCI bir elle yazilmis parametre dizisi YOKTUR.
 *
 * Kaynak GERCEK index.html'den kesilir (kopya tutulmaz) -> dosya degisince test onu okur.
 * Repoda npm bagimliligi YOK; mini ortam elde yazilmistir (riza-tikkimligi-test.js ile ayni
 * gelenek). Offline, stdlib, ~50 ms.
 */

"use strict";

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const KOK = path.dirname(__dirname);
const INDEX = fs.readFileSync(path.join(KOK, "index.html"), "utf8");

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

// ─── GERCEK kaynagi index.html'den KES (kopya tutma) ─────────────────────────
function dilim(metin, bas, bit, ad) {
  const i = metin.indexOf(bas);
  assert(i !== -1, ad + ": baslangic isareti bulunamadi -> " + bas);
  const j = metin.indexOf(bit, i);
  assert(j !== -1, ad + ": bitis isareti bulunamadi -> " + bit);
  return metin.slice(i, j);
}

const ATIF_SRC = dilim(INDEX, "var PRUVO_ATIF = (function(){",
                       "\n  /* Banner ayrı bir <script>", "PRUVO_ATIF");
assert(ATIF_SRC.indexOf("urlKorunan") !== -1,
       "PRUVO_ATIF dilimi urlKorunan() kancasini icermiyor -> tek kanonik kaynak YOK");

const SYNC_SRC = dilim(INDEX, "  function syncUrl(){",
                       "\n  // seçili kategori + aramaya uyan", "syncUrl");
assert(SYNC_SRC.indexOf("history.replaceState") !== -1,
       "syncUrl dilimi yanlis blogu aldi (replaceState yok)");

// ─── mini ortam: localStorage + location + history ───────────────────────────
function Depo() { this.data = {}; }
Depo.prototype.getItem = function (k) {
  return Object.prototype.hasOwnProperty.call(this.data, k) ? this.data[k] : null;
};
Depo.prototype.setItem = function (k, v) { this.data[k] = String(v); };
Depo.prototype.removeItem = function (k) { delete this.data[k]; };

/**
 * Tek kosum: verilen baslangic URL'si + verilen gorunum durumu ile syncUrl() calistirilir.
 * Donen deger replaceState'in BASTIGI URL'dir (yani ziyaretcinin adres cubugunda kalan).
 */
function kosum(baslangicUrl, durum) {
  const url = new URL(baslangicUrl, "https://pruvo3d.com");
  const konum = {
    get search() { return url.search; },
    get pathname() { return url.pathname; },
    get href() { return url.href; }
  };
  let basilan = null;
  const kutu = {
    URLSearchParams,
    URL,
    console: { log() {}, warn() {}, error() {} },
    localStorage: new Depo(),
    crypto: { getRandomValues(a) { for (let i = 0; i < a.length; i++) { a[i] = i; } return a; } },
    document: { cookie: "", readyState: "complete", addEventListener() {} },
    location: konum,
    history: { replaceState(_s, _t, u) { basilan = u; } },
    window: {},
    Date
  };
  kutu.window.addEventListener = function () {};
  kutu.window.localStorage = kutu.localStorage;
  vm.createContext(kutu);
  vm.runInContext(
    "var activeCat = " + JSON.stringify(durum.kategori || "Tümü") + ";" +
    "var activeAlt = " + JSON.stringify(durum.altkategori || "Tümü") + ";" +
    "var activeBrand = " + JSON.stringify(durum.marka || "Tümü") + ";" +
    "var activeModel = " + JSON.stringify(durum.model || "Tümü") + ";" +
    "var query = " + JSON.stringify(durum.ara || "") + ";\n" +
    ATIF_SRC + "\n" + SYNC_SRC + "\nsyncUrl();", kutu);
  assert(basilan !== null, "syncUrl replaceState CAGIRMADI");
  return basilan;
}

/** Basilan URL'nin sorgu parametrelerini sozluk + sayim olarak dondurur. */
function sorgu(basilan) {
  const i = basilan.indexOf("?");
  const q = new URLSearchParams(i === -1 ? "" : basilan.slice(i + 1));
  const map = {};
  const sayim = {};
  for (const [k, v] of q.entries()) {
    map[k] = v;
    sayim[k] = (sayim[k] || 0) + 1;
  }
  return { map, sayim, ham: basilan };
}

// ─── 1) ISIN CEKIRDEGI: gclid bir filtre tikindan SONRA da URL'de ────────────
senaryo("1 ?gclid ile acilan sayfada filtreye dokununca gclid URL'de KALIR", () => {
  const r = sorgu(kosum("/?gclid=CjwKCAiA_TEST123", { kategori: "Marin" }));
  assert(r.map.gclid === "CjwKCAiA_TEST123",
         "gclid URL'den DUSTU -> donusum atifi coker (basilan: " + r.ham + ")");
  assert(r.map.kategori === "Marin", "filtre davranisi bozuldu: kategori yok");
});

senaryo("1b arama yazilinca da gclid KALIR (ayri kol: query yolu)", () => {
  const r = sorgu(kosum("/?gclid=ABC", { ara: "kapak" }));
  assert(r.map.gclid === "ABC", "arama kolunda gclid dustu: " + r.ham);
  assert(r.map.ara === "kapak", "arama parametresi yazilmadi: " + r.ham);
});

// ─── 2) SEKIZ PARAMETRENIN HEPSI ─────────────────────────────────────────────
const SEKIZ = ["gclid", "gbraid", "wbraid", "utm_source", "utm_medium",
               "utm_campaign", "utm_term", "utm_content"];

senaryo("2 sekiz reklam parametresinin HEPSI korunur", () => {
  const giris = "/?" + SEKIZ.map((k) => k + "=" + k.toUpperCase() + "1").join("&");
  const r = sorgu(kosum(giris, { marka: "Audi" }));
  const eksik = SEKIZ.filter((k) => r.map[k] !== k.toUpperCase() + "1");
  assert(eksik.length === 0, "KORUNMAYAN parametre(ler): " + eksik.join(", ") +
         " | basilan: " + r.ham);
  assert(r.map.marka === "Audi", "filtre davranisi bozuldu");
});

// ─── 3) REKLAM PARAMETRESI YOKKEN DAVRANIS DEGISMEZ ──────────────────────────
senaryo("3 reklam parametresi YOKKEN URL temiz kalir (regresyon yok)", () => {
  assert(kosum("/", {}) === "/", "bos durumda pathname disinda bir sey basildi: " +
         kosum("/", {}));
  const r = sorgu(kosum("/", { kategori: "Ev", ara: "raf" }));
  assert(Object.keys(r.map).length === 2,
         "beklenmeyen parametre eklendi: " + JSON.stringify(r.map));
  assert(r.map.kategori === "Ev" && r.map.ara === "raf", "filtre yazimi bozuldu");
});

// ─── 4) FILTRE ADIYLA CAKISMA: filtre kazanir, MUKERRER yok ──────────────────
senaryo("4 cakismada filtre kazanir ve parametre MUKERRER yazilmaz", () => {
  const r = sorgu(kosum("/?kategori=Otomobil&gclid=X", { kategori: "Marin" }));
  assert(r.map.kategori === "Marin",
         "gorunum durumu yerine URL'deki eski kategori bastirildi: " + r.ham);
  assert(r.sayim.kategori === 1, "kategori MUKERRER yazildi: " + r.ham);
  assert(r.map.gclid === "X", "cakisma kolunda gclid dustu: " + r.ham);
});

// ─── 5) KAPSAM DISCIPLINI (yanlis-pozitif ekseni) ────────────────────────────
// Tek yonlu bir test ("gclid duruyor mu") syncUrl'i "her parametreyi tasi"ya cevirseydi de
// YESIL yanardi. O halde paylasilan linkler cop parametre biriktirir ve kanonik adres
// coklanir. Bu senaryo sinirin OBUR tarafini nobetler.
senaryo("5 reklamla ILGISIZ parametre KORUNMAZ (kapsam genislemedi)", () => {
  const r = sorgu(kosum("/?foo=bar&sayfa=3&gclid=Z", { kategori: "Ev" }));
  assert(r.map.foo === undefined, "kapsam disi `foo` tasindi -> syncUrl her seyi tasiyor");
  assert(r.map.sayfa === undefined, "kapsam disi `sayfa` tasindi");
  assert(r.map.gclid === "Z", "kontrol: gclid yine de korunmali");
});

// ─── 6) TEK KANONIK KAYNAK ───────────────────────────────────────────────────
senaryo("6 korunan liste TEK kanonik kaynaktan turer (ikinci elle liste YOK)", () => {
  assert(SYNC_SRC.indexOf("PRUVO_ATIF.urlKorunan()") !== -1,
         "syncUrl kanonik kaynagi cagirmiyor");
  // syncUrl govdesinde "gclid"/"utm_" gecen bir DIZI LITERALI olmamali (ikinci liste).
  const govde = SYNC_SRC.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
  assert(!/\[[^\]]*["']gclid["'][^\]]*\]/.test(govde),
         "syncUrl govdesinde IKINCI bir elle yazilmis parametre dizisi var");
  // ...ve kanonik kaynak sekizini de KAPSAMALI (kume iddiasi, davranistan bagimsiz).
  const kutu = { localStorage: new Depo(), document: { cookie: "", addEventListener() {} },
                 window: { addEventListener() {} }, location: { search: "" },
                 URLSearchParams, console: { warn() {} }, Date, cikti: null };
  vm.createContext(kutu);
  vm.runInContext(ATIF_SRC + "\ncikti = PRUVO_ATIF.urlKorunan();", kutu);
  const kume = kutu.cikti;
  assert(Array.isArray(kume) && kume.length > 0, "urlKorunan() dizi dondurmedi");
  const eksik = SEKIZ.filter((k) => kume.indexOf(k) === -1);
  assert(eksik.length === 0, "kanonik kume eksik: " + eksik.join(", "));
});

// ─── ozet ────────────────────────────────────────────────────────────────────
console.log("\n" + "-".repeat(70));
if (hatalar.length) {
  console.error("SONUC: KIRMIZI ❌  — " + hatalar.length + " senaryo dustu, " +
                passed + " gecti");
  hatalar.forEach((h) => console.error("  · " + h));
  process.exit(1);
}
console.log("SONUC: YESIL ✅  — " + passed +
            " senaryo: reklam tiklama kimligi sayfalar arasi KORUNUYOR, kapsam genislemedi.");
