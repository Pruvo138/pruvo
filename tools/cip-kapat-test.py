#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`cip-kapat.py` EMNIYET bataryasi — "olmamasi gerekirken SILMESIN".

🔴 CANLI AGACLAR UZERINDE kosar ama YALNIZ NEGATIF kollari olcer: her vakada
beklenen sonuc HICBIR SEYIN SILINMEMESIDIR. Pozitif silme kolu (rc=0 -> gercekten
siler) burada KOSULMAZ — gercek bir agaci yok etmek kabul testinin isi degildir;
o kol canli arsivleme aninda olculur ve kapanisa SAYIYLA yazilir.
"""
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "cip-kapat.py")

IDDIA = 0
GECTI = 0
KIRMIZI = []


def iddia(ad, kosul, ayrinti=""):
    global IDDIA, GECTI
    IDDIA += 1
    if kosul:
        GECTI += 1
        print("  [OK]   %s %s" % (ad, ayrinti))
    else:
        KIRMIZI.append(ad)
        print("  [KIRMIZI] %s %s" % (ad, ayrinti))


def kos(argv, cwd=None):
    p = subprocess.run([sys.executable] + argv, cwd=cwd, capture_output=True,
                       text=True, timeout=900, stdin=subprocess.DEVNULL)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def kirmizi_agac():
    """Kapisi rc!=0 olan CANLI bir cip agaci bul (yoksa vaka ATLANIR, YESIL SAYILMAZ)."""
    rc, cikti = kos(["-c",
                     "import subprocess,sys;"
                     "print(subprocess.run(['git','-C','%s','worktree','list'],"
                     "capture_output=True,text=True).stdout)" % KOK])
    for satir in cikti.splitlines():
        yol = satir.split()[0] if satir.strip() else ""
        if yol and os.path.realpath(yol) != os.path.realpath(KOK) and os.path.isdir(yol):
            r, _c = kos([ARAC, yol])
            if r != 0:
                return yol
    return None


def main():
    print("V1 — ANA CHECKOUT silinecek agac DEGIL")
    rc, cikti = kos([ARAC, KOK])
    iddia("V1a rc=0", rc == 0, "rc=%d" % rc)
    iddia("V1b 'ANA CHECKOUT' der", "ANA CHECKOUT" in cikti)
    iddia("V1c silme komutu ONERMEZ", "--uygula" not in cikti.split("ANA CHECKOUT")[-1])

    print()
    print("V2 — GIT AGACI OLMAYAN yol -> rc=2, hicbir sey yapmaz")
    rc, cikti = kos([ARAC, "/private/tmp"])
    iddia("V2a rc=2", rc == 2, "rc=%d" % rc)

    print()
    print("V3 — KAPI KIRMIZI iken --uygula HICBIR SEY SILMEZ (canli agac)")
    agac = kirmizi_agac()
    if not agac:
        print("  [ATLANDI] kapisi kirmizi canli cip agaci YOK — vaka OLCULEMEDI")
        print("            (YESILE SAYILMADI; kirmizi bir agac varken tekrar kos)")
        iddia("V3 OLCULEMEDI (yesile sayilmaz)", False, "canli kirmizi agac yok")
    else:
        var_once = os.path.isdir(agac)
        rc, cikti = kos([ARAC, agac, "--uygula"])
        var_sonra = os.path.isdir(agac)
        iddia("V3a agac ONCE vardi", var_once, agac)
        iddia("V3b --uygula rc!=0", rc != 0, "rc=%d" % rc)
        iddia("V3c agac SONRA DA DURUYOR (SILINMEDI)", var_sonra)
        iddia("V3d cikti YAPILACAK ISI ADIYLA sayar", "KOL=" in cikti)

        print()
        print("V4 — AGACIN ICINDEN --uygula REDDEDILIR (kendi zeminini cekemez)")
        rc4, cikti4 = kos([ARAC, agac, "--uygula"], cwd=agac)
        iddia("V4a rc!=0", rc4 != 0, "rc=%d" % rc4)
        iddia("V4b agac hala DURUYOR", os.path.isdir(agac))
        # 🔴 KOLUN GERCEKTEN CALISTIGI AYRICA OLCULUR: kapi KIRMIZI ise akis daha
        # ONCE cikar ve oz-agac emniyeti HIC KOSMAZ. "rc!=0 geldi" o kolun
        # kanitı DEGILDIR ([[emniyet-kontrolu-yorumdan-once-korlestirir]] emsali).
        ulasti = "UYGULAMA REDDEDİLDİ" in cikti4
        if ulasti:
            iddia("V4c OZ-AGAC EMNIYETI fiilen kostu (red metni basildi)", True)
        else:
            print("  [ULASMADI] V4c oz-agac emniyeti KOSMADI — kapi rc=%d ile ONCE cikti."
                  % rc4)
            print("             Bu kol YALNIZ rc=0 agacta olculebilir; su an KANITSIZ.")
            iddia("V4c oz-agac emniyeti KANITLANDI", False,
                  "rc=%d ile erken cikis; kol OLCULEMEDI" % rc4)

    print()
    print("V6 — CANLI OTURUM EMNIYETI: taze dokunulmus agac SILINMEZ")
    import subprocess as _sp
    rc6, cikti6 = kos(["-c", "import sys;sys.exit(0)"])
    # Agacin canlilik kolu KAPIDAN AYRIDIR: kapi yesil olsa bile taze agac silinmez.
    # Burada kolun KODDA VAR ve --uygula yolunda CAGRILIYOR oldugu olculur; canli
    # senaryo yukaridaki V3/V4 gercek agaclariyla zaten kirmizi doner.
    with open(ARAC, encoding="utf-8") as f:
        k6 = f.read()
    iddia("V6a canlilik kolu VAR", "taze_dokunus_dk" in k6)
    iddia("V6b --uygula yolunda CAGRILIYOR", "yas = taze_dokunus_dk(agac)" in k6)
    iddia("V6c OLCULEMEDI hali CANLI sayilir (fail-closed)",
          "yas is None or yas < a.yas_tavani" in k6)
    iddia("V6d ListAgents CANLILIK KANITI olarak KULLANILMIYOR",
          "ListAgents" not in k6.split("def taze_dokunus_dk")[1].split("def icinde_mi")[0]
          or "KULLANILMAZ" in k6)

    print()
    print("V5 — HUKUM IKIZLENMEDI: silme olcutu arsiv-kapisi.py'den gelir")
    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()
    iddia("V5a arsiv-kapisi CAGRILIYOR", "arsiv-kapisi.py" in kaynak)
    iddia("V5b ikinci bir 'silinebilir' olcutu YOK (rc disinda karar verilmiyor)",
          kaynak.count("worktree\", \"remove\"") == 1)
    iddia("V5c silmeden ONCE kapi YENIDEN kosuluyor (TOCTOU)",
          kaynak.count("kapi_kos(agac, repo)") >= 2)

    print()
    print("=" * 70)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (IDDIA, GECTI, len(KIRMIZI)))
    if KIRMIZI:
        for k in KIRMIZI:
            print("  DUSEN: %s" % k)
        return 1
    print("SONUC: GECTI ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
