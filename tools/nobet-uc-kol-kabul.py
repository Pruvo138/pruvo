#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K320 KABUL BATARYASI — nobet hatti UC KOL (A/B/C).

🔴 OLCUM VARSAYILAN OLARAK KURULU KOPYADAN YAPILIR
([[emir-canliligi-kurulu-kopyadan-olculur]]): bayraksiz kosumda her vaka
`~/.claude/cron/` altindaki CANLI dosyayi yukler. Repodaki yama kaynagini
olcmek YESIL yakar ama emrin canliligini KANITLAMAZ.

🔴 `--kok <yol>` (27 Agu 2026, mimar hukmu): olculen AGAC secilebilir.
Once bu bes ad ice aktarma aninda cakiliydi — batarya HANGI agaci olcerse
olcsun `~/.claude/cron`u tarif eden bir yesil basiyordu, ve o duzleme
baska cipler de yazabiliyordu. Bayrak verilmezse davranis AYNEN eskisidir.
Ciktinin basindaki `OLCULEN KOK:` + `YUZEY` satirlari hangi dosyanin
olculdugunu ADIYLA basar; iki kosumun farki bu satirlardan okunur.

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

VARSAYILAN_KOK = os.environ.get("PRUVO_NOBET_KOK") or os.path.join(
    os.path.expanduser("~"), ".claude", "cron")

# 🔴 OLCULEN YUZEY BAYRAKLA SECILIR (27 Agu 2026, mimar hukmu —
# KraL-KarantinaHukmu-27Agu). ONCE: bes ad ICE AKTARMA aninda BIR KEZ
# baglaniyordu; batarya NE olcerse olcsun yalnizca `~/.claude/cron`u tarif
# eden bir YESIL basiyordu — ve o duzleme baska cipler de yazabiliyor.
# SIMDI `--kok <yol>` hedefi degistirir. VARSAYILAN DAVRANIS AYNIDIR:
# bayrak verilmezse yine kurulu kopya olculur.
CRON = VARSAYILAN_KOK
SH = KAPI = GOZCU = KARANTINA = None


def kok_ayarla(kok):
    """Olculecek KOKU ve ondan tureyen dort dosya adini YENIDEN baglar.

    🔴 MUTANT TABLOSU YOL DEGIL ANAHTAR TUTAR (`_mutant_yolu`): aksi halde
    tablo ice aktarma anindaki yola CAKILI kalir ve `--kok` verildiginde
    mutantlar YANLIS AGACTA atesler ([[spec-mutlak-yol-yanlis-agaci-olcer]]).
    """
    global CRON, SH, KAPI, GOZCU, KARANTINA
    CRON = kok
    SH = os.path.join(CRON, "ci-nobeti.sh")
    KAPI = os.path.join(CRON, "nobet-kapi.py")
    GOZCU = os.path.join(CRON, "gozcu.py")
    KARANTINA = os.path.join(CRON, "isci-karantina-karar.py")


kok_ayarla(VARSAYILAN_KOK)


def _mutant_yolu(anahtar):
    """MUTANTLAR tablosundaki ANAHTARI kosum anindaki gercek yola cevirir."""
    return {"SH": SH, "KAPI": KAPI, "GOZCU": GOZCU,
            "KARANTINA": KARANTINA}[anahtar]

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

# 🔴 TETIK STUB'I ARTIK `sebep=` JETONU DA BASAR (A4, 27 Agu 2026).
# Gerekce: gercek `nobet-tetik.py` her kararda `TUR ACIL(MADI|IYOR) sebep=<kol>`
# satirini basar ve `ci-nobeti.sh` hukum adini ARTIK O SATIRDAN okur. Jetonsuz
# stub, olctugu seyi taklit etmiyordu ([[prob-gercek-isi-taklit-etmeli]]);
# jetonsuz hali A8'de AYRI bir vaka olarak (fail-closed kolu) olculur.
_STUB_TETIK = ("#!/usr/bin/env python3\nimport sys\nprint('STUB TETIK')\n"
               "%ssys.exit(%d)\n")


def _tetik_govdesi(sebep, acilir=False):
    """sebep None -> jeton BASILMAZ (fail-closed kolunu olcmek icin)."""
    if sebep is None:
        return ""
    if acilir:
        return ("print('TUR ACILIYOR sebep=%s anahtar=- bayraklar=--tur "
                "KIRMIZI=0')\n" % sebep)
    return "print('TUR ACILMADI sebep=%s KIRMIZI=1')\n" % sebep


def _a_kos(tetik_rc, kapi_rc, sh_yolu=None, tetik_sebebi=None):
    """ci-nobeti.sh'i STUB tetik/kapi ile kosar; (rc, log_metni) doner.

    `tetik_sebebi=None` -> stub `sebep=` jetonu BASMAZ.
    """
    gecici = tempfile.mkdtemp(prefix="k320-a-")
    try:
        tetik = os.path.join(gecici, "tetik.py")
        kapi = os.path.join(gecici, "kapi.py")
        log = os.path.join(gecici, "nobet.log")
        with open(tetik, "w") as f:
            f.write(_STUB_TETIK % (
                _tetik_govdesi(tetik_sebebi, acilir=(tetik_rc in (0, 1))),
                tetik_rc))
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
        rc, log = _a_kos(11, 0, sh_yolu, tetik_sebebi="SEVIYE_KIRMIZI_2")
        olc("A2 seviye kirmizi -> nobet_rc KOSMADI",
            ("SEVIYE_KIRMIZI_2", 1, "KOSMADI"),
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
            rc, log = _a_kos(t, k, sh_yolu, tetik_sebebi="SEVIYE_KIRMIZI_2")
            if (_a_hukum(log) == "TEMIZ") != (rc == 0):
                ihlal.append((t, k, _a_hukum(log), rc))
        olc("A6 degismezlik TEMIZ<=>rc0", [], ihlal)

    # 🔴 A7 — VAKANIN KENDISI (27 Agu 2026, KraL-NobetTuru-27Agu).
    # AYNI `tetik_rc=11`i ureten IKI FARKLI kol, IKI FARKLI `HUKUM` adi
    # basmalidir. Olculen ariza: 13:07Z-20:07Z arasi yedi rc=11 turunun
    # besi `ESKALASYON_ACIK`, biri `GOZCU_URETMEDI_OLCULEMEDI`, biri
    # `SEVIYE_KIRMIZI_2` idi; UCU DE `HUKUM=SEVIYE_KIRMIZI` basiyordu.
    # Ad, kolu DEGIL kabuktaki sabiti soyluyordu -> okuyan yanlis alani
    # dogruladi ve "iki duzlem birbirini yalanliyor" hukmu verdi.
    # Bu vaka BIR AD BEKLEMEZ, IKI ADIN FARKLI OLMASINI bekler: sabite
    # geri donen her mutant burada olur.
    if istenir("A7"):
        rc1, log1 = _a_kos(11, 0, sh_yolu, tetik_sebebi="ESKALASYON_ACIK")
        rc2, log2 = _a_kos(11, 0, sh_yolu, tetik_sebebi="GOZCU_URETMEDI_OLCULEMEDI")
        olc("A7 ayni rc=11, kol adlari AYRISIR",
            ("ESKALASYON_ACIK", "GOZCU_URETMEDI_OLCULEMEDI", 1, 1),
            (_a_hukum(log1), _a_hukum(log2), rc1, rc2))

    # A8 FAIL-CLOSED: tetik `sebep=` jetonu BASMAZSA ad SESSIZCE eski sabite
    # DUSMEZ; `TETIK_SEBEBI_OKUNAMADI` basilir ve tur YINE KIRMIZI kapanir.
    # "Adini okuyamadim" != "SEVIYE_KIRMIZI" ve kesinlikle != "TEMIZ".
    if istenir("A8"):
        rc, log = _a_kos(11, 0, sh_yolu, tetik_sebebi=None)
        olc("A8 sebepsiz rc=11 -> fail-closed ad",
            ("TETIK_SEBEBI_OKUNAMADI", 1, "KOSMADI"),
            (_a_hukum(log), rc, _a_alan(log, "nobet_rc")))

    # A9 KONTROL: tetik ciktisi LOGA AYNEN duser (yakalama, logu SUSTURMADI).
    if istenir("A9"):
        _rc, log = _a_kos(11, 0, sh_yolu, tetik_sebebi="ESKALASYON_ACIK")
        olc("A9 tetik ciktisi loga duser",
            (True, True),
            ("STUB TETIK" in log,
             "TUR ACILMADI sebep=ESKALASYON_ACIK" in log), kontrol=True)


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
        for ad in ("C1", "C2", "C3", "C4", "C5a", "C5b", "C6"):
            if istenir(ad):
                olc("%s (karantina YUKLENEMEDI)" % ad, "YUKLENDI",
                    "HATA:%s" % type(hata).__name__)
        return

    # C1: ARDISIK erisim reddi -> esige varinca YAZILIR, ve KAYDI YAZAN KOL
    #     ADIYLA gecer (`erisim-reddi-ardisik<n>`).
    #
    # 🔴 27 Agu 2026 — OLCULEN GOLGE ([[yeni-kol-onceki-kolun-golgesinde-olur]]).
    # Bu vaka once YALNIZ davranisi olcuyordu (yazildi mi + rc). Kol D
    # (imza taninmasa da ardisik esik yazar) eklendikten sonra o olcum
    # AYIRT EDEMEZ oldu: `M-C2-erisim-imzasi-korlesir` mutanti ERISIM_RE'yi
    # koru ettigi halde ayni dizi Kol D uzerinden YINE yaziliyor, C1 YESIL
    # kaliyor ve mutant YASIYORDU (olculdu: hedef_dusen=1/2, MUTANT=9/10).
    # Iki kol AYNI davranisi uretiyor; ayirt eden tek sey SEBEP ADIDIR --
    # ki Kol C'nin butun degeri de zaten "hangi kol yazdi"yi ADIYLA
    # soylemesidir. O yuzden iddia sebebi de olcer (C1 KONTROL DEGILDIR;
    # kontrol vakalari gerekce dizgesi olcmez -- bkz. C2/C5a notu).
    if istenir("C1"):
        gecici = tempfile.mkdtemp(prefix="k320-c1-")
        try:
            son = ("", 10)
            for _ in range(kz.ERISIM_ARDISIK_ESIGI):
                kod, cikti, kar = _c_kos(kz, gecici, 1, ERISIM_METNI)
                son = (cikti, kod)
            yazildi = os.path.exists(kar) and "claude" in open(kar).read()
            olc("C1 ardisik erisim reddi -> YAZILIR (sebep ADIYLA)",
                (True, 0, True),
                (yazildi, son[1], "erisim-reddi-ardisik" in son[0]))
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

    # ======================================================================
    # C5a / C5b — TANINMAYAN IMZA: IKI YONLU KURAL
    # ======================================================================
    # 🔴 27 Agu 2026 MIMAR HUKMU (KraL-KarantinaHukmu-27Agu). Eski C5 sunu
    # soyluyordu: "taninmayan metin kac kez tekrarlarsa tekrarlasin ASLA
    # yazmaz". Bu kural, ayni gun OLCULEN korlugu KURAL HALINE getiriyordu:
    # 13 ardisik `motor=claude rc=1` kosumunun HEPSINDE
    # `sebep=fatal-satir-yok` basildi ve TEK karantina kaydi yazilmadi --
    # cunku hata metni "taninan" listede degildi. Hat olu motoru saatlerce
    # yeniden denedi.
    #
    # Kural IKI YONLUDUR ve iki AYRI vaka ile olculur:
    #   C5a (KONTROL) TEK seferlik taninmayan dusus -> YAZMAZ  (yanlis pozitif yasagi)
    #   C5b           ESIK kez ARDISIK taninmayan dusus -> YAZAR, sebep ADIYLA
    #
    # 🔴 ESIK SAYISI BURAYA KOPYALANMAZ: `kz.GENEL_ARDISIK_ESIGI` MODULDEN
    # okunur. Sayiyi vakaya yazmak, esigi degistiren bir onarimin kabulu
    # SESSIZCE yesil birakmasi demektir ([[ad-iki-rolde-mutanti-golgeler]]).
    TANINMAYAN = "bilinmeyen bir hata\n"

    # C5a KONTROL: tek dusus YAZMAZ. 🔴 Yalnizca DAVRANIS olculur (yazildi mi,
    # rc ne), GEREKCE dizgesi DEGIL -- gerekceyi de olcen bir kontrol, hedef
    # kolu olduren mutantlar tarafindan da dusurulur ve hedef-kol atfi
    # kanitlanamaz ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
    if istenir("C5a"):
        gecici = tempfile.mkdtemp(prefix="k320-c5a-")
        try:
            kod, cikti, kar = _c_kos(kz, gecici, 1, TANINMAYAN)
            olc("C5a tek taninmayan dusus YAZMAZ (kontrol)",
                (False, 10), (os.path.exists(kar), kod), kontrol=True)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # C5b: ESIK kez ARDISIK taninmayan dusus YAZAR ve sebep ADIYLA gecer.
    if istenir("C5b"):
        gecici = tempfile.mkdtemp(prefix="k320-c5b-")
        try:
            son = ("", 10)
            for _ in range(kz.GENEL_ARDISIK_ESIGI):
                kod, cikti, kar = _c_kos(kz, gecici, 1, TANINMAYAN)
                son = (cikti, kod)
            yazildi = os.path.exists(kar) and "claude" in open(kar).read()
            olc("C5b esik kez ardisik taninmayan -> YAZAR",
                (True, 0, True),
                (yazildi, son[1], "ardisik-basarisiz-imzasiz" in son[0]))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)


# =========================================================================
# MUTANTLAR — hedef-kol atfi
# =========================================================================
MUTANTLAR = [
    # (ad, DOSYA_ANAHTARI, eski, yeni, hedef_dusen, kontrol_yesil, kol)
    # 🔴 ikinci sutun bir YOL DEGIL ANAHTARDIR; `--kok` ile degisen gercek
    # yola `_mutant_yolu()` kosum aninda cevirir.
    ("M-A1-kosmayan-kapi-sayi-basar", "SH",
     "NOBET_RC=KOSMADI", "NOBET_RC=0",
     ["A2"], ["A3", "A4"], "A"),
    ("M-A2-rc-hukumden-turemez", "SH",
     "  HUKUM=$TETIK_SINIFI\n  SON_RC=1",
     "  HUKUM=$TETIK_SINIFI\n  SON_RC=0",
     ["A2"], ["A3", "A4"], "A"),
    # --- KOL A4 (ad kolu) — IKI YON, IKI MUTANT --------------------------
    # (i) SABIT ADA GERI DONUS: rc=11'in TUM kollari yine tek adla basilir.
    #     A7 (iki kol AYRISIR) ve A8 (fail-closed ad) KIRMIZI olmali;
    #     A9 (cikti loga duser) ve A3/A4 YESIL kalmali -- mutant ADI bozdu,
    #     logu ya da rc turemesini DEGIL.
    ("M-A3-hukum-adi-sabite-doner", "SH",
     "  11) KIRMIZI=1; TETIK_SINIFI=${TETIK_SEBEBI:-TETIK_SEBEBI_OKUNAMADI} ;;",
     "  11) KIRMIZI=1; TETIK_SINIFI=SEVIYE_KIRMIZI ;;",
     ["A2", "A7", "A8"], ["A3", "A4", "A9"], "A"),
    # (ii) SEBEP AYIKLAMA KOLUNU oldurur: jeton BASILSA da okunmaz.
    #     A2/A7 KIRMIZI olmali; A8 (jetonsuz vaka) YESIL KALMALI -- cunku
    #     fail-closed ad zaten onun BEKLEDIGI addir. A8'in yesil kalmasi
    #     mutantin "her seyi kirmadigini" kanitlar.
    ("M-A4-sebep-ayiklama-korlesir", "SH",
     "awk '/^TUR ACIL/ {",
     "awk '/^ASLA_ESLESMEYEN_DESEN/ {",
     ["A2", "A7"], ["A8", "A3", "A9"], "A"),
    ("M-B1-ucuncu-kova-olur", "KAPI",
     "        if dondurma_isirdi:\n            rc, hukum = 0, \"DAGITIM_DONDURULDU\"",
     "        if False:\n            rc, hukum = 0, \"DAGITIM_DONDURULDU\"",
     ["B1"], ["B2", "B3"], "B"),
    ("M-B2-supurme-kapisi-korlesir", "KAPI",
     '"ONARIM_ILERLIYOR",\n                      "DAGITIM_DONDURULDU"}',
     '"ONARIM_ILERLIYOR"}',
     ["B3"], ["B1", "B2"], "B"),
    ("M-B3-tur-kapat-temiz-der", "KAPI",
     '"TEMIZ" if sonuc["rc"] == 0 else "DAGITIM_BACAGI_DUSTU"',
     '"TEMIZ"',
     ["B5"], ["B4"], "B"),
    ("M-B4-sebep-olculemediye-doner", "GOZCU",
     '        return "HUKUM=%s rc=%s" % (eslesme[-1], icra_rc)',
     '        return "OLCULEMEDI"',
     ["B6"], ["B7", "B8"], "B"),
    ("M-C1-esik-1-yanlis-pozitif", "KARANTINA",
     "ERISIM_ARDISIK_ESIGI = 3", "ERISIM_ARDISIK_ESIGI = 1",
     ["C2"], ["C1", "C4"], "C"),
    ("M-C2-erisim-imzasi-korlesir", "KARANTINA",
     "    if ERISIM_RE.search(metin):", "    if False:",
     ["C1", "C6"], ["C2", "C4", "C5a"], "C"),
    # --- KOL D (imza taninmasa da ARDISIK esik yazar) — IKI YON, IKI MUTANT ---
    # (i) ARDISIK ESIK KOLUNU oldurur -> "esikte yazar" yonu KIRMIZI olmali,
    #     "tek dususte yazmaz" yonu (C5a) ve bilinen imza kollari YESIL kalmali.
    ("M-D1-ardisik-esik-kolu-olur", "KARANTINA",
     "        elif rc != 0 and _ardisik >= GENEL_ARDISIK_ESIGI:",
     "        elif False:",
     ["C5b"], ["C5a", "C1", "C4"], "C"),
    # (ii) TEK-SEFERLIK KORUMASINI oldurur (esik 1'e iner) -> "tek dususte
    #     yazmaz" yonu (C5a) KIRMIZI olmali, "esikte yazar" yonu (C5b) YESIL
    #     kalmali. C2 de yesil kalir: erisim kolu KENDI esigini okur.
    ("M-D2-tek-seferlik-korumasi-olur", "KARANTINA",
     "GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI",
     "GENEL_ARDISIK_ESIGI = 1",
     ["C5a"], ["C5b", "C2", "C4"], "C"),
]


def mutant_kos(mutant):
    ad, anahtar, eski, yeni, hedef, kontrol, kol = mutant
    dosya = _mutant_yolu(anahtar)     # `--kok` KOSUM ANINDA cozulur
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
        if anahtar == "SH":
            os.chmod(kopya, 0o755)

        onceki = dict(_SAYAC)
        dusen_once = list(_DUSENLER)
        etiket = "_" + ad.replace("-", "_")
        try:
            if kol == "A":
                kol_a(sh_yolu=kopya, yalniz=set(hedef + kontrol))
            elif kol == "B":
                kol_b(kapi_yolu=kopya if anahtar == "KAPI" else None,
                      gozcu_yolu=kopya if anahtar == "GOZCU" else None,
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

    # --kok <yol> | --kok=<yol> : olculecek AGACI sec. Yoksa varsayilan
    # (PRUVO_NOBET_KOK ya da ~/.claude/cron) — BUGUNKU DAVRANIS DEGISMEZ.
    kok = None
    for i, parca in enumerate(argv):
        if parca == "--kok" and i + 1 < len(argv):
            kok = argv[i + 1]
        elif parca.startswith("--kok="):
            kok = parca.split("=", 1)[1]
    if kok:
        kok = os.path.abspath(os.path.expanduser(kok))
        if not os.path.isdir(kok):
            sys.stderr.write("HATA: --kok dizini YOK: %s\n" % kok)
            return 2
        kok_ayarla(kok)

    print("=== K320 KABUL — OLCULEN KOK: %s (%s) ===" % (
        CRON, "BAYRAKLA" if kok else "VARSAYILAN/kurulu"))
    for ad, yol in (("ci-nobeti.sh", SH), ("nobet-kapi.py", KAPI),
                    ("gozcu.py", GOZCU), ("isci-karantina-karar.py", KARANTINA)):
        print("  YUZEY %-24s %s var=%d" % (ad, yol, int(os.path.exists(yol))))
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
