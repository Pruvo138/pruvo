#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAMPA URETILEBILIRLIK OLCUMU — `rampa` ailesinin SATISA ACILABILIRLIK dayanagi.

NEDEN VAR: bir aile satisa acilirken bu depoda uzun sure TEK soru soruluyordu —
"fiyat dogru mu". `petek`/`cetvel`/`kase` tam bu yuzden URETILEMEZ kombinasyonlarla
satisa acik kaldi (uretilemez oran %50,0 / %66,7 / %83,3; 60.000 kurusa kadar
tahsil edilebiliyordu). IKINCI soru sorulmadan bir aile acilamaz:
"bu parametre kutusunun HER noktasi uretilebilir mi?"
Bu arac o ikinci soruyu `rampa` icin OLCER (rulman turundaki olcumun emsali:
jenerator/test/rulman-uretilebilirlik-olcum.py).

OLCULEN EKSENLER
  1. IZGARA         — semanin ILAN ETTIGI parametre kutusu, kol kol, nokta sayisiyla.
  2. URETILEMEZ     — sema kapisindan (KONF.dogrula) GECEN noktalarin kaci uretim
                      ucunda (OpenSCAD assert -> 422) reddediliyor. Kol kol.
  3. ASIRI RED      — TERS EKSEN: motorun URETEBILDIGI ama semanin REDDETTIGI
                      kombinasyonlar (kutu disi sonda kumesi). Varsa SATIS KAYBIDIR.
  4. KAPALI FORM    — hacim.js `rampa` fonksiyonunun GERCEK render hacmine karsi
                      sapmasi (fiyat bu formulden cikar).
  5. KISIT          — semada `kisitlar` blogu var mi (A3 kurali: kisiti olan aile
                      HACIM_DOGRULANMIS_AILELER'e konursa vaat kapisi kirmizi yakar).
  6. FIYAT KAPISI   — parametrikFiyatKurus("rampa", ...) BUGUN ne donuyor + kapinin
                      kor olmadigini gosteren KONTROL ailesi.
  7. FIYAT ARALIGI  — acilirsa musterinin gorecegi kurus araligi ve 3x tavan.

KABUL OLCUTU = CIKIS KODU DEGIL, BASILAN IDDIA SAYISI + ISARET SARTI.
Koşum sonunda "IDDIA TOPLAM: n  (KIRMIZI: k)" satiri basilir. Kabul:
  n >= BEKLENEN_IDDIA  VE  k == 0.
(Cokme de sifir-disi cikis kodu verir; iddia sayisi olmadan "kirmizi" ile "hic
olcmedi" birbirine karisir -> [[mutasyon-kaniti-yeniden-uretilebilir]].)

FAIL-CLOSED: gizli uretim paketi (uretim eslemesi + motorun .scad kaynagi) ya da
openscad yoksa OLCULEMEDI -> exit 3, "yesil" SAYILMAZ. Render edilen nokta 0 ise de
exit 3 ("uretilemez = 0" hukmu OLCULMEMIS bir sifira dayanamaz).
Motor dosya adi/tedarikci bu dosyada ANILMAZ; eslem dosyasindan okunur.

Kullanim:
  python3 jenerator/test/rampa-uretilebilirlik-olcum.py
  python3 jenerator/test/rampa-uretilebilirlik-olcum.py --ornek 300     # hizli tur
  python3 jenerator/test/rampa-uretilebilirlik-olcum.py --kosesiz       # kose alt-uzayi atla
  python3 jenerator/test/rampa-uretilebilirlik-olcum.py --mutasyon      # mutasyon bataryasi
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_BU_DIZIN = os.path.dirname(os.path.abspath(__file__))
# PRUVO_REPO: mutasyon bataryasi bu dosyanin KOPYASINI gecici dizinde kosturur —
# kopyanin konumundan depo koku TURETILEMEZ. Ortam degiskeni verilmezse davranis
# birebir eski hali (bu dosya jenerator/test altindadir).
REPO = os.environ.get("PRUVO_REPO") or os.path.dirname(os.path.dirname(_BU_DIZIN))
TEST_DIR = os.path.join(REPO, "jenerator", "test")
OLCULEMEDI = 3
URUN_ID = "olcuye-ozel-ramp-sim-takoz"
AILE = "rampa"                 # sema.hacimFormulu
KONTROL_AILE = "profil"        # allowlist'te OLAN aile — fiyat kapisi kor mu degil mi
SAPMA_SINIRI = 3.0             # % (isletme kurali: %3 ustu aile satisa acilmaz)
SIKI_ESIK = 0.01               # % (bilgi amacli: kapali form ne kadar sıkı tutuyor)
BEKLENEN_IDDIA = 25

# ---------------------------------------------------------------------------
# IZGARA BEYANI — olculen kutu BURADA tanimlanir, raporda AYNEN basilir.
# Her eksen ya {aralik: [min, max, adim]} ya {liste: [...]}.
# "Olu" eksen (o kolda geometriye girmeyen) BILEREK dahildir: olu oldugu
# IDDIA EDILMEZ, OLCULUR (min/varsayilan/max uc degeriyle suprulur).
# ---------------------------------------------------------------------------
IZGARA = {
    "kollar": [
        {
            "ad": "A-yukseklik",
            "sabit": {"egim_yontemi": "yukseklik"},
            "eksenler": {
                "genislik":   {"aralik": [10, 150, 5]},     # 29
                "uzunluk":    {"aralik": [20, 250, 5]},     # 47
                "yukseklik":  {"aralik": [2, 100, 2]},      # 50
                "egim_acisi": {"liste": [4, 15, 30]},       # 3  (bu kolda OLU)
                "ust_yuzey":  {"liste": ["duz", "basamakli", "tirtikli"]},
            },
        },
        {
            "ad": "B-aci",
            "sabit": {"egim_yontemi": "aci"},
            "eksenler": {
                "genislik":   {"aralik": [10, 150, 5]},     # 29
                "uzunluk":    {"aralik": [20, 250, 5]},     # 47
                "yukseklik":  {"liste": [2, 20, 100]},      # 3  (bu kolda OLU)
                "egim_acisi": {"aralik": [4, 30, 1]},       # 27
                "ust_yuzey":  {"liste": ["duz", "basamakli", "tirtikli"]},
            },
        },
    ],
    # Kose alt-uzayi: her sayisal eksenin {min, varsayilan, max} ucu x tum sayimlar.
    # %100 render edilir (orneklemeye BIRAKILMAZ).
    "koseler": {
        "genislik": [10, 40, 150],
        "uzunluk": [20, 80, 250],
        "yukseklik": [2, 20, 100],
        "egim_acisi": [4, 15, 30],
        "ust_yuzey": ["duz", "basamakli", "tirtikli"],
    },
    "varsayilan": {"genislik": 40, "uzunluk": 80, "yukseklik": 20,
                   "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "duz"},
}

# ---------------------------------------------------------------------------
# SONDA KUMESI (kutu DISI) — ASIRI RED ekseni.
# Sema bunlarin HEPSINI reddeder (aralik/adim/enum ihlali). Soru: motor
# uretebiliyor mu? Uretebiliyorsa o nokta SATIS KAYBI adayidir.
# Kume ayrica URETILEMEZ DEDEKTORUNUN POZITIF KONTROLUDUR: icinde motorun
# GERCEKTEN reddettigi noktalar (yukseklik=0, aci=0/90) vardir — dedektor
# hep "uretilebilir" deseydi bu eksen sifir cikar ve korlugu gorunurdu.
# ---------------------------------------------------------------------------
SONDA = {
    "aralik_disi": {
        "genislik":   [1, 5, 9, 151, 200, 300],
        "uzunluk":    [1, 5, 19, 251, 400, 600],
        "yukseklik":  [0, 0.5, 1, 1.9, 101, 200, 400],
        "egim_acisi": [0, 1, 2, 3, 31, 45, 60, 89, 90],
    },
    "adim_disi": {
        "genislik": [40.5], "uzunluk": [80.5],
        "yukseklik": [20.5], "egim_acisi": [15.5],
    },
    "enum_disi": [
        {"ust_yuzey": "kabartma"},
        {"ust_yuzey": "flat"},
        {"egim_yontemi": "otomatik"},
    ],
}

# ---------------------------------------------------------------------------
NODE_PROGRAM = r"""
"use strict";
var path = require("path"), fs = require("fs");
var REPO = process.argv[2];
var KONF = require(path.join(REPO, "jenerator", "konfigurator.js"));
var HACIM = require(path.join(REPO, "jenerator", "hacim.js"));
require(path.join(REPO, "secenekler.js"));
var SEC = globalThis.PRUVO_SECENEK;
var istek = JSON.parse(fs.readFileSync(0, "utf8"));
var sema = JSON.parse(fs.readFileSync(istek.sema_yolu, "utf8"));

function eksenDegerleri(t) {
  if (t.liste) { return t.liste.slice(); }
  var a = t.aralik, out = [], n = Math.round((a[1] - a[0]) / a[2]);
  for (var i = 0; i <= n; i++) { out.push(Math.round((a[0] + i * a[2]) * 1e6) / 1e6); }
  return out;
}
function lcg(s) { return function () { s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648; }; }

function nokta(kol, g, u, y, ac, yz) {
  var p = {genislik: g, uzunluk: u, yukseklik: y, egim_acisi: ac, ust_yuzey: yz};
  for (var k in kol.sabit) { if (kol.sabit.hasOwnProperty(k)) { p[k] = kol.sabit[k]; } }
  return p;
}

if (istek.gorev === "izgara") {
  var spec = istek.izgara, rasgele = lcg(istek.tohum), k = istek.ornek_kova;
  var kovalar = {}, toplam = 0, gecerli = 0, gecersiz = 0;
  var hacimMin = null, hacimMax = null, hacimMinP = null, hacimMaxP = null;
  spec.kollar.forEach(function (kol) {
    var E = kol.eksenler;
    var G = eksenDegerleri(E.genislik), U = eksenDegerleri(E.uzunluk);
    var Y = eksenDegerleri(E.yukseklik), A = eksenDegerleri(E.egim_acisi);
    var S = eksenDegerleri(E.ust_yuzey);
    S.forEach(function (yz) {
      var anahtar = kol.ad + "|" + yz;
      kovalar[anahtar] = {ad: anahtar, nokta: 0, gecerli: 0, gecersiz: 0,
                          gorulen: 0, ornek: []};
    });
    G.forEach(function (g) { U.forEach(function (u) { Y.forEach(function (y) {
      A.forEach(function (ac) { S.forEach(function (yz) {
        var p = nokta(kol, g, u, y, ac, yz);
        var kv = kovalar[kol.ad + "|" + yz];
        var d = KONF.dogrula(sema, p);
        toplam++; kv.nokta++;
        if (d.gecerli) { gecerli++; kv.gecerli++; } else { gecersiz++; kv.gecersiz++; }
        var h = HACIM.rampa(p);
        if (hacimMin === null || h < hacimMin) { hacimMin = h; hacimMinP = p; }
        if (hacimMax === null || h > hacimMax) { hacimMax = h; hacimMaxP = p; }
        if (!d.gecerli) { return; }               /* ornekleme SADECE kapidan gecenden */
        kv.gorulen++;
        if (kv.ornek.length < k) { kv.ornek.push(p); }
        else {
          var j = Math.floor(rasgele() * kv.gorulen);
          if (j < k) { kv.ornek[j] = p; }
        }
      }); });
    }); }); });
  });
  var kose = [], KS = spec.koseler;
  spec.kollar.forEach(function (kol) {
    KS.genislik.forEach(function (g) { KS.uzunluk.forEach(function (u) {
      KS.yukseklik.forEach(function (y) { KS.egim_acisi.forEach(function (ac) {
        KS.ust_yuzey.forEach(function (yz) {
          var p = nokta(kol, g, u, y, ac, yz);
          kose.push({p: p, kova: kol.ad + "|" + yz,
                     gecerli: KONF.dogrula(sema, p).gecerli, hacim: HACIM.rampa(p)});
        });
      }); });
    }); });
  });
  var ornekler = [];
  Object.keys(kovalar).forEach(function (a) {
    kovalar[a].ornek.forEach(function (p) {
      ornekler.push({p: p, kova: a, gecerli: true, hacim: HACIM.rampa(p)});
    });
    delete kovalar[a].ornek;
  });
  process.stdout.write(JSON.stringify({
    toplam: toplam, gecerli: gecerli, gecersiz: gecersiz,
    kovalar: kovalar, ornekler: ornekler, koseler: kose,
    hacim_min: hacimMin, hacim_min_p: hacimMinP,
    hacim_max: hacimMax, hacim_max_p: hacimMaxP
  }));
} else if (istek.gorev === "sonda") {
  var cikti = istek.noktalar.map(function (p) {
    var d = KONF.dogrula(sema, p), h = null;
    try { h = HACIM.rampa(KONF.hacimGirdisi(sema, p)); } catch (e) { h = null; }
    return {p: p, gecerli: d.gecerli, hatalar: Object.keys(d.hatalar), hacim: h};
  });
  process.stdout.write(JSON.stringify(cikti));
} else if (istek.gorev === "fiyat") {
  var tabanTL = sema.tabanFiyatTL, tabanH = sema.tabanHacimMm3;
  var out = {taban_tl: tabanTL, taban_hacim: tabanH, tavan_kurus: tabanTL * 100 * 3};
  out.kisitlar_var = Object.prototype.hasOwnProperty.call(sema, "kisitlar");
  out.allowlist = Object.keys(SEC.HACIM_DOGRULANMIS_AILELER);
  out.bugun_varsayilan = SEC.parametrikFiyatKurus(
    istek.aile, tabanTL, tabanH, istek.hacim_varsayilan, "PLA", "Siyah");
  out.kontrol_aile = SEC.parametrikFiyatKurus(
    istek.kontrol, tabanTL, tabanH, istek.hacim_varsayilan, "PLA", "Siyah");
  /* ACILIRSA senaryosu: allowlist'e SADECE BELLEKTE gecici kayit; dosya
     DEGISMEZ. Ayni fonksiyon, ayni kod yolu — ikinci bir fiyat formulu YAZILMAZ
     ([[ikiz-tanim-sessiz-ayrisma]]). */
  SEC.HACIM_DOGRULANMIS_AILELER[istek.aile] = 0;
  out.acilirsa = {
    varsayilan_pla_siyah: SEC.parametrikFiyatKurus(
      istek.aile, tabanTL, tabanH, istek.hacim_varsayilan, "PLA", "Siyah"),
    varsayilan_asa_diger: SEC.parametrikFiyatKurus(
      istek.aile, tabanTL, tabanH, istek.hacim_varsayilan, "ASA", "Diğer"),
    asgari_pla_siyah: SEC.parametrikFiyatKurus(
      istek.aile, tabanTL, tabanH, istek.hacim_min, "PLA", "Siyah"),
    azami_pla_siyah: SEC.parametrikFiyatKurus(
      istek.aile, tabanTL, tabanH, istek.hacim_max, "PLA", "Siyah"),
    azami_asa_diger: SEC.parametrikFiyatKurus(
      istek.aile, tabanTL, tabanH, istek.hacim_max, "ASA", "Diğer")
  };
  delete SEC.HACIM_DOGRULANMIS_AILELER[istek.aile];
  out.geri_alindi = SEC.parametrikFiyatKurus(
    istek.aile, tabanTL, tabanH, istek.hacim_varsayilan, "PLA", "Siyah");
  process.stdout.write(JSON.stringify(out));
} else {
  process.stderr.write("bilinmeyen gorev\n");
  process.exit(2);
}
"""


class Rapor(object):
    """IDDIA sayaci — kabul olcutu CIKIS KODU DEGIL, bu sayac + isaret sarti."""

    def __init__(self):
        self.n = 0
        self.kirmizi = 0
        self.satirlar = []

    def iddia(self, ad, kosul, olculen):
        self.n += 1
        isaret = "OK  " if kosul else "KIRMIZI"
        if not kosul:
            self.kirmizi += 1
        satir = "IDDIA %2d [%s] %s -> %s" % (self.n, isaret, ad, olculen)
        print(satir)
        self.satirlar.append(satir)

    def bilgi(self, metin):
        print("        %s" % metin)


def olculemedi(sebep):
    print("OLCULEMEDI: %s" % sebep)
    sys.exit(OLCULEMEDI)


def paket_yukle():
    """(server modulu, eslem_ailesi, scad_yolu) — yoksa OLCULEMEDI."""
    derleyici = os.environ.get("PRUVO_ONIZLEME_DIR",
                               os.path.join(REPO, "onizleme", "derleyici"))
    server_yol = os.path.join(derleyici, "server.py")
    eslem_yol = os.path.join(derleyici, "eslem-ozel.json")
    for yol in (server_yol, eslem_yol):
        if not os.path.exists(yol):
            olculemedi("gizli uretim paketi yok (%s). R2'deki paketten geri alin."
                       % os.path.basename(yol))
    spec = importlib.util.spec_from_file_location("onizleme_server", server_yol)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    eslem = json.load(io.open(eslem_yol, encoding="utf-8"))["aileler"]
    aile = eslem.get(URUN_ID)
    if not aile:
        olculemedi("uretim esleminde %s yok" % URUN_ID)
    adaylar = [derleyici, os.environ.get("PRUVO_UYELIK_DIR",
                                         os.path.join(REPO, ".uyelik-kodlar"))]
    for d in adaylar:
        scad = os.path.join(d, aile["scad"])
        if os.path.exists(scad):
            return server, aile, scad
    olculemedi("uretim motoru .scad kaynagi yok (%s)" % " | ".join(adaylar))


def openscad_yolu():
    sys.path.insert(0, TEST_DIR)
    import dogrula
    return dogrula.openscad_yolu()


def node_cagir(istek):
    js = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    js.write(NODE_PROGRAM)
    js.close()
    try:
        p = subprocess.run(["node", js.name, REPO], input=json.dumps(istek),
                           capture_output=True, text=True)
    finally:
        os.unlink(js.name)
    if p.returncode != 0:
        olculemedi("node kolu kosulamadi (%s): %s" % (istek.get("gorev"), p.stderr[:400]))
    return json.loads(p.stdout)


def sonda_noktalari():
    """Kutu DISI sonda kumesi — beyan SONDA sabitinden turer."""
    vars_ = IZGARA["varsayilan"]
    out = []
    for yz in IZGARA["koseler"]["ust_yuzey"]:
        for ad, degerler in sorted(SONDA["aralik_disi"].items()):
            for d in degerler:
                p = dict(vars_)
                p["ust_yuzey"] = yz
                p[ad] = d
                if ad == "egim_acisi":
                    p["egim_yontemi"] = "aci"
                out.append({"sinif": "aralik-disi:" + ad, "p": p})
        for ad, degerler in sorted(SONDA["adim_disi"].items()):
            for d in degerler:
                p = dict(vars_)
                p["ust_yuzey"] = yz
                p[ad] = d
                if ad == "egim_acisi":
                    p["egim_yontemi"] = "aci"
                out.append({"sinif": "adim-disi:" + ad, "p": p})
    for ihlal in SONDA["enum_disi"]:
        p = dict(vars_)
        p.update(ihlal)
        out.append({"sinif": "enum-disi:" + ",".join(sorted(ihlal)), "p": p})
    return out


def render(server, aile, scad, openscad, tmp, p, i):
    """(-> 'uretilir'|'uretilemez'|'eslem-reddi'|'hata', hacim_mm3|None, tani)"""
    bayraklar, sebep = server.d_bayraklari(aile, p)
    if bayraklar is None:
        return "eslem-reddi", None, sebep
    stl = os.path.join(tmp, "r%d.stl" % i)
    try:
        pr = subprocess.run([openscad, "-o", stl, "--export-format", "binstl"] +
                            server.OPENSCAD_EK_BAYRAKLAR + bayraklar + [scad],
                            capture_output=True, timeout=900)
    except subprocess.TimeoutExpired:
        return "hata", None, "zaman-asimi"
    h = pr.stderr.decode("utf-8", "replace")
    if pr.returncode == 0 and os.path.exists(stl):
        import stl_hacim
        v = stl_hacim.hacim(stl)
        os.unlink(stl)
        return "uretilir", v, ""
    if "ERROR: Assertion" in h or "assert" in h.lower():
        return "uretilemez", None, h.strip().splitlines()[-1][:140] if h.strip() else ""
    return "hata", None, (h.strip().splitlines() or [""])[-1][:140]


def yuzde_sapma(kapali, gercek):
    if gercek <= 0:
        return None
    return abs(kapali - gercek) / gercek * 100.0


def ana(a):
    sys.path.insert(0, TEST_DIR)
    R = Rapor()
    server, aile_eslem, scad = paket_yukle()
    openscad = openscad_yolu()
    if not openscad:
        olculemedi("openscad bulunamadi")
    sema_yolu = os.path.join(REPO, "jenerator", "urunler", "%s.json" % URUN_ID)
    if not os.path.exists(sema_yolu):
        olculemedi("sema yok: %s" % sema_yolu)
    sema = json.load(io.open(sema_yolu, encoding="utf-8"))

    print("=" * 78)
    print("RAMPA URETILEBILIRLIK OLCUMU  (urun %s / aile %s)" % (URUN_ID, AILE))
    print("=" * 78)

    # ---- 1) IZGARA + SEMA KAPISI -----------------------------------------
    izg = node_cagir({"gorev": "izgara", "sema_yolu": sema_yolu, "izgara": IZGARA,
                      "tohum": a.tohum, "ornek_kova": a.ornek})
    print("\n[1] IZGARA BEYANI")
    for kol in IZGARA["kollar"]:
        print("    kol %s  (%s)" % (kol["ad"], json.dumps(kol["sabit"], ensure_ascii=False)))
        for ad, t in sorted(kol["eksenler"].items()):
            print("        %-11s %s" % (ad, json.dumps(t, ensure_ascii=False)))
    print("    IZGARA NOKTA SAYISI: %d" % izg["toplam"])
    R.iddia("izgara noktasi > 0", izg["toplam"] > 0, "%d nokta" % izg["toplam"])
    R.iddia("sema kapisi kutu ICINDE hicbir noktayi reddetmiyor",
            izg["gecersiz"] == 0,
            "gecerli %d / gecersiz %d" % (izg["gecerli"], izg["gecersiz"]))

    # ---- 2+4) RENDER: URETILEMEZ ORAN + KAPALI FORM -----------------------
    noktalar = list(izg["ornekler"])
    if not a.kosesiz:
        noktalar += [k for k in izg["koseler"] if k["gecerli"]]
    tmp = tempfile.mkdtemp(prefix="rampa-olcum-")
    kova_sayac = {}
    en_kotu, en_kotu_p = 0.0, None
    siki_asan, hata_listesi, uretilemez_ornek = 0, [], []
    try:
        for i, kayit in enumerate(noktalar):
            p, kova = kayit["p"], kayit["kova"]
            s = kova_sayac.setdefault(kova, {"render": 0, "uretilir": 0,
                                             "uretilemez": 0, "hata": 0})
            hukum, hacim, tani = render(server, aile_eslem, scad, openscad, tmp, p, i)
            s["render"] += 1
            if hukum == "uretilir":
                s["uretilir"] += 1
                sap = yuzde_sapma(kayit["hacim"], hacim)
                if sap is not None:
                    if sap > en_kotu:
                        en_kotu, en_kotu_p = sap, (p, kayit["hacim"], hacim)
                    if sap > SIKI_ESIK:
                        siki_asan += 1
            elif hukum == "uretilemez":
                s["uretilemez"] += 1
                if len(uretilemez_ornek) < 5:
                    uretilemez_ornek.append((p, tani))
            else:
                s["hata"] += 1
                if len(hata_listesi) < 5:
                    hata_listesi.append((p, hukum, tani))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    render_toplam = sum(v["render"] for v in kova_sayac.values())
    uretilemez_toplam = sum(v["uretilemez"] for v in kova_sayac.values())
    hata_toplam = sum(v["hata"] for v in kova_sayac.values())

    print("\n[2] URETILEMEZ ORAN — kol kol (sema kapisindan GECEN noktalar)")
    # SIFIR-OLCUM FAIL-CLOSED: "uretilemez = 0" ile "hic olculmedi" ayni cikisa
    # dusmemeli ([[hukum-yanlis-birimde]], rulman turunda olculmus tuzak).
    if render_toplam == 0:
        olculemedi("render edilen nokta 0 — 'uretilemez = 0' hukmu verilemez")
    for kova in sorted(kova_sayac):
        v = kova_sayac[kova]
        oran = 100.0 * v["uretilemez"] / v["render"] if v["render"] else 0.0
        print("    %-22s render %4d | uretilir %4d | uretilemez %3d (%.4f%%) | hata %d"
              % (kova, v["render"], v["uretilir"], v["uretilemez"], oran, v["hata"]))
        R.iddia("kol %s uretilemez = 0" % kova, v["uretilemez"] == 0,
                "%d / %d render" % (v["uretilemez"], v["render"]))
    for p, tani in uretilemez_ornek:
        print("      [422] %s  %s" % (json.dumps(p, ensure_ascii=False), tani))
    R.iddia("render edilen nokta > 0 (sifir-olcum fail-closed)",
            render_toplam > 0, "%d render" % render_toplam)
    R.iddia("assert-disi derleme hatasi = 0", hata_toplam == 0,
            "%d hata" % hata_toplam)
    for p, hukum, tani in hata_listesi:
        print("      [HATA] %s %s %s" % (hukum, json.dumps(p, ensure_ascii=False), tani))
    print("    TOPLAM: %d render | uretilemez %d (%.4f%%)"
          % (render_toplam, uretilemez_toplam,
             (100.0 * uretilemez_toplam / render_toplam) if render_toplam else 0.0))

    # ---- 4) KAPALI FORM ---------------------------------------------------
    print("\n[4] KAPALI FORM (hacim.js `rampa`) vs GERCEK RENDER")
    print("    gercek render: %d | en kotu sapma: %.7f%%" % (render_toplam, en_kotu))
    if en_kotu_p:
        p, kf, gr = en_kotu_p
        print("    en kotu nokta: %s  kapali=%.4f gercek=%.4f"
              % (json.dumps(p, ensure_ascii=False), kf, gr))
    print("    sapmasi > %%%.2f olan nokta: %d" % (SIKI_ESIK, siki_asan))
    R.iddia("kapali form en kotu sapma < %%%.1f (isletme siniri)" % SAPMA_SINIRI,
            en_kotu < SAPMA_SINIRI, "%.7f%%" % en_kotu)
    R.iddia("kapali form ayrismasi (> %%%.2f) = 0" % SIKI_ESIK,
            siki_asan == 0, "%d nokta" % siki_asan)

    # ---- 3) ASIRI RED (ters eksen) ---------------------------------------
    print("\n[3] ASIRI RED — kutu DISI sonda kumesi (sema reddediyor, motor?)")
    sondalar = sonda_noktalari()
    hukumler = node_cagir({"gorev": "sonda", "sema_yolu": sema_yolu,
                           "noktalar": [s["p"] for s in sondalar]})
    tmp2 = tempfile.mkdtemp(prefix="rampa-sonda-")
    # 🔴 IKI AYRI RED TURU, IKI AYRI SAYAC (mutasyonla olculdu): `eslem-reddi`
    # uretim ESLEMESININ tablo-disi degeri reddetmesidir, motorun geometri
    # assert'i DEGILDIR. Tek sayacta toplandiklarinda "dedektor kor degil"
    # iddiasi eslem reddiyle YESIL kaliyordu — yani assert dedektorunu tamamen
    # oldurmek (M2) iddiayi kirmizi YAKMIYORDU ([[beyan-edilmis-survivor]]).
    asiri_red, motor_assert_reddi, eslem_reddi, sonda_hata = [], 0, 0, 0
    sinif_sayac = {}
    try:
        for i, (s, hk) in enumerate(zip(sondalar, hukumler)):
            if hk["gecerli"]:
                # Sema KABUL etti: bu nokta kutu disi sayilmaz, sonda gecersiz.
                sinif_sayac.setdefault(s["sinif"], {"n": 0, "sema_kabul": 0,
                                                    "motor_uretir": 0, "motor_red": 0})
                sinif_sayac[s["sinif"]]["n"] += 1
                sinif_sayac[s["sinif"]]["sema_kabul"] += 1
                continue
            c = sinif_sayac.setdefault(s["sinif"], {"n": 0, "sema_kabul": 0,
                                                    "motor_uretir": 0, "motor_red": 0})
            c["n"] += 1
            hukum, _, tani = render(server, aile_eslem, scad, openscad, tmp2, s["p"], i)
            if hukum == "uretilir":
                c["motor_uretir"] += 1
                asiri_red.append((s["sinif"], s["p"]))
            elif hukum == "uretilemez":
                c["motor_red"] += 1
                motor_assert_reddi += 1
            elif hukum == "eslem-reddi":
                c["motor_red"] += 1
                eslem_reddi += 1
            else:
                sonda_hata += 1
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    for sinif in sorted(sinif_sayac):
        c = sinif_sayac[sinif]
        print("    %-24s sonda %3d | sema-kabul %2d | motor URETIR %3d | motor RED %3d"
              % (sinif, c["n"], c["sema_kabul"], c["motor_uretir"], c["motor_red"]))
    print("    KUTU DISI ASIRI RED (satis kaybi adayi): %d" % len(asiri_red))
    for sinif, p in asiri_red[:8]:
        print("      [KAYIP] %s %s" % (sinif, json.dumps(p, ensure_ascii=False)))
    R.iddia("uretilemez dedektoru KOR DEGIL (sondada motor ASSERT reddi > 0)",
            motor_assert_reddi > 0, "%d assert reddi" % motor_assert_reddi)
    R.iddia("eslem kapisi KOR DEGIL (sondada eslem reddi > 0)",
            eslem_reddi > 0, "%d eslem reddi" % eslem_reddi)
    R.iddia("sonda kumesinde assert-disi hata = 0", sonda_hata == 0,
            "%d hata" % sonda_hata)
    R.iddia("KUTU ICI asiri red = 0 (sema kabul == motor kabul)",
            izg["gecersiz"] == 0 and uretilemez_toplam == 0,
            "kutu ici sema reddi %d, motor reddi %d"
            % (izg["gecersiz"], uretilemez_toplam))

    # ---- 5) KISIT BLOGU ---------------------------------------------------
    print("\n[5] SEMA `kisitlar` BLOGU (A3 kurali)")
    kisit_var = "kisitlar" in sema
    print("    %s icinde `kisitlar`: %s" % (os.path.basename(sema_yolu),
                                            "VAR" if kisit_var else "YOK"))
    R.iddia("semada `kisitlar` blogu YOK (A3 engeli olusmaz)",
            not kisit_var, "kisitlar %s" % ("VAR" if kisit_var else "YOK"))

    # ---- 6+7) FIYAT KAPISI + ARALIK --------------------------------------
    hv = None
    for k in izg["koseler"]:
        if k["p"] == IZGARA["varsayilan"]:
            hv = k["hacim"]
    if hv is None:
        hv = izg["hacim_min"]
    fy = node_cagir({"gorev": "fiyat", "sema_yolu": sema_yolu, "aile": AILE,
                     "kontrol": KONTROL_AILE, "hacim_varsayilan": hv,
                     "hacim_min": izg["hacim_min"], "hacim_max": izg["hacim_max"]})
    print("\n[6] FIYAT KAPISI (secenekler.js parametrikFiyatKurus)")
    print("    allowlist (%d aile): %s" % (len(fy["allowlist"]),
                                           ", ".join(sorted(fy["allowlist"]))))
    print("    parametrikFiyatKurus(\"%s\", ...) = %s" % (AILE, fy["bugun_varsayilan"]))
    print("    KONTROL parametrikFiyatKurus(\"%s\", ...) = %s"
          % (KONTROL_AILE, fy["kontrol_aile"]))
    R.iddia("bugun rampa tutar URETMIYOR (fail-closed)",
            fy["bugun_varsayilan"] is None, "%s" % fy["bugun_varsayilan"])
    R.iddia("fiyat kapisi KOR DEGIL: kontrol ailesi tutar uretiyor",
            isinstance(fy["kontrol_aile"], (int, float)), "%s kurus" % fy["kontrol_aile"])
    R.iddia("rampa allowlist'te DEGIL", AILE not in fy["allowlist"],
            "allowlist %d aile" % len(fy["allowlist"]))
    R.iddia("bellek ici allowlist kaydi GERI ALINDI (dosya degismedi)",
            fy["geri_alindi"] is None, "%s" % fy["geri_alindi"])

    print("\n[7] ACILIRSA FIYAT ARALIGI (taban %s TL / taban hacim %s mm3, tavan %d krs)"
          % (fy["taban_tl"], fy["taban_hacim"], fy["tavan_kurus"]))
    ac = fy["acilirsa"]
    print("    izgara hacim ARALIGI: %.1f .. %.1f mm3" % (izg["hacim_min"], izg["hacim_max"]))
    print("    varsayilan nokta hacmi: %.1f mm3" % hv)
    print("    varsayilan (PLA/Siyah) : %s krs" % ac["varsayilan_pla_siyah"])
    print("    varsayilan (ASA/Diger) : %s krs" % ac["varsayilan_asa_diger"])
    print("    asgari    (PLA/Siyah)  : %s krs" % ac["asgari_pla_siyah"])
    print("    azami     (PLA/Siyah)  : %s krs" % ac["azami_pla_siyah"])
    print("    azami     (ASA/Diger)  : %s krs" % ac["azami_asa_diger"])
    tavan = fy["tavan_kurus"]
    R.iddia("acilirsa varsayilan tutar URETILIR",
            isinstance(ac["varsayilan_pla_siyah"], (int, float)),
            "%s krs" % ac["varsayilan_pla_siyah"])
    R.iddia("azami tutar 3x tavani ASMIYOR",
            ac["azami_asa_diger"] is not None and ac["azami_asa_diger"] <= tavan,
            "%s <= %s krs" % (ac["azami_asa_diger"], tavan))
    R.iddia("azami tutar tavana DAYANIYOR (hacim carpani tavani asiyor)",
            ac["azami_pla_siyah"] == tavan,
            "%s krs (tavan %s)" % (ac["azami_pla_siyah"], tavan))
    R.iddia("asgari tutar taban fiyatin ALTINA inmiyor",
            ac["asgari_pla_siyah"] is not None and
            ac["asgari_pla_siyah"] >= fy["taban_tl"] * 100,
            "%s >= %s krs" % (ac["asgari_pla_siyah"], fy["taban_tl"] * 100))

    print("\n" + "=" * 78)
    print("IDDIA TOPLAM: %d  (KIRMIZI: %d)  | BEKLENEN >= %d"
          % (R.n, R.kirmizi, BEKLENEN_IDDIA))
    print("=" * 78)
    if R.n < BEKLENEN_IDDIA:
        print("KABUL DUSTU: basilan iddia sayisi beklenenin ALTINDA (eksik olcum).")
        return 1
    return 1 if R.kirmizi else 0


# ---------------------------------------------------------------------------
# MUTASYON BATARYASI — kanit REPODA durur ([[mutasyon-kaniti-yeniden-uretilebilir]]).
# Mutasyon CANLI dosyaya DEGIL, gecici KOPYAYA uygulanir.
#
# 🔴 CAPA ARAMASI YALNIZ "GOVDE"DE YAPILIR: mutant tablosu capa metinlerinin
# KENDISINI icerir; tum dosyada sayilsaydi her capa 2 kez bulunur ve batarya
# "BAYAT HARNESS" diye kendini kapatirdi (olculdu, ilk turda 4 mutant boyle dustu).
# GOVDE = MUT_SINIR isaretinden ONCEKI kisim.
#
# 🔴 HER MUTANT KENDI YOLUNU ICRA ETTIREN BAYRAKLA KOSAR: sifir-olcum kolu
# (`render_toplam == 0`) normal bayraklarla HIC calismaz — o mutant orada sag
# kalir ve "kapi yok" degil "yol hic yurunmedi" demektir (olculdu: M3 ilk turda
# SAG KALDI cunku --ornek 3 ile render sayisi 18'di). `bayraklar` alani bunu
# duzeltir, `olcut` ise hukmun hangi birimde verilecegini soyler.
#   olcut "iddia"      -> mutantta BEKLENEN capalar KIRMIZI yanmali
#   olcut "olculemedi" -> tabanda rc=3 (OLCULEMEDI) iken mutantta rc != 3 olmali
# ---------------------------------------------------------------------------
# Sinir isareti BILEREK parcali yazilir: tek parca yazilsaydi sabitin KENDISI de
# esleserdi ve isaret "2 kez bulundu" diye batarya kendini kapatirdi (olculdu).
MUT_SINIR = "# MUTASYON" + "-SINIRI (mutant tablosu bundan SONRA)"

# MUTASYON-SINIRI (mutant tablosu bundan SONRA)
MUTANTLAR = [
    # (ad, sinif, eski, yeni, beklenen_capalar, bayraklar, olcut)
    ("M1-kapali-form-x1.05", "OLDURUCU",
     'return abs(kapali - gercek) / gercek * 100.0',
     'return abs(kapali * 1.05 - gercek) / gercek * 100.0',
     ["kapali form en kotu sapma", "kapali form ayrismasi"], None, "iddia"),
    ("M2-uretilemez-dedektoru-kor", "OLDURUCU",
     'if "ERROR: Assertion" in h or "assert" in h.lower():',
     'if False:',
     ["motor ASSERT reddi"], None, "iddia"),
    ("M3-fail-closed-kolu-kalkti", "OLDURUCU",
     'if render_toplam == 0:\n        olculemedi(',
     'if False:\n        olculemedi(',
     [], ["--ornek", "0", "--kosesiz"], "olculemedi"),
    # SIFIR-OLCUMU tutan UC katman AYRI AYRI olculur ([[beyan-edilmis-survivor]]:
    # katmanlarin VEYA'si "savunma derinligi" KANITI degildir):
    #   1) fail-closed `olculemedi()` kolu        -> M3
    #   2) "render edilen nokta > 0" iddiasi      -> M3b (1 kalkinca 2 tasiyor mu)
    #   3) BEKLENEN_IDDIA tabani                  -> M3c (1+2 kalkinca 3 tasiyor mu)
    # M3c'de UCU BIRDEN kalkinca kosum TAM YESIL (rc=0, 0 kirmizi) donuyorsa
    # "uretilemez = 0" hukmu HIC render edilmeden satisa dayanak olabilirdi.
    ("M3b-iki-katman-kalkti", "OLDURUCU",
     ['if render_toplam == 0:\n        olculemedi(',
      'render_toplam > 0, "%d render" % render_toplam)'],
     ['if False:\n        olculemedi(',
      'render_toplam >= 0, "%d render" % render_toplam)'],
     [], ["--ornek", "0", "--kosesiz"], "hala-yesil-degil"),
    ("M3c-uc-katman-kalkti", "OLDURUCU",
     ['if render_toplam == 0:\n        olculemedi(',
      'render_toplam > 0, "%d render" % render_toplam)',
      'if R.n < BEKLENEN_IDDIA:'],
     ['if False:\n        olculemedi(',
      'render_toplam >= 0, "%d render" % render_toplam)',
      'if False:'],
     [], ["--ornek", "0", "--kosesiz"], "sessiz-yesil"),
    ("M4-fiyat-kapisi-kor", "OLDURUCU",
     'fy["bugun_varsayilan"] is None, "%s" % fy["bugun_varsayilan"])',
     'fy["bugun_varsayilan"] is not None, "%s" % fy["bugun_varsayilan"])',
     ["tutar URETMIYOR"], None, "iddia"),
    ("M5-kisit-iddiasi-ters", "OLDURUCU",
     'not kisit_var, "kisitlar %s"',
     'kisit_var, "kisitlar %s"',
     ["kisitlar` blogu YOK"], None, "iddia"),
    ("M6-sema-kapisi-devre-disi", "OLDURUCU",
     'var d = KONF.dogrula(sema, p);',
     'var d = {gecerli: false, hatalar: {}};',
     ["kutu ICINDE hicbir noktayi reddetmiyor"], None, "iddia"),
    ("M7-fiyat-tavani-kalkti", "OLDURUCU",
     'ac["azami_asa_diger"] is not None and ac["azami_asa_diger"] <= tavan',
     'ac["azami_asa_diger"] is not None and ac["azami_asa_diger"] <= tavan / 2',
     ["3x tavani ASMIYOR"], None, "iddia"),
    ("K1-yorum", "KONTROL",
     '    # ---- 5) KISIT BLOGU',
     '    # ---- 5) KISIT BLOKU (yalniz yorum degisti)',
     [], None, "iddia"),
    ("K2-etiket", "KONTROL",
     'print("\\n[5] SEMA `kisitlar` BLOGU (A3 kurali)")',
     'print("\\n[5] SEMA kisit blogu (A3 kurali)")',
     [], None, "iddia"),
]


def _iddia_ozeti(cikti):
    """(basilan iddia, kirmizi iddia). Ozet satiri YOKSA (kosum OLCULEMEDI ile
    erken kapanmis olabilir) IDDIA satirlari SAYILIR — yoksa gercekten kirmizi
    yakan bir mutant "olcum yok" diye SAG KALMIS gorunurdu (olculdu: M6)."""
    m = re.search(r"IDDIA TOPLAM: (\d+)\s+\(KIRMIZI: (\d+)\)", cikti)
    if m:
        return int(m.group(1)), int(m.group(2))
    return (len(re.findall(r"^IDDIA\s+\d+\s+\[", cikti, re.M)),
            len(re.findall(r"^IDDIA\s+\d+\s+\[KIRMIZI\]", cikti, re.M)))


def mutasyon(a):
    kaynak_yol = os.path.abspath(__file__)
    kaynak = io.open(kaynak_yol, encoding="utf-8").read()
    basta = hashlib.sha256(kaynak.encode("utf-8")).hexdigest()
    if kaynak.count(MUT_SINIR) != 1:
        print("BAYAT HARNESS: MUT_SINIR isareti %d kez bulundu" % kaynak.count(MUT_SINIR))
        return OLCULEMEDI
    kesim = kaynak.index(MUT_SINIR)
    govde, kuyruk = kaynak[:kesim], kaynak[kesim:]
    varsayilan_bayrak = ["--ornek", str(a.mut_ornek), "--kosesiz"]

    print("MUTASYON BATARYASI — rampa uretilebilirlik olcumu")
    print("kaynak sha256 (basta): %s" % basta[:16])

    ortam = dict(os.environ)
    ortam["PRUVO_REPO"] = REPO      # kopya gecici dizinde kosar, depo kokunu bilemez

    def kos(yol, bayraklar):
        p = subprocess.run([sys.executable, yol] + bayraklar, env=ortam,
                           capture_output=True, text=True, timeout=3600)
        return p.returncode, p.stdout + p.stderr

    tmpdir = tempfile.mkdtemp(prefix="rampa-mutasyon-")
    taban_yol = os.path.join(tmpdir, "taban.py")
    io.open(taban_yol, "w", encoding="utf-8").write(kaynak)
    rc0, cikti0 = kos(taban_yol, varsayilan_bayrak)
    taban_n, taban_k = _iddia_ozeti(cikti0)
    if "IDDIA TOPLAM:" not in cikti0:
        print("TABAN KOSUMU OLCULEMEDI — ozet satiri yok:\n%s" % cikti0[-1500:])
        shutil.rmtree(tmpdir, ignore_errors=True)
        return OLCULEMEDI
    print("TABAN: rc=%d iddia=%d kirmizi=%d  (%s)"
          % (rc0, taban_n, taban_k, " ".join(varsayilan_bayrak)))
    if taban_k != 0 or rc0 != 0:
        print("TABAN KIRMIZI — mutasyon bataryasi anlamsiz, once tabani onarin.")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return 1

    taban_onbellek = {}
    basarisiz = 0
    for ad, sinif, eski, yeni, capalar, bayraklar, olcut in MUTANTLAR:
        bayraklar = bayraklar or varsayilan_bayrak
        eskiler = eski if isinstance(eski, list) else [eski]
        yeniler = yeni if isinstance(yeni, list) else [yeni]
        sayimlar = [govde.count(e) for e in eskiler]
        if sayimlar != [1] * len(eskiler):
            print("  %-30s BAYAT HARNESS: capa govdede %s kez bulundu" % (ad, sayimlar))
            basarisiz += 1
            continue
        mutant_govde = govde
        for e, y in zip(eskiler, yeniler):
            mutant_govde = mutant_govde.replace(e, y)
        mut_yol = os.path.join(tmpdir, "mut.py")
        io.open(mut_yol, "w", encoding="utf-8").write(mutant_govde + kuyruk)
        rc, cikti = kos(mut_yol, bayraklar)
        n, k = _iddia_ozeti(cikti)
        anahtar = tuple(bayraklar)
        if anahtar not in taban_onbellek:
            if anahtar == tuple(varsayilan_bayrak):
                taban_onbellek[anahtar] = (rc0, taban_n, taban_k)
            else:
                t_rc2, t_cikti = kos(taban_yol, bayraklar)
                t_n2, t_k2 = _iddia_ozeti(t_cikti)
                taban_onbellek[anahtar] = (t_rc2, t_n2, t_k2)
        t_rc = taban_onbellek[anahtar][0]
        if sinif == "OLDURUCU" and olcut in ("olculemedi", "hala-yesil-degil",
                                             "sessiz-yesil"):
            # Bu kolun TABANI sifir-olcumde rc=3 (OLCULEMEDI) vermeli.
            #   "olculemedi"       -> mutant o hukmu kaybediyorsa OLDU (kol tasiyici).
            #   "hala-yesil-degil" -> ALT katman hala tutuyor mu (rc != 0 kalmali).
            #   "sessiz-yesil"     -> TUM katmanlar kalkinca kosum TAM YESILE
            #                         (rc=0, 0 kirmizi) donuyorsa OLDU: sifir-olcum
            #                         satisa dayanak olabilecek bir yesil uretiyor
            #                         ([[hukum-yanlis-birimde]]).
            oldu = t_rc == OLCULEMEDI and (
                rc != OLCULEMEDI if olcut == "olculemedi"
                else rc != 0 if olcut == "hala-yesil-degil"
                else (rc == 0 and k == 0))
            print("  %-30s %-9s taban rc=%d | mutant rc=%d kirmizi=%d -> %s"
                  % (ad, sinif, t_rc, rc, k, "OLDU" if oldu else "SAG KALDI"))
        elif sinif == "OLDURUCU":
            # ISARET SARTI: sadece "kirmizi oldu" yetmez — BEKLENEN iddia
            # kirmizi yanmali (yoksa alakasiz bir cokme mutanti "oldurdu" sanilir).
            capa_ok = all(
                re.search(r"IDDIA\s+\d+\s+\[KIRMIZI\][^\n]*" + re.escape(c), cikti)
                for c in capalar)
            oldu = k > 0 and capa_ok
            print("  %-30s %-9s rc=%d iddia=%d kirmizi=%d capa=%s -> %s"
                  % (ad, sinif, rc, n, k, "OK" if capa_ok else "YOK",
                     "OLDU" if oldu else "SAG KALDI"))
        else:
            oldu = (rc == 0 and k == 0 and n == taban_n)
            print("  %-30s %-9s rc=%d iddia=%d kirmizi=%d -> %s"
                  % (ad, sinif, rc, n, k, "YESIL" if oldu else "BEKLENMEDIK KIRMIZI"))
        if not oldu:
            basarisiz += 1
    shutil.rmtree(tmpdir, ignore_errors=True)

    sonda = hashlib.sha256(
        io.open(kaynak_yol, encoding="utf-8").read().encode("utf-8")).hexdigest()
    print("kaynak sha256 (sonda): %s  %s"
          % (sonda[:16], "SAGLAM" if sonda == basta else "CANLI DOSYA DEGISTI"))
    print("MUTANT: %d  BASARISIZ: %d" % (len(MUTANTLAR), basarisiz))
    return 1 if (basarisiz or sonda != basta) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ornek", type=int, default=200,
                    help="kova (kol x yuzey) basina orneklenecek nokta sayisi")
    ap.add_argument("--tohum", type=int, default=20260803)
    ap.add_argument("--kosesiz", action="store_true",
                    help="kose alt-uzayini atla (hizli tur)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="mutasyon bataryasi (KOPYAYA uygular, canli dosyaya DOKUNMAZ)")
    ap.add_argument("--mut-ornek", type=int, default=3,
                    help="mutasyon turunda kova basina ornek")
    a = ap.parse_args()
    if a.mutasyon:
        sys.exit(mutasyon(a))
    sys.exit(ana(a))


if __name__ == "__main__":
    main()
