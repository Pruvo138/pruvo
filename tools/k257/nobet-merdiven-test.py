#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K257 KABUL BATARYASI — eskalasyon merdiveni SAYILAN kural mi?

KANONIK KAYNAK: pruvo deposu `tools/k257/nobet-merdiven-test.py`.
KOSUM:  python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
KABUL:  son satir `KABUL=GECTI (n/n vaka)` ve rc=0.
CAGRI YERI: `testler.py` PAKETLER listesi.

OLCULEN KABUL MADDELERI (onceden CIVILI — buyutulmez)
  1) DORT HAL dordu AYRI vaka                          -> S1 + S2
  2) Her hal icin mutant + HEDEF-KOL ATFI              -> M1..M9
  3) KONTROL mutanti: ilgisiz kol bozulunca hedef YASAR-> KX (+ K0 harness)
  4) SAYAC TASINMASI: iki KATTA ardisik dusus 1->2     -> S3
  5) NEGATIF KONTROL: KAPI_REDDI sayaci ARTIRMAZ       -> S4
  6) CAPA SAGLIGI: bayat capa "YASADI" degil OLCULEMEDI-> BAYAT_CAPALAR
  7) KAPSAM TABANI SAYIYLA (oran DEGIL)                -> *_TABANI
  8) CAGRI YERI: uretimde gercekten kablolu mu         -> S7

🔴 IKI YONLU AYRIM (tautoloji freni): `hal_coz`'un iki ayri kolu ayni sonucu
uretebilir (metin izi ve `zorla`). Vakalar bunlari AYRI fiksturlerle olcer:
S1b yalniz IZ kolunu, S1f yalniz ZORLA kolunu belirleyici yapar. Tek yonlu
olsaydi izi olduren mutant `zorla` golgesinde YASARDI
([[ad-iki-rolde-mutanti-golgeler]] · [[isci-yesil-tablo-ic-olcumu-bosaltir]]).
"""

import ast
import importlib.util
import os
import shutil
import sys
import tempfile
import time

CRON_KOKU = "/Users/okan/.claude/cron"
MERDIVEN_YOLU = os.path.join(CRON_KOKU, "nobet_merdiven.py")
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
MUTASYON = os.path.join(CRON_KOKU, "nobet-kapi-mutasyon.py")

# --- KAPSAM TABANI (oran DEGIL SAYI) — [[batarya-kapsam-tabani-sayiyla-civilenir]]
# Buyutmek serbest, KUCULTMEK mimar kararidir.
VAKA_TABANI = 69
MUTANT_TABANI = 12
KONTROL_TABANI = 2

CANLI = ("minimax-m3", "kimi")

VAKALAR = []
BAYAT_CAPALAR = []


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-40s BEKLENEN=%-26s OLCULEN=%-26s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def kota_sahte(metin, rc):
    """`nobet-kapi.kota_reddi_mi` yerine gecen sahte: SEKLI ayni (metin, rc)."""
    if rc == 0:
        return False
    return "429" in (metin or "") or "usage limit" in (metin or "").lower()


def damga(saat):
    """Sabit taban + saat ofseti; `Date.now` yok, olcum tekrarlanabilir."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",
                         time.gmtime(1755000000 + saat * 3600))


# ===========================================================================
# S1 — hal_coz: DORT HAL, DORDU AYRI VAKA
# ===========================================================================

KAPI_METNI = "MIMAR ICRA KAPISI (20 Tem): olcum komutu reddedildi"
TAVAN_METNI = "isci kosuyor...\nSURE_TAVANI_ASILDI=1 TAVAN_SN=1500\n"
KOTA_METNI = "HTTP 429 usage limit reached"
DUZ_METNI = "Traceback: AssertionError: beklenen 3, olculen 5"


def bolum_s1(M, ek=""):
    print("--- BOLUM S1%s: hal_coz DORT HAL ---" % ek)
    vaka("S1a-rc0-dusme-yok%s" % ek, None, M.hal_coz(0, DUZ_METNI, kota_sahte))
    vaka("S1b-kapi-izi%s" % ek, "KAPI_REDDI",
         M.hal_coz(1, KAPI_METNI, kota_sahte))
    vaka("S1c-sure-tavani%s" % ek, "BITMEYEN_TUR",
         M.hal_coz(1, TAVAN_METNI, kota_sahte))
    vaka("S1d-kota%s" % ek, "KOTA", M.hal_coz(1, KOTA_METNI, kota_sahte))
    vaka("S1e-bilinmeyen-fail-closed%s" % ek, "YETENEK",
         M.hal_coz(1, DUZ_METNI, kota_sahte))
    # 🔴 IKI YONLU AYRIM: burada METINDE HICBIR KAPI IZI YOK; hukum yalniz
    # `zorla` kolundan gelebilir. S1b'nin tersi.
    vaka("S1f-zorla-izsiz-metin%s" % ek, "KAPI_REDDI",
         M.hal_coz(1, DUZ_METNI, kota_sahte, zorla="KAPI_REDDI"))
    # kota_kontrolu GECIRILMEZSE kota kolu OLCULEMEZ -> fail-closed varsayilan
    vaka("S1g-kota-kontrolsuz%s" % ek, "YETENEK", M.hal_coz(1, KOTA_METNI, None))
    # Oncelik: tur HIC BASLAMADIYSA kota da tuketilmemistir.
    vaka("S1h-kapi-kota-oncelik%s" % ek, "KAPI_REDDI",
         M.hal_coz(1, KAPI_METNI + "\n" + KOTA_METNI, kota_sahte))
    try:
        M.hal_coz(1, DUZ_METNI, kota_sahte, zorla="SACMA")
        hal = "SESSIZ_GECTI"
    except ValueError:
        hal = "ValueError"
    except Exception as hata:                                   # noqa: BLE001
        hal = type(hata).__name__
    vaka("S1i-zorla-bilinmeyen%s" % ek, "ValueError", hal)
    vaka("S1j-kapi-sahibi%s" % ek, "mimar-icra-kapisi",
         M.kapi_reddi_sahibi(KAPI_METNI))


# ===========================================================================
# S2 — YON TABLOSU + SAYAC ETKISI (dort hal, dordu AYRI)
# ===========================================================================

S2_BEKLENEN = (
    ("KOTA", "YANA", 0),
    ("YETENEK", "YUKARI", 1),
    ("BITMEYEN_TUR", "KOVA", 0),
    ("KAPI_REDDI", "SAHIBINE", 0),
)


def bolum_s2(M, ek=""):
    print("--- BOLUM S2%s: YON TABLOSU + SAYAC ---" % ek)
    for hal, yon, artis in S2_BEKLENEN:
        kayit = {}
        karar = M.merdiven_ilerlet(kayit, hal, damga=damga(0),
                                   canli_motorlar=CANLI, rc=1,
                                   metin=KAPI_METNI if hal == "KAPI_REDDI" else DUZ_METNI)
        vaka("S2-%s-yon%s" % (hal, ek), yon, (karar or {}).get("yon"))
        vaka("S2-%s-sayilir%s" % (hal, ek), artis == 1,
             (karar or {}).get("sayilir"))
        vaka("S2-%s-sayac%s" % (hal, ek), artis, M.sayac(kayit))


# ===========================================================================
# S3 — SAYAC TASINMASI: IKI FARKLI KATTA ARDISIK DUSUS
# ===========================================================================

def bolum_s3(M, ek=""):
    print("--- BOLUM S3%s: SAYAC TASINMASI (SIFIRLANMAZ) ---" % ek)
    kayit = {}
    izler = []
    for adim in range(3):
        karar = M.merdiven_ilerlet(kayit, "YETENEK", damga=damga(adim),
                                   canli_motorlar=CANLI, rc=1, metin=DUZ_METNI,
                                   atif="/rapor/%d.md" % adim)
        izler.append((karar["onceki_basamak"], karar["basamak"], karar["sayac"]))
    vaka("S3a-m3-birinci%s" % ek, "minimax-m3>minimax-m3=1",
         "%s>%s=%d" % izler[0])
    # 🔴 IKINCI dusus m3'un tavanini (2) doldurur -> KAT DEGISIR, sayac 1->2:
    # yeni kat sifirdan baslamaz. Merdivenin cekirdek iddiasi budur.
    vaka("S3b-m3-tavan-kat-degisir%s" % ek, "minimax-m3>kimi=2",
         "%s>%s=%d" % izler[1])
    vaka("S3c-kimi-ustune-mimar%s" % ek, "kimi>MIMAR=3", "%s>%s=%d" % izler[2])
    vaka("S3d-sayac-monoton%s" % ek, "1,2,3",
         ",".join(str(i[2]) for i in izler))
    vaka("S3e-denemeler-tasindi%s" % ek, 3, len(M.denemeler(kayit)))
    alanlar = all(d.get("basamak") and d.get("motor") and d.get("hal")
                  and d.get("damga") and d.get("atif")
                  for d in M.denemeler(kayit))
    vaka("S3f-deneme-alanlari-dolu%s" % ek, True, alanlar)


# ===========================================================================
# S4 — NEGATIF KONTROL: KAPI_REDDI NE YANA NE YUKARI
# ===========================================================================

def bolum_s4(M, ek=""):
    print("--- BOLUM S4%s: KAPI_REDDI NEGATIF KONTROLU ---" % ek)
    kayit = {}
    karar = M.merdiven_ilerlet(kayit, "KAPI_REDDI", damga=damga(0),
                               canli_motorlar=CANLI, rc=1, metin=KAPI_METNI)
    vaka("S4a-sayac-artmaz%s" % ek, 0, M.sayac(kayit))
    vaka("S4b-basamak-degismez%s" % ek, "minimax-m3>minimax-m3",
         "%s>%s" % (karar["onceki_basamak"], karar["basamak"]))
    vaka("S4c-durum%s" % ek, "ARAC_KUSURU", karar["durum"])
    vaka("S4d-sahip%s" % ek, "mimar-icra-kapisi", karar["sahip"])
    vaka("S4e-dagitilmaz%s" % ek, True, M.dagitilmaz_mi(kayit))
    for tekrar in range(1, 3):
        M.merdiven_ilerlet(kayit, "KAPI_REDDI", damga=damga(tekrar),
                           canli_motorlar=CANLI, rc=1, metin=KAPI_METNI)
    vaka("S4f-uc-redde-de-sabit%s" % ek, "0@minimax-m3",
         "%d@%s" % (M.sayac(kayit), M.basamak(kayit)))


# ===========================================================================
# S5 — MERDIVEN TURETIMI (ikinci motor listesi YOK)
# ===========================================================================

def bolum_s5(M, ek=""):
    print("--- BOLUM S5%s: MERDIVEN TURETIMI ---" % ek)
    basamaklar = M.merdiven_kur(CANLI)
    vaka("S5a-basamak-adlari%s" % ek,
         "minimax-m3,kimi,MIMAR,KRAL,BABA,OKAN",
         ",".join(b["ad"] for b in basamaklar))
    vaka("S5b-isci-tavanlari%s" % ek, "2,1",
         ",".join(str(b["tavan"]) for b in basamaklar if b["tur"] == "ISCI"))
    vaka("S5c-bos-kume-fail-closed%s" % ek, None, M.merdiven_kur(()))
    vaka("S5d-insan-sirasi%s" % ek, "MIMAR,KRAL,BABA,OKAN",
         ",".join(b["ad"] for b in basamaklar if b["tur"] != "ISCI"))
    vaka("S5e-baba-tavani-yok%s" % ek, None,
         M.basamak_bul(basamaklar, "BABA")[1]["tavan"])
    # Kume BUYURSE merdiven de buyur: liste TURETILIYOR, sabit DEGIL.
    uc = M.merdiven_kur(("a", "b", "c"))
    vaka("S5f-uc-motor-turetildi%s" % ek, "a:2,b:1,c:1",
         ",".join("%s:%s" % (b["ad"], b["tavan"])
                  for b in uc if b["tur"] == "ISCI"))


# ===========================================================================
# S6 — BABA BASAMAGI: SAYAC DEGIL SLA
# ===========================================================================

def _babaya_getir(M):
    """Kalemi BABA basamagina YETENEK dususleriyle tasir."""
    kayit = {}
    for adim in range(5):
        M.merdiven_ilerlet(kayit, "YETENEK", damga=damga(0),
                           canli_motorlar=CANLI, rc=1, metin=DUZ_METNI)
    return kayit


def bolum_s6(M, ek=""):
    print("--- BOLUM S6%s: BABA SLA (SAYACA DAHIL DEGIL) ---" % ek)
    kayit = _babaya_getir(M)
    vaka("S6a-baba-basamagi%s" % ek, "BABA=5",
         "%s=%d" % (M.basamak(kayit), M.sayac(kayit)))
    epok = 1755000000
    karar = M.sla_karari(kayit, simdi=epok + 12 * 3600, canli_motorlar=CANLI)
    vaka("S6b-sla-icinde%s" % ek, "False@BABA",
         "%s@%s" % (karar["asildi"], M.basamak(kayit)))
    once_deneme, once_sayac = len(M.denemeler(kayit)), M.sayac(kayit)
    karar = M.sla_karari(kayit, simdi=epok + 25 * 3600, canli_motorlar=CANLI)
    vaka("S6c-sla-asildi-okan%s" % ek, "True@OKAN",
         "%s@%s" % (karar["asildi"], M.basamak(kayit)))
    # 🔴 (d) SLA gocu SAYACA DOKUNMAZ: ne deneme eklenir ne sayac artar.
    vaka("S6d-sla-sayaca-dokunmaz%s" % ek,
         "%d/%d" % (once_deneme, once_sayac),
         "%d/%d" % (len(M.denemeler(kayit)), M.sayac(kayit)))
    # MIMAR basamagindaki kaleme SLA ISLEMEZ (yalniz BaBa basamagi).
    mimar = {}
    for adim in range(3):
        M.merdiven_ilerlet(mimar, "YETENEK", damga=damga(0),
                           canli_motorlar=CANLI, rc=1, metin=DUZ_METNI)
    vaka("S6e-mimar-sla-yok%s" % ek, "MIMAR@None",
         "%s@%s" % (M.basamak(mimar),
                    M.sla_karari(mimar, simdi=epok + 99 * 3600,
                                 canli_motorlar=CANLI)))


# ===========================================================================
# S8 — UCTAN UCA: OKAN'IN MERDIVENININ TAMAMI
# ===========================================================================

BEKLENEN_YURUYUS = (
    "minimax-m3=1", "kimi=2", "MIMAR=3", "KRAL=4", "BABA=5", "BABA=6",
)


def bolum_s8(M, ek=""):
    print("--- BOLUM S8%s: TAM MERDIVEN YURUYUSU ---" % ek)
    kayit = {}
    for sira, beklenen in enumerate(BEKLENEN_YURUYUS):
        karar = M.merdiven_ilerlet(kayit, "YETENEK", damga=damga(sira),
                                   canli_motorlar=CANLI, rc=1, metin=DUZ_METNI,
                                   atif="/rapor/y%d.md" % sira)
        vaka("S8-%d-%s" % (sira, beklenen.split("=")[0] + ek), beklenen,
             "%s=%d" % (karar["basamak"], karar["sayac"]))
    vaka("S8-durum-eskalasyon%s" % ek, "ESKALASYON", kayit["durum"])
    # (c) Ust kata giden kalem OLCUMU de goturur.
    ozet = M.olculmus_ozet(kayit)
    vaka("S8-olcum-tasindi%s" % ek, True,
         ozet.startswith("OLCUM=") and "atif=/rapor/y5.md" in ozet
         and "YETENEK@BABA" in ozet)


# ===========================================================================
# S9 — TOHUMLAMA: K257 ONCESI KAYDIN GECMISI SILINMEZ
# ===========================================================================

def bolum_s9(M, ek=""):
    print("--- BOLUM S9%s: DEVIR TOHUMLAMASI ---" % ek)
    # 🔴 Canli geri-izde SU AN boyle 15 kayit var: `dagitim_sayisi=3`, merdiven
    # kaydi YOK. Tohumlamasiz her biri SIFIRDAN baslardi — K257(a)'nin tam
    # yasakladigi sey.
    eski = {"id": "K01", "dagitim_sayisi": 3, "motor": "kimi",
            "damga": damga(0), "rapor_yolu": "/rapor/eski.md"}
    karar = M.merdiven_ilerlet(eski, "YETENEK", damga=damga(1),
                               canli_motorlar=CANLI, rc=1, metin=DUZ_METNI)
    vaka("S9a-devir-sayaci-tasindi%s" % ek, 4, karar["sayac"])
    vaka("S9b-devir-basamagi%s" % ek, "MIMAR>KRAL",
         "%s>%s" % (karar["onceki_basamak"], karar["basamak"]))
    vaka("S9c-devir-eskalasyon%s" % ek, "ESKALASYON", karar["durum"])
    vaka("S9d-devir-damgasi%s" % ek, 3,
         M.merdiven_kaydi(eski).get("devir", {}).get("dagitim_sayisi"))
    # KONTROL KOLU: gecmisi OLMAYAN kalem tohumlanmaz (fazla sayma YOK).
    taze = {"id": "K02"}
    karar2 = M.merdiven_ilerlet(taze, "YETENEK", damga=damga(1),
                                canli_motorlar=CANLI, rc=1, metin=DUZ_METNI)
    vaka("S9e-taze-kalem-tohumlanmaz%s" % ek, "minimax-m3=1",
         "%s=%d" % (karar2["basamak"], karar2["sayac"]))
    # `dagitim_sayisi` merdiven sayaciyla EZILMEZ (iki AYRI buyukluk).
    vaka("S9f-dagitim-sayisi-ezilmez%s" % ek, 3, eski.get("dagitim_sayisi"))


# ===========================================================================
# S7 — CAGRI YERI (uretim dosyasi; mutant harness'ine GIRMEZ)
# ===========================================================================

def _fonksiyon(agac, ad):
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef) and dugum.name == ad:
            return dugum
    return None


def _cagri_var(dugum, ad):
    for alt in ast.walk(dugum or ast.Module(body=[], type_ignores=[])):
        if isinstance(alt, ast.Call):
            hedef = alt.func
            if isinstance(hedef, ast.Attribute) and hedef.attr == ad:
                return True
            if isinstance(hedef, ast.Name) and hedef.id == ad:
                return True
    return False


def bolum_s7(kaynak, ek=""):
    print("--- BOLUM S7%s: CAGRI YERI (kapinin menzili) ---" % ek)
    agac = ast.parse(kaynak)
    vaka("S7a-modul-import" + ek, True,
         "nobet_merdiven" in kaynak or "MERDIVEN" in kaynak)
    vaka("S7b-kalemi-dusur-cagiriyor" + ek, True,
         _cagri_var(_fonksiyon(agac, "_kalemi_dusur"), "merdiven_ilerlet"))
    vaka("S7c-komut-reddedildi-kapi-reddi" + ek, True,
         "hal=MERDIVEN.HAL_KAPI_REDDI" in kaynak)
    # 🔴 (e) IKINCI MOTOR LISTESI: elle yazilmis tuple KALMADI mi?
    zincir = "-"
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Assign) and dugum.targets \
                and isinstance(dugum.targets[0], ast.Name) \
                and dugum.targets[0].id == "TUR_MOTOR_ZINCIRI":
            deger = dugum.value
            if isinstance(deger, (ast.Tuple, ast.List)) \
                    and all(isinstance(e, ast.Constant) for e in deger.elts):
                zincir = "ELLE_TUPLE"
            else:
                zincir = "TURETILDI"
    vaka("S7d-tur-motor-zinciri-turetildi" + ek, "TURETILDI", zincir)
    # 🔴 "TURETILDI" tek basina YETMEZ: ifade CANLI kumeyi GERCEKTEN okumali.
    # Okumuyorsa yine ikinci bir liste var demektir, sadece sekli degismistir.
    okur = "-"
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Assign) and dugum.targets \
                and isinstance(dugum.targets[0], ast.Name) \
                and dugum.targets[0].id == "TUR_MOTOR_ZINCIRI":
            adlar = {d.id for d in ast.walk(dugum.value)
                     if isinstance(d, ast.Name)}
            okur = "OKUR" if "CANLI_ISCI_MOTORLARI" in adlar else "OKUMAZ"
    vaka("S7h-zincir-canli-kumeyi-okur" + ek, "OKUR", okur)
    # 🔴 K257(e) TAM TURETIM (mimar hukmu, 20 Agu). "TURETILDI" ve "OKUR"
    # birlikte bile YETMEZ: `tuple(CANLI_ISCI_MOTORLARI[:1])` ikisini de
    # gecer ama zinciri DARALTIR ve BaBa'nin eski tekil hukmunu sessizce geri
    # getirir. Ifadede CANLI kumeye uygulanmis HICBIR dilim/indis olmamali.
    kirpma = "-"
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Assign) and dugum.targets \
                and isinstance(dugum.targets[0], ast.Name) \
                and dugum.targets[0].id == "TUR_MOTOR_ZINCIRI":
            kirpik = [d for d in ast.walk(dugum.value)
                      if isinstance(d, ast.Subscript)
                      and isinstance(d.value, ast.Name)
                      and d.value.id == "CANLI_ISCI_MOTORLARI"]
            kirpma = "KIRPILMIS" if kirpik else "TAM"
    vaka("S7j-zincir-TAM-turetilmis" + ek, "TAM", kirpma)
    vaka("S7e-sla-uretimde-cagriliyor" + ek, True,
         _cagri_var(_fonksiyon(agac, "tur_kapat"), "sla_karari"))
    vaka("S7f-dagitilmaz-durumlar-kullaniliyor" + ek, True,
         "DAGITILMAZ_DURUMLAR" in kaynak)
    # 🔴 IKINCI ESIK YASAGI: eski TEK ESIK sabiti hicbir kolda OKUNMAMALI.
    # Okunuyorsa merdivenin yaninda ikinci bir eskalasyon kurali yasiyor demektir.
    okuma = sum(1 for d in ast.walk(agac)
                if isinstance(d, ast.Name) and d.id == "ESKALASYON_DAGITIM"
                and isinstance(d.ctx, ast.Load))
    vaka("S7g-eski-tek-esik-okunmuyor" + ek, 0, okuma)
    # 🔴 BAGIMLILIK KAYDI: mutasyon surucusu mutanti IZOLE dizinde kosturur ve
    # bagimliliklari ELLE kopyalar. `nobet_merdiven` kaydedilmezse surucu
    # ModuleNotFoundError ile duser — ve rc ONCE de SONRA da 1 oldugu icin bu
    # ONCE=SONRA karsilastirmasinda GORUNMEZ. Kaydi burada CIVILIYORUZ.
    try:
        with open(MUTASYON, encoding="utf-8") as dosya:
            mut = dosya.read()
        kayitli = ("CANLI_MERDIVEN" in mut
                   and mut.count('"nobet_merdiven.py"') >= 2)
    except OSError:
        kayitli = "OLCULEMEDI"
    vaka("S7i-mutasyon-bagimlilik-kaydi" + ek, True, kayitli)


# ===========================================================================
# MUTANTLAR — hedef-kol atfi + capa sagligi
# ===========================================================================

def _bolumleri_kos(M, ek):
    bolum_s1(M, ek)
    bolum_s2(M, ek)
    bolum_s3(M, ek)
    bolum_s4(M, ek)
    bolum_s5(M, ek)
    bolum_s6(M, ek)
    bolum_s8(M, ek)
    bolum_s9(M, ek)


def capali_degistir(kaynak, eski, yeni, ad):
    """🔴 Capa bayatsa COKME degil KAYIT: arkasindaki capalar da olculur.

    [[capa-cokmesi-arkasindaki-capalari-gizler]]
    """
    sayi = kaynak.count(eski)
    if sayi != 1:
        BAYAT_CAPALAR.append("%s: capa sayisi=%d -> %r" % (ad, sayi, eski[:60]))
        return None
    return kaynak.replace(eski, yeni, 1)


def _atif(ad, isaret, hedef_onek, yan_onek):
    yeni = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    hedef = [v for v in yeni if any(v[0].startswith(o) for o in hedef_onek)]
    yan = [v for v in yeni if any(v[0].startswith(o) for o in yan_onek)]
    hedef_oldu = bool(hedef) and all(not v[3] for v in hedef)
    yan_yesil = bool(yan) and all(v[3] for v in yan)
    print("MUTANT=%-34s HEDEF_KOL=%-9s (%d vaka) YAN_EKSEN=%-8s (%d vaka)"
          % (ad, "OLDU" if hedef_oldu else "YASADI", len(hedef),
             "YESIL" if yan_yesil else "KIRMIZI", len(yan)))
    return hedef_oldu, yan_yesil


def mutant_kos(ad, kaynak, tmp, hedef_onek, yan_onek):
    """Mutasyonlu kaynagi AYRI modul olarak yukleyip tum bolumleri kosar."""
    if kaynak is None:                       # capa bayat -> OLCULEMEDI
        print("MUTANT=%-34s HEDEF_KOL=OLCULEMEDI (capa bayat)" % ad)
        return None, None
    isaret = len(VAKALAR)
    kisa = ad.split("-")[0].lower()
    yol = os.path.join(tmp, "mutant_%s.py" % kisa)
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(kaynak)
    try:
        mod = modul_yukle(yol, "k257_mutant_%s" % kisa)
        _bolumleri_kos(mod, "-%s" % ad)
    except Exception as hata:                                   # noqa: BLE001
        # Vaka patlarsa toplam KUCULMESIN: patlama tek vaka olarak sayilir.
        vaka("MUTANT_PATLADI-%s" % ad, "YOK", type(hata).__name__)
    return _atif(ad, isaret, hedef_onek, yan_onek)


# Yan eksen onekleri: hedefe DEGMEYEN bolumler. Her mutant kendi listesini verir.
TUM = ("S1", "S2", "S3", "S4", "S5", "S6", "S8", "S9")


def _yan(*haric):
    return tuple(o for o in TUM if o not in haric)


def bolum_mutant(kaynak, tmp):
    print("--- BOLUM M: MUTANTLAR ---")
    sonuclar = []

    # M1 — KOTA yonu YUKARI'ya cevrildi (yana kolu oldu)
    sonuclar.append(("M1-kota-yukari",) + mutant_kos(
        "M1-kota-yukari",
        capali_degistir(kaynak, "    HAL_KOTA: YON_YANA,",
                        "    HAL_KOTA: YON_YUKARI,", "M1"),
        # HEDEF yalniz YON kolu: `sayilir` ayri bir tablodan gelir ve bu
        # mutantla DEGISMEZ — hedefe konsaydi mutant "YASADI" gorunurdu
        # ([[ad-iki-rolde-mutanti-golgeler]]).
        tmp, ("S2-KOTA-yon",), _yan("S2")))

    # M2 — KAPI_REDDI sayaci ARTIRIYOR (negatif kontrolun hedefi)
    sonuclar.append(("M2-kapi-reddi-sayiyor",) + mutant_kos(
        "M2-kapi-reddi-sayiyor",
        capali_degistir(kaynak, "    HAL_KAPI_REDDI: False,\n}",
                        "    HAL_KAPI_REDDI: True,\n}", "M2"),
        tmp, ("S4a", "S4f", "S2-KAPI_REDDI-sayilir", "S2-KAPI_REDDI-sayac"),
        _yan("S2", "S4")))

    # M3 — hal_coz'un KAPI IZI kolu sokuldu (zorla kolu SAG kalir)
    sonuclar.append(("M3-kapi-izi-kolu-sokuldu",) + mutant_kos(
        "M3-kapi-izi-kolu-sokuldu",
        capali_degistir(kaynak,
                        "    if kapi_reddi_sahibi(metin):\n"
                        "        return HAL_KAPI_REDDI\n",
                        "    if False:\n        return HAL_KAPI_REDDI\n", "M3"),
        tmp, ("S1b", "S1h"), ("S1f", "S1a", "S1c", "S1d", "S1e", "S1g", "S1i")))

    # M4 — fail-closed varsayilan KOTA'ya cevrildi (bilinmeyen dusme sayilmaz)
    sonuclar.append(("M4-varsayilan-kota",) + mutant_kos(
        "M4-varsayilan-kota",
        capali_degistir(kaynak,
                        "def hal_coz(rc, cikti, kota_kontrolu=None, "
                        "varsayilan=HAL_YETENEK, zorla=None):",
                        "def hal_coz(rc, cikti, kota_kontrolu=None, "
                        "varsayilan=HAL_KOTA, zorla=None):", "M4"),
        tmp, ("S1e", "S1g"), _yan("S1")))

    # M5 — sayac `sayilir` suzgecini KAYBETTI (her dusme sayilir)
    sonuclar.append(("M5-sayac-suzgecsiz",) + mutant_kos(
        "M5-sayac-suzgecsiz",
        capali_degistir(kaynak,
                        "    return sum(1 for d in denemeler(kayit) "
                        "if d.get(\"sayilir\"))",
                        "    return len(denemeler(kayit))", "M5"),
        tmp, ("S2-KOTA-sayac", "S2-BITMEYEN_TUR-sayac",
              "S2-KAPI_REDDI-sayac", "S4a", "S4f"),
        _yan("S2", "S4")))

    # M6 — isci tavanlari (2,1) -> (1,1): m3 IKINCI denemeyi ALAMAZ
    sonuclar.append(("M6-isci-tavani-bir",) + mutant_kos(
        "M6-isci-tavani-bir",
        capali_degistir(kaynak, "ISCI_TAVANLARI = (2, 1)",
                        "ISCI_TAVANLARI = (1, 1)", "M6"),
        # S8-4/S6a HEDEF DEGIL: BABA tavani None oldugu icin o iki vaka
        # tavan mutantindan ETKILENMEZ ve YASAR (olculdu, hedef-kol atfi).
        tmp, ("S3a", "S3b", "S3c", "S5b", "S8-0", "S8-1", "S8-2", "S8-3"),
        ("S1", "S2", "S4", "S5a", "S5c", "S5d", "S5e")))

    # M7 — (e) IKINCI MOTOR LISTESI geri geldi: merdiven TURETILMIYOR
    sonuclar.append(("M7-ikinci-motor-listesi",) + mutant_kos(
        "M7-ikinci-motor-listesi",
        capali_degistir(kaynak, "    canli = tuple(m for m in (canli_motorlar or ()) if m)",
                        "    canli = (\"minimax-m3\",)", "M7"),
        # S5d HEDEF DEGIL: insan basamaklari zaten sabit listeden gelir,
        # turetim mutanti onlari DEGISTIRMEZ.
        tmp, ("S5a", "S5b", "S5c", "S5f"), ("S1",)))

    # M8 — SLA gocu SAYACA yaziyor (BaBa basamagi sayaca dahil ediliyor)
    sonuclar.append(("M8-sla-sayaca-yaziyor",) + mutant_kos(
        "M8-sla-sayaca-yaziyor",
        capali_degistir(
            kaynak,
            '    kayit["merdiven"]["basamak"] = BASAMAK_OKAN\n',
            '    kayit["merdiven"]["basamak"] = BASAMAK_OKAN\n'
            '    kayit["merdiven"]["denemeler"].append(\n'
            '        {"damga": "sla", "basamak": BASAMAK_BABA, "hal": "YETENEK",\n'
            '         "sayilir": True})\n', "M8"),
        tmp, ("S6d",),
        ("S1", "S2", "S3", "S4", "S5", "S8", "S9", "S6a", "S6b", "S6c")))

    # M9 — SAYAC BASAMAGA GORE SIFIRLANIYOR (K257'nin yasakladigi tam kusur)
    sonuclar.append(("M9-sayac-katta-sifirlanir",) + mutant_kos(
        "M9-sayac-katta-sifirlanir",
        capali_degistir(
            kaynak,
            "    return sum(1 for d in denemeler(kayit) if d.get(\"sayilir\"))",
            "    _b = merdiven_kaydi(kayit).get(\"basamak\")\n"
            "    return sum(1 for d in denemeler(kayit)\n"
            "               if d.get(\"sayilir\") and d.get(\"basamak\") == _b)",
            "M9"),
        tmp, ("S3b", "S3c", "S3d", "S8-1", "S8-2", "S8-3", "S8-4", "S8-5",
              "S6a", "S9a"),
        ("S1", "S2-KOTA", "S2-YETENEK", "S2-BITMEYEN_TUR", "S2-KAPI_REDDI-yon",
         "S4b", "S4c", "S4d", "S4e", "S5")))

    # M10 — 🔴 TOHUMLAMA SOKULDU: K257 oncesi kaydin gecmisi SILINIR.
    # Bu, ilk kurulumda CANLI olarak olculen kusurdur (nobet-kabul-test vaka 6
    # kirmizi yandi): `dagitim_sayisi=3` olan kalem sifirdan basliyordu.
    sonuclar.append(("M10-tohumlama-sokuldu",) + mutant_kos(
        "M10-tohumlama-sokuldu",
        capali_degistir(kaynak,
                        "    if eski <= 0:\n"
                        "        return [], basamaklar[0][\"ad\"]\n",
                        "    if True:\n"
                        "        return [], basamaklar[0][\"ad\"]\n", "M10"),
        tmp, ("S9a", "S9b", "S9c", "S9d"),
        ("S1", "S2", "S3", "S4", "S5", "S6", "S8", "S9e", "S9f")))

    return sonuclar


def bolum_s7_mutant(kapi_kaynak):
    """K257(e) — ZINCIR mutantlari. Hedef `nobet-kapi.py` KAYNAGIDIR (modul
    yuklenmez, yalniz S7 ast ekseni yeniden kosar).

    Uc ayri iddia UC AYRI seyi olcer ve bunu mutantlar KANITLAR:
      S7d "elle liste degil" · S7h "canli kumeyi okuyor" · S7j "TAM turemis".
    M11 yalniz S7j'yi oldurur (kirpma d/h'yi gecerdi), M12 yalniz S7d+S7h'yi
    oldurur (elle tuple'da kirpma YOK). Ucu de ayni sey olsaydi bu mumkun olmazdi.
    """
    print("--- BOLUM M-S7: ZINCIR MUTANTLARI (nobet-kapi.py kaynagi) ---")
    sonuclar = []
    if kapi_kaynak is None:
        return sonuclar

    def _kos(ad, mutant_kaynak, hedef_onek, yan_onek):
        if mutant_kaynak is None:
            print("MUTANT=%-34s HEDEF_KOL=OLCULEMEDI (capa bayat)" % ad)
            sonuclar.append((ad, None, None))
            return
        isaret = len(VAKALAR)
        try:
            bolum_s7(mutant_kaynak, ek="-%s" % ad)
        except Exception as hata:                               # noqa: BLE001
            vaka("MUTANT_PATLADI-%s" % ad, "YOK", type(hata).__name__)
        sonuclar.append((ad,) + _atif(ad, isaret, hedef_onek, yan_onek))

    _kos("M11-zincir-kirpildi",
         capali_degistir(kapi_kaynak,
                         "TUR_MOTOR_ZINCIRI = tuple(CANLI_ISCI_MOTORLARI)",
                         "TUR_MOTOR_ZINCIRI = tuple(CANLI_ISCI_MOTORLARI[:1])",
                         "M11"),
         # 🔴 HEDEF yalniz S7j: kirpilmis zincir HALA "TURETILDI" ve "OKUR"
         # oldugu icin S7d/S7h YASAR — tam da S7j'nin var olma sebebi budur.
         ("S7j",),
         ("S7a", "S7b", "S7c", "S7d", "S7e", "S7f", "S7g", "S7h", "S7i"))

    _kos("M12-zincir-elle-yazildi",
         capali_degistir(kapi_kaynak,
                         "TUR_MOTOR_ZINCIRI = tuple(CANLI_ISCI_MOTORLARI)",
                         'TUR_MOTOR_ZINCIRI = ("minimax-m3",)', "M12"),
         # HEDEF S7d+S7h; S7j HEDEF DEGIL: elle tuple'da kirpma YOKTUR, o vaka
         # dogru olarak YASAR (hedefe konsaydi mutant "YASADI" gorunurdu).
         ("S7d", "S7h"),
         ("S7a", "S7b", "S7c", "S7e", "S7f", "S7g", "S7i", "S7j"))

    return sonuclar


def bolum_kontrol(kaynak, tmp):
    """KONTROL MUTANTLARI — kirmiziyi mutasyon mu harness mi uretti?"""
    print("--- BOLUM K: KONTROL MUTANTLARI ---")
    kontroller = []

    # K0 — kaynak DEGISMEDEN ayni harness'ten gecer: hepsi YESIL olmali.
    isaret = len(VAKALAR)
    yol = os.path.join(tmp, "kontrol_k0.py")
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(kaynak)
    _bolumleri_kos(modul_yukle(yol, "k257_kontrol_k0"), "-K0")
    k0 = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    kontroller.append(("K0-harness", all(v[3] for v in k0), len(k0)))

    # KX — ILGISIZ kol bozulur (yalniz rapor BICIMI). Hedef vakalar YASAMALI:
    # tautoloji varsa burada gorunur ([[isci-yesil-tablo-ic-olcumu-bosaltir]]).
    kx_kaynak = capali_degistir(
        kaynak, '    return ("MERDIVEN kalem=%s HAL=%s YON=%s SAYILIR=%d SAYAC=%d "',
        '    return ("MRDVN kalem=%s HAL=%s YON=%s SAYILIR=%d SAYAC=%d "', "KX")
    if kx_kaynak is None:
        kontroller.append(("KX-ilgisiz-kol", None, 0))
    else:
        isaret = len(VAKALAR)
        yol = os.path.join(tmp, "kontrol_kx.py")
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(kx_kaynak)
        _bolumleri_kos(modul_yukle(yol, "k257_kontrol_kx"), "-KX")
        kx = VAKALAR[isaret:]
        del VAKALAR[isaret:]
        kontroller.append(("KX-ilgisiz-kol", all(v[3] for v in kx), len(kx)))

    for ad, yesil, n in kontroller:
        print("KONTROL=%-20s SONUC=%-11s (%d vaka)"
              % (ad, {True: "YESIL", False: "KIRMIZI", None: "OLCULEMEDI"}[yesil], n))
    return kontroller


# ===========================================================================

def main():
    try:
        with open(MERDIVEN_YOLU, encoding="utf-8") as dosya:
            kaynak = dosya.read()
    except OSError as hata:
        print("KABUL=KALDI (nobet_merdiven.py okunamadi: %s)" % hata)
        return 2
    M = modul_yukle(MERDIVEN_YOLU, "k257_merdiven")

    kapi_kaynak = None
    try:
        with open(NOBET_KAPI, encoding="utf-8") as dosya:
            kapi_kaynak = dosya.read()
    except OSError:
        pass

    tmp = tempfile.mkdtemp(prefix="k257-merdiven-")
    try:
        _bolumleri_kos(M, "")
        if kapi_kaynak is None:
            vaka("S7-CAGRI_YERI", "OLCULDU", "OLCULEMEDI(nobet-kapi.py yok)")
        else:
            bolum_s7(kapi_kaynak)
        mutantlar = bolum_mutant(kaynak, tmp)
        mutantlar += bolum_s7_mutant(kapi_kaynak)
        kontroller = bolum_kontrol(kaynak, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for *_x, g in VAKALAR if g)
    toplam = len(VAKALAR)
    m_hedef = sum(1 for _, h, _y in mutantlar if h)
    m_tam = sum(1 for _, h, y in mutantlar if h and y)
    m_olculemedi = sum(1 for _, h, _y in mutantlar if h is None)
    k_yesil = sum(1 for _, y, _n in kontroller if y)

    for satir in BAYAT_CAPALAR:
        print("BAYAT_CAPA=%s" % satir)

    print("MUTANT=%d/%d  HEDEF_KOL_ATFI=%d/%d  OLCULEMEDI=%d"
          % (m_tam, len(mutantlar), m_hedef, len(mutantlar), m_olculemedi))
    print("KONTROL=%d/%d" % (k_yesil, len(kontroller)))
    # 🔴 KAPSAM SAYIYLA (oran DEGIL): batarya kac vaka kostugunu BASAR.
    print("KAPSAM VAKA=%d/%d MUTANT=%d/%d KONTROL=%d/%d"
          % (toplam, VAKA_TABANI, len(mutantlar), MUTANT_TABANI,
             len(kontroller), KONTROL_TABANI))
    print("TOPLAM=%d GECTI=%d KALDI=%d" % (toplam, gecen, toplam - gecen))

    kapsam_hatasi = (toplam < VAKA_TABANI or len(mutantlar) < MUTANT_TABANI
                     or len(kontroller) < KONTROL_TABANI)
    if BAYAT_CAPALAR or m_olculemedi:
        print("KABUL=OLCULEMEDI (%d bayat capa, %d mutant olculemedi)"
              % (len(BAYAT_CAPALAR), m_olculemedi))
        return 3
    if k_yesil != len(kontroller):
        print("KABUL=OLCULEMEDI (kontrol mutanti kirmizi — batarya kararsiz)")
        return 3
    if kapsam_hatasi:
        print("KABUL=KALDI (KAPSAM TABANI ALTINDA)")
        return 1
    if gecen == toplam and m_tam == len(mutantlar):
        print("KABUL=GECTI (%d/%d vaka)" % (gecen, toplam))
        return 0
    print("KABUL=KALDI (%d/%d vaka, %d/%d mutant)"
          % (gecen, toplam, m_tam, len(mutantlar)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
