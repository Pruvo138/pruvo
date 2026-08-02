#!/usr/bin/env node
/**
 * ALT KATEGORI (GRUP) CIP SATIRI — DAVRANIS KOSUMU (kabul testinin ICRA KOLU).
 *
 *   node tools/altkategori-cip-kosum.js --kok <agac> --izinli <json>
 *
 * BU DOSYA TEK BASINA BIR KAPI DEGILDIR: iddialari JSON olarak stdout'a basar, HUKMU
 * tools/altkategori-cip-test.py verir (CI girisi odur). Adi bilerek "-test.js" DEGIL —
 * tools/ci-kapsam-test.py kesfi ikinci bir CI girisi beklemesin.
 *
 * NASIL OLCER: index.html'in GERCEK inline scripti node:vm icinde, minimal bir DOM
 * taklidi + SAHTE fetch ile CALISTIRILIR (kod kopyalanmaz; emsal: shop/test/sepet-panel.js).
 * Cipler GERCEKTEN tiklanir, URL GERCEKTEN yazilir/okunur, liste GERCEKTEN yeniden cizilir.
 *
 * IKI MOD DA KOSAR — cunku filtre IKI AYRI YOLDA yasar ve biri sessizce kopabilir:
 *   edge  (EDGE_KATALOG = true, CANLI hal): istemci `altkategori`yi Worker'a GONDERIR.
 *         Sahte sunucu degeri TAM ESITLIKLE suzer -> parametre dusurulurse sayi DEGISMEZ.
 *   yerel (bayrak false, geri donus yolu): istemci filtered() ile KENDI suzer -> donen
 *         kartlarin DEGERI tek tek olculur.
 * Tek modda olculseydi oteki yol sessizce fail-open kalirdi.
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// ---------------------------------------------------------------- argumanlar
function arg(ad, varsayilan) {
  const i = process.argv.indexOf("--" + ad);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : varsayilan;
}
const KOK = path.resolve(arg("kok", path.dirname(__dirname)));
const IZINLI = JSON.parse(fs.readFileSync(arg("izinli"), "utf8"));

const INDEX_METIN = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const SECENEK_SRC = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));

const SCRIPT_EDGE = inlineScriptBul(INDEX_METIN, "renderGrid");
if (!SCRIPT_EDGE) { throw new Error("index.html inline katalog scripti bulunamadi"); }

// Bayrak cevirme: MUTASYON DEGIL, belgelenmis geri donus yolunun ta kendisi
// (index.html :: EDGE_KATALOG "false = BUGUNKU davranis ... geri donus yolu budur").
// Capa tutmazsa SESSIZ GECME YOK — hata firlatilir.
const BAYRAK_ACIK = "var EDGE_KATALOG = true;";
if (SCRIPT_EDGE.indexOf(BAYRAK_ACIK) === -1) {
  throw new Error("EDGE_KATALOG capasi bulunamadi (index.html yapisi degisti mi?)");
}
const SCRIPT_YEREL = SCRIPT_EDGE.replace(BAYRAK_ACIK, "var EDGE_KATALOG = false;");

// ---------------------------------------------------------------- fikstur katalogu
// KUCUK ve ELLE SAYILABILIR: her iddia beklenen sayiyi KENDI hesaplar, sabit gomulmez.
// Marin/Otomobil alt kategorisi OLAN, Bisiklet alt kategorisi OLMAYAN kategori orneğidir.
function urun(id, kategori, altkategori, marka) {
  const p = {
    id, kategori, baslik: "Test " + id, aciklama: "aciklama " + id,
    fiyat: "100 TL", gorseller: ["https://media.pruvo3d.com/urunler/" + id + ".jpg"],
    marka: marka || [],
  };
  if (altkategori) { p.altkategori = altkategori; }
  return p;
}
const KATALOG = [];
for (let i = 1; i <= 5; i++) { KATALOG.push(urun("marin-buji-" + i, "Marin", "Bujiler", ["Champion"])); }
for (let i = 1; i <= 3; i++) { KATALOG.push(urun("marin-filtre-" + i, "Marin", "Filtreler")); }
for (let i = 1; i <= 2; i++) { KATALOG.push(urun("marin-grupsuz-" + i, "Marin", null)); }
for (let i = 1; i <= 4; i++) { KATALOG.push(urun("oto-aydinlatma-" + i, "Otomobil", "Aydınlatma")); }
for (let i = 1; i <= 2; i++) { KATALOG.push(urun("oto-kapi-" + i, "Otomobil", "Kapı ve Cam")); }
for (let i = 1; i <= 3; i++) { KATALOG.push(urun("bisiklet-" + i, "Bisiklet", null)); }

const ALT_HARITA = {};
KATALOG.forEach((p) => { ALT_HARITA[p.id] = p.altkategori || ""; });
const say = (f) => KATALOG.filter(f).length;

// ---------------------------------------------------------------- minimal DOM taklidi
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
  el.tetikle = (t, ev) => { const fn = el._dinleyiciler[t]; if (fn) { return fn(ev || { preventDefault() {} }); } };
  el.focus = () => {};
  el.scrollIntoView = () => {};
  el.querySelector = () => null;
  el.querySelectorAll = () => [];
  return el;
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
    cookie: "",
  };
}

// ---------------------------------------------------------------- sahte sunucu
// Worker'in katMarkaAltKosulu'yla AYNI kural: kategori/marka/altkategori TAM ESITLIK,
// q basliкta alt-dize. Suzgec SUNUCUDA oldugu icin istemci parametreyi DUSURURSE
// sonuc sayisi DEGISMEZ -> "cip tiklandi ama liste degismedi" KIRMIZI yanar.
function sunucuSuz(u) {
  const q = u.searchParams;
  const kategori = q.get("kategori") || "";
  const marka = q.get("marka") || "";
  const alt = q.get("altkategori") || "";
  const ara = (q.get("q") || "").toLocaleLowerCase("tr");
  return KATALOG.filter((p) => {
    if (kategori && p.kategori !== kategori) { return false; }
    if (alt && (p.altkategori || "") !== alt) { return false; }
    if (marka && (p.marka || []).indexOf(marka) === -1) { return false; }
    if (ara && p.baslik.toLocaleLowerCase("tr").indexOf(ara) === -1) { return false; }
    return true;
  });
}
function kartOzeti(p) {
  const k = {
    id: p.id, baslik: p.baslik, kategori: p.kategori, marka: p.marka || [],
    fiyat: p.fiyat, gorsel: (p.gorseller || [null])[0], parametrik: false,
    aciklama: (p.aciklama || "").slice(0, 160),
  };
  // Worker KART_ALANLARI `altkategori`yi TASIR (canlida olculdu) — ayna da tasimali.
  if (p.altkategori) { k.altkategori = p.altkategori; }
  return k;
}

// ---------------------------------------------------------------- sayfa kurucu
function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function sayfaKur(mod, search) {
  const belge = belgeKur();
  const fetchIzi = [];
  const konsolHatalari = [];
  const pencereDinleyiciler = {};
  const depo = {};

  const konum = { hash: "", search: search || "", pathname: "/", href: "", replace() {} };

  const ctx = {
    document: belge,
    location: konum,
    history: {
      // GERCEK tarayici davranisi: URL'yi DEGISTIRIR. Taklit etmezsek "URL round-trip"
      // iddiasi hicbir sey olcmez (yazilan URL kaybolur).
      replaceState(_s, _t, url) {
        const s = String(url || "");
        const i = s.indexOf("?");
        konum.pathname = i === -1 ? s : s.slice(0, i);
        konum.search = i === -1 ? "" : s.slice(i);
      },
      pushState(_s, _t, url) { this.replaceState(_s, _t, url); },
    },
    localStorage: {
      getItem: (k) => (k in depo ? depo[k] : null),
      setItem: (k, v) => { depo[k] = String(v); },
      removeItem: (k) => { delete depo[k]; },
    },
    fetch(url) {
      const u = new URL(String(url), "https://pruvo3d.com/");
      fetchIzi.push(u.pathname + u.search);
      const cevap = (govde) => Promise.resolve({
        ok: true, status: 200,
        json: () => Promise.resolve(JSON.parse(JSON.stringify(govde))),
      });
      if (u.pathname.indexOf("ozet.json") !== -1) {
        return cevap({
          surum: 1, toplam: KATALOG.length, kategoriler: {}, markalar: {},
          parametrik: [], bloklar: {}, yeni: KATALOG.map(kartOzeti), vitrin: {},
        });
      }
      if (u.pathname.indexOf("urunler.json") !== -1) { return cevap(KATALOG); }
      if (u.pathname.indexOf("/katalog") !== -1 || u.pathname.indexOf("/ara") !== -1) {
        const hepsi = sunucuSuz(u);
        const boy = Number(u.searchParams.get("boy") || u.searchParams.get("limit") || 24);
        const sayfa = Number(u.searchParams.get("sayfa") || 1);
        const dilim = u.searchParams.get("limit")
          ? hepsi.slice(0, boy)
          : hepsi.slice((sayfa - 1) * boy, sayfa * boy);
        return cevap({ toplam: hepsi.length, sayfa, sayfaBoyu: boy, urunler: dilim.map(kartOzeti) });
      }
      return cevap({});
    },
    console: { log() {}, error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
    alert() {},
    navigator: {},
    URL, URLSearchParams,
    setTimeout, clearTimeout, setInterval, clearInterval,
    requestIdleCallback: (f) => setTimeout(f, 0),
    addEventListener(t, fn) { pencereDinleyiciler[t] = fn; },
    removeEventListener(t) { delete pencereDinleyiciler[t]; },
    scrollTo() {}, scrollY: 0, innerHeight: 720,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SECENEK_SRC, ctx, { filename: "secenekler.js" });
  vm.runInContext(mod === "yerel" ? SCRIPT_YEREL : SCRIPT_EDGE, ctx, { filename: "index-inline.js" });
  await bekle(20); await bekle(20); await bekle(320);   // fetch zinciri + 250 ms debounce

  const el = (id) => belge.getElementById(id);
  const dur = async () => { await bekle(20); await bekle(20); await bekle(320); };

  function cipler() { return el("altChips").children.map((c) => c.textContent); }
  function aktifCip() {
    const a = el("altChips").children.filter((c) => c.className.indexOf("active") !== -1);
    return a.length === 1 ? a[0].textContent : (a.length === 0 ? null : "COKLU:" + a.length);
  }
  async function cipTikla(ad) {
    const c = el("altChips").children.filter((x) => x.textContent === ad)[0];
    if (!c) { throw new Error("cip yok: " + ad); }
    c.onclick();
    await dur();
  }
  async function katTikla(ad) {
    const c = el("cats").children.filter((x) => x.textContent === ad)[0];
    if (!c) { throw new Error("kategori cipi yok: " + ad); }
    c.onclick();
    await dur();
  }
  function sayi() {
    const m = /(\d+)\s+ürün/.exec(el("resultCount").textContent || "");
    return m ? Number(m[1]) : -1;
  }
  function kartIdleri() {
    const out = [];
    const gez = (n) => {
      const h = n.href || "";
      const m = /^\/urun\/(.+)\/$/.exec(h);
      if (m) { out.push(m[1]); }
      (n.children || []).forEach(gez);
    };
    el("grid").children.forEach(gez);
    return out;
  }
  function urlAlt() { return new URLSearchParams(konum.search).get("altkategori"); }
  async function popstate() {
    if (!pencereDinleyiciler.popstate) { throw new Error("popstate dinleyicisi YOK"); }
    pencereDinleyiciler.popstate({});
    await dur();
  }

  return { ctx, el, cipler, aktifCip, cipTikla, katTikla, sayi, kartIdleri, urlAlt,
           popstate, konum, fetchIzi, konsolHatalari,
           altGorunur: () => el("altRow").style.display !== "none" };
}

// ---------------------------------------------------------------- iddialar
const IDDIALAR = [];
function iddia(ad, gecti, detay) { IDDIALAR.push({ ad, gecti: !!gecti, detay: String(detay) }); }

async function modKos(mod) {
  const P = mod.toUpperCase();

  // --- 1) CIP EVRENI VERIDEN TURER (elle gomulu liste degil) ---------------
  {
    const s = await sayfaKur(mod, "");
    await s.katTikla("Marin");
    const beklenen = ["Tümü"].concat(IZINLI.Marin);
    const goruldu = s.cipler();
    iddia(P + " CIP EVRENI = IZINLI KUME (Marin)",
      JSON.stringify(goruldu) === JSON.stringify(beklenen),
      goruldu.length + " cip; beklenen " + beklenen.length);
  }

  // --- 2) ALT KATEGORISI OLMAYAN KATEGORIDE SATIR YOK ----------------------
  {
    const s = await sayfaKur(mod, "");
    await s.katTikla("Bisiklet");
    iddia(P + " ALT KATEGORISIZ KATEGORIDE SATIR YOK (Bisiklet)",
      s.altGorunur() === false && s.cipler().length === 0,
      "gorunur=" + s.altGorunur() + " cip=" + s.cipler().length);
    // KONTROL EKSENI: ayni kosumda alt kategorisi OLAN kategoride satir VAR olmali —
    // yoksa "hep gizli" bir mutant bu iddiayi bedavaya gecerdi.
    await s.katTikla("Marin");
    iddia(P + " ALT KATEGORILI KATEGORIDE SATIR VAR (Marin)",
      s.altGorunur() === true && s.cipler().length === IZINLI.Marin.length + 1,
      "gorunur=" + s.altGorunur() + " cip=" + s.cipler().length);
  }

  // --- 3) CIP TIKLANINCA LISTEDEKI URUN SAYISI DEGISIR --------------------
  {
    const s = await sayfaKur(mod, "");
    await s.katTikla("Marin");
    const once = s.sayi();
    await s.cipTikla("Bujiler");
    const sonra = s.sayi();
    const beklenenOnce = say((p) => p.kategori === "Marin");
    const beklenenSonra = say((p) => p.kategori === "Marin" && p.altkategori === "Bujiler");
    iddia(P + " CIP TIKLANINCA SAYI DEGISIR",
      once === beklenenOnce && sonra === beklenenSonra && sonra !== once,
      "Marin " + once + " -> Bujiler " + sonra + " (beklenen " + beklenenOnce + " -> " + beklenenSonra + ")");
    iddia(P + " SECILI CIP AKTIF ISARETLI", s.aktifCip() === "Bujiler", "aktif=" + s.aktifCip());

    // --- 4) AYNI CIPE TEKRAR TIK = SECIM TEMIZLENIR -----------------------
    await s.cipTikla("Bujiler");
    iddia(P + " TEKRAR TIK SECIMI TEMIZLER",
      s.sayi() === beklenenOnce && s.urlAlt() === null && s.aktifCip() === "Tümü",
      "sayi=" + s.sayi() + " url=" + s.urlAlt() + " aktif=" + s.aktifCip());

    // --- 5) "Tümü" CIPI DE TEMIZLER ---------------------------------------
    await s.cipTikla("Filtreler");
    await s.cipTikla("Tümü");
    iddia(P + " 'Tümü' CIPI SECIMI TEMIZLER",
      s.sayi() === beklenenOnce && s.urlAlt() === null,
      "sayi=" + s.sayi() + " url=" + s.urlAlt());
  }

  // --- 6) URL ROUND-TRIP: yaz -> oku -> ayni secim -------------------------
  {
    const s1 = await sayfaKur(mod, "");
    await s1.katTikla("Marin");
    await s1.cipTikla("Filtreler");
    const yazilan = s1.konum.search;
    const sayi1 = s1.sayi();
    iddia(P + " URL YAZILIYOR", new URLSearchParams(yazilan).get("altkategori") === "Filtreler",
      "search=" + yazilan);

    const s2 = await sayfaKur(mod, yazilan);
    iddia(P + " URL ROUND-TRIP (yaz -> oku -> ayni secim)",
      s2.aktifCip() === "Filtreler" && s2.sayi() === sayi1 && s2.altGorunur() === true,
      "aktif=" + s2.aktifCip() + " sayi=" + s2.sayi() + " (yazan kosum " + sayi1 + ")");
  }

  // --- 7) UYDURMA DEGER -> 0 (sessizce tam liste DONMEZ) ------------------
  {
    const s = await sayfaKur(mod, "?kategori=Marin&altkategori=xyzyok");
    iddia(P + " UYDURMA DEGER -> 0 URUN",
      s.sayi() === 0 && s.kartIdleri().length === 0,
      "sayi=" + s.sayi() + " kart=" + s.kartIdleri().length);
    // Kume disi deger secili: cip KAYBOLMAZ (temizleme yolu kalsin)
    iddia(P + " KUME DISI DEGER CIPI GORUNUR", s.cipler().indexOf("xyzyok") !== -1,
      "cipler=" + s.cipler().length);
  }

  // --- 8) KATEGORISIZ DEEP-LINK: ana vitrin listeyi EZMEZ -----------------
  {
    const s = await sayfaKur(mod, "?altkategori=Bujiler");
    const beklenen = say((p) => p.altkategori === "Bujiler");
    iddia(P + " KATEGORISIZ ?altkategori ANA VITRINE DUSMEZ",
      s.sayi() === beklenen && s.sayi() !== KATALOG.length,
      "sayi=" + s.sayi() + " beklenen=" + beklenen + " katalog=" + KATALOG.length);
  }

  // --- 9) KATEGORI DEGISINCE TANIMSIZ GRUP DUSER --------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Marin&altkategori=Bujiler");
    await s.katTikla("Otomobil");
    iddia(P + " KATEGORI DEGISINCE GRUP DUSER",
      s.urlAlt() === null && s.sayi() === say((p) => p.kategori === "Otomobil"),
      "url=" + s.urlAlt() + " sayi=" + s.sayi());
  }

  // --- 10) GERI/ILERI (popstate) ------------------------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Marin&altkategori=Bujiler");
    const secili = s.sayi();
    s.konum.search = "?kategori=Marin";      // tarayici geri tusu: URL degisti
    await s.popstate();
    iddia(P + " GERI/ILERI (popstate) GORUNUMU URL'YE OTURTUR",
      s.urlAlt() === null && s.aktifCip() === "Tümü" &&
      s.sayi() === say((p) => p.kategori === "Marin") && s.sayi() !== secili,
      "secili=" + secili + " -> geri=" + s.sayi() + " aktif=" + s.aktifCip());
  }

  // --- 11) DONEN URUNLERIN HEPSI SECILEN DEGERE ESIT (DEGERE bakar) -------
  {
    const s = await sayfaKur(mod, "?kategori=Marin&altkategori=Filtreler");
    const idler = s.kartIdleri();
    const sapan = idler.filter((id) => ALT_HARITA[id] !== "Filtreler");
    iddia(P + " DONEN URUNLERIN HEPSI 'Filtreler'",
      idler.length === say((p) => p.altkategori === "Filtreler") && sapan.length === 0,
      "kart=" + idler.length + " sapan=" + sapan.length + (sapan.length ? " [" + sapan.join(",") + "]" : ""));
  }

  // --- 12) MODA OZGU YOL --------------------------------------------------
  if (mod === "edge") {
    const s = await sayfaKur("edge", "");
    await s.katTikla("Marin");
    await s.cipTikla("Bujiler");
    const istek = s.fetchIzi.filter((u) => u.indexOf("altkategori=") !== -1);
    iddia("EDGE ISTEGI altkategori PARAMETRESINI TASIR", istek.length > 0,
      (istek[istek.length - 1] || "(hic)"));
    // ARAMA ile birlikte de tasinmali (/ara kolu) — tek kolda baglanip otekinde
    // dusmesi olculmus sessiz-hata sinifi.
    s.el("search").value = "Test";
    s.el("search").tetikle("input", {});
    await bekle(20); await bekle(400);
    const araIstek = s.fetchIzi.filter((u) => u.indexOf("/ara") !== -1);
    iddia("EDGE /ara KOLU DA altkategori TASIR",
      araIstek.length > 0 && araIstek[araIstek.length - 1].indexOf("altkategori=Bujiler") !== -1,
      araIstek[araIstek.length - 1] || "(hic)");
  } else {
    // YEREL modda filtre ISTEMCIDE kosar: marka + grup KESISIMI dogru mu.
    const s = await sayfaKur("yerel", "?kategori=Marin&altkategori=Bujiler&marka=Champion");
    const beklenen = say((p) => p.kategori === "Marin" && p.altkategori === "Bujiler" &&
                                (p.marka || []).indexOf("Champion") !== -1);
    const sapan = s.kartIdleri().filter((id) => ALT_HARITA[id] !== "Bujiler");
    iddia("YEREL MARKA+GRUP KESISIMI DOGRU",
      s.sayi() === beklenen && sapan.length === 0,
      "sayi=" + s.sayi() + " beklenen=" + beklenen + " sapan=" + sapan.length);
  }
}

// --- 13) IKIZ: CALISMA ZAMANI ALTKATEGORILER == arama.ALTKATEGORI_IZINLI ---
async function ikizKos() {
  const s = await sayfaKur("edge", "");
  // Blok degeri IIFE kapanisinda; DOM'dan gozlenebilir yuzeyi cip evrenidir. Her
  // kategori TEK TEK gezilir -> tek bir kategorinin sessizce ayrismasi da yakalanir.
  const sapan = [];
  const kategoriler = Object.keys(IZINLI);
  for (const kat of kategoriler) {
    const s2 = await sayfaKur("edge", "?kategori=" + encodeURIComponent(kat));
    const beklenen = ["Tümü"].concat(IZINLI[kat]);
    const goruldu = s2.cipler();
    if (JSON.stringify(goruldu) !== JSON.stringify(beklenen)) {
      sapan.push(kat + " (" + goruldu.length + "/" + beklenen.length + ")");
    }
  }
  iddia("IKIZ TAZELIK — cip evreni arama.ALTKATEGORI_IZINLI ile BIREBIR",
    sapan.length === 0, kategoriler.length + " kategori; sapan=" + sapan.length +
    (sapan.length ? " [" + sapan.join(", ") + "]" : ""));
  void s;
}

(async () => {
  try {
    await modKos("edge");
    await modKos("yerel");
    await ikizKos();
  } catch (e) {
    // Cokme SESSIZ GECMEZ: ayri bir KALDI iddiasi olur (cikis kodu ile karismasin diye
    // hukum Python tarafinda verilir).
    iddia("KOSUM TAMAMLANDI (cokme yok)", false, String((e && e.message) || e));
  }
  process.stdout.write(JSON.stringify({ iddialar: IDDIALAR }, null, 1));
})();
