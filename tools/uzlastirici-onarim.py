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

CIKIS KODLARI
=============
  0 = ONARILDI (D1'e yazildi ya da yazacak is yoktu)
  1 = GERCEK HATA (wrangler/D1/sema/kod) — YENIDEN DENENMEZ, gorunur kalir
  2 = OLCULEMEDI (agac uca TAZELENEMEDI: git/ag) — fail-closed
  3 = YARIS SURDU (tavan tukendi, agac hala bayat) — fail-closed

Kullanim:
    python3 tools/uzlastirici-onarim.py                 # GERCEK onarim (CI)
    python3 tools/uzlastirici-onarim.py --kendini-test  # AGSIZ + GERCEK GIT fikstur kabulu
"""
import argparse
import os
import subprocess
import sys
import time
from git_ortami import sentetik_git

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

D1_SYNC = os.path.join(TOOLS, "d1-sync.py")
UZAK = "origin"
DAL = "main"

# d1-sync.py bayatlik kapisi reddinin IMZASI (TEK KAYNAK: bayatlik_engel_metni()).
# Bu metin degisirse asagidaki `imza_capasi()` KIRMIZI yanar -> imza sessizce bayatlayamaz.
BAYATLIK_IMZASI = "!! BAYATLIK KAPISI:"

DENEME_TAVANI = 3
GERI_CEKILME_SN = (15, 45)      # 1. ve 2. basarisiz denemeden SONRA beklenen sure


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


def onar(kok=ROOT, kos=_kos, bekle=time.sleep, yaz=print):
    """Tazele -> d1-sync -> (yaris ise) tekrar. Doner: (rc, deneme_sayisi)."""
    for deneme in range(1, DENEME_TAVANI + 1):
        ok, bilgi = uca_tazele(kok, kos)
        if not ok:
            yaz("🔴 OLCULEMEDI: agac uzak %s/%s UCUNA tazelenemedi -> %s" % (UZAK, DAL, bilgi))
            yaz("   FAIL-CLOSED: tazelenemeyen agactan yazmak, uzlastiricinin ONLEMEK "
                "icin var oldugu kacagin ta kendisi olurdu.")
            return 2, deneme
        yaz("deneme %d/%d — agac uzak %s/%s ucunda: %s"
            % (deneme, DENEME_TAVANI, UZAK, DAL, bilgi[:12]))

        rc, cikti = kos(["python3", D1_SYNC], kok)
        yaz(cikti.rstrip())
        if rc == 0:
            yaz("✅ ONARILDI (deneme %d/%d)" % (deneme, DENEME_TAVANI))
            return 0, deneme
        if BAYATLIK_IMZASI not in cikti:
            yaz("🔴 GERCEK HATA (rc=%s) — bayatlik kapisi DEGIL. YENIDEN DENENMEZ: bu "
                "sinif (wrangler/D1/sema/kod) yeniden denemeyle gecmez ve GORUNUR "
                "kalmalidir." % rc)
            return 1, deneme
        if deneme < DENEME_TAVANI:
            gecikme = GERI_CEKILME_SN[deneme - 1]
            yaz("⚠️  YARIS: yazma sirasinda main'in ucu ILERLEDI (bayatlik kapisi kapandi). "
                "%d sn geri cekilip agaci yeni uca tazeleyerek TEKRAR deniyorum." % gecikme)
            bekle(gecikme)
    yaz("🔴 YARIS SURDU: %d denemenin hepsinde main'in ucu yazma penceresinde ilerledi. "
        "Olculen tek-deneme carpisma olasiligi %%1,47 idi; %d ardisik carpisma bu "
        "olcumun BAYATLADIGINA isarettir (itme sikligi artmis olabilir)."
        % (DENEME_TAVANI, DENEME_TAVANI))
    return 3, DENEME_TAVANI


# ---- KABUL TESTI ------------------------------------------------------------
def imza_capasi():
    """BAYATLIK_IMZASI d1-sync.py icinde GERCEKTEN uretiliyor mu.

    Imza sessizce degisirse bu surucu her yaris reddini 'GERCEK HATA' sayar ve yeniden
    deneme OLU kalir (sessiz zayiflama). Bu capa o hali KIRMIZI yakar."""
    with open(D1_SYNC, encoding="utf-8") as f:
        return BAYATLIK_IMZASI in f.read()


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
_GERCEK_BASARI_CIKTI = """\
urunler.json: 15955 urun | D1: 15955 urun | gizli baski kaydi: 0 | baski yetki: HAYIR \
(baski atlanir) | taban fiyat semasi: 23 | konfigur semasi: 17
yeni: 0 | degisen: 21 | baski-guncelle: 0 | taban-guncelle: 0 | konfigur-guncelle: 0 | \
silinen: 0 | dokunulmayan: 15934
D1 yazildi: 21 upsert | 0 silme | geri okuma teyidi TAMAM
"""
_GERCEK_HATA_CIKTI = """\
urunler.json: 15955 urun | D1: 15955 urun
wrangler SIFIR-DISI cikti (rc=1) — cikti BASARI sayilmaz:
{"error": {"code": 7429, "message": "D1 CPU limit exceeded"}}
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

    # --- IMZA CAPASI ---
    iddia("IMZA CAPASI: bayatlik reddinin imzasi d1-sync.py'de GERCEKTEN uretiliyor "
          "(imza bayatlarsa yeniden deneme OLU kalirdi)", imza_capasi(),
          "aranan %r" % BAYATLIK_IMZASI)

    # --- YESIL YOL ---
    rc, deneme, d1, uyku, kayit = kos_senaryo([(0, _GERCEK_BASARI_CIKTI)])
    iddia("V1 ilk denemede BASARI -> rc 0 · 1 deneme · 0 bekleme",
          (rc, deneme, d1, uyku) == (0, 1, 1, []), (rc, deneme, d1, uyku))
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
    rc, deneme, d1, uyku, _ = kos_senaryo([(1, _GERCEK_HATA_CIKTI)])
    iddia("V3 GERCEK hata (D1 7429 CPU tavani) -> rc 1 · TEK deneme · 0 bekleme "
          "(kod/altyapi hatasi yeniden denemeyle ORTULMEZ)",
          (rc, deneme, d1, uyku) == (1, 1, 1, []), (rc, deneme, d1, uyku))

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

    print("\n%d iddia kosturuldu, %d KIRMIZI." % (sayac[0], len(hatalar)))
    return hatalar


def main():
    ap = argparse.ArgumentParser(description="Uzlastirici onarim surucusu")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ + GERCEK GIT fikstur kabulu (CI'da bu kol da kosar)")
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
    rc, deneme = onar()
    print("SONUC: rc=%d (deneme %d/%d)" % (rc, deneme, DENEME_TAVANI))
    return rc


if __name__ == "__main__":
    sys.exit(main())
