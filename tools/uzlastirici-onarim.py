#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UZLASTIRICI ONARIM SURUCUSU — "yaris kaybettik" halini ONARIR, kod hatasini ORTMEZ.

NEDEN VAR (OLCULDU, 31 Tem 2026 — iki zamanlanmis kosumun IKISI de uzlastirma YAPMADI)
======================================================================================
`.github/workflows/d1-uzlastirici.yml` cron ofsetlendikten sonraki IKI zamanlanmis kosumu:

  · 30650256818 · 17:12:33Z · conclusion=FAILURE
      17:12:47.458Z  on-kosul : "bayatlik: UC — HEAD == uzak main ucu"  (121d0691aeee)
      17:13:16.249Z  onarim   : "bayatlik kapisi: BAYAT" (HEAD=121d0691aeee ·
                                 uzak uc=0db2aafbb580)
      -> ON-KOSUL ile YAZMA arasindaki 28,79 sn'lik pencerede main'in ucu ILERLEDI
         (0db2aafbb580 commit'i 17:12:42Z). Kapi DOGRU davrandi: 21 bayat hash'in 0'i
         yazildi. Ama is KIRMIZI kaldi ve sapma ONARILMADI.
      🔴 KOK NEDEN SINIFI = KOD/AKIS (TOCTOU yarisi), ALTYAPI DEGIL. Kanit: log'da
         wrangler hatasi, D1 7429/CPU tavani, ag hatasi ya da timeout YOK; tek sebep
         bayatlik kapisinin (dogru) reddi. Olcum adimi 19,0 sn, d1-sync yazma denemesi
         10,1 sn surdu.

  · 30664207786 · 20:47:18Z · conclusion=SUCCESS  (ama SIFIR denetim)
      20:51:07.376Z  on-kosul : "bayatlik: BAYAT" (HEAD=ca0376e7c448 · uzak uc=2d4975f4bf85)
      -> uc=hayir  ->  OLCUM · ONARIM · TEYIT adimlarinin HEPSI `skipped`  ->  kosum YESIL.
      🔴 KOK NEDEN: zamanlanmis kosum `github.sha`'yi (tetikleme anindaki main ucu)
         checkout eder. Kuyruk + kurulum gecikmesi (bu kosumda 3 dk 49 sn) boyunca main
         ilerlerse agac DOGUSTAN bayattir ve is HICBIR SEY YAPMADAN yesil doner.

ORTAK COZUM: agaci DONMUS `github.sha`'da birakmak yerine HER DENEMEDE uzak main'in
UCUNA TAZELE, sonra yaz. Yazma bayatlik kapisina takilirsa (= yaris kaybedildi) TAZELE
ve TEKRAR DENE. Yazma BASKA bir sebeple duserse (wrangler/D1/sema/kod) YENIDEN DENEME —
o hata GORUNUR kalmali.

DENEME TAVANI NEDEN 3 (OLCULDU, tahmin DEGIL)
=============================================
  · Yazma penceresi ............ 10,1 sn (17:13:06 -> 17:13:16, gercek d1-sync kosumu)
  · main'e itme sikligi ........ deploy.yml son 24 saatte 126 kosum -> ortalama 686 sn
  · Tek denemede carpisma ...... 10,1 / 686 = %1,47
  · Uc denemede hepsi carpisir . 0,0147^3 = 3,2e-6 (yaklasik 300 bin kosumda 1)
Geri cekilme 15 sn ve 45 sn: yazma penceresinin 1,5x ve 4,5x'i — ardisik bir itme
kumesinin gecmesine yeter, kosum suresini kabul edilemez sekilde uzatmaz (en kotu hal
15+45+3x10,1 = 90,3 sn).

SILME KARANTINASI (11 Agu 2026 — kosum 31532464176, 37 MESRU satir silindi)
===========================================================================
Bu surucu d1-sync'i ARTIK HER ZAMAN `--karantina-damgasi` ile cagirir: FAZLA gorulen
bir id ILK gozlemde SILINMEZ, damgaya yazilir; ancak FARKLI bir `origin/main` SHA'sinda
IKINCI kez FAZLA gorulurse silinir. Damga okunamazsa silme YAPILMAZ ve d1-sync
`KARANTINA DAMGASI OKUNAMADI` imzasiyla sifir-disi cikar -> burada rc 4. Bu sinif
YENIDEN DENENMEZ: damgayi ikinci kez okumak onu var etmez.
Gerekce + kural: tools/uzlastirici_karantina.py bas blogu.

HUKUM `rc`DEN DEGIL IMZADAN OKUNUR — UC HAL (K222Rc, 24 Agu 2026)
=================================================================
Bir alt surecin `rc`si o surecin NE YAPTIGINI degil, yalnizca COKUP COKMEDIGINI soyler.
d1-sync yazmayi atlayip duzgun bicimde 0 ile cikabilir. Bu yuzden hukum UC hâlde verilir
ve her hâl kendi IMZASINDAN okunur ([[rc-hukmu-kapi-imzasini-ezer]]):

  · ONARILDI    — d1-sync'in POZITIF onarim izi (`ONARIM_IZLERI`) ciktida VAR ve hicbir
                  kapi reddi imzasi YOK. "Onarim oldu" iddiasi burada KANITA baglanir.
  · ONARILAMADI — pozitif iz YOK ve rc != 0 (gercek hata: wrangler/D1/sema/kod).
  · OLCULEMEDI  — pozitif iz YOK **ama rc == 0**: arac SESSIZCE hicbir sey yapmadi.
                  Bu hâl `ONARILDI`ya KARISMAZ; ayri rc (6) ile fail-closed kirmizi yakar
                  ve sayisi `UC_HAL SAYIM:` satirinda BASILIR.

🔴 SIRA: iki imza kolu da (`_hukum_imzasi` = kapi reddi · `_onarim_izi` = pozitif onarim)
`rc` kolundan ONCE okunur. Sira tersse `rc == 0` imzayi EZER ve sahte yesil dogar.

CIKIS KODLARI
=============
  0 = ONARILDI (POZITIF iz VAR: D1'e yazildi + geri okuma teyit etti, ya da yazacak is yoktu)
  1 = ONARILAMADI / GERCEK HATA (wrangler/D1/sema/kod) — YENIDEN DENENMEZ, gorunur kalir
  2 = OLCULEMEDI (agac uca TAZELENEMEDI: git/ag) — fail-closed
  3 = YARIS SURDU (tavan tukendi, agac hala bayat) — fail-closed
  4 = KARANTINA OLCULEMEDI (silme damgasi okunamadi) — fail-closed, YENIDEN DENENMEZ
  5 = ERTELENDI (YAZICI_UCUSTA: baska makine canli D1 lease'i tutuyor) — YESIL DEGIL,
      "ONARILAMADI" da DEGIL: senkron denenmedi, BASARISIZ OLMADI. Dogru care RETRY'dir.
  6 = OLCULEMEDI / IZSIZ (rc=0 ama POZITIF onarim izi YOK) — arac sessizce hicbir sey
      yapmadi. YENIDEN DENENMEZ: ayni cagri ayni sessizligi uretir. Is akisi `exit "$rc"`
      ile bunu KIRMIZI yakar (ayri kol GEREKMEZ; yalnizca rc=5 yesile cevrilir).

Kullanim:
    python3 tools/uzlastirici-onarim.py                 # GERCEK onarim (CI)
    python3 tools/uzlastirici-onarim.py --kendini-test  # AGSIZ + GERCEK GIT fikstur kabulu
"""
import argparse
import os
import re
import subprocess
import sys
import time
from git_ortami import sentetik_git

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uzlastirici_karantina

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

D1_SYNC = os.path.join(TOOLS, "d1-sync.py")
UZAK = "origin"
DAL = "main"

# d1-sync.py bayatlik kapisi reddinin IMZASI (TEK KAYNAK: bayatlik_engel_metni()).
# Bu metin degisirse asagidaki `imza_capasi()` KIRMIZI yanar -> imza sessizce bayatlayamaz.
BAYATLIK_IMZASI = "!! BAYATLIK KAPISI:"
# Karantina fail-closed reddinin IMZASI — TEK KAYNAK modulun kendisi (ikiz tanim YOK).
KARANTINA_IMZASI = uzlastirici_karantina.OKUNAMADI_IMZASI
# d1-sync.py'nin CANLI LEASE (baska makinede yazici ucusta) reddinin makine-okunur
# IMZASI. Bu sinif GERCEK HATA DEGILDIR: lease surelidir, geri cekilip tekrar denemek
# TAM OLARAK calisan caredir. Kapsam kapisi (imza_kapsam_kapisi) bu sinifin d1-sync'te
# GERCEKTEN uretildigini ve BASKA bir red sinifinin sessizce dogmadigini olcer.
YAZICI_IMZASI = "D1_SENKRON=ATLANDI SEBEP=YAZICI_UCUSTA"
# Silme karantinasi damgasinin kosum-ici yolu. Is akisi ayni dosyayi indirir/yukler
# (ad TEK KAYNAK: uzlastirici_karantina.DAMGA_DOSYA).
KARANTINA_DAMGASI = os.environ.get("PRUVO_KARANTINA_DAMGASI") or os.path.join(
    ROOT, uzlastirici_karantina.DAMGA_DOSYA)

# ── POZITIF ONARIM IZLERI (K222Rc) ───────────────────────────────────────────────
# `_hukum_imzasi` NEGATIF imzalari (kapi reddi) okur. Ama "red imzasi YOK" bir onarimin
# GERCEKLESTIGINI kanitlamaz — arac hic yazmadan da sessizce 0 ile cikabilir. Bu tablo
# d1-sync'in YAZMA YOLUNUN SONUNA VARDIGINI bildiren POZITIF imzalarini tasir.
#
# Her giris: (kosum_jetonu, uretim_capasi)
#   · kosum_jetonu : d1-sync CIKTISINDA aranan metin (hukum bundan okunur)
#   · uretim_capasi: d1-sync.py GOVDESINDE tam olarak 1 kez gecmesi gereken uretim satiri.
#     Capa VARLIK degil COKLUK olcer ([[rc-hukmu-kapi-imzasini-ezer]]): ikinci (bayat) bir
#     uretim noktasi dogarsa capa KIRMIZI yakar, imza sessizce bayatlayamaz.
# Jetonlar BIRBIRINI KAPSAMAZ (ilk iki jeton `:` ve `(2. turda)` ile ayrisir) — ayni jeton
# iki girise dusseydi birini olduren mutant otekinin golgesinde YASARDI
# ([[ad-iki-rolde-mutanti-golgeler]]).
#
# Kapsam (OLCULDU 24 Agu 2026): surucu d1-sync'i `--karantina-damgasi` DISINDA bayraksiz
# cagirir; o cagri icin `_main()`'in rc=0 ile bitebildigi TUM yollar sunlardir —
#   d1-sync.py:4671 "degisiklik yok"  · :4702 bayatlik kapisi (NEGATIF imza) · fonksiyon
#   sonu (geri-okuma dogrulandi). `--seq-normalize/--sema/--durum/--kuru` kollari bu
#   cagride ERISILMEZ. Yani bu tablo o cagrinin POZITIF evrenini TAM kapsar.
ONARIM_IZLERI = (
    ("GERI-OKUMA DOGRULANDI:",
     'print("GERI-OKUMA DOGRULANDI: %d satirin yazilan alan degerleri / silinmesi D1\'de "'),
    ("GERI-OKUMA DOGRULANDI (2. turda)",
     'print("GERI-OKUMA DOGRULANDI (2. turda): 1. tur yazmasi KACMISTI, onarildi ✅")'),
    ("degisiklik yok — D1'e urun yazilmadi",
     'print("degisiklik yok — D1\'e urun yazilmadi ✅"'),
    ("geri-okuma: yazilan satir yok",
     'print("geri-okuma: yazilan satir yok — dogrulanacak sey yok")'),
)

DENEME_TAVANI = 3
GERI_CEKILME_SN = (15, 45)      # 1. ve 2. basarisiz denemeden SONRA beklenen sure
# TEK KAYNAK: "rc=0 ama POZITIF onarim izi YOK" hâlinin rc'si. Bu hâl `ONARILDI`ya
# KARISMAZ (mimar hukmu, K222Rc): sessizce hicbir sey yapmayan arac YESIL sayilamaz.
OLCULEMEDI_IZSIZ_RC = 6
# TEK KAYNAK: erteleme rc'sinin GERCEK sayisi. Is akisinin `if [ "$rc" = "5" ]` kolu
# ve tools/cron-nabiz-kapisi.py kablo capasi BU SABITI `ast` ile okur; ikiz sayi URETILMEZ
# ([[ikiz-tanim-sessiz-ayrisma]]). Bu satir silinir/yeniden adlandirilirsa kapi KIRMIZI
# yakar (cron-nabiz-kapisi.py kablo capasi).
ERTELENDI_RC = 5

# KAPSAM KAPISI — surucunun ELE ALDIGI d1-sync sinif evreni (beyan). Kapi bu beyani
# d1-sync.py'den TURETILEN evrenle karsilastirir; evrende olup burada olmayan bir
# sinif KIRMIZI yakar ([[kapi-varlik-olcer-yokluk-olcmez]]).
ELE_ALINAN_D1_RC = {0, 1, 4}          # 0 basari · 1 sys.exit(<mesaj>)=GERCEK HATA · 4 canli lease
ELE_ALINAN_SEBEP = {"YAZICI_UCUSTA"}  # d1-sync'in `SEBEP=<JETON>` makine jetonlari
TURETILMIS_RC_IZNI = {"_adim_kos"}    # main() icinde sabit olmayan return'lerin izinli kaynagi


def _kos(argv, cwd, zaman_asimi=900):
    """(rc, birlesik_cikti). Calistirilamazsa rc None."""
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=zaman_asimi)
    except Exception as e:                                        # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def uca_tazele(kok=ROOT, kos=_kos):
    """Agaci uzak main'in UCUNA getir. Doner: (ok, sha|sebep).

    Zamanlanmis kosumun DONMUS `github.sha` checkout'u burada duzeltilir: fetch + hard
    reset. Sig (depth 1) checkout'ta da calisir — bayatlik_olc() once `HEAD == uzak uc`
    esitligine bakar, tarih GEREKMEZ."""
    rc, cikti = kos(["git", "fetch", "--depth=1", UZAK, DAL], kok, 300)
    if rc != 0:
        return False, "git fetch %s %s basarisiz (rc=%s): %s" % (UZAK, DAL, rc,
                                                                 cikti.strip()[:300])
    rc, cikti = kos(["git", "reset", "--hard", "FETCH_HEAD"], kok, 300)
    if rc != 0:
        return False, "git reset --hard FETCH_HEAD basarisiz (rc=%s): %s" % (
            rc, cikti.strip()[:300])
    rc, sha = kos(["git", "rev-parse", "HEAD"], kok, 60)
    if rc != 0 or not sha.strip():
        return False, "HEAD okunamadi (rc=%s)" % rc
    return True, sha.strip()


def _hukum_imzasi(cikti):
    """Hangi KAPI kolu yazmayi blokladi? `rc`ye BAKMAZ. None = hicbir kapi imzasi yok.

    🔴 K222 (19 Agu 2026): hukum eskiden `rc`den okunuyordu (`if rc == 0` bayatlik
    kolundan ONCE geliyordu). Bir kapi yazmayi BLOKLAYIP surec 0 ile cikarsa surucu
    "✅ ONARILDI" basiyor, D1'e TEK SATIR yazilmamisken kosum YESIL doniyordu — sahte
    yesil, sahte kirmizidan BETERDIR. Hukum artik TEK KAYNAKTAN, kapinin kendi
    imzasindan turer; `rc` yalniz imzasiz kalan halde (gercek basari / gercek hata)
    ayirt edici olur."""
    if KARANTINA_IMZASI in cikti:
        return "KARANTINA"
    if YAZICI_IMZASI in cikti:
        return "YAZICI"
    if BAYATLIK_IMZASI in cikti:
        return "BAYATLIK"
    return None


def _onarim_izi(cikti):
    """POZITIF onarim izi: d1-sync YAZMA YOLUNUN SONUNA VARDI mi? `rc`ye BAKMAZ.
    Doner: bulunan kosum_jetonu (str) ya da None.

    🔴 K222Rc (24 Agu 2026): `_hukum_imzasi(cikti) is None` yalnizca "TANIDIGIM bir kapi
    reddetmedi" demektir — onarimin GERCEKLESTIGINI SOYLEMEZ. Arac hic yazmadan da
    (yeni bir erken `return`, kirpilmis cikti, tanimadigimiz bir atlama kolu) 0 ile
    cikabilir; eski surucu o hâlde "✅ ONARILDI" basiyordu. Hukum artik POZITIF izden
    okunur: iz YOKSA onarim OLMAMIS sayilir (fail-closed)."""
    for jeton, _capa in ONARIM_IZLERI:
        if jeton in cikti:
            return jeton
    return None


def onar(kok=ROOT, kos=_kos, bekle=time.sleep, yaz=print):
    """Tazele -> d1-sync -> (yaris/yazici ise) tekrar. Doner: (rc, deneme_sayisi).

    Her cikistan ONCE `UC_HAL SAYIM:` satiri basilir (kucuk harf ANAHTARLARLA: hukum
    METINLERIYLE karismasin — `V9c` ERTELENDI ciktisinda buyuk harfli 'ONARILAMADI'
    aramaya devam eder).

    🔴 `return <rc>, deneme` bicimi BILEREK KORUNDU: komsu batarya
    (`uzlastirici-karantina-test.py` KABLO vakasi) ve mutasyon capalari bu metne
    NISANLI. Sayim satiri sarmalayici DEGIL, ayri bir `_sayim_bas()` cagrisidir
    ([[kapinin-menzili-cagri-yeridir]] komsu-capa yuzu)."""
    son_sinif = None                      # tavan tukendiginde hangi hukum verilecek
    sayim = {"onarildi": 0, "onarilamadi": 0, "olculemedi": 0}

    def _sayim_bas():
        yaz("UC_HAL SAYIM: onarildi=%d onarilamadi=%d olculemedi=%d"
            % (sayim["onarildi"], sayim["onarilamadi"], sayim["olculemedi"]))

    for deneme in range(1, DENEME_TAVANI + 1):
        ok, bilgi = uca_tazele(kok, kos)
        if not ok:
            yaz("🔴 OLCULEMEDI: agac uzak %s/%s UCUNA tazelenemedi -> %s" % (UZAK, DAL, bilgi))
            yaz("   FAIL-CLOSED: tazelenemeyen agactan yazmak, uzlastiricinin ONLEMEK "
                "icin var oldugu kacagin ta kendisi olurdu.")
            sayim["olculemedi"] += 1
            _sayim_bas()
            return 2, deneme
        yaz("deneme %d/%d — agac uzak %s/%s ucunda: %s"
            % (deneme, DENEME_TAVANI, UZAK, DAL, bilgi[:12]))

        rc, cikti = kos(["python3", D1_SYNC, "--karantina-damgasi", KARANTINA_DAMGASI],
                        kok)
        yaz(cikti.rstrip())
        # 🔴 K222/K222Rc: SIRA BILEREK BOYLE — HER IKI imza kolu da `rc` kolundan ONCE
        # okunur. `ONARILDI` yalnizca "hicbir kapi reddi imzasi YOK **ve** POZITIF onarim
        # izi VAR" halinde yazilir; rc TEK BASINA hicbir hukum vermez.
        imza = _hukum_imzasi(cikti)
        iz = _onarim_izi(cikti)
        if imza is None and iz is not None:
            sayim["onarildi"] += 1
            yaz("✅ ONARILDI (deneme %d/%d) — POZITIF iz: %s"
                % (deneme, DENEME_TAVANI, iz))
            _sayim_bas()
            return 0, deneme
        if imza is None and rc == 0:
            # UCUNCU HAL: tanidigimiz hicbir kapi reddetmedi, arac 0 ile cikti, ama
            # yazma yolunun sonuna VARDIGINI gosteren POZITIF iz de YOK -> arac SESSIZCE
            # hicbir sey yapmis olabilir. Bu hâl `ONARILDI`ya KARISMAZ (fail-closed).
            sayim["olculemedi"] += 1
            yaz("🟣 OLCULEMEDI (deneme %d/%d): d1-sync rc=0 ile cikti ama POZITIF ONARIM "
                "IZI YOK — 'onarildi' iddiasi KANITSIZ. Beklenen izlerden HICBIRI ciktida "
                "gecmiyor: %s" % (deneme, DENEME_TAVANI,
                                  " | ".join(j for j, _c in ONARIM_IZLERI)))
            yaz("   YENIDEN DENENMEZ: ayni cagri ayni sessizligi uretir. Once d1-sync'in "
                "hangi koldan sessizce dondugu OLCULMELI (yeni erken `return` / kirpilmis "
                "cikti / tanimadigimiz atlama kolu).")
            _sayim_bas()
            return OLCULEMEDI_IZSIZ_RC, deneme
        if imza == "KARANTINA":
            yaz("🔴 KARANTINA OLCULEMEDI (rc=%s) — silme damgasi okunamadi. Upsert kolu "
                "uygulandi, SILME kolu fail-closed KAPALI kaldi. YENIDEN DENENMEZ: "
                "damgayi ikinci kez okumak onu VAR ETMEZ." % rc)
            sayim["olculemedi"] += 1
            _sayim_bas()
            return 4, deneme
        if imza == "YAZICI":
            son_sinif = "YAZICI"
            if deneme < DENEME_TAVANI:
                gecikme = GERI_CEKILME_SN[deneme - 1]
                yaz("⚠️  YAZICI UCUSTA: baska makine canli D1 lease'i tutuyor; senkron "
                    "TASARIM GEREGI atlandi (GERCEK HATA DEGIL). %d sn geri cekilip "
                    "TEKRAR deniyorum." % gecikme)
                bekle(gecikme)
            continue
        if imza == "BAYATLIK":
            son_sinif = "BAYATLIK"
            if deneme < DENEME_TAVANI:
                gecikme = GERI_CEKILME_SN[deneme - 1]
                yaz("⚠️  YARIS: yazma sirasinda main'in ucu ILERLEDI (bayatlik kapisi kapandi). "
                    "%d sn geri cekilip agaci yeni uca tazeleyerek TEKRAR deniyorum." % gecikme)
                bekle(gecikme)
            continue
        sayim["onarilamadi"] += 1
        yaz("🔴 ONARILAMADI — GERCEK HATA (rc=%s) — bayatlik kapisi DEGIL. YENIDEN "
            "DENENMEZ: bu sinif (wrangler/D1/sema/kod) yeniden denemeyle gecmez ve "
            "GORUNUR kalmalidir." % rc)
        _sayim_bas()
        return 1, deneme
    if son_sinif == "YAZICI":
        yaz("D1_SENKRON=ERTELENDI SEBEP=YAZICI_UCUSTA")
        yaz("🟠 ERTELENDI: %d denemenin hepsinde baska makine canli D1 lease'i tutuyordu. "
            "Senkron denenmedi, BASARISIZ OLMADI (lease geri cekildiginde tekrar denenebilir); "
            "YESIL de DEGILDIR: sapma hala acik olabilir." % DENEME_TAVANI)
        _sayim_bas()
        return ERTELENDI_RC, DENEME_TAVANI
    yaz("🔴 YARIS SURDU: %d denemenin hepsinde main'in ucu yazma penceresinde ilerledi. "
        "Olculen tek-deneme carpisma olasiligi %%1,47 idi; %d ardisik carpisma bu "
        "olcumun BAYATLADIGINA isarettir (itme sikligi artmis olabilir)."
        % (DENEME_TAVANI, DENEME_TAVANI))
    _sayim_bas()
    return 3, DENEME_TAVANI


# ---- KABUL TESTI ------------------------------------------------------------
def imza_capasi():
    """BAYATLIK_IMZASI d1-sync.py GOVDESINDE kac kez uretiliyor? (int doner)

    Imza sessizce degisirse bu surucu her yaris reddini 'GERCEK HATA' sayar ve yeniden
    deneme OLU kalir (sessiz zayiflama). Bu capa o hali KIRMIZI yakar.

    🔴 K222 eki (19 Agu 2026): capa artik `in` DEGIL **count**. Sebep: K222'den sonra
    hukum dogrudan bu imzadan okunuyor ([[_hukum_imzasi]]); capa varlik olcup coklugu
    olcmezse iki ayri uretim noktasi (biri bayat) SESSIZCE gecerdi
    ([[capa-cokmesi-arkasindaki-capalari-gizler]]). Kabul: **tam olarak 1**."""
    with open(D1_SYNC, encoding="utf-8") as f:
        return f.read().count(BAYATLIK_IMZASI)


def onarim_izi_capasi(d1_sync_yolu=D1_SYNC):
    """POZITIF onarim izlerinin d1-sync.py GOVDESINDEKI uretim capalari saglam mi?

    Doner: [(kosum_jetonu, capa_adedi)] — her adet TAM 1 olmali.

    NEDEN COKLUK (VARLIK DEGIL): hukum artik dogrudan bu izlerden okunuyor. Capa yalnizca
    varligi olcseydi, ayni metni basan IKINCI (bayat) bir uretim noktasi dogdugunda biri
    sessizce gecerdi ([[rc-hukmu-kapi-imzasini-ezer]] · [[capa-cokmesi-arkasindaki-capalari-gizler]]).
    Adet 0'a duserse (d1-sync o satiri degistirdi) surucu her basarili kosumu OLCULEMEDI
    sayar — sessiz zayiflama DEGIL, GURULTULU kirmizi."""
    with open(d1_sync_yolu, encoding="utf-8") as f:
        govde = f.read()
    return [(jeton, govde.count(capa)) for jeton, capa in ONARIM_IZLERI]


def imza_kapsam_kapisi(d1_sync_yolu=D1_SYNC):
    """Iki eksenli kapsam kapisi — d1-sync.py kaynagindan TURETILMIS evrenle
    surucunun ELE_ALINAN beyani karsilastirilir. (sorunlar, evren) doner; sorunlar
    bossa YESIL.

    A ekseni — cikis kodu evreni (ast ile): main() icindeki her ast.Return incelenir.
      * ast.Constant int -> evrene eklenir (dogrudan rc)
      * ast.Call -> cagrilan ad TURETILMIS_RC_IZNI icinde olmali ([[beyan-edilmis]])
      * baska -> SORUN (fail-closed)
      * evrene `1` daima eklenir (sys.exit(<mesaj>) yolunun dolayli rc'si)
      * ELE_ALINAN_D1_RC - evren_rc bos degilse SORUN (surekli uretilmeyen sinifi
        beyan ediyor -> imza sessizce degismis olabilir)
      * evren_rc - ELE_ALINAN_D1_RC bos degilse SORUN (uretilen reddi ele almiyor ->
        tanimayan her red GERCEK HATA'ya duser)

    B ekseni — SEBEP= jeton evreni (re ile): uretilen jetonlar kumesinin beyanla
    AYNI OLMASI gerekir; ne fazla ne eksik ([[kapi-varlik-olcer-yokluk-olcmez]]).

    Dosya okunamazsa/ast cozemezse SORUN — OLCULEMEDI yeşil degildir.
    """
    import ast as _ast

    sorunlar = []
    evren = {"rc": set(), "sebep": set()}
    try:
        with open(d1_sync_yolu, encoding="utf-8") as f:
            kaynak = f.read()
    except Exception as e:                                            # noqa: BLE001
        return (["d1-sync.py okunamadi (%s): %s" % (type(e).__name__, e)], evren)

    # --- A ekseni: ast ile main() rc evreni ---
    try:
        agac = _ast.parse(kaynak)
    except SyntaxError as e:
        return (["d1-sync.py AST cozumu basarisiz (SyntaxError): %s" % e], evren)
    main_func = None
    for dugum in _ast.walk(agac):
        if isinstance(dugum, _ast.FunctionDef) and dugum.name == "main":
            main_func = dugum
            break
    if main_func is None:
        sorunlar.append("d1-sync.py icinde modül düzeyinde `def main()` bulunamadi")
    evren_rc = {1}                                  # sys.exit(<mesaj>) yolu her zaman var
    if main_func is not None:
        for dugum in _ast.walk(main_func):
            if not isinstance(dugum, _ast.Return):
                continue
            deger = dugum.value
            if isinstance(deger, _ast.Constant) and isinstance(deger.value, int):
                evren_rc.add(deger.value)
            elif isinstance(deger, _ast.Call):
                # ast.Call: dugum.value.func -> Name/Attribute
                func = deger.func
                ad = getattr(func, "id", None) or getattr(func, "attr", None)
                if ad not in TURETILMIS_RC_IZNI:
                    sorunlar.append(
                        "d1-sync main() icinde return %s(...) var ama TURETILMIS_RC_IZNI "
                        "listesinde YOK -> surekli uretilmeyen rc'yi ele aliyor "
                        "olabilirsin" % ad)
            else:
                sorunlar.append(
                    "d1-sync main() icinde taninmayan return sekli (%s) — fail-closed"
                    % type(deger).__name__)
    evren["rc"] = evren_rc
    eksik = evren_rc - ELE_ALINAN_D1_RC
    fazla = ELE_ALINAN_D1_RC - evren_rc
    if eksik:
        sorunlar.append(
            "d1-sync main() rc=%s uretebiliyor ama surucude ele alinan kol YOK -> "
            "tanimayan her red GERCEK HATA'ya duser" % sorted(eksik))
    if fazla:
        sorunlar.append(
            "surucu ELE_ALINAN_D1_RC icinde rc=%s beyan ediyor ama d1-sync bunu "
            "URETMIYOR -> surekli uretilmeyen sinifi bekliyorsun (imza bayat)"
            % sorted(fazla))

    # --- B ekseni: SEBEP= jeton evreni (re ile) ---
    try:
        evren_sebep = set(re.findall(r"SEBEP=([A-Z0-9_]+)", kaynak))
    except re.error as e:
        return (sorunlar + ["SEBEP= re cozumu basarisiz: %s" % e], evren)
    evren["sebep"] = evren_sebep
    eksik_sebep = evren_sebep - ELE_ALINAN_SEBEP
    fazla_sebep = ELE_ALINAN_SEBEP - evren_sebep
    if eksik_sebep:
        sorunlar.append("d1-sync `SEBEP=%s` jetonunu uretiyor ama surucu bu sinifi "
                        "TANIMIYOR" % sorted(eksik_sebep))
    if fazla_sebep:
        sorunlar.append("surucu ELE_ALINAN_SEBEP icinde `%s` beyan ediyor ama d1-sync "
                        "bunu URETMIYOR -> imza sessizce degismis olabilir"
                        % sorted(fazla_sebep))

    return (sorunlar, evren)


def karantina_capasi():
    """Silme karantinasi KABLOLU mu — (bayrak_tanimli, imza_uretiliyor).

    IKI YONLU: (a) d1-sync.py `--karantina-damgasi` bayragini TANIYOR mu (tanimazsa bu
    surucunun gecirdigi bayrak argparse hatasina duser), (b) fail-closed imzayi TEK
    KAYNAKTAN (uzlastirici_karantina.OKUNAMADI_IMZASI) uretiyor mu. Ikisinden biri
    dusarse karantina SESSIZCE devre disi kalirdi ([[ikiz-tanim-sessiz-ayrisma]])."""
    with open(D1_SYNC, encoding="utf-8") as f:
        govde = f.read()
    return ("--karantina-damgasi" in govde,
            "uzlastirici_karantina.OKUNAMADI_IMZASI" in govde)


def _sahte_kos(sirali, kayit):
    """Enjekte edilebilir kosucu. `sirali`: [(rc, cikti), ...] — d1-sync cagrilari icin.

    git cagrilari varsayilan olarak BASARILI; `sirali` icinde ("GIT-HATA", metin) girisi
    varsa bir sonraki git cagrisi duser."""
    durum = {"git_hata": None}

    def kos(argv, cwd, zaman_asimi=900):                          # noqa: ARG001
        kayit.append(argv)
        if argv and argv[0] == "git":
            if durum["git_hata"] is not None:
                return 128, durum["git_hata"]
            if argv[1] == "rev-parse":
                return 0, "0db2aafbb580e1c4a7f9d3b2c1e0f5a6b7c8d9e0\n"
            return 0, ""
        # d1-sync cagrisi
        if not sirali:
            raise AssertionError("beklenenden FAZLA d1-sync cagrisi")
        rc, cikti = sirali.pop(0)
        if rc == "GIT-HATA":
            durum["git_hata"] = cikti
            return 0, ""
        return rc, cikti
    return kos


# GERCEK 17:12Z kosumunun d1-sync ciktisindan KOPYALANMIS govde (kisaltilmis sahte sekil
# DEGIL) -> [[nobetci-fikstur-sekli]]. Kisisel veri YOK.
_GERCEK_BAYAT_CIKTI = """\
urunler.json: 15955 urun | D1: 15955 urun | gizli baski kaydi: 0 | baski yetki: HAYIR \
(baski atlanir) | taban fiyat semasi: 23 | konfigur semasi: 17
yeni: 0 | degisen: 21 | baski-guncelle: 0 | taban-guncelle: 0 | konfigur-guncelle: 0 | \
silinen: 0 | dokunulmayan: 15934
bayatlik kapisi: BAYAT — uzak main ucu bu agacta YOK (yayinda bizde olmayan commit var) \
(HEAD=121d0691aeee · uzak uc=0db2aafbb580)
!! BAYATLIK KAPISI: BU AGACTAN D1'e HICBIR SEY YAZILMADI (durum: BAYAT).
   Sebep: uzak main ucu bu agacta YOK (yayinda bizde olmayan commit var)
   HEAD=121d0691aeee · uzak refs/heads/main ucu=0db2aafbb580
   Engellenen is (toplam 21): yeni 0 | degisen 21 | silinen 0 | baski 0 | taban 0 | konfigur 0
   NEDEN: bu agac yayindaki ucu bilmiyor. Yazma UYGULANSAYDI baska bir push'un
   D1'e yeni yazdigi urunler SILINIR ya da alanlari ESKI degerlere GERI ALINIRDI
   (site dogru gosterir, Ege bayat gorur = sessiz satis kaybi).
   Coz: agaci uca getir (git pull --ff-only / taze checkout) ve tekrar kos.
"""
# 🔴 K222Rc DUZELTMESI (24 Agu 2026): bu fikstürün son satiri eskiden
# `D1 yazildi: 21 upsert | 0 silme | geri okuma teyidi TAMAM` idi — d1-sync.py'nin
# HICBIR YERINDE URETILMEYEN, elle uydurulmus bir sekil ([[nobetci-fikstur-sekli]] ihlali).
# Gercek basari satiri `geri_okuma_dogrula()`'nin bastigi satirdir (d1-sync.py:2393) ve
# TEK KAYNAK olarak `ONARIM_IZLERI[0]` capasindan dogrulanir. Fikstur uydurma kaldigi
# surece POZITIF iz kolu hicbir sey olcemezdi.
_GERCEK_BASARI_CIKTI = """\
urunler.json: 15955 urun | D1: 15955 urun | gizli baski kaydi: 0 | baski yetki: HAYIR \
(baski atlanir) | taban fiyat semasi: 23 | konfigur semasi: 17
yeni: 0 | degisen: 21 | baski-guncelle: 0 | taban-guncelle: 0 | konfigur-guncelle: 0 | \
silinen: 0 | dokunulmayan: 15934
  parca 1/1 — yazilan satir: 21
TOPLAM yazilan satir (wrangler IDDIASI, asagida DOGRULANIR): 22
geri-okuma [hedefli]: 21 id | 1 sorgu | okunan satir: 21 | 2.87 s
GERI-OKUMA DOGRULANDI: 21 satirin yazilan alan degerleri / silinmesi D1'de teyit edildi ✅
"""
# "YAZACAK IS YOKTU" hâli — d1-sync.py:4669'un bastigi sekil. rc=0 + POZITIF iz VAR:
# ONARILDI mesrudur (onarim GEREKMEDI). OLCULEMEDI ile KARISTIRILMAMALIDIR.
_GERCEK_ISYOK_CIKTI = """\
urunler.json: 26906 urun | D1: 26906 urun | gizli baski kaydi: 0 | baski yetki: HAYIR \
(baski atlanir) | taban fiyat semasi: 23 | konfigur semasi: 17
yeni: 0 | degisen: 0 | baski-guncelle: 0 | taban-guncelle: 0 | konfigur-guncelle: 0 | \
silinen: 0 | dokunulmayan: 26906
degisiklik yok — D1'e urun yazilmadi ✅
"""
# 🔴 UCUNCU HAL FIKSTURU (K222Rc): arac SESSIZCE hicbir sey yapmadi. Govde gercek
# kosumun ILK IKI satiridir (yukaridaki basari ciktisiyla BIREBIR ayni kaynaktan);
# terminal satir — ne kapi reddi, ne pozitif iz — YOKTUR. Bu, d1-sync'in tanimadigimiz
# bir koldan erken donmesi / ciktinin kirpilmasi halinin sekli.
_GERCEK_IZSIZ_CIKTI = """\
urunler.json: 15955 urun | D1: 15955 urun | gizli baski kaydi: 0 | baski yetki: HAYIR \
(baski atlanir) | taban fiyat semasi: 23 | konfigur semasi: 17
yeni: 0 | degisen: 21 | baski-guncelle: 0 | taban-guncelle: 0 | konfigur-guncelle: 0 | \
silinen: 0 | dokunulmayan: 15934
"""
_GERCEK_HATA_CIKTI = """\
urunler.json: 15955 urun | D1: 15955 urun
wrangler SIFIR-DISI cikti (rc=1) — cikti BASARI sayilmaz:
{"error": {"code": 7429, "message": "D1 CPU limit exceeded"}}
"""
# CANLI LEASE (yazici ucusta) kosumunun d1-sync ciktisindan KOPYALANMIS govde
# ([[nobetci-fikstur-sekli]]). Kisisel veri YOK; ornek: kosum 32026332006.
_GERCEK_YAZICI_CIKTI = """\
D1 yazici kilidi ALINDI (PID=2738, ortak-kilit=/home/runner/work/pruvo/pruvo/.git/config)
D1 YAZICI UCUSTA (baska makine) — bu kosumda senkron ATLANDI; ucta kosan is + pre-push hook + d1-uzlastirici.yml katalogu senkron tutar.
D1_SENKRON=ATLANDI SEBEP=YAZICI_UCUSTA
"""
# KARANTINA FAIL-CLOSED govdesi — d1-sync'in `--karantina-damgasi` kolunun damga
# okunamadiginda bastigi sekil (imza TEK KAYNAKTAN gelir, elle kopyalanmaz).
_GERCEK_KARANTINA_CIKTI = """\
urunler.json: 25864 urun | D1: 25864 urun | gizli baski kaydi: 0 | baski yetki: HAYIR \
(baski atlanir) | taban fiyat semasi: 23 | konfigur semasi: 17
yeni: 0 | degisen: 0 | silinen: 37 | dokunulmayan: 25827
bayatlik kapisi: UC — HEAD == uzak main ucu (HEAD=c8b0451e1234 · uzak uc=c8b0451e1234)
""" + uzlastirici_karantina.OKUNAMADI_IMZASI + """ damga dosyasi YOK
KARANTINA_HUKUM=OLCULEMEDI
KARANTINA_ACILDI=37
KARANTINA_SILINDI=0
GERI-OKUMA DOGRULANDI: 0 satirin ... teyit edildi ✅
""" + uzlastirici_karantina.OKUNAMADI_IMZASI + """ hukum bu kosumda verilemedi.
"""


def _gercek_git_fiksturu():
    """GERCEK git ile: uzak (bare) + geride kalmis agac -> uca_tazele() -> agac UCTA mi.

    Bu, 20:47Z kosumunun (dogustan bayat checkout -> her sey skipped -> sahte YESIL)
    ONARIMININ dogrudan kanitidir. STUB YOK: gercek git komutlari kosar."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="pruvo-uzl-onarim-")
    try:
        uzak = os.path.join(tmp, "uzak.git")
        sentetik_git(tmp, "init", "--bare", "-b", DAL, uzak,
                      capture_output=True, check=True)
        tohum = os.path.join(tmp, "tohum")
        sentetik_git(tmp, "clone", uzak, tohum, capture_output=True, check=True,
                      kimlik_ad="pruvo", kimlik_eposta="pruvo@example.invalid")
        with open(os.path.join(tohum, "urunler.json"), "w", encoding="utf-8") as f:
            f.write("[]\n")
        sentetik_git(tohum, "add", "-A", capture_output=True, check=True)
        sentetik_git(tohum, "commit", "-m", "ilk", capture_output=True, check=True,
                      kimlik_ad="pruvo", kimlik_eposta="pruvo@example.invalid")
        sentetik_git(tohum, "push", UZAK, DAL, capture_output=True, check=True)
        eski = sentetik_git(tohum, "rev-parse", "HEAD", capture_output=True,
                             text=True).stdout.strip()

        # CI'nin donmus `github.sha` checkout'u = eski ucta duran agac
        agac = os.path.join(tmp, "ci")
        sentetik_git(tmp, "clone", uzak, agac, capture_output=True, check=True)

        # main ILERLER (baska bir push)
        with open(os.path.join(tohum, "urunler.json"), "w", encoding="utf-8") as f:
            f.write('[{"id":"yeni"}]\n')
        sentetik_git(tohum, "commit", "-am", "yeni parti", capture_output=True,
                      check=True, kimlik_ad="pruvo",
                      kimlik_eposta="pruvo@example.invalid")
        sentetik_git(tohum, "push", UZAK, DAL, capture_output=True, check=True)
        yeni = sentetik_git(tohum, "rev-parse", "HEAD", capture_output=True,
                             text=True).stdout.strip()

        once = sentetik_git(agac, "rev-parse", "HEAD", capture_output=True,
                             text=True).stdout.strip()
        ok, bilgi = uca_tazele(agac)
        sonra = sentetik_git(agac, "rev-parse", "HEAD", capture_output=True,
                              text=True).stdout.strip()
        return {"eski": eski, "yeni": yeni, "once": once, "sonra": sonra,
                "ok": ok, "bilgi": bilgi}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def kendini_test():
    hatalar = []
    sayac = [0]

    def iddia(ad, kosul, detay=""):
        if not isinstance(detay, str):
            detay = repr(detay)
        sayac[0] += 1
        print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", ad,
                               ("  -> " + detay) if detay else ""))
        if not kosul:
            hatalar.append(ad)

    def kos_senaryo(sirali):
        kayit, uyku = [], []
        rc, deneme = onar(kok="/yok", kos=_sahte_kos(list(sirali), kayit),
                          bekle=uyku.append, yaz=lambda *a: None)
        d1 = [a for a in kayit if a and a[0] != "git"]
        return rc, deneme, len(d1), uyku, kayit

    def kos_senaryo_yazili(sirali):
        """kos_senaryo gibi, ama surucunun YAZDIGI metni de dondurur (K222 vakalari
        hukmun METNINI olcer: rc dogru olsa bile 'ONARILDI' basilmis olabilir)."""
        kayit, uyku, yazilan = [], [], []
        rc, deneme = onar(kok="/yok", kos=_sahte_kos(list(sirali), kayit),
                          bekle=uyku.append,
                          yaz=lambda *a: yazilan.append(" ".join(str(x) for x in a)))
        d1 = [a for a in kayit if a and a[0] != "git"]
        return rc, deneme, len(d1), uyku, "\n".join(yazilan)

    # --- IMZA CAPASI ---
    _imza_adet = imza_capasi()
    iddia("IMZA CAPASI: bayatlik reddinin imzasi d1-sync.py'de GERCEKTEN ve TEK KEZ "
          "uretiliyor (imza bayatlarsa yeniden deneme OLU kalirdi; iki uretim noktasi "
          "olursa biri bayatlayip SESSIZCE gecerdi)", _imza_adet == 1,
          "aranan %r adet=%d (kabul: 1)" % (BAYATLIK_IMZASI, _imza_adet))

    # --- KARANTINA KABLO CAPASI ---
    _bayrak, _imza = karantina_capasi()
    iddia("KARANTINA CAPASI (a): d1-sync.py `--karantina-damgasi` bayragini TANIYOR "
          "(tanimazsa surucunun her cagrisi argparse hatasina duserdi)", _bayrak)
    iddia("KARANTINA CAPASI (b): d1-sync.py fail-closed imzayi TEK KAYNAKTAN "
          "(uzlastirici_karantina.OKUNAMADI_IMZASI) uretiyor", _imza)

    # --- YESIL YOL ---
    rc, deneme, d1, uyku, kayit = kos_senaryo([(0, _GERCEK_BASARI_CIKTI)])
    iddia("V1 ilk denemede BASARI -> rc 0 · 1 deneme · 0 bekleme",
          (rc, deneme, d1, uyku) == (0, 1, 1, []), (rc, deneme, d1, uyku))
    iddia("V1 d1-sync HER cagride `--karantina-damgasi` ile cagrilir (bayrak dusurse "
          "silme karantinasi SESSIZCE devre disi kalirdi)",
          any(a[0] != "git" and "--karantina-damgasi" in a for a in kayit), kayit)
    iddia("V1 yazmadan ONCE agac UCA tazelenir (fetch + reset --hard)",
          ["git", "fetch", "--depth=1", UZAK, DAL] in kayit
          and ["git", "reset", "--hard", "FETCH_HEAD"] in kayit, kayit)

    # --- ANA KANIT: 17:12Z KOSUMUNUN AYNI DIZISI ---
    rc, deneme, d1, uyku, kayit = kos_senaryo([(1, _GERCEK_BAYAT_CIKTI),
                                               (0, _GERCEK_BASARI_CIKTI)])
    iddia("V2 (GERCEK 17:12Z DIZISI) yaris kaybedildi -> tazele + TEKRAR -> rc 0",
          (rc, deneme, d1) == (0, 2, 2), (rc, deneme, d1))
    iddia("V2 geri cekilme OLCULEN degerle uygulanir (15 sn)", uyku == [15], uyku)
    iddia("V2 HER denemede agac YENIDEN tazelenir (2 fetch)",
          len([a for a in kayit if a[:2] == ["git", "fetch"]]) == 2, kayit)

    # --- KIRMIZI YOL: GERCEK HATA YENIDEN DENENMEZ ---
    # FIKSTUR SERTLESTIRILDI (dilim-1b): M4 mutantı 1 girişlik fikstürde sirali tukenmesine
    # yol açıyor, kendini_test() istasyona dusuyordu. 3 giriş: dogru kod 1. denemede rc=1
    # ile cikar (2 giriş kullanilmaz); M4 mutantı 3 denemeyi tuketir, rc=3 (YARIS SURDU)
    # doner -> iddia (1, 1, 1, []) YAKALAR (mod=IDDIA).
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_HATA_CIKTI)] * DENEME_TAVANI)
    iddia("V3 GERCEK hata (D1 7429 CPU tavani) -> rc 1 · TEK deneme · 0 bekleme "
          "(kod/altyapi hatasi yeniden denemeyle ORTULMEZ; M4 fikstur tukenmesi "
          "IDDIA'ya cevrildi)",
          (rc, deneme, d1, uyku) == (1, 1, 1, []), (rc, deneme, d1, uyku))

    # --- FAIL-CLOSED: KARANTINA DAMGASI OKUNAMADI ---
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_KARANTINA_CIKTI)])
    iddia("V3b KARANTINA damgasi okunamadi -> rc 4 · TEK deneme · 0 bekleme "
          "(damgayi ikinci kez okumak onu VAR ETMEZ; silme fail-closed KAPALI kaldi)",
          (rc, deneme, d1, uyku) == (4, 1, 1, []), (rc, deneme, d1, uyku))

    # --- FAIL-CLOSED: TAVAN TUKENDI ---
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_BAYAT_CIKTI)] * DENEME_TAVANI)
    iddia("V4 yaris TAVAN boyunca surdu -> rc 3 (YESIL DEGIL) · %d deneme · geri "
          "cekilme %s" % (DENEME_TAVANI, list(GERI_CEKILME_SN)),
          (rc, deneme, d1) == (3, DENEME_TAVANI, DENEME_TAVANI)
          and uyku == list(GERI_CEKILME_SN), (rc, deneme, d1, uyku))

    # --- FAIL-CLOSED: YARIS SONRASI TAZELEME DUSTU (tur ORTASINDA ag koptu) ---
    orta = {"d1": 0}
    kayit = []

    def _orta_git_dusen(argv, cwd, zaman_asimi=900):              # noqa: ARG001
        kayit.append(argv)
        if argv[0] == "git":
            if orta["d1"] >= 1:      # ILK d1-sync'ten SONRA ag kopar
                return 128, "fatal: unable to access 'origin': Could not resolve host"
            return (0, "121d0691aeee1122334455667788990011223344\n") \
                if argv[1] == "rev-parse" else (0, "")
        orta["d1"] += 1
        return 1, _GERCEK_BAYAT_CIKTI
    rc, deneme = onar(kok="/yok", kos=_orta_git_dusen, bekle=lambda s: None,
                      yaz=lambda *a: None)
    iddia("V5 yaris sonrasi TAZELEME duserse -> rc 2 (OLCULEMEDI), YESIL DEGIL · "
          "d1-sync 2. kez CAGRILMAZ",
          (rc, deneme, orta["d1"]) == (2, 2, 1), (rc, deneme, orta["d1"]))
    kayit = []

    def _git_dusen(argv, cwd, zaman_asimi=900):                   # noqa: ARG001
        kayit.append(argv)
        if argv[0] == "git":
            return 128, "fatal: unable to access 'origin': Could not resolve host"
        raise AssertionError("agac tazelenemedi ama d1-sync CAGRILDI (fail-open!)")
    rc, deneme = onar(kok="/yok", kos=_git_dusen, bekle=lambda s: None,
                      yaz=lambda *a: None)
    iddia("V6 agac UCA TAZELENEMEZSE -> rc 2 · d1-sync HIC cagrilmaz (fail-closed)",
          (rc, deneme) == (2, 1) and all(a[0] == "git" for a in kayit),
          (rc, deneme, kayit))

    # --- GERCEK GIT: 20:47Z 'DOGUSTAN BAYAT CHECKOUT' HALININ ONARIMI ---
    g = _gercek_git_fiksturu()
    iddia("V7 (GERCEK GIT) tazelemeden ONCE agac eski ucta (20:47Z kosumunun hali)",
          g["once"] == g["eski"] and g["once"] != g["yeni"],
          "once=%s eski=%s yeni=%s" % (g["once"][:12], g["eski"][:12], g["yeni"][:12]))
    iddia("V7 (GERCEK GIT) uca_tazele() agaci UZAK UCA getirir -> olcum artik SKIP "
          "edilmez", g["ok"] and g["sonra"] == g["yeni"],
          "ok=%s sonra=%s yeni=%s" % (g["ok"], g["sonra"][:12], g["yeni"][:12]))

    # --- UCUNCU RED SINIFI: YAZICI UCUSTA ---
    # V8: yazici + sonra basari -> RETRY (GERCEK HATA degil)
    rc, deneme, d1, uyku, kayit = kos_senaryo([(4, _GERCEK_YAZICI_CIKTI),
                                               (0, _GERCEK_BASARI_CIKTI)])
    iddia("V8 yazici ucusta + sonra basari -> rc 0 · 2 deneme · 1 bekleme (15 sn) "
          "(CANLI lease RETRY'edilir; GERCEK HATA degil)",
          (rc, deneme, d1, uyku) == (0, 2, 2, [15]), (rc, deneme, d1, uyku))

    # V9: 3 denemenin hepsinde yazici -> rc=5 (ERTELENDI)
    yazilan = []
    uyku_topla = []
    kayit9 = []
    rc, deneme = onar(kok="/yok", kos=_sahte_kos(
        [(4, _GERCEK_YAZICI_CIKTI)] * DENEME_TAVANI, kayit9),
        bekle=uyku_topla.append,
        yaz=lambda *a: yazilan.append(" ".join(str(x) for x in a)))
    iddia("V9 3 deneme yazici -> rc 5 (ERTELENDI) · %d deneme · bekleme [15, 45]"
          % DENEME_TAVANI,
          (rc, deneme) == (5, DENEME_TAVANI) and uyku_topla == list(GERI_CEKILME_SN),
          (rc, deneme, uyku_topla))
    yazi = "\n".join(yazilan)
    # V9b: ERTELENDI imzasi satir olarak VAR
    iddia("V9b ERTELENDI ciktisinda `D1_SENKRON=ERTELENDI SEBEP=YAZICI_UCUSTA` satiri VAR",
          YAZICI_IMZASI.replace("ATLANDI", "ERTELENDI") in yazi, repr(yazi[:200]))
    # V9c: ONARILAMADI / YARIS SURDU hukuM metinleri KARISMIYOR
    iddia("V9c ERTELENDI ciktisinda 'ONARILAMADI' ve 'YARIS SURDU' YOK (hukum karismaz)",
          "ONARILAMADI" not in yazi and "YARIS SURDU" not in yazi, repr(yazi[:200]))

    # V10: GERCEK wrangler hatasi (regresyon — V3 zaten var, KALIR)
    # FIKSTUR SERTLESTIRILDI (dilim-1b): M4 mutantı `_sahte_kos`'un 1 girişlik fikstürde
    # tükenmesine yol açıyordu (3. deneme MutationError → ISTASYON ölümü, IDDIA değil).
    # 3 girişli fikstür: doğru kodun davranışı DEĞİŞMEZ (ilk d1 hatasında `return 1, deneme`
    # ile çıkar; 2 giriş kullanılmaz); M4 mutantı 3 denemeyi de TÜKETİR, sonunda rc=3
    # (YARIS SURDU) üretir → test `(1, 1, 1, [])` iddiasıyla YAKALAR (mod=IDDIA).
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_HATA_CIKTI)] * DENEME_TAVANI)
    iddia("V10 GERCEK wrangler hatasi -> rc 1 AYNEN (V3 regresyonu; M4 fikstur tukenmesi "
          "IDDIA'ya cevrildi; dogru kod hâlâ 1. denemede rc=1)",
          (rc, deneme, d1, uyku) == (1, 1, 1, []), (rc, deneme, d1, uyku))

    # V11: karantina imzasi (regresyon — V3b zaten var, KALIR)
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_KARANTINA_CIKTI)])
    iddia("V11 karantina damgasi okunamadi -> rc 4 AYNEN (V3b regresyonu)",
          (rc, deneme, d1, uyku) == (4, 1, 1, []), (rc, deneme, d1, uyku))

    # V12: bayatlik tavan boyunca -> rc=3 AYNEN, YAZICI kolu bayatlik kolunu CALMAMIS
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_BAYAT_CIKTI)] * DENEME_TAVANI)
    iddia("V12 bayatlik tavan boyunca -> rc 3 AYNEN (YAZICI kolu bayatlik kolunu CALMAMIS)",
          (rc, deneme, d1) == (3, DENEME_TAVANI, DENEME_TAVANI)
          and uyku == list(GERI_CEKILME_SN), (rc, deneme, d1, uyku))

    # --- K222: HUKUM `rc`DEN DEGIL IMZADAN OKUNUR (19 Agu 2026) -----------------
    # CANLI SINIF: kapi yazmayi BLOKLAR ama surec 0 ile cikar. Eski surucu `if rc == 0`
    # kolunu imza kolundan ONCE okudugu icin "✅ ONARILDI" basiyordu: D1'e tek satir
    # yazilmamisken kosum YESIL. Asagidaki dort vaka UC imza kolunu da rc=0 altinda
    # olcer + POZITIF KONTROL ile gercek basarinin bozulmadigini kanitlar.
    rc, deneme, d1, uyku, yazi18 = kos_senaryo_yazili(
        [(0, _GERCEK_BAYAT_CIKTI)] * DENEME_TAVANI)
    iddia("V18 (K222) BAYATLIK imzasi + rc=0 -> 'ONARILDI' BASILMAZ, YARIS koluna gider "
          "(rc 3 · %d deneme · geri cekilme %s)" % (DENEME_TAVANI, list(GERI_CEKILME_SN)),
          (rc, deneme, d1) == (3, DENEME_TAVANI, DENEME_TAVANI)
          and uyku == list(GERI_CEKILME_SN)
          and "ONARILDI" not in yazi18 and "YARIS SURDU" in yazi18,
          (rc, deneme, d1, uyku, "ONARILDI" in yazi18))

    rc, deneme, d1, uyku, yazi19 = kos_senaryo_yazili([(0, _GERCEK_BASARI_CIKTI)])
    iddia("V19 (K222 POZITIF KONTROL) imza YOK + rc=0 -> 'ONARILDI' AYNEN yazilir "
          "(kapi gevsetilmedi; gercek basari hala YESIL)",
          (rc, deneme, d1, uyku) == (0, 1, 1, []) and "ONARILDI" in yazi19,
          (rc, deneme, d1, uyku, "ONARILDI" in yazi19))

    rc, deneme, d1, uyku, yazi20 = kos_senaryo_yazili([(0, _GERCEK_KARANTINA_CIKTI)])
    iddia("V20 (K222) KARANTINA imzasi + rc=0 -> rc 4 (fail-closed), 'ONARILDI' BASILMAZ",
          (rc, deneme, d1, uyku) == (4, 1, 1, []) and "ONARILDI" not in yazi20,
          (rc, deneme, d1, uyku, "ONARILDI" in yazi20))

    rc, deneme, d1, uyku, yazi21 = kos_senaryo_yazili(
        [(0, _GERCEK_YAZICI_CIKTI)] * DENEME_TAVANI)
    iddia("V21 (K222) YAZICI imzasi + rc=0 -> rc 5 (ERTELENDI), 'ONARILDI' BASILMAZ",
          (rc, deneme, d1) == (5, DENEME_TAVANI, DENEME_TAVANI)
          and uyku == list(GERI_CEKILME_SN) and "ONARILDI" not in yazi21,
          (rc, deneme, d1, uyku, "ONARILDI" in yazi21))

    # V22: rc=0 ile ONARILDI arasindaki bagi imza KOLU keser — imzasiz rc!=0 hala
    # GERCEK HATA. (Yeni kolun yanlis-pozitif ekseni: her sey 'imza' sayilmadi.)
    rc, deneme, d1, uyku, yazi22 = kos_senaryo_yazili(
        [(1, _GERCEK_HATA_CIKTI)] * DENEME_TAVANI)
    iddia("V22 (K222 YANLIS-POZITIF NOBETI) imza YOK + rc!=0 -> rc 1 GERCEK HATA AYNEN "
          "(imza kolu her ciktiyi 'kapi reddi' saymiyor)",
          (rc, deneme, d1, uyku) == (1, 1, 1, []) and "GERCEK HATA" in yazi22,
          (rc, deneme, d1, uyku))

    # --- K222Rc: HUKUM POZITIF IZDEN OKUNUR — UC HAL AYRI AYRI (24 Agu 2026) ------
    # MIMAR HUKMU: "rc, aracin NE YAPTIGINI degil COKUP COKMEDIGINI soyler." `_hukum_imzasi`
    # yalnizca TANIDIGIMIZ kapi reddini gorur; "red imzasi YOK" onarimin OLDUGUNU kanitlamaz.
    # Asagidaki UC vaka, uc hâlin her birini KENDI jetonu + KENDI rc'siyle ayri ayri olcer.

    # --- POZITIF IZ CAPALARI (izler d1-sync govdesinde GERCEKTEN ve TEK KEZ uretiliyor mu) ---
    for _jeton, _adet in onarim_izi_capasi():
        iddia("IZ CAPASI [%s]: uretim satiri d1-sync.py'de GERCEKTEN ve TEK KEZ geciyor "
              "(0 -> her basarili kosum OLCULEMEDI sayilir; 2 -> biri bayatlayip SESSIZCE "
              "gecer)" % _jeton, _adet == 1, "adet=%d (kabul: 1)" % _adet)

    # V23 — HAL 1/3: ONARILDI. POZITIF iz VAR (yazildi + geri okuma teyit etti), rc=0.
    rc, deneme, d1, uyku, yazi23 = kos_senaryo_yazili([(0, _GERCEK_BASARI_CIKTI)])
    iddia("V23 (K222Rc HAL 1/3 = ONARILDI) yazma izi VAR + rc=0 -> rc 0 · 'ONARILDI' "
          "yazilir · sayim onarildi=1",
          (rc, deneme, d1, uyku) == (0, 1, 1, [])
          and "ONARILDI" in yazi23
          and "GERI-OKUMA DOGRULANDI:" in yazi23
          and "UC_HAL SAYIM: onarildi=1 onarilamadi=0 olculemedi=0" in yazi23,
          (rc, deneme, d1, uyku, yazi23[-120:]))

    # V23b — ONARILDI'nin ikinci mesru sekli: YAZACAK IS YOKTU (d1-sync:4669).
    # Bu vaka olmadan "iz zorunlulugu" en sik canli hâli KIRMIZI yakardi (yanlis-pozitif).
    rc, deneme, d1, uyku, yazi23b = kos_senaryo_yazili([(0, _GERCEK_ISYOK_CIKTI)])
    iddia("V23b (K222Rc) 'degisiklik yok — D1'e urun yazilmadi' izi de ONARILDI'dir "
          "(yazacak is yoktu; en sik canli hal yanlis-pozitif OLMAZ)",
          (rc, deneme, d1, uyku) == (0, 1, 1, []) and "ONARILDI" in yazi23b,
          (rc, deneme, d1, uyku, "ONARILDI" in yazi23b))

    # V24 — HAL 2/3: ONARILAMADI. POZITIF iz YOK + rc != 0 -> gercek hata, rc 1.
    rc, deneme, d1, uyku, yazi24 = kos_senaryo_yazili(
        [(1, _GERCEK_HATA_CIKTI)] * DENEME_TAVANI)
    iddia("V24 (K222Rc HAL 2/3 = ONARILAMADI) iz YOK + rc!=0 -> rc 1 · 'ONARILAMADI' "
          "jetonu yazilir · sayim onarilamadi=1",
          (rc, deneme, d1, uyku) == (1, 1, 1, [])
          and "ONARILAMADI" in yazi24
          and "UC_HAL SAYIM: onarildi=0 onarilamadi=1 olculemedi=0" in yazi24,
          (rc, deneme, d1, uyku, yazi24[-120:]))

    # 🔴 V25 — HAL 3/3 = NEGATIF KONTROL (BU KALEMIN OZU).
    # Arac yazmayi YAPMADI ama surec DUZGUN bicimde 0 ile cikti ve TANIDIGIMIZ hicbir kapi
    # imzasi da basmadi. ESKI surucu burada "✅ ONARILDI" basar, kosum YESIL doner, D1'e tek
    # satir yazilmamis olurdu. Hukum: OLCULEMEDI (rc 6) — `ONARILDI` YAZILMAZ.
    rc, deneme, d1, uyku, yazi25 = kos_senaryo_yazili([(0, _GERCEK_IZSIZ_CIKTI)])
    iddia("V25 (K222Rc HAL 3/3 = OLCULEMEDI · NEGATIF KONTROL) iz YOK + rc=0 -> rc %d · "
          "'ONARILDI' BASILMAZ · 'OLCULEMEDI' yazilir · TEK deneme (yeniden DENENMEZ) · "
          "sayim olculemedi=1" % OLCULEMEDI_IZSIZ_RC,
          (rc, deneme, d1, uyku) == (OLCULEMEDI_IZSIZ_RC, 1, 1, [])
          and "ONARILDI" not in yazi25
          and "OLCULEMEDI" in yazi25
          and "UC_HAL SAYIM: onarildi=0 onarilamadi=0 olculemedi=1" in yazi25,
          (rc, deneme, d1, uyku, "ONARILDI" in yazi25, yazi25[-120:]))

    # V25b — UCUNCU HAL `ONARILDI`ya KARISMAZ: uc hâlin rc'leri BIRBIRINDEN AYRI.
    iddia("V25b (K222Rc) uc hâlin rc'leri AYRI: ONARILDI=0 · ONARILAMADI=1 · OLCULEMEDI=%d "
          "(ucuncu hal sessizce yesile ya da gercek hataya KARISMAZ)" % OLCULEMEDI_IZSIZ_RC,
          len({0, 1, OLCULEMEDI_IZSIZ_RC}) == 3
          and OLCULEMEDI_IZSIZ_RC not in (0, 1, 2, 3, 4, ERTELENDI_RC),
          "OLCULEMEDI_IZSIZ_RC=%d ERTELENDI_RC=%d" % (OLCULEMEDI_IZSIZ_RC, ERTELENDI_RC))

    # V25c — FAIL-CLOSED SIRA: kapi reddi imzasi VARKEN pozitif iz de ciktida gecse bile
    # hukum kapi reddine gider. (Karantina ciktisi GERCEKTEN ikisini birden tasir.)
    iddia("V25c (K222Rc) karantina ciktisi POZITIF izi de tasir; hukum yine de rc 4 "
          "(imza kolu izden ONCE — fail-closed)",
          "GERI-OKUMA DOGRULANDI:" in _GERCEK_KARANTINA_CIKTI
          and _onarim_izi(_GERCEK_KARANTINA_CIKTI) is not None
          and _hukum_imzasi(_GERCEK_KARANTINA_CIKTI) == "KARANTINA",
          _hukum_imzasi(_GERCEK_KARANTINA_CIKTI))

    print("  [SAYIM] K222Rc uc-hal vakasi: 3 (V23 ONARILDI · V24 ONARILAMADI · "
          "V25 OLCULEMEDI) + 4 destek (V23b · V25b · V25c + %d iz capasi)"
          % len(ONARIM_IZLERI))

    # --- KAPSAM KAPISI ---
    # V13: GERCEK d1-sync.py uzerinde -> sorunlar []
    sorunlar, evren = imza_kapsam_kapisi()
    iddia("V13 imza_kapsam_kapisi() GERCEK d1-sync.py uzerinde -> sorunlar YOK",
          sorunlar == [], (sorunlar, evren))

    # V14/V15 fikstur: gecici kopya uzerinde
    import shutil as _shutil
    import tempfile as _tempfile
    import importlib as _importlib
    tmp = _tempfile.mkdtemp(prefix="pruvo-uzl-kapsam-")
    try:
        _shutil.copy(D1_SYNC, os.path.join(tmp, "d1-sync.py"))
        gecici = os.path.join(tmp, "d1-sync.py")

        # V14: SEBEP=BASKA_SEY satiri eklenmis -> SORUN
        with open(gecici, encoding="utf-8") as f:
            govde14 = f.read()
        with open(gecici, "w", encoding="utf-8") as f:
            f.write(govde14 + "\nprint('D1_SENKRON=ATLANDI SEBEP=BASKA_SEY')\n")
        sorunlar14, _ = imza_kapsam_kapisi(d1_sync_yolu=gecici)
        iddia("V14 fikstur: gecici kopyada `SEBEP=BASKA_SEY` uretiliyor -> KIRMIZI",
              any("BASKA_SEY" in s for s in sorunlar14), sorunlar14)

        # V15: main() icine `return 7` eklenmis -> SORUN
        with open(gecici, "w", encoding="utf-8") as f:
            f.write(govde14)              # BASKA_SEY satiri EKLENMEMIS hali
        with open(gecici, encoding="utf-8") as f:
            govde15 = f.read()
        # main()'in hemen ONCESINE `return 7` ile biten satir enjekte et; main() tanimi
        # icinde degil, ama ast.parse modül duzeyinde tum Return'leri walk ile topluyor
        # — o yuzden bir alt fonksiyon ac ve icine `return 7` koy ki `main()`'in govdesine
        # etki etmesin AMA yine de evrende gorunsun... daha basit yol: main() icindeki
        # son if-elif'in bir koluna `return 7` enjekte et. main() kaynaginda `return 0`
        # tek-esleme; ondan once `return _adim_kos()` var. main()'in govdesine yeni bir
        # satir EKLE: `        return 7`.
        yeni15 = govde15.replace("        return _adim_kos()",
                                  "        return _adim_kos()\n        return 7", 1)
        if yeni15 == govde15:
            # Eslesmedi — fikstur metni sabit degil; bu durumda testi KIRMIZI yap
            iddia("V15 fikstur: `return 7` enjekte EDILEMEDI (kaynak metni degisti)",
                  False, "eslesme yok")
        else:
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(yeni15)
            sorunlar15, _ = imza_kapsam_kapisi(d1_sync_yolu=gecici)
            iddia("V15 fikstur: gecici kopyanin main()'ine `return 7` eklenmis -> KIRMIZI",
                  any("[7]" in s for s in sorunlar15), sorunlar15)

        # V16: TANINMAYAN return sekli — `return sys.exit(3)` (ast.Call, attr='exit',
        # TURETILMIS_RC_IZNI ∋ {"_adim_kos"} listesinde YOK). Fail-closed kolu
        # olculmemis ([[cec-dilim1b-cekTrC]] testi).
        with open(gecici, "w", encoding="utf-8") as f:
            f.write(govde15)
        with open(gecici, encoding="utf-8") as f:
            govde16 = f.read()
        yeni16 = govde16.replace("        return _adim_kos()",
                                  "        return _adim_kos()\n        return sys.exit(3)", 1)
        if yeni16 == govde16:
            iddia("V16 fikstur: `return sys.exit(3)` enjekte EDILEMEDI (kaynak metni degisti)",
                  False, "eslesme yok")
        else:
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(yeni16)
            sorunlar16, _ = imza_kapsam_kapisi(d1_sync_yolu=gecici)
            iddia("V16 fikstur: gecici kopyanin main()'ine `return sys.exit(3)` eklenmis -> "
                  "KIRMIZI (taninmayan return sekli; TURETILMIS_RC_IZNI listesinde YOK)",
                  any("exit" in s and "TURETILMIS_RC_IZNI" in s for s in sorunlar16), sorunlar16)
    finally:
        _shutil.rmtree(tmp, ignore_errors=True)

    # --- V17: fazla_sebep kolu (P3) ---
    # surucu'da `ELE_ALINAN_SEBEP`'e elle `"UYDURMA"` eklenmis bir kopyada kapı KIRMIZI
    # vermeli (fazla_sebep kolu olculmemis). Yontem: gecici surucu kopyasina sahneyi
    # yaz, importlib ile yukle, imza_kapsam_kapisi()'ni GERCEK d1-sync.py uzerinde kos.
    _tmp_surucu = _tempfile.mkdtemp(prefix="pruvo-uzl-surucu-")
    try:
        _shutil.copy(os.path.abspath(__file__), os.path.join(_tmp_surucu, "uzlastirici-onarim.py"))
        gecici_surucu = os.path.join(_tmp_surucu, "uzlastirici-onarim.py")
        with open(gecici_surucu, encoding="utf-8") as f:
            govde_surucu = f.read()
        yeni_surucu = govde_surucu.replace(
            'ELE_ALINAN_SEBEP = {"YAZICI_UCUSTA"}',
            'ELE_ALINAN_SEBEP = {"YAZICI_UCUSTA", "UYDURMA"}', 1)
        if yeni_surucu == govde_surucu:
            iddia("V17 fikstur: `ELE_ALINAN_SEBEP'e 'UYDURMA' enjekte EDILEMEDI",
                  False, "eslesme yok")
        else:
            with open(gecici_surucu, "w", encoding="utf-8") as f:
                f.write(yeni_surucu)
            # Gecici surecu import et (kendi mod adinda, ana surucuyle cakisma olmasin)
            _spec = _importlib.util.spec_from_file_location("uzlastirici_onarim_v17", gecici_surucu)
            _mod = _importlib.util.module_from_spec(_spec)
            sys.modules["uzlastirici_onarim_v17"] = _mod
            _spec.loader.exec_module(_mod)
            sorunlar17, _ = _mod.imza_kapsam_kapisi(d1_sync_yolu=D1_SYNC)
            iddia("V17 fikstur: ELE_ALINAN_SEBEP'e 'UYDURMA' eklenmis gecici surucu kopyasinda "
                  "kapı KIRMIZI (fazla_sebep kolu: surucu 'UYDURMA' beyan ediyor ama d1-sync "
                  "URETMIYOR)",
                  any("UYDURMA" in s for s in sorunlar17), sorunlar17)
    finally:
        _shutil.rmtree(_tmp_surucu, ignore_errors=True)

    print("\n%d iddia kosturuldu, %d KIRMIZI." % (sayac[0], len(hatalar)))
    return hatalar


def _mutant_oldu_mu(mutant_kaynak, dosya_yolu):
    """Bir mutant kaynagi bellekte exec et, kendini_test() kos, hata listesi bos degilse
    OLDU demektir. ns icindeki __name__/__file__ gercek __file__'a sabitlenir (importlib
    zincirinin patlamamasi icin). Mutant disk yazmaz; Okan disk kurali + bytecode
    onbellegi tuzaginin onlemi.

    Doner: (oldu:bool, mod:str, detay:str)
      mod ∈ "IDDIA"    -> kendini_test() hata listesi bos degil (gercek iddia ile yakalandi)
      mod ∈ "ISTASYON" -> kendini_test() calismadi (istisna atildi; mutant KILITLI)

    IDDIA modu: gercek kapinin calistigini ispatlar.
    ISTASYON modu: mutant calistirilamadi; fikstur tukenmesi yuzunden mutant kendini_test'i
    bile bitiremedi. Hâlâ OLDU sayilir ([[beyan-edilmis-survivor]] invariantinin tam tersi:
    mutant calismadi -> kapinin var oldugu ispatlandi) AMA GORUNUR ([[mutasyon-kaniti-
    yeniden-uretilebilir]]): --mutasyon ISTASYON sayisini ayri raporlar; sessiz esitleme
    biter. Ideal durum IDDIA=5; ISTASYON>0 fikstur sertlestirmesi bekleyen mutanttir.
    """
    import io as _io

    ns = globals().copy()
    ns["__name__"] = "mutant"
    ns["__file__"] = os.path.abspath(dosya_yolu)
    eski_stdout = sys.stdout
    sys.stdout = yakala = _io.StringIO()
    try:
        exec(compile(mutant_kaynak, dosya_yolu, "exec"), ns)
        hatalar = ns["kendini_test"]()
    except Exception as e:                                            # noqa: BLE001
        sys.stdout = eski_stdout
        # ISTASYON: mutant calismadi. Kapinin var oldugunu ispatlar AMA kapinin NE
        # yakaladigini iddia duzeyinde ispatlamaz -> fikstur sertlestirmesiyle IDDIA'ya
        # cevrilmeli; cevrilemiyorsa ISTASYON olarak raporlanir.
        return True, "ISTASYON", ("🔴 MUTANT CALISTIRILAMADI (kendini_test() istasyon): %s: %s"
                                   % (type(e).__name__, e))
    finally:
        sys.stdout = eski_stdout
    return bool(hatalar), "IDDIA", yakala.getvalue()


MUTANT_TANIMLARI = [
    # (etiket, arama, degistirme)
    ("M1 YAZICI_IMZASI kolunu 'if False and ...' yap -> V8 GERCEK HATA'ya dusmeli",
     "if YAZICI_IMZASI in cikti:", "if False and YAZICI_IMZASI in cikti:"),
    # DİLİM-2B: M2 çapası dilim-2 ile degisti — eski arama kaynakta count=0 idi
    # ([[yeni-kol-mutasyon-capasini-ikizler]]); UYGULANAMADI sayisini arttirip sessizce
    # YESIL'e boyuyordu. Yeni arama iki yerde gecmektedir: gercek cagri (source) ve bu
    # MUTANT_TANIMLARI satiri; replace(...,1) ilkini (source) degistirir.
    ("M2 ERTELENDI_RC yerine 0 doner (yesile boyama) -> V9 yakalar",
     "return ERTELENDI_RC, DENEME_TAVANI", "return 0, DENEME_TAVANI"),
    ("M3 YAZICI kolundaki 'continue' -> 'return 1, deneme' -> V8 tek denemede GERCEK HATA",
     "yaz(\"⚠️  YAZICI UCUSTA: baska makine canli D1 lease'i tutuyor; senkron \"\n"
     "                    \"TASARIM GEREGI atlandi (GERCEK HATA DEGIL). %d sn geri cekilip \"\n"
     "                    \"TEKRAR deniyorum.\" % gecikme)\n"
     "                bekle(gecikme)\n"
     "            continue",
     "yaz(\"⚠️  YAZICI UCUSTA: baska makine canli D1 lease'i tutuyor; senkron \"\n"
     "                    \"TASARIM GEREGI atlandi (GERCEK HATA DEGIL). %d sn geri cekilip \"\n"
     "                    \"TEKRAR deniyorum.\" % gecikme)\n"
     "                bekle(gecikme)\n"
     "            return 1, deneme"),
    ("M4 ONARILAMADI kolu 'return 1, deneme' -> 'son_sinif=BAYATLIK; continue' -> "
     "V10/V24 gorunmez",
     "        _sayim_bas()\n"
     "        return 1, deneme",
     "        son_sinif = \"BAYATLIK\"\n"
     "        continue"),
    ("M5 B ekseni re.findall -> el ile kume (kapsam korlugu) -> V14 gormezden gelinirdi",
     "evren_sebep = set(re.findall(r\"SEBEP=([A-Z0-9_]+)\", kaynak))",
     "evren_sebep = {\"YAZICI_UCUSTA\"}"),
    # --- K222 (19 Agu 2026) — HEDEF KOL: hukum imzadan mi rc'den mi okunuyor ---
    # M6, K222 kusurunu AYNEN geri koyar: `imza is None` sarti dusurulur, yani `rc == 0`
    # tek basina ONARILDI yazdirir. HEDEF KOL: V18/V20/V21 (rc=0 + kapi imzasi).
    # V1/V19 (gercek basari) DEGISMEZ -> mutantin oldurdugu kol IZOLE ([[K182]]).
    # Arama metni kaynakta IKI yerde gecer (gercek `onar()` govdesi + bu satir);
    # replace(...,1) ILKINI (govde) degistirir — M2 ile ayni bilinen desen.
    ("M6 (K222) `if imza is None and rc == 0:` -> `if rc == 0:` (sahte YESIL geri gelir) "
     "-> V18/V20/V21 yakalar, V19 pozitif kontrolu DEGISMEZ",
     "        if imza is None and rc == 0:",
     "        if rc == 0:"),
    # M7, imza TURETICISININ bayatlik kolunu oldurur: hukum kaynagi bosalir.
    # HEDEF KOL: V18 (rc=0'da ONARILDI'ya duser) + V2/V4 (rc=1'de GERCEK HATA'ya duser).
    # YAZICI/KARANTINA kollari SAGLAM kalir -> V9/V3b degismez ([[ad-iki-rolde-mutanti-golgeler]]).
    ("M7 (K222) `_hukum_imzasi` BAYATLIK kolu olur -> V18 ONARILDI'ya, V2/V4 GERCEK "
     "HATA'ya duser (YAZICI/KARANTINA kollari saglam kalir)",
     "    if BAYATLIK_IMZASI in cikti:\n        return \"BAYATLIK\"",
     "    if False and BAYATLIK_IMZASI in cikti:\n        return \"BAYATLIK\""),
    # --- K222Rc (24 Agu 2026) — HEDEF KOL: hukum POZITIF izden mi rc'den mi okunuyor ---
    # M8 (a) SIRA BOZMA: iz kolu `rc` kolundan SONRAYA alinir; yani `rc == 0` tek basina
    # ONARILDI yazdirir. HEDEF KOL: V25 (iz YOK + rc=0). IZOLASYON: V23/V23b/V19/V1
    # (iz VAR + rc=0) DEGISMEZ — mutant yalnizca ucuncu hâli oldurur ([[K182]] hedef-kol atfi).
    ("M8 (K222Rc/a) POZITIF iz kolu `rc` kolundan SONRAYA alinir (`rc == 0` tek basina "
     "ONARILDI yazdirir) -> V25 yakalar, V23/V23b DEGISMEZ",
     "        if imza is None and iz is not None:\n"
     "            sayim[\"onarildi\"] += 1",
     "        if imza is None and rc == 0:\n"
     "            sayim[\"onarildi\"] += 1"),
    # M9 (b) IZ KONTROLUNU TUMDEN KALDIR: `_onarim_izi` her ciktida iz "bulur".
    # HEDEF KOL: V25 (rc 6 -> 0) + V24/V3/V10 (rc 1 -> 0). IZOLASYON: V23 (gercek iz)
    # DEGISMEZ; V18/V20/V21 de degismez cunku onlarda `imza is not None`.
    ("M9 (K222Rc/b) `_onarim_izi` her zaman iz DONER (pozitif kontrol tumden kalkar) -> "
     "V24/V25 yakalar, V23 DEGISMEZ",
     "    for jeton, _capa in ONARIM_IZLERI:\n"
     "        if jeton in cikti:\n"
     "            return jeton\n"
     "    return None",
     "    for jeton, _capa in ONARIM_IZLERI:\n"
     "        if jeton in cikti:\n"
     "            return jeton\n"
     "    return ONARIM_IZLERI[0][0]"),
    # M10 (c) UCUNCU HALI YESILE KAYDIR: OLCULEMEDI kolu rc 0 doner (metin AYNEN kalir —
    # yani "hukum metni dogru ama sayi yalan" hâli). HEDEF KOL: V25'in rc iddiasi.
    # IZOLASYON: baska hicbir vaka bu satira ugramaz.
    ("M10 (K222Rc/c) OLCULEMEDI kolu `ONARILDI`ya kaydirilir (rc 6 -> 0, metin aynen) -> "
     "V25 yakalar",
     "            return OLCULEMEDI_IZSIZ_RC, deneme",
     "            return 0, deneme"),
]

# KONTROL MUTANTI (K222Rc kabul sarti): K222Rc vakalari TAUTOLOJI DEGIL mi?
# ILGISIZ bir kol bozulunca K222Rc vakalari YASAMALI, yalnizca o kolun KENDI vakasi
# olmelidir. Boyle bir olcum olmadan "3 mutant kirmizi yakti" cumlesi, vakalarin hedefle
# BIRLIKTE dusen tautolojiler olmadigini kanitlamaz ([[sahte-bagimlilik-sekli-negatif-blogu-kutsar]]).
KONTROL_MUTANTI = (
    "KONTROL: kapsam kapisinin B ekseni (re.findall) elle kumeye cevrilir — K222Rc ile "
    "ILGISIZ kol",
    "evren_sebep = set(re.findall(r\"SEBEP=([A-Z0-9_]+)\", kaynak))",
    "evren_sebep = {\"YAZICI_UCUSTA\"}",
    "V14",                       # OLMESI beklenen vaka (bu kolun KENDI vakasi)
    ("IZ CAPASI", "V23", "V24", "V25"),   # YASAMASI beklenen K222Rc vakalari
)

# HEDEF-KOL ATIFLARI (K222Rc kabul sarti): her mutant HANGI vakayi oldurdugunu AYRICA
# kanitlar. "Mutant kirmizi yakti" tek basina yetmez — mutant hedefini vurmadan yan
# hasarla da kirmizi yakabilir ([[ad-iki-rolde-mutanti-golgeler]]).
# (mutant_onek, OLMESI_beklenen_vaka_onekleri, YASAMASI_beklenen_vaka_onekleri)
HEDEF_KOL_ATIFLARI = (
    # M8 sirayi bozar -> yalnizca UCUNCU HAL duser; gercek basari kolu DOKUNULMAZ.
    ("M8", ("V25",), ("V23", "V19", "V1")),
    # M9 pozitif kontrolu tumden kaldirir -> hem ONARILAMADI hem OLCULEMEDI yesile kayar;
    # gercek iz tasiyan V23 DEGISMEZ (iz zaten bulunuyordu).
    ("M9", ("V24", "V25"), ("V23",)),
    # M10 yalnizca ucuncu hâlin rc'sini yesile kaydirir -> baska hicbir vaka bu satira ugramaz.
    ("M10", ("V25",), ("V23", "V24", "V19")),
)


def _mutasyonu_kos(dosya_yolu):
    """MUTANT_TANIMLARI'ndaki her mutant + KONTROL kos. (olduler, toplam, kontrol,
    detaylar, iddia_n, istasyon_n, uygulanamadi_n).

    iddia_n        : IDDIA ile yakalanan mutant sayisi (gercek kapinin ispati)
    istasyon_n     : ISTASYON (istisna) ile yakalanan mutant sayisi (fikstur tukenmesi;
                     IDDIA'ya cevrilmeli — cevrilemiyorsa ISTASYON olarak raporlanir)
    uygulanamadi_n : arama metni kaynakta HIC yok (count=0) → mutant ENJEKTE EDILEMEDI.
                     Sessiz survivor YASAK ([[beyan-edilmis-survivor]]); 0'dan buyukse
                     batarya rc=1 ile BASARISIZ sayilir (kapakli degil).
    iddia_n + istasyon_n + uygulanamadi_n == olduler degil: uygulanamadi ayri sayilir
    (replace uygulanamadi → mutant calismadi → olduler 0, uygulanamadi 1). 5 = 5+0+0
    ile 5 = 4+0+1 AYNI sayi vermez; bu farkindalik cercevesinde raporlanir.
    """
    with open(dosya_yolu, encoding="utf-8") as f:
        orijinal = f.read()

    # KONTROL: degismemis kaynak ayni yolla -> hata listesi BOS olmali (YESIL).
    kontrol_hata, kontrol_mod, _ = _mutant_oldu_mu(orijinal, dosya_yolu)
    if kontrol_hata:
        return 0, len(MUTANT_TANIMLARI), False, [
            "KONTROL kirmizi: degismemis kaynak bile kendini_test()'i gecmiyor (mod=%s) — "
            "batarya GEÇERSIZ (sessiz survivor olcmeden YESIL olamaz)" % kontrol_mod], 0, 0, 0

    detaylar = []
    olduler = 0
    iddia_n = 0
    istasyon_n = 0
    uygulanamadi_n = 0
    for etiket, arama, degistirme in MUTANT_TANIMLARI:
        mutant = orijinal.replace(arama, degistirme, 1)
        if mutant == orijinal:
            # replace uygulanamadi → sessiz survivor YASAK ([[beyan-edilmis-survivor]]).
            # olduler artmaz; uygulanamadi_n ayri sayilir ve bataryayi KIRMIZI yapar.
            uygulanamadi_n += 1
            detaylar.append("🔴 %s: UYGULANAMADI (kaynak metni degisti / count=0)" % etiket)
            continue
        oldu, mod, _ = _mutant_oldu_mu(mutant, dosya_yolu)
        if oldu:
            olduler += 1
            if mod == "IDDIA":
                iddia_n += 1
                detaylar.append("✅ %s: OLDU (mod=IDDIA)" % etiket)
            elif mod == "ISTASYON":
                istasyon_n += 1
                detaylar.append("⚠️  %s: OLDU (mod=ISTASYON) — iddia YAKALAYAMADI, fikstur "
                                "tukenmesi kapinin varligini ispatliyor; IDDIA'ya cevirmek "
                                "icin fikstur sertlestirilmeli" % etiket)
        else:
            detaylar.append("🔴 %s: SURVIVOR (mod=IDDIA, kendini_test() yine gecti — "
                            "kapali YOK)" % etiket)
    return olduler, len(MUTANT_TANIMLARI), True, detaylar, iddia_n, istasyon_n, uygulanamadi_n


def _atif_kos(dosya_yolu, etiket, arama, degistirme, olmesi, yasamasi):
    """HEDEF-KOL ATFI olcumu. Doner: (yesil, detay).

    "Mutant KIRMIZI yakti" YETMEZ ([[ad-iki-rolde-mutanti-golgeler]]): mutant hedef kolunu
    oldurmeden, BASKA bir vakanin yan hasariyla da kirmizi yakabilir. Bu fonksiyon mutanti
    uygular, `kendini_test()`'i kosar ve OLEN VAKA KUMESINI iki yonlu yargilar:
      · `olmesi`   onekleriyle baslayan vakalarin HEPSI olmus olmali (hedef GERCEKTEN vuruldu)
      · `yasamasi` onekleriyle baslayan vakalarin HICBIRI olmemis olmali (IZOLASYON /
        tautoloji yok — vaka hedefle BIRLIKTE dusmuyor)
    """
    import io as _io
    with open(dosya_yolu, encoding="utf-8") as f:
        orijinal = f.read()
    mutant = orijinal.replace(arama, degistirme, 1)
    if mutant == orijinal:
        return False, "%s: UYGULANAMADI (capa kaynakta YOK / count=0)" % etiket
    ns = globals().copy()
    ns["__name__"] = "atif_mutant"
    ns["__file__"] = os.path.abspath(dosya_yolu)
    eski_stdout = sys.stdout
    sys.stdout = _io.StringIO()
    try:
        exec(compile(mutant, dosya_yolu, "exec"), ns)
        hatalar = ns["kendini_test"]()
    except Exception as e:                                            # noqa: BLE001
        sys.stdout = eski_stdout
        return False, ("%s: kendini_test() ISTASYON (%s: %s) — ATIF OLCULEMEDI "
                       "(istisna-olumu hedef-kol atfini ifade EDEMEZ)"
                       % (etiket, type(e).__name__, e))
    finally:
        sys.stdout = eski_stdout
    vurulmayan = [o for o in olmesi
                  if not any(h.startswith(o) for h in hatalar)]
    kacan = sorted({h.split(" ")[0] for h in hatalar
                    if any(h.startswith(y) for y in yasamasi)})
    if vurulmayan:
        return False, ("%s: HEDEF KOL VURULMADI — su vakalar OLMEDI: %s. Mutant baska bir "
                       "yoldan kirmizi yakmis olabilir; olen vakalar: %s"
                       % (etiket, list(vurulmayan),
                          sorted({h.split(" ")[0] for h in hatalar})))
    if kacan:
        return False, ("%s: IZOLASYON BOZUK — yasamasi gereken vaka(lar) da oldu: %s "
                       "(vaka hedefle BIRLIKTE dusuyor = tautoloji riski)" % (etiket, kacan))
    return True, ("%s: hedef %s OLDU · izole %s YASADI (olen kume: %s)"
                  % (etiket, list(olmesi), list(yasamasi),
                     sorted({h.split(" ")[0] for h in hatalar})))


def _kontrol_mutantini_kos(dosya_yolu):
    """KONTROL MUTANTI — K222Rc vakalari TAUTOLOJI mi? Doner: (yesil, detay).

    ILGISIZ bir kol (kapsam kapisinin B ekseni) bozulur. YESIL sarti IKI YONLUDUR:
      · o kolun KENDI vakasi (V14) OLMELI      -> kontrol mutanti hedefini gercekten vurdu
      · K222Rc vakalari (IZ CAPASI/V23/V24/V25) YASAMALI -> hedefle BIRLIKTE dusmuyorlar
    Ikinci sart olmadan "3 mutant kirmizi yakti" cumlesi, vakalarin BAGIMSIZ olcum yaptigini
    KANITLAMAZ ([[sahte-bagimlilik-sekli-negatif-blogu-kutsar]])."""
    etiket, arama, degistirme, olmesi_beklenen, yasamasi_beklenen = KONTROL_MUTANTI
    return _atif_kos(dosya_yolu, etiket, arama, degistirme,
                     (olmesi_beklenen,), yasamasi_beklenen)


def _hedef_atiflarini_kos(dosya_yolu):
    """K222Rc mutantlarinin (M8/M9/M10) HEDEF-KOL ATIFLARI. Doner: (hepsi_yesil, detaylar).

    Her mutant icin, MUTANT_TANIMLARI'ndaki AYNI capa yeniden kullanilir (ikiz tanim YOK):
    etiket onekinden bulunur. Boylece capa bayatlarsa hem batarya hem atif AYNI ANDA
    kirmizi yakar; birinin sessizce otekini kutsamasi imkansizdir."""
    tanim = {e.split(" ")[0]: (e, a, d) for e, a, d in MUTANT_TANIMLARI}
    detaylar, hepsi = [], True
    for onek, olmesi, yasamasi in HEDEF_KOL_ATIFLARI:
        if onek not in tanim:
            detaylar.append("🔴 ATIF[%s]: MUTANT_TANIMLARI'nda boyle bir mutant YOK "
                            "(etiket degismis)" % onek)
            hepsi = False
            continue
        etiket, arama, degistirme = tanim[onek]
        yesil, detay = _atif_kos(dosya_yolu, "ATIF[%s]" % onek, arama, degistirme,
                                 olmesi, yasamasi)
        detaylar.append(("✅ " if yesil else "🔴 ") + detay)
        hepsi = hepsi and yesil
    return hepsi, detaylar


def main():
    ap = argparse.ArgumentParser(description="Uzlastirici onarim surucusu")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ + GERCEK GIT fikstur kabulu (CI'da bu kol da kosar)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="Mutasyon bataryasi (%d mutant + KONTROL); diske YAZMAZ"
                         % len(MUTANT_TANIMLARI))
    a = ap.parse_args()
    if a.kendini_test:
        print("UZLASTIRICI ONARIM SURUCUSU — KENDINI TEST")
        hatalar = kendini_test()
        if hatalar:
            print("🔴 KENDINI TEST KIRMIZI:")
            for h in hatalar:
                print("   - %s" % h)
            return 1
        print("✅ KENDINI TEST GECTI")
        return 0
    if a.mutasyon:
        print("UZLASTIRICI ONARIM SURUCUSU — MUTASYON BATARYASI")
        olduler, toplam, kontrol_ok, detaylar, iddia_n, istasyon_n, uygulanamadi_n = \
            _mutasyonu_kos(os.path.abspath(__file__))
        for d in detaylar:
            print("  " + d)
        kontrol_hukum = "YESIL" if kontrol_ok else "KIRMIZI"
        atif_ok, atif_detaylar = _hedef_atiflarini_kos(os.path.abspath(__file__))
        for d in atif_detaylar:
            print("  " + d)
        km_yesil, km_detay = _kontrol_mutantini_kos(os.path.abspath(__file__))
        print("  %s %s" % ("✅" if km_yesil else "🔴", km_detay))
        # iddia_n + istasyon_n == olduler (kendi icinde tutarli); uygulanamadi_n ayri sayilir
        print("\nMUTANT=%d/%d IDDIA=%d ISTASYON=%d UYGULANAMADI=%d KONTROL=%s "
              "HEDEF_ATFI=%d/%d KONTROL_MUTANTI=%s" % (
                  olduler, toplam, iddia_n, istasyon_n, uygulanamadi_n, kontrol_hukum,
                  sum(1 for d in atif_detaylar if d.startswith("✅")),
                  len(HEDEF_KOL_ATIFLARI), "YESIL" if km_yesil else "KIRMIZI"))
        # KIRMIZI: kontrol kirmizi VEYA survivor VEYA en az bir UYGULANAMADI VEYA
        # hedef-kol atfi kirmizi VEYA kontrol mutanti kirmizi (tautoloji / capa bayat)
        if (not kontrol_ok or olduler != toplam or uygulanamadi_n > 0
                or not atif_ok or not km_yesil):
            return 1
        return 0
    rc, deneme = onar()
    print("SONUC: rc=%d (deneme %d/%d)" % (rc, deneme, DENEME_TAVANI))
    return rc


if __name__ == "__main__":
    sys.exit(main())
