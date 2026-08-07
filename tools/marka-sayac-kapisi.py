#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA/MODEL SAYFASI SAYAÇ KAPISI — "N parça" DOĞRU BİRİMDE Mİ + MÜKERRER KART VAR MI.

🔴 NEDEN VAR (7 Ağu 2026, Okan: "marka sayfaları eksik görünüyor" — SESSİZ kusur):
  1. Kapsam şeridi bildirilen marka sayfasında (`?kategori=…`) "201 parça" yazıyordu; sayfadan
     ulaşılabilen gerçek küme 330 kalemdi. Sayaç YALNIZ `.card` düğümlerini sayıyordu, model
     butonlarının ARDINDAKİ parçaları saymıyordu. Aynı sayfanın meta'sı "330 parça" diyordu →
     tek sayfada İKİ FARKLI SAYI. Ekranda hata görünmüyor; müşteri kataloğu eksik sanıyor.
  2. `marka_only + ikincil + kucuk_urunler` birleşimi id bazında tekilleştirilmiyordu →
     31 marka sayfasında 282 fazla kart (aynı ürün iki kez).

KAPI NEYİ ÖLÇER (üretilen HTML üzerinden, ÖRNEKLEME YOK — 1022 marka adresinin TAMAMI):
  MUKERRER      : sayfadaki ham kart sayısı == tekil kart sayısı.
  KAYIP         : marka sayfasından ULAŞILABİLEN tekil küme == katalogdaki üyelik kümesi
                  (bağımsız türetme: `marka_uyelikleri`, gruplandır/sayfa üreticisi DEĞİL).
  TOPLAM        : SSR'de basılan `.mm-sayim-toplam` == ulaşılabilen tekil küme büyüklüğü.
  KIRILIM       : `data-katsay` kategori kırılımının toplamı == SSR toplamı (tek kaynak).
  KIRILIM_KAT   : kırılımdaki her kategori sayısı == ulaşılabilen kümenin o kategorideki sayısı.
  SIRA          : tekilleştirme kart sırasını BOZMAZ (kart id'leri katalog sırasına göre en
                  çok 3 monoton koşuya ayrılır: kucuk + marka_only + ikincil).
  JS_FILTRESIZ  : sayfanın KENDİ gömülü kapsam modülü, kapsam pasifken SSR toplamını verir.
  JS_SERIT      : `?kategori=K` ile şeridin BASTIĞI metin == "… — <beklenen> parça"; beklenen
                  HTML'den bağımsız sayılır (kart+model sayfası birleşimi, o kategoride).
  JS_ALTKUME    : şeritteki sayı görünen kart sayısından küçük olamaz.

Kullanım:
  python3 tools/marka-sayac-kapisi.py            # kapı (rc=0 yeşil, rc=1 kırmızı)
  python3 tools/marka-sayac-kapisi.py --iz       # yalnız kaynak izi (mutasyon kanıtı)
  python3 tools/marka-sayac-kapisi.py --ozet     # kapı + AUDI/mükerrer özet satırları
FAIL-CLOSED: ölçüm kurulamazsa rc=3 (ÖLÇÜLEMEDİ) — yeşil sayılmaz.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

KART_RE = re.compile(r'<div class="card" data-kat="([^"]*)"><a class="card-main" href="([^"]+)"')
BTN_RE = re.compile(r'<a class="mm-model-btn" href="([^"]+)" data-katsay="([^"]*)">')
TOPLAM_RE = re.compile(r'<p class="mm-toplam" data-katsay="([^"]*)">.*?'
                       r'<span class="mm-sayim-toplam">(\d+)</span>')
SAYIM_KART_RE = re.compile(r'<span class="mm-sayim-kart">(\d+)</span>')
SAYIM_MODEL_RE = re.compile(r'<span class="mm-sayim-model">(\d+)</span>')


def coz_katsay(ham):
    return json.loads(ham.replace("&quot;", '"').replace("&amp;", "&"))


def urun_id(href):
    return href.strip("/").split("/")[-1]


# --------------------------------------------------------------------------- node harness
_JS_HARNESS = r"""
"use strict";
const fs = require("fs");
const vm = require("vm");
const VERI = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

const ctx = { window: {}, JSON: JSON, String: String, Object: Object,
              URLSearchParams: URLSearchParams,
              console: {log(){}, warn(){}, error(){}} };
vm.runInNewContext(VERI.kapsamJs, ctx, {filename: "kapsam.js", timeout: 10000});
const K = ctx.window.PRUVO_KAPSAM;
if(!K){ console.log(JSON.stringify({hata: "PRUVO_KAPSAM tanimlanmadi"})); process.exit(0); }

function shim(sayfa){
  const kartlar = sayfa.kartlar.map((kat) => ({
    style: {display: ""}, getAttribute: (n) => (n === "data-kat" ? kat : null)}));
  const butonlar = sayfa.butonlar.map((b) => {
    const adet = {textContent: ""};
    const attrs = {"data-katsay": b.katsay, href: b.href};
    return {style: {display: ""}, attrs,
            getAttribute: (n) => (attrs[n] === undefined ? null : attrs[n]),
            setAttribute: (n, v) => { attrs[n] = v; },
            querySelector: (s) => (s === ".adet" ? adet : null)};
  });
  const toplamEl = sayfa.toplamKatsay === null ? [] : [{
    getAttribute: (n) => (n === "data-katsay" ? sayfa.toplamKatsay : null)}];
  const sayimToplam = {textContent: ""};
  const sayimKart = {textContent: ""};
  const sayimModel = {textContent: ""};
  const kutu = {
    kapsamNot: {style: {display: "none"}},
    kapsamNotMetin: {textContent: ""},
    kapsamNotSifirla: {attrs: {href: "./"},
                       getAttribute(n){ return this.attrs[n]; },
                       setAttribute(n, v){ this.attrs[n] = v; }},
    kapsamBos: {style: {display: "none"}}
  };
  const harita = {
    ".card[data-kat]": kartlar,
    ".mm-model-btn[data-katsay]": butonlar,
    ".mm-toplam[data-katsay]": toplamEl,
    "a[data-kapsam-tasi]": [],
    ".mm-sayim-kart": [sayimKart],
    ".mm-sayim-model": [sayimModel],
    ".mm-sayim-toplam": [sayimToplam]
  };
  return {dok: {querySelectorAll: (s) => (harita[s] || []),
                getElementById: (id) => (kutu[id] || null)},
          kartlar, kutu, sayimToplam};
}

// SENTETİK FAIL-CLOSED FİKSTÜRLERİ: gerçek sayfalarda kırılım HEP sağlamdır, bu yüzden
// "kırılım yok/bozuk/tutarsız" dalları gerçek katalogla ÖLÇÜLEMEZ (fail-open mutantı hayatta
// kalırdı). Bu fikstürler o dalları tek tek zorlar.
const sentetik = {};
for(const f of VERI.sentetik){
  const s = shim(f);
  K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(f.kategori), pathname: "/x/"});
  sentetik[f.ad] = {serit: s.kutu.kapsamNotMetin.textContent, rozet: s.sayimToplam.textContent};
}

const cikti = {sentetik: sentetik};
for(const yol of Object.keys(VERI.sayfalar)){
  const sayfa = VERI.sayfalar[yol];
  const kayit = {filtresiz: null, kategoriler: {}};
  // filtresiz: kapsam PASİF -> sayfaya dokunulmaz; kanonik toplam yine de okunabilmeli
  kayit.filtresiz = K.toplamla(shim(sayfa).dok, K.coz(null, VERI.kategoriler));
  for(const kat of sayfa.olcumKategorileri){
    const s = shim(sayfa);
    K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(kat), pathname: "/" + yol + "/"});
    kayit.kategoriler[kat] = {
      serit: s.kutu.kapsamNotMetin.textContent,
      rozet: s.sayimToplam.textContent,
      gorunenKart: s.kartlar.filter((k) => k.style.display !== "none").length
    };
  }
  cikti[yol] = kayit;
}
console.log(JSON.stringify(cikti));
"""


class Kapi:
    def __init__(self):
        self.gecen = 0
        self.dusen = []

    def iddia(self, kimlik, kosul, detay=""):
        if kosul:
            self.gecen += 1
        else:
            self.dusen.append(kimlik + ((" — " + detay) if detay else ""))

    @property
    def taban(self):
        return self.gecen + len(self.dusen)


def kaynak_izi():
    """Mutasyonun UYGULANDIĞINI kanıtlayan iz: ölçülen kaynak dosyaların sha1'i.
    (Aynı uzunlukta mutasyon + bytecode önbelleği tuzağı: mutant koşumu bu izi BASAR;
    iz değişmemişse mutasyon uygulanmamıştır ve o tur SAYILMAZ.)"""
    h = hashlib.sha1()
    for ad in ("marka_model_build.py",):
        with open(os.path.join(TOOLS, ad), "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def sayfalari_uret(tmp):
    import build                      # noqa: PLC0415
    import marka_model_build as mm    # noqa: PLC0415
    with open(os.path.join(build.ROOT, "urunler.json"), encoding="utf-8") as f:
        products = json.load(f)
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = tmp
    shutil.copy(os.path.join(build.ROOT, "index.html"), os.path.join(tmp, "index.html"))
    with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
        index_html = f.read()
    mm.uret(products, ctx)
    return products, mm, index_html


def tara(tmp):
    kok = os.path.join(tmp, "marka")
    sayfalar = {}
    for dirpath, _dn, filenames in os.walk(kok):
        if "index.html" not in filenames:
            continue
        rel = os.path.relpath(dirpath, tmp).replace(os.sep, "/")
        if rel == "marka":
            continue                          # /marka/ dizini: kart/kova yok
        with open(os.path.join(dirpath, "index.html"), encoding="utf-8") as f:
            page = f.read()
        kartlar = [(kat, urun_id(href)) for kat, href in KART_RE.findall(page)]
        butonlar = [(href, coz_katsay(ks)) for href, ks in BTN_RE.findall(page)]
        t = TOPLAM_RE.search(page)
        sayfalar[rel] = {
            "kartlar": kartlar,
            "butonlar": butonlar,
            "toplam_katsay": coz_katsay(t.group(1)) if t else None,
            "toplam_katsay_ham": t.group(1).replace("&quot;", '"') if t else None,
            "toplam": int(t.group(2)) if t else None,
            "sayim_kart": [int(x) for x in SAYIM_KART_RE.findall(page)],
            "sayim_model": [int(x) for x in SAYIM_MODEL_RE.findall(page)],
        }
    return sayfalar


def bagimsiz_uyelik(products, mm, index_html):
    """Katalogdaki GERÇEK marka üyeliği — sayfa üreticisinden BAĞIMSIZ türetme.
    index.html marka filtresiyle aynı yüklem (`marka_uyelikleri`); gruplandir/uret ÇAĞRILMAZ."""
    evren = mm.MarkaEvreni(index_html)
    ek = mm.cip_evreni_markalari(products, index_html)
    uyelik = {}
    for p in products:
        pid = p.get("id")
        if not pid:
            continue
        for kan in mm.marka_uyelikleri(p.get("marka") or [], evren, ek):
            uyelik.setdefault(kan, set()).add(pid)
    # SIRA iddiasının GİRDİSİ (iddiası değil): kovalar. Kapı tekilleştirmeyi KENDİ yazar.
    veri = mm.gruplandir(products, evren, ek)
    return uyelik, veri


def birim_iddialari(kapi):
    """BİRİM EKSENİ — kanonik sayma fonksiyonları, sayfa üretmeden.

    🔴 NEDEN AYRI VE ÖNCE KOŞAR: jeneratörün fail-closed ikiz kontrolü bir kusurda build'i
    DURDURUR; tek başına bırakılsa üç ayrı kusur da aynı "durdu" imzasını üretir ve batarya
    ayırt edemezdi ([[beyan-edilmis-survivor]]). Birim ekseni build'den ÖNCE koşar, bu yüzden
    her kusur kendi kimliğiyle düşer."""
    import marka_model_build as mm      # noqa: PLC0415
    a, b, c = {"id": "a"}, {"id": "b"}, {"id": "c"}
    a2 = {"id": "a"}
    kapi.iddia("BIRIM_TEKIL/mukerrer",
               [p["id"] for p in mm._tekil([a, b], [a2, c])] == ["a", "b", "c"],
               "mükerrer id düşmedi")
    kapi.iddia("BIRIM_TEKIL/sira",
               [p["id"] for p in mm._tekil([c, a, b])] == ["c", "a", "b"],
               "ilk görülen sıra bozuldu")
    kapi.iddia("BIRIM_KALEM/kova",
               [p["id"] for p in mm.sayfa_kalemleri([a], [[b], [c]])] == ["a", "b", "c"],
               "kova kalemleri toplama girmedi")
    kapi.iddia("BIRIM_KALEM/cakisma",
               len(mm.sayfa_kalemleri([a, b], [[a2, c]])) == 3,
               "kart ∩ kova çakışması iki kez sayıldı")


def marka_literal_iddialari(kapi, mm, index_html):
    """SINIF ONARIMI KAPISI (Okan hükmü): onarım TÜRETMEDE olmalı, marka-özel dalda değil.
    Onarımın dokunduğu her yüzeyde SABİT marka adı sayısı 0 olmalı — bir marka literali
    "bu sayfada çalışıyor" demektir, sınıfın kapandığı anlamına GELMEZ."""
    import inspect                       # noqa: PLC0415
    evren = mm.MarkaEvreni(index_html)
    adlar = sorted(set(evren.taninmis) | set(evren.marka_alias.keys())
                   | set(evren.marka_alias.values()), key=len, reverse=True)
    desen = re.compile(r"(?<![0-9A-Za-zÇĞİÖŞÜçğıöşü])(" +
                       "|".join(re.escape(a) for a in adlar if a) +
                       r")(?![0-9A-Za-zÇĞİÖŞÜçğıöşü])")
    hedefler = {
        "mm._tekil": inspect.getsource(mm._tekil),
        "mm.sayfa_kalemleri": inspect.getsource(mm.sayfa_kalemleri),
        "mm._toplam_bloku": inspect.getsource(mm._toplam_bloku),
        "mm._marka_sayfasi": inspect.getsource(mm._marka_sayfasi),
        "mm._model_sayfasi": inspect.getsource(mm._model_sayfasi),
        "mm.KAPSAM_JS": mm._KAPSAM_JS_GOVDE,
    }
    for ad in ("marka-sayac-kapisi.py", "marka-sayac-mutasyon.py"):
        with open(os.path.join(TOOLS, ad), encoding="utf-8") as f:
            hedefler["tools/" + ad] = f.read()
    for ad, metin in hedefler.items():
        vurus = sorted(set(desen.findall(metin)))
        kapi.iddia("MARKA_LITERAL/" + ad, not vurus, "sabit marka adı: %s" % (vurus,))


def olc(ozet=False, dokum=False, sayfa_detay=None):
    kapi = Kapi()
    birim_iddialari(kapi)
    tmp = tempfile.mkdtemp(prefix="mm-sayac-kapi-")
    try:
        products, mm, index_html = sayfalari_uret(tmp)
        sayfalar = tara(tmp)
    except SystemExit as e:
        # Jeneratörün FAIL-CLOSED ikiz kontrolü durdurdu: bu da bir ALARM kimliğidir
        # (mutasyon bataryası bunu ayrı bir düşüş imzası olarak sayar, "ölçülemedi" değil).
        kapi.iddia("FAIL_CLOSED/jenerator", False, str(e)[:120])
        print("FAIL-CLOSED: jeneratör durdu: %s" % (str(e)[:200],))
        return 1, kapi, {}
    marka_sayfalari = {k: v for k, v in sayfalar.items() if k.count("/") == 1}
    model_sayfalari = {k: v for k, v in sayfalar.items() if k.count("/") == 2}
    if len(marka_sayfalari) < 50 or len(model_sayfalari) < 500:
        print("OLCULEMEDI: sayfa evreni beklenenden küçük (marka=%d model=%d)"
              % (len(marka_sayfalari), len(model_sayfalari)))
        return 3, kapi, {}

    marka_literal_iddialari(kapi, mm, index_html)
    uyelik, veri = bagimsiz_uyelik(products, mm, index_html)
    slug_marka = {}
    for kan in uyelik:
        slug_marka.setdefault("marka/" + mm._slug(kan), kan)

    # ---------------------------------------------------------- ulaşılabilir tekil kümeler
    erisim = {}          # marka yolu -> {kategori: set(id)}
    for yol, s in marka_sayfalari.items():
        kume = {}
        for kat, pid in s["kartlar"]:
            kume.setdefault(kat, set()).add(pid)
        for href, _tablo in s["butonlar"]:
            mp = model_sayfalari.get(href.strip("/"))
            if mp is None:
                continue
            for kat, pid in mp["kartlar"]:
                kume.setdefault(kat, set()).add(pid)
        erisim[yol] = kume
    for yol, s in model_sayfalari.items():
        kume = {}
        for kat, pid in s["kartlar"]:
            kume.setdefault(kat, set()).add(pid)
        erisim[yol] = kume

    def tumu(kume):
        out = set()
        for v in kume.values():
            out |= v
        return out

    mukerrer_toplam = 0
    for yol, s in sayfalar.items():
        ham, tekil = len(s["kartlar"]), len(set(i for _k, i in s["kartlar"]))
        mukerrer_toplam += ham - tekil
        kapi.iddia("MUKERRER/" + yol, ham == tekil, "ham %d, tekil %d" % (ham, tekil))

    for yol, s in sayfalar.items():
        kume = tumu(erisim[yol])
        kapi.iddia("TOPLAM/" + yol, s["toplam"] == len(kume),
                   "SSR %s, ulaşılabilir %d" % (s["toplam"], len(kume)))
        tablo = s["toplam_katsay"] or {}
        kapi.iddia("KIRILIM/" + yol, sum(tablo.values()) == (s["toplam"] or -1),
                   "kırılım %d, SSR %s" % (sum(tablo.values()), s["toplam"]))
        beklenen_tablo = {k: len(v) for k, v in erisim[yol].items() if k}
        kapi.iddia("KIRILIM_KAT/" + yol, tablo == beklenen_tablo,
                   "gömülü %r != ölçülen %r" % (tablo, beklenen_tablo))

    for yol, marka in slug_marka.items():
        s = marka_sayfalari.get(yol)
        if s is None:
            continue                       # eşik altı marka: sayfa yok (ayrı eksen)
        kapi.iddia("KAYIP/" + yol, tumu(erisim[yol]) == uyelik[marka],
                   "sayfa %d, katalog %d, eksik %d, fazla %d"
                   % (len(tumu(erisim[yol])), len(uyelik[marka]),
                      len(uyelik[marka] - tumu(erisim[yol])),
                      len(tumu(erisim[yol]) - uyelik[marka])))

    # SIRA: tekilleştirme kart dizilimini yeniden DİZMEZ — İLK GÖRÜLEN KALIR.
    # 🔴 Kapı KENDİ tekilleştirmesini yazar (mm._tekil'i ÇAĞIRMAZ): jeneratörün fonksiyonunu
    # çağırsaydı "sırayı bozacak şekilde tekilleştir" mutantı kapıyı da bozar ve iddia
    # tautolojiye düşerdi (mutant yeşil geçerdi).
    def yerel_tekil(diziler):
        out, gor = [], set()
        for dz in diziler:
            for pid in dz:
                if pid in gor:
                    continue
                gor.add(pid)
                out.append(pid)
        return out

    for yol, s in marka_sayfalari.items():
        marka = slug_marka.get(yol)
        d = veri.get(marka) if marka else None
        if d is None:
            kapi.iddia("SIRA/" + yol, False, "marka kovası bulunamadı")
            continue
        gruplar = list(d["gruplar"].values())
        buyuk = [g for g in gruplar if mm.yayimlanir_mi(g)]
        yayimda = set()
        for g in buyuk:
            yayimda.update(p.get("id") for p in g["urunler"] if p.get("id"))
        kucuk, gor = [], set()
        for g in gruplar:
            if mm.yayimlanir_mi(g):
                continue
            for p in g["urunler"]:
                pid = p.get("id")
                if pid in yayimda or pid in gor:
                    continue
                gor.add(pid)
                kucuk.append(pid)
        beklenen = yerel_tekil([kucuk,
                                [p.get("id") for p in d["marka_only"]],
                                [p.get("id") for p in d.get("ikincil", [])]])
        gercek = [i for _k, i in s["kartlar"]]
        kapi.iddia("SIRA/" + yol, gercek == beklenen,
                   "kart dizilimi ayrıştı (sayfa %d, beklenen %d, ilk fark %s)"
                   % (len(gercek), len(beklenen),
                      next((n for n, (a, b) in enumerate(zip(gercek, beklenen)) if a != b),
                           "uzunluk")))

    # ------------------------------------------------------------------ istemci (node) ekseni
    kategoriler = mm.kategori_evreni(index_html)
    js = mm.kapsam_scripti(kategoriler)
    js = js[js.index(mm._KAPSAM_JS_BAS):js.index(mm._KAPSAM_JS_SON)]
    KAT = kategoriler[0]
    OLCULEMEDI = "Kapsam: yalnız %s kategorisi — parça sayısı ölçülemedi" % KAT
    sentetik = [
        # kırılım YOK -> sayı BASILMAZ (fail-open olsaydı 0/kart sayısı basardı)
        {"ad": "eksik", "kategori": KAT, "kartlar": [KAT, KAT], "butonlar": [],
         "toplamKatsay": None, "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım YOK + görünen kart 0 ama kovada 5 parça VAR: "0 parça" basmak tam da
        # bildirilen sessiz kusurdur. Tutarlılık kapısı (toplam < kart) burada devreye
        # GİREMEZ (kart 0) -> fail-open'a dönen bir düzeltme YALNIZ bu fikstürde yakalanır
        # ([[duzeltme-fail-open-cevirebilir]]).
        {"ad": "eksik_kovali", "kategori": KAT, "kartlar": ["Ofis"],
         "butonlar": [{"href": "/marka/x/y/", "katsay": '{"%s":5}' % KAT}],
         "toplamKatsay": None, "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım BOZUK JSON
        {"ad": "bozuk", "kategori": KAT, "kartlar": [KAT], "butonlar": [],
         "toplamKatsay": "{bozuk", "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım BOŞ metin
        {"ad": "bos", "kategori": KAT, "kartlar": [KAT], "butonlar": [],
         "toplamKatsay": "", "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım TUTARSIZ (toplam < görünen kart) -> bayat/bozuk veri, sayı BASILMAZ
        {"ad": "tutarsiz", "kategori": KAT, "kartlar": [KAT, KAT, KAT], "butonlar": [],
         "toplamKatsay": '{"%s":1}' % KAT, "serit": OLCULEMEDI, "rozet": "—"},
        # SAĞLAM kontrol: kova + kart, kapsam içindeki sayı basılır (hep-null mutantını öldürür)
        {"ad": "saglam", "kategori": KAT, "kartlar": [KAT, KAT, "Ofis"],
         "butonlar": [{"href": "/marka/x/y/", "katsay": '{"%s":5}' % KAT}],
         "toplamKatsay": '{"%s":7,"Ofis":1}' % KAT,
         "serit": "Kapsam: yalnız %s kategorisi — 7 parça" % KAT, "rozet": "7"},
    ]
    veri = {"kapsamJs": js, "kategoriler": kategoriler, "sentetik": sentetik, "sayfalar": {}}
    for yol, s in sayfalar.items():
        veri["sayfalar"][yol] = {
            "kartlar": [k for k, _i in s["kartlar"]],
            "butonlar": [{"href": h, "katsay": json.dumps(t, ensure_ascii=False,
                                                         separators=(",", ":"), sort_keys=True)}
                         for h, t in s["butonlar"]],
            "toplamKatsay": s["toplam_katsay_ham"],
            "olcumKategorileri": sorted(k for k in erisim[yol] if k),
        }
    girdi = os.path.join(tmp, "js-girdi.json")
    with open(girdi, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    harness = os.path.join(tmp, "harness.js")
    with open(harness, "w", encoding="utf-8") as f:
        f.write(_JS_HARNESS)
    try:
        cp = subprocess.run(["node", harness, girdi], capture_output=True, text=True,
                            timeout=600)
    except Exception as e:                                   # noqa: BLE001
        print("OLCULEMEDI: node koşturulamadı: %r" % (e,))
        return 3, kapi, {}
    if cp.returncode != 0 or not cp.stdout.strip():
        print("OLCULEMEDI: node rc=%d %s" % (cp.returncode, cp.stderr[-400:]))
        return 3, kapi, {}
    js_sonuc = json.loads(cp.stdout)
    if "hata" in js_sonuc:
        print("OLCULEMEDI: %s" % js_sonuc["hata"])
        return 3, kapi, {}

    for f in sentetik:
        r = (js_sonuc.get("sentetik") or {}).get(f["ad"]) or {}
        kapi.iddia("JS_SENTETIK/%s/serit" % f["ad"], r.get("serit") == f["serit"],
                   "şerit %r != %r" % (r.get("serit"), f["serit"]))
        kapi.iddia("JS_SENTETIK/%s/rozet" % f["ad"], r.get("rozet") == f["rozet"],
                   "rozet %r != %r" % (r.get("rozet"), f["rozet"]))

    for yol, s in sayfalar.items():
        r = js_sonuc.get(yol)
        if r is None:
            kapi.iddia("JS_FILTRESIZ/" + yol, False, "node çıktısı yok")
            continue
        kapi.iddia("JS_FILTRESIZ/" + yol, r["filtresiz"] == s["toplam"],
                   "js %s, SSR %s" % (r["filtresiz"], s["toplam"]))
        for kat, olcum in r["kategoriler"].items():
            bek = len(erisim[yol].get(kat, ()))
            kapi.iddia("JS_SERIT/%s/%s" % (yol, kat),
                       olcum["serit"] == ("Kapsam: yalnız %s kategorisi — %d parça" % (kat, bek)),
                       "şerit %r, beklenen %d parça" % (olcum["serit"], bek))
            kapi.iddia("JS_ROZET/%s/%s" % (yol, kat), olcum["rozet"] == str(bek),
                       "rozet %r != %d" % (olcum["rozet"], bek))
            kapi.iddia("JS_ALTKUME/%s/%s" % (yol, kat), olcum["gorunenKart"] <= bek,
                       "görünen kart %d > toplam %d" % (olcum["gorunenKart"], bek))

    bilgi = {"mukerrer": mukerrer_toplam, "marka": len(marka_sayfalari),
             "model": len(model_sayfalari), "tmp": tmp}

    # ---------------------------------------------------------------- BÜYÜKLÜK KATMANLARI
    # 🔴 TOPLAM TEKİL SAPMAYI GİZLER: onarım yalnız çok-ürünlü markalarda çalışıyorsa
    # "0 sapan" toplamı bunu ÖRTER. Katman katman ayrı basılır; sapanlar marka bazında.
    def katman(n):
        if n > 500:
            return "cok(>500)"
        if n >= 50:
            return "orta(50-500)"
        if n > 1:
            return "az(2-49)"
        return "tekil(1)"

    katmanlar = {}
    for yol, s in sayfalar.items():
        seviye = "marka" if yol.count("/") == 1 else "model"
        kt = katman(len(tumu(erisim[yol])))
        d0 = katmanlar.setdefault((seviye, kt), {"sayfa": 0, "sapan": [], "mukerrer": 0})
        d0["sayfa"] += 1
        d0["mukerrer"] += len(s["kartlar"]) - len(set(i for _k, i in s["kartlar"]))
        gercek = len(tumu(erisim[yol]))
        if s["toplam"] != gercek:
            d0["sapan"].append("%s (%s!=%d)" % (yol, s["toplam"], gercek))
        elif yol.count("/") == 1:
            marka = slug_marka.get(yol)
            if marka and tumu(erisim[yol]) != uyelik.get(marka, set()):
                d0["sapan"].append("%s (katalog ayrışması)" % yol)
    bilgi["katmanlar"] = katmanlar

    if dokum:
        print("== BÜYÜKLÜK KATMANLARI (üretilen == gerçek) ==")
        for anahtar in sorted(katmanlar):
            d0 = katmanlar[anahtar]
            print("  %-6s %-13s sayfa=%4d  sapan=%d  mukerrer_kart=%d%s"
                  % (anahtar[0], anahtar[1], d0["sayfa"], len(d0["sapan"]), d0["mukerrer"],
                     ("  -> " + ", ".join(d0["sapan"][:10])) if d0["sapan"] else ""))
    if sayfa_detay:
        s = sayfalar.get(sayfa_detay)
        if s is None:
            print("DETAY: %s bulunamadı" % sayfa_detay)
        else:
            print("DETAY %s: SSR_toplam=%s kart=%d tekil_kart=%d kirilim=%s"
                  % (sayfa_detay, s["toplam"], len(s["kartlar"]),
                     len(set(i for _k, i in s["kartlar"])),
                     json.dumps(s["toplam_katsay"], ensure_ascii=False, sort_keys=True)))
    shutil.rmtree(tmp, ignore_errors=True)
    return (0 if not kapi.dusen else 1), kapi, bilgi


def main():
    if "--iz" in sys.argv[1:]:
        print("IZ=" + kaynak_izi())
        return 0
    argv = sys.argv[1:]
    detay = argv[argv.index("--sayfa") + 1] if "--sayfa" in argv else None
    rc, kapi, bilgi = olc(dokum="--dokum" in argv, sayfa_detay=detay)
    for d in kapi.dusen[:40]:
        print("  DUSEN  " + d)
    if len(kapi.dusen) > 40:
        print("  ... (+%d düşen daha)" % (len(kapi.dusen) - 40))
    # AİLE İMZASI: mutasyon bataryası mutantları BUNUNLA ayırt eder (çıkış kodu DEĞİL —
    # iki farklı kusur da rc=1 verir; ayrışmayan imza "aynı iddiayı düşürdüler" demektir).
    aile = {}
    for d in kapi.dusen:
        aile[d.split("/")[0]] = aile.get(d.split("/")[0], 0) + 1
    print("AILELER=" + (",".join("%s:%d" % kv for kv in sorted(aile.items())) or "-"))
    print("IZ=" + kaynak_izi())
    print("IDDIA=%d/%d  DUSEN=%d  MUKERRER_KART=%s  SAYFA=marka %s + model %s"
          % (kapi.gecen, kapi.taban, len(kapi.dusen), bilgi.get("mukerrer"),
             bilgi.get("marka"), bilgi.get("model")))
    print("HUKUM=" + ("YESIL" if rc == 0 else ("KIRMIZI" if rc == 1 else "OLCULEMEDI")))
    return rc


if __name__ == "__main__":
    sys.exit(main())
