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
                   🔴 K380/a (6 Eyl 2026, BaBa hukmu — ortak kutu 16:5x): bu
                   sayim OKAN-KAPISI kalemlerini SAYMAZ (yalniz ACIK/UCUSTA/🔧).
                   Kapatani Okan'in eli olan kalem evin isci hattini
                   KILITLEYEMEZ; baski `OKAN_KAPISI=N` satirinda ve 23:00 Okan
                   ozetinde DURUR. Mutant: `M-a` (izole kopya).
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
                   🔴 K380/b: bir tablo satirinin DURUM hucresi kanonik bes
                   degerin (ACIK/UCUSTA/OKAN-KAPISI/KAPANDI/🔧) disindaysa satir
                   ARTIK SESSIZCE ATLANMAZ — `T4-OLCULEMEDI durum gecersiz
                   <kimlik>=<metin>` ile RED. Olculen ariza (FaR F08, 6 Eyl):
                   hucre `ACIK (Okan kapisi KALKTI)` yaziyordu; iki kanonik
                   kumeye de girmedigi icin parser satiri ATLIYORDU ve defter
                   borcu ilan ederken kapi TEMIZ goruyordu (yanlis-yesil).
                   Mutant: `M-b` (izole kopya).

Isletim modlari:
  default (kontrol): gercek EV'in defterini okur, esikle karsilastirir, RED/GECER.
                     Tek bir EV ile calisir (--ev). YAZMAZ.
  --kendini-test    : 8 mutant + 1 kontrol + izolasyon (tempfile.mkdtemp).
                      M1..M6 fikstur/parametre mutantlari; K380'in M-a/M-b'si
                      kaynagin IZOLE KOPYASINA yama uygular (benzersiz ad +
                      `dont_write_bytecode`), CANLI govdeye DEGIL.
                      Gercek deftere DOKUNMAZ; gercek ev yoluna silme YOK.
  --rapor           : gercek defterler uzerinde YAZMADAN; her ev icin acik kalem
                      sayisi + esik + RED/GECER hukumu basar. Salt okuma.
  --ev-haritasi-kur : KURTARMA (elle kosulur, RUNTIME FALLBACK DEGIL).
                      `~/.claude/cron/evler.json` YOKSA `tools/evler-tohum.json`
                      dan uretir; VARSA **EZMEZ** (`ZATEN VAR`, rc=0). Her
                      fail-closed RED metni bu komutu ADIYLA basar — RED cikmaz
                      sokak degildir.

KABUL (calistirilabilir):
  python3 tools/parti-borc-kapisi.py --kendini-test
    -> rc=0, MUTANT=8/8 KONTROL=1/1, bes kol adi ciktida GECER.
       M5/M6 hedef-kol atfi ESIK ALTINDA olculur (T4-BORC atesleyemez), ve
       kol OLDURULUNCE/GEVSETILINCE ayni fikstur GECER'e doner — "kirmizi
       geldi" tek basina kanit sayilmaz ([[ad-iki-rolde-mutanti-golgeler]]).

  python3 tools/parti-borc-kapisi.py --rapor
    -> her evin acik kalem sayisi + esik + RED/GECER.

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ (bu kapinin isi degil).
  - --kendini-test gercek defterlere DOKUNMAZ; tempfile.mkdtemp altinda kosar.
  - esik burada sabit; ev->dizin eslemesi REPO DISINDA tek kaynaktir
    (`~/.claude/cron/evler.json`, K361) ve buradan YUKLENIR — ikinci kopya
    YASAK. Yukleyici fail-closed'dir: yok/bozuk/bos -> `EV_DIZIN is None`
    (bos dict DEGIL) ve her kol `T4-OLCULEMEDI` sinifindan RED verir.
"""
import argparse
import datetime
import json
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
#
# 🔴 K380 (6 Eyl 2026, BaBa hukmu — ortak kutu 16:5x) — IKI AYRI KUME:
#   ACIK_DURUMLAR : PARSER'in sozlesmesi. DEGISMEDI ve DEGISMEZ. Bu kumeyi
#                   `devir-kapisi.py`, `korgoz_olcum.py`, `korgoz_kabul.py` ve
#                   `parti-kapisi.py` OKUR; daraltmak o dort okuyucunun
#                   olcumunu sessizce oynatirdi ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
#   BORC_DURUMLARI: T4-BORC KOLUNUN sayimi. OKAN-KAPISI **BORC DEGILDIR** —
#                   kapatani Okan'in eli olan bir kalem evin isci hattini
#                   KILITLEYEMEZ (olculen vaka: FaR, `T4-BORC ev=FaR
#                   acik_kalem=5 esik=0`, 5 kalemin 3'u OKAN-KAPISI).
#                   Baski KALKMAZ: sayi ayri `OKAN_KAPISI=N` satirinda basilir
#                   ve 23:00 Okan ozetine gider.
OKAN_KAPISI_DURUMU = "OKAN-KAPISI"
BORC_DURUMLARI = frozenset({"ACIK", "UCUSTA", "🔧"})
ACIK_DURUMLAR = BORC_DURUMLARI | frozenset({OKAN_KAPISI_DURUMU})

# 🔴 K380 (b) — KANONIK BES DEGER. Durum hucresi bu besinden BIRI DEGILSE satir
# ATLANMAZ: fail-closed RED (`T4-OLCULEMEDI durum gecersiz ...`).
# OLCULEN ARIZA (FaR F08, 6 Eyl): hucre `ACIK (Okan kapisi KALKTI)` yaziyordu;
# `durum in ACIK_DURUMLAR` tutmadi, `durum in KAPANDI` da tutmadi -> satir
# SESSIZCE ATLANDI ve kalem "yok" sayildi. Bu, yanlis-yesil sinifidir: defter
# borcu ilan ediyor, kapi gormuyor. Fail-closed RED evi defteri DUZELTMEYE
# zorlar ([[yeni-hal-cozucunun-varsayilan-kovasina-duser]]).
KAPALI_DURUM = "KAPANDI"
KANONIK_DURUMLAR = ACIK_DURUMLAR | frozenset({KAPALI_DURUM})

# ==============================================================================
# 🔴 K361 (2 Eyl 2026, Okan emri / BaBa) — EV -> DIZIN TABLOSU REPO DISINDA
# ==============================================================================
# OLCULEN ARIZA (iki ayri kusur, ikisi de yapisal):
#   (1) Tablo BU DOSYADA sabitti. Sonucu: **yeni bir ev acmak PRUVO kodu
#       degistirmeyi gerektiriyordu.** PRUVO-disi yeni is Faralya (FaR,
#       `/Users/okan/dev/faralya`) ayni `isci.sh` hattini paylastigi icin,
#       hattin ev listesine girebilmek adina PRUVO reposunda **commit'siz bir
#       satir** birakti (`git status` -> `M tools/parti-borc-kapisi.py`) ve
#       MaCiT `git add -A` yapsa urun partisine karisacakti.
#   (2) Depo ZATEN IKI TABLOLUYDU: `tools/sahiplik-kapisi.py:107` icinde elle
#       yazilmis ikinci bir kume vardi ve icinde `FaR` YOKTU — sessizce
#       ayrismisti ([[ikiz-tanim-sessiz-ayrisma]]). O kume SILINDI; artik bu
#       yukleyiciden TURETILIR.
#
# TEK KAYNAK: `~/.claude/cron/evler.json` (duz eslesme; `_` ile baslayan
# anahtarlar NOT'tur, ev sayilmaz). Gerekce yorumlari — JSON yorum tasimadigi
# icin — yanindaki `evler-NOT.md`'de BIREBIR durur (kayipsizlik
# `tools/ev-haritasi-kapisi-test.py::NOT_KAYIPSIZ` kolunda olculur).
#
# 🔴 FAIL-CLOSED, ISIN EMNIYET CEKIRDEGI: dosya YOK / bozuk / gecerli-ama-BOS
# ise tablo **BOS SAYILMAZ**. Bos tablo "hicbir evde acik kalem yok" demeye
# gelir ve kapiyi SESSIZCE ACAR ([[yeni-hal-cozucunun-varsayilan-kovasina-duser]]).
# Bu uc halde `EV_DIZIN` **None**'dir (bos dict DEGIL) ve her okuyucu
# `T4-OLCULEMEDI` sinifindan sifir-disi rc ile RED verir. Bilinmeyen depo koku
# HALA cozulemez (mevcut fail-closed davranis AYNEN korundu).
#
# 🔴 UCUNCU YOL (mimar hukmu, 2 Eyl — FaR'in "dosya yoksa gomulu tabloya DUS"
# onerisi REDDEDILDI, ama cikmaz sokak da birakilmadi):
#   (a) CALISMA ZAMANINDA SESSIZ DUSUS YOK — yukaridaki fail-closed AYNEN.
#       FaR'in onerisi su sinifi uretirdi: biri `evler.json`'a yazar, TEK
#       KARAKTER bozar, arac SESSIZCE tohuma duser -> o kisinin degisikligi
#       HIC ETKI ETMEZ ve kapi YESIL yanar (yama INERT).
#   (b) RED CIKMAZ SOKAK DEGIL — her RED metni KURTARAN TAM KOMUTU basar.
#   (c) Gomulu tablo TOHUM olarak yasar (`tools/evler-tohum.json`), RUNTIME
#       FALLBACK olarak DEGIL: yalniz `--ev-haritasi-kur` onu okur ve config
#       YOKSA uretir; VARSA EZMEZ (`ZATEN VAR`, rc=0).
#   Iki yolun AYRISTIGINI `ev-haritasi-kapisi-test.py::ME4` mutanti olcer:
#   tohumu runtime yukleyicisine baglayan mutant, "config yokken RED" iddiasini
#   OLDURMELIDIR.
# 🔴 TOHUM BIR `.py` TABLOSU DEGILDIR (veri dosyasidir): ev listesi hicbir
# Python kaynaginda tablo olarak durmaz — K361 kabul olcutu 3 boyle korunur.
EVLER_JSON_VARSAYILAN = "/Users/okan/.claude/cron/evler.json"
# Ortam degiskeni YALNIZ hermetik bataryalar icindir (uretimde verilmez).
EVLER_JSON_ORTAM = "PRUVO_EVLER_JSON"
TOHUM_DOSYA_ADI = "evler-tohum.json"
KURTARMA_BAYRAGI = "--ev-haritasi-kur"

# Ev adi: bos olamaz, `_` ile baslayamaz (o anahtarlar NOT'tur).
_EV_ADI_RE = re.compile(r"^[^_\W][\w.-]*$", re.UNICODE)


class EvHaritasiOlculemedi(RuntimeError):
    """Ev haritasi OKUNAMADI. Fail-closed: cagiran BOS TABLO SAYAMAZ."""


def evler_json_yolu():
    """Tek kaynagin yolu. Ortam degiskeni yalniz hermetik batarya icindir."""
    return os.environ.get(EVLER_JSON_ORTAM) or EVLER_JSON_VARSAYILAN


def tohum_yolu():
    """Tohum veri dosyasi (`tools/evler-tohum.json`) — RUNTIME'da OKUNMAZ."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        TOHUM_DOSYA_ADI)


def kurtarma_komutu():
    """RED'i cikmaz sokak olmaktan cikaran TAM KOMUT (fikstur bunu ARAR).

    Betigin KENDI mutlak yolunu kullanir: kopyada/worktree'de de KOSULABILIR
    bir komut basar, kanonik ama yanlis bir yol DEGIL.
    """
    return "python3 %s %s" % (os.path.abspath(__file__), KURTARMA_BAYRAGI)


def _olculemedi(mesaj):
    """🔴 RED CIKMAZ SOKAK DEGIL: her hata metni KURTARAN KOMUTU tasir.

    Metin makinece aranabilir olsun diye jeton SABIT: `KURTARMA:`. Fikstur
    "hata verdi" ile yetinmez, TAM KOMUTUN basildigini iddia eder.
    """
    return EvHaritasiOlculemedi("%s | KURTARMA: %s" % (mesaj, kurtarma_komutu()))


def ev_haritasi_yukle(yol=None):
    """`evler.json`'u okur ve {EV: dizin} doner.

    🔴 ASLA bos sozluk DONMEZ: yok / bozuk / bos / sema disi hallerin HEPSI
    `EvHaritasiOlculemedi` FIRLATIR. Hata metni aranan YOLU, sebebi ve
    KURTARMA KOMUTUNU tasir (fail-loud) — "OLCULEMEDI" demek yetmez.
    🔴 TOHUMA DUSMEZ: tohum yalniz `--ev-haritasi-kur` kolunda okunur.
    """
    yol = yol or evler_json_yolu()
    try:
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
    except OSError as e:
        raise _olculemedi(
            "EV_HARITASI okunamadi (yol=%s): %s: %s" % (yol, type(e).__name__, e))
    try:
        veri = json.loads(ham)
    except ValueError as e:
        raise _olculemedi(
            "EV_HARITASI BOZUK JSON (yol=%s): %s: %s" % (yol, type(e).__name__, e))
    if not isinstance(veri, dict):
        raise _olculemedi(
            "EV_HARITASI sema disi (yol=%s): kok nesne degil, %s"
            % (yol, type(veri).__name__))
    harita = {}
    for anahtar, deger in veri.items():
        if not isinstance(anahtar, str) or anahtar.startswith("_"):
            continue                      # `_` onekli anahtar = NOT, ev DEGIL
        if not _EV_ADI_RE.match(anahtar):
            raise _olculemedi(
                "EV_HARITASI sema disi (yol=%s): gecersiz ev adi %r" % (yol, anahtar))
        if not isinstance(deger, str) or not deger.strip():
            raise _olculemedi(
                "EV_HARITASI sema disi (yol=%s): %s icin dizin bos/dizge degil (%r)"
                % (yol, anahtar, deger))
        if not deger.startswith("/"):
            raise _olculemedi(
                "EV_HARITASI sema disi (yol=%s): %s icin dizin MUTLAK degil (%r)"
                % (yol, anahtar, deger))
        harita[anahtar] = deger.rstrip("/")
    if not harita:
        # 🔴 EN ONEMLI KOL: gecerli JSON ama SIFIR ev. "Ev yok" != "borc yok".
        raise _olculemedi(
            "EV_HARITASI BOS (yol=%s): 0 ev — bos tablo GECERLI SAYILMAZ "
            "(bos tablo kapiyi sessizce acar)" % yol)
    return harita


def _harita_baglayici(yol=None):
    """(harita|None, hata|None) — modul duzeyindeki isimleri baglar."""
    try:
        return ev_haritasi_yukle(yol), None
    except EvHaritasiOlculemedi as e:
        return None, str(e)


def ev_haritasi_tazele(yol=None):
    """Modul duzeyindeki EV_DIZIN/EV_BILINEN'i YENIDEN baglar.

    Okuyucularin hepsi bu isimleri CAGRI ANINDA okur; boylece hermetik
    bataryalar canli `evler.json`'a HIC dokunmadan kosabilir.
    Return: (EV_DIZIN|None, EV_HARITASI_HATA|None).
    """
    global EV_DIZIN, EV_BILINEN, EV_HARITASI_HATA
    EV_DIZIN, EV_HARITASI_HATA = _harita_baglayici(yol)
    EV_BILINEN = frozenset(EV_DIZIN) if EV_DIZIN else None
    return EV_DIZIN, EV_HARITASI_HATA


def ev_haritasi_kur(hedef=None, tohum=None):
    """🔴 KURTARMA KOLU — tohumdan `evler.json` URETIR. RUNTIME'da CAGRILMAZ.

    Sozlesme (mimar hukmu, 2 Eyl):
      * hedef VARSA: **EZMEZ** -> `ZATEN VAR`, rc=0. Ezmek, canli tabloya
        sonradan eklenen evleri (or. FaR'in satiri) YOK EDERDI.
      * hedef YOKSA: tohumu DOGRULAYIP yazar -> `YAZILDI`, rc=0.
      * tohum okunamiyorsa: rc=2 (`TOHUM_OLCULEMEDI`) — bos dosya URETILMEZ.
    Return: (rc, [cikti satirlari]).
    """
    hedef = hedef or evler_json_yolu()
    tohum = tohum or tohum_yolu()
    cikti = ["EV HARITASI KUR — tohumdan tek kaynagi uretir (RUNTIME FALLBACK DEGIL)",
             "TOHUM : %s" % tohum,
             "HEDEF : %s" % hedef]
    if os.path.exists(hedef):
        cikti.append("HUKUM : ZATEN VAR — UZERINE YAZILMADI (mevcut tabloya "
                     "sonradan eklenen evler korunur)")
        return 0, cikti
    try:
        harita = ev_haritasi_yukle(tohum)
    except EvHaritasiOlculemedi as e:
        cikti.append("HATA  : TOHUM_OLCULEMEDI %s" % e)
        cikti.append("HUKUM : RED — bos/bozuk tohumdan config URETILMEZ")
        return 2, cikti
    dizin = os.path.dirname(os.path.abspath(hedef))
    try:
        if dizin and not os.path.isdir(dizin):
            os.makedirs(dizin, exist_ok=True)
        with open(hedef, "w", encoding="utf-8") as f:
            json.dump(harita, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    except OSError as e:
        cikti.append("HATA  : YAZILAMADI %s: %s" % (type(e).__name__, e))
        return 2, cikti
    cikti.append("HUKUM : YAZILDI — %d ev: %s"
                 % (len(harita), ", ".join(sorted(harita))))
    cikti.append("NOT   : gerekce metinleri /Users/okan/.claude/cron/evler-NOT.md")
    return 0, cikti


def fikstur_haritasi_yaz(yol, harita):
    """HERMETIK BATARYA KOLU — uretimde CAGRILMAZ.

    Verilen {EV: dizin} haritasini `yol`a yazar, `PRUVO_EVLER_JSON`'u ona
    isaretler (alt sureclere de miras kalir) ve modul duzeyindeki tabloyu
    yeniden baglar. Boylece batarya CANLI `evler.json`'a HIC dokunmaz —
    kosucuda (CI) o dosya YOKTUR ([[patha-sorulan-ikili-cron-da-yok]]).
    """
    kok = os.path.dirname(os.path.abspath(yol))
    if kok and not os.path.isdir(kok):
        os.makedirs(kok, exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(dict(harita), f, ensure_ascii=False, indent=2)
    os.environ[EVLER_JSON_ORTAM] = yol
    ev_haritasi_tazele(yol)
    return yol


def fikstur_haritasi_kur(koku, evler):
    """Fikstur dizinleri KOKUN ALTINDA: canli yol literali (`-Users-okan-dev-*`)
    TASIMAZ. `fikstur_haritasi_yaz`in kisayolu."""
    return fikstur_haritasi_yaz(os.path.join(koku, "evler.json"),
                                {ev: os.path.join(koku, ev) for ev in evler})


# HERMETIK BATARYA fikstur EV ADLARI — canli tablonun kopyasi DEGIL, yalnizca
# izole kok altinda kullanilan sentetik adlardir (yol literali TASIMAZ).
# Kardes bataryalar (parti-kapisi / devir-kapisi / chip-duzeni) ayni demeti
# BURADAN okur; ikinci liste YAZILMAZ.
FIKSTUR_EVLERI = ("KraL", "MaCiT", "ArTisT", "HocA", "TeKiN", "BaBa", "ORTAK")

ACIK_KALEM_DOSYA = "memory/acik-kalemler.md"

# Modul duzeyi baglama — IMPORT ASLA COKMEZ (okuyucular kendi kovalarinda
# hukum verebilsin diye), fakat hata halinde EV_DIZIN **None**'dir: bos dict
# DEGIL. Bos dict fail-OPEN olurdu.
EV_DIZIN, EV_HARITASI_HATA = _harita_baglayici()
EV_BILINEN = frozenset(EV_DIZIN) if EV_DIZIN else None

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

# 🔴 K380 (b) — gecersiz durum dokumu ekrana SIGMALI. Olculdu: KraL defterinde
# gomulu `|` tasiyan bir `is` hucresi kolonlari kaydiriyor ve `kolonlar[5]`
# 1.700 baytlik bir metin oluyor. Dokum kirpilmazsa RED metni terminali yutar.
GECERSIZ_DOKUM_TAVANI = 6      # en fazla kac satir adiyla basilir
GECERSIZ_METIN_TAVANI = 60     # her hucre metninin bayt/karakter tavani


def _durum_kirp(metin):
    """Gecersiz durum hucresini tek satira ve tavana kirp (RED metni icin)."""
    tek = " ".join((metin or "").split())
    if len(tek) > GECERSIZ_METIN_TAVANI:
        tek = tek[:GECERSIZ_METIN_TAVANI] + "…"
    return "%r" % tek

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

    🔴 K361: harita OLCULEMEDIYSE (EV_BILINEN is None) `EvHaritasiOlculemedi`
    FIRLATILIR — "gecersiz EV" ile KARISTIRILMAZ, ve BOS KUME sayilmaz.
    """
    if EV_BILINEN is None:
        raise EvHaritasiOlculemedi(EV_HARITASI_HATA or "EV_HARITASI OLCULEMEDI")
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

# 🔴 K382 (c) — KALEM SATIRI SEKLI (TEK KAYNAK).
# `TabloSatir` satirin `|` ile BITMESINI de sart kosar. Bir kalem satirinin
# sonundaki `|` unutulursa satir `TabloSatir`a UYMAZ ve dongunun ILK satirinda
# `continue` ile SESSIZCE duser: ne sayilir, ne gecersiz kovasina girer, ne de
# RED metninde adi gecer. OLCULDU (6 Eyl, 8 ev): KraL/ORTAK defterinde 2 satir
# (K89 L107, K91 L109) tam olarak boyle kayboluyordu — ikisi de ACIK/🔧.
# Bu kalip "kalem satiri OLMAYA CALISIYOR" seklini yakalar; boyle bir satir
# `TabloSatir`a uymuyorsa ARTIK SESSIZ DUSMEZ, fail-closed RED'e gider.
KalemSatiriSekli = re.compile(r"^\s*\|\s*(?P<kimlik>[A-Za-z][A-Za-z0-9_.\-]*)\s*\|")

# Kalem KIMLIGI kanonik kalibi (TEK KAYNAK). Ciplak okuyucular kendi
# `^K\d+$` kaliplarini TUTMAZ: o dar kalip `K339-EK` · `K329-EK` ·
# `K351-31AGU` · `K320b` gibi kimlikleri GORMEZ ve capraz kontrolu sessizce
# ayristirir ([[ikiz-tanim-sessiz-ayrisma]]).
KalemKimligi = re.compile(r"^K\d+[A-Za-z]*(?:-[A-Za-z0-9]+)*$")

# 🔴 K380 (b) TUZAGI — AYRAC SATIRI. Markdown tablo ayraci `|---|---|...|---|`
# split sonrasi 8 parca verir (>=7), yani `len(kolonlar) < 7` elemesinden
# GECER ve `kolonlar[5]` = `"---"` olur. Kanonik-disi durum kolu bu satiri
# GORSEYDI her ev defteri ANINDA kirmizi yanardi — kapinin kendi ayracina
# takilmasi ([[kurucu-kendi-kapisina-takilir]]). Ayrac ONCE elenir; `---`,
# `:--`, `--:`, `:-:` ve bosluk varyantlari ayni kova.
AyracHucre = re.compile(r"^[\s:\-]+$")

# ==============================================================================
# 🔴 K382 (6 Eyl 2026) — KACIS KORLUGU. KANONIK HUCRE BOLUCU (TEK KAYNAK).
# ==============================================================================
# OLCULEN ARIZA (canli KraL defteri, iddia degil — `--kendini-test` disi olcum):
# markdown'in KANONIK pipe kacisi `\|` bir hucrenin ICINDE gecerli icerittir ve
# tarayicida DOGRU render olur. Ham `satir.split("|")` bu kacisi TANIMAZ:
#
#   L41  K371   ham 9 kolon  -> ham[5]='ege: test KOSULAMADI…'   (gercek: 🔧)
#   L126 K313   ham 15 kolon -> ham[5]='select((.gorseller//[])\\' (gercek: ACIK)
#   L144 K339   ham 10 kolon -> ham[5]='\\'                       (gercek: ACIK)
#
# Yani DEFTER DOGRU, OKUYUCU YANLIS. Bu uc satir aylardir HIC okunmadi: durum
# hucresi kanonik olmadigi icin ya `GECERSIZ_DURUM` kovasina dusuyor (fail-closed
# RED, hukum uretilemiyor) ya da kaymadan dogan BOS hucre `if not durum: continue`
# ile SESSIZCE atlaniyordu.
#
# 🔴 NEDEN TEK YARDIMCI, NEDEN HER CAGRI YERINDE ELLE DEGIL: bu tabloyu okuyan
# ON BIR cagri yeri var (kapinin kendisi + devir + korgoz uc kol + kral-sabah +
# CANLI `nobet-kapi.py`'nin parser'i VE IKI YAZMA yolu). Kacis cozumunu her
# yerde tekrar yazmak IKIZ TANIM uretir ve ikizler DAIMA gevsek yone ayrisir
# ([[ikiz-tanim-sessiz-ayrisma]]). Cozum TEK yardimcidir; okuyucular buraya
# sorar, ikinci bir yuklem KURMAZ.
#
# 🔴 GERI UYUMLULUK (regresyon 0): kacissiz bir satirda `hucrelere_bol` ciktisi
# `satir.split("|")` ile BIREBIR AYNIDIR (ayni uzunluk, ayni indeksler, bas/son
# bos eleman korunur). Bu yuzden mevcut `kolonlar[1]/[4]/[5]/[6]` indeksleri ve
# `len(kolonlar) < 7` elemesi DEGISMEDEN calisir.
#
# 🔴 KURAL DAR TUTULDU: yalnizca `|` ONUNDEKI ters bolu kacistir. Genel ters-bolu
# kacisi (`\\`) UYGULANMAZ — canli defterde `\\|` gecisi OLCULDU: 0. Genel kacis
# eklemek mevcut hucre metinlerini sessizce degistirirdi.
KacissizAyirici = re.compile(r"(?<!\\)\|")


def hucrelere_bol(satir):
    """Markdown tablo satirini hucrelere bolar; `\\|` hucre ICERIGIDIR.

    `satir.split("|")` yerine BUNU cagir. Doner: hucre listesi — bas ve son
    eleman bostur (ham split ile ayni sozlesme). Kacis COZULUR: hucre metnindeki
    `\\|` gercek `|` karakterine doner, boylece hucre icerigi tarayicida
    gorunen metinle AYNI olur.

    Ters islem: `hucreleri_birlestir` (YAZMA yolu icin — kacis GERI konur).
    """
    return [h.replace("\\|", "|") for h in KacissizAyirici.split(satir)]


def hucreleri_birlestir(kolonlar):
    """`hucrelere_bol`un TERSI: hucreleri `|`-ayrilmis satira geri cevirir.

    🔴 YAZMA YOLLARI BUNU KULLANMAK ZORUNDA: `"|".join(...)` ile birlestirmek,
    kacisi COZULMUS bir hucredeki `|` karakterini AYIRICI'ya cevirir ve satiri
    bir sonraki okumada KALICI olarak parcalar (sessiz defter bozulmasi).
    Hucre icindeki her `|` yeniden `\\|` olarak kacirilir; kacissiz bir satir
    bol->birlestir turunda BAYT BAYT AYNI kalir.
    """
    return "|".join(h.replace("|", "\\|") for h in kolonlar)


def _ayrac_satiri_mi(kolonlar):
    """Markdown tablo AYRAC satiri mi? (tum govde hucreleri yalniz -,:,bosluk)

    kolonlar: `hucrelere_bol(satir)` ciktisi — bas ve son eleman bostur.
    Govde BOSSA False doner (bos satir ayrac degildir).
    """
    govde = kolonlar[1:-1] if len(kolonlar) >= 2 else []
    if not govde:
        return False
    return all(AyracHucre.match(h or "") for h in govde)


def defter_dosyasi_var_mi(defter_yolu):
    """Defter DOSYASI fiziksel olarak var mi?

    🔴 K229 — UCUNCU KOVA'nin TEK KAYNAGI. `acik_kalem_listesi`nin ILK kapisi
    BU fonksiyondur; cagiran taraf (N2B parti kapisi) "defter dosyasi YOK" ile
    "defter OKUNAMADI"yi ayirt ederken ikinci bir yuklem KURMAZ, buraya sorar.
    Ikinci bir `os.path.isfile` cagrisi yazilirsa iki yuklem SESSIZCE ayrisir
    ([[ayni-alan-iki-hukum-biri-sessiz]]).
    """
    return bool(defter_yolu) and os.path.isfile(defter_yolu)


def acik_kalem_listesi(defter_yolu, *, gecersiz_sink=None):
    """Bir acik-kalemler.md dosyasindaki ACIK kalemleri DOKUMLU doner.

    🔴 TEK PARSER (19 Agu 2026, N2): `acik_kalem_sayisi` bu fonksiyondan
    TURER. Ikinci bir tablo okuyucu YAZILMAZ — N2'nin parti kapisi (yeni is
    basvurusunda kalem KIMLIGINI ve `kabul:` komutunu ekrana basmak zorunda)
    ayni satirlari buradan alir ([[ikiz-tanim-sessiz-ayrisma]]).

    Return: (kalemler, okundu_mu_bool, hata_mesaji_str_or_None)
      kalemler = [{"kimlik", "durum", "is", "kanit", "satir_no"}, ...]
    YOKSA / IO hatasi / format bozuk -> ([], False, hata). "borc yok" SAYILMAZ;
    fail-closed: cagri yeri T4-OLCULEMEDI ile RED verir.

    gecersiz_sink: (K380 b) VERILIRSE, durum hucresi KANONIK_DURUMLAR disinda
      kalan her satir buraya `{"kimlik","durum","satir_no"}` olarak EKLENIR.
      🔴 NEDEN LISTE PARAMETRESI, NEDEN 4. DONUS DEGERI DEGIL: bu fonksiyon
      TEK PARSER'dir ve uc-demet sozlesmesi 6 cagri yerinde acilir
      (`parti-kapisi.py:813`, `devir-kapisi.py:254/508/517/622`,
      `korgoz_olcum.py:243`, `korgoz_kabul.py:309/338`). Demeti buyutmek o
      okuyuculari kirardi; ikinci bir tablo okuyucu yazmak ise doktrin geregi
      YASAK ([[ikiz-tanim-sessiz-ayrisma]]). Sink VERILMEZSE davranis BIREBIR
      eskisi gibidir (regresyon 0).
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
            # 🔴 K382 (c): kalem satiri SEKLINDE olup tabloya UYMAYAN satir
            # SESSIZCE DUSMEZ. (Sondaki `|` unutulmus satir bu koldan gecer.)
            m_sekil = KalemSatiriSekli.match(satir)
            if m_sekil and gecersiz_sink is not None:
                gecersiz_sink.append({
                    "kimlik": m_sekil.group("kimlik"),
                    "durum": "<SATIR BICIMI BOZUK — satir `|` ile BITMIYOR>",
                    "satir_no": satir_no,
                })
            continue
        # 🔴 K382: KANONIK bolucu. Ham `satir.split("|")` markdown'in `\|`
        # kacisini tanimaz ve kolonlari KAYDIRIR (canli defterde 3 satir).
        kolonlar = [k.strip() for k in hucrelere_bol(satir)]
        # Markdown tablosunda: "" | col1 | col2 | ... | colN | ""
        # Yani split sonrasi: ['', col1, col2, ..., colN, '']
        if len(kolonlar) < 7:
            continue  # baslik (5 kolon) ya da ayrac (---|---) — gec
        # 🔴 K380 (b): AYRAC satiri EN ONCE elenir — `tablo_basladi`ya da
        # DOKUNMADAN. Ayrac 7+ kolon uretir ve `kolonlar[5]` = "---" olur;
        # kanonik-disi kolu bunu gorseydi HER defter kirmizi yanardi.
        if _ayrac_satiri_mi(kolonlar):
            continue
        # 5. sutun (1-indeksli) = kolonlar[5]; 0-indeksli = 5
        durum = kolonlar[5].strip()
        # 🔴 K382 (b) — BOS DURUM HUCRESI ARTIK SESSIZCE ATLANMAZ.
        # OLCULEN ARIZA: kolon kaymasi durum hucresini BOS birakabilir; eski
        # `if not durum: continue` boyle bir satiri GECERSIZ kovasina bile
        # sokmadan dusuruyordu. Canli KraL/ORTAK defterinde K339-EK (L147) tam
        # olarak bunun yuzunden GECERSIZ_DURUM sayisinda GORUNMUYORDU —
        # kapinin kendi RED metni onu HIC saymadi. Bos hucre kanonik bes
        # degerden biri DEGILDIR: asagidaki `durum not in KANONIK_DURUMLAR`
        # kolu onu fail-closed RED'e goturur.
        # MENZIL OLCULDU (yama oncesi, 8 ev): bos durumlu satir = 1 fiziksel
        # satir (KraL ve ORTAK ayni dosyayi gosteriyor) — bu kol baska hicbir
        # evi kirmiziya yakmaz.
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
        # 🔴 K380 (b) — KANONIK-DISI DURUM HUCRESI SESSIZCE ATLANMAZ.
        # Sink verilmemisse (eski cagri yerleri) davranis DEGISMEZ: satir eskisi
        # gibi sayilmaz. Sink verilmisse cagri yeri fail-closed RED verir.
        if durum not in KANONIK_DURUMLAR:
            if gecersiz_sink is not None:
                gecersiz_sink.append({
                    "kimlik": kolonlar[1].strip(),
                    "durum": durum,
                    "satir_no": satir_no,
                })
            continue
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
def _okan_kapisi_eki(sonuc):
    """🔴 K380 (a) — BASKI HER HUKUM SATIRINDA GORUNUR.

    OKAN-KAPISI kalemleri borctan CIKARILDI, ama SESSIZLESTIRILMEDI: hem RED
    hem GECER metninde `OKAN_KAPISI=N` eki durur. Ek yalnizca N>0 iken basilir
    (gurultu yok); N=0'da eskisiyle BIREBIR ayni metin uretilir — bu, `M1`/`M2`
    gibi mevcut mutantlarin metin capalarini KIRMAMASI icin gereklidir.
    """
    n = sonuc.get("OKAN_KAPISI_SAYISI", 0)
    if not n:
        return ""
    return (" | OKAN_KAPISI=%d (borc sayimi DISINDA — kapatani Okan'in eli; "
            "baski 23:00 ozetinde): %s"
            % (n, ",".join(sonuc.get("OKAN_KAPISI") or [])))


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
        # 🔴 K380 (a) — OKAN-KAPISI kalemleri: BORC DEGIL, ama GORUNUR.
        # `ACIK_SAYISI` artik YALNIZ ACIK/UCUSTA/🔧 sayar; Okan kapisindaki
        # kalemler bu ayri alanda tasinir ve 23:00 ozetine gider.
        "OKAN_KAPISI": [],
        "OKAN_KAPISI_SAYISI": 0,
        # Defterdeki TUM acik kalem (borc + Okan kapisi) — okuyuculara taban.
        "TOPLAM_ACIK_SAYISI": 0,
        # 🔴 K380 (b) — kanonik-disi durum hucreli satirlar.
        "GECERSIZ_DURUM": [],
        "GECERSIZ_DURUM_SAYISI": 0,
    }

    try:
        kok, defter_yol, gecerli = acik_kalem_yolu(ev, koku_root=koku_root)
    except EvHaritasiOlculemedi as e:
        # 🔴 K361 FAIL-CLOSED: harita yok/bozuk/bos -> "borc yok" SAYILMAZ.
        sonuc["OLCULEMEDI"] = True
        sonuc["RED"] = True
        sonuc["HATA"] = "%s %s" % (T4_OLCULEMEDI_JETON, e)
        return sonuc
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
    gecersizler = []
    kalemler, okundu, hata = acik_kalem_listesi(defter_yol,
                                                gecersiz_sink=gecersizler)
    # 🔴 K380 (a) — BORC ile OKAN-KAPISI AYRISIR. `ACIK_SAYISI` = T4-BORC'un
    # sayimi = YALNIZ ACIK/UCUSTA/🔧. Bu alan `parti-kapisi.py:782`de N2B'nin
    # `ACIK=<n>` satirini besler; hukmu veren sayiyla ekrana basilan sayi AYNI
    # kalsin diye burasi daraltildi (ikisi ayrisirsa kapi kendi gerekcesini
    # yalanlar). TUM acik kalem sayisi `TOPLAM_ACIK_SAYISI`de DURUYOR.
    borclu = [k for k in kalemler if k["durum"] in BORC_DURUMLARI]
    okan_kapisi = [k for k in kalemler if k["durum"] == OKAN_KAPISI_DURUMU]
    sayi = len(borclu)
    sonuc["ACIK_SAYISI"] = sayi
    sonuc["TOPLAM_ACIK_SAYISI"] = len(kalemler)
    sonuc["OKAN_KAPISI"] = [k.get("kimlik") or "?" for k in okan_kapisi]
    sonuc["OKAN_KAPISI_SAYISI"] = len(okan_kapisi)
    sonuc["GECERSIZ_DURUM"] = gecersizler
    sonuc["GECERSIZ_DURUM_SAYISI"] = len(gecersizler)
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

    # --- K380 (b) KOL: GECERSIZ DURUM HUCRESI -> T4-OLCULEMEDI fail-closed ----
    # 🔴 SIRA KASITLIDIR VE EN ONDEDIR: durum hucresi okunamayan bir satirin
    # ACIK mi KAPANDI mi oldugu BILINMIYOR demektir; yani SAYININ KENDISI
    # olculmemistir. Olculmemis sayidan hukum cikaran her kol (T4-OLCUTSUZ,
    # T4-BORC, T4-TEMIZ) bu satirin ARDINDA kalir. Once konmasaydi F08 tipi
    # satir tasiyan temiz bir defter `T4-TEMIZ GECER` verirdi — tam da
    # kapatilmak istenen yanlis-yesil.
    if gecersizler:
        sonuc["OLCULEMEDI"] = True
        sonuc["RED"] = True
        sonuc["DURUM"] = "BILINMIYOR"
        dokum = " ".join("%s=%s" % (g["kimlik"] or "?", _durum_kirp(g["durum"]))
                         for g in gecersizler[:GECERSIZ_DOKUM_TAVANI])
        if len(gecersizler) > GECERSIZ_DOKUM_TAVANI:
            dokum += " (+%d satir daha)" % (len(gecersizler) - GECERSIZ_DOKUM_TAVANI)
        sonuc["HATA"] = (
            "%s durum gecersiz %s — kanonik bes deger: %s. Satir ATLANMAZ: "
            "durumu okunamayan kalem ACIK mi KAPANDI mi BILINMEZ, sayi "
            "olculmemistir. Defterdeki hucreyi bes degerden BIRINE cek."
            % (T4_OLCULEMEDI_JETON, dokum,
               "/".join(sorted(KANONIK_DURUMLAR))))
        return sonuc

    # --- K289 KOL: T4-OLCUTSUZ (ESIKTEN BAGIMSIZ, T4-BORC'tan ONCE) -----------
    # 🔴 SIRA KASITLIDIR: T4-BORC'tan SONRA konsaydi kol PRODUKSIYONDA OLU
    # olurdu — varsayilan esik 0'dir, yani T4-BORC her acik kalemde once
    # ateslenir ve olcut kolu HIC kosmazdi ([[kapinin-menzili-cagri-yeridir]]).
    # Gerekce ayrica sirasal degil MANTIKSAL: olcutu olmayan bir borc SAYILABILIR
    # ama KAPATILAMAZ; once olcut yazilir, sonra borc kapatilir.
    # 🔴 K380 (a) ile AYNI MENZIL: olcut kolu da YALNIZ BORCLU kalemleri okur.
    # Aksi halde `kabul:` tasimayan tek bir OKAN-KAPISI satiri evi gene
    # kilitlerdi ve (a) INERT olurdu — kilit kapiyi degistirir, kalkmazdi
    # ([[kapinin-menzili-cagri-yeridir]]).
    olcutsuz = olcutsuz_kalemler(borclu, mutant=olcut_mutant)
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
        sonuc["RED_SEBEBI"] = ("T4-BORC ev=%s acik_kalem=%d esik=%d (esik asildi)%s"
                              % (ev, sayi, esik, _okan_kapisi_eki(sonuc)))
        sonuc["DURUM"] = "ACIK"
        return sonuc

    # GECER — acik kalem yok ya da esik altinda.
    sonuc["DURUM"] = "KAPANDI"
    sonuc["GECER_MESAJI"] = ("T4-TEMIZ ev=%s acik_kalem=%d esik=%d (esik altinda; "
                             "parti gecer)%s"
                             % (ev, sayi, esik, _okan_kapisi_eki(sonuc)))
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


# ==============================================================================
# 🔴 K380 — IZOLE KOPYA MUTANT ALTYAPISI (M-a / M-b)
# ==============================================================================
# BaBa hukmu (6 Eyl, ortak kutu 16:5x): "Mutant IZOLE kopyada (benzersiz ad +
# `dont_write_bytecode`); gercek ev yoluna `rm -rf`/`rmtree`/`unlink` YASAK."
#
# NEDEN GOVDE-ICI BAYRAK DEGIL (M5/M6 gibi): M5/M6 kolu bir PARAMETREYLE
# oldurur; o parametre KAYNAKTA DURUR ve gercek kolu tarif eder. K380'in iki
# kolu ise SABIT/AKIS duzeyinde (kume uyeligi + `if` kosulu); onlari parametreye
# cevirmek kolu gevsetirdi. Bu yuzden yama KAYNAK METNE uygulanir, ama CANLI
# govdeye DEGIL — canli govdede yasayan mutant kapinin kendisini bozar
# ([[mutant-canli-govdede-yasamaz]]).
#
# 🔴 CAPA FONKSIYONDUR, SABIT DIZGE DEGIL: capa regex'i kaynakta TAM 1 kez
# eslesmezse mutant "kirmizi gelmedi" diye SESSIZ gecmez — `CAPA-COZULMEDI`
# ile ADIYLA kirmizi yanar ([[capa-cokmesi-arkasindaki-capalari-gizler]],
# [[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]).
K380_MUTANT_ONEK = "pbk-k380-mutant-"


def _k380_m_a_yama(kaynak):
    """M-a: OKAN-KAPISI muafiyetini GERI ALIR (borc kumesine geri koyar)."""
    capa = re.compile(r"^BORC_DURUMLARI = frozenset\(\{[^}]*\}\)$", re.M)
    n = len(capa.findall(kaynak))
    if n != 1:
        return None, ("CAPA-COZULMEDI M-a: `BORC_DURUMLARI = frozenset({...})` "
                      "kaynakta %d kez eslesti (1 bekleniyordu)" % n)
    yeni = ('BORC_DURUMLARI = frozenset({"ACIK", "UCUSTA", "\U0001F527", '
            '"OKAN-KAPISI"})  # K380 M-a MUTANT')
    return capa.sub(lambda _m: yeni, kaynak, count=1), None


def _k380_m_b_yama(kaynak):
    """M-b: gecersiz-durum kolunu OLDURUR (satir yine SESSIZCE atlanir)."""
    capa = re.compile(r"^(?P<girinti>[ ]+)if durum not in KANONIK_DURUMLAR:$", re.M)
    eslesmeler = capa.findall(kaynak)
    if len(eslesmeler) != 1:
        return None, ("CAPA-COZULMEDI M-b: `if durum not in KANONIK_DURUMLAR:` "
                      "kaynakta %d kez eslesti (1 bekleniyordu)"
                      % len(eslesmeler))
    def _degistir(m):
        return "%sif False:  # K380 M-b MUTANT — kol OLDURULDU" % m.group("girinti")
    return capa.sub(_degistir, kaynak, count=1), None


def _k382_m_c_yama(kaynak):
    """M-c: KACIS KOLUNU SOKER (`\\|` yine ayirici sayilir = yama oncesi hal)."""
    # 🔴 CAPA `re.escape` ile kurulur: govde satiri ters-bolu ve tirnak
    # tasiyor; elle kacirmak capayi sessizce COZULMEZ yapardi
    # ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
    govde = ('    return [h.replace("\\\\|", "|") '
             'for h in KacissizAyirici.split(satir)]')
    capa = re.compile("^%s$" % re.escape(govde), re.M)
    n = len(capa.findall(kaynak))
    if n != 1:
        return None, ("CAPA-COZULMEDI M-c: `hucrelere_bol` govde satiri "
                      "kaynakta %d kez eslesti (1 bekleniyordu)" % n)
    yeni = '    return satir.split("|")  # K382 M-c MUTANT — kacis kolu SOKULDU'
    return capa.sub(lambda _m: yeni, kaynak, count=1), None


def _k382_m_d_yama(kaynak):
    """M-d: AYRAC SATIRI elemesini OLDURUR (`|---|---|` durum sayilir)."""
    capa = re.compile(r"^(?P<girinti>[ ]+)if _ayrac_satiri_mi\(kolonlar\):$", re.M)
    n = len(capa.findall(kaynak))
    if n != 1:
        return None, ("CAPA-COZULMEDI M-d: `if _ayrac_satiri_mi(kolonlar):` "
                      "kaynakta %d kez eslesti (1 bekleniyordu)" % n)

    def _degistir(m):
        return "%sif False:  # K382 M-d MUTANT — ayrac elemesi OLDURULDU" % m.group("girinti")
    return capa.sub(_degistir, kaynak, count=1), None


K380_MUTANTLARI = {
    "M-a": ("(a) OKAN-KAPISI borctan CIKAR", _k380_m_a_yama),
    "M-b": ("(b) gecersiz durum hucresi -> fail-closed RED", _k380_m_b_yama),
    # 🔴 K382 — iki YENI kol, ikisi de AYRI mutantla kanitlanir.
    "M-c": ("(c) `\\|` kacisi hucre icerigidir (kolon kaymasi YOK)", _k382_m_c_yama),
    "M-d": ("(d) markdown AYRAC satiri elenir (kapi kendi ayracina takilmaz)",
            _k382_m_d_yama),
}


def _k380_mutant_yukle(ad, gecici_dizin):
    """Kaynagin YAMALI, IZOLE bir kopyasini modul olarak yukler.

    Return: (modul, hata_mesaji_or_None). Kopya `gecici_dizin` altina BENZERSIZ
    adla yazilir; `sys.dont_write_bytecode` acikken import edilir ki yanina
    `__pycache__` DUSMESIN (Okan diski: makinede iz birakilmaz).
    """
    _aciklama, yamaci = K380_MUTANTLARI[ad]
    kendi_yol = os.path.abspath(__file__)
    try:
        with open(kendi_yol, encoding="utf-8") as f:
            kaynak = f.read()
    except OSError as e:
        return None, "KAYNAK-OKUNAMADI %s: %r" % (ad, e)

    yamali, hata = yamaci(kaynak)
    if hata:
        return None, hata
    if yamali == kaynak:
        # [[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]
        return None, "MUTANT-ULASMADI %s: yama kaynagi DEGISTIRMEDI" % ad

    benzersiz = "%s%s_%s" % (K380_MUTANT_ONEK.replace("-", "_"),
                             ad.replace("-", "_"), os.urandom(6).hex())
    kopya_yol = os.path.join(gecici_dizin, benzersiz + ".py")
    try:
        with open(kopya_yol, "w", encoding="utf-8") as f:
            f.write(yamali)
    except OSError as e:
        return None, "KOPYA-YAZILAMADI %s: %r" % (ad, e)

    eski_bayrak = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import importlib.util as _iu
        spec = _iu.spec_from_file_location(benzersiz, kopya_yol)
        if spec is None or spec.loader is None:
            return None, "KOPYA-YUKLENEMEDI %s: spec None" % ad
        modul = _iu.module_from_spec(spec)
        spec.loader.exec_module(modul)
    except Exception as e:          # noqa: BLE001 — mutant kopyasi cokerse ADIYLA
        return None, "KOPYA-COKTU %s: %r" % (ad, e)
    finally:
        sys.dont_write_bytecode = eski_bayrak
    return modul, None


def _k380_gecici_temizle(dizin):
    """🔴 YALNIZ kendi gecici dizinimizi siler. BaBa yasagi: gercek ev yoluna
    `rmtree`/`unlink` YOK. Yol tempdir altinda ve kendi onekimizi tasimiyorsa
    SILME — sessizce gec (silmemek zarar vermez, yanlis silmek yikimdir)."""
    if not dizin:
        return False
    mutlak = os.path.abspath(dizin)
    temp_kok = os.path.abspath(tempfile.gettempdir())
    taban = os.path.basename(mutlak)
    guvenli = (mutlak.startswith(temp_kok + os.sep)
               and taban.startswith(K380_MUTANT_ONEK))
    if not guvenli:
        return False
    shutil.rmtree(mutlak, ignore_errors=True)
    return True


def k380_bataryasi(esik, koku_root):
    """M-a + M-b: iki kol, iki IZOLE kopya mutanti, iki-yonlu kontrol.

    Return: (adimlar, gecici_dizin) — adim = (ad, jeton, gecti, mesaj, ayrinti).
    """
    adimlar = []
    gecici = tempfile.mkdtemp(prefix=K380_MUTANT_ONEK)

    # ---------------- M-a: OKAN-KAPISI BORCTAN CIKAR ----------------------
    # 🔴 IKI YONLU (NON-GROWTH): tek yonlu bir iddia ("OKAN-KAPISI'li defter
    # GECER") kolu tumden bosaltan bir yamayla da YESIL yanardi. Bu yuzden ayni
    # mutant AYNI kosumda ters kolda da olculur: ACIK'li defter HALA RED
    # olmalidir ([[grep-sifir-nobetcisi-yasak-kaydinda-oludur]]).
    defter_a = os.path.join(koku_root, "BaBa", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_a, acik_sayisi=1,
                         durum_dagilimi={OKAN_KAPISI_DURUMU: 1})
    gercek_a = parti_engeli_var_mi("BaBa", esik=esik, koku_root=koku_root)

    defter_b = os.path.join(koku_root, "ORTAK", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_b, acik_sayisi=1, durum_dagilimi={"ACIK": 1})
    gercek_b = parti_engeli_var_mi("ORTAK", esik=esik, koku_root=koku_root)

    mut_a, hata_a = _k380_mutant_yukle("M-a", gecici)
    if mut_a is None:
        adimlar.append(("M-a", T4_TEMIZ_JETON, False,
                        "IZOLE KOPYA KURULAMADI: %s" % hata_a, gercek_a))
    else:
        mutant_a = mut_a.parti_engeli_var_mi("BaBa", esik=esik,
                                             koku_root=koku_root)
        mutant_b = mut_a.parti_engeli_var_mi("ORTAK", esik=esik,
                                             koku_root=koku_root)
        gecti = (
            # (1) GERCEK govde: tek OKAN-KAPISI satirli defter -> T4-TEMIZ GECER
            gercek_a["RED"] is False
            and gercek_a["ACIK_SAYISI"] == 0
            and gercek_a["OKAN_KAPISI_SAYISI"] == 1
            and gercek_a["TOPLAM_ACIK_SAYISI"] == 1
            and (gercek_a["GECER_MESAJI"] or "").startswith(T4_TEMIZ_JETON + " ")
            # (2) GERCEK govde TERS KOL: tek ACIK satirli defter -> T4-BORC RED
            and gercek_b["RED"] is True
            and gercek_b["ACIK_SAYISI"] == 1
            and gercek_b["OKAN_KAPISI_SAYISI"] == 0
            and (gercek_b["RED_SEBEBI"] or "").startswith(T4_BORC_JETON + " ")
            # (3) MUTANT: muafiyet geri alininca AYNI defter T4-BORC'a doner
            and mutant_a["RED"] is True
            and mutant_a["ACIK_SAYISI"] == 1
            and (mutant_a["RED_SEBEBI"] or "").startswith(T4_BORC_JETON + " ")
            # (4) MUTANT TERS KOL: ACIK'li defter mutantta DA RED (yama kolu
            #     bosaltmadi, sadece muafiyeti kaldirdi)
            and mutant_b["RED"] is True
        )
        adimlar.append(("M-a", T4_TEMIZ_JETON, gecti,
                        "OKAN-KAPISI x1 -> T4-TEMIZ GECER (ACIK x1 -> T4-BORC RED); "
                        "izole kopyada muafiyet GERI ALININCA ayni defter "
                        "T4-BORC RED -> kirmizinin sebebi BU kol",
                        gercek_a))

    # ---------------- M-b: GECERSIZ DURUM HUCRESI -> RED ------------------
    # Fikstur F08'in BIREBIR kalibi: `ACIK (Okan kapisi KALKTI)`.
    F08_KALIBI = "ACIK (Okan kapısı KALKTI)"
    defter_c = os.path.join(koku_root, "BaBa", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_c, acik_sayisi=1,
                         durum_dagilimi={F08_KALIBI: 1})
    gercek_c = parti_engeli_var_mi("BaBa", esik=esik, koku_root=koku_root)

    # KONTROL: kanonik hucreli defter -> kol SUSAR (kor kapi degil). Ayni
    # fikstur AYRAC satirini da tasir; ayrac kolu tetiklerse burasi kirmizi.
    defter_d = os.path.join(koku_root, "ORTAK", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_d, acik_sayisi=2,
                         durum_dagilimi={KAPALI_DURUM: 1, OKAN_KAPISI_DURUMU: 1})
    gercek_d = parti_engeli_var_mi("ORTAK", esik=esik, koku_root=koku_root)

    mut_b, hata_b = _k380_mutant_yukle("M-b", gecici)
    if mut_b is None:
        adimlar.append(("M-b", T4_OLCULEMEDI_JETON, False,
                        "IZOLE KOPYA KURULAMADI: %s" % hata_b, gercek_c))
    else:
        mutant_c = mut_b.parti_engeli_var_mi("BaBa", esik=esik,
                                             koku_root=koku_root)
        gecti = (
            # (1) GERCEK govde: serbest-metinli hucre -> fail-closed RED
            gercek_c["RED"] is True
            and gercek_c["OLCULEMEDI"] is True
            and gercek_c["GECERSIZ_DURUM_SAYISI"] == 1
            and (gercek_c["HATA"] or "").startswith(T4_OLCULEMEDI_JETON + " ")
            and "durum gecersiz" in (gercek_c["HATA"] or "")
            # (2) MUTANT: kol oldurulunce AYNI satir SESSIZCE atlanir -> GECER
            #     (bu, F08'in bugunku hali: yanlis-yesil)
            and mutant_c["RED"] is False
            and (mutant_c["GECER_MESAJI"] or "").startswith(T4_TEMIZ_JETON + " ")
            # (3) KONTROL: kanonik hucreli defterde kol SUSAR (+ AYRAC satiri
            #     kolu TETIKLEMEZ) -> kapi "hep RED" diyen kor kapi DEGIL
            and gercek_d["GECERSIZ_DURUM_SAYISI"] == 0
            and gercek_d["RED"] is False
            and gercek_d["OKAN_KAPISI_SAYISI"] == 1
        )
        adimlar.append(("M-b", T4_OLCULEMEDI_JETON, gecti,
                        "`%s` -> T4-OLCULEMEDI RED (sessiz atlama YOK); izole "
                        "kopyada kol OLDURULUNCE ayni satir atlanip GECER "
                        "doner; kanonik+ayracli defterde kol SUSAR"
                        % F08_KALIBI,
                        gercek_c))

    return adimlar, gecici


def _k382_kacisli_defter_yaz(defter_yol, kacisli=True):
    """K382 fiksturu: `is` hucresinde markdown KACISLI `\\|` tasiyan 1 ACIK satir.

    kacisli=False ise AYNI satir kacissiz yazilir (KONTROL kolu): o hal
    gercekten bozuk bir defterdir ve HER IKI govdede de ayni davranmalidir —
    mutantin farki yalnizca KACISLI satirda gorunmelidir.
    """
    ayirici = "\\|" if kacisli else "|"
    satirlar = [
        "# AÇIK KALEM DEFTERİ (sentetik — K382)",
        "",
        "| id | tarih | kimden→kime | iş | durum | kapanış kanıtı |",
        "|---|---|---|---|---|---|",
        "| K901 | 2026-09-06 | sentetik→sentetik | grep -E '^(YAZILDI%sUYARI)' testi "
        "| ACIK | kabul: python3 tools/sentetik-kabul.py |" % ayirici,
    ]
    dizin = os.path.dirname(defter_yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin, exist_ok=True)
    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")


def k382_bataryasi(esik, koku_root):
    """M-c (kacis kolu) + M-d (ayrac elemesi), IZOLE kopya mutantlariyla.

    Her adim hedef kolunu AYRICA kanitlar (K182): mutantin urettigi kirmizinin
    SEBEBI o kol mu? Bunun icin her mutantin YANINDA bir KONTROL olculur —
    kolun DOKUNMADIGI bir fiksturde mutant ile gercek govde AYNI davranmali.
    """
    adimlar = []
    gecici = tempfile.mkdtemp(prefix=K380_MUTANT_ONEK)

    # ---------------- M-c: KACIS KOLU -------------------------------------
    defter_kacisli = os.path.join(koku_root, "KraL", ACIK_KALEM_DOSYA)
    _k382_kacisli_defter_yaz(defter_kacisli, kacisli=True)
    gercek_kacisli = parti_engeli_var_mi("KraL", esik=esik, koku_root=koku_root)

    # KONTROL fiksturu: kacisSIZ ayni satir. Kacis kolu bu satira DOKUNMAZ,
    # yani gercek govde ile mutant AYNI sonucu vermeli.
    defter_duz = os.path.join(koku_root, "ArTisT", ACIK_KALEM_DOSYA)
    _k382_kacisli_defter_yaz(defter_duz, kacisli=False)
    gercek_duz = parti_engeli_var_mi("ArTisT", esik=esik, koku_root=koku_root)

    mut_c, hata_c = _k380_mutant_yukle("M-c", gecici)
    if mut_c is None:
        adimlar.append(("M-c", T4_OLCULEMEDI_JETON, False,
                        "IZOLE KOPYA KURULAMADI: %s" % hata_c, gercek_kacisli))
    else:
        mutant_kacisli = mut_c.parti_engeli_var_mi("KraL", esik=esik,
                                                   koku_root=koku_root)
        mutant_duz = mut_c.parti_engeli_var_mi("ArTisT", esik=esik,
                                               koku_root=koku_root)
        gecti = (
            # (1) GERCEK govde: kacisli satir DOGRU okunur -> 1 ACIK kalem,
            #     gecersiz YOK, hukum T4-BORC (esik 0 asildi).
            gercek_kacisli["GECERSIZ_DURUM_SAYISI"] == 0
            and gercek_kacisli["OLCULEMEDI"] is False
            and gercek_kacisli["ACIK_SAYISI"] == 1
            and (gercek_kacisli["RED_SEBEBI"] or "").startswith(T4_BORC_JETON + " ")
            # (2) MUTANT: kacis kolu sokulunce AYNI satir kayar; durum hucresi
            #     kanonik olmaktan cikar -> fail-closed T4-OLCULEMEDI.
            and mutant_kacisli["OLCULEMEDI"] is True
            and mutant_kacisli["GECERSIZ_DURUM_SAYISI"] == 1
            and mutant_kacisli["ACIK_SAYISI"] == 0
            # (3) HEDEF-KOL ATFI (K182): kacisSIZ fiksturde mutant ile gercek
            #     govde AYNI davranir -> kirmizinin sebebi KACIS KOLUDUR,
            #     genel bir bozulma DEGIL.
            and gercek_duz["GECERSIZ_DURUM_SAYISI"] == mutant_duz["GECERSIZ_DURUM_SAYISI"]
            and gercek_duz["OLCULEMEDI"] == mutant_duz["OLCULEMEDI"]
            and gercek_duz["ACIK_SAYISI"] == mutant_duz["ACIK_SAYISI"]
        )
        adimlar.append(("M-c", T4_OLCULEMEDI_JETON, gecti,
                        "`\\|` kacisli satir GERCEK govdede ACIK=1 (gecersiz 0); "
                        "izole kopyada kacis kolu SOKULUNCE ayni satir kayar ve "
                        "T4-OLCULEMEDI RED olur; kacisSIZ KONTROL fiksturunde "
                        "mutant ile gercek govde AYNI -> kirmizinin sebebi BU kol",
                        gercek_kacisli))

    # ---------------- M-d: AYRAC SATIRI ELEMESI ---------------------------
    # Fikstur: kanonik durumlu, AYRAC satiri TASIYAN normal defter.
    defter_ayrac = os.path.join(koku_root, "HocA", ACIK_KALEM_DOSYA)
    _sentetik_defter_yaz(defter_ayrac, acik_sayisi=0,
                         durum_dagilimi={KAPALI_DURUM: 2})
    gercek_ayrac = parti_engeli_var_mi("HocA", esik=esik, koku_root=koku_root)

    mut_d, hata_d = _k380_mutant_yukle("M-d", gecici)
    if mut_d is None:
        adimlar.append(("M-d", T4_OLCULEMEDI_JETON, False,
                        "IZOLE KOPYA KURULAMADI: %s" % hata_d, gercek_ayrac))
    else:
        mutant_ayrac = mut_d.parti_engeli_var_mi("HocA", esik=esik,
                                                 koku_root=koku_root)
        gecti = (
            # (1) GERCEK govde: ayrac elenir -> gecersiz YOK, defter TEMIZ GECER
            gercek_ayrac["GECERSIZ_DURUM_SAYISI"] == 0
            and gercek_ayrac["RED"] is False
            and (gercek_ayrac["GECER_MESAJI"] or "").startswith(T4_TEMIZ_JETON + " ")
            # (2) MUTANT: eleme oldurulunce `|---|---|` satirinin `---` hucresi
            #     durum sayilir -> HER defter kirmizi yanar (kapinin kendi
            #     ayracina takilmasi, [[kurucu-kendi-kapisina-takilir]]).
            and mutant_ayrac["OLCULEMEDI"] is True
            and mutant_ayrac["GECERSIZ_DURUM_SAYISI"] >= 1
            # 🔴 HEDEF-KOL ATFI (K182): kirmizinin sebebi AYRAC hucresi olmali.
            # Yalnizca "kirmizi geldi" demek yetmez — RED metninde gecersiz
            # durum olarak BIREBIR `'---'` gorunmeli.
            and "'---'" in (mutant_ayrac["HATA"] or "")
        )
        adimlar.append(("M-d", T4_OLCULEMEDI_JETON, gecti,
                        "ayracli defter GERCEK govdede T4-TEMIZ GECER; izole "
                        "kopyada ayrac elemesi OLDURULUNCE `---` hucresi durum "
                        "sayilir ve T4-OLCULEMEDI RED olur",
                        gercek_ayrac))

    return adimlar, gecici


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

    # === K380 — M-a + M-b (IZOLE KOPYA MUTANTLARI) =========================
    # 🔴 EN SONA konur: BaBa/ORTAK defterlerini YAZAR ve onceki adimlarin
    # fiksturlerine (KraL/ArTisT/TeKiN/MaCiT/HocA) DOKUNMAZ.
    k380_adimlari, k380_gecici = k380_bataryasi(esik, koku_root)
    adimlar.extend(k380_adimlari)

    # === K382 — M-c + M-d (IZOLE KOPYA MUTANTLARI) =========================
    # 🔴 KraL/ArTisT/HocA fiksturlerini YENIDEN yazar; bu yuzden K380'den SONRA
    # ve ozet basimindan ONCE kosar (onceki adimlarin sonuclari zaten alindi).
    k382_adimlari, k382_gecici = k382_bataryasi(esik, koku_root)
    adimlar.extend(k382_adimlari)

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

    # 🔴 K380 — gecici mutant kopyalari SILINIR (Okan diski: iz birakilmaz).
    # Silme YALNIZ kendi tempdir onegimize uygular; gercek ev yoluna DOKUNMAZ.
    silindi = _k380_gecici_temizle(k380_gecici)
    print("K380 IZOLE MUTANT DIZINI: %s -> silindi=%s"
          % (k380_gecici, "EVET" if silindi else "HAYIR"))
    silindi382 = _k380_gecici_temizle(k382_gecici)
    print("K382 IZOLE MUTANT DIZINI: %s -> silindi=%s"
          % (k382_gecici, "EVET" if silindi382 else "HAYIR"))
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
def harita_olculemedi_bas(nerede):
    """🔴 K361 fail-closed cikisi. Harita okunabiliyorsa None doner."""
    if EV_BILINEN is not None:
        return None
    print("T4 PARTI BORC KAPISI — %s" % nerede)
    print("HATA: %s %s" % (T4_OLCULEMEDI_JETON,
                           EV_HARITASI_HATA or "EV_HARITASI OLCULEMEDI"))
    print("KAYNAK: %s" % evler_json_yolu())
    # 🔴 RED CIKMAZ SOKAK DEGIL — kurtaran TAM KOMUT burada BASILIR.
    print("KURTARMA: %s" % kurtarma_komutu())
    print("HUKUM: RED (%s fail-closed — BOS TABLO GECERLI SAYILMAZ; "
          "bos tablo 'hicbir evde acik kalem yok' demeye gelir ve kapiyi "
          "SESSIZCE ACAR)" % T4_OLCULEMEDI_JETON)
    return 2


def kontrol(ev, esik):
    """Tek bir EV icin parti kararini bas. YAZMAZ. --kendini-test degil."""
    rc = harita_olculemedi_bas("KONTROL")
    if rc is not None:
        return rc
    if ev not in EV_BILINEN:
        print("HATA: gecersiz EV: %r" % ev)
        print("bilinen EV'ler: %s" % ", ".join(sorted(EV_BILINEN)))
        return 1
    sonuc = parti_engeli_var_mi(ev, esik=esik)
    print("T4 PARTI BORC KAPISI — KONTROL (salt-okunur, YAZMAZ)")
    print("EV: %s" % sonuc["EV"])
    print("DEFTER: %s" % (sonuc["DEFTER_YOLU"] or "(yok)"))
    # 🔴 K380 — IKI SAYI, IKI SATIR. `ACIK_KALEM` hukmu veren sayidir (yalniz
    # ACIK/UCUSTA/🔧); `OKAN_KAPISI` baskiyi tasir ama KILITLEMEZ.
    print("ACIK_KALEM: %d (ACIK/UCUSTA/🔧 — hukmu veren sayi)"
          % sonuc["ACIK_SAYISI"])
    print("OKAN_KAPISI: %d%s"
          % (sonuc.get("OKAN_KAPISI_SAYISI", 0),
             (" -> " + ",".join(sonuc.get("OKAN_KAPISI") or []))
             if sonuc.get("OKAN_KAPISI") else ""))
    print("TOPLAM_ACIK: %d (borc + Okan kapisi)"
          % sonuc.get("TOPLAM_ACIK_SAYISI", 0))
    print("GECERSIZ_DURUM: %d" % sonuc.get("GECERSIZ_DURUM_SAYISI", 0))
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
    rc = harita_olculemedi_bas("RAPOR")
    if rc is not None:
        return rc
    print("T4 PARTI BORC KAPISI — RAPOR (salt-okunur, YAZMAZ)")
    print("esik: %d" % esik)
    print("")
    print("%-10s %-12s %-13s %-11s %-8s %-12s %s"
          % ("EV", "ACIK_KALEM", "OKAN_KAPISI", "OLCUTSUZ", "ESIK", "HUKUM",
             "DEFTER"))
    print("-" * 110)
    ozet = {"RED": 0, "GECER": 0, "OLCULEMEDI": 0, "OKAN_KAPISI": 0}
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
        ozet["OKAN_KAPISI"] += sonuc.get("OKAN_KAPISI_SAYISI", 0)
        print("%-10s %-12d %-13d %-11d %-8d %-12s %s"
              % (ev, sonuc["ACIK_SAYISI"], sonuc.get("OKAN_KAPISI_SAYISI", 0),
                 sonuc.get("OLCUTSUZ_SAYISI", 0),
                 sonuc["ESIK"], huk, sonuc["DEFTER_YOLU"] or "(yok)"))
    print("-" * 110)
    print("Ozet: RED=%d GECER=%d OLCULEMEDI=%d"
          % (ozet["RED"], ozet["GECER"], ozet["OLCULEMEDI"]))
    # 🔴 K380 (a) — FILO BASKI SATIRI. 23:00 Okan ozeti bu sayiyi buradan alir.
    print("OKAN_KAPISI=%d (borc sayimi DISINDA — kilit yok, baski var)"
          % ozet["OKAN_KAPISI"])
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
    ap.add_argument("--ev-haritasi-kur", action="store_true",
                    help="KURTARMA: `~/.claude/cron/evler.json` YOKSA "
                         "`tools/evler-tohum.json`dan uretir. VARSA EZMEZ. "
                         "Runtime fallback DEGILDIR — elle kosulur.")
    ap.add_argument("--ev-haritasi-hedef", default=None,
                    help="--ev-haritasi-kur icin hedef yol (hermetik fikstur; "
                         "uretimde verilmez)")
    ap.add_argument("--rapor", action="store_true",
                    help="Tum EV'ler icin acik kalem sayisi + RED/GECER bas "
                         "(salt-okunur)")
    ap.add_argument("--defter-koku-root", default=None,
                    help="--kendini-test icin izole defter koku "
                         "(default: tempfile.mkdtemp()). Belirtilmezse gecici dizin.")
    args = ap.parse_args()

    repo_kok = _repo_kok()

    # 🔴 KURTARMA KOLU EN BASTA: tam da harita YOKKEN kosulacak komut budur,
    # bu yuzden fail-closed kapilarindan ONCE dagitilir.
    if args.ev_haritasi_kur:
        rc, satirlar = ev_haritasi_kur(args.ev_haritasi_hedef)
        for s in satirlar:
            print(s)
        return rc

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
        # 🔴 K361: batarya HERMETIKTIR — canli `evler.json`'a DOKUNMAZ.
        # Fikstur haritasi kokun altina yazilir; kosucuda (CI) canli config
        # OLMADIGI icin bu ZORUNLUDUR ([[patha-sorulan-ikili-cron-da-yok]]).
        fikstur_haritasi_kur(koku, FIKSTUR_EVLERI)
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
        fikstur_haritasi_kur(koku, FIKSTUR_EVLERI)   # K361 — hermetik
        rc = curutme_testi(repo_kok, args.esik, koku)
        if not args.defter_koku_root:
            shutil.rmtree(koku, ignore_errors=True)
        return rc

    if args.rapor:
        return rapor(args.esik)

    return kontrol(args.ev or "KraL", args.esik)


if __name__ == "__main__":
    sys.exit(main())