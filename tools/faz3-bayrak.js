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
  const document = {
    body,
    cookie: "",
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
  if (bayrak) {
    const once = kod;
    kod = kod.replace("var EDGE_KATALOG = false;", "var EDGE_KATALOG = true;");
    if (kod === once) throw new Error("EDGE_KATALOG bayrak satiri bulunamadi — index.html degismis olabilir");
  }
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
    const ana = kart.bul("card-main");
    const m = ana && /^\/urun\/(.+)\/$/.exec(ana.href || "");
    const id = m ? m[1] : null;
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
        if (url.indexOf("ozet.json") !== -1) return yanit(ozetVeri);
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
        if (url.indexOf("ozet.json") !== -1) return yanit(ozetVeri);
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

    // "Daha fazla" -> /katalog?sayfa=2
    const dahaFazla = kayit.loadMoreWrap.children[0];
    kontrol('"Daha fazla goster" butonu var', !!dahaFazla);
    if (dahaFazla) {
      dahaFazla.tetikle("click");
      await bekle(40);
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
    const { kayit, hatalar } = sayfaKos({
      bayrak: true,
      fetchStub: (url) => {
        if (url.indexOf("ozet.json") !== -1) return yanit(ozetVeri);
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
    kontrol("yedek sonuclar gercekten sorguyla eslesiyor",
      kartlar(kayit).length > 0 && kartlar(kayit).every((c) => c.textContent.toLocaleLowerCase("tr").indexOf(hedef.toLocaleLowerCase("tr")) !== -1));
    kontrol("hata konsola yazildi (sessiz yutulmadi)", hatalar.length > 0, "hatalar: " + hatalar.length);

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
  console.log("gecti: %d | KALDI: %d", gecti, kaldi);
  if (kaldi) { console.log("\nSONUC: BAYRAK/VITRIN/BOZULMA TESTI ❌"); process.exit(1); }
  console.log("\nSONUC: BAYRAK + VITRIN + ZARIF BOZULMA ✅ (%d kontrol)", gecti);
})();
