#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — `tavsiye_filament` D1 hattinin DORT KOLU DA CANLI mi?

NEDEN VAR (11 Agu 2026, mimar karari + olculen sinif):
    `tavsiyeFilament` urunun KENDI malzeme onerisidir ve bir FIYAT girdisidir:
    filament_ortak.on_secim() / secenekler.js `onSecimMalzeme` bu alani gorurse KATEGORI
    haritasini EZER ve ON-SECILI malzemeyi buradan alir; on-secilen malzeme sepet
    CARPANINI ve ILAN EDILEN TUTARI surer. Alan D1'de HIC YOKTU -> edge Worker kartina
    konamiyordu.

    Kolon canliya eklendi ve HASH KAPSAMINA alindi (mimar karari). Bu batarya, o kararin
    ve onunla gelen FAIL-CLOSED TIP KAPISININ hala GECERLI oldugunu olcer. Olculen risk
    sinifi ikilidir ve iki yonu de SESSIZDIR:

      (a) SESSIZ AYRISMA — kolon hash kapsamindan cikarilirsa "alan degisti ama urun_hash
          AYNI" hali dogar; diff_plan satiri "degismemis" sayar ve kolon HICBIR ZAMAN
          senkronlanmaz. Bu deponun defalarca isirdigi desendir.
      (b) SESSIZ NORMALIZASYON — beklenen tipte olmayan kaydi ([] yapmak ya da dizeyi tek
          elemanli diziye cevirmek) VERI KUSURUNU GIZLER: birincisi urunun kendi onerisini
          dusurup tutari kaydirir, ikincisi kusuru katalogda kalicilastirir. Dogru davranis
          DURMAK ve SAYIYI basmaktir.

🔴 ONARIMIN KENDISI DE BIR RISKTIR: bir tip kapisini "daha hosgorulu" yapmak, fail-loud
bir kapiyi fail-open'a cevirmenin en ucuz yoludur ([[duzeltme-fail-open-cevirebilir]]).
Bu yuzden batarya TEK YONLU DEGILDIR — bes ayri kolu AYRI AYRI olcer:
    HASH_KAPSAMI   alan degisince urun_hash DEGISIYOR mu (sessiz ayrisma kolu)
    TIP_ISTISNA    beklenmeyen tipte ISTISNA atiliyor mu (fail-open kolu)
    NORMALIZE_YOK  dize sessizce diziye CEVRILMIYOR mu (kusuru gizleme kolu)
    POZITIF_KOL    gecerli dizi kaydi KABUL ediliyor mu (yanlis-pozitif kolu)
    KOLON_KILIDI   kolon BES tanimin hepsinde mi (sema · GOC · fikstur · INSERT · KOLONLAR)

🔴 JETONLAR AYRIK (bu depoda isirdi: [[maskeleme-kismi-kapatma]]). Kol adlarinin hicbiri
otekinin ALT DIZESI DEGILDIR; ortak bir govde ("TIP") uzerinden bir kolu olduren mutant
baska bir kolun icinden gecemez.

🔴 BYTECODE ONBELLEGI BAGISIKLIGI ([[mutasyon-bytecode-onbellegi]]): batarya HICBIR
mutasyonu DISKE YAZMAZ. Kaynak metin okunur, BELLEKTE degistirilir ve
`exec(compile(src, ...), types.ModuleType(...).__dict__)` ile calistirilir. Diskte .py
dosyasi olusmadigi icin CPython ne `__pycache__` yazar ne okur. Ayrica her mutant icin
(a) capa TAM 1 kez geciyor mu, (b) eski metin gitti mi, (c) yeni metin geldi mi UCU DE
olculur; kosum sonunda canli dosyalarin sha256'si bas=son karsilastirilir.

FIKSTURLER SENTETIKTIR: urunler.json OKUNMAZ, canli D1'e / wrangler'a / AGA DOKUNULMAZ.
Katalog partisi ucarken de, CI fresh checkout'unda da AYNI hukmu verir.

KONTROL MUTANTI olculen eksenin ICINDEN secildi: tip dokumu raporunun AYIRACI degistirilir
(" · " -> " | "). Ayni fonksiyona dokunur ama hicbir kol raporun AYIRACINI olcmez ->
YESIL kalmali. Kalmazsa batarya "her degisiklikte kirmizi" demektir ve hicbir sey
olcmuyordur ([[beyan-edilmis-survivor]]).

Calistir:  python3 tools/tavsiye-filament-mutasyon.py   (0 = gecti, 1 = kaldi)
"""
import hashlib
import importlib.util
import os
import sys
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAMA = os.path.join(TOOLS, "arama.py")
D1SYNC = os.path.join(TOOLS, "d1-sync.py")
SEMA = os.path.join(TOOLS, "d1-sema.sql")

ALAN = "tavsiyeFilament"      # urunler.json alan adi
KOLON = "tavsiye_filament"    # D1 kolon adi


# --------------------------------------------------------------------- fiksturler
# Gercek kayit SEKLINI taklit eder ([[nobetci-fikstur-sekli]]) ama icerik SENTETIKTIR.
def _urun(ek=None, uid="fikstur-urun"):
    u = {"id": uid, "baslik": "Fikstur Parca", "kategori": "Otomobil", "marka": [],
         "fiyat": "100 TL", "gorseller": ["https://media.example/fikstur-1.jpg"],
         "aciklama": "fikstur aciklama"}
    if ek:
        u.update(ek)
    return u


FIX_YOK = _urun(uid="tf-yok")
FIX_DIZI = _urun({ALAN: ["PETG"]}, uid="tf-dizi")
FIX_DIZI_BASKA = _urun({ALAN: ["ASA"]}, uid="tf-dizi")           # AYNI id, BASKA deger
FIX_DIZI_SIRA = _urun({ALAN: ["ASA", "PETG"]}, uid="tf-sira")
FIX_DIZI_SIRA_TERS = _urun({ALAN: ["PETG", "ASA"]}, uid="tf-sira")
FIX_DIZE = _urun({ALAN: "PETG"}, uid="tf-dize")                  # 🔴 VERI KUSURU
FIX_NONE = _urun({ALAN: None}, uid="tf-none")
FIX_SOZLUK = _urun({ALAN: {"ad": "PETG"}}, uid="tf-sozluk")
FIX_OGE_SAYI = _urun({ALAN: ["PETG", 7]}, uid="tf-oge-sayi")
FIX_OGE_BOS = _urun({ALAN: ["PETG", "  "]}, uid="tf-oge-bos")
FIX_BOS_DIZI = _urun({ALAN: []}, uid="tf-bos-dizi")

BOZUK_FIKSTURLER = [("dize", FIX_DIZE), ("None", FIX_NONE), ("sozluk", FIX_SOZLUK),
                    ("oge-sayi", FIX_OGE_SAYI), ("oge-bos", FIX_OGE_BOS)]


# ------------------------------------------------------------------------ iddialar
# Her iddia (ok, detay) doner. `mod` = (arama_modulu, d1_modulu) ciftidir.
def hash_kapsami(mods):
    """Alan DEGISINCE urun_hash DEGISIYOR mu? (sessiz ayrisma kolu)

    UC nokta olculur: (1) alan YOK vs DOLU · (2) DOLU vs BASKA DEGER · (3) SIRA degisimi.
    (3) sart: sira bir FIYAT girdisidir (on_secim KALAN ILK adi secer); hash sirayi
    gormezse ["ASA","PETG"] -> ["PETG","ASA"] degisimi D1'e HIC yazilmazdi.
    """
    arama = mods[0]
    # 🔴 ISTISNA BURADA "COKME" DEGIL "FAIL"DIR: bu kolun fikstulerinin HEPSI GECERLIDIR;
    # gecerli bir kayitta hash uretilememesi bir arizadir ve KIRMIZI sayilmalidir. Istisnayi
    # disari birakmak onu COKTU'ya cevirir ve harness onu "kirmizi degil" sayardi — yani
    # yanlis-pozitif mutantini SESSIZCE hayatta birakirdi ([[hukum-yanlis-birimde]]).
    try:
        h_yok = arama.urun_hash(FIX_YOK)
        h_dizi = arama.urun_hash(FIX_DIZI)
        h_baska = arama.urun_hash(FIX_DIZI_BASKA)
        h_sira = arama.urun_hash(FIX_DIZI_SIRA)
        h_ters = arama.urun_hash(FIX_DIZI_SIRA_TERS)
    except Exception as e:                                       # noqa: BLE001
        return False, "GECERLI kayitta urun_hash ISTISNA atti: %s: %s" % (type(e).__name__, e)
    ok = (h_yok != h_dizi) and (h_dizi != h_baska) and (h_sira != h_ters)
    return ok, ("yok=%s dolu=%s baska=%s | sira=%s ters=%s"
                % (h_yok, h_dizi, h_baska, h_sira, h_ters))


def tip_istisna(mods):
    """Beklenmeyen tipte ISTISNA atiliyor mu? (fail-open kolu)

    BES ayri bozuk sekil icin AYRI AYRI olculur — tek sekli yakalayip otekini yutan bir
    kapi "beyan edilmis survivor"dur ([[beyan-edilmis-survivor]]).
    """
    arama = mods[0]
    parcalar = []
    hepsi = True
    for ad, fx in BOZUK_FIKSTURLER:
        try:
            deger = arama.tavsiye_filament_kanonik(fx)
            ok = False
            detay = "ISTISNA YOK -> %r" % (deger,)
        except arama.TavsiyeFilamentTipHatasi as e:
            ok = arama.tavsiye_filament_tip_sebebi(fx) is not None
            detay = "istisna ✔" if ok else ("istisna VAR ama sebep None: %s" % e)
        except Exception as e:                                   # noqa: BLE001
            ok = False
            detay = "YANLIS ISTISNA TURU %s: %s" % (type(e).__name__, e)
        hepsi = hepsi and ok
        parcalar.append("%s:%s" % (ad, detay))
    # urun_hash da DUSMELI: bozuk kayitli katalogta hash URETILEMEZ (bozuk veri D1'e
    # sessizce akamaz). Kanonik istisna atarken hash'in try/except ile yutmasi tam da
    # kapatmaya calistigimiz fail-open'dir.
    try:
        arama.urun_hash(FIX_DIZE)
        hepsi = False
        parcalar.append("urun_hash:BOZUK KAYITTA HASH URETTI")
    except arama.TavsiyeFilamentTipHatasi:
        parcalar.append("urun_hash:istisna ✔")
    except Exception as e:                                       # noqa: BLE001
        hepsi = False
        parcalar.append("urun_hash:YANLIS ISTISNA %s" % type(e).__name__)
    return hepsi, " | ".join(parcalar)


def normalize_yok(mods):
    """Dize SESSIZCE diziye cevrilmiyor mu? (kusuru gizleme kolu)

    🔴 TIP_ISTISNA'dan AYRI BIR KOL: bir mutant istisnayi kaldirip yerine `["PETG"]`
    dondurebilir. O mutant TIP_ISTISNA'yi da dusurur ama bu kol, hukmu DEGERIN KENDISI
    uzerinden verir: kabul edilen bir sonuc, girdideki dizeye ESIT ICERIKLI bir dizi
    OLAMAZ. Ayrica bos dizi (fail-open'in oteki ucuzu) da kabul edilemez.
    """
    arama = mods[0]
    try:
        deger = arama.tavsiye_filament_kanonik(FIX_DIZE)
    except arama.TavsiyeFilamentTipHatasi:
        return True, "dize REDDEDILDI (normalizasyon YOK) ✔"
    except Exception as e:                                       # noqa: BLE001
        return False, "YANLIS ISTISNA %s: %s" % (type(e).__name__, e)
    return False, ("dize SESSIZCE kabul edildi -> %r (tek elemanli diziye cevirmek ya da "
                   "bosaltmak veri kusurunu GIZLER)" % (deger,))


def pozitif_kol(mods):
    """GECERLI dizi kaydi kabul ediliyor mu ve deger BIREBIR mi? (yanlis-pozitif kolu)

    Dort nokta: (a) sebep None · (b) kanonik deger BIREBIR (sirasi dahil) · (c) DERIN
    KOPYA (cagiran donen listeyi degistirirse katalog bozulmamali) · (d) alan YOK ve bos
    dizi de GECERLI — kapi katalogun %98,9'unu reddedemez.
    """
    arama = mods[0]
    d1 = mods[1]
    sorunlar = []
    for ad, fx, beklenen in (("dizi", FIX_DIZI, ["PETG"]),
                             ("sira", FIX_DIZI_SIRA, ["ASA", "PETG"]),
                             ("bos-dizi", FIX_BOS_DIZI, []),
                             ("alan-yok", FIX_YOK, [])):
        sebep = arama.tavsiye_filament_tip_sebebi(fx)
        if sebep is not None:
            sorunlar.append("%s REDDEDILDI: %s" % (ad, sebep))
            continue
        try:
            deger = arama.tavsiye_filament_kanonik(fx)
        except Exception as e:                                   # noqa: BLE001
            sorunlar.append("%s ISTISNA atti: %s" % (ad, e))
            continue
        if deger != beklenen:
            sorunlar.append("%s deger %r, beklenen %r" % (ad, deger, beklenen))
    # 🔴 ISTISNA = FAIL (COKME DEGIL): asagidaki fiksturlerin HEPSI GECERLIDIR; gecerli
    # kayitta istisna atmak bu kolun olctugu arizanin ta kendisidir. Disari birakilsaydi
    # harness onu COKTU sayar ve yanlis-pozitif mutanti hayatta kalirdi.
    try:
        # DERIN KOPYA: donen listeyi bozmak katalogu bozmamali.
        donen = arama.tavsiye_filament_kanonik(FIX_DIZI_SIRA)
        donen.append("BOZUNTU")
        if FIX_DIZI_SIRA[ALAN] != ["ASA", "PETG"]:
            sorunlar.append("DERIN KOPYA DEGIL: fikstur bozuldu -> %r"
                            % (FIX_DIZI_SIRA[ALAN],))
        # D1'e giden METIN: kanonik JSON dizi, SIRA KORUNUR, bos hal '[]' (kolon DEFAULT'u).
        if d1.tavsiye_filament_metin(FIX_DIZI_SIRA) != '["ASA","PETG"]':
            sorunlar.append("metin bicimi/sirasi bozuk -> %r"
                            % d1.tavsiye_filament_metin(FIX_DIZI_SIRA))
        if d1.tavsiye_filament_metin(FIX_YOK) != "[]":
            sorunlar.append("bos hal '[]' DEGIL -> %r" % d1.tavsiye_filament_metin(FIX_YOK))
        # TIP KAPISI: temiz katalogda SAYI basar ve DURMAZ.
        dokum, bozuklar = d1.tavsiye_filament_tip_dokumu(
            [FIX_YOK, FIX_DIZI, FIX_DIZI_SIRA, FIX_BOS_DIZI])
        if bozuklar:
            sorunlar.append("TEMIZ katalogta bozuk bulundu: %r" % (bozuklar,))
        if dokum.get("YOK") != 1 or dokum.get("dizi") != 3:
            sorunlar.append("temiz dokum yanlis: %r" % (dokum,))
    except Exception as e:                                       # noqa: BLE001
        sorunlar.append("GECERLI kayitta ISTISNA: %s: %s" % (type(e).__name__, e))
    return not sorunlar, "; ".join(sorunlar) or "4 gecerli sekil + derin kopya + metin ✔"


def sayim_dokumu(mods):
    """Bozuk katalogta KAC KAYITTA HANGI TIP oldugu SAYIYLA raporlaniyor mu?

    Kapinin degeri "durmasi" kadar "NE KADAR" dedigidir: sayi olmadan veri sahibi kac
    kaydi duzeltecegini bilemez ve is sessizce geri doner.
    """
    d1 = mods[1]
    katalog = [FIX_YOK, FIX_YOK, FIX_DIZI, FIX_DIZE, FIX_DIZE, FIX_DIZE, FIX_SOZLUK]
    dokum, bozuklar = d1.tavsiye_filament_tip_dokumu(katalog)
    ok = (dokum.get("YOK") == 2 and dokum.get("dizi") == 1 and dokum.get("str") == 3
          and dokum.get("dict") == 1 and len(bozuklar) == 4)
    rapor = d1.tavsiye_filament_tip_raporu(dokum)
    # Rapor SAYILARI TASIMALI (bos/soyut bir "bozuk var" cumlesi yeterli DEGIL).
    ok = ok and "str=3" in rapor and "dizi=1" in rapor
    return ok, "dokum=%r bozuk=%d rapor=%r" % (dokum, len(bozuklar), rapor)


def kolon_kilidi(mods):
    """Kolon BES tanimin hepsinde mi + hash kapsaminda mi + ZORUNLU mu?

    (sema · GOC_KOLON · offline fikstur _KT_SEMA · INSERT listesi · KOLONLAR)
    Biri otekinden ayrisirsa testler YESIL yanarken canli baska semayla kosar.
    """
    d1 = mods[1]
    with open(SEMA, encoding="utf-8") as f:
        sema_metni = f.read()
    # 🔴 ISTISNA = FAIL: FIX_DIZI GECERLI bir kayittir; onun uzerinde SQL uretilememesi
    # (yanlis-pozitif mutanti) bu kolun KIRMIZI yanmasi gereken hali, COKME degil.
    try:
        sql = d1.satir_sql(FIX_DIZI, 1, "hs", "HASH1")
    except Exception as e:                                       # noqa: BLE001
        return False, "GECERLI kayitta satir_sql ISTISNA atti: %s: %s" % (type(e).__name__, e)
    ins = sql.split("INSERT INTO urunler (", 1)[1].split(")", 1)[0].split(",")
    ins = [k.strip() for k in ins]
    eksik = []
    if ("  %s TEXT" % KOLON) not in sema_metni and ("  %s TEXT" % KOLON) not in sema_metni:
        eksik.append("d1-sema.sql")
    if KOLON not in dict(d1.GOC_KOLON):
        eksik.append("GOC_KOLON")
    if KOLON not in d1._KT_SEMA:
        eksik.append("_KT_SEMA")
    if KOLON not in ins:
        eksik.append("INSERT")
    if KOLON not in d1.KOLONLAR:
        eksik.append("KOLONLAR")
    if KOLON not in d1.HASH_KAPSAMI:
        eksik.append("HASH_KAPSAMI")
    if KOLON not in d1.ZORUNLU_KOLONLAR:
        eksik.append("ZORUNLU_KOLONLAR")
    # ON CONFLICT SET listesi KOLONLAR ile ayrismamali (excluded.<k> yazilan kolondan okunur).
    if ("%s=excluded.%s" % (KOLON, KOLON)) not in sql:
        eksik.append("ON CONFLICT SET")
    # DEGER de SQL'e girmis olmali (kolon adi var, degeri yok = bos upsert).
    if '\'["PETG"]\'' not in sql:
        eksik.append("SQL DEGERI")
    return not eksik, ("eksik=%s" % (eksik or "YOK"))


IDDIALAR = [
    ("HASH_KAPSAMI  (alan degisince urun_hash degisiyor mu)", hash_kapsami),
    ("TIP_ISTISNA   (beklenmeyen tipte istisna atiliyor mu)", tip_istisna),
    ("NORMALIZE_YOK (dize sessizce diziye cevrilmiyor mu)", normalize_yok),
    ("POZITIF_KOL   (gecerli dizi kaydi kabul ediliyor mu)", pozitif_kol),
    ("SAYIM_DOKUMU  (kac kayitta hangi tip — SAYIYLA)", sayim_dokumu),
    ("KOLON_KILIDI  (bes tanim + hash kapsami + zorunlu)", kolon_kilidi),
]

# ------------------------------------------------------------------------ mutantlar
# (ad, hedef_dosya, capa, yerine, KIRMIZI_beklenir_mi, oldurdugu_kol)
_HASH_SATIRI = "        tavsiye_filament_kanonik(u),\n"
_KANONIK_ISTISNA = (
    "    sebep = tavsiye_filament_tip_sebebi(u)\n"
    "    if sebep is not None:\n"
    "        raise TavsiyeFilamentTipHatasi(\n"
    '            "%s (id=%r)" % (sebep, u.get("id")))\n')
_TIP_YARGISI = (
    "    if not isinstance(deger, list):\n"
    '        return ("%s dizi olmali, %s degil (deger: %r) — tek elemanli diziye SESSIZCE "\n'
    '                "CEVRILMEZ: kusur katalogda kalicilasirdi"\n'
    "                % (TAVSIYE_FILAMENT_ALAN, type(deger).__name__, deger))\n")
_KOLONLAR_GIRISI = '    "tavsiye_filament",\n]\n'

MUTANTLAR = [
    ("M-1 HASH KAPSAMI SOKULDU: kolon urun_hash'ten cikarildi (SESSIZ AYRISMA)",
     ARAMA, _HASH_SATIRI, "", True, "HASH_KAPSAMI"),
    ("M-2 FAIL-OPEN: tip kapisi istisna yerine [] donduruyor (sessiz bosaltma)",
     ARAMA, _KANONIK_ISTISNA,
     "    if tavsiye_filament_tip_sebebi(u) is not None:\n        return []\n",
     True, "TIP_ISTISNA/NORMALIZE_YOK"),
    # 🔴 M-3'un YERINE metni capayi ICERMEZ (icerseydi mutasyon_uygula "eski metin hala
    # var" diyip mutanti UYGULANMAMIS sayardi — sessizce olcumsuz kalirdi).
    ("M-3 SESSIZ NORMALIZASYON: dize tek elemanli diziye cevriliyor (kusuru GIZLER)",
     ARAMA, _KANONIK_ISTISNA,
     "    _ham = u.get(TAVSIYE_FILAMENT_ALAN)\n"
     "    if isinstance(_ham, str):\n"
     "        return [_ham]\n"
     "    _sbp = tavsiye_filament_tip_sebebi(u)\n"
     "    if _sbp is not None:\n"
     '        raise TavsiyeFilamentTipHatasi("%s (id=%r)" % (_sbp, u.get("id")))\n',
     True, "NORMALIZE_YOK/TIP_ISTISNA"),
    ("M-4 POZITIF KOL OLDURULDU: gecerli dizi kaydi da REDDEDILIYOR (yanlis-pozitif)",
     ARAMA, _TIP_YARGISI,
     "    if isinstance(deger, list):\n"
     '        return "%s dizi OLMAMALI" % TAVSIYE_FILAMENT_ALAN\n',
     True, "POZITIF_KOL"),
    ("M-5 TIP YARGISI KORLESTIRILDI: her deger gecerli sayiliyor (kapi fiilen YOK)",
     ARAMA, _TIP_YARGISI, "    if False:\n        return None\n",
     True, "TIP_ISTISNA/NORMALIZE_YOK/SAYIM_DOKUMU"),
    ("M-6 UPSERT KILIDI SOKULDU: kolon KOLONLAR'dan cikti (ilk yazim dogru, guncelleme BAYAT)",
     D1SYNC, _KOLONLAR_GIRISI, "]\n", True, "KOLON_KILIDI"),
    ("M-7 KONTROL: tip dokumu raporunun AYIRACI degisti (davranis DEGISMEZ) — YESIL kalmali",
     D1SYNC, '    return " · ".join("%s=%d" % (k, dokum[k]) for k in sorted(dokum))\n',
     '    return " | ".join("%s=%d" % (k, dokum[k]) for k in sorted(dokum))\n',
     False, "-"),
]


# --------------------------------------------------------------------------- kosum
def kaynak_oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _arama_yukle(src, etiket):
    """arama.py'yi BELLEKTE modul olarak calistirir. DISKE YAZILMAZ -> __pycache__ YOK."""
    mod = types.ModuleType("arama")          # d1-sync `import arama` ile BUNU bulmali
    mod.__file__ = ARAMA
    exec(compile(src, "<arama %s>" % etiket, "exec"), mod.__dict__)
    return mod


def _d1_yukle(src, etiket, arama_mod):
    """d1-sync.py'yi BELLEKTE calistirir; `import arama` VERILEN modulu bulur."""
    onceki = sys.modules.get("arama")
    sys.modules["arama"] = arama_mod
    try:
        mod = types.ModuleType("d1_sync_mutant_" + etiket)
        mod.__file__ = D1SYNC
        exec(compile(src, "<d1-sync %s>" % etiket, "exec"), mod.__dict__)
        return mod
    finally:
        if onceki is not None:
            sys.modules["arama"] = onceki
        else:
            sys.modules.pop("arama", None)


def modulleri_yukle(arama_src, d1_src, etiket):
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    a = _arama_yukle(arama_src, etiket)
    d = _d1_yukle(d1_src, etiket, a)
    return (a, d)


def mutasyon_uygula(src, eski, yeni):
    """(mutant_kaynak, hata) — uygulandigini UC eksende olcer."""
    n = src.count(eski)
    if n != 1:
        return None, "capa kaynakta %d kez geciyor (1 olmali) — hedef dosya degismis" % n
    mut = src.replace(eski, yeni, 1)
    if mut == src:
        return None, "mutasyon metni DEGISTIRMEDI"
    if eski in mut:
        return None, "eski metin mutantta HALA var (mutasyon uygulanmadi)"
    if yeni and yeni not in mut:
        return None, "yeni metin mutantta YOK"
    return mut, None


def iddialari_kos(mods):
    """[(ad, durum, detay)] — durum: PASS | FAIL | COKTU."""
    sonuc = []
    for ad, fn in IDDIALAR:
        try:
            ok, detay = fn(mods)
        except Exception as e:                                   # noqa: BLE001
            sonuc.append((ad, "COKTU", "%s: %s" % (type(e).__name__, e)))
            continue
        sonuc.append((ad, "PASS" if ok else "FAIL", detay))
    return sonuc


def main():
    for yol in (ARAMA, D1SYNC, SEMA):
        if not os.path.exists(yol):
            print("KIRMIZI: hedef bulunamadi: %s" % yol)
            return 1
    arama_src = kaynak_oku(ARAMA)
    d1_src = kaynak_oku(D1SYNC)
    bas_sha = (hashlib.sha256(arama_src.encode("utf-8")).hexdigest(),
               hashlib.sha256(d1_src.encode("utf-8")).hexdigest())
    fails = []

    print("=== KONTROL KOSUMU (mutasyonsuz) — %d/%d iddia PASS olmali"
          % (len(IDDIALAR), len(IDDIALAR)))
    kontrol = iddialari_kos(modulleri_yukle(arama_src, d1_src, "kontrol"))
    for ad, durum, detay in kontrol:
        print("  %-6s %s" % (durum, ad))
        if durum != "PASS":
            print("        %s" % detay[:500])
            fails.append("mutasyonsuz kosumda %s -> %s" % (ad, durum))

    print("\n=== MUTANTLAR (oldurucu olanlar en az 1 iddiayi FAIL etmeli)")
    kirmizi = 0
    beklenen = sum(1 for m in MUTANTLAR if m[4])
    kontrol_mutant = None
    for ad, hedef, eski, yeni, kirmizi_bekle, kol in MUTANTLAR:
        kaynak = arama_src if hedef == ARAMA else d1_src
        mut, hata = mutasyon_uygula(kaynak, eski, yeni)
        if hata:
            print("  FAIL   %s -> MUTASYON UYGULANAMADI: %s" % (ad, hata))
            fails.append(ad + " (uygulanamadi)")
            continue
        a_src = mut if hedef == ARAMA else arama_src
        d_src = mut if hedef == D1SYNC else d1_src
        try:
            mods = modulleri_yukle(a_src, d_src, "mut")
        except Exception as e:                                   # noqa: BLE001
            print("  FAIL   %s -> MUTANT YUKLENEMEDI (%s: %s) — cokme KIRMIZI SAYILMAZ"
                  % (ad, type(e).__name__, e))
            fails.append(ad + " (yuklenemedi)")
            continue
        sonuc = iddialari_kos(mods)
        dusen = [s[0].split()[0] for s in sonuc if s[1] == "FAIL"]
        coken = [s[0].split()[0] for s in sonuc if s[1] == "COKTU"]
        if kirmizi_bekle:
            ok = bool(dusen) and not coken
            if ok:
                kirmizi += 1
            print("  %-6s %s" % ("PASS" if ok else "FAIL", ad))
            print("         beklenen kol: %s | DUSEN: %s | COKEN: %s"
                  % (kol, ", ".join(dusen) or "-", ", ".join(coken) or "-"))
            if not ok:
                fails.append(ad + (" (cokme kirmiziyla karismasin)" if coken
                                   else " (mutant YAKALANMADI — iddia OLU)"))
        else:
            ok = not dusen and not coken
            kontrol_mutant = "YESIL" if ok else "KIRMIZI"
            print("  %-6s %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol_mutant))
            if not ok:
                print("         DUSEN: %s | COKEN: %s"
                      % (", ".join(dusen) or "-", ", ".join(coken) or "-"))
                fails.append(ad + " (kontrol mutanti kirmizi yandi: batarya olcmuyor)")

    son_sha = (hashlib.sha256(kaynak_oku(ARAMA).encode("utf-8")).hexdigest(),
               hashlib.sha256(kaynak_oku(D1SYNC).encode("utf-8")).hexdigest())
    if son_sha != bas_sha:
        fails.append("canli kaynak dosyalar DEGISTI (bas!=son sha256)")
    print("\ncanli dosya sha256 bas=son: %s (mutasyon diske YAZILMADI)"
          % ("EVET ✔" if son_sha == bas_sha else "HAYIR ✘"))
    print("MUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
          % (kirmizi, beklenen, kontrol_mutant or "KOSULMADI"))
    if fails:
        print("SONUC: KIRMIZI ❌  (%d)" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("SONUC: YESIL ✅ — hash kapsami, fail-closed tip kapisi, normalizasyon YASAGI, "
          "pozitif kol, sayim dokumu ve bes-tanim kilidi AYRI AYRI olculdu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
