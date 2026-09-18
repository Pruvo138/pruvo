#!/usr/bin/env python3
"""PRUVO NOBET TETIGI — LLM turunu GOZCUNUN kararina baglayan DETERMINISTIK kapi.

NEDEN VAR (19 Agu 2026, N1 "gozcu kablolama", Okan emri "sozde degil ozde calissin"):
`ci-nobeti.sh` crontab'ta `7 * * * *` ile KOSULSUZ tur aciyordu — gunde 24 LLM turu,
CI yesil olsa da. Gozcu (`gozcu.py`) DOGRU karari zaten uretiyordu ama o kararin
ci-nobeti tarafinda TUKETICISI YOKTU (olculdu 19 Agu 19:23 kalbi: `llm_turu`,
`tetik`, `gunluk_gerekli` yaziliydi; ci-nobeti hicbirine bakmiyordu).
Bu dosya EKSIK KABLODUR: karari okur, turun acilip acilmayacagina karar verir.

TEK KAYNAK:
  - Karar girdisi = gozcunun yazdigi KALP dosyasi (`gozcu-kalp.json`). Burada
    IKINCI bir CI olcumu YOK, gh CAGRILMAZ, defter AYRISTIRILMAZ — hepsi gozcude.
  - Bayatlik esigi + bayatlik yuklemi gozcuden ITHAL edilir (`KALP_BAYATLIK_SN`,
    `kalp_bayat_mi`). IKIZ SAYI URETILMEZ.
  - Icra AYNEN `nobet-kapi.py`'de kalir; H1-H7 zinciri bu dosyadan GORULMEZ bile.
    Degisen yalniz TETIKLENME.

FAIL-LOUD (spec 3): gozcu olurse SESSIZLIK "yesil" SANILMAZ. Kalp yok ya da
45 dk'dan bayatsa: `KALP BAYAT` satiri + KIRMIZI hukum + gunluk tur acilir.
FAIL-CLOSED: bu kapinin KENDISI kosamazsa (gozcu yuklenemedi, kalp bozuk) hukum
"AC + KIRMIZI"dir — olculemedi YESIL DEGILDIR.

TEK TUR GARANTISI: bir karar en fazla BIR KEZ tuketilir. Tuketim damgasi
`gozcu-kilit/<anahtar>.tuketildi` dosyasidir; `O_CREAT|O_EXCL` ile atomik
olusturulur. Ayni run-id ikinci kez gorulunce dosya ZATEN VARDIR -> tur ACILMAZ.

CIKIS KODLARI (ci-nobeti.sh bunlari okur — TEK KAYNAK):
   0 = AC,   kirmizi YOK
   1 = AC,   KIRMIZI
  10 = ACMA, kirmizi YOK
  11 = ACMA, KIRMIZI
  20 = kapinin KENDISI dustu -> ci-nobeti FAIL-CLOSED davranir (ac + kirmizi)

Kabul:    python3 /Users/okan/.claude/cron/nobet-tetik-test.py
Curutucu: python3 /Users/okan/.claude/cron/nobet-tetik-mutasyon.py
"""

import argparse
import importlib.util
import json
import os
import sys
import time

CRON_KOKU = os.path.dirname(os.path.abspath(__file__))
GOZCU_YOLU = os.path.join(CRON_KOKU, "gozcu.py")

# Yollar env ile ezilebilir — YALNIZ kabul testi/uctan uca kosum icin. Uretimde
# hicbiri set edilmez ve varsayilanlar kullanilir.
KALP_YOLU = os.environ.get("PRUVO_TETIK_KALP") or os.path.join(CRON_KOKU, "gozcu-kalp.json")
KILIT_DIZINI = os.environ.get("PRUVO_TETIK_KILIT") or os.path.join(CRON_KOKU, "gozcu-kilit")
GOZCU_CRON_LOG = os.environ.get("PRUVO_TETIK_GOZCU_LOG") or os.path.join(CRON_KOKU, "gozcu-cron.log")

# Tuketim damgasi soneki. SONEK KUMESI TAM LISTEDIR: temizlik kolu YALNIZ bu
# soneki tasiyan dosyalari siler; gozcunun `<run-id>.kilit` dosyalarina DOKUNMAZ
# (canli turun kilidi silinirse ikinci isci acilir).
TUKETIM_SONEKI = ".tuketildi"
# Ureten temizler (Okan, USTUN kural): damgalar sonsuza kadar birikmez.
TUKETIM_YAS_ESIGI_SN = 7 * 86400

RC_AC_YESIL = 0
RC_AC_KIRMIZI = 1
RC_ACMA_YESIL = 10
RC_ACMA_KIRMIZI = 11
RC_KAPI_DUSTU = 20


def _gozcu_yukle(yol=GOZCU_YOLU):
    """gozcu.py TEK KAYNAKTIR; yukleme deseni gozcunun kendi yukleyicisiyle ayni.

    🔴 CRON_KOKU sys.path'e ONDEN eklenir: `gozcu.py` govdesinde `import kilit`
    vardir ve `kilit.py` bu dizindedir. Cagiran BASKA bir dizinden kosarsa
    (or. bir olcum betigi scratchpad'den) import DUSER, `GZ` None kalir ve kapi
    fail-closed varsayilanina gider — yani "olcum" yerine SABIT bir cevap uretir.
    19 Agu 2026'da tam bu olctu: 24 kaydin 24'u `GOZCU_YUKLENEMEDI` dondu ve
    projeksiyon "gunde 24 tur" diye SAHTE bir sayi yazdi. Kapinin dogrulugu
    cagiranin cwd tesadufune BIRAKILMAZ. Kabul: nobet-tetik-test.py I bolumu.
    """
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    spec = importlib.util.spec_from_file_location("gozcu_tetik", yol)
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


try:
    GZ = _gozcu_yukle()
    GOZCU_YUKLEME_HATASI = ""
except BaseException as _hata:            # fail-closed: sebebi TASI, yut ma
    GZ = None
    GOZCU_YUKLEME_HATASI = "%s: %s" % (type(_hata).__name__, _hata)

# 🔴 UCUNCU HAL JETONU: gozcu uzerinden nobet-kapi'den TURETILIR. Gozcu
# yuklenemediyse `None` kalir ve sessizlestirme kolu HIC ATESLEMEZ (fail-closed).
LLM_KOLU_KAPALI = getattr(GZ, "LLM_KOLU_KAPALI", None) if GZ is not None else None


class Karar(object):
    """Tek karar noktasinin ciktisi. Alanlar log satirina BIREBIR gider."""

    __slots__ = ("hukum", "sebep", "anahtar", "bayraklar", "kirmizi")

    def __init__(self, hukum, sebep, anahtar, bayraklar, kirmizi):
        self.hukum = hukum                    # "AC" | "ACMA"
        self.sebep = sebep
        self.anahtar = anahtar                # tuketim damgasinin adi ("" = damgasiz)
        self.bayraklar = tuple(bayraklar)     # nobet-kapi.py'ye gecen bayraklar
        self.kirmizi = bool(kirmizi)

    def _demet(self):
        return (self.hukum, self.sebep, self.anahtar, self.bayraklar, self.kirmizi)

    def __eq__(self, other):
        return isinstance(other, Karar) and self._demet() == other._demet()

    def __repr__(self):
        return "Karar(%r, %r, %r, %r, %r)" % self._demet()


def bugunun_adi(simdi):
    return time.strftime("%Y-%m-%d", time.gmtime(simdi))


def _uretken_karari(kalp):
    """K311: uretkenlik hukmu TEK KEZ verilir — GOZCU verir, tetik UYAR.

    Oncelik SIRASI hukumdur:
      1. Gozcunun kalbe YAZDIGI hukum (`uretken` / `uretken_sebep`). Ikiz
         hesap YOK: iki yerde hesaplanan kural sessizce ayrisir
         ([[ayni-alan-iki-hukum-biri-sessiz]]). Bu ayni zamanda o alanlarin
         CANLI TUKETICISIDIR — `k311-baglanti-kapisi.py` bunu SAYARAK olcer.
      2. Alan yoksa (eski kalp / kismi kurulum) gozcunun sozlesme fonksiyonu
         yeniden hesaplar.
    FAIL-CLOSED: gozcu yuklenemediyse ya da sozlesme fonksiyonu (`uretken_mi`)
    YOKSA hukum "URETMEDI"dir. Eksik sozlesme sessizce yesil sayilamaz; aksi
    halde kurulum yarim kalinca hat ESKI sahte-yesil davranisina geri doner ve
    kimse fark etmez ([[kapinin-menzili-cagri-yeridir]]).
    """
    kalp = kalp or {}
    if "uretken" in kalp:
        return bool(kalp.get("uretken")), str(kalp.get("uretken_sebep") or "-")
    if GZ is None or not hasattr(GZ, "uretken_mi"):
        return False, "SOZLESME_YOK"
    return GZ.uretken_mi(kalp)


def seviye_kirmizisi(kalp):
    """KORGOZ_K311_SEVIYE — "SU AN kac kirmizi DURUYOR?" (SEVIYE, kenar DEGIL).

    `gozcu.py` kalbe `kirmizi_toplam` YAZAR; 27 Agu 2026'ya kadar bu alanin
    OKUYANI YOKTU (yazan=1 okuyan=0; kiyas `yeni_kirmizi` 1/1). Olculmus
    sonuc: F2 (`kirmizi_toplam=11`, 11 duran kirmizi) ile F3 (KONTROL, 0
    kirmizi) BIREBIR ayni ciktiyi veriyordu -> `rc=10` ("ACMA, kirmizi YOK").
    4,7 saatlik yayin kesintisi boyunca hat bu yuzden "kirmizi YOK" dedi:
    kirmiziyi GORMEDI degil, GORDU ve `yeni_kirmizilar()` filtresinde ELEDI
    ([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]).

    🔴 BU KOL TUR ACMAZ. Dondurma emri yururlukte; degisen yalniz ACMA
    hukmunun YESIL mi KIRMIZI mi oldugudur.

    FAIL-CLOSED: alan YOKSA (eski kalp / yarim kurulum) SESSIZ SIFIR
    URETILMEZ -> -1 doner ve cagiran bunu OLCULEMEDI sayar. Sessiz sifir,
    tam da kapatmaya calistigimiz korlugun kendisidir.

    🔴 K326 (W2-2, 18 Eyl 2026): `kirmizi_toplam` 40-kosumluk PENCERENIN
    sayisidir — ardili YESIL olan eski kirmiziyi da sayar, pencereden dusen
    duran kirmiziyi da unutur. Gozcu artik `kirmizi_ardilsiz` (is akisi
    basina ardili olmayan kirmizi) yazar; SEVIYE once ONU okur. Alan yoksa
    (eski kalp) pencere sayisina DUSER — geriye donuk kol korunur, sessiz
    sifir URETILMEZ. Pencere alani SILINMEZ (iki eksen yan yana).
    """
    kalp = kalp or {}
    alan = "kirmizi_ardilsiz" if "kirmizi_ardilsiz" in kalp else "kirmizi_toplam"
    if alan not in kalp:
        return -1
    try:
        return max(0, int(kalp.get(alan) or 0))
    except (TypeError, ValueError):
        return -1


def seviye_karari(kalp):
    """SEVIYE kolunun TEK KARAR NOKTASI. Doner: Karar ya da None (kol susar).

    `karar()` merdiveninde IKI yerde cagrilir (3. basamagin ici + kuyruk);
    ikiz kural URETILMEZ — ikiz kural sessizce ayrisir
    ([[ayni-alan-iki-hukum-biri-sessiz]]). Mutant (`M-SEVIYE`) BU fonksiyonu
    hedefler: oldurulunce F2 yeniden F3'e esitlenir ve F4 DEGISMEZ.
    """
    seviye = seviye_kirmizisi(kalp)
    if seviye < 0:
        return Karar("ACMA", "SEVIYE_OLCULEMEDI", "", (), True)
    if seviye > 0:
        return Karar("ACMA", "SEVIYE_KIRMIZI_%d" % seviye, "", (), True)
    return None


def icra_etti_karari(kalp, olculemedi):
    """3. basamagin GOVDESI: gozcu bu nabizda bir tur ACTI — hukum ACMA.

    W2-2'de `karar()`dan AYNEN cikarildi (davranis degismedi); K334'un
    anahtar ekseni bu hukmun KIRMIZI bayragini asagi basamaga tasiyabilsin
    diye ayri fonksiyondur.
    """
    # 🔴 K311 YUZ C — "gozcu bir tur ACTI MI?" ile "gozcu IS GORDU MU?"
    # AYRI sorulardir. Eskiden bu kol yalniz `olculemedi`yi (ci/defter
    # olcumu) tasiyordu; gozcunun KENDI kosum hukmu buraya HIC GELMIYORDU.
    # Sonuc: "kostu, hicbir sey uretmedi" hali `RC_ACMA_YESIL=10` donuyor
    # ve `ci-nobeti.sh` `BITIS rc=0` yaziyordu (taban: 46 yesil bitis).
    # 🔴 Bu kol HALA "ACMA" der — cift atesleme yasagi DEGISMEDI; degisen
    # yalniz o ACMA'nin YESIL mi KIRMIZI mi oldugudur.
    uretken, uret_sebep = _uretken_karari(kalp)
    if not uretken:
        # 🔴 UCUNCU HAL — SESSIZ AMA DAR. Iki emniyet birlikte aranir:
        #   M1: sebep TAM O JETON olacak. Gercek `OLCULEMEDI` (gozcu FIILEN
        #       okuyamiyor) bu kola GIREMEZ ve KIRMIZI kalir.
        #   M2: kosum GERCEKTEN basarili bitmis olacak. Dusen/atlanan bir
        #       kosum, jeton tasisa bile SUSTURULAMAZ — yeni hal, acik
        #       koldaki bir arizayi gizlemek icin kullanilamaz.
        if (LLM_KOLU_KAPALI is not None
                and uret_sebep == LLM_KOLU_KAPALI
                and (kalp.get("icra_hal") or "") == "KOSTU_BASARILI"
                and kalp.get("icra_rc") == 0):
            return Karar("ACMA", LLM_KOLU_KAPALI, "", (), False)
        return Karar("ACMA", "GOZCU_URETMEDI_%s" % uret_sebep, "", (), True)
    # 🔴 K311 YUZ B — gozcunun KENDI saydigi ACIK ESKALASYON hatti KIRMIZI
    # yakar. `gozcu-eskalasyon.md`ye 19-26 Agu arasi 42 satir yazildi
    # (ISTISNASIZ deneme=3) ve HICBIRI bir karara donusmedi; bu kol o
    # sayiyi TUKETIR. Kendini temizler: ARDILI yesil olunca sayi duser
    # (W2-2: gozcu kesisimi `ardilsiz_kirmizilar` ile yapar, pencereyle DEGIL).
    if int(kalp.get("eskalasyon_acik") or 0) > 0:
        return Karar("ACMA", "ESKALASYON_ACIK", "", (), True)
    # 3b. KORGOZ_K311_SEVIYE — "gozcu bir tur ACTI MI?" ile "SU AN kac
    # kirmizi DURUYOR?" AYRI sorulardir. Duran kirmizi, cozulmusle ayni
    # kovada kalmaz. Hukum HALA "ACMA" (cift atesleme yasagi DEGISMEDI).
    _seviye = seviye_karari(kalp)
    if _seviye is not None:
        return _seviye
    return Karar("ACMA", "GOZCU_ICRA_ETTI", "", (), olculemedi)


def aday_anahtar(kalp, bugun):
    """4./5. basamagin ACACAGI turun anahtari ("" = acacak tur YOK).

    Sira `karar()` ile AYNI: once kirmizi (4), sonra gunluk (5). Gunluk
    aday YALNIZ kalbin gunu tetigin gunuyle ayniysa verilir — gece yarisini
    asan bir kalp (gozcu 23:53'te `gunluk:D` acti, tetik 00:07'de kostu)
    ertesi gunun turunu gozcuyle YARISTIRMAZ; o hal eski BLANKET kolda kalir.
    """
    hedef = str(kalp.get("hedef_run") or "")
    if kalp.get("tetik") == "CI_KIRMIZI" and hedef:
        return "kirmizi:%s" % hedef
    if kalp.get("gunluk_gerekli"):
        epok = kalp.get("epok")
        try:
            kalp_gunu = bugunun_adi(float(epok)) if epok is not None else None
        except (TypeError, ValueError):
            kalp_gunu = None
        if kalp_gunu == bugun:
            return "gunluk:%s" % bugun
    return ""


def ayni_tur_mu(kalp, bugun):
    """K334 — CIFT ATESLEME YASAGI ANAHTAR EKSENINDE (W2-2, 18 Eyl 2026).

    OLCULDU (27 Agu, 768 noktalik uzay): `rc=0` (AC) 60 kombinasyonda cikti
    ve ISTISNASIZ `icra_denendi=False` ile — 3. basamak BLANKET oldugu icin
    gozcu HERHANGI bir tur actiginda 4 (CI_KIRMIZI) ve 5 (GUNLUK_DEFTER)
    kollari yapisal olarak ULASILAMAZDI. Ornek: gozcu `DEFTER_DAGITIM`
    (`--tur-kapat`) kosturdu ve `gunluk_gerekli=True`; gunluk defter turu o
    nabizda HIC acilmadi, cunku "gozcu bir tur acti" = "gunluk tur acildi"
    sayiliyordu.

    Doner True (= 3. basamak hukmu gecerli, ACMA) su hallerde:
      · kalpte `icra_anahtar` alani YOK (eski kalp) -> BLANKET (geriye donuk)
      · alan BOS (gozcu tur acti ama anahtar yazmadi) -> BLANKET (fail-closed:
        bilinmeyen tur, ayni tur sayilir; cift atesleme riski alinmaz)
      · acilacak aday tur YOK
      · aday anahtar == gozcunun anahtari (ayni tur ikinci kez ACILMAZ)
    """
    if "icra_anahtar" not in kalp:
        return True
    gozcu_anahtari = str(kalp.get("icra_anahtar") or "")
    if not gozcu_anahtari:
        return True
    aday = aday_anahtar(kalp, bugun)
    if not aday:
        return True
    return aday == gozcu_anahtari


def karar(kalp, simdi, bugun, bayat_tavani=None):
    """SAF karar — dosya OKUMAZ, YAZMAZ. Tek karar noktasi.

    Merdiven (SIRALAMA HUKUMDUR, karistirma):
      1-2. kalp yok / bayat        -> FAIL-LOUD: AC + KIRMIZI (gunluk anahtar)
      3.   gozcu ZATEN icra etti   -> ACMA (cift atesleme yasagi; K334: yalniz
                                      AYNI anahtar icin — `ayni_tur_mu`)
      4.   yeni kirmizi            -> AC, anahtar = kirmizi:<run-id>  (TEK TUR)
      5.   gunluk defter turu      -> AC, anahtar = gunluk:<gun>      (24 saatte 1)
      6.   gozcu OLCEMEDI          -> ACMA + KIRMIZI (olculemedi != yesil)
      6b.  DURAN kirmizi (SEVIYE) -> ACMA + KIRMIZI (tur ACILMAZ)
      7.   yesil                   -> ACMA
    """
    if GZ is None:
        return Karar("AC", "GOZCU_YUKLENEMEDI", "gunluk:%s" % bugun, ("--tur",), True)
    tavan = bayat_tavani if bayat_tavani is not None else GZ.KALP_BAYATLIK_SN

    # 1. Gozcu hic yazmamis: sessizlik YESIL DEGILDIR.
    if kalp is None:
        return Karar("AC", "KALP_YOK", "gunluk:%s" % bugun, ("--tur",), True)

    # 2. Gozcu susmus (olmus / cron dusmus): sessizlik YESIL DEGILDIR.
    if GZ.kalp_bayat_mi(kalp, simdi, tavan):
        return Karar("AC", "KALP_BAYAT", "gunluk:%s" % bugun, ("--tur",), True)

    # Gozcu kendi olcumunu yapamadiysa hukum KIRMIZI'dir; ama acilacak is varsa
    # (gunluk tur) yine de acilir — bayrak asagidaki kollara TASINIR.
    olculemedi = not kalp.get("ci_olculdu") or not kalp.get("defter_olculdu")

    # 3. Gozcu turu ZATEN actiysa ikincisini ACMA.
    # B6: soru "rc ne?" DEGIL, "gozcu bir tur ACTI MI?" — iki soru AYRI
    # alandadir. `icra_rc` ATLANDI'da None olur; bu kol ona bakarsa
    # ucustaki turun ustune IKINCI tur acar. Eski kalplerde
    # `icra_denendi` yoktur -> geriye donuk kol korunur.
    # 🔴 K334 (W2-2, 18 Eyl 2026): yasak ANAHTAR eksenindedir — gozcunun
    # actigi tur ile 4./5. basamagin acacagi tur AYNI anahtarsa ACMA; FARKLI
    # ise asagi inilir (bkz. `ayni_tur_mu`). Gozcunun kendi turunun hukmu
    # (uretmedi / eskalasyon / seviye / kol kapali) asagidaki AC hukmune
    # ADIYLA ve RENGIYLE tasinir: sebep `<gozcu-sebebi>+<kol>` olur.
    # 🔴 Bagimsiz curutucu bulgusu (18 Eyl): ilk surum yalniz KIRMIZI
    # bayragini tasiyordu; `ESKALASYON_ACIK` adi `GUNLUK_DEFTER`e donusup
    # ci-nobeti HUKUM'unda KAYBOLUYORDU (A4/A7 kolunun tam korudugu sey).
    # Gozcu sebebi ONDE durur: ci-nobeti HUKUM'u kirmizinin ADIYLA baslar.
    ic_sebep = ""
    ic_kirmizi = False
    if kalp.get("icra_denendi", kalp.get("icra_rc") is not None):
        ic = icra_etti_karari(kalp, olculemedi)
        if ayni_tur_mu(kalp, bugun):
            return ic
        ic_sebep = ic.sebep + "+"
        ic_kirmizi = ic.kirmizi

    # 4. Yeni kirmizi var, gozcu acamamis (kilit doluydu vb.) -> o run-id icin TEK tur.
    hedef = str(kalp.get("hedef_run") or "")
    if kalp.get("tetik") == "CI_KIRMIZI" and hedef:
        return Karar("AC", ic_sebep + "CI_KIRMIZI", "kirmizi:%s" % hedef, ("--tur",),
                     olculemedi or ic_kirmizi)

    # 5. Gunluk defter turu — 24 saatlik pencerede TAM 1.
    if kalp.get("gunluk_gerekli"):
        return Karar("AC", ic_sebep + "GUNLUK_DEFTER", "gunluk:%s" % bugun, ("--tur",),
                     olculemedi or ic_kirmizi)

    # 6. Acilacak is yok ama gozcu olcemedi: SESSIZ YESIL URETME.
    if olculemedi:
        return Karar("ACMA", "OLCULEMEDI", "", (), True)

    # 6b. KORGOZ_K311_SEVIYE — yeni kirmizi YOK ama DURAN kirmizi VAR.
    # Bu basamak 6'dan SONRA gelir: olcum yapilamadiysa `kirmizi_toplam`
    # zaten guvenilmezdir, OLCULEMEDI daha dogru bir cevaptir.
    _seviye = seviye_karari(kalp)
    if _seviye is not None:
        return _seviye

    # 7. Yesil: tur ACILMAZ. (Gercekten sakin hat BOS TUR ACMAZ — kol
    # "hep AC"a cevrilmedi; F3 KONTROL fiksturu bunu her koşumda olcer.)
    return Karar("ACMA", "YESIL", "", (), False)


def anahtar_dosyasi(anahtar, dizin=None):
    """Damga yolu. Ad dosya-guvenli kumeye INDIRGENIR (`kirmizi:12/3` -> `kirmizi_12_3`)."""
    dizin = dizin or KILIT_DIZINI
    guvenli = "".join(ch if (ch.isalnum() or ch in ".-_") else "_" for ch in anahtar)
    return os.path.join(dizin, guvenli + TUKETIM_SONEKI)


def tuket(anahtar, simdi, dizin=None):
    """Damgayi ATOMIK koy. Doner: True = BU cagri kazandi (tur acilabilir).

    Ayni anahtar ikinci kez gelirse dosya ZATEN VARDIR -> False (tur ACILMAZ).
    `O_CREAT|O_EXCL` yarisi cekirdekte cozer; iki es zamanli ci-nobeti de guvenli.
    Damga YAZILAMAZSA False doner: yazamadigimiz bir tekillik garantisini
    "verdik" saymayiz (fail-closed — tur ACILMAZ, sebep loga duser).
    """
    yol = anahtar_dosyasi(anahtar, dizin)
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        fd = os.open(yol, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    except OSError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as dosya:
        dosya.write("ANAHTAR=%s\nEPOK=%.3f\nPID=%d\n" % (anahtar, simdi, os.getpid()))
    return True


def damga_temizle(dizin=None, yas_esik=TUKETIM_YAS_ESIGI_SN, simdi=None):
    """Ureten temizler: yasi esigi asan TUKETIM damgalarini siler.

    YALNIZ `*.tuketildi` dosyalari. Gozcunun `<run-id>.kilit` dosyalari ve
    dizinler bu kolun DISINDADIR — canli kilidi silmek ikinci isci acar.
    """
    dizin = dizin or KILIT_DIZINI
    simdi = simdi if simdi is not None else time.time()
    try:
        adlar = os.listdir(dizin)
    except OSError:
        return 0
    silinen = 0
    for ad in adlar:
        if not ad.endswith(TUKETIM_SONEKI):
            continue
        yol = os.path.join(dizin, ad)
        try:
            if not os.path.isfile(yol):
                continue
            if (simdi - os.path.getmtime(yol)) <= yas_esik:
                continue
            os.unlink(yol)
            silinen += 1
        except OSError:
            continue
    return silinen


# 🔴 KOL HALI — DEGER BURADA URETILIR, kabuk onu SATIRDAN OKUR. Boylece
# `ci-nobeti.sh` jeton literali TASIMAZ (sart ①: tek kaynak). Kapali deger
# jeton zincirinden (`nobet-kapi` -> `gozcu` -> burasi) TURER; yalniz ACIK
# etiketi burada tanimlidir.
KOL_HALI_ACIK = "ACIK"


def kol_hali(k):
    """Karardan kolun HALI: jeton (KAPALI) | 'ACIK' | 'OLCULEMEDI'.

    🔴 Jeton zinciri KOPUKSA 'ACIK' DENMEZ: `OLCULEMEDI` doner. Bilmedigimiz
    bir hali 'acik' diye raporlamak, olculemeyeni yanlis cevaba cevirmektir.
    """
    if LLM_KOLU_KAPALI is None:
        return "OLCULEMEDI"
    # K334 (W2-2): sebep `<gozcu-sebebi>+<kol>` birlesik olabilir; kapali kol
    # jetonu HERHANGI bir parcada ise kol KAPALI'dir (ACIK diye raporlanmaz).
    return LLM_KOLU_KAPALI if LLM_KOLU_KAPALI in k.sebep.split("+") else KOL_HALI_ACIK


def karar_satiri(k):
    """Greplenebilir tek satir. `TUR ACILMADI sebep=YESIL` jetonu BURADA uretilir."""
    # 🔴 `kol_hali=` alani SONA eklenir: mevcut alanlarin ADI ve SIRASI
    # DEGISMEZ (`sebep=` okuyan awk ve stub'lar aynen calisir).
    if k.hukum == "AC":
        return ("TUR ACILIYOR sebep=%s anahtar=%s bayraklar=%s KIRMIZI=%d "
                "kol_hali=%s") % (
            k.sebep, k.anahtar or "-", " ".join(k.bayraklar) or "-",
            1 if k.kirmizi else 0, kol_hali(k))
    return "TUR ACILMADI sebep=%s KIRMIZI=%d kol_hali=%s" % (
        k.sebep, 1 if k.kirmizi else 0, kol_hali(k))


def cikis_kodu(k):
    if k.hukum == "AC":
        return RC_AC_KIRMIZI if k.kirmizi else RC_AC_YESIL
    return RC_ACMA_KIRMIZI if k.kirmizi else RC_ACMA_YESIL


def kalp_yasi(kalp, simdi):
    if not isinstance(kalp, dict):
        return -1
    try:
        epok = float(kalp.get("epok"))
    except (TypeError, ValueError):
        return -1
    return int(simdi - epok)


def _kalp_oku(yol):
    if GZ is not None:
        return GZ.kalp_oku(yol)
    if not os.path.exists(yol):
        return None
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def _bayat_satiri_yaz(satir, yol=None):
    """spec 3(a): KALP BAYAT satiri gozcu-cron.log'a DA duser (sessiz kalma yolu yok)."""
    yol = yol or GOZCU_CRON_LOG
    try:
        with open(yol, "a", encoding="utf-8") as dosya:
            dosya.write(satir.rstrip("\n") + "\n")
    except OSError:
        pass


def kos(simdi=None, kalp_yolu=None, kilit_dizini=None, kuru=False,
        gozcu_log=None, bayat_tavani=None):
    """Tam bir tetik turu. Doner: (satirlar, rc)."""
    simdi = simdi if simdi is not None else time.time()
    kalp_yolu = kalp_yolu or KALP_YOLU
    kilit_dizini = kilit_dizini or KILIT_DIZINI
    satirlar = []

    if GZ is None:
        satirlar.append("GOZCU YUKLENEMEDI %s" % GOZCU_YUKLEME_HATASI)

    kalp = _kalp_oku(kalp_yolu)
    bugun = bugunun_adi(simdi)
    k = karar(kalp, simdi, bugun, bayat_tavani)

    if k.sebep in ("KALP_BAYAT", "KALP_YOK"):
        tavan = bayat_tavani if bayat_tavani is not None else (
            GZ.KALP_BAYATLIK_SN if GZ is not None else 0)
        bayat = "KALP BAYAT sebep=%s yas=%d tavan=%d damga=%s" % (
            k.sebep, kalp_yasi(kalp, simdi), tavan, (kalp or {}).get("damga") or "-")
        satirlar.append(bayat)
        if not kuru:
            _bayat_satiri_yaz(bayat, gozcu_log)

    if k.hukum == "AC" and k.anahtar and not kuru:
        if not tuket(k.anahtar, simdi, kilit_dizini):
            # Damga ZATEN var: bu karar bir kez tuketildi, IKINCISI ACILMAZ.
            k = Karar("ACMA", k.sebep + "_TUKETILDI", k.anahtar, (), k.kirmizi)

    satirlar.append(karar_satiri(k))
    if not kuru:
        damga_temizle(kilit_dizini, simdi=simdi)
    return satirlar, cikis_kodu(k)


def main(argv=None):
    ayristirici = argparse.ArgumentParser(
        description="PRUVO nobet tetigi (gozcu kararini tuketir)")
    ayristirici.add_argument("--karar", action="store_true",
                             help="karari ver, damgayi TUKET, cikis kodunu dondur")
    ayristirici.add_argument("--kuru", action="store_true",
                             help="karari basar; damga KOYMAZ, log YAZMAZ")
    args = ayristirici.parse_args(argv)

    if not args.karar and not args.kuru:
        ayristirici.print_help()
        return 2
    try:
        satirlar, rc = kos(kuru=args.kuru)
    except BaseException as hata:            # kapi dusmesi SESSIZ olmaz
        print("TETIK KAPISI DUSTU %s: %s" % (type(hata).__name__, hata))
        return RC_KAPI_DUSTU
    for satir in satirlar:
        print(satir)
    return rc


if __name__ == "__main__":
    sys.exit(main())
