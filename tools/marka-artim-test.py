#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARTIMLI KART ÇİZİMİ + SAYFA-İÇİ MODEL FİLTRESİ — DAVRANIŞ testi (node'da GERÇEK JS).

🔴 NEDEN VAR (Okan hükmü, 8 Ağu 2026): "marka sayfası markanın TÜM parçalarını kart olarak
listeler; model çipleri AYRI ADRESE GİTMEZ, sayfa İÇİNDE filtreler." Bu hüküm üç DAVRANIŞ
iddiası doğurur ve hiçbiri statik HTML'e bakarak ölçülemez:

  1. JS-SİZ hâlde sayfa BOZULMAZ: HTML'de duran N kart görünür kalır, çip model sayfasına
     giden GERÇEK bir <a>'dır (iç link + crawl hedefi + JS-siz erişim korunur).
  2. JS VARKEN çipe basmak ADRESİ DEĞİŞTİRMEZ: tıklama preventDefault edilir ve kartlar
     sayfa içinde süzülür.
  3. "Tümünü göster" sayfanın KALAN kalemlerini AYNI SAYFADA çizer ve kart yüzeyi sayfanın
     kanonik toplamına ULAŞIR (Okan'ın istediği "kullanıcı tamamını görür").

Ölçüm YÖNTEMİ: sayfaya GÖMÜLEN artım modülü marker'lardan ayıklanır ve node'da, şimlenmiş
bir DOM + fetch ile GERÇEKTEN koşturulur. Kartlar dizeden değil, modülün KENDİ ürettiği
HTML'den sayılır. Fikstür GERÇEK bir marka sayfasının üretilmiş HTML'i + gerçek
`parcalar.json` yüküdür (uydurma şekil yok → [[nobetci-fikstur-sekli]]).

FAIL-CLOSED: ölçüm kurulamazsa rc=3 (ÖLÇÜLEMEDİ) — yeşil sayılmaz.
Kullanım: python3 tools/marka-artim-test.py [--dokum]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
KART_RE = re.compile(r'<div class="card" data-kat="([^"]*)"([^>]*)><a class="card-main" '
                     r'href="([^"]+)"')
BTN_RE = re.compile(r'<a class="mm-model-btn" href="([^"]+)" data-katsay="([^"]*)" '
                    r'data-mm="(\d+)"')
MANIFEST_RE = re.compile(r'<script type="application/json" id="mmManifest">(.*?)</script>', re.S)
# BAŞLIK SAYACI. 🔴 12 Ağu 2026 (Okan, canlı): bu sayı O AN BASILAN kartı yazıyordu
# ("… parçaları (80)") ama sayfanın beyanı erişilebilir yüzeydi ("593 parça listeleniyor").
# A3d ESKİDEN o yalanı KUTSUYORDU: "sayaç == fiilen basılan kart". Yeni hüküm: başlık
# kullanıcının ERİŞEBİLDİĞİNİ gösterir; sayaç KENDİ kategori kırılımını taşır.
SAYIM_RE = re.compile(r'<span class="mm-sayim-kart" data-bolum="([^"]*)" '
                      r'data-katsay="([^"]*)">(\d+)</span>')
EDGE_KANON_RE = re.compile(
    r'fetch\(EDGE_UC \+ "([^"]+)" \+ encodeURIComponent\(eksik\.slice\(0,\s*(\d+)\)')

FIKSTUR_YANLIS_MARKA_ID = "fikstur-yalniz-toyota"
FIKSTUR_GECERSIZ_ID = ""

# --------------------------------------------------------------------------- node harness
_HARNESS = r"""
"use strict";
const fs = require("fs");
const vm = require("vm");
const V = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

// ------------------------------------------------------------------ minik DOM şimi
function el(tag, attrs, cls){
  return {tag: tag, attrs: attrs || {}, className: cls || "", style: {display: ""},
          cocuklar: [], ebeveyn: null,
          getAttribute(n){ return this.attrs[n] === undefined ? null : this.attrs[n]; },
          setAttribute(n, v){ this.attrs[n] = v; },
          addEventListener(t, f){ (this._d = this._d || {})[t] = f; },
          tetikle(t, ev){ if(this._d && this._d[t]){ this._d[t].call(this, ev); } },
          querySelector(s){ return s === ".card-main" ? this._main || null : null; },
          insertAdjacentHTML(_p, html){ this._html = (this._html || "") + html; }};
}
const grid = el("div", {id: "mmGrid"});
const dugme = el("button", {id: "mmTumu"});
const durum = el("span", {id: "mmDurum"});
const sifirla = el("a", {id: "mmFiltreSifirla"});
const manifestEl = {textContent: V.manifestMetni};

// SSR kartları: gerçek HTML'den geldi (kategori + data-mm + ürün id)
const ssrKartlar = V.ssrKartlar.map((k) => {
  const c = el("div", {"data-kat": k.kat, "data-mm": k.mm}, "card");
  if(k.mm === null){ delete c.attrs["data-mm"]; }
  c._main = {getAttribute: (n) => (n === "href" ? "/urun/" + k.id + "/" : null)};
  c._id = k.id;
  return c;
});
const cipler = V.cipler.map((b) => {
  const c = el("a", {href: b.href, "data-katsay": b.katsay, "data-mm": b.mm}, "mm-model-btn");
  return c;
});

// grid içindeki kartlar: SSR kartları + modülün insertAdjacentHTML ile eklediği kartlar.
// Eklenen HTML gerçekten PARSE edilmez; kart SAYISI ve data-artim işareti dizeden ölçülür
// (modülün ürettiği gövde ayrıca marka-sayac-kapisi'nda BAYT karşılaştırılıyor).
function eklenenKartlar(){
  const h = grid._html || "";
  const m = h.match(/<div class="card" data-kat="/g);
  return m ? m.length : 0;
}
const dok = {
  getElementById(id){
    return ({mmGrid: grid, mmTumu: dugme, mmDurum: durum, mmFiltreSifirla: sifirla,
             mmManifest: manifestEl})[id] || null;
  },
  querySelectorAll(s){
    if(s === "#mmGrid .card"){ return ssrKartlar; }
    if(s === "#mmGrid .card:not([data-artim])"){ return ssrKartlar; }
    if(s === "#mmGrid .card[data-artim]"){ return []; }   // şimde ayrı düğüm tutulmuyor
    if(s === ".mm-model-btn[data-mm]"){ return cipler; }
    return [];
  },
  body: {scrollHeight: 5000}
};

// ------------------------------------------------------------------ fetch + window şimi
// 🔴 fetch şimi TÜM KATALOG adresini BİLEREK tanımıyor: modül `/urunler.json` gibi bir
// toplu adrese giderse istek REDDEDİLİR ve iddia düşer (ağırlık regresyonu sessiz kalmaz).
let fetchCagri = 0, yukCagri = 0, edgeCagri = 0;
const istenenIdler = [];          // edge'den istenen TÜM id'ler (mükerrer dahil)
const partiBoylari = [];
const bilinmeyenAdres = [];
const EDGE_ONEK = V.manifest.uc + V.kanonikYol;
function fetchSim(u){
  fetchCagri++;
  if(u === V.manifest.yuk){
    yukCagri++;
    return Promise.resolve({ok: true, json: () => Promise.resolve(V.yuk)});
  }
  if(u.indexOf(EDGE_ONEK) === 0){
    edgeCagri++;
    const ham = decodeURIComponent(u.slice(EDGE_ONEK.length));
    const idler = ham ? ham.split(",") : [];
    partiBoylari.push(idler.length);
    idler.forEach((x) => istenenIdler.push(x));
    // edge ucunun GERÇEK sekli: tekil `gorsel`, `gorseller` dizisi YOK (canli olculdu)
    const urunler = idler.map((id) => V.edge[id]).filter((x) => !!x);
    return Promise.resolve({ok: true, json: () => Promise.resolve({urunler: urunler,
                                                                  toplam: urunler.length})});
  }
  bilinmeyenAdres.push(u);
  return Promise.reject(new Error("beklenmeyen adres: " + u));
}
const konum = {search: V.search || "", pathname: V.pathname || "/marka/x/",
               _degisti: false, replace(u){ this._degisti = true; this._hedef = u; }};
const dinleyiciler = {};
const g = {
  document: dok, location: konum, scrollY: 0, innerHeight: 800,
  addEventListener(t, f){ dinleyiciler[t] = f; },
  fetch: fetchSim, Promise: Promise, JSON: JSON, String: String, Object: Object,
  URLSearchParams: URLSearchParams, parseInt: parseInt, Math: Math,
  console: {log(){}, warn(){}, error(){}}, decodeURIComponent: decodeURIComponent
};
g.window = g;
// KAPSAM modülü de yüklenir (artım kolu sayaçları onun üzerinden tazeler)
vm.runInNewContext(V.kapsamJs, g, {filename: "kapsam.js", timeout: 10000});
vm.runInNewContext(V.artimJs, g, {filename: "artim.js", timeout: 10000});

const cikti = {kuruldu: !!g.PRUVO_ARTIM, domHazir: !!dinleyiciler.DOMContentLoaded};
if(!cikti.kuruldu || !cikti.domHazir){
  console.log(JSON.stringify(cikti)); process.exit(0);
}

// ---- 1) JS-SİZ ÖLÇÜM: modül HİÇ koşmadan kaç kart görünür + çip href gerçek mi
cikti.jssizKart = ssrKartlar.filter((c) => c.style.display !== "none").length;
cikti.cipHrefleri = cipler.map((c) => c.getAttribute("href"));

// ---- modülü kur (DOMContentLoaded)
dinleyiciler.DOMContentLoaded();
// 🔴 İLK AÇILIŞ: modül kurulduktan sonra, kullanıcı hiçbir şey yapmadan HİÇ istek atılmamalı
// (tüm katalog indirme regresyonunun davranışsal nöbeti).
cikti.acilistaFetch = fetchCagri;

let tik = Promise.resolve();
function bekle(){ return new Promise((r) => setTimeout(r, 0)); }

// ---- 2) ÇİP TIKLAMASI: adres DEĞİŞMEZ + preventDefault edilir + sayfa içinde süzülür
let onlendi = false;
tik = tik.then(bekle).then(() => {
  cipler[0].tetikle("click", {preventDefault(){ onlendi = true; }});
  return bekle();
}).then(bekle).then(bekle).then(() => {
  cikti.cipOnlendi = onlendi;
  cikti.adresDegisti = konum._degisti;
  cikti.filtreSonrasiGizliSsr = ssrKartlar.filter((c) => c.style.display === "none").length;
  cikti.filtreSonrasiEklenen = eklenenKartlar();
  cikti.filtreDurum = durum.textContent;
  cikti.cipAktifSinif = cipler[0].className;
  // ---- 3) FİLTREYİ SIFIRLA, sonra "TÜMÜNÜ GÖSTER": kalan kalemler AYNI SAYFADA çizilir
  grid._html = "";
  sifirla.tetikle("click", {preventDefault(){}});
  return bekle();
}).then(bekle).then(() => {
  grid._html = "";
  dugme.tetikle("click", {preventDefault(){}});
  return bekle();
}).then(bekle).then(bekle).then(() => {
  cikti.tumuEklenen = eklenenKartlar();
  cikti.tumuDurum = durum.textContent;
  cikti.dugmeGizli = dugme.style.display === "none";
  cikti.fetchCagri = fetchCagri;
  cikti.yukCagri = yukCagri;
  cikti.edgeCagri = edgeCagri;
  cikti.istenenIdSayisi = istenenIdler.length;
  cikti.istenenTekil = Object.keys(istenenIdler.reduce((a, x) => (a[x] = 1, a), {})).length;
  cikti.enBuyukParti = partiBoylari.length ? Math.max.apply(null, partiBoylari) : 0;
  cikti.bilinmeyenAdres = bilinmeyenAdres;
  cikti.artimIsaretli = ((grid._html || "").match(/data-artim=""/g) || []).length;
  cikti.durumKancasi = g.PRUVO_ARTIM_DURUM ? g.PRUVO_ARTIM_DURUM() : null;
  console.log(JSON.stringify(cikti));
});
"""


class Kapi:
    def __init__(self):
        self.gecen = 0
        self.dusen = []

    def iddia(self, kimlik, kosul, detay=""):
        if kosul:
            self.gecen += 1
            print("  GECTI %s" % kimlik)
        else:
            self.dusen.append(kimlik + ((" — " + detay) if detay else ""))
            print("  DUSEN %s%s" % (kimlik, (" — " + detay) if detay else ""))

    @property
    def taban(self):
        return self.gecen + len(self.dusen)


def olc(dokum=False):
    import build                          # noqa: PLC0415
    import marka_model_build as mm        # noqa: PLC0415

    kapi = Kapi()
    tmp = tempfile.mkdtemp(prefix="mm-artim-test-")
    try:
        with open(os.path.join(build.ROOT, "urunler.json"), encoding="utf-8") as f:
            products = json.load(f)
        # Ayırt edici kayıtlar: yalnız-Toyota kaydı Honda'ya sızamaz; boş kimlikli kayıt
        # hiçbir marka sayfasında karta dönüşemez. İki DAF desteği sayfayı eşikte tutar.
        # Bu dört sentetik kayıt ürün kaynağına yazılmaz.
        products = [
            {"id": FIKSTUR_GECERSIZ_ID, "kategori": "Otomobil", "marka": ["DAF"],
             "baslik": "Kimliksiz test parçası", "aciklama": "Test fikstürü",
             "fiyat": "1 TL", "gorseller": []},
            {"id": "fikstur-daf-destek-1", "kategori": "Otomobil", "marka": ["DAF"],
             "baslik": "DAF test parçası bir", "aciklama": "Test fikstürü",
             "fiyat": "1 TL", "gorseller": []},
            {"id": "fikstur-daf-destek-2", "kategori": "Otomobil", "marka": ["DAF"],
             "baslik": "DAF test parçası iki", "aciklama": "Test fikstürü",
             "fiyat": "1 TL", "gorseller": []},
            {"id": FIKSTUR_YANLIS_MARKA_ID, "kategori": "Otomobil", "marka": ["Toyota"],
             "baslik": "Toyota test parçası", "aciklama": "Test fikstürü",
             "fiyat": "1 TL", "gorseller": []},
        ] + products
        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        shutil.copy(os.path.join(build.ROOT, "index.html"), os.path.join(tmp, "index.html"))
        with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
        mm.uret(products, ctx)
    except SystemExit as e:
        print("OLCULEMEDI: jeneratör durdu: %s" % (str(e)[:200],))
        return 3, kapi
    except Exception as e:                                        # noqa: BLE001
        print("OLCULEMEDI: sayfa üretilemedi: %r" % (e,))
        return 3, kapi

    kanon_eslesmeleri = EDGE_KANON_RE.findall(index_html)
    if len(kanon_eslesmeleri) != 1:
        print("OLCULEMEDI: index.html edge kanonu tekil degil: %r" % (kanon_eslesmeleri,))
        shutil.rmtree(tmp, ignore_errors=True)
        return 3, kapi
    kanonik_yol, kanonik_parti_ham = kanon_eslesmeleri[0]
    kanonik_parti = int(kanonik_parti_ham)

    # BAĞIMSIZ KART KÜMESİ: üretilen her marka kartı kaynak ürünün ham marka üyeliğine
    # uymalı; boş/bilinmeyen kimlik hiçbir kartta görünmemeli.
    urunler_id = {p.get("id"): p for p in products if p.get("id")}
    evren = mm.MarkaEvreni(index_html)
    yanlis_marka = []
    gecersiz_kimlik = []

    # FİKSTÜR = en çok model butonu olan marka sayfası (filtre ekseni en zengin orada)
    aday = None
    for dirpath, _dn, fns in os.walk(os.path.join(tmp, "marka")):
        if "index.html" not in fns:
            continue
        rel = os.path.relpath(dirpath, tmp).replace(os.sep, "/")
        if rel.count("/") != 1 or not os.path.exists(os.path.join(dirpath, "parcalar.json")):
            continue
        with open(os.path.join(dirpath, "index.html"), encoding="utf-8") as f:
            ham = f.read()
        marka_slug = rel.split("/")[-1]
        for _kat, _ek, href in KART_RE.findall(SCRIPT_RE.sub("", ham)):
            pid = href.strip("/").split("/")[-1] if href != "/urun//" else ""
            p = urunler_id.get(pid)
            if not pid or p is None:
                gecersiz_kimlik.append((rel, href))
                continue
            uye_sluglari = {mm._slug(evren.katla((x or "").strip()))
                            for x in (p.get("marka") or [])}
            if marka_slug not in uye_sluglari:
                yanlis_marka.append((rel, pid, sorted(uye_sluglari)))
        n_btn = len(BTN_RE.findall(ham))
        if aday is None or n_btn > aday[2]:
            aday = (rel, dirpath, n_btn, ham)
    if aday is None or aday[2] == 0:
        print("OLCULEMEDI: model butonlu marka sayfası bulunamadı")
        shutil.rmtree(tmp, ignore_errors=True)
        return 3, kapi
    rel, dirpath, n_btn, ham = aday
    govde = SCRIPT_RE.sub("", ham)
    with open(os.path.join(dirpath, "parcalar.json"), encoding="utf-8") as f:
        yuk = json.load(f)
    mm_manifest = MANIFEST_RE.search(ham)
    if mm_manifest is None:
        print("OLCULEMEDI: mmManifest bulunamadı (%s)" % rel)
        shutil.rmtree(tmp, ignore_errors=True)
        return 3, kapi
    manifest_metni = mm_manifest.group(1)
    manifest = json.loads(manifest_metni)
    sayaclar = [(b, k, int(n)) for b, k, n in SAYIM_RE.findall(govde)]
    erisim_sayaclari = [n for b, _k, n in sayaclar if b == "erisim"]

    ssr_kartlar = [{"kat": kat, "mm": (ek.split('data-mm="')[1].split('"')[0]
                                      if 'data-mm="' in ek else None),
                    "id": href.strip("/").split("/")[-1]}
                   for kat, ek, href in KART_RE.findall(govde)]
    cipler = [{"href": h, "katsay": k.replace("&quot;", '"'), "mm": ix}
              for h, k, ix in BTN_RE.findall(govde)]
    kategoriler = mm.kategori_evreni(index_html)
    kapsam_js = mm.kapsam_scripti(kategoriler)
    kapsam_js = kapsam_js[kapsam_js.index(mm._KAPSAM_JS_BAS):
                          kapsam_js.index(mm._KAPSAM_JS_SON)]

    # EDGE ŞEKLİ: `/katalog?ids=` tekil `gorsel` döner, `gorseller` dizisi YOK
    # (canlı ölçüldü: 100/100 ürün, 0 sapan alan). Şim canlı şekli taklit eder.
    urun_ix = {p.get("id"): p for p in products if p.get("id")}
    edge = {}
    for kalem in yuk["k"]:
        p = urun_ix.get(kalem[0])
        if p is None:
            continue
        imgs = ctx["images_of"](p)
        edge[kalem[0]] = {"id": p.get("id"), "baslik": p.get("baslik"),
                          "kategori": p.get("kategori"), "marka": p.get("marka") or [],
                          "fiyat": p.get("fiyat"), "tabanFiyat": 0,
                          "gorsel": imgs[0] if imgs else "",
                          "parametrik": bool(p.get("parametrik")), "altkategori": ""}
    veri = {
        "artimJs": mm._ARTIM_JS_GOVDE, "kapsamJs": kapsam_js,
        "manifest": manifest, "manifestMetni": manifest_metni,
        "kanonikYol": kanonik_yol, "kanonikParti": kanonik_parti,
        "yuk": yuk, "edge": edge,
        "ssrKartlar": ssr_kartlar, "cipler": cipler,
        "search": "", "pathname": "/" + rel + "/",
    }
    girdi = os.path.join(tmp, "artim-girdi.json")
    with open(girdi, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    harness = os.path.join(tmp, "artim-harness.js")
    with open(harness, "w", encoding="utf-8") as f:
        f.write(_HARNESS)
    try:
        cp = subprocess.run(["node", harness, girdi], capture_output=True, text=True,
                            timeout=900)
    except Exception as e:                                        # noqa: BLE001
        print("OLCULEMEDI: node koşturulamadı: %r" % (e,))
        shutil.rmtree(tmp, ignore_errors=True)
        return 3, kapi
    if cp.returncode != 0 or not cp.stdout.strip():
        print("OLCULEMEDI: node rc=%d %s" % (cp.returncode, cp.stderr[-500:]))
        shutil.rmtree(tmp, ignore_errors=True)
        return 3, kapi
    r = json.loads(cp.stdout.strip().splitlines()[-1])

    print("FIKSTUR: /%s/ (model butonu %d, SSR kart %d, yük %d kalem, toplam %s)"
          % (rel, len(cipler), len(ssr_kartlar), len(yuk["k"]), manifest["toplam"]))

    kapi.iddia("A1 MODUL KURULDU", bool(r.get("kuruldu")) and bool(r.get("domHazir")),
               "PRUVO_ARTIM / DOMContentLoaded yok: %r" % (r,))
    if not (r.get("kuruldu") and r.get("domHazir")):
        shutil.rmtree(tmp, ignore_errors=True)
        return 1, kapi

    # ---- KABUL: JS-SİZ HÂLDE SAYFA BOZULMAZ
    kapi.iddia("A2 JS-SIZ N KART GORUNUR",
               r.get("jssizKart") == len(ssr_kartlar) == min(mm.MARKA_KART_N,
                                                             manifest["toplam"]),
               "js-siz görünen %s, SSR kart %d, beklenen %d"
               % (r.get("jssizKart"), len(ssr_kartlar),
                  min(mm.MARKA_KART_N, manifest["toplam"])))
    kapi.iddia("A3 CIP JS-SIZ GERCEK MODEL BAGI",
               all(h.startswith("/marka/") and h.endswith("/") and h.count("/") == 4
                   for h in (r.get("cipHrefleri") or [])) and len(r.get("cipHrefleri") or []) > 0,
               "çip href'leri model sayfasına gitmiyor: %r"
               % ((r.get("cipHrefleri") or [])[:3],))
    kapi.iddia("A3b HER KART SAYFASININ MARKASINA AIT",
               not yanlis_marka,
               "yanlis marka kartlari: %r" % (yanlis_marka[:3],))
    kapi.iddia("A3c GECERSIZ KIMLIKLI KART YOK",
               not gecersiz_kimlik,
               "gecersiz kimlik kartlari: %r" % (gecersiz_kimlik[:3],))
    kapi.iddia("A3d BASLIK SAYACI ERISILEBILIR YUZEYI GOSTERIR",
               bool(erisim_sayaclari)
               and all(n == manifest["toplam"] for n in erisim_sayaclari),
               "sayac %r != erisilebilir yuzey %r (o an basilan %d DEGIL: baslik "
               "kullanicinin ERISEBILDIGINI gostermeli)"
               % (erisim_sayaclari, manifest.get("toplam"), len(ssr_kartlar)))
    kapi.iddia("A3d2 BASLIK SAYACI KENDI KIRILIMINDAN DOGAR",
               all(n == sum(json.loads(k.replace("&quot;", '"').replace("&amp;", "&")).values())
                   for _b, k, n in sayaclar),
               "sayac kendi kategori kirilimiyla ayristi: %r"
               % ([(b, n) for b, _k, n in sayaclar],))
    kapi.iddia("A3d3 KONTROL: TAVAN BU FIKSTURDE GERCEKTEN KIRPIYOR",
               manifest["toplam"] > len(ssr_kartlar),
               "secilen sayfada SSR kart %d == toplam %r: sayac ekseni bu fiksturde "
               "ayirt edici DEGIL (dejenere yesil)"
               % (len(ssr_kartlar), manifest.get("toplam")))

    # ---- KABUL: ÇİP SAYFA İÇİNDE FİLTRELER, ADRES DEĞİŞMEZ
    kapi.iddia("A4 CIP TIKLAMASI ONLENDI (preventDefault)", bool(r.get("cipOnlendi")),
               "tıklama önlenmedi -> tarayıcı model sayfasına GİDERDİ")
    kapi.iddia("A5 ADRES DEGISMEDI", r.get("adresDegisti") is False,
               "location.replace çağrıldı (hedef %r)" % (r.get("adresDegisti"),))
    kapi.iddia("A6 SSR KARTLARI SUZULDU (sayfa icinde)",
               (r.get("filtreSonrasiGizliSsr") or 0) > 0,
               "hiçbir SSR kart gizlenmedi: filtre çalışmıyor (gizli=%r)"
               % (r.get("filtreSonrasiGizliSsr"),))
    ilk_model_kalem = len([k for k in yuk["k"] if 0 in (k[2] or [])])
    kapi.iddia("A7 FILTRE MODELIN KALEMLERINI CIZDI",
               (r.get("filtreSonrasiEklenen") or 0) > 0
               and (r.get("filtreSonrasiEklenen") or 0) <= ilk_model_kalem,
               "çizilen %r, modelin kalemi %d" % (r.get("filtreSonrasiEklenen"),
                                                  ilk_model_kalem))
    kapi.iddia("A8 FILTRE DURUMU KULLANICIYA YAZILDI",
               "filtre" in (r.get("filtreDurum") or ""),
               "durum metni %r" % (r.get("filtreDurum"),))
    kapi.iddia("A9 AKTIF CIP ISARETLENDI", "mm-aktif" in (r.get("cipAktifSinif") or ""),
               "sınıf %r" % (r.get("cipAktifSinif"),))

    # ---- KABUL: "TÜMÜNÜ GÖSTER" TÜM KALEMLERİ BASAR
    bek_tumu = len(yuk["k"]) - manifest["basili"]
    kapi.iddia("A10 TUMUNU GOSTER KALANI CIZDI", r.get("tumuEklenen") == bek_tumu,
               "çizilen %r, beklenen %d (yük %d - basılı %d)"
               % (r.get("tumuEklenen"), bek_tumu, len(yuk["k"]), manifest["basili"]))
    kapi.iddia("A11 KART YUZEYI TOPLAMA ULASTI",
               (r.get("tumuEklenen") or 0) + manifest["basili"] == manifest["toplam"],
               "çizilen %r + basılı %d != toplam %d"
               % (r.get("tumuEklenen"), manifest["basili"], manifest["toplam"]))
    kapi.iddia("A12 TUMU SONRASI DUGME GIZLENDI", bool(r.get("dugmeGizli")),
               "buton görünür kaldı (kullanıcı boş tıklar)")
    kapi.iddia("A13 CIZILEN KARTLAR ISARETLI (data-artim)",
               r.get("artimIsaretli") == r.get("tumuEklenen"),
               "işaretli %r != çizilen %r (filtre sıfırlanınca temizlenemez)"
               % (r.get("artimIsaretli"), r.get("tumuEklenen")))
    # ---- KABUL: AĞIRLIK — ilk açılışta HİÇ istek yok, veri EDGE'den PARTİLİ geliyor
    kapi.iddia("A14a ILK ACILISTA HIC ISTEK YOK", r.get("acilistaFetch") == 0,
               "modül kurulur kurulmaz %r istek attı (tüm katalog indirme regresyonu)"
               % (r.get("acilistaFetch"),))
    kapi.iddia("A14b BILINMEYEN/TOPLU ADRESE ISTEK YOK", not (r.get("bilinmeyenAdres") or []),
               "edge/yük dışı adrese istek atıldı: %r" % ((r.get("bilinmeyenAdres") or [])[:3],))
    kapi.iddia("A14b2 MANIFEST EDGE YOLU KANONIK",
               manifest.get("yol") == kanonik_yol,
               "manifest yolu %r != index kanonu %r" % (manifest.get("yol"), kanonik_yol))
    kapi.iddia("A14c YUK BIR KEZ CEKILDI", r.get("yukCagri") == 1,
               "parcalar.json %r kez çekildi (1 olmalı; sonrası bellekten)"
               % (r.get("yukCagri"),))
    bek_parti = (bek_tumu + kanonik_parti - 1) // kanonik_parti if bek_tumu else 0
    kapi.iddia("A14d EDGE ISTEGI PARTILI VE GEREKTIGI KADAR",
               (r.get("edgeCagri") or 0) > 0
               and (r.get("enBuyukParti") or 0) <= kanonik_parti
               and manifest.get("parti") == kanonik_parti,
               "edge isteği %r, en büyük parti %r (tavan %r); beklenen parti sayısı ~%d"
               % (r.get("edgeCagri"), r.get("enBuyukParti"), kanonik_parti, bek_parti))
    kapi.iddia("A14e YALNIZ GEREKEN ID ISTENDI (tum katalog DEGIL)",
               (r.get("istenenTekil") or 0) == bek_tumu,
               "istenen tekil id %r != çizilecek kalem %d (fazlası tüm katalog çekmek olurdu)"
               % (r.get("istenenTekil"), bek_tumu))
    # ---- FETCH GERCEKTEN CAGRILDI VE KART CIZDI (yalniz "fonksiyon var" yeterli DEGIL)
    dk = r.get("durumKancasi") or {}
    kapi.iddia("A14f FETCH CAGRILDI + BELLEGE GIRDI + KART CIZDI",
               (dk.get("istek") or 0) >= 2 and (dk.get("bellek") or 0) == bek_tumu
               and (dk.get("cizilen") or 0) == manifest["toplam"]
               and (r.get("tumuEklenen") or 0) == bek_tumu,
               "istek=%r bellek=%r (beklenen %d) cizilen=%r (beklenen %d) eklenenKart=%r"
               % (dk.get("istek"), dk.get("bellek"), bek_tumu, dk.get("cizilen"),
                  manifest["toplam"], r.get("tumuEklenen")))
    # KONTROL: ölçüm dejenere değil — fikstür GERÇEKTEN kesirli (kalan > 0, basılı > 0)
    kapi.iddia("A15 KONTROL: FIKSTUR KESIRLI (olcum dejenere degil)",
               bek_tumu > 0 and manifest["basili"] > 0
               and manifest["toplam"] > manifest["basili"],
               "fikstür kesirli değil: basılı %d, kalan %d, toplam %d"
               % (manifest["basili"], bek_tumu, manifest["toplam"]))

    if dokum:
        print("DOKUM: %s" % json.dumps(r, ensure_ascii=False, sort_keys=True)[:900])
    shutil.rmtree(tmp, ignore_errors=True)
    return (0 if not kapi.dusen else 1), kapi


def main():
    rc, kapi = olc(dokum="--dokum" in sys.argv[1:])
    print("IDDIA=%d/%d DUSEN=%d" % (kapi.gecen, kapi.taban, len(kapi.dusen)))
    print("HUKUM=" + ("YESIL" if rc == 0 else ("KIRMIZI" if rc == 1 else "OLCULEMEDI")))
    return rc


if __name__ == "__main__":
    sys.exit(main())
