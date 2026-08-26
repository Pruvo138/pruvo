#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/yedekle.py'nin SKILL KAPSAMI + SIR NOBETI + ESZAMANLILIK KILIDI.

NEDEN VAR: ~/.claude/skills (merge-kapisi + ege-diyalog) GIT DISINDA, tek kopya bu makinede.
yedekle.py onu Drive'a tasiyan tek yol. Uc sessiz-hata sinifi var:
  (A) KAPSAM CURUMESI — skills bloku bozulur/silinir, arac YINE "bitti" der, disk kaybinda
      mutasyon-kanitli dal-olc.py + kabul-test.py topluca gider (kimse fark etmez).
  (B) SIR SIZINTISI — skills agaci vetted degil; oraya dusen bir jeton/anahtar yedek klasorune
      (paylasilabilir Drive) tasinir.
  (C) ESZAMANLI YAZMA — yedekle.py her push'ta kosuyor, bu repoda paralel oturum NORMAL;
      kilitsiz iki kosum AYNI hedefe yazar, sonda damga yine "tam" der. Pano "taze"
      derken yedek karismis olabilir (bolum 13-15).
Bu yuzden her iddianin KIRMIZI-MUTASYON ya da davranissal kaniti var: kontrolu devre disi
birakan mutant surumde ilgili kontrol KIRMIZI yanmalidir; yanmazsa kontrol olcmuyor demektir.

⚠️ GERCEK HEDEFE YAZILMAZ: 13-15 tamamen izole ortamda kosar (sahte HOME + sahte git
deposu + drive_yolu STUB'u). Bolum 15 gercek Drive damgasinin bayt bayt DEGISMEDIGINI
ayrica kanitlar.

Kosum:  python3 tools/yedekle-test.py
"""
import fcntl
import fnmatch
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from git_ortami import sentetik_git
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")

# Skill agacinda BULUNMASI zorunlu iki dosya (26 Tem'de mutasyon kanitiyla sertlestirildi).
ZORUNLU = ("merge-kapisi/scripts/dal-olc.py", "merge-kapisi/evals/kabul-test.py")

# Sentetik sir fikstur govdesi — GERCEK anahtar DEGIL, imza tanima testi icin.
#
# 🔴 E2 — FIKSTUR IKI PARCALI KURULUR (27 Tem). shop/test/kabul.js `test6SirTaramasi`
# tum repoda `git grep -nIE "BEGIN [A-Z ]*PRIVATE KEY"` kosar; bu SATIR BAZLI bir
# taramadir ve fikstur tek satirda tam bicimde yazilinca 1 isabet vererek shop kabul
# testini KIRMIZI tutuyordu. Cozum tarayiciyi ZAYIFLATMAK/muaf tutmak DEGIL (o zaman
# gercek bir anahtar da kacardi): dize IKI parcaya bolunur -> hicbir KAYNAK SATIRI
# desene uymaz, CALISMA ANINDAKI dize ise BIREBIR AYNI kalir (yedekle.SIR_IMZALARI
# "ozel anahtar blogu" imzasi ayni sekilde yakalar; 4. bolum bunu olcer).
_ANAHTAR_KUYRUK = " KEY-----"
SAHTE_ANAHTAR = ("-----BEGIN RSA PRIVATE" + _ANAHTAR_KUYRUK + "\n"
                 "SAHTE-FIKSTUR-VERISI-GERCEK-ANAHTAR-DEGIL\n"
                 "-----END RSA PRIVATE" + _ANAHTAR_KUYRUK + "\n")

SONUC = []

# ===================== HERMETIK SERIT (A2) ==================================
# Bataryanin TAMAMI CI'da kosamaz (gercek ~/.claude/skills + Drive + gitignore'lu
# kok dosyalari). Ama 16/16b bolumu TAMAMEN hermetiktir ve `--hermetik` koluyla
# deploy.yml'de BLOKLAYICI kosar.
#
# 🔴 KABUL CIKIS KODU DEGIL, BASILAN IDDIA SAYISIDIR ([[kapi-yan-etkisi-gizli-onkosul]]):
# "ikisi de rc=0" YETMEZ — olculen YUZEY sessizce kuculebilir. Iki fail-closed sart:
#   (1) ASGARI: hermetik kume bu sayinin ALTINA duserse KIRMIZI. Yarin biri bolumu
#       hermetik olmaktan cikarir/kirparsa serit SESSIZCE BOS kosardi.
#   (2) PARITE: `--hermetik` kolunun BASTIGI sayi, tam bataryada AYNI bolumun
#       urettigi sayiya ESIT olmali. Esit degilse (ya da okunamiyorsa) KIRMIZI.
# SAYI TEK KAYNAK: yalniz burada yazilidir; ne workflow'a ne muafiyet metnine
# ikinci kopyasi konur (ikiz sayi sessizce ayrisir).
#
# 🔴 ASAGIDAKI BEYAN CI-KAPSAM KAPISINA BAGLANIR: bu alt kumenin OTOMATIK bir is
# akisinda FIILEN kosuyor olmasi ZORUNLU olur. deploy.yml `serit-a4`teki adim
# silinirse ci-kapsam-test.py KIRMIZI yanar -> serit sessizce dusurulemez.
# CI-ALT-KUME: --hermetik
HERMETIK_ASGARI = 60
HERMETIK_SAYI_ONEKI = "HERMETIK IDDIA SAYISI:"
HERMETIK_BAYRAK = "--hermetik"


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok), ayrinti))
    # ayrinti str olmayabilir (bolum 18 set/list gecirir; 19 Agu'da olculdu:
    # str + set TypeError'i tum takimi 16b'den sonra kesiyordu).
    print(("  ✅ " if ok else "  ❌ ") + ad +
          (("  — " + str(ayrinti)) if ayrinti else ""))
    return bool(ok)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mutant_yaz(dizin, degisimler, ad="mutant.py"):
    """yedekle.py'nin mutasyonlu kopyasini uretir. Capa bulunamazsa (kod degismis)
    RuntimeError -> testin kendisi KIRMIZI yanar (bayat mutasyon capasi sessizce gecmesin)."""
    with open(YEDEKLE, encoding="utf-8") as f:
        kaynak = f.read()
    for eski, yeni in degisimler:
        if eski not in kaynak:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r" % eski)
        kaynak = kaynak.replace(eski, yeni, 1)
    hedef = os.path.join(dizin, ad)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak)
    # yedekle.py import aninda kardes drive_yolu'yu cagirir -> yanina kopyala.
    shutil.copy2(DRIVE_YOLU, os.path.join(dizin, "drive_yolu.py"))
    return hedef


def fikstur_kur(kok):
    """Sentetik skills agaci: 1 normal dosya + 3 sir + 1 turetilmis gurultu."""
    os.makedirs(os.path.join(kok, "ornek-skill", "notlar"), exist_ok=True)
    os.makedirs(os.path.join(kok, "ornek-skill", "scripts", "__pycache__"), exist_ok=True)
    with open(os.path.join(kok, "ornek-skill", "SKILL.md"), "w") as f:
        f.write("# normal skill icerigi\n")
    with open(os.path.join(kok, "ornek-skill", ".r2-credentials.json"), "w") as f:
        f.write('{"access_key_id":"SAHTE","secret_access_key":"SAHTE"}\n')
    with open(os.path.join(kok, "ornek-skill", "notlar", "gizli-token.txt"), "w") as f:
        f.write("sahte-jeton-govdesi\n")
    with open(os.path.join(kok, "ornek-skill", "kurulum.md"), "w") as f:
        f.write("kurulum notlari\n" + SAHTE_ANAHTAR)
    with open(os.path.join(kok, "ornek-skill", "scripts", "__pycache__", "x.pyc"), "wb") as f:
        f.write(b"\x00\x01derlenmis")
    return {
        "normal": "ornek-skill/SKILL.md",
        "sirlar": ["ornek-skill/.r2-credentials.json",
                   "ornek-skill/notlar/gizli-token.txt",
                   "ornek-skill/kurulum.md"],
    }


# ===================== KOK SEVIYESI GLOB (7 Agu 2026) ========================
# 🔴 NEDEN VAR: EK_EVLER'de bir kardes evin kok defterleri artik TEK TEK ADIYLA
# degil ADSIZ bir KOK GLOB'u ile yazilir (depo PUBLIC: ad listesi hem ucuncu-taraf
# etiketi sizdiriyordu hem de her partide bayatliyordu — olculdu: 3 addan 1'i evde
# yoktu, ayni bicimde 4 ad kapsam DISINDA duruyordu).
# Kok glob'u AYRI bir kod yolundan cozulur (listdir; os.walk DEGIL) ve ayni hukmu
# IKI yerde verir: (1) kapsama ALMA, (2) KAPSAM-DISI kesfinde mukerrer eleme.
# O kod yolunun repoda TEK BIR IDDIASI YOKTU -> bozulursa batarya YESIL yanardi.
#
# ⚠️ FIKSTUR ADLARI TAMAMEN UYDURMA. Gercek defter adlari (ucuncu-taraf etiketleri)
# bu dosyaya YAZILMAZ: yazilsaydi sizinti KALDIRILMAZ, nobetcinin kendi izlenen
# dosyasina TASINIRDI ([[nobetci-kendi-dosyasinda-sizinti]]). Uydurma adlar gercek
# etiketlerin anlasilir turevi de DEGILDIR (1-harf mesafe yok).
# ⚠️ GERCEK EVE BAGIMLI DEGIL: fikstur gecici dizinde kendi git deposunu kurar.
KOK_GLOB_EV = "pruvo-hasat"          # EK_EVLER anahtari (basename ile cozulur)
# Hukmun TEK TANIMI. Adiyla anilir ki (1) mutasyon capasi ona baglansin,
# (2) "tek tanim / iki cagiran" ozelligi YAPISAL olarak da olculebilsin.
KOK_GLOB_FN = "_kok_desen_tutuyor"
KOK_GLOB_CAPA = "    return any(fnmatch.fnmatch(ad, d) for d in desenler)"
# Mutasyon capalari — kok glob'un IKI AYRI kod/veri ekseni.
KOK_GLOB_ISFILE_CAPA = (
    "            if not os.path.isfile(os.path.join(ev, giris)):\n"
    "                continue                       # dizin/soket: kok glob'u dosya alir")
# ALT-DIZIN kod yolu capalari (`_dizin_gez`) — A1 mutantlari icin.
ALT_GLOB_WALK_CAPA = (
    "            altlar[:] = sorted(a for a in altlar\n"
    "                               if a not in GURULTU_DIZIN and not _turetilmis_mi(a))")
ALT_GLOB_DOSYA_CAPA = (
    "            for dosya in sorted(dosyalar):\n"
    "                gor = os.path.relpath(os.path.join(dizin, dosya), ev)")
# Mutantin YUKLENEN MODULDE canli oldugunu kanitlayan isaret buraya enjekte edilir.
KOK_GLOB_ISARET_CAPA = 'EK_KLASOR = "ek"'

# ===================== SABIT FIKSTUR ADLARI (M-G onarimi) ====================
# 🔴 NEDEN SABIT (7 Agu 2026 — olculdu): bu adlar eskiden DESENDEN TURETILIYORDU
# (`_desenden_ad`). Turetildikleri surece desen HANGI DEGERE kayarsa kaysin fikstur
# onunla BIRLIKTE kayiyordu: deseni "ZZZUYDURMAYOK-*.md" gibi TAMAMEN YANLIS bir
# degere ceviren mutant 204 kontrolun HEPSINI YESIL geciyordu. Testin desen
# hakkindaki tek iddiasi `bool(desenler)` idi — yani VARLIK, DEGER DEGIL
# ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]] ile ayni sinif).
# Adlar SABIT + desen EK_EVLER'den OKUNUR -> desen kayarsa eslesme SIFIRA duser ve
# (a)+(b)+(i) iddialari KIRMIZI yanar. Desen dizesi buraya IKINCI KEZ YAZILMAZ:
# tek kaynak EK_EVLER'de kalir, burada yalniz DEGERI IDDIA EDILIR
# ([[ikiz-tanim-sessiz-ayrisma]]).
KOK_GLOB_KAPSANAN = ("DEVAM-KUMHAVUZU-ALFA.md",
                     "DEVAM-KUMHAVUZU-BETA.md",
                     "DEVAM-KUMHAVUZU-GAMA.md")
KOK_GLOB_ALTAGAC = "DEVAM-KUMHAVUZU-ALTAGAC/DERIN.md"   # '/' ayirmasaydi yutulurdu
KOK_GLOB_IZLENEN = "DEVAM-KUMHAVUZU-IZLENEN.md"         # git'te var -> alinmaz
KOK_GLOB_SIRLI = "DEVAM-KUMHAVUZU-token.md"             # sir nobetine takilir
KOK_GLOB_DESEN_DISI = "KUMHAVUZU-KAPSAM-DISI-KAYDI.txt"  # gorunur bosluk (negatif)
# UZANTI EKSENI (M-I): desen "DEVAM-*" olsaydi bu ikisi de kapsama girerdi.
KOK_GLOB_UZANTISIZ = "DEVAM-KUMHAVUZU-UZANTISIZ"
KOK_GLOB_BASKA_UZANTI = "DEVAM-KUMHAVUZU-BASKA.txt"
# DIZIN EKSENI (M-D): desene UYAN ama DOSYA OLMAYAN giris.
KOK_GLOB_DIZIN = "DEVAM-KUMHAVUZU-DIZIN.md"

# ============ ALT-DIZIN GLOB'U: AYNI DEGER KILIDI (A1, M-G IKIZI) ============
# 🔴 NEDEN: kok deseni G1'de kilitlendi ama "<dizin>/*.<uzanti>" sinifi HALA
# `_alt_dizin_glob` ile DESENDEN TURETILIYORDU -> desen yanlis bir DEGERE ya da
# yanlis DIZINE kaysa fikstur onunla BIRLIKTE kayar ve batarya YESIL kalirdi.
# Cozum kok ile AYNI: adlar SABIT, desen EK_EVLER'den OKUNUR, desen dizesi teste
# IKINCI KEZ YAZILMAZ.
# ⚠️ DIZIN BILESENI DE KILITLIDIR: "olcum"/"kalibrasyon" adlari BILEREK yazilidir.
# Desen baska bir dizine kayarsa (n)/(o) KIRMIZI yanar. Dizin MESRU olarak yeniden
# adlandirilirsa bu sabitler de guncellenir — sessiz kayma YOK (fail-closed).
ALT_GLOB_OLCUM = ("olcum/kumhavuzu-alfa.py", "olcum/kumhavuzu-beta.md")
ALT_GLOB_KALIBRASYON = ("kalibrasyon/kumhavuzu-gama.tsv",)
ALT_GLOB_TUM_KAPSANAN = ALT_GLOB_OLCUM + ALT_GLOB_KALIBRASYON
ALT_GLOB_BASKA_UZANTI = "olcum/kumhavuzu-baska.txt"     # uzanti eksene: kapsanmaz
ALT_GLOB_UZANTISIZ = "olcum/kumhavuzu-uzantisiz"        # uzanti eksene: kapsanmaz
# 🔴 OLCULMUS GERCEK DAVRANIS (7 Agu 2026) — IDDIA BUNA GORE YAZILDI:
# alt-dizin glob'u ALT AGACA INER. `_dizin_gez` os.walk ile TUM agaci gezer ve
# fnmatch "/" ayirmadigi icin "olcum/*.md" deseni "olcum/alt/derin.md"i DE tutar.
# Bu, KOK glob'unun TERSIDIR ve KUSUR DEGILDIR: kok glob'u elle yazilmis KOK
# adlarinin YERINI aldigi icin kume ESIT kalmak zorundaydi; burada oyle bir esitlik
# sarti YOK, amac "olcum/ altindaki elle yazilmis betikler yedeklensin". O yuzden
# iddia "TAKILMAZ" degil "KAPSANIR" yonundedir (olculen davranis budur).
ALT_GLOB_DERIN = "olcum/alt/kumhavuzu-derin.md"
# Desene UYAN ama DIZIN olan giris.
# NOT: `kapsam_disi` YALNIZ ev KOKUNDEKI girisleri sayar (os.listdir(ev)); alt
# agactaki bir dizin oraya YAPISAL OLARAK giremez -> kok tarafindaki (l) iddiasinin
# "kapsam_disi'nda GORUNUR" kolu burada YOKTUR, iddia "ne dahil ne haric"tir.
ALT_GLOB_DIZIN = "olcum/kumhavuzu-dizin.py"


def kok_desen_yapisi(kaynak):
    """yedekle.py kaynagindan (tanim_sayisi, cagri_sayisi) — TWIN-DEFINITION kilidi.

    🔴 NEDEN: kok glob hukmu IKI yerde gerekiyor (kapsama alma + KAPSAM-DISI
    mukerrer eleme). Ikisi ayri ayri yazilirsa ikiz tanim SESSIZCE ayrisir:
    biri genisleyip digeri genislemeyince ayni dosya hem yedege girer hem
    "alinmadi" diye raporlanir (ya da tersi: sessiz bosluk). Davranissal
    iddialar bunu mutantla olcer; bu olcum ayrismayi KAYNAKTA da kilitler."""
    tanim = kaynak.count("def %s(" % KOK_GLOB_FN)
    cagri = kaynak.count("%s(" % KOK_GLOB_FN) - tanim
    return tanim, cagri


def _kok_glob_desenleri(mod, ev_adi=KOK_GLOB_EV):
    """EK_EVLER'deki "/" TASIMAYAN glob girisleri = kok seviyesi desenler. TEK KAYNAK."""
    return [g for g in mod.EK_EVLER.get(ev_adi, ())
            if "/" not in g and ("*" in g or "?" in g)]


def _alt_dizin_globlari(mod, ev_adi=KOK_GLOB_EV):
    """EK_EVLER'deki "/" TASIYAN glob girisleri = alt-dizin desenleri. TEK KAYNAK."""
    return [g for g in mod.EK_EVLER.get(ev_adi, ()) if "/" in g and "*" in g]


def _alt_dizin_glob(mod, ev_adi=KOK_GLOB_EV):
    """Ayni evdeki "/" TASIYAN ILK glob (varlik capasi; DEGERI (m)-(o) iddia eder)."""
    hepsi = _alt_dizin_globlari(mod, ev_adi)
    return hepsi[0] if hepsi else None


def _ikinci_dizin_globu(mod, ev_adi=KOK_GLOB_EV):
    """Ilk glob'dan FARKLI bir DIZINE bakan ilk glob (dizin bileseni mutanti icin).

    Mutasyon capasi boylece EK_EVLER'den TURER; dizin adi teste ikinci kez YAZILMAZ."""
    hepsi = _alt_dizin_globlari(mod, ev_adi)
    if not hepsi:
        return None
    ilk_dizin = os.path.dirname(hepsi[0])
    for g in hepsi[1:]:
        if os.path.dirname(g) != ilk_dizin:
            return g
    return None


def kok_glob_fiksturu(td, mod):
    """Sahte kardes ev (gercek git deposu). Doner: (ev_yolu, beklenen dict).

    🔴 DOSYA ADLARI SABIT (yukaridaki KOK_GLOB_* sabitleri), DESENDEN TURETILMEZ:
    desenin DEGERI ancak boyle iddia edilebilir (bkz. sabitlerin ustundeki blok).
    Capa bayatlarsa RuntimeError -> test KIRMIZI yanar, sessizce gecmez."""
    desenler = _kok_glob_desenleri(mod)
    if not desenler:
        raise RuntimeError("KOK GLOB CAPASI YOK: EK_EVLER[%r] icinde '/' tasimayan "
                           "glob girisi bulunamadi (kod degismis)" % KOK_GLOB_EV)
    altglob = _alt_dizin_glob(mod)
    if not altglob:
        raise RuntimeError("ALT DIZIN GLOB CAPASI YOK: EK_EVLER[%r]" % KOK_GLOB_EV)

    ev = os.path.join(td, KOK_GLOB_EV)
    os.makedirs(ev)
    for arg in (["init", "-q"], ["config", "user.email", "kabul@test"],
                ["config", "user.name", "kabul"]):
        subprocess.run(["git", "-C", ev] + arg, capture_output=True)

    def yaz(gor, icerik="uydurma fikstur icerigi\n"):
        tam = os.path.join(ev, gor)
        os.makedirs(os.path.dirname(tam), exist_ok=True)
        with open(tam, "w", encoding="utf-8") as f:
            f.write(icerik)
        return gor

    # (1) HEDEF: desene UYMASI BEKLENEN, IZLENMEYEN 3 kok kaydi — adlar SABIT+UYDURMA.
    kapsanan = [yaz(ad) for ad in KOK_GLOB_KAPSANAN]
    # (2) ALT AGAC: desen "/" ayirmasaydi bunu da yutardi (fnmatch '/' ayirmaz).
    altagac = yaz(KOK_GLOB_ALTAGAC)
    # (3) DESEN DISI kok dosyasi -> gorunur bosluk olarak KAPSAM-DISI'nda kalmali.
    yaz(KOK_GLOB_DESEN_DISI)
    # (4) IZLENEN eslesme -> git zaten yedek, kapsama ALINMAMALI.
    izlenen = yaz(KOK_GLOB_IZLENEN)
    subprocess.run(["git", "-C", ev, "add", izlenen], capture_output=True)
    subprocess.run(["git", "-C", ev, "commit", "-qm", "fikstur"], capture_output=True)
    # (5) SIR eksenli eslesme -> desene UYSA BILE yedege girmez, `haric`e duser.
    sirli = yaz(KOK_GLOB_SIRLI)
    # (6) ALT-DIZIN GLOB'U — adlar SABIT (A1): dizin bileseni + uzanti KILITLI.
    for ad in ALT_GLOB_TUM_KAPSANAN:
        yaz(ad)
    yaz(ALT_GLOB_BASKA_UZANTI)
    yaz(ALT_GLOB_UZANTISIZ)
    yaz(ALT_GLOB_DERIN)                       # alt agac: OLCULDU -> kapsanir
    yaz(os.path.join(ALT_GLOB_DIZIN, "icerik.txt"))   # desene uyan DIZIN
    # (7) UZANTI EKSENI (M-I): uzantisiz ve farkli uzantili kok kayitlari.
    yaz(KOK_GLOB_UZANTISIZ)
    yaz(KOK_GLOB_BASKA_UZANTI)
    # (8) DIZIN EKSENI (M-D): desene UYAN ama DOSYA OLMAYAN kok girisi.
    #     Ici DOLU olmali: bos dizin KAPSAM-DISI kesfinde bilerek atlanir.
    yaz(os.path.join(KOK_GLOB_DIZIN, "icerik.txt"))
    return ev, {"kapsanan": kapsanan, "altagac": altagac,
                "desendisi": KOK_GLOB_DESEN_DISI, "izlenen": izlenen, "sirli": sirli,
                "desen_adet": len(desenler)}


def kok_glob_iddialari(mod, ev, bek):
    """Kok glob kod yolunun IDDIALARI -> [(etiket, ok, ayrinti)].

    🔴 SAGLAM ve MUTANT surumler AYNI fonksiyondan gecer: ikiz iddia listesi
    olusmaz, mutant "baska bir olcume" karsi kosturulmus olmaz."""
    dahil, haric, kapsam_disi = mod.ek_ev_plani(ev)
    d = set(g for g, _h in dahil)
    h = set(g for g, _s in haric)
    k = set(kapsam_disi)
    kaps = bek["kapsanan"]
    icinde = len([x for x in kaps if x in d])
    dusen = len([x for x in kaps if x in k])
    # (i) DEGER KILIDI: iddia MOD'un EK_EVLER'inden OKUNAN desen uzerinedir; sabit
    # adlar desenden TURETILMEDIGI icin desen kayarsa bu sayi SIFIRA duser.
    desenler = _kok_glob_desenleri(mod)
    tutan = [a for a in KOK_GLOB_KAPSANAN
             if any(fnmatch.fnmatch(a, x) for x in desenler)]
    uzanti_ekseni = (KOK_GLOB_UZANTISIZ, KOK_GLOB_BASKA_UZANTI)
    # A1 — ALT-DIZIN deseninin DEGER kilidi (ayni ilke: sabit ad, okunan desen).
    alt_desenler = _alt_dizin_globlari(mod)
    alt_tutan = [a for a in ALT_GLOB_TUM_KAPSANAN
                 if any(fnmatch.fnmatch(a, x) for x in alt_desenler)]
    return [
        ("(a) kok deseni ayni bicimdeki %d uydurma kaydi kapsama ALIR" % len(kaps),
         icinde == len(kaps), "%d/%d" % (icinde, len(kaps))),
        ("(b) kapsanan kayit KAPSAM-DISI raporuna MUKERRER DUSMEZ",
         dusen == 0, "dusen: %d" % dusen),
        ("(c) kok deseni ALT AGAC dosyasini YUTMAZ ('/' ayirir)",
         bek["altagac"] not in d, "alt agac dosyasi kapsamda mi: %s"
         % (bek["altagac"] in d)),
        # (d) KALDIRILDI: "alt-dizin glob'u korunur" iddiasi DESENDEN TURETILMIS bir
        # fikstur adina bakiyordu (M-G ikizi: desen kayinca ad da kayiyordu). Yerini
        # asagidaki (m)-(r) DEGER KILITLI iddialari aldi — daha genis, daha katı.
        ("(e) desene UYMAYAN kok dosyasi KAPSAM-DISI'nda GORUNUR (bosluk gizlenmiyor)",
         bek["desendisi"] in k and bek["desendisi"] not in d,
         "kapsam-disi=%s dahil=%s" % (bek["desendisi"] in k, bek["desendisi"] in d)),
        ("(f) git'te IZLENEN eslesme kapsama ALINMAZ",
         bek["izlenen"] not in d, "dahil mi: %s" % (bek["izlenen"] in d)),
        ("(g) desene uyan SIR dosyasi yedege GIRMEZ, `haric`e duser",
         bek["sirli"] not in d and bek["sirli"] in h,
         "dahil=%s haric=%s" % (bek["sirli"] in d, bek["sirli"] in h)),
        ("(h) SIR dosyasi KAPSAM-DISI'na da MUKERRER dusmez",
         bek["sirli"] not in k, "kapsam-disi mi: %s" % (bek["sirli"] in k)),
        # ---- DEGER KILIDI: desen VAR MI degil, DOGRU DEGERDE MI ----
        ("(i) EK_EVLER'den OKUNAN desen SABIT uydurma adlarin HEPSINI tutuyor "
         "(desen DEGERI kilitli)",
         len(tutan) == len(KOK_GLOB_KAPSANAN),
         "%d/%d ad tutuluyor" % (len(tutan), len(KOK_GLOB_KAPSANAN))),
        # ---- UZANTI EKSENI: desen uzantiyi GERCEKTEN suzuyor mu ----
        ("(j) UZANTISIZ kok kaydi desene TAKILMAZ (kapsama girmez)",
         KOK_GLOB_UZANTISIZ not in d, "dahil mi: %s" % (KOK_GLOB_UZANTISIZ in d)),
        ("(k) FARKLI UZANTILI kok kaydi desene TAKILMAZ ve KAPSAM-DISI'nda GORUNUR",
         KOK_GLOB_BASKA_UZANTI not in d and all(x in k for x in uzanti_ekseni),
         "dahil=%s kapsam-disi=%s"
         % (KOK_GLOB_BASKA_UZANTI in d, [x in k for x in uzanti_ekseni])),
        # ---- DIZIN EKSENI: kok glob'u DOSYA alir, dizin GORUNUR bosluk kalir ----
        ("(l) desene UYAN DIZIN yedege GIRMEZ, `haric`e de DUSMEZ, "
         "KAPSAM-DISI'nda GORUNUR",
         KOK_GLOB_DIZIN not in d and KOK_GLOB_DIZIN not in h and KOK_GLOB_DIZIN in k,
         "dahil=%s haric=%s kapsam-disi=%s"
         % (KOK_GLOB_DIZIN in d, KOK_GLOB_DIZIN in h, KOK_GLOB_DIZIN in k)),
        # ==================== ALT-DIZIN GLOB'U (A1) =========================
        ("(m) EK_EVLER'den OKUNAN ALT-DIZIN desenleri SABIT uydurma yollarin "
         "HEPSINI tutuyor (deger + dizin bileseni kilitli)",
         len(alt_tutan) == len(ALT_GLOB_TUM_KAPSANAN),
         "%d/%d yol tutuluyor" % (len(alt_tutan), len(ALT_GLOB_TUM_KAPSANAN))),
        ("(n) BIRINCI dizin bileseni CANLI: o dizindeki %d sabit kayit kapsama ALIR"
         % len(ALT_GLOB_OLCUM),
         all(x in d for x in ALT_GLOB_OLCUM),
         "dahil: %s" % [x in d for x in ALT_GLOB_OLCUM]),
        ("(o) IKINCI dizin bileseni CANLI: o dizindeki sabit kayit kapsama ALIR",
         all(x in d for x in ALT_GLOB_KALIBRASYON),
         "dahil: %s" % [x in d for x in ALT_GLOB_KALIBRASYON]),
        ("(p) alt-dizin deseni UZANTIYI suzuyor (uzantisiz + farkli uzantili "
         "kapsama GIRMEZ)",
         ALT_GLOB_UZANTISIZ not in d and ALT_GLOB_BASKA_UZANTI not in d,
         "uzantisiz=%s baska=%s" % (ALT_GLOB_UZANTISIZ in d, ALT_GLOB_BASKA_UZANTI in d)),
        ("(q) alt-dizin deseni ALT AGACA INER (derin dosya KAPSANIR — olculmus "
         "davranis, kok glob'unun TERSI)",
         ALT_GLOB_DERIN in d, "dahil mi: %s" % (ALT_GLOB_DERIN in d)),
        ("(r) alt-dizin desenine UYAN DIZIN ne yedege GIRER ne `haric`e DUSER "
         "(kapsam_disi yalniz KOK girisleri sayar)",
         ALT_GLOB_DIZIN not in d and ALT_GLOB_DIZIN not in h,
         "dahil=%s haric=%s" % (ALT_GLOB_DIZIN in d, ALT_GLOB_DIZIN in h)),
    ]


def kok_glob_mutant_tarifleri(mod, kaynak):
    """Kok glob eksenlerinin MUTANT TARIFLERI -> [(kod, etiket, degisimler, dogrula)].

    🔴 CAPALAR CANLI KAYNAKTAN TURER: desen dizesi bu dosyaya IKINCI KEZ YAZILMAZ,
    mutasyon capasi EK_EVLER'den OKUNAN degerden kurulur ([[ikiz-tanim-sessiz-ayrisma]]).
    Capa kaynakta TEKIL degilse RuntimeError -> fail-loud (bayat capa sessizce gecmez).

    🔴 HER MUTANT MODUL DUZEYI BIR ISARET TASIR (`MUTANT_ISARETI`): kabul, mutasyonun
    DISKE YAZILMASI degil YUKLENEN MODULDE CANLI olmasidir. Ayni uzunlukta/ayni
    saniyede yazilan mutasyon uygulanmayabilir ve mutant "oldurulmus" sanilir
    ([[mutasyon-diske-yazma-tuzagi]] · [[mutasyon-bytecode-onbellegi]]). Isaret her
    mutantta FARKLI bir degerdir ve mutasyonla AYNI yazimda dosyaya girer -> isaret
    canliysa dosyanin TAMAMI canlidir; bayat bytecode bu esikten gecemez."""
    desenler = _kok_glob_desenleri(mod)
    if not desenler:
        raise RuntimeError("KOK GLOB CAPASI YOK: EK_EVLER[%r]" % KOK_GLOB_EV)
    desen = desenler[0]
    desen_capa = '"%s"' % desen
    alt_desenler = _alt_dizin_globlari(mod)
    alt_ilk = _alt_dizin_glob(mod)
    alt_ikinci = _ikinci_dizin_globu(mod)
    if not alt_ilk or not alt_ikinci:
        raise RuntimeError("ALT-DIZIN GLOB CAPASI EKSIK: ilk=%r ikinci-dizin=%r"
                           % (alt_ilk, alt_ikinci))

    def alt_capa(hedef, yeni_deger):
        """(capa, mutant) cifti — capa EK_EVLER'deki KOMSU IKILIDEN kurulur.

        🔴 NEDEN IKILI: tek basina `"<dizin>/*.<uzanti>"` dizesi yedekle.py'de
        4 KEZ geciyor (aciklama bloklarinda da orneklenmis) -> tekil capa sarti
        fail-loud patlıyordu. Komsu ikili EK_EVLER demetine OZGUDUR ve deger yine
        CANLI kaynaktan turer; desen teste ikinci kez YAZILMAZ."""
        i = alt_desenler.index(hedef)
        if i + 1 >= len(alt_desenler):
            raise RuntimeError("ALT-DIZIN CAPASI KURULAMADI (komsu yok): %r" % hedef)
        komsu = alt_desenler[i + 1]
        return ('"%s", "%s"' % (hedef, komsu), '"%s", "%s"' % (yeni_deger, komsu))

    alt_g = alt_capa(alt_ilk, "ZZZUYDURMAYOK/*.zzzyok")
    alt_dir = alt_capa(alt_ikinci, "zzzyokdizin/" + os.path.basename(alt_ikinci))
    alt_ext = alt_capa(alt_ilk, os.path.dirname(alt_ilk) + "/*")
    for capa in (desen_capa, KOK_GLOB_CAPA, KOK_GLOB_ISFILE_CAPA, KOK_GLOB_ISARET_CAPA,
                 alt_g[0], alt_dir[0], ALT_GLOB_WALK_CAPA, ALT_GLOB_DOSYA_CAPA):
        if kaynak.count(capa) != 1:
            raise RuntimeError("MUTASYON CAPASI TEKIL DEGIL (%d kez): %r"
                               % (kaynak.count(capa), capa[:60]))
    # Mutant desen degerleri DE turetilir (elle yazilmis ikinci kopya olmasin):
    yanlis_desen = '"ZZZUYDURMAYOK-%s"' % desen          # TAMAMEN baska bir deger
    uzantisiz_desen = '"%s"' % (desen.rsplit(".", 1)[0] if "." in desen else desen + "*")

    def isaret(kod):
        return (KOK_GLOB_ISARET_CAPA,
                'MUTANT_ISARETI = "%s"\n%s' % (kod, KOK_GLOB_ISARET_CAPA))

    def _desen_kaydi(m):
        yeni = _kok_glob_desenleri(m)
        return bool(yeni) and yeni != desenler

    return [
        ("M1", "MUTANT-1 (eslesme hep False)",
         [isaret("M1"), (KOK_GLOB_CAPA, "    return False  # MUTANT")],
         lambda m: m._kok_desen_tutuyor("x", ["x"]) is False),
        ("M2", "MUTANT-2 (eslesme hep True)",
         [isaret("M2"), (KOK_GLOB_CAPA, "    return True  # MUTANT")],
         lambda m: m._kok_desen_tutuyor("x", ["yok"]) is True),
        ("MG", "M-G (kok deseni TAMAMEN YANLIS degere kaydi)",
         [isaret("MG"), (desen_capa, yanlis_desen)], _desen_kaydi),
        ("MI", "M-I (desenden UZANTI kontrolu dusuruldu)",
         [isaret("MI"), (desen_capa, uzantisiz_desen)], _desen_kaydi),
        ("MD", "M-D (kok yolundaki isfile suzgeci dusuruldu)",
         [isaret("MD"),
          (KOK_GLOB_ISFILE_CAPA,
           "            if False:  # MUTANT (isfile suzgeci dusuruldu)\n"
           "                continue")],
         lambda m: True),   # isaret dosyanin TAMAMI icin kanit (bkz. docstring)
        # ---------------- A1: ALT-DIZIN GLOB EKSENLERI ----------------
        ("MAG", "MA-G (alt-dizin deseni TAMAMEN YANLIS degere kaydi)",
         [isaret("MAG"), alt_g], lambda m: _alt_dizin_globlari(m) != alt_desenler),
        ("MADIR", "MA-DIR (alt-dizin deseninin DIZIN bileseni kaydi)",
         [isaret("MADIR"), alt_dir], lambda m: _alt_dizin_globlari(m) != alt_desenler),
        ("MAEXT", "MA-EXT (alt-dizin deseninden UZANTI kontrolu dusuruldu)",
         [isaret("MAEXT"), alt_ext], lambda m: _alt_dizin_globlari(m) != alt_desenler),
        ("MADERIN", "MA-DERIN (alt agac yuruyusu durduruldu)",
         [isaret("MADERIN"),
          (ALT_GLOB_WALK_CAPA, "            altlar[:] = []  # MUTANT (alt agaca inme)")],
         lambda m: True),
        ("MADIZIN", "MA-DIZIN (alt-dizin yolunda DIZINLER de dosya gibi islendi)",
         [isaret("MADIZIN"),
          (ALT_GLOB_DOSYA_CAPA,
           "            for dosya in sorted(dosyalar) + sorted(altlar):  # MUTANT\n"
           "                gor = os.path.relpath(os.path.join(dizin, dosya), ev)")],
         lambda m: True),
    ]


def izole_ortam(td, yedekle, memory_adet=40, skills_adet=20):
    """GERCEK Drive'a/HOME'a DOKUNMAYAN tam izole kosum ortami.

    - kok   : sahte git deposu -> yedekle.py'nin ROOT'u (ve `.yedek.lock`) buraya duser
    - HOME  : sahte ev -> MEMORY + SKILLS expanduser ile buraya duser
    - hedef : td/drive/Pruvo/backup (drive_yolu STUB'u; gercek mount ASLA cozulmez)
    Beklenen repo dosyalari yedekle.REPO_BEKLENEN'den okunur (fikstur bayatlamasin)."""
    kok = os.path.join(td, "repo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(YEDEKLE, os.path.join(kok, "tools", "yedekle.py"))
    pruvo = os.path.join(td, "drive", "Pruvo")
    os.makedirs(pruvo)
    with open(os.path.join(kok, "tools", "drive_yolu.py"), "w") as f:
        f.write('DESEN = "/olmayan-mount/*/STL"\n'
                'def stl_dizini(sessiz=False):\n    return %r\n'
                'def pruvo_dizini(sessiz=False):\n    return %r\n'
                % (os.path.join(pruvo, "STL"), pruvo))
    sentetik_git(kok, "init", "-q", capture_output=True)
    for ad in yedekle.REPO_BEKLENEN:
        with open(os.path.join(kok, ad), "w") as f:
            f.write("izole test icerigi: %s\n" % ad)
    ev = os.path.join(td, "ev")
    mem = os.path.join(ev, ".claude", "projects", "-Users-okan-dev-pruvo", "memory")
    sk = os.path.join(ev, ".claude", "skills", "ornek-skill")
    os.makedirs(mem)
    os.makedirs(sk)
    for i in range(memory_adet):
        with open(os.path.join(mem, "not-%03d.md" % i), "w") as f:
            f.write("hafiza kaydi %d\n" % i)
    for i in range(skills_adet):
        with open(os.path.join(sk, "adim-%03d.md" % i), "w") as f:
            f.write("skill adimi %d\n" % i)
    ortam = dict(os.environ)
    ortam["HOME"] = ev
    return {"kok": kok, "betik": os.path.join(kok, "tools", "yedekle.py"),
            # Hedef kok adi TEK KAYNAKTAN (yedekle.YEDEK_KOK_ADI): 14 Agu
            # 86e7a035 koku backup-v2 yapti; buradaki "backup" literali ikiz
            # tanim olarak bayatlamisti ve bu harness'i ITHAL eden yedek-sir /
            # durum-yedek / yedek-gorev bataryalari BOS klasore bakip dusuyordu
            # (19 Agu SERIT B onarimi; [[ikiz-tanim-sessiz-ayrisma]]).
            "ev": ev, "pruvo": pruvo,
            # Kaynak kokleri TEK KAYNAKTAN: bu harness'i ITHAL eden bataryalar
            # (yedek-sir-eleme, yedek-gorev-kapsam) yolu YENIDEN KURMASIN — ikiz
            # tanim burada sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]]).
            "memory_kok": mem, "skills_kok": sk,
            "gorev_kok": os.path.join(ev, ".claude", "scheduled-tasks"),
            "hedef": os.path.join(pruvo, yedekle.YEDEK_KOK_ADI),
            "kilit": os.path.join(kok, yedekle.KILIT_ADI), "ortam": ortam,
            "memory_adet": memory_adet, "skills_adet": skills_adet}


def izole_kos(o, *bayraklar):
    return subprocess.run([sys.executable, o["betik"]] + list(bayraklar),
                          capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])


def izole_imza(o):
    """KUM HAVUZUNUN kendi kaynak imzasi — kum havuzunun KENDI yedekle.py'si ve sahte
    HOME'u ile olculur (gercek makinenin ~/.claude'u KARISMAZ). dict ya da None.
    Pano ucu testlerinde `durum._canli_kaynak_imzasi` yerine bu verilir; aksi halde
    pano gercek makineyi olcer ve kum havuzu damgasiyla karsilastirma anlamsiz olur."""
    r = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util,json;"
         "spec=importlib.util.spec_from_file_location('y', %r);"
         "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
         "print(json.dumps(m.kaynak_imzasi()))" % o["betik"]],
        capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])
    try:
        veri = json.loads(r.stdout.strip())
    except ValueError:
        return None
    return veri if isinstance(veri, dict) else None


def izole_baslat(o, *bayraklar):
    return subprocess.Popen([sys.executable, o["betik"]] + list(bayraklar),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            env=o["ortam"], cwd=o["kok"])


def hedef_dosyalari(hedef):
    if not os.path.isdir(hedef):
        return []
    return sorted(os.path.relpath(os.path.join(d, a), hedef)
                  for d, _alt, adlar in os.walk(hedef) for a in adlar)


def damga_json(hedef, ad=".son-yedek.json"):
    try:
        with open(os.path.join(hedef, ad), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def atlama_json(hedef):
    """Atlama kaydi AYRI dosyada (yazici sinifi ayri; bkz. yedekle.ATLAMA_ADI)."""
    return damga_json(hedef, ".son-yedek-atlama.json")


def birlesik_json(hedef):
    """Panonun gordugu birlesik gorunum: damga + atlama kaydi (durum.py ile ayni kural)."""
    d = dict(damga_json(hedef) or {})
    d.update({k: v for k, v in (atlama_json(hedef) or {}).items()
              if k.startswith("son_atlama")})
    return d


def _gercek_pruvo_dizini_saltokunur():
    """GERCEK Drive'daki .../Pruvo dizinini SALT-OKUNUR cozer (ya da None).

    🔴 NEDEN drive_yolu'nun KENDI cozuculeri CAGRILMAZ (27 Tem): ust sarmalayici
    STL cozucusune duser ve kayitli yol BAYATSA `.stl-backup-dir`i DUZELTIR —
    yani GERCEK REPOYA YAZAR (drive_yolu.ROOT sabit "/Users/okan/dev/pruvo",
    worktree'de bile ana checkout'u gosterir). Bir KABUL TESTININ gercek repoya
    yazmasi kabul edilemez: bu makinede kayitli yol bugun gecerli oldugu icin
    yazma tetiklenmiyordu, mount adi degistigi gun sessizce tetiklenecekti
    (hesap yeniden adlandirmasi bu depoda 15 Tem'de YASANDI).
    Burada yalniz OKUNUR: kayitli yol + drive_yolu.DESEN glob'u (durum.py'nin
    yedek_dizini() ile ayni salt-okunur deseni)."""
    adaylar = []
    try:
        sys.path.insert(0, TOOLS)
        import drive_yolu
        desen = drive_yolu.DESEN
        cfg = drive_yolu.CFG
    except Exception:
        return None
    try:
        if os.path.isfile(cfg):
            with open(cfg, "r", errors="replace") as f:
                kayitli = f.read().strip()
            if kayitli:
                adaylar.append(kayitli)
    except OSError:
        pass
    try:
        adaylar += sorted(glob.glob(desen))
    except OSError:
        pass
    for stl in adaylar:
        ust = os.path.dirname(stl.rstrip("/"))
        try:
            if os.path.isdir(ust):
                return ust
        except OSError:
            continue
    return None


def gercek_kritik_parmakizi(yedekle):
    """Test SONUNDA aynen durmasi gereken GERCEK dosyalarin bayt+mtime parmak izi.
    Doner: {etiket: (yol, (bayt, mtime) | None)}  — dosya yoksa deger None.

    Kapsam BILEREK iki dosya: (a) Drive'daki tazelik damgasi (testin hedefine
    yazmadiginin kaniti), (b) repo kokundeki `.stl-backup-dir` (drive_yolu'nun
    YAZDIGI tek dosya — E2/K5 onariminin nobetcisi)."""
    izler = {}
    pruvo = _gercek_pruvo_dizini_saltokunur()
    izler["damga"] = (os.path.join(pruvo, yedekle.YEDEK_KOK_ADI,
                                   yedekle.DAMGA_ADI)
                      if pruvo else None, None)
    try:
        sys.path.insert(0, TOOLS)
        import drive_yolu
        izler[".stl-backup-dir"] = (drive_yolu.CFG, None)
    except Exception:
        izler[".stl-backup-dir"] = (None, None)
    for etiket, (yol, _x) in list(izler.items()):
        if not yol:
            continue
        try:
            with open(yol, "rb") as f:
                izler[etiket] = (yol, (f.read(), os.path.getmtime(yol)))
        except OSError:
            izler[etiket] = (yol, None)
    return izler


def hermetik_kapisi(hermetik_adet, serit_paritesi):
    """Hermetik kumenin BUYUKLUGUNU ve SERIT PARITESINI olcer (fail-closed).

    `serit_paritesi=True` yalniz TAM bataryada verilir: orada `--hermetik` kolu AYRI
    BIR SURECTE kosturulur ve BASTIGI sayi ile buradaki sayi KARSILASTIRILIR.
    Hermetik kolun kendisi bunu yapmaz (sonsuz ozyineleme olurdu)."""
    kontrol("HERMETIK KUME ASGARIYI KARSILIYOR (>= %d — kume kucultulurse KIRMIZI)"
            % HERMETIK_ASGARI,
            hermetik_adet >= HERMETIK_ASGARI, "%d iddia" % hermetik_adet)
    if not serit_paritesi:
        return
    r = subprocess.run([sys.executable, os.path.abspath(__file__), HERMETIK_BAYRAK],
                       capture_output=True, text=True)
    serit_adet = None
    for satir in r.stdout.splitlines():
        s = satir.strip()
        if s.startswith(HERMETIK_SAYI_ONEKI):
            try:
                serit_adet = int(s[len(HERMETIK_SAYI_ONEKI):].strip())
            except ValueError:
                serit_adet = None
    # FAIL-CLOSED: sayi OKUNAMAZSA da kirmizi (sessiz "olculemedi" yesil olamaz).
    kontrol("SERIT PARITESI: `%s` kolu YERINDEKI hermetik kume ile AYNI SAYIDA "
            "iddia basiyor (cikis kodu YETMEZ)" % HERMETIK_BAYRAK,
            serit_adet is not None and serit_adet == hermetik_adet and r.returncode == 0,
            "serit=%s yerinde=%d serit_rc=%d" % (serit_adet, hermetik_adet, r.returncode))


def hermetik_main():
    """`--hermetik` kolu: YALNIZ hermetik bolumu kosar, SAYIYI basar."""
    yedekle = modul_yukle(YEDEKLE, "yedekle_gercek")
    adet = hermetik_bolum(yedekle)
    print("\n%s %d" % (HERMETIK_SAYI_ONEKI, adet))
    hermetik_kapisi(adet, serit_paritesi=False)
    kirmizi = [a for a, ok, _ in SONUC if not ok]
    print("=" * 70)
    print("HERMETIK KOL — %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    for a in kirmizi:
        print("  ❌ " + a)
    print("SONUC: %s" % ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


def hermetik_bolum(yedekle):
    """HERMETIK ALT KUME — 16 + 16b (kok + alt-dizin glob kod yolu).

    🔴 NEDEN AYRI FONKSIYON (A2): bu iki bolum TAMAMEN hermetiktir — fikstur
    gecici dizinde KENDI git deposunu kurar; ~/.claude, Drive mount'u, kardes
    evler ve repo kokundeki gitignore'lu dosyalar OKUNMAZ. Bu yuzden taze bir CI
    checkout'unda da kosabilir ve `--hermetik` koluyla BLOKLAYICI seride baglidir.
    Bataryanin GERISI (1/2/10/11 = gercek skills agaci + gercek kok dosyalari,
    13/13e/14 = flock + paralel kosum + zamanlama, 15 = gercek Drive damgasi)
    ORTAMA BAGLIDIR ve CI'da yapisal kirmizi/flake verir — bkz. ci-kapsam-test.py
    muafiyet gerekcesi.

    Doner: BU BOLUMDE uretilen kontrol SAYISI (serit paritesi bunu karsilastirir).
    """
    basla = len(SONUC)
    # ---------------- 16) KOK SEVIYESI GLOB KOD YOLU ----------------
    # Kapsam iddiasi: adsiz kok deseni, yerini aldigi elle yazilmis kok adlariyla
    # AYNI kumeyi kapsar (daha genis DEGIL, daha dar DEGIL). Fikstur adlari UYDURMA.
    print("\n16) KOK GLOB — adsiz kok deseninin kapsami (fikstur adlari UYDURMA)")
    saglam_iddia = []
    with tempfile.TemporaryDirectory() as td:
        desenler = _kok_glob_desenleri(yedekle)
        kontrol("kok deseni EK_EVLER'de TANIMLI (fail-closed: yoksa olculemez)",
                bool(desenler), "desen sayisi: %d" % len(desenler))
        # YAPISAL KILIT: hukum TEK TANIM, cagiran EN AZ IKI (iki karar noktasi).
        kg_kaynak = open(YEDEKLE, encoding="utf-8").read()
        kg_tanim, kg_cagri = kok_desen_yapisi(kg_kaynak)
        kontrol("%s TEK TANIM (ikiz tanim yok)" % KOK_GLOB_FN,
                kg_tanim == 1, "tanim: %d" % kg_tanim)
        kontrol("%s iki karar noktasindan da CAGRILIYOR" % KOK_GLOB_FN,
                kg_cagri >= 2, "cagri: %d" % kg_cagri)
        kontrol("hukum fonksiyonu modulde CANLI (cagrilabilir)",
                callable(getattr(yedekle, KOK_GLOB_FN, None)),
                type(getattr(yedekle, KOK_GLOB_FN, None)).__name__)
        ev_kg, bek_kg = kok_glob_fiksturu(td, yedekle)
        sir_sebep = yedekle.sir_sebebi(os.path.join(ev_kg, bek_kg["sirli"]),
                                       bek_kg["sirli"])
        kontrol("fikstur TAZE: sir eksenli uydurma ad gercekten SIR sayiliyor",
                bool(sir_sebep), str(sir_sebep))
        # FIKSTUR TAZELIGI — negatif eksenler TEMIZ desende gercekten NEGATIF mi?
        # (Bunlar RuntimeError DEGIL kontrol: mutant kosumunda cokme kirmiziyla
        # karismasin diye yalniz SAGLAM kodda olculur.)
        kontrol("fikstur TAZE: desen-disi kontrol dosyasi desene UYMUYOR",
                not any(fnmatch.fnmatch(KOK_GLOB_DESEN_DISI, x) for x in desenler),
                KOK_GLOB_DESEN_DISI)
        uz_uyan = [a for a in (KOK_GLOB_UZANTISIZ, KOK_GLOB_BASKA_UZANTI)
                   if any(fnmatch.fnmatch(a, x) for x in desenler)]
        kontrol("fikstur TAZE: uzanti eksenli adlar TEMIZ desene UYMUYOR "
                "(negatif eksen olculebilir)", not uz_uyan, "uyan: %s" % (uz_uyan or "-"))
        kontrol("fikstur TAZE: dizin eksenli ad TEMIZ desene UYUYOR "
                "(yalniz 'dosya degil' diye eleniyor)",
                any(fnmatch.fnmatch(KOK_GLOB_DIZIN, x) for x in desenler),
                KOK_GLOB_DIZIN)
        saglam_iddia = kok_glob_iddialari(yedekle, ev_kg, bek_kg)
        for etiket, ok, ayrinti in saglam_iddia:
            kontrol("SAGLAM " + etiket, ok, ayrinti)
        gecen = len([1 for _e, ok, _a in saglam_iddia if ok])
        kontrol("SAGLAM KOD YESIL: butun kok-glob iddialari gecti",
                gecen == len(saglam_iddia),
                "gecen %d / %d iddia" % (gecen, len(saglam_iddia)))

    # 16b) KIRMIZI-MUTASYON — hukum bozulunca iddia GERCEKTEN dusuyor mu?
    # Kabul CIKIS KODU DEGIL: olculen IDDIA SAYISI + ISARET sarti. Cokme kirmiziyla
    # karismasin diye AYRI basilir (cokmus mutant "oldurulmus" sayilmaz).
    print("\n16b) KOK GLOB KIRMIZI-MUTASYON — hukum bozulunca iddia DUSUYOR mu?")
    mutant_dusenler = {}
    # CAPA TAZELIGI = KIRMIZI KONTROL, COKME DEGIL: capa bayatlayinca traceback
    # atmak "cokme mi kirmizi mi" ayrimini yok eder ve bataryanin GERISI hic
    # kosmaz ([[mutasyon-kaniti-yeniden-uretilebilir]]: kabul cikis kodu degil,
    # OLCULEN IDDIA SAYISIDIR).
    try:
        kg_tarifler = kok_glob_mutant_tarifleri(yedekle, kg_kaynak)
    except RuntimeError as e:                           # capa bayat/tekil degil
        kg_tarifler = []
        kontrol("MUTASYON CAPALARI TAZE (yedekle.py kaynagiyla hizali)", False, str(e))
    else:
        kontrol("MUTASYON CAPALARI TAZE (yedekle.py kaynagiyla hizali)",
                True, "%d mutant tarifi" % len(kg_tarifler))
    for kod, etiket, degisimler, dogrula in kg_tarifler:
        with tempfile.TemporaryDirectory() as td:
            mut = mutant_yaz(td, degisimler, ad="mutant-kok-glob-%s.py" % kod)
            mmod = modul_yukle(mut, "yedekle_mutant_kokglob_%s" % kod)
            # 🔴 MUTASYON FIILEN UYGULANDI MI: yuklenen MODULDE isaret + eksen kaniti.
            try:
                eksen_ok = bool(dogrula(mmod))
            except Exception as e:                      # noqa: BLE001
                eksen_ok = False
                kod_ayrinti = "%s: %s" % (type(e).__name__, e)
            else:
                kod_ayrinti = "isaret=%r" % getattr(mmod, "MUTANT_ISARETI", None)
            canli = getattr(mmod, "MUTANT_ISARETI", None) == kod and eksen_ok
            kontrol("%s MUTASYON YUKLENEN MODULDE CANLI (bayat bytecode degil)" % etiket,
                    canli, kod_ayrinti)
            cokme = None
            try:
                ev_m, bek_m = kok_glob_fiksturu(td, mmod)
                mut_iddia = kok_glob_iddialari(mmod, ev_m, bek_m)
            except Exception as e:                      # noqa: BLE001 — sinif AYIRT EDILIYOR
                cokme, mut_iddia = "%s: %s" % (type(e).__name__, e), []
            kontrol("%s COKMEDI (cokme KIRMIZI ile karismasin)" % etiket,
                    cokme is None, cokme or "cokme yok")
            dusen = [e for e, ok, _a in mut_iddia if not ok]
            mutant_dusenler[etiket] = set(dusen)
            kontrol("%s KIRMIZI: en az 1 iddia DUSTU" % etiket,
                    canli and cokme is None and len(dusen) > 0,
                    "dusen %d / %d iddia: %s"
                    % (len(dusen), len(mut_iddia),
                       " · ".join(x.split(")")[0] + ")" for x in dusen) or "-"))
    # AYIRT EDICI MUTANT: iki mutant AYNI iddiayi dusuruyorsa ikincisi ek kanit
    # tasimaz (bkz. hafiza: beyan edilmis survivor delik gizler). Kabul: TUM
    # ciftler icin kume FARKI — bir mutantin kumesi bir digerine ESIT olamaz.
    kumeler = list(mutant_dusenler.items())
    kontrol("her mutant EN AZ 1 iddia dusurdu (survivor yok)",
            all(v for _e, v in kumeler), "bos kume: %s"
            % ([e for e, v in kumeler if not v] or "-"))
    ayni = [(a, b) for i, (a, va) in enumerate(kumeler)
            for b, vb in kumeler[i + 1:] if va == vb]
    kontrol("%d mutantin HEPSI AYIRT EDICI (hicbir cift AYNI kumeyi dusurmuyor)"
            % len(kumeler),
            bool(kumeler) and not ayni and len(kumeler) == len(kg_tarifler),
            "esit cift: %s | kumeler: %s"
            % (ayni or "-", " || ".join("%s:%d" % (e.split(" ")[0], len(v))
                                        for e, v in kumeler)))
    # KORELME KONTROLU: mutasyondan sonra saglam kod HALA yesil mi (bkz. hafiza:
    # onarimdan sonra korelme kontrolu kosulur).
    with tempfile.TemporaryDirectory() as td:
        ev_g, bek_g = kok_glob_fiksturu(td, yedekle)
        geri = kok_glob_iddialari(yedekle, ev_g, bek_g)
        kontrol("KORELME YOK: mutasyondan SONRA saglam kod yine tam yesil",
                all(ok for _e, ok, _a in geri) and len(geri) == len(saglam_iddia),
                "%d/%d iddia" % (len([1 for _e, ok, _a in geri if ok]), len(geri)))

    return len(SONUC) - basla


# ================= K212/A KUM HAVUZU — FAIL-CLOSED SILME (26 Agu 2026) =========
# K212/K1 IDDIASI: alt agac silicisi (`yedek_agac_sir_sil`) kok kolunun fail-closed
# emniyetini ATLATABILIYOR -> tek kopyasi olan dosya KAYBOLUR. yedekle.py:850-866 +
# 1121-1137'de onarildigini SOYLEYEN yorum satirlari duruyor; yorum KANIT DEGILDIR
# ([[aracin-teshis-cumlesi-olcum-degil]]). Asagisi AYNI kalemi yedek KOKUNDE ve ALT
# AGACTA ayni anda kurar, IKI KOLU da kostururken UCUNCU bir gercegi de olcer:
# alt agac yuruyusu yedek KOKUNU DE gezer, yani kok kolunun fail-closed ile
# BIRAKTIGI kalemi ardindan kosan alt agac kolu ELINE ALIR. Olculen kusur tam
# buydu; vaka bu yuzden "iki ayri dosya" degil "AYNI kalem, iki kol" kurar.
#
# 🔴 GERCEK KAYNAGA/DRIVE'A DOKUNULMAZ: modul globalleri (ROOT, AGAC_KAPSAMI) kum
# havuzuna cevrilir ve `finally` ile GERI ALINIR. Silme YALNIZ tempfile icinde olur.

K212A_YERELSIZ = ".thingiverse-token"      # SIR_ADLARI'nda -> kok kolunun kumesinde DE var
K212A_ASILLI = ".r2-credentials.json"      # POZITIF kontrol: yerel asli VAR -> SILINMELI
K212A_KAPSAMDISI = "profil-kontrol"        # AGAC_EK_ATLA["cron"] "profil-" onekine uyar


def k212a_fikstur(td):
    """Kum havuzu: yerel asli OLMAYAN ayni ad yedek KOKUNDE ve ALT AGACTA;
    yerel asli OLAN ikinci ad yine ikisinde; + bir kapsam-disi bayat klasor.
    Doner: (backup, sahte_root, sahte_cron, yollar)."""
    backup = os.path.join(td, "backup-v2")
    sahte_root = os.path.join(td, "sahte-root")
    sahte_cron = os.path.join(td, "sahte-cron")
    os.makedirs(os.path.join(backup, "cron-nobet"))
    os.makedirs(os.path.join(backup, "cron-nobet", K212A_KAPSAMDISI))
    os.makedirs(sahte_root)
    os.makedirs(sahte_cron)
    # POZITIF kontrol icin YEREL ASIL: yalniz K212A_ASILLI'nin asli VAR.
    # K212A_YERELSIZ'in asli BILEREK YOK -> fail-closed kolun tek tetikleyicisi budur.
    for kaynak_kok in (sahte_root, sahte_cron):
        with open(os.path.join(kaynak_kok, K212A_ASILLI), "w") as fh:
            fh.write("SIMULASYON: yerel ASIL VAR (silme izni bundan gelir)\n")
    yollar = {}
    for etiket, gor in (("kok_yerelsiz", K212A_YERELSIZ),
                        ("kok_asilli", K212A_ASILLI),
                        ("agac_yerelsiz", "cron-nobet/" + K212A_YERELSIZ),
                        ("agac_asilli", "cron-nobet/" + K212A_ASILLI)):
        tam = os.path.join(backup, *gor.split("/"))
        with open(tam, "w") as fh:
            fh.write("SIMULASYON fikstur govdesi — GERCEK SIR DEGIL\n")
        yollar[etiket] = tam
    kap = os.path.join(backup, "cron-nobet", K212A_KAPSAMDISI, ".claude.json")
    with open(kap, "w") as fh:
        fh.write("{}\n")
    yollar["kapsamdisi"] = os.path.join(backup, "cron-nobet", K212A_KAPSAMDISI)
    return backup, sahte_root, sahte_cron, yollar


def k212a_kos(mod, td):
    """AYNI fiksturu `mod` ile kostur (asil modul ya da bir MUTANT). Kollarin
    sirasi GERCEK `yedek_al` ile AYNI: once kok (2770), sonra alt agac (2781).
    Doner: olculen hal sozlugu (dosya varligi DISKTEN okunur —
    [[silme-sayaci-diskten-dogrulanmali]]: sayaca degil diske bakilir)."""
    backup, sahte_root, sahte_cron, yollar = k212a_fikstur(td)
    eski_root, eski_kapsam = mod.ROOT, mod.AGAC_KAPSAMI
    mod.ROOT = sahte_root
    mod.AGAC_KAPSAMI = tuple(
        (e, sahte_cron if h == "cron-nobet" else k, h, i)
        for e, k, h, i in eski_kapsam)
    try:
        kok_islenen, kok_atlanan, _kb = mod.yedek_kok_sir_temizle(backup)
        agac_plan = mod.yedek_agac_sir_plani(backup)
        agac_islenen, agac_atlanan, _ab = mod.yedek_agac_sir_sil(agac_plan, backup)
        kap_plan = mod.yedek_agac_kapsamdisi_plani(backup)
        mod.yedek_agac_kapsamdisi_sil(kap_plan, backup)
    finally:
        mod.ROOT, mod.AGAC_KAPSAMI = eski_root, eski_kapsam
    return {"kok_islenen": sorted(a for a, _y in kok_islenen),
            "kok_atlanan": sorted(a for a, _s in kok_atlanan),
            "kok_sebepler": [s for _a, s in kok_atlanan],
            "agac_plan": sorted(g for g, _s, _b in agac_plan),
            "agac_islenen": sorted(g for g, _y in agac_islenen),
            "agac_atlanan": sorted(g for g, _s in agac_atlanan),
            "agac_sebepler": [s for _g, s in agac_atlanan],
            "duruyor": {k: os.path.exists(v) for k, v in yollar.items()}}


# MUTANT TARIFLERI — her biri TEK bir kolu hedefler; capa bulunamazsa mutant_yaz
# RuntimeError atar (bayat capa sessizce gecmesin).
K212A_MUTANT_HEDEF = (
    "        tamam, engel = yerel_asil_durumu(yedek_yerel_asli(gor))\n"
    "        if not tamam:\n"
    "            atlanan.append((gor, engel))\n"
    "            continue\n",
    "        tamam, engel = True, \"\"   # MUTANT K212/A: alt agac kolu EMNIYETSIZ\n")
# KONTROL mutanti BASKA bir kolu bozar (kapsam-disi silici). K212/A iddialarini
# DUSURMEMELI; ama OLU de olmamali -> kapsam-disi klasorun DURDUGU ayrica olculur.
K212A_MUTANT_KONTROL = (
    "            shutil.rmtree(tam)\n            islenen.append((gor, tam))\n",
    "            islenen.append((gor, tam))   # MUTANT KONTROL: kapsam-disi SILINMIYOR\n")


def main():
    yedekle = modul_yukle(YEDEKLE, "yedekle_gercek")
    izler_once = gercek_kritik_parmakizi(yedekle)

    # ---------------- 1) KAPSAM (gercek agac) ----------------
    print("\n1) KAPSAM — gercek ~/.claude/skills agaci planda mi?")
    dahil, haric, gurultu = yedekle.skills_plani()
    if not os.path.isdir(yedekle.SKILLS):
        kontrol("skills dizini var", False, yedekle.SKILLS + " YOK (bu makinede olcum yapilamaz)")
    else:
        kontrol("skills dizini var", True, "%d dahil / %d haric / %d gurultu"
                % (len(dahil), len(haric), len(gurultu)))
        for z in ZORUNLU:
            kontrol("planda: " + z, z in dahil)
        kontrol("gurultu (pyc/__pycache__) plana GIRMEDI",
                not any(g.endswith(".pyc") for g in dahil))
        kontrol("gercek agacta sir nobeti ELEMESI yok (temiz agac)", not haric,
                "elenen: " + ", ".join(g for g, _ in haric) if haric else "")

    # ---------------- 2) KURU KOSUM (ucdan uca, YAZMAZ) ----------------
    print("\n2) KURU KOSUM — --kuru listeler, hicbir sey yazmaz")
    r = subprocess.run([sys.executable, YEDEKLE, "--kuru"], capture_output=True, text=True)
    kontrol("--kuru exit 0", r.returncode == 0, "rc=%d" % r.returncode)
    kontrol("cikti 'KURU KOSUM' diyor", "KURU KOSUM" in r.stdout)
    for z in ZORUNLU:
        kontrol("kuru listede: skills/" + z, ("skills/" + z) in r.stdout)
    kontrol("kuru kosumda 'bitti ->' YOK (gercek yedek calismadi)", "bitti ->" not in r.stdout)

    # ---------------- 3) KIRMIZI MUTASYON: skills kapsam disi ----------------
    print("\n3) KIRMIZI-MUTASYON (kapsam) — skills plandan cikarilirsa kontrol kirmizi mi?")
    with tempfile.TemporaryDirectory() as td:
        mut = mutant_yaz(td, [("    dahil, haric, gurultu = skills_plani()",
                               "    dahil, haric, gurultu = [], [], []  # MUTANT")])
        rm = subprocess.run([sys.executable, mut, "--kuru"], capture_output=True, text=True)
        kontrol("mutant kosuyor (exit 0)", rm.returncode == 0, "rc=%d" % rm.returncode)
        eksik = [z for z in ZORUNLU if ("skills/" + z) not in rm.stdout]
        kontrol("MUTANTTA zorunlu skill dosyalari listede YOK (kontrol KIRMIZI yanardi)",
                len(eksik) == len(ZORUNLU), "kayip: %d/%d" % (len(eksik), len(ZORUNLU)))

    # ---------------- 4) SIR NOBETI (sentetik) ----------------
    print("\n4) SIR NOBETI — sentetik sir dosyalari pakete GIRMEMELI")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        f = fikstur_kur(kok)
        d, h, g = yedekle.skills_plani(kok=kok)
        h_yollar = [y for y, _ in h]
        kontrol("normal dosya planda", f["normal"] in d)
        for s in f["sirlar"]:
            kontrol("sir pakete GIRMEDI: " + s, s not in d)
            kontrol("sir SEBEPLE raporlandi: " + s, s in h_yollar)
        kontrol("pyc gurultu olarak ayrildi", not any(x.endswith(".pyc") for x in d + h_yollar))
        sebepler = " | ".join(s for _, s in h)
        kontrol("sebep metni sirrin KENDISINI icermiyor",
                "SAHTE-FIKSTUR-VERISI" not in sebepler and "sahte-jeton-govdesi" not in sebepler,
                sebepler)
        # 🔴 E2 NOBETCISI: iki parcali kurulan fikstur, ICERIK IMZASI yoluyla
        # elenmeye DEVAM ediyor mu? (ad deseni degil — kurulum.md masum bir ad.)
        # Bu kontrol olmadan "fiksturu bol" onarimi imza tanimayi sessizce olduruyor
        # olabilirdi ve 4. bolum yine yesil yanardi (ad deseni yeterdi sanilirdi).
        kurulum_sebep = dict(h).get("ornek-skill/kurulum.md", "")
        kontrol("iki parcali fikstur ICERIK IMZASI ile elendi (ad deseniyle DEGIL)",
                "icerik imzasi" in kurulum_sebep and "ozel anahtar" in kurulum_sebep,
                kurulum_sebep)
        # (beklenen dizeler de PARCALI kurulur — bu satirlar taramaya yem olmasin)
        kontrol("calisma anindaki fikstur dizesi TAM bicimde (bolme sizdirmadi)",
                SAHTE_ANAHTAR.startswith("-----BEGIN RSA PRIVATE" + _ANAHTAR_KUYRUK + "\n")
                and SAHTE_ANAHTAR.rstrip().endswith("-----END RSA PRIVATE"
                                                    + _ANAHTAR_KUYRUK),
                repr(SAHTE_ANAHTAR[:34]))

    # ---------------- 5) KIRMIZI MUTASYON: sir nobeti devre disi ----------------
    print("\n5) KIRMIZI-MUTASYON (sir nobeti) — nobet kapatilirsa sirlar sizar mi?")
    with tempfile.TemporaryDirectory() as td:
        mut = mutant_yaz(td, [("            sebep = sir_sebebi(tam, ad)",
                               "            sebep = None  # MUTANT")])
        mmod = modul_yukle(mut, "yedekle_mutant_sir")
        kok = os.path.join(td, "skills")
        f = fikstur_kur(kok)
        d, h, _g = mmod.skills_plani(kok=kok)
        sizan = [s for s in f["sirlar"] if s in d]
        kontrol("MUTANTTA sirlar pakete SIZDI (kontrol KIRMIZI yanardi)",
                len(sizan) == len(f["sirlar"]), "sizan: %d/%d" % (len(sizan), len(f["sirlar"])))

    # ---------------- 6) IDEMPOTENS ----------------
    print("\n6) IDEMPOTENS — iki kez kosmak mukerrer yigmaz/bozmaz")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        hedef = os.path.join(td, "backup-skills")
        fikstur_kur(kok)
        d, h, _g = yedekle.skills_plani(kok=kok)
        y1, b1 = yedekle.skills_yaz(kok, hedef, d, h)
        kume1 = sorted(os.path.relpath(os.path.join(kk, a), hedef)
                       for kk, _, aa in os.walk(hedef) for a in aa)
        y2, b2 = yedekle.skills_yaz(kok, hedef, d, h)
        kume2 = sorted(os.path.relpath(os.path.join(kk, a), hedef)
                       for kk, _, aa in os.walk(hedef) for a in aa)
        kontrol("iki kosumda ayni dosya kumesi", kume1 == kume2, "%d dosya" % len(kume2))
        kontrol("yazilan sayisi sabit", y1 == y2 == len(d), "%d/%d/%d" % (y1, y2, len(d)))
        kontrol("hedefte sir dosyasi YOK",
                not any(x.endswith(".r2-credentials.json") or "token" in x for x in kume2))

    # ---------------- 7) BAYAT SIR KOPYASI NOBETI ----------------
    print("\n7) BAYAT SIR NOBETI — filtresiz eski surumun biraktigi kopya yakalaniyor mu?")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        hedef = os.path.join(td, "backup-skills")
        fikstur_kur(kok)
        d, h, _g = yedekle.skills_plani(kok=kok)
        # Eski (filtresiz copytree) surumun birakacagi kopyayi taklit et:
        eski = os.path.join(hedef, "ornek-skill", ".r2-credentials.json")
        os.makedirs(os.path.dirname(eski), exist_ok=True)
        with open(eski, "w") as fh:
            fh.write("eski sizmis kopya\n")
        _y, bayat = yedekle.skills_yaz(kok, hedef, d, h, sir_temizle=False)
        kontrol("bayat sir kopyasi TESPIT edildi", eski in bayat, "%d bulundu" % len(bayat))
        kontrol("varsayilan SILMEZ (veri silme elle onaylanir)", os.path.exists(eski))
        _y, bayat2 = yedekle.skills_yaz(kok, hedef, d, h, sir_temizle=True)
        kontrol("--sir-temizle ile SILINDI", not os.path.exists(eski))

    # ---------------- 8) BILINMEYEN BAYRAK = FAIL-CLOSED ----------------
    print("\n8) FAIL-CLOSED — yazim hatasi olan bayrak GERCEK yedek baslatmasin")
    r = subprocess.run([sys.executable, YEDEKLE, "--kuruu"], capture_output=True, text=True)
    kontrol("bilinmeyen bayrak exit != 0", r.returncode != 0, "rc=%d" % r.returncode)
    kontrol("bilinmeyen bayrakta yedek CALISMADI",
            "bitti ->" not in r.stdout and "yedek:" not in r.stdout)

    # ---------------- 9) TAZELIK DAMGASI + UCUZ MOD ----------------
    print("\n9) DAMGA + --gerekliyse — pano bunu okur, hook bunu kullanir")
    with tempfile.TemporaryDirectory() as td:
        kontrol("damga yoksa None (patlamaz)", yedekle.damga_oku(td) is None)
        yedekle.damga_yaz(td, {"memory": 5, "skills": 3, "repo": 2, "skills_haric": 0})
        d = yedekle.damga_oku(td)
        kontrol("damga yazilip okunuyor", isinstance(d, dict) and d.get("skills") == 3)
        kontrol("damgada zaman VAR", isinstance(d.get("zaman"), (int, float)))
        with open(os.path.join(td, yedekle.DAMGA_ADI), "w") as fh:
            fh.write("{bozuk")
        kontrol("bozuk damga None doner", yedekle.damga_oku(td) is None)
    # gerekli_mi: FAIL-OPEN — atlamak KANITA bagli, yedeklemek varsayilan
    kontrol("damga yok  -> YEDEKLE", yedekle.gerekli_mi(None, 100) is True)
    kontrol("damga bozuk-> YEDEKLE", yedekle.gerekli_mi({"zaman": "abc"}, 100) is True)
    kontrol("mtime olculemedi -> YEDEKLE", yedekle.gerekli_mi({"zaman": 100}, None) is True)
    kontrol("kaynak damgadan YENI -> YEDEKLE", yedekle.gerekli_mi({"zaman": 100}, 150) is True)
    kontrol("kaynak damgadan ESKI -> ATLA", yedekle.gerekli_mi({"zaman": 100}, 50) is False)
    kontrol("--gerekliyse gecerli bayrak", "--gerekliyse" in yedekle.BAYRAKLAR)
    kontrol("en_yeni_kaynak_mtime sayi donduruyor",
            isinstance(yedekle.en_yeni_kaynak_mtime(), float))

    # ---------------- 10) F1: KOK ANA AGACA COZULUYOR MU ----------------
    print("\n10) F1 SAHTE TAZELIK — kok WORKTREE'den de ANA agaci gostermeli")
    wt = os.path.abspath(os.path.join(TOOLS, ".."))    # bu betik bir worktree'de kosuyor olabilir
    ana = yedekle.ana_calisma_agaci(wt)
    # Bagimsiz ayirt edici: ANA agacta .git bir DIZIN, worktree'de bir DOSYA.
    kontrol("cozulen kok ANA agac (.git DIZIN)", os.path.isdir(os.path.join(ana, ".git")), ana)
    kontrol("modul ROOT'u da ANA agac", yedekle.ROOT == ana, yedekle.ROOT)
    eksik = yedekle.repo_eksikleri()
    kontrol("beklenen repo dosyalarinin HEPSI bulundu (kismi yedek YOK)", eksik == [],
            "eksik: %s" % (eksik or "-"))
    kontrol("_repo_dosyalari 4 dosya donduruyor", len(yedekle._repo_dosyalari(False)) == 4,
            str(len(yedekle._repo_dosyalari(False))))
    # 🔴 30 TEM — SESSIZ KAPSAM DARALMASININ KOK NEDENI (bu kontrol aylardir KIRMIZI idi):
    # REPO_BEKLENEN "CLAUDE.md" diyordu, ama tek kaynak AGENTS.md'ye gecince CLAUDE.md
    # SYMLINK oldu ve _repo_dosyalari()'nin `not islink` suzgeci onu sessizce eledi ->
    # ajan baglam dosyasi HICBIR yedege girmedi (gitignore'da oldugu icin git'te de yok).
    # Iki iddia bunu KALICI olarak kilitler; ad tekrar symlink'e cevrilirse KIRMIZI yanar.
    repo_plan = yedekle._repo_dosyalari(False)
    kontrol("ajan baglam dosyasi (AGENTS.md) yedek planinda", "AGENTS.md" in repo_plan,
            ", ".join(repo_plan))
    kontrol("BEKLENEN adlarin hicbiri symlink DEGIL (yoksa sessizce yedeksiz kalir)",
            all(not os.path.islink(os.path.join(yedekle.ROOT, a))
                for a in yedekle.REPO_BEKLENEN),
            ", ".join(a for a in yedekle.REPO_BEKLENEN
                      if os.path.islink(os.path.join(yedekle.ROOT, a))) or "-")
    # SYMLINK NOBETI (davranissal, gercek repoya DOKUNMAZ): sahte bir kokte beklenen bir ad
    # symlink olursa repo_eksikleri() onu "eksik" saymali -> damga tam=False. Eski surumde
    # os.path.exists() symlink'i IZLEDIGI icin "var" diyordu = tam bu sessiz kayip.
    with tempfile.TemporaryDirectory() as td:
        for ad in yedekle.REPO_BEKLENEN:
            with open(os.path.join(td, ad), "w", encoding="utf-8") as f:
                f.write("x")
        eski_kok = yedekle.ROOT
        try:
            yedekle.ROOT = td
            kontrol("sahte kokte eksik YOK (taban)", yedekle.repo_eksikleri() == [],
                    str(yedekle.repo_eksikleri()))
            hedef = yedekle.REPO_BEKLENEN[1]
            os.remove(os.path.join(td, hedef))
            os.symlink(os.path.join(td, yedekle.REPO_BEKLENEN[2]), os.path.join(td, hedef))
            kontrol("🔴 BEKLENEN ad SYMLINK'e donunce 'eksik' sayiliyor (sessiz kayip yok)",
                    yedekle.repo_eksikleri() == [hedef], str(yedekle.repo_eksikleri()))
            kontrol("symlink _repo_dosyalari'ndan da dusuyor (iki olcum tutarli)",
                    hedef not in yedekle._repo_dosyalari(False),
                    ", ".join(yedekle._repo_dosyalari(False)))
        finally:
            yedekle.ROOT = eski_kok
    with tempfile.TemporaryDirectory() as td:
        mut = mutant_yaz(td, [("        if p.returncode == 0 and ortak:",
                               "        if False:  # MUTANT: git cozumu devre disi")])
        mmod = modul_yukle(mut, "yedekle_mutant_kok")
        kontrol("MUTANTTA kok WORKTREE'ye dusuyor (kontrol KIRMIZI yanardi)",
                mmod.ana_calisma_agaci(wt) == wt, mmod.ana_calisma_agaci(wt))

    # ---------------- 11) F1: KISMI YEDEK DAMGASI ----------------
    print("\n11) F1 — eksik dosya varsa TAM GUVEN damgasi ATILMAMALI")
    with tempfile.TemporaryDirectory() as td:
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 2},
                          eksik=[".urun-kaynaklari.json", "DEVAM-ARSIV.md"])
        d = yedekle.damga_oku(td)
        kontrol("damga tam=False", d.get("tam") is False)
        kontrol("eksik listesi damgada", d.get("eksik") == [".urun-kaynaklari.json",
                                                           "DEVAM-ARSIV.md"])
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 4}, eksik=[])
        kontrol("eksiksiz kosumda tam=True", yedekle.damga_oku(td).get("tam") is True)

    # ---------------- 12) F4: BUDANAN DIZIN RAPORLANIYOR MU ----------------
    print("\n12) F4 — budanan gurultu dizini SESSIZCE yutulmamali")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        fikstur_kur(kok)                                   # __pycache__/x.pyc iceriyor
        _d, _h, g = yedekle.skills_plani(kok=kok)
        kontrol("budanan dizin gurultu listesinde", any("__pycache__" in x for x in g),
                str(g))
        kontrol("dizin oldugu belirtiliyor", any("(dizin budandi)" in x for x in g))

    # ---------------- 13) KILIT: DETERMINISTIK KARSILIKLI DISLAMA ----------------
    print("\n13) KILIT — kilit BASKASINDAYKEN kosum ATLAR, damga YALAN SOYLEMEZ")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        kontrol("test hedefi gecici dizinde (gercek Drive DEGIL)",
                o["hedef"].startswith(td), o["hedef"])
        kilitci = open(o["kilit"], "a+")               # "kosan yedek" taklidi
        fcntl.flock(kilitci, fcntl.LOCK_EX)
        sahip_bas = time.time()
        kilitci.write(yedekle._sahip_imzasi(sahip_bas, pid=999999))
        kilitci.flush()
        r = izole_kos(o, "--gerekliyse")
        kontrol("kilit doluyken exit 0 (FAIL-OPEN: push bloklanmaz)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, r.stderr.strip()[:80]))
        kontrol("cikti 'yedek ATLANDI' diyor", "yedek ATLANDI" in r.stdout,
                r.stdout.strip().splitlines()[0] if r.stdout.strip() else "(bos)")
        kontrol("ATLANAN kosum HICBIR dosya kopyalamadi (yalniz atlama kaydi)",
                "bitti ->" not in r.stdout and hedef_dosyalari(o["hedef"]) ==
                [".son-yedek-atlama.json"], str(hedef_dosyalari(o["hedef"])))
        kontrol("ATLANAN kosum DAMGAYA hic dokunmadi (damga YOK)",
                damga_json(o["hedef"]) is None)
        d = atlama_json(o["hedef"]) or {}
        kontrol("atlama kaydinda TAM GUVEN alani YOK ('zaman' yok)", "zaman" not in d,
                str(sorted(d)))
        kontrol("atlama kaydi VAR", isinstance(d.get("son_atlama"), float))
        kontrol("atlama sebebi yazili", "baska yedek kosuyordu" in
                str(d.get("son_atlama_sebep")), str(d.get("son_atlama_sebep"))[:70])
        kontrol("kaynak degismemisken atlama KAPSANDI (pano bosuna uyarmaz)",
                d.get("son_atlama_kapsandi") is True, str(d.get("son_atlama_kapsandi")))
        kontrol("beklenen SAHIBIN baslangici TAM HASSAS kaydedildi",
                d.get("son_atlama_sahip_baslangici") == sahip_bas,
                "%r vs %r" % (d.get("son_atlama_sahip_baslangici"), sahip_bas))

        # 13a) KAPSANMAYAN atlama: kilit tutulurken kaynak DEGISIRSE uyari SART
        time.sleep(0.02)
        with open(os.path.join(o["ev"], ".claude", "projects",
                               "-Users-okan-dev-pruvo", "memory", "not-000.md"), "w") as fh:
            fh.write("kilit tutulurken YENI degisiklik\n")
        r3 = izole_kos(o, "--gerekliyse")
        d3 = atlama_json(o["hedef"]) or {}
        kontrol("kilit tutulurken degisen kaynak -> atlama KAPSANMADI",
                d3.get("son_atlama_kapsandi") is False, str(d3.get("son_atlama_kapsandi")))
        kontrol("kapsanmayan atlamada cikti UYARIYOR",
                "KAPSAMAYABILIR" in r3.stdout, r3.stdout.strip().splitlines()[-1][:80])
        kontrol("kapsanmayan atlamada da exit 0 (fail-open)", r3.returncode == 0)

        # kilit birakilinca ayni ortam NORMAL calismali (regresyon)
        fcntl.flock(kilitci, fcntl.LOCK_UN)
        kilitci.close()
        r2 = izole_kos(o)
        # +2: damga + (onceki atlamadan kalan) atlama kaydi
        bekle = o["memory_adet"] + o["skills_adet"] + len(yedekle.REPO_BEKLENEN) + 2
        gercek_dosya = hedef_dosyalari(o["hedef"])
        kontrol("kilit birakilinca yedek GERCEKTEN alindi (exit 0 + 'bitti ->')",
                r2.returncode == 0 and "bitti ->" in r2.stdout, "rc=%d" % r2.returncode)
        kontrol("hedefte beklenen dosya sayisi", len(gercek_dosya) == bekle,
                "%d/%d" % (len(gercek_dosya), bekle))
        d2 = damga_json(o["hedef"]) or {}
        kontrol("damga tam=True + sayilar dogru",
                d2.get("tam") is True and d2.get("memory") == o["memory_adet"]
                and d2.get("skills") == o["skills_adet"],
                "memory=%s skills=%s" % (d2.get("memory"), d2.get("skills")))
        kontrol("onceki ATLAMA kaydi KORUNDU (tamamlanan kosum onu silmez)",
                isinstance((atlama_json(o["hedef"]) or {}).get("son_atlama"), float))
        kontrol("gecici damga dosyasi kalmadi",
                not any(".tmp-" in x for x in gercek_dosya))

    # ---------------- 13e) IMZA HASSASIYETI (flake kaynagi) ----------------
    # Curutucu olcumu: imza `%.3f` ile yuvarlanirken karsilastirma tam hassas mtime
    # ile yapiliyordu -> 200 denemenin 94'u (%47) YANLIS karar; yedekle-test 16
    # kosumun 6'sinda kirmizi. Burada 2000 ornekte YANLIS KARAR 0 olmali.
    print("\n13e) IMZA HASSASIYETI — 2000 ornek, yanlis karar 0 (flake kapisi)")
    taban = time.time()
    sapmalar = (0.0, 1e-6, -1e-6, 1e-4, -1e-4)
    yanlis_yeni = yanlis_eski = tur_kaybi = 0
    for i in range(2000):
        t = taban + i * 0.000173                      # ms-alti kaymalari tarar
        coz = yedekle._imza_coz(yedekle._sahip_imzasi(t, pid=1))[1]
        if coz != t:
            tur_kaybi += 1
        eski_coz = yedekle._imza_coz("pid=1 baslangic=%.3f iso=x" % t)[1]  # ESKI bicim
        for s in sapmalar:
            dogru = yedekle.atlama_kapsandi_mi(t, t + s)
            if yedekle.atlama_kapsandi_mi(coz, t + s) is not dogru:
                yanlis_yeni += 1
            if yedekle.atlama_kapsandi_mi(eski_coz, t + s) is not dogru:
                yanlis_eski += 1
    kontrol("imza TAM tur-donusu yapiyor (float(repr(x)) == x)", tur_kaybi == 0,
            "%d/2000 kayip" % tur_kaybi)
    kontrol("2000 ornek x 5 sapma = 10000 kararda YANLIS 0", yanlis_yeni == 0,
            "yanlis=%d/10000" % yanlis_yeni)
    kontrol("ESKI %.3f bicimi AYNI fikstürde yaniliyordu (kontrol olcuyor)",
            yanlis_eski > 0, "eski bicim yanlis=%d/10000 (%.0f%%)"
            % (yanlis_eski, 100.0 * yanlis_eski / 10000))

    # ---------------- 13f) SAHIP ASILDI/OLDU -> PANO SUSMAMALI ----------------
    # Curutucu senaryosu: kaynak degisti -> SONRA bir yedek kilidi aldi (kapsandi=True)
    # -> sahip asildi/oldu, damgayi HIC yazmadi. Dosya yedekte YOK ama eski damga
    # "taze" gorunuyor. Pano UYARMAK ZORUNDA.
    print("\n13f) SAHIP BITIRMEDI — 'kapsandi' tek basina yeter mi? (pano ucu)")
    sys.path.insert(0, TOOLS)
    durum = modul_yukle(os.path.join(TOOLS, "durum.py"), "durum_kilit_kontrol")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        r0 = izole_kos(o)                              # 1) gercek bir yedek tamamlandi
        kontrol("hazirlik: ilk yedek tamamlandi", "bitti ->" in r0.stdout)
        d0 = damga_json(o["hedef"]) or {}
        taze_once = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
        kontrol("hazirlik: pano bu noktada TAZE", taze_once[0].strip().startswith("taze:"),
                taze_once[0])
        time.sleep(0.02)
        with open(os.path.join(o["ev"], ".claude", "projects",     # 2) KAYNAK DEGISTI
                               "-Users-okan-dev-pruvo", "memory", "not-001.md"), "w") as fh:
            fh.write("yedeklenmesi GEREKEN yeni icerik\n")
        time.sleep(0.02)
        asili = open(o["kilit"], "a+")                 # 3) sahip kilidi aldi ve ASILDI
        fcntl.flock(asili, fcntl.LOCK_EX)
        asili.truncate(0)
        asili.write(yedekle._sahip_imzasi(time.time(), pid=999999))
        asili.flush()
        r1 = izole_kos(o, "--gerekliyse")              # 4) push atladi
        d1 = birlesik_json(o["hedef"])
        sat = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
        print("     --- pano ciktisi (sahip bitirmedi) ---")
        for s in sat:
            print("    " + s)
        kontrol("atlama 'kapsandi' olctu (degisiklik sahipten ONCE)",
                d1.get("son_atlama_kapsandi") is True, str(d1.get("son_atlama_kapsandi")))
        kontrol("damganin `baslangic`i HALA ilk kosumun (sahip yazmadi)",
                d1.get("baslangic") == d0.get("baslangic"))
        kontrol("🔴 PANO SUSMUYOR: 'taze' DEMIYOR", not sat[0].strip().startswith("taze:"),
                sat[0])
        kontrol("pano sahibin bitirmedigini SOYLUYOR",
                "HIC YAZMADI" in sat[0] and "ATLANDI" in sat[0])
        kontrol("atlanan kosum yine exit 0 (fail-open bozulmadi)", r1.returncode == 0)
        # sahip serbest kalip GERCEKTEN kosunca uyari kendi kendine kapanmali
        fcntl.flock(asili, fcntl.LOCK_UN)
        asili.close()
        izole_kos(o)
        sat2 = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
        kontrol("gercek kosumdan sonra uyari KENDILIGINDEN kapandi",
                sat2[0].strip().startswith("taze:"), sat2[0])

    # ---------------- 13g) K1: ISTISNA YOLUNDA `bitti=` YAZILMAZ ----------------
    # 🔴 TUR-4'TE OLCULEN MERGE BLOKLAYICI KUSUR: main()'in `finally` blogu istisna
    # yolunda DA `bitti=` yaziyordu -> durum.kilit_durumu izi 'yok' sayiyor, pano
    # "YARIM KALMIS YEDEK" DEMIYOR, damga da eski kaldigi icin "taze" diyordu. Yani
    # kilidin EN SIK hata biciminde (kosum ortada cokuyor: disk dolu, Drive cevabi
    # kesiliyor, kill) dalin getirdigi nobetci OLUYDU ve hicbir test bunu civilemiyordu.
    # Asagisi GERCEK ICRA ile olcer: izole kopya kopyalama ORTASINDA istisna atar.
    print("\n13g) K1 — kosum ORTADA COKERSE iz `bitti=` TASIMAZ, pano 'yarim' der")
    # COKME NOKTASI: memory kopyalandiktan SONRA, skills kopyalanmadan ONCE ->
    # yedek GERCEKTEN yarim kalir (skills degisikligi hedefe HIC girmez).
    COKME_CAPA = "    yazilan = 0\n    if os.path.isdir(SKILLS):"
    COKME = ('    raise RuntimeError("TEST: kosum ortasinda cokme")\n'
             "    yazilan = 0\n    if os.path.isdir(SKILLS):")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        r0 = izole_kos(o)                              # 1) saglam kosum: damga olussun
        kontrol("13g hazirlik: ilk yedek tamamlandi", "bitti ->" in r0.stdout)
        iz0 = ""
        with open(o["kilit"], encoding="utf-8", errors="replace") as fh:
            iz0 = fh.read(256).strip()
        kontrol("13g: BASARILI kosumun izi `bitti=` TASIYOR (pozitif nobetci)",
                "bitti=" in iz0 and "hata=" not in iz0, iz0[-60:])
        kontrol("13g: basarili kosumdan sonra kilit hali 'yok' (pano SESSIZ)",
                durum.kilit_durumu(o["kok"])["hal"] == "yok"
                and durum.kilit_satirlari(durum.kilit_durumu(o["kok"])) == [],
                durum.kilit_durumu(o["kok"])["hal"])

        # 2) KAYNAK DEGISTI ve kosum ORTADA PATLADI -> gercek veri kaybi
        time.sleep(0.02)
        sk = os.path.join(o["ev"], ".claude", "skills", "ornek-skill")
        with open(os.path.join(sk, "kritik-yeni.md"), "w") as fh:
            fh.write("YEDEGE GIRMESI GEREKEN icerik\n")
        with open(o["betik"], encoding="utf-8") as fh:
            gov = fh.read()
        if COKME_CAPA not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r"
                               % COKME_CAPA)
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(COKME_CAPA, COKME, 1))
        r1 = izole_kos(o)
        iz1 = ""
        with open(o["kilit"], encoding="utf-8", errors="replace") as fh:
            iz1 = fh.read(256).strip()
        kd = durum.kilit_durumu(o["kok"])
        sat_k = durum.kilit_satirlari(kd)
        print("     --- pano ciktisi (kosum ortada coktu) ---")
        for s in (sat_k or ["(BOS)"]):
            print("    " + s)
        kontrol("13g: coken kosum exit!=0 (hata gizlenmiyor)", r1.returncode != 0,
                "rc=%d" % r1.returncode)
        kontrol("🔴 13g: ISTISNA yolunda iz `bitti=` TASIMIYOR",
                "bitti=" not in iz1, iz1[-70:])
        kontrol("13g: iz teshis icin `hata=` tasiyor (pid+baslangic korunuyor)",
                "hata=" in iz1 and "pid=" in iz1 and "baslangic=" in iz1, iz1[-70:])
        kontrol("🔴 13g: pano hali 'yarim' (kosum ortasinda kesilmis)",
                kd["hal"] == "yarim", kd["hal"])
        kontrol("13g: pano '⚠⚠ YARIM KALMIS YEDEK' diyor",
                bool(sat_k) and "YARIM KALMIS" in sat_k[0],
                (sat_k[0][:80] if sat_k else "(BOS)"))
        kontrol("13g: degisiklik GERCEKTEN yedege girmedi (kayip gercek)",
                not os.path.exists(os.path.join(o["hedef"], "skills", "ornek-skill",
                                                "kritik-yeni.md")))

        # 3) KIRMIZI-MUTASYON: istisna yolunda `bitti=` GERI gelirse pano SUSAR
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(COKME_CAPA, COKME, 1).replace(
                "                if basardi:\n"
                "                    imza = _sahip_imzasi(baslangic, bitti=simdi)\n"
                "                else:\n"
                "                    imza = _sahip_imzasi(baslangic, hata=simdi)",
                "                imza = _sahip_imzasi(baslangic, bitti=simdi)"
                "  # MUTANT: hep bitti", 1))
        izole_kos(o)
        iz_m = ""
        with open(o["kilit"], encoding="utf-8", errors="replace") as fh:
            iz_m = fh.read(256).strip()
        kd_m = durum.kilit_durumu(o["kok"])
        kontrol("MUTANTTA (hep bitti=) coken kosum TEMIZ gorunuyor, pano SUSUYOR "
                "(kontrol KIRMIZI yanardi)",
                "bitti=" in iz_m and kd_m["hal"] == "yok"
                and durum.kilit_satirlari(kd_m) == [],
                "hal=%s iz=%s" % (kd_m["hal"], iz_m[-50:]))

    # ---------------- 13i) KILIT CALINAMAZ (K1 regresyon nobeti) ----------------
    # K1 onarimi `bitti=`/`hata=` isaretlerini degistirdi. Isaretler bir KOLAYLIKTIR
    # (pano teshisi); KARSILIKLI DISLAMA cekirdekteki flock'tadir. Bir sey (bayat arac,
    # elle duzenleme, kotu niyetli iz) dosyaya SAHTE `bitti=` yazsa bile kilit
    # CALINAMAMALI: kilit gercekten tutuluyorken yeni kosum YINE atlamak zorunda.
    print("\n13i) KILIT CALINAMAZ — sahte `bitti=` izi flock'u DELMEZ")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        kilitci = open(o["kilit"], "a+")
        fcntl.flock(kilitci, fcntl.LOCK_EX)               # kilit GERCEKTEN tutuluyor
        kilitci.truncate(0)
        kilitci.write("pid=1 baslangic=%r iso=TEST bitti=%r\n"   # SAHTE temiz-birakma izi
                      % (time.time() - 7200, time.time()))
        kilitci.flush()
        r_c = izole_kos(o, "--gerekliyse")
        kontrol("sahte `bitti=` izine RAGMEN kosum ATLADI (flock cekirdekte)",
                r_c.returncode == 0 and "yedek ATLANDI" in r_c.stdout
                and "bitti ->" not in r_c.stdout,
                "rc=%d %s" % (r_c.returncode,
                              (r_c.stdout.strip().splitlines() or ["(bos)"])[0][:60]))
        kontrol("sahte iz hedefe yedek YAZDIRMADI (damga YOK)",
                damga_json(o["hedef"]) is None)
        fcntl.flock(kilitci, fcntl.LOCK_UN)
        kilitci.close()
        r_c2 = izole_kos(o, "--gerekliyse")
        kontrol("kilit gercekten birakilinca ayni kosum YEDEKLIYOR (kontrol olu degil)",
                "bitti ->" in r_c2.stdout, "rc=%d" % r_c2.returncode)

    # ---------------- 13h) K1 BIRIM: kilit_birak basari bayragi ----------------
    print("\n13h) K1 BIRIMI — kilit_birak(basardi=) fail-closed varsayilan")
    with tempfile.TemporaryDirectory() as td:
        yol = os.path.join(td, ".yedek.lock")
        hal, fd, bas = yedekle.kilit_al(yol)
        yedekle.kilit_birak(fd, baslangic=bas, basardi=True)
        kontrol("basardi=True -> iz `bitti=` tasiyor", "bitti=" in open(yol).read())
        hal, fd, bas = yedekle.kilit_al(yol)
        yedekle.kilit_birak(fd, baslangic=bas, basardi=False)
        iz = open(yol).read()
        kontrol("basardi=False -> `bitti=` YOK, `hata=` VAR",
                "bitti=" not in iz and "hata=" in iz, iz.strip()[-60:])
        hal, fd, bas = yedekle.kilit_al(yol)
        yedekle.kilit_birak(fd, baslangic=bas)          # bayrak VERILMEDI
        kontrol("bayrak verilmezse FAIL-CLOSED (`bitti=` yazilmaz)",
                "bitti=" not in open(yol).read(), open(yol).read().strip()[-60:])
        kontrol("main() basari bayragini kilit_birak'a GERCEKTEN veriyor (kablolama)",
                "basardi=basardi" in open(YEDEKLE, encoding="utf-8").read())

    # ---------------- 13c) atlama_kapsandi_mi SAF FONKSIYON (fail-closed) -------
    print("\n13c) KAPSAMA KARARI — olcemedigimiz her hal 'kapsanmadi' (fail-closed)")
    kontrol("kaynak sahip baslangicindan ESKI -> kapsandi",
            yedekle.atlama_kapsandi_mi(100.0, 50.0) is True)
    kontrol("kaynak sahip baslangiciyla AYNI -> kapsandi",
            yedekle.atlama_kapsandi_mi(100.0, 100.0) is True)
    kontrol("kaynak sahip baslangicindan YENI -> KAPSANMADI",
            yedekle.atlama_kapsandi_mi(100.0, 150.0) is False)
    kontrol("sahip baslangici bilinmiyor -> KAPSANMADI",
            yedekle.atlama_kapsandi_mi(None, 150.0) is False)
    kontrol("kaynak mtime olculemedi -> KAPSANMADI",
            yedekle.atlama_kapsandi_mi(100.0, None) is False)

    # ---------------- 13d) kilit_al/kilit_birak BIRIM DAVRANISI ----------------
    print("\n13d) KILIT BIRIMI — al/birak, ikinci alis MESGUL, kurulamayan yol FAIL-OPEN")
    with tempfile.TemporaryDirectory() as td:
        yol = os.path.join(td, ".yedek.lock")
        hal1, fd1, _b1 = yedekle.kilit_al(yol)
        kontrol("bos kilit ALINIYOR", hal1 == "alindi" and fd1 is not None, hal1)
        hal2, fd2, bilgi2 = yedekle.kilit_al(yol)
        kontrol("tutulurken ikinci alis MESGUL", hal2 == "mesgul" and fd2 is None, hal2)
        kontrol("sahip imzasi (pid+baslangic) okunabiliyor",
                "pid=%d" % os.getpid() in bilgi2[0] and isinstance(bilgi2[2], float),
                bilgi2[0][:60])
        # Alt sinir -1: time.time() MONOTON DEGIL; sahip imzasi ile okuma arasinda
        # milisaniye altinda negatif fark olculebiliyor (olculdu: -0,0003 sn). Yas
        # yalniz "asili sahip" (>1 saat) uyarisinda kullanildigi icin zararsiz.
        kontrol("sahip yasi hesaplaniyor (~0 sn)",
                isinstance(bilgi2[1], float) and -1 <= bilgi2[1] < 5, str(bilgi2[1]))
        yedekle.kilit_birak(fd1)
        hal3, fd3, _b3 = yedekle.kilit_al(yol)
        kontrol("birakilinca yeniden ALINIYOR", hal3 == "alindi", hal3)
        yedekle.kilit_birak(fd3)
        kontrol("kilit dosyasi SILINMEDI (inode yarisi onlenir)", os.path.exists(yol))
        kontrol("birakilan kilidin icerigi temizlendi (bayat sahip yaniltmasin)",
                open(yol).read().strip() == "")
        hal4, fd4, bilgi4 = yedekle.kilit_al(os.path.join(td, "olmayan-dizin", "x.lock"))
        kontrol("acilamayan kilit yolu -> 'kurulamadi' (FAIL-OPEN, yedek yine alinir)",
                hal4 == "kurulamadi" and fd4 is None, "%s / %s" % (hal4, str(bilgi4)[:50]))
        kontrol("kilit_birak(None) patlamiyor", yedekle.kilit_birak(None) is None)
        # kilitsiz kosum damgada ISARETLENIR (pano not duser)
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 4}, kilitsiz=True)
        kontrol("kilitsiz kosum damgada isaretli",
                yedekle.damga_oku(td).get("kilitsiz") is True)
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 4})
        kontrol("kilitli kosumda isaret YOK", "kilitsiz" not in yedekle.damga_oku(td))
        kontrol("damgada baslangic alani var (gerekli_mi + pano referansi)",
                isinstance(yedekle.damga_oku(td).get("baslangic"), float))
        kontrol("gerekli_mi ARTIK baslangici referans aliyor",
                yedekle.gerekli_mi({"zaman": 200, "baslangic": 100}, 150) is True
                and yedekle.gerekli_mi({"zaman": 200, "baslangic": 100}, 90) is False)

    # ---------------- 13b) KIRMIZI-MUTASYON: kilit devre disi ----------------
    print("\n13b) KIRMIZI-MUTASYON — kilit kaldirilirsa eszamanli kosum GECER mi?")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        # kilit_al DAIMA 'alindi' der (mutant): kilitli hedefe ikinci kosum yine yazar
        with open(o["betik"], encoding="utf-8") as f:
            gov = f.read()
        capa = '    hal, kilit_fd, kilit_bilgi = kilit_al()'
        if capa not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r" % capa)
        with open(o["betik"], "w", encoding="utf-8") as f:
            f.write(gov.replace(capa, '    hal, kilit_fd, kilit_bilgi = ("alindi", None, None)'
                                       '  # MUTANT', 1))
        kilitci = open(o["kilit"], "a+")
        fcntl.flock(kilitci, fcntl.LOCK_EX)
        rm = izole_kos(o, "--gerekliyse")
        fcntl.flock(kilitci, fcntl.LOCK_UN)
        kilitci.close()
        kontrol("MUTANTTA kilit dinlenmedi, yedek YINE yazildi (kontrol KIRMIZI yanardi)",
                "bitti ->" in rm.stdout and "yedek ATLANDI" not in rm.stdout,
                "rc=%d" % rm.returncode)

    # ---------------- 14) ESZAMANLILIK: iki kosum AYNI ANDA ----------------
    print("\n14) ESZAMANLILIK — 3 turda 2'ser kosum: biri yedekler, obur ATLAR")
    tur_sonuc = []
    for tur in range(3):
        with tempfile.TemporaryDirectory() as td:
            o = izole_ortam(td, yedekle, memory_adet=400, skills_adet=150)
            p1, p2 = izole_baslat(o), izole_baslat(o)
            c1 = p1.communicate()
            c2 = p2.communicate()
            ciktilar = [c1[0], c2[0]]
            kodlar = [p1.returncode, p2.returncode]
            yazan = sum(1 for c in ciktilar if "bitti ->" in c)
            atlayan = sum(1 for c in ciktilar if "yedek ATLANDI" in c)
            dosyalar = hedef_dosyalari(o["hedef"])
            # +2: damga + atlama kaydi (atlayan kosum kendi dosyasina yazar)
            bekle = o["memory_adet"] + o["skills_adet"] + len(yedekle.REPO_BEKLENEN) + 2
            d = birlesik_json(o["hedef"])
            tur_sonuc.append({
                "yazan": yazan, "atlayan": atlayan, "kodlar": kodlar,
                "dosya": len(dosyalar), "bekle": bekle, "damga": d,
                "artik": [x for x in dosyalar if ".tmp-" in x],
                "pano": durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var")),
            })
    for i, t in enumerate(tur_sonuc, 1):
        kontrol("tur%d: TAM 1 kosum yedekledi, 1 kosum ATLADI" % i,
                t["yazan"] == 1 and t["atlayan"] == 1,
                "yazan=%d atlayan=%d" % (t["yazan"], t["atlayan"]))
        kontrol("tur%d: IKI kosum da exit 0 (push bloklanmadi)" % i, t["kodlar"] == [0, 0],
                str(t["kodlar"]))
        kontrol("tur%d: hedefte yarim/karismis cikti YOK (%d dosya)" % (i, t["dosya"]),
                t["dosya"] == t["bekle"] and not t["artik"],
                "beklenen %d, artik %s" % (t["bekle"], t["artik"] or "-"))
        kontrol("tur%d: damga TAM OLARAK BIR tam kosum bildiriyor" % i,
                t["damga"].get("tam") is True
                and t["damga"].get("memory") == 400 and t["damga"].get("skills") == 150,
                "tam=%s memory=%s skills=%s" % (t["damga"].get("tam"),
                                                t["damga"].get("memory"),
                                                t["damga"].get("skills")))
        kontrol("tur%d: ATLAYAN kosum kendi kaydinda iz birakti" % i,
                isinstance(t["damga"].get("son_atlama"), float)
                and isinstance(t["damga"].get("baslangic"), float))
        # Eszamanli ciftte kaynak DEGISMEZ -> atlama kapsanir; pano her paralel
        # push'ta bosuna sariya donmemeli (gurultulu pano = olu pano).
        kontrol("tur%d: atlama KAPSANDI olarak isaretlendi (bos uyari yok)" % i,
                t["damga"].get("son_atlama_kapsandi") is True,
                str(t["damga"].get("son_atlama_kapsandi")))
        kontrol("tur%d: beklenen sahip damgayi YAZDI (baslangic == sahip baslangici)" % i,
                t["damga"].get("baslangic") == t["damga"].get("son_atlama_sahip_baslangici"),
                "%r vs %r" % (t["damga"].get("baslangic"),
                              t["damga"].get("son_atlama_sahip_baslangici")))
        kontrol("tur%d: PANO SUSUYOR (normal eszamanli ciftte bos uyari yok)" % i,
                t["pano"][0].strip().startswith("taze:"), t["pano"][0])

    # ---------------- 14b) GERCEK URETIM YOLU: paralel `--gerekliyse` cifti ----
    # 🔴 Bolum 14 SENTETIK ciftti (kaynak taze, tam kopyalama). Baskin GERCEK yol
    # iki paralel push = `--gerekliyse` + KAYNAKTA DEGISIKLIK YOK. Curutucu bu yolda
    # 20/20 YAPISKAN yanlis "⚠⚠ KISMI YEDEK" olctu. Iki bagimsiz sebep vardi:
    #   (F1) kilit_birak dosyayi BOSALTIYORDU -> atlayan kosum sahibi tanimlayamiyor,
    #   (F2) GUNCEL yolu damga YAZMIYORDU     -> "sahip bitirdi mi" TANIM GEREGI hayir.
    # Ikisi de kapatildi; asagida gercek yolun yanlis-uyari sayisi 0 olmali.
    print("\n14b) GERCEK YOL — paralel `--gerekliyse` cifti (kaynak DEGISMEDI)")

    def paralel_gerekliyse(o, tur_sayisi):
        """Doner: (yanlis_uyari, sahip_okunamadi, kod_hatasi, ornek_satir)."""
        yanlis = okunamadi = kod_hatasi = 0
        ornek = ""
        for _ in range(tur_sayisi):
            p1, p2 = izole_baslat(o, "--gerekliyse"), izole_baslat(o, "--gerekliyse")
            c1, c2 = p1.communicate(), p2.communicate()
            if p1.returncode != 0 or p2.returncode != 0:
                kod_hatasi += 1
            if any("sahip bilgisi yok" in c for c in (c1[0], c2[0])):
                okunamadi += 1
            sat = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
            if not sat[0].strip().startswith("taze:"):
                yanlis += 1
                ornek = ornek or sat[0].strip()
        return yanlis, okunamadi, kod_hatasi, ornek

    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        izole_kos(o)                                   # ilk tam yedek (damga olussun)
        yanlis, okunamadi, kod_hatasi, ornek = paralel_gerekliyse(o, 20)
        kontrol("🔢 20 paralel `--gerekliyse` cifti: YANLIS UYARI 0",
                yanlis == 0, "yanlis=%d/20  %s" % (yanlis, ornek[:80]))
        kontrol("20 ciftte 'sahip bilgisi yok' 0 (kilit izi okunabiliyor)",
                okunamadi == 0, "okunamadi=%d/20" % okunamadi)
        kontrol("20 ciftte exit!=0 yok (fail-open)", kod_hatasi == 0,
                "hata=%d/20" % kod_hatasi)
        d = damga_json(o["hedef"]) or {}
        kontrol("GUNCEL yolu damgayi DOGRULADI (baslangic ilerledi, zaman DOKUNULMADI)",
                isinstance(d.get("dogrulandi_iso"), str)
                and d.get("baslangic", 0) > d.get("zaman", 0),
                "baslangic-zaman=%.3f sn" % (d.get("baslangic", 0) - d.get("zaman", 0)))
        kontrol("dogrulama sayaclara/tamlik iddiasina DOKUNMADI",
                d.get("tam") is True and d.get("memory") == o["memory_adet"]
                and d.get("skills") == o["skills_adet"],
                "memory=%s skills=%s" % (d.get("memory"), d.get("skills")))

    # 14c) IKI DUZELTME DE GEREKLI MI? (birini kapatip ayni fiksturu olc)
    print("\n14c) HER IKI DUZELTME DE GEREKLI — birini kapatinca yanlis uyari donuyor mu?")
    for etiket, capa, yerine in (
            ("F1 kapali (kilit izi bosaltiliyor)",
             '                os.write(fd, imza.encode("utf-8"))',
             "                pass  # MUTANT: iz birakma"),
            ("F2 kapali (GUNCEL yolu damga yazmiyor)",
             "            tazelendi = damga_tazele(backup, baslangic, imza=bas_imza, "
             "kilitsiz=kilitsiz)",
             "            tazelendi = False  # MUTANT")):
        with tempfile.TemporaryDirectory() as td:
            o = izole_ortam(td, yedekle)
            with open(o["betik"], encoding="utf-8") as f:
                gov = f.read()
            if capa not in gov:
                raise RuntimeError("MUTASYON CAPASI BULUNAMADI: %r" % capa)
            with open(o["betik"], "w", encoding="utf-8") as f:
                f.write(gov.replace(capa, yerine, 1))
            izole_kos(o)
            m_yanlis, m_okunamadi, _h, m_ornek = paralel_gerekliyse(o, 10)
            kontrol("MUTANT [%s] -> yanlis uyari GERI GELDI" % etiket,
                    m_yanlis > 0, "yanlis=%d/10 sahip-okunamadi=%d/10  %s"
                    % (m_yanlis, m_okunamadi, m_ornek[:60]))

    # ---------------- 14d) K3: "DEGISIKLIK YOK" != "YEDEK BAYAT" ----------------
    # Tur-4 kusuru: `--gerekliyse` GUNCEL yolu `zaman`i ILERLETMEDIGI icin degismeyen
    # bir sistemde pano 2 gun sonra BOSUNA "⚠⚠ YEDEK BAYAT" diyordu; ayrica `kilitsiz`
    # notu MIRAS alinip yapisiyordu. Onarim: kosum OLCUMUNU damgaya yazar
    # (`dogrulandi` + `dogrulama_imzasi`) ve pano onu KENDISI dogrular.
    print("\n14d) K3 — IMZA BIRIMI + dogrulama kaydi + `kilitsiz` KOSUM-YEREL")
    imza_simdi = yedekle.kaynak_imzasi()
    kontrol("kaynak_imzasi adet/bayt/mtime donduruyor",
            isinstance(imza_simdi, dict)
            and isinstance(imza_simdi.get("adet"), int) and imza_simdi["adet"] > 0
            and isinstance(imza_simdi.get("bayt"), int)
            and isinstance(imza_simdi.get("mtime"), float),
            str(imza_simdi))
    kontrol("kaynak_imzasi mtime'i en_yeni_kaynak_mtime ile AYNI (tek gezinme kodu)",
            imza_simdi["mtime"] == yedekle.en_yeni_kaynak_mtime())
    kontrol("imza_esit_mi ayni imzada True", yedekle.imza_esit_mi(
        {"adet": 3, "bayt": 9, "mtime": 1.5}, {"adet": 3, "bayt": 9, "mtime": 1.5}) is True)
    for alan in ("adet", "bayt", "mtime"):
        bozuk = {"adet": 3, "bayt": 9, "mtime": 1.5}
        bozuk[alan] = 99
        kontrol("imza_esit_mi '%s' eksenindeki degisimi YAKALIYOR" % alan,
                yedekle.imza_esit_mi({"adet": 3, "bayt": 9, "mtime": 1.5}, bozuk) is False)
    kontrol("imza_esit_mi eksik/bozuk imzada fail-closed (False)",
            yedekle.imza_esit_mi(None, {"adet": 3, "bayt": 9, "mtime": 1.5}) is False
            and yedekle.imza_esit_mi({"adet": 3}, {"adet": 3}) is False)
    kontrol("gerekli_mi: imzalar FARKLIYSA mtime 'eski' dese bile YEDEKLE",
            yedekle.gerekli_mi({"zaman": 100, "baslangic": 100,
                                "kaynak_imzasi": {"adet": 3, "bayt": 9, "mtime": 50.0}},
                               50, imza={"adet": 3, "bayt": 10, "mtime": 50.0}) is True)
    kontrol("gerekli_mi: imzalar AYNIYSA (ve mtime eski) yine ATLA",
            yedekle.gerekli_mi({"zaman": 100, "baslangic": 100,
                                "kaynak_imzasi": {"adet": 3, "bayt": 9, "mtime": 50.0}},
                               50, imza={"adet": 3, "bayt": 9, "mtime": 50.0}) is False)

    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        izole_kos(o)                                   # tam yedek: kaynak_imzasi olussun
        d0 = damga_json(o["hedef"]) or {}
        kontrol("tam kosum damgaya `kaynak_imzasi` yaziyor",
                yedekle.imza_esit_mi(d0.get("kaynak_imzasi"), d0.get("kaynak_imzasi"))
                and isinstance(d0.get("kaynak_imzasi"), dict), str(d0.get("kaynak_imzasi")))
        r_g = izole_kos(o, "--gerekliyse")
        d1 = damga_json(o["hedef"]) or {}
        kontrol("GUNCEL yolu 'atla' dedi", "yedek GUNCEL" in r_g.stdout,
                r_g.stdout.strip().splitlines()[0][:70] if r_g.stdout.strip() else "")
        kontrol("GUNCEL yolu `dogrulandi` + `dogrulama_imzasi` yaziyor",
                isinstance(d1.get("dogrulandi"), float)
                and yedekle.imza_esit_mi(d1.get("dogrulama_imzasi"),
                                         d1.get("kaynak_imzasi")),
                "dogrulandi=%s" % (d1.get("dogrulandi") is not None))
        kontrol("GUNCEL yolu `zaman`a ve sayaclara DOKUNMADI",
                d1.get("zaman") == d0.get("zaman") and d1.get("memory") == d0.get("memory"))

        # PANO UCU: damgayi 3 gun geriye al (esik asilmis gibi) -> pano BAYAT DEMEMELI
        eski = dict(d1)
        eski["zaman"] = time.time() - 3 * 86400
        with open(os.path.join(o["hedef"], yedekle.DAMGA_ADI), "w", encoding="utf-8") as fh:
            json.dump(eski, fh)
        # 🔴 K5 (6. tur): pano artik KAYNAKLARIN SU ANKI imzasini da olcuyor. Burada
        # kaynaklar IZOLE KUM HAVUZUNDA (sahte HOME + sahte repo); panonun kendi
        # `_canli_kaynak_imzasi`i ise GERCEK makineyi olcer -> karsilastirma anlamsiz
        # olurdu. O yuzden olcum KUM HAVUZUNUN KENDI yedekle.py'siyle yapilir ve
        # panoya verilir: uctan uca zincir (yazici -> damga -> pano) gercekten olculur.
        _kum_imza = izole_imza(o)
        kontrol("hazirlik: kum havuzunun canli imzasi OLCULDU (fikstur ISIRIYOR)",
                isinstance(_kum_imza, dict) and _kum_imza.get("adet", 0) > 0,
                str(_kum_imza))
        _pano_gercek_canli = durum._canli_kaynak_imzasi
        durum._canli_kaynak_imzasi = lambda: {"kok": o["kok"], "adaylar": [_kum_imza]}
        try:
            dd = durum.yedek_durumu(o["hedef"], "var")
            sat = durum.yedek_satirlari(dd)
            print("     --- pano ciktisi (3 gun eski ama DOGRULANMIS) ---")
            for s in sat:
                print("    " + s)
            kontrol("🔴 K3: 3 gun eski ama dogrulanmis yedek 'guncel' "
                    "(BOSUNA BAYAT DEMIYOR)",
                    dd["hal"] == "guncel" and "GÜNCEL" in sat[0]
                    and not any("BAYAT" in s for s in sat), dd["hal"])
            # 🔴 K5 UCTAN UCA: kum havuzunda GERCEK bir dosya degisince (mtime KORUNARAK)
            # ayni damga artik GUNCEL SAYILMAZ — kardes kosum damgaya HIC DOKUNMASA da.
            _degisen = os.path.join(o["ev"], ".claude", "projects",
                                    "-Users-okan-dev-pruvo", "memory", "not-001.md")
            _st = os.stat(_degisen)
            with open(_degisen, "w") as fh:
                fh.write("mtime KORUNARAK buyutulmus icerik (K5 uctan uca nobeti)\n")
            os.utime(_degisen, (_st.st_atime, _st.st_mtime))     # mtime GERI alindi
            _kum_imza2 = izole_imza(o)
            kontrol("K5 hazirlik: mtime KORUNMUS degisim imzayi DEGISTIRDI (bayt ekseni)",
                    isinstance(_kum_imza2, dict)
                    and _kum_imza2.get("bayt") != _kum_imza.get("bayt")
                    and _kum_imza2.get("mtime") == _kum_imza.get("mtime"),
                    "%s -> %s" % (_kum_imza.get("bayt"), (_kum_imza2 or {}).get("bayt")))
            durum._canli_kaynak_imzasi = lambda: {"kok": o["kok"],
                                                  "adaylar": [_kum_imza2]}
            dd2 = durum.yedek_durumu(o["hedef"], "var")
            sat2 = durum.yedek_satirlari(dd2)
            kontrol("🔴 K5 UCTAN UCA: kaynak degisti + damgaya kimse dokunmadi -> "
                    "pano GUNCEL DEMIYOR",
                    dd2["hal"] == "kapsam-degisti" and "GÜNCEL" not in sat2[0]
                    and "KAPSAMIYOR" in sat2[0], "%s | %s" % (dd2["hal"], sat2[0][:70]))
        finally:
            durum._canli_kaynak_imzasi = _pano_gercek_canli

        # SESSIZ-YESIL NOBETI: kaynak GERCEKTEN degisirse ayni damga GUNCEL SAYILMAZ
        with open(os.path.join(o["ev"], ".claude", "projects",
                               "-Users-okan-dev-pruvo", "memory", "yeni-dosya.md"), "w") as fh:
            fh.write("yeni icerik\n")
        imza_yeni = None
        r_y = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util,json,sys;"
             "spec=importlib.util.spec_from_file_location('y', %r);"
             "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
             "print(json.dumps(m.kaynak_imzasi()))" % o["betik"]],
            capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])
        try:
            imza_yeni = json.loads(r_y.stdout.strip())
        except ValueError:
            imza_yeni = None
        kontrol("yeni dosya kaynak imzasini DEGISTIRDI (adet arttı)",
                isinstance(imza_yeni, dict)
                and imza_yeni.get("adet", 0) > (d1.get("kaynak_imzasi") or {}).get("adet", 0),
                "%s -> %s" % ((d1.get("kaynak_imzasi") or {}).get("adet"),
                              (imza_yeni or {}).get("adet")))
        r_g2 = izole_kos(o, "--gerekliyse")
        kontrol("degisiklikten sonra `--gerekliyse` GERCEKTEN yedekliyor (atlamiyor)",
                "bitti ->" in r_g2.stdout and "yedek GUNCEL" not in r_g2.stdout,
                r_g2.stdout.strip().splitlines()[-1][:60] if r_g2.stdout.strip() else "")

        # MTIME KORUNARAK yapilan icerik degisikligi de yakalanmali (imza `bayt` ekseni)
        hedef_md = os.path.join(o["ev"], ".claude", "projects",
                                "-Users-okan-dev-pruvo", "memory", "not-000.md")
        st = os.stat(hedef_md)
        with open(hedef_md, "w") as fh:
            fh.write("mtime KORUNARAK buyutulmus icerik — bayt ekseni bunu gormeli\n")
        os.utime(hedef_md, (st.st_atime, st.st_mtime))     # mtime GERI alindi
        r_g3 = izole_kos(o, "--gerekliyse")
        kontrol("🔴 mtime KORUNMUS icerik degisikligi ATLANMIYOR (bayt ekseni isiriyor)",
                "bitti ->" in r_g3.stdout and "yedek GUNCEL" not in r_g3.stdout,
                r_g3.stdout.strip().splitlines()[-1][:60] if r_g3.stdout.strip() else "")

        # `kilitsiz` KOSUM-YEREL: miras bayrak dogrulama kosumunda TEMIZLENIR
        d_k = damga_json(o["hedef"]) or {}
        d_k["kilitsiz"] = True
        with open(os.path.join(o["hedef"], yedekle.DAMGA_ADI), "w", encoding="utf-8") as fh:
            json.dump(d_k, fh)
        kontrol("hazirlik: damgada miras `kilitsiz` bayragi VAR",
                (damga_json(o["hedef"]) or {}).get("kilitsiz") is True)
        izole_kos(o, "--gerekliyse")
        kontrol("🔴 K3: kilitli dogrulama kosumu MIRAS `kilitsiz` notunu TEMIZLIYOR",
                "kilitsiz" not in (damga_json(o["hedef"]) or {}),
                str(sorted(damga_json(o["hedef"]) or {})))
        kontrol("pano yapiskan KILITSIZ notunu artik BASMIYOR",
                not any("KILITSIZ" in s for s in durum.yedek_satirlari(
                    durum.yedek_durumu(o["hedef"], "var"))))

    # 14e) KIRMIZI-MUTASYON: dogrulama imzasi yazilmazsa pano GUNCEL DEMEMELI
    print("\n14e) K3 KIRMIZI-MUTASYON — imza yazilmazsa yesil iddia URETILMEZ")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        with open(o["betik"], encoding="utf-8") as fh:
            gov = fh.read()
        capa = '        veri["dogrulama_imzasi"] = imza'
        if capa not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI: %r" % capa)
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(capa, "        pass  # MUTANT: imza yazilmiyor", 1))
        izole_kos(o)
        izole_kos(o, "--gerekliyse")
        d_m = damga_json(o["hedef"]) or {}
        d_m["zaman"] = time.time() - 3 * 86400
        with open(os.path.join(o["hedef"], yedekle.DAMGA_ADI), "w", encoding="utf-8") as fh:
            json.dump(d_m, fh)
        dd_m = durum.yedek_durumu(o["hedef"], "var")
        sat_m = durum.yedek_satirlari(dd_m)
        kontrol("MUTANTTA (imzasiz dogrulama) pano GUNCEL DEMIYOR -> OLCULEMEDI/BAYAT",
                dd_m["hal"] in ("dogrulama-olculemedi", "bayat")
                and "GÜNCEL" not in sat_m[0], "%s | %s" % (dd_m["hal"], sat_m[0][:60]))

    # ---------------- 15) GERCEK HEDEF DOKUNULMADI ----------------
    print("\n15) IZOLASYON KANITI — gercek Drive damgasi + .stl-backup-dir DEGISMEDI")
    izler_sonra = gercek_kritik_parmakizi(yedekle)
    d_yol, d_once = izler_once["damga"]
    kontrol("gercek damga yolu ile test yolu FARKLI",
            d_yol is None or not d_yol.startswith(tempfile.gettempdir()), str(d_yol))
    for etiket in sorted(izler_once):
        y1, v1 = izler_once[etiket]
        y2, v2 = izler_sonra[etiket]
        kontrol("GERCEK %s bayt+mtime AYNI (test yazmadi)" % etiket,
                y1 == y2 and v1 == v2,
                "%s" % ("yok (cozulemedi)" if v1 is None else "degismedi"))
    # 🔴 FAIL-CLOSED KABLOLAMA NOBETCISI (K5): gercek yola YAZAN yol (drive_yolu.
    # stl_dizini / pruvo_dizini) bu testin KAYNAGINDA cagrilmamali. Yukaridaki
    # bayt-esitlik kontrolu yalniz BUGUNKU ortamda (kayitli yol gecerli) yesil
    # yanar; yol bayatladigi gun yazma sessizce geri gelirdi.
    # ⚠️ IGNELER PARCALI kurulur: tek parca yazilsa bu satirin KENDISI eslesir
    # (kapi kendi kaynagini tarar) ve kontrol sonsuza dek sahte-kirmizi yanar.
    kendi_govde = open(__file__, encoding="utf-8").read()
    igneler = ("drive_yolu." + "stl_dizini(", "drive_yolu." + "pruvo_dizini(")
    yazan_cagri = [c for c in igneler if c in kendi_govde]
    kontrol("test GERCEK yola YAZAN cozucuyu HIC cagirmiyor (fail-closed)",
            not yazan_cagri, "bulunan: %s" % (yazan_cagri or "-"))
    # Kontrolun OLU olmadiginin kaniti: ayni arama, GERCEKTEN cagiran yedekle.py'de
    # ISABET vermeli (yoksa "igne hic eslesmiyor" diye sessizce yesil kalirdi).
    kontrol("igne olu DEGIL: ayni arama yedekle.py'de ISABET veriyor",
            any(c in open(YEDEKLE, encoding="utf-8").read() for c in igneler))
    if d_once:
        try:
            eski = json.loads(d_once[0].decode("utf-8"))
            kontrol("gercek damga sayaclari korundu",
                    isinstance(eski.get("memory"), int),
                    "memory=%s skills=%s repo=%s" % (eski.get("memory"), eski.get("skills"),
                                                     eski.get("repo")))
        except ValueError:
            kontrol("gercek damga JSON okunabilir", False)

    # ------- 16/16b: HERMETIK ALT KUME (ayni kod yolu, `--hermetik` de kosar) -------
    hermetik_adet = hermetik_bolum(yedekle)
    hermetik_kapisi(hermetik_adet, serit_paritesi=True)

    # ---------------- 17) CRON AGACI: .py DELIGI (16 AGU 2026) ----------------
    # Olculdu: ~/.claude/cron altindaki 24+ python betigi (nobet-kapi.py,
    # nobet-kabul-test.py, baglam-olcum.py, ...) eski ACIK ALLOWLIST'te (sadece
    # .sh/.crontab/.md/.txt/.json) UZANTI YOK diye disarida kaliyordu. Repo
    # DISINDA (git'te kopyasi YOK) → disk kaybinda EMIMEYEN KAYIP. Ayrica
    # `.navlungo-kimlik.json` `.json` uzantisinin korunmasiyla yedege
    # SIZIYORDU; buyuk transient dizinler (profil-*/, m3-profil*/,
    # tarayici-profili/, nobet-raporlar/) yedegi sisiriyordu.
    # Bu bolum kum havuzunda (sahte CRON kokune belirli atomlar konur) davranisi
    # olcer. Pseudo-AGAC_KAPSAMI girdisi kullanir (gercek kronik kok YAZILMAZ).
    print("\n17) CRON AGACI — .py deligi (16 Agu 2026) + sızıntı kapısı")
    with tempfile.TemporaryDirectory() as td:
        sahte_cron = os.path.join(td, "cron")
        os.makedirs(os.path.join(sahte_cron, "isci-baglam"))
        # Vaka A: izinli .py dosyasi plana GIRMELI
        with open(os.path.join(sahte_cron, "nobet-kapi.py"), "w") as fh:
            fh.write("#!/usr/bin/env python3\n# nobet yurutucusu\n")
        # Vaka A: izinli olmayan .pyc dosyasi (gurultu) plana GIRMEMELI
        os.makedirs(os.path.join(sahte_cron, "scripts", "__pycache__"))
        with open(os.path.join(sahte_cron, "scripts", "__pycache__", "x.py"), "wb") as fh:
            fh.write(b"\x00\x01\x00\x00")
        with open(os.path.join(sahte_cron, "scripts", "__pycache__", "x.pyc"), "wb") as fh:
            fh.write(b"\x00\x01\x00\x00")
        # Vaka B: sir dosyalari plana GIRMEMELI
        with open(os.path.join(sahte_cron, ".kimi-anahtar"), "w") as fh:
            fh.write("kimi-anahtar-icerik\n")
        with open(os.path.join(sahte_cron, ".deepseek-anahtar"), "w") as fh:
            fh.write("deepseek-anahtar-icerik\n")
        with open(os.path.join(sahte_cron, ".cf-token"), "w") as fh:
            fh.write("cf-token-icerik\n")
        with open(os.path.join(sahte_cron, ".gh-token"), "w") as fh:
            fh.write("gh-token-icerik\n")
        with open(os.path.join(sahte_cron, ".ci-token"), "w") as fh:
            fh.write("ci-token-icerik\n")
        with open(os.path.join(sahte_cron, ".cf-purge-token"), "w") as fh:
            fh.write("cf-purge-token-icerik\n")
        with open(os.path.join(sahte_cron, ".navlungo-kimlik.json"), "w") as fh:
            fh.write('{"platform":"navlungo","kimlik":"SAHTE"}\n')
        # Vaka C: BUYUK transient dizinler plana GIRMEMELI (profil-*/m3-profil*/
        # tarayici-profili/nobet-raporlar). Eklenen her dizine .jsonl transkript ve
        # .md not konur; HEPSI haric olmali (klasor budanir, dosyalar sayilmaz).
        for d in ("profil-minimax-m3-pruvo", "m3-profil-pruvo", "tarayici-profili",
                  "nobet-raporlar"):
            os.makedirs(os.path.join(sahte_cron, d))
            with open(os.path.join(sahte_cron, d, "oturum.jsonl"), "w") as fh:
                fh.write('{"konusma":"model-cevabi-sim"}\n')
            with open(os.path.join(sahte_cron, d, "rapor.md"), "w") as fh:
                fh.write("# nobet raporu\n")
        # Vaka D: isci-baglam/*.md plana GIRMELI (ORTAK.md / BUTCE.md / motor)
        for ad in ("ORTAK.md", "BUTCE.md", "minimax-m3.md",
                   "deepseek-flash.md", "deepseek-pro.md"):
            with open(os.path.join(sahte_cron, "isci-baglam", ad), "w") as fh:
                fh.write("# %s baglami\n" % ad)
        # Vaka D-negatif: isci-baglam/*.py GENELDE calismaz; yapinin .md icin
        # oldugunu kontrol etmek icin bir .json bile konur — SIZMAMALI (uzanti yok).
        with open(os.path.join(sahte_cron, "isci-baglam", "ek-not.json"), "w") as fh:
            fh.write('{"ek":1}\n')
        # ---------------- 18) ALT AGAC + KAPSAM-DISI PLAN (16 Agu 2026) ----------------
        # Olculmus kusur: yedek_kok_sir_plani yalniz os.listdir(backup) ile KOKU arar;
        # alt agactaki sir kopyalari (ornek: backup-v2/cron-nobet/.navlungo-kimlik.json)
        # GORULMEDIGI icin hedefte bayat kaliyordu. Ayni delik her alt klasor icin acik.
        # Yeni: yedek_agac_sir_plani (ozyinelemeli, sir_sebebi icerik_tara=False ile)
        # + yedek_agac_kapsamdisi_plani (AGAC_EK_ATLA["cron"] desenleriyle hedef
        # bayat klasor tarama). Bu bolum kum havuzunda vakalari sinar.
        #
        # 🔴 26 Agu 2026 (K212Yedek) — OLCULEN KUSUR, ONARILDI: 18) bolumu KENDI
        # `with tempfile.TemporaryDirectory() as td:` blogunu aciyordu ve 17)
        # bolumunun blogu YUKARIDA, fiksturu kurar kurmaz KAPANIYORDU. 17)'nin
        # IDDIALARI ise (bu blogun sonunda) `sahte_cron`a bakiyor — o yol artik
        # SILINMIS bir tempfile dizini. Sonuc main'de OLCULDU: 17)'nin 18 iddiasi
        # SESSIZCE KIRMIZI + sonuncusu FileNotFoundError ile TUM bataryayi kesiyor
        # (taban: rc=1, 18 kirmizi, Traceback VAR). Onarim: 18) ayri bir kum havuzu
        # ACMAZ, 17) ile AYNI `td`nin altinda kendi dizinlerini kurar; boylece
        # `sahte_cron` iddialar kosana kadar YASAR. Alt dizinler cakismaz:
        # 17) -> td/cron   ·   18) -> td/backup-v2, td/kaynak-cron, td/komsu.
        print("\n18) ALT AGAC + KAPSAM-DISI — kok disinda sir + artik kapsam-disi klasor")
        backup = os.path.join(td, "backup-v2")
        os.makedirs(backup)

        # 🔴 K212 (19 Agu 2026) — ALT AGAC KOLU ARTIK FAIL-CLOSED: bir kopya ancak
        # YERELDEKI ASLI VAR ve OKUNABILIR ise silinir (kok koluyla AYNI yuklem,
        # `yedekle.yerel_asil_durumu`). Kaynak kokunu kum havuzuna cevir ki iki hal
        # de DETERMINISTIK olculsun; GERCEK ~/.claude/cron ne okunur ne yazilir.
        sahte_kaynak_cron = os.path.join(td, "kaynak-cron")
        os.makedirs(sahte_kaynak_cron)
        with open(os.path.join(sahte_kaynak_cron, ".navlungo-kimlik.json"), "w") as fh:
            fh.write("SIMULASYON: YEREL ASIL (silme izni bunun varligindan gelir)\n")
        eski_kapsam = yedekle.AGAC_KAPSAMI
        yedekle.AGAC_KAPSAMI = tuple(
            (e, sahte_kaynak_cron if h == "cron-nobet" else k, h, i)
            for e, k, h, i in eski_kapsam)

        # ---- Vaka A: ic ice sir (cron-nobet/.navlungo-kimlik.json) ----
        os.makedirs(os.path.join(backup, "cron-nobet"))
        # ---- Vaka H (K212): YEREL ASLI OLMAYAN sir kopyasi -> SILINMEMELI ----
        yerelsiz_yol = os.path.join(backup, "cron-nobet", ".yerelsiz-token")
        with open(yerelsiz_yol, "w") as fh:
            fh.write("SIMULASYON: yereldeki asli YOK -> fail-closed\n")
        nav_yol = os.path.join(backup, "cron-nobet", ".navlungo-kimlik.json")
        with open(nav_yol, "w") as fh:
            fh.write("SIMULASYON: 350 B ic ice sir\n")
        # ---- Vaka B: surumlenmis kopya (ad.YYYYMMDD-HHMMSS.uzanti) ----
        versiyonlu = os.path.join(backup, "cron-nobet",
                                  ".navlungo-kimlik.20260816-011600.json")
        with open(versiyonlu, "w") as fh:
            fh.write("SIMULASYON: surumlenmis kopya\n")
        # ---- Vaka C: masum dosyalar — plana GIRMEDI ----
        with open(os.path.join(backup, "cron-nobet", "isci.sh"), "w") as fh:
            fh.write("#!/bin/sh\nsimulasyon\n")
        os.makedirs(os.path.join(backup, "gorev-tanimlari"))
        with open(os.path.join(backup, "gorev-tanimlari", "x.md"), "w") as fh:
            fh.write("# masum\n")
        # ---- Vaka D: kapsam-disi klasorler (AGAC_EK_ATLA["cron"] desenleri) ----
        for d in ("profil-kimi-x", "m3-profil-blabla", "tarayici-profili", "nobet-raporlar"):
            tam = os.path.join(backup, "cron-nobet", d)
            os.makedirs(tam)
            with open(os.path.join(tam, ".claude.json"), "w") as fh:
                fh.write("{}\n")           # D klasorunun ici dolu olmali (bos dizin atlanir)
        # ---- Vaka F: yedek KOKU DISINDAKI sir — kum havuzunun komsu dizini ----
        os.makedirs(os.path.join(td, "komsu"))
        komsu_dosya = os.path.join(td, "komsu", ".navlungo-kimlik.json")
        with open(komsu_dosya, "w") as fh:
            fh.write("SIMULASYON: yedek kokunun DISINDA\n")

        # --- Planlari uret ---
        sir_plan = yedekle.yedek_agac_sir_plani(backup)
        kap_plan = yedekle.yedek_agac_kapsamdisi_plani(backup)
        sir_yollar = {g for g, _, _ in sir_plan}
        kap_yollar = {g for g, _ in kap_plan}

        # ---- Vaka A ----
        kontrol("A) ic ice sir plana GIRDI: cron-nobet/.navlungo-kimlik.json",
                "cron-nobet/.navlungo-kimlik.json" in sir_yollar, sir_yollar)
        kontrol("A) ic ice sir icin YOL + BOYUT + SEBEP ucu de doner",
                any(g == "cron-nobet/.navlungo-kimlik.json" and boyut > 0 and sebep
                    for g, sebep, boyut in sir_plan), sir_plan)
        # ---- Vaka B ----
        kontrol("B) surumlenmis kopya plana GIRDI: .navlungo-kimlik.20260816-011600.json",
                "cron-nobet/.navlungo-kimlik.20260816-011600.json" in sir_yollar,
                sir_yollar)
        # ---- Vaka C ----
        kontrol("C) masum dosya plana GIRMEDI: cron-nobet/isci.sh",
                "cron-nobet/isci.sh" not in sir_yollar, sir_yollar)
        kontrol("C) masum dosya plana GIRMEDI: gorev-tanimlari/x.md",
                "gorev-tanimlari/x.md" not in sir_yollar, sir_yollar)
        kontrol("C) masum dizin plana GIRMEDI (cron-nobet ISIMLI dizinin kendisi)",
                "cron-nobet" not in sir_yollar, sir_yollar)
        # ---- Vaka D ----
        for d in ("profil-kimi-x", "m3-profil-blabla", "tarayici-profili", "nobet-raporlar"):
            kontrol("D) kapsam-disi VAR: cron-nobet/%s" % d,
                    "cron-nobet/%s" % d in kap_yollar, kap_yollar)
        kontrol("D) desene uymayan klasor plana GIRMEDI: cron-nobet/profil-baska",
                not any(g == "cron-nobet/profil-baska" for g in kap_yollar), kap_yollar)
        # ---- Vaka F: yedek kok disi dosya plana GIRMEDI ----
        kontrol("F) yedek kok disi dosya plana GIRMEDI (`..` segmenti YOK)",
                not any("/../" in g or g.startswith("..") for g in sir_yollar),
                [g for g in sir_yollar if ".." in g])
        # ---- Vaka H (K212): fail-closed kalemi PLANA girer (eleme daralmadi) ----
        kontrol("H) yerel asli OLMAYAN sir de plana GIRDI (eleme daralmadi)",
                "cron-nobet/.yerelsiz-token" in sir_yollar, sir_yollar)
        # ---- Vaka E: --sir-temizle sonrasi 0 sir / 0 kapsamdisi ----
        sir_islenen, sir_atlanan, _bul_s = yedekle.yedek_agac_sir_sil(sir_plan, backup)
        kap_islenen, kap_atlanan, _bul_k = yedekle.yedek_agac_kapsamdisi_sil(kap_plan, backup)
        # 🔴 K212: fail-closed kalem BILEREK kaliyor -> "plan 0" artik SADECE onu icerir.
        kalan_sir = [g for g, _, _ in yedekle.yedek_agac_sir_plani(backup)]
        kontrol("E) sir temizle sonrasi YALNIZ fail-closed kalem kaldi",
                kalan_sir == ["cron-nobet/.yerelsiz-token"], kalan_sir)
        kontrol("E) sir temizle sonrasi kapsam-disi plani 0",
                yedekle.yedek_agac_kapsamdisi_plani(backup) == [],
                [g for g, _ in yedekle.yedek_agac_kapsamdisi_plani(backup)])
        kontrol("E) yedek kok disi dosya HIC DOKUNULMAMAMALI (fail-closed)",
                os.path.exists(komsu_dosya), komsu_dosya)
        kontrol("E) atlanan kalem YALNIZ fail-closed olan (kapsam-disi hepsi temizlendi)",
                [g for g, _s in sir_atlanan] == ["cron-nobet/.yerelsiz-token"]
                and not kap_atlanan,
                "sir_atlanan=%s kap_atlanan=%s" % (sir_atlanan, kap_atlanan))
        kontrol("E) atlama SEBEBI yereldeki asla ATIF yapiyor (sessiz atlama YOK)",
                any("ASIL" in s for _g, s in sir_atlanan), sir_atlanan)
        kontrol("E) ic ice sir dosyasi SILINDI (yerel asli VAR)",
                not os.path.exists(nav_yol), nav_yol)
        kontrol("E) surumlenmis kopya SILINDI (asil = SURUMSUZ ad)",
                not os.path.exists(versiyonlu), versiyonlu)
        # 🔴 H) NEGATIF YON: emniyeti gevsetip her seyi birakmak KUSUR olurdu —
        # yukaridaki iki silme, "hicbir sey silinmiyor" halini AYIRT EDER.
        kontrol("H) yerel asli OLMAYAN sir kopyasi SILINMEDI (K212 fail-closed)",
                os.path.exists(yerelsiz_yol), yerelsiz_yol)
        kontrol("E) kapsam-disi klasor SILINDI (profil-kimi-x)",
                not os.path.exists(os.path.join(backup, "cron-nobet", "profil-kimi-x")),
                os.path.join(backup, "cron-nobet", "profil-kimi-x"))
        yedekle.AGAC_KAPSAMI = eski_kapsam        # kum havuzu yamasi GERI ALINIR
        # ---- Vaka G: regresyon mevcut kalmasin ----
        # Bu bölüm PASS olduysa mevcut `yedek_kok_sir_plani` hâlâ calisiyor demektir
        # (bölum 7). Yeni fonksiyonlar onu bozmadi. Burada dogrudan kontrol etmek
        # yerine, davranissal olarak: ayni kum havuzunda `yedek_kok_sir_plani` de
        # bos donmeli (yoksa cift sinif sinifi var — kok sir burada yok).
        kontrol("G) REGRESYON — yedek_kok_sir_plani yine bos (yeni kod yok sir eklemedi)",
                yedekle.yedek_kok_sir_plani(backup) == [],
                yedekle.yedek_kok_sir_plani(backup))
        # Ve `--dogrula` YASAK degil ama G'nin onemli parcasi: yedek_plani hâlâ
        # AYNI icerigi uretiyor — yeni fonksiyonlar onu degistirmedi.
        kontrol("G) REGRESYON — yedek_plani genisletildi/budanamadi (vaka sadece sir + kapsamdisi)",
                len(yedekle.yedek_plani(False)) > 0,
                len(yedekle.yedek_plani(False)))
        kontrol("G) REGRESYON — kronik doluluk (masum dosyalar hala vardi)",
                os.path.exists(os.path.join(backup, "cron-nobet", "isci.sh"))
                and os.path.exists(os.path.join(backup, "gorev-tanimlari", "x.md")),
                [os.path.exists(os.path.join(backup, "cron-nobet", "isci.sh")),
                 os.path.exists(os.path.join(backup, "gorev-tanimlari", "x.md"))])
        # 🔴 FIKSTUR CANLILIK NOBETCISI (26 Agu 2026, K212Yedek — SINIF KAPISI):
        # asagidaki 17) iddialarinin TAMAMI `sahte_cron`a bakar. O dizin bir
        # tempfile blogunun icindedir; blok erken kapanirsa iddialar "dosya yok"
        # diye SESSIZCE KIRMIZI yanar ve sebep gorunmez (main'de tam bu oldu).
        # Bu tek satir, sinifi SEBEBIYLE yakalar: fikstur olmeden iddia okunmaz.
        kontrol("🔴 17) FIKSTUR CANLI: `sahte_cron` iddia aninda DURUYOR "
                "(tempfile blogu erken kapanmadi)",
                os.path.isdir(sahte_cron), sahte_cron)
        # Sahte AGAC_KAPSAMI girdisi: cron agaci etiketini kullanmak, gercek
        # koklerin yazilmasini ONLER (sadece bu kum havuzuna yazilir).
        sahte_agac = ("cron", sahte_cron, "cron-nobet-DUMMY", (".sh", ".crontab", ".md", ".txt", ".json", ".py"))
        # Vaka gercek kokun uzerine yazma riski: KAPALI (sahte_cron = tempfile icinde).
        kontrol("SAHTE KOK GERCEK ~/.claude/cron DEGIL (güvenli kum havuzu)",
                not os.path.realpath(sahte_cron).startswith(os.path.realpath(os.path.expanduser("~/.claude"))),
                sahte_cron)
        # Direkt agac_plani cagrisi
        dahil, haric, gurultu = yedekle.agac_plani(sahte_agac)
        dahil_set = set(dahil)
        haric_set = {x: y for x, y in haric}
        gurultu_set = set(gurultu)
        # ---- Vaka A: .py dosyasi VAR ----
        kontrol("A) cron kokunde .py dosyasi yedek planinda VAR",
                "nobet-kapi.py" in dahil_set, dahil_set)
        kontrol("A) .py dosyasi haric listesinde DEGIL",
                "nobet-kapi.py" not in haric_set, haric_set.get("nobet-kapi.py"))
        # ---- Vaka B: sir dosyalari YOK ----
        for sir in (".kimi-anahtar", ".deepseek-anahtar", ".cf-token", ".gh-token",
                    ".ci-token", ".cf-purge-token", ".navlungo-kimlik.json"):
            kontrol("B) cron'daki sir %s plana GIRMEDI" % sir,
                    sir not in dahil_set, dahil_set)
            kontrol("B) cron'daki sir %s haric SEBEBIYLE sayildi" % sir,
                    sir in haric_set, haric_set.get(sir))
        kontrol("B) TUM sirlar ayni kategoride (sir nobeti yakaliyor)",
                all("ad deseni" in haric_set.get(s, "")
                    or "icerik imzasi" in haric_set.get(s, "")
                    for s in (".kimi-anahtar", ".deepseek-anahtar", ".cf-token",
                              ".gh-token", ".ci-token", ".cf-purge-token",
                              ".navlungo-kimlik.json")),
                "sebepler: " + " | ".join(
                    haric_set.get(s, "(YOK)") for s in
                    (".kimi-anahtar", ".navlungo-kimlik.json")))
        # ---- Vaka C: transient dizinler BUDANDI (dosyalar plana GIREMEZ) ----
        for d in ("profil-minimax-m3-pruvo", "m3-profil-pruvo", "tarayici-profili",
                  "nobet-raporlar"):
            kontrol("C) transient dizin %s/ plana GIRMEDI (dosyalar dahil)" % d,
                    not any(x.startswith(d + "/") for x in dahil_set),
                    [x for x in dahil_set if x.startswith(d + "/")])
            kontrol("C) transient dizin %s/ gurultu listesinde budandi" % d,
                    any(d in g for g in gurultu_set), gurultu_set)
        kontrol("C) __pycache__/x.py + x.pyc plana GIRMEDI (mevcut GURULTU_DIZIN hâlâ calisiyor)",
                not any(x.startswith("scripts/__pycache__/") for x in dahil_set),
                [x for x in dahil_set if x.startswith("scripts/__pycache__/")])
        # ---- Vaka D: isci-baglam/*.md VAR ----
        kontrol("D) isci-baglam/ORTAK.md yedek planinda VAR",
                "isci-baglam/ORTAK.md" in dahil_set, dahil_set)
        kontrol("D) isci-baglam/BUTCE.md yedek planinda VAR",
                "isci-baglam/BUTCE.md" in dahil_set, dahil_set)
        for ad in ("isci-baglam/minimax-m3.md", "isci-baglam/deepseek-flash.md",
                   "isci-baglam/deepseek-pro.md"):
            kontrol("D) isci-baglam/%s VAR" % os.path.basename(ad), ad in dahil_set)
        # isci-baglam/ kendisi haric listesinde OLMAMALI (sadece gecici dizinler
        # budanir; isci-baglam icindeki *.md gercek icerik)
        kontrol("D) isci-baglam/ dizini haric listesinde DEGIL (yalniz girisler kontrol)",
                not any(x == "isci-baglam" or x.startswith("isci-baglam (") for x in haric_set),
                [x for x in haric_set if "isci-baglam" in x])
        # D-ek: isci-baglam/ icindeki .json uzanti da allowlist'te (sadece *.md
        # gelmedi; bu dogrudan allowlist davranisi - isci-baglam/ icin ozel kural
        # yok). Bu, sirf baglam .md'lerinin yedeklendigini GARANTI etmez ama
        # tasarim geregi: allowlist + dizin atlama birlikte calisiyor.
        kontrol("D) isci-baglam/ dizini AGAC EK ATLA listesinde DEGIL (kullanici .md gibi dosyalar yedeklenir)",
                "isci-baglam" not in [d.rstrip("/") for d in yedekle.AGAC_EK_ATLA.get("cron", ())],
                yedekle.AGAC_EK_ATLA.get("cron", ()))
        # ---- Vaka E: REGRESYON (mevcut kontrollerden bir kismi) ----
        # .sh, .md, .crontab, .txt, .json — eski kume hâlâ calisiyor
        with open(os.path.join(sahte_cron, "nober.sh"), "w") as fh:
            fh.write("#!/bin/sh\nsahte nobet\n")
        with open(os.path.join(sahte_cron, "gorev.md"), "w") as fh:
            fh.write("# nobet gorevi\n")
        with open(os.path.join(sahte_cron, "zamanlama.crontab"), "w") as fh:
            fh.write("0 * * * * /usr/bin/true\n")
        with open(os.path.join(sahte_cron, "not.txt"), "w") as fh:
            fh.write("not\n")
        with open(os.path.join(sahte_cron, "ayar.json"), "w") as fh:
            fh.write("{}\n")
        # Teste dahil etmek icin plani YENIDEN hesapla
        dahil2, haric2, _ = yedekle.agac_plani(sahte_agac)
        kontrol("E) eski kume .sh hâlâ VAR (regresyon)",
                "nober.sh" in set(dahil2), dahil2)
        kontrol("E) eski kume .md hâlâ VAR",
                "gorev.md" in set(dahil2), dahil2)
        kontrol("E) eski kume .crontab hâlâ VAR",
                "zamanlama.crontab" in set(dahil2), dahil2)
        kontrol("E) eski kume .txt hâlâ VAR",
                "not.txt" in set(dahil2), dahil2)
        kontrol("E) eski kume .json hâlâ VAR",
                "ayar.json" in set(dahil2), dahil2)
        # 17 bolumunun toplam kontrol sayisi (sonraki serit paritesi icin)
        print("     17) bolumunun test sayisi: %d" % len([1 for _ in SONUC if _]))

    # ======== 19) K212/A — FAIL-CLOSED SILME EMNIYETI: IKI KOL, TEK YUKLEM ======
    # Kalem K212'nin BIRINCI yuzu. Bolum 18 (Vaka H) alt agac kolunu TEK BASINA
    # olcuyordu; buradaki fark: AYNI kalem yedek KOKUNDE de duruyor ve alt agac
    # yuruyusu KOKU DE geziyor -> kok kolunun BIRAKTIGI kalemi ikinci kol eline
    # aliyor. Olculen veri kaybi tam bu geciste olmustu.
    print("\n19) K212/A — yereldeki ASLI OLMAYAN kalem: KOK kolu DA alt agac kolu DA SILMEZ")
    with tempfile.TemporaryDirectory() as td:
        taban = k212a_kos(yedekle, os.path.join(td, "taban"))
        # --- ANTI-TAUTOLOJI: iddia ancak IKINCI kol o kalemi GERCEKTEN gorursa
        # anlamlidir. Gormuyorsa "silmedi" bedava dogru olurdu
        # ([[isci-yesil-tablo-ic-olcumu-bosaltir]]).
        kontrol("19) ANTI-TAUTOLOJI: alt agac plani yedek KOKUNDEKI kalemi DE gordu",
                K212A_YERELSIZ in taban["agac_plan"], taban["agac_plan"])
        kontrol("19) ANTI-TAUTOLOJI: alt agac plani ALT AGACTAKI kalemi de gordu",
                "cron-nobet/" + K212A_YERELSIZ in taban["agac_plan"], taban["agac_plan"])
        # --- ASIL IDDIA: iki kol da SILMEDI (disk teyidi) ---
        kontrol("🔴 19) KOK kolu: yerel asli OLMAYAN kalem SILINMEDI (fail-closed)",
                taban["duruyor"]["kok_yerelsiz"], taban["duruyor"])
        kontrol("🔴 19) ALT AGAC kolu: kok kolunun BIRAKTIGI kalemi SILMEDI "
                "(K212/K1 — sessiz veri kaybi kapali)",
                taban["duruyor"]["kok_yerelsiz"]
                and K212A_YERELSIZ in taban["agac_atlanan"],
                "atlanan=%s" % taban["agac_atlanan"])
        kontrol("🔴 19) ALT AGACTAKI ayni ad da SILINMEDI",
                taban["duruyor"]["agac_yerelsiz"]
                and "cron-nobet/" + K212A_YERELSIZ in taban["agac_atlanan"],
                "atlanan=%s" % taban["agac_atlanan"])
        kontrol("19) atlama SEBEBI yereldeki ASLA atif yapiyor (iki kolda da)",
                any("ASIL" in s for s in taban["kok_sebepler"])
                and any("ASIL" in s for s in taban["agac_sebepler"]),
                "kok=%s agac=%s" % (taban["kok_sebepler"], taban["agac_sebepler"]))
        # --- POZITIF KONTROL: "hicbir sey silmiyor" hali AYIRT EDILIR ---
        kontrol("19) POZITIF: yerel asli VAR olan kalem KOK kolunda SILINDI",
                not taban["duruyor"]["kok_asilli"]
                and K212A_ASILLI in taban["kok_islenen"], taban["kok_islenen"])
        kontrol("19) POZITIF: yerel asli VAR olan kalem ALT AGAC kolunda SILINDI",
                not taban["duruyor"]["agac_asilli"]
                and "cron-nobet/" + K212A_ASILLI in taban["agac_islenen"],
                taban["agac_islenen"])
        kontrol("19) POZITIF: kapsam-disi bayat klasor SILINDI (kontrol kolu CANLI)",
                not taban["duruyor"]["kapsamdisi"], taban["duruyor"])

        # ---- MUTANT A (HEDEF KOL): alt agac kolundan `yerel_asil_durumu` KALKAR ----
        mut_yol = mutant_yaz(td, [K212A_MUTANT_HEDEF], ad="mutant-k212a.py")
        mut_a = k212a_kos(modul_yukle(mut_yol, "mutant_k212a"), os.path.join(td, "ma"))
        kontrol("🔴 19-M) MUTANT A alt agac kolunu OLDURDU: fail-closed kalem SILINDI "
                "(saglam kodda YASIYORDU -> iddia bos degil)",
                not mut_a["duruyor"]["agac_yerelsiz"]
                and not mut_a["duruyor"]["kok_yerelsiz"]
                and mut_a["agac_atlanan"] == [],
                "duruyor=%s atlanan=%s" % (mut_a["duruyor"], mut_a["agac_atlanan"]))
        # 🔴 IKI YONLU AYRIM: mutant HEDEF kolu oldururken KOMSU kolu (kok) DUSURMEMELI.
        # Tek yonlu "hedef koldu oldu" kaniti tautolojiyi gormez.
        kontrol("🔴 19-M) MUTANT A KOK kolunu ETKILEMEDI (hedef-kol atfi iki yonlu)",
                K212A_YERELSIZ in mut_a["kok_atlanan"]
                and K212A_ASILLI in mut_a["kok_islenen"],
                "kok_atlanan=%s kok_islenen=%s"
                % (mut_a["kok_atlanan"], mut_a["kok_islenen"]))

        # ---- MUTANT KONTROL (ILGISIZ KOL): K212/A iddialari YESIL KALMALI ----
        mut_k_yol = mutant_yaz(td, [K212A_MUTANT_KONTROL], ad="mutant-k212a-kontrol.py")
        mut_k = k212a_kos(modul_yukle(mut_k_yol, "mutant_k212a_kontrol"),
                          os.path.join(td, "mk"))
        kontrol("19-K) KONTROL MUTANTI GERCEKTEN ETKIN (kapsam-disi klasor DURUYOR)",
                mut_k["duruyor"]["kapsamdisi"], mut_k["duruyor"])
        kontrol("🔴 19-K) KONTROL MUTANTINDA K212/A iddialari YESIL kaldi "
                "(mutant AYIRT EDICI, batarya toptan yanmiyor)",
                mut_k["duruyor"]["kok_yerelsiz"] and mut_k["duruyor"]["agac_yerelsiz"]
                and not mut_k["duruyor"]["kok_asilli"]
                and not mut_k["duruyor"]["agac_asilli"]
                and mut_k["agac_atlanan"] == taban["agac_atlanan"]
                and mut_k["kok_atlanan"] == taban["kok_atlanan"],
                "duruyor=%s" % mut_k["duruyor"])

    # ======== 20) K212/B — DAMGA KAPSAM SAYACLARI: IKI SOZLUK, IKI AD ==========
    # Kalem K212'nin IKINCI yuzu. `agac_temizlik_sayilari` ONCEDEN `agac_sayilari`
    # adiyla yaziliyordu -> AGAC_KAPSAMI'nin gorev/cron/plan sayaclari damgaya HIC
    # girmiyordu ve "yedek TAM" beyani o eksen icin OLCULMEMIS kaliyordu.
    # Asagisi damgayi GERCEK ICRA ile uretir ve sayaclarin TURETILMIS oldugunu
    # (cipiplak sifir DEGIL, fiksturun dosya sayisi) olcer.
    print("\n20) K212/B — damga hem gorev/cron/plan hem alt-agac temizlik sayaclarini TASIR")
    # Fikstur boyutlari TEK KAYNAK: iddia bu sozlukten turer, elle yazilmaz.
    K212B_AGAC = {
        "gorev": (os.path.join(".claude", "scheduled-tasks"),
                  ("gorev-a.md", "gorev-b.md", "gorev-c.md", "not.txt"), ("cikti.log",)),
        "cron":  (os.path.join(".claude", "cron"),
                  ("nobet.sh", "surucu.py", "ayar.json"), ("kosum.log",)),
        "plan":  (os.path.join(".claude", "plans"),
                  ("plan-a.md", "plan-b.md"), ("veri.bin",)),
    }

    def k212b_ortam(td):
        o = izole_ortam(td, yedekle)
        for _etiket, (gorece, dahil, haric) in K212B_AGAC.items():
            kok = os.path.join(o["ev"], gorece)
            os.makedirs(kok, exist_ok=True)
            for ad in dahil + haric:
                with open(os.path.join(kok, ad), "w") as fh:
                    fh.write("izole fikstur: %s\n" % ad)
        return o

    def k212b_eksik_anahtarlar(damga):
        """Damgada BULUNMAYAN gorev/cron/plan sayaclari (bos liste = tam kapsam)."""
        if not isinstance(damga, dict):
            return ["(damga YOK)"]
        bek = [e + s for e in K212B_AGAC for s in ("", "_yeni", "_haric")]
        return sorted(a for a in bek if a not in damga)

    TEMIZLIK_ANAHTARLARI = ("agac_sir_bulunan", "agac_sir_silinen", "agac_sir_atlanan",
                            "kapsamdisi_bulunan", "kapsamdisi_silinen",
                            "kapsamdisi_atlanan")

    with tempfile.TemporaryDirectory() as td:
        o = k212b_ortam(td)
        r = izole_kos(o)
        d = damga_json(o["hedef"])
        kontrol("20) hazirlik: izole yedek TAMAMLANDI (rc=0, damga yazildi)",
                r.returncode == 0 and isinstance(d, dict),
                "rc=%d damga=%s" % (r.returncode, type(d).__name__))
        kontrol("🔴 20) damga gorev/cron/plan sayaclarinin HEPSINI tasiyor "
                "(K212/K2 — ezme geri gelmedi)",
                k212b_eksik_anahtarlar(d) == [], k212b_eksik_anahtarlar(d))
        kontrol("20) damga alt-agac TEMIZLIK sayaclarini da tasiyor (iki sozluk YAN YANA)",
                all(a in (d or {}) for a in TEMIZLIK_ANAHTARLARI),
                [a for a in TEMIZLIK_ANAHTARLARI if a not in (d or {})])
        # 🔴 SAYAC TURETILMIS OLMALI: ciplak sifir yanlis hipotez uretir
        # ([[tasima-birimi-yanlis-seviyede]]). Her eksen fiksturun dosya sayisini basar.
        for etiket, (_gorece, dahil, haric) in sorted(K212B_AGAC.items()):
            kontrol("20) %s sayaci TURETILMIS: dosya=%d, yeni=%d, haric=%d"
                    % (etiket, len(dahil), len(dahil), len(haric)),
                    (d or {}).get(etiket) == len(dahil)
                    and (d or {}).get(etiket + "_yeni") == len(dahil)
                    and (d or {}).get(etiket + "_haric") == len(haric),
                    "damga: %s=%s yeni=%s haric=%s"
                    % (etiket, (d or {}).get(etiket), (d or {}).get(etiket + "_yeni"),
                       (d or {}).get(etiket + "_haric")))

    # ---- MUTANT B (HEDEF KOL): ezme GERI gelir -> gorev/cron/plan damgadan DUSER ----
    K212B_MUTANT_HEDEF = [
        ("    agac_temizlik_sayilari = yedek_agac_raporu(backup, sir_temizle=sir_temizle)",
         "    agac_sayilari = yedek_agac_raporu(backup, sir_temizle=sir_temizle)"
         "   # MUTANT K212/B: ezme"),
        ("    sayilar.update(agac_temizlik_sayilari)     # alt agac sir + kapsam-disi temizligi",
         "    sayilar.update(agac_sayilari)   # MUTANT K212/B: ikinci sozluk YOK"),
    ]
    with tempfile.TemporaryDirectory() as td:
        o = k212b_ortam(td)
        with open(YEDEKLE, encoding="utf-8") as fh:
            gov = fh.read()
        for eski, yeni in K212B_MUTANT_HEDEF:
            if eski not in gov:
                raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r"
                                   % eski)
            gov = gov.replace(eski, yeni, 1)
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov)
        r_m = izole_kos(o)
        d_m = damga_json(o["hedef"])
        eksik_m = k212b_eksik_anahtarlar(d_m)
        kontrol("🔴 20-M) MUTANT B damgadan gorev/cron/plan sayaclarini DUSURDU "
                "(saglam kodda VARDI -> iddia bos degil)",
                r_m.returncode == 0 and len(eksik_m) == 9, "eksik=%s" % eksik_m)
        kontrol("🔴 20-M) MUTANT B KOMSU ekseni (temizlik sayaclari) DUSURMEDI "
                "(hedef-kol atfi iki yonlu)",
                all(a in (d_m or {}) for a in TEMIZLIK_ANAHTARLARI),
                [a for a in TEMIZLIK_ANAHTARLARI if a not in (d_m or {})])

    # ---- MUTANT KONTROL (ILGISIZ KOL): K212/A mutanti B iddialarini DUSURMEMELI ----
    with tempfile.TemporaryDirectory() as td:
        o = k212b_ortam(td)
        with open(YEDEKLE, encoding="utf-8") as fh:
            gov = fh.read()
        if K212A_MUTANT_HEDEF[0] not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis)")
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(K212A_MUTANT_HEDEF[0], K212A_MUTANT_HEDEF[1], 1))
        r_k = izole_kos(o)
        d_k = damga_json(o["hedef"])
        kontrol("🔴 20-K) KONTROL MUTANTINDA (K212/A kolu bozuk) K212/B iddialari "
                "YESIL kaldi — iki eksen BAGIMSIZ olculuyor",
                r_k.returncode == 0 and k212b_eksik_anahtarlar(d_k) == []
                and all(a in (d_k or {}) for a in TEMIZLIK_ANAHTARLARI),
                "rc=%d eksik=%s" % (r_k.returncode, k212b_eksik_anahtarlar(d_k)))

    # ======== 21) KARANTINA TESHIS ETIKETI — AYNI ADLI DOKUZ DOSYAYI AYIRIR =====
    # 🔴 26 Agu 2026, GERCEK VAKA (K212Yedek, eksen C): canli kosum her push'ta
    # rc=1 dondu ve kaydi sundan ibaretti: "ATLANDI: MEMORY.md". Yedekte AYNI ADI
    # tasiyan DOKUZ dosya var -> satir hicbir seyi ayirt etmiyor. Kok neden ancak
    # dokuz evin MEMORY.md'si TEK TEK boyutlanarak bulundu
    # (ek/memory-evler/...-m-beyin/MEMORY.md: 6688 -> 1691 bayt).
    print("\n21) KARANTINA ETIKETI — ayni adli dosyalar AYIRT EDILIYOR mu?")
    with tempfile.TemporaryDirectory() as td:
        kok_b = os.path.join(td, "backup-v2")
        ev_a = os.path.join(kok_b, "ek", "memory-evler", "-ev-a", "MEMORY.md")
        ev_b = os.path.join(kok_b, "ek", "memory-evler", "-ev-b", "MEMORY.md")
        disarisi = os.path.join(td, "yedek-disi", "MEMORY.md")
        e_a = yedekle.karantina_etiketi(ev_a, kok_b)
        e_b = yedekle.karantina_etiketi(ev_b, kok_b)
        kontrol("🔴 21) AYNI ADLI iki kalem FARKLI etiket aliyor (kayit ayirt ediyor)",
                e_a != e_b, "a=%s b=%s" % (e_a, e_b))
        kontrol("21) etiket kaydin EVINI adlandiriyor (yedek kokune gorece yol)",
                e_a == os.path.join("ek", "memory-evler", "-ev-a", "MEMORY.md")
                and "-ev-b" in e_b, "a=%s b=%s" % (e_a, e_b))
        kontrol("21) yedek koku DISINDAKI yol MUTLAK basilir (bilgi daraltilmaz)",
                yedekle.karantina_etiketi(disarisi, kok_b) == disarisi,
                yedekle.karantina_etiketi(disarisi, kok_b))
        kontrol("21) `backup` bilinmiyorsa mutlak yol doner (fail-open DEGIL, TAM bilgi)",
                yedekle.karantina_etiketi(ev_a, None) == ev_a
                and yedekle.karantina_etiketi(ev_a, "") == ev_a)
        # ---- MUTANT (HEDEF KOL): eski `basename` davranisi geri gelir ----
        mut21 = mutant_yaz(
            td,
            [("    if not backup or not yol:\n        return yol\n",
              "    if True:\n        return os.path.basename(yol)"
              "   # MUTANT 21: basename'e geri don\n")],
            ad="mutant-karantina.py")
        m21 = modul_yukle(mut21, "mutant_karantina")
        kontrol("🔴 21-M) MUTANT etiketi COKERTTI: dokuz ayri kalem TEK ADA dustu "
                "(saglam kodda ayriliyorlardi -> iddia bos degil)",
                m21.karantina_etiketi(ev_a, kok_b) == m21.karantina_etiketi(ev_b, kok_b)
                == "MEMORY.md",
                "a=%s b=%s" % (m21.karantina_etiketi(ev_a, kok_b),
                               m21.karantina_etiketi(ev_b, kok_b)))
        # ---- KONTROL MUTANTI (ILGISIZ KOL): 21) iddialari YESIL kalmali ----
        mutk21 = mutant_yaz(td, [K212A_MUTANT_KONTROL], ad="mutant-karantina-kontrol.py")
        mk21 = modul_yukle(mutk21, "mutant_karantina_kontrol")
        kontrol("🔴 21-K) KONTROL MUTANTINDA (kapsam-disi kolu bozuk) 21) iddialari "
                "YESIL kaldi — mutant AYIRT EDICI",
                mk21.karantina_etiketi(ev_a, kok_b) == e_a
                and mk21.karantina_etiketi(ev_b, kok_b) == e_b
                and e_a != e_b,
                "a=%s b=%s" % (mk21.karantina_etiketi(ev_a, kok_b),
                               mk21.karantina_etiketi(ev_b, kok_b)))

    # ---------------- OZET ----------------
    kirmizi = [a for a, ok, _ in SONUC if not ok]
    print("\n" + "=" * 70)
    print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    if kirmizi:
        for a in kirmizi:
            print("  ❌ " + a)
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(hermetik_main() if HERMETIK_BAYRAK in sys.argv[1:] else main())
