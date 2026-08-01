#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/faz3-sayfalama.js "OLCULEMEDI vs BOZUK" NOBETCISI.

    python3 tools/faz3-sayfalama-test.py

NEDEN VAR (1 Agu 2026 olcumu):
faz3-sayfalama.js her istek arizasini "gorunum ayristi" sayiyordu: yerel wrangler
kosmuyorken 7/7 gorunum "fetch failed" verdi ve betik "SAYFALAMA/SIRA BOZUK ❌"
basip cikis 1 dondu — hicbir sayfa gorulmeden. Bu yanlis suclamadir; kardes arac
faz3-gecikme.js ayni durumu zaten OLCULEMEDI (cikis 2) sayiyordu, yani sozlesme
ikizleri AYRISMISTI.

Bu nobetci kusurun IKI YONUNU birden olcer:
  - gevseme yonu: gercek sayfalama/sira kirilmasi hala KIRMIZI mi (fail-open yok)
  - suclama yonu: uc yokken/susarken KIRMIZI YANMIYOR mu ve "BOZUK" demiyor mu
Tek yonlu bir fikstur yetmez: kosulsuz exit 0 basan bir betik "uc yok" senaryosunu
gecer, kosulsuz exit 1 basan betik ise "bozuk uc" senaryosunu gecer.

OFFLINE: yalniz 127.0.0.1'e baglanir. D1 / R2 / canli Worker OKUNMAZ. Sahte uc
urunler.json'u KENDI okur (betigin referansi da odur) ve yalniz id doner.
Cikis: 0 = tum senaryolar bekleneni verdi, 1 = en az bir sapma.
"""

import json
import math
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
BETIK = os.path.join(TOOLS, "faz3-sayfalama.js")
URUNLER = os.path.join(KOK, "urunler.json")

# Betigin sozlesmesi (kardes faz3-gecikme.js ile ayni).
CIK_OK = 0
CIK_KIRMIZI = 1
CIK_OLCULEMEDI = 2

AYAR = {"mod": "dogru"}
KILIT = threading.Lock()
ONBELLEK = {}

with open(URUNLER, "r", encoding="utf-8") as f:
    PRODUCTS = json.load(f)


def gorunum_listesi(kategori, marka):
    """Betikteki beklenen() ile AYNI suzgec: dosya sirasi = en yeni ustte."""
    ids = []
    for p in PRODUCTS:
        if kategori and kategori != "Tümü" and p.get("kategori") != kategori:
            continue
        if marka and marka != "Tümü" and marka not in (p.get("marka") or []):
            continue
        ids.append(p["id"])
    return ids


def servis_listesi(kategori, marka, mod, boy):
    """Ucun GERCEKTEN sunacagi liste + iddia ettigi toplam. Bozukluklar burada uretilir."""
    anahtar = (kategori, marka, mod, boy)
    with KILIT:
        if anahtar in ONBELLEK:
            return ONBELLEK[anahtar]
    dogru = gorunum_listesi(kategori, marka)
    toplam = len(dogru)
    liste = list(dogru)
    if mod == "atla" and len(liste) > boy:
        # OFFSET sayfalamasinin klasik hatasi: sayfa sinirindaki urun ATLANIR.
        # Uc "toplam" olarak dogru sayiyi soyler, ama o urunu HIC sunmaz.
        del liste[boy]
    elif mod == "sira" and len(liste) > 1:
        # D1 sirasi dosya sirasindan ayrisir: "en yeni ustte" iddiasi sessizce olur.
        liste[0], liste[1] = liste[1], liste[0]
    elif mod == "mukerrer" and len(liste) > boy:
        # Sinirdaki urun IKI KEZ gelir (ve bir baskasi kaybolur).
        liste[boy] = liste[boy - 1]
    sonuc = (liste, toplam)
    with KILIT:
        ONBELLEK[anahtar] = sonuc
    return sonuc


class SahteUc(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        with KILIT:
            mod = AYAR["mod"]
        q = parse_qs(urlparse(self.path).query)
        kategori = (q.get("kategori") or ["Tümü"])[0]
        marka = (q.get("marka") or ["Tümü"])[0]
        sayfa = int((q.get("sayfa") or ["1"])[0])
        boy = int((q.get("boy") or ["100"])[0])

        if mod == "hata":
            # Uc AYAKTA ama kendi arizasini bildiriyor.
            self._json({"hata": "D1 baglantisi yok", "toplam": 0, "urunler": []}, 500)
            return
        if mod == "bos":
            # Yanit geldi ama sayfalama alanlari YOK (eski surum / govde degisimi).
            self._json({"tamam": True}, 200)
            return
        if mod == "susuyor":
            # 502 + JSON OLMAYAN govde (WAF/proxy hata sayfasi imzasi).
            self._ham(b"<html>502 Bad Gateway</html>", 502, "text/html")
            return
        if mod == "kismi" and kategori == "Marin":
            # KISMI HAL: bir gorunum olculemez, digerleri GERCEKTEN bozuk.
            self._ham(b"<html>502 Bad Gateway</html>", 502, "text/html")
            return
        if mod == "kismi":
            liste, toplam = servis_listesi(kategori, marka, "sira", boy)
        else:
            liste, toplam = servis_listesi(kategori, marka, mod, boy)

        bas = (sayfa - 1) * boy
        self._json({
            "toplam": toplam,
            "sonSayfa": max(1, math.ceil(toplam / float(boy))),
            "urunler": [{"id": i} for i in liste[bas:bas + boy]],
        }, 200)

    def _json(self, govde, durum):
        self._ham(json.dumps(govde).encode("utf-8"), durum, "application/json; charset=utf-8")

    def _ham(self, ham, durum, tur):
        self.send_response(durum)
        self.send_header("content-type", tur)
        self.send_header("content-length", str(len(ham)))
        self.send_header("cache-control", "public, max-age=60")
        self.end_headers()
        self.wfile.write(ham)


def bos_port():
    """Hicbir seyin dinlemedigi bir port: 'uc yok' senaryosu icin."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def kos(uc):
    ort = dict(os.environ)
    ort["KATALOG_UC"] = uc
    try:
        p = subprocess.run([os.environ.get("NODE_BIN", "node"), BETIK],
                           capture_output=True, text=True, timeout=900, env=ort)
    except FileNotFoundError:
        # FAIL-CLOSED: node yoksa yalanci-yesil OLMAZ.
        print("❌ node bulunamadi — bu nobetci node gerektirir.")
        sys.exit(1)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# (ad, mod|None(=uc yok), beklenen_cikis, ICERMELI, ICERMEMELI, gerekce)
SENARYOLAR = [
    ("A uc YOK (hicbir sey dinlemiyor)", None, CIK_OLCULEMEDI,
     ["OLCULEMEDI"], ["BOZUK"],
     "hicbir sayfa gorulmedi -> hukum YOK; 'bozuk' demek yanlis suclama"),

    ("B uc DOGRU", "dogru", CIK_OK,
     ["SAYFALAMA + SIRA KORUNUMU TAM"], ["BOZUK", "OLCULEMEDI"],
     "kume + sira birebir -> YESIL"),

    ("C uc BOZUK: sayfa sinirinda urun ATLANIYOR", "atla", CIK_KIRMIZI,
     ["SAYFALAMA/SIRA BOZUK", "TOPLANAN"], ["OLCULEMEDI ⚪"],
     "gercek sayfalama kaybi -> KIRMIZI (onarim gevsemedi mi)"),

    ("D uc BOZUK: SIRA ayristi", "sira", CIK_KIRMIZI,
     ["SAYFALAMA/SIRA BOZUK", "SIRA "], ["OLCULEMEDI ⚪"],
     "'en yeni ustte' iddiasi kirik -> KIRMIZI"),

    ("E uc BOZUK: MUKERRER urun", "mukerrer", CIK_KIRMIZI,
     ["SAYFALAMA/SIRA BOZUK", "MUKERRER"], ["OLCULEMEDI ⚪"],
     "sinirdaki urun iki kez geliyor -> KIRMIZI"),

    ("F uc kendi hatasini bildiriyor (govdede 'hata')", "hata", CIK_KIRMIZI,
     ["ISTEK HATASI", "uc hata donduruyor"], ["SAYFALAMA/SIRA BOZUK"],
     "gercek ariza -> kirmizi, ama sebep 'sayfalama' DIYE raporlanmamali"),

    ("G yanit JSON DEGIL (WAF/502)", "susuyor", CIK_OLCULEMEDI,
     ["OLCULEMEDI"], ["BOZUK"],
     "uc protokolumuzu konusmuyor -> olculemedi, suclama YOK"),

    ("H yanitta sayfalama alanlari YOK", "bos", CIK_OLCULEMEDI,
     ["OLCULEMEDI"], ["BOZUK"],
     "alan yoksa sayfalama OLCULEMEZ; eskiden .map cakip 'bozuk' yaziyordu"),

    ("I KISMI: 1 gorunum olculemedi + 6 gorunum ayristi", "kismi", CIK_KIRMIZI,
     ["SAYFALAMA/SIRA BOZUK", "OLCULEMEDI"], [],
     "olculemeyen gorunum, OLCULMUS ayrismayi MASKELEYEMEZ -> KIRMIZI baskin"),
]


def main():
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), SahteUc)
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    time.sleep(0.2)
    kapali = bos_port()

    print("faz3-sayfalama.js nobetcisi | sahte uc 127.0.0.1:%d | %d urun\n"
          % (port, len(PRODUCTS)))
    kaldi = 0
    for ad, mod, bek_cikis, icermeli, icermemeli, gerekce in SENARYOLAR:
        if mod is None:
            uc = "http://127.0.0.1:%d/katalog" % kapali
        else:
            with KILIT:
                AYAR["mod"] = mod
            uc = "http://127.0.0.1:%d/katalog" % port
        t0 = time.time()
        cikis, cikti = kos(uc)
        sure = time.time() - t0
        eksik = [m for m in icermeli if m not in cikti]
        fazla = [m for m in icermemeli if m in cikti]
        if cikis == bek_cikis and not eksik and not fazla:
            print("  ✅ %s" % ad)
            print("       cikis=%d (beklenen %d)  (%.1f sn)" % (cikis, bek_cikis, sure))
        else:
            kaldi += 1
            print("  ❌ KALDI: %s" % ad)
            print("       gerekce: %s" % gerekce)
            if cikis != bek_cikis:
                print("       cikis=%d ama beklenen %d" % (cikis, bek_cikis))
            for m in eksik:
                print("       ciktida \"%s\" YOK" % m)
            for m in fazla:
                print("       ciktida \"%s\" VAR — olmamali" % m)
            print("       --- cikti ---")
            for satir in cikti.strip().splitlines():
                print("       " + satir)

    sunucu.shutdown()
    print("\n%d/%d GEÇTI" % (len(SENARYOLAR) - kaldi, len(SENARYOLAR)))
    if kaldi:
        print("SONUC: KABUL TESTI KIRMIZI ❌ (%d kaldi)" % kaldi)
        sys.exit(1)
    print("SONUC: KABUL TESTI YEŞİL ✅ (olculemedi ≠ bozuk; gercek bozukluk hala kirmizi)")


if __name__ == "__main__":
    main()
