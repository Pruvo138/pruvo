#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`cip-supurme.py` mutasyon turu — her mutant HEDEF KOLU oldurdugunu KANITLAR.

🔴 K182: "kirmizi geldi" kanit DEGILDIR. Mutant, DUSEN IDDIANIN ADINI basar; taban
ile AYNI sonuc verirse mutant hedefe ULASMAMISTIR ve kusur BATARYADADIR, kodda degil.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "cip-supurme.py")
TEST = os.path.join(KOK, "tools", "cip-supurme-test.py")

MUTANTLAR = [
    ("M1 AD KUMESI -> TEK AD (K360-A geri gelir)",
     r"if any\(a in kutu_kapanan or a in arsiv_kapanan for a in adlar\):",
     "if adlar[0] in kutu_kapanan or adlar[0] in arsiv_kapanan:",
     ["V1f"]),
    ("M2 ARSIV DUZLEMI kolu kaldirilir (K359-B geri gelir)",
     r"arsiv_kapanan = K\.kapanan_cipler\(a_sat, a_bas\) if not a_hata else set\(\)",
     "arsiv_kapanan = set()",
     ["V1e"]),
    ("M3 YAS ESIGI yok sayilir",
     r"if gun_esigi and \(yas is None or yas < gun_esigi\):",
     "if False:",
     ["V3b"]),
    ("M4 --terk KAPANISI OLANA da yazar (emniyet kalkar)",
     r"hedef = next\(\(s for s in veri\[\"acik\"\] if ad in s\[\"adlar\"\]\), None\)",
     'hedef = {"ad": ad, "adlar": (ad,), "ev": "X", "tarih": "2026-01-01", "yas": 1}',
     ["V5a", "V5c"]),
    ("KONTROL — ilgisiz: rapor baslik metni degisir (DAVRANIS DISI)",
     r"ÇİP SÜPÜRGESİ — kutuda kapanışı OLMAYAN",
     "CIP SUPURGESI (ilgisiz degisiklik) — kutuda kapanışı OLMAYAN",
     []),
]


def taban():
    p = subprocess.run([sys.executable, TEST], capture_output=True, text=True,
                       timeout=300, stdin=subprocess.DEVNULL)
    m = re.search(r"IDDIA=(\d+) GECTI=(\d+) KIRMIZI=(\d+)", p.stdout or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def dusenler(cikti):
    return set(re.findall(r"\[KIRMIZI\] (\w+)", cikti or ""))


def main():
    t = taban()
    if not t or t[2] != 0:
        print("🔴 TABAN YESIL DEGIL — mutasyon turu anlamsiz. taban=%s" % (t,))
        return 2
    print("TABAN: IDDIA=%d GECTI=%d KIRMIZI=%d" % t)
    print()

    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()

    gecici = tempfile.mkdtemp(prefix="cip-supurme-mut-")
    artiklar = []
    oldu = 0
    ulasmadi = 0
    kontrol_ok = True
    try:
        for ad, desen, yerine, beklenen in MUTANTLAR:
            yeni, n = re.subn(desen, yerine, kaynak, count=1)
            if n != 1:
                print("  [ULASMADI] %s — CAPA TUTMADI (desen kaynakta yok)" % ad)
                ulasmadi += 1
                continue
            # 🔴 MUTANT CANLI GOVDEDE YASAR: kopya `tools/` DISINA yazilirsa arac
            # kendi KOK'unu kendi yolundan turettigi icin `kutu-arsivle.py`yi
            # BULAMAZ ve import'ta COKER — dort mutant da "ULASMADI" verir ve kusur
            # koda degil BATARYAYA yazilirdi ([[mutant-canli-govdede-yasamaz]],
            # [[mutant-kopyasi-cokerse-izin-okunur]]). Kopya tools/ ICINE, gizli adla
            # yazilir ve `finally`de MUTLAKA silinir ([[artik-yuzey-mutant-dedektorunu-korlestirir]]).
            yol = os.path.join(KOK, "tools", ".cip-supurme-mutant-%d.py" % os.getpid())
            artiklar.append(yol)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(yeni)
            ort = dict(os.environ, CIP_SUPURME_ARAC=yol)
            p = subprocess.run([sys.executable, TEST], capture_output=True, text=True,
                               timeout=300, env=ort, stdin=subprocess.DEVNULL)
            m = re.search(r"KIRMIZI=(\d+)", p.stdout or "")
            kirmizi = int(m.group(1)) if m else -1
            dusen = dusenler(p.stdout)

            if not beklenen:  # KONTROL mutanti: YESIL kalmali
                if kirmizi == 0:
                    print("  [OK]   %s -> KIRMIZI=0 (davranis disi, dogru)" % ad)
                else:
                    print("  [KIRMIZI] %s -> KIRMIZI=%d BEKLENMIYORDU: %s"
                          % (ad, kirmizi, sorted(dusen)))
                    kontrol_ok = False
                continue

            hedef_dustu = [b for b in beklenen if any(d.startswith(b) for d in dusen)]
            if kirmizi == 0:
                print("  [ULASMADI] %s -> taban ile AYNI (KIRMIZI=0); kusur BATARYADA" % ad)
                ulasmadi += 1
            elif len(hedef_dustu) == len(beklenen):
                oldu += 1
                print("  [OLDU] %s" % ad)
                print("         OLDURDUGU KOL: %s  (toplam dusen=%d)"
                      % (", ".join(sorted(dusen)), kirmizi))
            else:
                print("  [KIRMIZI] %s -> kirmizi VAR ama HEDEF KOL dusmedi "
                      "(beklenen=%s, dusen=%s)" % (ad, beklenen, sorted(dusen)))
                ulasmadi += 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        for y in artiklar:
            try:
                os.remove(y)
            except OSError:
                pass
        kalan = [y for y in artiklar if os.path.exists(y)]
        print()
        print("TEMIZLIK: mutant artigi kalan=%d %s" % (len(kalan), kalan or ""))

    hedefli = [m for m in MUTANTLAR if m[3]]
    print()
    print("=" * 70)
    print("MUTANT=%d/%d OLDU · ULASMADI=%d · KONTROL=%s"
          % (oldu, len(hedefli), ulasmadi, "YESIL" if kontrol_ok else "KIRMIZI"))
    return 0 if (oldu == len(hedefli) and kontrol_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
