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

ESIKLER — HEPSI 1 Agu 2026 OLCUMUNDEN (son 100 deploy kosumu, ~23 saat)
=======================================================================
Olculen taban (dagilim: 28 success · 26 failure · 44 cancelled · 2 kosan):
  * BASARILI kosum suresi: ortanca 27,9 dk · p90 36,8 dk · max 44,0 dk
  * TEPE BEKLEME YASI (bir yayin dongusunde en eski bekleyen commit'in yayin anindaki
    yasi; push GELMEYEN dongular haric, n=26): ortanca 19,3 · p75 25,6 · p90 59,5 dk.
    En yuksek IKI deger 117 dk ve 496 dk idi ve IKISI DE GERCEK OLAYDIR (117 dk = tam
    da bugunku tikanma). Yani saglikli tepe ~59 dk'da biter, olaylar 117 dk'dan baslar.
  * ZINCIR dagilimi (tamamlanmis kosumlar): IPTAL zincirleri [5,4,3,3,3,2,...] — 6 ve
    ustu HIC gorulmedi. HATA zincirleri [10,5,3,2,1,...] — 4 ve ustu yalniz IKI kez,
    ikisi de gercek tikanma.

Secilen degerler ve TEK CUMLE gerekceleri:
  GECIKME_YAS_DK   = 45  — saglikli p90 (59,5) ile ortanca (19,3) arasinda: UYARI
                           seviyesi, alarm degil (3/26 dongu asar).
  TIKALI_YAS_DK    = 75  — saglikli tepe yasinin (p90 59,5) USTUNDE, olculen olaylarin
                           (117 dk) ALTINDA: 26 dongunun yalnizca 2'si asar ve o ikisi
                           gercek olaydir.
  TIKALI_HATA_ZINCIR = 4 — olculen gurultu tavani 3 ardisik hata; gercek tikanmalar 5 ve
                           10 zincirdi.
  ACLIK_IPTAL_ZINCIR = 6 — 23 saatte olculen EN UZUN saglikli iptal zinciri 5; eszamanlilik
                           iptali NORMAL bir olaydir, alarm ancak zincir tavani asinca dogar.
  GECIKME_BIRIKME    = 12 — ~28 dk'lik build + 3-8 dk'lik push araligi saglikli halde
                           4-9 commit biriktirir; 12 onun USTUDUR.

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
    bekleme_baslangici = max(en_eski_bekleyen_commit_tarihi, son_basarili.run_started_at)
    yas_dk             = simdi - bekleme_baslangici
Taban SART: bu depoda dallar `--ff-only` ile alinir ve commit'ler ORIJINAL committer
tarihini tasir. Tabansiz olcum, saatler once bir worktree'de yazilip bugun alinan bir
commit'i "saatlerdir bekliyor" sayar -> yanlis alarm. Bir commit son BASARILI kosum
BASLAMADAN once bekliyor OLAMAZ (baslamis olsaydi o kosumun icinde yayinlanirdi), o
yuzden taban odur.

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

GECIKME_YAS_DK = 45
TIKALI_YAS_DK = 75
TIKALI_HATA_ZINCIR = 4
ACLIK_IPTAL_ZINCIR = 6
GECIKME_BIRIKME = 12

# GitHub `conclusion` degerleri: hangisi "dustu" sayilir.
HATA_SONUCLARI = ("failure", "startup_failure", "timed_out", "action_required")
# "completed" DISI her status kosumun HALA CALISTIGI/BEKLEDIGI anlamina gelir; zincir
# sayiminda ATLANIR (kanit degil) ama raporda sayilir.
TAMAMLANDI = "completed"

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


def api_getir(yol, zaman_asimi=25):
    """`gh api <yol>` -> JSON. HER ariza OlcumHatasi'dir (sessiz yesil YOK)."""
    try:
        p = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", yol],
                           capture_output=True, text=True, timeout=zaman_asimi)
    except FileNotFoundError:
        raise OlcumHatasi("`gh` bulunamadi (PATH'te yok) — GitHub Actions durumu "
                          "sorulamadi")
    except subprocess.TimeoutExpired:
        raise OlcumHatasi("`gh api` %d sn icinde yanit vermedi" % zaman_asimi)
    if p.returncode != 0:
        hata = (p.stderr or p.stdout or "").strip().splitlines()
        raise OlcumHatasi("`gh api %s` rc=%d: %s"
                          % (yol.split("?")[0], p.returncode,
                             hata[0][:160] if hata else "(cikti yok)"))
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise OlcumHatasi("`gh api` govdesi JSON degil (%d bayt)" % len(p.stdout or ""))


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


# ---------------------------------------------------------------- zincirler
def zincirler(kosumlar):
    """(ardisik_iptal, ardisik_hata, son_basarili, tamamlanan, calisan).

    Zincirler YALNIZ tamamlanmis kosumlar uzerinde, EN YENIDEN geriye sayilir ve ilk
    FARKLI sonucta DURUR. Kosan/bekleyen kosum kanit degildir -> atlanir.
    """
    tamam = [k for k in kosumlar if k.get("status") == TAMAMLANDI]
    calisan = len(kosumlar) - len(tamam)

    def zincir(kume):
        n = 0
        for k in tamam:
            if k.get("conclusion") in kume:
                n += 1
            else:
                break
        return n

    ardisik_iptal = zincir(("cancelled",))
    ardisik_hata = zincir(HATA_SONUCLARI)
    son_basarili = next((k for k in tamam if k.get("conclusion") == "success"), None)
    return ardisik_iptal, ardisik_hata, son_basarili, len(tamam), calisan


# ---------------------------------------------------------------- olcum
def olc(getir=api_getir, simdi=None, depo=None, dal=DAL):
    """Ham olcum sozlugu. HER ariza OlcumHatasi ile yukari cikar (fail-closed)."""
    simdi = simdi or _simdi()
    kosumlar = kosumlari_ayikla(getir(kosum_yolu(depo=depo, dal=dal)))
    ardisik_iptal, ardisik_hata, son_basarili, tamamlanan, calisan = zincirler(kosumlar)

    olcum = {
        "simdi": simdi,
        "pencere": len(kosumlar),
        "tamamlanan": tamamlanan,
        "calisan": calisan,
        "ardisik_iptal": ardisik_iptal,
        "ardisik_hata": ardisik_hata,
        "son_basarili_sha": None,
        "son_basarili_baslangic": None,
        "son_basarili_bitis": None,
        "geride": None,
        "yas_dk": None,
        "kirpildi": False,
        "zincir_pencere_kenarinda": (ardisik_iptal >= tamamlanan
                                     or ardisik_hata >= tamamlanan),
    }
    if son_basarili is None:
        return olcum

    olcum["son_basarili_sha"] = str(son_basarili["head_sha"])[:8]
    olcum["son_basarili_baslangic"] = _iso(son_basarili["run_started_at"], "run_started_at")
    olcum["son_basarili_bitis"] = _iso(son_basarili["updated_at"], "updated_at")

    geride, en_eski, kirpildi = karsilastirmayi_ayikla(
        getir(karsilastirma_yolu(son_basarili["head_sha"], dal=dal, depo=depo)))
    olcum["geride"] = geride
    olcum["kirpildi"] = kirpildi
    if geride > 0:
        # TABAN: bir commit son basarili kosum BASLAMADAN once bekliyor olamaz.
        baslangic = max(en_eski, olcum["son_basarili_baslangic"])
        olcum["yas_dk"] = max(0.0, (simdi - baslangic).total_seconds() / 60.0)
    else:
        olcum["yas_dk"] = 0.0
    return olcum


# ---------------------------------------------------------------- yargi
def degerlendir(olcum):
    """olcum -> (sinif, gerekce satirlari). Sira: ACLIK > TIKALI > GECIKME > AKIYOR."""
    geride = olcum["geride"]
    yas = olcum["yas_dk"]
    ai = olcum["ardisik_iptal"]
    ah = olcum["ardisik_hata"]

    if olcum["son_basarili_sha"] is None:
        # Pencerede HIC basarili yayin yok: olculdu, yargi verilebilir (OLCULEMEDI DEGIL).
        if ai >= ACLIK_IPTAL_ZINCIR:
            return "ACLIK", ["son %d tamamlanmis kosumun %d'si IPTAL, pencerede (%d kosum) "
                             "HIC basarili yayin YOK" % (olcum["tamamlanan"], ai,
                                                         olcum["pencere"])]
        return "TIKALI", ["pencerede (%d kosum) HIC basarili yayin YOK — canli, main'in "
                          "ne kadar gerisinde oldugu bile bu pencereden olculemiyor"
                          % olcum["pencere"]]

    if not geride:
        return "AKIYOR", ["canli = main (bekleyen commit YOK); kosum zincirleri "
                          "(iptal %d · hata %d) icerik bekletMIYOR" % (ai, ah)]

    neden = []
    if ai >= ACLIK_IPTAL_ZINCIR and yas >= GECIKME_YAS_DK:
        neden.append("%d ARDISIK iptal (esik %d) + en eski bekleyen commit %.0f dk "
                     "(esik %d) -> kosumlar ust uste iptal ediliyor, hicbiri tamamlanmiyor"
                     % (ai, ACLIK_IPTAL_ZINCIR, yas, GECIKME_YAS_DK))
        return "ACLIK", neden

    if ah >= TIKALI_HATA_ZINCIR:
        neden.append("%d ARDISIK dusen kosum (esik %d)" % (ah, TIKALI_HATA_ZINCIR))
    if yas >= TIKALI_YAS_DK:
        neden.append("en eski bekleyen commit %.0f dk (esik %d dk)" % (yas, TIKALI_YAS_DK))
    if neden:
        return "TIKALI", neden

    if yas >= GECIKME_YAS_DK:
        neden.append("en eski bekleyen commit %.0f dk (uyari esigi %d dk)"
                     % (yas, GECIKME_YAS_DK))
    if geride >= GECIKME_BIRIKME:
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
        s.append("son basarili yayin: pencerede YOK (%d kosum tarandi)" % olcum["pencere"])
    else:
        s.append("canli main'den %d commit geride · en eski bekleyen %s"
                 % (olcum["geride"],
                    "yok" if not olcum["geride"] else "%.0f dk" % olcum["yas_dk"]))
        s.append("son basarili deploy: %s (%s)"
                 % (olcum["son_basarili_sha"],
                    olcum["son_basarili_bitis"].strftime("%H:%M UTC")))
    s.append("ardisik iptal: %d (aclik esigi %d) · ardisik hata: %d (tikanma esigi %d)"
             % (olcum["ardisik_iptal"], ACLIK_IPTAL_ZINCIR,
                olcum["ardisik_hata"], TIKALI_HATA_ZINCIR))
    s.append("pencere: %d kosum (%d tamamlandi · %d kosuyor/bekliyor)"
             % (olcum["pencere"], olcum["tamamlanan"], olcum["calisan"]))
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
    for a in ("kosum", "karsilastirma"):
        if a not in capa:
            raise OlcumHatasi("sekil capasinda `%s` YOK" % a)
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

    def getir(yol_, zaman_asimi=25):        # noqa: ARG001 — imza api_getir ile AYNI
        if hata:
            raise OlcumHatasi(hata)
        if "/actions/workflows/" in yol_:
            return {"total_count": len(kosumlar), "workflow_runs": copy.deepcopy(kosumlar)}
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
    if SINIF_RC["OLCULEMEDI"] == 0:
        kusur.append("SOZLESME: OLCULEMEDI cikis kodu 0 (YESIL ile karisiyor)")
    if len(set(SINIF_RC.values())) != len(SINIF_RC):
        kusur.append("SOZLESME: iki sinif AYNI cikis kodunu paylasiyor")
    if not (0 < GECIKME_YAS_DK < TIKALI_YAS_DK):
        kusur.append("SOZLESME: yas esikleri sirali degil (%s/%s)"
                     % (GECIKME_YAS_DK, TIKALI_YAS_DK))
    # OLCULEMEDI'nin HER kaynagi rc 2 vermeli (ag yok / yetki yok / govde bozuk).
    for ad, patlat in (("gh yok", FileNotFoundError("gh")),
                       ("beklenmeyen tip", ValueError("bozuk"))):
        def _patlayan(yol_, zaman_asimi=25, _e=patlat):   # noqa: ARG001
            raise _e
        sinif, rc, _, _ = olc_ve_degerlendir(getir=_patlayan)
        if not (sinif == "OLCULEMEDI" and rc == 2):
            kusur.append("FAIL-CLOSED: %s -> %s/rc %d (OLCULEMEDI olmaliydi)"
                         % (ad, sinif, rc))

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
