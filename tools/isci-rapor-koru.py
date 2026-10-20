#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISCI RAPOR KORUMASI — K337 kapanis cagrisi ortak isci raporuna YALNIZ EKLER (20 Eki 2026).

Hedef `~/.claude/cron/isci.sh` (repoda KOPYASI YOKTUR); arac repoda YASAR,
`yama` alt komutu kurulu isci.sh'e kancalar ve kendini isci.sh'in yanina
(`$CRON_KOKU/isci-rapor-koru.py`) KOPYALAR; olcum KURULU KOPYADAN yapilir.

OLCULEN VAKA (KraL halef-46 02:3x, BaBa 02:4x (3b) + 08:1x (3)): 19 Eki 23:29
EyLuL iscisinin K337 kapanis LLM cagrisi ("ortak rapora DURMA
NOKTASI yaz") ortak `~/.claude/cron` isci raporunu (ad: AD sabiti) EZDI: 355.997 B /
97 baslik -> 18.930 B / 8 baslik. Cagri yazacagi dizini secmez; devraldigi
dizindeki (PWD / EV_KOKU / CRON_KOKU) dosyaya yazar. Prompt cumlesi ricadir;
deterministik kol bu aractir: yazim sonrasi dosya, yazim ONCESI icerigin
BAYT-ONEKI degilse (kucultme, ortadan degistirme, silme) RED.

Alt komutlar:
  once  --kok D [--kok D ...] [--kimlik K]
        her kokte (realpath ile tekillesir) rapor dosyasi (AD) varsa
        `<AD>[.koru-K].bak` yedegi alinir. Ayni adli bayat yedek
        varsa EZILMEZ: `.eski-<ns>` ekiyle kenara alinir (kayip 0).
  sonra --kok D [--kok D ...] [--kimlik K]
        yedegi olan her kokte: simdiki icerik yedekle BASLIYORSA GECTI;
        degilse RED -> dosya = yedek + tarihli ayrac + yazilan icerik (SONA,
        kayip 0), atomik yazilir, dogrulanir, ancak o zaman yedek silinir.
        rc 0 = hepsi GECTI · 1 = en az bir RED (geri alindi) · 3 = OLCULEMEDI
        (geri yazilamadi; yedek DURUR).
  yama    <isci.sh>  kancayi ekler (idempotent) + araci isci.sh yanina kopyalar;
                     capa eksik/cogulsa rc=3 OLCULEMEDI, HICBIR SEY YAZMAZ.
  kontrol <isci.sh>  KORU_KANCASI=<n>/2 KOPYA=ESIT|FARKLI|YOK; rc 0 yalniz 2/2+ESIT.
Kabul: tools/isci-rapor-koru-test.py (nobet.yml serit-b).
"""
import hashlib
import os
import sys
import tempfile
import time

AD = "RAPOR-MIMARA.md"
KOPYA_ADI = "isci-rapor-koru.py"

CAGRI_CAPASI = '"$KAPANIS_PROMPTU" "${KAPANIS_BAYRAKLAR[@]}"'
RC_CAPASI = "KAPANIS_RC=$?"
ONCE_BAS = "# === ISCI-RAPOR-KORU BAS"
ONCE_SON = "# === ISCI-RAPOR-KORU SON ==="
SONRA_BAS = "# === ISCI-RAPOR-KORU-SONRA BAS"
SONRA_SON = "# === ISCI-RAPOR-KORU-SONRA SON ==="


def _ic(girinti, satirlar):
    return [girinti + s + "\n" for s in satirlar]


def once_blogu(girinti):
    return _ic(girinti, [
        ONCE_BAS + " (20 Eki 2026, BaBa 08:1x (3)) ===",
        "# Kapanis cagrisi ortak rapora YALNIZ EKLER: once .bak yedegi; sonra",
        "# yedek bayt-oneki degilse RED + .bak'tan geri + yazilan icerik SONA.",
        'RAPOR_KORU_ARG=(--kok "$PWD" --kok "$EV_KOKU" --kok "$CRON_KOKU" --kimlik "$$")',
        'python3 "$CRON_KOKU/' + KOPYA_ADI + '" once "${RAPOR_KORU_ARG[@]}" >> "$LOG" 2>&1',
        ONCE_SON,
    ])


def sonra_blogu(girinti):
    return _ic(girinti, [
        SONRA_BAS + " ===",
        'python3 "$CRON_KOKU/' + KOPYA_ADI + '" sonra "${RAPOR_KORU_ARG[@]}" >> "$LOG" 2>&1',
        'echo "RAPOR_KORU rc=$?" >> "$LOG"',
        "unset RAPOR_KORU_ARG",
        SONRA_SON,
    ])


# ---------------------------------------------------------------- koruma

def _kokler(ham):
    gorulen, sonuc = set(), []
    for k in ham:
        if not k:
            continue
        r = os.path.realpath(k)
        if r not in gorulen and os.path.isdir(r):
            gorulen.add(r)
            sonuc.append(r)
    return sonuc


def _bak(kok, kimlik):
    ek = ".koru-%s" % kimlik if kimlik else ""
    return os.path.join(kok, AD + ek + ".bak")


def _atomik_yaz(yol, veri, kip):
    fd, gecici = tempfile.mkstemp(dir=os.path.dirname(yol), prefix=".rapor-koru.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(veri)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(gecici, kip)
        os.replace(gecici, yol)
    except BaseException:
        if os.path.exists(gecici):
            os.unlink(gecici)
        raise


def _oku(yol):
    with open(yol, "rb") as f:
        return f.read()


def once(kokler, kimlik):
    for kok in kokler:
        dosya, bak = os.path.join(kok, AD), _bak(kok, kimlik)
        if not os.path.isfile(dosya):
            print("RAPOR_KORU_ONCE kok=%s hal=YOK" % kok)
            continue
        if os.path.exists(bak):
            eski = "%s.eski-%d" % (bak, time.time_ns())
            os.replace(bak, eski)
            print("RAPOR_KORU_ONCE kok=%s uyari=BAYAT_YEDEK_KENARA hedef=%s" % (kok, eski))
        veri = _oku(dosya)
        _atomik_yaz(bak, veri, os.stat(dosya).st_mode & 0o7777)
        print("RAPOR_KORU_ONCE kok=%s hal=YEDEK once=%d" % (kok, len(veri)))
    return 0


def ayrac(n_once, n_sonra, kok):
    return ("\n\n## %s — ⚠ isci-rapor-koru: EKLEME-DISI YAZIM GERI ALINDI "
            "(yazim oncesi %d B, yazim sonrasi %d B, kok %s); yazilan icerik asagida, "
            "hicbir sey silinmedi\n\n" % (time.strftime("%Y-%m-%d %H:%M"), n_once, n_sonra, kok)
            ).encode("utf-8")


def sonra(kokler, kimlik):
    red = olculemedi = 0
    for kok in kokler:
        dosya, bak = os.path.join(kok, AD), _bak(kok, kimlik)
        if not os.path.isfile(bak):
            hal = "YENI" if os.path.isfile(dosya) else "YOK"
            print("RAPOR_KORU kok=%s hal=%s" % (kok, hal))
            continue
        eski = _oku(bak)
        yeni = _oku(dosya) if os.path.isfile(dosya) else b""
        if yeni.startswith(eski):
            os.unlink(bak)
            print("RAPOR_KORU kok=%s hal=GECTI once=%d sonra=%d" % (kok, len(eski), len(yeni)))
            continue
        geri = eski
        if yeni:
            geri = eski + (b"" if eski.endswith(b"\n") or not eski else b"\n") \
                + ayrac(len(eski), len(yeni), kok) + yeni
        try:
            _atomik_yaz(dosya, geri, os.stat(bak).st_mode & 0o7777)
            tamam = _oku(dosya) == geri
        except OSError as e:
            tamam = False
            print("RAPOR_KORU kok=%s hata=%s" % (kok, e.__class__.__name__))
        if not tamam:
            olculemedi += 1
            print("RAPOR_KORU kok=%s hal=OLCULEMEDI sebep=geri-yazilamadi yedek=%s" % (kok, bak))
            continue
        os.unlink(bak)
        red += 1
        print("RAPOR_KORU kok=%s hal=RED once=%d sonra=%d geri=%d"
              % (kok, len(eski), len(yeni), len(geri)))
    print("RAPOR_KORU_OZET=%s red=%d olculemedi=%d"
          % ("OLCULEMEDI" if olculemedi else ("RED" if red else "GECTI"), red, olculemedi))
    return 3 if olculemedi else (1 if red else 0)


# ---------------------------------------------------------------- yama

def _capalar(satirlar):
    cagri = [i for i, s in enumerate(satirlar) if CAGRI_CAPASI in s]
    rc = [i for i, s in enumerate(satirlar) if s.strip() == RC_CAPASI]
    if len(cagri) != 1 or len(rc) != 1 or not cagri[0] < rc[0]:
        return None
    return cagri[0], rc[0]


def kanca_sayisi(satirlar):
    m = _capalar(satirlar)
    if m is None:
        return 0
    c, r = m
    n = 0
    if c > 0 and satirlar[c - 1].strip() == ONCE_SON:
        n += 1
    if r + 1 < len(satirlar) and satirlar[r + 1].strip().startswith(SONRA_BAS):
        n += 1
    return n


def yamala(satirlar):
    c, r = _capalar(satirlar)
    girinti = satirlar[c][:len(satirlar[c]) - len(satirlar[c].lstrip())]
    yeni = list(satirlar)
    if not (r + 1 < len(yeni) and yeni[r + 1].strip().startswith(SONRA_BAS)):
        yeni[r + 1:r + 1] = sonra_blogu(girinti)
    if not (c > 0 and yeni[c - 1].strip() == ONCE_SON):
        yeni[c:c] = once_blogu(girinti)
    return yeni


def _sha(yol):
    try:
        return hashlib.sha256(_oku(yol)).hexdigest()
    except OSError:
        return None


def kopya_hali(isci):
    hedef = os.path.join(os.path.dirname(os.path.abspath(isci)), KOPYA_ADI)
    s = _sha(hedef)
    if s is None:
        return hedef, "YOK"
    return hedef, "ESIT" if s == _sha(os.path.abspath(__file__)) else "FARKLI"


def main(argv):
    if len(argv) >= 2 and argv[1] in ("once", "sonra"):
        kokler, kimlik, i = [], "", 2
        while i < len(argv):
            if argv[i] == "--kok" and i + 1 < len(argv):
                kokler.append(argv[i + 1])
            elif argv[i] == "--kimlik" and i + 1 < len(argv):
                kimlik = argv[i + 1]
            else:
                print("kullanim: once|sonra --kok D [--kok D ...] [--kimlik K]", file=sys.stderr)
                return 2
            i += 2
        if not kokler:
            print("kullanim: en az bir --kok", file=sys.stderr)
            return 2
        kokler = _kokler(kokler)
        return (once if argv[1] == "once" else sonra)(kokler, kimlik)
    if len(argv) != 3 or argv[1] not in ("yama", "kontrol"):
        print("kullanim: isci-rapor-koru.py once|sonra|yama|kontrol ...", file=sys.stderr)
        return 2
    yol = argv[2]
    try:
        with open(yol, encoding="utf-8") as f:
            satirlar = f.readlines()
    except OSError as e:
        print("OLCULEMEDI sebep=okunamadi:%s" % e.__class__.__name__)
        return 3
    if _capalar(satirlar) is None:
        print("OLCULEMEDI sebep=capa-yok-ya-da-cogul (%s / %s)" % (CAGRI_CAPASI, RC_CAPASI))
        return 3
    if argv[1] == "yama":
        yeni = yamala(satirlar)
        degisti = yeni != satirlar
        if degisti:
            kip = os.stat(yol).st_mode & 0o7777
            _atomik_yaz(os.path.abspath(yol), "".join(yeni).encode("utf-8"), kip)
            satirlar = yeni
        hedef, hal = kopya_hali(yol)
        if hal != "ESIT":
            _atomik_yaz(hedef, _oku(os.path.abspath(__file__)), 0o755)
        print("UYGULANDI degisti=%d kopya=%s" % (int(degisti), "yazildi" if hal != "ESIT" else "esit"))
    n = kanca_sayisi(satirlar)
    _, hal = kopya_hali(yol)
    print("KORU_KANCASI=%d/2 KOPYA=%s" % (n, hal))
    return 0 if n == 2 and hal == "ESIT" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
