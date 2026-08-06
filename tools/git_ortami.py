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


def git_ortami():
    """Miras alinan git baglami SILINMIS `os.environ` kopyasi (PATH vb. KORUNUR)."""
    ort = os.environ.copy()
    for ad in GIT_BAGLAM_DEGISKENLERI:
        ort.pop(ad, None)
    return ort


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
# 🔴 BEYAN EDILMIS SINIR (OLCULMEDI, uydurma degil — ACIKCA yazili): asagidaki bicimler
# YAKALANMAZ ve bugun bu depoda ORNEGI YOKTUR:
#   (a) adlarin AYRI AYRI ifadelerde silinmesi (`ort.pop("GIT_DIR"); ort.pop("GIT_WORK_TREE")`),
#   (b) adlarin CALISMA ZAMANINDA uretilmesi (`"GIT_" + "DIR"`, konfigurasyondan okuma),
#   (c) .py DISI dosyalar (kabuk kancalari, YAML) — bu nobet YALNIZ izlenen `.py` tarar.
# Olculen alternatif eksen ("dosyada 11 addan >=4'u dizi sabiti olarak geciyor") bugun
# AYNI 3 dosyayi buluyor (V1 == V2) -> ek yakalama getirmiyor, ek yanlis-pozitif riski
# getiriyor; bu yuzden DAR eksen secildi ve sinir burada BEYAN EDILDI.
_CIFT = frozenset(("GIT_DIR", "GIT_WORK_TREE"))


def scrub_kumeleri(kaynak):
    """<kaynak> icindeki AD'DAN BAGIMSIZ scrub kume literalleri -> [frozenset(adlar)].

    `SyntaxError` YUKARI BIRAKILIR: ayristirilamayan dosya 'temiz' SAYILAMAZ."""
    agac = ast.parse(kaynak)
    bulgular = []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):
            continue
        adlar = {e.value for e in dugum.elts
                 if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        if _CIFT <= adlar:
            bulgular.append(frozenset(adlar))
    return bulgular


def kume_imzasi(adlar):
    """Kume ICERIGINE bagli imza: kume DEGISIRSE muafiyet GECERSIZLESIR (path bazli
    genel bir 'bu dosyaya bakma' kacisi DEGILDIR)."""
    return hashlib.sha256("|".join(sorted(adlar)).encode("utf-8")).hexdigest()


# KAYITLI MUAFIYET — (yol, kume imzasi, gerekce). Muafiyet KUMENIN ICERIGINE baglidir:
# o dosyadaki kume tek ad bile degisirse imza tutmaz ve dosya KIRMIZI yanar.
DRIFT_MUAFIYETI = (
    ("tools/urunler-guard-provenans-test.py",
     "2ed8a9b7c1f5e7aef46fdbde842e6ddf3c0ffce1a3ac90af30c6f5747d9c0977",
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


def _muafiyet_kumesi():
    return {(yol, imza) for yol, imza, _g in DRIFT_MUAFIYETI}


def ikinci_tanimlar(kok=None):
    """Izlenen `.py` dosyalarinda IKINCI bir scrub kumesi arar (bu modul HARIC).

    Dondurur: (bulgular, hata); bulgular = [(yol, sirali ad listesi)].
    hata != None -> OLCULEMEDI (fail-closed: tarama yapilamadiysa 'ikinci tanim yok'
    HUKMU VERILMEZ). <kok> verilmezse BETIGIN kendi agaci olculur."""
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
    muaf = _muafiyet_kumesi()
    muaf_yollar = {y for y, _i in muaf}
    gorulen_yol = set()      # muafiyet yolu TARANAN AGACTA var mi
    kullanilan = set()       # muafiyet FIILEN bir kumeye denk geldi mi
    bulunan = []
    for yol in [y for y in r.stdout.split("\0") if y]:
        tam = os.path.join(kok, yol)
        if not yol.endswith(".py") or os.path.realpath(tam) == kendi:
            continue
        if yol in muaf_yollar:
            gorulen_yol.add(yol)
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
    # BAYAT MUAFIYET: yol TARANAN AGACTA VAR ama kayitli imza artik TUTMUYOR ->
    # kume degismis, gerekce yeniden olculmeli (fail-closed). Yol bu agacta HIC yoksa
    # (or. sentetik fikstur agaci) muafiyet KULLANILMAMIS sayilir, hata DEGILDIR —
    # hukum yalniz olculebilen agac icin verilir.
    bayat = sorted(a for a in muaf if a[0] in gorulen_yol and a not in kullanilan)
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

    # IDDIA-DRIFT (SENTETIK AGAC): tespit ekseni AD'DAN CAPASIZ mi? Fikstur GERCEK
    # dosyalara BAGIMLI DEGILDIR (repo temizlense de bu iddia ayakta kalir) ve dort
    # AYRI bicim tasir: `(...)` · `[...]` · BASKA AD · satir-ici `for` dongusu.
    # Ada capali ESKI desen bunlarin UCUNU birden kacirir -> MUT-DRIFT-ADA-CAPALI.
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
    # Tespit ekseni ADA CAPALI eski haline doner: `[...]`, BASKA AD ve satir-ici
    # bicimler kacar -> sentetik fikstur KIRMIZI yanar (bugun YESIL yakiyordu).
    ("MUT-DRIFT-ADA-CAPALI",
     "    agac = ast.parse(kaynak)\n"
     "    bulgular = []\n"
     "    for dugum in ast.walk(agac):\n"
     "        if not isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):\n"
     "            continue\n"
     "        adlar = {e.value for e in dugum.elts\n"
     "                 if isinstance(e, ast.Constant) and isinstance(e.value, str)}\n"
     "        if _CIFT <= adlar:\n"
     "            bulgular.append(frozenset(adlar))\n"
     "    return bulgular\n",
     "    bulgular = []\n"
     "    if re.search(r\"^\\s*GIT_BAGLAM_DEGISKENLERI\\s*=\\s*\\(\", kaynak, re.M):\n"
     "        bulgular.append(frozenset(_CIFT))\n"
     "    return bulgular\n",
     "IDDIA-DRIFT"),
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

    def kos_kopya(icerik, kok_d):
        depo = os.path.join(kok_d, "depo")
        os.makedirs(os.path.join(depo, "tools"))
        _kos(depo, "init", "-q", "-b", "main")
        hedef = os.path.join(depo, "tools", MODUL_ADI)
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(icerik)
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
    print("CANLI DOSYA sha256 once==sonra: %s" % (once_hash == sonra_hash))
    if once_hash != sonra_hash:
        hatalar.append("CANLI DOSYA DEGISTI — mutasyon yalniz KOPYAYA uygulanmali")
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
        with open(args.kume_imzasi, "r", encoding="utf-8") as f:
            kumeler = scrub_kumeleri(f.read())
        if not kumeler:
            print("kume YOK: %s" % args.kume_imzasi)
            return 1
        for adlar in kumeler:
            print("('%s', '%s', 'GEREKCE YAZ')  # %d ad: %s"
                  % (args.kume_imzasi, kume_imzasi(adlar), len(adlar), sorted(adlar)))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
