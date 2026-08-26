#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K308 + K310 KABUL SURUCUSU — TABAN ve SONRA sayilarini AYNI TURDA yan yana basar.

NEDEN AYRI BIR SURUCU VAR: bu iki kalem TEK SINIFTIR (*bir satir guven veriyor ama
arkasindaki olcum ya hic yok ya sebebi yutulmus*) ve kapanislari **taban ile SONRA'nin
birebir kiyaslanmasina** baglidir. Tabani "hatirlayarak" yazmak bu evde kabul degildir
([[olcut-civilenirken-taban-olculmeli]]); taban `git show <ref>:<yol>` ile DISKE
cikarilir ve GERCEKTEN kosturulur.

  K308  pre-push YEDEK blogu: `rc!=0`in SEBEBI push ciktisina ulasiyor mu?
  K310  kutu-arsivle: `lossless_dogrulama=GECTI` beyani blok BUTUNLUGUNU olcuyor mu?

CIKTI YOLU GIT-DISINA CIVILIDIR: ic kosum raporu izlenen agaca dusrse `serit-a3`
kirmizi yanar ve YAYIN DURUR ([[ic-kosum-raporu-izlenen-birakilirsa-yayini-durdurur]]).
`--cikti` depo icini gosterirse arac FAIL-LOUD durur.

Kullanim:
    python3 tools/k308-k310-kabul.py --cikti /tmp/k308-k310.txt
    python3 tools/k308-k310-kabul.py --cikti /tmp/k308-k310.txt --taban-ref main
(cikis kodu 0 = SONRA tarafinin TAMAMI yesil VE mutantlar beklendigi gibi)
"""
import argparse
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)

KUR = os.path.join(TOOLS, "yedek-hook-kur.py")
ARAC = os.path.join(TOOLS, "kutu-arsivle.py")
HOOK_TEST = os.path.join(TOOLS, "yedek-hook-test.py")
KUTU_TEST = os.path.join(TOOLS, "kutu-arsivle-test.py")
IZLENEN_KANCA = os.path.join(TOOLS, "kancalar", "pre-push")

# Hukum satiri sayilan onekler — K6 (iki ardisik tur BIREBIR) yalniz BUNLARI kiyaslar.
# Ham ciktida gecici dizin adlari var; onlari kiyaslamak turler arasi sahte fark uretir.
HUKUM_ONEKLERI = ("rc=", "TOPLAM ", "VAKA=", "SONUC:", "MUTASYON:", "  -> ",
                  "oksuz_govde_", "lossless_dogrulama=", "EKSEN_KOR=", "ayrac_kutu=",
                  "imza_yigilmasi_")

SATIRLAR = []


def y(metin=""):
    print(metin)
    SATIRLAR.append(metin)


def kos(*komut):
    r = subprocess.run(list(komut), capture_output=True, text=True, cwd=KOK)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ozet(cikti, kac=14):
    """Ciktinin HUKUM tasiyan satirlari (gurultu degil)."""
    secili = [s.rstrip() for s in cikti.splitlines()
              if s.strip().startswith("❌") or any(
                  s.strip().startswith(o) or o in s for o in HUKUM_ONEKLERI)]
    return secili[-kac:] if len(secili) > kac else secili


def hukum_izi(cikti):
    return [s.strip() for s in cikti.splitlines()
            if any(s.strip().startswith(o) for o in HUKUM_ONEKLERI)]


def taban_cikar(ref, td):
    """git show <ref>:<yol> ile taban surumleri diske cikarir. (kur, arac) doner."""
    cikti = {}
    for ad in ("yedek-hook-kur.py", "kutu-arsivle.py"):
        r = subprocess.run(["git", "-C", KOK, "show", "%s:tools/%s" % (ref, ad)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None, None, "git show %s:tools/%s -> rc=%d %s" % (
                ref, ad, r.returncode, (r.stderr or "").strip()[:120])
        yol = os.path.join(td, "taban-" + ad)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(r.stdout)
        cikti[ad] = yol
    return cikti["yedek-hook-kur.py"], cikti["kutu-arsivle.py"], None


def eksen_sayilari(yol):
    """Kaynak ekseninde iki sayi: oksuz-govde ekseni var mi, lossless kac kez geciyor."""
    with open(yol, encoding="utf-8", errors="replace") as f:
        metin = f.read().lower()
    return metin.count("oksuz") + metin.count("öksüz"), metin.count("lossless")


def blok_kiyas():
    """5c ekseni: kurucunun BLOK sablonu ile izlenen kancanin blogu BIREBIR mi."""
    if not os.path.isfile(IZLENEN_KANCA):
        return None, "izlenen kanca YOK: %s" % IZLENEN_KANCA
    sys.path.insert(0, TOOLS)
    import importlib.util
    spec = importlib.util.spec_from_file_location("_kur_blok", KUR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with open(IZLENEN_KANCA, encoding="utf-8", errors="replace") as f:
        metin = f.read()
    if mod.BAS not in metin or mod.SON not in metin:
        return False, "izlenen kancada blok isaretleri YOK"
    b = metin.index(mod.BAS)
    s = metin.index(mod.SON) + len(mod.SON)
    return metin[b:s] == mod.BLOK, "kurucu=%d bayt izlenen=%d bayt" % (
        len(mod.BLOK), s - b)


def taban_bataryasi(ref, td):
    """A0 — main'deki kabul bataryasinin KENDISINI oldugu gibi kostur.

    🔴 NEDEN SART: A1-A3 YENI bataryayi ESKI arac uzerinde kosturur; bu, kalemin
    ekseninde tabani verir ama "B1'deki kirmizi benim mi, zaten var miydi" sorusunu
    CEVAPLAMAZ. O soru ancak DOKUNULMAMIS batarya kosularak kapanir
    ([[olcut-civilenirken-taban-olculmeli]]).
    """
    kum = os.path.join(td, "taban-batarya")
    os.makedirs(os.path.join(kum, "kancalar"), exist_ok=True)
    for ad in ("yedek-hook-test.py", "yedek-hook-kur.py", "yedekle.py",
               "git_ortami.py", "kanca-nobeti.py", "icra-suzgeci.py",
               "kutu-arsivle.py", "drive_yolu.py", "kancalar/pre-push"):
        r = subprocess.run(["git", "-C", KOK, "show", "%s:tools/%s" % (ref, ad)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            continue
        with open(os.path.join(kum, ad), "w", encoding="utf-8") as f:
            f.write(r.stdout)
    test = os.path.join(kum, "yedek-hook-test.py")
    if not os.path.isfile(test):
        return None, "taban bataryasi cikarilamadi"
    r = subprocess.run([sys.executable, test], capture_output=True, text=True, cwd=kum)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def yedek_damgasi_tanisi():
    """4d/5b kirmizisinin KOKU: basarili yolda `yedekle.py --gerekliyse` NE yapiyor?"""
    sys.path.insert(0, TOOLS)
    import importlib.util
    spec = importlib.util.spec_from_file_location("_hook_test_ns", HOOK_TEST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as td:
        kok = mod.sahte_repo(td, True)
        d = subprocess.run([sys.executable, os.path.join(kok, "tools", "yedekle.py"),
                            "--gerekliyse"], capture_output=True, text=True, cwd=kok)
        drive = os.path.join(td, "drive", "Pruvo")
        backup = os.path.join(drive, "backup")
        return {
            "rc": d.returncode,
            "son_satirlar": [s.rstrip() for s in (
                (d.stdout or "") + (d.stderr or "")).splitlines()][-12:],
            "drive_icerik": sorted(os.listdir(drive)) if os.path.isdir(drive) else None,
            "backup_icerik": (sorted(os.listdir(backup))[:20]
                              if os.path.isdir(backup) else None),
        }


def bolum_taban(taban_kur, taban_arac):
    y("=" * 78)
    y("A) TABAN — dokunulmamis surumler (git show), AYNI kabul bataryasiyla")
    y("=" * 78)
    rc = {}
    rc["A1 yedek-hook-test --yalniz-tetik  (taban kurucu)"], c = kos(
        sys.executable, HOOK_TEST, "--yalniz-tetik", "--kur", taban_kur)
    for s in ozet(c):
        y("      " + s)
    rc["A2 yedek-hook-test --yalniz-yedek-tani (taban kurucu)"], c = kos(
        sys.executable, HOOK_TEST, "--yalniz-yedek-tani", "--kur", taban_kur)
    for s in ozet(c):
        y("      " + s)
    rc["A3 kutu-arsivle-test (taban arac)"], c = kos(
        sys.executable, KUTU_TEST, "--arac", taban_arac)
    for s in ozet(c):
        y("      " + s)
    rc["A4 taban kutu-arsivle.py --kuru (CANLI kutu)"], c = kos(
        sys.executable, taban_arac, "--kuru")
    for s in ozet(c, 10):
        y("      " + s)
    for ad, deger in rc.items():
        y("  %-52s rc=%s" % (ad, deger))
    o_kur, l_kur = eksen_sayilari(taban_kur)
    o_arac, l_arac = eksen_sayilari(taban_arac)
    y("  A5 kaynak ekseni  taban kutu-arsivle.py : oksuz=%d lossless=%d"
      % (o_arac, l_arac))
    y("  A5 kaynak ekseni  taban yedek-hook-kur.py: oksuz=%d lossless=%d"
      % (o_kur, l_kur))
    with open(taban_kur, encoding="utf-8", errors="replace") as f:
        tk = f.read()
    y("  A6 taban kurucu BLOK'unda `$(true)` (kutu-arsivle HIC cagrilmiyor): %s"
      % ("VAR 🔴" if "pruvo_kutu_cikti=$(true)" in tk else "yok"))
    y("  A7 taban YEDEK cagrisi ciktisini YUTUYOR (>/dev/null 2>&1): %s"
      % ("EVET 🔴" if 'yedekle.py" --gerekliyse >/dev/null 2>&1' in tk else "hayir"))
    return rc


def bolum_sonra(tur):
    y("=" * 78)
    y("B) SONRA — dalin agaci (tur %d)" % tur)
    y("=" * 78)
    izler = []
    rc = {}
    for ad, komut in (
            ("B1 yedek-hook-test (TAM)", [sys.executable, HOOK_TEST]),
            ("B2 kutu-arsivle-test (TAM)", [sys.executable, KUTU_TEST]),
            ("B3 kutu-arsivle.py --kuru (CANLI kutu)", [sys.executable, ARAC, "--kuru"])):
        kod, c = kos(*komut)
        rc[ad] = kod
        izler.extend(hukum_izi(c))
        for s in ozet(c):
            y("      " + s)
    for ad, deger in rc.items():
        y("  %-52s rc=%s" % (ad, deger))
    o_arac, l_arac = eksen_sayilari(ARAC)
    o_kur, l_kur = eksen_sayilari(KUR)
    y("  B5 kaynak ekseni  kutu-arsivle.py  : oksuz=%d lossless=%d" % (o_arac, l_arac))
    y("  B5 kaynak ekseni  yedek-hook-kur.py: oksuz=%d lossless=%d" % (o_kur, l_kur))
    esit, tani = blok_kiyas()
    y("  B6 kurucu BLOK'u ≡ izlenen kanca blogu: %s  (%s)"
      % ({True: "EVET ✅", False: "HAYIR 🔴", None: "OLCULEMEDI"}[esit], tani))
    return rc, izler


def bolum_mutasyon():
    y("=" * 78)
    y("C) MUTASYON — hedef-kol atifli, KOPYA uzerinde (canli dosya DEGISMEZ)")
    y("=" * 78)
    rc = {}
    for ad, komut in (
            ("C1 yedek-hook-test --mutasyon",
             [sys.executable, HOOK_TEST, "--mutasyon"]),
            ("C2 kutu-arsivle-test --mutasyon",
             [sys.executable, KUTU_TEST, "--mutasyon"])):
        kod, c = kos(*komut)
        rc[ad] = kod
        for s in ozet(c, 20):
            y("      " + s)
    for ad, deger in rc.items():
        y("  %-52s rc=%s" % (ad, deger))
    return rc


def bolum_geriye_donuk(pencereler):
    """K5 — bugun tasinan bloklar arsivde OKSUZ GOVDE birakti mi."""
    y("=" * 78)
    y("D) GERIYE DONUK — arsiv KUYRUGUNDA oksuz govde (bugunku 9 blok / 268 satiri kapsar)")
    y("=" * 78)
    rc = {}
    for p in pencereler:
        kod, c = kos(sys.executable, ARAC, "--kuru", "--arsiv-kuyruk", str(p))
        rc["D pencere=%d" % p] = kod
        for s in c.splitlines():
            if "arsiv_kuyruk" in s or "OKSUZ GOVDE" in s or s.startswith("KIRMIZI"):
                y("      " + s.rstrip())
        y("  pencere=%-5d rc=%d" % (p, kod))

    # D2 — CANLI KOL: `--geri-yukle --kuru` gercekten hook BULUYOR mu? (hicbir sey yazmaz)
    # 🔴 Bu, `86e7a035`in kacirdigi kok-adi ayrismasinin CANLI olcumudur: yol yanlisken
    # arac daima "Yedekte hook bulunamadi" der ve rc=1 doner — sessiz degil ama ATIFSIZ.
    y("")
    y("  D2 CANLI — `yedek-hook-kur.py --geri-yukle --kuru` (YAZMAZ, yalniz bulur)")
    for ad, yol in (("TABAN(main)", None), ("SONRA(dal)", KUR)):
        if yol is None:
            continue
        kod, c = kos(sys.executable, yol, "--geri-yukle", "--kuru")
        for s in c.splitlines():
            if s.strip():
                y("      | " + s.rstrip()[:110])
        # 🔴 KAPSAM DURUSTLUGU: bu surucu WORKTREE'den kosuyor. `_ev_hedefi()` yerel evi
        # `dirname(repo)`un KARDESI olarak cozer -> worktree'den bakinca `.../worktrees/
        # pruvo` aranir ve HICBIR EV BULUNAMAZ; rc=1 bundan gelir, yedekten gelmez.
        # Olculen sey su: KAYNAK tarafi (Drive yedegindeki ev klasorleri) BULUNDU MU.
        ev_sayisi = len([s for s in c.splitlines() if "GIT-HOOKS" in s
                         or "YEREL EV YOK" in s])
        y("      %s rc=%d | KAYNAK tarafi: %d ev satiri gorundu "
          "(HEDEF tarafi worktree'den OLCULEMEDI — ev cozumu ana checkout'a gore)"
          % (ad, kod, ev_sayisi))
        rc["D2 %s" % ad] = kod
    return rc


def main():
    ap = argparse.ArgumentParser(description="K308+K310 kabul surucusu")
    ap.add_argument("--cikti", required=True,
                    help="HAM raporun yazilacagi GIT-DISI dosya yolu")
    ap.add_argument("--taban-ref", default="main")
    ap.add_argument("--pencere", default="400,1000",
                    help="arsiv kuyruk pencereleri (virgullu)")
    a = ap.parse_args()

    hedef = os.path.abspath(os.path.expanduser(a.cikti))
    if hedef.startswith(KOK + os.sep):
        print("KIRMIZI: --cikti DEPO ICINI gosteriyor -> ic kosum raporu izlenen agaca "
              "dusemez (yayin durdurur). Git-disi bir yol ver: %s" % hedef)
        return 2

    y("K308 + K310 KABUL SURUCUSU")
    y("depo: %s" % KOK)
    y("taban ref: %s" % a.taban_ref)
    y("")

    with tempfile.TemporaryDirectory() as td:
        taban_kur, taban_arac, hata = taban_cikar(a.taban_ref, td)
        if hata:
            y("🔴 TABAN CIKARILAMADI: %s" % hata)
            taban_rc = None
        else:
            taban_rc = bolum_taban(taban_kur, taban_arac)
        y("")
        y("=" * 78)
        y("A0) TABAN BATARYASI — %s:tools/yedek-hook-test.py OLDUGU GIBI" % a.taban_ref)
        y("=" * 78)
        a0rc, a0c = taban_bataryasi(a.taban_ref, td)
        if a0rc is None:
            y("  OLCULEMEDI: %s" % a0c)
        else:
            for s in (a0c or "").splitlines():
                t = s.strip()
                if t.startswith("❌") or t.startswith("TOPLAM") or t.startswith("SONUC"):
                    y("      " + t)
            y("  A0 taban bataryasi rc=%d" % a0rc)
        y("")
        y("=" * 78)
        y("A8) 4d/5b KOKU — basarili yolda `yedekle.py --gerekliyse` ne yapiyor")
        y("=" * 78)
        try:
            t = yedek_damgasi_tanisi()
            y("  rc=%s" % t["rc"])
            for s in t["son_satirlar"]:
                y("  | " + s)
            y("  drive icerik : %r" % (t["drive_icerik"],))
            y("  backup icerik: %r" % (t["backup_icerik"],))
        except Exception as e:
            y("  OLCULEMEDI: %s: %s" % (type(e).__name__, e))
        y("")
        sonra1, iz1 = bolum_sonra(1)
        y("")
        sonra2, iz2 = bolum_sonra(2)
        y("")
        mut_rc = bolum_mutasyon()
        y("")
        geri_rc = bolum_geriye_donuk(
            [int(x) for x in a.pencere.split(",") if x.strip()])

    y("")
    y("=" * 78)
    y("E) K6 — IKI ARDISIK TURUN HUKUM IZI BIREBIR MI")
    y("=" * 78)
    ayni = iz1 == iz2
    y("  tur1 hukum satiri=%d  tur2=%d  BIREBIR=%s" % (len(iz1), len(iz2),
                                                       "EVET ✅" if ayni else "HAYIR 🔴"))
    if not ayni:
        fark = [s for s in iz1 if s not in iz2][:5] + [s for s in iz2 if s not in iz1][:5]
        for s in fark:
            y("    fark: %s" % s[:110])

    kirmizi = [ad for ad, k in list(sonra1.items()) + list(sonra2.items()) if k != 0]
    kirmizi += [ad for ad, k in mut_rc.items() if k != 0]
    y("")
    y("=" * 78)
    y("HUKUM: SONRA kirmizi=%d · mutasyon kirmizi=%d · K6 birebir=%s"
      % (len([x for x in kirmizi if x.startswith("B")]),
         len([x for x in kirmizi if x.startswith("C")]), ayni))
    for ad in kirmizi:
        y("  ❌ %s" % ad)
    y("SONUC: " + ("YESIL ✅" if (not kirmizi and ayni) else "KIRMIZI 🔴"))
    y("(taban rc'leri A bolumunde; taban KIRMIZI olmasi BEKLENIR — kalem oradan aciliyor)")

    with open(hedef, "w", encoding="utf-8") as f:
        f.write("\n".join(SATIRLAR) + "\n")
    print("\nHAM RAPOR -> %s" % hedef)
    del taban_rc, geri_rc
    return 0 if (not kirmizi and ayni) else 1


if __name__ == "__main__":
    sys.exit(main())
