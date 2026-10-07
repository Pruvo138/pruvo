#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""izin-manifest-tuket-test.py — post-commit izin manifesti TUKETIM kancasinin kabul testi.

HERMETIK: her vaka tempfile altinda `git init` edilen sahte depoda GERCEK `git commit` ile
kosar; izlenen tools/kancalar/post-commit + tools/izin-manifest-tuket.py depoya kopyalanir,
core.hooksPath o depoya baglanir. HOME / GIT_CONFIG_GLOBAL / GIT_CONFIG_SYSTEM gecici
dizine yonlendirilir; gercek ev yoluna hicbir sey yazilmaz/silinmez.

  V1 A'nin izni commit'lenmeden B commit atar        -> A'nin girdisi KALIR
  V2 A commit'ler                                     -> girdi silinir, dosya YOK olur
  V3 karisik (biri tuketildi biri degil + alan silme) -> yalniz tuketilen gider
  V4 bozuk JSON manifest                              -> dosya bayt-birebir AYNI
  V5 sil + rename tuketimi                            -> iki dosya da YOK olur
  V6 sil id-bagli: bekleyen silme YASAR, bayat (WT'de id duruyor) girdi DUSER

MUTANT (izole kopya): eski kosulsuz `rm -f` post-commit govdesi -> V1 KIRMIZI yanmali.

Kullanim:  python3 tools/izin-manifest-tuket-test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KANCA = os.path.join(TOOLS, "kancalar", "post-commit")
ARAC = os.path.join(TOOLS, "izin-manifest-tuket.py")

DUZELT = ".urunler-duzelt-izin.json"
SIL = ".urunler-sil-izin.json"
RENAME = ".urunler-id-rename-izin.json"

ESKI_KANCA = """#!/bin/sh
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
rm -f "$root/.urunler-duzelt-izin.json" 2>/dev/null || true
rm -f "$root/.urunler-sil-izin.json" 2>/dev/null || true
rm -f "$root/.urunler-id-rename-izin.json" 2>/dev/null || true
exit 0
"""

TABAN = [
    {"id": "a1", "ad": "A1", "fiyat": "10", "eski": "x"},
    {"id": "a2", "ad": "A2", "fiyat": "20"},
    {"id": "d1", "ad": "D1", "fiyat": "30"},
    {"id": "d2", "ad": "D2", "fiyat": "40"},
    {"id": "r1", "ad": "R1", "fiyat": "50"},
]


class Ortam(object):
    def __init__(self, kok, kanca_govdesi):
        self.kok = kok
        self.depo = os.path.join(kok, "depo")
        home = os.path.join(kok, "home")
        os.makedirs(home)
        self.env = dict(os.environ)
        for k in list(self.env):
            if k.startswith("GIT_"):
                del self.env[k]
        self.env.update({"HOME": home, "GIT_CONFIG_GLOBAL": os.devnull,
                         "GIT_CONFIG_SYSTEM": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        os.makedirs(os.path.join(self.depo, "tools", "kancalar"))
        shutil.copy2(ARAC, os.path.join(self.depo, "tools", "izin-manifest-tuket.py"))
        pc = os.path.join(self.depo, "tools", "kancalar", "post-commit")
        with open(pc, "w") as f:
            f.write(kanca_govdesi)
        os.chmod(pc, 0o755)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@example.invalid")
        self.urunler(TABAN)
        self.yaz("b.txt", "0\n")
        self.git("add", "-A")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "ilk")
        self.git("config", "core.hooksPath", "tools/kancalar")

    def git(self, *a):
        p = subprocess.run(["git", "-C", self.depo] + list(a), env=self.env,
                           capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise RuntimeError("git %s rc=%d: %s" % (" ".join(a), p.returncode, p.stderr))
        return p

    def yol(self, ad):
        return os.path.join(self.depo, ad)

    def yaz(self, ad, metin):
        with open(self.yol(ad), "w", encoding="utf-8") as f:
            f.write(metin)

    def urunler(self, liste):
        self.yaz("urunler.json", json.dumps(liste, ensure_ascii=False, indent=2))

    def manifest(self, ad, obj):
        self.yaz(ad, json.dumps(obj, ensure_ascii=False, indent=2))

    def oku(self, ad):
        if not os.path.exists(self.yol(ad)):
            return None
        with open(self.yol(ad), encoding="utf-8") as f:
            return json.load(f)

    def commit(self, *dosyalar):
        self.git("add", *dosyalar)
        return self.git("commit", "-q", "-m", "c")

    def b_commit(self):
        with open(self.yol("b.txt"), "a") as f:
            f.write("b\n")
        return self.commit("b.txt")


def _degistir(liste, uid, **alanlar):
    out = []
    for p in liste:
        p = dict(p)
        if p["id"] == uid:
            for k, v in alanlar.items():
                if v is None:
                    p.pop(k, None)
                else:
                    p[k] = v
        out.append(p)
    return out


def v1(o):
    """A'nin izni commit'lenmeden B commit atar -> A'nin girdisi KALIR."""
    o.urunler(_degistir(TABAN, "a1", fiyat="11"))
    o.manifest(DUZELT, {"a1": {"fiyat": "11"}})
    o.b_commit()
    m = o.oku(DUZELT)
    return m == {"a1": {"fiyat": "11"}}, "manifest=%r" % (m,)


def v2(o):
    """A commit'ler -> girdi silinir, dosya YOK olur."""
    o.urunler(_degistir(TABAN, "a1", fiyat="11"))
    o.manifest(DUZELT, {"a1": {"fiyat": "11"}})
    o.b_commit()
    once = o.oku(DUZELT) is not None
    o.commit("urunler.json")
    yok = not os.path.exists(o.yol(DUZELT))
    return once and yok, "B sonrasi var=%s, A sonrasi yok=%s" % (once, yok)


def v3(o):
    """Karisik: a1 (fiyat + alan silme) commit'lendi, a2 commit'lenmedi -> yalniz a2 kalir."""
    commitlenen = _degistir(TABAN, "a1", fiyat="12", eski=None)
    o.urunler(commitlenen)
    o.git("add", "urunler.json")
    o.urunler(_degistir(commitlenen, "a2", fiyat="21"))  # WT'de, stage DISI
    o.manifest(DUZELT, {"a1": {"fiyat": "12", "eski": {"__alan_sil__": True}},
                        "a2": {"fiyat": "21"}})
    o.git("commit", "-q", "-m", "c")
    m = o.oku(DUZELT)
    return m == {"a2": {"fiyat": "21"}}, "manifest=%r" % (m,)


def v4(o):
    """Bozuk JSON manifest -> dosya bayt-birebir AYNI (uc manifest icin)."""
    ham = {DUZELT: b'{"a1": {"fiyat": "11"', SIL: b"[\"d1\",", RENAME: b"bozuk{"}
    for ad, b in ham.items():
        with open(o.yol(ad), "wb") as f:
            f.write(b)
    o.urunler(_degistir(TABAN, "a1", fiyat="11"))
    o.commit("urunler.json")
    sonra = {}
    for ad in ham:
        with open(o.yol(ad), "rb") as f:
            sonra[ad] = f.read()
    return sonra == ham, "farkli=%r" % [a for a in ham if sonra.get(a) != ham[a]]


def v5(o):
    """sil + rename tuketimi -> iki dosya da YOK olur."""
    liste = [p for p in TABAN if p["id"] != "d1"]
    liste = [dict(p, id="r2") if p["id"] == "r1" else p for p in liste]
    o.urunler(liste)
    o.manifest(SIL, ["d1"])
    o.manifest(RENAME, {"r1": "r2"})
    o.b_commit()
    once = o.oku(SIL) == ["d1"] and o.oku(RENAME) == {"r1": "r2"}
    o.commit("urunler.json")
    yok = not os.path.exists(o.yol(SIL)) and not os.path.exists(o.yol(RENAME))
    return once and yok, "B sonrasi yasadi=%s, A sonrasi ikisi de yok=%s" % (once, yok)


def v6(o):
    """sil id-bagli: d2 WT'de silinmis (bekleyen) YASAR; d1 WT'de duruyor (bayat) DUSER."""
    o.urunler([p for p in TABAN if p["id"] != "d2"])
    o.manifest(SIL, ["d1", "d2"])
    o.b_commit()
    m = o.oku(SIL)
    return m == ["d2"], "sil=%r" % (m,)


VAKALAR = (("V1", v1), ("V2", v2), ("V3", v3), ("V4", v4), ("V5", v5), ("V6", v6))


def _gecici_mi(yol):
    gercek = os.path.realpath(yol)
    tmp = os.path.realpath(tempfile.gettempdir())
    return gercek.startswith(tmp + os.sep)


def kos(kanca_govdesi, sessiz=False):
    sonuc = {}
    for ad, fn in VAKALAR:
        kok = tempfile.mkdtemp(prefix="izin-tuket-%s-" % ad)
        try:
            try:
                ok, ayrinti = fn(Ortam(kok, kanca_govdesi))
            except Exception as e:
                ok, ayrinti = False, "ISTISNA %s: %s" % (type(e).__name__, e)
            sonuc[ad] = ok
            if not sessiz:
                print("%s %s — %s" % (ad, "GECTI" if ok else "KIRMIZI", ayrinti))
        finally:
            if _gecici_mi(kok):
                shutil.rmtree(kok, ignore_errors=True)
    return sonuc


def main():
    with open(KANCA, encoding="utf-8") as f:
        govde = f.read()
    print("== izlenen post-commit")
    gercek = kos(govde)
    print("== MUTANT: eski kosulsuz rm -f post-commit (izole kopya)")
    mutant = kos(ESKI_KANCA, sessiz=True)
    mutant_ok = mutant.get("V1") is False
    print("MUTANT %s — V1=%s (beklenen KIRMIZI)" % (
        "KIRMIZI" if mutant_ok else "YASADI", "GECTI" if mutant["V1"] else "KIRMIZI"))
    hepsi = all(gercek.values()) and mutant_ok
    print("SONUC: %s (%d/%d vaka, mutant=%s)" % (
        "GECTI" if hepsi else "KIRMIZI", sum(gercek.values()), len(gercek),
        "oldu" if mutant_ok else "YASADI"))
    return 0 if hepsi else 1


if __name__ == "__main__":
    sys.exit(main())
