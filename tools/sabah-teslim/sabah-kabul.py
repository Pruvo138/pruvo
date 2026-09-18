#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KraL SABAH RUTINI — KABUL BATARYASI (A1–A5).

27 Agu 2026, `KraL-SabahTeslim-27Agu`. `kral-sabah.py`nin daha once HIC kabul
bataryasi YOKTU — bu yuzden "yeni dosya acip tabani kacirma" yasagi burada
konusuz: kacirilacak taban DOSYASI yok, ve TABAN SAYILARI her kosumda BASILIR.

  A1  `--kendini-test` rc=0  VE  crontab'in KENDI yorumlayicisiyla kosum
      COKMUYOR — IKISI AYRI BASILIR.
  A2  Gercek kosum BUGUNUN spec'ini URETIYOR (dosya VAR, boyut > 0).
  A3  SONUC KOLU: "dosya uretilmedi" hali ADIYLA raporlanir (rc=0 iken bile).
      Fiksturde spec yazimi engellenince kol KIRMIZI yanar.
  A4  MUTANT: A3 kolu oldurulunce A3 FIKSTURU YESILE DONER (arac sessizce
      basarili gorunur); KONTROL (normal kosum) DEGISMEZ. Hedef-kol atfi ayrica.
  A5  Iki ardisik kosumda A1·A2 BIREBIR ayni.

27 Agu 2026, `KraL-SabahYorumlayici-27Agu` — IKI KOL EKLENDI:

  A6  ORTAM KOLU DOGRUYU OLCUYOR MU: asgari surum ELLE YAZILMIS LITERAL degil,
      kaynagin KENDISINDEN TURETILMIS mi. Fikstur = 27 Agu sabahinin ta kendisi
      (`__future__` satiri YOK). MUTANT literal'e geri cevirir. A6g kolun
      SINIRINI ORTMEZ, OLCER.
  A7  KURUCU IDEMPOTENSI (K320): `capa ⊂ yeni` sinifi. TAZE kurulum + ARGUMANSIZ
      IKINCI KOSUM bayt-birebir olmali (cogaltma=0). MUTANT eski kolu geri
      getirir ve ikinci kosumu COGALTIR.

18 Eyl 2026, `elegant-swanson-2a0319` — CANLIDAN TASINAN IKI VAKA + KAYNAK GERIDE:

  A8  UCUNCU KOVA (K356): suren kosum yesil sayilmaz (enjekte `gh` fiksturu).
  A9  TAVAN FRENI: panel sinirina KAYIPSIZ kirpma (A9-1 canli defteri okur).
  A7d2/A7f-h  `kur.py` KAYNAK GERIDE kolu: canli hedef yamanin ilerletilmis
      halini tasiyorsa kurulum DURUR (eski blok ikinci kez EKLENMEZ).
  A8/A9 10 Eyl'den beri yalniz `~/.claude/cron/sabah-kabul.py`de yasiyordu.

Fazlar:
  --faz on   : A1 + A6 + A7 + A8 + A9 (yazim YAPMAZ — canli spec'e dokunmaz)
  --faz tam  : hepsi (A2 canli spec'i URETIR)
  --vaka A7|A8|A9 : yalniz o vaka (A7/A8 hermetik — CI serit-b bunlari kosar)
"""

import argparse
import datetime as dt
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

CRON = os.path.join(os.path.expanduser("~"), ".claude", "cron")
VARSAYILAN_ARAC = os.path.join(CRON, "kral-sabah.py")
SPEC_DIZINI = os.path.join(CRON, "tamirci-spec")
PY = sys.executable or "python3"

# 🔴 OLCULEN ARAC BAYRAKLA SECILIR (27 Agu 2026, mimar hukmu —
# KraL-KarantinaHukmu-27Agu). ONCE: `ARAC` KURULU KOPYAYA cakiliydi; batarya
# yesil yansa da o yesil DALIN dosyasini degil kurulu kopyayi tarif ediyordu
# — ve o duzleme baska cipler de yazabiliyor. SIMDI `--arac <yol>` hedefi
# degistirir; A4 MUTANTI da o dosyadan turer. Bayraksiz davranis AYNEN eski.
ARAC = VARSAYILAN_ARAC

SONUC = []


def kayit(ad, gecti, ayrinti=""):
    SONUC.append((ad, gecti, ayrinti))
    bayrak = "GECTI" if gecti is True else ("DUSTU" if gecti is False else "OLCULEMEDI")
    print("  [%s] %-42s %s" % (bayrak, ad, ayrinti))
    return gecti


def baslik(m):
    print("\n=== %s ===" % m)


def kos(argv, zaman_asimi=180, ortam=None):
    """`ortam`: ek ortam degiskenleri (A8 `gh` enjeksiyonu). None ise ortam AYNEN."""
    try:
        cevre = None
        if ortam:
            cevre = dict(os.environ)
            cevre.update(ortam)
        r = subprocess.run(argv, capture_output=True, text=True, timeout=zaman_asimi,
                           env=cevre)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "ZAMAN_ASIMI %ds" % zaman_asimi
    except Exception as hata:
        return 125, "%s: %s" % (type(hata).__name__, hata)


def jeton(cikti, onek):
    """Ciktidan `<onek>...` ile baslayan SON satiri dondurur."""
    bulunan = "-"
    for satir in (cikti or "").splitlines():
        if satir.startswith(onek):
            bulunan = satir.strip()
    return bulunan


def bugunun_spec_yolu():
    return os.path.join(SPEC_DIZINI, "KraL-Tamirci-%s.md" % time.strftime("%Y%m%d"))


# --------------------------------------------------------------------- A1

def a1_ortam():
    baslik("A1 — ORTAM: kendini-test + crontab'in KENDI yorumlayicisi (AYRI basilir)")

    rc, cikti = kos([PY, ARAC, "--kendini-test"], 240)
    ortam = jeton(cikti, "ORTAM ")
    capraz = jeton(cikti, "KENDINI_TEST: CAPRAZ_ORTAM=")
    kayit("A1a --kendini-test rc=0", rc == 0,
          "rc=%d | %s | %s" % (rc, ortam, capraz))
    for satir in (cikti or "").splitlines():
        if satir.startswith("CAPRAZ_ORTAM"):
            print("      %s" % satir.strip())

    # A1b — CRONTAB'IN yorumlayicisi. 🔴 Yol ELLE yazilmaz: aracin KENDI
    # `crontab_yorumlayicilari()` fonksiyonundan okunur (tek kaynak).
    yorumlayicilar, sebep = crontab_yorumlayicilari_oku()
    if not yorumlayicilar:
        kayit("A1b crontab yorumlayicisiyla kosum", None,
              "OLCULEMEDI sebep=%s" % sebep)
        return
    hepsi = True
    ayrintilar = []
    for py in yorumlayicilar:
        rc2, cikti2 = kos([py, ARAC, "--ortam-testi"], 120)
        son = jeton(cikti2, "ORTAM ")
        ayrintilar.append("%s rc=%d %s" % (py, rc2, son))
        if rc2 != 0:
            hepsi = False
            ayrintilar.append("  ham=%s" % (cikti2 or "").strip()[-200:])
    kayit("A1b crontab yorumlayicisi COKMUYOR", hepsi, " || ".join(ayrintilar))


def crontab_yorumlayicilari_oku():
    """Aracin kendi fonksiyonunu KULLANIR (ikiz tanim URETILMEZ)."""
    rc, cikti = kos([PY, "-c",
                     "import importlib.util,sys;"
                     "s=importlib.util.spec_from_file_location('ks',%r);"
                     "m=importlib.util.module_from_spec(s);"
                     "s.loader.exec_module(m);"
                     "y,se=m.crontab_yorumlayicilari();"
                     "print('YORUMLAYICILAR=' + ','.join(y));"
                     "print('SEBEP=' + (se or '-'))" % ARAC], 60)
    if rc != 0:
        return [], "arac yuklenemedi rc=%d %s" % (rc, (cikti or "").strip()[-120:])
    ham = jeton(cikti, "YORUMLAYICILAR=").split("=", 1)[-1]
    sebep = jeton(cikti, "SEBEP=").split("=", 1)[-1]
    return ([p for p in ham.split(",") if p], sebep)


# --------------------------------------------------------------------- A2

def a2_gercek_kosum():
    baslik("A2 — GERCEK KOSUM bugunun spec'ini URETIYOR")
    hedef = bugunun_spec_yolu()
    once_var = os.path.isfile(hedef)
    once_boyut = os.path.getsize(hedef) if once_var else -1
    print("  TABAN: dosya_var=%d boyut=%d yol=%s" % (int(once_var), once_boyut, hedef))

    rc, cikti = kos([PY, ARAC], 240)
    ozet = jeton(cikti, "SABAH_SPEC=")
    sonuc = jeton(cikti, "SONUC_KOLU=")
    var = os.path.isfile(hedef)
    boyut = os.path.getsize(hedef) if var else -1
    kayit("A2 bugunun spec'i VAR ve boyut>0",
          rc == 0 and var and boyut > 0 and sonuc.startswith("SONUC_KOLU=SPEC_VAR"),
          "rc=%d dosya_var=%d boyut=%d" % (rc, int(var), boyut))
    print("      %s" % ozet)
    print("      %s" % sonuc)
    return {"rc": rc, "ozet": ozet, "sonuc": sonuc, "boyut": boyut}


# --------------------------------------------------------------------- A3/A4

CAPA = "    if sonuc_kirmizi:\n        rc = max(rc, 1)\n"
YAMA = "    if False:  # MUTANT: SONUC KOLU rc'yi YUKSELTMEZ\n        rc = max(rc, 1)\n"


def _yazilamaz_dizin(td):
    """mkdir'in YAPISAL olarak basarisiz oldugu bir yol: ebeveyn bir DOSYA.

    Izin bitleriyle (`chmod 500`) degil YAPIYLA engelliyoruz — izin bitleri
    root/umask/FS'ye gore degisebilir, `NotADirectoryError` degismez."""
    blok = os.path.join(td, "blok")
    with open(blok, "w", encoding="utf-8") as f:
        f.write("bu bir DOSYA; altina dizin acilamaz\n")
    return os.path.join(blok, "spec-dizini")


def a3_a4_sonuc_kolu():
    baslik("A3/A4 — SONUC KOLU: 'spec uretilmedi' hali ADIYLA raporlanir + MUTANT")
    with tempfile.TemporaryDirectory(prefix="sabah-kabul-") as td:
        yazilamaz = _yazilamaz_dizin(td)

        # --- A3 TABAN: canli arac, yazilamaz spec dizini -> KIRMIZI
        rc3, cikti3 = kos([PY, ARAC, "--spec-dizin", yazilamaz], 240)
        satir3 = jeton(cikti3, "SONUC_KOLU=")
        kayit("A3 spec yazilamayinca kol KIRMIZI yanar",
              rc3 >= 1 and satir3.startswith("SONUC_KOLU=SPEC_URETILMEDI"),
              "rc=%d | %s" % (rc3, satir3[:150]))

        # --- A3-KONTROL: normal kosum (kuru) -> kol SESSIZ, rc temiz
        rcK, ciktiK = kos([PY, ARAC, "--kuru"], 240)
        satirK = jeton(ciktiK, "SONUC_KOLU=")
        kayit("A3-KONTROL kuru kosum rc temiz",
              rcK == 0 and satirK.startswith("SONUC_KOLU=KURU"),
              "rc=%d | %s" % (rcK, satirK[:110]))

        # --- A4 MUTANT
        with open(ARAC, encoding="utf-8") as f:
            kaynak = f.read()
        capa_adedi = kaynak.count(CAPA)
        if capa_adedi != 1:
            kayit("A4a MUTANT capasi TEK", False,
                  "capa_adedi=%d (1 bekleniyor) -> mutant KOSTURULAMADI" % capa_adedi)
            kayit("A4b MUTANT A3 fiksturu YESILE DONER", None, "capa yok")
            kayit("A4c MUTANT KONTROL DEGISMEDI", None, "capa yok")
            return
        kayit("A4a MUTANT capasi TEK", True, "capa_adedi=1")

        mutant = os.path.join(td, "kral-sabah-mutant.py")
        with open(mutant, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(CAPA, YAMA))

        rcM, ciktiM = kos([PY, mutant, "--spec-dizin", yazilamaz], 240)
        satirM = jeton(ciktiM, "SONUC_KOLU=")
        # HEDEF-KOL ATFI: mutantta arac AYNI hatayi yasar (satir DEGISMEZ) ama
        # rc DUSER -> yani olen sey tam olarak "rc'yi yukselten kol"dur.
        kayit("A4b MUTANT A3 fiksturu YESILE DONER (hedef-kol atifli)",
              rc3 >= 1 and rcM == 0
              and satirM.startswith("SONUC_KOLU=SPEC_URETILMEDI"),
              "taban_rc=%d mutant_rc=%d | mutant satiri AYNEN duruyor=%d "
              "(sebep: rc yukseltme kolu)" % (
                  rc3, rcM, int(satirM.startswith("SONUC_KOLU=SPEC_URETILMEDI"))))

        rcMK, ciktiMK = kos([PY, mutant, "--kuru"], 240)
        kayit("A4c MUTANT KONTROL DEGISMEDI",
              rcMK == rcK == 0,
              "kontrol taban_rc=%d mutant_rc=%d" % (rcK, rcMK))


# --------------------------------------------------------------------- A5

def _kararli(cikti):
    """A5 kiyasi icin DETERMINIST satirlar (zaman damgasi tasiyan satir YOK)."""
    tutulan = []
    for satir in (cikti or "").splitlines():
        if satir.startswith(("ORTAM ", "SABAH_SPEC=", "SONUC_KOLU=",
                             "KENDINI_TEST:", "CAPRAZ_ORTAM")):
            tutulan.append(satir.strip())
    return tutulan


def a5_iki_tur():
    baslik("A5 — IKI ARDISIK KOSUMDA A1·A2 BIREBIR AYNI")
    rc1a, c1a = kos([PY, ARAC, "--kendini-test"], 240)
    rc2a, c2a = kos([PY, ARAC], 240)
    rc1b, c1b = kos([PY, ARAC, "--kendini-test"], 240)
    rc2b, c2b = kos([PY, ARAC], 240)

    a1_ayni = (rc1a == rc1b) and (_kararli(c1a) == _kararli(c1b))
    a2_ayni = (rc2a == rc2b) and (_kararli(c2a) == _kararli(c2b))
    kayit("A5a A1 iki turda BIREBIR", a1_ayni,
          "rc %d/%d satir %d/%d" % (rc1a, rc1b, len(_kararli(c1a)), len(_kararli(c1b))))
    kayit("A5b A2 iki turda BIREBIR", a2_ayni,
          "rc %d/%d | T1: %s | T2: %s" % (
              rc2a, rc2b, jeton(c2a, "SABAH_SPEC=")[:90], jeton(c2b, "SABAH_SPEC=")[:90]))
    if not (a1_ayni and a2_ayni):
        print("      T1 A1:\n        " + "\n        ".join(_kararli(c1a)))
        print("      T2 A1:\n        " + "\n        ".join(_kararli(c1b)))
        print("      T1 A2:\n        " + "\n        ".join(_kararli(c2a)))
        print("      T2 A2:\n        " + "\n        ".join(_kararli(c2b)))


# --------------------------------------------------------------------- A6
# ORTAM KOLU DOGRUYU OLCUYOR MU — asgari surum LITERAL degil TURETILMIS mi.
#
# 🔴 27 Agu 2026, `KraL-SabahYorumlayici-27Agu`. Kalemin vakasi: 06:20 cron
# kosumunda arac `TypeError` ile COKTU ve ayni log'a `ASGARI=3.7 UYUM=EVET`
# yazdi — yani arac KENDI CALISAMADIGI surumu "uyumlu" ilan etti.
#
# ⚠️ DURUST SINIR (iddia edilmiyor, YAZILIYOR): bir dosya IMPORT ANINDA
# coktugunde (annotation'lar `def` aninda degerlendirilir) `main()` hic
# calismaz — hicbir IC kol o cokusu "adiyla" raporlayamaz. Bu yuzden turetme
# kolunun degeri iki yerdedir: (1) `--asgari` ON-UCUS kontrolu olarak
# KOSTURULMADAN once dogru sayiyi verir, (2) capraz-ortam kolu (A1) gercek
# cokusu yakalar. A6e bu siniri OLCER, ortmez.

# 🔴 MUTANT, TURETMENIN KENDISINI oldurur — modul duzeyi degiskeni DEGIL.
# Ilk denemede capa `ASGARI_SURUM, ... = asgari_surum_turet()` satiriydi ve
# mutant A6b'yi OLDURMEDI (olculdu: 3.10 -> 3.10): cunku `--asgari` yolu o
# degiskeni HIC okumaz, fonksiyonu DOGRUDAN cagirir. Yani capa hedef kolun
# uzerinde DEGILDI ([[ad-iki-rolde-mutanti-golgeler]] ailesi). Dogru capa,
# KANITI SAYIYA CEVIREN satirdir.
MUT_A6_CAPA = '    return max(k[0] for k in kanit), kanit, ""\n'
MUT_A6_YAMA = '    return _SURUM_TABANI, [], ""  # MUTANT: kanit YOK SAYILIR (literal)\n'

FUTURE_SATIRI = "from __future__ import annotations\n"


def _alan(satir, ad):
    """'ASGARI=3.10' gibi bir alani satirdan cikarir."""
    for parca in (satir or "").split():
        if parca.startswith(ad + "="):
            return parca[len(ad) + 1:]
    return "-"


def a6_ortam_turetme():
    baslik("A6 — ORTAM KOLU: asgari surum TURETILIR (literal DEGIL) + MUTANT")
    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()

    with tempfile.TemporaryDirectory(prefix="sabah-a6-") as td:
        # --- A6a KONTROL: canli arac kendi asgarisini TURETIR ve UYUMLU der
        rcA, ciktiA = kos([PY, ARAC, "--asgari"], 120)
        satirA = jeton(ciktiA, "ASGARI_TURETME ")
        asgari_a = _alan(satirA, "ASGARI")
        kaynak_a = _alan(satirA, "ASGARI_KAYNAK")
        kayit("A6a KONTROL canli arac: UYUM=EVET + kaynak ADLI",
              rcA == 0 and _alan(satirA, "UYUM") == "EVET"
              and asgari_a not in ("-", "OLCULEMEDI") and kaynak_a != "-",
              "rc=%d ASGARI=%s KAYNAK=%s" % (rcA, asgari_a, kaynak_a))

        # --- A6b FIKSTUR: 27 Agu sabahinin ta kendisi — `__future__` satiri YOK,
        #     `str | None` annotation'lari DURUYOR. Dogru cevap 3.10, UYUM=HAYIR.
        if kaynak.count(FUTURE_SATIRI) != 1:
            kayit("A6b FIKSTUR (__future__ YOK) -> ASGARI 3.10 + UYUM=HAYIR", None,
                  "future satiri adedi=%d (1 bekleniyor)" % kaynak.count(FUTURE_SATIRI))
            asgari_b = "-"
            rcB = -1
        else:
            fx = os.path.join(td, "kral-sabah-futuresiz.py")
            with open(fx, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(FUTURE_SATIRI, "", 1))
            rcB, ciktiB = kos([PY, ARAC, "--asgari", fx], 120)
            satirB = jeton(ciktiB, "ASGARI_TURETME ")
            asgari_b = _alan(satirB, "ASGARI")
            kayit("A6b FIKSTUR (__future__ YOK) -> ASGARI 3.10 + UYUM=HAYIR",
                  rcB == 3 and asgari_b == "3.10" and _alan(satirB, "UYUM") == "HAYIR",
                  "rc=%d ASGARI=%s KAYNAK=%s" % (rcB, asgari_b, _alan(satirB, "ASGARI_KAYNAK")))

        # --- A6c FAIL-CLOSED: bu yorumlayicinin DERLEYEMEDIGI kaynak.
        #     `match/case` 3.10 sozdizimidir; 3.9'da `ast.parse` DUSER ->
        #     hukum "OLCULEMEDI + UYUM=HAYIR" olmali, sessiz yesil DEGIL.
        fx2 = os.path.join(td, "match-kullanan.py")
        with open(fx2, "w", encoding="utf-8") as f:
            f.write("def f(x):\n    match x:\n        case 1:\n            return 'bir'\n"
                    "    return '-'\n")
        rcC, ciktiC = kos([PY, ARAC, "--asgari", fx2], 120)
        satirC = jeton(ciktiC, "ASGARI_TURETME ")
        asgari_c = _alan(satirC, "ASGARI")
        uyum_c = _alan(satirC, "UYUM")
        # 3.10+ yorumlayicida ayni dosya DERLENIR -> ASGARI=3.10, UYUM=EVET.
        # Iki hal de DOGRUDUR; olculen sey "sessiz yesil YOK".
        derleyebiliyor = sys.version_info[:2] >= (3, 10)
        beklenen = (rcC == 0 and asgari_c == "3.10" and uyum_c == "EVET") if derleyebiliyor \
            else (rcC == 3 and asgari_c == "OLCULEMEDI" and uyum_c == "HAYIR")
        kayit("A6c FAIL-CLOSED: derlenemeyen kaynak sessiz YESIL DONMEZ", beklenen,
              "kosan=%s rc=%d ASGARI=%s UYUM=%s KAYNAK=%s" % (
                  ".".join(str(x) for x in sys.version_info[:2]), rcC, asgari_c, uyum_c,
                  _alan(satirC, "ASGARI_KAYNAK")))

        # --- A6d MUTANT: turetme LITERAL'e geri cevrilir -> A6b YESILE DONER
        capa_adedi = kaynak.count(MUT_A6_CAPA)
        if capa_adedi != 1 or rcB == -1:
            kayit("A6d MUTANT capasi TEK", capa_adedi == 1,
                  "capa_adedi=%d (1 bekleniyor)" % capa_adedi)
            kayit("A6e MUTANT A6b'yi YESILE cevirir (hedef-kol atifli)", None,
                  "mutant kosturulamadi")
            kayit("A6f MUTANT KONTROL (A6a) DEGISMEDI", None, "mutant kosturulamadi")
        else:
            kayit("A6d MUTANT capasi TEK", True, "capa_adedi=1")
            mut = os.path.join(td, "kral-sabah-mutant-literal.py")
            with open(mut, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(MUT_A6_CAPA, MUT_A6_YAMA, 1))
            fx = os.path.join(td, "kral-sabah-futuresiz.py")
            rcMB, ciktiMB = kos([PY, mut, "--asgari", fx], 120)
            satirMB = jeton(ciktiMB, "ASGARI_TURETME ")
            # HEDEF-KOL ATFI: mutant yalniz MODUL DUZEYI degeri literal yapar;
            # `--asgari` yolu hala turetiyor olsaydi mutant OLMEZDI. Bu yuzden
            # mutant ayrica `--asgari` yolunun da ayni fonksiyondan besledigini
            # kanitlar: A6b'nin 3.10'u KAYBOLMALI.
            kayit("A6e MUTANT A6b'yi YESILE cevirir (hedef-kol atifli)",
                  asgari_b == "3.10" and _alan(satirMB, "ASGARI") != "3.10",
                  "taban ASGARI=%s -> mutant ASGARI=%s (rc %d->%d)" % (
                      asgari_b, _alan(satirMB, "ASGARI"), rcB, rcMB))
            rcMA, ciktiMA = kos([PY, mut, "--asgari"], 120)
            kayit("A6f MUTANT KONTROL (A6a) DEGISMEDI",
                  rcMA == rcA == 0 and _alan(jeton(ciktiMA, "ASGARI_TURETME "), "UYUM") == "EVET",
                  "kontrol taban_rc=%d mutant_rc=%d" % (rcA, rcMA))

        # --- A6g SINIR OLCUMU (ortulmuyor): future'suz fikstur BU yorumlayiciyla
        #     DOGRUDAN kosturulunca ne olur? Import aninda coker -> IC kol
        #     ulasilmaz. Kolun degeri ON-UCUS (`--asgari`) + capraz ortamdadir.
        fx = os.path.join(td, "kral-sabah-futuresiz.py")
        if os.path.isfile(fx):
            rcG, ciktiG = kos([PY, fx, "--kuru"], 120)
            if sys.version_info[:2] >= (3, 10):
                kayit("A6g SINIR: fikstur BU yorumlayicida (>=3.10) KOSAR", rcG in (0, 1, 3),
                      "rc=%d (3.10+ zaten destekliyor)" % rcG)
            else:
                kayit("A6g SINIR: fikstur import aninda COKER, ic kol ULASILMAZ",
                      rcG != 0 and "TypeError" in (ciktiG or ""),
                      "rc=%d TypeError=%d — bu yuzden A6b ON-UCUS kolu SART" % (
                          rcG, int("TypeError" in (ciktiG or ""))))


# --------------------------------------------------------------------- A7
# KURUCU IDEMPOTENSI (K320) — `capa ⊂ yeni` sinifi.
#
# Eski kol: `if metin.count(yeni) >= 1 and capa_adedi == 0: ZATEN`. EKLEME tipi
# yamalarda capa eklenen metnin ICINDE kalir -> kurulumdan sonra da
# `capa_adedi == 1` -> her kosum yeniden UYGULA -> ICERIK COGALIR.
# Kusur `--geri-al`li yordamla maskelenmisti; kanit ARGUMANSIZ IKINCI KOSUMDUR.

MUT_A7_CAPA = "        if yeni_adedi == 1:\n"
MUT_A7_YAMA = "        if yeni_adedi == 1 and capa_adedi == 0:  # MUTANT: eski kol\n"

# 🔴 SENTETIK TABAN (16 Eyl 2026) — A7 ARTIK GERCEK YEDEK DUZLEMINE BAGLI DEGIL.
# ONCE: taban `_en_eski_yedek()` ile `~/.claude/cron/<ad>.yedek-sabahteslim-*`
# dosyalarindan kuruluyordu. O yedekler BU makinede yoktu ve CI'da HICBIR ZAMAN
# olmayacak -> A7b/A7c `OLCULEMEDI` donuyor, K320'nin onarimi kabul EDILEMIYORDU
# ([[emir-canliligi-kurulu-kopyadan-olculur]] kardesi: olculen duzlem YOKSA hukum
# de yok). SIMDI taban `kur.py` `yamalar()` CAPA SOZLESMESINDEN URETILIR: her
# hedef dosya icin capalari BIREBIR tasiyan, DERLENEBILIR bir stub yazilir.
# Hedef listesi de ELLE TUTULMAZ, `yamalar()`tan turer (bayat liste sinifi yok).

_ACIK = {"(": ")", "[": "]", "{": "}"}
_KAPALI = {")": "(", "]": "[", "}": "{"}
_TIRNAKLAR = ('"""', "'''", '"', "'")
_BLOK_DEVAMI = ("elif ", "else:", "except", "finally:")


def _parantez_dengesi(metin):
    """(ONCE acilmasi gereken parantezler, SONRA kapatilmasi gerekenler).

    Capa metinleri ifade ORTASINDAN baslayabilir (or. bir liste literalinin
    kapanis `]`'i). Dizge (tek/uc tirnak, kacis) ve `#` yorumu farkindadir.
    """
    yigin, eksik = [], []
    i, n, tirnak = 0, len(metin), None
    while i < n:
        c = metin[i]
        if tirnak:
            if c == "\\" and len(tirnak) == 1:
                i += 2
            elif metin.startswith(tirnak, i):
                i += len(tirnak)
                tirnak = None
            else:
                i += 1
            continue
        if c == "#":
            j = metin.find("\n", i)
            i = n if j < 0 else j
            continue
        acilan = next((t for t in _TIRNAKLAR if metin.startswith(t, i)), None)
        if acilan:
            tirnak = acilan
            i += len(acilan)
            continue
        if c in _ACIK:
            yigin.append(c)
        elif c in _KAPALI:
            if yigin and yigin[-1] == _KAPALI[c]:
                yigin.pop()
            else:
                eksik.append(_KAPALI[c])
        i += 1
    return eksik, yigin


def _girinti(satir):
    return len(satir) - len(satir.lstrip())


def _dolu_satirlar(metin):
    return [s for s in metin.splitlines() if s.strip()]


def _iskele_olcutu(metin):
    """Bir metin parcasini derlenebilir kilmak icin gereken iskelenin TARIFI."""
    sat = _dolu_satirlar(metin)
    if not sat:
        return (0, None, (), (), ())
    taban = min(_girinti(s) for s in sat)
    kuyruk = _girinti(sat[-1]) + 4 if sat[-1].rstrip().endswith(":") else None
    eksik, acik = _parantez_dengesi(metin)
    bas = tuple(k for k in _BLOK_DEVAMI if sat[0].lstrip().startswith(k))
    return (taban, kuyruk, tuple(eksik), tuple(acik), bas)


def _sar(capa, yeni, sira):
    """Capayi BIREBIR koruyarak derlenebilir bir govdeye sarar.

    🔴 FAIL-CLOSED: iskele hem capa hem de YAMA SONRASI metin (`yeni`) icin
    gecerli olmali. Ikisinin olcutu ayrisiyorsa stub URETILMEZ — sessizce
    derlenmeyen bir taban yazip "olculemedi"yi gizlemek yerine SEBEP basilir.
    """
    o_capa, o_yeni = _iskele_olcutu(capa), _iskele_olcutu(yeni)
    if o_capa != o_yeni:
        raise ValueError("yama %02d: capa/yeni iskele olcutu AYRISIYOR %r != %r"
                         % (sira, o_capa, o_yeni))
    taban, kuyruk, eksik, acik, bas = o_capa

    on = []
    if taban:
        on.append("def _capa_%02d():\n" % sira)
        for d in range(4, taban, 4):
            on.append(" " * d + "if True:\n")
    if bas:
        on.append(" " * taban + "if False:\n")
        on.append(" " * (taban + 4) + "pass\n")
    if eksik:
        on.append(" " * taban + "_iskele = "
                  + "".join(reversed(eksik)) + "\n")

    arka = []
    if acik:
        arka.append(" " * taban + "".join(_ACIK[k] for k in reversed(acik)) + "\n")
    if kuyruk is not None:
        arka.append(" " * kuyruk + "pass\n")
    if taban:
        arka.append(" " * taban + "pass\n")
    govde = capa if capa.endswith("\n") else capa + "\n"
    return "".join(on) + govde + "".join(arka)


def _stub_metni(Y, hedef):
    parcalar = ["#!/usr/bin/env python3\n", "# -*- coding: utf-8 -*-\n",
                '"""SENTETIK A7 FIKSTURU — %s.\n\n'
                'Bu dosya gercek `%s`nin kopyasi DEGILDIR; `kur.py` yamalar()\n'
                'capa sozlesmesinden URETILMISTIR. Amaci kurucunun IDEMPOTENS\n'
                'kolunu (`capa subset yeni` sinifi) gercek yedek duzlemine\n'
                'dokunmadan olcmektir.\n"""\n' % (hedef, hedef)]
    for sira, (h, capa, yeni, _a) in enumerate(Y):
        if h != hedef:
            continue
        parcalar.append("\n\n# =capa= %02d =\n" % sira)
        parcalar.append(_sar(capa, yeni, sira))
    return "".join(parcalar)


def _yamalari_oku(kurucu):
    """`kur.py`nin yamalar() sozlesmesini OKUR (ONCUL: capa listesi oradan turer)."""
    import importlib.util
    onceki = list(sys.path)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(kurucu)))
        spec = importlib.util.spec_from_file_location("_a7_kurmod", kurucu)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.yamalar()
    finally:
        sys.path[:] = onceki


def _sentetik_cron(Y, dizin):
    """Sahte CRON dizinini capa sozlesmesinden kurar; (hedefler, sorun) dondurur."""
    os.makedirs(dizin, exist_ok=True)
    hedefler = sorted({y[0] for y in Y})
    sorunlar = []
    for hedef in hedefler:
        try:
            metin = _stub_metni(Y, hedef)
        except ValueError as hata:
            sorunlar.append(str(hata))
            continue
        try:
            compile(metin, hedef, "exec")
        except SyntaxError as hata:
            sorunlar.append("%s stub DERLENMIYOR: %s (satir %s)"
                            % (hedef, hata.msg, hata.lineno))
            continue
        cogul = [i for i, (h, c, _y, _a) in enumerate(Y)
                 if h == hedef and metin.count(c) != 1]
        if cogul:
            sorunlar.append("%s stub'unda capa sayimi != 1: yama %s"
                            % (hedef, ",".join("%02d" % i for i in cogul)))
            continue
        with open(os.path.join(dizin, hedef), "w", encoding="utf-8") as f:
            f.write(metin)
    return hedefler, sorunlar


KURUCU_YOLU = None  # --kurucu ile civilenir


def _kurucu_yolu():
    """🔴 OLCUM DUZLEMI ADIYLA SECILIR — ilk surumde SESSIZ dusuluyordu.

    Olculdu (27 Agu): batarya KURULU kopyadan (`~/.claude/cron/`) kostugu icin
    `dirname(__file__)/kur.py` YOKTU ve akis sessizce ANA CHECKOUT'un kur.py'sine
    dusuyordu — yani DALDAKI onarim degil, main'deki ESKI kurucu olculuyordu
    (`rc=2 unrecognized arguments`, `capa_adedi=0`). Bu tam olarak bu kalemin
    sinifi: OLCULEN DUZLEM ile ONARILAN DUZLEM ayrisirsa hukum yalandir
    ([[emir-canliligi-kurulu-kopyadan-olculur]]). Artik yol ya ACIKCA verilir
    ya da hangi adayin secildigi BASILIR.
    """
    if KURUCU_YOLU:
        return (KURUCU_YOLU, "--kurucu") if os.path.isfile(KURUCU_YOLU) else (None, "--kurucu YOK")
    aday = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kur.py")
    if os.path.isfile(aday):
        return aday, "batarya_yani"
    aday = "/Users/okan/dev/pruvo/tools/sabah-teslim/kur.py"
    if os.path.isfile(aday):
        return aday, "ana_checkout"
    return None, "BULUNAMADI"


def _dizin_parmak_izi(dizin):
    """Dizindeki her dosyanin (bayt, sha256) izi — BIREBIR kiyas icin."""
    izler = {}
    for ad in sorted(os.listdir(dizin)):
        yol = os.path.join(dizin, ad)
        if os.path.isfile(yol):
            with open(yol, "rb") as f:
                ham = f.read()
            izler[ad] = (len(ham), hashlib.sha256(ham).hexdigest()[:16])
    return izler


def a7_kurucu_idempotens():
    baslik("A7 — KURUCU IDEMPOTENSI: `capa ⊂ yeni` + ARGUMANSIZ IKINCI KOSUM")
    kurucu, nereden = _kurucu_yolu()
    if not kurucu:
        kayit("A7a SINIF sayimi: kac yama `capa ⊂ yeni`", None, "kur.py YOK (%s)" % nereden)
        kayit("A7b TAZE kurulum + IKINCI kosum BIREBIR", None, "kur.py YOK (%s)" % nereden)
        kayit("A7c MUTANT capasi TEK", None, "kur.py YOK (%s)" % nereden)
        return
    print("  kurucu=%s (kaynak: %s)" % (kurucu, nereden))

    with open(kurucu, encoding="utf-8") as f:
        kur_kaynak = f.read()

    # 🔴 DUZLEM PROBU: olculecek kurucu FIKSTUR destekliyor mu. Desteklemiyorsa
    #    "dustu" DEMEYIZ — `OLCULEMEDI` + SEBEP yazariz (bayat duzlem ≠ arizali kol).
    if "--cron-dizin" not in kur_kaynak:
        kayit("A7a SINIF sayimi: kac yama `capa ⊂ yeni`", None,
              "BAYAT DUZLEM: %s `--cron-dizin` TASIMIYOR (kaynak: %s)" % (kurucu, nereden))
        kayit("A7b TAZE kurulum + IKINCI kosum BIREBIR", None, "bayat duzlem")
        kayit("A7c MUTANT capasi TEK", None, "bayat duzlem")
        return

    # --- A7a: SINIFIN BUYUKLUGU SAYIYLA basilir (iddia degil).
    rcS, ciktiS = kos([PY, "-c",
                       "import sys; sys.path.insert(0, %r); "
                       "import importlib.util as u; "
                       "s = u.spec_from_file_location('kurmod', %r); "
                       "m = u.module_from_spec(s); s.loader.exec_module(m); "
                       "Y = m.yamalar(); "
                       "print('YAMA_SINIF toplam=%%d capa_alt_kume=%%d' %% "
                       "(len(Y), sum(1 for h, c, y, a in Y if c in y)))"
                       % (os.path.dirname(kurucu), kurucu)], 120)
    satirS = jeton(ciktiS, "YAMA_SINIF ")
    alt = _alan(satirS, "capa_alt_kume")
    kayit("A7a SINIF sayimi: kac yama `capa ⊂ yeni`",
          rcS == 0 and alt not in ("-", ""),
          "%s (bu yamalarda capa kurulumdan SONRA da gorunur)" % satirS[:110])

    with tempfile.TemporaryDirectory(prefix="sabah-a7-") as td:
        # --- SENTETIK TABAN: capa sozlesmesinden uretilir (gercek yedek YOK).
        try:
            Y = _yamalari_oku(kurucu)
        except Exception as hata:
            kayit("A7b TAZE kurulum + IKINCI kosum BIREBIR", None,
                  "yamalar() OKUNAMADI: %s: %s" % (type(hata).__name__, hata))
            kayit("A7c MUTANT capasi TEK", None, "taban yok")
            kayit("A7d MUTANT ikinci kosumu COGALTIR", None, "taban yok")
            return

        sahte_cron = os.path.join(td, "cron")
        hedefler, sorunlar = _sentetik_cron(Y, sahte_cron)
        alt_kume = sum(1 for _h, c, y, _a in Y if c in y)
        print("  SENTETIK_TABAN hedef=%d (%s) capa_alt_kume=%d"
              % (len(hedefler), ",".join(hedefler), alt_kume))
        if sorunlar:
            # 🔴 Sessiz yesil YOK: taban kurulamadi, sebebi ADIYLA yazilir.
            kayit("A7b TAZE kurulum + IKINCI kosum BIREBIR", None,
                  "SENTETIK TABAN KURULAMADI: %s" % " | ".join(sorunlar)[:220])
            kayit("A7c MUTANT capasi TEK", None, "taban yok")
            kayit("A7d MUTANT ikinci kosumu COGALTIR", None, "taban yok")
            return
        if alt_kume < 1:
            # Mutantin oldurecegi SINIF bos ise A7d anlamsizdir; sessizce
            # yesil yanmasin diye ADIYLA durulur.
            kayit("A7b TAZE kurulum + IKINCI kosum BIREBIR", None,
                  "capa_alt_kume=0 — olculecek `capa subset yeni` sinifi YOK")
            kayit("A7c MUTANT capasi TEK", None, "sinif bos")
            kayit("A7d MUTANT ikinci kosumu COGALTIR", None, "sinif bos")
            return

        cikti_d = os.path.join(td, "log")
        ortak = ["--cron-dizin", sahte_cron, "--cikti-dizin", cikti_d]

        rc1, c1 = kos([PY, kurucu] + ortak, 240)
        ozet1 = jeton(c1, "YAMA_OZET ")
        iz1 = _dizin_parmak_izi(sahte_cron)

        rc2, c2 = kos([PY, kurucu] + ortak, 240)
        ozet2 = jeton(c2, "YAMA_OZET ")
        iz2 = _dizin_parmak_izi(sahte_cron)

        birebir = iz1 == iz2
        uygulanan2 = _alan(ozet2, "uygulanan")
        kayit("A7b TAZE kurulum + IKINCI kosum BIREBIR (cogaltma=0)",
              rc1 == 0 and rc2 == 0 and birebir and uygulanan2 == "0",
              "T1 rc=%d %s | T2 rc=%d %s | bayt_birebir=%d" % (
                  rc1, ozet1[:64], rc2, ozet2[:64], int(birebir)))
        if not birebir:
            for ad in sorted(set(list(iz1) + list(iz2))):
                if iz1.get(ad) != iz2.get(ad):
                    print("      SAPMA %s: T1=%s T2=%s" % (ad, iz1.get(ad), iz2.get(ad)))

        # --- A7c MUTANT: idempotens kolunu ESKI hale (capa_adedi == 0) cevir.
        capa_adedi = kur_kaynak.count(MUT_A7_CAPA)
        if capa_adedi != 1:
            kayit("A7c MUTANT capasi TEK", False,
                  "capa_adedi=%d (1 bekleniyor)" % capa_adedi)
            kayit("A7d MUTANT ikinci kosumu COGALTIR (hedef-kol atifli)", None, "capa yok")
            return
        kayit("A7c MUTANT capasi TEK", True, "capa_adedi=1")

        # 🔴 18 Eyl 2026: `kur.py` ARTIK IKI KATLI — idempotens kolunun arkasinda
        # KAYNAK GERIDE kolu (A7f) durur ve eski-kol mutantinin ikinci kosumunu
        # fail-closed DURDURUR (rc=3, yazim yok). Tek kolu soken mutant bu yuzden
        # COGALTAMAZ ve A7d'yi olduremezdi ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
        # A7d'nin mutanti IKI kolu birlikte soker (idempotens kolunun cogaltmayi
        # onleyen kol oldugunu korumasiz zeminde kanitlar); tek-kol mutanti A7d2'de
        # ikinci katin DURDURDUGUNU olcer.
        mut_dizin = os.path.join(td, "mutant-kaynak")
        shutil.copytree(os.path.dirname(kurucu), mut_dizin,
                        ignore=shutil.ignore_patterns("__pycache__"))
        mut_kurucu = os.path.join(mut_dizin, "kur.py")
        tek_kol = kur_kaynak.replace(MUT_A7_CAPA, MUT_A7_YAMA, 1)
        ikinci_kat = kur_kaynak.count(MUT_A7G_CAPA) == 1
        with open(mut_kurucu, "w", encoding="utf-8") as f:
            f.write(tek_kol.replace(MUT_A7G_CAPA, MUT_A7G_YAMA, 1) if ikinci_kat else tek_kol)
        tek_dizin = os.path.join(td, "mutant-tek-kol")
        shutil.copytree(os.path.dirname(kurucu), tek_dizin,
                        ignore=shutil.ignore_patterns("__pycache__"))
        with open(os.path.join(tek_dizin, "kur.py"), "w", encoding="utf-8") as f:
            f.write(tek_kol)

        # Mutant TAZE bir sentetik tabandan baslar (taban AYNI sozlesmeden
        # uretilir; degisen TEK sey kurucunun idempotens koludur).
        m_cron = os.path.join(td, "cron-mutant")
        _hedefler_m, m_sorun = _sentetik_cron(Y, m_cron)
        if m_sorun:
            kayit("A7d MUTANT ikinci kosumu COGALTIR (hedef-kol atifli)", None,
                  "mutant tabani kurulamadi: %s" % " | ".join(m_sorun)[:160])
            kayit("A7e MUTANT KONTROL: ILK kosum DEGISMEDI", None, "mutant tabani yok")
            return
        m_ortak = ["--cron-dizin", m_cron, "--cikti-dizin", os.path.join(td, "log-m")]

        rcM1, cM1 = kos([PY, mut_kurucu] + m_ortak, 240)
        izM1 = _dizin_parmak_izi(m_cron)
        rcM2, cM2 = kos([PY, mut_kurucu] + m_ortak, 240)
        izM2 = _dizin_parmak_izi(m_cron)
        m_birebir = izM1 == izM2
        # HEDEF-KOL ATFI: mutant YALNIZ idempotens sartini degistirir. Ilk kosum
        # AYNI kalir (rc ve uygulanan), ikinci kosum COGALTIR. Yani olen sey tam
        # olarak "sonuc ekseninden okuyan idempotens kolu"dur.
        kayit("A7d MUTANT ikinci kosumu COGALTIR (hedef-kol atifli)",
              birebir and not m_birebir,
              "taban T1==T2 %d | mutant T1==T2 %d | mutant T1 %s / T2 %s" % (
                  int(birebir), int(m_birebir),
                  jeton(cM1, "YAMA_OZET ")[:52], jeton(cM2, "YAMA_OZET ")[:52]))
        kayit("A7e MUTANT KONTROL: ILK kosum DEGISMEDI",
              rcM1 == rc1 and _alan(jeton(cM1, "YAMA_OZET "), "uygulanan")
              == _alan(ozet1, "uygulanan"),
              "taban ilk=%s mutant ilk=%s" % (
                  _alan(ozet1, "uygulanan"), _alan(jeton(cM1, "YAMA_OZET "), "uygulanan")))

        # --- A7d2: YALNIZ idempotens kolu sokuldu -> ikinci kat DURDURUR.
        if not ikinci_kat:
            kayit("A7d2 TEK-KOL MUTANT: ikinci kat (KAYNAK GERIDE) DURDURUR", False,
                  "kurucuda KAYNAK GERIDE kolu YOK (capa_adedi=%d)"
                  % kur_kaynak.count(MUT_A7G_CAPA))
        else:
            t_cron = os.path.join(td, "cron-tek-kol")
            _sentetik_cron(Y, t_cron)
            t_ortak = ["--cron-dizin", t_cron, "--cikti-dizin", os.path.join(td, "log-t")]
            t_kurucu = os.path.join(tek_dizin, "kur.py")
            kos([PY, t_kurucu] + t_ortak, 240)
            izT1 = _dizin_parmak_izi(t_cron)
            rcT2, cT2 = kos([PY, t_kurucu] + t_ortak, 240)
            ozT2 = jeton(cT2, "YAMA_OZET ")
            kayit("A7d2 TEK-KOL MUTANT: ikinci kat (KAYNAK GERIDE) DURDURUR",
                  rcT2 == 3 and _dizin_parmak_izi(t_cron) == izT1
                  and _alan(ozT2, "kaynak_geride") not in ("-", "0"),
                  "T2 rc=%d bayt_degismedi=%d %s" % (
                      rcT2, int(_dizin_parmak_izi(t_cron) == izT1), ozT2[-44:]))

        a7_kaynak_geride(kurucu, kur_kaynak, Y, sahte_cron, td)


# 🔴 A7f-h — KAYNAK GERIDE (18 Eyl 2026, `elegant-swanson-2a0319`). Olculen vaka:
# canli `bekci-kabul.py` H bataryasi 28 Agu'da (K331) elle ilerletildi, repodaki
# `kabul-blok.py` geride kaldi. `kur.py --kuru` bu yamaya `UYGULANDI` dedi: capa
# (`# ---- ana`) hala TEK, `yeni` artik yok -> ESKI H blogu IKINCI KEZ eklenecekti;
# yalniz komsu yamanin capa cokmesi kurulumu durdurdu (tesaduf korumasi).
MUT_A7G_CAPA = "        if imza is not None and imza in metin:\n"
MUT_A7G_YAMA = "        if False:  # MUTANT: KAYNAK GERIDE kolu YOK\n"
A7F_SATIR = "# A7f FIKSTURU: canli bu blogu kurulumdan SONRA ilerletti\n"


def _ileri_surum(Y, sahte_cron, imza_fn):
    """Kurulu sahte tabanda bir EKLE yamasini 'canli ilerletti' haline getirir.

    Doner (yama_sirasi, hedef) ya da (None, sebep)."""
    for sira, (hedef, capa, yeni, _a) in enumerate(Y):
        if capa not in yeni:
            continue
        imza = imza_fn(capa, yeni)
        if imza is None:
            continue
        yol = os.path.join(sahte_cron, hedef)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        if metin.count(yeni) != 1 or metin.count(imza + "\n") != 1:
            continue
        girinti = " " * _girinti(imza)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin.replace(imza + "\n", imza + "\n" + girinti + A7F_SATIR, 1))
        return sira, hedef
    return None, "uygun EKLE yamasi yok (capa ⊂ yeni ∧ imza TEK)"


def a7_kaynak_geride(kurucu, kur_kaynak, Y, sahte_cron, td):
    try:
        import importlib.util as _u
        s = _u.spec_from_file_location("_a7f_kurmod", kurucu)
        m = _u.module_from_spec(s)
        s.loader.exec_module(m)
        imza_fn = m.yama_imzasi
    except Exception as hata:
        kayit("A7f KAYNAK GERIDE: ilerlemis hedef -> kurulum DURUR", False,
              "kurucu `yama_imzasi` TASIMIYOR: %s: %s" % (type(hata).__name__, hata))
        kayit("A7g MUTANT ilerlemis hedefe ESKI blogu IKINCI KEZ ekler", None, "kol yok")
        kayit("A7h MUTANT KONTROL: ilerlememis hedef DEGISMEDI", None, "kol yok")
        return

    f_cron = os.path.join(td, "cron-geride")
    shutil.copytree(sahte_cron, f_cron)
    sira, hedef = _ileri_surum(Y, f_cron, imza_fn)
    if sira is None:
        kayit("A7f KAYNAK GERIDE: ilerlemis hedef -> kurulum DURUR", None, hedef)
        kayit("A7g MUTANT ilerlemis hedefe ESKI blogu IKINCI KEZ ekler", None, "fikstur yok")
        kayit("A7h MUTANT KONTROL: ilerlememis hedef DEGISMEDI", None, "fikstur yok")
        return
    m_fikstur = os.path.join(td, "cron-geride-mutant")
    shutil.copytree(f_cron, m_fikstur)

    iz0 = _dizin_parmak_izi(f_cron)
    rcF, cF = kos([PY, kurucu, "--cron-dizin", f_cron,
                   "--cikti-dizin", os.path.join(td, "log-f")], 240)
    izF = _dizin_parmak_izi(f_cron)
    kayit("A7f KAYNAK GERIDE: ilerlemis hedef -> kurulum DURUR (hic yazim yok)",
          rcF == 3 and "[KAYNAK_GERIDE]" in cF and izF == iz0
          and _alan(jeton(cF, "YAMA_OZET "), "kaynak_geride") == "1",
          "yama=%02d hedef=%s rc=%d %s | bayt_degismedi=%d" % (
              sira, hedef, rcF, jeton(cF, "YAMA_OZET ")[-40:], int(izF == iz0)))

    if kur_kaynak.count(MUT_A7G_CAPA) != 1:
        kayit("A7g MUTANT ilerlemis hedefe ESKI blogu IKINCI KEZ ekler", False,
              "capa_adedi=%d (1 bekleniyor)" % kur_kaynak.count(MUT_A7G_CAPA))
        kayit("A7h MUTANT KONTROL: ilerlememis hedef DEGISMEDI", None, "capa yok")
        return
    mut_dizin = os.path.join(td, "mutant-geride")
    shutil.copytree(os.path.dirname(kurucu), mut_dizin,
                    ignore=shutil.ignore_patterns("__pycache__"))
    mut = os.path.join(mut_dizin, "kur.py")
    with open(mut, "w", encoding="utf-8") as f:
        f.write(kur_kaynak.replace(MUT_A7G_CAPA, MUT_A7G_YAMA, 1))

    izM0 = _dizin_parmak_izi(m_fikstur)
    rcM, cM = kos([PY, mut, "--cron-dizin", m_fikstur,
                   "--cikti-dizin", os.path.join(td, "log-fm")], 240)
    izM = _dizin_parmak_izi(m_fikstur)
    with open(os.path.join(m_fikstur, hedef), encoding="utf-8") as f:
        yeni_adedi = f.read().count(Y[sira][2])
    # HEDEF-KOL ATFI: mutant YALNIZ imza kolunu soker; olen sey tam olarak o
    # kol ise mutant ilerlemis hedefe ESKI `yeni`yi ekler (yeni_adedi 0 -> 1)
    # ve rc=0 ile "basarili kurulum" der.
    kayit("A7g MUTANT ilerlemis hedefe ESKI blogu IKINCI KEZ ekler (hedef-kol atifli)",
          rcM == 0 and izM != izM0 and yeni_adedi == 1,
          "mutant rc=%d bayt_degisti=%d eski_blok_eklendi=%d" % (
              rcM, int(izM != izM0), yeni_adedi))

    izK0 = _dizin_parmak_izi(sahte_cron)
    rcK, cK = kos([PY, mut, "--cron-dizin", sahte_cron,
                   "--cikti-dizin", os.path.join(td, "log-fk")], 240)
    kayit("A7h MUTANT KONTROL: ilerlememis hedef DEGISMEDI",
          rcK == 0 and _dizin_parmak_izi(sahte_cron) == izK0
          and _alan(jeton(cK, "YAMA_OZET "), "uygulanan") == "0",
          "mutant rc=%d %s" % (rcK, jeton(cK, "YAMA_OZET ")[:70]))


# --------------------------------------------------------------------- A8

# 🔴 K356 — UCUNCU KOVA CAPASI. Mutant, kolu ESKI IKI-KOVALI hale geri cevirir:
# "kirmizi kumesinde degilse ATLA" (yani suren kosum SESSIZCE YESIL sayilir).
# 🔴 18 Eyl 2026 (`elegant-swanson-2a0319`): capa BAYATLAMISTI — 18 Eyl sabahi
# siniflama `kirmizi_siniflandir()`e tasindi (girinti 12->8, kirmizi satiri
# ardil hukmunu tasiyor) ve canli A8d `capa_adedi=0` ile DUSUYORDU. Kirmizi
# satirinin govdesi artik capaya GIRMEZ: capa YALNIZ iki hukumsuz kolu tutar
# (ikisi de sokulmeli — biri kalirsa suren kosum "BILINMEYEN SONUC" kovasindan
# yine yakalanir ve mutant OLMEZ). Her capa TEK olmali.
A8_CAPALAR = (
    ('        if durum != "completed":\n'
     '            hukumsuz.append("- [{}] {} · dal={} (HÜKÜM YOK: koşum sürüyor)".format(\n'
     '                durum or "durum-yok", ad, dal))\n'
     '        elif conc in KIRMIZI_KUME:\n',
     '        if False:  # MUTANT (K356): UCUNCU KOVA YOK — iki-kovali eski hal\n'
     '            pass\n'
     '        elif conc in KIRMIZI_KUME:\n'),
    ('        elif conc not in YESIL_KUME:\n',
     '        elif False:  # MUTANT (K356): bilinmeyen sonuc da yesil sayilir\n'),
)

_A8_SAHTE_GH = (
    "#!/usr/bin/env python3\n"
    "# GECICI KABUL FIKSTURU (A8) — argv'yi yok sayar, sabit JSON basar.\n"
    "import sys\n"
    "print(%r)\n"
    "sys.exit(0)\n"
)


def _a8_gh_yaz(td, ad, kayitlar):
    """`gh run list --json ...` ciktisini TAKLIT eden calistirilabilir fikstur."""
    import json as _json
    gun = time.strftime("%Y-%m-%d", time.gmtime())
    veri = []
    for ad_i, durum, conc, saat in kayitlar:
        veri.append({
            "name": ad_i,
            "status": durum,
            "conclusion": conc,
            "createdAt": "%sT%sZ" % (gun, saat),
            "headBranch": "main",
        })
    yol = os.path.join(td, ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(_A8_SAHTE_GH % _json.dumps(veri, ensure_ascii=False))
    os.chmod(yol, 0o755)
    return yol


def _a8_kos(arac, gh_yolu, spec_dizin):
    rc, cikti = kos([PY, arac, "--spec-dizin", spec_dizin], 240,
                    ortam={"_KRAL_SABAH_GH_YOL": gh_yolu})
    satir = jeton(cikti, "SABAH_SPEC=")
    return rc, satir, cikti


# 🔴 A8 KUMU (18 Eyl 2026, `elegant-swanson-2a0319`). `kral-sabah.py` KUTU/KALEMLER/
# DEVAM/REPO/MOTOR_RAPORU_DOSYA'yi SABIT Mac yoluyla okur. Mac'te bos-HOME aynasi
# bile YESIL verdi (yollar HOME'dan degil mutlak) ama CI dal kosumu `35355261365`
# A8'i KIRMIZI yakti: KALEMLER okunamayinca arac `rc=1` doner (fail-loud kolu) ve
# A8a "temiz gun rc=0" sarti duser ([[ayna-kosumu-ci-git-baglam-env-mirasi-alir]]).
# Onarim araca DOKUNMAZ (canli kurulu kopya korunur): A8 kopyasinda bu bes sabit
# ayni bicimde kuma cevrilir; mutant AYNI kumlu kopyadan turer -> iki taraf arasindaki
# TEK fark A8 capasidir (hedef-kol atfi korunur). Sabit bulunamazsa fail-closed.
A8_KUM_SABITLERI = ("KUTU", "KALEMLER", "DEVAM", "REPO", "MOTOR_RAPORU_DOSYA")


def _a8_kumla(kaynak, td):
    """(kumlu_kaynak, None) ya da (None, sebep). REPO/DEVAM = bu checkout (salt okuma)."""
    kum = os.path.join(td, "kum")
    os.makedirs(kum, exist_ok=True)
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    yollar = {
        "KUTU": os.path.join(kum, "mimar-posta-kutusu.md"),
        "KALEMLER": os.path.join(kum, "acik-kalemler.md"),
        "DEVAM": os.path.join(repo, "DEVAM.md"),
        "REPO": repo,
        "MOTOR_RAPORU_DOSYA": os.path.join(kum, "gunluk-motor-raporu-YOK.py"),
    }
    with open(yollar["KUTU"], "w", encoding="utf-8") as f:
        f.write("# A8 kum kutusu\n")
    with open(yollar["KALEMLER"], "w", encoding="utf-8") as f:
        f.write("# A8 kum defteri\n\n| ID | Tarih | Kimden | Is | Durum | Kanit |\n"
                "|---|---|---|---|---|---|\n")
    for ad in A8_KUM_SABITLERI:
        desen = re.compile(r'^%s = Path\("[^"\n]*"\)\n' % ad, re.M)
        adet = len(desen.findall(kaynak))
        if adet != 1:
            return None, "%s sabiti adedi=%d (1 bekleniyor)" % (ad, adet)
        kaynak = desen.sub(lambda _m, a=ad: "%s = Path(%r)\n" % (a, yollar[a]), kaynak)
    return kaynak, None


def a8_ucuncu_kova():
    """A8 — HUKMU OLMAYAN KOSUM YESIL SAYILAMAZ (K356).

    31 Agu 2026 OLCUMU (iddia degil): `Nöbet şeridi (SERIT B)` 02:24:45Z basladi,
    03:30:16Z `failure` kapandi; sabah spec'i 03:20:02Z uretildi -> o an
    `conclusion=null` idi, eski iki-kovali dongu onu ATLADI ve baslik
    "HUKUM=OK · ADET=0 (OLCULDU)" bastı. AYNI KOD 09:5xZ'de degistirilmeden
    `KIRMIZI=1` verdi. Bu vaka o ucuncu kovayi olcer.
    """
    baslik("A8 — UCUNCU KOVA: HUKMU OLMAYAN KOSUM (K356) + MUTANT")
    with tempfile.TemporaryDirectory(prefix="sabah-a8-") as td:
        spec_dizin = os.path.join(td, "spec")
        os.makedirs(spec_dizin, exist_ok=True)

        gh_saglikli = _a8_gh_yaz(td, "gh-saglikli", [
            ("Build & deploy to GitHub Pages", "completed", "success", "02:24:45"),
            ("D1 uzlastirici", "completed", "success", "01:39:05"),
        ])
        gh_suren = _a8_gh_yaz(td, "gh-suren", [
            ("Build & deploy to GitHub Pages", "completed", "success", "02:24:45"),
            ("Nöbet şeridi (SERIT B)", "in_progress", None, "02:24:45"),
        ])
        gh_karma = _a8_gh_yaz(td, "gh-karma", [
            ("Odeme yolu bayatlik nabzi", "completed", "failure", "02:24:45"),
            ("Nöbet şeridi (SERIT B)", "in_progress", None, "02:24:45"),
        ])

        with open(ARAC, encoding="utf-8") as f:
            kaynak, kum_sorun = _a8_kumla(f.read(), td)
        if kum_sorun:
            for ad in ("A8a KONTROL temiz gun: OK + ADET=0 + rc=0",
                       "A8b SUREN KOSUM yesil sayilmaz -> OLCULEMEDI + rc=1 + ACIK KALEM",
                       "A8c KIRMIZI=1 iken hukumsuz kosum ADIYLA GORUNUR",
                       "A8d MUTANT capasi TEK"):
                kayit(ad, None, "KUM KURULAMADI: %s" % kum_sorun)
            return
        taban = os.path.join(td, "kral-sabah-kum.py")
        with open(taban, "w", encoding="utf-8") as f:
            f.write(kaynak)
        print("  A8_KUM arac=%s kopya=%s sabit=%d" % (ARAC, taban, len(A8_KUM_SABITLERI)))

        # --- A8a KONTROL: gercekten temiz gun -> OLCULMUS SIFIR, rc=0
        rcA, satirA, _ = _a8_kos(taban, gh_saglikli, spec_dizin)
        kayit("A8a KONTROL temiz gun: OK + ADET=0 + rc=0",
              rcA == 0 and _alan(satirA, "CI_HUKUM") == "OK"
              and _alan(satirA, "KIRMIZI") == "0",
              "rc=%d CI_HUKUM=%s KIRMIZI=%s" % (
                  rcA, _alan(satirA, "CI_HUKUM"), _alan(satirA, "KIRMIZI")))

        # --- A8b TABAN: kapanmis kirmizi YOK ama bir kosum SURUYOR
        rcB, satirB, _ = _a8_kos(taban, gh_suren, spec_dizin)
        spec_yolu = os.path.join(spec_dizin, os.path.basename(bugunun_spec_yolu()))
        govde = ""
        if os.path.isfile(spec_yolu):
            with open(spec_yolu, encoding="utf-8") as f:
                govde = f.read()
        kalem_var = "CI-OLCULEMEDI" in govde
        kayit("A8b SUREN KOSUM yesil sayilmaz -> OLCULEMEDI + rc=1 + ACIK KALEM",
              rcB >= 1 and _alan(satirB, "CI_HUKUM") == "OLCULEMEDI"
              and _alan(satirB, "KIRMIZI") == "OLCULEMEDI" and kalem_var,
              "rc=%d CI_HUKUM=%s KIRMIZI=%s CI-OLCULEMEDI_kalemi=%d" % (
                  rcB, _alan(satirB, "CI_HUKUM"), _alan(satirB, "KIRMIZI"), int(kalem_var)))

        # --- A8c KIRMIZI VARKEN hukumsuz YUTULMAZ (adet'e girmez, ama GORUNUR)
        rcC, satirC, _ = _a8_kos(taban, gh_karma, spec_dizin)
        govde_c = ""
        if os.path.isfile(spec_yolu):
            with open(spec_yolu, encoding="utf-8") as f:
                govde_c = f.read()
        gorunur = "HÜKMÜ OLMAYAN" in govde_c and "Nöbet şeridi (SERIT B)" in govde_c
        kayit("A8c KIRMIZI=1 iken hukumsuz kosum ADIYLA GORUNUR",
              _alan(satirC, "CI_HUKUM") == "OK" and _alan(satirC, "KIRMIZI") == "1"
              and gorunur,
              "rc=%d CI_HUKUM=%s KIRMIZI=%s hukumsuz_gorunur=%d" % (
                  rcC, _alan(satirC, "CI_HUKUM"), _alan(satirC, "KIRMIZI"), int(gorunur)))

        # --- A8d/A8e MUTANT: ucuncu kova SOKULUNCE A8b YESILE DONMELI
        #     (kaynak = KUMLU kopya; taban ile tek fark A8 capasi)
        adetler = [kaynak.count(capa) for capa, _y in A8_CAPALAR]
        if adetler != [1] * len(A8_CAPALAR):
            kayit("A8d MUTANT capasi TEK", False,
                  "capa_adetleri=%s (hepsi 1 bekleniyor) -> mutant KOSTURULAMADI" % adetler)
            kayit("A8e MUTANT A8b fiksturunu YESILE DONDURUR", None, "capa yok")
            kayit("A8f MUTANT KONTROL DEGISMEDI", None, "capa yok")
            return
        kayit("A8d MUTANT capasi TEK", True, "capa_adetleri=%s" % adetler)

        mutant = os.path.join(td, "kral-sabah-mutant-k356.py")
        for capa, yama in A8_CAPALAR:
            kaynak = kaynak.replace(capa, yama, 1)
        with open(mutant, "w", encoding="utf-8") as f:
            f.write(kaynak)

        rcM, satirM, ciktiM = _a8_kos(mutant, gh_suren, spec_dizin)
        kayit("A8e MUTANT A8b fiksturunu YESILE DONDURUR (hedef-kol atifli)",
              rcB >= 1 and rcM == 0 and _alan(satirM, "CI_HUKUM") == "OK"
              and _alan(satirM, "KIRMIZI") == "0",
              "taban rc=%d/%s | mutant rc=%d CI_HUKUM=%s KIRMIZI=%s" % (
                  rcB, _alan(satirB, "CI_HUKUM"), rcM,
                  _alan(satirM, "CI_HUKUM"), _alan(satirM, "KIRMIZI")))

        rcMK, satirMK, _ = _a8_kos(mutant, gh_saglikli, spec_dizin)
        kayit("A8f MUTANT KONTROL (temiz gun) DEGISMEDI",
              rcMK == rcA == 0 and _alan(satirMK, "KIRMIZI") == _alan(satirA, "KIRMIZI"),
              "kontrol taban rc=%d KIRMIZI=%s | mutant rc=%d KIRMIZI=%s" % (
                  rcA, _alan(satirA, "KIRMIZI"), rcMK, _alan(satirMK, "KIRMIZI")))


# --------------------------------------------------------------------- A9
# A9 — TAVAN FRENI (kayipsiz kirpma). Cip: KraL-TamirciTavan-10Eyl.
#
# 🔴 NEDEN A9-0 BIR "ALTIN DOSYA" KULLANMIYOR: onarim oncesi ciktiyi diske
# donduran bir altin fikstur, BUGUNUN canli girdisini (52 kalem / 67 dal / o anki
# DEVAM) icine gomer. Yarin defter degisince altin bayatlar ve A9-0 KRONIK
# KIRMIZI yanar — arizanin adi "davranis bozuldu" sanilir, oysa bayat olan
# FIKSTURDUR ([[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]] sinifi).
# Ustelik olculdu (10 Eyl): `_motor_raporu_bolumu` CANLI jeton sayaclarini okur;
# onbellek OLMADAN iki ardisik kosumun metni KENDILIGINDEN farkliydi — ham md5
# zaten kararsizdi. Bu yuzden kalici kol BAYATLAMAYAN bir DEGISMEZ olcer:
# sinir verilmezse (a) isaretci blogu YOK, (b) her kalem ve her dal render
# EDILMIS, (c) DEVAM blogu tam. Onarim turundaki tek seferlik md5 esitligi
# mimarin kapanis raporunda sayiyla durur.

A9_TAVAN = 28000
A9_KOLLARI = ("A9-S SABIT", "A9-0 DAVRANIS KORUNDU", "A9-1 BUGUNUN GIRDISI",
              "A9-2 MUTANT 200/200", "A9-3 MUTANT 1000/1000",
              "A9-4 MUTANT TEK DEV MADDE", "A9-5 KAYIPSIZLIK",
              "A9-6 ISARETCI BASTA", "A9-7 SON EMNIYET KOLU",
              "A9-8 UZUN EK YOLU", "A9-NEG FRENSIZ MUTANT")


def _a9_arac():
    """kral-sabah.py'yi modul olarak yukler (dosyada zaten kullanilan desen)."""
    spec = importlib.util.spec_from_file_location("kral_sabah_a9", ARAC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["kral_sabah_a9"] = mod
    spec.loader.exec_module(mod)
    return mod


def _a9_kalem(i):
    return {
        "id": "K%04d" % i,
        "durum": "ACIK",
        "is": "sentetik kalem %d — " % i + ("olcum kolu civilenecek " * 8),
        "kimden": "A9",
        "kanit": "kanit sutunu %d " % i + ("bagimsiz kosum " * 4),
    }


def _a9_dal(i):
    return "claude/sentetik-dal-%04d-uzun-ad-parcasi" % i


def _a9_okunabilir():
    return {"kutu": True, "kalemler": True, "devam": True, "gh": True, "git": True}


def _a9_uret_fabrika(ks, kalemler, dallar, devam_blok, ek_yolu):
    """`tavana_indir`'in bekledigi uret(sinir_kalem, sinir_dal, sinir_devam_kar)."""
    dal_blok = "\n".join("- " + d for d in dallar) if dallar else "Main disi dal YOK."
    kutu_blok = "Son 24 saatte kutuya yeni blok DUSMEMIS."

    def uret(sinir_kalem, sinir_dal, sinir_devam_kar):
        return ks.build_spec(
            dt.date.today(), kalemler, "CI temiz.", dal_blok, kutu_blok, devam_blok,
            0, len(dallar), 0, _a9_okunabilir(), ci_hukum="OK", gh_kaynak="-",
            dallar=dallar, sinir_kalem=sinir_kalem, sinir_dal=sinir_dal,
            sinir_devam_kar=sinir_devam_kar, ek_yolu=ek_yolu)

    return uret


def _a9_mutant(ks, ek_yolu, kalem_n, dal_n, devam_kar, dev_madde=False):
    """Sentetik girdiden (kalemler, dallar, tam, metin, ek, olcum, uret) uretir."""
    if dev_madde:
        k = _a9_kalem(1)
        k["is"] = "D" * 200000
        kalemler = [k]
    else:
        kalemler = [_a9_kalem(i) for i in range(1, kalem_n + 1)]
    dallar = [_a9_dal(i) for i in range(1, dal_n + 1)]
    devam_blok = ("devam satiri uzun bir kuyruk tasiyor " * (devam_kar // 40 + 1))
    uret = _a9_uret_fabrika(ks, kalemler, dallar, devam_blok, ek_yolu)
    tam = uret(None, None, None)
    metin, ek_metin, olcum = ks.tavana_indir(uret, tam, ek_yolu, tavan=A9_TAVAN)
    return kalemler, dallar, tam, metin, ek_metin, olcum, uret


def _a9_hepsini_dusur(gecti, ayrinti):
    for ad in A9_KOLLARI:
        kayit(ad, gecti, ayrinti)


def a9_tavan_freni():
    baslik("A9 — TAVAN FRENI: panel 32.000 karakterini KAYIPSIZ kirpma")

    try:
        ks = _a9_arac()
    except Exception as hata:
        _a9_hepsini_dusur(None, "arac yuklenemedi: %s: %s" % (
            type(hata).__name__, str(hata)[:80]))
        return

    # Fren KURULMAMISSA kollar OLCULEMEDI degil KIRMIZI yanar: eksik fren, olcum
    # arizasi degil URUN arizasidir.
    for gerek in ("tavana_indir", "SPEC_TAVANI"):
        if not hasattr(ks, gerek):
            _a9_hepsini_dusur(False, "arac `%s` TASIMIYOR (tavan freni kurulmamis)" % gerek)
            return

    kayit("A9-S SABIT: SPEC_TAVANI karakter tavani", ks.SPEC_TAVANI == A9_TAVAN,
          "SPEC_TAVANI=%s beklenen=%d" % (ks.SPEC_TAVANI, A9_TAVAN))

    with tempfile.TemporaryDirectory(prefix="sabah-kabul-a9-") as td:
        ek_yolu = os.path.join(td, "KraL-Tamirci-A9-TAM.md")

        # ---------- A9-0: SINIR YOKSA KIRPMA YOK (bayatlamayan degismez)
        kalemler = [_a9_kalem(i) for i in range(1, 13)]
        dallar = [_a9_dal(i) for i in range(1, 9)]
        devam_blok = "devam satiri\n" * 12
        uret0 = _a9_uret_fabrika(ks, kalemler, dallar, devam_blok, ek_yolu)
        sinirsiz = uret0(None, None, None)
        kimlik_hepsi = all(k["id"] in sinirsiz for k in kalemler)
        dal_hepsi = all(d in sinirsiz for d in dallar)
        devam_tam = devam_blok.strip() in sinirsiz
        isaretci_yok = ("TAVAN FRENI ETKIN" not in sinirsiz
                        and "TAVAN FRENİ ETKİN" not in sinirsiz)
        kayit("A9-0 DAVRANIS KORUNDU (sinir yok -> kirpma yok)",
              kimlik_hepsi and dal_hepsi and devam_tam and isaretci_yok,
              "kalem_hepsi=%s dal_hepsi=%s devam_tam=%s isaretci_yok=%s kar=%d" % (
                  kimlik_hepsi, dal_hepsi, devam_tam, isaretci_yok, len(sinirsiz)))

        # ---------- A9-1: BUGUNUN GERCEK GIRDISI
        try:
            kutu_txt = ks.oku_yol(ks.KUTU)
            kalem_txt = ks.oku_yol(ks.KALEMLER)
            devam_txt = ks.oku_yol(ks.DEVAM)
            g_kalemler, _ = ks.acik_kalemleri_topla(kalem_txt or "")
            g_dal = ks.merge_kuyrugu()
            g_dallar = g_dal[2] if len(g_dal) >= 3 else []
            g_devam = ks.devam_ozet(devam_txt)
            g_kutu, g_kutu_n = ks.kutuda_yeni(kutu_txt)

            def uret1(sk, sd, sdk):
                return ks.build_spec(
                    dt.date.today(), g_kalemler, "CI temiz.", g_dal[0], g_kutu, g_devam,
                    0, g_dal[1], g_kutu_n, _a9_okunabilir(), ci_hukum="OK",
                    gh_kaynak="-", dallar=g_dallar, sinir_kalem=sk, sinir_dal=sd,
                    sinir_devam_kar=sdk, ek_yolu=ek_yolu)

            tam1 = uret1(None, None, None)
            m1, _, o1 = ks.tavana_indir(uret1, tam1, ek_yolu, tavan=A9_TAVAN)
            kayit("A9-1 BUGUNUN GIRDISI <= 28000", len(m1) <= A9_TAVAN,
                  "kalem=%d dal=%d tam=%d -> teslim=%d tavan=%d" % (
                      len(g_kalemler), len(g_dallar), len(tam1), len(m1), A9_TAVAN))
        except Exception as hata:
            kayit("A9-1 BUGUNUN GIRDISI <= 28000", None,
                  "canli girdi okunamadi: %s: %s" % (type(hata).__name__, str(hata)[:80]))

        # ---------- A9-2/3/4: MUTANTLAR (+ A9-NEG sayimi ayni turda)
        mutantlar = (
            ("A9-2 MUTANT 200/200", 200, 200, 4000, False),
            ("A9-3 MUTANT 1000/1000", 1000, 1000, 4000, False),
            ("A9-4 MUTANT TEK DEV MADDE", 1, 1, 400, True),
        )
        frensiz_asan = 0
        a9_2 = None
        for ad, kn, dn, dk, dev in mutantlar:
            kalemlerM, dallarM, tamM, metinM, ekM, olcumM, uretM = _a9_mutant(
                ks, ek_yolu, kn, dn, dk, dev)
            # 🔴 A9-4'te `son_emniyet` SART KOSULMAZ — olculdu (10 Eyl): merdivenin
            # son basamagi (0,0,200) dev maddeyi TAMAMEN dusurur, metin tavan altina
            # iner ve son emniyete GEREK KALMAZ. Bu, frenin dogru calistigidir.
            # Son emniyet kolu ayri bir kolda (A9-7) ATESLENIR ve orada olculur;
            # burada sart kosmak, calisan freni KIRMIZI yakardi.
            gecti = len(metinM) <= A9_TAVAN
            kayit(ad, gecti, "tam=%d -> teslim=%d tavan=%d son_emniyet=%s" % (
                len(tamM), len(metinM), A9_TAVAN, olcumM.get("son_emniyet")))
            # A9-NEG: AYNI mutant, fren DEVRE DISI -> tavani ASMALI
            mN, _, _ = ks.tavana_indir(uretM, tamM, ek_yolu, tavan=10 ** 9)
            if len(mN) > A9_TAVAN:
                frensiz_asan += 1
            if a9_2 is None:
                a9_2 = (kalemlerM, dallarM, tamM, metinM, ekM, olcumM)

        # ---------- A9-5: KAYIPSIZLIK (A9-2 uzerinden)
        if a9_2 is None:
            kayit("A9-5 KAYIPSIZLIK", None, "A9-2 kosulamadi")
            kayit("A9-6 ISARETCI BASTA", None, "A9-2 kosulamadi")
        else:
            kalemlerM, dallarM, tamM, metinM, ekM, olcumM = a9_2
            if ekM is None:
                kayit("A9-5 KAYIPSIZLIK", False,
                      "kirpma yapildi ama ek metin URETILMEDI (veri KAYBI)")
            else:
                with open(ek_yolu, "w", encoding="utf-8") as f:
                    f.write(ekM)
                var = os.path.isfile(ek_yolu)
                ek_satir = ekM.count("\n") + 1
                sk = olcumM.get("sinir_kalem")
                render_kalem = len(kalemlerM) if sk is None else min(sk, len(kalemlerM))
                kirpilan = len(kalemlerM) - render_kalem
                eksik = [k["id"] for k in kalemlerM if k["id"] not in ekM]
                birebir = (ekM == tamM)   # KAYIPSIZ = ek, tam metnin BIREBIR kendisi
                kayit("A9-5 KAYIPSIZLIK (ek dosya + kimlik eksigi 0)",
                      var and birebir and len(eksik) == 0 and ek_satir >= kirpilan,
                      "ek=VAR birebir=%s ek_satir=%d kirpilan_madde=%d kimlik_eksik=%d"
                      % (birebir, ek_satir, kirpilan, len(eksik)))

            # ---------- A9-6: ISARETCI BASTA
            i_isaret = -1
            for aday in ("TAVAN FRENİ ETKİN", "TAVAN FRENI ETKIN"):
                if aday in metinM:
                    i_isaret = metinM.index(aday)
                    break
            i_ci = metinM.find("## BUGÜNÜN KIRMIZILARI")
            if i_ci < 0:
                i_ci = metinM.find("## BUGUNUN KIRMIZILARI")
            kayit("A9-6 ISARETCI BASTA (CI basligindan ONCE)",
                  i_isaret >= 0 and i_ci >= 0 and i_isaret < i_ci,
                  "isaretci_indeks=%d ci_indeks=%d" % (i_isaret, i_ci))

        # ---------- A9-7: SON EMNIYET KOLU OLU KOD DEGIL
        # Merdiven YALNIZ kalem/dal/devam'i kisitlar; `kirmizi_blok` her basamakta
        # AYNEN render edilir. Tek basina tavani asan bir kirmizi_blok merdiveni
        # bastan sona tuketir ve SON EMNIYETI atesler. Bu kol olmadan, "girdi ne
        # olursa olsun <= tavan" KOSULSUZ garantisi HIC kosulmamis olurdu.
        dev_kirmizi = "K" * 120000

        def uret7(sk, sd, sdk):
            return ks.build_spec(
                dt.date.today(), [], dev_kirmizi, "dal yok", "kutu yok", "devam yok",
                0, 0, 0, _a9_okunabilir(), ci_hukum="OK", gh_kaynak="-",
                dallar=[], sinir_kalem=sk, sinir_dal=sd, sinir_devam_kar=sdk,
                ek_yolu=ek_yolu)

        tam7 = uret7(None, None, None)
        m7, ek7, o7 = ks.tavana_indir(uret7, tam7, ek_yolu, tavan=A9_TAVAN)
        kayit("A9-7 SON EMNIYET KOLU ATESLENIR (olu kod DEGIL)",
              len(m7) <= A9_TAVAN and o7.get("son_emniyet") is True and ek7 == tam7,
              "tam=%d -> teslim=%d son_emniyet=%s ek_birebir=%s kuyruk_notu=%s" % (
                  len(tam7), len(m7), o7.get("son_emniyet"), ek7 == tam7,
                  "KUYRUK KESİLDİ" in m7))

        # ---------- A9-8: ISARETCI PAYI SABIT DEGIL, OLCULMUS
        # Isaretci blogu `ek_yolu`'nu ICINDE tasir; yol uzarsa blok uzar. Sabit
        # bir emniyet payi (or. `tavan - 240`) bu vakada OLUR: uzun yol payi
        # tasirir ve fonksiyon tavani ASAN metin dondurur. Bu kol, payin
        # OLCULMUS oldugunu kanitlar — A9-7 ile ayni girdi, YALNIZ yol uzun.
        uzun_yol = os.path.join(td, "U" * 280 + ".md")

        def uret8(sk, sd, sdk):
            return ks.build_spec(
                dt.date.today(), [], dev_kirmizi, "dal yok", "kutu yok", "devam yok",
                0, 0, 0, _a9_okunabilir(), ci_hukum="OK", gh_kaynak="-",
                dallar=[], sinir_kalem=sk, sinir_dal=sd, sinir_devam_kar=sdk,
                ek_yolu=uzun_yol)

        tam8 = uret8(None, None, None)
        m8, ek8, o8 = ks.tavana_indir(uret8, tam8, uzun_yol, tavan=A9_TAVAN)
        kayit("A9-8 UZUN EK YOLU: pay SABIT degil OLCULMUS",
              len(m8) <= A9_TAVAN and ek8 == tam8,
              "yol_kar=%d tam=%d -> teslim=%d tavan=%d asim=%d" % (
                  len(uzun_yol), len(tam8), len(m8), A9_TAVAN,
                  max(0, len(m8) - A9_TAVAN)))

        # ---------- A9-NEG: FREN YOKSA TEST GECMEMELI
        kayit("A9-NEG FRENSIZ MUTANT KIRMIZI YANAR", frensiz_asan == 3,
              "frensiz_mutant_asti=%d/3 (3 degilse test kendini YANLIS-YESILE boyuyor)"
              % frensiz_asan)


def main(argv=None):
    # 🔴 CAKISMA COZUMU (27 Agu 2026, KraL-DogrulaMerge-27Agu) — BIRLESIM, taraf
    # secimi DEGIL. Iki dal main()'e AYRI birer bayrak ekledi ve bayraklar AYRI
    # yuzey seciyor; birini dusurmek otekinin olcumunu KORLESTIRIRDI:
    #   * `--kurucu` (main, sabah dalindan) -> A7'nin olctugu **kur.py**. Yoksa
    #     dal olculurken ANA CHECKOUT'un kurucusu olculur (sabah dalinin kendi
    #     yan bulgusu; o tur 3 vaka bu yuzden dusmustu).
    #   * `--arac`   (nobet dali)           -> A1/A6'nin olctugu **kral-sabah.py**.
    #     Yoksa daima KURULU KOPYA olculur ve batarya yesili dalin dosyasini
    #     tarif etmez ([[kayipli-damga-korunani-korunmayana-benzetir]] komsusu:
    #     olculen duzlem != onarilan duzlem).
    # Ikisi ayni `args` uzerinde durur, birbirine DOKUNMAZ; bayraksiz davranis
    # her iki eksende de ESKISIYLE ayni kalir.
    global KURUCU_YOLU, ARAC
    ap = argparse.ArgumentParser()
    ap.add_argument("--faz", choices=("on", "tam"), default="tam")
    ap.add_argument("--kurucu", default=None,
                    help="A7'de olculecek kur.py (dal olcumu icin ZORUNLU — "
                         "aksi halde ANA CHECKOUT'un kopyasi olculur)")
    # 🔴 K320 SECICI (16 Eyl 2026): A7 vakasini TEK BASINA kosar.
    # NEDEN: A7'nin onarimi (kur.py `yeni_adedi == 1 -> ZATEN` / `> 1 -> COGALMIS`)
    # main'de DURUYOR ama kabul KOSULAMIYORDU — `--faz tam` A2'de GERCEK kral-sabah.py
    # kosup `~/.claude/cron/tamirci-spec/` yaziyor, `--faz on` ise A1/A6 ile ORTAMA
    # (kurulu kopya, gercek yedek duzlemi) bagli. Ikisi de CI'da ve dal olcumunde
    # KOSULAMAZ hale geliyordu; sonuc: onarim VAR, kabul `OLCULEMEDI`.
    # A7'nin KENDISI zaten hermetiktir: SAHTE CRON dizini (`tempfile` altinda)
    # kurar, kurucuyu orada iki kez kosar, mutanti IZOLE kopyada dener. Secici
    # yalnizca yanindaki ORTAM-bagimli vakalari DISARIDA birakir.
    # 18 Eyl 2026 (`elegant-swanson-2a0319`): A8/A9 CANLIDAN TASINDI. Iki vaka
    # 31 Agu / 10 Eyl'de yalniz `~/.claude/cron/sabah-kabul.py`de yazilmisti
    # (hicbir git nesnesinde yoktu) -> CI onlari HIC kosmuyordu ve `kur.py`
    # KOPYA_AYRISIK ile duruyordu. A8 hermetiktir (enjekte `gh` + gecici spec
    # dizini); A9'un A9-1 kolu CANLI defteri okur, o yuzden A9 CI'ya baglanmaz.
    ap.add_argument("--vaka", choices=("A7", "A8", "A9"), default=None,
                    help="YALNIZ bu vakayi kos (A7: kurucu idempotensi, hermetik "
                         "sahte CRON dizini · A8: ucuncu kova, enjekte gh · A9: "
                         "tavan freni; A1/A6/A2 KOSULMAZ)")
    ap.add_argument("--arac", default=None, metavar="YOL",
                    help="olculecek kral-sabah.py (varsayilan: kurulu kopya "
                         "~/.claude/cron/kral-sabah.py). Dalin KENDI dosyasini "
                         "olcmek icin: --arac tools/sabah-teslim/kral-sabah.py")
    args = ap.parse_args(argv)
    KURUCU_YOLU = args.kurucu
    if args.arac:
        ARAC = os.path.abspath(os.path.expanduser(args.arac))

    print("KraL SABAH RUTINI KABUL BATARYASI — faz=%s" % args.faz)
    print("damga=%s python=%s" % (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), PY))
    # 🔴 OLCULEN YUZEY ADIYLA BASILIR: iki kosumun farki bu satirdan okunur.
    print("OLCULEN_ARAC=%s (%s)" % (
        ARAC, "BAYRAKLA" if args.arac else "VARSAYILAN/kurulu"))
    print("SPEC_DIZINI=%s" % SPEC_DIZINI)

    # 🔴 ARAC SARTI VAKAYA BAGLI (16 Eyl 2026). A7 kurucuyu (`kur.py`) olcer ve
    # sentetik tabanda kosar; A8 `kral-sabah.py` KAYNAGINI `--arac` ile alir.
    # Ikisi de KURULU KOPYAYA (`~/.claude/cron/kral-sabah.py`) muhtac degildir —
    # eski kosulsuz kontrol CI'da rc=2 ile ikisini de olduruyordu.
    if args.vaka != "A7" and not os.path.isfile(ARAC):
        print("HATA: arac YOK -> %s" % ARAC)
        return 2

    if args.vaka == "A7":
        # Hermetik kol: SAHTE CRON dizini + izole mutant kopyasi. Gercek
        # `kral-sabah.py` KOSMAZ, `~/.claude/cron` altina TEK BAYT yazilmaz.
        a7_kurucu_idempotens()
    elif args.vaka == "A8":
        a8_ucuncu_kova()
    elif args.vaka == "A9":
        a9_tavan_freni()
    else:
        a1_ortam()
        # A6/A7 CANLI DUZLEME YAZMAZ (yalniz gecici dizin + salt-okuma) -> her fazda.
        a6_ortam_turetme()
        a7_kurucu_idempotens()
        # A8 CANLI DUZLEME YAZMAZ (gecici spec dizini + enjekte `gh`) -> her fazda.
        a8_ucuncu_kova()
        # A9 CANLI DUZLEME YAZMAZ (build_spec/tavana_indir DOGRUDAN cagrilir, ek
        # dosya gecici dizine yazilir) -> her fazda.
        a9_tavan_freni()
        if args.faz == "tam":
            a2_gercek_kosum()
            a3_a4_sonuc_kolu()
            a5_iki_tur()

    baslik("OZET")
    gecen = sum(1 for _, g, _ in SONUC if g is True)
    dusen = [a for a, g, _ in SONUC if g is False]
    olculemeyen = [a for a, g, _ in SONUC if g is None]
    print("VAKA=%d GECTI=%d DUSTU=%d OLCULEMEDI=%d" % (
        len(SONUC), gecen, len(dusen), len(olculemeyen)))
    if dusen:
        print("DUSEN: %s" % ", ".join(dusen))
    if olculemeyen:
        print("OLCULEMEDI: %s" % ", ".join(olculemeyen))
    print("SABAH_KABUL rc=%d" % (1 if (dusen or olculemeyen) else 0))
    return 1 if (dusen or olculemeyen) else 0


if __name__ == "__main__":
    sys.exit(main())
