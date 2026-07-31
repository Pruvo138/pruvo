#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESKI FIYAT KABUL TESTI — opsiyonel `eski_fiyat` alani (ustu cizili indirim gosterimi).

    python3 tools/eski-fiyat-test.py
    python3 tools/eski-fiyat-test.py --mutasyon     # + 12 mutant (hepsi KIRMIZI olmali)

NEDEN VAR — HATA SINIFI SESSIZ: `eski_fiyat` musteriye "indirim" gosterir. Yanlis
gosterim (eski <= guncel, baska para birimi, ayristirilamaz dize, olcuye gore DEGISEN
fiyatin yaninda SABIT bir eski fiyat) YANILTICI INDIRIM'dir: kimse hata mesaji gormez,
sayfa duzgun gorunur, zarar ticari/hukukidir. Bu yuzden kural FAIL-CLOSED'dir —
supheli her durumda HIC gosterilmez — ve burada CALISTIRILARAK olculur.

🔴 PARA EKSENI: `eski_fiyat` YALNIZ GOSTERIMDIR. Sepet/konfigur/iyzico/D1/feed/JSON-LD
   fiyat hesabi bu alani OKUMAZ. Bolum (e) bunu TAM KUME ile kanitlar: bugunku katalogun
   BUTUN konfigur kombinasyonlari (17 urun x 25 boy x 3 malzeme = 1275) degisiklik
   ONCESI (merge-base tools/build.py) ve SONRASI kurusu kurusuna karsilastirilir.
   ORNEKLEME YOK.

OLCULEN BOLUMLER
  (a) KURAL         — tools/build.py eski_fiyat_gosterim(), 27 vakalik tablo.
  (b) PARITE        — index.html'in GERCEK kart cizicisi (node:vm, kod KOPYALANMAZ) AYNI
                      tabloda AYNI hukmu verir. Iki dilde iki kalip = drift riski; bu
                      bolum o drifti yakar.
  (c) SAYFA         — tools/build.py render_product ciktisi: gecerli vakada <s
                      class="eski-fiyat"> + line-through GERCEKTEN uretilir; GECERSIZ
                      vakada uretilen HTML, alan HIC YOKKEN uretilenle BAYT-ESITTIR
                      (sifir iz); parametrik/konfigur sayfasinda basilmaz; XSS yuku
                      sayfaya SIZMAZ.
  (d) CANLI NOBET   — uretilen sayfanin KENDI JS'i (node:vm) ustu cizili fiyati, secim
                      birim fiyati eski fiyatin ustune ciktiginda GIZLER.
  (e) PARA EKSENI   — 1275 kombinasyon oncesi/sonrasi kurus esitligi + feed/JSON-LD
                      fiyatlarinin degismedigi.
  (f) OZET/KART     — kart_ozeti alani YALNIZ kurali gecen uründe tasir; bugunku
                      katalogda ozet.json BAYT-ESIT kalir.
  (g) SEMA KAPILARI — duzelt.py alani mesru sayar, diriltme-kapisi.py EKSEN 2 kapsaminda.

NE IDDIA EDILMEZ (beyan edilen kor noktalar — sessiz yesil yasak):
  * Worker (/katalog, /ara) kart alanlari: `eski_fiyat` orada YOK. Edge modunda Worker'dan
    gelen kartta ustu cizili fiyat GORUNMEZ (fail-closed: eksik alan = gosterme). Worker
    HocA'nin duzlemi -> KraL'a raporlandi, burada OLCULEMEZ.
  * Gorsel yerlesim/estetik (CSS kurallari basilir mi olculur, NASIL gorundugu olculmez).
  * Kullanicinin malzeme KARTINA TIKLAMASI: (d) nobeti render() kod yolunu GERCEKTEN
    kosar ama tetikleyicisi tiklama degil, kontrollu satirOzeti'dir.

CIKIS: 0 yesil · 1 kirmizi · 2 olculemedi (referans/node yok).
Offline; depoya YAZMAZ (mutantlar bellekte exec / gecici dizinde).
"""
import argparse
import copy
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

import build  # noqa: E402

HATALAR = []
OLCULEMEDI = []


def kontrol(kosul, mesaj):
    if kosul:
        print("  ✅ " + mesaj)
    else:
        print("  ❌ " + mesaj)
        HATALAR.append(mesaj)
    return bool(kosul)


def olculemedi(mesaj):
    print("  ⚪ ÖLÇÜLEMEDİ — " + mesaj)
    OLCULEMEDI.append(mesaj)


# ------------------------------------------------------------------ VAKA TABLOSU
# TEK KAYNAK: (a) Python kuralini, (b) index.html'in gercek kart cizicisini AYNI tablo
# uzerinde olcer. "beklenen" = gosterilecek metin ya da None (HIC gosterme).
KONF_SAHTE = {"boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150}}
VAKALAR = [
    ("yok", {"fiyat": "850 TL"}, None),
    ("gecerli", {"fiyat": "850 TL", "eski_fiyat": "1.200 TL"}, "1.200 TL"),
    ("gecerli-kurusatli", {"fiyat": "850 TL", "eski_fiyat": "1.200,50 TL"}, "1.200,50 TL"),
    ("gecerli-try", {"fiyat": "850 TL", "eski_fiyat": "1200 TRY"}, "1200 TRY"),
    ("gecerli-simge", {"fiyat": "850 TL", "eski_fiyat": "1.200 ₺"}, "1.200 ₺"),
    ("gecerli-bosluklu", {"fiyat": "850 TL", "eski_fiyat": "  1.200 TL  "}, "1.200 TL"),
    ("gecerli-ek-metinli-fiyat", {"fiyat": "350 TL (12 cm)", "eski_fiyat": "500 TL"}, "500 TL"),
    ("eski-kucuk", {"fiyat": "850 TL", "eski_fiyat": "800 TL"}, None),
    ("eski-esit", {"fiyat": "850 TL", "eski_fiyat": "850 TL"}, None),
    ("eski-esit-kurus", {"fiyat": "850 TL", "eski_fiyat": "850,00 TL"}, None),
    ("birim-farkli-eski", {"fiyat": "850 TL", "eski_fiyat": "1200 USD"}, None),
    ("birim-farkli-guncel", {"fiyat": "850 USD", "eski_fiyat": "1200 TL"}, None),
    ("bos-dize", {"fiyat": "850 TL", "eski_fiyat": ""}, None),
    ("yalniz-bosluk", {"fiyat": "850 TL", "eski_fiyat": "   "}, None),
    ("cop-dize", {"fiyat": "850 TL", "eski_fiyat": "indirim!"}, None),
    ("cop-sayisiz", {"fiyat": "850 TL", "eski_fiyat": "TL"}, None),
    ("belirsiz-nokta", {"fiyat": "850 TL", "eski_fiyat": "1.25 TL"}, None),
    # ⚠️ "9.99 TL" = belirsiz bicimin TEHLIKELI yonu: nokta binlik sayilirsa 999 TL olur
    # ve guncel 850 TL'nin USTUNE cikar -> UYDURMA bir indirim gorunur. Kalip gevserse
    # bu vaka KIRMIZI yanar (mutant M8).
    ("belirsiz-nokta-tehlikeli", {"fiyat": "850 TL", "eski_fiyat": "9.99 TL"}, None),
    ("bozuk-nokta", {"fiyat": "850 TL", "eski_fiyat": "1.2.3 TL"}, None),
    ("negatif", {"fiyat": "850 TL", "eski_fiyat": "-1200 TL"}, None),
    ("guncel-bozuk", {"fiyat": "1.2.3 TL", "eski_fiyat": "1.200 TL"}, None),
    ("guncel-bos", {"fiyat": "", "eski_fiyat": "1.200 TL"}, None),
    ("parametrik", {"fiyat": "850 TL", "eski_fiyat": "1.200 TL", "parametrik": True}, None),
    ("konfigur", {"fiyat": "150 TL", "eski_fiyat": "300 TL", "konfigur": KONF_SAHTE}, None),
    ("xss-onek", {"fiyat": "850 TL",
                  "eski_fiyat": "<s onload=alert(1)>1.200 TL</s>"}, None),
    ("xss-sonek", {"fiyat": "850 TL",
                   "eski_fiyat": "1.200 TL<img src=x onerror=alert(1)>"}, None),
    ("tip-sayi", {"fiyat": "850 TL", "eski_fiyat": 1200}, None),
    ("tip-liste", {"fiyat": "850 TL", "eski_fiyat": ["1.200 TL"]}, None),
    ("tip-null", {"fiyat": "850 TL", "eski_fiyat": None}, None),
]


def vaka_urunu(ad, govde, sira):
    """Vaka govdesinden GERCEK bir urun kaydi (kart cizilebilsin diye zorunlu alanlar)."""
    p = {
        "id": "eskifiyat-vaka-%02d-%s" % (sira, re.sub(r"[^a-z0-9]+", "-", ad)),
        "kategori": "Otomobil",
        "marka": [],
        "baslik": "Eski fiyat vakasi %02d" % sira,
        "aciklama": "Kabul testi fiksturu.",
        "gorseller": ["https://media.pruvo3d.com/urunler/eskifiyat-%02d.jpg" % sira],
    }
    p.update(govde)
    return p


VAKA_URUNLERI = [(ad, vaka_urunu(ad, g, i), bek)
                 for i, (ad, g, bek) in enumerate(VAKALAR)]


# ------------------------------------------------------------------ node kosucusu
NODE_RUNNER = r"""
"use strict";
/* PRUVO — eski-fiyat kabul testi node kosucusu (gecici dizine yazilir, depoda DURMAZ).
   Kod KOPYALANMAZ: GERCEK index.html / GERCEK uretilmis urun sayfasi node:vm'de kosar. */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const KOK = process.argv[2];
const MOD = process.argv[3];
const { inlineScriptBul, inlineScriptGovdeleri } =
  require(path.join(KOK, "tools", "html-blok-ayikla.js"));
const SECENEK = fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8");

const TUM = [];
function eleman(tag) {
  const el = {
    tagName: String(tag || "div").toUpperCase(), children: [], parentNode: null,
    style: {}, dataset: {}, attrs: {}, className: "", textContent: "", id: "",
    disabled: false, checked: false, value: "", href: "", hidden: false,
    onclick: null, onerror: null, offsetWidth: 0,
  };
  let html = "";
  Object.defineProperty(el, "innerHTML", {
    get() { return html; }, set(v) { html = String(v); el.children.length = 0; },
  });
  el.classList = {
    add(c) { if (!this.contains(c)) { el.className = (el.className + " " + c).trim(); } },
    remove(c) { el.className = el.className.split(/\s+/).filter((x) => x !== c).join(" "); },
    contains(c) { return el.className.split(/\s+/).indexOf(c) !== -1; },
    toggle(c, v) { const on = (v === undefined) ? !this.contains(c) : !!v;
      if (on) { this.add(c); } else { this.remove(c); } },
  };
  el.appendChild = (c) => { el.children.push(c); c.parentNode = el; return c; };
  el.removeChild = (c) => { el.children = el.children.filter((x) => x !== c); };
  el.insertBefore = (c) => el.appendChild(c);
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); if (k === "href") { el.href = String(v); } };
  el.removeAttribute = (k) => { delete el.attrs[k]; };
  el.getAttribute = (k) => (k in el.attrs ? el.attrs[k] : null);
  el.addEventListener = () => {}; el.removeEventListener = () => {};
  el.focus = () => {}; el.scrollIntoView = () => {}; el.click = () => {};
  el.querySelector = () => null; el.querySelectorAll = () => [];
  el.closest = () => null; el.remove = () => {};
  TUM.push(el);
  return el;
}
function belgeKur() {
  const kimlikler = new Map(), seciciler = new Map();
  return {
    getElementById(id) {
      if (!kimlikler.has(id)) { const e = eleman("div"); e.id = id; kimlikler.set(id, e); }
      return kimlikler.get(id);
    },
    _kimlikler: kimlikler,
    _elle(id, el) { el.id = id; kimlikler.set(id, el); return el; },
    createElement: (t) => eleman(t),
    createTextNode: (t) => { const e = eleman("#text"); e.textContent = String(t); return e; },
    querySelector(s) { if (!seciciler.has(s)) { seciciler.set(s, eleman("div")); } return seciciler.get(s); },
    querySelectorAll: () => [],
    body: eleman("body"), documentElement: eleman("html"),
    addEventListener() {}, removeEventListener() {}, execCommand: () => true,
    readyState: "complete", head: eleman("head"), cookie: "",
  };
}
function ctxKur(belge, ekFetch) {
  const ctx = {
    document: belge,
    location: { hash: "", search: "", pathname: "/", href: "https://pruvo3d.com/", replace() {} },
    history: { replaceState() {} },
    localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    fetch: ekFetch || (() => new Promise(() => {})),
    console: { log() {}, warn() {}, error() {}, info() {}, debug() {} },
    alert() {}, confirm: () => true, navigator: { userAgent: "node" },
    URLSearchParams, URL, setTimeout, clearTimeout, setInterval, clearInterval,
    Math, JSON, Date, encodeURIComponent, decodeURIComponent, Promise,
    addEventListener() {}, removeEventListener() {},
    scrollTo() {}, scrollY: 0, innerHeight: 720, innerWidth: 1280,
    requestAnimationFrame(f) { return setTimeout(f, 0); },
    matchMedia: () => ({ matches: false, addListener() {}, addEventListener() {} }),
  };
  ctx.window = ctx;
  ctx.self = ctx;
  ctx.globalThis = ctx;
  return ctx;
}
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---- MOD "kart": index.html'in GERCEK kart cizicisiyle vaka tablosunu olc ---- */
async function kart() {
  const indexYol = process.argv[4];
  const urunler = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
  let html = fs.readFileSync(indexYol, "utf8");
  const src = inlineScriptBul(html, "kartCiz");
  if (!src) { throw new Error("index.html inline scripti (imza 'kartCiz') bulunamadi"); }
  /* Kart cizici IKI besleme yolunda da AYNI fonksiyondur; HAM urun objesini (urunler.json
     sekli) olcmek icin edge yolu KAPATILIR. Capa bulunamazsa OLCULEMEDI (sessiz yesil yok). */
  const CAPA = "var EDGE_KATALOG = true;";
  if (src.indexOf(CAPA) === -1) { throw new Error("EDGE_KATALOG capasi bulunamadi"); }
  const kaynak = src.replace(CAPA, "var EDGE_KATALOG = false;");
  const belge = belgeKur();
  const ctx = ctxKur(belge, (url) => {
    const ham = String(url);
    if (ham.indexOf("urunler.json") === 0 || ham.indexOf("/urunler.json") === 0) {
      return Promise.resolve({ ok: true, status: 200,
        json: () => Promise.resolve(JSON.parse(JSON.stringify(urunler))) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
  });
  vm.createContext(ctx);
  vm.runInContext(SECENEK, ctx, { filename: "secenekler.js" });
  vm.runInContext(kaynak, ctx, { filename: "index-inline.js" });
  for (let i = 0; i < 40; i++) { await bekle(5); }

  /* Kart -> hukum: .card-price altinda <s class="eski-fiyat"> var mi? */
  const hukumler = {};
  for (const el of TUM) {
    if (!/(^|\s)card-price(\s|$)/.test(el.className || "")) { continue; }
    let ust = el.parentNode, pid = null;
    while (ust) {
      if (ust.href && ust.href.indexOf("/urun/") === 0) {
        pid = ust.href.replace(/^\/urun\/|\/$/g, ""); break;
      }
      ust = ust.parentNode;
    }
    if (!pid) { continue; }
    const s = el.children.find((c) => /(^|\s)eski-fiyat(\s|$)/.test(c.className || ""));
    hukumler[pid] = s ? s.textContent : null;
    /* Enjeksiyon capasi: ham veri innerHTML ile DOM'a girmemeli. */
    if (el.innerHTML) { hukumler["__innerHTML__" + pid] = el.innerHTML; }
  }
  process.stdout.write(JSON.stringify({ hukumler: hukumler }));
}

/* ---- MOD "sayfa": uretilen urun sayfasinin KENDI JS'i ustu cizili fiyati gizler mi ---- */
async function sayfa() {
  const sayfaHtml = fs.readFileSync(process.argv[4], "utf8");
  const birim = process.argv[5] === "null" ? null : parseInt(process.argv[5], 10);
  const belge = belgeKur();
  const eskiEl = eleman("s");
  eskiEl.className = "eski-fiyat";
  const m = sayfaHtml.match(/id="eskiFiyat" data-kurus="(\d+)"/);
  if (!m) { process.stdout.write(JSON.stringify({ bulundu: false })); return; }
  eskiEl.setAttribute("data-kurus", m[1]);
  belge._elle("eskiFiyat", eskiEl);
  const ctx = ctxKur(belge, null);
  vm.createContext(ctx);
  vm.runInContext(SECENEK, ctx, { filename: "secenekler.js" });
  /* GERCEK secenekler.js yuklendikten SONRA satirOzeti kontrollu bir birim kurus dondurur:
     olculen sey FIYAT hesabi degil, NOBETIN kendisidir (fiyat ekseni bolum (e)'de). */
  ctx.PRUVO_SECENEK.satirOzeti = function () {
    return { detay: "", adet: 1, birimKurus: birim, kurus: birim,
      fiyatMetni: "test", birimMetni: "test", odenebilir: birim != null };
  };
  for (const govde of inlineScriptGovdeleri(sayfaHtml)) {
    try { vm.runInContext(govde, ctx, { filename: "urun-sayfasi.js" }); } catch (e) { /* diger bloklar */ }
  }
  for (let i = 0; i < 10; i++) { await bekle(5); }
  process.stdout.write(JSON.stringify({ bulundu: true, hidden: !!eskiEl.hidden }));
}

(async () => {
  try {
    if (MOD === "kart") { await kart(); } else { await sayfa(); }
  } catch (e) {
    process.stderr.write(String((e && e.stack) || e));
    process.exit(3);
  }
})();
"""


def _node():
    return shutil.which("node")


def _runner_yaz(gecici):
    yol = os.path.join(gecici, "kosucu.js")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(NODE_RUNNER)
    return yol


def node_kart_hukumleri(gecici, index_yol, urunler):
    """index.html'in GERCEK kart cizicisiyle {id: metin|None} hukum haritasi.
    PAGE_SIZE (24) sinirini asmamak icin parti parti kosulur."""
    node = _node()
    if not node:
        return None, "node bulunamadi"
    runner = _runner_yaz(gecici)
    hepsi = {}
    for i in range(0, len(urunler), 18):
        parti = urunler[i:i + 18]
        fx = os.path.join(gecici, "fikstur-%d.json" % i)
        with open(fx, "w", encoding="utf-8") as f:
            json.dump(parti, f, ensure_ascii=False)
        r = subprocess.run([node, runner, ROOT, "kart", index_yol, fx],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return None, (r.stderr or "").strip()[-500:]
        hepsi.update(json.loads(r.stdout)["hukumler"])
    return hepsi, None


def node_sayfa_nobeti(gecici, html, birim_kurus):
    """Uretilen sayfanin KENDI JS'ini kosar; ustu cizili fiyat gizli mi doner."""
    node = _node()
    if not node:
        return None, "node bulunamadi"
    runner = _runner_yaz(gecici)
    yol = os.path.join(gecici, "urun-sayfasi.html")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(html)
    r = subprocess.run(
        [node, runner, ROOT, "sayfa", yol,
         "null" if birim_kurus is None else str(birim_kurus)],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None, (r.stderr or "").strip()[-500:]
    return json.loads(r.stdout), None


# ------------------------------------------------------------------ (a) KURAL
def bolum_a(mod=build):
    print("\n(a) KURAL — eski_fiyat_gosterim() (fail-closed, %d vaka)" % len(VAKALAR))
    gecen = 0
    for ad, p, beklenen in VAKA_URUNLERI:
        metin, kurus = mod.eski_fiyat_gosterim(p)
        ok = (metin == beklenen)
        if beklenen is None:
            ok = ok and kurus is None
        else:
            ok = ok and isinstance(kurus, int) and kurus > 0
        if ok:
            gecen += 1
        else:
            kontrol(False, "vaka '%s': beklenen %r, gelen %r (kurus=%r)"
                    % (ad, beklenen, metin, kurus))
    kontrol(gecen == len(VAKALAR),
            "%d/%d vaka kuraldan GECTI" % (gecen, len(VAKALAR)))
    gosterilen = sum(1 for _, _, b in VAKA_URUNLERI if b is not None)
    kontrol(gosterilen >= 5 and gosterilen < len(VAKALAR),
            "tablo VAKUM DEGIL: %d vaka gosterir, %d vaka gostermez"
            % (gosterilen, len(VAKALAR) - gosterilen))
    return gecen == len(VAKALAR)


# ------------------------------------------------------------------ (b) PARITE
def bolum_b(gecici, index_yol=None):
    print("\n(b) PARITE — index.html'in GERCEK kart cizicisi ayni hukmu verir mi (drift nobeti)")
    index_yol = index_yol or os.path.join(ROOT, "index.html")
    urunler = [p for _, p, _ in VAKA_URUNLERI]
    hukumler, hata = node_kart_hukumleri(gecici, index_yol, urunler)
    if hukumler is None:
        olculemedi("index.html kart cizicisi kosulamadi: %s" % hata)
        return None
    olculen = 0
    sapan = []
    for ad, p, beklenen in VAKA_URUNLERI:
        if p["id"] not in hukumler:
            continue
        olculen += 1
        if hukumler[p["id"]] != beklenen:
            sapan.append("%s (beklenen %r, kart %r)" % (ad, beklenen, hukumler[p["id"]]))
    kontrol(olculen == len(VAKA_URUNLERI),
            "her vaka icin kart CIZILDI (%d/%d — cizilmeyen vaka VAKUM olurdu)"
            % (olculen, len(VAKA_URUNLERI)))
    kontrol(not sapan, "kart cizici PARITE: sapan %d vaka%s"
            % (len(sapan), (" -> " + "; ".join(sapan)) if sapan else ""))
    enjeksiyon = [k for k in hukumler if k.startswith("__innerHTML__")]
    kontrol(not enjeksiyon,
            "ENJEKSIYON YOK: fiyat alani innerHTML ile YAZILMADI (%d sizinti)"
            % len(enjeksiyon))
    return not sapan and olculen == len(VAKA_URUNLERI)


# ------------------------------------------------------------------ (c) SAYFA
def _urun(**ek):
    p = {"id": "test-eski-fiyat", "kategori": "Otomobil", "marka": ["Audi"],
         "baslik": "Test Ürünü", "aciklama": "Kabul testi.", "fiyat": "850 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/test-1.jpg"]}
    p.update(ek)
    return p


def _konfigur_urunu():
    """Gercek katalogdan bir konfigur'lu urunun KOPYASI (urunler.json'a DOKUNULMAZ)."""
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        for p in json.load(f):
            if p.get("konfigur"):
                return copy.deepcopy(p)
    return None


def bolum_c(mod=build):
    print("\n(c) SAYFA — render_product ciktisi (uctan uca)")
    gecerli = _urun(eski_fiyat="1.200 TL")
    html = mod.render_product(gecerli, [gecerli])
    kontrol('<s class="eski-fiyat"' in html, "gecerli vakada <s class=\"eski-fiyat\"> basilir")
    kontrol('data-kurus="120000"' in html, "data-kurus dogru kurusu tasir (120000)")
    kontrol(">1.200 TL</s>" in html, "ustu cizili metin sayfada gorunur")
    kontrol("text-decoration:line-through" in html,
            "CSS line-through kurali sayfada var")
    kontrol('class="fiyat-satiri"' in html,
            "eski + guncel fiyat AYNI satirda (fiyat-satiri sarmalayicisi)")
    kontrol('id="opsiyonFiyat"' in html,
            "guncel fiyat elemani YERINDE (sarmalayici onu yutmadi)")

    # GECERSIZ -> SIFIR IZ: ciktinin alan HIC YOKKEN uretilenle BAYT-ESIT olmasi
    for ad, gecersiz in (("eski<=guncel", _urun(eski_fiyat="800 TL")),
                         ("cop dize", _urun(eski_fiyat="indirim!")),
                         ("baska para birimi", _urun(eski_fiyat="1200 USD")),
                         ("XSS yuku", _urun(eski_fiyat="1.200 TL<img src=x onerror=alert(1)>"))):
        alansiz = _urun()
        kontrol(mod.render_product(gecersiz, [gecersiz]) ==
                mod.render_product(alansiz, [alansiz]),
                "gecersiz (%s) -> cikti alan-YOK haliyle BAYT-ESIT (sifir iz)" % ad)
    xss = _urun(eski_fiyat="<s onload=alert(1)>1.200 TL</s>")
    xss_html = mod.render_product(xss, [xss])
    kontrol("onload=alert" not in xss_html and "onerror=alert" not in xss_html,
            "XSS yuku sayfaya SIZMAZ")

    # parametrik / konfigur: BILEREK basilmaz (canli degisen fiyat)
    # ⚠️ CAPA `<s class="eski-fiyat"` (etiket) — duz "eski-fiyat" dizgesi PAGE_CSS'te HER
    # sayfada gectigi icin OLU IDDIA olurdu (olculdu: her iki iddia da o yuzden yaniyordu).
    par = _urun(id="test-eski-fiyat-par", kategori="Jeneratör", parametrik=True,
                fiyat="850 TL", eski_fiyat="1.200 TL")
    kontrol('<s class="eski-fiyat"' not in mod.render_product(par, [par]),
            "parametrik (sari) sayfada eski fiyat BASILMAZ")
    konf = _konfigur_urunu()
    if konf is None:
        olculemedi("katalogda konfigur'lu urun yok -> konfigur dali olculemedi")
    else:
        konf["eski_fiyat"] = "9.999 TL"
        kontrol('<s class="eski-fiyat"' not in mod.render_product(konf, [konf]),
                "konfigur'lu sayfada eski fiyat BASILMAZ (fiyat boya gore degisir)")

    # panelsiz (fonksiyonel OLMAYAN) dal da kapsanir
    panelsiz = _urun(id="test-eski-fiyat-panelsiz", kategori="Jeneratör",
                     eski_fiyat="1.200 TL")
    ph = mod.render_product(panelsiz, [panelsiz])
    kontrol('<s class="eski-fiyat"' in ph and '<div class="price"' in ph,
            "panelsiz (statik .price) dalinda da basilir")


# ------------------------------------------------------------------ (d) CANLI NOBET
def bolum_d(gecici, mod=build):
    print("\n(d) CANLI NOBET — sayfanin KENDI JS'i yaniltici indirimi gizler mi")
    p = _urun(eski_fiyat="1.200 TL")
    html = mod.render_product(p, [p])
    beklenen = [("taban fiyat (85.000 kurus < 120.000)", 85000, False),
                ("secim fiyati ASTI (127.500 kurus > 120.000)", 127500, True),
                ("tam esit (120.000 kurus)", 120000, True),
                ("fiyat hesaplanamadi (null)", None, True)]
    for ad, birim, gizli_olmali in beklenen:
        sonuc, hata = node_sayfa_nobeti(gecici, html, birim)
        if sonuc is None:
            olculemedi("sayfa JS'i kosulamadi (%s): %s" % (ad, hata))
            return
        if not sonuc.get("bulundu"):
            kontrol(False, "sayfada #eskiFiyat capasi YOK -> nobet olculemez (%s)" % ad)
            return
        kontrol(sonuc["hidden"] == gizli_olmali,
                "nobet %s -> hidden=%s (beklenen %s)"
                % (ad, sonuc["hidden"], gizli_olmali))


# ------------------------------------------------------------------ (e) PARA EKSENI
REF_YOK, REF_TOTOLOJI, REF_OLCULDU = "yok", "totoloji", "olculdu"


def eski_build_modulu():
    """merge-base'deki tools/build.py'yi ayri modul olarak yukler (konfigur-test.py deseni).
    HEAD referans DEGILDIR: kendisiyle karsilastirma TOTOLOJIdir, sessiz yesil yakar."""
    calisan = open(os.path.join(TOOLS, "build.py"), "rb").read()
    for ref in ("origin/main", "main"):
        mb = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", ref],
                            capture_output=True, text=True)
        if mb.returncode != 0:
            continue
        commit = mb.stdout.strip()
        kaynak = subprocess.run(["git", "-C", ROOT, "show", commit + ":tools/build.py"],
                                capture_output=True)
        if kaynak.returncode != 0:
            continue
        taban = "%s (merge-base HEAD..%s)" % (commit[:12], ref)
        if kaynak.stdout == calisan:
            return None, REF_TOTOLOJI, taban
        g = {"__file__": os.path.join(TOOLS, "build.py"), "__name__": "build_eski"}
        exec(compile(kaynak.stdout.decode("utf-8"), "build_eski", "exec"), g)
        return g, REF_OLCULDU, taban
    return None, REF_YOK, "merge-base/git show alinamadi"


def _kombinasyonlar(urunler):
    """TAM KUME: her konfigur'lu urun x her boy adimi x her malzeme. ORNEKLEME YOK."""
    for p in urunler:
        k = p.get("konfigur")
        if not k:
            continue
        bm = k["boyutMm"]
        adim_sayisi = int(round((bm["max"] - bm["min"]) / bm["adim"])) + 1
        malzemeler = k.get("malzemeler") or [{"ad": "PLA", "katsayi": 1.0}]
        for i in range(adim_sayisi):
            boy = bm["min"] + i * bm["adim"]
            for m in malzemeler:
                yield p, k, boy, float(m.get("katsayi") or 1.0)


def bolum_e():
    print("\n(e) PARA EKSENI — TAM KUME fiyat esitligi (ornekleme YOK)")
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    eski, durum, taban = eski_build_modulu()
    if durum != REF_OLCULDU:
        olculemedi("degisiklik ONCESI build.py alinamadi (%s: %s) -> tam kume "
                   "karsilastirmasi YAPILAMADI" % (durum, taban))
        return
    print("     referans taban: %s" % taban)
    n = 0
    sapan = 0
    toplam_yeni = 0
    toplam_eski = 0
    urun_kumesi = set()
    for p, k, boy, kat in _kombinasyonlar(urunler):
        y = build.konfigur_fiyat_kurus(k, boy, kat)
        e = eski["konfigur_fiyat_kurus"](k, boy, kat)
        n += 1
        toplam_yeni += y
        toplam_eski += e
        urun_kumesi.add(p["id"])
        if y != e:
            sapan += 1
    print("     olculen kombinasyon: %d (%d urun) · toplam kurus yeni=%d eski=%d"
          % (n, len(urun_kumesi), toplam_yeni, toplam_eski))
    kontrol(n > 0, "kombinasyon kumesi BOS DEGIL (%d) — vakum nobeti" % n)
    kontrol(sapan == 0, "TAM KUME kurus esitligi: sapan %d / %d" % (sapan, n))
    kontrol(toplam_yeni == toplam_eski,
            "toplam kurus birebir (%d == %d)" % (toplam_yeni, toplam_eski))

    # Feed / JSON-LD fiyat beyani da degismedi mi (eski_fiyat oralara SIZMAMALI)
    ornek = [p for p in urunler if (p.get("fiyat") or "").strip()][:200]
    feed_sapan = sum(1 for p in ornek
                     if build.feed_price(p["fiyat"]) != eski["feed_price"](p["fiyat"]))
    kontrol(feed_sapan == 0, "feed_price degismedi (%d urunde sapan %d)"
            % (len(ornek), feed_sapan))
    ld = _urun(eski_fiyat="1.200 TL")
    ld_html = build.render_product(ld, [ld])
    ld_bloklar = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                            ld_html, re.S)
    offer = (json.loads(ld_bloklar[0]).get("offers") or {}) if ld_bloklar else {}
    kontrol(offer.get("price") == "850",
            "JSON-LD Offer.price GUNCEL fiyat kalir (%r) — eski_fiyat sizmadi"
            % offer.get("price"))
    kontrol("1200" not in json.dumps(offer) and "1.200" not in json.dumps(offer),
            "JSON-LD Offer'da eski fiyat/priceSpecification UYDURULMADI")
    feed_xml, _ = build.render_merchant_feed([ld])
    kontrol("<g:price>850 TRY</g:price>" in feed_xml,
            "Merchant feed fiyati GUNCEL fiyat kalir")


# ------------------------------------------------------------------ (f) OZET / KART
def bolum_f(mod=build):
    print("\n(f) OZET / EDGE KARTI")
    gecerli = _urun(eski_fiyat="1.200 TL")
    kart = mod.kart_ozeti(gecerli)
    kontrol(kart.get("eski_fiyat") == "1.200 TL",
            "kart_ozeti gecerli eski fiyati TASIR")
    for ad, p in (("eski<=guncel", _urun(eski_fiyat="800 TL")),
                  ("cop", _urun(eski_fiyat="indirim!")),
                  ("alan yok", _urun())):
        kontrol("eski_fiyat" not in mod.kart_ozeti(p),
                "kart_ozeti %s halinde alani HIC EKLEMEZ" % ad)
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    tasiyan = sum(1 for p in urunler if "eski_fiyat" in p)
    kontrol(tasiyan == 0,
            "bugunku katalogda eski_fiyat tasiyan kayit %d (bu dal VERI YAZMAZ)" % tasiyan)
    eski, durum, _ = eski_build_modulu()
    if durum != REF_OLCULDU:
        olculemedi("ozet.json bayt-esitligi: referans build.py yok")
    else:
        kontrol(build.render_ozet(urunler) == eski["render_ozet"](urunler),
                "ozet.json bugunku katalogda BAYT-ESIT (geriye donuk uyumlu)")


# ------------------------------------------------------------------ (g) SEMA KAPILARI
def bolum_g():
    print("\n(g) SEMA / KAPI KAYITLARI")
    import importlib.util
    for ad, dosya, sabit in (("duzelt.py DEGISTIRILEBILIR", "duzelt.py", "DEGISTIRILEBILIR"),
                             ("diriltme-kapisi.py KAPSAM_ALANLARI", "diriltme-kapisi.py",
                              "KAPSAM_ALANLARI")):
        yol = os.path.join(TOOLS, dosya)
        kaynak = open(yol, encoding="utf-8").read()
        # Sabitin DEGERINI kosmadan (yan etkisiz) okumak icin AST kullanilir.
        import ast
        agac = ast.parse(kaynak)
        deger = None
        for dugum in agac.body:
            if isinstance(dugum, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == sabit for t in dugum.targets):
                deger = ast.literal_eval(dugum.value)
        kontrol(deger is not None and "eski_fiyat" in deger,
                "%s icinde eski_fiyat MESRU alan olarak kayitli" % ad)
        kontrol(deger is not None and "fiyat" in deger,
                "%s hala fiyat'i da kapsiyor (kapsam daralmadi)" % ad)
    del importlib


# ------------------------------------------------------------------ MUTASYON
# Her mutant: (ad, hedef, [(aranan, konan), ...]). Birden cok cift = BILESIK mutant;
# gerekcesi ilgili girisin yanindadir (tek basina ESDEGER kalan mutasyonlar bilesik
# olarak olculur — "esdeger mutant" sessizce listeden dusurulmez).
MUTANTLAR = [
    ("M1 eski<=guncel kontrolu kalkti", "build",
     [("    if eski_kurus <= guncel_kurus:\n        return (None, None)",
       "    if False:\n        return (None, None)")]),
    ("M2 parametrik muafiyeti kalkti", "build",
     [('if p.get("parametrik") or p.get("konfigur"):', 'if p.get("konfigur"):')]),
    ("M3 konfigur muafiyeti kalkti", "build",
     [('if p.get("parametrik") or p.get("konfigur"):', 'if p.get("parametrik"):')]),
    ("M4 tam kalip gevsedi (bastan sona esleme yok)", "build",
     [("    m = _ESKI_FIYAT_TAM_RE.match(ham)", "    m = _FIYAT_ARA_RE.search(ham)")]),
    ("M5 guncel fiyat ayristirilamayinca fail-open", "build",
     [("    if guncel_kurus is None:\n        return (None, None)",
       "    if guncel_kurus is None:\n        guncel_kurus = 0")]),
    # BILESIK (olculdu): esc() TEK BASINA kaldirilinca cikti DEGISMEZ — cunku TAM kalip
    # zaten yalniz rakam/nokta/virgul/bosluk/para birimi gecirir (esdeger mutant). Kacisin
    # TASIYICI oldugu tek dunya "kalip gevsemis" dunyadir; ikisi birlikte kaldirilinca
    # <img onerror=...> yuku sayfaya BASILIR ve nobet KIRMIZI yanar.
    ("M6 kalip gevsedi + HTML kacisi kalkti (bilesik)", "build",
     [("    m = _ESKI_FIYAT_TAM_RE.match(ham)", "    m = _FIYAT_ARA_RE.search(ham)"),
      ("% (kurus, esc(metin)))", "% (kurus, metin))")]),
    ("M7 canli nobet kalkti (yaniltici indirim gizlenmez)", "build",
     [("      eskiEl.hidden = !(_eskiKurus > 0 && ozet.birimKurus != null\n"
       "                        && _eskiKurus > ozet.birimKurus);",
       "      eskiEl.hidden = false;")]),
    # Sayi kalibi gevserse "9.99 TL" -> 999 TL okunur ve 850 TL'nin ustune cikar:
    # UYDURMA indirim. (Tip kontrolunun tek basina kaldirilmasi ESDEGERdir — str(1200)
    # da kalibi gecemez — o yuzden mutant sayi kalibina konumlandirildi.)
    ("M8 sayi kalibi gevsedi (belirsiz nokta 9.99 -> 999 TL)", "build",
     [(r'_PARA_SAYI_RE = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?"',
       r'_PARA_SAYI_RE = r"\d[\d.]*(?:,\d{1,2})?"')]),
    ("M9 kart_ozeti kosulu kalkti (ham deger karta)", "build",
     [('    eski_metin, _ = eski_fiyat_gosterim(p)\n    if eski_metin:\n'
       '        kart["eski_fiyat"] = eski_metin',
       '    if p.get("eski_fiyat"):\n        kart["eski_fiyat"] = p["eski_fiyat"]')]),
    ("M10 index.html eski<=guncel kontrolu kalkti", "index",
     [("    if(!(paraKurus(me[1]) > paraKurus(mg[1]))){ return null; }",
       "    if(false){ return null; }")]),
    ("M11 index.html parametrik/konfigur muafiyeti kalkti", "index",
     [("    if(!p || p.parametrik || p.konfigur){ return null; }", "    if(!p){ return null; }")]),
    ("M12 index.html kalibi capalari kalkti (cop/XSS gecer)", "index",
     [(r'var ESKI_FIYAT_TAM_RE = /^\s*((?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?)\s*(?:TL|TRY|₺)\s*$/i;',
       r'var ESKI_FIYAT_TAM_RE = /((?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?)\s*(?:TL|TRY|₺)/i;')]),
    ("M13 index.html sayi kalibi gevsedi (9.99 -> 999 TL)", "index",
     [(r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?)\s*(?:TL|TRY|₺)\s*$/i;",
       r"\d[\d.]*(?:,\d{1,2})?)\s*(?:TL|TRY|₺)\s*$/i;")]),
]


class _Mod(object):
    """exec'lenmis kaynak icin nokta erisimli sarmalayici."""

    def __init__(self, g):
        self._g = g

    def __getattr__(self, ad):
        return self._g[ad]


def _uygula(ham, ciftler):
    """Her (aranan, konan) cifti TEKIL olmali; degilse None (capa cakti -> OLCULEMEDI)."""
    for eski, _ in ciftler:
        if ham.count(eski) != 1:
            return None
    for eski, yeni in ciftler:
        ham = ham.replace(eski, yeni)
    return ham


def _mutant_build(kaynak):
    g = {"__file__": os.path.join(TOOLS, "build.py"), "__name__": "build_mutant"}
    exec(compile(kaynak, "build_mutant", "exec"), g)
    return _Mod(g)


def mutasyon(gecici):
    print("\n=== MUTASYON — her mutant KIRMIZI yanmali ===")
    build_ham = open(os.path.join(TOOLS, "build.py"), encoding="utf-8").read()
    index_ham = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    kirmizi = 0
    for ad, hedef, ciftler in MUTANTLAR:
        ham = build_ham if hedef == "build" else index_ham
        mutant_kaynak = _uygula(ham, ciftler)
        if mutant_kaynak is None:
            print("  ⚪ %s -> capa bulunamadi/tekil degil — OLCULEMEDI" % ad)
            OLCULEMEDI.append("mutant capasi: " + ad)
            continue
        n0 = len(HATALAR)
        if hedef == "build":
            mod = _mutant_build(mutant_kaynak)
            try:
                bolum_a(mod)
                bolum_c(mod)
                bolum_f(mod)
                bolum_d(gecici, mod)
            except Exception as e:                      # coken mutant da KIRMIZIdir
                HATALAR.append("%s -> istisna: %s" % (ad, e))
        else:
            mutant_yol = os.path.join(gecici, "mutant-index.html")
            with open(mutant_yol, "w", encoding="utf-8") as f:
                f.write(mutant_kaynak)
            bolum_b(gecici, mutant_yol)
        yeni_hata = len(HATALAR) - n0
        del HATALAR[n0:]                                 # mutant hatalari SAYILMAZ
        if yeni_hata > 0:
            kirmizi += 1
            print("  🔴 %s -> KIRMIZI (%d iddia ihlali)" % (ad, yeni_hata))
        else:
            print("  ❌ %s -> YESIL KALDI (nobet OLU!)" % ad)
            HATALAR.append("mutant yakalanmadi: " + ad)
    print("  MUTASYON SONUCU: %d/%d KIRMIZI" % (kirmizi, len(MUTANTLAR)))
    return kirmizi


# ------------------------------------------------------------------ ana akis
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="mutant turunu da kosar (yavas: her mutant node kosar)")
    a = ap.parse_args()

    print("ESKI FIYAT KABUL TESTI — opsiyonel `eski_fiyat` (ustu cizili indirim)")
    gecici = tempfile.mkdtemp(prefix="eski-fiyat-test-")
    try:
        bolum_a()
        bolum_b(gecici)
        bolum_c()
        bolum_d(gecici)
        bolum_e()
        bolum_f()
        bolum_g()
        if a.mutasyon:
            mutasyon(gecici)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("\n" + "=" * 72)
    if HATALAR:
        print("KIRMIZI — %d iddia ihlali:" % len(HATALAR))
        for h in HATALAR:
            print("  · " + h)
        sys.exit(1)
    if OLCULEMEDI:
        print("OLCULEMEDI — %d eksen:" % len(OLCULEMEDI))
        for o in OLCULEMEDI:
            print("  · " + o)
        sys.exit(2)
    print("YESIL — butun iddialar olculdu ve gecti.")
    sys.exit(0)


if __name__ == "__main__":
    main()
