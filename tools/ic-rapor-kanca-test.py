#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ic-rapor-kanca-test.py — IC RAPOR ADI KAPISININ PRE-COMMIT KOLUNUN
CALISTIRILABILIR KABUL BATARYASI (K66).

🔴 NEDEN REPODA DURUYOR ([[mutasyon-kaniti-yeniden-uretilebilir]]): anlatilan
batarya kanit DEGILDIR. Bu dosya, tools/ic-rapor-index-kolu.py'nin ve onu cagiran
tools/kancalar/pre-commit blogunun hukmunu HER KOSUMDA yeniden uretir.

OLCULEN ARIZA (12 Agu 2026, kosum 31549865286): kanonik kapi
tools/ic-rapor-adi-kapisi.py YALNIZ CI'da yasiyordu; izlenen kok deftere sizan bir
satir `serit-a3`u KIRMIZI yakti, `deploy` + `yayin` SKIPPED kaldi, YAYIN DURDU.
Onarim kapiyi DEGISTIRMEZ (bir bayti bile), yalnizca COMMIT ANINA bir CAGRI
NOKTASI ekler. Bu batarya o cagri noktasinin iki yonunu de olcer.

IKI KATMAN:
  A) ARAC KATMANI — gercek gecici git depolari + gercek `git add`: index kolu
     stage'i mi yargiliyor, muafiyet iceriğe mi bagli, fail-closed mi.
  B) KANCA KATMANI (E2E) — gercek `git commit`: kanca blogu VERBATIM olarak
     tools/kancalar/pre-commit'ten CIKARILIR (yeniden YAZILMAZ; ikiz govde
     olurdu) ve gercek bir kancada kosturulur. Ihlal commit'i REDDEDILMELI.

🔴 FIKSTURLER LITERAL DEGIL, KANONIK KAYNAKTAN TURER: aranan desen ve muafiyet
satirlari tools/ic-rapor-adi-kapisi.py'den OKUNUR. Aksi halde bu dosyanin KENDISI
kapinin taramasinda KIRMIZI yanardi ([[nobetci-kendi-dosyasinda-sizinti]]) ve
desen degisince fikstur sessizce bayatlardi.

Kullanim:
    python3 tools/ic-rapor-kanca-test.py           # tam batarya (rc 0/1)
    python3 tools/ic-rapor-kanca-test.py --sessiz  # yalniz ozet
"""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

from git_ortami import sentetik_git   # noqa: E402

KAPI_ADI = "ic-rapor-adi-kapisi.py"
KOL_ADI = "ic-rapor-index-kolu.py"
MODUL_ADI = "git_ortami.py"
KANCA_KAYNAGI = os.path.join(TOOLS, "kancalar", "pre-commit")

# Kanca govdesindeki blogun CAPASI. Blok buradan dosya SONUNA kadar VERBATIM
# alinir; capa bulunamazsa ya da BIRDEN COK eslesirse hukum VERILMEZ (fail-closed).
BLOK_CAPASI = "# --- 7) IC RAPOR ADI KAPISI"

RC_TEMIZ, RC_IHLAL, RC_OLCULEMEDI = 0, 1, 2


# ---------------------------------------------------------------------------
# Kanonik kaynaklar
# ---------------------------------------------------------------------------
def kapi_modulu():
    yol = os.path.join(TOOLS, KAPI_ADI)
    spec = importlib.util.spec_from_file_location("_pruvo_k66_kapi", yol)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


def ihlal_satiri(modul, onek="kanit"):
    """Kayitli OLMAYAN, kesinlikle KIRMIZI yakmasi gereken bir satir uret."""
    return "%s %s dosyasinda duruyor" % (onek, modul.DESEN.upper())


# ---------------------------------------------------------------------------
# Sentetik depo kurulumu
# ---------------------------------------------------------------------------
def depo_kur(d, kol_var=True, kapi_var=True, kapi_eki=None):
    """Gecici git deposu + tools kopyalari. (hicbir sey commit ETMEZ)"""
    os.makedirs(os.path.join(d, "tools"), exist_ok=True)
    shutil.copyfile(os.path.join(TOOLS, MODUL_ADI), os.path.join(d, "tools", MODUL_ADI))
    if kapi_var:
        hedef = os.path.join(d, "tools", KAPI_ADI)
        shutil.copyfile(os.path.join(TOOLS, KAPI_ADI), hedef)
        if kapi_eki:
            with open(hedef, "a", encoding="utf-8") as f:
                f.write(kapi_eki)
    if kol_var:
        shutil.copyfile(os.path.join(TOOLS, KOL_ADI), os.path.join(d, "tools", KOL_ADI))
    # 🔴 ADIM 8 (defter kota) FIKSTURE GERI KONDU — 1 Eyl 2026, KraL-Tamirci-1Eyl.
    # OLCULEN ARIZA: `KraL-KapiSupurmesi-29Agu` pre-commit adim 8'i silmis ve
    # fiksturun o adim icin kopyaladigi dosyalari da kaldirmisti. Ertesi gun K353
    # (30 Agu) adimi KANCAYA GERI KOYDU (`tools/kancalar/pre-commit`, "COMMIT
    # DURDURULDU — tools/defter-kota-kapisi.py YOK" blogu CANLI) ama FIKSTUR geride
    # kaldi. Bu dosya kanca govdesini `BLOK_CAPASI`'ndan dosya SONUNA kadar VERBATIM
    # aldigi icin adim 8 de e2e vakalarda kosuyor; dosya sentetik depoda olmayinca
    # kanca "temiz commit GECER" vakalarinda bile exit 1 veriyordu.
    # SONUC (CI kosumu 33445049998, hijyen-a3): 21 vakanin 4'u (B2/B5/B6/B7) her
    # kosumda KIRMIZI — ve gerekce ic rapor ekseni DEGIL, EKSIK FIKSTUR dosyasiydi.
    # SINIF: kanca govdesi TEK KAYNAKTAN aliniyor ama govdenin BAGIMLILIKLARI elle
    # tutuluyor; ikisi ayrisinca batarya kendi ekseni disinda kirmizi yanar.
    for _bagimlilik in ("defter-kota-kapisi.py", "defter-kota-taban.py",
                        "serbest_cagrilar.py"):
        _kaynak = os.path.join(TOOLS, _bagimlilik)
        if os.path.exists(_kaynak):
            shutil.copyfile(_kaynak, os.path.join(d, "tools", _bagimlilik))
    sentetik_git(d, "init", "-q", capture_output=True, text=True,
                 kimlik_ad="t", kimlik_eposta="t@t.local")
    return d


def kol_kos(d):
    """(rc, cikti) — index kolunu SENTETIK deponun icinden kostur."""
    p = subprocess.run([sys.executable, os.path.join(d, "tools", KOL_ADI)],
                       cwd=d, capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items()
                            if not k.startswith("GIT_")})
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def yaz(d, yol, icerik):
    tam = os.path.join(d, yol)
    os.makedirs(os.path.dirname(tam), exist_ok=True) if os.path.dirname(yol) else None
    with open(tam, "w", encoding="utf-8") as f:
        f.write(icerik)
    return tam


def ekle(d, *yollar):
    return sentetik_git(d, "add", *yollar, capture_output=True, text=True,
                        kimlik_ad="t", kimlik_eposta="t@t.local")


# ---------------------------------------------------------------------------
# A) ARAC KATMANI
# ---------------------------------------------------------------------------
def arac_vakalari(modul):
    """[(ad, gecti_mi, detay)]"""
    sonuc = []
    ihlal = ihlal_satiri(modul)
    muaf_dosya, muaf_satir, _g = modul._MUAFIYET_GOVDESI[0]

    # A1 POZITIF — stage'lenmis izlenen kok defterde ihlal -> KIRMIZI
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, "DEVAM.md", "notr satir\n%s\n" % ihlal)
        ekle(d, "DEVAM.md")
        rc, cikti = kol_kos(d)
        sonuc.append(("A1 pozitif: stage'lenmis kok defter ihlali",
                      rc == RC_IHLAL and "DEVAM.md:2" in cikti,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_IHLAL, cikti[-160:])))

    # A2 NEGATIF — ihlalsiz .md degisikligi -> YESIL (yanlis-pozitif nobeti)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, "DEVAM.md", "## Devam\n- olculdu: 618 izlenen dosya, 0 isabet\n")
        ekle(d, "DEVAM.md")
        rc, cikti = kol_kos(d)
        sonuc.append(("A2 negatif: temiz .md commit'lenebilmeli",
                      rc == RC_TEMIZ,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_TEMIZ, cikti[-160:])))

    # A3 STAGE EKSENI — ihlal YALNIZ calisma agacinda (stage TEMIZ) -> YESIL.
    # [[kanca-stage-disi-agaci-tarar]]: bu checkout'u BES ev paylasir; baska bir
    # oturumun yarim taslagi HERKESIN commit'ini kilitlememeli.
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md")
        yaz(d, "DEVAM.md", "temiz\n%s\n" % ihlal)          # stage'lenMEDI
        rc, cikti = kol_kos(d)
        sonuc.append(("A3 stage ekseni: stage'lenmemis ihlal BLOKLAMAZ",
                      rc == RC_TEMIZ,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_TEMIZ, cikti[-160:])))

    # A4 TERS EKSEN — ihlal INDEKSTE, calisma agaci TEMIZ -> KIRMIZI.
    # (A3'un ikizi: icerik DISKTEN degil INDEKSTEN okunuyor mu?)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, "DEVAM.md", "temiz\n%s\n" % ihlal)
        ekle(d, "DEVAM.md")
        yaz(d, "DEVAM.md", "temiz\n")                      # diskte artik temiz
        rc, cikti = kol_kos(d)
        sonuc.append(("A4 ters eksen: INDEKSTEKI ihlal BLOKLAR",
                      rc == RC_IHLAL,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_IHLAL, cikti[-160:])))

    # A5 MUAFIYET YESIL — kayitli dosya + kayitli satir BIREBIR
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, muaf_dosya, muaf_satir + "\n")
        ekle(d, muaf_dosya)
        rc, cikti = kol_kos(d)
        sonuc.append(("A5 muafiyet: kayitli satir YESIL kalir",
                      rc == RC_TEMIZ,
                      "rc=%d (beklenen %d); dosya=%s" % (rc, RC_TEMIZ, muaf_dosya)))

    # A6 MUAFIYET ICERIGE BAGLI — ayni dosya, DEGISTIRILMIS satir -> KIRMIZI
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, muaf_dosya, muaf_satir + " EKSTRA-KELIME\n")
        ekle(d, muaf_dosya)
        rc, cikti = kol_kos(d)
        sonuc.append(("A6 muafiyet icerige bagli: degisen satir KIRMIZI",
                      rc == RC_IHLAL,
                      "rc=%d (beklenen %d)" % (rc, RC_IHLAL)))

    # A7 KENDI_YOLU — kapinin KENDI dosyasi stage'lenirse KIRMIZI YANMAZ
    # (deseni TANIMLAMAK icin TASIMAK ZORUNDADIR; kanonik kapinin istisnasi TASINIR)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        ekle(d, modul.KENDI_YOLU)
        rc, cikti = kol_kos(d)
        sonuc.append(("A7 KENDI_YOLU: kapinin kendi dosyasi muaf",
                      rc == RC_TEMIZ and "1 atlandi" in cikti,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_TEMIZ, cikti[-160:])))

    # A8 EVREN AD DESENI DEGIL — `.md` OLMAYAN, KOKTE OLMAYAN dosya da olculur
    # ([[kapsam-evrenini-cagri-grafindan-turet]]: evren kapinin cagri grafindan
    # turer, "kok *.md" defterinden DEGIL).
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, "shop/src/alt/notlar.js", "// %s\n" % ihlal)
        ekle(d, "shop/src/alt/notlar.js")
        rc, cikti = kol_kos(d)
        sonuc.append(("A8 evren: alt dizindeki .js de olculur",
                      rc == RC_IHLAL and "shop/src/alt/notlar.js:1" in cikti,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_IHLAL, cikti[-160:])))

    # A9 BOS STAGE — atlama SESSIZ DEGIL, nedeni BASILIR
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        yaz(d, "DEVAM.md", "%s\n" % ihlal)                 # stage'lenMEDI
        rc, cikti = kol_kos(d)
        sonuc.append(("A9 bos stage: YESIL + neden BASILIR",
                      rc == RC_TEMIZ and "stage'de olculecek metin dosyasi YOK" in cikti,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_TEMIZ, cikti[-160:])))

    # A10 BINARY — UTF-8 cozulemeyen stage'lenmis dosya ATLANIR (cokmez)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        with open(os.path.join(d, "gorsel.bin"), "wb") as f:
            f.write(b"\xff\xfe\x00" + ihlal.encode("utf-16-le"))
        ekle(d, "gorsel.bin")
        rc, cikti = kol_kos(d)
        sonuc.append(("A10 binary stage: atlanir, cokme YOK",
                      rc == RC_TEMIZ and "atlandi" in cikti,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_TEMIZ, cikti[-160:])))

    # A11 FAIL-CLOSED (kaynak YOK) — kanonik kapi kopyada YOKSA hukum VERILMEZ
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d, kapi_var=False)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md")
        rc, cikti = kol_kos(d)
        sonuc.append(("A11 fail-closed: kanonik kapi YOK -> rc=2",
                      rc == RC_OLCULEMEDI,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_OLCULEMEDI, cikti[-160:])))

    # A12 FAIL-CLOSED (OLU HUKUM) — kapi VAR, API'si TAM, ama `tara` hicbir sey
    # bulmuyor. VARLIK degil DAVRANIS olculur
    # ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]]): olu hukum "0 isabet"
    # verirdi ve bu kol sessizce YESIL yanardi.
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d, kapi_eki="\n\ndef tara(ciftler, govde=None):\n    return []\n")
        yaz(d, "DEVAM.md", "%s\n" % ihlal)
        ekle(d, "DEVAM.md")
        rc, cikti = kol_kos(d)
        sonuc.append(("A12 fail-closed: OLU hukum -> rc=2 (yesil DEGIL)",
                      rc == RC_OLCULEMEDI,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_OLCULEMEDI, cikti[-160:])))

    # A13 FAIL-CLOSED (ASIRI GENIS HUKUM) — sozlesmenin IKINCI ayagi: kapi her
    # satiri yakiyorsa muafiyet govdesi olmus demektir -> hukum VERILMEZ.
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d, kapi_eki="\n\ndef tara(ciftler, govde=None):\n"
                             "    return [(y, 1, 'her satir') for y, _i in ciftler]\n")
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md")
        rc, cikti = kol_kos(d)
        sonuc.append(("A13 fail-closed: ASIRI GENIS hukum -> rc=2",
                      rc == RC_OLCULEMEDI,
                      "rc=%d (beklenen %d); cikti=%r" % (rc, RC_OLCULEMEDI, cikti[-160:])))
    return sonuc


# ---------------------------------------------------------------------------
# B) KANCA KATMANI (E2E, gercek `git commit`)
# ---------------------------------------------------------------------------
def kanca_blogu():
    """(govde, hata) — pre-commit'teki blok VERBATIM. Yeniden YAZILMAZ."""
    try:
        with open(KANCA_KAYNAGI, encoding="utf-8") as f:
            ham = f.read()
    except OSError as e:
        return None, "kanca kaynagi okunamadi (%s): %s" % (KANCA_KAYNAGI, e)
    n = ham.count(BLOK_CAPASI)
    if n != 1:
        return None, ("blok capasi %d kez eslesti (TAM 1 olmali): %r"
                      % (n, BLOK_CAPASI))
    return ham[ham.index(BLOK_CAPASI):], None


def kanca_kur(d, govde):
    hooks = os.path.join(d, ".git", "hooks")
    os.makedirs(hooks, exist_ok=True)
    yol = os.path.join(hooks, "pre-commit")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n"
                "pruvo_kok=$(git rev-parse --show-toplevel 2>/dev/null)\n"
                'if [ -z "$pruvo_kok" ]; then exit 1; fi\n\n')
        f.write(govde)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return yol


def commit_dene(d, mesaj="fikstur"):
    p = sentetik_git(d, "commit", "-q", "-m", mesaj, capture_output=True, text=True,
                     kimlik_ad="t", kimlik_eposta="t@t.local")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def pathspec_commit_dene(d, yol, mesaj="pathspec fiksturu"):
    """Gercek `git commit -- <yol>`; Git kancaya gecici index ihrac eder."""
    p = sentetik_git(d, "commit", "-q", "-m", mesaj, "--", yol,
                     capture_output=True, text=True,
                     kimlik_ad="t", kimlik_eposta="t@t.local")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def kolu_eski_scrub_mutantina_cevir(d):
    """K70 kok nedenini yeniden uret: gecici index baglamini scrub'da dusur."""
    yol = os.path.join(d, "tools", KOL_ADI)
    with open(yol, encoding="utf-8") as f:
        icerik = f.read()
    eski = 'env=git_ortami(korunan_baglam=("GIT_INDEX_FILE",)),'
    yeni = "env=git_ortami(),"
    if icerik.count(eski) != 1:
        raise RuntimeError("K70 mutasyon capasi TAM 1 kez bulunmadi")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik.replace(eski, yeni))


def kanca_vakalari(modul):
    sonuc = []
    govde, hata = kanca_blogu()
    if hata:
        sonuc.append(("B0 kanca blogu CIKARILDI", False, hata))
        return sonuc
    sonuc.append(("B0 kanca blogu CIKARILDI (verbatim, tek capa)", True,
                  "%d bayt" % len(govde)))
    ihlal = ihlal_satiri(modul)

    # B1 E2E POZITIF — stage'lenmis ihlal -> `git commit` REDDEDILMELI
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "notr\n%s\n" % ihlal)
        ekle(d, "DEVAM.md", "tools")
        rc, cikti = commit_dene(d)
        tamam = (rc != 0 and "COMMIT DURDURULDU" in cikti
                 and KAPI_ADI in cikti and "DEVAM.md:2" in cikti)
        sonuc.append(("B1 e2e pozitif: ihlal commit'i REDDEDILIR + gerekce basilir",
                      tamam, "rc=%d; cikti=%r" % (rc, cikti[-260:])))

    # B2 E2E NEGATIF — ihlalsiz commit GECMELI (kapi yayini kilitlemez)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "## Devam\n- olculdu: 0 isabet\n")
        ekle(d, "DEVAM.md", "tools")
        rc, cikti = commit_dene(d)
        sonuc.append(("B2 e2e negatif: temiz commit GECER",
                      rc == 0, "rc=%d; cikti=%r" % (rc, cikti[-260:])))

    # B3 E2E FAIL-CLOSED — arac YOKSA commit DURUR (sessiz atlama YOK)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d, kol_var=False)
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md", "tools")
        rc, cikti = commit_dene(d)
        tamam = rc != 0 and "COMMIT DURDURULDU" in cikti and KOL_ADI in cikti
        sonuc.append(("B3 e2e fail-closed: arac YOK -> commit DURUR",
                      tamam, "rc=%d; cikti=%r" % (rc, cikti[-260:])))

    # B4 E2E OLCULEMEDI — rc=2 de commit'i DURDURUR (fail-open'a YUVARLANMAZ)
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d, kapi_eki="\n\ndef tara(ciftler, govde=None):\n    return []\n")
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md", "tools")
        rc, cikti = commit_dene(d)
        tamam = rc != 0 and "rc=2" in cikti
        sonuc.append(("B4 e2e: rc=2 (OLCULEMEDI) commit'i DURDURUR",
                      tamam, "rc=%d; cikti=%r" % (rc, cikti[-260:])))

    # B5 E2E STAGE EKSENI — stage'lenmemis ihlal commit'i DURDURMAZ
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md", "tools")
        yaz(d, "DEVAM.md", "temiz\n%s\n" % ihlal)          # stage DISI
        rc, cikti = commit_dene(d)
        sonuc.append(("B5 e2e stage ekseni: stage DISI ihlal commit'i DURDURMAZ",
                      rc == 0, "rc=%d; cikti=%r" % (rc, cikti[-260:])))

    # B6 E2E PATHSPEC — proje commit bicimi `git commit -- <yol>` Git'in kancaya
    # GIT_INDEX_FILE ile verdigi GECICI index'i olcmeli. Scrub bu adi dusururse
    # kapi varsayilan (HEAD'e gore bos) index'i okuyup sessizce YESIL verir.
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md", "tools")
        rc0, cikti0 = commit_dene(d, "ilk")
        yaz(d, "DEVAM.md", "temiz\n%s\n" % ihlal)
        rc, cikti = pathspec_commit_dene(d, "DEVAM.md")
        tamam = (rc0 == 0 and rc != 0 and "COMMIT DURDURULDU" in cikti
                 and "DEVAM.md:2" in cikti)
        sonuc.append(("B6 e2e pathspec: gecici index'teki ihlal REDDEDILIR",
                      tamam, "ilk_rc=%d; rc=%d; ilk=%r; cikti=%r"
                      % (rc0, rc, cikti0[-120:], cikti[-260:])))

    # B7 KOK NEDEN MUTANTI — eski tam scrub geri getirildiginde AYNI gercek
    # pathspec commit'i ihlale ragmen gecer. Bu, B6'nin yalniz genel bir kanca
    # yesili degil tam K70 kusurunu olduren regresyon oldugunu kanitlar.
    with tempfile.TemporaryDirectory() as d:
        depo_kur(d)
        kanca_kur(d, govde)
        yaz(d, "DEVAM.md", "temiz\n")
        ekle(d, "DEVAM.md", "tools")
        rc0, cikti0 = commit_dene(d, "ilk")
        kolu_eski_scrub_mutantina_cevir(d)
        yaz(d, "DEVAM.md", "temiz\n%s\n" % ihlal)
        rc, cikti = pathspec_commit_dene(d, "DEVAM.md")
        tamam = (rc0 == 0 and rc == 0
                 and "stage'de olculecek metin dosyasi YOK" in cikti)
        sonuc.append(("B7 K70 mutanti: GIT_INDEX_FILE scrub edilirse fail-open",
                      tamam, "ilk_rc=%d; mutant_rc=%d; ilk=%r; cikti=%r"
                      % (rc0, rc, cikti0[-120:], cikti[-260:])))
    return sonuc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sessiz = "--sessiz" in argv
    bilinmeyen = [a for a in argv if a not in ("--sessiz",)]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2
    try:
        modul = kapi_modulu()
    except BaseException as e:                                # noqa: BLE001
        print("⚪ OLCULEMEDI: kanonik kapi yuklenemedi: %r" % e, file=sys.stderr)
        return 1

    vakalar = arac_vakalari(modul) + kanca_vakalari(modul)
    dusen = [v for v in vakalar if not v[1]]
    if not sessiz:
        print("IC RAPOR ADI KAPISI — PRE-COMMIT KOLU KABUL BATARYASI")
        for ad, tamam, detay in vakalar:
            print("  %s %-62s %s" % ("✅" if tamam else "🔴", ad, detay))
        print()
    print("SONUC: %d vaka, %d gecti, %d dustu"
          % (len(vakalar), len(vakalar) - len(dusen), len(dusen)))
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
