#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""denetim-kapisi-kacak-test.py — TEST YUKU GERCEK VERI KOKUNU SILEMEZ (6 Eki olayi).

OLAY: `denetim-kapisi.py --kendini-test` onay bataryasi (`_kt_onay_batarya`) kopya kapiyi
`dict(os.environ)` ile kosuyordu. Miras `PRUVO_VERI_KOK` kopyanin veri kokunu GERCEK koke
cozdu; mutant M1 (`_mutant-onay-M1.py --tum-katalog --uygula`) gercek katalogdaki her
auto_sil kaydini `duzelt.py --sil` ile sildi (~1.192 kayit). Zaman asiminda ebeveyn oldu,
torun yetim kalip silmeye devam etti.

DUZELTME (iki katman, bu test IKISINI ayri ayri olcer):
  (1) PIN: test alt surecleri `veri_kok.test_ortami(depo, tmp)` ile kosar — veri koku
      gecici depoya ACIKCA sabitlenir, miras ezilir.
  (2) SIGORTA: `PRUVO_TEST_KUM` tanimliyken `duzelt.py` (acilis + her atomik yazim) ve
      `denetim-kapisi._uygula` (her silmeden once) hedef kumun DISINDAYSA ya da
      `PRUVO_TEST_EBEVEYN` olmusse fail-closed durur (rc!=0, yazim yok).

Her kosum GECICI dizinde, tools/ KOPYASI uzerinde yapilir; "sahte gercek kok" de gecici
dizindedir. Mutantlar yalniz kopyaya yazilir. Kabul: davranis (sha256 once/sonra), rc degil.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

_TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = "denetim-kapisi.py"
SAHTE_N = 40
_SUZ = ("PRUVO_VERI_KOK", "PRUVO_TEST_KUM", "PRUVO_TEST_EBEVEYN", "PRUVO_URUN_SIL_IZNI")


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _sayi(yol):
    with open(yol, encoding="utf-8") as f:
        return len(json.load(f))


def _taban_ortam():
    return {k: v for k, v in os.environ.items()
            if not k.startswith("GIT_") and k not in _SUZ}


def _git_depo(kok):
    o = _taban_ortam()
    for a in (["init", "-q"], ["add", "-A"],
              ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "taban"]):
        subprocess.run(["git", "-C", kok, *a], capture_output=True, env=o)


def _katalog_yaz(kok):
    os.makedirs(kok, exist_ok=True)
    urun = [{"id": "s%d" % i, "kategori": "Otomobil", "marka": ["Audi"],
             "baslik": "Audi A4 Uyumlu Braket s%d" % i,
             "aciklama": "Araca birebir oturan parca. Yaklasik dis olculer: 40 × 30 × 12 mm.",
             "fiyat": "500 TL", "gorseller": ["https://x/y%d.webp" % i]}
            for i in range(SAHTE_N)]
    yol = os.path.join(kok, "urunler.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(urun, f, ensure_ascii=False)
    return yol


def _kopya(hedef_kok, mutasyon):
    """tools/ -> hedef_kok/tools (mutasyon: {dosya: [(capa, yerine)]}). Capa tutmazsa None."""
    shutil.copytree(_TOOLS, os.path.join(hedef_kok, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_mutant*"))
    for dosya, degisim in (mutasyon or {}).items():
        yol = os.path.join(hedef_kok, "tools", dosya)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        for capa, yerine in degisim:
            if capa not in metin:
                return "capa yok: %s %r" % (dosya, capa[:50])
            metin = metin.replace(capa, yerine)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
    return None


# ── VAKALAR: her biri (gecti, detay) doner ─────────────────────────────────────────────
def vaka_k1(tmp):
    """Miras PRUVO_VERI_KOK=<sahte gercek kok> ile --kendini-test -> sahte kok DEGISMEZ."""
    sahte = os.path.join(tmp, "sahte-gercek")
    yol = _katalog_yaz(sahte)
    _git_depo(sahte)
    s0 = _sha(yol)
    o = _taban_ortam()
    o["PRUVO_VERI_KOK"] = sahte
    p = subprocess.run([sys.executable, os.path.join(tmp, "kopya", "tools", KAPI),
                        "--kendini-test"], env=o, capture_output=True, text=True, timeout=900)
    ayni = _sha(yol) == s0
    return ayni, "rc=%d sahte_sha_ayni=%s kayit %d->%d" % (
        p.returncode, ayni, SAHTE_N, _sayi(yol)), p.returncode


def vaka_k2(tmp):
    """PRUVO_VERI_KOK HIC YOKKEN, kopya agac bir git deposu (ana checkout benzetimi) ->
    kopyanin kendi urunler.json'u DEGISMEZ."""
    kopya = os.path.join(tmp, "kopya")
    yol = _katalog_yaz(kopya)
    _git_depo(kopya)
    s0 = _sha(yol)
    p = subprocess.run([sys.executable, os.path.join(kopya, "tools", KAPI), "--kendini-test"],
                       env=_taban_ortam(), cwd=kopya, capture_output=True, text=True,
                       timeout=900)
    ayni = _sha(yol) == s0
    return ayni, "rc=%d kok_sha_ayni=%s kayit %d->%d" % (
        p.returncode, ayni, SAHTE_N, _sayi(yol)), p.returncode


def _duzelt_sil(tmp, kum, ebeveyn=None):
    sahte = os.path.join(tmp, "sahte-gercek")
    yol = _katalog_yaz(sahte)
    s0 = _sha(yol)
    o = _taban_ortam()
    o.update({"PRUVO_VERI_KOK": sahte, "PRUVO_TEST_KUM": kum, "PRUVO_URUN_SIL_IZNI": "OKAN"})
    if ebeveyn is not None:
        o["PRUVO_TEST_EBEVEYN"] = str(ebeveyn)
    p = subprocess.run([sys.executable, os.path.join(tmp, "kopya", "tools", "duzelt.py"),
                        "s0", "--sil", "kacak-test"], env=o, capture_output=True, text=True,
                       timeout=120)
    return p.returncode, _sha(yol) == s0, (p.stdout or "") + (p.stderr or "")


def vaka_s1(tmp):
    """SIGORTA: PRUVO_TEST_KUM=<kum>, veri koku kumun DISINDA -> rc!=0, yazim YOK."""
    kum = os.path.join(tmp, "kum")
    os.makedirs(kum)
    rc, ayni, out = _duzelt_sil(tmp, kum)
    return rc != 0 and ayni, "rc=%d sahte_sha_ayni=%s sigorta_metni=%s" % (
        rc, ayni, "SIGORTASI" in out), rc


def vaka_s2(tmp):
    """YETIM TORUN: hedef kumun ICINDE ama PRUVO_TEST_EBEVEYN olmus -> rc!=0, yazim YOK."""
    p = subprocess.Popen(["true"])
    p.wait()
    rc, ayni, out = _duzelt_sil(tmp, tmp, ebeveyn=p.pid)
    return rc != 0 and ayni, "rc=%d sahte_sha_ayni=%s olu_pid=%d" % (rc, ayni, p.pid), rc


def vaka_s3(tmp):
    """POZITIF: hedef kumun ICINDE, ebeveyn CANLI -> silme YAPILIR (sigorta mesru kum
    yazimini KIRMAZ; olu-sigorta nobeti)."""
    rc, ayni, out = _duzelt_sil(tmp, tmp, ebeveyn=os.getpid())
    return rc == 0 and not ayni, "rc=%d sahte_sha_ayni=%s" % (rc, ayni), rc


VAKALAR = [("K1 miras PRUVO_VERI_KOK=<sahte kok> + --kendini-test -> sahte kok DEGISMEZ",
            vaka_k1),
           ("K2 PRUVO_VERI_KOK YOK, kopya=git deposu + --kendini-test -> kok DEGISMEZ",
            vaka_k2),
           ("S1 sigorta: hedef kum DISINDA -> duzelt.py rc!=0, yazim YOK", vaka_s1),
           ("S2 sigorta: ebeveyn OLU (yetim torun) -> duzelt.py rc!=0, yazim YOK", vaka_s2),
           ("S3 pozitif: kum ICINDE + ebeveyn canli -> silme YAPILIR", vaka_s3)]

_SIGORTA_CAPA = ("    ortam = os.environ if _ortam is None else _ortam\n"
                 "    kum = ortam.get(TEST_KUM_ENV)\n")
# Mutant: (ad, aciklama, mutasyon, KIRMIZIYA donmesi BEKLENEN vaka onekleri, YESIL kalmasi
# beklenen vaka onekleri). Kabul: hangi vakanin dondugu — cikis kodu degil.
MUTANTLAR = [
    ("MUT-KACAK", "test_ortami KALDIRILDI (dict(os.environ) = 6 Eki kodu: pin+sigorta yok)",
     {KAPI: [("_vk.test_ortami(depo, tmp)", "dict(os.environ)")]}, ["K1"], []),
    ("MUT-PIN", "yalniz PIN kaldirildi (miras kok geri, sigorta DURUYOR) -> sigorta TEK BASINA",
     {KAPI: [("_vk.test_ortami(depo, tmp)",
              "dict(_vk.test_ortami(depo, tmp), PRUVO_VERI_KOK=os.environ.get("
              "'PRUVO_VERI_KOK', depo))")]}, [], ["K1"]),
    ("MUT-SIGORTA", "test_kumu_denetle NO-OP", {"veri_kok.py": [
        (_SIGORTA_CAPA, "    return\n" + _SIGORTA_CAPA)]}, ["S1", "S2"], ["S3"]),
    ("MUT-EBEVEYN", "olu ebeveyn kontrolu NO-OP", {"veri_kok.py": [
        ("        if not _pid_canli(pid):", "        if False:")]}, ["S2"], ["S1", "S3"]),
]


def _kos_vaka(fn, mutasyon=None):
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="denetim-kacak-test-"))
    try:
        hata = _kopya(os.path.join(tmp, "kopya"), mutasyon)
        if hata:
            return None, hata
        r = fn(tmp)
        return r[0], r[1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    kalan = 0
    toplam = 0
    print("DENETIM KAPISI — TEST YUKU KACAK TESTI")
    for ad, fn in VAKALAR:
        ok, detay = _kos_vaka(fn)
        toplam += 1
        kalan += 0 if ok else 1
        print("  %s %-72s %s" % ("✅" if ok else "❌", ad, detay))
    for mad, aciklama, mutasyon, kirmizi, yesil in MUTANTLAR:
        for ad, fn in VAKALAR:
            onek = ad.split()[0]
            if onek not in kirmizi and onek not in yesil:
                continue
            ok, detay = _kos_vaka(fn, mutasyon)
            beklenen = onek in yesil
            dogru = ok is not None and ok == beklenen
            toplam += 1
            kalan += 0 if dogru else 1
            print("  %s %s [%s] %s -> %s (beklenen %s) %s" % (
                "✅" if dogru else "❌", mad, aciklama, onek,
                "OLCULEMEDI" if ok is None else ("YESIL" if ok else "KIRMIZI"),
                "YESIL" if beklenen else "KIRMIZI", detay))
    artik = sorted(x for x in os.listdir(_TOOLS) if x.startswith("_mutant"))
    toplam += 1
    if artik:
        kalan += 1
    print("  %s gercek tools/ dizininde mutant artigi YOK %s" % ("❌" if artik else "✅",
                                                                artik or ""))
    print("-" * 70)
    if kalan:
        print("SONUC: KIRMIZI ❌ — %d/%d iddia GECMEDI" % (kalan, toplam))
        return 1
    print("SONUC: YESIL ✅ — %d/%d iddia gecti" % (toplam, toplam))
    return 0


if __name__ == "__main__":
    sys.exit(main())
