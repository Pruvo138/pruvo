#!/usr/bin/env python3
"""WORKTREE KAPI BAYATLIK KAPISI  (K80/K250 icra kolu, 10 Eyl 2026)

NE OLCER
--------
Bir worktree'de kosan makine kapilarinin, evin ANA checkout'undaki CANLI
kapilarla ayni olup olmadigini. Iki eksen:

  EKSEN-A (govde bayatligi): kancaya BAGLI her kapi dosyasinin worktree'de
    cozulen govdesi, ana checkout'ta cozulen govdesiyle bayt-ozdes mi?
  EKSEN-B (baglanti dusmesi): worktree'nin settings.json'indan cikan BAGLI
    kapi adlari kumesi, ana checkout'unkiyle ayni mi? Dusen kapi HIC kosmaz
    — bu, bayat govdeden STRIKTLY daha kotudur.

NEDEN VAR (K250 hukmu, 20 Agu — d76ca45c)
-----------------------------------------
Bu ariza sinifi bir kez zaten kapatilmisti: kural evin IZLENEN kapi dosyasina
yazilir, skip-worktree KALDIRILIR, ev mimari commit'ler; boylece HEAD kurali
tasir ve her taze agac kapiyi HAZIR alir. K250'nin ICRA araclari
(tools/mimar-kapi-kur.py, tools/isci-sablon-kapisi.py) 29 Agu supurmesinde
SILINDI (ca8c3815, "48 kapi silindi"). Hukum tarihte kaldi, ZORLAYICI kalmadi
-- ve ariza geri geldi. Bu kol o icrayi geri getirir.
[[hukum-yazmak-icra-degildir]] · [[kapi-supurmesi-29agu]]

MEKANIZMA (10 Eyl'de olculdu, TeKiN'in teshisi DOGRULANDI ve GENISLETILDI)
--------------------------------------------------------------------------
1. Kanca komutundaki ${CLAUDE_PROJECT_DIR} bir cip agacinda WORKTREE kokune
   cozulur; kanca o agactaki govdeyi kosturur.
2. Harness, ignore edilen .claude/ dizinini worktree DOGARKEN kopyalar. Bu bir
   DOGUM ANLIK GORUNTUSUDUR: dogumdan sonra ana checkout'ta degisen kablolama
   yasayan agaclara ULASMAZ.
3. Bir yol hem IZLENIYOR hem skip-worktree ise, canli govde YALNIZ ana
   checkout'un DISKINDE yasar; HEAD ondan ayrisir. Taze worktree kendi
   index'ini alir (bayrak GELMEZ) ve git, harness kopyasinin UZERINE HEAD'deki
   BAYAT govdeyi yazar. Belirleyici olan tek basina skip-worktree degil,
   "izlenen + skipli yol" ile harness kopyasinin CARPISMASIDIR.

Bu kol HICBIR SEY YAZMAZ; salt okur ve sayi basar. Fail-closed: olculemeyen
her agac KIRMIZI yanar, sessizce 0 sayilmaz.
[[izin-tablosu-duymadigini-kirmizi-yakmali]] · [[fail-closed-kol-arkasindaki-kolu-maskeler]]
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Kanca komutundan .py yollarini cikaran desen.
PY_DESEN = re.compile(r'[^\s"\';|&]*\.py')

# Bilinen ev kokleri (--tum-evler icin). Yoksa sessizce atlanir, HAL basilir.
# EV-GORELI COZUMLEME (K250 grameri, d76ca45c): makineye cakili mutlak yol
# hem baska makinede YANLIS olur hem PUBLIC depoda kullanici adi tasir.
# expanduser cozemezse '~' oneki oldugu gibi kalir, dizin bulunamaz ve ev
# "EV-DIZINI-YOK" olarak RAPORLANIR (fail-closed yon: sessizce atlanmaz).
EVLER = [
    ("KraL/pruvo", os.path.expanduser("~/dev/pruvo")),
    ("ArTisT/pazarlama", os.path.expanduser("~/dev/pruvo-pazarlama")),
    ("HocA/bot", os.path.expanduser("~/dev/pruvo-bot")),
    ("MaCiT/hasat", os.path.expanduser("~/dev/pruvo-hasat")),
    ("TeKiN/jenerator", os.path.expanduser("~/dev/pruvo-jenerator")),
]


# ---------------------------------------------------------------- yardimcilar
def ev_kokunu_bul(baslangic):
    """Bir worktree icinden bile EVIN ANA kokunu verir.

    git-common-dir daima ANA deponun .git'ini gosterir (worktree'nin kendi
    git-dir'ini DEGIL); ebeveyni ev kokudur. ${CLAUDE_PROJECT_DIR}'in aksine
    bu deger worktree'den worktree'ye DEGISMEZ -- capa olarak dogru olan budur.
    """
    r = subprocess.run(["git", "-C", baslangic, "rev-parse", "--git-common-dir"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    ortak = r.stdout.strip()
    if not ortak:
        return None
    if not os.path.isabs(ortak):
        ortak = os.path.join(baslangic, ortak)
    return os.path.realpath(os.path.dirname(ortak))


def worktreeler(kok):
    """[(yol, ana_mi)] ya da (None, HAL)."""
    r = subprocess.run(["git", "-C", kok, "worktree", "list", "--porcelain"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, "GIT-RC=%d" % r.returncode
    yollar = [s[len("worktree "):].strip()
              for s in r.stdout.splitlines() if s.startswith("worktree ")]
    if not yollar:
        return None, "WORKTREE-YOK"
    return [(y, i == 0) for i, y in enumerate(yollar)], None


def skipli_yollar(kok):
    """skip-worktree bayrakli izlenen yollar (teshis ciktisi icin)."""
    r = subprocess.run(["git", "-C", kok, "ls-files", "-v"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [s[2:].strip() for s in r.stdout.splitlines() if s.startswith("S ")]


def kanca_kapilari(settings_yolu):
    """settings.json -> ({kapi_adi: [(ham_yol, capa)]}, None) | (None, HAL).

    UC HAL ayri dondurulur; 'dosya yok' ile 'hook yok' ayni kovaya DUSMEZ.
    """
    if not os.path.exists(settings_yolu):
        return None, "SETTINGS-YOK"
    try:
        with open(settings_yolu, encoding="utf-8") as f:
            veri = json.load(f)
    except Exception as e:
        return None, "SETTINGS-BOZUK:%s" % type(e).__name__
    if not isinstance(veri, dict):
        return None, "SETTINGS-DICT-DEGIL"
    hooks = veri.get("hooks")
    if hooks is None:
        return {}, None          # hook blogu yok: mesru bos kume
    if not isinstance(hooks, dict):
        return None, "HOOKS-DICT-DEGIL"

    bulunan = {}
    for _olay, gruplar in hooks.items():
        if not isinstance(gruplar, list):
            continue
        for grup in gruplar:
            if not isinstance(grup, dict):
                continue
            for kanca in grup.get("hooks", []) or []:
                if not isinstance(kanca, dict):
                    continue
                komut = kanca.get("command")
                if not isinstance(komut, str):
                    continue
                for ham in PY_DESEN.findall(komut):
                    ham = ham.strip("\"'")
                    if not ham.endswith(".py"):
                        continue
                    capa = ("RELATIF"
                            if ("CLAUDE_PROJECT_DIR" in ham or not ham.startswith("/"))
                            else "SABIT")
                    bulunan.setdefault(os.path.basename(ham), []).append((ham, capa))
    return bulunan, None


def coz(ham_yol, kok):
    """Ham kanca yolunu, kok'te calisirken isaret edecegi dosyaya cevir."""
    y = ham_yol
    for kalip in ("${CLAUDE_PROJECT_DIR:-.}", "${CLAUDE_PROJECT_DIR}",
                  "$CLAUDE_PROJECT_DIR"):
        y = y.replace(kalip, kok)
    if not y.startswith("/"):
        y = os.path.join(kok, y)
    return os.path.normpath(y)


def sha(yol):
    """Dosyanin ham baytlarinin sha1'i; yoksa None. Bayt DEGIL SHA karsilastirilir
    -- ayni boyutta farkli govde [[lossless-beyani-blok-butunlugu-olcmez]]."""
    import hashlib
    try:
        with open(yol, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


# -------------------------------------------------------------------- olcum
def evi_olc(ev_adi, kok, ayrinti=True):
    """(eksen_a, eksen_b, olculemedi, satirlar)"""
    satirlar = []
    wtler, hal = worktreeler(kok)
    if wtler is None:
        satirlar.append("%-18s HAL=%s  (OLCULEMEDI)" % (ev_adi, hal))
        return 0, 0, 1, satirlar

    ana_yol = wtler[0][0]
    ana_kapilar, ana_hal = kanca_kapilari(
        os.path.join(ana_yol, ".claude", "settings.json"))
    if ana_kapilar is None:
        satirlar.append("%-18s ANA-SETTINGS HAL=%s  (OLCULEMEDI)" % (ev_adi, ana_hal))
        return 0, 0, 1, satirlar

    ana_kume = set(ana_kapilar)
    cocuklar = [w for w, ana_mi in wtler if not ana_mi]
    satirlar.append("### %s  agac=%d  ana-bagli-kapi=%d"
                    % (ev_adi, len(cocuklar), len(ana_kume)))
    if ayrinti:
        skipli = [p for p in skipli_yollar(kok) if p.endswith((".py", ".json"))]
        if skipli:
            satirlar.append("    skip-worktree (ariza ETKENI): %s" % ", ".join(skipli))

    a_top = b_top = olculemedi = 0
    for wt in cocuklar:
        kisa = os.path.basename(wt)
        wt_kapilar, wt_hal = kanca_kapilari(
            os.path.join(wt, ".claude", "settings.json"))
        if wt_kapilar is None:
            # Kablolama HIC okunamiyor: TUM ana kapilar dusmus sayilir. Bu bir
            # OLCULEMEDI degil, olculmus bir KAYIPTIR -- ama ayrica isaretlenir.
            b_top += len(ana_kume)
            olculemedi += 1
            satirlar.append("    %-30s EKSEN-B=%-2d HAL=%s  DUSEN=%s"
                            % (kisa[:29], len(ana_kume), wt_hal,
                               ",".join(sorted(ana_kume)) or "-"))
            continue

        wt_kume = set(wt_kapilar)
        dusen = ana_kume - wt_kume
        fazla = wt_kume - ana_kume
        b = len(dusen) + len(fazla)

        # EKSEN-A: BAGLI her cagri yerini ayri say [[kapinin-menzili-cagri-yeridir]]
        sapmalar = []
        for ad, kayitlar in sorted(wt_kapilar.items()):
            for ham, capa in kayitlar:
                s_wt = sha(coz(ham, wt))
                s_ana = sha(coz(ham, ana_yol))
                if s_wt != s_ana:
                    sapmalar.append("%s[%s] wt=%s ana=%s"
                                    % (ad, capa,
                                       "YOK" if s_wt is None else s_wt[:8],
                                       "YOK" if s_ana is None else s_ana[:8]))
        a_top += len(sapmalar)
        b_top += b
        if b or sapmalar:
            satirlar.append("    %-30s EKSEN-A=%-2d EKSEN-B=%-2d %s%s"
                            % (kisa[:29], len(sapmalar), b,
                               ("DUSEN=" + ",".join(sorted(dusen)) + " ") if dusen else "",
                               ("FAZLA=" + ",".join(sorted(fazla)) + " ") if fazla else ""))
            for s in sapmalar:
                satirlar.append("        BAYAT %s" % s)
        elif ayrinti:
            satirlar.append("    %-30s EKSEN-A=0  EKSEN-B=0  TEMIZ" % kisa[:29])

    return a_top, b_top, olculemedi, satirlar


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ev", help="olculecek ev koku (varsayilan: bu agacin evi)")
    ap.add_argument("--tum-evler", action="store_true", help="bes evi birden olc")
    ap.add_argument("--sessiz", action="store_true", help="yalniz ozet")
    a = ap.parse_args(argv)

    if a.tum_evler:
        hedefler = [(ad, k) for ad, k in EVLER if os.path.isdir(k)]
        eksik = [ad for ad, k in EVLER if not os.path.isdir(k)]
    else:
        kok = a.ev or ev_kokunu_bul(os.getcwd())
        if kok is None:
            print("HAL=EV-KOKU-COZULEMEDI")
            print("EKSEN-A_SAPAN=0")
            print("EKSEN-B_FARK=0")
            print("OLCULEMEDI=1")
            return 1
        hedefler = [(os.path.basename(kok), kok)]
        eksik = []

    a_top = b_top = olculemedi = 0
    for ad, kok in hedefler:
        ea, eb, om, satirlar = evi_olc(ad, kok, ayrinti=not a.sessiz)
        a_top += ea
        b_top += eb
        olculemedi += om
        if not a.sessiz:
            print("\n".join(satirlar))
            print()
    for ad in eksik:
        print("%-18s HAL=EV-DIZINI-YOK (atlandi)" % ad)

    # Ozet HER ZAMAN basilir; erken return ile kisa devre YAPILMAZ.
    print("=" * 62)
    print("EKSEN-A_SAPAN=%d" % a_top)
    print("EKSEN-B_FARK=%d" % b_top)
    print("OLCULEMEDI=%d" % olculemedi)
    kirmizi = (a_top > 0) or (b_top > 0) or (olculemedi > 0)
    print("HAL=%s" % ("BAYAT" if kirmizi else "TEMIZ"))
    print("=" * 62)
    if kirmizi:
        print("CARE: kapi GOVDESI bayatsa K250 hukmu -- govde evin IZLENEN")
        print("      dosyasina yazilir, skip-worktree KALDIRILIR, ev mimari")
        print("      commit'ler. KABLOLAMA (settings.json hooks) commit EDILMEZ;")
        print("      onun caresi capayi worktree'den bagimsizlastirmaktir")
        print("      (git rev-parse --git-common-dir turevi ev koku).")
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
