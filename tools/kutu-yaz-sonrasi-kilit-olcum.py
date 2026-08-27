#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K324 `--yaz-sonrasi` KOLU — KILIT GUVENLIGI OLCUMU (27 Agu 2026).

🔴 BU ARAC KABLO TAKMAZ. `kutu-arsivle.py --yaz-sonrasi` kolu main'de DURUYOR
ama bir PostToolUse kancasina BAGLI DEGIL. Kabloyu MIMAR takacak; mimarin
sormadan once ucuncu bir seye bakmasi gerekiyor: bu kol bir YAZIM kancasinda,
yani en kotu anda (baska bir yazici kutuyu tam o sirada dondururken) kosacak.
Uc soru SAYIYLA yanitlanir, hicbiri "bakildi iyi" degil:

  (a) KILIT   — kol `flock` ile mi kosuyor? Kilit BASKASINDAYKEN cagrilirsa
                ne yapiyor: yaziyor mu, cekiliyor mu?
  (b) NO-OP   — kutu tavanin ALTINDAYKEN HICBIR SEY yazmiyor mu (arsiv
                dosyasi bile olusmuyor mu)?
  (c) YARIS   — IKI ESZAMANLI cagrida kutu BAYT-BIREBIR bozulmadan kaliyor
                mu (tek kosumun urettigi kutuyla ayni mi)?

Olcum HERMETIKTIR: gercek kutuya/arsive/kilide DOKUNMAZ, her vaka kendi
gecici dizininde kurulur ve sonunda silinir (Okan disk kurali).

Kullanim:
    python3 tools/kutu-yaz-sonrasi-kilit-olcum.py
    python3 tools/kutu-yaz-sonrasi-kilit-olcum.py --arac /yol/kutu-arsivle.py

🔴 `--arac` NEDEN VAR: `--yaz-sonrasi` kolu K324 ile MAIN'e girdi; bu dal
main'den ONCE dallandigi icin dalin KENDI `tools/kutu-arsivle.py` kopyasinda
o kol YOKTUR. Hangi dosyanin olculdugu ciktinin basinda ADIYLA basilir —
"yesil" hangi kopyayi tarif ediyor, okuyan gormeden gecemez
([[emir-canliligi-kurulu-kopyadan-olculur]]).

Cikti (tek makine-okunur ozet):
    KILIT_OLCUM VAKA=<gecen>/<toplam> DUSEN=<n> ARAC=<yol>
Cikis: 0 = hepsi yesil · 1 = en az bir kirmizi · 2 = arac hatasi.
"""

import argparse
import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading

PY = sys.executable or "python3"

# Fikstur olcusu: KUCUK ve HIZLI tutulur; tavan/koru bayrakla verilir ki
# gercek tavani (300) beklemek gerekmesin. Kol TAVANI DEGISTIRMEZ, bize
# gecirdigimiz `--tavan`i AYNEN kullanir (K324 sarti 1) — olcum tam da
# bunu kullanir.
TAVAN = 20
KORU = 1

_SAYAC = {"vaka": 0, "gecen": 0}
_DUSENLER = []


def olc(ad, beklenen, gozlenen):
    _SAYAC["vaka"] += 1
    tamam = (beklenen == gozlenen)
    if tamam:
        _SAYAC["gecen"] += 1
    else:
        _DUSENLER.append(ad)
        sys.stderr.write("[DUSTU] %s\n  beklenen=%r\n  gozlenen=%r\n"
                         % (ad, beklenen, gozlenen))
    print("VAKA %-44s %s" % (ad, "GECTI" if tamam else "DUSTU"))
    return tamam


def _blok(i):
    return ("## 2026-01-%02d — FIKSTUR-%02d — olcum blogu\n"
            "\n"
            "Govde satiri bir.\n"
            "Govde satiri iki.\n"
            "— FIKSTUR-%02d\n"
            "\n"
            "---\n"
            "\n") % ((i % 28) + 1, i, i)


def kutu_kur(dizin, blok_sayisi):
    """(kutu_yolu, arsiv_yolu, kilit_yolu) — hermetik fikstur."""
    kutu = os.path.join(dizin, "kutu.md")
    with open(kutu, "w", encoding="utf-8") as f:
        f.write("".join(_blok(i) for i in range(blok_sayisi)))
    return (kutu,
            os.path.join(dizin, "kutu-arsiv.md"),
            os.path.join(dizin, ".kutu.md.lock"))


def sha(yol):
    if not os.path.exists(yol):
        return "-yok-"
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def satir_sayisi(yol):
    if not os.path.exists(yol):
        return -1
    with open(yol, "rb") as f:
        return len(f.read().splitlines())


def cagir(arac, kutu, arsiv, kilit, yaz_sonrasi_hedefi):
    return subprocess.run(
        [PY, arac, "--kutu", kutu, "--arsiv", arsiv, "--kilit", kilit,
         "--tavan", str(TAVAN), "--koru", str(KORU),
         "--yaz-sonrasi", yaz_sonrasi_hedefi],
        capture_output=True, text=True, timeout=180)


def _ic_rc(cikti):
    """`YAZ_SONRASI_IC_RC=<n> ...` satirindan ic rc'yi ayiklar (yoksa None).

    🔴 DIS rc OLCUM DEGILDIR: kol FAIL-OPEN'dir ve HER HALDE 0 doner
    (yazim kancasini bloklamamak icin). Gercek hukum yalnizca bu jetondadir
    ([[boru-rc-isci-olcumunu-yalanlar]] ile ayni aile: disaridan gorunen rc
    icerideki kararı YALANLAR)."""
    for satir in (cikti or "").splitlines():
        if satir.startswith("YAZ_SONRASI_IC_RC="):
            parca = satir.split()[0].split("=", 1)[1]
            try:
                return int(parca)
            except ValueError:
                return parca
    return None


def _jeton(cikti, onek):
    for satir in (cikti or "").splitlines():
        if satir.startswith(onek):
            return satir.strip()
    return "-"


# =========================================================================
# (a) KILIT — kilit BASKASINDAYKEN kol YAZMAZ
# =========================================================================
def vaka_kilit(arac):
    gecici = tempfile.mkdtemp(prefix="k324-kilit-")
    try:
        kutu, arsiv, kilit = kutu_kur(gecici, 12)   # 12 blok -> tavan(20) USTU
        once_sha = sha(kutu)
        # Kilidi BIZ tutuyoruz: kol ayni kilidi LOCK_EX|LOCK_NB ile isteyecek.
        tutucu = open(kilit, "a+")
        fcntl.flock(tutucu.fileno(), fcntl.LOCK_EX)
        try:
            r = cagir(arac, kutu, arsiv, kilit, kutu)
        finally:
            fcntl.flock(tutucu.fileno(), fcntl.LOCK_UN)
            tutucu.close()
        cikti = (r.stdout or "") + (r.stderr or "")
        print("   " + _jeton(cikti, "YAZ_SONRASI="))
        print("   " + _jeton(cikti, "YAZ_SONRASI_IC_RC="))
        print("   " + _jeton(cikti, "KILIT ALINAMADI"))
        # (1) ATESLEDI (yani tavan ustu oldugunu gordu),
        # (2) IC rc = RC_KILIT(3) -> fail-closed cekildi,
        # (3) kutu BAYT-BIREBIR ayni, (4) arsiv HIC olusmadi,
        # (5) DIS rc 0 -> yazim kancasi BLOKLANMADI (fail-open korunuyor).
        olc("a-KILIT kilit baskasindayken YAZMAZ",
            (True, 3, once_sha, False, 0),
            ("YAZ_SONRASI=ATESLEDI" in cikti, _ic_rc(cikti), sha(kutu),
             os.path.exists(arsiv), r.returncode))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# =========================================================================
# (b) NO-OP — tavan ALTINDA hicbir sey yazilmaz
# =========================================================================
def vaka_noop(arac):
    gecici = tempfile.mkdtemp(prefix="k324-noop-")
    try:
        kutu, arsiv, kilit = kutu_kur(gecici, 2)    # 2 blok -> tavan ALTI
        once_sha = sha(kutu)
        r = cagir(arac, kutu, arsiv, kilit, kutu)
        cikti = (r.stdout or "") + (r.stderr or "")
        print("   " + _jeton(cikti, "YAZ_SONRASI="))
        olc("b-NOOP tavan altinda HICBIR SEY yazmaz",
            (True, once_sha, False, False, 0),
            ("sebep=tavan-altinda" in cikti, sha(kutu),
             os.path.exists(arsiv), os.path.exists(kilit), r.returncode))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# b2: HEDEF SARTI — duzenlenen dosya KUTU DEGILSE kol hicbir seye dokunmaz.
def vaka_hedef_disi(arac):
    gecici = tempfile.mkdtemp(prefix="k324-hedef-")
    try:
        kutu, arsiv, kilit = kutu_kur(gecici, 12)   # tavan USTU (ama hedef baska)
        baska = os.path.join(gecici, "baska.md")
        with open(baska, "w", encoding="utf-8") as f:
            f.write("baska bir dosya\n")
        once_sha = sha(kutu)
        r = cagir(arac, kutu, arsiv, kilit, baska)
        cikti = (r.stdout or "") + (r.stderr or "")
        print("   " + _jeton(cikti, "YAZ_SONRASI="))
        olc("b2-HEDEF kutu disi yol -> DOKUNMAZ",
            (True, once_sha, False, 0),
            ("sebep=hedef-kutu-degil" in cikti, sha(kutu),
             os.path.exists(arsiv), r.returncode))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# =========================================================================
# (c) YARIS — iki eszamanli cagri kutuyu BOZMAZ
# =========================================================================
def vaka_yaris(arac):
    # TABAN: ayni baslangictan TEK kosum ne uretiyor?
    taban_dizin = tempfile.mkdtemp(prefix="k324-yaris-taban-")
    yaris_dizin = tempfile.mkdtemp(prefix="k324-yaris-")
    try:
        k1, a1, l1 = kutu_kur(taban_dizin, 12)
        r1 = cagir(arac, k1, a1, l1, k1)
        taban_sha, taban_satir = sha(k1), satir_sayisi(k1)
        print("   TABAN tek kosum: sha=%s satir=%d ic_rc=%s"
              % (taban_sha, taban_satir,
                 _ic_rc((r1.stdout or "") + (r1.stderr or ""))))

        k2, a2, l2 = kutu_kur(yaris_dizin, 12)
        sonuclar = [None, None]

        def kos(i):
            try:
                sonuclar[i] = cagir(arac, k2, a2, l2, k2)
            except Exception as hata:                      # noqa: BLE001
                sonuclar[i] = hata

        ipler = [threading.Thread(target=kos, args=(i,)) for i in (0, 1)]
        for ip in ipler:
            ip.start()
        for ip in ipler:
            ip.join()

        ic_rcler = []
        for s in sonuclar:
            if isinstance(s, Exception):
                ic_rcler.append("PATLADI:%s" % type(s).__name__)
            else:
                ic_rcler.append(_ic_rc((s.stdout or "") + (s.stderr or "")))
        dis_rcler = [None if isinstance(s, Exception) else s.returncode
                     for s in sonuclar]
        print("   YARIS iki kosum: ic_rc=%s dis_rc=%s sha=%s satir=%d"
              % (ic_rcler, dis_rcler, sha(k2), satir_sayisi(k2)))

        # 🔴 IDDIA: kutu, TEK kosumun urettigiyle BAYT-BIREBIR ayni olmali.
        # Iki yazicidan biri kilidi alamayip cekilir (RC_KILIT=3) ya da
        # kutuyu tavan ALTINDA bulup atlar; ikisi de kutuyu IKI KEZ
        # dondurmez. Bozulma (yarim/mukerrer govde) burada YAKALANIR.
        olc("c-YARIS iki eszamanli cagri kutuyu BOZMAZ",
            (taban_sha, taban_satir, [0, 0]),
            (sha(k2), satir_sayisi(k2), dis_rcler))
        # Ikinci eksen: iki cagridan EN COK BIRI gercekten dondurmus olmali.
        donduren = sum(1 for v in ic_rcler if v == 0)
        olc("c2-YARIS en cok BIR cagri dondurur", True, donduren <= 1)
    finally:
        shutil.rmtree(taban_dizin, ignore_errors=True)
        shutil.rmtree(yaris_dizin, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arac", default=None, metavar="YOL",
                    help="olculecek kutu-arsivle.py (varsayilan: bu betikle "
                         "AYNI dizindeki kopya)")
    a = ap.parse_args(argv)

    arac = a.arac or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "kutu-arsivle.py")
    arac = os.path.abspath(os.path.expanduser(arac))
    print("=== K324 --yaz-sonrasi KILIT GUVENLIGI OLCUMU ===")
    print("OLCULEN_ARAC=%s var=%d" % (arac, int(os.path.isfile(arac))))
    print("tavan=%d koru=%d (fikstur; kol TAVANI DEGISTIRMEZ)" % (TAVAN, KORU))
    if not os.path.isfile(arac):
        print("HATA: arac YOK")
        return 2

    # 🔴 ON-KOSUL: bu kopyada kol VAR MI? Yoksa uc vaka da "yesil" gorunur
    # (hicbiri atesleyemez) ve olcum SESSIZCE bosalir.
    with open(arac, encoding="utf-8") as f:
        kaynak = f.read()
    if "--yaz-sonrasi" not in kaynak:
        print("KIRMIZI: bu kopyada `--yaz-sonrasi` kolu YOK -> OLCUM YAPILAMAZ")
        print("KILIT_OLCUM VAKA=0/0 DUSEN=0 ARAC=%s KOL=YOK" % arac)
        return 2

    vaka_kilit(arac)
    vaka_noop(arac)
    vaka_hedef_disi(arac)
    vaka_yaris(arac)

    print("KILIT_OLCUM VAKA=%d/%d DUSEN=%d ARAC=%s"
          % (_SAYAC["gecen"], _SAYAC["vaka"], len(_DUSENLER), arac))
    if _DUSENLER:
        print("DUSEN_VAKALAR=%s" % ",".join(_DUSENLER))
    return 0 if not _DUSENLER else 1


if __name__ == "__main__":
    sys.exit(main())
