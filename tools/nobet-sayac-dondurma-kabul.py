#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K341 KABUL — onarimsiz sayacinin DONDURMA korlugu (28 Agu 2026).

Yama: `tools/nobet-sayac-dondurma-yama.py`. Hedef: `~/.claude/cron/nobet-kapi.py`.

🔴 BU BATARYA DIZGE DEGIL DAVRANIS OLCER: her vaka gercek `tur_kapat()`i
hermetik bir defter/geri-iz/sayac/bayrak dortlusuyle KOSTURUR ve sayacin
DISKTEKI degerini okur ([[n2b-kapisi-dizge-olcer]] · [[prob-gercek-isi-taklit-etmeli]]).

🔴 TABAN VAKASI ZORUNLU: V1 YAMASIZ kaynagi kosturur ve sayacin ARTTIGINI
gosterir. Taban olculmeden "duzeldi" denemez
([[olcut-civilenirken-taban-olculmeli]] · [[bayat-taban-hipotezi-kosumdan-once-curutulur]]).

🔴 GEVSETME KAPISI: V3/V4 KONTROL vakalari bayrak ISIRMADIGINDA (ADAY=0)
sayacin HALA ARTTIGINI olcer. M6 mutanti tam da bu ayrimi oldurur; kontrol
vakasi olmadan bu yama bir gevsetmedir
([[emir-ariza-kovasina-duserse-hat-kendi-kendine-kirmizi-yanar]]).

Kullanim:
    python3 tools/nobet-sayac-dondurma-kabul.py [--kok <cron-agaci>]
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

VARSAYILAN_KOK = os.environ.get("PRUVO_NOBET_KOK") or os.path.expanduser(
    "~/.claude/cron")
CRON = VARSAYILAN_KOK
KAPI = os.path.join(CRON, "nobet-kapi.py")
YAMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "nobet-sayac-dondurma-yama.py")

VAKALAR = []      # (ad, beklenen, olculen, gecti)
_ISO_DESENI = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def kok_ayarla(kok):
    global CRON, KAPI
    CRON = kok
    KAPI = os.path.join(kok, "nobet-kapi.py")


def vaka(ad, beklenen, olculen):
    gecti = str(beklenen) == str(olculen)
    VAKALAR.append((ad, beklenen, olculen, gecti))
    print("VAKA=%-42s BEKLENEN=%-26s OLCULEN=%-26s SONUC=%s"
          % (ad, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


def _modul(yol, ad):
    # 🔴 cron koku sys.path'te OLMAZSA kardes import'lar (kilit,
    # nobet_merdiven) ModuleNotFoundError verir ve batarya "kol dustu" degil
    # "OLCEMEDIM" durumuna duser.
    # 🔴 `--kok` hermetik bir dizini gosterebilir; kardes moduller (kilit,
    # nobet_merdiven) orada YOKTUR. GERCEK cron koku da yola eklenir, yoksa
    # batarya "kol dustu" degil "OLCEMEDIM" durumuna duser.
    for _p in (VARSAYILAN_KOK, CRON):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# ===========================================================================
# HERMETIK ORTAM
# ===========================================================================
_DEFTER_BASI = (
    "# sentetik defter\n\n"
    "| id | tarih | kimden→kime | is | durum | kanit |\n"
    "|---|---|---|---|---|---|\n")

# Dagitilabilir kalem: `kime` Okan DEGIL, metinde OKAN jetonu YOK.
_SATIR_DAGITILABILIR = "| K901 | 2026-08-28 | Mimar→Isci | sentetik mekanik is | ACIK | - |\n"
# Dagitilamaz kalem: `kime=Okan` -> KOVA_OKAN (aday havuzuna GIRMEZ), ama
# kalem ACIK oldugu icin kova BOS DEGILDIR -> IS_YOK koluna DUSMEZ.
_SATIR_OKAN = "| K902 | 2026-08-28 | Mimar→Okan | sentetik karar kalemi | ACIK | - |\n"


def _ortam(gecici, dagitilabilir, dondur, sayac, damga="2026-08-26"):
    """Hermetik dortlu kurar; (defter, geri_iz, sayac_yolu, bayrak) doner."""
    defter = os.path.join(gecici, "defter.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write(_DEFTER_BASI
                + (_SATIR_DAGITILABILIR if dagitilabilir else "")
                + _SATIR_OKAN)
    geri_iz = os.path.join(gecici, "geri-iz.json")
    with open(geri_iz, "w", encoding="utf-8") as f:
        json.dump({"tur_no": 100, "kalemler": {}}, f)
    sayac_yolu = os.path.join(gecici, "sayac.json")
    with open(sayac_yolu, "w", encoding="utf-8") as f:
        json.dump({"ustuste_onarimsiz": sayac}, f)
    bayrak = os.path.join(gecici, "dondurma.json")
    if dondur:
        with open(bayrak, "w", encoding="utf-8") as f:
            json.dump({"dagitim_donduruldu": True,
                       "sebep": "SENTETIK_EMIR", "damga": damga}, f)
    return defter, geri_iz, sayac_yolu, bayrak


def tur_kos(modul_yolu, dagitilabilir, dondur, sayac=10, damga="2026-08-26"):
    """Gercek `tur_kapat()`i hermetik ortamda kosar.

    Doner: {"sayac": <diskten>, "kayit": <json>, "rapor": str, "hukum": str}
    """
    gecici = tempfile.mkdtemp(prefix="k341-")
    try:
        modul = _modul(modul_yolu, "k341kapi_" + os.path.basename(gecici))
        defter, geri_iz, sayac_yolu, bayrak = _ortam(
            gecici, dagitilabilir, dondur, sayac, damga)
        modul.DEFTER_YOLU = defter
        modul.GERI_IZ_YOLU = geri_iz
        modul.ONARIMSIZ_SAYAC_YOLU = sayac_yolu
        modul.DONDURMA_BAYRAK_YOLU = bayrak
        # 🔴 env ezmesi bayrak DOSYASINI atlatir; seviye kolu damgayi
        # dosyadan okudugu icin ezme KAPALI olmalidir.
        onceki_env = os.environ.pop("PRUVO_NOBET_DONDURMA", None)
        try:
            sonuc = modul.tur_kapat(kuru=False, yaz=True)
        finally:
            if onceki_env is not None:
                os.environ["PRUVO_NOBET_DONDURMA"] = onceki_env
        with open(sayac_yolu, encoding="utf-8") as f:
            kayit = json.load(f)
        return {"sayac": int(kayit.get("ustuste_onarimsiz", -1)),
                "kayit": kayit,
                "rapor": sonuc.get("rapor") or "",
                "hukum": sonuc.get("hukum") or "-"}
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# ===========================================================================
# YAMASIZ TABAN KOPYASI
# ===========================================================================

def _yamasiz_kopya(gecici):
    """Kurulu kopyanin YAMASIZ halini uretir (yedekten ya da ters cevirerek).

    Kurulu dosya ZATEN yamaliysa yamanin `_YENI -> _CAPA` tersini uygulayarak
    taban uretilir. Ters cevrilemezse (None) taban vakasi OLCULEMEDI olur —
    sessizce "gecti" SAYILMAZ.
    """
    yama = _modul(YAMA, "k341yama")
    with open(KAPI, encoding="utf-8") as f:
        metin = f.read()
    for _ad, anahtar, capa, yeni, _isaret in yama.YAMALAR:
        if anahtar != "KAPI":          # taban YALNIZ nobet-kapi.py'den uretilir
            continue
        if yeni in metin:
            metin = metin.replace(yeni, capa, 1)
        elif capa not in metin:
            return None
    hedef = os.path.join(gecici, "nobet-kapi-TABAN.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(metin)
    return hedef


# ===========================================================================
# VAKALAR
# ===========================================================================

def bolum_taban(ek=""):
    """V1 — YAMASIZ kaynak: donmus turda sayac ARTAR (arizanin kendisi)."""
    gecici = tempfile.mkdtemp(prefix="k341-taban-")
    try:
        taban = _yamasiz_kopya(gecici)
        if taban is None:
            vaka("V1-taban-donmus-tur-sayac%s" % ek, 11, "OLCULEMEDI:ters_cevrilemedi")
            return
        s = tur_kos(taban, dagitilabilir=True, dondur=True, sayac=10)
        vaka("V1-taban-donmus-tur-sayac%s" % ek, 11, s["sayac"])
        vaka("V1b-taban-hukmu-yesil%s" % ek, "DAGITIM_DONDURULDU", s["hukum"])
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def bolum_davranis(kapi_yolu, ek="", yalniz=None):
    """V2-V4 — yamali kaynak: ISIRAN dondurma sifirlar, ISIRMAYAN ARTIRIR."""
    def _ist(ad):
        return yalniz is None or ad in yalniz

    if _ist("V2"):
        s = tur_kos(kapi_yolu, dagitilabilir=True, dondur=True, sayac=10)
        vaka("V2-isiran-dondurma-sifirlar%s" % ek, 0, s["sayac"])
        vaka("V2b-hukum-bozulmadi%s" % ek, "DAGITIM_DONDURULDU", s["hukum"])
        vaka("V2c-isirdi-satiri-durur%s" % ek, True,
             "DONDURMA_ISIRDI=1 ENGELLENEN=1" in s["rapor"])
    if _ist("V6"):
        s = tur_kos(kapi_yolu, dagitilabilir=True, dondur=True, sayac=10)
        vaka("V6-kayit-son-hal%s" % ek, "DONDURULDU", s["kayit"].get("son_hal"))
        vaka("V6b-kayit-son-iso%s" % ek, True,
             bool(_ISO_DESENI.match(str(s["kayit"].get("son_iso") or ""))))
        vaka("V6c-kayit-son-sebep%s" % ek, "SENTETIK_EMIR",
             s["kayit"].get("son_sebep"))
    if _ist("V8"):
        s = tur_kos(kapi_yolu, dagitilabilir=True, dondur=True, sayac=10,
                    damga="2026-08-26")
        vaka("V8-seviye-satiri%s" % ek, True,
             "DONDURMA_SEVIYE GUN=" in s["rapor"])
        vaka("V8b-seviye-eskale-edilir%s" % ek, True,
             "ESKALASYON=OKAN DONDURMA_GUN=" in s["rapor"])
    if _ist("V8c"):
        # Damga BOZUK -> seviye OLCULEMEDI, ama eskalasyon FAIL-CLOSED yanar.
        s = tur_kos(kapi_yolu, dagitilabilir=True, dondur=True, sayac=10,
                    damga="bozuk-damga")
        vaka("V8c-damga-bozuk-failclosed%s" % ek, True,
             "ESKALASYON=OKAN DONDURMA_GUN=OLCULEMEDI" in s["rapor"])
    # --- KONTROL: GEVSETME YOK ---
    if _ist("V3"):
        s = tur_kos(kapi_yolu, dagitilabilir=False, dondur=True, sayac=10)
        vaka("V3-KONTROL-isirmayan-dondurma-artirir%s" % ek, 11, s["sayac"])
        vaka("V3b-KONTROL-isirmadi-satiri%s" % ek, True,
             "DONDURMA_ISIRDI=0" in s["rapor"])
    if _ist("V4"):
        s = tur_kos(kapi_yolu, dagitilabilir=False, dondur=False, sayac=10)
        vaka("V4-KONTROL-dondurma-yok-artirir%s" % ek, 11, s["sayac"])


def bolum_kapi(kapi_yolu, ek="", yalniz=None):
    """V5/V9/V10/V11 — sayac kapisinin KENDI yuklemleri (birim)."""
    def _ist(ad):
        return yalniz is None or ad in yalniz

    modul = _modul(kapi_yolu, "k341kapi_birim" + ek.replace("-", "_"))
    gecici = tempfile.mkdtemp(prefix="k341-birim-")
    try:
        yol = os.path.join(gecici, "sayac.json")

        def _kur(deger, ham=None):
            with open(yol, "w", encoding="utf-8") as f:
                json.dump(ham if ham is not None
                          else {"ustuste_onarimsiz": deger}, f)

        if _ist("V5"):
            # ONARIM dondurmayi EZER: donmus turda kalem KAPANDIYSA o onarimdir.
            _kur(9)
            n, yazildi = modul.tur_sayacini_kaydet("KOSTU_ONARDI", 1, yol=yol)
            vaka("V5-onarim-dondurmayi-ezer%s" % ek, "0/True",
                 "%s/%s" % (n, yazildi))
        if _ist("V9"):
            # Geriye donuk uyum: ESKI tek-alanli dosya okunabilmeli.
            _kur(None, ham={"ustuste_onarimsiz": 7})
            vaka("V9-eski-bicim-okunur%s" % ek, 7,
                 modul.ustuste_onarimsiz_oku(yol))
        if _ist("V10"):
            # Fail-closed: bilinmeyen hal SESSIZ gecmez.
            _kur(3)
            try:
                modul.tur_sayacini_kaydet("SACMA_HAL", yol=yol)
                sonuc = "SESSIZ_GECTI"
            except ValueError:
                sonuc = "ValueError"
            vaka("V10-bilinmeyen-hal-failclosed%s" % ek, "ValueError", sonuc)
        if _ist("V11"):
            _kur(5)
            n, yazildi = modul.tur_sayacini_kaydet("ATLANDI", yol=yol)
            vaka("V11-atlandi-yazmaz%s" % ek, "5/False", "%s/%s" % (n, yazildi))
        if _ist("V12"):
            # DONDURULDU hali TUR_HALLERI'nde tanimli VE sifirlayici.
            _kur(12)
            n, _ = modul.tur_sayacini_kaydet("DONDURULDU", 0, yol=yol,
                                             sebep="X")
            vaka("V12-donduruldu-hali-sifirlar%s" % ek, 0, n)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def bolum_seviye(kapi_yolu, ek="", yalniz=None):
    """V7 — seviye BAYRAGIN damgasindan okunur, sayactan DEGIL."""
    def _ist(ad):
        return yalniz is None or ad in yalniz

    modul = _modul(kapi_yolu, "k341kapi_seviye" + ek.replace("-", "_"))
    gecici = tempfile.mkdtemp(prefix="k341-sev-")
    try:
        bayrak = os.path.join(gecici, "d.json")
        onceki_env = os.environ.pop("PRUVO_NOBET_DONDURMA", None)
        try:
            if _ist("V7"):
                with open(bayrak, "w", encoding="utf-8") as f:
                    json.dump({"dagitim_donduruldu": True, "sebep": "X",
                               "damga": "2026-08-26"}, f)
                import datetime as _dt
                gun, _s = modul.dondurma_seviyesi(
                    yol=bayrak, simdi=_dt.datetime(2026, 8, 28, 12, 0, 0))
                vaka("V7-seviye-damgadan%s" % ek, 2, gun)
            if _ist("V7b"):
                with open(bayrak, "w", encoding="utf-8") as f:
                    json.dump({"dagitim_donduruldu": True, "sebep": "X",
                               "damga": "XX"}, f)
                gun, sebep = modul.dondurma_seviyesi(yol=bayrak)
                vaka("V7b-bozuk-damga-none%s" % ek, "None/DAMGA_BOZUK",
                     "%s/%s" % (gun, str(sebep).split(":")[0]))
            if _ist("V7c"):
                with open(bayrak, "w", encoding="utf-8") as f:
                    json.dump({"dagitim_donduruldu": False}, f)
                gun, sebep = modul.dondurma_seviyesi(yol=bayrak)
                vaka("V7c-donmus-degil-none%s" % ek, "None/DONMUS_DEGIL",
                     "%s/%s" % (gun, str(sebep).split(":")[0]))
        finally:
            if onceki_env is not None:
                os.environ["PRUVO_NOBET_DONDURMA"] = onceki_env
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# ===========================================================================
# MUTANTLAR
# ===========================================================================
# 🔴 HEDEF/KONTROL kumeleri TAM VAKA ADIYLA yazilir, ONEKLE DEGIL. Ilk surumde
# onek eslestirmesi vardi ve `V8` oneki `V8b`/`V8c`yi de yakaliyordu: ayni vaka
# HEM hedef HEM kontrol sayilip atif daima HAYIR cikti
# ([[ad-iki-rolde-mutanti-golgeler]] — ayni sinif, olcen tarafta).
V2 = "V2-isiran-dondurma-sifirlar"
V3 = "V3-KONTROL-isirmayan-dondurma-artirir"
V4 = "V4-KONTROL-dondurma-yok-artirir"
V5 = "V5-onarim-dondurmayi-ezer"
V6 = "V6-kayit-son-hal"
V8 = "V8-seviye-satiri"
V8B = "V8b-seviye-eskale-edilir"
V8C = "V8c-damga-bozuk-failclosed"
V11 = "V11-atlandi-yazmaz"
V12 = "V12-donduruldu-hali-sifirlar"

MUTANTLAR = [
    # (ad, eski, yeni, hedef, kontrol, gruplar)
    ("M1-donduruldu-kolu-olur",
     '    if hal in ("IS_YOK", "DONDURULDU"):',
     '    if hal in ("IS_YOK",):',
     [V2, V12], [V3, V4, V5, V11], {"V2", "V3", "V4", "V5", "V11", "V12"}),
    ("M2-cagri-yeri-gecirmez",
     '            else "DONDURULDU" if _dondurma_isirdi\n',
     '',
     [V2], [V3, V4, V5, V11, V12], {"V2", "V3", "V4", "V5", "V11", "V12"}),
    ("M3-dondu-yuklemi-olur",
     "    if kova_bos or dondu or onarim > 0:",
     "    if kova_bos or onarim > 0:",
     [V2, V12], [V3, V4, V5, V11], {"V2", "V3", "V4", "V5", "V11", "V12"}),
    ("M4-kayit-kolu-olur",
     '                       "son_hal": hal or "-",',
     '                       "son_hal": "-",',
     [V6], [V2, V3, V4, V12], {"V2", "V3", "V4", "V6", "V12"}),
    ("M5-seviye-tuketicisi-olur",
     "        if _dgun is None or _dgun >= DONDURMA_ESKALASYON_GUN:",
     "        if False:",
     # 🔴 V8 (seviye SATIRI) KONTROLDUR: satir yazilmaya devam etmeli, olen
     # yalniz TUKETICI olmali — "yazan var okuyan yok" haline geri donus.
     [V8B, V8C], [V8, V2, V3, V4], {"V2", "V3", "V4", "V8", "V8c"}),
    # 🔴 GEVSETME MUTANTI: `_dondurma_isirdi` kosulu kalkarsa bayrak ISIRMASA
    # da (hatta bayrak HIC YOKKEN de) sayac sifirlanir -> IKI kontrol vakasi
    # da KIRMIZI olmali. Bu mutant olmezse yaptigimiz sey onarim degil
    # GEVSETMEDIR. V4 hedeftedir cunku `if True` dondurma YOKKEN de isirir.
    ("M6-GEVSETME-isirma-kosulu-olur",
     '            else "DONDURULDU" if _dondurma_isirdi\n',
     '            else "DONDURULDU" if True\n',
     [V3, V4], [V2, V12], {"V2", "V3", "V4", "V12"}),
]


def mutant_kos(mutant, ozet):
    ad, eski, yeni, hedef, kontrol, gruplar = mutant
    gecici = tempfile.mkdtemp(prefix="k341-m-")
    try:
        with open(KAPI, encoding="utf-8") as f:
            metin = f.read()
        n = metin.count(eski)
        if n != 1:
            # 🔴 Capa tek degilse mutant OLCMEZ; sessizce "oldu" SAYILAMAZ.
            print("MUTANT=%-34s OLCULEMEDI CAPA_SAYISI=%d" % (ad, n))
            ozet.append((ad, False, False, "CAPA_SAYISI=%d" % n))
            return
        kopya = os.path.join(gecici, "nobet-kapi.py")
        with open(kopya, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni, 1))

        isaret = len(VAKALAR)
        etiket = "-" + ad.split("-")[0]
        try:
            bolum_davranis(kopya, ek=etiket, yalniz=gruplar)
            bolum_kapi(kopya, ek=etiket, yalniz=gruplar)
        except Exception as hata:      # mutant COKERSE sessiz gecmez
            print("MUTANT=%-34s COKTU %s: %s" % (ad, type(hata).__name__, hata))
        yeniler = VAKALAR[isaret:]
        del VAKALAR[isaret:]

        def _taban(ad_):
            return ad_[:-len(etiket)] if ad_.endswith(etiket) else ad_

        def _dusenler(kume):
            return [v[0] for v in yeniler if not v[3] and _taban(v[0]) in kume]

        def _mevcut(kume):
            return [v[0] for v in yeniler if _taban(v[0]) in kume]

        hedef_kume, kontrol_kume = set(hedef), set(kontrol)
        hedef_dusen = _dusenler(hedef_kume)
        kontrol_dusen = _dusenler(kontrol_kume)
        # 🔴 TAM ATIF: hedefin HEPSI olmeli. "biri oldu" yetmezse mutant
        # yarim olculur ve kol OLU kalabilir.
        eksik_hedef = [h for h in hedef if h not in
                       set(_taban(v) for v in _mevcut(hedef_kume))]
        oldu = not eksik_hedef and len(hedef_dusen) == len(hedef)
        atif = oldu and not kontrol_dusen
        print("MUTANT=%-34s %-7s ATIF=%-5s hedef_dusen=%s kontrol_dusen=%s"
              % (ad, "OLDU" if oldu else "YASADI", "EVET" if atif else "HAYIR",
                 hedef_dusen or "-", kontrol_dusen or "-"))
        ozet.append((ad, oldu, atif, "-"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def kontrol_mutanti(ozet):
    """K0 — HIC mutasyon yok: her sey YESIL olmali. Batarya kararli mi?"""
    isaret = len(VAKALAR)
    bolum_davranis(KAPI, ek="-K0")
    bolum_kapi(KAPI, ek="-K0")
    bolum_seviye(KAPI, ek="-K0")
    yeniler = VAKALAR[isaret:]
    dusen = [v[0] for v in yeniler if not v[3]]
    print("MUTANT=%-34s %-7s (%d vaka) dusen=%s"
          % ("K0-kontrol", "YESIL" if not dusen else "KIRMIZI",
             len(yeniler), dusen or "-"))
    ozet.append(("K0-kontrol", not dusen, not dusen, "-"))
    return not dusen


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    for i, parca in enumerate(argv):
        if parca == "--kok" and i + 1 < len(argv):
            kok_ayarla(os.path.abspath(os.path.expanduser(argv[i + 1])))
        elif parca.startswith("--kok="):
            kok_ayarla(os.path.abspath(os.path.expanduser(parca.split("=", 1)[1])))
    print("=== K341 KABUL — OLCULEN KOK: %s ===" % CRON)
    print("--- BOLUM T: TABAN (YAMASIZ kaynak) ---")
    bolum_taban()
    print("--- BOLUM K0: YAMALI KAYNAK ---")
    kararli = kontrol_mutanti([])
    print("--- MUTANTLAR ---")
    ozet = []
    for m in MUTANTLAR:
        mutant_kos(m, ozet)
    oldu = sum(1 for _a, o, _t, _n in ozet if o)
    atif = sum(1 for _a, _o, t, _n in ozet if t)
    gecti = sum(1 for *_x, g in VAKALAR if g)
    print("TOPLAM=%d GECTI=%d KALDI=%d" % (len(VAKALAR), gecti,
                                           len(VAKALAR) - gecti))
    print("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL_MUTANTI=%s"
          % (oldu, len(MUTANTLAR), atif, len(MUTANTLAR),
             "YESIL" if kararli else "KIRMIZI"))
    if not kararli:
        print("KABUL=OLCULEMEDI (K0 kontrol mutanti kirmizi — batarya kararsiz)")
        return 3
    if gecti != len(VAKALAR) or oldu != len(MUTANTLAR) or atif != len(MUTANTLAR):
        print("KABUL=KALDI")
        return 1
    print("KABUL=GECTI (%d/%d vaka · %d/%d mutant · atif %d/%d)"
          % (gecti, len(VAKALAR), oldu, len(MUTANTLAR), atif, len(MUTANTLAR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
