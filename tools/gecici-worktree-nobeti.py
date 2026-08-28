#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gecici-worktree-nobeti.py — OLCUM KOLU: gercek repoya kayitli SIZAN gecici worktree.

Okan'in DISK EMRI (13 Agu 2026, USTUN): "makineye hicbir sey kalici kaydedilmez;
kaydetmek zorunda kalirsan is bitince geri sileceksin." Bu arac o emrin GECICI WORKTREE
eksenindeki NOBETCISIDIR: kural bir daha SESSIZCE ihlal edilemesin diye.

Neden AYRI bir savunma hatti (ureticinin `finally`sinin YEDEGI DEGIL):
`tools/gecici_worktree.py::temizligi_bagla` atexit + SIGTERM/SIGINT/SIGHUP kapsar ama
**SIGKILL yakalanamaz** ve disk dolulugu/kernel OOM gibi hallerde hicbir kol kosmaz.
Ureticinin kolu "cogu vakayi" kapatir; bu kol "kapanmayan vakayi GORUNUR yapar".

SINIFLAMA (turetimi tools/gecici_worktree.py'de, TEK KAYNAK):
  SIZINTI     sahip PID olu      -> rc=1 (KIRMIZI). `--temizle` ile kaldirilir.
  CANLI       sahip PID yasiyor  -> rc=0. KOSAN bir batarya; DOKUNULMAZ.
  OLCULEMEDI  damga yok          -> rc=3. Eski surum/yabanci uretici; ASLA SILINMEZ.

🔴 "SAYI != 0 ISE KIRMIZI" SEKLINDE NAIF BIR KOL YAZILAMAZ. Bu fiksturler saniyelik
yasar; komsu ev bir batarya kosarken yapilan olcum her an bir tane gorur. Tam bu sahte
kirmizi 19 Agu 2026'da `worktree-tavan-nobeti.py`de yasandi ve 28 Agu'da bu cip
tarafindan TEKRAR olculdu (ad iki olcumde degisti: `ub7g6gr6` -> `pp1d1xdk`).
Sahte kirmizi, gercek kirmiziyi gorunmez yapar.

Kullanim:
    python3 tools/gecici-worktree-nobeti.py                  # ana repoyu olcer
    python3 tools/gecici-worktree-nobeti.py --temizle        # SIZINTI'lari kaldirir
    python3 tools/gecici-worktree-nobeti.py --repo /yol      # baska depoyu olcer
    python3 tools/gecici-worktree-nobeti.py --vakalar        # V1..V6 davranis vakalari
    python3 tools/gecici-worktree-nobeti.py --kendini-test   # mutasyon bataryasi
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

BURASI = os.path.dirname(os.path.abspath(__file__))
if BURASI not in sys.path:
    sys.path.insert(0, BURASI)          # MUTANT KOPYA kendi yanindakini yuklesin
import gecici_worktree as gw            # noqa: E402

KOK = os.path.dirname(BURASI)

RC_TEMIZ = 0
RC_SIZINTI = 1
RC_OLCULEMEDI = 3


# ==========================================================================
# OLCUM
# ==========================================================================
def olc(repo, temizle=False):
    kaldirilan = []
    if temizle:
        kaldirilan, hatalar = gw.sizintilari_temizle(repo)
        for yol, hata in hatalar:
            print("TEMIZLIK BASARISIZ: %s -> %s" % (yol, hata))
        print("TEMIZLENEN_SIZINTI=%d %s" % (len(kaldirilan), kaldirilan or ""))

    kayitlar = gw.gecici_kayitlar(repo)
    sayac = {gw.SIZINTI: 0, gw.CANLI: 0, gw.OLCULEMEDI: 0}
    for yol, sinif, pid in kayitlar:
        sayac[sinif] += 1
        print("  %-11s pid=%-8s %s" % (sinif, pid if pid is not None else "-", yol))

    print("GECICI_WORKTREE SIZINTI=%d CANLI=%d OLCULEMEDI=%d TOPLAM=%d" % (
        sayac[gw.SIZINTI], sayac[gw.CANLI], sayac[gw.OLCULEMEDI], len(kayitlar)))

    if sayac[gw.SIZINTI]:
        print("HUKUM=SIZINTI — sahibi OLU gecici worktree kaydi var; disk emri ihlal "
              "edildi. Kaldirmak icin: python3 tools/gecici-worktree-nobeti.py --temizle")
        return RC_SIZINTI
    if sayac[gw.OLCULEMEDI]:
        print("HUKUM=OLCULEMEDI — damgasiz gecici worktree var (eski surum ya da yabanci "
              "uretici). SILINMEDI: kosan bir komsuya ait olabilir. Ureticisi damga "
              "kazanana kadar hakkinda hukum verilemez.")
        return RC_OLCULEMEDI
    print("HUKUM=TEMIZ")
    return RC_TEMIZ


# ==========================================================================
# URETICI PROBU — gercek bir uretici gibi davranir (V5/V6 icin)
# ==========================================================================
def uretici_probu(repo):
    """Damgali taban + gercek `git worktree add`, sonra sinyal bekler.
    STDOUT'a tek satir `TABAN=<yol>` basar ve akisi bosaltir."""
    gw.temizligi_bagla()
    temel = gw.damgali_mkdtemp("pruvo-nobet-prob-")
    yol = os.path.join(temel, "kayitli-wt")
    sonuc = gw.kaydet(repo, yol, "--no-checkout", "--detach", commitish="HEAD")
    if sonuc.returncode != 0:
        print("PROB-HATA=" + (sonuc.stderr or "?").strip()[:200], flush=True)
        return 2
    print("TABAN=" + temel, flush=True)
    while True:
        time.sleep(0.05)


# ==========================================================================
# V1..V6 — DAVRANIS VAKALARI (mutantlar bunlari kirmizi yakar)
# ==========================================================================
def _git(depo, *argv):
    return subprocess.run(["git", "-C", depo] + list(argv), capture_output=True, text=True)


def _sentetik_depo(temel):
    depo = os.path.join(temel, "depo")
    os.makedirs(depo)
    _git(depo, "init", "-q", "-b", "main")
    _git(depo, "config", "user.email", "nobet@pruvo.local")
    _git(depo, "config", "user.name", "Gecici Worktree Nobeti")
    with open(os.path.join(depo, "f.txt"), "w") as f:
        f.write("taban\n")
    _git(depo, "add", "-A")
    _git(depo, "commit", "-q", "-m", "taban")
    # 🔴 realpath SART: macOS'ta /var -> /private/var symlink'i; git kayda GERCEK yolu
    # yazar, biz de kaydi oyle okuruz ([[sentetik-git-fiksturunde-realpath-sart]]).
    return os.path.realpath(depo)


def _olu_pid():
    """KESIN olu bir PID uretir: bir sureci baslat, BITMESINI BEKLE, pid'ini al."""
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def _fikstur_kur(depo, temel, ad):
    """<temel>/<ad>/kayitli-wt olarak gercek bir worktree kaydeder."""
    ust = os.path.join(temel, ad)
    os.makedirs(ust, exist_ok=True)
    yol = os.path.join(ust, "kayitli-wt")
    r = subprocess.run(["git", "-C", depo, "worktree", "add", "--no-checkout",
                        "--detach", yol, "HEAD"], capture_output=True, text=True)
    return (os.path.realpath(yol) if r.returncode == 0 else None), r


def _kendi_kendini_kos(depo, *ek):
    """Bu betigi (MUTANT kopya olabilir) alt sureçte kosturur, (rc, stdout) doner."""
    komut = [sys.executable, os.path.abspath(__file__), "--repo", depo] + list(ek)
    r = subprocess.run(komut, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _prob_baslat(depo):
    """Uretici probunu baslatir; (popen, taban_yolu|None) doner."""
    p = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--uretici-probu", "--repo", depo],
        stdout=subprocess.PIPE, text=True)
    for _ in range(400):
        satir = p.stdout.readline()
        if satir.startswith("TABAN="):
            return p, satir.strip()[len("TABAN="):]
        if satir.startswith("PROB-HATA=") or p.poll() is not None:
            break
    return p, None


def vakalar():
    """V1..V6. Basarisiz her vaka `vaka N:` satiri basar (mutasyon kolu bunu okur).

    🔴 HER VAKA KENDI SENTETIK DEPOSUNDA KOSAR. Ilk kurguda hepsi TEK depoyu
    paylasiyordu ve OLCULDU: bir mutant V5'i dusurunce V5'in ARTIGI ayni depoda kalip
    V6'nin sayacini da bozuyordu (`SIZINTI=1` yerine `SIZINTI=2`). Yani mutant
    "iki kol birden" oldurmus gibi okunuyor, HEDEF KOL ATFI cokuyordu — bulgu degil,
    ARTIK ([[artik-yuzey-mutant-dedektorunu-korlestirir]] sinifi). Izolasyon bir
    zarafet degil, atfin ON KOSULUDUR."""
    kirmizi = []

    def kayit(no, aciklama, gecti, ayrinti=""):
        print("%-4s %-64s %s" % (no, aciklama, "OK" if gecti else "KIRMIZI"))
        if not gecti:
            print("  vaka %d: %s | %s" % (no, aciklama, ayrinti))
            kirmizi.append(no)

    def ortam():
        temel = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-nobet-vaka-"))
        return temel, _sentetik_depo(temel)

    def kapat(temel, depo, prob=None):
        if prob is not None and prob.poll() is None:
            prob.kill()
            prob.wait(timeout=20)
        for entry in gw.kayitli_agaclar(depo)[1:]:
            subprocess.run(["git", "-C", depo, "worktree", "remove", "--force",
                            entry["yol"]], capture_output=True, text=True)
        shutil.rmtree(temel, ignore_errors=True)

    # --- V1: sahibi OLU damgali fikstur -> SIZINTI + rc=1 --------------------
    temel, depo = ortam()
    try:
        v1_yol, r1 = _fikstur_kur(depo, temel,
                                  "pruvo-nobet-fikstur-p%d-aaaaaaaa" % _olu_pid())
        if v1_yol is None:
            kayit(1, "CEVRE: olu-sahipli fikstur kurulamadi", False,
                  (r1.stderr or "").strip()[:160])
        else:
            rc, cikti = _kendi_kendini_kos(depo)
            kayit(1, "olu sahip PID -> SIZINTI=1 ve rc=1",
                  rc == RC_SIZINTI and "SIZINTI=1 " in cikti,
                  "rc=%s | %s" % (rc, cikti.strip().splitlines()[-1:]))
    finally:
        kapat(temel, depo)

    # --- V2: OLCULEMEDI, SIZINTI'yi GOLGELEMEZ (AYRI KOVA) ------------------
    temel, depo = ortam()
    try:
        _fikstur_kur(depo, temel, "pruvo-nobet-fikstur-p%d-bbbbbbbb" % _olu_pid())
        _fikstur_kur(depo, temel, "pruvo-nobet-fikstur-damgasiz")
        rc, cikti = _kendi_kendini_kos(depo)
        kayit(2, "damgasiz fikstur AYRI kovada: SIZINTI=1 CANLI=0 OLCULEMEDI=1",
              "SIZINTI=1 CANLI=0 OLCULEMEDI=1" in cikti,
              cikti.strip().splitlines()[-2:])
    finally:
        kapat(temel, depo)

    # --- V3: --temizle YALNIZ SIZINTI'yi alir, OLCULEMEDI'ye DOKUNMAZ -------
    temel, depo = ortam()
    try:
        v3_olu, _ = _fikstur_kur(depo, temel,
                                 "pruvo-nobet-fikstur-p%d-cccccccc" % _olu_pid())
        v3_damgasiz, _ = _fikstur_kur(depo, temel, "pruvo-nobet-fikstur-damgasiz")
        rc, cikti = _kendi_kendini_kos(depo, "--temizle")
        olu_gitti = v3_olu is not None and not os.path.exists(v3_olu)
        damgasiz_durdu = v3_damgasiz is not None and os.path.exists(v3_damgasiz)
        kayit(3, "--temizle: SIZINTI kaldirildi, OLCULEMEDI DOKUNULMADI",
              olu_gitti and damgasiz_durdu and rc == RC_OLCULEMEDI,
              "olu_gitti=%s damgasiz_durdu=%s rc=%s" % (olu_gitti, damgasiz_durdu, rc))
    finally:
        kapat(temel, depo)

    # --- V4: sahibi CANLI fikstur -> CANLI, rc=0, --temizle DOKUNMAZ --------
    temel, depo = ortam()
    prob = None
    try:
        prob, taban = _prob_baslat(depo)
        if not taban:
            kayit(4, "CEVRE: uretici probu baslatilamadi", False, "TABAN satiri gelmedi")
        else:
            prob_wt = os.path.join(taban, "kayitli-wt")
            rc, cikti = _kendi_kendini_kos(depo, "--temizle")
            kayit(4, "CANLI sahip: CANLI=1 · rc=0 · --temizle DOKUNMADI",
                  rc == RC_TEMIZ and "SIZINTI=0 CANLI=1" in cikti
                  and os.path.exists(prob_wt),
                  "rc=%s var=%s | %s" % (rc, os.path.exists(prob_wt),
                                         cikti.strip().splitlines()[-1:]))
    finally:
        kapat(temel, depo, prob)

    # --- V5: SIGTERM -> URETICININ KOLU temizler (fikstur KALMAZ) -----------
    temel, depo = ortam()
    prob = None
    try:
        prob, taban = _prob_baslat(depo)
        if not taban:
            kayit(5, "CEVRE: uretici probu baslatilamadi", False, "TABAN satiri gelmedi")
        else:
            prob.terminate()
            prob.wait(timeout=20)
            prob_wt = os.path.join(taban, "kayitli-wt")
            kaldi = os.path.exists(prob_wt) or os.path.exists(taban)
            rc, cikti = _kendi_kendini_kos(depo)
            kayit(5, "SIGTERM: ureticinin sinyal kolu fiksturu KALDIRDI",
                  (not kaldi) and rc == RC_TEMIZ and "TOPLAM=0" in cikti,
                  "diskte_kaldi=%s rc=%s | %s" % (kaldi, rc,
                                                  cikti.strip().splitlines()[-1:]))
    finally:
        kapat(temel, depo, prob)

    # --- V6: SIGKILL -> uretici kolu KOSAMAZ, OLCUM KOLU yakalar ------------
    temel, depo = ortam()
    prob = None
    try:
        prob, taban = _prob_baslat(depo)
        if not taban:
            kayit(6, "CEVRE: uretici probu baslatilamadi", False, "TABAN satiri gelmedi")
        else:
            prob.kill()
            prob.wait(timeout=20)
            rc, cikti = _kendi_kendini_kos(depo)
            kayit(6, "SIGKILL: uretici kolu KOSAMAZ -> olcum kolu SIZINTI yakar",
                  rc == RC_SIZINTI and "SIZINTI=1" in cikti,
                  "rc=%s | %s" % (rc, cikti.strip().splitlines()[-1:]))
    finally:
        kapat(temel, depo, prob)

    print("")
    print("VAKA KIRMIZI: %d %s" % (len(kirmizi), sorted(kirmizi) or ""))
    return 1 if kirmizi else 0


# ==========================================================================
# MUTASYON BATARYASI
# ==========================================================================
MODUL = "gecici_worktree.py"
BETIK = "gecici-worktree-nobeti.py"


def _yama(dizin, dosya, eski, yeni):
    yol = os.path.join(dizin, dosya)
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if eski not in govde:
        raise RuntimeError("MUTASYON CAPASI YOK: %s icinde %r" % (dosya, eski[:70]))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni, 1))


# (ad, uygulayici, aciklama, BEKLENEN kirmizi vaka kumesi = HEDEF KOL ATFI)
MUTASYONLAR = [
    ("M1", lambda d: _yama(
        d, MODUL,
        "    atexit.register(hepsini_temizle)\n",
        "    pass  # MUTANT: atexit+sinyal temizligi KALDIRILDI\n    return\n"),
     "URETICI KOLU olduruldu (atexit/sinyal baglanmaz) -> V5 kirmizi", {5}),

    ("M2", lambda d: _yama(
        d, MODUL,
        "    return (CANLI if pid_canli_mi(pid) else SIZINTI), pid\n",
        "    return CANLI, pid  # MUTANT: sizinti dedektoru korlestirildi\n"),
     "OLCUM KOLU olduruldu (her sey CANLI) -> V1/V2/V3/V6 kirmizi", {1, 2, 3, 6}),

    ("M3", lambda d: _yama(
        d, MODUL,
        "    except PermissionError:\n        return True          # baska kullanicinin sureci — YASIYOR\n",
        "    except PermissionError:\n        return False  # MUTANT: supheyi SILME yonune akitir\n"),
     "SUPHE YONU ters cevrildi (PermissionError -> olu) -> KONTROL: davranis "
     "degismemeli (bu vakalarda PermissionError olusmaz) -> YESIL kalmali", set()),

    ("M4", lambda d: _yama(
        d, MODUL,
        "        if sinif != SIZINTI:\n            continue\n",
        "        if sinif == CANLI:\n            continue  # MUTANT: OLCULEMEDI de silinir\n"),
     "TEMIZLIK MENZILI genisletildi (OLCULEMEDI de silinir) -> V3 kirmizi", {3}),

    ("M5", lambda d: _yama(
        d, MODUL,
        r'PID_DESENI = re.compile(r"-p(\d+)-[A-Za-z0-9_]+\Z")',
        r'PID_DESENI = re.compile(r"-p(\d*)-[A-Za-z0-9_]*\Z")  # MUTANT: gevsetildi'),
     "DAMGA DESENI gevsetildi -> KONTROL: ayni kume, ayni karar -> YESIL kalmali",
     set()),
]


def kendini_test():
    kok = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-nobet-mutasyon-"))
    basarisiz = []
    try:
        def kos(ad, uygulayici):
            dizin = os.path.join(kok, ad)
            os.makedirs(dizin)
            for dosya in (MODUL, BETIK):
                shutil.copyfile(os.path.join(BURASI, dosya), os.path.join(dizin, dosya))
            if uygulayici is not None:
                uygulayici(dizin)
            r = subprocess.run([sys.executable, os.path.join(dizin, BETIK), "--vakalar"],
                               capture_output=True, text=True)
            kirmizi = set()
            for satir in (r.stdout or "").splitlines():
                m = re.match(r"\s*vaka (\d+):", satir)
                if m:
                    kirmizi.add(int(m.group(1)))
            return kirmizi, r.returncode

        # 🔴 TABAN ONCE OLCULUR ([[olcut-civilenirken-taban-olculmeli]]): mutasyonsuz
        # kopyada kirmizi varsa her mutantin kumesine karisir ve hukum COKER.
        TABAN, taban_rc = kos("TABAN", None)
        print("TABAN (mutasyonsuz kopya) | kirmizi=%d %s | rc=%d"
              % (len(TABAN), sorted(TABAN), taban_rc))
        if TABAN or taban_rc != 0:
            basarisiz.append(("TABAN", "0 kirmizi + rc=0", "%s / rc=%d"
                              % (sorted(TABAN), taban_rc)))

        olduruldu = 0
        atif = 0
        for ad, uygulayici, aciklama, beklenen in MUTASYONLAR:
            ham, rc = kos(ad, uygulayici)
            net = ham - TABAN
            kontrol = not beklenen
            if kontrol:
                tamam = (not net) and rc == 0
            else:
                tamam = (net == beklenen)
            if tamam:
                if kontrol:
                    olduruldu += 1        # KONTROL de "beklendigi gibi davrandi"
                else:
                    olduruldu += 1
                    atif += 1
            else:
                basarisiz.append((ad, sorted(beklenen), sorted(net)))
            print("%-4s %-70s beklenen=%-14s net=%-14s %s"
                  % (ad, aciklama[:70], sorted(beklenen), sorted(net),
                     "OLDU" if tamam else "KACTI"))

        hedefli = [m for m in MUTASYONLAR if m[3]]
        print("")
        print("MUTASYON=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d"
              % (olduruldu, len(MUTASYONLAR), atif, len(hedefli),
                 olduruldu - atif, len(MUTASYONLAR) - len(hedefli)))
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    if basarisiz:
        print("KENDINI-TEST KIRMIZI: %s" % (basarisiz,))
        return 1
    print("KENDINI-TEST YESIL")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=KOK)
    ap.add_argument("--temizle", action="store_true")
    ap.add_argument("--vakalar", action="store_true")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--uretici-probu", action="store_true")
    a = ap.parse_args()

    if a.uretici_probu:
        return uretici_probu(os.path.realpath(a.repo))
    if a.kendini_test:
        return kendini_test()
    if a.vakalar:
        return vakalar()
    return olc(os.path.realpath(a.repo), temizle=a.temizle)


if __name__ == "__main__":
    sys.exit(main())
