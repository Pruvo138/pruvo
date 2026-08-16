#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-rotasyon-test.py — Fikstur + mutant + pre-commit RED provasi.

Gercek DEVAM.md / DEVAM-ARSIV.md / pre-commit uzerinde CALISMAZ; tempfile
altinda sentetik veri kurar. Cikti son satiri:

    FIKSTUR=<g/t> MUTANT=<OLDU|SURVIVOR> RED_RC=<n> KONTROL_RC=<n> KAPSAM_RC=<n> CARE_SATIRI=<VAR|YOK> SAYAC_YOL=<yol> SAYAC_SATIR=<n>
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROTASYON = os.path.join(TOOLS, "defter-rotasyon.py")
PRE_COMMIT_KAYNAK = os.path.join(TOOLS, "kancalar", "pre-commit")


def _fikstur_defter():
    return (
        "# Baslik bolgesi\n"
        "Bu kisim asla tasinmamalidir.\n"
        "\n"
        "## A — OTURUM KAPANISI 2026-08-10 ✅\n"
        "- Satir 1\n"
        "- Satir 2\n"
        "\n"
        "## B — ACIK KALEMLER\n"
        "- Bu blokta 🔴 acik isaretci var, kalmali.\n"
        "\n"
        "## C — X KAPANDI ✅\n"
        "- Bu blok kapanis isaretcisi tasiyor, tasinmali.\n"
        "\n"
        "## D — OKAN'DA\n"
        "- Bu blokta acik isaretci var, kalmali.\n"
        "\n"
        "## E — Y KAPANDI ✅ ama 🔧 yapilacak\n"
        "- Hem kapanis hem acik isaretci iceren karisik blok, kalmali.\n"
    )


def _kur(tmp, tarih="2026-08-16"):
    defter = os.path.join(tmp, "DEVAM.md")
    arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write(_fikstur_defter())
    with open(arsiv, "w", encoding="utf-8") as f:
        f.write("## Eski arsiv basligi\n- Eski kayit\n")
    return defter, arsiv, tarih


def _kostur(defter, arsiv, tarih="2026-08-16"):
    r = subprocess.run(
        [sys.executable, ROTASYON, defter, arsiv, "--tarih", tarih],
        capture_output=True, text=True)
    return r


def _bloklar(metin):
    """Baslik bolgesi haric blok basliklarini sirayla dondur."""
    basladi = False
    basliklar = []
    for satir in metin.splitlines():
        if satir.startswith("## "):
            basladi = True
            basliklar.append(satir)
        elif not basladi:
            continue
    return basliklar


def fikstur_test():
    hatalar = []
    kontrol = 0

    with tempfile.TemporaryDirectory() as tmp:
        defter, arsiv, tarih = _kur(tmp)
        eski_defter = open(defter, encoding="utf-8").read()
        eski_arsiv = open(arsiv, encoding="utf-8").read()

        r = _kostur(defter, arsiv, tarih)
        if r.returncode != 0:
            hatalar.append("F1 rotasyon basarisiz (rc=%d): %s" % (r.returncode, r.stderr))
            return hatalar, kontrol

        yeni_defter = open(defter, encoding="utf-8").read()
        yeni_arsiv = open(arsiv, encoding="utf-8").read()

        # F1: tasinanlar dogru (A, C)
        kontrol += 1
        arsiv_basliklar = _bloklar(yeni_arsiv)
        if not (any("A — OTURUM KAPANISI" in b for b in arsiv_basliklar) and
                any("C — X KAPANDI" in b for b in arsiv_basliklar)):
            hatalar.append("F1 tasinanlar yanlis: arsiv basliklari %r" % arsiv_basliklar)
        if any("B — ACIK KALEMLER" in b for b in arsiv_basliklar):
            hatalar.append("F1 B blogu yanlislikla tasindi")
        if any("D — OKAN'DA" in b for b in arsiv_basliklar):
            hatalar.append("F1 D blogu yanlislikla tasindi")
        if any("E — Y KAPANDI" in b for b in arsiv_basliklar):
            hatalar.append("F1 E blogu yanlislikla tasindi")

        # F2: kalanlar yerinde ve sirasi bozulmamis
        kontrol += 1
        defter_basliklar = _bloklar(yeni_defter)
        beklenen = [
            "## B — ACIK KALEMLER",
            "## D — OKAN'DA",
            "## E — Y KAPANDI ✅ ama 🔧 yapilacak",
        ]
        if defter_basliklar != beklenen:
            hatalar.append("F2 kalanlar sirasi bozuk: %r (beklenen %r)" % (
                defter_basliklar, beklenen))

        # F3: arsiv buyudu
        kontrol += 1
        if len(yeni_arsiv.encode("utf-8")) <= len(eski_arsiv.encode("utf-8")):
            hatalar.append("F3 arsiv buyumedu")

        # F4: defterden cikarilan icerik arsive eklenmis (kayip yok).
        kontrol += 1
        defter_azalma = len(eski_defter.encode("utf-8")) - len(yeni_defter.encode("utf-8"))
        arsiv_artis = len(yeni_arsiv.encode("utf-8")) - len(eski_arsiv.encode("utf-8"))
        if arsiv_artis < defter_azalma:
            hatalar.append("F4 icerik kayboldu: defter -%d bayt, arsiv +%d bayt" % (
                defter_azalma, arsiv_artis))

        # F5: tasinacak blok yokken dosyalar degismemeli
        kontrol += 1
        with tempfile.TemporaryDirectory() as tmp2:
            defter2 = os.path.join(tmp2, "DEVAM.md")
            arsiv2 = os.path.join(tmp2, "DEVAM-ARSIV.md")
            with open(defter2, "w", encoding="utf-8") as f:
                f.write("# Baslik\n## A — ACIK KALEMLER\n- 🔴 acik\n")
            with open(arsiv2, "w", encoding="utf-8") as f:
                f.write("## Eski\n- kayit\n")
            r2 = _kostur(defter2, arsiv2, tarih)
            if r2.returncode != 0:
                hatalar.append("F5 rc != 0: %s" % r2.stderr)
            d2_ici = open(defter2, encoding="utf-8").read()
            a2_ici = open(arsiv2, encoding="utf-8").read()
            if d2_ici != "# Baslik\n## A — ACIK KALEMLER\n- 🔴 acik\n":
                hatalar.append("F5 defter degisti (tasinacak yokken)")
            if a2_ici != "## Eski\n- kayit\n":
                hatalar.append("F5 arsiv degisti (tasinacak yokken)")

        # F6: baslik bolgesi hic tasinmadi
        kontrol += 1
        if "Baslik bolgesi" not in yeni_defter:
            hatalar.append("F6 baslik bolgesi defterden kayboldu")
        if "Baslik bolgesi" in yeni_arsiv:
            hatalar.append("F6 baslik bolgesi arsive gecti")

    return hatalar, kontrol


def mutant_test():
    """Aci isaretci vetosunu devre disi birakan mutant uret; F1/F2'yi kir."""
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    eski = "    for isaretci in ACIK_ISARETCILER:\n"
    yeni = "    for isaretci in []:  # mutant: acik isaretci vetosu devre disi\n"
    if eski not in govde:
        return None, "MUTANT CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-defter-rotasyon.py")
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(_fikstur_defter())
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("## Eski arsiv basligi\n- Eski kayit\n")

        r = subprocess.run(
            [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
            capture_output=True, text=True)

        if r.returncode != 0:
            return True, "mutant kirmizi yandi (rc=%d)" % r.returncode

        yeni_defter = open(defter, encoding="utf-8").read()
        yeni_arsiv = open(arsiv, encoding="utf-8").read()
        arsiv_basliklar = _bloklar(yeni_arsiv)
        defter_basliklar = _bloklar(yeni_defter)

        bozuk = False
        sebep = []
        if not (any("A — OTURUM KAPANISI" in b for b in arsiv_basliklar) and
                any("C — X KAPANDI" in b for b in arsiv_basliklar)):
            bozuk = True
            sebep.append("A/C tasinmadi")
        if any("B — ACIK KALEMLER" in b for b in arsiv_basliklar):
            bozuk = True
            sebep.append("B tasindi")
        if any("D — OKAN'DA" in b for b in arsiv_basliklar):
            bozuk = True
            sebep.append("D tasindi")
        if any("E — Y KAPANDI" in b for b in arsiv_basliklar):
            bozuk = True
            sebep.append("E tasindi")
        if defter_basliklar != []:
            bozuk = True
            sebep.append("defterde kalanlar yanlis: %r" % defter_basliklar)

        if bozuk:
            return True, "mutant F1/F2'yi bozdu (%s)" % "; ".join(sebep)
        return False, "mutant F1/F2'yi bozMADI (SURVIVOR)"


# ---------------------------------------------------------------------------
# RED PROVASI (pre-commit)
# ---------------------------------------------------------------------------
def _git(kok, args, capture=True, env=None):
    env = env if env is not None else os.environ.copy()
    r = subprocess.run(["git", "-C", kok] + list(args),
                       capture_output=capture, text=True, env=env)
    return r


def _devam_olustur(tmp, satir):
    yol = os.path.join(tmp, "DEVAM.md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("# Defter\n")
        for i in range(1, satir):
            f.write("- Satir %d\n" % i)
    return yol


MINIMAL_PRE_COMMIT = """#!/bin/sh
# Test kancasi: yalnizca defter kota kolunu calistirir.
pruvo_kok=$(git rev-parse --show-toplevel 2>/dev/null)
python3 "$pruvo_kok/tools/defter-kota-kapisi.py" "$pruvo_kok"
pruvo_defter_kota_rc=$?
if [ "$pruvo_defter_kota_rc" -ne 0 ]; then
  exit 1
fi
exit 0
"""


def _sentetik_depo(tmp, sayac_yol):
    _git(tmp, ["init", "-q", "-b", "main"], capture=False)
    _git(tmp, ["config", "user.email", "test@ornek.gecersiz"], capture=False)
    _git(tmp, ["config", "user.name", "Test Kullanici"], capture=False)
    # Kanca icin sadece defter-kota-kapisi.py'yi tools altina koy.
    kanca_tools = os.path.join(tmp, "tools")
    os.makedirs(kanca_tools, exist_ok=True)
    shutil.copy(os.path.join(TOOLS, "defter-kota-kapisi.py"),
                os.path.join(kanca_tools, "defter-kota-kapisi.py"))
    kanca_dizin = os.path.join(tmp, ".git", "hooks")
    os.makedirs(kanca_dizin, exist_ok=True)
    kanca_yol = os.path.join(kanca_dizin, "pre-commit")
    with open(kanca_yol, "w", encoding="utf-8") as f:
        f.write(MINIMAL_PRE_COMMIT)
    os.chmod(kanca_yol, 0o755)
    # Betigin kendi ROOT'unu sentetik depo olarak gormesi icin ortam degiskeni.
    os.environ["PRUVO_DEFTER_KOTA_SAYAC"] = sayac_yol
    return tmp


def red_provasi():
    with tempfile.TemporaryDirectory() as tmp:
        sayac_yol = os.path.join(tmp, "bypass.tsv")
        _sentetik_depo(tmp, sayac_yol)

        # README.md ilk commit
        with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("# depo\n")
        _git(tmp, ["add", "README.md"], capture=False)
        _git(tmp, ["commit", "-q", "-m", "ilk"], capture=False)

        # RED vakasi: 131 satirlik DEVAM.md staged
        _devam_olustur(tmp, 131)
        _git(tmp, ["add", "DEVAM.md"], capture=False)
        r_red = _git(tmp, ["commit", "-m", "red test"])

        # KONTROL vakasi: 129 satirlik DEVAM.md staged
        _devam_olustur(tmp, 129)
        _git(tmp, ["add", "DEVAM.md"], capture=False)
        r_kontrol = _git(tmp, ["commit", "-m", "kontrol test"])

        # KAPSAM vakasi: 131 satirlik DEVAM.md stage disi, baska dosya commit
        _devam_olustur(tmp, 131)
        with open(os.path.join(tmp, "diger.txt"), "w", encoding="utf-8") as f:
            f.write("baska dosya\n")
        _git(tmp, ["add", "diger.txt"], capture=False)
        r_kapsam = _git(tmp, ["commit", "-m", "kapsam test"])

        sayac_satir = 0
        if os.path.exists(sayac_yol):
            with open(sayac_yol, encoding="utf-8") as f:
                sayac_satir = sum(1 for _ in f)

        return r_red, r_kontrol, r_kapsam, sayac_yol, sayac_satir


def main():
    hatalar, kontrol = fikstur_test()
    mutant_oldu, mutant_mesaj = mutant_test()

    r_red, r_kontrol, r_kapsam, sayac_yol, sayac_satir = red_provasi()

    red_rc = r_red.returncode
    kontrol_rc = r_kontrol.returncode
    kapsam_rc = r_kapsam.returncode
    cikti = (r_red.stdout or "") + (r_red.stderr or "")
    care_var = "VAR" if "DEFTER KOTASI ASILDI" in cikti and "CARE:" in cikti else "YOK"

    for h in hatalar:
        print("  ✗ %s" % h, file=sys.stderr)

    # RED provasi iddialari
    if red_rc == 0:
        print("  ✗ RED vakasi RED vermedi (rc=0)", file=sys.stderr)
        hatalar.append("RED vakasi RED vermedi")
    if kontrol_rc != 0:
        print("  ✗ KONTROL vakasi yanlis-pozitif (rc=%d): %s" % (
            kontrol_rc, r_kontrol.stderr), file=sys.stderr)
        hatalar.append("KONTROL vakasi yanlis-pozitif")
    if kapsam_rc != 0:
        print("  ✗ KAPSAM vakasi stage-disini engelledi (rc=%d): %s" % (
            kapsam_rc, r_kapsam.stderr), file=sys.stderr)
        hatalar.append("KAPSAM vakasi stage-disini engelledi")
    if care_var != "VAR":
        print("  ✗ CARE satiri yok; RED ciktisi: %s" % cikti, file=sys.stderr)
        hatalar.append("CARE satiri yok")
    if sayac_satir < 1:
        print("  ✗ Bypass sayaci yazilmadi (%s)" % sayac_yol, file=sys.stderr)
        hatalar.append("bypass sayaci yazilmadi")

    for h in hatalar:
        if h not in ["RED vakasi RED vermedi", "KONTROL vakasi yanlis-pozitif",
                     "KAPSAM vakasi stage-disini engelledi", "CARE satiri yok",
                     "bypass sayaci yazilmadi"]:
            pass  # zaten yukarida basilacak

    mutant_durum = "OLDU" if mutant_oldu else "SURVIVOR"
    gecen = kontrol - len(hatalar)
    print("FIKSTUR=%d/%d MUTANT=%s RED_RC=%d KONTROL_RC=%d KAPSAM_RC=%d CARE_SATIRI=%s SAYAC_YOL=%s SAYAC_SATIR=%d"
          % (gecen, kontrol, mutant_durum, red_rc, kontrol_rc, kapsam_rc,
             care_var, sayac_yol, sayac_satir))

    if hatalar or not mutant_oldu:
        print("MUTANT DETAY: %s" % mutant_mesaj, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
