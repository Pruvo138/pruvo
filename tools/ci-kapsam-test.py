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
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DEPLOY_VARSAYILAN = os.path.join(ROOT, ".github", "workflows", "deploy.yml")


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


# ---- GERCEK YAML AYRISTIRICISI — TEK KARAR MERCII (PARSER-FIRST) -----------
# tools/yaml-oku.py (KATMAN 0): `run:` degerlerini GERCEK bir ayristiriciyla
# (PyYAML | ruby/psych) cozer ve HAM satir araligini verir. FAIL-CLOSED yuklenir:
# dosya kaldirilirsa kapi taklide SESSIZCE dusmez, konusur.
_YAML_OKU_SOZLESME = ("run_dugumleri", "ayristirici_adi", "onbellegi_isit")


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
TOOLS_PAT = re.compile(
    r"^tools/([^/]*-test\.(?:py|js)|test-[^/]*\.(?:py|js)|[^/]*-kapisi\.py)$")
DIR_PAT = re.compile(r"^(?:shop/test|onizleme/test|jenerator/test)/[^/]+\.(?:py|js|mjs|cjs)$")


def kesfet():
    """git ls-files uzerinden IZLENEN kabul-testi dosyalarini (repo-rel yol) dondur."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    bulunan = []
    for yol in r.stdout.splitlines():
        if yol.startswith("tools/arsiv/"):
            continue
        if TOOLS_PAT.match(yol) or DIR_PAT.match(yol):
            bulunan.append(yol)
    return sorted(bulunan)


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

# ---- IZIN LISTESI (muaf test -> GEREKCE). Bos gerekce = exit 1. ----------
IZIN_LISTESI = {
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
    # "jenerator/test/kabul.py" MUAFIYETI KALDIRILDI (31 Tem, madde 34b) — ayni gerekce:
    # `--kendini-test` kolu TARAMA KUMESI nobetcisini sinar (5 iddia: gitignore'lu artefakt
    # sahte KIRMIZI yakmiyor · izlenen kaynak taraniyor · izlenmeyen-ama-yoksayilmayan yeni
    # kaynak yakalaniyor · beyanli uretilen kok taraniyor · kume olculemezse OLCULEMEDI).
    # argparse'ta sys.exit(kendini_test()) ile ERKEN DONER: TEST 1'in OpenSCAD render'ina ve
    # build.py cagrisina HIC girmez. 8 testlik TAM suite CI'ya BAGLANMADI (openscad ister).
    "jenerator/test/kalibrasyon-referans-uret.py": (
        R_URETEC + " Somut: kalibrasyon-referans.json fiksturunu YAZAR — CI'da kosarsa "
        "kabul testlerinin karsilastirdigi referansi EZER (test kendi kendini onaylardi)."),
    "jenerator/test/kalibrasyon-senkron.js": (
        "🔴 GEREKCE DUZELTILDI (31 Tem): eski blanket R_AYRI cumlesi ('o projenin CI "
        "hattinda kosulur') YANLISTI — oyle bir hat YOK. GERCEK engel iki parcali ve "
        "SOMUT: (1) testin CEKIRDEK iddiasi olan 2. katman (kardes ev "
        "~/dev/pruvo-jenerator/dogrulama/test/aileler ile birebir senkron) CI fresh "
        "checkout'unda YAPISAL olarak olculemez — dizin yoktur, kol sessizce atlanir ve "
        "geriye yalnizca dondurulmus referans karsilastirmasi kalir (R_YOL sinifi, "
        "mimar-kapi-6ev-test.py emsali); (2) o kalan kol bile TEMIZ checkout'ta 25,2 s "
        "surdu (olculdu) — tek build job'una eklenen en pahali aday. Hacim/fiyat "
        "cekirdegi CI'da jenerator/test/fiyat-test.js + konfigur-test.py ile olculuyor."),
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
    "tools/parite-mutasyon-test.js": (
        R_YAVAS + " OLCULDU (31 Tem, temiz checkout): 14 mutant x fikstur kosumu = "
        "217,1 s — tek build job'unu blokar (M14 asilma nobeti tek basina ~120 s). "
        "Kardesleri (parite-sozlesme + parite-fikstur) artik CI'da kosuyor; bu dosya "
        "izole/ayri bir job'a alinmadan Pages hattina EKLENMEZ."),
    # --- tools/ python: mimar-disiplin (mutlak yol + commit'siz kablolama) ---
    "tools/mimar-kilit-test.py": R_YOL,
    "tools/mimar-commit-kapisi-test.py": R_YOL,
    "tools/mimar-kapi-mutasyon-test.py": R_YOL,
    # MAKINEYE BAGIMLI: kardes mimar evi dizinleri (~/dev/pruvo-hasat, -jenerator, -pazarlama,
    # -bot, -advisor) CI runner'inda YOK -> fail-closed test orada yapisal KIRMIZI yanar ve
    # bloklayici adim olarak TUM yayini durdurur (yedekle-test.py / yedek-hook-test.py emsali).
    "tools/mimar-kapi-6ev-test.py": (
        R_YOL + " Somut olarak: olcum girdisi 5 KARDES MIMAR EVININ dizini (~/dev/pruvo-hasat, "
        "-jenerator, -pazarlama, -bot, -advisor) ve o evlerin commit EDILMEYEN "
        ".claude/mimar-icra-kapisi.py kapilari. CI fresh checkout'unda bu evlerin hicbiri "
        "YOKTUR -> 6 evin 5'i olculemez, fail-closed test KIRMIZI yanar."),
    "tools/kapi-envanteri-test.py": R_YOL,
    "tools/kod-kilidi-test.py": R_YOL,  # E paketi YESILLEDI; mutlak /Users/okan/dev/pruvo yoluna bagli -> fresh checkout'ta yapisal KIRMIZI
    "tools/agent-kapisi-test.py": (
        R_YOL + " Somut: AGENT-KAPISI kabul testi (28 Tem) — mimar-icra-kapisi.py'nin "
        "Agent/Task kolu + mimar-kapi-kur.py kablosu; mimar-kilit/6ev/mutasyon/kod-kilidi ile "
        "AYNI aile. Girdisi kardes mimar evi gate'leri (/Users/okan/dev/pruvo-hasat, -advisor "
        "... .claude/mimar-icra-kapisi.py) ve o evlerin commit EDILMEYEN kablolamasi. "
        "🔴 GEREKCE DUZELTILDI (31 Tem, OLCULDU): eski metin 'Bolum A+B offline-YESIL, C "
        "guarded-CEVRE-ATLANAN (skip=exit 0)' diyordu — bu YANLIS. `git clone --local` ile "
        "kurulan TEMIZ checkout'ta bayraksiz kosum rc=1 verdi "
        "(\"SONUC: KIRMIZI — basarisiz: ('MaCiT','ZATEN TAM',[]) ('BaBa','ZATEN TAM',[])\"), "
        "yani atlanan degil KIRMIZI yanan bir kol var. Bloklayici adim olarak eklenirse "
        "CI'da yapisal olarak TUM yayini durdururdu. Muafiyet MESRU; gerekce artik "
        "olculen davranisi anlatiyor."),
    # --- tools/ NOBETCILER (*-kapisi.py) — kesif 21 Tem genisletildi, CI'da kosmayanlar ---
    "tools/komut-stili-kapisi.py": R_HOOK,
    "tools/mimar-icra-kapisi.py": R_HOOK,
    "tools/mimar-commit-kapisi.py": (
        R_HOOK + " Ayrica git commit backstop'u olarak commit EDILMEYEN .git/hooks kablolamasina "
        "ve ana-checkout/worktree ayrimina bagli (R_YOL ile ayni sinif)."),
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
    "tools/filament-test.py": (
        R_YAVAS + " + " + R_AG + " 🔴 GEREKCE DUZELTILDI (1 Agu, OLCULDU): eski metin "
        "\"76,1 s\" diyordu — BAYATTI (katalog buyudu) ve TEK EKSENLIYDI. Iki somut engel:\n"
        "  (1) SURE: `PARITE=0` ile bile 161,8 s (16.736 urun). Testin 0. adimi build.py'yi "
        "      BASTAN kosturur; deploy zaten ayni build'i yapar -> tek build job'una eklenen "
        "      EN PAHALI kalem olur (feed-cache-bust 25,4 s ile kiyasla ~6x).\n"
        "  (2) AG: VARSAYILAN kosum (PARITE=1) TEST 5'te `node tools/parite-test.js 300` + "
        "      `parite-ege.js 200` ile CANLI CDN/D1'e 500 istek atar -> regresyon-kapisi.py "
        "      ile AYNI sinif (R_AG): tek gecici DNS/429 hatasi tum ekibin yayinini durdurur. "
        "      `PARITE=0` ile baglamak bu ekseni ANLAMSIZ YESILE cevirir ([[kapi-kapsam-eksen"
        "-secimi]]); bu depoda \"hem kosuyor hem olcmuyor\" hali kabul edilmiyor.\n"
        "  CI'YA ALINMA KOSULU (feed-cache-bust emsali): alt-surec build.py yerine "
        "  `build.render_product` import edilip yalniz FIKSTUR sayfalari uretilirse sure "
        "  saniyeye iner; TEST 5 ayri (agli) bir is'e alinir. O iki sart saglanmadan EKLENMEZ.\n"
        "  NOT: fikstur kaymasi (eski 7/25 kirmizisi) 1 Agu'da KAPANDI ve TEST 26 nobetcisi "
        "  eklendi (26/26); yani muafiyet artik BILINEN BIR KIRMIZIYI ortmuyor."),
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
    "tools/yedekle-test.py": (
        "Olcum girdisi MAKINEYE OZGU ve git DISI: ~/.claude/skills agaci (yedeklenen sey) ile "
        "Google Drive mount'u. CI fresh checkout'unda ikisi de YOK -> kapsam kontrolleri "
        "yapisal olarak KIRMIZI yanar (R_YOL sinifi; sentetik sir/mutasyon bolumleri offline "
        "yesil olsa da testin cekirdek iddiasi 'gercek skill agaci planda mi' CI'da "
        "olculemez). Ayrica yedekle.py yayin hattinin parcasi degil: yerel disk-kaybi "
        "sigortasi -> Pages build'ini bloklamasi orantisiz."),
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
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()

    icra_idx = _icra_satir_indeksleri(gercek, hedef)
    if not icra_idx:
        return False, ["gercek deploy.yml'de %s'yi KOSAN hicbir icra satiri yok "
                       "(cagri bicimi degistiyse bu nobetciyi guncelle)" % hedef]

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
KENDINI_TEST_TANI = (
    "deploy.yml'de bu betigi `--kendini-test` ile ANLAMLI olarak kosan hicbir adim YOK "
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
    "deploy.yml'de bu betigi BAYRAKSIZ (kapsam kolu) ANLAMLI olarak kosan hicbir adim YOK.\n"
    "   OLCULEN IKI DELIK (30 Tem, geçici kopyada; dort denetci de rc=0 idi):\n"
    "     (1) `run: python3 tools/ci-kapsam-test.py --help` -> adim CI'da YESIL kosar,\n"
    "         argparse kullanim metnini basip exit 0 verir, HICBIR kapsam iddiasi olculmez.\n"
    "     (2) bayraksiz ADIM butunuyle SILINIR, yalniz `--kendini-test` adimi kalir ->\n"
    "         KAPSAM kurali (her kabul testi kosuluyor/muaf) CI'da HIC olculmez.\n"
    "   Ikisi de `kosulan()` tarafindan gorulemez: bu betigin deploy.yml'de IKI cagrisi\n"
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
    verdi (ham cikti RAPOR-MIMARA.md). `echo` bir MENSIYON komutudur; artik
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
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
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
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
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
                               ICRA_INDEKS_FIKSTUR_ASGARI)):
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
NOBETCI_KABLOLARI = (
    ("denetle", ("bulgu1_mutasyon_kontrol", "muaf_sayaci_kontrol",
                 "kendini_test_adimi_kontrol", "bayraksiz_adim_kontrol",
                 "suzgec_fikstur_kontrol", "suzgec_kablosu_kontrol")),
    ("main", ("bulgu1_mutasyon_kontrol", "muaf_sayaci_kontrol",
              "kendini_test_adimi_kontrol", "bayraksiz_adim_kontrol",
              "suzgec_fikstur_kontrol", "suzgec_kablosu_kontrol")),
)


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


def suzgec_kablosu_kontrol():
    """SUZGEC KABLOSU NOBETCISI — ortak suzgec GERCEKTEN cagriliyor mu (AST).

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
    kaynak_yol = os.path.abspath(__file__)
    try:
        with open(kaynak_yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
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
    return (not hata), hata


# ---- SAF DENETIM GOVDESI ---------------------------------------------------
# main() eskiden hem karar veriyor hem BASIYORDU -> govdeyi disaridan (nobetciden)
# olcmek imkansizdi ve "CI'da kosan kod" ile "test edilen kod" ayrisiyordu.
# denetle() saftir: girdisini parametreden alir, hicbir sey basmaz, (kod, satirlar) dondurur.
# Boylece muaf_sayaci_kontrol() TA KENDISINI olcer (kopya mantik yazmaz).
def denetle(deploy_metin, kesif, izin_listesi, kontroller=True):
    """(exit_kodu, rapor_satirlari) dondurur. Hicbir sey BASMAZ.

    kontroller=True iken kendi mutasyon nobetcilerini (bulgu1 + muaf sayaci) BLOKLAYICI
    olarak kosar. muaf_sayaci_kontrol() bu fonksiyonu tekrar cagirdigi icin oradan
    DAIMA kontroller=False ile girilir (OZYINELEME KORUMASI)."""
    satirlar = []
    kos = kosulan(deploy_metin, kesif)
    kesif_kume = set(kesif)

    # T8: bloklamayan gelecek-robustluk uyarisi (hatalar listesine GIRMEZ, exit degismez).
    for satir in sayilamayan_python3(deploy_metin):
        satirlar.append("UYARI: python3 iceren ama sayilamayan icra satiri "
                        "(bare 'python3 tools/x.py' formu kullan): %s" % satir)

    hatalar = []

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
    kapsamsiz = []
    for yol in kesif:
        if yol in kos:
            continue
        if yol in izin_listesi:
            continue
        kapsamsiz.append(yol)
    for yol in kapsamsiz:
        hatalar.append("KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % yol)

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
    satirlar.append("  deploy.yml'de kosulan  : %d  (%s)" % (
        len(kos), ", ".join(sorted(kos)) or "-"))
    satirlar.append("  Muaf (izin listesi)    : %d" % len(muaf))
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
    args = ap.parse_args()

    # 🔴 HANGI KOL KARAR VERIYOR (mimar hukmu madde 3) — HER kosumda basilir.
    print("  YAML ayristirici kolu  : %s" % (
        YAML_OKU.ayristirici_adi() or "YOK -> taklit-fallback (fail-closed)"))

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
        if ok1 and ok2 and ok3 and ok4 and ok5 and ok6:
            print("SONUC: YESIL ✅")
            return 0
        print("SONUC: KIRMIZI ❌")
        return 1

    if not os.path.exists(args.deploy):
        sys.exit("deploy.yml bulunamadi: " + args.deploy)
    with open(args.deploy, encoding="utf-8") as f:
        deploy_metin = f.read()

    kod, satirlar = denetle(
        deploy_metin, kesfet(), IZIN_LISTESI,
        kontroller=os.path.abspath(args.deploy) == os.path.abspath(DEPLOY_VARSAYILAN))
    for satir in satirlar:
        print(satir)
    return kod


if __name__ == "__main__":
    sys.exit(main())
