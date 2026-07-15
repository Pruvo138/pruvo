"""PRUVO Ortak Drive'indaki STL klasorunun yolunu bulur — hesap adi degisse bile.

Neden var: yol, hesabin e-postasini iceriyor (.../GoogleDrive-info@pruvo3d.com/Ortak Drive'lar/...).
Hesap yeniden adlandirilinca (15 Tem 2026: info@gocekbroker.com -> info@pruvo3d.com) Drive
uygulamasi mount klasorunun adini degistirir ve `.stl-backup-dir` bayatlar.

Eskiden bu SESSIZCE kiriliyordu, en tehlikeli yaniydi:
  - thingiverse-fetch/printables-fetch: `if os.path.isdir(bdir)` -> yedegi sessizce ATLAR
  - yedekle.py / thing-hazirla.py: `os.makedirs(...)` -> Drive yerine SAHTE yerel klasor yaratir
Iki durumda da "yedek aliniyor" sanip yedeksiz kalirdin.

Artik: (1) kayitli yolu dene, (2) tutmazsa mount'lari tara ve `.stl-backup-dir`'i kendin duzelt,
(3) hicbiri olmazsa GURULTULU uyar — sessizce gecme.
"""
import glob
import os
import sys

ROOT = "/Users/okan/dev/pruvo"
CFG = os.path.join(ROOT, ".stl-backup-dir")
# Hesap adi degisebilir -> GoogleDrive-* joker. Ortak Drive adi ("PRUVO/Pruvo") sabit.
DESEN = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Ortak Drive'lar/PRUVO/Pruvo/STL")


def stl_dizini(sessiz=False):
    """Canli STL klasoru yolunu dondurur; bulunamazsa None (ve uyarir).

    Bayat `.stl-backup-dir`'i bulursa kendisi duzeltir — bir dahaki sefere tarama gerekmez.
    """
    kayitli = open(CFG).read().strip() if os.path.exists(CFG) else ""
    if kayitli and os.path.isdir(kayitli):
        return kayitli

    bulunan = sorted(glob.glob(DESEN))
    if bulunan:
        yeni = bulunan[0]
        try:
            with open(CFG, "w") as w:
                w.write(yeni)
            if not sessiz:
                print("NOT: Drive yolu degismis, .stl-backup-dir duzeltildi -> " + yeni, file=sys.stderr)
        except Exception as e:
            if not sessiz:
                print("NOT: Drive yolu bulundu ama .stl-backup-dir yazilamadi: " + str(e), file=sys.stderr)
        return yeni

    if not sessiz:
        print(
            "UYARI: PRUVO Ortak Drive'i bulunamadi -> STL YEDEGI ALINMIYOR.\n"
            "  Kayitli yol: " + (kayitli or "(yok)") + "\n"
            "  Drive uygulamasi acik mi? Hesap baglantisi duruyor mu? (Hesap adi degistiyse\n"
            "  klasor adi da degisir; Drive'i acip yeniden giris yapmak yeter.)",
            file=sys.stderr,
        )
    return None


def pruvo_dizini(sessiz=False):
    """STL'in ust klasoru (.../Pruvo) — backup/ ve lisans belge/ orada. Yoksa None."""
    stl = stl_dizini(sessiz=sessiz)
    return os.path.dirname(stl) if stl else None
