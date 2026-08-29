#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI KAPSAM KAPISI — her kabul testi ya CI'da kosuluyor ya da GEREKCELI olarak muaf.

NEDEN VAR (denetim, 20 Tem): .github/workflows/deploy.yml uzun sure YALNIZ 2 test kosuyordu
(kisisel-veri + kategori-parite). Repodaki onlarca kabul testi hicbir push'ta kosmadigi icin
"olu nobetci" bir test CI'dan YESIL/success alarak gecebiliyordu (B paketi olu sepet nobetcisi
son 4 kosumda success aldi). Bu kapi FAIL-CLOSED bir kapsam bekcisidir: repoda IZLENEN
(git ls-files) her kabul-testi dosyasi ya deploy.yml'de FIILEN kosulur, ya da asagidaki
IZIN_LISTESI'nde GEREKCE ile muaf tutulur. Ucuncu bir hal yoktur -> yeni bir test sessizce
CI-disi kalamaz.

KESIF (discovery) — git ls-files uzerinden (CI checkout == yerel; os.walk kullanılmaz cunku
gitignore'lu/uretilmis dosyalar yerelde gorunup CI'da gorunmez, sapma yaratirdi):
  * tools/  (arsiv/ HARIC):  <ad>-test.(py|js)  VEYA  test-<ad>.(py|js)  VEYA  <ad>-kapisi.py
    (META-DELIK ONARIMI, 21 Tem: kesif uzun sure yalniz "-test"/"test-" adlarina bakiyordu ->
     ADI "-kapisi.py" olan NOBETCILER — odeme-beyani-kapisi, landing-hukuk-kapisi,
     enjeksiyon-kapisi ... — kesfe HIC girmiyordu. Sonuc: biri deploy.yml'den silinse bu kapi
     UYARMAZ, YESIL kalirdi; olculdu: "run: python3 tools/odeme-beyani-kapisi.py" satiri
     silinmis mutant deploy.yml'de kapi eski desenle exit 0 veriyordu. Artik kapsam kurali
     nobetcilere de uygulanir.)
  * shop/test, onizleme/test, jenerator/test:  o dizinin DOGRUDAN altindaki .py/.js/.mjs/.cjs
    (alt dizinler — jenerator/test/aileler, esleme — fikstur/aile verisi, kosulabilir suite degil)

🔴 COKLU IS AKISI (2 Agu): kapi ARTIK IZLENEN TUM `.github/workflows/*.yml` dosyalarini
okur ve her birinin TETIK SINIFINI GERCEK YAML ayristiricisiyla belirler
(tools/yaml-oku.py :: tetikleyiciler). OTOMATIK (push/schedule/...) bir is akisinda
kosmak KAPSAM SAYILIR; YALNIZ ELLE tetiklenen (`workflow_dispatch`/`repository_dispatch`)
bir is akisinda kosmak SAYILMAZ — kimse elle tetiklemezse o nobetci HIC kosmaz.
Tetigi cozulemeyen is akisi BELIRSIZ'dir ve ELLE gibi ele alinir (fail-closed yon:
ters yon kapiyi SESSIZCE gevsetirdi); BELIRSIZ raporda UYARI satiridir, exit kodunu
ETKILEMEZ.

🔴 OPT-IN ALT KUME BEYANI (2 Agu): bir kabul testi dosyasi, CI'ya baglanabilir
DETERMINISTIK alt kumesini KENDI ICINDE beyan edebilir (yorum isareti + `CI-ALT-KUME:`
+ tek jeton). BEYAN EDILEN her alt kume ya OTOMATIK bir is akisinda FIILEN kosmali ya
da ALT_KUME_IZIN_LISTESI'nde OLCULMUS gerekceyle muaf olmali; ucuncu hal yok (exit 1).
  🔴 BILINEN SINIR — KACAMAKSIZ: BEYAN EDILMEYEN yeni bir alt kume bu kapiya GORUNMEZ.
  Bu bir DISIPLIN CIHAZIDIR, KAFES DEGIL ([[kapi-disiplin-ilkesi]]). Duz (beyansiz)
  bayrak kapsami OLCULDU ve CURUDU: 126 (dosya,bayrak) cifti hicbir OTOMATIK is
  akisinda kosmuyor ve ezici cogunlugu MODIFIKATORDUR -> sinyal/gurultu ~1:115 ve her
  yeni modifikator bayrak TUM ekibin yayinini kirmiziya cevirirdi. Yeni A-sinifi
  adaylar UYARI KATMANIYLA (asagida) her kosumda yuzeye cikar; bloklama bedeli sifirdir.

🔴 UYARI KATMANI: kesfedilen her dosyada (a) ayri bir main kolu tetikleyen, (b) hicbir
is akisinda kosmayan, (c) beyan edilmemis ve muaf olmayan bayraklari CI logunda GORUNUR
basar. EXIT KODUNA ASLA DOKUNMAZ ve istisnayi yutar ("UYARI KATMANI OLCULEMEDI").

KABUL (bu dosyanin kendi kabul testleri):
  1. IZLENEN her kabul testi ya kosuluyor ya IZIN_LISTESI'nde -> degilse exit 1 (KAPSAMSIZ).
  2. IZIN_LISTESI'nde GEREKCESIZ (bos) giris -> exit 1.
  3. IZIN_LISTESI'nde olup artik KESFEDILMEYEN (silinmis/yeniden adlandirilmis) giris -> exit 1
     (liste curumesin).
  4. IZIN_LISTESI'nde olup AYNI ZAMANDA deploy.yml'de kosulan giris -> exit 1 (bayat muafiyet;
     kosuluyorsa listeden cikarilmali).
KIRMIZI-MUTASYON: deploy.yml'den bir "python3 tools/<x>-test.py" satiri silinirse o test
kapsamsiz kalir -> kapi KIRMIZI (exit 1). (--deploy <yol> ile alternatif/mutasyonlu bir kopyaya
isaret ederek GERCEK deploy.yml'e dokunmadan kanitlanabilir.)

KENDI NOBETCILERI (kontroller=True iken BLOKLAYICI, yani CI'da fiilen kosar):
  * bulgu1_mutasyon_kontrol() — yalniz-yorum mensiyonu 'kosuluyor' sayilmasin.
  * muaf_sayaci_kontrol()     — rapordaki "Muaf (izin listesi)" sayisi GERCEKTEN izin
    listesini saysin (kapsamsiz dosya o sayiya sizmasin, muafiyet eklenince sayi artsin).
  * kendini_test_adimi_kontrol() — deploy.yml'de bu betigi "--kendini-test" ile
    ANLAMLI OLARAK ICRA EDEN bir cagri var mi (ZINCIRIN SON HALKASI). 30 Tem'e kadar
    duz `in` aramasiydi; olculdu ki `run: echo python3 ... --kendini-test` mutantinda
    hicbir sey kosmadigi halde dort denetci de rc=0 veriyordu -> artik ortak suzgec
    (tools/icra-suzgeci.py) kullanilir. "Adim kosuyor + BLOKLUYOR" hala IDDIA EDILMEZ
    (o eksen tools/is-akisi-kapisi.py BOLUM D'dedir).
  * bayraksiz_adim_kontrol() — deploy.yml'de bu betigi BAYRAKSIZ (kapsam kolu) kosan
    bir adim var mi. GERCEK kapisi `--kendini-test` KOLUNDADIR: olculdu ki (a) bayraksiz
    cagri `--help`'e cevrilince ve (b) bayraksiz ADIM butunuyle silinince kapsam kurali
    CI'da HIC olculmuyor ve dort denetci de rc=0 veriyordu (bu betigin deploy.yml'de IKI
    cagrisi oldugu icin kosulan() bunu gormez).
  * suzgec_fikstur_kontrol() / suzgec_kablosu_kontrol() — ortak suzgecin GOVDESI
    (sentetik ariza enjeksiyonu) ve KABLOSU (AST) yerinde mi.
  * alt_kume_fikstur_kontrol() — coklu is akisi TETIK siniflandirmasi + opt-in BEYAN
    ayristirmasi + UCTAN UCA alt kume kabul/ret semantigi + UYARI KATMANININ exit
    koduna dokunmadigi (bulgu bassa da ISTISNA atsa da). Hepsi SENTETIK fiksturlerle;
    GERCEK deploy.yml'e mutasyon UYGULANMAZ.

ORTAK "GERCEK ICRA MI" SUZGECI: tools/icra-suzgeci.py (TEK KAYNAK; bu dosya,
tools/is-akisi-kapisi.py, jenerator/test/kabul.py ve tools/konfigur-nobet-mutasyon.py
onu KULLANIR, KOPYALAMAZ).

Kullanim:
    python3 tools/ci-kapsam-test.py
    python3 tools/ci-kapsam-test.py --deploy /gecici/mutant-deploy.yml
    python3 tools/ci-kapsam-test.py --kendini-test
"""
import argparse
import ast
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DEPLOY_VARSAYILAN = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

# ---- BU BETIGIN KENDI ADIMLARININ YASADIGI IS AKISI (5 Agu 2026) ------------
# 🔴 NEDEN AYRI SABIT: bu betigin IKI kolu (bayraksiz KAPSAM + `--kendini-test`)
# "aracin KENDINI sinamasi" sinifindadir ve serit ayriminda deploy.yml'den
# nobet.yml'e TASINDI (bloklamayan nobet/alarm joblari yayin kosumunun rengini
# boyamasin diye; olculen bedel: 28 ardisik "failure" kosumun 14'unde deploy+yayin
# YESILDI, mimar yanlis hukum verdi — [[hukum-yanlis-birimde]]).
# Asagidaki UC oz-nobetci (bulgu1 · kendini-test adimi · bayraksiz adim) "bu betigin
# su kolu CI'da GERCEKTEN icra ediliyor mu" der; o yuzden ADIMLARIN BULUNDUGU dosyaya
# bakmalidir. Dosya yoksa fail-closed KIRMIZI (yoklugu YESIL degildir).
# DOSYA GRANULU AYRICA OLCULUR: tools/is-akisi-kapisi.py :: BOLUM E her zorunlu
# cagriyi HANGI is akisinda arayacagini tablosunda tasir (ikiz tanim degil, iki AYRI
# surecten olculen ayni iddia — biri susarsa oteki konusur).
KENDI_IS_AKISI = os.path.join(ROOT, ".github", "workflows", "nobet.yml")

# ---- COKLU IS AKISI (BOLUM A) ----------------------------------------------
# 🔴 OLCULEN KUSUR (2 Agu): bu kapi SADECE deploy.yml'e bakiyordu. Repoda IZLENEN
# DORT is akisi var ve ucu OTOMATIK tetikleniyor:
#     deploy.yml               push + workflow_dispatch        -> OTOMATIK
#     d1-uzlastirici.yml       schedule + workflow_dispatch    -> OTOMATIK
#     paket-tazelik-alarmi.yml schedule + workflow_dispatch    -> OTOMATIK
#     onizleme-imaj.yml        YALNIZ workflow_dispatch        -> ELLE
# Sonuc: cron'da GERCEKTEN kosan cagrilar "hic kosmuyor" gorunuyordu.
# 🔴 ELLE TETIKLENEN IS AKISINDA KOSMAK "CI'DA KOSUYOR" SAYILMAZ: kimse elle
# tetiklemezse o nobetci HIC kosmaz; kapsam kapisinin tum anlami "her push'ta
# GERCEKTEN olculuyor mu" sorusudur.
IS_AKISI_DIZINI = os.path.join(ROOT, ".github", "workflows")
# `workflow_call`: is akisi ancak BASKA bir is akisi onu CAGIRIRSA kosar; kendi basina
# hicbir olayla tetiklenmez. Kapsam acisindan `workflow_dispatch` ile AYNI SINIFTIR
# (olculdu, bagimsiz curutucu O1): ELLE sayilmazsa cagrilmayan bir `workflow_call`
# akisindaki her cagri sessizce "kapsanmis" olurdu.
ELLE_TETIKLER = frozenset(("workflow_dispatch", "repository_dispatch", "workflow_call"))
IS_AKISI_PAT = re.compile(r"^\.github/workflows/[^/]+\.(?:yml|yaml)$")
SINIF_OTOMATIK = "OTOMATIK"
SINIF_ELLE = "ELLE"
SINIF_BELIRSIZ = "BELIRSIZ"


def otomatik_mi(sinif):
    """🔴 'OTOMATIK MI' SORUSUNUN TEK KAYNAGI (O4, [[ikiz-tanim-sessiz-ayrisma]]).

    ONCE bu hukum IKI YERDE bagimsiz hesaplaniyordu (`kosulan_coklu` ve
    `bayrak_envanteri`). Olculdu (bagimsiz curutucu N13): `kosulan_coklu`'yu BELIRSIZ'i
    OTOMATIK sayacak sekilde bozan mutant IKI KOLDA DA YESIL GECTI — cunku bayrak
    yolundaki fikstur o mutanti ORTUYOR, DOSYA duzeyi kapsamda ise BELIRSIZ yonunu
    civileyen fikstur YOKTU. Tek kaynak + ALT_KUME_FIKSTURLERI'ndeki dosya-duzeyi
    BELIRSIZ fiksturu birlikte o kacisi kapatir."""
    return sinif == SINIF_OTOMATIK


# ---- ORTAK "GERCEK ICRA MI" SUZGECI — TEK KAYNAK ---------------------------
# tools/icra-suzgeci.py: bir kabuk satirinin <yol>'u GERCEKTEN icra ettigini
# `shlex` (POSIX sozcuk ayirici) ile olcer. BURADA KOPYASI TUTULMAZ — 30 Tem
# yargi turunda olculdu ki metin capasi "cagri duruyor" derken CI'da hicbir sey
# olculmeyen dort yol vardi (`--help`, `echo` mensiyonu, silinmis adim, sahte
# tetikleyici). Ayni mantigin ikinci kopyasi = drift ([[ayna-kapi-kesif-ekseni]]).
_SUZGEC_SOZLESME = ("anlamli_cagri", "cagri_sayilir", "onek_re", "birlestir_devam",
                    "yorumlayici_adi", "etkili_arguman", "EVET", "HAYIR", "OLCULEMEDI")


def _suzgec_yukle():
    """tools/icra-suzgeci.py'yi MODUL olarak yukle. FAIL-CLOSED: yoksa ya da
    sozlesmesi degismisse RuntimeError (SystemExit DEGIL — bu dosya
    tools/is-akisi-kapisi.py tarafindan MODUL olarak yuklenir ve orası `Exception`
    yakalayip okunur tani basar; SystemExit o tani kanalini atlar)."""
    import importlib.util
    yol = os.path.join(TOOLS, "icra-suzgeci.py")
    if not os.path.exists(yol):
        raise RuntimeError(
            "tools/icra-suzgeci.py YOK -> ortak 'gercek icra mi' suzgeci yuklenemedi. "
            "Bu kapi suzgec olmadan `--help`/`echo` sinifi sessiz kacislari GORMEZ, "
            "o yuzden YESIL SAYMAZ (fail-closed).")
    spec = importlib.util.spec_from_file_location("pruvo_icra_suzgeci", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_icra_suzgeci"] = mod
    spec.loader.exec_module(mod)
    for ad in _SUZGEC_SOZLESME:
        if not hasattr(mod, ad):
            raise RuntimeError("tools/icra-suzgeci.py'de %s YOK -> suzgec sozlesmesi "
                               "degismis, tuketicileri guncelle (fail-closed)" % ad)
    return mod


SUZGEC = _suzgec_yukle()


def _git_ortami_yukle():
    """tools/git_ortami.py — "bayat kayit" hukmunun TEK KAYNAGI (fail-closed, SUZGEC
    ile ayni desen: modul yoksa TAHMIN URETILMEZ, kapi konusur)."""
    import importlib.util
    yol = os.path.join(TOOLS, "git_ortami.py")
    if not os.path.exists(yol):
        raise RuntimeError(
            "tools/git_ortami.py YOK -> 'kayit defterinin isaret ettigi dosya artik "
            "izlenmiyor' hukmunun TEK KAYNAGI yuklenemedi. Ikinci bir kopya YAZILMAZ "
            "(ikiz tanim sessizce ayrisir), o yuzden YESIL SAYILMAZ (fail-closed).")
    spec = importlib.util.spec_from_file_location("pruvo_git_ortami", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_git_ortami"] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "bayat_kayit_yollari"):
        raise RuntimeError("tools/git_ortami.py'de bayat_kayit_yollari YOK -> sozlesme "
                           "degismis, tuketicileri guncelle (fail-closed)")
    return mod


GIT_ORTAMI = _git_ortami_yukle()


# ---- GERCEK YAML AYRISTIRICISI — TEK KARAR MERCII (PARSER-FIRST) -----------
# tools/yaml-oku.py (KATMAN 0): `run:` degerlerini GERCEK bir ayristiriciyla
# (PyYAML | ruby/psych) cozer ve HAM satir araligini verir. FAIL-CLOSED yuklenir:
# dosya kaldirilirsa kapi taklide SESSIZCE dusmez, konusur.
_YAML_OKU_SOZLESME = ("run_dugumleri", "ayristirici_adi", "onbellegi_isit",
                      "tetikleyiciler", "tetik_onbellegi_isit")


def _yaml_oku_yukle():
    """tools/yaml-oku.py'yi MODUL olarak yukle (fail-closed, SUZGEC ile ayni desen)."""
    import importlib.util
    yol = os.path.join(TOOLS, "yaml-oku.py")
    if not os.path.exists(yol):
        raise RuntimeError(
            "tools/yaml-oku.py YOK -> GERCEK YAML ayristiricisi kolu yuklenemedi. "
            "Bu kapi o zaman `run:` degerlerini yalniz METIN TAKLIDIYLE gorur; olculdu "
            "(30 Tem differential fuzzing, 1037 kiyaslanabilir girdi): taklit ile gercek "
            "ayristirici 303 girdide FARKLI hukum veriyor (29'u sahte-YESIL bilesenli). "
            "O yuzden YESIL SAYILMAZ (fail-closed).")
    spec = importlib.util.spec_from_file_location("pruvo_yaml_oku", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_yaml_oku"] = mod
    spec.loader.exec_module(mod)
    for ad in _YAML_OKU_SOZLESME:
        if not hasattr(mod, ad):
            raise RuntimeError("tools/yaml-oku.py'de %s YOK -> ayristirici sozlesmesi "
                               "degismis, tuketicileri guncelle (fail-closed)" % ad)
    return mod


YAML_OKU = _yaml_oku_yukle()

# ---- KESIF PREDIKATLARI ----------------------------------------------------
# 🔴 UCUNCU META-DELIK ONARIMI (8 Agu 2026) — `*-mutasyon.py` / `*-mutasyon.js`
# Kesif uzun sure yalniz "-test" / "test-" / "-kapisi" adlarina bakiyordu. Bu depoda
# UCUNCU bir kabul-araci sinifi var ve TAMAMEN disarida kaliyordu: MUTASYON SURUCUSU
# (bir kapinin/testin GERCEKTEN olcup olcmedigini kanitlayan batarya).
# OLCULEN ENVANTER (8 Agu 2026, `git ls-files`):
#     43 surucu · 8'i OTOMATIK bir is akisinda kosuyor · 35'i kosmuyor
#     bunlarin 31'i kesif predikatinin HIC gormedigi dosyalardi
# Sonuc IKI YONLU idi:
#   (a) Kosmayan 31 surucu icin kapsam sorusu HIC SORULMUYORDU -> surucu curuse kimse
#       duymazdi. Olculdu, CURUME ZATEN OLMUS: `tools/d1-sapma-mutasyon.py` (rc=1,
#       capa bulunamiyor) ve `tools/gecmis-geri-donus-mutasyon.py` (rc=1, kendi
#       raporunda "arac bayat") temiz checkout'ta KIRMIZI ve kimse gormemis.
#   (b) Daha kotusu: KOSAN ikisi (`tools/varlik-mutasyon.py` deploy.yml'de,
#       `tools/yayin-sinyali-mutasyon.py` nobet.yml'de) kesif disi oldugu icin
#       RATCHET'SIZDI — cagri satirlari silinse bu kapi UYARMAZ, YESIL kalirdi.
#       Tam olarak "-kapisi.py" meta-deliginin (21 Tem, yukarida) AYNISI
#       ([[nobetci-cagri-satiri-nobetsiz]]).
# NEDEN ACIK KESIF KAYDI (ACIK_KESIF) DEGIL, PREDIKAT: 6 Agu'daki karar "kabul kolu
# tasiyan her tools/*.py" predikatina karsiydi cunku o predikat KAPSAM DISI 6 dosya
# getiriyordu (sinyal/gurultu kotu). Burada durum TERS: `-mutasyon` adi bu depoda
# TEK ANLAMLI bir konvansiyondur — 43 adayin 43'u de gercek mutasyon surucusudur
# (yanlis-pozitif 0, olculdu). 31 kalemi ACIK_KESIF'e TEK TEK yazmak ayni sonucu
# BAKIMI ELDE olan bir defterle verirdi ve defter her yeni surucude bayatlardi
# ([[envanter-drift-parti-basina]]). Predikat ratchet'i BAKIMSIZ tasir.
# YANLIS-POZITIF SINIRI (fikstur ile civili — KESIF_PREDIKAT_FIKSTURLERI): yalniz
# `tools/` DOGRUDAN altindaki `.py`/`.js`. Fikstur/veri/dokuman (`.md`, `.json`,
# `.txt`), `tools/arsiv/` ve alt dizinler YAKALANMAZ.
TOOLS_PAT = re.compile(
    r"^tools/([^/]*-test\.(?:py|js)|test-[^/]*\.(?:py|js)|[^/]*-kapisi\.py"
    r"|[^/]*-mutasyon\.(?:py|js))$")
DIR_PAT = re.compile(r"^(?:shop/test|onizleme/test|jenerator/test)/[^/]+\.(?:py|js|mjs|cjs)$")

# ---- KESIF PREDIKATI FIKSTURLERI (POZITIF + NEGATIF, iki yonlu) -------------
# 🔴 TEK YONLU NOBETCI OLU NOBETCIDIR: predikat yalniz "yakaliyor mu" diye olculurse
# `^tools/.*$` gibi bir gevsetme de YESIL gecerdi. O yuzden NEGATIF vakalar (kapsam
# disi ad/uzanti/dizin) AYNI tabloda ve AYNI agirlikta durur.
# (yol, yakalanmali_mi, NEDEN)
KESIF_PREDIKAT_FIKSTURLERI = (
    # --- POZITIF: mutasyon surucusu konvansiyonu ---
    ("tools/varlik-referans-mutasyon.py", True, "surucu (.py) — 8 Agu somut vakasi"),
    ("tools/parite-marka-mutasyon.js", True, "surucu (.js) — node ile kosar"),
    ("tools/zzz-yeni-mutasyon.py", True, "YARIN eklenecek surucu de RATCHET'e girmeli"),
    # --- POZITIF: onceden zaten kapsanan adlar DUSMEMELI (regresyon nobeti) ---
    ("tools/ci-kapsam-test.py", True, "`-test.py` kolu AYNEN durmali"),
    ("tools/test-ornek.py", True, "`test-` oneki kolu AYNEN durmali"),
    ("tools/uyum-kapisi.py", True, "`-kapisi.py` kolu AYNEN durmali"),
    ("shop/test/eposta.mjs", True, "DIR_PAT kolu AYNEN durmali"),
    ("jenerator/test/kisit-mutasyon.js", True, "DIR_PAT zaten yakaliyordu"),
    # --- NEGATIF: benzer ADLI ama kapsam DISI ---
    ("tools/mutasyon-notlari.md", False, "DOKUMAN — kosulabilir suite degil"),
    ("tools/varlik-referans-mutasyon.json", False, "VERI/fikstur — kosulabilir degil"),
    ("tools/mutasyon-kayit.txt", False, "duz metin"),
    ("tools/arsiv/eski-mutasyon.py", False, "tools/arsiv/ BILINCLI olarak kapsam disi"),
    ("tools/alt/dizin/x-mutasyon.py", False, "tools/ DOGRUDAN alti degil"),
    ("jenerator/test/aileler/x-mutasyon.js", False, "DIR_PAT alt dizini kapsamaz"),
    ("belgeler/x-mutasyon.py", False, "tools/ disinda"),
    ("tools/mutasyon.py", False, "`-mutasyon` EKI yok (ciplak ad) — konvansiyon disi"),
    ("tools/x-mutasyonlu.py", False, "jeton siniri: `-mutasyonlu` EK DEGILDIR"),
)


def kesif_predikat_kontrol():
    """KESIF_PREDIKAT_FIKSTURLERI iki yonlu tutuyor mu (pozitif VE negatif)."""
    hatalar = []
    for yol, beklenen, neden in KESIF_PREDIKAT_FIKSTURLERI:
        # 🔴 `tools/arsiv/` icin AYRI bir maske KONULMAZ: kesfet()'te o eleme ayrica
        # var ama fikstur PREDIKATIN kendisini olcmeli — maske konsaydi, predikati
        # slash'a izin verecek sekilde gevseten bir mutant bu fiksturde GORUNMEZDI
        # ([[beyan-edilmis-survivor]]).
        goruldu = bool(TOOLS_PAT.match(yol) or DIR_PAT.match(yol))
        if goruldu != beklenen:
            hatalar.append("KESIF PREDIKATI FIKSTURU DUSTU: %s -> yakalandi=%s "
                           "beklenen=%s (%s)" % (yol, goruldu, beklenen, neden))
    poz = sum(1 for _y, b, _n in KESIF_PREDIKAT_FIKSTURLERI if b)
    neg = len(KESIF_PREDIKAT_FIKSTURLERI) - poz
    if poz < 8 or neg < 9:
        hatalar.append("KESIF PREDIKATI FIKSTUR TABLOSU KUCULDU (pozitif %d, negatif %d; "
                       "taban 8/9) — tabloyu kucultmek nobetciyi SESSIZCE oldurur "
                       "([[fikstur-degeri-mutasyon-koru]])." % (poz, neg))
    return (not hatalar), hatalar

# ---- ACIK KESIF KAYDI (6 Agu 2026) -----------------------------------------
# 🔴 OLCULEN KESIF KORLUGU: yukaridaki predikatlar AD tabanlidir. Kabul kolu
# (`--kendini-test` / `--ic-nobetci` / `--mutasyon`) TASIYAN ama bu adlarin hicbirine
# uymayan IZLENEN `tools/*.py` dosyalari kesfe HIC girmez -> CI'da hic kosmasalar bile
# bu kapi YESIL yanar. Kosmayan nobetci nobetsizdir ([[nobetci-cagri-satiri-nobetsiz]]).
#
# 🔴 NEDEN PREDIKAT GENISLETILMEDI, ACIK KAYIT SECILDI (OLCULDU, 6 Agu 2026):
# "kabul kolu olan her tools/*.py" predikatı bugun 7 dosya getirir; 6'si BU ISIN
# KAPSAMI DISINDADIR (cip-sayfa-bagi · d1-sync · onizleme-deploy-hazirla ·
# uzlastirici-onarim · yayin-erisim-nobeti · yayin-gecikme-nobeti). Bunlarin her biri
# icin "CI cagri satiri mi, gerekceli muafiyet mi" karari AYRI bir serit/maliyet
# yargisidir (ikisi zaten BILEREK CI'da kosmayan canli-olcum nobetcileridir — bkz.
# is-akisi-kapisi.py::SERIT_B gerekceleri). Predikati simdi genisletmek o 6 dosyayi
# ANINDA "KAPSAMSIZ" yapip kapiyi kirmiziya cakardi ve tek cikis yolu 6 aceleci
# muafiyet yazmak olurdu — yani genisleme, kapiyi GUCLENDIRMEK yerine MUAFIYET
# LISTESINI sisirirdi ([[kapi-kapsam-genisletme-tuzagi]]). Acik kayit DAR ve
# ratchet'lidir: kayitli dosyanin cagri satiri silinirse kapi KIRMIZI yanar.
# (yol -> NEDEN kesfe zorla alindigi)
ACIK_KESIF = {
    "tools/git_ortami.py":
        "Kutuphane modulu (alt cizgili ad -> `import` edilebilir olmak ZORUNDA, bu "
        "yuzden `*-kapisi.py` adlandirmasina uymaz) ama KABUL KOLU vardir: "
        "`--kendini-test` hem scrub DAVRANISINI hem `GIT_BAGLAM_DEGISKENLERI` "
        "listesinin IKINCI bir tanimini (drift) fail-closed olcer. Uc kapi kok "
        "turetimini bu modulden alir; nobet kosmazsa ikiz sessizce geri gelir.",
    "tools/faz3-bayrak.js":
        "index.html EDGE_KATALOG bayraginin kabul testi (2/6/7 — 50 kontrol) ama adi "
        "`-test.js`/`test-`/`-kapisi.py`/`-mutasyon.js` konvansiyonlarinin HICBIRINE "
        "uymaz (kardesleri faz3-gecikme/faz3-sayfalama nobetcilerini `-test.py` "
        "surucusuyle tasir, bu dosya kendisi surucudur). OLCULEN BEDEL (12 Agu 2026): "
        "kesif disi oldugu icin kapsam sorusu HIC sorulmuyordu -> test aylarca hicbir "
        "is akisinda kosmadi ve icindeki `ozetAc` kopyasi temsil v3'e gecince sessizce "
        "ayristi; TEST 7'ye varmadan TypeError ile coken bir OLU NOBETCIYE dondu ve "
        "kimse duymadi ([[nobetci-cagri-satiri-nobetsiz]]). Onarildi ve deploy.yml "
        "serit-a3'te BLOKLAYICI adima baglandi; bu kayit RATCHET'tir — cagri satiri "
        "silinirse kapi KIRMIZI yanar. MUAFIYET DEGIL, kapsam ZORLAMASIDIR.",
    "tools/merge-kanit.py":
        "Merge kabul kanit tablosu. `--kendini-test` kolu (6 mutant + 2 kontrol) "
        "vardir ama adi `-kapisi.py`/`-test.py`/`-mutasyon.js` konvansiyonlarina "
        "uymaz. Paket ⑤b (19 Agu 2026) ile nobet.yml `serit-b` job'una baglandi; "
        "kesif disi kalirsa CI kapsam kapisinda OTOMATIK'te kosmuyor gorunurdu. "
        "Bu kayit RATCHET'tir — cagri satiri silinirse kapi KIRMIZI yanar. "
        "MUAFIYET DEGIL, kapsam ZORLAMASIDIR.",
}


def acik_kesif_kontrol():
    """ACIK_KESIF girisleri hala IZLENIYOR mu (bayat kayit = sessiz kapsam kaybi).

    Bir kayit yeniden adlandirilir/silinirse kesif listesinden SESSIZCE duser ve o
    dosya icin kapsam sorusu sorulmaz olur. Fail-closed: kayit izlenmiyorsa KIRMIZI."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True,
                       env=GIT_ORTAMI.git_ortami())
    if r.returncode != 0:
        return False, ["ACIK_KESIF dogrulanamadi: git ls-files basarisiz: "
                       + r.stderr.strip()]
    izlenen = set(r.stdout.splitlines())
    hatalar = []
    # 🔴 "kayit defterinin isaret ettigi dosya artik IZLENMIYOR" hukmu TEK KAYNAKTAN
    # gelir: tools/git_ortami.py::bayat_kayit_yollari. Ayni kural orada drift muafiyeti
    # defteri icin de uygulanir; ikinci bir kopya YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
    bayat_yollar = set(GIT_ORTAMI.bayat_kayit_yollari(ACIK_KESIF.keys(), izlenen))
    for yol, gerekce in sorted(ACIK_KESIF.items()):
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ ACIK_KESIF girisi (bos gerekce): %s" % yol)
        if yol in bayat_yollar:
            hatalar.append("BAYAT ACIK_KESIF girisi (artik IZLENMIYOR — sil ya da yolu "
                           "duzelt): %s" % yol)
        elif TOOLS_PAT.match(yol) or DIR_PAT.match(yol):
            hatalar.append("GEREKSIZ ACIK_KESIF girisi (ad predikati ZATEN yakaliyor — "
                           "kayit kaldirilmali, ikiz kapsam kaydi tutma): %s" % yol)
    return (not hatalar), hatalar


def _kesif_adayi_mi(yol):
    """🔴 TEK KAYNAK — bir repo-goreli yol kesif kumesine giriyor mu.

    kesfet() (IZLENEN agac) ve kesfet_izlenmeyen() (calisma agaci) bu predikati
    BURADAN alir; ikinci bir kopya yazilirsa iki kova sessizce ayrisir ve
    "izlenmeyen" kolu gevserken kimse duymaz ([[ikiz-tanim-sessiz-ayrisma]])."""
    if yol.startswith("tools/arsiv/"):
        return False
    return bool(TOOLS_PAT.match(yol) or DIR_PAT.match(yol) or yol in ACIK_KESIF)


# 🔴 `git ls-files` ARGUMANLARI SABIT — mutasyon surucusu bu iki listeyi capa olarak
# kullanir. `--others` DUSERSE izlenmeyen kova IZLENEN dosyalarla dolar (bos degil,
# YANLIS dolar) ve fikstur bunu TEK BASINA kirmizi yakar.
LS_FILES_IZLENEN = ("ls-files",)
LS_FILES_IZLENMEYEN = ("ls-files", "--others", "--exclude-standard")


def kesfet():
    """git ls-files uzerinden IZLENEN kabul-testi dosyalarini (repo-rel yol) dondur.

    AD predikatlarina ek olarak ACIK_KESIF kaydindaki (izlenen) yollar da girer."""
    r = subprocess.run(["git", "-C", ROOT] + list(LS_FILES_IZLENEN),
                       capture_output=True, text=True, env=GIT_ORTAMI.git_ortami())
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    bulunan = []
    for yol in r.stdout.splitlines():
        if _kesif_adayi_mi(yol):
            bulunan.append(yol)
    return sorted(bulunan)


def kesfet_izlenmeyen():
    """CALISMA AGACINDA duran ama HENUZ `git add` EDILMEMIS kabul-testi adaylari.

    (yollar, olculemedi_sebep) dondurur — kesfet()'in imzasi/donus tipi DEGISMEZ.

    🔴 OLCULEN KORLUK (9 Agu 2026, bagimsiz curutucu): kesif YALNIZ `git ls-files`
    uzerinden yuruyordu. Yeni bir `tools/<x>-kapisi.py` yazip `git add` ETMEDEN bu
    kapiyi kosan mimar rc=0 "SONUC: YESIL ✅" aliyordu; ayni dosya `git add`
    edilince rc=1 "KAPSAMSIZ" oluyordu. Yani kirmizi ancak push'tan SONRA, CI'da
    konusuyordu — ve bu tur `katalog-alan-kapisi.py` partisinde FIILEN yasandi.
    Bu kova o pencereyi kapatir: dosya HENUZ izlenmiyorken de kapsam sorusu sorulur.

    🔴 FAIL-CLOSED: git okunamazsa BOS LISTE dondurup sessizce gecmez, SEBEP
    dondurur; denetle() bunu ayri bir OLCULEMEDI hatasina cevirir. "Bos kova" ile
    "olcemedim" ayni sey degildir ([[hukum-yanlis-birimde]]).

    NOT: `--exclude-standard` gitignore'u UYGULAR -> `urun/`, `sitemap.xml` gibi
    uretilen artefaktlar bu kovaya GIRMEZ; temiz/CI checkout'unda kova BOSTUR
    (olculdu: 9 Agu 2026, temiz klonda `--others` = 0 satir)."""
    r = subprocess.run(["git", "-C", ROOT] + list(LS_FILES_IZLENMEYEN),
                       capture_output=True, text=True, env=GIT_ORTAMI.git_ortami())
    if r.returncode != 0:
        return [], ("git %s basarisiz (rc=%d): %s"
                    % (" ".join(LS_FILES_IZLENMEYEN), r.returncode,
                       r.stderr.strip() or "-"))
    return sorted(y for y in r.stdout.splitlines() if _kesif_adayi_mi(y)), None


# ---- PRE-PUSH KAPSAMI (git'in kancaya verdigi ref/SHA satirlari) -----------
# Kapsam yalnız pre-push stdin'indeki
#   <local ref> <local sha> <remote ref> <remote sha>
# satirlarindan turetilir. Bu bilgi yoksa/tutarsizsa tahmin uretilmez: izlenmeyen
# kova eski kati hukumle KIRMIZI kalir (fail-closed).
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")


def _sifir_sha(sha):
    return bool(sha) and set(sha) == {"0"}


def push_kapsamini_turet(girdi):
    """(repo-goreli_yollar|None, sebep|None) — pre-push ref/SHA girdisinden.

    Uzak SHA sifirsa yeni ref itiliyordur; bu durumda yerel SHA'dan hicbir uzak
    refte bulunmayan commitler alınır. Silinen ref dosya tasimaz. Her baska halde
    uzak..yerel araligindaki commitlerin dokundugu yollar birlestirilir.
    """
    satirlar = [s.strip() for s in (girdi or "").splitlines() if s.strip()]
    if not satirlar:
        return None, "pre-push stdin'inde ref/SHA satiri YOK"
    kapsam = set()
    for no, satir in enumerate(satirlar, 1):
        alanlar = satir.split()
        if len(alanlar) != 4:
            return None, ("pre-push satiri %d dort alanli degil: %r"
                          % (no, satir[:160]))
        _yerel_ref, yerel_sha, _uzak_ref, uzak_sha = alanlar
        if not _SHA_RE.match(yerel_sha) or not _SHA_RE.match(uzak_sha):
            return None, ("pre-push satiri %d SHA bicimi gecersiz (local=%r remote=%r)"
                          % (no, yerel_sha[:20], uzak_sha[:20]))
        if _sifir_sha(yerel_sha):
            continue
        dogrula = subprocess.run(
            ["git", "-C", ROOT, "cat-file", "-e", yerel_sha + "^{commit}"],
            capture_output=True, text=True, env=GIT_ORTAMI.git_ortami())
        if dogrula.returncode != 0:
            return None, ("pre-push local SHA commit olarak cozulmedi: %s"
                          % yerel_sha)
        if _sifir_sha(uzak_sha):
            komut = ["git", "-C", ROOT, "rev-list", yerel_sha, "--not", "--remotes"]
        else:
            dogrula = subprocess.run(
                ["git", "-C", ROOT, "cat-file", "-e", uzak_sha + "^{commit}"],
                capture_output=True, text=True, env=GIT_ORTAMI.git_ortami())
            if dogrula.returncode != 0:
                return None, ("pre-push remote SHA commit olarak cozulmedi: %s"
                              % uzak_sha)
            komut = ["git", "-C", ROOT, "rev-list", uzak_sha + ".." + yerel_sha]
        revler = subprocess.run(komut, capture_output=True, text=True,
                                env=GIT_ORTAMI.git_ortami())
        if revler.returncode != 0:
            return None, ("push commit araligi cozulmedi (rc=%d): %s"
                          % (revler.returncode, revler.stderr.strip() or "-"))
        for commit in revler.stdout.splitlines():
            yollar = subprocess.run(
                ["git", "-C", ROOT, "diff-tree", "--root", "--no-commit-id",
                 "--name-only", "-r", commit], capture_output=True, text=True,
                env=GIT_ORTAMI.git_ortami())
            if yollar.returncode != 0:
                return None, ("push commit dosyalari cozulmedi (%s, rc=%d): %s"
                              % (commit, yollar.returncode,
                                 yollar.stderr.strip() or "-"))
            kapsam.update(y for y in yollar.stdout.splitlines() if y)
    return kapsam, None


# ---- IZLENMEYEN KOVA FIKSTURU (SENTETIK GIT DEPOSU) -------------------------
# 🔴 GERCEK DEPOYA MUTASYON UYGULANMAZ: fikstur `tempfile` icinde AYRI bir git
# deposu kurar ve `ROOT`u gecici olarak oraya cevirir (okuma_dayanikliligi_kontrol_
# govdesi ile AYNI desen). Kosum sonunda ROOT geri alinir, dizin silinir.
# 🔴 `core.hooksPath` BOSALTILIR: bu makinede GLOBAL hooksPath PRUVO kancalarina
# bakiyor; bosaltilmazsa sentetik depodaki `git commit` gercek deponun kancalarini
# kosardi (olculdu: `git config --global core.hooksPath` = .git/pruvo-kancalar).
_FIKSTUR_GIT_AYAR = ("-c", "core.hooksPath=", "-c", "commit.gpgsign=false",
                     "-c", "core.excludesFile=", "-c", "gc.auto=0")
# Kabul kolu tasiyan sentetik dosya (deploy fikstur metninde KOSAN taban dosya).
_IZ_TABAN = "tools/onceki-test.py"
# 🔴 POZITIF KUME COK SINIFLI OLMAK ZORUNDA (9 Agu 2026, bagimsiz curutucu bulgusu):
# tek pozitif vaka `*-kapisi.py` iken, kovayi YALNIZ o sinifa daraltan bir mutant
# (`Y1'`) uc dosyadan ikisini sessizce dusuruyor ve batarya YESIL kaliyordu — KISMI
# KAPSAM KAYBI gorunmez sinifi. Dort ad konvansiyonunun DORDU de kovada olcuulur.
_IZ_YENI = "tools/zzz-yeni-kapisi.py"
_IZ_YENI_TEST = "tools/zzz-yeni-test.py"
_IZ_YENI_MUT = "tools/zzz-yeni-mutasyon.py"
_IZ_YENI_DIR = "shop/test/zzz-yeni.mjs"          # DIR_PAT kolu
_IZ_POZITIF = (_IZ_YENI, _IZ_YENI_TEST, _IZ_YENI_MUT, _IZ_YENI_DIR)
_IZ_PUSH_YENI = "tools/zzz-push-kapisi.py"
_IZ_PUSH_DISI = "tools/zzz-wip-kapisi.py"
# NEGATIF kova: predikat gevserse (M-IZ3) BUNLAR sizar ve fikstur TEK BASINA kirmizi yakar.
# `zzz-uretilen-*`: `.gitignore` ile ELENIR -> `--exclude-standard` iddiasini FIILEN
# olcer (curutucu: fikstur `.gitignore`suz oldugu icin o iddia hic olculmuyordu).
_IZ_GITIGNORE = "zzz-uretilen-*\n"
_IZ_NEGATIF = ("tools/zzz-notlar.md", "tools/zzz-veri-mutasyon.json",
               "tools/alt/dizin/zzz-x-mutasyon.py", "tools/arsiv/zzz-eski-kapisi.py",
               "tools/zzz-uretilen-kapisi.py")
_IZ_DEPLOY = ("jobs:\n  a:\n    steps:\n      - name: taban\n"
              "        run: python3 %s\n" % _IZ_TABAN)


def _iz_yaz(depo, rel, metin):
    tam = os.path.join(depo, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(tam), exist_ok=True)
    with open(tam, "w", encoding="utf-8") as f:
        f.write(metin)


def izlenmeyen_fikstur_kontrol():
    """🔴 IZLENMEYEN KESIF KOVASI — ADIM ADIM SENARYO (9 Agu 2026 olculen korluk).

    Kanitlanan iddialar (her biri AYRI, her biri TEK BASINA kirilabilir):
      A1a TABAN HUKMU  — kova BOSKEN rc=0 (yoksa kirmizi 'hep kirmizi'dan ayrilmaz).
      A1b TABAN KOVASI — izlenmeyen dosya YOKKEN kova BOS (izlenen dosya SIZMAZ).
         🔴 A1a/A1b AYRI: birlesikken `--others` dusuren mutant TABAN HUKMUNU de
         zehirliyordu ve "kova bozuldu" ile "her sey bozuldu" ayrilmiyordu.
      A2 KOVA DOLUYOR  — `git add` EDILMEMIS DORT ad konvansiyonu (kapisi/test/
         mutasyon/DIR_PAT) da kovaya DUSER (kismi kapsam kaybi gorunur olur).
      A3 HUKUM KIRMIZI — o dosyalar icin rc=1 ve tani `HENUZ IZLENMIYOR (kapsamsiz)`.
      A4 `git add` SONRASI — dosya IZLENEN kesife gecer, kovadan CIKAR, hukum yine
         rc=1 ama tani bu kez `KAPSAMSIZ (ne kosuluyor ne izin listesinde)`.
      A5 NEGATIF YON   — `.md`/`.json`/alt dizin/`tools/arsiv/` VE `.gitignore` ile
         elenen uretilen artefakt kovaya SIZMAZ (`--exclude-standard` iddiasi
         FIILEN olculur; predikat gevsemesi TEK BASINA kirmizi yakar).
      A6 KAPSANAN IZLENMEYEN — cagri satiri OLAN izlenmeyen dosya hata DEGIL, BILGI.
      A7 OLCULEMEDI (TUKETIM) — kovaya sebep VERILINCE rc=1; "bos kova" SAYILMAZ.
      A8 OLCULEMEDI (URETIM)  — `kesfet_izlenmeyen()` git patlayinca SEBEP URETIR
         (git deposu OLMAYAN bir kokte olculur). A7 sebebi parametreyle aliyordu;
         uretim tarafi olculmeyince `return [], None` mutanti sessizce geciyordu.
      V1 IZLENEN-KORUNDU       — push disi olsa da izlenen kapsamsiz dosya KIRMIZI.
      V2 PUSH-YENI-KORUNDU     — ref/SHA araliginda gelen yeni dosya KIRMIZI.
      V3 PUSH-DISI-IZLENMEYEN  — ref/SHA araligi disindaki WIP UYARI + YESIL.
      F1 KAPSAM BILINMIYOR     — ref/SHA yoksa eski kati hukum KIRMIZI.

    (ok, hatalar) dondurur; hicbir sey BASMAZ."""
    global ROOT
    hata = []
    gecici = tempfile.mkdtemp(prefix="pruvo-izlenmeyen-fikstur-")
    eski_kok = ROOT
    # 🔴 IZIN LISTESI BOS: taban dosya `_IZ_DEPLOY` cagri satiriyla KAPSANIR. Muafiyet
    # kullanilsaydi "BAYAT izin (test ARTIK KOSULUYOR)" ekseni de kirmizi yakar ve
    # kirmizinin TEK eksenden geldigi iddiasi COKERDI ([[beyan-edilmis-survivor]]).
    izin = {}
    try:
        depo = os.path.join(gecici, "depo")
        os.makedirs(depo)

        def g(*a):
            return GIT_ORTAMI.sentetik_git(
                depo, *a, ayarlar=_FIKSTUR_GIT_AYAR,
                capture_output=True, text=True)

        r = g("init", "--quiet", "-b", "main")
        if r.returncode != 0:
            return False, ["IZLENMEYEN FIKSTURU OLCULEMEDI: git init rc=%d %s"
                           % (r.returncode, r.stderr.strip()[:200])]
        _iz_yaz(depo, _IZ_TABAN, "# fikstur taban\n")
        # `.gitignore` IZLENEN olur: `--exclude-standard` iddiasi ancak GERCEK bir
        # eleme kurali varken olculebilir (kural yoksa mutant sessizce gecer).
        _iz_yaz(depo, ".gitignore", _IZ_GITIGNORE)
        g("add", "-A")
        r = g("commit", "--quiet", "-m", "fikstur taban")
        if r.returncode != 0:
            return False, ["IZLENMEYEN FIKSTURU OLCULEMEDI: git commit rc=%d %s"
                           % (r.returncode, (r.stderr or r.stdout).strip()[:200])]
        ROOT = depo

        def hukum(kesif, iz, sebep=None):
            return denetle(_IZ_DEPLOY, kesif, izin, kontroller=False, akislar=None,
                           izlenmeyen=iz, izlenmeyen_sebep=sebep)

        # --- A1a/A1b: TABAN (yalniz izlenen taban dosya, kova BOS) ---
        iz0, sebep0 = kesfet_izlenmeyen()
        kod, satir = hukum(kesfet(), iz0, sebep0)
        if kod != 0:
            hata.append("A1a TABAN HUKMU YESIL DEGIL: rc=%d -> kirmizi iddialari "
                        "'hep kirmizi'dan AYIRT EDILEMEZ." % kod)
        if iz0 or sebep0:
            hata.append("A1b TABAN KOVASI BOS DEGIL: kova=%r sebep=%r -> izlenmeyen "
                        "dosya YOKKEN kovaya dosya giriyor (`--others` dusmus olabilir: "
                        "IZLENEN dosyalar kovaya doluyor)." % (iz0, sebep0))

        # --- ADIM 1: dosyalar YAZILDI, `git add` YOK ---
        for rel in _IZ_POZITIF:
            _iz_yaz(depo, rel, "# yeni kabul testi (henuz izlenmiyor)\n")
        for rel in _IZ_NEGATIF:
            _iz_yaz(depo, rel, "# negatif kova adayi\n")
        kesif1 = kesfet()
        iz1, sebep1 = kesfet_izlenmeyen()
        beklenen1 = sorted(_IZ_POZITIF)
        if sebep1:
            hata.append("A2 KOVA OKUNAMADI: %s" % sebep1)
        sizan_kesif = [y for y in _IZ_POZITIF if y in kesif1]
        if sizan_kesif:
            hata.append("A2 SIZINTI: `git add` EDILMEMIS dosya IZLENEN kesife girdi "
                        "(%r) -> kesfet() artik `git ls-files` demiyor." % sizan_kesif)
        if iz1 != beklenen1:
            eksik = [y for y in beklenen1 if y not in iz1]
            fazla = [y for y in iz1 if y not in beklenen1]
            hata.append(
                "A2/A5 IZLENMEYEN KOVA YANLIS: eksik=%r fazla=%r (beklenen %r, gelen "
                "%r) -> kova bir AD SINIFINI kaybetmis olabilir (KISMI KAPSAM: yalniz "
                "`-kapisi.py` goren mutant), `--others` dusmus, predikat gevsemis "
                "(.md/.json/alt dizin/arsiv siziyor) ya da `--exclude-standard` "
                "dusmus (.gitignore'lu uretilen artefakt siziyor)."
                % (eksik, fazla, beklenen1, iz1))
        kod, satir = hukum(kesif1, iz1, sebep1)
        rapor = "\n".join(satir)
        if kod != 1:
            hata.append(
                "A3 SESSIZ YESIL: `git add` EDILMEMIS kapsamsiz kapi varken rc=%d "
                "(beklenen 1) -> kova UYARI'ya cevrilmis olabilir (exit'e dokunmayan "
                "kova [[beyan-edilmis-survivor]] sinifidir)." % kod)
        eksik_tani = [y for y in beklenen1
                      if "HENUZ IZLENMIYOR (kapsamsiz): %s" % y not in rapor]
        if eksik_tani:
            hata.append("A3 TANI KAYIP: rapor `HENUZ IZLENMIYOR (kapsamsiz): <yol>` "
                        "satirini su dosyalar icin BASMIYOR: %r -> hukum dogru olsa "
                        "bile hangi dosya oldugu okunmaz." % eksik_tani)
        if "Henuz izlenmiyor (aday): %d" % len(beklenen1) not in rapor:
            hata.append("A3 SAYAC KAYIP/YANLIS: rapor satiri `Henuz izlenmiyor "
                        "(aday): %d` yok -> olculen sayi BASILMIYOR ya da kismi "
                        "kapsam sayaci sessizce kucultuyor." % len(beklenen1))

        # --- ADIM 2: `git add` yapildi -> IZLENEN kesife gecer, kova BOSALIR ---
        g("add", *_IZ_POZITIF)
        kesif2 = kesfet()
        iz2, sebep2 = kesfet_izlenmeyen()
        kesifte_yok = [y for y in _IZ_POZITIF if y not in kesif2]
        if kesifte_yok:
            hata.append("A4 REGRESYON: `git add` sonrasi su dosyalar IZLENEN kesifte "
                        "YOK: %r" % kesifte_yok)
        if iz2 != []:
            hata.append("A4 KOVA BOSALMADI: `git add` sonrasi izlenmeyen kova %r "
                        "-> `--exclude-standard`/`--others` semantigi bozulmus." % (iz2,))
        kod, satir = hukum(kesif2, iz2, sebep2)
        rapor = "\n".join(satir)
        if kod != 1:
            hata.append("A4 SESSIZ YESIL (izlenen kol): rc=%d (beklenen 1)." % kod)
        eksik4 = [y for y in _IZ_POZITIF
                  if "KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % y not in rapor]
        if eksik4:
            hata.append("A4 TANI KAYIP: `git add` sonrasi tani KAPSAMSIZ olmali "
                        "(HENUZ IZLENMIYOR degil); eksik: %r" % eksik4)
        if "HENUZ IZLENMIYOR" in rapor:
            hata.append("A4 ETIKET KARISTI: izlenen dosya icin `HENUZ IZLENMIYOR` "
                        "etiketi basildi -> iki kova ayni sey sanilir.")

        # --- A6: izlenmeyen ama KAPSANMIS (cagri satiri VAR) -> hata DEGIL ---
        kod, satir = hukum([], [_IZ_TABAN])
        rapor = "\n".join(satir)
        if kod != 0:
            hata.append("A6 YANLIS-KIRMIZI: cagri satiri OLAN izlenmeyen dosya icin "
                        "rc=%d (beklenen 0) -> kova kapsam sorusunu HIC sormuyor, "
                        "korlemesine kirmizi yakiyor." % kod)
        if "HENUZ IZLENMIYOR ama KAPSANMIS" not in rapor:
            hata.append("A6 BILGI SATIRI KAYIP: kapsanan izlenmeyen dosya rapora "
                        "HIC girmiyor -> gorunmeyen olcum olculmemis sayilir.")

        # --- A7: kova OKUNAMADI -> fail-closed (bos kova SAYILMAZ) ---
        # kesif KASTEN yalniz TABAN dosya: rc=1'in TEK sebebi OLCULEMEDI olsun.
        kod, satir = hukum([_IZ_TABAN], [], sebep="SENTETIK: git cagrisi patladi")
        rapor = "\n".join(satir)
        if kod != 1:
            hata.append("A7 FAIL-OPEN: kova OKUNAMAZKEN rc=%d (beklenen 1) -> "
                        "'olcemedim' sessizce 'temiz' sayiliyor." % kod)
        if "HENUZ IZLENMIYOR kovasi OKUNAMADI" not in rapor:
            hata.append("A7 TANI KAYIP: olculemedi sebebi rapora yazilmiyor.")

        # --- A8: OLCULEMEDI'nin URETIM tarafi (A7 sebebi PARAMETRE olarak aliyordu) ---
        # 🔴 KOSUM: git deposu OLMAYAN bir kok -> `git ls-files --others` rc!=0.
        # `kesfet_izlenmeyen()` burada BOS LISTE + None dondurmemeli; dondurseydi
        # "olcemedim" sessizce "temiz" sayilirdi ve A7 bunu GORMEZDI.
        depo_disi = os.path.join(gecici, "git-olmayan")
        os.makedirs(depo_disi, exist_ok=True)
        ROOT = depo_disi
        iz_yok, sebep_yok = kesfet_izlenmeyen()
        ROOT = depo
        if sebep_yok is None:
            hata.append(
                "A8 FAIL-OPEN (URETIM): `kesfet_izlenmeyen()` git deposu OLMAYAN "
                "kokte sebep=None dondurdu (kova=%r) -> git patlayinca kapi 'kova bos' "
                "sanir ve HICBIR yerde alarm calmaz." % (iz_yok,))
        elif iz_yok:
            hata.append("A8 CELISKI: sebep VAR ama kova DOLU (%r) -> olculemeyen "
                        "eksenden veri uretiliyor." % (iz_yok,))

        # --- V1/V2/V3: GERCEK ref/SHA araligindan push kapsami -----------------
        # ADIM 2'de staged olan dort aday artik "onceki/izlenen" tabana commitlenir.
        r = g("commit", "--quiet", "-m", "fikstur izlenen taban")
        if r.returncode != 0:
            hata.append("PUSH KAPSAM FIKSTURU OLCULEMEDI: taban commit rc=%d %s"
                        % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
        taban = g("rev-parse", "HEAD").stdout.strip()
        _iz_yaz(depo, _IZ_PUSH_YENI, "# bu push ile gelen yeni kapi\n")
        g("add", _IZ_PUSH_YENI)
        r = g("commit", "--quiet", "-m", "fikstur push yeni")
        if r.returncode != 0:
            hata.append("PUSH KAPSAM FIKSTURU OLCULEMEDI: yeni commit rc=%d %s"
                        % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
        yerel = g("rev-parse", "HEAD").stdout.strip()
        _iz_yaz(depo, _IZ_PUSH_DISI, "# baska oturumun commitlenmemis WIP dosyasi\n")
        ref_girdisi = "refs/heads/main %s refs/heads/main %s\n" % (yerel, taban)
        kapsam, kapsam_sebep = push_kapsamini_turet(ref_girdisi)

        # 1) Kapsam GERCEK git araligindan ve hatasiz turemeli.
        if kapsam is None or kapsam_sebep:
            hata.append("V-KAPSAM OLCULEMEDI: kapsam=%r sebep=%r"
                        % (kapsam, kapsam_sebep))
        else:
            # 2/3/4) Araligin pozitif ve iki negatif uyeligi.
            if _IZ_PUSH_YENI not in kapsam:
                hata.append("V2 PUSH KAPSAMI KOR: yeni commit dosyasi kapsamda YOK: %r"
                            % sorted(kapsam))
            if _IZ_YENI in kapsam:
                hata.append("V1 PUSH KAPSAMI SIZINTI: onceki izlenen dosya kapsamda")
            if _IZ_PUSH_DISI in kapsam:
                hata.append("V3 PUSH KAPSAMI SIZINTI: commitlenmemis WIP kapsamda")

            # 5) V1: IZLENEN ve kosmayan dosya push disi olsa da KIRMIZI.
            kod, satir = denetle("", [_IZ_YENI], {}, kontroller=False,
                                 izlenmeyen=[], push_kapsami=kapsam)
            rapor = "\n".join(satir)
            if kod != 1 or "KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % _IZ_YENI not in rapor:
                hata.append("V1 POZITIF KAYIP: izlenen+kapsamsiz dosya rc=%d, tani=%s"
                            % (kod, "VAR" if "KAPSAMSIZ" in rapor else "YOK"))

            # 6) V2: bu push ile gelen yeni/izlenen dosya KIRMIZI.
            kod, satir = denetle("", [_IZ_PUSH_YENI], {}, kontroller=False,
                                 izlenmeyen=[], push_kapsami=kapsam)
            rapor = "\n".join(satir)
            if kod != 1 or "KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % _IZ_PUSH_YENI not in rapor:
                hata.append("V2 POZITIF KAYIP: push-yeni+kapsamsiz dosya rc=%d, tani=%s"
                            % (kod, "VAR" if "KAPSAMSIZ" in rapor else "YOK"))

            # 7) V3: izlenmeyen + push disi WIP yalniz UYARI, hukum YESIL.
            kod, satir = denetle("", [], {}, kontroller=False,
                                 izlenmeyen=[_IZ_PUSH_DISI], push_kapsami=kapsam)
            rapor = "\n".join(satir)
            if (kod != 0
                    or "UYARI: HENUZ IZLENMIYOR ve PUSH KAPSAMI DISI: %s" % _IZ_PUSH_DISI not in rapor
                    or "HENUZ IZLENMIYOR (kapsamsiz): %s" % _IZ_PUSH_DISI in rapor):
                hata.append("V3 YANLIS HUKUM: push-disi WIP rc=%d; uyari=%s; kirmizi=%s"
                            % (kod, "VAR" if "PUSH KAPSAMI DISI" in rapor else "YOK",
                               "VAR" if "HENUZ IZLENMIYOR (kapsamsiz)" in rapor else "YOK"))

        # 8) Ref/SHA bilgisi yoksa eski kati davranis: fail-closed KIRMIZI.
        kod, satir = denetle("", [], {}, kontroller=False,
                             izlenmeyen=[_IZ_PUSH_DISI], push_kapsami=None,
                             push_kapsami_sebep="SENTETIK: ref bilgisi yok")
        if kod != 1 or not any("push kapsami BILINMIYOR" in s for s in satir):
            hata.append("F1 FAIL-CLOSED KAYIP: kapsam bilinmiyorken rc=%d" % kod)

        # 9) Bozuk pre-push satiri kapsam UYDURMAMALI.
        bozuk_kapsam, bozuk_sebep = push_kapsamini_turet("bozuk satir\n")
        if bozuk_kapsam is not None or not bozuk_sebep:
            hata.append("F2 BOZUK REF GIRDISI FAIL-OPEN: kapsam=%r sebep=%r"
                        % (bozuk_kapsam, bozuk_sebep))
    except Exception as e:  # noqa: BLE001 — fikstur kapiyi patlatmaz, konusur
        hata.append("IZLENMEYEN FIKSTURU OLCULEMEDI: %s: %s" % (type(e).__name__, e))
        # (A8 ROOT'u gecici olarak degistirir; asagidaki finally onu geri alir.)
    finally:
        ROOT = eski_kok
        shutil.rmtree(gecici, ignore_errors=True)
    return (not hata), hata


# ---- main() KABLO FIKSTURU (UCTAN UCA, SENTETIK DEPO) -----------------------
_MK_DEPLOY = (
    "on:\n"
    "  push:\n"
    "    branches: [main]\n"
    "jobs:\n"
    "  a:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - name: taban\n"
    "        run: python3 %s\n" % _IZ_TABAN)
_MK_YENI = "tools/zzz-kablo-kapisi.py"


# 🔴 YENIDEN GIRIS KILIDI (9 Agu, ikinci tur): bu fikstur ALTI modul global'ini
# gecici olarak eziyor ve `main()`'i ozyinelemeli cagiriyor — ustelik PUSH
# KANCASININ ICINDE kosuyor. Ic ice giris olursa ikinci `finally` SENTETIK degerleri
# "asil" sanip geri yazar ve gercek ROOT/IZIN_LISTESI KALICI olarak bozulur.
# Kilit bunu fail-closed reddeder; `main_kablosu_kontrol()` bunu ayrica OLCER.
_KABLO_FIKSTURU_ICINDE = False


# 🔴 AYIRT EDICI JETONLAR (UCUNCU TUR, Z2): "yeniden giris reddedildi" mesaji ile
# "zorlanan istisna olculdu" mesaji AYNI kelimeyi (`OLCULEMEDI`) tasiyordu. Bayrak
# `finally`de sifirlanmayinca 2. ve 3. cagri ERKEN DONUYOR, K5'in `any("OLCULEMEDI")`
# kontrolu REDDETME mesajiyla tatmin oluyor ve K5/K6 sessizce NO-OP'a donuyordu —
# nobetci YESIL rapor ediyordu ([[damga-finally-tuzagi]] · [[beyan-edilmis-survivor]]).
_KABLO_ISTISNA_JETONU = "ZORLANAN-ISTISNA-OLCUMU"
_KABLO_REDDETME_JETONU = "YENIDEN-GIRIS-REDDEDILDI"


def _kablo_global_anlik():
    """Fiksturun ezdigi kuresel durumun PARMAK IZI (sizinti olcumu icin).

    🔴 BAYRAK DA PARMAK IZINDE: `_KABLO_FIKSTURU_ICINDE` disarida birakilinca
    "bayrak asili kaldi" hali sizinti sayilmiyordu (olculdu: Z2 mutanti 4/4 yesil)."""
    return (ROOT, DEPLOY_VARSAYILAN, id(IZIN_LISTESI), len(IZIN_LISTESI),
            id(ALT_KUME_IZIN_LISTESI), len(ALT_KUME_IZIN_LISTESI),
            kesfet_izlenmeyen, tuple(sys.argv), sys.stdout,
            _KABLO_FIKSTURU_ICINDE)


def main_kablosu_kontrol():
    """KABLO iddiasi + fiksturun KENDI YAN ETKISININ olcumu.

    K1..K3 kablo iddialari `_main_kablosu_govdesi()`de; burada AYRICA:
      K4 SIZINTI (normal yol)  — ezilen 6 global birebir geri yuklendi mi.
      K5 SIZINTI (istisna yolu) — govde ORTASINDA istisna atilinca da geri yuklendi mi
         (tek `finally` bu kadar kuresel durumu tasiyor; 'bakildi iyi' KABUL DEGIL).
      K6 YENIDEN GIRIS — ic ice cagri fail-closed REDDEDILIYOR mu (kabul edilseydi
         ikinci `finally` SENTETIK degerleri kalici yazardi).
    """
    once = _kablo_global_anlik()
    hata = _main_kablosu_govdesi()
    sonra = _kablo_global_anlik()
    if once != sonra:
        hata.append("K4 KURESEL SIZINTI (normal yol): fikstur sonrasi durum "
                    "DEGISMIS. once=%r sonra=%r" % (once[:2], sonra[:2]))
    # K5 — ISTISNA YOLU: govde ortasinda patlat, `finally` yine geri yuklemeli.
    istisna_hata = _main_kablosu_govdesi(_zorla_istisna=True)
    sonra2 = _kablo_global_anlik()
    if once != sonra2:
        hata.append("K5 KURESEL SIZINTI (ISTISNA yolu): govde ortasinda istisna "
                    "atilinca durum GERI YUKLENMEDI. once=%r sonra=%r"
                    % (once[:2], sonra2[:2]))
    # 🔴 AYIRT EDICI JETON SART: "OLCULEMEDI" kelimesi REDDETME mesajinda da geciyordu
    # ve K5 onunla tatmin oluyordu (Z2). Artik YALNIZ zorlanan istisnanin jetonu sayar.
    if not any(_KABLO_ISTISNA_JETONU in h for h in istisna_hata):
        hata.append("K5 SESSIZ YUTMA: ZORLANAN istisna raporlanmadi (jeton `%s` yok; "
                    "gelen=%r) -> govde ya hic kosmadi (bayrak asili kalmis olabilir) "
                    "ya da istisna sessizce yutuldu."
                    % (_KABLO_ISTISNA_JETONU, [h[:80] for h in istisna_hata[:2]]))
    if any(_KABLO_REDDETME_JETONU in h for h in istisna_hata):
        hata.append("K5 ERKEN DONUS: govde `%s` ile ERKEN dondu -> istisna yolu HIC "
                    "olculmedi (yeniden giris bayragi bir onceki cagridan ASILI "
                    "kalmis; `finally` sifirlamiyor olabilir)." % _KABLO_REDDETME_JETONU)
    # K6 — YENIDEN GIRIS: kilit acikken cagri REDDEDILMELI, globaller KORUNMALI.
    global _KABLO_FIKSTURU_ICINDE
    _KABLO_FIKSTURU_ICINDE = True
    try:
        yeniden = _main_kablosu_govdesi()
    finally:
        _KABLO_FIKSTURU_ICINDE = False
    sonra3 = _kablo_global_anlik()
    if not any(_KABLO_REDDETME_JETONU in h for h in yeniden):
        hata.append("K6 YENIDEN GIRIS KILIDI YOK: ic ice cagri kabul edildi -> ikinci "
                    "`finally` SENTETIK ROOT/IZIN_LISTESI degerlerini KALICI yazabilir "
                    "(bu fikstur PUSH KANCASININ icinde kosuyor).")
    if once != sonra3:
        hata.append("K6 KURESEL SIZINTI (yeniden giris yolu): durum DEGISMIS.")
    return (not hata), hata


def _main_kablosu_govdesi(_zorla_istisna=False):
    """🔴 KABLO IDDIASI — `main()` olcumu `denetle()`'ye FIILEN GECIRIYOR MU.

    OLCULEN DELIK (9 Agu 2026, bagimsiz curutucu): butun kova iddialari
    `denetle()`'yi DOGRUDAN cagiriyordu (`hukum(kesif, iz, sebep)`), yani
    `main()` -> `kesfet_izlenmeyen()` -> `denetle()` KABLOSU hicbir yerde
    olculmuyordu. Iki tek-satirlik mutant kapiyi TAM KOR birakip (rc=0, gercek
    agacta 3 izlenmeyen+kapsamsiz dosya varken) DORT bataryayi da YESIL
    biraktı: `izlenmeyen=None` (Y4) ve `izlenmeyen=[]` (Y8). Kanonik sinif:
    [[nobetci-cagri-satiri-nobetsiz]] — ozellik duruyor, kablosu yok.

    YONTEM: SENTETIK depoda `main()` UCTAN UCA kosulur (argparse dahil), stdout
    yakalanir. GERCEK depoya DOKUNULMAZ.
    🔴 OZYINELEME KORUMASI: `--deploy` ACIKCA verilir ve `DEPLOY_VARSAYILAN`
    BASKA bir yola cevrilir -> `gercek_deploy=False` -> `kontroller=False`, yani
    main() bu fiksturu (ve kardeslerini) TEKRAR cagirmaz.

    Iddialar:
      K1 TABAN   — izlenmeyen dosya YOKKEN main() rc=0 (kirmizi anlamli olsun).
      K2 KABLO   — izlenmeyen+kapsamsiz dosya VARKEN main() rc=1 ve dosya adi
         raporda; `izlenmeyen=None`/`[]` mutantlari BURADA duser.
      K3 SEBEP KABLOSU — `kesfet_izlenmeyen()` SEBEP dondururse main() onu
         `denetle()`'ye gecirir (rc=1 + `kovasi OKUNAMADI`); sebebi yutan mutant duser.

    [hata, ...] dondurur (LISTE); hicbir sey BASMAZ."""
    global ROOT, DEPLOY_VARSAYILAN, IZIN_LISTESI, ALT_KUME_IZIN_LISTESI
    global kesfet_izlenmeyen, _KABLO_FIKSTURU_ICINDE
    hata = []
    if _KABLO_FIKSTURU_ICINDE:
        return ["MAIN KABLO FIKSTURU %s: fikstur zaten kosuyor. Ic ice giris kabul "
                "edilseydi ikinci `finally` SENTETIK ROOT/IZIN_LISTESI degerlerini "
                "KALICI yazardi (fail-closed)." % _KABLO_REDDETME_JETONU]
    gecici = tempfile.mkdtemp(prefix="pruvo-main-kablo-fikstur-")
    saklanan = (ROOT, DEPLOY_VARSAYILAN, IZIN_LISTESI, ALT_KUME_IZIN_LISTESI,
                kesfet_izlenmeyen, sys.argv)
    _KABLO_FIKSTURU_ICINDE = True
    try:
        depo = os.path.join(gecici, "depo")
        os.makedirs(depo)

        def g(*a):
            return GIT_ORTAMI.sentetik_git(
                depo, *a, ayarlar=_FIKSTUR_GIT_AYAR,
                capture_output=True, text=True)

        r = g("init", "--quiet", "-b", "main")
        if r.returncode != 0:
            return ["MAIN KABLO FIKSTURU OLCULEMEDI: git init rc=%d %s"
                    % (r.returncode, r.stderr.strip()[:200])]
        _iz_yaz(depo, _IZ_TABAN, "# fikstur taban\n")
        _iz_yaz(depo, ".github/workflows/deploy.yml", _MK_DEPLOY)
        g("add", "-A")
        r = g("commit", "--quiet", "-m", "fikstur taban")
        if r.returncode != 0:
            return ["MAIN KABLO FIKSTURU OLCULEMEDI: git commit rc=%d %s"
                    % (r.returncode, (r.stderr or r.stdout).strip()[:200])]

        deploy_yolu = os.path.join(depo, ".github", "workflows", "deploy.yml")
        ROOT = depo
        # 🔴 `--deploy` ACIKCA verilir, VARSAYILAN baska yola cevrilir -> kontroller=False.
        DEPLOY_VARSAYILAN = os.path.join(gecici, "kullanilmayan-deploy.yml")
        IZIN_LISTESI = {}
        ALT_KUME_IZIN_LISTESI = {}
        if _zorla_istisna:
            # K5 SEAM: globaller EZILDIKTEN sonra patlat -> `finally`nin gercekten
            # geri yukledigi OLCULUR ("bakildi iyi" degil, kosulan iddia).
            raise RuntimeError("%s — SENTETIK: `finally` geri-yukleme yolunu olcmek "
                               "icin bilincli olarak atildi" % _KABLO_ISTISNA_JETONU)

        def kos():
            sys.argv = ["ci-kapsam-test.py", "--deploy", deploy_yolu]
            tampon = io.StringIO()
            eski_cikti = sys.stdout
            sys.stdout = tampon
            try:
                kod = main()
            finally:
                sys.stdout = eski_cikti
            return kod, tampon.getvalue()

        # --- K1: TABAN (izlenmeyen dosya YOK) -> rc=0 ---
        kod, cikti = kos()
        if kod != 0:
            hata.append("K1 TABAN KIRMIZI: sentetik depoda izlenmeyen dosya YOKKEN "
                        "main() rc=%d (beklenen 0) -> K2'nin kirmizisi 'hep kirmizi'dan "
                        "AYIRT EDILEMEZ. Cikti kuyrugu: %s"
                        % (kod, cikti.strip().splitlines()[-1:] or "-"))
        if "Henuz izlenmiyor (aday): 0" not in cikti:
            hata.append("K1 KABLO KOPUK (TABAN): main() ciktisinda `Henuz izlenmiyor "
                        "(aday): 0` satiri YOK -> olcum `denetle()`'ye HIC gecmiyor "
                        "(izlenmeyen=None mutanti tam burada yasar).")

        # --- K2: izlenmeyen + kapsamsiz dosya VAR -> rc=1 + adiyla basilmali ---
        _iz_yaz(depo, _MK_YENI, "# yeni kapi (henuz izlenmiyor)\n")
        kod, cikti = kos()
        if kod != 1:
            hata.append(
                "K2 KABLO KOPUK: calisma agacinda izlenmeyen+kapsamsiz `%s` VARKEN "
                "main() rc=%d (beklenen 1) -> `main()` olcumu `denetle()`'ye "
                "GECIRMIYOR (izlenmeyen=None / izlenmeyen=[] sinifi). Ozellik "
                "duruyor ama KABLOSU YOK ([[nobetci-cagri-satiri-nobetsiz]])."
                % (_MK_YENI, kod))
        if "HENUZ IZLENMIYOR (kapsamsiz): %s" % _MK_YENI not in cikti:
            hata.append("K2 TANI KAYIP: main() ciktisi `HENUZ IZLENMIYOR (kapsamsiz): "
                        "%s` satirini BASMIYOR." % _MK_YENI)
        if "Henuz izlenmiyor (aday): 1" not in cikti:
            hata.append("K2 SAYAC KAYIP: main() ciktisinda `Henuz izlenmiyor "
                        "(aday): 1` satiri YOK -> kova bosaltilmis olabilir.")
        os.remove(os.path.join(depo, _MK_YENI.replace("/", os.sep)))

        # --- K3: URETIM SEBEBI main() tarafindan YUTULMAMALI ---
        kesfet_izlenmeyen = lambda: ([], "SENTETIK: uretim tarafi sebep")  # noqa: E731
        kod, cikti = kos()
        if kod != 1:
            hata.append("K3 SEBEP YUTULDU: `kesfet_izlenmeyen()` SEBEP dondururken "
                        "main() rc=%d (beklenen 1) -> olculemedi hali sessizce "
                        "'temiz' sayiliyor." % kod)
        if "HENUZ IZLENMIYOR kovasi OKUNAMADI" not in cikti:
            hata.append("K3 TANI KAYIP: uretim sebebi main() ciktisina HIC yazilmiyor "
                        "-> `izlenmeyen_sebep` argumani main()'de dusurulmus olabilir.")
    except Exception as e:  # noqa: BLE001 — fikstur kapiyi patlatmaz, konusur
        hata.append("MAIN KABLO FIKSTURU OLCULEMEDI: %s: %s" % (type(e).__name__, e))
    finally:
        (ROOT, DEPLOY_VARSAYILAN, IZIN_LISTESI, ALT_KUME_IZIN_LISTESI,
         kesfet_izlenmeyen, sys.argv) = saklanan
        _KABLO_FIKSTURU_ICINDE = False
        shutil.rmtree(gecici, ignore_errors=True)
    return hata


# ---- pre-push KABLO NOBETCISI (KOSUL + BAYRAK + VARLIK EKSENI) --------------
# 🔴 OLCULEN DELIK (9 Agu 2026, bagimsiz curutucu): kayit raseti (kanca-nobeti
# BEKLENEN + kanca-kablolama FAIL_CLOSED) YALNIZ "cagri satiri var mi / `exit` var
# mi" sorusunu soruyor. Iki mutant uc nobetciyi de YESIL birakti:
#   P4) cagri `--kendini-test` koluna cevrildi -> push kapisi GERCEK calisma agacini
#       HIC olcmez (olculdu: agacta 3 izlenmeyen+kapsamsiz dosya varken bayraksiz
#       kol rc=1, `--kendini-test` rc=0).
#   P5) kosul `-ne 0` yerine `-eq 12345` -> kapi rc=1 iken kanca rc=0, PUSH GECTI.
# Bu, kanonik [[kapi-beyanin-dogrulugunu-degil-varligini-olcer]] sinifidir: kayit
# BEYANIN VARLIGINI olcuyor, DAVRANISINI degil. Asagidaki nobetci davranisi olcer.
PRE_PUSH_YOLU = os.path.join(TOOLS, "kancalar", "pre-push")
_PP_KAPI = "tools/ci-kapsam-test.py"
_PP_CAGRI_RE = re.compile(
    r"^(?P<one>[^\n]*?)python3\s+\"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/tools/"
    r"ci-kapsam-test\.py\"?(?P<arg>[^\n]*)$")
_PP_RC_YAKALA_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=\$\?\s*$")
# SIFIR-DISI kosul bicimleri (mesru varyantlar): `-ne 0` · `!= 0` · `-gt 0`.
_PP_SIFIR_DISI_RE = re.compile(r"-ne\s+\"?0\"?|!=\s*\"?0\"?|-gt\s+\"?0\"?")
_PP_VARLIK_POZ_RE = re.compile(
    r"\[\s*-f\s+\"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/tools/ci-kapsam-test\.py\"\s*\]")
_PP_CIKIS_RE = re.compile(r"^exit\s+[1-9]")


def _pre_push_tanisi(govde):
    """🟡 IKINCIL — YALNIZ TANI METNI URETIR, HUKUM VERMEZ (9 Agu, ikinci tur).

    Bu fonksiyon bir KABUK TAKLIDIDIR; taklit hakim olursa gercek `sh`te fail-open
    olan govdeler (N1 yeniden atama, N3 `if false` sarmali) YESIL gecer — olculdu.
    Hukum artik `pre_push_kablo_kontrol()`'un DAVRANIS ayagindadir; buradan donen
    satirlar yalniz "hangi satirda ne gorundu" tanisidir."""
    hata = []
    satirlar = govde.splitlines()
    if _PP_VARLIK_POZ_RE.search(govde):
        hata.append(
            "ARAC YOKSA SESSIZ ATLANIYOR: `[ -f \"$kok/%s\" ]` POZITIF varlik kapisi "
            "kullaniliyor -> dosya yoksa kanca rc=0 verir ve PUSH GECER. Kardes "
            "`gecmis-geri-donus` blogu ayni halde `exit 1` veriyor; 'kapiyi kosamadim' "
            "sessizce 'kapi yesil' DEMEK DEGILDIR (fail-closed simetrisi)." % _PP_KAPI)
    anlamli = []
    for i, s in enumerate(satirlar):
        m = _PP_CAGRI_RE.match(s)
        if not m or s.lstrip().startswith("#"):
            continue
        one, arg = m.group("one"), m.group("arg")
        if any(j in one for j in ("echo ", "grep ", "printf ")):
            continue          # MENSIYON, icra degil
        if "--help" in arg or "--version" in arg or "-h " in arg:
            continue          # ICRA DISI bayrak
        anlamli.append((i, s, arg))
    if not anlamli:
        hata.append(
            "CAGRI YOK: pre-push govdesinde `%s`'i ANLAMLI olarak ICRA EDEN satir yok "
            "(silinmis, yoruma alinmis ya da yalniz `echo`/`--help` mensiyonu) -> push "
            "kapisi HIC kosmaz ([[nobetci-cagri-satiri-nobetsiz]])." % _PP_KAPI)
        return hata
    for i, s, arg in anlamli:
        if KENDINI_TEST_BAYRAGI in arg:
            hata.append(
                "CAGRI `%s` KOLUNA CEVRILMIS (satir %d): o kol GERCEK calisma agacini "
                "HIC olcmez (olculdu: agacta izlenmeyen+kapsamsiz dosya varken "
                "bayraksiz kol rc=1, `%s` rc=0). Push kapisi, eklendigi korlugu "
                "gormeyen kola indirgenmis olur."
                % (KENDINI_TEST_BAYRAGI, i + 1, KENDINI_TEST_BAYRAGI))
        if "--pre-push" not in arg:
            hata.append(
                "PRE-PUSH KAPSAM BAYRAGI YOK (satir %d): git'in ref/SHA stdin'i "
                "kapsam kapisina aktarilmiyor; izlenmeyen WIP icin push kapsami "
                "TURETILEMEZ ve kapi eski kati hukumde kalir." % (i + 1))
        if "</dev/null" in s:
            hata.append(
                "PRE-PUSH STDIN KESILMIS (satir %d): ref/SHA girdisi /dev/null'a "
                "yonlenmis; push kapsami turetilemez." % (i + 1))
        if "|| true" in s or "|| :" in s:
            hata.append("RC YUTULMUS (satir %d): `|| true` / `|| :` -> kapi KIRMIZI "
                        "olsa bile kanca 0 gorur." % (i + 1))
        rc_degisken, rc_i = None, None
        for j in range(i + 1, min(i + 6, len(satirlar))):
            m2 = _PP_RC_YAKALA_RE.match(satirlar[j])
            if m2:
                rc_degisken, rc_i = m2.group(1), j
                break
        if rc_degisken is None:
            hata.append("RC YAKALANMIYOR (satir %d): cagriyi izleyen 5 satirda "
                        "`<degisken>=$?` yok -> cikis kodu hukme HIC girmiyor."
                        % (i + 1))
            continue
        kosul_i = None
        for j in range(rc_i + 1, len(satirlar)):
            if ("$" + rc_degisken) in satirlar[j] and satirlar[j].lstrip().startswith("if "):
                kosul_i = j
                break
        if kosul_i is None:
            hata.append("KOSUL YOK: yakalanan rc (`%s`) hicbir `if` kosulunda "
                        "kullanilmiyor -> olculen deger hukme girmiyor." % rc_degisken)
            continue
        if not _PP_SIFIR_DISI_RE.search(satirlar[kosul_i]):
            hata.append(
                "KOSUL SIFIR-DISI DEGIL (satir %d): `%s` -> kapi KIRMIZI iken blok "
                "ATESLENMEYEBILIR. Olculdu: `-eq 12345` mutantinda kapi rc=1 iken "
                "kanca rc=0 verdi ve PUSH GECTI; uc kayit nobetcisi de YESIL kaldi."
                % (kosul_i + 1, satirlar[kosul_i].strip()[:90]))
        cikis_var = False
        for j in range(kosul_i + 1, len(satirlar)):
            g2 = satirlar[j].strip()
            if g2 == "fi":
                break
            if _PP_CIKIS_RE.match(g2):
                cikis_var = True
                break
        if not cikis_var:
            hata.append("EXIT YOK (kosul satiri %d): kapi KIRMIZI iken blok sifir-disi "
                        "`exit` VERMIYOR -> push DURMAZ." % (kosul_i + 1))
    return hata


# ---- DAVRANIS AYAGI: GERCEK `sh` (BIRINCIL HAKIM) --------------------------
# 🔴 NEDEN REGEX HAKIM OLAMAZ (9 Agu 2026, IKINCI TUR curutme): yukaridaki
# `_pre_push_tanisi()` bir KABUK TAKLIDIDIR. Gercek `sh`te fail-open olan IKI govde
# ondan YESIL geciyordu ve 7 kardes nobetci de yesildi:
#   N1) `pruvo_kapsam_rc=$?` satirinin ALTINA `pruvo_kapsam_rc=0` -> PUSH GECTI
#   N3) blogun tamami `if false; then … fi` icine alindi        -> PUSH GECTI
# Regex'e "yeniden atama" + "if false" deseni eklemek TEKIL YAMADIR ve sinifi
# KAPATMAZ ([[tekil-yama-sinifi-kapatmaz]] · [[mimar-kapi-parser-taklidi]]).
# COZUM: hukmu KABUK VERIR. Blok sentetik bir git deposunda `sh` ile FIILEN kosar,
# sahte kapi betiginin rc'si secilir ve KANCANIN rc'si olculur. Regex yalnizca
# TANI metni uretir; ok/kirmizi hukmune GIRMEZ.
_PP_BLOK_BAS = "# --- 0b) CI KAPSAM KAPISI"
# 14 Agu 2026: capa KOMSU bolumun basligindan 0b'nin KENDI bitis satirina tasindi.
# Eski hali "bir sonraki bolum nerede basliyorsa 0b orada bitiyordur" varsayimiydi;
# araya bolum eklenince (K80/0c) fikstur yabanci bir adimi kosturdu ve yanlis-kirmizi
# verdi. Capa artik bolumun KENDISINE ait ([[kapi-anchor-coupling-ikilemi]]).
_PP_BLOK_SON = "# --- 0b) SONU (FIKSTUR CAPASI"
# Sahte kapi: BAYRAKSIZ cagrida secilen rc'yi, `--kendini-test` cagrisinda 0 dondurur.
# 🔴 BU MODEL OLCULMUSTUR: gercek agacta 3 izlenmeyen+kapsamsiz dosya varken
# bayraksiz kol rc=1, `--kendini-test` rc=0 verdi. Sahte kapi bu ASIMETRIYI taklit
# eder; etmeseydi P4 (kolu degistirme) davranissal ayakta GORUNMEZDI.
_PP_SAHTE_KAPI = (
    "import sys\n"
    "print('SAHTE KAPI CIKTISI')\n"
    "girdi = sys.stdin.read().split()\n"
    "if '--kendini-test' in sys.argv[1:]:\n"
    "    sys.exit(0)\n"
    "if '--pre-push' not in sys.argv[1:] or not girdi or len(girdi) %% 4:\n"
    "    sys.exit(2)\n"
    "sys.exit(%d)\n")


def _pp_blok(govde):
    """<govde>'den YALNIZ 0b blogunu kes (fail-closed: isaretci yoksa istisna).

    Tam kanca kosulsa sonraki bloklar (sizinti kapisi, D1) kendi `exit`leriyle
    rc'yi kirletir ve hukum TEK EKSENDEN gelmez ([[beyan-edilmis-survivor]])."""
    if _PP_BLOK_BAS not in govde or _PP_BLOK_SON not in govde:
        raise RuntimeError(
            "PRE-PUSH BLOK ISARETCISI YOK (`%s` / `%s`) -> davranis ayagi kosulamaz; "
            "sessizce 'olctum' DENMEZ." % (_PP_BLOK_BAS, _PP_BLOK_SON))
    bas = govde.index(_PP_BLOK_BAS)
    son = govde.index(_PP_BLOK_SON)
    if son <= bas:
        raise RuntimeError("PRE-PUSH BLOK ISARETCILERI TERS SIRADA -> kesit gecersiz.")
    return "#!/bin/sh\n" + govde[bas:son] + "\nexit 0\n"


# 🔴 ORTAM SADAKATI (9 Agu 2026, UCUNCU TUR curutme): blok CIPLAK `sh` ile
# kosuluyordu. Olculdu (X4): blogu `if [ -z "$GIT_EXEC_PATH" ]` sarmalina almak
# fiksturde YESIL geciyor ama GERCEK `git push`ta blogu TAMAMEN susturuyor ->
# kanca rc=0, PUSH GECTI, alti nobetci de yesil. Bu, 2. turda kapatilan `if false`
# sinifinin ORTAM eksenindeki ikizidir.
# 🔴 NEDEN "eksik ENV degiskenini ekle" DEGIL: ortam kumesini elle saymak TEKIL
# YAMADIR ([[tekil-yama-sinifi-kapatmaz]]) — yarin git baska bir degisken ihrac
# eder ve ayni delik geri gelir. Sinifi kapatan TEK yol, kancanin GERCEKTEN git
# tarafindan cagrilmasidir ([[nobetci-fikstur-sekli]]): sentetik depo + BARE uzak
# + gercek `git push`. Ortam kumesi boylece git'in KENDISINDEN turer.
_PP_GIT_AYAR = ("-c", "commit.gpgsign=false", "-c", "core.excludesFile=",
                "-c", "gc.auto=0")


class _PpKosucu(object):
    """Sentetik depo + BARE uzak; blok GERCEK `git push` ile (git ortaminda) kosar.

    Depo BIR KEZ kurulur; her kosumda yalniz kanca dosyasi + sahte kapi yazilir ve
    YENI bir uzak ref'e push edilir (ayni ref'e ikinci push 'up-to-date' olur ve
    kanca HIC kosmaz — sessiz sahte-YESIL olurdu)."""

    def __init__(self, gecici):
        self.depo = os.path.join(gecici, "depo")
        self.uzak = os.path.join(gecici, "uzak.git")
        self.kanca_dizini = os.path.join(gecici, "kancalar")
        os.makedirs(os.path.join(self.depo, "tools"))
        os.makedirs(self.kanca_dizini)

        def g(*a):
            ayarlar = _PP_GIT_AYAR + ("-c", "core.hooksPath=" + self.kanca_dizini)
            return GIT_ORTAMI.sentetik_git(
                self.depo, *a, ayarlar=ayarlar, capture_output=True, text=True)

        r = GIT_ORTAMI.sentetik_git(
            gecici, "init", "--quiet", "--bare", "-b", "main", self.uzak,
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("PP DAVRANIS FIKSTURU: bare init rc=%d %s"
                               % (r.returncode, r.stderr.strip()[:200]))
        r = g("init", "--quiet", "-b", "main")
        if r.returncode != 0:
            raise RuntimeError("PP DAVRANIS FIKSTURU: git init rc=%d %s"
                               % (r.returncode, r.stderr.strip()[:200]))
        # 🔴 hooksPART YALNIZ BIZIM DIZIN: bu makinede GLOBAL hooksPath PRUVO
        # kancalarina bakiyor; ezilmezse sentetik push GERCEK kancalari kosardi.
        with open(os.path.join(self.depo, "a.txt"), "w", encoding="utf-8") as f:
            f.write("x\n")
        g("add", "-A")
        r = g("commit", "--quiet", "-m", "fikstur taban")
        if r.returncode != 0:
            raise RuntimeError("PP DAVRANIS FIKSTURU: git commit rc=%d %s"
                               % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
        self.kanca = os.path.join(self.kanca_dizini, "pre-push")
        self.kapi = os.path.join(self.depo, "tools", "ci-kapsam-test.py")
        self.sayac = 0

    def kos(self, blok, kapi_rc, arac_var=True):
        """(push_rc, cikti) — blok GERCEK `git push` icinde, GIT ORTAMIYLA kosar."""
        with open(self.kanca, "w", encoding="utf-8") as f:
            f.write(blok)
        os.chmod(self.kanca, 0o755)
        if arac_var:
            with open(self.kapi, "w", encoding="utf-8") as f:
                f.write(_PP_SAHTE_KAPI % kapi_rc)
        elif os.path.exists(self.kapi):
            os.remove(self.kapi)
        self.sayac += 1
        p = GIT_ORTAMI.sentetik_git(
            self.depo, "push", "--quiet", self.uzak,
            "HEAD:refs/heads/d%d" % self.sayac,
            ayarlar=_PP_GIT_AYAR + ("-c", "core.hooksPath=" + self.kanca_dizini),
            capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout + p.stderr


# DAVRANIS SOZLESMESI — her govde bu UC vakada olculur.
# (etiket, kapi_rc, arac_var, kanca_rc_sifir_disi_olmali, NEDEN)
PRE_PUSH_DAVRANIS_VAKALARI = (
    ("D1 kapi KIRMIZI", 1, True, True,
     "kapi rc=1 iken kanca PUSH'u DURDURMALI (fail-closed cekirdek)"),
    ("D2 kapi YESIL", 0, True, False,
     "kapi rc=0 iken kanca GECIRMELI (yanlis-kirmizi tum ekibin yayinini durdurur)"),
    ("D3 arac YOK", 0, False, True,
     "arac dosyasi yoksa da DURMALI (kardes `gecmis-geri-donus` blogu ile simetri)"),
)

# (etiket, ((capa, ikame, adet), ...), beklenen_ok, NEDEN)
# 🔴 CAPALAR KISA VE BICIMDEN BAGIMSIZ: ikinci turda `&& [ 1 -eq 2 ]` eklenen bir
# govdede TAM SATIR capalari 0 kez tutup COKME ureti (kirmizi ile karisti,
# [[mutasyon-kaniti-yeniden-uretilebilir]]). Artik capa `"$pruvo_kapsam_rc" -ne 0`
# gibi EN KISA ayirt edici parcadir.
PRE_PUSH_MUTANTLARI = (
    ("SAGLAM", (), True, "gercek IZLENEN govde — taban yesil olmali"),
    ("P1 cagri baska araca cevrildi",
     (('python3 "$pruvo_kapsam_kok/tools/ci-kapsam-test.py"',
       'python3 "$pruvo_kapsam_kok/tools/zzz-yok.py"', 1),), False,
     "cagri satiri silinme/degisme ekseni"),
    ("P1b cagri yoruma alindi",
     (('pruvo_kapsam_cikti=$(python3', '# pruvo_kapsam_cikti=$(python3', 1),), False,
     "yorum korlugu ekseni"),
    ("P2 rc blogundaki `exit 1` dusuruldu",
     (('kayitli)." >&2\n  exit 1', 'kayitli)." >&2\n  :', 1),), False,
     "kirmizi gorulur ama push DURMAZ"),
    ("P3 rc `|| true` ile yutuldu",
     (('< "$pruvo_kapsam_girdi")', '</dev/null) || true', 1),), False,
     "cikis kodu yutma ekseni"),
    ("P4 cagri `--kendini-test` koluna cevrildi",
     (('ci-kapsam-test.py" --pre-push 2>&1',
       'ci-kapsam-test.py" --kendini-test 2>&1', 1),), False,
     "gercek agac HIC olculmez (kol asimetrisi olculdu)"),
    ("P7 `--pre-push` bayragi dusuruldu",
     (('ci-kapsam-test.py" --pre-push 2>&1', 'ci-kapsam-test.py" 2>&1', 1),), False,
     "git ref/SHA girdisi olsa da kapsam kolu etkinlesmez; fail-closed durmali"),
    ("P5 kosul asla ateslenmiyor",
     (('"$pruvo_kapsam_rc" -ne 0', '"$pruvo_kapsam_rc" -eq 12345', 1),), False,
     "kapi rc=1 iken PUSH GECIYOR (birinci tur deligi)"),
    ("P6 varlik kapisi POZITIFE cevrildi (sessiz atlama)",
     (('[ -z "$pruvo_kapsam_kok" ] || [ ! -f', '[ -n "$pruvo_kapsam_kok" ] && [ -f', 1),),
     False, "arac yoksa kanca rc=0 -> PUSH GECER"),
    ("N1 rc YENIDEN ATANIYOR (`pruvo_kapsam_rc=0`)",
     (('pruvo_kapsam_rc=$?', 'pruvo_kapsam_rc=$?\npruvo_kapsam_rc=0', 1),), False,
     "IKINCI TUR deligi: regex hakim GOREMEDI, gercek `sh`te PUSH GECTI"),
    ("N2 kosula `&& [ 1 -eq 2 ]` eklendi",
     (('"$pruvo_kapsam_rc" -ne 0 ]', '"$pruvo_kapsam_rc" -ne 0 ] && [ 1 -eq 2 ]', 1),),
     False, "kosul SEMANTIK olarak olu — capa kisaldigi icin artik COKME degil IDDIA"),
    ("N3 blok `if false; then … fi` sarmalinda",
     (("pruvo_kapsam_kok=$(git rev-parse --show-toplevel 2>/dev/null)",
       "if false; then\npruvo_kapsam_kok=$(git rev-parse --show-toplevel 2>/dev/null)", 1),
      (_PP_BLOK_SON, "fi\n" + _PP_BLOK_SON, 1)), False,
     "IKINCI TUR deligi: blogun KOSULLU BAGLAMI — satir-ici desen bunu GORMEZ"),
    ("X4 blok `[ -z \"$GIT_EXEC_PATH\" ]` sarmalinda (ORTAM ekseni)",
     (("pruvo_kapsam_kok=$(git rev-parse --show-toplevel 2>/dev/null)",
       "if [ -z \"$GIT_EXEC_PATH\" ]; then\n"
       "pruvo_kapsam_kok=$(git rev-parse --show-toplevel 2>/dev/null)", 1),
      (_PP_BLOK_SON, "fi\n" + _PP_BLOK_SON, 1)), False,
     "UCUNCU TUR deligi: ciplak `sh` fiksturunde YESIL, GERCEK `git push`ta blok "
     "HIC kosmuyordu — ortam sadakati olmadan gorunmez"),
    ("KONTROL-A mesru alternatif kosul bicimi",
     (('"$pruvo_kapsam_rc" -ne 0', '"$pruvo_kapsam_rc" != 0', 1),), True,
     "YANLIS-POZITIF yuzeyi: bicim serbest, SEMANTIK sart"),
    ("KONTROL-B ilgisiz yorum satiri",
     (("# SESSIZ CALISIR:", "# SESSIZ CALISIR (kontrol mutanti):", 1),), True,
     "ilgisiz degisiklik hukmu DEGISTIRMEMELI"),
    ("KONTROL-C `${...}` bicimine yeniden yazim (SEMANTIK AYNI)",
     (("$pruvo_kapsam_rc", "${pruvo_kapsam_rc}", 2),), True,
     "mesru refactor YAYINI DURDURMAMALI — regex hakimde sahte-KIRMIZI yakiyordu"),
)


def kanca_kablo_adimi_kontrol():
    """🔴 UCUNCU KOLUN CAGRI SATIRI NOBETI (5. tur, F2) — UCUZ, `denetle` kolunda.

    OLCULEN DELIK: `--kanca-kablo` adimini deploy.yml'den SILMEK (B1) ya da
    `echo`'ya SARMAK (B3) hem pre-push hem `is-akisi-kapisi` kolunda YESIL
    geciyordu -> push da yayin da GECIYORDU; kirmizi yalniz bloklamayan
    `nobet.yml`de kaliyordu. Bu, 21 Tem meta-deliginin UCUNCU tekrari
    ([[nobetci-cagri-satiri-nobetsiz]]): iki kardes kol (`kendini_test_adimi_
    kontrol` · `bayraksiz_adim_kontrol`) kendi adimlarini `denetle` kolunda
    civiliyor, UCUNCU kol icin muadili YOKTU.

    NEDEN BU DESEN (ikinci mantik YAZILMADI): kardeslerle AYNI `_hedef_cagrilari()`
    tek kaynagi kullanilir -> `echo`/`--help` mensiyonlari ORTAK suzgecten elenir.
    NEDEN `kanca_kablo_serit_kontrol()` YETMEZ: o nobetci `main` kaydinda yasar
    (`--kanca-kablo` + `--kendini-test` kollari); adim silindiginde O KOL CI'da HIC
    KOSMAZ ve kendi kirmizisi kimseye ulasmaz.
    (ok, hata_satirlari) dondurur."""
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["KANCA-KABLO ADIMI OLCULEMEDI: deploy.yml bulunamadi: %s"
                       % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()
    anlamli, reddedilen = _hedef_cagrilari(gercek, HEDEF_BETIK)
    for argumanlar in anlamli:
        # None = jetonlanamayan cagri (OLCULEMEDI) -> kardeslerle AYNI fail-OPEN.
        if argumanlar is None or KANCA_KABLO_BAYRAGI in argumanlar:
            return True, []
    return False, [
        "KANCA-KABLO ADIMI YOK: deploy.yml'de `%s` bayragini ANLAMLI olarak ICRA "
        "EDEN adim BULUNAMADI (silinmis, `echo`'ya sarilmis ya da `--help`e "
        "cevrilmis olabilir). O adim silinince agir davranis ayagi CI'da HIC "
        "KOSMAZ ve N1/N3/X4 sinifi sabotaj push'u DA yayini DA gecer."
        % KANCA_KABLO_BAYRAGI + _reddedilen_ozeti(reddedilen)]


def kanca_kablo_serit_kontrol():
    """🔴 AGIR AYAK GERCEKTEN BLOKLAYICI SERITTE MI (beyan degil, DAVRANIS).

    OLCULEN HATA (4. tur): teslim "deploy.yml'de BLOKLAYICI" diye BEYAN etti; adim
    aslinda `nobet.yml`deydi (SERIT B, yayini BLOKLAMAZ) ve N1/N3/X4 sinifi push'u
    da deploy'u da geciyordu. Kanonik sinif:
    [[kapi-beyanin-dogrulugunu-degil-varligini-olcer]] — beyanin VARLIGI degil
    DOGRULUGU olculmeli.

    UC IDDIA (hepsi GERCEK deploy.yml uzerinden, YAML AYRISTIRICISIYLA):
      S1 ADIM VAR   — `%s` bayragini ANLAMLI olarak icra eden bir adim var.
      S2 JOB KIMLIGI — o adim HANGI job'da, ADIYLA soylenir (tani).
      S3 ZORLAMA    — o job `deploy: needs` zincirinde (dogrudan ya da dolayli).

    🔴 KAPSAM SINIRI (BEYAN OLCULENE ESITLENDI, 5. tur F1): buradaki "zorlama"
    YALNIZ `needs` TOPOLOJISIDIR. Adim duzeyinde `if: false`, adimda
    `continue-on-error: true` ve JOB duzeyinde `if: false` eksenleri BU NOBETCIDE
    OLCULMEZ (olculdu: ucunde de bu kol 0 doner). O eksen `tools/is-akisi-kapisi.py`
    dedir ve o kapi AYNI bloklayici `serit-a3` job'unda kosar (ucunde de rc=1
    olculdu). Beyanin dogrulugu, varligi degil, olculen seye esittir
    ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]]).
    """ % KANCA_KABLO_BAYRAGI
    hata = []
    try:
        with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
            metin = f.read()
    except OSError as e:
        return False, ["KANCA KABLO SERIDI OLCULEMEDI: deploy.yml okunamadi: %s" % e]
    belge, ayrist_hata = YAML_OKU.belge(metin)
    if belge is None:
        return False, ["KANCA KABLO SERIDI OLCULEMEDI (fail-closed): deploy.yml "
                       "GERCEK ayristirici ile cozulemedi (%s) -> 'adim bloklayici "
                       "job'da' hukmu TAHMIN EDILMEZ." % (ayrist_hata or "?")]
    joblar = (belge or {}).get("jobs") or {}
    tasiyan = []
    for job_adi, job in joblar.items():
        for adim in (job or {}).get("steps") or []:
            komut = (adim or {}).get("run")
            if not komut:
                continue
            for satir in _icra_komutlari(str(komut)):
                if not _onek_re(_PP_KAPI).match(satir):
                    continue
                if KANCA_KABLO_BAYRAGI not in satir:
                    continue
                if SUZGEC.cagri_sayilir(satir, _PP_KAPI):
                    tasiyan.append(job_adi)
                    break
    tasiyan = sorted(set(tasiyan))
    if not tasiyan:
        return False, ["S1 ADIM YOK: deploy.yml'de `%s` bayragini ANLAMLI olarak icra "
                       "eden adim BULUNAMADI -> agir davranis ayagi hicbir bloklayici "
                       "seritte kosmuyor." % KANCA_KABLO_BAYRAGI]
    # S3: `deploy` job'unun needs zinciri (gecisli kapanis).
    deploy_job = joblar.get("deploy") or {}
    gerekli = deploy_job.get("needs") or []
    if isinstance(gerekli, str):
        gerekli = [gerekli]
    zincir, kuyruk = set(), list(gerekli)
    while kuyruk:
        j = kuyruk.pop()
        if j in zincir:
            continue
        zincir.add(j)
        alt = (joblar.get(j) or {}).get("needs") or []
        kuyruk.extend([alt] if isinstance(alt, str) else alt)
    if not zincir:
        hata.append("S3 OLCULEMEDI: `deploy` job'unun `needs` listesi BOS/YOK -> "
                    "zorlama zinciri cozulemedi (fail-closed).")
    bloklayan = [j for j in tasiyan if j in zincir]
    if not bloklayan:
        hata.append(
            "S3 ZORLAMA YOK: `%s` adimi %s job(lar)inda ama `deploy: needs` zinciri "
            "%s -> o job KIRMIZI yansa bile YAYIN GECER. Adim BLOKLAYICI bir job'a "
            "(or. `serit-a3`) tasinmali; aksi halde N1/N3/X4 sinifi 'kapi' degil "
            "yalniz 'alarm'dir." % (KANCA_KABLO_BAYRAGI, tasiyan, sorted(zincir)))
    return (not hata), hata


def pre_push_capa_kontrol():
    """🟢 UCUZ KOL — pre-push'ta (yerel push oncesi) kosan STATIK on-uyari.

    🔴 MALIYET HUKMU (9 Agu 2026, olculdu): davranis ayagi 45 GERCEK `git push`
    yapiyor ve TEK BASINA 2,40 sn suruyor; bayraksiz kol medyan 5,84 · P95 6,04 sn
    olup 5 sn esigini ASTI. Mimar hukmu geregi AGIR ayak `--kendini-test` koluna
    (deploy.yml'de BLOKLAYICI) tasindi; burada yalniz UCUZ statik capalar kalir.
    🔴 BU KOL TEK BASINA HAKIM DEGILDIR ve oyle olmadigi ACIKCA yazilidir: statik
    metin N1 (rc yeniden atama), N3 (`if false`) ve X4 (ortam sarmali) sinifini
    GOREMEZ — onlarin hukmu `pre_push_kablo_kontrol()`'un kabuk ayagindadir.
    Buradaki deger, cagri/`exit`/kosul KAYBINI push anindan ONCE bagirmaktir."""
    try:
        with open(PRE_PUSH_YOLU, encoding="utf-8") as f:
            govde = f.read()
    except OSError as e:
        return False, ["PRE-PUSH CAPASI OLCULEMEDI: izlenen kanca kaynagi okunamadi "
                       "(%s): %s" % (PRE_PUSH_YOLU, e)]
    hata = ["PRE-PUSH CAPASI: " + h for h in _pre_push_tanisi(govde)]
    try:
        _pp_blok(govde)
    except RuntimeError as e:
        hata.append("PRE-PUSH CAPASI: %s" % e)
    return (not hata), hata


def pre_push_kablo_kontrol():
    """pre-push kapsam blogunun DAVRANISINI olcer (varligini/bicimini degil).

    🔴 HUKMU KABUK VERIR: her govde sentetik depoda `sh` ile FIILEN kosulur
    (`PRE_PUSH_DAVRANIS_VAKALARI`). `_pre_push_tanisi()` yalniz TANI metni uretir.
    GERCEK govde okunur; mutantlar BELLEKTE uygulanir, gecici dizine yazilir;
    IZLENEN kanca kaynagina DOKUNULMAZ. Capa/isaretci bulunamazsa OLCULEMEDI."""
    hata = []
    try:
        with open(PRE_PUSH_YOLU, encoding="utf-8") as f:
            govde = f.read()
    except OSError as e:
        return False, ["PRE-PUSH KABLOSU OLCULEMEDI: izlenen kanca kaynagi "
                       "okunamadi (%s): %s" % (PRE_PUSH_YOLU, e)]
    gecici = tempfile.mkdtemp(prefix="pruvo-pp-davranis-")
    try:
        kosucu = _PpKosucu(gecici)
        for etiket, degisiklikler, beklenen_ok, neden in PRE_PUSH_MUTANTLARI:
            mutant, capa_hatasi = govde, None
            for capa, ikame, adet in degisiklikler:
                gecen = mutant.count(capa)
                if gecen != adet:
                    capa_hatasi = ("capa %r govdede %d kez gecti (beklenen %d)"
                                   % (capa[:50], gecen, adet))
                    break
                mutant = mutant.replace(capa, ikame)
            if capa_hatasi:
                hata.append("PRE-PUSH MUTANTI OLCULEMEDI (%s): %s -> mutasyon "
                            "UYGULANMADI, hukum ANLAMSIZ olurdu (cokme kirmiziyla "
                            "KARISTIRILMAZ)." % (etiket, capa_hatasi))
                continue
            try:
                blok = _pp_blok(mutant)
            except RuntimeError as e:
                hata.append("PRE-PUSH MUTANTI OLCULEMEDI (%s): %s" % (etiket, e))
                continue
            dusen = []
            for v_etiket, kapi_rc, arac_var, durmali, v_neden in \
                    PRE_PUSH_DAVRANIS_VAKALARI:
                try:
                    kanca_rc, _cikti = kosucu.kos(blok, kapi_rc, arac_var)
                except Exception as e:  # noqa: BLE001 — cokme KIRMIZI SAYILMAZ
                    hata.append("PRE-PUSH DAVRANISI OLCULEMEDI (%s/%s): %s: %s"
                                % (etiket, v_etiket, type(e).__name__, e))
                    dusen = None
                    break
                durdu = kanca_rc != 0
                if durdu != durmali:
                    dusen.append("%s: kanca rc=%d (%s) · %s"
                                 % (v_etiket, kanca_rc,
                                    "DURDU" if durdu else "PUSH GECTI", v_neden))
            if dusen is None:
                continue
            ok = not dusen
            if ok != beklenen_ok:
                tani = _pre_push_tanisi(mutant)
                hata.append(
                    "PRE-PUSH FIKSTURU DUSTU (%s): beklenen=%s gelen=%s · %s · "
                    "davranis=%r · (ikincil TANI: %r)"
                    % (etiket, "YESIL" if beklenen_ok else "KIRMIZI",
                       "YESIL" if ok else "KIRMIZI", neden, dusen,
                       [t[:70] for t in tani]))
    except Exception as e:  # noqa: BLE001 — nobetci kapiyi patlatmaz, konusur
        hata.append("PRE-PUSH KABLOSU OLCULEMEDI: %s: %s" % (type(e).__name__, e))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    oldurucu = sum(1 for _e, _d, b, _n in PRE_PUSH_MUTANTLARI if not b)
    kontrol = sum(1 for _e, _d, b, _n in PRE_PUSH_MUTANTLARI if b)
    if oldurucu < 12 or kontrol < 4:
        hata.append("PRE-PUSH MUTANT TABLOSU KUCULDU (oldurucu %d, kontrol %d; taban "
                    "12/4) — tabloyu kucultmek nobetciyi SESSIZCE oldurur "
                    "([[fikstur-degeri-mutasyon-koru]])." % (oldurucu, kontrol))
    return (not hata), hata


def _icra_govdesi(ham_satir):
    """TEK KAYNAK — bir deploy.yml satirini FIILEN kosan komut govdesine indirger.

    Yorum satiri (strip -> '#'), bos satir ve ADIM ADI ('- name:' / 'name:') ELENIR;
    'run:' oneki soyulur. Icra degilse None. _icra_komutlari(), _icra_satir_indeksleri()
    ve mutant ureticileri HEP bunu kullanir -> repoda iki farkli 'satir icra mi' mantigi
    TUTULMAZ. Kaba ve fail-closed: YAML ayristiricisi taklit ETMEZ (bkz.
    mimar-kapi-parser-taklidi).

    'name:' ELEMESI NEDEN BURADA (28 Tem, curutucu turu): bir step ADI HICBIR ZAMAN icra
    degildir — T7'nin ('mensiyon kosuluyor sayilmasin') ta kendisidir. Eskiden yalniz
    yorumlar eleniyordu; 'run:' satiri silinip komut metni step ADINA tasinirsa
    (`- name: python3 tools/x-test.py`) satir icra govdesi olarak listeye giriyordu.
    Bu, paylasilan capayi (kosulan() dahil) DOGRU yonde sertlestirir; olculdu: kosulan
    sayisi ve bulgu1/muaf nobetcileri DEGISMEDI (rapor TUR 3)."""
    s = ham_satir.strip()
    if not s or s.startswith("#"):
        return None  # bos satir ya da YAML yorumu -> icra degil
    if s.startswith("- name:") or s.startswith("name:"):
        return None  # step ADI -> icra degil (mensiyon, T7 sinifi)
    # 🔴 DIZI TIRESI `- run:` (ADSIZ ADIM — GitHub Actions'in tamamen MESRU yazimi;
    # onizleme-imaj.yml'de zaten kullaniliyor). Eskiden yalniz CIPLAK `run:` soyuluyordu
    # -> `- run: python3 tools/x.py` govdesi `- run: python3 ...` kaliyor, `^python3 <yol>`
    # capasi TUTMUYOR ve cagri kapiya TUMUYLE GORUNMEZ oluyordu. Olculdu (30 Tem curutme
    # turu): bu bicime cevrilmis TEK bir mesru adim bloklayici kapiyi KIRMIZI yakiyordu
    # (190 fuzz girdisinde taban regresyonu) — sahte-KIRMIZI. Ters yonu de var: adsiz
    # adimdaki cagri "yok" gorunduğü icin bir SILME mutasyonu fark edilmeyebilirdi.
    if s.startswith("- "):
        kalan = s[2:].lstrip()
        if kalan.startswith("run:"):
            s = kalan
    if s.startswith("run:"):
        s = s[4:].strip()  # inline 'run: <komut>' ya da blok basi 'run: |'
    return s or None


# ---- YAML `run:` DEGERLERI — PARSER-FIRST / TAKLIT-FALLBACK ----------------
# `run: >-` blogunda YAML, AYNI GIRINTIDEKI ardisik satirlari TEK BOSLUKLA birlestirir.
# Metin duzleminde satir satir gezen bir suzgec bunu iki YARIM satir gorur -> bayrak ayri
# satirda kalir, arguman sayilmaz ve bayrak sorgulayan nobetciler SAHTE-KIRMIZI yanar.
# Bu kapi continue-on-error'SUZ kosar: tek sahte-kirmizi TUM ekibin yayinini durdurur.
#
# 🔴 30 TEM — MIMAR HUKMU: PARSER-FIRST / TAKLIT-FALLBACK ([[mimar-kapi-parser-taklidi]])
# Onceki tur bu donusumu METIN duzleminde TAKLIT etmisti. Bagimsiz curutme turu bunu
# differential fuzzing ile olctu (1150 girdi, 1037'si iki gercek ayristiriciyla da
# kiyaslanabilir):
#     BAYT sapmasi 350 · HUKUM sapmasi 303 (274 salt sahte-KIRMIZI, 29 sahte-YESIL
#     bilesenli) · psych <-> PyYAML sapmasi 0 · tabana gore 190 REGRESYON.
# Yani taklit hem yayini gereksiz durduruyor hem de EN AZ IKI sinifta (TAB girintili
# satir, anchor'li blok) kapiyi SESSIZCE gevsetiyordu. "PyYAML her ortamda yok"
# gerekcesi de OLCULDU ve CURUDU: CI'da PyYAML kurulu, bu Mac'te ruby/psych var.
# BUGUNKU MIMARI:
#   1. GERCEK AYRISTIRICI (PyYAML -> ruby/psych) VARSA **TEK KARAR MERCII ODUR**;
#      taklit devre disi kalir. `run` degerinin katlama/literal/tirnak/anchor semantigi
#      ayristiricidan gelir, HAM SATIR ARALIGI da ondan gelir (mutant ureticileri icin).
#   2. HICBIR ayristirici yoksa (ya da dosya ayristirilamiyorsa) taklit devreye girer.
#      Taklit ASLA bir cagriyi yok sayacak yonde "akilli" davranmaz: cozemedigi yazimda
#      (alias, `run:` degeri sonraki satirda, ayristirma hatasi) satiri HAM birakir ->
#      cagri gorunur kalir; yalniz EMIN oldugu olumsuzlukta (literal blok, paragraf
#      ayrimi, more-indented satir) satirlari ayri tutar.
#   3. Hangi kolun karar verdigi CIKTIDA gorunur: `ayristirici_kolu()` -> main() ve
#      `_teshis_ozeti()` bunu basar.
#   4. Taklit ile ayristirici arasindaki sapma KUSURDUR: KATLAMA_FIKSTURLERI iki kolu
#      AYNI beklentiye kilitler (fikstur kumesinde sapma = KIRMIZI).
#
# 🟡 BEYAN EDILEN SINIRLAR (yalniz FALLBACK kolunda — ayristirici varken GECERSIZ):
#   (a) `env:`ten gelen yol (`run: python3 "$KAPI"`) STATIK cozulemez; hicbir YAML
#       donusumu kabuk degisken genislemesini yapmaz. Ayristirici kolunda da boyledir.
#       Kapi `sayilamayan_python3()` T8 uyarisini basar.
#   (b) Fallback kolunda ALIAS (`run: *capa`) cozulmez -> satir HAM gecer; o adimdaki
#       cagri gorunmez (sahte-KIRMIZI yonu). Anchor TANIMININ kendisi (`run: &capa >-`)
#       kapsanir, yani cagri en az bir yerde gorunur.
#   (c) Fallback kolunda TIRNAKLI cok satirli skalarda tirnaklar metinde KALIR; hukum
#       degismez (SUZGEC `shlex` ile jetonlar), yalniz tani metni tirnakli gorunur.
_RUN_ANAHTAR_RE = re.compile(r"^(?P<girinti>[ ]*)(?P<tire>-[ ]+)?run:(?P<kalan>[ \t].*|)$")

# `run:` degerinin basindaki YAML dugum ozellikleri: anchor (`&ad`) ve/veya etiket (`!tip`).
# 🔴 ANCHOR NEDEN BURADA: eski desen `run:` ile `>` arasinda anchor beklemiyordu ->
# `run: &capa >-` blogu HIC taninmiyor, govde satirlari HAM gecip bayraksiz cagri gibi
# gorunuyordu = SAHTE-YESIL (curutme turu X04).
_OZELLIK_ONEK_RE = re.compile(r"^(?:(?:&[^\s]+|![^\s]*)[ \t]+)+")

_BLOK_BASI_RE = re.compile(
    r"^(?P<girinti>[ ]*)(?P<tire>-[ ]+)?run:[ \t]*"
    r"(?:(?:&[^\s]+|![^\s]*)[ \t]+)*"
    r"(?P<stil>[|>])(?P<gosterge>[0-9+\-]{0,2})[ \t]*(?:#.*)?$")


def _girinti_olcu(satir):
    """(bosluk_girintisi, girintiden_HEMEN_SONRA_TAB_VAR_MI).

    🔴 TAB NEDEN AYRI OLCULUYOR: YAML'da TAB GIRINTI DEGILDIR — icerigin parcasidir.
    `          \\t--bayrak` satirini gercek ayristirici more-indented sayar ve satir
    sonunu KORUR; yalniz bosluk sayan taklit onu ayni girintide sanip KATLIYORDU.
    Olculdu (curutme turu, 27 kayit): bu tam bir SAHTE-YESIL idi — kapi "oz-nobetci
    adimi bayrakla kosuyor" derken CI'da bayrak komuta GITMIYORDU."""
    g = len(satir) - len(satir.lstrip(" "))
    return g, satir[g:g + 1] == "\t"


def _deger_satirlari(deger):
    """Bir `run` skalar degerini MANTIKSAL satirlara ayir (sondaki bos satirlar duser).

    Chomping (`-`/`+`/yok) yalnizca SONDAKI satir sonlarini belirler -> sondaki bos
    dizeler dusurulunce `>`, `>-`, `>+` AYNI listeyi verir (fiksturlerle kilitli)."""
    satirlar = deger.split("\n")
    while satirlar and not satirlar[-1].strip():
        satirlar.pop()
    return satirlar or [""]


def _ayristirici_run_bloklari(metin):
    """(bloklar, hata) — GERCEK ayristirici kolu.
    bloklar = [(anahtar_satir, ilk_ham, son_ham, [mantiksal_satir, ...]), ...]."""
    dugumler, hata = YAML_OKU.run_dugumleri(metin)
    if hata:
        return None, hata
    return [(anahtar, bas, son, _deger_satirlari(deger))
            for anahtar, bas, son, deger in dugumler], None


def _taklit_blok_skalar(satirlar, i, anahtar_girinti, m):
    """(son_ham_satir, [mantiksal_satir, ...]) — blok gostergeli (`|`/`>`) skalar, TAKLIT."""
    n = len(satirlar)
    j = i + 1
    govde = []  # (bosluk_girintisi | None, tab_var, ham_indeks)
    while j < n:
        s = satirlar[j]
        if not s.strip():
            govde.append((None, False, j))
            j += 1
            continue
        g, tab = _girinti_olcu(s)
        # ANAHTAR girintisi (tire dahil) esik: `- run: >-` yaziminda kardes `env:`/`if:`
        # satirlari `girinti`den fazla ama ANAHTAR girintisine ESIT olur; eski esik
        # (`len(girinti)`) onlari bloga YUTUYORDU (curutme turu X21).
        if g <= anahtar_girinti and not tab:
            break
        govde.append((g, tab, j))
        j += 1
    # SONDAKI BOS satirlar icerik uretmez -> bloga dahil ETME, aynen bassinlar
    while govde and govde[-1][0] is None:
        govde.pop()
        j -= 1
    dolu = [x for x in govde if x[0] is not None]
    if not dolu:
        return i, [""]
    rakam = "".join(c for c in m.group("gosterge") if c.isdigit())
    blok_girinti = (anahtar_girinti + int(rakam)) if rakam else dolu[0][0]
    literal = m.group("stil") == "|"
    deger = ""
    ilk = True
    onceki_ayri = False
    bos_sayaci = 0
    for g, tab, ham_i in govde:
        if g is None:
            bos_sayaci += 1
            continue
        ham = satirlar[ham_i]
        icerik = ham[blok_girinti:] if len(ham) >= blok_girinti else ham.lstrip(" ")
        # KATLANIR MI: literal blokta ASLA; katlanan blokta yalniz TAM blok girintisinde
        # ve girintide TAB YOKKEN (YAML more-indented kurali).
        ayri = literal or tab or g != blok_girinti
        parca = icerik if ayri else icerik.strip()
        if ilk:
            deger = parca
            ilk = False
        elif literal:
            deger += "\n" * (bos_sayaci + 1) + parca
        elif bos_sayaci:
            deger += "\n" * bos_sayaci + parca
        elif ayri or onceki_ayri:
            deger += "\n" + parca
        else:
            deger += " " + parca
        onceki_ayri = ayri
        bos_sayaci = 0
    return j - 1, _deger_satirlari(deger)


def _taklit_duz_skalar(satirlar, i, anahtar_girinti, kalan):
    """(son_ham_satir, [mantiksal_satir, ...]) — blok gostergesiz (duz/tirnakli) skalar.

    COK SATIRLI DUZ SKALAR (`run: python3 x.py` + sonraki satirda daha girintili
    `--bayrak`) YAML'da da TEK BOSLUKLA katlanir. Eski taklit bunu HIC kapsamiyordu ->
    kapi ilk satiri BAYRAKSIZ cagri sanip YESIL kaliyordu (curutme turu X08:
    bayraksiz nobetcide SAHTE-YESIL). None dondurulurse blok URETILMEZ (satir HAM gecer)."""
    kalan = kalan.strip()
    if not kalan:
        return i, None  # `run:` degeri sonraki satirda / bos -> HAM birak (fail-closed)
    kalan = _OZELLIK_ONEK_RE.sub("", kalan, count=1)
    if kalan.startswith("*"):
        return i, None  # ALIAS -> taklit cozemez, HAM birak (cagri yok SAYILMAZ)
    tirnakli = kalan[:1] in ('"', "'")
    if not tirnakli:
        p = kalan.find(" #")
        if p >= 0:
            kalan = kalan[:p].rstrip()  # YAML: duz skalarda ` #` YORUM baslatir
        if kalan.startswith("#"):
            kalan = ""
    n = len(satirlar)
    j = i + 1
    son = i
    deger = kalan
    bos_sayaci = 0
    while j < n:
        s = satirlar[j]
        if not s.strip():
            bos_sayaci += 1
            j += 1
            continue
        g, _tab = _girinti_olcu(s)
        if g <= anahtar_girinti:
            break
        deger += ("\n" * bos_sayaci if bos_sayaci else " ") + s.strip()
        bos_sayaci = 0
        son = j
        j += 1
    return son, _deger_satirlari(deger)


def _taklit_run_bloklari(metin):
    """TAKLIT KOL (FALLBACK) — [(anahtar_satir, ilk_ham, son_ham, [mantiksal, ...])]."""
    satirlar = metin.splitlines()
    n = len(satirlar)
    bloklar = []
    i = 0
    while i < n:
        m = _RUN_ANAHTAR_RE.match(satirlar[i])
        if not m:
            i += 1
            continue
        anahtar_girinti = len(m.group("girinti")) + len(m.group("tire") or "")
        blok = _BLOK_BASI_RE.match(satirlar[i])
        if blok:
            son, dsat = _taklit_blok_skalar(satirlar, i, anahtar_girinti, blok)
        else:
            son, dsat = _taklit_duz_skalar(satirlar, i, anahtar_girinti, m.group("kalan"))
        if dsat is None:
            i += 1
            continue
        bloklar.append((i, i, son, dsat))
        i = son + 1
    return bloklar


def _blok_provenans(satirlar, bas, son, dsat):
    """Her MANTIKSAL satir icin, onu ureten HAM satir indeksleri.

    🔴 NEDEN HAM INDEKS: mutant ureticileri (_silme_mutanti / _yorum_mutanti) HAM
    satirlar uzerinde calisir. Katlanan blokta bir cagri UC ham satira bolunebilir
    (`python3` / `tools/x.py` / `--bayrak`); hicbir HAM satir tek basina `^python3 <yol>`
    capasina uymaz -> mutasyon cagriyi HIC dokunmadan birakir, cagri hayatta kalir ve
    bulgu1_mutasyon_kontrol "BULGU 1 GERI GELDI" diye YANLIS SINIFLA sahte-KIRMIZI yanar.
    Eslesme kurulamazsa (tirnakli skalar, kacis dizileri) FAIL-CLOSED: blogun TUM govde
    satirlari dondurulur — mutasyon eksik kalmaktansa genis olsun."""
    ham = [k for k in range(bas + 1, son + 1) if satirlar[k].strip()]
    if not ham:
        return [[] for _ in dsat]
    tum = list(range(bas + 1, son + 1))
    sonuc = []
    p = 0
    for d in dsat:
        hedef = d.strip()
        if not hedef:
            sonuc.append([])
            continue
        alinan = []
        birikim = ""
        while p < len(ham):
            parca = satirlar[ham[p]].strip()
            alinan.append(ham[p])
            p += 1
            birikim = (birikim + " " + parca) if birikim else parca
            if birikim == hedef:
                break
        if birikim != hedef:
            return [list(tum) for _ in dsat]
        sonuc.append(alinan)
    if p != len(ham):
        return [list(tum) for _ in dsat]
    return sonuc


def _bloklardan_mantiksal(satirlar, bloklar):
    """[(mantiksal_satir, [ham_satir_indeksi, ...]), ...] — iki kolun ORTAK cikti bicimi.

    `run:` blogunun ham satirlari TUKETILIR ve yerine degerin mantiksal satirlari gecer
    (`run:` oneki YOK: _icra_govdesi() dogrudan komut govdesini gorur). Blok DISI satirlar
    aynen gecer. ILK mantiksal satirin provenansina `run:` ANAHTAR satiri da eklenir:
    inline yazimda cagri O satirda YASAR, mutasyon onu hedeflemek ZORUNDA."""
    kapali = {}
    for anahtar, bas, son, dsat in bloklar:
        kapali[bas] = (max(son, bas), dsat)
    cikti = []
    i = 0
    n = len(satirlar)
    while i < n:
        if i in kapali:
            son, dsat = kapali[i]
            son = min(son, n - 1)
            prov = _blok_provenans(satirlar, i, son, dsat)
            for k, d in enumerate(dsat):
                hamlar = ([i] + list(prov[k])) if k == 0 else list(prov[k])
                cikti.append((d, hamlar or [i]))
            i = son + 1
            continue
        cikti.append((satirlar[i], [i]))
        i += 1
    return cikti


_KOL_ADI = "?"
_MANTIKSAL_ONBELLEK = {}


def ayristirici_kolu():
    """Son hukmu HANGI kol verdi: "pyyaml 6.0.3" | "psych 3.1.0" | "taklit-fallback(...)".
    main() ve _teshis_ozeti() bunu BASAR (mimar hukmu madde 3: kol gorunur olsun)."""
    return _KOL_ADI


def _mantiksal_yaml_satirlari(metin):
    """`run:` degerlerini MANTIKSAL satirlara indir — PARSER-FIRST, taklit FALLBACK.

    Girdi: is-akisi metni. Cikti: [(mantiksal_satir, [ham_satir_indeksi, ...]), ...].
    Gercek ayristirici varsa ve metin ayristirilabiliyorsa TEK KARAR MERCII ODUR;
    aksi halde taklit kolu (fail-closed: cozemedigi yazimi HAM birakir) devreye girer."""
    global _KOL_ADI
    if metin in _MANTIKSAL_ONBELLEK:
        _KOL_ADI, sonuc = _MANTIKSAL_ONBELLEK[metin]
        return sonuc
    satirlar = metin.splitlines()
    bloklar, hata = _ayristirici_run_bloklari(metin)
    if bloklar is not None:
        kol = YAML_OKU.ayristirici_adi() or "?"
    else:
        kol = "taklit-fallback (%s)" % (hata or "?")
        bloklar = _taklit_run_bloklari(metin)
    sonuc = _bloklardan_mantiksal(satirlar, bloklar)
    if len(_MANTIKSAL_ONBELLEK) > 512:
        _MANTIKSAL_ONBELLEK.clear()
    _MANTIKSAL_ONBELLEK[metin] = (kol, sonuc)
    _KOL_ADI = kol
    return sonuc


def _taklit_mantiksal_satirlari(metin):
    """YALNIZ TAKLIT KOLU (fikstur nobetcisi icin) — kol secimini ATLAR."""
    return _bloklardan_mantiksal(metin.splitlines(), _taklit_run_bloklari(metin))


def _ayristirici_mantiksal_satirlari(metin):
    """YALNIZ GERCEK AYRISTIRICI KOLU (fikstur nobetcisi icin); yoksa/hata varsa None."""
    bloklar, _hata = _ayristirici_run_bloklari(metin)
    if bloklar is None:
        return None
    return _bloklardan_mantiksal(metin.splitlines(), bloklar)


def _katlanan_bloklari_birlestir(metin):
    """_mantiksal_yaml_satirlari()'nin METIN kolu — `run:` degerleri cozulmus
    deploy.yml metnini dondurur (tuketiciler: _icra_komutlari, _hedef_cagrilari)."""
    return "\n".join(t for t, _ in _mantiksal_yaml_satirlari(metin))


def _icra_komutlari(deploy_metin):
    """deploy.yml'de FIILEN kosan komut govdelerini (satir satir) dondur.
    Bir 'python3 <yol>' mensiyonu YORUM icinde ya da echo-string icinde geciyorsa
    bu listede komutun BASINDA yer almaz -> kosulan() onu 'kosuluyor' saymaz.

    IKI BIRLESTIRME KATMANI (sirasi ONEMLI — once YAML, sonra KABUK):
      1. YAML KATLAMASI (_katlanan_bloklari_birlestir): `run: >-` blogunun ayni
         girintideki satirlari TEK komut olur. LITERAL `run: |` DOKUNULMAZ.
      2. KABUK SATIR DEVAMI (SUZGEC.birlestir_devam): `\\` ile biten satir sonrakiyle
         birlesir. `run: |` blogunda mesru bir cagri `python3 tools/x-test.py \\` +
         sonraki satirda `--bayrak` biciminde yazilabilir.
    Ikisi de yapilmazsa jetonlayici YARIM satiri gorur, bayrak listesi eksik cikar ve
    bayrak sorgulayan nobetciler SAHTE-KIRMIZI yanar (olculdu: `>-` icin 3 denetci).
    ⚠️ _icra_satir_indeksleri() BILINCLI olarak HAM satirlarda kalir (mutant ureticileri
    SATIR SILER/YORUMA CEVIRIR; birlestirilmis metinde satir indeksi kaymis olur)."""
    komutlar = []
    for ham in SUZGEC.birlestir_devam(_katlanan_bloklari_birlestir(deploy_metin)):
        g = _icra_govdesi(ham)
        if g:
            komutlar.append(g)
    return komutlar


# Kesif predikati .py YANINDA .js/.mjs/.cjs dosyalarini da buluyor (DIR_PAT); bunlar
# python3 ile DEGIL node ile kosulur. Yorumlayici DOSYA UZANTISINDAN turetilir.
# ⚠️ TABLO BURADAN TASINDI -> tools/icra-suzgeci.py (UZANTI_YORUMLAYICI). Burada KOPYASI
# BIRAKILMADI; iki yerde tutulsa biri .mjs eklerken digeri eklemez ve kapi sessizce
# yarim korur ([[ayna-kapi-kesif-ekseni]]).
def _yorumlayici(yol):
    """<yol> hangi yorumlayiciyla kosulur? (SUZGEC'e delege — tek kaynak)"""
    return SUZGEC.yorumlayici_adi(yol)


def _onek_re(yol):
    """'bu komut govdesi <yol>'u kosuyor' KABA ADAY capasi — SUZGEC'e delege edilir.

    Komut govdesi '<yorumlayici> <yol>' ile BASLAMALI (yorumlayici uzantidan: .py ->
    python3, .js/.mjs/.cjs -> node); negatif ileri-bakis (?![\\w./-]) uzun bir baska yolun
    on-eki olarak yanlis eslesmeyi engeller (ve '<yol> --bayrak' biciminde BAYRAKLI cagriyi
    DOGRU sekilde ESLESTIRIR — bkz. bulgu1 docstring'i).

    NODE EKSENI (28 Tem): eski capa SABIT 'python3' idi -> deploy.yml'e node ile kosulan bir
    kabul testi eklense bile kapi onu 'kosulmuyor' sayardi; tek cikis yolu GERCEKTE KOSAN bir
    testi 'muaf' diye izin listesine yazmakti (yalan kayit) ya da testi hic baglamamakti
    (cagrisiz nobetci). Olculdu: 'run: node shop/test/konfigur-fail-closed.mjs' adimi
    eklendigi halde kapi KAPSAMSIZ diyordu.

    🔴 30 TEM (delik 1): bu capa TEK BASINA YETMEZ. `python3 tools/ci-kapsam-test.py --help`
    capaya UYAR (yolun ardindan bosluk var) ama argparse kullanim metnini basip exit 0
    verir — hicbir iddia olculmez ve kapi "kosuluyor" der. O yuzden capa artik yalniz ADAY
    bulur; hukmu SUZGEC.anlamli_cagri() verir (bkz. kosulan())."""
    return SUZGEC.onek_re(yol)


def _icra_satir_indeksleri(deploy_metin, yol):
    """<yol>'u FIILEN kosan satirlarin (0-tabanli) indekslerini dondur.

    kosulan() ile AYNI semantik (_icra_govdesi + _onek_re) — mutant ureticileri
    bunu kullanir, boylece 'kapinin saydigi satir' ile 'mutasyonun sildigi satir'
    ayrisamaz. Ayni yol BIRDEN COK adimda kosuluyorsa HEPSI dondurulur.

    KATLANAN BLOK (TUR 7): hukum MANTIKSAL satirda verilir, dondurulen indeksler HAM
    satirlardir — bir cagri katlanan blokta birden cok ham satira bolunmusse HEPSI
    dondurulur (_mantiksal_yaml_satirlari provenansi). Boylece silme/yorum mutasyonu
    cagriyi GERCEKTEN oldurur; eskiden mutasyon cagriyi hic dokunmadan birakip
    "BULGU 1 GERI GELDI" diye yanlis sinifla sahte-KIRMIZI yakiyordu.
    ⚠️ KABUK `\\` satir devami BILINCLI olarak BIRLESTIRILMEZ (bugunku davranis): orada
    ilk ham satir zaten capaya uyar ve tek basina silinmesi cagriyi oldurur."""
    onek = _onek_re(yol)
    idx = set()
    for metin, hamlar in _mantiksal_yaml_satirlari(deploy_metin):
        g = _icra_govdesi(metin)
        if g and onek.match(g):
            idx.update(hamlar)
    return sorted(idx)


def _silme_mutanti(deploy_metin, yol):
    """(mutant_metin, silinen_satir_sayisi) — <yol>'u kosan TUM icra satirlari silinir."""
    satirlar = deploy_metin.splitlines(keepends=True)
    idx = set(_icra_satir_indeksleri(deploy_metin, yol))
    kalan = [s for i, s in enumerate(satirlar) if i not in idx]
    return "".join(kalan), len(idx)


def _yorum_mutanti(deploy_metin, yol):
    """(mutant_metin, cevrilen_satir_sayisi) — <yol>'u kosan TUM icra satirlari
    '<girinti># python3 <yol> ...' biciminde YORUMA cevrilir (girinti + satir sonu korunur).
    T7 kanaryasi: python3-onekli bir yorum 'kosuluyor' SAYILMAMALIDIR."""
    satirlar = deploy_metin.splitlines(keepends=True)
    idx = set(_icra_satir_indeksleri(deploy_metin, yol))
    yeni = []
    for i, ham in enumerate(satirlar):
        if i not in idx:
            yeni.append(ham)
            continue
        govde = _icra_govdesi(ham)
        girinti = ham[:len(ham) - len(ham.lstrip())]
        son = "\n" if ham.endswith("\n") else ""
        yeni.append("%s# %s%s" % (girinti, govde, son))
    return "".join(yeni), len(idx)


def kosulan(deploy_metin, kesif):
    """deploy.yml'de FIILEN ICRA edilen (kosulan) kesif dosyalarini dondur.

    BULGU 1 + T7 (curutucu/olcum kanitladi): eski regex TUM metni tariyordu ->
    bir YORUM / step-name / echo-string'de gecen ad da 'kosuluyor' sayiliyordu;
    biri 'run: python3 tools/x-test.py' satirini silip yerine '# python3
    tools/x-test.py' yorumu birakinca kapi SAHTE-YESIL kaliyordu (olu nobetci
    CI'dan success gecerdi). 072c0294 eslesmeyi 'python3 <yol>' on-ekine daraltti
    ama YORUM SATIRLARINI hala eliyordu degil -> python3 onekli bir yorum yine
    eslesiyordu. FIX: eslesmeyi GERCEK KOMUT GOVDESINE ve komutun BASINA capala
    (_icra_komutlari yorumlari eler, 'run:' onekini soyar). Negatif ileri-bakis
    (?![\\w./-]): uzun bir baska yolun on-eki olarak yanlis eslesmesin.
    CAPA TEK KAYNAKTAN: _onek_re() — mutant ureticileri de ayni fonksiyonu kullanir.

    🔴 IKINCI KATMAN (30 Tem, DELIK 1): capaya uyan her satir "kosuluyor" DEMEK DEGILDIR.
    Olculdu: `run: python3 tools/ci-kapsam-test.py --help` capadan geciyor, CI'da yesil
    kosuyor ve HICBIR IDDIA olculmuyordu; dort denetci de rc=0 verdi. Artik aday satirlar
    SUZGEC.cagri_sayilir()'dan gecirilir:
      * ICRA_DISI_BAYRAK (`--help`/`-h`/`--version`/`-V`/`--usage`) -> SAYILMAZ
      * MENSIYON komutu (`echo`/`grep`/...) -> SAYILMAZ
      * jetonlanamayan satir -> SAYILIR (fail-OPEN, bilincli: bu kapi
        continue-on-error'SUZ kosar, tek sahte-kirmizi TUM ekibin yayinini durdurur
        [[kapi-kapsam-eksen-secimi]] -> belirsizlikte BUGUNKU davranis korunur)"""
    kos = set()
    komutlar = _icra_komutlari(deploy_metin)
    for yol in kesif:
        onek = _onek_re(yol)
        for k in komutlar:
            if not onek.match(k):
                continue
            if SUZGEC.cagri_sayilir(k, yol):
                kos.add(yol)
                break
    return kos


# ---- BOLUM A: COKLU IS AKISI ENVANTERI + TETIK SINIFI ----------------------
def is_akisi_yollari():
    """IZLENEN is akisi dosyalarinin repo-goreli yollari (git ls-files).

    `os.walk` DEGIL — kesfet() ile AYNI disiplin: gitignore'lu/uretilmis bir .yml
    yerelde gorunup CI checkout'unda gorunmez ve kapi makineye gore FARKLI hukum
    verirdi ([[ayna-kapi-kesif-ekseni]])."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True,
                       env=GIT_ORTAMI.git_ortami())
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    return sorted(y for y in r.stdout.splitlines() if IS_AKISI_PAT.match(y))


def tetik_sinifi(metin):
    """(sinif, tetikler, hata) — is akisinin tetik SINIFI.

    OTOMATIK  : tetik kumesi ELLE_TETIKLER DISINDA en az bir eleman iceriyor
                (push / pull_request / schedule / release / ...)
    ELLE      : yalniz workflow_dispatch / repository_dispatch
    BELIRSIZ  : tetik COZULEMEDI (ayristirma hatasi, `on:` yok, ayristirici yok)

    🔴 BELIRSIZ NEDEN "ELLE GIBI" ELE ALINIR (fail-closed YON SECIMI): ters yon
    (BELIRSIZ -> OTOMATIK saymak) kapiyi SESSIZCE GEVSETIR — cozulemeyen bir
    workflow'daki cagri "kapsandi" sayilir ve kapsamsiz bir nobetci fark edilmez
    (sahte-YESIL). Bu yonde ise BELIRSIZ yalnizca KAPSAMI DARALTIR; daralma bir
    dosyayi kapsamsiz gosterebilir, o yuzden BELIRSIZ ayrica raporda UYARI satiri
    olarak basilir ama EXIT KODUNU ETKILEMEZ (tek sahte-kirmizi tum ekibin
    yayinini durdurur, [[kapi-kapsam-eksen-secimi]])."""
    tetikler, hata = YAML_OKU.tetikleyiciler(metin)
    if hata or tetikler is None:
        return SINIF_BELIRSIZ, None, (hata or "tetik kumesi None")
    if set(tetikler) - ELLE_TETIKLER:
        return SINIF_OTOMATIK, set(tetikler), None
    return SINIF_ELLE, set(tetikler), None


def is_akislari(deploy_metin=None):
    """[(repo_rel_yol, metin, sinif), ...] — IZLENEN tum is akislari + tetik sinifi.

    <deploy_metin> verilirse deploy.yml girisinin METNI onunla degistirilir
    (`--deploy <mutant>` kolu GERCEK dosyaya dokunmadan olculebilsin diye).
    Okunamayan dosya ATLANMAZ: BELIRSIZ sinifiyla bos metinle girer (fail-closed:
    kapsam SAYILMAZ, ve rapor bunu UYARI satirinda soyler)."""
    okunan = []
    for yol in is_akisi_yollari():
        tam = os.path.join(ROOT, yol)
        if deploy_metin is not None and os.path.abspath(tam) == os.path.abspath(
                DEPLOY_VARSAYILAN):
            okunan.append((yol, deploy_metin, True))
            continue
        try:
            with open(tam, encoding="utf-8") as f:
                okunan.append((yol, f.read(), True))
        except OSError:
            okunan.append((yol, "", False))
    # psych kolunda her tetik sorgusu bir ruby SURECI acar -> TOPLU isit (tek surec).
    YAML_OKU.tetik_onbellegi_isit([m for _y, m, ok in okunan if ok])
    kayit = []
    for yol, metin, ok in okunan:
        if not ok:
            kayit.append((yol, "", SINIF_BELIRSIZ))
            continue
        sinif, _tetikler, _hata = tetik_sinifi(metin)
        kayit.append((yol, metin, sinif))
    return kayit


def kosulan_coklu(akislar, kesif):
    """(kos_otomatik, kos_elle) — hangi kesif dosyasi hangi is akis(lar)inda kosuyor.

    kos_otomatik: {yol -> {workflow_yolu, ...}} — OTOMATIK tetikli is akislari
    kos_elle    : {yol -> {workflow_yolu, ...}} — ELLE ve BELIRSIZ tetikli is akislari

    KAPSAM YALNIZ kos_otomatik'ten sayilir (A2). kosulan()'in imzasi/semantigi
    AYNEN KALIR: bulgu1 / muaf / bayraksiz / kendini-test nobetcileri onu TEK
    METINLE cagirir ve bu fonksiyon onlarin gordugu seyi DEGISTIRMEZ."""
    kos_otomatik = {}
    kos_elle = {}
    for akis_yol, metin, sinif in akislar:
        # TEK KAYNAK (O4): bayrak_envanteri() ile AYNI predikat.
        hedef = kos_otomatik if otomatik_mi(sinif) else kos_elle
        for yol in kosulan(metin, kesif):
            hedef.setdefault(yol, set()).add(akis_yol)
    return kos_otomatik, kos_elle


# T8: kosulan()'in capasina uyan "bare" form — komut govdesi 'python3 <duz-gorece-yol>'
# ile baslar (yol '-' bayragiyla, './' ile ya da '/' tam-yolla BASLAMAZ).
SAYILABILIR_PY3 = re.compile(r"^python3\s+[A-Za-z0-9_][\w./-]*(?:\s|$)")


def sayilamayan_python3(deploy_metin):
    """T8 GELECEK-ROBUSTLUK UYARISI (BLOKLAMAZ — exit kodunu ETKILEMEZ).

    T7 capasi ('^python3 <yol>') su GERCEK-ICRA formlarini SAYAMAZ: 'env X=1 python3 ...',
    'cd x && python3 ...', 'python3 -X utf8 tools/x.py' (bayrak araya), 'python3 ./tools/x.py',
    '/usr/bin/python3 ...'. Cari deploy.yml'de hepsi bare form (18/18, olculdu T8) -> cari
    sorun YOK. RISK: gelecekte biri kapiyi bu formlarla eklerse kosulan() onu 'kosulmuyor'
    sanir -> YANLIS-POZITIF KIRMIZI tum yayini durdurur ve kapi suclanir. Bu fonksiyon
    _icra_komutlari()'ndan gecen (YORUM OLMAYAN) satirlarda 'python3' gecen ama bare capaya
    uymayan satirlari dondurur; main() bunlari BLOKLAMAYAN uyari olarak basar."""
    supheli = []
    for k in _icra_komutlari(deploy_metin):
        if "python3" not in k:
            continue
        if SAYILABILIR_PY3.match(k):
            continue
        supheli.append(k)
    return supheli


# ---- BOLUM B: OPT-IN ALT KUME BEYANI ---------------------------------------
# NE ISE YARAR: bir kabul testi dosyasi, CI'ya baglanabilir DETERMINISTIK alt kumesini
# KENDI ICINDE beyan eder; kapi o alt kumenin OTOMATIK bir is akisinda FIILEN kosuyor
# olmasini ZORUNLU kilar.
#
# BICIM (satir basi, bosluk serbest; satirin kalani serbest aciklama):
#     .py            -> yorum isareti `#`  + etiket + iki nokta + tek jeton
#     .js/.mjs/.cjs  -> yorum isareti `//` + etiket + iki nokta + tek jeton
# Jeton `--` ile BASLAMAK ZORUNDA. Bir dosyada birden cok beyan satiri olabilir.
#
# 🔴 KENDI DOSYASINDA SIZINTI TUZAGI ([[nobetci-kendi-dosyasinda-sizinti]]): bu dosya
# kesif predikatina ZATEN giriyor (`-test.py`), yani bu bicimi ANLATAN her yorum satiri
# GERCEK bir beyan gibi ayristirilabilirdi. O yuzden prose'da DAIMA `<bayrak>` yer
# tutucusu kullanilir, ASLA gercek bir `-`+`-` ornegi yazilmaz. Bunun FIKSTURU var
# (BEYAN_FIKSTURLERI: doc bicimi beyan SAYILMAMALI) — yani kural metinde degil
# OLCUMDE durur.
#
# 🔴 NEDEN DUZ BAYRAK KAPSAMI DEGIL — OLCULDU VE CURUDU (bkz. ALT_KUME_IZIN_LISTESI
# basligi): duz bayrak kapsami sinyal/gurultu ~1:115 olur ve her yeni modifikator
# bayrak TUM ekibin yayinini kirmiziya cevirir. BEYAN EDILMEYEN bayrak bu kapiya
# GORUNMEZ -> yanlis-kirmizi yuzeyi ~sifir.
BEYAN_ETIKETI = "CI-ALT-KUME"
BEYAN_RE = re.compile(r"^[ \t]*(?:#|//)[ \t]*" + BEYAN_ETIKETI + r":[ \t]*(--\S+)")

# O9: bir satirin "beyan OLMAK ISTEDIGI ama ayristirilamadigi" hali. BLOKLAMAZ, tani basar.
BEYAN_BENZERI_RE = re.compile(r"^[\s﻿]*(?:#|//|\*|/\*)", re.U)

_JETON_CAPA_ONBELLEK = {}


def _jeton_capasi(bayrak):
    """<bayrak>'i JETON SINIRIYLA arayan regex (O10 — ALT-DIZE capasi curume kacirtiyordu).

    🔴 OLCULEN KACIS: curume kurali `bayrak not in metin` ALT-DIZE arıyordu. `--x`
    girisi, dosyada bayrak `--x-yeni` diye YENIDEN ADLANDIRILDIKTAN sonra da "taze"
    kaliyordu (`--x` hala `--x-yeni`'nin icinde geciyor) -> BAYAT kirmizisi HIC YANMADI
    (3 vakada olculdu). Jeton sinirinda `-`/`_`/alfanumerik DEVAM ETMEMELIDIR."""
    capa = _JETON_CAPA_ONBELLEK.get(bayrak)
    if capa is None:
        capa = re.compile(r"(?<![\w-])" + re.escape(bayrak) + r"(?![\w-])")
        _JETON_CAPA_ONBELLEK[bayrak] = capa
    return capa


def beyanlari_ayikla(metin):
    """[bayrak, ...] — <metin>'in KENDI ICINDE beyan ettigi CI alt kumeleri.

    Sirali ve tekrarsiz. `--` ile BASLAMAYAN jeton (or. doc yer tutucusu) beyan
    SAYILMAZ: bu, kapinin kendi dokumantasyonunu kendi kurali sanmasini engelleyen
    tek mekanizmadir.

    O9: jetonun SONUNDAKI noktalama temizlenir. Olculdu — virgullu yazim
    (`<etiket>: --bayrak, --beta`) `--bayrak,` jetonu uretiyordu; o jeton dosya
    metninde ASLA gecmedigi icin curume kurali SAHTE-KIRMIZI yakiyordu."""
    bulunan = []
    for satir in metin.splitlines():
        m = BEYAN_RE.match(satir)
        if not m:
            continue
        bayrak = m.group(1).rstrip(",;.:)]}\"'")
        if bayrak.startswith("--") and bayrak != "--" and bayrak not in bulunan:
            bulunan.append(bayrak)
    return bulunan


def beyan_benzeri_ayristirilamayan(metin):
    """[(satir_no, satir), ...] — icinde BEYAN ETIKETI GECEN ama beyan olarak
    AYRISTIRILAMAYAN YORUM satirlari (O9 — BLOKLAMAZ, yalniz tani).

    🔴 NEDEN: beyan yaziminin 8 varyantindan 6'si SESSIZCE dusuyordu (BOM, kucuk harf
    etiket, `/* */`, jsdoc ` * `, iki nokta yok, tirnakli bayrak). Tipo = beyanin
    TUMUYLE SILINMESI ve HICBIR tani yok -> yazar 'beyan ettim' saniyor, kapi gormuyor.
    SAYI CAPASI EKLENMEZ (bayatlar); yalniz gorunur tani basilir.
    Yer tutucu disiplini: etiket sabitten TURETILIR, bu dosyanin kendi prose'u
    `#`/`//` ile baslamayan satirlarda yasadigi icin kendi metnini beyan sanmaz."""
    bulgular = []
    for i, satir in enumerate(metin.splitlines(), 1):
        if BEYAN_ETIKETI.lower() not in satir.lower():
            continue
        if not BEYAN_BENZERI_RE.match(satir):
            continue
        if BEYAN_RE.match(satir):
            continue
        bulgular.append((i, satir.strip()[:120]))
    return bulgular


def dosya_metinleri_oku(kesif):
    """({yol: metin}, okunamayan) — KESFEDILEN dosyalarin icerigi.

    Okunamayan dosya LISTEYE GIRMEZ (fail-open: beyan/capa sorulari o dosya icin
    sorulmaz; kapsam kurali degismez) AMA SAYIYLA raporlanir.

    🔴 O8: ONCE yalniz `OSError` yakalaniyordu. UTF-8 OLMAYAN baytli IZLENEN bir test
    dosyasi `UnicodeDecodeError` atar (OSError DEGIL) ve BLOKLAYICI kapiyi TRACEBACK'le
    patlatirdi — okunur tani yerine yigin izi, tum yayin durur. Artik her istisna
    yakalanir ve 'okunamadi' olarak SAYILIR (sessiz atlama degil)."""
    metinler = {}
    okunamayan = []
    for yol in kesif:
        try:
            with open(os.path.join(ROOT, yol), encoding="utf-8") as f:
                metinler[yol] = f.read()
        except Exception as e:  # noqa: BLE001 — bilincli: tek dosya kapiyi patlatmasin
            okunamayan.append((yol, "%s: %s" % (type(e).__name__, e)))
    return metinler, okunamayan


def _bayrak_jetonlari(argumanlar):
    """Bir cagrinin ETKILI argumanlarindan BAYRAK jetonlari.

    O6: GNU `--bayrak=deger` yazimi da SAYILIR. Olculdu (bagimsiz curutucu): gercek
    `--yonet-cerez` cagrisi `--yonet-cerez=1` bicimine cevrildiginde alt kume
    'kosmuyor' sayiliyordu -> SAHTE-KIRMIZI (tum ekibin yayini durur). Hem tam jeton
    hem `=` oncesi kok eklenir; `--` tek basina bayrak DEGILDIR."""
    bayraklar = set()
    for a in (argumanlar or []):
        if not a.startswith("--") or a == "--":
            continue
        bayraklar.add(a)
        if "=" in a:
            kok = a.split("=", 1)[0]
            if kok != "--":
                bayraklar.add(kok)
    return bayraklar


def bayrak_envanteri(akislar, kesif):
    """{yol: (otomatik_bayraklar, elle_bayraklar, olculemedi_satirlar)}.

    Bayrak tespiti HAM METINDE `in` ARAMASIYLA YAPILMAZ: hukum SUZGEC.anlamli_cagri()
    EVET dedigi zaman DONEN `argumanlar` listesinden okunur. Ham metin araması
    `echo`/yorum/`--help` sinifi sessiz kacislarin yasadigi yerdir (30 Tem, olculen
    4 delik) — suzgec o ekseni sahiplenen sertlestirilmis TEK KAYNAKTIR.

    olculemedi_satirlar = [(akis_yolu, komut, sebep), ...] — OTOMATIK bir is akisinda
    bu yolu ANAN ama JETONLANAMAYAN satirlar (fail-OPEN yonu spec B2 geregi KORUNUR).

    🔴 O2 — FAIL-OPEN KALDI AMA (a) DARALDI (b) SESSIZ DEGIL:
      (a) KAPSAM: ONCE bir tek jetonlanamayan satir o dosyanin TUM beyan edilen alt
          kumelerini "kapsanmis" yapiyordu (DOSYA duzeyi). Olculdu: gercek
          `--yonet-cerez` cagrisi SILINIP tek bozuk satir eklendiginde kapi rc=0 verip
          "kapsanan 2" YAZIYORDU — aktif YANLIS BEYAN. Artik fail-open yalniz jetonu
          o SATIRIN HAM METNINDE GECEN bayrak icin gecerlidir (spec B2 zaten SATIR
          icin veriyordu; kod DOSYA'ya genellemisti).
      (b) GORUNURLUK: fail-open ile kapsanmis sayilan her (yol,bayrak) denetle()'de
          GORUNUR bir "ALT KUME OLCULEMEDI -> kapsanmis SAYILDI" satiri basar."""
    komutlar = {}
    sinif = {}
    for akis_yol, metin, akis_sinifi in akislar:
        komutlar[akis_yol] = _icra_komutlari(metin)
        sinif[akis_yol] = akis_sinifi
    envanter = {}
    for yol in kesif:
        onek = _onek_re(yol)
        oto = set()
        elle = set()
        olculemedi = []
        for akis_yol, kmt in komutlar.items():
            oto_mu = otomatik_mi(sinif[akis_yol])
            for k in kmt:
                if not onek.match(k):
                    continue
                hukum, sebep, argumanlar = SUZGEC.anlamli_cagri(k, yol)
                if hukum == SUZGEC.OLCULEMEDI:
                    if oto_mu:
                        olculemedi.append((akis_yol, k, sebep))
                    continue
                if hukum != SUZGEC.EVET:
                    continue
                (oto if oto_mu else elle).update(_bayrak_jetonlari(argumanlar))
        envanter[yol] = (oto, elle, olculemedi)
    return envanter


def fail_open_kapsar(bayrak, olculemedi_satirlar):
    """(kapsiyor_mu, sebep) — <bayrak> jetonlanamayan bir SATIR yuzunden kapsanmis
    sayilmali mi (O2 daraltmasi).

    Yalniz jetonu HAM SATIRDA GECEN bayrak icin EVET. Jetonu hic gecmeyen bir satir
    o bayragi calistiriyor OLAMAZ, dolayisiyla onu 'kapsanmis' saymak fail-open
    DEGIL, olculmus bir YANLIS BEYANDI."""
    for akis_yol, komut, sebep in olculemedi_satirlar:
        if _jeton_capasi(bayrak).search(komut):
            return True, "%s · %s" % (akis_yol, sebep or "jetonlanamadi")
    return False, None


def alt_kume_denetimi(kesif, dosya_metinleri, bayrak_env, alt_kume_izin,
                      olculemedi_hepsi=False):
    """(hatalar, beyan_sayisi, kapsanan_sayisi, muaf_sayisi, fail_open) — BLOKLAYICI CEKIRDEK.

    fail_open = [(yol, bayrak, sebep), ...] — JETONLANAMAYAN bir satir yuzunden
    "kapsanmis" SAYILAN alt kumeler (O2). Cagiran bunlari GORUNUR uyari olarak basar;
    sessiz kalmasi olculmus bir YANLIS BEYANDI.

    KURAL (ucuncu hal YOK):
      1. OTOMATIK bir is akisi o dosyayi FIILEN kosuyor VE komutun etkili argumanlari
         arasinda bayrak geciyor  -> KAPSANMIS
      2. Degilse alt_kume_izin[(yol, bayrak)] DOLU gerekce ile var -> MUAF
      3. Ucuncu hal yok -> hata (exit 1)

    CURUME KURALLARI (dosya duzeyindeki 2/3/4'un aynasi):
      * bos/boslukli gerekce                      -> hata
      * yol artik KESFEDILMIYOR                   -> hata (BAYAT)
      * bayrak jetonu dosya METNINDE hic gecmiyor -> hata (BAYAT; ucuz ve saglam capa:
        bayrak yeniden adlandirilirsa giris curur)
      * giris VAR ama alt kume OTOMATIK'te FIILEN kosuyor -> hata (BAYAT)"""
    hatalar = []
    fail_open = []
    beyan_sayisi = 0
    kapsanan = 0
    muaf = 0
    kesif_kume = set(kesif)

    for yol in kesif:
        metin = dosya_metinleri.get(yol)
        if metin is None:
            continue
        oto, _elle, olculemedi = bayrak_env.get(yol, (set(), set(), []))
        for bayrak in beyanlari_ayikla(metin):
            beyan_sayisi += 1
            if bayrak in oto:
                kapsanan += 1
                continue
            # 🔴 P5 — AYRISTIRICI YOKKEN "KOSMUYOR" DEME, "OLCULEMEDI" DE.
            # Olculen AKTIF YANLIS BEYAN: ayristirici kapaliyken rapor
            # "BEYAN EDILEN ALT KUME KOSMUYOR: shop/test/kabul.js --sema-paritesi"
            # yaziyordu — oysa o alt kume CI'da BLOKLAYICI kosuyor. Dosya ekseninde
            # OLCULEMEDI denip alt kume ekseninde KOSMUYOR demek KENDI ICINDE celiskili.
            if olculemedi_hepsi:
                # kapsanan ARTIRILMAZ: bu bir "kapsandi" hukmu DEGIL, "olcemedik"tir.
                fail_open.append((yol, bayrak, "hicbir GERCEK YAML ayristiricisi yok",
                                  False))
                continue
            # O2: fail-open ARTIK SATIR DUZEYINDE ve GORUNUR.
            acik, sebep = fail_open_kapsar(bayrak, olculemedi)
            if acik:
                kapsanan += 1
                fail_open.append((yol, bayrak, sebep, True))
                continue
            gerekce = alt_kume_izin.get((yol, bayrak))
            if gerekce and gerekce.strip():
                muaf += 1
                continue
            hatalar.append(
                "BEYAN EDILEN ALT KUME KOSMUYOR: %s %s -> dosya kendi icinde bu alt "
                "kumeyi CI'ya baglanabilir ilan ediyor ama OTOMATIK tetikli hicbir is "
                "akisi onu bu bayrakla kosmuyor. Ya bloklayici bir adima bagla ya da "
                "ALT_KUME_IZIN_LISTESI'ne OLCULMUS gerekceyle yaz." % (yol, bayrak))

    for (yol, bayrak), gerekce in sorted(alt_kume_izin.items()):
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ alt kume izni (bos gerekce): %s %s" % (yol, bayrak))
        if yol not in kesif_kume:
            hatalar.append("BAYAT alt kume izni (yol artik KESFEDILMIYOR — sil ya da "
                           "yolu duzelt): %s %s" % (yol, bayrak))
            continue
        metin = dosya_metinleri.get(yol)
        # O10: JETON SINIRLI capa (alt-dize capasi `--x` -> `--x-yeni` curumesini kacirdi).
        if metin is not None and not _jeton_capasi(bayrak).search(metin):
            hatalar.append("BAYAT alt kume izni (bayrak jetonu dosyanin METNINDE HIC "
                           "gecmiyor — yeniden adlandirildi ya da silindi): %s %s"
                           % (yol, bayrak))
        oto, _elle, _olculemedi = bayrak_env.get(yol, (set(), set(), []))
        if bayrak in oto:
            hatalar.append("BAYAT alt kume izni (alt kume ARTIK OTOMATIK is akisinda "
                           "KOSUYOR — izinden cikar): %s %s" % (yol, bayrak))
    return hatalar, beyan_sayisi, kapsanan, muaf, fail_open


# ---- BOLUM C: UYARI KATMANI (EXIT KODUNA ASLA DOKUNMAZ) --------------------
def _py_bayrak_analizi(metin):
    """(tum_bayraklar, ayri_main_kolu_bayraklari) — .py dosyasinin argparse bayraklari.

    🟡 "AYRI MAIN KOLU" TESPITI **HEURISTIKTIR** ve raporda ACIKCA oyle etiketlenir:
    `add_argument("<bayrak>", action="store_true")` ile tanimli bir bayragin `dest`'i
    bir `if` testinde geciyor VE o `if` govdesinde `return` / `<modul>.exit(...)` var.
    Yani "bu bayrak programi BASKA bir kola sokup erken bitiriyor" tahminidir; kesin
    degildir ve HICBIR SEYI BLOKLAMAZ. Ayristirilamayan dosya (None, None) doner."""
    try:
        agac = ast.parse(metin)
    except SyntaxError:
        return None, None
    tum = set()
    bayrak_dest = {}
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute)
                and dugum.func.attr == "add_argument"):
            continue
        adlar = [a.value for a in dugum.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)
                 and a.value.startswith("--")]
        if not adlar:
            continue
        tum.update(adlar)
        aksiyon = None
        dest = None
        for kw in dugum.keywords:
            if kw.arg == "action" and isinstance(kw.value, ast.Constant):
                aksiyon = kw.value.value
            if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                dest = kw.value.value
        if aksiyon != "store_true":
            continue
        for ad in adlar:
            bayrak_dest[ad] = dest or ad[2:].replace("-", "_")
    erken = set()
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.If):
            continue
        adlar = set()
        for t in ast.walk(dugum.test):
            if isinstance(t, ast.Name):
                adlar.add(t.id)
            elif isinstance(t, ast.Attribute):
                adlar.add(t.attr)
        if not adlar:
            continue
        cikis = False
        for govde in dugum.body:
            for t in ast.walk(govde):
                if isinstance(t, ast.Return):
                    cikis = True
                elif (isinstance(t, ast.Call) and isinstance(t.func, ast.Attribute)
                        and t.func.attr == "exit"):
                    cikis = True
        if cikis:
            erken |= adlar
    ayri = {b for b, dest in bayrak_dest.items() if dest in erken}
    return tum, ayri


UYARI_TAVANI = 20


def _uyari_listesi(etiket, kalemler):
    """Kirpilmis liste satirlari. 🔴 SESSIZ KIRPMA YOK ([[hukum-yanlis-birimde]]):
    kac kalem DUSURULDUGU yazilir."""
    satirlar = ["  %s: %d" % (etiket, len(kalemler))]
    for yol, bayrak in kalemler[:UYARI_TAVANI]:
        satirlar.append("      %s %s" % (yol, bayrak))
    if len(kalemler) > UYARI_TAVANI:
        satirlar.append("      ... %d kalem BASILMADI (tavan %d)"
                        % (len(kalemler) - UYARI_TAVANI, UYARI_TAVANI))
    return satirlar


def uyari_katmani(kesif, dosya_metinleri, bayrak_env, alt_kume_izin):
    """[rapor_satiri, ...] — A-SINIFI ADAYLARI HER KOSUMDA YUZEYE CIKARIR.

    🔴 EXIT KODUNA ASLA DOKUNMAZ. Cagiran taraf bu fonksiyonu `try/except Exception`
    ile sarar; istisna tek satir "UYARI KATMANI OLCULEMEDI" olur ve exit kodu
    DEGISMEZ ([[duzeltme-fail-open-cevirebilir]] dersinin tersi degil: bu katman zaten
    bloklamiyor, TEK riski bloklayan koda istisna sizdirmasidir).

    Uc sinif basilir: (a) ayri bir main kolu tetikleyen, (b) hicbir is akisinda
    kosmayan, (c) beyan edilmemis ve muaf olmayan. Ayrica (d) YALNIZ ELLE tetiklenen
    is akisinda kosan bayraklar AYRI satirda ("CI kapsami SAYILMAZ") listelenir.
    "basarili / olculemedi" AYRI sayilir, tek toplamda gizlenmez."""
    ayri_kol = []
    kosmayan = []
    beyansiz = []
    yalniz_elle = []
    js_olculemedi = 0
    py_olculemedi = 0
    olculen_dosya = 0
    for yol in sorted(kesif):
        metin = dosya_metinleri.get(yol)
        if metin is None:
            continue
        oto, elle, _olculemedi = bayrak_env.get(yol, (set(), set(), []))
        if not yol.endswith(".py"):
            js_olculemedi += 1
            for b in sorted(elle - oto):
                yalniz_elle.append((yol, b))
            continue
        tum, ayri = _py_bayrak_analizi(metin)
        if tum is None:
            py_olculemedi += 1
            continue
        olculen_dosya += 1
        beyan = set(beyanlari_ayikla(metin))
        for b in sorted(tum):
            if b in oto:
                continue
            if b in ayri:
                ayri_kol.append((yol, b))
            if b not in oto and b not in elle:
                kosmayan.append((yol, b))
            if b not in beyan and (yol, b) not in alt_kume_izin:
                beyansiz.append((yol, b))
        for b in sorted(elle - oto):
            yalniz_elle.append((yol, b))

    satirlar = ["UYARI KATMANI (BLOKLAMAZ — exit kodunu ETKILEMEZ)"]
    satirlar.extend(_uyari_listesi(
        "(a) 🟡 HEURISTIK — ayri bir main kolu tetikleyen ama OTOMATIK is akisinda "
        "KOSMAYAN bayrak", ayri_kol))
    satirlar.extend(_uyari_listesi(
        "(b) hicbir is akisinda (OTOMATIK ya da ELLE) KOSMAYAN bayrak", kosmayan))
    satirlar.extend(_uyari_listesi(
        "(c) BEYAN EDILMEMIS ve muaf OLMAYAN bayrak", beyansiz))
    satirlar.extend(_uyari_listesi(
        "(d) YALNIZ ELLE tetiklenen is akisinda kosuyor — CI kapsami SAYILMAZ",
        yalniz_elle))
    satirlar.append("  olculen: %d .py dosyasi · olculemedi: %d dosya (js/mjs/cjs — "
                    "bayrak cikarimi YAPILMADI) + %d dosya (py ayristirilamadi)"
                    % (olculen_dosya, js_olculemedi, py_olculemedi))
    return satirlar


# ---- GEREKCE SABITLERI -----------------------------------------------------
R_AYRI = ("Ayri alt-proje/dagitim hedefi (shop=Cloudflare Worker, onizleme, jenerator kendi "
          "harness'i). Bu is akisi YALNIZ GitHub Pages site build'i; bu suite o projenin CI "
          "hattinda kosulur, Pages job'una girmez.")
# 🔴 R_NODE SABITI KALDIRILDI (30 Tem) — GEREKCE FIILEN YANLISTI, GERI EKLEME.
# Metni soyleydi: "CI build job'u Python-only (setup-node yok) -> JS/Node suite'i kosamaz."
# OLCULDU: .github/workflows/deploy.yml'de `actions/setup-node@v4` (node 20) BLOKLAYICI bir
# ON-KOSULDUR ve o is akisinda ZATEN bes node testi kosuyor (shop/test/*.mjs, sepet-panel.js,
# jenerator/test/*.js|mjs, onizleme/test/*.mjs). Yani bu gerekce dogru olsaydi o adimlarin
# hepsi kirmizi yanardi. Gerekceye dayanan dort giris (riza-tikkimligi-test.js — GIZLILIK,
# attribution-ref-test.js — LISANS ATIFI, url-senkron-test.js, marka-limit-test.js)
# muafiyetten CIKARILDI ve deploy.yml'de bloklayici adim olarak kosuyor.
# "CI'da node yok" gerekcesiyle YENI bir muafiyet yazmak isteyen once bu satiri okusun.
R_AG = ("Ag/uzak platform erisimi gerektirir (parite CDN'e vurur) -> CI'da deterministik degil; "
        "ag-izinli ayri adim gerekir (RAPOR onerisi).")
R_YOL = ("Mimar-disiplin kapisi: mutlak /Users/okan/dev/pruvo yoluna VE commit EDILMEYEN "
         ".claude/settings.json + .git/hooks kablolamasina bagli -> GitHub fresh checkout'ta "
         "yapisal olarak KIRMIZI. Yerel gelistirici disiplini araci, deploy CI adimi degil.")
R_YAVAS = ("Yerelde >30s (build+ag ya da mutasyon harness) -> tek build job'unu blokar; "
           "izole/ayri job olmadan Pages hattina alinmaz (RAPOR onerisi).")
# 🔴 R_SONRA (31 TEM): GEREKCE CURUTULDU, YENI GIRIS ICIN KULLANMA.
# Metni "sonraki turda CI'ya alinabilir / deploy.yml'e 0-hunk sarti var" idi — yani
# TEKNIK degil SURECSEL bir gerekce; o tur bitince gerekce OLDU ama muafiyet KALDI.
# Bu, denetimde "curuk gerekce" sinifinin ta kendisidir: kimse kapiyi acmiyor, kimse
# de KIRMIZI gormuyor. OLCULDU (31 Tem, `git clone --local` ile kurulan TEMIZ CI-benzeri
# checkout, HEAD): R_SONRA'li 27 girisin 26'si rc=0 ve toplam ~11 s; 24'u mutasyonla
# CANLI oldugu (konusu bozulunca KIRMIZI yandigi) kanitlandi ve deploy.yml'de
# continue-on-error'SUZ BLOKLAYICI adim olarak baglandi. Kalan uc giris ASAGIDA
# TEK TEK ve SOMUT gerekceyle durur (R_SONRA metnine dayanan giris KALMADI).
R_SONRA = ("KULLANIM DISI (bkz. yukaridaki not): surecsel 'sonraki turda' gerekcesi "
           "31 Tem'de curutuldu. Yeni muafiyet SOMUT ve OLCULEBILIR bir engel yazmali "
           "(yapisal CI-kirmizi / ag / sure / gizli girdi).")
R_HOOK = ("Claude Code PreToolUse KANCASI, kosulabilir kabul testi DEGIL: stdin'den JSON alir, "
          "karar objesi dondurur (argumansiz kosunca girdi yok -> exit 0, hicbir sey kanitlamaz). "
          "Yerel ajan disiplin cihazi; GitHub Pages build'inde karsiligi yok.")
R_GIZLI = ("Gizli/izlenmeyen girdiye bagli: .urun-kaynaklari.json (gitignore) + working-tree'de "
           "stage'lenmis PARTI farki. CI fresh checkout'unda ikisi de YOK -> kapi bos parti "
           "gorup anlamsiz YESIL yakar (sahte nobetci). Urun-ekleme hattinda (MaCiT) yerel "
           "kosulur; deploy hattinin girdisi degil.")
R_TASARIM = ("TASARIM GEREGI yayin-disi (kendi dosyasindaki not): 'bu kapi build.py'ye BAGLANMAZ "
             "— tek kotu kategori TUM yayini kirmasin'. Kategori drifti urunu katalogda birakir, "
             "yalniz filtreden dusurur; yayini bloklamak orantisiz. Bagimsiz calistirilabilir "
             "kabul testi olarak yerelde/duzeltme akisinda kosulur.")
R_YEREL_HIJYEN = ("Yerel calisma-agaci hijyeni: .gitignore blogunun CONTENT_PAGES ile ortusmesini "
                  "denetler. Drift CI'da GORUNMEZ (uretilen dizinler fresh checkout'ta yok) ve "
                  "canli siteyi bozmaz — yalniz gelistiricinin `git status`ini kirletir/kazara "
                  "commit riski dogurur. Yayini bloklamasi orantisiz; commit oncesi yerel kapi.")
# 🔴 30 TEM — DURUST GEREKCE: kesif predikati jenerator/test/ altindaki HER .py/.js'i
# "kabul testi" sayar, ama bu dizindeki bir kismi TEST DEGIL: fikstur/cikti URETECI ya da
# CLI yardimcisi. Denetimde olculdu (IDDIA sutunu "IDDIA-YOK"): konularini tamamen bozsan
# bile rc=0 veriyorlar, cunku iddialari YOK. Bunlar CI'ya BAGLANMAMALI — kosarlarsa
# uzerine yazdiklari fiksturu/kaynagi EZERLER (birlestir.py dogrudan hacim.js'i yeniden
# yazar; *-uret.py referans dosyalarini uretir). Muafiyetleri MESRU; eskiden R_AYRI
# ("o projenin CI hattinda kosulur") deniyordu — o hat YOK ve zaten kosmamalilar.
R_URETEC = ("KABUL TESTI DEGIL — fikstur/cikti URETECI ya da CLI yardimcisi (olculdu: "
            "konusu tamamen bozulunca bile rc=0, yani hicbir iddiasi yok). CI'da KOSMAMALI: "
            "kosarsa uzerine yazdigi fiksturu/kaynagi EZER. Elle, gelistirme akisinda "
            "cagrilir; uretimin dogrulugunu tuketen KABUL testleri ayrica olcer.")

R_FTS5 = ("Yerel fts5-trigram sqlite gerektirir (sema-yukleme adiminda CREATE VIRTUAL TABLE ... "
          "USING fts5(tokenize='trigram')). CI ubuntu stok sqlite3'unde fts5-trigram tokenizer'i "
          "yok -> test daha sema yuklerken patlar (yerel-yesil / CI-kirmizi). R_YAVAS/R_YOL ile "
          "ayni sinif: yapisal olarak CI-disi, deploy.yml'e EKLENMEZ; canli D1 dogrulamasi ayri "
          "go-live fazinda yapilir.")

# R_SAHIPLIK = ("Paket ③ (18 Agu 2026, BaBa hukmu, KraL mimar): KAPI/NOBET sahiplik haritasi "
#              "kapisi. Salt-okunur envanter + invaryant kontrolu + `--kendini-test` bayragi "
#              "(3 mutant + 2 kontrol). CI'da ayri kosulmaz (R_URETEC + R_TASARIM karisimi: "
#              "KENDISI evren hesaplar ve evrene kendi dahildir -- CI'da koşarsa oz-dongu "
#              "sinyali uretir); merge-kapisi sirasinda ve mimar oncesi elle kosulur. "
#              "IDDIA semasi: --kendini-test 3 mutant RED + 2 kontrol YESIL; main cikti "
#              "EVREN=HARITADA EKSIK=0 BAYAT=0.")
# Paket ③-d §4 (18 Agu 2026): R_SAHIPLIK muafiyeti ve IZIN_LISTESI girisi KALDIRILDI —
# kapi artik nobet.yml SERIT B adimi olarak OTOMATIK kosar (`python3 tools/sahiplik-kapisi.py`).
# Referans yorum olarak korunur; muafiyet/izin anlamsiz ve yanlis yon olurdu.

# ---- IZIN LISTESI (muaf test -> GEREKCE). Bos gerekce = exit 1. ----------
IZIN_LISTESI = {
    # --- Izin-kancasi KAYNAKLARI (silinemez sinif — BaBa 29 Agu FILO FELCI karari) ---
    # 29 Agu supurmesi (ca8c3815) bu iki govdeyi silmisti; oturum kancalari bunlari
    # calisma aninda OKUDUGU icin filodaki her oturumun Bash'i fail-closed kilitlendi
    # (kutu ~19:xZ teshisi). Geri yuklendiler. CI tuketicileri (deploy.yml K304 adimlari,
    # nobet.yml) supurmede BILEREK sokuldu ve geri TAKILMADI — bunlar CI'da kosan kabul
    # testleri degil, PreToolUse kancasinin calisma aninda okudugu izin-kapisi
    # govdeleridir; canliliklari her Bash cagrisinda olculur (dosya yoksa oturumlar
    # aninda DENY basar, sessiz curume yapisal olarak imkansiz).
    "tools/mimar-icra-kapisi.py": (
        "IZIN-KANCASI KAYNAGI, kabul testi DEGIL: 6 evin .claude shim'i bu govdeyi her "
        "Bash cagrisinda calisma aninda okur (K304 tek kaynak). 29 Agu supurmesi silince "
        "tum filo fail-closed kilitlendi; BaBa'nin silinemez-sinif kurali ile geri "
        "yuklendi. CI'da kosturulmaz; canliligi kancanin kendisi olcer."),
    "tools/kapi-dagitim-kapisi.py": (
        "IZIN-KANCASI KAYNAGI, kabul testi DEGIL: supurme oncesi settings ile acik "
        "canli oturumlarin Bash kancasi bu dosyayi calisma aninda okur (MaCiT "
        "blokajinda stub ciftiyle olculdu, kutu 29 Agu). Ayni silinemez-sinif kurali "
        "ile geri yuklendi; CI tuketicisi supurmede bilerek sokuldu, geri takilmadi."),
    # --- Ayri dagitim hedefleri (shop / onizleme / jenerator) ---
    # "shop/test/eposta.mjs" MUAFIYETI KALDIRILDI (31 Tem) — R_AYRI'nin cekirdek cumlesi
    # ("bu suite o projenin CI hattinda kosulur") bu dosya icin OLCULEREK YANLIS: oyle bir
    # hat YOK (repoda yalniz deploy.yml + onizleme-imaj.yml var) ve test wrangler/ag/D1
    # ISTEMEZ — shop/src/eposta.js'i DOGRUDAN import eder, TEMIZ checkout'ta 0,05 s.
    # Kardesleri (fiyat-prova.mjs, iki-renk-ucret.mjs, olcum.mjs, sepet-panel.js) zaten
    # deploy.yml'de kosuyor. Muafiyetin bedeli PARA ekseninde: siparis e-postasindaki urun
    # linki/kapak gorseli sessizce duserse musteri neyi aldigini goremez.
    # "shop/test/ref-route.mjs" MUAFIYETI KALDIRILDI (31 Tem) — AYNI sinif: ref.js dogrudan
    # import edilir, env.KATALOG mock'lanir (wrangler/ag YOK, 0,07 s). Nobet ekseni REKLAM
    # ATIFI + D1 KOTA KORUMASI (click-id kalicilik, INSERT OR IGNORE, IP rate-limit).
    # "shop/test/kabul.js" MUAFIYETI KALDIRILDI (31 Tem) — gerekce KISMEN dogruydu ve tam da
    # bu yuzden tehlikeliydi: suite'in BIR YARISI gercekten CI-disi (test 1..25 `wrangler dev
    # --local` + `npx wrangler@4` indirmesi; test 7 CANLI /ara ucuna vurup YEREL urunler.json
    # ile karsilastirir -> KARARSIZ, olculdu: sorgu sayisi kosumdan kosuma 841 <-> 843 kayiyor,
    # cunku sorgular katalogtan turuyor ve baska oturumlar urun ekliyor). Ama AYNI dosyadaki
    # test 9(a) — "semalar.js import listesi <-> jenerator/urunler/ BIREBIR mi" — agsiz,
    # wranglersiz ve TAMAMEN deterministik bir PARA nobetiydi ve blanket muafiyet yuzunden
    # HIC KOSMUYORDU: sari seri semasi listeye eklenmezse urun kartla tahsil edilemez.
    # COZUM (susturma DEGIL, AYIRMA): dosyaya `--sema-paritesi` kolu eklendi (9a + 9b + 26
    # sari fail-closed; ag/wrangler/D1 YOK, 12 ard arda kosumda cikti sha256 birebir ayni,
    # ~0,06 s) ve deploy.yml'de `continue-on-error`SUZ BLOKLAYICI kosuyor. Non-deterministik
    # yari (bayraksiz tam kosum + test 7) CI'ya BAGLANMADI — silinmedi/susturulmadi, yerelde
    # ve merge kapisinda kosulmaya devam ediyor.
    # 🔴 IKINCI KATMAN: liste ekseninin KENDISI artik elle bakimli degil —
    # tools/sema-bundle-kapisi.py semalar.js'i jenerator/urunler/'den TURETIR ve drift'i ayrica
    # bloklar (mukerrer/eksik sema id'si dahil, ki 9a onu GORMUYORDU).
    # "shop/test/olcum-kapisi.cjs" MUAFIYETI KALDIRILDI (30 Tem) — iki kat yanlisti.
    # (1) Gerekce R_AYRI ("bu suite o projenin CI hattinda kosulur") idi; oyle bir hat YOK.
    # (2) Daha kotusu dosya SAF MODULDU: `module.exports` var, `require.main` kolu YOK ->
    #     `node shop/test/olcum-kapisi.cjs` rc=0 verip SIFIR IDDIA kosuyordu. Olculdu:
    #     shop/.dev.vars'a SAHTE bir META_CAPI_TOKEN + GA4_API_SECRET konsa BILE rc=0.
    #     Tek tuketicisi shop/test/kabul.js, o da wrangler dev istedigi icin hicbir yerde
    #     kosmuyor -> "yerel test GERCEK Meta pikseline sahte Purchase basmasin" fail-closed
    #     kapisi FIILEN YOKTU. Dosyaya ciplak kosum kolu eklendi (A: karar mantigi sentetik
    #     girdiyle, B: bu ortamdaki gercek env/dosya/wrangler.toml taramasi) -> 26 iddia,
    #     agsiz, ~0,1 s; artik deploy.yml'de BLOKLAYICI kosuyor.
    # "shop/test/olcum.mjs" MUAFIYETI KALDIRILDI (30 Tem) — gerekce OLCULEREK YANLIS bulundu.
    # R_AYRI "bu suite o projenin CI hattinda kosulur, Pages job'una girmez" diyordu; oysa
    # kardes shop testleri (konfigur-fail-closed.mjs, fiyat-prova.mjs, iki-renk-ucret.mjs)
    # deploy.yml'de ZATEN kosuyor (setup-node bloklayici on-kosul). Gercek sebep dagitim
    # hedefi degil, RUNTIME idi: test `module.registerHooks` (v22.15+) istiyordu, runner
    # Node 20 -> 6 iddia her kosuda kirmizi (129/6). Hook `module.register` (v20.6+)'a
    # cevrildi, Node 20.20.2'de 188/0 -> test artik deploy.yml'de KOSUYOR.
    # "shop/test/sepet-panel.js" MUAFIYETI KALDIRILDI (30 Tem) — olcum.mjs ile AYNI SINIF hata:
    # gerekce R_AYRI ("shop ayri Worker hedefi") idi, oysa bu test wrangler/ag/D1 ISTEMEZ;
    # index.html'in inline scriptini node:vm'de kosar ve kardesleri (konfigur-fail-closed.mjs,
    # fiyat-prova.mjs, olcum.mjs) deploy.yml'de ZATEN kosuyor. Muafiyetin bedeli olculdu:
    # EDGE_KATALOG bayragi acildiginda sahte fetch edge uclarini tanimadigi icin dosya
    # "TEST ALTYAPI HATASI" ile duruyordu -> 9 nobetcinin 9'u hicbir iddia kosturmadan
    # OLDU ve kimse gormedi (CI onu hic calistirmiyordu). Sahte fetch edge'e uyarlandi
    # (14/14 yesil) ve test deploy.yml'de BLOKLAYICI adim olarak kosuyor.
    # 🔴 31 TEM — GEREKCE DUZELTILDI (blanket R_AYRI cumlesi "o projenin CI hattinda
    # kosulur" bu ucu icin YANLISTI: oyle bir hat YOK). GERCEK engel OLCULDU (temiz
    # checkout): ilk ikisi `onizleme/derleyici/eslem-ozel.json` GIZLI paketini ister
    # (gitignore'lu, R2'den cekilir) -> CI fresh checkout'unda "Paket toplanamadi" ile
    # rc=1; ucuncusu `KAPAT_ANAHTAR` ortam degiskeni (secret) ister -> rc=2. Ucu de
    # onizleme-imaj.yml hattinda, paket + secret ayaktayken kosar.
    # 🔴 31 TEM — "onizleme/test/eslem-olcum.py" MUAFIYETI KALDIRILDI. Gerekce dogruydu
    # (TAM kol gizli paketi ister) ama BEDELI olculmedi: muaf oldugu icin HUKUM mantigi
    # CI'da hic kosmuyordu ve orada bir FAIL-OPEN vardi (422/sifir-olculen-set sessiz
    # YESIL). Cozum kabul.py deseninin aynisi: ag/paket/openscad ISTEMEYEN
    # `--kendini-test` kolu deploy.yml'de BLOKLAYICI kosar; TAM kol yine imaj hattinda.
    "onizleme/test/kabul.js": (
        R_AYRI + " Somut (31 Tem olcumu): TEMIZ checkout'ta rc=1 — ayni gizli paket "
        "girdisi (`eslem-ozel.json`) yok. Deploy hattinin girdisi degil."),
    "onizleme/test/kapi1.js": (
        R_AYRI + " Somut (31 Tem olcumu): TEMIZ checkout'ta rc=2 — `KAPAT_ANAHTAR` "
        "ortam degiskeni (secret) zorunlu; Pages build job'unda tanimli DEGIL."),
    # 28 Tem (G2): duman_toka_kabul.py -> duman_kabul.py olarak GENELLESTI (tek-aile
    # jeton pini yerine drift+kapsam kapisinin ayirt ediciligi/no-op/CI-kablo olcumu).
    # 🔴 30 Tem (O6 onarimi): bu iki girisin gerekcesi ARTIK MAKINE-DOGRULANIR. Eskiden
    # gerekce metni "onizleme-imaj.yml'de bloklayici kosar" DIYORDU ama bunu olcen
    # HICBIR makine yoktu (bu kapi YALNIZ deploy.yml'e bakar) -> curutme turunda
    # 8 etkisizlestirme mutasyonundan 7'si SESSIZ gecti. Simdi iddia
    # tools/is-akisi-kapisi.py BOLUM B'de bir IDDIA SATIRI olarak durur (dosya bazli
    # POZITIF nobetci: cagri var mi + zorunlu alt-komut var mi + `|| true`/`|| :`/
    # `continue-on-error`/`if: false`/`set +e`/`--help` ile etkisizlestirilmis mi) VE
    # ayni dosyadaki B-CAPRAZ kurali bu iki muafiyet girisinin B iddiasiyla BIRLIKTE
    # var olmasini zorlar (birini silmek digerini KIRMIZI yakar).
    "onizleme/test/duman_kabul.py": (
        R_AYRI + " Somut: onizleme-imaj.yml'de (Pages deploy'unda DEGIL) bloklayici adim "
        "olarak kosar; ana site yayinini alakasiz bir imaj isi durdurmasin diye "
        "deploy.yml'e BAGLANMAZ (jeton ekseni, [[kapi-kapsam-eksen-secimi]]). "
        "MAKINE DAYANAGI: tools/is-akisi-kapisi.py BOLUM B iddiasi 'duman_kabul' "
        "(+ B-CAPRAZ kurali)."),
    "tools/onizleme-kapisi.py": (
        R_AYRI + " Somut: kapinin KENDISI (kosulabilir kabul testi degil, olculen arac). "
        "Iki komutu da (parmakizi-dogrula / duman) onizleme-imaj.yml'de kosar ve GERCEK "
        "bir derleyici servisi ister (docker + gizli paket) -> Pages build job'unda "
        "girdisi YOK. Ayirt ediciligi onizleme/test/duman_kabul.py ile olculur. "
        "MAKINE DAYANAGI: tools/is-akisi-kapisi.py BOLUM B iddialari "
        "'parmakizi-dizin' / 'parmakizi-url' / 'duman-url' (+ B-CAPRAZ kurali)."),
    # "onizleme/test/iki-govde-olcum.py" MUAFIYETI KALDIRILDI (31 Tem) — gerekcenin son
    # paragrafi kendi kendini curutuyordu: dosyanin AGSIZ/openscad'siz `--kendini-test`
    # kolu VAR, ~0,05 s ve deterministik; eklenmeme sebebi TEKNIK degil SURECSELDI
    # ("bu turda deploy.yml'e 0 hunk sarti var"). O tur bitti, sart dustu -> kol
    # deploy.yml'de continue-on-error'SUZ BLOKLAYICI kosuyor (25 gercek commit'te 25
    # yesil). MESH olcumu (ucgen/bbox/hacim, openscad) yine YALNIZ onizleme-imaj.yml'de;
    # o cagri BOLUM B iddiasiyla ayrica korunuyor (silme/yorum/`|| true`/`if: false`
    # -> is-akisi-kapisi.py KIRMIZI).
    "onizleme/test/fiyat-taban-olcum.mjs": "Kabul KAPISI DEGIL — fiyat regresyonu icin dokum/karsilastirma ARACI (--yaz / --karsilastir). Sabit bir taban dosyasi repoda tutulmadigi icin CI'da tek basina anlamli bir iddiasi yoktur; fiyat kapilari ayri ve bloklayicidir (tools/konfigur-test.py, shop/test/fiyat-prova.mjs, shop/test/iki-renk-ucret.mjs).",
    "jenerator/test/birlestir.py": (
        R_URETEC + " Somut: aile .js dosyalarini jenerator/hacim.js'e BIRLESTIREN arac "
        "(kaynagin UZERINE yazar) — CI'da kosmasi calisma agacini degistirirdi."),
    # "jenerator/test/dogrula.py" MUAFIYETI KALDIRILDI (31 Tem, madde 34b) — R_AYRI blanket
    # gerekcesi bu dosyanin `--kendini-test` kolu icin GECERSIZDI: kol OpenSCAD YASAK
    # nobetcisini sentetik PATH/symlink fiksturleriyle sinar (18 iddia), openscad/ag/build.py
    # GEREKTIRMEZ ve deterministiktir. Muafiyet yuzunden nobetcinin KENDISI hic olculmuyordu.
    # Bayraksiz tam kosum HALA CI disi (openscad ister) — susturulmadi, yalnizca baglanmadi.
    "jenerator/test/fiyat-tablosu-uret.py": (
        R_URETEC + " Somut: Okan'a .md fiyat sablonu ureten dokum araci."),
    # "jenerator/test/fiyat-test.js" MUAFIYETI KALDIRILDI (31 Tem) — R_AYRI'nin "jenerator
    # kendi harness'i" dali OLCULEREK YANLIS: oyle bir CI hatti YOK ve test node disinda
    # HICBIR sey istemez (openscad/ag/build.py yok, TEMIZ checkout'ta 0,14 s). Kardesi
    # jenerator/test/metin-beyaz-liste.mjs zaten deploy.yml'de kosuyor. Nobet ekseni PARA:
    # sema varsayilanlari + tabanHacim + PLA/Siyah taban fiyat esdegerligi.
    "jenerator/test/hacim-eval.js": (
        R_URETEC + " Somut: stdin'den JSON alip hacim hesaplayan CLI yardimcisi "
        "(argumansiz 'gecersiz JSON' der); kabul testi degil, olcum borusu."),
    # --- sema.kisitlar ucusu (3 Agu, rulman sema araligi) --------------------
    # Ucu de AYNI iddiayi cevreler: uretim motorunun kabul kumesi ile ilan edilen
    # sema araligi arasindaki bosluk (olculdu: izgaranin 43.085/126.945 = %33,94'u
    # motorda URETILEMEZDI). Kapsam muhasebesi bu yuzden TEK BLOKTA durur.
    "jenerator/test/kisit-vakalar.js": (
        "KOSULABILIR SUITE DEGIL — vaka TABLOSU modulu (`module.exports`, `require.main` "
        "kolu YOK). OLCULDU (3 Agu, bu agac): `node jenerator/test/kisit-vakalar.js` "
        "rc=0, 0,04 s, SIFIR cikti satiri, SIFIR iddia. deploy.yml'e boyle baglanmasi "
        "shop/test/olcum-kapisi.cjs vakasinin AYNISI olurdu: iddiasiz rc=0, yani "
        "'kosuyor ama olcmuyor' ([[kapi-kapsam-eksen-secimi]]). Tablonun 22 IDDIASI "
        "CI'da FIILEN kosuyor: jenerator/test/fiyat-test.js tabloyu require edip her "
        "vakayi `esit(...)` ile iddia eder ve o dosya deploy.yml'de `build` isinde "
        "(deploy: needs: build) continue-on-error'SUZ kosar — olculdu: fiyat-test.js "
        "rc=0, 176 iddia, bunlarin 22'si 'kisit ...' satiri. Tablo bozulursa CI KIRMIZI."),
    "jenerator/test/kisit-mutasyon.js": (
        "META OZ-DOGRULAMA SURUCUSU — kabul testi DEGIL: olctugu sey yukaridaki vaka "
        "tablosunun AYIRT EDICILIGI, tablonun kendisi zaten `build` isinde bloklayici "
        "kosuyor (CI'ya baglamak CIFT SAYIM olur; tools/eski-fiyat-test.py --mutasyon ve "
        "A_MUTASYON kumesiyle AYNI depo konvansiyonu). OLCULDU (3 Agu, bu agac): rc=0, "
        "0,14 s, taban 22 iddia / 0 kirmizi, 14/14 mutant — 12 olduruculuk mutanti "
        "KIRMIZI (isaret sarti ile: her mutant beklenen vaka KODLARINI kirmizi yakti), "
        "2 KONTROL mutanti YESIL, kaynak butunlugu sha256 basta=sonda SAGLAM. "
        "ASIL BAGLANMAMA SEBEBI SURE DEGIL, CAPA BAGI ([[kapi-anchor-coupling-ikilemi]]): "
        "mutantlar konfigurator.js/sema METNINE birebir capalidir ve capa bulunamazsa "
        "'BAYAT HARNESS' ile PATLAR — kisit kolunun her mesru refaktoru TUM EKIBIN "
        "yayinini durdururdu. Kapi degil, degisiklik-zamani kanit araci; "
        "[[mutasyon-kaniti-yeniden-uretilebilir]] geregi REPODA durur."),
    "jenerator/test/rulman-uretilebilirlik-olcum.py": (
        R_GIZLI + " Somut (3 Agu, bu worktree — gitignore'lu girdiler YOK): bayrakli "
        "kosum rc=3 \"OLCULEMEDI: gizli uretim paketi yok (eslem-ozel.json)\", 0,04 s. "
        "Iki gitignore'lu girdi ister — `onizleme/derleyici/eslem-ozel.json` (uretim "
        "eslemesi, R2 paketinden gelir) ve motorun .scad kaynagi — ARTI yerel OpenSCAD; "
        "CI fresh checkout'unda ucu de YOKTUR, yani baglanirsa YAPISAL rc=3 (fail-closed "
        "'yesil sayma' kolu bilerek boyle yazilmis). Kolun HUKUM mantigi yine de "
        "olculuyor: kapali form + sema kapisinin AYNI kabul kumesini verdigi 471 GERCEK "
        "render'da 0 ayrisma ile dogrulandi; sifir-olcum artik SESSIZ YESIL degil rc=3 "
        "(mutasyon: sifir-set kolu kaldirilinca rc=0 -> onarimla rc=3). Katalog/fiyat "
        "ekseninin CI'da kosan nobetcisi jenerator/test/fiyat-test.js'tir."),
    "jenerator/test/rampa-uretilebilirlik-olcum.py": (
        "AYNI SINIF, AYNI GEREKCE (emsal: rulman-uretilebilirlik-olcum.py). Iki "
        "gitignore'lu girdi ister — `onizleme/derleyici/eslem-ozel.json` (uretim "
        "eslemesi, R2 paketinden gelir) ve motorun .scad kaynagi — ARTI yerel "
        "OpenSCAD; CI fresh checkout'unda ucu de YOKTUR, yani baglanirsa YAPISAL "
        "rc=3 (fail-closed 'yesil sayma' kolu bilerek boyle yazildi). OLCULDU "
        "(3 Agu, bu agac): paketsiz kosum rc=3 \"OLCULEMEDI: gizli uretim paketi "
        "yok (server.py)\", 0,04 s; paketli TAM kosum rc=0, 25 iddia / 0 kirmizi, "
        "944.559 noktalik ilan edilmis izgara + 1.686 GERCEK render, sema "
        "kapisindan gecen noktalarda uretilemez 0 (%0,0000), hacim kapali "
        "formunun render'a karsi en kotu sapmasi %0,0000079. Mutasyon bataryasi "
        "(--mutasyon; mutasyon DAIMA KOPYAYA uygulanir, canli dosya sha256 "
        "basta=sonda SAGLAM): 11 mutant, 9 OLDURUCUnun hepsi ISARET SARTIYLA oldu "
        "(beklenen iddia kirmizi yandi), 2 KONTROL mutanti YESIL kaldi. "
        "Sifir-olcumu tutan 3 katman AYRI AYRI olculur (M3/M3b/M3c): ucu birden "
        "kalkinca kosum TAM YESIL donuyor — yani hicbiri tek basina 'savunma "
        "derinligi' diye sayilmiyor. Satisa acma karari MIMARIN; bu arac yalnizca "
        "dayanagi olcer."),
    # "jenerator/test/kabul.py" MUAFIYETI KALDIRILDI (31 Tem, madde 34b) — ayni gerekce:
    # `--kendini-test` kolu TARAMA KUMESI nobetcisini sinar (5 iddia: gitignore'lu artefakt
    # sahte KIRMIZI yakmiyor · izlenen kaynak taraniyor · izlenmeyen-ama-yoksayilmayan yeni
    # kaynak yakalaniyor · beyanli uretilen kok taraniyor · kume olculemezse OLCULEMEDI).
    # argparse'ta sys.exit(kendini_test()) ile ERKEN DONER: TEST 1'in OpenSCAD render'ina ve
    # build.py cagrisina HIC girmez. 8 testlik TAM suite CI'ya BAGLANMADI (openscad ister).
    "jenerator/test/kalibrasyon-referans-uret.py": (
        R_URETEC + " Somut: kalibrasyon-referans.json fiksturunu YAZAR — CI'da kosarsa "
        "kabul testlerinin karsilastirdigi referansi EZER (test kendi kendini onaylardi)."),
    # 🔴 "jenerator/test/kalibrasyon-senkron.js" MUAFIYETI KALDIRILDI (3 Agu 2026).
    # Eski gerekcenin IKI dayanagi da OLCULEREK CURUDU:
    #   (1) "o kalan kol bile TEMIZ checkout'ta 25,2 s surdu" -> olculen 1,3 s.
    #       25,2 s FIGURU kardes-ev katmanini DA iceren TAM kosumun suresiydi;
    #       kardes ev yokken (yani CI'daki halinde) kol 1,3 s'de bitiyordu. Yeni
    #       3. katmanla birlikte bile 3,5 s (39 iddia) — build job'unda 100 s'lik
    #       adimlarin yaninda pahali aday DEGIL.
    #   (2) "cekirdek iddia kardes ev olmadan olculemez" DOGRUYDU ve TAM DA BU
    #       YUZDEN muafiyet bir PARA deligiydi: `yay` ailesine konan +%5 TAHSILAT
    #       mutanti kardes ev VARKEN 26 kontrolu kirmizi yakiyor, kardes ev YOKKEN
    #       TAM YESIL geciyordu; ayni mutant `build` + `serit-b` islerinin 134
    #       kosulabilir adiminin HICBIRINDE ayirt edici kirmizi yakmadi (olculdu
    #       3 Agu; tek rc degisimi jenerator/test/yay-tarama.py --kendini-test'te
    #       ve o adim KONTROL mutantinda -yalniz yorum satiri- da kirmizi yandigi
    #       icin AYIRT EDICI DEGIL, ustelik serit B'de yayini durdurmuyor).
    # COZUM susturma degil KAPSAM DARALTMA oldu: 3. katman (dondurulmus kalibrasyon
    # kaynagi, jenerator/test/kaynak-referans.json) dis kaynak ISTEMEDEN kosar ve
    # ayni hukmu verir. Kapi artik `build` job'unda BLOKLAYICI (`deploy: needs:
    # build`), mutasyon turu serit-b'de.
    "jenerator/test/kaynak-referans-uret.js": (
        R_URETEC + " Somut: jenerator/test/kaynak-referans.json fiksturunu YAZAR "
        "(--yaz) — CI'da kosarsa kalibrasyon senkron kapisinin karsilastirdigi "
        "referansi EZER (test kendi kendini onaylardi). Ayrica girdisi kardes ev "
        "kalibrasyon kaynagidir; CI checkout'unda o dizin YOKTUR (rc 2)."),
    "jenerator/test/stl_hacim.py": (
        R_URETEC + " Somut: 'kullanim: stl_hacim.py <dosya.stl>' — tek dosya olcen CLI."),
    "jenerator/test/vida-referans-uret.py": (
        R_URETEC + " Somut: vida referans fiksturunu ureten arac; ayrica OPENSCAD ister "
        "(CI'da yok, yerel Mac'te SIGABRT)."),
    # "jenerator/test/vitrin-kabul.js" MUAFIYETI KALDIRILDI (30 Tem) — gerekce OLCULEREK
    # YANLIS bulundu. R_AYRI'nin "jenerator kendi harness'i" dali bu dosya icin gecersiz:
    # test jenerator'u DEGIL ANA SAYFAYI (index.html inline scripti) sinar — gizli kategori,
    # sari kart fiyati, banner gorunum kurali, edge uc sozlesmesi. Kardesi
    # jenerator/test/metin-beyaz-liste.mjs de deploy.yml'de zaten kosuyor. Gercek sebep:
    # EDGE_KATALOG=true olunca testin sahte fetch'i ozet.json / Worker cevabini `ok`/`status`
    # ile taklit etmiyordu -> "HTTP undefined" ile ALTYAPI HATASI (7 testten 6'si hic
    # kosmuyordu). Bagimlilik testin ICINDE kurulur oldu (build.py --sadece-ozet + sunucusuz
    # tasima taklidi); Node 20.20.2 ve 25.x'te 9/0 -> test artik deploy.yml'de KOSUYOR.
    # --- tools/ JS ---
    # 🔴 DORT R_NODE MUAFIYETI KALDIRILDI (30 Tem): attribution-ref-test.js (LISANS ATIFI),
    # marka-limit-test.js, riza-tikkimligi-test.js (GIZLILIK/riza), url-senkron-test.js.
    # Gerekce "CI'da setup-node yok" idi; deploy.yml:33 actions/setup-node@v4 BLOKLAYICI
    # on-kosul olarak duruyor ve o dosyada zaten bes node testi kosuyor. Dorduyle de
    # mutasyon olcumu yapildi (hedef kaynagi bozunca rc=1) -> hazir ve calisir olduklari
    # icin deploy.yml'e bloklayici adim olarak baglandilar. Bkz. yukarida R_NODE notu.
    "tools/parite-test.js": R_AG,
    # --- parite karar-cekirdegi harness'leri (27 Tem): AGSIZ + yerelde YESIL ---
    # 🔴 31 TEM: bu kumenin IKISI (parite-sozlesme-test.py 0,19 s · parite-fikstur-test.js
    # 6,5 s / 226 iddia) muafiyetten CIKARILDI ve deploy.yml'de BLOKLAYICI kosuyor.
    # Gerekceleri "deploy.yml'e 0-hunk sarti" idi — SURECSEL, o tur bitince curudu; 27 Tem
    # notunun kendisi zaten "sonraki turda eklenmeli, onerilen sira ..." diyordu ve o sira
    # bu turda uygulandi. Ucuncusu (mutasyon harness'i) SURE ile duruyor:
    # --- marka katlama sinifi kapsam kapisi (10 Agu 2026) ---
    # 🔴 GEREKCE SURECSEL DEGIL, OLCULDU: kapi iki korpusu da URETIR; ege korpus ureteci
    # bot'un `nrm` fonksiyonunu ister ve bot AYRI bir checkout'tur
    # (/Users/okan/dev/pruvo-bot/worker/src/index.js). CI fresh checkout'unda o depo
    # YOKTUR -> kapi fail-closed olarak rc=3 (OLCULEMEDI) verir; bloklayici adim olarak
    # baglanirsa serit-a3 YAPISAL olarak kirmizi yanar ve TUM yayini durdurur
    # (mimar-kapi-6ev-test.py / kaynak-referans-uret.js ile AYNI sinif).
    # NOT (mimara): site ekseni bot ISTEMEZ. Kapi ege eksenini ayirip yalniz site
    # ekseniyle CI'ya baglanabilir; bu KAPSAM DARALTMA karari MIMARINDIR, burada
    # tek tarafli alinmadi.
    "tools/parite-kapsam-test.js": (
        R_YOL + " Somut: kapi tools/parite-ege.js korpusunu uretir, o da bot deposunun "
        "(~/dev/pruvo-bot, AYRI checkout) `nrm` fonksiyonunu ister; CI'da o dizin YOK -> "
        "fail-closed rc=3 (OLCULEMEDI). Site ekseni bot istemez; ayrilirsa CI'ya "
        "baglanabilir (mimar karari)."),
    "tools/parite-kapsam-mutasyon.js": (
        R_YAVAS + " Somut: 15 mutant x kapi kosumu; her mutant icin AYRI gecici agac "
        "kurulur. Ayrica kapinin KENDISI CI'da rc=3 verdigi icin (bkz. "
        "tools/parite-kapsam-test.js girisi) nobet CI'da AYIRT EDICI olcum yapamaz: "
        "oldurucu ile kontrol mutanti ayni isareti verirdi."),
    "tools/parite-mutasyon-test.js": (
        R_YAVAS + " OLCULDU (31 Tem, temiz checkout): 14 mutant x fikstur kosumu = "
        "217,1 s — tek build job'unu blokar (M14 asilma nobeti tek basina ~120 s). "
        "Kardesleri (parite-sozlesme + parite-fikstur) artik CI'da kosuyor; bu dosya "
        "izole/ayri bir job'a alinmadan Pages hattina EKLENMEZ."),
    # --- tools/ python: mimar-disiplin ---
    # (KraL-KapiSupurmesi-29Agu: mimar-kilit/commit/kapi-mutasyon/6ev/kod-kilidi/
    # agent-kapisi test muafiyetleri kaldirildi — dosyalar BaBa 28 Agu filo
    # karariyla silindi.)
    "tools/kapi-envanteri-test.py": R_YOL,
    # --- tools/ NOBETCILER (*-kapisi.py) — kesif 21 Tem genisletildi, CI'da kosmayanlar ---
    "tools/komut-stili-kapisi.py": R_HOOK,
    # (KraL-KapiSupurmesi-29Agu: mimar-icra-kapisi ve mimar-commit-kapisi
    # muafiyetleri kaldirildi — kapilar silindi.)
    # "tools/denetim-kapisi.py" MUAFIYETI KALDIRILDI (31 Tem, madde 32) — R_GIZLI gerekcesi
    # (shop/test/kabul.js vakasinin AYNISI) YARI DOGRUYDU ve tam da bu yuzden tehlikeliydi:
    #  (a) "parti CI'da BOS kalir -> anlamsiz YESIL" kismi OLCULEREK DOGRULANDI (git archive
    #      HEAD ile kurulan temiz checkout'ta bayraksiz kol rc=0, tum sayaclar 0). Bu yuzden
    #      bayraksiz kol CI'ya BAGLANMADI.
    #  (b) ".urun-kaynaklari.json YOK -> kapi olcemez" kismi YANLIS: cikis kodu YALNIZ
    #      `ihlal` kumesinden turer (kaynak: main()'in son satiri), lisans ekseni auto_sil'e
    #      gider ve cikisi HIC etkilemez. Gizli kayitli/kayitsiz --tum-katalog olcumu
    #      BIREBIR ayni: IHLAL 332/332 (auto_sil 2182 -> 17850 kayiyor ama bloklamaz).
    # COZUM (susturma DEGIL, AYIRMA): `--commit-farki` kolu eklendi — parti = HEAD^ -> HEAD
    # arasinda eklenen/DEGISEN id'ler; yalniz BU ITMENIN GETIRDIGI ihlal bloklar (ayni
    # (id,kapi,gerekce) HEAD^'te de varsa rapor edilir, bloklamaz). Fail-closed: HEAD/HEAD^
    # okunamazsa OLCULEMEDI rc 3. deploy.yml'de continue-on-error'SUZ kosuyor + kendi
    # `--kendini-test`i (15 iddia, 2 mutasyon) de bloklayici.

    "tools/kategori-kapisi.py": R_TASARIM,
    "tools/gitignore-kapisi.py": R_YEREL_HIJYEN,
    "tools/regresyon-kapisi.py": (
        R_YOL + " Ek olarak varsayilan suite'i node tools/parite-test.js + parite-ege.js icerir; "
        "bunlar CANLI CDN/D1'e 1200 istek atar -> CI'da deterministik degil (R_AG). "
        "🔴 DUZELTME (30 Tem): bu gerekce eskiden 'CI'da node YOK' da diyordu — OLCUMLE "
        "YANLIS (deploy.yml'de setup-node bloklayici on-kosul); engel AG ekseni ve mutlak "
        "yol, node DEGIL. Ayrica kapsadigi testler zaten tek tek bu listede muhasebeli -> "
        "CI'da kosmasi cift-sayim olurdu."),
    # --- tools/ python: yavas/harici (>30s) ---
    "tools/feed-cache-bust-test.py": (
        R_YAVAS + " OLCULDU: test build.py'yi 2 KEZ kosuyor. ⚠️ SAYI TAZELENDI (31 Tem, "
        "temiz checkout): toplam 25,4 s — eski kayittaki 227,9 s BAYATTI (F2 raporu, "
        "108 s'lik build ile). 25 s hala tek build job'una eklenen en pahali ucuncu "
        "kalem ve kendisi deploy'un ZATEN kosturdugu build.py'nin ciktisini yeniden "
        "uretir. CI'YA ALINMA KOSULU degismedi: alt-surec yerine render_merchant_feed "
        "import edilip 2 kez cagrilirsa sure saniyeye iner ve bloklayici eklenebilir."),
    "tools/kaynak-akis-test.py": (
        R_YAVAS + " OLCULDU (31 Tem, temiz checkout): 86,9 s. "
        "🔴 GEREKCE DUZELTILDI: yalniz YAVAS degil — ayni kosumda rc=1 verdi. Iddialari "
        "depo DISINDAKI ~/.claude/skills agacina bakiyor (\"x myminifactory.md mevcut\", "
        "\"x cgt.md emekli notu\"); CI fresh checkout'unda o agac YOKTUR -> bloklayici "
        "eklenirse YAPISAL KIRMIZI (R_YOL sinifi, yedekle-test.py emsali)."),
    # "tools/test-bbox-3mf.py" MUAFIYETI KALDIRILDI (30 Tem) — gerekce R_YAVAS (">30 s")
    # idi; OLCULEN 0,1 s'lik bir COKUSTU. Test ankraj olarak GERCEK urun dosyalarini
    # (stl/pr1173083.3mf, stl/pr912419.3mf) aciyordu, ama stl/ gitignore'da: dosyalar ne
    # bu makinede ne CI'da var -> FileNotFoundError, HICBIR iddia kosmuyordu. Ankraj
    # depoya alindi (tools/fikstur/3mf/, ~3 KB; uretici tools/fikstur/3mf-fikstur-uret.py
    # ALT DIZINDE, yani kesif predikatina girmez ve CI'da kosup fiksturu EZEMEZ), mutlak
    # /Users/okan/... yolu betigin kendi konumundan turetilir oldu, stl/ yoksa regresyon
    # bolumu ACIKCA "ATLANDI" der. 0,06 s, agsiz -> deploy.yml'de BLOKLAYICI kosuyor.
    # --- tools/ python: fts5-trigram sqlite gerektiren (CI ubuntu'da yok) ---
    "tools/taban-fiyat-d1-test.py": R_FTS5,
    # --- tools/ python: eski "offline-yesil, sonraki turda alinabilir" (R_SONRA) kumesi ---
    # 🔴 31 TEM: bu kumede 24 giris MUAFIYETTEN CIKARILDI ve deploy.yml'de
    # continue-on-error'SUZ BLOKLAYICI adim olarak kosuyor (d1-sync-durum · derin-cap ·
    # durum-edge · durum · gorsel-anahtar · kaynak-entegrasyon · lisans-havuz ·
    # makerworld-ara · makerworld-lisans · marka-filtre · meta-piksel · olculmemis-siparis ·
    # printables-lisans · siparisler · stl-bbox-binary · surum · test-baski-senkron ·
    # test-merchant-feed · thing-codex · thingiverse-gallery · yargi-firearm · yazdir ·
    # parite-sozlesme · parite-fikstur). Yordam: (1) TEMIZ CI-benzeri checkout'ta kosum
    # (hepsi rc=0, toplam ~17 s), (2) CANLILIK mutasyonu — her testin ACTIGI kaynak
    # dosyada satir silme / hedefli bozma; hicbiri "iddiasiz" cikmadi, (3) YANLIS-POZITIF
    # nobeti: son 25 gercek commit'te tam kosum. Asagida KALAN ucu SOMUT engelle durur.
    "tools/denetim-kapisi-test.py": (
        "Olcum girdisi denetim-kapisi.py'nin MUTLAK /Users/okan/dev/pruvo yoluna ve "
        "working-tree'deki stage'lenmis PARTI farkina bagli (R_YOL/R_GIZLI sinifi): CI "
        "fresh checkout'unda parti BOStur, kapinin bayraksiz kolu anlamsiz YESIL yakar. "
        "Denetim kapisinin CI'da olculen kolu `--commit-farki` + `--kendini-test`'tir ve "
        "deploy.yml'de BLOKLAYICI kosuyor (bkz. yukarida tools/denetim-kapisi.py notu)."),
    "tools/gorsel-kapisi-test.py": (
        "Mutlak /Users/okan/dev/pruvo yoluna VE gitignore'lu yerel gorsel/onbellek "
        "girdisine bagli (R_YOL sinifi) -> CI fresh checkout'unda yapisal olarak olcum "
        "yapamaz. Gorsel ekseninin CI'da kosan nobetcisi tools/gorsel-boyut-test.py'dir "
        "(deploy.yml'de bloklayici)."),
    "tools/thing-hazirla-bbox-test.py": (
        "thing-hazirla.py import aninda hardcoded ROOT=/Users/okan/dev/pruvo altindan .thingiverse-token "
        "okur -> CI fresh-checkout'ta import PATLAR (yapisal CI-kirmizi, R_YOL sinifi). bbox() "
        "BELIRSIZ-BIRIM birim testi (metre-sezgisi 2. kopyasi, stl-bbox testi bu ayri fonksiyonu "
        "kapsamaz); sentetik/offline/<1s, yerelde YESIL. test-bbox-3mf emsali: deploy.yml'e kor-eklenmedi."),
    # NOT: tools/durum-yedek-test.py 27 Tem'de MUAFIYETTEN CIKARILDI -> deploy.yml'de
    # bloklayici adim olarak kosuyor. Olcum: CI taklidinde (bos HOME, Drive yok, sadece
    # takip edilen dosyalar) YESIL (cikis 0). "Hermetik" DEGIL: ortam eksenleri
    # (`ps`/`git`/kaynak kumesi) sorgulandigi icin bir kismi ⚪ OLCULEMEDI olur ve
    # kontrol SAYISI makineye gore degisir. Kontrol SAYISI buraya YAZILMAZ —
    # sayi betigin KENDI ciktisindadir; sabit sayi bir VERI CAPASIDIR ve her yeni
    # nobetci eklendiginde sessizce bayatlar (olculdu: yorumdaki "88/88" gerceginde
    # 89'du, "89/89 ~2 s" ise 4,6 s). Buraya GERI EKLEME: iki yerde birden sayilirsa
    # bu kapi "hem kosuluyor hem muaf" celiskisini yakalar.
    "tools/yedek-hook-test.py": (
        R_YOL + " Somut olarak: .git/hooks/pre-push commit EDILMEZ (per-makine) -> CI "
        "fresh checkout'unda kurulu blok YOKTUR, 'olu konum' nobetcisi orada yapisal "
        "olarak kirmizi yanar. Yerel push disiplini araci; deploy CI adimi degil."),
    # 🔴 NOT: tools/yedekle-test.py 7 AGU 2026'da MUAFIYETTEN CIKARILDI — deploy.yml
    # `serit-a4`te `--hermetik` koluyla BLOKLAYICI kosuyor (continue-on-error YOK) ve
    # o kol BOLUM B'de dosyanin KENDI beyaniyla ("<etiket>: <bayrak>") kilitli, yani
    # adim silinirse bu kapi KIRMIZI yanar. BURAYA GERI EKLEME: "hem kosuluyor hem
    # muaf" celiskisini bu kapinin BAYAT-IZIN kolu zaten yakalar.
    # TAM BATARYA (bayraksiz kol) BILEREK BAGLANMADI — OLCULDU (temiz `git clone`,
    # BOS HOME, kardes ev YOK, Drive YOK): `python3 tools/yedekle-test.py` -> rc=1,
    # "TOPLAM 220 kontrol, 6 kirmizi", COKME YOK, 6,1 s. Alti da ORTAM KAYNAKLI:
    # HOME/.claude/skills YOK (3 kontrol) + gitignore'lu kok dosyalari YOK
    # ('.urun-kaynaklari.json', 'AGENTS.md', 'DEVAM-ARSIV.md' -> 3 kontrol). Ayrica
    # 13/13e/14 flock + paralel kosum + 2000 orneklik zamanlama olcer (paylasilan
    # kosucuda FLAKE), 15 GERCEK Drive damgasina bakar. Gerekce ve tam kirmizi dokumu
    # deploy.yml'deki adim yorumundadir.
    "tools/yayin-kapisi-mutasyon-test.py": (
        "GIT GECMISI GEREKTIRIR -> sig checkout'ta YAPISAL CI-KIRMIZI (R_YOL/R_FTS5 "
        "sinifi). A kolu 'onarim ONCESI surum' ile 'yeni surum'u AYNI fiksturle kosar "
        "ve bunun icin `git show <onarim-oncesi-sha>:tools/yayin-kapisi.py` ister. "
        "OLCULDU (7 Agu 2026, `git clone --depth 1` ile kurulan CI-benzeri klon): "
        "commit sayisi 1, `git cat-file -e db836975` -> ERISILEMEZ, surucu "
        "'OLCULEMEDI: git show basarisiz' basip rc=1 verir. B kolu (mutasyon bataryasi) "
        "gecmis ISTEMEZ ve ayni klonda 12/12 ayirt edici mutant + kontrol mutanti "
        "YESIL verir; yani muafiyet yalniz A kolunun gecmis bagimliligindan dogar. "
        "OLCULEN NOBET YERI: kapinin KENDI kabul testi (tools/yayin-kapisi.py "
        "--kendini-test, ayni klonda 105 iddia / rc=0) nobet.yml:552'de OTOMATIK "
        "kosuyor -> kapi kapsamsiz DEGIL; bu dosya onun uzerine 'eski davranis "
        "curutuldu mu' arkeoloji kolunu ekler."),

    # ═══ MUTASYON SURUCULERI — KESIF GENISLEMESIYLE GELEN 33 DOSYA (8 Agu 2026) ═══
    # 🔴 BU BLOK BIR "TOPLU MUAFIYET" DEGILDIR. Kesif genislemesi 33 dosya getirdi;
    # 17'si nobet.yml `serit-b`de KENDI DUZ TEK KOMUT ADIMIYLA kosuyor (muafiyet YOK,
    # ratchet VAR), 2'si zaten kosuyordu (varlik-mutasyon deploy.yml · yayin-sinyali
    # nobet.yml — artik ratchet'li), 15'i asagida TEK TEK ve OLCUMLE muaf.
    # OLCUM YORDAMI (hepsi icin AYNI, 8 Agu 2026): `git clone --local` ile kurulan
    # TEMIZ checkout + BOS HOME (~/.claude YOK) -> `<yorumlayici> <yol>`; rc, duvar
    # saati suresi ve son rapor satiri kaydedildi. 300 s'de kesildi.
    # KABLOLAMA ESIGI (KraL olcutu): rc=0 VE sure <= 40 s VE calisma agacini
    # KIRLETMIYOR. Esigin gerekcesi olculdu: kablolanan 17 adim `serit-b`ye toplam
    # ~186 s katiyor; asagidaki 15 dosya kablolansaydi ek yuk ~2.400 s+ olurdu ve
    # `serit-b` bugunku 752 s'lik suresinin dort katina cikardi.
    # 🔴 UC DOSYA ZATEN CURUMUS HALDE BULUNDU (rc=1) — bu, kesif genislemesinin
    # NEDENININ kanitidir: kosmayan surucu sessizce bayatlar. Onarim AYRI IS.
    "tools/d1-sapma-mutasyon.py": (
        "BAYAT SURUCU — CI'YA BAGLANAMAZ (rc=1). OLCULDU (8 Agu 2026, temiz klon + bos "
        "HOME): rc=1, 19,9 s; rapor `Aranan: \"if: failure() && steps.olcum.outputs."
        "sapma == 'var'\"` diyor -> mutasyon CAPASI is akisi metninde ARTIK YOK, yani "
        "mutant UYGULANAMIYOR. Bu bir kapi kirmizisi DEGIL, aracin kendi bayatligidir; "
        "bloklamayan seride baglanirsa `serit-b` KALICI kirmizi yanar ve gercek "
        "alarmlari bogar ([[alarm-onarim-ucus-suresi]]). ONARIM AYRI IS: capa "
        "d1-sapma-alarmi.yml'in cari metninden yeniden turetilmeli."),
    "tools/gecmis-geri-donus-mutasyon.py": (
        "BAYAT SURUCU + SURE. OLCULDU (8 Agu 2026, temiz klon + bos HOME): rc=1, "
        "88,5 s; aracin KENDI raporu `M12 KANCA exit 1 -> exit 0 (fail-open) -> CAPA "
        "BULUNAMADI (mutasyon uygulanamadi — arac bayat)` diyor. Iki gerekce birden: "
        "(a) bugun kirmizi -> kablolanirsa `serit-b` KALICI kirmizi olur, (b) 88,5 s "
        "ile 40 s esiginin ustunde. Olctugu eksenin CI kolu ZATEN var ve kosuyor: "
        "`tools/gecmis-geri-donus-kapisi.py --kendini-test` nobet.yml `mesaj-nobeti` "
        "job'unda. ONARIM AYRI IS."),
    "tools/r2-onek-mutasyon.py": (
        "BAYAT SURUCU — CI'YA BAGLANAMAZ (rc=1). OLCULDU (8 Agu 2026, temiz klon + bos "
        "HOME): rc=1, 3,4 s, `AssertionError: MUTASYON UYGULANAMADI (M15) — kaynak "
        "degisti mi?`. Capa kaynaktan kaymis; surucu kendi fail-loud koluyla duruyor "
        "(dogru davranis) ama bu HAL kablolanamaz. Olctugu kapi CI'da ZATEN kosuyor: "
        "`tools/r2-onek-gelenek-kapisi.py` nobet.yml `r2-onek-nobeti` job'unda. "
        "ONARIM AYRI IS: M15 capasi r2_anahtar.py'nin cari metninden yeniden turetilmeli."),
    # --- SURE ESIGI (>40 s) — hepsi rc=0, yani SAGLAM; yalniz PAHALI --------------
    "tools/commit-mesaji-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 233,9 s, `oldurucu mutant 28/28 "
        "OLDU · ilgisiz kontrol 3/3 YESIL`. Her mutant GERCEK bir git deposu kurup "
        "commit ürettiği icin sure mutant sayisiyla dogrusal buyur. 40 s esiginin ~6 "
        "kati; TEK BASINA `serit-b`yi %31 uzatirdi. Olctugu kapinin CI kolu ZATEN "
        "kosuyor: `tools/commit-mesaji-kapisi.py --kendini-test` nobet.yml "
        "`mesaj-nobeti` job'unda (SERIT_B'de beyanli)."),
    "tools/cron-teslim-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 177,3 s, `CURUTME GECTI — her "
        "oldurucu mutant KIRMIZI yandi, beyanli mutantlarin kirmizi eksen kumesi "
        "beyana TAM ESIT`. 40 s esiginin ~4,4 kati. Olctugu eksenin CI kolu ZATEN "
        "kosuyor: `tools/cron-nabiz-kapisi.py --kendini-test` nobet.yml `cron-nabzi` "
        "job'unda."),
    "tools/d1-kaynak-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 163,3 s, `7 mutant: her "
        "OLDURUCU beyan ettigi kodlari yakti, her KONTROL tabani degistirmedi`. "
        "40 s esiginin ~4 kati (mutant basina ~23 s: her mutant tam bir d1-sync "
        "kaynak turetimi kosar). Olctugu kapinin CI kolu `serit-b`de "
        "`tools/d1-sync-tani-test.py` ile duruyor."),
    "tools/iletisim-baglam-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 80,1 s, `SONUC: GECTI`. "
        "40 s esiginin 2 kati. Sinifi SAGLAM (rc=0) — muafiyet YALNIZ suredendir; "
        "esik degisirse ya da surucu hizlandirilirsa BURADAN CIKARILIP nobet.yml "
        "`serit-b`ye kendi adimiyla baglanmalidir."),
    "tools/ilan-tutari-mutasyon.py": (
        "SURE. OLCULDU (12 Agu 2026, dal calisma agaci): rc=0, 259,9 s, `OK: mutantlarin "
        "hepsi beklenen rengi VE izini verdi; canli agac EL DEGMEMIS` (7 OLDURUCU + 1 "
        "KONTROL). 40 s esiginin ~6,5 kati: her mutant, olctugu kapinin TAM KAPSAM "
        "eksenini kosar ve 25.968 urun sayfasinin HEPSINI yeniden uretir (~32 s/mutant) "
        "— spec 'ORNEKLEME YOK' dedigi icin kapsam DARALTILAMAZ. Sinifi SAGLAM (rc=0) ve "
        "calisma agacini KIRLETMEZ (mutasyon KOPYAYA uygulanir, sha256 bas=son + artik "
        "yedek=0 KOSARAK dogrulanir). Olctugu kapinin CI kolu ZATEN BLOKLAYICI kosuyor: "
        "deploy.yml `Ilan edilen tutar kapisi`."),
    "tools/marka-arama-mutasyon.py": (
        "SURE — OLCULEMEYECEK KADAR UZUN. OLCULDU (8 Agu 2026, temiz klon): 300 s "
        "duvar saatinde KESILDI (TIMEOUT), o ana kadar rapor satiri URETMEDI. Ust "
        "sinir bilinmiyor; 40 s esiginin en az 7,5 kati. Kablolanirsa `serit-b`nin "
        "suresini TEK BASINA en az %40 uzatir ve tavani belirsizlestirir."),
    "tools/marka-invaryant-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 283,8 s, `19 mutant: her "
        "OLDURUCU kirmizi, her KONTROL yesil`. 40 s esiginin ~7 kati; mutant basina "
        "~15 s (her mutant tum marka envanterini yeniden turetir)."),
    "tools/marka-sayac-mutasyon.py": (
        "SURE + CALISMA AGACINI KIRLETIYOR (iki bagimsiz gerekce). OLCULDU (8 Agu "
        "2026, temiz klon): 300 s'de KESILDI (TIMEOUT) VE kosum sonunda "
        "`git status --porcelain` -> ` M tools/marka_model_build.py`, yani surucu "
        "IZLENEN bir kaynagi degistirip GERI YUKLEMEDI. Ikinci eksen tek basina "
        "bloklayicidir: CI'da kosan bir adimin izlenen dosyayi kirletmesi sonraki "
        "adimlarin girdisini sessizce degistirir. ONARIM (mutasyon KOPYAYA uygulansin "
        "+ sha256 bas=son nobeti) AYRI IS."),
    "tools/marka-uyelik-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 202,1 s, `BATARYA: GECTI "
        "(6 mutant)`. 40 s esiginin ~5 kati; mutant basina ~34 s."),
    "tools/model-kanon-mutasyon.py": (
        "SURE — OLCULEMEYECEK KADAR UZUN. OLCULDU (8 Agu 2026, temiz klon): 300 s "
        "duvar saatinde KESILDI (TIMEOUT), rapor satiri URETMEDI. marka-arama ile "
        "AYNI sinif; ust sinir bilinmiyor."),
    "tools/urunler-guard-provenans-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 78,0 s, `MUTANT=22 "
        "TABAN_IDDIA=28 SAPMA=0`. 40 s esiginin ~2 kati. Her mutant gercek bir git "
        "deposu + guard kancasi kurar. Olctugu eksenin sahibi urun VERISI duzlemidir "
        "(MaCiT); bloklamayan seritte bile kirmizisinin sahibi bu ev degildir."),
    "tools/yayin-gecikme-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 193,8 s, `TUM MUTANTLAR "
        "BEYANINA UYDU, KONTROLLER YESIL, HER EKSENIN TEK-KIRMIZI MUTANTI VAR`. "
        "40 s esiginin ~4,8 kati. Olctugu nobetcinin kabul testi ZATEN `serit-b`de "
        "kosuyor: `tools/yayin-gecikme-test.py`."),
    "tools/yonet-cerez-mutasyon.py": (
        "SURE. OLCULDU (8 Agu 2026, temiz klon): rc=0, 54,8 s, `TUM MUTANTLAR "
        "YAKALANDI, KONTROLLER YESIL`. 40 s esiginin ~1,4 kati — ESIGE EN YAKIN "
        "GIRIS. Surucu ~10 s hizlandirilirsa esigi gecer; o zaman BURADAN CIKARILIP "
        "nobet.yml `serit-b`ye kendi adimiyla baglanmalidir."),
    # "tools/sahiplik-kapisi.py" muafiyeti KALDIRILDI (18 Agu, Paket ③-d §4) — kapi
    # artik nobet.yml SERIT B adimi olarak OTOMATIK kosar; muafiyet anlamsiz ve
    # yanlis yon olurdu (kosulmuyor muamelesi). Izin listesi bos YOK (eger referans
    # gerekirse R_SAHIPLIK yorumu yukarida).
    "tools/nobet-dagitilmaz-sebep-test.py": (
        "URETIM KAYNAGI CI'DA YOK: ~/.claude/cron/nobet-kapi.py repoya dahil degil; "
        "test Okan makinesinde canli cron karsisinda kosar."),
    # (KraL-KapiSupurmesi-29Agu: nobet-gorev-jeton-kapisi muafiyeti kaldirildi —
    # kapi silindi.)
}


# ---- ALT KUME MUAFIYETLERI (BOLUM B) ---------------------------------------
# 🔴 BILINEN SINIR — KACAMAKSIZ:
#   BEYAN EDILMEYEN yeni bir alt kume bu kapiya GORUNMEZ. Bu bir DISIPLIN CIHAZIDIR,
#   KAFES DEGIL ([[kapi-disiplin-ilkesi]]). Duz (beyansiz, genel) bayrak kapsami
#   OLCULDU ve CURUDU: 160 dosya kesfediliyor, 124'u kosuyor; 126 (dosya,bayrak) cifti
#   hicbir OTOMATIK is akisinda kosmuyor ve bunlarin ezici cogunlugu MODIFIKATORDUR
#   (girdi/kip/cikti secer, AYRI bir iddia kumesi DEGIL). Duz bayrak kapsami boylece
#   sinyal/gurultu ~1:115 olur ve her yeni modifikator bayrak TUM ekibin yayinini
#   kirmiziya cevirirdi ([[kapi-kapsam-eksen-secimi]] · [[kapi-kapsam-genisletme-tuzagi]]).
#   Yeni A-sinifi adaylar BOLUM C UYARI KATMANIYLA her kosumda yuzeye cikar; bloklama
#   bedeli sifirdir.
#
# ANAHTAR: (repo_goreli_yol, bayrak) · DEGER: OLCULMUS gerekce (bos = exit 1).
# CURUME: yol kesfedilmiyorsa · bayrak jetonu dosya metninde yoksa · alt kume ARTIK
# OTOMATIK is akisinda kosuyorsa -> exit 1 (giris listeden CIKARILMALI).
A_MUTASYON = (
    "META OZ-DOGRULAMA KOLU — kabul testi DEGIL: kapinin KENDI iddiasinin canli "
    "oldugunu mutantla kanitlar, yani olctugu sey zaten deploy.yml'de BLOKLAYICI kosan "
    "kapinin ta kendisidir (CI'ya baglamak CIFT SAYIM olur). OLCULDU (2 Agu, bu makine, "
    "11 kolun tamami): hepsi rc=0, TOPLAM 64,9 s, calisma agaci kirlenmiyor "
    "(`git status --porcelain` ONCE == SONRA). CI'YA ALINMA BEDELI: tek build job'una "
    "+64,9 s — feed-cache-bust (25,4 s) muafiyetinin ~2,6 kati. CI'YA ALINMA KOSULU: "
    "mutasyon kollari AYRI/paralel bir job'a alinirsa bloklayici baglanabilir.")
A_ESLEM_PAKET = (
    "Gitignore'lu R2 veri paketine bagli: `onizleme/derleyici/eslem-ozel.json` PUBLIC "
    "repoda YOKTUR (gizli pakette gelir). OLCULDU (2 Agu, bu checkout): rc=1, 0,1 s, "
    "\"eslem-ozel.json yok ... (gitignore'lu — R2'deki paketten gelir)\". Taze CI "
    "checkout'unda YAPISAL olarak kosamaz; bloklayici eklenirse tum yayini durdurur "
    "(R_YOL/R_GIZLI sinifi). Bu dosyanin AGSIZ/paketsiz `--kendini-test` kolu "
    "deploy.yml'de ZATEN bloklayici kosuyor.")

ALT_KUME_IZIN_LISTESI = {
    # --- 11 x meta oz-dogrulama (mutasyon harness'i) -------------------------
    ("tools/altkategori-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 11,4 s, \"17/17 beklenti TUTTU\".",
    ("tools/altkategori-yuzey-test.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 4,7 s, \"8/8 beklenti TUTTU\".",
    ("tools/cayma-beyani-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 0,6 s, \"sinif karari kaldirilinca kapi KIRMIZI\".",
    ("tools/devam-sinif-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 26,7 s (kumenin EN PAHALI kalemi), 15 mutant · 0 hata.",
    ("tools/edge-kart-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 0,2 s, \"3/3 mutant KIRMIZI (iddia CANLI)\".",
    ("tools/fiziksel-urun-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 0,3 s, \"kosul kaldirilinca kapi KIRMIZI\".",
    ("tools/gorselsiz-render-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 0,3 s, \"MUTASYON: 7/7 oldu\".",
    ("tools/stok-d1-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 1,9 s, \"13/13 (11 oldurucu KIRMIZI + 2 ilgisiz YESIL)\".",
    ("tools/ticari-hal-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 13,3 s, \"ONCE-KIRMIZI: 1/1\".",
    ("tools/uyum-kapisi.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 2,8 s, \"13/13 beklenti TUTTU\".",
    ("tools/yedek-hook-test.py", "--mutasyon"):
        A_MUTASYON + " Somut: rc=0, 2,7 s, \"2/2 beklendigi gibi\".",
    # --- gizli/uzak girdi isteyenler ----------------------------------------
    ("onizleme/test/eslem-olcum.py", "--hepsi"): A_ESLEM_PAKET,
    ("onizleme/test/eslem-olcum.py", "--metin-testi"): A_ESLEM_PAKET,
    ("onizleme/test/eslem-olcum.py", "--tohumlar"): A_ESLEM_PAKET,
    ("shop/test/kabul.js", "--sandbox"): (
        "GERCEK iyzico SANDBOX ucuna vurur ve `shop/.dev.vars` icindeki GERCEK sandbox "
        "anahtarlarini ister (dosyanin kendi basligi: \"4 (<bayrak>): gercek sandbox. "
        "Script odeme sayfasi URL'ini basar\"). Sir CI'da tanimli DEGIL ve tanimli olsa "
        "bile uctan uca odeme cagrisi AG'a bagli -> non-deterministik: tek gecici 5xx "
        "TUM ekibin yayinini durdurur (R_AG sinifi). PARA ekseni oldugu icin "
        "susturulmuyor, YERELDE ve merge kapisinda kosulmaya devam ediyor."),
    ("tools/olculmemis-siparis-test.py", "--canli"): (
        "CANLI D1/uca vurur -> non-deterministik (R_AG sinifi: gecici DNS/429 tum ekibin "
        "yayinini durdurur). OLCULDU (2 Agu): rc=0, 7,5 s, \"29/29 GECTI\" — yani kol "
        "SAGLIKLI, engel dogruluk degil AG BAGIMLILIGI. Ayni dosyanin agsiz kolu "
        "deploy.yml'de ZATEN bloklayici kosuyor."),
    # --- operasyonel alt komut (kabul testi degil) ---------------------------
    ("tools/yayin-kapisi.py", "--geriye-doldur"): (
        "OPERASYONEL ALT KOMUT, kabul testi DEGIL: eksik yayin satirlarini D1'e YAZAR "
        "(yan etkili). OLCULDU (2 Agu): rc=0, 12,9 s, \"Doldurulacak satir yok\". CI'da "
        "her push'ta kosturmak yayin verisine yazan bir bakim isini kor kosturmak olur; "
        "kapinin ASIL kolu (`--kendini-test` + `--yayinla` + `--durum`) deploy.yml'de ve "
        "d1-uzlastirici.yml'de ZATEN kosuyor."),
    ("tools/yayin-kapisi.py", "--hal-json"): (
        "OPERASYONEL DOKUM KOLU, kabul testi DEGIL: makine-okunur durum JSON'u basar ve "
        "HICBIR iddia olcmez. OLCULDU (2 Agu): rc=0, 0,1 s, cikti "
        "'{\"olculdu\": true, \"sebep\": \"\", ...}' — konusu tamamen bozulsa da rc=0 "
        "kalirdi (IDDIA-YOK sinifi, R_URETEC emsali)."),
    # NOT (2 Agu): `("shop/test/kabul.js", "--yonet-cerez")` girisi buradaydi ve
    # "ACIK DELIK" olarak kaydedilmisti. O tespit YANLISTI — dalin tabani (68c92a44)
    # main'in GERISINDEYDI; delik main'de b9facc26 ile ZATEN kapatilmisti (deploy.yml
    # "Yonet anahtar/cerez kabul testi" adimi). Taban tazelenince curume kurali (j)
    # girisi KENDILIGINDEN kirmizi yakti ("BAYAT alt kume izni ... ARTIK OTOMATIK is
    # akisinda KOSUYOR") ve giris SILINDI; alt kume artik KURAL 1 ile kapsaniyor.
    # Ders: [[bayat-worktree-mukerrer-is]] / [[worktree-diff-taban-tuzagi]].
}


def bulgu1_mutasyon_kontrol():
    """BULGU 1 KALICI MUTASYON NOBETCISI (curutucu kanitladi):
    Bir testin 'run: python3 <yol>' ICRA satiri deploy.yml'den silinip ADI yalniz bir
    YORUM/step-name'de kalirsa, kosulan() o testi 'kosuluyor' SAYMAMALIDIR. Eski regex tum
    metni tariyordu -> yalniz-yorum mensiyonu sahte-yesil yapiyordu (olu nobetci CI'dan
    success gecerdi). Bu kontrol GERCEK deploy.yml'den mutant uretir ve uc sarti dogrular:
      + POZITIF: gercek deploy o yolu SAYAR (run: ile gecer).
      + SILME MUTANTI: icra satir(lar)i silinip ad yalniz yorumda kalinca SAYMAZ.
      + YORUM MUTANTI (T7): icra satir(lar)i '# python3 <yol>' yorumuna cevrilince SAYMAZ
        -> yorum-bypass (olculdu: B/C/D/E/F kanaryalari) geri gelirse KIRMIZI yanar.

    NEDEN COK-SATIR CAPASI GEREKTI (olculdu 27 Tem, bu nobetcinin KENDI ariza kaydi):
    mutant uretimi eskiden TEK bir duz metin sabitini ('        run: python3 <hedef>\\n')
    replace(..., 1) ile YALNIZ 1 KEZ siliyordu. deploy.yml'e hedefi ikinci kez kosan bir
    adim ('run: python3 tools/ci-kapsam-test.py --kendini-test') eklenince o satir kosulan()
    capasina UYUYOR (yolun ardindan BOSLUK var -> (?![\\w./-]) negatif ileri-bakisi geciyor),
    ama mutasyon onu GORMUYORDU: mutantta yol HALA 'kosuluyor' sayiliyor ve nobetci
    "BULGU 1 GERI GELDI" + "T7 YORUM-BYPASS GERI GELDI" ile SAHTE-KIRMIZI yaniyordu.
    Yani harness kendi hedefinin cagri sayisina KIRILGANDI. FIX: mutasyon SATIR BAZLI ve
    kosulan() ile AYNI semantikten (_icra_govdesi + _onek_re) turetilir; hedefin TUM icra
    satirlari kapsanir. Ikinci bir eslesme mantigi YAZILMAZ (capa tek kaynak).

    BAYAT-HARNESS KORUMASI (fail-closed): hedefi kosan HIC icra satiri bulunamazsa ya da
    mutasyon sonrasi geriye kosan satir KALIRSA sessizce yesil GECMEZ -> (False, tani).
    (ok, hata_satirlari) dondurur."""
    hedef = HEDEF_BETIK
    if not os.path.exists(KENDI_IS_AKISI):
        return False, ["bu betigin adimlarini tasiyan is akisi bulunamadi: %s"
                       % KENDI_IS_AKISI]
    with open(KENDI_IS_AKISI, encoding="utf-8") as f:
        gercek = f.read()

    icra_idx = _icra_satir_indeksleri(gercek, hedef)
    if not icra_idx:
        return False, ["gercek %s'de %s'yi KOSAN hicbir icra satiri yok "
                       "(cagri bicimi degistiyse ya da adim baska bir is akisina "
                       "tasindiysa KENDI_IS_AKISI sabitini guncelle)"
                       % (os.path.basename(KENDI_IS_AKISI), hedef)]

    mutant, silinen = _silme_mutanti(gercek, hedef)
    yorum_mutant, cevrilen = _yorum_mutanti(gercek, hedef)
    if silinen == 0 or cevrilen == 0:
        return False, ["mutant uretimi HICBIR satiri degistirmedi (silinen=%d, cevrilen=%d) "
                       "-> harness bayat, bu nobetciyi guncelle" % (silinen, cevrilen)]
    # Fail-closed post-kosul: mutantlarda hedefi kosan satir KALMAMALI. Kalirsa mutasyon
    # eksiktir ve asagidaki iddialar 'sahte-kirmizi' uretir (tam da 27 Tem arizasi).
    kalan_silme = _icra_satir_indeksleri(mutant, hedef)
    kalan_yorum = _icra_satir_indeksleri(yorum_mutant, hedef)
    if kalan_silme or kalan_yorum:
        return False, ["mutant uretimi EKSIK: %s'yi kosan satir mutantta KALDI "
                       "(silme mutanti %d, yorum mutanti %d) -> mutasyon capasi cok dar, "
                       "bu nobetciyi guncelle" % (hedef, len(kalan_silme), len(kalan_yorum))]
    if hedef not in mutant:
        return False, ["mutantta yorum mensiyonu kalmadi -> mutasyon testi anlamsiz "
                       "(deploy.yml yorumu %s'yi artik anmiyor)" % hedef]

    kesif = kesfet()
    if hedef not in kesif:
        return False, ["%s kesif predikatiyla bulunamadi (predikat bozulmus)" % hedef]
    hata = []
    if hedef not in kosulan(gercek, kesif):
        hata.append("POZITIF KONTROL BASARISIZ: gercek deploy.yml %s'yi kosulan saymadi" % hedef)
    if hedef in kosulan(mutant, kesif):
        hata.append("BULGU 1 GERI GELDI: %d icra satiri silinip yalniz yorumda kalan %s "
                    "hala 'kosuluyor' sayildi (regex icra baglamina daralmali)"
                    % (silinen, hedef))
    if hedef in kosulan(yorum_mutant, kesif):
        hata.append("T7 YORUM-BYPASS GERI GELDI: %d icra satiri '# python3 <yol>' yorumuna "
                    "cevrilince %s hala 'kosuluyor' sayildi (yorum satirlari elenmeli)"
                    % (cevrilen, hedef))
    return (not hata), hata


# Yalniz BELLEKTE kesif listesine enjekte edilen sentetik yol. Repoda BOYLE BIR DOSYA YOK
# (ve olmamali): gercek bir kapsamsiz test dosyasi yaratmak kapinin kendi 1. kuralini
# tetikler ve kapiyi kalici kirmiziya cakardi.
SENTETIK_KAPSAMSIZ = "tools/zzz-sentetik-kapsamsiz-test.py"

# Iddia RAPOR SATIRININ KENDISINE capalanir (etiketi degistiren biri nobetciyi de
# guncellemek zorunda kalsin diye) — degeri gövde degiskeninden degil, basilan metinden oku.
# CAPA SATIR SONUNA DEGIL SAYIYA (3. tur curutucu olcumu): eski `\s*$` capasi asiri
# kirilgandi — rapor satirinin SONUNA kozmetik bir ek yapilsa ('kosulan' satirindaki gibi
# parantezli detay listesi) SAYI DOGRU basildigi halde regex eslesmiyor -> n is None ->
# kapi SAHTE-KIRMIZI, ustelik teshis "etiket degistiyse guncelle" diyor ama etiket
# DEGISMEMIS oluyor. Bu kapi deploy.yml'de continue-on-error'suz kosar; yanlis-pozitif TUM
# yayini durdurur ([[kapi-kapsam-eksen-secimi]]). `\b` ile etiket GERCEKTEN degisirse hala
# eslesmez ve dogru teshisi verir — istenen davranis odur, o KALIR.
MUAF_SATIR_RE = re.compile(r"^\s*Muaf \(izin listesi\)\s*:\s*(\d+)\b")


def _muaf_sayisi(satirlar):
    """Rapor satirlarindan "Muaf (izin listesi)" degerini oku; yoksa None."""
    for s in satirlar:
        m = MUAF_SATIR_RE.match(s)
        if m:
            return int(m.group(1))
    return None


def muaf_sayaci_kontrol():
    """MUAF SAYACI KALICI NOBETCISI (27 Tem olcumu).

    OLCULEN HATA: rapor satiri `muaf = [y for y in kesif if y not in kos]` ile
    uretiliyordu -> "Muaf (izin listesi)" etiketiyle basilan sayi, IZIN_LISTESI'nde
    OLMAYAN (yani KAPSAMSIZ) dosyalari da iceriyordu. Somut: bir merge sirasinda
    tools/mimar-kapi-6ev-test.py kapsamsizken satir "Muaf: 71" yazdi; gercek muafiyet
    eklendikten SONRA (IZIN_LISTESI 70 -> 71) satir YINE "71" yazdi. Yani basilan sayi
    muafiyet eklemesine KOR ve kapsamsiz dosya sessizce "muaf" etiketleniyordu.

    NEDEN BLOKLAYICI: merge prosedürü (~/.claude/skills/merge-kapisi/SKILL.md) bu sayiyi
    dalin ONCE/SONRA olcumu olarak rapor ettirir. Sayi etiketine uymayinca "kac muafiyet
    eklendi" sorusu bu ciktidan cevaplanamaz hale gelir ve IZIN_LISTESI'ni elle AST okumak
    gerekir (27 Tem'de aynen bu yasandi). Yani bu bir kozmetik degil, OLCUM kanali hatasi.

    YONTEM: GERCEK deploy.yml + GERCEK kesif uzerine yalniz bellekte SENTETIK bir kapsamsiz
    yol enjekte edilir ve denetle(..., kontroller=False) cagrilir -> CI'da kosan kodun TA
    KENDISI olculur, kopya mantik yazilmaz. (kontroller=False sart: ozyineleme korumasi.)
      TEMEL: sentetiksiz kosum; basilan Muaf sayisi = N, exit kodu = TEMEL_KOD.
      MUTLAK: TEMEL_KOD == 0 iken N == len(IZIN_LISTESI) OLMAK ZORUNDA (asagida gerekcesi).
      (a) kesif + SENTETIK, izin = IZIN_LISTESI
          -> exit 1 + SENTETIK icin KAPSAMSIZ satiri + Muaf sayisi HALA N (sizmamali).
      (b) kesif + SENTETIK, izin = IZIN_LISTESI + {SENTETIK: gerekce}
          -> exit TEMEL_KOD (muafiyet kapiyi temelin verdigi hale geri dondurur)
             + Muaf sayisi TAM OLARAK N+1 (muafiyete kor olmamali).
    (a)/(b) DELTA iddialaridir; tek baslarina sabit bir kaydirmayi (or. satiri `len(muaf)-1`
    basmak) YAKALAYAMAZ — merge prosedürü MUTLAK sayiyi okudugu icin MUTLAK capa sarttir.

    TEMEL KIRMIZI OLSA DA CALISIR (duzeltme, 27 Tem): iddialar MUTLAK degil TEMELE GORELI
    DELTA'dir -> "temel kirmizi, olcum anlamsiz" diye erken donmez. Eski hali tam da bu
    bug'in gorundugu senaryoda (repoda GERCEK bir kapsamsiz test dosyasi varken) kapiya
    IKINCI bir ❌ satiri ekliyordu: kapi zaten KAPSAMSIZ ile kirmiziyken "SONUC: KIRMIZI
    (2 sorun)" cikiyordu. merge prosedürü bu SORUN SAYISINI okur -> olcum kanalini duzeltmek
    icin yazilan nobetci, kirmizi halde olcum kanalini yeniden kirletiyordu; ustelik nobetci
    en cok ise yarayacagi anda (kapsamsiz VARKEN) kendini kapatiyordu. Tek istisna n is None:
    etiket/regex kaymasinda gercekten olculecek sey yoktur, orada erken donus KALIR."""
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()
    kesif = kesfet()
    if SENTETIK_KAPSAMSIZ in kesif:
        return False, ["sentetik yol repoda GERCEKTEN var: %s -> nobetci anlamsizlasti "
                       "(dosyayi sil ya da sentetik adi degistir)" % SENTETIK_KAPSAMSIZ]

    temel_kod, temel_satirlar = denetle(gercek, kesif, IZIN_LISTESI, kontroller=False)
    n = _muaf_sayisi(temel_satirlar)
    if n is None:
        # TEK mesru erken donus: etiket/regex kaymissa olculecek sayi YOKTUR.
        return False, ["temel raporda 'Muaf (izin listesi)' satiri bulunamadi "
                       "(etiket degistiyse MUAF_SATIR_RE'yi guncelle)"]
    # NOT: temel_kod KIRMIZI olabilir (repoda gercek bir kapsamsiz dosya varken normaldir).
    # Erken DONULMEZ; asagidaki iddialar temel_kod'a GORELI kurulur -> nobetci o halde de
    # olcer ve kapinin sorun sayisini SISIRMEZ.

    kesif_sentetik = sorted(list(kesif) + [SENTETIK_KAPSAMSIZ])
    hata = []

    # MUTLAK CAPA (3. tur curutucu olcumu): asagidaki (a)/(b) iddialari DELTA'dir ve n, n_a,
    # n_b UCU DE AYNI rapor satirindan okunur -> sabit bir KAYDIRMA (olculdu: satiri
    # `len(muaf) - 1` basacak sekilde degistirmek) delta'lari BOZMAZ, nobetci HIC KONUSMAZ,
    # ama basilan mutlak sayi (70) yalan olur. merge prosedürü tam da bu MUTLAK sayiyi olcum
    # olarak okudugu icin delta korunumu YETMEZ.
    # NEDEN GECERLI: kapi YESIL iken kural 3 (bayat izin: artik kesfedilmiyor) ve kural 4
    # (bayat izin: artik kosuluyor) ZATEN sifirdir -> izin ⊆ kesif ve izin ∩ kos = bos ->
    # tanim geregi muaf == IZIN_LISTESI. Yani yesil kosumda basilan sayi len(IZIN_LISTESI)'ne
    # ESIT OLMAK ZORUNDA. temel_kod != 0 iken bu esitlik GECERLI DEGILDIR (bayat girisler
    # sapma yaratir) -> capa YALNIZ yesil temelde uygulanir; (a)/(b) delta iddialari her iki
    # halde de aynen kalir.
    if temel_kod == 0 and n != len(IZIN_LISTESI):
        hata.append("MUTLAK SAYI YALAN: basilan %r, gercek izin listesi %d -> delta korunmus "
                    "olsa da rapor sayisi merge olcumunu yaniltir"
                    % (n, len(IZIN_LISTESI)))

    # (a) sentetik yol KAPSAMSIZ: red semantigi korunmali VE muaf sayisina SIZMAMALI
    kod_a, satir_a = denetle(gercek, kesif_sentetik, IZIN_LISTESI, kontroller=False)
    n_a = _muaf_sayisi(satir_a)
    if kod_a != 1:
        hata.append("(a) KAPSAMSIZ TESPITI BOZUK: sentetik kapsamsiz yol eklenince exit 1 "
                    "bekleniyordu, exit %r geldi" % kod_a)
    if not any(("KAPSAMSIZ" in s and SENTETIK_KAPSAMSIZ in s) for s in satir_a):
        hata.append("(a) KAPSAMSIZ SATIRI YOK: %s icin 'KAPSAMSIZ' hatasi beklenmisti"
                    % SENTETIK_KAPSAMSIZ)
    if n_a != n:
        hata.append("(a) MUAF SAYACI SIZDIRIYOR: kapsamsiz dosya 'Muaf (izin listesi)' "
                    "sayisina girdi (beklenen %d, basilan %r) -> sayi etiketine uymuyor "
                    "(27 Tem hatasinin ta kendisi)" % (n, n_a))

    # (b) sentetik yol GEREKCELI MUAF: kabul semantigi korunmali VE sayi TAM 1 artmali.
    #     Iddia TEMELE GORELI: gerekceli muafiyet kapiyi TEMELIN verdigi hale geri dondurur
    #     (temel yesilse 0, temel kirmiziysa 1 kalir) -> temel kirmizi iken de kirilgan degil.
    izin_b = dict(IZIN_LISTESI)
    izin_b[SENTETIK_KAPSAMSIZ] = ("SENTETIK NOBETCI GIRISI — yalniz bellekte, repoda "
                                  "karsilik gelen dosya yok.")
    kod_b, satir_b = denetle(gercek, kesif_sentetik, izin_b, kontroller=False)
    n_b = _muaf_sayisi(satir_b)
    if kod_b != temel_kod:
        hata.append("(b) MUAFIYET KABULU BOZUK: sentetik yol gerekceyle izin listesine "
                    "eklenince kapi temel verdigi exit %r'e donmeliydi, exit %r geldi (%s)"
                    % (temel_kod, kod_b,
                       "; ".join(s.strip() for s in satir_b if s.strip().startswith("❌"))))
    if n_b != n + 1:
        hata.append("(b) MUAF SAYACI KOR: muafiyet eklenince sayi %d -> %d olmaliydi, "
                    "basilan %r (27 Tem'de olculen 71 -> 71 kor sayaci)" % (n, n + 1, n_b))
    return (not hata), hata


# ---- OZ-NOBETCI ADIMI (zincirin son halkasi) -------------------------------
# BU BETIGIN kendi repo-goreli yolu — bulgu1 mutasyon nobetcisi, oz-nobetci adimi
# nobetcisi ve bayraksiz adim nobetcisi AYNI sabiti kullanir (dosya yeniden
# adlandirilirsa uc nobetci birden dogru yeri arar; uc ayri literal TUTULMAZ).
HEDEF_BETIK = "tools/ci-kapsam-test.py"

KENDINI_TEST_BAYRAGI = "--kendini-test"
# 🔴 AGIR DAVRANIS AYAGININ KENDI BAYRAGI (9 Agu 2026, 4. tur): `--kendini-test`
# adimi `nobet.yml`de (SERIT B — yayini BLOKLAMAZ) yasiyor. Agir ayak oraya
# alininca N1/N3/X4 sinifi push'u DA deploy'u DA gecer oldu. Ayri bayrak, ayri
# adim: YALNIZ bu bayrak `deploy.yml`in BLOKLAYICI `serit-a3` job'una baglanir,
# nobet.yml serit karari BOZULMAZ.
KANCA_KABLO_BAYRAGI = "--kanca-kablo"
KENDINI_TEST_TANI = (
    "nobet.yml'de (bu betigin adimlarinin yasadigi is akisi — bkz. KENDI_IS_AKISI) "
    "bu betigi `--kendini-test` ile ANLAMLI olarak kosan hicbir adim YOK "
    "-> oz-nobetci adimi kalkmis, bayragi dusmus ya da cagri MENSIYONA cevrilmis. "
    "GERI KOY: 'CI kapsam kapisi oz-nobetcileri' adimi, "
    "`run: python3 tools/ci-kapsam-test.py --kendini-test`.\n"
    "   KABUL EDILEN BICIMLER (olculdu; bu liste kapinin FIILEN kabul ettikleridir):\n"
    "     * inline `run: <komut>` · cift/tek TIRNAKLI skalar · `bash -c \"<komut>\"`\n"
    "     * `python3 -u` / `-X utf8` / `env VAR=1 python3 ...` / `python3 ./tools/...`\n"
    "     * KATLANAN blok: `run: >-` / `>` / `>+` — komut BIRDEN COK satira bolunebilir,\n"
    "       yeter ki satirlar AYNI GIRINTIDE olsun (YAML onlari boslukla birlestirir).\n"
    "     * LITERAL blok `run: |` / `|-` — burada her satir AYRI bir kabuk komutudur:\n"
    "       bayrak komutla AYNI satirda olmali ya da satir `\\` ile devam etmeli.\n"
    "   KABUL EDILMEYEN (bilerek): katlanan blokta BOS SATIRLA ya da DAHA GIRINTILI\n"
    "     satirla ayrilmis bayrak (YAML onlari birlestirmez -> CI'da da bayrak GITMEZ) ·\n"
    "     `echo`/`printf`/`grep` mensiyonu · `--help`/`-h`/`--version` · `env:`ten gelen\n"
    "     yol (`python3 \"$KAPI\"`) statik cozulemez -> bare `python3 tools/x.py` yaz.\n"
    "   Bayrak adi bilerek degistiyse KENDINI_TEST_BAYRAGI sabitini guncelle.")

BAYRAKSIZ_TANI = (
    "nobet.yml'de (bu betigin adimlarinin yasadigi is akisi — bkz. KENDI_IS_AKISI) bu "
    "betigi BAYRAKSIZ (kapsam kolu) ANLAMLI olarak kosan hicbir adim YOK.\n"
    "   OLCULEN IKI DELIK (30 Tem, geçici kopyada; dort denetci de rc=0 idi):\n"
    "     (1) `run: python3 tools/ci-kapsam-test.py --help` -> adim CI'da YESIL kosar,\n"
    "         argparse kullanim metnini basip exit 0 verir, HICBIR kapsam iddiasi olculmez.\n"
    "     (2) bayraksiz ADIM butunuyle SILINIR, yalniz `--kendini-test` adimi kalir ->\n"
    "         KAPSAM kurali (her kabul testi kosuluyor/muaf) CI'da HIC olculmez.\n"
    "   Ikisi de `kosulan()` tarafindan gorulemez: bu betigin o is akisinda IKI cagrisi\n"
    "   vardir, biri kalinca yol yine 'kosuluyor' sayilir. O yuzden AYRI nobetci sart.\n"
    "   🔴 NEDEN `--kendini-test` KOLUNDA YASAR: iki mutantta da BAYRAKSIZ kol CI'da\n"
    "   ya hic kosmaz (2) ya da olcum govdesine HIC girmez (1) -> kendi olumunu haber\n"
    "   veremez. Kanit hala kosan `--kendini-test` adimindan gelmek ZORUNDA.\n"
    "   GERI KOY: 'CI kapsam kapisi (her kabul testi kosuluyor mu / gerekceli muaf mi)'\n"
    "   adimi, `run: python3 tools/ci-kapsam-test.py` (bayraksiz, continue-on-error YOK).")


def _hedef_cagrilari(deploy_metin, hedef):
    """(anlamli, reddedilen) — deploy.yml'de <hedef>'i kosan cagrilarin envanteri.

    anlamli    : her ANLAMLI cagri icin ARGUMAN listesi. Jetonlanamayan (OLCULEMEDI)
                 cagri icin None konur -> "cagri var ama BAYRAKLARI SORGULANAMAZ"
                 demektir ve bayrak sorusu olan nobetciler onu KABUL eder (fail-OPEN;
                 bkz. kosulan() gerekcesi).
    reddedilen : [(komut_govdesi, sebep), ...] — capaya uyan ama ANLAMSIZ bulunan
                 adaylar (kara liste bayragi / mensiyon komutu). Tanida basilir ki
                 mimar "neden kirmizi" sorusunu ciktidan cevaplayabilsin.

    TEK KAYNAK: hem kendini_test_adimi_kontrol() hem bayraksiz_adim_kontrol() BURADAN
    beslenir -> "cagri var mi" mantiginin ikinci kopyasi TUTULMAZ.

    _icra_komutlari() ile AYNI iki birlestirme katmani uygulanir (once YAML katlamasi,
    sonra kabuk satir devami). Katlama BURADA da SART: bu fonksiyon BAYRAK listesi
    dondurur ve `run: >-` blogunda bayrak ayri HAM satirda kalirsa argüman sayilmaz ->
    oz-nobetci adimi duruyor olsa bile "YOK" hukmu verilir (olculdu: Y05)."""
    anlamli = []
    reddedilen = []
    for ham in SUZGEC.birlestir_devam(_katlanan_bloklari_birlestir(deploy_metin)):
        govde = _icra_govdesi(ham)
        if not govde:
            continue
        hukum, sebep, argumanlar = SUZGEC.anlamli_cagri(govde, hedef)
        if hukum == SUZGEC.EVET:
            anlamli.append(list(argumanlar or []))
        elif hukum == SUZGEC.OLCULEMEDI:
            anlamli.append(None)
        elif hukum == SUZGEC.HAYIR:
            reddedilen.append((govde, sebep))
    return anlamli, reddedilen


def _reddedilen_ozeti(reddedilen):
    if not reddedilen:
        return ""
    return "\n   REDDEDILEN ADAY(LAR): " + " | ".join(
        "%r -> %s" % (k[:90], s) for k, s in reddedilen[:3])


# ---- BICIM TESHISI (Y05 / T3) ----------------------------------------------
# 🔴 NEDEN: "cagri YOK" tanisi, cagriyi MESRU bir bicimde YAZMIS olan kisiye hicbir sey
# soylemez ("ama ben yazdim") ve o kisi kapiyi gevsetmeye yonelir — Y05'te tam bu oldu:
# `run: >-` ile COK SATIRA yayilmis mesru cagri "YOK" gorundu, ustelik tani metni `>-`'yi
# gecerli bicim diye ONERIYORDU. Bu tani, kapinin O ADIMDA hangi YAML BICIMINI ve
# FIILEN hangi komut(lar)i gordugunu + her birine verdigi HUKMU basar.
# Nobetcisi: BICIM_FIKSTURLERI (govde) + TANI_KABLOLARI (AST cagri).
_RUN_BASI_TANI_RE = re.compile(r"^(?P<girinti>[ ]*)(?P<tire>-[ ]+)?run:[ \t]*(?P<deger>.*)$")
_ADIM_ADI_RE = re.compile(r"^[ ]*(?:-[ ]+)?name:[ \t]*(?P<ad>.+?)[ \t]*$")


def _bicim_etiketi(deger):
    """`run:` degerinin YAML SKALAR BICIMINI insan diliyle etiketle."""
    # anchor (`&capa`) / etiket (`!tip`) onekleri BICIMI degistirmez -> at.
    deger = _OZELLIK_ONEK_RE.sub("", deger.strip(), count=1)
    d = deger.split("#")[0].strip() if deger.strip()[:1] in "|>" else deger.strip()
    if not d:
        return "BOS `run:` degeri"
    if d[0] == ">":
        return ("KATLANAN blok skalari (`run: %s`) — ayni girintideki satirlar YAML "
                "tarafindan TEK BOSLUKLA birlestirilir" % d)
    if d[0] == "|":
        return ("LITERAL blok skalari (`run: %s`) — satirlar BIRLESMEZ, her satir AYRI "
                "bir kabuk komutudur" % d)
    if d[0] == '"':
        return "CIFT-TIRNAKLI inline skalar"
    if d[0] == "'":
        return "TEK-TIRNAKLI inline skalar"
    return "DUZ (inline) skalar"


def _run_bloklari(satirlar):
    """[(run_i, son_i, deger), ...] — her `run:` satiri ve govdesinin HAM satir araligi
    ([run_i, son_i)). Govde = `run:` satirindan DAHA GIRINTILI (ya da bos) satirlar."""
    bloklar = []
    n = len(satirlar)
    for i, s in enumerate(satirlar):
        m = _RUN_BASI_TANI_RE.match(s)
        if not m:
            continue
        girinti = len(m.group("girinti"))
        j = i + 1
        while j < n:
            t = satirlar[j]
            if t.strip() and (len(t) - len(t.lstrip(" "))) <= girinti:
                break
            j += 1
        bloklar.append((i, j, m.group("deger")))
    return bloklar


_DIZI_BASI_RE = re.compile(r"^[ ]*-[ \t]")


def _adim_adi(satirlar, run_i):
    """<run_i> satirindaki `run:`in AIT OLDUGU adimin adi ("" = adsiz adim).

    🔴 NEDEN ADIM SINIRINDA DURUYOR (curutme turu Y4): tani, geriye dogru ilk `name:`
    satirini ariyordu; ADSIZ bir adimda (`- run: ...` — GHA'da adim adi ZORUNLU DEGIL)
    bu, bir ONCEKI adimin adini suclamak demektir. Bakimci yanlis adima bakar. Dizi
    ogesi basi (`- ` ile baslayan satir) ADIM SINIRIDIR: oraya once varilirsa adim ADSIZDIR."""
    if _DIZI_BASI_RE.match(satirlar[run_i]):
        return ""            # `- run:` -> adimin ILK anahtari run, ad YOK
    for k in range(run_i - 1, max(run_i - 60, -1), -1):
        s = satirlar[k]
        if not s.strip():
            continue
        m = _ADIM_ADI_RE.match(s)
        if m:
            return m.group("ad").strip().strip("\"'")
        if _DIZI_BASI_RE.match(s):
            return ""        # ONCEKI adimin basina varildi -> bu adim ADSIZ
    return ""


def bicim_teshisi(deploy_metin, hedef):
    """[(adim_adi, bicim, [(komut, hukum_metni), ...]), ...] — <hedef>'i ANAN her `run:`
    blogu icin: hangi ADIMDA, hangi YAML BICIMINDE ve kapinin O BLOKTA FIILEN gordugu
    MANTIKSAL komut satirlari + her birine verdigi hukum.

    Mantiksal satirlar _mantiksal_yaml_satirlari()'ndan gelir (kapinin kendi gozu) —
    tani ile hukum AYRISAMAZ. Katlanan blokta bayrak AYRI mantiksal satirda kaldiysa
    (bos satir / daha girintili satir ayirdi) bu ACIKCA yazilir: CI'da da AYRI komut
    olurlar, yani KIRMIZI GERCEKTIR."""
    satirlar = deploy_metin.splitlines()
    bloklar = _run_bloklari(satirlar)
    kova = {}
    for metin, hamlar in _mantiksal_yaml_satirlari(deploy_metin):
        bas = hamlar[0] if hamlar else 0
        for run_i, son_i, _deger in bloklar:
            if run_i <= bas < son_i:
                kova.setdefault(run_i, []).append(metin)
                break
    kayit = []
    for run_i, son_i, deger in bloklar:
        gorulen = kova.get(run_i, [])
        if not any(hedef in m for m in gorulen):
            continue
        adim = _adim_adi(satirlar, run_i)
        satir_hukmu = []
        for metin in gorulen:
            govde = _icra_govdesi(metin)
            # BOS satir ve blok GOSTERGESININ kendisi (`run: |` -> "|") tani URETMEZ:
            # bunlar komut degildir, listede gorunurse "kac AYRI komut oldu" sayisini
            # sisirir ve okuyani yaniltir.
            if not (govde or metin).strip().strip("|>+-0123456789"):
                continue
            if not govde:
                satir_hukmu.append((metin.strip(),
                                    "ICRA SATIRI DEGIL (yorum / YAML anahtari gorundu)"))
                continue
            hukum, sebep, argumanlar = SUZGEC.anlamli_cagri(govde, hedef)
            if hukum == SUZGEC.EVET:
                h = "ANLAMLI CAGRI — gorulen argumanlar: %r" % (list(argumanlar or []),)
            elif hukum == SUZGEC.HAYIR:
                h = "ANLAMSIZ (cagri SAYILMAZ): %s" % sebep
            elif hukum == SUZGEC.OLCULEMEDI:
                h = "OLCULEMEDI (jetonlanamadi, BUGUNKU davranis korunur): %s" % sebep
            else:
                h = "bu yolla ILGISIZ gorundu"
            satir_hukmu.append((govde, h))
        kayit.append((adim, _bicim_etiketi(deger), satir_hukmu))
    return kayit


def _teshis_ozeti(deploy_metin, hedef):
    """bicim_teshisi()'ni tani metnine cevir (kapi KIRMIZI yandiginda basilir)."""
    kayit = bicim_teshisi(deploy_metin, hedef)
    # 🔴 HANGI KOL HUKUM VERDI (mimar hukmu madde 3): tani ile hukum AYNI nesneden
    # beslenir; okuyan, kararin GERCEK ayristiricidan mi taklitten mi geldigini gorsun.
    kol = "\n   AYRISTIRICI: %s" % ayristirici_kolu()
    if not kayit:
        return (kol + "\n   GORULEN: deploy.yml'de `%s` yolunu ANAN hicbir `run:` blogu "
                "YOK -> adim butunuyle silinmis ya da yol degismis olabilir." % hedef)
    parcalar = [kol]
    for adim, bicim, satir_hukmu in kayit:
        p = "\n   GORULEN ADIM: %r\n     BICIM: %s" % (adim or "(adsiz)", bicim)
        for komut, hukum in satir_hukmu[:4]:
            p += "\n     KAPININ GORDUGU KOMUT: %r\n       -> %s" % (komut[:150], hukum)
        if bicim.startswith("KATLANAN") and len(satir_hukmu) > 1:
            p += ("\n     ⚠️ Bu KATLANAN blok %d AYRI mantiksal satir uretti: BOS SATIR ya da "
                  "DAHA GIRINTILI satir onlari ayirmis. YAML bunlari BIRLESTIRMEZ -> CI'da da "
                  "AYRI kabuk komutu olurlar (bayrak komuta GITMEZ). Satirlari AYNI GIRINTIDE "
                  "ve ARALIKSIZ yaz." % len(satir_hukmu))
        if bicim.startswith("LITERAL") and len(satir_hukmu) > 1:
            p += ("\n     ⚠️ LITERAL blokta her satir AYRI komuttur: bayragi komutla AYNI "
                  "satira koy ya da satiri `\\` ile devam ettir.")
        parcalar.append(p)
    return "".join(parcalar)
KENDINI_TEST_SABIT_TANI = (
    "KENDINI_TEST_BAYRAGI sabiti BOZULMUS (deger: %r). Bos ya da `--` ile baslamayan bir "
    "sabit duz alt-dize aramasini ANLAMSIZ kilar: bos dize HER govdede gecer -> adim "
    "silinse bile nobetci YESIL kalirdi. Sabiti gercek bayrak metnine geri koy "
    "(`--kendini-test`).")


MODEL_URETIM_KOLLARI = (
    "tools/model-uyelik-kapisi.py",
    "tools/model-baslik-kolu-test.py",
)


def model_uretim_kollari_dogrula(deploy_metin):
    """Iki model kapisinin BAYRAKSIZ uretim kolu deploy'da kalmis mi."""
    hatalar = []
    for hedef in MODEL_URETIM_KOLLARI:
        anlamli, reddedilen = _hedef_cagrilari(deploy_metin, hedef)
        if any(argumanlar == [] for argumanlar in anlamli):
            continue
        hatalar.append(
            "MODEL URETIM KOLU YOK: deploy.yml `%s` yolunu BAYRAKSIZ kosmuyor; "
            "yalniz `--kendini-test` kolunun baska is akisinda kosmasi canli katalog "
            "iddiasinin yerini tutmaz.%s%s"
            % (hedef, _teshis_ozeti(deploy_metin, hedef),
               _reddedilen_ozeti(reddedilen)))
    return hatalar


def kendini_test_adimi_kontrol():
    """OZ-NOBETCI ADIMI KALICI NOBETCISI (3. tur curutucu olcumu, 27 Tem).

    OLCULEN DELIK: 791b0366 deploy.yml'e `python3 tools/ci-kapsam-test.py --kendini-test`
    adimini ekledi ve CI'da yesil kostu — AMA EKLENEN ADIMIN KENDISI NOBETCISIZDI.
    Iki mutant sinifi repoda TEK BIR KIRMIZI bile yakmiyordu (olculdu: ikisinde de
    bayraksiz kosum 0, --kendini-test kosumu 0):
      (1) `--kendini-test` adimi deploy.yml'den SILINDI,
      (2) adim duruyor ama `--kendini-test` BAYRAGI dusuruldu (adim ikinci kez duz
          `python3 tools/ci-kapsam-test.py` kosuyor).
    Yani biri oz-nobetci adimini kaldirsa zincir SESSIZCE kopuyordu: bulgu1 +
    muaf sayaci nobetcileri hala denetle(kontroller=True) yolundan cagriliyor gorunse
    de, o adimin korudugu IKI mutant sinifi (nobetci CAGRILARININ silinmesi ve
    denetle()'nin kirmizi cikis yolunun sakatlanmasi) yeniden ORTULU hale geliyordu.

    NEDEN BAYRAKSIZ (BLOKLAYICI) KOLDA YASAR: bu nobetci `--kendini-test` kolunda
    OLURDU — adim silindiginde o kol CI'da ZATEN kosmaz, yani kendi olumunu haber
    veremezdi. Kanit hala kosan DUZ adimdan gelmek ZORUNDA; bu yuzden
    denetle(..., kontroller=True) icinden cagrilir. (--kendini-test kolunda AYRICA
    raporlanir, ama tek GERCEK kapi bayraksiz kosumdur.)

    IDDIA (TUR 6, 30 Tem — DUZ `in` ARAMASI KALDIRILDI): deploy.yml'de bu betigi
    `--kendini-test` ARGUMANIYLA **ANLAMLI OLARAK ICRA EDEN** bir cagri var mi.
    Olcum ortak suzgecle yapilir (SUZGEC.anlamli_cagri, tools/icra-suzgeci.py): satir
    gercek bir kabuk sozcuk ayiricisiyla (`shlex`, POSIX kip) jetonlanir,
    `&&`/`||`/`;`/`|` segmentlerine bolunur ve her segmentin BASINDAKI komut bulunur.

    🔴 NEDEN DUZ `in` BIRAKILDI (olculdu 30 Tem, DELIK 3): eski iddia "bayrak metni
    yorum-olmayan bir icra govdesinde GECIYOR MU" idi ve BILEREK mensiyonu da
    "duruyor" sayiyordu. O bedel olculdu ve KABUL EDILEMEZ cikti:
        `run: echo python3 tools/ci-kapsam-test.py --kendini-test`
    mutantinda oz-nobetci adimi HICBIR SEY kosmadigi halde dort denetci de rc=0
    verdi (ham cikti muhendis raporunda). `echo` bir MENSIYON komutudur; artik
    SUZGEC.MENSIYON_KOMUTLARI kara listesiyle HAYIR hukmu alir.

    🔴 AYRISTIRICI TAKLIDI YOK ([[mimar-kapi-parser-taklidi]]): TUR 2/3'te ELLE
    yazilan on-ek/tirnak capalari mesru yazimlari sahte-KIRMIZI yakmisti. Bu turda
    elle capa YAZILMADI — `shlex` standart kutuphanenin GERCEK kabuk sozcuk
    ayiricisidir, YAML tarafi ise aynen _icra_govdesi() ortak suzgecidir. Jetonlama
    patlarsa (dengesiz tirnak vb.) hukum OLCULEMEDI olur ve nobetci onu KABUL EDER
    (fail-OPEN) -> yeni bir sahte-kirmizi yuzeyi ACILMAZ.

    OLCULDU (30 Tem TUR 6, gecici kopyada; canli dosyaya mutasyon UYGULANMADI):
      YESIL 15/15 mesru kabuk bicimi: bare · `--kendini-test` · `python3 -u` ·
        `python3 -X utf8` · `bash -c "..."` · `bash -c \'...\'` · fazla bosluk ·
        satir sonunda `;` · sonda bosluk · `env VAR=1 python3 ...` ·
        `VAR=1 python3 ...` · `python3 ./tools/...` · `--deploy <yol>` ·
        `> /dev/null` yonlendirmesi · shebang ile DOGRUDAN cagri.
      KIRMIZI 8/8 anlamsiz bicim: `--help` · `-h` · `--version` · `echo ...` ·
        `printf ...` · `echo \'<tam komut>\'` · `grep ...` · `bash -c "echo ..."`.
      YESIL kalan mesru YAML bicimleri (TUR 4 listesi, aynen korunur): cift/tek
        tirnakli skalar · `run: |` · `run: >-` katlanan · `\\` satir devami ·
        `if:`/`env:` bloklu adim · baska job'a tasima.

    🔴 TUR 7 (30 Tem) — Y05 SAHTE-KIRMIZI ONARIMI: TUR 4/6'nin "`run: >-` katlanan YESIL"
    kaydi YANILTICIYDI — o fikstur TEK SATIRLIK `>-` kullaniyordu, yani KATLAMAYI HIC
    egzersiz etmiyordu. Olculdu (gecici kopyada, ruby-psych ile `run` degeri BAYT-OZDES
    dogrulanarak): COK SATIRLI `>-` / `>` / `>+` blogunda 6 mesru yazim SAHTE-KIRMIZI
    yaniyordu — ustelik YUKARIDAKI onarim mesaji `>-`'yi "gecerli bicim" diye ONERIYORDU.
    FIX: _katlanan_bloklari_birlestir() (YAML katlama kurali, LITERAL `|` bloklara
    DOKUNMAZ) _hedef_cagrilari() + _icra_komutlari() girdisine uygulanir; nobetcisi
    KATLAMA_FIKSTURLERI (govde) + KATLAMA_KABLOLARI (AST cagri).

    NE KANITLAR / NE KANITLAMAZ: bu nobetci "adim CI'da KOSUYOR ve BLOKLUYOR"
    demez — "deploy.yml'de bu betigi bu bayrakla ICRA EDEN bir komut YAZILI" der.
    Adim `if: false` / `continue-on-error: true` / `|| true` ile etkisizlestirilirse
    bu nobetci DEGIL tools/is-akisi-kapisi.py BOLUM D konusur (o eksen orada:
    kuresel, gercek YAML uzerinde, D_IZIN beyan mekanizmasiyla). Kapsam disi kalan
    tek sinif nobetci/suzgec GOVDESININ no-op yapilmasidir ->
    suzgec_fikstur_kontrol() + suzgec_kablosu_kontrol().
    (ok, hata_satirlari) dondurur."""
    # FAIL-CLOSED SABIT DAYANAGI (TUR 5): bos ya da `--` ile baslamayan bir sabit
    # bayrak sorgusunu ANLAMSIZ kilar -> adim silinse bile nobetci YESIL kalirdi.
    if not KENDINI_TEST_BAYRAGI or not KENDINI_TEST_BAYRAGI.startswith("--"):
        return False, [KENDINI_TEST_SABIT_TANI % (KENDINI_TEST_BAYRAGI,)]
    if not os.path.exists(KENDI_IS_AKISI):
        return False, ["bu betigin adimlarini tasiyan is akisi bulunamadi: %s"
                       % KENDI_IS_AKISI]
    with open(KENDI_IS_AKISI, encoding="utf-8") as f:
        gercek = f.read()
    anlamli, reddedilen = _hedef_cagrilari(gercek, HEDEF_BETIK)
    for argumanlar in anlamli:
        # None = jetonlanamadi -> bayraklar sorgulanamaz, BUGUNKU davranis korunur.
        if argumanlar is None or KENDINI_TEST_BAYRAGI in argumanlar:
            return True, []
    return False, [KENDINI_TEST_TANI + _teshis_ozeti(gercek, HEDEF_BETIK)
                   + _reddedilen_ozeti(reddedilen)]


def bayraksiz_adim_kontrol():
    """BAYRAKSIZ (KAPSAM KOLU) ADIMI NOBETCISI — 30 Tem, DELIK 1 + DELIK 4.

    OLCULEN IKI DELIK (gecici kopyada; canli deploy.yml'e DOKUNULMADI. Her ikisinde
    de `ci-kapsam-test.py`, `ci-kapsam-test.py --kendini-test`, `is-akisi-kapisi.py`,
    `is-akisi-kapisi.py --kendini-test` DORDU de rc=0 verdi):
      D1) `run: python3 tools/ci-kapsam-test.py` -> `... --help`. Adim CI'da GORUNUR
          ve YESIL kosar; argparse kullanim metnini basip exit 0 verir. Kapsam kurali
          (her kabul testi kosuluyor / gerekceli muaf) HIC olculmez.
      D4) Bayraksiz ADIM (name + run) BUTUNUYLE SILINDI; yalniz `--kendini-test`
          adimi kaldi. Ayni sonuc: kapsam kurali CI'da hic olculmez.

    NEDEN kosulan() GORMEZ: bu betigin deploy.yml'de IKI cagrisi var. Biri
    bozulsa/silinse OTEKI capaya uyar ve `tools/ci-kapsam-test.py` yine "kosuluyor"
    sayilir -> KAPSAMSIZ satiri hic olusmaz. TEK cagrisi olan kapilarda `kosulan()`
    bu sinifi ARTIK ZATEN yakalar (`--help` sayilmiyor); iki cagrili tek dosya bu
    betiktir, o yuzden AYRI nobetci sart.

    NEREDE YASAR (kritik): `--kendini-test` KOLUNDA. Iki mutantta da bayraksiz kol ya
    hic kosmaz (D4) ya olcum govdesine hic girmez (D1) -> kendi olumunu haber
    veremez. denetle(kontroller=True) icinden de cagrilir (yerel bayraksiz kosum
    icin), ama CI'daki GERCEK kanit `--kendini-test` adimindadir. Ayrica
    tools/is-akisi-kapisi.py BOLUM E ayni iddiayi BAGIMSIZ BIR SURECTEN olcer
    (iki adim birden silinse de konussun).

    IDDIA: deploy.yml'de bu betigi `--kendini-test` BAYRAGI OLMADAN anlamli olarak
    icra eden EN AZ BIR cagri var. (`--deploy <yol>` gibi girdi seçen bayraklar
    kapsam kolunu KOSTURUR -> gecerli sayilir; kolu baska bir kola ceviren tek
    bayrak `--kendini-test`tir.)
    (ok, hata_satirlari) dondurur."""
    if not os.path.exists(KENDI_IS_AKISI):
        return False, ["bu betigin adimlarini tasiyan is akisi bulunamadi: %s"
                       % KENDI_IS_AKISI]
    with open(KENDI_IS_AKISI, encoding="utf-8") as f:
        gercek = f.read()
    anlamli, reddedilen = _hedef_cagrilari(gercek, HEDEF_BETIK)
    for argumanlar in anlamli:
        if argumanlar is None or KENDINI_TEST_BAYRAGI not in argumanlar:
            return True, []
    return False, [BAYRAKSIZ_TANI + _teshis_ozeti(gercek, HEDEF_BETIK)
                   + _reddedilen_ozeti(reddedilen)]


# ---- SUZGECIN KENDI NOBETCILERI (ARIZA ENJEKSIYONU + AST KABLO) ------------
# NEDEN IKI AYRI NOBETCI: yeni ortak suzgec iki farkli yolla oldurulebilir.
#   (a) GOVDESI no-op yapilir (or. anlamli_cagri daima EVET / daima None doner)
#       -> mutasyonlar yeniden sessizlesir. Yakalayan: suzgec_fikstur_kontrol()
#          (SENTETIK fikstur, gercek dosya icerigine BAGIMSIZ).
#   (b) CAGRISI silinir (kosulan() ya da nobetciler suzgeci artik sormaz)
#       -> ayni sonuc. Yakalayan: suzgec_kablosu_kontrol() — AST ile.
# 🔴 AST/AYRISTIRICI TABANLI, METIN CAPASI DEGIL ([[kapi-anchor-coupling-ikilemi]]):
# bu depoda olculdu ki metin capasi (satiri harfiyen aramak) masum bir yorum
# duzenlemesinde sahte-KIRMIZI yakip TUM ekibin yayinini durduruyordu.
SUZGEC_FIKSTURLERI = (
    # (kabuk_satiri, hedef_yol, beklenen_hukum, etiket)
    ("python3 tools/zzz-sentetik-test.py", "tools/zzz-sentetik-test.py",
     "EVET", "bare cagri ANLAMLI sayilmali"),
    ("python3 tools/zzz-sentetik-test.py --kendini-test", "tools/zzz-sentetik-test.py",
     "EVET", "bayrakli cagri ANLAMLI sayilmali"),
    ("python3 -u tools/zzz-sentetik-test.py", "tools/zzz-sentetik-test.py",
     "EVET", "yorumlayici bayragi (-u) cagriyi bozmamali"),
    ('bash -c "python3 tools/zzz-sentetik-test.py"', "tools/zzz-sentetik-test.py",
     "EVET", "`bash -c` sarmali cagri ANLAMLI sayilmali"),
    ("node shop/test/zzz-sentetik.mjs", "shop/test/zzz-sentetik.mjs",
     "EVET", "node ekseni (uzantidan yorumlayici) ANLAMLI sayilmali"),
    ("python3 tools/zzz-sentetik-test.py --help", "tools/zzz-sentetik-test.py",
     "HAYIR", "`--help` ANLAMSIZ sayilmali (DELIK 1)"),
    ("python3 tools/zzz-sentetik-test.py -h", "tools/zzz-sentetik-test.py",
     "HAYIR", "`-h` ANLAMSIZ sayilmali"),
    ("echo python3 tools/zzz-sentetik-test.py --kendini-test", "tools/zzz-sentetik-test.py",
     "HAYIR", "`echo` MENSIYONU cagri sayilmamali (DELIK 3)"),
    ("python3 tools/baska-sentetik-test.py --kendini-test", "tools/zzz-sentetik-test.py",
     "ILGISIZ", "BASKA betige verilen bayrak bu yolu ilgilendirmez"),
)


# ---- KATLAMA FIKSTURLERI (`run:` cozumu — IKI KOLUN ORTAK govde nobetcisi) --
# IKI YONLU IDDIA: (a) KATLANAN blok GERCEKTEN birlesir, (b) LITERAL blok / paragraf
# ayrimi / more-indented satir / TAB girinti birlestirilMEZ. Tek yonlu olsa govde "daima
# birlestir" ya da "hic birlestirme" (no-op) yapilip sessizce oldurulebilirdi.
#
# 🔴 UC YONLU NOBET (30 Tem, PARSER-FIRST turu). Her fikstur UC iddia tasir:
#   1. TAKLIT (fallback) kolu beklenen mantiksal satirlari uretir,
#   2. GERCEK AYRISTIRICI kolu AYNI seyi uretir (ortamda ayristirici varsa),
#   3. iki kolun PROVENANSI (her mantiksal satiri ureten HAM satir indeksleri) da AYNI.
# (2) olmasaydi fikstur kendi kendini onaylardi; (1) olmasaydi PARSER-FIRST'ten sonra
# taklit govdesindeki her mutasyon SESSIZLESIRDI (curutme turu Z1/Z3: acik girinti
# gostergesini yok sayan ve sondaki bos satiri yutan sabotajlar KACMISTI); (3) olmasaydi
# provenansi bozan mutasyon (Z7) kacardi.
#
# 🔴 BEKLENTILER GERCEK AYRISTIRICIYA KILITLI: her satir hem ruby/psych 3.1.0 hem
# PyYAML 6.0.3 ile olculdu, ikisi de BAYT-OZDES sonuc verdi (30 Tem). Yani bu tablo
# "ayristirici taklidi" DEGIL, iki bagimsiz gercek ayristiriciya kilitlenmis bir
# esdegerlik iddiasidir.
#
# 🔴 FIKSTUR SAYISI IDDIA EDILIR (KATLAMA_FIKSTUR_ASGARI): curutme turunda olculdu ki
# tabloyu BOSALTMAK (Z6) tek basina hicbir kapiyi kirmizi yakmiyordu -> once tablo
# bosaltilir, sonra govde no-op yapilirdi: iki adimli ve TAMAMEN SESSIZ kacis.
_FK_ADIM = "      - name: sentetik adim\n"
_FK_SON = "      - name: sonraki adim\n"
_FK_P1 = "python3 tools/zzz-sentetik-test.py"
_FK_P2 = "--kendini-test"
_FK_KOMUT = _FK_P1 + " " + _FK_P2
_FK_A = "      - name: sentetik adim"
_FK_S = "      - name: sonraki adim"

KATLAMA_FIKSTURLERI = (
    # (girdi_metni, beklenen_mantiksal_satirlar, beklenen_provenans, etiket)
    (_FK_ADIM + "        run: >-\n          " + _FK_KOMUT + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2], [3]],
     "`>-` TEK satir -> `run:` oneki soyulur"),
    (_FK_ADIM + "        run: >-\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2, 3], [4]],
     "`>-` IKI satir TEK BOSLUKLA birlesmeli (Y05)"),
    (_FK_ADIM + "        run: >\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2, 3], [4]],
     "`>` (clip) da AYNI sekilde katlanmali"),
    (_FK_ADIM + "        run: >+\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2, 3], [4]],
     "`>+` (keep) da AYNI sekilde katlanmali"),
    (_FK_ADIM + "        run: >-2\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2, 3], [4]],
     "acik girinti gostergesi (`>-2`) + icerik TAM gostergede -> katlanir"),
    (_FK_ADIM + "        run: >-2\n            " + _FK_P1 + "\n            " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, "  " + _FK_P1, "  " + _FK_P2, _FK_S], [[0], [1, 2], [3], [4]],
     "acik gosterge (`>-2`) + icerik DAHA girintili -> KATLANMAZ "
     "(gostergeyi yok sayan mutasyon burada YAKALANIR)"),
    (_FK_ADIM + "        run: >-\n          " + _FK_P1 + "\n\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_P1, _FK_P2, _FK_S], [[0], [1, 2], [4], [5]],
     "BOS SATIR paragraf ayirir -> BIRLESTIRILMEMELI"),
    (_FK_ADIM + "        run: >-\n          " + _FK_P1 + "\n            " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_P1, "  " + _FK_P2, _FK_S], [[0], [1, 2], [3], [4]],
     "DAHA GIRINTILI satir KATLANMAZ (more-indented)"),
    (_FK_ADIM + "        run: |\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_P1, _FK_P2, _FK_S], [[0], [1, 2], [3], [4]],
     "LITERAL `|` blokta her satir AYRI komut (davranis DEGISMEZ)"),
    (_FK_ADIM + "        run: |-\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_P1, _FK_P2, _FK_S], [[0], [1, 2], [3], [4]],
     "LITERAL `|-` blokta her satir AYRI komut (davranis DEGISMEZ)"),
    (_FK_ADIM + "        run: " + _FK_KOMUT + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1], [2]],
     "blok gostergesi OLMAYAN inline skalar"),
    # --- 30 TEM: CURUTME TURUNUN FIKSTUR KORLUGUNU KAPATAN BES BICIM -----------
    ("      - run: >-\n          " + _FK_P1 + "\n          " + _FK_P2 + "\n" + _FK_SON,
     [_FK_KOMUT, _FK_S], [[0, 1, 2], [3]],
     "🔴 `- run: >-` ADSIZ ADIM (dizi tiresi RUN uzerinde) — MESRU GHA yazimi; "
     "eskiden cagri kapiya TUMUYLE GORUNMEZDI (190 girdilik taban regresyonu)"),
    ("      - run: " + _FK_KOMUT + "\n" + _FK_SON,
     [_FK_KOMUT, _FK_S], [[0], [1]],
     "🔴 `- run: <komut>` ADSIZ ADIM, INLINE — ayni kok neden, blok gostergesiz hali"),
    (_FK_ADIM + "        run: >-\n          " + _FK_P1 + "\n          \t" + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_P1, "\t" + _FK_P2, _FK_S], [[0], [1, 2], [3], [4]],
     "🔴 TAB girintili satir KATLANMAZ (YAML'da TAB girinti degildir) — eskiden "
     "katlaniyordu = SAHTE-YESIL (bayrak CI'da komuta GITMEDIGI halde 'gidiyor' denirdi)"),
    (_FK_ADIM + "        run: &capa >-\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2, 3], [4]],
     "🔴 ANCHOR'li blok (`run: &capa >-`) TANINMALI — eskiden blok hic taninmiyor, "
     "govde satirlari BAYRAKSIZ cagri gibi gorunuyordu = SAHTE-YESIL"),
    (_FK_ADIM + "        run: >-\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, "", _FK_S], [[0], [1, 2, 3], [4], [5]],
     "🔴 blok SONRASI BOS SATIR bloga YUTULMAZ (geri sarma nobeti: sondaki bos satiri "
     "yutan mutasyon burada YAKALANIR)"),
    (_FK_ADIM + "        run: " + _FK_P1 + "\n          " + _FK_P2 + "\n" + _FK_SON,
     [_FK_A, _FK_KOMUT, _FK_S], [[0], [1, 2], [3]],
     "🔴 COK SATIRLI DUZ (plain) skalar da KATLANIR — eskiden kapsam DISIYDI ve ilk "
     "satir BAYRAKSIZ cagri sanilirdi = SAHTE-YESIL"),
    ("      - run: >-\n          " + _FK_P1 + "\n          " + _FK_P2
     + "\n        env:\n          A: b\n" + _FK_SON,
     [_FK_KOMUT, "        env:", "          A: b", _FK_S],
     [[0, 1, 2], [3], [4], [5]],
     "🔴 `- run: >-` blogu KARDES `env:` satirlarini YUTMAZ (esik ANAHTAR girintisi, "
     "tire dahil)"),
)

# ---- ICRA GOVDESI FIKSTURLERI (_icra_govdesi onek soyma nobetcisi) ---------
# 🔴 NEDEN AYRI TABLO: `- run:` onekinin soyulmasi PARSER-FIRST'ten sonra IKINCI
# savunma hattidir (iki kol da artik BARE komut uretir) -> sabotaj enjeksiyonu onu
# tek basina oldurdugunde HICBIR kapi kirmizi yanmiyordu (olculdu: KACTI). Ikinci
# hat da NOBETLI olmali: yarin `run:` cozumu degisir de ham satir yeniden gelirse,
# onek soyma sessizce kayipsa cagri kapiya TUMUYLE gorunmez olur (Y05'in kok nedeni).
ICRA_GOVDESI_FIKSTURLERI = (
    # (ham_satir, beklenen_govde, etiket)
    ("        run: python3 tools/zzz-sentetik-test.py",
     "python3 tools/zzz-sentetik-test.py", "CIPLAK `run:` oneki soyulmali"),
    ("      - run: python3 tools/zzz-sentetik-test.py",
     "python3 tools/zzz-sentetik-test.py",
     "🔴 DIZI TIRESI `- run:` oneki de soyulmali (ADSIZ adim, mesru GHA yazimi)"),
    ("      -   run: python3 tools/zzz-sentetik-test.py",
     "python3 tools/zzz-sentetik-test.py", "tire ile `run:` arasi COK BOSLUK"),
    ("      - name: python3 tools/zzz-sentetik-test.py", None,
     "adim ADI icra DEGIL (T7 mensiyon sinifi)"),
    ("        name: python3 tools/zzz-sentetik-test.py", None,
     "tiresiz adim ADI da icra DEGIL"),
    ("        # python3 tools/zzz-sentetik-test.py", None, "YAML yorumu icra DEGIL"),
    ("           ", None, "bos satir icra DEGIL"),
    ("        run: |", "|", "blok gostergesinin kendisi govde olarak gecer"),
)


# ---- ICRA SATIR INDEKSI FIKSTURLERI (mutant capasi / provenans nobetcisi) ---
# 🔴 NEDEN: mutant ureticileri (_silme_mutanti / _yorum_mutanti) BU listeye gore satir
# siler. Katlanan blokta bolunmus bir cagrinin YALNIZ ILK ham satirini dondurmek
# mutasyonu YARIM birakir: cagri hayatta kalir, bulgu1_mutasyon_kontrol "BULGU 1 GERI
# GELDI" diye YANLIS SINIFLA sahte-KIRMIZI yanar. Olculdu: bu sabotaj (provenansta
# `idx.update(hamlar)` -> `idx.add(hamlar[0])`) hicbir kapiyi kirmizi yakmadan KACIYORDU.
# TERS YON de olculur: provenansi gereksiz genisletmek (tum blogu dondurmek) ALAKASIZ
# komutlari da siler -> literal blok fiksturu bunu yakalar.
_FI_HEDEF = "tools/zzz-sentetik-test.py"
ICRA_INDEKS_FIKSTURLERI = (
    # (metin, beklenen_indeksler, etiket)
    (_FK_ADIM + "        run: python3 tools/zzz-sentetik-test.py\n" + _FK_SON,
     [1], "inline cagri -> yalniz kendi satiri"),
    (_FK_ADIM + "        run: >-\n          python3\n"
     "          tools/zzz-sentetik-test.py\n          --kendini-test\n" + _FK_SON,
     [1, 2, 3, 4],
     "🔴 katlanan blokta UC ham satira bolunmus cagri -> DORT satir da (blok basi dahil)"),
    ("      - run: >-\n          python3 tools/zzz-sentetik-test.py\n"
     "          --kendini-test\n" + _FK_SON,
     [0, 1, 2], "🔴 ADSIZ adim (`- run: >-`) -> blok basi + iki govde satiri"),
    (_FK_ADIM + "        run: |\n          echo hazir\n"
     "          python3 tools/zzz-sentetik-test.py --kendini-test\n" + _FK_SON,
     [3], "🔴 LITERAL blokta YALNIZ cagri satiri (alakasiz `echo` satiri SILINMEZ)"),
)

# Tablo BOSALTILIRSA/KUCULURSE kapi KIRMIZI yanar (curutme turu Z6: fikstur sayisi
# hicbir yerde IDDIA EDILMIYORDU -> tabloyu bosaltmak tamamen sessizdi).
KATLAMA_FIKSTUR_ASGARI = 18
SUZGEC_FIKSTUR_ASGARI = 9
BICIM_FIKSTUR_ASGARI = 6
ICRA_GOVDESI_FIKSTUR_ASGARI = 8
ICRA_INDEKS_FIKSTUR_ASGARI = 4


# ---- BICIM TESHISI FIKSTURLERI (T3) ----------------------------------------
# IDDIA: tani, KIRMIZI yandiginda "ne gordugunu" SOYLER. Tek yonlu olmasin diye hem
# ANLAMLI (dogru yazim) hem ANLAMSIZ (mensiyon / ayrilmis bayrak) durumu olculur.
# Govde no-op yapilirsa (or. `return []`) fikstur bozulur; CAGRISI silinirse
# TANI_KABLOLARI (AST) konusur.
_BT_HEDEF = "tools/zzz-sentetik-test.py"
_BT_ADIM = "      - name: sentetik oz-nobetci adimi\n"
BICIM_FIKSTURLERI = (
    # (yaml_parcasi, beklenen_alt_dizeler, beklenmeyen_alt_dizeler, etiket)
    (_BT_ADIM + "        run: python3 tools/zzz-sentetik-test.py --kendini-test\n",
     ("sentetik oz-nobetci adimi", "DUZ (inline) skalar", "ANLAMLI CAGRI",
      "'--kendini-test'"), (),
     "DUZ inline cagri -> adim adi + bicim + ANLAMLI hukum"),
    (_BT_ADIM + "        run: >-\n          python3 tools/zzz-sentetik-test.py\n"
     "          --kendini-test\n",
     ("KATLANAN blok skalari", "ANLAMLI CAGRI", "'--kendini-test'"),
     ("AYRI mantiksal satir",),
     "KATLANAN blok BIRLESMIS -> tek satir, ANLAMLI"),
    (_BT_ADIM + "        run: >-\n          python3 tools/zzz-sentetik-test.py\n\n"
     "          --kendini-test\n",
     ("KATLANAN blok skalari", "2 AYRI mantiksal satir", "BOS SATIR ya da"), (),
     "KATLANAN blokta BOS SATIR -> bayrak AYRILDI, tani bunu SOYLER"),
    (_BT_ADIM + "        run: |\n          python3 tools/zzz-sentetik-test.py\n"
     "          --kendini-test\n",
     ("LITERAL blok skalari", "her satir AYRI komuttur"), ("KATLANAN",),
     "LITERAL blok -> 'her satir AYRI komut' uyarisi"),
    (_BT_ADIM + "        run: echo python3 tools/zzz-sentetik-test.py --kendini-test\n",
     ("ANLAMSIZ (cagri SAYILMAZ)", "echo"), ("ANLAMLI CAGRI",),
     "MENSIYON (`echo`) -> ANLAMSIZ hukmu taniya YAZILIR"),
    ("      - name: ilgisiz adim\n        run: python3 tools/baska-test.py\n",
     ("hicbir `run:` blogu YOK",), ("GORULEN ADIM",),
     "hedef HIC ANILMIYOR -> 'blok YOK' tanisi"),
)


def bicim_teshis_kontrol_govdesi():
    """BICIM_FIKSTURLERI'ni olcer; (hata_satirlari) dondurur."""
    hata = []
    for girdi, beklenenler, beklenmeyenler, etiket in BICIM_FIKSTURLERI:
        metin = _teshis_ozeti(girdi, _BT_HEDEF)
        eksik = [b for b in beklenenler if b not in metin]
        fazla = [b for b in beklenmeyenler if b in metin]
        if eksik or fazla:
            hata.append("BICIM TESHIS FIKSTURU BOZUK (%s): eksik=%r fazla=%r\n"
                        "     uretilen tani: %r\n     -> _teshis_ozeti()/bicim_teshisi() "
                        "govdesi no-op ya da ters yapilmis olabilir; kapi KIRMIZI yandiginda "
                        "mesru yazan kisi NEDEN oldugunu goremez (T3/Y05)."
                        % (etiket, eksik, fazla, metin[:400]))
    return hata


def _fikstur_sayisi_kontrol():
    """FIKSTUR TABLOSU NOBETI (curutme turu Z6) — tablolar BOSALTILINCA/KUCULUNCE konus.

    OLCULEN DELIK: KATLAMA_FIKSTURLERI'ni BOSALTMAK tek basina hicbir kapiyi kirmizi
    yakmiyordu (sayi hicbir yerde IDDIA EDILMIYORDU, yalniz bilgi amacli basiliyordu).
    Yani kacis IKI SESSIZ ADIMDI: once tabloyu bosalt, sonra govdeyi no-op yap."""
    hata = []
    for ad, tablo, asgari in (("KATLAMA_FIKSTURLERI", KATLAMA_FIKSTURLERI,
                               KATLAMA_FIKSTUR_ASGARI),
                              ("SUZGEC_FIKSTURLERI", SUZGEC_FIKSTURLERI,
                               SUZGEC_FIKSTUR_ASGARI),
                              ("BICIM_FIKSTURLERI", BICIM_FIKSTURLERI,
                               BICIM_FIKSTUR_ASGARI),
                              ("ICRA_GOVDESI_FIKSTURLERI", ICRA_GOVDESI_FIKSTURLERI,
                               ICRA_GOVDESI_FIKSTUR_ASGARI),
                              ("ICRA_INDEKS_FIKSTURLERI", ICRA_INDEKS_FIKSTURLERI,
                               ICRA_INDEKS_FIKSTUR_ASGARI),
                              ("TETIK_FIKSTURLERI", TETIK_FIKSTURLERI,
                               TETIK_FIKSTUR_ASGARI),
                              ("BEYAN_FIKSTURLERI", BEYAN_FIKSTURLERI,
                               BEYAN_FIKSTUR_ASGARI),
                              ("ALT_KUME_FIKSTURLERI", ALT_KUME_FIKSTURLERI,
                               ALT_KUME_FIKSTUR_ASGARI),
                              ("AYRISTIRICI_YOK_FIKSTURLERI",
                               AYRISTIRICI_YOK_FIKSTURLERI,
                               AYRISTIRICI_YOK_FIKSTUR_ASGARI),
                              ("IKI_KOL_RUN_GIRDILERI", IKI_KOL_RUN_GIRDILERI,
                               IKI_KOL_RUN_ASGARI),
                              ("IKI_KOL_EK_GIRDILER", IKI_KOL_EK_GIRDILER,
                               IKI_KOL_EK_ASGARI)):
        if len(tablo) < asgari:
            hata.append("FIKSTUR TABLOSU KUCULMUS: %s'de %d girdi var, EN AZ %d "
                        "olmali -> fikstur nobetcisi sessizce etkisizlestirilebilir "
                        "(once tabloyu bosalt, sonra govdeyi no-op yap). GERI KOY ya da "
                        "asgari sayiyi BILEREK dusur." % (ad, len(tablo), asgari))
    return hata


def icra_govdesi_fikstur_kontrol_govdesi():
    """ICRA_GOVDESI_FIKSTURLERI'ni olcer; (hata_satirlari) dondurur."""
    hata = []
    for ham, beklenen, etiket in ICRA_GOVDESI_FIKSTURLERI:
        gelen = _icra_govdesi(ham)
        if gelen != beklenen:
            hata.append("ICRA GOVDESI FIKSTURU BOZUK (%s): %r icin %r bekleniyordu, "
                        "%r geldi -> _icra_govdesi() onek soyma/eleme mantigi "
                        "degismis. `- run:` oneki soyulmazsa ADSIZ adimdaki cagri "
                        "kapiya TUMUYLE GORUNMEZ olur (Y05 kok nedeni)."
                        % (etiket, ham, beklenen, gelen))
    return hata


def icra_indeks_fikstur_kontrol_govdesi():
    """ICRA_INDEKS_FIKSTURLERI'ni olcer; (hata_satirlari) dondurur.
    Mutant ureticilerinin capasi = bu fonksiyon; provenans bozulursa mutasyon YARIM
    kalir ve nobetci YANLIS SINIFLA sahte-KIRMIZI yanar."""
    hata = []
    for metin, beklenen, etiket in ICRA_INDEKS_FIKSTURLERI:
        gelen = _icra_satir_indeksleri(metin, _FI_HEDEF)
        if gelen != beklenen:
            hata.append("ICRA INDEKS FIKSTURU BOZUK (%s): beklenen %r, gelen %r\n"
                        "     -> _icra_satir_indeksleri()/_blok_provenans() provenansi "
                        "bozulmus. DAR olursa silme/yorum mutasyonu cagriyi OLDUREMEZ "
                        "(bulgu1 nobetcisi yanlis sinifla sahte-KIRMIZI yanar); GENIS "
                        "olursa mutasyon ALAKASIZ komutlari da siler."
                        % (etiket, beklenen, gelen))
    return hata


def katlama_fikstur_kontrol_govdesi():
    """KATLAMA_FIKSTURLERI'ni IKI KOLDA birden olcer; (hata_satirlari) dondurur.

    UC IDDIA (bkz. tablo basligi):
      1. TAKLIT (fallback) kolu beklenen mantiksal satirlari + PROVENANSI uretir,
      2. GERCEK AYRISTIRICI kolu AYNI seyi uretir (ortamda ayristirici VARSA),
      3. iki kol BIRBIRINE ESIT (fikstur kumesinde taklit sapmasi = KIRMIZI).
    (1) PARSER-FIRST'ten sonra sart: hukmu artik ayristirici verdigi icin taklit
    govdesine yapilan mutasyonlar aksi halde SESSIZLESIR (curutme turu Z1/Z3 KACMISTI).
    suzgec_fikstur_kontrol() icinden cagrilir (ayni sinif: 'ortak donusum govdesi
    no-op yapildi')."""
    hata = _fikstur_sayisi_kontrol()
    hata.extend(icra_govdesi_fikstur_kontrol_govdesi())
    hata.extend(icra_indeks_fikstur_kontrol_govdesi())
    # psych kolunda her ayristirma bir ruby SURECI acar -> fiksturleri TOPLU isit.
    YAML_OKU.onbellegi_isit([g for g, _s, _p, _e in KATLAMA_FIKSTURLERI])
    ayristirici = YAML_OKU.ayristirici_adi()
    for girdi, beklenen, beklenen_prov, etiket in KATLAMA_FIKSTURLERI:
        taklit = _taklit_mantiksal_satirlari(girdi)
        t_satir = [t for t, _ in taklit]
        t_prov = [h for _, h in taklit]
        if t_satir != beklenen or t_prov != beklenen_prov:
            hata.append("KATLAMA FIKSTURU BOZUK — TAKLIT (fallback) KOLU (%s):\n"
                        "     beklenen satirlar: %r\n     gelen satirlar   : %r\n"
                        "     beklenen provenans: %r\n     gelen provenans   : %r\n"
                        "     -> taklit govdesi (_taklit_run_bloklari / _blok_provenans) "
                        "no-op/ters yapilmis olabilir. Bu kol HICBIR YAML ayristiricisi "
                        "olmayan ortamda TEK karar mercii olur."
                        % (etiket, beklenen, t_satir, beklenen_prov, t_prov))
        if ayristirici is None:
            continue
        gercek = _ayristirici_mantiksal_satirlari(girdi)
        if gercek is None:
            hata.append("KATLAMA FIKSTURU OLCULEMEDI — AYRISTIRICI KOLU (%s): ortamda "
                        "%s VAR ama fikstur ayristirilamadi -> fikstur metni bozulmus "
                        "olabilir (fail-closed)." % (etiket, ayristirici))
            continue
        g_satir = [t for t, _ in gercek]
        g_prov = [h for _, h in gercek]
        if g_satir != beklenen or g_prov != beklenen_prov:
            hata.append("KATLAMA FIKSTURU BOZUK — GERCEK AYRISTIRICI KOLU (%s, %s):\n"
                        "     beklenen satirlar: %r\n     gelen satirlar   : %r\n"
                        "     beklenen provenans: %r\n     gelen provenans   : %r\n"
                        "     -> _ayristirici_run_bloklari()/_bloklardan_mantiksal() "
                        "govdesi ya da tools/yaml-oku.py bozulmus olabilir."
                        % (etiket, ayristirici, beklenen, g_satir,
                           beklenen_prov, g_prov))
        if gercek != taklit:
            hata.append("KOL SAPMASI (%s, %s): TAKLIT kolu ile GERCEK AYRISTIRICI kolu "
                        "AYNI girdide FARKLI hukum veriyor.\n     taklit: %r\n"
                        "     gercek: %r\n     -> taklidin her sapmasi KUSURDUR: "
                        "ayristiricisiz ortamda kapi bu sapmayla karar verir."
                        % (etiket, ayristirici, taklit, gercek))
    # 🔴 KOL SECIMI NOBETI: ayristirici VARKEN hukmu GERCEKTEN o vermeli. Dagitici
    # (_mantiksal_yaml_satirlari) "daima taklit" haline getirilirse butun fiksturler yine
    # gecerdi (iki kol fikstur kumesinde esit) — bu iddia o sessiz gerilemeyi yakalar.
    if ayristirici is not None and KATLAMA_FIKSTURLERI:
        _mantiksal_yaml_satirlari(KATLAMA_FIKSTURLERI[0][0])
        if ayristirici_kolu() != ayristirici:
            hata.append("KOL SECIMI BOZUK: ortamda GERCEK ayristirici (%s) VAR ama hukmu "
                        "%r kolu verdi -> PARSER-FIRST dagiticisi kisa devre edilmis. "
                        "GERI KOY." % (ayristirici, ayristirici_kolu()))
    return hata


# ---- TETIK / BEYAN / ALT KUME FIKSTURLERI (BOLUM A + B) --------------------
# 🔴 UC AYRI TABLO, UC AYRI KACIS YOLU:
#   TETIK  -> tetik_sinifi() no-op ("daima OTOMATIK" / "daima ELLE") yapilirsa
#             kapsam ya sessizce genisler (sahte-YESIL) ya tumuyle kapanir.
#   BEYAN  -> beyanlari_ayikla() "daima bos liste" doner ve BOLUM B TAMAMEN olur;
#             ya da "cok genis" olur ve KENDI dokumantasyonunu beyan sanir.
#   UCTAN UCA -> denetle()'nin alt kume kollari (kapsanmis / muaf / kosmuyor /
#             bayat) yon degistirir.
_TF_JOBS = "jobs:\n  x:\n    runs-on: ubuntu-latest\n"
TETIK_FIKSTURLERI = (
    # (yaml_metni, beklenen_sinif, beklenen_tetikler, etiket)
    ("on: push\n" + _TF_JOBS, SINIF_OTOMATIK, {"push"},
     "SKALAR yazim (`on: push`) -> OTOMATIK"),
    ("on: [push, workflow_dispatch]\n" + _TF_JOBS, SINIF_OTOMATIK,
     {"push", "workflow_dispatch"}, "DIZI yazim -> OTOMATIK"),
    ("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n" + _TF_JOBS,
     SINIF_OTOMATIK, {"push", "workflow_dispatch"}, "ESLEME yazim -> OTOMATIK"),
    ("on:\n  schedule:\n    - cron: \"7,22,37,52 * * * *\"\n  workflow_dispatch:\n"
     + _TF_JOBS, SINIF_OTOMATIK, {"schedule", "workflow_dispatch"},
     "🔴 CRON (schedule) OTOMATIKTIR — bu ayrim olmadan cron'da GERCEKTEN kosan "
     "cagrilar 'hic kosmuyor' gorunuyordu (BOLUM A kok kusuru)"),
    ("on:\n  workflow_dispatch:\n    inputs:\n      a:\n        required: false\n"
     + _TF_JOBS, SINIF_ELLE, {"workflow_dispatch"},
     "🔴 YALNIZ workflow_dispatch -> ELLE (kimse tetiklemezse HIC kosmaz)"),
    ("on:\n  repository_dispatch:\n    types: [x]\n" + _TF_JOBS, SINIF_ELLE,
     {"repository_dispatch"}, "YALNIZ repository_dispatch -> ELLE"),
    ('"on":\n  push:\n    branches: [main]\n' + _TF_JOBS, SINIF_OTOMATIK, {"push"},
     "TIRNAKLI `\"on\":` anahtari da taninmali"),
    ("name: tetiksiz\n" + _TF_JOBS, SINIF_BELIRSIZ, None,
     "`on:` YOK -> BELIRSIZ (kapsam acisindan ELLE gibi; sahte-YESIL yonu KAPALI)"),
    ("on: [push\n" + _TF_JOBS, SINIF_BELIRSIZ, None,
     "AYRISTIRMA HATASI -> BELIRSIZ (taklit/tahmin URETILMEZ)"),
    ("- bu bir dizi\n- kok esleme degil\n", SINIF_BELIRSIZ, None,
     "kok ESLEME degil -> BELIRSIZ"),
    # ---- O1: "AYRISTIRICI BASARILI AMA TETIK KUMESI BOS/ANLAMSIZ" -------------
    # 🔴 BU YONU HICBIR FIKSTUR TUTMUYORDU: curutucunun N11 mutanti IKI KOLDA DA
    # YESIL gecti. Bos kume -> ELLE_TETIKLER farki bos -> tuketici OTOMATIK sayardi.
    ("on:\n  # push:\n" + _TF_JOBS, SINIF_BELIRSIZ, None,
     "🔴 TETIKLERI YORUMA ALINMIS (`on:` altinda yalniz `# push:`) -> tetik kumesi "
     "BOS -> BELIRSIZ. ONCE: {''} -> OTOMATIK (SAHTE-YESIL; GitHub bu akisi HIC "
     "kosturmaz, icindeki her cagri 'kapsanmis' sayilirdi)"),
    ("on: ''\n" + _TF_JOBS, SINIF_BELIRSIZ, None,
     "`on: ''` (BOS SKALAR) -> BELIRSIZ (ayni sinif)"),
    ("t: &t\n  push:\n    branches: [main]\non:\n  <<: *t\n" + _TF_JOBS,
     SINIF_BELIRSIZ, None,
     "YAML MERGE ANAHTARI (`<<: *t`) -> jeton '<<' gecerli olay adi DEGIL -> BELIRSIZ"),
    ("on:\n  workflow_call:\n" + _TF_JOBS, SINIF_ELLE, {"workflow_call"},
     "🔴 YALNIZ `workflow_call` -> ELLE: baska bir is akisi CAGIRMADAN kosmaz, "
     "kendi basina hicbir olayla tetiklenmez"),
    # ---- O3: IKI KOL PARITESI (alias + cok-belgeli) --------------------------
    ("t: &t\n  - push\non: *t\n" + _TF_JOBS, SINIF_OTOMATIK, {"push"},
     "🔴 ALIAS (`on: *t`, anchor=[push]) -> OTOMATIK. ONCE KOL SAPMASIYDI: "
     "psych ELLE / pyyaml OTOMATIK ([[ikiz-tanim-sessiz-ayrisma]])"),
    ("t: &t\n  push:\n    branches: [main]\non: *t\n" + _TF_JOBS, SINIF_OTOMATIK,
     {"push"}, "ALIAS ESLEMESI (`on: *t`) -> OTOMATIK (ayni kol sapmasi)"),
    ("on: push\n" + _TF_JOBS + "---\nbaska: belge\n", SINIF_BELIRSIZ, None,
     "🔴 COK BELGELI (`---`) -> IKI KOLDA da BELIRSIZ (fail-closed). ONCE: "
     "psych ilk belgeyi sessizce okuyup ELLE, pyyaml ComposerError ile BELIRSIZ"),
    # ---- P4: curutucu 2. turunun 3 SAPAN girdisi ----------------------------
    ("on: *t\nt: &t\n  - push\n" + _TF_JOBS, SINIF_BELIRSIZ, None,
     "🔴 ILERI ALIAS (alias anchor'dan ONCE) -> BELIRSIZ. YAML'da ileri referans "
     "TANIMSIZDIR; PyYAML ComposerError atar. ONCE psych tum belgeyi tarayip "
     "cozuyordu -> pyyaml BELIRSIZ / psych OTOMATIK KOL SAPMASI"),
    ("on: *t\nt: &t\n  push:\n    branches: [main]\n" + _TF_JOBS, SINIF_BELIRSIZ, None,
     "ILERI ALIAS (esleme anchor'i) -> BELIRSIZ (ayni sapma)"),
    ("﻿on: push\n" + _TF_JOBS, SINIF_OTOMATIK, {"push"},
     "🔴 BOM ONEKLI `on: push` -> OTOMATIK. YAML akis basinda BOM'a IZIN VERIR; "
     "PyYAML yutar, psych YUTMAZDI -> psych ortaminda TEK BOM'lu akis 125 dosyayi "
     "KAPSAMSIZ yapip YERELDE rc=1 uretiyordu, CI'da (pyyaml) YESIL. BOM artik "
     "TEK KAYNAKTA (`_bom_sil`) iki kolun ONUNDE siliniyor"),
)

# 🔴 YER TUTUCU DISIPLINI: asagidaki fiksturlerde GERCEK beyan satirlari `_BY_ISARET`
# uzerinden URETILIR; kaynak metne harfiyen yazilmaz. Boylece bu tablo, kendisi
# kesfedilen bir dosyada (bu dosya `-test.py`) yasarken bile KENDI dosyasinda gercek
# bir beyan URETMEZ ([[nobetci-kendi-dosyasinda-sizinti]]).
_BY_ISARET = "#"
_BY_JS = "//"
_BY_ET = BEYAN_ETIKETI + ":"
BEYAN_FIKSTURLERI = (
    # (metin, beklenen_bayraklar, etiket)
    ("%s %s --alfa\n" % (_BY_ISARET, _BY_ET), ["--alfa"],
     ".py yorumu (`#`) ile beyan"),
    ("%s %s --alfa\n" % (_BY_JS, _BY_ET), ["--alfa"],
     ".js yorumu (`//`) ile beyan"),
    ("      %s   %s   --alfa   serbest aciklama\n" % (_BY_ISARET, _BY_ET), ["--alfa"],
     "satir basi bosluk + jetondan sonra SERBEST aciklama"),
    ("%s %s --alfa\nkod\n%s %s --beta\n" % (_BY_ISARET, _BY_ET, _BY_ISARET, _BY_ET),
     ["--alfa", "--beta"], "bir dosyada BIRDEN COK beyan"),
    ("%s %s --alfa\n%s %s --alfa\n" % (_BY_ISARET, _BY_ET, _BY_ISARET, _BY_ET),
     ["--alfa"], "ayni bayrak iki kez -> TEK kayit"),
    ("%s %s <bayrak>\n" % (_BY_ISARET, _BY_ET), [],
     "🔴 DOC BICIMI (yer tutucu) BEYAN SAYILMAZ — kendi dokumantasyonunu kural "
     "sanma tuzagi ([[nobetci-kendi-dosyasinda-sizinti]])"),
    ("%s %s alfa\n" % (_BY_ISARET, _BY_ET), [],
     "`-`+`-` ile BASLAMAYAN jeton beyan SAYILMAZ"),
    ("kod = 1  %s %s --alfa\n" % (_BY_ISARET, _BY_ET), [],
     "SATIR BASINDA olmayan (kod satirinin sonundaki) yorum beyan SAYILMAZ"),
    ("%s %s\n" % (_BY_ISARET, _BY_ET), [],
     "etiket var ama JETON YOK -> beyan SAYILMAZ"),
    # ---- O9: SONDAKI NOKTALAMA -----------------------------------------------
    # Olculdu: virgullu yazim `--alfa,` jetonu uretiyordu; o jeton dosya metninde
    # ASLA gecmedigi icin curume kurali SAHTE-KIRMIZI yakiyordu (yayin durur).
    ("%s %s --alfa, --beta\n" % (_BY_ISARET, _BY_ET), ["--alfa"],
     "🔴 VIRGULLU yazim -> sondaki noktalama TEMIZLENIR (`--alfa,` DEGIL `--alfa`); "
     "ikinci jeton beyan SAYILMAZ (satirda TEK beyan kurali korunur)"),
    ("%s %s --alfa.\n" % (_BY_ISARET, _BY_ET), ["--alfa"],
     "cumle sonu noktasi TEMIZLENIR"),
)

# ---- UCTAN UCA ALT KUME FIKSTURLERI ----------------------------------------
# denetle()'yi SENTETIK envanterle cagirir: (akislar, kesif, dosya_metinleri,
# alt_kume_izin) -> beklenen exit kodu + rapor metninde beklenen/beklenmeyen izler.
# GERCEK deploy.yml'e ve gercek dosya agacina BAGIMSIZDIR (zzz-sentetik-* yollari).
_AK_YOL = "tools/zzz-sentetik-test.py"
_AK_CAGRI_SADE = "python3 " + _AK_YOL
_AK_CAGRI_ALFA = _AK_CAGRI_SADE + " --alfa"


def _ak_akis(komut, sinif=SINIF_OTOMATIK, yol=".github/workflows/zzz-sentetik.yml"):
    return (yol, "      - name: sentetik\n        run: %s\n" % komut, sinif)


def _ak_metin(*bayraklar, **kw):
    """Sentetik dosya metni: istenen beyan satirlari + bayrak jetonlarinin gectigi govde."""
    ek = kw.get("govde", "")
    satirlar = ["%s %s %s" % (_BY_ISARET, _BY_ET, b) for b in bayraklar]
    return "\n".join(satirlar) + "\n" + ek + "\n"


_AK_TEMEL_AKIS = [_ak_akis(_AK_CAGRI_ALFA)]
ALT_KUME_FIKSTURLERI = (
    # (akislar, kesif, dosya_metinleri, alt_kume_izin, beklenen_kod,
    #  beklenen_izler, beklenmeyen_izler, etiket)
    (_AK_TEMEL_AKIS, [_AK_YOL], {_AK_YOL: _ak_metin("--alfa")}, {}, 0,
     ("Beyan edilen alt kume  : 1  (kapsanan 1",), ("KOSMUYOR",),
     "POZITIF: beyan edilen alt kume OTOMATIK is akisinda kosuyor -> YESIL"),
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL], {_AK_YOL: _ak_metin("--alfa")}, {}, 1,
     ("BEYAN EDILEN ALT KUME KOSMUYOR", "--alfa"), (),
     "(a) alt kumenin CAGRISI SILINDI (bayraksiz cagri kaldi) -> KIRMIZI"),
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL],
     {_AK_YOL: _ak_metin("--beta")}, {}, 1,
     ("BEYAN EDILEN ALT KUME KOSMUYOR", "--beta"), (),
     "(b) beyan VAR, bayrak HICBIR yerde kosmuyor -> KIRMIZI"),
    (_AK_TEMEL_AKIS, [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa", govde='ap.add_argument("--yeni-modifikator")')},
     {}, 0, ("SONUC: YESIL",), ("KOSMUYOR",),
     "🔴 (c) BEYAN EDILMEYEN yeni modifikator bayrak -> YESIL (yanlis-kirmizi YOK). "
     "BU VAKA SILINEMEZ: kapi continue-on-error'SUZ kosar."),
    ([_ak_akis(_AK_CAGRI_ALFA, SINIF_ELLE)], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, 1,
     ("BEYAN EDILEN ALT KUME KOSMUYOR", "YALNIZ ELLE'de kosulan : 1"), (),
     "(e) alt kume YALNIZ ELLE tetiklenen is akisinda kosuyor -> KIRMIZI"),
    ([_ak_akis(_AK_CAGRI_ALFA, SINIF_OTOMATIK,
               ".github/workflows/zzz-cron.yml")], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, 0, ("SONUC: YESIL",), ("KOSMUYOR",),
     "(f) alt kume CRON (OTOMATIK) is akisinda kosuyor -> YESIL"),
    (_AK_TEMEL_AKIS, [_AK_YOL],
     {_AK_YOL: "%s %s <bayrak>\n--alfa\n" % (_BY_ISARET, _BY_ET)}, {}, 0,
     ("Beyan edilen alt kume  : 0",), ("KOSMUYOR",),
     "(g) DOC BICIMI beyan SAYILMAZ -> YESIL"),
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL], {_AK_YOL: _ak_metin("--beta")},
     {(_AK_YOL, "--beta"): "   "}, 1,
     ("GEREKCESIZ alt kume izni",), (),
     "(h) izin girisi BOS gerekce -> KIRMIZI"),
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL],
     {_AK_YOL: "kod\n"}, {(_AK_YOL, "--beta"): "olculmus gerekce"}, 1,
     ("BAYAT alt kume izni", "METNINDE HIC"), (),
     "(i) izin girisinin bayragi dosya metninden KALDIRILDI -> KIRMIZI (BAYAT)"),
    (_AK_TEMEL_AKIS, [_AK_YOL], {_AK_YOL: _ak_metin("--alfa")},
     {(_AK_YOL, "--alfa"): "olculmus gerekce"}, 1,
     ("BAYAT alt kume izni", "ARTIK OTOMATIK"), (),
     "(j) izin girisindeki alt kume ASLINDA KOSUYOR -> KIRMIZI (BAYAT)"),
    ([_ak_akis(_AK_CAGRI_ALFA + " ; echo bitti"),
      (".github/workflows/zzz-ilgisiz.yml",
       "      - name: alakasiz rutin adim\n        run: echo merhaba\n",
       SINIF_OTOMATIK)],
     [_AK_YOL], {_AK_YOL: _ak_metin("--alfa", govde="# alakasiz rutin yorum")}, {}, 0,
     ("SONUC: YESIL",), ("KOSMUYOR", "BAYAT alt kume"),
     "🔴 (k) KONTROL MUTANTI — konuyla ILGISIZ rutin duzenleme (alakasiz `- name:` "
     "adimi + test dosyasina alakasiz yorum) -> YESIL. BU VAKA SILINEMEZ "
     "([[fikstur-degeri-mutasyon-koru]]: kontrol mutanti olmadan olcum korelir)."),
    ([_ak_akis(_AK_CAGRI_ALFA, SINIF_BELIRSIZ)], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, 1,
     ("BEYAN EDILEN ALT KUME KOSMUYOR", "TETIGI COZULEMEDI"), (),
     "BELIRSIZ tetik ELLE gibi ele alinir (kapsam SAYILMAZ) + UYARI satiri basilir"),
    # ---- O2: FAIL-OPEN'IN KAPSAMI SATIR DUZEYINE INDIRILDI + GORUNUR ---------
    ([_ak_akis(_AK_CAGRI_SADE + ' --x "acik-tirnak')], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, 1,
     ("BEYAN EDILEN ALT KUME KOSMUYOR", "--alfa"), ("kapsanan 1",),
     "🔴 (O2-a) JETONLANAMAYAN satir bayragi ICERMIYOR -> alt kume KAPSANMIS "
     "SAYILMAZ. ONCE: tek bozuk satir DOSYANIN TUM alt kumelerini kapsiyordu; "
     "gercek cagri silinip bu satir konunca kapi rc=0 verip 'kapsanan 2' YAZIYORDU "
     "(aktif YANLIS BEYAN, tek satir OLCULEMEDI izi yoktu)."),
    ([_ak_akis(_AK_CAGRI_SADE + ' --alfa "acik-tirnak')], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, 0,
     ("ALT KUME OLCULEMEDI -> kapsanmis SAYILDI (fail-open)", "--alfa"), ("KOSMUYOR",),
     "(O2-b) JETONLANAMAYAN satir bayragi ICERIYOR -> fail-open KORUNUR (spec B2) "
     "ama artik GORUNUR bir OLCULEMEDI satiri basar (sessiz DEGIL)"),
    # ---- O4: DOSYA DUZEYINDE BELIRSIZ -> KAPSAM SAYILMAZ ---------------------
    ([_ak_akis(_AK_CAGRI_SADE, SINIF_BELIRSIZ)], [_AK_YOL],
     {_AK_YOL: "kod\n"}, {}, 1,
     ("KAPSAMSIZ", "TETIGI COZULEMEDI"), (),
     "🔴 (O4) DOSYA duzeyi BELIRSIZ: beyan YOK, yalniz BELIRSIZ tetikli akis kosuyor "
     "-> KAPSAMSIZ (KIRMIZI). Bu yonu hicbir fikstur tutmuyordu; curutucunun N13 "
     "mutanti (`kosulan_coklu` BELIRSIZ'i OTOMATIK sayar) IKI KOLDA da YESIL gecti."),
    ([_ak_akis(_AK_CAGRI_SADE, SINIF_OTOMATIK)], [_AK_YOL],
     {_AK_YOL: "kod\n"}, {}, 0,
     ("SONUC: YESIL",), ("KAPSAMSIZ",),
     "(O4 KONTROL) ayni girdi OTOMATIK tetikle -> YESIL (fikstur cifti; tek yonlu "
     "olcum korelir)"),
    # ---- O6: GNU `--bayrak=deger` ------------------------------------------
    ([_ak_akis(_AK_CAGRI_SADE + " --alfa=1")], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, 0,
     ("Beyan edilen alt kume  : 1  (kapsanan 1",), ("KOSMUYOR",),
     "🔴 (O6) `--bayrak=deger` yazimi KAPSAR. ONCE: `--alfa=1` cagrisi `--alfa` "
     "beyanini kapsamiyordu -> SAHTE-KIRMIZI (tum ekibin yayini durur)"),
    # ---- O10: CURUME CAPASI JETON SINIRLI -----------------------------------
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL],
     {_AK_YOL: "ap.add_argument('--alfa-yeni')\n"},
     {(_AK_YOL, "--alfa"): "olculmus gerekce"}, 1,
     ("BAYAT alt kume izni", "METNINDE HIC"), (),
     "🔴 (O10) `--alfa` -> `--alfa-yeni` YENIDEN ADLANDIRMASI izni BAYAT yapar. "
     "ONCE: capa ALT-DIZE ariyordu, `--alfa` hala `--alfa-yeni` icinde gectigi icin "
     "giris 'taze' kaliyordu ve BAYAT kirmizisi HIC yanmiyordu (3 vakada olculdu)"),
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL],
     {_AK_YOL: "ap.add_argument('--alfa')\n"},
     {(_AK_YOL, "--alfa"): "olculmus gerekce"}, 0,
     ("SONUC: YESIL",), ("BAYAT alt kume",),
     "(O10 KONTROL) jeton GERCEKTEN duruyorsa giris TAZE kalir -> YESIL"),
    ([_ak_akis(_AK_CAGRI_SADE)], [_AK_YOL], {_AK_YOL: _ak_metin("--beta")},
     {(_AK_YOL, "--beta"): "OLCULMUS gerekce: sentetik"}, 0,
     ("Beyan edilen alt kume  : 1  (kapsanan 0 · muaf 1)",), ("KOSMUYOR",),
     "MUAF yolu: gerekceli izin girisi kapiyi YESIL birakir"),
)

# 🔴 P5 — "AYRISTIRICI YOK" HALININ UCTAN UCA FIKSTURLERI.
# Olculen AKTIF YANLIS BEYAN: ayristirici kapaliyken rapor DOSYA ekseninde dogru
# ("OLCULEMEDI", 0 KAPSAMSIZ satiri) davraniyor ama ALT KUME ekseninde
# "BEYAN EDILEN ALT KUME KOSMUYOR: shop/test/kabul.js --sema-paritesi" yaziyordu —
# oysa o alt kume CI'da BLOKLAYICI kosuyor. Ayrica O5 yamasini geri sarmak NOBETSIZDI.
# (akislar, kesif, dosya_metinleri, alt_kume_izin, ayristirici_yok, beklenen_kod,
#  beklenen_izler, beklenmeyen_izler, etiket)
AYRISTIRICI_YOK_FIKSTURLERI = (
    ([_ak_akis(_AK_CAGRI_ALFA, SINIF_BELIRSIZ)], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, True, 1,
     ("HICBIR GERCEK YAML AYRISTIRICISI YOK", "OLCULEMEDI"),
     ("KOSMUYOR", "KAPSAMSIZ"),
     "🔴 (P5) ayristirici YOK -> rc=1 KALIR (fail-closed) ama SEBEP dogru: tek okunur "
     "tani; alt kume ekseninde 'KOSMUYOR' DEMEZ, 'OLCULEMEDI' der; 125 anlamsiz "
     "KAPSAMSIZ satiri BASILMAZ"),
    ([_ak_akis(_AK_CAGRI_ALFA, SINIF_BELIRSIZ)], [_AK_YOL],
     {_AK_YOL: _ak_metin("--alfa")}, {}, False, 1,
     ("BEYAN EDILEN ALT KUME KOSMUYOR", "KAPSAMSIZ"),
     ("HICBIR GERCEK YAML AYRISTIRICISI YOK",),
     "(P5 KONTROL) ayristirici VARKEN ayni girdi normal hukmu verir — bayrak "
     "semantigi degistirmedigini kanitlar (tek yonlu olcum korelir)"),
)

TETIK_FIKSTUR_ASGARI = 20
BEYAN_FIKSTUR_ASGARI = 11
ALT_KUME_FIKSTUR_ASGARI = 20
AYRISTIRICI_YOK_FIKSTUR_ASGARI = 2
# Iki-kol girdi kumeleri de BOSALTILABILIR (sapma 0 sahte-yesili) -> tavan nobeti.
IKI_KOL_RUN_ASGARI = 9
IKI_KOL_EK_ASGARI = 9


def tetik_fikstur_kontrol_govdesi():
    """TETIK_FIKSTURLERI'ni olcer; (hata_satirlari) dondurur."""
    hata = []
    YAML_OKU.tetik_onbellegi_isit([g for g, _s, _t, _e in TETIK_FIKSTURLERI])
    for metin, beklenen_sinif, beklenen_tetik, etiket in TETIK_FIKSTURLERI:
        sinif, tetikler, _h = tetik_sinifi(metin)
        if sinif != beklenen_sinif or (beklenen_tetik is not None
                                       and tetikler != beklenen_tetik):
            hata.append("TETIK FIKSTURU BOZUK (%s): beklenen sinif=%s tetik=%r, "
                        "gelen sinif=%s tetik=%r -> tetik_sinifi()/yaml-oku "
                        "tetikleyiciler() govdesi no-op ya da ters yapilmis olabilir. "
                        "OTOMATIK'e kayan bir hata kapiyi SESSIZCE GEVSETIR "
                        "(sahte-YESIL); ELLE'ye kayan bir hata TUM ekibin yayinini "
                        "durdurur." % (etiket, beklenen_sinif, beklenen_tetik,
                                       sinif, tetikler))
    hata.extend(iki_kol_tetik_kontrol_govdesi())
    return hata


# 🔴 O3b — IKI KOLU FIILEN KARSILASTIRAN NOBETCI (KATLAMA_FIKSTURLERI deseninin aynisi).
# NEDEN GEREKTI: yaml-oku.py'nin yorumu "iki kol AYNI kumeyi dondurmek ZORUNDADIR
# (tuketicideki TETIK_FIKSTURLERI bunu kilitler)" DIYORDU ama KILITLEMIYORDU:
# TETIK_FIKSTURLERI yalniz O ANDA AKTIF kolda kosar (PyYAML varsa psych HIC cagrilmaz),
# yani iki kol HIC karsilastirilmiyordu. Olculdu (bagimsiz curutucu, 25 girdi): UC ayrisma.
# Ayrisma YEREL-KIRMIZI / CI-YESIL uretir — yani en pahali hata sinifi.
# OLCULEMEDI HALI SESSIZ GECMEZ: tek kol varsa "karsilastirma YAPILAMADI" satiri basilir
# (bloklamaz); sessiz "sapma yok" saymak bu nobetciyi OLU yapardi.
IKI_KOL_EK_GIRDILER = (
    "on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n" + _TF_JOBS,
    "t: &t\n  - push\n  - schedule\non: *t\n" + _TF_JOBS,
    "on:\n  <<: *yok\n" + _TF_JOBS,
    'on: "push"\n' + _TF_JOBS,
    "on:\n" + _TF_JOBS,
    # ---- P4: curutucunun 28 girdisinde SAPAN uc yazim -----------------------
    "on: *t\nt: &t\n  - push\n" + _TF_JOBS,                 # ILERI alias (dizi)
    "on: *t\nt: &t\n  push:\n    branches: [main]\n" + _TF_JOBS,  # ILERI alias (esleme)
    "\ufeffon: push\n" + _TF_JOBS,                          # BOM onekli
    "\ufeffon:\n  schedule:\n    - cron: \"7 * * * *\"\n" + _TF_JOBS,
)

# `run:` KOLUNUN iki-kol girdileri (P3). Curutucunun 4 yapisal ayrismasi + kontroller.
_RUN_ADIM = "jobs:\n  x:\n    steps:\n"
IKI_KOL_RUN_GIRDILERI = (
    _RUN_ADIM + "      - run: *c\n      - run: &c python3 tools/x.py --alfa\n",
    _RUN_ADIM + "      - run: *yok\n",
    _RUN_ADIM + "      - run: echo a\n---\nbaska: belge\n",
    "---\n---\n" + _RUN_ADIM + "      - run: echo a\n",
    _RUN_ADIM + "      - run: &c python3 tools/x.py --alfa\n      - run: *c\n",
    _RUN_ADIM + "      - run: echo a\n",
    "\ufeff" + _RUN_ADIM + "      - run: echo a\n",
    _RUN_ADIM + "      - run: |\n          python3 tools/x.py --alfa\n          echo bitti\n",
    _RUN_ADIM + "      - run: >\n          python3 tools/x.py\n          --alfa\n",
)


def iki_kol_girdi_kumesi():
    """(tetik_girdileri, run_girdileri) — IKI-KOL nobetcisinin TEK KAYNAK girdi kumesi.

    Nobetci ile rapor satiri AYNI kumeyi kullanmak ZORUNDA: ayrisirlarsa rapor
    "sapma 0" yazarken nobetci baska bir kumeyi olcer ([[kabul-araligi-karsilastirma-araligi]])."""
    return ([g for g, _s, _t, _e in TETIK_FIKSTURLERI] + list(IKI_KOL_EK_GIRDILER),
            list(IKI_KOL_RUN_GIRDILERI))


def iki_kol_tetik_kontrol_govdesi():
    """TETIK kolunda PyYAML ile psych'i AYNI girdilerde karsilastirir; (hata) dondurur."""
    girdiler, _run = iki_kol_girdi_kumesi()
    try:
        sapmalar, olculen_kol = YAML_OKU.iki_kol_tetik_sapmasi(girdiler)
    except Exception as e:  # noqa: BLE001 — nobetci kapiyi PATLATMAZ, konusur
        return ["IKI KOL KARSILASTIRMASI OLCULEMEDI: %s: %s" % (type(e).__name__, e)]
    if olculen_kol < 2:
        # BLOKLAMAZ ama GORUNUR (durum satiri raporda kalir; sessiz yesil YOK).
        return []
    return ["KOL SAPMASI (tetik, girdi #%d): PyYAML kolu %r, psych kolu %r -> AYNI "
            "girdide FARKLI tetik kumesi. Bu YEREL-KIRMIZI / CI-YESIL uretir "
            "([[ikiz-tanim-sessiz-ayrisma]]); iki kol TEK KAYNAKTAN turemeli."
            % (i, p, r) for i, p, r in sapmalar]


def iki_kol_run_kontrol_govdesi():
    """🔴 `run:` KOLUNDA PyYAML ile psych'i karsilastirir (P3); (hata) dondurur.

    KATLAMA_FIKSTURLERI TAKLIT ile GERCEK ayristiriciyi kiyaslar, pyyaml ile psych'i
    DEGIL. O bosluk olculdu: `RUBY_KAYNAK`'taki Alias korumasini geri saran mutant
    IKI ORTAMDA DA rc=0 YESIL kaliyordu (esdeger DEGIL — bir `run:` satiri kapsamdan
    SESSIZCE yok oluyordu)."""
    _tetik, girdiler = iki_kol_girdi_kumesi()
    try:
        sapmalar, olculen_kol = YAML_OKU.iki_kol_run_sapmasi(girdiler)
    except Exception as e:  # noqa: BLE001
        return ["IKI KOL RUN KARSILASTIRMASI OLCULEMEDI: %s: %s" % (type(e).__name__, e)]
    if olculen_kol < 2:
        return []
    return ["KOL SAPMASI (run, girdi #%d): PyYAML kolu %r, psych kolu %r -> AYNI girdide "
            "FARKLI `run:` blok kumesi. Bir icra satiri kapsamdan SESSIZCE dusebilir."
            % (i, p, r) for i, p, r in sapmalar]


def iki_kol_durum_satiri():
    """Raporda basilacak (bloklamayan) iki-kol olcum durumu — KUME BOYUTUYLA birlikte."""
    tetik, run = iki_kol_girdi_kumesi()
    try:
        t_sap, t_kol = YAML_OKU.iki_kol_tetik_sapmasi(tetik)
        r_sap, r_kol = YAML_OKU.iki_kol_run_sapmasi(run)
    except Exception as e:  # noqa: BLE001
        return "  🟡 IKI KOL PARITESI OLCULEMEDI: %s: %s" % (type(e).__name__, e)
    if min(t_kol, r_kol) < 2:
        return ("  🟡 IKI KOL PARITESI OLCULEMEDI: bu ortamda %d GERCEK kol var "
                "(karsilastirma icin 2 gerekir) — sapma YOK demek DEGILDIR" % t_kol)
    # 🔴 IDDIA KUME BOYUTUYLA BIRLIKTE BEYAN EDILIR: "sapma 0" tek basina, kume
    # kucuk/sabit oldugunda yaniltir (P4'te tam bu oldu).
    return ("  Iki kol paritesi       : tetik %d girdi · sapma %d | run %d girdi · sapma %d"
            % (len(tetik), len(t_sap), len(run), len(r_sap)))


def iki_kol_canlilik_kontrol_govdesi():
    """🔴 P1 — IKI-KOL NOBETCILERININ POZITIF CANLILIGI (SENTETIK SAPMA ENJEKSIYONU).

    AST kablosu CAGRININ SILINMESINI yakalar; GOVDENIN `return []` yapilmasini YAKALAMAZ
    (fonksiyon cagriliyor, hicbir sey demiyor). Olculdu: `iki_kol_tetik_kontrol_govdesi`
    govdesine tek satir `return []` koymak kapiyi rc=0 YESIL birakiyordu.
    Bu nobetci UYDURMA bir sapma enjekte eder ve govdenin KONUSMASINI SART kosar —
    `uyari_katmani_izole_kontrol_govdesi`'nin ariza-enjeksiyon deseniyle AYNI."""
    hata = []
    gercek_tetik = YAML_OKU.iki_kol_tetik_sapmasi
    gercek_run = YAML_OKU.iki_kol_run_sapmasi
    try:
        YAML_OKU.iki_kol_tetik_sapmasi = lambda m: ([(0, {"push"}, None)], 2)
        YAML_OKU.iki_kol_run_sapmasi = lambda m: ([(0, [(1, 1, 1, "x")], None)], 2)
        t = iki_kol_tetik_kontrol_govdesi()
        r = iki_kol_run_kontrol_govdesi()
        if not any("KOL SAPMASI" in s for s in t):
            hata.append(
                "IKI KOL TETIK NOBETCISI OLU: sentetik bir SAPMA enjekte edildi ama "
                "govde hicbir hata satiri uretmedi (gelen=%r) -> govde `return []` "
                "yapilmis olabilir. O halde pyyaml<->psych ayrismasi SESSIZ kalir ve "
                "YEREL-KIRMIZI / CI-YESIL uretir." % (t,))
        if not any("KOL SAPMASI" in s for s in r):
            hata.append(
                "IKI KOL RUN NOBETCISI OLU: sentetik SAPMA enjekte edildi ama govde "
                "konusmadi (gelen=%r) -> bir `run:` satirinin kapsamdan sessizce "
                "dusmesi GORULMEZ olur." % (r,))
        # NEGATIF YON: sapma YOKKEN hata URETMEMELI (yanlis-kirmizi yuzeyi acmasin).
        YAML_OKU.iki_kol_tetik_sapmasi = lambda m: ([], 2)
        YAML_OKU.iki_kol_run_sapmasi = lambda m: ([], 2)
        if iki_kol_tetik_kontrol_govdesi() or iki_kol_run_kontrol_govdesi():
            hata.append("IKI KOL NOBETCISI YANLIS-KIRMIZI: sapma YOKKEN hata uretti.")
        # OLCULEMEDI YONU: tek kol varken BLOKLAMAMALI (sessiz degil — durum satiri konusur).
        YAML_OKU.iki_kol_tetik_sapmasi = lambda m: ([(0, {"push"}, None)], 1)
        YAML_OKU.iki_kol_run_sapmasi = lambda m: ([(0, [], None)], 1)
        if iki_kol_tetik_kontrol_govdesi() or iki_kol_run_kontrol_govdesi():
            hata.append("IKI KOL NOBETCISI TEK KOLDA BLOKLUYOR: karsilastirma "
                        "YAPILAMAZKEN kirmizi yakmak tum ekibin yayinini durdurur.")
    except Exception as e:  # noqa: BLE001
        hata.append("IKI KOL CANLILIK NOBETCISI OLCULEMEDI: %s: %s"
                    % (type(e).__name__, e))
    finally:
        YAML_OKU.iki_kol_tetik_sapmasi = gercek_tetik
        YAML_OKU.iki_kol_run_sapmasi = gercek_run
    return hata


# Durum satirinin KABUL EDILEN iki bicimi (F5: sabit metin dondurmek de bir mutasyondur).
IKI_KOL_DURUM_RE = re.compile(
    r"^\s*Iki kol paritesi\s+: tetik (\d+) girdi · sapma (\d+) \| run (\d+) girdi · sapma (\d+)\s*$")
IKI_KOL_OLCULEMEDI_RE = re.compile(r"^\s*🟡 IKI KOL PARITESI OLCULEMEDI:")


def tutarlilik_kontrolu(satirlar, hatalar, kontroller):
    """🔴 F1/F5 — RAPOR METNI ile HUKUM CELISEMEZ.

    OLCULEN EN KOTU VAKA (DA4): gercek bir kol sapmasi VARKEN rapor satiri `sapma 3`
    yaziyor ve kapi `SONUC: YESIL ✅` veriyordu — olcum YAPILIYOR, BASILIYOR, HUKME
    GIRMIYOR. Bu nobetci o celiskiyi BLOKLAYICI olarak yakalar; boylece `hata.extend(x())`
    -> `x()` sinifindaki TUM sonuc-yutma mutasyonlari (iki-kol ekseninde) kirmizi yanar.

    Ayrica durum satirinin BICIMI dogrulanir: sabit/serbest metin dondurmek (A6) da
    bir olcum kaybidir ve buradan yakalanir."""
    hata = []
    durum = [s for s in satirlar
             if IKI_KOL_DURUM_RE.match(s) or IKI_KOL_OLCULEMEDI_RE.match(s)]
    if len(durum) != 1:
        hata.append(
            "IKI KOL DURUM SATIRI KAYIP/BOZUK: beklenen BICIMDE tam 1 satir olmali, %d "
            "bulundu -> `iki_kol_durum_satiri()` sabit metin donduruyor ya da cagrisi "
            "dusmus olabilir; rapor 'olctum' der gibi gorunup HICBIR SEY olcmez."
            % len(durum))
        return hata
    m = IKI_KOL_DURUM_RE.match(durum[0])
    if not m:
        return hata  # OLCULEMEDI bicimi: sapma iddiasi YOK, celiski de YOK.
    t_sapma, r_sapma = int(m.group(2)), int(m.group(4))
    if (t_sapma or r_sapma) and kontroller:
        if not any("KOL SAPMASI" in h for h in hatalar):
            hata.append(
                "CELISKI — RAPOR 'sapma %d/%d' DIYOR AMA HUKUM TEMIZ: iki-kol sapmasi "
                "OLCULMUS ve BASILMIS ama hata listesine GIRMEMIS -> nobetcinin sonucu "
                "YUTULMUS (`hata.extend(x())` yerine `x()`). Olcum hukme girmiyorsa "
                "nobetci OLUDUR." % (t_sapma, r_sapma))
    return hata


def iki_kol_govde_kontrol_govdesi():
    """🔴 F2 — KARSILASTIRMA GOVDESININ KENDISI olculur (nobetcinin olctugu govde nobetsizdi).

    `iki_kol_canlilik_kontrol_govdesi()` tam bu iki fonksiyonu MONKEYPATCH ettigi icin
    onlarin GOVDESINI yapisal olarak OLCEMEZ. Olculdu: `if p_kume != r_kume:` satirini
    `if False and ...` yapan mutant psych'te rc=1 verirken **pyyaml'da rc=0** birakiyor ve
    rapor `sapma 0` YAZIYORDU (gercek BOM sapmasi varken AKTIF YANLIS BEYAN).

    YONTEM: KOL FONKSIYONLARI (bir alt katman) monkeypatch'lenir, `iki_kol_*_sapmasi`
    GERCEK govdesiyle kosar. Boylece `!=` karsilastirmasi FIILEN olculur."""
    hata = []
    y = YAML_OKU
    saklanan = (y.kollar_mevcut, y._pyyaml_tetikler, y._psych_tetikler_toplu,
                y._pyyaml_bloklar, y._psych_bloklar_toplu)
    try:
        y.kollar_mevcut = lambda: (True, True)
        # --- TETIK: kollar AYRI hukum veriyor -> SAPMA GORULMELI ---
        y._pyyaml_tetikler = lambda m: ({"push"}, None)
        y._psych_tetikler_toplu = lambda ms: [(None, "hata")] * len(ms)
        sap, kol = YAML_OKU.iki_kol_tetik_sapmasi(["a", "b"])
        if kol != 2 or len(sap) != 2:
            hata.append("IKI KOL TETIK GOVDESI OLU: kollar AYRI hukum verirken sapma "
                        "GORULMEDI (kol=%r sapma=%r) -> `!=` karsilastirmasi no-op "
                        "yapilmis olabilir; gercek ayrisma SESSIZ kalir." % (kol, sap))
        # --- TETIK: kollar AYNI -> SAPMA OLMAMALI (yanlis-kirmizi yuzeyi) ---
        y._psych_tetikler_toplu = lambda ms: [({"push"}, None)] * len(ms)
        sap, _kol = YAML_OKU.iki_kol_tetik_sapmasi(["a", "b"])
        if sap:
            hata.append("IKI KOL TETIK GOVDESI YANLIS-KIRMIZI: kollar AYNI hukum "
                        "verirken sapma bildirdi (%r)." % (sap,))
        # --- RUN: kollar AYRI -> SAPMA GORULMELI ---
        y._pyyaml_bloklar = lambda m: ([(1, 1, 1, "x")], None)
        y._psych_bloklar_toplu = lambda ms: [(None, "hata")] * len(ms)
        sap, kol = YAML_OKU.iki_kol_run_sapmasi(["a", "b"])
        if kol != 2 or len(sap) != 2:
            hata.append("IKI KOL RUN GOVDESI OLU: kollar AYRI blok kumesi verirken sapma "
                        "GORULMEDI (kol=%r sapma=%r) -> bir `run:` satirinin kapsamdan "
                        "sessizce dusmesi FARK EDILMEZ." % (kol, sap))
        # --- RUN: kollar AYNI -> SAPMA OLMAMALI ---
        y._psych_bloklar_toplu = lambda ms: [([(1, 1, 1, "x")], None)] * len(ms)
        sap, _kol = YAML_OKU.iki_kol_run_sapmasi(["a", "b"])
        if sap:
            hata.append("IKI KOL RUN GOVDESI YANLIS-KIRMIZI: kollar AYNI blok kumesi "
                        "verirken sapma bildirdi (%r)." % (sap,))
        # --- TEK KOL: karsilastirma YAPILAMAZ, sapma UYDURULMAMALI ---
        y.kollar_mevcut = lambda: (True, False)
        sap, kol = y.iki_kol_tetik_sapmasi(["a"])
        if kol == 2 or sap:
            hata.append("IKI KOL GOVDESI TEK KOLDA HUKUM URETTI (kol=%r sapma=%r) -> "
                        "olculemeyen sey 'olculdu' sayiliyor." % (kol, sap))
    except Exception as e:  # noqa: BLE001
        hata.append("IKI KOL GOVDE NOBETCISI OLCULEMEDI: %s: %s" % (type(e).__name__, e))
    finally:
        (y.kollar_mevcut, y._pyyaml_tetikler, y._psych_tetikler_toplu,
         y._pyyaml_bloklar, y._psych_bloklar_toplu) = saklanan
    return hata


# F3: girdi kumesinin AYIRT EDICI oldugunu civileyen ICERIK capalari. Salt SAYI capasi
# yetmez — olculdu: `iki_kol_girdi_kumesi()` AYNI UZUNLUKTA NOTR girdi dondurunce tavan
# nobeti YESIL kaliyordu ([[hukum-yanlis-birimde]]: tablo sayiliyordu, FONKSIYON CIKTISI degil).
IKI_KOL_TETIK_CAPALARI = (
    ("﻿", "BOM onekli girdi"),
    ("on: *t\nt: &t", "ILERI alias girdisi"),
    ("---", "cok-belgeli girdi"),
    ("workflow_call", "workflow_call girdisi"),
)
IKI_KOL_RUN_CAPALARI = (
    ("run: *c", "alias'li run girdisi"),
    ("run: *yok", "TANIMSIZ alias girdisi"),
    ("---", "cok-belgeli run girdisi"),
    ("﻿", "BOM onekli run girdisi"),
)


def iki_kol_girdi_kumesi_kontrol_govdesi():
    """🔴 F3 — asgari kontrol FONKSIYONUN CIKTISI uzerinde + kume AYIRT EDICI olmali."""
    hata = []
    try:
        tetik, run = iki_kol_girdi_kumesi()
    except Exception as e:  # noqa: BLE001
        return ["IKI KOL GIRDI KUMESI OLCULEMEDI: %s: %s" % (type(e).__name__, e)]
    for ad, kume, asgari in (("tetik", tetik, len(TETIK_FIKSTURLERI) + IKI_KOL_EK_ASGARI),
                             ("run", run, IKI_KOL_RUN_ASGARI)):
        if len(kume) < asgari:
            hata.append("IKI KOL GIRDI KUMESI KUCULMUS (%s): fonksiyon %d girdi "
                        "donduruyor, EN AZ %d olmali -> 'sapma 0' iddiasi kume "
                        "kadar guclu; kume kucultulurse iddia SESSIZCE zayiflar."
                        % (ad, len(kume), asgari))
    for kume, capalar, ad in ((tetik, IKI_KOL_TETIK_CAPALARI, "tetik"),
                              (run, IKI_KOL_RUN_CAPALARI, "run")):
        govde = "\n".join(kume)
        for capa, etiket in capalar:
            if capa not in govde:
                hata.append("IKI KOL GIRDI KUMESI AYIRT EDICILIGINI KAYBETMIS (%s): %s "
                            "kumede YOK -> kume AYNI UZUNLUKTA notr girdilerle "
                            "degistirilmis olabilir; sayi capasi bunu GORMEZ "
                            "([[hukum-yanlis-birimde]])." % (ad, etiket))
    return hata


def ayristirici_yok_kontrol_govdesi():
    """AYRISTIRICI_YOK_FIKSTURLERI'ni denetle() UZERINDEN olcer (P5); (hata) dondurur."""
    hata = []
    for (akislar, kesif, metinler, izin, yok, beklenen_kod, beklenen_izler,
         beklenmeyen_izler, etiket) in AYRISTIRICI_YOK_FIKSTURLERI:
        kod, satirlar = denetle("", list(kesif), {}, kontroller=False,
                                akislar=list(akislar), dosya_metinleri=dict(metinler),
                                alt_kume_izin=dict(izin), ayristirici_yok=yok)
        rapor = "\n".join(satirlar)
        eksik = [b for b in beklenen_izler if b not in rapor]
        fazla = [b for b in beklenmeyen_izler if b in rapor]
        if kod != beklenen_kod or eksik or fazla:
            hata.append("AYRISTIRICI-YOK FIKSTURU BOZUK (%s): beklenen exit %d, gelen %d; "
                        "eksik iz=%r; OLMAMASI gereken iz=%r -> `ayristirici_yok` dali "
                        "no-op yapilmis ya da alt kume ekseni yine 'KOSMUYOR' diyor "
                        "olabilir (AKTIF YANLIS BEYAN)."
                        % (etiket, beklenen_kod, kod, eksik, fazla))
    return hata


def okuma_dayanikliligi_kontrol_govdesi():
    """🔴 P2a — `dosya_metinleri_oku()` OKUNAMAYAN dosyada PATLAMAMALI, SAYMALI.

    OLCULEN OLU NOBETCI: `except Exception` -> `except OSError` mutanti kapiyi rc=0
    YESIL birakiyordu. Islev DOGRUYDU (UTF-8 disi baytli dosyada "okunamayan: 1"
    basiyordu) ama KILIT yoktu.

    IZLENEN AGACA DOKUNULMAZ: fikstur GECICI dizinde kurulur ve `ROOT` gecici olarak
    oraya cevrilir (monkeypatch); kesif/gercek dosyalar etkilenmez."""
    global ROOT
    hata = []
    gecici = tempfile.mkdtemp(prefix="pruvo-okuma-fikstur-")
    eski_kok = ROOT
    try:
        # (1) UTF-8 OLMAYAN bayt -> UnicodeDecodeError (OSError DEGIL)
        bozuk = "zzz-sentetik-utf8-disi.py"
        with open(os.path.join(gecici, bozuk), "wb") as f:
            f.write(b"# kod\n\xff\xfe gecersiz utf-8\n")
        # (2) HIC OLMAYAN dosya -> FileNotFoundError (OSError)
        yok = "zzz-sentetik-yok.py"
        # (3) OKUNABILIR kontrol -> listeye GIRMELI
        saglam = "zzz-sentetik-saglam.py"
        with open(os.path.join(gecici, saglam), "w", encoding="utf-8") as f:
            f.write("# kod\n")
        ROOT = gecici
        metinler, okunamayan = dosya_metinleri_oku([bozuk, yok, saglam])
        okunamayan_yollar = sorted(y for y, _s in okunamayan)
        if okunamayan_yollar != sorted([bozuk, yok]):
            hata.append(
                "OKUMA DAYANIKLILIGI FIKSTURU BOZUK: okunamayan=%r bekleniyordu, %r "
                "geldi -> `dosya_metinleri_oku()` yalniz OSError yakaliyor olabilir. "
                "O halde UTF-8 disi baytli IZLENEN bir test dosyasi BLOKLAYICI kapiyi "
                "TRACEBACK ile patlatir (okunur tani yerine yigin izi, tum yayin durur)."
                % (sorted([bozuk, yok]), okunamayan_yollar))
        if list(metinler) != [saglam]:
            hata.append("OKUMA DAYANIKLILIGI FIKSTURU BOZUK: okunabilir dosya listeye "
                        "GIRMELI (gelen=%r) -> fail-open yonu tersine donmus olabilir."
                        % list(metinler))
        if any("UnicodeDecodeError" in s for _y, s in okunamayan) is False:
            hata.append("OKUMA DAYANIKLILIGI FIKSTURU BOZUK: UTF-8 hatasinin SEBEBI "
                        "raporlanmiyor -> 'okunamadi' sayisi var ama tani yok.")
    except Exception as e:  # noqa: BLE001 — fikstur kapiyi patlatmaz, konusur
        hata.append("OKUMA DAYANIKLILIGI FIKSTURU OLCULEMEDI: %s: %s"
                    % (type(e).__name__, e))
    finally:
        ROOT = eski_kok
        shutil.rmtree(gecici, ignore_errors=True)
    return hata


def beyan_fikstur_kontrol_govdesi():
    """BEYAN_FIKSTURLERI'ni olcer; (hata_satirlari) dondurur."""
    hata = []
    for metin, beklenen, etiket in BEYAN_FIKSTURLERI:
        gelen = beyanlari_ayikla(metin)
        if gelen != beklenen:
            hata.append("BEYAN FIKSTURU BOZUK (%s): %r icin %r bekleniyordu, %r geldi "
                        "-> beyanlari_ayikla() cok DAR (BOLUM B tamamen oler) ya da cok "
                        "GENIS (kapi kendi dokumantasyonunu kural sanar) olmus."
                        % (etiket, metin, beklenen, gelen))
    return hata


def uctan_uca_alt_kume_kontrol_govdesi():
    """ALT_KUME_FIKSTURLERI'ni denetle() UZERINDEN olcer; (hata_satirlari) dondurur.

    🔴 CI'DA KOSAN KODUN TA KENDISI OLCULUR: kopya bir karar mantigi yazilmaz
    (muaf_sayaci_kontrol ile ayni desen). kontroller=False SART — ozyineleme korumasi."""
    hata = []
    for (akislar, kesif, metinler, izin, beklenen_kod, beklenen_izler,
         beklenmeyen_izler, etiket) in ALT_KUME_FIKSTURLERI:
        kod, satirlar = denetle("", list(kesif), {}, kontroller=False,
                                akislar=list(akislar), dosya_metinleri=dict(metinler),
                                alt_kume_izin=dict(izin))
        rapor = "\n".join(satirlar)
        eksik = [b for b in beklenen_izler if b not in rapor]
        fazla = [b for b in beklenmeyen_izler if b in rapor]
        if kod != beklenen_kod or eksik or fazla:
            hata.append("ALT KUME UCTAN UCA FIKSTURU BOZUK (%s): beklenen exit %d, "
                        "gelen %d; eksik iz=%r fazla iz=%r\n     RAPOR: %r"
                        % (etiket, beklenen_kod, kod, eksik, fazla, rapor[:700]))
    return hata


# 🔴 F1 — `hata.extend(<nobetci>())` -> `<nobetci>()` SINIFI (SONUC YUTULUR).
# OLCULEN OLU NOBETCI: bu tek karakterlik mutasyon her nobetciyi SESSIZCE olduruyordu;
# AST kablosu yalniz CAGRININ VARLIGINA baktigi icin YESIL kaliyordu (olculdu: 5 mutant,
# iki ortamda da 0/0). ONARIM YAPISALDIR: govdeler bir TABLODAN dolasilir, sonuc
# TEK YERDE toplanir — "extend'i dusurmek" diye bir hamle KALMAZ. Tabloya dokunmak ise
# _nobetci_tablosu_kontrol() tarafindan yakalanir.
# NOT: bu sinif MAIN'DEN MIRASTIR (mevcut nobetcilerde de ayni desen var). Burada YALNIZ
# BU DALIN EKLEDIGI nobetciler kapsanir; miras ayri madde olarak rapora yazildi.
ALT_KUME_NOBETCI_GOVDELERI = (
    ("fikstur-sayisi", lambda: _fikstur_sayisi_kontrol()),
    ("tetik", lambda: tetik_fikstur_kontrol_govdesi()),
    ("beyan", lambda: beyan_fikstur_kontrol_govdesi()),
    ("uctan-uca", lambda: uctan_uca_alt_kume_kontrol_govdesi()),
    ("uyari-izole", lambda: uyari_katmani_izole_kontrol_govdesi()),
    ("okuma-dayanikliligi", lambda: okuma_dayanikliligi_kontrol_govdesi()),
    ("ayristirici-yok", lambda: ayristirici_yok_kontrol_govdesi()),
    ("iki-kol-canlilik", lambda: iki_kol_canlilik_kontrol_govdesi()),
    ("iki-kol-run", lambda: iki_kol_run_kontrol_govdesi()),
    ("iki-kol-govde", lambda: iki_kol_govde_kontrol_govdesi()),
    ("iki-kol-girdi-kumesi", lambda: iki_kol_girdi_kumesi_kontrol_govdesi()),
)

# Tablodan DUSURULMESI yasak nobetciler (F1'in ikinci adimi: once tabloyu buda, sonra...).
ZORUNLU_NOBETCILER = ("fikstur-sayisi", "tetik", "beyan", "uctan-uca", "uyari-izole",
                      "okuma-dayanikliligi", "ayristirici-yok", "iki-kol-canlilik",
                      "iki-kol-run", "iki-kol-govde", "iki-kol-girdi-kumesi")


def _nobetci_tablosu_kontrol():
    """ALT_KUME_NOBETCI_GOVDELERI'nden zorunlu bir nobetci DUSURULDU mu."""
    var = {ad for ad, _f in ALT_KUME_NOBETCI_GOVDELERI}
    eksik = [ad for ad in ZORUNLU_NOBETCILER if ad not in var]
    if not eksik:
        return []
    return ["NOBETCI TABLOSU BUDANMIS: %r tablodan dusurulmus -> o eksen SESSIZCE "
            "olculmez olur (fikstur govdesi dogru cevap verir, ONA KIMSE SORMAZ). "
            "GERI KOY." % (eksik,)]


def alt_kume_fikstur_kontrol():
    """ALT KUME EKSENI NOBETCISI (BOLUM A + B + C) — (ok, hata_satirlari).

    Govdeler TABLODAN dolasilir (F1): her govdenin bulgusu TEK yerde toplanir, boylece
    tek bir `extend` dusurup bir ekseni sessizce oldurmek MUMKUN DEGILDIR."""
    hata = _nobetci_tablosu_kontrol()
    for ad, govde in ALT_KUME_NOBETCI_GOVDELERI:
        try:
            bulgular = govde() or []
        except Exception as e:  # noqa: BLE001 — bir govde patlarsa OTEKILER olculmeli
            hata.append("NOBETCI GOVDESI PATLADI (%s): %s: %s"
                        % (ad, type(e).__name__, e))
            continue
        hata.extend("[%s] %s" % (ad, b) for b in bulgular)
    return (not hata), hata


def uyari_katmani_izole_kontrol_govdesi():
    """UYARI KATMANI 'EXIT KODUNA DOKUNMAZ' IDDIASININ NOBETCISI.

    IKI YONLU:
      (d) uyari katmani BULGU BASSA BILE exit 0 KALIR,
      (x) uyari katmani ISTISNA ATSA BILE exit 0 KALIR ve tani satiri basilir.
    (x) SENTETIK ARIZA ENJEKSIYONU: `alt_kume_izin` yerine `__contains__`'i patlayan
    bir sozluk verilir. `in` operatoru YALNIZ uyari_katmani() icinde kullanilir
    (bloklayici cekirdek `.get()` ve `.items()` kullanir) -> ariza TAM OLARAK uyari
    katmanina enjekte edilmis olur, baska hicbir yolu bozmaz."""
    hata = []
    metin = _ak_metin("--alfa", govde='ap.add_argument("--baska-modifikator")\n'
                                      'ap.add_argument("--ucuncu")')
    kod, satirlar = denetle("", [_AK_YOL], {}, kontroller=False,
                            akislar=list(_AK_TEMEL_AKIS),
                            dosya_metinleri={_AK_YOL: metin}, alt_kume_izin={})
    rapor = "\n".join(satirlar)
    if kod != 0:
        hata.append("(d) UYARI KATMANI EXIT KODUNU DEGISTIRDI: bulgu basildi ve exit %d "
                    "geldi, 0 olmaliydi -> katman BLOKLAYICI hale gelmis; tek bir "
                    "modifikator bayrak TUM ekibin yayinini durdurur." % kod)
    if "UYARI KATMANI" not in rapor or "--baska-modifikator" not in rapor:
        hata.append("(d) UYARI KATMANI SESSIZ: beyan edilmemis modifikator bayrak "
                    "raporda GORUNMUYOR -> A-sinifi adaylar bir daha yuzeye cikmaz.\n"
                    "     RAPOR: %r" % rapor[:600])

    class _Patlayan(dict):
        def __contains__(self, anahtar):
            raise RuntimeError("SENTETIK ARIZA (uyari katmani)")

    try:
        kod2, satirlar2 = denetle("", [_AK_YOL], {}, kontroller=False,
                                  akislar=list(_AK_TEMEL_AKIS),
                                  dosya_metinleri={_AK_YOL: metin},
                                  alt_kume_izin=_Patlayan())
    except Exception as e:  # noqa: BLE001 — TAM OLARAK olculmek istenen ariza
        return hata + [
            "(x) UYARI KATMANI TRY/EXCEPT SARMALI KALKMIS: sentetik ariza denetle()'den "
            "DISARI sizdi (%s: %s) -> BLOKLAMAYAN bir katmandaki kusur artik BLOKLAYAN "
            "kodu patlatiyor ve tum ekibin yayinini durduruyor. GERI KOY."
            % (type(e).__name__, e)]
    rapor2 = "\n".join(satirlar2)
    if kod2 != 0:
        hata.append("(x) UYARI KATMANI ISTISNASI EXIT KODUNU DEGISTIRDI: exit %d geldi, "
                    "0 olmaliydi -> try/except sarmali kalkmis; katmandaki bir kusur "
                    "bloklayan koda sizip yayini durdurur." % kod2)
    if "UYARI KATMANI OLCULEMEDI" not in rapor2:
        hata.append("(x) UYARI KATMANI ISTISNASI SESSIZ YUTULDU: 'UYARI KATMANI "
                    "OLCULEMEDI' tani satiri basilmadi -> katman olur, kimse gormez.\n"
                    "     RAPOR: %r" % rapor2[:600])
    return hata


def suzgec_fikstur_kontrol():
    """ORTAK SUZGEC GOVDESI NOBETCISI — ariza enjeksiyonu, SENTETIK fiksturlerle.

    Fiksturler repoda VAR OLMAYAN sentetik yollar kullanir (zzz-sentetik-*), yani
    gercek deploy.yml / gercek dosya agaci degisince BAYATLAMAZ. Iddia iki YONLU:
    ANLAMLI bicimler EVET, ANLAMSIZ bicimler HAYIR. Tek yonlu olsa suzgec "daima
    EVET" ya da "daima None" doner hale getirilip sessizce oldurulebilirdi.
    (ok, hata_satirlari) dondurur."""
    hata = []
    for satir, yol, beklenen, etiket in SUZGEC_FIKSTURLERI:
        hukum, sebep, _ = SUZGEC.anlamli_cagri(satir, yol)
        gelen = hukum if hukum is not None else "ILGISIZ"
        if gelen != beklenen:
            hata.append("SUZGEC FIKSTURU BOZUK (%s): %r icin %s bekleniyordu, %s geldi "
                        "(sebep: %s) -> tools/icra-suzgeci.py govdesi no-op/ters "
                        "yapilmis olabilir" % (etiket, satir, beklenen, gelen, sebep))
    # `etkili_arguman` ekseni (jenerator/test/kabul.py TEST 4'un dayanagi) de olculur.
    for satir, beklenen, etiket in (
            ("cp jenerator/zzz-sentetik.js _site/jenerator/", "EVET",
             "gercek komutun argumani ETKILI mensiyon"),
            ("echo cp jenerator/zzz-sentetik.js _site/jenerator/", "HAYIR",
             "`echo` icindeki mensiyon ETKILI SAYILMAMALI (DUZ-MENSIYON 1)"),
            ("# cp jenerator/zzz-sentetik.js _site/jenerator/", "ILGISIZ",
             "kabuk yorumu ETKILI SAYILMAMALI (DUZ-MENSIYON 1)")):
        hukum, sebep = SUZGEC.etkili_arguman(satir, "jenerator/zzz-sentetik.js")
        gelen = hukum if hukum is not None else "ILGISIZ"
        if gelen != beklenen:
            hata.append("SUZGEC etkili_arguman FIKSTURU BOZUK (%s): %r icin %s "
                        "bekleniyordu, %s geldi (sebep: %s)"
                        % (etiket, satir, beklenen, gelen, sebep))
    # YAML KATLAMA ekseni (Y05) — ayni sinif: ORTAK DONUSUM GOVDESI no-op yapildi.
    hata.extend(katlama_fikstur_kontrol_govdesi())
    # BICIM TESHISI ekseni (T3) — tani govdesi no-op/ters yapildi.
    hata.extend(bicim_teshis_kontrol_govdesi())
    # NOT: `run:` kolu IKI-KOL PARITESI artik ALT_KUME_NOBETCI_GOVDELERI tablosunda
    # ("iki-kol-run") — F1 geregi TEK toplama noktasi kullanilir.
    return (not hata), hata


# AST ile aranan kablolar: (fonksiyon_adi, SUZGEC uzerinde cagrilmasi ZORUNLU uye(ler))
SUZGEC_KABLOLARI = (
    ("kosulan", ("cagri_sayilir", "anlamli_cagri")),
    ("_hedef_cagrilari", ("anlamli_cagri",)),
    ("_icra_komutlari", ("birlestir_devam",)),
)

# KATLAMA KABLOLARI (Y05): YAML katlama donusumu, komut govdelerini uretcen IKI yolun
# HER IKISINDE de cagrilmak ZORUNDA. Fikstur nobetcisi (KATLAMA_FIKSTURLERI) govdenin
# no-op yapilmasini yakalar ama CAGRISININ silinmesini GORMEZ (fonksiyon dogru cevap
# veriyor, ona kimse sormuyor) -> AST kablosu. Metin capasi DEGIL
# ([[kapi-anchor-coupling-ikilemi]]): biçimlendirme/yorum degisikligi sahte-kirmizi yakmaz.
KATLAMA_KABLOLARI = (
    ("_icra_komutlari", ("_katlanan_bloklari_birlestir",)),
    ("_hedef_cagrilari", ("_katlanan_bloklari_birlestir",)),
    ("_katlanan_bloklari_birlestir", ("_mantiksal_yaml_satirlari",)),
    # mutant ureticilerinin capasi da MANTIKSAL satirdan gelmek ZORUNDA (yoksa katlanan
    # blokta bolunmus cagri mutasyondan SAG cikar ve nobetci yanlis sinifla kirmizi yanar)
    ("_icra_satir_indeksleri", ("_mantiksal_yaml_satirlari",)),
    # 🔴 PARSER-FIRST KABLOSU: hukum yolu GERCEK ayristiriciyi SORMAK ZORUNDA. Bu cagri
    # silinir/kisa devre edilirse kapi taklide SESSIZCE duser — olculdu (30 Tem): taklit
    # ile gercek ayristirici 1037 girdinin 303'unde FARKLI hukum veriyor.
    ("_mantiksal_yaml_satirlari", ("_ayristirici_run_bloklari",)),
    ("_mantiksal_yaml_satirlari", ("_taklit_run_bloklari",)),
    ("_mantiksal_yaml_satirlari", ("_bloklardan_mantiksal",)),
    # 🔴 FIKSTUR NOBETI IKI KOLU DA SORMAK ZORUNDA: yalniz bir kol sorulursa oteki koldaki
    # mutasyon sessizlesir (PARSER-FIRST'ten sonra taklit govdesi tam olarak boyle kaciyordu).
    ("katlama_fikstur_kontrol_govdesi", ("_taklit_mantiksal_satirlari",)),
    ("katlama_fikstur_kontrol_govdesi", ("_ayristirici_mantiksal_satirlari",)),
    ("katlama_fikstur_kontrol_govdesi", ("_fikstur_sayisi_kontrol",)),
    ("katlama_fikstur_kontrol_govdesi", ("icra_govdesi_fikstur_kontrol_govdesi",)),
    ("katlama_fikstur_kontrol_govdesi", ("icra_indeks_fikstur_kontrol_govdesi",)),
    ("icra_govdesi_fikstur_kontrol_govdesi", ("_icra_govdesi",)),
    ("icra_indeks_fikstur_kontrol_govdesi", ("_icra_satir_indeksleri",)),
)

# AYRISTIRICI KABLOLARI: `YAML_OKU.<uye>(...)` cagrilari (SUZGEC deseninin aynisi).
# Govde nobetcisi (KATLAMA_FIKSTURLERI) ayristirici kolunun DOGRU calistigini olcer ama
# CAGRILMADIGINI gormez: `_ayristirici_run_bloklari` "daima None dondur" haline
# getirilirse tum fiksturler yine gecer (taklit kolu dogru cevap verir) ve kapi sessizce
# PARSER-FIRST'ten CIKAR.
AYRISTIRICI_KABLOLARI = (
    ("_ayristirici_run_bloklari", ("run_dugumleri",)),
    ("_mantiksal_yaml_satirlari", ("ayristirici_adi",)),
    ("katlama_fikstur_kontrol_govdesi", ("ayristirici_adi",)),
    # 🔴 TETIK EKSENI DE PARSER-FIRST: `on:` blogu METIN TAKLIDIYLE okunamaz (uc yazim
    # + YAML 1.1 boolean tuzagi). Bu cagri silinirse tetik siniflandirmasi elle yazilmis
    # bir capaya duser ve ELLE/OTOMATIK ayrimi sessizce yanlislasir.
    ("tetik_sinifi", ("tetikleyiciler",)),
    ("tetik_fikstur_kontrol_govdesi", ("tetik_onbellegi_isit",)),
    # F2: KARSILASTIRMA GOVDESI monkeypatch'ten BAGIMSIZ olculmeli — nobetci kol
    # fonksiyonlarini degistirir ama `iki_kol_*_sapmasi`'nin GERCEK govdesini cagirir.
    ("iki_kol_govde_kontrol_govdesi", ("iki_kol_tetik_sapmasi", "iki_kol_run_sapmasi")),
    ("iki_kol_tetik_kontrol_govdesi", ("iki_kol_tetik_sapmasi",)),
    ("iki_kol_run_kontrol_govdesi", ("iki_kol_run_sapmasi",)),
    ("iki_kol_durum_satiri", ("iki_kol_tetik_sapmasi", "iki_kol_run_sapmasi")),
)

# ALT KUME KABLOLARI (BOLUM A+B+C): nobetci govdesi UC olcumu de SORMAK ZORUNDA.
# Fikstur tablolari govdenin no-op yapilmasini yakalar ama CAGRISININ silinmesini
# GORMEZ (fonksiyon dogru cevap veriyor, ona kimse sormuyor) -> AST kablosu.
ALT_KUME_KABLOLARI = (
    # F1: govdeler artik ALT_KUME_NOBETCI_GOVDELERI tablosundan dolasiliyor; tablonun
    # BUDANMASINI `_nobetci_tablosu_kontrol` yakalar, o cagrinin dusmesini ise bu kablo.
    ("alt_kume_fikstur_kontrol", ("_nobetci_tablosu_kontrol",)),
    ("okuma_dayanikliligi_kontrol_govdesi", ("dosya_metinleri_oku",)),
    ("ayristirici_yok_kontrol_govdesi", ("denetle",)),
    ("iki_kol_canlilik_kontrol_govdesi", ("iki_kol_tetik_kontrol_govdesi",
                                          "iki_kol_run_kontrol_govdesi")),
    # F3: asgari kontrol FONKSIYONUN CIKTISI uzerinde olmali.
    ("iki_kol_girdi_kumesi_kontrol_govdesi", ("iki_kol_girdi_kumesi",)),
    # F1/F5: rapor metni <-> hukum tutarliligi.
    ("denetle", ("tutarlilik_kontrolu",)),
    # uctan uca nobetci CI'da kosan kodun TA KENDISINI cagirmali (kopya karar
    # mantigi yazilirsa fikstur kendi kendini onaylar)
    ("uctan_uca_alt_kume_kontrol_govdesi", ("denetle",)),
    ("uyari_katmani_izole_kontrol_govdesi", ("denetle",)),
    ("tetik_fikstur_kontrol_govdesi", ("tetik_sinifi",)),
    ("beyan_fikstur_kontrol_govdesi", ("beyanlari_ayikla",)),
    # KAPSAM COKLU-WORKFLOW'DAN gelmek ZORUNDA: bu cagri silinirse kapi tek dosyaya
    # (deploy.yml) geri duser ve cron'da kosan cagrilar yine "kosmuyor" gorunur.
    ("denetle", ("kosulan_coklu",)),
    ("denetle", ("alt_kume_denetimi",)),
    ("denetle", ("uyari_katmani",)),
    ("denetle", ("bayrak_envanteri",)),
    ("kosulan_coklu", ("kosulan",)),
    ("is_akislari", ("tetik_sinifi", "is_akisi_yollari")),
    ("alt_kume_denetimi", ("beyanlari_ayikla",)),
    ("uyari_katmani", ("_py_bayrak_analizi", "beyanlari_ayikla")),
    ("main", ("is_akislari",)),
    # 🔴 P1 — IKI-KOL PARITESI OLCUM AYGITININ KABLOSU (curutucu 2. tur):
    # O3'un TUM aygiti TEK SATIRLA etkisizlestirilebiliyordu — `iki_kol_tetik_kontrol_
    # govdesi` govdesine `return []` koymak ya da `iki_kol_durum_satiri()` cagrisini
    # silmek kapiyi rc=0 YESIL birakiyordu. Govde nobetcisi fonksiyonun DOGRU cevap
    # verdigini olcer, ONA KIMSE SORMADIGINI gormez.
    ("tetik_fikstur_kontrol_govdesi", ("iki_kol_tetik_kontrol_govdesi",)),
    ("denetle", ("iki_kol_durum_satiri",)),
    ("iki_kol_tetik_kontrol_govdesi", ("iki_kol_girdi_kumesi",)),
    ("iki_kol_durum_satiri", ("iki_kol_girdi_kumesi",)),
    # 🔴 P2 — O8/O9 tanilarinin kablosu: cagriyi silmek rc=0 birakiyordu.
    ("denetle", ("beyan_benzeri_ayristirilamayan",)),
    ("denetle", ("dosya_metinleri_oku",)),
)

# TANI KABLOLARI (T3): bicim teshisi, KIRMIZI yanan IKI nobetcinin de tani metnine
# baglanmak ZORUNDA. Govde nobetcisi (BICIM_FIKSTURLERI) teshisin DOGRU calistigini
# olcer ama CAGRILMADIGINI gormez -> "cagri YOK" tanisi sessizce eski (sagir) haline
# doner ve bir sonraki mesru yazim yine korku salar (Y05'in ta kendisi).
TANI_KABLOLARI = (
    ("kendini_test_adimi_kontrol", ("_teshis_ozeti",)),
    ("bayraksiz_adim_kontrol", ("_teshis_ozeti",)),
    ("_teshis_ozeti", ("bicim_teshisi",)),
    ("bicim_teshisi", ("_mantiksal_yaml_satirlari", "_run_bloklari", "_bicim_etiketi")),
    ("bicim_teshis_kontrol_govdesi", ("_teshis_ozeti",)),
)

# NOBETCI KABLOLARI: hangi fonksiyonun govdesinde hangi NOBETCI cagrilmali.
# 🔴 CAPRAZ NOBET (bilincli): her nobetci IKI yerden cagrilir — denetle() (bayraksiz kol)
# ve main()'in `--kendini-test` kolu. Boylece "bir koldaki cagriyi sil" mutasyonu OTEKI
# kol tarafindan yakalanir. Kendi cagrisini da silen IKI ADIMLI mutasyon kacar (mevcut
# beyanla ayni sinir; ust kat tools/nobetci-mutasyon-test.py).
# 🔴 KABLONUN KABLOSU (9 Agu 2026, IKINCI TUR curutme): birinci turda eklenen iki
# nobetciyi GOVDESINDEN sokmak `kesif-kapsam-mutasyon.py` tarafindan yakalaniyordu,
# ama BLOKLAYICI koldan CAGRI SATIRLARINI silmek (KB-C/KB-D) DORT bataryayi da
# YESIL birakiyordu — birinci turda kapatilan sinifin bir kat yukarisi
# ([[nobetci-cagri-satiri-nobetsiz]]). Ucu de asagiya EKLENDI.
# 🔴 DEFTER **TAM** OLMAK ZORUNDA (9 Agu 2026, 4. tur): asagidaki kume ile
# fonksiyonun FIILEN cagirdigi `*_kontrol` nobetcileri BIREBIR ESIT olmalidir.
# Eskiden defter yalnizca ALT KUME idi; o zaman "defterden kaydi sil" mutanti
# (E5-a) hicbir gate kolunda kirmizi yakmiyordu — sayisal taban (`KOL_BIRLESIM_
# TABANI`) da ayni saboteur tarafindan dusurulebildigi icin IKIZ olusuyordu.
# ESITLIK ikizi ortadan kaldirir: iki eksen (defter vs GERCEK cagri) birbirini
# capalar, tek satirlik kacis kalmaz ([[ikiz-tanim-sessiz-ayrisma]]).
NOBETCI_KABLOLARI = (
    ("denetle", ("acik_kesif_kontrol", "alt_kume_fikstur_kontrol",
                 "bayraksiz_adim_kontrol", "bulgu1_mutasyon_kontrol",
                 "hukum_davranis_kontrol", "hukum_fuzz_kontrol",
                 "izlenmeyen_fikstur_kontrol", "kanca_kablo_adimi_kontrol",
                 "kendini_test_adimi_kontrol", "kesif_predikat_kontrol",
                 "main_kablosu_kontrol", "muaf_sayaci_kontrol",
                 "pre_push_capa_kontrol", "suzgec_fikstur_kontrol",
                 "suzgec_kablosu_kontrol")),
    ("main", ("alt_kume_fikstur_kontrol", "bayraksiz_adim_kontrol",
              "bulgu1_mutasyon_kontrol", "hukum_davranis_fikstur_kontrol",
              "hukum_davranis_kontrol", "hukum_fuzz_kontrol",
              "izlenmeyen_fikstur_kontrol", "kanca_kablo_serit_kontrol",
              "kendini_test_adimi_kontrol", "kesif_predikat_kontrol",
              "main_kablosu_kontrol", "muaf_sayaci_kontrol",
              "pre_push_kablo_kontrol", "suzgec_fikstur_kontrol",
              "suzgec_kablosu_kontrol")),
)
# 🔴 `tutarlilik_kontrolu` BU DEFTERDE DEGIL (10. tur): (ok, hata) sozlesmesine
# UYMAZ — LISTE dondurur ve `hatalar.extend(...)` ile akar, yani stub sozlesmesine
# de girmez. Cagri raseti KAYBOLMADI: `ALT_KUME_KABLOLARI`'nda
# ("denetle", ("tutarlilik_kontrolu",)) olarak duruyor; cagrisi silinince
# `suzgec_kablosu_kontrol` KIRMIZI yakiyor (olculdu). Iki defter AYNI seyi degil,
# AYRI sozlesmeleri yargilar — birlesim sayisinin 19'dan 18'e inmesi YUZEY KAYBI
# DEGIL, OLCU BIRIMI degisimidir ([[hukum-yanlis-birimde]]).

# 🔴 TOPLAM YUZEY RASETI ([[kapi-yan-etkisi-gizli-onkosul]]): bir adimi kolun
# birinden otekine TASIMAK yuzeyi SESSIZCE kucultebilir — iki kol da rc=0 verirken.
# NOT: bu SAYI artik TEK BASINA yuk tasimiyor (dusurulebilir olmasi E5-a deligiydi);
# asil capa yukaridaki ESITLIK kontroludur. Sayi ikinci bir ratchet olarak kalir.
KOL_BIRLESIM_TABANI = 18
# UCUNCU (BLOKLAYICI) KOL — `--kanca-kablo`. `NOBETCI_KABLOLARI`'nin anahtarlari
# FONKSIYON adi oldugu icin bu kolun nobetcileri `main` kaydinda erir ve kol dokumu
# onu RAPORLAMIYORDU (5. tur F6). Ayri kayit: dokum UC SERIDI de basar.
KANCA_KABLO_KOL_NOBETCILERI = ("hukum_davranis_fikstur_kontrol",
                               "kanca_kablo_serit_kontrol",
                               "pre_push_kablo_kontrol")

# 🔴 `--kendini-test` HUKMUNUN KENDISI (KB-E): butun `okN` degiskenleri hukme
# `and` ile girmeli. Olculdu: `and ok10 and ok11` -> `or ok10 or ok11` yapildiginda
# o iki nobetci ARTIK KIRMIZI YAKAMAZ ve dort batarya da YESIL kalir. Cagri satirini
# civilemek yetmez; PAYIN hukumde durdugu da olculmelidir.
_OK_ADI_RE = re.compile(r"^ok\d+$")
# `--kanca-kablo` kolunun hukum degiskenleri `okN` desenine UYMUYOR; sinif olarak
# kapsanmalari icin ADAY listesine alinir (tekil yama degil: asagidaki `turevli`
# turetimi zaten "nobetci cagrisindan deger alan HER ad" kuralini uygular).
_HUKUM_ADAY_ADLARI = ("ok", "ok_s")
# 🟡 NOBETCI ADLANDIRMA KONVANSIYONU — **KURALDIR, KAPI DEGILDIR** (10. tur J3)
# ─────────────────────────────────────────────────────────────────────────────
# 9. turda bu konvansiyon `kapi-envanteri-test.py`de IDDIA olarak civilenmisti;
# 10. turda o iddia KALDIRILDI. Sebep: evren artik ADDAN degil CAGRI GRAFI +
# (ok, hata) SOZLESMESINDEN turuyor (`_sozlesme_evreni`), yani desen disi
# adlandirilan bir nobetci ZATEN kendiliginden kapsaniyor. Ada dayali bir iddia
# birakmak, kapsami ADIN saglIadigi izlenimi verirdi — YANLIS IDDIA, iddiasizliktan
# kotudur ([[beyan-edilmis-survivor]]). Asagisi UYUM ONERISIDIR (okunabilirlik),
# kapsam garantisi DEGIL.
#
# ESKI GEREKCE (tarihsel kayit, 9. tur I3-a):
# ─────────────────────────────────────────────────────────────────────────────
# Bu dosyadaki HER nobetci fonksiyonun adi `*_kontrol` ya da `*_kontrolu` ile
# BITMEK ZORUNDADIR. Sebep: hem `_kol_kapsam_kontrol()` (defter/cagri esitligi)
# hem `hukum_davranis_kontrol()` (stub evreni) nobetci kumesini BU AD DESENINDEN
# turetir. Desen disi adlandirilan bir nobetci HER IKI eksende de SESSIZCE kapsam
# disi kalir: cagrisi silinse kimse gormez, hukmu ezilse kimse gormez
# ([[envanter-drift-parti-basina]] · [[nobetci-cagri-satiri-nobetsiz]]).
# Olculdu (9 Agu 2026): modul duzeyinde 113 fonksiyonun 24'u desene uyuyor.
#
# ISTISNALAR — GEREKCELI ve KAYITLI olmak zorunda (yenisi eklenmeden ONCE buraya
# yazilir; kayitsiz istisna `kapi-envanteri-test.py`de KIRMIZI yakar):
#   * `alt_kume_denetimi` — nobetci DEGIL, `denetle()`nin BOLUM B alt-rutinidir;
#     kendi hukmunu vermez, bulgularini cagirana dondurur ve o hukmu `denetle()`
#     verir. Stub'lanmasi anlamsizdir (donusu (hata, sayi, sayi, sayi, liste)).
NOBETCI_ADLANDIRMA_ISTISNALARI = {
    "alt_kume_denetimi":
        "nobetci degil ALT-RUTIN: kendi hukmunu vermez, coklu deger dondurur ve "
        "hukum denetle() BOLUM B'de verilir; stub sozlesmesine uymaz.",
}
_NOBETCI_CAGRI_RE = re.compile(r"_kontrol$|_kontrolu$")


def _hedef_deger_ciftleri(hedef, deger):
    """(ad, o ada dusen DEGER ifadesi) — tuple hedefte KONUMSAL eslesme yapar."""
    if isinstance(hedef, ast.Tuple):
        parcalar = (deger.elts if isinstance(deger, ast.Tuple)
                    and len(deger.elts) == len(hedef.elts) else None)
        for i, alt in enumerate(hedef.elts):
            yield from _hedef_deger_ciftleri(alt,
                                             parcalar[i] if parcalar else deger)
        return
    if isinstance(hedef, ast.Name):
        yield hedef.id, deger


def _nobetci_cagrisi_mi(deger):
    """<deger> icinde `*_kontrol(...)` bicimli bir NOBETCI cagrisi var mi."""
    for c in ast.walk(deger):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) \
                and _NOBETCI_CAGRI_RE.search(c.func.id):
            return True
    return False


def _cagridan_mi(deger, turevli):
    """<deger> bir NOBETCI cagrisindan turuyor mu.

    🔴 "HERHANGI BIR CAGRI" YETMEZ (6. tur, G1): eski surum `any(isinstance(c,
    ast.Call) ...)` diyordu; `ok4 = bool(1)`, `ok4 = len([]) == 0`, `ok4 = any([])`
    sabotajlarinin UCU DE DORT KOLDA YESIL geciyordu — kural "cagridan turemis mi"
    degil "icinde parantez var mi" olcuyordu. Artik TEK KAYNAK
    `_nobetci_cagrisi_mi()`dir ([[ikiz-tanim-sessiz-ayrisma]])."""
    if _nobetci_cagrisi_mi(deger):
        return True
    if isinstance(deger, ast.Name):
        return deger.id in turevli
    if isinstance(deger, ast.IfExp):
        return (_cagridan_mi(deger.body, turevli)
                and _cagridan_mi(deger.orelse, turevli))
    if isinstance(deger, ast.BoolOp):
        return all(_cagridan_mi(v, turevli) for v in deger.values)
    if isinstance(deger, (ast.Tuple, ast.List)):
        return bool(deger.elts) and all(_cagridan_mi(e, turevli)
                                        for e in deger.elts)
    if isinstance(deger, ast.Subscript):
        return _cagridan_mi(deger.value, turevli)
    if isinstance(deger, ast.Starred):
        return _cagridan_mi(deger.value, turevli)
    return False


def _cagri_turevli_adlar(fn):
    """<fn> govdesinde degeri (dolayli da olsa) bir CAGRIDAN gelen yerel adlar.

    Sabit nokta: `_s = f()` -> `_s` turevli; `ok, hata = _s` -> `ok` da turevli.
    Bu, `okN` kuralini SOZDIZIMSEL olmaktan cikarip ANLAMSAL yapan cekirdektir."""
    turevli = set()
    for _ in range(8):
        eklendi = False
        for d in ast.walk(fn):
            if not isinstance(d, ast.Assign):
                continue
            for hedef in d.targets:
                for ad, deger in _hedef_deger_ciftleri(hedef, d.value):
                    if ad in turevli:
                        continue
                    if _cagridan_mi(deger, turevli):
                        turevli.add(ad)
                        eklendi = True
        if not eklendi:
            break
    return turevli

# 🔴 TEST SEAMI'NIN KENDISI (UCUNCU TUR, S1): `suzgec_kablosu_kontrol(kaynak=None)`
# uretim yolunda KENDI CALISAN dosyasini okumali. Olculdu: o dali tek satirda
# `git show HEAD:...` okumaya cevirmek DORT bataryayi da YESIL biraktı — "uretimde
# daima None gelir, dosya diskten okunur" beyani hicbir yerde IDDIA degildi
# ([[olculdu-diyen-hukum-kaniti]]). Asagidaki nobetci o beyani kaynak ekseninde olcer.
_SEAM_YASAK_CAGRI = ("run", "check_output", "Popen", "check_call", "getoutput",
                     "urlopen", "loads")


# 🔴 IKI KOLUN KENDI FIKSTURU (5. tur F4-D3/D4): `defter_eksik` kolunu bosaltmak ya
# da seam YASAK LISTESINI bosaltmak hicbir gate kolunda kirmizi yakmiyordu — govde
# dogru cevap veriyordu, KIMSE ONA BILEREK BOZUK GIRDI VERMIYORDU. Asagidaki iki
# sentetik kaynak, her kolun BILINEN-BOZUK girdide ATESLENDIGINI olcer.
# 🔴 SEKIL GERCEK KODU TAKLIT EDER (10. tur): evren artik CAGRI GRAFI + (ok, hata)
# sozlesmesinden turedigi icin fikstur de o sekli tasimali — `x, y = f()` ve
# `for h in y:` ([[nobetci-fikstur-sekli]]).
_IC_FIKSTUR_DEFTER = (
    'NOBETCI_KABLOLARI = (("denetle", ("suzgec_kablosu_kontrol",)), ("main", ()))\n'
    "def suzgec_kablosu_kontrol():\n    return True, []\n"
    "def alt_kume_fikstur_kontrol():\n    return True, []\n"
    "def denetle():\n"
    "    hatalar = []\n"
    "    _, a_hata = suzgec_kablosu_kontrol()\n"
    "    for h in a_hata:\n        hatalar.append(h)\n"
    "    _, b_hata = alt_kume_fikstur_kontrol()\n"
    "    for h in b_hata:\n        hatalar.append(h)\n"
    "    return hatalar\n"
    "def main():\n    pass\n")
_IC_FIKSTUR_SEAM = (
    "def suzgec_kablosu_kontrol(kaynak=None):\n"
    "    if kaynak is None:\n"
    "        yol = os.path.abspath(__file__)\n"
    "        with open(yol) as f:\n"
    "            kaynak = f.read()\n"
    "        kaynak = subprocess.run(['git', 'show'],\n"
    "                                capture_output=True).stdout\n"
    "    return kaynak\n")


def _kablo_ic_fikstur():
    """Iki kol BILINEN-BOZUK girdide ATESLENIYOR mu (kolun kendi nobeti)."""
    hata = []
    try:
        agac = ast.parse(_IC_FIKSTUR_DEFTER)
        duz = {d.name: _duz_cagrilar(d) for d in ast.walk(agac)
               if isinstance(d, ast.FunctionDef)}
        if not any("KAYIT DEFTERI EKSIK" in h
                   for h in _kol_kapsam_kontrol(agac, duz, _IC_FIKSTUR_DEFTER)):
            hata.append("IC FIKSTUR (DEFTER) DUSTU: defterde OLMAYAN bir nobetci "
                        "cagrilirken `KAYIT DEFTERI EKSIK` ATESLENMEDI -> defter "
                        "esitliginin bir yonu no-op yapilmis olabilir.")
        if not any("SEAM SIZINTISI" in h and "ALT SUREC" in h
                   for h in _seam_kontrol(ast.parse(_IC_FIKSTUR_SEAM))):
            hata.append("IC FIKSTUR (SEAM) DUSTU: `kaynak`a alt-surec ciktisi "
                        "atanirken `SEAM SIZINTISI ... ALT SUREC` ATESLENMEDI -> "
                        "YASAK LISTESI bosaltilmis olabilir.")
    except Exception as e:  # noqa: BLE001 — fikstur kapiyi patlatmaz, konusur
        hata.append("IC FIKSTUR OLCULEMEDI: %s: %s" % (type(e).__name__, e))
    return hata


def _kol_kapsam_kontrol(agac, duz, kaynak):
    """KAYIT DEFTERI ile FIILEN CAGRILAN nobetciler BIREBIR ESIT mi (iki kol).

    🔴 NEDEN ESITLIK (4. tur, E5-a): defter ALT KUME olarak yorumlandiginda
    "defterden kaydi sil" mutanti hicbir gate kolunda kirmizi yakmiyordu; sayisal
    taban da ayni dosyada oldugu icin saboteur ikisini birden dusurebiliyordu.
    Simdi iki BAGIMSIZ eksen (kaynak defteri vs AST cagrilari) birbirini capaliyor:
      * cagri var / defter yok -> DEFTER EKSIK (yeni; E5-a burada duser)
      * defter var / cagri yok -> KABLO KOPMUS (eskiden beri)
    Kalan bilinen sinir: HEM cagriyi HEM kaydi silen IKI ADIMLI mutasyon (mevcut
    beyanla ayni; ust kat tools/nobetci-mutasyon-test.py)."""
    hata = []
    kayit = None
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Assign):
            continue
        if "NOBETCI_KABLOLARI" not in [t.id for t in dugum.targets
                                       if isinstance(t, ast.Name)]:
            continue
        try:
            kayit = dict(ast.literal_eval(dugum.value))
        except (ValueError, SyntaxError):
            return ["KOL KAPSAMI OLCULEMEDI: NOBETCI_KABLOLARI sabit ifade degil -> "
                    "defter kaynaktan okunamiyor (fail-closed)."]
        break
    if kayit is None:
        return ["KOL KAPSAMI OLCULEMEDI: NOBETCI_KABLOLARI atamasi kaynakta "
                "BULUNAMADI -> defter yeniden adlandirilmis olabilir."]
    # NOBETCI EVRENI — 🔴 TEK KAYNAK `_sozlesme_evreni()` (10. tur, J3): "nobetci
    # nedir" tanimi ADDAN degil CAGRI GRAFI + (ok, hata) SOZLESMESINDEN turer.
    # Ad desenine dayali eski tanim 6 yanlis-pozitif uretiyor ve desen disi bir
    # nobetciyi (`*_denetimi`) SESSIZCE kapsam disi birakiyordu.
    evren = set(_sozlesme_evreni(kaynak))
    for ad in ("denetle", "main"):
        if ad not in duz:
            hata.append("KOL KAPSAMI OLCULEMEDI: %s() bulunamadi." % ad)
            continue
        cagrilan = duz[ad] & evren
        kayitli = set(kayit.get(ad, ()))
        defter_eksik = sorted(cagrilan - kayitli)
        if defter_eksik:
            hata.append(
                "KAYIT DEFTERI EKSIK (%s): %s FIILEN cagriliyor ama "
                "NOBETCI_KABLOLARI'nda YOK -> o cagrinin silinmesi bir daha KIRMIZI "
                "YAKMAZ (raset sessizce dustu)." % (ad, ", ".join(defter_eksik)))
    birlesim = set()
    for _ad, gerekli in kayit.items():
        birlesim |= set(gerekli)
    # 🔴 TABAN **ESIT** OLMALI, ">=" DEGIL (6. tur G3-iv/G4): taban tek basina
    # dusurulunce hicbir gate kolu konusmuyordu (yalniz surucu). Esitlik sarti,
    # tabani dusurmeyi TEK BASINA kirmizi yapar; yuzeyi buyutmek ise tabani
    # BILINCLI olarak guncellemeyi zorunlu kilar (raset).
    if len(birlesim) != KOL_BIRLESIM_TABANI:
        hata.append(
            "KOL BIRLESIMI TABANLA UYUSMUYOR: TOPLAM nobetci kumesi %d, taban %d -> "
            "%s ([[kapi-yan-etkisi-gizli-onkosul]])."
            % (len(birlesim), KOL_BIRLESIM_TABANI,
               "yuzey KUCULMUS ya da taban DUSURULMUS olabilir"
               if len(birlesim) < KOL_BIRLESIM_TABANI
               else "yuzey buyudu; tabani BILINCLI olarak guncelle"))
    return hata


def _seam_kontrol(agac):
    """`kaynak is None` dali GERCEKTEN `os.path.abspath(__file__)` okuyor mu."""
    hata = []
    fn = next((d for d in ast.walk(agac) if isinstance(d, ast.FunctionDef)
               and d.name == "suzgec_kablosu_kontrol"), None)
    if fn is None:
        return ["SEAM NOBETCISI BAYAT: suzgec_kablosu_kontrol() bulunamadi."]
    # 🔴 KAPSAM = FONKSIYONUN TAMAMI (4. tur, E3-iv): eskiden yalniz `kaynak is None`
    # If DUGUMUNUN ICI taraniyordu; seam If DISINDA ezilince (`kaynak = <baska>`) iki
    # gate kolu da YESIL kaliyordu ([[tekil-yama-sinifi-kapatmaz]]). Artik `kaynak`a
    # yapilan HER yeniden atama ve govdedeki HER yasak cagri olculur.
    dal = None
    for d in ast.walk(fn):
        if isinstance(d, ast.If):
            metin = {n.id for n in ast.walk(d.test) if isinstance(n, ast.Name)}
            if "kaynak" in metin:
                dal = d
                break
    if dal is None:
        hata.append("SEAM DALI BULUNAMADI: `kaynak is None` kosulu YOK -> seam "
                    "uretim yoluna sessizce sizmis olabilir (fail-closed).")
    adlar, oznitelikler, isimler = set(), set(), set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                adlar.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                oznitelikler.add(n.func.attr)
        if isinstance(n, ast.Name):
            isimler.add(n.id)
    if "abspath" not in oznitelikler or "__file__" not in isimler:
        hata.append(
            "SEAM SIZINTISI: `suzgec_kablosu_kontrol()` govdesi "
            "`os.path.abspath(__file__)` OKUMUYOR (gorulen cagri=%r) -> nobetci "
            "KOSAN dosyayi degil BASKA bir kaynagi (or. `git show HEAD:...`) "
            "yargiliyor olabilir; calisma agacindaki sabotaj SESSIZ kalir."
            % (sorted(oznitelikler | adlar)[:8],))
    if "open" not in adlar:
        hata.append("SEAM SIZINTISI: govdede `open(...)` cagrisi YOK -> kaynak metni "
                    "diskten okunmuyor.")
    yasak = sorted((adlar | oznitelikler) & set(_SEAM_YASAK_CAGRI))
    if yasak:
        hata.append("SEAM SIZINTISI: govdede ALT SUREC/HARICI kaynak cagrisi var (%s) "
                    "-> uretim yolu artik CALISAN dosyayi okumuyor." % ", ".join(yasak))
    # `kaynak`a yapilan ATAMALAR: yalniz (a) parametre, (b) `open(...).read()`
    # mesrudur. Baska her yeniden atama seam'i uretim yoluna sizdirir.
    for n in ast.walk(fn):
        if not isinstance(n, ast.Assign):
            continue
        if "kaynak" not in [t.id for t in n.targets if isinstance(t, ast.Name)]:
            continue
        kaynak_cagri = {c.func.attr for c in ast.walk(n.value)
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
        if "read" not in kaynak_cagri:
            hata.append(
                "SEAM SIZINTISI: `kaynak` degiskenine `f.read()` OLMAYAN bir atama "
                "yapiliyor (satir %d) -> nobetciye YARGILAYACAGI metin disaridan "
                "verilmis olur ve CALISAN dosya hic okunmaz."
                % getattr(n, "lineno", -1))
    return hata


# ---- HUKUM KURALI FUZZ FIKSTURU (23 VARYANT, IKI YONLU) --------------------
# 🔴 NEDEN REPODA (6. tur, mimar hukmu): bu kural artik BLOKLAYICI pre-push kolunda
# HERKESIN itmesini yargiliyor. Bagimsiz curutucunun 23 varyantlik fuzz'i iki yonde
# de sizinti buldu (4 sahte-YESIL + 6 sahte-KIRMIZI). Tablo kalici kabul testi
# olarak baglandi; KUCULTULURSE kirmizi yanar ([[fikstur-degeri-mutasyon-koru]]).
# Fikstur SENTETIK bir mini-`main()` uzerinde kosar: gercek 6000 satirlik kaynagi
# 23 kez ayristirmak pre-push kolunu ~1 sn buyuturdu (olculdu), sekil ise birebir
# taklit edilir ([[nobetci-fikstur-sekli]]).
_HUKUM_TABAN_KAYNAK = (
    "def bayraksiz_adim_kontrol():\n    return True, []\n"
    "def kanca_kablo_serit_kontrol():\n    return True, []\n"
    "def main():\n"
    "    ok4, hata4 = bayraksiz_adim_kontrol()\n"
    "    ok, hatalar = kanca_kablo_serit_kontrol()\n"
    "    ok_s, hata_s = bayraksiz_adim_kontrol()\n"
    "    if ok and ok_s:\n"
    "        return 0\n"
    "    if ok4 and ok:\n"
    "        return 0\n"
    "    return 1\n")
_HT_OK4 = "    ok4, hata4 = bayraksiz_adim_kontrol()\n"
_HT_HUKUM = "    if ok and ok_s:\n        return 0\n"
_F = "bayraksiz_adim_kontrol()"

# (etiket, capa, ikame, beklenen_YESIL, NEDEN)
HUKUM_FUZZ_FIKSTURLERI = (
    # --- MESRU YAZIMLAR: rc=0 (sahte-kirmizi yuzeyi) ---
    ("M00 taban", None, None, True, "mutasyonsuz sekil"),
    ("M01 ara degisken", _HT_OK4,
     "    _s = %s\n    ok4, hata4 = _s\n" % _F, True, "tasiyici ad"),
    ("M02 iki adimli zincir", _HT_OK4,
     "    _a = %s\n    _b = _a\n    ok4, hata4 = _b\n" % _F, True, "sabit nokta 2 adim"),
    ("M03 try/except", _HT_OK4,
     "    try:\n        ok4, hata4 = %s\n    except Exception:\n"
     "        ok4, hata4 = %s\n" % (_F, _F), True, "iki dal da cagridan"),
    ("M04 kosullu atama", _HT_OK4,
     "    if hata4:\n        ok4, hata4 = %s\n    else:\n        ok4, hata4 = %s\n"
     % (_F, _F), True, "iki dal da cagridan"),
    ("M05 ternary", _HT_OK4,
     "    ok4, hata4 = %s if hata4 else %s\n" % (_F, _F), True, "IfExp iki kol"),
    ("M06 `or` zinciri", _HT_OK4,
     "    ok4, hata4 = %s or %s\n" % (_F, _F), True, "BoolOp tum degerler cagridan"),
    ("M07 coklu hedef", _HT_OK4,
     "    _t = ok4x = %s\n    ok4, hata4 = _t\n" % _F, True, "ikinci hedef TASIYICI"),
    ("M08 `*` unpack", _HT_OK4,
     "    ok4, *hata4 = %s\n" % _F, True, "Starred hedef"),
    ("M09 try/finally", _HT_OK4,
     "    try:\n        ok4, hata4 = %s\n    finally:\n        pass\n" % _F,
     True, "finally hukmu degistirmez"),
    ("M10 `with` blogu", _HT_OK4,
     "    with open('x') as _fh:\n        ok4, hata4 = %s\n" % _F, True, "ic blok"),
    ("M11 lambda araciligi", _HT_OK4,
     "    _f = lambda: %s\n    ok4, hata4 = _f()\n" % _F, True, "cagri yoluyla tuketim"),
    ("M12 dongude biriktirme (ILK atama SABIT)", _HT_OK4,
     "    ok4 = True\n    for _i in [1]:\n        ok4, hata4 = %s\n" % _F,
     False, "🔴 DOGRU KIRMIZI: ilk atama sabit literal"),
    ("M13 tuple ara degisken", _HT_OK4,
     "    _p = (%s,)\n    ok4, hata4 = _p[0]\n" % _F, True, "abone yoluyla tuketim"),
    ("M14 ic ice fonksiyon", _HT_OK4,
     "    def _ic():\n        return %s\n    ok4, hata4 = _ic()\n" % _F,
     True, "ic fonksiyon donusu"),
    ("M15 liste ara degisken", _HT_OK4,
     "    _l = [%s]\n    ok4, hata4 = _l[0]\n" % _F, True, "abone yoluyla tuketim"),
    # 🔴 SABIT-NOKTA DERINLIGI CIVISI (6. tur G3-v): `_cagri_turevli_adlar()`
    # yinelemesini `range(1)`e indirmek hicbir kolda kirmizi yakmiyordu. Bes adimli
    # tasiyici zinciri o zayiflatmayi TEK BASINA kirmizi yakar.
    # Zincirin BASI ic blokta, tuketimi DIS blokta: `ast.walk` BFS'i dis satirlari
    # ONCE gordugu icin TEK GECIS yetmez -> `range(8)` sabit-noktasi FIILEN olculur.
    ("M16 gec-cozulen tasiyici zinciriyle YENIDEN atama (sabit-nokta derinligi)",
     _HT_OK4,
     _HT_OK4 + "    if hata4:\n        _g1 = %s\n    _g2 = _g1\n    _g3 = _g2\n"
     "    ok4 = _g3\n" % _F, True,
     "ok4 zaten hukum degiskeni; ikinci atama UC ADIMLIK gec zincirden turer -> "
     "`range(8)` sabit-noktasi FIILEN olculur"),
    # --- SABOTAJ: rc=1 (kacis yuzeyi) ---
    ("S01 `ok4 = True`", _HT_OK4, _HT_OK4 + "    ok4 = True\n", False, "sabit literal"),
    ("S02 `ok4, hata4 = True, []`", _HT_OK4, _HT_OK4 + "    ok4, hata4 = True, []\n",
     False, "tuple sabit"),
    ("S03 `ok4 = bool(1)`", _HT_OK4, _HT_OK4 + "    ok4 = bool(1)\n",
     False, "🔴 6. tur deligi: NOBETCI OLMAYAN cagri"),
    ("S04 `ok4 = len([]) == 0`", _HT_OK4, _HT_OK4 + "    ok4 = len([]) == 0\n",
     False, "🔴 6. tur deligi: Compare + nobetci disi cagri"),
    ("S05 `ok4 = ok4 or True`", _HT_OK4, _HT_OK4 + "    ok4 = ok4 or True\n",
     False, "BoolOp'ta sabit dal"),
    ("S06 `ok4 = any([])`", _HT_OK4, _HT_OK4 + "    ok4 = any([])\n",
     False, "🔴 6. tur deligi: yerlesik cagri"),
    ("S07 ara degiskene SABIT", _HT_OK4,
     _HT_OK4 + "    _z = True\n    ok4 = _z\n", False,
     "tasiyici cagridan TUREMIYOR -> hukum yine ezilir"),
    ("S08 `globals()['ok4'] = True`", _HT_OK4,
     _HT_OK4 + "    globals()['ok4'] = True\n", False,
     "🔴 6. tur deligi: `Name` OLMAYAN hedef -> fail-closed"),
    # --- YESIL CIKIS BICIMLERI (G2): hukum SABITLENMEDIKCE mesru ---
    ("G2-A ternary `return`", _HT_HUKUM, "    return 0 if (ok and ok_s) else 1\n",
     True, "🔴 6. tur sahte-kirmizisi: `return 0` daraltmasi"),
    ("G2-B degiskene atayip `return`", _HT_HUKUM,
     "    _kod = 0 if (ok and ok_s) else 1\n    return _kod\n", True,
     "🔴 6. tur sahte-kirmizisi"),
    ("G2-C `sys.exit(0)`", _HT_HUKUM,
     "    if ok and ok_s:\n        sys.exit(0)\n", True,
     "🔴 6. tur sahte-kirmizisi"),
    ("G2-D erken `return 1` + dusme", _HT_HUKUM,
     "    if not (ok and ok_s):\n        return 1\n", True,
     "🔴 6. tur sahte-kirmizisi"),
    ("G2-E SABOTAJ `if True:`", _HT_HUKUM, "    if True:\n        return 0\n",
     False, "hukum SABITTEN geliyor"),
)


# ---- HUKUM DAVRANIS AYAGI (8. tur — SOZDIZIMDEN DAVRANISA) -----------------
# 🔴 NEDEN (7. tur, H1/H2/H3): yedi turdur her SOZDIZIMSEL daraltma ya sahte-kirmizi
# ya sahte-yesil uretti. "Hangi ad yargidir, hangi `if` hukumdur" sorusu AST'te
# KARAR VERILEBILIR DEGIL: `if ok or True:` · `if not False:` · `if 1 == 1:` ·
# `if bool(1):` · `if len([])==0:` · kosulun TAMAMEN silinmesi · `while True:` ·
# `_ = nobetci()` + sabit atama · yanlis tuple indisi · `all([])` ·
# `any([..., True])` — ON BIR sabotaj UC gate kolunun UCUNDE de YESIL geciyordu.
#
# SORU DEGISTI: "bu kod hukmu eziyor mu" (karar verilemez) YERINE
# "bir nobetci `False` DONERSE kol KIRMIZI yaniyor mu" (KARAR VERILEBILIR).
# Desen 3. turdaki `pre_push_kablo_kontrol()` kabuk ayaginin AYNISI: taklit degil
# DAVRANIS. Her nobetci TEK TEK `False` dondurulur, kollar UCTAN UCA kosulur ve
# rc'nin SIFIR-DISI oldugu olculur ([[mimar-kapi-parser-taklidi]]).
#
# MALIYET: modul BIR KEZ yuklenir; her vakada nobetciler MONKEYPATCH'lenir, yani
# GERCEK is (kesif, is akisi, 45 itme, fikstur bataryalari) HIC kosmaz. Olculen
# sey yalnizca KARAR MANTIGIDIR.
_STUB_JETONU = "SENTETIK-NOBETCI-KIRMIZISI"
# 🔴 DAVRANIS AYAGINDAN MUAF (GEREKCELI, kapsam degil KOSUM meselesi):
# `tutarlilik_kontrolu` YALNIZ `akislar is not None` yolunda cagrilir; davranis
# fiksturu ise KASTEN `akislar=None` ile kosar (kapsam/izin/alt-kume eksenlerinin
# kirmizisi karismasin, hukum TEK EKSENDEN gelsin). Kayit defterinde DURUR —
# yani cagri satirinin silinmesi yine KIRMIZI yakar; yalniz STUB olcumu disidir.
_DAVRANIS_MUAF = {
    "tutarlilik_kontrolu":
        "yalniz akislar is not None yolunda kosar; davranis fiksturu tek eksen "
        "kalsin diye akislar=None ile kosuyor",
}


def _davranis_modulu(kaynak=None):
    """Kendi kaynagini AYRI bir modul olarak yukler (canli modul KIRLENMEZ).

    <kaynak> verilirse O METIN yuklenir — TEST SEAMI: davranis fiksturu sabotaj
    varyantlarini boyle olcer. Uretimde daima None gelir ve KOSAN dosya okunur."""
    kaynak_yol = os.path.abspath(__file__)
    if kaynak is None:
        with open(kaynak_yol, encoding="utf-8") as f:
            kaynak = f.read()
    mod = types.ModuleType("_ci_kapsam_davranis")
    mod.__file__ = kaynak_yol
    mod.__pruvo_kaynak__ = kaynak      # evren BU metinden turer (bkz. _nobetci_evreni)
    exec(compile(kaynak, kaynak_yol, "exec"), mod.__dict__)
    mod.__pruvo_kaynak__ = kaynak      # exec `__dict__`i ezebilir -> yeniden yaz
    return mod


# 🔴 EVREN ARTIK CAGRI GRAFINDAN TURER, AD DESENINDEN DEGIL (10. tur, J3).
# OLCULEN KOK NEDEN: ada dayali her tanim bu depoda bayatladi. `_NOBETCI_CAGRI_RE`
# ile turetilen evren 24 ad veriyordu; bunun 6'si NOBETCI DEGILDI (ozel alt-kontrol
# ya da liste donduren alt-rutin) ve desen disi adlandirilan yeni bir nobetci
# (`*_denetimi`) SESSIZCE kapsam disi kaliyordu — butun kapilar 8/8 YESIL.
#
# YENI TANIM (ad TAMAMEN onemsiz): bir fonksiyon NOBETCIDIR ancak ve ancak
#   (1) KOK fonksiyonlardan (`denetle` / `main`) FIILEN cagriliyorsa,
#   (2) donusu `<hukum>, <hata>` biciminde IKILI demete aciliyorsa,
#   (3) ve o `<hata>` adi AYNI kok fonksiyonda bir `for` dongusunun iterable'i
#       oluyorsa (= bulgulari raporlanan/hukme katilan gercek (ok, hata) sozlesmesi).
# Bu uc sart birlikte veri ureticilerini (`kosulan_coklu`, `dosya_metinleri_oku`,
# `bayrak_envanteri`) DISARIDA birakir ve desen disi adli bir nobetciyi
# KENDILIGINDEN kapsar ([[envanter-drift-parti-basina]] · [[ikiz-tanim-sessiz-ayrisma]]).
NOBETCI_KOK_FONKSIYONLARI = ("denetle", "main")


def _sozlesme_evreni(kaynak):
    """{nobetci_adi: {kok_fonksiyon, ...}} — CAGRI GRAFI + (ok, hata) sozlesmesi."""
    agac = ast.parse(kaynak)
    modul_fn = {d.name for d in agac.body if isinstance(d, ast.FunctionDef)}
    evren = {}
    for d in agac.body:
        if not (isinstance(d, ast.FunctionDef)
                and d.name in NOBETCI_KOK_FONKSIYONLARI):
            continue
        # AYNI kok fonksiyonda `for <ad> in <Name>:` biciminde donulen adlar.
        dongu_adlari = {n.iter.id for n in ast.walk(d)
                        if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)}
        for alt in ast.walk(d):
            if not isinstance(alt, ast.Assign) or not isinstance(alt.value, ast.Call):
                continue
            f = alt.value.func
            if not (isinstance(f, ast.Name) and f.id in modul_fn):
                continue
            # KOK fonksiyonlar kendileri nobetci DEGILDIR (`kod, satirlar = denetle()`
            # sekle uyar ama o, yargilanan GOVDEDIR — yargilayan degil).
            if f.id in NOBETCI_KOK_FONKSIYONLARI:
                continue
            for hedef in alt.targets:
                if not (isinstance(hedef, ast.Tuple) and len(hedef.elts) == 2):
                    continue
                ikinci = hedef.elts[1]
                if isinstance(ikinci, ast.Name) and ikinci.id in dongu_adlari:
                    evren.setdefault(f.id, set()).add(d.name)
    return evren


def _nobetci_evreni(mod):
    """NOBETCI adlari — CAGRI GRAFINDAN (modulun YUKLENDIGI kaynak ayristirilir).

    🔴 KAYNAK MODULE ILISTIRILIR (`__pruvo_kaynak__`): mutasyon surucusu mutant
    METNI yukluyor; `mod.__file__` okunsaydi evren DAIMA pristine dosyadan turer
    ve evren mutantlari SESSIZCE gecerdi."""
    kaynak = getattr(mod, "__pruvo_kaynak__", None)
    if kaynak is None:
        try:
            with open(mod.__file__, encoding="utf-8") as f:
                kaynak = f.read()
        except OSError:
            return []
    return sorted(_sozlesme_evreni(kaynak))


# 🔴 SURE TAVANI (9. tur, I1-d): stub kurulamazsa GERCEK is kosar ve ozyineleme
# yuzunden kollar ASILIR. Fail-fast guard'i bunu ONLER, bu tavan ise SON EMNIYETTIR:
# bir kol bu sureyi asarsa hukum "asildi" degil ACIK BIR KIRMIZI olur. Saglam
# kosumda uc kolun toplami ~0,14 sn; tavan iki kat buyuklukte tutuldu.
_KOL_SURE_TAVANI_SN = 30.0


def _sure_tavani_dene(baslangic, kol):
    """Tavan asildiysa ASILMAYI acik bir hataya cevir (sessiz bekleme YOK)."""
    gecen = time.monotonic() - baslangic
    if gecen > _KOL_SURE_TAVANI_SN:
        raise TimeoutError(
            "DAVRANIS AYAGI SURE TAVANINI ASTI (%s kolu, %.1f sn > %.0f sn): stub "
            "kurulamamis ve GERCEK is kosuyor olabilir (ozyineleme). Bloklayici bir "
            "kapida ASILMA hukumsuzluktur; bu yuzden KIRMIZI'ya cevrildi."
            % (kol, gecen, _KOL_SURE_TAVANI_SN))


def _kollari_kos(mod):
    """(bayraksiz_rc, kanca_kablo_rc, kendini_test_rc) — UC KOLUN KARAR MANTIGI.

    Nobetciler zaten STUB'landigi icin GERCEK is kosmaz; olculen sey yalnizca
    "nobetci sonucu kolun cikis koduna giriyor mu"dur.
    🔴 SURE TAVANI asilirsa `TimeoutError` atilir — cagiran onu KIRMIZI'ya cevirir;
    asilma sessizce "olcum" sayilmaz."""
    baslangic = time.monotonic()
    eski_argv, eski_cikti = sys.argv, sys.stdout
    sys.stdout = io.StringIO()
    try:
        # BAYRAKSIZ kol: denetle() KARAR govdesi (kontroller=True -> nobetciler kosar).
        # Girdi KASTEN bos: kapsam/izin ekseninden KIRMIZI gelmesin, tek eksen kalsin.
        kod_b, _s = mod.denetle("", [], {}, kontroller=True, akislar=None)
        _sure_tavani_dene(baslangic, "BAYRAKSIZ")
        sys.argv = ["ci-kapsam-test.py", mod.KANCA_KABLO_BAYRAGI]
        kod_k = mod.main()
        _sure_tavani_dene(baslangic, mod.KANCA_KABLO_BAYRAGI)
        sys.argv = ["ci-kapsam-test.py", mod.KENDINI_TEST_BAYRAGI]
        kod_t = mod.main()
        _sure_tavani_dene(baslangic, mod.KENDINI_TEST_BAYRAGI)
    finally:
        sys.argv, sys.stdout = eski_argv, eski_cikti
    return kod_b, kod_k, kod_t


def hukum_davranis_kontrol(kaynak=None):
    """🔴 HUKUM EZME SINIFI — DAVRANISTAN olculur (sozdiziminden DEGIL).

    Iddialar:
      D0 TABAN — TUM nobetciler `True` donerken UC kol da rc=0 (yoksa kirmizi
         'hep kirmizi'dan ayirt edilemez).
      D1..Dn HER NOBETCI TEK TEK — nobetci `False` dondugunde onu CAGIRAN her kol
         SIFIR-DISI donmeli. Bir nobetci kapsanmazsa onun hukmu ezilebilir kalir.
    (ok, hatalar) dondurur; hicbir sey BASMAZ."""
    hata = []
    try:
        mod = _davranis_modulu(kaynak)
    except Exception as e:  # noqa: BLE001 — cokme KIRMIZI ile KARISTIRILMAZ
        return False, ["HUKUM DAVRANISI OLCULEMEDI: modul kopyasi yuklenemedi "
                       "(%s: %s)" % (type(e).__name__, e)]
    evren = _nobetci_evreni(mod)
    # 🔴 FAIL-FAST, FAIL-SLOW DEGIL (9. tur, I1-d): eski surum hata EKLIYOR ama
    # RETURN ETMIYORDU. Akis devam edip HICBIR nobetciyi stub'lamadan
    # `_kollari_kos()` cagiriyor, `--kendini-test` kolu bu ayagi YENIDEN cagiriyor
    # (ozyineleme) ve 45 gercek itme her katmanda tekrarlaniyordu -> UC KOL DA
    # >150 sn ASILDI (ilk olcumde 46+ dk). Bloklayici bir kapida ASILMA, kirmizi
    # DEGILDIR: terminal doner, hukum YOKTUR — "olculemedi"nin de otesinde ucuncu
    # bir hal ([[hukum-yanlis-birimde]]). Stub kurulamiyorsa HUKUM VERILMEZ.
    # 🔴 TABAN GERCEGE BAGLI: eski taban 14 iken gercek evren 24'tu; 9 nobetci
    # dusse tetiklenmiyordu. Taban artik KAYIT DEFTERINDEN turer (iki kolun
    # birlesimi) -> defter buyuyunce taban da buyur, elle bakim YOK.
    kayit = dict(NOBETCI_KABLOLARI)
    defter_birlesimi = set()
    for _a, _g in NOBETCI_KABLOLARI:
        defter_birlesimi |= set(_g)
    if len(evren) < len(defter_birlesimi):
        return False, ["NOBETCI EVRENI KUCULDU (fail-closed, HUKUM VERILMEDI): %d "
                       "nobetci bulundu, KAYIT DEFTERI %d ad istiyor (eksik: %s) -> "
                       "`_NOBETCI_CAGRI_RE` bozulmus ya da nobetciler yeniden "
                       "adlandirilmis olabilir. Stub kurulamadigi icin olcum "
                       "YAPILMADI."
                       % (len(evren), len(defter_birlesimi),
                          ", ".join(sorted(defter_birlesimi - set(evren))[:6]) or "-")]
    # Hangi kol hangi nobetciyi cagiriyor (KAYIT DEFTERINDEN — `_kol_kapsam_kontrol`
    # defterin GERCEK cagrilarla ESIT oldugunu ayrica olcer).
    kol_kaydi = {"bayraksiz": set(kayit.get("denetle", ())),
                 "kanca-kablo": set(KANCA_KABLO_KOL_NOBETCILERI),
                 "kendini-test": set(kayit.get("main", ()))
                 - set(KANCA_KABLO_KOL_NOBETCILERI)}
    saklanan = {ad: getattr(mod, ad) for ad in evren}

    def kur(yalan_donen=None):
        for ad in evren:
            if ad == yalan_donen:
                setattr(mod, ad, lambda *a, **k: (False, [_STUB_JETONU]))
            else:
                setattr(mod, ad, lambda *a, **k: (True, []))

    try:
        kur(None)
        taban = _kollari_kos(mod)
        if taban != (0, 0, 0):
            hata.append(
                "D0 TABAN KIRMIZI: TUM nobetciler `True` donerken kollar %r (beklenen "
                "(0,0,0)) -> asagidaki kirmizilar 'hep kirmizi'dan AYIRT EDILEMEZ."
                % (taban,))
            return False, hata
        for ad in evren:
            kur(ad)
            kod_b, kod_k, kod_t = _kollari_kos(mod)
            olculen = {"bayraksiz": kod_b, "kanca-kablo": kod_k, "kendini-test": kod_t}
            for kol, kume in kol_kaydi.items():
                if ad not in kume or ad in _DAVRANIS_MUAF:
                    continue
                if olculen[kol] == 0:
                    hata.append(
                        "HUKUM EZILIYOR (%s kolu): `%s()` `False` donduruyor ama kol "
                        "rc=0 (YESIL) veriyor -> o nobetcinin sonucu kolun cikis koduna "
                        "GIRMIYOR. Sinif: `if ok or True:` / kosulun silinmesi / "
                        "`_ = nobetci()` / yanlis tuple indisi — sozdizimsel kural "
                        "bunlari GOREMEZ, davranis GORUR ([[beyan-edilmis-survivor]])."
                        % (kol, ad))
    except Exception as e:  # noqa: BLE001
        hata.append("HUKUM DAVRANISI OLCULEMEDI: %s: %s" % (type(e).__name__, e))
    finally:
        for ad, deger in saklanan.items():
            setattr(mod, ad, deger)
    return (not hata), hata


# ---- 7. TURUN 11 KACISI + KONTROLLER — DAVRANIS AYAGINDA KALICI FIKSTUR ----
# 🔴 Bu tablo, sozdizimsel kuralin GORMEDIGI on bir sabotajin DAVRANIS ayaginda
# yakalandigini KALICI olarak civiler. Sabotajlar GERCEK kaynak metnine uygulanir
# (bellekte), ucuncu kolun hukum blogu hedeflenir. Tablo kucultulurse kirmizi yanar.
# (AYNI GEREKCE: parcali yazim, GERCEK hukum satirinin ikizini uretmemek icin.)
_DK_HUKUM = ("        if ok and ok_s and %s:\n"
             "            print(\"SONUC: YESIL ✅\")\n" % "ok_d")
# 🔴 PARCALI YAZIM (bilincli): duz yazilsaydi bu sabit, GERCEK `main()` satiriyla
# BIREBIR ayni metni ikinci kez uretir ve mutasyon capalari "2 kez gecti" diye
# COKERDI ([[mutasyon-kaniti-yeniden-uretilebilir]]: cokme kirmiziyla karisir).
_DK_OKS = "        ok_s, hata_s = %s()\n" % "kanca_kablo_serit_kontrol"

# (etiket, capa, ikame, beklenen_YESIL, NEDEN)
HUKUM_DAVRANIS_FIKSTURLERI = (
    ("D00 taban (mutasyonsuz)", None, None, True, "kirmizilar ayirt edilebilsin"),
    ("H1-a `if True:`", _DK_HUKUM,
     "        if True:\n            print(\"SONUC: YESIL ✅\")\n", False, "literal"),
    ("H1-b `if ok or True:`", _DK_HUKUM,
     "        if ok or True:\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: sabit-degerli BoolOp"),
    ("H1-c `if not False:`", _DK_HUKUM,
     "        if not False:\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: UnaryOp"),
    ("H1-d `if 1 == 1:`", _DK_HUKUM,
     "        if 1 == 1:\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: Compare"),
    ("H1-e `if bool(1):`", _DK_HUKUM,
     "        if bool(1):\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: yerlesik cagri"),
    ("H1-f `if len([]) == 0:`", _DK_HUKUM,
     "        if len([]) == 0:\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: cagri + Compare"),
    ("H1-g hukum kosulu TAMAMEN silindi", _DK_HUKUM,
     "        if True:\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: kosulsuz yesil cikis"),
    ("H1-h `while True:` + yesil cikis", _DK_HUKUM,
     "        while True:\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: `if` DISI dongu"),
    ("H3-1 `_ = nobetci()` + sabit atama", _DK_OKS,
     "        _ = kanca_kablo_serit_kontrol()\n        ok_s, hata_s = True, []\n",
     False, "🔴 7. tur kacisi: donus HIC kullanilmiyor"),
    ("H3-5 tuple'dan YANLIS indis", _DK_OKS,
     "        _r = kanca_kablo_serit_kontrol()\n        hata_s, ok_s = _r[0], _r[1]\n",
     False, "🔴 7. tur kacisi: ok/hata yer degistirdi"),
    ("H3-6 hukum `all([])`", _DK_HUKUM,
     "        if all([]):\n            print(\"SONUC: YESIL ✅\")\n", False,
     "🔴 7. tur kacisi: bos kume daima True"),
    ("H3-7 hukum `any([ok, ok_s, True])`", _DK_HUKUM,
     "        if any([ok, ok_s, True]):\n            print(\"SONUC: YESIL ✅\")\n",
     False, "🔴 7. tur kacisi: sabit dal"),
    ("H3-8 `ok` sonradan sabitle eziliyor", _DK_OKS,
     _DK_OKS + "        ok_s = True\n", False, "ikinci atama sabit"),
    # --- KONTROLLER: MESRU yazimlar YESIL kalmali (sahte-kirmizi yuzeyi) ---
    ("K-1 `bool(...)` sarmali", _DK_HUKUM,
     "        if bool(ok and ok_s and ok_d):\n"
     "            print(\"SONUC: YESIL ✅\")\n", True,
     "sabit DEGIL, hukum degiskenlerinden turer"),
    ("K-2 ara degisken", _DK_HUKUM,
     "        _karar = ok and ok_s and ok_d\n        if _karar:\n"
     "            print(\"SONUC: YESIL ✅\")\n", True, "tasiyici ad"),
    ("K-3 ters kosul", _DK_HUKUM,
     "        if not (ok and ok_s and ok_d):\n            pass\n"
     "        elif ok and ok_s and ok_d:\n"
     "            print(\"SONUC: YESIL ✅\")\n", True, "negatif yazim"),
    ("K-4 `all([...])` hukum degiskenleriyle", _DK_HUKUM,
     "        if all([ok, ok_s, ok_d]):\n            print(\"SONUC: YESIL ✅\")\n",
     True, "`all` MESRU olabilir — icerik sabit degil"),
)


def hukum_davranis_fikstur_kontrol():
    """7. turun 11 kacisi + 4 kontrol — DAVRANIS ayaginda iki yonlu olcum."""
    hata = []
    kaynak_yol = os.path.abspath(__file__)
    try:
        with open(kaynak_yol, encoding="utf-8") as f:
            taban = f.read()
    except OSError as e:
        return False, ["HUKUM DAVRANIS FIKSTURU OLCULEMEDI: kaynak okunamadi: %s" % e]
    for etiket, capa, ikame, beklenen_yesil, neden in HUKUM_DAVRANIS_FIKSTURLERI:
        kaynak = taban
        if capa is not None:
            if kaynak.count(capa) != 1:
                hata.append("HUKUM DAVRANIS FIKSTURU OLCULEMEDI (%s): capa %d kez "
                            "gecti (beklenen 1) — cokme KIRMIZI SAYILMAZ"
                            % (etiket, kaynak.count(capa)))
                continue
            kaynak = kaynak.replace(capa, ikame)
        ok, bulgular = hukum_davranis_kontrol(kaynak=kaynak)
        if ok != beklenen_yesil:
            hata.append(
                "HUKUM DAVRANIS FIKSTURU DUSTU (%s): beklenen=%s gelen=%s · %s · %r"
                % (etiket, "YESIL" if beklenen_yesil else "KIRMIZI",
                   "YESIL" if ok else "KIRMIZI", neden, [b[:80] for b in bulgular[:2]]))
    mesru = sum(1 for _e, _c, _i, y, _n in HUKUM_DAVRANIS_FIKSTURLERI if y)
    sabotaj = len(HUKUM_DAVRANIS_FIKSTURLERI) - mesru
    if mesru < 5 or sabotaj < 13:
        hata.append("HUKUM DAVRANIS TABLOSU KUCULDU (mesru %d, sabotaj %d; taban 5/13) "
                    "— tabloyu kucultmek nobetciyi SESSIZCE oldurur "
                    "([[fikstur-degeri-mutasyon-koru]])." % (mesru, sabotaj))
    return (not hata), hata


def hukum_fuzz_kontrol():
    """23+ varyantlik IKI YONLU fuzz — kural ne sizdiriyor ne sahte-kirmizi yakiyor.

    Mesru yazimlar YESIL, sabotajlar KIRMIZI olmali. Tablo KUCULURSE kirmizi yanar."""
    hata = []
    for etiket, capa, ikame, beklenen_yesil, neden in HUKUM_FUZZ_FIKSTURLERI:
        kaynak = _HUKUM_TABAN_KAYNAK
        if capa is not None:
            if kaynak.count(capa) != 1:
                hata.append("HUKUM FUZZ OLCULEMEDI (%s): capa %d kez gecti (beklenen 1)"
                            % (etiket, kaynak.count(capa)))
                continue
            kaynak = kaynak.replace(capa, ikame)
        try:
            bulgular = _kendini_test_hukum_kontrol(ast.parse(kaynak))
        except SyntaxError as e:
            hata.append("HUKUM FUZZ OLCULEMEDI (%s): fikstur kaynagi ayristirilamadi "
                        "(%s) — cokme KIRMIZI SAYILMAZ" % (etiket, e))
            continue
        yesil = not bulgular
        if yesil != beklenen_yesil:
            hata.append(
                "HUKUM FUZZ DUSTU (%s): beklenen=%s gelen=%s · %s · bulgular=%r"
                % (etiket, "YESIL" if beklenen_yesil else "KIRMIZI",
                   "YESIL" if yesil else "KIRMIZI", neden,
                   [b[:90] for b in bulgular]))
    mesru = sum(1 for _e, _c, _i, y, _n in HUKUM_FUZZ_FIKSTURLERI if y)
    sabotaj = len(HUKUM_FUZZ_FIKSTURLERI) - mesru
    if mesru < 19 or sabotaj < 10:
        hata.append("HUKUM FUZZ TABLOSU KUCULDU (mesru %d, sabotaj %d; taban 19/10) — "
                    "tabloyu kucultmek nobetciyi SESSIZCE oldurur "
                    "([[fikstur-degeri-mutasyon-koru]])." % (mesru, sabotaj))
    return (not hata), hata


def _kendini_test_hukum_kontrol(agac):
    """main()'in `--kendini-test` hukmu: TUM `okN`ler `and` ile hukme giriyor mu."""
    hata = []
    main_dugum = next((d for d in ast.walk(agac)
                       if isinstance(d, ast.FunctionDef) and d.name == "main"), None)
    if main_dugum is None:
        return ["KENDINI-TEST HUKMU OLCULEMEDI: main() bulunamadi (dosya yeniden "
                "duzenlendiyse nobetciyi guncelle)."]
    # 🔴 KURAL ANLAMSAL, SOZDIZIMSEL DEGIL (5. tur, F3+D1). Iki ders birden:
    #  (a) SAHTE-KIRMIZI: "TAM BIR KEZ ve DOGRUDAN `Call`" kurali UC MESRU yazimi
    #      (try/except, kosullu atama, ara degisken) BLOKLAYICI kolda kirmizi
    #      yakiyordu; mesru bir refactor tum ekibin itmesini durdururdu
    #      ([[kapi-anchor-coupling-ikilemi]] · 3. turdaki `${rc}` dersi).
    #  (b) KAPSAM: kural yalniz `ok\d+` adlarini goruyordu; ucuncu kolun `ok`/`ok_s`
    #      degiskenleri desen disindaydi ve `if True:` mutanti 5/5 yesil geciyordu.
    # YENI KURAL: HUKUM DEGISKENI = govdede bir NOBETCI CAGRISINDAN deger alan ad.
    # Her boyle ada yapilan HER atamanin degeri CAGRIDAN TUREMELI (dogrudan, ara
    # degisken uzerinden ya da her dali cagridan gelen kosullu/try yapisiyla), ve
    # her hukum degiskeni EN AZ BIR `if` kosulunda GORUNMELI.
    turevli = _cagri_turevli_adlar(main_dugum)
    # HUKUM DEGISKENI = bir NOBETCI cagrisinin BIRINCI (boolean) donusunu alan ad.
    # Ikinci donus (`hataN`) tani listesidir, hukum degildir — kapsam sorusu ona
    # sorulmaz (olculdu: sorulunca 13 sahte-kirmizi ureti).
    # 🔴 `Name` OLMAYAN ATAMA HEDEFI = FAIL-CLOSED (6. tur, S08): `globals()['ok4']`
    # / `setattr(...)` / `obj.ok4` / `d['ok4']` bicimleri HIC INCELENMIYORDU ve
    # `globals()['ok4'] = True` sabotaji DORT KOLDA da YESIL geciyordu. Bu bicimler
    # main() icinde MESRU degildir; gorulurse hukum verilemez.
    for d in ast.walk(main_dugum):
        if not isinstance(d, ast.Assign):
            continue
        for hedef in d.targets:
            for alt in ([hedef] if not isinstance(hedef, ast.Tuple) else hedef.elts):
                if isinstance(alt, (ast.Subscript, ast.Attribute)):
                    hata.append(
                        "KENDINI-TEST HUKMU OLCULEMEZ (fail-closed): main()'de `Name` "
                        "OLMAYAN atama hedefi var (satir %d, %s) -> `globals()['okN']"
                        " = True` sinifi ezme AST ekseninde gorunmez olur."
                        % (getattr(d, "lineno", -1), type(alt).__name__))
    for d in ast.walk(main_dugum):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) \
                and d.func.id in ("setattr", "exec", "eval"):
            hata.append("KENDINI-TEST HUKMU OLCULEMEZ (fail-closed): main()'de `%s(...)` "
                        "cagrisi var (satir %d) -> hukum degiskeni AST disindan "
                        "ezilebilir." % (d.func.id, getattr(d, "lineno", -1)))
    # 🔴 TASIYICI SORUNU ARTIK YAPISAL OLARAK YOK (6. tur, M07/M11/M13/M15): "hangi
    # ad yargidir" sorusu kaldirildi. Bir ad ancak KENDISINE bir NOBETCI cagrisi
    # atanmissa hukum degiskenidir; tasiyicilar (`_s`, `_f`, `_p`, `_l`, ikinci
    # hedef `ok4x`) zaten dogru dogru cevap verir ve KAPSAM sorusu HIC sorulmaz.
    okler = set()
    for d in ast.walk(main_dugum):
        if not isinstance(d, ast.Assign) or not _nobetci_cagrisi_mi(d.value):
            continue
        for hedef in d.targets:
            if isinstance(hedef, ast.Tuple) and hedef.elts:
                ilk = hedef.elts[0]
                if isinstance(ilk, ast.Name):
                    okler.add(ilk.id)
            elif isinstance(hedef, ast.Name):
                okler.add(hedef.id)
    for ad in sorted(okler):
        for d in ast.walk(main_dugum):
            if not isinstance(d, ast.Assign):
                continue
            for hedef in d.targets:
                for a2, deger in _hedef_deger_ciftleri(hedef, d.value):
                    if a2 != ad:
                        continue
                    if not _cagridan_mi(deger, turevli):
                        hata.append(
                            "KENDINI-TEST HUKMU ATLANIYOR: `%s` degiskenine CAGRIDAN "
                            "TUREMEYEN bir deger atanmis (satir %d) -> nobetcinin "
                            "sonucu hukme girmeden ezilmis olur; cagri durur, hukum "
                            "coper." % (ad, getattr(d, "lineno", -1)))
    # 🔴 "KAPSAM DISI" EKSENI KALDIRILDI (6. tur karari, ALTI SAHTE-KIRMIZI):
    # "her hukum degiskeni `return 0` iceren bir `if` kosulunda gorunmeli" varsayimi
    # ALTI MESRU yazimi (M07/M11/M13/M15 tasiyicilar + G2-A/B/C/D yesil-cikis
    # bicimleri: ternary `return`, degiskene atayip `return`, `sys.exit(0)`,
    # erken-`return 1`+dusme) BLOKLAYICI pre-push kolunda kirmizi yakiyordu. "Hangi
    # ad yargidir" ve "hangi `if` hukumdur" sorularinin ikisi de SOZDIZIMSEL olarak
    # KARAR VERILEBILIR DEGIL; her daraltma yeni bir mesru bicimi disari atiyor
    # ([[tekil-yama-sinifi-kapatmaz]] · [[kapi-anchor-coupling-ikilemi]]).
    # YERINE: hukmu SABITLEYEN tek somut bicim dogrudan yasaklanir. Mesru kodda
    # `if <sabit>:` YOKTUR; sahte-kirmizi yuzeyi sifirdir, `if True:` sabotaji ise
    # TEK BASINA kirmizi yakar (olculdu: G2-E rc=1, G2-A..D rc=0).
    for d in ast.walk(main_dugum):
        if isinstance(d, ast.If) and isinstance(d.test, ast.Constant):
            hata.append(
                "KENDINI-TEST HUKMU SABITLENMIS: main()'de `if %r:` var (satir %d) -> "
                "kolun hukmu nobetci sonucundan degil SABITTEN geliyor; olcum sessizce "
                "cope gider ([[beyan-edilmis-survivor]])."
                % (d.test.value, getattr(d, "lineno", -1)))
    # HUKUM BIRLESTIRICISI `and` OLMALI — HER kol icin AYRI AYRI. (Eski surum tek
    # bir global BoolOp ariyor ve "payi olmayan" listesini TUM kollar uzerinden
    # cikariyordu; ucuncu kolun `ok`/`ok_s`u eklenince o liste SAHTE-KIRMIZI
    # uretiyordu — kapsam iddiasi zaten yukaridaki KAPSAM DISI kontrolunde.)
    hukum_sayisi = 0
    for d in ast.walk(main_dugum):
        if not (isinstance(d, ast.If) and isinstance(d.test, ast.BoolOp)):
            continue
        adlar = {n.id for n in ast.walk(d.test) if isinstance(n, ast.Name)}
        if len(adlar & okler) < 2:
            continue
        hukum_sayisi += 1
        if not isinstance(d.test.op, ast.And):
            hata.append(
                "KENDINI-TEST HUKMU `and` DEGIL (satir %d, %s): tek bir nobetci "
                "yesilse kol YESIL dondurur -> o kollar ARTIK KIRMIZI YAKAMAZ."
                % (getattr(d, "lineno", -1), type(d.test.op).__name__))
    if hukum_sayisi == 0 and okler:
        hata.append("KENDINI-TEST HUKMU BULUNAMADI: main()'de nobetci sonuclarini "
                    "birlestiren bir BoolOp kosulu YOK -> kol hukmu baska bir bicime "
                    "tasinmis olabilir; nobetci OLU kalmasin diye fail-closed.")
    return hata


def _suzgec_cagrilari(fonksiyon_dugumu):
    """<fonksiyon_dugumu> govdesinde `SUZGEC.<uye>(...)` biciminde cagrilan uye adlari."""
    adlar = set()
    for alt in ast.walk(fonksiyon_dugumu):
        if not isinstance(alt, ast.Call):
            continue
        f = alt.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id == "SUZGEC":
            adlar.add(f.attr)
    return adlar


def _yaml_oku_cagrilari(fonksiyon_dugumu):
    """<fonksiyon_dugumu> govdesinde `YAML_OKU.<uye>(...)` biciminde cagrilan uye adlari."""
    adlar = set()
    for alt in ast.walk(fonksiyon_dugumu):
        if not isinstance(alt, ast.Call):
            continue
        f = alt.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id == "YAML_OKU":
            adlar.add(f.attr)
    return adlar


def _duz_cagrilar(fonksiyon_dugumu):
    """<fonksiyon_dugumu> govdesinde `<ad>(...)` biciminde cagrilan DUZ isim adlari."""
    adlar = set()
    for alt in ast.walk(fonksiyon_dugumu):
        if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name):
            adlar.add(alt.func.id)
    return adlar


def suzgec_kablosu_kontrol(kaynak=None):
    """SUZGEC + NOBETCI + HUKUM KABLOSU NOBETCISI — AST uzerinden.

    <kaynak> verilirse dosya yerine O METIN ayristirilir. TEST SEAMI: mutasyon
    surucusu (`kesif-kapsam-mutasyon.py`) kablo mutantlarini boyle olcer; gercek
    kosumda daima None gelir ve nobetci KENDI dosyasini okur.

    OLCULEN RISK: suzgec dosyasi repoda dursun, fiksturleri de gecsin, ama
    `kosulan()` icindeki `SUZGEC.cagri_sayilir(...)` cagrisi SILINSIN -> kapi
    30 Tem oncesi haline (duz capa) doner ve `--help` sinifi yeniden sessizlesir;
    suzgec_fikstur_kontrol() bunu GORMEZ (suzgec dogru cevap veriyor, ona kimse
    sormuyor).

    YONTEM: kendi kaynagini `ast` ile ayristirir; SUZGEC_KABLOLARI'ndaki her
    fonksiyonun govdesinde `SUZGEC.<uye>(...)` cagrisi arar. Metin capasi DEGIL —
    bicimlendirme/yeniden-adlandirma sahte-kirmizi yakmasin
    ([[kapi-anchor-coupling-ikilemi]]).

    🔴 KABUL EDILEN SINIR (sonsuz geriye gidis burada KESILIR, mevcut beyanla ayni):
    BU fonksiyonun denetle()/main() icinden cagrisi kendi basina nobetsizdir. Yani
    "hem suzgec cagrisini hem bu nobetci cagrisini birden silen" IKI ADIMLI mutasyon
    kacar; tek-adimli mutasyon kapsanir (ust kat tools/nobetci-mutasyon-test.py
    sinifidir).
    (ok, hata_satirlari) dondurur."""
    if kaynak is None:
        kaynak_yol = os.path.abspath(__file__)
        try:
            with open(kaynak_yol, encoding="utf-8") as f:
                kaynak = f.read()
        except OSError as e:
            return False, ["SUZGEC KABLOSU OLCULEMEDI: kendi kaynagi okunamadi (%s)" % e]
    try:
        agac = ast.parse(kaynak)
    except SyntaxError as e:
        return False, ["SUZGEC KABLOSU OLCULEMEDI: kendi kaynagi ayristirilamadi (%s)" % e]
    bulunan = {}
    yaml_bulunan = {}
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef):
            bulunan[dugum.name] = _suzgec_cagrilari(dugum)
            yaml_bulunan[dugum.name] = _yaml_oku_cagrilari(dugum)
    hata = []
    for ad, gerekli in AYRISTIRICI_KABLOLARI:
        if ad not in yaml_bulunan:
            hata.append("AYRISTIRICI KABLOSU BAYAT: %s() fonksiyonu bulunamadi -> dosya "
                        "yeniden duzenlendiyse AYRISTIRICI_KABLOLARI'ni guncelle" % ad)
            continue
        if not (yaml_bulunan[ad] & set(gerekli)):
            hata.append("AYRISTIRICI KABLOSU KOPMUS: %s() govdesinde YAML_OKU.%s cagrisi "
                        "YOK -> kapi GERCEK YAML ayristiricisini artik SORMUYOR ve METIN "
                        "TAKLIDINE dusuyor. Olculdu (30 Tem, 1037 kiyaslanabilir girdi): "
                        "taklit ile gercek ayristirici 303 girdide FARKLI hukum veriyor "
                        "(29'u sahte-YESIL bilesenli). GERI KOY."
                        % (ad, "/".join(gerekli)))
    for ad, gerekli in SUZGEC_KABLOLARI:
        if ad not in bulunan:
            hata.append("SUZGEC KABLOSU BAYAT: %s() fonksiyonu bulunamadi -> dosya "
                        "yeniden duzenlendiyse SUZGEC_KABLOLARI'ni guncelle" % ad)
            continue
        if not (bulunan[ad] & set(gerekli)):
            hata.append("SUZGEC KABLOSU KOPMUS: %s() govdesinde SUZGEC.%s cagrisi YOK "
                        "-> ortak 'gercek icra mi' suzgeci artik sorulmuyor, `--help` / "
                        "`echo` sinifi kacislari yeniden SESSIZ olur. GERI KOY."
                        % (ad, "/".join(gerekli)))
    # NOBETCI KABLOLARI — nobetci CAGRILARI yerinde mi (capraz nobet, bkz. sabit yorumu)
    duz = {}
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef):
            duz[dugum.name] = _duz_cagrilar(dugum)
    for ad, gerekli in TANI_KABLOLARI:
        if ad not in duz:
            hata.append("TANI KABLOSU BAYAT: %s() fonksiyonu bulunamadi -> dosya "
                        "yeniden duzenlendiyse TANI_KABLOLARI'ni guncelle" % ad)
            continue
        eksik = [g for g in gerekli if g not in duz[ad]]
        if eksik:
            hata.append("TANI KABLOSU KOPMUS: %s() govdesinde %s cagrisi YOK -> kapi "
                        "KIRMIZI yandiginda ARTIK 'hangi adimda hangi bicimde ne gordum' "
                        "demiyor, yalniz 'cagri YOK' diyor (T3/Y05 gerilemesi). GERI KOY."
                        % (ad, ", ".join(eksik)))
    for ad, gerekli in KATLAMA_KABLOLARI:
        if ad not in duz:
            hata.append("KATLAMA KABLOSU BAYAT: %s() fonksiyonu bulunamadi -> dosya "
                        "yeniden duzenlendiyse KATLAMA_KABLOLARI'ni guncelle" % ad)
            continue
        eksik = [g for g in gerekli if g not in duz[ad]]
        if eksik:
            hata.append("KATLAMA KABLOSU KOPMUS: %s() govdesinde %s cagrisi YOK -> YAML "
                        "katlanan blok skalari (`run: >-`) yeniden HAM satir olarak gorulur "
                        "ve mesru adimlar SAHTE-KIRMIZI yanar (Y05). GERI KOY."
                        % (ad, ", ".join(eksik)))
    for ad, gerekli in ALT_KUME_KABLOLARI:
        if ad not in duz:
            hata.append("ALT KUME KABLOSU BAYAT: %s() fonksiyonu bulunamadi -> dosya "
                        "yeniden duzenlendiyse ALT_KUME_KABLOLARI'ni guncelle" % ad)
            continue
        eksik = [g for g in gerekli if g not in duz[ad]]
        if eksik:
            hata.append("ALT KUME KABLOSU KOPMUS: %s() govdesinde %s cagrisi YOK -> "
                        "coklu-workflow kapsami / opt-in alt kume kurali / uyari katmani "
                        "sessizce DEVRE DISI kalir. Somut riskler: cron'da kosan cagri "
                        "yine 'kosmuyor' gorunur (BOLUM A kok kusuru) · beyan edilen alt "
                        "kume hic olculmez (BOLUM B) · A-sinifi adaylar bir daha yuzeye "
                        "cikmaz (BOLUM C). GERI KOY." % (ad, ", ".join(eksik)))
    for ad, gerekli in NOBETCI_KABLOLARI:
        if ad not in duz:
            hata.append("NOBETCI KABLOSU BAYAT: %s() fonksiyonu bulunamadi -> dosya "
                        "yeniden duzenlendiyse NOBETCI_KABLOLARI'ni guncelle" % ad)
            continue
        eksik = [g for g in gerekli if g not in duz[ad]]
        if eksik:
            hata.append("NOBETCI KABLOSU KOPMUS: %s() govdesinde %s cagrisi YOK -> o "
                        "nobetci(ler) artik kosmuyor ve korudugu mutasyon sinifi yeniden "
                        "SESSIZ olur. GERI KOY." % (ad, ", ".join(eksik)))
    # KB-E: cagri satiri durup HUKUMDEKI PAYI dusurulebiliyordu (`and` -> `or`).
    hata.extend(_kendini_test_hukum_kontrol(agac))
    # S1: bu nobetcinin KENDI uretim yolu (kaynak is None) CALISAN dosyayi okumali.
    hata.extend(_seam_kontrol(agac))
    # TOPLAM YUZEY + DEFTER/CAGRI ESITLIGI (twin-free capa).
    hata.extend(_kol_kapsam_kontrol(agac, duz, kaynak))
    # Bu iki kolun KENDI nobeti: bilinen-bozuk girdide atesliyorlar mi.
    hata.extend(_kablo_ic_fikstur())
    return (not hata), hata


# ---- SAF DENETIM GOVDESI ---------------------------------------------------
# main() eskiden hem karar veriyor hem BASIYORDU -> govdeyi disaridan (nobetciden)
# olcmek imkansizdi ve "CI'da kosan kod" ile "test edilen kod" ayrisiyordu.
# denetle() saftir: girdisini parametreden alir, hicbir sey basmaz, (kod, satirlar) dondurur.
# Boylece muaf_sayaci_kontrol() TA KENDISINI olcer (kopya mantik yazmaz).
def denetle(deploy_metin, kesif, izin_listesi, kontroller=True, akislar=None,
            dosya_metinleri=None, alt_kume_izin=None, ayristirici_yok=None,
            izlenmeyen=None, izlenmeyen_sebep=None, model_uretim=False,
            push_kapsami=None, push_kapsami_sebep=None):
    """(exit_kodu, rapor_satirlari) dondurur. Hicbir sey BASMAZ.

    kontroller=True iken kendi mutasyon nobetcilerini (bulgu1 + muaf sayaci) BLOKLAYICI
    olarak kosar. muaf_sayaci_kontrol() bu fonksiyonu tekrar cagirdigi icin oradan
    DAIMA kontroller=False ile girilir (OZYINELEME KORUMASI).

    🔴 <akislar> OPSIYONELDIR VE VARSAYILANI None'DIR (BOLUM A5): None iken kapsam
    YALNIZ verilen <deploy_metin>'den sayilir ve ALT KUME (BOLUM B) + UYARI KATMANI
    (BOLUM C) HIC CALISMAZ -> bugunku davranis BIREBIR korunur, ozyinelemeli
    nobetciler (muaf_sayaci_kontrol) degismeden gecer. main() GERCEK envanteri
    ([(yol, metin, sinif), ...]) gecirir ve kapsam OTOMATIK tetikli is akislarindan
    sayilir; ELLE/BELIRSIZ tetikli is akisinda kosmak KAPSAM SAYILMAZ.

    🔴 <izlenmeyen> DE OPSIYONELDIR VE VARSAYILANI None'DIR (AYNI GEREKCE): None iken
    HENUZ IZLENMIYOR kovasi HIC olculmez ve rapora HIC satir eklenmez -> ozyinelemeli
    nobetciler ve mevcut mutasyon bataryalari BIREBIR eskisi gibi kosar. main()
    GERCEK olcumu (kesfet_izlenmeyen()) gecirir. <izlenmeyen_sebep> doluysa kova
    OKUNAMADI demektir ve hukum FAIL-CLOSED'dir (rc=1) — "bos kova" DEGIL.

    <push_kapsami> yalnız pre-push kancasinin stdin ref/SHA araligindan turetilmis
    repo-goreli yol kumesidir. None ise kapsam bilinmiyor demektir ve izlenmeyen
    kapsamsiz adaylar ESKI kati hukumle KIRMIZI kalir. Bilinen kapsamda bulunmayan
    izlenmeyen adaylar gorunur UYARI olur, cikis koduna dokunmaz."""
    satirlar = []
    if akislar is None:
        kos = kosulan(deploy_metin, kesif)
        kos_elle = {}
    else:
        kos_otomatik, kos_elle = kosulan_coklu(akislar, kesif)
        kos = set(kos_otomatik)
    kesif_kume = set(kesif)

    # T8: bloklamayan gelecek-robustluk uyarisi (hatalar listesine GIRMEZ, exit degismez).
    for satir in sayilamayan_python3(deploy_metin):
        satirlar.append("UYARI: python3 iceren ama sayilamayan icra satiri "
                        "(bare 'python3 tools/x.py' formu kullan): %s" % satir)

    # BELIRSIZ tetikli is akislari: UYARI (exit kodunu ETKILEMEZ), cunku ters yon
    # (BELIRSIZ -> OTOMATIK) kapiyi SESSIZCE GEVSETIRDI; bu yon ise yalniz daraltir.
    if akislar is not None:
        for akis_yol, _metin, sinif in akislar:
            if sinif == SINIF_BELIRSIZ:
                satirlar.append("UYARI: is akisinin TETIGI COZULEMEDI (%s) -> kapsam "
                                "acisindan ELLE gibi ele alindi (fail-closed yon)."
                                % akis_yol)

    hatalar = []

    # Iki model araci artik iki seride kosar: pahali KENDINI-TEST nobet.yml'de,
    # canli katalogu olcen BAYRAKSIZ kollar deploy.yml'de. Dosya-granullu kapsam
    # ikinci kolu ilkinden ayiramaz; bu pozitif kablo iddiasi sessiz daralmayi kapatir.
    if model_uretim:
        for h in model_uretim_kollari_dogrula(deploy_metin):
            hatalar.append("MODEL-URETIM-KOLU: " + h)

    # 🔴 O5 — "HICBIR GERCEK AYRISTIRICI YOK" AYRI VE ACIK BIR HALDIR.
    # Olculen sahte-KIRMIZI: ayristirici yokken 4 is akisinin 4'u de BELIRSIZ olur,
    # hicbiri OTOMATIK sayilmaz ve kapi 124 ADET "KAPSAMSIZ" satiri basardi. O 124
    # satir DOGRU DEGIL — testler kosuluyor, kapi OLCEMIYOR. `run:` cozumunun taklit
    # yedegi var, tetik siniflandirmasinin YOK; bu asimetri raporda ACIKCA soylenir.
    # SEMANTIK GEVSETILMEZ: rc=1 KALIR (fail-closed), yalniz SEBEP dogru yazilir.
    if ayristirici_yok is None:
        ayristirici_yok = YAML_OKU.ayristirici_adi() is None
    ayristirici_yok = bool(ayristirici_yok) and akislar is not None
    if ayristirici_yok:
        hatalar.append(
            "OLCULEMEDI — HICBIR GERCEK YAML AYRISTIRICISI YOK (PyYAML de ruby/psych de "
            "yok): is akislarinin TETIK SINIFI cozulemedigi icin %d is akisinin hepsi "
            "BELIRSIZ sayildi ve KAPSAM HIC OLCULEMEDI. Bu 'testler kosmuyor' DEMEK "
            "DEGILDIR; kapi OLCEMIYOR demektir (fail-closed: rc=1). COZUM: `pip install "
            "pyyaml` ya da ortama ruby kur. NOT: `run:` cozumunun taklit yedegi VAR, "
            "tetik siniflandirmasinin YOKTUR — kapsam hukmu tetige dayandigi icin "
            "tahmin URETILMEZ." % len(akislar))

    # B) OPT-IN ALT KUME BEYANI — BLOKLAYICI CEKIRDEK (yalniz akislar verilince)
    beyan_sayisi = kapsanan_alt_kume = muaf_alt_kume = 0
    alt_kume_fail_open = []
    okunamayan_dosya = []
    beyan_benzeri = []
    if akislar is not None:
        if dosya_metinleri is None:
            dosya_metinleri, okunamayan_dosya = dosya_metinleri_oku(kesif)
        if alt_kume_izin is None:
            alt_kume_izin = ALT_KUME_IZIN_LISTESI
        bayrak_env = bayrak_envanteri(akislar, kesif)
        (alt_hata, beyan_sayisi, kapsanan_alt_kume, muaf_alt_kume,
         alt_kume_fail_open) = alt_kume_denetimi(
            kesif, dosya_metinleri, bayrak_env, alt_kume_izin,
            olculemedi_hepsi=ayristirici_yok)
        hatalar.extend(alt_hata)
        # O9: beyan OLMAK ISTEYEN ama ayristirilamayan satirlar (BLOKLAMAZ).
        for yol in sorted(dosya_metinleri):
            for satir_no, satir in beyan_benzeri_ayristirilamayan(dosya_metinleri[yol]):
                beyan_benzeri.append((yol, satir_no, satir))

    # 2) gerekcesiz izin girisi
    for yol, gerekce in izin_listesi.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ izin girisi (bos gerekce): %s" % yol)

    # 3) bayat izin: kesfedilmeyen (silinmis/yeniden adlandirilmis) yol
    for yol in izin_listesi:
        if yol not in kesif_kume:
            hatalar.append("BAYAT izin (artik kesfedilmiyor — sil ya da yolu duzelt): %s" % yol)

    # 4) bayat izin: hem izinde hem kosuluyor
    for yol in izin_listesi:
        if yol in kos:
            hatalar.append("BAYAT izin (test ARTIK KOSULUYOR — izinden cikar): %s" % yol)

    # 1) kapsamsiz: kesfedilmis ama ne kosuluyor ne izinli
    # O5: ayristirici HIC yoksa bu liste 'kapsamsiz test' DEGIL, 'olculemeyen kapi'dir
    # -> tek satirlik dogru tani yukarida basildi, 124 yaniltici satir BASILMAZ.
    kapsamsiz = []
    if not ayristirici_yok:
        for yol in kesif:
            if yol in kos:
                continue
            if yol in izin_listesi:
                continue
            kapsamsiz.append(yol)
    for yol in kapsamsiz:
        hatalar.append("KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % yol)

    # 1b) 🔴 HENUZ IZLENMIYOR KOVASI (9 Agu 2026) — AYRI ETIKET, AYNI HUKUM.
    # NEDEN CIKIS KODUNA DOKUNUYOR: exit'i degistirmeyen "uyari-yalniz" kova
    # [[beyan-edilmis-survivor]] sinifidir — ayirt edici olmayan bir iddiadir ve bu
    # turda tam olarak SESSIZ YESIL yanlis teslim uretti. Kova AYRI etiketle basilir
    # ki tani dogru olsun (`git add` unutulmus mu, yoksa gercekten kapsam mi yok).
    # MARUZIYET OLCUMU (9 Agu 2026): dal worktree'si 0 · ana checkout 0 · TEMIZ KLON 0
    # -> bugun hicbir mesru WIP dosyasi bu kovaya DUSMUYOR, fail-closed bedelsiz.
    izlenmeyen_kapsamsiz = []
    izlenmeyen_kapsanan = []
    izlenmeyen_push_disi = []
    if izlenmeyen_sebep:
        hatalar.append(
            "OLCULEMEDI — HENUZ IZLENMIYOR kovasi OKUNAMADI: %s. Bu 'izlenmeyen "
            "kapsamsiz dosya YOK' DEMEK DEGILDIR; kapi o ekseni OLCEMEDI "
            "(fail-closed: rc=1)." % izlenmeyen_sebep)
    if izlenmeyen:
        # KAPSAM SORUSU AYRI KUMEDE SORULUR: `kos` yalnizca <kesif> uzerinden
        # hesaplanir, bu yuzden izlenmeyen yollar oraya HIC giremez. Rapordaki
        # "kosulan : N" sayisi BOZULMASIN diye ayri bir kume hesaplanir.
        if akislar is None:
            iz_kos = kosulan(deploy_metin, izlenmeyen)
        else:
            iz_kos_otomatik, _iz_kos_elle = kosulan_coklu(akislar, izlenmeyen)
            iz_kos = set(iz_kos_otomatik)
        for yol in izlenmeyen:
            if yol in iz_kos or yol in izin_listesi:
                izlenmeyen_kapsanan.append(yol)
            else:
                izlenmeyen_kapsamsiz.append(yol)
    for yol in izlenmeyen_kapsamsiz:
        if push_kapsami is not None and yol not in push_kapsami:
            izlenmeyen_push_disi.append(yol)
            satirlar.append(
                "UYARI: HENUZ IZLENMIYOR ve PUSH KAPSAMI DISI: %s — calisma "
                "agacinda gorunur ama bu itmenin ref/SHA araliginda yok; push'u "
                "BLOKLAMIYOR." % yol)
            continue
        kapsam_tani = (
            "push kapsaminda" if push_kapsami is not None
            else "push kapsami BILINMIYOR (fail-closed: %s)"
                 % (push_kapsami_sebep or "pre-push ref/SHA bilgisi verilmedi"))
        hatalar.append(
            "HENUZ IZLENMIYOR (kapsamsiz): %s — calisma agacinda duruyor ama `git "
            "add` EDILMEMIS ve hicbir OTOMATIK is akisinda kosmuyor / izin "
            "listesinde degil; %s. `git add` etmek bu satiri KAPSAMSIZ'a cevirir, "
            "kapatmaz: once cagri satirini ekle ya da GEREKCELI muafiyet yaz."
            % (yol, kapsam_tani))

    # 5) kendi mutasyon nobetcileri — yalniz GERCEK deploy.yml'e karsi (mutant --deploy
    #    verildiginde pozitif kontrol anlamsiz olur, o yuzden atlanir) ve nobetcinin
    #    kendi ic cagrilarinda (ozyineleme) atlanir.
    if kontroller:
        _, mutasyon_hata = bulgu1_mutasyon_kontrol()
        for h in mutasyon_hata:
            hatalar.append("BULGU1-MUTASYON: " + h)
        _, muaf_hata = muaf_sayaci_kontrol()
        for h in muaf_hata:
            hatalar.append("MUAF-SAYACI: " + h)
        # ACIK KESIF KAYDI hijyeni: bayat/gerekcesiz/gereksiz giris SESSIZ kapsam
        # kaybidir (kayit dusense o dosya icin kapsam sorusu hic sorulmaz olur).
        _, acik_hata = acik_kesif_kontrol()
        for h in acik_hata:
            hatalar.append("ACIK-KESIF: " + h)
        # KESIF PREDIKATI (8 Agu): pozitif VE negatif yon birlikte. Predikati
        # gevsetmek (her seyi yakalamak) ya da daraltmak (mutasyon surucusunu
        # dusurmek) TEK BASINA KIRMIZI yakar.
        _, predikat_hata = kesif_predikat_kontrol()
        for h in predikat_hata:
            hatalar.append("KESIF-PREDIKATI: " + h)
        # IZLENMEYEN KOVA (9 Agu): SENTETIK git deposunda ADIM ADIM senaryo. Bayraksiz
        # kolda da kosar cunku bu kolun asil tuketicisi YEREL push-oncesi kosumdur —
        # korlugun olculdugu yer tam orasiydi.
        _, izlenmeyen_hata = izlenmeyen_fikstur_kontrol()
        for h in izlenmeyen_hata:
            hatalar.append("IZLENMEYEN-FIKSTUR: " + h)
        # KABLO (9 Agu): `main()` olcumu `denetle()`'ye FIILEN geciriyor mu.
        # Ozellik + fikstur duruyorken kablosu sokulebiliyordu (Y4/Y8).
        _, kablo_hata = main_kablosu_kontrol()
        for h in kablo_hata:
            hatalar.append("MAIN-KABLO: " + h)
        # PUSH KABLOSU — UCUZ KOL. AGIR davranis ayagi (45 gercek `git push`,
        # 2,40 sn) MALIYET HUKMU geregi `--kendini-test` koluna tasindi; burada
        # statik capa kalir. Iki kolun TOPLAM nobetci kumesi KUCULMEDI —
        # `_kol_kapsam_kontrol()` bunu AST ekseninde olcer
        # ([[kapi-yan-etkisi-gizli-onkosul]]).
        _, pp_hata = pre_push_capa_kontrol()
        for h in pp_hata:
            hatalar.append("PRE-PUSH-CAPA: " + h)
        # 🔴 SERIT NOBETCISI BU KOLDA DEGIL — MALIYET OLCUMU: `kanca_kablo_serit_
        # kontrol()` deploy.yml'i GERCEK ayristiriciyla cozer; pyyaml yoksa psych
        # (ruby SURECI) kosar ve bu kolun medyani 3,89 -> 9,89 sn'ye cikti (olculdu).
        # Nobetci `--kanca-kablo` (deploy.yml BLOKLAYICI serit-a3) ve `--kendini-test`
        # kollarinda kosar; iddia CI'da bloklayicidir, pre-push'a bindirilmez.
        # AMA UCUNCU KOLUN CAGRI SATIRI BURADA CIVILENIR (5. tur F2): adim silinir
        # ya da `echo`'ya sarilirsa o kol CI'da HIC KOSMAZ; ucuz `_hedef_cagrilari`
        # (kardeslerle AYNI onbellekli tek kaynak) bunu push aninda yakalar.
        _, kk_adim_hata = kanca_kablo_adimi_kontrol()
        for h in kk_adim_hata:
            hatalar.append("KANCA-KABLO-ADIMI: " + h)
        # HUKUM KURALI FUZZ'I (6. tur): kural BLOKLAYICI kolda herkesin itmesini
        # yargiliyor -> iki yonu de (sizinti + sahte-kirmizi) BURADA kilitlenir.
        _, fuzz_hata = hukum_fuzz_kontrol()
        for h in fuzz_hata:
            hatalar.append("HUKUM-FUZZ: " + h)
        # 🔴 HUKUM EZME SINIFININ ASIL HAKIMI (8. tur): sozdizimsel kural degil,
        # DAVRANIS. Ucuz (0,14 sn — nobetciler stub'lanir, GERCEK is kosmaz), o
        # yuzden BLOKLAYICI pre-push kolunda da yasar. 18 varyantlik SABOTAJ
        # tablosu (2,3 sn) yalniz `--kanca-kablo` (CI) kolundadir.
        _, dav_hata = hukum_davranis_kontrol()
        for h in dav_hata:
            hatalar.append("HUKUM-DAVRANISI: " + h)
        # ZINCIRIN SON HALKASI: oz-nobetci ADIMI deploy.yml'de duruyor mu. BURADA
        # (bayraksiz/bloklayici kolda) yasamak ZORUNDA — --kendini-test kolunda olsa,
        # adim silindiginde o kol kosmayacagi icin nobetci OLU olurdu.
        _, adim_hata = kendini_test_adimi_kontrol()
        for h in adim_hata:
            hatalar.append("KENDINI-TEST-ADIMI: " + h)
        # ORTAK SUZGEC (30 Tem): govdesi + kablosu. Bayraksiz kolda da kosar cunku
        # yerel push-oncesi kosum bu koldur; CI'daki asil kanit --kendini-test'te.
        _, fikstur_hata = suzgec_fikstur_kontrol()
        for h in fikstur_hata:
            hatalar.append("SUZGEC-FIKSTUR: " + h)
        _, kablo_hata = suzgec_kablosu_kontrol()
        for h in kablo_hata:
            hatalar.append("SUZGEC-KABLO: " + h)
        # BAYRAKSIZ ADIM: burada da olculur ama GERCEK kanit --kendini-test kolundadir
        # (D1/D4 mutantlarinda bu kol ya kosmaz ya olcum govdesine hic girmez).
        _, bayraksiz_hata = bayraksiz_adim_kontrol()
        for h in bayraksiz_hata:
            hatalar.append("BAYRAKSIZ-ADIM: " + h)
        # ALT KUME (BOLUM A+B) govdesi: tetik siniflandirmasi + beyan ayristirmasi +
        # uctan uca kabul/ret semantigi (SENTETIK fiksturler; GERCEK deploy.yml'e
        # mutasyon UYGULANMAZ).
        _, alt_kume_hata = alt_kume_fikstur_kontrol()
        for h in alt_kume_hata:
            hatalar.append("ALT-KUME-FIKSTUR: " + h)

    # ---- rapor ----
    # FIX (27 Tem, olculdu): eski hal `[y for y in kesif if y not in kos]` idi -> etiket
    # "Muaf (izin listesi)" derken KAPSAMSIZ dosyalari da sayiyordu. Somut olcum:
    # tools/mimar-kapi-6ev-test.py kapsamsizken satir "Muaf: 71" yazdi; gercek muafiyet
    # eklenince (IZIN_LISTESI 70 -> 71) satir YINE "71" yazdi -> sayi muafiyet eklemesine
    # KOR, kapsamsiz dosya sessizce "muaf" etiketleniyordu. merge prosedürü bu sayiyi
    # ONCE/SONRA olcumu olarak rapor ettirdigi icin yanlis etiket olcumu bozuyordu.
    # (Kabul/ret semantigi DEGISMEDI: kapsamsiz tespiti yukarida, ayri ve aynen duruyor.)
    muaf = [y for y in kesif if y not in kos and y in izin_listesi]
    satirlar.append("CI KAPSAM KAPISI")
    satirlar.append("  Kesfedilen kabul testi : %d" % len(kesif))
    if akislar is None:
        satirlar.append("  deploy.yml'de kosulan  : %d  (%s)" % (
            len(kos), ", ".join(sorted(kos)) or "-"))
    else:
        sayim = {}
        for _y, _m, sinif in akislar:
            sayim[sinif] = sayim.get(sinif, 0) + 1
        satirlar.append("  Is akisi (izlenen)     : %d  (OTOMATIK %d · ELLE %d · "
                        "BELIRSIZ %d)" % (len(akislar), sayim.get(SINIF_OTOMATIK, 0),
                                          sayim.get(SINIF_ELLE, 0),
                                          sayim.get(SINIF_BELIRSIZ, 0)))
        satirlar.append("  OTOMATIK'te kosulan    : %d  (%s)" % (
            len(kos), ", ".join(sorted(kos)) or "-"))
        yalniz_elle = sorted(y for y in kos_elle if y not in kos)
        satirlar.append("  YALNIZ ELLE'de kosulan : %d  (kapsam SAYILMAZ: %s)" % (
            len(yalniz_elle), ", ".join(yalniz_elle) or "-"))
    satirlar.append("  Muaf (izin listesi)    : %d" % len(muaf))
    if kontroller:
        # 🔴 KOL KOL SAYI ([[kapi-yan-etkisi-gizli-onkosul]]): agir davranis ayagi
        # `--kendini-test` koluna tasindi; hangi kolun KAC nobetci kostugu GORUNUR
        # olmali, yoksa tasima yuzeyi sessizce kucultur.
        _kol = dict(NOBETCI_KABLOLARI)
        _birlesim = set()
        for _a, _g in NOBETCI_KABLOLARI:
            _birlesim |= set(_g)
        satirlar.append(
            "  Oz-nobetci (UC SERIT)  : BAYRAKSIZ(bu kol, BLOKLAYICI: push+yayin) %d "
            "· `%s`(BLOKLAYICI: deploy serit-a3) %d · `%s`(nobet.yml, BLOKLAMAZ) %d "
            "· BIRLESIM %d (taban %d)"
            % (len(_kol.get("denetle", ())), KANCA_KABLO_BAYRAGI,
               len(KANCA_KABLO_KOL_NOBETCILERI), KENDINI_TEST_BAYRAGI,
               len(_kol.get("main", ())), len(_birlesim), KOL_BIRLESIM_TABANI))
    # 🔴 KOVA GORUNUR OLMAK ZORUNDA: olculdu ama basilmadi = olculmedi. "0" satiri da
    # BASILIR — yoksa "satir yok" ile "kova bos" ayirt edilemez ([[hukum-yanlis-birimde]]).
    if izlenmeyen_sebep:
        satirlar.append("  Henuz izlenmiyor (aday): OLCULEMEDI (fail-closed) · %s"
                        % izlenmeyen_sebep)
    elif izlenmeyen is not None:
        bloklayan_izlenmeyen = len(izlenmeyen_kapsamsiz) - len(izlenmeyen_push_disi)
        satirlar.append(
            "  Henuz izlenmiyor (aday): %d  (bloklayan %d · push-disi uyari %d · "
            "kosuyor/muaf %d)"
            % (len(izlenmeyen), bloklayan_izlenmeyen,
               len(izlenmeyen_push_disi), len(izlenmeyen_kapsanan)))
        for yol in izlenmeyen_kapsanan:
            satirlar.append("      ℹ️ HENUZ IZLENMIYOR ama KAPSANMIS (cagri satiri/"
                            "muafiyet zaten var): %s" % yol)
    if akislar is not None:
        satirlar.append("  Beyan edilen alt kume  : %d  (kapsanan %d · muaf %d)"
                        % (beyan_sayisi, kapsanan_alt_kume, muaf_alt_kume))
        satirlar.append("  Muaf alt kume (izin)   : %d" % len(alt_kume_izin))
        # O3b: iki-kol paritesi HER kosumda GORUNUR (olculemediyse de soylenir).
        satirlar.append(iki_kol_durum_satiri())
        # 🔴 O2 — FAIL-OPEN GORUNUR OLMAK ZORUNDA. Bu satirlar exit kodunu ETKILEMEZ
        # ama "kapsanan" sayisinin bir kismi OLCUMDEN DEGIL, OLCEMEMEKTEN geliyorsa
        # rapor bunu SOYLEMELIDIR (yoksa aktif yanlis beyan olur — olculdu).
        for yol, bayrak, sebep, kapsandi in alt_kume_fail_open:
            satirlar.append(
                "  🟡 ALT KUME OLCULEMEDI -> %s: %s %s · %s"
                % ("kapsanmis SAYILDI (fail-open)" if kapsandi
                   else "kapsam HUKMU VERILMEDI (ne kosuyor ne kosmuyor denebilir)",
                   yol, bayrak, sebep))
        # O8: okunamayan kesif dosyalari SAYIYLA (sessiz atlama degil).
        if okunamayan_dosya:
            satirlar.append("  🟡 OKUNAMAYAN kesif dosyasi: %d (beyan/capa sorulari bu "
                            "dosyalar icin SORULMADI)" % len(okunamayan_dosya))
            for yol, sebep in okunamayan_dosya[:5]:
                satirlar.append("      %s · %s" % (yol, sebep[:120]))
            if len(okunamayan_dosya) > 5:
                satirlar.append("      ... %d kalem BASILMADI"
                                % (len(okunamayan_dosya) - 5))
        # O9: beyan olmak isteyip ayristirilamayan satirlar (tani, BLOKLAMAZ).
        if beyan_benzeri:
            satirlar.append("  🟡 BEYAN BENZERI satir ayristirilamadi: %d (tipo = beyanin "
                            "TUMUYLE dusmesi demektir)" % len(beyan_benzeri))
            for yol, satir_no, satir in beyan_benzeri[:10]:
                satirlar.append("      %s:%d  %s" % (yol, satir_no, satir))
            if len(beyan_benzeri) > 10:
                satirlar.append("      ... %d kalem BASILMADI" % (len(beyan_benzeri) - 10))
        # 🔴 BOLUM C — UYARI KATMANI: EXIT KODUNA ASLA DOKUNMAZ. Istisna sizarsa
        # tek satir tani basilir ve hukum DEGISMEZ.
        try:
            satirlar.extend(uyari_katmani(kesif, dosya_metinleri, bayrak_env,
                                          alt_kume_izin))
        except Exception as e:  # noqa: BLE001 — bilincli: uyari katmani BLOKLAMAZ
            satirlar.append("UYARI KATMANI OLCULEMEDI: %s: %s"
                            % (type(e).__name__, e))
    # 🔴 F1/F5 — RAPOR METNI ile HUKUM arasindaki celiski BLOKLAYICIDIR. En sonda,
    # tum satirlar ve tum hatalar olustuktan SONRA sorulur.
    if akislar is not None:
        hatalar.extend(tutarlilik_kontrolu(satirlar, hatalar, kontroller))
    satirlar.append("-" * 70)
    if hatalar:
        for h in hatalar:
            satirlar.append("  ❌ " + h)
        satirlar.append("-" * 70)
        satirlar.append("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1, satirlar
    satirlar.append("SONUC: YESIL ✅  — her kabul testi ya kosuluyor ya gerekceli muaf.")
    return 0, satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", default=DEPLOY_VARSAYILAN,
                    help="deploy.yml yolu (kirmizi-mutasyon icin alternatif kopya verilebilir)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YALNIZ kendi mutasyon nobetcilerini kosar: bulgu1 + muaf sayaci "
                         "(gercek deploy.yml uzerinden)")
    ap.add_argument(KANCA_KABLO_BAYRAGI, action="store_true",
                    help="YALNIZ pre-push kanca kablosunun DAVRANIS ayagini kosar "
                         "(45 GERCEK `git push`). BLOKLAYICI seride (deploy.yml) "
                         "AYRI adim olarak baglanir.")
    ap.add_argument("--pre-push", action="store_true",
                    help="stdin'deki git pre-push ref/SHA satirlarindan bu itmenin "
                         "kapsamini turetir; yalniz kanca kullanir")
    args = ap.parse_args()

    # 🔴 HANGI KOL KARAR VERIYOR (mimar hukmu madde 3) — HER kosumda basilir.
    print("  YAML ayristirici kolu  : %s" % (
        YAML_OKU.ayristirici_adi() or "YOK -> taklit-fallback (fail-closed)"))

    # 🔴 AGIR DAVRANIS AYAGI — AYRI BAYRAK, BLOKLAYICI SERIT (9 Agu 2026, 4. tur).
    # OLCULEN HATA: ayak `--kendini-test` koluna alinmisti; o adim `nobet.yml`de
    # (SERIT B — yayini BLOKLAMAZ) yasiyor -> N1/N3/X4 sinifi sabotaj push'u DA
    # deploy'u DA geciyordu; sinif KAPI olmaktan cikip ALARMA dusmustu.
    # `--kendini-test`i deploy.yml'e geri koymak 5 Agu'daki serit kararini bozardi
    # ([[hukum-yanlis-birimde]]: bloklamayan alarm joblari yayin kosumunun rengini
    # boyamasin) -> AYRI BAYRAK acildi ve YALNIZ O ADIM bloklayici job'a baglandi.
    if getattr(args, KANCA_KABLO_BAYRAGI.lstrip("-").replace("-", "_")):
        ok_d, hata_d = hukum_davranis_fikstur_kontrol()
        print("HUKUM EZME SINIFI — DAVRANIS FIKSTURU (%d varyant: %d sabotaj KIRMIZI "
              "yakmali + %d mesru yazim YESIL kalmali; her biri STUB'lanmis nobetciyle "
              "UCTAN UCA kosulur)"
              % (len(HUKUM_DAVRANIS_FIKSTURLERI),
                 sum(1 for _e, _c, _i, y, _n in HUKUM_DAVRANIS_FIKSTURLERI if not y),
                 sum(1 for _e, _c, _i, y, _n in HUKUM_DAVRANIS_FIKSTURLERI if y)))
        if ok_d:
            print("  ✅ `if ok or True:` · `if not False:` · `if 1==1:` · `if bool(1):` "
                  "· `if len([])==0:` · kosulun SILINMESI · `while True:` · "
                  "`_ = nobetci()` · yanlis tuple indisi · `all([])` · "
                  "`any([...,True])` TEK BASINA kirmizi; mesru yazimlar YESIL")
        else:
            for h in hata_d:
                print("  ❌ " + h)
        ok_s, hata_s = kanca_kablo_serit_kontrol()
        print("KANCA KABLOSU SERIDI — AGIR AYAK BLOKLAYICI JOB'DA MI (davranissal)")
        if ok_s:
            print("  ✅ `%s` adimi `deploy: needs` zincirindeki bir job'da kosuyor"
                  % KANCA_KABLO_BAYRAGI)
        else:
            for h in hata_s:
                print("  ❌ " + h)
        ok, hatalar = pre_push_kablo_kontrol()
        print("pre-push KABLOSU — GERCEK `git push` ILE DAVRANIS, GIT KANCA ORTAMINDA "
              "(%d govde x %d vaka = %d kosum; %d oldurucu + %d kontrol)"
              % (len(PRE_PUSH_MUTANTLARI), len(PRE_PUSH_DAVRANIS_VAKALARI),
                 len(PRE_PUSH_MUTANTLARI) * len(PRE_PUSH_DAVRANIS_VAKALARI),
                 sum(1 for _e, _d, b, _n in PRE_PUSH_MUTANTLARI if not b),
                 sum(1 for _e, _d, b, _n in PRE_PUSH_MUTANTLARI if b)))
        if ok:
            print("  ✅ HUKMU KABUK VERIYOR: kapi KIRMIZI iken push DURUYOR, YESIL "
                  "iken GECIYOR, arac YOKKEN DURUYOR; N1/N3/X4/N2/P4/P6 TEK BASINA "
                  "kirmizi; `${...}` ve ilgisiz degisiklik YANLIS-KIRMIZI yakmiyor")
        else:
            for h in hatalar:
                print("  ❌ " + h)
        if ok and ok_s and ok_d:
            print("SONUC: YESIL ✅")
            return 0
        print("SONUC: KIRMIZI ❌")
        return 1

    if args.kendini_test:
        ok1, hata1 = bulgu1_mutasyon_kontrol()
        print("BULGU 1 MUTASYON NOBETCISI")
        if ok1:
            print("  ✅ gercek deploy sayiyor; yalniz-yorum mutanti saymiyor")
        else:
            for h in hata1:
                print("  ❌ " + h)
        ok2, hata2 = muaf_sayaci_kontrol()
        print("MUAF SAYACI NOBETCISI")
        if ok2:
            print("  ✅ kapsamsiz dosya 'Muaf' sayilmiyor; muafiyet eklenince sayi 1 artiyor")
        else:
            for h in hata2:
                print("  ❌ " + h)
        # 3. nobetci BU KOLDA yalnizca RAPORLANIR — gercek kapisi bayraksiz kosumdadir
        # (bu adim silinirse bu kol CI'da hic kosmaz; bkz. kendini_test_adimi_kontrol).
        ok3, hata3 = kendini_test_adimi_kontrol()
        print("OZ-NOBETCI ADIMI NOBETCISI")
        if ok3:
            print("  ✅ deploy.yml bu betigi `%s` ile ANLAMLI olarak kosan bir adim "
                  "tasiyor (bicim serbest; `echo`/`--help` mensiyonu SAYILMAZ; "
                  "'kosuyor+blokluyor' IDDIA EDILMEZ — o eksen is-akisi-kapisi BOLUM D)"
                  % KENDINI_TEST_BAYRAGI)
        else:
            for h in hata3:
                print("  ❌ " + h)
        # 🔴 BAYRAKSIZ ADIM NOBETCISI — GERCEK KAPISI BU KOLDADIR (D1 + D4).
        # D1 (`--help`) ve D4 (adim silindi) mutantlarinda bayraksiz kol ya hic
        # kosmaz ya olcum govdesine hic girmez -> kanit YALNIZ burada uretilebilir.
        ok4, hata4 = bayraksiz_adim_kontrol()
        print("BAYRAKSIZ (KAPSAM KOLU) ADIMI NOBETCISI")
        if ok4:
            print("  ✅ deploy.yml bu betigi `%s` OLMADAN anlamli olarak kosan bir "
                  "adim tasiyor (kapsam kolu CI'da GERCEKTEN olculuyor)"
                  % KENDINI_TEST_BAYRAGI)
        else:
            for h in hata4:
                print("  ❌ " + h)
        ok5, hata5 = suzgec_fikstur_kontrol()
        print("ORTAK ICRA SUZGECI + `run:` COZUMU — GOVDE (ariza enjeksiyonu, %d sentetik "
              "fikstur)" % (len(SUZGEC_FIKSTURLERI) + 3 + len(KATLAMA_FIKSTURLERI)
                            + len(BICIM_FIKSTURLERI) + len(ICRA_GOVDESI_FIKSTURLERI)
                            + len(ICRA_INDEKS_FIKSTURLERI)))
        if ok5:
            print("  ✅ ANLAMLI bicimler EVET, ANLAMSIZ bicimler (`--help`/`echo`) HAYIR; "
                  "KATLANAN `>`/`>-`/`>+` blok birlesiyor, LITERAL `|` blok DEGISMIYOR; "
                  "TAKLIT kolu ile GERCEK AYRISTIRICI kolu AYNI hukmu veriyor; mutant "
                  "capasi (provenans) yerinde; BICIM TESHISI adim/bicim/gorulen komutu "
                  "SOYLUYOR")
        else:
            for h in hata5:
                print("  ❌ " + h)
        ok6, hata6 = suzgec_kablosu_kontrol()
        print("ORTAK ICRA SUZGECI + AYRISTIRICI + KATLAMA + BICIM TESHISI — KABLO (AST)")
        if ok6:
            print("  ✅ %s govdelerinde SUZGEC cagrisi duruyor; %s govdelerinde GERCEK "
                  "AYRISTIRICI (YAML_OKU) cagrisi duruyor; %s govdelerinde `run:` cozum "
                  "cagrisi duruyor; %s govdelerinde bicim teshisi cagrisi duruyor"
                  % (", ".join("%s()" % a for a, _ in SUZGEC_KABLOLARI),
                     ", ".join(sorted({"%s()" % a for a, _ in AYRISTIRICI_KABLOLARI})),
                     ", ".join(sorted({"%s()" % a for a, _ in KATLAMA_KABLOLARI})),
                     ", ".join("%s()" % a for a, _ in TANI_KABLOLARI)))
        else:
            for h in hata6:
                print("  ❌ " + h)
        ok7, hata7 = alt_kume_fikstur_kontrol()
        print("COKLU IS AKISI (tetik sinifi) + OPT-IN ALT KUME + UYARI KATMANI — "
              "GOVDE (%d sentetik fikstur)"
              % (len(TETIK_FIKSTURLERI) + len(BEYAN_FIKSTURLERI)
                 + len(ALT_KUME_FIKSTURLERI) + 2))
        if ok7:
            print("  ✅ cron/push OTOMATIK · yalniz workflow_dispatch ELLE · cozulemeyen "
                  "tetik BELIRSIZ (ELLE gibi, fail-closed); beyan ayristirmasi doc "
                  "bicimini SAYMIYOR; beyan edilen alt kume kosmuyorsa KIRMIZI, "
                  "gerekceli muafsa YESIL, beyansiz modifikator bayrak YESIL; uyari "
                  "katmani bulgu bassa da ISTISNA atsa da exit kodunu DEGISTIRMIYOR")
        else:
            for h in hata7:
                print("  ❌ " + h)
        ok8, hata8 = kesif_predikat_kontrol()
        print("KESIF PREDIKATI — IKI YONLU (%d fikstur: pozitif ad konvansiyonlari + "
              "negatif kapsam disi ad/uzanti/dizin)"
              % len(KESIF_PREDIKAT_FIKSTURLERI))
        if ok8:
            print("  ✅ `-test`/`test-`/`-kapisi`/`-mutasyon` YAKALANIYOR; dokuman/veri "
                  "(`.md`/`.json`/`.txt`), `tools/arsiv/`, alt dizinler ve `-mutasyonlu` "
                  "gibi jeton-disi adlar YAKALANMIYOR")
        else:
            for h in hata8:
                print("  ❌ " + h)
        ok9, hata9 = izlenmeyen_fikstur_kontrol()
        print("IZLENMEYEN KESIF KOVASI + PUSH KAPSAMI — SENTETIK GIT DEPOSU "
              "(18 iddia: A1a taban "
              "hukmu · A1b taban kovasi · A2 kova doluyor (4 ad sinifi) · A3 `git "
              "add` ONCESI kapsam bilinmiyorsa KIRMIZI · A4 `git add` SONRASI "
              "etiket degisiyor · A5 negatif sizinti yok (.gitignore dahil) · A6 "
              "kapsanan izlenmeyen YESIL · A7/A8 olculemedi fail-closed · V1 izlenen "
              "KIRMIZI · V2 push-yeni KIRMIZI · V3 push-disi WIP UYARI+YESIL · "
              "bozuk/yok ref fail-closed)")
        if ok9:
            print("  ✅ V1/V2 KIRMIZI; V3 YESIL+UYARI; kapsam git'in pre-push "
                  "ref/SHA araligindan turetiliyor; kapsam yok/bozuksa eski kati "
                  "hukumle fail-closed; `.md`/`.json`/alt dizin/`tools/arsiv/` "
                  "SIZMIYOR")
        else:
            for h in hata9:
                print("  ❌ " + h)
        ok10, hata10 = main_kablosu_kontrol()
        print("main() KABLOSU — UCTAN UCA SENTETIK DEPO (6 iddia: K1 taban rc=0 · K2 "
              "izlenmeyen+kapsamsiz dosya varken rc=1 + adiyla basiliyor · K3 uretim "
              "SEBEBI yutulmuyor · K4/K5 kuresel sizinti YOK (normal + ISTISNA yolu) "
              "· K6 yeniden giris fail-closed reddediliyor)")
        if ok10:
            print("  ✅ `main()` -> `kesfet_izlenmeyen()` -> `denetle()` kablosu "
                  "FIILEN olculuyor (izlenmeyen=None / izlenmeyen=[] / sebep-yutma "
                  "mutantlari BURADA duser); fiksturun ezdigi 6 global her yolda "
                  "geri yukleniyor ve ic ice giris REDDEDILIYOR")
        else:
            for h in hata10:
                print("  ❌ " + h)
        ok13, hata13 = hukum_davranis_kontrol()
        print("HUKUM EZME SINIFI — DAVRANIS AYAGI (her nobetci TEK TEK `False` "
              "dondurulur, kollar UCTAN UCA kosulur, rc SIFIR-DISI olmali)")
        if ok13:
            print("  ✅ nobetci `False` dondugunde onu CAGIRAN her kol KIRMIZI yaniyor "
                  "(soru 'kod hukmu eziyor mu' DEGIL, 'nobetci False donerse kol "
                  "kirmizi mi' — bu KARAR VERILEBILIR)")
        else:
            for h in hata13:
                print("  ❌ " + h)
        ok12, hata12 = hukum_fuzz_kontrol()
        print("HUKUM KURALI FUZZ'I — IKI YONLU (%d varyant: %d mesru yazim YESIL "
              "kalmali + %d sabotaj KIRMIZI yakmali)"
              % (len(HUKUM_FUZZ_FIKSTURLERI),
                 sum(1 for _e, _c, _i, y, _n in HUKUM_FUZZ_FIKSTURLERI if y),
                 sum(1 for _e, _c, _i, y, _n in HUKUM_FUZZ_FIKSTURLERI if not y)))
        if ok12:
            print("  ✅ tasiyici/ternary/`or`/lambda/abone/derin-zincir yazimlari "
                  "SAHTE-KIRMIZI yakmiyor; `bool(1)`/`len()==0`/`any([])`/"
                  "`globals()[...]`/sabit-literal/`if True:` ezmeleri TEK BASINA "
                  "kirmizi")
        else:
            for h in hata12:
                print("  ❌ " + h)
        ok11, hata11 = kanca_kablo_serit_kontrol()
        print("KANCA KABLOSU SERIDI — AGIR AYAK BLOKLAYICI JOB'DA MI (davranissal: "
              "adim GERCEK ayristiriciyla bulunur, job adi soylenir, `deploy: needs` "
              "gecisli zinciri cozulur)")
        if ok11:
            print("  ✅ `%s` adimi `deploy: needs` zincirindeki bir job'da kosuyor -> "
                  "N1/N3/X4 sinifi ALARM degil KAPI (yayin bloklanir)"
                  % KANCA_KABLO_BAYRAGI)
        else:
            for h in hata11:
                print("  ❌ " + h)
        _kol = dict(NOBETCI_KABLOLARI)
        _birlesim = set()
        for _a, _g in NOBETCI_KABLOLARI:
            _birlesim |= set(_g)
        print("KOL KAPSAMI — UC SERIT: bu kol (`%s`, nobet.yml SERIT B, yayini "
              "BLOKLAMAZ) %d oz-nobetci · BAYRAKSIZ kapsam kolu (pre-push + CI, "
              "BLOKLAYICI) %d · `%s` (deploy.yml serit-a3, BLOKLAYICI) %d [%s] · "
              "BIRLESIM %d (taban %d). AGIR davranis ayagi (45 gercek `git push`) "
              "BU KOLDA DEGIL, ucuncu seritte."
              % (KENDINI_TEST_BAYRAGI, len(_kol.get("main", ())),
                 len(_kol.get("denetle", ())), KANCA_KABLO_BAYRAGI,
                 len(KANCA_KABLO_KOL_NOBETCILERI),
                 ", ".join(KANCA_KABLO_KOL_NOBETCILERI), len(_birlesim),
                 KOL_BIRLESIM_TABANI))
        if (ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 and ok8 and ok9
                and ok10 and ok11 and ok12 and ok13):
            print("SONUC: YESIL ✅")
            return 0
        print("SONUC: KIRMIZI ❌")
        return 1

    if not os.path.exists(args.deploy):
        sys.exit("deploy.yml bulunamadi: " + args.deploy)
    with open(args.deploy, encoding="utf-8") as f:
        deploy_metin = f.read()

    gercek_deploy = os.path.abspath(args.deploy) == os.path.abspath(DEPLOY_VARSAYILAN)
    # 🔴 GERCEK ENVANTER: IZLENEN TUM is akislari + tetik sinifi. `--deploy <mutant>`
    # verildiginde deploy.yml girisinin METNI mutantla degistirilir -> GERCEK dosyaya
    # DOKUNMADAN kirmizi-mutasyon kanitlanabilir.
    izlenmeyen, izlenmeyen_sebep = kesfet_izlenmeyen()
    if args.pre_push:
        push_kapsami, push_kapsami_sebep = push_kapsamini_turet(sys.stdin.read())
    else:
        push_kapsami = None
        push_kapsami_sebep = "--pre-push verilmedi; ref/SHA kapsami mevcut degil"
    kod, satirlar = denetle(
        deploy_metin, kesfet(), IZIN_LISTESI, kontroller=gercek_deploy,
        akislar=is_akislari(None if gercek_deploy else deploy_metin),
        izlenmeyen=izlenmeyen, izlenmeyen_sebep=izlenmeyen_sebep,
        model_uretim=gercek_deploy, push_kapsami=push_kapsami,
        push_kapsami_sebep=push_kapsami_sebep)
    for satir in satirlar:
        print(satir)
    return kod


if __name__ == "__main__":
    sys.exit(main())
