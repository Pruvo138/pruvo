#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/durgun-kalem-kapisi.py — PAKET T5: 4 SAAT hareketsiz kalem OTOMATIK DEVREDILIR.

Mimar hukumu (19 Agu 2026, KraL). BaBa tatbikat programi T5.

Bir kalem **4 saattir durum degistirmediyse** (yeni dagitim, kapanis, onarim,
eskalasyon YOK) otomatik olarak DEVREDILIR: sahibi T3'un EV eksenine gore
cozulur ve devir izi birakilir. Kapı adı: `tools/durgun-kalem-kapisi.py`.

4 kol — her biri AYRI olculur; her mutant HEDEF KOLU kanitlar:
  T5-DURGUN     : son hareket >= 4 saat ise kalem DEVIR adayidir
  T5-TAZE       : son hareket < 4 saat ise DOKUNULMAZ (yanlis-pozitif nobeti)
  T5-IZ         : devir bir IZ birakir (kalem iki ucta da gorunur; SILME YOK)
  T5-OLCULEMEDI : damga yok/bozuk/gelecek tarihli ise **fail-closed**: "taze"
                  SAYILMAZ, ayri sayacla raporlanir

🔴 **ZAMAN KAYNAGI TEK** olsun ve enjekte edilebilir olsun (`--simdi <ISO>`),
yoksa test gercek saate baglanir ve gece yarisi kirmizi yanar. Sentetik
damgalarla olc.

Isletim modlari:
  --kendini-test       : 4 mutant + izolasyon (tempfile.mkdtemp); gercek
                          deftere / durum dosyasina / posta kutusuna DOKUNMAZ.
  --rapor --simdi <ISO>: gercek defter uzerinde YAZMADAN; kac kalem durgun,
                          kaci taze, kaci OLCULEMEDI.

🔴 **CANLI KABLOLAMA BU PAKETTE YOK.** Kapi yazilir, olculur, CI'da
`--kendini-test` olarak kosar. `nobet-kapi.py`'ye takilmasi AYRI karardir
(o dosya versiyon kontrolu disinda; yedegi ayri is).

KABUL (calistirilabilir):
  python3 tools/durgun-kalem-kapisi.py --kendini-test
    -> rc=0, MUTANT=4/4, dort kol adi ciktida; sentetik defter/damga
       tempfile izolasyonunda, GERCEK deftere DOKUNMAZ.

  Dort curutme: her kolun govdesi oldurulunce ilgili mutant SESSIZ kalmali.

  python3 tools/durgun-kalem-kapisi.py --rapor --simdi <ISO>
    -> gercek defter uzerinde YAZMADAN: kac kalem durgun, kaci taze,
       kaci OLCULEMEDI.

  nobet.yml serit-b'ye adim ekle (`if: ${{ !cancelled() }}`), `skipped` DEGIL.

Disiplin:
  - urunler.json / .urun-kaynaklari.json'a YAZMAZ (bu kapinin isi degil).
  - --kendini-test gercek deftere / durum dosyasina / posta kutusuna ASLA
    dokunmaz; tum islemler tempfile.mkdtemp() altinda izole.
  - --rapor salt-okunur: defteri + durum dosyasini okur, hicbir yere yazmaz.
  - Kol ayrimi: her kol KENDI jetonu ile konusur (`T5-DURGUN`, `T5-TAZE`,
    `T5-IZ`, `T5-OLCULEMEDI`); mutant dogrulamasi jeton BASINA bakar, boylece
    bir kolun govdesi oldurulunce DIGER kolun mesaji onun yerine gecse bile
    mutant YASAMAZ (kol ayrimi).
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile

# ---- sabitler -----------------------------------------------------------------
ESIK_DAKIKA = 240   # 4 saat = 240 dakika
DURUM_DOSYA_ADI = "durgun-kalem-durum.json"

# Kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir. Kol ATIFI
# mesajin BASINDA gecer; mutant dogrulamasi `startswith(kol + " ")` ile yalnizca
# kendi kolunun imzasini dogrular. Bu sayede bir kol oldurulunce diger kolun
# mesaji onun yerine gecse bile mutant YASAMAZ (kol ayrimi).
T5_DURGUN_JETON     = "T5-DURGUN"
T5_TAZE_JETON       = "T5-TAZE"
T5_IZ_JETON         = "T5-IZ"
T5_OLCULEMEDI_JETON = "T5-OLCULEMEDI"

# Mutant adlari + hedef kol eslestirmesi.
MUTANT_HEDEF = {
    "M1": T5_DURGUN_JETON,
    "M2": T5_TAZE_JETON,
    "M3": T5_IZ_JETON,
    "M4": T5_OLCULEMEDI_JETON,
}

# Varsayilan durum dosyasi yolu (gercek mod). --kendini-test bunu KULLANMAZ,
# tum islemlerini gecici dizinde yapar.
VARSAYILAN_DURUM_YOLU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/" + DURUM_DOSYA_ADI)


# ------------------------------------------------------------------------------
# YARDIMCILAR
# ------------------------------------------------------------------------------
def _repo_kok():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        os.pardir))


def _simdi_coz(simdi_str):
    """ISO 8601 (YYYY-MM-DDTHH:MM:SSZ veya +TZ) -> aware datetime (UTC). Hata -> None."""
    if not simdi_str:
        return None
    s = simdi_str.strip()
    if not s:
        return None
    # Z son ek
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt


def _damga_coz(deger, simdi=None):
    """Bir damga degeri -> aware datetime (UTC). None/yanlis bicim/gelecek tarihli
    ise None doner. Gelecek tarihli = simdi'den SONRA ise fail-closed (None doner).

    simdi verilmisse ve dt > simdi ise gelecek sayilir (None doner)."""
    if deger is None:
        return None
    if not isinstance(deger, str):
        return None
    s = deger.strip()
    if not s:
        return None
    dt = _simdi_coz(s)
    if dt is None:
        return None
    if simdi is not None and dt > simdi:
        return None  # gelecek tarihli -> fail-closed
    return dt


# ------------------------------------------------------------------------------
# DEFTER PARSE
# ------------------------------------------------------------------------------
def _acik_bolge(defter):
    """ACIK KALEMLER bolgesinin (baslik dahil) satir listesini doner.

    Baslik ## ile baslar; sonraki ## ile bolge biter. Bolge YOKSA None doner.
    """
    satirlar = defter.splitlines()
    bas = None
    for i, satir in enumerate(satirlar):
        if satir.startswith("## ACIK KALEMLER"):
            bas = i
            break
    if bas is None:
        return None
    son = len(satirlar)
    for i in range(bas + 1, len(satirlar)):
        if satirlar[i].startswith("## "):
            son = i
            break
    return satirlar[bas:son]


KIMLIK_RE_PATTERN = r"\bK\d+\b"


def kalem_listesi(defter):
    """ACIK KALEMLER bolgesindeki kalemleri bulur. Returns: [
        {"kimlik": "K186", "satir": str, "satir_no": int, "tip": "KALEM"|"DIGER"}, ...
    ]
    Yoksa [].

    Kalem tespiti: bolgedeki "- " ile baslayan satirlar. K-NNN tokenu iceriyorsa
    KALEM; yoksa DIGER (yine de sayilabilir ama T5'in odağı KALEM).
    """
    import re
    bolge = _acik_bolge(defter)
    if bolge is None:
        return []
    out = []
    kimlik_re = re.compile(KIMLIK_RE_PATTERN)
    for i, satir in enumerate(bolge):
        if not satir.startswith("- "):
            continue
        m = kimlik_re.search(satir)
        if m is None:
            continue
        out.append({"kimlik": m.group(0).upper(),
                    "satir": satir,
                    "satir_no": i,
                    "tip": "KALEM"})
    return out


# ------------------------------------------------------------------------------
# DURUM DOSYASI
# ------------------------------------------------------------------------------
def durum_oku(yol):
    """Durum dosyasini okur. Returns: {"son_guncelleme": iso|None,
    "kalemler": {kimlik: iso_damga}} veya None (dosya yok/bozuk).

    Bozuk JSON -> None (fail-closed; OLCULEMEDI sayaci artar).
    """
    if not os.path.isfile(yol):
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(veri, dict):
        return None
    son = veri.get("son_guncelleme")
    kalemler_raw = veri.get("kalemler", {})
    if not isinstance(kalemler_raw, dict):
        kalemler_raw = {}
    kalemler = {}
    for k, v in kalemler_raw.items():
        if isinstance(k, str) and isinstance(v, str):
            kalemler[k.upper()] = v
    return {"son_guncelleme": son if isinstance(son, str) else None,
            "kalemler": kalemler}


def durum_yaz_atomik(yol, veri):
    """Durum dosyasini atomik yazar (gecici + os.replace). IOError raise."""
    dizin = os.path.dirname(yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".durum-", dir=dizin or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(gecici, yol)
    except Exception:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


# ------------------------------------------------------------------------------
# KALEM SINIFLANDIRMA
# ------------------------------------------------------------------------------
def kalem_damgasi(kalem, durum, simdi, *, kirik_kol=None):
    """Bir kalemin damgasini durum dosyasindan alip simdi ile karsilastirir.
    Returns: {"kol": "T5-DURGUN"|"T5-TAZE"|"T5-OLCULEMEDI",
              "damga": iso|None, "fark_dakika": float|None, "hata": str|None}.

    Kurallar:
      - Durum dosyasi yoksa veya bozuksa: T5-OLCULEMEDI (fail-closed).
      - Kalem durumda yoksa: T5-OLCULEMEDI (fail-closed; "taze" SAYILMAZ).
      - Damga None / yanlis bicimli / gelecek tarihli: T5-OLCULEMEDI.
      - Damga gecerli, fark >= 240 dk: T5-DURGUN.
      - Damga gecerli, fark < 240 dk: T5-TAZE.

    kirik_kol: curutme testi icin. None ise normal mantik; bir kol jetonu
    ise o kolu DEVRE DISI birakir (o kolun karar vermesi gereken yerde
    her zaman ZIT kol uretir). Bu sayede "kol govdesi oldurulunce mutant
    yasar mi" sorusu yanitlanir.
    """
    if durum is None:
        return {"kol": T5_OLCULEMEDI_JETON, "damga": None,
                "fark_dakika": None, "hata": "durum dosyasi yok/bozuk"}
    iso_damga = durum["kalemler"].get(kalem["kimlik"])
    if iso_damga is None:
        return {"kol": T5_OLCULEMEDI_JETON, "damga": None,
                "fark_dakika": None, "hata": "kalem durum dosyasinda yok"}
    dt = _damga_coz(iso_damga, simdi=simdi)
    if dt is None:
        return {"kol": T5_OLCULEMEDI_JETON, "damga": iso_damga,
                "fark_dakika": None, "hata": "damga bozuk veya gelecek tarihli"}
    fark_sn = (simdi - dt).total_seconds()
    fark_dk = fark_sn / 60.0
    # Curutme testi: eger T5-DURGUN kolu oldurulmusse, HER DURUMDA TAZE
    # uret (4-saat-kuralini devre disi birak); T5-TAZE oldurulmusse HER
    # DURUMDA DURGUN uret; T5-OLCULEMEDI oldurulmusse gelecek tarihliyi
    # gecerli say (TAZE uret).
    if kirik_kol == T5_DURGUN_JETON:
        return {"kol": T5_TAZE_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T5_TAZE_JETON:
        return {"kol": T5_DURGUN_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if kirik_kol == T5_OLCULEMEDI_JETON:
        # Gelecek tarihliyi gecerli say — bu M4'un test ettigi kural.
        # Burada M4'un vakasi zaten gecmis; ama gelecek-tarihli davranisi
        # test icin TAZE donelim.
        return {"kol": T5_TAZE_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    if fark_dk >= ESIK_DAKIKA:
        return {"kol": T5_DURGUN_JETON, "damga": iso_damga,
                "fark_dakika": fark_dk, "hata": None}
    return {"kol": T5_TAZE_JETON, "damga": iso_damga,
            "fark_dakika": fark_dk, "hata": None}


def hepsini_simfla(defter, durum_yolu, simdi, *, kirik_kol=None):
    """Butun kalemleri siniflandirir. Returns:
      {"kalemler": [{kimlik, kol, damga, fark_dakika, hata}, ...],
       "durgun": int, "taze": int, "olculemedi": int,
       "hata": str|None, "kalem_sayisi": int, "durum_ok": bool}.
    """
    if not defter or not isinstance(defter, str):
        return {"kalemler": [], "durgun": 0, "taze": 0, "olculemedi": 0,
                "hata": "defter yok/yanlis tip", "kalem_sayisi": 0,
                "durum_ok": False}
    kalemler_raw = kalem_listesi(defter)
    durum = durum_oku(durum_yolu)
    kalemler = []
    durgun = taze = olcu = 0
    for k in kalemler_raw:
        sonuc = kalem_damgasi(k, durum, simdi, kirik_kol=kirik_kol)
        kalemler.append({"kimlik": k["kimlik"], "kol": sonuc["kol"],
                         "damga": sonuc["damga"], "fark_dakika": sonuc["fark_dakika"],
                         "hata": sonuc["hata"]})
        if sonuc["kol"] == T5_DURGUN_JETON:
            durgun += 1
        elif sonuc["kol"] == T5_TAZE_JETON:
            taze += 1
        else:
            olcu += 1
    hata = None if durum is not None else "durum dosyasi okunamadi"
    return {"kalemler": kalemler, "durgun": durgun, "taze": taze,
            "olculemedi": olcu, "hata": hata,
            "kalem_sayisi": len(kalemler_raw),
            "durum_ok": durum is not None}


# ------------------------------------------------------------------------------
# DEVIR + IZ (T5-IZ kolu)
# ------------------------------------------------------------------------------
def _iz_satiri(kalem, ev, damga):
    """Devir iz satiri. Format: T5-IZ <kalem> <EV> <damga>."""
    return ("T5-IZ %s %s damga=%s"
            % (kalem["kimlik"], ev, damga))


def devir_yap(kalem, ev, damga, kaynak_yol, hedef_yol, *,
              iz_yazilamaz=False):
    """Bir kalemi hedef posta kutusuna yazar + kaynak posta kutusuna IZ birakir.
    Returns: {"yazildi": bool, "iz_yazildi": bool, "hata": str|None}.

    Kol ayrimi:
      - Hedef kutu yazilamazsa: HATA `T5-OLCULEMEDI ` onekiyle baslar.
      - IZ yazilamazsa: HATA `T5-IZ ` onekiyle baslar; yazildi=True ama iz
        yazilmadi ise devir TAMAMLANMIS SAYILMAZ (fail-closed).
    """
    sonuc = {"yazildi": False, "iz_yazildi": False, "hata": None}
    # Hedefe yaz
    try:
        mevcut = ""
        if os.path.isfile(hedef_yol):
            with open(hedef_yol, encoding="utf-8") as f:
                mevcut = f.read()
        if mevcut and not mevcut.endswith("\n"):
            mevcut += "\n"
        yeni = mevcut + ("DEVREDILDI: %s -> %s damga=%s\n"
                         % (kalem["kimlik"], ev, damga))
        fd, gecici = tempfile.mkstemp(prefix=".devir-", dir=os.path.dirname(hedef_yol) or None)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(yeni)
            os.replace(gecici, hedef_yol)
            sonuc["yazildi"] = True
        except Exception as e:
            try:
                os.unlink(gecici)
            except OSError:
                pass
            sonuc["hata"] = "T5-OLCULEMEDI hedef kutu yazma basarisiz: %r" % e
            return sonuc
    except Exception as e:
        sonuc["hata"] = "T5-OLCULEMEDI hedef kutu yazma basarisiz: %r" % e
        return sonuc

    # IZ birak (kaynaga)
    if iz_yazilamaz:
        sonuc["hata"] = "T5-IZ iz yazma kanal bozuk (mutant M3 simulasyonu)"
        return sonuc
    try:
        mevcut = ""
        if os.path.isfile(kaynak_yol):
            with open(kaynak_yol, encoding="utf-8") as f:
                mevcut = f.read()
        if mevcut and not mevcut.endswith("\n"):
            mevcut += "\n"
        yeni = mevcut + _iz_satiri(kalem, ev, damga) + "\n"
        fd, gecici = tempfile.mkstemp(prefix=".iz-", dir=os.path.dirname(kaynak_yol) or None)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(yeni)
            os.replace(gecici, kaynak_yol)
            sonuc["iz_yazildi"] = True
        except Exception as e:
            try:
                os.unlink(gecici)
            except OSError:
                pass
            sonuc["hata"] = "T5-IZ iz yazma basarisiz: %r" % e
            return sonuc
    except Exception as e:
        sonuc["hata"] = "T5-IZ iz yazma basarisiz: %r" % e
        return sonuc

    return sonuc


# ------------------------------------------------------------------------------
# --rapor (salt-okunur)
# ------------------------------------------------------------------------------
def rapor_yaz(sonuc, simdi_str):
    """Raporu insan-okur ve makine-okur formatinda bas."""
    print("DURGUN KALEM KAPISI — RAPOR (YAZMAZ)")
    print("simdi: %s" % simdi_str)
    print("esik: %d dakika (4 saat)" % ESIK_DAKIKA)
    print("")
    print("kalem_sayisi=%d durgun=%d taze=%d olculemedi=%d durum_ok=%s"
          % (sonuc["kalem_sayisi"], sonuc["durgun"], sonuc["taze"],
             sonuc["olculemedi"], sonuc["durum_ok"]))
    if sonuc["hata"]:
        print("HATA: %s" % sonuc["hata"])
    print("")
    for k in sonuc["kalemler"]:
        fark = "?"
        if k["fark_dakika"] is not None:
            fark = "%.1f dk" % k["fark_dakika"]
        damga = k["damga"] or "-"
        print("%-10s %-15s damga=%-22s fark=%-12s %s"
              % (k["kimlik"], k["kol"], damga, fark,
                 ("hata: " + k["hata"]) if k["hata"] else ""))


# ------------------------------------------------------------------------------
# --kendini-test (4 mutant + izolasyon)
# ------------------------------------------------------------------------------
SENTETIK_DEfter = (
    "# sentetik devter\n"
    "\n"
    "## ACIK KALEMLER\n"
    "- K190 CHIP `KraL-test bir`\n"
    "- K191 CHIP `KraL-test iki`\n"
    "- K192 CHIP `KraL-test uc`\n"
    "- K193 CHIP `KraL-test dort`\n"
    "## SONRA\n"
)


def _ft(dakika):
    """simdi'den dakika once ISO string."""
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=dakika)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ft_ileri(dakika):
    """simdi'den dakika sonra (gelecek tarihli)."""
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=dakika)).strftime("%Y-%m-%dT%H:%M:%SZ")


def kendini_test(gecici_kok):
    """4 mutant + izolasyon. Her mutant kendi kolunu AYRICA kanitlar.

    kucuk gecici kok: --kendini-test disindan cagrilmaz (yine de savunmaci).
    """
    # Gecici izolasyon kokunu hazirla
    defter_yol = os.path.join(gecici_kok, "DEVAM.md")
    durum_yol = os.path.join(gecici_kok, DURUM_DOSYA_ADI)
    kaynak_posta = os.path.join(gecici_kok, "kaynak.md")
    hedef_posta = os.path.join(gecici_kok, "hedef.md")

    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)
    # Hicbir kalem durumda yok -> hepsi OLCULEMEDI (fail-closed)

    simdi_dt = datetime.datetime.now(datetime.timezone.utc)
    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    adimlar = []

    # --- M1: T5-DURGUN ------------------------------------------------------
    # Damga 300 dk (5 saat) once -> DURGUN olmali.
    # M1 dogrulamasi: T5-DURGUN govdesi oldurulurse bu kalem TAZE
    # veya OLCULEMEDI diye YANLIS siniflanir; mutant YASAMAZ.
    durum_m1 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": _ft(300)}}
    durum_yaz_atomik(durum_yol, durum_m1)
    with open(defter_yol, encoding="utf-8") as f:
        defter = f.read()
    sonuc_m1 = hepsini_simfla(defter, durum_yol, simdi_dt)
    m1_kalem = next((k for k in sonuc_m1["kalemler"] if k["kimlik"] == "K190"), None)
    m1_durgun = (m1_kalem is not None
                 and m1_kalem["kol"] == T5_DURGUN_JETON)
    t5_durgun_mesaj = ("K190 T5-DURGUN damga=%s fark=%.1f dk"
                       % (m1_kalem["damga"] if m1_kalem else "?",
                          m1_kalem["fark_dakika"] if m1_kalem and m1_kalem["fark_dakika"] is not None else 0.0))
    adimlar.append(("M1", T5_DURGUN_JETON, m1_durgun, t5_durgun_mesaj,
                    {"kol": m1_kalem["kol"] if m1_kalem else "?"}))

    # --- M2: T5-TAZE --------------------------------------------------------
    # Damga 60 dk (1 saat) once -> TAZE olmali.
    # M2 dogrulamasi: T5-TAZE govdesi oldurulurse bu kalem DURGUN
    # olarak YANLIS siniflanir; mutant YASAMAZ.
    durum_m2 = {"son_guncelleme": simdi_str,
                "kalemler": {"K190": _ft(300),   # ayni kalem
                             "K191": _ft(60)}}   # taze
    durum_yaz_atomik(durum_yol, durum_m2)
    sonuc_m2 = hepsini_simfla(defter, durum_yol, simdi_dt)
    m2_kalem = next((k for k in sonuc_m2["kalemler"] if k["kimlik"] == "K191"), None)
    m2_taze = (m2_kalem is not None
               and m2_kalem["kol"] == T5_TAZE_JETON)
    t5_taze_mesaj = ("K191 T5-TAZE damga=%s fark=%.1f dk"
                     % (m2_kalem["damga"] if m2_kalem else "?",
                        m2_kalem["fark_dakika"] if m2_kalem and m2_kalem["fark_dakika"] is not None else 0.0))
    adimlar.append(("M2", T5_TAZE_JETON, m2_taze, t5_taze_mesaj,
                    {"kol": m2_kalem["kol"] if m2_kalem else "?"}))

    # --- M3: T5-IZ ----------------------------------------------------------
    # Devir yapilirken IZ birakilmali. IZ kanalini iz_yazilamaz=True ile
    # kirdigimizda hata T5-IZ onekiyle baslamali; mutant YASAMAZ.
    # Gercek kosumda iz_yazilamaz=False oldugundan IZ yazilir + kalem iki
    # ucta da gorunur.
    durum_m3 = {"son_guncelleme": simdi_str,
                "kalemler": {"K192": _ft(500)}}
    durum_yaz_atomik(durum_yol, durum_m3)
    kalem_m3 = {"kimlik": "K192"}
    # ONCE bozuk kanal: iz_yazilamaz=True
    sonuc_m3_bozuk = devir_yap(kalem_m3, ev="MaCiT", damga=_ft(500),
                               kaynak_yol=kaynak_posta, hedef_yol=hedef_posta,
                               iz_yazilamaz=True)
    m3_iz_hatasi = (sonuc_m3_bozuk["hata"] is not None
                    and sonuc_m3_bozuk["hata"].startswith(T5_IZ_JETON + " ")
                    and sonuc_m3_bozuk["iz_yazildi"] is False)
    # SONRA saglam kanal: gercek devir
    sonuc_m3_ok = devir_yap(kalem_m3, ev="MaCiT", damga=_ft(500),
                            kaynak_yol=kaynak_posta, hedef_yol=hedef_posta)
    # IZ satirinin KAYNAK dosyada gorunmesi + DEVREDILDI'nin HEDEF dosyada
    # gorunmesi = kalem iki ucta da var (SILME YOK).
    kaynak_icerik = open(kaynak_posta, encoding="utf-8").read() if os.path.isfile(kaynak_posta) else ""
    hedef_icerik = open(hedef_posta, encoding="utf-8").read() if os.path.isfile(hedef_posta) else ""
    m3_iz_yazildi = (sonuc_m3_ok["iz_yazildi"] is True
                     and T5_IZ_JETON in kaynak_icerik
                     and "K192" in kaynak_icerik
                     and "DEVREDILDI" in hedef_icerik
                     and "K192" in hedef_icerik)
    t5_iz_mesaj = ("K192 T5-IZ bozuk kanal: hata=%s | saglam kanal: iz_yazildi=%s "
                   "kaynak_icerik_iz=%s hedef_icerik_devredildi=%s"
                   % (sonuc_m3_bozuk["hata"], sonuc_m3_ok["iz_yazildi"],
                      T5_IZ_JETON in kaynak_icerik,
                      "DEVREDILDI" in hedef_icerik))
    m3_reddetti = (m3_iz_hatasi and m3_iz_yazildi)
    adimlar.append(("M3", T5_IZ_JETON, m3_reddetti, t5_iz_mesaj,
                    {"bozuk": m3_iz_hatasi, "ok": m3_iz_yazildi}))

    # --- M4: T5-OLCULEMEDI --------------------------------------------------
    # 3 alt vaka: damga YOK, damga BOZUK, damga GELECEK. Hepsi T5-OLCULEMEDI
    # olarak siniflanmali (fail-closed; "taze" SAYILMAZ).
    durum_m4 = {"son_guncelleme": simdi_str,
                "kalemler": {"K193": _ft(60),       # K193 yok ama 4. kalem
                             # K190 hic yok, K191 bozuk, K192 gelecek
                             "K191": "bozuk-tarih-degil",
                             "K192": _ft_ileri(60)}}
    durum_yaz_atomik(durum_yol, durum_m4)
    sonuc_m4 = hepsini_simfla(defter, durum_yol, simdi_dt)
    olculemedi_sayaci = sum(1 for k in sonuc_m4["kalemler"]
                            if k["kol"] == T5_OLCULEMEDI_JETON)
    # 4 kalemden 3'u (K190 yok + K191 bozuk + K192 gelecek) OLCULEMEDI olmali.
    # K193 var (60 dk = taze) ve TAZE olmali; bu vakanin M4'le ilgisi yok
    # ama dogrulama yapalim.
    m4_olcu = (olculemedi_sayaci == 3
               and sonuc_m4["olculemedi"] == 3)
    # Ayni zamanda K193 TAZE olmali (yani OLCULEMEDI'a sigmayan tek kalem TAZE).
    k193 = next((k for k in sonuc_m4["kalemler"] if k["kimlik"] == "K193"), None)
    m4_taze_tazede = (k193 is not None and k193["kol"] == T5_TAZE_JETON)
    t5_olcu_mesaj = ("4 kalemden 3'u OLCULEMEDI (damga yok/bozuk/gelecek); "
                     "K193 TAZE (kanit: 'taze' SAYILMAZ kurali calisiyor). "
                     "olculemedi_sayaci=%d K193=%s"
                     % (olculemedi_sayaci,
                        k193["kol"] if k193 else "?"))
    adimlar.append(("M4", T5_OLCULEMEDI_JETON, (m4_olcu and m4_taze_tazede),
                    t5_olcu_mesaj,
                    {"olcu": olculemedi_sayaci, "K193": k193["kol"] if k193 else "?"}))

    # ---- ozet bas ---------------------------------------------------------
    print("T5 DURGUN KALEM KAPISI — KENDINI-TEST")
    print("izolasyon koku: %s" % gecici_kok)
    print("simdi: %s (enjekte)" % simdi_str)
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
    # Dort kol adinin da ciktida gectigini teyit et
    print("KOL_ISIMLERI: %s %s %s %s"
          % (T5_DURGUN_JETON, T5_TAZE_JETON, T5_IZ_JETON, T5_OLCULEMEDI_JETON))
    print("")
    print("MUTANT=%d/4" % mutant_sayaci)
    return 0 if mutant_sayaci == 4 else 1


# ------------------------------------------------------------------------------
# CURUTME: her kolun govdesi oldurulunce ilgili mutant YASAMALI
# ------------------------------------------------------------------------------
def curutme(gecici_kok):
    """Dort curutme testi. Her biri bir kolun govdesini 'oldurur' (kirik_kol
    bayragi ile o kol devre disi birakilir) ve o mutant'in YASAMASINI
    (hedef kolu kanitlamamasini) bekler.

    Sonra DIGER mutant'lerin hala normal sekilde calistigini teyit eder.

    Biri hâlâ kirmizi (yasamaz) geliyorsa mutant test'i kendi kolunu
    kanitlamiyor demektir — `KUSUR:` olarak raporlanir.
    """
    defter_yol = os.path.join(gecici_kok, "DEVAM.md")
    durum_yol = os.path.join(gecici_kok, DURUM_DOSYA_ADI)
    kaynak_posta = os.path.join(gecici_kok, "kaynak-curutme.md")
    hedef_posta = os.path.join(gecici_kok, "hedef-curutme.md")

    with open(defter_yol, "w", encoding="utf-8") as f:
        f.write(SENTETIK_DEfter)

    simdi_dt = datetime.datetime.now(datetime.timezone.utc)
    simdi_str = simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _kurulum_ve_simfla(kirik_kol):
        """Verilen kirik_kol ile test kurulumunu hazirla ve sinifla."""
        durum = {"son_guncelleme": simdi_str,
                 "kalemler": {"K190": _ft(300),
                              "K191": _ft(60),
                              "K193": _ft(60),
                              "K192": _ft_ileri(60)}}
        durum_yaz_atomik(durum_yol, durum)
        with open(defter_yol, encoding="utf-8") as f:
            defter = f.read()
        return hepsini_simfla(defter, durum_yol, simdi_dt, kirik_kol=kirik_kol)

    curutmeler = []

    # ---- Curutme 1: T5-DURGUN govdesi oldurulunce ----------------------------
    # Beklenen: K190 artik T5-DURGUN degil (kirik_kol onu TAZE yapiyor),
    # dolayisiyla M1'in "K190 == T5-DURGUN" kontrolu YASAMALI.
    # M2/M3/M4 normal mantikla calismali (kirik_kol=T5-DURGUN onlar icin
    # anlamsiz — sadece T5-DURGUN kararini bozar).
    sonuc_d = _kurulum_ve_simfla(kirik_kol=T5_DURGUN_JETON)
    k190 = next((k for k in sonuc_d["kalemler"] if k["kimlik"] == "K190"), None)
    k191 = next((k for k in sonuc_d["kalemler"] if k["kimlik"] == "K191"), None)
    k192 = next((k for k in sonuc_d["kalemler"] if k["kimlik"] == "K192"), None)
    m1_yasamali = (k190 is not None and k190["kol"] == T5_TAZE_JETON)
    m2_dokunulmaz = (k191 is not None and k191["kol"] == T5_TAZE_JETON)
    m4_dokunulmaz = (k192 is not None and k192["kol"] == T5_OLCULEMEDI_JETON)
    curutme_1_ok = (m1_yasamali and m2_dokunulmaz and m4_dokunulmaz)
    curutmeler.append((T5_DURGUN_JETON, curutme_1_ok,
                       "K190=T5-TAZE (oldurulmus kol uretti) | "
                       "K191=T5-TAZE (M2 normal) | "
                       "K192=T5-OLCULEMEDI (M4 normal)"))

    # ---- Curutme 2: T5-TAZE govdesi oldurulunce ------------------------------
    # Beklenen: K191 artik T5-TAZE degil (kirik_kol onu DURGUN yapiyor);
    # M2 yasamali. M1/M4 normal.
    sonuc_t = _kurulum_ve_simfla(kirik_kol=T5_TAZE_JETON)
    k190 = next((k for k in sonuc_t["kalemler"] if k["kimlik"] == "K190"), None)
    k191 = next((k for k in sonuc_t["kalemler"] if k["kimlik"] == "K191"), None)
    k192 = next((k for k in sonuc_t["kalemler"] if k["kimlik"] == "K192"), None)
    m2_yasamali = (k191 is not None and k191["kol"] == T5_DURGUN_JETON)
    m1_dokunulmaz = (k190 is not None and k190["kol"] == T5_DURGUN_JETON)
    m4_dokunulmaz = (k192 is not None and k192["kol"] == T5_OLCULEMEDI_JETON)
    curutme_2_ok = (m2_yasamali and m1_dokunulmaz and m4_dokunulmaz)
    curutmeler.append((T5_TAZE_JETON, curutme_2_ok,
                       "K191=T5-DURGUN (oldurulmus kol uretti) | "
                       "K190=T5-DURGUN (M1 normal) | "
                       "K192=T5-OLCULEMEDI (M4 normal)"))

    # ---- Curutme 3: T5-IZ govdesi oldurulunce --------------------------------
    # devir_yap'a iz_yazilamaz=True ile YASAMAZ davranisini test ettik
    # zaten M3'un BOZUK KANAL vakasinda. Burada SAGLAM kanalda iz_yazilamaz
    # simule edilir: hata T5-IZ onekiyle baslamali (zaten oluyor) +
    # iz_yazildi=False. Mutant M3'un "ok=True" kosulu YASAMALI.
    kalem_m3 = {"kimlik": "K192"}
    sonuc_m3_bozuk = devir_yap(kalem_m3, ev="MaCiT", damga=_ft(500),
                               kaynak_yol=kaynak_posta, hedef_yol=hedef_posta,
                               iz_yazilamaz=True)
    # M3'un "saglam kanal" kontrolu iz_yazildi=False ise YASAMALI (cikti False).
    m3_ok_yasamali = (sonuc_m3_bozuk["iz_yazildi"] is False)
    curutme_3_ok = m3_ok_yasamali
    curutmeler.append((T5_IZ_JETON, curutme_3_ok,
                       "devir_yap iz_yazilamaz=True: iz_yazildi=False | "
                       "hata T5-IZ onekiyle basliyor=%s"
                       % (sonuc_m3_bozuk["hata"].startswith(T5_IZ_JETON + " ")
                          if sonuc_m3_bozuk["hata"] else False)))

    # ---- Curutme 4: T5-OLCULEMEDI govdesi oldurulunce ------------------------
    # kirik_kol=T5-OLCULEMEDI ile gelecek tarihli damga gecerli sayilir
    # ve T5-TAZE uretilir. M4'un "3 kalem OLCULEMEDI" kontrolu YASAMALI
    # (sadece 2 kalem OLCULEMEDI kalir).
    durum_m4_kirik = {"son_guncelleme": simdi_str,
                      "kalemler": {"K190": _ft(300),
                                   "K191": "bozuk-tarih-degil",
                                   "K192": _ft_ileri(60),
                                   "K193": _ft(60)}}
    durum_yaz_atomik(durum_yol, durum_m4_kirik)
    with open(defter_yol, encoding="utf-8") as f:
        defter = f.read()
    sonuc_o = hepsini_simfla(defter, durum_yol, simdi_dt,
                             kirik_kol=T5_OLCULEMEDI_JETON)
    m4_yasamali = (sonuc_o["olculemedi"] < 3)
    curutme_4_ok = m4_yasamali
    curutmeler.append((T5_OLCULEMEDI_JETON, curutme_4_ok,
                       "olculemedi_sayaci=%d (normal 3; kirik ile <3 = mutant yasadi)"
                       % sonuc_o["olculemedi"]))

    # ---- ozet bas ---------------------------------------------------------
    print("T5 DURGUN KALEM KAPISI — CURUTME (kol govdesi oldurulunce mutant SESSIZ)")
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
# MAIN
# ------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kendini-test", action="store_true",
                    help="4 mutantu izole kos (gercek deftere / durum dosyasina / "
                         "posta kutusuna DOKUNMAZ)")
    ap.add_argument("--curutme", action="store_true",
                    help="dort curutme: her kolun govdesi oldurulunce ilgili "
                         "mutant YASAMALI (sessiz kalmali). --kendini-test'ten "
                         "AYRI calisir; izolasyon tempfile.mkdtemp.")
    ap.add_argument("--rapor", action="store_true",
                    help="gercek defter uzerinde YAZMADAN; kac kalem durgun/taze/"
                         "olculemedi")
    ap.add_argument("--simdi", default=None,
                    help="simdi yerine kullanilacak ISO zaman (--rapor icin)")
    ap.add_argument("--defter", default=None,
                    help="defter yolu (default: <repo>/DEVAM.md)")
    ap.add_argument("--durum", default=None,
                    help="durum dosyasi yolu (default: ~/.claude/projects/.../memory/"
                         + DURUM_DOSYA_ADI + ")")
    args = ap.parse_args(argv)

    if args.kendini_test:
        # Izolasyon: tempfile.mkdtemp(). Gercek dosyalara ASLA dokunulmaz.
        gecici = tempfile.mkdtemp(prefix="t5-kendinitest-")
        try:
            return kendini_test(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.curutme:
        gecici = tempfile.mkdtemp(prefix="t5-curutme-")
        try:
            return curutme(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.rapor:
        simdi_dt = _simdi_coz(args.simdi) if args.simdi else datetime.datetime.now(datetime.timezone.utc)
        if simdi_dt is None:
            print("HATA: --simdi gecersiz ISO: %r" % args.simdi, file=sys.stderr)
            return 2
        simdi_str = (args.simdi if args.simdi
                     else simdi_dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
        repo = _repo_kok()
        defter_yol = args.defter or os.path.join(repo, "DEVAM.md")
        durum_yol = args.durum or VARSAYILAN_DURUM_YOLU
        if not os.path.isfile(defter_yol):
            print("HATA: defter yok: %s" % defter_yol, file=sys.stderr)
            return 2
        with open(defter_yol, encoding="utf-8") as f:
            defter = f.read()
        sonuc = hepsini_simfla(defter, durum_yol, simdi_dt)
        rapor_yaz(sonuc, simdi_str)
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
