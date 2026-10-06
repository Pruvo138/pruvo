#!/usr/bin/env python3
"""yedekle.py OZET DEFTERI kabul testi (6 Eki 2026) — hedef ICERIGI okunmadan "ayni mi".

HERMETIK: gecici dizinde sahte kaynak + sahte Drive koku; defter de gecici dizinde.
GERCEK Drive'a, ROOT'a ve ~/.claude'a YAZMAZ (main() cagrilmaz; defter `yol=` ile verilir).

Vakalar:
  (a) ikinci kosumda degismeyen dosyalar icin hedef okuma (open) = 0
  (b) kaynak ayni boyutla degisti + mtime ileri -> kopyalandi
  (c) kaynak mtime degisti icerik ayni -> kopya YOK, defter mtime'i guncel
  (d) defter bozuk -> fail-closed tam karsilastirma, yedek dogru
  (e) bayt-dususu karantinasi defter acikken de tutar (hedef degismez)
Her kol icin izole kopyada MUTANT: kontrol kaldirilinca ilgili vaka KIRMIZI olmali.

Cikis: 0 = tum vakalar YESIL ve tum mutantlar KIRMIZI; aksi 1.
"""
import builtins
import importlib.util
import os
import shutil
import sys
import tempfile

ARACLAR = os.path.dirname(os.path.abspath(__file__))
KAYNAK_MODUL = os.path.join(ARACLAR, "yedekle.py")
if ARACLAR not in sys.path:
    sys.path.insert(0, ARACLAR)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class OkumaSayaci:
    """`kok` altindaki dosyalarin OKUMA amacli open() cagrilarini sayar."""

    def __init__(self, kok):
        self.kok = os.path.realpath(kok) + os.sep
        self.okuma = 0
        self.yazma = 0
        self._asil = builtins.open

    def __enter__(self):
        asil = self._asil

        def sarmal(dosya, mode="r", *a, **k):
            if isinstance(dosya, (str, bytes, os.PathLike)):
                yol = os.path.realpath(os.fsdecode(dosya))
                if yol.startswith(self.kok):
                    if any(c in mode for c in "wax+"):
                        self.yazma += 1
                    else:
                        self.okuma += 1
            return asil(dosya, mode, *a, **k)
        builtins.open = sarmal
        return self

    def __exit__(self, *a):
        builtins.open = self._asil


def yaz(yol, veri, mtime=None):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "wb") as f:
        f.write(veri)
    if mtime is not None:
        os.utime(yol, (mtime, mtime))


def oku(yol):
    with open(yol, "rb") as f:
        return f.read()


def kur(tmp):
    kaynak = os.path.join(tmp, "kaynak")
    backup = os.path.join(tmp, "drive", "backup-v2")
    defter = os.path.join(tmp, "yerel", ".yedek-ozet.json")
    os.makedirs(os.path.dirname(defter))
    os.makedirs(backup)
    taban = 1_700_000_000
    dosyalar = {
        "memory/a.md": b"alfa " * 200,
        "memory/b.md": b"beta " * 300,
        "skills/x/SKILL.md": b"skill " * 100,
        "memory/kayit.json": b'[' + b','.join(b'{"i":%d}' % i for i in range(50)) + b']',
    }
    for gor, veri in dosyalar.items():
        yaz(os.path.join(kaynak, gor), veri, taban)
    return kaynak, backup, defter, sorted(dosyalar)


def kosum(y, kaynak, backup, defter, gorler):
    y._ozet_ac(backup, yol=defter)
    try:
        for gor in gorler:
            varis = os.path.join(backup, gor)
            os.makedirs(os.path.dirname(varis), exist_ok=True)
            y._drive_kopyala_karantinali(os.path.join(kaynak, gor), varis)
    finally:
        y._ozet_kapat()


def surum_sayisi(backup):
    n = 0
    for _d, _a, fs in os.walk(backup):
        n += sum(1 for f in fs if y_surum(f))
    return n


def y_surum(ad):
    import re
    return re.search(r"\.\d{8}-\d{6}(?:-\d{2})?(\.[^.]*)?$", ad) is not None


# ---------------------------------------------------------------- vakalar
def vaka_a(y):
    """(a) ikinci kosum: hedef okuma 0. Kontrol: defter KAPALI ikinci kosum OKUR (sayac canli)."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak, backup, defter, gorler = kur(tmp)
        kosum(y, kaynak, backup, defter, gorler)               # ilk kosum: kopyalar + defter
        with OkumaSayaci(backup) as s:
            kosum(y, kaynak, backup, defter, gorler)
        # kontrol kolu: defter yokken AYNI ikinci kosum hedefi okur -> sayac olcuyor
        with OkumaSayaci(backup) as k:
            for gor in gorler:
                y._drive_kopyala(os.path.join(kaynak, gor), os.path.join(backup, gor))
        tamam = all(oku(os.path.join(kaynak, g)) == oku(os.path.join(backup, g)) for g in gorler)
        return (s.okuma == 0 and s.yazma == 0 and k.okuma > 0 and tamam,
                "hedef_okuma=%d hedef_yazma=%d kontrol_okuma=%d icerik_esit=%s"
                % (s.okuma, s.yazma, k.okuma, tamam))


def vaka_b(y):
    """(b) ayni boyut, farkli icerik, mtime ileri -> kopyalandi."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak, backup, defter, gorler = kur(tmp)
        kosum(y, kaynak, backup, defter, gorler)
        k = os.path.join(kaynak, "memory/a.md")
        eski = oku(k)
        yeni = b"ALFA " * 200
        assert len(yeni) == len(eski)
        yaz(k, yeni, os.stat(k).st_mtime + 10)
        kosum(y, kaynak, backup, defter, gorler)
        hedef = oku(os.path.join(backup, "memory/a.md"))
        return hedef == yeni, "hedef_yeni_icerik=%s surum=%d" % (hedef == yeni, surum_sayisi(backup))


def vaka_c(y):
    """(c) yalniz mtime degisti -> kopya YOK (hedefe yazma 0, surum 0), defter mtime guncel."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak, backup, defter, gorler = kur(tmp)
        kosum(y, kaynak, backup, defter, gorler)
        k = os.path.join(kaynak, "memory/b.md")
        os.utime(k, (os.stat(k).st_mtime + 50,) * 2)
        with OkumaSayaci(backup) as s:
            kosum(y, kaynak, backup, defter, gorler)
        import json
        with open(defter, encoding="utf-8") as f:
            kayit = json.load(f)["kayitlar"]["memory/b.md"]
        guncel = kayit[1] == os.stat(k).st_mtime_ns
        sv = surum_sayisi(backup)
        return (s.yazma == 0 and s.okuma == 0 and sv == 0 and guncel,
                "hedef_yazma=%d hedef_okuma=%d surum=%d defter_mtime_guncel=%s"
                % (s.yazma, s.okuma, sv, guncel))


def vaka_d(y):
    """(d) defter bozuk + hedef ayni boyut/mtime ama BAYAT icerik -> tam karsilastirma duzeltir."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak, backup, defter, gorler = kur(tmp)
        kosum(y, kaynak, backup, defter, gorler)
        with open(defter, "w", encoding="utf-8") as f:
            f.write("{bozuk")
        k = os.path.join(kaynak, "memory/a.md")
        h = os.path.join(backup, "memory/a.md")
        mt = os.stat(k).st_mtime
        yaz(h, b"BAYAT" * 200, mt)                          # ayni boyut + ayni mtime
        durum = y._ozet_ac(backup, yol=defter)
        y._ozet_kapat()
        kosum(y, kaynak, backup, defter, gorler)
        dogru = oku(h) == oku(k)
        return durum == "bozuk" and dogru, "defter_durum=%s yedek_dogru=%s" % (durum, dogru)


def vaka_e(y):
    """(e) defter acikken bayt-dususu karantinasi tutar; hedef DEGISMEZ."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak, backup, defter, gorler = kur(tmp)
        kosum(y, kaynak, backup, defter, gorler)
        k = os.path.join(kaynak, "memory/b.md")
        h = os.path.join(backup, "memory/b.md")
        once = oku(h)
        yaz(k, b"x" * 10, os.stat(k).st_mtime + 10)
        del y._KORUMA_KARANTINA[:]
        del y._KORUMA_AYRINTI[:]
        kosum(y, kaynak, backup, defter, gorler)
        karantina = [a["sinif"] for a in y._KORUMA_AYRINTI]
        degismedi = oku(h) == once
        del y._KORUMA_KARANTINA[:]
        del y._KORUMA_AYRINTI[:]
        return ("bayt-dususu" in karantina and degismedi,
                "karantina=%s hedef_degismedi=%s" % (karantina, degismedi))


VAKALAR = {"a": vaka_a, "b": vaka_b, "c": vaka_c, "d": vaka_d, "e": vaka_e}

# (vaka, ad, aranan, yerine) — izole kopyada TEK yerde uygulanir.
MUTANTLAR = [
    ("a", "defter-devre-disi",
     'if _OZET["kayitlar"] is not None:\n        return _drive_kopyala_ozetli(kaynak, varis)',
     'if False:\n        return _drive_kopyala_ozetli(kaynak, varis)'),
    ("b", "sha-karsilastirmasi-yok",
     "if hedef_tutar and ks.st_size == kayit[0] and sha == kayit[2]:",
     "if hedef_tutar and ks.st_size == kayit[0]:"),
    ("c", "mtime-degisince-kopyala",
     "_ozet_yaz_kayit(anahtar, ks, sha, kaynak_kayit, kaynak)   # yalniz mtime degisti\n        return True",
     "pass   # yalniz mtime degisti"),
    ("d", "dataless-sarti-yok",
     "hs.st_blocks == 0 and hs.st_size > 0",
     "hs.st_size > 0"),
    ("e", "ozetli-koruma-yok",
     "_yedek_korumasi(kaynak, varis, yedek_kayit=kayit[3])",
     "pass"),
]


def main():
    hatali = 0
    y = modul_yukle(KAYNAK_MODUL, "yedekle_ozet_test")
    print("== VAKALAR ==")
    for ad, fn in VAKALAR.items():
        try:
            ok, ayrinti = fn(y)
        except Exception as e:
            ok, ayrinti = False, "ISTISNA %s: %s" % (type(e).__name__, e)
        hatali += 0 if ok else 1
        print("  (%s) %s  %s" % (ad, "YESIL" if ok else "KIRMIZI", ayrinti))

    print("== MUTANTLAR (izole kopya; KIRMIZI beklenir) ==")
    kaynak_metin = open(KAYNAK_MODUL, encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as tmp:
        for i, (vaka, ad, aranan, yerine) in enumerate(MUTANTLAR):
            n = kaynak_metin.count(aranan)
            if n != 1:
                hatali += 1
                print("  [%s] %-24s UYGULANAMADI (capa %d kez)" % (vaka, ad, n))
                continue
            yol = os.path.join(tmp, "yedekle_mutant_%d.py" % i)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kaynak_metin.replace(aranan, yerine))
            try:
                m = modul_yukle(yol, "yedekle_mutant_%d" % i)
                ok, ayrinti = VAKALAR[vaka](m)
            except Exception as e:
                ok, ayrinti = False, "ISTISNA %s" % type(e).__name__
            olur = not ok
            hatali += 0 if olur else 1
            print("  [%s] %-24s %s  %s" % (vaka, ad, "OLDU (KIRMIZI)" if olur
                                           else "HAYATTA KALDI", ayrinti))
    print("SONUC: %s" % ("YESIL ✅" if hatali == 0 else "KIRMIZI ❌ (%d)" % hatali))
    return 0 if hatali == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
