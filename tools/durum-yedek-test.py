#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — durum.py "7) YEDEK TAZELIGI" bolumu (bkz. durum-edge-test.py emsali).

NEDEN VAR: yedegin kendisi degil, YEDEGIN SESSIZCE DURMASI oldurucu (26 Tem olcumu:
yedekle.py dogru calisiyordu, 5 gun kimse kosmadi, mutasyon-kanitli skill dosyalari
yedekte bayat kaldi, hicbir sey uyarmadi). Pano bu bayatligi GORUNUR kilar. Uc sessiz-hata:
  (A) esik olu -- "bayat" hali hic yanmaz, pano hep yesil gorunur,
  (B) pano Drive yokken PATLAR -- her oturum basinda kirilir, kimse kosmaz olur,
  (C) pano SALT-OKUNUR sozlesmesini kirar -- drive_yolu.stl_dizini() cagirmak
      .stl-backup-dir'i DUZELTIR = DOSYA YAZAR (pano "hicbir sey yazmaz" diyor).
Ucunun de KIRMIZI-MUTASYON kaniti asagida.

⚪ ORTAM BAGIMLILIGI — `ps` (K4, 27 Tem): surec KIMLIK dogrulamasini olcen 5 kontrol dis
`ps` binary'sine baglidir. Bu adim deploy.yml'de BLOKLAYICI kosuyor ve `deploy: needs:
build` -> `ps` yoksa kirmizi yanmak TUM pruvo3d.com YAYININI durdururdu. Bu depoda
yanlis-pozitifin butun yayini durdurdugu bir vaka YASANDI ([[kapi-kapsam-eksen-secimi]]).
Karar: `ps` yoksa o kontroller GORUNUR ⚪ OLCULEMEDI olur (ozet satirinda sayilir) ve
cikis kodunu BOZMAZ; kapinin geri kalani BLOKLAYICI kalir.
🔴 SESSIZ YESILE CEVRILMEZ: kapi durum.py'nin KENDI fonksiyonuna degil `ps` BINARY'sinin
varligina bakar (ps_kullanilabilir). Yoksa `_surec_bilgisi`'ni olduren bir mutasyon
"OLCULEMEDI" kilifina girip kacardi — bunun kaniti 6h'deki mutant nobetcidir.

🔴 8. TUR (27 Tem) — IKI ONARIM, ikisi de AYNI hatanin duzeltmesi:
"nobetciyi, korumasi gereken kosulun ICINE koymak".
  (1) `ps` YOKKEN kimlik nobetcisinin KENDISI de ⚪ oluyordu -> `_surec_bilgisi`'ni ve
      pid-yeniden-kullanim tespitini olduren iki GERCEK mutant o makinede rc 0 / YESIL
      kaliyordu (olculdu). Onarim: 6h2 — nobet artik ENJEKTE EDILMIS SENTETIK `ps`
      fiksturuyle kosar, makinenin `ps` durumundan BAGIMSIZ ve DAIMA bloklayici.
  (2) UCUNCU ORTAM EKSENI: `git`. Bolum 8'deki `git init` korumasizdi -> git'siz
      makinede YAKALANMAMIS FileNotFoundError + rc 1 = TUM YAYIN DURUYORDU; ustelik
      panonun kendisi (durum.git) de cokuyordu. Onarim: git_ortami/git_kontrol ile
      `ps` ile AYNI doktrin (yok -> ⚪ [git], bozuk -> fail-closed KIRMIZI, var ->
      bloklayici) + durum.git() fail-soft + 8b sentetik gitsiz-PATH nobeti.
Ortam eksenlerinin SAYISI buraya YAZILMAZ (veri capasi): ozet her ekseni AYRI satirda
kendisi basar ve "EKSENSIZ OLCULEMEDI" ilan edilmemis her ⚪'yi yakalar.

Kosum:  python3 tools/durum-yedek-test.py
"""
import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
DURUM = os.path.join(TOOLS, "durum.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")
YEDEKLE = os.path.join(TOOLS, "yedekle.py")

# Alt kosum bayragi (K4 nobetcisi kendini `ps`siz PATH ile yeniden cagirir).
ALT_KOSUM = "--ps-yok-alt-kosum"

SONUC = []
OLCULEMEDI = []
PS_BAGIMLI = [0]          # ps'e bagli kontrol SAYISI (ilan; alt kosum bunu dogrular)
GIT_BAGIMLI = [0]         # `git`e bagli kontrol SAYISI (ayni ilan/dogrulama deseni)
ORTAM_BAGIMLI = [0]       # ps/git DISI ortam bagimliligi (yedeklenecek KAYNAK kumesi)
# DIS BINARY ORTAMINDAN BAGIMSIZ (sentetik PATH ile kosan) nobetlerin SAYISI. Bolum 9
# alt kosumun AYNI sayiyi raporlamasini ISTER -> bu nobetlerden biri ps_kontrol/
# git_kontrol'e sarilirsa (yani binary yoklugunda ⚪'ya kacarsa) alt kosumun sayisi
# duser ve kapi KIRMIZI yanar. Nobetcinin nobetcisi budur.
BAGIMSIZ_NOBET = [0]
EKSEN = {}                # eksen -> ⚪ sayisi ("ps" | "git" | "kaynak" | "fikstur" | "launchd")
PS_ORTAMI = ["var"]       # "var" | "yok" | "bozuk"  (bkz. ps_ortami)
GIT_ORTAMI = ["var"]      # "var" | "yok" | "bozuk"  (bkz. git_ortami)
LAUNCHD_BAGIMLI = [0]     # pid=1 (launchd/init) 'asili sahip' surrogatina bagli kontrol SAYISI
LAUNCHD_ORTAMI = ["?"]    # "var" | "yok"  (bkz. launchd_ortami)
# pid=1 mutant fiksturunun kilit YASI (sn). Kimlik-yok mutantinin pid=1'i 'asili' sanmasi
# (macOS'ta KIRMIZI) ANCAK pid=1 bu yastan YASLIYSA gorunur; genc pid=1'de (taze-boot CI
# runner) baslangic-yeniden-kullanim clause'u mutantta da pid=1'i eler -> fikstur mutanti
# OLCEMEZ. Fikstur kilit yasi (6h) ile launchd_ortami esigi TEK sabitle baglidir (drift YOK).
LAUNCHD_MUT_KILIT_YASI = 7200.0
# `ps` sorgusunun zaman siniri. CALISMA ANINDA okunur (durum.YEDEK_ZAMAN_ASIMI deseni)
# -> fikstur bunu gecici kisaltip "asili ps" yolunu SANIYE HARCAMADAN kanitlayabilir.
PS_SORGU_ZAMAN_ASIMI = [5.0]
GIT_SORGU_ZAMAN_ASIMI = [5.0]     # ayni desen, `git` siniflandiricisi icin
# ⚪ eksen ADLARI — ozet "EKSENSIZ" sayacini bunlarin DISINDA kalan her ⚪ besler
# (sebebi ILAN EDILMEMIS atlama = sessiz atlamaya en yakin hal, nobetci onu yakar).
BILINEN_EKSENLER = ("ps", "git", "kaynak", "fikstur", "launchd")


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def olculemedi(ad, ayrinti="", eksen="?"):
    """GORUNUR olculemedi: cikis kodunu BOZMAZ ama ozette SAYILIR (sessiz atlama YOK).

    `eksen`: HANGI ortam eksigi yuzunden olculemedi ("ps" | "kaynak" | "fikstur").
    🔴 NEDEN EKSEN: nobetci "ps VARKEN ⚪ SAYISI 0 olmali" der; eksen ayrimi olmadan
    ALAKASIZ bir eksenin ⚪'si o nobetciyi kirmiziya cevirir (CI taklidinde olctum:
    kaynak-kumesi eksigi ps nobetcisini yaniltip kapiyi kirmizi yakiyordu)."""
    OLCULEMEDI.append((ad, ayrinti, eksen))
    EKSEN[eksen] = EKSEN.get(eksen, 0) + 1
    print("  ⚪ ÖLÇÜLEMEDİ  " + ad + (("  — " + ayrinti) if ayrinti else ""))
    return None


def ps_ortami():
    """`ps` ORTAMININ UC HALI — durum.py'den BAGIMSIZ olcum:
      "yok"   -> binary PATH'te HIC YOK. Bu bir ORTAM EKSIKLIGIDIR (ariza degil):
                 ps'e bagli kontroller ⚪ OLCULEMEDI olur, deploy BLOKLANMAZ.
      "bozuk" -> binary PATH'te VAR ama calismiyor (rc!=0 / cikti BOS / asildi / OSError).
                 Bu bir ARIZADIR -> fail-closed KIRMIZI (sessiz yesile CEVRILMEZ).
      "var"   -> binary var ve calisiyor: kontroller NORMAL (bloklayici) kosar.

    🔴 NEDEN UC HAL, IKI DEGIL (6. tur onarimi): "yok" ile "bozuk" tek bir False'a
    katlaninca ikisi de AYNI muameleyi goruyordu ve kapi ancak 882. satirdaki
    "OLCULEMEDI 0" iddiasi sayesinde kirmizi yanabiliyordu. O iddiayi kosullu yapmak
    (K4'un cozumu) `bos`/`rc=1`/`asili` ps arizalarinin KIRMIZISINI da sessizce
    oldururdu — OLCULDU: 5 K3 fiksturunun 3'unun kirmizisi YALNIZ o satirdan geliyordu.
    Ayrim ORTAM ekseninde yapilir: eksik bagimlilik yayini durdurmaz, BOZUK bagimlilik
    durdurur.

    🔴 NEDEN durum._surec_bilgisi KULLANILMAZ: kapiyi olculen kodun kendi fonksiyonuna
    baglamak SESSIZ YESIL uretir — o fonksiyonu olduren bir mutasyon "ps yokmus"
    goruntusu verip 5 kontrolu birden OLCULEMEDI'ye kacirirdi. Burada yalniz ORTAM
    sorgulanir; kodun dogrulugu ayri (6h mutant nobetcisi)."""
    yol = shutil.which("ps")
    if not yol:
        return "yok"
    try:
        p = subprocess.run([yol, "-p", str(os.getpid()), "-o", "etime=,comm="],
                           capture_output=True, text=True,
                           timeout=PS_SORGU_ZAMAN_ASIMI[0])
    except (OSError, subprocess.SubprocessError):
        return "bozuk"                       # asildi / calistirilamadi -> ARIZA
    if p.returncode != 0 or not (p.stdout or "").strip():
        return "bozuk"                       # rc!=0 ya da cikti BOS -> ARIZA
    return "var"


def ps_kontrol(ad, ok, ayrinti=""):
    """`ps`e BAGIMLI kontrol: ortam "var" ise NORMAL kontrol (kirmizi yanabilir),
    "yok"/"bozuk" ise GORUNUR ⚪ OLCULEMEDI. "bozuk" halinde kapinin KIRMIZISI ayrica
    bolum 9'daki ORTAM kontrolunden gelir (fail-closed). Bkz. modul basligi K4."""
    PS_BAGIMLI[0] += 1
    if PS_ORTAMI[0] == "var":
        return kontrol(ad, ok, ayrinti)
    return olculemedi(ad, "`ps` ortami '%s' — surec kimligi olculemez" % PS_ORTAMI[0],
                      eksen="ps")


def bagimsiz_kontrol(ad, ok, ayrinti=""):
    """DIS BINARY ORTAMINDAN BAGIMSIZ nobet — DAIMA bloklayici, ASLA ⚪ olmaz.

    🔴 NEDEN AYRI SARMALAYICI (8. tur, curutucu olcumu): 7. turda kimlik nobetlerinin
    HEPSI `ps_kontrol` ile sariliydi; `ps` PATH'te yokken nobetcinin KENDISI de ⚪
    oluyordu -> `_surec_bilgisi`'ni ve pid-yeniden-kullanim tespitini olduren IKI
    GERCEK mutant o makinede rc 0 / YESIL kaliyordu (olculdu: 2 sessiz yesil hucre).
    Ders: "nobetciyi, koruması gereken kosulun ICINE koymak" = nobetciyi kendi kor
    noktasina hapsetmek. Cozum: bu nobetler SENTETIK bir `ps` fiksturuyle (kendi
    PATH'iyle) kosar, yani makinede `ps` olsa da olmasa da bozuk olsa da AYNI olcumu
    yapar.

    ⚠️ AD ISARETI ZORUNLU ("[sentetik…"): bolum 9 alt kosumun CIKTISINDA bu isareti
    sayar. SAYAC TEK BASINA YETMEZ — olculdu: bir nobeti ps_kontrol'e sarmak sayaci
    ANA ve ALT kosumda ESIT dusurur, yani sayac karsilastirmasi mutanti KACIRIR.
    Isaret sayesinde alt kosumda "⚪ … [sentetik…" satiri BELIRIR ve nobetci yakar."""
    if not ad.startswith("[sentetik"):
        ad = "[sentetik] " + ad
    BAGIMSIZ_NOBET[0] += 1
    return kontrol(ad, ok, ayrinti)


def git_ortami():
    """`git` ORTAMININ UC HALI — ps_ortami ile AYNI doktrin, AYRI eksen.

      "yok"   -> binary PATH'te HIC YOK: ORTAM EKSIKLIGI. git'e bagli kontroller
                 ⚪ OLCULEMEDI olur, deploy BLOKLANMAZ.
      "bozuk" -> PATH'te VAR ama calismiyor (rc!=0 / cikti BOS / asildi / OSError):
                 ARIZA -> fail-closed KIRMIZI (bolum 9'daki ORTAM nobetcisinden gelir).
      "var"   -> normal: git'e bagli kontroller BLOKLAYICI kosar.

    🔴 NEDEN VAR (8. tur, curutucu UCUNCU ekseni olctu): `git` PATH'te yokken bu adim
    rc 1 + YAKALANMAMIS FileNotFoundError veriyordu (bolum 8'deki `git init`), yani
    dalin kapatmak icin var oldugu ariza sinifinin (dis binary yoklugu TUM YAYINI
    durduruyor) AYNISI acikti. Kod git'sizligi zaten BILIYORDU — yedekle.ana_calisma_agaci
    OSError'i yutuyor, bolum 9 `if git_yolu:` ile korumali — ama bolum 8 korumasizdi.

    🔴 NEDEN BOZUK GIT KIRMIZI: git VAR ama calismiyorsa yedekle.ana_calisma_agaci
    sessizce __file__ tabanina duser -> ROOT WORKTREE olur. Bu, 26 Tem'de olculen
    "sahte tazelik" (F1) hatasinin ta kendisidir: worktree'de gitignore'lu dosyalar
    yedeklenmeden TAM GUVEN damgasi atilir. Sessiz veri kaybi -> fail-closed.

    🔴 NEDEN yedekle.ana_calisma_agaci KULLANILMAZ: kapiyi olculen fonksiyona baglamak
    SESSIZ YESIL uretir (o fonksiyonu olduren mutasyon "git yokmus" kilifina girer).
    Burada yalniz ORTAM sorgulanir."""
    yol = shutil.which("git")
    if not yol:
        return "yok"
    try:
        p = subprocess.run([yol, "--version"], capture_output=True, text=True,
                           timeout=GIT_SORGU_ZAMAN_ASIMI[0])
    except (OSError, subprocess.SubprocessError):
        return "bozuk"
    if p.returncode != 0 or not (p.stdout or "").strip():
        return "bozuk"
    return "var"


def git_kontrol(ad, ok, ayrinti="", ek_ortam=True, ek_ayrinti=""):
    """`git`e BAGIMLI kontrol: ortam "var" ise NORMAL (kirmizi yanabilir), aksi halde
    GORUNUR ⚪ OLCULEMEDI [git]. "bozuk" halinde kapinin KIRMIZISI bolum 9'daki ORTAM
    nobetcisinden gelir (fail-closed). `ek_ortam` False ise (or. yedeklenecek KAYNAK
    kumesi yok) ⚪ KAYNAK ekseninde yazilir — eksenler KARISTIRILMAZ."""
    GIT_BAGIMLI[0] += 1
    if GIT_ORTAMI[0] != "var":
        return olculemedi(ad, "`git` ortami '%s' — ana calisma agaci COZULEMEZ"
                          % GIT_ORTAMI[0], eksen="git")
    if not ek_ortam:
        ORTAM_BAGIMLI[0] += 1
        return olculemedi(ad, ek_ayrinti or "ortam eksik", eksen="kaynak")
    return kontrol(ad, ok, ayrinti)


def _etime_yerel(metin):
    """ps ETIME bicimini ([[DD-]HH:]MM:SS) saniyeye cevirir. Cozulemezse None.

    🔴 NEDEN durum._etime_saniye DEGIL (BAGIMSIZ kopya): launchd_ortami ORTAM sorgusudur;
    onu olculen kodun (durum.py) bir yardimcisina baglamak, o yardimciyi olduren bir
    mutasyonun "launchd yokmus" kilifina girip pid=1 nobetini SESSIZ ⚪'ya kacirmasina
    izin verirdi (ps_ortami/git_ortami ile AYNI doktrin: ortam bagimsiz sorgulanir)."""
    metin = (metin or "").strip()
    gun = 0
    if "-" in metin:
        g, _sep, metin = metin.partition("-")
        if not g.isdigit():
            return None
        gun = int(g)
    parcalar = metin.split(":")
    if not parcalar or not all(p.isdigit() for p in parcalar):
        return None
    sayilar = [int(p) for p in parcalar]
    if len(sayilar) == 2:
        sa, dk, sn = 0, sayilar[0], sayilar[1]
    elif len(sayilar) == 3:
        sa, dk, sn = sayilar
    else:
        return None
    return gun * 86400 + sa * 3600 + dk * 60 + sn


def launchd_ortami():
    """pid=1 (launchd/init) fiksturu 'asili sahip' surrogatini SUNUYOR mu? "var" | "yok".

    Kimlik-yok mutantinin (6h) pid=1'i YANLISLIKLA 'asili' siniflamasi -> yani mutanti
    KIRMIZI yakabilmemiz- ANCAK pid=1:
      (a) canli,  (b) komutu python DEGIL,
      (c) gecen suresi LAUNCHD_MUT_KILIT_YASI'ndan (fikstur kilit yasi) BUYUK
          -> baslangic-yeniden-kullanim clause'u onu BAGIMSIZ elemez
    ise gorunur. macOS'ta launchd gunlerdir canli -> (a)(b)(c) tutar, mutant KIRMIZI.
    Taze-boot CI runner'inda (Ubuntu) pid=1 (systemd) DAKIKALAR oncedir -> (c) TUTMAZ:
    baslangic clause'u mutantta da pid=1'i 'yarim' yapar, fikstur mutanti OLCEMEZ. Bu bir
    ORTAM EKSIKLIGIDIR (ps yoklugu ile AYNI sinif) -> ⚪ OLCULEMEDI [launchd], KIRMIZI DEGIL.

    Tespit `sys.platform`/`platform.system()` DEGIL, YETENEGE gore (CI'da bir Linux'ta
    pid=1 2 saatten yasliysa fikstur GECERLIDIR ve orada da kosar).
    🔴 durum._surec_bilgisi/_surec_canli KULLANILMAZ (ps_ortami doktrini): kapiyi olculen
    koda baglamak SESSIZ YESIL uretir; burada YALNIZ ORTAM sorgulanir (kendi `ps`+parser)."""
    yol = shutil.which("ps")
    if not yol:
        return "yok"                          # `ps` yok -> pid=1 olculemez (ps ekseniyle ayni sinif)
    try:
        os.kill(1, 0)                         # pid=1 canli mi (POSIX init/launchd; ProcessLookupError -> yok)
    except ProcessLookupError:
        return "yok"
    except (PermissionError, OSError):
        pass                                  # var ama baska kullanici -> kimlige `ps` ile bak
    try:
        p = subprocess.run([yol, "-p", "1", "-o", "etime=,comm="],
                           capture_output=True, text=True,
                           timeout=PS_SORGU_ZAMAN_ASIMI[0])
    except (OSError, subprocess.SubprocessError):
        return "yok"
    satir = (p.stdout or "").strip()
    if p.returncode != 0 or not satir:
        return "yok"
    parcalar = satir.split(None, 1)
    gecen = _etime_yerel(parcalar[0])
    komut = parcalar[1].strip() if len(parcalar) > 1 else ""
    if gecen is None:
        return "yok"
    if komut and "python" in os.path.basename(komut).lower():
        return "yok"                          # pid=1 python ise fikstur anlamsiz (fail-open)
    if gecen < LAUNCHD_MUT_KILIT_YASI - 2.0:  # taze-boot: baslangic clause pid=1'i BAGIMSIZ eler
        return "yok"
    return "var"


def launchd_kontrol(ad, ok, ayrinti=""):
    """pid=1 (launchd/init) 'asili sahip' surrogatina BAGIMLI kontrol: ortam "var" ise
    NORMAL bloklayici (macOS'ta mutant KIRMIZI yanar); "yok" ise GORUNUR ⚪ OLCULEMEDI
    [launchd] (taze-boot CI runner / `ps` yok / pid=1 python — yayin BLOKLANMAZ).
    ps_kontrol/git_kontrol ekseninin BIREBIR deseni. Bkz. launchd_ortami."""
    LAUNCHD_BAGIMLI[0] += 1
    if LAUNCHD_ORTAMI[0] == "var":
        return kontrol(ad, ok, ayrinti)
    return olculemedi(ad, "pid=1 (launchd/init) 'asili' surrogati bu ortamda yok "
                          "(taze-boot runner / ps yok / pid=1 python) — mutant olculemez",
                      eksen="launchd")


def kaynak_ortami():
    """Bu makinede YEDEKLENECEK KAYNAK var mi? "var" | "yok" — ORTAM sorgusu.

    🔴 NEDEN VAR (27 Tem, 6. tur; CI TAKLIDINDE YAKALANDI): K5 canli-imza olcumunun
    GERCEK (enjeksiyonsuz) ucunu kosulsuz bloklayici yapmak, CI fresh checkout'unda
    kapiyi KIRMIZI yakiyordu -> `deploy: needs: build` zinciri TUM pruvo3d.com yayinini
    durdururdu. Sebep: CI'da HOME BOS (~/.claude YOK) ve yedeklenen 4 repo dosyasi
    gitignore'lu (izlenen degil) -> olculecek KAYNAK KUMESI hic yoktur, imza tanim
    geregi None doner. Bu bir ARIZA DEGIL, ortam eksikligidir (ps ile ayni sinif).

    🔴 NEDEN durum._canli_kaynak_imzasi KULLANILMAZ: kapiyi olculen fonksiyona baglamak
    SESSIZ YESIL uretir (o fonksiyonu olduren mutasyon "kaynak yokmus" kilifina girer).
    Burada yalniz ORTAM sorgulanir: yedekle.py'nin ilan ettigi MEMORY/SKILLS dizinleri
    ve REPO_BEKLENEN dosyalarindan HERHANGI BIRI diskte var mi?"""
    try:
        yedekle = modul_yukle(os.path.join(TOOLS, "yedekle.py"), "yedekle_ortam")
    except Exception:
        return "yok"
    if os.path.isdir(yedekle.MEMORY) or os.path.isdir(yedekle.SKILLS):
        return "var"
    for ad in yedekle.REPO_BEKLENEN:
        if os.path.isfile(os.path.join(yedekle.ROOT, ad)):
            return "var"
    return "yok"


def ortam_kontrol(ad, ortam_var, ok, ayrinti=""):
    """ORTAMA bagli kontrol: ortam varsa NORMAL (bloklayici), yoksa GORUNUR ⚪."""
    ORTAM_BAGIMLI[0] += 1
    if ortam_var:
        return kontrol(ad, ok, ayrinti)
    return olculemedi(ad, "yedeklenecek KAYNAK kumesi bu makinede yok "
                          "(fresh checkout / bos HOME) — olculemez", eksen="kaynak")


def canli_olcum(adaylar, kok=None):
    """`durum._canli_kaynak_imzasi` enjeksiyonu icin olcum sozlugu uretir (K5).
    `kok=None` -> damga/olcum agac karsilastirmasi ATLANIR (fikstur damgalarinda
    `kok` alani zaten yok); kok verilirse agac-uyusmazligi yolu olculur."""
    return {"kok": kok, "adaylar": [dict(a) for a in adaylar]}


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mutant_yaz(dizin, eski, yeni, ad="durum_mutant.py"):  # noqa: D401 (bkz. asagi)
    """durum.py'nin mutasyonlu kopyasi. Capa yoksa RuntimeError (bayat capa sessiz gecmesin).
    ⚠️ drive_yolu.py mutantin YANINA KOPYALANMAZ: o modulun ROOT'u GERCEK repoyu gosterir,
    mutant onu cagirsa gercek .stl-backup-dir'e yazardi."""
    with open(DURUM, encoding="utf-8") as f:
        kaynak = f.read()
    if eski not in kaynak:
        raise RuntimeError("MUTASYON CAPASI BULUNAMADI (durum.py degismis): %r" % eski)
    hedef = os.path.join(dizin, ad)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(eski, yeni, 1))
    return hedef


def damga_kur(backup, yas_saniye, **ekstra):
    """yas_saniye NEGATIF verilirse damga GELECEK tarihli olur (F3 senaryosu)."""
    os.makedirs(backup, exist_ok=True)
    veri = {"surum": 2, "zaman": time.time() - yas_saniye, "iso": "TEST", "tam": True,
            "eksik": [], "memory": 0, "skills": 0, "repo": 4}
    veri.update(ekstra)
    with open(os.path.join(backup, ".son-yedek.json"), "w") as f:
        json.dump(veri, f)
    return backup


# ============================================================================
# YEDEKLE.PY 3 GUVENCE — CI-KOSULABILIR DAVRANISSAL NOBET (bkz. bolum 10 / main)
# ----------------------------------------------------------------------------
# yedekle.py'nin sessiz-yedek-kaybini onleyen UC guvencesi vardi ki YALNIZ
# tools/yedekle-test.py'de olculuyordu; o test ise CI-MUAF (taze runner'da bos
# HOME + gitignore'lu dosyalar olmadigi icin env-bagimli kirmizi yanar). Sonuc:
# bu ucunden HERHANGI biri gelecekte bir regresyonla kalkarsa GERCEK CI'da hicbir
# nobetci kirmizi yanmaz. Bu bolum o bosluğu, bu dosya (deploy.yml'de zaten
# BLOKLAYICI kosan durum-yedek-test.py) icinde DAVRANISSAL + ENV-BAGIMSIZ olarak
# kapatir. Guvenceler:
#   (a) flock          -> kilit_al'daki fcntl.flock(LOCK_EX|LOCK_NB) paralel
#                         yedekleri serilestirir.
#   (b) damga-finally  -> `bitti=` basari izi YALNIZ basari yolunda; istisnada
#                         `hata=` (finally sahte-yesil vermez → [[damga-finally-tuzagi]]).
#   (c) cikis-damgasi  -> .son-yedek.json en sonda, YALNIZ kosum tamamlaninca.
#
# 🔴 NEDEN DAVRANISSAL (yapisal/regex DEGIL — [[mimar-kapi-parser-taklidi]]): her
# guvence yedekle.py'nin ILGILI KOD YOLUNU tam-izole bir kum havuzunda (sahte HOME
# + sahte git deposu + drive_yolu STUB'u) GERCEKTEN kosarak olculur. Base kontrol
# yalnizca GOZLENEN DAVRANISA (atladi mi / iz `bitti=` mi / damga tazelendi mi)
# bakar; degisken adi/yorum/satir tasima gibi MESRU refaktorler davranisi
# degistirmez -> yanlis-pozitif YOK (negatif fiksturler bunu kanitlar). Vakum
# olmadigini POZITIF MUTANT ispatlar: guvenceyi KOPYADAN kaldirinca base kontrolun
# gozledigi davranis TERSINE doner.
#
# 🔴 CI-BAGIMSIZLIK: kum havuzu her seyi tempdir'de kurar (ortam["HOME"]=sahte ev);
# gercek runner'in bos HOME'u / gitignore'lu dosyalarin yoklugu SONUCU ETKILEMEZ.
# git YOKSA bile yedekle.ana_calisma_agaci taban=kok'a duser (OSError -> fallback),
# yani kum havuzu git'siz runner'da da kosar.

# COKME injeksiyonu (yedekle-test 13g deseni): memory kopyalandiktan SONRA, skills
# kopyalanmadan ONCE gercek bir istisna at -> kosum ORTADA yarim kalir. Anchor
# _yedekle icinde TEKIL (skills_yaz'daki yazilan=0'dan `if os.path.isdir(SKILLS):`
# ile ayrilir). Base + mutant + refaktor AYNI cokme ile kosar; tek fark guvence.
_COKME_CAPA = "    yazilan = 0\n    if os.path.isdir(SKILLS):"
_COKME = ('    raise RuntimeError("TEST: kosum ortasinda cokme")\n'
          "    yazilan = 0\n    if os.path.isdir(SKILLS):")


def _yedekle_izole_ortam(td, yb, memory_adet=8, skills_adet=4):
    """yedekle.py icin TAM IZOLE kosum ortami (gercek HOME/Drive'a DOKUNMAZ).
    Doner: {kok, betik, ev, hedef, kilit, ortam}."""
    kok = os.path.join(td, "repo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(YEDEKLE, os.path.join(kok, "tools", "yedekle.py"))
    pruvo = os.path.join(td, "drive", "Pruvo")
    os.makedirs(pruvo)
    with open(os.path.join(kok, "tools", "drive_yolu.py"), "w") as f:
        f.write('DESEN = "/olmayan-mount/*/STL"\nCFG = "/olmayan/.stl-backup-dir"\n'
                'def stl_dizini(sessiz=False):\n    return %r\n'
                'def pruvo_dizini(sessiz=False):\n    return %r\n'
                % (os.path.join(pruvo, "STL"), pruvo))
    try:                                    # git YOKSA fallback taban=kok yeter (env-bagimsiz)
        subprocess.run(["git", "-C", kok, "init", "-q"], capture_output=True)
    except OSError:
        pass
    for ad in yb.REPO_BEKLENEN:
        with open(os.path.join(kok, ad), "w") as f:
            f.write("izole test icerigi: %s\n" % ad)
    ev = os.path.join(td, "ev")
    mem = os.path.join(ev, ".claude", "projects", "-Users-okan-dev-pruvo", "memory")
    sk = os.path.join(ev, ".claude", "skills", "ornek-skill")
    os.makedirs(mem)
    os.makedirs(sk)
    for i in range(memory_adet):
        with open(os.path.join(mem, "not-%03d.md" % i), "w") as f:
            f.write("hafiza %d\n" % i)
    for i in range(skills_adet):
        with open(os.path.join(sk, "adim-%03d.md" % i), "w") as f:
            f.write("skill %d\n" % i)
    ortam = dict(os.environ)
    ortam["HOME"] = ev
    return {"kok": kok, "betik": os.path.join(kok, "tools", "yedekle.py"),
            "ev": ev, "hedef": os.path.join(pruvo, "backup"),
            "kilit": os.path.join(kok, yb.KILIT_ADI), "ortam": ortam}


def _yedekle_kos(o, *bayraklar):
    return subprocess.run([sys.executable, o["betik"]] + list(bayraklar),
                          capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])


def _betik_uygula(o, degisimler):
    """o["betik"] (kopya yedekle.py) kaynagina anchor-tabanli degisim uygular.
    degisimler: (eski, yeni) ya da (eski, yeni, adet) — adet None -> HEPSI (rename).
    Capa yoksa RuntimeError (bayat capa sessizce gecmesin; yedekle-test.py deseni)."""
    with open(o["betik"], encoding="utf-8") as f:
        gov = f.read()
    for d in degisimler:
        eski, yeni = d[0], d[1]
        adet = d[2] if len(d) > 2 else 1
        if eski not in gov:
            raise RuntimeError(
                "MUTASYON/REFAKTOR CAPASI BULUNAMADI (yedekle.py degismis): %r" % eski)
        gov = gov.replace(eski, yeni) if adet is None else gov.replace(eski, yeni, adet)
    with open(o["betik"], "w", encoding="utf-8") as f:
        f.write(gov)


def _damga_zaman(hedef, damga_adi):
    try:
        with open(os.path.join(hedef, damga_adi), encoding="utf-8") as f:
            return json.load(f).get("zaman")
    except (OSError, ValueError):
        return None


def _kilit_izi(kilit_yolu):
    try:
        with open(kilit_yolu, encoding="utf-8", errors="replace") as f:
            return f.read(256).strip()
    except OSError:
        return ""


def _senaryo_flock(yb, degisimler):
    """Kilit BASKASINDAYKEN `--gerekliyse` kosumu ATLAMALI (serilestirme).
    degisimler betik'e uygulanir (mutant/refaktor). Doner: (atladi, bitti_yazdi)."""
    with tempfile.TemporaryDirectory() as td:
        o = _yedekle_izole_ortam(td, yb)
        if degisimler:
            _betik_uygula(o, degisimler)
        kilitci = open(o["kilit"], "a+")                 # "kosan yedek" taklidi
        fcntl.flock(kilitci, fcntl.LOCK_EX)              # kilit GERCEKTEN tutuluyor
        kilitci.write(yb._sahip_imzasi(time.time(), pid=999999))
        kilitci.flush()
        try:
            r = _yedekle_kos(o, "--gerekliyse")
        finally:
            fcntl.flock(kilitci, fcntl.LOCK_UN)
            kilitci.close()
        atladi = (r.returncode == 0 and "yedek ATLANDI" in r.stdout
                  and "bitti ->" not in r.stdout)
        return atladi, ("bitti ->" in r.stdout)


def _senaryo_cokme(yb, ekstra_degisimler):
    """Ilk kosum basarili (damga T0), sonra kosum ORTADA coker. ekstra_degisimler
    COKME'ye EK uygulanir. Doner: dict(r0_ok, T0, damga_degisti, iz_bitti, iz_hata, cokdu)."""
    with tempfile.TemporaryDirectory() as td:
        o = _yedekle_izole_ortam(td, yb)
        r0 = _yedekle_kos(o)                             # saglam kosum -> damga T0 + iz `bitti=`
        T0 = _damga_zaman(o["hedef"], yb.DAMGA_ADI)
        time.sleep(0.02)                                 # T1 != T0 ayirt edilebilsin
        _betik_uygula(o, [(_COKME_CAPA, _COKME)] + list(ekstra_degisimler))
        r1 = _yedekle_kos(o)                             # kosum ORTADA coker
        T1 = _damga_zaman(o["hedef"], yb.DAMGA_ADI)
        iz = _kilit_izi(o["kilit"])
        return {"r0_ok": "bitti ->" in r0.stdout, "T0": T0,
                "damga_degisti": (T0 is not None and T1 != T0),
                "iz_bitti": "bitti=" in iz, "iz_hata": "hata=" in iz,
                "cokdu": r1.returncode != 0}


# ============================================================================
# BOLUM 11 FIKSTURU — IMZA KAPSAMI = KOPYA PLANI (glob fail-open nobeti)
# ----------------------------------------------------------------------------
# 🔴 NEDEN VAR (31 Tem 2026, OLCULDU): yedekle.kaynak_imzasi() ek kokleri
# `os.path.join(ev, giris)` ile kuruyordu; EK_EVLER'deki GLOB'lu girisler
# ("olcum/*.py") ne isfile ne isdir oldugu icin SESSIZCE atlaniyordu. Olcum: imza
# 767 dosya / kopya plani 2642 dosya; farkin 1934'u glob kapsami. Sonuc: o dosyalar
# degistiginde imza KIMILDAMIYOR, `--gerekliyse` "guncel" deyip yedegi ATLIYOR =
# fail-open, sessiz veri kaybi. Onarim: imza da dogrulama da kopya da yedek_plani()
# TEK tanimindan turer. Bu bolum onu DAVRANISSAL olcer (yapisal/regex DEGIL):
# gercek yedekle.py'yi tam-izole kum havuzunda kosturur ve kararina bakar.
#
# mtime BILEREK ESKIYE cekilir: mtime ekseni "degisiklik yok" derken karari YALNIZ
# imza ekseni verebilir -> nobet tam olculmek istenen sinifi olcer.


def _glob_girisi(yb):
    """EK_EVLER'de GLOB tasiyan ILK (ev_adi, giris). Fikstur sabit YAZMAZ, KONFIGU OKUR.
    Yoksa (None, None) -> senaryo artik gercek konfigurasyonu temsil etmiyordur ve
    bunu KIRMIZI soyler (⚪'ya KACMAZ; ⚪ butcesi bolum 10'da tam 1'dir)."""
    for ev_adi in sorted(yb.EK_EVLER):
        for giris in yb.EK_EVLER[ev_adi]:
            if "*" in giris or "?" in giris:
                return ev_adi, giris
    return None, None


# Kum havuzundaki yedekle.py KOPYASINI ayni sahte HOME ile olcen surucu: imza +
# plan uzunlugu + plandaki kaynak yollari. (Ana surecte import etmek GERCEK HOME'u
# olcerdi; alt surec ortam["HOME"] ile kosar.)
_IMZA_SURUCU = (
    "import importlib.util, json, os\n"
    "yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'yedekle.py')\n"
    "spec = importlib.util.spec_from_file_location('yedekle_olcum', yol)\n"
    "m = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
    "plan = m.yedek_plani(False)\n"
    "print(json.dumps({'imza': m.kaynak_imzasi(False), 'plan': len(plan),\n"
    "                  'kaynaklar': [k for k, _h in plan]}))\n")


def _imza_olc(o):
    """Kum havuzu kopyasinin imza/plan olcumu. Doner: {"imza","plan","kaynaklar"}."""
    surucu = os.path.join(o["kok"], "imza_surucu.py")
    with open(surucu, "w", encoding="utf-8") as f:
        f.write(_IMZA_SURUCU)
    r = subprocess.run([sys.executable, surucu], capture_output=True, text=True,
                       env=o["ortam"], cwd=o["kok"])
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"imza": None, "plan": -1, "kaynaklar": [],
                "hata": (r.stderr or "")[-200:]}


def _senaryo_glob_kapsam(yb, degisimler):
    """GLOB kapsamindaki dosya DEGISINCE `--gerekliyse` yedegi ATLAMAMALI.

    Kurulum: sahte HOME + sahte Drive + EK_EVLER'den OKUNAN adla bir kardes ev
    (kok'un KARDESI: yedekle.ev_yollari() onu boyle cozer). Sira:
      r0  TAM yedek  -> damga + hedefte kopya
      degisiklik     -> glob kapsamindaki dosya YENI icerik, mtime ESKIYE cekili
      r1  --gerekliyse -> ATLAMAMALI (yedeklemeli), kopya TAZELENMELI
      r2  --gerekliyse -> degisiklik yokken ATLAMALI (yanlis-pozitif yok)
    Doner: olcum dict'i; EK_EVLER'de glob yoksa None."""
    ev_adi, desen = _glob_girisi(yb)
    if not ev_adi:
        return None
    with tempfile.TemporaryDirectory() as td:
        o = _yedekle_izole_ortam(td, yb)
        ev = os.path.join(td, ev_adi)
        os.makedirs(os.path.join(ev, ".git", "hooks"))     # ev_yollari .git ARAR
        alt = os.path.dirname(desen)
        dizin = os.path.join(ev, alt) if alt else ev
        os.makedirs(dizin, exist_ok=True)
        ad = "kapsam-fikstur" + os.path.splitext(desen)[1]
        dosya = os.path.join(dizin, ad)
        ILK = "# glob kapsami fiksturu\n"
        YENI = "# glob kapsami fiksturu -- ICERIK DEGISTI (bilerek daha uzun satir)\n"
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(ILK)
        if degisimler:
            _betik_uygula(o, degisimler)
        r0 = _yedekle_kos(o)                               # TAM yedek
        d0 = _imza_olc(o)
        kopya = os.path.join(o["hedef"], yb.EK_KLASOR, "evler", ev_adi,
                             os.path.join(alt, ad) if alt else ad)
        ilk_kopyalandi = os.path.isfile(kopya)
        with open(dosya, "w", encoding="utf-8") as f:      # DEGISIKLIK
            f.write(YENI)
        eski = time.time() - 7200                          # mtime ekseni SUSTURULUR
        os.utime(dosya, (eski, eski))
        d1 = _imza_olc(o)
        r1 = _yedekle_kos(o, "--gerekliyse")
        try:
            with open(kopya, encoding="utf-8") as f:
                kopya_icerik = f.read()
        except OSError:
            kopya_icerik = ""
        r2 = _yedekle_kos(o, "--gerekliyse")               # degisiklik YOK
        # realpath: kum havuzu /var/... (symlink) altinda kurulur ama yedekle.ROOT
        # git'ten FIZIKSEL yolu (/private/var/...) alir -> ham string karsilastirmasi
        # dosya PLANDA OLSA BILE kirmizi yakardi (olculdu).
        planda = os.path.realpath(dosya) in set(
            os.path.realpath(k) for k in d0.get("kaynaklar", []))
        return {"r0_ok": "bitti ->" in r0.stdout,
                "planda": planda,
                "olculdu": isinstance(d0.get("imza"), dict) and isinstance(d1.get("imza"), dict),
                "imza_degisti": not yb.imza_esit_mi(d0.get("imza"), d1.get("imza")),
                "imza_plani_kadar": (isinstance(d0.get("imza"), dict)
                                     and d0["imza"].get("adet") == d0.get("plan")),
                "atladi": "kopyalanmadi" in r1.stdout,
                "yedekledi": "bitti ->" in r1.stdout,
                "kopya_guncel": kopya_icerik == YENI,
                "ilk_kopyalandi": ilk_kopyalandi,
                "degisiklik_yokken_atladi": "kopyalanmadi" in r2.stdout,
                "d0": d0.get("imza"), "d1": d1.get("imza"), "plan": d0.get("plan")}


# TEK MESRU ⚪ URETICISI: bolum 10 sonundaki KALICI fikstur. Adi BURADA ilan edilir
# ki _capa "ilan edilmis fikstur" ile "kaymis gercek capa"yi AYIRT EDEBILSIN.
_CAPA_FIKSTUR_ADI = "(fikstur) kasitli anchor-KIRAN refaktor"


def _capa(ad, fn):
    """Bolum 10 anchor-miss nobetcisi — FAIL-CLOSED.

    🔴 NEDEN DEGISTI (31 Tem, capa-onarim turu): eski hal her anchor kaybini ⚪'ya
    dusururdu ve ⚪ cikis kodunu BOZMAZ. Olculdu: `bas_imza` -> baska ad seklinde TEK
    mesru yeniden adlandirma bolum 10'un 6 senaryosundan 4'unu (b/c mutant + base +
    neg-2) sessizce ⚪ yapar, KIRMIZI 0 kalir, kapi YESIL yanardi = tam da bu kapinin
    kovaladigi SESSIZ-YESIL sinifi. Artik yalniz ILAN EDILMIS kalici fikstur
    (_CAPA_FIKSTUR_ADI) ⚪ olur; baska her capa kaybi ADIYLA KIRMIZI yanar.

    🔴 NEDEN YAYINI DURDURMAZ: `serit-b` job'unun `needs:`i YOKTUR ve hicbir is ona
    bagli degildir (`deploy: needs: build`) -> buradaki KIRMIZI pruvo3d.com yayinini
    DURDURMAZ, yalniz kapiyi GORUNUR kirar. Fail-closed'in maliyeti budur.

    DAR: base davranissal KIRMIZI (ok=False) korunur; disi istisna re-raise."""
    try:
        return fn()
    except RuntimeError as e:
        if "CAPASI BULUNAMADI" not in str(e):
            raise
        if ad == _CAPA_FIKSTUR_ADI:
            olculemedi(ad, "yedekle.py yapisi degisti — capa guncellenmeli", "fikstur")
            return None
        kontrol("ÇAPA VAR: %s" % ad, False,
                "yedekle.py yapisi degisti, CAPA BULUNAMADI -> nobet SESSIZ GECMEZ; "
                "capayi bugunku yapiya TASI. %s" % str(e)[:150])
        return None


def main():
    PS_ORTAMI[0] = ps_ortami()
    GIT_ORTAMI[0] = git_ortami()
    LAUNCHD_ORTAMI[0] = launchd_ortami()
    if LAUNCHD_ORTAMI[0] != "var":
        print("⚪ NOT: pid=1 (launchd/init) 'asili' surrogati YOK (taze-boot runner / ps "
              "yok / pid=1 python) -> pid=1 mutant nobeti OLCULEMEDI [launchd] olur "
              "(deploy BLOKLANMAZ; kimlik regresyonu 6h2-(3) ile her platformda KIRMIZI).")
    if PS_ORTAMI[0] == "yok":
        print("⚪ NOT: `ps` binary'si YOK -> surec kimligi kontrolleri OLCULEMEDI "
              "olarak isaretlenecek (deploy BLOKLANMAZ; bkz. modul basligi K4).")
        print("   (Kimlik nobetlerinin SENTETIK `ps` ile kosan ucu buradan ETKILENMEZ "
              "— bkz. 6h2; mutantlar bu makinede de KIRMIZI yanar.)")
    elif PS_ORTAMI[0] == "bozuk":
        print("❌ NOT: `ps` PATH'te VAR ama CALISMIYOR -> fail-closed KIRMIZI "
              "(bozuk bagimlilik, eksik bagimliliktan farklidir; bkz. ps_ortami).")
    if GIT_ORTAMI[0] == "yok":
        print("⚪ NOT: `git` binary'si YOK -> ana calisma agaci kontrolleri OLCULEMEDI "
              "[git] olarak isaretlenecek (deploy BLOKLANMAZ; bkz. git_ortami).")
    elif GIT_ORTAMI[0] == "bozuk":
        print("❌ NOT: `git` PATH'te VAR ama CALISMIYOR -> fail-closed KIRMIZI "
              "(bozuk bagimlilik: ROOT sessizce worktree'ye duser; bkz. git_ortami).")
    durum = modul_yukle(DURUM, "durum_gercek")

    # ---------------- 1) TAZE ----------------
    print("\n1) TAZE damga — uyari BASMAMALI")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 3600)          # 1 saat once
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'taze'", d["hal"] == "taze", d["hal"])
        kontrol("satirda BAYAT/uyari YOK", "BAYAT" not in satir and "⚠" not in satir, satir)

    # ---------------- 2) BAYAT (kirmizi-mutasyon: yedegi yapay bayatlat) ----------------
    print("\n2) BAYAT damga (3 gun geriye alindi) — UYARI BASMALI")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 3 * 86400)
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'bayat'", d["hal"] == "bayat", d["hal"])
        kontrol("satirda BAYAT uyarisi VAR", "BAYAT" in satir and "⚠" in satir)
        kontrol("uyari ne yapilacagini SOYLUYOR", "tools/yedekle.py" in satir)

    # ---------------- 3) ESIK SABITI GERCEKTEN KULLANILIYOR MU ----------------
    print("\n3) KIRMIZI-MUTASYON (esik) — sabit degisince siniflama degismeli")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 3600)          # 1 saat: normalde TAZE
        eski_esik = durum.YEDEK_BAYAT_SANIYE
        try:
            durum.YEDEK_BAYAT_SANIYE = 10                        # mutasyon: esik 10 sn
            d = durum.yedek_durumu(b, "var")
        finally:
            durum.YEDEK_BAYAT_SANIYE = eski_esik
        kontrol("esik 10 sn iken ayni damga BAYAT sayildi (sabit olu degil)",
                d["hal"] == "bayat", d["hal"])
        kontrol("esik geri alininca yine TAZE",
                durum.yedek_durumu(b, "var")["hal"] == "taze")
        kontrol("varsayilan esik ~2 gun", eski_esik == 2 * 86400, str(eski_esik))

    # ---------------- 4) DAMGASIZ (eski surumle alinmis yedek) ----------------
    print("\n4) DAMGASIZ yedek — 'olculemedi' demeli, TAZE SAYMAMALI")
    with tempfile.TemporaryDirectory() as td:
        b = os.path.join(td, "backup")
        os.makedirs(b)
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'damgasiz'", d["hal"] == "damgasiz", d["hal"])
        kontrol("ÖLÇÜLEMEDİ diyor", "ÖLÇÜLEMEDİ" in satir)
        kontrol("taze DEMIYOR (sahte guven yok)", "taze:" not in satir)
        # bozuk JSON da damgasiz sayilmali (patlamamali)
        with open(os.path.join(b, ".son-yedek.json"), "w") as f:
            f.write("{bozuk json")
        kontrol("bozuk damga JSON'unda PATLAMIYOR",
                durum.yedek_durumu(b, "var")["hal"] == "damgasiz")

    # ---------------- 5) DRIVE YOK ----------------
    print("\n5) DRIVE YOK — ÖLÇÜLEMEDİ, cokme yok")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        eski = durum._drive_deseni
        try:
            durum._drive_deseni = lambda: os.path.join(td, "olmayan-*", "STL")
            yol, hal = durum.yedek_dizini(kok)
        finally:
            durum._drive_deseni = eski
        satir = " ".join(durum.yedek_satirlari(durum.yedek_durumu(yol, hal)))
        kontrol("hal 'drive-yok'", hal == "drive-yok", hal)
        kontrol("ÖLÇÜLEMEDİ + 'Drive bagli degil'",
                "ÖLÇÜLEMEDİ" in satir and "Drive bagli degil" in satir)

    # ---------------- 6) SALT-OKUNUR SOZLESMESI ----------------
    print("\n6) SALT-OKUNUR — pano .stl-backup-dir'e DOKUNMAMALI")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        cfg = os.path.join(kok, ".stl-backup-dir")
        with open(cfg, "w") as f:
            f.write("/bayat/olmayan/yol/STL")
        onceki = (open(cfg).read(), os.path.getmtime(cfg))
        durum.yedek_dizini(kok)
        kontrol("bayat .stl-backup-dir DEGISMEDI (pano yazmadi)",
                (open(cfg).read(), os.path.getmtime(cfg)) == onceki)

        # KIRMIZI-MUTASYON: pano dosya yazsa bu kontrol kirmizi yanar mi?
        mut = mutant_yaz(td,
                         '    cfg = os.path.join(repo_kok, ".stl-backup-dir")',
                         '    cfg = os.path.join(repo_kok, ".stl-backup-dir")\n'
                         '    open(cfg, "w").write("MUTANT")  # MUTANT: pano yaziyor')
        mmod = modul_yukle(mut, "durum_mutant_yazan")
        with open(cfg, "w") as f:
            f.write("/bayat/olmayan/yol/STL")
        onceki = open(cfg).read()
        mmod.yedek_dizini(kok)
        kontrol("MUTANTTA dosya DEGISTI (kontrol KIRMIZI yanardi)",
                open(cfg).read() != onceki)

    # ---------------- 6b) F2: DAMGANIN IDDIASI vs DRIVE'IN GERCEGI ----------------
    print("\n6b) F2 — 'icerik' satiri damganin IDDIASI; gercekle karsilastirilmali")
    with tempfile.TemporaryDirectory() as td:
        b = os.path.join(td, "backup")
        damga_kur(b, 3600, memory=3, skills=2)
        for alt, adet in (("memory", 3), ("skills", 2)):
            os.makedirs(os.path.join(b, alt))
            for i in range(adet):
                with open(os.path.join(b, alt, "d%d.txt" % i), "w") as f:
                    f.write("x")
        saglam = " ".join(durum.yedek_satirlari(durum.yedek_durumu(b, "var")))
        kontrol("saglam yedekte ICERIK EKSIK uyarisi YOK", "ICERIK EKSIK" not in saglam)
        # F2 senaryosu: yedek icerigi silindi, damga aynen duruyor
        shutil.rmtree(os.path.join(b, "skills"))
        d = durum.yedek_durumu(b, "var")
        bozuk = " ".join(durum.yedek_satirlari(d))
        kontrol("silinen icerik YAKALANDI", "ICERIK EKSIK" in bozuk, bozuk[-120:])
        kontrol("sayim gercekle karsilastirildi", d["sayim"].get("skills") == (0, 2),
                str(d["sayim"]))
        kontrol("hala 'taze' diyor ama uyari EKLI (sahte guven yok)",
                d["hal"] == "taze" and "⚠⚠" in bozuk)

    # ---------------- 6c) F3: GELECEK TARIHLI DAMGA ----------------
    print("\n6c) F3 — gelecek tarihli damga 'taze' DEMEMELI")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), -3600)      # 1 saat GELECEKTE
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'supheli'", d["hal"] == "supheli", d["hal"])
        kontrol("'taze' DEMIYOR", "taze:" not in satir)
        kontrol("ŞÜPHELİ + ÖLÇÜLEMEDİ diyor", "ŞÜPHELİ" in satir and "ÖLÇÜLEMEDİ" in satir)
        kontrol("1 saniye gelecek bile taze SAYILMIYOR (tolerans yok)",
                durum.yedek_durumu(damga_kur(os.path.join(td, "b2"), -1), "var")["hal"]
                == "supheli")

    # ---------------- 6d) F1: KISMI DAMGA PANODA ----------------
    print("\n6d) F1 — kismi yedek panoda TAZE gibi gecmemeli")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 60, tam=False,
                      eksik=[".urun-kaynaklari.json", "DEVAM-ARSIV.md"])
        satir = " ".join(durum.yedek_satirlari(durum.yedek_durumu(b, "var")))
        kontrol("KISMI YEDEK uyarisi VAR", "KISMI YEDEK" in satir)
        kontrol("eksik dosya adlari yaziliyor", ".urun-kaynaklari.json" in satir)
        b2 = damga_kur(os.path.join(td, "b2"), 60, tam=True, eksik=[])
        kontrol("tam yedekte KISMI uyarisi YOK",
                "KISMI YEDEK" not in " ".join(durum.yedek_satirlari(durum.yedek_durumu(b2, "var"))))
        b3 = os.path.join(td, "b3")
        os.makedirs(b3)
        with open(os.path.join(b3, ".son-yedek.json"), "w") as f:
            json.dump({"zaman": time.time() - 60, "iso": "ESKI", "memory": 1}, f)
        kontrol("eski surum damgasi 'tamlik bilgisi yok' notu aliyor",
                "tamlik bilgisi yok" in " ".join(
                    durum.yedek_satirlari(durum.yedek_durumu(b3, "var"))))

    # ---------------- 6e) N2: ILK SATIR DURUMU SOYLUYOR MU ----------------
    print("\n6e) N2 — goz gezdiren ILK SATIRDAN yanlis sonuca VARAMAMALI")
    with tempfile.TemporaryDirectory() as td:
        # (a) tam + taze + icerik tutuyor -> tek mesru "taze" hali
        a = damga_kur(os.path.join(td, "a"), 60, memory=1, skills=1)
        for alt in ("memory", "skills"):
            os.makedirs(os.path.join(a, alt))
            with open(os.path.join(a, alt, "d.txt"), "w") as f:
                f.write("x")
        bas_a = durum.yedek_satirlari(durum.yedek_durumu(a, "var"))[0]
        kontrol("(a) tam-taze ILK SATIR 'taze'", bas_a.strip().startswith("taze:"), bas_a)

        # (b) kismi yedek
        b = damga_kur(os.path.join(td, "b"), 60, tam=False, eksik=[".urun-kaynaklari.json"])
        bas_b = durum.yedek_satirlari(durum.yedek_durumu(b, "var"))[0]
        kontrol("(b) kismi ILK SATIR 'KISMI YEDEK'", "KISMI YEDEK" in bas_b, bas_b)
        kontrol("(b) ILK SATIR 'taze' DEMIYOR", "taze:" not in bas_b)

        # (c) icerik eksik
        c = damga_kur(os.path.join(td, "c"), 60, memory=0, skills=5)
        bas_c = durum.yedek_satirlari(durum.yedek_durumu(c, "var"))[0]
        kontrol("(c) icerik-eksik ILK SATIR 'ICERIK EKSIK'", "ICERIK EKSIK" in bas_c, bas_c)
        kontrol("(c) ILK SATIR 'taze' DEMIYOR", "taze:" not in bas_c)

        # (d) gelecek tarihli
        d4 = damga_kur(os.path.join(td, "d"), -3600)
        bas_d = durum.yedek_satirlari(durum.yedek_durumu(d4, "var"))[0]
        kontrol("(d) gelecek-tarihli ILK SATIR 'ŞÜPHELİ'", "ŞÜPHELİ" in bas_d, bas_d)
        kontrol("(d) ILK SATIR 'taze' DEMIYOR", "taze:" not in bas_d)

        # bayat + kismi birlikte: baslik uyariyor, digeri de kaybolmuyor
        e = damga_kur(os.path.join(td, "e"), 3 * 86400, tam=False, eksik=["DEVAM-ARSIV.md"])
        sat_e = durum.yedek_satirlari(durum.yedek_durumu(e, "var"))
        kontrol("(e) bayat+kismi: baslik BAYAT, kismi da raporlu",
                "BAYAT" in sat_e[0] and any("KISMI YEDEK" in s for s in sat_e[1:]))

    # ---------------- 6g) ATLANAN KOSUM (kilit) ----------------
    # yedekle.py kilidi alamazsa hicbir sey kopyalamaz; damgaya yalniz `son_atlama*`
    # yazar. Pano bu hali TAZE SAYMAMALI — ama KAPSANMIS atlamada da bosuna
    # uyarmamali (her paralel push'ta sari pano = kimsenin bakmadigi pano).
    print("\n6g) ATLANAN KOSUM — kapsanmayan atlama uyarir, kapsanan SUSAR")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        # (a) KAPSANMAYAN atlama: son tam kosum bitti, SONRA bir kosum atlandi
        a = damga_kur(os.path.join(td, "a"), 600, baslangic=simdi - 660,
                      son_atlama=simdi - 300, son_atlama_iso="2026-07-26 12:00:00",
                      son_atlama_sebep="baska yedek kosuyordu (pid=1234)",
                      son_atlama_kapsandi=False)
        sat_a = durum.yedek_satirlari(durum.yedek_durumu(a, "var"))
        print("     --- pano ciktisi (a) ---")
        for s in sat_a:
            print("    " + s)
        kontrol("(a) ILK SATIR 'taze' DEMIYOR", "taze:" not in sat_a[0], sat_a[0])
        kontrol("(a) mevcut sozluk: 'KISMI YEDEK' + 'ATLANDI'",
                "KISMI YEDEK" in sat_a[0] and "ATLANDI" in sat_a[0])
        kontrol("(a) sebep ve zaman yaziyor",
                "2026-07-26 12:00:00" in sat_a[0] and "baska yedek" in sat_a[0])
        kontrol("(a) ne yapilacagi yazili", "tools/yedekle.py" in " ".join(sat_a))

        # (b) KAPSANAN atlama + sahip damgayi YAZDI (eszamanli push cifti): uyari YOK
        b = damga_kur(os.path.join(td, "b"), 600, baslangic=simdi - 660,
                      son_atlama=simdi - 300, son_atlama_kapsandi=True,
                      son_atlama_sahip_baslangici=simdi - 660)
        sat_b = durum.yedek_satirlari(durum.yedek_durumu(b, "var"))
        kontrol("(b) kapsanan + sahip bitirmis atlamada pano SUSUYOR ('taze')",
                sat_b[0].strip().startswith("taze:") and not any("ATLANDI" in s for s in sat_b),
                sat_b[0])

        # (b2) 🔴 KAPSANAN ama sahip damgayi HIC YAZMAMIS (asildi/oldu) -> UYARI SART
        b2 = damga_kur(os.path.join(td, "b2"), 600, baslangic=simdi - 660,
                       son_atlama=simdi - 300, son_atlama_kapsandi=True,
                       son_atlama_sahip_baslangici=simdi - 400)   # damga ondan ESKI
        sat_b2 = durum.yedek_satirlari(durum.yedek_durumu(b2, "var"))
        kontrol("(b2) sahip bitirmemisken 'kapsandi' SUSTURMUYOR",
                not sat_b2[0].strip().startswith("taze:") and "ATLANDI" in sat_b2[0],
                sat_b2[0])
        kontrol("(b2) sebep aciklikla yaziyor", "HIC YAZMADI" in sat_b2[0])

        # (b2b) ATLAMA KAYDI AYRI DOSYADAN da okunmali (yeni surum yazicisi orayi kullanir)
        b2b = damga_kur(os.path.join(td, "b2b"), 600, baslangic=simdi - 660)
        with open(os.path.join(b2b, ".son-yedek-atlama.json"), "w") as fh:
            json.dump({"son_atlama": simdi - 300, "son_atlama_iso": "AYRI-DOSYA",
                       "son_atlama_sebep": "baska yedek kosuyordu",
                       "son_atlama_kapsandi": True,
                       "son_atlama_sahip_baslangici": simdi - 400}, fh)
        sat_b2b = durum.yedek_satirlari(durum.yedek_durumu(b2b, "var"))
        kontrol("(b2b) ayri dosyadaki atlama kaydi PANOYA giriyor",
                "ATLANDI" in sat_b2b[0] and "AYRI-DOSYA" in sat_b2b[0], sat_b2b[0][:90])
        # ayni dizinde damga-ici ESKI kopya varsa AYRI DOSYA kazanir (daha yeni yazici)
        b2c = damga_kur(os.path.join(td, "b2c"), 600, baslangic=simdi - 660,
                        son_atlama=simdi - 300, son_atlama_iso="DAMGA-ICI",
                        son_atlama_kapsandi=False)
        with open(os.path.join(b2c, ".son-yedek-atlama.json"), "w") as fh:
            json.dump({"son_atlama": simdi - 900, "son_atlama_iso": "AYRI-DOSYA",
                       "son_atlama_kapsandi": True,
                       "son_atlama_sahip_baslangici": simdi - 1000}, fh)
        sat_b2c = durum.yedek_satirlari(durum.yedek_durumu(b2c, "var"))
        kontrol("(b2c) ayri dosya damga-ici eski kopyayi EZIYOR (uyari yok)",
                sat_b2c[0].strip().startswith("taze:"), sat_b2c[0][:90])

        # (b3) sahip alani HIC YOK (cozulemez) -> fail-closed UYAR
        b3 = damga_kur(os.path.join(td, "b3"), 600, baslangic=simdi - 660,
                       son_atlama=simdi - 300, son_atlama_kapsandi=True)
        kontrol("(b3) sahip alani yoksa fail-closed UYARIYOR",
                "ATLANDI" in durum.yedek_satirlari(durum.yedek_durumu(b3, "var"))[0])

        # (b2d) 🔴 K2: DAMGADAN MIRAS `son_atlama*` FAIL-CLOSED'I SUSTURMAMALI.
        # Fikstur: ayri dosya (yeni yazici) sahibi TANIMLAYAMADI (alan YOK) -> uyari
        # SART. Damgada ise MIRAS kalmis bir `son_atlama_sahip_baslangici` var ve o
        # alan tek basina "sahip bitirdi" hukmu verip uyariyi SUSTURUR. Anahtar-anahtar
        # `update` mirasi birakiyordu; REPLACE semantigi ayri dosya varken damgadan
        # gelen TUM `son_atlama*` alanlarini DUSURUR.
        b2d = damga_kur(os.path.join(td, "b2d"), 600, baslangic=simdi - 660,
                        son_atlama=simdi - 3000, son_atlama_iso="DAMGA-ICI-MIRAS",
                        son_atlama_kapsandi=True,
                        son_atlama_sahip_baslangici=simdi - 5000)   # MIRAS susturucu
        with open(os.path.join(b2d, ".son-yedek-atlama.json"), "w") as fh:
            json.dump({"son_atlama": simdi - 300, "son_atlama_iso": "AYRI-DOSYA",
                       "son_atlama_sebep": "baska yedek kosuyordu",
                       "son_atlama_kapsandi": True}, fh)     # sahip alani BILEREK YOK
        d_b2d = durum.yedek_durumu(b2d, "var")
        sat_b2d = durum.yedek_satirlari(d_b2d)
        kontrol("(b2d) K2: miras `son_atlama_sahip_baslangici` DUSURULDU (replace)",
                "son_atlama_sahip_baslangici" not in (d_b2d["damga"] or {}),
                str(sorted(k for k in (d_b2d["damga"] or {}) if k.startswith("son_atlama"))))
        kontrol("(b2d) K2: miras alan fail-closed uyarisini SUSTURMUYOR",
                not sat_b2d[0].strip().startswith("taze:") and "ATLANDI" in sat_b2d[0],
                sat_b2d[0][:90])
        kontrol("(b2d) uyari AYRI DOSYADAKI kaydi anlatiyor (damga-ici degil)",
                "AYRI-DOSYA" in sat_b2d[0] and "DAMGA-ICI-MIRAS" not in sat_b2d[0],
                sat_b2d[0][:90])
        # KIRMIZI-MUTASYON: `update` semantigine donunce miras alan geri gelir ve susturur
        mut_k2 = mutant_yaz(td,
                            '        damga = {k: v for k, v in damga.items() '
                            'if not k.startswith("son_atlama")}\n'
                            '        damga.update({k: v for k, v in (atlama_kaydi or {}).items()\n'
                            '                      if k.startswith("son_atlama")})',
                            '        damga = dict(damga)  # MUTANT: update semantigi\n'
                            '        damga.update({k: v for k, v in (atlama_kaydi or {}).items()\n'
                            '                      if k.startswith("son_atlama")})',
                            ad="durum_mutant_miras.py")
        mmod_k2 = modul_yukle(mut_k2, "durum_mutant_miras")
        m_k2 = mmod_k2.yedek_satirlari(mmod_k2.yedek_durumu(b2d, "var"))
        kontrol("MUTANTTA (update) miras alan panoyu SUSTURUYOR (kontrol KIRMIZI yanardi)",
                m_k2[0].strip().startswith("taze:"), m_k2[0][:90])

        # ---- (b2e) 🔴 K2 / 6. TUR: BOZUK ATLAMA DOSYASINDA MIRAS YASIYORDU ----------
        # Curutucu olcumu: `except: pass` yuzunden ayri dosya OKUNAMADIGINDA damgadan
        # gelen miras `son_atlama_sahip_baslangici` ayakta kaliyor ve fail-closed uyariyi
        # SUSTURUYORDU -> pano "taze". 8 bozuk-dosya biciminin 6'sinda oldu.
        # ILKE (mimar karari): ayri dosya VAR ama ondan dict elde EDILEMIYORSA atlama
        # duzlemi BILINMIYOR'dur -> damganin mirasi ASLA devreye girmez, sonuc GORUNUR
        # uyaridir, hicbir bicimde "taze"/"GUNCEL" DENMEZ.
        BOZUK_BICIMLER = (
            ("gecersiz JSON", b'{"son_atlama": bozuk,,'),
            ("BOS dosya (0 bayt)", b""),
            ("kesik/kismi JSON", b'{"son_atlama": 1785000000, "son_atlama_kapsandi"'),
            ("dict DEGIL — liste", b"[1, 2, 3]"),
            ("dict DEGIL — dize", b'"son_atlama"'),
            ("dict DEGIL — sayi", b"12345"),
            ("ikili cop (UTF-8 degil)", b"\xff\xfe\x00\x01\x02gurultu\x80\x81"),
            ("yalniz bosluk", b"   \n\t  \n"),
        )
        # ⚠️ BASLIKTAKI SAYI ELLE YAZILMAZ: bu satirda "8 bicimi" yaziyordu, gercekte
        # 10 bicim kosuyor (tuple + asagidaki 2 yapisal bicim) — yani basligin kendisi
        # bayat bir VERI CAPASIYDI. Sayiyi listenin uzunlugu basar.
        print("\n6g2) K2 — BOZUK atlama dosyasinin %d bicimi: miras SUSTURMAMALI"
              % (len(BOZUK_BICIMLER) + 2))
        for etiket, ham in BOZUK_BICIMLER:
            bz = damga_kur(os.path.join(td, "bz-" + etiket[:12].replace(" ", "_")), 600,
                           baslangic=simdi - 660,
                           son_atlama=simdi - 300, son_atlama_iso="DAMGA-ICI-MIRAS",
                           son_atlama_kapsandi=True,
                           son_atlama_sahip_baslangici=simdi - 5000)  # MIRAS susturucu
            with open(os.path.join(bz, ".son-yedek-atlama.json"), "wb") as fh:
                fh.write(ham)
            d_bz = durum.yedek_durumu(bz, "var")
            sat_bz = durum.yedek_satirlari(d_bz)
            tum = " ".join(sat_bz)
            kontrol("(bozuk: %s) hal 'bilinmiyor' + miras DUSTU" % etiket,
                    d_bz.get("atlama_hali") == "bilinmiyor"
                    and not any(k.startswith("son_atlama") for k in (d_bz["damga"] or {})),
                    "hal=%s alanlar=%s" % (d_bz.get("atlama_hali"),
                                           sorted(k for k in (d_bz["damga"] or {})
                                                  if k.startswith("son_atlama"))))
            kontrol("(bozuk: %s) pano 'taze'/'GUNCEL' DEMIYOR + GORUNUR uyari" % etiket,
                    not sat_bz[0].strip().startswith("taze:")
                    and "GÜNCEL" not in sat_bz[0]
                    and ("ÖLÇÜLEMEDİ" in tum or "⚠" in tum)
                    and "OKUNAMADI" in tum,
                    sat_bz[0][:100])
        # IKI IZINSIZ/YAPISAL BICIM (ayri kurulum gerekiyor: chmod + dizin)
        bz_izin = damga_kur(os.path.join(td, "bz-izin"), 600, baslangic=simdi - 660,
                            son_atlama=simdi - 300, son_atlama_kapsandi=True,
                            son_atlama_sahip_baslangici=simdi - 5000)
        _izin_yolu = os.path.join(bz_izin, ".son-yedek-atlama.json")
        with open(_izin_yolu, "w") as fh:
            json.dump({"son_atlama": simdi - 300}, fh)
        os.chmod(_izin_yolu, 0o000)
        bz_dizin = damga_kur(os.path.join(td, "bz-dizin"), 600, baslangic=simdi - 660,
                             son_atlama=simdi - 300, son_atlama_kapsandi=True,
                             son_atlama_sahip_baslangici=simdi - 5000)
        os.makedirs(os.path.join(bz_dizin, ".son-yedek-atlama.json"))
        for etiket, yer in (("IZINSIZ dosya (chmod 000)", bz_izin),
                            ("yolda DIZIN var (dosya degil)", bz_dizin)):
            d_bz = durum.yedek_durumu(yer, "var")
            sat_bz = durum.yedek_satirlari(d_bz)
            tum = " ".join(sat_bz)
            if etiket.startswith("IZINSIZ") and d_bz.get("atlama_hali") == "var":
                # root olarak kosuluyorsa chmod 000 ISIRMAZ -> fikstur GECERSIZ, sessiz
                # gecmesin: GORUNUR olculemedi (kirmizi degil, cunku kod degil ORTAM).
                olculemedi("(bozuk: %s) fikstur ISIRMADI (root?)" % etiket,
                           "chmod 000 dosya yine okundu", eksen="fikstur")
                continue
            kontrol("(bozuk: %s) hal 'bilinmiyor' + miras DUSTU" % etiket,
                    d_bz.get("atlama_hali") == "bilinmiyor"
                    and not any(k.startswith("son_atlama") for k in (d_bz["damga"] or {})),
                    "hal=%s" % d_bz.get("atlama_hali"))
            kontrol("(bozuk: %s) pano 'taze'/'GUNCEL' DEMIYOR + GORUNUR uyari" % etiket,
                    not sat_bz[0].strip().startswith("taze:")
                    and "GÜNCEL" not in sat_bz[0] and "OKUNAMADI" in tum,
                    sat_bz[0][:100])
        os.chmod(_izin_yolu, 0o644)                  # tempdir silinebilsin
        # SAGLIKLI DICT bicimleri (bozuk DEGIL): replace zaten mirasi dusuruyor ->
        # POZITIF nobetci (kapsam yanlis eksene kaymasin: bunlar uyari URETMEZ)
        for etiket, kayit in (("bos dict {}", {}),
                              ("alakasiz anahtarli dict", {"baska": 1})):
            sg = damga_kur(os.path.join(td, "sg-" + etiket[:8].replace(" ", "_")), 600,
                           baslangic=simdi - 660, son_atlama=simdi - 300,
                           son_atlama_kapsandi=True,
                           son_atlama_sahip_baslangici=simdi - 5000)
            with open(os.path.join(sg, ".son-yedek-atlama.json"), "w") as fh:
                json.dump(kayit, fh)
            d_sg = durum.yedek_durumu(sg, "var")
            kontrol("(saglikli: %s) hal 'var' + miras DUSTU + OKUNAMADI uyarisi YOK"
                    % etiket,
                    d_sg.get("atlama_hali") == "var"
                    and not any(k.startswith("son_atlama") for k in (d_sg["damga"] or {}))
                    and "OKUNAMADI" not in " ".join(durum.yedek_satirlari(d_sg)),
                    "hal=%s" % d_sg.get("atlama_hali"))
        # KIRMIZI-MUTASYON: 'bilinmiyor' yeniden 'yok' gibi ele alinirsa miras geri gelir
        mut_k2b = mutant_yaz(td,
                             '        return None, ("bilinmiyor" if os.path.exists(yol) '
                             'else "yok")',
                             '        return None, "yok"  # MUTANT: bozuk == yok',
                             ad="durum_mutant_bozuk_atlama.py")
        mmod_k2b = modul_yukle(mut_k2b, "durum_mutant_bozuk_atlama")
        bz_m = damga_kur(os.path.join(td, "bz-mutant"), 600, baslangic=simdi - 660,
                         son_atlama=simdi - 300, son_atlama_kapsandi=True,
                         son_atlama_sahip_baslangici=simdi - 5000)
        with open(os.path.join(bz_m, ".son-yedek-atlama.json"), "w") as fh:
            fh.write("{bozuk")
        m_k2b = mmod_k2b.yedek_satirlari(mmod_k2b.yedek_durumu(bz_m, "var"))
        kontrol("MUTANTTA (bozuk==yok) bozuk dosyada miras SUSTURUYOR "
                "(kontrol KIRMIZI yanardi)",
                m_k2b[0].strip().startswith("taze:"), m_k2b[0][:90])

        # ---- (b2f) K2: ayri dosya YOK + YENI surum damga -> miras KALINTIdir --------
        # `damga_yaz` onceki damgadan `son_atlama*` alanlarini TASIR: bir kez girdiginde
        # SONSUZA DEK yasar. Surum >= 3 atlamayi AYRI dosyaya yazar; o halde damganin
        # ICINDEKI alanlar kalintidir -> SUSTURMA yetkisi TASIMAZ (uyari fail-closed).
        b2f = damga_kur(os.path.join(td, "b2f"), 600, baslangic=simdi - 660, surum=4,
                        son_atlama=simdi - 300, son_atlama_iso="KALINTI",
                        son_atlama_kapsandi=True,
                        son_atlama_sahip_baslangici=simdi - 5000)
        d_b2f = durum.yedek_durumu(b2f, "var")
        sat_b2f = durum.yedek_satirlari(d_b2f)
        kontrol("(b2f) YENI surum + ayri dosya YOK: susturucu ikili DUSTU",
                d_b2f.get("atlama_kalintisi") is True
                and "son_atlama_sahip_baslangici" not in (d_b2f["damga"] or {})
                and "son_atlama_kapsandi" not in (d_b2f["damga"] or {}),
                "kalinti=%s" % d_b2f.get("atlama_kalintisi"))
        kontrol("(b2f) atlamanin KENDISI kaldi -> pano UYARIYOR ('taze' DEMIYOR)",
                not sat_b2f[0].strip().startswith("taze:") and "ATLANDI" in sat_b2f[0],
                sat_b2f[0][:90])
        # POZITIF nobetci: ESKI surum (<3) damgayi TEK yazici olarak kullanirdi ->
        # onun susturucusu MESRUDUR (asiri-daralma olmasin; (b) fiksturu bunu tasiyor)
        b2g = damga_kur(os.path.join(td, "b2g"), 600, baslangic=simdi - 660, surum=2,
                        son_atlama=simdi - 300, son_atlama_kapsandi=True,
                        son_atlama_sahip_baslangici=simdi - 660)
        kontrol("(b2g) ESKI surum (<3) damga-ici susturucu MESRU (asiri-daralma YOK)",
                durum.yedek_satirlari(durum.yedek_durumu(b2g, "var"))[0]
                .strip().startswith("taze:"),
                durum.yedek_satirlari(durum.yedek_durumu(b2g, "var"))[0][:90])
        # KIRMIZI-MUTASYON: kalinti kurali kaldirilirsa (b2f) sessizce "taze" olur
        mut_k2c = mutant_yaz(td,
                             "    if son_atlama_var and not eski_yazici:",
                             "    if False:  # MUTANT: kalinti kurali YOK",
                             ad="durum_mutant_kalinti.py")
        mmod_k2c = modul_yukle(mut_k2c, "durum_mutant_kalinti")
        m_k2c = mmod_k2c.yedek_satirlari(mmod_k2c.yedek_durumu(b2f, "var"))
        kontrol("MUTANTTA (kalinti kurali yok) (b2f) 'taze' diyor (kontrol KIRMIZI yanardi)",
                m_k2c[0].strip().startswith("taze:"), m_k2c[0][:90])

        # (c) ESKI atlama: sonrasinda TAM bir kosum BASLADI -> kendi kendine temizlenir
        c = damga_kur(os.path.join(td, "c"), 60, baslangic=simdi - 120,
                      son_atlama=simdi - 3000, son_atlama_kapsandi=False)
        sat_c = durum.yedek_satirlari(durum.yedek_durumu(c, "var"))
        kontrol("(c) sonraki tam kosum atlamayi KAPATIR (uyari yok)",
                sat_c[0].strip().startswith("taze:"), sat_c[0])

        # (d) HIC yedek yokken atlanan kosum: damgada `zaman` YOK -> ÖLÇÜLEMEDİ
        d6 = os.path.join(td, "d")
        os.makedirs(d6)
        with open(os.path.join(d6, ".son-yedek.json"), "w") as fh:
            json.dump({"son_atlama": simdi, "son_atlama_iso": "TEST",
                       "son_atlama_sebep": "baska yedek kosuyordu",
                       "son_atlama_kapsandi": False}, fh)
        dd = durum.yedek_durumu(d6, "var")
        sat_d = durum.yedek_satirlari(dd)
        print("     --- pano ciktisi (d) ---")
        for s in sat_d:
            print("    " + s)
        kontrol("(d) atlama-only damga 'damgasiz' sayiliyor", dd["hal"] == "damgasiz",
                dd["hal"])
        kontrol("(d) 'taze' DEMIYOR + ÖLÇÜLEMEDİ diyor",
                "taze:" not in " ".join(sat_d) and "ÖLÇÜLEMEDİ" in " ".join(sat_d))

        # (e) KILITSIZ kosum notu
        e = damga_kur(os.path.join(td, "e"), 60, baslangic=simdi - 120, kilitsiz=True)
        kontrol("(e) kilitsiz kosum panoda NOT olarak gorunuyor",
                any("KILITSIZ" in s for s in durum.yedek_satirlari(durum.yedek_durumu(e, "var"))))

        # (f) KIRMIZI-MUTASYON 1: atlama kontrolu tumden kaldirilirsa (a) TAZE olur
        mut = mutant_yaz(td,
                         "                and atlama > _ref\n"
                         '                and not (dmg.get("son_atlama_kapsandi") is True '
                         'and _sahip_bitti))',
                         '                and False)  # MUTANT: atlama gorulmuyor',
                         ad="durum_mutant_atlama.py")
        mmod = modul_yukle(mut, "durum_mutant_atlama")
        m_sat = mmod.yedek_satirlari(mmod.yedek_durumu(a, "var"))
        kontrol("MUTANTTA atlanan yedek 'taze' gorunuyor (kontrol KIRMIZI yanardi)",
                m_sat[0].strip().startswith("taze:"), m_sat[0])

        # (g) KIRMIZI-MUTASYON 2: SAHIP COZUMU kaldirilirsa (b2) sessizce TAZE olur
        #     = curutucunun buldugu sessiz veri kaybi yolu, geri gelirse yakalanir.
        mut2 = mutant_yaz(td,
                          "    _sahip_bitti = (isinstance(_sahip, (int, float)) and "
                          "isinstance(_ref, (int, float))\n"
                          "                    and _ref >= _sahip)",
                          "    _sahip_bitti = True  # MUTANT: sahip bitirdi VARSAYILIYOR",
                          ad="durum_mutant_sahip.py")
        mmod2 = modul_yukle(mut2, "durum_mutant_sahip")
        m2 = mmod2.yedek_satirlari(mmod2.yedek_durumu(b2, "var"))
        kontrol("MUTANTTA (varsayim) asili sahip 'taze' gorunuyor (kontrol KIRMIZI yanardi)",
                m2[0].strip().startswith("taze:"), m2[0])

    # ---------------- 6h) YEDEK KILIDI PANODA ----------------
    # Atlama push aninda %100 SESSIZ (pre-push blogu stdout+stderr'i yutar, atlama
    # exit 0). Saatlerdir asili kilit yalnizca BURADA gorunur.
    print("\n6h) KILIT PANODA — asili/yarim kilit GORUNUR, normal kilit SESSIZ")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        yol = os.path.join(kok, ".yedek.lock")
        kontrol("kilit dosyasi YOK -> hal 'yok', satir YOK",
                durum.kilit_durumu(kok)["hal"] == "yok"
                and durum.kilit_satirlari(durum.kilit_durumu(kok)) == [])
        with open(yol, "w") as fh:
            fh.write("")
        kontrol("bos kilit (birakilmis) -> hal 'yok', satir YOK",
                durum.kilit_durumu(kok)["hal"] == "yok"
                and durum.kilit_satirlari(durum.kilit_durumu(kok)) == [])
        # BAGIMLILIK NOBETCISI (K4, 27 Tem): surec kimligi `ps` (procps) ile olculur.
        # `ps` VARSA bu kontrol GERCEKTEN olcer (mutasyonla kirmizi yanar); `ps` YOKSA
        # ⚪ OLCULEMEDI olur ve TUM SITE YAYINI durmaz. Sessiz atlama YOK: ozet sayar.
        ps_kontrol("ps ile surec bilgisi okunabiliyor (kimlik dogrulamasinin on kosulu)",
                   durum._surec_bilgisi(os.getpid())[0] is not None,
                   str(durum._surec_bilgisi(os.getpid())))
        # `bitti=` isaretli iz: kosum DUZGUN bitti, kimse tutmuyor -> SESSIZ
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST bitti=%r\n"
                     % (os.getpid(), simdi - 5, simdi - 4))
        d_bitti = durum.kilit_durumu(kok)
        kontrol("'bitti=' isaretli iz -> hal 'yok', satir YOK (temiz birakma)",
                d_bitti["hal"] == "yok" and durum.kilit_satirlari(d_bitti) == [],
                d_bitti["hal"])
        # canli sahip, yas kucuk -> NORMAL: pano susar (gurultu yapmaz)
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST\n" % (os.getpid(), simdi))
        d_norm = durum.kilit_durumu(kok)
        kontrol("canli + yeni kilit -> 'tutuluyor', satir YOK",
                d_norm["hal"] == "tutuluyor" and durum.kilit_satirlari(d_norm) == [],
                d_norm["hal"])
        # 2 saattir tutan GERCEKTEN canli sahip -> UYARI
        # (yas simule edilir; surec kimligi DAIMA gercek saatle olculur)
        cocuk = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            with open(yol, "w") as fh:
                fh.write("pid=%d baslangic=%r iso=TEST\n" % (cocuk.pid, time.time()))
            d_asili = durum.kilit_durumu(kok, simdi=time.time() + 7200)
            sat_asili = durum.kilit_satirlari(d_asili)
            print("     --- pano ciktisi (kilit 2 saattir asili) ---")
            for s in sat_asili:
                print("    " + s)
            kontrol("2 saatlik CANLI python sahibi -> hal 'asili'",
                    d_asili["hal"] == "asili", d_asili["hal"])
            kontrol("pano SURESINI ve pid'i SOYLUYOR",
                    "2.0 saattir" in sat_asili[0] and str(cocuk.pid) in sat_asili[0])
            kontrol("pano 'yedekler ATLANIYOR' diyor", "ATLANIYOR" in sat_asili[0])
            kontrol("pano kilidi KIRMA talimati vermiyor, elle kontrol diyor",
                    "KIRILMAZ" in sat_asili[1])
            # ESIK SABITI OLU MU: ayni canli sahip, yas 60 sn -> varsayilan esikte
            # 'tutuluyor', esik 10 sn'ye cekilince 'asili' olmali.
            ileri = time.time() + 60
            kontrol("60 sn'lik kilit varsayilan esikte 'tutuluyor'",
                    durum.kilit_durumu(kok, simdi=ileri)["hal"] == "tutuluyor")
            kontrol("esik 10 sn'ye cekilince ayni kilit 'asili' oluyor",
                    durum.kilit_durumu(kok, simdi=ileri, esik=10)["hal"] == "asili")
        finally:
            cocuk.kill()
            cocuk.wait()
        kontrol("sahip surec olunce ayni iz 'yarim' oluyor",
                durum.kilit_durumu(kok)["hal"] == "yarim")
        # OLU sahip: yarim kalmis kosum izi
        with open(yol, "w") as fh:
            fh.write("pid=999999 baslangic=%r iso=TEST\n" % (simdi - 60))
        d_yarim = durum.kilit_durumu(kok)
        kontrol("olu pid -> hal 'yarim' (kosum ortasinda kesilmis)",
                d_yarim["hal"] == "yarim" and d_yarim["canli"] is False, d_yarim["hal"])
        kontrol("yarim kilit panoda UYARIYOR",
                "YARIM KALMIS" in durum.kilit_satirlari(d_yarim)[0])

        # 🔴 PID YENIDEN KULLANIMI (C) — pid CANLI ama bu kilidin sahibi DEGIL
        # (surec, imzadan SONRA basladi). Pano yanlis SUSMAMALI ve alakasiz sureci
        # "sonlandir" diye GOSTERMEMELI.
        with open(yol, "w") as fh:                       # kendi pid'imiz: python, ama
            fh.write("pid=%d baslangic=%r iso=TEST\n"    # kilit 2 saat once alinmis
                     % (os.getpid(), simdi - 7200))      # -> surec kilitten SONRA basladi
        d_geri = durum.kilit_durumu(kok)
        sat_geri = durum.kilit_satirlari(d_geri)
        ps_kontrol("yeniden kullanilan pid -> 'tutuluyor' DEGIL 'yarim'",
                   d_geri["hal"] == "yarim" and d_geri["canli"] is False, d_geri["hal"])
        ps_kontrol("yeniden kullanilan pid'de 'sonlandir' onerisi YOK",
                   not any("sonlandir" in s for s in sat_geri), " | ".join(sat_geri)[:90])
        # launchd (pid 1): canli ama python DEGIL -> sahip olamaz.
        # Kilit YASI = LAUNCHD_MUT_KILIT_YASI: kimlik-yok mutantinin bunu 'asili' sanmasi
        # (macOS'ta KIRMIZI) ANCAK pid=1 bu yastan yasliysa gorunur; surrogat kapisi
        # (launchd_ortami) tam bu esigi olcer -> ikisi AYNI sabitle baglidir (drift YOK).
        with open(yol, "w") as fh:
            fh.write("pid=1 baslangic=%r iso=TEST\n" % (simdi - LAUNCHD_MUT_KILIT_YASI))
        d_launchd = durum.kilit_durumu(kok)
        ps_kontrol("pid=1 (launchd) sahip SAYILMIYOR -> 'yarim'",
                   d_launchd["hal"] == "yarim", d_launchd["hal"])
        ps_kontrol("pid=1 icin 'sonlandir' onerisi YOK",
                   not any("sonlandir" in s for s in durum.kilit_satirlari(d_launchd)))
        # KIRMIZI-MUTASYON: kimlik dogrulamasi kaldirilirsa ikisi de yanlis siniflanir
        mut_pid = mutant_yaz(td,
                             '    if komut and "python" not in os.path.basename(komut).lower():\n'
                             "        return False                      "
                             "# baska bir program bu pid'i almis",
                             "    if False:\n        return False  # MUTANT: kimlik yok",
                             ad="durum_mutant_pid.py")
        mmod_pid = modul_yukle(mut_pid, "durum_mutant_pid")
        # ⚪ PLATFORM-DAYANIKLILIK (CI-parite, 27 Tem): bu fikstur pid=1'i (launchd/init)
        # 'asili sahip' surrogati olarak kullanir. macOS'ta launchd gunlerdir canlidir ->
        # kimlik-yok mutanti pid=1'i 'asili' sanar (KIRMIZI). Taze-boot CI runner'inda
        # (Ubuntu) pid=1 (systemd) dakikalar oncedir -> baslangic-yeniden-kullanim clause'u
        # mutantta da pid=1'i 'yarim' yapar -> fikstur mutanti OLCEMEZ. Bu bir ORTAM
        # EKSIKLIGIDIR (ps/git yoklugu sinifiyla ayni): launchd_kontrol ile ⚪ OLCULEMEDI
        # [launchd] olur, KIRMIZI DEGIL -> deploy BLOKLANMAZ. macOS'ta mutant yakalanir.
        # (Kimlik clause'unun GERCEK regresyonu ORTAMDAN BAGIMSIZ 6h2-(3) sentetik-ps
        #  nobetiyle her platformda KIRMIZI kalir; bu, o mutant-ISPATININ pid=1 ucudur.)
        launchd_kontrol(
                "MUTANTTA (kimlik yok) launchd/init 'asili' gorunuyor (kontrol KIRMIZI yanardi)",
                mmod_pid.kilit_durumu(kok)["hal"] == "asili",
                mmod_pid.kilit_durumu(kok)["hal"])

        # 🔴 K4 SESSIZ-YESIL NOBETCISI: `ps` VARKEN, _surec_bilgisi'ni olduren bir
        # mutasyon "OLCULEMEDI" kilifina KACAMAZ — kimlik kontrolleri KIRMIZI yanar.
        # (Kapi ortama bakiyor, olculen kodun kendi fonksiyonuna DEGIL; bu kontrol
        # o tercihin kanitidir. Mutant `ps`i degil KODU bozar.)
        mut_ps = mutant_yaz(td,
                            "    satir = (p.stdout or \"\").strip()",
                            "    satir = \"\"  # MUTANT: ps ciktisi yok sayiliyor",
                            ad="durum_mutant_ps.py")
        mmod_ps = modul_yukle(mut_ps, "durum_mutant_ps")
        with open(yol, "w") as fh:                       # pid=1: canli ama python DEGIL
            fh.write("pid=1 baslangic=%r iso=TEST\n" % (simdi - 7200))
        ps_kontrol("ps VAR: _surec_bilgisi'ni olduren mutant kimligi KAYBEDIYOR "
                   "(OLCULEMEDI'ye kacamaz)",
                   mmod_ps._surec_bilgisi(os.getpid())[0] is None
                   and mmod_ps.kilit_durumu(kok)["hal"] != "yarim",
                   "mutant hal=%s" % mmod_ps.kilit_durumu(kok)["hal"])
        with open(yol, "w") as fh:                       # 6h'nin bozuk-imza adimina hazirla
            fh.write("pid=1 baslangic=%r iso=TEST\n" % (simdi - 7200))
        # bozuk imza
        with open(yol, "w") as fh:
            fh.write("bozuk satir\n")
        kontrol("bozuk imza -> 'okunamadi', pano yine konusuyor",
                durum.kilit_durumu(kok)["hal"] == "okunamadi"
                and "COZULEMEDI" in durum.kilit_satirlari(durum.kilit_durumu(kok))[0])
        # iki dosyadaki esik/ad AYNI mi (surukleme nobetcisi)
        yedekle_mod = modul_yukle(os.path.join(TOOLS, "yedekle.py"), "yedekle_esik")
        kontrol("kilit ADI iki dosyada ayni",
                durum.YEDEK_KILIT_ADI == yedekle_mod.KILIT_ADI, durum.YEDEK_KILIT_ADI)
        kontrol("asili esigi iki dosyada ayni",
                durum.YEDEK_KILIT_ASILI == yedekle_mod.KILIT_UYARI_YASI,
                "%s / %s" % (durum.YEDEK_KILIT_ASILI, yedekle_mod.KILIT_UYARI_YASI))
        # pano ana akisi kilidi GERCEKTEN cagiriyor mu (kablolama nobetcisi)
        gov = open(DURUM, encoding="utf-8").read()
        kontrol("main() kilit satirlarini ekliyor", "kilit_satirlari(kilit_durumu(kok))" in gov)

    # ---------------- 6h2) PS'TEN BAGIMSIZ KIMLIK NOBETI ----------------
    # 🔴 8. TURUN MERGE BLOKLAYICISI (curutucu olctu): yukaridaki kimlik kontrollerinin
    # HEPSI `ps_kontrol` ile sariliydi -> `ps` PATH'te YOKKEN nobetcinin KENDISI ⚪
    # oluyordu ve IKI GERCEK mutant sessizce YESIL geciyordu:
    #   MA  `_surec_bilgisi` olduruldu            -> ps=VAR rc1 / ps=YOK **rc0** 🔴
    #   MB  pid-yeniden-kullanim tespiti olduruldu -> ps=VAR rc1 / ps=YOK **rc0** 🔴
    # Cozum (fizibilitesi 9b'de zaten kanitli): sozlesmeyi GERCEK `ps` binary'siyle
    # degil, ENJEKTE EDILMIS SENTETIK bir `ps` ile sina. Boylece olcum makinenin ps
    # durumundan (yok/bozuk/var) BAGIMSIZ olur -> bu blok DAIMA bloklayici (⚪ YOK).
    # Sahte `ps` GERCEK ps'in ASLA dondurmeyecegi bir komut adi basar ("*-SAHTE"):
    # fikstur ISIRMAZSA (PATH enjeksiyonu tutmazsa) ilk kontrol KIRMIZI yanar, yani
    # nobetin kendisi de olculur.
    print("\n6h2) SENTETIK `ps` — kimlik nobeti gercek `ps`e BAGLI DEGIL (⚪'ya kacamaz)")
    _eski_path = os.environ.get("PATH", "")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        yol = os.path.join(kok, ".yedek.lock")

        def sahte_ps_path(dizin, etime, komut):
            """PATH'i YALNIZ sahte `ps` iceren bir dizine cevirir; dizini dondurur."""
            kutu = os.path.join(dizin, "bin")
            os.makedirs(kutu)
            sahte = os.path.join(kutu, "ps")
            with open(sahte, "w") as fh:
                fh.write("#!/bin/sh\necho '   %s %s'\nexit 0\n" % (etime, komut))
            os.chmod(sahte, 0o755)
            os.environ["PATH"] = kutu
            return kutu

        def kilit_yaz(pid, baslangic):
            with open(yol, "w") as fh:
                fh.write("pid=%d baslangic=%r iso=TEST\n" % (pid, baslangic))

        try:
            # (1) FIKSTUR ISIRIYOR MU + MA NOBETI: sozlesme "gecen sn + komut adi".
            #     MA (_surec_bilgisi olduruldu) burada (None, None) doner -> KIRMIZI.
            with tempfile.TemporaryDirectory() as ftd:
                sahte_ps_path(ftd, "01:23", "python3-SAHTE")     # 1 dk 23 sn = 83 sn
                gecen, komut = durum._surec_bilgisi(os.getpid())
                bagimsiz_kontrol("[sentetik ps] _surec_bilgisi sahte ciktiyi OKUYOR "
                                 "(fikstur ISIRIYOR; MA mutanti burada olur)",
                                 gecen == 83 and komut == "python3-SAHTE",
                                 "gecen=%s komut=%s" % (gecen, komut))
                # (2) MB NOBETI — pid YENIDEN KULLANILMIS: surec 83 sn once basladi,
                #     kilit 2 saat once alindi -> bu surec kilidin sahibi OLAMAZ.
                kilit_yaz(os.getpid(), simdi - 7200)
                d_mb = durum.kilit_durumu(kok)
                sat_mb = durum.kilit_satirlari(d_mb)
                bagimsiz_kontrol("[sentetik ps] kilitten SONRA baslamis surec sahip DEGIL "
                                 "-> 'yarim' (MB mutanti burada olur)",
                                 d_mb["hal"] == "yarim" and d_mb["canli"] is False,
                                 "hal=%s canli=%s" % (d_mb["hal"], d_mb["canli"]))
                bagimsiz_kontrol("[sentetik ps] yeniden kullanilan pid'de 'sonlandir' "
                                 "onerisi YOK",
                                 not any("sonlandir" in s for s in sat_mb),
                                 " | ".join(sat_mb)[:90])
                # (2b) GOMULU MUTANT KANITI, ps'ten BAGIMSIZ: kodu (ps'i degil) bozan
                #      mutant kimligi KAYBEDER, GERCEK kod KAYBETMEZ. Iki uc birlikte
                #      olculur -> tek yon bozulunca kontrol KIRMIZI yanar.
                mut2 = mutant_yaz(td,
                                  "    satir = (p.stdout or \"\").strip()",
                                  "    satir = \"\"  # MUTANT: ps ciktisi yok sayiliyor",
                                  ad="durum_mutant_ps_sentetik.py")
                mmod2 = modul_yukle(mut2, "durum_mutant_ps_sentetik")
                bagimsiz_kontrol("[sentetik ps] _surec_bilgisi'ni olduren mutant kimligi "
                                 "KAYBEDIYOR, GERCEK kod KAYBETMIYOR",
                                 mmod2._surec_bilgisi(os.getpid())[0] is None
                                 and durum._surec_bilgisi(os.getpid())[0] is not None,
                                 "mutant=%s gercek=%s"
                                 % (mmod2._surec_bilgisi(os.getpid()),
                                    durum._surec_bilgisi(os.getpid())))
            # (3) KIMLIK (komut adi) NOBETI: kilit GENC (yeniden-kullanim yolu
            #     TETIKLENMEZ), ama komut python DEGIL -> sahip olamaz.
            with tempfile.TemporaryDirectory() as ftd:
                sahte_ps_path(ftd, "01:23", "launchd-SAHTE")
                kilit_yaz(os.getpid(), simdi - 10)
                d_kim = durum.kilit_durumu(kok)
                bagimsiz_kontrol("[sentetik ps] python OLMAYAN komut sahip SAYILMIYOR "
                                 "-> 'yarim' (kimlik mutanti burada olur)",
                                 d_kim["hal"] == "yarim" and d_kim["canli"] is False,
                                 "hal=%s canli=%s" % (d_kim["hal"], d_kim["canli"]))
            # (4) POZITIF NOBET — "hep yarim" DEGIL: surec kilitten ONCE basladi ve
            #     python; kilit genc -> NORMAL 'tutuluyor', pano SUSAR.
            #     (Bu ucu olmadan "canli hep False" diyen bir mutant yesil gecerdi.)
            with tempfile.TemporaryDirectory() as ftd:
                sahte_ps_path(ftd, "07:11:13", "python3-SAHTE")   # 25873 sn once basladi
                kilit_yaz(os.getpid(), simdi - 60)
                d_poz = durum.kilit_durumu(kok)
                bagimsiz_kontrol("[sentetik ps] kilitten ONCE baslamis python sahibi "
                                 "NORMAL: 'tutuluyor' + pano SUSUYOR",
                                 d_poz["hal"] == "tutuluyor" and d_poz["canli"] is True
                                 and durum.kilit_satirlari(d_poz) == [],
                                 "hal=%s canli=%s" % (d_poz["hal"], d_poz["canli"]))
        finally:
            os.environ["PATH"] = _eski_path
    # Enjeksiyon SIZINTI birakmadi mi (6i'deki geri-alma nobetcisinin emsali).
    kontrol("6h2 sonunda PATH GERI ALINDI (sentetik ps sizmadi)",
            os.environ.get("PATH", "") == _eski_path,
            "PATH uzunlugu=%d" % len(os.environ.get("PATH", "")))

    # ---------------- 6i) K3: "DEGISIKLIK YOK" != "YEDEK BAYAT" ----------------
    # `--gerekliyse` GUNCEL yolu hicbir sey kopyalamaz -> `zaman` ilerlemez. Degismeyen
    # bir sistemde pano 2 gun sonra BOSUNA "⚠⚠ YEDEK BAYAT" diyordu (gurultulu pano =
    # olu pano). Artik ayrim OLCUMLE yapilir: damgadaki `dogrulandi` + `dogrulama_imzasi`
    # ile kopyanin `kaynak_imzasi` KARSILASTIRILIR. Pano iddiaya GUVENMEZ, DOGRULAR.
    print("\n6i) K3 — dogrulanmis 'degisiklik yok' GUNCEL, dogrulanamayan OLCULEMEDI")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        imza = {"adet": 133, "bayt": 5771055, "mtime": simdi - 90000}
        # 🔴 K5 SART 5: pano artik KAYNAKLARIN SU ANKI imzasini da olcuyor. Fikstur
        # sentetik bir imza kullandigi icin canli olcum ENJEKTE edilir (aksi halde
        # gercek makinenin imzasi karsilastirmaya girer -> belirlenimsiz test).
        # Enjeksiyon deseni durum._agac_say ile ayni (6f'de kullanilan).
        _gercek_canli = durum._canli_kaynak_imzasi
        durum._canli_kaynak_imzasi = lambda: canli_olcum([imza])

        # (a) esik asildi AMA taze + ESLESEN dogrulama var -> ✅ GUNCEL
        a = damga_kur(os.path.join(td, "a"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza))
        d_a = durum.yedek_durumu(a, "var")
        sat_a = durum.yedek_satirlari(d_a)
        print("     --- pano ciktisi (K3 a: dogrulanmis guncel) ---")
        for s in sat_a:
            print("    " + s)
        kontrol("(a) hal 'guncel'", d_a["hal"] == "guncel", d_a["hal"])
        kontrol("(a) ILK SATIR '✅ GÜNCEL' + son gercek yedegi SOYLUYOR",
                "GÜNCEL" in sat_a[0] and "son gercek yedek" in sat_a[0], sat_a[0][:90])
        kontrol("(a) BAYAT uyarisi YOK (bosuna uyarmiyor)",
                not any("BAYAT" in s for s in sat_a))
        kontrol("(a) 'taze:' de DEMIYOR (durum ayri: kopyalama gerekmedi)",
                not sat_a[0].strip().startswith("taze:"), sat_a[0][:60])

        # (b) dogrulama VAR ama imzalar FARKLI (kaynak degismis) -> ⚪ OLCULEMEDI
        farkli = dict(imza)
        farkli["bayt"] = imza["bayt"] + 1
        b = damga_kur(os.path.join(td, "b"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=farkli)
        d_b = durum.yedek_durumu(b, "var")
        sat_b = durum.yedek_satirlari(d_b)
        kontrol("(b) imzalar farkli -> hal 'dogrulama-olculemedi'",
                d_b["hal"] == "dogrulama-olculemedi", d_b["hal"])
        kontrol("(b) ÖLÇÜLEMEDİ diyor, GUNCEL/taze DEMIYOR",
                "ÖLÇÜLEMEDİ" in sat_b[0] and "GÜNCEL" not in sat_b[0]
                and not sat_b[0].strip().startswith("taze:"), sat_b[0][:90])
        kontrol("(b) ne yapilacagini SOYLUYOR", "tools/yedekle.py" in " ".join(sat_b))

        # (c) dogrulamanin KENDISI bayat (3 gun once dogrulanmis) -> ⚠⚠ BAYAT
        c = damga_kur(os.path.join(td, "c"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 3 * 86400, dogrulama_imzasi=dict(imza))
        kontrol("(c) bayat dogrulama GUNCEL SAYILMIYOR -> 'bayat'",
                durum.yedek_durumu(c, "var")["hal"] == "bayat",
                durum.yedek_durumu(c, "var")["hal"])

        # (d) dogrulama HIC YOK -> BAYAT (regresyon nobeti: eski davranis korunuyor)
        d_yok = damga_kur(os.path.join(td, "d"), 3 * 86400)
        kontrol("(d) dogrulama yoksa yine 'bayat' (BAYAT hali OLU DEGIL)",
                durum.yedek_durumu(d_yok, "var")["hal"] == "bayat")

        # (e) `dogrulandi` var ama imza alanlari EKSIK -> OLCULEMEDI (sessiz yesil YOK)
        e = damga_kur(os.path.join(td, "e"), 3 * 86400, dogrulandi=simdi - 300)
        kontrol("(e) imza eksikken GUNCEL DEMIYOR -> 'dogrulama-olculemedi'",
                durum.yedek_durumu(e, "var")["hal"] == "dogrulama-olculemedi",
                durum.yedek_durumu(e, "var")["hal"])
        # (e2) imza alanlari SAYI DEGIL (bozuk yazim) -> yine OLCULEMEDI
        e2 = damga_kur(os.path.join(td, "e2"), 3 * 86400,
                       kaynak_imzasi={"adet": "133", "bayt": None, "mtime": True},
                       dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza))
        kontrol("(e2) bozuk imza turleri fail-closed (GUNCEL DEMIYOR)",
                durum.yedek_durumu(e2, "var")["hal"] == "dogrulama-olculemedi",
                durum.yedek_durumu(e2, "var")["hal"])
        # (e3) `dogrulandi` GELECEK tarihli -> yesil verilmez
        e3 = damga_kur(os.path.join(td, "e3"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi + 3600, dogrulama_imzasi=dict(imza))
        kontrol("(e3) gelecek tarihli dogrulama GUNCEL SAYILMIYOR",
                durum.yedek_durumu(e3, "var")["hal"] == "bayat",
                durum.yedek_durumu(e3, "var")["hal"])
        # (e4) 🔴 KARISIK SURUM DELIGI: damgaya EN SON dokunan kosum dogrulamayi
        # YAZMAMISSA yesil verilmez. Fikstur, BAYAT bir kardes worktree'nin ESKI
        # yedekle.py surumuyle kosmasinin BIREBIR izidir: `baslangic` ilerlemis
        # (o kosum damgaya dokundu) ama `dogrulandi` GERIDE kalmis (imza eksenini
        # bilmedigi icin dogrulama yazmadi, eski cifti dict(onceki) ile TASIDI).
        # Olculdu (scratchpad/karisik-surum.py): sart olmadan pano "✅ GUNCEL" diyordu
        # ve mtime KORUNARAK degismis dosya yedekte YOKTU.
        e4 = damga_kur(os.path.join(td, "e4"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi - 3600, dogrulama_imzasi=dict(imza),
                       baslangic=simdi - 300)          # damgaya SONRADAN dokunuldu
        d_e4 = durum.yedek_durumu(e4, "var")
        sat_e4 = durum.yedek_satirlari(d_e4)
        kontrol("(e4) dogrulamadan SONRA damgaya dokunulmussa GUNCEL DEMIYOR",
                d_e4["hal"] == "bayat" and "GÜNCEL" not in sat_e4[0],
                "%s | %s" % (d_e4["hal"], sat_e4[0][:60]))
        # ayni fikstur, `dogrulandi` == `baslangic` (YENI surumun uretecegi hal) -> GUNCEL
        e5 = damga_kur(os.path.join(td, "e5"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza),
                       baslangic=simdi - 300)
        kontrol("(e5) dogrulandi == baslangic ise GUNCEL (kontrol asiri-daralmadi)",
                durum.yedek_durumu(e5, "var")["hal"] == "guncel",
                durum.yedek_durumu(e5, "var")["hal"])
        # KIRMIZI-MUTASYON: sart kaldirilirsa (e4) sessizce GUNCEL olur
        mut_e4 = mutant_yaz(td,
                            "    if isinstance(ref, (int, float)) and not "
                            "isinstance(ref, bool) and dogrulandi < ref:\n"
                            "        return None                                   "
                            "# damgaya sonradan BASKASI dokundu",
                            "    if False:\n        return None  # MUTANT: sart yok",
                            ad="durum_mutant_karisik.py")
        mmod_e4 = modul_yukle(mut_e4, "durum_mutant_karisik")
        mmod_e4._canli_kaynak_imzasi = lambda: canli_olcum([imza])   # sart 5 nobeti ayri
        kontrol("MUTANTTA (karisik surum sarti yok) (e4) GUNCEL gorunuyor "
                "(kontrol KIRMIZI yanardi)",
                mmod_e4.yedek_durumu(e4, "var")["hal"] == "guncel",
                mmod_e4.yedek_durumu(e4, "var")["hal"])

        # (f) esik altinda dogrulama VARSA yine 'taze' (yeni hal eskiyi EZMESIN)
        f = damga_kur(os.path.join(td, "f"), 3600, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 60, dogrulama_imzasi=dict(imza))
        kontrol("(f) esik ALTINDA hal yine 'taze' (regresyon)",
                durum.yedek_durumu(f, "var")["hal"] == "taze",
                durum.yedek_durumu(f, "var")["hal"])
        # (g) KISMI yedek dogrulanmis olsa BILE basligi kismi uyarisi ALIR
        g = damga_kur(os.path.join(td, "g"), 3 * 86400, tam=False,
                      eksik=["DEVAM-ARSIV.md"], kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza))
        sat_g = durum.yedek_satirlari(durum.yedek_durumu(g, "var"))
        kontrol("(g) kismi yedek 'GUNCEL' basligina KACMIYOR",
                "KISMI YEDEK" in sat_g[0] and "GÜNCEL" not in sat_g[0], sat_g[0][:90])

        # KIRMIZI-MUTASYON 1: pano imzayi DOGRULAMAYI birakirsa (b) sessizce GUNCEL olur
        mut_g1 = mutant_yaz(td,
                            '    if not _imza_kullanilir(imza) or not _imza_kullanilir(kopya):\n'
                            '        return "olculemedi"',
                            '    if False:\n        return "olculemedi"\n'
                            '    return "guncel"  # MUTANT: iddiaya GUVENIYOR',
                            ad="durum_mutant_dogrulama.py")
        mmod_g1 = modul_yukle(mut_g1, "durum_mutant_dogrulama")
        kontrol("MUTANTTA (iddiaya guven) degismis kaynak GUNCEL gorunuyor "
                "(kontrol KIRMIZI yanardi)",
                mmod_g1.yedek_durumu(b, "var")["hal"] == "guncel",
                mmod_g1.yedek_durumu(b, "var")["hal"])
        # KIRMIZI-MUTASYON 2: 'guncel' hali oldurulurse (a) bosuna BAYAT der
        #   (POZITIF nobetci: yeni hal GERCEKTEN erisilebilir olmali)
        mut_g2 = mutant_yaz(td,
                            '    hal = _dogrulama_hali(damga, simdi, esik, '
                            'canli=_canli_kaynak_imzasi())',
                            '    hal = None  # MUTANT: dogrulama gorulmuyor\n'
                            '    _ = _dogrulama_hali',
                            ad="durum_mutant_guncelsiz.py")
        mmod_g2 = modul_yukle(mut_g2, "durum_mutant_guncelsiz")
        mmod_g2._canli_kaynak_imzasi = lambda: canli_olcum([imza])
        kontrol("MUTANTTA (dogrulama korlestirilmis) (a) BOSUNA 'bayat' diyor "
                "(kontrol KIRMIZI yanardi)",
                mmod_g2.yedek_durumu(a, "var")["hal"] == "bayat",
                mmod_g2.yedek_durumu(a, "var")["hal"])

        # ---- 6i2) 🔴 K5 / 6. TUR: KARDES SURUM DAMGAYA HIC DOKUNMAZSA ---------------
        # Curutucu olcumu: sart 2 yalniz `damga_tazele` CAGIRAN eski surume karsi
        # calisiyordu. `main`'in surumu `--gerekliyse` ATLA yolunda damgaya HIC
        # DOKUNMUYOR (14 worktree'nin 12'si o surumde) -> sart hic tetiklenmiyor ve
        # pano `✅ GUNCEL` kaliyordu, degisiklik yedekte YOKKEN. Cozum: tazelik artik
        # baska bir kosumun DAVRANISINDAN degil, OLCULEN ICERIKTEN turetilir.
        print("\n6i2) K5 — kapsam OLCULEN icerikten: kardes surum damgaya dokunmasa da")
        # (h) K5 SENARYOSU BIREBIR: damga tutarli (dogrulandi == baslangic, imzalar esit)
        #     ama KAYNAKLAR degismis (canli imza FARKLI) ve kardes kosum damgaya
        #     DOKUNMAMIS (baslangic ilerlememis) -> sart 2 sessiz, sart 5 YAKALAR.
        h = damga_kur(os.path.join(td, "h"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza),
                      baslangic=simdi - 300)
        canli_degismis = dict(imza)
        canli_degismis["bayt"] = imza["bayt"] + 4096      # mtime KORUNMUS icerik degisimi
        durum._canli_kaynak_imzasi = lambda: canli_olcum([canli_degismis])
        d_h = durum.yedek_durumu(h, "var")
        sat_h = durum.yedek_satirlari(d_h)
        print("     --- pano ciktisi (K5 h: kaynak degisti, kardes dokunmadi) ---")
        for s in sat_h:
            print("    " + s)
        kontrol("(h) K5: canli imza FARKLI -> hal 'kapsam-degisti'",
                d_h["hal"] == "kapsam-degisti", d_h["hal"])
        kontrol("(h) K5: pano '✅ GÜNCEL' DEMIYOR (sessiz yesil KAPANDI)",
                "GÜNCEL" not in sat_h[0] and not sat_h[0].strip().startswith("taze:"),
                sat_h[0][:100])
        kontrol("(h) K5: uyari NE oldugunu SOYLUYOR (kaynaklar DEGISTI)",
                "KAPSAMIYOR" in sat_h[0] and "DEGISTI" in sat_h[0], sat_h[0][:100])
        kontrol("(h) K5: ne yapilacagi yazili", "tools/yedekle.py" in " ".join(sat_h))
        # (h2) BASLANGIC HIC ILERLEMEMIS (kardes kosum damgayi gercekten hic yazmadi):
        #      sart 2'nin TANIM GEREGI sessiz kaldigi hal -> yine yakalanmali
        h2 = damga_kur(os.path.join(td, "h2"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza),
                       baslangic=simdi - 3 * 86400)      # damgaya sonradan DOKUNULMADI
        kontrol("(h2) K5: kardes damgaya HIC dokunmasa da yesil verilmiyor",
                durum.yedek_durumu(h2, "var")["hal"] == "kapsam-degisti",
                durum.yedek_durumu(h2, "var")["hal"])
        # (h3) POZITIF nobetci — asiri-daralma YOK: canli imza ESITSE yine GUNCEL
        durum._canli_kaynak_imzasi = lambda: canli_olcum([imza])
        kontrol("(h3) K5: canli imza ESIT ise hal yine 'guncel' (asiri-daralma YOK)",
                durum.yedek_durumu(h, "var")["hal"] == "guncel",
                durum.yedek_durumu(h, "var")["hal"])
        # (h4) `--sirlar` VARYANTI: damgayi hangi bayrakla kosan yedek yazdi bilinmez ->
        #      iki adaydan BIRI tutuyorsa kapsam saglanmistir (bosuna uyarma yok)
        durum._canli_kaynak_imzasi = lambda: canli_olcum([canli_degismis, imza])
        kontrol("(h4) K5: iki aday imzadan BIRI tutuyorsa GUNCEL (sirlar varyanti)",
                durum.yedek_durumu(h, "var")["hal"] == "guncel",
                durum.yedek_durumu(h, "var")["hal"])
        # (h4b) DAMGA BASKA KAYNAK AGACINA ait (yasanmis F1: ROOT worktree'ye dusuyordu,
        #       ayrica izole kum havuzu kosumlari) -> "degisti" diye BAGIRMAK yanlis
        #       alarmdir; dogru cevap GORUNUR 'olculemedi' (gurultulu pano = olu pano).
        h4b = damga_kur(os.path.join(td, "h4b"), 3 * 86400, kaynak_imzasi=dict(imza),
                        dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza),
                        baslangic=simdi - 300, kok="/baska/kaynak/agaci")
        durum._canli_kaynak_imzasi = lambda: canli_olcum([imza], kok="/gercek/agac")
        kontrol("(h4b) K5: damga BASKA agac icin yazilmissa 'kapsam-olculemedi' "
                "(yanlis alarm YOK)",
                durum.yedek_durumu(h4b, "var")["hal"] == "kapsam-olculemedi",
                durum.yedek_durumu(h4b, "var")["hal"])
        durum._canli_kaynak_imzasi = lambda: canli_olcum([imza],
                                                        kok="/baska/kaynak/agaci")
        kontrol("(h4c) K5: agac AYNI ise karsilastirma yapiliyor (asiri-daralma YOK)",
                durum.yedek_durumu(h4b, "var")["hal"] == "guncel",
                durum.yedek_durumu(h4b, "var")["hal"])
        # (h4d) 🔴 SYMLINK'LI YOL AYNI AGACTIR: macOS'ta /var -> /private/var; damgayi
        # yazan kosum bir yolu, panonun olcumu digerini gorebilir. Metin karsilastirmasi
        # (normpath) burada SAHTE uyusmazlik uretir ve pano her acilista bosuna
        # "olculemedi" der. GERCEK symlink ile olculur (sentetik dize yetmez: iki
        # fonksiyon sentetik dizede AYNI sonucu verir -> mutant kacar).
        _gercek = os.path.join(td, "agac-gercek")
        os.makedirs(_gercek)
        _bag = os.path.join(td, "agac-symlink")
        os.symlink(_gercek, _bag)
        h4d = damga_kur(os.path.join(td, "h4d"), 3 * 86400, kaynak_imzasi=dict(imza),
                        dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza),
                        baslangic=simdi - 300, kok=_bag)          # damga: SYMLINK yolu
        durum._canli_kaynak_imzasi = lambda: canli_olcum([imza], kok=_gercek)  # olcum: GERCEK
        kontrol("(h4d) K5: symlink'li yol ile gercek yol AYNI agac sayiliyor "
                "(sahte uyusmazlik YOK)",
                durum.yedek_durumu(h4d, "var")["hal"] == "guncel",
                "%s  (%s -> %s)" % (durum.yedek_durumu(h4d, "var")["hal"], _bag, _gercek))
        # (h5) CANLI IMZA OLCULEMEDI -> GORUNUR 'kapsam-olculemedi', sessiz yesil YOK
        durum._canli_kaynak_imzasi = lambda: None
        d_h5 = durum.yedek_durumu(h, "var")
        sat_h5 = durum.yedek_satirlari(d_h5)
        kontrol("(h5) K5: canli imza olculemezse hal 'kapsam-olculemedi'",
                d_h5["hal"] == "kapsam-olculemedi", d_h5["hal"])
        kontrol("(h5) K5: ÖLÇÜLEMEDİ diyor, GUNCEL/taze DEMIYOR",
                "ÖLÇÜLEMEDİ" in sat_h5[0] and "GÜNCEL" not in sat_h5[0]
                and not sat_h5[0].strip().startswith("taze:"), sat_h5[0][:100])
        # (h6) BOS aday listesi de olculemedi sayilir (fail-closed)
        durum._canli_kaynak_imzasi = lambda: canli_olcum([])
        kontrol("(h6) K5: bos aday listesi de 'kapsam-olculemedi' (fail-closed)",
                durum.yedek_durumu(h, "var")["hal"] == "kapsam-olculemedi",
                durum.yedek_durumu(h, "var")["hal"])
        # KIRMIZI-MUTASYON: sart 5 kaldirilirsa (h) sessizce GUNCEL olur
        durum._canli_kaynak_imzasi = lambda: canli_olcum([canli_degismis])
        mut_h = mutant_yaz(td,
                           "    if not isinstance(canli, dict) or not "
                           'canli.get("adaylar"):\n'
                           '        return "kapsam-olculemedi"',
                           "    if False:\n"
                           '        return "kapsam-olculemedi"\n'
                           '    return "guncel"  # MUTANT: sart 5 YOK',
                           ad="durum_mutant_kapsam.py")
        mmod_h = modul_yukle(mut_h, "durum_mutant_kapsam")
        mmod_h._canli_kaynak_imzasi = lambda: canli_olcum([canli_degismis])
        kontrol("MUTANTTA (sart 5 yok) (h) GUNCEL gorunuyor (kontrol KIRMIZI yanardi)",
                mmod_h.yedek_durumu(h, "var")["hal"] == "guncel",
                mmod_h.yedek_durumu(h, "var")["hal"])
        # KABLOLAMA NOBETCISI: canli olcum GERCEKTEN cagriliyor mu (enjeksiyon bir
        # test kolayligi; kod yolunun kendisi de baglanmis olmali)
        gov_k5 = open(DURUM, encoding="utf-8").read()
        kontrol("K5: _bayat_mi_guncel_mi canli imzayi GERCEKTEN gecirivor",
                "_dogrulama_hali(damga, simdi, esik, canli=_canli_kaynak_imzasi())" in gov_k5)
        kontrol("K5: canli olcum yedekle.py'nin TEK kaynagini kullaniyor "
                "(ikinci tanim YOK)",
                "yedekle.kaynak_imzasi(s)" in gov_k5 and "_yedekle_modulu()" in gov_k5)
        # GERCEK (enjeksiyonsuz) olcum ISLIYOR mu — ortam ekseninde
        durum._canli_kaynak_imzasi = _gercek_canli
        _canli_gercek = durum._canli_kaynak_imzasi()
        _kaynak_var = kaynak_ortami() == "var"
        ortam_kontrol("K5: GERCEK canli imza olcumu adet/bayt/mtime + kok dondurdu",
                      _kaynak_var,
                      isinstance(_canli_gercek, dict) and _canli_gercek.get("adaylar")
                      and isinstance(_canli_gercek.get("kok"), str)
                      and all(durum._imza_kullanilir(x)
                              for x in (_canli_gercek or {}).get("adaylar", [])),
                      str(_canli_gercek)[:130])
        # 🔴 IKI EKSENLI: hem yedeklenecek KAYNAK kumesi hem `git` gerekir. git yoksa
        # yedekle.ana_calisma_agaci() TANIM GEREGI __file__ tabanina duser (worktree'de
        # kosuluyorsa kok worktree'dir) -> bu, olculecek bir DAVRANIS degil, ORTAM
        # eksikligidir. 7. turda korumasizdi: git'siz makinede KIRMIZI yaniyordu.
        git_kontrol("K5: GERCEK olcum ANA calisma agacini gosteriyor (worktree DEGIL)",
                    ".claude/worktrees" not in (_canli_gercek or {}).get("kok", "x"),
                    (_canli_gercek or {}).get("kok"),
                    ek_ortam=_kaynak_var,
                    ek_ayrinti="yedeklenecek KAYNAK kumesi bu makinede yok "
                               "(fresh checkout / bos HOME) — olculemez")
        # FAIL-CLOSED yon: kaynak YOKKEN olcum None DONMELI (uydurma imza URETMEMELI)
        kontrol("K5: kaynak yoksa olcum None doner (uydurma imza YOK)",
                _kaynak_var or _canli_gercek is None,
                "kaynak=%s olcum=%s" % (kaynak_ortami(), str(_canli_gercek)[:60]))
        # ---- 6i) SONU: enjeksiyon GERI ALINDI (sizinti yok) ----
        kontrol("6i sonunda canli olcum GERCEK fonksiyona geri alindi",
                durum._canli_kaynak_imzasi is _gercek_canli)

    # ---------------- 6f) N3: ZAMAN ASIMI — PANO ASILMAZ ----------------
    print("\n6f) N3 — Drive yanit vermezse pano BEKLEMEZ")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 60)
        eski_say, eski_asim = durum._agac_say, durum.YEDEK_ZAMAN_ASIMI

        def asili_say(dizin):                      # yanit vermeyen mount taklidi
            time.sleep(2.0)
            return 0

        try:
            durum._agac_say = asili_say
            durum.YEDEK_ZAMAN_ASIMI = 0.2
            bas = time.time()
            sonuc, asildi = durum.zaman_asimiyla(
                lambda: durum.yedek_satirlari(durum.yedek_durumu(b, "var")))
            sure = time.time() - bas
            kontrol("zaman asimina DUSTU", asildi is True)
            kontrol("sure SINIRLI (<1 sn)", sure < 1.0, "%.3f sn" % sure)
            kontrol("sonuc dondurulmedi (terk edildi)", sonuc is None)

            # KIRMIZI-MUTASYON: zaman asimi kaldirilirsa asili mount panoyu bekletir
            mut = mutant_yaz(td,
                             "    ip = threading.Thread(target=sar, daemon=True)",
                             "    sar()  # MUTANT: zaman asimi YOK\n"
                             "    return kutu.get('sonuc'), False\n"
                             "    ip = threading.Thread(target=sar, daemon=True)",
                             ad="durum_mutant_asim.py")
            mmod = modul_yukle(mut, "durum_mutant_asim")
            mmod._agac_say = asili_say
            mmod.YEDEK_ZAMAN_ASIMI = 0.2
            bas = time.time()
            _s, m_asildi = mmod.zaman_asimiyla(
                lambda: mmod.yedek_satirlari(mmod.yedek_durumu(b, "var")))
            m_sure = time.time() - bas
            kontrol("MUTANTTA zaman asimi YOK (asili mount panoyu bekletti)",
                    m_asildi is False and m_sure >= 1.5, "%.3f sn" % m_sure)
        finally:
            durum._agac_say, durum.YEDEK_ZAMAN_ASIMI = eski_say, eski_asim
        kontrol("saglam olcum zaman asimina DUSMUYOR",
                durum.zaman_asimiyla(lambda: "ok") == ("ok", False))
        kontrol("varsayilan zaman asimi makul (1-30 sn)",
                1 <= durum.YEDEK_ZAMAN_ASIMI <= 30, str(durum.YEDEK_ZAMAN_ASIMI))
        # KABLOLAMA NOBETCISI: yardimci VAR ama main() onu KULLANMIYORSA yukaridaki
        # davranissal kanit anlamsizdir (gercek Drive'i asili yapamadigimiz icin
        # uctan uca olculemiyor) -> kaynak capasiyla baglanti dogrulanir.
        gov = open(DURUM, encoding="utf-8").read()
        kontrol("main() olcumu zaman_asimiyla ile sariyor", "zaman_asimiyla(_olc)" in gov)
        kontrol("zaman asimi mesaji panoda tanimli", "Drive yanit vermiyor" in gov)

    # ---------------- 7) UCTAN UCA: gercek pano ----------------
    print("\n7) UCTAN UCA — python3 tools/durum.py")
    r = subprocess.run([sys.executable, DURUM], capture_output=True, text=True)
    kontrol("exit 0", r.returncode == 0, "rc=%d" % r.returncode)
    kontrol("'7) YEDEK TAZELIGI' bolumu basildi", "7) YEDEK TAZELIGI" in r.stdout)
    kontrol("bolum bos degil", any(
        x in r.stdout for x in ("taze:", "BAYAT", "ÖLÇÜLEMEDİ", "backup/ klasoru YOK")))

    # ---------------- 8) UCTAN UCA: DRIVE YOKKEN COKMUYOR ----------------
    print("\n8) UCTAN UCA — Drive'siz makinede pano cokmemeli (exit 0)")
    with tempfile.TemporaryDirectory() as td:
        sahte_ev = os.path.join(td, "ev")
        kok = os.path.join(td, "repo")
        os.makedirs(os.path.join(kok, "tools"))
        os.makedirs(sahte_ev)
        shutil.copy2(DURUM, os.path.join(kok, "tools", "durum.py"))
        shutil.copy2(DRIVE_YOLU, os.path.join(kok, "tools", "drive_yolu.py"))
        # 🔴 GIT EKSENI (8. tur onarimi): burasi KORUMASIZ `git` cagiriyordu ->
        # `git` PATH'te yokken YAKALANMAMIS FileNotFoundError, adim rc 1, `deploy:
        # needs: build` ile TUM YAYIN DURUYORDU (ps ekseninde kapatilan arizanin
        # AYNISI). Artik ORTAM sorgulanir: git yoksa fikstur git DEPOSU OLMADAN kosar
        # (asagidaki uc kontrol BLOKLAYICI kalir) ve eksik olcum GORUNUR ⚪ [git] olur.
        if GIT_ORTAMI[0] == "var":
            subprocess.run(["git", "-C", kok, "init", "-q"], capture_output=True)
            GIT_BAGIMLI[0] += 1
            kontrol("8) fikstur GIT DEPOSU olarak kuruldu (pano repo baglaminda olculdu)",
                    os.path.isdir(os.path.join(kok, ".git")))
        else:
            GIT_BAGIMLI[0] += 1
            olculemedi("8) fikstur GIT DEPOSU olarak kuruldu (pano repo baglaminda olculdu)",
                       "`git` ortami '%s' — fikstur deposu kurulamaz; asagidaki cokme "
                       "kontrolleri yine BLOKLAYICI kosar" % GIT_ORTAMI[0], eksen="git")
        ortam = dict(os.environ)
        ortam["HOME"] = sahte_ev                 # Drive mount deseni HICBIR SEYE uymaz
        r = subprocess.run([sys.executable, os.path.join(kok, "tools", "durum.py")],
                           capture_output=True, text=True, env=ortam)
        kontrol("Drive'siz pano exit 0 (COKMEDI)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, r.stderr.strip()[:120]))
        kontrol("ÖLÇÜLEMEDİ yazdi", "ÖLÇÜLEMEDİ" in r.stdout)
        kontrol("traceback YOK", "Traceback" not in r.stderr)

        # ---- 8b) GIT'SIZ PATH ile AYNI PANO — SENTETIK, ORTAMDAN BAGIMSIZ ----
        # 🔴 NEDEN SENTETIK: makinede `git` varsa da yoksa da AYNI olcum yapilsin.
        # (6h2'nin `ps` icin yaptigini bu blok `git` icin yapar: nobetci, korudugu
        # kosulun ICINE konmaz.) durum.git() eskiden FileNotFoundError firlatiyordu ->
        # PANONUN KENDISI cokuyordu; bu kontrol o cokusun geri gelmesini engeller.
        bos_kutu = os.path.join(td, "gitsiz-bin")
        os.makedirs(bos_kutu)
        ortam_gitsiz = dict(ortam)
        ortam_gitsiz["PATH"] = bos_kutu           # `git` (ve `ps`) BULUNAMAZ
        r_g = subprocess.run([sys.executable, os.path.join(kok, "tools", "durum.py")],
                             capture_output=True, text=True, env=ortam_gitsiz)
        bagimsiz_kontrol("[sentetik gitsiz PATH] pano exit 0 (COKMEDI)",
                         r_g.returncode == 0,
                         "rc=%d %s" % (r_g.returncode, r_g.stderr.strip()[:120]))
        bagimsiz_kontrol("[sentetik gitsiz PATH] traceback YOK "
                         "(FileNotFoundError: 'git' geri gelmedi)",
                         "Traceback" not in r_g.stderr and "FileNotFoundError"
                         not in r_g.stderr, r_g.stderr.strip()[-120:])
        # durum.git() SOZLESMESI: git yoksa ISTISNA DEGIL (cikti, rc!=0) doner.
        try:
            _g_cikti, _g_rc = "", None
            _eski_p = os.environ.get("PATH", "")
            os.environ["PATH"] = bos_kutu
            try:
                _g_cikti, _g_rc = durum.git(kok, "rev-parse", "--show-toplevel")
            finally:
                os.environ["PATH"] = _eski_p
            _g_ok = _g_rc not in (0, None) and _g_cikti == ""
        except OSError as e:                      # try/except kaldirilirsa buraya duser
            _g_ok, _g_rc = False, "ISTISNA: %s" % e
        bagimsiz_kontrol("[sentetik gitsiz PATH] durum.git() ISTISNA ATMIYOR, "
                         "cikis kodu != 0 donuyor (fail-soft sozlesme)",
                         _g_ok, "rc=%s cikti=%r" % (_g_rc, _g_cikti))

    # ---------------- 9) K4: `ps` YOKKEN KAPI YAYINI DURDURMAZ ----------------
    # Kendini `ps`siz bir PATH ile YENIDEN cagirir (gercek ortam yoklugu taklidi).
    # Iddia: cikis 0 + ps'e bagli kontrollerin HEPSI ⚪ OLCULEMEDI olarak GORUNUR.
    # Sayi SABIT YAZILMAZ: alt kosumun kendi ilan ettigi "PS BAGIMLI" sayisiyla
    # OLCULEMEDI sayisi karsilastirilir (veri capasi bayatlamasin).
    if ALT_KOSUM not in sys.argv:
        print("\n9) K4 — `ps` YOKKEN: exit 0 + gorunur ⚪ OLCULEMEDI (yayin durmaz)")
        with tempfile.TemporaryDirectory() as td:
            kutu = os.path.join(td, "bin")
            os.makedirs(kutu)
            git_yolu = shutil.which("git")            # git gerekli (durum.py + fikstur)
            if git_yolu:
                os.symlink(git_yolu, os.path.join(kutu, "git"))
            ortam = dict(os.environ)
            ortam["PATH"] = kutu                      # `ps` PATH'te YOK
            r_ps = subprocess.run([sys.executable, os.path.abspath(__file__), ALT_KOSUM],
                                  capture_output=True, text=True, env=ortam)
            cik = r_ps.stdout

            def _sayi(onek):
                for s in cik.splitlines():
                    if s.startswith(onek):
                        try:
                            return int(s[len(onek):].split()[0])
                        except (ValueError, IndexError):
                            return None
                return None

            kontrol("ps YOKKEN alt kosum exit 0 (TUM SITE YAYINI durmaz)",
                    r_ps.returncode == 0,
                    "rc=%d %s" % (r_ps.returncode, r_ps.stderr.strip()[:100]))
            kontrol("ps YOKKEN alt kosum `ps`i GERCEKTEN bulamadi (fikstur ISIRIYOR)",
                    "PS: YOK" in cik,
                    " ".join(s for s in cik.splitlines() if s.startswith("PS:")))
            kontrol("ps YOKKEN cikti ⚪ ÖLÇÜLEMEDİ basiyor (sessiz yesil DEGIL)",
                    "⚪ ÖLÇÜLEMEDİ" in cik)
            kontrol("ps YOKKEN ozet OLCULEMEDI SAYISINI yaziyor (CI log'unda goze batar)",
                    _sayi("OLCULEMEDI: ") is not None, str(_sayi("OLCULEMEDI: ")))
            # ps EKSENINDEKI ⚪ SAYISI = ILAN EDILEN ps-bagimli kontrol SAYISI.
            # (Toplam ⚪ ile karsilastirmak YANLIS olur: baska eksenler de ⚪ uretebilir —
            # CI taklidinde kaynak ekseni tam bunu yapti.)
            kontrol("ps YOKKEN ps-ekseni ⚪ sayisi = ilan edilen ps-bagimli sayisi",
                    _sayi("PS EKSEN OLCULEMEDI: ") == _sayi("PS BAGIMLI: ")
                    and (_sayi("PS BAGIMLI: ") or 0) > 0,
                    "ps-eksen-⚪=%s / ps-bagimli=%s"
                    % (_sayi("PS EKSEN OLCULEMEDI: "), _sayi("PS BAGIMLI: ")))
            # HER ⚪ EKSENINI ILAN ETMELI: eksensiz ⚪ = sebebi yazilmamis atlama.
            kontrol("ps YOKKEN her ⚪ ortam eksenini ILAN ETMIS (eksensiz 0)",
                    _sayi("EKSENSIZ OLCULEMEDI: ") == 0,
                    "eksensiz=%s" % _sayi("EKSENSIZ OLCULEMEDI: "))
            # ...ve SAYAC degil, BASILAN SATIR olculur: ozet sayaci dogru kalirken
            # listeleme "[?]" basan bir mutasyon olculdu ve YUKARIDAKI kontrolden
            # KACIYORDU. CI log'unu okuyan kisi hangi bagimliligin eksik oldugunu
            # satirin ETIKETINDEN gorur -> etiket, ⚪'nin kendisi kadar zorunludur.
            _etiketli = [s for s in cik.splitlines() if "⚪ ÖLÇÜLEMEDİ [" in s]
            _bilinmeyen = [s for s in _etiketli
                           if not any("[%s]" % e in s for e in BILINEN_EKSENLER)]
            kontrol("ps YOKKEN BASILAN her ⚪ satiri BILINEN eksen etiketi tasiyor",
                    len(_etiketli) > 0 and not _bilinmeyen,
                    "etiketli=%d bilinmeyen=%d %s"
                    % (len(_etiketli), len(_bilinmeyen),
                       _bilinmeyen[0].strip()[:70] if _bilinmeyen else ""))
            kontrol("ps YOKKEN kapinin GERI KALANI hala BLOKLAYICI (kirmizi 0 + coklu yesil)",
                    _sayi("KIRMIZI: ") == 0 and (_sayi("GECTI: ") or 0) > 50,
                    "gecti=%s kirmizi=%s" % (_sayi("GECTI: "), _sayi("KIRMIZI: ")))
            # 🔴 NOBETCININ NOBETCISI (8. tur): ORTAMDAN BAGIMSIZ nobetler (6h2 + 8b)
            # `ps` YOKKEN de AYNEN kosmali — 7. turda sessiz yesile kacan iki mutant
            # tam bu nobetin yoklugundan kacti.
            # ⚠️ SAYAC KARSILASTIRMASI TEK BASINA YETMEZ (olculdu): bir nobeti
            # ps_kontrol'e sarmak sayaci ANA ve ALT kosumda ESIT dusurur -> mutant
            # kacardi. O yuzden alt kosumun CIKTISI okunur: "[sentetik…" isaretli
            # satirlarin ✅ olani ilan edilen sayiya ESIT, ⚪ olani SIFIR olmali.
            # Sabit sayi YOK; iki kosumun kendi ilan ettikleri karsilastirilir.
            _ok_sent = sum(1 for s in cik.splitlines() if s.startswith("  ✅ [sentetik"))
            _beyaz_sent = sum(1 for s in cik.splitlines()
                              if "ÖLÇÜLEMEDİ" in s and "[sentetik" in s)
            kontrol("ps YOKKEN ORTAMDAN BAGIMSIZ nobetler AYNEN kostu "
                    "(alt kosumda ✅ = ilan, ⚪ = 0)",
                    _ok_sent == BAGIMSIZ_NOBET[0] and BAGIMSIZ_NOBET[0] > 0
                    and _beyaz_sent == 0,
                    "alt-✅=%d alt-⚪=%d ana-ilan=%d"
                    % (_ok_sent, _beyaz_sent, BAGIMSIZ_NOBET[0]))
            # Ozetteki ILAN ile CIKTIDAKI gercek de uyusmali (ozet satirini uyduran
            # bir mutasyon buradan yakalanir).
            kontrol("ps YOKKEN ozetteki 'BAGIMSIZ NOBET' ilani ciktiyla UYUSUYOR",
                    _sayi("BAGIMSIZ NOBET: ") == _ok_sent and _ok_sent > 0,
                    "ilan=%s cikti=%d" % (_sayi("BAGIMSIZ NOBET: "), _ok_sent))
            # 🔴 K4 MERGE BLOKLAYICISININ TA KENDISI (6. tur): bu iddia KOSULSUZ
            # bloklayiciydi -> `ps` YOKKEN kapi rc=1 veriyor, `deploy: needs: build`
            # zinciri yuzunden TUM pruvo3d.com yayini duruyordu. Artik ORTAM ekseninde
            # ucce ayrilir; "yok" tek basina yayini durdurmaz, "bozuk" DURDURUR.
            if PS_ORTAMI[0] == "yok":
                PS_BAGIMLI[0] += 1            # "⚪ == ilan edilen ortam bagimliligi"
                olculemedi("ps VARKEN ps-ekseninde OLCULEMEDI 0 (kapi TAM olcuyor)",
                           "`ps` binary'si PATH'te YOK — bu makinede kapinin TAM "
                           "olcumu yapilamaz (yayin BLOKLANMAZ; bkz. K4)", eksen="ps")
            else:
                # "var" -> nobetci CANLI: ps'e bagli hicbir kontrol OLCULEMEDI'ye
                # KACAMAZ (_surec_bilgisi'ni olduren mutantin kacis yolu buydu).
                # "bozuk" -> fail-closed KIRMIZI (bozuk bagimlilik yayini durdurur).
                # ⚠️ YALNIZ ps EKSENI sayilir: alakasiz bir eksenin ⚪'si (or. CI'da
                # kaynak kumesinin yoklugu) bu nobetciyi kirmiziya cevirmemeli — CI
                # taklidinde olculdu, tam bu olmustu.
                kontrol("ps VARKEN ps-ekseninde OLCULEMEDI 0 (kapi TAM olcuyor)",
                        PS_ORTAMI[0] == "var" and EKSEN.get("ps", 0) == 0,
                        "ps_ortami=%s ps-eksen-⚪=%d (toplam ⚪=%d)"
                        % (PS_ORTAMI[0], EKSEN.get("ps", 0), len(OLCULEMEDI)))
            # AYNI NOBET, KAYNAK EKSENI: kaynak kumesi VARSA hicbir kontrol
            # "kaynak yok" kilifina kacamaz (aksi halde K5 sessizce olculmez olurdu).
            if kaynak_ortami() == "var":
                kontrol("kaynak VARKEN kaynak-ekseninde OLCULEMEDI 0",
                        EKSEN.get("kaynak", 0) == 0,
                        "kaynak-eksen-⚪=%d" % EKSEN.get("kaynak", 0))
            else:
                ORTAM_BAGIMLI[0] += 1
                olculemedi("kaynak VARKEN kaynak-ekseninde OLCULEMEDI 0",
                           "yedeklenecek KAYNAK kumesi yok — bu nobet burada "
                           "kosulamaz", eksen="kaynak")
            # AYNI NOBET, GIT EKSENI (8. tur): git VARSA hicbir kontrol "git yok"
            # kilifina kacamaz; git BOZUKSA fail-closed KIRMIZI (ROOT sessizce
            # worktree'ye duser -> 26 Tem'in "sahte tazelik" veri kaybi sinifi).
            if GIT_ORTAMI[0] == "yok":
                GIT_BAGIMLI[0] += 1
                olculemedi("git VARKEN git-ekseninde OLCULEMEDI 0 (kapi TAM olcuyor)",
                           "`git` binary'si PATH'te YOK — bu makinede kapinin TAM "
                           "olcumu yapilamaz (yayin BLOKLANMAZ; bkz. git_ortami)",
                           eksen="git")
            else:
                kontrol("git VARKEN git-ekseninde OLCULEMEDI 0 (kapi TAM olcuyor)",
                        GIT_ORTAMI[0] == "var" and EKSEN.get("git", 0) == 0,
                        "git_ortami=%s git-eksen-⚪=%d (toplam ⚪=%d)"
                        % (GIT_ORTAMI[0], EKSEN.get("git", 0), len(OLCULEMEDI)))
            # AYNI NOBET, LAUNCHD EKSENI: pid=1 (launchd/init) 'asili' surrogati VARSA
            # (macOS: launchd gunlerdir canli) pid=1 mutant nobeti GERCEKTEN kosmali ->
            # launchd ekseninde ⚪ 0. Surrogat YOKSA (taze-boot CI runner) ⚪ >=1 BEKLENIR
            # (fail-open): bu nobet burada kosulamaz, deploy DURMAZ. Bu, "launchd_ortami'yi
            # hep 'var' dondur" diye olduren bir mutasyonun (macOS'ta ⚪'yi gizleyip
            # sessiz-yesil verecek) kacis yolunu da kapatir.
            if LAUNCHD_ORTAMI[0] == "var":
                kontrol("launchd surrogati VARKEN launchd-ekseninde OLCULEMEDI 0 "
                        "(pid=1 mutant nobeti GERCEKTEN kostu)",
                        EKSEN.get("launchd", 0) == 0,
                        "launchd_ortami=%s launchd-eksen-⚪=%d"
                        % (LAUNCHD_ORTAMI[0], EKSEN.get("launchd", 0)))
            else:
                LAUNCHD_BAGIMLI[0] += 1
                olculemedi("launchd surrogati VARKEN launchd-ekseninde OLCULEMEDI 0",
                           "pid=1 (launchd/init) 'asili' surrogati bu ortamda yok "
                           "(taze-boot runner / ps yok) — bu nobet burada kosulamaz",
                           eksen="launchd")

            # ---- 9b) ORTAM SINIFLANDIRICISININ KENDI KABUL FIKSTURLERI ----
            # 🔴 NEDEN: artik "yok" hali rc'yi BOZMUYOR -> ps_ortami()'yi "hep yok
            # dondur" diye olduren bir mutasyon TUM ps eksenini sessizce ⚪'ya cevirip
            # YESIL yanardi. Bu fiksturler SENTETIK PATH ile kosar, yani GERCEK ortamdan
            # BAGIMSIZ: `ps` olmayan bir makinede de mutant kirmizi yanar.
            print("\n9b) ps_ortami() siniflandiricisi — sentetik PATH fiksturleri")
            eski_path = os.environ.get("PATH", "")
            SAHTE = {                             # ad -> (govde, beklenen hal)
                "yok": (None, "yok"),
                "calisan": ("#!/bin/sh\necho '01:23 python3'\nexit 0\n", "var"),
                "bos-cikti": ("#!/bin/sh\nexit 0\n", "bozuk"),
                "rc1": ("#!/bin/sh\necho hata\nexit 1\n", "bozuk"),
                "calistirilamaz": ("bu bir betik DEGIL\n", "bozuk"),
                # ASILI ps: zaman asimi gecici olarak 0,3 sn'ye cekilir -> gercek 5 sn
                # beklemeden "asili -> bozuk" yolu KANITLANIR (kapi hizli kalir).
                "asili": ("#!/bin/sh\nsleep 5\n", "bozuk"),
            }
            try:
                for ad in sorted(SAHTE):
                    govde, beklenen = SAHTE[ad]
                    PS_SORGU_ZAMAN_ASIMI[0] = 0.3 if ad == "asili" else 5.0
                    with tempfile.TemporaryDirectory() as ftd:
                        kutu2 = os.path.join(ftd, "bin")
                        os.makedirs(kutu2)
                        if govde is not None:
                            sahte_ps = os.path.join(kutu2, "ps")
                            with open(sahte_ps, "w") as fh:
                                fh.write(govde)
                            os.chmod(sahte_ps, 0o755)
                        os.environ["PATH"] = kutu2
                        gorulen = ps_ortami()
                    kontrol("ps_ortami() '%s' fiksturunu '%s' diye siniflandiriyor"
                            % (ad, beklenen), gorulen == beklenen, "gorulen=%s" % gorulen)
            finally:
                os.environ["PATH"] = eski_path
                PS_SORGU_ZAMAN_ASIMI[0] = 5.0
            kontrol("ps_ortami() gercek ortami ILAN ETTIGI gibi goruyor (tekrarlanabilir)",
                    ps_ortami() == PS_ORTAMI[0], "%s == %s" % (ps_ortami(), PS_ORTAMI[0]))
            kontrol("varsayilan `ps` zaman asimi makul (1-15 sn)",
                    1 <= PS_SORGU_ZAMAN_ASIMI[0] <= 15, str(PS_SORGU_ZAMAN_ASIMI[0]))

            # ---- 9c) `git` SINIFLANDIRICISININ KENDI KABUL FIKSTURLERI ----
            # 9b ile AYNI gerekce: "yok" hali artik rc'yi bozmuyor -> git_ortami()'yi
            # "hep yok dondur" diye olduren bir mutasyon git eksenini sessizce ⚪'ya
            # cevirip YESIL yanardi. Sentetik PATH => gercek ortamdan BAGIMSIZ olcum.
            print("\n9c) git_ortami() siniflandiricisi — sentetik PATH fiksturleri")
            eski_path = os.environ.get("PATH", "")
            SAHTE_GIT = {                         # ad -> (govde, beklenen hal)
                "yok": (None, "yok"),
                "calisan": ("#!/bin/sh\necho 'git version 2.39.0'\nexit 0\n", "var"),
                "bos-cikti": ("#!/bin/sh\nexit 0\n", "bozuk"),
                "rc1": ("#!/bin/sh\necho hata\nexit 1\n", "bozuk"),
                "calistirilamaz": ("bu bir betik DEGIL\n", "bozuk"),
                "asili": ("#!/bin/sh\nsleep 5\n", "bozuk"),
            }
            try:
                for ad in sorted(SAHTE_GIT):
                    govde, beklenen = SAHTE_GIT[ad]
                    GIT_SORGU_ZAMAN_ASIMI[0] = 0.3 if ad == "asili" else 5.0
                    with tempfile.TemporaryDirectory() as ftd:
                        kutu3 = os.path.join(ftd, "bin")
                        os.makedirs(kutu3)
                        if govde is not None:
                            sahte_git = os.path.join(kutu3, "git")
                            with open(sahte_git, "w") as fh:
                                fh.write(govde)
                            os.chmod(sahte_git, 0o755)
                        os.environ["PATH"] = kutu3
                        gorulen = git_ortami()
                    kontrol("git_ortami() '%s' fiksturunu '%s' diye siniflandiriyor"
                            % (ad, beklenen), gorulen == beklenen, "gorulen=%s" % gorulen)
            finally:
                os.environ["PATH"] = eski_path
                GIT_SORGU_ZAMAN_ASIMI[0] = 5.0
            kontrol("git_ortami() gercek ortami ILAN ETTIGI gibi goruyor (tekrarlanabilir)",
                    git_ortami() == GIT_ORTAMI[0],
                    "%s == %s" % (git_ortami(), GIT_ORTAMI[0]))
            kontrol("varsayilan `git` zaman asimi makul (1-15 sn)",
                    1 <= GIT_SORGU_ZAMAN_ASIMI[0] <= 15, str(GIT_SORGU_ZAMAN_ASIMI[0]))

            # ---- 9d) launchd_ortami() SINIFLANDIRICISININ KENDI KABUL FIKSTURLERI ----
            # 9b/9c ile AYNI gerekce: launchd_ortami()'yi "hep yok dondur" diye olduren
            # bir mutasyon pid=1 mutant nobetini sessizce ⚪'ya cevirir, "hep var dondur"
            # diye olduren bir mutasyon taze-boot CI'da SAHTE-KIRMIZI yakar. Sentetik `ps`
            # (pid=1'i istedigimiz etime/comm ile raporlar) => GERCEK ortamdan BAGIMSIZ
            # olcum: bu makinede pid=1 ne olursa olsun siniflandirici KIRMIZI yanar.
            print("\n9d) launchd_ortami() siniflandiricisi — sentetik `ps` (pid=1) fiksturleri")
            eski_path = os.environ.get("PATH", "")
            YASLI = "%02d:00:00" % (int(LAUNCHD_MUT_KILIT_YASI // 3600) + 2)  # esikten YASLI
            SAHTE_LD = {                          # ad -> (etime, komut, beklenen hal)
                "eski-launchd": (YASLI, "launchd", "var"),    # yasli + python-disi -> surrogat VAR
                "taze-init":    ("00:05:00", "systemd", "yok"),   # 300 sn < esik -> taze-boot CI
                "python-pid1":  (YASLI, "python3", "yok"),    # pid=1 python -> fikstur anlamsiz
                "cozulemez":    ("COZULEMEZ", "launchd", "yok"),  # etime ayristirilamaz -> yok
            }
            try:
                for ad in sorted(SAHTE_LD):
                    etime_s, komut_s, beklenen = SAHTE_LD[ad]
                    with tempfile.TemporaryDirectory() as ftd:
                        kutu4 = os.path.join(ftd, "bin")
                        os.makedirs(kutu4)
                        sahte_ps = os.path.join(kutu4, "ps")
                        with open(sahte_ps, "w") as fh:
                            fh.write("#!/bin/sh\necho '   %s %s'\nexit 0\n"
                                     % (etime_s, komut_s))
                        os.chmod(sahte_ps, 0o755)
                        os.environ["PATH"] = kutu4
                        gorulen = launchd_ortami()
                    kontrol("launchd_ortami() '%s' fiksturunu '%s' diye siniflandiriyor"
                            % (ad, beklenen), gorulen == beklenen, "gorulen=%s" % gorulen)
                # `ps` HIC YOK -> "yok" (ps ekseniyle ayni sinif; pid=1 olculemez)
                with tempfile.TemporaryDirectory() as ftd:
                    kutu4 = os.path.join(ftd, "bin")
                    os.makedirs(kutu4)
                    os.environ["PATH"] = kutu4
                    gorulen = launchd_ortami()
                kontrol("launchd_ortami() `ps` YOKKEN 'yok' diye siniflandiriyor",
                        gorulen == "yok", "gorulen=%s" % gorulen)
            finally:
                os.environ["PATH"] = eski_path
            kontrol("launchd_ortami() gercek ortami ILAN ETTIGI gibi goruyor (tekrarlanabilir)",
                    launchd_ortami() == LAUNCHD_ORTAMI[0],
                    "%s == %s" % (launchd_ortami(), LAUNCHD_ORTAMI[0]))

    # ---------------- 10) YEDEKLE 3 GUVENCE — CI-KOSULABILIR DAVRANISSAL NOBET ----------------
    # AXIS-3 KAPATMA: flock / damga-finally-degil / cikis-damgasi-basari-yolunda
    # guvenceleri SIMDIYE DEK yalniz CI-MUAF yedekle-test.py'de olculuyordu. Burada
    # tam-izole (sahte HOME + sahte git deposu + drive_yolu STUB'u) DAVRANISSAL
    # nobetlerle olculur -> taze ubuntu-latest runner'da (bos HOME, gitignore'lu dosya
    # yok) da KOSAR. Alt kosumda (ps-siz PATH taklidi) KOSTURULMAZ: bu nobetler kendi
    # sahte ortamini kurar, ps/git eksenleriyle ilgisi yoktur (gereksiz maliyet + delikat
    # alt-kosum muhasebesini bozma riski). Env-bagimsizligin kendi kaniti asagidaki
    # bos-HOME alt kosumundadir (RAPOR-MIMARA kabul).
    if ALT_KOSUM not in sys.argv:
        print("\n10) YEDEKLE 3 GUVENCE (flock / damga-finally-degil / cikis-damgasi) "
              "— tam-izole DAVRANISSAL, env-bagimsiz")
        yb = modul_yukle(YEDEKLE, "yedekle_guvence")   # yalniz sabitler + _sahip_imzasi

        # --- POZITIF MUTANTLAR: her biri TEK guvenceyi yedekle.py KOPYASINDAN kaldirir ---
        MUT_FLOCK = ("        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)",
                     "        pass  # MUTANT: flock cagrisi silindi (serilestirme yok)")
        MUT_FINALLY = ("    basardi = False",
                       "    basardi = True  # MUTANT: basari izi finally'de kosulsuz "
                       "(istisna yolu sahte-yesil)")
        MUT_CIKIS = (
            "    bas_imza = kaynak_imzasi(sirlar)",
            "    bas_imza = kaynak_imzasi(sirlar)\n"
            "    damga_yaz(backup, {'memory': 0, 'skills': 0, 'repo': 0}, "
            "eksik=repo_eksikleri(), baslangic=baslangic, kilitsiz=kilitsiz, imza=bas_imza)"
            "  # MUTANT: cikis damgasi basari-yolundan alindi (basta yaziliyor)")

        # --- (d) IMZA KAPSAMI (bolum 11): imza kumesi = KOPYA PLANI --------------
        # 🔴 MUTANT NE YAPAR: kaynak_imzasi()'nin okudugu kumeyi yedek_plani()'ndan
        # AYIRIR (ek kapsami plandan suzer) — 31 Tem'de OLCULEN sessiz fail-open'in
        # ta kendisi: imza glob kapsamindaki 1934 dosyayi gormuyor, `--gerekliyse`
        # "guncel" deyip yedegi ATLIYOR, kopya BAYAT kaliyor, kimse uyarmiyor.
        MUT_IMZA = (
            "    for kaynak, _hedef in yedek_plani(sirlar):",
            "    for kaynak, _hedef in [x for x in yedek_plani(sirlar)\n"
            "                           if not x[1].startswith(EK_KLASOR + os.sep)]:"
            "  # MUTANT: imza EK kapsami GORMUYOR = plandan AYRISTI")

        # --- NEGATIF (MESRU) REFAKTORLER: guvence KORUNUR -> davranis DEGISMEZ ---
        REF_YORUM = ("        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)",
                     "        # refaktor yorumu: non-blocking exclusive kilit denemesi\n"
                     "        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)")
        REF_RENAME = ("bas_imza", "baslangic_imzasi", None)   # None -> HEPSI (yeniden adlandirma)
        REF_YORUM2 = ("    basardi = False",
                      "    # refaktor: fail-closed basari bayragi varsayilani\n"
                      "    basardi = False")
        REF_IMZA = ("    for kaynak, _hedef in yedek_plani(sirlar):",
                    "    # refaktor yorumu: imza kumesi TEK tanimdan (yedek_plani) gelir\n"
                    "    for kaynak, _hedef in yedek_plani(sirlar):")

        # ---- ÇAPA-VARLIK NOBETI (fail-closed, senaryolardan ONCE) ------------------
        # Asagidaki nobetlerin GUCU 1. siniftir: mutant yedekle.py'yi GERCEKTEN
        # kosturur ve CIKTIYA assert eder. Zayif halka capanin KENDISIYDI — kayarsa
        # senaryo hic kosmaz ve (eski _capa'da) kapi sessizce ⚪'ya duserdi. Burada
        # her capa GERCEK tools/yedekle.py'de ILAN EDILEN ADETTE aranir: kayma,
        # senaryo davranisina hic karismadan, capanin ADIYLA KIRMIZI yanar.
        # `kesin=True` -> tek-vurus mutasyon capasi (adet=1 replace anlamli olsun);
        # `kesin=False` -> yeniden adlandirma capasi (adet=None, HEPSI), >=1 yeter.
        _gov_y = open(YEDEKLE, encoding="utf-8").read()
        for _cad, _cmetin, _cadet, _kesin in (
                ("MUT_FLOCK/REF_YORUM (fcntl.flock non-blocking cagrisi)",
                 MUT_FLOCK[0], 1, True),
                ("MUT_FINALLY/REF_YORUM2 (basari bayragi varsayilani)",
                 MUT_FINALLY[0], 1, True),
                ("MUT_CIKIS (baslangic imzasi satiri)", MUT_CIKIS[0], 1, True),
                ("_COKME_CAPA (kopya dongusu basi)", _COKME_CAPA, 1, True),
                ("MUT_IMZA/REF_IMZA (imza kumesi = yedek_plani dongusu)",
                 MUT_IMZA[0], 1, True),
                ("REF_RENAME (bas_imza tanimlayicisi)", REF_RENAME[0], 1, False)):
            _g = _gov_y.count(_cmetin)
            kontrol("ÇAPA-VARLIK: %s capasi tools/yedekle.py'de %s%d kez var"
                    % (_cad, "tam " if _kesin else "en az ", _cadet),
                    (_g == _cadet) if _kesin else (_g >= _cadet),
                    "gorulen=%d" % _g)

        # ---- GUVENCE (a): flock paralel yedekleri serilestirir ----
        a_base_atladi, a_base_bitti = _senaryo_flock(yb, [])
        kontrol("(a) flock BASE: kilit baskasindayken kosum ATLADI (serilestirme calisiyor)",
                a_base_atladi and not a_base_bitti,
                "atladi=%s bitti=%s" % (a_base_atladi, a_base_bitti))
        a_mut = _capa("(a) flock POZITIF MUTANT [capa]", lambda: _senaryo_flock(yb, [MUT_FLOCK]))
        a_mut_atladi, a_mut_bitti = a_mut or (None, None)
        a_mut is None or kontrol("(a) flock POZITIF MUTANT (flock cagrisi silindi) -> kosum ATLAMADI, "
                "kilitli hedefe YAZDI (base kontrol KIRMIZI yanardi)",
                a_mut_bitti and not a_mut_atladi,
                "atladi=%s bitti=%s" % (a_mut_atladi, a_mut_bitti))

        # ---- GUVENCE (b): `bitti=` basari izi YALNIZ basari yolunda ----
        b_base = _capa("(b) base cokme senaryosu [capa]", lambda: _senaryo_cokme(yb, []))
        b_base is None or kontrol("(b) hazirlik: ilk yedek tamamlandi + coken kosum GERCEKTEN cokuyor",
                b_base["r0_ok"] and b_base["cokdu"] and b_base["T0"] is not None,
                "r0_ok=%s cokdu=%s" % (b_base["r0_ok"], b_base["cokdu"]))
        b_base is None or kontrol("(b) damga-finally BASE: kosum coktugunde iz `bitti=` TASIMIYOR, `hata=` "
                "tasiyor (basari izi yalniz basari yolunda)",
                (not b_base["iz_bitti"]) and b_base["iz_hata"],
                "bitti=%s hata=%s" % (b_base["iz_bitti"], b_base["iz_hata"]))
        b_mut = _capa("(b) mutant cokme senaryosu [capa]", lambda: _senaryo_cokme(yb, [MUT_FINALLY]))
        b_mut is None or kontrol("(b) damga-finally POZITIF MUTANT (basardi=True finally) -> coken kosumun "
                "izi `bitti=` TASIYOR = sahte-yesil (base kontrol KIRMIZI yanardi)",
                b_mut["iz_bitti"], "bitti=%s hata=%s" % (b_mut["iz_bitti"], b_mut["iz_hata"]))

        # ---- GUVENCE (c): cikis damgasi (.son-yedek.json) YALNIZ basari yolunda ----
        c_base = _capa("(c) base cokme senaryosu [capa]", lambda: _senaryo_cokme(yb, []))
        c_base is None or kontrol("(c) cikis-damgasi BASE: kosum coktugunde .son-yedek.json TAZELENMEDI "
                "(damga en sonda, yalniz tamamlaninca)",
                not c_base["damga_degisti"], "damga_degisti=%s" % c_base["damga_degisti"])
        c_mut = _capa("(c) mutant cokme senaryosu [capa]", lambda: _senaryo_cokme(yb, [MUT_CIKIS]))
        c_mut is None or kontrol("(c) cikis-damgasi POZITIF MUTANT (damga basa tasindi) -> coken kosum TAZE "
                "damga yazdi = sahte-yesil (base kontrol KIRMIZI yanardi)",
                c_mut["damga_degisti"], "damga_degisti=%s" % c_mut["damga_degisti"])

        # ---- NEGATIF FIKSTUR (yanlis-pozitif YOK): mesru refaktor base kontrolu YESIL birakir ----
        n1 = _capa("(neg-1) flock refaktor senaryosu [capa]", lambda: _senaryo_flock(yb, [REF_YORUM]))
        n1_atladi, n1_bitti = n1 or (None, None)
        n1 is None or kontrol("(neg-1) mesru refaktor (flock'a yorum satiri) -> (a) BASE davranisi AYNEN "
                "YESIL (FP yok)", n1_atladi and not n1_bitti,
                "atladi=%s bitti=%s" % (n1_atladi, n1_bitti))
        n2 = _capa("(neg-2) cokme refaktor senaryosu [capa]", lambda: _senaryo_cokme(yb, [REF_RENAME]))
        n2 is None or kontrol("(neg-2) mesru refaktor (bas_imza -> baslangic_imzasi yeniden adlandirma) -> "
                "(b)+(c) BASE davranisi AYNEN YESIL (FP yok)",
                (not n2["iz_bitti"]) and n2["iz_hata"] and (not n2["damga_degisti"])
                and n2["cokdu"],
                "bitti=%s hata=%s damga_degisti=%s" % (n2["iz_bitti"], n2["iz_hata"],
                                                       n2["damga_degisti"]))
        n3 = _capa("(neg-3) cokme refaktor senaryosu [capa]", lambda: _senaryo_cokme(yb, [REF_YORUM2]))
        n3 is None or kontrol("(neg-3) mesru refaktor (basardi'ya yorum satiri) -> (b)+(c) BASE davranisi "
                "AYNEN YESIL (FP yok)",
                (not n3["iz_bitti"]) and n3["iz_hata"] and (not n3["damga_degisti"]),
                "bitti=%s hata=%s damga_degisti=%s" % (n3["iz_bitti"], n3["iz_hata"],
                                                       n3["damga_degisti"]))

        # KALICI FIKSTUR (anchor-kirilgan DEGIL): '__CAPA_FIKSTUR_ASLA_YOK__' hicbir yedekle.py'de
        # yok = anchor-KIRAN mesru refaktor; _capa onu tam 1 ⚪+None yapmali, suite ABORT etmemeli.
        _ol0 = len(OLCULEMEDI)
        _kir0 = len([1 for _a, _ok in SONUC if not _ok])
        _fx = _capa(_CAPA_FIKSTUR_ADI,
                    lambda: _senaryo_flock(yb, [("__CAPA_FIKSTUR_ASLA_YOK__", "x")]))
        kontrol("(fikstur) anchor-KIRAN refaktor GRACEFUL: _capa None dondu + tam 1 ⚪ "
                "uretti + suite ABORT ETMEDI (FP mayini kapali kalir)",
                _fx is None and len(OLCULEMEDI) == _ol0 + 1,
                "None=%s yeni_olculemedi=%d" % (_fx is None, len(OLCULEMEDI) - _ol0))

        # ---- ÇAPA BUTCESI (fail-closed): ILAN EDILMEYEN her capa kaybi KIRMIZI ----
        # (1) Fikstur ⚪ URETIR ama KIRMIZI URETMEZ — ilan edilmis tek mesru yol budur.
        kontrol("(fikstur) ILAN EDILMIS capa kaybi KIRMIZI URETMEDI (⚪ yolu yalniz "
                "ilan edilene acik)",
                len([1 for _a, _ok in SONUC if not _ok]) == _kir0,
                "kirmizi_delta=%d"
                % (len([1 for _a, _ok in SONUC if not _ok]) - _kir0))
        # (2) ILAN EDILMEYEN bir capa kayarsa _capa KIRMIZI yakar — ayni kod yolu,
        #     sahte adla KOSTURULARAK kanitlanir (iddia degil, OLCUM).
        _kir1 = len([1 for _a, _ok in SONUC if not _ok])
        _ol1 = len(OLCULEMEDI)
        print("     (asagidaki TEK ❌ KASITLI oz-nobet fiksturudur: ilan edilmemis "
              "capa kaybinin KIRMIZI yaktigini KOSARAK kanitlar; kaydi hemen geri "
              "alinir, ozete GIRMEZ)")
        _fx2 = _capa("(oz-nobet) ILAN EDILMEMIS capa kaybi",
                     lambda: _senaryo_flock(yb, [("__CAPA_FIKSTUR_ASLA_YOK__", "x")]))
        _yeni_kirmizi = len([1 for _a, _ok in SONUC if not _ok]) - _kir1
        # Oz-nobetin KENDI urettigi KIRMIZI kaydi ozete sizmasin: dogrulandiktan sonra
        # geri alinir (kapinin kendi kanitini kendi kirmizisi yapmasi anlamsiz olurdu).
        if _yeni_kirmizi == 1:
            SONUC.pop()
        kontrol("ÖZ-NOBET: ILAN EDILMEYEN capa kaybi KIRMIZI yakiyor (⚪'ya KACMIYOR) "
                "-> capa bayatlarsa kapi SESSIZ GECMEZ",
                _fx2 is None and _yeni_kirmizi == 1 and len(OLCULEMEDI) == _ol1,
                "None=%s yeni_kirmizi=%d yeni_⚪=%d"
                % (_fx2 is None, _yeni_kirmizi, len(OLCULEMEDI) - _ol1))
        # (3) BUTCE: fikstur ekseninde ⚪ SAYISI tam 1. Ikinci bir fail-open yol
        #     acilirsa (yeni bir ⚪ ureticisi) bu nobet KIRMIZI yanar.
        kontrol("ÇAPA BUTCESI: fikstur-ekseninde tam 1 ⚪ var (ilan edilen kalici "
                "fikstur); ikinci fail-open yol YOK",
                EKSEN.get("fikstur", 0) == 1, "fikstur ⚪=%d" % EKSEN.get("fikstur", 0))

        # ------- 11) IMZA KAPSAMI = KOPYA PLANI (glob fail-open nobeti) -------
        # Gerekce ve senaryo: _senaryo_glob_kapsam ustundeki blok.
        print("\n11) IMZA KAPSAMI = KOPYA PLANI — glob'lu allowlist girisleri "
              "(sessiz fail-open nobeti)")
        _ev_adi, _desen = _glob_girisi(yb)
        kontrol("(11) VERI CAPASI: EK_EVLER'de GLOB'lu giris VAR (senaryo gercek "
                "konfigurasyonu temsil ediyor; yoksa nobet bayattir)",
                bool(_ev_adi), "ev=%s giris=%s" % (_ev_adi, _desen))

        g_base = _capa("(11) base glob-kapsam senaryosu [capa]",
                       lambda: _senaryo_glob_kapsam(yb, []))
        g_base is None or kontrol(
            "(11) hazirlik: ilk TAM yedek bitti + glob kapsamindaki dosya PLANDA ve "
            "hedefe KOPYALANDI + imza OLCULDU",
            g_base["r0_ok"] and g_base["planda"] and g_base["ilk_kopyalandi"]
            and g_base["olculdu"],
            "r0=%s planda=%s kopya=%s olculdu=%s"
            % (g_base["r0_ok"], g_base["planda"], g_base["ilk_kopyalandi"],
               g_base["olculdu"]))
        g_base is None or kontrol(
            "(11a) glob kapsamindaki dosya DEGISINCE kaynak imzasi DEGISTI "
            "(mtime ESKI -> karari YALNIZ imza ekseni verebilir)",
            g_base["imza_degisti"] and g_base["olculdu"],
            "%s -> %s" % (g_base["d0"], g_base["d1"]))
        g_base is None or kontrol(
            "(11b) `--gerekliyse` yedegi ATLAMADI, GERCEKTEN yedekledi (fail-open KAPALI)",
            g_base["yedekledi"] and not g_base["atladi"],
            "yedekledi=%s atladi=%s" % (g_base["yedekledi"], g_base["atladi"]))
        g_base is None or kontrol(
            "(11c) hedefteki kopya YENI icerigi tasiyor (sessiz veri kaybi YOK)",
            g_base["kopya_guncel"], "kopya_guncel=%s" % g_base["kopya_guncel"])
        g_base is None or kontrol(
            "(11d) YANLIS-POZITIF YOK: hicbir kaynak degismeden kosum ATLIYOR",
            g_base["degisiklik_yokken_atladi"],
            "atladi=%s" % g_base["degisiklik_yokken_atladi"])
        g_base is None or kontrol(
            "(11e) INVARYANT: imza adedi == yedek plani uzunlugu (imzanin IKINCI bir "
            "yuruyusu YOK -> tanimlar ayrisamaz)",
            g_base["imza_plani_kadar"],
            "adet=%s plan=%s" % ((g_base["d0"] or {}).get("adet"), g_base["plan"]))

        g_mut = _capa("(11) POZITIF MUTANT senaryosu [capa]",
                      lambda: _senaryo_glob_kapsam(yb, [MUT_IMZA]))
        g_mut is None or kontrol(
            "(11) POZITIF MUTANT (imza plandan AYRISTI: ek kapsami gormuyor) -> kosum "
            "ATLADI, imza KIMILDAMADI, kopya BAYAT kaldi = sessiz veri kaybi "
            "(11a/11b/11c KIRMIZI yanardi)",
            g_mut["atladi"] and not g_mut["imza_degisti"] and not g_mut["kopya_guncel"],
            "atladi=%s imza_degisti=%s kopya_guncel=%s"
            % (g_mut["atladi"], g_mut["imza_degisti"], g_mut["kopya_guncel"]))

        g_ref = _capa("(neg-11) imza dongusu refaktor senaryosu [capa]",
                      lambda: _senaryo_glob_kapsam(yb, [REF_IMZA]))
        g_ref is None or kontrol(
            "(neg-11) mesru refaktor (imza dongusune yorum satiri) -> (11) BASE "
            "davranisi AYNEN YESIL (FP yok)",
            g_ref["imza_degisti"] and g_ref["yedekledi"] and g_ref["kopya_guncel"]
            and g_ref["degisiklik_yokken_atladi"] and g_ref["imza_plani_kadar"],
            "imza_degisti=%s yedekledi=%s kopya_guncel=%s bos_kosum_atladi=%s"
            % (g_ref["imza_degisti"], g_ref["yedekledi"], g_ref["kopya_guncel"],
               g_ref["degisiklik_yokken_atladi"]))

    # ---------------- OZET ----------------
    kirmizi = [a for a, ok in SONUC if not ok]
    print("\n" + "=" * 70)
    # Makine-okunur ozet (alt kosum bunlari ayristirir; sabit sayi YOK).
    print("PS: " + PS_ORTAMI[0].upper())      # VAR | YOK | BOZUK
    print("GIT: " + GIT_ORTAMI[0].upper())    # VAR | YOK | BOZUK
    print("LAUNCHD: " + LAUNCHD_ORTAMI[0].upper())  # VAR | YOK (pid=1 surrogati)
    print("PS BAGIMLI: %d" % PS_BAGIMLI[0])
    print("GIT BAGIMLI: %d" % GIT_BAGIMLI[0])
    print("LAUNCHD BAGIMLI: %d" % LAUNCHD_BAGIMLI[0])
    print("ORTAM BAGIMLI: %d" % ORTAM_BAGIMLI[0])
    print("KAYNAK ORTAMI: " + kaynak_ortami().upper())
    # ORTAMDAN BAGIMSIZ (sentetik PATH ile kosan) nobet sayisi — bolum 9 alt kosumun
    # AYNI sayiyi raporladigini dogrular (nobetcinin nobetcisi).
    print("BAGIMSIZ NOBET: %d" % BAGIMSIZ_NOBET[0])
    # EKSEN BAZLI ⚪ SAYILARI (alt kosum bunlari ayristirir; sabit sayi YOK).
    # "EKSENSIZ" > 0 demek: bir ⚪ hangi ortam eksigi yuzunden yazildigini ILAN
    # ETMEMISTIR -> sessiz atlamaya en yakin hal, nobetci onu KIRMIZI yakar.
    print("PS EKSEN OLCULEMEDI: %d" % EKSEN.get("ps", 0))
    print("GIT EKSEN OLCULEMEDI: %d" % EKSEN.get("git", 0))
    print("KAYNAK EKSEN OLCULEMEDI: %d" % EKSEN.get("kaynak", 0))
    print("FIKSTUR EKSEN OLCULEMEDI: %d" % EKSEN.get("fikstur", 0))
    print("LAUNCHD EKSEN OLCULEMEDI: %d" % EKSEN.get("launchd", 0))
    print("EKSENSIZ OLCULEMEDI: %d"
          % sum(n for e, n in EKSEN.items() if e not in BILINEN_EKSENLER))
    print("GECTI: %d" % (len(SONUC) - len(kirmizi)))
    print("KIRMIZI: %d" % len(kirmizi))
    print("OLCULEMEDI: %d" % len(OLCULEMEDI))
    print("TOPLAM %d kontrol, %d kirmizi, %d ⚪ ÖLÇÜLEMEDİ"
          % (len(SONUC), len(kirmizi), len(OLCULEMEDI)))
    for a in kirmizi:
        print("  ❌ " + a)
    for a, ayrinti, eksen in OLCULEMEDI:
        print("  ⚪ ÖLÇÜLEMEDİ [%s]: %s  (%s)" % (eksen, a, ayrinti))
    if OLCULEMEDI:
        print("NOT: ⚪ OLCULEMEDI cikis kodunu BOZMAZ (ortam eksikligi yayini durdurmaz) "
              "ama GORUNURDUR — bkz. modul basligi K4.")
    print("SONUC: " + ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
