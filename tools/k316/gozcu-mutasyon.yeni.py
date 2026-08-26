#!/usr/bin/env python3
"""GOZCU CURUTUCUSU — 16 mutant; capalar KAYNAKTAN TURETILIR (K316, 27 Agu 2026).

K160 dilim-1b (sahte yesil) onarimi AYNEN durur: M11/M12/M14/M15/M16 mutantli
`kilit` modulunu BELLEK ICINDE derleyip `sys.modules`e ENJEKTE eder; `gozcu`nun
o module baglandigi KABLO_KANITI ile olculur.

=== K316 (27 Agu 2026) — CAPA ELLE YAZILMAZ ===================================
🔴 OLCULEN KUSUR: 16 mutantin capasi `gozcu.py`/`kilit.py` kaynagindan ELLE
KOPYALANMIS literal dizelerdi. 26 Agu'da K311 (B6 `icra_hal` gocu) + bekci
turlari `gozcu.py`yi yeniden yazinca M10'un capasi
(`if icra_rc is not None and icra_rc != 0:`) kaynakta SIFIR kez gecer oldu:
o eksen 26 Agu'dan beri HIC OLCULMUYORDU ve batarya `MUTANT=15/16` diyerek
kapsami SESSIZCE daraltiyordu.

Ayni sinif bu depoda daha once olculdu ve altyapisi YAZILDI ama VAKALARA
INMEDI ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]): `tools/mutasyon_kopya.py`
`mutant_metni(mod, metin, [(kapsam, desen, donusum), ...])` ile capayi hedef
yuklem'in KENDI kaynagindan turetir. Bu surucu artik O ALTYAPIYI KULLANIR —
ikinci bir turetici YAZILMADI.

Capa artik uc parcadir:
  · kapsam  = hedef YUKLEM adi (fonksiyon) · "__modul__" (modul govdesi) · ya da
              ("<yuklem>", bas_deseni, son_deseni) = yuklemin KENDI kaynagindan
              turetilen ALT BLOK. Alt blok, ayni satirin farkli girintiyle
              tekrarlandigi yerler icin gerekir (bkz. M11: `al` icinde IKI
              `fd = os.open(...)` var ve 8 bosluklu olan 12 bosluklunun
              ALT DIZESIDIR — yani "satir tekil mi" testi tek basina yetmez).
              Yuklem adi degisirse capa CAKAR ve eksen ADIYLA raporlanir.
  · desen   = kapsam ICINDE tek satira uyan dar regex (kod metni DEGIL, NISAN).
  · donusum = o satiri mutanta ceviren yuklem; ETKISIZ kalirsa FAIL-LOUD.

🔴 SON SATIR NORMALIZASYONU: `inspect.getsource` bir yuklemin kaynagini DAIMA
`\\n` ile bitirir; dosya son satirinda newline TASIMIYORSA (kilit.py boyle) o
dosyanin SON yuklemi "kaynakta 0 kez geciyor" diye capa hatasi verir — ve bu
sessiz bir KAPSAM KAYBIDIR (M12 boyle dustu). Kaynak metin bellekte `\\n` ile
kapatilir; diske TEK BAYT yazilmaz.

=== K316 — KAPSAM TABANDAN DUSMEZ ============================================
🔴 Eski satir `toplam_mutant = len(MUTANTLAR) - sayac["YAMA_TUTMADI"]` KAPSAMI
SESSIZCE DARALTAN koldu: bir eksen olculemez hale gelince payda kuculuyor ve
batarya `15/15` gibi "tam" bir oran basabiliyordu. Artik payda DAIMA
`len(MUTANTLAR)`; pay OLEN mutant sayisidir. Olculemeyen eksenler ayri ve ADLI
bir kovaya (`CAPA_BAYAT_EKSENLER`) dusurulur — "COKME" ile ayni kovaya
KONMAZ ([[capa-turetme-altyapisi-kullanilmadan-kaldi]] 3. kol).

rc≠0 emniyeti (IDDIA == len(MUTANTLAR) ve diger kovalar 0) GEVSETILMEDI.

Beklenen: MUTANT=16/16 IDDIA=16 ISTASYON=0 KABLO_KOPUK=0 YAMA_TUTMADI=0
"""

import os
import re
import shutil
import sys
import tempfile
import types

KOK = os.path.dirname(os.path.abspath(__file__))
GOZCU_YOLU = os.path.join(KOK, "gozcu.py")
KILIT_YOLU = os.path.join(KOK, "kilit.py")           # K160 dilim-1 TEK KAYNAK
TEST_YOLU = os.path.join(KOK, "gozcu-test.py")

# TEK KAYNAK: capa turetme altyapisi ~/dev/pruvo/tools/mutasyon_kopya.py'dedir.
# Ikinci bir turetici YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Import edilemezse
# FAIL-LOUD: capasiz batarya "yesil" DEMEZ.
EV_KOKU = "/Users/okan/dev/pruvo"
_arac_yolu = os.path.join(EV_KOKU, "tools")
if _arac_yolu not in sys.path:
    sys.path.insert(0, _arac_yolu)
import mutasyon_kopya as MK                                        # noqa: E402

MODUL_KAPSAMI = "__modul__"


def _yerine(eski, yeni):
    """Satir icinde `eski` -> `yeni`. Etkisiz kalirsa mutant_metni FAIL-LOUD verir."""
    def donusum(satir):
        return satir.replace(eski, yeni)
    return donusum


def _one_ekle(eski, yeni):
    """Satirin `eski` ile baslayan parcasini `yeni` ile degistirir (kol devre disi)."""
    return _yerine(eski, yeni)


def _m7(satir):
    """`return NK.kilit_karari(...)` -> BAYAT hukmunu DOLU'ya ceviren sarmalayici."""
    return (satir.replace("return NK.kilit_karari(", "_h = NK.kilit_karari(")
            + '; return "DOLU" if _h == "BAYAT" else _h')


# (ad, hedef_dosya, kapsam, desen, donusum)
# 🔴 `desen` KOD METNI DEGIL NISANDIR: kapsamin kendi kaynaginda TEK satira
# uymak zorundadir (uymazsa/birden fazlaysa mutant CAPA_BAYAT sayilir ve ADIYLA
# raporlanir — sessizce dusmez).
MUTANTLAR = [
    # --- GOZCU hedefli -------------------------------------------------
    ("M1 cancelled kirmizi sayilir",
     GOZCU_YOLU, "kirmizi_kosumlar", r'!= "failure"',
     _yerine('!= "failure"', '== "success"')),
    ("M2 ci_olculdu kontrolu kalkar (fail-open)",
     GOZCU_YOLU, "tetik_karari", r"not ci_olculdu or not defter_olculdu",
     _yerine("not ci_olculdu or not defter_olculdu", "not defter_olculdu")),
    ("M3 OLCULEMEDI rc 2 -> 0",
     GOZCU_YOLU, MODUL_KAPSAMI, r"^OLCULEMEDI_RC\s*=",
     _yerine("= 2", "= 0")),
    ("M4 deneme tavani -> 99 (isci firtinasi)",
     GOZCU_YOLU, "yeni_kirmizilar", r"deneme >= ESKALASYON_ESIGI",
     _yerine("ESKALASYON_ESIGI", "99")),
    ("M5 KAT_MIMAR suzgeci kalkar",
     GOZCU_YOLU, "dagitilabilir_kalemler", r"NK\.kat_sec\(k\) not in",
     _yerine("(NK.KAT_MIMAR, NK.KAT_OKAN)", "(NK.KAT_OKAN,)")),
    ("M6 ESKALASYON esigi 3 -> 4",
     GOZCU_YOLU, MODUL_KAPSAMI, r"^ESKALASYON_ESIGI\s*=",
     _yerine("= 3", "= 4")),
    ("M7 olu PID'de DOLU (ikinci isci engellenmez)",
     GOZCU_YOLU, "kilit_karari", r"return NK\.kilit_karari\(", _m7),
    ("M8 epok yokken kalp TAZE sayilir (fail-open)",
     GOZCU_YOLU, "kalp_bayat_mi", r"^\s+return True\s*$",
     _yerine("return True", "return False")),
    ("M9 artik onek kontrolu kalkar (komsu dosya silinir)",
     GOZCU_YOLU, "tur_artigi_temizle", r"not ad\.startswith\(ARTIK_ONEKLERI\)",
     _yerine("not ad.startswith(ARTIK_ONEKLERI)", "False")),
    # 🔴 M10 K316'da YENIDEN NISANLANDI: eksen AYNI ("kosan turun rc'si gozcuye
    # TASINIR"), ama B6 gocunden (K311) sonra o kol `icra_rc` degil `icra_hal`
    # uzerinden okunuyor. Capa artik `tur` yukleminin KENDI kaynagindan turer.
    ("M10 kosan turun rc'si gozcuye tasinmaz",
     GOZCU_YOLU, "tur", r'icra_hal == "KOSTU_DUSTU"',
     _one_ekle("if icra_hal ==", "if False and icra_hal ==")),
    ("M13 esik yeniden sabit 3",
     GOZCU_YOLU, "yeni_kirmizilar", r"deneme >= ESKALASYON_ESIGI",
     _yerine("ESKALASYON_ESIGI", "3")),

    # --- KILIT hedefli --------------------------------------------------
    # 🔴 ALT BLOK: `al` icinde IKI `fd = os.open(...)` satiri var; 8 bosluklu
    # olan 12 bosluklunun ALT DIZESI oldugu icin "tekil satir" testi 2 sayar.
    # Kapsam, yuklemin KENDI kaynagindan turetilen ILK-OPEN blogudur.
    ("M11 birinci os.open O_EXCL -> O_TRUNC (CANLI rakip calinir)",
     KILIT_YOLU, ("al", r"^ {4}devralindi = False", r"^ {4}except FileExistsError:"),
     r"fd = os\.open\(", _yerine("os.O_EXCL", "os.O_TRUNC")),
    ("M12 kilit birakmada sahiplik denetimi kalkar",
     KILIT_YOLU, "birak", r'PID=%d.*not in icerik',
     _yerine('if ("PID=%d" % os.getpid()) not in icerik:', "if False:")),
    ("M14 devralma kolunda unlink kalkar (ARTIK devralinmaz)",
     KILIT_YOLU, "al", r"os\.unlink\(yol\)",
     _yerine("os.unlink(yol)", "pass")),
    ("M15 kor devralma: DOLU denetimi kalkar (CANLI calinir)",
     KILIT_YOLU, "al", r"karar\(taze,",
     _yerine('karar(taze, simdi, pid_canli_mi) == "DOLU"', "False")),
    ("M16 bayat-pid kolu kalkar (olu PID DOLU sayilir)",
     KILIT_YOLU, "karar", r"pid_canli_mi\(pid\)",
     _one_ekle("if pid and not", "if False and pid and not")),
]


def _test_modulu(test_yolu=None):
    import importlib.util
    spec = importlib.util.spec_from_file_location("gozcu_test", test_yolu or TEST_YOLU)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _bellekte_kur(kaynak, ad, kaynak_yolu):
    modul = types.ModuleType(ad)
    modul.__file__ = kaynak_yolu
    exec(compile(kaynak, kaynak_yolu, "exec"), modul.__dict__)
    return modul


def _pycache_temizle(kok=None):
    yol = os.path.join(kok or KOK, "__pycache__")
    if os.path.isdir(yol):
        shutil.rmtree(yol, ignore_errors=True)


def _ilk_hata_testi(test_sonuc):
    """Ilk basarisiz testin AD'ini doner (self.hatalar satirinin basindaki)."""
    if not test_sonuc.hatalar:
        return "?"
    ilk = test_sonuc.hatalar[0]
    if ":" in ilk:
        return ilk.split(":", 1)[0]
    return ilk


def _alt_blok(blok, ilk_desen, son_desen):
    """Yuklemin KENDI kaynagindan ALT BLOK turet: `ilk_desen`e uyan TEK satirdan
    `son_desen`e uyan ILK satira kadar (ikisi de DAHIL). Elle yazilmis kod YOK."""
    satirlar = blok.splitlines(keepends=True)
    bas = [i for i, s in enumerate(satirlar) if re.search(ilk_desen, s)]
    if len(bas) != 1:
        raise MK.CapaHatasi("alt blok BASI %d satira uydu (1 olmali): %r"
                            % (len(bas), ilk_desen))
    for son in range(bas[0] + 1, len(satirlar)):
        if re.search(son_desen, satirlar[son]):
            return "".join(satirlar[bas[0]:son + 1])
    raise MK.CapaHatasi("alt blok SONU bulunamadi: %r" % (son_desen,))


def _capa_haritasi(kaynak, yol, kapsamlar, ad):
    """Kapsam -> KAYNAK esleme. TEMIZ dosyadan, mutasyondan ONCE kurulur
    (MK.kapsam_haritasi doktrini: capa, olculen seyin kendisinden etkilenemez)."""
    harita = {MODUL_KAPSAMI: kaynak}
    yuklemler = sorted({k for k in kapsamlar if isinstance(k, str)
                        and k != MODUL_KAPSAMI})
    alt_bloklar = [k for k in kapsamlar if isinstance(k, tuple)]
    if not yuklemler and not alt_bloklar:
        return harita
    modul = _bellekte_kur(kaynak, ad, yol)
    for kapsam in yuklemler:
        harita[kapsam] = MK.kapsam_kaynagi(modul, kapsam)
    for kapsam in alt_bloklar:
        yuklem, ilk_desen, son_desen = kapsam
        harita[kapsam] = _alt_blok(
            MK.kapsam_kaynagi(modul, yuklem), ilk_desen, son_desen)
    return harita


def kos_batarya(gozcu_yolu=None, kilit_yolu=None, test_yolu=None, yaz=print):
    """Bataryayi kostur; sonucu SOZLUK olarak dondur (rapor `yaz` ile basilir).

    Yollar PARAMETRIK: `--kendini-test` fikstur kopyalari uzerinde ayni govdeyi
    kosturur (canli dosyada mutasyon YASAK)."""
    gozcu_yolu = gozcu_yolu or GOZCU_YOLU
    kilit_yolu = kilit_yolu or KILIT_YOLU
    kok = os.path.dirname(os.path.abspath(gozcu_yolu))

    kaynak_onbellegi = {}
    for yol in (gozcu_yolu, kilit_yolu):
        with open(yol, encoding="utf-8") as dosya:
            ham = dosya.read()
        # 🔴 SON SATIR NORMALIZASYONU (bkz. modul docstring): dosyanin SON
        # yuklemi `inspect.getsource` ciktisiyla ancak boyle esleser. Diske
        # yazilmaz — yalnizca bellekteki karsilastirma metnidir.
        kaynak_onbellegi[yol] = ham if ham.endswith("\n") else ham + "\n"
    test = _test_modulu(test_yolu)

    # Capa haritalari TEMIZ kaynaktan, TEK KEZ.
    hedefler = {GOZCU_YOLU: gozcu_yolu, KILIT_YOLU: kilit_yolu}
    haritalar = {}
    capa_hatasi = {}
    for kanonik, gercek in hedefler.items():
        kapsamlar = [m[2] for m in MUTANTLAR if m[1] == kanonik]
        sys.modules.pop("kilit", None)
        if gercek == kilit_yolu:
            sys.modules["kilit"] = _bellekte_kur(
                kaynak_onbellegi[kilit_yolu], "kilit", kilit_yolu)
        try:
            haritalar[kanonik] = _capa_haritasi(
                kaynak_onbellegi[gercek], gercek, kapsamlar,
                "capa_%s" % os.path.basename(gercek).replace(".", "_"))
        except Exception as hata:                                  # noqa: BLE001
            haritalar[kanonik] = {MODUL_KAPSAMI: kaynak_onbellegi[gercek]}
            capa_hatasi[kanonik] = "%s: %s" % (type(hata).__name__, hata)
        finally:
            sys.modules.pop("kilit", None)

    # KONTROL: gercek kilit + gercek gozcu
    sys.modules.pop("kilit", None)
    kontrol = test.kos(_bellekte_kur(
        kaynak_onbellegi[gozcu_yolu], "gozcu_kontrol", gozcu_yolu))
    if kontrol.gecen != kontrol.toplam:
        for hata in kontrol.hatalar:
            yaz("KONTROL KIRIK " + hata)
        yaz("KONTROL=KIRMIZI GECEN=%d/%d" % (kontrol.gecen, kontrol.toplam))
        sys.modules.pop("kilit", None)
        _pycache_temizle(kok)
        return {"rc": 2, "kontrol": "KIRMIZI", "olen": 0,
                "toplam": len(MUTANTLAR), "sayac": {}, "bayat": []}
    yaz("KONTROL=YESIL GECEN=%d/%d" % (kontrol.gecen, kontrol.toplam))

    sayac = {"IDDIA": 0, "ISTASYON": 0, "KABLO_KOPUK": 0, "YAMA_TUTMADI": 0}
    bayat_eksenler = []          # ADLI kova: hangi eksen OLCULEMEDI
    olum_eslesmesi = {}

    for sira, (ad, kanonik_yol, kapsam, desen, donusum) in enumerate(MUTANTLAR, 1):
        gercek_yol = hedefler[kanonik_yol]
        kaynak = kaynak_onbellegi[gercek_yol]
        try:
            if kanonik_yol in capa_hatasi:
                raise MK.CapaHatasi(capa_hatasi[kanonik_yol])
            mutant_kaynak = MK.mutant_metni(
                haritalar[kanonik_yol], kaynak, [(kapsam, desen, donusum)])
        except MK.CapaHatasi as hata:
            # 🔴 ADLI KOVA: capa bayatligi COKME ile ayni kovaya KONMAZ.
            yaz("%-58s YAMA_TUTMADI (capa: %s)" % (ad, hata))
            sayac["YAMA_TUTMADI"] += 1
            bayat_eksenler.append(ad.split()[0])
            continue

        sys.modules.pop("kilit", None)
        try:
            if kanonik_yol == KILIT_YOLU:
                mutant_kilit = _bellekte_kur(mutant_kaynak, "kilit", kilit_yolu)
                sys.modules["kilit"] = mutant_kilit
                gozcu_kaynak = kaynak_onbellegi[gozcu_yolu]
            else:
                gercek_kilit = _bellekte_kur(
                    kaynak_onbellegi[kilit_yolu], "kilit", kilit_yolu)
                sys.modules["kilit"] = gercek_kilit
                mutant_kilit = gercek_kilit
                gozcu_kaynak = mutant_kaynak

            mutant_gozcu = _bellekte_kur(gozcu_kaynak, "gozcu_mutant_%d" % sira,
                                         gozcu_yolu)

            # KABLO KANITI
            if mutant_gozcu.kilit is not mutant_kilit:
                yaz("%-58s KABLO_KOPUK (gozcu.kilit != mutant_kilit)" % ad)
                sayac["KABLO_KOPUK"] += 1
                continue

            try:
                sonuc = test.kos(mutant_gozcu)
                gecen = sonuc.gecen
                toplam = sonuc.toplam
                if gecen != toplam:
                    sayac["IDDIA"] += 1
                    vaka = _ilk_hata_testi(sonuc)
                    olum_eslesmesi[ad.split()[0]] = vaka
                    yaz("%-58s OLDU GECEN=%d/%d vaka=%s" % (ad, gecen, toplam, vaka))
                else:
                    yaz("%-58s HAYATTA GECEN=%d/%d" % (ad, gecen, toplam))
            except BaseException as hata:                          # noqa: BLE001
                sayac["ISTASYON"] += 1
                yaz("%-58s OLDU ISTISNA=%s" % (ad, type(hata).__name__))
        finally:
            sys.modules.pop("kilit", None)

    _pycache_temizle(kok)
    yaz("")
    eslesme_str = " ".join("%s=%s" % (k, v) for k, v in olum_eslesmesi.items())
    yaz("OLUM_ESLESMESI: " + (eslesme_str if eslesme_str else "YOK"))
    # 🔴 ADLI KOVA her koşumda BASILIR (bos olsa da): "hangi eksen olculmedi"
    # sorusu bir tur daha ertelenemez.
    yaz("CAPA_BAYAT_EKSENLER: " + (", ".join(bayat_eksenler) if bayat_eksenler else "YOK"))
    # 🔴 PAYDA DAIMA len(MUTANTLAR): kapsam tabandan DUSMEZ.
    yaz("MUTANT=%d/%d IDDIA=%d ISTASYON=%d KABLO_KOPUK=%d YAMA_TUTMADI=%d KONTROL=YESIL" % (
        sayac["IDDIA"], len(MUTANTLAR),
        sayac["IDDIA"], sayac["ISTASYON"], sayac["KABLO_KOPUK"], sayac["YAMA_TUTMADI"]))

    kapi = (sayac["IDDIA"] == len(MUTANTLAR)
            and sayac["ISTASYON"] == 0
            and sayac["KABLO_KOPUK"] == 0
            and sayac["YAMA_TUTMADI"] == 0)
    return {"rc": 0 if kapi else 1, "kontrol": "YESIL", "olen": sayac["IDDIA"],
            "toplam": len(MUTANTLAR), "sayac": sayac, "bayat": bayat_eksenler}


# ------------------------------------------------------------------ kendini test
# 🔴 [[capa-turetme-altyapisi-kullanilmadan-kaldi]] 2. kol: "bayatligi olcen kol,
# olctugu seyin YANINDA olsun". Bu kol capa bayatligini FIKSTURDE uretir ve
# bataryanin onu ADIYLA raporlayip rc≠0 dondurdugunu KANITLAR. Canli dosyada
# mutasyon YOK — fikstur KOPYADIR.
KENDINI_TEST_FIKSTURU = ("OLCULEMEDI_RC = 2", 'OLCULEMEDI_RC = int("2")')


def kendini_test():
    """K316/K4: capa bayatlayinca batarya 16/16 DEMEZ, ekseni ADIYLA basar, rc≠0.

    Fikstur DAVRANISI DEGISTIRMEZ (`2` == `int("2")`) — yani KONTROL yesil kalir
    ve olculen tek sey CAPA'nin bayatligidir; boylece "kirmizinin sebebi hedef
    kol mu" sorusu tek yanitli olur.
    """
    gecen, toplam = 0, 0

    def esit(ad, gercek, beklenen):
        nonlocal gecen, toplam
        toplam += 1
        if gercek == beklenen:
            gecen += 1
            print("YESIL  %-52s %r" % (ad, gercek))
        else:
            print("KIRMIZI %-51s beklenen=%r gercek=%r" % (ad, beklenen, gercek))

    tmp = tempfile.mkdtemp(prefix="gozcu-mutasyon-kendini-test-")
    try:
        with open(GOZCU_YOLU, encoding="utf-8") as dosya:
            gozcu_kaynak = dosya.read()
        eski, yeni = KENDINI_TEST_FIKSTURU
        if gozcu_kaynak.count(eski) != 1:
            print("KIRMIZI fikstur capasi kaynakta %d kez (1 olmali): %r"
                  % (gozcu_kaynak.count(eski), eski))
            return 1
        f_gozcu = os.path.join(tmp, "gozcu.py")
        f_kilit = os.path.join(tmp, "kilit.py")
        f_test = os.path.join(tmp, "gozcu-test.py")
        with open(f_gozcu, "w", encoding="utf-8") as dosya:
            dosya.write(gozcu_kaynak.replace(eski, yeni, 1))
        shutil.copyfile(KILIT_YOLU, f_kilit)
        shutil.copyfile(TEST_YOLU, f_test)

        satirlar = []
        sonuc = kos_batarya(f_gozcu, f_kilit, f_test, yaz=satirlar.append)
        rapor = "\n".join(satirlar)

        esit("F1 fiksturde KONTROL YESIL kalir", sonuc["kontrol"], "YESIL")
        esit("F2 rc sifir DEGIL", sonuc["rc"] != 0, True)
        esit("F3 payda TABANDAN dusmez", sonuc["toplam"], len(MUTANTLAR))
        esit("F4 oran 16/16 DEMEZ", sonuc["olen"] == len(MUTANTLAR), False)
        esit("F5 dusen eksen ADIYLA raporlanir", sonuc["bayat"], ["M3"])
        esit("F6 rapor satirinda ADLI kova var",
             "CAPA_BAYAT_EKSENLER: M3" in rapor, True)
        esit("F7 oran satiri 15/16", "MUTANT=15/16" in rapor, True)
        esit("F8 YAMA_TUTMADI=1", sonuc["sayac"].get("YAMA_TUTMADI"), 1)
        # KONTROL MUTANTI: fikstursuz kosumda ayni kol YESIL yanmali.
        temiz = []
        temiz_sonuc = kos_batarya(yaz=temiz.append)
        esit("K1 KONTROL (fikstursuz) rc=0", temiz_sonuc["rc"], 0)
        esit("K2 KONTROL 16/16", temiz_sonuc["olen"], len(MUTANTLAR))
        esit("K3 KONTROL bayat eksen YOK", temiz_sonuc["bayat"], [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _pycache_temizle()

    print("\nKENDINI_TEST VAKA=%d DUSEN=%d" % (toplam, toplam - gecen))
    return 0 if gecen == toplam else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--kendini-test" in argv:
        return kendini_test()
    return kos_batarya()["rc"]


if __name__ == "__main__":
    sys.exit(main())
