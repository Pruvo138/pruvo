#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IC SERI IZI KAPISI — gizli seri adi MUSTERIYE GORUNEN yuzeyde GECEMEZ (11 Agu 2026).

    python3 tools/ic-seri-izi-kapisi.py
    python3 tools/ic-seri-izi-kapisi.py --mutasyon     # + kontrol mutantlari

NEDEN VAR: CLAUDE.md kurali — parametrik ("sari") serinin semasi ve arkasindaki uretec IC
bilgidir; seri adi ("Jeneratör") musteriye gorunen yuzeyde GECMEZ. 11 Agu'ya kadar
parametrik urun sayfasi bu adi KATEGORI ROZETINDE, BREADCRUMB'da (metin + link), JSON-LD
`category` ve `BreadcrumbList`inde, "Diğer ... ürünleri" basliginda ve ana sayfa kart
rozetinde YAZIYORDU -> aktif kural ihlali (canlida olculdu: /urun/olcuye-ozel-cerceve/).

🔴 TEKIL YAMA SINIFI KAPATMAZ. Bu yuzden kapi TEK BIR ROZETE degil KURALA bakar:
  * Yasak KUME kanonik kaynaktan turer: tools/build.py GIZLI_SERI_KARARI (NAV_GIZLI'daki
    her gizli seri icin ZORUNLU karar) -> IC_SERI_ETIKET. Elle tutulan ikinci defter YOK;
    yeni gizli seri karara baglanmadan build ZATEN duser.
  * Olculen YUZEY acikca tanimlidir (rozet, breadcrumb, baslik, meta, JSON-LD, ilgili-urun
    basligi, sayfa ici linkler) — kor bir tam-metin grep'i DEGIL.

⚠️ YANLIS-POZITIF EKSENI (bu depoda olculdu): "Jeneratör" ayni zamanda 17 GERCEK jenerator
yedek parcasinin kategorisidir (Honda EU20i, Yamaha EF3000 ...). Orada kelime musterinin
ARADIGI kelimedir ve KALMALIDIR. Ihlal, kelimenin kendisi degil, kelimenin PARAMETRIK
SERININ etiketi olarak gorunmesidir. Kapi bu ayrimi olcer; N7 mutanti (ceviriyi TUM
urunlere uygulamak) KIRMIZI yakar.

OLCULEN BOLUMLER
  (a) KANONIK KUME — yasak kume GIZLI_SERI_KARARI'ndan turuyor, NAV_GIZLI tam kapsanmis.
  (b) IKIZ TANIM   — index.html KATEGORI_ALIAS/KATEGORI_GORUNUR ile build.py IC_SERI_ETIKET
                     BIREBIR; ayrisma fail-closed KIRMIZI.
  (c) POZITIF      — parametrik urun sayfasinin gorunen yuzeylerinde ic ad 0 (uretilen
                     GERCEK sayfa uzerinde, gecici dizinde).
  (d) YANLIS-POZ.  — gercek jenerator yedek parcasinin sayfasinda kelime AYNEN duruyor.
  (e) ANA SAYFA    — index.html'in GERCEK kart cizicisi (node:vm) parametrik kartta gorunen
                     etiketi, gercek jenerator parcasinda ic adi basiyor.
  (f) VERI         — `urunler.json` ve sayfadaki URUN JSON blogu ic adi TASIMAYA DEVAM
                     ediyor (kategori VERI olarak korunur; yalniz GORUNEN metin degisti).
  (g) FAIL-CLOSED KAPSAM — ic-etiketli seride, kapinin olcmedigi bir yuzeyi acacak veri
                     (dolu `marka` -> marka cipi href'i; bos `gorseller` -> yer tutucu
                     SVG'ye kategori adi cizilir) ORTAYA CIKARSA KIRMIZI.

CIKIS: 0 yesil · 1 kirmizi · 2 olculemedi. Depoya YAZMAZ.
"""
import argparse
import html as _html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build          # noqa: E402
import yayin_yuzey    # noqa: E402

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


def _yasak_desenler():
    """Yasak kume KANONIK kaynaktan: build.IC_SERI_ETIKET anahtarlari (ic seri adlari).
    Her ad icin iki bicim taranir: kendisi (buyuk/kucuk harf duyarsiz) ve ASCII'ye
    katlanmis hali (URL/slug/dosya adinda Turkce harf kaybolur: Jeneratör -> Jenerator)."""
    kat = {"ö": "o", "Ö": "O", "ü": "u", "Ü": "U", "ı": "i", "İ": "I",
           "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ç": "c", "Ç": "C"}
    out = []
    for ad in build.IC_SERI_ETIKET:
        bicimler = {ad, "".join(kat.get(c, c) for c in ad)}
        for b in bicimler:
            out.append((ad, re.compile(re.escape(b), re.I)))
    return out


# --------------------------------------------------------- gorunen yuzey ayiklayicisi
def gorunen_yuzeyler(h):
    """Sayfanin MUSTERIYE GORUNEN parcalari. Kor tam-metin taramasi BILEREK yapilmaz:
    ilgili-urun kartlarinin BASLIKLARI gercek urun adlaridir ("Yamaha İnvertör Jeneratör
    İp Çekme Mandalı") ve orada kelime MESRUDUR."""
    y = []
    for m in re.finditer(r'<span class="cat">([^<]*)</span>', h):
        y.append(("kategori rozeti", m.group(1)))
    for m in re.finditer(r'<span class="ozel-badge">([^<]*)</span>', h):
        y.append(("ozel rozet", m.group(1)))
    m = re.search(r'<nav class="crumbs".*?</nav>', h, re.S)
    if m:
        y.append(("breadcrumb", unquote(m.group(0))))
    m = re.search(r"<title>([^<]*)</title>", h)
    if m:
        y.append(("title", m.group(1)))
    for m in re.finditer(r'<meta[^>]+content="([^"]*)"', h):
        y.append(("meta", m.group(1)))
    for m in re.finditer(r'<script type="application/ld\+json">([\s\S]*?)</script>', h):
        y.append(("json-ld", unquote(m.group(1))))
    for m in re.finditer(r'<section class="related"><h2>([^<]*)</h2>', h):
        y.append(("ilgili urun basligi", m.group(1)))
    # Sayfa ici linkler — URUN adresleri HARIC (slug gercek urun adindan turer, mesru).
    for m in re.finditer(r'<a\b[^>]*href="([^"]*)"', h):
        href = m.group(1)
        if "/urun/" in href:
            continue
        y.append(("link", unquote(href)))
    return y


def iz_say(h, desenler):
    bulgular = []
    for ad, metin in gorunen_yuzeyler(h):
        for ic_ad, rx in desenler:
            if rx.search(metin or ""):
                bulgular.append((ad, ic_ad, (metin or "")[:120]))
    return bulgular


# --------------------------------------------------------------------- fikstur render
def sayfalari_uret(gecici, idler, mod=build):
    tum = _urunler()
    ix = {p["id"]: p for p in tum}
    mod.VARLIK_DIR = os.path.join(gecici, "varlik")
    mod._VARLIK_ONBELLEK = {}
    cikti = {}
    for pid in idler:
        p = ix.get(pid)
        if not p:
            return None, "fikstur urunu katalogda YOK: %s" % pid
        havuz = [x for x in tum if x.get("kategori") == p.get("kategori")][:12]
        if p not in havuz:
            havuz = [p] + havuz
        yol = os.path.join(gecici, pid + ".html")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(yayin_yuzey.govde(mod.render_product(p, havuz, None), gecici))
        cikti[pid] = yol
    return cikti, None


def _seri_urunleri():
    """(ic_ad -> {parametrik: [...], digerleri: [...]}) — IC_SERI_ETIKET'li kategoriler."""
    out = {}
    for p in _urunler():
        kat = p.get("kategori") or ""
        if kat not in build.IC_SERI_ETIKET:
            continue
        d = out.setdefault(kat, {"parametrik": [], "digerleri": []})
        d["parametrik" if p.get("parametrik") else "digerleri"].append(p)
    return out


# ------------------------------------------------------------------ (a) KANONIK KUME
def bolum_a():
    print("\n(a) KANONIK KUME — yasak kume GIZLI_SERI_KARARI'ndan turuyor")
    kontrol(bool(build.IC_SERI_ETIKET),
            "ic seri etiketi kumesi BOS DEGIL (%s)" % sorted(build.IC_SERI_ETIKET))
    eksik = [k for k in build.NAV_GIZLI if k not in build.GIZLI_SERI_KARARI]
    kontrol(not eksik, "NAV_GIZLI'nin TAMAMI karara baglanmis (eksik: %s)" % eksik)
    kontrol(set(build.IC_SERI_ETIKET) <= set(build.NAV_GIZLI),
            "ic etiketli her ad NAV_GIZLI icinde (kume kanonik kaynaktan turuyor)")
    kontrol(all(v and v not in build.IC_SERI_ETIKET
                for v in build.IC_SERI_ETIKET.values()),
            "gorunur etiketlerin kendisi ic ad DEGIL (donusum sabit noktaya dusmuyor)")


# ------------------------------------------------------------------ (b) IKIZ TANIM
def bolum_b(kok=None):
    print("\n(b) IKIZ TANIM — index.html ile build.py esleme BIREBIR")
    kok = kok or ROOT
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        ix = f.read()

    def _sozluk(ad):
        m = re.search(r"var\s+" + ad + r"\s*=\s*(\{[^;]*\});", ix)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except ValueError:
            return None

    alias = _sozluk("KATEGORI_ALIAS")
    gorunur = _sozluk("KATEGORI_GORUNUR")
    kontrol(alias is not None and gorunur is not None,
            "index.html KATEGORI_ALIAS + KATEGORI_GORUNUR bulundu ve ayristirildi")
    if alias is None or gorunur is None:
        return
    kontrol(gorunur == build.IC_SERI_ETIKET,
            "KATEGORI_GORUNUR == build.IC_SERI_ETIKET (olculen: %s / %s)"
            % (gorunur, build.IC_SERI_ETIKET))
    kontrol(alias == {v: k for k, v in build.IC_SERI_ETIKET.items()},
            "KATEGORI_ALIAS, esleme TERSI (gorunen etiket -> ic ad) (olculen: %s)" % alias)


# ------------------------------------------------------------------ (c)+(d) SAYFALAR
def bolum_cd(gecici):
    print("\n(c)+(d) SAYFA YUZEYLERI — parametrikte iz 0, gercek urunde kelime KALIR")
    desenler = _yasak_desenler()
    seriler = _seri_urunleri()
    sonuc = {"pozitif": 0, "yanlis_poz": 0}
    for ic_ad, gruplar in seriler.items():
        par = gruplar["parametrik"]
        dig = gruplar["digerleri"]
        if not par:
            olculemedi("%s: parametrik fikstur yok" % ic_ad)
            continue
        idler = [par[0]["id"]] + ([dig[0]["id"]] if dig else [])
        sayfalar, hata = sayfalari_uret(gecici, idler)
        if sayfalar is None:
            olculemedi(hata)
            continue
        h = open(sayfalar[par[0]["id"]], encoding="utf-8").read()
        bulgu = iz_say(h, desenler)
        sonuc["pozitif"] = len(bulgu)
        kontrol(not bulgu,
                "%s: PARAMETRIK sayfada (%s) gorunen yuzeylerde ic ad izi = %d%s"
                % (ic_ad, par[0]["id"], len(bulgu),
                   ("  -> " + "; ".join("%s:%r" % (a, m) for a, _i, m in bulgu[:4])
                    if bulgu else "")))
        # Gorunur etiket GERCEKTEN basilmis mi (yerine bos/eksik metin gecmesin)
        kontrol(build.IC_SERI_ETIKET[ic_ad] in h,
                "%s: gorunur etiket (%r) sayfada BASILI"
                % (ic_ad, build.IC_SERI_ETIKET[ic_ad]))
        if dig:
            h2 = open(sayfalar[dig[0]["id"]], encoding="utf-8").read()
            b2 = iz_say(h2, desenler)
            sonuc["yanlis_poz"] = len(b2)
            kontrol(len(b2) > 0,
                    "%s: YANLIS-POZITIF EKSENI — gercek urun sayfasinda (%s) kelime "
                    "AYNEN duruyor (%d yuzey); kapi bunu ihlal SAYMAZ"
                    % (ic_ad, dig[0]["id"], len(b2)))
            m = re.search(r'<span class="cat">([^<]*)</span>', h2)
            kontrol(bool(m) and m.group(1) == ic_ad,
                    "%s: gercek urunun kategori rozeti DEGISMEDI (%r)"
                    % (ic_ad, m.group(1) if m else None))
        else:
            olculemedi("%s: parametrik OLMAYAN karsilastirma urunu yok" % ic_ad)
        # (f) VERI DOKUNULMAZ
        kontrol('"kategori":"%s"' % ic_ad in h.replace(", ", ",").replace('": "', '":"'),
                "%s: sayfadaki URUN JSON blogu IC adi tasimaya devam ediyor (veri korundu)"
                % ic_ad)
    return sonuc


# ------------------------------------------------------------------ (e) ANA SAYFA
KART_RUNNER = r"""
"use strict";
/* index.html'in GERCEK kart cizicisi node:vm'de kosar (kod KOPYALANMAZ). */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const KOK = process.argv[2];
const urunler = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const { inlineScriptBul } = require(path.join(KOK, "tools", "html-blok-ayikla.js"));
const html = fs.readFileSync(path.join(KOK, "index.html"), "utf8");
const src = inlineScriptBul(html, "kartCiz");
if (!src) { throw new Error("index.html inline scripti (imza 'kartCiz') bulunamadi"); }
const CAPA = "var EDGE_KATALOG = true;";
if (src.indexOf(CAPA) === -1) { throw new Error("EDGE_KATALOG capasi bulunamadi"); }
const kaynak = src.replace(CAPA, "var EDGE_KATALOG = false;");
const TUM = [];
function eleman(tag) {
  const el = { tagName: String(tag || "div").toUpperCase(), children: [], parentNode: null,
    style: {}, dataset: {}, attrs: {}, className: "", textContent: "", id: "", value: "",
    href: "", hidden: false, disabled: false, checked: false, onclick: null, onerror: null,
    offsetWidth: 0 };
  let inner = "";
  Object.defineProperty(el, "innerHTML", {
    get() { return inner; }, set(v) { inner = String(v); el.children.length = 0; } });
  el.classList = {
    add(c) { if (!this.contains(c)) { el.className = (el.className + " " + c).trim(); } },
    remove(c) { el.className = el.className.split(/\s+/).filter((x) => x !== c).join(" "); },
    contains(c) { return el.className.split(/\s+/).indexOf(c) !== -1; },
    toggle(c, v) { const on = (v === undefined) ? !this.contains(c) : !!v;
      if (on) { this.add(c); } else { this.remove(c); } } };
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
  const kim = new Map(), sec = new Map();
  return {
    getElementById(id) {
      if (!kim.has(id)) { const e = eleman("div"); e.id = id; kim.set(id, e); }
      return kim.get(id);
    },
    createElement: (t) => eleman(t),
    createTextNode: (t) => { const e = eleman("#text"); e.textContent = String(t); return e; },
    querySelector(s) { if (!sec.has(s)) { sec.set(s, eleman("div")); } return sec.get(s); },
    querySelectorAll: () => [],
    body: eleman("body"), documentElement: eleman("html"), head: eleman("head"),
    addEventListener() {}, removeEventListener() {}, execCommand: () => true,
    readyState: "complete", cookie: "",
  };
}
const ctx = {
  document: belgeKur(),
  location: { hash: "", search: "", pathname: "/", href: "https://pruvo3d.com/", replace() {} },
  history: { replaceState() {} },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  fetch: (url) => {
    const ham = String(url);
    if (ham.indexOf("urunler.json") !== -1) {
      return Promise.resolve({ ok: true, status: 200,
        json: () => Promise.resolve(JSON.parse(JSON.stringify(urunler))) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
  },
  console: { log() {}, warn() {}, error() {}, info() {}, debug() {} },
  alert() {}, confirm: () => true, navigator: { userAgent: "node" },
  URLSearchParams, URL, setTimeout, clearTimeout, setInterval, clearInterval,
  Math, JSON, Date, encodeURIComponent, decodeURIComponent, Promise,
  addEventListener() {}, removeEventListener() {}, scrollTo() {}, scrollY: 0,
  innerHeight: 800, innerWidth: 1280,
  requestAnimationFrame(f) { return setTimeout(f, 0); },
  matchMedia: () => ({ matches: false, addListener() {}, addEventListener() {} }),
};
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), ctx,
                { filename: "secenekler.js" });
vm.runInContext(kaynak, ctx, { filename: "index-inline.js" });
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  for (let i = 0; i < 40; i++) { await bekle(5); }
  /* Kart -> {urun id: gorunen kategori rozeti} */
  const hukum = {};
  for (const el of TUM) {
    if (!/(^|\s)card-cat(\s|$)/.test(el.className || "")) { continue; }
    let ust = el.parentNode, pid = null;
    while (ust) {
      if (ust.href && ust.href.indexOf("/urun/") === 0) {
        pid = ust.href.replace(/^\/urun\/|\/$/g, ""); break;
      }
      ust = ust.parentNode;
    }
    if (pid) { hukum[pid] = el.textContent; }
  }
  process.stdout.write(JSON.stringify({ hukum }));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(3); });
"""


def bolum_e(gecici, kok=None):
    print("\n(e) ANA SAYFA — index.html'in GERCEK kart cizicisi (node:vm)")
    kok = kok or ROOT
    node = shutil.which("node")
    if not node:
        olculemedi("node yok — ana sayfa kart olcumu yapilamadi")
        return
    seriler = _seri_urunleri()
    for ic_ad, gruplar in seriler.items():
        par = gruplar["parametrik"]
        dig = gruplar["digerleri"]
        if not par:
            continue
        fx = [par[0]] + ([dig[0]] if dig else [])
        fy = os.path.join(gecici, "kart-fikstur.json")
        with open(fy, "w", encoding="utf-8") as f:
            json.dump(fx, f, ensure_ascii=False)
        ry = os.path.join(gecici, "kart-kosucu.js")
        with open(ry, "w", encoding="utf-8") as f:
            f.write(KART_RUNNER)
        r = subprocess.run([node, ry, kok, fy], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            olculemedi("kart kosucusu dustu: %s" % (r.stderr or "")[-500:])
            return
        hukum = json.loads(r.stdout).get("hukum", {})
        kontrol(hukum.get(par[0]["id"]) == build.IC_SERI_ETIKET[ic_ad],
                "%s: ana sayfa kartinda PARAMETRIK urunun rozeti = %r (olculen: %r)"
                % (ic_ad, build.IC_SERI_ETIKET[ic_ad], hukum.get(par[0]["id"])))
        if dig:
            kontrol(hukum.get(dig[0]["id"]) == ic_ad,
                    "%s: ana sayfa kartinda GERCEK urunun rozeti DEGISMEDI (olculen: %r)"
                    % (ic_ad, hukum.get(dig[0]["id"])))


# ------------------------------------------------------------------ (f)+(g) VERI/KAPSAM
def bolum_fg():
    print("\n(f)+(g) VERI DOKUNULMAZ + FAIL-CLOSED KAPSAM")
    seriler = _seri_urunleri()
    for ic_ad, gruplar in seriler.items():
        par = gruplar["parametrik"]
        kontrol(all((p.get("kategori") or "") == ic_ad for p in par),
                "%s: urunler.json'da kategori VERISI ic adi tasimaya devam ediyor (%d urun)"
                % (ic_ad, len(par)))
        markali = [p["id"] for p in par if p.get("marka")]
        kontrol(not markali,
                "%s: ic-etiketli seride MARKA tasiyan urun YOK — marka cipi href'i (kapinin "
                "olcmedigi tek kalan kategori-linki) ic adla dogamaz (bulunan: %s)"
                % (ic_ad, markali[:3]))
        gorselsiz = [p["id"] for p in par if not (p.get("gorseller") or [])]
        kontrol(not gorselsiz,
                "%s: ic-etiketli seride GORSELSIZ urun YOK — yer tutucu SVG'ye kategori adi "
                "cizilme yolu acilmadi (bulunan: %s)" % (ic_ad, gorselsiz[:3]))


# ------------------------------------------------------------------ mutasyon
MUTANTLAR = [
    ("N1", "gorunur_kategori KIMLIK yapildi (donusum sokuldu)", "tools/build.py",
     '    if p.get("parametrik") and kat in IC_SERI_ETIKET:', '    if False:', 1),
    ("N2", "JSON-LD category HAM kategoriye dondu", "tools/build.py",
     '        "category": (gorunur_kat + " > " + altkategori) if altkategori else gorunur_kat,',
     '        "category": (kategori + " > " + altkategori) if altkategori else kategori,', 1),
    ("N3", "breadcrumb/rozet HAM kategoriye dondu", "tools/build.py",
     "        katq=esc(kategori_url(gorunur_kat)),\n        kategori=esc(gorunur_kat),",
     "        katq=esc(kategori_url(kategori)),\n        kategori=esc(kategori),", 1),
    ("N4", "ana sayfa kart rozeti HAM kategoriye dondu", "index.html",
     "    cat.textContent = gorunurUrunKategorisi(p);",
     "    cat.textContent = p.kategori;", 1),
    ("N5", "IKIZ AYRISMASI: index.html esleme degeri kaydi", "index.html",
     'var KATEGORI_GORUNUR = {"Jeneratör":"Ölçüye Özel Üretim"};',
     'var KATEGORI_GORUNUR = {"Jeneratör":"Ölçüye Özel"};', 1),
    ("N7", "YANLIS-POZITIF EKSENI: ceviri TUM urunlere uygulandi (gercek urun de kaybetti)",
     "tools/build.py",
     '    if p.get("parametrik") and kat in IC_SERI_ETIKET:',
     '    if kat in IC_SERI_ETIKET:', 1),
    ("N6", "KONTROL: davranisi degistirmeyen yeniden adlandirma", "tools/build.py",
     "    gorunur_kat = gorunur_kategori(p)", "    gorunur_etiket = gorunur_kategori(p)", 0),
]
N6_EK = [
    ('        "category": (gorunur_kat + " > " + altkategori) if altkategori else gorunur_kat,',
     '        "category": (gorunur_etiket + " > " + altkategori) '
     'if altkategori else gorunur_etiket,'),
    ('            {"@type": "ListItem", "position": 2, "name": gorunur_kat,\n'
     '             "item": SITE + kategori_url(gorunur_kat)},',
     '            {"@type": "ListItem", "position": 2, "name": gorunur_etiket,\n'
     '             "item": SITE + kategori_url(gorunur_etiket)},'),
    ('    kapsam = ("kategori=" + _urlq(gorunur_kat, safe="") + "&") if gorunur_kat else ""',
     '    kapsam = ("kategori=" + _urlq(gorunur_etiket, safe="") + "&") '
     'if gorunur_etiket else ""'),
    ("    cover = paylasim_gorseli or placeholder_data_uri(gorunur_kat)",
     "    cover = paylasim_gorseli or placeholder_data_uri(gorunur_etiket)"),
    ("    rel_baslik = gorunur_kat", "    rel_baslik = gorunur_etiket"),
    ("        katq=esc(kategori_url(gorunur_kat)),\n        kategori=esc(gorunur_kat),",
     "        katq=esc(kategori_url(gorunur_etiket)),\n"
     "        kategori=esc(gorunur_etiket),"),
]
MUTASYON_KOK_DOSYALARI = ("index.html", "secenekler.js", "konfigur.js")


def _gecici_kok():
    tmp = tempfile.mkdtemp(prefix="ic-seri-mut-")
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
    print("MUTASYON NOBETI — kapi OLU mu? (alti kirmizi + bir KONTROL yesil)")
    sapan = []
    print("\n%-4s %-60s %-9s %-9s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
    for kod, aciklama, dosya, eski, yeni, beklenen in MUTANTLAR:
        ciftler = [(eski, yeni)] + (N6_EK if kod == "N6" else [])
        tmp = _gecici_kok()
        try:
            ok, capa = _uygula(os.path.join(tmp, *dosya.split("/")), ciftler)
            if not ok:
                sapan.append("%s: capa uygulanamadi (%r)" % (kod, capa))
                print("%-4s %-60s %-9s %-9s CAPA YOK" % (kod, aciklama[:60], beklenen, "-"))
                continue
            r = subprocess.run(
                [sys.executable, os.path.join(tmp, "tools", os.path.basename(__file__))],
                capture_output=True, text=True, cwd=tmp)
            rc = r.returncode
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        tamam = (rc == beklenen)
        if not tamam:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d" % (kod, beklenen, rc))
        print("%-4s %-60s %-9s %-9s %s"
              % (kod, aciklama[:60], "KIRMIZI" if beklenen else "YESIL", renk,
                 "OK" if tamam else "SAPTI"))
    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: %d mutantin hepsi beklenen rengi verdi (N6 kontrol mutanti YESIL)."
          % len(MUTANTLAR))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args()

    print("IC SERI IZI KAPISI — gizli seri adi musteriye gorunen yuzeyde GECEMEZ")
    gecici = tempfile.mkdtemp(prefix="ic-seri-")
    try:
        bolum_a()
        bolum_b()
        bolum_cd(gecici)
        bolum_e(gecici)
        bolum_fg()
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
    print("SONUC: YESIL ✅ — ic seri adi musteriye gorunen yuzeyde YOK")

    if a.mutasyon:
        return mutasyon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
