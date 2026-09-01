#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/git_ortami.py — GIT BAGLAM SCRUB'ININ TEK TANIMI (kutuphane modulu).

NE ISE YARAR: bu depodaki kapilar depo kokunu `git -C <yol> rev-parse --show-toplevel`
ile TURETIR. Cagiran surecten MIRAS ALINAN git baglam degiskenleri (bir git kancasi
bunlari IHRAC EDER) bu ACIK `-C` hedefini SESSIZCE ezer. Bu modul, git cagrilarinin
kosacagi TEMIZ ortami ve o ortamla kok turetimini TEK YERDE tanimlar.

OLCULEN KUSUR (6 Agu 2026, yeniden uretildi — tools/diriltme-kapisi.py):
  * linked worktree kancasinda GIT_DIR MUTLAK olarak miras alinir (ana checkout
    kancasinda hic set EDILMEZ);
  * GIT_DIR mutlak + GIT_WORK_TREE bos oldugunda git depo KESFINI ATLAR ve CARI DIZINI
    calisma agacinin tepesi kabul eder;
  * boylece `git -C <depo>/tools rev-parse --show-toplevel` -> `<depo>/tools` doner
    (YANLIS), cunku `-C` once o ALT DIZINE gecer.
Sonuc: kapi worktree'de ya yanlis agaci olcer ya da OLCULEMEDI verip commit'i bloklar
(ve isciyi kapinin kendisini atlatmaya iter).

NEDEN TEK KAYNAK ([[ikiz-tanim-sessiz-ayrisma]]): ayni listenin ikinci bir kopyasi
zamanla sessizce ayrisir ve ayrisma DAIMA gevsek yonde olur (bir ad eksik kalir, o ad
uzerinden miras alinan baglam geri sizar). Bu yuzden:
  * `GIT_BAGLAM_DEGISKENLERI` bu depoda YALNIZ BURADA tanimlanir (nobeti asagida:
    `--kendini-test` izlenen .py dosyalarini tarar, ikinci tanim gorurse KIRMIZI);
  * `tools/ic-rapor-adi-kapisi.py`, `tools/spec-ifsa-kapisi.py` ve
    `tools/diriltme-kapisi.py` UCU DE bu modulden turer;
  * TUKETICIDE `try/except ImportError -> yerel tanim` YAZILMAZ: o dusus yolu ikizin
    ta kendisidir ve gevsek yonde ayrisir. Modul yoksa cagri COKSUN (gurultulu).

Kullanim (kutuphane):
    from git_ortami import git_kok, git_ortami
    kok = git_kok(dizin, git_ortami())      # "" = git agaci degil (fail-closed sozlesme)

Kullanim (nobet):
    python3 tools/git_ortami.py --kendini-test    # scrub davranisi + TEK KAYNAK nobeti

Cikis kodu (--kendini-test): 0 = tum iddialar gecti, 1 = en az biri dustu.
"""
import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # tuketiciler SALT-OKUNUR tarar: hedef repoya __pycache__ yazma.

MODUL_ADI = "git_ortami.py"

# Miras alinan git baglami: bu 11 ad git'in depo KESFINI degistirir ya da ACIK `-C`
# hedefini ezer. Liste DAR degil GENIS tutulur — eksik kalan her ad bir sizinti yoludur.
GIT_BAGLAM_DEGISKENLERI = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_PREFIX", "GIT_NAMESPACE", "GIT_INDEX_VERSION",
)


def git_ortami(korunan_baglam=()):
    """Miras alinan git baglami SILINMIS `os.environ` kopyasi (PATH vb. KORUNUR).

    Bir tuketici Git'in kancaya ACIKCA ihrac ettigi bir baglami olcuyorsa o ad
    ``korunan_baglam`` ile ilan edilir. Bilinmeyen ad fail-closed reddedilir;
    varsayilan bos kume onceki tam-scrub davranisidir.
    """
    korunan = frozenset(korunan_baglam)
    bilinmeyen = korunan.difference(GIT_BAGLAM_DEGISKENLERI)
    if bilinmeyen:
        raise ValueError("korunan_baglam kanonik degil: %s" % sorted(bilinmeyen))
    ort = os.environ.copy()
    for ad in GIT_BAGLAM_DEGISKENLERI:
        if ad in korunan:
            continue
        ort.pop(ad, None)
    return ort


# Sentetik fiksturlerin varsaydigi ilk dal adi. Tek kaynak: cagri yerleri bunu
# TEKRAR ETMEZ ([[ikiz-tanim-sessiz-ayrisma]]).
ILK_DAL = "main"


def _ilk_dal_civile(args):
    """`git init` cagrilarina `-b main` CIVILER (zaten verilmisse DOKUNMAZ).

    🔴 OLCULEN KUSUR (1 Eyl 2026, KraL-Tamirci-1Eyl — SERIT B `Merge-kanit tablosu`
    kirmizisinin KOK NEDENI, CI benzesimiyle yeniden uretildi):
    `git init`'in urettigi ilk dal adi GIT SURUMUNE/AYARINA BAGLIDIR. Okan'in
    makinesindeki Apple Git 2.50.1 `main` uretir; GitHub runner'indaki git 2.55.0
    `master` uretir ("hint: Using 'master' as the name for the initial branch" —
    kirmizi kosumun checkout logunda BIREBIR duruyor). Dolayisiyla `init` sonrasi
    `checkout main` yapan her sentetik fikstur OKAN'DA YESIL, CI'DA KIRMIZI kosar;
    kusur ne kodda ne veride, ORTAMDADIR ve 'bende geciyor' savunmasi onu gizler.

    NEDEN CAGRI YERINDE DEGIL BURADA (sinif onarimi, [[ucuncu-tekrar-sinif-kapisi]]):
    olculdu — bu depodaki `sentetik_git(..., "init", ...)` cagri yerlerinin bir kismi
    `-b main` yaziyor, bir kismi YAZMIYOR. Ayni invaryanti her cagri yerinde elle
    tekrarlamak tam da sessizce ayrisan ikiz tanimdir: yeni yazilan her fikstur
    kurali unutmaya adaydir. Kanonik yardimci onu TEK YERDE garanti eder.

    Hicbir cagri yeri `master` BEKLEMIYOR (olculdu, 1 Eyl); acikca `-b`/
    `--initial-branch` veren cagri yerinin secimi KORUNUR.
    """
    args = list(args)
    if not args or args[0] != "init":
        return args
    for a in args:
        if a == "-b" or a == "--initial-branch" or str(a).startswith("--initial-branch="):
            return args
    return [args[0], "-b", ILK_DAL] + args[1:]


def sentetik_git(calisma_dizini, *args, kimlik_ad="fikstur",
                 kimlik_eposta="fikstur@ornek.gecersiz", ek_ortam=None,
                 korunan_baglam=(), ayarlar=(), **run_kw):
    """Sentetik/gecici depolardaki git'in TEK guvenli cagri yolu.

    Ortam daima kopyadir; depo kesfini etkileyen miras GIT_* adlari temizlenir.
    Pozitif bir nobet belirli bir git baglamini OLCUYORSA o ad, cagri yerinde
    ``korunan_baglam`` ile acikca korunur. Varsayilan bos kume = fail-safe scrub.
    Kimlik yalniz bu komuta ``-c`` ile verilir, hicbir config dosyasina yazilmaz.
    ``calisma_dizini`` zorunludur ve subprocess cwd'si acikca sabitlenir.
    """
    korunan = frozenset(korunan_baglam)
    bilinmeyen = korunan.difference(GIT_BAGLAM_DEGISKENLERI)
    if bilinmeyen:
        raise ValueError("korunan_baglam kanonik degil: %s" % sorted(bilinmeyen))
    ortam = git_ortami()
    if ek_ortam:
        ortam.update(ek_ortam)
    for ad in GIT_BAGLAM_DEGISKENLERI:
        if ad not in korunan:
            ortam.pop(ad, None)
    komut = ["git", "-c", "user.name=" + kimlik_ad,
             "-c", "user.email=" + kimlik_eposta]
    komut.extend(ayarlar)
    komut.extend(_ilk_dal_civile(args))
    return subprocess.run(komut, cwd=calisma_dizini, env=ortam, **run_kw)


def git_kok(dizin, ortam=None):
    """<dizin>'in AIT OLDUGU git agacinin kokunu doner; "" = git agaci DEGIL.

    `-C dizin` ZORUNLUDUR (argumansiz cagri CWD'ye bakar) ve cagri VARSAYILAN OLARAK
    temizlenmis ortamda kosar: kok ORTAMDAN degil, `-C <yol>` KESFINDEN turer.
    <ortam> yalniz cagri yerinin bu secimi ACIKCA tasimasi icin disaridan verilebilir
    (mutasyon capasi cagri yerinde dursun diye); None = git_ortami().

    Fail-closed sozlesme: hata durumunda "" doner — hukum veren taraf bunu OLCULEMEDI
    sayar, sessiz bir yesile CEVIRMEZ.
    """
    p = subprocess.run(["git", "-C", dizin, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, errors="replace",
                       env=git_ortami() if ortam is None else ortam)
    return p.stdout.strip() if p.returncode == 0 else ""


def _kos(depo, *args):
    return subprocess.run(["git", "-C", depo, *args], capture_output=True, text=True,
                          errors="replace", env=git_ortami())


# ===========================================================================
# DAVRANISSAL SONDA — kapilarin KENDI kabul testleri icin ORTAK surucu.
# Anlati kanit degildir: sentetik depo + GERCEK `git worktree add` + GERCEK `git commit`
# ile tetiklenen GERCEK bir pre-commit kancasi kurulur; kapinin BASTIGI KOK olculur.
# Ortam ELLE set edilip kanca TAKLIT EDILMEZ — kanca baglamini git'in kendisi uretir.
# ===========================================================================
_KOK_DESENI = re.compile(r"olculen agac = (.+?)(?:\s+\(|\s*$)", re.M)
_KANCA_GOVDESI = """#!/bin/sh
# Sentetik pre-commit: kapiyi kanca baglamindan kosar, ciktisini kaydeder ve
# commit'i BLOKLAMAZ (olculen sey kapinin HUKMU degil, BASTIGI KOK).
"%(python)s" "./tools/%(kapi)s" > "%(kayit)s" 2>&1
printf 'SONDA_RC=%%s\\n' "$?" >> "%(kayit)s"
exit 0
"""


def _basilan_kok(cikti):
    m = _KOK_DESENI.search(cikti or "")
    return m.group(1).strip() if m else None


def worktree_kanca_kok_olcumu(kapi_kaynagi, hedef_ad):
    """Kapi kopyasini IKI baglamda kosturur ve BASTIGI KOKU olcer.

    <kapi_kaynagi> : kosturulacak kapi dosyasinin yolu (mutasyonlu KOPYA olabilir).
    <hedef_ad>     : sentetik depoda `tools/` altina konacak AD (kapinin kendi
                     dosyasini tarama disi birakan istisnasi bu ada bagli olabilir).

    Dondurur: {"wt": <worktree koku>, "kancasiz": (rc, kok, esit_mi),
               "kanca": (rc, kok, esit_mi), "kanca_kosti": bool, "kanca_cikti": str}
    """
    with tempfile.TemporaryDirectory(prefix="pruvo-kok-sondasi-") as kd:
        ana = os.path.join(kd, "ana")
        os.makedirs(os.path.join(ana, "tools"))
        _kos(ana, "init", "-q", "-b", "main")
        _kos(ana, "config", "user.email", "t@t.local")
        _kos(ana, "config", "user.name", "t")
        shutil.copyfile(kapi_kaynagi, os.path.join(ana, "tools", hedef_ad))
        shutil.copyfile(os.path.abspath(__file__), os.path.join(ana, "tools", MODUL_ADI))
        with open(os.path.join(ana, "veri.txt"), "w", encoding="utf-8") as f:
            f.write("sentetik icerik\n")
        _kos(ana, "add", "-A")
        _kos(ana, "commit", "-q", "-m", "ilk")

        wt = os.path.join(kd, "wt")
        _kos(ana, "worktree", "add", "-q", "-b", "sonda-dali", wt)
        gercek_wt = os.path.realpath(wt)
        kapi_wt = os.path.join(wt, "tools", hedef_ad)

        # (a) KANCASIZ: dogrudan calistirma, cwd = worktree koku.
        pa = subprocess.run([sys.executable, kapi_wt], cwd=wt, capture_output=True,
                            text=True, errors="replace", env=git_ortami())
        kok_a = _basilan_kok(pa.stdout + pa.stderr)

        # (b) KANCA ICI: GERCEK commit -> GERCEK pre-commit. Linked worktree kancalari
        #     ORTAK dizinden (`<ana>/.git/hooks`) okunur.
        kayit = os.path.join(kd, "kanca-cikti.txt")
        kanca = os.path.join(ana, ".git", "hooks", "pre-commit")
        os.makedirs(os.path.dirname(kanca), exist_ok=True)
        with open(kanca, "w", encoding="utf-8") as f:
            f.write(_KANCA_GOVDESI % {"python": sys.executable, "kapi": hedef_ad,
                                      "kayit": kayit})
        os.chmod(kanca, 0o755)
        with open(os.path.join(wt, "veri.txt"), "a", encoding="utf-8") as f:
            f.write("worktree'de degisiklik\n")
        _kos(wt, "add", "-A")
        subprocess.run(["git", "-C", wt, "-c", "user.email=t@t.local", "-c",
                        "user.name=t", "commit", "-q", "-m", "kanca sondasi"],
                       capture_output=True, text=True, errors="replace",
                       env=git_ortami())
        kanca_cikti = ""
        if os.path.exists(kayit):
            with open(kayit, "r", encoding="utf-8", errors="replace") as f:
                kanca_cikti = f.read()
        m = re.search(r"SONDA_RC=(\d+)", kanca_cikti)
        kanca_rc = int(m.group(1)) if m else None
        kok_b = _basilan_kok(kanca_cikti)

        def esit(k):
            return k is not None and os.path.realpath(k) == gercek_wt

        return {
            "wt": gercek_wt,
            "kancasiz": (pa.returncode, kok_a, esit(kok_a)),
            "kanca": (kanca_rc, kok_b, esit(kok_b)),
            "kanca_kosti": bool(kanca_cikti),
            "kanca_cikti": kanca_cikti,
        }


# ===========================================================================
# NOBET — scrub DAVRANISI + TEK KAYNAK (drift) iddiasi.
# ===========================================================================
# 🔴 6 AGU 2026, BAGIMSIZ CURUTUCU OLCUMU — ESKI DRIFT EKSENI YALANCI YESIL BASIYORDU.
# Eski desen `GIT_BAGLAM_DEGISKENLERI\s*=\s*\(` idi: yani nobet DEGISKEN ADINA capaliydi.
# Birlesmis agacta olculdu: nobetci "ikinci tanim yok" (PASS) derken ada BAKMAYAN bir
# tarama UC scrub kumesi buldu ve biri ZATEN SAPMISTI (`tools/kok-cozum-taramasi.py`
# icindeki kume 10 ad tasiyordu, `GIT_INDEX_VERSION` EKSIKTI). Yani iddia YAPISAL OLARAK
# kordu: ad degisirse, `[...]` yazilirsa ya da kume satir-ici bir `for` dongusunde
# durursa nobet HICBIR SEY gormezdi ([[ikiz-tanim-sessiz-ayrisma]]).
#
# YENI EKSEN — AD'DAN CAPASIZ, YAPIYA BAKAR (regex degil `ast`):
# "GIT_DIR ve GIT_WORK_TREE'yi BIRLIKTE tasiyan her tuple/liste/kume LITERALI" bir
# scrub kumesidir; degisken adi, parantez bicimi ve nerede durdugu ONEMSIZDIR.
#
# SOZLUK EKSENI (7 Agu 2026, curutucu enjeksiyon olcumu): `{"GIT_DIR": None,
# "GIT_WORK_TREE": None}` ve `ortam.update({...})` bicimleri DIZI eksenine takilmiyordu
# -> delik VARDI ama BEYANDA YOKTU (okuyucu kapsami oldugundan GENIS saniyordu).
# Sozluk ANAHTARLARI da taranir; ANCAK dizi ekseninden DAHA DAR bir sartla:
#   sozlugun TUM sabit-dize anahtarlari KANONIK git baglam adlarindan olmali.
# NEDEN ASIMETRIK (olculdu, yanlis-pozitif kaniti): sozluk bu depoda MESRU olarak
# "her degiskenin DEGERINI raporlayan" bir teshis kaydi icin de kullaniliyor
# (`tools/kok-cozum-taramasi.py` -> `{"agac": ..., "GIT_DIR": ..., "GIT_WORK_TREE": ...,
# "araclar": {...}}`). O kayit bir scrub kumesi DEGILDIR; ham "iki ad ayni sozlukte"
# olcutu onu KIRMIZI yakardi (yanlis pozitif). YABANCI ANAHTAR sarti onu eler ve
# gercek scrub sozluklerini yakalar (olculen yanlis pozitif: 0).
# Dizi ekseninde ayni daraltma UYGULANMAZ: orada yabanci dize gorulen bir kume bugun
# YOK ve daraltmak DETEKSIYONU KUCULTUR (kapsam kaybi > yanlis-pozitif kazanci).
#
# 🔴 BEYAN EDILMIS SINIR (OLCULMEDI, uydurma degil — ACIKCA yazili): asagidaki bicimler
# YAKALANMAZ ve bugun bu depoda ORNEGI YOKTUR:
#   (a) adlarin AYRI AYRI ifadelerde silinmesi (`ort.pop("GIT_DIR"); ort.pop("GIT_WORK_TREE")`),
#   (b) adlarin CALISMA ZAMANINDA uretilmesi (`"GIT_" + "DIR"`, konfigurasyondan okuma),
#   (c) .py DISI dosyalar (kabuk kancalari, YAML) — bu nobet YALNIZ izlenen `.py` tarar,
#   (d) git baglam adlarinin YANINDA YABANCI anahtar da tasiyan SOZLUK (or.
#       `{"GIT_DIR": ..., "aciklama": ...}`) — yukaridaki yanlis-pozitif ayrimi geregi.
#   (e) sozlugun LITERAL yerine ANAHTAR-KELIME CAGRISIYLA kurulmasi (or.
#       `dict(GIT_DIR=None, GIT_WORK_TREE=None)`): bu bicimde adlar `ast.Constant`
#       dize anahtari DEGIL, `ast.keyword.arg` tanimlayicisidir; ne dizi ne sozluk
#       ekseni gorur. Bagimsiz curutucu 7 Agu 2026'da enjeksiyonla OLCTU (kaciyor,
#       rc=0). Depoda bu bicimde ornek SAYISI: 0 -> delik bugun TEORIK; kabul
#       edilemez olan "delik VAR ama beyanda YOK" haliydi, bu satirla kapatildi.
#       Tespit mantigi BILEREK degistirilmedi: ornegi olmayan bir eksen icin
#       tarama yuzeyini genisletmek yanlis-pozitif riskini bedelsiz artirirdi.
# Olculen alternatif eksen ("dosyada 11 addan >=4'u dizi sabiti olarak geciyor") bugun
# AYNI dosyalari buluyor (V1 == V2) -> ek yakalama getirmiyor, ek yanlis-pozitif riski
# getiriyor; bu yuzden DAR eksen secildi ve sinir burada BEYAN EDILDI.
_CIFT = frozenset(("GIT_DIR", "GIT_WORK_TREE"))


def _dizi_adlari(dugum):
    """Tuple/List/Set literalindeki sabit dize ogeleri."""
    return {e.value for e in dugum.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)}


def _sozluk_adlari(dugum):
    """Sozluk literalinin sabit dize ANAHTARLARI — ancak HER anahtari `GIT_` onekliyse.

    Yabanci anahtar (or. `"agac"`, `"araclar"`) tasiyan sozluk bir TESHIS/RAPOR
    kaydidir, scrub kumesi DEGILDIR. Onek olcutu KANONIK 11 ADA capalanmaz: yarin
    listeye girecek bir `GIT_*` adini tasiyan scrub sozlugu de yakalanmalidir (ada
    capalamak bu nobetcinin ZATEN olculmus kusuruydu)."""
    anahtarlar = [k for k in dugum.keys if k is not None]
    adlar = {k.value for k in anahtarlar
             if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    if len(adlar) != len(anahtarlar):
        return set()                      # sabit-dize OLMAYAN anahtar var -> kayit degil
    if not all(a.startswith("GIT_") for a in adlar):
        return set()                      # YABANCI anahtar -> teshis kaydi (yanlis pozitif)
    return adlar


def scrub_kumeleri(kaynak):
    """<kaynak> icindeki AD'DAN BAGIMSIZ scrub kume literalleri -> [frozenset(adlar)].

    `SyntaxError` YUKARI BIRAKILIR: ayristirilamayan dosya 'temiz' SAYILAMAZ."""
    agac = ast.parse(kaynak)
    bulgular = []
    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):
            adlar = _dizi_adlari(dugum)
        elif isinstance(dugum, ast.Dict):
            adlar = _sozluk_adlari(dugum)
        else:
            continue
        if _CIFT <= adlar:
            bulgular.append(frozenset(adlar))
    return bulgular


def kume_imzasi(adlar):
    """Kume ICERIGINE bagli imza: kume DEGISIRSE muafiyet GECERSIZLESIR (path bazli
    genel bir 'bu dosyaya bakma' kacisi DEGILDIR)."""
    return hashlib.sha256("|".join(sorted(adlar)).encode("utf-8")).hexdigest()


# KAYITLI MUAFIYET — (yol, MUAF KUME, gerekce). Muafiyet KUMENIN ICERIGINE baglidir:
# o dosyadaki kume tek ad bile degisirse imza tutmaz ve dosya KIRMIZI yanar. Kume
# ACIKCA yazilir (imza ondan TURETILIR): hem okunur, hem kabul testi defteri KARSILAYAN
# fikstur uretebilir — "sentetik agacta nobeti kapat" kacisina gerek kalmaz.
DRIFT_MUAFIYETI = (
    ("tools/urunler-guard-provenans-test.py",
     ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
      "GIT_OBJECT_DIRECTORY"),
     "AYRI EKSEN + BILEREK DAR, OLCUMLE secilmis kume: bu liste depo KOKU KESFI icin "
     "degil, kabul testinin ALT SURECLERINE git degiskeni SIZMASINI onlemek icin var "
     "ve her ad icin 'bu degisken kac iddiayi kirmizi yakiyor' AYRI AYRI olculmus, "
     "olcumsuz adlar (GIT_NAMESPACE, GIT_CEILING_DIRECTORIES, "
     "GIT_ALTERNATE_OBJECT_DIRECTORIES, GIT_DISCOVERY_ACROSS_FILESYSTEM) BILEREK "
     "disarida birakilmistir. Modulden turetmek o testin OLCULMUS davranisini "
     "degistirir (kor 'tum GIT_* sil' bu depoda ZATEN reddedilmis bir karardir: "
     "GIT_AUTHOR_DATE/GIT_COMMITTER_* o testin deterministik damgalaridir). Ayrica "
     "dosyanin KENDI X1 iddiasi bu kumeyi `_env()` ile capalar: sapma ORADA kirmizi "
     "yanar, yani kume nobetsiz DEGILDIR."),
)


def _muafiyet_kumesi(govde):
    return {(yol, kume_imzasi(adlar)) for yol, adlar, _g in govde}


GEREKCE_YER_TUTUCU = "GEREKCE YAZ — bu kume neden AYRI EKSEN, OLCUMLE anlat"


def muafiyet_kaydi(dosya_yolu, kok=None):
    """<dosya_yolu> icin DRIFT_MUAFIYETI'ne OLDUGU GIBI yapistirilabilir kayit(lar).

    🔴 NEDEN AYRI FONKSIYON: yardimcinin BASTIGI govde ile defterin BEKLEDIGI govde ayri
    ayri yazilirsa sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]]). 7 Agu 2026 OLCULDU:
    defter (yol, IMZA HEX, gerekce)'den (yol, AD DIZISI, gerekce)'ye gecti ama yardimci
    ESKI bicimde kaldi -> bastigi 3 kaydin 3'u de defterde TUTMUYORDU (uyan=0/3). Bicim
    artik TEK YERDE (burada) uretilir ve `IDDIA-KAYIT-BICIM` onu defterin TUKETICISIYLE
    (`_muafiyet_kumesi`) capalar: emitter kayarsa kabul testi KIRMIZI yanar.

    Yol REPO-GORELI dondurulur: hijyen nobeti (`bayat_kayit_yollari`) kaydi `git ls-files`
    ciktisiyla karsilastirir; MUTLAK yol orada HIC bulunmaz -> kayit DOGDUGU AN bayat olur.
    Ayni kume dosyada birden cok yerde geciyorsa TEK kayit basilir (defterde mukerrer
    satir gurultuden baska ise yaramaz; muafiyet zaten kume ICERIGINE baglidir)."""
    tam = os.path.realpath(dosya_yolu)
    with open(tam, "r", encoding="utf-8") as f:
        kumeler = scrub_kumeleri(f.read())
    agac = git_kok(os.path.dirname(tam), git_ortami()) if kok is None else kok
    yol = dosya_yolu
    if agac:
        goreli = os.path.relpath(tam, os.path.realpath(agac))
        if not goreli.startswith(".."):
            yol = goreli
    tekil = {}
    for adlar in kumeler:
        tekil[tuple(sorted(adlar))] = None
    return [(yol, adlar, GEREKCE_YER_TUTUCU) for adlar in tekil]


def muafiyet_fiksturu_yaz(depo, govde=None):
    """Sentetik depoya kayit defterinin YOLLARINI, KAYITLI kumeyle serer.

    Defter hijyeni (bayat kayit nobeti) boylece sentetik agaclarda da FIILEN kosar;
    "kabul testinde nobeti kapat" gibi bir kacis yolu ACILMAZ. Fikstur govdesi defterden
    TURETILIR — ikinci bir yerde ad listesi tutulmaz."""
    for yol, adlar, _g in (DRIFT_MUAFIYETI if govde is None else govde):
        tam = os.path.join(depo, yol)
        os.makedirs(os.path.dirname(tam), exist_ok=True)
        with open(tam, "w", encoding="utf-8") as f:
            f.write("# sentetik fikstur — kayitli muaf kume\nMUAF = (%s)\n"
                    % ", ".join('"%s"' % a for a in adlar))


def bayat_kayit_yollari(kayit_yollari, izlenen_yollar):
    """🔴 TEK KAYNAK — "kayit defterinin isaret ettigi dosya artik IZLENMIYOR" hukmu.

    Bu depoda AYNI hukum iki yerde veriliyor: burada (drift muafiyeti) ve
    `tools/ci-kapsam-test.py::acik_kesif_kontrol` (acik kesif kaydi). Ikisi de BU
    fonksiyonu cagirir — ikinci bir kopya yazilmaz ([[ikiz-tanim-sessiz-ayrisma]]).
    Kural: kayit YENIDEN ADLANDIRMADA da SILINMEDE de BAYATTIR; "dosya yoksa kayit
    zararsiz" muhakemesi kaydi SESSIZCE OLU birakir ve kimse kirmizi gormez."""
    return sorted(y for y in set(kayit_yollari) if y not in set(izlenen_yollar))


def ikinci_tanimlar(kok=None, muafiyet=None, hijyen=None):
    """Izlenen `.py` dosyalarinda IKINCI bir scrub kumesi arar (bu modul HARIC).

    Dondurur: (bulgular, hata); bulgular = [(yol, sirali ad listesi)].
    hata != None -> OLCULEMEDI (fail-closed: tarama yapilamadiysa 'ikinci tanim yok'
    HUKMU VERILMEZ). <kok> verilmezse BETIGIN kendi agaci olculur.

    <muafiyet> kayit defteri (varsayilan DRIFT_MUAFIYETI) — kabul testi SENTETIK
    defterle de cagirir. <hijyen> defterin BAYAT olup olmadigini da olcer; varsayilani
    "yalniz betigin KENDI agaci taranirken" (defter O agaci tarif eder, rastgele bir
    fikstur agacini DEGIL)."""
    govde = DRIFT_MUAFIYETI if muafiyet is None else muafiyet
    hijyen = (kok is None) if hijyen is None else hijyen
    if kok is None:
        # 🔴 realpath (abspath DEGIL): `git_kok` COZULMUS yol dondurur; symlink'li bir
        # kokten (macOS `/tmp` -> `/private/tmp`) bakildiginda `abspath` symlink'i
        # COZMEDIGI icin kendi yolu tutmaz ve modul KENDINI ikiz sayardi -> YANLIS
        # KIRMIZI (6 Agu 2026 olculdu). Nobeti: IDDIA-SYMLINK.
        betik_dizini = os.path.dirname(os.path.realpath(__file__))
        kok = git_kok(betik_dizini, git_ortami())
        if not kok:
            return None, "betigin agaci bir git deposu DEGIL: %s" % betik_dizini
    r = _kos(kok, "ls-files", "-z")
    if r.returncode != 0:
        return None, "git ls-files basarisiz: %s" % r.stderr.strip()[:200]
    kendi = os.path.realpath(__file__)
    muaf = _muafiyet_kumesi(govde)
    izlenen = [y for y in r.stdout.split("\0") if y]
    kullanilan = set()       # muafiyet FIILEN bir kumeye denk geldi mi
    bulunan = []
    for yol in izlenen:
        tam = os.path.join(kok, yol)
        if not yol.endswith(".py") or os.path.realpath(tam) == kendi:
            continue
        try:
            with open(tam, "r", encoding="utf-8") as f:
                icerik = f.read()
        except (UnicodeDecodeError, OSError) as e:
            return None, "%s okunamadi (fail-closed): %s" % (yol, e)
        try:
            kumeler = scrub_kumeleri(icerik)
        except SyntaxError as e:
            return None, "%s AST ile ayristirilamadi (fail-closed): %s" % (yol, e)
        for adlar in kumeler:
            imza = kume_imzasi(adlar)
            if (yol, imza) in muaf:
                kullanilan.add((yol, imza))
                continue
            bulunan.append((yol, sorted(adlar)))
    if hijyen:
        # BAYAT MUAFIYET — IKI YON, ikisi de fail-closed KIRMIZI:
        #   (a) kayit YOLU artik IZLENMIYOR (silinmis YA DA yeniden adlandirilmis) ->
        #       hukum `bayat_kayit_yollari` TEK KAYNAGINDAN gelir (ci-kapsam-test.py'nin
        #       acik kesif kaydiyla AYNI kural, ikinci bir mantik yazilmaz);
        #   (b) yol duruyor ama KAYITLI IMZA artik tutmuyor -> kume degismis, gerekce
        #       yeniden olculmeli.
        yok_olan = bayat_kayit_yollari([y for y, _i in muaf], izlenen)
        if yok_olan:
            return None, ("BAYAT DRIFT MUAFIYETI (kaydin isaret ettigi dosya IZLENEN "
                          "kumede YOK — silinmis ya da yeniden adlandirilmis; kaydi "
                          "sil ya da yolu duzelt): %s" % yok_olan)
        bayat = sorted(a for a in muaf if a not in kullanilan)
        if bayat:
            return None, ("BAYAT DRIFT MUAFIYETI (kume DEGISMIS -> muafiyet ARTIK "
                          "GECERSIZ, gerekceyi yeniden olc): %s"
                          % [(y, i[:12]) for y, i in bayat])
    return sorted(bulunan), None


def _kendini_test():
    sonuclar = []

    # IDDIA-ORTAM (DAVRANIS): dusman bir GIT_DIR mirasi ALTINDA bile kok, `-C` ile
    # verilen ALT DIZININ agacinin TEPESIDIR — o alt dizin DEGIL.
    with tempfile.TemporaryDirectory(prefix="pruvo-git-ortami-") as d:
        depo = os.path.join(d, "depo")
        alt = os.path.join(depo, "tools")
        os.makedirs(alt)
        _kos(depo, "init", "-q", "-b", "main")
        eski = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = os.path.join(depo, ".git")   # kancanin ihrac ettigi sekil
        try:
            temiz = git_kok(alt, git_ortami())
            kirli = git_kok(alt, os.environ.copy())
        finally:
            if eski is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = eski
        iddia_ortam = (os.path.realpath(temiz or "") == os.path.realpath(depo))
        sonuclar.append(("IDDIA-ORTAM scrub-kok-dogru", iddia_ortam,
                         "miras alinan GIT_DIR altinda kok=%r beklenen=%r" % (temiz, depo)))
        # KONTROL: scrub'siz cagri AYNI girdide FARKLI (yanlis) cevap verir — iddia
        # gercekten scrub'i olcuyor, her ortamda kendiliginden yesil degil.
        sonuclar.append(("KONTROL-SCRUBSUZ ayirt-edici",
                         os.path.realpath(kirli or "") != os.path.realpath(depo),
                         "scrub'siz cagri kok=%r (alt dizini agac tepesi sanmali)" % (kirli,)))

    # IDDIA-TEK-KAYNAK (GERCEK AGAC): izlenen agacta muafiyet-disi IKINCI scrub kumesi
    # VARSA KIRMIZI. Fail-closed: tarama/ayristirma yapilamazsa da KIRMIZI.
    ikinci, hata = ikinci_tanimlar()
    sonuclar.append(("IDDIA-TEK-KAYNAK ikinci-tanim-yok", hata is None and ikinci == [],
                     "ikinci kume tasiyan izlenen .py: %r (hata=%r)" % (ikinci, hata)))

    # IDDIA-DRIFT (SENTETIK AGAC): DIZI ekseni AD'DAN CAPASIZ mi? Fikstur GERCEK
    # dosyalara BAGIMLI DEGILDIR (repo temizlense de bu iddia ayakta kalir) ve dort
    # AYRI bicim tasir: `(...)` · `[...]` · BASKA AD · satir-ici `for` dongusu.
    # SOZLUK ekseni AYRI bir iddiadir (IDDIA-DRIFT-SOZLUK) — yoksa tek mutant ikisini
    # birden dusurur ve hangi eksenin oldugu ANLASILMAZ.
    with tempfile.TemporaryDirectory(prefix="pruvo-drift-") as d:
        sdepo = os.path.join(d, "sdepo")
        os.makedirs(os.path.join(sdepo, "tools"))
        _kos(sdepo, "init", "-q", "-b", "main")
        fiksturler = {
            # (1) KANONIK ADLA, tuple — eski desen bunu ZATEN goruyordu
            "tools/f1-kanonik.py":
                'GIT_BAGLAM_DEGISKENLERI = ("GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX")\n',
            # (2) BASKA AD, tuple — eski desen KACIRIYORDU (olculen gercek kusur)
            "tools/f2-baska-ad.py":
                'KESIF_ORTAMI = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")\n',
            # (3) LISTE bicimi — eski desen `\\(` bekliyordu, KACIRIYORDU
            "tools/f3-liste.py":
                'TEMIZLENECEK = [\n    "GIT_DIR",\n    "GIT_WORK_TREE",\n]\n',
            # (4) ADSIZ, satir-ici scrub — hicbir atama YOK, eski desen KACIRIYORDU
            "tools/f4-satir-ici.py":
                'import os\n\n\ndef temiz():\n    o = os.environ.copy()\n'
                '    for ad in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):\n'
                '        o.pop(ad, None)\n    return o\n',
            # (5) KONTROL: TEK ad -> scrub kumesi DEGIL, isaretlenMEmeli
            "tools/f5-kontrol-tek-ad.py": 'SADECE = ("GIT_DIR",)\n',
            # (6) KONTROL: ilgisiz dosya
            "tools/f6-kontrol-ilgisiz.py": 'AYARLAR = ("a", "b")\n',
        }
        for yol, govde in fiksturler.items():
            with open(os.path.join(sdepo, yol), "w", encoding="utf-8") as f:
                f.write(govde)
        _kos(sdepo, "add", "-A")
        s_bulgu, s_hata = ikinci_tanimlar(kok=sdepo)
        s_yollar = sorted({y for y, _a in (s_bulgu or [])})
        iddia_drift = s_hata is None and s_yollar == [
            "tools/f1-kanonik.py", "tools/f2-baska-ad.py", "tools/f3-liste.py",
            "tools/f4-satir-ici.py"]
        sonuclar.append(("IDDIA-DRIFT ada-capasiz-tespit", iddia_drift,
                         "beklenen 4 bicim (kanonik/baska-ad/liste/satir-ici) "
                         "isaretli, 2 kontrol temiz; olculen=%r (hata=%r)"
                         % (s_yollar, s_hata)))

    # IDDIA-DRIFT-SOZLUK (SENTETIK AGAC): SOZLUK ekseni. Curutucu enjeksiyonla olctu:
    # `{"GIT_DIR": None, "GIT_WORK_TREE": None}` ve `update({...})` bicimleri DIZI
    # eksenine takilmiyordu. Fikstur ayrica YANLIS-POZITIF kontrolu tasir: yabanci
    # anahtarli TESHIS kaydi (gercek ornegi `tools/kok-cozum-taramasi.py`de vardir)
    # isaretlenMEmeli — yoksa eksen kapiyi cope atar.
    with tempfile.TemporaryDirectory(prefix="pruvo-drift-sozluk-") as d:
        sdepo = os.path.join(d, "sdepo")
        os.makedirs(os.path.join(sdepo, "tools"))
        _kos(sdepo, "init", "-q", "-b", "main")
        s_fiksturler = {
            # (1) sozluk ATAMASI — anahtarlarin HEPSI git baglam adi
            "tools/d1-sozluk.py": 'SCRUB = {"GIT_DIR": None, "GIT_WORK_TREE": None}\n',
            # (2) satir-ici `update({...})` — hicbir atama YOK
            "tools/d2-update.py":
                'import os\n\n\ndef kur(ortam):\n'
                '    ortam.update({"GIT_DIR": "", "GIT_WORK_TREE": ""})\n'
                '    return ortam\n',
            # (3) KONTROL/YANLIS-POZITIF: TESHIS kaydi — yabanci anahtar tasir
            "tools/d3-kontrol-teshis.py":
                'def rapor(agac):\n    return {"agac": agac, "GIT_DIR": "<yok>",\n'
                '            "GIT_WORK_TREE": "<yok>", "araclar": {}}\n',
            # (4) KONTROL: tek git adi tasiyan sozluk
            "tools/d4-kontrol-tek-ad.py": 'X = {"GIT_DIR": "a"}\n',
        }
        for yol, govde in s_fiksturler.items():
            with open(os.path.join(sdepo, yol), "w", encoding="utf-8") as f:
                f.write(govde)
        _kos(sdepo, "add", "-A")
        d_bulgu, d_hata = ikinci_tanimlar(kok=sdepo)
        d_yollar = sorted({y for y, _a in (d_bulgu or [])})
        iddia_sozluk = d_hata is None and d_yollar == ["tools/d1-sozluk.py",
                                                       "tools/d2-update.py"]
        sonuclar.append(("IDDIA-DRIFT-SOZLUK sozluk-ekseni", iddia_sozluk,
                         "sozluk + update isaretli, TESHIS kaydi (yabanci anahtar) ve "
                         "tek-ad temiz; olculen=%r (hata=%r)" % (d_yollar, d_hata)))

    # --- KAYIT YARDIMCISI (`--kume-imzasi`) DEFTERLE AYNI GOVDEYI MI URETIYOR?
    #     7 Agu 2026 OLCULDU: defterin govdesi (yol, IMZA HEX, gerekce) -> (yol, AD
    #     DIZISI, gerekce) olarak degisti, yardimci ESKI bicimde kaldi; bastigi 3 kaydin
    #     3'u de defterde TUTMUYORDU (uyan=0/3) -> yardimciyi izleyen bir insan, kapinin
    #     kendi talimatiyla COZULEMEYEN bir kirmizi uretiyordu. IKI AYRI IDDIA (bicim /
    #     yol) — tek mutant ikisini birden dusurmesin.
    with tempfile.TemporaryDirectory(prefix="pruvo-kayit-") as d:
        d = os.path.realpath(d)
        kdepo = os.path.join(d, "kdepo")
        os.makedirs(os.path.join(kdepo, "tools"))
        _kos(kdepo, "init", "-q", "-b", "main")
        k_yol = "tools/k1-kaynak.py"
        with open(os.path.join(kdepo, k_yol), "w", encoding="utf-8") as f:
            # TUPLE bicimi BILEREK: dizi/sozluk eksen mutantlari bu fiksturu
            # dusurmesin (MUT-DRIFT-DIZI-KOR tuple'i KORUR, MUT-DRIFT-SOZLUK-KOR
            # sozluge bakar) -> bu iki iddia AYIRT EDICI kalir.
            f.write('SCRUB = ("GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX")\n')
        _kos(kdepo, "add", "-A")
        k_kayitlar = muafiyet_kaydi(os.path.join(kdepo, k_yol))
        with open(os.path.join(kdepo, k_yol), "r", encoding="utf-8") as f:
            k_gercek = {kume_imzasi(a) for a in scrub_kumeleri(f.read())}
        try:
            k_uretilen = {i for _y, i in _muafiyet_kumesi(k_kayitlar)}
        except Exception as _e:                       # govde defterle UYUSMUYOR
            k_uretilen = set()

        # IDDIA-KAYIT-BICIM: kayit defterin TUKETICISINE verilince DOSYADAKI kumenin
        # imzasini uretmeli — yani "yapistir ve kapi yesillenir" FIILEN dogru olmali.
        iddia_bicim = bool(k_kayitlar) and k_uretilen == k_gercek
        sonuclar.append(("IDDIA-KAYIT-BICIM yapistirilabilir-govde", iddia_bicim,
                         "yardimcinin kaydi defter govdesine UYMALI; kayit=%r "
                         "uretilen=%r dosyadaki=%r"
                         % (k_kayitlar, sorted(i[:12] for i in k_uretilen),
                            sorted(i[:12] for i in k_gercek))))

        # IDDIA-KAYIT-YOL: kayit REPO-GORELI yol tasimali. Mutlak yol `git ls-files`
        # ciktisinda HIC bulunmaz -> `bayat_kayit_yollari` kaydi DOGDUGU AN bayat sayar.
        k_yollar = [y for y, _a, _g in k_kayitlar]
        iddia_kayit_yol = k_yollar == [k_yol]
        sonuclar.append(("IDDIA-KAYIT-YOL repo-goreli", iddia_kayit_yol,
                         "kayit izlenen kumeyle karsilastirilir -> REPO-GORELI olmali; "
                         "olculen=%r beklenen=%r" % (k_yollar, [k_yol])))

    # --- KAYIT DEFTERI HIJYENI: IKI AYRI YON, IKI AYRI IDDIA (tek mutant ikisini
    #     birden dusurmesin diye BILEREK ayri kuruldu). Defter SENTETIKTIR: gercek
    #     DRIFT_MUAFIYETI'ne bagimli DEGIL.
    _s_defter = (("tools/muaf-ornek.py",
                  ("GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX"), "sentetik gerekce"),)
    with tempfile.TemporaryDirectory(prefix="pruvo-muaf-") as d:
        mdepo = os.path.join(d, "mdepo")
        os.makedirs(os.path.join(mdepo, "tools"))
        _kos(mdepo, "init", "-q", "-b", "main")
        # Kayitli kume BASKA BIR YOLDA duruyor (dosya yeniden adlandirilmis gibi).
        with open(os.path.join(mdepo, "tools", "baska-ad-almis.py"), "w",
                  encoding="utf-8") as f:
            f.write('MUAF = ("GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX")\n')
        _kos(mdepo, "add", "-A")

        # IDDIA-MUAF-AD-DEGISTI: muafiyet YOLA BAGLIDIR — ayni kume BASKA bir yolda
        # belirirse MUAF DEGILDIR, ihlal olarak BASILIR.
        a_bulgu, a_hata = ikinci_tanimlar(kok=mdepo, muafiyet=_s_defter, hijyen=False)
        iddia_ad = a_hata is None and [y for y, _a in (a_bulgu or [])] == [
            "tools/baska-ad-almis.py"]
        sonuclar.append(("IDDIA-MUAF-AD-DEGISTI yol-bagli-muafiyet", iddia_ad,
                         "kayitli kume BASKA yolda -> ihlal SAYILMALI; olculen=%r "
                         "(hata=%r)" % (a_bulgu, a_hata)))

        # IDDIA-MUAF-SILINDI: kaydin yolu IZLENEN kumede YOKSA (silinmis ya da yeniden
        # adlandirilmis) kayit OLUDUR -> fail-closed KIRMIZI. Eski hal burada SESSIZCE
        # rc=0 veriyordu (7 Agu 2026 olculdu); hukum artik `bayat_kayit_yollari`
        # TEK KAYNAGINDAN gelir (ci-kapsam-test.py acik kesif kaydiyla AYNI kural).
        s_bulgu2, s_hata2 = ikinci_tanimlar(kok=mdepo, muafiyet=_s_defter, hijyen=True)
        iddia_silme = s_bulgu2 is None and s_hata2 is not None and \
            "IZLENEN kumede YOK" in s_hata2
        sonuclar.append(("IDDIA-MUAF-SILINDI olu-kayit-kirmizi", iddia_silme,
                         "kaydin yolu agacta YOK -> OLCULEMEDI olmali; hata=%r"
                         % (s_hata2,)))

    # IDDIA-SYMLINK (REGRESYON BEKCISI): depo SYMLINK'li bir yoldan gorulunce modul
    # KENDINI ikiz SAYMAMALI. Olculen kusur: `abspath` symlink COZMEZ, `git_kok` ise
    # COZULMUS yol dondurur -> kendi yolu tutmaz, nobet YANLIS KIRMIZI verirdi.
    with tempfile.TemporaryDirectory(prefix="pruvo-symlink-") as d:
        d = os.path.realpath(d)
        gercek = os.path.join(d, "gercek")
        os.makedirs(os.path.join(gercek, "tools"))
        _kos(gercek, "init", "-q", "-b", "main")
        shutil.copyfile(os.path.realpath(__file__),
                        os.path.join(gercek, "tools", MODUL_ADI))
        muafiyet_fiksturu_yaz(gercek)     # defter hijyeni burada da FIILEN kosar
        _kos(gercek, "add", "-A")
        bag = os.path.join(d, "bag")            # symlink -> gercek
        os.symlink(gercek, bag)
        p = subprocess.run([sys.executable, os.path.join(bag, "tools", MODUL_ADI),
                            "--ikinci-tanimlar"], cwd=bag, capture_output=True,
                           text=True, errors="replace", env=git_ortami())
        cikti = (p.stdout or "") + (p.stderr or "")
        iddia_symlink = p.returncode == 0 and "IKINCI KUME YOK" in cikti
        sonuclar.append(("IDDIA-SYMLINK kendini-ikiz-saymaz", iddia_symlink,
                         "symlink'li kokten kosum rc=%d cikti=%r"
                         % (p.returncode, cikti.strip()[:160])))

    # KONTROL: liste TAM — ad sayisi ve icerik beyanla ayni (kirpilma nobeti).
    sonuclar.append(("KONTROL-LISTE 11-ad", len(GIT_BAGLAM_DEGISKENLERI) == 11
                     and "GIT_DIR" in GIT_BAGLAM_DEGISKENLERI
                     and "GIT_WORK_TREE" in GIT_BAGLAM_DEGISKENLERI,
                     "ad sayisi=%d" % len(GIT_BAGLAM_DEGISKENLERI)))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


# ===========================================================================
# MUTASYON BATARYASI (`--mutasyon`) — [[mutasyon-kaniti-yeniden-uretilebilir]].
# Her mutant TEK bir IDDIA'yi dusurmeli; KONTROL mutanti YESIL kalmali; capa kaynakta
# TAM BIR KEZ eslesmeli; canli dosya sha256'si once==sonra.
# 🔴 MUTANT NEREDE KOSAR: gecici bir SENTETIK DEPONUN `tools/` dizininde, IZLENEN dosya
# olarak. Sebep: `IDDIA-TEK-KAYNAK` betigin KENDI agacini olcer — kopya git agaci
# OLMAYAN bir dizine konsaydi o iddia TABAN'da bile OLCULEMEDI verirdi ve batarya
# hicbir seyi ayirt edemezdi. Sentetik depo yolu `realpath` ile SYMLINK'SIZ alinir:
# symlink ekseni AYRI bir iddiadir (IDDIA-SYMLINK) ve mutantlari karismaz.
# ===========================================================================
# (ad, eski, yeni, dusmesi beklenen TEK iddia | None = KONTROL)
MUTANTLAR = (
    # DIZI ekseni DARALTILIR: `[...]` bicimi kacar (tuple kalir) -> dizi fiksturu
    # KIRMIZI. 🔴 NEDEN "tumunu oldur" DEGIL: tuple tespiti kayit defteri hijyeninin
    # fiksturlerini de tasir; tumunu oldurmek DORT iddiayi birden dusurur ve mutant
    # AYIRT EDICI olmaz (olculdu: IDDIA-DRIFT + MUAF-AD-DEGISTI + SYMLINK + TEK-KAYNAK).
    ("MUT-DRIFT-DIZI-KOR",
     "        if isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):",
     "        if isinstance(dugum, (ast.Tuple, ast.Set)):", "IDDIA-DRIFT"),
    # SOZLUK ekseni geri alinir (7 Agu ONCESI hal): `{...}` ve `update({...})` kacar.
    ("MUT-DRIFT-SOZLUK-KOR", "        elif isinstance(dugum, ast.Dict):",
     "        elif False:", "IDDIA-DRIFT-SOZLUK"),
    # Muafiyet YOLDAN kopartilir (yalniz imzaya bakar): kume BASKA bir yola tasinsa
    # bile muaf sayilir -> ad degisikligi SESSIZ gecer.
    ("MUT-MUAF-IMZASIZ", "            if (yol, imza) in muaf:",
     "            if imza in {i for _y, i in muaf}:", "IDDIA-MUAF-AD-DEGISTI"),
    # K2 onarimini geri alir: kaydin yolu agacta YOKSA "zararsiz" sayilir -> olu kayit.
    ("MUT-BAYAT-SILME-KOR",
     "        yok_olan = bayat_kayit_yollari([y for y, _i in muaf], izlenen)",
     "        yok_olan = []", "IDDIA-MUAF-SILINDI"),
    # Yardimci defterin ESKI (imza HEX) govdesine doner -> bastigi kayit yapistirilinca
    # TUTMAZ. 7 Agu 2026'nin FIILI hali buydu; mutant o hali geri getirir.
    ("MUT-KAYIT-BICIM-HEX",
     "    return [(yol, adlar, GEREKCE_YER_TUTUCU) for adlar in tekil]",
     "    return [(yol, kume_imzasi(adlar), GEREKCE_YER_TUTUCU) for adlar in tekil]",
     "IDDIA-KAYIT-BICIM"),
    # Yardimci yolu REPO-GORELI yapmaz (verilen argumani aynen basar) -> kayit izlenen
    # kumede HIC bulunmaz, DOGDUGU AN bayat olur.
    ("MUT-KAYIT-YOL-MUTLAK", "            yol = goreli", "            pass",
     "IDDIA-KAYIT-YOL"),
    # Symlink onarimini geri alir: `abspath` symlink COZMEZ -> modul KENDINI ikiz sayar.
    ("MUT-SYMLINK-ABSPATH", "    kendi = os.path.realpath(__file__)",
     "    kendi = os.path.abspath(__file__)", "IDDIA-SYMLINK"),
    # Scrub'i no-op yapar: miras alinan GIT_DIR geri gelir, kok ALT DIZIN cikar.
    ("MUT-SCRUB-NOOP", "        ort.pop(ad, None)", "        pass", "IDDIA-ORTAM"),
    # KONTROL: davranisi DEGISTIRMEYEN metin degisikligi -> batarya YESIL kalmali.
    ("KONTROL-METIN", 'MODUL_ADI = "git_ortami.py"',
     'MODUL_ADI = "git_ortami.py"   # bu depoda scrub\'in TEK tanimi', None),
)

_TABLO_BAS = "MUTANTLAR = ("
_TABLO_SON = "_TABLO_BAS = "


def _tablo_disi(govde):
    """Kaynagi (tablo_oncesi, tablo, tablo_sonrasi) diye ayirir — MUTANTLAR tablosu
    capa metinlerini KENDISI tasir, sayimdan/degisimden HARIC tutulmali."""
    bas = govde.index(_TABLO_BAS)
    son = govde.index(_TABLO_SON, bas + len(_TABLO_BAS))
    return govde[:bas], govde[bas:son], govde[son:]


def _sha256_dosya(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _mutasyon_bataryasi():
    kaynak_yolu = os.path.realpath(__file__)
    with open(kaynak_yolu, "r", encoding="utf-8") as f:
        govde = f.read()
    once_hash = hashlib.sha256(govde.encode("utf-8")).hexdigest()
    _on, _tablo, _arka = _tablo_disi(govde)
    # HIJYEN: bu bataryanin DOKUNMAMASI gereken canli dosyalar (mutasyon YALNIZ
    # kopyaya). Kok tespit edilemezse hijyen OLCULEMEDI olarak basilir, sessiz gecmez.
    _kok = git_kok(os.path.dirname(kaynak_yolu), git_ortami())
    komsu = ["tools/kok-cozum-taramasi.py", "tools/urunler-guard-provenans-test.py"]
    komsu_once = {y: (_sha256_dosya(os.path.join(_kok, y))
                      if _kok and os.path.exists(os.path.join(_kok, y)) else None)
                  for y in komsu}

    def kos_kopya(icerik, kok_d):
        depo = os.path.join(kok_d, "depo")
        os.makedirs(os.path.join(depo, "tools"))
        _kos(depo, "init", "-q", "-b", "main")
        hedef = os.path.join(depo, "tools", MODUL_ADI)
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(icerik)
        muafiyet_fiksturu_yaz(depo)   # defter hijyeni sentetik depoda da KOSAR
        _kos(depo, "add", "-A")
        r = subprocess.run([sys.executable, hedef, "--kendini-test"],
                           capture_output=True, text=True, errors="replace",
                           env=git_ortami())
        cikti = r.stdout + r.stderr
        dusen = set(re.findall(r"^\s*\[FAIL\]\s+(\S+?)\s", cikti, re.M))
        etiket = re.findall(r"^\s*\[(?:PASS|FAIL)\]\s+(\S+?)\s", cikti, re.M)
        return dusen, len(etiket), ("Traceback" in cikti)

    def kos(icerik):
        with tempfile.TemporaryDirectory(prefix="pruvo-mutasyon-") as d:
            return kos_kopya(icerik, os.path.realpath(d))

    hatalar = []
    t_dusen, t_sayi, t_cokme = kos(govde)
    print("TABAN: %d iddia, %d dusen, cokme=%s" % (t_sayi, len(t_dusen), t_cokme))
    if t_dusen or t_cokme:
        hatalar.append("TABAN temiz DEGIL: dusen=%s cokme=%s" % (sorted(t_dusen), t_cokme))

    beyan = [m[3] for m in MUTANTLAR if m[3]]
    if len(set(beyan)) != len(beyan):
        hatalar.append("IKI mutant AYNI iddiaya isaret ediyor: %s" % beyan)

    for ad, eski, yeni, bekle in MUTANTLAR:
        n = _on.count(eski) + _arka.count(eski)
        if n != 1:
            hatalar.append("%s: capa %d kez eslesti (TAM 1 olmali)" % (ad, n))
            print("  [CAPA-HATASI] %-22s eslesme=%d" % (ad, n))
            continue
        mutant = _on.replace(eski, yeni, 1) + _tablo + _arka.replace(eski, yeni, 1)
        dusen, sayi, cokme = kos(mutant)
        if cokme:
            hatalar.append("%s COKTU (cokme kirmiziyla karisir)" % ad)
        if sayi != t_sayi:
            hatalar.append("%s: iddia sayisi %d, taban %d" % (ad, sayi, t_sayi))
        if bekle is None:
            ok = not dusen
            if not ok:
                hatalar.append("KONTROL mutanti %s KIRMIZI yakti (dusen=%s) — batarya "
                               "ayirt edici degil" % (ad, sorted(dusen)))
            print("  [%s] %-22s dusen=%s (KONTROL: YESIL kalmali)"
                  % ("YESIL" if ok else "SAPMA", ad, sorted(dusen)))
        else:
            ok = {e for e in dusen if e.startswith("IDDIA-")} == {bekle}
            if not ok:
                hatalar.append("%s: dusen=%s, beyan={%s}" % (ad, sorted(dusen), bekle))
            print("  [%s] %-22s dusen=%s sayi=%d cokme=%s"
                  % ("OLDU" if ok else "SAPMA", ad, sorted(dusen), sayi, cokme))

    sonra_hash = _sha256_dosya(kaynak_yolu)
    print("CANLI DOSYA (git_ortami.py) sha256 once==sonra: %s"
          % (once_hash == sonra_hash))
    if once_hash != sonra_hash:
        hatalar.append("CANLI DOSYA DEGISTI — mutasyon yalniz KOPYAYA uygulanmali")
    for yol in komsu:
        tam = os.path.join(_kok, yol) if _kok else None
        sonra = _sha256_dosya(tam) if tam and os.path.exists(tam) else None
        esit = (komsu_once[yol] is not None and komsu_once[yol] == sonra)
        print("CANLI DOSYA (%s) sha256 once==sonra: %s"
              % (os.path.basename(yol), esit if komsu_once[yol] is not None
                 else "OLCULEMEDI (dosya/kok bulunamadi)"))
        if komsu_once[yol] is None:
            hatalar.append("%s sha256 OLCULEMEDI (fail-closed: 'dokunmadim' iddiasi "
                           "olculmeden gecemez)" % yol)
        elif not esit:
            hatalar.append("%s DEGISTI — batarya komsu canli dosyaya YAZMAMALI" % yol)
    print()
    if hatalar:
        print("MUTASYON BATARYASI KIRMIZI:")
        for h in hatalar:
            print("  - " + h)
        return 1
    oldurucu = len([m for m in MUTANTLAR if m[3]])
    print("MUTASYON BATARYASI YESIL: %d oldurucu mutant TEK KIRMIZI + beyana esit, "
          "%d KONTROL mutanti YESIL; iddia sayisi %d sabit; Traceback 0."
          % (oldurucu, len(MUTANTLAR) - oldurucu, t_sayi))
    return 0


def main():
    ap = __import__("argparse").ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="scrub davranisi + TEK KAYNAK (drift) + symlink nobeti")
    ap.add_argument("--mutasyon", action="store_true",
                    help="kabul bataryasinin mutasyon kanitini kostur (KOPYAYA uygular)")
    ap.add_argument("--ikinci-tanimlar", action="store_true", dest="ikinci",
                    help="betigin agacinda muafiyet-disi IKINCI scrub kumesi var mi")
    ap.add_argument("--kume-imzasi", metavar="YOL", default=None,
                    help="verilen dosyadaki scrub kumelerinin muafiyet imzasini yaz")
    args = ap.parse_args()
    if args.kendini:
        return _kendini_test()
    if args.mutasyon:
        return _mutasyon_bataryasi()
    if args.ikinci:
        bulgular, hata = ikinci_tanimlar()
        if hata:
            print("OLCULEMEDI (fail-closed): %s" % hata)
            return 2
        if not bulgular:
            print("IKINCI KUME YOK (tek kaynak korunuyor).")
            return 0
        print("IKINCI SCRUB KUMESI BULUNDU (%d):" % len(bulgular))
        for yol, adlar in bulgular:
            print("  %s  imza=%s  ad sayisi=%d" % (yol, kume_imzasi(adlar)[:16], len(adlar)))
        return 1
    if args.kume_imzasi:
        kayitlar = muafiyet_kaydi(args.kume_imzasi)
        if not kayitlar:
            print("kume YOK: %s" % args.kume_imzasi)
            return 1
        print("# DRIFT_MUAFIYETI'ne OLDUGU GIBI yapistirilabilir kayit(lar) "
              "(gerekceyi OLCUMLE doldur):")
        for kayit in kayitlar:
            print("    %r," % (kayit,))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
