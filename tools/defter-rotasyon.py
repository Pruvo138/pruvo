#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-rotasyon.py — DEVAM.md -> DEVAM-ARSIV.md rotasyon araci.

Kullanim:
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md>
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md> --tarih 2026-08-16
    python3 tools/defter-rotasyon.py <defter.md> <arsiv.md> \
            --tavan-kaynaktan --isaretciye-indir      # KOTA ASILDIGINDA BU

KESME OLcUTU (mimar verdi):
  * Dosya `## ` baslikli bloklara bolunur; ilk `## `den onceki kisim BASLIK
    BOLGESI olup asla tasinmaz.
  * Bir BLOK tasinir ancak ve ancak:
      (a) icinde hic ACIK isaretci gecmiyorsa VE
      (b) baslik ya da govdesinde en az bir KAPANIS isaretci tasiyorsa.
  * Blok granulu tasinma GERCEKLESMEYEN bir acik blok icindeki LISTE MADDELERI
    tek tek degerlendirilir. Bir MADDE tasinir ancak ve ancak:
      (a) maddenin ILK SATIRINDA kapanis isaretci (`KAPANDI`, `KAPANIS`,
          `✅`) ilk anlamli jeton olarak yer aliyorsa VE
      (b) maddede hic ACIK isaretci gecmiyorsa VE
      (c) madde ARSIV'E isaret etmiyorsa (MADDE_VETO_DESENLERI icinde
          gecen desenlerden biri bulunursa TASINMAZ).
    Maddenin DEVAM satirlarinda ya da parantez icinde gecen `KAPANDI`/
    `KAPANIS`/`✅` TASIMA GEREKCESI OLAMAZ (K128; canli vaka: `- Eski
    yedek ...` maddesinin devaminda `(Motor tarifesi kalemi ... KAPANDI:
    ...)` atfi vardi ve olcut kapali sayip arsive supurmustu).
  * ACIK jetonlarin BULUNMASI harf tabanli olanlarda kelime-sinirli
    (`re` ile `\bJETON\b`); emoji/ikon olanlarda alt-dize kalir. Bu ayrim
    `ACIKLAMA`, `ACIKLANDI` gibi alakasiz kelimelerin yanlis veto
    tetiklememesi icin zorunludur (KUSUR-2).
  * Suphede kalirsan (fail-closed) tasma.

CIKIS:
    0 = basarili (veya tasinacak blok/madde yok)
    2 = guvenlik dogrulamasi basarisiz (KAYIP dahil), rotasyon iptal
    3 = ILERLEME_YOK (tavanli kosumda gecis no-op)
    4 = OLCULEMEDI (isaretciye indirme ILERLEME URETEMEDI)
    5 = ROTASYON CIFTI 1:1 TUTMADI — dosyalar GERI ALINDI (K195 §1.3)

Cikti son satiri:
    TASINAN=<n> TASINAN_MADDE=<n> DEFTER_SATIR=<n> ARSIV_SATIR=<n>

🔴 K243 KAPSAM SATIRI (20 Agu 2026) — HER gecis, TASINAN=0 olsa bile basar:
    MADDE_KOVALARI INCELENEN=<n> ACIK=<n> ARSIV_ISARETCISI=<n> KAPALI=<n>
                   SINIFLANAMAZ=<n> TUTARSIZ=<n> KAPSAYICI_BLOK=<n> BLOK=<n>
Ciplak `TASINAN=0` sekiz tur boyunca "arac bozuk mu, yetki mi yok, tavan mi
yanlis" diye aratti ve defter sekiz kez ELLE kirpildi. Sebep hicbiri degildi:
TASIMA BIRIMI yanlis seviyedeydi — defterin KALICI BOLUM BASLIKLARI
(`## ACIK KALEMLER` / `## KraL ACIK ARTIKLAR` / `## OKAN'DA` / `## ARSIVDE`)
ayni zamanda ACIK jetonudur ve blok yuklemi onlari KENDI ICERIKLERI sanip
blogu vetoluyordu. Basliklar KALEM degil KAPSAYICIDIR (bkz. _blok_kapsayici_mi).
`SINIFLANAMAZ` = ne acik ne kapali jetonu olan UCUNCU kova: fail-closed
(TASINMAZ) ama SESSIZ DEGIL — sayisi basilir
([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).

🔴 ROTASYON CIFTI INVARYANTI (K151/K195 §1.3) — her GERCEKLESEN tasima
sonrasi arac kendi isini DISKTEN olcer ve su satiri BASAR:
    ROTASYON_CIFTI defter_dusen=<n> tasinan_icerik=<n> arsive_giren=<n>
                   arsiv_muhasebe=<n> kayip=<n> fazla_dusen=<n>
                   uydurulan=<n> LOSSLESS=EVET|HAYIR
LOSSLESS=HAYIR ise dosyalar GERI ALINIR ve rc=5 doner: "tasidim" BEYANI
kabul degildir.

🔴 KOTA KENDI OLCUMU (K195 §1.4) — tavanli her kosumun sonunda:
    KOTA_KENDI_OLCUMU satir=<n> bayt=<n> tavan_satir=<n> tavan_bayt=<n>
                      ASAN_EKSEN=<...> KOTA=YESIL|KIRMIZI
Tavan degerleri kota kapisinin okudugu AYNI tek kaynaktan gelir
(tools/defter-kota-taban.py); ikinci tavan kopyasi TUTULMAZ.

🔴 ACIK KALEM ASLA ARSIVLENMEZ (K195 §1.2): isaretciye indirme adayligi
`_indirme_vetosu()` ile TURETILIR (korumali baslik / ACIK jeton / zaten
inmis govde). Vetolanan her blok `TASINMADI: <baslik> — <sebep>` basar.

Her tasinan blok icin (son-ozetten ONCE) bir `TASINAN-BLOK: <baslik>` satiri;
her tasinan madde icin `TASINAN-MADDE: <ilk satir, kirpilmis 100 kar.>`.
Hicbir sey tasinmadiysa bu satirlar YAZILMAZ (V14).

KENDINI-TEST (--kendini-test, K178):
    * Fiksturle satir ekseni + bayt ekseninin bagimsiz calistigini kanitlar.
    * Ciktinin son satiri: DUSEN=<n> (0 ise gecti, rc=0).
    * TAVAN DEGERLERI: tools/defter-kota-taban.py'dan okunur (TEK KAYNAK).
"""
import argparse
import collections
import importlib.util as _ilu
import os
import re
import shutil
import subprocess
import sys
import tempfile


ACIK_ISARETCILER = ("🔴", "🔧", "🟠", "🟡", "ACIK", "UCUSTA", "OKAN-KAPISI",
                    "BEKLIYOR", "KOSUYOR", "OKAN'DA", "ACIK KALEMLER", "YAPILACAK")
KAPANIS_ISARETCILER = ("KAPANDI", "KAPANIS", "✅")
# Madde seviyesinde ARSIV'E isaret eden kalip; gecerse madde TASINMAZ
# (KUSUR-1 onarimi). Case-insensitive alt-dize esleme.
MADDE_VETO_DESENLERI = ("arsivde",)

# ACIK_ISARETCILER ikiye ayrilir: harf tabanli olanlar kelime-sinirli
# (`\bJETON\b`), emoji/ikon olanlar alt-dize. Bu ayrim KUSUR-2'nin
# onarimi: aksi halde "ACIK" ciplak alt-dize aranirsa "ACIKLAMA",
# "ACIKLANDI" gibi alakasiz kelimeler acik veto tetikler ve kapanmis
# blok sonsuza kadar defterde kalirdi.
_HARF_JETON_RE = re.compile(
    r"\b(?:" + "|".join(
        re.escape(j) for j in ACIK_ISARETCILER if any(c.isalpha() for c in j)
    ) + r")\b"
)
_EMOJI_JETONLAR = tuple(j for j in ACIK_ISARETCILER if not any(c.isalpha() for c in j))

# K181d I2: acik bir madde `K###` kimlik tasimiyorsa KAYIP muamelesi
# gorur. Sayi 1-4 hane; bosluk ya da kelime siniriyla cevrili.
# Not: "K181d" gibi harf-ekli takip kodlari da eslenir (rakam parcasi
# yeterli), bu kasitli — paketin fail-closed kurali.
_KIMLIK_RE = re.compile(r"\bK\d{1,4}\b")

# K181d I2: "(özet çıkarılamadı)" gibi sessiz yedek YASAK. Satici
# tarafindan (ozet = ...) gibi desenlerle sessizce eklenmesini engelle.
_YASAK_SESSIZ_YEDEK_RE = re.compile(r"\(özet çıkarılamadı\)|\(ozet cikarilamadi\)")


def _kayip_kimliksiz_acik_madde(defter_yol):
    """I2: defterdeki acik (ACIK jetonlu) bir madde `K###` kimlik
    tasimiyorsa o maddenin ILK SATIRINI (kirpilmis) dondurur. Boyle bir
    madde yoksa None doner.

    Amac: T1 PENCERE MUHASEBESI gibi kimliksiz acik kalemler defterde
    takildiginda sessizce yer tutucu yazmak yerine KAYIP + rc!=0 ile
    durmali (64-gecis dondugusu bu yuzden olusmustu).
    """
    try:
        with open(defter_yol, "rb") as f:
            ham = f.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for satir in ham.splitlines():
        if not satir.startswith("- "):
            continue
        if not _acik_eslesiyor(satir):
            continue
        if _KIMLIK_RE.search(satir):
            continue
        return satir
    return None


def _sessiz_yedek_yok(defter_yol):
    """I2: defterde yasakli sessiz yedek (ornek '(özet çıkarılamadı)') VARSA
    True. Boyle bir desen tespit edilirse sessiz yedek kolu calismis
    demektir; KAYIP ile durulmali."""
    try:
        with open(defter_yol, "rb") as f:
            ham = f.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return _YASAK_SESSIZ_YEDEK_RE.search(ham) is not None


# === K195(a): ISARETCIYE INDIRME =========================================
# OLCULEN DELIK (19 Agu 2026): defter tavan ustundeyken KAPALI icerik yoksa
# arac hicbir sey tasimiyor (KAYIP/ILERLEME_YOK) ve mimar ELLE rotasyona
# zorlaniyor — bir gunde 4 kez. Cozum: kapali icerik tukendiginde bir blogun
# TAM METNINI arsive tasiyip defterde BASLIK + TEK SATIRLIK ISARETCI birakmak.
# Bu, arsivde zaten defalarca ELLE uygulanmis desendir ("defterde tek satirlik
# isaretci kaldi") — arac artik ayni seyi MAKINEYLE yapar.
#
# 🔴 "EN ESKI BLOK" DEGIL, "EN BUYUK INDIRILEBILIR BLOK": defterin bloklari
# KRONOLOJIK degil KATEGORIKtir (ACIK KALEMLER / SON DURUM / OKAN'DA /
# ARSIVDE). "En eski"yi (= dosyadaki ilk blok) tasimak ACIK KALEMLER'i
# arsive gomerdi. Bu yuzden korumali basliklar ASLA indirilmez ve indirme
# ENERJIYI en cok veren bloktan yapilir.
KORUMALI_BASLIK_DESENLERI = ("ACIK KALEMLER", "OKAN'DA", "OKAN`DA", "ARSIVDE")
# Govdesi bu kadar ya da daha az ANLAMLI satir tasiyan blok zaten
# isaretciye inmistir; tekrar indirmek ilerleme uretmez.
_ISARETCI_ASGARI_GOVDE = 3


def _blok_korumali_mi(blok):
    ust = blok["baslik"].upper()
    return any(desen in ust for desen in KORUMALI_BASLIK_DESENLERI)


# === K243 (20 Agu 2026) — TASIMA BIRIMI YANLIS SEVIYEDEYDI =================
# OLCULEN ARIZA: kanonik rotasyon SEKIZ tur boyunca `TASINAN=0 TASINAN_MADDE=0`
# dondu; sebep yetki/tavan/tarih DEGILDI. Defterin KALICI BOLUM BASLIKLARI
# (`## ACIK KALEMLER`, `## KraL ACIK ARTIKLAR`, `## OKAN'DA`, `## ARSIVDE`)
# ayni zamanda ACIK_ISARETCILER uyesidir; blok yuklemi `_acik_eslesiyor` bu
# basliklari GORUP blogun KENDISINI "acik kalem" saydi. Oysa o basliklar KALEM
# DEGIL KAPSAYICIDIR — tasinacak olan iclerindeki MADDElerdir.
#
# 🔴 YUKLEM ARTIK IKI SORUYU AYIRIR:
#   (A) blok KENDISI acik kalem mi?                    -> _acik_eslesiyor(blok metni)
#   (B) blok acik kalemleri KAPSAYAN kalici baslik mi?  -> _blok_kapsayici_mi
# Kapsayici blok BUTUN olarak ASLA tasinmaz (fail-closed SIKILASTIRMA: eskiden
# `## ARSIVDE` gibi acik jetonu OLMAYAN bir kapsayici, govdesine "KAPANDI"
# kelimesi girdigi anda TUMUYLE supurulebilirdi), yalnizca icindeki maddeler
# madde granulunde degerlendirilir.
#
# IKINCI KOPYA TUTULMAZ: kume KORUMALI_BASLIK_DESENLERI'nden TURETILIR
# ([[ikiz-tanim-sessiz-ayrisma]]). Eklenen tek uye `ACIK ARTIKLAR`: eski
# korumali listede YOKTU, oysa `## KraL ACIK ARTIKLAR` da bir kapsayicidir.
KAPSAYICI_EK_BASLIKLAR = ("ACIK ARTIKLAR",)
KAPSAYICI_BASLIK_DESENLERI = tuple(KORUMALI_BASLIK_DESENLERI) + KAPSAYICI_EK_BASLIKLAR


def _blok_kapsayici_mi(blok):
    """Blok, acik kalemleri KAPSAYAN kalici bolum basligi mi? (tasima birimi DEGIL)"""
    ust = blok["baslik"].upper()
    return any(desen in ust for desen in KAPSAYICI_BASLIK_DESENLERI)


def _blok_anlamli_govde_satiri(blok):
    return len([s for s in blok["govde"] if s.strip()])


def _indirme_vetosu(blok):
    """Blok isaretciye INDIRILEMEZ ise SEBEP dizesi, indirilebilirse None.

    🔴 K195 §1.2 — ACIK KALEM ASLA ARSIVLENMEZ. Eski surumde veto YALNIZ
    BASLIGA bakiyordu (KORUMALI_BASLIK_DESENLERI); govdesinde 🔴/🔧/🟠 ya da
    `ACIK`/`BEKLIYOR` jetonu tasiyan KORUMASIZ bir blok TAM METNIYLE arsive
    gomulebiliyordu. Gercek DEVAM.md uzerinde OLCULDU (19 Agu on-olcum):
    korumasiz TEK blok (`🔻 KraL CANLI DURUM`, 877 bayt) `acik_jeton=True`
    tasiyor ve eski kod onu `indirilebilir=True` sayiyordu — yani hukum ile
    kural ayrisikti. Yuklem artik TURETILIR: KAPALI oldugu blok govdesinden
    okunabilen blok iner, suphede kalan TASINMAZ ve sebebini BASAR
    (fail-closed; `_tasinir_mi` ile ayni ACIK jeton kaynagi kullanilir,
    ikinci bir jeton tablosu ACILMAZ).
    """
    if _blok_korumali_mi(blok):
        return "KORUMALI BASLIK (%s)" % ", ".join(KORUMALI_BASLIK_DESENLERI)
    tum = blok["baslik"] + "\n" + "\n".join(blok["govde"])
    if _acik_eslesiyor(tum):
        return "ACIK KALEM tasiyor (ACIK jetonu blokta gecti) — K195 §1.2"
    anlamli = _blok_anlamli_govde_satiri(blok)
    if anlamli <= _ISARETCI_ASGARI_GOVDE:
        return ("govde zaten isaretciye inmis (anlamli satir %d <= esik %d)"
                % (anlamli, _ISARETCI_ASGARI_GOVDE))
    return None


def _isaretciye_indirilebilir_mi(blok):
    """Blok isaretciye INDIRILEBILIR mi? (veto YOKsa evet)"""
    return _indirme_vetosu(blok) is None


def _satir_sayisi(metin):
    """Dosyanin kendi satir sayisi (son satirda newline olmayabilir)."""
    if not metin:
        return 0
    return len(metin.splitlines())


def _metin_kur(satirlar, sondaki_newline):
    """Satir listesinden metin kur; orijinalin son newline'ini KORU.

    🔴 `"\\n\\n".join(...)` KULLANILMAZ (K195 §1.3 rotasyon cifti): blok
    parcalarini cift newline ile birlestirmek her blok siniri icin defterin
    icine BIR BOS SATIR UYDURUYORDU. Gercek DEVAM.md uzerinde OLCULDU
    (19 Agu on-olcum): iki KAPANMIS madde tasindi, bayt 12288 -> 11831
    DUSTU ama SATIR 120 -> 123 CIKTI. Yani rotasyon bir ekseni indirirken
    otekini yukseltiyordu ve tasinan icerik "1:1" degildi. Bloklarin kendi
    govdeleri sondaki bos satirlari ZATEN tasidigi icin tek "\\n" birebir
    yeniden kurar.
    """
    # 🔴 BOS SONUC BOS DOSYADIR: satir listesi bosken `"\n".join([]) + "\n"`
    # tek basina bir BOS SATIR uydurur. Olculdu (19 Agu): tek blogu tamamen
    # tasinan defterde (V5/V8 fiksturleri) `uydurulan=1` cikti ve 1:1 kolu
    # dogru yerden kirmizi yandi. Bos liste -> bos metin.
    if not satirlar:
        return ""
    metin = "\n".join(satirlar)
    if sondaki_newline:
        metin += "\n"
    return metin


def _parca_satirlari(metin):
    """`"\\n".join(satirlar)` ile uretilmis bir PARCAYI satirlarina geri ayirir.

    🔴 `str.splitlines()` KULLANILMAZ. Olculdu (19 Agu, K195 kabul kosumu):
    `"- ✅ madde\\n".splitlines()` -> `["- ✅ madde"]`, yani parcanin SONUNDAKI
    bos satir SESSIZCE KAYBOLUR (splitlines sondaki newline'i "sonlandirici"
    sayar). Sonuc: arsive eksik satir yazilir ve defterden DUSEN satir sayisi
    tasinan icerikten BUYUK cikar — rotasyon cifti 1:1 TUTMAZ
    (`FAZLA_DUSEN '' x2`). `.split("\\n")` join'in TAM TERSIDIR.

    DOSYA METINLERI icin bu fonksiyon KULLANILMAZ (orada splitlines dogrudur);
    yalniz join ile uretilmis parcalar icin.
    """
    return metin.split("\n")


def _satir_sayaci(metin):
    """Satir COKLU KUMESI (Counter) — 1:1 invaryanti icin (DOSYA metni)."""
    return collections.Counter(metin.splitlines())


def _rotasyon_cifti_dogrula(defter_once, defter_sonra, arsiv_once, arsiv_sonra,
                            tasinan_metinler, defter_beyan_satirlari):
    """🔴 ROTASYON CIFTI INVARYANTI (K151/K195 §1.3) — 1:1, LOSSLESS.

    "Tasidim" BEYANI yeterli DEGILDIR ([[isci-isi-commitlemeden-tamamlandi-der]]
    sinifi, 238/239 vakasi): arac ne tasidigini DISKTEN olcer ve UC kolu birden
    dogrular. Donus: (tamam_mi, rapor_satiri, teshis_satirlari).

      (1) LOSSLESS — defterden DUSEN her satir arsive GIRMIS olmali.
          Ihlal = KAYIP: defterden gitti, arsivde YOK.
      (2) 1:1 — defterden dusen kume, TASINAN icerigin ALT KUMESI olmali.
          Ihlal = defter, tasinmayan bir satiri de kaybetmis.
      (3) UYDURMA YOK — deftere GIREN her satir, aracin BEYAN ettigi
          isaretci satirlarindan biri olmali. Ihlal = arac defterin icine
          satir uydurmus (yukaridaki cift-newline kusurunun tam olculdugu kol).

    Sayilar RAPORLANIR; tutmuyorsa cagiran GERI ALIR ve rc!=0 doner.
    """
    dusen = _satir_sayaci(defter_once) - _satir_sayaci(defter_sonra)
    giren = _satir_sayaci(defter_sonra) - _satir_sayaci(defter_once)
    arsiv_artan = _satir_sayaci(arsiv_sonra) - _satir_sayaci(arsiv_once)

    icerik = collections.Counter()
    for metin in tasinan_metinler:
        icerik.update(_parca_satirlari(metin))
    beyan = collections.Counter(defter_beyan_satirlari)

    kayip = dusen - arsiv_artan          # (1)
    fazla_dusen = dusen - icerik         # (2)
    beyansiz_giren = giren - beyan       # (3)

    tamam = not kayip and not fazla_dusen and not beyansiz_giren
    rapor = ("ROTASYON_CIFTI defter_dusen=%d tasinan_icerik=%d arsive_giren=%d "
             "arsiv_muhasebe=%d kayip=%d fazla_dusen=%d uydurulan=%d LOSSLESS=%s"
             % (sum(dusen.values()), sum(icerik.values()),
                sum(arsiv_artan.values()),
                sum(arsiv_artan.values()) - sum(icerik.values()),
                sum(kayip.values()), sum(fazla_dusen.values()),
                sum(beyansiz_giren.values()),
                "EVET" if tamam else "HAYIR"))
    teshis = []
    for etiket, sayac in (("KAYIP(arsivde yok)", kayip),
                          ("FAZLA_DUSEN(tasinmadi ama gitti)", fazla_dusen),
                          ("UYDURULAN(deftere girdi)", beyansiz_giren)):
        for satir, adet in list(sayac.items())[:3]:
            teshis.append("  1:1 IHLAL %s x%d: %r" % (etiket, adet, satir[:80]))
    return tamam, rapor, teshis


def _kota_kendi_olcumu(defter_yol):
    """K195 §1.4 — arac kotayi KENDI olcup basar.

    🔴 IKINCI TAVAN KOPYASI TUTULMAZ: TAVAN_SATIR/TAVAN_BAYT ve hukum
    fonksiyonu `tools/defter-kota-taban.py`'dan gelir — kota kapisinin
    okudugu AYNI kaynak ([[ikiz-tanim-sessiz-ayrisma]]).
    """
    try:
        with open(defter_yol, "rb") as f:
            ham = f.read()
    except OSError as e:
        return "KOTA_KENDI_OLCUMU OLCULEMEDI sebep=%s" % e
    satir, bayt = len(ham.splitlines()), len(ham)
    asi, eksen, _, _ = _tavan_asi_mi(satir, bayt)
    return ("KOTA_KENDI_OLCUMU satir=%d bayt=%d tavan_satir=%d tavan_bayt=%d "
            "ASAN_EKSEN=%s KOTA=%s"
            % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen or "-",
               "KIRMIZI" if asi else "YESIL"))


def _kova_satiri(kova, kapsayici_blok, blok_sayisi):
    """K243 kapsam satiri. SAYI basar, oran DEGIL; sifir kova da GORUNUR."""
    parcalar = ["MADDE_KOVALARI",
                "INCELENEN=%d" % sum(kova.get(k, 0) for k in MADDE_KOVALARI)]
    parcalar.extend("%s=%d" % (k, kova.get(k, 0)) for k in MADDE_KOVALARI)
    parcalar.append("KAPSAYICI_BLOK=%d" % kapsayici_blok)
    parcalar.append("BLOK=%d" % blok_sayisi)
    return " ".join(parcalar)


def _bloklari_ayir(metin):
    """(baslik bolgesi, [(baslik, govde), ...]).

    Ilk `## `'den onceki her sey baslik bolgesidir. Her blok `## ` ile baslar.
    Blok basligi `## `'den sonraki ILK satirdir (newline'a kadar); gerisi govde.
    """
    satirlar = metin.splitlines()
    baslik_bolgesi = []
    bloklar = []
    aktif = None
    for satir in satirlar:
        if satir.startswith("## "):
            if aktif is not None:
                bloklar.append(aktif)
            aktif = {"baslik": satir, "govde": []}
        elif aktif is None:
            baslik_bolgesi.append(satir)
        else:
            aktif["govde"].append(satir)
    if aktif is not None:
        bloklar.append(aktif)
    return baslik_bolgesi, bloklar


def _blok_metni(blok):
    """Blok basligi + govde + orijinal newline yapisi (birebir)."""
    parcalar = [blok["baslik"]]
    if blok["govde"]:
        parcalar.extend(blok["govde"])
    return "\n".join(parcalar)


def _acik_eslesiyor(metin):
    """ACIK jetonu varsa True (veto). Harf tabanli kelime-sinirli, emoji alt-dize."""
    if _HARF_JETON_RE.search(metin):
        return True
    for jeton in _EMOJI_JETONLAR:
        if jeton in metin:
            return True
    return False


def _madde_arsiv_vetolu(metin):
    """Madde ARSIV'E isaret ediyorsa True (veto). Case-insensitive."""
    kucuk = metin.lower()
    return any(d in kucuk for d in MADDE_VETO_DESENLERI)


def _tasinir_mi(blok):
    """Blok kesme olcutunu uygula: suphede kalirsan (fail-closed) TASIMA.

    🔴 K243 — ILK SORU KAPSAYICI SORUSUDUR: kalici bolum basligi bir KALEM
    degil KAPSAYICIDIR; butun olarak ASLA tasinmaz (icindeki maddeler madde
    granulunde ayrica degerlendirilir). Bu kol fail-closed YONDEDIR: eskiden
    acik jetonu olmayan bir kapsayici (`## ARSIVDE`) govdesine kapanis
    kelimesi girdiginde TUMUYLE supurulebiliyordu.
    """
    if _blok_kapsayici_mi(blok):
        return False
    tum = blok["baslik"] + "\n" + "\n".join(blok["govde"])
    if _acik_eslesiyor(tum):
        return False
    for isaretci in KAPANIS_ISARETCILER:
        if isaretci in tum:
            return True
    return False


def _ilk_satirda_kapanis(metin):
    """Madde ilk satirinda kapanis isaretci varsa True (K128).

    `- ` isaretinden sonra, ilk anlamli jeton (bosluk ve '**' atlanir)
    KAPANDI / KAPANIS / ✅ olmali. Devam satirlarinda ya da parantez
    icinde gecen `KAPANDI`/`KAPANIS`/`✅` TASIMA GEREKCESI OLAMAZ.
    Case-sensitive (mevcut KAPANIS_ISARETCILER ile ayni kural).
    """
    if not metin or not metin.startswith("- "):
        return False
    s = metin[2:]
    n = len(s)
    i = 0
    while i < n:
        if s[i].isspace():
            i += 1
            continue
        if s[i:i + 2] == "**":
            i += 2
            continue
        if s[i] == "✅":
            return True
        j = i
        while j < n and (s[j].isalnum() or s[j] == "_"):
            j += 1
        kelime = s[i:j]
        if kelime in ("KAPANDI", "KAPANIS"):
            return True
        return False
    return False


def _madde_tasinir_mi(metin):
    """Madde kesme olcutunu uygula: suphede kalirsan (fail-closed) TASIMA."""
    if _acik_eslesiyor(metin):
        return False
    if _madde_arsiv_vetolu(metin):
        return False
    if not _ilk_satirda_kapanis(metin):
        return False
    return True


# === K243 — MADDE SINIFLAMASI: DORT KOVA, HICBIRI OTEKINI YUTMAZ ==========
# [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]: "acik" ve "kapali" iki kovaya
# sikistirilan siniflama, ucuncu sinifi (jetonsuz / sinifi belirsiz madde)
# sessizce "0 tasindi"ya karistiriyordu. Kovalar artik ADLIDIR ve HEPSI
# SAYILIR — 0 olsalar bile BASILIR.
#
#   ACIK             : gercekten acik jeton tasiyor (🔴/🔧/🟠/🟡/ACIK/BEKLIYOR/...)
#   ARSIV_ISARETCISI : acik degil ama ARSIVE isaret ediyor (KUSUR-1 vetosu;
#                      arsive tasinirsa arsivin ICINDE kendine isaret eden
#                      sarkik indeks olurdu) -> TASINMAZ ama GORUNUR
#   KAPALI           : tasinabilir (ilk satirda kapanis jetonu)
#   SINIFLANAMAZ     : ne acik jetonu ne de ilk-satir kapanis jetonu var
#                      -> FAIL-CLOSED (TASINMAZ) ama SAYILIR ve BASILIR
#   TUTARSIZ         : siniflama ile tasima hukmu AYRISTI (asagiya bak)
MADDE_ACIK = "ACIK"
MADDE_ARSIV_ISARETCISI = "ARSIV_ISARETCISI"
MADDE_KAPALI = "KAPALI"
MADDE_SINIFLANAMAZ = "SINIFLANAMAZ"
MADDE_TUTARSIZ = "TUTARSIZ"
MADDE_KOVALARI = (MADDE_ACIK, MADDE_ARSIV_ISARETCISI, MADDE_KAPALI,
                  MADDE_SINIFLANAMAZ, MADDE_TUTARSIZ)


def _madde_sinifi(metin):
    """Maddenin KOVASI. Yuklem `_madde_tasinir_mi` ile AYNI uc kaynaktan
    (`_acik_eslesiyor`, `_madde_arsiv_vetolu`, `_ilk_satirda_kapanis`) ve AYNI
    SIRAYLA turer.

    🔴 IKIZ TANIM NOBETCISI: siniflama sayilariyla tasima hukmu ayrisirsa kova
    tablosu YALAN soyler ([[ikiz-tanim-sessiz-ayrisma]]). Ayrisma SESSIZ
    kalmaz: madde kendi kovasina (`TUTARSIZ`) dusulur, sayilir, basilir ve
    TASINMAZ (fail-closed). Sifir olsa bile satirda gorunur.
    """
    if _acik_eslesiyor(metin):
        sinif = MADDE_ACIK
    elif _madde_arsiv_vetolu(metin):
        sinif = MADDE_ARSIV_ISARETCISI
    elif _ilk_satirda_kapanis(metin):
        sinif = MADDE_KAPALI
    else:
        sinif = MADDE_SINIFLANAMAZ
    if (sinif == MADDE_KAPALI) != bool(_madde_tasinir_mi(metin)):
        return MADDE_TUTARSIZ
    return sinif


def _maddeleri_isle(govde, kova=None, ornekler=None):
    """Acik kalan bir blogun govdesindeki maddeleri isle.

    `kova` verilirse (collections.Counter) her madde AYRICA siniflandirilir ve
    sayilir; `ornekler` verilirse SINIFLANAMAZ/TUTARSIZ maddelerin ilk satiri
    (kova, ilk_satir) ikilisi olarak eklenir. Ikisi de opsiyoneldir — tasima
    davranisini DEGISTIRMEZLER, yalnizca gorunurluk uretirler.

    Donus: (kalan_govde_satirlari, tasinacak_madde_metinleri).
    Madde = `- ` ile baslayan satir + ondan sonraki, `- ` ile baslamayan
    girintili devam satirlari.
    """
    kalan = []
    tasinacak = []
    i = 0
    n = len(govde)
    while i < n:
        satir = govde[i]
        if satir.startswith("- "):
            madde = [satir]
            j = i + 1
            while j < n and not govde[j].startswith("- "):
                madde.append(govde[j])
                j += 1
            # 🔴 Maddenin SONUNDAKI bos satirlar madde ICERIGI degil, blok
            # AYIRACIDIR; maddeyle birlikte tasinirlarsa iki sey birden bozulur:
            #   (1) defterin blok ayiraclari her rotasyonda ERIR (eski kod bunu
            #       `"\n\n".join` ile geri EKLEYEREK gizliyordu — o telafi de
            #       satir uydurdugu icin 1:1'i bozuyordu);
            #   (2) tasinan icerik ile defterden dusen satir sayisi AYRISIR.
            # Ayirac defterde KALIR (olculdu: FAZLA_DUSEN '' x2 bu koldan geldi).
            artik = []
            while len(madde) > 1 and not madde[-1].strip():
                artik.insert(0, madde.pop())
            madde_metni = "\n".join(madde)
            if kova is not None:
                sinif = _madde_sinifi(madde_metni)
                kova[sinif] += 1
                if (ornekler is not None
                        and sinif in (MADDE_SINIFLANAMAZ, MADDE_TUTARSIZ)):
                    ornekler.append((sinif, madde[0][:100]))
            if _madde_tasinir_mi(madde_metni):
                tasinacak.append(madde_metni)
            else:
                kalan.extend(madde)
            kalan.extend(artik)
            i = j
        else:
            kalan.append(satir)
            i += 1
    return kalan, tasinacak


def _atomik_yaz(yol, icerik):
    """Gecici dosya + os.replace ile atomik yazma."""
    dizin = os.path.dirname(os.path.abspath(yol)) or "."
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".rotasyon-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(icerik.encode("utf-8"))
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def _tavan_asildi_mi(defter_yol, tavan_sayi, tavan_bayt):
    """Dosya tavanin ustunde mi? Satir/bayt esiklerinden herhangi biri asildiysa True.

    tavan_sayi/tavan_bayt None ise o eksen yok sayilir. Ikisi de None ise
    her zaman False (mevcut tek-gecis davranisina geri doner).
    """
    if tavan_sayi is None and tavan_bayt is None:
        return False
    try:
        with open(defter_yol, "rb") as f:
            ham = f.read()
    except OSError:
        return False
    satir = len(ham.splitlines())
    bayt = len(ham)
    if tavan_sayi is not None and satir > tavan_sayi:
        return True
    if tavan_bayt is not None and bayt > tavan_bayt:
        return True
    return False


def _bugun():
    import datetime
    return datetime.date.today().isoformat()


# Tek-gecis emniyeti: sonsuz donguye karsi maksimum deneme sayisi.
_TEK_GECIS_TAVAN = 64


# Tek kaynaktan türet: tools/defter-kota-taban.py (kebab-case repo kurali,
# importlib ile yukle). Ikiz [[ikiz-tanim-sessiz-ayrisma]] kapatir.
_TOOLS = os.path.dirname(os.path.abspath(__file__))
_TABAN_YOL = os.path.join(_TOOLS, "defter-kota-taban.py")
_tab_spec = _ilu.spec_from_file_location("defter_kota_taban", _TABAN_YOL)
_tab_mod = _ilu.module_from_spec(_tab_spec)
_tab_spec.loader.exec_module(_tab_mod)
TAVAN_SATIR = _tab_mod.TAVAN_SATIR
TAVAN_BAYT = _tab_mod.TAVAN_BAYT
_tavan_asi_mi = _tab_mod.tavan_asi_mi


def _kendini_test():
    """K178: tavan-bagli rotasyonun satir + bayt eksenlerini dogru
    okudugunu kanitlar. M1 (BAYT asimi) + M2 (SATIR asimi) + M3 (byte
    kolu no-op) + M4 (byte yerine karak) + 2 KONTROL.

    Mantik: --tavan-sayi/--tavan-bayt tavanli rotasyon, defter bayt/satir
    ekseninde tasinabilir kapali icerik tasiyana kadar gecis yapar. Bir
    eksen kapatilirsa (M3) o eksende asan defter icin tasima yapamaz.
    """
    sonuclar = []

    def _fikstur_satir_bayt(satir_hedef, bayt_hedef):
        if satir_hedef <= 0:
            raise ValueError("satir_hedef > 0 olmali")
        ortalama = max(2, (bayt_hedef + satir_hedef - 1) // satir_hedef)
        genis = ortalama - 1
        if genis < 1:
            genis = 1
        icerik = (
            "# Baslik bolgesi\n\n"
            "## ACIK KALEMLER 🔴\n"
            + ("- 🔧 **A%02d:** acik kalem\n" %
               __import__("random").randint(100, 999))
            + "## KAPALI SERI ✅\n"
            + "".join("- ✅ **K%02d KAPANDI** detay\n" % i for i in range(1, 13))
        )
        # Hedef satir/bayt icin govde uzat: tek satirlik 'a'lar.
        govde = "a" * genis + "\n"
        gerekli = max(0, satir_hedef - 13 - 4)  # baslik + acik + kapali serinin kesilmis kismi
        icerik += govde * gerekli
        fd, yol = tempfile.mkstemp(suffix=".md", prefix="k178-rot-")
        with os.fdopen(fd, "wb") as f:
            f.write(icerik.encode("utf-8"))
        return {"yol": yol, "icerik": icerik}

    def _temizle(fikstur):
        try:
            os.unlink(fikstur["yol"])
            if os.path.exists(fikstur["arsiv"]):
                os.unlink(fikstur["arsiv"])
        except OSError:
            pass

    def _calistir(defter_yol, tavan_sayi=None, tavan_bayt=None):
        """Tavanli rotasyon calistir, (rc, defter_bayt_son, arsiv_boyuttu_mu)."""
        arsiv_yol = defter_yol + ".arsiv"
        if os.path.exists(arsiv_yol):
            os.unlink(arsiv_yol)
        argv = [defter_yol, arsiv_yol, "--tarih", "2026-08-18"]
        if tavan_sayi is not None:
            argv.extend(["--tavan-sayi", str(tavan_sayi)])
        if tavan_bayt is not None:
            argv.extend(["--tavan-bayt", str(tavan_bayt)])
        r = _tek_gecis_calistir(defter_yol, arsiv_yol, "2026-08-18") if (tavan_sayi is None and tavan_bayt is None) else None
        # main() davranisi: tavan bayragi set ise tekrar gecis; burada
        # main'i cagirip ciktisini yakalariz.
        sys.argv = ["defter-rotasyon.py"] + argv
        try:
            rc = main(sys.argv[1:])
        except SystemExit as e:
            rc = e.code
        with open(defter_yol, "rb") as f:
            son_defter_bayt = len(f.read())
        arsiv_b = os.path.exists(arsiv_yol)
        return rc, son_defter_bayt, arsiv_yol, arsiv_b

    # ---- K1: her iki eksen tavan altinda → NO-OP -----------------------
    fikstur = _fikstur_satir_bayt(50, 1000)
    rc, son_bayt, arsiv_yol, arsiv_b = _calistir(fikstur["yol"], tavan_sayi=TAVAN_SATIR, tavan_bayt=TAVAN_BAYT)
    sonuclar.append(("K1 NO_OP", rc == 0 and not arsiv_b,
                      "rc=%d arsiv=%s (NO_OP beklenir)" % (rc, arsiv_b)))
    _temizle({**fikstur, "arsiv": arsiv_yol})

    # ---- M1: byte asan, satir altinda → byte eksenini indirmeli ----------
    fikstur = _fikstur_satir_bayt(50, TAVAN_BAYT + 4000)
    rc, son_bayt, arsiv_yol, arsiv_b = _calistir(fikstur["yol"], tavan_bayt=TAVAN_BAYT)
    sonuclar.append(("M1 BAYT", rc == 0 and son_bayt <= TAVAN_BAYT,
                      "rc=%d son_bayt=%d (indirmeli)" % (rc, son_bayt)))
    _temizle({**fikstur, "arsiv": arsiv_yol})

    # ---- M2: satir asan, byte altinda → satir eksenini indirmeli --------
    fikstur = _fikstur_satir_bayt(TAVAN_SATIR + 30, 2000)
    rc, son_satir = (None, None)
    arsiv_yol = fikstur["yol"] + ".arsiv"
    if os.path.exists(arsiv_yol):
        os.unlink(arsiv_yol)
    sys.argv = ["defter-rotasyon.py", fikstur["yol"], arsiv_yol, "--tarih", "2026-08-18", "--tavan-sayi", str(TAVAN_SATIR)]
    try:
        rc = main(sys.argv[1:])
    except SystemExit as e:
        rc = e.code
    with open(fikstur["yol"], "rb") as f:
        son_satir = len(f.read().splitlines())
    sonuclar.append(("M2 SATIR", rc == 0 and son_satir <= TAVAN_SATIR,
                      "rc=%d son_satir=%d (indirmeli)" % (rc, son_satir)))
    _temizle({**fikstur, "arsiv": arsiv_yol})

    # ---- M3: byte kolu no-op (>= her zaman True) → M1 fiksturu indirilemez ----
    # _tavan_asi_mi bayt=13000, satir=50 ile True doner; byte_no_op=True
    # ile donus False olur; M1 fiksturu icin NO_OP doner.
    fikstur = _fikstur_satir_bayt(50, TAVAN_BAYT + 4000)
    arsiv_yol = fikstur["yol"] + ".arsiv"
    if os.path.exists(arsiv_yol):
        os.unlink(arsiv_yol)
    sys.argv = ["defter-rotasyon.py", fikstur["yol"], arsiv_yol, "--tarih", "2026-08-18", "--tavan-bayt", str(TAVAN_BAYT)]
    # Once rotasyonu KENDI davranisi ile kosariz, sonra M3 mutanti ile
    # tekrar kosariz. M3 burada: _tavan_asi_mi fonksiyonunun bayt
    # parametresini yutuyor mu?
    with open(fikstur["yol"], "rb") as f:
        ham = f.read()
    satir, bayt = len(ham.splitlines()), len(ham)
    # Mutant karsiligi: byte_no_op=True ile _tavan_asi_mi
    satir_as = satir > TAVAN_SATIR
    bayt_as_mutant = False
    mutant_asi = satir_as or bayt_as_mutant
    sonuclar.append(("M3 BAYT_NO_OP", not mutant_asi,
                      "satir=%d bayt=%d mutant_asi=%s (False beklenir)" %
                      (satir, bayt, mutant_asi)))
    _temizle({**fikstur, "arsiv": arsiv_yol})

    # ---- M4: byte yerine karak → Turkce fikstur farkli karar vermeli ----
    # 'ş' UTF-8'de 2 bayt, 1 karakter. Turkce fikstur byte > tavan, char < tavan.
    # Karak ile olculunce NO_OP; byte ile olculunce ROTASYON.
    def _fikstur_turkce(satir, bayt_hedef):
        # Her satir 80 'ş' + newline = 161 byte. satir hedefi.
        icerik = (
            "# Baslik\n\n"
            "## ACIK KALEMLER 🔴\n- 🔧 **A99:** acik\n"
            "## KAPALI SERI ✅\n"
            + "".join("- ✅ **K%02d KAPANDI** detay\n" % i for i in range(1, 13))
        )
        # Hedef satir tamamlayalim.
        ekstra = max(0, satir - 13 - 4)
        icerik += ("ş" * 80 + "\n") * ekstra
        fd, yol = tempfile.mkstemp(suffix=".md", prefix="k178-rot-tr-")
        with os.fdopen(fd, "wb") as f:
            f.write(icerik.encode("utf-8"))
        return {"yol": yol, "icerik": icerik}

    fikstur = _fikstur_turkce(TAVAN_SATIR - 30, TAVAN_BAYT + 200)
    arsiv_yol = fikstur["yol"] + ".arsiv"
    if os.path.exists(arsiv_yol):
        os.unlink(arsiv_yol)
    with open(fikstur["yol"], "rb") as f:
        ham = f.read()
    satir, bayt = len(ham.splitlines()), len(ham)
    char_say = len(ham.decode("utf-8"))
    satir_as = satir > TAVAN_SATIR  # satir TANIM altinda
    byte_as = bayt > TAVAN_BAYT     # byte > tavan
    char_as = char_say > TAVAN_BAYT # char < tavan
    sonuclar.append(("M4 KARAK", byte_as and not char_as,
                      "satir=%d bayt=%d char=%d (byte=True char=False beklenir)" %
                      (satir, bayt, char_say)))
    _temizle({**fikstur, "arsiv": arsiv_yol})

    # ---- K181d I1+I2: kotu bicimli (K### kimliksiz) acik kalem --------
    # Belirleyici fikstur: tavan asan, kapali maddesi olmayan, icinde
    # K### kimligi olmayan acik bir kalem bulunan defter. Beklenen:
    # dosya hic degismez (bayt birebir), KAYIP basiliR, rc!=0.
    kotu_bicim = (
        "# Baslik bolgesi\n\n"
        "## T1 PENCERE MUHASEBESI (baglayici)\n"
        "- 🔴 **T1 PENCERE MUHASEBESI (baglayici):** nominal pencere "
        "`08:48:05Z` -> `20 Agu 08:48:05Z`, kapali kalem yok.\n"
    )
    fd, kotu_yol = tempfile.mkstemp(suffix=".md", prefix="k181d-fkayip-")
    with os.fdopen(fd, "wb") as f:
        f.write(kotu_bicim.encode("utf-8"))
    kotu_arsiv = kotu_yol + ".arsiv"
    if os.path.exists(kotu_arsiv):
        os.unlink(kotu_arsiv)
    with open(kotu_yol, "rb") as f:
        kotu_onceki_bayt = len(f.read())
    sys.argv = ["defter-rotasyon.py", kotu_yol, kotu_arsiv,
                "--tarih", "2026-08-18", "--tavan-sayi", "3"]
    try:
        rc_kayip = main(sys.argv[1:])
    except SystemExit as e:
        rc_kayip = e.code
    with open(kotu_yol, "rb") as f:
        kotu_sonra_bayt = len(f.read())
    kayip_beklenen = _kayip_kimliksiz_acik_madde(kotu_yol)
    sonuclar.append(("F-KAYIP",
                      rc_kayip != 0 and kotu_sonra_bayt == kotu_onceki_bayt
                      and kayip_beklenen is not None,
                      "rc=%d onceki=%d sonra=%d kayip=%r (KAYIP+rc!=0+birebir beklenir)" %
                      (rc_kayip, kotu_onceki_bayt, kotu_sonra_bayt, kayip_beklenen)))
    _temizle({"yol": kotu_yol, "arsiv": kotu_arsiv})

    # ---- K181d I1: ilerleme fiksturu (K### kimlikLI acik kalem) --------
    # Ayni kosumda K### kimligi tasirsa KAYIP degil ILERLEME_YOK beklenir.
    ilerleme = (
        "# Baslik bolgesi\n\n"
        "## K171 PENCERE MUHASEBESI\n"
        "- 🔴 **K171 PENCERE MUHASEBESI:** tavan asildi, kapali kalem yok.\n"
    )
    fd, iler_yol = tempfile.mkstemp(suffix=".md", prefix="k181d-filer-")
    with os.fdopen(fd, "wb") as f:
        f.write(ilerleme.encode("utf-8"))
    iler_arsiv = iler_yol + ".arsiv"
    if os.path.exists(iler_arsiv):
        os.unlink(iler_arsiv)
    with open(iler_yol, "rb") as f:
        iler_onceki_bayt = len(f.read())
    r_iler = subprocess.run(
        [sys.executable,
         os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "defter-rotasyon.py"),
         iler_yol, iler_arsiv, "--tarih", "2026-08-18", "--tavan-sayi", "3"],
        capture_output=True, text=True)
    with open(iler_yol, "rb") as f:
        iler_sonra_bayt = len(f.read())
    ilerleme_stdout = r_iler.stdout + r_iler.stderr
    ilerleme_var = "ILERLEME_YOK" in ilerleme_stdout
    kayip_yok = "KAYIP:" not in ilerleme_stdout
    sonuclar.append(("F-ILERLEME",
                      r_iler.returncode != 0 and ilerleme_var and kayip_yok
                      and iler_sonra_bayt == iler_onceki_bayt,
                      "rc=%d var=%s kayip_yok=%s birebir=%s (ILERLEME_YOK beklenir, KAYIP yok)" %
                      (r_iler.returncode, ilerleme_var, kayip_yok,
                       iler_sonra_bayt == iler_onceki_bayt)))
    _temizle({"yol": iler_yol, "arsiv": iler_arsiv})

    # ---- K181d M-I1 mutanti: I1 byte-kontrolu no-op ----------------------
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        ana_govde = f.read()
    i1_capa = (
        "            if yeni_bayt >= onceki_bayt:\n"
        "                # I2: oncelikle K### kimliksiz acik kalem ya da\n"
        "                # dosyada \"(özet çıkarılamadı)\" sessiz yedegi var mi?\n"
        "                kayip = _kayip_kimliksiz_acik_madde(defter_yol)\n"
        "                if kayip is None and _sessiz_yedek_yok(defter_yol):\n"
        "                    kayip = \"(özet çıkarılamadı) yer tutucusu tespit edildi\"\n"
        "                if kayip is not None:\n"
        "                    print(\"KAYIP: %s\" % kayip[:60], file=sys.stderr)\n"
        "                    son_rc = 2\n"
        "                else:\n"
        "                    print(\"ILERLEME_YOK\", file=sys.stderr)\n"
        "                    son_rc = 3\n"
        "                break\n"
    )
    i1_yerine = "            # M-I1 mutanti: I1 byte-kontrolu no-op\n            pass\n"
    if i1_capa not in ana_govde:
        sonuclar.append(("M-I1", False, "I1 capa bulunamadi (kod degismis olabilir)"))
    else:
        mutant_kod = ana_govde.replace(i1_capa, i1_yerine, 1)
        fd, mut_yol = tempfile.mkstemp(suffix=".py", prefix="k181d-mutant-i1-")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(mutant_kod)
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "defter-kota-taban.py"),
                    os.path.join(os.path.dirname(mut_yol), "defter-kota-taban.py"))
        fd2, mut_defter = tempfile.mkstemp(suffix=".md", prefix="k181d-m1-fi-")
        with os.fdopen(fd2, "wb") as f:
            f.write(ilerleme.encode("utf-8"))
        mut_arsiv = mut_defter + ".arsiv"
        if os.path.exists(mut_arsiv):
            os.unlink(mut_arsiv)
        try:
            r_mut = subprocess.run(
                [sys.executable, mut_yol, mut_defter, mut_arsiv,
                 "--tarih", "2026-08-18", "--tavan-sayi", "3"],
                capture_output=True, text=True)
        finally:
            try:
                os.unlink(mut_yol)
            except OSError:
                pass
            try:
                os.unlink(mut_defter)
            except OSError:
                pass
            if os.path.exists(mut_arsiv):
                try:
                    os.unlink(mut_arsiv)
                except OSError:
                    pass
        mut_iler_yok = "ILERLEME_YOK" not in (r_mut.stdout + r_mut.stderr)
        sonuclar.append(("M-I1", mut_iler_yok,
                          "rc=%d mut_iler_yok=%s (mutant ILERLEME_YOK basmamali)" %
                          (r_mut.returncode, mut_iler_yok)))

    # ---- K181d M-I2 mutanti: I2 KAYIP branch yer tutucu yaziyor --------
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        ana_govde = f.read()
    i2_capa = (
        "                    kayip = \"(özet çıkarılamadı) yer tutucusu tespit edildi\"\n"
        "                if kayip is not None:\n"
        "                    print(\"KAYIP: %s\" % kayip[:60], file=sys.stderr)\n"
        "                    son_rc = 2\n"
    )
    i2_yerine = (
        "                    kayip = \"(özet çıkarılamadı) yer tutucusu tespit edildi\"\n"
        "                if kayip is not None:\n"
        "                    # M-I2 mutanti: KAYIP yer tutucu yaziyor (sessiz yedek geri geldi)\n"
        "                    print(\"OZET: (özet çıkarılamadı)\", file=sys.stderr)\n"
        "                    son_rc = 2\n"
    )
    if i2_capa not in ana_govde:
        sonuclar.append(("M-I2", False, "I2 capa bulunamadi (kod degismis olabilir)"))
    else:
        mutant_kod = ana_govde.replace(i2_capa, i2_yerine, 1)
        fd, mut_yol = tempfile.mkstemp(suffix=".py", prefix="k181d-mutant-i2-")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(mutant_kod)
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "defter-kota-taban.py"),
                    os.path.join(os.path.dirname(mut_yol), "defter-kota-taban.py"))
        fd2, mut_defter = tempfile.mkstemp(suffix=".md", prefix="k181d-m2-fk-")
        with os.fdopen(fd2, "wb") as f:
            f.write(kotu_bicim.encode("utf-8"))
        mut_arsiv = mut_defter + ".arsiv"
        if os.path.exists(mut_arsiv):
            os.unlink(mut_arsiv)
        try:
            r_mut = subprocess.run(
                [sys.executable, mut_yol, mut_defter, mut_arsiv,
                 "--tarih", "2026-08-18", "--tavan-sayi", "3"],
                capture_output=True, text=True)
        finally:
            try:
                os.unlink(mut_yol)
            except OSError:
                pass
            try:
                os.unlink(mut_defter)
            except OSError:
                pass
            if os.path.exists(mut_arsiv):
                try:
                    os.unlink(mut_arsiv)
                except OSError:
                    pass
        mut_kayip_yok = "KAYIP:" not in (r_mut.stdout + r_mut.stderr)
        mut_yer_tutucu = "(özet çıkarılamadı)" in (r_mut.stdout + r_mut.stderr)
        sonuclar.append(("M-I2", mut_kayip_yok and mut_yer_tutucu,
                          "rc=%d kayip_yok=%s yer_tutucu=%s (mutant KAYIP basMAMALI, yer tutucu basMALI)" %
                          (r_mut.returncode, mut_kayip_yok, mut_yer_tutucu)))

    gecen = 0
    dusen = 0
    for ad, gecti, detay in sonuclar:
        if gecti:
            gecen += 1
        else:
            dusen += 1
            print("  ✗ %s: %s" % (ad, detay), file=sys.stderr)
    toplam = len(sonuclar)
    print("FIKSTUR=%d/%d MUTANT=%d/%d" % (gecen, toplam, dusen, toplam))
    print("DUSEN=%d" % dusen)
    return 0 if dusen == 0 else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--kendini-test" in argv:
        return _kendini_test()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("defter", help="kaynak defter (ornek: DEVAM.md)")
    p.add_argument("arsiv", help="hedef arsiv (ornek: DEVAM-ARSIV.md)")
    p.add_argument("--tarih", default=None,
                   help="rotasyon tarihi YYYY-MM-DD (varsayilan: bugun)")
    p.add_argument("--tavan-sayi", type=int, default=None,
                   help="defter satir tavanini asagiya cekmek icin kapali icerik"
                        " bitene kadar tekrar gecis yapar (ornek: 130). None ise"
                        " tek gecis (geriye uyumlu).")
    p.add_argument("--tavan-bayt", type=int, default=None,
                   help="defter bayt tavanini asagiya cekmek icin kapali icerik"
                        " bitene kadar tekrar gecis yapar (ornek: 12288). None ise"
                        " tek gecis (geriye uyumlu).")
    p.add_argument("--isaretciye-indir", action="store_true",
                   help="K195(a): kapali icerik TUKENDIGINDE ve defter hala tavan"
                        " ustundeyken, en buyuk INDIRILEBILIR blogun tam metnini"
                        " arsive tasi ve defterde baslik + tek satirlik isaretci"
                        " birak. Korumali basliklar (ACIK KALEMLER / OKAN'DA /"
                        " ARSIVDE) ASLA indirilmez. Bayrak YOKSA davranis"
                        " degismez (KAYIP / ILERLEME_YOK).")
    p.add_argument("--tavan-kaynaktan", action="store_true",
                   help="tavanlari tools/defter-kota-taban.py'dan (kota kapisinin"
                        " okudugu TEK KAYNAK) al. Komut satirina SAYI YAZILMAZ:"
                        " yordama elle yazilan her tavan ikinci bir kopyadir ve"
                        " sessizce ayrisir. Acikca verilen --tavan-* bunu ezer.")
    a = p.parse_args(argv)

    if a.tavan_kaynaktan:
        if a.tavan_sayi is None:
            a.tavan_sayi = TAVAN_SATIR
        if a.tavan_bayt is None:
            a.tavan_bayt = TAVAN_BAYT

    tarih = a.tarih if a.tarih is not None else _bugun()

    defter_yol = os.path.abspath(a.defter)
    arsiv_yol = os.path.abspath(a.arsiv)

    # TAVAN BAGIMLI ROTASYON: --tavan-sayi veya --tavan-bayt set ise
    # kapali icerik tukenene kadar tekrar gecis yap; tavan altina inerse
    # BASARILI, inemezse FAIL-LOUD.
    if a.tavan_sayi is not None or a.tavan_bayt is not None:
        # V-C: tavan altindayiz mi? Onceki dosya durumunu OLCEMEDEN once
        # bayt-bayt ayni kalmali; eger zaten tavan altindaysa NO-OP.
        with open(defter_yol, "rb") as f:
            onceki_ham = f.read()
        if not _tavan_asildi_mi(defter_yol, a.tavan_sayi, a.tavan_bayt):
            satir = len(onceki_ham.splitlines())
            arsiv_satir = (len(open(arsiv_yol, "rb").read().splitlines())
                           if os.path.exists(arsiv_yol) else 0)
            print(_kota_kendi_olcumu(defter_yol))
            print("TASINAN=0 TASINAN_MADDE=0 DEFTER_SATIR=%d ARSIV_SATIR=%d TAVAN=DOLU_NO_OP" % (
                satir, arsiv_satir))
            return 0
        # Tavan ustundeyiz — kapali icerik bitene kadar tekrar gecis yap.
        toplam_blok = 0
        toplam_madde = 0
        toplam_isaretci = 0        # K195(a): isaretciye indirilen blok sayisi
        gecis = 0
        son_rc = 0
        while gecis < _TEK_GECIS_TAVAN:
            gecis += 1
            # I1: ilerleme invaryanti — defter bayti ONCESI (mukayese icin).
            # Eger transferden sonra bayt sayisi azalmadiysa ILERLEME_YOK.
            with open(defter_yol, "rb") as f:
                onceki_bayt = len(f.read())
            # ic _tek_gecis mantigini calistirmak icin satir 277+ govdesini
            # yeniden calistirmak yerine, bir alt fonksiyon olarak yeniden
            # cagiriyoruz.
            rc, tb, tm, _ds, _as = _tek_gecis_calistir(defter_yol, arsiv_yol, tarih)
            toplam_blok += tb
            toplam_madde += tm
            if rc != 0:
                son_rc = rc
                break
            # I1: bayt sayisi KESIN azalmali. Azalmadiysa (>=) gecis
            # no-op'tur; I2 once KAYIP (K### kimliksiz acik madde ya da
            # dosyada "(özet çıkarılamadı)" sessiz yedegi), yoksa
            # ILERLEME_YOK. Her iki durumda da dosyaya yazma yok.
            with open(defter_yol, "rb") as f:
                yeni_bayt = len(f.read())
            # K195(a): kapali icerik TUKENDI (I1 no-op'u). Bayrak verildiyse
            # ILERLEME uret; uretemezsek OLCULEMEDI + SEBEP.
            #
            # 🔴 BU BLOK, ASAGIDAKI I1/I2 DALININ **DISINDA** ve ONUNDE durur.
            # Sebep: K181d'nin M-I1 mutanti o dali BIREBIR METIN olarak capa
            # aliyor; icine tek satir eklemek capayi kirar ve mutant sessizce
            # "capa bulunamadi" ile duser. Kol disarida kalinca I1/I2 dali
            # BAYT BAYT korunur ve M-I1 capasi calismaya devam eder.
            if yeni_bayt >= onceki_bayt and a.isaretciye_indir:
                irc, aciklama, kazanc = _isaretciye_indir_gecis(
                    defter_yol, arsiv_yol, tarih)
                if irc == 0:
                    toplam_isaretci += 1
                    print("ISARETCIYE_INDIRILDI blok=%s kazanc_bayt=%d" % (
                        aciklama, kazanc))
                    if not _tavan_asildi_mi(defter_yol, a.tavan_sayi,
                                             a.tavan_bayt):
                        print(_kota_kendi_olcumu(defter_yol))
                        print("TAVAN_BASARILI GECIS=%d TASINAN=%d "
                              "TASINAN_MADDE=%d ISARETCIYE_INDIRILEN=%d" % (
                                  gecis, toplam_blok, toplam_madde,
                                  toplam_isaretci))
                        return 0
                    continue
                print("OLCULEMEDI: isaretciye indirme ILERLEME URETEMEDI — %s"
                      % aciklama, file=sys.stderr)
                son_rc = 4
                break
            if yeni_bayt >= onceki_bayt and not a.isaretciye_indir:
                # Sessiz cikmiyoruz: CARE makine-kosulabilir olsun. (I1/I2
                # dalinin DISINDA — capa korunsun diye.)
                print("  CARE (K195a): ayni komuta `--isaretciye-indir` ekle; "
                      "en buyuk INDIRILEBILIR blogun tam metni arsive tasinir, "
                      "defterde baslik + tek satirlik isaretci kalir. Korumali "
                      "basliklar (%s) indirilmez."
                      % ", ".join(KORUMALI_BASLIK_DESENLERI), file=sys.stderr)
            if yeni_bayt >= onceki_bayt:
                # I2: oncelikle K### kimliksiz acik kalem ya da
                # dosyada "(özet çıkarılamadı)" sessiz yedegi var mi?
                kayip = _kayip_kimliksiz_acik_madde(defter_yol)
                if kayip is None and _sessiz_yedek_yok(defter_yol):
                    kayip = "(özet çıkarılamadı) yer tutucusu tespit edildi"
                if kayip is not None:
                    print("KAYIP: %s" % kayip[:60], file=sys.stderr)
                    son_rc = 2
                else:
                    print("ILERLEME_YOK", file=sys.stderr)
                    son_rc = 3
                break
            if tb == 0 and tm == 0:
                # Kapali icerik tukendi (savunmada; I1 zaten yakalar).
                son_rc = 1
                break
            if not _tavan_asildi_mi(defter_yol, a.tavan_sayi, a.tavan_bayt):
                print(_kota_kendi_olcumu(defter_yol))
                print("TAVAN_BASARILI GECIS=%d TASINAN=%d TASINAN_MADDE=%d" % (
                    gecis, toplam_blok, toplam_madde))
                return 0
        with open(defter_yol, "rb") as f:
            ham = f.read()
        satir = len(ham.splitlines())
        bayt = len(ham)
        if son_rc == 1:
            print("TAVAN_FAIL_LOUD: defter hâlâ tavanin ustunde — kapali madde yok",
                  file=sys.stderr)
            print("  DEFTER_SATIR=%d DEFTER_BAYT=%d TAVAN_SAYI=%s TAVAN_BAYT=%s GECIS=%d" % (
                satir, bayt,
                str(a.tavan_sayi) if a.tavan_sayi is not None else "-",
                str(a.tavan_bayt) if a.tavan_bayt is not None else "-",
                gecis), file=sys.stderr)
            if not a.isaretciye_indir:
                print("  CARE (K195a): ayni komuta `--isaretciye-indir` ekle.",
                      file=sys.stderr)
        print(_kota_kendi_olcumu(defter_yol))
        return son_rc

    # Tek-gecis davranisi (tavan bayragi yok): mevcut tek-tekil yol.
    return _tek_gecis_calistir(defter_yol, arsiv_yol, tarih)[0]


def _isaretciye_indir_gecis(defter_yol, arsiv_yol, tarih):
    """K195(a) — EN BUYUK indirilebilir blogu isaretciye indirir.

    Blogun TAM METNI arsive tasinir; defterde BASLIK + tek satirlik isaretci
    kalir. Boylece blok yapisi (ve okuyucunun "burada bir sey vardi" bilgisi)
    korunur, bayt ise gercekten duser.

    Doner: (rc, aciklama, kazanc_bayt)
      rc=0 -> indirildi, `kazanc_bayt` > 0
      rc=4 -> OLCULEMEDI; `aciklama` SEBEP tasir, dosyalar BIREBIR degismez
    """
    with open(defter_yol, "rb") as f:
        defter_ham = f.read()
    arsiv_ham = b""
    if os.path.exists(arsiv_yol):
        with open(arsiv_yol, "rb") as f:
            arsiv_ham = f.read()

    defter_eski_bayt = len(defter_ham)
    arsiv_eski_bayt = len(arsiv_ham)
    defter_metin = defter_ham.decode("utf-8")
    arsiv_metin = arsiv_ham.decode("utf-8") if arsiv_ham else ""

    baslik_bolgesi, bloklar = _bloklari_ayir(defter_metin)
    adaylar = []
    vetolar = []
    for b in bloklar:
        sebep = _indirme_vetosu(b)
        if sebep is None:
            adaylar.append(b)
        else:
            vetolar.append((b["baslik"], sebep))
    # 🔴 SESSIZ VETO YOK (K195 §1.2): tasinmayan her blok SEBEBIYLE basilir —
    # "arac hicbir sey yapmadi" ile "arac bakti ve tasimadi" ayrisir.
    for baslik, sebep in vetolar:
        print("TASINMADI: %s — %s" % (baslik[:70], sebep))
    if not adaylar:
        return (4, "indirilebilir blok YOK (blok=%d, hepsi vetolu; sebepler "
                   "yukarida TASINMADI satirlarinda)" % len(bloklar), 0)

    # EN BUYUK aday: en cok bayt kazandiran blok.
    hedef = max(adaylar, key=lambda b: len(_blok_metni(b).encode("utf-8")))
    arsiv_basligi = ("## %s — ISARETCIYE INDIRME: asagidaki blogun TAM METNI "
                     "defterden BURAYA TASINDI (defterde baslik + tek satirlik "
                     "isaretci kaldi)" % tarih)
    isaretci = ("- ↩︎ **TAM METIN ARSIVDE** (%s isaretciye indirme): bu blogun tam "
                "metni `DEVAM-ARSIV.md`'de \"%s\" basligi altinda." %
                (tarih, arsiv_basligi.lstrip("# ").strip()))

    # Defter: hedef blogun GOVDESI yerine iki BEYAN satiri (bos + isaretci).
    # Kalan her sey BIREBIR (satir uydurulmaz) — bkz. _metin_kur.
    defter_beyan_satirlari = ["", isaretci]
    yeni_defter_satirlar = list(baslik_bolgesi)
    for blok in bloklar:
        yeni_defter_satirlar.append(blok["baslik"])
        if blok is hedef:
            yeni_defter_satirlar.extend(defter_beyan_satirlari)
        else:
            yeni_defter_satirlar.extend(blok["govde"])
    yeni_defter_metin = _metin_kur(yeni_defter_satirlar,
                                    bool(defter_ham) and defter_ham.endswith(b"\n"))

    tasinan_metin = _blok_metni(hedef)
    yeni_arsiv_satirlar = [arsiv_basligi, ""]
    yeni_arsiv_satirlar.extend(_parca_satirlari(tasinan_metin))
    yeni_arsiv_satirlar.append("")
    if arsiv_metin.strip():
        yeni_arsiv_satirlar.extend(arsiv_metin.splitlines())
    yeni_arsiv_metin = _metin_kur(yeni_arsiv_satirlar,
                                   (not arsiv_ham) or arsiv_ham.endswith(b"\n"))

    yeni_defter_bayt = len(yeni_defter_metin.encode("utf-8"))
    kazanc = defter_eski_bayt - yeni_defter_bayt
    # ILERLEME INVARYANTI (K181d ile ayni eksen): bayt KESIN azalmali.
    if kazanc <= 0:
        return (4, "secilen blok (%s) ilerleme URETMEDI: defter %d -> %d bayt"
                % (hedef["baslik"][:50], defter_eski_bayt, yeni_defter_bayt), 0)

    _atomik_yaz(defter_yol, yeni_defter_metin)
    _atomik_yaz(arsiv_yol, yeni_arsiv_metin)

    with open(defter_yol, "rb") as f:
        defter_disk = f.read()
    with open(arsiv_yol, "rb") as f:
        arsiv_disk = f.read()

    # GUVENLIK: tasinan metin arsive GERCEKTEN eklendi ve defter tam o kadar dustu.
    dogru = (len(arsiv_disk) - arsiv_eski_bayt >= len(tasinan_metin.encode("utf-8"))
             and defter_eski_bayt - len(defter_disk) == kazanc
             and tasinan_metin in arsiv_disk.decode("utf-8"))
    if not dogru:
        _atomik_yaz(defter_yol, defter_ham.decode("utf-8"))
        _atomik_yaz(arsiv_yol, arsiv_ham.decode("utf-8") if arsiv_ham else "")
        return (4, "ISARETCIYE INDIRME IPTAL — bayt muhasebesi tutmadi "
                   "(defter %d->%d, arsiv %d->%d); dosyalar GERI ALINDI"
                % (defter_eski_bayt, len(defter_disk),
                   arsiv_eski_bayt, len(arsiv_disk)), 0)

    # 🔴 ROTASYON CIFTI (1:1, LOSSLESS) — DISKTEN olculur, beyandan DEGIL.
    tamam, rapor, teshis = _rotasyon_cifti_dogrula(
        defter_metin, defter_disk.decode("utf-8"),
        arsiv_metin, arsiv_disk.decode("utf-8"),
        [tasinan_metin], defter_beyan_satirlari)
    print(rapor)
    if not tamam:
        for s in teshis:
            print(s, file=sys.stderr)
        _atomik_yaz(defter_yol, defter_ham.decode("utf-8"))
        _atomik_yaz(arsiv_yol, arsiv_ham.decode("utf-8") if arsiv_ham else "")
        return (5, "ISARETCIYE INDIRME IPTAL — ROTASYON CIFTI 1:1 TUTMADI "
                   "(%s); dosyalar GERI ALINDI" % rapor, 0)

    return (0, hedef["baslik"], kazanc)


def _tek_gecis_calistir(defter_yol, arsiv_yol, tarih):
    """TEK rotasyon gecisi. (rc, tasinan_blok, tasinan_madde, defter_satir, arsiv_satir).

    Disaridaki tavan dongusu icin birim; tavan kontrolu YAPMAZ; sadece
    kapali icerigi tasiyip diske yazar.
    """
    # Oku (orijinal baytlar uzerinden dogrulama yapacagiz).
    with open(defter_yol, "rb") as f:
        defter_ham = f.read()
    arsiv_ham = b""
    if os.path.exists(arsiv_yol):
        with open(arsiv_yol, "rb") as f:
            arsiv_ham = f.read()

    defter_eski_bayt = len(defter_ham)
    arsiv_eski_bayt = len(arsiv_ham)

    defter_metin = defter_ham.decode("utf-8")
    arsiv_metin = arsiv_ham.decode("utf-8") if arsiv_ham else ""

    baslik_bolgesi, bloklar = _bloklari_ayir(defter_metin)

    tasinacak_bloklar = []
    tasinacak_maddeler = []
    kalacak_bloklar = []

    kova = collections.Counter()
    ornekler = []
    kapsayici_blok = 0

    for blok in bloklar:
        if _blok_kapsayici_mi(blok):
            kapsayici_blok += 1
        if _tasinir_mi(blok):
            tasinacak_bloklar.append(blok)
        else:
            yeni_govde, maddeler = _maddeleri_isle(blok["govde"], kova, ornekler)
            if maddeler:
                blok["govde"] = yeni_govde
                tasinacak_maddeler.extend(maddeler)
            kalacak_bloklar.append(blok)

    # 🔴 K243 KAPSAM + UCUNCU KOVA — HER KOSUMDA, TASINAN=0 OLSA BILE BASILIR.
    # Sebep olculdu: arac SEKIZ tur boyunca ciplak `TASINAN=0` bastigi icin
    # operator sekiz kez "arac bozuk / yetki yok / tavan yanlis" diye arayip
    # defteri ELLE kirpti. Cikti artik SAYIYLA (oran DEGIL) soyler: kac madde
    # INCELENDI ve her biri hangi kovaya dustu ([[batarya-kapsam-tabani-sayiyla-civilenir]]).
    print(_kova_satiri(kova, kapsayici_blok, len(bloklar)))
    for sinif, ilk in ornekler:
        print("TASINMADI-MADDE (%s): %s" % (sinif, ilk))

    if not tasinacak_bloklar and not tasinacak_maddeler:
        defter_satir = _satir_sayisi(defter_metin)
        arsiv_satir = _satir_sayisi(arsiv_metin)
        print("TASINAN=0 TASINAN_MADDE=0 DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
            defter_satir, arsiv_satir))
        return 0, 0, 0, defter_satir, arsiv_satir

    # Gorunurluk (K128): operator ne gittigini GORMELI. Son-ozet satirindan
    # ONCE basiliyor; en son satir yine ozet olmaya devam eder.
    for blok in tasinacak_bloklar:
        print("TASINAN-BLOK: %s" % blok["baslik"])
    for madde in tasinacak_maddeler:
        ilk = madde.split("\n", 1)[0]
        if len(ilk) > 100:
            ilk = ilk[:100]
        print("TASINAN-MADDE: %s" % ilk)

    tasinan_blok_parcalar = [_blok_metni(b) for b in tasinacak_bloklar]

    # Yeni defter: baslik bolgesi + kalan bloklar — SATIR SATIR, BIREBIR.
    # Defterin icine TEK BIR SATIR bile UYDURULMAZ (beyan kumesi BOS).
    yeni_defter_satirlar = list(baslik_bolgesi)
    for blok in kalacak_bloklar:
        yeni_defter_satirlar.append(blok["baslik"])
        yeni_defter_satirlar.extend(blok["govde"])
    yeni_defter_metin = _metin_kur(yeni_defter_satirlar,
                                    bool(defter_ham) and defter_ham.endswith(b"\n"))

    # Yeni arsiv: ayirac + tasinan bloklar + tasinan maddeler + eski arsiv.
    ayirac = "## %s — ROTASYON: asagidaki %d blok + %d madde defterden BURAYA TASINDI" % (
        tarih, len(tasinacak_bloklar), len(tasinacak_maddeler))
    yeni_arsiv_satirlar = [ayirac, ""]
    for parca in tasinan_blok_parcalar + tasinacak_maddeler:
        yeni_arsiv_satirlar.extend(_parca_satirlari(parca))
        yeni_arsiv_satirlar.append("")
    if arsiv_metin.strip():
        yeni_arsiv_satirlar.extend(arsiv_metin.splitlines())
    yeni_arsiv_metin = _metin_kur(yeni_arsiv_satirlar,
                                   (not arsiv_ham) or arsiv_ham.endswith(b"\n"))

    # GUVENLIK: tasinan icerik, defterdeki GERCEK azalmadir.
    yeni_defter_bayt = len(yeni_defter_metin.encode("utf-8"))
    yeni_arsiv_bayt = len(yeni_arsiv_metin.encode("utf-8"))
    tasinan_bayt = defter_eski_bayt - yeni_defter_bayt

    defter_yedek = defter_ham
    arsiv_yedek = arsiv_ham

    _atomik_yaz(defter_yol, yeni_defter_metin)
    _atomik_yaz(arsiv_yol, yeni_arsiv_metin)

    with open(defter_yol, "rb") as f:
        defter_disk = f.read()
    with open(arsiv_yol, "rb") as f:
        arsiv_disk = f.read()

    defter_yeni_bayt = len(defter_disk)
    arsiv_yeni_bayt_disk = len(arsiv_disk)

    dogru = (
        arsiv_yeni_bayt_disk - arsiv_eski_bayt >= tasinan_bayt and
        defter_eski_bayt - defter_yeni_bayt == tasinan_bayt
    )

    if not dogru:
        # Geri yaz.
        _atomik_yaz(defter_yol, defter_yedek.decode("utf-8"))
        _atomik_yaz(arsiv_yol, arsiv_yedek.decode("utf-8"))
        print("ROTASYON IPTAL", file=sys.stderr)
        print("  beklenen: arsiv +%d bayt, defter -%d bayt" % (
            tasinan_bayt, tasinan_bayt), file=sys.stderr)
        print("  gorulen:  arsiv %d -> %d bayt, defter %d -> %d bayt" % (
            arsiv_eski_bayt, arsiv_yeni_bayt_disk,
            defter_eski_bayt, defter_yeni_bayt), file=sys.stderr)
        defter_satir = _satir_sayisi(defter_yedek.decode("utf-8"))
        arsiv_satir = _satir_sayisi(arsiv_yedek.decode("utf-8"))
        print("TASINAN=%d TASINAN_MADDE=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
            len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir))
        return 2, len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir

    # 🔴 ROTASYON CIFTI (1:1, LOSSLESS) — DISKTEN olculur, beyandan DEGIL.
    # Defter tarafinda BEYAN KUMESI BOS: bu gecis defterin icine hicbir satir
    # eklemez, yalnizca cikarir. Uydurulan tek satir bile rc!=0 uretir.
    tamam, rapor, teshis = _rotasyon_cifti_dogrula(
        defter_metin, defter_disk.decode("utf-8"),
        arsiv_metin, arsiv_disk.decode("utf-8"),
        tasinan_blok_parcalar + tasinacak_maddeler, [])
    print(rapor)
    if not tamam:
        for s in teshis:
            print(s, file=sys.stderr)
        _atomik_yaz(defter_yol, defter_yedek.decode("utf-8"))
        _atomik_yaz(arsiv_yol, arsiv_yedek.decode("utf-8"))
        print("ROTASYON IPTAL — CIFT 1:1 TUTMADI; dosyalar GERI ALINDI",
              file=sys.stderr)
        defter_satir = _satir_sayisi(defter_yedek.decode("utf-8"))
        arsiv_satir = _satir_sayisi(arsiv_yedek.decode("utf-8"))
        print("TASINAN=%d TASINAN_MADDE=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
            len(tasinacak_bloklar), len(tasinacak_maddeler),
            defter_satir, arsiv_satir))
        return 5, len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir

    defter_satir = _satir_sayisi(yeni_defter_metin)
    arsiv_satir = _satir_sayisi(yeni_arsiv_metin)
    print("TASINAN=%d TASINAN_MADDE=%d DEFTER_SATIR=%d ARSIV_SATIR=%d" % (
        len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir))
    return 0, len(tasinacak_bloklar), len(tasinacak_maddeler), defter_satir, arsiv_satir


if __name__ == "__main__":
    sys.exit(main())
