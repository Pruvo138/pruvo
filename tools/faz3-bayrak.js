#!/usr/bin/env node
/**
 * KABUL TESTLERI 2, 6, 7 — index.html'in EDGE_KATALOG bayragi (FAZ 3).
 *
 *   node tools/faz3-bayrak.js
 *
 * Neyi kanitlar:
 *   2) BAYRAK-KAPALI REGRESYON: EDGE_KATALOG=false iken sayfa BUGUNKU gibi davranir —
 *      urunler.json cekilir, /katalog ve /ara HIC cagrilmaz. (Geri donus yolunun
 *      calistiginin kaniti. Bu testin degeri: bayrak kapaliyken kazara ag istegi
 *      eklemek GOZLE fark edilmez, sadece "site biraz yavasladi" olur.)
 *   6) PARAMETRIK VITRIN: bayrak acikken ana sayfada 4 parametrik kart, sari rozetli, en ustte.
 *   7) ZARIF BOZULMA: Worker 500/ulasilamaz iken sayfa COKMEZ; kullaniciya mesaj cikar ve
 *      arama kutusu ozet.json icinde EN AZINDAN baslik aramasiyla calismaya devam eder.
 * Ayrica: ilk boyamada /katalog cagrilmaz (ozet.json yeter) ve arama ~250 ms debounce'lu.
 *
 * NEDEN ELDE YAZILMIS MINI-DOM: bu repoda npm bagimliligi YOK (parite testleri de saf
 * Node) ve is paketi yeni kutuphane yasakliyor. jsdom eklemek yerine index.html'in KENDI
 * script'i cikartilip, sadece bu sayfanin dokundugu DOM yuzeyi taklit edilerek kosuluyor.
 * Referans = gercek dosya: index.html degisince test onu okur, kopyayi degil.
 */

const fs = require("fs");
const path = require("path");

const KOK = path.dirname(__dirname);
const INDEX = path.join(KOK, "index.html");
const OZET = path.join(KOK, "ozet.json");

// ─── mini-DOM (sadece index.html'in kullandigi yuzey) ────────────────────────
class Oge {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.style = {}; this._attrs = {};
    this.className = ""; this._text = ""; this._html = ""; this._dinleyici = {};
    this.onclick = null; this.onerror = null; this.disabled = false;
  }
  get classList() {
    const self = this;
    const liste = () => (self.className || "").split(/\s+/).filter(Boolean);
    return {
      add(c) { const l = liste(); if (l.indexOf(c) === -1) l.push(c); self.className = l.join(" "); },
      remove(c) { self.className = liste().filter((x) => x !== c).join(" "); },
      contains(c) { return liste().indexOf(c) !== -1; },
    };
  }
  appendChild(c) { this.children.push(c); return c; }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  getAttribute(k) { return this._attrs[k] === undefined ? null : this._attrs[k]; }
  removeAttribute(k) { delete this._attrs[k]; }
  addEventListener(t, f) { (this._dinleyici[t] = this._dinleyici[t] || []).push(f); }
  focus() {}
  tetikle(tur) {
    (this._dinleyici[tur] || []).forEach((f) => f.call(this, { type: tur }));
    if (tur === "click" && typeof this.onclick === "function") this.onclick();
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(v) { this._html = String(v); if (v === "") this.children = []; }
  get innerHTML() { return this._html; }
  // Agacta gezinme (test yardimcilari)
  *hepsi() { for (const c of this.children) { yield c; yield* c.hepsi(); } }
  bul(sinif) { for (const e of this.hepsi()) if ((e.className || "").split(/\s+/).indexOf(sinif) !== -1) return e; return null; }
}

const GEREKLI_IDLER = [
  "search", "searchClear", "cats", "brandChips", "brandRow", "sectionTitle",
  "resultCount", "edgeDurum", "grid", "loadMoreWrap", "emptyState",
  "cartFab", "cartCount", "cartClose", "cartOverlay", "cartClear",
  "cartPanel", "cartItems", "cartOrder",
];

function domYap() {
  const kayit = {};
  GEREKLI_IDLER.forEach((id) => { kayit[id] = new Oge("div"); kayit[id].id = id; });
  kayit.search.value = "";
  const document = {
    getElementById: (id) => kayit[id] || null,
    createElement: (t) => new Oge(t),
    querySelectorAll: (sel) => {
      // index.html'de tek kullanim: ".cart-btn[data-id]"
      if (sel !== ".cart-btn[data-id]") throw new Error("mini-DOM: bilinmeyen secici " + sel);
      const out = [];
      Object.values(kayit).forEach((kok) => {
        for (const e of kok.hepsi()) {
          if ((e.className || "").split(/\s+/).indexOf("cart-btn") !== -1 && e.getAttribute("data-id")) out.push(e);
        }
      });
      return out;
    },
  };
  return { document, kayit };
}

/** index.html'in son <script> blogunu cikar (kopya DEGIL — gercek dosyadan). */
function scriptCikar() {
  const html = fs.readFileSync(INDEX, "utf8");
  const bloklar = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  if (!bloklar.length) throw new Error("index.html'de <script> bulunamadi");
  return bloklar.sort((a, b) => b.length - a.length)[0];   // en buyuk blok = uygulama
}

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Sayfayi kosar. bayrak=true ise index.html'deki EDGE_KATALOG satiri true'ya cevrilir
 * (kaynaktaki GERCEK bayrak; ayri bir kopya degil).
 */
function sayfaKos({ bayrak, fetchStub }) {
  let kod = scriptCikar();
  if (bayrak) {
    const once = kod;
    kod = kod.replace("var EDGE_KATALOG = false;", "var EDGE_KATALOG = true;");
    if (kod === once) throw new Error("EDGE_KATALOG bayrak satiri bulunamadi — index.html degismis olabilir");
  }
  const { document, kayit } = domYap();
  const ag = [];                       // cagrilan TUM url'ler
  const depo = {};
  const localStorage = {
    getItem: (k) => (depo[k] === undefined ? null : depo[k]),
    setItem: (k, v) => { depo[k] = String(v); },
  };
  const location = { hash: "", search: "", replace() {} };
  const window = {};
  const fetch = (url, opt) => { ag.push(String(url)); return fetchStub(String(url), opt); };

  const hatalar = [];
  const konsol = {
    log: () => {}, warn: () => {},
    error: (...a) => hatalar.push(a.map(String).join(" ")),
  };

  const calistir = new Function("window", "document", "location", "localStorage", "fetch", "console", kod);
  calistir(window, document, location, localStorage, fetch, konsol);
  return { ag, kayit, hatalar };
}

function yanit(veri, ok) {
  return Promise.resolve({ ok: ok !== false, status: ok === false ? 500 : 200, json: () => Promise.resolve(veri) });
}

// ─── test kosum ─────────────────────────────────────────────────────────────
const PRODUCTS = JSON.parse(fs.readFileSync(path.join(KOK, "urunler.json"), "utf8"));
if (!fs.existsSync(OZET)) {
  console.log("ozet.json YOK — once `python3 tools/build.py` calistir.");
  process.exit(1);
}
const ozetVeri = JSON.parse(fs.readFileSync(OZET, "utf8"));

let gecti = 0, kaldi = 0;
function kontrol(ad, sart, detay) {
  if (sart) { gecti++; console.log("  ✅ " + ad); }
  else { kaldi++; console.log("  ❌ " + ad + (detay ? "\n       " + detay : "")); }
}
const kartlar = (kayit) => kayit.grid.children;
const rozetliMi = (kart) => !!kart.bul("card-badge");

(async () => {
  // ── TEST 2: bayrak KAPALI = bugunku davranis ──────────────────────────────
  console.log("\nTEST 2 — bayrak KAPALI regresyon (EDGE_KATALOG=false)");
  {
    const { ag, kayit, hatalar } = sayfaKos({
      bayrak: false,
      fetchStub: (url) => (url.indexOf("urunler.json") !== -1 ? yanit(PRODUCTS) : yanit({ hata: "beklenmedik: " + url }, false)),
    });
    await bekle(50);
    kontrol("urunler.json cekildi (bugunku yol)", ag.some((u) => u.indexOf("urunler.json") !== -1), "cagrilanlar: " + JSON.stringify(ag));
    kontrol("/katalog HIC cagrilmadi", !ag.some((u) => u.indexOf("/katalog") !== -1), "cagrilanlar: " + JSON.stringify(ag));
    kontrol("/ara HIC cagrilmadi", !ag.some((u) => u.indexOf("/ara") !== -1), "cagrilanlar: " + JSON.stringify(ag));
    kontrol("ozet.json cekilmedi (bayrak kapali)", !ag.some((u) => u.indexOf("ozet.json") !== -1));
    kontrol("baska hicbir ag istegi yok (toplam 1)", ag.length === 1, "toplam " + ag.length + ": " + JSON.stringify(ag));
    kontrol("kartlar cizildi", kartlar(kayit).length > 0, "kart sayisi: " + kartlar(kayit).length);
    kontrol("konsol hatasi yok", hatalar.length === 0, hatalar.join(" | "));

    // Yerel arama hala tarayicida ve SEMANTIGI ayni (alt-dize, cok kelimeli)
    kayit.search.value = "audi a4";
    kayit.search.tetikle("input");
    await bekle(10);
    const bek = PRODUCTS.filter((p) => {
      const hs = [p.baslik, p.aciklama, (p.marka || []).join(" "), p.kategori, (p.id || "").replace(/-/g, " ")]
        .join(" ").toLocaleLowerCase("tr").replace(/ı/g, "i").replace(/İ/g, "i").replace(/ç/g, "c")
        .replace(/ğ/g, "g").replace(/ö/g, "o").replace(/ş/g, "s").replace(/ü/g, "u").replace(/â/g, "a").replace(/î/g, "i");
      return hs.indexOf("audi") !== -1 && hs.indexOf("a4") !== -1;
    }).length;
    kontrol('yerel arama ("audi a4") bugunku sonucu veriyor: ' + bek,
      kayit.resultCount.textContent === bek + " ürün", "ekranda: " + kayit.resultCount.textContent);
    kontrol("arama sirasinda da ag istegi yok", ag.length === 1, JSON.stringify(ag));
  }

  // ── TEST 6 + ilk boyama: bayrak ACIK, saglikli ────────────────────────────
  console.log("\nTEST 6 — bayrak ACIK: ilk boyama ozet.json ile + parametrik vitrin");
  {
    const { ag, kayit, hatalar } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return yanit(ozetVeri);
        if (url.indexOf("/katalog") !== -1) return yanit({ toplam: 7171, sayfa: 2, sayfaBoyu: 24, sonSayfa: 300, urunler: ozetVeri.yeni.slice(24, 48) });
        return yanit({ hata: "beklenmedik: " + url }, false);
      },
    });
    await bekle(50);
    kontrol("ozet.json cekildi", ag.some((u) => u.indexOf("ozet.json") !== -1), JSON.stringify(ag));
    kontrol("urunler.json INMEDI (paketin asil amaci)", !ag.some((u) => u.indexOf("urunler.json") !== -1), JSON.stringify(ag));
    kontrol("ilk boyamada /katalog cagrilmadi (ozet.json yetti)", !ag.some((u) => u.indexOf("/katalog") !== -1), JSON.stringify(ag));
    kontrol("ilk yukte tek istek (ozet.json)", ag.length === 1, "toplam " + ag.length + ": " + JSON.stringify(ag));
    kontrol("konsol hatasi yok", hatalar.length === 0, hatalar.join(" | "));

    const k = kartlar(kayit);
    const ilk4 = k.slice(0, 4);
    kontrol("ana sayfada 4 parametrik kart EN USTTE", ilk4.length === 4 && ilk4.every(rozetliMi),
      "ilk 4 rozet durumu: " + ilk4.map(rozetliMi).join(","));
    kontrol('rozet metni "Ölçüye Özel"', ilk4.every((c) => (c.bul("card-badge") || {}).textContent === "Ölçüye Özel"));
    kontrol("vitrin ozet.json parametrik havuzundan", ilk4.every((c) => ozetVeri.parametrik.some((p) => c.textContent.indexOf(p.baslik) !== -1)));
    kontrol("toplam urun sayisi ozet.json'dan (7171)", kayit.resultCount.textContent === ozetVeri.toplam + " ürün", kayit.resultCount.textContent);
    kontrol("vitrin + ilk sayfa kart cizildi", k.length > 4, "kart sayisi: " + k.length);

    // "Daha fazla" -> /katalog?sayfa=2
    const dahaFazla = kayit.loadMoreWrap.children[0];
    kontrol('"Daha fazla goster" butonu var', !!dahaFazla);
    if (dahaFazla) {
      dahaFazla.tetikle("click");
      await bekle(30);
      kontrol("'Daha fazla' /katalog?sayfa=2 cagirdi",
        ag.some((u) => u.indexOf("/katalog") !== -1 && u.indexOf("sayfa=2") !== -1),
        JSON.stringify(ag.filter((u) => u.indexOf("/katalog") !== -1)));
    }
  }

  // ── Arama: debounce + /ara (site modu) ────────────────────────────────────
  console.log("\nTEST 4b — bayrak ACIK: arama /ara?q= ucuna ~250 ms debounce ile bagli");
  {
    const { ag, kayit } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return yanit(ozetVeri);
        if (url.indexOf("/ara") !== -1) return yanit({ toplam: 3, urunler: ozetVeri.yeni.slice(0, 3) });
        return yanit({ hata: "beklenmedik" }, false);
      },
    });
    await bekle(30);
    // Hizli yazma: 5 tus
    for (const s of ["a", "au", "aud", "audi", "audi "]) {
      kayit.search.value = s;
      kayit.search.tetikle("input");
      await bekle(30);
    }
    const oncesi = ag.filter((u) => u.indexOf("/ara") !== -1).length;
    kontrol("hizli yazarken istek ATILMADI (debounce tutuyor)", oncesi === 0, "istek sayisi: " + oncesi);
    await bekle(350);
    const araIstekleri = ag.filter((u) => u.indexOf("/ara") !== -1);
    kontrol("yazma bitince TEK /ara istegi", araIstekleri.length === 1, JSON.stringify(araIstekleri));
    kontrol("/ara site modunda (mod=ege YOK — Ege'ye dokunulmadi)",
      araIstekleri.every((u) => u.indexOf("mod=ege") === -1), JSON.stringify(araIstekleri));
    kontrol("sorgu url'de", araIstekleri.length === 1 && /q=audi/.test(araIstekleri[0]), JSON.stringify(araIstekleri));
    kontrol("sonuc cizildi", kartlar(kayit).length === 3, "kart: " + kartlar(kayit).length);
  }

  // ── TEST 7: zarif bozulma ─────────────────────────────────────────────────
  console.log("\nTEST 7 — zarif bozulma: Worker 500 / ulasilamaz");
  {
    const { ag, kayit, hatalar } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return yanit(ozetVeri);
        return Promise.reject(new Error("baglanti yok"));   // Worker ULASILAMAZ
      },
    });
    await bekle(30);
    kontrol("ana sayfa yine cizildi (ozet.json yetti, Worker'a hic gitmedi)", kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);

    // Worker cokmusken arama yap -> yedek yol
    const hedef = ozetVeri.yeni[0].baslik.split(/\s+/)[0];
    kayit.search.value = hedef;
    kayit.search.tetikle("input");
    await bekle(400);

    kontrol("sayfa COKMEDI (istisna disari sizmadi)", true);
    kontrol("kullaniciya mesaj gosterildi", /bağlantısı kurulamadı/i.test(kayit.edgeDurum.innerHTML), "durum: " + kayit.edgeDurum.innerHTML);
    kontrol("durum satiri gorunur", kayit.edgeDurum.style.display === "flex", "display: " + kayit.edgeDurum.style.display);
    kontrol('yedek BASLIK aramasi calisti ("' + hedef + '")', kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);
    kontrol("yedek sonuclar gercekten sorguyla eslesiyor",
      kartlar(kayit).length > 0 && kartlar(kayit).every((c) => c.textContent.toLocaleLowerCase("tr").indexOf(hedef.toLocaleLowerCase("tr")) !== -1));
    kontrol("hata konsola yazildi (sessiz yutulmadi)", hatalar.length > 0, "hatalar: " + hatalar.length);

    // Sonuc vermeyecek sorgu -> "bulunamadi" (bos ekran degil)
    kayit.search.value = "yokboylebirsey12345";
    kayit.search.tetikle("input");
    await bekle(400);
    kontrol("bos sonucta 'bulunamadi' gosteriliyor", kayit.emptyState.style.display === "block", "display: " + kayit.emptyState.style.display);
  }

  // ── ozet.json'un kendisi inmezse ──────────────────────────────────────────
  console.log("\nTEST 7b — ozet.json bile inmiyor (en kotu hal)");
  {
    const { kayit } = sayfaKos({
      bayrak: true,
      fetchStub: () => Promise.reject(new Error("ag yok")),
    });
    await bekle(60);
    kontrol("sayfa COKMEDI", true);
    kontrol("kullaniciya mesaj gosterildi", /bağlantısı kurulamadı/i.test(kayit.edgeDurum.innerHTML), "durum: " + kayit.edgeDurum.innerHTML);
    kontrol("kategori menusu yine cizildi (sayfa kullanilabilir)", kayit.cats.children.length > 0);
  }

  console.log("\n" + "─".repeat(60));
  console.log("gecti: %d | KALDI: %d", gecti, kaldi);
  if (kaldi) { console.log("\nSONUC: BAYRAK/VITRIN/BOZULMA TESTI ❌"); process.exit(1); }
  console.log("\nSONUC: BAYRAK + VITRIN + ZARIF BOZULMA ✅ (%d kontrol)", gecti);
})();
