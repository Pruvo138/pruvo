#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K320 KABUL BATARYASI — nobet hatti UC KOL (A/B/C).

🔴 OLCUM KURULU KOPYADAN YAPILIR ([[emir-canliligi-kurulu-kopyadan-olculur]]):
her vaka `~/.claude/cron/` altindaki CANLI dosyayi yukler. Repodaki yama
kaynagini olcmek YESIL yakar ama emrin canliligini KANITLAMAZ.

Her kol icin: VAKA'lar + en az bir KONTROL + HEDEF-KOL ATIFLI MUTANT.
Mutant sozlesmesi ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]):
bir mutant YALNIZ kendi hedef vakasini dusurmeli, KONTROL vakalari YESIL
kalmalidir. Kontrol de duserse mutant "her seyi kirdi" demektir ve
kirmizinin SEBEBI hedef kol OLDUGU KANITLANMAZ -> YAMA_TUTMADI sayilir.

Cikti (tek makine-okunur ozet):
    KABUL VAKA=<gecen>/<toplam> DUSEN=<n> MUTANT=<olen>/<toplam> \\
          YAMA_TUTMADI=<n> HEDEF_KOL_ATFI=<n>/<n> KONTROL=<gecen>/<toplam>
Cikis: 0 = hepsi yesil · 1 = en az bir kirmizi · 2 = arac hatasi.

NOT: `MUTANT ...` satirlari NORMAL TESHIS ciktisidir, hata DEGILDIR
([[boru-rc-isci-olcumunu-yalanlar]]). rc'yi BORUSUZ oku.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

CRON = os.environ.get("PRUVO_NOBET_KOK") or os.path.join(
    os.path.expanduser("~"), ".claude", "cron")
SH = os.path.join(CRON, "ci-nobeti.sh")
KAPI = os.path.join(CRON, "nobet-kapi.py")
GOZCU = os.path.join(CRON, "gozcu.py")
KARANTINA = os.path.join(CRON, "isci-karantina-karar.py")

_SAYAC = {"vaka": 0, "gecen": 0, "kontrol": 0, "kontrol_gecen": 0}
_DUSENLER = []


def olc(ad, beklenen, gozlenen, kontrol=False):
    _SAYAC["vaka"] += 1
    if kontrol:
        _SAYAC["kontrol"] += 1
    tamam = (beklenen == gozlenen)
    if tamam:
        _SAYAC["gecen"] += 1
        if kontrol:
            _SAYAC["kontrol_gecen"] += 1
    else:
        _DUSENLER.append(ad)
        sys.stderr.write("[DUSTU] %s\n  beklenen=%r\n  gozlenen=%r\n"
                         % (ad, beklenen, gozlenen))
    print("VAKA %-34s %s%s" % (ad, "GECTI" if tamam else "DUSTU",
                               " (KONTROL)" if kontrol else ""))
    return tamam


def _modul(yol, ad):
    # 🔴 `nobet-kapi.py`/`gozcu.py` KARDES modullerini (kilit, nobet_devir,
    # nobet_merdiven, _nobet_bekci ...) duz `import` ile cagirir. importlib ile
    # dosyadan yuklerken cron koku sys.path'te OLMAZSA `ModuleNotFoundError`
    # gelir ve BATARYA "kol dustu" degil "OLCEMEDIM" durumuna duser --
    # ilk kosumda tam olarak bu oldu (9 vaka OLCULEMEDI).
    if CRON not in sys.path:
        sys.path.insert(0, CRON)
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# =========================================================================
# KOL A — ci-nobeti.sh: rc HUKUM'den turer, kosmayan kapi SAYI BASMAZ
# =========================================================================
_STUB = "#!/usr/bin/env python3\nimport sys\nprint('STUB %s')\nsys.exit(%d)\n"


def _a_kos(tetik_rc, kapi_rc, sh_yolu=None):
    """ci-nobeti.sh'i STUB tetik/kapi ile kosar; (rc, log_metni) doner."""
    gecici = tempfile.mkdtemp(prefix="k320-a-")
    try:
        tetik = os.path.join(gecici, "tetik.py")
        kapi = os.path.join(gecici, "kapi.py")
        log = os.path.join(gecici, "nobet.log")
        with open(tetik, "w") as f:
            f.write(_STUB % ("TETIK", tetik_rc))
        with open(kapi, "w") as f:
            f.write(_STUB % ("KAPI", kapi_rc))
        cevre = dict(os.environ)
        cevre.update({
            "PRUVO_NOBET_KOK": gecici,
            "PRUVO_NOBET_LOG": log,
            "PRUVO_NOBET_EV": gecici,
            "PRUVO_NOBET_TETIK": tetik,
            "PRUVO_NOBET_KAPI": kapi,
        })
        sonuc = subprocess.run(["/bin/zsh", sh_yolu or SH], env=cevre,
                               capture_output=True, text=True, timeout=120)
        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                metin = f.read()
        except OSError:
            metin = ""
        return sonuc.returncode, metin
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _a_alan(metin, anahtar):
    """`TETIK_HUKMU ... <anahtar>=<deger>` alanini doner (yoksa None)."""
    for satir in metin.splitlines():
        if satir.startswith("TETIK_HUKMU "):
            for parca in satir.split():
                if parca.startswith(anahtar + "="):
                    return parca.split("=", 1)[1]
    return None


def _a_hukum(metin):
    for satir in metin.splitlines():
        if satir.startswith("HUKUM="):
            return satir.split("=", 1)[1].strip()
    return None


def kol_a(sh_yolu=None, yalniz=None):
    """yalniz=None -> hepsi; aksi halde yalniz o vaka adlarini kos."""
    def istenir(ad):
        return yalniz is None or ad in yalniz

    # A1: tetik ACMA/yesil -> kapi KOSMAZ, hukum TEMIZ, rc 0
    if istenir("A1"):
        rc, log = _a_kos(10, 0, sh_yolu)
        olc("A1 acma/yesil -> TEMIZ rc0",
            ("TEMIZ", 0, "KOSMADI"),
            (_a_hukum(log), rc, _a_alan(log, "nobet_rc")))

    # A2: tetik ACMA/KIRMIZI (seviye) -> kapi KOSMAZ.
    # 🔴 VAKANIN KENDISI: eskiden `nobet_rc=0` basiliyordu ve `BITIS rc=1`
    # ile CELISIYORDU. Kosmayan kapi SAYI BASMAZ.
    if istenir("A2"):
        rc, log = _a_kos(11, 0, sh_yolu)
        olc("A2 seviye kirmizi -> nobet_rc KOSMADI",
            ("SEVIYE_KIRMIZI", 1, "KOSMADI"),
            (_a_hukum(log), rc, _a_alan(log, "nobet_rc")))

    # A3 KONTROL: tetik AC/yesil + kapi yesil -> gercekten TEMIZ
    if istenir("A3"):
        rc, log = _a_kos(0, 0, sh_yolu)
        olc("A3 ac/yesil + kapi yesil -> TEMIZ",
            ("TEMIZ", 0, "0"),
            (_a_hukum(log), rc, _a_alan(log, "nobet_rc")), kontrol=True)

    # A4 KONTROL: kapi GERCEKTEN dustu -> hala KIRMIZI (gevsetme YOK)
    if istenir("A4"):
        rc, log = _a_kos(0, 1, sh_yolu)
        olc("A4 kapi dustu -> ONARIMSIZ_TUR rc1",
            ("ONARIMSIZ_TUR", 1, "1"),
            (_a_hukum(log), rc, _a_alan(log, "nobet_rc")), kontrol=True)

    # A5: BILINMEYEN tetik rc -> fail-closed (tur ACILIR, hukum KIRMIZI)
    if istenir("A5"):
        rc, log = _a_kos(99, 0, sh_yolu)
        olc("A5 bilinmeyen tetik rc -> fail-closed",
            ("TETIK_BILINMEYEN_RC", 1, "1"),
            (_a_hukum(log), rc, _a_alan(log, "acilan_tur")))

    # A6 DEGISMEZLIK: HUKUM=TEMIZ <=> rc=0, dort senaryonun HEPSINDE.
    if istenir("A6"):
        ihlal = []
        for t, k in ((10, 0), (11, 0), (0, 0), (0, 1), (99, 0)):
            rc, log = _a_kos(t, k, sh_yolu)
            if (_a_hukum(log) == "TEMIZ") != (rc == 0):
                ihlal.append((t, k, _a_hukum(log), rc))
        olc("A6 degismezlik TEMIZ<=>rc0", [], ihlal)


# =========================================================================
# KOL B — ucuncu kova + KOSUM_HUKMU jetonu + sebep adiyla
# =========================================================================
def kol_b(kapi_yolu=None, gozcu_yolu=None, yalniz=None, etiket=""):
    def istenir(ad):
        return yalniz is None or ad in yalniz

    try:
        nk = _modul(kapi_yolu or KAPI, "nk_k320" + etiket)
    except Exception as hata:
        for ad in ("B1", "B2", "B3", "B4", "B5"):
            if istenir(ad):
                olc("%s (nobet-kapi YUKLENEMEDI)" % ad, "YUKLENDI",
                    "HATA:%s" % type(hata).__name__)
        nk = None

    if nk is not None:
        # B1: bayrak ISIRDI -> ucuncu kova, rc 0
        if istenir("B1"):
            olc("B1 dondurma isirdi -> DAGITIM_DONDURULDU",
                (0, "DAGITIM_DONDURULDU"),
                nk.tur_hukmu(2, 0, 0, dondurma_isirdi=True))

        # B2 KONTROL: bayrak ISIRMADI -> eski hukum AYNEN durur (gevsetme YOK)
        if istenir("B2"):
            olc("B2 isirmadi -> ONARIMSIZ_TUR (kontrol)",
                (1, "ONARIMSIZ_TUR"),
                nk.tur_hukmu(2, 0, 0, dondurma_isirdi=False), kontrol=True)

        # B3 KONTROL: dondurma, ONARIMSIZ_SUPURME kapisini KALDIRMAZ
        if istenir("B3"):
            olc("B3 dondurma supurmeyi kaldirmaz",
                (1, "ONARIMSIZ_SUPURME"),
                nk.tur_hukmu(2, 0, 0, tasinan=1, dondurma_isirdi=True),
                kontrol=True)

        # B4/B5: `--tur-kapat` KOSUM_HUKMU= jetonunu BASAR (eskiden HIC basmazdi)
        def _tur_kapat_ciktisi(rc, hukum):
            gercek = nk.tur_kapat
            nk.tur_kapat = lambda *a, **k: {
                "rc": rc, "hukum": hukum, "rapor": "RAPOR HUKUM=%s rc=%d" % (hukum, rc)}
            eski = sys.stdout
            sys.stdout = yakala = _Yakala()
            try:
                nk.main(["--tur-kapat"])
            finally:
                sys.stdout = eski
                nk.tur_kapat = gercek
            return yakala.metin()

        if istenir("B4"):
            metin = _tur_kapat_ciktisi(0, "TEMIZ")
            olc("B4 --tur-kapat KOSUM_HUKMU basar",
                True, "KOSUM_HUKMU=TEMIZ" in metin)

        # B5 KONTROL: rc!=0 iken jeton ASLA TEMIZ olmaz (fail-closed)
        if istenir("B5"):
            metin = _tur_kapat_ciktisi(1, "ONARIMSIZ_TUR")
            olc("B5 dusen tur-kapat TEMIZ demez",
                (True, False),
                ("KOSUM_HUKMU=DAGITIM_BACAGI_DUSTU" in metin,
                 "KOSUM_HUKMU=TEMIZ" in metin), kontrol=True)

    try:
        gz = _modul(gozcu_yolu or GOZCU, "gz_k320" + etiket)
    except Exception as hata:
        for ad in ("B6", "B7", "B8", "B9"):
            if istenir(ad):
                olc("%s (gozcu YUKLENEMEDI)" % ad, "YUKLENDI",
                    "HATA:%s" % type(hata).__name__)
        return

    # B6: sebep ADIYLA -- ciktidaki makine HUKUM'u tasinir
    if istenir("B6"):
        sebep = gz.icra_sebebini_ayikla(
            "KOSTU_DUSTU", 1, "satir\nHUKUM=ONARIMSIZ_TUR rc=1\n")
        olc("B6 sebep adiyla (OLCULEMEDI degil)",
            (True, False),
            ("ONARIMSIZ_TUR" in sebep, sebep.strip() == "OLCULEMEDI"))

    # B7: cikti BOS bile olsa CIPLAK 'OLCULEMEDI' donmez -- menzil bildirilir
    if istenir("B7"):
        sebep = gz.icra_sebebini_ayikla("KOSTU_DUSTU", 1, "")
        olc("B7 bos ciktida menzil bildirilir",
            (True, False), ("CIKTI_BOS" in sebep, sebep.strip() == "OLCULEMEDI"))

    # B8 KONTROL: dusmeyen icra icin sebep URETILMEZ
    if istenir("B8"):
        olc("B8 dusmeyen icrada sebep yok", "-",
            gz.icra_sebebini_ayikla("KOSTU_BASARILI", 0, "HUKUM=TEMIZ"),
            kontrol=True)

    # B9: insan satiri alanlari TASIR ve patlamaz (format/arguman esitligi)
    if istenir("B9"):
        try:
            satir = gz.kalp_satiri({"icra_hal": "KOSTU_DUSTU",
                                    "icra_sebep": "HUKUM=ONARIMSIZ_TUR rc=1"})
            gozlenen = ("ICRA_SEBEP=" in satir and "ICRA_HAL=KOSTU_DUSTU" in satir)
        except Exception as hata:
            gozlenen = "PATLADI:%s" % type(hata).__name__
        olc("B9 kalp satiri ICRA alanlarini tasir", True, gozlenen)


class _Yakala:
    def __init__(self):
        self._parcalar = []

    def write(self, s):
        self._parcalar.append(s)
        return len(s)

    def flush(self):
        pass

    def metin(self):
        return "".join(self._parcalar)


# =========================================================================
# KOL C — karantina olcutu MESAJI da okur, ama yanlis pozitif URETMEZ
# =========================================================================
ERISIM_METNI = ("Your organization has disabled Claude subscription access "
                "for Claude Code · Use an Anthropic API key instead, or "
                "ask your admin to enable access\n")
FATAL_METNI = "API Error: 429 rate limit exceeded\n"


def _c_kos(modul, gecici, rc, metin, motor="claude"):
    cikti = os.path.join(gecici, "cikti.log")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write(metin)
    kar = os.path.join(gecici, "motor-karantina")
    eski = sys.stdout
    sys.stdout = yakala = _Yakala()
    try:
        kod = modul.main(["x", str(rc), cikti, motor, kar,
                          r"(claude|kimi|minimax-m3)"])
    finally:
        sys.stdout = eski
    return kod, yakala.metin(), kar


def kol_c(karantina_yolu=None, yalniz=None, etiket=""):
    def istenir(ad):
        return yalniz is None or ad in yalniz

    try:
        kz = _modul(karantina_yolu or KARANTINA, "kz_k320" + etiket)
    except Exception as hata:
        for ad in ("C1", "C2", "C3", "C4", "C5"):
            if istenir(ad):
                olc("%s (karantina YUKLENEMEDI)" % ad, "YUKLENDI",
                    "HATA:%s" % type(hata).__name__)
        return

    # C1: ARDISIK erisim reddi -> esige varinca YAZILIR
    if istenir("C1"):
        gecici = tempfile.mkdtemp(prefix="k320-c1-")
        try:
            son = ("", 10)
            for _ in range(kz.ERISIM_ARDISIK_ESIGI):
                kod, cikti, kar = _c_kos(kz, gecici, 1, ERISIM_METNI)
                son = (cikti, kod)
            yazildi = os.path.exists(kar) and "claude" in open(kar).read()
            olc("C1 ardisik erisim reddi -> YAZILIR",
                (True, 0), (yazildi, son[1]))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # C2 KONTROL 🔴 YANLIS POZITIF YASAGI: TEK seferlik rc!=0 karantina URETMEZ
    if istenir("C2"):
        gecici = tempfile.mkdtemp(prefix="k320-c2-")
        try:
            kod, cikti, kar = _c_kos(kz, gecici, 1, ERISIM_METNI)
            # 🔴 KONTROL YALNIZ DAVRANISI olcer (yazildi mi?), GEREKCE
            # dizgesini DEGIL. Gerekce ayri vakadir (C6) -- yoksa erisim
            # imzasini olduren mutant KONTROLU de dusurur ve hedef-kol atfi
            # kanitlanamaz ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
            olc("C2 tek seferlik rc!=0 YAZMAZ (kontrol)",
                (False, 10),
                (os.path.exists(kar), kod), kontrol=True)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # C6: esik ALTI hal GEREKCESIYLE bildirilir -- "sessizce atlandi" degil.
    if istenir("C6"):
        gecici = tempfile.mkdtemp(prefix="k320-c6-")
        try:
            kod, cikti, kar = _c_kos(kz, gecici, 1, ERISIM_METNI)
            olc("C6 esik alti GEREKCESIYLE bildirilir",
                (True, True),
                ("-esik-alti" in cikti, "imza=var" in cikti))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # C3 KONTROL: araya giren rc=0 sayaci SIFIRLAR -> esik bir daha bastan
    if istenir("C3"):
        gecici = tempfile.mkdtemp(prefix="k320-c3-")
        try:
            _c_kos(kz, gecici, 1, ERISIM_METNI)
            _c_kos(kz, gecici, 1, ERISIM_METNI)
            _c_kos(kz, gecici, 0, "iyi\n")          # <- iyilesme
            kod, cikti, kar = _c_kos(kz, gecici, 1, ERISIM_METNI)
            olc("C3 rc=0 sayaci sifirlar (kontrol)",
                (False, 10), (os.path.exists(kar), kod), kontrol=True)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # C4 KONTROL: ESKI kol (fatal+kota) DERHAL yazmaya devam eder (regresyon yok)
    if istenir("C4"):
        gecici = tempfile.mkdtemp(prefix="k320-c4-")
        try:
            kod, cikti, kar = _c_kos(kz, gecici, 1, FATAL_METNI)
            olc("C4 fatal+kota kolu DERHAL yazar (kontrol)",
                (True, 0), (os.path.exists(kar), kod), kontrol=True)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # C5 KONTROL: TANINMAYAN hata metni kac kez tekrarlarsa tekrarlasin YAZMAZ
    if istenir("C5"):
        gecici = tempfile.mkdtemp(prefix="k320-c5-")
        try:
            kod = 0
            for _ in range(kz.ERISIM_ARDISIK_ESIGI + 2):
                kod, cikti, kar = _c_kos(kz, gecici, 1, "bilinmeyen bir hata\n")
            olc("C5 taninmayan metin ASLA yazmaz (kontrol)",
                (False, 10), (os.path.exists(kar), kod), kontrol=True)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)


# =========================================================================
# MUTANTLAR — hedef-kol atfi
# =========================================================================
MUTANTLAR = [
    # (ad, dosya, eski, yeni, hedef_dusen, kontrol_yesil, kol)
    ("M-A1-kosmayan-kapi-sayi-basar", SH,
     "NOBET_RC=KOSMADI", "NOBET_RC=0",
     ["A2"], ["A3", "A4"], "A"),
    ("M-A2-rc-hukumden-turemez", SH,
     "  HUKUM=$TETIK_SINIFI\n  SON_RC=1",
     "  HUKUM=$TETIK_SINIFI\n  SON_RC=0",
     ["A2"], ["A3", "A4"], "A"),
    ("M-B1-ucuncu-kova-olur", KAPI,
     "        if dondurma_isirdi:\n            rc, hukum = 0, \"DAGITIM_DONDURULDU\"",
     "        if False:\n            rc, hukum = 0, \"DAGITIM_DONDURULDU\"",
     ["B1"], ["B2", "B3"], "B"),
    ("M-B2-supurme-kapisi-korlesir", KAPI,
     '"ONARIM_ILERLIYOR",\n                      "DAGITIM_DONDURULDU"}',
     '"ONARIM_ILERLIYOR"}',
     ["B3"], ["B1", "B2"], "B"),
    ("M-B3-tur-kapat-temiz-der", KAPI,
     '"TEMIZ" if sonuc["rc"] == 0 else "DAGITIM_BACAGI_DUSTU"',
     '"TEMIZ"',
     ["B5"], ["B4"], "B"),
    ("M-B4-sebep-olculemediye-doner", GOZCU,
     '        return "HUKUM=%s rc=%s" % (eslesme[-1], icra_rc)',
     '        return "OLCULEMEDI"',
     ["B6"], ["B7", "B8"], "B"),
    ("M-C1-esik-1-yanlis-pozitif", KARANTINA,
     "ERISIM_ARDISIK_ESIGI = 3", "ERISIM_ARDISIK_ESIGI = 1",
     ["C2"], ["C1", "C4"], "C"),
    ("M-C2-erisim-imzasi-korlesir", KARANTINA,
     "    if ERISIM_RE.search(metin):", "    if False:",
     ["C1", "C6"], ["C2", "C4", "C5"], "C"),
]


def mutant_kos(mutant):
    ad, dosya, eski, yeni, hedef, kontrol, kol = mutant
    gecici = tempfile.mkdtemp(prefix="k320-m-")
    try:
        try:
            with open(dosya, encoding="utf-8") as f:
                metin = f.read()
        except OSError as e:
            return (False, False, "DOSYA_YOK:%s" % type(e).__name__)
        n = metin.count(eski)
        if n != 1:
            # 🔴 Capa tek degilse mutant OLCMEZ; sessizce "oldu" sayilamaz.
            return (False, False, "CAPA_SAYISI=%d" % n)
        kopya = os.path.join(gecici, os.path.basename(dosya))
        with open(kopya, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni, 1))
        if dosya == SH:
            os.chmod(kopya, 0o755)

        onceki = dict(_SAYAC)
        dusen_once = list(_DUSENLER)
        etiket = "_" + ad.replace("-", "_")
        try:
            if kol == "A":
                kol_a(sh_yolu=kopya, yalniz=set(hedef + kontrol))
            elif kol == "B":
                kol_b(kapi_yolu=kopya if dosya == KAPI else None,
                      gozcu_yolu=kopya if dosya == GOZCU else None,
                      yalniz=set(hedef + kontrol), etiket=etiket)
            else:
                kol_c(karantina_yolu=kopya, yalniz=set(hedef + kontrol),
                      etiket=etiket)
        except Exception:
            traceback.print_exc(file=sys.stderr)
        yeni_dusenler = [d for d in _DUSENLER[len(dusen_once):]]

        # Sayaclari geri sar: mutant turu ANA karneye yazilmaz.
        _SAYAC.clear()
        _SAYAC.update(onceki)
        del _DUSENLER[len(dusen_once):]

        def _var(kume):
            return [h for h in kume
                    if any(d.split()[0] == h for d in yeni_dusenler)]

        hedef_dusen = _var(hedef)
        kontrol_dusen = _var(kontrol)
        oldu = len(hedef_dusen) == len(hedef)
        # 🔴 HEDEF-KOL ATFI: mutant hedefi dusurmeli VE kontrolu dusurmemeli.
        atif = oldu and not kontrol_dusen
        not_ = "hedef_dusen=%s/%s kontrol_dusen=%s" % (
            len(hedef_dusen), len(hedef), kontrol_dusen or "-")
        return (oldu, atif, not_)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    yalniz_vaka = "--yalniz-vaka" in argv

    print("=== K320 KABUL — KURULU KOPYA: %s ===" % CRON)
    kol_a()
    kol_b()
    kol_c()

    olen = atifli = 0
    yama_tutmadi = 0
    if not yalniz_vaka:
        print("--- MUTANTLAR (bu satirlar NORMAL teshis ciktisidir) ---")
        for mutant in MUTANTLAR:
            oldu, atif, not_ = mutant_kos(mutant)
            olen += int(oldu)
            atifli += int(atif)
            if not oldu or not atif:
                yama_tutmadi += 1
            print("MUTANT %-34s %s ATIF=%s %s" % (
                mutant[0], "OLDU" if oldu else "YASADI",
                "EVET" if atif else "HAYIR", not_))

    print("KABUL VAKA=%d/%d DUSEN=%d MUTANT=%d/%d YAMA_TUTMADI=%d "
          "HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d"
          % (_SAYAC["gecen"], _SAYAC["vaka"], len(_DUSENLER),
             olen, 0 if yalniz_vaka else len(MUTANTLAR), yama_tutmadi,
             atifli, 0 if yalniz_vaka else len(MUTANTLAR),
             _SAYAC["kontrol_gecen"], _SAYAC["kontrol"]))
    if _DUSENLER:
        print("DUSEN_VAKALAR=%s" % ",".join(_DUSENLER))
    return 0 if (not _DUSENLER and yama_tutmadi == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
