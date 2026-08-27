#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`--kok` BAYRAGININ KANITI + YEDEK GERI YUKLEME KANITI (27 Agu 2026).

🔴 NEDEN AYRI BIR ARAC: bir bayrak eklemek onun CALISTIGINI kanitlamaz.
`nobet-uc-kol-kabul.py --kok X` calismasa da (yani sessizce yine kurulu
kopyayi olcse de) cikti YESIL yanardi — bu evde tam olarak bu sinif hata
olculdu ([[emir-canliligi-kurulu-kopyadan-olculur]],
[[spec-mutlak-yol-yanlis-agaci-olcer]]). Bayragin kaniti, BOZULMUS bir
agaca yoneltildiginde bataryanin KIRMIZI yanmasidir.

UC KOSUM + BIR GERI YUKLEME (hepsinin ozet satiri BASILIR, farki okunur):

  1. KURULU     — bayraksiz. Bugunku davranis; DEGISMEMIS olmali.
  2. AYNA       — `--kok <kopya>`; kurulu agacin BIREBIR kopyasi.
                  Ozet satiri (1) ile AYNI olmali. Bayrak burada
                  "hicbir seyi bozmuyor" der.
  3. BOZUK      — `--kok <kopya2>`; kopyada KOL D'nin ardisik esik satiri
                  `elif False:` yapilmis. Batarya KIRMIZI yanmali ve
                  DUSEN_VAKALAR icinde C5b GECMELI. 🔴 KANIT BUDUR:
                  bayrak gercekten VERILEN agaci okuyor; okumasaydi (1) ile
                  ayni yesili basardi.
  4. GERI_YUKLEME — verilen `.yedek-*` dosyasi bir kopyaya GERI YUKLENIR ve
                  batarya orada kosturulur. Yedegin kaniti rc=0 degil
                  GERI YUKLEMEDIR ([[yedek-kaniti-geri-yuklemeyle-olculur]]);
                  ustelik geri yuklenen surumun ozeti (1)'den FARKLI cikarsa
                  yedek gercekten ESKI surumdur, ayni dosyanin kopyasi degil.

Agac kopyasi SEMBOLIK BAG CIFTLIGIDIR: `nobet-kapi.py`/`gozcu.py` kardes
modulleri (kilit, nobet_devir, _nobet_bekci ...) duz `import` ile cagirir,
o yuzden koke YALNIZ dort dosyayi kopyalamak `ModuleNotFoundError` uretir.
Ciftlikte her giris kurulu koke BAGLANIR, yalnizca olculecek dosya GERCEK
KOPYA olur — boylece kopya tam, ama yazma kurulu duzleme SIZMAZ.

Kullanim:
    python3 tools/nobet-kok-bayragi-kaniti.py
    python3 tools/nobet-kok-bayragi-kaniti.py --yedek /yol/....yedek-...

Cikti: her kosum icin `KOSUM <ad> rc=<n> <KABUL ozet satiri>` + son ozet
    KOK_KANITI KOSUM=<gecen>/<toplam> DUSEN=<n>
Cikis: 0 = dort iddia da yesil · 1 = en az bir kirmizi · 2 = arac hatasi.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable or "python3"

# Kol D'nin ardisik esik satiri — BOZUK agacta bunu olduruyoruz.
KOL_D_SATIRI = "        elif rc != 0 and _ardisik >= GENEL_ARDISIK_ESIGI:"
KOL_D_OLU = "        elif False:"

_SAYAC = {"iddia": 0, "gecen": 0}
_DUSENLER = []


def olc(ad, beklenen, gozlenen):
    _SAYAC["iddia"] += 1
    tamam = (beklenen == gozlenen)
    if tamam:
        _SAYAC["gecen"] += 1
    else:
        _DUSENLER.append(ad)
        sys.stderr.write("[DUSTU] %s\n  beklenen=%r\n  gozlenen=%r\n"
                         % (ad, beklenen, gozlenen))
    print("IDDIA %-46s %s" % (ad, "GECTI" if tamam else "DUSTU"))
    return tamam


def ciftlik(kurulu_kok, dizin):
    """Kurulu koku SEMBOLIK BAG ciftligi olarak `dizin`e yansitir."""
    for ad in os.listdir(kurulu_kok):
        kaynak = os.path.join(kurulu_kok, ad)
        hedef = os.path.join(dizin, ad)
        try:
            os.symlink(kaynak, hedef)
        except OSError:
            pass
    return dizin


def gercek_kopya(dizin, ad):
    """Ciftlikteki bir BAGI gercek dosya kopyasiyla degistirir ve icerigini doner."""
    yol = os.path.join(dizin, ad)
    hedef = os.path.realpath(yol)
    with open(hedef, encoding="utf-8") as f:
        metin = f.read()
    if os.path.islink(yol):
        os.unlink(yol)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return yol, metin


def kabul_kos(kabul_yolu, kok=None):
    """(rc, ozet_satiri, dusen_vakalar) — KABUL bataryasini kosturur."""
    argv = [PY, kabul_yolu]
    if kok:
        argv += ["--kok", kok]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=1200)
    cikti = (r.stdout or "") + (r.stderr or "")
    ozet, dusen = "-", "-"
    for satir in cikti.splitlines():
        if satir.startswith("KABUL VAKA="):
            ozet = satir.strip()
        elif satir.startswith("DUSEN_VAKALAR="):
            dusen = satir.split("=", 1)[1].strip()
    return r.returncode, ozet, dusen, cikti


def main(argv=None):
    burada = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kurulu-kok", default=os.path.join(
        os.path.expanduser("~"), ".claude", "cron"))
    ap.add_argument("--kabul", default=os.path.join(
        burada, "nobet-uc-kol-kabul.py"))
    ap.add_argument("--yedek", default=None, metavar="YOL",
                    help="isci-karantina-karar.py'nin `.yedek-*` kopyasi; "
                         "GERI YUKLEME kanitinda kullanilir")
    a = ap.parse_args(argv)

    kurulu = os.path.abspath(os.path.expanduser(a.kurulu_kok))
    kabul = os.path.abspath(os.path.expanduser(a.kabul))
    print("=== --kok BAYRAK KANITI ===")
    print("KURULU_KOK=%s var=%d" % (kurulu, int(os.path.isdir(kurulu))))
    print("KABUL=%s var=%d" % (kabul, int(os.path.isfile(kabul))))
    if not os.path.isdir(kurulu) or not os.path.isfile(kabul):
        return 2

    # --- 1. KURULU (bayraksiz) --------------------------------------------
    rc1, ozet1, dusen1, _ = kabul_kos(kabul)
    print("KOSUM 1-KURULU        rc=%d %s" % (rc1, ozet1))
    olc("1 kurulu kosum YESIL", (0, "-"), (rc1, dusen1))

    gecici = tempfile.mkdtemp(prefix="kok-kanit-")
    try:
        # --- 2. AYNA (--kok, birebir kopya) -------------------------------
        ayna = os.path.join(gecici, "ayna")
        os.makedirs(ayna, exist_ok=True)
        ayna = ciftlik(kurulu, ayna)
        for ad in ("ci-nobeti.sh", "nobet-kapi.py", "gozcu.py",
                   "isci-karantina-karar.py"):
            yol, _m = gercek_kopya(ayna, ad)
            if ad.endswith(".sh"):
                os.chmod(yol, 0o755)
        rc2, ozet2, dusen2, _ = kabul_kos(kabul, ayna)
        print("KOSUM 2-AYNA          rc=%d %s" % (rc2, ozet2))
        olc("2 ayna kosumu KURULU ile AYNI", (rc1, ozet1), (rc2, ozet2))

        # --- 3. BOZUK (--kok, Kol D olduruldu) ----------------------------
        bozuk = os.path.join(gecici, "bozuk")
        os.makedirs(bozuk, exist_ok=True)
        bozuk = ciftlik(kurulu, bozuk)
        for ad in ("ci-nobeti.sh", "nobet-kapi.py", "gozcu.py",
                   "isci-karantina-karar.py"):
            yol, _m = gercek_kopya(bozuk, ad)
            if ad.endswith(".sh"):
                os.chmod(yol, 0o755)
        kar = os.path.join(bozuk, "isci-karantina-karar.py")
        with open(kar, encoding="utf-8") as f:
            metin = f.read()
        n = metin.count(KOL_D_SATIRI)
        if n != 1:
            olc("3 bozuk agac CAPASI TEK", 1, n)
        else:
            with open(kar, "w", encoding="utf-8") as f:
                f.write(metin.replace(KOL_D_SATIRI, KOL_D_OLU, 1))
            rc3, ozet3, dusen3, _ = kabul_kos(kabul, bozuk)
            print("KOSUM 3-BOZUK         rc=%d %s" % (rc3, ozet3))
            print("      DUSEN_VAKALAR=%s" % dusen3)
            # 🔴 KANIT: bayrak VERILEN agaci okuyor. Okumasaydi 1-KURULU ile
            # ayni YESIL basardi; burada C5b KIRMIZI yanmali.
            olc("3 bozuk agacta C5b KIRMIZI (bayrak GERCEKTEN yoneliyor)",
                (1, True), (rc3, "C5b" in dusen3))
            olc("3 bozuk kosum KURULU'dan FARKLI", True, ozet3 != ozet1)

        # --- 4. GERI YUKLEME kaniti ---------------------------------------
        if not a.yedek:
            print("KOSUM 4-GERI_YUKLEME  ATLANDI (--yedek verilmedi)")
        else:
            yedek = os.path.abspath(os.path.expanduser(a.yedek))
            if not os.path.isfile(yedek):
                olc("4 yedek dosyasi VAR", True, False)
            else:
                geri = os.path.join(gecici, "geri")
                os.makedirs(geri, exist_ok=True)
                geri = ciftlik(kurulu, geri)
                for ad in ("ci-nobeti.sh", "nobet-kapi.py", "gozcu.py",
                           "isci-karantina-karar.py"):
                    yol, _m = gercek_kopya(geri, ad)
                    if ad.endswith(".sh"):
                        os.chmod(yol, 0o755)
                hedef = os.path.join(geri, "isci-karantina-karar.py")
                shutil.copyfile(yedek, hedef)
                with open(hedef, "rb") as f:
                    geri_bayt = f.read()
                with open(yedek, "rb") as f:
                    yedek_bayt = f.read()
                olc("4a yedek BAYT-BIREBIR geri yuklendi",
                    True, geri_bayt == yedek_bayt)
                rc4, ozet4, dusen4, _ = kabul_kos(kabul, geri)
                print("KOSUM 4-GERI_YUKLEME  rc=%d %s" % (rc4, ozet4))
                print("      DUSEN_VAKALAR=%s" % dusen4)
                # Geri yuklenen surum GERCEKTEN eski surumse ozeti KURULU'dan
                # farkli olmalidir (aksi halde "yedek" ayni dosyanin kopyasidir
                # ve geri yukleme hicbir sey KANITLAMAZ).
                olc("4b geri yuklenen surum KURULU'dan FARKLI",
                    True, ozet4 != ozet1)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("KOK_KANITI KOSUM=%d/%d DUSEN=%d"
          % (_SAYAC["gecen"], _SAYAC["iddia"], len(_DUSENLER)))
    if _DUSENLER:
        print("DUSEN_IDDIALAR=%s" % ",".join(_DUSENLER))
    return 0 if not _DUSENLER else 1


if __name__ == "__main__":
    sys.exit(main())
