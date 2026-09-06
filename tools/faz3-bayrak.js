#!/usr/bin/env node
/**
 * KABUL TESTLERI 2, 6, 7 — index.html'in EDGE_KATALOG bayragi (FAZ 3).
 *
 *   python3 tools/build.py      # once (ozet.json'u uretir)
 *   node tools/faz3-bayrak.js
 *
 * Neyi kanitlar:
 *   2) BAYRAK-KAPALI REGRESYON: EDGE_KATALOG=false iken sayfa BUGUNKU gibi davranir —
 *      urunler.json cekilir, /katalog ve /ara HIC cagrilmaz, ozet.json bile inmez.
 *      (Geri donus yolunun calistiginin kaniti. Bu testin degeri: bayrak kapaliyken
 *      kazara ag istegi eklemek GOZLE fark edilmez, sadece "site biraz yavasladi" olur.)
 *      + KART SADELIGI: kartta "Sepete Ekle" butonu YOK (Okan 16 Tem kararinin kilidi —
 *      eski FAZ 3 dali bu butonu geri getiriyordu, cakismasiz sekilde).
 *   6) PARAMETRIK VITRIN: bayrak acikken ana sayfada 4 parametrik kart, sari rozetli, en ustte.
 *   7) ZARIF BOZULMA: Worker 500/ulasilamaz iken sayfa COKMEZ; kullaniciya mesaj cikar ve
 *      arama kutusu ozet.json icinde EN AZINDAN baslik aramasiyla calismaya devam eder.
 * Ayrica: ilk boyamada /katalog cagrilmaz (ozet.json yeter) ve arama ~250 ms debounce'lu.
 *
 * NEDEN ELDE YAZILMIS MINI-DOM: bu repoda npm bagimliligi YOK (parite testleri de saf
 * Node) ve is paketi yeni kutuphane yasakliyor. jsdom eklemek yerine index.html'in KENDI
 * script'i cikartilip, sadece bu sayfanin dokundugu DOM yuzeyi taklit edilerek kosuluyor.
 * Referans = gercek dosyalar: index.html + secenekler.js degisince test onlari okur,
 * kopyayi degil. Gereken element id'leri de index.html'den REGEX ile cikarilir → sayfaya
 * yeni bir id eklenince test kendiliginden ogrenir (bayat id listesi tuzagi yok).
 *
 * OZET COZUCUSU DE KOPYA DEGIL ([[ikiz-tanim-sessiz-ayrisma]]): testin fetch taslaklarini
 * beslemek icin ozet.json'u ACAN fonksiyon, index.html'in KENDI `ozetAc`'idir ve
 * tools/ozet-ac-ayikla.js ile CANLI dosyadan ayiklanir. Onceden burada elle kopyalanmis
 * bir `ozetAc` duruyordu; temsil v3'e (`yeniRef` + `gorselOnek`) gecince kopya sessizce
 * ayristi, `ozetVeri.yeni` BOSALDI ve test TEST 7'ye varmadan TypeError ile coktu.
 * Ayiklama basarisiz olursa test FAIL-CLOSED durur (rc=2, OLCULEMEDI) — eski koda
 * sessizce dusmez. Kosum oncesi kapi da `yeni` havuzunun DOLU oldugunu dogrular, boylece
 * sema kaymasi TypeError yerine acik mesajla yakalanir.
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
    this.dataset = {}; this.value = ""; this.hidden = false;
  }
  get classList() {
    const self = this;
    const liste = () => (self.className || "").split(/\s+/).filter(Boolean);
    return {
      add(c) { const l = liste(); if (l.indexOf(c) === -1) l.push(c); self.className = l.join(" "); },
      remove(c) { self.className = liste().filter((x) => x !== c).join(" "); },
      contains(c) { return liste().indexOf(c) !== -1; },
      toggle(c, zorla) {
        const var_ = liste().indexOf(c) !== -1;
        const hedef = zorla === undefined ? !var_ : !!zorla;
        if (hedef) this.add(c); else this.remove(c);
        return hedef;
      },
    };
  }
  appendChild(c) { this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter((x) => x !== c); return c; }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  getAttribute(k) { return this._attrs[k] === undefined ? null : this._attrs[k]; }
  removeAttribute(k) { delete this._attrs[k]; }
  addEventListener(t, f) { (this._dinleyici[t] = this._dinleyici[t] || []).push(f); }
  focus() {}
  select() {}
  tetikle(tur) {
    (this._dinleyici[tur] || []).forEach((f) => f.call(this, { type: tur, preventDefault() {} }));
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

/** index.html'de gecen TUM getElementById id'leri — liste bayatlamasin diye dosyadan. */
function gerekliIdler(html) {
  return [...new Set([...html.matchAll(/getElementById\("([^"]+)"\)/g)].map((m) => m[1]))];
}

function domYap(idler) {
  const kayit = {};
  idler.forEach((id) => { kayit[id] = new Oge("div"); kayit[id].id = id; });
  if (kayit.search) kayit.search.value = "";
  const body = new Oge("body");
  // K184 ONARIMI — SAHTE DOM'UN BORCU, URETIMIN DEGIL.
  // index.html belge duzeyinde `document.addEventListener("keydown", ...)` baglar
  // (talep sihirbazinin Esc kolu). Bu MESRU uretim kodudur: gercek tarayicida calisir.
  // Sahte DOM o API'yi sunmadigi icin yukleme `TypeError: document.addEventListener is
  // not a function` ile patliyordu ve `deploy` SKIPPED kaliyordu. Cozum kodu fiksture
  // uydurmak DEGIL, fiksturu gercek ortamin alt kumesi olacak sekilde tamamlamak —
  // K194'te ayni sinif ayni careyle kapandi ([[kabul-fiksturu-yasagi-kutsar]]).
  // Dinleyiciler `Oge` ile AYNI bicimde KAYDEDILIR (yutulmaz) ve `belgeTetikle` ile
  // ateslenebilir; hicbir mevcut davranis degismez.
  const belgeDinleyici = {};
  const document = {
    body,
    cookie: "",
    addEventListener(t, f) {
      (belgeDinleyici[t] = belgeDinleyici[t] || []).push(f);
    },
    removeEventListener(t, f) {
      belgeDinleyici[t] = (belgeDinleyici[t] || []).filter((x) => x !== f);
    },
    belgeTetikle(tur, olay) {
      (belgeDinleyici[tur] || []).forEach(
        (f) => f.call(document, Object.assign({ type: tur, preventDefault() {} }, olay || {})));
      return (belgeDinleyici[tur] || []).length;
    },
    getElementById: (id) => (kayit[id] === undefined ? null : kayit[id]),
    createElement: (t) => new Oge(t),
    execCommand: () => true,
    querySelector: (sel) => {
      // index.html'de iki kullanim var; ikisi de yalnizca ODEME akisinda (yuklemede degil).
      if (sel === ".cart-panel-foot") return new Oge("div");
      if (sel.indexOf('name="oYontem"') !== -1) { const o = new Oge("input"); o.value = "kart"; return o; }
      throw new Error("mini-DOM: bilinmeyen secici " + sel);
    },
  };
  return { document, kayit };
}

/** index.html'in EN BUYUK <script> blogunu cikar (kopya DEGIL — gercek dosyadan). */
function scriptCikar(html) {
  const bloklar = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  if (!bloklar.length) throw new Error("index.html'de <script> bulunamadi");
  return bloklar.sort((a, b) => b.length - a.length)[0];   // en buyuk blok = uygulama
}

/** taban-fiyatlar.js'i (build.py cikti dosyasi) okuyup haritayi al. */
function tabanHaritasi() {
  const yol = path.join(KOK, "taban-fiyatlar.js");
  if (!fs.existsSync(yol)) {
    throw new Error("taban-fiyatlar.js YOK — once `python3 tools/build.py` calistir " +
      "(sari kart taban-fiyat kolu test edilemez).");
  }
  const w = {};
  new Function("window", fs.readFileSync(yol, "utf8"))(w);
  if (!w.PRUVO_TABAN_FIYATLAR) throw new Error("taban-fiyatlar.js PRUVO_TABAN_FIYATLAR vermedi");
  return w.PRUVO_TABAN_FIYATLAR;
}

/** secenekler.js'i (gercek dosya) kosup PRUVO_SECENEK'i al. */
function secenekYukle(localStorage) {
  const src = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");
  const w = {};
  new Function("window", "localStorage", src)(w, localStorage);
  if (!w.PRUVO_SECENEK) throw new Error("secenekler.js PRUVO_SECENEK vermedi (tek kaynak bozulmus)");
  return w.PRUVO_SECENEK;
}

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Sayfayi kosar. bayrak=true ise index.html'deki EDGE_KATALOG satiri true'ya cevrilir
 * (kaynaktaki GERCEK bayrak; ayri bir kopya degil).
 */
function sayfaKos({ bayrak, fetchStub, arama }) {
  const html = fs.readFileSync(INDEX, "utf8");
  let kod = scriptCikar(html);
  const once = kod;
  kod = kod.replace(/var EDGE_KATALOG = (?:true|false);/,
    "var EDGE_KATALOG = " + (bayrak ? "true" : "false") + ";");
  if (kod === once && kod.indexOf("var EDGE_KATALOG = " + (bayrak ? "true" : "false") + ";") === -1) {
    throw new Error("EDGE_KATALOG bayrak satiri bulunamadi — index.html degismis olabilir");
  }
  /**
   * KANONIK ARAMA YUKLEMINI DISA VER — testin IDDIASI ikinci bir govdeden DOGMASIN.
   *
   * 🔴 NEDEN (olculdu 12 Agu 2026): TEST 7'nin "yedek sonuclar sorguyla eslesiyor"
   * iddiasi 20 Tem'den kalma ELLE yazilmis bir substring kuraliydi (kartin gorunen
   * metninde sorgu sozcugunu arardi). index.html 5 Agu'da (a522cb14 / 8913db28) marka
   * sorgusunu UYELIK ∪ BASLIKTA TAM KELIME yuklemine baglayinca (`markaSorgusuEsler`)
   * iddia BAYAT AYNA'ya dondu: `marka:["Citroën"]` tasiyip basliginda marka gecmeyen
   * kart sitenin KANONIK kuralina gore DOGRU sonuctu, testin substring kuralina gore
   * "eslesmiyor"du. Yayin bu yuzden durdu. [[ikiz-tanim-sessiz-ayrisma]]
   *
   * COZUM: kabul araligi ile kiyas araligi AYNI kanonik fonksiyondan gelir — ihrac,
   * test edilen sayfanin TA KENDI ornegindendir (ayri bir vm/ayri bir cip-indeks hali
   * DEGIL), boylece iki taraf ayni calisma zamani durumunu paylasir.
   * Capa tutmazsa FAIL-CLOSED durur: yuklemsiz, sessiz-yesil kosum YOK.
   */
  const KAPANIS = /\n\}\)\(\);\s*$/;
  if (!KAPANIS.test(kod)) {
    throw new Error("index.html ana script IIFE kapanisi bulunamadi — kanonik arama "
      + "yuklemi disa verilemedi (yapi degisti mi?)");
  }
  kod = kod.replace(KAPANIS,
    "\n  window.__PRUVO_ARAMA = { PAGE_SIZE: PAGE_SIZE, norm: norm, markaKatla: markaKatla,"
    + " markaUyeMi: markaUyeMi, baslikMarkalari: baslikMarkalari,"
    + " aramaPlani: aramaPlani, aramaPlaniEsler: aramaPlaniEsler,"
    + " edgeHavuz: edgeHavuz, edgeTekille: edgeTekille };\n})();\n");
  const { document, kayit } = domYap(gerekliIdler(html));
  const ag = [];                       // cagrilan TUM url'ler
  const depo = {};
  const localStorage = {
    getItem: (k) => (depo[k] === undefined ? null : depo[k]),
    setItem: (k, v) => { depo[k] = String(v); },
    removeItem: (k) => { delete depo[k]; },
  };
  const location = { hash: "", search: arama || "", pathname: "/", href: "", replace() {} };
  const history = { replaceState() {} };
  const window = { scrollY: 0, scrollTo() {}, addEventListener() {} };
  // Sari seri "X TL'den baslayan" haritasi: canli sayfada /taban-fiyatlar.js ayri bir
  // <script> olarak window'a yaziyor. Harita YUKLENMEZSE kartCiz'in taban kolu HIC
  // kosmaz ve o kol testte KOR NOKTA olur (denetci bulgusu, 20 Tem) -> gercek dosyadan yukle.
  window.PRUVO_TABAN_FIYATLAR = tabanHaritasi();
  const fetch = (url, opt) => { ag.push(String(url)); return fetchStub(String(url), opt); };

  const hatalar = [];
  const konsol = {
    log: () => {}, warn: () => {},
    error: (...a) => hatalar.push(a.map(String).join(" ")),
  };
  const PRUVO_SECENEK = secenekYukle(localStorage);

  const calistir = new Function(
    "window", "document", "location", "history", "localStorage",
    "fetch", "console", "PRUVO_SECENEK", "alert", kod);
  calistir(window, document, location, history, localStorage,
    fetch, konsol, PRUVO_SECENEK, () => {});
  const api = window.__PRUVO_ARAMA;
  if (!api || typeof api.aramaPlaniEsler !== "function") {
    throw new Error("kanonik arama yuklemi disa verilemedi (window.__PRUVO_ARAMA yok) — "
      + "iddia ELLE yazilmis ikinci govdeye dusemez, kosum durur");
  }
  return { ag, kayit, hatalar, api };
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
const ozetHam = JSON.parse(fs.readFileSync(OZET, "utf8"));

/**
 * CANLI istemci cozucusu — index.html'in kendi `ozetAc`'i (kopya TUTULMAZ).
 * FAIL-CLOSED: ayiklanamazsa rc=2 (OLCULEMEDI) ile durur; eski/elle yazilmis cozucuye
 * SESSIZCE dusmek yasak — o hal, degismis temsili hic olcmeden yesil verirdi.
 */
let ozetAc;
try {
  ozetAc = require(path.join(KOK, "tools", "ozet-ac-ayikla.js")).ozetAcAl(INDEX);
} catch (e) {
  console.log("OLCULEMEDI: index.html ozetAc ayiklanamadi: " + (e && e.message ? e.message : String(e)));
  process.exit(2);
}
const ozetVeri = ozetAc(JSON.parse(JSON.stringify(ozetHam)));

/**
 * 🔴 KOSUM ONCESI KAPI (12 Agu 2026): asagidaki testler `ozetVeri.yeni` havuzunu
 * DOGRUDAN indeksliyor (ornegin TEST 7'de `ozetVeri.yeni[0].baslik`). Havuz sema
 * kaymasi yuzunden bosalirsa test TypeError ile coker ve GERIYE KALAN testler HIC
 * kosmaz — kapsama kaybi "kirmizi" gibi gorunur ama nedeni gorunmez. Bu kapi o hali
 * acik mesajla, testler baslamadan durdurur.
 */
if (!Array.isArray(ozetVeri.yeni) || ozetVeri.yeni.length === 0) {
  console.log("OLCULEMEDI: ozet.json 'yeni' havuzu BOS — sema kaymis olabilir "
    + "(yeni/yeniRef), test kosamaz. (surum=" + JSON.stringify(ozetHam.surum)
    + ", ham anahtarlar: " + Object.keys(ozetHam).join(",") + ")");
  process.exit(2);
}
if (ozetVeri.yeniCozulemeyen !== 0) {
  console.log("OLCULEMEDI: ozet.json 'yeniRef' referanslarinin "
    + ozetVeri.yeniCozulemeyen + " tanesi COZULEMEDI — kart havuzu eksik, test kosamaz.");
  process.exit(2);
}
const ozetYaniti = () => yanit(JSON.parse(JSON.stringify(ozetHam)));

let gecti = 0, kaldi = 0, atlandi = 0;
function kontrol(ad, sart, detay) {
  if (sart) { gecti++; console.log("  ✅ " + ad); }
  else { kaldi++; console.log("  ❌ " + ad + (detay ? "\n       " + detay : "")); }
}
/**
 * OLCULEMEDI kolu (mimar hukmu, 6 Eyl): olculecek VERI yoksa eksen KIRMIZI degil
 * ATLANMIS'tir. Sessiz fail-open DEGILDIR, cunku:
 *   (a) AYRI jetonla (`⚪ ATLANDI`) basilir — yesil sayilmaz,
 *   (b) `atlandi` sayaci ozet satirinda gorunur,
 *   (c) atlanan eksenin korumasi BASKA bir iddiayla ayakta tutulur; o iddia da
 *       kosamiyorsa hal KIRMIZI kalir (bkz. "UYELIK EKSENI ANKRAJI").
 * Iddia SILINMEZ: atlamak ≠ silmek.
 */
function atla(ad, sebep) {
  atlandi++;
  console.log("  ⚪ ATLANDI (OLCULEMEDI) — " + ad + (sebep ? "\n       " + sebep : ""));
}
const kartlar = (kayit) => kayit.grid.children;
/** Kartin urun id'si — kartCiz main.href = productUrl(p) = "/urun/<id>/". TEK GOVDE. */
const kartId = (kart) => {
  const ana = kart.bul("card-main");
  const m = ana && /^\/urun\/(.+)\/$/.exec(ana.href || "");
  return m ? m[1] : null;
};
const rozetliMi = (kart) => !!kart.bul("card-badge");
/** Kartta buton var mi? (Sepete Ekle geri gelirse burasi kirmizi yanar.) */
const kartButonu = (kart) => { for (const e of kart.hepsi()) if (e.tagName === "button") return e; return null; };
const fiyatMetni = (kart) => { const e = kart.bul("card-price"); return e ? e.textContent : null; };
/** Beklenen sari kart fiyati — secenekler.js'in kurusMetni'ni CAGIRMADAN, bagimsiz kurulur. */
const TABAN = tabanHaritasi();
function beklenenTaban(id) {
  const t = TABAN[id];
  if (t == null) return null;
  return (Math.round(t * 100) / 100).toLocaleString("tr-TR",
    { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " TL'den başlayan";
}
/**
 * KAPSAMA BOSLUGU KAPATMASI (denetci bulgusu, 20 Tem): kartCiz artik IKI MODUN ortak
 * cizicisi; sari seri "X TL'den baslayan" kolu bilerek kirildiginda test YESIL kaliyordu.
 * Burasi o kolu id bazinda dogrular: taban haritasinda olan HER parametrik kart, taban
 * fiyatindan TURETILMIS metni gostermeli (fallback "Ölçüye özel fiyat" ile karistirilamaz).
 */
function tabanKontrolu(etiket, kartlarListesi) {
  let bakilan = 0;
  const sapan = [];
  kartlarListesi.forEach((kart) => {
    // Kartin id'si linkinden okunur: kartCiz main.href = productUrl(p) = "/urun/<id>/"
    const id = kartId(kart);
    const bek = id ? beklenenTaban(id) : null;
    if (bek === null) return;          // taban fiyati olmayan sari urun — bu kontrolun disinda
    bakilan++;
    const goruntu = fiyatMetni(kart);
    if (goruntu !== bek) sapan.push(id + ": bekl=" + JSON.stringify(bek) + " goruldu=" + JSON.stringify(goruntu));
  });
  kontrol(etiket + " — taban-fiyat kolu kosuyor (" + bakilan + " kart)", bakilan > 0,
    "HIC kart bakilmadi -> kontrol BOS kosuyor, kapsama yok");
  kontrol(etiket + " — her sari kart PRUVO_TABAN_FIYATLAR'dan turetilmis fiyat gosteriyor",
    bakilan > 0 && sapan.length === 0, sapan.slice(0, 5).join(" | "));
}

/**
 * YEDEK YOLUN ESLESME KONTROLU — iddia sitenin KANONIK eslestiricisinden turer.
 *
 * Ne olcer (uc eksen, ucu de ayni kanonik yuklemi kullanir):
 *   1. SAGLAMLIK+TAMLIK: cizilen kart kumesi, havuzun kanonik yuklemle suzulmus
 *      halinin ilk PAGE_SIZE'i ile BIREBIR ayni mi (edgeYedek: liste.slice(0, PAGE_SIZE),
 *      renderGrid edge-filtreli dalda edgeListe'nin TAMAMINI cizer).
 *   2. AYIRT EDICILIK: sorgu havuzu GERCEKTEN daraltiyor mu (0 < beklenen < havuz)?
 *      🔴 TOTOLOJI KIRICI: yuklem "hep true"ya (ya da "hep false"a) bozulursa 1. eksen
 *      iki tarafi birden kaydirdigi icin YESIL kalirdi; bu eksen o mutanti KIRMIZI yakar.
 *   3. UYELIK ALT SINIRI (yalniz marka sorgusunda): `marka[]` alaninda o markayi TASIYAN
 *      her havuz urunu sonucta OLMALI. Bu bir URUN KURALIDIR (5 Agu, a522cb14: "marka
 *      adiyla arama UYELIGI de bulur"), eslestirme algoritmasinin kopyasi DEGIL — girdisi
 *      urun VERISI (`marka[]`) ve kanonik katlama. `markaSorgusuEsler`in uyelik kolu
 *      dusurulurse (yani 5 Agu oncesine donulurse) bu eksen KIRMIZI yanar.
 */
/*
 * `uyelikZorunlu`: 3. eksen (marka[] uyeligi) icin kapsam beklentisi. YALNIZ secici
 * (`havuzunUyelikKolunuEnCokGerektirenMarkasi`) ile kurulan OZEL marka senaryosunda
 * `true` — secici uye>0'i YAPISAL olarak garanti eder, o zaman "uye yok" gercek bir
 * kapsam kaybidir ve KIRMIZIDIR. Baslik-kelimesi senaryosunda (`hedef`) kelimenin
 * markaya denk gelmesi VE havuzda uyesi bulunmasi o gunun ilk kartina baglidir
 * (olculdu 15 Agu: "Vespa" — havuzda marka uyesi 0, baslik eslesmesi 1; site dogru,
 * eksen BOS) — orada bos eksen RAPORLANIR, KALDIRILMAZ.
 */
function yedekEslesmeKontrolu(etiket, kayit, api, sorgu, uyelikZorunlu) {
  const plan = api.aramaPlani(sorgu);
  // Yedek yol serbest metinde YALNIZ BASLIGA bakar (ozet kartinda aciklama yok) —
  // index.html::edgeYedek ile AYNI hsAl.
  const baslikHs = (u) => api.norm(u.baslik || "");
  const havuz = api.edgeTekille(api.edgeHavuz());
  const beklenen = havuz.filter((p) => api.aramaPlaniEsler(p, plan, baslikHs));
  const beklenenIlk = beklenen.slice(0, api.PAGE_SIZE).map((p) => p.id);
  const cizilen = kartlar(kayit).map(kartId);

  kontrol(etiket + " — cizilen kartlar KANONIK eslestiricinin verdigi kume (" +
    cizilen.length + " kart / " + beklenen.length + " eslesme / " + havuz.length + " havuz)",
    cizilen.length === beklenenIlk.length &&
    cizilen.every((id, i) => id === beklenenIlk[i]),
    "cizilen=" + JSON.stringify(cizilen.slice(0, 5)) +
    " beklenen=" + JSON.stringify(beklenenIlk.slice(0, 5)));

  kontrol(etiket + " — sorgu havuzu GERCEKTEN daraltiyor (yuklem ayirt edici)",
    beklenen.length > 0 && beklenen.length < havuz.length,
    "beklenen=" + beklenen.length + " havuz=" + havuz.length +
    " (0 ya da havuzun tamami -> yuklem korelmis)");

  if (plan.kanon) {
    const uye = havuz.filter((p) => api.markaUyeMi(p, plan.kanon));
    const kacan = uye.filter((p) => beklenen.indexOf(p) === -1).map((p) => p.id);
    if (uye.length === 0 && !uyelikZorunlu) {
      // Baslik-kelimesi senaryosu: marka sorgusuna denk gelmesi tesaduf, havuzda
      // uye yoksa eksen OLCULEMEZ — kirmizi yakmak yerine raporla (bos eksen).
      // 6 Eyl: artik SAYILIYOR da (`atla`), boylece ozet satirinda gorunur.
      atla(etiket + " — uyelik ekseni BOS", "havuzda `marka[]`de " + plan.kanon +
        " tasiyan urun yok; baslik-kelimesi senaryosu, zorunlu degil");
    } else {
      kontrol(etiket + " — uyelik kolu KOSUYOR (`marka[]`de " + plan.kanon +
        " tasiyan " + uye.length + " havuz urunu var)", uye.length > 0,
        "HIC uye urun yok -> 3. eksen BOS kosar, kapsama yok");
      kontrol(etiket + " — `marka[]` uyeligi olan HER urun sonucta (" + plan.kanon + ")",
        uye.length > 0 && kacan.length === 0, "kacan=" + JSON.stringify(kacan.slice(0, 5)));
    }
  }
  return { beklenen: beklenen, havuz: havuz };
}

/**
 * Havuzda basliginda marka gecmeyen EN COK uyeye sahip kanonik marka.
 * Iki ilkel de test edilen sayfanin KANONIK yukleminden gelir: `markaUyeMi` ve
 * `baslikMarkalari`. Boylece senaryo sabit ada/veri tesadufuna dayanmaz; uyelik kolu
 * dusurulurse kaybolmasi gereken en az bir gercek urunu YAPISAL olarak garanti eder.
 */
function havuzunUyelikKolunuEnCokGerektirenMarkasi(api, havuz) {
  const say = {};
  havuz.forEach((p) => (p.marka || []).forEach((b) => {
    const k = api.markaKatla(b);
    // Sorgu olarak AYNI kanona donmeli ve bu urun BASLIK kolundan bulunamiyor olmali.
    if (k && api.aramaPlani(k).kanon === k && api.markaUyeMi(p, k) &&
        api.baslikMarkalari(p).indexOf(k) === -1) {
      say[k] = (say[k] || 0) + 1;
    }
  }));
  const sirali = Object.keys(say).sort((a, b) => (say[b] - say[a]) || (a < b ? -1 : 1));
  return sirali.length ? sirali[0] : null;
}

(async () => {
  // ── TEST 2: bayrak KAPALI = bugunku davranis ──────────────────────────────
  console.log("\nTEST 2 — bayrak KAPALI regresyon (EDGE_KATALOG=false)");
  {
    const { ag, kayit, hatalar } = sayfaKos({
      bayrak: false,
      fetchStub: (url) => (url.indexOf("urunler.json") !== -1 ? yanit(PRODUCTS) : yanit({ hata: "beklenmedik: " + url }, false)),
    });
    await bekle(80);
    kontrol("urunler.json cekildi (bugunku yol)", ag.some((u) => u.indexOf("urunler.json") !== -1), "cagrilanlar: " + JSON.stringify(ag));
    kontrol("/katalog HIC cagrilmadi", !ag.some((u) => u.indexOf("/katalog") !== -1), "cagrilanlar: " + JSON.stringify(ag));
    kontrol("/ara HIC cagrilmadi", !ag.some((u) => u.indexOf("/ara") !== -1), "cagrilanlar: " + JSON.stringify(ag));
    kontrol("ozet.json cekilmedi (bayrak kapali)", !ag.some((u) => u.indexOf("ozet.json") !== -1));
    kontrol("baska hicbir ag istegi yok (toplam 1)", ag.length === 1, "toplam " + ag.length + ": " + JSON.stringify(ag));
    kontrol("kartlar cizildi", kartlar(kayit).length > 0, "kart sayisi: " + kartlar(kayit).length);
    kontrol("durum satiri GIZLI kaldi (bayrak kapali)", kayit.edgeDurum.style.display === "none" || kayit.edgeDurum.style.display === undefined,
      "display: " + kayit.edgeDurum.style.display);
    kontrol("konsol hatasi yok", hatalar.length === 0, hatalar.join(" | "));

    // KART SADELIGI (Okan 16 Tem): kartta buton YOK — sepete ekleme yalniz urun sayfasindan.
    const butonluKart = kartlar(kayit).find((c) => kartButonu(c));
    kontrol('kartta "Sepete Ekle" butonu YOK (kart sade)', !butonluKart,
      butonluKart ? "buton metni: " + kartButonu(butonluKart).textContent : "");

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
    await bekle(350);   // syncUrl debounce'u da gecsin — yine ag istegi olmamali
    kontrol("arama sirasinda da ag istegi yok", ag.length === 1, JSON.stringify(ag));
  }

  // ── TEST 2b: sari seri taban-fiyat kolu, bayrak KAPALI (YEREL urun objesi) ─
  // ?kategori=Jeneratör -> deterministik: TUM parametrik urunler cizilir (rastgele vitrin degil).
  console.log("\nTEST 2b — bayrak KAPALI: sari kart \"X TL'den başlayan\" (yerel urun objesi)");
  {
    const { ag, kayit, hatalar } = sayfaKos({
      bayrak: false,
      arama: "?kategori=Jeneratör",
      fetchStub: (url) => (url.indexOf("urunler.json") !== -1 ? yanit(PRODUCTS) : yanit({ hata: "beklenmedik: " + url }, false)),
    });
    await bekle(80);
    kontrol("Jeneratör kategorisi cizildi", kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);
    kontrol("konsol hatasi yok", hatalar.length === 0, hatalar.join(" | "));
    kontrol("hala tek ag istegi (urunler.json)", ag.length === 1, JSON.stringify(ag));
    tabanKontrolu("bayrak KAPALI", kartlar(kayit));
  }

  // ── TEST 6c: AYNI kol, bayrak ACIK (EDGE karti) ───────────────────────────
  // Asil risk burasi: kartCiz artik edge kartini da ciziyor ve edge kartinda `fiyat` BOS
  // string geliyor -> taban kolu calismazsa sari kart "Ölçüye özel fiyat"a sessizce duser.
  console.log("\nTEST 6c — bayrak ACIK: AYNI taban-fiyat kolu EDGE kartinda da kosuyor");
  {
    const { kayit, hatalar } = sayfaKos({
      bayrak: true,
      arama: "?kategori=Jeneratör",
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return ozetYaniti();
        if (url.indexOf("/katalog") !== -1) {
          return yanit({ toplam: ozetVeri.parametrik.length, sayfa: 1, sayfaBoyu: 24,
            sonSayfa: 1, urunler: ozetVeri.parametrik });
        }
        return yanit({ hata: "beklenmedik: " + url }, false);
      },
    });
    await bekle(80);
    kontrol("edge /katalog?kategori=Jeneratör cizildi", kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);
    kontrol("konsol hatasi yok", hatalar.length === 0, hatalar.join(" | "));
    kontrol("edge kartinda fiyat alani BOS geliyor (kolun sartini kanitlar)",
      ozetVeri.parametrik.every((p) => !p.fiyat || p.fiyat.trim() === ""),
      "bos olmayan: " + ozetVeri.parametrik.filter((p) => p.fiyat && p.fiyat.trim()).length);
    tabanKontrolu("bayrak ACIK (edge kart)", kartlar(kayit));
  }

  // ── TEST 6 + ilk boyama: bayrak ACIK, saglikli ────────────────────────────
  console.log("\nTEST 6 — bayrak ACIK: ilk boyama ozet.json ile + parametrik vitrin");
  {
    const { ag, kayit, hatalar } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return ozetYaniti();
        if (url.indexOf("/katalog") !== -1) return yanit({ toplam: ozetVeri.toplam, sayfa: 2, sayfaBoyu: 24, sonSayfa: 300, urunler: ozetVeri.yeni.slice(24, 48) });
        return yanit({ hata: "beklenmedik: " + url }, false);
      },
    });
    await bekle(80);
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
    kontrol("toplam urun sayisi ozet.json'dan (" + ozetVeri.toplam + ")",
      kayit.resultCount.textContent === ozetVeri.toplam + " ürün", kayit.resultCount.textContent);
    kontrol("vitrin + ilk sayfa kart cizildi", k.length > 4, "kart sayisi: " + k.length);
    kontrol("edge kartinda da buton YOK (kart sade)", !k.find((c) => kartButonu(c)));

    // İlk "Daha fazla" özet havuzundaki hazır 48 karta kadar yerel genişler; ağ gerekmez.
    const dahaFazla = kayit.loadMoreWrap.children[0];
    kontrol('"Daha fazla goster" butonu var', !!dahaFazla);
    if (dahaFazla) {
      dahaFazla.tetikle("click");
      await bekle(40);
      kontrol("ilk 'Daha fazla' ozet havuzunda YEREL genisledi (/katalog yok)",
        !ag.some((u) => u.indexOf("/katalog") !== -1),
        JSON.stringify(ag.filter((u) => u.indexOf("/katalog") !== -1)));
    }
  }

  // ── Arama: debounce + /ara (site modu) ────────────────────────────────────
  console.log("\nTEST 4b — bayrak ACIK: arama /ara?q= ucuna ~250 ms debounce ile bagli");
  {
    const { ag, kayit } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return ozetYaniti();
        if (url.indexOf("/ara") !== -1) return yanit({ toplam: 3, urunler: ozetVeri.yeni.slice(0, 3) });
        return yanit({ hata: "beklenmedik" }, false);
      },
    });
    await bekle(40);
    // Hizli yazma: 5 tus
    for (const s of ["a", "au", "aud", "audi", "audi "]) {
      kayit.search.value = s;
      kayit.search.tetikle("input");
      await bekle(30);
    }
    const oncesi = ag.filter((u) => u.indexOf("/ara") !== -1).length;
    kontrol("hizli yazarken istek ATILMADI (debounce tutuyor)", oncesi === 0, "istek sayisi: " + oncesi);
    await bekle(400);
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
    const { kayit, hatalar, api } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return ozetYaniti();
        return Promise.reject(new Error("baglanti yok"));   // Worker ULASILAMAZ
      },
    });
    await bekle(40);
    kontrol("ana sayfa yine cizildi (ozet.json yetti, Worker'a hic gitmedi)", kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);

    // Worker cokmusken arama yap -> yedek yol
    const hedef = ozetVeri.yeni[0].baslik.split(/\s+/)[0];
    kayit.search.value = hedef;
    kayit.search.tetikle("input");
    await bekle(450);

    kontrol("sayfa COKMEDI (istisna disari sizmadi)", true);
    kontrol("kullaniciya mesaj gosterildi", /bağlantısı kurulamadı/i.test(kayit.edgeDurum.innerHTML), "durum: " + kayit.edgeDurum.innerHTML);
    kontrol("durum satiri gorunur", kayit.edgeDurum.style.display === "flex", "display: " + kayit.edgeDurum.style.display);
    kontrol('yedek BASLIK aramasi calisti ("' + hedef + '")', kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);
    yedekEslesmeKontrolu('yedek sonuc ("' + hedef + '")', kayit, api, hedef, false);
    kontrol("hata konsola yazildi (sessiz yutulmadi)", hatalar.length > 0, "hatalar: " + hatalar.length);

    // 🔴 MARKA SORGUSU SENARYOSU (12 Agu): yukaridaki `hedef` bir BASLIK kelimesidir ve
    // marka sorgusu olup olmadigi katalogun o gunku ilk kartina baglidir — uyelik ekseni
    // orada BOS kosabilir. Bu senaryo marka sorgusunu VERIDEN turetip o ekseni HER
    // kosumda calistirir (sabit marka adi YAZILMAZ; katalog degisince kendiliginde kayar).
    const edgeHavuzu = api.edgeTekille(api.edgeHavuz());
    const markaSorgusu = havuzunUyelikKolunuEnCokGerektirenMarkasi(api, edgeHavuzu);
    if (markaSorgusu === null) {
      // 🔴 MIMAR HUKMU (6 Eyl): edge havuzu `ozet.json`in ILK N urunudur; yeni bir parti
      // havuzun basini "markasi BASLIGINDA da gecen" urunlerle doldurdugunda AYIRT EDICI
      // uye kalmaz ve bu senaryo VERIDEN kurulamaz. Olculecek veri yoksa eksen
      // OLCULEMEDI'dir, KIRMIZI degil. OLCULDU (6 Eyl, havuz 231): uye=154,
      // kanon-esit=113, AYIRT-EDICI=0 (Yamaha 13 / Audi 40 / Mercedes 5 / Toyota 45 /
      // Mazda 10 — hepsinin markasi kendi basliginda geciyor).
      // Atlama korumayi DELMEZ: asagidaki "UYELIK EKSENI ANKRAJI" ayni TEK GOVDEyi
      // (`markaSorgusuEsler`) ayirt edici verinin GERCEKTEN bulundugu TAM KATALOG'da
      // olcer ve kosamazsa KIRMIZI yanar.
      atla("marka sorgusu senaryosu VERIDEN kurulabildi (edge havuzu)",
        "havuzda `marka[]` uyesi olup markasi BASLIGINDA gecmeyen urun yok (havuz " +
        edgeHavuzu.length + ") -> edge kolunda uyelik ekseni ayirt edilemiyor");
    }
    if (markaSorgusu) {
      kontrol("marka sorgusu senaryosu VERIDEN kurulabildi (edge havuzu, \"" +
        markaSorgusu + "\")", true);
      kayit.search.value = markaSorgusu;
      kayit.search.tetikle("input");
      await bekle(450);
      kontrol('yedek marka aramasi kart cizdi ("' + markaSorgusu + '")',
        kartlar(kayit).length > 0, "kart: " + kartlar(kayit).length);
      yedekEslesmeKontrolu('yedek marka sorgusu ("' + markaSorgusu + '")',
        kayit, api, markaSorgusu, true);
    }

    // ── UYELIK EKSENI ANKRAJI — atlamanin korumayi DELMEDIGINI olcer ─────────
    // NEDEN VAR (olculdu 6 Eyl, izole kopyada): edge havuzunda AYIRT EDICI uye 0 iken
    // gercek uyelik regresyonu (`markaSorgusuEsler`ten `markaUyeMi` dusurulur) yukaridaki
    // DOM kollarindan HICBIRINI kirmizi yakmiyordu (mutantli 53/1 = mutantsiz 53/1) —
    // yani "uye.length > 0" YESILI kapsam DEGIL, tesadüftu. Ankraj ayni TEK GOVDEyi
    // (`aramaPlaniEsler` -> `markaSorgusuEsler`) UYELIK GERCEGINE (`markaUyeMi`) karsi,
    // ayirt edici verinin bulundugu TAM KATALOG'da sinar. Iki AYRI fonksiyon karsilastirilir:
    // uyelik kolu dusurulurse baglanti kopar ve bu iddia KIRMIZI yanar.
    // FAIL-CLOSED: ankraj kurulamazsa (tam katalogda da ayirt edici uye yoksa, ya da
    // yardimci BOZULDUYSA) bu KIRMIZIDIR — atlama degil; cunku o zaman uyelik ekseni
    // TUM kosumda olculmemis olur ve "hic kontrol kosmadi" halidir.
    console.log("\nUYELIK EKSENI ANKRAJI — atlanan edge kolunun korumasi ayakta mi?");
    {
      const tamMarka = havuzunUyelikKolunuEnCokGerektirenMarkasi(api, PRODUCTS);
      kontrol("uyelik ekseni TAM KATALOG'da AYIRT EDICI (senaryo veriden kuruldu)",
        tamMarka !== null,
        "tam katalogda (" + PRODUCTS.length + " urun) `marka[]` uyesi olup markasi " +
        "BASLIGINDA gecmeyen urun YOK -> uyelik ekseni HIC olculemiyor, koruma dustu");
      if (tamMarka) {
        const plan = api.aramaPlani(tamMarka);
        const baslikHs = (u) => api.norm(u.baslik || "");
        // Yalniz BASLIKTAN bulunamayan uyeler: uyelik kolu dusunce kaybolmasi
        // GEREKEN kume tam olarak budur.
        const gizliUye = PRODUCTS.filter((p) => api.markaUyeMi(p, tamMarka) &&
          api.baslikMarkalari(p).indexOf(tamMarka) === -1);
        kontrol("ayirt edici uye kumesi BOS DEGIL (" + tamMarka + ": " +
          gizliUye.length + " urun)", gizliUye.length > 0,
          "kume bosalirsa asagidaki iddia bos kosar = kapsam yanilsamasi");
        const kacan = gizliUye.filter((p) => !api.aramaPlaniEsler(p, plan, baslikHs))
          .map((p) => p.id);
        kontrol("`marka[]` uyesi olup markasi BASLIGINDA GECMEYEN her urun marka " +
          "sorgusunda (" + tamMarka + ", " + gizliUye.length + " urun)",
          gizliUye.length > 0 && kacan.length === 0,
          "kacan=" + kacan.length + " " + JSON.stringify(kacan.slice(0, 5)) +
          " -> uyelik kolu dusmus, marka sorgusu yalniz BASLIGA bakiyor");
        // 🔴 TOTOLOJI KIRICI — UST SINIR (6 Eyl, OLCULDU). Yukaridaki iddia yalniz
        // ALT SINIRI olcer: "uye kaybolmasin". Yuklem "hep true"ya bozulursa HICBIR
        // uye kaybolmaz, `kacan` bos kalir ve o iddia YESIL yanar. Olculen korluk:
        // `aramaPlaniEsler`in marka kolu `return true` yapildiginda 3 mutantin biri
        // KACTI (rc=0) — kapi kor kaldi. Ayirt edicilik ekseni ZATEN vardi ama
        // `yedekEslesmeKontrolu` icindeydi ve o kol EDGE HAVUZU verisine bagli
        // (`markaSorgusu === null` ise HIC kosmuyor) — yani koruma, kosmasi
        // GARANTI OLMAYAN bir yerde duruyordu. Ust sinir bu yuzden ankrajin
        // icinde, TAM KATALOG'da olculur: burasi her kosumda calisir.
        const eslesenTam = PRODUCTS.filter(
          (p) => api.aramaPlaniEsler(p, plan, baslikHs));
        kontrol("marka sorgusu TAM KATALOG'da GERCEKTEN daraltiyor (yuklem ayirt " +
          "edici, " + tamMarka + ": 0 < " + eslesenTam.length + " < " +
          PRODUCTS.length + ")",
          eslesenTam.length > 0 && eslesenTam.length < PRODUCTS.length,
          "eslesen=" + eslesenTam.length + " katalog=" + PRODUCTS.length +
          " (0 ya da katalogun TAMAMI -> yuklem korelmis; 'hep true' bozulmasi " +
          "tam olarak boyle gorunur)");
      }
    }

    // Sonuc vermeyecek sorgu -> "bulunamadi" (bos ekran degil)
    kayit.search.value = "yokboylebirsey12345";
    kayit.search.tetikle("input");
    await bekle(450);
    kontrol("bos sonucta 'bulunamadi' gosteriliyor", kayit.emptyState.style.display === "block", "display: " + kayit.emptyState.style.display);
  }

  // ── ozet.json'un kendisi inmezse ──────────────────────────────────────────
  console.log("\nTEST 7b — ozet.json bile inmiyor (en kotu hal)");
  {
    const { kayit } = sayfaKos({
      bayrak: true,
      fetchStub: () => Promise.reject(new Error("ag yok")),
    });
    await bekle(120);
    kontrol("sayfa COKMEDI", true);
    kontrol("kullaniciya mesaj gosterildi", /bağlantısı kurulamadı/i.test(kayit.edgeDurum.innerHTML), "durum: " + kayit.edgeDurum.innerHTML);
    kontrol("kategori menusu yine cizildi (sayfa kullanilabilir)", kayit.cats.children.length > 0);
  }

  console.log("\n" + "─".repeat(60));
  console.log("gecti: %d | KALDI: %d | ATLANDI(OLCULEMEDI): %d", gecti, kaldi, atlandi);
  if (kaldi) { console.log("\nSONUC: BAYRAK/VITRIN/BOZULMA TESTI ❌"); process.exit(1); }
  // "HIC kontrol kosmadi" hali KIRMIZI kalir — atlamalar tum kosumu bosaltamaz.
  if (!gecti) {
    console.log("\nSONUC: HIC KONTROL KOSMADI (yalniz %d atlama) ❌", atlandi);
    process.exit(1);
  }
  console.log("\nSONUC: BAYRAK + VITRIN + ZARIF BOZULMA ✅ (%d kontrol, %d atlanan eksen)",
    gecti, atlandi);
})();
