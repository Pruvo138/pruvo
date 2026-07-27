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
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time

ANA_DAL = "main"


def git(repo, *args):
    """Salt-okunur git cagrisi. (cikti, cikis_kodu) doner; hata basmaz.

    🔴 `git` BINARY'SI YOKKEN COKMEZ (8. tur olcumu, 27 Tem): eskiden yakalanmamis
    FileNotFoundError firlatiyordu -> panonun KENDISI cokuyor, panoyu ucdan uca kosan
    BLOKLAYICI CI adimi kirmiziya donuyor ve `deploy: needs: build` zinciriyle TUM
    yayin duruyordu. Bu, `ps` ekseninde daha once yasanan arizanin AYNISI (dis binary
    yoklugu = ORTAM EKSIKLIGI, ariza degil). Cagiranlarin hepsi zaten `kod != 0`
    yolunu tasiyor (repo_koku/ana_repo/worktreeler fallback'li) -> git yoksa
    "calistirilamadi" cikis kodu donerek ayni yola girilir.
    ⚠️ git VARKEN davranis DEGISMEZ: subprocess.run istisna atmaz, ayni (cikti, rc)."""
    try:
        p = subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, text=True)
    except OSError:
        return "", 127                    # `git` yok/calistirilamadi (sh emsali: 127)
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


# ------------------------------------------------------------------- YEDEK TAZELIGI
# Kaynak: tools/yedekle.py -> Drive'daki backup/.son-yedek.json damgasi.
#
# NEDEN VAR (26 Tem olcumu): yedekle.py DOGRU calisiyordu ama ELLE cagriliyordu; 5 gun
# kosulmadi, mutasyon-kanitli skill dosyalari yedekte bayat kaldi ve HICBIR SEY bunu
# gostermiyordu. Sessizce durmus yedek = yedek yok. Gorunurluk otomasyondan ONCE gelir.
#
# NEDEN DAMGA, NEDEN MTIME DEGIL: yedekle.py shutil.copy2 kullanir -> KAYNAK mtime'ini
# korur. Yedekteki dosyanin mtime'i "yedek ne zaman kosuldu"yu degil "kaynak ne zaman
# duzenlendi"yi soyler; tazeligi ondan olcmek YANILTIR (Drive'daki dosyalar 21 Tem
# gorunuyordu cunku kaynak o tarihliydi).
#
# ⚠️ SALT-OKUNUR SOZLESMESI: drive_yolu.stl_dizini() BILEREK cagrilmaz — o fonksiyon
# bayat .stl-backup-dir'i DUZELTIR, yani DOSYA YAZAR. Pano yazmaz (modul basligindaki
# sozlesme). Burada yalniz drive_yolu.DESEN sabiti (tek kaynak) okunur, cozum yerelde
# ve salt-okunur yapilir.

YEDEK_DAMGA_ADI = ".son-yedek.json"
# ATLAMA KAYDI ayri dosyada: damgayi yalniz kilidi tutan kosum yazar, atlamayi ise
# kilidi ALAMAYAN kosum -> ayni dosyada oku-degistir-yaz birbirini eziyordu (olculdu:
# 20 paralel ciftin 2'sinde yanlis ⚠⚠). Pano ikisini BIRLESTIREREK okur; eski
# surumlerde alanlar damganin ICINDE olabilir, o yuzden birlestirmede AYRI DOSYA
# onceliklidir (daha yeni kayit odur).
YEDEK_ATLAMA_ADI = ".son-yedek-atlama.json"
YEDEK_BAYAT_SANIYE = 2 * 86400   # ~2 gun. TEK YER — esigi baska yere serpistirme.
YEDEK_ZAMAN_ASIMI = 5.0          # saniye. Olculen normal sure: 0,0005 s.

# YEDEK KILIDI (tools/yedekle.py `.yedek.lock`) — panonun IKINCI kanali.
# NEDEN VAR: atlanan yedek push aninda %100 SESSIZDIR (pre-push blogu stdout+stderr'i
# /dev/null'a yutar ve atlama exit 0 oldugu icin "YEDEK alinamadi" da basilmaz).
# Kilit saatlerdir asili olsa bile kullanicinin gorecegi TEK yer burasi.
# ⚠️ Pano kilidi ALMAYA CALISMAZ: bir an icin almak, o sirada kosan GERCEK bir yedegi
# atlatirdi. Yalnizca dosya icerigi okunur + pid CANLILIGI sorulur (sinyal 0 = yalniz
# varlik sorusu, surece hicbir sey gondermez). Dosya yerel diskte -> Drive gibi asilmaz.
YEDEK_KILIT_ADI = ".yedek.lock"
YEDEK_KILIT_ASILI = 3600.0       # sn — yedekle.KILIT_UYARI_YASI ile AYNI (test esitler)

# N3 — PANO ASLA ASILMAZ. Bolum 7 bir AG/BULUT mount'una (CloudStorage) dokunuyor;
# mount yanit vermezse glob/isdir/os.walk KILITLENIR ve `durum.py` asilir. Bu arac her
# oturumun ILK komutu -> asilirsa mimarin butun acilisi bloklanir. Cozum: olcumu ayri
# bir DAEMON is parcaciginda kos, sureyi asarsa PARCACIGI TERK ET ve panoya devam et.
# Neden signal.alarm DEGIL: SIGALRM yalniz ana is parcaciginda kurulabilir ve asili
# bir mount'ta kesintisiz (uninterruptible) sistem cagrisini kesmeyebilir; daemon
# parcacik asilsa bile yorumlayici cikisini engellemez.


def zaman_asimiyla(fonk, saniye=None):
    """fonk()'u zaman siniriyla kosar. Doner: (sonuc, asildi_mi).

    saniye None ise modul sabiti CALISMA ANINDA okunur (edge_esigi/yedek_durumu ile
    ayni desen) -> test sabiti gecici kisaltip zaman asimi yolunu kanitlayabilir.
    fonk icinde olusan istisna CAGIRANA aynen aktarilir (davranis degismesin)."""
    if saniye is None:
        saniye = YEDEK_ZAMAN_ASIMI
    kutu = {}

    def sar():
        try:
            kutu["sonuc"] = fonk()
        except BaseException as e:                     # pano: hicbir hal disari sizmasin
            kutu["hata"] = e

    ip = threading.Thread(target=sar, daemon=True)
    ip.start()
    ip.join(saniye)
    if ip.is_alive():
        return None, True                              # parcacik TERK EDILDI (daemon)
    if "hata" in kutu:
        raise kutu["hata"]
    return kutu.get("sonuc"), False


def _drive_deseni():
    """drive_yolu.DESEN (Drive mount joker deseni) — tek kaynak. Modul yoksa None.
    drive_yolu import aninda HICBIR SEY yazmaz/calistirmaz (yalniz sabit tanimlar)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import drive_yolu
        return drive_yolu.DESEN
    except Exception:
        return None


def yedek_dizini(repo_kok):
    """Drive'daki backup/ dizinini SALT-OKUNUR cozer. (yol, hal) doner.
    hal: 'var' | 'klasor-yok' (Drive bagli ama backup yok) | 'drive-yok'."""
    adaylar = []
    cfg = os.path.join(repo_kok, ".stl-backup-dir")
    try:
        if os.path.isfile(cfg):
            with open(cfg, "r", errors="replace") as f:
                kayitli = f.read().strip()
            if kayitli:
                adaylar.append(kayitli)
    except OSError:
        pass
    desen = _drive_deseni()
    if desen:
        try:
            adaylar += sorted(glob.glob(desen))
        except OSError:
            pass
    drive_bagli = False
    for stl in adaylar:
        ust = os.path.dirname(stl.rstrip("/"))       # .../Pruvo/STL -> .../Pruvo
        try:
            if not os.path.isdir(ust):
                continue                              # kayitli yol bayat/mount yok
            drive_bagli = True
            backup = os.path.join(ust, "backup")
            if os.path.isdir(backup):
                return backup, "var"
        except OSError:
            continue
    return None, ("klasor-yok" if drive_bagli else "drive-yok")


def _agac_say(dizin):
    """SALT-OKUNUR dosya sayimi (os.walk). Okunamazsa None. HICBIR SEY YAZMAZ."""
    try:
        if not os.path.isdir(dizin):
            return 0
        adet = 0
        for _d, _altlar, dosyalar in os.walk(dizin):
            adet += len(dosyalar)
        return adet
    except OSError:
        return None


def _atlama_kaydi_oku(backup_dizini):
    """Ayri atlama dosyasinin (.son-yedek-atlama.json) hali. SALT-OKUNUR, ASLA patlamaz.

    Doner (kayit, hal):
      'var'        -> dosya var ve DICT olarak cozuldu (kayit = o dict)
      'yok'        -> dosya YOK. Bu KESIN bir cevaptir: ayri kayit hic tutulmamis.
      'bilinmiyor' -> dosya VAR ama ondan dict elde EDILEMEDI (bozuk JSON, bos dosya,
                      kesik JSON, dict-olmayan JSON, izinsiz, dizin, ikili cop...).

    🔴 NEDEN 'yok' ILE 'bilinmiyor' AYRI (K2, 27 Tem — 6. tur): eskiden ikisi de tek
    bir `except: pass` icindeydi, yani "dosyayi okuyamadim" ile "dosya hic yok" AYNI
    sonucu veriyordu: damgadan gelen `son_atlama*` mirasi ayakta kaliyor ve fail-closed
    uyariyi SUSTURUYORDU (olculdu: 8 bozuk-dosya biciminin 6'sinda pano "taze" diyordu).
    Okunamayan dosya bir CEVAP DEGILDIR; atlama duzlemi BILINMIYOR demektir."""
    yol = os.path.join(backup_dizini, YEDEK_ATLAMA_ADI)
    try:
        with open(yol, "r", errors="replace") as f:
            kayit = json.load(f)
    except FileNotFoundError:
        return None, "yok"
    except (OSError, ValueError, UnicodeDecodeError):
        # IsADirectoryError / PermissionError / JSONDecodeError ...: dosya VAR ama
        # cozulemedi. (Yaris: arada silinmisse exists False -> 'yok'a duseriz.)
        return None, ("bilinmiyor" if os.path.exists(yol) else "yok")
    if not isinstance(kayit, dict):
        return None, "bilinmiyor"          # JSON gecerli ama dict DEGIL (liste/dize/sayi)
    return kayit, "var"


# Atlamayi SUSTURABILEN alanlar: "o atlama zararsizdi" hukmunu bu ikisi verir.
# Yalniz atlamayi GERCEKTEN goren yazici (ayri dosya) ya da atlamayi damganin ICINE
# yazan ESKI surum (<=2) bunlari uretebilir; baska her kaynak KALINTIdir.
ATLAMA_SUSTURUCU = ("son_atlama_kapsandi", "son_atlama_sahip_baslangici")
# Atlamayi ayri dosyaya yazan ILK damga surumu. Bundan itibaren damganin ICINDEKI
# `son_atlama*` alanlari yalnizca damga_yaz'in TASIDIGI kalintidir.
ATLAMA_AYRI_DOSYA_SURUMU = 3


def _atlama_birlestir(damga, atlama_kaydi, atlama_hali):
    """Atlama duzlemini damgayla birlestirir. Doner: (damga, okunamadi, kalinti).

    ILKE: bir atlamayi SUSTURMAK icin KANIT gerekir; uyarmak icin gerekmez.
      'var'        -> ayri dosya TEK KAYNAK: damgadan gelen TUM `son_atlama*` DUSER
                      (kismi miras yok), yerine dosyadakiler gecer.
      'bilinmiyor' -> damgadan gelen TUM `son_atlama*` DUSER **ve** panoya gorunur bir
                      "atlama kaydi OKUNAMADI" uyarisi cikar (fail-closed). Miras ne
                      susturabilir ne de uydurabilir.
      'yok'        -> ayri kayit hic tutulmamis.
                      * damga ESKI surum (<3): atlamayi damganin ICINE yazan yazici
                        buydu -> alanlar MESRU, oldugu gibi kalir.
                      * damga YENI surum (>=3): bu alanlar damga_yaz'in onceki damgadan
                        TASIDIGI kalintidir (bir kez girdi mi sonsuza dek yasar) ->
                        SUSTURUCU ikili DUSER, atlamanin KENDISI kalir ki pano UYARSIN."""
    son_atlama_var = any(k.startswith("son_atlama") for k in damga)
    if atlama_hali == "var":
        damga = {k: v for k, v in damga.items() if not k.startswith("son_atlama")}
        damga.update({k: v for k, v in (atlama_kaydi or {}).items()
                      if k.startswith("son_atlama")})
        return damga, False, False
    if atlama_hali == "bilinmiyor":
        return ({k: v for k, v in damga.items() if not k.startswith("son_atlama")},
                True, False)
    surum = damga.get("surum")
    eski_yazici = (isinstance(surum, (int, float)) and not isinstance(surum, bool)
                   and surum < ATLAMA_AYRI_DOSYA_SURUMU)
    if son_atlama_var and not eski_yazici:
        return ({k: v for k, v in damga.items() if k not in ATLAMA_SUSTURUCU},
                False, True)
    return damga, False, False


def _yedekle_modulu():
    """tools/yedekle.py'yi TEMBEL + KORUMALI yukler (imza olcumunun TEK kaynagi).

    🔴 NEDEN KOPYALAMIYORUZ: imza tanimini panoda IKINCI kez yazmak, iki tanimin
    sessizce ayrisma riskidir (tam da kapatmaya calistigimiz sinif). Import yalnizca
    okur (modul duzeyinde tek `git rev-parse` var, yazma YOK) ve olcum zaman asimi
    sarmalayicisinin ICINDE kosar."""
    global _YEDEKLE_MODULU
    if _YEDEKLE_MODULU is None:
        yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yedekle.py")
        spec = importlib.util.spec_from_file_location("yedekle_pano", yol)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _YEDEKLE_MODULU = m
    return _YEDEKLE_MODULU


_YEDEKLE_MODULU = None


def _canli_kaynak_imzasi():
    """Kaynak kumesinin SU ANKI olcumu. SALT-OKUNUR, ASLA patlamaz.
    Doner: {"kok": <olcumun ait oldugu ana agac>, "adaylar": [imza, ...]} ya da None.

    IKI ADAY (`--sirlar` kapali/acik): damgadaki imzayi hangi bayrakla kosan bir yedek
    yazdi bilemeyiz; ikisinden BIRI tutuyorsa kapsam saglanmistir. Fail-closed yon:
    hicbiri tutmuyorsa "degisti" denir.

    `kok` NEDEN DONER: imza yalnizca AYNI kaynak agaci icin anlamlidir. Damga baska bir
    agac icin yazilmissa (yasanmis F1 hatasi: ROOT worktree'ye dusuyordu; ayrica izole
    kum havuzu kosumlari) karsilastirma "degisti" diye BAGIRIR ve pano gurultuye boger —
    gurultulu pano olu panodur. O halde cevap "olculemedi"dir, yanlis alarm DEGIL.
    Maliyet olculdu: import 0,017 sn + aday basina 0,002 sn (stat gezinmesi, okuma YOK)."""
    try:
        yedekle = _yedekle_modulu()
        adaylar = [imza for imza in (yedekle.kaynak_imzasi(s) for s in (False, True))
                   if isinstance(imza, dict)]
        if not adaylar:
            return None
        return {"kok": yedekle.ROOT, "adaylar": adaylar}
    except Exception:                      # pano bir KAPI degil: olcemedik -> None
        return None


def yedek_durumu(backup_dizini, hal="var", simdi=None, esik=None):
    """Damgayi okuyup yasi esikle karsilastirir + damganin IDDIASINI dogrular.

    esik None ise modul sabiti CALISMA ANINDA okunur (varsayilani def anina
    SABITLEMEZ) -- edge_esigi() ile ayni desen: test sabiti gecici degistirip
    bu fonksiyonun gercekten onu kullandigini kanitlayabilir.

    F2 (26 Tem): "icerik: memory 112 + skills 13" satiri DAMGANIN IDDIASIYDI,
    Drive'in gercegi degil -- backup/skills silinse bile pano "taze" diyordu.
    Artik backup/memory + backup/skills SAYILIR ve iddiayla karsilastirilir.
    Gercek < iddia ise uyarilir. (Gercek > iddia NORMALDIR: kaynaktan silinen
    dosyanin yedek kopyasi durur; yedek eklemelidir, ayna degil.)
    F3: damga GELECEKTE ise "taze" DENMEZ -- saat kaymasi/bozuk yazim panoyu
    yesile civilemesin. Tolerans YOK (bilerek): sahte-yesil, tek seferlik
    "supheli" gurultusunden pahalidir; bir sonraki yedek kendi kendine duzeltir.
    """
    if esik is None:
        esik = YEDEK_BAYAT_SANIYE
    simdi = time.time() if simdi is None else simdi
    sonuc = {"hal": hal, "yas": None, "damga": None, "esik": esik,
             "yol": backup_dizini, "sayim": {}}
    if hal != "var" or not backup_dizini:
        return sonuc
    damga = None
    try:
        with open(os.path.join(backup_dizini, YEDEK_DAMGA_ADI), "r", errors="replace") as f:
            damga = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError):
        damga = None
    # ATLAMA KAYDI ayri dosyadan gelir ve damgadaki (eski surum) kopyasini EZER.
    # UC HAL ayri ayri yorumlanir (bkz. _atlama_kaydi_oku): 'var' | 'yok' | 'bilinmiyor'.
    atlama_kaydi, atlama_hali = _atlama_kaydi_oku(backup_dizini)
    sonuc["atlama_hali"] = atlama_hali
    if isinstance(damga, dict):
        damga, sonuc["atlama_okunamadi"], sonuc["atlama_kalintisi"] = \
            _atlama_birlestir(damga, atlama_kaydi, atlama_hali)
    if not isinstance(damga, dict) or not isinstance(damga.get("zaman"), (int, float)):
        sonuc["hal"] = "damgasiz"
        return sonuc
    sonuc["damga"] = damga
    sonuc["yas"] = simdi - damga["zaman"]

    # F2: damganin iddiasini Drive'daki GERCEK dosya sayisiyla karsilastir.
    for ad in ("memory", "skills"):
        iddia = damga.get(ad)
        if not isinstance(iddia, int):
            continue
        gercek = _agac_say(os.path.join(backup_dizini, ad))
        sonuc["sayim"][ad] = (gercek, iddia)

    if sonuc["yas"] < 0:
        sonuc["hal"] = "supheli"                      # F3: damga gelecekte
    elif sonuc["yas"] < esik:
        sonuc["hal"] = "taze"
    else:
        sonuc["hal"] = _bayat_mi_guncel_mi(damga, simdi, esik)
    return sonuc


def _dogrulama_hali(damga, simdi, esik, canli=None):
    """K3 — esik asilmis bir damganin DOGRULAMA kaydini yorumlar (saf fonksiyon).
    Doner: 'guncel' | 'olculemedi' | 'kapsam-degisti' | 'kapsam-olculemedi' | None.

    `canli`: kaynaklarin SU ANKI imzalari (aday listesi) ya da None (olculemedi).
    Cagiran olcer (bkz. _bayat_mi_guncel_mi); bu fonksiyon SAF kalir.

    'guncel' demek icin BES sart birden (biri tutmazsa yesil VERILMEZ):
      1. `dogrulandi` sayi VE kendisi TAZE (esigi asmamis) — yoksa dogrulama da bayat,
      2. `dogrulandi` >= damganin `baslangic`i — yani dogrulama, damgaya EN SON dokunan
         kosuma ait (bkz. asagidaki KARISIK SURUM gerekcesi),
      3. `dogrulama_imzasi` ile damganin `kaynak_imzasi` KARSILASTIRILABILIR (ikisi de
         adet/bayt/mtime tasiyan sozluk),
      4. iki imza ESIT — yani o kosum "kopyadaki kaynak kumesi HALA aynidir" OLCTU.
      5. KAYNAKLARIN SU ANKI imzasi kopyanin imzasina ESIT — yani "degisiklik yok"
         iddiasi SIMDI de gecerli (bkz. asagidaki SART 5 gerekcesi).
    Sart 3 tutmazsa 'olculemedi' (GORUNUR) doner: iddia var ama dogrulanamiyor.
    🔴 NEDEN PANO KENDI DOGRULUYOR: yazicinin "degisiklik yok" iddiasina GUVENMEK,
    K1'de kapatilan sessiz-yesil deligini baska kapidan acmak olurdu.

    🔴 SART 2 — KARISIK SURUM DELIGI (27 Tem, izole kum havuzunda GERCEK ICRAYLA olculdu):
    bu depoda paralel worktree'lerin HER BIRININ kendi tools/yedekle.py'si var ama Drive'daki
    damga TEKTIR. Olculen sira: (a) YENI surum tam kopya (kaynak_imzasi yazildi), (b) YENI
    surum dogrulama (imzalar esit), (c) bir dosya mtime KORUNARAK degistirildi, (d) BAYAT bir
    kardes worktree ESKI surumle `--gerekliyse` kosdu. ESKI surumun imza ekseni olmadigi icin
    ATLADI ve `damga_tazele`si `dict(onceki)` yaptigi icin BAYAT `dogrulandi`/`dogrulama_imzasi`
    ciftini AYNEN korudu -> pano "✅ GUNCEL" dedi, degisiklik ise yedekte YOK. Sart 2 bunu
    kapatir: ESKI surum `baslangic`i ilerletir ama `dogrulandi`ya DOKUNMAZ -> `dogrulandi`
    geride kalir -> yesil verilmez. YENI surumde ikisi ayni cagride ayni degere yazilir.

    🔴 SART 5 — SART 2 YETMEZ (27 Tem, 6. tur; curutucu olcumu): sart 2'nin tetiklenmesi
    kardes surumun damgaya DOKUNMASINA bagliydi. Bugun 14 worktree'nin 12'si `main`
    surumundedir ve `main`'in `--gerekliyse` ATLA yolu damgaya HIC DOKUNMAZ -> sart 2 hic
    tetiklenmez -> ayni sira (mtime KORUNARAK degisen dosya + bayat kardes kosum) panoyu
    yine "✅ GUNCEL" yakiyordu, degisiklik yedekte YOKKEN. Yani gercek dunyadaki baskin
    hal kapsanmiyordu. Cozum: tazelik artik BASKA BIR KOSUMUN DAVRANISINDAN degil,
    OLCULEN ICERIKTEN turetilir — kopyanin imzasi kaynaklarin SU ANKI imzasiyla
    karsilastirilir. Kim ne kosarsa kossun (ya da hic kosmasin), degisen kaynak yesil
    vermez. Olculemezse (imza alinamadi) 'kapsam-olculemedi' -> GORUNUR, yesil DEGIL.
    ⚠️ ILAN EDILMIS KOR NOKTA: adet+bayt+mtime UCUNU birden koruyan bir icerik degisimi
    (ayni boyutta yerinde bayt takasi + mtime geri yazimi) bu eksende de gorunmez;
    ne_olculmedi() bunu tam kosuluyla ILAN eder."""
    dogrulandi = damga.get("dogrulandi")
    imza = damga.get("dogrulama_imzasi")
    kopya = damga.get("kaynak_imzasi")
    if not isinstance(dogrulandi, (int, float)) or isinstance(dogrulandi, bool):
        return None                                   # dogrulama iddiasi YOK -> bayat
    if dogrulandi > simdi or (simdi - dogrulandi) >= esik:
        return None                                   # dogrulamanin KENDISI bayat
    ref = damga.get("baslangic")
    if isinstance(ref, (int, float)) and not isinstance(ref, bool) and dogrulandi < ref:
        return None                                   # damgaya sonradan BASKASI dokundu
    if not _imza_kullanilir(imza) or not _imza_kullanilir(kopya):
        return "olculemedi"
    for alan in ("adet", "bayt", "mtime"):
        if imza[alan] != kopya[alan]:
            return "olculemedi"                       # degisiklik VAR: yesil verilmez
    # SART 5: iddiaya degil, SU ANA bak.
    if not isinstance(canli, dict) or not canli.get("adaylar"):
        return "kapsam-olculemedi"                    # olcemedik -> GORUNUR, yesil YOK
    dmg_kok, canli_kok = damga.get("kok"), canli.get("kok")
    # realpath: symlink'li yollar (macOS /var -> /private/var) ayni agaci gosterirken
    # metin olarak farklidir; normpath ile karsilastirmak SAHTE uyusmazlik uretiyordu.
    if (isinstance(dmg_kok, str) and dmg_kok and isinstance(canli_kok, str) and canli_kok
            and os.path.realpath(dmg_kok) != os.path.realpath(canli_kok)):
        return "kapsam-olculemedi"                    # damga BASKA agac icin: kiyaslanamaz
    for aday in canli["adaylar"]:
        if _imza_kullanilir(aday) and all(aday[a] == kopya[a]
                                          for a in ("adet", "bayt", "mtime")):
            return "guncel"
    return "kapsam-degisti"


def _imza_kullanilir(imza):
    """Kaynak imzasi karsilastirilabilir mi (adet/bayt/mtime sayisal)? fail-closed."""
    if not isinstance(imza, dict):
        return False
    for alan in ("adet", "bayt", "mtime"):
        d = imza.get(alan)
        if not isinstance(d, (int, float)) or isinstance(d, bool):
            return False
    return True


def _bayat_mi_guncel_mi(damga, simdi, esik):
    """Esik asildi: gercekten BAYAT mi, yoksa 'degisiklik YOK' diye DOGRULANMIS mi?

    🔴 K3 GEREKCESI: bayatlik `zaman`dan (son GERCEK kopyalama) olculur ve bu DOGRU;
    ama `--gerekliyse` yolu hicbir sey kopyalamadigi icin degismeyen bir sistemde
    `zaman` hic ilerlemez ve pano 2 gun sonra BOSUNA "⚠⚠ YEDEK BAYAT" der. Bosuna
    uyaran pano, kimsenin bakmadigi panodur. "YEDEK GEREKSIZ" ile "YEDEK BAYAT" ayri
    seylerdir; ayrimi OLCUM yapar (bkz. _dogrulama_hali), varsayim degil.

    CANLI IMZA burada olculur (yan etkili adim) ve saf _dogrulama_hali'ye VERILIR ->
    test olcumu `durum._canli_kaynak_imzasi`i degistirerek belirlenimli kilabilir."""
    hal = _dogrulama_hali(damga, simdi, esik, canli=_canli_kaynak_imzasi())
    if hal == "guncel":
        return "guncel"
    if hal == "olculemedi":
        return "dogrulama-olculemedi"
    if hal in ("kapsam-degisti", "kapsam-olculemedi"):
        return hal
    return "bayat"


def yedek_satirlari(d):
    """basim icin metin satirlari (kabul testi de dogrudan bunu okur)."""
    esik_gun = d["esik"] / 86400.0
    hal = d["hal"]
    if hal == "drive-yok":
        return ["  ÖLÇÜLEMEDİ: Drive bagli degil — yedek tazeligi bilinmiyor.",
                "  (Drive uygulamasini ac; pano bu yuzden hata VERMEZ, sadece olcemez.)"]
    if hal == "klasor-yok":
        return ["  ⚠ Drive bagli ama backup/ klasoru YOK — hic yedek alinmamis olabilir.",
                "  Kos: python3 tools/yedekle.py"]
    if hal == "damgasiz":
        return ["  ⚠ ÖLÇÜLEMEDİ: yedek var ama tazelik damgasi (%s) YOK." % YEDEK_DAMGA_ADI,
                "  (Damga oncesi surumle alinmis.) Bir kez kos: python3 tools/yedekle.py"]
    dmg = d["damga"] or {}
    ozet = "memory %s + skills %s + repo %s" % (
        dmg.get("memory", "?"), dmg.get("skills", "?"), dmg.get("repo", "?"))
    ne_zaman = _gecen(time.time() - d["yas"])

    # N2: ILK SATIR DURUMU SOYLER. "taze" YALNIZ tam + zamaninda + icerigi tutuyor iken
    # yazilir. Eskiden basligi hep "taze:" olup ⚠⚠ ALTTA kaliyordu -> goz gezdiren yanlis
    # sonuca variyordu. Panonun tek isi bu; 5 gunluk bayatligin fark edilmeme sebebi de buydu.
    kismi = dmg.get("tam") is False

    # ATLANAN KOSUM (26 Tem, kilit): yedekle.py kilidi alamazsa hicbir sey kopyalamaz
    # ve damgaya YALNIZ `son_atlama*` yazar (guven alanlarina dokunmaz). Atlama ancak
    # UC kosul birden saglanirsa SESSIZ gecer; biri bile tutmazsa UYARILIR:
    #   (1) atlama, son TAMAMLANAN kosumun BASLANGICINDAN once -> daha sonra kosan
    #       tam bir yedek kaybi zaten kapatmistir (kendi kendine temizlenir), ya da
    #   (2) `son_atlama_kapsandi` True  -> atlayan kosum OLCTU: o an kosan yedek
    #       basladiginda butun degisiklikler yerindeydi, VE
    #   (3) `son_atlama_sahip_baslangici` <= damganin `baslangic`i -> beklenen o
    #       kosum damgayi GERCEKTEN yazdi (bitti).
    # 🔴 (3) OLMADAN (2) BIR VARSAYIMDIR: sahip kilidi alip asilir/olurse dosya
    # yedege girmez, pano esige kadar (2 gun) "taze" der — kapatmaya calistigimiz
    # sessiz-hata sinifinin ta kendisi. Alan YOKSA cozulemez sayilir -> UYAR.
    # `baslangic` yoksa (eski surum damgasi) `zaman`a duseriz.
    # K2: atlama duzleminin BILINMEDIGI hal, basligi "taze"den ALIR (fail-closed).
    atlama_okunamadi = bool(d.get("atlama_okunamadi"))
    atlama = dmg.get("son_atlama")
    _ref = dmg.get("baslangic")
    if not isinstance(_ref, (int, float)):
        _ref = dmg.get("zaman")
    _sahip = dmg.get("son_atlama_sahip_baslangici")
    _sahip_bitti = (isinstance(_sahip, (int, float)) and isinstance(_ref, (int, float))
                    and _ref >= _sahip)
    atlanmis = (isinstance(atlama, (int, float)) and isinstance(_ref, (int, float))
                and atlama > _ref
                and not (dmg.get("son_atlama_kapsandi") is True and _sahip_bitti))
    atlama_satiri = (
        "  ⚠⚠ KISMI YEDEK: son kosumdan SONRA bir yedek ATLANDI (%s) — %s"
        % (dmg.get("son_atlama_iso", "?"), dmg.get("son_atlama_sebep", "?")))
    if isinstance(atlama, (int, float)) and dmg.get("son_atlama_kapsandi") is True \
            and not _sahip_bitti:
        atlama_satiri += "; beklenen kosum damgayi HIC YAZMADI (asildi/oldu)"

    eksik_icerik = []
    sayilamayan = []
    for ad, (gercek, iddia) in sorted((d.get("sayim") or {}).items()):
        if gercek is None:
            sayilamayan.append(ad)
        elif gercek < iddia:
            eksik_icerik.append((ad, gercek, iddia))

    kos = "  Kos: python3 tools/yedekle.py"
    if hal == "supheli":                              # F3
        return ["  ⚠ ŞÜPHELİ: damga GELECEK tarihli (%s) — tazelik ÖLÇÜLEMEDİ."
                % dmg.get("iso", "?"),
                "  (Saat kaymasi ya da bozuk yazim.)" + kos[1:]]
    dogrulandi_ne_zaman = ""
    if isinstance(dmg.get("dogrulandi"), (int, float)):
        dogrulandi_ne_zaman = _gecen(dmg["dogrulandi"])

    if hal == "bayat":
        satirlar = ["  ⚠⚠ YEDEK BAYAT: son yedek %s (%s) — esik %.0f gun."
                    % (ne_zaman, dmg.get("iso", "?"), esik_gun),
                    kos + "     (damga iddiasi: %s)" % ozet]
    elif kismi:
        # F1: kismi yedek ASLA "taze" diye gecmez — eksik yedek, eksik oldugunu SOYLER.
        satirlar = ["  ⚠⚠ KISMI YEDEK: son kosum %s ama beklenen repo dosyalari EKSIKTI (%s)"
                    % (ne_zaman, ", ".join(dmg.get("eksik") or []) or "?"),
                    "  -> bu dosyalarin yedegi TAZELENMEDI; ANA repodan kos: "
                    "python3 tools/yedekle.py"]
    elif eksik_icerik:
        ad, gercek, iddia = eksik_icerik[0]
        satirlar = ["  ⚠⚠ ICERIK EKSIK: backup/%s icinde %d dosya var, damga %d diyor "
                    "-> yedek bozulmus/silinmis." % (ad, gercek, iddia),
                    "  (son kosum %s)" % ne_zaman + kos[1:]]
        eksik_icerik = eksik_icerik[1:]
    elif atlanmis:
        satirlar = [atlama_satiri,
                    "  -> o kosumun degisiklikleri yedekte OLMAYABILIR (son tam kosum %s)."
                    % ne_zaman + kos[1:]]
        atlanmis = False                              # baslikta anlatildi
    elif atlama_okunamadi:
        # K2 fail-closed: ayri atlama dosyasi VAR ama cozulemedi -> atlanmis bir yedek
        # olup olmadigi BILINMIYOR. Miras alanlar bu hukmu VERMEZ (dusuruldu).
        satirlar = ["  ⚠ ÖLÇÜLEMEDİ: atlama kaydi (%s) VAR ama OKUNAMADI — atlanmis bir "
                    "yedek olup olmadigi BILINMIYOR." % YEDEK_ATLAMA_ADI,
                    "  (bozuk/bos/izinsiz kayit; son tam kosum %s)" % ne_zaman + kos[1:]]
        atlama_okunamadi = False                      # baslikta anlatildi
    elif hal == "kapsam-degisti":
        # K5 fail-closed: "degisiklik yok" dogrulamasi vardi ama kaynaklarin SU ANKI
        # imzasi kopyanin imzasindan FARKLI -> yedek bugunku kaynaklari KAPSAMIYOR.
        # (Kardes bir kosumun damgaya dokunup dokunmadigindan BAGIMSIZ olcum.)
        satirlar = ["  ⚠⚠ YEDEK KAPSAMIYOR: kaynaklar son yedekten (%s / %s) SONRA "
                    "DEGISTI — 'degisiklik yok' dogrulamasi artik gecerli DEGIL."
                    % (dmg.get("iso", "?"), ne_zaman),
                    "  (kaynak imzasi kopyanin imzasiyla UYUSMUYOR.)" + kos[1:]]
    elif hal == "kapsam-olculemedi":
        satirlar = ["  ⚠ ÖLÇÜLEMEDİ: 'degisiklik yok' dogrulamasi var ama kaynaklarin "
                    "SU ANKI imzasi OLCULEMEDI (son yedek %s)." % ne_zaman,
                    "  (yedekle.py imza olcumu basarisiz — GUNCEL denmez.)" + kos[1:]]
    elif hal == "dogrulama-olculemedi":
        # K3 fail-closed ucu: "degisiklik yok" iddiasi VAR ama pano onu DOGRULAYAMIYOR
        # (imza eksik/bozuk ya da imzalar FARKLI). Sessiz yesil YOK — gorunur olcum yok.
        satirlar = ["  ⚠ ÖLÇÜLEMEDİ: son gercek yedek %s (%s) esigi (%.0f gun) asti; "
                    "'degisiklik yok' dogrulamasi var ama DOGRULANAMIYOR."
                    % (ne_zaman, dmg.get("iso", "?"), esik_gun),
                    "  (kaynak imzasi eksik/bozuk ya da imzalar FARKLI.)" + kos[1:]]
    elif hal == "guncel":
        # K3: esik asildi AMA bu kosum "hicbir kaynak degismemis" OLCTU ve pano
        # olcumu DOGRULADI -> yedek gereksizdi, bayat DEGIL.
        satirlar = ["  ✅ GÜNCEL (son gercek yedek: %s / %s) — degisiklik YOK, "
                    "dogrulandi %s." % (dmg.get("iso", "?"), ne_zaman,
                                        dogrulandi_ne_zaman or "?"),
                    "  damga iddiasi: %s   (esik %.0f gun; kopyalamaya gerek olmadi)"
                    % (ozet, esik_gun)]
    else:
        satirlar = ["  taze: son yedek %s (%s) — esik %.0f gun."
                    % (ne_zaman, dmg.get("iso", "?"), esik_gun),
                    "  damga iddiasi: %s" % ozet]

    # Baslikta yer bulamayan kalan sorunlar (baslik zaten uyariyor).
    if kismi and hal == "bayat":
        satirlar.append("  ⚠⚠ KISMI YEDEK: beklenen repo dosyalari EKSIKTI (%s)"
                        % (", ".join(dmg.get("eksik") or []) or "?"))
    if atlanmis:                                      # baslik baska sorunu anlatiyor
        satirlar.append(atlama_satiri)
    if atlama_okunamadi:                              # baslik baska sorunu anlatiyor
        satirlar.append("  ⚠ atlama kaydi (%s) VAR ama OKUNAMADI — atlanmis yedek olup "
                        "olmadigi BILINMIYOR." % YEDEK_ATLAMA_ADI)
    if d.get("atlama_kalintisi"):
        satirlar.append("  ⚠ damgadaki `son_atlama*` alanlari KALINTI (ayri kayit yok, "
                        "damga yeni surum) — 'zararsiz atlama' hukmu VERMEZ.")
    if dmg.get("kilitsiz"):
        satirlar.append("  ⚠ son kosum KILITSIZ alindi (kilit dosyasi kurulamadi) — "
                        "eszamanli bir kosum varsa icerik karismis olabilir.")
    if "tam" not in dmg:
        satirlar.append("  not: damga eski surum (tamlik bilgisi yok) — bir kez yeniden kos.")
    for ad in sayilamayan:
        satirlar.append("  ⚠ %s/ sayilamadi (izin/okuma hatasi) — icerik DOGRULANAMADI." % ad)
    for ad, gercek, iddia in eksik_icerik:
        satirlar.append("  ⚠⚠ ICERIK EKSIK: backup/%s icinde %d dosya var, damga %d diyor."
                        % (ad, gercek, iddia))
    return satirlar


# ILAN EDILMIS KOR NOKTALAR — bolum 7'nin OLCMEDIGI seyler, TAM KOSULUYLA.
# 🔴 NEDEN AYRI BIR KANAL: "olculmedi" ile "sorun yok" ayni cikti icinde birbirine
# karisirsa pano sessiz-yesile doner. Bir sinif yapisal olarak olculemiyorsa (ya da
# bilerek olculmuyorsa) burada YUKSEK SESLE ilan edilir; okuyan neyin GARANTI
# OLMADIGINI bilir. Yeni bir kapi/eksen eklenince buraya da yazilir (kabul testi
# bu listenin BOS OLMADIGINI ve tam kosul tasidigini nobetler).
KOR_NOKTALAR = (
    ("adet+bayt+mtime UCUNU birden koruyan icerik degisimi",
     "yerinde ayni boyutta bayt takasi YAPILIR **VE** mtime eski degerine geri yazilir "
     "-> kaynak imzasi (adet/bayt/mtime) DEGISMEZ, pano 'GUNCEL' der. Hash alinmiyor "
     "(her oturum acilisinda ~6 MB okumanin bedeli olcuye deger bulunmadi)."),
    ("`ps` binary'si PATH'te yokken surec KIMLIGI",
     "kilit sahibinin pid'i CANLI mi + KIMLIGI tutuyor mu sorusu `ps`e baglidir; `ps` "
     "YOKSA pano 'asili/yarim' ayrimini yapamaz ve ⚪ OLCULEMEDI der (kirmizi yanmaz: "
     "bloklayici kapinin dis binary yoklugunda tum yayini durdurmasi yasanmis ariza)."),
    ("KILITSIZ bir KOPYALAMA'dan sonra kilitli bir DOGRULAMA kosumu",
     "dogrulama kosumu `kilitsiz` notunu temizler (not kosum-yereldir) ama `zaman` ve "
     "sayilar hala o kilitsiz kopyaya aittir -> 'eszamanli kosum icerigi karistirdi' "
     "riski panoda GORUNMEZ olur."),
    ("Drive mount ASILI iken yedegin GERCEK icerigi",
     "olcum %.0f sn zaman asimina duserse pano 'Drive yanit vermiyor' der; o an yedegin "
     "bayat/kismi/bozuk olup olmadigi OLCULMEMISTIR (asili mount okunamaz)."
     % YEDEK_ZAMAN_ASIMI),
)


def ne_olculmedi():
    """Ilan edilmis kor noktalar — basim icin metin satirlari."""
    satirlar = ["  (pano bunlari OLCMEZ — 'sorun yok' demek DEGILDIR:)"]
    for baslik, kosul in KOR_NOKTALAR:
        satirlar.append("  ⚪ %s" % baslik)
        satirlar.append("     KOSUL: %s" % kosul)
    return satirlar


def _etime_saniye(metin):
    """ps ETIME bicimini saniyeye cevirir: [[DD-]HH:]MM:SS. Cozulemezse None."""
    metin = (metin or "").strip()
    gun = 0
    if "-" in metin:
        g, _sep, metin = metin.partition("-")
        try:
            gun = int(g)
        except ValueError:
            return None
    parcalar = metin.split(":")
    try:
        sayilar = [int(p) for p in parcalar]
    except ValueError:
        return None
    if len(sayilar) == 2:
        sa, dk, sn = 0, sayilar[0], sayilar[1]
    elif len(sayilar) == 3:
        sa, dk, sn = sayilar
    else:
        return None
    return gun * 86400 + sa * 3600 + dk * 60 + sn


def _surec_bilgisi(pid):
    """(gecen_saniye, komut) — `ps` ile. Okunamazsa (None, None). SALT-OKUNUR."""
    try:
        p = subprocess.run(["ps", "-p", str(pid), "-o", "etime=,comm="],
                           capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None, None
    satir = (p.stdout or "").strip()
    if p.returncode != 0 or not satir:
        return None, None
    parcalar = satir.split(None, 1)
    gecen = _etime_saniye(parcalar[0])
    komut = parcalar[1].strip() if len(parcalar) > 1 else ""
    return gecen, komut


def _surec_canli(pid, baslangic=None, tolerans=2.0):
    """Bu pid, kilidi yazan kosumun SURECI OLABILIR mi?
      True  -> yasiyor ve kimligi tutarli
      False -> surec yok, YA DA pid yeniden kullanilmis (baska program / kilitten
               SONRA baslamis bir surec)
      None  -> olculemedi (ps yok/yanit vermedi)
    SALT-OKUNUR: sinyal 0 hicbir sey GONDERMEZ, `ps` yalnizca okur.

    🔴 NEDEN KIMLIK DOGRULAMASI (curutucu C): yalnizca "pid var mi" sormak iki yonlu
    yaniltir — yeniden kullanilan pid'de pano YANLIS SUSAR ('yarim' yerine 'tutuluyor'),
    ve 1 saati asinca ALAKASIZ CANLI bir sureci (pid=1/launchd dahil) "sonlandir" diye
    gosterir. Iki olcut: (1) komut adi python olmali (yedegi python kosar),
    (2) surec, kilit imzasindan ONCE var olmali — imzadan SONRA baslamis bir surec
    tanim geregi baska bir surectir. `tolerans` yalnizca ETIME'in 1 sn cozunurlugu icin.
    ⚠️ Burada DAIMA gercek saat kullanilir; kilit_durumu'nun `simdi` parametresi
    (test icin ileri alinabilir) YASI olcer, surec kimligini DEGIL."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass                              # baska kullanicinin sureci: VAR, kimlige bak
    except OSError:
        return None
    gecen, komut = _surec_bilgisi(pid)
    if gecen is None:
        return None                       # ps olcemedi -> bilinmiyor de, uydurma
    if komut and "python" not in os.path.basename(komut).lower():
        return False                      # baska bir program bu pid'i almis
    if isinstance(baslangic, (int, float)) and (time.time() - gecen) > baslangic + tolerans:
        return False                      # surec kilitten SONRA basladi -> yeniden kullanim
    return True


def kilit_durumu(repo_kok, simdi=None, esik=None):
    """`.yedek.lock`'i SALT-OKUNUR yorumlar. Kilidi ALMAYA CALISMAZ.

    hal: 'yok'       -> dosya yok/bos YA DA `bitti=` isaretli: kimse tutmuyor
         'tutuluyor' -> canli sahip, yas esigin altinda (NORMAL: pano susar)
         'asili'     -> canli sahip ama yas esigi asti -> yeni yedekler ATLANIYOR
         'yarim'     -> `bitti=` YOK ve sahip surec YOK/BASKASI: kosum ortasinda kesilmis
         'okunamadi' -> imza cozulemedi (bozuk satir)
    """
    esik = YEDEK_KILIT_ASILI if esik is None else esik
    simdi = time.time() if simdi is None else simdi
    sonuc = {"hal": "yok", "yas": None, "pid": None, "canli": None,
             "yol": os.path.join(repo_kok, YEDEK_KILIT_ADI), "esik": esik}
    try:
        with open(sonuc["yol"], "r", errors="replace") as f:
            ham = f.read(256).strip()
    except OSError:
        return sonuc
    if not ham:
        return sonuc
    pid = baslangic = bitti = None
    for parca in ham.split():
        if parca.startswith("pid="):
            try:
                pid = int(parca.split("=", 1)[1])
            except ValueError:
                pid = None
        elif parca.startswith("baslangic="):
            try:
                baslangic = float(parca.split("=", 1)[1])
            except ValueError:
                baslangic = None
        elif parca.startswith("bitti="):
            try:
                bitti = float(parca.split("=", 1)[1])
            except ValueError:
                bitti = None
    sonuc["pid"] = pid
    # `bitti=` isareti: kosum DUZGUN bitti, kilit birakildi -> kimse tutmuyor.
    # (yedekle.kilit_birak yazar; bosaltmak atlayan kosumun sahibi tanimasini
    #  engelledigi icin birakildi — bkz. yedekle.py kilit_birak gerekcesi.)
    if bitti is not None:
        sonuc["bitti"] = bitti
        return sonuc                      # hal 'yok'
    if baslangic is None:
        sonuc["hal"] = "okunamadi"
        sonuc["canli"] = _surec_canli(pid)
        return sonuc
    sonuc["canli"] = _surec_canli(pid, baslangic)
    sonuc["yas"] = simdi - baslangic
    if sonuc["canli"] is False:
        sonuc["hal"] = "yarim"
    elif sonuc["yas"] >= esik:
        sonuc["hal"] = "asili"
    else:
        sonuc["hal"] = "tutuluyor"
    return sonuc


def kilit_satirlari(d):
    """Kilit icin basim satirlari. NORMAL hallerde BOS liste doner (gurultu yapmaz);
    yalniz asili/yarim/bozuk kilitte konusur."""
    hal = d["hal"]
    if hal in ("yok", "tutuluyor"):
        return []
    if hal == "okunamadi":
        return ["  ⚠ yedek kilidi (%s) dolu ama imzasi COZULEMEDI — elle bak."
                % YEDEK_KILIT_ADI]
    if hal == "yarim":
        return ["  ⚠⚠ YARIM KALMIS YEDEK: kilit izi 'bitti' isareti TASIMIYOR ve sahip "
                "surec (pid %s) artik YOK -> kosum ortasinda kesilmis." % d["pid"],
                "  Kos: python3 tools/yedekle.py     (bir sonraki kosum izi temizler)"]
    return ["  ⚠⚠ YEDEK KILIDI %.1f saattir tutuluyor (pid %s %s) — bu sirada gelen "
            "yedekler ATLANIYOR." % ((d["yas"] or 0) / 3600.0, d["pid"],
                                     "CANLI" if d["canli"] else "canliligi OLCULEMEDI"),
            "  Kilit KIRILMAZ (yasayan yazici veriyi bozar): sureci kontrol et, "
            "gerekirse elle sonlandir. Kilit: %s" % d["yol"]]


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

    # 7) YEDEK TAZELIGI — pano ASLA patlamaz ve ASLA ASILMAZ:
    #    Drive yoksa/okunamazsa "ÖLÇÜLEMEDİ", yanit vermezse zaman asimi (N3).
    print("\n7) YEDEK TAZELIGI (Drive)")

    def _olc():
        yol, hal = yedek_dizini(kok)
        return yedek_satirlari(yedek_durumu(yol, hal))

    try:
        satirlar, asildi = zaman_asimiyla(_olc)
        if asildi:
            satirlar = ["  ⚠ ÖLÇÜLEMEDİ: Drive yanit vermiyor (%.0f sn zaman asimi asildi)."
                        % YEDEK_ZAMAN_ASIMI,
                        "  (Mount asili olabilir; pano BEKLEMEDI, devam ediyor.)"]
    except Exception as e:                    # pano bir KAPI degil: hicbir hal exit'i bozmaz
        satirlar = ["  ÖLÇÜLEMEDİ: yedek tazeligi okunamadi (%s)" % type(e).__name__]
    # KILIT: Drive olcumunun DISINDA — yerel dosya, asilma riski yok; Drive zaman
    # asimina dusse bile asili/yarim kilit GORUNMELI (atlama push'ta sessiz).
    try:
        satirlar = satirlar + kilit_satirlari(kilit_durumu(kok))
    except Exception:
        pass
    for satir in satirlar:
        print(satir)
    # ILAN EDILMIS KOR NOKTALAR: her kosumda 9 satir basmak panoyu gurultuye bogar
    # (gurultulu pano = olu pano) -> tam metin BAYRAKLA, isaret ise ÖLÇÜLEMEDİ ciktigi
    # anda GORUNUR. Boylece "olculemedi" hicbir zaman "sorun yok" gibi okunmaz.
    if "--ne-olculmedi" in sys.argv:
        print("\n7b) NE ÖLÇÜLMEDİ (ilan edilmis kor noktalar)")
        for satir in ne_olculmedi():
            print(satir)
    elif any("ÖLÇÜLEMEDİ" in s for s in satirlar):
        print("  (neyin olculMEDIGI icin: python3 tools/durum.py --ne-olculmedi)")

    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
