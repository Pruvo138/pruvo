"""KILIT — TEK KAYNAK. K160 dilim-1.

Tarihce: nobet-kapi.py:54'teki KILIT_BAYATLIK_SN, nobet-kapi.py:628'deki
kilit_karari, nobet-kapi.py:951'deki kilit_al, nobet-kapi.py:973'teki
kilit_birak VE gozcu.py:296'daki _kilit_al (K148 onarimli), gozcu.py:346'daki
_kilit_birak — bu modulun govdesine TASINMIS, KOPYASI kalmamistir.

Referans govde: gozcu.py K148 (O_EXCL-once + FileExistsError'da taze-okuma
+ "DOLU CALINMAZ, artik kilit TEK KEZ devralinir").

Cagri sozlesmesi:
  - al(): doner (alindi: bool, hukum: str)
      hukum ∈ {"KILIT_ALINDI", "ONCEKI_TUR_SURUYOR", "DEVRALINDI", "YAZILAMADI"}
  - birak(): sahiplik denetimli; dosyada PID=<kendi pid> yoksa SILMEZ, False doner.
  - karar(): AL | DOLU | BAYAT.

DİKKAT: `epok_bicimi` parametresi gozcunun "%.3f" ve nöbetin "%.0f"
biçimleri farkli davranir (mevcut vakalar bu bicimlere bagli).
Bicimi TEKLESTIRME — vaka kiralar.
"""

import os


KILIT_BAYATLIK_SN = 3600  # TEK KAYNAK (nobet-kapi.py:54'ten TASINDI)


def karar(icerik, simdi, pid_canli_mi):
    """AL | DOLU | BAYAT — nobet-kapi.py:628'deki govde TASINDI (kopya DEGIL)."""
    if not icerik:
        return "AL"
    pid = 0
    damga = 0.0
    for satir in icerik.split("\n"):
        if satir.startswith("PID="):
            try:
                pid = int(satir[4:].strip())
            except ValueError:
                pid = 0
        elif satir.startswith("EPOK="):
            try:
                damga = float(satir[5:].strip())
            except ValueError:
                damga = 0.0
    if damga and (simdi - damga) > KILIT_BAYATLIK_SN:
        return "BAYAT"
    if pid and not pid_canli_mi(pid):
        return "BAYAT"
    if not pid:
        return "BAYAT"
    return "DOLU"


def al(yol, simdi, pid_canli_mi, epok_bicimi="%.0f", damga=None, araya_gir=None):
    """Doner: (alindi: bool, hukum: str).

    hukum ∈ {"KILIT_ALINDI", "ONCEKI_TUR_SURUYOR", "DEVRALINDI", "YAZILAMADI"}

    Govde = gozcu.py:296-343 K148 (referans). `damga` cagrilabilir; None ise
    damga satiri "" yazilir. `araya_gir` YALNIZ TEST dikisi; uretimde daima None.
    """
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    try:
        with open(yol, encoding="utf-8") as dosya:
            icerik = dosya.read()
    except OSError:
        icerik = None
    if karar(icerik, simdi, pid_canli_mi) == "DOLU":
        return False, "ONCEKI_TUR_SURUYOR"
    # DIKIS (YALNIZ TEST): karar ile yazma arasindaki TOCTOU penceresini
    # DETERMINISTIK olarak uretmek icin. Uretimde daima None.
    if araya_gir is not None:
        araya_gir()
    devralindi = False  # T2: dosya varken DEVRALINDI ayirt edilsin.
    try:
        fd = os.open(yol, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        # Dosya ya zaten duruyordu ya da PENCEREDE dogdu. KOR SILME YOK:
        # once TAZE oku, hukmu YENIDEN ver.
        try:
            with open(yol, encoding="utf-8") as dosya:
                taze = dosya.read()
        except OSError:
            return False, "YAZILAMADI"
        if karar(taze, simdi, pid_canli_mi) == "DOLU":
            return False, "ONCEKI_TUR_SURUYOR"  # CANLI rakip — kilidi CALMA
        # Artik kilit (0 bayt / bozuk / olu pid): TEK KEZ devral.
        try:
            os.unlink(yol)
        except FileNotFoundError:
            pass
        except OSError:
            return False, "YAZILAMADI"
        try:
            fd = os.open(yol, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError:
            return False, "ONCEKI_TUR_SURUYOR"  # devralma yarisini baskasi kazandi
        devralindi = True  # T2: devralma farkli bir olay — sicilde ayri gorunmeli.
    except OSError:
        return False, "YAZILAMADI"
    damga_str = damga() if damga is not None else ""
    with os.fdopen(fd, "w", encoding="utf-8") as dosya:
        dosya.write("PID=%d\nEPOK=%s\nDAMGA=%s\n" % (os.getpid(), epok_bicimi % simdi, damga_str))
    if devralindi:
        return True, "DEVRALINDI"
    return True, "KILIT_ALINDI"


def birak(yol):
    """Sahiplik denetimli: dosyada `PID=<kendi pid>` yoksa SILMEZ, False doner."""
    try:
        with open(yol, encoding="utf-8") as dosya:
            icerik = dosya.read()
    except OSError:
        return False
    if ("PID=%d" % os.getpid()) not in icerik:
        return False
    try:
        os.unlink(yol)
    except OSError:
        return False
    return True