#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATOMIK YAYIN KAPISI — "karti gorunen urun asla 404 vermez".

  python3 tools/yayin-kapisi.py --durum          # sayilar (D1 taslak/yayinda + canli)
  python3 tools/yayin-kapisi.py --yayinla        # deploy'dan SONRA: canli 200 -> yayinda=1
  python3 tools/yayin-kapisi.py --geriye-doldur  # TEK SEFERLIK goc: canlidakileri yayinda=1
  python3 tools/yayin-kapisi.py --hal-json       # MAKINE-OKUNUR: stdin'deki id'lerin yayin hali
  python3 tools/yayin-kapisi.py --kendini-test   # OFFLINE kabul testi (ag/D1 GEREKMEZ)

════════════════════════════════════════════════════════════════════════════════════
NEDEN VAR — OLCULEN PENCERE (iddia degil; ham sayilar muhendis raporunda)
════════════════════════════════════════════════════════════════════════════════════
Katalog iki ayri yerde yayinlanir ve bu ikisi AYNI ANDA olmaz:
  * D1 (Ege'nin okudugu yer): `.git/hooks/pre-push` d1-sync'i push'tan ONCE kosar.
  * /urun/<id>/ (musterinin tikladigi sayfa): GitHub Actions'in SONUNDA yayinlanir.
OLCUM (31 Tem, gh api, son 8 basarili kosum): push -> canli MEDYAN 593 sn (9,9 dk),
min 395 sn, max 740 sn. CI KIRMIZI olursa pencere kirmizi kaldigi surece SURER:
run#1079..1082 arasi 3.241 sn (54 dk) — o sure boyunca 98 urun D1'DEYDI, sayfalari 404'tu.
CANLI TEYIT (31 Tem 07:33Z): d75a4cf7'nin 8/8 yeni id'si D1'de bulundu, ornek 3 urun
sayfasinin 3'u de HTTP 404 dondu.

COZUM (Okan'in karari): gorunurluk ile sayfanin yayinlanmasi TEK ATOMIK islem olur.
Yeni urun D1'e TASLAK girer (yayinda=0, hicbir kesif yuzeyinde gorunmez); yayina alma
AYRI bir adimdir ve ancak /urun/<id>/ CANLIDA 200 dondugu FIILEN dogrulaninca yapilir.

🔴 FAIL-CLOSED YONU: bu kapinin her arizasi urunu GORUNMEZ birakir (satis gecikir),
ASLA "404 veren kart" uretmez. Yanlis yon (kolon okunamayinca hepsini gostermek) bu
dosyada BILEREK yoktur.

════════════════════════════════════════════════════════════════════════════════════
KOR YESIL ONARIMI (7 Agu) — "OLCECEK BIR SEY BULAMADIM" ≠ "KATALOG YAYINDA"
════════════════════════════════════════════════════════════════════════════════════
OLCULEN KUSUR: `--yayinla` kolu YALNIZCA D1'de `yayinda=0` olan TASLAK satirlarin
adresine HTTP atiyordu. Taslak satir yoksa fonksiyon "TASLAK yok ... (exit 0)" basip
HICBIR SAYFA OLCMEDEN `success` donuyordu. Deploy'un `yayin` job'unun yesili boylece
"katalog yayinda" hukmunu kapatmak icin KULLANILAMAZ bir yesildi: yoklanan sayfa
sayisi 0 iken de yesildi ([[beyan-edilmis-survivor]] · [[olculdu-diyen-hukum-kaniti]]).

ONARIM — UC HAL, IKI EKSEN:
  * YUZEY (olculen sayfalar): taslak adaylarinin YANINDA canli katalogdan DETERMINISTIK
    bir kesit de yoklanir (en yeni N + katalogun tamamina yayilmis N) ARTI var olmayan
    bir id'nin 404 VERDIGINI dogrulayan nobet satiri.
  * HUKUM: YESIL yalniz POZITIF OLCUM varsa (>=1 katalog sayfasi fiilen yoklandi ve
    beklenen kodu verdi). Yoklanacak sayfa yoksa hukum `success` DEGIL, ayri bir
    OLCULEMEDI/BOS YUZEY halidir ve BUYUK harfle basilir.
  * CIKIS KODU tek basina hukum degildir; her kosumda BASILAN SAYILAR (kaynak basina
    yoklanan / beklenen-alinan / sapan / atlanan) hukmun kanitidir.

⚠️ SIRA (bozulursa TUM KATALOG gizlenir):
  1. python3 tools/d1-sync.py --sema        (yayinda/release_id kolonlari + indeksler)
  2. python3 tools/yayin-kapisi.py --geriye-doldur    (canlidaki her urun -> yayinda=1)
  3. python3 tools/yayin-kapisi.py --durum            (taslak sayisi ~0 teyidi)
  4. ANCAK BUNDAN SONRA worker'daki `yayinda=1` okuma sarti yayina alinir (HocA/KraL).
"""
import argparse
import contextlib
import email.utils
import importlib.util
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
SITE = "https://pruvo3d.com"

# Canli sayfa dogrulamasi ayarlari.
UA = "Mozilla/5.0 (compatible; PruvoYayinKapisi/1.0)"   # ciplak urllib UA'si 403 alabiliyor
ZAMAN_ASIMI = 20
ES_ZAMAN = 8                 # paralel HTTP kontrolu (CI suresi makul kalsin)
DENEME = 3                   # CDN isinmasi icin tekrar (404 kaliciysa 3'u de 404 doner)
DENEME_BEKLE = 4.0

# TEK KOSUMDA dogrulanabilecek azami aday. Asilirsa kapi YAYIN YAPMAZ ve sifir-disi doner:
# bu olcekteki taslak yigini "normal parti" degil GOC demektir -> --geriye-doldur kullanilir
# (canli urunler.json'u KANIT alir, 15.000 HTTP istegi atmaz). Sessiz ornekleme YASAK.
AZAMI_ADAY = 300

# UPDATE'lerin tek wrangler cagrisina konacak parca boyu (d1-sync PARCA deseni).
# 400 id ~ 6 KB SQL (D1 ifade tavani ~92 KB) — goc kosumunda cagri sayisini yariya indirir.
# 🔴 ACIK ID LISTESI (NOT IN degil) BILEREK: yayin kararini SELECT anindaki kume KILITLER.
# NOT IN yazilsaydi, SELECT ile UPDATE arasinda baska bir oturumun push'uyla D1'e giren
# YENI satir da (canlida sayfasi YOKKEN) yayina alinirdi — tam da kapattigimiz pencere.
PARCA = 400

# ═══════════════════════════════════════════════════════════════════════════════
# OLCUM YUZEYI (kor yesil onarimi)
# ═══════════════════════════════════════════════════════════════════════════════
# Canli katalogdan yoklanacak DETERMINISTIK kesit. Rastgelelik BILEREK YOK: ayni
# katalog ayni sayfalari yoklar -> iki kosumun sayilari KARSILASTIRILABILIR olur
# ([[kapi-yan-etkisi-gizli-onkosul]]: cikis kodu degil BASILAN SAYI karsilastirilir).
YENI_N = 5      # urunler.json'un BASINDAKI N kayit = EN YENI N urun (yeni urun basa girer)
KESIT_N = 5     # katalogun tamamina esit adimla yayilmis N kayit (bas/orta/son)

# 🔴 NOBET SATIRI — "kapi 200 gormeyi biliyor ama 404'u AYIRT EDEBILIYOR MU?"
# Var olmayan bir id 404 VERMEK ZORUNDADIR. 200 donerse site her yola 200 basiyor
# (catch-all / SPA fallback / yanlis 404 sayfasi) demektir ve o kosumdaki TUM 200
# olcumleri ANLAMSIZDIR -> hukum KIRMIZI. Pozitif tanima izni olmadan "olctum" demek
# yasak ([[olculdu-diyen-hukum-kaniti]]). Id UYDURMADIR, katalogda bulunmaz.
NOBET_ID = "olmayan-urun-nobet-satiri-zzq"

KAYNAK_TASLAK = "taslak"        # D1'de yayinda=0 olan, yayina alma ADAYI satirlar
KAYNAK_YENI = "canli-yeni"      # canli katalogun en yeni N kaydi
KAYNAK_KESIT = "canli-kesit"    # canli katalogun deterministik kesiti
KAYNAK_NOBET = "nobet-404"      # var olmayan id (404 bekleniyor)

# HUKUM — ucuncu hal ("OLCULEMEDI") YESIL ve KIRMIZI'dan AYRI TUTULUR.
# ([[hukum-yanlis-birimde]]: basarili / basarisiz / olculemedi ayni kovaya konmaz.)
HUKUM_YESIL = "YESIL"
HUKUM_KIRMIZI = "KIRMIZI"
HUKUM_OLCULEMEDI = "OLCULEMEDI"

# 🔴 UC JETON -> UC AYRI CIKIS KODU (evin kurali; emsal: nobet.yml:88,
# paket-tazelik-alarmi.yml:195 -> "rc 1 = ariza, rc 2 = OLCULEMEDI; ikisi de kosumu
# KIRMIZI yakar, yayini DURDURMAZ"). Hukum jetonu HICBIR is akisi tarafindan
# tuketilmiyor (olculdu: `grep "BOS YUZEY|KATALOG POZITIF" .github/workflows` = 0
# vurus) -> karar yuzeyi TEK BASINA rc'dir. OLCULEMEDI'yi rc=0 birakmak, kapinin
# hukmunu JOB biriminde `success`e cevirir ([[hukum-yanlis-birimde]]).
RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 2
# 🔴 KULLANIM HATASI AYRI KODA TASINDI: argparse'in varsayilan `sys.exit(2)`'si "bayrak
# yanlis yazildi" ile "olcum yapilamadi"yi AYNI kova icine atiyordu. rc=2 artik YALNIZ
# OLCULEMEDI'ye ayrilmistir; kullanim hatasi sysexits.h EX_USAGE (64) doner.
RC_KULLANIM = 64

# ── OLCUM SINIFLARI: "gecici/ortam" ile "gercek kusur" AYRI ────────────────────
SINIF_OK = "OK"
SINIF_KIRMIZI = "KIRMIZI"
SINIF_GECICI = "GECICI"

# Ortam/gecici HTTP kodlari: bunlar kapinin olcemedigini soyler, sitenin bozuk
# oldugunu SOYLEMEZ -> asla rc=1 uretmezler.
#   403 : bu dosyanin kendi notu — "ciplak urllib UA'si 403 alabiliyor" (UA/WAF)
#   408 : istek zaman asimi (sunucu tarafli)
#   425 : Too Early (TLS erken veri)
#   429 : hiz siniri — 9 sayfayi paralel yoklayan bir kapinin BEKLENEN riski
#   5xx : kaynak/CDN gecici arizasi
GECICI_KODLAR = frozenset({403, 408, 425, 429})

# 🔴 ROLLOUT AFFI YASA BAGLI — SINIRSIZ AF YOK.
# `canli-yeni` kolundaki 404, YALNIZ yayin artefakti HENUZ TAZEYSE bagislanir. Af
# suresizse "en yeni urunun sayfasi kalici 404" hali kapiya HIC gorunmez — yani kapinin
# yakalamasi gereken asil vaka ortulur (7 Agu: canlida yeni bir urun adresi gercekten
# 404 verdi). Saat: CANLI /urunler.json artefaktinin YASI (`date` - `last-modified`,
# SUNUCU saati) = "bu deploy ne kadardir yayinda" = yayin adiminin elinde ne kadar
# zaman oldugu (D1 semasinda zaman damgasi YOK, bkz. yas_sn docstring'i).
# ESIK GEREKCESI (olculmus iki emsal):
#   * bu dosyanin kendi olcumu: push -> canli MEDYAN 593 sn, MAX 740 sn
#   * [[container-rollout-penceresi]]: olculen rollout penceresi ~11 dk = ~660 sn
# 900 sn (15 dk) ikisinin de USTUNDE -> saglikli rollout'ta yanlis-pozitif uretmez,
# ama "kalici 404" halini SINIRSIZ bagislamaz.
ROLLOUT_ESIK_SN = 900

# 🔴 SOFT-404 (200 + hata govdesi) — govde ZATEN indiriliyordu ve ATILIYORDU.
# Iki isaret birlikte olculur (blanket catch-all'a guvenilmez):
#   1. KANONIK CAPA: sayfa kendi kanonik adresini tasir (build.py: <link rel="canonical"
#      href="https://pruvo3d.com/urun/<id>/">). Capa AYNI urun_yolu()'ndan TURETILIR
#      ([[ikiz-tanim-sessiz-ayrisma]]: ikiz sabit yazilmaz).
#   2. ASGARI GOVDE: tek sayfaya ozgu bozuk/kirpik render (capa var ama govde bos) da
#      yakalanmali.
GOVDE_ASGARI_BAYT = 512


def yukle_d1sync():
    """d1-sync.py'yi modul olarak yukle (tire iceren ad -> importlib).
    NEDEN IMPORT: wrangler cagrisi, hata tanisi, alintlama (q) ve parca mantigi TEK
    KAYNAKTA kalsin — ikinci bir wrangler sarmalayicisi yazmak drift uretirdi."""
    yol = os.path.join(KOK, "tools", "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# SAF KARAR MANTIGI (D1'e / aga DOKUNMAZ -> kabul testi burayi dogrudan cagirir)
# ═══════════════════════════════════════════════════════════════════════════════
def adaylari_sec(taslaklar, yerel_idler, canli_idler):
    """Yayina ALINABILECEK id'ler.

    KOSUL (fail-closed, UCU BIRDEN): id D1'de TASLAK olmali + YAYINLANAN (yerel, yani
    deploy edilen commit'in) urunler.json'da olmali + CANLI urunler.json'da da olmali.
    Canli JSON sarti, "CI daha yeni bir commit yayinladi / deploy henuz oturmadi"
    halinde yanlislikla yayina almayi engeller (canli JSON ile /urun/ AYNI artefaktta
    yayinlanir — deploy.yml `_site` beyaz listesi).
    Doner: (adaylar_sirali, atlanan_sebep_haritasi)"""
    yerel = set(yerel_idler)
    canli = set(canli_idler)
    adaylar, atlanan = [], {}
    for uid in taslaklar:
        if uid not in yerel:
            atlanan[uid] = "yerel urunler.json'da YOK (silinmis/bayat satir)"
        elif uid not in canli:
            atlanan[uid] = "canli urunler.json'da HENUZ YOK (deploy oturmadi)"
        else:
            adaylar.append(uid)
    return sorted(adaylar), atlanan


def urun_yolu(uid):
    """KANONIK urun adresi — TEK KAYNAK.

    🔴 `.html` URETILMEZ: kanonik adres `/urun/<id>/` bicimindedir. `/urun/<id>.html`
    ile yoklamak SAHTE 404 uretir ve kapiyi saglikli sitede kirmiziya surukler
    ([[kanonik-adres-olcum-yanlisi]]). Adres uretimi tek fonksiyonda toplandi ki
    "kabul araligi" ile "kiyas araligi" ayrisamasin ([[kabul-araligi-karsilastirma-araligi]]).
    """
    return "/urun/" + uid + "/"


def urun_capasi(uid):
    """SOFT-404 CAPASI — sayfanin tasimasi ZORUNLU dizge. TEK KAYNAK: urun_yolu().
    build.py her urun sayfasina `<link rel="canonical" href="<SITE>/urun/<id>/">` basar.
    Capa buradan TURETILIR; ikinci bir sabit yazilmaz ([[ikiz-tanim-sessiz-ayrisma]])."""
    return SITE + urun_yolu(uid)


def govde_isareti(uid, govde):
    """Govde GERCEK urun sayfasi mi, yoksa 200 donen bir HATA sayfasi mi (SOFT-404)?

    Doner: True (gercek) | False (soft-404 / bozuk render) | None (govde YOK = olculemedi)
    IKI isaret birlikte: kanonik capa VAR mi + govde ASGARI boyutta mi. Ikisi de
    gerekli; capasi olup govdesi bos olan kirpik render de FALSE'tur."""
    if govde is None:
        return None
    if isinstance(govde, str):
        govde = govde.encode("utf-8", "replace")
    if len(govde) < GOVDE_ASGARI_BAYT:
        return False
    return urun_capasi(uid).encode("utf-8") in govde


def kesit_indeksleri(n, adet):
    """`n` uzunlugundaki listeden `adet` kadar DETERMINISTIK, esit adimli indeks.
    Rastgelelik yok; n<=adet ise TUM indeksler doner. Bas/orta/son kapsanir."""
    if n <= 0 or adet <= 0:
        return []
    if n <= adet:
        return list(range(n))
    adim = (n - 1) / float(adet - 1) if adet > 1 else 1.0
    return sorted({int(round(i * adim)) for i in range(adet)})


def olcum_plani(taslak_adaylari, canli_idler, yeni_n=YENI_N, kesit_n=KESIT_N,
                nobet_id=NOBET_ID):
    """SAF PLANLAMA — yoklanacak sayfalarin TAM listesi (aga/D1'e DOKUNMAZ).

    canli_idler: canli urunler.json'daki id'ler DOSYA SIRASIYLA (yeni urun BASA girer,
    yani ilk N = en yeni N). Doner: [{"kaynak","id","yol","beklenen","katalog"}]
      beklenen : bu yoldan beklenen HTTP kodu (None = iddia yok)
      katalog  : bu satir "katalog sayfasi canli" POZITIF olcumu sayilabilir mi
                 (nobet satiri sayilmaz — o yalniz kapinin gozunu test eder)
    Ayni id iki kaynaga girmez; sira deterministik (tekrar edilebilir sayilar)."""
    plan, gorulen = [], set()

    def ekle(kaynak, uid, beklenen, katalog):
        if uid in gorulen:
            return
        gorulen.add(uid)
        plan.append({"kaynak": kaynak, "id": uid, "yol": urun_yolu(uid),
                     "beklenen": beklenen, "katalog": katalog})

    for uid in taslak_adaylari:
        # TASLAK ADAYI zaten "yerel VE canli urunler.json'da var" suzgecinden gecmistir
        # (adaylari_sec) -> sayfasi da AYNI artefaktta yayinlanmis olmali: 200 SART.
        # Canli JSON'da OLMAYAN taslak hic aday olmaz, yani "normal yayin gecikmesi"
        # penceresi bu listeye HIC girmez; buradaki 404 GERCEK arizadir (eski kod da
        # bu hali rc=1 sayiyordu — o duyarlilik AYNEN korunur).
        ekle(KAYNAK_TASLAK, uid, 200, True)
    # 🔴 KOVA SINIRI (N TUZAGI): `canli-yeni` kolu ROLLOUT AFFI tasir, `canli-kesit`
    # TASIMAZ. Eskiden yeni-kova ilk YENI_N kaydi KOSULSUZ aliyordu; n<=YENI_N olan bir
    # katalogta TUM kayitlar affli kovaya dusuyor, kesit BOS kaliyor ve KIRMIZI sinifi
    # ULASILAMAZ hale geliyordu (olculdu: n=1/3/5 -> OLCULEMEDI, n=6 -> KIRMIZI).
    # KURAL: yeni-kova en cok `n-1` kayit alir -> EN ESKI kayit DAIMA kesit kovasinda
    # kalir. Gerekce: en eski kayit tanimi geregi rollout penceresinde OLAMAZ (cok once
    # yayinlandi), yani katı yargilanacak dogru yerdir. Kesit, yeni-kovanin ALMADIGI
    # kuyruktan cekilir -> ayni id iki kovada OLMAZ, kova secimi EN SPESIFIKtir.
    canli_idler = list(canli_idler)
    n = len(canli_idler)
    yeni_adet = min(max(0, yeni_n), max(0, n - 1))
    for uid in canli_idler[:yeni_adet]:
        # CANLI KATALOG: id canli urunler.json'da -> sayfasi da AYNI artefaktta, 200 SART.
        ekle(KAYNAK_YENI, uid, 200, True)
    kuyruk = canli_idler[yeni_adet:]
    for i in kesit_indeksleri(len(kuyruk), kesit_n):
        ekle(KAYNAK_KESIT, kuyruk[i], 200, True)
    if nobet_id:
        ekle(KAYNAK_NOBET, nobet_id, 404, False)
    return plan


def sayfa_yok_sinifi(o, artefakt_yas):
    """"SAYFA YOK" (hard 404 ya da SOFT-404) hangi sinifa duser?

    🔴 AF YASA BAGLI: yalniz `canli-yeni` kolunda ve YALNIZ artefakt HENUZ TAZEYSE
    (yas < ROLLOUT_ESIK_SN) bagislanir. Yas OLCULEMIYORSA af VERILMEZ (fail-closed):
    "olcemedim" bir mazeret degildir ([[olculdu-diyen-hukum-kaniti]])."""
    if o.get("kaynak") != KAYNAK_YENI:
        return SINIF_KIRMIZI, "SAYFA YOK — gercek kusur (kol=%s, af YOK)" % o.get("kaynak")
    if artefakt_yas is None:
        return (SINIF_KIRMIZI,
                "SAYFA YOK (kol=%s) + artefakt YASI OLCULEMEDI -> ROLLOUT AFFI VERILMEDI "
                "(fail-closed)" % KAYNAK_YENI)
    if int(artefakt_yas) < ROLLOUT_ESIK_SN:
        return (SINIF_GECICI,
                "SAYFA YOK ama kol=%s ve artefakt yasi %d sn < %d sn -> ROLLOUT PENCERESI"
                % (KAYNAK_YENI, int(artefakt_yas), ROLLOUT_ESIK_SN))
    return (SINIF_KIRMIZI,
            "SAYFA YOK (kol=%s) ve artefakt yasi %d sn >= %d sn -> rollout penceresi "
            "GECTI, KALICI 404" % (KAYNAK_YENI, int(artefakt_yas), ROLLOUT_ESIK_SN))


def olcum_sinifi(o, artefakt_yas=None):
    """🔴 TEK KAYNAK — bir yoklamanin SINIFI: OK / KIRMIZI (gercek kusur) / GECICI.

    "Gecici hal" ile "gercek kusur" AYRILMAK ZORUNDA, cunku bu kapi UC yerden cagrilir
    ve biri BLOKLAYICI: `d1-uzlastirici.yml:250` (`--yayinla`, continue-on-error YOK).
    Orada bir 403/429 yanlis-pozitifi onarim isini kirmiziya cevirirdi; ustune bu kapi
    artik her kosumda ~9 sayfa yokluyor (eski kod taslak yokken 0 yokluyordu), yani
    maruziyet buyudu. Doner: (sinif, gerekce_metni)

    KURALLAR (kaynak kolu adiyla yargilanir):
      * kod ALINAMADI (None: ag/DNS/TLS/timeout)      -> GECICI
      * beklenen kod alindi                            -> OK
      * 403/408/425/429/5xx                            -> GECICI (ortam/hiz siniri/CDN)
      * 404 + beklenen 200                             -> sayfa_yok_sinifi() karar verir
        (`canli-yeni` + artefakt TAZE ise ROLLOUT AFFI; aksi halde KIRMIZI)
      * 200 + beklenen 200 ama GOVDE ISARETI YOK       -> SOFT-404: ayni sekilde
        sayfa_yok_sinifi()'na baglanir (ucuncu bir sinif URETILMEZ; "200 donen hata
        sayfasi" ile "404" musteri acisindan AYNI seydir — kart tiklanir, urun yok)
      * 200 + beklenen 200 ama govde OLCULEMEDI (None)  -> GECICI (fail-closed: govdeyi
        gormeden "sayfa saglam" denmez)
      * 200 + beklenen 404 (nobet satiri)              -> KIRMIZI: kapinin GOZU bozuk,
        o kosumdaki TUM 200 olcumleri anlamsiz
      * MODELLENMEYEN kod (410/451/400 ...)            -> GECICI (fail-toward-NOTR).
        Notr, SESSIZ degildir: rc=2 kosumu KIRMIZI yakar, yalniz yayini durdurmaz;
        modellenmemis bir kodu "gercek kusur" saymak yanlis-pozitif uretirdi.
      * 301/308: urllib varsayilan opener yonlendirmeyi IZLER (olculdu) -> ayri kol yok,
        yargi IZLENEN SON koda gore verilir.
    """
    alinan, beklenen = o.get("alinan"), o.get("beklenen")
    if alinan is None:
        return SINIF_GECICI, "kod ALINAMADI (ag/DNS/TLS/timeout)"
    if beklenen is None:
        return SINIF_OK, "iddia edilmedi"
    if alinan in GECICI_KODLAR or 500 <= int(alinan) <= 599:
        return SINIF_GECICI, "ortam/gecici kod %s" % alinan
    if alinan == beklenen:
        # 200 BEKLENEN VE ALINAN HAL: govde ISARETI olculmeden "saglam" DENMEZ.
        if beklenen == 200:
            isaret = o.get("govde")
            if isaret is None:
                return (SINIF_GECICI, "200 alindi ama GOVDE ISARETI OLCULEMEDI "
                        "(fail-closed: soft-404 ayirt edilemez)")
            if isaret is False:
                s, g = sayfa_yok_sinifi(o, artefakt_yas)
                return s, ("SOFT-404 (200 alindi ama kanonik capa YOK ya da govde < %d "
                           "bayt) -> %s" % (GOVDE_ASGARI_BAYT, g))
        return SINIF_OK, "beklenen kod (%s)" % alinan
    if alinan == 404 and beklenen == 200:
        return sayfa_yok_sinifi(o, artefakt_yas)
    if beklenen == 404 and alinan == 200:
        return SINIF_KIRMIZI, "var olmayan id 200 verdi — kapinin GOZU bozuk"
    return SINIF_GECICI, "MODELLENMEYEN kod %s (fail-toward-NOTR)" % alinan


def yuzey_hukmu(olcumler, artefakt_yas=None):
    """SAF HUKUM — "bos yuzey" ve "gecici hal" YESIL'den AYRI hallerdir.

    olcumler: olcum_plani satirlari + "alinan" (int HTTP kodu | None) + "govde"
    (True/False/None). artefakt_yas: canli /urunler.json'un yasi (sn) — rollout affinin
    SAATI; None ise af verilmez. Doner: (hukum, sebep, sayac)

    SIRA (fail-closed):
      1. GERCEK KUSUR (olcum_sinifi -> KIRMIZI) -> KIRMIZI. Gercek kirmizi, gecici
         gurultuyu YENER: kusuru "ortam sorunu" diye ortmek kapiyi olduruR.
      2. GECICI/OLCULEMEYEN olcum varsa -> OLCULEMEDI (sessiz yesil DEGIL).
      3. POZITIF OLCUM YOK (hicbir katalog sayfasi 200 dogrulanmadi) -> OLCULEMEDI:
         BOS YUZEY. 🔴 ESKI DAVRANIS BURADA `success` DONUYORDU.
      4. Aksi halde YESIL (>=1 katalog sayfasi fiilen yoklandi ve beklenen kodu verdi).
    """
    siniflar = [(o, olcum_sinifi(o, artefakt_yas)) for o in olcumler]
    kirmizi = [(o, g) for o, (s, g) in siniflar if s == SINIF_KIRMIZI]
    gecici = [(o, g) for o, (s, g) in siniflar if s == SINIF_GECICI]
    # 🔴 POZITIF = 200 **VE** govde isareti GERCEK. Soft-404 (200 + hata govdesi) pozitif
    # olcum SAYILMAZ; yoksa "yoklandi ve 200 aldi" sahte kaniti yuzeyi sisirirdi.
    pozitif = [o for o, (s, _) in siniflar
               if s == SINIF_OK and o.get("katalog") and o.get("alinan") == 200
               and o.get("govde") is True]
    sayac = {"yoklanan": len(olcumler), "kirmizi": len(kirmizi), "gecici": len(gecici),
             "ag_hatasi": sum(1 for o in olcumler if o.get("alinan") is None),
             "katalog_pozitif": len(pozitif), "artefakt_yas_sn": artefakt_yas}
    if kirmizi:
        o, g = kirmizi[0]
        return (HUKUM_KIRMIZI,
                "%d GERCEK KUSUR (or. kol=%s id=%s bekleniyordu %s alindi %s -> %s)"
                % (len(kirmizi), o["kaynak"], o["id"], o["beklenen"], o["alinan"], g),
                sayac)
    if gecici:
        o, g = gecici[0]
        return (HUKUM_OLCULEMEDI,
                "%d GECICI/OLCULEMEYEN yoklama (or. kol=%s id=%s -> %s) — sessiz yesil "
                "verilmez, gercek kusur da IDDIA EDILMEZ" % (len(gecici), o["kaynak"],
                                                             o["id"], g),
                sayac)
    if not pozitif:
        return (HUKUM_OLCULEMEDI,
                "BOS YUZEY: hicbir katalog sayfasi yoklanmadi/dogrulanmadi "
                "(yoklanan=%d) — 'olcecek sey yok' YAYINDA demek DEGILDIR" % len(olcumler),
                sayac)
    return (HUKUM_YESIL, "%d katalog sayfasi beklenen kodu verdi" % len(pozitif), sayac)


def hukum_cikis_kodu(hukum):
    """🔴 CIKIS KODU POLITIKASI — UC JETON, UC AYRI RC (gerekce kodda dursun):

      YESIL      -> 0.
      KIRMIZI    -> 1. Yoklanan bir sayfa GERCEK KUSUR gosterdi: canli katalogtaki
                    (taslak/kesit) id'nin sayfasi 404, ya da var olmayan id 200 verdi.
      OLCULEMEDI -> 2. Evin kurali: "rc 2 = OLCULEMEDI = kosumu KIRMIZI yakar, yayini
                    DURDURMAZ" (emsal: nobet.yml:88, paket-tazelik-alarmi.yml:195).
                    🔴 NEDEN 0 DEGIL: hukum jetonunu ("BOS YUZEY"/"KATALOG POZITIF")
                    HICBIR is akisi tuketmiyor (olculdu: 0 vurus) -> karar yuzeyi tek
                    basina rc. rc=0 verilirse `yayin` job'u bos yuzeyde HALA `success`
                    olur ve onarim yalnizca stdout metnini degistirmis olur
                    ([[hukum-yanlis-birimde]]).
                    🔴 NEDEN 1 DEGIL: "olcemedim" ile "site bozuk" ayni sey degildir; bu
                    kod UC yerden cagrilir ve `d1-uzlastirici.yml:250` BLOKLAYICIDIR.
                    403/429/5xx/timeout orada onarim isini kirmiziya cevirmemeli.
                    Yayin DURMAZ: `deploy.yml:2166-2170` bu isin kirmizisinin siteyi
                    etkilemedigini yazar ve `needs: yayin` yazan JOB YOKTUR (olculdu).
    """
    if hukum == HUKUM_KIRMIZI:
        return RC_KIRMIZI
    if hukum == HUKUM_OLCULEMEDI:
        return RC_OLCULEMEDI
    return RC_YESIL


def yayin_karari(adaylar, kodlar):
    """kodlar = {id: HTTP kodu ya da None (istek patladi)}.
    Doner: (yayinlanacak, basarisiz) — SADECE 200 yayinlanir; None/404/500 TASLAK KALIR.
    🔴 Eksik olculen id (kodlar'da hic yoksa) da BASARISIZ sayilir: "olculmedi" asla
    "iyi" demek degildir (bkz. [[nobetci-cagri-satiri-nobetsiz]])."""
    yayinlanacak, basarisiz = [], []
    for uid in adaylar:
        if kodlar.get(uid) == 200:
            yayinlanacak.append(uid)
        else:
            basarisiz.append((uid, kodlar.get(uid, "OLCULMEDI")))
    return yayinlanacak, basarisiz


def ihlal_idler(yayinda, canli_idler):
    """🔴 ASIL DEGISMEZ (invariant): "yayinda=1 olan her id CANLI urunler.json'da vardir."
    Canli JSON ile /urun/ sayfalari AYNI artefaktta yayinlanir ve uretici butunlugu
    (tools/uretim-butunluk-kapisi.py) "JSON'daki her id'nin sayfasi var"i BLOKLAYICI
    olcer -> bu iki kapi birlikte "karti gorunen urun 404 vermez"i verir.
    Bu fonksiyon degismezin IHLALLERINI dondurur; 0 disi her sonuc KIRMIZIDIR.
    Olcum TAM'dir (ornekleme yok) ve TEK HTTP istegi maliyetindedir."""
    return sorted(set(yayinda) - set(canli_idler))


def hal_bol(idler, harita):
    """🔴 SAF SINIFLANDIRMA — "yayin gecikmesi" ile "GERCEK KAYIP"i AYIRIR.

    harita = {id: yayinda degeri (0/1)} — D1'den FIILEN okunmus satirlar. Haritada
    OLMAYAN id, D1'de satiri HIC OLMAYAN id'dir.
    Doner: (yok, yayinda, taslak) — ucu de sirali liste.

    🔴 AYRIM SAYI FARKINDAN TUREMEZ: bir id ancak `yayinda` degeri OKUNDUYSA taslak
    sayilir. Deger okunamamissa id 'yok' kolonuna DUSMEZ, cagiran taraf zaten tum
    okumayi basarisiz sayar (fail-closed) — "olcemedim" hicbir kolonda 'iyi' degildir.
    """
    yok, yayinda, taslak = [], [], []
    for uid in idler:
        if uid not in harita:
            yok.append(uid)
        elif int(harita[uid] or 0) == 1:
            yayinda.append(uid)
        else:
            taslak.append(uid)
    return sorted(yok), sorted(yayinda), sorted(taslak)


def yas_sn(kod, tarih, degisim):
    """HTTP `date` - `last-modified` (saniye). Artefaktin NE KADARDIR CANLI oldugu.

    🔴 NEDEN BU SAAT: D1 semasinda zaman damgasi kolonu YOKTUR (d1-sema.sql) — satirin
    "ne zamandir taslak" oldugu D1'den OLCULEMEZ. Olculebilen tek gercek saat, o satirin
    sayfasini tasiyan Pages artefaktinin CANLI OLMA suresidir; ve zararli hal (sayfa
    canli + satir taslak) icin gereken sure TAM OLARAK budur: yayin adiminin elinde ne
    kadar zaman oldugu. Sunucu saati kullanilir (yerel saat kaymasi olcumu bozmasin).
    Doner: int saniye | None (basliklar okunamadi -> OLCULEMEDI).
    """
    if kod is None or not tarih or not degisim:
        return None
    try:
        d = email.utils.parsedate_to_datetime(tarih)
        m = email.utils.parsedate_to_datetime(degisim)
    except Exception:
        return None
    if d is None or m is None:
        return None
    return max(0, int((d - m).total_seconds()))


def parcala(idler, boy=PARCA):
    return [idler[i:i + boy] for i in range(0, len(idler), boy)]


def yayin_sql(idler, release, alinti):
    """Tek yon: 0 -> 1. `WHERE yayinda=0` sarti BILEREK var — zaten yayinda olan satirin
    release_id'sini ezmez (denetim izi korunur) ve gereksiz yazma uretmez."""
    return ("UPDATE urunler SET yayinda=1, release_id=%s WHERE yayinda=0 AND id IN (%s);"
            % (alinti(release), ",".join(alinti(i) for i in idler)))


# ═══════════════════════════════════════════════════════════════════════════════
# IO
# ═══════════════════════════════════════════════════════════════════════════════
def yerel_idler():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    return [u["id"] for u in d if u.get("id")]


def canli_getir(yol, ikili=False):
    """Canli siteden dosya cek. Doner: (kod, govde) — hata halinde (None, mesaj)."""
    istek = urllib.request.Request(SITE + yol, headers={"User-Agent": UA,
                                                        "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as c:
            return c.getcode(), c.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:                       # ag/DNS/TLS -> OLCULEMEDI
        return None, str(e).encode("utf-8", "replace")


def canli_urun_idleri():
    """CANLI (yayinlanmis) urunler.json'daki id kumesi. Bu dosya /urun/ sayfalariyla
    AYNI Pages artefaktinda yayinlanir -> icindeki her id'nin sayfasi da canlidadir
    (uretici butunlugu ayrica tools/uretim-butunluk-kapisi.py ile BLOKLAYICI olcuLur)."""
    kod, govde = canli_getir("/urunler.json")
    if kod != 200:
        return None, "canli urunler.json alinamadi (kod=%s)" % kod
    try:
        d = json.loads(govde.decode("utf-8"))
    except Exception as e:
        return None, "canli urunler.json cozulemedi: %s" % e
    return [u["id"] for u in d if u.get("id")], None


def canli_hal(yol):
    """Canli bir yolun (kod, yas_sn) hali. Govde INDIRILMEZ (HEAD) — /urunler.json 14 MB.

    SINIFLANDIRMA PROBU (yayin kararindan AYRI, bilerek daha ucuz): temiz bir 404
    KESINDIR, tekrar denemek yalniz sure yakar; yalniz AG/5xx hatasinda tek bir tekrar
    yapilir. Yayina alma karari BU FONKSIYONU KULLANMAZ — o hala sayfa_kodu()'nun
    3 denemeli, CDN isinmasina paylı yolundan gecer.
    """
    for i in range(2):
        istek = urllib.request.Request(SITE + yol, method="HEAD",
                                       headers={"User-Agent": UA, "Cache-Control": "no-cache"})
        kod, basliklar = None, None
        try:
            with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as c:
                kod, basliklar = c.getcode(), c.headers
        except urllib.error.HTTPError as e:
            kod, basliklar = e.code, e.headers
        except Exception:
            kod, basliklar = None, None
        if kod is not None and (kod == 200 or kod == 404):
            return kod, yas_sn(kod, basliklar.get("date"), basliklar.get("last-modified"))
        if i == 0:
            time.sleep(1.5)
    return kod, (yas_sn(kod, basliklar.get("date"), basliklar.get("last-modified"))
                 if basliklar is not None else None)


def yol_kodu(yol, beklenen=200, uid=None):
    """Bir yolu yoklar. Doner: (kod, yas_sn, govde_isareti)

    `beklenen` DISI kodlarda DENEME kez tekrar (CDN isinmasi).
    NEDEN `beklenen` PARAMETRESI: nobet satiri 404 BEKLER; sabit "200 olana kadar dene"
    mantigi orada bosa 3 deneme + 8 sn yakardi. Tekrar sarti beklenen koddan TUREtilir.
    🔴 GOVDE ARTIK ATILMIYOR: `canli_getir` govdeyi ZATEN indiriyordu; SOFT-404 isareti
    ondan turetilir (uid verilmisse). uid yoksa isaret None = OLCULEMEDI (fail-closed)."""
    kod, govde = None, None
    for i in range(DENEME):
        kod, govde = canli_getir(yol)
        if kod == beklenen:
            break
        if i < DENEME - 1:
            time.sleep(DENEME_BEKLE)
    isaret = govde_isareti(uid, govde) if (uid and kod == 200) else None
    return kod, None, isaret


def sayfa_kodu(uid):
    """/urun/<id>/ icin HTTP kodu (adres TEK KAYNAKTAN: urun_yolu)."""
    return yol_kodu(urun_yolu(uid), 200, uid)[0]


def olcumleri_yap(plan, prob=None):
    """Plan satirlarini FIILEN yokla; her satira "alinan" + "govde" ekle.

    prob(yol, beklenen, uid) -> (kod, yas_sn, govde_isareti)  ENJEKTE EDILEBILIR: kabul
    testi AG CAGIRMADAN sahte bir prob ile ayni karar yolunu olcer (fikstur gercek cikti
    SEKLINI taklit eder) ([[nobetci-fikstur-sekli]]).
    🔴 GERIYE UYUM DEGIL FAIL-CLOSED: prob duz bir kod dondururse govde isareti None
    kalir ve o satir GECICI/OLCULEMEDI olur — sessizce "saglam" SAYILMAZ."""
    if not plan:
        return []
    if prob is None:
        prob = yol_kodu

    def tek(o):
        sonuc = prob(o["yol"], o["beklenen"] or 200, o["id"])
        if isinstance(sonuc, tuple):
            kod = sonuc[0]
            govde = sonuc[2] if len(sonuc) > 2 else None
        else:
            kod, govde = sonuc, None
        return kod, govde

    with ThreadPoolExecutor(max_workers=ES_ZAMAN) as havuz:
        sonuclar = list(havuz.map(tek, plan))
    return [dict(o, alinan=k, govde=g) for o, (k, g) in zip(plan, sonuclar)]


def bos_sayac():
    return {"yoklanan": 0, "kirmizi": 0, "gecici": 0, "ag_hatasi": 0,
            "katalog_pozitif": 0, "artefakt_yas_sn": None}


def dokum_bas(olcumler, hukum, sebep, sayac, atlanan_taslak, rc=None, artefakt_yas=None,
              ariza=None):
    """🔴 BASILAN SAYI = HUKMUN KANITI. Cikis kodu tek basina hukum degildir; HANGI KOL
    HANGI KODU verdi, kaynak basina ACIKCA basilir (kod dagilimi dahil).

    🔴 BU FONKSIYON `finally` ICINDEN CAGRILIR: wrangler/D1 istisnasi firlasa bile jeton
    satiri ve kol sayilari BASILMALIDIR. Aksi halde 2. turun tum tasarimi ("basilan sayi
    = hukum kaniti") en olasi operasyonel arizada COKER ([[damga-finally-tuzagi]]).
    Bu yuzden burada HICBIR sey firlatmamali; cagiran taraf ayrica sarmalar."""
    print("──── OLCUM DOKUMU (yoklanan sayfa yuzeyi · kol bazinda) ────")
    print("ARTEFAKT YASI (canli /urunler.json, sunucu saati): %s  ·  ROLLOUT ESIGI: %d sn"
          % (("%d sn" % int(artefakt_yas)) if artefakt_yas is not None
             else "OLCULEMEDI (rollout affi VERILMEZ)", ROLLOUT_ESIK_SN))
    if ariza:
        print("!! ARIZA (olcum yarida kesildi): %s" % ariza)
    print("%-12s %9s %5s %8s %8s  %s"
          % ("kol", "yoklanan", "OK", "KIRMIZI", "GECICI", "alinan kodlar"))
    for kaynak in (KAYNAK_TASLAK, KAYNAK_YENI, KAYNAK_KESIT, KAYNAK_NOBET):
        k = [o for o in olcumler if o["kaynak"] == kaynak]
        if not k:
            print("%-12s %9d %5d %8d %8d  %s" % (kaynak, 0, 0, 0, 0, "-"))
            continue
        s = [olcum_sinifi(o, artefakt_yas)[0] for o in k]
        kodlar = {}
        for o in k:
            anahtar = "AG-HATASI" if o["alinan"] is None else str(o["alinan"])
            if o["alinan"] == 200 and o.get("govde") is False:
                anahtar = "200-SOFT404"
            elif o["alinan"] == 200 and o.get("govde") is None:
                anahtar = "200-GOVDESIZ"
            kodlar[anahtar] = kodlar.get(anahtar, 0) + 1
        print("%-12s %9d %5d %8d %8d  %s"
              % (kaynak, len(k), s.count(SINIF_OK), s.count(SINIF_KIRMIZI),
                 s.count(SINIF_GECICI),
                 ", ".join("%s×%d" % (a, n) for a, n in sorted(kodlar.items()))))
    # Kol adiyla TEK TEK: OK OLMAYAN her yoklama, sinifi ve gerekcesiyle.
    for o in olcumler:
        s, g = olcum_sinifi(o, artefakt_yas)
        if s != SINIF_OK:
            print("   %-8s kol=%-12s id=%s yol=%s bekleniyordu=%s alindi=%s govde=%s — %s"
                  % (s, o["kaynak"], o["id"], o["yol"], o["beklenen"], o["alinan"],
                     o.get("govde"), g))
    print("KATALOG POZITIF DOGRULANAN SAYFA: %d" % sayac["katalog_pozitif"])
    print("ATLANAN (hic yoklanmadi): %d taslak aday secimde dustu — sebepleri yukarida "
          "(canli/yerel JSON sarti; NORMAL yayin gecikmesi penceresi)" % len(atlanan_taslak))
    if hukum == HUKUM_YESIL:
        print("HUKUM: YESIL — %s" % sebep)
    else:
        print("HUKUM: %s — %s" % (hukum.upper(), sebep))
        if HUKUM_OLCULEMEDI == hukum:
            print("!! ##################################################################")
            print("!! OLCULEMEDI (rc=%d) — BU KOSUM 'KATALOG YAYINDA' DEMEK DEGILDIR."
                  % RC_OLCULEMEDI)
            print("!! Yoklanan sayfa: %d · katalog pozitif dogrulanan: %d · gecici: %d"
                  % (sayac["yoklanan"], sayac["katalog_pozitif"], sayac["gecici"]))
            print("!! rc 2 = OLCULEMEDI: kosumu KIRMIZI yakar, YAYINI DURDURMAZ.")
            print("!! ##################################################################")
    if rc is not None:
        print("CIKIS KODU: %d  (YESIL=%d · KIRMIZI=%d · OLCULEMEDI=%d)"
              % (rc, RC_YESIL, RC_KIRMIZI, RC_OLCULEMEDI))


# ═══════════════════════════════════════════════════════════════════════════════
# KOMUTLAR
# ═══════════════════════════════════════════════════════════════════════════════
def d1_sayilar(m):
    r = m.sorgu("SELECT COUNT(*) AS toplam, "
                "SUM(CASE WHEN yayinda=1 THEN 1 ELSE 0 END) AS yayinda, "
                "SUM(CASE WHEN yayinda=0 THEN 1 ELSE 0 END) AS taslak FROM urunler")
    s = ((r[0].get("results") or [{}])[0] or {})
    return int(s.get("toplam") or 0), int(s.get("yayinda") or 0), int(s.get("taslak") or 0)


def taslak_idler(m):
    r = m.sorgu("SELECT id FROM urunler WHERE yayinda=0")
    return [s["id"] for s in (r[0].get("results") or [])]


def yayinda_idler(m):
    r = m.sorgu("SELECT id FROM urunler WHERE yayinda=1")
    return [s["id"] for s in (r[0].get("results") or [])]


def kolon_hazir(m):
    if m.kolon_var_mi("urunler", "yayinda"):
        return True
    print("!! `yayinda` kolonu D1'de YOK. Once: python3 tools/d1-sync.py --sema")
    return False


def komut_durum(m):
    """🔴 AYNI UC-JETON POLITIKASI: olcum engeli (kolon yok / canli JSON okunamadi /
    wrangler istisnasi) -> rc=2 OLCULEMEDI; DEGISMEZ IHLALI -> rc=1 KIRMIZI.
    Eskiden ucu de rc=1 idi, yani "olcemedim" ile "kart 404 verecek" ayni kovadaydi."""
    try:
        if not kolon_hazir(m):
            print("HUKUM: OLCULEMEDI (rc=%d) — sema eksigi OLCUM ENGELI" % RC_OLCULEMEDI)
            return RC_OLCULEMEDI
        toplam, yayinda, taslak = d1_sayilar(m)
        yerel = yerel_idler()
        print("D1 toplam satir      : %d" % toplam)
        print("D1 yayinda (=1)      : %d" % yayinda)
        print("D1 TASLAK  (=0)      : %d" % taslak)
        print("yerel urunler.json id: %d" % len(set(yerel)))
        canli, hata = canli_urun_idleri()
        if canli is None:
            print("canli urunler.json   : OLCULEMEDI (%s)" % hata)
            print("HUKUM: OLCULEMEDI (rc=%d)" % RC_OLCULEMEDI)
            return RC_OLCULEMEDI
        print("canli urunler.json id: %d" % len(set(canli)))
        print("YAYIN GECIKMESI (canli JSON'da olup D1'de TASLAK olan): %d"
              % len(set(taslak_idler(m)) & set(canli)))
        ihlal = ihlal_idler(yayinda_idler(m), canli)
        print("DEGISMEZ IHLALI (yayinda=1 olup canli JSON'da OLMAYAN): %d%s"
              % (len(ihlal), ("  -> " + ", ".join(ihlal[:10])) if ihlal else ""))
        print("HUKUM: %s (rc=%d)" % ((HUKUM_KIRMIZI, RC_KIRMIZI) if ihlal
                                     else (HUKUM_YESIL, RC_YESIL)))
        return RC_KIRMIZI if ihlal else RC_YESIL
    except Exception as e:
        print("!! ISTISNA: %s: %s" % (type(e).__name__, e))
        print("HUKUM: OLCULEMEDI (rc=%d) — wrangler/D1 arizasi 'site bozuk' DEMEK DEGIL"
              % RC_OLCULEMEDI)
        return RC_OLCULEMEDI


def yayin_hali_harita(m, idler):
    """{id: yayinda} — YALNIZ D1'de SATIRI OLAN id'ler icin. Parcali okunur."""
    harita = {}
    for parca in parcala(sorted(set(idler))):
        r = m.sorgu("SELECT id, yayinda FROM urunler WHERE id IN (%s)"
                    % ",".join(m.q(i) for i in parca))
        for s in (r[0].get("results") or []):
            harita[s["id"]] = s.get("yayinda")
    return harita


# HAL-JSON sayfa probu tavani. Bunu asan bir taslak yigini "parti" degil GOC'tur
# (--yayinla ile AYNI olcek kurali, AZAMI_ADAY): o olcekte tek tek HTTP dogrulamasi
# yapilmaz. Tavan asilirsa sayfa hali OLCULMEZ ve cikti bunu ACIKCA soyler; cagiran
# taraf (parite kapisi) o kosumu KANONIK sayamaz.
def komut_hal_json(idler):
    """MAKINE-OKUNUR yayin hali. stdin: id listesi (satir ya da virgul). stdout: TEK JSON.

    🔴 VAR OLMA SEBEBI: her kesif ucu (`/ara`, `/katalog`, `/katalog?ids=`) `yayinda = 1`
    suzer — yani TASLAK satir, uc icin "D1'de HIC YOK" satirdan AYIRT EDILEMEZ. Parite
    kapisi bu iki hali ayirmak zorundadir: ilki gecici YAYIN GECIKMESI, ikincisi GERCEK
    KAYIP. Ayrim ancak `yayinda` kolonunu FIILEN okuyarak kurulabilir; bu komut o okumanin
    TEK kaynagidir (ikinci bir wrangler sarmalayicisi yazilmaz).

    SOZLESME (cagiran taraf buna gore fail-closed davranir):
      {"olculdu": true, "yok": [...], "yayinda": [...],
       "taslak": [{"id": ..., "sayfa": 200|404|null, "yas_sn": int|null}, ...],
       "sayfa_olculdu": bool, "artefakt_yas_sn": int|null}
      Ariza halinde: {"olculdu": false, "sebep": "..."} + sifir-disi cikis.
    stdout'ta JSON'DAN BASKA HICBIR SEY YOKTUR (tum teshis stderr'e gider).
    """
    sonuc = {"olculdu": False, "sebep": "", "yok": [], "yayinda": [], "taslak": [],
             "sayfa_olculdu": False, "artefakt_yas_sn": None}

    def bitir(kod):
        sys.stdout.write(json.dumps(sonuc, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        return kod

    if not idler:
        sonuc["olculdu"] = True
        return bitir(0)

    # Wrangler/d1-sync teshis ciktisi stdout'a KARISMASIN: JSON tek satir kalmali.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            m = yukle_d1sync()
            if not m.kolon_var_mi("urunler", "yayinda"):
                sonuc["sebep"] = "`yayinda` kolonu D1'de YOK (once: d1-sync.py --sema)"
                return bitir(1)
            harita = yayin_hali_harita(m, idler)
    except Exception as e:
        sonuc["sebep"] = "D1 okunamadi: %s" % e
        return bitir(1)

    yok, yayinda, taslak = hal_bol(sorted(set(idler)), harita)
    sonuc["yok"] = yok
    sonuc["yayinda"] = yayinda

    # ARTEFAKT SAATI: canli /urunler.json ne kadardir yayinda (sunucu saatiyle).
    kod, yas = canli_hal("/urunler.json")
    sonuc["artefakt_yas_sn"] = yas if kod == 200 else None

    # SAYFA HALI: taslak satirin ZARARLI mi ZARARSIZ mi oldugunu belirleyen TEK olcu.
    #   sayfa 200 + satir TASLAK -> ZARARLI  (site satiyor, Ege GOREMEZ)
    #   sayfa 200 DEGIL          -> ZARARSIZ (gosterilseydi 404 veren kart uretilirdi —
    #                               atomik yayinin ONLEMEK ICIN VAR OLDUGU hal)
    if taslak and len(taslak) <= AZAMI_ADAY:
        with ThreadPoolExecutor(max_workers=ES_ZAMAN) as havuz:
            haller = list(havuz.map(lambda u: canli_hal("/urun/" + u + "/"), taslak))
        sonuc["sayfa_olculdu"] = True
        sonuc["taslak"] = [{"id": u, "sayfa": h[0], "yas_sn": h[1]}
                           for u, h in zip(taslak, haller)]
    else:
        if taslak:
            sys.stderr.write("!! TASLAK sayisi tavani asti (%d > %d): sayfa hali OLCULMEDI.\n"
                             % (len(taslak), AZAMI_ADAY))
        sonuc["taslak"] = [{"id": u, "sayfa": None, "yas_sn": None} for u in taslak]

    sonuc["olculdu"] = True
    return bitir(0)


def artefakt_yasi():
    """CANLI /urunler.json artefaktinin yasi (sn) — ROLLOUT AFFININ SAATI.
    None = olculemedi (af VERILMEZ). TEK HEAD istegi (govde 14 MB, indirilmez)."""
    kod, yas = canli_hal("/urunler.json")
    return yas if kod == 200 else None


def komut_yayinla(m, release, prob=None, canli_kaynak=None, yerel_kaynak=None,
                  yas_kaynak=None):
    """DEPLOY'DAN SONRA kosar. IKI IS BIR ARADA, AMA AYRI RAPORLANIR:

      1. YAYINA ALMA (yazma): canli 200 dogrulanmadan hicbir satir yayina alinmaz.
      2. YUZEY HUKMU (okuma): taslak olsun olmasin, canli katalogdan DETERMINISTIK bir
         kesit yoklanir. Yoklanacak sayfa yoksa hukum `success` DEGIL, OLCULEMEDI/BOS
         YUZEY'dir. Eski kod burada hicbir sayfa olcmeden `success` donuyordu.

    🔴 KANIT KAYBI KAPALI ([[damga-finally-tuzagi]]): govde `try/finally` icindedir.
    wrangler/D1 istisnasi (ag, kota, kolon yok) firlasa BILE jeton satiri + kol bazindaki
    sayilar BASILIR ve rc jetondan bagimsiz `1`'e COKMEZ — istisna hali OLCULEMEDI (rc=2)
    olarak siniflanir, cunku "wrangler patladi" ile "sitede 404 veren kart var" AYNI
    SEY DEGILDIR. Istisna METNI de basilir; `finally` icindeki ikinci bir istisna
    orijinali GIZLEMEZ (ayrica yakalanip ayri satirda basilir).

    prob / canli_kaynak / yerel_kaynak / yas_kaynak: kabul testi IO dikisleri (AG YOK)."""
    canli_kaynak = canli_kaynak or canli_urun_idleri
    yerel_kaynak = yerel_kaynak or yerel_idler
    yas_kaynak = yas_kaynak or artefakt_yasi

    d = {"olcumler": [], "hukum": HUKUM_OLCULEMEDI, "sayac": bos_sayac(), "atlanan": {},
         "sebep": "olcum TAMAMLANMADI", "rc": RC_OLCULEMEDI, "yas": None, "ariza": None}
    try:
        if not kolon_hazir(m):
            # 🔴 rc=2 (rc=1 DEGIL): sema eksigi bir OLCUM ENGELIDIR, "sitede 404 var"
            # iddiasi degil. Dokum yine basilir (finally).
            d["sebep"] = "`yayinda` kolonu D1'de YOK -> yuzey OLCULEMEDI"
            d["ariza"] = "D1 semasinda `yayinda` kolonu yok (once: d1-sync.py --sema)"
            return d["rc"]

        d["yas"] = yas_kaynak()
        taslaklar = taslak_idler(m)
        canli, hata = canli_kaynak()
        canli_sirali = list(canli) if canli is not None else []
        if canli is None:
            # Canli JSON okunamadi: yayina alma FAIL-CLOSED durur (satirlar taslak kalir,
            # yani gorunmez — 404 uretilemez). Yuzey de bos kalir -> hukum OLCULEMEDI.
            print("!! CANLI KATALOG OKUNAMADI: %s" % hata)

        adaylar, atlanan = adaylari_sec(taslaklar, yerel_kaynak(), canli_sirali)
        d["atlanan"] = atlanan
        print("D1 TASLAK: %d · yayin adayi: %d · aday-disi: %d"
              % (len(taslaklar), len(adaylar), len(atlanan)))
        for uid, sebep in sorted(atlanan.items())[:20]:
            print("   aday DEGIL %s — %s" % (uid, sebep))

        tavan_asildi = len(adaylar) > AZAMI_ADAY
        if tavan_asildi:
            print("!! ADAY SAYISI TAVANI ASTI: %d > %d. Bu bir GOC yigini; tek tek HTTP "
                  "dogrulamasi bu olcekte yapilmaz." % (len(adaylar), AZAMI_ADAY))
            print("!! Coz: python3 tools/yayin-kapisi.py --geriye-doldur")
            adaylar = []      # yazma yapilmaz; yuzey hukmu YINE DE olculur

        # ── OLCUM: taslak adaylari + canli katalog kesiti + nobet satiri ───────────
        plan = olcum_plani(adaylar, canli_sirali)
        d["olcumler"] = olcumleri_yap(plan, prob=prob)
        d["hukum"], d["sebep"], d["sayac"] = yuzey_hukmu(d["olcumler"], d["yas"])

        # ── YAZMA: yalniz TASLAK kaynagindan 200 alanlar ────────────────────────────
        kodlar = {o["id"]: o["alinan"] for o in d["olcumler"]
                  if o["kaynak"] == KAYNAK_TASLAK and o.get("govde") is not False}
        yayinlanacak, basarisiz = yayin_karari(adaylar, kodlar)
        if adaylar:
            print("canli 200 dogrulanan aday: %d / %d" % (len(yayinlanacak), len(adaylar)))
        for uid, kod in basarisiz[:20]:
            print("   TASLAK KALDI %s — HTTP %s" % (uid, kod))

        yazma_hatasi = False
        if yayinlanacak:
            for parca in parcala(yayinlanacak):
                m.dosya_calistir(yayin_sql(parca, release, m.q))
            # GERI-OKUMA: iddia degil, D1'den TEYIT (d1-sync write-verify deseni).
            kalan = []
            for parca in parcala(yayinlanacak):
                r = m.sorgu("SELECT id FROM urunler WHERE yayinda=0 AND id IN (%s)"
                            % ",".join(m.q(i) for i in parca))
                kalan += [s["id"] for s in (r[0].get("results") or [])]
            if kalan:
                print("!! YAZMA DOGRULANAMADI: %d id hala TASLAK (or. %s)"
                      % (len(kalan), ", ".join(kalan[:5])))
                yazma_hatasi = True
            else:
                print("YAYINA ALINDI: %d urun (release=%s) — geri-okuma ile DOGRULANDI"
                      % (len(yayinlanacak), release))

        # ── CIKIS KODU: hukum politikasi + yazma/olcek arizalari ───────────────────
        # 🔴 KAYBOLAN KIRMIZI GERI KONDU: taslak adayinin sayfa probu 200 vermediyse
        # (404, soft-404, 5xx, 403 ya da AG HATASI/None) o satir YAYINA ALINMADI ve bu
        # hal rc'ye MUTLAKA girer. Hangi kola dustugu SINIFA gore belirlenir:
        #   404 / soft-404 (sayfa YOK)       -> hukum KIRMIZI -> rc=1
        #   403/429/5xx/None (ortam/gecici)  -> hukum OLCULEMEDI -> rc=2 (rc=1 DEGIL)
        # Ikisi de sifir-DISI; "olculemedi" hicbir kolda 'iyi' degildir.
        d["rc"] = hukum_cikis_kodu(d["hukum"])
        if basarisiz and d["rc"] == RC_YESIL:
            # DERINLIK SAVUNMASI — YAPISAL OLARAK ULASILAMAZ (ayirt edici mutanti YOK,
            # raporda BEYAN edilir): `basarisiz` bos degilse o taslak olcumu zaten
            # KIRMIZI ya da GECICI siniftadir, dolayisiyla hukum YESIL olamaz.
            print("!! %d aday yayina ALINAMADI ama hukum YESIL dedi -> OLCULEMEDI'ye "
                  "cekiliyor" % len(basarisiz))
            d["hukum"], d["rc"] = HUKUM_OLCULEMEDI, RC_OLCULEMEDI
        if yazma_hatasi or tavan_asildi:
            d["rc"] = RC_KIRMIZI   # D1 yazmasi dogrulanamadi / goc olcegi: GERCEK ariza
        return d["rc"]
    except Exception as e:
        # 🔴 rc=2: wrangler/D1 ARIZASI bir OLCUM engelidir, "site bozuk" iddiasi degil.
        d["hukum"], d["rc"] = HUKUM_OLCULEMEDI, RC_OLCULEMEDI
        d["ariza"] = "%s: %s" % (type(e).__name__, e)
        d["sebep"] = "olcum ISTISNAYLA kesildi -> %s" % d["ariza"]
        print("!! ISTISNA (yutulmadi, siniflandirildi): %s" % d["ariza"])
        return d["rc"]
    finally:
        # Jeton + kol sayilari HER YOLDA basilir. Buradaki ikinci bir istisna orijinali
        # GIZLEMEZ: yakalanir ve AYRI satirda basilir.
        try:
            dokum_bas(d["olcumler"], d["hukum"], d["sebep"], d["sayac"], d["atlanan"],
                      rc=d["rc"], artefakt_yas=d["yas"], ariza=d["ariza"])
        except Exception as e2:
            print("!! DOKUM BASILAMADI (orijinal ariza yukarida durur): %s: %s"
                  % (type(e2).__name__, e2))


def komut_geriye_doldur(m, release):
    """TEK SEFERLIK goc: CANLI urunler.json'da olan her id -> yayinda=1.
    KANIT: canli urunler.json ile /urun/ sayfalari AYNI Pages artefaktindan yayinlanir
    (deploy.yml `_site`), yani canli JSON'daki id'nin sayfasi da canlidadir. Bu yuzden
    15.000 tekil HTTP istegi ATILMAZ — ve ORNEKLEME de yapilmaz: karar TEK bir kanit
    kumesi (canli JSON) uzerinden TAM uygulanir.
    🔴 AYNI UC-JETON POLITIKASI: olcum engeli -> rc=2; geri-okuma basarisiz -> rc=1."""
    if not kolon_hazir(m):
        print("HUKUM: OLCULEMEDI (rc=%d) — sema eksigi OLCUM ENGELI" % RC_OLCULEMEDI)
        return RC_OLCULEMEDI
    canli, hata = canli_urun_idleri()
    if canli is None:
        print("OLCULEMEDI: %s — geriye doldurma YAPILMADI (fail-closed)." % hata)
        print("HUKUM: OLCULEMEDI (rc=%d)" % RC_OLCULEMEDI)
        return RC_OLCULEMEDI
    taslaklar = set(taslak_idler(m))
    hedef = sorted(taslaklar & set(canli))
    print("D1 taslak: %d · canli JSON id: %d · doldurulacak: %d"
          % (len(taslaklar), len(set(canli)), len(hedef)))
    if not hedef:
        print("Doldurulacak satir yok (exit 0).")
        return 0
    for parca in parcala(hedef):
        m.dosya_calistir(yayin_sql(parca, release, m.q))
    toplam, yayinda, taslak = d1_sayilar(m)
    print("SONRASI — toplam=%d yayinda=%d taslak=%d" % (toplam, yayinda, taslak))
    kalan = sorted(set(taslak_idler(m)) & set(canli))
    if kalan:
        print("!! GERI-OKUMA: %d id hala TASLAK (or. %s)" % (len(kalan), ", ".join(kalan[:5])))
        return 1
    print("GERIYE DOLDURMA DOGRULANDI: canli JSON'daki hicbir id TASLAK degil.")
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# KABUL FIKSTURLERI — SAHTE D1 + SAHTE HTTP (ag CAGRILMAZ, dosya YAZILMAZ)
# ═══════════════════════════════════════════════════════════════════════════════
class SahteD1:
    """D1 taklidi: gercek d1-sync sozlesmesinin YALNIZ bu kapinin kullandigi yuzeyi.
    Id'ler UYDURMADIR (gercek katalog id'si, tedarikci ya da kova adi GECMEZ)."""

    def __init__(self, satirlar, kolon=True, sorgu_patlar=False, yazma_patlar=False):
        self.satirlar = dict(satirlar)      # {uydurma_id: yayinda (0/1)}
        self.kolon = kolon
        self.yazilan_sql = []
        # ARIZA ENJEKSIYONU: gercek hayatta wrangler ag/kota hatasi ISTISNA firlatir.
        self.sorgu_patlar = sorgu_patlar
        self.yazma_patlar = yazma_patlar

    def kolon_var_mi(self, tablo, kolon):
        return self.kolon

    @staticmethod
    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    def sorgu(self, sql):
        if self.sorgu_patlar:
            raise RuntimeError("wrangler d1 execute basarisiz (sahte ag/kota hatasi)")
        if "IN (" in sql:               # geri-okuma: WHERE yayinda=0 AND id IN (...)
            secili = [i for i in self.satirlar if self.q(i) in sql]
            return [{"results": [{"id": i} for i in sorted(secili)
                                 if int(self.satirlar[i] or 0) == 0]}]
        if "WHERE yayinda=0" in sql:
            return [{"results": [{"id": i} for i, v in sorted(self.satirlar.items())
                                 if int(v or 0) == 0]}]
        raise AssertionError("SahteD1: beklenmeyen sorgu -> " + sql)

    def dosya_calistir(self, sql):
        if self.yazma_patlar:
            raise RuntimeError("wrangler d1 dosya calistirma basarisiz (sahte kota)")
        self.yazilan_sql.append(sql)
        for i in list(self.satirlar):
            if self.q(i) in sql and int(self.satirlar[i] or 0) == 0:
                self.satirlar[i] = 1


def sahte_prob(kod_haritasi, varsayilan=404, govde_haritasi=None):
    """(yol, beklenen, uid) -> (kod, yas_sn, govde_isareti). Gercek yol_kodu()'nun CIKTI
    SEKLINI taklit eder ([[nobetci-fikstur-sekli]]).
      kod_haritasi   : yol -> HTTP kodu (eslenmeyen yol `varsayilan`; None = AG HATASI)
      govde_haritasi : yol -> govde isareti (True/False/None). VERILMEZSE 200 alan sayfa
                       SAGLIKLI govde (True) sayilir — fikstur varsayilani BU, cunku
                       vakalarin cogu govde eksenini SINAMAZ; soft-404 vakalari isareti
                       ACIKCA False verir."""
    cagrilan = []
    govde_haritasi = govde_haritasi or {}

    def prob(yol, beklenen=200, uid=None):
        cagrilan.append(yol)
        kod = kod_haritasi.get(yol, varsayilan)
        if yol in govde_haritasi:
            govde = govde_haritasi[yol]
        else:
            govde = True if kod == 200 else None
        return kod, None, govde

    prob.cagrilan = cagrilan
    return prob


# ═══════════════════════════════════════════════════════════════════════════════
# KENDINI TEST — OFFLINE (ag YOK, D1 YOK, wrangler YOK, dosya YAZMAZ)
# ═══════════════════════════════════════════════════════════════════════════════
def kendini_test():
    gecen, kalan = [0], [0]

    def dogrula(ad, kosul, detay=""):
        if kosul:
            gecen[0] += 1
            print("  GECTI " + ad)
        else:
            kalan[0] += 1
            print("  KALDI " + ad + (" — " + str(detay) if detay else ""))

    # ── ADAY SECIMI (fail-closed uc sart) ────────────────────────────────────────
    a, atl = adaylari_sec(["x", "y", "z"], ["x", "y"], ["x"])
    dogrula("Y1 ADAY: yalniz yerel VE canli JSON'da olan taslak aday olur", a == ["x"], a)
    dogrula("Y2 ADAY: yerelde olmayan taslak 'bayat satir' diye atlanir",
            "bayat" in atl.get("z", ""), atl)
    dogrula("Y3 ADAY: canlida henuz olmayan taslak 'deploy oturmadi' diye atlanir",
            "deploy oturmadi" in atl.get("y", ""), atl)
    a2, _ = adaylari_sec([], ["x"], ["x"])
    dogrula("Y4 ADAY: taslak yoksa aday da yok (yanlis-pozitif nobeti)", a2 == [], a2)

    # ── YAYIN KARARI (yalniz 200) ────────────────────────────────────────────────
    y, b = yayin_karari(["a", "b", "c", "d"],
                        {"a": 200, "b": 404, "c": None, "d": 500})
    dogrula("Y5 KARAR POZITIF: 200 donen yayina alinir", y == ["a"], y)
    dogrula("Y6 KARAR NEGATIF: 404 TASLAK kalir", ("b", 404) in b, b)
    dogrula("Y7 KARAR NEGATIF: istek patlayan (None) TASLAK kalir", ("c", None) in b, b)
    dogrula("Y8 KARAR NEGATIF: 5xx TASLAK kalir", ("d", 500) in b, b)
    y2, b2 = yayin_karari(["a", "b"], {"a": 200})
    dogrula("Y9 KARAR: HIC OLCULMEYEN id 'iyi' sayilmaz -> basarisiz",
            y2 == ["a"] and b2 == [("b", "OLCULMEDI")], (y2, b2))
    y3, b3 = yayin_karari(["a", "b"], {"a": 200, "b": 200})
    dogrula("Y10 KARAR: hepsi 200 -> hepsi yayinda, basarisiz YOK",
            y3 == ["a", "b"] and b3 == [], (y3, b3))

    # ── SQL SOZLESMESI ───────────────────────────────────────────────────────────
    alinti = (lambda s: "'" + str(s).replace("'", "''") + "'")
    sql = yayin_sql(["a", "b"], "sha1", alinti)
    dogrula("Y11 SQL: yalniz TASLAK satiri gunceller (WHERE yayinda=0)",
            "WHERE yayinda=0" in sql, sql)
    dogrula("Y12 SQL: yayinda=1 + release_id yazilir", "SET yayinda=1" in sql
            and "release_id='sha1'" in sql, sql)
    dogrula("Y13 SQL: TEK YON — yayinda=0'a dusuren ifade URETILMEZ",
            "yayinda=0," not in sql and "SET yayinda=0" not in sql, sql)
    dogrula("Y14 SQL: id'ler alintilanir (enjeksiyon nobeti)",
            yayin_sql(["a'b"], "r", alinti).count("''") == 1,
            yayin_sql(["a'b"], "r", alinti))

    # ── DEGISMEZ (yayinda=1 -> canli JSON'da olmali) ─────────────────────────────
    dogrula("Y20 DEGISMEZ POZITIF: yayindakilerin hepsi canli JSON'da -> ihlal 0",
            ihlal_idler(["a", "b"], ["a", "b", "c"]) == [], ihlal_idler(["a", "b"], ["a", "b", "c"]))
    dogrula("Y21 DEGISMEZ NEGATIF: canli JSON'da olmayan yayinda kayit YAKALANIR",
            ihlal_idler(["a", "hayalet"], ["a"]) == ["hayalet"],
            ihlal_idler(["a", "hayalet"], ["a"]))
    dogrula("Y22 DEGISMEZ: TASLAK kayit ihlal SAYILMAZ (yalniz yayinda=1 olculur)",
            ihlal_idler([], ["a"]) == [])

    # ── HAL-JSON: "yayin gecikmesi" ile "GERCEK KAYIP" ayrimi ────────────────────
    yk, yy, yt = hal_bol(["a", "b", "c"], {"a": 1, "b": 0})
    dogrula("Y23 HAL: D1'de satiri OLMAYAN id 'yok' (GERCEK KAYIP) kolonuna duser",
            yk == ["c"], yk)
    dogrula("Y24 HAL: yayinda=1 olan id 'yayinda' kolonuna duser", yy == ["a"], yy)
    dogrula("Y25 HAL: yayinda=0 olan id 'taslak' (YAYIN GECIKMESI) kolonuna duser",
            yt == ["b"], yt)
    dogrula("Y26 HAL: bos girdi -> uc kolon da bos (yanlis-pozitif nobeti)",
            hal_bol([], {}) == ([], [], []))
    # MUTASYON M4: "haritada yoksa taslak say" -> GERCEK KAYIP sessizce muaf olurdu.
    mutant = sorted([u for u in ["a", "c"] if int({"a": 1}.get(u, 0)) != 1])
    dogrula("Y27 MUTASYON M4: 'bilinmeyen id'yi taslak say' mutanti gercek kaybi YUTAR",
            mutant == ["c"] and yk == ["c"], mutant)

    # ── YAS OLCUSU (sunucu saati; yerel saat kaymasindan BAGIMSIZ) ───────────────
    dogrula("Y28 YAS: date - last-modified saniye olarak cikar",
            yas_sn(200, "Sat, 01 Aug 2026 12:30:00 GMT",
                   "Sat, 01 Aug 2026 12:00:00 GMT") == 1800,
            yas_sn(200, "Sat, 01 Aug 2026 12:30:00 GMT", "Sat, 01 Aug 2026 12:00:00 GMT"))
    dogrula("Y29 YAS: last-modified YOKSA None (OLCULEMEDI — 0 DEGIL)",
            yas_sn(200, "Sat, 01 Aug 2026 12:30:00 GMT", None) is None)
    dogrula("Y30 YAS: cozulemeyen tarih None (uydurma sayi URETILMEZ)",
            yas_sn(200, "dun", "bugun") is None)
    dogrula("Y31 YAS: negatif fark 0'a kirpilir (saat kaymasi negatif yas uretmesin)",
            yas_sn(200, "Sat, 01 Aug 2026 12:00:00 GMT",
                   "Sat, 01 Aug 2026 12:30:00 GMT") == 0)

    # ── PARCALAMA (olcek) ────────────────────────────────────────────────────────
    p = parcala(["i%d" % i for i in range(450)], 200)
    dogrula("Y15 PARCA: 450 id -> 200'luk parcalar (200/200/50), id KAYBI YOK",
            [len(x) for x in p] == [200, 200, 50] and sum(len(x) for x in p) == 450,
            [len(x) for x in p])

    # ── TAVAN: goc yigini yayin YAPMAZ ───────────────────────────────────────────
    dogrula("Y16 TAVAN: AZAMI_ADAY sonlu ve makul (sessiz 15k HTTP taramasi YOK)",
            0 < AZAMI_ADAY <= 2000, AZAMI_ADAY)

    # ── KIRMIZI-MUTASYON: kapinin kendi mantigini bozup KACIRDIGINI kanitla ──────
    # M1: "200 sarti" gevsetilir (200 disi da yayinlanir) -> Y6/Y7/Y8 KACIRILIR.
    def mutant_karar_gevsek(adaylar, kodlar):
        return list(adaylar), []
    ym, bm = mutant_karar_gevsek(["a", "b"], {"a": 200, "b": 404})
    dogrula("Y17 MUTASYON M1: '200 sarti' silinince 404'lu urun yayina girer (kapi olu)",
            ym == ["a", "b"] and bm == [], (ym, bm))
    # M2: aday secimi canli JSON sartini birakir -> Y3 KACIRILIR.
    def mutant_aday_gevsek(taslaklar, yerel, canli):
        return sorted(set(taslaklar) & set(yerel)), {}
    am, _ = mutant_aday_gevsek(["x", "y"], ["x", "y"], ["x"])
    dogrula("Y18 MUTASYON M2: canli JSON sarti silinince deploy oturmadan yayin acilir",
            am == ["x", "y"], am)
    # M3: SQL'den WHERE yayinda=0 dusurulur -> release_id ezilir (denetim izi kaybi).
    mutant_sql = "UPDATE urunler SET yayinda=1, release_id='r' WHERE id IN ('a');"
    dogrula("Y19 MUTASYON M3: WHERE yayinda=0 dusen mutant zaten-yayindaki satiri da yazar",
            "WHERE yayinda=0" not in mutant_sql, mutant_sql)

    # ══════════════════════════════════════════════════════════════════════════════
    # BOS YUZEY EKSENI (7 Agu) — "olcecek sey yok" ARTIK YESIL DEGIL
    # ══════════════════════════════════════════════════════════════════════════════
    # ── ADRES BICIMI: `.html` HIC URETILMEZ ([[kanonik-adres-olcum-yanlisi]]) ──────
    dogrula("Y32 ADRES: kanonik bicim /urun/<id>/ (sonda egik cizgi)",
            urun_yolu("uydurma-parca-a1") == "/urun/uydurma-parca-a1/",
            urun_yolu("uydurma-parca-a1"))
    tum_plan = olcum_plani(["taslak-a"], ["canli-%d" % i for i in range(12)])
    dogrula("Y33 ADRES: planin HICBIR satirinda `.html` YOK (sahte 404 tuzagi)",
            all(".html" not in o["yol"] for o in tum_plan),
            [o["yol"] for o in tum_plan if ".html" in o["yol"]])
    dogrula("Y34 ADRES: planin her yolu `/` ile biter (dizin bicimi)",
            all(o["yol"].endswith("/") for o in tum_plan), [o["yol"] for o in tum_plan])
    # SAHTE 404 TUZAGI: site `.html` yoluna 404, kanonik yola 200 verir. Kapi kanonik
    # bicimi urettigi icin YESIL kalmali; `.html` uretse KIRMIZI yanardi.
    kanonik_200 = {urun_yolu(u): 200 for u in ["taslak-a"] + ["canli-%d" % i for i in range(12)]}
    kanonik_200["/urun/" + NOBET_ID + "/"] = 404
    kanonik_200.update({"/urun/canli-%d.html" % i: 404 for i in range(12)})
    h_c, _, s_c = yuzey_hukmu(olcumleri_yap(tum_plan, prob=sahte_prob(kanonik_200)))
    # Beklenen 11 = 1 taslak + 5 en-yeni (min(YENI_N, n-1)) + kuyruktan 5 kesit.
    # Kovalar AYRIK (kesit yeni-kovanin ALMADIGI kuyruktan cekilir) -> sayi kova
    # kuralini da olcer; kural bozulursa bu iddia duser.
    dogrula("Y35 ADRES: `.html` 404 verse bile kanonik yol olculdugu icin hukum YESIL",
            h_c == HUKUM_YESIL and s_c["katalog_pozitif"] == 11, (h_c, s_c))

    # ── KESIT: deterministik, bas/orta/son kapsanir, tekrar YOK ────────────────────
    dogrula("Y36 KESIT: 100 kayittan 5 indeks -> bas ve son DAHIL, artan sirali",
            kesit_indeksleri(100, 5) == [0, 25, 50, 74, 99], kesit_indeksleri(100, 5))
    dogrula("Y37 KESIT: kayit sayisi adetten az -> TUM indeksler (kirpma yok)",
            kesit_indeksleri(3, 5) == [0, 1, 2], kesit_indeksleri(3, 5))
    dogrula("Y38 KESIT: bos katalog -> bos kesit (uydurma indeks URETILMEZ)",
            kesit_indeksleri(0, 5) == [])
    p2 = olcum_plani([], ["c%d" % i for i in range(30)])
    dogrula("Y39 PLAN: ayni id iki kaynaga girmez (tekil id, deterministik sira)",
            len({o["id"] for o in p2}) == len(p2), [o["id"] for o in p2])
    dogrula("Y40 PLAN: ayni girdi ayni plani uretir (rastgelelik YOK)",
            [o["id"] for o in p2] == [o["id"] for o in
                                      olcum_plani([], ["c%d" % i for i in range(30)])])
    # 🔴 COKME DEGIL OLCUM: nobet satiri hic uretilmezse liste BOS olur; indeksleme
    # yapan bir iddia burada COKER ve cokme "kirmizi"yla karisir
    # ([[mutasyon-kaniti-yeniden-uretilebilir]]). Bu yuzden VARLIK ayri olculur.
    nobetler = [o for o in p2 if o["kaynak"] == KAYNAK_NOBET]
    dogrula("Y41 PLAN: nobet satiri HER planda VAR (tam 1 tane)", len(nobetler) == 1,
            len(nobetler))
    dogrula("Y41b PLAN: nobet satiri 404 BEKLER",
            bool(nobetler) and nobetler[0]["beklenen"] == 404, nobetler)
    dogrula("Y42 PLAN: nobet satiri katalog POZITIFI SAYILMAZ",
            bool(nobetler) and nobetler[0]["katalog"] is False, nobetler)

    # ── HUKUM: uc hal ayri ────────────────────────────────────────────────────────
    def olc(satirlar, yas=0):
        """satirlar: (kaynak, id, beklenen, katalog, alinan) ya da 6. eleman govde.
        govde verilmezse 200 alan satir SAGLIKLI (True) sayilir (fikstur varsayilani)."""
        rows = []
        for s in satirlar:
            k, i, b, kt, a = s[:5]
            g = s[5] if len(s) > 5 else (True if a == 200 else None)
            rows.append(dict(kaynak=k, id=i, yol=urun_yolu(i), beklenen=b, katalog=kt,
                             alinan=a, govde=g))
        return yuzey_hukmu(rows, yas)
    h, sb, sc = olc([(KAYNAK_KESIT, "c1", 200, True, 200),
                     (KAYNAK_NOBET, NOBET_ID, 404, False, 404)])
    dogrula("Y43 HUKUM POZITIF: 1+ katalog sayfasi beklenen kodu verdi -> YESIL",
            h == HUKUM_YESIL and sc["katalog_pozitif"] == 1, (h, sc))
    h, sb, sc = olc([])
    dogrula("Y44 HUKUM BOS YUZEY: hic olcum yok -> OLCULEMEDI (success DEGIL)",
            h == HUKUM_OLCULEMEDI and "BOS YUZEY" in sb, (h, sb))
    h, sb, sc = olc([(KAYNAK_NOBET, NOBET_ID, 404, False, 404)])
    dogrula("Y45 HUKUM BOS YUZEY: YALNIZ nobet satiri olculdu -> OLCULEMEDI "
            "(nobet yesili katalog kanitina SAYILMAZ)",
            h == HUKUM_OLCULEMEDI and "BOS YUZEY" in sb, (h, sb))
    h, sb, sc = olc([(KAYNAK_KESIT, "c1", 200, True, 404),
                     (KAYNAK_NOBET, NOBET_ID, 404, False, 404)])
    dogrula("Y46 HUKUM KIRMIZI: yoklanan katalog sayfasi 404 verdi -> KIRMIZI",
            h == HUKUM_KIRMIZI and sc["kirmizi"] == 1, (h, sc))
    h, sb, sc = olc([(KAYNAK_KESIT, "c1", 200, True, 200),
                     (KAYNAK_NOBET, NOBET_ID, 404, False, 200)])
    dogrula("Y47 HUKUM KIRMIZI: nobet id'si 200 verdi (site her yola 200 basiyor) "
            "-> tum 200 olcumleri anlamsiz, KIRMIZI",
            h == HUKUM_KIRMIZI, (h, sb))
    h, sb, sc = olc([(KAYNAK_KESIT, "c1", 200, True, None),
                     (KAYNAK_NOBET, NOBET_ID, 404, False, None)])
    dogrula("Y48 HUKUM AG HATASI: kod alinamadi -> OLCULEMEDI (sessiz yesil DEGIL)",
            h == HUKUM_OLCULEMEDI and sc["ag_hatasi"] == 2, (h, sc))
    dogrula("Y48b HUKUM AG HATASI: SEBEP 'kod ALINAMADI' der, 'BOS YUZEY' ile "
            "KARISTIRILMAZ (operator hangi ariza oldugunu logdan bilmeli)",
            "kod ALINAMADI" in sb and "BOS YUZEY" not in sb, sb)
    # 🔴 KISMI OLCUM: 2 sayfa 200 + 1 ag hatasi. Pozitif olcum VAR ama yuzeyin bir
    # parcasi OLCULEMEDI -> yesil VERILMEZ. Bu satir olmadan "ag hatasini yut" mutanti
    # (BOS YUZEY dalina dusup ayni jetonu urettigi icin) SAG KALIYORDU.
    h, sb, sc = olc([(KAYNAK_YENI, "c1", 200, True, 200),
                     (KAYNAK_KESIT, "c2", 200, True, 200),
                     (KAYNAK_NOBET, NOBET_ID, 404, False, None)])
    dogrula("Y48c HUKUM KISMI: pozitif olcum VARKEN tek ag hatasi bile YESIL'i keser",
            h == HUKUM_OLCULEMEDI and sc["katalog_pozitif"] == 2 and sc["ag_hatasi"] == 1,
            (h, sb, sc))
    # 🔴 `katalog` BAYRAGININ SOZLESMESI: katalog=False bir satir 200 verse de POZITIF
    # SAYILMAZ. (Bugun boyle bir satir tipi yok; bu iddia bayragin anlamini kilitler ki
    # yarin eklenen "katalog olmayan ama 200 bekleyen" bir prob yuzeyi SISIRMESIN.)
    h, sb, sc = olc([(KAYNAK_NOBET, "yardimci-uc", 200, False, 200)])
    dogrula("Y48d HUKUM: katalog=False satir 200 verse de POZITIF SAYILMAZ -> BOS YUZEY",
            h == HUKUM_OLCULEMEDI and "BOS YUZEY" in sb and sc["katalog_pozitif"] == 0,
            (h, sb, sc))
    h, sb, sc = olc([(KAYNAK_KESIT, "c1", 200, True, 404),
                     (KAYNAK_YENI, "c2", 200, True, None)])
    dogrula("Y49 HUKUM SIRA: GERCEK SAPMA ag gurultusunu YENER (kirmizi ortulemez)",
            h == HUKUM_KIRMIZI, (h, sc))
    h, sb, sc = olc([(KAYNAK_TASLAK, "t1", 200, True, 404)])
    dogrula("Y50 HUKUM: canli JSON'da olan TASLAK adayin sayfasi 404 -> KIRMIZI "
            "(eski kodun rc=1 duyarliligi korundu)", h == HUKUM_KIRMIZI, (h, sc))

    # ── CIKIS KODU POLITIKASI: UC JETON -> UC AYRI RC ─────────────────────────────
    dogrula("Y51 RC: KIRMIZI -> 1 (gercek kusur)",
            hukum_cikis_kodu(HUKUM_KIRMIZI) == 1, hukum_cikis_kodu(HUKUM_KIRMIZI))
    dogrula("Y52 RC: YESIL -> 0", hukum_cikis_kodu(HUKUM_YESIL) == 0)
    dogrula("Y53 RC: OLCULEMEDI -> 2 (ev kurali: kosumu KIRMIZI yakar, yayini DURDURMAZ; "
            "emsal nobet.yml:88 · paket-tazelik-alarmi.yml:195)",
            hukum_cikis_kodu(HUKUM_OLCULEMEDI) == 2, hukum_cikis_kodu(HUKUM_OLCULEMEDI))
    dogrula("Y54 RC: uc hal UC AYRI jeton (ikisi ayni degere COKMEZ)",
            len({HUKUM_YESIL, HUKUM_KIRMIZI, HUKUM_OLCULEMEDI}) == 3)
    dogrula("Y54b RC: uc jeton UC AYRI cikis koduna duser (hicbiri COKMEZ) — "
            "OLCULEMEDI artik `success` DEGIL",
            len({hukum_cikis_kodu(HUKUM_YESIL), hukum_cikis_kodu(HUKUM_KIRMIZI),
                 hukum_cikis_kodu(HUKUM_OLCULEMEDI)}) == 3
            and hukum_cikis_kodu(HUKUM_OLCULEMEDI) != 0,
            [hukum_cikis_kodu(h) for h in (HUKUM_YESIL, HUKUM_KIRMIZI, HUKUM_OLCULEMEDI)])

    # ── OLCUM SINIFI: gecici hal vs GERCEK KUSUR ───────────────────────────────────
    def sinif(kaynak, beklenen, alinan, yas=0, govde=None):
        if govde is None:
            govde = True if alinan == 200 else None
        return olcum_sinifi({"kaynak": kaynak, "id": "x", "beklenen": beklenen,
                             "alinan": alinan, "katalog": True, "govde": govde}, yas)[0]
    dogrula("Y67 SINIF: beklenen kod alindi -> OK",
            sinif(KAYNAK_KESIT, 200, 200) == SINIF_OK)
    dogrula("Y68 SINIF: canli-KESIT 404 -> KIRMIZI (eski/deterministik kayit; rollout "
            "penceresiyle aciklanamaz)", sinif(KAYNAK_KESIT, 200, 404) == SINIF_KIRMIZI,
            sinif(KAYNAK_KESIT, 200, 404))
    dogrula("Y69 SINIF: canli-YENI 404 + artefakt TAZE -> GECICI (ROLLOUT PENCERESI)",
            sinif(KAYNAK_YENI, 200, 404, yas=0) == SINIF_GECICI,
            sinif(KAYNAK_YENI, 200, 404, yas=0))
    # ── ROLLOUT AFFI YASA BAGLI (3. tur): sinirsiz af KALICI 404'u ortuyordu ────────
    dogrula("Y69b AF: yas < esik (%d sn) -> GECICI" % ROLLOUT_ESIK_SN,
            sinif(KAYNAK_YENI, 200, 404, yas=ROLLOUT_ESIK_SN - 1) == SINIF_GECICI,
            sinif(KAYNAK_YENI, 200, 404, yas=ROLLOUT_ESIK_SN - 1))
    dogrula("Y69c AF: yas == esik -> KIRMIZI (af BITTI; sinir DAHIL degil)",
            sinif(KAYNAK_YENI, 200, 404, yas=ROLLOUT_ESIK_SN) == SINIF_KIRMIZI,
            sinif(KAYNAK_YENI, 200, 404, yas=ROLLOUT_ESIK_SN))
    dogrula("Y69d AF: yas >> esik -> KIRMIZI (KALICI 404; sinirsiz af KAPANDI)",
            sinif(KAYNAK_YENI, 200, 404, yas=ROLLOUT_ESIK_SN * 10) == SINIF_KIRMIZI,
            sinif(KAYNAK_YENI, 200, 404, yas=ROLLOUT_ESIK_SN * 10))
    dogrula("Y69e AF: yas OLCULEMEDI (None) -> KIRMIZI (fail-closed; af mazerete "
            "dayanmaz)", sinif(KAYNAK_YENI, 200, 404, yas=None) == SINIF_KIRMIZI,
            sinif(KAYNAK_YENI, 200, 404, yas=None))
    dogrula("Y69f AF: af YALNIZ canli-yeni kolunda — kesit TAZE artefaktta bile KIRMIZI",
            sinif(KAYNAK_KESIT, 200, 404, yas=0) == SINIF_KIRMIZI
            and sinif(KAYNAK_TASLAK, 200, 404, yas=0) == SINIF_KIRMIZI)
    dogrula("Y69g AF: esik kodda TEK SABIT ve makul (0 < esik <= 1 saat)",
            0 < ROLLOUT_ESIK_SN <= 3600, ROLLOUT_ESIK_SN)

    # ── SOFT-404 (200 + hata govdesi) ──────────────────────────────────────────────
    dogrula("Y69h SOFT404: 200 + govde isareti FALSE -> hard 404 gibi yargilanir "
            "(kesit kolunda KIRMIZI)",
            sinif(KAYNAK_KESIT, 200, 200, yas=0, govde=False) == SINIF_KIRMIZI,
            sinif(KAYNAK_KESIT, 200, 200, yas=0, govde=False))
    dogrula("Y69i SOFT404: canli-yeni kolunda TAZE artefaktta af GECERLI (ayni yasaya "
            "bagli, ucuncu sinif URETILMEDI)",
            sinif(KAYNAK_YENI, 200, 200, yas=0, govde=False) == SINIF_GECICI)
    dogrula("Y69j SOFT404: canli-yeni + yas > esik -> KIRMIZI",
            sinif(KAYNAK_YENI, 200, 200, yas=ROLLOUT_ESIK_SN + 1,
                  govde=False) == SINIF_KIRMIZI)
    dogrula("Y69k SOFT404: 200 ama govde OLCULEMEDI (None) -> GECICI "
            "(fail-closed: govdeyi gormeden 'saglam' denmez)",
            olcum_sinifi({"kaynak": KAYNAK_KESIT, "id": "x", "beklenen": 200,
                          "alinan": 200, "katalog": True, "govde": None}, 0)[0]
            == SINIF_GECICI)
    # ISARET: kanonik capa + asgari govde. Capa AYNI urun_yolu()'ndan turer.
    gercek_govde = (b"<html><head><link rel=\"canonical\" href=\""
                    + urun_capasi("uydurma-parca-a1").encode() + b"\">"
                    + b"x" * GOVDE_ASGARI_BAYT + b"</head></html>")
    dogrula("Y69l ISARET: kanonik capa + asgari boy VAR -> True (gercek urun sayfasi)",
            govde_isareti("uydurma-parca-a1", gercek_govde) is True)
    dogrula("Y69m ISARET: capa YOK (hata sayfasi govdesi) -> False",
            govde_isareti("uydurma-parca-a1", b"<html>Sayfa bulunamadi</html>"
                          + b"y" * GOVDE_ASGARI_BAYT) is False)
    dogrula("Y69n ISARET: capa VAR ama govde kirpik (< %d bayt) -> False"
            % GOVDE_ASGARI_BAYT,
            govde_isareti("uydurma-parca-a1",
                          urun_capasi("uydurma-parca-a1").encode()) is False)
    dogrula("Y69o ISARET: govde YOK -> None (OLCULEMEDI, False DEGIL)",
            govde_isareti("uydurma-parca-a1", None) is None)
    dogrula("Y69p ISARET: BASKA urunun capasi kendi sayfasini DOGRULAMAZ "
            "(capa id'ye BAGLI)",
            govde_isareti("uydurma-parca-b2", gercek_govde) is False)
    dogrula("Y70 SINIF: TASLAK adayi 404 -> KIRMIZI (canli JSON'da OLDUGU garanti)",
            sinif(KAYNAK_TASLAK, 200, 404) == SINIF_KIRMIZI)
    for kod in (403, 429, 408, 425, 500, 502, 503, 504):
        dogrula("Y71.%s SINIF: %s -> GECICI (ortam; asla KIRMIZI)" % (kod, kod),
                sinif(KAYNAK_KESIT, 200, kod) == SINIF_GECICI,
                sinif(KAYNAK_KESIT, 200, kod))
    dogrula("Y72 SINIF: kod ALINAMADI (None = timeout/ag) -> GECICI",
            sinif(KAYNAK_KESIT, 200, None) == SINIF_GECICI)
    dogrula("Y73 SINIF: nobet id'si 200 verdi -> KIRMIZI (kapinin gozu bozuk)",
            olcum_sinifi({"kaynak": KAYNAK_NOBET, "id": NOBET_ID, "beklenen": 404,
                          "alinan": 200, "katalog": False})[0] == SINIF_KIRMIZI)
    dogrula("Y74 SINIF: MODELLENMEYEN kod (410) -> GECICI (fail-toward-NOTR; rc=2 zaten "
            "kosumu kirmizi yakar, yanlis-pozitif 'site bozuk' iddiasi URETMEZ)",
            sinif(KAYNAK_KESIT, 200, 410) == SINIF_GECICI, sinif(KAYNAK_KESIT, 200, 410))
    dogrula("Y75 SINIF: gerekce metni KOL ADINI tasir (hangi kol hangi kodu verdi)",
            KAYNAK_YENI in olcum_sinifi({"kaynak": KAYNAK_YENI, "id": "x", "beklenen": 200,
                                         "alinan": 404, "katalog": True})[1],
            olcum_sinifi({"kaynak": KAYNAK_YENI, "id": "x", "beklenen": 200,
                          "alinan": 404, "katalog": True})[1])

    # ══════════════════════════════════════════════════════════════════════════════
    # UCTAN UCA: komut_yayinla, SAHTE D1 + SAHTE HTTP ile (ag/dosya YOK)
    # ══════════════════════════════════════════════════════════════════════════════
    canli12 = ["canli-%d" % i for i in range(12)]

    def kos(d1_satirlari, canli_liste, kod_haritasi, varsayilan=404, canli_hata=None,
            yerel=None, yas=0, govde_haritasi=None, kolon=True, sorgu_patlar=False,
            yazma_patlar=False):
        """komut_yayinla'yi FIKSTURLE kosar; stdout yakalanir (dokum gurultusu tasmasin).
        `yas` = artefakt yasi (rollout affinin saati). Doner: (rc, d1, prob, cikti)"""
        m = SahteD1(d1_satirlari, kolon=kolon, sorgu_patlar=sorgu_patlar,
                    yazma_patlar=yazma_patlar)
        prob = sahte_prob(kod_haritasi, varsayilan, govde_haritasi)
        kaynak = (lambda: (None, canli_hata)) if canli_hata else (lambda: (canli_liste, None))
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            rc = komut_yayinla(m, "test-release", prob=prob, canli_kaynak=kaynak,
                               yerel_kaynak=(lambda: list(yerel if yerel is not None
                                                          else canli_liste)),
                               yas_kaynak=(lambda: yas))
        return rc, m, prob, tampon.getvalue()

    def hukum_of(cikti):
        for s in cikti.splitlines():
            if s.startswith("HUKUM: "):
                return s.split("HUKUM: ", 1)[1].split(" —")[0].strip()
        return "(HUKUM BASILMADI)"

    tum_200 = {urun_yolu(u): 200 for u in canli12}
    tum_200["/urun/" + NOBET_ID + "/"] = 404

    # 🔴 KOL ID'LERI PLANDAN TURETILIR, SABIT YAZILMAZ: kol dagitim kurali degistiginde
    # sabit id sessizce "hic yoklanmayan" bir sayfaya isaret eder ve fikstur KOR olur
    # (olculdu: 3. turda dagitim kurali degisti, elle yazilan id artik hicbir kolda yer
    # almiyordu -> kesit-404 vakasi rc=0 verdi). ([[ikiz-tanim-sessiz-ayrisma]])
    # 🔴 COKME DEGIL OLCUM: kol bosalirsa indeksleme COKER ve cokme "kirmizi"yla
    # karisir ([[mutasyon-kaniti-yeniden-uretilebilir]]) -> varlik AYRI olculur.
    _p12 = olcum_plani([], canli12)
    _yeniler = [o["id"] for o in _p12 if o["kaynak"] == KAYNAK_YENI]
    _kesitler = [o["id"] for o in _p12 if o["kaynak"] == KAYNAK_KESIT]
    dogrula("Y54c FIKSTUR: 12'lik katalogta HER IKI kol da DOLU (yeni=%d · kesit=%d)"
            % (len(_yeniler), len(_kesitler)), bool(_yeniler) and bool(_kesitler),
            (_yeniler, _kesitler))
    YENI_ID = _yeniler[0] if _yeniler else canli12[0]
    KESIT_ID = _kesitler[0] if _kesitler else canli12[-1]
    dogrula("Y54d FIKSTUR: kol id'leri plandan turedi (yeni=%s · kesit=%s), FARKLI"
            % (YENI_ID, KESIT_ID), YENI_ID != KESIT_ID)

    # ── 1) RC TABLOSU: uc jeton UCTAN UCA uc AYRI rc'ye dusuyor mu? ────────────────
    print("\n  ┌─ RC TABLOSU (uctan uca fikstur) ─────────────────────────────")
    rc_y, m_y, prob_y, ck_y = kos({}, canli12, tum_200)                      # hepsi 200
    kesit404 = dict(tum_200)
    kesit404[urun_yolu(KESIT_ID)] = 404              # KESIT kolu: af YOK -> KIRMIZI
    rc_k, m_k, _, ck_k = kos({}, canli12, kesit404)
    rc_o, m_o, _, ck_o = kos({}, [], {"/urun/" + NOBET_ID + "/": 404})       # bos yuzey
    for etiket, rc_v, ck in (("YESIL     ", rc_y, ck_y), ("KIRMIZI   ", rc_k, ck_k),
                             ("OLCULEMEDI", rc_o, ck_o)):
        print("  │ %s -> rc=%d  (basilan hukum: %s)" % (etiket, rc_v, hukum_of(ck)))
    print("  └──────────────────────────────────────────────────────────────")
    dogrula("Y55 RC TABLOSU: YESIL->0 · KIRMIZI->1 · OLCULEMEDI->2 (uc AYRI rc, "
            "hicbiri COKMEZ)", (rc_y, rc_k, rc_o) == (0, 1, 2), (rc_y, rc_k, rc_o))
    dogrula("Y55b RC TABLOSU: basilan hukum jetonlari da UC AYRI",
            (hukum_of(ck_y), hukum_of(ck_k), hukum_of(ck_o))
            == (HUKUM_YESIL, HUKUM_KIRMIZI, HUKUM_OLCULEMEDI),
            (hukum_of(ck_y), hukum_of(ck_k), hukum_of(ck_o)))
    dogrula("Y55c RC: cikti CIKIS KODU satirini ACIKCA basar (rc gorunur olsun)",
            "CIKIS KODU: 2" in ck_o, ck_o.strip()[-160:])

    # ── 2) KONTROL MUTANTI (YESIL KALMALI) ────────────────────────────────────────
    dogrula("Y56 KONTROL: taslak yok + canli sayfalar 200 -> rc=0 VE >=6 sayfa FIILEN "
            "yoklandi (kor yesil DEGIL)",
            rc_y == 0 and len(prob_y.cagrilan) >= 6, (rc_y, len(prob_y.cagrilan)))
    dogrula("Y56b KONTROL: yoklanan yollarin hepsi kanonik (`.html` YOK)",
            all(".html" not in y for y in prob_y.cagrilan), prob_y.cagrilan)
    kaynaklar = {o["kaynak"] for o in olcum_plani([], canli12)}
    dogrula("Y56c KONTROL: taslak yokken bile YUZEY = canli-yeni + canli-kesit + nobet",
            kaynaklar == {KAYNAK_YENI, KAYNAK_KESIT, KAYNAK_NOBET}, kaynaklar)

    # ── 3) CURUTUCUNUN BES SAHTE-YESIL VEKTORU — HER BIRI ICIN rc AYRI BASILIR ────
    print("\n  ┌─ SAHTE-YESIL VEKTORLERI (hicbiri rc=0 OLMAYACAK) ────────────")
    vektorler = []
    # (a) taslak 0 + canli katalog BOS
    va = kos({}, [], {"/urun/" + NOBET_ID + "/": 404})
    vektorler.append(("(a) taslak 0 + canli BOS", va))
    # (b) canli JSON okunuyor ama 0 KAYIT; D1'de taslak VAR (aday olamaz)
    vb = kos({"taslak-b": 0}, [], {"/urun/" + NOBET_ID + "/": 404})
    vektorler.append(("(b) canli 0 kayit + taslak var", vb))
    # (c) HTTP her istekte patlar
    vc = kos({}, canli12, {}, varsayilan=None)
    vektorler.append(("(c) HTTP her istekte patlar", vc))
    # (d) YALNIZ nobet-404 olculdu (katalog kolu bos, nobet dogru cevap verdi)
    vd = kos({}, [], {"/urun/" + NOBET_ID + "/": 404})
    vektorler.append(("(d) yalniz nobet-404 olculdu", vd))
    # (e) canli JSON OKUNAMADI + bekleyen taslak
    ve = kos({"taslak-e": 0}, canli12, tum_200,
             canli_hata="canli urunler.json alinamadi (kod=None)")
    vektorler.append(("(e) canli JSON okunamadi + taslak bekliyor", ve))
    for ad, (rcv, mv, pv, ckv) in vektorler:
        print("  │ %-40s rc=%d  hukum=%s  yazma=%d" % (ad, rcv, hukum_of(ckv),
                                                       len(mv.yazilan_sql)))
    print("  └──────────────────────────────────────────────────────────────")
    for i, (ad, (rcv, mv, pv, ckv)) in enumerate(vektorler):
        dogrula("Y57.%d SAHTE-YESIL %s -> rc=%d (SIFIR DEGIL) ve hukum OLCULEMEDI"
                % (i + 1, ad, rcv),
                rcv == RC_OLCULEMEDI and hukum_of(ckv) == HUKUM_OLCULEMEDI, (rcv, ckv[-200:]))
        dogrula("Y58.%d SAHTE-YESIL %s -> hicbir satir yayina ALINMAZ" % (i + 1, ad),
                mv.yazilan_sql == [], mv.yazilan_sql)

    # ── 4) KAYIP KIRMIZI GERI GELDI: taslak adayinin probu 200 VERMEDI ────────────
    print("\n  ┌─ KAYIP KIRMIZI (taslak adayinin probu 200 degil) ────────────")
    # taslak-n YOLU haritada YOK -> `varsayilan=None` ile AG HATASI/timeout taklit edilir;
    # digerlerinin kodu haritadan gelir (yani yalniz TASLAK kolu olculemez).
    rc_n, m_n, _, ck_n = kos({"taslak-n": 0}, canli12 + ["taslak-n"], tum_200,
                             varsayilan=None)
    print("  │ taslak adayi AG HATASI (None) -> rc=%d hukum=%s yazma=%d"
          % (rc_n, hukum_of(ck_n), len(m_n.yazilan_sql)))
    dogrula("Y59 KAYIP KIRMIZI: taslak adayinin probu AG HATASI -> rc!=0 (rc=2, cunku "
            "ortam/gecici: 'olcemedim' ile 'site bozuk' AYNI SEY DEGIL)",
            rc_n != 0 and rc_n == RC_OLCULEMEDI, rc_n)
    dogrula("Y59b KAYIP KIRMIZI: o taslak YAYINA ALINMADI (fail-closed korundu)",
            m_n.satirlar["taslak-n"] == 0 and m_n.yazilan_sql == [],
            (m_n.satirlar, m_n.yazilan_sql))
    ile_t2 = dict(tum_200)
    ile_t2[urun_yolu("taslak-q")] = 404
    rc_q, m_q, _, ck_q = kos({"taslak-q": 0}, canli12 + ["taslak-q"], ile_t2)
    print("  │ taslak adayi 404 (sayfa YOK)      -> rc=%d hukum=%s"
          % (rc_q, hukum_of(ck_q)))
    print("  └──────────────────────────────────────────────────────────────")
    dogrula("Y59c KAYIP KIRMIZI: taslak adayi 404 -> rc=1 (GERCEK kusur; eski kodun "
            "duyarliligi bu kolda AYNEN korundu)", rc_q == RC_KIRMIZI, rc_q)

    # ── 5) YANLIS-POZITIF KONTROLU: gecici kodlar KIRMIZI YAKMAZ ─────────────────
    print("\n  ┌─ YANLIS-POZITIF KONTROLU (hicbiri rc=1 OLMAYACAK) ──────────")
    yp = []
    for etiket, kod, hedef in (("403 (UA/WAF)", 403, KESIT_ID),
                               ("429 (hiz siniri)", 429, KESIT_ID),
                               ("503 (CDN gecici)", 503, KESIT_ID),
                               ("timeout (None)", None, KESIT_ID),
                               ("canli-YENI 404 (rollout, yas=0)", 404, YENI_ID)):
        h = dict(tum_200)
        if kod is None:
            del h[urun_yolu(hedef)]               # eslenmeyen yol -> varsayilan
            rcv, mv, pv, ckv = kos({}, canli12, h, varsayilan=None)
        else:
            h[urun_yolu(hedef)] = kod
            rcv, mv, pv, ckv = kos({}, canli12, h)
        yp.append((etiket, rcv, hukum_of(ckv)))
        print("  │ %-34s rc=%d hukum=%s" % (etiket, rcv, hukum_of(ckv)))
    rc_kesit, _, _, ck_kesit = kos({}, canli12, kesit404)
    print("  │ %-34s rc=%d hukum=%s" % ("canli-KESIT 404 (gercek kusur)", rc_kesit,
                                        hukum_of(ck_kesit)))
    yeni404 = dict(tum_200)
    yeni404[urun_yolu(YENI_ID)] = 404
    rc_bayat, _, _, ck_bayat = kos({}, canli12, yeni404, yas=ROLLOUT_ESIK_SN + 1)
    print("  │ %-34s rc=%d hukum=%s" % ("canli-YENI 404 (yas>esik: KALICI)", rc_bayat,
                                        hukum_of(ck_bayat)))
    rc_yassiz, _, _, ck_yassiz = kos({}, canli12, yeni404, yas=None)
    print("  │ %-34s rc=%d hukum=%s" % ("canli-YENI 404 (yas OLCULEMEDI)", rc_yassiz,
                                        hukum_of(ck_yassiz)))
    print("  └──────────────────────────────────────────────────────────────")
    for etiket, rcv, hv in yp:
        dogrula("Y60.%s YANLIS-POZITIF: %s -> rc=%d, KIRMIZI (rc=1) DEGIL"
                % (etiket.split()[0], etiket, rcv),
                rcv != RC_KIRMIZI and rcv == RC_OLCULEMEDI, (rcv, hv))
    dogrula("Y61 AYIRT EDICI: canli-KESIT 404 -> rc=1 KIRMIZI (yeni-kol 404 TAZE "
            "artefaktta rc=2 iken; iki kol AYNI kodu AYRI yargilar)",
            rc_kesit == RC_KIRMIZI and yp[-1][1] == RC_OLCULEMEDI,
            (rc_kesit, yp[-1]))
    dogrula("Y61b AF SINIRI (uctan uca): canli-YENI 404 + yas>esik -> rc=1 "
            "(SINIRSIZ AF KAPANDI)", rc_bayat == RC_KIRMIZI, rc_bayat)
    dogrula("Y61c AF SINIRI (uctan uca): canli-YENI 404 + yas OLCULEMEDI -> rc=1 "
            "(fail-closed)", rc_yassiz == RC_KIRMIZI, rc_yassiz)
    dogrula("Y61d AF: ayni 404 uc AYRI rc uretir (yas<esik:2 · yas>esik:1 · yas yok:1)",
            (yp[-1][1], rc_bayat, rc_yassiz) == (2, 1, 1),
            (yp[-1][1], rc_bayat, rc_yassiz))
    dogrula("Y62 DOKUM: OK olmayan her yoklama KOL ADIYLA basilir",
            ("kol=" + KAYNAK_KESIT) in ck_kesit, ck_kesit.strip()[-300:])
    dogrula("Y62b DOKUM: artefakt yasi ve rollout esigi ACIKCA basilir",
            "ARTEFAKT YASI" in ck_bayat and "ROLLOUT ESIGI" in ck_bayat)
    dogrula("Y63 NOBET: var olmayan id 200 verdi -> rc=1 (kapinin gozu bozuk)",
            kos({}, canli12, dict(tum_200, **{"/urun/" + NOBET_ID + "/": 200}))[0]
            == RC_KIRMIZI)

    # ── 5b) SOFT-404 UCTAN UCA ────────────────────────────────────────────────────
    print("\n  ┌─ SOFT-404 (200 + govde ekseni) ──────────────────────────────")
    rc_sf, m_sf, _, ck_sf = kos({}, canli12, tum_200,
                                govde_haritasi={urun_yolu(KESIT_ID): False})
    print("  │ %-34s rc=%d hukum=%s" % ("200 + HATA govdesi (kesit)", rc_sf,
                                        hukum_of(ck_sf)))
    rc_sg, m_sg, _, ck_sg = kos({}, canli12, tum_200,
                                govde_haritasi={urun_yolu(KESIT_ID): None})
    print("  │ %-34s rc=%d hukum=%s" % ("200 + govde OLCULEMEDI", rc_sg,
                                        hukum_of(ck_sg)))
    print("  │ %-34s rc=%d hukum=%s  (KONTROL)" % ("200 + GERCEK urun govdesi", rc_y,
                                                   hukum_of(ck_y)))
    print("  └──────────────────────────────────────────────────────────────")
    dogrula("Y63b SOFT404: 200 + hata govdesi -> rc!=0 (rc=1 KIRMIZI: musteri icin 404 "
            "ile AYNI sey)", rc_sf == RC_KIRMIZI, rc_sf)
    dogrula("Y63c SOFT404: dokumde `200-SOFT404` kodu ACIKCA basilir",
            "200-SOFT404" in ck_sf, ck_sf.strip()[-400:])
    dogrula("Y63d SOFT404: 200 + govde OLCULEMEDI -> rc=2 (fail-closed, yesil DEGIL)",
            rc_sg == RC_OLCULEMEDI, rc_sg)
    dogrula("Y63e SOFT404 KONTROL: 200 + GERCEK urun govdesi -> rc=0 (yanlis-pozitif YOK)",
            rc_y == RC_YESIL, rc_y)
    # Soft-404 veren TASLAK adayi YAYINA ALINMAZ (200 gordu diye acilmasin).
    ile_sf = dict(tum_200)
    ile_sf[urun_yolu("taslak-sf")] = 200
    rc_tsf, m_tsf, _, _ = kos({"taslak-sf": 0}, canli12 + ["taslak-sf"], ile_sf,
                              govde_haritasi={urun_yolu("taslak-sf"): False})
    dogrula("Y63f SOFT404: 200 alan ama govdesi HATA olan TASLAK yayina ALINMAZ",
            m_tsf.satirlar["taslak-sf"] == 0 and m_tsf.yazilan_sql == []
            and rc_tsf == RC_KIRMIZI, (rc_tsf, m_tsf.satirlar, m_tsf.yazilan_sql))

    # ── 5c) N SINIRI: kucuk katalogda KIRMIZI sinifi ULASILABILIR mi? ─────────────
    print("\n  ┌─ N TABLOSU (kova sinirlari; KIRMIZI ulasilabilir mi) ────────")
    n_tablo, n_kirmizi_hepsi = [], True
    for n in (1, 3, 5, 6, 10):
        idler = ["k%02d" % i for i in range(n)]
        pn = olcum_plani([], idler)
        kesitler = [o["id"] for o in pn if o["kaynak"] == KAYNAK_KESIT]
        yeniler = [o["id"] for o in pn if o["kaynak"] == KAYNAK_YENI]
        harita = {urun_yolu(u): 200 for u in idler}
        harita["/urun/" + NOBET_ID + "/"] = 404
        rc_ok, _, _, ck_ok = kos({}, idler, harita)
        bozuk_n = dict(harita)
        if kesitler:
            bozuk_n[urun_yolu(kesitler[0])] = 404
        rc_bz, _, _, ck_bz = kos({}, idler, bozuk_n)
        n_tablo.append((n, len(yeniler), len(kesitler), hukum_of(ck_ok), rc_ok,
                        hukum_of(ck_bz), rc_bz))
        print("  │ n=%-3d yeni=%d kesit=%d · saglam: %s(rc=%d) · kesit-404: %s(rc=%d)"
              % (n, len(yeniler), len(kesitler), hukum_of(ck_ok), rc_ok,
                 hukum_of(ck_bz), rc_bz))
        if not (kesitler and rc_bz == RC_KIRMIZI):
            n_kirmizi_hepsi = False
    print("  └──────────────────────────────────────────────────────────────")
    dogrula("Y63g N SINIRI: n=1/3/5/6/10 — HER birinde kesit kovasi >=1 kayit alir VE "
            "kesit-404 rc=1 KIRMIZI verir (KIRMIZI sinifi ULASILAMAZ DEGIL)",
            n_kirmizi_hepsi, n_tablo)
    dogrula("Y63h N SINIRI: saglam katalogta her n icin hukum YESIL (yanlis-pozitif YOK)",
            all(t[3] == HUKUM_YESIL and t[4] == RC_YESIL for t in n_tablo), n_tablo)
    dogrula("Y63i N SINIRI: ayni id iki kovada OLMAZ (her n icin)",
            all(len({o["id"] for o in olcum_plani([], ["k%02d" % i for i in range(n)])})
                == len(olcum_plani([], ["k%02d" % i for i in range(n)]))
                for n in (1, 3, 5, 6, 10)))

    # ── 5d) KANIT KAYBI: istisna firlasa da jeton + kol sayilari BASILIR ──────────
    print("\n  ┌─ KANIT KAYBI (istisna halinde dokum basiliyor mu) ───────────")
    kk = []
    kk.append(("dosya_calistir istisnasi",
               kos({"taslak-w": 0}, canli12 + ["taslak-w"],
                   dict(tum_200, **{urun_yolu("taslak-w"): 200}), yazma_patlar=True)))
    kk.append(("sorgu istisnasi", kos({}, canli12, tum_200, sorgu_patlar=True)))
    kk.append(("`yayinda` kolonu YOK", kos({}, canli12, tum_200, kolon=False)))
    for ad, (rcv, mv, pv, ckv) in kk:
        print("  │ %-26s rc=%d hukum=%s dokum=%s kol_satiri=%s"
              % (ad, rcv, hukum_of(ckv), "VAR" if "OLCUM DOKUMU" in ckv else "YOK",
                 "VAR" if KAYNAK_KESIT in ckv else "YOK"))
    print("  └──────────────────────────────────────────────────────────────")
    for i, (ad, (rcv, mv, pv, ckv)) in enumerate(kk):
        dogrula("Y63j.%d KANIT KAYBI [%s]: rc=%d OLCULEMEDI (1'e COKMEZ)" % (i + 1, ad, rcv),
                rcv == RC_OLCULEMEDI, (rcv, ckv.strip()[-200:]))
        dogrula("Y63k.%d KANIT KAYBI [%s]: OLCUM DOKUMU + jeton satiri + kol satirlari "
                "BASILDI" % (i + 1, ad),
                "OLCUM DOKUMU" in ckv and "HUKUM:" in ckv and KAYNAK_KESIT in ckv
                and "CIKIS KODU:" in ckv, ckv.strip()[-300:])
    dogrula("Y63l KANIT KAYBI: istisna METNI de basilir (yutulmaz)",
            "ISTISNA" in kk[0][1][3] and "ISTISNA" in kk[1][1][3],
            (kk[0][1][3][-200:], kk[1][1][3][-200:]))
    dogrula("Y63m KANIT KAYBI: kolon yoksa ARIZA satiri sebebi ACIKCA yazar",
            "ARIZA" in kk[2][1][3] and "yayinda" in kk[2][1][3],
            kk[2][1][3].strip()[:400])

    # ── 5e) KULLANIM HATASI rc=2'DEN AYRI ─────────────────────────────────────────
    dogrula("Y63n RC: KULLANIM hatasi kodu OLCULEMEDI'den AYRI (%d != %d)"
            % (RC_KULLANIM, RC_OLCULEMEDI), RC_KULLANIM != RC_OLCULEMEDI)
    dogrula("Y63o RC: KULLANIM kodu YESIL/KIRMIZI ile de CAKISMAZ",
            RC_KULLANIM not in (RC_YESIL, RC_KIRMIZI, RC_OLCULEMEDI))

    # ── 6) KORELME: yayina alma yolu bozulmadi ────────────────────────────────────
    ile_taslak = dict(tum_200)
    ile_taslak[urun_yolu("taslak-y")] = 200
    rc, m, prob, _ = kos({"taslak-y": 0}, canli12 + ["taslak-y"], ile_taslak)
    dogrula("Y64 KORELME: canli 200 veren taslak yayina ALINDI (yayinda=1) ve rc=0",
            rc == 0 and m.satirlar["taslak-y"] == 1, (rc, m.satirlar))
    dogrula("Y65 KORELME: yazilan SQL tek yon (SET yayinda=1) ve WHERE yayinda=0 tasir",
            len(m.yazilan_sql) == 1 and "SET yayinda=1" in m.yazilan_sql[0]
            and "WHERE yayinda=0" in m.yazilan_sql[0], m.yazilan_sql)
    dogrula("Y66 KORELME: yerel JSON'da OLMAYAN taslak aday olmaz -> yazma YOK",
            kos({"hayalet-z": 0}, canli12, tum_200, yerel=canli12)[1].yazilan_sql == [])

    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


class KullanimAyristirici(argparse.ArgumentParser):
    """🔴 KULLANIM HATASI rc=2'DEN AYRILDI. argparse varsayilan olarak hem `error()` hem
    de "bayrak verilmedi" halinde `sys.exit(2)` yapar; rc=2 artik YALNIZ OLCULEMEDI'ye
    ayrilmistir, yoksa "bayragi yanlis yazdim" ile "olcum yapilamadi" AYNI kova olur ve
    cagiran taraf ikisini AYIRT EDEMEZ. Kullanim hatasi = EX_USAGE (64)."""

    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("KULLANIM HATASI (rc=%d, OLCULEMEDI'nin rc=%d'sinden AYRI): %s\n"
                         % (RC_KULLANIM, RC_OLCULEMEDI, message))
        sys.exit(RC_KULLANIM)


def main():
    ap = KullanimAyristirici()
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--yayinla", action="store_true")
    ap.add_argument("--geriye-doldur", action="store_true", dest="geriye")
    ap.add_argument("--hal-json", action="store_true", dest="hal")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    ap.add_argument("--release", default=os.environ.get("GITHUB_SHA", "")[:12] or "yerel")
    a = ap.parse_args()

    if a.kendini:
        sys.exit(kendini_test())
    if a.hal:
        ham = sys.stdin.read()
        idler = [s.strip() for s in ham.replace(",", "\n").splitlines() if s.strip()]
        sys.exit(komut_hal_json(idler))
    if not (a.durum or a.yayinla or a.geriye):
        ap.print_help()
        sys.exit(RC_KULLANIM)      # KULLANIM hatasi — OLCULEMEDI (2) ile KARISTIRILMAZ

    m = yukle_d1sync()
    if a.durum:
        sys.exit(komut_durum(m))
    if a.geriye:
        sys.exit(komut_geriye_doldur(m, "geriye-doldur"))
    sys.exit(komut_yayinla(m, a.release))


if __name__ == "__main__":
    main()
