#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""veri_kok.py — ekleme betikleri icin KOD KOKU ile VERI KOKU'nu AYIRIR.

NEDEN VAR (olculdu, S4 turu — sessiz-hata sinifi):
urun-ekle / printables-ekle / makerworld-ekle betiklerinde ROOT sabiti uzun sure
"/Users/okan/dev/pruvo" idi. Bu, kabul testinin bir WORKTREE'den betigi gercekten import
etmesini engelliyordu (yanindaki YENI modulleri degil, ana kopyadakileri arardi; ana kopyada
henuz olmayan bir modul -> ImportError). O yuzden ROOT `__file__`'dan turetildi. AMA bu tek
degisiklik VERI duzlemini de tasidi: betik bir worktree'den kosuldugunda artik WORKTREE'nin
urunler.json / .urun-kaynaklari.json / .urunler.lock dosyalarina yazardi. Urun verisinin TEK
yazari (MaCiT) bir worktree'den ekleme yaparsa is SESSIZCE YANLIS YERE gider: parti "STAGED"
gorunur, ana kopyada hicbir sey yoktur, worktree silinince kayit da gider. Ustelik kilit
(.urunler.lock) da ayri dosya olur -> ana kopyadaki paralel yazicilarla serilesme COKER.

COZUM (iki kok, tek kural):
  * KOD KOKU  = betigin KENDI konumu (tools/../). Modul yukleme HEP buradan yapilir ->
    worktree'de test edilebilirlik korunur.
  * VERI KOKU = deponun ANA KOPYASI. Git'e sorulur: `git rev-parse --git-common-dir` bagli
    (linked) bir worktree'de ANA kopyanin .git dizinini verir; ana kopyada ".git" doner.
    Boylece veri DAIMA tek yere (ana kopya) yazilir — sabit "/Users/okan/dev/pruvo" yolunu
    KODA GOMMEDEN (fresh checkout / CI / baska makine calisir).
  * Ikisi FARKLIYSA (= worktree'den kosuluyorsun) STDERR'e GURULTULU uyari basilir ve akis
    OLDURULMEZ (fail-loud, fail-open degil): is dogru yere gider ama neden oraya gittigi
    gorunur olur.
  * Git yoksa / burasi git deposu degilse (or. sentetik fikstur agaci) veri koku = kod koku;
    sessiz. Bu, kabul testlerinin sahte agaclarda kosabilmesi icindir.

COZUM SIRASI (18 Eyl, BaBa ek sarti — sandbox ANLAMI):
  (1) `PRUVO_VERI_KOK` env override — verilmisse VERI KOKU odur (dizin olmali; bos / dizin
      olmayan deger FAIL-CLOSED SystemExit, sessizce (2)/(3)'e DUSMEZ).
  (2) git ortak-dizin (yukaridaki kural: linked worktree -> ana kopya).
  (3) `__file__` (git yok / depo degil -> kod koku).
  NEDEN (1): araci gecici koke KOPYALAYIP sahte katalogda kosan testler (urun-silme-kapisi-
  test, ticari-hal-kapisi, d1-bayat-cikis-test ...) kokun NEREYE dustugunu sansa birakmamali:
  gecici dizin bir git agacinin icindeyse ya da CI'nin GIT_DIR mirasi sizarsa (2) ANA
  KOPYAYI dondurur -> test CANLI kataloga yazar. Bu yuzden kopyalayan test override'i
  KENDI gecici kokune kurar (`kum_ortami`). `veri_kok.py` YOKSA "eski davranisa dus"
  fallback'i YOKTUR (kor nobetciyi sessizce geri getirir): kopyalayan test dosyayi kopyalar,
  kopya kumesi de import'lardan TURETILIR (`kardes_kapanisi` / `kum_kur`) — elle liste
  bayatlar ([[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]]).

Saf/yan-etkisiz: dosya yazmaz, ag'a cikmaz; yalniz `git rev-parse` okur (enjekte edilebilir).
Istisna: `kum_kur` yalniz CAGIRANIN verdigi gecici dizine kopyalar (test yardimcisi).
"""
import os
import subprocess

ENV_AD = "PRUVO_VERI_KOK"


def _git_ortak_dizin(kok):
    """`git rev-parse --git-common-dir` ciktisi (str) ya da None (git yok / depo degil)."""
    try:
        r = subprocess.run(["git", "-C", kok, "rev-parse", "--git-common-dir"],
                           capture_output=True, text=True)
    except (OSError, ValueError):
        return None
    if r.returncode != 0:
        return None
    cikti = (r.stdout or "").strip()
    return cikti or None


def _override(kod_kok, ortam):
    """(1) `PRUVO_VERI_KOK` -> (kod_kok, veri_kok, uyari) ya da None (tanimsiz)."""
    ham = ortam.get(ENV_AD)
    if ham is None:
        return None
    if not ham.strip():
        raise SystemExit("!! %s TANIMLI ama BOS — veri koku belirsiz, FAIL-CLOSED DURDU "
                         "(sessizce git/__file__ kokune dusulmez)." % ENV_AD)
    veri = os.path.abspath(ham)
    if not os.path.isdir(veri):
        raise SystemExit("!! %s=%s bir DIZIN DEGIL — veri koku belirsiz, FAIL-CLOSED DURDU."
                         % (ENV_AD, ham))
    if os.path.normpath(veri) == os.path.normpath(kod_kok):
        return kod_kok, kod_kok, None
    uyari = ("⚠️  %s override: VERI (urunler.json) = %s   (kod = %s)\n"
             % (ENV_AD, veri, kod_kok))
    return kod_kok, veri, uyari


def cozumle(betik_dosyasi, _git=None, _ortam=None):
    """Doner (kod_kok, veri_kok, uyari). Sira: env override -> git ortak-dizin -> __file__.

    uyari: None (ayni kok) ya da STDERR'e basilacak metin (worktree / override tespit edildi).
    _git: yalniz test enjeksiyonu icin — kok alip git-common-dir metni/None dondurur.
    _ortam: yalniz test enjeksiyonu icin — os.environ yerine okunacak sozluk.
    """
    kod_kok = os.path.dirname(os.path.dirname(os.path.abspath(betik_dosyasi)))
    ov = _override(kod_kok, os.environ if _ortam is None else _ortam)
    if ov is not None:
        return ov
    git = _git or _git_ortak_dizin
    ortak = git(kod_kok)
    if not ortak:
        return kod_kok, kod_kok, None                    # git yok / depo degil -> tek kok
    if not os.path.isabs(ortak):
        ortak = os.path.join(kod_kok, ortak)
    # <ana-kopya>/.git  ->  <ana-kopya>
    ana = os.path.dirname(os.path.normpath(ortak))
    if not ana or os.path.normpath(ana) == os.path.normpath(kod_kok):
        return kod_kok, kod_kok, None                    # ana kopyadayiz -> sessiz
    uyari = (
        "\n" + "=" * 78 + "\n"
        "⚠️  DIKKAT — WORKTREE'DEN KOSULUYOR: KOD ile VERI ayri koklerde.\n"
        "    kod  (moduller)     : %s\n"
        "    VERI (urunler.json) : %s   <-- YAZMA BURAYA GIDER (ana kopya)\n"
        "    Sebep: urun verisinin TEK kopyasi ana depodadir; worktree'ye yazsaydik parti\n"
        "    STAGED gorunur ama ana kopyada HIC OLMAZDI (worktree silininde kayit da giderdi)\n"
        "    ve .urunler.lock ayrisip paralel yazicilarin serilesmesi COKERDI.\n"
        + "=" * 78 + "\n") % (kod_kok, ana)
    return kod_kok, ana, uyari


# ── ARACI GECICI KOKE KOPYALAYAN TESTLER ICIN (kopya kumesi TURETILIR, elle liste YOK) ──

def _kardes_adlari(metin, kaynak_tools):
    """Kaynak metnin `kaynak_tools/` kardeslerinden yukledigi .py dosya adlari.

    Iki kanit AST'den okunur: (a) `import x` / `from x import ...` (seviye 0) ve
    kaynak_tools/x.py var; (b) TAM degeri `<ad>.py` olan dizge sabiti (ornek
    `spec_from_file_location(.., os.path.join(dirname(__file__), "veri_kok.py"))`) ve
    dosya kaynak_tools'ta var. Fazla dahil etmek zararsizdir (kopya kumdadir); EKSIK
    kalirsa kopya ilk yuklemede FileNotFoundError ile GURULTULU coker (sessiz degil)."""
    import ast
    import re
    adlar = set()
    for dugum in ast.walk(ast.parse(metin)):
        if isinstance(dugum, ast.Import):
            for a in dugum.names:
                adlar.add(a.name.split(".")[0] + ".py")
        elif isinstance(dugum, ast.ImportFrom) and not dugum.level and dugum.module:
            adlar.add(dugum.module.split(".")[0] + ".py")
        elif isinstance(dugum, ast.Constant) and isinstance(dugum.value, str):
            if re.fullmatch(r"[A-Za-z0-9_.-]+\.py", dugum.value):
                adlar.add(dugum.value)
    return {a for a in adlar if os.path.isfile(os.path.join(kaynak_tools, a))}


def kardes_kapanisi(kaynaklar, kaynak_tools):
    """Verilen arac(lar)in kaynak_tools/ icindeki GECISLI kardes kapanisi (ad kumesi).

    kaynaklar: {ad: metin} — metin None ise kaynak_tools/ad okunur (mutant metin
    verilebilir; o zaman mutantin import'lari sayilir). Donen kume kaynaklarin KENDI
    adlarini icermez (onlari cagiran yazar)."""
    bekleyen = []
    for ad, metin in kaynaklar.items():
        if metin is None:
            with open(os.path.join(kaynak_tools, ad), encoding="utf-8") as f:
                metin = f.read()
        bekleyen.append(metin)
    kume = set()
    while bekleyen:
        for a in _kardes_adlari(bekleyen.pop(), kaynak_tools):
            if a in kume or a in kaynaklar:
                continue
            kume.add(a)
            with open(os.path.join(kaynak_tools, a), encoding="utf-8") as f:
                bekleyen.append(f.read())
    return kume


def kum_kur(hedef_tools, kaynaklar, kaynak_tools):
    """hedef_tools/ altina araclari (+ turetilmis kardes kapanisini) yazar/kopyalar.

    kaynaklar: {ad: metin|None} — None = kaynak_tools/ad oldugu gibi kopyalanir, metin =
    o metin (mutant) yazilir. Var olan hedef dosya EZILMEZ (cagiranin yazdigi korunur).
    Doner: kopyalanan kardes adlari (sirali)."""
    import shutil
    os.makedirs(hedef_tools, exist_ok=True)
    for ad, metin in kaynaklar.items():
        hedef = os.path.join(hedef_tools, ad)
        if metin is None:
            shutil.copy(os.path.join(kaynak_tools, ad), hedef)
        else:
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin)
    kardesler = sorted(kardes_kapanisi(kaynaklar, kaynak_tools))
    for a in kardesler:
        hedef = os.path.join(hedef_tools, a)
        if not os.path.exists(hedef):
            shutil.copy(os.path.join(kaynak_tools, a), hedef)
    return kardesler


def kum_ortami(kok, taban=None):
    """`taban` (vars. os.environ) kopyasi + `PRUVO_VERI_KOK=kok` — kopyalanan araci kosan
    alt surece verilir; kok ANA kopyaya/git'e SANSLA dusmez."""
    ortam = dict(os.environ if taban is None else taban)
    ortam[ENV_AD] = os.path.abspath(kok)
    return ortam
