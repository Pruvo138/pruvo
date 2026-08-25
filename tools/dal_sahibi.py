#!/usr/bin/env python3
"""DAL SAHIBI — dal/is basina TEK-SAHIP kaydi (K50).

OLCULMUS VAKA (kalem K50, [[paylasilan-defterde-mukerrer-tur]]): `kral/d1-tavsiye-kolon`
merge'i IKI oturuma paralel verildi; ikinci oturum merge'i, birincisi henuz olcerken
icra etti. Kayip olmadi ama yalniz sans eseri — dal basina tek-sahip kaydi YOKTU.
Taban olcumu (25 Agu 2026): `grep -rn 'dal_sahibi' tools ~/.claude/cron` -> 0 hit.

BU ARACIN YAPTIGI SEY (kapsam, bilerek DAR):
  Bir dal/is adini bir SAHIBE kaydeder, kaydi makine-okunur basar, ikinci talibi
  REDDEDER. Kayit `.git` ortak dizininde tutulur — TUM worktree'ler ayni kaydi gorur.

BU ARACIN YAPMADIGI SEY (YASAK, spec K50):
  * MERGE KAPISININ YERINE GECMEZ. Hicbir git islemi yapmaz, merge'i durdurmaz,
    dal silmez. Merge yargisi ayri katmandir (skill: merge-kapisi). Bu arac yalniz
    "bu dali kim aldi" sorusunu cevaplar.
  * FAIL-OPEN DEGILDIR: kayit dizini acilamiyorsa ya da kayit okunamiyorsa is
    SERBEST sayilmaz — RED doner (rc=2 / HUKUM=SAHIPLI KOL=OKUNAMAZ).
  * SONSUZ KILIT DE KURMAZ: bkz BAYAT KOLU.

BAYAT KOLU — NEDEN HEM TAVAN HEM DEVIR (⑤, secim SEBEBIYLE):
  Iki kolu birden koyduk, cunku tek basina her biri olculmus bir ariza sinifi uretir:
    (a) YALNIZ ZAMAN TAVANI olsaydi: yavas ama CANLI bir sahibin kilidi, o hala
        calisirken calinirdi. Cozum: her `al`/`dokun`/`birak` cagrisi kalp atisini
        (`dokunuldu`) tazeler — canli sahip tavana hic yaklasmaz.
    (b) YALNIZ ACIK DEVRALMA olsaydi: oturum SESSIZCE olurse (panel kapandi, makine
        yeniden basladi) kimse devralmayi bilmez ve kilit SONSUZA kadar kalir. Bu tam
        olarak [[izleyici-sonsuz-dongu-terminal-kol]] sinifidir: kosul saglanamaz hale
        gelince dongu olmez. Cozum: `dokunuldu` uzerinden ZAMAN TAVANI (varsayilan
        7200 sn) — kalp atisi durunca kayit kendiliginden devralinabilir olur.
  Yani: kalp atisi canli sahibi KORUR, tavan olu sahibi TEMIZLER, `devral --gerekce`
  ise beklemeden gecmenin GEREKCESI KAYITLI yoludur. Ucu bir arada; hicbiri tek basina
  yeterli degil.

ES ZAMANLILIK: butun okuma-degistirme-yazma bolgesi kayit dosyasi uzerinde `flock`
(LOCK_EX|LOCK_NB + tavanli deneme dongusu) ile serilestirilir. Beklemenin tavani vardir
(KILIT_BEKLEME_SN) — kilit alinamazsa HATA doner, sonsuza kadar BEKLEMEZ.

KOMUTLAR
  al      --dal D --sahip S [--tavan-sn N] [--not X]   dali al (yeniden-giris serbest)
  dokun   --dal D --sahip S                            kalp atisini tazele
  birak   --dal D --sahip S                            kaydi birak
  devral  --dal D --sahip S --gerekce G                acik devralma (gerekce ZORUNLU)
  durum   [--dal D]                                    makine-okunur dokum

CIKIS KODU
  0  dal SENIN (ALINDI / SAHIP-BEN / BAYAT-DEVIR / DEVRALINDI / BIRAKILDI / durum ok)
  1  dal BASKASININ (SAHIPLI) — yeni is BASLATILMAZ
  2  RED / HATA (eksik arguman, kayit dizini acilamadi, gerekcesiz devralma)
"""
import argparse
import errno
import fcntl
import hashlib
import json
import os
import re
import sys
import time

# Kalp atisi tavani: bu kadar saniyedir dokunulmamis kayit BAYAT sayilir.
VARSAYILAN_TAVAN_SN = 7200
# Kayit dosyasinin flock'unu beklemenin TAVANI. Tavansiz bekleme yasak.
KILIT_BEKLEME_SN = 5.0
KILIT_ARA_SN = 0.02

_SLUG_TEMIZ = re.compile(r"[^A-Za-z0-9._-]+")


def _git_ortak_dizin(baslangic):
    """`.git` ortak dizinini bulur (worktree'den de dogru kokU verir).

    git'i CAGIRMADAN cozer: worktree'de `.git` bir DOSYADIR ve icinde
    'gitdir: <yol>/.git/worktrees/<ad>' yazar; ortak dizin onun iki ust dizinidir.
    Bulunamazsa None — cagiran fail-closed davranir.
    """
    yol = os.path.abspath(baslangic)
    while True:
        aday = os.path.join(yol, ".git")
        if os.path.isdir(aday):
            return aday
        if os.path.isfile(aday):
            try:
                with open(aday, encoding="utf-8") as f:
                    icerik = f.read().strip()
            except OSError:
                return None
            if icerik.startswith("gitdir:"):
                gd = os.path.normpath(icerik.split(":", 1)[1].strip())
                # <ortak>/.git/worktrees/<ad>  ->  <ortak>/.git
                ust = os.path.dirname(os.path.dirname(gd))
                if os.path.basename(ust) == ".git":
                    return ust
                return gd
            return None
        ust = os.path.dirname(yol)
        if ust == yol:
            return None
        yol = ust


def kayit_koku(cwd=None):
    """Kayitlarin tutuldugu dizin.

    Neden `.git` ORTAK dizini: (a) tum worktree'ler ve tum oturumlar ayni dosyayi
    gorur — kayit gercekten TEK'tir; (b) izlenmez, commit'lenmez, merge catismasi
    uretmez; (c) klonla birlikte olur — Okan'in makinesinde kalici iz birakmaz
    (DISK KURALI). Testler `PRUVO_DAL_SAHIP_KOK` ile baska bir koke yonlendirir.
    """
    zorlama = os.environ.get("PRUVO_DAL_SAHIP_KOK")
    if zorlama:
        return zorlama
    ortak = _git_ortak_dizin(cwd or os.getcwd())
    if not ortak:
        return None
    return os.path.join(ortak, "pruvo-dal-sahipleri")


def _slug(dal):
    """Dal adini dosya adina cevirir. Ham adin sha1 oneki EKLENIR ki
    'a/b' ile 'a_b' ayni dosyaya dusmesin (temizleme carpismasi)."""
    ozet = hashlib.sha1(dal.encode("utf-8")).hexdigest()[:12]
    govde = _SLUG_TEMIZ.sub("_", dal).strip("_") or "dal"
    return govde[:80] + "-" + ozet + ".json"


def _simdi():
    return time.time()


# ---------------------------------------------------------------- KOL: KILIT
def _kilit_al(fd):
    """ARM/KOL: KILIT — kayit dosyasi uzerinde ozel (exclusive) flock.

    Bu kol, iki oturumun ayni kaydi AYNI ANDA okuyup yazmasini engeller; "ikisi de
    bos gordu, ikisi de yazdi" yarisini kapatan sey budur. Beklemenin TAVANI var:
    KILIT_BEKLEME_SN icinde alinamazsa False doner (cagiran RED verir).
    """
    bitis = _simdi() + KILIT_BEKLEME_SN
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError as e:
            if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                return False
            if _simdi() >= bitis:
                return False
            time.sleep(KILIT_ARA_SN)


def _kilit_birak(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


# ---------------------------------------------------------------- KOL: BAYAT
def _bayat_mi(kayit, simdi):
    """ARM/KOL: BAYAT — kalp atisi tavani asildi mi?

    Tavan kaydin KENDI `tavan_sn` alanindan okunur (sahibi alirken belirler).
    `tavan_sn <= 0` => kayit dogusta bayattir (testler bunu kullanir).
    Kayit bozuksa cagiran dosya mtime'ini `dokunuldu` yerine gecirir.
    """
    tavan = kayit.get("tavan_sn", VARSAYILAN_TAVAN_SN)
    try:
        tavan = float(tavan)
    except (TypeError, ValueError):
        tavan = VARSAYILAN_TAVAN_SN
    if tavan <= 0:
        return True
    try:
        dokunuldu = float(kayit.get("dokunuldu") or 0.0)
    except (TypeError, ValueError):
        dokunuldu = 0.0
    return (simdi - dokunuldu) > tavan


def _kalan_sn(kayit, simdi):
    tavan = kayit.get("tavan_sn", VARSAYILAN_TAVAN_SN)
    try:
        tavan = float(tavan)
    except (TypeError, ValueError):
        tavan = VARSAYILAN_TAVAN_SN
    try:
        dokunuldu = float(kayit.get("dokunuldu") or 0.0)
    except (TypeError, ValueError):
        dokunuldu = 0.0
    return int(max(0.0, tavan - (simdi - dokunuldu)))


# ---------------------------------------------------------------- KOL: SAHIP
def _sahip_mi(kayit, sahip):
    """ARM/KOL: SAHIP — kayitli sahip ile cagiran ayni mi?

    Bu kol ③'un (yanlis-pozitif nobeti) tasiyicisidir: sahibi olan oturum kendi
    dalinda calismaya DEVAM edebilmeli; kilit kendi sahibini bloklarsa kabul DEGIL.
    """
    return (kayit.get("sahip") or "") == sahip


def _oku(fd):
    """Kayit govdesini okur. Donus: (kayit|None, bozuk_mu)."""
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        ham = os.read(fd, 1 << 20).decode("utf-8")
    except OSError:
        return None, True
    if not ham.strip():
        return None, False  # bos dosya = SERBEST
    try:
        kayit = json.loads(ham)
    except ValueError:
        return None, True
    if not isinstance(kayit, dict) or not kayit.get("sahip"):
        return None, True
    return kayit, False


def _yaz(fd, kayit):
    govde = json.dumps(kayit, ensure_ascii=False, sort_keys=True, indent=1)
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    os.write(fd, govde.encode("utf-8"))
    try:
        os.fsync(fd)
    except OSError:
        pass


def _kayit_kur(dal, sahip, tavan_sn, notu, simdi, onceki=None, gerekce=""):
    return {
        "dal": dal,
        "sahip": sahip,
        "pid": os.getpid(),
        "alindi": simdi,
        "dokunuldu": simdi,
        "tavan_sn": tavan_sn,
        "not": notu or "",
        "onceki_sahip": onceki or "",
        "devir_gerekce": gerekce or "",
    }


def _satir(hukum, kol, dal, sahip, kayit=None, onceki="", simdi=None):
    simdi = simdi if simdi is not None else _simdi()
    kalan = _kalan_sn(kayit, simdi) if kayit else 0
    return (
        "DAL_SAHIP HUKUM=%s KOL=%s DAL=%s SAHIP=%s ONCEKI=%s KALAN_SN=%d"
        % (hukum, kol, dal, sahip, onceki or "-", kalan)
    )


def _cikti(args, hukum, kol, dal, sahip, kayit=None, onceki="", aciklama=""):
    simdi = _simdi()
    if getattr(args, "json", False):
        print(json.dumps({
            "hukum": hukum, "kol": kol, "dal": dal, "sahip": sahip,
            "onceki_sahip": onceki, "kalan_sn": _kalan_sn(kayit, simdi) if kayit else 0,
            "aciklama": aciklama, "kayit": kayit,
        }, ensure_ascii=False, sort_keys=True))
    else:
        print(_satir(hukum, kol, dal, sahip, kayit, onceki, simdi))
        if aciklama:
            print("  " + aciklama)
    return hukum


def _dosya_ac(dal, args):
    """Kayit dosyasini acar (yoksa yaratir) ve kilitler.

    FAIL-CLOSED: kok dizin acilamaz ya da kilit alinamazsa (None, rc) doner —
    cagiran isi SERBEST saymaz, RED verir.
    """
    kok = kayit_koku()
    if not kok:
        _cikti(args, "HATA", "KOK-YOK", dal, getattr(args, "sahip", "") or "-",
               aciklama="git ortak dizini bulunamadi; kayit YAZILAMAZ -> fail-closed RED")
        return None, 2
    try:
        os.makedirs(kok, exist_ok=True)
    except OSError as e:
        _cikti(args, "HATA", "KOK-ACILMADI", dal, getattr(args, "sahip", "") or "-",
               aciklama="kayit dizini acilamadi (%s) -> fail-closed RED" % e)
        return None, 2
    yol = os.path.join(kok, _slug(dal))
    try:
        fd = os.open(yol, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as e:
        _cikti(args, "HATA", "DOSYA-ACILMADI", dal, getattr(args, "sahip", "") or "-",
               aciklama="kayit dosyasi acilamadi (%s) -> fail-closed RED" % e)
        return None, 2
    if not _kilit_al(fd):
        os.close(fd)
        _cikti(args, "HATA", "KILIT-TAVANI", dal, getattr(args, "sahip", "") or "-",
               aciklama="flock %.1f sn icinde alinamadi -> fail-closed RED (sonsuz bekleme YOK)"
                        % KILIT_BEKLEME_SN)
        return None, 2
    return (fd, yol), 0


def _kapat(tutamac):
    fd, _ = tutamac
    _kilit_birak(fd)
    os.close(fd)


def _bozuk_bayat_mi(yol, simdi, tavan_sn):
    """Bozuk kayit icin BAYAT olcumu: govde okunamadigindan dosya mtime'i
    kalp atisi yerine gecer. Boylece bozuk bir kayit da SONSUZ kilit uretmez."""
    try:
        mt = os.stat(yol).st_mtime
    except OSError:
        return True
    return (simdi - mt) > max(0.0, float(tavan_sn))


# ---------------------------------------------------------------- KOMUTLAR
def komut_al(args):
    tutamac, rc = _dosya_ac(args.dal, args)
    if tutamac is None:
        return rc
    fd, yol = tutamac
    try:
        simdi = _simdi()
        kayit, bozuk = _oku(fd)

        if bozuk:
            # FAIL-CLOSED: bozuk kayit SERBEST demek DEGILDIR.
            if not _bozuk_bayat_mi(yol, simdi, args.tavan_sn):
                _cikti(args, "SAHIPLI", "OKUNAMAZ", args.dal, args.sahip,
                       aciklama="kayit bozuk ama TAZE -> serbest SAYILMAZ (fail-closed)")
                return 1
            yeni = _kayit_kur(args.dal, args.sahip, args.tavan_sn, args.notu, simdi,
                              onceki="?bozuk", gerekce="bozuk+bayat kayit")
            _yaz(fd, yeni)
            _cikti(args, "BAYAT-DEVIR", "BOZUK-BAYAT", args.dal, args.sahip, yeni, "?bozuk")
            return 0

        if kayit is None:
            yeni = _kayit_kur(args.dal, args.sahip, args.tavan_sn, args.notu, simdi)
            _yaz(fd, yeni)
            _cikti(args, "ALINDI", "YENI", args.dal, args.sahip, yeni)
            return 0

        if _sahip_mi(kayit, args.sahip):
            # ③ YANLIS-POZITIF NOBETI: kendi sahibini BLOKLAMAZ, kalp atisini tazeler.
            kayit["dokunuldu"] = simdi
            kayit["pid"] = os.getpid()
            if args.notu:
                kayit["not"] = args.notu
            _yaz(fd, kayit)
            _cikti(args, "SAHIP-BEN", "YENIDEN-GIRIS", args.dal, args.sahip, kayit)
            return 0

        if _bayat_mi(kayit, simdi):
            onceki = kayit.get("sahip") or ""
            yeni = _kayit_kur(args.dal, args.sahip, args.tavan_sn, args.notu, simdi,
                              onceki=onceki, gerekce="kalp atisi tavani asildi")
            _yaz(fd, yeni)
            _cikti(args, "BAYAT-DEVIR", "TAVAN-ASILDI", args.dal, args.sahip, yeni, onceki)
            return 0

        # ② YARIS PENCERESI: ikinci talip REDDEDILIR.
        _cikti(args, "SAHIPLI", "BASKASI", args.dal, args.sahip, kayit,
               kayit.get("sahip") or "",
               aciklama="dal sahibi: %s (kalan %d sn). Yeni is BASLATMA; "
                        "beklemeyeceksen 'devral --gerekce' kullan."
                        % (kayit.get("sahip"), _kalan_sn(kayit, simdi)))
        return 1
    finally:
        _kapat(tutamac)


def komut_dokun(args):
    tutamac, rc = _dosya_ac(args.dal, args)
    if tutamac is None:
        return rc
    fd, _ = tutamac
    try:
        simdi = _simdi()
        kayit, bozuk = _oku(fd)
        if bozuk or kayit is None:
            _cikti(args, "SAHIPSIZ", "KAYIT-YOK", args.dal, args.sahip,
                   aciklama="dokunulacak gecerli kayit yok -> once 'al'")
            return 1
        if not _sahip_mi(kayit, args.sahip):
            _cikti(args, "SAHIPLI", "BASKASI", args.dal, args.sahip, kayit,
                   kayit.get("sahip") or "")
            return 1
        kayit["dokunuldu"] = simdi
        kayit["pid"] = os.getpid()
        _yaz(fd, kayit)
        _cikti(args, "DOKUNULDU", "KALP-ATISI", args.dal, args.sahip, kayit)
        return 0
    finally:
        _kapat(tutamac)


def komut_birak(args):
    tutamac, rc = _dosya_ac(args.dal, args)
    if tutamac is None:
        return rc
    fd, _ = tutamac
    try:
        kayit, bozuk = _oku(fd)
        if kayit is None and not bozuk:
            _cikti(args, "SAHIPSIZ", "ZATEN-BOS", args.dal, args.sahip)
            return 0
        if not bozuk and not _sahip_mi(kayit, args.sahip):
            _cikti(args, "SAHIPLI", "BASKASI", args.dal, args.sahip, kayit,
                   kayit.get("sahip") or "",
                   aciklama="baskasinin kaydini birakamazsin; 'devral --gerekce' kullan")
            return 1
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        _cikti(args, "BIRAKILDI", "SAHIP", args.dal, args.sahip)
        return 0
    finally:
        _kapat(tutamac)


def komut_devral(args):
    # ⑤ ACIK DEVRALMA KOLU: GEREKCE ZORUNLU — sessiz calma yok, iz kalir.
    if not (args.gerekce or "").strip():
        _cikti(args, "RED", "GEREKCE-YOK", args.dal, args.sahip,
               aciklama="acik devralma --gerekce ZORUNLU")
        return 2
    tutamac, rc = _dosya_ac(args.dal, args)
    if tutamac is None:
        return rc
    fd, _ = tutamac
    try:
        simdi = _simdi()
        kayit, bozuk = _oku(fd)
        onceki = "" if (bozuk or kayit is None) else (kayit.get("sahip") or "")
        yeni = _kayit_kur(args.dal, args.sahip, args.tavan_sn, args.notu, simdi,
                          onceki=onceki or ("?bozuk" if bozuk else ""),
                          gerekce=args.gerekce.strip())
        _yaz(fd, yeni)
        _cikti(args, "DEVRALINDI", "ACIK-DEVIR", args.dal, args.sahip, yeni, onceki)
        return 0
    finally:
        _kapat(tutamac)


def komut_durum(args):
    kok = kayit_koku()
    simdi = _simdi()
    satirlar = []
    if kok and os.path.isdir(kok):
        for ad in sorted(os.listdir(kok)):
            if not ad.endswith(".json"):
                continue
            yol = os.path.join(kok, ad)
            try:
                with open(yol, encoding="utf-8") as f:
                    ham = f.read()
            except OSError:
                continue
            if not ham.strip():
                continue
            try:
                k = json.loads(ham)
            except ValueError:
                satirlar.append({"dal": "?", "sahip": "?bozuk", "dosya": ad,
                                 "bayat": _bozuk_bayat_mi(yol, simdi, VARSAYILAN_TAVAN_SN)})
                continue
            if not isinstance(k, dict) or not k.get("sahip"):
                continue
            if args.dal and k.get("dal") != args.dal:
                continue
            satirlar.append({"dal": k.get("dal"), "sahip": k.get("sahip"),
                             "kalan_sn": _kalan_sn(k, simdi), "bayat": _bayat_mi(k, simdi),
                             "not": k.get("not", ""), "onceki_sahip": k.get("onceki_sahip", "")})
    if args.json:
        print(json.dumps({"kok": kok, "kayit_sayisi": len(satirlar), "kayitlar": satirlar},
                         ensure_ascii=False, sort_keys=True))
    else:
        print("DAL_SAHIP DURUM KOK=%s KAYIT=%d" % (kok or "-", len(satirlar)))
        for s in satirlar:
            print("  DAL=%s SAHIP=%s KALAN_SN=%s BAYAT=%s NOT=%s"
                  % (s.get("dal"), s.get("sahip"), s.get("kalan_sn", "-"),
                     "EVET" if s.get("bayat") else "HAYIR", s.get("not", "")))
    return 0


def ana(argv=None):
    p = argparse.ArgumentParser(
        prog="dal_sahibi.py",
        description="Dal/is basina tek-sahip kaydi (K50). Merge kapisinin YERINE GECMEZ.")
    alt = p.add_subparsers(dest="komut", required=True)

    def ortak(sp, sahip_zorunlu=True):
        sp.add_argument("--dal", required=True)
        sp.add_argument("--sahip", required=sahip_zorunlu)
        sp.add_argument("--tavan-sn", dest="tavan_sn", type=float,
                        default=VARSAYILAN_TAVAN_SN)
        sp.add_argument("--not", dest="notu", default="")
        sp.add_argument("--json", action="store_true")

    sp = alt.add_parser("al"); ortak(sp); sp.set_defaults(fn=komut_al)
    sp = alt.add_parser("dokun"); ortak(sp); sp.set_defaults(fn=komut_dokun)
    sp = alt.add_parser("birak"); ortak(sp); sp.set_defaults(fn=komut_birak)
    sp = alt.add_parser("devral"); ortak(sp)
    sp.add_argument("--gerekce", default="")
    sp.set_defaults(fn=komut_devral)
    sp = alt.add_parser("durum")
    sp.add_argument("--dal", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=komut_durum)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(ana())
