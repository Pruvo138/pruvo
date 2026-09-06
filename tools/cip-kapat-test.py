#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`cip-kapat.py` EMNIYET bataryasi — "olmamasi gerekirken SILMESIN".

🔴 CANLI AGACLAR UZERINDE kosar ama YALNIZ NEGATIF kollari olcer: her vakada
beklenen sonuc HICBIR SEYIN SILINMEMESIDIR. Pozitif silme kolu (rc=0 -> gercekten
siler) burada KOSULMAZ — gercek bir agaci yok etmek kabul testinin isi degildir;
o kol canli arsivleme aninda olculur ve kapanisa SAYIYLA yazilir.
"""
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "cip-kapat.py")
# 🔴 SENTETIK GIT TEK KAPIDAN (`tools/git_ortami.py`): fikstur depolari kanonik
# yardimciyla kurulur — miras alinan GIT_* baglami ve `git init`in ortama bagli ilk
# dal adi ORADA cozulur. `try/except ImportError -> yerel kopya` YAZILMAZ.
sys.path.insert(0, os.path.join(KOK, "tools"))
from git_ortami import sentetik_git  # noqa: E402

IDDIA = 0
GECTI = 0
KIRMIZI = []


def iddia(ad, kosul, ayrinti=""):
    global IDDIA, GECTI
    IDDIA += 1
    if kosul:
        GECTI += 1
        print("  [OK]   %s %s" % (ad, ayrinti))
    else:
        KIRMIZI.append(ad)
        print("  [KIRMIZI] %s %s" % (ad, ayrinti))


def kos(argv, cwd=None):
    p = subprocess.run([sys.executable] + argv, cwd=cwd, capture_output=True,
                       text=True, timeout=900, stdin=subprocess.DEVNULL)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sentetik_agaclar(gecici):
    """(ana_checkout, kirmizi_worktree) — IZOLE sentetik depo; canliya DOKUNMAZ.

    🔴 OLCULEN KUSUR (6 Eyl 2026 — bu bataryanin IKI kolu birden ORTAMIN SEKLINI
    olcuyordu, kolun kendisini DEGIL):
      * V1 `KOK`u (bu dosyanin deposunun koku) ANA CHECKOUT SANIYORDU. Batarya bir
        worktree'den kosuldugunda `KOK` bir worktree'dir -> V1a/V1b/V1c UCU BIRDEN
        kirmizi yanardi; kodda hicbir sey bozuk degildir.
      * V3 CANLI worktree listesinde 'kapisi kirmizi bir agac' ARIYORDU. CI
        runner'inda worktree HIC YOKTUR -> `V3 OLCULEMEDI` iddiasi 10 gundur
        SERIT B'yi kirmizi tutuyordu; V3/V4 kollari ise HIC olculmuyordu.
    Cozum sinif duzeyinde: iki sekil de SENTETIK olarak KURULUR (ana checkout +
    kapisi kirmizi worktree), kol her ortamda AYNI seyi olcer; canli ortamin sekli
    ayri bir eksende (V8) yalnizca RAPOR edilir, hukum vermez.
    """
    kok = os.path.realpath(gecici)
    repo = os.path.join(kok, "repo")
    os.makedirs(repo)
    sentetik_git(kok, "init", "-q", "-b", "main", repo, check=True)
    with open(os.path.join(repo, "a.txt"), "w", encoding="utf-8") as f:
        f.write("taban\n")
    sentetik_git(repo, "add", "a.txt", check=True)
    sentetik_git(repo, "commit", "-qm", "taban", check=True)

    cip = "sentetik-cip-a1b2c3"
    dal = "claude/" + cip
    worktree = os.path.join(kok, "wt", cip)
    sentetik_git(repo, "worktree", "add", "-q", "-b", dal, worktree, check=True)
    # Dala main'de OLMAYAN + hicbir uzaga ITILMEMIS bir commit koy -> kapi KIRMIZI.
    with open(os.path.join(worktree, "b.txt"), "w", encoding="utf-8") as f:
        f.write("dal isi\n")
    sentetik_git(worktree, "add", "b.txt", check=True)
    sentetik_git(worktree, "commit", "-qm", "dal isi", check=True)
    return repo, worktree


def main():
    gecici = tempfile.mkdtemp(prefix="cip-kapat-test-")
    try:
        return _kollar(gecici)
    finally:
        # 🔴 SILME MENZILI: yalnizca BU turun kendi actigi gecici dizin. Gercek ev
        # yoluna `rmtree` bu depoda KIRMIZI siniftir (FILO DERSI, 4 Eyl).
        shutil.rmtree(gecici, ignore_errors=True)


def _kollar(gecici):
    ana, kirmizi_wt = sentetik_agaclar(gecici)

    print("V1 — ANA CHECKOUT silinecek agac DEGIL (SENTETIK ana checkout)")
    rc, cikti = kos([ARAC, ana])
    iddia("V1a rc=0", rc == 0, "rc=%d" % rc)
    iddia("V1b 'ANA CHECKOUT' der", "ANA CHECKOUT" in cikti)
    iddia("V1c silme komutu ONERMEZ", "--uygula" not in cikti.split("ANA CHECKOUT")[-1])
    iddia("V1d SENTETIK ana checkout gercekten ana (worktree DEGIL)",
          os.path.isdir(os.path.join(ana, ".git")))

    print()
    print("V2 — GIT AGACI OLMAYAN yol -> rc=2, hicbir sey yapmaz")
    rc, cikti = kos([ARAC, "/private/tmp"])
    iddia("V2a rc=2", rc == 2, "rc=%d" % rc)

    print()
    print("V3 — KAPI KIRMIZI iken --uygula HICBIR SEY SILMEZ (SENTETIK kirmizi agac)")
    agac = kirmizi_wt
    # 🔴 ON KOSUL OLCULUR, VARSAYILMAZ: fikstur gercekten KIRMIZI mi? Yesil bir
    # fiksturde "silmedi" iddiasi hicbir sey kanitlamaz (kapi zaten silmeye
    # gelmezdi) — [[kabul-fiksturu-yasagi-kutsar]].
    on_rc, on_cikti = kos([ARAC, agac])
    iddia("V3-oncul FIKSTURUN KAPISI GERCEKTEN KIRMIZI", on_rc != 0,
          "rc=%d" % on_rc)
    # 🔴 YANLIS-YESIL OLDURUCU (6 Eyl 2026, olculdu): `rc != 0` tek basina
    # "kapi kirmizi dedi" ANLAMINA GELMEZ — arac kapiyi HIC KOSAMADIGINDA da
    # rc=2 doner. CI'da tam bu oluyordu (`cip-kapat.py` kapi yolunu
    # `/Users/okan/dev/pruvo` sabitinden turetiyordu; runner'da o yol YOK).
    # O hâlde V3-oncul/V3b/V3c "gecti" diye okunurken hicbir emniyet kolu
    # olculmemis oluyordu. Bu iddia rc'nin KAPI HUKMUNDEN geldigini olcer.
    # NOT: `HUKUM=` satirini ARAC HER ZAMAN basar (kapi cokse bile varsayilan
    # OLCULEMEDI yazilir) — o yuzden varligi kanit DEGILDIR. Kanit ikilidir:
    # kol satirlari (`KOL=`) uretilmis VE hukum OLCULEMEDI'ye dusmemis olmali.
    iddia("V3-oncul-b KAPI FIILEN KOSTU (rc kapi hukmunden geliyor)",
          "KOL=" in on_cikti and "HUKUM=OLCULEMEDI" not in on_cikti,
          "kol=%s" % ("VAR" if "KOL=" in on_cikti else "YOK"))
    var_once = os.path.isdir(agac)
    rc, cikti = kos([ARAC, agac, "--uygula"])
    var_sonra = os.path.isdir(agac)
    iddia("V3a agac ONCE vardi", var_once, agac)
    iddia("V3b --uygula rc!=0", rc != 0, "rc=%d" % rc)
    iddia("V3c agac SONRA DA DURUYOR (SILINMEDI)", var_sonra)
    iddia("V3d cikti YAPILACAK ISI ADIYLA sayar", "KOL=" in cikti)

    print()
    print("V4 — AGACIN ICINDEN --uygula REDDEDILIR (kendi zeminini cekemez)")
    rc4, cikti4 = kos([ARAC, agac, "--uygula"], cwd=agac)
    iddia("V4a rc!=0", rc4 != 0, "rc=%d" % rc4)
    iddia("V4b agac hala DURUYOR", os.path.isdir(agac))
    # 🔴 KOLUN GERCEKTEN CALISTIGI AYRICA OLCULUR: kapi KIRMIZI ise akis daha
    # ONCE cikar ve oz-agac emniyeti HIC KOSMAZ. "rc!=0 geldi" o kolun
    # kanitı DEGILDIR ([[emniyet-kontrolu-yorumdan-once-korlestirir]] emsali).
    ulasti = "UYGULAMA REDDEDİLDİ" in cikti4
    if ulasti:
        iddia("V4c OZ-AGAC EMNIYETI fiilen kostu (red metni basildi)", True)
    else:
        print("  [ULASMADI] V4c oz-agac emniyeti KOSMADI — kapi rc=%d ile ONCE cikti."
              % rc4)
        print("             Bu kol YALNIZ rc=0 agacta olculebilir; su an KANITSIZ.")
        iddia("V4c oz-agac emniyeti KANITLANDI", False,
              "rc=%d ile erken cikis; kol OLCULEMEDI" % rc4)

    print()
    print("V6 — CANLI OTURUM EMNIYETI: taze dokunulmus agac SILINMEZ")
    import subprocess as _sp
    rc6, cikti6 = kos(["-c", "import sys;sys.exit(0)"])
    # Agacin canlilik kolu KAPIDAN AYRIDIR: kapi yesil olsa bile taze agac silinmez.
    # Burada kolun KODDA VAR ve --uygula yolunda CAGRILIYOR oldugu olculur; canli
    # senaryo yukaridaki V3/V4 gercek agaclariyla zaten kirmizi doner.
    with open(ARAC, encoding="utf-8") as f:
        k6 = f.read()
    iddia("V6a canlilik kolu VAR", "taze_dokunus_dk" in k6)
    iddia("V6b --uygula yolunda CAGRILIYOR", "yas = taze_dokunus_dk(agac)" in k6)
    iddia("V6c OLCULEMEDI hali CANLI sayilir (fail-closed)",
          "yas is None or yas < a.yas_tavani" in k6)
    iddia("V6d ListAgents CANLILIK KANITI olarak KULLANILMIYOR",
          "ListAgents" not in k6.split("def taze_dokunus_dk")[1].split("def icinde_mi")[0]
          or "KULLANILMAZ" in k6)

    print()
    print("V5 — HUKUM IKIZLENMEDI: silme olcutu arsiv-kapisi.py'den gelir")
    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()
    iddia("V5a arsiv-kapisi CAGRILIYOR", "arsiv-kapisi.py" in kaynak)
    iddia("V5b ikinci bir 'silinebilir' olcutu YOK (rc disinda karar verilmiyor)",
          kaynak.count("worktree\", \"remove\"") == 1)
    iddia("V5c silmeden ONCE kapi YENIDEN kosuluyor (TOCTOU)",
          kaynak.count("kapi_kos(agac, repo)") >= 2)

    print()
    print("V9 — ORTAM CAPASI MUTANTI: kapi yolu SABIT EV YOLUNA capalanirsa kol OLUR")
    # 🔴 6 EYL 2026, OLCULMUS: `cip-kapat.py` HUKUM kaynagini
    # `/Users/okan/dev/pruvo` sabitinden turetiyordu. Okan'in diskinde o yol VAR
    # (kapi kosar, KOL= basilir); CI runner'inda YOK (`python3 <olmayan dosya>`
    # rc=2, cikti bos) -> V3d 10+ gun KIRMIZI, V3-oncul/V3b ise AYNI arizadan
    # YANLIS YESIL. Bu mutant capayi geri sokar ve kolun fiilen OLDUGUNU olcer.
    # Mutant CANLI govdede YASAMAZ: tools/ gecici dizine SYMLINK'lenir, yalniz
    # cip-kapat.py mutantli GERCEK KOPYA olur ve arac O AYNADAN kosulur.
    V9_CAPA = "ARAC_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
    V9_MUTANT = 'ARAC_KOKU = "/olmayan/ev/pruvo"'
    with open(ARAC, encoding="utf-8") as f:
        k9 = f.read()
    # 🔴 CAPA ULASIMI: capa kaynakta TEKIL degilse mutant hicbir seyi degistirmez
    # ve "gecti" bulgusu tabanin bulgusu olur
    # ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
    iddia("V9a CAPA TEKIL (mutant ULASIR)", k9.count(V9_CAPA) == 1,
          "isabet=%d" % k9.count(V9_CAPA))
    ayna = os.path.join(gecici, "ayna")
    os.makedirs(os.path.join(ayna, "tools"))
    _tools = os.path.join(KOK, "tools")
    for _ad in os.listdir(_tools):
        _k = os.path.join(_tools, _ad)
        if _ad != "cip-kapat.py" and os.path.isfile(_k):
            os.symlink(_k, os.path.join(ayna, "tools", _ad))
    _mut = os.path.join(ayna, "tools", "cip-kapat.py")
    with open(_mut, "w", encoding="utf-8") as f:
        f.write(k9.replace(V9_CAPA, V9_MUTANT, 1))
    rc9, cikti9 = kos([_mut, agac])
    iddia("V9b MUTANT kapiyi KOSAMAZ -> KOL= YOK, HUKUM OLCULEMEDI (hedef kol OLDU)",
          "KOL=" not in cikti9 and "HUKUM=OLCULEMEDI" in cikti9, "rc=%d" % rc9)
    # 🔴 KONTROL: kirmizinin sebebi MUTASYON mu, AYNANIN KENDISI mi? Ayni aynada
    # MUTASYONSUZ kopya ayni fiksturde KOL= BASMALI. Basmiyorsa V9b hicbir sey
    # kanitlamaz (ayna bozuktur, kol degil).
    _kontrol = os.path.join(ayna, "tools", "cip-kapat-kontrol.py")
    with open(_kontrol, "w", encoding="utf-8") as f:
        f.write(k9)
    rc9k, cikti9k = kos([_kontrol, agac])
    iddia("V9c KONTROL: mutasyonsuz AYNA kopya ayni fiksturde KOL= BASAR",
          "KOL=" in cikti9k and "HUKUM=OLCULEMEDI" not in cikti9k, "rc=%d" % rc9k)

    print()
    print("V8 — CANLI ORTAM EKSENI (RAPOR; hukum VERMEZ)")
    # 🔴 NEDEN HUKUM VERMEZ: canli ortamda kac worktree oldugu, bataryanin kosuldugu
    # agacin ana checkout olup olmadigi ARACIN dogrulugu hakkinda HICBIR SEY SOYLEMEZ.
    # Bu eksen kirmiziya baglanirsa batarya araci degil ORTAMI olcer ve her CI
    # kosumunda takvimle/makineyle birlikte renk degistirir (6 Eyl'e kadar oyleydi).
    ana_mi = os.path.isdir(os.path.join(KOK, ".git"))
    print("  ORTAM: batarya koku=%s ana_checkout=%s" % (KOK, "EVET" if ana_mi else "HAYIR"))
    rc8, cikti8 = kos([ARAC, KOK])
    print("  CANLI KOK uzerinde arac rc=%d hukum=%s"
          % (rc8, "ANA CHECKOUT" if "ANA CHECKOUT" in cikti8 else "CIP AGACI"))

    print()
    print("=" * 70)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (IDDIA, GECTI, len(KIRMIZI)))
    if KIRMIZI:
        for k in KIRMIZI:
            print("  DUSEN: %s" % k)
        return 1
    print("SONUC: GECTI ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
