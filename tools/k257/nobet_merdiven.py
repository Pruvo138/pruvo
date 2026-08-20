#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K257 — ESKALASYON MERDIVENI: prozadan SAYILAN kurala (20 Agu 2026, KraL).

KANONIK KAYNAK: pruvo deposu `tools/k257/nobet_merdiven.py`.
CANLI KOPYA:    /Users/okan/.claude/cron/nobet_merdiven.py  (git DISI duzlem)
CAGRI YERI:     `nobet-kapi.py::_kalemi_dusur` + `kalem_dagit` + `tur_kapat`
                (kapinin menzili KODU degil CAGRI YERIDIR — [[kapinin-menzili-cagri-yeridir]])

Okan'in merdiveni (20 Agu 2026):
    m3 (2 deneme) -> kimi (1) -> mimar kati (1) -> KraL -> BaBa -> Okan

Bu modul o merdiveni OLCULEBILIR hale getirir. Dort sart:

(a) DENEME SAYACI ISLE BIRLIKTE TASINIR. Sayac AYRI bir tamsayi DEGILDIR;
    `denemeler` listesinden TURETILIR. Boylece "her kat sifirdan sayar"
    kusuru YAZILAMAZ hale gelir (disiplinle degil, YAPIYLA).
    Her deneme: damga · basamak · motor · hal · yon · rc · atif.

(b) DORT HAL, UCU FARKLI YONE GIDER:
      KOTA         -> YANA      (m3 -> kimi) · sayac ARTMAZ
      YETENEK      -> YUKARI    · sayac ARTAR
      BITMEYEN_TUR -> KOVA      (B7'nin konusu; ayni tur YENIDEN KURULMAZ)
      KAPI_REDDI   -> SAHIBINE  · NE YANA NE YUKARI, sayaca DAHIL DEGIL
    KAPI_REDDI kolu K236'nin kok sebebidir: tur HIC BASLAMADIGI icin onu
    yukari tasimak, pahali katta AYNI DUVARA carpmaktir.

(c) YUKARI CIKAN IS OLCULMUSU DE GOTURUR: `denemeler` kalemle birlikte
    tasinir; ust kat sifirdan olcmez (hata sinifi + cikti atfi yaninda gelir).

(d) BABA BASAMAGI SAYACA DAHIL DEGILDIR — orada sayac degil SLA isler:
    kalem yasi > 24 saat ise Okan basamagi (`sla_karari`, `merdiven_ilerlet`
    o basamagi ASLA ilerletmez cunku tavani None'dir).

(e) IKINCI MOTOR LISTESI TUTULMAZ: isci basamaklari `CANLI_ISCI_MOTORLARI`'ndan
    TURETILIR ([[ikiz-tanim-sessiz-ayrisma]]). Canli kume BOS ise merdiven
    KURULMAZ ve hukum `OLCULEMEDI`'dir (fail-closed; bos kume "hepsi bitti"
    DEMEK DEGILDIR).

Kabul bataryasi: python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
"""

import calendar
import re
import time

# --- dort hal + yon tablosu ------------------------------------------------

HAL_KOTA = "KOTA"
HAL_YETENEK = "YETENEK"
HAL_BITMEYEN_TUR = "BITMEYEN_TUR"
HAL_KAPI_REDDI = "KAPI_REDDI"
DORT_HAL = (HAL_KOTA, HAL_YETENEK, HAL_BITMEYEN_TUR, HAL_KAPI_REDDI)

YON_YANA = "YANA"
YON_YUKARI = "YUKARI"
YON_KOVA = "KOVA"
YON_SAHIBINE = "SAHIBINE"

# 🔴 Bu tablo K257'nin CEKIRDEGIDIR: uc hal UC AYRI yone gider ve YALNIZ biri
# sayaci artirir. Tabloyu bozan mutant kabul bataryasinda KIRMIZI yanar.
YON_TABLOSU = {
    HAL_KOTA: YON_YANA,
    HAL_YETENEK: YON_YUKARI,
    HAL_BITMEYEN_TUR: YON_KOVA,
    HAL_KAPI_REDDI: YON_SAHIBINE,
}
SAYAC_ARTAR = {
    HAL_KOTA: False,
    HAL_YETENEK: True,
    HAL_BITMEYEN_TUR: False,
    HAL_KAPI_REDDI: False,
}

# --- basamaklar ------------------------------------------------------------

# K257: m3 IKI deneme, kimi BIR deneme. Fazla canli motor eklenirse tavani 1.
ISCI_TAVANLARI = (2, 1)
# BaBa: hukum/teshis kati, ICRA DEGIL -> tavan None (sayacla ILERLEMEZ, SLA ile).
INSAN_BASAMAKLARI = (
    ("MIMAR", "INSAN", 1),
    ("KRAL", "INSAN", 1),
    ("BABA", "HUKUM", None),
    ("OKAN", "INSAN", None),
)
BASAMAK_BABA = "BABA"
BASAMAK_OKAN = "OKAN"

SLA_SN = 24 * 3600          # (d) BaBa basamagi SLA'si — sayac DEGIL, YAS
# Ayni katta iki kez tur bitmezse "o kat bu isi bitiremiyor" hukmu dogar ve
# hal YETENEK'e YENIDEN SINIFLANIR (gorunur, sessiz degil). Aksi halde
# BITMEYEN_TUR sayaci hic artirmadigi icin merdiven sonsuz doner.
BITMEYEN_TUR_TAVANI = 2

# --- durumlar --------------------------------------------------------------

DURUM_DUSTU = "DUSTU"                   # isci katinda, yeniden dagitilir
DURUM_ESKALASYON = "ESKALASYON"         # insan/hukum kati — dagitilmaz
DURUM_ARAC_KUSURU = "ARAC_KUSURU"       # KAPI_REDDI: sahibine doner
DURUM_BITMEYEN_TUR = "BITMEYEN_TUR"     # B7 kovasi; BU TURDA yeniden kurulmaz
DURUM_KOTA_BEKLEMEDE = "KOTA_BEKLEMEDE"  # tum canli motorlar kotada
DAGITILMAZ_DURUMLAR = (DURUM_ESKALASYON, DURUM_ARAC_KUSURU, DURUM_KOTA_BEKLEMEDE)

# --- KAPI REDDI izleri -----------------------------------------------------

# 🔴 Bunlar TURUN HIC BASLAMADIGININ izleridir; hepsi bir KAPININ agzindan
# cikar ve her birinin bir SAHIBI vardir (kalem o sahibe doner).
KAPI_REDDI_DESENLERI = (
    (r"M[İI]MAR [İI]CRA KAPISI", "mimar-icra-kapisi"),
    (r"MIMAR ICRA KAPISI", "mimar-icra-kapisi"),
    (r"N2B\s+HUKUM\s*=\s*RED", "parti-kapisi"),
    (r"PARTI_KAPISI\s*=\s*RED", "parti-kapisi"),
    (r"komut-stili-kapisi", "komut-stili-kapisi"),
    (r"mimar-kod-kilidi", "mimar-kod-kilidi"),
    (r"AGENT[-_ ]KAPISI", "agent-kapisi"),
    (r"kabul-komutu-kapisi", "kabul-komutu-kapisi"),
    (r"KAPI_REDDI\s*=\s*1", "beyan"),
)
_KAPI_REDDI = tuple((re.compile(d, re.IGNORECASE), s)
                    for d, s in KAPI_REDDI_DESENLERI)

# B7'nin izi (tek kaynak: nobet-kapi.py `_sure_tavani_sonucu` bu jetonu basar).
SURE_TAVANI_JETONU = "SURE_TAVANI_ASILDI=1"


# ===========================================================================
# merdiven kurulumu
# ===========================================================================

def merdiven_kur(canli_motorlar):
    """(e) Isci basamaklarini CANLI kumeden TURETIR. Bos kume -> None.

    None donusu "merdiven yok" DEGIL, "OLCULEMEDI" demektir: cagiran taraf
    fail-closed davranir ve kalemi hicbir yone TASIMAZ.
    """
    canli = tuple(m for m in (canli_motorlar or ()) if m)
    if not canli:
        return None
    basamaklar = []
    for sira, motor in enumerate(canli):
        tavan = ISCI_TAVANLARI[sira] if sira < len(ISCI_TAVANLARI) else 1
        basamaklar.append({"ad": motor, "tur": "ISCI", "tavan": tavan})
    for ad, tur, tavan in INSAN_BASAMAKLARI:
        basamaklar.append({"ad": ad, "tur": tur, "tavan": tavan})
    return tuple(basamaklar)


def basamak_bul(basamaklar, ad):
    for sira, basamak in enumerate(basamaklar or ()):
        if basamak["ad"] == ad:
            return sira, basamak
    return -1, None


def isci_basamaklari(basamaklar):
    return tuple(b["ad"] for b in (basamaklar or ()) if b["tur"] == "ISCI")


# ===========================================================================
# hal cozumu (dort hal)
# ===========================================================================

def kapi_reddi_sahibi(cikti):
    """Metinde bir KAPI reddi izi varsa o kapinin sahibini doner, yoksa None."""
    metin = cikti or ""
    for desen, sahip in _KAPI_REDDI:
        if desen.search(metin):
            return sahip
    return None


def hal_coz(rc, cikti, kota_kontrolu=None, varsayilan=HAL_YETENEK, zorla=None):
    """Bir dusmeyi DORT HAL'den birine sokar. rc=0 -> None (dusme YOK).

    Sira ONEMLI ve gerekcesi var:
      1) KAPI_REDDI  — tur HIC BASLAMADI; kota da tuketilmedi, sure de dolmadi.
      2) BITMEYEN_TUR— tur BASLADI ama bitmedi (B7).
      3) KOTA        — motor reddetti (429 / usage limit / karantina).
      4) varsayilan  — 🔴 FAIL-CLOSED: siniflandiramadigimiz dusme YETENEK
         sayilir, cunku YETENEK sayaci ARTIRIR. Bilinmeyeni "kota" saymak
         kalemi sonsuz dongude tutardi.

    `zorla`: cagri yerinin YAPISAL bilgisi metinden ustundur (or. kabul komutu
    C4 kapisinca REDDEDILDI -> komut hic kosmadi, bu bir ARAC KUSURUDUR).
    `kota_kontrolu`: `nobet-kapi.kota_reddi_mi` gecirilir. IKINCI bir kota
    deseni listesi BURADA TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]); gecirilmezse
    KOTA kolu OLCULEMEZ ve karar varsayilana duser (fail-closed).
    """
    if rc == 0:
        return None
    if zorla is not None:
        if zorla not in DORT_HAL:
            raise ValueError("bilinmeyen hal: %r" % (zorla,))
        return zorla
    metin = cikti or ""
    if kapi_reddi_sahibi(metin):
        return HAL_KAPI_REDDI
    if SURE_TAVANI_JETONU in metin:
        return HAL_BITMEYEN_TUR
    if kota_kontrolu is not None and kota_kontrolu(metin, rc if rc is not None else 1):
        return HAL_KOTA
    return varsayilan


# ===========================================================================
# kalem kaydi — sayac TURETILIR, saklanmaz
# ===========================================================================

DEVIR_HALI = "DEVIR"    # K257 ONCESI `dagitim_sayisi`'ndan TURETILEN deneme


def _basamak_ilerlet(basamaklar, sira, basamakta):
    """Bir basamakta tavan doldu mu? Doldu ise SONRAKI basamaga gecer."""
    b = basamaklar[sira]
    if b["tavan"] is not None and basamakta >= b["tavan"] \
            and sira + 1 < len(basamaklar):
        return sira + 1, 0
    return sira, basamakta


def merdiven_tohumla(kayit, basamaklar, damga):
    """🔴 (a) ESKI kayitlarin GECMISI SILINMEZ. Doner: (denemeler, basamak).

    K257 oncesinde tek sayac `dagitim_sayisi` idi. Merdiven kaydi olmayan bir
    kaleme SIFIRDAN baslamak, K257(a)'nin tam yasakladigi seydir: kalem her
    kat degisiminde gecmisini kaybeder ve merdiven sonsuz donguye doner.
    O yuzden eski sayi kadar DEVIR denemesi TURETILIR ve kalem, o denemelerin
    goturdugu basamaga KONUR. Tohumlama BIR KEZ olur (merdiven kaydi dogunca).
    """
    kayit = kayit or {}
    try:
        eski = int(kayit.get("dagitim_sayisi") or 0)
    except (TypeError, ValueError):
        eski = 0
    if eski <= 0:
        return [], basamaklar[0]["ad"]
    tohum = []
    sira, basamakta = 0, 0
    for _ in range(eski):
        tohum.append({
            "damga": kayit.get("damga") or damga,
            "basamak": basamaklar[sira]["ad"],
            "motor": kayit.get("motor") or basamaklar[sira]["ad"],
            "hal": DEVIR_HALI,
            "etkin_hal": HAL_YETENEK,
            "yon": YON_YUKARI,
            "sayilir": True,
            "rc": None,
            "atif": kayit.get("rapor_yolu"),
        })
        basamakta += 1
        sira, basamakta = _basamak_ilerlet(basamaklar, sira, basamakta)
    return tohum, basamaklar[sira]["ad"]


def merdiven_kaydi(kayit):
    return (kayit or {}).get("merdiven") or {}


def denemeler(kayit):
    return list(merdiven_kaydi(kayit).get("denemeler") or ())


def sayac(kayit):
    """(a) MERDIVEN SAYACI — `denemeler` listesinden TURETILIR.

    Ayri bir tamsayi alani YOKTUR; dolayisiyla "yeni kat sifirdan baslatir"
    kusuru bu modulde YAZILAMAZ. Yalniz `sayilir=True` denemeler sayilir
    (KOTA / KAPI_REDDI / BITMEYEN_TUR sayilmaz).
    """
    return sum(1 for d in denemeler(kayit) if d.get("sayilir"))


def basamak_sayaci(kayit, basamak_adi):
    return sum(1 for d in denemeler(kayit)
               if d.get("sayilir") and d.get("basamak") == basamak_adi)


def kova_sayaci(kayit, hal):
    return sum(1 for d in denemeler(kayit) if d.get("hal") == hal)


def basamak(kayit, basamaklar=None):
    """Kalemin BUGUNKU basamagi; kayit yoksa merdivenin ILK basamagi."""
    ad = merdiven_kaydi(kayit).get("basamak")
    if ad:
        return ad
    return basamaklar[0]["ad"] if basamaklar else None


def _kota_serisi_basamaklari(kayitlar):
    """Sondaki KESINTISIZ KOTA serisinde denenmis basamaklarin kumesi."""
    seri = set()
    for deneme in reversed(kayitlar):
        if deneme.get("hal") != HAL_KOTA:
            break
        seri.add(deneme.get("basamak"))
    return seri


# ===========================================================================
# ana gecis
# ===========================================================================

def merdiven_ilerlet(kayit, hal, motor=None, damga=None, canli_motorlar=None,
                     rc=None, atif=None, basamaklar=None, metin=None):
    """Bir dusmeyi merdivende isler. Doner: karar sozlugu ya da None.

    None -> merdiven KURULAMADI (canli kume bos): kalem HICBIR yone tasinmaz,
    cagiran taraf `MERDIVEN=OLCULEMEDI` yazar (fail-closed).

    `kayit` YERINDE guncellenir (geri-iz sozlugu).
    """
    if hal not in DORT_HAL:
        raise ValueError("bilinmeyen hal: %r" % (hal,))
    basamaklar = basamaklar or merdiven_kur(canli_motorlar)
    if not basamaklar:
        return None
    damga = damga or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    kayit = kayit if kayit is not None else {}
    merdiven = kayit.get("merdiven")
    if not merdiven:
        # 🔴 (a) TOHUMLAMA: K257 oncesi kaydin gecmisi TASINIR, silinmez.
        tohum, tohum_basamak = merdiven_tohumla(kayit, basamaklar, damga)
        merdiven = kayit["merdiven"] = {
            "denemeler": tohum,
            "basamak": tohum_basamak,
            "dogus_damgasi": kayit.get("damga") or damga,
        }
        if tohum:
            merdiven["devir"] = {"dagitim_sayisi": len(tohum), "damga": damga}
    merdiven.setdefault("denemeler", [])
    merdiven.setdefault("dogus_damgasi", damga)
    simdiki = merdiven.get("basamak") or basamaklar[0]["ad"]
    sira, basamak_kaydi = basamak_bul(basamaklar, simdiki)
    if basamak_kaydi is None:
        # Basamak adi merdivende YOK (or. emekli motor). Fail-closed: kalem
        # merdivenin ILK basamagina alinir ve bu GORUNUR olur.
        sira, basamak_kaydi = 0, basamaklar[0]
        simdiki = basamak_kaydi["ad"]
        merdiven["basamak"] = simdiki
        merdiven["basamak_gocu"] = damga

    etkin_hal = hal
    yeniden_siniflandi = False
    if hal == HAL_BITMEYEN_TUR:
        onceki = sum(1 for d in merdiven["denemeler"]
                     if d.get("hal") == HAL_BITMEYEN_TUR
                     and d.get("basamak") == simdiki)
        if onceki + 1 > BITMEYEN_TUR_TAVANI:
            etkin_hal = HAL_YETENEK
            yeniden_siniflandi = True

    yon = YON_TABLOSU[etkin_hal]
    sayilir = SAYAC_ARTAR[etkin_hal]
    # Sahip METINDEN okunur (atif bir DOSYA YOLUDUR, kapi metni degildir).
    sahip = kapi_reddi_sahibi(metin) if etkin_hal == HAL_KAPI_REDDI else None

    deneme = {
        "damga": damga,
        "basamak": simdiki,
        "motor": motor or simdiki,
        "hal": hal,                  # ham sinif (gorunur kalir)
        "etkin_hal": etkin_hal,      # yeniden siniflanma sonrasi
        "yon": yon,
        "sayilir": bool(sayilir),
        "rc": rc,
        "atif": atif,
    }
    merdiven["denemeler"].append(deneme)

    yeni_basamak = simdiki
    durum = DURUM_DUSTU
    sebep = etkin_hal

    if yon == YON_YUKARI:
        tavan = basamak_kaydi["tavan"]
        basamakta = basamak_sayaci(kayit, simdiki)
        if tavan is not None and basamakta >= tavan and sira + 1 < len(basamaklar):
            yeni_basamak = basamaklar[sira + 1]["ad"]
            sira, basamak_kaydi = sira + 1, basamaklar[sira + 1]
        durum = (DURUM_DUSTU if basamak_kaydi["tur"] == "ISCI"
                 else DURUM_ESKALASYON)
    elif yon == YON_YANA:
        # (b) KOTA: YANA — sayac ARTMAZ, merdivende YUKARI CIKILMAZ.
        isciler = isci_basamaklari(basamaklar)
        if basamak_kaydi["tur"] != "ISCI":
            # Insan basamaginda KOTA olmaz; yana da yukari da GIDILMEZ.
            durum, sebep = DURUM_ESKALASYON, "YANA_YOK_INSAN_BASAMAGI"
        elif len(isciler) < 2:
            durum, sebep = DURUM_DUSTU, "YANA_YOK_TEK_MOTOR"
        else:
            seri = _kota_serisi_basamaklari(merdiven["denemeler"])
            if seri >= set(isciler):
                # Tum canli motorlar bu seride kotaya carpti: kalem BEKLER,
                # yukari CIKMAZ (kota bir YETENEK kusuru DEGILDIR).
                durum, sebep = DURUM_KOTA_BEKLEMEDE, "TUM_MOTORLAR_KOTADA"
            else:
                yer = isciler.index(simdiki)
                for adim in range(1, len(isciler) + 1):
                    aday = isciler[(yer + adim) % len(isciler)]
                    if aday not in seri:
                        yeni_basamak = aday
                        break
                durum, sebep = DURUM_DUSTU, "YANA_GECILDI"
    elif yon == YON_KOVA:
        # (b) BITMEYEN_TUR: B7'nin kovasi. Ayni tur YENIDEN KURULMAZ ->
        # kalem BU TURDA aday havuzundan cikar, basamak DEGISMEZ.
        durum, sebep = DURUM_BITMEYEN_TUR, "B7_KOVASI"
    else:  # YON_SAHIBINE
        # 🔴 (b) KAPI_REDDI: NE YANA NE YUKARI. Tur hic baslamadi; bu bir
        # ARAC KUSURUDUR ve kapinin SAHIBINE doner. K236 aylarca "motor
        # yetersiz" sanildi cunku bu kol YOKTU.
        durum, sebep = DURUM_ARAC_KUSURU, "SAHIBINE:%s" % (sahip or "bilinmeyen")

    merdiven["basamak"] = yeni_basamak
    merdiven["son_hal"] = hal
    merdiven["son_damga"] = damga
    kayit["durum"] = durum
    # 🔴 `dagitim_sayisi`'na DOKUNULMAZ. O alan "kac kez DAGITILDI"yi sayar;
    # merdiven sayaci ise "kac deneme YUKARI sayildi"yi. Ikisi FARKLI
    # buyukluktur — ayni alana yazmak [[ad-iki-rolde-mutanti-golgeler]]
    # sinifidir ve `kalem_dagit`'in sayimini bir tur ileri kaydiriyordu.
    # Merdiven sayaci yalniz `sayac(kayit)` ile OKUNUR.

    return {
        "hal": hal,
        "etkin_hal": etkin_hal,
        "yeniden_siniflandi": yeniden_siniflandi,
        "yon": yon,
        "sayilir": bool(sayilir),
        "onceki_basamak": simdiki,
        "basamak": yeni_basamak,
        "basamak_turu": basamak_kaydi["tur"],
        "sayac": sayac(kayit),
        "basamakta": basamak_sayaci(kayit, yeni_basamak),
        "durum": durum,
        "sebep": sebep,
        "sahip": sahip,
        "atif": atif,
        "yas_sn": None,
    }


# ===========================================================================
# (d) BaBa basamagi: SAYAC DEGIL SLA
# ===========================================================================

def kalem_yasi_sn(kayit, simdi=None):
    """Kalemin MERDIVENDEKI yasi (dogus damgasindan bu yana, saniye)."""
    dogus = merdiven_kaydi(kayit).get("dogus_damgasi")
    if not dogus:
        return None
    try:
        # 🔴 UTC damgasi: `time.mktime` YEREL saat varsayar, `calendar.timegm`
        # dogru olandir; yerel saatle olculen yas SLA'yi saatlerce kaydirirdi.
        epok = calendar.timegm(time.strptime(dogus, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, TypeError):
        return None
    simdi = time.time() if simdi is None else simdi
    return max(0.0, simdi - epok)


def sla_karari(kayit, simdi=None, sla_sn=SLA_SN, basamaklar=None,
               canli_motorlar=None):
    """(d) BaBa basamagindaki kalem 24 saati asarsa OKAN basamagi.

    🔴 SAYACA DOKUNMAZ: `denemeler` listesine HICBIR sey eklemez. BaBa
    basamagi hukum/teshis katidir, icra kati DEGILDIR; orada "deneme" diye
    bir sey yoktur, yalniz YAS vardir.
    Doner: karar sozlugu ya da None (SLA islemiyor / basamak BaBa degil).
    """
    basamaklar = basamaklar or merdiven_kur(canli_motorlar)
    if not basamaklar:
        return None
    merdiven = merdiven_kaydi(kayit)
    if not merdiven or merdiven.get("basamak") != BASAMAK_BABA:
        return None
    yas = kalem_yasi_sn(kayit, simdi)
    if yas is None:
        return {"basamak": BASAMAK_BABA, "yas_sn": None, "asildi": False,
                "sebep": "YAS_OLCULEMEDI", "sayac": sayac(kayit)}
    if yas <= sla_sn:
        return {"basamak": BASAMAK_BABA, "yas_sn": yas, "asildi": False,
                "sebep": "SLA_ICINDE", "sayac": sayac(kayit)}
    kayit["merdiven"]["basamak"] = BASAMAK_OKAN
    kayit["merdiven"]["sla_gocu"] = {"yas_sn": int(yas), "sla_sn": sla_sn}
    kayit["durum"] = DURUM_ESKALASYON
    return {"basamak": BASAMAK_OKAN, "yas_sn": yas, "asildi": True,
            "sebep": "SLA_ASILDI", "sayac": sayac(kayit)}


# ===========================================================================
# raporlama — (c) yukari cikan is OLCULMUSU de goturur
# ===========================================================================

def merdiven_satiri(kalem_id, karar):
    """Turun logunda GORUNEN tek satir (tuketici desen kurabilsin)."""
    if karar is None:
        return "MERDIVEN kalem=%s HUKUM=OLCULEMEDI sebep=canli_motor_kumesi_bos" \
            % kalem_id
    return ("MERDIVEN kalem=%s HAL=%s YON=%s SAYILIR=%d SAYAC=%d "
            "BASAMAK=%s->%s DURUM=%s SEBEP=%s") % (
        kalem_id, karar["hal"], karar["yon"], int(karar["sayilir"]),
        karar["sayac"], karar["onceki_basamak"], karar["basamak"],
        karar["durum"], karar["sebep"])


def olculmus_ozet(kayit, adet=3):
    """(c) Ust kata giden kalemin YANINDA giden olcum: son denemeler.

    "Hangi kat · hangi hata sinifi · hangi cikti" — ust kat sifirdan olcmesin.
    """
    son = denemeler(kayit)[-adet:]
    if not son:
        return "OLCUM=YOK"
    parcalar = []
    for deneme in son:
        parcalar.append("%s@%s/%s%s" % (
            deneme.get("hal") or "-", deneme.get("basamak") or "-",
            deneme.get("damga") or "-",
            (" atif=" + deneme["atif"]) if deneme.get("atif") else ""))
    return "OLCUM=" + " | ".join(parcalar)


def eskalasyon_satiri(kalem_id, kayit):
    """(c) Eskalasyon satiri OLCUMU de tasir."""
    merdiven = merdiven_kaydi(kayit)
    return "ESKALASYON=%s kalem=%s SAYAC=%d %s" % (
        merdiven.get("basamak") or "-", kalem_id, sayac(kayit),
        olculmus_ozet(kayit))


def dagitilmaz_mi(kayit):
    """Merdiven hukmuyle bu turda dagitilmayacak kalemler."""
    return (kayit or {}).get("durum") in DAGITILMAZ_DURUMLAR
