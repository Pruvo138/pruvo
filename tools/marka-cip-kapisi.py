#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA SAYFASI MODEL ÇİPİ KAPISI — hedef · sayı · gürültü · TIKLAMA DAVRANIŞI.

🔴 NEDEN VAR (12 Ağu 2026, Okan canlıdan): "/marka/… sayfalarında modeller eksik, çipler
dağınık, çipteki sayı ürünle tutmuyor, çipe tıklanınca hedef açılmıyor." Dördü de SESSİZ:
sayfa "çalışıyor" görünüyor, HTTP 200 dönüyor, hiçbir kapı kırmızı yanmıyordu.

ÖLÇÜLDÜ (canlı, GERÇEK TARAYICI, cache-bust'SIZ — `curl` bu ekseni ÖLÇEMEZ, çünkü çip
AYRI ADRESE GİTMEZ, sayfa İÇİNDE filtreler):
  · 1024 çipin 1024'ü HTTP 200 (kalıcı kırık link 0) — yani HTTP ekseni TEMİZDİ,
  · ama çipe basılınca ekranda 0 KART kalıyordu: Kia/Sportage 1,9 sn · Hyundai/Ioniq 5
    ~1-3 sn · Hyundai/Palisade >6,5 sn. Sebep: SSR'de basılı kartlar sayfanın YEREL
    kalemleridir, model üyeliği TAŞIMAZLAR; çip hepsini gizliyor ve yük gelene kadar
    ekran BOŞ kalıyor.
  · O pencerede durum metni ya BOŞTU ya da BİR ÖNCEKİ çipin sayısını gösteriyordu
    (seçili çip "Palisade 7 parça" iken ekranda "54 parça (model filtresi etkin)").
    Kullanıcının gördüğü şey tam olarak "çipe tıklanınca hedef açılmıyor"dur.

KAPI NEYİ ÖLÇER (ÖRNEKLEME YOK — üretilen TÜM marka sayfaları, TÜM çipler):
  HEDEF/cozuldu   : her çipin `href` hedefi üretilen ağaçta GERÇEKTEN var (çip basıldıysa
                    sayfası da doğmuş olmalı; "çipi bas, 404 olsun" kabul değil).
  HEDEF/dolu      : hedef sayfa BOŞ değil (HTTP 200 + boş liste de BOZUKTUR).
  SAYI/filtre     : çipin BASTIĞI sayı == sayfanın KENDİ yükünde (`parcalar.json`) o model
                    indeksine düşen kalem sayısı (kullanıcının filtrede göreceği küme).
  SAYI/sayfa      : çipin BASTIĞI sayı == hedef model sayfasının BEYAN ettiği toplam.
  GURULTU/yabanci : çip etiketi KENDİ BAŞINA bir marka (katalogda ham `marka[0]` olarak
                    >= ESIK üründe geçiyor) VE kovanın ürünlerinin ÇOĞUNLUĞUNUN ham
                    `marka[0]`'ı o ETİKET ise, kova bu markanın MODELİ DEĞİLDİR.
                    🔴 SINIF KURALI, KARA LİSTE DEĞİL: marka adı yazılmaz, katalogdan ölçülür.
  GURULTU/kontrol : sınıf kuralı SENTETİK pozitifte GERÇEKTEN ateşler (dejenere ölçüm değil).
  TIKLAMA/*       : sayfanın KENDİ gömülü filtre modülü node'da SAHTE DOM ile koşturulur ve
                    tıklama davranışı ölçülür — "kapı yeşil, demek ki çalışıyor" YASAK.
    TIKLAMA/aninda: tıklamadan SONRA, yük GELMEDEN durum metni BOŞ KALMAZ ve o çipin
                    KENDİ bastığı sayıyı taşır.
    TIKLAMA/bayat : ikinci çipe basılınca ekranda bir önceki çipin sayısı KALMAZ.
    TIKLAMA/onyuk : işaretçi çipe DOKUNUNCA (tıklamadan önce) yük istenmeye başlar.
    TIKLAMA/sonuc : yük gelince görünen kart sayısı == çipin bastığı sayı.
    TIKLAMA/kontrol: aynı koşum, filtre HİÇ uygulanmazsa BAŞKA sonuç verir (dejenere değil).

Kullanım:
  python3 tools/marka-cip-kapisi.py          # kapı (rc=0 yeşil · rc=1 kırmızı · rc=3 ÖLÇÜLEMEDİ)
  python3 tools/marka-cip-kapisi.py --iz     # yalnız kaynak izi (mutasyon kanıtı)
FAIL-CLOSED: ölçüm kurulamazsa rc=3; sessiz yeşil YASAK.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
CIP_RE = re.compile(
    r'<a class="mm-model-btn" href="([^"]+)" data-katsay="[^"]*" data-mm="(\d+)">'
    r'(.*?)<span class="adet">(\d+) parça</span></a>')
TOPLAM_RE = re.compile(r'<span class="mm-sayim-toplam">(\d+)</span>')
KART_RE = re.compile(r'<div class="card" data-kat="[^"]*"[^>]*><a class="card-main" href="')
BAG_RE = re.compile(r'<li class="mm-kalan-oge" data-kat="[^"]*"><a href="')
ARTIM_BAS = "/* PRUVO ARTIM BAS */"
ARTIM_SON = "/* PRUVO ARTIM SON */"


class Olculemedi(Exception):
    """Ölçüm KURULAMADI — yeşil sayılmaz (rc=3)."""


class Kapi(object):
    """İddia defteri. İNSANA BASILAN ÖZET, HÜKMÜ BESLEYEN KÜMEDEN türer — ikinci sayım
    noktası AÇILMAZ (bu depoda ölçülmüş hata sınıfı: kapı KIRMIZI iken özet 'sapan 0')."""

    def __init__(self):
        self.dusen = []      # (aile, ayrinti)
        self.kosan = 0

    def iddia(self, aile, dogru_mu, ayrinti=""):
        self.kosan += 1
        if not dogru_mu:
            self.dusen.append((aile, ayrinti))
        return bool(dogru_mu)

    @property
    def aileler(self):
        return sorted(set(a for a, _d in self.dusen))

    @property
    def yesil(self):
        return not self.dusen


def kaynak_izi():
    """Mutasyonun UYGULANDIĞINI kanıtlayan iz (aynı uzunlukta mutant + bytecode önbelleği
    tuzağı: mutant koşumu bu izi BASAR; iz değişmemişse o tur SAYILMAZ)."""
    h = hashlib.sha1()
    for ad in ("marka_model_build.py",):
        with open(os.path.join(TOOLS, ad), "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def sayfalari_uret(tmp):
    try:
        import build                      # noqa: PLC0415
        import marka_model_build as mm    # noqa: PLC0415
        with open(os.path.join(build.ROOT, "urunler.json"), encoding="utf-8") as f:
            products = json.load(f)
        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        shutil.copy(os.path.join(build.ROOT, "index.html"),
                    os.path.join(tmp, "index.html"))
        with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
        mm.uret(products, ctx)
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("marka/model sayfaları üretilemedi: %r" % (e,))
    return products, mm, index_html


def agaci_tara(tmp):
    """Üretilen ağaçtaki HER sayfa: çipler + beyan + kalem yüzeyi."""
    sayfalar = {}
    kok = os.path.join(tmp, "marka")
    if not os.path.isdir(kok):
        raise Olculemedi("/marka ağacı üretilmedi")
    for dirpath, _dn, filenames in os.walk(kok):
        if "index.html" not in filenames:
            continue
        rel = os.path.relpath(dirpath, tmp).replace(os.sep, "/")
        with open(os.path.join(dirpath, "index.html"), encoding="utf-8") as f:
            ham = f.read()
        page = SCRIPT_RE.sub("", ham)
        t = TOPLAM_RE.search(page)
        yuk = None
        yyol = os.path.join(dirpath, "parcalar.json")
        if os.path.exists(yyol):
            try:
                with open(yyol, encoding="utf-8") as f:
                    yuk = json.load(f)
            except Exception:                                     # noqa: BLE001
                yuk = "BOZUK"
        sayfalar[rel] = {
            "cipler": [(h, int(ix), int(n)) for h, ix, _e, n in CIP_RE.findall(ham)],
            "toplam": int(t.group(1)) if t else None,
            "kart": len(KART_RE.findall(page)),
            "bag": len(BAG_RE.findall(page)),
            "yuk": yuk,
            "ham": ham,
        }
    return sayfalar


def yabanci_marka_sinifi(products, mm, index_html):
    """GÜRÜLTÜ SINIFI — 'çip etiketi aslında AYRI BİR MARKA'.

    İki şart BİRDEN (kara liste YOK, ikisi de katalogdan ölçülür):
      (1) etiket katalogda ham `marka[0]` olarak >= ESIK üründe geçiyor (yani bir MARKADIR),
      (2) kovanın ürünlerinin ÇOĞUNLUĞUNUN ham `marka[0]`'ı o etiket, sayfanın markası DEĞİL.
    Dönüş: {(marka_slug, model_slug)} ihlal kümesi + sınıfın ateşleyebilirliği (kontrol)."""
    ham0 = {}
    ham0_sayaci = Counter()
    for p in products:
        pid, m = p.get("id"), (p.get("marka") or [])
        if pid and m:
            ham0[pid] = mm._canon(m[0])
            ham0_sayaci[mm._canon(m[0])] += 1
    evren = mm.MarkaEvreni(index_html)
    ek = mm.cip_evreni_markalari(products, index_html)
    veri = mm.gruplandir(products, evren, ek)
    ihlal, olculen = {}, 0
    for marka, d in veri.items():
        if mm.marka_urun_sayisi(d) < mm.ESIK:
            continue
        mslug = mm._slug(marka)
        for g in d["gruplar"].values():
            if not mm.yayimlanir_mi(g):
                continue
            olculen += 1
            etiket = mm._canon(g["display"])
            if etiket == mm._canon(marka):
                continue
            if ham0_sayaci.get(etiket, 0) < mm.ESIK:
                continue
            ids = [p.get("id") for p in g["urunler"] if p.get("id")]
            if not ids:
                continue
            say = Counter(ham0.get(i) for i in ids)
            if say.get(etiket, 0) * 2 > len(ids) \
                    and say.get(mm._canon(marka), 0) * 2 <= len(ids):
                ihlal[("marka/%s" % mslug, g["slug"])] = (
                    marka, g["display"], len(ids), say.get(etiket, 0))
    return ihlal, olculen, ham0_sayaci


def envanter_drifti(products, mm, index_html):
    """ELLE TUTULAN ENVANTERİN (`arama.BASLIK_DOGAN_ALLOW`) BAYATLADIĞINI ÖLÇER.

    🔴 NEDEN VAR (12 Ağu, KraL şartı): envanter kolu (a) DURUYOR. Duran her elle liste bu
    depoda bayatlar — ölçüldü: 80 kova / 588 ürün YALNIZCA "envanterde yok" diye çipsiz ve
    sayfasızdı. Kural kolu (d) o boşluğu kapattı; bu nöbetçi KAPALI KALDIĞINI ölçer.

    İKİ EKSEN, ikisi de katalogdan türer (elle sayı/liste YOK):
      drift    : eşiği+birinciliği geçen, gürültü sınıfında OLMAYAN, jetonunun SAHİBİ bu
                 marka olan bir kova YALNIZCA envanterde yok diye çipsiz kalamaz.
      gereksiz : envanterdeki bir giriş KURAL tarafından zaten yargılanıyorsa ÖLÜ AĞIRLIKTIR
                 ve listeden çıkmalıdır (liste büyüyerek çözülmez — anti-büyüme kilidi).

    Yargı gövdesi KAPININ KENDİSİNİNDİR: `mm.baslik_yargisi_var_mi` ÇAĞRILMAZ (çağrılsaydı
    iddia totoloji olurdu)."""
    import arama                                                   # noqa: PLC0415
    evren = mm.MarkaEvreni(index_html)
    ek = mm.cip_evreni_markalari(products, index_html)
    veri = mm.gruplandir(products, evren, ek)
    # --- kapının KENDİ sahiplik tablosu (üretimin tablosu çağrılmaz) ---
    jeton = {}
    for p in products:
        m = p.get("marka") or []
        if not m:
            continue
        h = mm._canon(m[0])
        adaylar = list(m) + [u.get("model") for u in (p.get("uyum") or [])
                             if isinstance(u, dict) and u.get("model")]
        for t in adaylar:
            k = mm._canon(t or "")
            if not k:
                continue
            d = jeton.setdefault(k, {})
            d[h] = d.get(h, 0) + 1

    def sahip(display):
        say = jeton.get(mm._canon(display or ""))
        if not say:
            return frozenset()
        toplam = sum(say.values())
        return frozenset(k for k, n in say.items()
                         if n * mm.JETON_SAHIP_ESIK_PAYDA >= toplam)

    izin = set((mk, mm.model_kanon.kanon(jt)) for mk, jt in arama.BASLIK_DOGAN_ALLOW)
    # (d) kolu çapraz-marka çarpışmasında SUSAR -> aynayı kapı da kurar
    taban_canon = set()
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            if not (g.get("birincil") and len(g["urunler"]) >= mm.ESIK):
                continue
            if g.get("baslik_dogan") and (marka, g["canon"]) not in izin \
                    and not mm.sekil_kurali_yargisi(marka, g["canon"],
                                                    g.get("display") or g["canon"]):
                continue
            taban_canon.add(g["canon"])

    drift, gereksiz = [], []
    for marka, d in veri.items():
        if mm.marka_urun_sayisi(d) < mm.ESIK:
            continue
        for g in d["gruplar"].values():
            canon, dsp = g["canon"], (g.get("display") or g["canon"])
            kural_yargilar = (mm._canon(marka) in sahip(dsp)
                              and canon not in taban_canon)
            if (marka, canon) in izin and (
                    kural_yargilar or mm.sekil_kurali_yargisi(marka, canon, dsp)):
                gereksiz.append((marka, dsp))
            if not g.get("baslik_dogan") or mm.yayimlanir_mi(g):
                continue
            if not (g.get("birincil") and len(g["urunler"]) >= mm.ESIK):
                continue
            if g.get("yabanci_marka") or mm.model_olmayan_cift_mi(marka, dsp) \
                    or mm.donanim_kuyruklu_mu(dsp) or (marka, canon) in mm.ROZET_DISI:
                continue
            if kural_yargilar:
                drift.append((marka, dsp, len(g["urunler"])))
    return drift, gereksiz, len(izin)


def sinif_kontrol_mutanti(mm, ham0_sayaci):
    """KONTROL: gürültü sınıfı SENTETİK bir pozitifte GERÇEKTEN ateşliyor mu? Ateşlemiyorsa
    'ihlal 0' hükmü dejenere ölçümdür (kural ölü)."""
    etiket = None
    for ad, n in ham0_sayaci.items():
        if n >= mm.ESIK:
            etiket = ad
            break
    if etiket is None:
        return False
    ids = ["s1", "s2", "s3"]
    ham0 = {"s1": etiket, "s2": etiket, "s3": mm._canon("SahteMarka")}
    say = Counter(ham0.get(i) for i in ids)
    return (say.get(etiket, 0) * 2 > len(ids)
            and say.get(mm._canon("SahteMarka2"), 0) * 2 <= len(ids))


_JS_HARNESS = r"""
// TIKLAMA HARNESS — sayfanin KENDI gomulu filtre modulunu SAHTE DOM ile kosturur.
// Genel amacli DOM motoru DEGIL: modulun kullandigi secicilerin TAMAMI burada karsilanir;
// tanimadigi bir secici gelirse HATA atar (fail-closed -> modul degisirse kapi OLCULEMEDI
// der, sessizce "yesil" demez).
"use strict";
const fs = require("fs");
const girdi = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

function El(tag, attrs, cocuk){
  this.tag = tag; this.attrs = attrs || {}; this.cocuk = cocuk || [];
  this.style = {display: ""}; this.className = this.attrs["class"] || "";
  this._metin = this.attrs._metin || ""; this.dinleyici = {};
}
El.prototype.getAttribute = function(a){
  return Object.prototype.hasOwnProperty.call(this.attrs, a) ? this.attrs[a] : null;
};
El.prototype.addEventListener = function(t, f){
  (this.dinleyici[t] = this.dinleyici[t] || []).push(f);
};
El.prototype.dispatch = function(t){
  const l = this.dinleyici[t] || [];
  for (let i = 0; i < l.length; i++) { l[i].call(this, {preventDefault: function(){}}); }
};
El.prototype.querySelector = function(s){
  if (s === ".adet") {
    for (const c of this.cocuk) { if (c.className === "adet") { return c; } }
    return null;
  }
  if (s === ".card-main") {
    for (const c of this.cocuk) { if (c.className === "card-main") { return c; } }
    return null;
  }
  throw new Error("HARNESS: taninmayan querySelector " + s);
};
Object.defineProperty(El.prototype, "textContent", {
  get: function(){ return this._metin; },
  set: function(v){ this._metin = String(v); }
});

function kart(id, mm){
  const a = new El("a", {"class": "card-main", href: "/urun/" + id + "/"});
  a.className = "card-main";
  const k = new El("div", {"class": "card", "data-kat": "Otomobil"}, [a]);
  k.className = "card";
  if (mm !== null) { k.attrs["data-mm"] = String(mm); }
  return k;
}

const yuk = girdi.yuk;                       // {k:[[id,katIx,[modelIx..]]], kat:[], m:[]}
const manifestEl = new El("script", {id: "mmManifest", _metin: girdi.manifestMetni});
const grid = new El("div", {id: "mmGrid"});
grid.cocuk = girdi.ssrKartlar.map(function(k){ return kart(k[0], k[1]); });
const durum = new El("span", {id: "mmDurum"});
const dugme = new El("button", {id: "mmTumu"});
// BEYAN DUGUMLERI (bolum basliklari + toplam cumlesi) ve DUZ BAG bolumu.
const beyanErisim = new El("span", {"class": "mm-sayim-kart", "data-bolum": "erisim",
                                    _metin: String(girdi.beyanErisim)});
beyanErisim.className = "mm-sayim-kart";
const beyanAlt = new El("span", {"class": "mm-sayim-kart", "data-bolum": "alt",
                                 _metin: String(girdi.beyanAlt)});
beyanAlt.className = "mm-sayim-kart";
const beyanToplam = new El("span", {"class": "mm-sayim-toplam",
                                    _metin: String(girdi.beyanErisim)});
beyanToplam.className = "mm-sayim-toplam";
const kalanBolum = new El("div", {id: "mmKalan"});
const cipler = girdi.cipler.map(function(c){
  const adet = new El("span", {"class": "adet", _metin: c.n + " parça"});
  adet.className = "adet";
  const e = new El("a", {"class": "mm-model-btn", "data-mm": String(c.ix),
                         href: c.href}, [adet]);
  e.className = "mm-model-btn";
  return e;
});

const document = {
  getElementById: function(id){
    if (id === "mmManifest") { return manifestEl; }
    if (id === "mmGrid") { return grid; }
    if (id === "mmDurum") { return durum; }
    if (id === "mmTumu") { return dugme; }
    if (id === "mmFiltreSifirla") { return null; }
    if (id === "mmKalan") { return kalanBolum; }
    throw new Error("HARNESS: taninmayan getElementById " + id);
  },
  querySelector: function(s){
    if (s === ".mm-sayim-toplam") { return beyanToplam; }
    throw new Error("HARNESS: taninmayan querySelector " + s);
  },
  querySelectorAll: function(s){
    if (s === ".mm-model-btn[data-mm]") { return cipler; }
    if (s === ".mm-sayim-kart") { return [beyanErisim, beyanAlt]; }
    if (s === "#mmGrid .mm-iskelet") {
      return grid.cocuk.filter(function(k){ return k.className === "mm-iskelet"; });
    }
    if (s === "#mmGrid .card") {
      return grid.cocuk.filter(function(k){ return k.className === "card"; });
    }
    if (s === "#mmGrid .card[data-artim]") {
      return grid.cocuk.filter(function(k){ return k.className === "card"
                                                   && k.attrs["data-artim"] !== undefined; });
    }
    if (s === "#mmGrid .card:not([data-artim])") {
      return grid.cocuk.filter(function(k){ return k.className === "card"
                                                   && k.attrs["data-artim"] === undefined; });
    }
    throw new Error("HARNESS: taninmayan querySelectorAll " + s);
  }
};
grid.removeChild = function(k){
  const i = grid.cocuk.indexOf(k);
  if (i !== -1) { grid.cocuk.splice(i, 1); }
};
grid.cocuk.forEach(function(k){ k.parentNode = grid; });
grid.insertAdjacentHTML = function(_yer, html){
  // Cizilen kartlari SAY: gercek DOM ayristirmasi GEREKMEZ, kart sayisi kart acilisindan.
  const n = (html.match(/data-artim=""/g) || []).length;
  for (let i = 0; i < n; i++) {
    const k = kart("artim-" + (grid.cocuk.length + i), girdi.aktifIxIcinUye);
    k.attrs["data-artim"] = "";
    k.parentNode = grid;
    grid.cocuk.push(k);
  }
  // ISKELET (yer tutucu) dugumleri: sinifi `card` DEGIL, ayri sayilir.
  const isk = (html.match(/class="mm-iskelet"/g) || []).length;
  for (let i = 0; i < isk; i++) {
    const e = new El("div", {"class": "mm-iskelet"});
    e.className = "mm-iskelet";
    e.parentNode = grid;
    grid.cocuk.push(e);
  }
};

let istek = 0;
let bekleyenler = [];
function coz(){ const b = bekleyenler; bekleyenler = []; b.forEach(function(f){ f(); }); }
const g = {
  location: {search: ""},
  addEventListener: function(t, f){ (this._d = this._d || {}), (this._d[t] = this._d[t] || []).push(f); },
  _tetikle: function(t){ (this._d && this._d[t] || []).forEach(function(f){ f(); }); }
};
g.fetch = function(url){
  istek++;
  return new Promise(function(res){
    bekleyenler.push(function(){
      res({ok: true, json: function(){
        if (String(url).indexOf("parcalar.json") !== -1) { return Promise.resolve(yuk); }
        return Promise.resolve({urunler: girdi.edgeKayitlari});
      }});
    });
  });
};
g.Promise = Promise;

// MODULU KUR
const modul = girdi.artimJs;
try { (new Function("window", "document", "URLSearchParams", "fetch", "Promise",
                    modul + "\n"))(g, document, URLSearchParams, g.fetch, Promise); }
catch (e) { console.log(JSON.stringify({hata: "modul kurulamadi: " + e.message})); process.exit(0); }
g._tetikle("DOMContentLoaded");

function gorunen(){
  return grid.cocuk.filter(function(k){
    return k.className === "card" && k.style.display !== "none";
  }).length;
}
function gorunenTumDugum(){         // kart + iskelet: EKRANDA bir sey var mi
  return grid.cocuk.filter(function(k){ return k.style.display !== "none"; }).length;
}
const sonuc = {kuruldu: typeof g.PRUVO_ARTIM_DURUM === "function", istek0: istek,
               beyanIlk: [beyanErisim.textContent, beyanAlt.textContent,
                          beyanToplam.textContent]};

// (1) ON YUKLEME: isaretci cipe dokununca, TIKLAMADAN ONCE yuk istenmeli
cipler[0].dispatch("pointerdown");
sonuc.onyukIstek = istek;

// (2) ANINDA BEYAN: tiklamadan hemen sonra, yuk GELMEDEN durum metni + EKRAN DOLU MU
cipler[0].dispatch("click");
sonuc.aninda = durum.textContent;
sonuc.anindaGorunen = gorunen();
sonuc.anindaDugum = gorunenTumDugum();            // 0 ise EKRAN BOS -> kabul degil
sonuc.anindaBeyan = [beyanErisim.textContent, beyanAlt.textContent, beyanToplam.textContent];
sonuc.anindaKalan = kalanBolum.style.display;

// (3) yuk gelsin -> kesin sayi + cizilen kart. Zincir cok asamali (yuk -> suz -> edge ->
// ciz): TEK tik YETMEZ; bekleyen cozulur ve mikro-gorev kuyrugu bosalana kadar donulur.
(async function(){
  for (let i = 0; i < 40; i++) {
    coz();
    await new Promise(function(r){ setTimeout(r, 0); });
  }
  sonuc.sonDurum = durum.textContent;
  sonuc.sonGorunen = gorunen();
  sonuc.sonIskelet = grid.cocuk.filter(function(k){
    return k.className === "mm-iskelet"; }).length;   // gercek kart gelince 0 olmali
  sonuc.sonBeyan = [beyanErisim.textContent, beyanAlt.textContent, beyanToplam.textContent];
  // (4) BAYAT YOK: ikinci cipe basilinca onceki sayi ANINDA gitmeli
  cipler[1].dispatch("click");
  sonuc.ikinciAninda = durum.textContent;
  sonuc.ikinciBeyan = [beyanErisim.textContent, beyanAlt.textContent, beyanToplam.textContent];
  sonuc.istekSon = istek;
  // (5) SIFIRLAMA: beyan SSR degerlerine DONER, duz bag bolumu geri gelir.
  // Once ikinci cipin yuku COZULUR: modul mesgulken gelen tiklamayi BILEREK yutar
  // (`if(mesgul){ return; }`), sifirlama iddiasi o yutmayi olcmemeli.
  for (let i = 0; i < 40; i++) {
    coz();
    await new Promise(function(r){ setTimeout(r, 0); });
  }
  cipler[1].dispatch("click");                        // ayni cipe tekrar -> filtre kalkar
  sonuc.sifirBeyan = [beyanErisim.textContent, beyanAlt.textContent, beyanToplam.textContent];
  sonuc.sifirKalan = kalanBolum.style.display;
  console.log(JSON.stringify(sonuc));
})();
"""


def tiklama_olcumu(tmp, mm, sayfalar):
    """Sayfanın KENDİ modülünü node'da koştur; tıklama davranışını ÖLÇ."""
    artim = mm.artim_scripti()
    bas, son = artim.find(ARTIM_BAS), artim.find(ARTIM_SON)
    if bas < 0 or son < 0:
        raise Olculemedi("artım modülü işaretçileri bulunamadı")
    js = artim[bas + len(ARTIM_BAS):son]
    # Fikstür GERÇEK ÇIKTI ŞEKLİNİ taklit eder: SSR kartları YEREL kalemlerdir (model
    # üyeliği YOK) — canlıda boş ekranı doğuran şekil budur.
    yuk = {"toplam": 12, "basili": 4, "kat": ["Otomobil"], "m": ["a", "b"],
           "k": [["y1", 0, []], ["y2", 0, []], ["y3", 0, []], ["y4", 0, []],
                 ["a1", 0, [0]], ["a2", 0, [0]], ["a3", 0, [0]], ["a4", 0, [0]],
                 ["a5", 0, [0]], ["b1", 0, [1]], ["b2", 0, [1]], ["b3", 0, [1]]],
           "o": {}}
    manifest = {"yuk": "/marka/x/parcalar.json", "uc": "https://uc.example",
                "yol": "/katalog?ids=", "parti": 100, "site": "https://pruvo3d.com",
                "toplam": 12, "basili": 4}
    girdi = {
        "artimJs": js,
        "yuk": yuk,
        "manifestMetni": json.dumps(manifest, ensure_ascii=False),
        "ssrKartlar": [["y1", None], ["y2", None], ["y3", None], ["y4", None]],
        "cipler": [{"ix": 0, "n": 5, "href": "/marka/x/a/"},
                   {"ix": 1, "n": 3, "href": "/marka/x/b/"}],
        "aktifIxIcinUye": 0,
        "beyanErisim": 12,        # SSR bolum sayisi (kart yuzeyi)
        "beyanAlt": 4,            # SSR duz bag bolumu (YEREL kalemler)
        "edgeKayitlari": [{"id": "a%d" % i, "baslik": "A%d" % i, "kategori": "Otomobil",
                           "fiyat": "10 TL", "gorsel": "x.jpg"} for i in range(1, 6)],
    }
    gyol = os.path.join(tmp, "tiklama-girdi.json")
    hyol = os.path.join(tmp, "tiklama-harness.js")
    with open(gyol, "w", encoding="utf-8") as f:
        json.dump(girdi, f, ensure_ascii=False)
    with open(hyol, "w", encoding="utf-8") as f:
        f.write(_JS_HARNESS)
    try:
        cp = subprocess.run(["node", hyol, gyol], capture_output=True, text=True, timeout=300)
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("node koşturulamadı: %r" % (e,))
    if cp.returncode != 0 or not cp.stdout.strip():
        raise Olculemedi("node rc=%d %s" % (cp.returncode, (cp.stderr or "")[-300:]))
    try:
        out = json.loads(cp.stdout.strip().splitlines()[-1])
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("node çıktısı okunamadı: %r" % (e,))
    if "hata" in out:
        raise Olculemedi(out["hata"])
    return out


def kapiyi_kos():
    kapi = Kapi()
    tmp = tempfile.mkdtemp(prefix="mm-cip-kapi-")
    try:
        products, mm, index_html = sayfalari_uret(tmp)
        sayfalar = agaci_tara(tmp)
        marka_sayfalari = {y: s for y, s in sayfalar.items()
                           if y.count("/") == 1 and y != "marka" and s["cipler"]}
        if not marka_sayfalari:
            raise Olculemedi("çip taşıyan marka sayfası bulunamadı")

        cip_toplam = 0
        kirik, bos, sayi_filtre, sayi_sayfa = [], [], [], []
        for yol, s in sorted(marka_sayfalari.items()):
            yuk = s["yuk"]
            if not isinstance(yuk, dict) or "k" not in yuk:
                raise Olculemedi("%s: parcalar.json yok/bozuk — filtre kümesi ölçülemez" % yol)
            filtre = Counter()
            for k in yuk["k"]:
                for ix in (k[2] or []):
                    filtre[ix] += 1
            for href, ix, n in s["cipler"]:
                cip_toplam += 1
                hedef = href.strip("/")
                h = sayfalar.get(hedef)
                if h is None:
                    kirik.append((yol, href))
                    continue
                if (h["kart"] + h["bag"]) <= 0 or not h["toplam"]:
                    bos.append((yol, href))
                if filtre.get(ix, 0) != n:
                    sayi_filtre.append((yol, href, n, filtre.get(ix, 0)))
                if h["toplam"] != n:
                    sayi_sayfa.append((yol, href, n, h["toplam"]))

        kapi.iddia("HEDEF/cozuldu", not kirik,
                   "çip hedefi üretilen ağaçta YOK: %d çip — %s" % (len(kirik), kirik[:5]))
        kapi.iddia("HEDEF/dolu", not bos,
                   "çip hedefi BOŞ (200 ama liste yok): %d — %s" % (len(bos), bos[:5]))
        kapi.iddia("SAYI/filtre", not sayi_filtre,
                   "çipin bastığı sayı sayfa-içi filtre kümesinden AYRIŞTI: %d — %s"
                   % (len(sayi_filtre), sayi_filtre[:5]))
        kapi.iddia("SAYI/sayfa", not sayi_sayfa,
                   "çipin bastığı sayı hedef sayfanın beyanından AYRIŞTI: %d — %s"
                   % (len(sayi_sayfa), sayi_sayfa[:5]))
        kapi.iddia("KAPSAM/dejenere", cip_toplam >= 100,
                   "ölçülen çip sayısı dejenere (%d) — evren kurulamadı" % cip_toplam)

        ihlal, olculen_kova, ham0 = yabanci_marka_sinifi(products, mm, index_html)
        kapi.iddia("GURULTU/yabanci", not ihlal,
                   "çip etiketi AYRI BİR MARKA (kova o markanın ürünlerini taşıyor): %d — %s"
                   % (len(ihlal), sorted(ihlal.values(), key=lambda v: -v[2])[:5]))
        kapi.iddia("GURULTU/kontrol", sinif_kontrol_mutanti(mm, ham0),
                   "gürültü sınıfı SENTETİK pozitifte ateşlemedi (kural ÖLÜ, 'ihlal 0' dejenere)")
        kapi.iddia("GURULTU/evren", olculen_kova >= 100,
                   "gürültü ekseninde ölçülen kova sayısı dejenere (%d)" % olculen_kova)

        drift, gereksiz, envanter_n = envanter_drifti(products, mm, index_html)
        # Sahiplik kolunu canlı katalog tesadüfen örtemez: pozitif ve yabancı-sahip
        # sentinelleri yalnız (d) kolunu ateşler. Böylece kol kapanırsa mevcut kovalar
        # başka bir yargıdan yayımlansa bile mutasyon sessizce kaçamaz.
        sahiplik_kolu_canli = (
            mm.baslik_yargisi_var_mi("KapiMarka", "kapijeton", "KapiJeton",
                                     mm._canon("KapiMarka"))
            and not mm.baslik_yargisi_var_mi("KapiMarka", "kapijeton", "KapiJeton",
                                             mm._canon("BaskaMarka")))
        kapi.iddia("ENVANTER/drift", not drift and sahiplik_kolu_canli,
                   "kova YALNIZCA elle envanterde olmadığı için çipsiz kaldı (envanter "
                   "bayatladı) veya sahiplik kolu sentineli çalışmadı: %d kova, kol=%s — %s"
                   % (len(drift), sahiplik_kolu_canli,
                      sorted(drift, key=lambda v: -v[2])[:5]))
        kapi.iddia("ENVANTER/gereksiz", not gereksiz,
                   "elle envanterde KURALIN zaten yargıladığı ÖLÜ giriş var (liste büyüyerek "
                   "çözülmez): %d — %s" % (len(gereksiz), gereksiz[:5]))
        kapi.iddia("ENVANTER/evren", envanter_n > 0,
                   "envanter BOŞ okundu — bayatlık ekseni dejenere")

        t = tiklama_olcumu(tmp, mm, sayfalar)
        kapi.iddia("TIKLAMA/kuruldu", bool(t.get("kuruldu")),
                   "filtre modülü node'da kurulmadı — tıklama davranışı ölçülemez")
        kapi.iddia("TIKLAMA/onyuk", t.get("onyukIstek", 0) >= 1,
                   "işaretçi çipe dokununca yük İSTENMEDİ (istek=%s) — boş pencere ağ turu "
                   "kadar uzar" % t.get("onyukIstek"))
        kapi.iddia("TIKLAMA/aninda", "5 parça" in str(t.get("aninda") or ""),
                   "tıklamadan sonra yük gelmeden durum metni ÇİPİN SAYISINI taşımıyor: %r"
                   % (t.get("aninda"),))
        kapi.iddia("TIKLAMA/bosdegil", bool(str(t.get("aninda") or "").strip()),
                   "tıklamadan sonra ekran BOŞ ve durum metni de BOŞ (kullanıcı 'çalışmıyor' görür)")
        kapi.iddia("TIKLAMA/sonuc", t.get("sonGorunen") == 5,
                   "yük geldikten sonra görünen kart sayısı çipin bastığı sayı DEĞİL: %s != 5"
                   % (t.get("sonGorunen"),))
        kapi.iddia("TIKLAMA/sonmetin", "5 parça" in str(t.get("sonDurum") or ""),
                   "yük sonrası durum metni kanonik sayıyı taşımıyor: %r" % (t.get("sonDurum"),))
        kapi.iddia("TIKLAMA/bayat", "5 parça" not in str(t.get("ikinciAninda") or "")
                   and "3 parça" in str(t.get("ikinciAninda") or ""),
                   "ikinci çipe basılınca ÖNCEKİ çipin sayısı ekranda KALDI: %r"
                   % (t.get("ikinciAninda"),))
        kapi.iddia("TIKLAMA/kontrol", t.get("anindaGorunen") != t.get("sonGorunen"),
                   "filtre koşumu dejenere: tıklamadan önceki ve sonraki görünen kart sayısı AYNI")
        # 🔴 EKRAN BOŞ KALMAZ: tıklamadan sonra, yük GELMEDEN grid'de görünür düğüm olmalı
        # (yer tutucu). Ölçülen kusur tam buydu: 1,0-6,5 sn boyunca ekranda HİÇBİR ŞEY yoktu.
        kapi.iddia("TIKLAMA/ekran_dolu", (t.get("anindaDugum") or 0) > 0,
                   "tıklamadan sonra yük gelmeden ekranda GÖRÜNÜR DÜĞÜM YOK (boş ekran): %s"
                   % (t.get("anindaDugum"),))
        kapi.iddia("TIKLAMA/iskelet_temiz", t.get("sonIskelet") == 0,
                   "gerçek kartlar geldiği hâlde yer tutucular ASILI KALDI: %s"
                   % (t.get("sonIskelet"),))
        # 🔴 BEYAN == O AN ERİŞİLEBİLEN KÜME (Okan hükmünün MODEL ekseni)
        kapi.iddia("BEYAN/aninda", t.get("anindaBeyan") == ["5", "0", "5"],
                   "model filtresi etkinken bölüm başlıkları/beyan cümlesi filtreli kümeyi "
                   "GÖSTERMİYOR: %s (beklenen ['5','0','5'])" % (t.get("anindaBeyan"),))
        kapi.iddia("BEYAN/son", t.get("sonBeyan") == ["5", "0", "5"],
                   "yük geldikten sonra beyan kanonik kümeden AYRIŞTI: %s"
                   % (t.get("sonBeyan"),))
        kapi.iddia("BEYAN/bayat", t.get("ikinciBeyan") == ["3", "0", "3"],
                   "ikinci çipe basılınca beyan ÖNCEKİ çipin sayısında KALDI: %s"
                   % (t.get("ikinciBeyan"),))
        kapi.iddia("BEYAN/kalan_kapandi", t.get("anindaKalan") == "none",
                   "model filtresi etkinken düz bağ bölümü (yerel kalemler) EKRANDA KALDI")
        kapi.iddia("BEYAN/sifirlama", t.get("sifirBeyan") == t.get("beyanIlk")
                   and t.get("sifirKalan") != "none",
                   "filtre kaldırılınca beyan/düz bağ bölümü SSR hâline DÖNMEDİ: %s / %s"
                   % (t.get("sifirBeyan"), t.get("sifirKalan")))

        ozet = {"CIP_TOPLAM": cip_toplam, "MARKA_SAYFASI": len(marka_sayfalari),
                "KIRIK_LINK": len(kirik), "BOS_LISTE": len(bos),
                "SAYI_SAPAN_FILTRE": len(sayi_filtre), "SAYI_SAPAN_SAYFA": len(sayi_sayfa),
                "GURULTU": len(ihlal), "OLCULEN_KOVA": olculen_kova,
                "ENVANTER_GIRIS": envanter_n, "ENVANTER_DRIFT": len(drift),
                "ENVANTER_GEREKSIZ": len(gereksiz)}
        return kapi, ozet
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if "--iz" in sys.argv:
        print("IZ=%s" % kaynak_izi())
        return 0
    try:
        kapi, ozet = kapiyi_kos()
    except Olculemedi as e:
        print("OLCULEMEDI: %s" % (e,))
        print("HUKUM=OLCULEMEDI")
        return 3
    except Exception as e:                                        # noqa: BLE001
        print("OLCULEMEDI: beklenmeyen hata: %r" % (e,))
        print("HUKUM=OLCULEMEDI")
        return 3
    print("IZ=%s" % kaynak_izi())
    for k in sorted(ozet):
        print("  %s=%s" % (k, ozet[k]))
    for aile, ayrinti in kapi.dusen:
        print("  DUSTU %s — %s" % (aile, ayrinti))
    print("KOSAN_IDDIA=%d DUSEN_IDDIA=%d" % (kapi.kosan, len(kapi.dusen)))
    # 🔴 İNSANA BASILAN ÖZET HÜKMÜ BESLEYEN KÜMEDEN TÜRER: aile listesi `kapi.dusen`in
    # KENDİSİNDEN okunur, ikinci bir sayım noktası açılmaz.
    print("DUSEN_AILELER=%s" % (",".join(kapi.aileler) or "-"))
    print("HUKUM=%s" % ("YESIL" if kapi.yesil else "KIRMIZI"))
    return 0 if kapi.yesil else 1


if __name__ == "__main__":
    sys.exit(main())
