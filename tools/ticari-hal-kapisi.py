#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TICARI HAL KAPISI — `tur` + `gorselsiz` alanlarinin duzelt.py'deki MESRU GERI ALMA
yolunu ve o yolun SINIRLARINI olcer.

NEDEN VAR (olculdu 1 Agu)
-------------------------
724a69b2 gorsel zorunluluguna dar bir istisna acti: `"gorselsiz": true` + `tur ==
"fiziksel"` + gercekten gorselsiz olan urun eklenebiliyor. Ama iki alan da duzelt.py'nin
DEGISTIRILEBILIR kumesinde YOKTU. Sonuc: bayrak bir kez konunca MESRU YOLDAN geri
alinamiyordu. Bu depoda ayni sinif daha once iki kez cikti (goc indeksi, kurtarma dali) ve
her seferinde geri donus ELLE temizlik istedi. Tek yonlu kapi, kapi degil TUZAKTIR.

Ayrica ONCEDEN OLCULEN ikinci delik: `--alan-sil` izinli-alan kumesine BAKMIYORDU, yani
`--alan-sil tur` zaten calisiyordu ve `gorselsiz: true` bayragini kayitta ASILI birakiyordu
— parti-kontrol'un ASLA kabul etmeyecegi bir ara durum, sessizce uretilebiliyordu.
(Bu iddia OLCULUR: bkz. O-serisi "ONCE" kosumlari.)

NE ACILDI, NE ACILMADI
----------------------
ACILAN: urun-basi, beyanli, guard manifestine bagli, `.urunler-guard.log`a yazilan TEKIL
duzeltme. ACILMAYAN: toplu/sessiz kayma — tools/parti-kontrol.py bu iki alanin BACKFILL'de
degismesini KIRMIZI saymaya DEVAM eder ve o kural GEVSETILMEDI (bu kapi onu da olcer: P1).

🔴 SINIF ATLAMASI SERBEST DEGIL: hazir mal <-> ozel uretim gecisi PARA (secenekler.js
`tur`u okuyup malzeme/renk carpanini 1,00'e sabitler) ve CAYMA HAKKI rejimi demektir.
Gecis `--gerekce` ZORUNLU tutar ve loga izlenebilir sekilde yazilir.

IDDIALAR (hepsi GERCEK duzelt.py SUREC olarak kosturulur; cikis kodlari OLCULUR)
-------------------------------------------------------------------------------
  O0 FIKS  ONCE kolunun kaynagi (tools/fikstur/duzelt-once-gorselsiz.py) sha256 PININE
           uyar; uymazsa O-serisi KOSMAZ (fail-closed).
  O0b FIKS Gecmis erisilebiliyorsa fikstur `026baebc^:tools/duzelt.py` ile BAYT-ESITTIR.
           Sig klonda bu iddia ATLANIR (not olarak yazilir), digerleri TAM kosar.
  O1 ONCE  ONCE fiksturundeki duzelt.py `--alan gorselsiz` ve `--alan tur` yazimini
           REDDEDER (izinsiz alan) -> bayrak mesru yoldan KONULAMIYOR/DUZELTILEMIYORDU.
  O2 ONCE  ONCE fiksturundeki duzelt.py `--alan-sil tur` ile sinifi dusurur ve
           `gorselsiz: true` kayitta ASILI kalir (rc=0, sessiz gecersiz durum).
  Y1 SONRA Yeni duzelt.py bayragi hazir + gorselsiz kayda KOYAR (rc=0) ve
           `--alan-sil gorselsiz` ile GERI ALIR (rc=0).
  Y2 SONRA `--alan-sil tur --alan-sil gorselsiz` (gerekceyle) TEK cagrida temiz doner;
           kayitta ne `tur` ne `gorselsiz` kalir.
  T1 SINIR `tur` kanonik olmayan deger ("Fiziksel", " fiziksel", "", 1) -> rc=6.
  T2 SINIR `gorselsiz` boolean true DISI deger ("true", 1, "evet", false) -> rc=6.
  T3 SINIR `--alan-sil tur` yapip `gorselsiz: true` birakmak -> rc=6 (O2'nin kapanisi).
  T4 SINIR Gorselli kayda `gorselsiz: true` -> rc=6.
  T5 SINIR Sinif atlamasi --gerekce OLMADAN -> rc=6; gerekceyle -> rc=0 ve
           `.urunler-guard.log`ta "ticari-hal:" satiri + gerekce metni GECER.
  B1 TOPLU Ayni kurallar --toplu kipinde de gecerli (T5 gerekcesiz -> rc=6, "ya hep ya
           hic": urunler.json BAYT-ESIT kalir; gerekceli -> rc=0).
  P1 KOMSU parti-kontrol.py'nin BACKFILL kurali GEVSEMEDI: mevcut urunde `gorselsiz`
           belirmesi hala bulgu uretir.
  R1 REG   Siradan alan duzeltmesi (`fiyat`) ve mevcut `--alan-sil uyelik` yolu
           DEGISMEDI (rc=0).

MUTASYON (--mutasyon): yeni duzelt.py'de tek satirlik kaynak mutasyonlari uygulanir ve bu
kapinin KIRMIZI yandigi KANITLANIR. Mutasyon yalniz SAHTE REPO KOPYASINA yazilir; gercek
tools/duzelt.py'ye ASLA dokunulmaz.

GERCEK urunler.json'a DOKUNULMAZ: her senaryo icin gecici sahte repo kurulur
(duzelt-toplu-test.py deseni). Ag YOK.

Kullanim:
    python3 tools/ticari-hal-kapisi.py
    python3 tools/ticari-hal-kapisi.py --mutasyon

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
# --------------------------------------------------------------------------- ONCE kolu
# O-serisi "duzeltmeden ONCEKI duzelt.py" davranisini olcer. Bu kaynak GIT GECMISINDEN
# DEGIL, REPOYA GOMULU FIKSTURDEN gelir. Neden (olculdu 1 Agu, iki ayri tuzak):
#   1) ANA-HAT REFERANS TAUTOLOJISI: eskiden `git show HEAD:tools/duzelt.py` okunuyordu.
#      Duzeltme main'e girince HEAD ARTIK DUZELTILMIS dosyaydi -> kapi "ONCE
#      reddediliyordu" iddiasini DUZELTILMIS koda karsi sinayip kendi kendini
#      yanliskliyordu. 1 Agu: 6 kosum ust uste dustu, yayin 20 commit boyunca tikandi.
#   2) SABIT HASH DE YETMEZ: `026baebc^` bir SIG (shallow) checkout'ta COZULMEZ
#      (olculdu: `git clone --depth 1` -> `rev-parse 026baebc^` rc=128, kapi fail-closed
#      rc=1 ve 32 iddia yerine yalniz 2 satir olcer). CI'da bugun `fetch-depth: 0` var,
#      ama kapinin kaniti O YAML SATIRINA, rebase/squash'a ve gecmis topolojisine
#      BAGIMLI OLMAMALI — aksi halde tarih her yeniden yazildiginda YAYIN DURUR.
# Fikstur bu iki bagimliligin IKISINI de keser: dosya repoda durur, sha256 ile PINLENIR
# (sessiz kayma KIRMIZI yanar) ve gecmis erisilebildiginde ONCE_REF'e karsi BAYT-ESITLIGI
# ayrica dogrulanir (O0b) -> fikstur "uydurma bir eski dosya" olamaz.
ONCE_REF = "026baebc^"                       # yalnizca O0b capraz dogrulamasinin capasi
ONCE_FIKSTUR = os.path.join(TOOLS, "fikstur", "duzelt-once-gorselsiz.py")
ONCE_FIKSTUR_SHA256 = "17a8095d51af5b5b44539144aa1804b153d8fbf647d8fe00ba2f19072f939b01"

# duzelt.py bunlari KOSULSUZ import eder -> sahte repoya da kopyalanmalilar.
YARDIMCILAR = ["gorsel_koken.py", "arama.py"]
KAYNAK_INDEX = os.path.join(ROOT, "index.html")

# --mutasyon kipinde sahte repoya yazilacak MUTANT duzelt.py kaynagi (None = gercegi).
# TOOLS/ROOT sabitleri ASLA degistirilmez: P1 iddiasi (parti-kontrol) ve "ONCE" kolu
# (gomulu fikstur) mutandan ETKILENMEMELI, yoksa mutant onlari cokertip sahte "oldu"
# uretirdi. O-serisi kaynagini ACIKCA gecirir -> MUTANT_SRC'yi zaten es geter.
MUTANT_SRC = None

RC_TICARI_HAL = 6          # duzelt.py ile AYNI deger; burada BAGIMSIZ capa olarak durur
                           # ([[kapi-anchor-coupling-ikilemi]]: iki taraf ayni sabiti
                           # okusaydi kod sessizce degistirilip test yine yesil yanardi).

FIZ_GORSELSIZ = {"id": "hazir-mal", "kategori": "Marin", "marka": ["Sinama"],
                 "baslik": "Hazir Ticari Mal", "aciklama": "aciklama", "fiyat": "100 TL",
                 "tur": "fiziksel", "gorselsiz": True}
FIZ_GORSELLI = {"id": "hazir-gorselli", "kategori": "Marin", "marka": [],
                "baslik": "Hazir Gorselli", "aciklama": "aciklama", "fiyat": "200 TL",
                "tur": "fiziksel",
                "gorseller": ["https://media.pruvo3d.com/urunler/hg-1.jpg"]}
OZEL = {"id": "ozel-uretim", "kategori": "Ofis", "marka": [],
        "baslik": "Ozel Uretim", "aciklama": "aciklama", "fiyat": "300 TL",
        "uyelik": "gizli",
        "gorseller": ["https://media.pruvo3d.com/urunler/ou-1.jpg"]}
OZEL_GORSELSIZ = {"id": "ozel-gorselsiz", "kategori": "Ofis", "marka": [],
                  "baslik": "Ozel Gorselsiz", "aciklama": "aciklama", "fiyat": "400 TL"}
KATALOG = [FIZ_GORSELSIZ, FIZ_GORSELLI, OZEL, OZEL_GORSELSIZ]

hatalar = []
satirlar = []
notlar = []          # OLCULEMEYEN ama gizlenmemesi gereken durumlar; IDDIA SAYILMAZ


def kontrol(kosul, mesaj):
    satirlar.append(("  ✔ " if kosul else "  ✘ ") + mesaj)
    if not kosul:
        hatalar.append(mesaj)


# --------------------------------------------------------------------------- ONCE kaynagi
def _once_fiksturu():
    """(kaynak, ariza) dondurur. Fikstur YOKSA ya da sha256 PINI TUTMUYORSA kaynak
    None'dir -> cagiran FAIL-CLOSED gider. Pin, fiksturun sessizce "duzeltilmis" bir
    kopyayla degistirilmesini engeller: o an O-serisi yesil yanar ama HICBIR SEY
    olcmez ([[ikiz-tanim-sessiz-ayrisma]])."""
    if not os.path.exists(ONCE_FIKSTUR):
        return None, "fikstur DOSYASI YOK: tools/fikstur/%s" % os.path.basename(ONCE_FIKSTUR)
    with open(ONCE_FIKSTUR, "rb") as f:
        ham = f.read()
    ozet = hashlib.sha256(ham).hexdigest()
    if ozet != ONCE_FIKSTUR_SHA256:
        return None, ("fikstur sha256 PINI TUTMUYOR (beklenen %s…, olculen %s…)"
                      % (ONCE_FIKSTUR_SHA256[:16], ozet[:16]))
    return ham.decode("utf-8"), None


def _once_capraz_dogrulama():
    """Fikstur GERCEKTEN `ONCE_REF:tools/duzelt.py` mi? True/False; gecmis erisilemezse
    None (sig klon / yeniden yazilmis tarih). None hali KIRMIZI YAKMAZ ama gizlenmez de:
    olcum gucu fiksturun kendisinde durur, capraz dogrulama yalnizca EK kanittir."""
    r = subprocess.run(["git", "-C", ROOT, "show", ONCE_REF + ":tools/duzelt.py"],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return hashlib.sha256(r.stdout).hexdigest() == ONCE_FIKSTUR_SHA256


# --------------------------------------------------------------------------- sahte repo
def _duzelt_kaynagi():
    with open(os.path.join(TOOLS, "duzelt.py"), encoding="utf-8") as f:
        return f.read()


def sahte_repo(duzelt_kaynak=None, katalog=None):
    """Gecici repo: <tmp>/tools/{duzelt,gorsel_koken,arama}.py + <tmp>/urunler.json.
    duzelt.py yollarini kendi __file__'indan turettigi icin kopya sahte katalogda calisir.
    Gercek repoya HICBIR SEY yazilmaz (mutant da yalniz bu kopyaya girer)."""
    d = tempfile.mkdtemp(prefix="ticari-hal-kapisi-")
    os.makedirs(os.path.join(d, "tools"))
    for ad in YARDIMCILAR:
        shutil.copy(os.path.join(TOOLS, ad), os.path.join(d, "tools", ad))
    # arama.py arac es-anlamli sabitlerini kanonik index.html literalinden yukler.
    shutil.copy(KAYNAK_INDEX, os.path.join(d, "index.html"))
    src = duzelt_kaynak
    if src is None:
        src = MUTANT_SRC if MUTANT_SRC is not None else _duzelt_kaynagi()
    with open(os.path.join(d, "tools", "duzelt.py"), "w", encoding="utf-8") as f:
        f.write(src)
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(KATALOG if katalog is None else katalog, f,
                  ensure_ascii=False, indent=2)
    return d


def cagir(repo, *argv):
    """duzelt.py'yi SUREC olarak kostur -> gercek cikis kodu."""
    r = subprocess.run([sys.executable, os.path.join(repo, "tools", "duzelt.py")]
                       + list(argv), capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def kayit(repo, uid):
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        for u in json.load(f):
            if u.get("id") == uid:
                return u
    return None


def katalog_hash(repo):
    with open(os.path.join(repo, "urunler.json"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def log_metni(repo):
    yol = os.path.join(repo, ".urunler-guard.log")
    if not os.path.exists(yol):
        return ""
    with open(yol, encoding="utf-8") as f:
        return f.read()


def temizle(*repolar):
    for d in repolar:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- iddialar
def kosum():
    del hatalar[:]
    del satirlar[:]
    del notlar[:]

    # ---------------------------------------------------------------- O0 (fikstur butunlugu)
    eski_src, ariza = _once_fiksturu()
    kontrol(eski_src is not None,
            "O0 FIKSTUR ONCE kopyasi butun (sha256 pinli)"
            if eski_src is not None else "O0 FIKSTUR OKUNAMADI: %s" % ariza)
    if eski_src is None:
        # FAIL-CLOSED: "ONCE" kolu olculemezse kapi yesil VEREMEZ (kanit yarim kalir).
        hatalar.append("O-serisi OLCULEMEDI: %s" % ariza)
        return

    # -------------------------------------------------- O0b (fikstur <-> gercek gecmis)
    esit = _once_capraz_dogrulama()
    if esit is None:
        notlar.append("O0b capraz dogrulama ATLANDI — `%s` bu checkout'ta cozulmuyor "
                      "(sig klon veya yeniden yazilmis gecmis). O-serisi gomulu "
                      "fiksturden TAM olarak olculur; sha256 pini gecerlidir." % ONCE_REF)
    else:
        kontrol(esit, "O0b FIKSTUR = `%s:tools/duzelt.py` BAYT-ESIT" % ONCE_REF)
        if not esit:
            return

    # ---------------------------------------------------------------- O1 / O2 (ONCE)
    r = sahte_repo(duzelt_kaynak=eski_src)
    rc1, c1 = cagir(r, "hazir-mal", "--alan", "gorselsiz", "--deger", "true")
    rc2, c2 = cagir(r, "ozel-uretim", "--alan", "tur", "--deger", "fiziksel")
    kontrol(rc1 != 0 and "izinsiz alan" in c1,
            "O1 ONCE: `--alan gorselsiz` REDDEDILIYORDU (rc=%d)" % rc1)
    kontrol(rc2 != 0 and "izinsiz alan" in c2,
            "O1 ONCE: `--alan tur` REDDEDILIYORDU (rc=%d)" % rc2)
    rc3, _ = cagir(r, "hazir-mal", "--alan-sil", "tur")
    asili = kayit(r, "hazir-mal")
    kontrol(rc3 == 0 and asili is not None and "tur" not in asili
            and asili.get("gorselsiz") is True,
            "O2 ONCE: `--alan-sil tur` GECIYOR (rc=%d) ve `gorselsiz: true` ASILI kaliyor "
            "-> gecersiz ara durum sessizce uretilebiliyordu" % rc3)
    temizle(r)

    # ---------------------------------------------------------------- Y1 (SONRA)
    r = sahte_repo()
    rc, c = cagir(r, "ozel-gorselsiz", "--alan", "tur", "--deger", "fiziksel",
                  "--gerekce", "hazir ticari mal olarak siniflandirildi")
    rc_b, c_b = cagir(r, "ozel-gorselsiz", "--alan", "gorselsiz", "--deger", "true")
    k = kayit(r, "ozel-gorselsiz")
    kontrol(rc == 0 and rc_b == 0 and k.get("tur") == "fiziksel"
            and k.get("gorselsiz") is True,
            "Y1 SONRA: bayrak mesru yoldan KONULABILIYOR (rc=%d/%d)" % (rc, rc_b))
    rc_c, _ = cagir(r, "ozel-gorselsiz", "--alan-sil", "gorselsiz")
    k = kayit(r, "ozel-gorselsiz")
    kontrol(rc_c == 0 and "gorselsiz" not in k,
            "Y1 SONRA: bayrak `--alan-sil gorselsiz` ile GERI ALINABILIYOR (rc=%d)" % rc_c)
    del c, c_b
    temizle(r)

    # ---------------------------------------------------------------- Y2 (SONRA, tek cagri)
    r = sahte_repo()
    rc, c = cagir(r, "hazir-mal", "--alan-sil", "gorselsiz", "--alan-sil", "tur",
                  "--gerekce", "yanlis siniflandirilmisti; ozel uretim")
    k = kayit(r, "hazir-mal")
    kontrol(rc == 0 and "tur" not in k and "gorselsiz" not in k,
            "Y2 SONRA: bayrak+sinif TEK cagrida temiz geri alindi (rc=%d)" % rc)
    kontrol("ticari-hal:" in log_metni(r)
            and "yanlis siniflandirilmisti" in log_metni(r),
            "Y2 SONRA: sinif atlamasi gerekcesiyle `.urunler-guard.log`a yazildi")
    temizle(r)

    # ---------------------------------------------------------------- T1 `tur` degeri
    for deger in ("Fiziksel", " fiziksel", "", "fiziksel-degil"):
        r = sahte_repo()
        h = katalog_hash(r)
        rc, c = cagir(r, "ozel-gorselsiz", "--alan", "tur", "--deger", deger,
                      "--gerekce", "sinama")
        kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h,
                "T1 `tur`=%r REDDEDILDI (rc=%d) ve katalog bayt-esit kaldi" % (deger, rc))
        del c
        temizle(r)

    # ---------------------------------------------------------------- T2 `gorselsiz` degeri
    # CLI kolu: bu alanda deger JSON olarak cozulur (bkz. duzelt._parse_deger), yani
    # `true` GERCEK boolean olur ve GECER; boolean OLMAYAN her sey T2'ye takilir.
    for deger in ("1", "evet", "false", "[]", "null"):
        r = sahte_repo()
        h = katalog_hash(r)
        rc, c = cagir(r, "hazir-mal", "--alan", "gorselsiz", "--deger", deger)
        kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h and "T2" in c,
                "T2 CLI `gorselsiz`=%s REDDEDILDI (rc=%d) ve katalog bayt-esit kaldi"
                % (deger, rc))
        temizle(r)
    # TOPLU kolu HAM JSON tasir: "true" DIZESI ancak buradan gelebilir — ve reddedilir.
    for ham in ("true", 1, "evet", False, [], None):
        r = sahte_repo()
        h = katalog_hash(r)
        islem = os.path.join(r, "islem.json")
        with open(islem, "w", encoding="utf-8") as f:
            json.dump([{"id": "hazir-mal", "alan": "gorselsiz", "deger": ham}], f)
        rc, c = cagir(r, "--toplu", islem)
        kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h and "T2" in c,
                "T2 TOPLU `gorselsiz`=%r (ham JSON) REDDEDILDI (rc=%d), katalog bayt-esit"
                % (ham, rc))
        temizle(r)

    # ---------------------------------------------------------------- T3 asili bayrak
    r = sahte_repo()
    h = katalog_hash(r)
    rc, c = cagir(r, "hazir-mal", "--alan-sil", "tur", "--gerekce", "sinama")
    kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h and "T3" in c,
            "T3 sinif dusurulup `gorselsiz` ASILI birakilamiyor (rc=%d); O2 kapandi" % rc)
    temizle(r)

    # ---------------------------------------------------------------- T4 gorselli kayit
    r = sahte_repo()
    h = katalog_hash(r)
    rc, c = cagir(r, "hazir-gorselli", "--alan", "gorselsiz", "--deger", "true")
    kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h and "T4" in c,
            "T4 GORSELLI kayda `gorselsiz` beyani konulamiyor (rc=%d)" % rc)
    temizle(r)

    # ---------------------------------------------------------------- T5 gerekce zorunlulugu
    r = sahte_repo()
    h = katalog_hash(r)
    rc, c = cagir(r, "ozel-gorselsiz", "--alan", "tur", "--deger", "fiziksel")
    kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h and "T5" in c,
            "T5 sinif atlamasi --gerekce OLMADAN reddedildi (rc=%d)" % rc)
    rc, c = cagir(r, "ozel-gorselsiz", "--alan", "tur", "--deger", "fiziksel",
                  "--gerekce", "tedarikciden hazir alinan mal")
    kontrol(rc == 0 and kayit(r, "ozel-gorselsiz").get("tur") == "fiziksel",
            "T5 ayni yazim --gerekce ILE gecti (rc=%d)" % rc)
    kontrol("ticari-hal:" in log_metni(r)
            and "tedarikciden hazir alinan mal" in log_metni(r),
            "T5 gecis + gerekce loga yazildi (izlenebilir)")
    temizle(r)

    # ---------------------------------------------------------------- B1 toplu kip
    r = sahte_repo()
    h = katalog_hash(r)
    islem_yol = os.path.join(r, "islem.json")
    with open(islem_yol, "w", encoding="utf-8") as f:
        json.dump([{"id": "ozel-gorselsiz", "alan": "tur", "deger": "fiziksel"},
                   {"id": "ozel-uretim", "alan": "fiyat", "deger": "999 TL"}], f)
    rc, c = cagir(r, "--toplu", islem_yol)
    kontrol(rc == RC_TICARI_HAL and katalog_hash(r) == h,
            "B1 toplu: gerekcesiz sinif atlamasi reddedildi (rc=%d) ve TUM parti geri "
            "alindi (katalog bayt-esit)" % rc)
    with open(islem_yol, "w", encoding="utf-8") as f:
        json.dump([{"id": "ozel-gorselsiz", "alan": "tur", "deger": "fiziksel",
                    "gerekce": "toplu sinama gerekcesi"},
                   {"id": "ozel-uretim", "alan": "fiyat", "deger": "999 TL"}], f)
    rc, c = cagir(r, "--toplu", islem_yol)
    kontrol(rc == 0 and kayit(r, "ozel-gorselsiz").get("tur") == "fiziksel"
            and kayit(r, "ozel-uretim").get("fiyat") == "999 TL",
            "B1 toplu: gerekceli parti gecti (rc=%d)" % rc)
    kontrol("toplu sinama gerekcesi" in log_metni(r),
            "B1 toplu: gerekce loga yazildi")
    temizle(r)

    # ---------------------------------------------------------------- P1 parti-kontrol
    # BACKFILL kurali GEVSEMEDI: mevcut urunde `gorselsiz` belirmesi hala bulgu uretir.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "parti_kontrol_olculen", os.path.join(TOOLS, "parti-kontrol.py"))
    pk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pk)
    onceki = [dict(OZEL_GORSELSIZ)]
    sonraki = [dict(OZEL_GORSELSIZ, tur="fiziksel", gorselsiz=True)]
    bulgular = pk._mevcut_denetle(onceki, sonraki)
    kontrol(any("gorselsiz" in a for _, a in bulgular)
            and any("tur" in a for _, a in bulgular),
            "P1 parti-kontrol BACKFILL kurali GEVSEMEDI (%d bulgu)" % len(bulgular))

    # ---------------------------------------------------------------- R1 regresyon
    r = sahte_repo()
    rc_a, _ = cagir(r, "ozel-uretim", "--alan", "fiyat", "--deger", "555 TL")
    rc_b, _ = cagir(r, "ozel-uretim", "--alan-sil", "uyelik")
    k = kayit(r, "ozel-uretim")
    kontrol(rc_a == 0 and rc_b == 0 and k.get("fiyat") == "555 TL" and "uyelik" not in k,
            "R1 siradan alan duzeltmesi + --alan-sil DEGISMEDI (rc=%d/%d)" % (rc_a, rc_b))
    temizle(r)


# --------------------------------------------------------------------------- mutasyon
MUTANTLAR = [
    ("alanlar izinli listeden dusurulur (geri alma yolu yine tek-yonlu olur)",
     ('"tur", "gorselsiz"}', '}')),
    ("T1 kanonik deger kontrolu no-op edilir",
     ('if TUR_ALANI in u and not _tur_gecerli_acik_deger(u.get(TUR_ALANI)):',
      'if False and TUR_ALANI in u and not _tur_gecerli_acik_deger(u.get(TUR_ALANI)):')),
    ("T2 bayrak `is True` kontrolu gevsetilir (truthy yeter)",
     ('if bayrak_var and u.get(GORSELSIZ_BAYRAK) is not True:',
      'if bayrak_var and not u.get(GORSELSIZ_BAYRAK):')),
    ("T3 sinif esligi kontrolu kalkar (asili bayrak yine mumkun)",
     ('            if not arama.tur_kanonik(u):', '            if False:')),
    ("T4 gorselli kayit kontrolu kalkar",
     ('            if _gorsel_var(u):', '            if False:')),
    ("T5 gerekce zorunlulugu kalkar (sinif sessizce atlanir)",
     ('if eski is not None and eski != yeni and not (gerekceler.get(uid) or "").strip():',
      'if False:')),
    ("ticari hal kapisi tek-urun kipinde hic cagrilmaz",
     ('        hal_ihlal = _ticari_hal_ihlalleri(eski_hal, urunler, {args.id},\n'
      '                                          {args.id: args.gerekce})',
      '        hal_ihlal = []')),
    ("ticari hal kapisi TOPLU kipte hic cagrilmaz",
     ('        hal_ihlal = _ticari_hal_ihlalleri(\n'
      '            eski_hal, urunler, set(setler) | set(alan_silmeler), gerekceler)',
      '        hal_ihlal = []')),
]


def mutasyon_kosumu():
    """Her mutant YALNIZ sahte repo kopyasina yazilir; gercek tools/duzelt.py'ye
    DOKUNULMAZ ([[mutasyon-diske-yazma-tuzagi]]).

    PROBE DARLIGI: mutantin oldurulmus sayilmasi icin "herhangi bir hata" yetmez —
    mutantin bozdugu EKSENDEN bir bulgu gelmeli. Mutant O-serisini (gomulu fikstur) ya
    da P1'i (parti-kontrol) etkileyemez; onlar mutandan bagimsiz kosar. Bu yuzden
    bulgular filtrelenir: yalnizca Y/T/B/R iddialarindan gelen bulgu OLUM sayilir.

    SON MUTANT = ONCE-KIRMIZI: tek satirlik mutantlarin yaninda, DUZELTME ONCESI
    duzelt.py'nin TAMAMI mutant olarak kosturulur. Bu, kapinin "delik gercekten kapandi"
    kanitinin ta kendisidir: eski delikli davranista kapi KIRMIZI, bugunkunde YESIL
    yanmali. Fikstur yolu sabit hash'e degil repodaki dosyaya bagli oldugu icin bu kanit
    sig klonda da, tarih yeniden yazildiginda da AYAKTA kalir."""
    global MUTANT_SRC
    print("MUTASYON — her mutant bu kapiyi KIRMIZI yakmali:")
    temiz_src = _duzelt_kaynagi()
    olen = 0
    for ad, (eski, yeni) in MUTANTLAR:
        if temiz_src.count(eski) != 1:
            print("  ⚪ %s -> capa kayip/coklu (%d adet)" % (ad, temiz_src.count(eski)))
            continue
        MUTANT_SRC = temiz_src.replace(eski, yeni, 1)
        try:
            kosum()
            ilgili = [h for h in hatalar if h[:2] in ("Y1", "Y2", "T1", "T2", "T3",
                                                      "T4", "T5", "B1", "R1")]
        except Exception as e:                                   # noqa: BLE001
            ilgili = ["mutant coktu: %s: %s" % (type(e).__name__, e)]
        finally:
            MUTANT_SRC = None
        if ilgili:
            olen += 1
            print("  ✔ OLDU  %s" % ad)
            print("          ilk bulgu: %s" % ilgili[0][:140])
        else:
            print("  ✘ HAYATTA %s  — KAPI BU DEGISIKLIGI GORMUYOR" % ad)
    print("\nMUTASYON: %d/%d oldu" % (olen, len(MUTANTLAR)))

    # ------------------------------------------------------------- ONCE-KIRMIZI
    print("\nONCE-KIRMIZI — duzeltme ONCESI duzelt.py'nin TAMAMI mutant olarak:")
    once_src, ariza = _once_fiksturu()
    once_kirmizi = 0
    if once_src is None:
        print("  ✘ fikstur alinamadi: %s" % ariza)
    else:
        MUTANT_SRC = once_src
        try:
            kosum()
            ilgili = [h for h in hatalar if h[:2] in ("Y1", "Y2", "T1", "T2", "T3",
                                                      "T4", "T5", "B1", "R1")]
        except Exception as e:                                   # noqa: BLE001
            ilgili = ["eski kaynak coktu: %s: %s" % (type(e).__name__, e)]
        finally:
            MUTANT_SRC = None
        if ilgili:
            once_kirmizi = 1
            print("  ✔ KIRMIZI  eski delikli duzelt.py bu kapidan GECEMIYOR (%d bulgu)"
                  % len(ilgili))
            print("             ilk bulgu: %s" % ilgili[0][:140])
        else:
            print("  ✘ YESIL YANDI — kapi eski DELIKLI davranisi GORMUYOR; "
                  "O-serisi kaniti BOS")
    print("ONCE-KIRMIZI: %d/1" % once_kirmizi)

    # Kapiyi temiz kaynakla geri kostur (kosum() global durumu mutantla birakmasin).
    kosum()
    return 0 if (olen == len(MUTANTLAR) and once_kirmizi == 1) else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Ticari hal (tur/gorselsiz) kapisi")
    ap.add_argument("--mutasyon", action="store_true")
    args = ap.parse_args()

    if args.mutasyon:
        return mutasyon_kosumu()

    kosum()
    print("TICARI HAL KAPISI")
    print("-" * 72)
    for s in satirlar:
        print(s)
    for n in notlar:
        print("  ⚠ " + n)
    print("-" * 72)
    if hatalar:
        print("KIRMIZI — %d bulgu:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — %d iddia olculdu ve gecti." % len(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
