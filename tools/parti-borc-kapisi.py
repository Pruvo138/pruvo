#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/parti-borc-kapisi.py — PAKET T4: ACIK KALEMLI EVDE YENI PARTI MAKINECE RED.

Mimar hukumu (18 Agu 2026, KraL): `tools/paket-t4-parti-reddi.md`.

Bir evin **acik kalem borcu** varken o evde **YENI PARTI** baslatmak makinece
REDDEDILIR. "Parti" = katalog/urun hattinda toplu is baslatan giris noktasi
(ornek: `tools/urun-ekle.py` ve kardesleri). Bu kapi kapisi yazar, olcer,
kendini-test eder; gercek parti AKISINI DURDURMAZ (ayri karar: Okan kapisi).

5 kol — her biri MUTANT tarafindan hedef kolu kanitlanmistir:
  T4-OLCUTSUZ    : (K289, 25 Agu 2026) bir ACIK kalem makine-okunur kapanis
                   olcutu (`kabul:` alani) TASIMIYORSA parti REDDEDILIR — ESIKTEN
                   BAGIMSIZ ve T4-BORC'tan ONCE. Gerekce: olcutu olmayan borc
                   SAYILABILIR ama KAPATILAMAZ; ev suresiz kilitli kalir.
                   Mesaj `T4-OLCUTSUZ ` onekiyle baslar (kol ayrimi).
  T4-BORC        : evin acik kalem sayisi esigi ASIYORSA parti REDDEDILIR (rc!=0).
                   Mesaj `T4-BORC ` onekiyle baslar (kol ayrimi).
  T4-TEMIZ       : acik kalem sayisi esigin ALTINDAYSA parti GECER. Bu kol
                   YANLIS-POZITIF nobeti: borc 0 oldugunda T4-BORC'un RED
                   uretmedigini kanitlar (kirmizi = esik altinda kabul DEGIL).
                   Mesaj `T4-TEMIZ ` onekiyle baslar.
  T4-EV          : borc, partiyi baslatanin EVINDEN okunur. Baskasinin defteri
                   KARAR VERMEZ — parti baslatan EV=ArTisT ise KraL'in 12 acik
                   kalemi olsa bile GECER (cunku parti ArTisT'de baslar).
                   Mesaj `T4-EV ` onekiyle baslar.
  T4-OLCULEMEDI  : defter okunamiyorsa (yol yok / IO / format bozuk) **fail-closed
                   RED** ("borc yok" SAYILMAZ). Mesaj `T4-OLCULEMEDI ` onekiyle
                   baslar (kol ayrimi).

Isletim modlari:
  default (kontrol): gercek EV'in defterini okur, esikle karsilastirir, RED/GECER.
                     Tek bir EV ile calisir (--ev). YAZMAZ.
  --kendini-test    : 6 mutant + 1 kontrol + izolasyon (tempfile.mkdtemp).
                      Gercek deftere DOKUNMAZ.
  --rapor           : gercek defterler uzerinde YAZMADAN; her ev icin acik kalem
                      sayisi + esik + RED/GECER hukumu basar. Salt okuma.

KABUL (calistirilabilir):
  python3 tools/parti-borc-kapisi.py --kendini-test
    -> rc=0, MUTANT=6/6 KONTROL=1/1, bes kol adi ciktida GECER.
       M5/M6 hedef-kol atfi ESIK ALTINDA olculur (T4-BORC atesleyemez), ve
       kol OLDURULUNCE/GEVSETILINCE ayni fikstur GECER'e doner — "kirmizi
       geldi" tek basina kanit sayilmaz ([[ad-iki-rolde-mutanti-golgeler]]).

  python3 tools/parti-borc-kapisi.py --rapor
    -> her evin acik kalem sayisi + esik + RED/GECER.

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ (bu kapinin isi degil).
  - --kendini-test gercek defterlere DOKUNMAZ; tempfile.mkdtemp altinda kosar.
  - esik ve ev->defter eslemesi TEK KAYNAKTA sabit (buradaki sabitler); ikinci
    kopya YASAK.
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import tempfile

# ---- sabitler -----------------------------------------------------------------
# Bir evin "acik kalem borcu" tek sayi: acik-kalemler.md icindeki tablo satirlarinda
# durum sutunu ACIK/UCUSTA/OKAN-KAPISI/🔧 olanlar (KAPANDI HARIC). Bu esik
# makinece sabit: 0 (her acik kalem bir engel). Spec acik bir sayi vermedigi
# icin varsayilan 0 (sifir-disi acik = RED). --esik ile asilabilir.
DEFAULT_ESIK = 0

# Durum sutunu degerleri — KAPANDI HARIC hepsi acik sayilir.
# acik-kalemler.md doktrinine gore bes deger: ACIK · UCUSTA · OKAN-KAPISI · KAPANDI · 🔧.
# Burada yalniz KAPANDI "kapali" sayilir; diger dort deger acik.
ACIK_DURUMLAR = frozenset({"ACIK", "UCUSTA", "OKAN-KAPISI", "🔧"})

# EV -> defter yolu koku. Tek kaynak: /Users/okan/.claude/projects/-Users-okan-
# dev-pruvo-<EV>/memory/acik-kalemler.md. (T3 ile ayni EV_DIZIN yapisi; burada
# acik_kalem_yolu(ev) uretip ozellikle sade tutuldu.)
EV_DIZIN = {
    "KraL":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",
    "MaCiT":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-hasat",
    "ArTisT":  "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-pazarlama",
    "HocA":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-bot",
    "TeKiN":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-jenerator",
    # 🔴 27 Agu 2026 (KraL-N2BEvHaritasi-27Agu) — BaBa'nin satiri BAYATTI.
    # Eskiden `-Users-okan-dev-pruvo` idi ("BaBa KraL'da oturur"); BaBa'nin
    # kendi deposu (`/Users/okan/dev/pruvo-advisor`) acildiktan sonra bu satir
    # ARTIK DOGRU DEGILDI ve iki sonucu vardi:
    #   (1) `parti-kapisi.ev_coz()` bu tablonun TERSINI kurar; advisor koku
    #       hicbir anahtara duşmedigi icin `N2B-OLCULEMEDI depo koku bilinen
    #       bir eve cozulemedi` -> HUKUM=RED -> sarmalayici exit 3. BaBa'nin
    #       isci kanali fiilen KAPALIYDI (olculdu, 27 Agu).
    #   (2) BaBa'nin defteri/postasi KraL'in dizininde ARANIYORDU.
    # Bu satir bir DIZGE yamasi degil, tablonun DISKTEKI gercege
    # esitlenmesidir; bilinmeyen kok HALA cozulemez (fail-closed KORUNUR).
    "BaBa":    "/Users/okan/.claude/projects/-Users-okan-dev-pruvo-advisor",
    "ORTAK":   "/Users/okan/.claude/projects/-Users-okan-dev-pruvo",
}

ACIK_KALEM_DOSYA = "memory/acik-kalemler.md"

EV_BILINEN = frozenset(EV_DIZIN.keys())

# Hedef kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir.
# Kol ATIFI mesajin BASINDA gecer; mutant dogrulamasi `startswith(kol + " ")`
# ile yalnizca kendi kolunun imzasini dogrular. Bu sayede bir kol oldurulunce
# diger kolun mesaji onun yerine gecse bile mutant YASAMAZ (kol ayrimi).
T4_BORC_JETON       = "T4-BORC"
T4_TEMIZ_JETON      = "T4-TEMIZ"
T4_EV_JETON         = "T4-EV"
T4_OLCULEMEDI_JETON = "T4-OLCULEMEDI"
# 🔴 K289 (25 Agu 2026) — SINIF KOLU: OLCUTSUZ KALEM.
# OLCULEN ARIZA: KraL defterindeki 26 acik kalemin 17'si makine-okunur bir
# kapanis olcutu (`kabul:` alani) TASIMIYORDU — sayi TAHMIN DEGIL, kolun kendi
# ciktisindan okundu: `--ev KraL` -> `OLCUTSUZ_KALEM: 17 -> K24,K26,K27,K29,K31,
# K35,K36,K42,K44,K55,K57,K62,K67,K50,K74,K87,K92`. Olcutsuz kalem KAPANAMAZ, cunku
# "kapandi" hukmu ne kosulacagini kimse bilmiyor — kalem defterde suresiz durur
# ve ev makinece kilitli kalir ([[kayit-kendini-olcmez]] K201 ailesi).
# KOL: bir evin ACIK kalemi `kabul:` tasimadan yeni is baslatilamaz.
T4_OLCUTSUZ_JETON   = "T4-OLCUTSUZ"

# (kod yolu — mutanti yok) T4-BORC-HUKUMSUZ: defter bos olsa bile RED
# yerine GECER donerse (T4-BORC govdesi oldurulurse) M1 yakalar.
# Bu sabit yalnizca dokumantasyon; mutasyon yok.

# Mutant adlari + hedef kol eslestirmesi.
MUTANT_HEDEF = {
    "M1": T4_BORC_JETON,
    "M2": T4_TEMIZ_JETON,
    "M3": T4_EV_JETON,
    "M4": T4_OLCULEMEDI_JETON,
    # K289 — iki mutant kolun IKI AYRI yanini oldurur; tek mutant yetmez
    # ([[ad-iki-rolde-mutanti-golgeler]] + K182 hedef-kol atfi).
    "M5": T4_OLCUTSUZ_JETON,   # kol tamamen OLDURULUR  -> olcutsuz kalem GECER
    "M6": T4_OLCUTSUZ_JETON,   # kol GEVSETILIR (kanit dolu olsun yeter)
}


# ------------------------------------------------------------------------------
# EV -> defter yolu
# ------------------------------------------------------------------------------
def _repo_kok():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def acik_kalem_yolu(ev, koku_root=None):
    """Bir EV icin acik-kalemler.md yolunu doner.

    koku_root verilmisse (--kendini-test izolasyonu) o kokun ALTINDA
    <EV>/memory/acik-kalemler.md'ye yazilir. Gercek modda EV_DIZIN[ev] kullanilir.

    Return: (kok, acik_kalem_yolu, EV_gecerli_mi). Gecersiz EV icin hepsi None.
    """
    if ev not in EV_BILINEN:
        return None, None, False
    if koku_root is not None:
        # Izolasyon: her EV ayri alt dizinde.
        yol = os.path.join(koku_root, ev, ACIK_KALEM_DOSYA)
        return koku_root, yol, True
    kok = EV_DIZIN.get(ev)
    if kok is None:
        return None, None, False
    return kok, os.path.join(kok, ACIK_KALEM_DOSYA), True


# ------------------------------------------------------------------------------
# DEFTER OKUMA
# ------------------------------------------------------------------------------
# acik-kalemler.md icindeki tablo formati (kaynak: DEVAM.md'deki ornek format):
#   | id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |
# Tablo, markdown pipe-row: satir `|` ile baslar ve en az 5 `|` tasir. Durum
# sutunu 5. sutun (0-indeksli: 4). Bu parser FORMAT BOZUKLUGUNU YUTMAZ: beklenen
# kolon sayisi tutmazsa ya da durum sutunu bos ise okunamadi sayilir (fail-closed).
TabloSatir = re.compile(r"^\s*\|.*\|\s*$")


def defter_dosyasi_var_mi(defter_yolu):
    """Defter DOSYASI fiziksel olarak var mi?

    🔴 K229 — UCUNCU KOVA'nin TEK KAYNAGI. `acik_kalem_listesi`nin ILK kapisi
    BU fonksiyondur; cagiran taraf (N2B parti kapisi) "defter dosyasi YOK" ile
    "defter OKUNAMADI"yi ayirt ederken ikinci bir yuklem KURMAZ, buraya sorar.
    Ikinci bir `os.path.isfile` cagrisi yazilirsa iki yuklem SESSIZCE ayrisir
    ([[ayni-alan-iki-hukum-biri-sessiz]]).
    """
    return bool(defter_yolu) and os.path.isfile(defter_yolu)


def acik_kalem_listesi(defter_yolu):
    """Bir acik-kalemler.md dosyasindaki ACIK kalemleri DOKUMLU doner.

    🔴 TEK PARSER (19 Agu 2026, N2): `acik_kalem_sayisi` bu fonksiyondan
    TURER. Ikinci bir tablo okuyucu YAZILMAZ — N2'nin parti kapisi (yeni is
    basvurusunda kalem KIMLIGINI ve `kabul:` komutunu ekrana basmak zorunda)
    ayni satirlari buradan alir ([[ikiz-tanim-sessiz-ayrisma]]).

    Return: (kalemler, okundu_mu_bool, hata_mesaji_str_or_None)
      kalemler = [{"kimlik", "durum", "is", "kanit", "satir_no"}, ...]
    YOKSA / IO hatasi / format bozuk -> ([], False, hata). "borc yok" SAYILMAZ;
    fail-closed: cagri yeri T4-OLCULEMEDI ile RED verir.
    """
    if not defter_dosyasi_var_mi(defter_yolu):
        return [], False, "defter dosyasi yok: %s" % defter_yolu
    try:
        with open(defter_yolu, encoding="utf-8") as f:
            icerik = f.read()
    except OSError as e:
        return [], False, "defter okunamadi (IO): %r" % e

    if not icerik.strip():
        return [], False, "defter bos"

    kalemler = []
    tablo_basladi = False
    for satir_no, satir in enumerate(icerik.splitlines(), start=1):
        if not TabloSatir.match(satir):
            continue
        kolonlar = [k.strip() for k in satir.split("|")]
        # Markdown tablosunda: "" | col1 | col2 | ... | colN | ""
        # Yani split sonrasi: ['', col1, col2, ..., colN, '']
        if len(kolonlar) < 7:
            continue  # baslik (5 kolon) ya da ayrac (---|---) — gec
        # 5. sutun (1-indeksli) = kolonlar[5]; 0-indeksli = 5
        durum = kolonlar[5].strip()
        if not durum:
            continue
        # Ilk gecerli tablo satiri baslik DEGILSE — saymaya basla.
        # (Baslikta "durum" sozcugu durum degil; "Durum"/"durum" stringi
        #  eslestirilmez.)
        if not tablo_basladi:
            if durum.lower() in ("durum",):
                tablo_basladi = True
                continue
            # Eger ilk tablo satiri "durum" degilse — eski format / karmasik
            # format. Yine de say (durdur): "ACIK" olanlari say.
            tablo_basladi = True
        if durum in ACIK_DURUMLAR:
            kalemler.append({
                "kimlik": kolonlar[1].strip(),
                "durum": durum,
                "is": kolonlar[4].strip(),
                "kanit": kolonlar[6].strip() if len(kolonlar) > 6 else "",
                "satir_no": satir_no,
            })
    if not tablo_basladi:
        # Tablo bulunamadi; format bozuk (dosya var ama tablo yok).
        return [], False, "defter icinde tablo bulunamadi (format bozuk)"
    return kalemler, True, None


# ------------------------------------------------------------------------------
# K289 — OLCUTSUZ KALEM KOLU (T4-OLCUTSUZ)
# ------------------------------------------------------------------------------
# Makine-okunur kapanis olcutu = satirda gecen `kabul:` alani. Alan `is` ya da
# `kapanis kaniti` kolonunda olabilir (defterde ikisi de kullanilmis).
#
# 🔴 NEDEN `kabul:` VE "kanit dolu degil": defterdeki satirlarin cogu kanit
# kolonunda serbest metin tasiyor ("kanama sessiz", "—", "kismi: <sha>"). Bunlar
# KOSULABILIR bir olcut DEGIL. Kol yalnizca `kabul:` alanini arar; M6 mutanti tam
# olarak bu ayrimi oldurur (kanit-dolu yeterli sayilirsa serbest metin olcut
# gorunur ve kalem yine kapanamaz).
KABUL_ALANI_RE = re.compile(r"kabul\s*:", re.IGNORECASE)


def olcutsuz_kalemler(kalemler, *, mutant=None):
    """`kabul:` alani TASIMAYAN ACIK kalemleri doner (kimlik listesi).

    kalemler: `acik_kalem_listesi()` ciktisi (yalniz ACIK olanlar).
    mutant:   None (gercek) | "M5" (kol OLDURULUR) | "M6" (kol GEVSETILIR).
    """
    if mutant == "M5":
        # KOL OLU: hicbir kalem olcutsuz sayilmaz -> T4-OLCUTSUZ hic tetiklenmez.
        return []
    if mutant == "M6":
        # KOL GEVSEK: `kabul:` yerine "kanit kolonu bos degil" yeter. Serbest
        # metinli kanit tasiyan olcutsuz kalem GECER — kol korlesir.
        return [k for k in kalemler if not (k.get("kanit") or "").strip()]
    olcutsuz = []
    for k in kalemler:
        govde = "%s\n%s" % (k.get("is") or "", k.get("kanit") or "")
        if not KABUL_ALANI_RE.search(govde):
            olcutsuz.append(k)
    return olcutsuz


def acik_kalem_sayisi(defter_yolu):
    """Bir acik-kalemler.md dosyasindan ACIK kalem sayisini say.

    Return: (sayi, okundu_mu_bool, hata_mesaji_str_or_None).
    Sozlesme DEGISMEDI; govde `acik_kalem_listesi`den TURER (tek parser).
    """
    kalemler, okundu, hata = acik_kalem_listesi(defter_yolu)
    return len(kalemler), okundu, hata


# ------------------------------------------------------------------------------
# KARAR FONKSIYONU
# ------------------------------------------------------------------------------
def parti_engeli_var_mi(ev, esik=DEFAULT_ESIK, *, koku_root=None, muafiyet_yok=None,
                        olcut_mutant=None):
    """Parti baslatma engeli var mi?

    ev: parti baslatan ev.
    esik: acik kalem sayisi bu degeri ASIYORSA -> RED.
    koku_root: --kendini-test izolasyonu (None ise gercek EV_DIZIN).
    muafiyet_yok: True ise T4-BORC kolunu BYPASS eder (yanlis-pozitif nobet
                  testi icin: gercek bir borc oldugunda RED uretmesini
                  beklemiyoruz; "borc var" demesini istiyoruz). Kullanim:
                  T4-TEMIZ ve T4-EV kollarinda borc olan bir evde bile GECER
                  istemiyoruz; bu yuzden MUAFIYET YOK.

    Return dict:
      {
        "EV": str,
        "ACIK_SAYISI": int,
        "ESIK": int,
        "RED": bool,                    # True == parti reddedildi
        "RED_SEBEBI": str|None,         # RED ise neden
        "GECER_MESAJI": str|None,       # GECER ise neden
        "HATA": str|None,               # format/IO hatasi (T4-OLCULEMEDI)
        "OLCULEMEDI": bool,             # True == defter okunamadi
        "DEFTER_YOK": bool,             # True == defter DOSYASI hic YOK (K229)
        "DEFTER_YOLU": str|None,
        "ESIK_ASILDI": bool,            # ACIK_SAYISI > ESIK ise True
        "DURUM": "ACIK"|"KAPANDI"|"BILINMIYOR",   # KAPANDI=kapanmis kalem
      }

    Kabul sozlesmesi:
      - ev gecersiz ise: HATA T4-OLCULEMEDI onekiyle (EV_GECERSIZ) RED.
      - defter okunamadi ise: HATA T4-OLCULEMEDI onekiyle (OLCULEMEDI) RED.
      - ACIK_SAYISI > esik ise: RED, RED_SEBEBI T4-BORC onekiyle.
      - aksi: GECER, GECER_MESAJI T4-TEMIZ onekiyle.
    """
    sonuc = {
        "EV": ev,
        "ACIK_SAYISI": 0,
        "ESIK": esik,
        "RED": False,
        "RED_SEBEBI": None,
        "GECER_MESAJI": None,
        "HATA": None,
        "OLCULEMEDI": False,
        "DEFTER_YOK": False,
        "DEFTER_YOLU": None,
        "ESIK_ASILDI": False,
        "DURUM": "BILINMIYOR",
        # K289 — olcutsuz (kabul: alani olmayan) ACIK kalemler.
        "OLCUTSUZ": [],
        "OLCUTSUZ_SAYISI": 0,
    }

    kok, defter_yol, gecerli = acik_kalem_yolu(ev, koku_root=koku_root)
    if not gecerli:
        # Gecersiz EV — T4-OLCULEMEDI sinifinin alt turu (kol ayrimi: bu mesaj
        # T4-OLCULEMEDI onekiyle baslar ki M4 yanlis tetiklenmesin; M4
        # "defter okunamadi"yi hedefler, EV gecersizligi DEGIL — fakat bu
        # ikisi de fail-closed RED oldugu icin ayni kolun uzantisi).
        sonuc["HATA"] = ("T4-OLCULEMEDI EV gecersiz: %r" % ev)
        sonuc["OLCULEMEDI"] = True
        sonuc["RED"] = True
        sonuc["DURUM"] = "BILINMIYOR"
        return sonuc
    sonuc["DEFTER_YOLU"] = defter_yol

    # Defter oku (TEK PARSER — `acik_kalem_listesi`)
    kalemler, okundu, hata = acik_kalem_listesi(defter_yol)
    sayi = len(kalemler)
    sonuc["ACIK_SAYISI"] = sayi
    if not okundu:
        # T4-OLCULEMEDI: fail-closed RED ("borc yok" SAYILMAZ).
        # 🔴 K229 — T4'un HUKMU DEGISMEDI (burasi hala fail-closed RED). Yalniz
        # ALT SINIF makinece GORUNUR kilindi: `DEFTER_YOK` = defter DOSYASI hic
        # yok (ev defter gelenegini benimsememis) · `DEFTER_YOK=False` +
        # `OLCULEMEDI=True` = defter VAR ama okunamadi (bos/bozuk/IO). Ikisini
        # ayirmak POLITIKA katmanının (N2B parti kapisi) isidir; T4 yalnizca
        # OLCUYU verir, kapiyi acmaz [[iki-kovali-siniflama-ucuncu-sinifi-yutar]].
        sonuc["DEFTER_YOK"] = not defter_dosyasi_var_mi(defter_yol)
        sonuc["HATA"] = "T4-OLCULEMEDI %s" % (hata or "defter okunamadi")
        sonuc["OLCULEMEDI"] = True
        sonuc["RED"] = True
        sonuc["DURUM"] = "BILINMIYOR"
        return sonuc

    # --- K289 KOL: T4-OLCUTSUZ (ESIKTEN BAGIMSIZ, T4-BORC'tan ONCE) -----------
    # 🔴 SIRA KASITLIDIR: T4-BORC'tan SONRA konsaydi kol PRODUKSIYONDA OLU
    # olurdu — varsayilan esik 0'dir, yani T4-BORC her acik kalemde once
    # ateslenir ve olcut kolu HIC kosmazdi ([[kapinin-menzili-cagri-yeridir]]).
    # Gerekce ayrica sirasal degil MANTIKSAL: olcutu olmayan bir borc SAYILABILIR
    # ama KAPATILAMAZ; once olcut yazilir, sonra borc kapatilir.
    olcutsuz = olcutsuz_kalemler(kalemler, mutant=olcut_mutant)
    sonuc["OLCUTSUZ"] = [k.get("kimlik") or "?" for k in olcutsuz]
    sonuc["OLCUTSUZ_SAYISI"] = len(olcutsuz)
    if olcutsuz and not muafiyet_yok:
        sonuc["RED"] = True
        sonuc["DURUM"] = "ACIK"
        sonuc["RED_SEBEBI"] = (
            "%s ev=%s acik_kalem=%d olcutsuz=%d (satirda makine-okunur `kabul:` "
            "alani YOK): %s"
            % (T4_OLCUTSUZ_JETON, ev, sayi, len(olcutsuz),
               ",".join(sonuc["OLCUTSUZ"])))
        return sonuc

    # Acik kalem sayisi > esik ise RED.
    # (>= degil; ">": esik=0 oldugunda 1 acik kalem RED uretir; 0 acik kalem
    # GECER uretir. Spec acik bir sayi vermedigi icin varsayilan 0.)
    if sayi > esik:
        sonuc["ESIK_ASILDI"] = True
        sonuc["RED"] = True
        sonuc["RED_SEBEBI"] = ("T4-BORC ev=%s acik_kalem=%d esik=%d (esik asildi)"
                              % (ev, sayi, esik))
        sonuc["DURUM"] = "ACIK"
        return sonuc

    # GECER — acik kalem yok ya da esik altinda.
    sonuc["DURUM"] = "KAPANDI"
    sonuc["GECER_MESAJI"] = ("T4-TEMIZ ev=%s acik_kalem=%d esik=%d (esik altinda; "
                             "parti gecer)" % (ev, sayi, esik))
    return sonuc


# ------------------------------------------------------------------------------
# MUTANT ALTYAPISI (--kendini-test)
# ------------------------------------------------------------------------------
def _gvd_yedekle(yol):
    yedek = yol + ".kendinitest-yedek"
    with open(yol, encoding="utf-8") as f, open(yedek, "w", encoding="utf-8") as g:
        g.write(f.read())
    return yedek


def _gvd_yedekten_geri(yol, yedek):
    with open(yedek, encoding="utf-8") as f, open(yol, "w", encoding="utf-8") as g:
        g.write(f.read())
    os.unlink(yedek)


def _sentetik_defter_yaz(defter_yol, acik_sayisi, durum_dagilimi=None,
                         olcut=True, kanit=None):
    """Sentetik bir acik-kalemler.md yaz. durum_dagilimi dict ise onu kullan;
    None ise acik_sayisi kadar ACIK satiri uret.

    olcut: True ise her satir makine-okunur `kabul:` alani tasir (K289 kolu
           tetiklenmez; M1..M4'un davranisi DEGISMEZ = regresyon 0).
           False ise satir olcutsuzdur (K289 kolunun fikstur uretimi).
    kanit: kanit kolonuna yazilacak metin. None ise olcut'e gore secilir.
           `olcut=False` + dolu `kanit` = M6'nin ayirt ettigi hal (kanit VAR,
           `kabul:` YOK).
    """
    if durum_dagilimi is None:
        durum_dagilimi = {"ACIK": acik_sayisi}
    if kanit is None:
        kanit = ("kabul: python3 tools/sentetik-kabul.py" if olcut else "—")
    satirlar = [
        "# AÇIK KALEM DEFTERİ (sentetik — T4 kendini-test)",
        "",
        "| id | tarih | kimden→kime | iş | durum | kapanış kanıtı |",
        "|---|---|---|---|---|---|",
    ]
    sayac = 0
    for durum, n in durum_dagilimi.items():
        for i in range(n):
            sayac += 1
            satirlar.append("| K%03d | 2026-08-19 | sentetik→%s | sentetik kalem %d | %s | %s |"
                            % (sayac, durum, sayac, durum, kanit))
    dizin = os.path.dirname(defter_yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin, exist_ok=True)
    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")


def kendini_test(repo_kok, esik, koku_root):
    """6 mutant + 1 kontrol + izolasyon. Her biri hedef kolunu AYRICA kanitlar.

    koku_root: --kendini-test'te tempfile.mkdtemp(); gercek defterlere
    DOKUNULMAZ.

    KABUL: MUTANT=6/6 KONTROL=1/1 — T4-BORC, T4-TEMIZ, T4-EV, T4-OLCULEMEDI,
    T4-OLCUTSUZ (M5 kol OLU + M6 kol GEVSEK) gecti ve kol olcutlu kalemde SUSTU.
    """
    adimlar = []

    # --- M1: acik kalem sayisi esikten BUYUK olsun -> T4-BORC RED -----------
    # 1 acik kalem, esik=0 -> esik asildi -> RED T4-BORC oneki.
    defter_m1 = os.path.join(koku_root, "KraL", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_m1, acik_sayisi=1, durum_dagilimi={"ACIK": 1})
    sonuc_m1 = parti_engeli_var_mi("KraL", esik=0, koku_root=koku_root)
    m1_reddetti = (
        sonuc_m1["RED"] is True
        and sonuc_m1["RED_SEBEBI"] is not None
        and sonuc_m1["RED_SEBEBI"].startswith(T4_BORC_JETON + " ")
        and sonuc_m1["ACIK_SAYISI"] == 1
        and sonuc_m1["ESIK_ASILDI"] is True
    )
    m1_mesaj = ("ev=KraL acik=1 esik=0 -> T4-BORC RED (esik asildi)")
    adimlar.append(("M1", T4_BORC_JETON, m1_reddetti, m1_mesaj, sonuc_m1))

    # --- M2: acik kalem sayisi esikten KUCUK olsun -> T4-TEMIZ GECER --------
    # 0 acik kalem, esik=5 -> esik asilmadi -> GECER T4-TEMIZ oneki.
    # Burada KRITIK: T4-BORC govdesi oldurulurse M2'de de RED gelebilir; ama
    # M2'de biz T4-TEMIZ onekini ariyoruz. Kol ayrimi: T4-TEMIZ onekini
    # gormezse M2 YASAMAZ (kirmizi kalir).
    defter_m2 = os.path.join(koku_root, "ArTisT", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_m2, acik_sayisi=0, durum_dagilimi={})
    sonuc_m2 = parti_engeli_var_mi("ArTisT", esik=5, koku_root=koku_root)
    m2_reddetti = (
        sonuc_m2["RED"] is False
        and sonuc_m2["GECER_MESAJI"] is not None
        and sonuc_m2["GECER_MESAJI"].startswith(T4_TEMIZ_JETON + " ")
        and sonuc_m2["ACIK_SAYISI"] == 0
        and sonuc_m2["ESIK_ASILDI"] is False
    )
    m2_mesaj = ("ev=ArTisT acik=0 esik=5 -> T4-TEMIZ GECER (esik altinda)")
    adimlar.append(("M2", T4_TEMIZ_JETON, m2_reddetti, m2_mesaj, sonuc_m2))

    # --- M3: T4-EV — baslatan EV'in defteri okunur; baska evin borcu --------
    # KARAR VERMEZ. KraL'in defteri bos olmali; ArTisT'in defteri dolu olmali
    # (10 ACIK kalem); parti ArTisT'te baslatilir -> ArTisT'in borcu sayilir
    # (10 > esik=0), RED. Eger T4-EV yanlis calisip KraL'in defterini okusa
    # (0 acik), GECER donerdi — bu M3'un YASAMAMASINA sebep olur (mutant
    # tarafindan hedef kol kanitlanamaz).
    defter_kral_m3 = os.path.join(koku_root, "KraL", ACIK_KALEM_DOSYA)
    defter_artist_m3 = os.path.join(koku_root, "ArTisT", ACIK_KALEM_DOSYA)
    # KraL temiz (0 acik)
    _sentetik_defter_yaz(defter_kral_m3, acik_sayisi=0, durum_dagilimi={})
    # ArTisT kirli (10 acik)
    _sentetik_defter_yaz(defter_artist_m3, acik_sayisi=10, durum_dagilimi={"ACIK": 10})
    sonuc_m3 = parti_engeli_var_mi("ArTisT", esik=0, koku_root=koku_root)
    m3_reddetti = (
        sonuc_m3["RED"] is True
        and sonuc_m3["ACIK_SAYISI"] == 10
        and sonuc_m3["DEFTER_YOLU"] == defter_artist_m3
        and sonuc_m3["RED_SEBEBI"] is not None
        and sonuc_m3["RED_SEBEBI"].startswith(T4_BORC_JETON + " ")
    )
    m3_mesaj = ("ev=ArTisT acik=10 esik=0 -> T4-BORC RED (T4-EV: parti baslatan EV=ArTisT, "
                "KraL bos olsa bile ArTisT'in borcu sayildi)")
    adimlar.append(("M3", T4_EV_JETON, m3_reddetti, m3_mesaj, sonuc_m3))

    # --- M4: defter OKUNAMAZ -> T4-OLCULEMEDI fail-closed RED ---------------
    # Sentetik kok altinda HocA'nin defteri YOK (yol olusturulmaz). Parti
    # HocA'da baslatilir -> defter okunamadi -> RED T4-OLCULEMEDI oneki.
    # Eger T4-OLCULEMEDI govdesi oldurulurse "borc yok" sayip GECER donerdi;
    # M4'te T4-OLCULEMEDI onekini arayan dogrulama YAKALAMAZ (mutant yasar).
    sonuc_m4 = parti_engeli_var_mi("HocA", esik=0, koku_root=koku_root)
    m4_reddetti = (
        sonuc_m4["RED"] is True
        and sonuc_m4["OLCULEMEDI"] is True
        and sonuc_m4["HATA"] is not None
        and sonuc_m4["HATA"].startswith(T4_OLCULEMEDI_JETON + " ")
    )
    m4_mesaj = ("ev=HocA defter=YOK -> T4-OLCULEMEDI fail-closed RED "
                "(borc yok SAYILMAZ)")
    adimlar.append(("M4", T4_OLCULEMEDI_JETON, m4_reddetti, m4_mesaj, sonuc_m4))

    # === K289 — T4-OLCUTSUZ KOLU ============================================
    # 🔴 HEDEF-KOL ATFI (K182): fikstur ESIGIN ALTINDA kurulur (1 acik kalem,
    # esik=5). Boylece T4-BORC ATESLENEMEZ ve kirmizinin TEK olasi sebebi
    # T4-OLCUTSUZ kolu olur. Mutant "kirmizi geldi" diye kanit sayilmaz:
    # kolu OLDURUNCE ayni fikstur GECER'e donmeli (asagida ayrica olculuyor).
    defter_m5 = os.path.join(koku_root, "TeKiN", ACIK_KALEM_DOSYA)

    # --- M5: kol OLDURULUR -> olcutsuz kalem GECER (kol OLU demektir) -------
    _sentetik_defter_yaz(defter_m5, acik_sayisi=1, durum_dagilimi={"ACIK": 1},
                         olcut=False)
    sonuc_m5 = parti_engeli_var_mi("TeKiN", esik=5, koku_root=koku_root)
    olu_m5 = parti_engeli_var_mi("TeKiN", esik=5, koku_root=koku_root,
                                 olcut_mutant="M5")
    m5_reddetti = (
        # (a) GERCEK kol: esik ALTINDA olmasina ragmen RED, ve oneki T4-OLCUTSUZ
        sonuc_m5["RED"] is True
        and sonuc_m5["ESIK_ASILDI"] is False          # T4-BORC ATESLENMEDI
        and sonuc_m5["ACIK_SAYISI"] == 1
        and sonuc_m5["OLCUTSUZ_SAYISI"] == 1
        and sonuc_m5["RED_SEBEBI"] is not None
        and sonuc_m5["RED_SEBEBI"].startswith(T4_OLCUTSUZ_JETON + " ")
        # (b) HEDEF KOL ATFI: kol oldurulunce AYNI fikstur GECER'e doner.
        #     Kirmizinin sebebi baska bir kol olsaydi bu adim RED kalirdi.
        and olu_m5["RED"] is False
        and olu_m5["OLCUTSUZ_SAYISI"] == 0
        and olu_m5["GECER_MESAJI"] is not None
        and olu_m5["GECER_MESAJI"].startswith(T4_TEMIZ_JETON + " ")
    )
    m5_mesaj = ("ev=TeKiN acik=1 esik=5 olcut=YOK -> T4-OLCUTSUZ RED; kol "
                "oldurulunce (M5) AYNI fikstur GECER -> kirmizinin sebebi BU kol")
    adimlar.append(("M5", T4_OLCUTSUZ_JETON, m5_reddetti, m5_mesaj, sonuc_m5))

    # --- M6: kol GEVSETILIR -> "kanit dolu" olcut sayilir -------------------
    # Fikstur: kanit kolonu DOLU ama `kabul:` YOK (defterdeki gercek kalip:
    # "kanama sessiz", "kismi: <sha>"). Gercek kol bunu OLCUTSUZ sayar; gevsek
    # kol (M6) "kanit dolu" diye GECIRIR. Yalniz M5 kosulsaydi bu korluk
    # GORUNMEZDI — M5'in fiksturunde kanit da bostu ([[ad-iki-rolde-mutanti-golgeler]]).
    defter_m6 = os.path.join(koku_root, "MaCiT", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_m6, acik_sayisi=1, durum_dagilimi={"ACIK": 1},
                         olcut=False, kanit="kanama sessiz; kismi: 55b291f")
    sonuc_m6 = parti_engeli_var_mi("MaCiT", esik=5, koku_root=koku_root)
    gevsek_m6 = parti_engeli_var_mi("MaCiT", esik=5, koku_root=koku_root,
                                    olcut_mutant="M6")
    m6_reddetti = (
        sonuc_m6["RED"] is True
        and sonuc_m6["ESIK_ASILDI"] is False          # T4-BORC ATESLENMEDI
        and sonuc_m6["OLCUTSUZ_SAYISI"] == 1
        and sonuc_m6["RED_SEBEBI"] is not None
        and sonuc_m6["RED_SEBEBI"].startswith(T4_OLCUTSUZ_JETON + " ")
        # HEDEF KOL ATFI: gevsetilince AYNI fikstur GECER'e doner.
        and gevsek_m6["RED"] is False
        and gevsek_m6["OLCUTSUZ_SAYISI"] == 0
    )
    m6_mesaj = ("ev=MaCiT acik=1 esik=5 kanit=DOLU ama `kabul:` YOK -> "
                "T4-OLCUTSUZ RED; kol gevsetilince (M6) GECER -> kol serbest "
                "metni degil `kabul:` ALANINI okuyor")
    adimlar.append(("M6", T4_OLCUTSUZ_JETON, m6_reddetti, m6_mesaj, sonuc_m6))

    # --- KONTROL K5: olcut VARSA kol SUSAR (kor kapi degil) -----------------
    # 🔴 Bu adim olmadan M5/M6 tautolojiye acik olurdu: "hep RED" diyen bos bir
    # kol da ikisini gecerdi. K5, olcutlu kalemde kolun SUSTUGUNU olcer.
    defter_k5 = os.path.join(koku_root, "TeKiN", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_k5, acik_sayisi=1, durum_dagilimi={"ACIK": 1},
                         olcut=True)
    sonuc_k5 = parti_engeli_var_mi("TeKiN", esik=5, koku_root=koku_root)
    k5_gecti = (
        sonuc_k5["RED"] is False
        and sonuc_k5["ACIK_SAYISI"] == 1
        and sonuc_k5["OLCUTSUZ_SAYISI"] == 0
        and sonuc_k5["GECER_MESAJI"] is not None
        and sonuc_k5["GECER_MESAJI"].startswith(T4_TEMIZ_JETON + " ")
    )

    # ---- ozet bas -------------------------------------------------------
    print("T4 PARTI BORC KAPISI — KENDINI-TEST")
    print("izolasyon koku (defterler): %s" % koku_root)
    print("esik: %d" % esik)
    print("")
    mutant_sayaci = 0
    for ad, jeton, gecti, mesaj, sonuc in adimlar:
        print("MUTANT %s -> hedef kol %s" % (ad, jeton))
        print("  mesaj: %s" % mesaj)
        print("  EV=%s ACIK=%d ESIK=%d RED=%s OLCULEMEDI=%s OLCUTSUZ=%d"
              % (sonuc["EV"], sonuc["ACIK_SAYISI"], sonuc["ESIK"],
                 sonuc["RED"], sonuc["OLCULEMEDI"],
                 sonuc.get("OLCUTSUZ_SAYISI", 0)))
        if sonuc.get("DEFTER_YOLU"):
            print("  DEFTER=%s" % sonuc["DEFTER_YOLU"])
        if sonuc["RED_SEBEBI"]:
            print("  RED_SEBEBI=%s" % sonuc["RED_SEBEBI"])
        if sonuc["GECER_MESAJI"]:
            print("  GECER=%s" % sonuc["GECER_MESAJI"])
        if sonuc["HATA"]:
            print("  HATA=%s" % sonuc["HATA"])
        if gecti:
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
            mutant_sayaci += 1
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        print("")

    # K289 kontrol vakasi — kol KOR degil (olcutlu kalemde SUSAR).
    print("KONTROL K5 -> %s" % T4_OLCUTSUZ_JETON)
    print("  mesaj: ev=TeKiN acik=1 esik=5 olcut=VAR -> kol SUSAR, T4-TEMIZ GECER")
    print("  EV=%s ACIK=%d OLCUTSUZ=%d RED=%s"
          % (sonuc_k5["EV"], sonuc_k5["ACIK_SAYISI"],
             sonuc_k5["OLCUTSUZ_SAYISI"], sonuc_k5["RED"]))
    print("  SONUÇ: %s" % ("YESIL (kol kor degil)" if k5_gecti
                           else "KIRMIZI (kol HEP RED — kor kapi)"))
    print("")

    print("MUTANT=%d/%d" % (mutant_sayaci, len(adimlar)))
    print("KONTROL=%d/1" % (1 if k5_gecti else 0))
    return 0 if (mutant_sayaci == len(adimlar) and k5_gecti) else 1


# ------------------------------------------------------------------------------
# CURUTME TESTI (--curutme-test)
# ------------------------------------------------------------------------------
# Spec §2: her kolun govdesi oldurulunce ilgili mutant SESSIZ kalmali —
# yani curutulmus govde beklendigi gibi CALISMAMALI ve dogrulama YAKALAMALI
# ("kirmizi gelmesi kanit DEGIL — K183b'de olculen desen"). Bu mod, gercek
# `parti_engeli_var_mi` cagrisini YAMALI (sarmalayici ile) ve 4 kol icin
# mutant davranisinin YAKALANDIGINI gosterir.
CURUTME_TURLERI = {
    "T4-BORC":        "sayi > esik -> False",
    "T4-TEMIZ":       "GECER_MESAJI -> None",
    "T4-EV":          "ev parametresini KraL'a sabitle",
    "T4-OLCULEMEDI":  "OLCULEMEDI -> False, RED -> False (okunamadi durumunda GECER)",
}


def _curutulmus_parti_engeli(alt_kol, ev, esik, koku_root=None):
    """parti_engeli_var_mi'yi sarmala; secilen alt kolun govdesini YAMA."""
    sonuc = parti_engeli_var_mi(ev, esik=esik, koku_root=koku_root)

    if alt_kol == "T4-BORC":
        # T4-BORC oldu: "sayi > esik" kararini devre disi birak. RED uretmez,
        # RED_SEBEBI T4-BORC oneki tasimaz.
        if sonuc["ACIK_SAYISI"] > sonuc["ESIK"]:
            sonuc["RED"] = False
            sonuc["RED_SEBEBI"] = None
            sonuc["ESIK_ASILDI"] = False
            sonuc["GECER_MESAJI"] = "T4-BORC YAMALI: esik asildi ama GECER donuldu"
            sonuc["DURUM"] = "KAPANDI"
    elif alt_kol == "T4-TEMIZ":
        # T4-TEMIZ oldu: GECER_MESAJI uretmez; boylece M2 "T4-TEMIZ " onekini
        # gormez ve YAKALAMAZ.
        if not sonuc["RED"]:
            sonuc["GECER_MESAJI"] = None
    elif alt_kol == "T4-EV":
        # T4-EV oldu: ev parametresini KraL'a sabitle (yani parti hangi EV'de
        # baslatilirsa baslatilsin, KraL'in defterine baksin). KraL bos ise
        # ACIK_SAYISI=0 doner; M3 bekledigini (10 acik) bulamaz ve YAKALAMAZ.
        return parti_engeli_var_mi("KraL", esik=esik, koku_root=koku_root)
    elif alt_kol == "T4-OLCULEMEDI":
        # T4-OLCULEMEDI oldu: okunamadi durumunda "borc yok" sayip GECER don.
        if sonuc.get("OLCULEMEDI") or sonuc.get("HATA"):
            sonuc["OLCULEMEDI"] = False
            sonuc["HATA"] = None
            sonuc["RED"] = False
            sonuc["DURUM"] = "KAPANDI"
            sonuc["GECER_MESAJI"] = "T4-OLCULEMEDI YAMALI: okunamadi ama GECER donuldu"
    return sonuc


def curutme_testi(repo_kok, esik, koku_root):
    """4 alt kol icin govde oldurme simulasyonu. Her mutant hedef kolu icin:
    - normal parti_engeli_var_mi beklenen davranisi URETIR (esik asildi/GECER)
    - curutulmus sarmalayici ayni davranisi URETEMEZ (kol ayrimi bozulur)
    Boylece M1-M4'un "mutant yasamaz" dogrulamasi curutulmus ortamda YAKALAMAZ
    ve "BEKLENDI YAKALANMADI" olarak rapor edilir; bu, kolun gercekten
    YAKALANDIGINI kanitlar (kirmizi gelmesi kanit DEGIL).

    Her mutant icin OZGUN sentetik defter senaryosu kurulur (paylasim yok);
    boylece bir onceki mutantin defter yazimi sonrakini etkilemez."""
    # 4 alt kol icin beklenen davranis (curutme ONCESI). Her biri icin
    # sentetik defter senaryosu kurulacak.
    senaryolar = [
        # (ad, jeton, ev, esik, ev_acik_sayisi_map, aciklama)
        ("M1", "T4-BORC",        "KraL",   0, {"KraL": 1},
         "esik=0, KraL 1 acik -> T4-BORC RED beklenir"),
        ("M2", "T4-TEMIZ",       "ArTisT", 5, {"ArTisT": 0},
         "esik=5, ArTisT 0 acik -> T4-TEMIZ GECER beklenir"),
        ("M3", "T4-EV",          "ArTisT", 0, {"KraL": 0, "ArTisT": 10},
         "esik=0, ArTisT 10 acik (KraL 0) -> T4-BORC RED (T4-EV: ArTisT)"),
        ("M4", "T4-OLCULEMEDI",  "HocA",   0, {"HocA": None},
         "esik=0, HocA defter yok -> T4-OLCULEMEDI fail-closed RED beklenir"),
    ]

    print("T4 PARTI BORC KAPISI — CURUTME TESTI (4 alt kol, govde yamasiz kanit)")
    print("izolasyon koku: %s" % koku_root)
    print("")
    curutme_sayaci = 0
    for ad, jeton, ev, esik_m, ev_acik_map, aciklama in senaryolar:
        # Bu mutant icin OZGUN sentetik defterleri yaz (paylasim yok).
        for e, n in ev_acik_map.items():
            if n is None:
                # Defter YOK: dizini bile yazma
                yol = os.path.join(koku_root, e, ACIK_KALEM_DOSYA)
                if os.path.isfile(yol):
                    os.unlink(yol)
                dizin = os.path.dirname(yol)
                if os.path.isdir(dizin):
                    shutil.rmtree(dizin, ignore_errors=True)
                continue
            yol = os.path.join(koku_root, e, ACIK_KALEM_DOSYA)
            _sentetik_defter_yaz(yol, acik_sayisi=n,
                                 durum_dagilimi={"ACIK": n} if n else {})

        # 1) Normal kosum — beklenen davranis URETILMELI.
        sonuc_normal = parti_engeli_var_mi(ev, esik=esik_m, koku_root=koku_root)
        # 2) Curutme — secilen kol yamanir; ayni girdi.
        sonuc_curuk = _curutulmus_parti_engeli(jeton, ev, esik=esik_m,
                                               koku_root=koku_root)

        # Beklenen vs curuk: normaldeki beklenti curukle saglanmiyor olmali.
        fark_var = (sonuc_normal["RED"] != sonuc_curuk["RED"]
                    or sonuc_normal["ACIK_SAYISI"] != sonuc_curuk["ACIK_SAYISI"]
                    or bool(sonuc_normal["RED_SEBEBI"]) != bool(sonuc_curuk["RED_SEBEBI"])
                    or bool(sonuc_normal["GECER_MESAJI"]) != bool(sonuc_curuk["GECER_MESAJI"])
                    or bool(sonuc_normal["HATA"]) != bool(sonuc_curuk["HATA"])
                    or sonuc_normal["OLCULEMEDI"] != sonuc_curuk["OLCULEMEDI"])

        print("CURUTME %s -> hedef kol %s" % (ad, jeton))
        print("  aciklama: %s" % aciklama)
        print("  normal : RED=%s OLCULEMEDI=%s ACIK=%d RED_SEBEBI=%s"
              % (sonuc_normal["RED"], sonuc_normal["OLCULEMEDI"],
                 sonuc_normal["ACIK_SAYISI"],
                 sonuc_normal["RED_SEBEBI"] or "-"))
        print("  curuk  : RED=%s OLCULEMEDI=%s ACIK=%d RED_SEBEBI=%s"
              % (sonuc_curuk["RED"], sonuc_curuk["OLCULEMEDI"],
                 sonuc_curuk["ACIK_SAYISI"],
                 sonuc_curuk["RED_SEBEBI"] or "-"))
        if fark_var:
            print("  SONUÇ: KOL FARKEDILDI (normal != curuk; yama algilanir)")
            curutme_sayaci += 1
        else:
            print("  SONUÇ: KOL FARKEDILMEDI (curutme etkisiz — TEHLIKELI)")
        print("")

    print("CURUTME=%d/4 (her biri: yama normalden farkli davranis uretiyor)"
          % curutme_sayaci)
    return 0 if curutme_sayaci == 4 else 1


# ------------------------------------------------------------------------------
# ANALIZ / KONTROL (default, yazmaz)
# ------------------------------------------------------------------------------
def kontrol(ev, esik):
    """Tek bir EV icin parti kararini bas. YAZMAZ. --kendini-test degil."""
    if ev not in EV_BILINEN:
        print("HATA: gecersiz EV: %r" % ev)
        print("bilinen EV'ler: %s" % ", ".join(sorted(EV_BILINEN)))
        return 1
    sonuc = parti_engeli_var_mi(ev, esik=esik)
    print("T4 PARTI BORC KAPISI — KONTROL (salt-okunur, YAZMAZ)")
    print("EV: %s" % sonuc["EV"])
    print("DEFTER: %s" % (sonuc["DEFTER_YOLU"] or "(yok)"))
    print("ACIK_KALEM: %d" % sonuc["ACIK_SAYISI"])
    print("OLCUTSUZ_KALEM: %d%s"
          % (sonuc.get("OLCUTSUZ_SAYISI", 0),
             (" -> " + ",".join(sonuc.get("OLCUTSUZ") or []))
             if sonuc.get("OLCUTSUZ") else ""))
    print("ESIK: %d" % sonuc["ESIK"])
    print("ESIK_ASILDI: %s" % sonuc["ESIK_ASILDI"])
    print("DURUM: %s" % sonuc["DURUM"])
    if sonuc["OLCULEMEDI"]:
        print("HATA: %s" % sonuc["HATA"])
        print("HUKUM: RED (T4-OLCULEMEDI fail-closed)")
        return 1
    if sonuc["RED"]:
        print("RED_SEBEBI: %s" % sonuc["RED_SEBEBI"])
        print("HUKUM: RED")
        return 1
    print("GECER_MESAJI: %s" % sonuc["GECER_MESAJI"])
    print("HUKUM: GECER")
    return 0


def rapor(esik):
    """Tum bilinen EV'ler icin acik kalem sayisi + esik + RED/GECER hukumu.
    Salt okuma. YAZMAZ."""
    print("T4 PARTI BORC KAPISI — RAPOR (salt-okunur, YAZMAZ)")
    print("esik: %d" % esik)
    print("")
    print("%-10s %-12s %-11s %-8s %-12s %s"
          % ("EV", "ACIK_KALEM", "OLCUTSUZ", "ESIK", "HUKUM", "DEFTER"))
    print("-" * 96)
    ozet = {"RED": 0, "GECER": 0, "OLCULEMEDI": 0}
    for ev in sorted(EV_BILINEN):
        sonuc = parti_engeli_var_mi(ev, esik=esik)
        if sonuc["OLCULEMEDI"]:
            huk = "OLCULEMEDI"
            ozet["OLCULEMEDI"] += 1
        elif sonuc["RED"]:
            huk = "RED"
            ozet["RED"] += 1
        else:
            huk = "GECER"
            ozet["GECER"] += 1
        print("%-10s %-12d %-11d %-8d %-12s %s"
              % (ev, sonuc["ACIK_SAYISI"], sonuc.get("OLCUTSUZ_SAYISI", 0),
                 sonuc["ESIK"], huk, sonuc["DEFTER_YOLU"] or "(yok)"))
    print("-" * 96)
    print("Ozet: RED=%d GECER=%d OLCULEMEDI=%d"
          % (ozet["RED"], ozet["GECER"], ozet["OLCULEMEDI"]))
    return 0


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ev", default=None,
                    help="Parti baslatan ev (default: KraL)")
    ap.add_argument("--esik", type=int, default=DEFAULT_ESIK,
                    help="Acik kalem esigi (default: %d). Ustunde -> RED." % DEFAULT_ESIK)
    ap.add_argument("--kendini-test", action="store_true",
                    help="6 mutant + 1 kontrolu izole kos (gercek defterlere "
                         "DOKUNMAZ)")
    ap.add_argument("--curutme-test", action="store_true",
                    help="4 alt kol govdesini yama ile oldur; farkin algilandigini kanitla")
    ap.add_argument("--rapor", action="store_true",
                    help="Tum EV'ler icin acik kalem sayisi + RED/GECER bas "
                         "(salt-okunur)")
    ap.add_argument("--defter-koku-root", default=None,
                    help="--kendini-test icin izole defter koku "
                         "(default: tempfile.mkdtemp()). Belirtilmezse gecici dizin.")
    args = ap.parse_args()

    repo_kok = _repo_kok()

    if args.kendini_test:
        koku = args.defter_koku_root or tempfile.mkdtemp(prefix="t4-kendinitest-")
        if not os.path.isdir(koku):
            try:
                os.makedirs(koku)
            except OSError as e:
                print("HATA: defter koku olusturulamadi: %r" % e)
                return 1
        # Izolasyon altinda EV alt dizinleri olustur (boylesine sentetik defterler
        # yazabilelim). M4'te HocA icin YAZMIYORUZ — bu, defter-yok senaryosunu
        # olusturur (T4-OLCULEMEDI kaniti).
        for ev in ("KraL", "MaCiT", "ArTisT", "TeKiN"):
            os.makedirs(os.path.join(koku, ev, "memory"), exist_ok=True)
        # HocA'yi kasten olusturma; M4 onu kullanir.
        rc = kendini_test(repo_kok, args.esik, koku)
        # Is bitince gecici koku temizle (Okan diski).
        if not args.defter_koku_root:
            shutil.rmtree(koku, ignore_errors=True)
        return rc

    if args.curutme_test:
        koku = args.defter_koku_root or tempfile.mkdtemp(prefix="t4-curutme-")
        if not os.path.isdir(koku):
            try:
                os.makedirs(koku)
            except OSError as e:
                print("HATA: defter koku olusturulamadi: %r" % e)
                return 1
        for ev in ("KraL", "ArTisT"):
            os.makedirs(os.path.join(koku, ev, "memory"), exist_ok=True)
        rc = curutme_testi(repo_kok, args.esik, koku)
        if not args.defter_koku_root:
            shutil.rmtree(koku, ignore_errors=True)
        return rc

    if args.rapor:
        return rapor(args.esik)

    return kontrol(args.ev or "KraL", args.esik)


if __name__ == "__main__":
    sys.exit(main())