#!/usr/bin/env python3
"""KOR GOZ KABULU — K1..K7 (cip KraL-KorGoz-27Agu, 27 Agu 2026).

CIVILI, GEVSETILMEZ. Her madde bir HUKUM satiri basar:
  `K<n> HUKUM=GECTI|KALDI|OLCULEMEDI ...`
Sonda `KABUL=GECTI|KALDI` + `KX=<gecen>/<toplam>`.

⚖️ DONDURMA EMRI: hicbir madde `acilan_tur=1` TALEP ETMEZ — emir yururlukteyken
o olcut hicbir zaman gecemez ve gecmemelidir.

🔴 MUTASYON CANLI DOSYADA YAPILMAZ. Her mutant icin gecici bir SEMBOLIK-BAG
CIFTLIGI kurulur (`~/.claude/cron`'un tum dosyalarina symlink), yalniz hedef
dosya GERCEK kopyayla degistirilir. Boylece `CRON_KOKU`-goreli import'lar
(`gozcu.py`, `kilit.py`, `nobet-kapi.py`) cozulur ama canli dosyalarin BIR
BAYTI bile degismez.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

CRON = "/Users/okan/.claude/cron"
TETIK = os.path.join(CRON, "nobet-tetik.py")
TETIK_TEST = os.path.join(CRON, "nobet-tetik-test.py")
KAPI = os.path.join(CRON, "nobet-kapi.py")
KAT_KOVASI_TEST = os.path.join(CRON, "nobet-kat-kovasi-test.py")
CI_LOG = os.path.join(CRON, "ci-nobeti.log")
GOZCU_LOG = os.path.join(CRON, "gozcu.log")
DEFTER = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md"
T4_YOLU = "/Users/okan/dev/pruvo/tools/parti-borc-kapisi.py"

SIMDI = 1_755_000_000.0
BUGUN = "2026-08-27"

# TABAN — 27 Agu, ONARIMDAN ONCE olculdu (korgoz_olcum.py ciktisi, birebir).
TABAN = {
    "F1": 10, "F2": 10, "F3": 10, "F4": 0,
    "F2_F3_ESIT": 1,
    "ACIK_KALEM": 0,
    "N2B_ACIK": 12,
    "BATARYA_VAKA": 71,
    "DEFTER_SATIR": 88,
    # N2B ikinci okuyucusunun TABAN hukum satiri — onarimdan ONCE, canli
    # kapinin kendi agzindan birebir alindi (isci.sh reddi, 27 Agu):
    #   N2B HUKUM=RED KOL=N2B-RED EV=KraL ACIK=12 KALEM=K306,...,K316
    "N2B_HUKUM": "RED",
    "N2B_KALEM": ("K306,K309,K314,K310,K311,K140,K152,K161,K188,K312,K291,K316"),
}

# K5 fiksturu: DONMUS defter metni. N2B okuyucusunun bu metin uzerindeki sayisi
# SABITTIR; canli defter baskalari tarafindan degistirilse bile bu sayi kaymaz.
# "Benim yamam bu okuyucuyu oynatti mi?" sorusunu CANLI sayidan BAGIMSIZ olarak
# cevaplayan tek olcum budur ([[bayat-taban-hipotezi-kosumdan-once-curutulur]]).
K5_FIKSTUR_DEFTER = """| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |
|---|---|---|---|---|---|
| K901 | 2026-08-27 | A→B | acik kalem | ACIK | - |
| K902 | 2026-08-27 | A→B | onarim kalemi | 🔧 | - |
| K903 | 2026-08-27 | A→B | ucusta kalem | UCUSTA | - |
| K904 | 2026-08-27 | A→B | okan kapisi | OKAN-KAPISI | - |
| K905 | 2026-08-27 | A→B | kapanmis kalem | KAPANDI | - |
| K906 | 2026-08-27 | A→B | tanimsiz durum | DEVREDILDI (ArTisT) | - |
"""
K5_FIKSTUR_BEKLENEN = 4      # ACIK + 🔧 + UCUSTA + OKAN-KAPISI

SONUCLAR = []
SATIRLAR = []


def hukum(kod, verdict, detay):
    SONUCLAR.append((kod, verdict))
    SATIRLAR.append("%s HUKUM=%s %s" % (kod, verdict, detay))


def not_(metin):
    SATIRLAR.append(metin)


# --------------------------------------------------------------------------
def modul_yukle(ad, yol, kok=None):
    kok = kok or os.path.dirname(os.path.abspath(yol))
    if kok not in sys.path:
        sys.path.insert(0, kok)
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
        if kok in sys.path:
            sys.path.remove(kok)
    return modul


def ciftlik_kur(hedef_ad, yeni_icerik):
    """CRON'un symlink ciftligi; yalniz `hedef_ad` gercek (mutantli) kopya."""
    kok = tempfile.mkdtemp(prefix="korgoz-mutant-")
    for ad in os.listdir(CRON):
        kaynak = os.path.join(CRON, ad)
        if not os.path.isfile(kaynak):
            continue
        try:
            os.symlink(kaynak, os.path.join(kok, ad))
        except OSError:
            pass
    yol = os.path.join(kok, hedef_ad)
    try:
        os.unlink(yol)
    except OSError:
        pass
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni_icerik)
    return kok, yol


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------------
# FIKSTURLER (korgoz_olcum.py ile BIREBIR ayni — ikiz tanim yok, kopya var
# ama degerler tek kaynaktan: asagidaki `_kalp` varsayilanlari)
# --------------------------------------------------------------------------
def _kalp(**ek):
    temel = {
        "damga": "2026-08-27T00:00:00Z", "epok": SIMDI, "tetik": "YOK",
        "llm_turu": False, "yeni_kirmizi": 0, "kirmizi_toplam": 0,
        "hedef_run": "", "dagitilabilir": 0, "kat_mimar": 0, "kat_okan": 0,
        "kat_isci": 0, "gunluk_gerekli": False, "ci_olculdu": True,
        "ci_sebep": "TAMAM", "defter_olculdu": True, "icra_rc": None,
        "icra_denendi": False, "icra_hal": "KOSULMADI",
        "kosum_hukmu": "TEMIZ", "uretken": True,
        "uretken_sebep": "ICRA_DENENMEDI", "eskalasyon_acik": 0,
    }
    temel.update(ek)
    return temel


def fiksturler():
    return {
        "F1": _kalp(kirmizi_toplam=11, icra_denendi=True, icra_hal="KOSTU",
                    kosum_hukmu="TEMIZ", uretken=True, uretken_sebep="TEMIZ"),
        "F2": _kalp(kirmizi_toplam=11),
        "F3": _kalp(kirmizi_toplam=0),
        "F4": _kalp(tetik="CI_KIRMIZI", hedef_run="99887766", yeni_kirmizi=1,
                    kirmizi_toplam=1),
    }


def fikstur_rc(NT):
    tablo = {}
    for ad, kalp in fiksturler().items():
        k = NT.karar(kalp, SIMDI, BUGUN)
        tablo[ad] = {"rc": NT.cikis_kodu(k), "sebep": k.sebep,
                     "hukum": k.hukum, "kirmizi": bool(k.kirmizi),
                     "satir": NT.karar_satiri(k)}
    return tablo


# ==========================================================================
def k1_seviye(NT):
    t = fikstur_rc(NT)
    for ad in ("F1", "F2", "F3", "F4"):
        not_("K1_FIKSTUR %s rc=%d hukum=%s sebep=%s kirmizi=%d (taban rc=%d)"
             % (ad, t[ad]["rc"], t[ad]["hukum"], t[ad]["sebep"],
                1 if t[ad]["kirmizi"] else 0, TABAN[ad]))
    ayri = t["F2"]["rc"] != t["F3"]["rc"]
    f4_korundu = t["F4"]["rc"] == TABAN["F4"] and t["F4"]["hukum"] == "AC"
    f3_yesil = t["F3"]["rc"] == 10 and not t["F3"]["kirmizi"]
    detay = ("F2_rc=%d F3_rc=%d F2_F3_ESIT=%d (taban 1) F3_KONTROL_YESIL=%d "
             "F4_TUR_ACILIYOR=%d" % (t["F2"]["rc"], t["F3"]["rc"],
                                     0 if ayri else 1,
                                     1 if f3_yesil else 0,
                                     1 if f4_korundu else 0))
    hukum("K1", "GECTI" if (ayri and f4_korundu and f3_yesil) else "KALDI", detay)
    return t


def k2_mutant_seviye():
    """MUTANT-SEVIYE: hedef kol OLDURULUNCE F2 yeniden F3'e esitlenir ve F4
    DEGISMEZ -> kirmizinin SEBEBI hedef koldur (K182 sinifi). KONTROL YESIL."""
    kaynak = oku(TETIK)
    hedef_capa = '''    seviye = seviye_kirmizisi(kalp)
    if seviye < 0:
        return Karar("ACMA", "SEVIYE_OLCULEMEDI", "", (), True)
    if seviye > 0:
        return Karar("ACMA", "SEVIYE_KIRMIZI_%d" % seviye, "", (), True)
    return None'''
    if kaynak.count(hedef_capa) != 1:
        hukum("K2", "OLCULEMEDI",
              "M-SEVIYE capasi %d kez bulundu (beklenen 1) — yama kurulu mu?"
              % kaynak.count(hedef_capa))
        return
    mutantlar = {
        "M-SEVIYE": kaynak.replace(hedef_capa, "    return None  # M-SEVIYE", 1),
        "KONTROL": kaynak.replace("# 7. Yesil: tur ACILMAZ.",
                                  "# 7. Yesil: tur ACILMAZ. (KONTROL MUTANTI)", 1),
    }
    olcum = {}
    for ad, icerik in mutantlar.items():
        kok, yol = ciftlik_kur("nobet-tetik.py", icerik)
        try:
            M = modul_yukle("tetik_%s" % ad.replace("-", "_"), yol, kok)
            olcum[ad] = {k: v["rc"] for k, v in fikstur_rc(M).items()}
        except Exception as hata:
            olcum[ad] = {"HATA": repr(hata)}
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        not_("K2_MUTANT %s -> %s" % (ad, json.dumps(olcum[ad], sort_keys=True)))
    m = olcum.get("M-SEVIYE", {})
    c = olcum.get("KONTROL", {})
    oldu = m.get("F2") == m.get("F3") == TABAN["F2"]       # tabana geri dondu
    f4_sabit = m.get("F4") == TABAN["F4"]                   # yan hasar YOK
    kontrol_yesil = c.get("F2") != c.get("F3") and c.get("F4") == TABAN["F4"]
    hukum("K2", "GECTI" if (oldu and f4_sabit and kontrol_yesil) else "KALDI",
          "M-SEVIYE_F2=%s M-SEVIYE_F3=%s (tabana_dondu=%d) F4_DEGISMEDI=%d "
          "KONTROL_YESIL=%d" % (m.get("F2"), m.get("F3"), 1 if oldu else 0,
                                1 if f4_sabit else 0, 1 if kontrol_yesil else 0))


def k3_dondurma(NT, t):
    """Donmus tur 'kirmizi YOK' DEMEZ; gercek kirmizida tetik_rc=11.
    `acilan_tur=1` TALEP EDILMEZ."""
    duran = t["F2"]
    satir = duran["satir"]
    yanlis_yesil = ("KIRMIZI=0" in satir) or ("sebep=YESIL" in satir)
    rc11 = duran["rc"] == 11
    not_("K3_TETIK_SATIRI %s" % satir)

    # Dondurma damgasi CANLI hatta gorunuyor mu? (Bu kol ZATEN kuruluydu;
    # burada REGRESYON olcuyoruz — dirilltmiyoruz.)
    damga = atif = 0
    ornek = "-"
    for yol in (CI_LOG, GOZCU_LOG):
        try:
            with open(yol, encoding="utf-8", errors="replace") as f:
                for s in f:
                    if "DONDURULDU@" in s:
                        damga += 1
                        if "ATIF=BAYRAK" in s:
                            atif += 1
                            ornek = s.strip()[:160]
        except OSError:
            continue
    not_("K3_DONDURMA damga_gecisi=%d ATIF_BAYRAK=%d ornek=%s"
         % (damga, atif, ornek))
    if damga == 0:
        hukum("K3", "OLCULEMEDI",
              "canli logda `DONDURULDU@` damgasi YOK — dondurma kolunun canli "
              "izi bu pencerede olusmamis; tetik ayagi rc11=%d yanlis_yesil=%d"
              % (1 if rc11 else 0, 1 if yanlis_yesil else 0))
        return
    hukum("K3", "GECTI" if (rc11 and not yanlis_yesil and atif > 0) else "KALDI",
          "duran_kirmizi_rc=%d YANLIS_YESIL=%d ATIF_BAYRAK=%d "
          "acilan_tur_TALEP_EDILMEDI=1"
          % (duran["rc"], 1 if yanlis_yesil else 0, atif))


def _ciplak_defter_sayimi():
    """Hicbir parser kullanmayan kolon-5 sayimi (K4'un bagimsiz dogrulamasi)."""
    sayac = {}
    satir = 0
    with open(DEFTER, encoding="utf-8") as f:
        for s in f:
            if not s.startswith("| K"):
                continue
            kolon = s.split("|")
            if len(kolon) < 7 or not re.match(r"^K\d+$", kolon[1].strip()):
                continue
            satir += 1
            sayac[kolon[5].strip()] = sayac.get(kolon[5].strip(), 0) + 1
    return satir, sayac


def k4_acik_kalem(NK):
    tum = NK.defter_oku()
    onarilacak = NK.onarim_kalemleri(tum)
    bilinmeyen = NK.bilinmeyen_durumlu_kalemler(tum)
    sahipli = NK.sahipli_kalemler(tum)
    satir, ciplak = _ciplak_defter_sayimi()
    ciplak_acik = ciplak.get("ACIK", 0)
    not_("K4_OKUYUCU_A ACIK_KALEM=%d KALEM=%s"
         % (len(onarilacak), ",".join(k["id"] for k in onarilacak) or "-"))
    not_("K4_CIPLAK K_SATIR=%d ACIK=%d DAGILIM=%s"
         % (satir, ciplak_acik, json.dumps(ciplak, ensure_ascii=False,
                                           sort_keys=True)[:400]))
    not_("K4_SOZLUK SAHIPLI=%d BILINMEYEN_DURUM=%d BILINMEYEN=%s"
         % (len(sahipli), len(bilinmeyen),
            ",".join("%s(%s)" % (k["id"], k["durum"]) for k in bilinmeyen) or "-"))
    esles = len(onarilacak) == ciplak_acik
    hukum("K4", "GECTI" if (len(onarilacak) > 0 and esles) else "KALDI",
          "ACIK_KALEM=%d (taban %d) CIPLAK_GREP_ACIK=%d ESLESTI=%d"
          % (len(onarilacak), TABAN["ACIK_KALEM"], ciplak_acik,
             1 if esles else 0))
    return len(onarilacak)


def k5_ikinci_okuyucu():
    """N2B parti kapisinin okudugu `ACIK=<n>` — DEGISTIRILMEYEN okuyucu."""
    try:
        T4 = modul_yukle("parti_borc", T4_YOLU)
        kalemler, okundu, hata = T4.acik_kalem_listesi(DEFTER)
    except Exception as h:
        hukum("K5", "OLCULEMEDI", "T4 yuklenemedi: %r" % (h,))
        return
    n = len(kalemler)
    canli_ids = [k["kimlik"] for k in kalemler]
    not_("K5_N2B_CANLI ACIK=%d okundu=%s hata=%s SOZLUK=%s KALEM=%s"
         % (n, okundu, hata or "-", ",".join(sorted(T4.ACIK_DURUMLAR)),
            ",".join(canli_ids) or "-"))

    # --- (1) YAPISAL BAGIMSIZLIK: bu okuyucu `nobet-kapi.py`yi ICE AKTARIYOR MU?
    # Aktarmıyorsa bu cipin yamasi onun sayisini OYNATAMAZ — iddia degil, olcum.
    kaynak = oku(T4_YOLU)
    ad_gecisi = kaynak.count("nobet-kapi") + kaynak.count("nobet_kapi")
    dinamik = sum(kaynak.count(j) for j in
                  ("spec_from_file_location", "import_module", "exec_module"))
    bagli = bool(ad_gecisi or dinamik)
    not_("K5_BAGIMSIZLIK parti-borc-kapisi.py :: nobet-kapi_ad_gecisi=%d "
         "dinamik_yukleme=%d -> BAGIMSIZ=%d (yamanin bu okuyucuya ulasabilecegi "
         "bir kablo YOK)" % (ad_gecisi, dinamik, 0 if bagli else 1))

    # --- (2) DONMUS FIKSTUR: canli defter baskalarinca degisse bile bu sayi
    # SABIT kalmali. Yamanin bu okuyucuyu oynatip oynatmadigini CANLI sayidan
    # BAGIMSIZ olarak yalniz bu olcer.
    gecici = tempfile.mkdtemp(prefix="korgoz-k5-")
    try:
        fyol = os.path.join(gecici, "acik-kalemler.md")
        with open(fyol, "w", encoding="utf-8") as f:
            f.write(K5_FIKSTUR_DEFTER)
        fkalem, fokundu, fhata = T4.acik_kalem_listesi(fyol)
        fikstur_n = len(fkalem)
    except Exception as h:
        fikstur_n, fokundu, fhata = -1, False, repr(h)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    not_("K5_FIKSTUR donmus_defter ACIK=%d beklenen=%d okundu=%s hata=%s"
         % (fikstur_n, K5_FIKSTUR_BEKLENEN, fokundu, fhata or "-"))
    fikstur_sabit = fikstur_n == K5_FIKSTUR_BEKLENEN

    # --- (3) CANLI FARKIN ATFI: taban listesiyle id farki + her yeni id'nin
    # defterdeki durum hucresi. "Sessiz kayma YOK" sarti tam olarak budur.
    taban_ids = TABAN["N2B_KALEM"].split(",")
    yeni_ids = [i for i in canli_ids if i not in taban_ids]
    dusen_ids = [i for i in taban_ids if i not in canli_ids]
    ham = {}
    try:
        with open(DEFTER, encoding="utf-8") as f:
            for s in f:
                if not s.startswith("| K"):
                    continue
                kolon = s.split("|")
                if len(kolon) < 7:
                    continue
                ham[kolon[1].strip()] = kolon[5].strip()[:40]
    except OSError:
        pass
    not_("K5_FARK taban=%d canli=%d fark=%+d YENI=%s DUSEN=%s"
         % (TABAN["N2B_ACIK"], n, n - TABAN["N2B_ACIK"],
            ",".join("%s(%s)" % (i, ham.get(i, "?")) for i in yeni_ids) or "-",
            ",".join(dusen_ids) or "-"))

    # --- (4) BLOKLAMA HUKMU: sayi degil, kapinin KENDI hukmu okunur.
    kapi_hukum = "OLCULEMEDI"
    kapi_satir = "-"
    try:
        PK = modul_yukle("parti_kapisi_k5", os.path.join(
            os.path.dirname(T4_YOLU), "parti-kapisi.py"))
        sonuc = PK.parti_karari("/Users/okan/dev/pruvo", "yeni-parti")
        kapi_satir = PK.hukum_satiri(sonuc)
        kapi_hukum = sonuc.get("HUKUM") or "OLCULEMEDI"
    except Exception as h:
        kapi_satir = "OLCULEMEDI %r" % (h,)
    not_("K5_KAPI_HUKMU taban=%s sonra=%s satir=%s"
         % (TABAN["N2B_HUKUM"], kapi_hukum, kapi_satir))
    hukum_sinifi_ayni = kapi_hukum == TABAN["N2B_HUKUM"]

    # HUKUM: (a) okuyucu yapisal olarak bagimsiz, (b) donmus fiksturde sayi
    # SABIT, (c) canli farkin her id'si ATFEDILMIS (yabanci satir), (d) kapinin
    # hukum SINIFI degismemis -> YENI bir ev BLOKLANMADI.
    atif_tam = all(i in ham for i in yeni_ids)
    hukum("K5", "GECTI" if (not bagli and fikstur_sabit and atif_tam
                            and hukum_sinifi_ayni) else "KALDI",
          "BAGIMSIZ=%d FIKSTUR_SABIT=%d CANLI_FARK=%+d ATIF_TAM=%d "
          "KAPI_HUKMU=%s->%s YENI_BLOKLAMA=%d"
          % (0 if bagli else 1, 1 if fikstur_sabit else 0,
             n - TABAN["N2B_ACIK"], 1 if atif_tam else 0,
             TABAN["N2B_HUKUM"], kapi_hukum,
             0 if hukum_sinifi_ayni else 1))


def k6_mutant_sozluk():
    """M-SOZLUK: hedef kume tabana dondurulunce ACIK_KALEM 0'a duser.
    M-PARTISYON: butunluk emniyeti oldurulmeden kume daraltilirsa import PATLAR
    (fail-loud kol GERCEKTEN yasiyor mu). KONTROL YESIL."""
    kaynak = oku(KAPI)
    capa = 'ONARILACAK_DURUMLAR = (ONARIM_DURUMU, "ACIK")'
    kapali_capa = 'KAPALI_DURUMLAR_DEFTER = ("KAPANDI",)'
    if kaynak.count(capa) != 1 or kaynak.count(kapali_capa) != 1:
        hukum("K6", "OLCULEMEDI", "M-SOZLUK capasi bulunamadi — yama kurulu mu?")
        return
    mutantlar = {
        # Hedef kol OLUR, partisyon butunlugu KORUNUR -> import gecer, sayi duser.
        "M-SOZLUK": kaynak.replace(capa, "ONARILACAK_DURUMLAR = (ONARIM_DURUMU,)", 1)
                          .replace(kapali_capa,
                                   'KAPALI_DURUMLAR_DEFTER = ("KAPANDI", "ACIK")', 1),
        # Butunluk emniyeti: kume daraltilir, kova YAZILMAZ -> import PATLAMALI.
        "M-PARTISYON": kaynak.replace(capa,
                                      "ONARILACAK_DURUMLAR = (ONARIM_DURUMU,)", 1),
        "KONTROL": kaynak.replace("# --- KORGOZ_K311_SOZLUK sonu",
                                  "# --- KORGOZ_K311_SOZLUK sonu (KONTROL MUTANTI)", 1),
    }
    olcum = {}
    for ad, icerik in mutantlar.items():
        kok, yol = ciftlik_kur("nobet-kapi.py", icerik)
        try:
            M = modul_yukle("kapi_%s" % ad.replace("-", "_"), yol, kok)
            olcum[ad] = {"ACIK_KALEM": len(M.onarim_kalemleri(M.defter_oku())),
                         "IMPORT": "GECTI"}
        except Exception as hata:
            olcum[ad] = {"IMPORT": "PATLADI", "sebep": type(hata).__name__}
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        not_("K6_MUTANT %s -> %s" % (ad, json.dumps(olcum[ad], sort_keys=True)))
    m = olcum.get("M-SOZLUK", {})
    p = olcum.get("M-PARTISYON", {})
    c = olcum.get("KONTROL", {})
    dustu = m.get("ACIK_KALEM") == TABAN["ACIK_KALEM"]
    patladi = p.get("IMPORT") == "PATLADI"
    kontrol = c.get("IMPORT") == "GECTI" and (c.get("ACIK_KALEM") or 0) > 0
    hukum("K6", "GECTI" if (dustu and patladi and kontrol) else "KALDI",
          "M-SOZLUK_ACIK_KALEM=%s (tabana_dondu=%d) M-PARTISYON_IMPORT=%s "
          "(fail_loud=%d) KONTROL_YESIL=%d"
          % (m.get("ACIK_KALEM"), 1 if dustu else 0, p.get("IMPORT"),
             1 if patladi else 0, 1 if kontrol else 0))


def k7_iki_tur(NT, NK):
    """K1 · K4 iki ardisik kosumda BIREBIR ayni rc/sayi."""
    imzalar = []
    for _ in range(2):
        t = fikstur_rc(NT)
        acik = len(NK.onarim_kalemleri(NK.defter_oku()))
        imzalar.append(json.dumps(
            {"F": {k: v["rc"] for k, v in t.items()}, "ACIK_KALEM": acik},
            sort_keys=True))
    not_("K7_TUR1 %s" % imzalar[0])
    not_("K7_TUR2 %s" % imzalar[1])
    hukum("K7", "GECTI" if imzalar[0] == imzalar[1] else "KALDI",
          "BIREBIR_AYNI=%d" % (1 if imzalar[0] == imzalar[1] else 0))


def mevcut_bataryalar():
    """Vakalar MEVCUT bataryaya eklenir; tabani kacirmamak icin ikisi de kosar."""
    for ad, yol, taban in (("nobet-tetik-test.py", TETIK_TEST, TABAN["BATARYA_VAKA"]),
                           ("nobet-kat-kovasi-test.py", KAT_KOVASI_TEST, None)):
        try:
            p = subprocess.run([sys.executable, yol], capture_output=True,
                               text=True, timeout=900)
            ozet = "-"
            for s in reversed((p.stdout or "").strip().splitlines()):
                if s.startswith("VAKA=") or s.startswith("KABUL="):
                    ozet = s
                    break
            not_("BATARYA %s rc=%d ozet=%s taban_VAKA=%s"
                 % (ad, p.returncode, ozet, taban))
            for s in (p.stdout or "").splitlines():
                if s.startswith("KIRIK ") or s.startswith("DUSEN "):
                    not_("BATARYA_%s %s" % (ad, s))
        except Exception as hata:
            not_("BATARYA %s OLCULEMEDI %r" % (ad, hata))


def main():
    SATIRLAR.append("# KOR GOZ KABULU — cip KraL-KorGoz-27Agu")
    SATIRLAR.append("# TABAN (onarimdan ONCE, birebir): %s"
                    % json.dumps(TABAN, sort_keys=True))
    NT = modul_yukle("nobet_tetik_kabul", TETIK, CRON)
    NK = modul_yukle("nobet_kapi_kabul", KAPI, CRON)

    t = k1_seviye(NT)
    k2_mutant_seviye()
    k3_dondurma(NT, t)
    k4_acik_kalem(NK)
    k5_ikinci_okuyucu()
    k6_mutant_sozluk()
    k7_iki_tur(NT, NK)
    mevcut_bataryalar()

    gecen = sum(1 for _, v in SONUCLAR if v == "GECTI")
    SATIRLAR.append("KX=%d/%d" % (gecen, len(SONUCLAR)))
    SATIRLAR.append("KABUL=%s" % ("GECTI" if gecen == len(SONUCLAR) else "KALDI"))
    metin = "\n".join(SATIRLAR)
    print(metin)
    hedef = os.environ.get("KORGOZ_CIKTI")
    if hedef:
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin + "\n")
    return 0 if gecen == len(SONUCLAR) else 1


if __name__ == "__main__":
    sys.exit(main())
