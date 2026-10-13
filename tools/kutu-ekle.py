#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTAK POSTA KUTUSU — BASA EKLEME TEK YOLU (BaBa 13 Eki 2026).

NEDEN VAR (BaBa 13 Eki 16:2x + 17:5x): 14:5x KraL blogu eşzamanlı tam-dosya yazımıyla
EZILDI; Pages 38399235384'te kırmızı koşumun derinlik adımı 30+ dk asılı kaldı. Bu iki
aksın AYNI anda TEK bir cozumu var — tek bir kutu yazım yolu:

  1. AYNI kilidi (`.<kutu-adı>.lock`) kutu-arsivle ile ORTAK kullan (tek dosya formulu,
     kilit biri tutuyorken digeri bloke olur → iki aracin yarisi YARIS OLMAZ).
  2. Kilidi ALDIKTAN SONRA kutuyu oku (bayat snapshot uzerine yazma).
  3. Basa yazimi ATOMIK yap (gecici + fsync + os.replace → yarim dosya GORUNMEZ).
  4. Blogu "## " ile baslamaya ZORLA (bebek bloklar / yorum eklenmez; spec'i olmayan
     metin kapidan GEÇEMEZ).

Iki KRITIK kural:
  * FAIL-CLOSED: kilit 60 sn'de alinamazsa rc=2 + HICBIR SEY yazilmaz (sessiz basari
    YOK). 14:5x'te "yaris kazandi, ben de yazdim" yaklasimi sifir BLOG kaybi demek.
  * TEK KAYNAK: kilit yolu kutu-arsivle'deki formulu birebir uygular
    (`.<kutu-adı>.lock`, ayni dizin). Ikinci bir formül YAZILMAZ; kutu-arsivle bunu
    import etseydi daha iyi olurdu, ama o geriye donuk baglamiligi ile yasak — bu
    yuzden formulu satir satir TUTARIZ, birinin degismesi durumunda DIGERINI DE
    degistirmeyi UNUTMAYIZ.

Kullanim:
    python3 tools/kutu-ekle.py --kutu <kutu.md> --dosya <blok.md>
    echo "## ..." | python3 tools/kutu-ekle.py --kutu <kutu.md> --metin -
"""
import argparse
import fcntl
import os
import sys
import tempfile
import time

RC_OK = 0
RC_KIRMIZI = 1       # bozuk girdi / bicim hatasi / atomik yazim basarisiz
RC_KILIT = 2         # kilit 60 sn'de alinamadi -> fail-closed

# Kilit yolu: kutu ile ayni dizinde ".<kutu-adı>.lock". kutu-arsivle ile ORTAK
# formül (kutu-arsivle.py ~L3168-3169); biri degisirse DIGERI de degismeli.
KILIT_DOSYA_ADI_BICIMI = ".%s.lock"


def _kilit_yolu(kutu_yolu):
    return os.path.join(os.path.dirname(os.path.abspath(kutu_yolu)),
                        KILIT_DOSYA_ADI_BICIMI % os.path.basename(kutu_yolu))


def _kilit_al_blokeli(yol, zaman_asimi_sn=60):
    """(fd, hata). LOCK_EX ile BLOKLANARAK kilit al; zaman_asimi_sn'de alinamazsa rc=2.

    NON-BLOCKING DEGIL: bu arac genellikle etkilesimli (mimar acilis-kapanis blogu
    yaziyor); karsidaki yazici zaten bayat kopya uzerinden plan yapiyor, bizim
    BEKLEMEMIZ + sonra bayatlamis kopya uzerine yazmamamiz dogrudur. zaman_asimi_sn
    sonsuz beklemeyi engeller — karsi taraf cop olursa sonsuza kadar bloklanmayiz.
    """
    try:
        fd = open(yol, "a+")
    except OSError as e:
        return None, "kilit dosyasi acilamadi: %s -> %s" % (yol, e)
    # Zaman asimi GERCEKTEN uygulanir: LOCK_NB ile dener, karsi taraf kilidi
    # birakmazsa zaman_asimi_sn sonunda rc=2 (eskiden parametre okunmuyordu ->
    # takilan tutucu araci sonsuza dek bloklardi; KraL halef-28 olctu, 13 Eki).
    son = time.monotonic() + zaman_asimi_sn
    while True:
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd, None
        except BlockingIOError:
            if time.monotonic() >= son:
                fd.close()
                return None, "kilit ALINAMADI (zaman asimi %s sn): %s" % (zaman_asimi_sn, yol)
            time.sleep(0.1)
        except OSError as e:
            fd.close()
            return None, "kilit ALINAMADI (BLOK): %s -> %s" % (yol, e)


def _kilit_birak(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    finally:
        fd.close()


def _oku(yol):
    """(metin, hata). Yoksa None+sebep; UTF-8 degilse None+sebep."""
    if not os.path.exists(yol):
        return None, "dosya YOK: %s" % yol
    if os.path.isdir(yol):
        return None, "yol bir DIZIN: %s" % yol
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError as e:
        return None, "okunamadi: %s -> %s" % (yol, e)
    try:
        return ham.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, "UTF-8 degil: %s -> %s" % (yol, e)


def _atomik_yaz(yol, metin):
    """Gecici dosya + fsync + os.replace. Kismi/yarim dosya GORUNMEZ."""
    dizin = os.path.dirname(os.path.abspath(yol)) or "."
    kip = None
    if os.path.exists(yol):
        kip = os.stat(yol).st_mode & 0o777
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".kutu-ekle-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        if kip is not None:
            os.chmod(gecici, kip)
        os.replace(gecici, yol)
        gecici = None
    finally:
        if gecici and os.path.exists(gecici):
            os.unlink(gecici)


def main(argv):
    ap = argparse.ArgumentParser(description="Kutunun BASINA tek bir blok ekler.")
    ap.add_argument("--kutu", required=True,
                    help="kutu dosyasinin TAM YOLU")
    grup = ap.add_mutually_exclusive_group(required=True)
    grup.add_argument("--dosya", help="eklenecek blogun TAM YOLU")
    grup.add_argument("--metin", help="stdin icin - ; dogrudan metin olarak verilirse o")
    ap.add_argument("--bekle-sn", type=float, default=60.0,
                    help="kilit icin en cok bekleme (sn); asilirsa rc=2")
    args = ap.parse_args(argv)

    kutu_yolu = os.path.abspath(args.kutu)
    if args.dosya:
        blok_metin, hata = _oku(args.dosya)
        if hata:
            print("KUTU_EKLE=HATA sebep=%s" % hata, file=sys.stderr)
            return RC_KIRMIZI
    else:
        if args.metin == "-":
            blok_metin = sys.stdin.read()
        else:
            blok_metin = args.metin

    # BLOG BICIMI: "## " ile baslamak zorundasinm — bebek blok / duz metin kabul
    # edilmez. Spec'ten gelen her blogun bu sartı zaten tasidigi OLCULDU; bicim
    # hatalisi ALIN EKLENIRSE (1) frontmatter'a karisabilir, (2) blok yapisi bozulur.
    if not blok_metin.startswith("## "):
        print("KUTU_EKLE=HATA sebep=blok '## ' ile baslamiyor (bicim hatalisi)",
              file=sys.stderr)
        return RC_KIRMIZI

    kilit_yolu = _kilit_yolu(kutu_yolu)
    fd, khata = _kilit_al_blokeli(kilit_yolu, args.bekle_sn)
    if fd is None:
        print("KUTU_EKLE=HATA sebep=%s" % khata, file=sys.stderr)
        return RC_KILIT

    try:
        # KILIT ALTINDA oku — ayni anda iki yazici bayat snapshot uzerine yazip
        # birbirinin ekledigi blogu ezer. 14:5x'te tam da bu olculdu.
        eski_metin, ohata = _oku(kutu_yolu)
        if ohata:
            print("KUTU_EKLE=HATA sebep=kutu okunamadi: %s" % ohata,
                  file=sys.stderr)
            return RC_KIRMIZI
        eski = eski_metin or ""

        # SPEC: blok + "\n\n" + eski icerik. Atomik yazim oncesi TAM OLARAK bu
        # formu uret; blokun sonundaki fazla satir sonlari ile cirkin olma.
        satir_once = eski.count("\n")
        yeni = blok_metin.rstrip("\n") + "\n\n" + eski
        satir_sonra = yeni.count("\n")

        try:
            _atomik_yaz(kutu_yolu, yeni)
        except OSError as e:
            print("KUTU_EKLE=HATA sebep=atomik yazim basarisiz: %s" % e,
                  file=sys.stderr)
            return RC_KIRMIZI

        print("KUTU_EKLE=OK satir_once=%d satir_sonra=%d" % (satir_once, satir_sonra))
        return RC_OK
    finally:
        _kilit_birak(fd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))