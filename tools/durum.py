#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO DURUM PANOSU — oturumlar-arasi gorunurluk. SALT-OKUNUR.

    python3 tools/durum.py

Uygulamanin /tasks + /workflows ekranlari OTURUMA OZELDIR: baska oturumun isini
gostermez. Bu arac o bosluğu kapatir — "hangi is bitmis, hangisi devam ediyor"
sorusunu repo'nun kendi gercekliginden (worktree + dal + DEVAM.md) cevaplar.

KAPSAM = SADECE GORUNURLUK. Is baslatmaz, dal silmez, DOSYA YAZMAZ. Sadece okuyan
git komutlari calistirir; onerdigi silme komutunu EKRANA yazar, kendisi CALISTIRMAZ.
Karari mimar/Okan verir.

"MERGED" TUZAGI (bu aracin asil teknik riski):
  `git branch --merged` YETMEZ. Squash-merge / cherry-pick / rebase edilmis bir dalin
  ucu main'in atasi DEGILDIR — `--merged` onu "bitmemis" sanir, arac da yanlis rapor
  verir (hafiza: worktree-yol-hatasi, "merged gorunumu tuzak").
  Bu yuzden iki durum AYRI siniflanir ve ucu-degil-icerigi olculur:
    ucu-main-de    : merge-base --is-ancestor  (dalin ucu main'in atasi)
    icerigi-main-de: merge-tree --write-tree   (dali main'e katmak main'in agacini
                     DEGISTIRMIYOR => icerik zaten main'de; squash/cherry-pick/rebase
                     dahil yakalar. Tek tek patch-id (`git cherry`) COK-COMMITLI
                     squash'ta kacirir: 3 commit tek commit'e ezilince patch-id'ler
                     tutmaz. Kabul testi madde 2 tam bunu kanitlar.)
    devam          : main'de olmayan icerigi var

Repo yolu sabit yazili DEGIL: betik kendi konumundan repo kokunu bulur.
Harici bagimlilik yok — saf stdlib + git.
"""
import glob
import json
import os
import subprocess
import sys
import time

ANA_DAL = "main"


def git(repo, *args):
    """Salt-okunur git cagrisi. (cikti, cikis_kodu) doner; hata basmaz."""
    p = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True)
    return p.stdout.strip(), p.returncode


def repo_koku():
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cikti, kod = git(kok, "rev-parse", "--show-toplevel")
    return cikti if kod == 0 and cikti else kok


def ana_repo(repo):
    """Asil calisma agaci (worktree degil) — .git ortak dizininin ustu."""
    cikti, kod = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if kod != 0 or not cikti:
        return repo
    return os.path.dirname(cikti.rstrip("/"))


# ---------------------------------------------------------------- worktree'ler

def worktreeler(repo):
    cikti, kod = git(repo, "worktree", "list", "--porcelain")
    if kod != 0:
        return []
    liste = []
    kayit = {}
    for satir in cikti.splitlines() + [""]:
        if not satir.strip():
            if kayit:
                liste.append(kayit)
                kayit = {}
            continue
        parca = satir.split(" ", 1)
        anahtar = parca[0]
        deger = parca[1] if len(parca) > 1 else True
        if anahtar == "worktree":
            kayit = {"yol": deger, "dal": None, "kilitli": False}
        elif anahtar == "branch":
            kayit["dal"] = deger.replace("refs/heads/", "")
        elif anahtar == "detached":
            kayit["dal"] = "(detached)"
        elif anahtar == "locked":
            kayit["kilitli"] = True
    return liste


def rapor_bilgisi(worktree_yolu):
    yol = os.path.join(worktree_yolu, "RAPOR-MIMARA.md")
    if not os.path.isfile(yol):
        return None
    baslik = ""
    try:
        with open(yol, "r", errors="replace") as f:
            for satir in f:
                if satir.startswith("#"):
                    baslik = satir.lstrip("# ").strip()
                    break
    except OSError:
        return None
    return {"mtime": os.path.getmtime(yol), "baslik": baslik}


# ------------------------------------------------------------------- dal siniflama

def dal_sinifi(repo, dal, ana=ANA_DAL):
    """Dali uc siniftan birine koyar: ucu-main-de / icerigi-main-de / devam.

    `git branch --merged` BILEREK KULLANILMIYOR: squash-merge'i kaciriyor
    (kabul testi 2b bunu her kosuda yeniden kanitlar). Sira:
      1) merge-base --is-ancestor -> dalin ucu main'in atasi mi?
      2) merge-tree --write-tree  -> dali main'e katmak main'in AGACINI
         degistiriyor mu? Degistirmiyorsa icerik zaten main'de.
      3) `git cherry` (patch-id) -> merge-tree yoksa (eski git) yedek yol;
         cok-commitli squash'i kacirir, o yuzden sadece yedek.
    """
    _, kod = git(repo, "merge-base", "--is-ancestor", dal, ana)
    if kod == 0:
        return "ucu-main-de"

    ana_agac, kod_a = git(repo, "rev-parse", "%s^{tree}" % ana)
    cikti, kod_m = git(repo, "merge-tree", "--write-tree", ana, dal)
    if kod_a == 0 and kod_m == 0 and cikti:
        # kod_m == 0: catismasiz birlesme. Ilk satir = sonuc agacinin oid'i.
        if cikti.splitlines()[0].strip() == ana_agac:
            return "icerigi-main-de"
        return "devam"
    if kod_m == 1:
        # catisma var => dal main'de olmayan icerik tasiyor
        return "devam"

    # yedek yol: merge-tree desteklenmiyor
    cikti, kod = git(repo, "cherry", ana, dal)
    if kod == 0 and cikti:
        if not [s for s in cikti.splitlines() if s.startswith("+")]:
            return "icerigi-main-de"
    return "devam"


def dal_bilgisi(repo, dal, ana=ANA_DAL):
    ozet, _ = git(repo, "log", "-1", "--format=%cr|%h|%s", dal)
    parcalar = ozet.split("|", 2)
    ileri, _ = git(repo, "rev-list", "--count", "%s..%s" % (ana, dal))
    return {
        "dal": dal,
        "ne_zaman": parcalar[0] if parcalar else "?",
        "sha": parcalar[1] if len(parcalar) > 1 else "?",
        "konu": parcalar[2] if len(parcalar) > 2 else "",
        "ileri": ileri or "0",
        "sinif": dal_sinifi(repo, dal, ana),
    }


def yerel_dallar(repo):
    cikti, kod = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    return cikti.splitlines() if kod == 0 else []


# ------------------------------------------------------------------- DEVAM.md

def devam_ozeti(repo, en_fazla=8):
    yol = os.path.join(ana_repo(repo), "DEVAM.md")
    if not os.path.isfile(yol):
        return None
    basliklar = []
    try:
        with open(yol, "r", errors="replace") as f:
            for satir in f:
                # SADECE ust duzey baslik — 70 KB'lik dosyanin ICERIGI DOKULMEZ.
                if satir.startswith("# "):
                    basliklar.append(satir[2:].strip())
                    if len(basliklar) >= en_fazla:
                        break
    except OSError:
        return None
    return {"mtime": os.path.getmtime(yol), "basliklar": basliklar,
            "boyut": os.path.getsize(yol)}


# ------------------------------------------------------------------- oturumlar

def _proje_dizin_adi(yol):
    """Claude Code kodlamasi: yoldaki '/' ve '.' -> '-'."""
    return yol.replace("/", "-").replace(".", "-")


def oturumlar(repo, en_fazla=10, gun=3):
    """Oturum transkript dosyalarindan SADECE ust veri: cwd + dal + son aktivite.

    MESAJ ICERIGI OKUNMAZ/BASILMAZ (transkriptte musteri/is verisi olabilir).
    Format belgelenmemis ic formattir -> alanlar .get() ile okunur, yoksa '?'
    yazilir, betik ASLA patlamaz.
    'Kosuyor mu' diske YAZILMIYOR (olculdu: lsof'ta acik dosya tutulmuyor, surec
    komut satirinda oturum kimligi yok) -> sadece SON AKTIVITE raporlanir.
    """
    kok = os.path.expanduser("~/.claude/projects")
    if not os.path.isdir(kok):
        return []
    desen = os.path.join(kok, _proje_dizin_adi(ana_repo(repo)) + "*")
    simdi = time.time()
    bulunan = []
    for dizin in glob.glob(desen):
        for dosya in glob.glob(os.path.join(dizin, "*.jsonl")):
            try:
                mtime = os.path.getmtime(dosya)
            except OSError:
                continue
            if simdi - mtime > gun * 86400:
                continue
            bulunan.append((mtime, dosya))
    bulunan.sort(reverse=True)
    liste = []
    for mtime, dosya in bulunan[:en_fazla]:
        cwd, dal = None, None
        try:
            with open(dosya, "r", errors="replace") as f:
                for sira, satir in enumerate(f):
                    if sira > 60 or (cwd and dal):
                        break
                    try:
                        kayit = json.loads(satir)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(kayit, dict):
                        cwd = cwd or kayit.get("cwd")
                        dal = dal or kayit.get("gitBranch")
        except OSError:
            continue
        liste.append({
            "kimlik": os.path.basename(dosya)[:8],
            "cwd": cwd or "?",
            "dal": dal or "?",
            "mtime": mtime,
        })
    return liste


# ------------------------------------------------------------------- basim

def _gecen(mtime):
    fark = time.time() - mtime
    if fark < 90:
        return "az once"
    if fark < 5400:
        return "%d dk once" % (fark // 60)
    if fark < 172800:
        return "%d saat once" % (fark // 3600)
    return "%d gun once" % (fark // 86400)


SINIF_ETIKET = {
    "ucu-main-de": "ucu main'de",
    "icerigi-main-de": "icerigi main'de (squash/cherry-pick/rebase)",
    "devam": "DEVAM EDIYOR",
}


# ------------------------------------------------------------------- EDGE_KATALOG esigi
# Kaynak: tools/edge-katalog-tetik.md (mimar karari, 20 Tem 2026).
# B-HAZIRLIK 10k / A-BIRINCIL TETIK (flip) 12k / C-MECBURI SON TARIH 14k.
# Ag cagrisi YOK (mimar karari: panoya ag eklenmez, urunler.json yerelden sayilir).

EDGE_HAZIRLIK = 10000
EDGE_FLIP = 12000
EDGE_MECBURI = 14000
EDGE_GUNLUK_BUYUME = 245  # edge-katalog-tetik.md: "karali buyume ~245 urun/gun"


def urunler_sayisi(yol):
    """urunler.json'daki BENZERSIZ id sayisi. Dosyayi BAGLAMA basmaz/dokmez,
    sadece sayar. Bozuk/eksik dosyada None doner (betik ASLA patlamaz)."""
    if not os.path.isfile(yol):
        return None
    try:
        with open(yol, "r", errors="replace") as f:
            veri = json.load(f)
    except (ValueError, OSError):
        return None
    if not isinstance(veri, list):
        return None
    idler = set()
    for urun in veri:
        if isinstance(urun, dict) and "id" in urun:
            idler.add(urun["id"])
    return len(idler)


def edge_esigi(sayi, hazirlik=None, flip=None, mecburi=None, gunluk=None):
    """Sabit esiklere gore siniflama -- saf fonksiyon (girdi->cikti).

    hazirlik/flip/mecburi/gunluk parametreleri None ise modul sabitleri CALISMA
    ANINDA okunur (varsayilan-degeri def anina SABITLEMEZ) -- boylece testler
    `durum.EDGE_HAZIRLIK` gibi sabitleri gecici olarak degistirip (mutasyon)
    bu fonksiyonun gercekten o sabiti kullandigini kanitlayabilir.
    """
    if hazirlik is None:
        hazirlik = EDGE_HAZIRLIK
    if flip is None:
        flip = EDGE_FLIP
    if mecburi is None:
        mecburi = EDGE_MECBURI
    if gunluk is None:
        gunluk = EDGE_GUNLUK_BUYUME

    kalan_hazirlik = hazirlik - sayi
    tahmin_gun = None
    if gunluk and gunluk > 0:
        tahmin_gun = -(-max(0, kalan_hazirlik) // gunluk)  # tavana yuvarla (tamsayi)

    return {
        "urun": sayi,
        "hazirlik": {"esik": hazirlik, "kalan": kalan_hazirlik, "asildi": sayi >= hazirlik},
        "flip": {"esik": flip, "kalan": flip - sayi, "asildi": sayi >= flip},
        "mecburi": {"esik": mecburi, "kalan": mecburi - sayi, "asildi": sayi >= mecburi},
        "gunluk_buyume": gunluk,
        "tahmini_gun_hazirlik": tahmin_gun,
    }


def edge_satirlari(e):
    """basim icin metin satirlari uretir (kabul testi de dogrudan bunu okur)."""
    def isaret(anahtar):
        return "⚠ " if e[anahtar]["asildi"] else ""

    satirlar = [
        "  urun: %d | %shazirlik %d'e kalan: %d | %sflip %d | %smecburi %d"
        % (e["urun"],
           isaret("hazirlik"), e["hazirlik"]["esik"], e["hazirlik"]["kalan"],
           isaret("flip"), e["flip"]["esik"],
           isaret("mecburi"), e["mecburi"]["esik"])
    ]
    if e["tahmini_gun_hazirlik"] is not None and not e["hazirlik"]["asildi"]:
        satirlar.append(
            "  tahmin: karali ~%d urun/gun buyume varsayimiyla hazirliga (%d) kalan gun: %d"
            % (e["gunluk_buyume"], e["hazirlik"]["esik"], e["tahmini_gun_hazirlik"]))
    else:
        satirlar.append(
            "  tahmin: hazirlik esigi (%d) zaten gecildi -- buyume tahmini gecersiz"
            % e["hazirlik"]["esik"])
    return satirlar


def main():
    repo = repo_koku()
    kok = ana_repo(repo)
    print("=" * 72)
    print("PRUVO DURUM PANOSU — %s" % time.strftime("%Y-%m-%d %H:%M"))
    print("repo: %s   (salt-okunur: hicbir sey yazilmaz/silinmez)" % kok)
    print("=" * 72)

    wt = worktreeler(repo)
    wt_dallari = set(w["dal"] for w in wt if w["dal"])

    print("\n1) AKTIF WORKTREE'LER (%d)" % len(wt))
    for w in wt:
        ozet, _ = git(w["yol"], "log", "-1", "--format=%cr — %h %s")
        kirli, _ = git(w["yol"], "status", "--porcelain")
        print("  • %s" % w["yol"])
        print("      dal: %s%s | son commit: %s"
              % (w["dal"], "  [kilitli]" if w["kilitli"] else "", ozet or "?"))
        if kirli:
            print("      ⚠ calisma agaci KIRLI (%d dosya) — sahibi calisiyor olabilir, dokunma"
                  % len(kirli.splitlines()))
        rapor = rapor_bilgisi(w["yol"])
        if rapor:
            print("      RAPOR-MIMARA.md: %s — %s"
                  % (_gecen(rapor["mtime"]), rapor["baslik"][:60]))

    dallar = [d for d in yerel_dallar(repo) if d != ANA_DAL]
    print("\n2) DALLAR (%d, main haric)" % len(dallar))
    bilgiler = []
    for d in dallar:
        b = dal_bilgisi(repo, d)
        bilgiler.append(b)
        isaret = "✔" if b["sinif"] != "devam" else "→"
        print("  %s %s" % (isaret, b["dal"]))
        print("      %s | %s ileri | %s" % (b["ne_zaman"], b["ileri"], SINIF_ETIKET[b["sinif"]]))
        print("      son: %s %s" % (b["sha"], b["konu"][:56]))

    artik = [b for b in bilgiler
             if b["sinif"] != "devam" and b["dal"] not in wt_dallari]
    print("\n3) ARTIK DALLAR (%d) — worktree'si yok + icerigi main'de" % len(artik))
    if not artik:
        print("  (yok)")
    for b in artik:
        print("  • %s — %s" % (b["dal"], SINIF_ETIKET[b["sinif"]]))
    if artik:
        print("\n  Temizleme komutu (arac CALISTIRMAZ — karar mimar/Okan'in):")
        print("    git -C %s branch -D %s" % (kok, " ".join(b["dal"] for b in artik)))

    devam = devam_ozeti(repo)
    print("\n4) DEVAM.md")
    if not devam:
        print("  (bulunamadi)")
    else:
        print("  guncelleme: %s | %d KB — icerik DOKULMEZ, sadece basliklar:"
              % (_gecen(devam["mtime"]), devam["boyut"] // 1024))
        for b in devam["basliklar"]:
            print("    - %s" % b[:66])

    otr = oturumlar(repo)
    print("\n5) OTURUMLAR (son 3 gun, en fazla 10) — SON AKTIVITE")
    print("   not: 'kosuyor mu' diske yazilmiyor; asagidaki sadece son yazma zamanidir.")
    if not otr:
        print("  (kayit yok)")
    for o in otr:
        yer = o["cwd"].replace(kok, ".") if o["cwd"] != "?" else "?"
        print("  • %s… | dal: %s | %s" % (o["kimlik"], o["dal"], _gecen(o["mtime"])))
        print("      %s" % yer)

    urun_yolu = os.path.join(kok, "urunler.json")
    sayi = urunler_sayisi(urun_yolu)
    print("\n6) EDGE_KATALOG ESIGI")
    if sayi is None:
        print("  urunler.json okunamadi/bulunamadi: %s" % urun_yolu)
    else:
        for satir in edge_satirlari(edge_esigi(sayi)):
            print(satir)
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
