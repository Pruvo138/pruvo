#!/usr/bin/env python3
"""mukerrer-kontrol.py KAYNAK HARITASI FAIL-CLOSED bataryasi (21 Eki 2026, MaCiT 03:15 +
BaBa 04:4x) — AG YOK, git YOK; veri koku PRUVO_VERI_KOK ile tempfile'a yonlendirilir.

Vakalar (varsayilan kip = calisma agaci taramasi):
  K1 .urun-kaynaklari.json YOK       -> rc=2, "KAYNAK HARITASI OKUNAMADI"
  K2 .urun-kaynaklari.json BOZUK     -> rc=2
  K3 gecerli harita, cift yok        -> rc=0 "mukerrer yok"
  K4 gecerli harita, ayni link 2 id  -> rc=1 "MUKERRER KAYNAK" (eksen gercekten olcuyor)
Mutant (IZOLE kopya): M1 fail-closed donusu kalkar -> {K1, K2} KIRMIZI (eski fail-open rc=0).
Gercek kataloga/haritaya DOKUNMAZ: tum dosyalar tempfile altinda.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "mukerrer-kontrol.py")
VERI_KOK_MODUL = os.path.join(KOK, "tools", "veri_kok.py")
URUNLER = [{"id": "a-parca", "baslik": "A Parca"}, {"id": "b-parca", "baslik": "B Parca"}]


def kos(arac, veri, harita):
    """harita: None (dosya yok) | 'BOZUK' | dict."""
    with open(os.path.join(veri, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(URUNLER, f)
    yol = os.path.join(veri, ".urun-kaynaklari.json")
    if os.path.exists(yol):
        os.remove(yol)
    if harita == "BOZUK":
        with open(yol, "w", encoding="utf-8") as f:
            f.write("{bozuk")
    elif harita is not None:
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(harita, f)
    ortam = dict(os.environ, PRUVO_VERI_KOK=veri)
    r = subprocess.run([sys.executable, arac], capture_output=True, text=True, env=ortam, cwd=veri)
    return r.returncode, r.stdout + r.stderr


def vakalar(arac):
    s = {}
    with tempfile.TemporaryDirectory() as veri:
        rc, o = kos(arac, veri, None)
        s["K1"] = rc == 2 and "KAYNAK HARITASI OKUNAMADI" in o
        rc, o = kos(arac, veri, "BOZUK")
        s["K2"] = rc == 2 and "KAYNAK HARITASI OKUNAMADI" in o
        rc, o = kos(arac, veri, {"a-parca": "https://ornek.gecersiz/1", "b-parca": "https://ornek.gecersiz/2"})
        s["K3"] = rc == 0 and "mukerrer yok" in o
        rc, o = kos(arac, veri, {"a-parca": "https://ornek.gecersiz/1", "b-parca": "https://ornek.gecersiz/1"})
        s["K4"] = rc == 1 and "MUKERRER KAYNAK" in o
    return s


VAKALAR = ["K1", "K2", "K3", "K4"]


def main():
    kirmizi = 0
    taban = vakalar(ARAC)
    for v in VAKALAR:
        ok = taban.get(v) is True
        kirmizi += 0 if ok else 1
        print(("  YESIL   " if ok else "  KIRMIZI ") + v)
    if kirmizi:
        print("SONUC: KIRMIZI %d (taban kirmiziyken mutant olcumu anlamsiz)" % kirmizi)
        return 1
    kaynak = open(ARAC, encoding="utf-8").read()
    capa = "return _kaynak_haritasi_olculemedi()"
    n = kaynak.count(capa)
    with tempfile.TemporaryDirectory() as t:
        if n != 2:
            print("  KIRMIZI M1 — capa iki cagri yerinde bulunmali, isabet " + str(n))
            kirmizi += 1
        else:
            tools = os.path.join(t, "tools")
            os.makedirs(tools)
            shutil.copy(VERI_KOK_MODUL, tools)
            kopya = os.path.join(tools, "mukerrer-kontrol.py")
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, "pass"))
            s = vakalar(kopya)
            yanan = {v for v in VAKALAR if s.get(v) is not True}
            ok = {"K1", "K2"} <= yanan
            kirmizi += 0 if ok else 1
            print(("  YESIL   " if ok else "  KIRMIZI ") + "M1 fail-closed donusu kalkar -> yanan "
                  + (",".join(sorted(yanan)) or "YOK"))
    print("SONUC: " + ("YESIL (%d vaka + 1 mutant)" % len(VAKALAR) if kirmizi == 0 else "KIRMIZI %d" % kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
