#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN ERISIM NOBETCISI — "yayinladigimiz sayfa CANLIDA GERCEKTEN ACIK MI?".

NEDEN VAR (3 Agu 2026, OLCULDU — bu nobetci bir olayin faturasidir)
====================================================================
UC landing sayfasi canlida **12 gun boyunca 403 Forbidden** dondu ve HICBIR NOBETCI
GORMEDI. Sebep bizim uretimimiz DEGILDI: kardes depodaki Worker rotasi
`pruvo3d.com/ara*` bir ONEK JOKERIDIR ve `araba-…` / `arac-…` ile baslayan slug'lari
yutup webhook catch-all'ina dusuruyordu (403, istek origin'e HIC ulasmiyordu).

O gun her kapi YESILDI:
  * dosyalar origin'de URETILDI  (deploy fail-closed kopyaladi, kosum success),
  * sitemap'te VARDI             (17.812 <loc> icinde ucu de),
  * 10 canli sayfadan 22 IC LINK onlara gidiyordu,
  * `_yayin-icerik-dizinleri.txt` beyaz-listesinde VARDI.
Musteri ve Googlebot ise KAPALI KAPIYA carpiyordu.

🔴 SINIF: yayinlanan icerigin URETILDIGI olculuyordu, ERISILEBILDIGI olculmuyordu.
Bu nobetci tam o bosluktadir: "depo/CI ne diyor" degil, "MUSTERI KAPIYI ACABILIYOR MU".

🔴 GET KULLANIR — HEAD YETMEZ (ayirt edici, o gun OLCULDU)
=========================================================
Ayni URL: `HEAD -> 200` · `GET -> 403`. Sebep worker kodunda `request.method === "GET"`
dalinin HEAD'i kapsamamasiydi. HEAD'e bakan bir nobetci bu kusuru **HIC GORMEZDI** ve
"290/290 acik" diye YESIL yanardi. Bu yuzden `YONTEM = "GET"` TEK KAYNAKTIR ve kabul
testi bunu FIKSTURLE (HEAD 200 / GET 403 uretn gercek bir HTTP sunucusu) nobetler;
`YONTEM`i "HEAD"e ceviren mutant kabul testini KIRMIZI yakar.

🔴 EVREN HIZALAMA — KUME "SON BASARILI DEPLOY"UN SHA'SINDAN TURER (12 Agu 2026)
==============================================================================
Kosum `31579567151` (12 Agu 08:42Z) KAPALI yakti: 11 URL 404. Bagimsiz teyit dakikalar
sonra ayni 11 URL'yi 200 buldu. Kapanma GERCEKTI ama GECICIYDI: alarm, "yayinlanmis
olmasi beklenen" kumeyi TAZE checkout'tan (main ucu) turetiyordu; olctugu canli yuzey
ise SON BASARILI DEPLOY'un SHA'sindaydi. O turda olculen fark: deploy `9cf40ae3`,
`origin/main` `c4a1931a` -> agac deploy'dan **4 commit ONDE**. Yeni sayfa tasiyan bir
parti indiginde alarm, HENUZ DEPLOY EDILMEMIS sayfalari canlida arayip 404 aliyordu.
`GECICI` ayrimi 5xx/ag arizasini yeniden yokluyor ama 404'u FINAL sayar — oysa rollout
penceresinde tam da 404 gecici olandir. Sinif: [[canli-evren-bayat-agac-yarisi]].

  * EVREN: `kume_turet` artik `deploy_agaci()` ile cikarilan **deploy SHA'sinin**
    `tools/` agacindan okur; calisma agacinin HEAD'inden DEGIL.
  * KANIT: `hizalama_kanitla()` `git merge-base --is-ancestor <deploy_sha> <ref>`
    kosar ve kaniti CIKTIYA BASAR. Beyan degil, kosulan komuttur.
  * KANIT YOKSA -> **OLCULEMEDI (rc 2)**, `KAPALI` DEGIL. Ne yesile boyama ne de
    sahte kirmizi: "olculemedi ≠ yesil, olculemedi ≠ ariza".
  * 🔴 HEAD'E YEDEK YOL YOKTUR. deploy SHA'si okunamayinca HEAD'e dusmek, tam da
    kapatilan ariza sinifini geri getirirdi -> `deploy_sha_bul` OlcumHatasi atar.
  * 🔴 KORLUK KORUMASI: hizalamadan SONRA da 404 donen URL — yani deploy'a DAHIL
    OLDUGU HALDE canlida kapali sayfa — HALA KAPALI ve rc 1'dir. Onarim alarmi
    sagirlastirmaz; kabul testi bunu ayri bir kolda (E9) nobetler.
  * K4/K5 (yerel build artefaktlari) ancak calisma agaci deploy SHA'sina TAM ESITSE
    kullanilir; esit degilse deploy agacindan okunur (orada yoktur -> kume K1-K3).
    Sebep: yerel `sitemap.xml` HEAD'in build'idir, deploy edilmis kumenin DEGIL.

KUME NEREDEN TURER (elle liste YOK — elle liste CURUR)
======================================================
  K1  tools/sayfalar.py :: SITEMAP_SLUGS   (STATIK_SAYFALAR + CONTENT_PAGES slug'lari)
  K2  tools/landing_hub_build.py :: HUB_SLUG (landing hub dizini)
  K3  site KOKU "/" (ana sayfa; build.py render_sitemap'te de sabittir)
  K4  _yayin-icerik-dizinleri.txt — build'in URETTIGI deploy beyaz-listesi (VARSA;
      `marka` gibi ust dizinleri buradan alir). CI'da build kosmadan YOKTUR.
  K5  sitemap.xml — YEREL uretilmis kopya (VARSA): TEK SEGMENTLI (ust duzey) <loc>'lar.
K1 ve K2 ZORUNLUDUR: yuklenemezse hukum YOK -> OLCULEMEDI (rc 2). K4/K5 zenginlestirir;
yoksa kume kucuk kalir ama kaynak kaynak SAYIYLA basilir (sessiz daralma YASAK).

🔴 KUME TABANI (`KUME_TABANI`): turetilen kume tabandan kucukse OLCULEMEDI'dir.
Sebep: bos/collapsed bir kume uzerinde donen dongu HICBIR SEY olcmez ama "hepsi acik"
diye YESIL yanar — bu nobetcinin en ucuz oldurulme yoludur.

EKSEN SINIRI — IKINCI KOPYA ACILMAZ
===================================
  * `/urun/<id>/` sayfalari (bugun 17.028) BU ARACIN ISI DEGILDIR: onlar
    `tools/canli-saglik-kapisi.py` K2 ekseninindir (orneklemli, yeni urun odakli).
  * `/marka/...` sayfalari (bugun 487) varsayilan kapsamda DEGILDIR; `--kapsam marka`
    ya da `--kapsam tam` ile olculur ve kaynagi YEREL sitemap'tir (yoksa OLCULEMEDI —
    sessizce daraltilmaz).
  * Kapsam her kosumda BASILIR; "hepsi yesil" cumlesi kapsam sayisi OLMADAN kurulmaz.

HUKUM
=====
  ACIK        her URL 200 (ya da yonlendirme zinciri 200'de bitiyor).
  KAPALI      en az bir URL 200 disi / dongu / zincir tavani asildi  -> rc 1.
  OLCULEMEDI  ag/DNS/zaman asimi/kaynak yuklenemedi/kume tabanin altinda -> rc 2.
Yonlendirme zinciri 200'de bitiyorsa SAPMA DEGILDIR (rapora AYRI satir olarak yazilir:
sitemap kanonik URL vermeli, ama musteri kapiyi acabiliyor).

🔴 FAIL-CLOSED: olculemeyen sey ASLA yesil sayilmaz. Ag yoksa, DNS cozmuyorsa, zaman
asimi olduysa ya da oran sinirina takildiysak rc 2'dir — "hepsi 200" VARSAYILMAZ.
🔴 SAPMA KANITI OLCUM ARIZASINI EZER: elimizde zaten KAPALI bir kapi varken arac
"olculemedi"ye dusmez (kanit kaybolmasin); iki hal de raporda AYRI AYRI sayilir.

NEREYE BAGLIDIR (gerekce: yanlis-pozitif TUM EKIBIN yayinini durdurur)
======================================================================
  * CANLI olcum kolu `deploy.yml`'e BAGLANMAZ. `deploy` YALNIZ `build`'e baglidir;
    aga bagimli bir kapiyi oraya koymak, tek gecici DNS hatasinda yayini durdururdu
    ([[kapi-kapsam-eksen-secimi]], [[kapi-birikimi-yayin-gecikmesi]]).
  * CANLI kol AYRI ve SEYREK kosan bir ALARM KOLUNDADIR:
    `.github/workflows/yayin-erisim-alarmi.yml` (saatlik cron, `push` tetikleyicisi YOK,
    ayri `concurrency` grubu, `continue-on-error` YOK). Ayni desen 1 Agu'da paket
    tazeligi alarmi icin secildi ve kosuyor.
  * `deploy.yml`'de YALNIZ bu dosyanin AGSIZ/YEREL fikstur kabulu kosar
    (`tools/yayin-erisim-test.py`, serit B — beyan: tools/is-akisi-kapisi.py :: SERIT_B).

MALIYET
=======
Varsayilan kapsam bugun 295-296 URL. Istek hizi `--hiz` (istek/sn) ile SINIRLIDIR ve
toplam sure her kosumda OLCULUP BASILIR. ORNEKLEME YOKTUR: kume kirpilmaz; pahali
gelirse cadans seyreltilir (cron), kume degil.

KULLANIM
========
    python3 tools/yayin-erisim-nobeti.py                  # canli olcum (ag ISTER)
    python3 tools/yayin-erisim-nobeti.py --kapsam tam     # + /marka sayfalari (yerel sitemap)
    python3 tools/yayin-erisim-nobeti.py --liste          # yalniz kumeyi bas (AG YOK)
    python3 tools/yayin-erisim-nobeti.py --json           # makine okunur
    python3 tools/yayin-erisim-nobeti.py --gh-ozet        # GitHub kosum ozeti + output
    python3 tools/yayin-erisim-nobeti.py --kendini-test   # YEREL fikstur sunucusu kabulu
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

SITE_VARSAYILAN = "https://pruvo3d.com"

# 🔴 TEK KAYNAK — ISTEK YONTEMI. "HEAD" yapan her mutant kabul testini KIRMIZI yakar:
# 3 Agu 2026'da olculen kusurda ayni URL HEAD'e 200, GET'e 403 donuyordu.
YONTEM = "GET"

# 200 DISI HER SEY KAPALIDIR. Bu demet genisletilirse (or. 403/404 "acik" sayilirsa)
# nobetci tam da dogdugu kusuru gormez -> kabul testi KIRMIZI yanar.
ACIK_KODLAR = (200,)

# R2/edge urllib UA 403 dersi ([[r2-urllib-ua-403-tuzagi]]): ciplak `Python-urllib` UA'si
# Cloudflare tarafindan bot sayilip 403 yiyebilir -> nobetci TUM sayfalari "kapali"
# sanip yanlis alarm verirdi. Tarayici UA'si ZORUNLUDUR.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# ─────────────────────────────────────────── GECICI SINIF (BIR KEZ YENIDEN YOKLAMA)
# 🔴 10 Agu 2026 OLCULDU (bu ek de bir olayin faturasidir): alarm AYNI GUN IKI KEZ
# kirmizi yandi; her iki kosumda da 328 URL'den TEK biri kapali gorundu ve her seferinde
# FARKLI bir sayfa: HTTP 503 + GitHub Pages'in gecici "Hello future GitHubber" govdesi.
# Dakikalar sonra ayni adresler (no-cache dahil) 200 donuyordu -> KALICI erisim arizasi
# YOKTU. Yani alarm anlik bir edge/origin blip'ini "KALICI KAPALI" sayiyordu.
#
# 🔴 DUZELTME SESSIZLESTIRME DEGILDIR:
#   * gecici sinif YALNIZ BIR KEZ yeniden yoklanir (no-cache; uc onbellegi atlansin),
#   * ikinci yoklama da basarisizsa hukum DEGISMEZ: URL KAPALI/ARIZA kalir (rc 1/2),
#   * ikinci yoklama basariliysa URL ACIK sayilir AMA `GECICI` sayacina girer, satiri
#     raporda 🟡 olarak GORUNUR ve hukum satirina `GECICI=<n>` yazilir. "Yesile boyama"
#     ancak sayilan sey GORUNMEZ olursa olur ([[hukum-yanlis-birimde]]).
#
# 🔴 SINIF SINIRI (dar tutulmustur — genisletmek nobetciyi korlestirir):
#   * 5xx  -> gecici (uc/origin anlik hatasi),
#   * ag/DNS/TLS/zaman asimi (ARIZA) -> gecici,
#   * 4xx (404/410/403) -> ASLA yeniden yoklanmaz; silinmis/yasakli sayfa YAPISALDIR ve
#     ikinci istek de ATILMAZ (bos yere trafik yok, sinif affi hic yok),
#   * DONGU / `location`siz yonlendirme -> ASLA; yapisal kusurdur.
YENIDEN_YOKLAMA_BEKLEME = 5.0
GECICI_KOD_ALT, GECICI_KOD_UST = 500, 600

ZAMAN_ASIMI_VARSAYILAN = 20.0
# Istek hizi (istek/sn). Sayfa istekleri statik CDN'e gider (worker oran siniri DEGIL);
# yine de uc nazikce kullanilir: 6/sn -> ~296 URL ~50 sn.
HIZ_VARSAYILAN = 6.0
YONLENDIRME_TAVANI = 5

# Kume tabani: bugun K1 tek basina 293 uretiyor. Taban ALTINA dusen bir kume "olculemedi"
# demektir (kaynak bozuldu / bos dondu), "her sey acik" DEMEK DEGILDIR.
KUME_TABANI = 250

SINIF_RC = {"ACIK": 0, "KAPALI": 1, "OLCULEMEDI": 2}
DURUM_ETIKET = {"ACIK": "acik", "KAPALI": "kapali", "OLCULEMEDI": "olculemedi"}

KAPSAMLAR = ("sayfa", "marka", "tam")

# ───────────────────────────────────────────────── EVREN HIZALAMA (deploy SHA'si)
# Son basarili deploy'un SHA'sini is akisi cozer (`gh api` -> `deploy.yml` son
# `success` kosumunun `head_sha`'si) ve BU ORTAM DEGISKENINE yazar. Elle kosumda
# `--deploy-sha` verilir. 🔴 UCUNCU BIR YOL (HEAD'e dusme) YOKTUR.
DEPLOY_SHA_ORTAM = "PRUVO_DEPLOY_SHA"
# Evreni turetmek icin deploy agacindan cikarilan yollar. `tools/` yeter: K1
# (sayfalar.py) + K2 (landing_hub_build.py) oradadir; K4/K5 zaten izlenmez.
ARSIV_YOLLARI = ("tools",)
SHA_DESENI = re.compile(r"^[0-9a-f]{7,40}$")
# Canli yuzeyi URETEN is akisi. Son `success` kosumunun `head_sha`'si = canlida duran
# kumenin SHA'si. (Alarm is akisi bu sorgu icin `actions: read` izni tasir.)
DEPLOY_IS_AKISI = "deploy.yml"
DEPLOY_DALI = "main"
API_TABAN = "https://api.github.com"


class OlcumHatasi(Exception):
    """Olculemedi -> YESIL degil, rc 2."""


def _git(args, kok=ROOT, zaman_asimi=90.0):
    """(rc, stdout, stderr) — ASLA istisna atmaz (git yoksa bile rc!=0 doner).

    Kabul testleri bu yordami ENJEKTE eder (`git_fn`), ama E9 ekseni GERCEK bir git
    deposu kurar: git'in ata semantigini taklit eden bir sahte, tam da olculmek
    istenen seyi (ata mi degil mi) kendi varsayimimizla aynalardi."""
    import subprocess
    try:
        p = subprocess.run(["git", "-C", kok] + list(args), capture_output=True,
                           text=True, timeout=zaman_asimi)
    except Exception as e:                                  # noqa: BLE001
        return 127, "", "%s: %s" % (type(e).__name__, e)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def deploy_sha_api(ortam=None, zaman_asimi=20.0, istek_fn=None):
    """Son BASARILI `deploy.yml` kosumunun `head_sha`'si (GitHub API). None donebilir.

    Yan etkisiz salt-okunur GET. Token yoksa / API konusmazsa None doner ve cagiran
    OLCULEMEDI'ye duser — bu yol bir YEDEK DEGIL, kaynagin KENDISIDIR."""
    ortam = os.environ if ortam is None else ortam
    depo = (ortam.get("GITHUB_REPOSITORY") or "").strip()
    jeton = (ortam.get("GITHUB_TOKEN") or ortam.get("GH_TOKEN") or "").strip()
    if not depo or not jeton:
        return None, "depo=%s jeton=%s" % ("VAR" if depo else "YOK",
                                           "VAR" if jeton else "YOK")
    url = ("%s/repos/%s/actions/workflows/%s/runs?status=success&branch=%s&per_page=1"
           % (API_TABAN, depo, DEPLOY_IS_AKISI, DEPLOY_DALI))
    istek = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer %s" % jeton,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            veri = json.loads(y.read().decode("utf-8", "replace"))
    except Exception as e:                                  # noqa: BLE001
        return None, "API konusmadi (%s: %s)" % (type(e).__name__, str(e)[:80])
    kosumlar = veri.get("workflow_runs") or []
    if not kosumlar:
        return None, "API basarili `%s` kosumu DONDURMEDI" % DEPLOY_IS_AKISI
    sha = (kosumlar[0].get("head_sha") or "").strip().lower()
    kosum_id = kosumlar[0].get("id")
    if not sha:
        return None, "API kosumu `head_sha` TASIMIYOR (id=%s)" % kosum_id
    return sha, "kosum %s" % kosum_id


def deploy_sha_bul(ortam=None, acik=None, api_fn=None):
    """SON BASARILI DEPLOY'un SHA'si. Doner: (sha, kaynak).

    Sira: `--deploy-sha` > PRUVO_DEPLOY_SHA ortam degiskeni > GitHub API (son
    `success` `deploy.yml` kosumunun `head_sha`'si).

    🔴 FAIL-CLOSED VE YEDEK YOLSUZ: hicbiri vermezse OlcumHatasi -> OLCULEMEDI.
    "Bulamazsan HEAD'i kullan" bir kolaylik gibi gorunur ama tam da 12 Agu'da
    olculen ariza sinifidir: HEAD deploy'dan ONDEyse henuz yayinlanmamis sayfalar
    canlida aranir, 404 gelir ve alarm KALICI KAPANMA sanip kirmizi yanar."""
    ortam = os.environ if ortam is None else ortam
    api_fn = api_fn or deploy_sha_api
    api_notu = "denenmedi"
    if acik:
        ham, kaynak = acik, "--deploy-sha"
    else:
        ham, kaynak = ortam.get(DEPLOY_SHA_ORTAM) or "", DEPLOY_SHA_ORTAM
        if not (ham or "").strip():
            ham, api_notu = api_fn(ortam=ortam)
            kaynak = "GitHub API/%s (%s)" % (DEPLOY_IS_AKISI, api_notu)
    ham = (ham or "").strip().lower()
    if not ham:
        raise OlcumHatasi(
            "son basarili deploy SHA'si YOK (--deploy-sha verilmedi, %s bos, API: %s). "
            "Evren HEAD'den TURETILMEZ: HEAD deploy'dan ONDEyse henuz yayinlanmamis "
            "sayfalar canlida aranir ve 404 'KAPALI' sanilir."
            % (DEPLOY_SHA_ORTAM, api_notu))
    if not SHA_DESENI.match(ham):
        raise OlcumHatasi("deploy SHA'si SHA'ya benzemiyor: %r (kaynak: %s)"
                          % (ham[:64], kaynak))
    return ham, kaynak


def hizalama_kanitla(deploy_sha, kok=ROOT, ref="HEAD", git_fn=None):
    """Evren ile olculen agacin AYNI TARIHTE oldugunun KANITI (kosulan komut).

    Doner: {"deploy_sha","ref","ref_sha","ileri","satir"}. Kanit kurulamazsa
    OlcumHatasi (-> OLCULEMEDI, KAPALI DEGIL).

    Kanit `git merge-base --is-ancestor <deploy_sha> <ref_sha>` rc'sidir:
      * rc 0  -> deploy SHA'si bizim gecmisimizde; evren o SHA'nin agacindan
                 GUVENLE turetilebilir (agac ondeyse fark SAYIYLA basilir),
      * rc!=0 -> deploy baska bir gecmisten (zorla itilmis / sig klon / baska dal);
                 hangi kumeyi olcecegimizi BILMIYORUZ -> OLCULEMEDI."""
    git_fn = git_fn or _git
    rc, ref_sha, err = git_fn(["rev-parse", "--verify", "%s^{commit}" % ref], kok=kok)
    if rc != 0 or not ref_sha:
        raise OlcumHatasi("olculen ref (%s) cozulemedi: rc=%d %s" % (ref, rc, err[:120]))
    rc, tam, err = git_fn(["rev-parse", "--verify", "%s^{commit}" % deploy_sha], kok=kok)
    if rc != 0 or not tam:
        raise OlcumHatasi(
            "deploy SHA %s bu agacta YOK (sig klon / zorla itilmis gecmis?): rc=%d %s"
            % (deploy_sha[:12], rc, err[:120]))
    rc, _o, err = git_fn(["merge-base", "--is-ancestor", tam, ref_sha], kok=kok)
    if rc != 0:
        raise OlcumHatasi(
            "HIZALANAMADI: deploy SHA %s, olculen ref %s (%s) ATASI DEGIL "
            "(`git merge-base --is-ancestor` rc=%d). Canli yuzeyin hangi kumeden "
            "dogdugu BILINMIYOR -> hukum OLCULEMEDI, KAPALI DEGIL. %s"
            % (tam[:12], ref, ref_sha[:12], rc, err[:120]))
    rc, sayi, _e = git_fn(["rev-list", "--count", "%s..%s" % (tam, ref_sha)], kok=kok)
    ileri = int(sayi) if rc == 0 and sayi.isdigit() else -1
    satir = ("HIZALAMA KANITI: `git merge-base --is-ancestor %s %s` -> rc 0 (ATA) · "
             "olculen ref %s=%s · agac deploy'dan %s commit ONDE -> EVREN DEPLOY "
             "SHA'SINDAN turer, HEAD'den DEGIL."
             % (tam[:12], ref_sha[:12], ref, ref_sha[:12],
                ("%d" % ileri) if ileri >= 0 else "?"))
    return {"deploy_sha": tam, "ref": ref, "ref_sha": ref_sha, "ileri": ileri,
            "satir": satir}


def deploy_agaci(deploy_sha, kok=ROOT, git_fn=None, hedef=None):
    """deploy SHA'sindaki `tools/` agacini GECICI dizine cikarir; o kokU doner.

    Checkout/worktree DEGIL `git archive`: calisma agacini KIRLETMEZ, HEAD'i
    oynatmaz, baska oturumun isine dokunmaz."""
    import tarfile
    import tempfile
    git_fn = git_fn or _git
    hedef = hedef or tempfile.mkdtemp(prefix="yayin-erisim-deploy-")
    tar_yol = os.path.join(hedef, "_deploy.tar")
    rc, _o, err = git_fn(["archive", "--format=tar", "--output=%s" % tar_yol,
                          deploy_sha] + list(ARSIV_YOLLARI), kok=kok)
    if rc != 0 or not os.path.exists(tar_yol):
        raise OlcumHatasi("deploy SHA %s agaci cikarilamadi (git archive rc=%d): %s"
                          % (deploy_sha[:12], rc, err[:160]))
    with tarfile.open(tar_yol) as t:
        try:
            t.extractall(hedef, filter="data")
        except TypeError:                                   # py<3.12
            t.extractall(hedef)
    os.remove(tar_yol)
    if not os.path.exists(os.path.join(hedef, "tools", "sayfalar.py")):
        raise OlcumHatasi("deploy agacinda tools/sayfalar.py YOK -> evren turetilemez "
                          "(deploy SHA %s)" % deploy_sha[:12])
    return hedef


# =========================================================== KUME (KAYNAK KATMANI)
def _modul(ad, yol):
    if not os.path.exists(yol):
        raise OlcumHatasi("kaynak dosya YOK: %s" % yol)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    try:
        spec.loader.exec_module(m)
    except Exception as e:                                  # noqa: BLE001
        raise OlcumHatasi("%s yuklenemedi (%s: %s)" % (os.path.basename(yol),
                                                       type(e).__name__, e))
    return m


def _yol(slug):
    """slug -> '/slug/' (kok icin '/')."""
    s = (slug or "").strip().strip("/")
    return "/" if not s else "/%s/" % s


def kume_turet(kok=ROOT, kapsam="sayfa", zengin_kok=None, zengin_not=""):
    """(yollar, kaynaklar) — yollar sirali '/...' listesi; kaynaklar beyan tablosu.

    Elle yazilmis URL listesi YOKTUR: her yol bir KAYNAKTAN turer ve hangi kaynagin kac
    yol verdigi rapora basilir. K1/K2 ZORUNLU (yuklenemezse OlcumHatasi = rc 2).

    `kok` = EVREN KOKU. Canli kosumda bu, calisma agaci DEGIL `deploy_agaci()` ile
    cikarilmis SON BASARILI DEPLOY agacidir (bkz. modul basligi: evren hizalama).
    `zengin_kok` = K4/K5/K6 kaynaklarinin (yerel build artefaktlari) kokU; verilmezse
    `kok` kullanilir. Calisma agaci deploy SHA'sina TAM ESIT degilse buraya calisma
    agaci VERILMEZ: yerel `sitemap.xml` HEAD'in build'idir, deploy edilenin degil."""
    if kapsam not in KAPSAMLAR:
        raise OlcumHatasi("bilinmeyen kapsam %r (izinli: %s)" % (kapsam,
                                                                 ", ".join(KAPSAMLAR)))
    zk = kok if zengin_kok is None else zengin_kok
    zn = ("  [%s]" % zengin_not) if zengin_not else ""
    kaynaklar = []
    sayfa = []

    if kapsam in ("sayfa", "tam"):
        sayfalar = _modul("pruvo_sayfalar", os.path.join(kok, "tools", "sayfalar.py"))
        slugler = list(getattr(sayfalar, "SITEMAP_SLUGS", []) or [])
        if not slugler:
            raise OlcumHatasi("sayfalar.py::SITEMAP_SLUGS BOS -> olculecek sayfa yok "
                              "(kaynak bozuk; bos kume 'hepsi acik' DEMEK DEGILDIR)")
        k1 = [_yol(s) for s in slugler]
        kaynaklar.append(("K1 sayfalar.py::SITEMAP_SLUGS", len(k1), True, ""))
        sayfa += k1

        hub = _modul("pruvo_landing_hub", os.path.join(kok, "tools",
                                                       "landing_hub_build.py"))
        hub_slug = getattr(hub, "HUB_SLUG", None)
        if not hub_slug:
            raise OlcumHatasi("landing_hub_build.py::HUB_SLUG BOS -> hub dizini "
                              "olculemez")
        kaynaklar.append(("K2 landing_hub_build.py::HUB_SLUG", 1, True, hub_slug))
        sayfa.append(_yol(hub_slug))

        kaynaklar.append(("K3 site koku (ana sayfa)", 1, True, "/"))
        sayfa.append("/")

        man = os.path.join(zk, "_yayin-icerik-dizinleri.txt")
        if os.path.exists(man):
            with open(man, encoding="utf-8") as f:
                satirlar = [s.strip() for s in f if s.strip()]
            k4 = [_yol(s) for s in satirlar]
            yeni = len(set(k4) - set(sayfa))
            kaynaklar.append(("K4 _yayin-icerik-dizinleri.txt (build manifesti)",
                              len(k4), True, "%d yeni" % yeni))
            sayfa += k4
        else:
            kaynaklar.append(("K4 _yayin-icerik-dizinleri.txt (build manifesti)",
                              0, False,
                              "dosya YOK (build kosmamis) — kume K1-K3'ten" + zn))

    sitemap_yol = os.path.join(zk, "sitemap.xml")
    sitemap_var = os.path.exists(sitemap_yol)
    ust, marka = [], []
    if sitemap_var:
        with open(sitemap_yol, encoding="utf-8") as f:
            ham = f.read()
        for u in re.findall(r"<loc>([^<]+)</loc>", ham):
            p = urllib.parse.urlsplit(u.strip()).path or "/"
            if p.startswith("/marka/"):
                marka.append(p)
            elif p.startswith("/urun/"):
                continue                       # EKSEN SINIRI: canli-saglik-kapisi K2
            elif p.count("/") <= 2:
                ust.append(p)

    if kapsam in ("sayfa", "tam"):
        if sitemap_var:
            yeni = len(set(ust) - set(sayfa))
            kaynaklar.append(("K5 sitemap.xml (yerel, ust duzey)", len(ust), True,
                              "%d yeni" % yeni))
            sayfa += ust
        else:
            kaynaklar.append(("K5 sitemap.xml (yerel, ust duzey)", 0, False,
                              "dosya YOK (build kosmamis)" + zn))

    yollar = list(sayfa)
    if kapsam in ("marka", "tam"):
        if not sitemap_var:
            raise OlcumHatasi("--kapsam %s YEREL sitemap.xml ISTER (marka sayfalarinin "
                              "tek kaynagi odur) ama dosya YOK -> kume sessizce "
                              "daraltilmaz, OLCULEMEDI%s" % (kapsam, zn))
        kaynaklar.append(("K6 sitemap.xml (yerel, /marka/)", len(marka), True, ""))
        yollar += marka

    benzersiz = sorted(set(yollar))
    if len(benzersiz) < KUME_TABANI and kapsam != "marka":
        raise OlcumHatasi("turetilen kume %d URL — TABAN %d'in ALTINDA. Collapsed bir "
                          "kume hicbir sey olcmez ama 'hepsi acik' diye yesil yanardi."
                          % (len(benzersiz), KUME_TABANI))
    return benzersiz, kaynaklar


# =========================================================== OLCUM (AG KATMANI)
class _YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    """Otomatik yonlendirme KAPALI: zinciri KENDIMIZ gezeriz (nereye gittigi + dongu
    olculsun diye). urllib'in kendi takibi zinciri GORUNMEZ kilardi."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ACICI = urllib.request.build_opener(_YonlendirmeYok())


def _istek(url, yontem=None, zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None,
           no_cache=False):
    """(kod|None, basliklar, govde_ilk_baytlari, hata|None). ASLA istisna atmaz.

    `no_cache=True` YALNIZ yeniden yoklamada kullanilir: ilk yoklamayi 503'e dusuren
    sey uc onbelleginde duruyorsa ikinci istek ayni bayat yaniti gorurdu."""
    yontem = yontem or YONTEM
    basliklar = {"User-Agent": UA,
                 "Accept": "text/html,application/xhtml+xml,"
                           "application/xml;q=0.9,*/*;q=0.8"}
    if no_cache:
        basliklar["Cache-Control"] = "no-cache"
        basliklar["Pragma"] = "no-cache"
    istek = urllib.request.Request(url, method=yontem, headers=basliklar)
    acici = acici or _ACICI
    try:
        with acici.open(istek, timeout=zaman_asimi) as y:
            return y.status, {k.lower(): v for k, v in y.headers.items()}, \
                y.read(4096), None
    except urllib.error.HTTPError as e:
        try:
            ham = e.read(4096)
        except Exception:                                   # noqa: BLE001
            ham = b""
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, ham, None
    except Exception as e:                                  # ag / DNS / TLS / timeout
        return None, {}, b"", "%s: %s" % (type(e).__name__, e)


def _govde_ozeti(ham):
    metin = (ham or b"")[:80].decode("utf-8", "replace")
    metin = re.sub(r"\s+", " ", metin).strip()
    return "".join(c for c in metin if c.isprintable())[:60]


def olc_tek(taban, yol, zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None, yontem=None,
            no_cache=False, istek_fn=None):
    """TEK URL'in canli hali. Doner: kayit sozlugu.

    sinif: ACIK | YONLENDI | KAPALI | DONGU | ARIZA

    `istek_fn` YOKLAYICIDIR (enjekte edilebilir): kabul testi buraya AG'A CIKMAYAN sahte
    bir yoklayici verir ve URL BASINA kac istek atildigini sayar."""
    istek_fn = istek_fn or _istek
    url = taban.rstrip("/") + yol
    zincir = []
    gorulen = set()
    suanki = url
    for _adim in range(YONLENDIRME_TAVANI + 1):
        if suanki in gorulen:
            return {"yol": yol, "url": url, "sinif": "DONGU", "kod": None,
                    "zincir": zincir, "tani": "yonlendirme DONGUSU: %s tekrar ediyor"
                                              % suanki, "govde": ""}
        gorulen.add(suanki)
        kod, basliklar, govde, hata = istek_fn(suanki, yontem=yontem,
                                               zaman_asimi=zaman_asimi, acici=acici,
                                               no_cache=no_cache)
        if hata:
            return {"yol": yol, "url": url, "sinif": "ARIZA", "kod": None,
                    "zincir": zincir, "tani": hata[:160], "govde": ""}
        if kod in ACIK_KODLAR:
            return {"yol": yol, "url": url,
                    "sinif": "ACIK" if not zincir else "YONLENDI",
                    "kod": kod, "zincir": zincir, "tani": "", "govde": ""}
        if 300 <= (kod or 0) < 400:
            hedef = basliklar.get("location")
            if not hedef:
                return {"yol": yol, "url": url, "sinif": "KAPALI", "kod": kod,
                        "zincir": zincir,
                        "tani": "%d yonlendirmesi `location` basligi TASIMIYOR" % kod,
                        "govde": ""}
            suanki = urllib.parse.urljoin(suanki, hedef)
            zincir.append((kod, suanki))
            continue
        tani = "HTTP %d" % kod
        for b in ("server", "cf-mitigated", "cf-cache-status", "content-type", "age"):
            if basliklar.get(b):
                tani += " · %s=%s" % (b, basliklar[b][:40])
        return {"yol": yol, "url": url, "sinif": "KAPALI", "kod": kod,
                "zincir": zincir, "tani": tani, "govde": _govde_ozeti(govde)}
    return {"yol": yol, "url": url, "sinif": "DONGU", "kod": None, "zincir": zincir,
            "tani": "yonlendirme zinciri %d adimi asti" % YONLENDIRME_TAVANI,
            "govde": ""}


def gecici_mi(kayit):
    """Bu kayit GECICI sinifta mi (BIR KEZ yeniden yoklanmali mi)?

    🔴 TEK KAYNAK. Yalniz 5xx ve ag/zaman asimi arizasi. 4xx ve DONGU/yonlendirme
    kusuru YAPISALDIR: yeniden yoklanmaz, ikinci istek de ATILMAZ."""
    sinif = kayit.get("sinif")
    if sinif == "ARIZA":
        return True
    if sinif == "KAPALI":
        kod = kayit.get("kod")
        return isinstance(kod, int) and GECICI_KOD_ALT <= kod < GECICI_KOD_UST
    return False


def yeniden_yokla(kayit, taban, yol, zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None,
                  yontem=None, uyu=time.sleep, bekleme=YENIDEN_YOKLAMA_BEKLEME,
                  istek_fn=None):
    """GECICI kaydi BIR KEZ (yalniz bir kez) yeniden yoklar. Doner: kayit sozlugu.

    🔴 FAIL-CLOSED: ikinci yoklama da basarisizsa ILK KAYIT (KAPALI/ARIZA) OLDUGU GIBI
    doner — hukum ve rc DEGISMEZ. Basariliysa ikinci kayit doner ama `gecici=True`
    isaretiyle: ACIK sayilir, SESSIZLESMEZ."""
    ilk = ("%s %s" % (kayit.get("sinif"), kayit.get("tani") or "")).strip()
    if bekleme:
        uyu(bekleme)
    ikinci = olc_tek(taban, yol, zaman_asimi=zaman_asimi, acici=acici, yontem=yontem,
                     no_cache=True, istek_fn=istek_fn)
    if ikinci["sinif"] in ("ACIK", "YONLENDI"):
        ikinci["gecici"] = True
        ikinci["ilk"] = ilk
        return ikinci
    kalici = dict(kayit)
    kalici["gecici"] = False
    kalici["ikinci_yoklama"] = ikinci.get("tani") or ikinci["sinif"]
    kalici["tani"] = ("%s · 2. yoklama (no-cache, %.0f sn sonra) DA basarisiz: %s"
                      % (kayit.get("tani") or kayit.get("sinif"), bekleme or 0.0,
                         kalici["ikinci_yoklama"]))
    return kalici


def olc(yollar, taban=SITE_VARSAYILAN, hiz=HIZ_VARSAYILAN,
        zaman_asimi=ZAMAN_ASIMI_VARSAYILAN, acici=None, yontem=None, uyu=time.sleep,
        istek_fn=None, yeniden_bekleme=YENIDEN_YOKLAMA_BEKLEME):
    """Kumenin TAMAMINI olcer (ORNEKLEME YOK). Doner: (kayitlar, sure_sn).

    `hiz` istek/sn tavanidir: istekler arasi en az 1/hiz saniye beklenir. Sure OLCULUR
    ve rapora basilir (butce karari sayiyla verilsin diye). GECICI sinifa dusen URL
    hukme yazilmadan ONCE bir kez yeniden yoklanir (bkz. `gecici_mi`)."""
    bekleme = (1.0 / hiz) if hiz and hiz > 0 else 0.0
    kayitlar = []
    bas = time.monotonic()
    for i, yol in enumerate(yollar):
        if i and bekleme:
            uyu(bekleme)
        kayit = olc_tek(taban, yol, zaman_asimi=zaman_asimi, acici=acici,
                        yontem=yontem, istek_fn=istek_fn)
        if gecici_mi(kayit):
            kayit = yeniden_yokla(kayit, taban, yol, zaman_asimi=zaman_asimi,
                                  acici=acici, yontem=yontem, uyu=uyu,
                                  bekleme=yeniden_bekleme, istek_fn=istek_fn)
        kayitlar.append(kayit)
    return kayitlar, time.monotonic() - bas


# =========================================================== HUKUM (SAF)
def degerlendir(kayitlar, kume_sayisi=None):
    """(sinif, rc, satirlar, ozet) — AG YOK, saf fonksiyon."""
    sayim = {"ACIK": 0, "YONLENDI": 0, "KAPALI": 0, "DONGU": 0, "ARIZA": 0}
    for k in kayitlar:
        sayim[k["sinif"]] = sayim.get(k["sinif"], 0) + 1
    kapali = [k for k in kayitlar if k["sinif"] in ("KAPALI", "DONGU")]
    ariza = [k for k in kayitlar if k["sinif"] == "ARIZA"]
    # GECICI: ilk yoklamada 5xx/ag arizasiydi, ikinci yoklamada (no-cache) ACIK dondu.
    # ACIK sayilir ama SAYILIR: kayboldugu an duzeltme sessizlestirmeye donusur.
    gecici = [k for k in kayitlar if k.get("gecici")]
    olculen = len(kayitlar)
    beklenen = kume_sayisi if kume_sayisi is not None else olculen

    satirlar = []
    ozet = {"olculen": olculen, "beklenen": beklenen, "sayim": sayim,
            "kapali": [{"yol": k["yol"], "kod": k["kod"], "tani": k["tani"],
                        "govde": k["govde"]} for k in kapali],
            "ariza": [{"yol": k["yol"], "tani": k["tani"]} for k in ariza],
            "gecici": [{"yol": k["yol"], "ilk": k.get("ilk", ""), "kod": k["kod"]}
                       for k in gecici],
            "yonlendirme": [{"yol": k["yol"], "zincir": k["zincir"]}
                            for k in kayitlar if k["sinif"] == "YONLENDI"]}

    if olculen != beklenen:
        satirlar.append("🔴 ORNEKLEM: kume %d URL ama %d olculdu — kirpilmis olcum "
                        "'hepsi acik' diye raporlanamaz." % (beklenen, olculen))
    if not olculen:
        satirlar.append("🔴 HIC URL OLCULMEDI -> hukum YOK (bos kume yesil DEGILDIR)")
        return "OLCULEMEDI", SINIF_RC["OLCULEMEDI"], satirlar, ozet

    for k in kapali:
        satirlar.append("🔴 KAPALI %s -> %s%s"
                        % (k["yol"], k["tani"],
                           ("  govde=%r" % k["govde"]) if k["govde"] else ""))
    for k in kayitlar:
        if k["sinif"] == "YONLENDI":
            satirlar.append("🟡 YONLENDIRME %s -> %s (zincir 200'de bitiyor; sapma "
                            "DEGIL ama sitemap kanonik URL vermeli)"
                            % (k["yol"], " -> ".join("%d %s" % z for z in k["zincir"])))
    for k in ariza:
        satirlar.append("⚪ OLCULEMEDI %s -> %s" % (k["yol"], k["tani"]))
    for k in gecici:
        satirlar.append("🟡 GECICI %s -> ilk yoklama: %s · ikinci yoklama (no-cache) "
                        "%s ACIK (uc blip'i; ACIK sayildi ama SESSIZLESTIRILMEDI)"
                        % (k["yol"], k.get("ilk") or "-", k["kod"]))

    # SAPMA KANITI, OLCUM ARIZASINI EZER: elimizde kapali kapi varken "olculemedi"ye
    # dusmek kaniti kaybettirirdi. Iki hal de sayida AYRI AYRI gorunur.
    if kapali:
        satirlar.append("HUKUM: KAPALI — %d URL kapali/dongu, %d olcum arizasi, "
                        "%d acik (%d yonlendirmeli) · GECICI=%d."
                        % (len(kapali), len(ariza), sayim["ACIK"] + sayim["YONLENDI"],
                           sayim["YONLENDI"], len(gecici)))
        return "KAPALI", SINIF_RC["KAPALI"], satirlar, ozet
    if ariza or olculen != beklenen:
        satirlar.append("HUKUM: OLCULEMEDI — %d URL olculemedi (ag/DNS/zaman asimi) · "
                        "GECICI=%d. Saglik KANITLANMADI; 'hepsi 200' VARSAYILMAZ."
                        % (len(ariza), len(gecici)))
        return "OLCULEMEDI", SINIF_RC["OLCULEMEDI"], satirlar, ozet
    satirlar.append("HUKUM: ACIK — %d/%d URL 200 (%d yonlendirme zinciriyle) · "
                    "GECICI=%d."
                    % (sayim["ACIK"] + sayim["YONLENDI"], beklenen, sayim["YONLENDI"],
                       len(gecici)))
    return "ACIK", SINIF_RC["ACIK"], satirlar, ozet


# =========================================================== FIKSTUR (YEREL SUNUCU)
# 🔴 Fikstur GERCEK bir HTTP sunucusudur (gercek soket, gercek yanit satirlari), kendi
# varsayimimizi aynalayan bir simulator DEGIL ([[nobetci-fikstur-sekli]]). Govdeler
# 3 Agu 2026'da CANLIDAN olculen sekli tasir: worker 403'u 9 baytlik `Forbidden` düz
# metindir ve AYNI yol HEAD'e 200 doner.
FIKSTUR_YOLLARI = {
    "/acik-1/": "acik",
    "/acik-2/": "acik",
    # 🔴 AYIRT EDICI VAKA: GET 403 · HEAD 200 (3 Agu'da canlida olculen davranis).
    "/araba-guneslik-klipsi-yaptirma/": "get403-head200",
    # Kontrol: metoda DUYARSIZ 403 (WAF benzeri) — HEAD mutanti bunu KACIRMAZ.
    "/tutarli-403/": "403",
    "/yok/": "404",
    "/tasindi/": "301",
    "/hedef/": "acik",
    "/dongu-a/": "dongu-a",
    "/dongu-b/": "dongu-b",
    "/uzun-zincir/": "uzun",
    "/yavas/": "yavas",
}


def _fikstur_handler():
    from http.server import BaseHTTPRequestHandler

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        gecikme_sn = 2.0

        def log_message(self, *a):                          # sessiz
            return

        def _yaz(self, kod, govde=b"", ctype="text/html; charset=utf-8", ek=None,
                 govde_gonder=True):
            self.send_response(kod)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Server", "cloudflare")
            for k, v in (ek or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if govde_gonder and govde:
                self.wfile.write(govde)

        def _sayfa(self, gorev, yontem):
            if gorev == "acik":
                self._yaz(200, b"<!doctype html><title>PRUVO</title><h1>acik</h1>",
                          govde_gonder=(yontem == "GET"))
            elif gorev == "get403-head200":
                if yontem == "GET":
                    self._yaz(403, b"Forbidden", ctype="text/plain;charset=UTF-8")
                else:
                    self._yaz(200, b"", ctype="text/plain;charset=UTF-8")
            elif gorev == "403":
                self._yaz(403, b"Forbidden", ctype="text/plain;charset=UTF-8",
                          govde_gonder=(yontem == "GET"))
            elif gorev == "404":
                self._yaz(404, b"<!doctype html><title>404</title>",
                          govde_gonder=(yontem == "GET"))
            elif gorev == "301":
                self._yaz(301, b"", ek={"Location": "/hedef/"})
            elif gorev == "dongu-a":
                self._yaz(302, b"", ek={"Location": "/dongu-b/"})
            elif gorev == "dongu-b":
                self._yaz(302, b"", ek={"Location": "/dongu-a/"})
            elif gorev == "uzun":
                self._yaz(302, b"", ek={"Location": "/uzun-zincir/?n=%d"
                                                    % int(time.time() * 1000 % 100000)})
            elif gorev == "yavas":
                time.sleep(H.gecikme_sn)
                self._yaz(200, b"gec", govde_gonder=(yontem == "GET"))
            else:
                self._yaz(404, b"", govde_gonder=(yontem == "GET"))

        def _gorev(self):
            yol = urllib.parse.urlsplit(self.path).path
            if yol.startswith("/uzun-zincir/"):
                return "uzun"
            return FIKSTUR_YOLLARI.get(yol)

        def do_GET(self):                                   # noqa: N802
            g = self._gorev()
            if g is None:
                self._yaz(404, b"yok")
                return
            self._sayfa(g, "GET")

        def do_HEAD(self):                                  # noqa: N802
            g = self._gorev()
            if g is None:
                self._yaz(404, b"", govde_gonder=False)
                return
            self._sayfa(g, "HEAD")

    return H


class FiksturSunucu:
    """`with FiksturSunucu() as s:` -> s.taban ('http://127.0.0.1:PORT')."""

    def __init__(self):
        self.httpd = None
        self.taban = None
        self._is = None

    def __enter__(self):
        from http.server import ThreadingHTTPServer
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _fikstur_handler())
        self.taban = "http://127.0.0.1:%d" % self.httpd.server_address[1]
        self._is = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._is.start()
        return self

    def __exit__(self, *a):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:                                   # noqa: BLE001
            pass
        return False


def olu_taban():
    """Dinleyicisi OLMAYAN bir taban (ag arizasi fiksturu): baglanti REDDEDILIR."""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d" % port


# =========================================================== RAPOR
def kaynak_satirlari(kaynaklar, yollar, kapsam):
    satirlar = ["KUME TURETIMI (elle liste YOK — her yol bir KAYNAKTAN gelir):"]
    for ad, sayi, var, not_ in kaynaklar:
        satirlar.append("   %-46s %5s %s%s"
                        % (ad, sayi if var else "-", "VAR" if var else "YOK",
                           ("  (%s)" % not_) if not_ else ""))
    satirlar.append("   %-46s %5d BENZERSIZ  (kapsam: %s)"
                    % ("BIRLESIM", len(yollar), kapsam))
    satirlar.append("   KAPSAM DISI (eksen siniri): /urun/<id>/ -> "
                    "tools/canli-saglik-kapisi.py K2 ekseni"
                    + ("" if kapsam in ("marka", "tam") else " · /marka/... -> "
                       "`--kapsam marka|tam`"))
    return satirlar


def gh_ozet_yaz(sinif, ozet, satirlar, sure):
    """GitHub kosum ozeti + step output (varsa). Yan etkisi YOK: env yoksa sessiz."""
    cikti = os.environ.get("GITHUB_OUTPUT")
    if cikti:
        with open(cikti, "a", encoding="utf-8") as f:
            f.write("durum=%s\n" % DURUM_ETIKET.get(sinif, "olculemedi"))
            f.write("kapali=%d\n" % len(ozet.get("kapali") or []))
            f.write("olculen=%d\n" % ozet.get("olculen", 0))
            f.write("gecici=%d\n" % len(ozet.get("gecici") or []))
    ozet_yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet_yol:
        with open(ozet_yol, "a", encoding="utf-8") as f:
            f.write("## Yayin erisim nobeti — %s\n\n" % sinif)
            f.write("* olculen URL: **%d** · sure: **%.1f s**\n"
                    % (ozet.get("olculen", 0), sure))
            f.write("* kapali: **%d** · olcum arizasi: **%d** · yonlendirme: **%d** · "
                    "GECICI (1 kez yeniden yoklandi, 200 dondu): **%d**\n\n"
                    % (len(ozet.get("kapali") or []), len(ozet.get("ariza") or []),
                       len(ozet.get("yonlendirme") or []),
                       len(ozet.get("gecici") or [])))
            for s in satirlar:
                f.write("%s\n" % s)
            f.write("\nNE YAPILMALI: kapali URL'ler ORIGIN'de degil EDGE'de kapanmis "
                    "olabilir (worker rotasi/WAF). Once yanitin `server`/`cf-mitigated` "
                    "basliklarina bak; 9 baytlik `Forbidden` duz metin worker rotasi "
                    "isaretidir.\n")


def evren_hazirla(kapsam="sayfa", kok=ROOT, ortam=None, acik_sha=None, git_fn=None,
                  ref="HEAD", api_fn=None):
    """HIZALANMIS evren. Doner: (yollar, kaynaklar, hizalama_sozlugu).

    🔴 TEK GIRIS KAPISI. Sira BAGLAYICIDIR ve her adim fail-closed'dur:
      1. `deploy_sha_bul`      — son basarili deploy'un SHA'si (yedek yol YOK),
      2. `hizalama_kanitla`    — `merge-base --is-ancestor` KANITI (beyan degil),
      3. `deploy_agaci`        — evren o SHA'nin agacindan cikarilir,
      4. `kume_turet(kok=...)` — kume O AGACTAN turer, calisma agacindan DEGIL.
    Herhangi bir adim OlcumHatasi atarsa hukum OLCULEMEDI'dir (rc 2), KAPALI DEGIL."""
    deploy_sha, sha_kaynak = deploy_sha_bul(ortam=ortam, acik=acik_sha, api_fn=api_fn)
    hz = hizalama_kanitla(deploy_sha, kok=kok, ref=ref, git_fn=git_fn)
    hz["kaynak"] = sha_kaynak
    evren_kok = deploy_agaci(hz["deploy_sha"], kok=kok, git_fn=git_fn)
    hz["evren_kok"] = evren_kok
    # K4/K5 (yerel build artefaktlari) ANCAK calisma agaci deploy SHA'sina TAM ESITSE
    # gecerlidir; aksi halde HEAD'in build'idir ve tam da kapatilan drift'i geri getirir.
    esit = (hz["ref_sha"] == hz["deploy_sha"])
    zengin_kok = kok if esit else evren_kok
    zengin_not = ("" if esit else
                  "yerel build artefaktlari KULLANILMADI: agac deploy SHA'sina esit "
                  "degil (%d commit onde)" % max(hz["ileri"], 0))
    yollar, kaynaklar = kume_turet(kok=evren_kok, kapsam=kapsam, zengin_kok=zengin_kok,
                                   zengin_not=zengin_not)
    return yollar, kaynaklar, hz


def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayin erisim nobetcisi (canli sayfa acik mi)")
    ap.add_argument("--taban", default=SITE_VARSAYILAN, help="olculecek origin")
    ap.add_argument("--kapsam", default="sayfa", choices=KAPSAMLAR)
    ap.add_argument("--hiz", type=float, default=HIZ_VARSAYILAN, help="istek/sn tavani")
    ap.add_argument("--zaman-asimi", type=float, default=ZAMAN_ASIMI_VARSAYILAN)
    ap.add_argument("--liste", action="store_true", help="yalniz kumeyi bas (AG YOK)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gh-ozet", action="store_true")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YEREL fikstur sunucusuyla kabul (dis ag YOK)")
    ap.add_argument("--deploy-sha", default=None,
                    help="son basarili deploy SHA'si (yoksa %s ortam degiskeni; "
                         "ikisi de yoksa OLCULEMEDI)" % DEPLOY_SHA_ORTAM)
    ap.add_argument("--ref", default="HEAD",
                    help="hizalamanin olculecegi ref (varsayilan HEAD)")
    a = ap.parse_args(argv)

    if a.kendini_test:
        return kendini_test()

    try:
        yollar, kaynaklar, hz = evren_hazirla(kapsam=a.kapsam, acik_sha=a.deploy_sha,
                                              ref=a.ref)
    except OlcumHatasi as e:
        # 🔴 EKSEN: hizalanamayan olcum KAPALI DEGIL OLCULEMEDI'dir (rc 2).
        print("⚪ OLCULEMEDI (evren hizalanamadi): %s" % e)
        if a.gh_ozet:
            gh_ozet_yaz("OLCULEMEDI", {"olculen": 0},
                        ["evren hizalanamadi: %s" % e], 0.0)
        return SINIF_RC["OLCULEMEDI"]

    print("YAYIN ERISIM NOBETCISI — %s (%s)" % (a.taban, a.kapsam))
    print("-" * 78)
    print(hz["satir"])
    print("EVREN KOKU: deploy %s agaci (%s) — calisma agaci HEAD'i DEGIL"
          % (hz["deploy_sha"][:12], hz["kaynak"]))
    for s in kaynak_satirlari(kaynaklar, yollar, a.kapsam):
        print(s)
    if a.liste:
        for y in yollar:
            print(y)
        print("KUME: %d URL (AG KULLANILMADI — hukum YOK)" % len(yollar))
        return 0

    print("YONTEM: %s (HEAD YETMEZ — olculdu: ayni URL HEAD 200 / GET 403)" % YONTEM)
    print("HIZ: %.1f istek/sn · zaman asimi %.0f s" % (a.hiz, a.zaman_asimi))
    kayitlar, sure = olc(yollar, taban=a.taban, hiz=a.hiz, zaman_asimi=a.zaman_asimi)
    sinif, rc, satirlar, ozet = degerlendir(kayitlar, kume_sayisi=len(yollar))
    # Kanit satiri HUKMU BESLEYEN kumeye girer ([[kapi-ozeti-hukumden-ayrisir]]): kosum
    # ozetinde "hangi SHA'nin kumesi olculdu" sorusu cevapsiz kalmaz.
    satirlar = [hz["satir"]] + satirlar
    ozet["hizalama"] = {"deploy_sha": hz["deploy_sha"], "ref_sha": hz["ref_sha"],
                        "ileri": hz["ileri"], "kaynak": hz["kaynak"]}
    print("-" * 78)
    for s in satirlar:
        print(s)
    print("SURE: %.1f s (%d URL · %.1f istek/sn olculen)"
          % (sure, len(kayitlar), (len(kayitlar) / sure) if sure else 0.0))
    print("SINIF: %s (rc %d) · GECICI=%d (5xx/ag arizasi bir kez yeniden yoklandi ve "
          "ACIK dondu)" % (sinif, rc, len(ozet.get("gecici") or [])))
    if a.json:
        print(json.dumps({"sinif": sinif, "rc": rc, "sure_sn": round(sure, 2),
                          "kapsam": a.kapsam, "taban": a.taban, "ozet": ozet},
                         ensure_ascii=False, indent=2, sort_keys=True))
    if a.gh_ozet:
        gh_ozet_yaz(sinif, ozet, satirlar, sure)
    return rc


# =========================================================== KENDINI TEST (YEREL)
def kendini_test():
    """YEREL fikstur sunucusuyla hukum kabulu. DIS AG YOK.

    Bu kol `tools/yayin-erisim-test.py`nin bir alt kumesidir; alarm is akisi tikandiginda
    elle kosulabilsin diye burada da durur. TAM takim (kablolama + mutasyon nobetleri)
    kabul testindedir."""
    fails = []
    sayac = []

    def iddia(ad, kosul, detay=""):
        sayac.append(ad)
        print(("  ✔ " if kosul else "  ✘ ") + ad + (("   [%s]" % detay) if detay else ""))
        if not kosul:
            fails.append(ad)

    print("YAYIN ERISIM NOBETCISI — YEREL FIKSTUR KABULU")
    with FiksturSunucu() as s:
        kayitlar, _ = olc(["/acik-1/", "/acik-2/"], taban=s.taban, hiz=0)
        sinif, rc, _, _ = degerlendir(kayitlar)
        iddia("KONTROL: hepsi 200 -> ACIK (yanlis-pozitif yok)",
              sinif == "ACIK" and rc == 0, "%s rc=%d" % (sinif, rc))

        kayitlar, _ = olc(["/acik-1/", "/araba-guneslik-klipsi-yaptirma/"],
                          taban=s.taban, hiz=0)
        sinif, rc, _, _ = degerlendir(kayitlar)
        iddia("OLDURUCU: GET 403 / HEAD 200 olan URL -> KAPALI (rc 1)",
              sinif == "KAPALI" and rc == 1, "%s rc=%d" % (sinif, rc))

        kayitlar, _ = olc(["/yok/"], taban=s.taban, hiz=0)
        sinif, _, _, _ = degerlendir(kayitlar)
        iddia("OLDURUCU: 404 -> KAPALI", sinif == "KAPALI", sinif)

        kayitlar, _ = olc(["/dongu-a/"], taban=s.taban, hiz=0)
        sinif, _, _, ozet = degerlendir(kayitlar)
        iddia("OLDURUCU: 3xx DONGUSU -> KAPALI", sinif == "KAPALI",
              "%s %s" % (sinif, ozet["kapali"]))

        kayitlar, _ = olc(["/tasindi/"], taban=s.taban, hiz=0)
        sinif, rc, _, ozet = degerlendir(kayitlar)
        iddia("301 -> 200 zinciri KAPALI DEGIL ama RAPORLANIR",
              sinif == "ACIK" and rc == 0 and len(ozet["yonlendirme"]) == 1,
              "%s yonlendirme=%d" % (sinif, len(ozet["yonlendirme"])))

    # Bekleme SAHTE: gercek 5 sn beklenmez (kabul testi ayni yordami kullanir).
    kayitlar, _ = olc(["/acik-1/"], taban=olu_taban(), hiz=0, zaman_asimi=3,
                      uyu=lambda _s: None)
    sinif, rc, _, _ = degerlendir(kayitlar)
    iddia("FAIL-CLOSED: ag yok (baglanti reddedildi, 2 kez) -> OLCULEMEDI rc 2, "
          "YESIL DEGIL", sinif == "OLCULEMEDI" and rc == 2, "%s rc=%d" % (sinif, rc))

    # GECICI SINIF — AG'A CIKMAYAN sahte yoklayici (10 Agu 2026 yanlis-pozitifi).
    for ad, ikinci_kod, bek_sinif, bek_rc, bek_gecici in (
            ("503 -> 200: GECICI (ACIK ama sayilir)", 200, "ACIK", 0, 1),
            ("KONTROL 503 -> 503: KAPALI KALIR (yeniden yoklama korlestirmez)",
             503, "KAPALI", 1, 0)):
        kodlar = iter([503, ikinci_kod])

        def sahte(url, yontem=None, zaman_asimi=None, acici=None, no_cache=False,
                  _k=kodlar):
            return next(_k), {"server": "cloudflare"}, b"blip", None

        kayitlar, _ = olc(["/blip/"], taban="http://ornek.invalid", hiz=0,
                          istek_fn=sahte, uyu=lambda _s: None)
        sinif, rc, satirlar, ozet = degerlendir(kayitlar)
        iddia("GECICI: %s" % ad,
              sinif == bek_sinif and rc == bek_rc
              and len(ozet["gecici"]) == bek_gecici
              and any("GECICI=%d" % bek_gecici in s for s in satirlar),
              "%s rc=%d gecici=%d" % (sinif, rc, len(ozet["gecici"])))

    print("%d iddia, %d KIRMIZI." % (len(sayac), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
