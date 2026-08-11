#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEPETE EKLE — SESSIZ BASARISIZLIK KAPISI (11 Agu 2026).

    python3 tools/sepet-secim-kapisi.py
    python3 tools/sepet-secim-kapisi.py --mutasyon     # + kontrol mutantlari

NEDEN VAR — HATA SINIFI SESSIZ VE PARALI: 11 Agu'ya kadar kart-secim urun sayfasinda
zorunlu MALZEME secimi "Sepete Ekle" butonunun ~168 px ALTINDAYDI ve onden secili
DEGILDI. Musteri butona basiyor, secim eksik oldugu icin ekleme SESSIZCE dusuyordu:
ekranda yalniz 500 ms'lik bir titreme oluyor, hicbir hata METNI cikmiyor, `pruvo_sepet`
bos kaliyordu. Kullanici sepete ekledigini SANIYOR -> dogrudan satis kaybi. Canlida
olculdu (pruvo3d.com/urun/bmw-kaput-a-ma-kolu/ ve /urun/olcuye-ozel-cerceve/): iki
sayfada da #filCipler, #cartBtn'den SONRA geliyordu ve onden secili cip/buton YOKTU.

KAPININ IDDIASI (uc ayak, hepsi KOSULARAK olculur):
  (a) YAPISAL  — secici butondan ONCE basiliyor; #filCipler TEK; varsayilan malzeme+renk
                 onden `secili`; #secimHata kutusu sayfada var.
  (b) FIYAT    — on-secim bir ARAYUZ varsayilanidir, fiyat mantigina DOKUNMAZ: secilen
                 varsayilanlar secenekler.js bosSatir() degerlerinin TA KENDISIDIR,
                 malzeme farki %0 ve renk "Diğer" degil -> carpanlar 1,00.
  (c) DAVRANIS — uretilen sayfanin KENDI JS'i node:vm'de KOSTURULUR (kod kopyalanmaz):
                 c1 hic secim yapmadan tiklama -> sepet DOLU (kurus = liste fiyati),
                 c2 secim eksiltilince tiklama -> GORUNUR hata metni (sessiz yol YOK),
                 c3 eksik giderilince tiklama -> sepet buyuyor, hata kutusu kapaniyor.
  (d) SUNUCU   — c1'in localStorage'a YAZDIGI satir, shop worker'in sunucu fiyat kolundan
                 (SECENEK.satirOzeti, /fiyat ile AYNI fonksiyon) gecirilir; istemcinin
                 gosterdigi kurus ile SUNUCUNUN hesapladigi kurus BIREBIR esit olmali.

NE IDDIA EDILMEZ (beyan edilen kor noktalar — sessiz yesil yasak):
  * Gorsel yerlesim/piksel mesafesi. Kapi DOM SIRASINI olcer; CSS ile geri cevrilebilecek
    bir siralama (order/column-reverse) ayrica (a4) ekseninde taranir ama "kullanici
    gercekten gorüyor mu" sorusu tarayici isidir (dalda ayrica elle dogrulandi).
  * Parametrik (sari) sayfanin KONFIGURATOR fiyati: o kol sunucuda semadan hesaplanir ve
    bu degisiklikten etkilenmez; burada yalniz malzeme/renk on-secimi ve gorunur hata
    yolu olculur.

CIKIS: 0 yesil · 1 kirmizi · 2 olculemedi (node/fikstur yok). Depoya YAZMAZ.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build          # noqa: E402
import yayin_yuzey    # noqa: E402

# Fikstur urunleri — UC KOL DA olculur (tekil yama sinifi kapatmaz):
#   kart     : malzeme filament KARTLARINDAN secilir (#filCipler) — duz katalog + sari seri
#   konfigur : dekor konfiguratoru, malzeme #malzemeButonlar kartlarindan secilir
FIKSTURLER = [
    {"id": "bmw-kaput-a-ma-kolu", "ad": "duz katalog (kart-secim)", "kol": "kart",
     "malzeme_kok": "filCipler", "malzeme_sinif": "fil-cip", "kart_secim": True},
    {"id": "olcuye-ozel-cerceve", "ad": "parametrik/sari (kart-secim)", "kol": "kart",
     "malzeme_kok": "filCipler", "malzeme_sinif": "fil-cip", "kart_secim": True},
    {"id": "capa-serit-dekoratif-figur", "ad": "konfigur (dekor)", "kol": "konfigur",
     "malzeme_kok": "malzemeButonlar", "malzeme_sinif": "malzeme-btn", "kart_secim": False},
]

HATALAR = []
OLCULEMEDI = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


def olculemedi(mesaj):
    print("  ⚠️  OLCULEMEDI: " + mesaj)
    OLCULEMEDI.append(mesaj)


def _urunler():
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        return json.load(f)


def sayfalari_uret(gecici, mod=build):
    """Fikstur urunlerinin GERCEK sayfalarini gecici dizine uretir (build.py LOKALDE
    TUM katalogla KOSTURULMAZ — spec siniri). /varlik/ referanslari icerikleriyle
    yerine konur (yayin_yuzey) ki olculen metin tarayiciya inen metin olsun."""
    tum = _urunler()
    ix = {p["id"]: p for p in tum}
    mod.VARLIK_DIR = os.path.join(gecici, "varlik")
    mod._VARLIK_ONBELLEK = {}
    cikti = {}
    for fx in FIKSTURLER:
        pid = fx["id"]
        p = ix.get(pid)
        if not p:
            return None, "fikstur urunu katalogda YOK: %s" % pid
        havuz = [x for x in tum if x.get("kategori") == p.get("kategori")][:12]
        if p not in havuz:
            havuz = [p] + havuz
        ham = mod.render_product(p, havuz, None)
        yol = os.path.join(gecici, pid + ".html")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(yayin_yuzey.govde(ham, gecici))
        cikti[pid] = yol
    return cikti, None


# ------------------------------------------------------------------ (a) YAPISAL
def bolum_a(sayfalar):
    print("\n(a) YAPISAL — secici butondan ONCE, onden secili, gorunur hata kutusu var")
    urun_ix = {p["id"]: p for p in _urunler()}
    for fx in FIKSTURLER:
        pid, ad, kok, sinif = fx["id"], fx["ad"], fx["malzeme_kok"], fx["malzeme_sinif"]
        h = open(sayfalar[pid], encoding="utf-8").read()
        i_cip = h.find('id="%s"' % kok)
        i_cart = h.find('id="cartBtn"')
        i_renk = h.find('id="renkButonlar"')
        i_hata = h.find('id="secimHata"')
        kontrol(0 <= i_cip < i_cart,
                "%s: malzeme secicisi (#%s @%d) sepet butonundan (@%d) ONCE"
                % (ad, kok, i_cip, i_cart))
        kontrol(h.count('id="%s"' % kok) == 1,
                "%s: #%s TEK (ikinci kopya olsaydi tiklanan kart hicbir seye yazmazdi)"
                % (ad, kok))
        kontrol(0 <= i_renk < i_cart, "%s: renk secicisi butondan ONCE (@%d)" % (ad, i_renk))
        kontrol(i_hata >= 0, "%s: gorunur hata kutusu (#secimHata) sayfada" % ad)
        secili_m = re.findall(r'class="[^"]*\b%s\b[^"]*\bsecili\b[^"]*" data-malzeme="([^"]+)"'
                              % sinif, h)
        secili_r = re.findall(r'class="renk-btn secili" data-renk="([^"]+)"', h)
        p = urun_ix[pid]
        # 🔴 BEKLENTI SABIT DEGIL, TURETILIR (11 Agu, isletme karari): duz katalog kolunda
        # onden secili malzeme artik URUNUN ONERILEN malzemesidir. "PLA" diye civilenmis
        # bir beklenti bugun BAYAT olurdu ([[bayat-kabul-testi]]). Iddia zayiflamaz: hala
        # "sayfadaki secili cip = kuralin sectigi malzeme" denir, yalnizca kural TEK
        # KAYNAKTAN okunur.
        bek_m = ((p.get("konfigur") or {}).get("varsayilanMalzeme")
                 if fx["kol"] == "konfigur" else build.on_secim_malzeme(p))
        bek_r = (build._konfigur_varsayilan_renk(p["konfigur"])
                 if fx["kol"] == "konfigur" else build.VARSAYILAN_RENK)
        kontrol(secili_m == [bek_m],
                "%s: onden secili malzeme = %r (olculen: %r)" % (ad, bek_m, secili_m))
        kontrol(secili_r == [bek_r],
                "%s: onden secili renk = %r (olculen: %r)" % (ad, bek_r, secili_r))
        kontrol(("var URUN_KART_SECIM = true" in h) == fx["kart_secim"],
                "%s: KART_SECIM bayragi beklenen halde (%s)" % (ad, fx["kart_secim"]))
        # (a4) CSS ile siralamayi geri ceviren kural YOK (DOM sirasi gorsel siraya esit kalsin)
        stil = "\n".join(re.findall(r"<style>([\s\S]*?)</style>", h))
        # ⚠️ `order:` ararken `border:` YAKALANMAMALI (ilk yazimda yakaliyordu ve kapi
        # sahte-kirmizi yaniyordu): ozellik adi satir/`{`/`;` sonrasi BASLAMALI.
        ters = re.findall(r"\.opsiyonlar[^{}]*\{[^{}]*(?:column-reverse|[{;\s]order\s*:)", stil)
        kontrol(not ters, "%s: opsiyon panelinde DOM sirasini terse ceviren CSS YOK" % ad)
        # (a5) sessiz yol kapali: eksik secim dalinda gorunur metin cagrisi VAR
        kontrol("hataGoster(" in h,
                "%s: eksik secim dalinda gorunur hata cagrisi (hataGoster) basiliyor" % ad)


# ------------------------------------------------------------------ (b) FIYAT (yapisal)
def bolum_b():
    print("\n(b) FIYAT — on-secim ARAYUZ varsayilanidir, fiyat mantigina DOKUNMAZ")
    with open(os.path.join(ROOT, "secenekler.js"), encoding="utf-8") as f:
        sec = f.read()
    m = re.search(r"function\s+bosSatir\s*\([^)]*\)\s*\{\s*return\s*\{(.*?)\}\s*;", sec, re.S)
    kontrol(bool(m), "secenekler.js bosSatir() bulundu (tek kaynak)")
    if not m:
        return
    govde = m.group(1)
    bm = re.search(r'malzeme\s*:\s*"([^"]*)"', govde)
    br = re.search(r'renk\s*:\s*"([^"]*)"', govde)
    kontrol(bool(bm) and bm.group(1) == build.VARSAYILAN_MALZEME,
            "onden secili malzeme == bosSatir().malzeme (%r)" % build.VARSAYILAN_MALZEME)
    kontrol(bool(br) and br.group(1) == build.VARSAYILAN_RENK,
            "onden secili renk == bosSatir().renk (%r)" % build.VARSAYILAN_RENK)
    kontrol(build.FILAMENT_FARK.get(build.VARSAYILAN_MALZEME, 0) == 0,
            "varsayilan malzemenin fiyat farki %0 (liste fiyatinin USTUNE cikmaz)")
    kontrol(build.VARSAYILAN_RENK != "Diğer",
            'varsayilan renk "Diğer" DEGIL (+%%%d ozel renk carpani devreye girmez)'
            % build.RENK_DIGER_YUZDE)


# ------------------------------------------------------------------ node kosucusu
NODE_RUNNER = r"""
"use strict";
/* PRUVO — sepet secim kabul testi node kosucusu (gecici dizine yazilir, depoda DURMAZ).
   KOD KOPYALANMAZ: uretilen GERCEK urun sayfasinin KENDI JS'i node:vm'de kosar; DOM
   sadece o sayfanin ISARETLEMESINDEN kurulur (onden secili siniflar dahil). */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const KOK = process.argv[2];
const SAYFA = process.argv[3];
const html = fs.readFileSync(SAYFA, "utf8");
const SECENEK = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");

/* ---------------- mini DOM ---------------- */
function El(tag) {
  this.tagName = String(tag || "div").toUpperCase();
  this.children = []; this.parentNode = null; this.attrs = {}; this.style = {};
  this.className = ""; this.textContent = ""; this.id = ""; this.value = "";
  this.hidden = false; this.disabled = false; this.offsetWidth = 0; this._dinleyici = {};
}
El.prototype.setAttribute = function (k, v) {
  this.attrs[k] = String(v);
  if (k === "class") { this.className = String(v); }
  if (k === "hidden") { this.hidden = true; }
  if (k === "id") { this.id = String(v); }
};
El.prototype.removeAttribute = function (k) {
  delete this.attrs[k];
  if (k === "hidden") { this.hidden = false; }
};
El.prototype.getAttribute = function (k) {
  if (k === "class") { return this.className; }
  return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null;
};
El.prototype.appendChild = function (c) { this.children.push(c); c.parentNode = this; return c; };
El.prototype.insertBefore = function (c) { return this.appendChild(c); };
El.prototype.removeChild = function (c) {
  this.children = this.children.filter((x) => x !== c);
};
El.prototype.focus = function () {};
El.prototype.scrollIntoView = function () {};
El.prototype.addEventListener = function (tur, f) {
  (this._dinleyici[tur] = this._dinleyici[tur] || []).push(f);
};
El.prototype.removeEventListener = function () {};
El.prototype.tetikle = function (tur) {
  for (const f of (this._dinleyici[tur] || [])) { f.call(this, { type: tur }); }
};
El.prototype.click = function () { this.tetikle("click"); };
El.prototype._tumu = function (out) {
  out = out || [];
  for (const c of this.children) { out.push(c); c._tumu(out); }
  return out;
};
function eslesir(el, sec) {
  /* Cok dar bir secici motoru: ".a", ".a.b", "tag", virgullu liste. */
  for (const parca of sec.split(",")) {
    const s = parca.trim();
    if (!s) { continue; }
    const siniflar = s.split(".").filter(Boolean);
    const etiket = s.startsWith(".") ? null : siniflar.shift();
    if (etiket && el.tagName !== etiket.toUpperCase()) { continue; }
    const var_ = (el.className || "").split(/\s+/);
    if (siniflar.every((c) => var_.indexOf(c) !== -1)) { return true; }
  }
  return false;
}
El.prototype.querySelectorAll = function (sec) {
  return this._tumu().filter((e) => eslesir(e, sec));
};
El.prototype.querySelector = function (sec) {
  const l = this.querySelectorAll(sec); return l.length ? l[0] : null;
};
Object.defineProperty(El.prototype, "classList", {
  get() {
    const el = this;
    return {
      add(c) { if (!this.contains(c)) { el.className = (el.className + " " + c).trim(); } },
      remove(c) {
        el.className = el.className.split(/\s+/).filter((x) => x !== c).join(" ");
      },
      contains(c) { return el.className.split(/\s+/).indexOf(c) !== -1; },
      toggle(c, v) {
        const on = (v === undefined) ? !this.contains(c) : !!v;
        if (on) { this.add(c); } else { this.remove(c); }
      },
    };
  },
});

/* ---- sayfanin ISARETLEMESINDEN DOM kur (onden secili siniflar AYNEN gelir) ---- */
const kok = new El("body");
const kimlik = new Map();
function ekle(el, id) { if (id) { el.id = id; kimlik.set(id, el); } kok.appendChild(el); return el; }

function grupKur(kapsayiciId) {
  const re = new RegExp('id="' + kapsayiciId + '">([\\s\\S]*?)</div>');
  const m = html.match(re);
  if (!m) { return null; }
  const kap = ekle(new El("div"), kapsayiciId);
  const btnRe = /<button\b([^>]*)>/g;
  let b;
  while ((b = btnRe.exec(m[1])) !== null) {
    const el = new El("button");
    /* Butonun TUM ozniteligi kopyalanir (class, data-malzeme, data-katsayi, data-renk,
       data-gorsel ...) — sayfa JS'i hangisini okursa okusun ISARETLEMEDEN gelsin. */
    const oz = /([-\w]+)="([^"]*)"/g;
    let a;
    while ((a = oz.exec(b[1])) !== null) { el.setAttribute(a[1], a[2]); }
    kap.appendChild(el);
  }
  return kap;
}
grupKur("filCipler");
grupKur("malzemeButonlar");
grupKur("renkButonlar");
for (const id of ["cartBtn", "cartFab", "cartCount", "orderAlt", "opsiyonFiyat",
                  "adetSec", "adetEksi", "adetArti", "konfAlanlar", "konfHacim",
                  "konfigurBoy", "konfigurKaydirici", "mainImg"]) {
  if (html.indexOf('id="' + id + '"') !== -1) { ekle(new El("div"), id); }
}
if (html.indexOf('id="renkOzel"') !== -1) { ekle(new El("input"), "renkOzel"); }
/* #secimHata sayfada VARSA DOM'a girer; YOKSA bilerek girmez -> sayfa JS'inin
   kendi kutusunu URETIP uretmedigi (fail-loud yedek yol) da olculebilsin. */
if (html.indexOf('id="secimHata"') !== -1) {
  const h = ekle(new El("div"), "secimHata");
  h.setAttribute("hidden", "hidden");
}
const adet = kimlik.get("adetSec");
if (adet) { adet.value = "1"; }

const depo = new Map();
/* getElementById SAYFAYA SADIK: id sayfada VARSA (gerekirse tembel) uretilir, YOKSA null
   doner. "Bilinmeyen her id icin bos eleman uret" saplamasi kolay olurdu ama #secimHata'yi
   SAYFADAN SOKEN mutant (M4) o saplamada da yesil kalirdi — kapi olurdu. */
function idVarMi(id) { return html.indexOf('id="' + id + '"') !== -1; }
const belge = {
  getElementById: (id) => {
    if (kimlik.has(id)) { return kimlik.get(id); }
    if (!idVarMi(id)) { return null; }
    return ekle(new El("div"), id);
  },
  createElement: (t) => new El(t),
  createTextNode: (t) => { const e = new El("#text"); e.textContent = String(t); return e; },
  querySelector: (s) => kok.querySelector(s),
  querySelectorAll: (s) => kok.querySelectorAll(s),
  body: kok, documentElement: new El("html"), head: new El("head"),
  addEventListener() {}, removeEventListener() {}, readyState: "complete", cookie: "",
};
let alertMetni = null;
const ctx = {
  document: belge,
  location: { hash: "", search: "", pathname: "/urun/x/", href: "https://pruvo3d.com/urun/x/",
              replace() {} },
  history: { replaceState() {} },
  localStorage: {
    getItem: (k) => (depo.has(k) ? depo.get(k) : null),
    setItem: (k, v) => { depo.set(k, String(v)); },
    removeItem: (k) => { depo.delete(k); },
  },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  console: { log() {}, warn() {}, error() {}, info() {}, debug() {} },
  alert(m) { alertMetni = String(m); },
  confirm: () => true, navigator: { userAgent: "node" },
  URLSearchParams, URL, setTimeout, clearTimeout, setInterval, clearInterval,
  Math, JSON, Date, encodeURIComponent, decodeURIComponent, Promise,
  addEventListener() {}, removeEventListener() {}, scrollTo() {}, scrollY: 0,
  innerHeight: 800, innerWidth: 1280,
  requestAnimationFrame(f) { return setTimeout(f, 0); },
  matchMedia: () => ({ matches: false, addListener() {}, addEventListener() {} }),
  fetch: () => new Promise(() => {}),
};
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(SECENEK, ctx, { filename: "secenekler.js" });
/* Sayfanin REFERANS ETTIGI yerel moduller (kod kopyalanmaz, GERCEK dosya kosar).
   /varlik/ varliklari yayin_yuzey ile zaten satir ici gelmistir. */
for (const yerel of ["/konfigur.js"]) {
  if (html.indexOf('src="' + yerel + '"') !== -1 ||
      html.indexOf('src="' + yerel + '?') !== -1) {
    vm.runInContext(fs.readFileSync(path.join(KOK, yerel.slice(1)), "utf8"), ctx,
                    { filename: yerel });
  }
}
const scriptHatalari = [];
let scriptSayisi = 0;
for (const m of html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)) {
  const govde = m[1];
  if (!govde.trim() || /application\/ld\+json/.test(m[0])) { continue; }
  scriptSayisi += 1;
  try { vm.runInContext(govde, ctx, { filename: "sayfa.js" }); }
  catch (e) { scriptHatalari.push(String((e && e.message) || e)); }
}

/* ---------------- olcumler ---------------- */
const cart = kimlik.get("cartBtn");
const cipler = kimlik.get("filCipler");
const renkler = kimlik.get("renkButonlar");
const ozel = kimlik.get("renkOzel");
function sepet() {
  const ham = depo.get("pruvo_sepet");
  if (!ham) { return []; }
  try { return JSON.parse(ham); } catch (e) { return null; }
}
function hataDurumu() {
  const el = kimlik.get("secimHata") ||
             kok._tumu().find((e) => e.id === "secimHata");
  if (!el) { return { var: false, metin: alertMetni || "", gorunur: !!alertMetni }; }
  return { var: true, metin: el.textContent || "", gorunur: !el.hidden };
}
const sonuc = { adimlar: {}, scriptHatalari, scriptSayisi,
                cartDinleyici: cart ? (cart._dinleyici.click || []).length : -1 };
sonuc.baslangic = {
  seciliMalzeme: cipler ? (cipler.querySelectorAll(".fil-cip.secili")
    .map((e) => e.getAttribute("data-malzeme"))) : [],
  seciliRenk: renkler ? (renkler.querySelectorAll(".renk-btn.secili")
    .map((e) => e.getAttribute("data-renk"))) : [],
};

sonuc.konfiguratorVar = !!ctx.PRUVO_KONFIGUR;
sonuc.konfigurGecerli = ctx.PRUVO_KONFIGUR && ctx.PRUVO_KONFIGUR.hazir
  ? !!ctx.PRUVO_KONFIGUR.gecerliMi() : null;

/* c1 — HIC SECIM YAPMADAN tikla */
if (cart) { cart.click(); }
sonuc.adimlar.c1 = { sepet: sepet(), hata: hataDurumu() };

/* c2 — sepeti bosalt, secimi EKSILT ve tekrar tikla -> GORUNUR hata bekleniyor.
   kart kolu : rengi "Diğer"e cek, serbest metin kutusunu BOS birak.
   konfigur  : sayfanin gordugu gecerlilik hukmunu false'a sabitle (guard'in KENDISI olculur;
               konfigur'de renk butonunu "bosaltmanin" arayuz yolu yok). */
depo.set("pruvo_sepet", "[]");
let eksiltildi = false;
const digerBtn = renkler
  ? renkler.querySelectorAll(".renk-btn").find((e) => e.getAttribute("data-renk") === "Diğer")
  : null;
if (ctx.URUN_KART_SECIM && digerBtn) {
  digerBtn.click();
  if (ozel) { ozel.value = ""; }
  eksiltildi = true;
} else if (ctx.PRUVO_KONFIGUR) {
  ctx.PRUVO_KONFIGUR.gecerliMi = () => false;
  eksiltildi = true;
}
if (cart) { cart.click(); }
sonuc.adimlar.c2 = { sepet: sepet(), hata: hataDurumu(), eksiltildi };

/* c3 — eksigi gider, tekrar tikla -> sepet dolar, hata kapanir */
if (ctx.URUN_KART_SECIM) {
  if (ozel) { ozel.value = "turuncu"; ozel.tetikle("input"); }
} else if (ctx.PRUVO_KONFIGUR && renkler) {
  ctx.PRUVO_KONFIGUR.gecerliMi = () => true;
  const ilk = renkler.querySelectorAll(".renk-btn")[0];
  if (ilk) { ilk.click(); }
}
if (cart) { cart.click(); }
sonuc.adimlar.c3 = { sepet: sepet(), hata: hataDurumu() };

/* istemcinin GORDUGU kurus — c1 satiri icin (URUN sayfadaki gercek veri) */
try {
  const s1 = (sonuc.adimlar.c1.sepet || [])[0];
  if (s1 && ctx.PRUVO_SECENEK && ctx.URUN) {
    const oz = ctx.PRUVO_SECENEK.satirOzeti(ctx.URUN, s1);
    sonuc.istemciKurus = oz ? oz.kurus : null;
    sonuc.istemciBirim = oz ? oz.birimKurus : null;
  }
  sonuc.urun = ctx.URUN || null;
} catch (e) { sonuc.istemciHata = String(e && e.message); }

process.stdout.write(JSON.stringify(sonuc));
"""


def _node():
    return shutil.which("node")


def node_kos(gecici, sayfa_yolu):
    node = _node()
    if not node:
        return None, "node bulunamadi"
    runner = os.path.join(gecici, "sepet-kosucu.js")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(NODE_RUNNER)
    r = subprocess.run([node, runner, ROOT, sayfa_yolu], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None, "kosucu dustu (rc=%s): %s" % (r.returncode, (r.stderr or "")[-800:])
    try:
        return json.loads(r.stdout), None
    except ValueError as e:
        return None, "kosucu ciktisi ayristirilamadi: %s" % e


# ------------------------------------------------------------------ (c) DAVRANIS
def bolum_c(gecici, sayfalar):
    print("\n(c) DAVRANIS — uretilen sayfanin KENDI JS'i (node:vm) tiklamayla surulur")
    olcumler = {}
    urun_ix = {p["id"]: p for p in _urunler()}
    for fx in FIKSTURLER:
        pid, ad = fx["id"], fx["ad"]
        veri, hata = node_kos(gecici, sayfalar[pid])
        if veri is None:
            olculemedi("%s: %s" % (ad, hata))
            continue
        olcumler[pid] = veri
        if fx["kol"] == "konfigur":
            kontrol(veri.get("konfiguratorVar"),
                    "%s: /konfigur.js gercekten yuklendi (olcum bosa dusmedi)" % ad)
            kontrol(veri.get("konfigurGecerli") is True,
                    "%s: sayfa acilir acilmaz konfigur GECERLI — onden secili renk yalnizca "
                    "gorunuste degil, DURUMDA da dolu (%s)" % (ad, veri.get("konfigurGecerli")))
        # FAIL-LOUD: sayfanin kendi JS'i patlarsa asagidaki "sepet bos" olcumu YANLIS
        # sebeple kirmizi/yesil olurdu -> hata SESSIZ YUTULMAZ.
        kontrol(not veri.get("scriptHatalari"),
                "%s: sayfa scriptleri hatasiz kostu (%d blok, hata: %s)"
                % (ad, veri.get("scriptSayisi", 0), veri.get("scriptHatalari")))
        kontrol(veri.get("cartDinleyici") == 1,
                "%s: sepet butonuna TEK click dinleyicisi baglandi (%s)"
                % (ad, veri.get("cartDinleyici")))
        b = veri.get("baslangic", {})
        if fx["kol"] == "kart":
            kontrol(b.get("seciliMalzeme") == [build.on_secim_malzeme(urun_ix[pid])],
                    "%s: sayfa yuklenince malzeme durumu DOLU ve KURALIN sectigi ad (%r)"
                    % (ad, b.get("seciliMalzeme")))
        c1 = veri["adimlar"]["c1"]
        s1 = c1.get("sepet") or []
        kontrol(len(s1) == 1,
                "%s: c1 — hic secim yapmadan tiklama SEPETI DOLDURDU (satir: %d)"
                % (ad, len(s1)))
        if s1 and fx["kol"] == "kart":
            kontrol(s1[0].get("malzeme") == build.on_secim_malzeme(urun_ix[pid])
                    and s1[0].get("renk") == build.VARSAYILAN_RENK,
                    "%s: c1 satiri ONDEN SECILI malzemeyi + varsayilan rengi tasiyor (%s/%s)"
                    % (ad, s1[0].get("malzeme"), s1[0].get("renk")))
        if s1 and fx["kol"] == "konfigur":
            bek_r = build._konfigur_varsayilan_renk(urun_ix[pid]["konfigur"])
            kontrol(s1[0].get("renk") == bek_r
                    and s1[0].get("malzeme")
                    == (urun_ix[pid]["konfigur"] or {}).get("varsayilanMalzeme"),
                    "%s: c1 satiri onden secili malzeme/rengi tasiyor (%s/%s)"
                    % (ad, s1[0].get("malzeme"), s1[0].get("renk")))
        c2 = veri["adimlar"]["c2"]
        kontrol(c2.get("eksiltildi"), "%s: c2 — secim gercekten eksiltilebildi" % ad)
        kontrol((c2.get("sepet") or []) == [],
                "%s: c2 — eksik secimde sepet DEGISMEDI" % ad)
        kontrol(bool((c2.get("hata") or {}).get("gorunur"))
                and len(((c2.get("hata") or {}).get("metin") or "").strip()) >= 10,
                "%s: c2 — GORUNUR hata METNI cikti (%r) — sessiz basarisizlik yolu YOK"
                % (ad, (c2.get("hata") or {}).get("metin")))
        c3 = veri["adimlar"]["c3"]
        kontrol(len(c3.get("sepet") or []) == 1,
                "%s: c3 — eksik giderilince ekleme BASARILI" % ad)
        kontrol(not (c3.get("hata") or {}).get("gorunur"),
                "%s: c3 — hata kutusu kendiliginden kapandi" % ad)
    return olcumler


# ------------------------------------------------------------------ (d) SUNUCU PARITESI
SUNUCU_RUNNER = r"""
"use strict";
/* Istemcinin YAZDIGI sepet satirini SUNUCUNUN fiyat kolundan gecirir.
   Kural KOPYALANMAZ: shop worker'in sabit-katalog kolu SECENEK.satirOzeti'yi
   D1 satirindan (kategori/fiyat/tur) kurulan urunle cagirir — burada AYNISI yapilir. */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const KOK = process.argv[2];
const veri = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const ctx = { console: { log() {} }, Math, JSON, Date };
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), ctx,
                { filename: "secenekler.js" });
const S = ctx.PRUVO_SECENEK;
const k = veri.kalem;
/* Worker istekCoz() dogrulamasi: malzeme/renk/adet beyaz-listeden GECMELI. */
const gecerliMalzeme = Object.prototype.hasOwnProperty.call(S.FILAMENT_FARK, k.malzeme);
const gecerliRenk = S.RENK_SECENEKLERI.indexOf(k.renk) !== -1;
const gecerliAdet = Number.isInteger(k.adet) && k.adet >= S.ADET_EN_AZ && k.adet <= S.ADET_EN_COK;
const d1 = veri.d1;   /* D1 `urunler` satiri (kategori, fiyat, tur) */
const ozet = S.satirOzeti(
  { kategori: d1.kategori, fiyat: d1.fiyat, parametrik: false, boy_secenekleri: [], tur: d1.tur },
  { id: k.id, malzeme: k.malzeme, renk: k.renk, renk_ozel: k.renk_ozel,
    boy_etiket: null, adet: k.adet });
process.stdout.write(JSON.stringify({
  gecerliMalzeme, gecerliRenk, gecerliAdet,
  sunucuKurus: ozet.kurus, sunucuBirim: ozet.birimKurus,
}));
"""


def bolum_d(gecici, olcumler):
    print("\n(d) SUNUCU PARITESI — istemcinin yazdigi satir SUNUCU fiyat kolundan gecer")
    node = _node()
    if not node:
        olculemedi("node yok — sunucu paritesi olculemedi")
        return
    pid = "bmw-kaput-a-ma-kolu"      # sabit katalog fiyatli kol (paylasilan satirOzeti)
    veri = olcumler.get(pid)
    if not veri:
        olculemedi("%s davranis olcumu yok — sunucu paritesi olculemedi" % pid)
        return
    satir = (veri["adimlar"]["c1"].get("sepet") or [None])[0]
    if not satir:
        kontrol(False, "sunucu paritesi: c1 sepeti BOS — olculecek satir yok")
        return
    urun = {p["id"]: p for p in _urunler()}[pid]
    girdi = {
        "kalem": {"id": satir.get("id"), "malzeme": satir.get("malzeme"),
                  "renk": satir.get("renk"), "renk_ozel": satir.get("renk_ozel") or "",
                  "adet": satir.get("adet")},
        # D1 `urunler` satirinin PARA YOLUNA giren alanlari (kategori/fiyat/tur)
        "d1": {"kategori": urun.get("kategori"), "fiyat": urun.get("fiyat"),
               "tur": urun.get("tur")},
    }
    gy = os.path.join(gecici, "sunucu-girdi.json")
    with open(gy, "w", encoding="utf-8") as f:
        json.dump(girdi, f, ensure_ascii=False)
    ry = os.path.join(gecici, "sunucu-kosucu.js")
    with open(ry, "w", encoding="utf-8") as f:
        f.write(SUNUCU_RUNNER)
    r = subprocess.run([node, ry, ROOT, gy], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        olculemedi("sunucu kosucusu dustu: %s" % (r.stderr or "")[-500:])
        return
    s = json.loads(r.stdout)
    kontrol(s["gecerliMalzeme"] and s["gecerliRenk"] and s["gecerliAdet"],
            "sunucu dogrulamasi: on-secimli satir malzeme/renk/adet beyaz-listesinden GECIYOR")
    kontrol(veri.get("istemciKurus") is not None and s["sunucuKurus"] is not None,
            "iki uc da kurus uretti (istemci=%s sunucu=%s)"
            % (veri.get("istemciKurus"), s["sunucuKurus"]))
    kontrol(veri.get("istemciKurus") == s["sunucuKurus"]
            and veri.get("istemciBirim") == s["sunucuBirim"],
            "KURUS ESITLIGI — istemci %s / sunucu %s (birim %s / %s)"
            % (veri.get("istemciKurus"), s["sunucuKurus"],
               veri.get("istemciBirim"), s["sunucuBirim"]))
    # 🔴 IDDIA YON DEGISTIRDI (11 Agu, isletme karari): urun sayfasi artik ONERILEN
    # malzemenin tutarini vurgular, yani sunucu birimi LISTE tutari OLMAYABILIR. Eski
    # iddia ("liste fiyati DEGISMEDI") bugun bayattir. Yerine IKI iddia konur ve
    # boylece kapsam SIZINTISI da olculur (iddia sayisi DUSMEZ, ARTAR):
    #   1. sunucu birimi = URUN SAYFASININ ilan ettigi tutar  (sessiz zam/indirim YOK)
    #   2. KART/BESLEME tutari LISTE'de KALDI                 (kapsam sizmadi)
    liste = build.price_number(urun.get("fiyat"))
    try:
        liste_kurus = None if liste in (None, "") else int(round(float(liste) * 100))
    except (TypeError, ValueError):
        liste_kurus = None
    ilan = build.ilan_kurus(urun)
    kontrol(ilan is not None and s["sunucuBirim"] == ilan,
            "SUNUCU birimi = urun sayfasinin ILAN ettigi tutar (%s kurus = %s)"
            % (ilan, s["sunucuBirim"]))
    kontrol(liste_kurus is not None and build.vitrin_kurus(urun) == liste_kurus,
            "KART/BESLEME tutari LISTE'de KALDI — kapsam sizmasi YOK (liste %s = kart %s)"
            % (liste_kurus, build.vitrin_kurus(urun)))


# ------------------------------------------------------------------ mutasyon
# (kod, aciklama, hedef dosya, eski, yeni, beklenen_rc)
MUTANTLAR = [
    ("M1", "onden secim SOKULDU (varsayilan cip isaretlenmiyor)", "tools/build.py",
     '        if secili is not None and f["ad"] == secili:',
     '        if False:', 1),
    ("M2", "gorunur hata metni SOKULDU (yalniz titreme kalir)", "tools/build.py",
     '        hataGoster(eksikAd.length', '        void(eksikAd.length', 1),
    ("M3", "kart-secim: secici yeniden butonun ALTINA alindi", "tools/build.py",
     "      {malzeme}\n      {renk}\n      {boy}\n      {adet}\n      {hata}\n      {fiyat_blok}",
     "      {renk}\n      {boy}\n      {adet}\n      {hata}\n      {malzeme}\n      {fiyat_blok}",
     1),
    ("M7", "konfigur: secici yeniden butonun ALTINA alindi", "tools/build.py",
     "      {malzeme}\n      {renk}\n      {boy}\n      {adet}\n      {hata}\n"
     '      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>',
     "      {renk}\n      {boy}\n      {adet}\n      {hata}\n      {malzeme}\n"
     '      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>', 1),
    ("M8", "konfigur: onden secili renk DURUMA yazilmiyor (secili gorunur, calismaz)",
     "konfigur.js",
     'var ilkR = durum.renkKok.querySelector(".renk-btn.secili");',
     'var ilkR = null;', 1),
    ("M4", "hata kutusu sayfadan KALDIRILDI (yedek yol da olculur)", "tools/build.py",
     "SECIM_HATA_HTML = ('<div class=\"secim-hata\" id=\"secimHata\"",
     "SECIM_HATA_HTML = ('<div class=\"secim-hata\" id=\"secimHataYOK\"", 1),
    ("M5", "on-secim FIYAT FARKLI malzemeye cevrildi (sessiz zam)", "tools/build.py",
     'VARSAYILAN_MALZEME = _js_bos_satir_varsayilani(_SEC_JS, "malzeme")',
     'VARSAYILAN_MALZEME = "PETG"', 1),
    ("M6", "KONTROL: davranisi degistirmeyen yeniden adlandirma", "tools/build.py",
     "def _fil_cipleri(p, secili=None):", "def _fil_cipleri(p, secili_ad=None):", 0),
]
M6_EK = [
    ('        if secili is not None and f["ad"] == secili:',
     '        if secili_ad is not None and f["ad"] == secili_ad:'),
]
# Mutasyona ugrayabilen KOK dosyalari GERCEK KOPYA olur; kalan her sey symlink kalir
# (gercek depo dosyasina DOKUNULMAZ — symlink uzerinden yazmak kaynagi bozardi).
MUTASYON_KOK_DOSYALARI = ("konfigur.js", "index.html", "secenekler.js")


def _gecici_kok():
    tmp = tempfile.mkdtemp(prefix="sepet-secim-mut-")
    shutil.copytree(TOOLS, os.path.join(tmp, "tools"), symlinks=True)
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git", "varlik", "urun", "_yayin"):
            continue
        kaynak = os.path.join(ROOT, ad)
        if ad in MUTASYON_KOK_DOSYALARI and os.path.isfile(kaynak):
            shutil.copy2(kaynak, os.path.join(tmp, ad))
        else:
            os.symlink(kaynak, os.path.join(tmp, ad))
    return tmp


def _uygula(yol, ciftler):
    with open(yol, encoding="utf-8") as f:
        s = f.read()
    for eski, yeni in ciftler:
        if eski not in s:
            return False, eski[:60]
        s = s.replace(eski, yeni, 1)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(s)
    return True, None


def mutasyon():
    print("\n" + "=" * 70)
    print("MUTASYON NOBETI — kapi OLU mu? (yedi kirmizi + bir KONTROL yesil)")
    kendi = os.path.abspath(__file__)
    sapan = []
    print("\n%-4s %-56s %-9s %-9s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
    for kod, aciklama, dosya, eski, yeni, beklenen in MUTANTLAR:
        ciftler = [(eski, yeni)] + (M6_EK if kod == "M6" else [])
        tmp = _gecici_kok()
        try:
            ok, capa = _uygula(os.path.join(tmp, *dosya.split("/")), ciftler)
            if not ok:
                sapan.append("%s: capa uygulanamadi (%r)" % (kod, capa))
                print("%-4s %-56s %-9s %-9s CAPA YOK" % (kod, aciklama[:56], beklenen, "-"))
                continue
            r = subprocess.run([sys.executable, os.path.join(tmp, "tools",
                                                             os.path.basename(kendi))],
                               capture_output=True, text=True, cwd=tmp)
            rc = r.returncode
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        tamam = (rc == beklenen)
        if not tamam:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d" % (kod, beklenen, rc))
        print("%-4s %-56s %-9s %-9s %s"
              % (kod, aciklama[:56], "KIRMIZI" if beklenen else "YESIL", renk,
                 "OK" if tamam else "SAPTI"))
    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: %d mutantin hepsi beklenen rengi verdi (M6 kontrol mutanti YESIL)."
          % len(MUTANTLAR))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args()

    print("SEPETE EKLE — SESSIZ BASARISIZLIK KAPISI")
    gecici = tempfile.mkdtemp(prefix="sepet-secim-")
    try:
        sayfalar, hata = sayfalari_uret(gecici)
        if sayfalar is None:
            print("OLCULEMEDI: " + hata)
            return 2
        bolum_a(sayfalar)
        bolum_b()
        olcumler = bolum_c(gecici, sayfalar)
        bolum_d(gecici, olcumler)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("\n" + "-" * 70)
    if OLCULEMEDI:
        print("OLCULEMEDI (%d):" % len(OLCULEMEDI))
        for m in OLCULEMEDI:
            print("  - " + m)
    if HATALAR:
        print("SONUC: KIRMIZI ❌ — %d iddia dustu" % len(HATALAR))
        for m in HATALAR:
            print("  - " + m)
        return 1
    if OLCULEMEDI:
        print("SONUC: OLCULEMEDI ⚠️")
        return 2
    print("SONUC: YESIL ✅ — sessiz sepet basarisizligi yolu KALMADI")

    if a.mutasyon:
        return mutasyon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
