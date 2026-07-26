#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/faz3-gecikme.js YANLIS-POZITIF / YANLIS-NEGATIF NOBETCISI.

    python3 tools/faz3-gecikme-test.py

NEDEN VAR (25 Tem 2026, HocA bildirimi):
faz3-gecikme.js bir zamanlar uctan uca RTT'yi butceyle karsilastiriyordu. Fethiye→
Cloudflare ag gecikmesi tek basina 300 ms'i asabildigi icin SAGLIKLI bir sistemde
KIRMIZI yaniyordu (yanlis pozitif) — ve simetrigi de vardi: hizli agda yavas bir
Worker YESIL yaniyordu (yanlis negatif). Karar artik YALNIZ worker-ici sureye
(yanit govdesindeki "ms") gore verilir; RTT bilgi olarak raporlanir.

Bu nobetci o kusurun GERI GELMESINI engeller. Sahte bir Worker ucu ayaga kaldirir ve
IKI EKSENI BAGIMSIZ oynatir:
    ag_gecikme_ms -> uctan uca RTT       (sunucu cevap vermeden once bekler)
    ic_ms         -> worker-ici sure     (yanittaki "ms" alani)
Bu ayrim sart: tek eksenli bir fikstur (ikisi birlikte artan) RTT'ye bakan bir betigi
de YESIL yakar, yani hicbir sey olcmez.

OFFLINE: yalniz 127.0.0.1'e baglanir. urunler.json / D1 / R2 / canli Worker OKUNMAZ.
Cikis: 0 = tum senaryolar bekleneni verdi, 1 = en az bir sapma.
"""

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOOLS = os.path.dirname(os.path.abspath(__file__))
BETIK = os.path.join(TOOLS, "faz3-gecikme.js")

# Kanonik ornek 20; nobetci hizi icin 4 (betik kanonik olmadigini kendisi basar).
N_FIKSTUR = "4"

# Betikin butcesi 300 ms. Fikstur degerleri butcenin IKI YANINDA, jitter payiyla.
AG_YAVAS = 350      # RTT'yi butcenin USTUNE cikarir
AG_HIZLI = 5        # RTT butcenin cok altinda
IC_SAGLIKLI = 25    # worker-ici sure butce ICINDE
IC_YAVAS = 450      # worker-ici sure butce DISINDA

AYAR = {"ag_gecikme_ms": AG_HIZLI, "ic_ms": IC_SAGLIKLI, "ic_alani_var": True,
        "hata_ver": False, "kismi_hata_her": 0}
SAYAC = {"n": 0}
KILIT = threading.Lock()


class SahteUc(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        with KILIT:
            SAYAC["n"] += 1
            sira = SAYAC["n"]
            ayar = dict(AYAR)
        time.sleep(ayar["ag_gecikme_ms"] / 1000.0)
        if ayar["hata_ver"]:
            self._gonder({"hata": "KATALOG baglantisi yok", "toplam": 0, "urunler": []}, 500)
            return
        if ayar["kismi_hata_her"] and (sira % ayar["kismi_hata_her"] == 0):
            self._gonder({"hata": "gecici D1 hatasi", "toplam": 0, "urunler": []}, 500)
            return
        govde = {"toplam": 1, "urunler": [{"id": "x", "baslik": "y"}]}
        if ayar["ic_alani_var"]:
            govde["ms"] = ayar["ic_ms"]
        self._gonder(govde, 200)

    def _gonder(self, govde, durum):
        ham = json.dumps(govde).encode("utf-8")
        self.send_response(durum)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(ham)))
        self.send_header("cache-control", "public, max-age=60")
        self.end_headers()
        self.wfile.write(ham)


def kos(port):
    ort = dict(os.environ)
    ort["EDGE_UC"] = "http://127.0.0.1:%d" % port
    ort["FAZ3_ISTEK_SAYISI"] = N_FIKSTUR
    try:
        p = subprocess.run([os.environ.get("NODE_BIN", "node"), BETIK],
                           capture_output=True, text=True, timeout=300, env=ort)
    except FileNotFoundError:
        # FAIL-CLOSED: node yoksa yalanci-yesil OLMAZ.
        print("❌ node bulunamadi — bu nobetci node gerektirir (CI'da setup-node var).")
        sys.exit(1)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# (ad, ayar, beklenen_cikis, stdout'ta GECMESI gereken metin, gerekce)
SENARYOLAR = [
    ("A yanlis-pozitif: yavas ag + SAGLIKLI worker",
     {"ag_gecikme_ms": AG_YAVAS, "ic_ms": IC_SAGLIKLI, "ic_alani_var": True,
      "hata_ver": False, "kismi_hata_her": 0},
     0, "RTT butcenin ustunde",
     "RTT butce disi ama ic butce ici -> YESIL; ustelik 'asim AGDAN' notu dusmeli"),

    ("B gercek gerileme: yavas worker",
     {"ag_gecikme_ms": AG_YAVAS, "ic_ms": IC_YAVAS, "ic_alani_var": True,
      "hata_ver": False, "kismi_hata_her": 0},
     1, "GECIKME BUTCESI ASILDI",
     "worker-ici 450 ms -> KIRMIZI"),

    ("C yanlis-negatif: HIZLI ag + yavas worker",
     {"ag_gecikme_ms": AG_HIZLI, "ic_ms": IC_YAVAS, "ic_alani_var": True,
      "hata_ver": False, "kismi_hata_her": 0},
     1, "GECIKME BUTCESI ASILDI",
     "RTT kucuk ama ic 450 -> KIRMIZI (RTT'ye bakan betik burada YESIL yanar)"),

    ("D olculemedi: yanitta ic sure alani YOK",
     {"ag_gecikme_ms": AG_HIZLI, "ic_ms": 0, "ic_alani_var": False,
      "hata_ver": False, "kismi_hata_her": 0},
     2, "OLCULEMEDI",
     "sessiz yesil de sessiz kirmizi da YOK -> ayri cikis 2"),

    ("E olculemedi: uc hic cevap vermiyor",
     {"ag_gecikme_ms": AG_HIZLI, "ic_ms": 0, "ic_alani_var": True,
      "hata_ver": True, "kismi_hata_her": 0},
     2, "OLCULEMEDI",
     "uc kapali = gecikme gerilemesi DEGIL -> cikis 2"),

    ("F kismi hata: uc bozuk ama ic sure dusuk",
     {"ag_gecikme_ms": AG_HIZLI, "ic_ms": IC_SAGLIKLI, "ic_alani_var": True,
      "hata_ver": False, "kismi_hata_her": 3},
     1, "ISTEK HATASI",
     "veri VAR + hata VAR -> kirmizi, ama sebep 'butce' DIYE raporlanmamali"),
]


def main():
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), SahteUc)
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    time.sleep(0.2)

    print("faz3-gecikme.js nobetcisi | sahte uc 127.0.0.1:%d | ornek N=%s\n" % (port, N_FIKSTUR))
    kaldi = 0
    for ad, ayar, bek_cikis, bek_metin, gerekce in SENARYOLAR:
        with KILIT:
            AYAR.update(ayar)
            SAYAC["n"] = 0
        t0 = time.time()
        cikis, cikti = kos(port)
        sure = time.time() - t0
        cikis_ok = (cikis == bek_cikis)
        metin_ok = (bek_metin in cikti)
        if cikis_ok and metin_ok:
            print("  ✅ %s" % ad)
            print("       cikis=%d (beklenen %d), \"%s\" var  (%.1f sn)"
                  % (cikis, bek_cikis, bek_metin, sure))
        else:
            kaldi += 1
            print("  ❌ KALDI: %s" % ad)
            print("       gerekce: %s" % gerekce)
            if not cikis_ok:
                print("       cikis=%d ama beklenen %d" % (cikis, bek_cikis))
            if not metin_ok:
                print("       ciktida \"%s\" YOK" % bek_metin)
            print("       --- cikti ---")
            for satir in cikti.strip().splitlines():
                print("       " + satir)

    sunucu.shutdown()
    print("\n%d/%d GEÇTI" % (len(SENARYOLAR) - kaldi, len(SENARYOLAR)))
    if kaldi:
        print("SONUC: KABUL TESTI KIRMIZI ❌ (%d kaldi)" % kaldi)
        sys.exit(1)
    print("SONUC: KABUL TESTI YEŞİL ✅ (karar worker-ici sureye gore veriliyor)")


if __name__ == "__main__":
    main()
