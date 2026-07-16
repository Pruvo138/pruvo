#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO onizleme derleyicisi — parametre -> OpenSCAD -> binary STL (HTTP servisi).

Bu dosya PUBLIC repodadir ve SIR ICERMEZ: hangi .scad'in hangi degiskenlerle
surulecegi tamamen GIZLI eslem dosyasindan (paket dizinindeki eslem-ozel.json,
gitignore'lu; kanonik kopya R2 pruvo-ozel) okunur. Uretec kaynak kodu ve
degisken adlari istemciye/repoya gitmez; istemciye yalnizca derlenmis mesh doner.

ENJEKSIYON MODELI (tasarimla imkansiz): istemciden gelen deger -D satirina
HICBIR ZAMAN metin olarak gecmez. Sayisal parametreler yalniz sonlu float
olarak dogrusal kombinasyona girer ("%.6f" formatlanir); secim parametreleri
yalniz eslem dosyasindaki tablo'da TANIMLI anahtarlarin KARSILIKLARINI secer.
Yani -D'ye yazilan her metin bizim dosyamizdan gelir, istekten degil.
(subprocess argv listesi kullanilir; shell yorumlamasi da yoktur.)

Calisma bicimleri:
  python3 server.py --paket <dizin> --port 8791            # gercek derleme
  python3 server.py --port 8791 --mock                     # openscad'siz mock STL
  python3 server.py --oz-test                              # ic guvenlik testleri
Uclar:
  POST /derle  {"aile": "...", "parametreler": {...}} -> 200 binary STL
               400 gecersiz istek / 404 aile yok / 422 gecersiz-geometri /
               500 derleme hatasi / 504 zaman asimi
  GET  /saglik -> {"durum": "hazir", "aileler": [...], "mock": bool}
  GET  /sayac  -> {"derleme": N}   (kabul testi 4c: onbellek isabetinde artmamali)

Cloudflare Container'da: Dockerfile bu dosyayi ve gizli paketi imaja koyar,
CMD server.py --paket /srv/paket --port 8080. Worker'daki adaptor
(onizleme/src/derleyici.js) ayni HTTP sozlesmesiyle konusur.
"""
import argparse
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VARSAYILAN_ZAMAN_ASIMI_SN = 5.0
HAM_STL_TAVANI = 20 * 1024 * 1024  # guvenlik tavani; asil 2 MB gzip tavani Worker'da
SAYAC = {"derleme": 0}
SAYAC_KILIT = threading.Lock()


def openscad_yolu():
    import glob
    import shutil
    adaylar = [os.environ.get("PRUVO_OPENSCAD"),
               "/usr/bin/openscad", "/usr/local/bin/openscad",
               "/opt/homebrew/bin/openscad"]
    adaylar += sorted(glob.glob(
        "/opt/homebrew/Caskroom/openscad*/*/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
        reverse=True)
    adaylar.append(shutil.which("openscad"))
    for yol in adaylar:
        if yol and os.path.exists(yol):
            return yol
    return None


def eslem_yukle(paket_dizin):
    yol = os.path.join(paket_dizin, "eslem-ozel.json")
    with open(yol, "r", encoding="utf-8") as f:
        veri = json.load(f)
    return veri["aileler"]


def sayi_mi(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def sayi_metni(v):
    s = "%.6f" % float(v)
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def d_deger(deger):
    """eslem SABITINI -D metnine cevirir (istemci verisi buraya giremez)."""
    if isinstance(deger, bool):
        return "true" if deger else "false"
    if sayi_mi(deger):
        return sayi_metni(deger)
    if isinstance(deger, str):
        # Kendi dosyamizdan gelse de savunma: tirnak/ters bolu/yenisatir sokulur.
        temiz = deger.replace("\\", "").replace('"', "").replace("\n", " ").replace("\r", " ")
        return '"%s"' % temiz
    if isinstance(deger, list):
        # OpenSCAD vektor sabiti, or. [4, 2] — elemanlar yalniz sayi/bool.
        return "[%s]" % ", ".join(d_deger(x) for x in deger)
    raise ValueError("desteklenmeyen sabit tipi: %r" % (deger,))


def sayisal_kural(kural, parametreler, hatalar, scad_ad):
    """Tek dogrusal kombinasyon kuralini hesaplar; hata durumunda None."""
    toplam = float(kural.get("sabit", 0))
    for param, katsayi in (kural.get("terimler") or {}).items():
        v = parametreler.get(param)
        if not sayi_mi(v):
            hatalar.append("sayisal-degil:" + param)
            return None
        toplam += float(katsayi) * float(v)
    if "en_az" in kural:
        toplam = max(float(kural["en_az"]), toplam)
    if "en_cok" in kural:
        toplam = min(float(kural["en_cok"]), toplam)
    if not math.isfinite(toplam):
        hatalar.append("sonlu-degil:" + scad_ad)
        return None
    return toplam


def blok_uygula(blok, parametreler, dler, hatalar):
    """Tek eslem blogunu (sayisal/vektor/secim/sabit) -D sozlugune isler."""
    for scad_ad, kural in (blok.get("sayisal") or {}).items():
        toplam = sayisal_kural(kural, parametreler, hatalar, scad_ad)
        if toplam is None:
            return
        dler[scad_ad] = sayi_metni(toplam)
    for scad_ad, kurallar in (blok.get("vektor") or {}).items():
        # OpenSCAD vektor degiskeni: her bilesen kendi dogrusal kurali.
        parcalar = []
        for kural in kurallar:
            toplam = sayisal_kural(kural, parametreler, hatalar, scad_ad)
            if toplam is None:
                return
            parcalar.append(sayi_metni(toplam))
        dler[scad_ad] = "[%s]" % ", ".join(parcalar)
    for scad_ad, kural in (blok.get("secim") or {}).items():
        v = parametreler.get(kural["param"])
        tablo = kural["tablo"]
        # Sayi degerli parametre de tabloya baglanabilir (or. standart olcu
        # izgarasi: cap -> "M5"): anahtar kanonik sayi metnidir.
        if sayi_mi(v):
            v = sayi_metni(v)
        if not isinstance(v, str) or v not in tablo:
            hatalar.append("secim-tanimsiz:" + kural["param"])
            return
        dler[scad_ad] = d_deger(tablo[v])
    for scad_ad, deger in (blok.get("sabit") or {}).items():
        dler[scad_ad] = d_deger(deger)


def d_bayraklari(aile_eslem, parametreler):
    """Istek parametrelerinden -D bayrak listesi. Hata varsa (None, sebep)."""
    dler, hatalar = {}, []
    blok_uygula(aile_eslem.get("ortak") or {}, parametreler, dler, hatalar)
    secici = aile_eslem.get("secici")
    if secici:
        v = parametreler.get(secici)
        varyantlar = aile_eslem.get("varyantlar") or {}
        if not isinstance(v, str) or v not in varyantlar:
            hatalar.append("varyant-tanimsiz:" + str(secici))
        else:
            blok_uygula(varyantlar[v], parametreler, dler, hatalar)
    if hatalar:
        return None, ",".join(hatalar)
    bayraklar = []
    for ad, deger in dler.items():
        bayraklar += ["-D", "%s=%s" % (ad, deger)]
    return bayraklar, None


def mock_stl(parametreler):
    """Deterministik 12 ucgenlik kup STL'i (openscad'siz test). Kenar, parametre
    ozetinden turetilir ki farkli girdiler farkli byte'lar uretsin."""
    ozet = json.dumps(parametreler, sort_keys=True, ensure_ascii=False)
    kenar = 10.0 + (sum(ozet.encode("utf-8")) % 50)
    k = kenar / 2.0
    v = [(-k, -k, -k), (k, -k, -k), (k, k, -k), (-k, k, -k),
         (-k, -k, k), (k, -k, k), (k, k, k), (-k, k, k)]
    yuzler = [(0, 3, 2), (0, 2, 1), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
              (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    govde = bytearray(b"PRUVO mock STL".ljust(80, b"\0"))
    govde += struct.pack("<I", len(yuzler))
    for (a, b, c) in yuzler:
        pa, pb, pc = v[a], v[b], v[c]
        u = tuple(pb[i] - pa[i] for i in range(3))
        w = tuple(pc[i] - pa[i] for i in range(3))
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        boy = math.sqrt(sum(x * x for x in n)) or 1.0
        govde += struct.pack("<3f", *(x / boy for x in n))
        for p in (pa, pb, pc):
            govde += struct.pack("<3f", *p)
        govde += struct.pack("<H", 0)
    return bytes(govde)


def derle(ayarlar, aile, parametreler):
    """(kod, govde_bytes | hata_dict) doner."""
    eslem = ayarlar["eslem"].get(aile)
    if eslem is None:
        return 404, {"hata": "aile-yok"}
    bayraklar, sebep = d_bayraklari(eslem, parametreler)
    if bayraklar is None:
        return 400, {"hata": "gecersiz-parametre", "sebep": sebep}

    with SAYAC_KILIT:
        SAYAC["derleme"] += 1

    if ayarlar["mock"]:
        return 200, mock_stl(parametreler)

    # Cift-uretecli aileler: secici varyanti kendi .scad'ini gosterebilir.
    # Deger d_bayraklari'ndan gecti (tabloda TANIMLI), scad adi bizim dosyamizdan.
    scad_ad = eslem["scad"]
    if eslem.get("secici"):
        varyant = (eslem.get("varyantlar") or {}).get(
            parametreler.get(eslem["secici"])) or {}
        scad_ad = varyant.get("scad", scad_ad)
    scad_yol = os.path.join(ayarlar["paket"], scad_ad)
    if not os.path.exists(scad_yol):
        return 500, {"hata": "scad-eksik"}
    with tempfile.TemporaryDirectory() as tmp:
        stl = os.path.join(tmp, "cikti.stl")
        komut = [ayarlar["openscad"], "-o", stl, "--export-format", "binstl"]
        komut += bayraklar
        komut.append(scad_yol)
        try:
            proc = subprocess.run(komut, capture_output=True,
                                  timeout=ayarlar["zaman_asimi"])
        except subprocess.TimeoutExpired:
            return 504, {"hata": "derleme-zaman-asimi"}
        if proc.returncode != 0 or not os.path.exists(stl):
            hata_metni = proc.stderr.decode("utf-8", "replace")
            # Uretec assert'i = musteri kombinasyonu geometrik olarak uretilELEMEZ
            # (or. cok kalin et + cok kucuk kesit). Istemciye temiz 422 doner.
            if "ERROR: Assertion" in hata_metni or "assert" in hata_metni.lower():
                return 422, {"hata": "gecersiz-geometri"}
            sys.stderr.write("derleme hatasi (%s): %s\n" % (aile, hata_metni[-500:]))
            return 500, {"hata": "derleme-hatasi"}
        boyut = os.path.getsize(stl)
        if boyut > HAM_STL_TAVANI:
            return 413, {"hata": "cikti-cok-buyuk"}
        with open(stl, "rb") as f:
            return 200, f.read()


class Istekci(BaseHTTPRequestHandler):
    ayarlar = None  # main() doldurur

    def _json(self, kod, veri):
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        if self.path == "/saglik":
            self._json(200, {"durum": "hazir", "mock": self.ayarlar["mock"],
                             "aileler": sorted(self.ayarlar["eslem"].keys())})
        elif self.path == "/sayac":
            self._json(200, {"derleme": SAYAC["derleme"]})
        else:
            self._json(404, {"hata": "bulunamadi"})

    def do_POST(self):
        if self.path != "/derle":
            return self._json(404, {"hata": "bulunamadi"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > 64 * 1024:
                return self._json(400, {"hata": "gecersiz-istek"})
            govde = json.loads(self.rfile.read(n).decode("utf-8"))
            aile = govde.get("aile")
            parametreler = govde.get("parametreler")
            if not isinstance(aile, str) or not isinstance(parametreler, dict):
                return self._json(400, {"hata": "gecersiz-istek"})
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"hata": "gecersiz-json"})
        kod, sonuc = derle(self.ayarlar, aile, parametreler)
        if kod != 200:
            return self._json(kod, sonuc)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(sonuc)))
        self.end_headers()
        self.wfile.write(sonuc)

    def log_message(self, fmt, *args):
        sys.stderr.write("[derleyici] %s\n" % (fmt % args))


def oz_test():
    """Ic guvenlik testleri — kabul 4b'nin sunucu ayagi. Cikis kodu 0/1."""
    eslem = {
        "scad": "x.scad", "secici": "kesit",
        "ortak": {"sayisal": {"Boy": {"terimler": {"uzunluk": 1}}},
                  "secim": {"Tip": {"param": "renk", "tablo": {"kirmizi": "red"}}},
                  "sabit": {"Sabit": 'a"b\\c'}},
        "varyantlar": {"i": {"sayisal": {"H": {"terimler": {"yukseklik": 1, "et": -2}}}}},
    }
    hatalar = []

    def dogrula(ad, kosul):
        durum = "OK " if kosul else "HATA"
        print("  [%s] %s" % (durum, ad))
        if not kosul:
            hatalar.append(ad)

    # 1) String enjeksiyonu SAYISAL parametreye: reddedilir, -D uretilmez.
    b, sebep = d_bayraklari(eslem, {"uzunluk": '10; cube(999); //',
                                    "renk": "kirmizi", "kesit": "i",
                                    "yukseklik": 40, "et": 3})
    dogrula("sayisal alana string -> ret", b is None and "sayisal-degil" in sebep)
    # 2) Secim disi deger (klasik enjeksiyon kaligrafisi): reddedilir.
    b, sebep = d_bayraklari(eslem, {"uzunluk": 10, "renk": '"; cube(999); //',
                                    "kesit": "i", "yukseklik": 40, "et": 3})
    dogrula("secim disi deger -> ret", b is None and "secim-tanimsiz" in sebep)
    # 3) Varyant disi secici: reddedilir.
    b, sebep = d_bayraklari(eslem, {"uzunluk": 10, "renk": "kirmizi",
                                    "kesit": 'z"; import("/etc/passwd"); //',
                                    "yukseklik": 40, "et": 3})
    dogrula("varyant disi secici -> ret", b is None and "varyant-tanimsiz" in sebep)
    # 4) NaN/Infinity: JSON'da zaten yasak ama float("nan") savunmasi.
    b, sebep = d_bayraklari(eslem, {"uzunluk": float("nan"), "renk": "kirmizi",
                                    "kesit": "i", "yukseklik": 40, "et": 3})
    dogrula("NaN -> ret", b is None)
    # 5) bool sayi sayilmaz (True == 1 tuzagi).
    b, sebep = d_bayraklari(eslem, {"uzunluk": True, "renk": "kirmizi",
                                    "kesit": "i", "yukseklik": 40, "et": 3})
    dogrula("bool -> ret", b is None)
    # 6) Gecerli istek: -D'lerde istemci metni YOK; sabitteki tirnak sokulmus.
    b, sebep = d_bayraklari(eslem, {"uzunluk": 100, "renk": "kirmizi",
                                    "kesit": "i", "yukseklik": 40, "et": 3})
    metin = " ".join(b or [])
    dogrula("gecerli istek derlenir", b is not None)
    dogrula("tehlikeli karakter yok", ";" not in metin and "\\" not in metin)
    dogrula("dogrusal kombinasyon dogru", "H=34" in metin and "Boy=100" in metin)
    dogrula("sabit tirnaklari sokuldu", 'Sabit="abc"' in metin)
    # 7) mock STL gecerli binary STL (84 + 12*50 byte).
    m = mock_stl({"a": 1})
    dogrula("mock STL boyutu", len(m) == 84 + 12 * 50)
    # 8) vektor kurali + liste sabiti + sayi-anahtarli secim tablosu (Faz D).
    eslem2 = {
        "scad": "y.scad",
        "ortak": {
            "vektor": {"Boyut": [{"terimler": {"en": 1}}, {"terimler": {"boy": 1}}]},
            "secim": {"Olcu": {"param": "cap", "tablo": {"5": "M5", "6": "M6"}}},
            "sabit": {"Aralik": [4, 2.5], "Bayrak": [True, False]},
        },
    }
    b, sebep = d_bayraklari(eslem2, {"en": 80, "boy": 60.5, "cap": 5})
    metin2 = " ".join(b or [])
    dogrula("vektor kurali", b is not None and "Boyut=[80, 60.5]" in metin2)
    dogrula("liste sabiti", "Aralik=[4, 2.5]" in metin2 and "Bayrak=[true, false]" in metin2)
    dogrula("sayi-anahtarli secim", 'Olcu="M5"' in metin2)
    b, sebep = d_bayraklari(eslem2, {"en": 80, "boy": 60, "cap": 5.5})
    dogrula("izgara disi sayi secimi -> ret", b is None and "secim-tanimsiz" in sebep)
    b, sebep = d_bayraklari(eslem2, {"en": "x", "boy": 60, "cap": 5})
    dogrula("vektor bileseninde string -> ret", b is None and "sayisal-degil" in sebep)

    print("oz-test: %d hata" % len(hatalar))
    return 1 if hatalar else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paket", help="eslem-ozel.json + .scad dosyalarinin dizini")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--adres", default="127.0.0.1")
    ap.add_argument("--mock", action="store_true", help="openscad'siz mock STL")
    ap.add_argument("--zaman-asimi", type=float, default=VARSAYILAN_ZAMAN_ASIMI_SN)
    ap.add_argument("--oz-test", action="store_true")
    args = ap.parse_args()

    if args.oz_test:
        sys.exit(oz_test())

    if args.mock:
        # Mock'ta eslem yine yuklenir (varsa) ki dogrulama yollari gercekle ayni olsun;
        # paket verilmediyse pilot ailelerinin adlariyla bos gecilmez — paket sart.
        eslem = eslem_yukle(args.paket) if args.paket else {}
        if not eslem:
            sys.exit("--mock icin de --paket verin (eslem dogrulamasi gercekle ayni kossun)")
        openscad = None
    else:
        if not args.paket:
            sys.exit("--paket zorunlu")
        eslem = eslem_yukle(args.paket)
        openscad = openscad_yolu()
        if not openscad:
            sys.exit("openscad bulunamadi (PRUVO_OPENSCAD ayarlayin)")

    Istekci.ayarlar = {"eslem": eslem, "paket": args.paket, "mock": args.mock,
                       "openscad": openscad, "zaman_asimi": args.zaman_asimi}
    sunucu = ThreadingHTTPServer((args.adres, args.port), Istekci)
    sys.stderr.write("[derleyici] hazir: %s:%d mock=%s aile=%d\n" %
                     (args.adres, args.port, args.mock, len(eslem)))
    sunucu.serve_forever()


if __name__ == "__main__":
    main()
