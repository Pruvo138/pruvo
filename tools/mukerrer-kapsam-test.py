#!/usr/bin/env python3
"""Mukerrer kapisinin pre-commit yargi kapsamini izole depolarda sinar."""

import json
import os
import shutil
import subprocess
import sys
import tempfile


TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "mukerrer-kontrol.py")
TEMIZ = [
    {"id": "urun-a", "baslik": "Baslik A"},
    {"id": "urun-b", "baslik": "Baslik B"},
]
MUKERRER = [
    {"id": "urun-a", "baslik": "Ayni Baslik"},
    {"id": "urun-b", "baslik": "Ayni Baslik"},
]


def _kos(kok, *args):
    return subprocess.run(
        [sys.executable, os.path.join(kok, "tools", "mukerrer-kontrol.py")] + list(args),
        cwd=kok,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _git(kok, *args):
    return subprocess.run(
        ["git", "-C", kok] + list(args),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _yaz(path, veri):
    with open(path, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False)
        dosya.write("\n")


def _depo(ilk=TEMIZ, commit=True):
    gecici = tempfile.TemporaryDirectory(prefix="pruvo-mukerrer-kapsam-")
    kok = gecici.name
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(KAPI, os.path.join(kok, "tools", "mukerrer-kontrol.py"))
    _git(kok, "init", "-q")
    _git(kok, "config", "user.name", "Kapsam Testi")
    _git(kok, "config", "user.email", "kapsam@example.invalid")
    _yaz(os.path.join(kok, "urunler.json"), ilk)
    if commit:
        _git(kok, "add", "urunler.json", "tools/mukerrer-kontrol.py")
        _git(kok, "commit", "-q", "--no-verify", "-m", "taban")
    return gecici, kok


def _a1():
    gecici, kok = _depo()
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        with open(os.path.join(kok, "alakasiz.py"), "w", encoding="utf-8") as dosya:
            dosya.write("DEGER = 1\n")
        _git(kok, "add", "alakasiz.py")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode == 0, sonuc
    finally:
        gecici.cleanup()


def _a2():
    gecici, kok = _depo()
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode != 0 and "MUKERRER BASLIK" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


def _a3():
    gecici, kok = _depo([{"id": "eski", "baslik": "Mevcut Baslik"}])
    try:
        _yaz(os.path.join(kok, "urunler.json"), [
            {"id": "yeni", "baslik": "Mevcut Baslik"},
            {"id": "eski", "baslik": "Mevcut Baslik"},
        ])
        _git(kok, "add", "urunler.json")
        sonuc = _kos(kok, "--pre-commit")
        return sonuc.returncode != 0 and "yeni, eski" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


def _a4():
    gecici, kok = _depo(TEMIZ, commit=False)
    try:
        sonuc = _kos(kok, "--pre-commit")
        return (
            sonuc.returncode != 0
            and "COMMIT KAYNAGI OKUNAMADI" in sonuc.stdout
            and "calisma agaci tarandi" in sonuc.stdout
        ), sonuc
    finally:
        gecici.cleanup()


def _a5():
    gecici, kok = _depo()
    try:
        _yaz(os.path.join(kok, "urunler.json"), MUKERRER)
        sonuc = _kos(kok)
        return sonuc.returncode != 0 and "MUKERRER BASLIK" in sonuc.stdout, sonuc
    finally:
        gecici.cleanup()


# ══════════════════════════════════════════════════════════════════════════════
# A6-A8 — ISTISNA KAYDI WORKTREE'DE DE GORULMELI (16 Agu 2026, olculdu)
# ══════════════════════════════════════════════════════════════════════════════
# `.mukerrer-istisna.json` .gitignore'dadir; `git worktree add` IZLENMEYEN dosyalari
# TASIMAZ. Olculen sonuc: AYNI HEAD icin ana agacta rc=0, worktree'de rc=1 — hukum
# AGACA GORE degisiyordu. Bedeli: iki tur kancayi ATLADI, `k119e` worktree'si
# temizlenemedi, urun verisine HIC dokunmayan commit'ler bile bloklandi.
# A6 dogru davranisi, A7+A8 ise duzeltmenin KAPSAMINI (fail-closed kalmasini) tutar.
KAYNAK_URL = "https://example.invalid/paylasilan-kaynak"


def _paylasilan_kaynak_deposu(istisna=None):
    """(gecici, ana_kok, worktree_kok) — ayni kaynagi paylasan IKI urun + worktree.

    `.urun-kaynaklari.json` COMMIT'LENIR (gercekte izlenen dosya), `.mukerrer-istisna.json`
    ise YALNIZ ana agaca IZLENMEDEN yazilir (gercekte .gitignore'da)."""
    gecici, kok = _depo()
    _yaz(os.path.join(kok, ".urun-kaynaklari.json"),
         {"urun-a": {"link": KAYNAK_URL}, "urun-b": {"link": KAYNAK_URL}})
    _git(kok, "add", ".urun-kaynaklari.json")
    _git(kok, "commit", "-q", "--no-verify", "-m", "kaynaklar")
    if istisna is not None:
        _yaz(os.path.join(kok, ".mukerrer-istisna.json"), istisna)
    wt = os.path.join(kok, "wt")
    _git(kok, "worktree", "add", "-q", "-b", "dal", wt)
    return gecici, kok, wt


def _a6():
    gecici, _kok, wt = _paylasilan_kaynak_deposu([{"kaynak": KAYNAK_URL}])
    try:
        sonuc = _kos(wt, "--pre-commit")
        return sonuc.returncode == 0, sonuc
    finally:
        gecici.cleanup()


def _a7():
    gecici, _kok, wt = _paylasilan_kaynak_deposu(None)
    try:
        sonuc = _kos(wt, "--pre-commit")
        return (sonuc.returncode != 0
                and "MUKERRER KAYNAK" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def _a8():
    gecici, _kok, wt = _paylasilan_kaynak_deposu(
        [{"kaynak": "https://example.invalid/BASKA-kaynak"}])
    try:
        sonuc = _kos(wt, "--pre-commit")
        return (sonuc.returncode != 0
                and "MUKERRER KAYNAK" in sonuc.stdout), sonuc
    finally:
        gecici.cleanup()


def main():
    iddialar = [
        ("A1 yabanci veri bloklamaz", _a1),
        ("A2 staged mukerrer yakalanir", _a2),
        ("A3 HEAD'e karsi mukerrer yakalanir", _a3),
        ("A4 okuma hatasi fail-closed", _a4),
        ("A5 bayraksiz tam katalog korunur", _a5),
        ("A6 worktree ANA AGACTAKI istisnayi gorur (ayni HEAD = ayni hukum)", _a6),
        ("A7 istisna HICBIR agacta yoksa worktree'de de KIRMIZI (fail-closed)", _a7),
        ("A8 paylasilan istisnanin VARLIGI degil ICERIGI hukum verir", _a8),
    ]
    gecen = 0
    for ad, sinama in iddialar:
        try:
            gecti, sonuc = sinama()
        except Exception as hata:
            gecti = False
            sonuc = None
            ayrinti = "%s: %s" % (type(hata).__name__, hata)
        else:
            ayrinti = "rc=%d" % sonuc.returncode
        print("%s %s (%s)" % ("GECTI" if gecti else "KALDI", ad, ayrinti))
        if not gecti and sonuc is not None and sonuc.stdout.strip():
            print(sonuc.stdout.strip())
        gecen += int(gecti)
    toplam = len(iddialar)
    print("SONUC: %d/%d iddia GECTI" % (gecen, toplam))
    return 0 if gecen == toplam else 1


if __name__ == "__main__":
    sys.exit(main())
