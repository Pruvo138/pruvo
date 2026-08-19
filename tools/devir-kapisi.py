#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/devir-kapisi.py — N2 (C): 4 SAAT HAREKETSIZ KALEM TAMIRCI'YE DEVREDILIR.

Okan'in vakasi (birebir): "MaCiT 100-100 urun ekliyor, iletiyi gormedi, isine
devam etti; tamirat yapilmadigi icin **tum mimarlar MaCiT'i bekledi**."
(B) yeni is baslatmayi durdurur; ama sahip hic donmezse ekip yine bekler.
(C) o beklemeyi bitirir: kalem 4 saat kimildamazsa **Tamirci'ye (KraL) gecer**,
kaciran evin hanesine **ihlal** islenir (sayac; ceza DEGIL, olcu).

HAREKET NEDIR (spec'in izin verdigi uc olcutten SECILEN — raporda yazilir)
--------------------------------------------------------------------------
**Kalemin defter satirinin DEGISMESI.** Her kalem icin satirin sha256 imzasi
durum dosyasinda tutulur; imza degisirse damga `simdi`ye cekilir. Bu olcut:
  - her ev icin ayni sekilde calisir (defterler ayri depolarda/dizinlerde),
  - `git` gecmisi gerektirmez (MaCiT'in defteri KraL'in deposunda degildir),
  - "durum ACIK->KAPANDI", "is metni guncellendi", "kanit eklendi" — hepsini
    hareket sayar.
🔴 ILK GORULEN kalem TAZE kaydedilir ve ASLA hemen devredilmez: olculmemis
   kalemi devretmek "olcum yerine tahmin"dir. Fail-closed yon budur.

BES KOL (her birinin MUTANTI ve HEDEF KOL ATFI vardir — K182)
--------------------------------------------------------------
  N2C-DURGUN      damga >= 240 dk  -> DEVIR
  N2C-TAZE        damga <  240 dk  -> DEVIR YOK (negatif vaka)
  N2C-IHLAL       devirde kaciran evin hanesine +1
  N2C-TEKSAHIP    devir sonrasi kalem **iki defterde birden acik kalmaz**
  N2C-OLCULEMEDI  damga/defter cozulemedi -> DEVIR YOK (fail-closed)

TEK KAYNAK
----------
  - 4 saat esigi + `DEVREDILDI`/`T5-IZ` yazicisi: `tools/durgun-kalem-kapisi.py`
    (T5). Bu dosya ikinci bir esik ya da ikinci bir posta yazici TANIMLAMAZ.
  - Defter parser + EV->dizin: `tools/parti-borc-kapisi.py` (T4).
  - 🔴 Baska evin defterine ELLE satir YAZILMAZ; yazan MEKANIZMA budur.

KABUL (calistirilabilir)
------------------------
  python3 tools/devir-kapisi.py --kendini-test
    son satir + rc=0:  MUTANT=5/5 HEDEF_KOL_ATFI=5/5 KONTROL=4/4

  python3 tools/devir-kapisi.py --rapor --simdi 2026-08-19T20:00:00Z   (YAZMAZ)
  python3 tools/devir-kapisi.py --uygula --simdi <ISO>                 (YAZAR)

Cikis kodu: 0 = tamam · 1 = kusur · 2 = OLCULEMEDI.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone


_BU_DIZIN = os.path.dirname(os.path.abspath(__file__))


def _yukle(ad, dosya):
    yol = os.path.join(_BU_DIZIN, dosya)
    try:
        spec = importlib.util.spec_from_file_location(ad, yol)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


T4 = _yukle("pruvo_t4_borc", "parti-borc-kapisi.py")
T5 = _yukle("pruvo_t5_durgun", "durgun-kalem-kapisi.py")


# ---- sabitler -----------------------------------------------------------------
# 🔴 ESIK T5'ten TURER — ikinci "240" YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
ESIK_DAKIKA = T5.ESIK_DAKIKA if T5 is not None else None

TAMIRCI = "KraL"
DURUM_DOSYA_ADI = "n2-devir-durum.json"
IHLAL_DOSYA_ADI = "n2-ihlal-sayaci.json"
POSTA_DOSYA_ADI = "mimar-posta-kutusu.md"
ACIK_KALEM_DOSYA_ADI = "acik-kalemler.md"

# Devredilen kalemin KAYNAK defterindeki yeni durumu. T4'un ACIK_DURUMLAR
# kumesinde OLMAYAN bir deger olmak ZORUNDA (yoksa kaynak ev acik sayilmaya
# devam eder ve kalem IKI defterde birden acik kalir — tek sahip invaryanti).
DEVREDILDI_DURUMU = "DEVREDILDI"

# Hedef (Tamirci) defterinde acilan satirin durumu.
HEDEF_DURUMU = "🔧"

N2C_DURGUN_JETON     = "N2C-DURGUN"
N2C_TAZE_JETON       = "N2C-TAZE"
N2C_IHLAL_JETON      = "N2C-IHLAL"
N2C_TEKSAHIP_JETON   = "N2C-TEKSAHIP"
N2C_OLCULEMEDI_JETON = "N2C-OLCULEMEDI"

MUTANT_HEDEF = {
    "M1": N2C_DURGUN_JETON,
    "M2": N2C_TAZE_JETON,
    "M3": N2C_IHLAL_JETON,
    "M4": N2C_TEKSAHIP_JETON,
    "M5": N2C_OLCULEMEDI_JETON,
}

RC_TAMAM = 0
RC_KUSUR = 1
RC_OLCULEMEDI = 2


# ------------------------------------------------------------------------------
# YOLLAR
# ------------------------------------------------------------------------------
def ev_koku(ev, koku_root=None):
    """Bir EV'in memory dizini. koku_root verilirse izole (kendini-test)."""
    if koku_root:
        return os.path.join(koku_root, ev, "memory")
    if T4 is None:
        return None
    dizin = T4.EV_DIZIN.get(ev)
    return os.path.join(dizin, "memory") if dizin else None


def defter_yolu(ev, koku_root=None):
    kok = ev_koku(ev, koku_root)
    return os.path.join(kok, ACIK_KALEM_DOSYA_ADI) if kok else None


def posta_yolu(ev, koku_root=None):
    kok = ev_koku(ev, koku_root)
    return os.path.join(kok, POSTA_DOSYA_ADI) if kok else None


def durum_yolu(koku_root=None):
    kok = ev_koku(TAMIRCI, koku_root)
    return os.path.join(kok, DURUM_DOSYA_ADI) if kok else None


def ihlal_yolu(koku_root=None):
    kok = ev_koku(TAMIRCI, koku_root)
    return os.path.join(kok, IHLAL_DOSYA_ADI) if kok else None


def izlenen_evler():
    """Devir taramasina giren evler: TAMIRCI HARIC bilinen evler."""
    if T4 is None:
        return []
    return [e for e in sorted(T4.EV_BILINEN)
            if e not in (TAMIRCI, "BaBa", "ORTAK")]


# ------------------------------------------------------------------------------
# DURUM / IHLAL DOSYALARI (atomik)
# ------------------------------------------------------------------------------
def _json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else dict(varsayilan)
    except Exception:
        return dict(varsayilan)


def _json_yaz(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".n2c-", dir=os.path.dirname(yol))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def _imza(kalem):
    """Bir kalemin defter satirinin icerik imzasi (hareket olcutu)."""
    ham = "|".join([kalem.get("kimlik") or "", kalem.get("durum") or "",
                    kalem.get("is") or "", kalem.get("kanit") or ""])
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _simdi_coz(metin):
    if T5 is not None:
        return T5._simdi_coz(metin)
    return None


# ------------------------------------------------------------------------------
# SINIFLANDIRMA — N2C-DURGUN / N2C-TAZE / N2C-OLCULEMEDI
# ------------------------------------------------------------------------------
def siniflandir(simdi, *, koku_root=None, mutant=None):
    """Tum izlenen evlerin acik kalemlerini siniflandirir. YAZMAZ.

    Return: {"kalemler": [...], "durum": {...}, "hata": str|None}
      kalem = {ev, kimlik, durum, is, kanit, imza, damga, fark_dk, kol}
    """
    out = {"kalemler": [], "durum": {}, "hata": None}
    if T4 is None or T5 is None:
        out["hata"] = "%s T4/T5 yuklenemedi" % N2C_OLCULEMEDI_JETON
        return out

    dyol = durum_yolu(koku_root)
    if not dyol:
        out["hata"] = "%s durum dosyasi yolu cozulemedi" % N2C_OLCULEMEDI_JETON
        return out
    durum = _json_oku(dyol, {})
    out["durum"] = durum

    for ev in izlenen_evler():
        defter = defter_yolu(ev, koku_root)
        if not defter:
            continue
        kalemler, okundu, hata = T4.acik_kalem_listesi(defter)
        if not okundu:
            # Defteri okunamayan ev OLCULEMEDI'dir; kalemleri UYDURULMAZ.
            out["kalemler"].append({
                "ev": ev, "kimlik": "-", "durum": "-", "is": "",
                "kanit": "", "imza": None, "damga": None, "fark_dk": None,
                "kol": N2C_OLCULEMEDI_JETON, "hata": hata})
            continue
        for k in kalemler:
            anahtar = "%s/%s" % (ev, k["kimlik"])
            imza = _imza(k)
            kayit = durum.get(anahtar) or {}
            eski_imza = kayit.get("imza")
            eski_damga = kayit.get("damga")

            if eski_imza is None or eski_imza != imza or not eski_damga:
                # Ilk gorulen ya da DEGISMIS kalem: hareket VAR -> damga simdi.
                damga_dt = simdi
                yeni_damga = _iso(simdi)
            else:
                damga_dt = T5._damga_coz(eski_damga, simdi=simdi)
                yeni_damga = eski_damga

            if damga_dt is None:
                kol = N2C_OLCULEMEDI_JETON
                fark = None
            else:
                fark = (simdi - damga_dt).total_seconds() / 60.0
                if mutant == "M5":
                    # FAIL-OPEN mutanti: cozulemeyen damgayi 'cok eski' say.
                    kol = N2C_DURGUN_JETON
                elif mutant == "M1":
                    kol = N2C_TAZE_JETON          # durgun kolu oldurulur
                elif mutant == "M2":
                    kol = N2C_DURGUN_JETON        # taze kolu oldurulur
                elif fark >= ESIK_DAKIKA:
                    kol = N2C_DURGUN_JETON
                else:
                    kol = N2C_TAZE_JETON

            if damga_dt is None and mutant == "M5":
                kol = N2C_DURGUN_JETON
                fark = float(ESIK_DAKIKA) + 1.0

            out["kalemler"].append({
                "ev": ev, "kimlik": k["kimlik"], "durum": k["durum"],
                "is": k["is"], "kanit": k["kanit"], "imza": imza,
                "damga": yeni_damga, "fark_dk": fark, "kol": kol,
                "satir_no": k.get("satir_no"), "hata": None})
    return out


# ------------------------------------------------------------------------------
# DEFTER YAZIMI — TEK SAHIP INVARYANTI (N2C-TEKSAHIP)
# ------------------------------------------------------------------------------
def _satiri_kapat(defter_metni, kimlik, *, mutant=None):
    """Kaynak defterde `kimlik` satirinin DURUM sutununu DEVREDILDI yapar.

    Return: (yeni_metin, degisti_mi). M4 mutanti bu adimi ATLAR -> kalem
    iki defterde birden ACIK kalir (tek sahip invaryanti kirilir).
    """
    if mutant == "M4":
        return defter_metni, False
    satirlar = defter_metni.splitlines()
    degisti = False
    for i, satir in enumerate(satirlar):
        if not T4.TabloSatir.match(satir):
            continue
        kolonlar = satir.split("|")
        if len(kolonlar) < 7:
            continue
        if kolonlar[1].strip() != kimlik:
            continue
        if kolonlar[5].strip() not in T4.ACIK_DURUMLAR:
            continue
        kolonlar[5] = " %s " % DEVREDILDI_DURUMU
        satirlar[i] = "|".join(kolonlar)
        degisti = True
    return "\n".join(satirlar) + ("\n" if defter_metni.endswith("\n") else ""), degisti


def _satir_ac(defter_metni, kalem, kaynak_ev):
    """Hedef (Tamirci) defterine kalemi ACIK olarak ekler. Zaten varsa EKLEMEZ."""
    kimlik = kalem["kimlik"]
    for satir in defter_metni.splitlines():
        if not T4.TabloSatir.match(satir):
            continue
        kolonlar = satir.split("|")
        if len(kolonlar) >= 7 and kolonlar[1].strip() == kimlik:
            return defter_metni, False
    yeni = ("| %s | %s | %s→%s | %s | %s | devir: 4 saat hareketsiz (N2C) |"
            % (kimlik, kalem.get("damga", "")[:10], kaynak_ev, TAMIRCI,
               kalem.get("is") or "-", HEDEF_DURUMU))
    metin = defter_metni if defter_metni.endswith("\n") else defter_metni + "\n"
    return metin + yeni + "\n", True


def _dosya_yaz_atomik(yol, metin):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".n2c-defter-", dir=os.path.dirname(yol))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(metin)
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


# ------------------------------------------------------------------------------
# DEVIR — YAZAN MEKANIZMA (elle satir YAZILMAZ)
# ------------------------------------------------------------------------------
def devret(simdi, *, koku_root=None, mutant=None, uygula=False):
    """Durgun kalemleri Tamirci'ye devreder.

    Return: {"devredilen": [...], "taze": n, "olculemedi": n, "ihlal": {...},
             "hata": str|None, "yazildi": bool}
    """
    sonuc = {"devredilen": [], "taze": 0, "olculemedi": 0, "ihlal": {},
             "hata": None, "yazildi": False}
    sinif = siniflandir(simdi, koku_root=koku_root, mutant=mutant)
    if sinif["hata"]:
        sonuc["hata"] = sinif["hata"]
        return sonuc

    durum = dict(sinif["durum"])
    ihlal = _json_oku(ihlal_yolu(koku_root), {})
    hedef_defter_yolu = defter_yolu(TAMIRCI, koku_root)
    hedef_posta = posta_yolu(TAMIRCI, koku_root)

    for k in sinif["kalemler"]:
        anahtar = "%s/%s" % (k["ev"], k["kimlik"])
        if k["kol"] == N2C_OLCULEMEDI_JETON:
            sonuc["olculemedi"] += 1
            continue
        if k["kol"] == N2C_TAZE_JETON:
            sonuc["taze"] += 1
            durum[anahtar] = {"imza": k["imza"], "damga": k["damga"]}
            continue

        # --- N2C-DURGUN: devir ---------------------------------------------
        kayit = {"ev": k["ev"], "kimlik": k["kimlik"], "damga": k["damga"],
                 "fark_dk": k["fark_dk"], "posta": False, "iz": False,
                 "kaynak_kapandi": False, "hedef_acildi": False}
        if not uygula:
            sonuc["devredilen"].append(kayit)
            continue

        # 1) posta: DEVREDILDI (hedef) + T5-IZ (kaynak) — T5'in TEK yazicisi
        pk = T5.devir_yap({"kimlik": k["kimlik"]}, TAMIRCI, k["damga"],
                          posta_yolu(k["ev"], koku_root), hedef_posta)
        kayit["posta"] = bool(pk.get("yazildi"))
        kayit["iz"] = bool(pk.get("iz_yazildi"))

        # 2) kaynak defterde satiri KAPAT (tek sahip invaryanti)
        kyol = defter_yolu(k["ev"], koku_root)
        try:
            with open(kyol, encoding="utf-8") as f:
                kaynak_metin = f.read()
            yeni_kaynak, degisti = _satiri_kapat(kaynak_metin, k["kimlik"],
                                                 mutant=mutant)
            if degisti:
                _dosya_yaz_atomik(kyol, yeni_kaynak)
            kayit["kaynak_kapandi"] = degisti
        except Exception as e:
            sonuc["hata"] = "%s kaynak defter yazilamadi: %r" % (
                N2C_OLCULEMEDI_JETON, e)

        # 3) hedef deftere satiri AC
        try:
            hedef_metin = ""
            if os.path.isfile(hedef_defter_yolu):
                with open(hedef_defter_yolu, encoding="utf-8") as f:
                    hedef_metin = f.read()
            yeni_hedef, acildi = _satir_ac(hedef_metin, k, k["ev"])
            if acildi:
                _dosya_yaz_atomik(hedef_defter_yolu, yeni_hedef)
            kayit["hedef_acildi"] = acildi
        except Exception as e:
            sonuc["hata"] = "%s hedef defter yazilamadi: %r" % (
                N2C_OLCULEMEDI_JETON, e)

        # 4) ihlal sayaci: kaciran evin hanesine +1 (ceza DEGIL, olcu)
        if mutant != "M3":
            hane = ihlal.get(k["ev"]) or {"ihlal": 0, "son": None, "kalemler": []}
            hane["ihlal"] = int(hane.get("ihlal") or 0) + 1
            hane["son"] = _iso(simdi)
            kalemler = list(hane.get("kalemler") or [])
            if k["kimlik"] not in kalemler:
                kalemler.append(k["kimlik"])
            hane["kalemler"] = kalemler
            ihlal[k["ev"]] = hane

        durum[anahtar] = {"imza": None, "damga": _iso(simdi),
                          "devredildi": _iso(simdi)}
        sonuc["devredilen"].append(kayit)

    sonuc["ihlal"] = ihlal
    if uygula:
        try:
            _json_yaz(durum_yolu(koku_root), durum)
            _json_yaz(ihlal_yolu(koku_root), ihlal)
            sonuc["yazildi"] = True
        except Exception as e:
            sonuc["hata"] = "%s durum/ihlal yazilamadi: %r" % (
                N2C_OLCULEMEDI_JETON, e)
    else:
        # kuru kosumda bile ILK GORULEN kalemlerin damgasi kaydedilmeli mi?
        # HAYIR: --rapor YAZMAZ. Damga yalniz --uygula ile kalicilasir.
        pass
    return sonuc


def hukum_satiri(s):
    return ("N2C DEVREDILEN=%d TAZE=%d OLCULEMEDI=%d IHLAL_EV=%d YAZILDI=%s"
            % (len(s["devredilen"]), s["taze"], s["olculemedi"],
               len(s["ihlal"]), s["yazildi"]))


# ------------------------------------------------------------------------------
# KENDINI-TEST — 5 mutant + hedef kol atfi + 4 kontrol
# ------------------------------------------------------------------------------
def _defter_yaz(yol, kalemler):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    satirlar = ["# sentetik defter", "", "## ACIK KALEMLER", "",
                "| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |",
                "|---|---|---|---|---|---|"]
    for kimlik, durum, isim in kalemler:
        satirlar.append("| %s | 2026-08-19 | X→Y | %s | %s | - |"
                        % (kimlik, isim, durum))
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")


def _kurulum(kok, simdi, yas_dk):
    """Izole fikstur: MaCiT'te 1 kalem (yas_dk once damgali), KraL bos."""
    for ev in (TAMIRCI, "MaCiT"):
        os.makedirs(os.path.join(kok, ev, "memory"), exist_ok=True)
        with open(posta_yolu(ev, kok), "w", encoding="utf-8") as f:
            f.write("# sentetik posta kutusu\n")
    _defter_yaz(defter_yolu("MaCiT", kok), [("K777", "🔧", "sentetik tamirat")])
    _defter_yaz(defter_yolu(TAMIRCI, kok), [])
    # bos evler: diger izlenen evler icin defter YOK -> OLCULEMEDI kolu
    # damgayi geriye at
    kalemler, _o, _h = T4.acik_kalem_listesi(defter_yolu("MaCiT", kok))
    durum = {"MaCiT/K777": {"imza": _imza(kalemler[0]),
                            "damga": _iso(simdi - timedelta(minutes=yas_dk))}}
    _json_yaz(durum_yolu(kok), durum)
    _json_yaz(ihlal_yolu(kok), {})


def _acik_mi(yol, kimlik):
    """Kalem bu defterde ACIK sayiliyor mu?"""
    kalemler, okundu, _h = T4.acik_kalem_listesi(yol)
    if not okundu:
        return False
    return any(k["kimlik"] == kimlik for k in kalemler)


def kendini_test(gecici_kok):
    simdi = datetime(2026, 8, 19, 20, 0, 0, tzinfo=timezone.utc)
    print("N2C DEVIR KAPISI — KENDINI-TEST")
    print("izolasyon koku: %s" % gecici_kok)
    print("simdi: %s (enjekte)" % _iso(simdi))
    print("esik: %s dakika (T5'ten turedi)" % ESIK_DAKIKA)
    print("")

    if T4 is None or T5 is None:
        print("T4/T5 YUKLENEMEDI — olcum ANLAMSIZ.")
        print("MUTANT=0/5 HEDEF_KOL_ATFI=0/5 KONTROL=0/4")
        return 1

    def senaryo(yas_dk, mutant=None, uygula=False, alt="s"):
        kok = os.path.join(gecici_kok, "%s-%s-%s" % (alt, yas_dk, mutant))
        os.makedirs(kok, exist_ok=True)
        _kurulum(kok, simdi, yas_dk)
        s = devret(simdi, koku_root=kok, mutant=mutant, uygula=uygula)
        return kok, s

    # --- TABAN --------------------------------------------------------------
    _k_eski, eski = senaryo(300, alt="taban-eski")     # 5 saat -> DURGUN
    _k_yeni, yeni = senaryo(60, alt="taban-yeni")      # 1 saat -> TAZE
    taban_ok = (len(eski["devredilen"]) == 1 and eski["taze"] == 0
                and len(yeni["devredilen"]) == 0 and yeni["taze"] == 1)
    print("TABAN (mutantsiz, KURU):")
    print("  300 dk (>=240): %s" % hukum_satiri(eski))
    print("   60 dk (< 240): %s" % hukum_satiri(yeni))
    print("  %s" % ("✓ taban dogru" if taban_ok else "✗ TABAN KIRMIZI"))
    print("")
    if not taban_ok:
        print("MUTANT=0/5 HEDEF_KOL_ATFI=0/5 KONTROL=0/4")
        return 1

    # --- MUTANTLAR ----------------------------------------------------------
    mutant_sayaci = 0
    atif_sayaci = 0
    for ad in sorted(MUTANT_HEDEF):
        kol = MUTANT_HEDEF[ad]
        print("MUTANT %s -> hedef kol %s" % (ad, kol))
        hedef_kirmizi = False
        yan_bozulan = []

        if ad == "M1":     # DURGUN kolu oldurulur -> 300 dk devredilmez
            _k, m = senaryo(300, mutant="M1", alt="m1")
            hedef_kirmizi = (len(m["devredilen"]) == 0 and m["taze"] == 1)
            print("  300 dk: normal=%s | mutant=%s"
                  % (hukum_satiri(eski), hukum_satiri(m)))
            _k2, m2 = senaryo(60, mutant="M1", alt="m1y")
            if (len(m2["devredilen"]), m2["taze"]) != (0, 1):
                yan_bozulan.append("60dk")
        elif ad == "M2":   # TAZE kolu oldurulur -> 60 dk DEVREDILIR (erken!)
            _k, m = senaryo(60, mutant="M2", alt="m2")
            hedef_kirmizi = (len(m["devredilen"]) == 1)
            print("  60 dk: normal=%s | mutant=%s"
                  % (hukum_satiri(yeni), hukum_satiri(m)))
            print("  -> M2 altinda 4 SAAT DOLMADAN devir olurdu (kol koruyor)")
            _k2, m2 = senaryo(300, mutant="M2", alt="m2e")
            if len(m2["devredilen"]) != 1:
                yan_bozulan.append("300dk")
        elif ad == "M3":   # IHLAL kolu oldurulur -> sayac artmaz
            kn, n = senaryo(300, uygula=True, alt="m3n")
            km, m = senaryo(300, mutant="M3", uygula=True, alt="m3m")
            n_ihlal = (n["ihlal"].get("MaCiT") or {}).get("ihlal", 0)
            m_ihlal = (m["ihlal"].get("MaCiT") or {}).get("ihlal", 0)
            hedef_kirmizi = (n_ihlal == 1 and m_ihlal == 0)
            print("  ihlal sayaci: normal=%d | mutant=%d" % (n_ihlal, m_ihlal))
            if len(m["devredilen"]) != 1:
                yan_bozulan.append("devir-sayisi")
        elif ad == "M4":   # TEKSAHIP kolu oldurulur -> iki defterde birden acik
            kn, n = senaryo(300, uygula=True, alt="m4n")
            km, m = senaryo(300, mutant="M4", uygula=True, alt="m4m")
            n_kaynak = _acik_mi(defter_yolu("MaCiT", kn), "K777")
            n_hedef = _acik_mi(defter_yolu(TAMIRCI, kn), "K777")
            m_kaynak = _acik_mi(defter_yolu("MaCiT", km), "K777")
            m_hedef = _acik_mi(defter_yolu(TAMIRCI, km), "K777")
            hedef_kirmizi = ((not n_kaynak and n_hedef)
                             and (m_kaynak and m_hedef))
            print("  normal: kaynakta acik=%s hedefte acik=%s (beklenen False/True)"
                  % (n_kaynak, n_hedef))
            print("  mutant: kaynakta acik=%s hedefte acik=%s (IKI DEFTERDE BIRDEN)"
                  % (m_kaynak, m_hedef))
            if (m["ihlal"].get("MaCiT") or {}).get("ihlal", 0) != 1:
                yan_bozulan.append("ihlal")
        elif ad == "M5":   # OLCULEMEDI kolu fail-OPEN yapilir
            kok = os.path.join(gecici_kok, "m5")
            os.makedirs(kok, exist_ok=True)
            _kurulum(kok, simdi, 300)
            # damgayi BOZ: cozulemez deger
            _json_yaz(durum_yolu(kok),
                      {"MaCiT/K777": {"imza": "BOZUK-IMZA-ESLESMEZ",
                                      "damga": "cozulemez-damga"}})
            n = devret(simdi, koku_root=kok, mutant=None)
            kok2 = os.path.join(gecici_kok, "m5m")
            os.makedirs(kok2, exist_ok=True)
            _kurulum(kok2, simdi, 300)
            _json_yaz(durum_yolu(kok2),
                      {"MaCiT/K777": {"imza": "BOZUK-IMZA-ESLESMEZ",
                                      "damga": "cozulemez-damga"}})
            m = devret(simdi, koku_root=kok2, mutant="M5")
            # normal: imza eslesmiyor -> hareket VAR -> TAZE (devir YOK)
            # mutant M5: cozulemeyen damga 'cok eski' sayilir -> DEVIR
            hedef_kirmizi = (len(n["devredilen"]) == 0
                             and len(m["devredilen"]) == 1)
            print("  bozuk damga: normal=%s | mutant=%s"
                  % (hukum_satiri(n), hukum_satiri(m)))

        yan_yesil = not yan_bozulan
        print("  yan eksen bozulan: %s" % (",".join(yan_bozulan) or "-"))
        if hedef_kirmizi:
            mutant_sayaci += 1
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        if hedef_kirmizi and yan_yesil:
            atif_sayaci += 1
            print("  ATIF : hedef kol kirmizi + yan eksen YESIL")
        else:
            print("  ATIF : KUSUR (hedef kol ya da yan eksen tutmadi)")
        print("")

    # --- KONTROLLER ---------------------------------------------------------
    kontrol = 0
    kok, s = senaryo(300, uygula=True, alt="k")

    # K1: kutuya DEVREDILDI satiri dustu (elle DEGIL, mekanizma yazdi)
    with open(posta_yolu(TAMIRCI, kok), encoding="utf-8") as f:
        hedef_posta_metni = f.read()
    with open(posta_yolu("MaCiT", kok), encoding="utf-8") as f:
        kaynak_posta_metni = f.read()
    k1 = ("DEVREDILDI: K777 -> KraL" in hedef_posta_metni
          and "T5-IZ" in kaynak_posta_metni)
    print("KONTROL K1 kutuda DEVREDILDI + kaynakta T5-IZ: %s"
          % ("GECTI" if k1 else "KUSUR"))
    print("    | hedef : %s" % hedef_posta_metni.strip().splitlines()[-1])
    print("    | kaynak: %s" % kaynak_posta_metni.strip().splitlines()[-1])
    kontrol += 1 if k1 else 0

    # K2: ihlal sayaci +1
    ihlal = _json_oku(ihlal_yolu(kok), {})
    k2 = ((ihlal.get("MaCiT") or {}).get("ihlal") == 1)
    print("KONTROL K2 ihlal sayaci +1: %s (%s)"
          % ("GECTI" if k2 else "KUSUR", json.dumps(ihlal, ensure_ascii=False)))
    kontrol += 1 if k2 else 0

    # K3: TEK SAHIP — kalem iki defterde birden acik DEGIL
    kaynak_acik = _acik_mi(defter_yolu("MaCiT", kok), "K777")
    hedef_acik = _acik_mi(defter_yolu(TAMIRCI, kok), "K777")
    k3 = (not kaynak_acik) and hedef_acik
    print("KONTROL K3 tek sahip (kaynak kapali=%s, hedef acik=%s): %s"
          % (not kaynak_acik, hedef_acik, "GECTI" if k3 else "KUSUR"))
    kontrol += 1 if k3 else 0

    # K4: 4 SAAT DOLMADAN devir YOK + hicbir dosya DEGISMEDI
    kok2, s2 = senaryo(239, uygula=True, alt="k4")
    with open(posta_yolu(TAMIRCI, kok2), encoding="utf-8") as f:
        posta2 = f.read()
    k4 = (len(s2["devredilen"]) == 0 and "DEVREDILDI" not in posta2
          and _acik_mi(defter_yolu("MaCiT", kok2), "K777")
          and not _acik_mi(defter_yolu(TAMIRCI, kok2), "K777"))
    print("KONTROL K4 239 dk -> devir YOK, kutu temiz: %s (%s)"
          % ("GECTI" if k4 else "KUSUR", hukum_satiri(s2)))
    kontrol += 1 if k4 else 0

    print("")
    print("MUTANT=%d/5 HEDEF_KOL_ATFI=%d/5 KONTROL=%d/4"
          % (mutant_sayaci, atif_sayaci, kontrol))
    return 0 if (mutant_sayaci == 5 and atif_sayaci == 5 and kontrol == 4) else 1


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--simdi", help="ISO 8601 (enjekte edilebilir zaman)")
    ap.add_argument("--rapor", action="store_true", help="salt-okunur")
    ap.add_argument("--uygula", action="store_true", help="devri UYGULA (YAZAR)")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--koku-root", default=None, help="izole defter koku")
    args = ap.parse_args(argv)

    if args.kendini_test:
        gecici = tempfile.mkdtemp(prefix="n2c-kendinitest-")
        try:
            return kendini_test(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if T4 is None or T5 is None:
        print("HATA: %s T4/T5 yuklenemedi" % N2C_OLCULEMEDI_JETON)
        return RC_OLCULEMEDI

    simdi = _simdi_coz(args.simdi) if args.simdi else datetime.now(timezone.utc)
    if simdi is None:
        print("HATA: --simdi gecersiz ISO: %r" % args.simdi)
        return RC_OLCULEMEDI

    s = devret(simdi, koku_root=args.koku_root, uygula=args.uygula)
    print("N2C DEVIR KAPISI — %s" % ("UYGULA (YAZAR)" if args.uygula
                                     else "RAPOR (YAZMAZ)"))
    print("simdi: %s | esik: %s dk" % (_iso(simdi), ESIK_DAKIKA))
    for k in s["devredilen"]:
        print("  DEVIR %s/%s damga=%s fark=%.1f dk posta=%s iz=%s "
              "kaynak_kapandi=%s hedef_acildi=%s"
              % (k["ev"], k["kimlik"], k["damga"], k["fark_dk"] or 0.0,
                 k["posta"], k["iz"], k["kaynak_kapandi"], k["hedef_acildi"]))
    if s["hata"]:
        print("HATA: %s" % s["hata"])
    print(hukum_satiri(s))
    if s["hata"]:
        return RC_OLCULEMEDI
    return RC_TAMAM


if __name__ == "__main__":
    sys.exit(main())
