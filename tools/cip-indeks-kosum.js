#!/usr/bin/env node
/**
 * CIP SATIRLARI (MARKA · GRUP · MODEL) — DAVRANIS KOSUMU (kabul testinin ICRA KOLU).
 *
 *   node tools/cip-indeks-kosum.js --kok <agac> --katalog <json> --indeks <json>
 *
 * BU DOSYA TEK BASINA BIR KAPI DEGILDIR: iddialari JSON olarak stdout'a basar, HUKMU
 * tools/cip-indeks-test.py verir (CI girisi odur). Adi bilerek "-test.js" DEGIL —
 * tools/ci-kapsam-test.py kesfi ikinci bir CI girisi beklemesin.
 *
 * NASIL OLCER: index.html'in GERCEK inline scripti node:vm icinde, minimal DOM taklidi +
 * SAHTE fetch ile CALISTIRILIR (kod KOPYALANMAZ; emsal: tools/altkategori-cip-kosum.js).
 * Cipler GERCEKTEN tiklanir, URL GERCEKTEN yazilir/okunur, liste GERCEKTEN yeniden cizilir.
 *
 * CIP INDEKSI (window.PRUVO_CIP_INDEKS) kosum tarafindan UYDURULMAZ: Python yargici
 * GERCEK ureteci (tools/cip-indeks.py) fikstur katalogu uzerinde calistirip verir. Boylece
 * uretec ile istemci TEK OLCUMDE olculur — birinde mutasyon otekini de kirmizi yakar.
 *
 * IKI MOD DA KOSAR (filtre IKI AYRI YOLDA yasar, biri sessizce kopabilir):
 *   edge  (EDGE_KATALOG=true, CANLI hal): istemci parametreleri Worker'a GONDERIR.
 *   yerel (bayrak false, geri donus yolu): filtre istemcide kosar.
 *
 * SAHTE SUNUCU CANLI UCU TAKLIT EDER (olculdu 2 Agu): kategori/altkategori/marka/model
 * TAM ESITLIKLE suzulur. AYRICA `--yoksay <eksen>` senaryolarinda uc BILEREK bozulur
 * (parametreyi yok sayar / karttan alani duserir) — cunku ayni gun daha ONCE olculdugunde
 * `model` SESSIZCE YOK SAYILIYORDU (marka+model -> marka toplaminin aynisi). Fail-open
 * yasagi bu REGRESYON senaryosuyla olculur, "bugun calisiyor"a guvenilmez.
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
const KATALOG = JSON.parse(fs.readFileSync(arg("katalog"), "utf8"));
const INDEKS = JSON.parse(fs.readFileSync(arg("indeks"), "utf8"));

const INDEX_METIN = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const SECENEK_SRC = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));

const SCRIPT_EDGE = inlineScriptBul(INDEX_METIN, "renderGrid");
if (!SCRIPT_EDGE) { throw new Error("index.html inline katalog scripti bulunamadi"); }
const BAYRAK_ACIK = "var EDGE_KATALOG = true;";
if (SCRIPT_EDGE.indexOf(BAYRAK_ACIK) === -1) {
  throw new Error("EDGE_KATALOG capasi bulunamadi (index.html yapisi degisti mi?)");
}
const SCRIPT_YEREL = SCRIPT_EDGE.replace(BAYRAK_ACIK, "var EDGE_KATALOG = false;");

// ---------------------------------------------------------------- yardimcilar
const HAM = (p) => (p.marka || []).map((x) => String(x).trim()).filter(Boolean);
// index.html markaKatla'nin fikstur icin YETERLI karsiligi: fikstur markalari
// TANINMIS_MARKALAR'da AYNEN yazili (varyant/onek yok), bu yuzden katlama kimliktir.
// (Katlama davranisi ayri bir kapinin — tools/marka-liste-test.py — konusu.)
const say = (f) => KATALOG.filter(f).length;
const sayKM = (kat, altk, marka, model) => say((p) =>
  (kat === null || p.kategori === kat) &&
  (altk === null || (p.altkategori || "") === altk) &&
  (marka === null || HAM(p).indexOf(marka) !== -1) &&
  (model === null || HAM(p).indexOf(model) !== -1));

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
  el.tetikle = (t, ev) => { const fn = el._dinleyiciler[t]; if (fn) { return fn(ev || { preventDefault() {} }); } };
  el.focus = () => {};
  el.scrollIntoView = () => { el._gorunurKilindi = true; };
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
// Worker'in katMarkaAltKosulu'yla AYNI kural: kategori/altkategori/marka/model TAM
// ESITLIK (`marka` JSON dizisinde uyelik), q baslikta alt-dize.
// yoksay: bir ekseni BILEREK yok saydirir — "uc suzmeyi birakirsa" REGRESYON provasi.
function sunucuSuz(u, yoksay) {
  const q = u.searchParams;
  const kategori = q.get("kategori") || "";
  const marka = q.get("marka") || "";
  const alt = q.get("altkategori") || "";
  const model = q.get("model") || "";
  const ara = (q.get("q") || "").toLocaleLowerCase("tr");
  return KATALOG.filter((p) => {
    if (kategori && p.kategori !== kategori) { return false; }
    if (alt && yoksay !== "altkategori" && (p.altkategori || "") !== alt) { return false; }
    if (marka && yoksay !== "marka" && HAM(p).indexOf(marka) === -1) { return false; }
    if (model && yoksay !== "model" && HAM(p).indexOf(model) === -1) { return false; }
    if (ara && p.baslik.toLocaleLowerCase("tr").indexOf(ara) === -1) { return false; }
    return true;
  });
}
function kartOzeti(p, yoksay) {
  const k = {
    id: p.id, baslik: p.baslik, kategori: p.kategori, marka: p.marka || [],
    fiyat: p.fiyat, gorsel: (p.gorseller || [null])[0], parametrik: false,
    aciklama: (p.aciklama || "").slice(0, 160),
  };
  if (p.altkategori) { k.altkategori = p.altkategori; }
  // "kart-marka": uc kartin `marka` alanini DUSURUR -> istemci DOGRULAYAMAZ.
  // "Olcemedim" YESIL DEGILDIR: bu durum da REDDEDILMELI.
  if (yoksay === "kart-marka") { delete k.marka; }
  return k;
}

// ---------------------------------------------------------------- sayfa kurucu
function bekle(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function sayfaKur(mod, search, secenek) {
  const ayar = secenek || {};
  const indeksVar = ayar.indeks !== false;
  const yoksay = ayar.yoksay || null;
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
        const markalar = {};
        KATALOG.forEach((p) => {
          markalar[p.kategori] = markalar[p.kategori] || {};
          HAM(p).forEach((b) => { markalar[p.kategori][b] = (markalar[p.kategori][b] || 0) + 1; });
        });
        return cevap({
          surum: 1, toplam: KATALOG.length, kategoriler: {}, markalar,
          parametrik: [], bloklar: {}, yeni: KATALOG.map((p) => kartOzeti(p)), vitrin: {},
        });
      }
      if (u.pathname.indexOf("urunler.json") !== -1) { return cevap(KATALOG); }
      if (u.pathname.indexOf("/katalog") !== -1 || u.pathname.indexOf("/ara") !== -1) {
        const hepsi = sunucuSuz(u, yoksay);
        const boy = Number(u.searchParams.get("boy") || u.searchParams.get("limit") || 24);
        const sayfa = Number(u.searchParams.get("sayfa") || 1);
        const dilim = u.searchParams.get("limit")
          ? hepsi.slice(0, boy)
          : hepsi.slice((sayfa - 1) * boy, sayfa * boy);
        return cevap({ toplam: hepsi.length, sayfa, sayfaBoyu: boy,
                       urunler: dilim.map((p) => kartOzeti(p, yoksay)) });
      }
      return cevap({});
    },
    console: { log() {}, warn() {}, error(...a) { konsolHatalari.push(a.map(String).join(" ")); } },
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
  // GERCEK uretecin ciktisi — kosum UYDURMAZ (build.py yayin kopyasina bunu gomer).
  if (indeksVar) { ctx.PRUVO_CIP_INDEKS = JSON.parse(JSON.stringify(INDEKS)); }
  vm.createContext(ctx);
  vm.runInContext(SECENEK_SRC, ctx, { filename: "secenekler.js" });
  vm.runInContext(mod === "yerel" ? SCRIPT_YEREL : SCRIPT_EDGE, ctx, { filename: "index-inline.js" });
  await bekle(20); await bekle(20); await bekle(320);

  const el = (id) => belge.getElementById(id);
  const dur = async () => { await bekle(20); await bekle(20); await bekle(320); };

  const cipler = (kutu) => el(kutu).children.map((c) => c.textContent);
  function aktif(kutu) {
    const a = el(kutu).children.filter((c) => c.className.indexOf("active") !== -1);
    return a.length === 1 ? a[0].textContent : (a.length === 0 ? null : "COKLU:" + a.length);
  }
  async function tikla(kutu, ad) {
    const c = el(kutu).children.filter((x) => x.textContent === ad)[0];
    if (!c) { throw new Error(kutu + " cipi yok: " + ad); }
    if (!c.onclick) { throw new Error(kutu + " cipi TIKLANAMAZ (link?): " + ad); }
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
  const urlP = (ad) => new URLSearchParams(konum.search).get(ad);
  async function popstate() {
    if (!pencereDinleyiciler.popstate) { throw new Error("popstate dinleyicisi YOK"); }
    pencereDinleyiciler.popstate({});
    await dur();
  }
  const gorunur = (id) => el(id).style.display !== "none";

  return { ctx, el, cipler, aktif, tikla, katTikla, sayi, kartIdleri, urlP, popstate,
           konum, fetchIzi, konsolHatalari, gorunur, dur };
}

// ---------------------------------------------------------------- iddialar
const IDDIALAR = [];
function iddia(ad, gecti, detay) { IDDIALAR.push({ ad, gecti: !!gecti, detay: String(detay) }); }

// Katalogda hangi kart hangi degeri tasiyor — DEGER ekseni icin harita.
const KART = {};
KATALOG.forEach((p) => {
  KART[p.id] = { kategori: p.kategori, altkategori: p.altkategori || "", marka: HAM(p) };
});

async function modKos(mod) {
  const P = mod.toUpperCase();

  // --- 1) MARKA CIPI LISTEYI DARALTIR (sayi + DEGER) -----------------------
  {
    const s = await sayfaKur(mod, "");
    await s.katTikla("Otomobil");
    const once = s.sayi();
    await s.tikla("brandChips", "BMW");
    const sonra = s.sayi();
    const idler = s.kartIdleri();
    const sapan = idler.filter((id) => KART[id].marka.indexOf("BMW") === -1);
    iddia(P + " MARKA CIPI LISTEYI DARALTIR",
      once === sayKM("Otomobil", null, null, null) &&
      sonra === sayKM("Otomobil", null, "BMW", null) && sonra < once,
      "Otomobil " + once + " -> BMW " + sonra);
    iddia(P + " DONEN URUNLERIN HEPSI SECILEN MARKAYI TASIR (DEGER)",
      idler.length > 0 && sapan.length === 0,
      "kart=" + idler.length + " sapan=" + sapan.length);
  }

  // --- 2) UYDURMA MARKA -> 0 ----------------------------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil&marka=Xyzyokmarka");
    iddia(P + " UYDURMA MARKA -> 0 URUN",
      s.sayi() === 0 && s.kartIdleri().length === 0,
      "sayi=" + s.sayi());
  }

  // --- 3) <15 URUNLU MARKA CIP DEGIL (kontrol: >=15 olan cip) -------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil");
    const c = s.cipler("brandChips");
    iddia(P + " <15 URUNLU MARKA CIP DEGIL (Opel " + sayKM("Otomobil", null, "Opel", null) + ")",
      c.indexOf("Opel") === -1, "cipler=" + JSON.stringify(c));
    iddia(P + " KONTROL: >=15 URUNLU MARKA CIP (BMW+Ford)",
      c.indexOf("BMW") !== -1 && c.indexOf("Ford") !== -1, "cipler=" + JSON.stringify(c));
  }

  // --- 4) GRUP SECILINCE MARKA SATIRI DARALIR -----------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Marin");
    const genis = s.cipler("brandChips");
    const s2 = await sayfaKur(mod, "?kategori=Marin&altkategori=Motor Parçaları");
    const dar = s2.cipler("brandChips");
    iddia("" + P + " GRUP SECILINCE MARKA SATIRI DARALIR (Marin/Motor Parçaları)",
      genis.indexOf("Yamaha") !== -1 && dar.indexOf("Yamaha") === -1 &&
      dar.indexOf("Mercury") !== -1,
      "grupsuz=" + JSON.stringify(genis) + " -> grup=" + JSON.stringify(dar));
  }

  // --- 5) GORUNEN HER MARKA CIPI >0 (TEK TEK, ORNEKLEME YOK) --------------
  for (const [kat, altk] of [["Otomobil", null], ["Otomobil", "Aydınlatma"],
                             ["Marin", null], ["Marin", "Motor Parçaları"],
                             ["Marin", "Pervaneler"]]) {
    const url = "?kategori=" + encodeURIComponent(kat) +
      (altk ? "&altkategori=" + encodeURIComponent(altk) : "");
    const s = await sayfaKur(mod, url);
    const adlar = s.cipler("brandChips").filter((x) => x !== "Tümü");
    const bos = [];
    for (const ad of adlar) {
      const t = await sayfaKur(mod, url + "&marka=" + encodeURIComponent(ad));
      if (t.sayi() <= 0) { bos.push(ad + "=" + t.sayi()); }
    }
    iddia(P + " HER MARKA CIPI >0 [" + kat + (altk ? "/" + altk : "") + "]",
      adlar.length > 0 && bos.length === 0,
      "cip=" + adlar.length + " bos=" + bos.length + (bos.length ? " [" + bos.join(",") + "]" : ""));
  }

  // --- 6) MARKA SECILINCE GRUP SATIRI DARALIR + KENDI EKSENI DARALMAZ -----
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil");
    const genis = s.cipler("altChips");
    const s2 = await sayfaKur(mod, "?kategori=Otomobil&marka=Ford");
    const dar = s2.cipler("altChips");
    iddia(P + " MARKA SECILINCE GRUP SATIRI DARALIR (Ford)",
      genis.indexOf("Aydınlatma") !== -1 && dar.indexOf("Aydınlatma") === -1 &&
      dar.indexOf("Motor Bölümü") !== -1,
      "markasiz=" + JSON.stringify(genis) + " -> Ford=" + JSON.stringify(dar));

    // KENDI EKSENI: grup secili iken DIGER gruplara gecilebilmeli
    const s3 = await sayfaKur(mod, "?kategori=Otomobil&marka=BMW&altkategori=Motor Bölümü");
    const c3 = s3.cipler("altChips");
    iddia(P + " GRUP SATIRI KENDI SECIMIYLE DARALMAZ (baska gruba gecilebilir)",
      c3.indexOf("Aydınlatma") !== -1 && c3.indexOf("Motor Bölümü") !== -1,
      "cipler=" + JSON.stringify(c3));
  }

  // --- 7) GORUNEN HER GRUP CIPI >0 ----------------------------------------
  for (const [kat, marka] of [["Otomobil", null], ["Otomobil", "BMW"], ["Otomobil", "Ford"],
                              ["Marin", "Mercury"]]) {
    const url = "?kategori=" + encodeURIComponent(kat) +
      (marka ? "&marka=" + encodeURIComponent(marka) : "");
    const s = await sayfaKur(mod, url);
    const adlar = s.cipler("altChips").filter((x) => x !== "Tümü");
    const bos = [];
    for (const ad of adlar) {
      const t = await sayfaKur(mod, url + "&altkategori=" + encodeURIComponent(ad));
      if (t.sayi() <= 0) { bos.push(ad + "=" + t.sayi()); }
    }
    iddia(P + " HER GRUP CIPI >0 [" + kat + (marka ? "/" + marka : "") + "]",
      adlar.length > 0 && bos.length === 0,
      "cip=" + adlar.length + " bos=" + bos.length + (bos.length ? " [" + bos.join(",") + "]" : ""));
  }

  // --- 8) MODEL SATIRI: yalniz secili markada -----------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil");
    iddia(P + " MARKA SECILI DEGILKEN MODEL SATIRI YOK",
      s.gorunur("modelRow") === false && s.cipler("modelChips").length === 0,
      "gorunur=" + s.gorunur("modelRow") + " cip=" + s.cipler("modelChips").length);
    const s2 = await sayfaKur(mod, "?kategori=Otomobil&marka=BMW");
    iddia(P + " MARKA SECILINCE MODEL SATIRI VAR (BMW)",
      s2.gorunur("modelRow") === true && s2.cipler("modelChips").length > 1,
      "gorunur=" + s2.gorunur("modelRow") + " cipler=" + JSON.stringify(s2.cipler("modelChips")));
    // MODELLER YALNIZ O MARKANIN: Ford'un modeli (Focus) BMW satirinda GORUNMEZ
    iddia(P + " MODEL CIPLERI YALNIZ SECILI MARKANIN",
      s2.cipler("modelChips").indexOf("Focus") === -1 &&
      s2.cipler("modelChips").indexOf("E46") !== -1,
      "cipler=" + JSON.stringify(s2.cipler("modelChips")));
  }

  // --- 9) MODEL SATIRI yalniz >=2 MODELLI markada -------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil&marka=Ford");
    iddia(P + " TEK MODELLI MARKADA MODEL SATIRI YOK (Ford)",
      s.gorunur("modelRow") === false, "gorunur=" + s.gorunur("modelRow") +
      " cipler=" + JSON.stringify(s.cipler("modelChips")));
  }

  // --- 10) MODEL CIPI DARALTIR + DEGER ekseni -----------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil&marka=BMW");
    const once = s.sayi();
    await s.tikla("modelChips", "E46");
    const sonra = s.sayi();
    const idler = s.kartIdleri();
    const sapan = idler.filter((id) => KART[id].marka.indexOf("E46") === -1);
    iddia(P + " MODEL CIPI LISTEYI DARALTIR (BMW -> E46)",
      once === sayKM("Otomobil", null, "BMW", null) &&
      sonra === sayKM("Otomobil", null, "BMW", "E46") && sonra < once,
      "BMW " + once + " -> E46 " + sonra);
    iddia(P + " MODELDE DONEN URUNLERIN HEPSI O MODELI TASIR (DEGER)",
      idler.length > 0 && sapan.length === 0,
      "kart=" + idler.length + " sapan=" + sapan.length);
    iddia(P + " SECILI MODEL CIPI AKTIF", s.aktif("modelChips") === "E46",
      "aktif=" + s.aktif("modelChips"));
    await s.tikla("modelChips", "E46");
    iddia(P + " MODEL: TEKRAR TIK SECIMI TEMIZLER",
      s.sayi() === once && s.urlP("model") === null,
      "sayi=" + s.sayi() + " url=" + s.urlP("model"));
  }

  // --- 11) UYDURMA MODEL -> 0 ---------------------------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil&marka=BMW&model=xyzyok");
    iddia(P + " UYDURMA MODEL -> 0 URUN",
      s.sayi() === 0 && s.kartIdleri().length === 0, "sayi=" + s.sayi());
    iddia(P + " KUME DISI MODEL CIPI GORUNUR (temizleme yolu kalir)",
      s.cipler("modelChips").indexOf("xyzyok") !== -1,
      "cipler=" + JSON.stringify(s.cipler("modelChips")));
  }

  // --- 12) GORUNEN HER MODEL CIPI >0 --------------------------------------
  {
    const url = "?kategori=Otomobil&marka=BMW";
    const s = await sayfaKur(mod, url);
    const adlar = s.cipler("modelChips").filter((x) => x !== "Tümü");
    const bos = [];
    for (const ad of adlar) {
      const t = await sayfaKur(mod, url + "&model=" + encodeURIComponent(ad));
      if (t.sayi() <= 0) { bos.push(ad + "=" + t.sayi()); }
    }
    iddia(P + " HER MODEL CIPI >0 (BMW)",
      adlar.length >= 2 && bos.length === 0,
      "cip=" + adlar.length + " bos=" + bos.length + (bos.length ? " [" + bos.join(",") + "]" : ""));
  }

  // --- 13) SECILI CIP DARALMA SONUCU DUSSE BILE GORUNUR -------------------
  {
    // Mercury'nin "Pervaneler" grubunda urunu YOK; marka+grup birlikte secilirse
    // marka cipi daralma kumesinden DUSER ama GORUNUR kalmali (geri alma yolu).
    const s = await sayfaKur(mod, "?kategori=Marin&altkategori=Pervaneler&marka=Mercury");
    iddia(P + " SECILI MARKA CIPI DARALMADA DUSSE BILE GORUNUR",
      s.cipler("brandChips").indexOf("Mercury") !== -1 && s.aktif("brandChips") === "Mercury",
      "cipler=" + JSON.stringify(s.cipler("brandChips")));
    iddia(P + " KONTROL: o kombinasyon GERCEKTEN BOS (0 urun)",
      s.sayi() === 0 && sayKM("Marin", "Pervaneler", "Mercury", null) === 0,
      "sayi=" + s.sayi());
  }

  // --- 14) URL ROUND-TRIP (marka+model) + GERI/ILERI -----------------------
  {
    const s1 = await sayfaKur(mod, "");
    await s1.katTikla("Otomobil");
    await s1.tikla("brandChips", "BMW");
    await s1.tikla("modelChips", "E46");
    const yazilan = s1.konum.search;
    const sayi1 = s1.sayi();
    iddia(P + " URL'YE marka+model YAZILIYOR",
      s1.urlP("marka") === "BMW" && s1.urlP("model") === "E46", "search=" + yazilan);

    const s2 = await sayfaKur(mod, yazilan);
    iddia(P + " URL ROUND-TRIP (yaz -> oku -> ayni secim)",
      s2.aktif("brandChips") === "BMW" && s2.aktif("modelChips") === "E46" &&
      s2.sayi() === sayi1,
      "marka=" + s2.aktif("brandChips") + " model=" + s2.aktif("modelChips") +
      " sayi=" + s2.sayi() + " (yazan " + sayi1 + ")");

    s2.konum.search = "?kategori=Otomobil&marka=BMW";
    await s2.popstate();
    iddia(P + " GERI/ILERI (popstate) MODEL SECIMINI URL'YE OTURTUR",
      s2.urlP("model") === null && s2.aktif("modelChips") === "Tümü" &&
      s2.sayi() === sayKM("Otomobil", null, "BMW", null),
      "url=" + s2.urlP("model") + " aktif=" + s2.aktif("modelChips") + " sayi=" + s2.sayi());
  }

  // --- 15) MARKA DEGISINCE MODEL DUSER ------------------------------------
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil&marka=BMW&model=E46");
    await s.tikla("brandChips", "Ford");
    iddia(P + " MARKA DEGISINCE SECILI MODEL DUSER",
      s.urlP("model") === null && s.sayi() === sayKM("Otomobil", null, "Ford", null),
      "url=" + s.urlP("model") + " sayi=" + s.sayi());
  }

  // --- 16) INDEKS YOKSA: MODEL SATIRI HIC CIZILMEZ, FILTRELER CALISIR -----
  {
    const s = await sayfaKur(mod, "?kategori=Otomobil&marka=BMW", { indeks: false });
    iddia(P + " INDEKS YOKSA MODEL SATIRI YOK (fail-closed geri donus)",
      s.gorunur("modelRow") === false && s.cipler("modelChips").length === 0,
      "gorunur=" + s.gorunur("modelRow"));
    iddia(P + " INDEKS YOKSA MARKA FILTRESI YINE CALISIR",
      s.sayi() === sayKM("Otomobil", null, "BMW", null), "sayi=" + s.sayi());
    // Kontrol: daralma YOK -> <15 marka (Opel) yine cip olur (bugunku davranis)
    const s2 = await sayfaKur(mod, "?kategori=Otomobil", { indeks: false });
    iddia(P + " INDEKS YOKSA CAPRAZ DARALMA YAPILMAZ (kontrol ekseni)",
      s2.cipler("brandChips").indexOf("Opel") !== -1,
      "cipler=" + JSON.stringify(s2.cipler("brandChips")));
  }
}

// ---------------------------------------------------------------- moda ozgu
async function edgeOzel() {
  // --- E0) UC MARKA ETIKETI: cip KATLANMIS, uc HAM ister -----------------
  // Olculen CANLI hata (3 Agu): /katalog?kategori=Marin&marka=Volvo -> 0 (51 urun kayip);
  // marka=Volvo Penta -> 51. Uc TAM eslesir, KATLAMAZ. Bu iddia istemcinin uca HANGI
  // etiketi gonderdigini fetch izinden okur — DOM'da cip aramak bu sinifi gormez.
  // KONTROL EKSENI hemen altinda: kanonik = ham olan markada etiket DEGISMEMELI
  // (yoksa "her marka icin `e` uret" mutanti da yesil gecerdi).
  {
    const s = await sayfaKur("edge", "?kategori=Marin&marka=Volvo");
    const son = s.fetchIzi[s.fetchIzi.length - 1] || "";
    iddia("EDGE UCA HAM MARKA ETIKETI GIDER (cip 'Volvo' -> uc 'Volvo Penta')",
      son.indexOf("marka=Volvo+Penta") !== -1 || son.indexOf("marka=Volvo%20Penta") !== -1,
      "istek=" + son);
    iddia("EDGE KATLANMIS CIP >0 URUN DONDURUR (olu uc yok)",
      s.sayi() === sayKM("Marin", null, "Volvo Penta", null) && s.sayi() > 0,
      "sayi=" + s.sayi() + " beklenen=" + sayKM("Marin", null, "Volvo Penta", null));
    iddia("EDGE SECILI CIP ETIKETI KATLANMIS KALIR (musteri 'Volvo' gorur)",
      s.aktif("brandChips") === "Volvo", "aktif=" + s.aktif("brandChips"));

    const t = await sayfaKur("edge", "?kategori=Marin&marka=Mercury");
    const sonT = t.fetchIzi[t.fetchIzi.length - 1] || "";
    iddia("EDGE KONTROL: KANONIK=HAM MARKADA ETIKET DEGISMEZ (Mercury)",
      sonT.indexOf("marka=Mercury") !== -1 && t.sayi() === sayKM("Marin", null, "Mercury", null),
      "istek=" + sonT + " sayi=" + t.sayi());
  }

  // --- E1) MODEL `model=` PARAMETRESIYLE GIDER, MARKA KORUNUR -------------
  {
    const s = await sayfaKur("edge", "?kategori=Otomobil&marka=BMW");
    await s.tikla("modelChips", "E46");
    const son = s.fetchIzi[s.fetchIzi.length - 1] || "";
    iddia("EDGE MODEL `model=` PARAMETRESIYLE GONDERILIR (marka KORUNUR)",
      son.indexOf("model=E46") !== -1 && son.indexOf("marka=BMW") !== -1, "istek=" + son);
    iddia("EDGE MODEL SECIMINDE LISTE DARALIR (uc suzer)",
      s.sayi() === sayKM("Otomobil", null, "BMW", "E46") && s.sayi() > 0,
      "sayi=" + s.sayi());
  }

  // --- E2) FAIL-OPEN YASAGI: uc `model`i YOK SAYARSA SESSIZCE GECMEZ -----
  // Bu senaryo bir REGRESYON provasi: ayni gun daha ONCE canli uc `model`i sessizce
  // yok sayiyordu (marka+model -> marka toplaminin AYNISI). Uc bugun suzuyor diye
  // istemcinin dogrulamayi birakmasi, o gunku hatanin geri gelmesini SESSIZ yapardi.
  {
    const s = await sayfaKur("edge", "?kategori=Otomobil&marka=BMW", { yoksay: "model" });
    await s.tikla("modelChips", "E46");
    const uyari = s.el("edgeDurum");
    iddia("EDGE UC MODELI YOK SAYARSA LISTE SESSIZCE KABUL EDILMEZ (fail-open yasagi)",
      s.kartIdleri().length === 0 && s.sayi() === 0,
      "kart=" + s.kartIdleri().length + " sayi=" + s.sayi());
    iddia("EDGE SUZMEME DURUMU GORUNUR UYARI BASAR",
      uyari.style.display !== "none" && /uyari/.test(uyari.className) &&
      (uyari.innerHTML || "").length > 20,
      "display=" + uyari.style.display + " sinif=" + uyari.className);
    iddia("EDGE SUZMEME KONSOLA ADIYLA YAZILIR (sessiz degil)",
      s.konsolHatalari.some((x) => x.indexOf("suzgec UYGULANMADI") !== -1),
      "hatalar=" + JSON.stringify(s.konsolHatalari).slice(0, 200));
    // KONTROL: AYNI tik DURUST sunucuda GECER (guard her model tikini reddetmiyor)
    const t = await sayfaKur("edge", "?kategori=Otomobil&marka=BMW");
    await t.tikla("modelChips", "E46");
    iddia("EDGE KONTROL: durust sunucuda ayni model tiki GECER",
      t.sayi() === sayKM("Otomobil", null, "BMW", "E46") && t.sayi() > 0,
      "sayi=" + t.sayi());
  }

  // --- E2b) DOGRULANAMAYAN CEVAP DE REDDEDILIR ("olcemedim" YESIL DEGIL) --
  {
    const s = await sayfaKur("edge", "?kategori=Otomobil&marka=BMW&model=E46",
      { yoksay: "kart-marka" });
    iddia("EDGE KART `marka` TASIMIYORSA DOGRULANAMAZ -> REDDEDILIR",
      s.kartIdleri().length === 0 && s.sayi() === 0,
      "kart=" + s.kartIdleri().length + " sayi=" + s.sayi());
    iddia("EDGE DOGRULANAMAZ CEVAP KONSOLA 'olculemedi' EKSENIYLE YAZILIR",
      s.konsolHatalari.some((x) => x.indexOf("olculemedi") !== -1),
      "hatalar=" + JSON.stringify(s.konsolHatalari).slice(0, 200));
  }

  // --- E3) GUARD EKSEN-BAGIMSIZ: uc `altkategori`yi yok sayarsa da reddet -
  {
    const s = await sayfaKur("edge", "?kategori=Otomobil&altkategori=Aydınlatma",
      { yoksay: "altkategori" });
    iddia("EDGE GUARD EKSEN-BAGIMSIZ (grup yok sayilirsa da reddedilir)",
      s.kartIdleri().length === 0 && s.sayi() === 0, "sayi=" + s.sayi());
    // KONTROL: ayni istek DURUST sunucuda GECER (guard her seyi reddetmiyor)
    const t = await sayfaKur("edge", "?kategori=Otomobil&altkategori=Aydınlatma");
    iddia("EDGE KONTROL: durust sunucuda ayni istek GECER",
      t.sayi() === sayKM("Otomobil", "Aydınlatma", null, null) && t.sayi() > 0,
      "sayi=" + t.sayi());
  }

  // --- E4) /ara kolu da model parametresini tasir -------------------------
  {
    const s = await sayfaKur("edge", "?kategori=Otomobil&marka=BMW");
    await s.tikla("modelChips", "E46");
    s.el("search").value = "Test";
    s.el("search").tetikle("input", {});
    await bekle(20); await bekle(400);
    const ara = s.fetchIzi.filter((u) => u.indexOf("/ara") !== -1);
    iddia("EDGE /ara KOLU DA MODEL EKSENINI TASIR",
      ara.length > 0 && ara[ara.length - 1].indexOf("model=E46") !== -1,
      ara[ara.length - 1] || "(hic)");
  }
}

async function yerelOzel() {
  // Belirsiz etiket (E36) YEREL yolda istemcide DOGRU suzulur — "ya yerel yola dus"
  // secenegi fiilen calisiyor mu?
  const s = await sayfaKur("yerel", "?kategori=Otomobil&marka=BMW&model=E36");
  const idler = s.kartIdleri();
  const sapan = idler.filter((id) => KART[id].marka.indexOf("E36") === -1 ||
                                     KART[id].marka.indexOf("BMW") === -1);
  iddia("YEREL BELIRSIZ ETIKET ISTEMCIDE DOGRU SUZULUR (E36)",
    s.sayi() === sayKM("Otomobil", null, "BMW", "E36") && s.sayi() > 0 && sapan.length === 0,
    "sayi=" + s.sayi() + " sapan=" + sapan.length);

  // Arama + model KESISIMI (hs'e model EKLENMEDIGI icin arama metni degismedi;
  // kesisim yine de dogru olmali)
  const t = await sayfaKur("yerel", "?kategori=Otomobil&marka=BMW&model=E46&ara=Test");
  iddia("YEREL ARAMA + MODEL KESISIMI DOGRU",
    t.sayi() === sayKM("Otomobil", null, "BMW", "E46"), "sayi=" + t.sayi());
}

(async () => {
  try {
    await modKos("edge");
    await modKos("yerel");
    await edgeOzel();
    await yerelOzel();
  } catch (e) {
    iddia("KOSUM TAMAMLANDI (cokme yok)", false, String((e && e.stack) || e).slice(0, 400));
  }
  process.stdout.write(JSON.stringify({ iddialar: IDDIALAR }, null, 1));
})();
