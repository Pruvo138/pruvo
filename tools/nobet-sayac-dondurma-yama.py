#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K341 — ONARIMSIZ SAYACININ DONDURMA KORLUGU (28 Agu 2026, cip KraL-OnarimSayaci-28Agu).

Okan'in 28 Agu 15:10 emrinin 4. kalemi. Hedef dosya `~/.claude/cron/nobet-kapi.py`
(repoda KOPYASI YOKTUR); bu yuzden yama REPODA yasar, kurulu kopyaya UYGULANIR ve
olcum KURULU KOPYADAN yapilir ([[emir-canliligi-kurulu-kopyadan-olculur]]).
Kardes yama: `tools/nobet-uc-kol-yama.py` (K320, 27 Agu).

--------------------------------------------------------------------------
OLCULEN VAKA (iddia degil; 28 Agu 2026, canli dosyalardan okundu)
--------------------------------------------------------------------------
`nobet-onarimsiz-sayac.json` = 154. `gozcu.log` son 20 damgasi 145->154, MONOTON
+1: sayac 3 gundur hic dusmedi (89 -> 129 -> 153/154). Ama ayni turun butun
saglik sinyalleri YESIL:
    HUKUM=DAGITIM_DONDURULDU rc=0
    KOSUM_HUKMU=TEMIZ MOTOR_RC=- TUR_HUKMU=DAGITIM_DONDURULDU
    DONDURMA_ISIRDI=1 ENGELLENEN=4        <-- bayrak GERCEKTEN isirdi
    KAPANAN=0 DAGITILAN=0 ONARIM=0
    ESKALASYON=OKAN USTUSTE_ONARIMSIZ=154 <-- her turda, ANLAMSIZ

--------------------------------------------------------------------------
KOK NEDEN — ARIZA ONARILMADI, YER DEGISTIRDI
--------------------------------------------------------------------------
27 Agu'nun B1 yamasi (`nobet-uc-kol-yama.py`) `DONDURMA_ISIRDI=1` satirina bir
TUKETICI yazdi: `tur_hukmu()` artik bayrak isirdiysa `DAGITIM_DONDURULDU/rc=0`
donuyor. Kirmizi sondu.

🔴 Ama AYNI OLGUNUN IKINCI OKUYUCUSU ogretilmedi. `nobet-kapi.py:2123`:

    ustuste_onarimsiz, _ = tur_sayacini_kaydet(   # B8 TEK KAPI
        "IS_YOK" if kova_bos_hali
        else "KOSTU_ONARDI" if onarim > 0
        else "KOSTU_DUSTU", onarim)

Donmus turda `onarim==0` ve kova BOS DEGIL (acik=27) -> `KOSTU_DUSTU` -> +1.
Yani `tur_hukmu` "bu bir emir" derken, sayac kapisi ayni turu "onarim DENENDI ve
DUSTU" sayiyor. Okan'in DONDURMA emri, hattin KENDI arizasi gibi puanlaniyor —
[[emir-ariza-kovasina-duserse-hat-kendi-kendine-kirmizi-yanar]] (i)'in AYNISI,
bir sonraki tuketicide. Sinif: [[ucuncu-tekrar-sinif-kapisi]] / "onarim yapilirken
tek yon kutsanmaz, DIGER OKUYUCU da ayni turda olculur"
([[defter-durum-sozlugu-onarim-bacagini-korlestirir]] madde 3).

HIPOTEZLER (hepsi olculdu, sadece biri ayakta):
  H1 dagitim kolu kaydi yazmadan donuyor .. CURUDU: kol hic CAGRILMIYOR, cunku
     Okan'in bayragi onu ATLATIYOR (`DONDURULDU@tur984 ... ADAY=4`). Kayit
     "yazilamadi" degil, "yazilmasi YASAK".
  H2 sayaci sifirlayan yuklem baska alan/yol okuyor .. CURUDU: tek yazici
     `ustuste_onarimsiz_guncelle`, tek yol `ONARIMSIZ_SAYAC_YOLU`, tek alan
     `ustuste_onarimsiz`. Ad/yol ekseninde ayrisma YOK.
  H3 `kosum_hukmu=TEMIZ` onarim bacagini kisa devre yaptiriyor .. CURUDU:
     `kosum_hukmu` B5 ekseni AYRIDIR ve `tur_sayacini_kaydet`e HIC girmez
     (`kosum_hukmu_coz` sayaci ne okur ne yazar).
  H4 olcut YANLIS TANIMLI .. 🔴 AYAKTA — ama incelmis haliyle: sayac "onarimsiz
     tur" derken iki AYRI hali tek kovaya atiyor: (a) onarmayi DENEDI, DUSTU
     (b) EMIRLE onarmadi. Care sayaci ELLE SIFIRLAMAK DEGIL, olcutu duzeltmek.

--------------------------------------------------------------------------
DORT KOL
--------------------------------------------------------------------------
E0  `datetime` import edilir (E4 seviye hesabi icin).
E1  `TUR_HALLERI`ne DORDUNCU hal: `DONDURULDU`. `tur_sayacini_kaydet` onu
    sifirlayici kola alir; `ustuste_onarimsiz_sonraki` ayri bir `dondu`
    yuklemi tasir (kova_bos ile AYNI KOVAYA konmaz — "kova bostu" ile
    "kova doluydu ama emir kapatti" ayri iddialardir).
E2  CAGRI YERI: `_dondurma_isirdi` bilgisini sayac kapisina GECIRIR.
    🔴 GEVSETME DEGIL: yalniz bayrak GERCEKTEN ISIRDIYSA (`ADAY>0`). Bayrak
    acik ama dagitilacak kalem ZATEN yoksa (`ADAY=0`) eski `KOSTU_DUSTU`
    AYNEN durur ve sayac ARTAR — kabul bataryasinin KONTROL vakasi budur.
E3  KAYIT ARTEFAKTI: sayac dosyasi artik `son_hal` + `son_iso` + `son_sebep`
    tasir. Onceden dosyada TEK sayi vardi: "sayac neden bu degerde" sorusu
    diskten okunamiyordu. `ustuste_onarimsiz_oku` degismedi (fazla alan
    zararsiz), yani geriye donuk uyum korunur.
    🔴 `ilk_*` alani BILEREK YOK: sifirlama yoluna "ilk gorulme" alani
    konursa alan kendi kendini yalanlar
    ([[saglikli-kosum-sayaci-sifirlar-kronik-ariza-birikmez]]).
E4  SEVIYE: `dondurma_seviyesi()` dondurmanin KAC GUNDUR durdugunu BAYRAGIN
    KENDI DAMGASINDAN okur (sayacin kenarindan DEGIL — araya giren saglikli
    tur onu sifirlayamaz). Deger her turda BASILIR **ve TUKETILIR**: esik
    asilirsa `ESKALASYON=OKAN DONDURMA_GUN=...` yazilir.
    🔴 Bu kol eskalasyon kanalini SUSTURMAZ, DOGRULTUR: Okan'a her turda
    giden anlamsiz `USTUSTE_ONARIMSIZ=154` yerine gercek karar sorusu
    ("dagitim N gundur donuk, M kalem bekliyor") gider. Okunamayan damga
    fail-closed ESKALE eder.
"""
import argparse
import os
import shutil
import sys
import time

CRON = os.path.expanduser("~/.claude/cron")
KAPI = os.path.join(CRON, "nobet-kapi.py")
KABUL_TESTI = os.path.join(CRON, "nobet-kabul-test.py")


def kok_ayarla(kok):
    """Yamayi baska bir AGACA yoneltir (hermetik kopyada olcum icin)."""
    global CRON, KAPI, KABUL_TESTI
    CRON = kok
    KAPI = os.path.join(kok, "nobet-kapi.py")
    KABUL_TESTI = os.path.join(kok, "nobet-kabul-test.py")


def _hedef(anahtar):
    return {"KAPI": KAPI, "KABUL_TESTI": KABUL_TESTI}[anahtar]


# ===========================================================================
# E0 — import
# ===========================================================================
E0_CAPA = '''import argparse
import importlib.util
'''
E0_YENI = '''import argparse
import datetime
import importlib.util
'''

# ===========================================================================
# E1 — DORDUNCU HAL
# ===========================================================================
E1_CAPA = '''def ustuste_onarimsiz_sonraki(onceki, onarim, kova_bos=False):
    """Ilk ONARIM>0 turunda sifirlar; kova bos ise sifirlar; aksi halde ard arda sayaci bir artirir.

    🔴 D-sayac (25 Agu 2026): "yapacak is yoktu" (kova bos + eskalasyon yok)
    ile "onarim DENENDI ve DUSTU" hali AYRIDIR. Bos kova sayaci ANLAMSIZ artirir
    ve yanlis eskalasyon uretirdi (olculdu: bir tur OKAN_KAPISI=0 basip USTUSTE_
    ONARIMSIZ=82 kaldi).
    """
    if kova_bos or onarim > 0:
        return 0
    return onceki + 1


def ustuste_onarimsiz_guncelle(onarim, yol=None, kova_bos=False):
    """Ard arda onarimsiz sayacini atomik yazar ve yeni degeri dondurur."""
    yol = yol or ONARIMSIZ_SAYAC_YOLU
    yeni = ustuste_onarimsiz_sonraki(ustuste_onarimsiz_oku(yol), onarim,
                                     kova_bos=kova_bos)
'''
E1_YENI = '''def ustuste_onarimsiz_sonraki(onceki, onarim, kova_bos=False, dondu=False):
    """Ilk ONARIM>0 turunda sifirlar; kova bos ise sifirlar; aksi halde ard arda sayaci bir artirir.

    🔴 D-sayac (25 Agu 2026): "yapacak is yoktu" (kova bos + eskalasyon yok)
    ile "onarim DENENDI ve DUSTU" hali AYRIDIR. Bos kova sayaci ANLAMSIZ artirir
    ve yanlis eskalasyon uretirdi (olculdu: bir tur OKAN_KAPISI=0 basip USTUSTE_
    ONARIMSIZ=82 kaldi).

    🔴 E-sayac (28 Agu 2026, K341): UCUNCU sifirlayici — `dondu`. Okan'in
    DONDURMA emri dagitim kolunu YAPISAL olarak kapatinca `onarim` daima 0
    kalir; eski yuklem bunu "onarim DENENDI ve DUSTU" sayip her turda +1
    atiyordu (olculdu: 89 -> 129 -> 154, uc gun MONOTON, HIC dusmedi).
    "Emirle yapmadi" ile "yapacakti, YAPAMADI" ayni kovaya GIREMEZ
    ([[emir-ariza-kovasina-duserse-hat-kendi-kendine-kirmizi-yanar]]).
    `kova_bos` ile AYRI parametre: "kova bostu" ile "kova doluydu ama emir
    kapatti" AYRI iddialardir ve kayitta ayri okunur.
    """
    if kova_bos or dondu or onarim > 0:
        return 0
    return onceki + 1


def ustuste_onarimsiz_guncelle(onarim, yol=None, kova_bos=False, dondu=False,
                               hal=None, sebep=None):
    """Ard arda onarimsiz sayacini atomik yazar ve yeni degeri dondurur.

    🔴 E3 (K341): dosya artik SAYIYI DEGIL KAYDI tasir — `son_hal`/`son_iso`/
    `son_sebep`. Onceden diskte tek sayi vardi ve "sayac neden bu degerde"
    sorusu dosyadan CEVAPLANAMIYORDU. `ustuste_onarimsiz_oku` yalniz
    `ustuste_onarimsiz` alanini okur, yani geriye donuk uyum KORUNUR.
    🔴 `ilk_*` alani BILEREK YOK: sifirlama yolunda duran bir "ilk gorulme"
    alani kendi kendini yalanlar
    ([[saglikli-kosum-sayaci-sifirlar-kronik-ariza-birikmez]]); seviye sorusu
    `dondurma_seviyesi()` ile BAYRAGIN damgasindan okunur.
    """
    yol = yol or ONARIMSIZ_SAYAC_YOLU
    yeni = ustuste_onarimsiz_sonraki(ustuste_onarimsiz_oku(yol), onarim,
                                     kova_bos=kova_bos, dondu=dondu)
'''

E1B_CAPA = '''            json.dump({"ustuste_onarimsiz": yeni}, dosya, ensure_ascii=False,
                      indent=2, sort_keys=True)
'''
E1B_YENI = '''            json.dump({"ustuste_onarimsiz": yeni,
                       "son_hal": hal or "-",
                       "son_iso": _damga(),
                       "son_sebep": sebep or "-"},
                      dosya, ensure_ascii=False,
                      indent=2, sort_keys=True)
'''

E1C_CAPA = '''TUR_HALLERI = ("KOSTU_ONARDI", "KOSTU_DUSTU", "ATLANDI", "IS_YOK")
'''
E1C_YENI = '''# 🔴 K341 (28 Agu 2026): DORDUNCU hal `DONDURULDU`. Ucuncu kova `tur_hukmu`ye
# 27 Agu'da ogretildi (B1) ama AYNI OLGUNUN IKINCI OKUYUCUSU olan bu kapi
# ogretilmedi -> rc yesile dondu, sayac tirmanmaya DEVAM etti (154). Arizanin
# onarilmasi degil YER DEGISTIRMESIYDI ([[ucuncu-tekrar-sinif-kapisi]]).
TUR_HALLERI = ("KOSTU_ONARDI", "KOSTU_DUSTU", "ATLANDI", "IS_YOK",
               "DONDURULDU")
'''

E1D_CAPA = '''    if hal == "IS_YOK":
        return ustuste_onarimsiz_guncelle(0, yol, kova_bos=True), True
    return ustuste_onarimsiz_guncelle(onarim if hal == "KOSTU_ONARDI" else 0,
                                      yol), True
'''
E1D_YENI = '''    if hal in ("IS_YOK", "DONDURULDU"):
        # Ikisi de sifirlar ama AYRI yuklemle ve kayitta AYRI adla: "kova
        # bostu" ile "kova doluydu, EMIR kapatti" ayri iddialardir.
        return ustuste_onarimsiz_guncelle(
            0, yol, kova_bos=(hal == "IS_YOK"), dondu=(hal == "DONDURULDU"),
            hal=hal, sebep=sebep), True
    return ustuste_onarimsiz_guncelle(onarim if hal == "KOSTU_ONARDI" else 0,
                                      yol, hal=hal, sebep=sebep), True
'''

E1E_CAPA = '''def tur_sayacini_kaydet(hal, onarim=0, yaz=True, yol=None, kova_bos=False):
    """Turun `ustuste_onarimsiz` etkisini TEK kapidan gecirir.

    KOSTU_ONARDI -> sifirlanir · KOSTU_DUSTU -> +1 · IS_YOK -> sifirlanir
'''
E1E_YENI = '''def tur_sayacini_kaydet(hal, onarim=0, yaz=True, yol=None, kova_bos=False,
                        sebep=None):
    """Turun `ustuste_onarimsiz` etkisini TEK kapidan gecirir.

    KOSTU_ONARDI -> sifirlanir · KOSTU_DUSTU -> +1 · DONDURULDU -> sifirlanir
    (K341: bayrak GERCEKTEN isirdi; onarimsizlik EMRIN sonucu, arizanin
    degil) · IS_YOK -> sifirlanir
'''

# ===========================================================================
# E2 — CAGRI YERI
# ===========================================================================
E2_CAPA = '''        ustuste_onarimsiz, _ = tur_sayacini_kaydet(   # B8 TEK KAPI
            "IS_YOK" if kova_bos_hali
            else "KOSTU_ONARDI" if onarim > 0
            else "KOSTU_DUSTU", onarim)
'''
E2_YENI = '''        # 🔴 K341 E2: `DONDURMA_ISIRDI=1` satirinin IKINCI tuketicisi.
        # SIRA onemli: gercek onarim (KOSTU_ONARDI) dondurmayi EZER — donmus
        # bir turda kalem KAPANMIS olabilir, o hal onarimdir.
        # 🔴 GEVSETME DEGIL: `_dondurma_isirdi` yalniz ADAY>0 iken True'dur;
        # bayrak acik ama dagitilacak kalem zaten yoksa eski KOSTU_DUSTU
        # AYNEN durur ve sayac ARTAR (kabul bataryasinin KONTROL vakasi).
        ustuste_onarimsiz, _ = tur_sayacini_kaydet(   # B8 TEK KAPI
            "IS_YOK" if kova_bos_hali
            else "KOSTU_ONARDI" if onarim > 0
            else "DONDURULDU" if _dondurma_isirdi
            else "KOSTU_DUSTU", onarim, sebep=_dondu_sebep if _dondu else None)
'''

# ===========================================================================
# E4 — SEVIYE (bayragin KENDI damgasindan) + TUKETICI
# ===========================================================================
E4_CAPA = '''def dondurma_karari(yol=None, env=None):
'''
E4_YENI = '''# 🔴 K341 E4: dondurma KAC GUNDUR duruyor. Esik asilinca Okan'a ESKALE edilir.
# Bu kol eskalasyon kanalini SUSTURMAZ, DOGRULTUR: eskiden her turda anlamsiz
# `USTUSTE_ONARIMSIZ=154` gidiyordu; artik gercek karar sorusu gidiyor.
DONDURMA_ESKALASYON_GUN = 1


def dondurma_seviyesi(yol=None, simdi=None, env=None):
    """(gun: int|None, sebep: str) — dondurma KAC GUNDUR duruyor.

    🔴 SEVIYE, sayacin KENARINDAN degil BAYRAGIN KENDI damgasindan okunur:
    araya giren saglikli bir tur bu degeri SIFIRLAYAMAZ
    ([[saglikli-kosum-sayaci-sifirlar-kronik-ariza-birikmez]]).
    Damga yoksa/bozuksa None doner -> cagri yeri FAIL-CLOSED eskale eder;
    "olculemedi" sessiz sifira DUSMEZ.
    """
    donduruldu, karar_sebep = dondurma_karari(yol=yol, env=env)
    if not donduruldu:
        return (None, "DONMUS_DEGIL:%s" % karar_sebep)
    yol = yol or DONDURMA_BAYRAK_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
        damga = str((veri or {}).get("damga") or "")
    except (OSError, ValueError):
        return (None, "BAYRAK_OKUNAMADI")
    if not damga:
        return (None, "DAMGA_YOK")
    try:
        baslangic = datetime.datetime.strptime(damga[:10], "%Y-%m-%d").date()
    except ValueError:
        return (None, "DAMGA_BOZUK:%s" % damga[:16])
    bugun = (simdi or datetime.datetime.utcnow()).date()
    return (max(0, (bugun - baslangic).days), "DAMGA=%s" % damga[:10])


def dondurma_karari(yol=None, env=None):
'''

E4B_CAPA = '''    if ustuste_onarimsiz >= 3:
        satirlar.append("ESKALASYON=OKAN USTUSTE_ONARIMSIZ=%d" % ustuste_onarimsiz)
'''
E4B_YENI = '''    if ustuste_onarimsiz >= 3:
        satirlar.append("ESKALASYON=OKAN USTUSTE_ONARIMSIZ=%d" % ustuste_onarimsiz)
    # 🔴 K341 E4 TUKETICI: seviye YAZILIP OKUNUR. Yazilip okunmayan alan kayit
    # degil SUStur ([[kapinin-menzili-cagri-yeridir]]); ve duran bir emir
    # gorunmez olursa hat en cok gereken anda korlesir
    # ([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]).
    if _dondurma_isirdi:
        _dgun, _dgun_sebep = dondurma_seviyesi()
        _dgun_metin = "OLCULEMEDI" if _dgun is None else str(_dgun)
        satirlar.append(
            "DONDURMA_SEVIYE GUN=%s SEBEP=%s ENGELLENEN=%d SAYAC_HAL=DONDURULDU"
            % (_dgun_metin, _dgun_sebep, _aday))
        if _dgun is None or _dgun >= DONDURMA_ESKALASYON_GUN:
            satirlar.append(
                "ESKALASYON=OKAN DONDURMA_GUN=%s ENGELLENEN=%d SIRADA=%d bayrak=%s"
                % (_dgun_metin, _aday, len(plan["sirada"]),
                   DONDURMA_BAYRAK_YOLU))
'''


# ===========================================================================
# E5 — BAYATLAYAN MUTANT ANKRAJI (nobet-kabul-test.py)
# ===========================================================================
# 🔴 `nobet-kabul-test.py::yeni_mutasyon_bataryasi` M-B mutantini
# `if kova_bos or onarim > 0:` satirina cakiyor. E1 o satiri degistirince
# ankraj TEKIL olmaktan cikti ve batarya FAIL-CLOSED `AssertionError` verdi
# (rc 0 -> 1, ONCEKI_MUTANT_KIRMIZI 2/2 -> 0/2). Bu ISTENEN davranistir:
# ankraj sessizce kaymadi, GORULDU. Ankraj yeni satira tasinir — mutantin
# OLCTUGU SEY DEGISMEZ (kova_bos kolu hala olur).
# Ders: mutant capasi da bir CAPADIR; kaynak degisince onunla birlikte
# tasinmazsa mutant kaynaga HIC dokunmadan "yasadi" gorunur.
E5_CAPA = '''        ("M-B", "    if kova_bos or onarim > 0:",
         "    if False:", vaka30_ustuste_sayaci_kova_bossa_sifirlar_gercek_dustude_artan),
'''
E5_YENI = '''        # 🔴 K341 (28 Agu 2026): E1 bu satira `dondu` yuklemini ekledi;
        # ankraj onunla birlikte tasindi. Mutant AYNI SEYI olcer: yuklem
        # tumden olurse kova_bos kolu da olur.
        ("M-B", "    if kova_bos or dondu or onarim > 0:",
         "    if False:", vaka30_ustuste_sayaci_kova_bossa_sifirlar_gercek_dustude_artan),
'''


YAMALAR = [
    ("E0",  "KAPI", E0_CAPA,  E0_YENI,  "import datetime"),
    ("E1",  "KAPI", E1_CAPA,  E1_YENI,  "kova_bos=False, dondu=False"),
    ("E1b", "KAPI", E1B_CAPA, E1B_YENI, '"son_hal": hal or "-"'),
    ("E1c", "KAPI", E1C_CAPA, E1C_YENI, '"IS_YOK",\n               "DONDURULDU")'),
    # 🔴 E1e, E1d'DEN ONCE gelmeli: E1d govdeyi degistirmiyor ama ikisi de
    # `tur_sayacini_kaydet`in icinde; imza once genisler ki `sebep` adi
    # govdede TANIMLI olsun. Ters sirada da metin yamasi TUTAR, ama okuyan
    # icin sira mantigi bozulur.
    ("E1e", "KAPI", E1E_CAPA, E1E_YENI, "yol=None, kova_bos=False,\n                        sebep=None"),
    ("E1d", "KAPI", E1D_CAPA, E1D_YENI, 'dondu=(hal == "DONDURULDU")'),
    ("E2",  "KAPI", E2_CAPA,  E2_YENI,  'else "DONDURULDU" if _dondurma_isirdi'),
    # 🔴 E4 capasi `def dondurma_karari(` — ONUNE ekler. `dondurma_seviyesi`
    # o fonksiyonu CAGIRIR; Python'da modul duzeyinde tanim sirasi cagri
    # anindan once cozuldugu icin sorun YOK.
    ("E4",  "KAPI", E4_CAPA,  E4_YENI,  "def dondurma_seviyesi"),
    ("E4b", "KAPI", E4B_CAPA, E4B_YENI, "DONDURMA_SEVIYE GUN=%s"),
    # 🔴 E5 AYRI DOSYADA: E1'in kaydirdigi mutant ankraji. AYNI TURDA
    # tasinmazsa komsu batarya fail-closed kirmizi yanar — nitekim YANDI
    # ([[defter-durum-sozlugu-onarim-bacagini-korlestirir]] madde 3: onarimda
    # tek yon kutsanmaz, DIGER OKUYUCU da ayni turda olculur).
    ("E5",  "KABUL_TESTI", E5_CAPA, E5_YENI,
     "if kova_bos or dondu or onarim > 0:"),
]


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def _yedekle(yol, damga):
    hedef = "%s.yedek-K341sayac-%s" % (yol, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def durum():
    """Her kol icin (ad, yol, KURULU|EKSIK|CAPA_YOK|CAPA_COK) doner."""
    sonuc = []
    onbellek = {}
    for ad, anahtar, capa, _yeni, isaret in YAMALAR:
        yol = _hedef(anahtar)
        if yol not in onbellek:
            try:
                onbellek[yol] = _oku(yol)
            except OSError as e:
                onbellek[yol] = None
                sonuc.append((ad, yol, "DOSYA_YOK:%s" % type(e).__name__))
                continue
        metin = onbellek[yol]
        if metin is None:
            sonuc.append((ad, yol, "DOSYA_YOK"))
            continue
        if isaret in metin:
            sonuc.append((ad, yol, "KURULU"))
            continue
        n = metin.count(capa)
        if n == 0:
            sonuc.append((ad, yol, "CAPA_YOK"))
        elif n > 1:
            sonuc.append((ad, yol, "CAPA_COK=%d" % n))
        else:
            sonuc.append((ad, yol, "EKSIK"))
    return sonuc


def uygula(kuru=False):
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    uygulanan, atlanan, dusen = 0, 0, 0
    icerik, degisen = {}, set()
    for ad, anahtar, capa, yeni, isaret in YAMALAR:
        yol = _hedef(anahtar)
        if yol not in icerik:
            try:
                icerik[yol] = _oku(yol)
            except OSError as e:
                print("KOL %-4s DOSYA_YOK %s (%s)" % (ad, yol, e))
                icerik[yol] = None
                dusen += 1
                continue
        metin = icerik[yol]
        if metin is None:
            dusen += 1
            continue
        if isaret in metin:
            print("KOL %-4s ZATEN_KURULU isaret=%r" % (ad, isaret[:40]))
            atlanan += 1
            continue
        n = metin.count(capa)
        if n != 1:
            # 🔴 Capa TEK olmali: 0 -> hedef degisti (bayat yama),
            # >1 -> hangi kopyaya vurdugumuz BELIRSIZ. Ikisi de RED.
            print("KOL %-4s CAPA_SAYISI=%d (1 bekleniyor) -> UYGULANMADI" % (ad, n))
            dusen += 1
            continue
        icerik[yol] = metin.replace(capa, yeni, 1)
        degisen.add(yol)
        print("KOL %-4s UYGULANDI %s" % (ad, os.path.basename(yol)))
        uygulanan += 1
    yedekler = []
    if not kuru:
        for yol in sorted(degisen):
            yedekler.append(_yedekle(yol, damga))
            _yaz(yol, icerik[yol])
    print("YAMA UYGULANAN=%d ZATEN=%d DUSEN=%d KURU=%d damga=%s"
          % (uygulanan, atlanan, dusen, int(kuru), damga))
    for y in yedekler:
        print("YEDEK %s" % y)
    return 0 if dusen == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kuru", action="store_true", help="yazmadan uygula")
    ap.add_argument("--durum", action="store_true", help="kurulu kopya yamali mi")
    ap.add_argument("--kok", default=None, metavar="DIZIN",
                    help="yamanin uygulanacagi AGAC (varsayilan: kurulu kopya "
                         "~/.claude/cron). Hermetik kopyayi yamalayip olcmek "
                         "icin; bayraksiz davranis DEGISMEZ.")
    args = ap.parse_args(argv)
    if args.kok:
        kok = os.path.abspath(os.path.expanduser(args.kok))
        if not os.path.isdir(kok):
            print("HATA: --kok dizini YOK: %s" % kok)
            return 2
        kok_ayarla(kok)
    print("KOK: %s (%s)" % (CRON, "BAYRAKLA" if args.kok else "VARSAYILAN/kurulu"))
    if args.durum:
        kotu = 0
        for ad, yol, hal in durum():
            print("KOL %-4s %-12s %s" % (ad, hal, os.path.basename(yol)))
            if hal != "KURULU":
                kotu += 1
        print("DURUM KURULU=%d EKSIK=%d" % (len(YAMALAR) - kotu, kotu))
        return 0 if kotu == 0 else 1
    return uygula(kuru=args.kuru)


if __name__ == "__main__":
    sys.exit(main())
