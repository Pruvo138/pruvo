#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN GECIKME NOBETCISI — "canli, main'den NE KADAR geride?".

NEDEN VAR (1 Agu 2026, OLCULDU — bu nobetci bir olayin faturasidir)
====================================================================
Yayin hatti bir kapi yuzunden tikandi ve **20 commit birikene, 6 kosum ust uste
dusene ve canli ~1,5 saat bayatlayana kadar KIMSE FARK ETMEDI**. Fark edilis bicimi
TESADUFTU: parite testi "OLCULEMEDI" dedi, mimar sebebini kovaladi. O gunun kosum
tablosu (son 15 kosum): 3 success / 5 cancelled / 5 failure.

Ikinci risk ayni olcumde gorunur oldu: build ~28 dk surerken push'lar 3-8 dk arayla
geliyor; her yeni BEKLEYEN kosum onceki bekleyeni iptal ediyor. Yeterince sik push
gelirse hicbir kosum tamamlanamaz (**ACLIK**) — hat "kirmizi" bile yanmadan yayin
durur. Yani IKI ayri ariza sinifi var ve ikisi de sessizdir:

    TIKANMA : kosumlar DUSUYOR      (failure zinciri; hat kirmizi ama kimse bakmiyor)
    ACLIK   : kosumlar IPTAL EDILIYOR (cancelled zinciri; hicbiri tamamlanmiyor)

Bu nobetci ikisini de AYRI AYRI olcer ve tek bir soruya sayiyla cevap verir:
"canli yayin, main'in kac commit ve kac dakika gerisinde?"

🔴 "YAYIN INDI MI" IS DUZEYINDE OLCULUR — KOSUM DUZEYINDE DEGIL (1 Agu 2026, OLCULDU)
=====================================================================================
Bu nobetcinin ILK gercek kullaniminda YANLIS ALARM verdigi olculdu: "TIKALI, canli
main'den 3 commit geride, en eski bekleyen 85 dk" dedi; oysa canlinin `last-modified`
damgasi 20:50 idi ve o turda yayinlanan icerik CANLIDA GORUNUYORDU. Sebep: nobetci bir
kosumu "yayinladi" sayarken kosumun GENEL `conclusion`'ina bakiyordu.

Olculen govde (kosum 30716502665, sha aa114660): genel `conclusion` = **failure**,
CUNKU yayini bloklaMAYAN `serit-b` isi dustu. Ayni kosumda:
    build=success · deploy=**success** · yayin=**success**
Yani icerik INMISTI. Ayni gun ikinci ornek: kosum 30715829554 (d4806461) — yine genel
`failure`, yine deploy+yayin success.

Bu depoda `deploy.yml` BILEREK boyle kurulmustur: `serit-b` yayini bloklamaz
([[kapi-birikimi-yayin-gecikmesi]] — bloklayan kapi yayini 1,5 saat durdurdu). Yani
"genel conclusion = failure" bu hatta yayinin inmedigi ANLAMINA GELMEZ ve o alani
yayin kaniti saymak, aracin OLCMEDIGI bir sey hakkinda hukum vermesidir.

Onarim: her tamamlanmis kosum icin `.../actions/runs/<id>/jobs` sorulur ve
    ETKIN SONUC = "success"   <=> `deploy` isinin conclusion'i success
                = "yayinsiz"  <=> kosum success ama `deploy` success DEGIL (or. skipped)
                = kosumun kendi conclusion'i (failure/cancelled/...) aksi halde
Zincirler ve "son basarili yayin" ARTIK bu etkin sonuc uzerinden sayilir.

🔴 KORELME KARSI-OLCUMU (ayni gun, ayni veri): 17:01-17:43 arasi BES ardisik kosumda
`build` DUSTU ve `deploy` HIC KOSMADI (`deploy=skipped`) — 20 commit birikti. Onarimdan
sonra da bu senaryo TIKALI vermek ZORUNDADIR; fikstur `bugun-build-dustu.json` bunun
kanaridir. Iki fikstur bu iki ekseni birbirine kilitler: `bugun-serit-b-dustu.json`
(genel failure ama deploy=success -> AKIYOR) ve `bugun-build-dustu.json`
(genel failure, deploy=skipped -> TIKALI).

⚖️ `deploy` MI `yayin` MI YETKILIDIR: SITEYI canliya koyan is `deploy`'dur; `yayin` isi
deploy'dan SONRA kosar ve D1'deki taslaklari yayina alir ([[ege-d1-bagimliligi]]).
`yayin` duserse SITE CANLIDIR ama Ege yeni urunleri goremez. Bu yuzden "canli, main'in
kac commit gerisinde" sorusunun yetkilisi `deploy`'dur; `yayin` isinin sonucu OLCULUR ve
raporda AYRI bir bozulma satiri olarak GORUNUR — ama site tazeligi hakkinda hukum
vermez (aksi halde "site canli" iken TIKALI diyen YENI bir yanlis alarm sinifi dogardi).

IS SORGUSU BUTCESI (olculdu 1 Agu 2026): kosum listesi 1,7 sn · her `jobs` cagrisi
ort. 1,0 sn. Tarama ILK yayinlayan kosumda DURUR -> saglikli halde 1 ek cagri. Tavan
IS_SORGU_TAVANI=8 (=> ~9,7 sn ust sinir); tavana dayanilmasi zaten 8 ardisik
yayinlaMAYAN kosum demektir ve o hal her esigin USTUNDEDIR (TIKALI/ACLIK).

🔴 BAGIMSIZLIK — NEDEN CI'DA KOSMAZ
===================================
Bir yayin-gecikme nobetcisi YALNIZ CI icinde kosarsa, hat tikandigi anda O DA KOSAMAZ:
tam ihtiyac duyuldugu dakikada susar. Bu yuzden:
  * ELLE kosulur   : python3 tools/yayin-gecikme-nobeti.py
  * PANODA gorunur : tools/durum.py bolum 9 (pano zaten her oturum basi okunur)
  * deploy.yml'e BAGLANMAZ. deploy.yml'de yalniz bu dosyanin AGSIZ fikstur kabulu
    (`--kendini-test`) kosar — olcumun kendisi degil. Boylece nobetci, olctugu
    hattin saglikli olmasina BAGIMLI DEGILDIR ve bu betik hicbir kosulda yayini
    BLOKLAYAMAZ (bir kapi degil, bir NOBETCI'dir).

🔴 AG YOKSA YESIL DEME — VE TERSINI DE YAPMA
============================================
`gh` yoksa, yetki yoksa, API hata verirse ya da govde anlasilamazsa sonuc
**OLCULEMEDI**'dir (rc 2): YESIL DEGIL. Ama bu ev bunun TERSINI de olctu — bir kapi
"olculemedi"yi KIRMIZI sayip yayini 1,5 saat tikadi. O yuzden OLCULEMEDI burada:
  * asla "AKIYOR" uretmez (rc 0 vermez),
  * ama bir KAPI degildir: hicbir is akisini bloklamaz, panoda ⚪ olarak gorunur.

🔴 YAS TABANI KOSUMUN BASLANGICI DEGIL, YAYIN ANIDIR (2 Agu 2026, OLCULDU)
==========================================================================
Ilk hal tabani `son_basarili.run_started_at` (kosumun BASLADIGI an) aliyordu. Oysa
kosum baslar, ~24 dk build kosar ve ancak ondan SONRA yayinlar: olculen ornek — kosum
30750470532 13:41:34'te BASLADI, `deploy` isi 14:29:21'de BITTI (47,8 dk fark). Taban
baslangic olunca bir sonraki dongunun yasi, olcum baslamadan ONCE, onceki kosumun TUM
suresini tasiyor: yapisal alt sinir ~ (onceki kosum suresi + mevcut kosum suresi).

Olculen fatura (2 Agu, 40 yayin dongusu, ~27 saat — asagidaki taban olcumunun ta kendisi):
    ESKI taban (run_started_at) : ortanca 46,0 · p90 75,0 · max 491,7 dk
    YENI taban (yayin ani)      : ortanca 25,0 · p90 43,7 · max 464,5 dk
Ayni gunun en keskin ornegi: kosum 30747898143 dongusu ESKI tabanla 75,0 dk (= o gunun
TIKALI esigi, KIRMIZI), YENI tabanla 26,6 dk (YESIL). Hat bozuk DEGILDI. Fikstur
`bugunku-kuyruk-saglikli.json` bu dongunun GERCEK govdesidir ve bu ekseni kilitler.

Taban artik `deploy` isinin `completed_at`'idir: siteyi canliya koyan is bittiginde
icerik INMISTIR; o andan onceki bekleme o dongunun degil, ONCEKI dongunun hesabidir.

🔴 TABAN DUZELMESI BIR EKSENI KORELTIR — O YUZDEN IKINCI EKSEN VAR
==================================================================
Yas her yayinda sifirlanmaya basladigi icin "kosum BASLADI ama HIC BITMIYOR" sinifi
zayiflar; ustelik yas ekseninin TAMAMI `ahead_by > 0` kapisinin ARKASINDADIR (bekleyen
commit yoksa yas hic olculmez). Yani takilan bir kosum, bekleyen icerik olmadigi surece
yas ekseninde SONSUZA KADAR gorunmez.

Bu yuzden AYRI bir eksen olculur: KOSUM OMUR TAVANI — tamamlanmamis (kosan/bekleyen) bir
kosumun `run_started_at`'tan bu yana gecen omru. Bu eksen `ahead_by` kapisinin ONUNDEDIR
ve yas ekseninden BAGIMSIZ hukum verir; ikisi ayni siniftan (TIKALI) olsa bile gerekce
satirlari AYRIDIR ve `olcum["eksenler"]` her ekseni TEK BASINA raporlar
([[hukum-yanlis-birimde]]: toplu sonuc tekil ekseni gizlemesin).

ESIKLER — HEPSI 2 Agu 2026 OLCUMUNDEN (son 100 deploy kosumu, ~27 saat)
=======================================================================
Olculen taban (99 tamamlanmis kosum · 41 yayin (`deploy`=success) · 40 dongu):
  * YAYIN ANI TABANLI dongu yasi (n=40): min 18,9 · ortanca 25,0 · p90 43,7 dk.
    Kuyrugun tamami: 51,8 (17 commit'lik patlama) · 70,0 ve 76,9 (1 Agu'nun IKI GERCEK
    tikanmasi) · 464,5 (gece boyu push gelmeyen pencere — bkz. asagidaki kalinti sinif).
    Yani SAGLIKLI tepe 51,8'de biter, GERCEK olaylar 70 dk'dan baslar.
  * KOSUM OMRU (tamamlanmis 99 kosumun `updated_at - run_started_at`'i):
    ortanca 13,0 · p90 36,8 · max 49,1 dk. `build` isi (41 yayinlayan kosum):
    ortanca 22,6 · p90 23,5 · max 25,2 dk.
  * ZINCIR dagilimi (1 Agu olcumu, DEGISMEDI): IPTAL zincirleri [5,4,3,3,3,2,...] — 6 ve
    ustu HIC gorulmedi. HATA zincirleri [10,5,3,2,1,...] — 4 ve ustu yalniz IKI kez,
    ikisi de gercek tikanma.

Secilen degerler ve TEK CUMLE gerekceleri:
  GECIKME_YAS_DK   = 50  — olculen SAGLIKLI tepenin (51,8) hemen ALTI, p90'in (43,7)
                           USTU: UYARI seviyesi, alarm degil (40 dongunun 4'u asar).
  TIKALI_YAS_DK    = 65  — saglikli tepenin (51,8) USTUNDE, olculen GERCEK olaylarin
                           (70,0 · 76,9) ALTINDA: 40 dongunun 3'u asar, ucu de gercek
                           olay ya da beyan edilmis kalinti siniftir.
  KOSUM_OMUR_TAVANI_DK = 75 — olculen EN UZUN kosum omrunun (49,1 dk) ~1,5 kati ve
                           olculen en uzun `build` isinin (25,2 dk) ~3 kati: bu deponun
                           OLCULEN geometrisiyle (tek bekleyen kuyruk + ~25 dk build)
                           aciklanamaz. 99 kosumun HICBIRI bu esige yaklasmadi.
  TIKALI_HATA_ZINCIR = 4 — olculen gurultu tavani 3 ardisik hata; gercek tikanmalar 5 ve
                           10 zincirdi.
  ACLIK_IPTAL_ZINCIR = 6 — 23 saatte olculen EN UZUN saglikli iptal zinciri 5; eszamanlilik
                           iptali NORMAL bir olaydir, alarm ancak zincir tavani asinca dogar.
  GECIKME_BIRIKME    = 12 — olculen dongu basi birikme: ortanca 3 · p90 7 · max 17;
                           12 saglikli p90'in cok ustu, olculen tepenin altidir.

🔴 BEYAN EDILMIS KALINTI SINIF (olculdu, ONARILMADI): gece boyu push gelmeyen pencerede
(00:57 -> 08:41) sabah gelen commit'ler `--ff-only` ile ESKI committer tarihi tasidi ve
taban da 7,7 saat oncesinin yayin aniydi -> yas 464,5 dk. ESKI tabanda da 491,7 idi, yani
bu bir GERILEME DEGIL; kalan bir siniftir ve TIKALI yakar. Onarimi ayri bir tur isidir
(taban ucuncu bir alt sinir daha ister: "kosum tetikleyen push'un GELDIGI an").

🔴 TEK IPTAL ALARM DEGILDIR. Eszamanlilik iptali bu depoda BILINCLI bir tasarimin
(`cancel-in-progress: false` + tek bekleyen kuyrugu) normal sonucudur. ACLIK ancak
iptaller ART ARDA gelip HICBIR kosum tamamlanmayinca dogar — ve tek basina zincir de
yetmez, ayrica BEKLEYEN ICERIK yaslanmis olmalidir (zincir >= 6 VE yas >= 45 dk).
Fikstur `iptal-firtinasi-taze.json` bu ayrimin kanaridir: 6 ardisik iptal ama taze
yayin -> AKIYOR (alarm YOK).

🔴 ALARMLARIN HEPSI "BEKLEYEN ICERIK VAR MI" KAPISININ ARKASINDADIR. `ahead_by == 0`
ise canli main'in TA KENDISIDIR; kosum zincirleri ne olursa olsun sonuc AKIYOR
(fikstur `guncel-hic-bekleyen-yok.json`).

YAS NASIL OLCULUR (ve neden TABANLANIR)
=======================================
    yayin_ani          = son_basarili kosumun `deploy` isinin `completed_at`'i
    bekleme_baslangici = max(en_eski_bekleyen_commit_tarihi, yayin_ani)
    yas_dk             = simdi - bekleme_baslangici
Taban SART: bu depoda dallar `--ff-only` ile alinir ve commit'ler ORIJINAL committer
tarihini tasir. Tabansiz olcum, saatler once bir worktree'de yazilip bugun alinan bir
commit'i "saatlerdir bekliyor" sayar -> yanlis alarm. Bir commit son yayindan ONCE
bekliyor OLAMAZ (bekliyor olsaydi o yayinda inerdi), o yuzden taban YAYIN ANIDIR.
(Kosumun BASLANGICI degil: aradaki fark bu hatta 47,8 dk olcuLDU — bkz. yukarida.)

KOSUM OMRU NASIL OLCULUR (EKSEN 2)
==================================
    omur_dk = simdi - kosum.run_started_at        # YALNIZ status != "completed" kosumlar
    takilan = bu omurlerin EN BUYUGU
Tamamlanmis kosum bu ekseni ilgilendirmez (bitti = takilmadi). Kuyrukta BEKLEYEN kosum da
sayilir ve bu BILEREK boyledir: `cancel-in-progress: false` kuyrugunda sonsuza kadar
bekleyen bir kosum da "yayin inmiyor" demektir; olculen en uzun kosum omru (49,1 dk)
KUYRUK BEKLEMESINI ZATEN ICERIR, esik onun uzerinden secilmistir.

SINIFLAR ve CIKIS KODLARI (rc)
==============================
    AKIYOR      0   bekleyen yok ya da esiklerin altinda
    GECIKME     1   birikme var, hat calisiyor (UYARI)
    OLCULEMEDI  2   olculemedi — YESIL DEGIL, KIRMIZI DA DEGIL (fail-closed teshis)
    TIKALI      3   kosumlar dusuyor / icerik esigin uzerinde bayat
    ACLIK       4   kosumlar ust uste iptal, hicbiri tamamlanmiyor
Kodlar BILEREK ayridir: "olculemedi" hicbir kabuk kosulunda "yesil" ile karismaz.

KULLANIM
========
    python3 tools/yayin-gecikme-nobeti.py               # canli olcum (gh gerekir)
    python3 tools/yayin-gecikme-nobeti.py --kendini-test # AGSIZ fikstur kabulu
    python3 tools/yayin-gecikme-nobeti.py --fikstur bugun-tikali
    python3 tools/yayin-gecikme-nobeti.py --liste        # fiksturleri listeler
"""
import argparse
import copy
import datetime
import glob
import json
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
FIKSTUR_DIZIN = os.path.join(TOOLS, "fikstur", "yayin-gecikme")
SEKIL_CAPASI = os.path.join(FIKSTUR_DIZIN, "sekil-capasi.json")

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"
IS_AKISI = "deploy.yml"
DAL = "main"

# Pencere: olculen en uzun hata zinciri 10, en uzun iptal zinciri 5 idi; 40 tamamlanmis
# kosum ~10 saatlik trafigi kapsar -> zincirler pencereye SIGAR (pencere kenarina
# dayanan zincir raporda ILAN EDILIR).
PENCERE_KOSUM = 40

GECIKME_YAS_DK = 50
TIKALI_YAS_DK = 65
TIKALI_HATA_ZINCIR = 4
ACLIK_IPTAL_ZINCIR = 6
GECIKME_BIRIKME = 12

# 🔴 EKSEN 2 — KOSUM OMUR TAVANI (dk). "Kosum basladi ama HIC bitmiyor" sinifinin TEK
# olcusu budur ve `ahead_by` kapisinin ONUNDEDIR (bkz. baslik). Sayinin GELDIGI YER:
# 2 Agu 2026 olcumunde 99 tamamlanmis kosumun EN UZUNU 49,1 dk surdu (kuyruk beklemesi
# DAHIL), `build` isinin en uzunu 25,2 dk idi. 75 = 49,1 x ~1,5 = 25,2 x ~3 -> olculen
# geometriyle aciklanamayan omur. Sihirli sabit DEGIL: asagidaki OLCULEN_* tavanlar
# sozlesme nobetiyle bu esigin ALTINDA kalmak zorundadir.
KOSUM_OMUR_TAVANI_DK = 75

# 🔴 OLCULEN SAGLIKLI TAVANLAR (zincirler: 1 Agu 2026 / 100 kosum · omur+yas: 2 Agu 2026 /
# 100 kosum — bkz. baslik "ESIKLER"). Esikler bu tavanlarin USTUNDE olmak ZORUNDADIR:
# altina cekilen bir esik NORMAL eszamanlilik iptallerine, gurultu hatalarina ya da
# NORMAL SUREN bir kosuma alarm verir (yanlis alarm = kapatilan nobetci). Sozlesme
# nobeti bunu `kendini_test` icinde olcer; fikstur kanarilari
# `iptal-zinciri-bayat-saglikli.json` (zincir) ve `takilan-kosum-normal.json` (omur).
OLCULEN_SAGLIKLI_IPTAL_TAVANI = 5
OLCULEN_SAGLIKLI_HATA_TAVANI = 3
OLCULEN_KOSUM_OMRU_MAX_DK = 49.1
OLCULEN_SAGLIKLI_YAS_TAVANI_DK = 51.8

# GitHub `conclusion` degerleri: hangisi "dustu" sayilir.
HATA_SONUCLARI = ("failure", "startup_failure", "timed_out", "action_required")
# "completed" DISI her status kosumun HALA CALISTIGI/BEKLEDIGI anlamina gelir; zincir
# sayiminda ATLANIR (kanit degil) ama raporda sayilir.
TAMAMLANDI = "completed"

# 🔴 YAYIN YETKILISI: siteyi canliya koyan is (deploy.yml :: jobs.deploy). "Yayin indi
# mi" YALNIZ bunun is-duzeyi sonucundan okunur; kosumun genel conclusion'indan DEGIL
# (modul basligindaki olcum). TASLAK_ISI (jobs.yayin) deploy'dan sonra kosar, OLCULUR
# ve raporda ayri satir olarak gorunur — site tazeligi hakkinda hukum VERMEZ.
YAYIN_ISI = "deploy"
TASLAK_ISI = "yayin"
# Is objesinde OKUNAN alanlar — biri yoksa OLCULEMEDI (fail-closed sekil dogrulamasi).
# `completed_at` YAS TABANIDIR (yayin ani): alani listeden dusurmek tabani sessizce
# kaybettirir, o yuzden sekil sozlesmesinde durur.
IS_ZORUNLU = ("name", "status", "conclusion", "completed_at")
# Tarama ilk yayinlayan kosumda DURUR; tavan yalnizca butce sinuridir (bkz. baslik).
IS_SORGU_TAVANI = 8

SINIF_RC = {"AKIYOR": 0, "GECIKME": 1, "OLCULEMEDI": 2, "TIKALI": 3, "ACLIK": 4}
SINIF_ISARET = {"AKIYOR": "🟢", "GECIKME": "🟡", "OLCULEMEDI": "⚪",
                "TIKALI": "🔴", "ACLIK": "🔴"}

# Kosum objesinde OKUNAN alanlar — biri yoksa OLCULEMEDI (fail-closed sekil dogrulamasi).
KOSUM_ZORUNLU = ("id", "status", "conclusion", "created_at", "run_started_at",
                 "updated_at", "head_sha", "event")


class OlcumHatasi(Exception):
    """Veri cekilemedi / anlasilamadi -> YESIL degil, OLCULEMEDI (rc 2)."""


# ---------------------------------------------------------------- zaman
def _iso(metin, ne="zaman damgasi"):
    if not isinstance(metin, str) or not metin:
        raise OlcumHatasi("%s okunamadi (bos/yanlis tur: %r)" % (ne, metin))
    ham = metin.strip()
    if ham.endswith("Z"):
        ham = ham[:-1] + "+00:00"
    try:
        d = datetime.datetime.fromisoformat(ham)
    except ValueError:
        raise OlcumHatasi("%s cozulemedi: %r" % (ne, metin))
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return d.astimezone(datetime.timezone.utc)


def _simdi():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------- API
def kosum_yolu(depo=None, is_akisi=None, dal=DAL, pencere=None):
    return ("repos/%s/actions/workflows/%s/runs?branch=%s&per_page=%d"
            % (depo or DEPO, is_akisi or IS_AKISI, dal,
               PENCERE_KOSUM if pencere is None else pencere))


def karsilastirma_yolu(taban, dal=DAL, depo=None):
    return "repos/%s/compare/%s...%s" % (depo or DEPO, taban, dal)


def is_yolu(kosum_id, depo=None):
    return "repos/%s/actions/runs/%s/jobs?per_page=100" % (depo or DEPO, kosum_id)


# `gh` stderr'i -> SABIT sinif etiketi. Anahtarlar kucuk harfe cevrilmis metinde ARANIR.
# Sira ONEMLI DEGIL: eslesen TUM siniflar bildirilir (biri digerini gizlemesin).
GH_HATA_SOZLUGU = (
    ("http 401", "yetkisiz (401)"),
    ("http 403", "yasak ya da kota (403)"),
    ("http 404", "bulunamadi (404)"),
    ("http 422", "islenemedi (422)"),
    ("http 5", "sunucu hatasi (5xx)"),
    ("rate limit", "kota siniri"),
    ("gh auth login", "oturum yok"),
    ("authentication", "kimlik dogrulanamadi"),
    ("could not resolve", "ag/DNS"),
    ("connection refused", "ag/baglanti"),
    ("timeout", "zaman asimi"),
)


def gh_hata_sinifi(ham):
    """`gh` stderr'ini SINIFA cevirir — HAM METIN DISARI CIKMAZ.

    NEDEN (olculdu): eski hal `hata[0][:160]` ile `gh`'in kendi stderr'ini oldugu gibi
    panoya basiyordu. Sentetik bir `gh` ile olculdu: URL/yol tasiyan bir hata metni
    oldugu gibi yakalanip panoya dusuyor ve pano "sir/kimlik bicimli dizgi basmasin"
    nobetini KIRIYOR (bu ev bu tuzaga iki kez dustu). Gercek `gh` dort senaryoda URL
    basmadi — yani sizinti bugun TEORIK; ama gecirgenlik gercek.

    Cikan bilgi: SABIT sozlukten gelen sinif etiketi (teshis KORUNUR) + olculen bayt
    sayisi. Hicbir kosulda cagrilan URL, jeton ya da yol basilmaz.
    """
    metin = (ham or "").strip()
    d = metin.lower()
    siniflar = []
    for anahtar, ad in GH_HATA_SOZLUGU:
        if anahtar in d and ad not in siniflar:
            siniflar.append(ad)
    if siniflar:
        return " · ".join(siniflar)
    if not metin:
        return "(cikti yok)"
    return "taninmayan hata metni (%d bayt — ICERIK BASILMAZ)" % len(metin)


def api_getir(yol, zaman_asimi=25, etiket="api"):
    """`gh api <yol>` -> JSON. HER ariza OlcumHatasi'dir (sessiz yesil YOK).

    `etiket`: cagri YERINI soyleyen SABIT dizgi (`runs` / `jobs` / `compare`), CAGRI
    YERINDE verilir. Yoldan DESENLE turetilMEZ. Gerekcesi olculdu: gercek `gh` ucuncu
    farkli uc icin de ayni metni basiyor (`gh: Not Found (HTTP 404)`), dolayisiyla
    etiket olmadan kirmizi yandiginda HANGI cagrinin dustugu anlasilmiyordu.
    """
    try:
        p = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", yol],
                           capture_output=True, text=True, timeout=zaman_asimi)
    except FileNotFoundError:
        raise OlcumHatasi("`gh` bulunamadi (PATH'te yok) — GitHub Actions durumu "
                          "sorulamadi [%s]" % etiket)
    except subprocess.TimeoutExpired:
        raise OlcumHatasi("`gh api` [%s] %d sn icinde yanit vermedi" % (etiket, zaman_asimi))
    if p.returncode != 0:
        raise OlcumHatasi("`gh api` [%s] rc=%d: %s"
                          % (etiket, p.returncode, gh_hata_sinifi(p.stderr or p.stdout)))
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise OlcumHatasi("`gh api` [%s] govdesi JSON degil (%d bayt)"
                          % (etiket, len(p.stdout or "")))


# ---------------------------------------------------------------- sekil dogrulama
def _sozluk(govde, ne):
    if not isinstance(govde, dict):
        raise OlcumHatasi("%s: sozluk bekleniyordu, %s geldi" % (ne, type(govde).__name__))
    return govde


def kosumlari_ayikla(govde):
    """API govdesinden kosum listesi — sekil FAIL-CLOSED dogrulanir."""
    g = _sozluk(govde, "kosum listesi govdesi")
    if "workflow_runs" not in g:
        raise OlcumHatasi("govdede `workflow_runs` YOK — API sekli degismis olabilir")
    kosumlar = g["workflow_runs"]
    if not isinstance(kosumlar, list):
        raise OlcumHatasi("`workflow_runs` liste degil (%s)" % type(kosumlar).__name__)
    if not kosumlar:
        raise OlcumHatasi("`workflow_runs` BOS — hicbir deploy kosumu gorulmedi; "
                          "bu bir yargi degil, olcum yoklugudur")
    for i, k in enumerate(kosumlar):
        _sozluk(k, "kosum[%d]" % i)
        eksik = [a for a in KOSUM_ZORUNLU if a not in k]
        if eksik:
            raise OlcumHatasi("kosum[%d] alanlari EKSIK: %s (API sekli degismis olabilir)"
                              % (i, ", ".join(eksik)))
    # Yeniden eskiye: API zaten boyle dondurur, yine de KENDIMIZ siralariz.
    return sorted(kosumlar, key=lambda k: _iso(k["created_at"], "created_at"), reverse=True)


def karsilastirmayi_ayikla(govde):
    """compare govdesi -> (geride, en_eski_bekleyen_tarih, kirpildi_mi)."""
    g = _sozluk(govde, "karsilastirma govdesi")
    for a in ("ahead_by", "commits", "total_commits"):
        if a not in g:
            raise OlcumHatasi("karsilastirma govdesinde `%s` YOK — API sekli degismis "
                              "olabilir" % a)
    geride = g["ahead_by"]
    if not isinstance(geride, int) or geride < 0:
        raise OlcumHatasi("`ahead_by` sayi degil: %r" % (geride,))
    commits = g["commits"]
    if not isinstance(commits, list):
        raise OlcumHatasi("`commits` liste degil (%s)" % type(commits).__name__)
    if geride == 0:
        return 0, None, False
    if not commits:
        raise OlcumHatasi("`ahead_by`=%d ama `commits` BOS — govde kendi icinde tutarsiz"
                          % geride)
    ilk = _sozluk(commits[0], "commits[0]")
    try:
        tarih = ilk["commit"]["committer"]["date"]
    except (KeyError, TypeError):
        raise OlcumHatasi("commits[0].commit.committer.date YOK — API sekli degismis "
                          "olabilir")
    # compare en fazla 250 commit dondurur: uzerinde yas ALTTAN olculur, ILAN EDILIR.
    return geride, _iso(tarih, "commits[0] committer.date"), geride > len(commits)


# ---------------------------------------------------------------- is (job) duzeyi
def isleri_ayikla(govde, kosum_id):
    """jobs govdesi -> ({is adi: conclusion}, {is adi: completed_at}). FAIL-CLOSED.

    IKI sozluk doner cunku iki AYRI soru sorulur ve karistirilmalari sessiz hatadir:
      conclusion  -> "yayin INDI mi"      (etkin_sonuc)
      completed_at-> "yayin NE ZAMAN indi" (yas tabani)

    BOS liste MESRUDUR ve olculmustur: bekleme kuyrugunda iptal edilen kosumlarda hic
    is yaratilmaz (`total_count: 0`) -> o kosum hicbir sey yayinlamamistir.
    """
    g = _sozluk(govde, "is listesi govdesi (kosum %s)" % kosum_id)
    if "jobs" not in g:
        raise OlcumHatasi("is govdesinde `jobs` YOK (kosum %s) — API sekli degismis "
                          "olabilir" % kosum_id)
    isler = g["jobs"]
    if not isinstance(isler, list):
        raise OlcumHatasi("`jobs` liste degil (%s, kosum %s)"
                          % (type(isler).__name__, kosum_id))
    cikti, bitisler = {}, {}
    for i, j in enumerate(isler):
        _sozluk(j, "kosum %s is[%d]" % (kosum_id, i))
        eksik = [a for a in IS_ZORUNLU if a not in j]
        if eksik:
            raise OlcumHatasi("kosum %s is[%d] alanlari EKSIK: %s (API sekli degismis "
                              "olabilir)" % (kosum_id, i, ", ".join(eksik)))
        if j.get("status") == TAMAMLANDI:
            cikti[str(j["name"])] = j["conclusion"]
            bitisler[str(j["name"])] = j["completed_at"]
    return cikti, bitisler


def etkin_sonuc(kosum, isler):
    """Kosumun YAYIN acisindan ETKIN sonucu (modul basligindaki olcum).

    Kosumun genel `conclusion`'i bu hatta yayin kaniti DEGILDIR: bloklaMAYAN bir isin
    (serit-b) dusmesi kosumu `failure` yapar, deploy+yayin basariyla kosmus olsa bile.
    """
    if isler.get(YAYIN_ISI) == "success":
        return "success"
    kosum_sonucu = kosum.get("conclusion")
    if kosum_sonucu == "success":
        # Kosum yesil ama SITEYI koyan is basarili degil (or. `skipped`): bu ne bir
        # yayindir ne de bir hata zinciri halkasidir -> kendi sinifi.
        return "yayinsiz"
    return kosum_sonucu


def yayin_taramasi(kosumlar, is_getir, tavan=IS_SORGU_TAVANI):
    """Tamamlanmis kosumlari YENIDEN geriye tarar, ILK YAYINLAYAN kosumda DURUR.

    Doner: (etkin_sonuclar, son_yayinlayan, son_isleri, son_bitisleri, taranan,
    tavana_dayandi). `etkin_sonuclar` taranan onekle AYNI sirada; zincirler bu onekten
    sayilir (bir zincir yayinlayan kosumu ASAMAZ, o yuzden onek yeterlidir).
    """
    etkin, son, son_isler, son_bitisler = [], None, None, None
    taranan, tavana_dayandi = 0, False
    for k in kosumlar:
        if k.get("status") != TAMAMLANDI:
            continue
        if taranan >= tavan:
            tavana_dayandi = True
            break
        isler, bitisler = isleri_ayikla(is_getir(k), k.get("id"))
        taranan += 1
        if k.get("conclusion") == "success" and YAYIN_ISI not in isler:
            # Kosum yesil ama bekledigimiz is ADI govdede HIC yok -> is akisinin
            # sekli degismis olabilir. Sessizce "yayinlamadi" saymak SAHTE KIRMIZI
            # uretirdi; bu bir yargi degil, olcum yoklugudur.
            raise OlcumHatasi("kosum %s YESIL ama `%s` isi govdede YOK (goruldu: %s) — "
                              "is akisi is adlari degismis olabilir"
                              % (k.get("id"), YAYIN_ISI,
                                 ", ".join(sorted(isler)) or "hic is yok"))
        e = etkin_sonuc(k, isler)
        etkin.append(e)
        if e == "success":
            son, son_isler, son_bitisler = k, isler, bitisler
            break
    return etkin, son, son_isler, son_bitisler, taranan, tavana_dayandi


def takilan_kosum(kosumlar, simdi):
    """EKSEN 2: en uzun suredir TAMAMLANMAMIS kosumun (omur_dk, id)'si — yoksa (None, None).

    Yalniz `status != "completed"` kosumlar sayilir. Bu eksen `ahead_by` kapisinin
    ONUNDEDIR (bkz. modul basligi): bekleyen commit olmasa da takilan kosum bir arizadir.
    """
    en_omur, en_id = None, None
    for k in kosumlar:
        if k.get("status") == TAMAMLANDI:
            continue
        basladi = _iso(k.get("run_started_at"), "run_started_at (kosum %s)" % k.get("id"))
        omur = max(0.0, (simdi - basladi).total_seconds() / 60.0)
        if en_omur is None or omur > en_omur:
            en_omur, en_id = omur, k.get("id")
    return en_omur, en_id


# ---------------------------------------------------------------- zincirler
def zincirler(kosumlar, etkin):
    """(ardisik_iptal, ardisik_hata, tamamlanan, calisan).

    Zincirler YALNIZ tamamlanmis kosumlarin ETKIN sonuclari uzerinde, EN YENIDEN geriye
    sayilir ve ilk FARKLI sonucta DURUR. Kosan/bekleyen kosum kanit degildir -> atlanir.
    """
    tamam = [k for k in kosumlar if k.get("status") == TAMAMLANDI]
    calisan = len(kosumlar) - len(tamam)

    def zincir(kume):
        n = 0
        for e in etkin:
            if e in kume:
                n += 1
            else:
                break
        return n

    return zincir(("cancelled",)), zincir(HATA_SONUCLARI), len(tamam), calisan


# ---------------------------------------------------------------- olcum
def olc(getir=api_getir, simdi=None, depo=None, dal=DAL):
    """Ham olcum sozlugu. HER ariza OlcumHatasi ile yukari cikar (fail-closed)."""
    simdi = simdi or _simdi()
    kosumlar = kosumlari_ayikla(getir(kosum_yolu(depo=depo, dal=dal), etiket="runs"))

    def is_getir(k):
        return getir(is_yolu(k.get("id"), depo=depo), etiket="jobs")

    (etkin, son_basarili, son_isler, son_bitisler,
     taranan, tavana_dayandi) = yayin_taramasi(kosumlar, is_getir)
    ardisik_iptal, ardisik_hata, tamamlanan, calisan = zincirler(kosumlar, etkin)
    takilan_dk, takilan_id = takilan_kosum(kosumlar, simdi)

    olcum = {
        "simdi": simdi,
        "pencere": len(kosumlar),
        "tamamlanan": tamamlanan,
        "calisan": calisan,
        "taranan": taranan,
        "is_tavanina_dayandi": tavana_dayandi,
        "ardisik_iptal": ardisik_iptal,
        "ardisik_hata": ardisik_hata,
        "son_basarili_sha": None,
        "son_basarili_baslangic": None,
        "son_basarili_bitis": None,
        "yayin_ani": None,
        "taslak_isi": None,
        "geride": None,
        "yas_dk": None,
        "kirpildi": False,
        # EKSEN 2 — yas ekseninden BAGIMSIZ olculur, `ahead_by` kapisinin ONUNDE.
        "takilan_kosum_dk": takilan_dk,
        "takilan_kosum_id": takilan_id,
        "zincir_pencere_kenarinda": (tavana_dayandi
                                     or ardisik_iptal >= tamamlanan
                                     or ardisik_hata >= tamamlanan),
    }
    if son_basarili is None:
        return olcum

    olcum["son_basarili_sha"] = str(son_basarili["head_sha"])[:8]
    olcum["son_basarili_baslangic"] = _iso(son_basarili["run_started_at"], "run_started_at")
    olcum["son_basarili_bitis"] = _iso(son_basarili["updated_at"], "updated_at")
    # YAS TABANI: `deploy` isinin BITISI = icerigin CANLIYA INDIGI an (bkz. modul basligi).
    # Alan bos/None ise bu bir yargi degil, OLCUM YOKLUGUDUR -> OLCULEMEDI.
    yayin_ani_ham = (son_bitisler or {}).get(YAYIN_ISI)
    if not yayin_ani_ham:
        raise OlcumHatasi("kosum %s `%s` isi BASARILI ama `completed_at` YOK/bos — yayin "
                          "ani okunamadi, yas tabansiz kalirdi"
                          % (son_basarili.get("id"), YAYIN_ISI))
    olcum["yayin_ani"] = _iso(yayin_ani_ham, "`%s` isi completed_at" % YAYIN_ISI)
    # `yayin` isi OLCULUR ama site tazeligi hakkinda hukum VERMEZ (bkz. modul basligi).
    olcum["taslak_isi"] = (son_isler or {}).get(TASLAK_ISI)

    geride, en_eski, kirpildi = karsilastirmayi_ayikla(
        getir(karsilastirma_yolu(son_basarili["head_sha"], dal=dal, depo=depo),
              etiket="compare"))
    olcum["geride"] = geride
    olcum["kirpildi"] = kirpildi
    if geride > 0:
        # TABAN: bir commit son YAYINDAN once bekliyor olamaz (bekliyorsa o yayinda inerdi).
        # Kosumun BASLANGICI DEGIL — aradaki fark bu hatta 47,8 dk olculdu.
        baslangic = max(en_eski, olcum["yayin_ani"])
        olcum["yas_dk"] = max(0.0, (simdi - baslangic).total_seconds() / 60.0)
    else:
        olcum["yas_dk"] = 0.0
    return olcum


# ---------------------------------------------------------------- yargi
# Sinif AGIRLIGI (yalniz yargi birlestirme icin). SINIF_RC'den TURETILMEZ: orada
# OLCULEMEDI (2) TIKALI (3) ile GECIKME (1) ARASINDA durur ve bir agirlik SIRASI degildir.
SINIF_AGIRLIK = {"AKIYOR": 0, "GECIKME": 1, "TIKALI": 2, "ACLIK": 3}


def eksen_hukumleri(olcum):
    """HER EKSEN AYRI AYRI, TEK KANONIK YERDE olculur -> {eksen adi: bool}.

    🔴 IKIZ TANIM YASAGI ([[ikiz-tanim-sessiz-ayrisma]]): esik karsilastirmasi SADECE
    burada yazilir; `degerlendir` yalnizca bu sozlugu OKUR. Boylece "hangi eksen yandi"
    sorusunun cevabi, gerekce metniyle AYNI kaynaktan gelir ve sessizce ayrisamaz.

    Bu fonksiyon OLCER, KAPI UYGULAMAZ: "bekleyen icerik var mi" gibi kapilar hukmun
    (degerlendir) isidir. Boylece bir eksenin kapatilmasi eksenin OLCUMUNU yok etmez.
    """
    yas = olcum.get("yas_dk")
    geride = olcum.get("geride")
    takilan = olcum.get("takilan_kosum_dk")
    return {
        # EKSEN 1 — bekleyen icerigin YASI (tabani: yayin ani)
        "yas_gecikme": yas is not None and yas >= GECIKME_YAS_DK,
        "yas_tikali": yas is not None and yas >= TIKALI_YAS_DK,
        "hata_zinciri": olcum["ardisik_hata"] >= TIKALI_HATA_ZINCIR,
        "iptal_zinciri": olcum["ardisik_iptal"] >= ACLIK_IPTAL_ZINCIR,
        "birikme": geride is not None and geride >= GECIKME_BIRIKME,
        # EKSEN 2 — KOSUM OMRU (yas ekseninden BAGIMSIZ; `ahead_by` kapisinin ONUNDE)
        "sure_tavani": takilan is not None and takilan >= KOSUM_OMUR_TAVANI_DK,
    }


def degerlendir(olcum):
    """olcum -> (sinif, gerekce satirlari). Sira: ACLIK > TIKALI > GECIKME > AKIYOR.

    IKI EKSEN AYRI AYRI HUKUM VERIR: icerik ekseni (_icerik_hukmu) ve kosum omru ekseni.
    Ikisi ayni sinifi (TIKALI) uretebilir ama BIRI DIGERINI MASKELEMEZ: omur ekseni
    yandiysa gerekce satiri HER HALUKARDA eklenir, icerik ekseni ne derse desin
    ([[hukum-yanlis-birimde]]).
    """
    eksen = eksen_hukumleri(olcum)
    sinif, neden = _icerik_hukmu(olcum, eksen)

    if eksen["sure_tavani"]:
        neden = list(neden) + [
            "kosum %s %.0f dk'dir TAMAMLANMADI (omur tavani %d dk; olculen en uzun kosum "
            "omru %.1f dk) -> kosum basladi ama bitmiyor"
            % (olcum.get("takilan_kosum_id"), olcum["takilan_kosum_dk"],
               KOSUM_OMUR_TAVANI_DK, OLCULEN_KOSUM_OMRU_MAX_DK)]
        if SINIF_AGIRLIK[sinif] < SINIF_AGIRLIK["TIKALI"]:
            sinif = "TIKALI"
    return sinif, neden


def _icerik_hukmu(olcum, eksen):
    """EKSEN 1: bekleyen ICERIK ne kadar bayat / hat icerigi gecirebiliyor mu."""
    geride = olcum["geride"]
    yas = olcum["yas_dk"]
    ai = olcum["ardisik_iptal"]
    ah = olcum["ardisik_hata"]

    if olcum["son_basarili_sha"] is None:
        # Taranan onekte HIC yayinlayan kosum yok: olculdu, yargi verilebilir
        # (OLCULEMEDI DEGIL). "Yayinlayan" = `deploy` isi basarili olan kosum.
        kapsam = "taranan %d kosum (pencere %d)" % (olcum.get("taranan", 0),
                                                    olcum["pencere"])
        if eksen["iptal_zinciri"]:
            return "ACLIK", ["son %d tamamlanmis kosumun %d'si IPTAL, %s icinde `%s` isini "
                             "BASARIYLA kosan kosum YOK"
                             % (olcum["tamamlanan"], ai, kapsam, YAYIN_ISI)]
        return "TIKALI", ["%s icinde `%s` isini BASARIYLA kosan kosum YOK — canli, main'in "
                          "ne kadar gerisinde oldugu bile bu pencereden olculemiyor"
                          % (kapsam, YAYIN_ISI)]

    if not geride:
        return "AKIYOR", ["canli = main (bekleyen commit YOK); kosum zincirleri "
                          "(iptal %d · hata %d) icerik bekletMIYOR" % (ai, ah)]

    neden = []
    if eksen["iptal_zinciri"] and eksen["yas_gecikme"]:
        neden.append("%d ARDISIK iptal (esik %d) + en eski bekleyen commit %.0f dk "
                     "(esik %d) -> kosumlar ust uste iptal ediliyor, hicbiri tamamlanmiyor"
                     % (ai, ACLIK_IPTAL_ZINCIR, yas, GECIKME_YAS_DK))
        return "ACLIK", neden

    if eksen["hata_zinciri"]:
        neden.append("%d ARDISIK dusen kosum (esik %d)" % (ah, TIKALI_HATA_ZINCIR))
    if eksen["yas_tikali"]:
        neden.append("en eski bekleyen commit %.0f dk (esik %d dk, taban: yayin ani)"
                     % (yas, TIKALI_YAS_DK))
    if neden:
        return "TIKALI", neden

    if eksen["yas_gecikme"]:
        neden.append("en eski bekleyen commit %.0f dk (uyari esigi %d dk, taban: yayin ani)"
                     % (yas, GECIKME_YAS_DK))
    if eksen["birikme"]:
        neden.append("%d commit birikti (uyari esigi %d)" % (geride, GECIKME_BIRIKME))
    if neden:
        return "GECIKME", neden

    return "AKIYOR", ["%d commit bekliyor, en eskisi %.0f dk (esiklerin altinda)"
                      % (geride, yas)]


def olc_ve_degerlendir(getir=api_getir, simdi=None, depo=None, dal=DAL):
    """(sinif, rc, satirlar). OLCULEMEDI burada dogar ve ASLA rc 0 vermez."""
    try:
        olcum = olc(getir=getir, simdi=simdi, depo=depo, dal=dal)
    except OlcumHatasi as e:
        return "OLCULEMEDI", SINIF_RC["OLCULEMEDI"], [str(e)], None
    except Exception as e:                 # beklenmeyen her sey de OLCULEMEDI'dir
        return ("OLCULEMEDI", SINIF_RC["OLCULEMEDI"],
                ["beklenmeyen olcum hatasi: %s: %s" % (type(e).__name__, e)], None)
    # Eksen hukumleri RAPORA ve KABUL TESTINE tasinir: "hangi eksen yandi" sorusu
    # cikti metninden AYIKLANMAZ, olcumden OKUNUR ([[hukum-yanlis-birimde]]).
    olcum["eksenler"] = eksen_hukumleri(olcum)
    sinif, satirlar = degerlendir(olcum)
    if sinif not in SINIF_RC or sinif == "OLCULEMEDI":
        # degerlendir() OLCULEMEDI URETEMEZ (o yalniz olcum ARIZASINDAN dogar); ureti-
        # yorsa sozlesme bozulmustur -> sessizce yesile dusmek yerine OLCULEMEDI de.
        return ("OLCULEMEDI", SINIF_RC["OLCULEMEDI"],
                ["sinif sozlesmesi bozuldu: degerlendir() %r dondurdu" % (sinif,)], olcum)
    return sinif, SINIF_RC[sinif], satirlar, olcum


# ---------------------------------------------------------------- cikti
def _ozet_satirlari(olcum):
    if olcum is None:
        return []
    s = []
    if olcum["geride"] is None:
        s.append("`%s` isini basariyla kosan kosum: taranan %d kosumda YOK (pencere %d)"
                 % (YAYIN_ISI, olcum.get("taranan", 0), olcum["pencere"]))
    else:
        s.append("canli main'den %d commit geride · en eski bekleyen %s"
                 % (olcum["geride"],
                    "yok" if not olcum["geride"] else "%.0f dk" % olcum["yas_dk"]))
        # YAS TABANI = `deploy` isinin bitisi. Kosumun bitisi AYRI basilir: ikisi bu
        # hatta 47,8 dk'ya kadar ayrisir ve tabani karistirmak yanlis alarm uretmisti.
        s.append("son yayinlanan sha: %s (`%s` isi %s'de BITTI = yas tabani · kosum %s'de "
                 "bitti · kosum %s'de basladi)"
                 % (olcum["son_basarili_sha"], YAYIN_ISI,
                    olcum["yayin_ani"].strftime("%H:%M UTC"),
                    olcum["son_basarili_bitis"].strftime("%H:%M"),
                    olcum["son_basarili_baslangic"].strftime("%H:%M")))
        taslak = olcum.get("taslak_isi")
        if taslak is not None and taslak != "success":
            # OLCULUR ama site tazeligi hakkinda hukum VERMEZ (bkz. modul basligi).
            s.append("⚠ o kosumda `%s` isi `%s` — SITE CANLI ama D1 taslaklari taslak "
                     "kalmis olabilir (Ege yeni urunleri goremez)" % (TASLAK_ISI, taslak))
    s.append("ardisik iptal: %d (aclik esigi %d) · ardisik hata: %d (tikanma esigi %d)"
             % (olcum["ardisik_iptal"], ACLIK_IPTAL_ZINCIR,
                olcum["ardisik_hata"], TIKALI_HATA_ZINCIR))
    # EKSEN 2 HER ZAMAN BASILIR (yandi ya da yanmadi): "olculdu ve temiz" ile "hic
    # olculmedi" ayni satirda karismasin.
    takilan = olcum.get("takilan_kosum_dk")
    s.append("en uzun KOSAN kosum omru: %s (omur tavani %d dk) · eksen 2 %s"
             % ("yok (kosan/bekleyen kosum YOK)" if takilan is None
                else "%.0f dk (kosum %s)" % (takilan, olcum.get("takilan_kosum_id")),
                KOSUM_OMUR_TAVANI_DK,
                # Esik karsilastirmasi TEK KANONIK YERDE: burada TEKRARLANMAZ.
                "KIRMIZI" if eksen_hukumleri(olcum)["sure_tavani"] else "temiz"))
    s.append("pencere: %d kosum (%d tamamlandi · %d kosuyor/bekliyor) · is duzeyi "
             "sorulan: %d kosum" % (olcum["pencere"], olcum["tamamlanan"],
                                    olcum["calisan"], olcum.get("taranan", 0)))
    if olcum.get("is_tavanina_dayandi"):
        s.append("⚠ is sorgu TAVANINA (%d) dayanildi — yayinlayan kosum daha geride "
                 "olabilir (alttan olcum)" % IS_SORGU_TAVANI)
    if olcum.get("zincir_pencere_kenarinda"):
        s.append("⚠ zincir PENCERE KENARINDA — gercek zincir daha uzun olabilir "
                 "(alttan olcum)")
    if olcum.get("kirpildi"):
        s.append("⚠ compare 250 commit'te kirpildi — bekleme yasi ALTTAN olculdu")
    return s


def satirlar(getir=api_getir, simdi=None):
    """tools/durum.py bolum 9 icin hazir satirlar (2 bosluk girintili)."""
    sinif, rc, gerekce, olcum = olc_ve_degerlendir(getir=getir, simdi=simdi)
    cikti = ["  %s %s (rc %d)" % (SINIF_ISARET[sinif], sinif, rc)]
    for g in gerekce:
        cikti.append("      %s" % g)
    for o in _ozet_satirlari(olcum):
        cikti.append("      %s" % o)
    if sinif == "OLCULEMEDI":
        cikti.append("      ('sorun yok' DEMEK DEGILDIR — yayin gecikmesi bu kosumda "
                     "OLCULMEDI)")
    return cikti


def rapor(sinif, rc, gerekce, olcum):
    print("=" * 72)
    print("YAYIN GECIKME NOBETCISI — %s" % _simdi().strftime("%Y-%m-%d %H:%M UTC"))
    print("depo: %s · is akisi: %s · dal: %s" % (DEPO, IS_AKISI, DAL))
    print("=" * 72)
    for o in _ozet_satirlari(olcum):
        print("  %s" % o)
    print("")
    print("SONUC: %s %s (cikis kodu %d)" % (SINIF_ISARET[sinif], sinif, rc))
    for g in gerekce:
        print("  - %s" % g)
    if sinif == "OLCULEMEDI":
        print("  ! OLCULEMEDI YESIL DEGILDIR ve KIRMIZI da degildir: bu nobetci hicbir "
              "is akisini bloklamaz.")


# ================================================================= FIKSTURLER
# GERCEK API govdesinin SEKLI tek bir yerde durur (sekil-capasi.json, 1 Agu 2026
# `gh api` ciktisindan uretildi; kisisel veri sabit fikstur degerleriyle degistirildi).
# Senaryo fiksturleri o capayi SABLON alir ve YALNIZ VAR OLAN alanlari ezer ->
# uydurma alan icat EDILEMEZ ([[nobetci-fikstur-sekli]], [[ikiz-tanim-sessiz-ayrisma]]).
def sekil_capasi(yol=None):
    yol = yol or SEKIL_CAPASI
    if not os.path.exists(yol):
        raise OlcumHatasi("sekil capasi YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        capa = json.load(f)
    for a in ("kosum", "karsilastirma", "isler"):
        if a not in capa:
            raise OlcumHatasi("sekil capasinda `%s` YOK" % a)
    if not (isinstance(capa["isler"].get("jobs"), list) and capa["isler"]["jobs"]):
        raise OlcumHatasi("sekil capasi: `isler.jobs` bos ya da liste degil — is duzeyi "
                          "fiksturleri SABLONSUZ kalir")
    return capa


def _bindir(sablon, ustyazim, iz="kok"):
    """Sablona derin bindirme. Var OLMAYAN alani ezmek YASAK (uydurma alan kapisi).

    `_sil`: sablonda VAR OLAN bir alani KALDIRIR (bozuk-sekil fiksturleri icin).
    """
    if not isinstance(ustyazim, dict):
        return copy.deepcopy(ustyazim)
    sonuc = copy.deepcopy(sablon)
    if not isinstance(sonuc, dict):
        raise OlcumHatasi("fikstur bindirme: %s sablonda sozluk degil" % iz)
    for silinecek in ustyazim.get("_sil", []):
        if silinecek not in sonuc:
            raise OlcumHatasi("fikstur `_sil`: %s.%s sablonda ZATEN yok"
                              % (iz, silinecek))
        del sonuc[silinecek]
    for k, v in ustyazim.items():
        if k.startswith("_"):
            continue
        if k not in sonuc:
            raise OlcumHatasi(
                "fikstur UYDURMA ALAN uretti: %s.%s sekil capasinda YOK — fikstur "
                "gercek API sekline uymak ZORUNDA" % (iz, k))
        sonuc[k] = _bindir(sonuc[k], v, "%s.%s" % (iz, k))
    return sonuc


def fikstur_yolu(ad):
    return os.path.join(FIKSTUR_DIZIN, ad if ad.endswith(".json") else ad + ".json")


def fikstur_adlari():
    return sorted(os.path.basename(y)[:-5]
                  for y in glob.glob(os.path.join(FIKSTUR_DIZIN, "*.json"))
                  if os.path.basename(y) != "sekil-capasi.json")


def fikstur_yukle(ad, capa=None):
    """Fikstur -> (getir, simdi, beklenen_sinif, aciklama)."""
    yol = fikstur_yolu(ad)
    if not os.path.exists(yol):
        raise OlcumHatasi("fikstur YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        f_ = json.load(f)
    capa = capa or sekil_capasi()
    beklenen = f_.get("_beklenen")
    if beklenen not in SINIF_RC:
        raise OlcumHatasi("fikstur %s: `_beklenen` gecersiz (%r)" % (ad, beklenen))
    simdi = _iso(f_["_simdi"], "fikstur `_simdi`") if "_simdi" in f_ else None

    hata = f_.get("_hata")
    kosumlar = [_bindir(capa["kosum"], k, "kosum[%d]" % i)
                for i, k in enumerate(f_.get("kosumlar", []))]

    # ---- IS (job) duzeyi govdeleri -------------------------------------------------
    # `_isler` = {"<kosum id>": {"<is adi>": <deger>}} ve <deger> IKI bicimden biridir:
    #     "success"                                   -> yalniz conclusion
    #     {"conclusion": "...", "completed_at": "..."} -> conclusion + YAYIN ANI
    # Govde SABLONU sekil capasindan gelir -> alan adlari uydurulAMAZ.
    #
    # 🔴 `completed_at` BILDIRILMEMISSE kosumun `updated_at`'i kullanilir, yani "yayin
    # ani = kosum sonu" varsayimi. Bu varsayim GERCEK hatta YANLISTIR (olculen fark
    # 47,8 dk'ya cikti) ve yalnizca bu eksenden ONCE yazilmis fiksturlerin anlamini
    # KORUMAK icin vardir. Yas tabani ekseninin fiksturleri `completed_at`'i ACIKCA
    # bildirmek ZORUNDADIR — kabul testi Y7 bunu nobetler.
    #
    # `_isler` HIC verilmemisse ESKI anlam korunur: kosumun genel conclusion'i `deploy`
    # isine yansitilir (kosum duzeyi == is duzeyi). `_isler` VERILMISSE artik sozlesme
    # odur: sorulan bir kosum orada YOKSA fikstur OLCULEMEDI verir (sessiz varsayim YOK).
    is_ustyazim = f_.get("_isler")
    is_sablonu = capa["isler"]["jobs"][0]

    def _is_govdesi(adlar_degerler, varsayilan_bitis, iz):
        isler = []
        for is_adi, deger in adlar_degerler.items():
            if isinstance(deger, dict):
                bilinmeyen = sorted(set(deger) - {"conclusion", "completed_at"})
                if bilinmeyen:
                    raise OlcumHatasi("fikstur %s: %s.%s icinde bilinmeyen anahtar: %s "
                                      "(izinli: conclusion, completed_at)"
                                      % (ad, iz, is_adi, ", ".join(bilinmeyen)))
                son = deger.get("conclusion")
                bitis = deger.get("completed_at", varsayilan_bitis)
            else:
                son, bitis = deger, varsayilan_bitis
            isler.append(_bindir(is_sablonu,
                                 {"name": is_adi, "status": "completed",
                                  "conclusion": son, "completed_at": bitis},
                                 "%s.%s" % (iz, is_adi)))
        return {"total_count": len(isler), "jobs": isler}

    def _kosum(kosum_id):
        k = next((k for k in kosumlar if str(k.get("id")) == str(kosum_id)), None)
        if k is None:
            raise OlcumHatasi("fikstur %s: is sorulan kosum %s listede YOK"
                              % (ad, kosum_id))
        return k

    def _kosum_isleri(kosum_id):
        k = _kosum(kosum_id)
        varsayilan_bitis = k.get("updated_at")
        if is_ustyazim is None:
            return _is_govdesi({YAYIN_ISI: k.get("conclusion")}, varsayilan_bitis, "_miras")
        if str(kosum_id) not in is_ustyazim:
            raise OlcumHatasi("fikstur %s: kosum %s icin `_isler` TANIMSIZ ama nobetci "
                              "is duzeyini sordu" % (ad, kosum_id))
        return _is_govdesi(is_ustyazim[str(kosum_id)], varsayilan_bitis,
                           "_isler[%s]" % kosum_id)
    kars_ust = f_.get("karsilastirma")
    kars = None
    if kars_ust is not None:
        commit_ust = kars_ust.get("commits")
        kars = _bindir({k: v for k, v in capa["karsilastirma"].items() if k != "commits"},
                       {k: v for k, v in kars_ust.items() if k != "commits"},
                       "karsilastirma")
        if commit_ust is None:
            kars["commits"] = copy.deepcopy(capa["karsilastirma"]["commits"])
        else:
            sablon = capa["karsilastirma"]["commits"][0]
            kars["commits"] = [_bindir(sablon, c, "karsilastirma.commits[%d]" % i)
                               for i, c in enumerate(commit_ust)]

    def getir(yol_, zaman_asimi=25, etiket="api"):  # noqa: ARG001 — imza api_getir ile AYNI
        if hata:
            raise OlcumHatasi(hata)
        if "/actions/workflows/" in yol_:
            return {"total_count": len(kosumlar), "workflow_runs": copy.deepcopy(kosumlar)}
        if "/actions/runs/" in yol_ and "/jobs" in yol_:
            return _kosum_isleri(yol_.split("/actions/runs/")[1].split("/")[0])
        if "/compare/" in yol_:
            if kars is None:
                raise OlcumHatasi("fikstur %s: compare govdesi TANIMSIZ ama nobetci "
                                  "sordu (%s)" % (ad, yol_))
            # Fikstur, DOGRU tabani sorup sormadigimizi da nobetler: taban SHA'si son
            # basarili kosumun SHA'si olmali (yanlis taban = sessiz yanlis olcum).
            taban = yol_.split("/compare/")[1].split("...")[0]
            beklenen_taban = f_.get("_karsilastirma_tabani")
            if beklenen_taban and taban != beklenen_taban:
                raise OlcumHatasi("fikstur %s: compare TABANI yanlis — beklenen %s, "
                                  "sorulan %s" % (ad, beklenen_taban, taban))
            return copy.deepcopy(kars)
        raise OlcumHatasi("fikstur %s: bilinmeyen API yolu: %s" % (ad, yol_))

    return getir, simdi, beklenen, f_.get("_aciklama", "")


# ---------------------------------------------------------------- kendini test
def _fikstur_ham(ad):
    try:
        with open(fikstur_yolu(ad), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def yg_etkin_kusuru():
    """etkin_sonuc sozlesmesi: "yayinladi" YALNIZ `deploy` isinin success'inden dogar."""
    vakalar = (
        ({"conclusion": "failure"}, {YAYIN_ISI: "success"}, "success"),
        ({"conclusion": "failure"}, {YAYIN_ISI: "skipped"}, "failure"),
        ({"conclusion": "cancelled"}, {}, "cancelled"),
        ({"conclusion": "success"}, {YAYIN_ISI: "skipped"}, "yayinsiz"),
    )
    return any(etkin_sonuc(k, i) != b for k, i, b in vakalar)


def _fikstur_bitis_bildiriyor(ham):
    """Fikstur `_isler` icinde ACIK bir `completed_at` bildiriyor mu (yas tabani)."""
    for _, isler in (ham.get("_isler") or {}).items():
        for _, deger in (isler or {}).items():
            if isinstance(deger, dict) and deger.get("completed_at"):
                return True
    return False


# ================================================================= EKSEN NOBETLERI
# 🔴 TEK KAYNAK: her nobet SADECE burada yazilir; hem `--kendini-test` hem
# tools/yayin-gecikme-test.py bu listeleri OKUR. Ikinci bir kopya yazmak, kabul testiyle
# CI'nin sessizce ayrismasi demektir ([[ikiz-tanim-sessiz-ayrisma]]). Fonksiyonlar
# EKSEN BASINA ayridir: bir eksen kirmizi yandiginda HANGI eksen oldugu belirsiz kalmaz
# ([[hukum-yanlis-birimde]]).
def sozlesme_kusurlari():
    """Y2 — sinif/cikis kodu sozlesmesi + esiklerin OLCULEN tabana gore konumu."""
    kusur = []
    if SINIF_RC["OLCULEMEDI"] == 0:
        kusur.append("SOZLESME: OLCULEMEDI cikis kodu 0 (YESIL ile karisiyor)")
    if len(set(SINIF_RC.values())) != len(SINIF_RC):
        kusur.append("SOZLESME: iki sinif AYNI cikis kodunu paylasiyor")
    if not (0 < GECIKME_YAS_DK < TIKALI_YAS_DK):
        kusur.append("SOZLESME: yas esikleri sirali degil (%s/%s)"
                     % (GECIKME_YAS_DK, TIKALI_YAS_DK))
    if ACLIK_IPTAL_ZINCIR <= OLCULEN_SAGLIKLI_IPTAL_TAVANI:
        kusur.append("SOZLESME: aclik esigi (%d) OLCULEN saglikli iptal tavaninin (%d) "
                     "ustunde DEGIL — normal eszamanlilik iptali alarm uretir"
                     % (ACLIK_IPTAL_ZINCIR, OLCULEN_SAGLIKLI_IPTAL_TAVANI))
    if TIKALI_HATA_ZINCIR <= OLCULEN_SAGLIKLI_HATA_TAVANI:
        kusur.append("SOZLESME: tikanma esigi (%d) OLCULEN saglikli hata tavaninin (%d) "
                     "ustunde DEGIL — gurultu hatalari alarm uretir"
                     % (TIKALI_HATA_ZINCIR, OLCULEN_SAGLIKLI_HATA_TAVANI))
    if TIKALI_YAS_DK <= OLCULEN_SAGLIKLI_YAS_TAVANI_DK:
        kusur.append("SOZLESME: tikanma yas esigi (%d dk) OLCULEN saglikli tepe yasinin "
                     "(%.1f dk) ustunde DEGIL — normal kuyruk alarm uretir"
                     % (TIKALI_YAS_DK, OLCULEN_SAGLIKLI_YAS_TAVANI_DK))
    # OLCULEMEDI'nin HER kaynagi rc 2 vermeli (ag yok / yetki yok / govde bozuk).
    # 🔴 `OlcumHatasi` LISTEDE OLMAK ZORUNDA (2 Agu, mutasyonla OLCULDU): once yalnizca
    # FileNotFoundError/ValueError sinaniyordu ve ikisi de GENEL `except Exception`
    # kolundan doner. `except OlcumHatasi` kolunu "AKIYOR" dondurecek sekilde bozan bir
    # mutant bu nobetten SESSIZCE geciyordu — yani nobet, olcmedigi bir kolu kutsuyordu.
    # 🔴 SAHTE GETIRICININ IMZASI `api_getir` ILE BIREBIR AYNI OLMAK ZORUNDA (2 Agu,
    # mutasyonla OLCULDU): `etiket` parametresi `etiket_` diye yeniden adlandirilinca
    # gercek cagri (`getir(yol, etiket="runs")`) TypeError firlatti, TypeError de GENEL
    # `except Exception` kolundan dondu — yani nobet UC vakada da AYNI kolu olcuyordu ve
    # hedefledigi `except OlcumHatasi` kolu HIC SINANMIYORDU ([[nobetci-fikstur-sekli]]).
    for ne, patlat in (("gh yok", FileNotFoundError("gh")),
                       ("beklenmeyen tip", ValueError("bozuk")),
                       ("olcum hatasi", OlcumHatasi("sinama: govde anlasilmadi"))):
        def _patlayan(yol_, zaman_asimi=25, etiket="api", _e=patlat):   # noqa: ARG001
            raise _e
        sinif, rc, _, _ = olc_ve_degerlendir(getir=_patlayan)
        if not (sinif == "OLCULEMEDI" and rc == 2):
            kusur.append("FAIL-CLOSED: %s -> %s/rc %d (OLCULEMEDI olmaliydi)"
                         % (ne, sinif, rc))
    return kusur


def is_duzeyi_kusurlari(adlar=None):
    """Y5 — "yayin indi mi" YALNIZ `deploy` isinden okunur (kosum duzeyinden DEGIL)."""
    kusur = []
    if yg_etkin_kusuru():
        kusur.append("SOZLESME: etkin sonuc `%s` isinden DOGMUYOR (kosum duzeyine "
                     "geri donulmus olabilir)" % YAYIN_ISI)
    adlar = fikstur_adlari() if adlar is None else adlar
    if not any("_isler" in _fikstur_ham(a) for a in adlar):
        kusur.append("SOZLESME: HICBIR fikstur `_isler` bildirmiyor — is duzeyi ekseni "
                     "FIKSTURSUZ kalmis (sessizce kosum duzeyine donebilir)")
    return kusur


def yas_tabani_kusurlari(adlar=None):
    """Y7 — yas tabani YAYIN ANIDIR; ekseni fiiliyatta olcen fikstur var mi."""
    kusur = []
    adlar = fikstur_adlari() if adlar is None else adlar
    if not any(_fikstur_bitis_bildiriyor(_fikstur_ham(a)) for a in adlar):
        kusur.append("SOZLESME: HICBIR fikstur `%s.completed_at` bildirmiyor — YAS TABANI "
                     "ekseni fiiliyatta olculmuyor (taban sessizce kosum baslangicina "
                     "donebilir)" % YAYIN_ISI)
    return kusur


def omur_ekseni_kusurlari():
    """Y8 — kosum omur ekseni: `ahead_by` kapisinin ONUNDE ve yanlis alarm uretmiyor.

    Olcumu TAKLIT ETMEDEN dogrudan `degerlendir` uzerinde sinanir: eksenin kapiya gore
    KONUMU bir kod olgusudur, fiksturle degil birim iddiayla tutulur.
    """
    kusur = []
    bekleyensiz = {"geride": 0, "yas_dk": 0.0, "ardisik_iptal": 0, "ardisik_hata": 0,
                   "son_basarili_sha": "abc12345", "pencere": 1, "tamamlanan": 1,
                   "taranan": 1, "takilan_kosum_dk": KOSUM_OMUR_TAVANI_DK + 1.0,
                   "takilan_kosum_id": 1}
    if degerlendir(bekleyensiz)[0] != "TIKALI":
        kusur.append("SOZLESME: kosum omur ekseni `ahead_by == 0` kapisinin ARKASINA "
                     "dusmus — takilan kosum bekleyen icerik yokken GORUNMEZ oluyor")
    normal = dict(bekleyensiz, takilan_kosum_dk=OLCULEN_KOSUM_OMRU_MAX_DK)
    if degerlendir(normal)[0] != "AKIYOR":
        kusur.append("SOZLESME: OLCULEN en uzun kosum omru (%.1f dk) bile alarm uretiyor "
                     "— eksen 2 yanlis alarm makinesi" % OLCULEN_KOSUM_OMRU_MAX_DK)
    if KOSUM_OMUR_TAVANI_DK <= OLCULEN_KOSUM_OMRU_MAX_DK:
        kusur.append("SOZLESME: kosum omur tavani (%d dk) OLCULEN en uzun kosum omrunun "
                     "(%.1f dk) ustunde DEGIL — normal suren kosum alarm uretir"
                     % (KOSUM_OMUR_TAVANI_DK, OLCULEN_KOSUM_OMRU_MAX_DK))
    return kusur


def sizinti_kusurlari():
    """Y6 — `gh` stderr'i disari SIZMAZ ama teshis SINIFI da yok edilmez."""
    kusur = []
    ornek = "gh: Not Found (HTTP 404) https://api.github.com/repos/X/actions/runs/1/jobs"
    ozet = gh_hata_sinifi(ornek)
    if "https://" in ozet or ornek in ozet:
        kusur.append("SIZINTI: `gh` stderr'i ozetten OLDUGU GIBI cikiyor")
    if "404" not in ozet:
        kusur.append("TESHIS: hata sinifi ozetten SILINMIS (teshis tamamen yok edilmis)")
    return kusur


def kendini_test(yazdir=True):
    """AGSIZ fikstur kabulu. 0 = hepsi gecti, 1 = en az bir kusur."""
    kusur = []
    gecen = 0
    adlar = fikstur_adlari()
    if not adlar:
        print("KUSUR: fikstur YOK (%s) — bu nobetcinin kabulu OLCULEMEZ" % FIKSTUR_DIZIN)
        return 1
    for ad in adlar:
        try:
            getir, simdi, beklenen, aciklama = fikstur_yukle(ad)
        except OlcumHatasi as e:
            kusur.append("%s: fikstur YUKLENEMEDI — %s" % (ad, e))
            continue
        sinif, rc, gerekce, _ = olc_ve_degerlendir(getir=getir, simdi=simdi)
        tamam = (sinif == beklenen and rc == SINIF_RC[beklenen])
        if tamam:
            gecen += 1
        else:
            kusur.append("%s: beklenen %s (rc %d), olculen %s (rc %d) — %s"
                         % (ad, beklenen, SINIF_RC[beklenen], sinif, rc,
                            "; ".join(gerekce)[:200]))
        if yazdir:
            print("  %s %-30s -> %-10s rc %d   %s"
                  % ("✔" if tamam else "✘", ad, sinif, rc, aciklama[:60]))

    # SOZLESME NOBETLERI — fiksturlerden BAGIMSIZ, kod icindeki iddialar.
    # KOPYA YOK: hepsi eksen basina ayrilmis TEK KAYNAK fonksiyonlardan gelir; kabul
    # testi (tools/yayin-gecikme-test.py) AYNI fonksiyonlari eksen koduyla okur.
    for _liste in (sozlesme_kusurlari(), is_duzeyi_kusurlari(adlar),
                   yas_tabani_kusurlari(adlar), omur_ekseni_kusurlari(),
                   sizinti_kusurlari()):
        kusur.extend(_liste)

    if yazdir:
        print("")
        print("fikstur: %d/%d gecti · sozlesme nobetleri: %s"
              % (gecen, len(adlar), "TEMIZ" if not kusur else "KUSURLU"))
        for k in kusur:
            print("  ✘ %s" % k)
    return 1 if kusur else 0


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayin gecikme nobetcisi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ fikstur kabulu (0 = hepsi gecti)")
    ap.add_argument("--fikstur", metavar="AD", help="tek fiksturu kostur ve raporla")
    ap.add_argument("--liste", action="store_true", help="fiksturleri listele")
    a = ap.parse_args(argv)

    if a.liste:
        for ad in fikstur_adlari():
            print(ad)
        return 0
    if a.kendini_test:
        return kendini_test()
    if a.fikstur:
        try:
            getir, simdi, beklenen, _ = fikstur_yukle(a.fikstur)
        except OlcumHatasi as e:
            print("FIKSTUR HATASI: %s" % e)
            return 2
        sinif, rc, gerekce, olcum = olc_ve_degerlendir(getir=getir, simdi=simdi)
        rapor(sinif, rc, gerekce, olcum)
        print("  (fikstur beklentisi: %s)" % beklenen)
        return rc

    sinif, rc, gerekce, olcum = olc_ve_degerlendir()
    rapor(sinif, rc, gerekce, olcum)
    return rc


if __name__ == "__main__":
    sys.exit(main())
