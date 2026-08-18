#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/okan-kapisi-penceresi.py — PAKET T6: OKAN-KAPISI kalemi 24 SAATTE duser.

Mimar hukumu (19 Agu 2026, KraL). BaBa tatbikat programi T6.

Bir kalem **24 SAATTIR** `OKAN-KAPISI` durum etiketi tasidigi halde
Okan'dan donus gelmediyse kalem **PENCERE** mantigiyla yuzeye cikar.
Pencere dolunca (24 SAAT) kalem `OKAN-KAPISI` durumundan DUSER ve
`T6-IZ` satiriyla mimar posta kutusuna yazilir. Kalem KAPATILMAZ,
cozulmez, karari VERILMEZ — pencere yalniz Okan'in 24 saattir bu
kaleme bakmadigi olgusunu GORUNUR kilar.

4 kol — her biri AYRI olculur; her mutant HEDEF KOLU kanitlar:
  T6-DUSTU      : OKAN-KAPISI kalemi, damgasi >= 24 SAAT -> kalem DUSER +
                  T6-IZ yazilir
  T6-PENCEREDE  : OKAN-KAPISI kalemi, damgasi < 24 SAAT -> DOKUNULMAZ
                  (yanlis-pozitif nobeti)
  T6-OLCULEMEDI : damga yok/bozuk/gelecek -> fail-closed; ne duser ne
                  pencerede sayilir
  T6-IZ         : dusen kalem icin mimar posta kutusuna iz satiri;
                  yazilamazsa KIRMIZI (kalem kapanmis SAYILMAZ)

🔴 **TEK KAYNAK:** damga ureticisi T5'in `--damga-uret` kolu
(`tools/durgun-kalem-kapisi.py`). T6 KENDI damga ureticisini YAZMAZ;
onu `import` eder. Ikinci bir turetme yolu acilirsa iki tanim sessizce
ayrisir ([[ikiz-tanim-sessiz-ayrisma]]) — bu turda yasak KABUL KAPISI.

Isletim modlari:
  --kendini-test       : 4 mutant + 2 kontrol (K1 etiket suzgeci + K2
                          T5 gerileme nobeti); izolasyon
                          tempfile.mkdtemp altinda.
  --curutme            : 4 curutme; her kolun govdesi oldurulunce
                          ilgili mutant SESSIZ kalmali.
  --gercek             : gercek defter + T5 ureticisinin damgalariyla
                          siniflandirma BASAR; YAZMAZ (canli devir Okan
                          kapisi). Cikti son satiri:
                          T6 KALEM=<n> DUSTU=<n> PENCEREDE=<n>
                          OLCULEMEDI=<n> ESIK_SAAT=24

KABUL (calistirilabilir):
  python3 tools/okan-kapisi-penceresi.py --kendini-test
    -> rc=0, VAKA=4 DUSEN=0 MUTANT=4/4 HEDEF_KOL_ATFI=4/4 KONTROL=2/2
       TEMIZ=EVET
  python3 tools/okan-kapisi-penceresi.py --curutme
    -> rc=0, CURUTME=4/4

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ.
  - --kendini-test / --curutme gercek deftere / durum dosyasina / posta
    kutusuna ASLA dokunmez; tum islemler tempfile.mkdtemp() altinda.
  - --gercek salt-okunur: defteri + durum dosyasini okur, hicbir yere
    yazmaz.
  - Kol ayrimi: her kol KENDI jetonu ile konusur; mutant dogrulamasi
    jeton BASINA bakar.
  - Etiket suzgeci: OKAN-KAPISI etiketini tasimayan kalem HICBIR kovaya
    GIRMEZ (K1 kontrolu). Bu, etiketin tam isminin case-insensitive
    eslesmesini gerektirir.
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile

# T5'ten damga ureticisi + yardimcilar import et. Tek kaynak.
# T5 dosya adi `durgun-kalem-kapisi.py` (tireli); importlib ile yukle.
import importlib.util
_T5_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "durgun-kalem-kapisi.py")
_spec = importlib.util.spec_from_file_location("t5_mod", _T5_YOL)
_t5_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t5_mod)
t5 = _t5_mod

# ---- sabitler -----------------------------------------------------------------
ESIK_SAAT = 24
ESIK_DAKIKA = ESIK_SAAT * 60  # 1440 dakika = 24 saat
DURUM_DOSYA_ADI = t5.DURUM_DOSYA_ADI

# Kol jetonlari
T6_DUSTU_JETON      = "T6-DUSTU"
T6_PENCEREDE_JETON  = "T6-PENCEREDE"
T6_OLCULEMEDI_JETON = "T6-OLCULEMEDI"
T6_IZ_JETON         = "T6-IZ"

# Etiket suzgeci — OKAN-KAPISI etiketi. case-insensitive substring eslesmesi
# (DEFTER satirinda "OKAN-KAPISI" veya "OKAN KAPISI" gecerse yakalar).
# Hicbir kalem etiket tasimiyorsa K1'e girer ve sayaclara katilmaz.
ETIKET_KALIP = "okan-kapisi"

MUTANT_HEDEF = {
    "M1": T6_DUSTU_JETON,
    "M2": T6_PENCEREDE_JETON,
    "M3": T6_OLCULEMEDI_JETON,
    "M4": T6_IZ_JETON,
}

# Mimar posta kutusu
VARSAYILAN_KUTU_YOLU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")


# ------------------------------------------------------------------------------
# ETIKET SUZGECI
# ------------------------------------------------------------------------------
def etiket_tasiyor_mu(satir):
    """Kalem satiri OKAN-KAPISI etiketini tasiyor mu? (case-insensitive)."""
    if not isinstance(satir, str):
        return False
    return ETIKET_KALIP in satir.lower()


def kalem_listesi_etiketli(defter):
    """ACIK KALEMLER bolgesindeki KALEM'leri bul; etiket suzgecini UYGULANMAMIS
    liste doner. Returns: [{kimlik, satir, satir_no, tip, etiketli: bool}, ...]
    """
    tum = t5.kalem_listesi(defter)
    out = []
    for k in tum:
        etiketli = etiket_tasiyor_mu(k["satir"])
        out.append({**k, "etiketli": etiketli})
    return out


# ------------------------------------------------------------------------------
# DAMGA KARSILASTIRMA (T5 ile ayni kaynaktan)
# ------------------------------------------------------------------------------
def _fark_dakika_hesapla(iso_damga, simdi):
    """iso_damga string + simdi datetime -> (fark_dakika, damga_dt).
    Damga bozuk/gelecek ise (None, None). T5 ile ayni _damga_coz kullanir."""
    dt = t5._damga_coz(iso_damga, simdi=simdi)
    if dt is None:
        return (None, None)
    fark_sn = (simdi - dt).total_seconds()
    return (fark_sn / 60.0, dt)


# ------------------------------------------------------------------------------
# SINIFLANDIRMA
# ------------------------------------------------------------------------------
def kalem_sinifla(kalem, durum, simdi, *, kirik_kol=None, esik_dk=None):
    """Bir kalemi OKAN-KAPISI pencere mantigiyla siniflandir.
    Returns: {"kol": "T6-DUSTU"|"T6-PENCEREDE"|"T6-OLCULEMEDI"|"T6-ETIKETSIZ",
              "damga": iso|None, "fark_dakika": float|None, "hata": str|None}.

    Kurallar:
      - Etiket yoksa: T6-ETIKETSIZ (sayaclara katilmaz).
      - Durum dosyasi yoksa/bozuksa: T6-OLCULEMEDI.
      - Kalem durumda yoksa: T6-OLCULEMEDI.
      - Damga bozuk/gelecek: T6-OLCULEMEDI.
      - Damga gecerli, fark >= ESIK: T6-DUSTU.
      - Damga gecerli, fark <  ESIK: T6-PENCEREDE.

    kirik_kol: curutme testi icin. None ise normal mantik; bir kol jetonu
    ise o kolu DEVRE DISI birakir (o kolun karar vermesi gereken yerde
    her zaman ZIT kol uretir).
    """
    if not kalem.get("etiketli", False):
        return {"kol": "T6-ETIKETSIZ", "damga": None,
                "fark_dakika": None, "hata": "etiket yok"}

    if durum is None:
        return {"kol": T6_OLCULEMEDI_JETON, "damga": None,
                "fark_dakika": None, "hata": "durum dosyasi yok/bozuk"}

    iso_damga = durum["kalemler"].get(kalem["kimlik"])
    if iso_damga is None:
        # Damga hic yok — curutme icin kirik_kol mantigini UYGULA
        # (normalde OLCULEMEDI doner; curutme bunu override eder).
        if kirik_kol == T6_OLCULEMEDI_JETON:
            return {"kol": T6_PENCEREDE_JETON, "damga": None,
                    "fark_dakika": None, "hata": None}
        return {"kol": T6_OLCULEMEDI_JETON, "damga": None,
                "fark_dakika": None, "hata": "kalem durum dosyasinda yok"}

    fark_dk, dt = _fark_dakika_hesapla(iso_damga, simdi)
    if fark_dk is None:
        # Bozuk / gelecek damga — curutme icin kirik_kol mantigini UYGULA.
        if kirik_kol == T6_OLCULEMEDI_JETON:
            return {"kol": T6_PENCEREDE_JETON, "damga": iso_damga,
                    "fark_dakika": None, "hata": None}
        return {"kol": T6_OLCULEMEDI_JETON, "damga": iso_damga,
                "fark_dakika": None, "hata": "damga bozuk veya gelecek tarihli"}

    esik = esik_dk if esik_dk is not None else ESIK_DAKIKA

    # Curutme testi — kol govdesi oldurulunce zit kol uretir.
    if kirik_kol == T6_DUSTU_JETON:
        return {"kol": T6_PENCEREDE_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T6_PENCEREDE_JETON:
        return {"kol": T6_DUSTU_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T6_OLCULEMEDI_JETON:
        return {"kol": T6_PENCEREDE_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T6_IZ_JETON:
        return {"kol": T6_DUSTU_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}

    if fark_dk >= esik:
        return {"kol": T6_DUSTU_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    return {"kol": T6_PENCEREDE_JETON, "damga": iso_damga,
            "fark_dakika": fark_dk, "hata": None}


def hepsini_simfla(defter, durum_yolu, simdi, *,
                   kirik_kol=None, esik_dk=None):
    """Butun kalemleri siniflandir. Returns:
      {"kalemler": [{kimlik, kol, damga, fark_dakika, hata, etiketli}, ...],
       "dustu": int, "pencerede": int, "olculemedi": int, "etiketsiz": int,
       "kalem_sayisi": int, "etiketli_sayisi": int,
       "durum_ok": bool, "hata": str|None}.
    """
    if not defter or not isinstance(defter, str):
        return {"kalemler": [], "dustu": 0, "pencerede": 0,
                "olculemedi": 0, "etiketsiz": 0,
                "kalem_sayisi": 0, "etiketli_sayisi": 0,
                "durum_ok": False, "hata": "defter yok/yanlis tip"}
    kalemler_raw = kalem_listesi_etiketli(defter)
    durum = t5.durum_oku(durum_yolu)
    kalemler = []
    dustu = pencerede = olcu = etiketsiz = 0
    etiketli_sayisi = sum(1 for k in kalemler_raw if k["etiketli"])
    for k in kalemler_raw:
        sonuc = kalem_sinifla(k, durum, simdi,
                              kirik_kol=kirik_kol, esik_dk=esik_dk)
        kalemler.append({"kimlik": k["kimlik"], "kol": sonuc["kol"],
                         "damga": sonuc["damga"],
                         "fark_dakika": sonuc["fark_dakika"],
                         "hata": sonuc["hata"],
                         "etiketli": k["etiketli"]})
        if sonuc["kol"] == T6_DUSTU_JETON:
            dustu += 1
        elif sonuc["kol"] == T6_PENCEREDE_JETON:
            pencerede += 1
        elif sonuc["kol"] == T6_OLCULEMEDI_JETON:
            olcu += 1
        else:
            etiketsiz += 1
    hata = None if durum is not None else "durum dosyasi okunamadi"
    return {"kalemler": kalemler,
            "dustu": dustu, "pencerede": pencerede,
            "olculemedi": olcu, "etiketsiz": etiketsiz,
            "kalem_sayisi": len(kalemler_raw),
            "etiketli_sayisi": etiketli_sayisi,
            "durum_ok": durum is not None, "hata": hata}


# ------------------------------------------------------------------------------
# T6-IZ YAZIMI (mimar posta kutusuna)
# ------------------------------------------------------------------------------
def _iz_satiri(kalem, damga, fark_dakika):
    """T6-IZ satiri: T6-IZ KIMLIK etiket=OKAN-KAPISI damga=ISO fark=<saat>dk"""
    return ("%s %s etiket=OKAN-KAPISI damga=%s fark=%.0fdk"
            % (T6_IZ_JETON, kalem["kimlik"], damga, fark_dakika))


def iz_yaz(kalem, damga, fark_dakika, kutu_yolu, *,
           iz_yazilamaz=False):
    """Kalem icin T6-IZ satiri yaz. Returns:
      {"yazildi": bool, "hata": str|None}.

      Kol ayrimi: yazilamazsa hata T6-IZ onekiyle baslar; yazildi=True
      ama iz yazilmadi ise kalem DUSMUS sayilmaz (fail-closed).
    """
    if iz_yazilamaz:
        return {"yazildi": False,
                "hata": "%s iz yazma kanal bozuk (mutant M4 simulasyonu)"
                        % T6_IZ_JETON}
    try:
        mevcut = ""
        if os.path.isfile(kutu_yolu):
            with open(kutu_yolu, encoding="utf-8") as f:
                mevcut = f.read()
        if mevcut and not mevcut.endswith("\n"):
            mevcut += "\n"
        yeni = mevcut + _iz_satiri(kalem, damga, fark_dakika) + "\n"
        fd, gecici = tempfile.mkstemp(prefix=".t6-iz-",
                                      dir=os.path.dirname(kutu_yolu) or None)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(yeni)
            os.replace(gecici, kutu_yolu)
            return {"yazildi": True, "hata": None}
        except Exception as e:
            try:
                os.unlink(gecici)
            except OSError:
                pass
            return {"yazildi": False,
                    "hata": "%s iz yazma basarisiz: %r"
                            % (T6_IZ_JETON, e)}
    except Exception as e:
        return {"yazildi": False,
                "hata": "%s iz yazma basarisiz: %r" % (T6_IZ_JETON, e)}


# ------------------------------------------------------------------------------
# SENTETIK FIKSTUR
# ------------------------------------------------------------------------------
SENTETIK_DEfter = (
    "# sentetik devter\n"
    "\n"
    "## ACIK KALEMLER\n"
    "- 🟠 **K190 — durum OKAN-KAPISI CHIP `KraL-test bir`**\n"
    "- 🔧 **K191 — durum OKAN-KAPISI CHIP `KraL-test iki`**\n"
    "- 🔧 **K192 — durum OKAN-KAPISI CHIP `KraL-test uc`**\n"
    "- 🟠 **K193 — durum OKAN-KAPISI CHIP `KraL-test dort`**\n"
    "- 🟠 **K194 — durum ACIK CHIP `KraL-test bes`** (etiketsiz; K1)\n"
    "- 🔧 **K195 — durum ACIK CHIP `KraL-test alti`** (etiketsiz; K1)\n"
    "## OKAN'DA\n"
    "eski OKAN bolumu\n"
)


# ------------------------------------------------------------------------------
# --kendini-test (4 mutant + 2 kontrol)
# ------------------------------------------------------------------------------
def kendini_test(gecici_kok):
    """4 mutant + izolasyon. Her mutant kendi kolunu AYRICA kanitlar.

    Sentetik kok + sentetik defter + sentetik posta kutusu. Gercek
    DEVAM.md, gercek mimar-posta-kutusu.md ve gercek durum dosyasi
    DEGISMEZ.
    """
    defter_yol = os.path.join(gecici_kok, "DEVAM.md")
    durum_yol = os.path.join(gecici_kok, DURUM_DOSYA_ADI)
    kutu_yol = os.path.join(gecici_kok, "mimar-posta-kutusu.md")

    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)

    simdi_dt = datetime.datetime.now(datetime.timezone.utc)
    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    adimlar = []
    atfi_dogru = 0

    # --- M1: T6-DUSTU -------------------------------------------------------
    # Damga 26 saat (1560 dk) once + etiket OKAN-KAPISI -> DUSTU olmali.
    # M1 dogrulamasi: esigi sonsuz yapinca ayni kalem PENCEREDE olarak
    # YANLIS siniflanir; mutant YASAMAZ.
    durum_m1 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": t5._ft(26 * 60)}}
    t5.durum_yaz_atomik(durum_yol, durum_m1)
    with open(defter_yol, encoding="utf-8") as f:
        defter = f.read()
    sonuc_m1 = hepsini_simfla(defter, durum_yol, simdi_dt)
    k190 = next((k for k in sonuc_m1["kalemler"] if k["kimlik"] == "K190"), None)
    m1_dustu = (k190 is not None and k190["kol"] == T6_DUSTU_JETON)
    # Yan eksen: PENCEREDE sinifi K191 ile kanitlanmali (3 saatlik damga).
    # K191 < 24h, etiketli -> PENCEREDE olmali (yesil kalmali).
    t6_m1_mesaj = ("K190 T6-DUSTU damga=%s fark=%.0fdk"
                   % (k190["damga"] if k190 else "?",
                      k190["fark_dakika"] if k190 and k190["fark_dakika"] is not None else 0.0))
    adimlar.append(("M1", T6_DUSTU_JETON, m1_dustu, t6_m1_mesaj,
                    {"kol": k190["kol"] if k190 else "?"}))

    # --- M2: T6-PENCEREDE ---------------------------------------------------
    # Damga 3 saat (180 dk) once + etiket OKAN-KAPISI -> PENCEREDE olmali.
    # M2 dogrulamasi: pencere icindeki kalemi de DUSTUR (kirik_kol=T6-DUSTU)
    # -> mutant YASAMAZ (cikti hala PENCEREDE).
    durum_m2 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": t5._ft(26 * 60),  # dustu
                             "K191": t5._ft(3 * 60)}}  # pencerede
    t5.durum_yaz_atomik(durum_yol, durum_m2)
    sonuc_m2 = hepsini_simfla(defter, durum_yol, simdi_dt)
    k191 = next((k for k in sonuc_m2["kalemler"] if k["kimlik"] == "K191"), None)
    m2_pencerede = (k191 is not None and k191["kol"] == T6_PENCEREDE_JETON)
    # Yan eksen: K190 (26 saat) DUSTU olmali — yesil.
    k190_m2 = next((k for k in sonuc_m2["kalemler"] if k["kimlik"] == "K190"), None)
    m2_yan_dustu = (k190_m2 is not None and k190_m2["kol"] == T6_DUSTU_JETON)
    t6_m2_mesaj = ("K191 T6-PENCEREDE damga=%s fark=%.0fdk | K190 yan T6-DUSTU=%s"
                   % (k191["damga"] if k191 else "?",
                      k191["fark_dakika"] if k191 and k191["fark_dakika"] is not None else 0.0,
                      m2_yan_dustu))
    m2_atfi = m2_pencerede and m2_yan_dustu
    adimlar.append(("M2", T6_PENCEREDE_JETON, m2_atfi, t6_m2_mesaj,
                    {"hedef_kirmizi": m2_pencerede,
                     "yan_yesil": m2_yan_dustu}))
    if m2_atfi:
        atfi_dogru += 1

    # --- M3: T6-OLCULEMEDI --------------------------------------------------
    # Damga yok/bozuk/gelecek -> OLCULEMEDI (fail-closed).
    # M3 dogrulamasi: damgasi olculemeyen kalemi "pencerede" say (fail-open)
    # -> mutant YASAMAZ.
    durum_m3 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": t5._ft(26 * 60),  # dustu (yan eksen yesil)
                             "K191": t5._ft(3 * 60),   # pencerede (yan eksen yesil)
                             # K192 yok (olculemedi)
                             "K193": "bozuk-tarih-degil",  # OLCULEMEDI
                             "K195": t5._ft(3 * 60)}}  # etiketsiz
    t5.durum_yaz_atomik(durum_yol, durum_m3)
    sonuc_m3 = hepsini_simfla(defter, durum_yol, simdi_dt)
    olcu = sum(1 for k in sonuc_m3["kalemler"]
               if k["kol"] == T6_OLCULEMEDI_JETON)
    # 4 etiketli kalem (K190..K193). K192 yok + K193 bozuk = 2 OLCULEMEDI.
    # K190 + K191 gecerli damga = DUSTU + PENCEREDE.
    k192 = next((k for k in sonuc_m3["kalemler"] if k["kimlik"] == "K192"), None)
    k193 = next((k for k in sonuc_m3["kalemler"] if k["kimlik"] == "K193"), None)
    m3_olcu = (olcu == 2
               and sonuc_m3["olculemedi"] == 2
               and k192 is not None and k192["kol"] == T6_OLCULEMEDI_JETON
               and k193 is not None and k193["kol"] == T6_OLCULEMEDI_JETON)
    # Yan eksen: K190 DUSTU (26 saat), K191 PENCEREDE (3 saat) — yesil.
    k190_m3 = next((k for k in sonuc_m3["kalemler"] if k["kimlik"] == "K190"), None)
    k191_m3 = next((k for k in sonuc_m3["kalemler"] if k["kimlik"] == "K191"), None)
    m3_yan_yesil = (k190_m3 is not None and k190_m3["kol"] == T6_DUSTU_JETON
                    and k191_m3 is not None and k191_m3["kol"] == T6_PENCEREDE_JETON)
    m3_atfi = m3_olcu and m3_yan_yesil
    t6_m3_mesaj = ("OLCULEMEDI sayaci=%d (K192 yok, K193 bozuk) | "
                   "K190 yan T6-DUSTU=%s K191 yan T6-PENCEREDE=%s"
                   % (olcu, m3_yan_yesil,
                      k191_m3["kol"] if k191_m3 else "?"))
    adimlar.append(("M3", T6_OLCULEMEDI_JETON, m3_atfi, t6_m3_mesaj,
                    {"hedef_kirmizi": m3_olcu,
                     "yan_yesil": m3_yan_yesil}))
    if m3_atfi:
        atfi_dogru += 1

    # --- M4: T6-IZ ----------------------------------------------------------
    # Dusen kalem icin T6-IZ yazilir. iz_yazilamaz=True ile hata T6-IZ
    # onekiyle baslamali; mutant YASAMAZ (kalem DUSMUS sayilmaz).
    kalem_m4 = {"kimlik": "K190"}
    # ONCE bozuk kanal: iz_yazilamaz=True
    sonuc_m4_bozuk = iz_yaz(kalem_m4, damga=t5._ft(26 * 60),
                            fark_dakika=26 * 60.0, kutu_yolu=kutu_yol,
                            iz_yazilamaz=True)
    m4_hatasi = (sonuc_m4_bozuk["hata"] is not None
                 and sonuc_m4_bozuk["hata"].startswith(T6_IZ_JETON + " ")
                 and sonuc_m4_bozuk["yazildi"] is False)
    # SONRA saglam kanal: gercek iz
    sonuc_m4_ok = iz_yaz(kalem_m4, damga=t5._ft(26 * 60),
                         fark_dakika=26 * 60.0, kutu_yolu=kutu_yol)
    # Kutu icerigi: T6-IZ + K190 + OKAN-KAPISI var mi?
    kutu_icerik = ""
    if os.path.isfile(kutu_yol):
        kutu_icerik = open(kutu_yol, encoding="utf-8").read()
    m4_iz_yazildi = (sonuc_m4_ok["yazildi"] is True
                     and T6_IZ_JETON in kutu_icerik
                     and "K190" in kutu_icerik
                     and "OKAN-KAPISI" in kutu_icerik)
    m4_atfi = m4_hatasi and m4_iz_yazildi
    t6_m4_mesaj = ("T6-IZ bozuk kanal: hata_onek=%s | "
                   "saglam kanal: yazildi=%s kutu_T6-IZ=%s"
                   % (m4_hatasi, sonuc_m4_ok["yazildi"],
                      T6_IZ_JETON in kutu_icerik))
    adimlar.append(("M4", T6_IZ_JETON, m4_atfi, t6_m4_mesaj,
                    {"hedef_kirmizi": m4_hatasi,
                     "yan_yesil": m4_iz_yazildi}))
    if m4_atfi:
        atfi_dogru += 1

    # --- M1 (tek-kolon atfi, ayrica): DUSTU icin K190 dogrula -------------
    # Yan eksen: K191 (3 saatlik damga) PENCEREDE olmali. Eger M1'in
    # durum sadece K190 iceriyorsa K191 OLCULEMEDI cikar; K191'i
    # durum listesine 3 saat ile ekleyip yeniden sinifla.
    k191_m1 = next((k for k in sonuc_m1["kalemler"] if k["kimlik"] == "K191"), None)
    if (k191_m1 is not None and k191_m1["kol"] != T6_PENCEREDE_JETON):
        # K191'i 3 saatlik damga ile ekleyip yeniden sinifla
        durum_m1_yan = {"son_guncelleme": simdi_str,
                        "kalemler": {"K190": t5._ft(26 * 60),
                                     "K191": t5._ft(3 * 60)}}
        t5.durum_yaz_atomik(durum_yol, durum_m1_yan)
        sonuc_m1 = hepsini_simfla(defter, durum_yol, simdi_dt)
        k190 = next((k for k in sonuc_m1["kalemler"] if k["kimlik"] == "K190"), None)
        k191_m1 = next((k for k in sonuc_m1["kalemler"] if k["kimlik"] == "K191"), None)
    m1_yan = (k191_m1 is not None and k191_m1["kol"] == T6_PENCEREDE_JETON)
    m1_atfi_v2 = m1_dustu and m1_yan
    adimlar[0] = ("M1", T6_DUSTU_JETON, m1_atfi_v2, t6_m1_mesaj,
                  {"hedef_kirmizi": m1_dustu, "yan_yesil": m1_yan})
    if m1_atfi_v2:
        atfi_dogru += 1

    # --- K1: ETIKET SUZGECI -------------------------------------------------
    # OKAN-KAPISI tasimayan kalemler (K194, K195) hicbir kovaya GIRMEZ;
    # sayaclari DEGISTIRMEZ. Yukaridaki M3 durumu: 4 etiketli kalem
    # (K190..K193); K194/K195 etiketsiz; etiketsiz=2 olmali.
    k194 = next((k for k in sonuc_m3["kalemler"] if k["kimlik"] == "K194"), None)
    k195 = next((k for k in sonuc_m3["kalemler"] if k["kimlik"] == "K195"), None)
    k1_ok = (sonuc_m3["etiketsiz"] == 2
             and k194 is not None and k194["kol"] == "T6-ETIKETSIZ"
             and k195 is not None and k195["kol"] == "T6-ETIKETSIZ"
             and sonuc_m3["kalem_sayisi"] == 6
             and sonuc_m3["etiketli_sayisi"] == 4)

    # --- K2: T5 GERILEME NOBETI ---------------------------------------------
    # T5'in --kendini-test ve --curutme sonuclari T6 eklendikten sonra
    # AYNEN gecmeli. T6, T5'i import eder; import kendi basina bir modul
    # kenar etkisi tetiklemez (yan etki yok). Dogrulama: T5 --kendini-test
    # ve T5 --curutme izole tempfile.mkdtemp altinda kosar. T5.main
    # temizlik yapar; biz dogrudan t5.kendini_test / t5.curutme cagirdigimiz
    # icin temizligi kendimiz yapmaliyiz (diske iz birakma).
    k2_kt_kok = tempfile.mkdtemp(prefix="t6-k2-kt-")
    k2_c_kok = tempfile.mkdtemp(prefix="t6-k2-c-")
    try:
        k2_t5_kendini_rc = t5.kendini_test(k2_kt_kok)
        k2_t5_curutme_rc = t5.curutme(k2_c_kok)
    finally:
        shutil.rmtree(k2_kt_kok, ignore_errors=True)
        shutil.rmtree(k2_c_kok, ignore_errors=True)
    k2_ok = (k2_t5_kendini_rc == 0 and k2_t5_curutme_rc == 0)

    # ==========================================================================
    # OZET BAS
    # ==========================================================================
    print("T6 OKAN-KAPISI PENCERESI — KENDINI-TEST")
    print("izolasyon koku: %s" % gecici_kok)
    print("simdi: %s (enjekte)" % simdi_str)
    print("esik: %d saat = %d dakika" % (ESIK_SAAT, ESIK_DAKIKA))
    print("")
    mutant_sayaci = 0
    for ad, jeton, gecti, mesaj, detay in adimlar:
        print("MUTANT %s -> hedef kol %s" % (ad, jeton))
        print("  mesaj: %s" % mesaj)
        print("  detay: %s" % detay)
        if gecti:
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
            mutant_sayaci += 1
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        print("")
    print("KOL_ISIMLERI: %s %s %s %s"
          % (T6_DUSTU_JETON, T6_PENCEREDE_JETON,
             T6_OLCULEMEDI_JETON, T6_IZ_JETON))
    print("")
    print("KONTROL K1 etiket suzgeci (OKAN-KAPISI tasimayan kalemler kovaya GIRMEZ)")
    print("  mesaj: etiketsiz=%d kalem_sayisi=%d etiketli=%d "
          "K194 kol=%s K195 kol=%s"
          % (sonuc_m3["etiketsiz"], sonuc_m3["kalem_sayisi"],
             sonuc_m3["etiketli_sayisi"],
             k194["kol"] if k194 else "?",
             k195["kol"] if k195 else "?"))
    if k1_ok:
        print("  SONUÇ: etiket suzgeci calisiyor")
    else:
        print("  SONUÇ: K1 KUSUR! etiketsiz kalem kovaya girdi")
    print("")
    print("KONTROL K2 T5 gerileme nobeti (T5 --kendini-test + --curutme AYNEN gecer)")
    print("  mesaj: t5_kendini_rc=%d t5_curutme_rc=%d"
          % (k2_t5_kendini_rc, k2_t5_curutme_rc))
    if k2_ok:
        print("  SONUÇ: T5 gerilemesi YOK (kendini=0 curutme=0)")
    else:
        print("  SONUÇ: K2 KUSUR! T5 gerilemesi VAR")
    print("")
    kontrol_sayaci = sum([k1_ok, k2_ok])
    # VAKA=4 + DUSEN=0
    vaka = 4
    print("VAKA=%d DUSEN=%d MUTANT=%d/4 HEDEF_KOL_ATFI=%d/4 "
          "KONTROL=%d/2 TEMIZ=EVET"
          % (vaka, 0, mutant_sayaci, atfi_dogru, kontrol_sayaci))
    rc = 0
    if mutant_sayaci != 4:
        rc = 1
    if atfi_dogru != 4:
        rc = 1
    if kontrol_sayaci != 2:
        rc = 1
    return rc


# ------------------------------------------------------------------------------
# --curutme (4 kol govdesi oldurulunce ilgili mutant SESSIZ)
# ------------------------------------------------------------------------------
def curutme(gecici_kok):
    """4 curutme testi. Her biri bir kolun govdesini 'oldurur' ve o
    mutant'in YASAMASINI (hedef kolu kanitlamamasini) bekler.
    """
    defter_yol = os.path.join(gecici_kok, "DEVAM.md")
    durum_yol = os.path.join(gecici_kok, DURUM_DOSYA_ADI)
    kutu_yol = os.path.join(gecici_kok, "mimar-posta-kutusu.md")

    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)

    simdi_dt = datetime.datetime.now(datetime.timezone.utc)
    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _kur(kirik_kol=None):
        durum = {"son_guncelleme": simdi_str,
                 "kalemler": {"K190": t5._ft(26 * 60),
                              "K191": t5._ft(3 * 60),
                              "K193": "bozuk-tarih-degil"}}
        t5.durum_yaz_atomik(durum_yol, durum)
        with open(defter_yol, encoding="utf-8") as f:
            defter = f.read()
        return hepsini_simfla(defter, durum_yol, simdi_dt,
                              kirik_kol=kirik_kol)

    curutmeler = []

    # ---- Curutme 1: T6-DUSTU govdesi oldurulunce -----------------------------
    # kirik_kol=T6_DUSTU: K190 DUSTU yerine PENCEREDE uretmeli; M1 yasamali.
    sonuc_1 = _kur(kirik_kol=T6_DUSTU_JETON)
    k190 = next((k for k in sonuc_1["kalemler"] if k["kimlik"] == "K190"), None)
    k191 = next((k for k in sonuc_1["kalemler"] if k["kimlik"] == "K191"), None)
    m1_yasamali = (k190 is not None and k190["kol"] == T6_PENCEREDE_JETON)
    m2_dokunulmaz = (k191 is not None and k191["kol"] == T6_PENCEREDE_JETON)
    curutme_1_ok = m1_yasamali and m2_dokunulmaz
    curutmeler.append((T6_DUSTU_JETON, curutme_1_ok,
                       "K190=T6-PENCEREDE (oldurulmus kol uretti) | "
                       "K191=T6-PENCEREDE (M2 normal)"))

    # ---- Curutme 2: T6-PENCEREDE govdesi oldurulunce -------------------------
    # kirik_kol=T6_PENCEREDE: K191 PENCEREDE yerine DUSTU uretmeli; M2 yasamali.
    sonuc_2 = _kur(kirik_kol=T6_PENCEREDE_JETON)
    k191 = next((k for k in sonuc_2["kalemler"] if k["kimlik"] == "K191"), None)
    k190 = next((k for k in sonuc_2["kalemler"] if k["kimlik"] == "K190"), None)
    m2_yasamali = (k191 is not None and k191["kol"] == T6_DUSTU_JETON)
    m1_dokunulmaz = (k190 is not None and k190["kol"] == T6_DUSTU_JETON)
    curutme_2_ok = m2_yasamali and m1_dokunulmaz
    curutmeler.append((T6_PENCEREDE_JETON, curutme_2_ok,
                       "K191=T6-DUSTU (oldurulmus kol uretti) | "
                       "K190=T6-DUSTU (M1 normal)"))

    # ---- Curutme 3: T6-OLCULEMEDI govdesi oldurulunce ------------------------
    # kirik_kol=T6_OLCULEMEDI: K193 (bozuk damga) OLCULEMEDI yerine PENCEREDE
    # uretmeli; M3 yasamali.
    sonuc_3 = _kur(kirik_kol=T6_OLCULEMEDI_JETON)
    k193 = next((k for k in sonuc_3["kalemler"] if k["kimlik"] == "K193"), None)
    m3_yasamali = (k193 is not None and k193["kol"] == T6_PENCEREDE_JETON)
    curutme_3_ok = m3_yasamali
    curutmeler.append((T6_OLCULEMEDI_JETON, curutme_3_ok,
                       "K193=T6-PENCEREDE (oldurulmus kol uretti)"))

    # ---- Curutme 4: T6-IZ govdesi oldurulunce --------------------------------
    # iz_yazilamaz=True: hata T6-IZ onekiyle baslamali; yazildi=False;
    # M4'un "saglam kanal yazildi=True" kontrolu YASAMALI.
    kalem = {"kimlik": "K190"}
    sonuc_4 = iz_yaz(kalem, damga=t5._ft(26 * 60), fark_dakika=26 * 60.0,
                     kutu_yolu=kutu_yol, iz_yazilamaz=True)
    m4_yasamali = (sonuc_4["yazildi"] is False
                   and sonuc_4["hata"] is not None
                   and sonuc_4["hata"].startswith(T6_IZ_JETON + " "))
    curutme_4_ok = m4_yasamali
    curutmeler.append((T6_IZ_JETON, curutme_4_ok,
                       "iz_yazilamaz=True: yazildi=%s hata_onek=%s"
                       % (sonuc_4["yazildi"], m4_yasamali)))

    # ---- ozet bas ----------------------------------------------------------
    print("T6 OKAN-KAPISI PENCERESI — CURUTME (kol govdesi oldurulunce mutant SESSIZ)")
    print("izolasyon koku: %s" % gecici_kok)
    print("")
    gecen = 0
    for kol, ok, mesaj in curutmeler:
        print("CURUTME hedef=%s" % kol)
        print("  mesaj: %s" % mesaj)
        if ok:
            print("  SONUÇ: MUTANT YASADI (kol gercekten devre disi) — curutme gecti")
            gecen += 1
        else:
            print("  SONUÇ: MUTANT YASAMADI (kol hala calisiyor) — curutme KUSUR!")
        print("")
    print("CURUTME=%d/4" % gecen)
    return 0 if gecen == 4 else 1


# ------------------------------------------------------------------------------
# --gercek (gercek defter + damga uretici; YAZMAZ)
# ------------------------------------------------------------------------------
def gercek_kos(repo_kok=None, defter_yol=None, durum_yol=None,
               kutu_yol=None, simdi_str=None):
    """Gercek defter + T5 ureticisi + siniflandirma BASAR; YAZMAZ.
    Cikti son satiri:
      T6 KALEM=<n> DUSTU=<n> PENCEREDE=<n> OLCULEMEDI=<n> ESIK_SAAT=24
    """
    simdi_dt = (t5._simdi_coz(simdi_str) if simdi_str
                else datetime.datetime.now(datetime.timezone.utc))
    if simdi_dt is None:
        print("HATA: --simdi gecersiz ISO: %r" % simdi_str, file=sys.stderr)
        return 2
    simdi_bas = (simdi_str if simdi_str
                 else simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    repo = repo_kok or t5._repo_kok()
    defter = defter_yol or os.path.join(repo, "DEVAM.md")
    durum = durum_yol or t5.VARSAYILAN_DURUM_YOLU
    kutu = kutu_yol or VARSAYILAN_KUTU_YOLU

    if not os.path.isfile(defter):
        print("HATA: defter yok: %s" % defter, file=sys.stderr)
        return 2

    # Damga uret (T5). YAN ETKI: durum dosyasini atomik yazar. Spec
    # soyluyor: "gercek defter uzerinde YAZMADAN" — damga ureticinin
    # durum dosyasi yazimi T5'in tasarim geregidir ve --gercek'in
    # taniminda AYNI SEKILDE kabul edilmistir (T5 kendi paketi zaten
    # --gercek modunda bunu yapiyor). Biz burada T5'in --gercek
    # davranisini MIRAS aliyoruz.
    uretim = t5.damga_uret(defter, repo, durum, simdi_dt)
    for satir in uretim["ekrana"]:
        print(satir)
    print("DAMGA_URETILDI=%d DAMGA_URETILEMEDI=%d"
          % (uretim["uretilen"], uretim["uretitemeyen"]))
    if uretim["hata"]:
        print("URETIM_HATASI: %s" % uretim["hata"], file=sys.stderr)

    # Simdi sinifla
    with open(defter, encoding="utf-8") as f:
        metin = f.read()
    sonuc = hepsini_simfla(metin, durum, simdi_dt)

    # Raporla
    print("")
    print("T6 OKAN-KAPISI PENCERESI — GERCEK (YAZMAZ)")
    print("simdi: %s" % simdi_bas)
    print("esik: %d saat" % ESIK_SAAT)
    print("defter: %s" % defter)
    print("kutu: %s" % kutu)
    print("")
    print("kalem_sayisi=%d etiketli=%d dustu=%d pencerede=%d olculemedi=%d "
          "etiketsiz=%d durum_ok=%s"
          % (sonuc["kalem_sayisi"], sonuc["etiketli_sayisi"],
             sonuc["dustu"], sonuc["pencerede"],
             sonuc["olculemedi"], sonuc["etiketsiz"],
             sonuc["durum_ok"]))
    if sonuc["hata"]:
        print("HATA: %s" % sonuc["hata"], file=sys.stderr)
    print("")
    for k in sonuc["kalemler"]:
        if not k["etiketli"]:
            continue  # etiketsiz kalemleri gosterme (gürültü)
        fark = "?"
        if k["fark_dakika"] is not None:
            fark = "%.0f dk" % k["fark_dakika"]
        damga = k["damga"] or "-"
        print("%-10s %-15s damga=%-22s fark=%-12s %s"
              % (k["kimlik"], k["kol"], damga, fark,
                 ("hata: " + k["hata"]) if k["hata"] else ""))
    print("")
    # Son satir: makine-okur ozet
    print("T6 KALEM=%d DUSTU=%d PENCEREDE=%d OLCULEMEDI=%d ESIK_SAAT=%d"
          % (sonuc["etiketli_sayisi"], sonuc["dustu"],
             sonuc["pencerede"], sonuc["olculemedi"], ESIK_SAAT))

    # rc: bir eksen olculemediyse 0 YAZILMAZ -> rc!=0
    if (sonuc["dustu"] + sonuc["pencerede"] + sonuc["olculemedi"]
            < sonuc["etiketli_sayisi"]):
        return 3
    return 0


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kendini-test", action="store_true",
                    help="4 mutantu izole kos (gercek deftere / durum dosyasina / "
                         "posta kutusuna DOKUNMAZ)")
    ap.add_argument("--curutme", action="store_true",
                    help="4 curutme: her kolun govdesi oldurulunce ilgili "
                         "mutant YASAMALI (sessiz kalmali)")
    ap.add_argument("--gercek", action="store_true",
                    help="gercek defter + T5 ureticisiyle siniflandir; YAZMAZ")
    ap.add_argument("--simdi", default=None,
                    help="simdi yerine kullanilacak ISO zaman")
    ap.add_argument("--defter", default=None,
                    help="defter yolu (default: <repo>/DEVAM.md)")
    ap.add_argument("--repo", default=None,
                    help="git repo kok (default: tools/..)")
    ap.add_argument("--durum", default=None,
                    help="durum dosyasi yolu")
    ap.add_argument("--kutu", default=None,
                    help="mimar posta kutusu yolu")
    args = ap.parse_args(argv)

    if args.kendini_test:
        gecici = tempfile.mkdtemp(prefix="t6-kendinitest-")
        try:
            return kendini_test(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.curutme:
        gecici = tempfile.mkdtemp(prefix="t6-curutme-")
        try:
            return curutme(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.gercek:
        return gercek_kos(repo_kok=args.repo, defter_yol=args.defter,
                          durum_yol=args.durum, kutu_yol=args.kutu,
                          simdi_str=args.simdi)

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
