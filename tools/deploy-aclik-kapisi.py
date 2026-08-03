#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/deploy-aclik-kapisi.py — YAYIN ACLIGI (starvation) NOBETCISI.

NE OLCER: "art arda gelen push'larda BASLAMIS bir kosum oldurulup icerigi yayinsiz
kalabilir mi". Uc eksen, hepsi TEK BASINA hukum verir ([[hukum-yanlis-birimde]]):

  E1  ESZAMANLILIK SOZLESMESI  — Pages yayin akisinin `concurrency` blogu:
      grup VAR ve `cancel-in-progress` FALSE. (statik, agsiz, BLOKLAYICI)
  E2  YAYIN ZINCIRI            — `deploy` -> needs build · `yayin` -> needs deploy;
      zincirde kosula/`continue-on-error`a bagli KACIS yok. (statik, agsiz, BLOKLAYICI)
  E3  ESZAMANLILIK SIMULASYONU — E1'den OKUNAN ayarla, art arda push senaryosu
      KOSTURULUR: BASLAMIS her kosum `deploy`ina ulasmali. (statik, agsiz, BLOKLAYICI)
  E4  CANLI TARIH              — gercek kosum gecmisinde iptallerin SINIFI: kuyrukta
      iptal (zararsiz) mi, CALISIRKEN iptal (aclik) mi. (`--canli`, ag ister, AYRI EV)

═══════════════════════════════════════════════════════════════════════════════
NEDEN VAR — OLCULEN OLAY ve OLCULEN YANLIS TESHIS (3 Agu 2026)
═══════════════════════════════════════════════════════════════════════════════
3 Agu gunu `Build & deploy to GitHub Pages` akisinda 25 kosumun 8'i `cancelled` ile
bitti ve `tools/parite-test.js` rc=3 (OLCULEMEDI) verdi: "site en son 142,1 dk once
deploy etmis (sinir 30,0)". Ilk teshis "`cancel-in-progress: true` kosumlari olduruyor"
idi. OLCULDU ve CURUDU — iki ayri sayiyla:

  (a) `cancel-in-progress` ZATEN `false` (30 Tem'den beri, deploy.yml :: concurrency).
  (b) Iptal edilen kosumlarin `jobs` dizisi BOS: 30829845771 ve 30831100269 icin
      GitHub API `jobs: []` dondu — yani o kosumlar TEK BIR IS bile BASLATMADI.
      Sureleri de bunu soyluyor (93 sn · 92 sn · 122 sn · 158 sn), `build` isi ise
      ayni gun 1487 sn (24,8 dk) surdu.

Yani bu iptaller KUYRUKTA iptaldir: `cancel-in-progress: false` altinda GitHub bir
grupta EN FAZLA 1 BEKLEYEN kosum tutar ve yeni bekleyen geldiginde ONCEKI BEKLEYENI
iptal eder. main DOGRUSAL oldugu icin ayakta kalan bekleyen kosumun agaci, iptal
edilenlerin icerigini ZATEN TASIR -> bu iptallerde ICERIK KAYBI YOKTUR. Ilk raporun
"45f30fd7'nin icerigi ancak saatler sonra cikabildi" cumlesi bir GECIKME olgusudur,
KAYIP degil.

GERCEK ACLIK SINIFI BASKADIR ve bu kapinin konusu odur: bir kosum BASLADIKTAN sonra
oldurulurse (`cancel-in-progress: true`) o kosumun `deploy` isi HIC kosmaz. Push akisi
kosum suresinden hizliysa HICBIR kosum tamamlanamaz -> yayin SINIRSIZ acliga girer
(30 Tem olcumu: 7 ARDISIK iptal, iki basarili yayin arasi 37,7 dk, o pencereye dusen
her yeni urun canlida 404). Bugunku `false` ayari bu sinifi kapatir; BU KAPI o ayarin
GERI ALINAMAMASINI saglar.

═══════════════════════════════════════════════════════════════════════════════
KARAR — NE DEGISTIRILDI, NE DEGISTIRILMEDI (3 Agu 2026, olculerek)
═══════════════════════════════════════════════════════════════════════════════
ESZAMANLILIK AYARI DEGISTIRILMEDI. `cancel-in-progress: false` + tek-bekleyen kuyrugu
OLCULEN veriyle DOGRU secimdir ve degistirilirse GERILEME olur:
  * `true`  -> calisan kosum olur, icerik kaybi + sinirsiz aclik (yukaridaki olcum).
  * grupsuz -> Pages deploy'lari PARALEL kosar; `actions/deploy-pages` ayni anda iki
    deployment kabul etmez, ustelik SONRA BITEN ESKI agac son soz olur (yayin geri
    sarmasi). Grup, seri yayin garantisinin TA KENDISIDIR.
Onerilen (b) secenegi — `deploy`i `workflow_run`/zamanlanmis AYRI bir akisa tasimak —
REDDEDILDI: bu depoda `deploy` -> `needs: build` bagi, ~100 kabul adiminin KIRMIZISININ
YAYINI DURDURMASI demektir (fail-closed yayin sozlesmesi). Deploy'u build'den ayirmak,
kirmizi kapilarla canliya cikmayi MUMKUN kilardi — aclik gecikmesini onarmak icin yayin
BUTUNLUGUNU bozmak, olculen zararin buyugunu secmektir.
Onerilen (c) secenegi — urun partilerini tek push'ta birlestirmek — MaCiT duzlemidir ve
CI'da ZORLANAMAZ; ustelik gecikmenin olculen agirlikli sebebi de degildir (asagi).

GECIKMENIN OLCULEN SEBEBI ESZAMANLILIK DEGIL, `build` SURESIDIR (kosum 30838521694):
  build 1487 sn (24,8 dk · 104 adim) · deploy 34 sn · yayin 38 sn.
  build'in %71'i DORT adimda: "Statik sayfalari uret" 316 sn · "Yasal sayfa drift
  kapisi" 306 sn · "Piksel<->katalog parite kapisi" 299 sn · "Yayin kopyasi fiyat
  paritesi" 139 sn = 1060 sn. DORDU DE 17k urunluk `build.py` uretimini AYRI AYRI
  yeniden kosar.
Grup serilestirdigi icin yayin TAVANI = 1 deploy / ~26 dk; push araligi parti sirasinda
2-5 dk. Ustune ayni gun 25 kosumun 6'si `failure` ile bitti ve `deploy` -> `needs: build`
oldugu icin o dongulerde HIC yayin inmedi. 142 dk'lik bosluk bu IKI carpanin toplamidir.
`build.py` uretiminin TEK KEZ yapilip uc kapiya ARTEFAKT olarak verilmesi build'i ~10
dk'ya cekerdi; bu AYRI ve BUYUK bir istir (bu kapinin konusu DEGIL, raporda sayiyla
teslim edildi).

═══════════════════════════════════════════════════════════════════════════════
NEDEN SIMULASYON (E3) — statik bayrak okumak NEDEN YETMEZ
═══════════════════════════════════════════════════════════════════════════════
E1 yalniz bir bayragin degerini iddia eder. Bayragin ANLAMI ("baslamis kosum olmez")
ancak GitHub'in grup semantigi KOSTURULARAK olculur. E3 bu semantigi modelleyip
ayari GERCEK dosyadan okur ve senaryoyu isletir; boylece kapi "true yazmayin" diyen bir
metin kontrolu degil, "su senaryoda su kadar kosum oldu" diyen bir OLCUM olur.
FIKSTUR `seyrek-push` KONTROL MUTANTIDIR ([[fikstur-degeri-mutasyon-koru]]): push
araligi kosum suresinden UZUN oldugunda `true` de `false` da YESILDIR. Yani E3'un
kirmizisi bayragin KENDISINDEN degil, senaryo DINAMIGINDEN dogar — simulasyon
gercekten simule etmezse bu fikstur onu ele verir.

═══════════════════════════════════════════════════════════════════════════════
CIKIS KODLARI
═══════════════════════════════════════════════════════════════════════════════
    0  TEMIZ        eksenlerin hepsi yesil
    1  IHLAL        en az bir eksen kirmizi
    2  OLCULEMEDI   ayristirici/dosya/API yok — YESIL DEGIL, KIRMIZI DA DEGIL

KULLANIM
    python3 tools/deploy-aclik-kapisi.py                # statik eksenler (E1-E3)
    python3 tools/deploy-aclik-kapisi.py --kendini-test # fikstur + MUTASYON bataryasi
    python3 tools/deploy-aclik-kapisi.py --canli        # E4: gercek kosum gecmisi (gh)
"""
import argparse
import copy
import importlib.util
import json
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORKFLOW_DIZIN = os.path.join(ROOT, ".github", "workflows")

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"

# Pages yayin isini TANIYAN eylem. Akis dosyasi ADIYLA aranmaz: ad degisebilir, bu
# `uses:` degeri yayin isinin TANIMIDIR.
PAGES_EYLEMI = "actions/deploy-pages"

# Yayin zinciri: (is, beklenen bagimlilik). `yayin` isi deploy'dan SONRA kosmali, aksi
# halde dogrulayacagi sayfa henuz canlida degildir (deploy.yml :: jobs.yayin basligi).
ZINCIR = (("deploy", "build"), ("yayin", "deploy"))

# E4 butcesi: her iptal/hata kosumu icin AYRI bir `jobs` sorgusu gerekir.
CANLI_PENCERE = 30
CANLI_IS_SORGU_TAVANI = 20


class OlcumHatasi(Exception):
    """Veri cekilemedi/anlasilamadi -> YESIL degil, OLCULEMEDI (rc 2)."""


# ---------------------------------------------------------------------------
# YAML — TEK KAYNAK, IKIZ TANIM YOK ([[ikiz-tanim-sessiz-ayrisma]])
# ---------------------------------------------------------------------------
# Ayristirici bu dosyada YENIDEN YAZILMAZ: tools/cron-nabiz-kapisi.py'deki
# `yaml_belge` (PyYAML -> ruby/psych, fail-closed) MODUL olarak yuklenir. Ikinci bir
# kopya tutulsaydi iki okuyucu sessizce ayrisabilirdi; burada ayrisacak ikinci mantik
# YOKTUR. Yukleme kendisi de fail-closed: kaynak kaybolursa kapi taklide DUSMEZ.
_NABIZ_SOZLESME = ("yaml_belge", "yaml_ayristirici_adi", "OlcumHatasi")


def _nabiz_yukle():
    yol = os.path.join(TOOLS, "cron-nabiz-kapisi.py")
    if not os.path.exists(yol):
        raise OlcumHatasi(
            "tools/cron-nabiz-kapisi.py YOK -> ortak YAML ayristiricisi (yaml_belge) "
            "yuklenemedi. Bu kapi is akisi dosyalarini METIN TAKLIDIYLE okumaz "
            "([[mimar-kapi-parser-taklidi]]), o yuzden YESIL SAYMAZ.")
    spec = importlib.util.spec_from_file_location("pruvo_cron_nabiz", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_cron_nabiz"] = mod
    spec.loader.exec_module(mod)
    for ad in _NABIZ_SOZLESME:
        if not hasattr(mod, ad):
            raise OlcumHatasi(
                "tools/cron-nabiz-kapisi.py'de %s YOK -> ayristirici sozlesmesi degismis, "
                "tuketicileri guncelle (fail-closed)" % ad)
    return mod


def yaml_belge(metin):
    """YAML metni -> python nesnesi. Hatalari BU dosyanin OlcumHatasi'na cevirir."""
    nabiz = _nabiz_yukle()
    try:
        return nabiz.yaml_belge(metin)
    except nabiz.OlcumHatasi as e:
        raise OlcumHatasi(str(e))


def ayristirici_adi():
    return _nabiz_yukle().yaml_ayristirici_adi()


# ---------------------------------------------------------------------------
# KESIF — Pages yayin akisi
# ---------------------------------------------------------------------------
def _is_kullanimlari(job):
    """Bir job'daki tum `uses:` degerleri (adim duzeyi + job duzeyi reusable)."""
    cikti = []
    if not isinstance(job, dict):
        return cikti
    if isinstance(job.get("uses"), str):
        cikti.append(job["uses"])
    for adim in job.get("steps") or []:
        if isinstance(adim, dict) and isinstance(adim.get("uses"), str):
            cikti.append(adim["uses"])
    return cikti


def yayin_akislari(dizin=None):
    """[(dosya_adi, govde), ...] — `actions/deploy-pages` KOSTURAN is akislari.

    FAIL-CLOSED: dizin yoksa ya da HIC yayin akisi bulunmazsa OlcumHatasi. "Bulamadim ->
    ihlal yok -> yesil" bu kapinin en tehlikeli sessiz halidir (dosya yeniden
    adlandirilirsa kapi hicbir sey olcmeden yesil yanardi)."""
    dizin = dizin or WORKFLOW_DIZIN
    if not os.path.isdir(dizin):
        raise OlcumHatasi("is akisi dizini YOK: %s" % dizin)
    bulunan = []
    for ad in sorted(os.listdir(dizin)):
        if not ad.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(dizin, ad), encoding="utf-8") as f:
            govde = yaml_belge(f.read())
        if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
            continue
        for job in govde["jobs"].values():
            if any(u.split("@")[0] == PAGES_EYLEMI for u in _is_kullanimlari(job)):
                bulunan.append((ad, govde))
                break
    if not bulunan:
        raise OlcumHatasi(
            "HICBIR is akisinda `%s` kullanimi bulunamadi -> Pages yayin akisi "
            "TANINAMADI. Kapi olcecek nesneyi bulamadi, YESIL SAYMAZ." % PAGES_EYLEMI)
    return bulunan


def yayin_isi_adi(govde):
    """Pages'e yayinlayan job'un ADI (deploy.yml'de `deploy`). Ad SABIT DEGILDIR,
    `uses:` degerinden TURETILIR — yeniden adlandirma kapiyi korletmesin."""
    for ad, job in (govde.get("jobs") or {}).items():
        if any(u.split("@")[0] == PAGES_EYLEMI for u in _is_kullanimlari(job)):
            return str(ad)
    return None


# ---------------------------------------------------------------------------
# E1 — ESZAMANLILIK SOZLESMESI
# ---------------------------------------------------------------------------
def eszamanlilik(govde):
    """(grup, iptal_bayragi, tani) — kok `concurrency` blogundan.

    Bayrak DEGERI YAML'in cozdugu haliyle alinir: `false` ile `"false"` AYNI SEY
    DEGILDIR ve GitHub tirnakli dizeyi de false sayar; ikisi de kabul edilir, ama
    `true`/`"true"`/ifade (`${{ ... }}`) KABUL EDILMEZ (ifade CALISMA ANINDA cozulur,
    statik olarak "olduremez" DIYEMEYIZ -> fail-closed)."""
    ham = govde.get("concurrency")
    if ham is None:
        return None, None, "kok `concurrency` blogu YOK"
    if isinstance(ham, str):
        return ham, None, "`concurrency` duz dize (grup adi) — `cancel-in-progress` YOK"
    if not isinstance(ham, dict):
        return None, None, "`concurrency` beklenmedik tur: %s" % type(ham).__name__
    grup = ham.get("group")
    bayrak = ham.get("cancel-in-progress")
    if isinstance(bayrak, str):
        s = bayrak.strip()
        if "${{" in s:
            return grup, "ifade", "`cancel-in-progress` bir IFADE: %r" % bayrak
        if s.lower() in ("true", "false"):
            bayrak = (s.lower() == "true")
        else:
            return grup, "cozulemedi", "`cancel-in-progress` cozulemedi: %r" % bayrak
    return grup, bayrak, ""


def e1_degerlendir(dosya, govde):
    grup, bayrak, tani = eszamanlilik(govde)
    sorunlar = []
    if grup is None or not str(grup).strip():
        sorunlar.append(
            "🔴 E1 %s: `concurrency.group` YOK (%s). Grupsuz Pages yayini PARALEL kosar; "
            "`actions/deploy-pages` ayni anda iki deployment kabul etmez ve SONRA BITEN "
            "ESKI agac son soz olur (yayin geri sarmasi)." % (dosya, tani or "-"))
    if bayrak is None:
        sorunlar.append(
            "🔴 E1 %s: `cancel-in-progress` BEYAN EDILMEMIS (%s). Varsayilan bugun `false` "
            "olsa da beyansiz birakmak sozlesmeyi GitHub'in varsayilanina emanet eder; "
            "bu kapinin olctugu sey ACIK BEYANDIR." % (dosya, tani or "-"))
    elif bayrak is True:
        sorunlar.append(
            "🔴 E1 %s: `cancel-in-progress: true`. BASLAMIS kosum oldurulur ve o kosumun "
            "`deploy` isi HIC kosmaz -> push akisi kosum suresinden hizliysa yayin "
            "SINIRSIZ acliga girer (olculdu 30 Tem: 7 ardisik iptal, 37,7 dk yayinsiz "
            "pencere, o pencereye dusen her urun canlida 404)." % dosya)
    elif bayrak in ("ifade", "cozulemedi"):
        sorunlar.append(
            "🔴 E1 %s: %s. Calisma aninda cozulen bir deger icin 'baslamis kosum olmez' "
            "STATIK olarak IDDIA EDILEMEZ (fail-closed)." % (dosya, tani))
    return sorunlar, {"grup": grup, "cancel_in_progress": bayrak}


# ---------------------------------------------------------------------------
# E2 — YAYIN ZINCIRI
# ---------------------------------------------------------------------------
def _needs_kumesi(job):
    ham = (job or {}).get("needs")
    if ham is None:
        return set()
    if isinstance(ham, str):
        return {ham}
    if isinstance(ham, list):
        return set(str(x) for x in ham)
    return set()


def e2_degerlendir(dosya, govde):
    """`deploy` -> needs build · `yayin` -> needs deploy, ve zincirde KACIS yok.

    KACIS = `if:` kosulu (kosum sirasinda atlanabilir) ya da `continue-on-error: true`
    (kirmizi yayini durdurmaz). Ikisi de bu zincirde FAIL-OPEN'dir: `deploy`in build'e
    bagli olmasinin TEK anlami "kapilar kirmiziysa canliya cikma"dir."""
    joblar = govde.get("jobs") or {}
    sorunlar = []
    for is_adi, beklenen in ZINCIR:
        job = joblar.get(is_adi)
        if not isinstance(job, dict):
            sorunlar.append(
                "🔴 E2 %s: `%s` isi YOK -> yayin zinciri kirik (bu is adlari "
                "tools/yayin-gecikme-nobeti.py'nin de YAYIN YETKILISIDIR)."
                % (dosya, is_adi))
            continue
        needs = _needs_kumesi(job)
        if beklenen not in needs:
            sorunlar.append(
                "🔴 E2 %s: `%s.needs` icinde `%s` YOK (bugun: %s). Bag koparsa %s, %s "
                "kirmiziyken de kosar = FAIL-OPEN yayin."
                % (dosya, is_adi, beklenen, sorted(needs) or "-", is_adi, beklenen))
        if "if" in job:
            sorunlar.append(
                "🔴 E2 %s: `%s` isinde `if:` kosulu VAR (%r). Kosullu bir yayin isi NORMAL "
                "bir push'ta SESSIZCE atlanabilir; bu kapinin olctugu aclikla ayirt "
                "edilemez bir hal uretir." % (dosya, is_adi, job.get("if")))
        if job.get("continue-on-error") is True:
            sorunlar.append(
                "🔴 E2 %s: `%s` isinde `continue-on-error: true` VAR -> kirmizi zinciri "
                "DURDURMAZ (beyansiz fail-open)." % (dosya, is_adi))
    return sorunlar


# ---------------------------------------------------------------------------
# E3 — ESZAMANLILIK SIMULASYONU
# ---------------------------------------------------------------------------
def simule(iptal_calisani, kosum_dk, push_anlari, deploy_dk=0.6):
    """GitHub `concurrency` grubu semantigini KOSTURUR.

    MODELLENEN KURALLAR (GitHub Actions concurrency, tek grup):
      * Grupta ayni anda EN FAZLA 1 CALISAN kosum vardir.
      * Yeni kosum gelir ve calisan YOKSA -> hemen calismaya baslar.
      * Calisan VARSA:
          - `cancel-in-progress: true`  -> CALISAN OLDURULUR, yeni kosum baslar.
          - `cancel-in-progress: false` -> yeni kosum BEKLEMEYE alinir; grupta zaten
            bekleyen varsa ONCEKI BEKLEYEN iptal edilir (tavan: 1 calisan + 1 bekleyen).
      * Calisan biterse `deploy` isi kosar; OLDURULEN kosumun `deploy`i HIC kosmaz.

    Doner: olcum sozlugu. `calisirken_iptal` bu kapinin YASAKLADIGI sinifitir;
    `kuyrukta_iptal` ZARARSIZDIR (main dogrusaldir, ayakta kalan bekleyen kosumun agaci
    iptal edilenlerin icerigini zaten tasir — bkz. modul basligi (b) olcumu)."""
    if kosum_dk <= 0:
        raise OlcumHatasi("kosum suresi pozitif olmali (verilen: %r)" % kosum_dk)
    calisan = None          # (id, bitis_dk)
    bekleyen = None         # id
    basladi = set()
    sonuc = {}
    deploy_bitisleri = []
    sirali = sorted(push_anlari)
    i = 0
    while i < len(sirali) or calisan is not None:
        sonraki_push = sirali[i] if i < len(sirali) else None
        if calisan is not None and (sonraki_push is None or calisan[1] <= sonraki_push):
            simdi = calisan[1]
            sonuc[calisan[0]] = "tamamlandi"
            deploy_bitisleri.append(simdi + deploy_dk)
            calisan = None
            if bekleyen is not None:
                calisan = (bekleyen, simdi + kosum_dk)
                basladi.add(bekleyen)
                bekleyen = None
            continue
        simdi = sonraki_push
        yeni = i
        i += 1
        if calisan is None:
            calisan = (yeni, simdi + kosum_dk)
            basladi.add(yeni)
        elif iptal_calisani:
            sonuc[calisan[0]] = "calisirken_iptal"
            calisan = (yeni, simdi + kosum_dk)
            basladi.add(yeni)
        else:
            if bekleyen is not None:
                sonuc[bekleyen] = "kuyrukta_iptal"
            bekleyen = yeni
    if bekleyen is not None:  # pragma: no cover — dongu bekleyeni daima calistirir
        sonuc[bekleyen] = "kuyrukta_iptal"

    calisirken = sorted(k for k, v in sonuc.items() if v == "calisirken_iptal")
    kuyrukta = sorted(k for k, v in sonuc.items() if v == "kuyrukta_iptal")
    # YAYINSIZ PENCERE: ilk push'tan itibaren, ardisik iki deploy arasindaki EN UZUN
    # bosluk. `true` altinda firtina boyunca hic deploy inmedigi icin bu sayi push
    # sayisiyla BUYUR; `false` altinda ~2 x kosum suresiyle SINIRLIDIR.
    sinirlar = [sirali[0]] + sorted(deploy_bitisleri) if sirali else sorted(deploy_bitisleri)
    yayinsiz = 0.0
    for onceki, sonraki in zip(sinirlar, sinirlar[1:]):
        yayinsiz = max(yayinsiz, sonraki - onceki)
    return {
        "push": len(sirali),
        "basladi": len(basladi),
        "deploy_kosan": len(deploy_bitisleri),
        "calisirken_iptal": len(calisirken),
        "kuyrukta_iptal": len(kuyrukta),
        "yayinsiz_pencere_dk": round(yayinsiz, 2),
        "kosum_dk": kosum_dk,
    }


# SENARYO: art arda IKI push — ikincisi birincinin kosumu BITMEDEN gelir. Sayilar
# 3 Agu olcumunden: build 24,8 dk; parti sirasinda push araligi 2-5 dk.
OLCULEN_KOSUM_DK = 24.8
ARDISIK_PUSH_ARALIGI_DK = 3.0
FIRTINA_PUSH = 8


def e3_degerlendir(dosya, bayrak):
    """E1'den OKUNAN ayarla iki senaryo kosturulur ve BASLAMIS her kosumun `deploy`ina
    ulastigi olculur. Ayar okunamadiysa (None/ifade) simulasyon YAPILMAZ -> OLCULEMEDI
    degil, E1 zaten kirmizidir; burada sessizce yesil DONMEZ."""
    if bayrak not in (True, False):
        return ["⚪ E3 %s: `cancel-in-progress` okunamadigi icin simulasyon KOSMADI "
                "(E1 hukmu gecerlidir)." % dosya], None
    senaryolar = {
        "ardisik-iki-push": [0.0, ARDISIK_PUSH_ARALIGI_DK],
        "firtina-%d-push" % FIRTINA_PUSH:
            [ARDISIK_PUSH_ARALIGI_DK * k for k in range(FIRTINA_PUSH)],
    }
    sorunlar = []
    olcumler = {}
    for ad, anlar in sorted(senaryolar.items()):
        o = simule(bayrak, OLCULEN_KOSUM_DK, anlar)
        olcumler[ad] = o
        if o["calisirken_iptal"]:
            sorunlar.append(
                "🔴 E3 %s [%s]: BASLAMIS %d kosumun %d'i CALISIRKEN olduruldu; `deploy` "
                "yalniz %d kez kostu. O kosumlarin icerigi kendi yayinini HIC ALMAZ ve "
                "yayinsiz pencere %.1f dk'ya cikar (kosum suresi %.1f dk)."
                % (dosya, ad, o["basladi"], o["calisirken_iptal"], o["deploy_kosan"],
                   o["yayinsiz_pencere_dk"], o["kosum_dk"]))
        elif o["deploy_kosan"] != o["basladi"]:
            sorunlar.append(
                "🔴 E3 %s [%s]: BASLAYAN kosum %d, `deploy` kosan %d — baslamis her kosum "
                "deploy'una ULASMALI." % (dosya, ad, o["basladi"], o["deploy_kosan"]))
    return sorunlar, olcumler


# ---------------------------------------------------------------------------
# STATIK DEGERLENDIRME (E1+E2+E3)
# ---------------------------------------------------------------------------
def degerlendir(akislar=None):
    akislar = akislar if akislar is not None else yayin_akislari()
    sorunlar = []
    olcum = {"ayristirici": ayristirici_adi(), "akislar": {}}
    for dosya, govde in akislar:
        e1_sorun, e1_olcum = e1_degerlendir(dosya, govde)
        e2_sorun = e2_degerlendir(dosya, govde)
        e3_sorun, e3_olcum = e3_degerlendir(dosya, e1_olcum["cancel_in_progress"])
        sorunlar.extend(e1_sorun + e2_sorun + e3_sorun)
        olcum["akislar"][dosya] = {
            "yayin_isi": yayin_isi_adi(govde),
            "eszamanlilik": e1_olcum,
            "simulasyon": e3_olcum,
        }
    return sorunlar, olcum


# ---------------------------------------------------------------------------
# E4 — CANLI TARIH (ag ister; AYRI EV, yayini bloklamaz)
# ---------------------------------------------------------------------------
def _gh_json(yol):
    try:
        p = subprocess.run(["gh", "api", yol], capture_output=True, text=True, timeout=90)
    except FileNotFoundError:
        raise OlcumHatasi("`gh` YOK -> canli eksen olculemedi (rc 2, yesil DEGIL)")
    except subprocess.TimeoutExpired:
        raise OlcumHatasi("`gh api %s` zaman asimi" % yol)
    if p.returncode != 0:
        raise OlcumHatasi("`gh api %s` rc=%d: %s"
                          % (yol, p.returncode, (p.stderr or "").strip()[:300]))
    try:
        return json.loads(p.stdout)
    except ValueError as e:
        raise OlcumHatasi("`gh api %s` ciktisi JSON degil: %s" % (yol, e))


def canli_olc(depo=None, pencere=CANLI_PENCERE, akis="deploy.yml"):
    """Gercek kosum gecmisinde IPTALLERIN SINIFINI ayirir.

    kuyrukta_iptal  = `cancelled` ve HIC is baslamamis (jobs bos)  -> ZARARSIZ
    calisirken_iptal= `cancelled` ama en az bir is baslamis        -> ACLIK SINIFI
    yayinsiz_dongu  = `build` success ama `deploy` skipped/cancelled -> yayin inmedi
    Bu ayrim 3 Agu'deki yanlis teshisin ta kendisidir: ikisi de raporda `cancelled`
    gorunur, ama biri normal, digeri onarilmasi gereken bir arizadir."""
    g = _gh_json("repos/%s/actions/workflows/%s/runs?branch=main&per_page=%d"
                 % (depo or DEPO, akis, pencere))
    if not isinstance(g, dict) or "workflow_runs" not in g:
        raise OlcumHatasi("API govdesinde `workflow_runs` YOK — sekil degismis olabilir")
    kosumlar = g["workflow_runs"]
    if not isinstance(kosumlar, list) or not kosumlar:
        raise OlcumHatasi("`workflow_runs` bos/liste degil — hicbir kosum gorulmedi")

    olcum = {"pencere": len(kosumlar), "sonuclar": {}, "kuyrukta_iptal": 0,
             "calisirken_iptal": 0, "yayinsiz_dongu": 0, "sorgulanmayan": 0,
             "calisirken_iptal_kosumlari": [], "yayinsiz_dongu_kosumlari": []}
    sorgu = 0
    for k in kosumlar:
        son = k.get("conclusion")
        olcum["sonuclar"][son or k.get("status")] = \
            olcum["sonuclar"].get(son or k.get("status"), 0) + 1
        if son not in ("cancelled", "failure", "success"):
            continue
        if sorgu >= CANLI_IS_SORGU_TAVANI:
            olcum["sorgulanmayan"] += 1
            continue
        sorgu += 1
        j = _gh_json("repos/%s/actions/runs/%s/jobs?per_page=100" % (depo or DEPO, k["id"]))
        isler = j.get("jobs") if isinstance(j, dict) else None
        if not isinstance(isler, list):
            raise OlcumHatasi("kosum %s: `jobs` okunamadi (sekil degismis)" % k.get("id"))
        if son == "cancelled":
            if isler:
                olcum["calisirken_iptal"] += 1
                olcum["calisirken_iptal_kosumlari"].append(k["id"])
            else:
                olcum["kuyrukta_iptal"] += 1
            continue
        adlar = {str(x.get("name")): x.get("conclusion") for x in isler}
        if adlar.get("build") == "success" and adlar.get("deploy") in (
                "skipped", "cancelled", None):
            olcum["yayinsiz_dongu"] += 1
            olcum["yayinsiz_dongu_kosumlari"].append(k["id"])
    return olcum


def canli_rapor(olcum):
    sorunlar = []
    if olcum["calisirken_iptal"]:
        sorunlar.append(
            "🔴 E4: %d kosum CALISIRKEN olduruldu (%s). Bu, `cancel-in-progress: false` "
            "altinda OLMAMASI gereken siniftir: ayar geri alinmis ya da kosumlar elle "
            "iptal ediliyor olabilir."
            % (olcum["calisirken_iptal"],
               ", ".join(str(x) for x in olcum["calisirken_iptal_kosumlari"][:6])))
    if olcum["yayinsiz_dongu"]:
        sorunlar.append(
            "🟡 E4: %d kosumda `build` YESIL ama `deploy` kosmadi (%s) — yayin o "
            "dongude inmedi."
            % (olcum["yayinsiz_dongu"],
               ", ".join(str(x) for x in olcum["yayinsiz_dongu_kosumlari"][:6])))
    return sorunlar


# ---------------------------------------------------------------------------
# KENDINI TEST — fikstur + MUTASYON BATARYASI
# ---------------------------------------------------------------------------
# 🔴 SIMULASYON FIKSTURLERI. Her satir: (ad, iptal_bayragi, kosum_dk, push_anlari,
# beklenen_calisirken_iptal, beklenen_deploy). Son iki satir KONTROL MUTANTLARIDIR:
# push araligi kosum suresinden UZUN oldugunda `true` da `false` da YESILDIR — yani
# E3'un kirmizisi bayragin DEGERINDEN degil senaryo DINAMIGINDEN dogar
# ([[fikstur-degeri-mutasyon-koru]]).
SIM_FIKSTURLERI = (
    ("iki-push-false", False, 24.8, [0.0, 3.0], 0, 2),
    ("iki-push-true", True, 24.8, [0.0, 3.0], 1, 1),
    ("firtina-8-false", False, 24.8, [3.0 * k for k in range(8)], 0, 2),
    ("firtina-8-true", True, 24.8, [3.0 * k for k in range(8)], 7, 1),
    ("tek-push-true", True, 24.8, [0.0], 0, 1),
    ("seyrek-push-true", True, 5.0, [0.0, 10.0, 20.0], 0, 3),
    ("seyrek-push-false", False, 5.0, [0.0, 10.0, 20.0], 0, 3),
)

# 🔴 MUTASYON BATARYASI — kanit YENIDEN URETILEBILIR olmali
# ([[mutasyon-kaniti-yeniden-uretilebilir]]): anlatilan degil, KOSULAN. Her mutant
# GERCEK deploy.yml govdesinin kopyasina uygulanir ve o eksenin TEK BASINA kirmizi
# yandigi olculur. M0 KONTROL MUTANTIDIR: alakasiz bir alani degistirir ve kapi YESIL
# KALMALIDIR (yoksa kapi "her seye kirmizi yanan" bir gurultu kaynagidir).
def _mutant_m0(govde):
    govde["jobs"]["deploy"]["runs-on"] = "ubuntu-22.04"


def _mutant_e1_true(govde):
    govde["concurrency"]["cancel-in-progress"] = True


def _mutant_e1_grupsuz(govde):
    govde.pop("concurrency", None)


def _mutant_e1_ifade(govde):
    govde["concurrency"]["cancel-in-progress"] = "${{ github.ref != 'refs/heads/main' }}"


def _mutant_e2_needs_kopuk(govde):
    govde["jobs"]["deploy"].pop("needs", None)


def _mutant_e2_yayin_yanlis_bag(govde):
    govde["jobs"]["yayin"]["needs"] = "build"


def _mutant_e2_kosullu(govde):
    govde["jobs"]["deploy"]["if"] = "github.event_name == 'workflow_dispatch'"


def _mutant_e2_fail_open(govde):
    govde["jobs"]["deploy"]["continue-on-error"] = True


MUTANTLAR = (
    ("M0 KONTROL: alakasiz alan (deploy.runs-on)", _mutant_m0, None),
    ("M1 E1: cancel-in-progress -> true", _mutant_e1_true, ("E1", "E3")),
    ("M2 E1: concurrency blogu SILINDI", _mutant_e1_grupsuz, ("E1",)),
    ("M3 E1: cancel-in-progress -> ifade", _mutant_e1_ifade, ("E1",)),
    ("M4 E2: deploy.needs SILINDI", _mutant_e2_needs_kopuk, ("E2",)),
    ("M5 E2: yayin.needs -> build (deploy DEGIL)", _mutant_e2_yayin_yanlis_bag, ("E2",)),
    ("M6 E2: deploy'a `if:` eklendi", _mutant_e2_kosullu, ("E2",)),
    ("M7 E2: deploy continue-on-error: true", _mutant_e2_fail_open, ("E2",)),
)


def _eksenler(sorunlar):
    """Bulgu satirlarindan EKSEN kumesi. Her eksen TEK BASINA raporlanir."""
    bulunan = set()
    for s in sorunlar:
        for eksen in ("E1", "E2", "E3"):
            if (" %s " % eksen) in s:
                bulunan.add(eksen)
    return bulunan


def kendini_test():
    """Doner: (hata_satirlari, iddia_sayisi). Iddia SAYISI kabulun olcusudur —
    cikis kodu tek basina 'batarya kostu' demez ([[mutasyon-kaniti-yeniden-uretilebilir]])."""
    hatalar = []
    iddia = 0

    # ---- BOLUM 1: simulasyon fiksturleri
    for ad, bayrak, kosum_dk, anlar, bek_iptal, bek_deploy in SIM_FIKSTURLERI:
        o = simule(bayrak, kosum_dk, anlar)
        iddia += 2
        if o["calisirken_iptal"] != bek_iptal:
            hatalar.append("SIM %s: calisirken_iptal beklenen %d, olculen %d"
                           % (ad, bek_iptal, o["calisirken_iptal"]))
        if o["deploy_kosan"] != bek_deploy:
            hatalar.append("SIM %s: deploy_kosan beklenen %d, olculen %d"
                           % (ad, bek_deploy, o["deploy_kosan"]))
    # Sinirlilik iddiasi: `false` altinda yayinsiz pencere push SAYISINDAN BAGIMSIZ
    # olarak ~2 x kosum suresiyle sinirlidir; `true` altinda push sayisiyla BUYUR.
    kucuk = simule(False, 24.8, [3.0 * k for k in range(4)])
    buyuk = simule(False, 24.8, [3.0 * k for k in range(16)])
    iddia += 1
    if buyuk["yayinsiz_pencere_dk"] > 2 * 24.8 + 1 or \
            buyuk["yayinsiz_pencere_dk"] > kucuk["yayinsiz_pencere_dk"] + 1:
        hatalar.append("SIM sinirlilik: `false` altinda yayinsiz pencere push sayisiyla "
                       "BUYUDU (4 push: %.1f dk, 16 push: %.1f dk)"
                       % (kucuk["yayinsiz_pencere_dk"], buyuk["yayinsiz_pencere_dk"]))
    t_kucuk = simule(True, 24.8, [3.0 * k for k in range(4)])
    t_buyuk = simule(True, 24.8, [3.0 * k for k in range(16)])
    iddia += 1
    if t_buyuk["yayinsiz_pencere_dk"] <= t_kucuk["yayinsiz_pencere_dk"]:
        hatalar.append("SIM aclik: `true` altinda yayinsiz pencere push sayisiyla "
                       "BUYUMEDI (%.1f -> %.1f) — simulasyon aclik sinifini URETEMIYOR"
                       % (t_kucuk["yayinsiz_pencere_dk"], t_buyuk["yayinsiz_pencere_dk"]))

    # ---- BOLUM 2: gercek dosya YESIL mi (taban)
    try:
        akislar = yayin_akislari()
    except OlcumHatasi as e:
        return hatalar + ["TABAN: yayin akisi okunamadi: %s" % e], iddia
    taban_sorun, _ = degerlendir(akislar)
    iddia += 1
    if taban_sorun:
        hatalar.append("TABAN: gercek is akisi KIRMIZI (mutasyon bataryasi anlamsizlasir):"
                       "\n    " + "\n    ".join(taban_sorun))

    # ---- BOLUM 3: mutasyon bataryasi
    hedef = None
    for dosya, govde in akislar:
        if yayin_isi_adi(govde) == "deploy":
            hedef = (dosya, govde)
            break
    if hedef is None:
        return hatalar + ["MUTASYON: `deploy` adli Pages yayin isi bulunamadi"], iddia
    dosya, govde = hedef
    for ad, uygula, beklenen in MUTANTLAR:
        kopya = copy.deepcopy(govde)
        try:
            uygula(kopya)
        except Exception as e:  # noqa: BLE001 — mutant capasi kaymis
            hatalar.append("MUTASYON %s: uygulanamadi (%s: %s) — capa kaymis, mutant "
                           "HICBIR SEY olcmedi" % (ad, type(e).__name__, e))
            continue
        m_sorun, _ = degerlendir([(dosya, kopya)])
        bulunan = _eksenler(m_sorun)
        iddia += 1
        if beklenen is None:
            if m_sorun:
                hatalar.append("MUTASYON %s: KONTROL mutanti KIRMIZI yakti (kapi alakasiz "
                               "degisikliklere de baginyor):\n    " + "\n    ".join(m_sorun))
        else:
            eksik = set(beklenen) - bulunan
            if eksik:
                hatalar.append(
                    "MUTASYON %s: %s ekseni KIRMIZI YANMADI (yanan: %s) — o eksen bu "
                    "mutanti GORMUYOR" % (ad, ", ".join(sorted(eksik)),
                                          ", ".join(sorted(bulunan)) or "hicbiri"))
    return hatalar, iddia


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayin acligi (starvation) nobetcisi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="fikstur + mutasyon bataryasi (agsiz)")
    ap.add_argument("--canli", action="store_true",
                    help="E4: gercek kosum gecmisinde iptal siniflari (gh gerekir)")
    a = ap.parse_args(argv)

    if a.kendini_test:
        try:
            hatalar, iddia = kendini_test()
        except OlcumHatasi as e:
            print("⚪ OLCULEMEDI — %s" % e)
            return 2
        if hatalar:
            print("🔴 KENDINI TEST DUSTU (%d iddia kosuldu):" % iddia)
            for h in hatalar:
                print("  " + h)
            return 1
        print("🟢 KENDINI TEST TEMIZ — %d iddia kosuldu "
              "(%d simulasyon fiksturu + %d mutant, biri KONTROL)"
              % (iddia, len(SIM_FIKSTURLERI), len(MUTANTLAR)))
        return 0

    if a.canli:
        try:
            olcum = canli_olc()
        except OlcumHatasi as e:
            print("⚪ OLCULEMEDI — %s" % e)
            return 2
        sorunlar = canli_rapor(olcum)
        print("E4 CANLI — son %d kosum · sonuclar: %s"
              % (olcum["pencere"],
                 ", ".join("%s=%d" % kv for kv in sorted(olcum["sonuclar"].items()))))
        print("   kuyrukta iptal (ZARARSIZ): %d · CALISIRKEN iptal (ACLIK): %d · "
              "build yesil ama deploy kosmadi: %d · butce disi kalan: %d"
              % (olcum["kuyrukta_iptal"], olcum["calisirken_iptal"],
                 olcum["yayinsiz_dongu"], olcum["sorgulanmayan"]))
        for s in sorunlar:
            print("  " + s)
        return 1 if any(s.startswith("🔴") for s in sorunlar) else 0

    try:
        sorunlar, olcum = degerlendir()
    except OlcumHatasi as e:
        print("⚪ OLCULEMEDI — %s" % e)
        return 2
    for dosya, d in sorted(olcum["akislar"].items()):
        e = d["eszamanlilik"]
        print("%s · yayin isi=%s · grup=%s · cancel-in-progress=%s"
              % (dosya, d["yayin_isi"], e["grup"], e["cancel_in_progress"]))
        for senaryo, s in sorted((d["simulasyon"] or {}).items()):
            print("   [%s] push=%d basladi=%d deploy=%d calisirken_iptal=%d "
                  "kuyrukta_iptal=%d yayinsiz_pencere=%.1f dk"
                  % (senaryo, s["push"], s["basladi"], s["deploy_kosan"],
                     s["calisirken_iptal"], s["kuyrukta_iptal"],
                     s["yayinsiz_pencere_dk"]))
    if sorunlar:
        print("🔴 YAYIN ACLIGI KAPISI DUSTU (%d bulgu):" % len(sorunlar))
        for s in sorunlar:
            print("  " + s)
        return 1
    print("🟢 TEMIZ — ayristirici: %s · baslamis her kosum deploy'una ulasiyor"
          % olcum["ayristirici"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
