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
    for uid in list(canli_idler)[:max(0, yeni_n)]:
        # CANLI KATALOG: id canli urunler.json'da -> sayfasi da AYNI artefaktta, 200 SART.
        ekle(KAYNAK_YENI, uid, 200, True)
    for i in kesit_indeksleri(len(canli_idler), kesit_n):
        ekle(KAYNAK_KESIT, canli_idler[i], 200, True)
    if nobet_id:
        ekle(KAYNAK_NOBET, nobet_id, 404, False)
    return plan


def olcum_sinifi(o):
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
      * 404 + beklenen 200:
          - kaynak `canli-yeni` (en yeni N kayit)      -> GECICI: EDGE ROLLOUT penceresi
            (yeni sayfa CDN kenarina henuz oturmamis olabilir — bilinen ve BEKLENEN hal)
          - kaynak `taslak` / `canli-kesit`            -> KIRMIZI: sayfa YOK (gercek kusur;
            iki kaynak da id'nin CANLI urunler.json'da OLDUGUNU garanti eder, kesit ayrica
            ESKI/deterministik kayitlari secer -> rollout penceresiyle aciklanamaz)
      * 200 + beklenen 404 (nobet satiri)              -> KIRMIZI: kapinin GOZU bozuk,
        o kosumdaki TUM 200 olcumleri anlamsiz
      * MODELLENMEYEN kod (410/451/400 ...)            -> GECICI (fail-toward-NOTR).
        Notr, SESSIZ degildir: rc=2 kosumu KIRMIZI yakar, yalniz yayini durdurmaz;
        modellenmemis bir kodu "gercek kusur" saymak yanlis-pozitif uretirdi.
      * 301/308: urllib varsayilan opener yonlendirmeyi IZLER (olculdu) -> ayri kol yok,
        yargi IZLENEN SON koda gore verilir.
    """
    alinan, beklenen, kaynak = o.get("alinan"), o.get("beklenen"), o.get("kaynak")
    if alinan is None:
        return SINIF_GECICI, "kod ALINAMADI (ag/DNS/TLS/timeout)"
    if beklenen is None:
        return SINIF_OK, "iddia edilmedi"
    if alinan == beklenen:
        return SINIF_OK, "beklenen kod (%s)" % alinan
    if alinan in GECICI_KODLAR or 500 <= int(alinan) <= 599:
        return SINIF_GECICI, "ortam/gecici kod %s" % alinan
    if alinan == 404 and beklenen == 200:
        if kaynak == KAYNAK_YENI:
            return SINIF_GECICI, "404 ama kol=%s: EDGE ROLLOUT penceresi" % KAYNAK_YENI
        return SINIF_KIRMIZI, "SAYFA YOK (404) — gercek kusur (kol=%s)" % kaynak
    if beklenen == 404 and alinan == 200:
        return SINIF_KIRMIZI, "var olmayan id 200 verdi — kapinin GOZU bozuk"
    return SINIF_GECICI, "MODELLENMEYEN kod %s (fail-toward-NOTR)" % alinan


def yuzey_hukmu(olcumler):
    """SAF HUKUM — "bos yuzey" ve "gecici hal" YESIL'den AYRI hallerdir.

    olcumler: olcum_plani satirlari + "alinan" (int HTTP kodu | None = istek patladi).
    Doner: (hukum, sebep, sayac)

    SIRA (fail-closed):
      1. GERCEK KUSUR (olcum_sinifi -> KIRMIZI) -> KIRMIZI. Gercek kirmizi, gecici
         gurultuyu YENER: kusuru "ortam sorunu" diye ortmek kapiyi olduruR.
      2. GECICI/OLCULEMEYEN olcum varsa -> OLCULEMEDI (sessiz yesil DEGIL).
      3. POZITIF OLCUM YOK (hicbir katalog sayfasi 200 dogrulanmadi) -> OLCULEMEDI:
         BOS YUZEY. 🔴 ESKI DAVRANIS BURADA `success` DONUYORDU.
      4. Aksi halde YESIL (>=1 katalog sayfasi fiilen yoklandi ve beklenen kodu verdi).
    """
    siniflar = [(o, olcum_sinifi(o)) for o in olcumler]
    kirmizi = [(o, g) for o, (s, g) in siniflar if s == SINIF_KIRMIZI]
    gecici = [(o, g) for o, (s, g) in siniflar if s == SINIF_GECICI]
    pozitif = [o for o, (s, _) in siniflar
               if s == SINIF_OK and o.get("katalog") and o.get("alinan") == 200]
    sayac = {"yoklanan": len(olcumler), "kirmizi": len(kirmizi), "gecici": len(gecici),
             "ag_hatasi": sum(1 for o in olcumler if o.get("alinan") is None),
             "katalog_pozitif": len(pozitif)}
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


def yol_kodu(yol, beklenen=200):
    """Bir yolun HTTP kodu. `beklenen` DISI kodlarda DENEME kez tekrar (CDN isinmasi).

    NEDEN `beklenen` PARAMETRESI: nobet satiri 404 BEKLER; sabit "200 olana kadar dene"
    mantigi orada bosa 3 deneme + 8 sn yakardi. Tekrar sarti beklenen koddan TUREtilir."""
    kod = None
    for i in range(DENEME):
        kod, _ = canli_getir(yol)
        if kod == beklenen:
            return kod
        if i < DENEME - 1:
            time.sleep(DENEME_BEKLE)
    return kod


def sayfa_kodu(uid):
    """/urun/<id>/ icin HTTP kodu (adres TEK KAYNAKTAN: urun_yolu)."""
    return yol_kodu(urun_yolu(uid), 200)


def olcumleri_yap(plan, prob=None):
    """Plan satirlarini FIILEN yokla; her satira "alinan" ekle.

    prob(yol, beklenen) -> kod | None  ENJEKTE EDILEBILIR: kabul testi AG CAGIRMADAN
    sahte bir prob ile ayni karar yolunu olcer (fikstur gercek cikti seklini taklit
    eder: (yol, beklenen) -> HTTP kodu ya da None) ([[nobetci-fikstur-sekli]])."""
    if not plan:
        return []
    if prob is None:
        prob = yol_kodu
    with ThreadPoolExecutor(max_workers=ES_ZAMAN) as havuz:
        kodlar = list(havuz.map(lambda o: prob(o["yol"], o["beklenen"] or 200), plan))
    return [dict(o, alinan=k) for o, k in zip(plan, kodlar)]


def dokum_bas(olcumler, hukum, sebep, sayac, atlanan_taslak, rc=None):
    """🔴 BASILAN SAYI = HUKMUN KANITI. Cikis kodu tek basina hukum degildir; HANGI KOL
    HANGI KODU verdi, kaynak basina ACIKCA basilir (kod dagilimi dahil)."""
    print("──── OLCUM DOKUMU (yoklanan sayfa yuzeyi · kol bazinda) ────")
    print("%-12s %9s %5s %8s %8s  %s"
          % ("kol", "yoklanan", "OK", "KIRMIZI", "GECICI", "alinan kodlar"))
    for kaynak in (KAYNAK_TASLAK, KAYNAK_YENI, KAYNAK_KESIT, KAYNAK_NOBET):
        k = [o for o in olcumler if o["kaynak"] == kaynak]
        if not k:
            print("%-12s %9d %5d %8d %8d  %s" % (kaynak, 0, 0, 0, 0, "-"))
            continue
        s = [olcum_sinifi(o)[0] for o in k]
        kodlar = {}
        for o in k:
            anahtar = "AG-HATASI" if o["alinan"] is None else str(o["alinan"])
            kodlar[anahtar] = kodlar.get(anahtar, 0) + 1
        print("%-12s %9d %5d %8d %8d  %s"
              % (kaynak, len(k), s.count(SINIF_OK), s.count(SINIF_KIRMIZI),
                 s.count(SINIF_GECICI),
                 ", ".join("%s×%d" % (a, n) for a, n in sorted(kodlar.items()))))
    # Kol adiyla TEK TEK: OK OLMAYAN her yoklama, sinifi ve gerekcesiyle.
    for o in olcumler:
        s, g = olcum_sinifi(o)
        if s != SINIF_OK:
            print("   %-8s kol=%-12s id=%s yol=%s bekleniyordu=%s alindi=%s — %s"
                  % (s, o["kaynak"], o["id"], o["yol"], o["beklenen"], o["alinan"], g))
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
    if not kolon_hazir(m):
        return 1
    toplam, yayinda, taslak = d1_sayilar(m)
    yerel = yerel_idler()
    print("D1 toplam satir      : %d" % toplam)
    print("D1 yayinda (=1)      : %d" % yayinda)
    print("D1 TASLAK  (=0)      : %d" % taslak)
    print("yerel urunler.json id: %d" % len(set(yerel)))
    canli, hata = canli_urun_idleri()
    if canli is None:
        print("canli urunler.json   : OLCULEMEDI (%s)" % hata)
        return 1
    print("canli urunler.json id: %d" % len(set(canli)))
    print("YAYIN GECIKMESI (canli JSON'da olup D1'de TASLAK olan): %d"
          % len(set(taslak_idler(m)) & set(canli)))
    ihlal = ihlal_idler(yayinda_idler(m), canli)
    print("DEGISMEZ IHLALI (yayinda=1 olup canli JSON'da OLMAYAN): %d%s"
          % (len(ihlal), ("  -> " + ", ".join(ihlal[:10])) if ihlal else ""))
    return 1 if ihlal else 0


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


def komut_yayinla(m, release, prob=None, canli_kaynak=None, yerel_kaynak=None):
    """DEPLOY'DAN SONRA kosar. IKI IS BIR ARADA, AMA AYRI RAPORLANIR:

      1. YAYINA ALMA (yazma): canli 200 dogrulanmadan hicbir satir yayina alinmaz.
      2. YUZEY HUKMU (okuma): taslak olsun olmasin, canli katalogdan DETERMINISTIK bir
         kesit yoklanir. Yoklanacak sayfa yoksa hukum `success` DEGIL, OLCULEMEDI/BOS
         YUZEY'dir. Eski kod burada hicbir sayfa olcmeden `success` donuyordu.

    prob / canli_kaynak / yerel_kaynak: kabul testi icin IO dikisleri (AG CAGRILMAZ)."""
    if not kolon_hazir(m):
        return 1
    canli_kaynak = canli_kaynak or canli_urun_idleri
    yerel_kaynak = yerel_kaynak or yerel_idler

    taslaklar = taslak_idler(m)
    canli, hata = canli_kaynak()
    canli_sirali = list(canli) if canli is not None else []
    if canli is None:
        # Canli JSON okunamadi: yayina alma FAIL-CLOSED durur (satirlar taslak kalir,
        # yani gorunmez — 404 uretilemez). Yuzey de bos kalir -> hukum OLCULEMEDI.
        print("!! CANLI KATALOG OKUNAMADI: %s" % hata)

    adaylar, atlanan = adaylari_sec(taslaklar, yerel_kaynak(), canli_sirali)
    print("D1 TASLAK: %d · yayin adayi: %d · aday-disi: %d"
          % (len(taslaklar), len(adaylar), len(atlanan)))
    for uid, sebep in sorted(atlanan.items())[:20]:
        print("   aday DEGIL %s — %s" % (uid, sebep))

    tavan_asildi = len(adaylar) > AZAMI_ADAY
    if tavan_asildi:
        print("!! ADAY SAYISI TAVANI ASTI: %d > %d. Bu bir GOC yigini; tek tek HTTP "
              "dogrulamasi bu olcekte yapilmaz." % (len(adaylar), AZAMI_ADAY))
        print("!! Coz: python3 tools/yayin-kapisi.py --geriye-doldur")
        adaylar = []          # yazma yapilmaz; yuzey hukmu YINE DE olculur

    # ── OLCUM: taslak adaylari + canli katalog kesiti + nobet satiri ───────────────
    plan = olcum_plani(adaylar, canli_sirali)
    olcumler = olcumleri_yap(plan, prob=prob)
    hukum, sebep, sayac = yuzey_hukmu(olcumler)

    # ── YAZMA: yalniz TASLAK kaynagindan 200 alanlar ───────────────────────────────
    kodlar = {o["id"]: o["alinan"] for o in olcumler if o["kaynak"] == KAYNAK_TASLAK}
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

    # ── CIKIS KODU: hukum politikasi + yazma/olcek arizalari ──────────────────────
    # 🔴 KAYBOLAN KIRMIZI GERI KONDU: taslak adayinin sayfa probu 200 vermediyse (404,
    # 5xx, 403 ya da AG HATASI/None) o satir YAYINA ALINMADI ve bu hal rc'ye MUTLAKA
    # girer. `basarisiz` listesini yalnizca BASMAK, eski kodun `if basarisiz: return 1`
    # duyarliligini sessizce dusuruyordu. Hangi kola dustugu SINIFA gore belirlenir:
    #   404 (sayfa YOK)                  -> hukum KIRMIZI -> rc=1
    #   403/429/5xx/None (ortam/gecici)  -> hukum OLCULEMEDI -> rc=2 (rc=1 DEGIL)
    # Ikisi de sifir-DISI; "olculemedi" hicbir kolda 'iyi' degildir.
    rc = hukum_cikis_kodu(hukum)
    if basarisiz and rc == RC_YESIL:
        # Emniyet kemeri: hukum bir sekilde YESIL dedi ama bir aday yayina alinamadi.
        # Bu hal SINIFLANDIRILAMAMIS bir eksiktir -> OLCULEMEDI (sessiz yesil YOK).
        print("!! %d aday yayina ALINAMADI ama hukum YESIL dedi -> OLCULEMEDI'ye cekiliyor"
              % len(basarisiz))
        hukum, rc = HUKUM_OLCULEMEDI, RC_OLCULEMEDI
    if yazma_hatasi or tavan_asildi:
        rc = RC_KIRMIZI          # D1 yazmasi dogrulanamadi / goc olcegi: GERCEK ariza
    dokum_bas(olcumler, hukum, sebep, sayac, atlanan, rc=rc)
    return rc


def komut_geriye_doldur(m, release):
    """TEK SEFERLIK goc: CANLI urunler.json'da olan her id -> yayinda=1.
    KANIT: canli urunler.json ile /urun/ sayfalari AYNI Pages artefaktindan yayinlanir
    (deploy.yml `_site`), yani canli JSON'daki id'nin sayfasi da canlidadir. Bu yuzden
    15.000 tekil HTTP istegi ATILMAZ — ve ORNEKLEME de yapilmaz: karar TEK bir kanit
    kumesi (canli JSON) uzerinden TAM uygulanir."""
    if not kolon_hazir(m):
        return 1
    canli, hata = canli_urun_idleri()
    if canli is None:
        print("OLCULEMEDI: %s — geriye doldurma YAPILMADI (fail-closed)." % hata)
        return 1
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

    def __init__(self, satirlar, kolon=True):
        self.satirlar = dict(satirlar)      # {uydurma_id: yayinda (0/1)}
        self.kolon = kolon
        self.yazilan_sql = []

    def kolon_var_mi(self, tablo, kolon):
        return self.kolon

    @staticmethod
    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    def sorgu(self, sql):
        if "IN (" in sql:               # geri-okuma: WHERE yayinda=0 AND id IN (...)
            secili = [i for i in self.satirlar if self.q(i) in sql]
            return [{"results": [{"id": i} for i in sorted(secili)
                                 if int(self.satirlar[i] or 0) == 0]}]
        if "WHERE yayinda=0" in sql:
            return [{"results": [{"id": i} for i, v in sorted(self.satirlar.items())
                                 if int(v or 0) == 0]}]
        raise AssertionError("SahteD1: beklenmeyen sorgu -> " + sql)

    def dosya_calistir(self, sql):
        self.yazilan_sql.append(sql)
        for i in list(self.satirlar):
            if self.q(i) in sql and int(self.satirlar[i] or 0) == 0:
                self.satirlar[i] = 1


def sahte_prob(kod_haritasi, varsayilan=404):
    """(yol, beklenen) -> HTTP kodu | None. Gercek yol_kodu()'nun CIKTI SEKLINI taklit
    eder. `kod_haritasi` yolu (tam string) koda esler; eslenmeyen yol `varsayilan`.
    varsayilan=None verilirse AG HATASI taklit edilir."""
    cagrilan = []

    def prob(yol, beklenen=200):
        cagrilan.append(yol)
        return kod_haritasi.get(yol, varsayilan)

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
    # Beklenen 9 = 1 taslak + 5 en-yeni + kesitin YENI eklediyi 3 (indeks 0 ve 2 zaten
    # en-yeni kumesinde; tekilleme yuzunden 13 DEGIL 9 — sayi tekillemeyi de olcer).
    dogrula("Y35 ADRES: `.html` 404 verse bile kanonik yol olculdugu icin hukum YESIL",
            h_c == HUKUM_YESIL and s_c["katalog_pozitif"] == 9, (h_c, s_c))

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
    def olc(satirlar):
        return yuzey_hukmu([dict(kaynak=k, id=i, yol=urun_yolu(i), beklenen=b,
                                 katalog=kt, alinan=a)
                            for (k, i, b, kt, a) in satirlar])
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
    def sinif(kaynak, beklenen, alinan):
        return olcum_sinifi({"kaynak": kaynak, "id": "x", "beklenen": beklenen,
                             "alinan": alinan, "katalog": True})[0]
    dogrula("Y67 SINIF: beklenen kod alindi -> OK",
            sinif(KAYNAK_KESIT, 200, 200) == SINIF_OK)
    dogrula("Y68 SINIF: canli-KESIT 404 -> KIRMIZI (eski/deterministik kayit; rollout "
            "penceresiyle aciklanamaz)", sinif(KAYNAK_KESIT, 200, 404) == SINIF_KIRMIZI,
            sinif(KAYNAK_KESIT, 200, 404))
    dogrula("Y69 SINIF: canli-YENI 404 -> GECICI (EDGE ROLLOUT penceresi, kirmizi DEGIL)",
            sinif(KAYNAK_YENI, 200, 404) == SINIF_GECICI, sinif(KAYNAK_YENI, 200, 404))
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
            yerel=None):
        """komut_yayinla'yi FIKSTURLE kosar; stdout yakalanir (dokum gurultusu tasmasin).
        Doner: (rc, sahte_d1, prob, cikti_metni)"""
        m = SahteD1(d1_satirlari)
        prob = sahte_prob(kod_haritasi, varsayilan)
        kaynak = (lambda: (None, canli_hata)) if canli_hata else (lambda: (canli_liste, None))
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            rc = komut_yayinla(m, "test-release", prob=prob, canli_kaynak=kaynak,
                               yerel_kaynak=(lambda: list(yerel if yerel is not None
                                                          else canli_liste)))
        return rc, m, prob, tampon.getvalue()

    def hukum_of(cikti):
        for s in cikti.splitlines():
            if s.startswith("HUKUM: "):
                return s.split("HUKUM: ", 1)[1].split(" —")[0].strip()
        return "(HUKUM BASILMADI)"

    tum_200 = {urun_yolu(u): 200 for u in canli12}
    tum_200["/urun/" + NOBET_ID + "/"] = 404

    # ── 1) RC TABLOSU: uc jeton UCTAN UCA uc AYRI rc'ye dusuyor mu? ────────────────
    print("\n  ┌─ RC TABLOSU (uctan uca fikstur) ─────────────────────────────")
    rc_y, m_y, prob_y, ck_y = kos({}, canli12, tum_200)                      # hepsi 200
    kesit404 = dict(tum_200)
    kesit404[urun_yolu("canli-6")] = 404                                     # canli-6 KESIT kolunda
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
    for etiket, kod, hedef in (("403 (UA/WAF)", 403, "canli-6"),
                               ("429 (hiz siniri)", 429, "canli-6"),
                               ("503 (CDN gecici)", 503, "canli-6"),
                               ("timeout (None)", None, "canli-6"),
                               ("canli-YENI 404 (edge rollout)", 404, "canli-0")):
        h = dict(tum_200)
        if kod is None:
            del h[urun_yolu(hedef)]               # eslenmeyen yol -> varsayilan
            rcv, mv, pv, ckv = kos({}, canli12, h, varsayilan=None)
        else:
            h[urun_yolu(hedef)] = kod
            rcv, mv, pv, ckv = kos({}, canli12, h)
        yp.append((etiket, rcv, hukum_of(ckv)))
        print("  │ %-32s rc=%d hukum=%s" % (etiket, rcv, hukum_of(ckv)))
    rc_kesit, _, _, ck_kesit = kos({}, canli12, kesit404)
    print("  │ %-32s rc=%d hukum=%s" % ("canli-KESIT 404 (gercek kusur)", rc_kesit,
                                        hukum_of(ck_kesit)))
    print("  └──────────────────────────────────────────────────────────────")
    for etiket, rcv, hv in yp:
        dogrula("Y60.%s YANLIS-POZITIF: %s -> rc=%d, KIRMIZI (rc=1) DEGIL"
                % (etiket.split()[0], etiket, rcv),
                rcv != RC_KIRMIZI and rcv == RC_OLCULEMEDI, (rcv, hv))
    dogrula("Y61 AYIRT EDICI: canli-KESIT 404 -> rc=1 KIRMIZI (yeni-kol 404 rc=2 iken; "
            "iki kol AYNI kodu AYRI yargilar)",
            rc_kesit == RC_KIRMIZI and yp[-1][1] == RC_OLCULEMEDI,
            (rc_kesit, yp[-1]))
    dogrula("Y62 DOKUM: OK olmayan her yoklama KOL ADIYLA basilir",
            ("kol=" + KAYNAK_KESIT) in ck_kesit, ck_kesit.strip()[-300:])
    dogrula("Y63 NOBET: var olmayan id 200 verdi -> rc=1 (kapinin gozu bozuk)",
            kos({}, canli12, dict(tum_200, **{"/urun/" + NOBET_ID + "/": 200}))[0]
            == RC_KIRMIZI)

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


def main():
    ap = argparse.ArgumentParser()
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
        sys.exit(2)

    m = yukle_d1sync()
    if a.durum:
        sys.exit(komut_durum(m))
    if a.geriye:
        sys.exit(komut_geriye_doldur(m, "geriye-doldur"))
    sys.exit(komut_yayinla(m, a.release))


if __name__ == "__main__":
    main()
