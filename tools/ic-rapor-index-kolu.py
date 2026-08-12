#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ic-rapor-index-kolu.py — IC RAPOR ADI KAPISININ *INDEX* (COMMIT ANI) KOLU.

Bu dosya BIR KAPI DEGILDIR: `tools/ic-rapor-adi-kapisi.py`nin HUKMUNU commit
anina tasiyan bir CAGRI NOKTASIDIR. Hukum, muafiyet govdesi ve desen BURADA
YENIDEN YAZILMAZ — kanonik kapidan IMPORT edilir ([[ikiz-tanim-sessiz-ayrisma]]).
Kapinin bir bayti bile degismez; degisen tek sey NEREDEN ve HANGI KUME UZERINDE
cagrildigidir.

🔴 NEDEN VAR — 12 AGU 2026 OLCULEN ARIZA (IKINCI VAKA):
Kanonik kapi izlenen dosyalarda ic isci-raporunun protokol adini arar ve CI'da
SERIT A'da BLOKLAYICIDIR (deploy.yml). 12 Agu 00:2xZ kosumu 31549865286'da
`serit-a3` KIRMIZI yandi -> `deploy` + `yayin` SKIPPED = YAYIN DURDU. Kok neden:
bir nobet turu o protokol adini IZLENEN kok defter DEVAM.md'ye birebir yazdi
(satir 206 + 214); kanama 3383aa90 ile durduruldu.

OLCULEN BOSLUK (`grep -rn ic-rapor-adi-kapisi tools/kancalar/` -> 0 isabet):
kapi YALNIZ deploy.yml (2 cagri) + nobet.yml (2 cagri) icinde yasiyordu. Yani
defteri yazan kisi ihlali ANCAK YAYIN DURDUKTAN SONRA ogreniyordu. Maliyet
ihlalin buyuklugunden degil YAKALANDIGI YERDEN geliyor: ayni sinifin BIRINCI
vakasi (9 Agu, `bdddaee0`) tools/devam-sinif-kapisi.py ekseninde yasandi ve o
kapi pre-commit kancasina baglanarak kapatildi — bu kapi baglanmadi, ikinci vaka
geldi. Bu kol ihlali COMMIT ANINDA durdurur: main'e HIC girmez, yayini HIC
durduramaz. (CI kolu YERINDE KALIR: kancalar commit EDILMEZ ve atlanabilir;
ZORLAYICI hukum deploy.yml'dedir. Bu kol onun YERINE GECMEZ, ONUNDE DURUR.)

🔴 EKSEN INDEX'TIR, CALISMA AGACI DEGIL ([[kanca-stage-disi-agaci-tarar]]):
Bu checkout'u BES ev paylasir. Kanonik kapinin BAYRAKSIZ kolu TUM izlenen
CALISMA AGACINI tarar (`git ls-files` + diskten okuma); o kolu kancaya oldugu
gibi baglamak, baska bir oturumun HENUZ STAGE'LENMEMIS yarim DEVAM.md taslagi
yuzunden HERKESIN commit'ini kilitlerdi. Bu kol INDEX KESISIMINI olcer:
evren = "bu commit'e giren dosyalar", icerik = INDEKSTEKI icerik (calisma
agacindaki degil). Yani stage'lenmemis bir ihlal burada KIRMIZI YAKMAZ — onu
CI'daki calisma-agaci kolu ve `--uzak` kolu kovalar.

🔴 KAPSAM EVRENI AD DESENINDEN DEGIL, KAPININ CAGRI GRAFINDAN TURER
([[kapsam-evrenini-cagri-grafindan-turet]]): kanonik kapinin `ana_tarama()`
evreni = `git ls-files` (TUM izlenen dosyalar) EKSI `KENDI_YOLU`. Buradaki
evren onun INDEX izdusumudur: stage'lenmis TUM yollar (yalniz `*.md` degil,
yalniz kok degil) EKSI ayni `KENDI_YOLU`. "Kok defterler" bir ALT KUMEDIR ve
ayrica sart kosulMAZ: bir ad deseni bir DEFTERDIR ve bayatlar.

🔴 FAIL-CLOSED, FAIL-SLOW DEGIL ([[fail-slow-fail-opendir]]): olculemeyen her
hal (kanonik kapi yuklenemedi / API'si taninmiyor / KENDI kirmizi-yesil
sozlesmesini karsilamiyor / git komutu dustu / indeks okunamadi) rc 2'dir ve
cagiran kanca commit'i DURDURUR. Hicbir kolda hata biriktirilip devam edilmez.

Kullanim:
    python3 tools/ic-rapor-index-kolu.py            # BETIGIN agacinin INDEKSI
    python3 tools/ic-rapor-index-kolu.py --kok YOL  # ACIKCA verilen agacin indeksi

Cikis kodu: 0 = temiz (stage'de muafiyet-disi isabet yok, ya da stage BOS),
1 = stage'lenmis en az bir dosyada muafiyet-disi gecis, 2 = OLCULEMEDI.
"""
import argparse
import importlib.util
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # SALT-OKUNUR tarama: hedef repoya __pycache__ yazma.

BETIK_DIZINI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BETIK_DIZINI)

# 🔴 TEK KAYNAK: git baglam scrub'i tools/git_ortami.py'dedir. Bir GIT KANCASI
# icinden kosuldugunda cagiran surec GIT_DIR/GIT_WORK_TREE ihrac eder ve acik
# `-C` hedefini SESSIZCE ezer; burada FALLBACK YAZILMAZ (modul yoksa cagri coker).
from git_ortami import git_ortami   # noqa: E402

# Hukmun KANONIK kaynagi. Bu dosya onun bir SURETI DEGIL, CAGIRANIDIR.
KAPI_DOSYA = "ic-rapor-adi-kapisi.py"

# Kanonik kapidan BEKLENEN API. Biri yoksa BICIM DEGISMIS demektir -> OLCULEMEDI.
_KAPI_API = ("tara", "kok_coz", "KENDI_YOLU", "DESEN", "_MUAFIYET_GOVDESI",
             "RC_TEMIZ", "RC_IHLAL", "RC_OLCULEMEDI")

RC_TEMIZ = 0
RC_IHLAL = 1
RC_OLCULEMEDI = 2

# `git diff --cached` icin TABAN: HEAD yoksa (ilk commit) BOS AGAC.
BOS_AGAC = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# Bu commit'e GIREN yollar. D (silinen) DISARIDA: silinen dosyanin indekste
# icerigi YOKTUR ve zaten ihlali GOTURUR. U (unmerged) fail-closed ele alinir.
DIFF_SUZGECI = "--diff-filter=ACMR"

# ---------------------------------------------------------------------------
# 🔴 KANCANIN VERDIGI INDEX KORUNUR — 12 AGU 2026 OLCULEN FAIL-OPEN (K70).
# `git commit -- <yol>` (pathspec / `--only`) ve `git commit -a` bicimleri GECICI
# bir index kurar ve pre-commit kancasina ONU `GIT_INDEX_FILE` ile verir. Olculen
# degerler: pathspec -> `<kok>/.git/next-index-<pid>.lock`, `-a` -> `<kok>/.git/
# index.lock`, duz `git add` + `git commit` -> `.git/index`.
# `git_ortami()`nin scrub kumesi GIT_INDEX_FILE'i DE dusurur; dusunce bu kol
# GERCEK `.git/index`i okur, o da HEAD ile AYNIDIR -> "stage'de 0 metin dosyasi
# tarandi" basip BOSTA YESIL verirdi. Yeniden uretildi: AYNI ihlal `git add`
# biciminde rc=1 (commit BLOKLANDI), pathspec biciminde rc=0 (commit ATILDI).
# NEDEN CIDDI: proje kurali `git add`i YASAKLAR ve tam da `git commit -F ... --
# <yollar>` bicimini ZORUNLU kilar -> kapi, MANDAT EDILEN commit yolunda KORDU.
# Kardes kol tools/devam-sinif-kapisi.py::_git AYNI commit'te 1 kok belgesi
# okuyordu; sebebi olculdu: o kol GERCEK yolda ortami BILEREK TEMIZLEMEZ
# (tools/katalog-alan-kapisi.py ile AYNI karar, orada da yazili).
# SCRUB YINE DE KALIR: miras alinan GIT_DIR/GIT_WORK_TREE acik `-C kok` hedefini
# SESSIZCE ezer (tools/git_ortami.py'de olculen kusur). ORTAK MODULUN DAVRANISI
# DEGISMEZ — geri verilen TEK ad burada, CAGRI YERINDE secilir.
# GIT_PREFIX BILEREK GERI VERILMEZ (olculdu): kanca cwd'si dort commit biciminin
# DORDUNDE de calisma agacinin TEPESIDIR, yani prefix'e ihtiyac YOKTUR; buna
# karsilik GIT_PREFIX set edildiginde `git -C kok diff --cached` cikti kumesi o
# prefix'e gore DARALIR -> kapsam SESSIZCE kuculurdu. Tasimak delik acardi.
# ---------------------------------------------------------------------------
INDEX_DEGISKENI = "GIT_INDEX_FILE"


def kanca_ortami(kaynak=None, cwd=None):
    """Scrub'li ortam + kancanin verdigi GIT_INDEX_FILE (MUTLAKLASTIRILMIS).

    Git, GIT_INDEX_FILE'i BASLADIGI dizine gore cozer; bu kol git'i `-C kok` ile
    cagirir, yani GORECELI bir deger (olculen: `.git/index`) `-C` hedefine gore
    cozulurdu. Deger burada surecin KENDI cwd'sine — kanca baglaminda calisma
    agacinin tepesine — gore MUTLAKLASTIRILIR, boylece `-C` ile arasinda fark
    kalmaz. Degisken YOKSA (kancasiz dogrudan kosum) hicbir sey EKLENMEZ: o
    halde GERCEK index zaten dogru evrendir."""
    kaynak = os.environ if kaynak is None else kaynak
    ort = git_ortami()
    ort.pop(INDEX_DEGISKENI, None)   # niyet ACIK: scrub dusurur, sonra biz veririz
    ham = kaynak.get(INDEX_DEGISKENI)
    if ham:
        ort[INDEX_DEGISKENI] = os.path.abspath(
            ham if cwd is None else os.path.join(cwd, ham))
    return ort


def kapi_modulu(dizin=BETIK_DIZINI):
    """(modul, hata) — kanonik kapiyi YUKLE ve SOZLESMESINI dogrula.

    🔴 SOZLESME AYAGI (varlik DEGIL DAVRANIS — [[kapi-beyanin-dogrulugunu-degil-
    varligini-olcer]]): API adlarinin var olmasi yetmez; kapinin `tara()` hukmu
    CANLI mi diye KENDI verisiyle sinanir:
      (a) kayitli bir muafiyet satiri YESIL kalmali,
      (b) kayitsiz yeni bir gecis KIRMIZI yanmali.
    Olu/bozuk bir hukum "0 isabet" verirdi ve bu kol sessizce YESIL yanardi."""
    yol = os.path.join(dizin, KAPI_DOSYA)
    if not os.path.isfile(yol):
        return None, ("KANONIK KAPI KAYNAGI YOK: %s — hukum burada YENIDEN "
                      "YAZILMAZ (ikiz tanim)." % yol)
    try:
        spec = importlib.util.spec_from_file_location("_pruvo_ic_rapor_kapi", yol)
        modul = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = modul
        eski_yol = list(sys.path)
        sys.path.insert(0, dizin)
        try:
            spec.loader.exec_module(modul)
        finally:
            sys.path[:] = eski_yol
    except BaseException as e:                                # noqa: BLE001
        return None, ("KANONIK KAPI YUKLENEMEDI (%s): %r" % (yol, e))

    eksik = [a for a in _KAPI_API if not hasattr(modul, a)]
    if eksik:
        return None, ("KANONIK KAPI API'si TANINMIYOR (%s): eksik %s — bicim "
                      "degismis olabilir; hukum VERILMEZ" % (yol, eksik))
    govde = list(getattr(modul, "_MUAFIYET_GOVDESI"))
    if not govde:
        return None, ("KANONIK KAPI MUAFIYET GOVDESI BOS (%s) — sozlesme "
                      "taninmiyor" % yol)
    kayitli_dosya, kayitli_satir, _gerekce = govde[0]
    try:
        yesil = modul.tara([(kayitli_dosya, kayitli_satir)])
        kirmizi = modul.tara([("sentetik-fikstur.md",
                               "kanit %s dosyasinda" % modul.DESEN.upper())])
    except BaseException as e:                                # noqa: BLE001
        return None, ("KANONIK KAPI HUKMU KOSTURULAMADI (%s): %r" % (yol, e))
    if yesil:
        return None, ("KANONIK KAPI ASIRI GENIS (%s): KENDI kayitli muafiyet "
                      "satiri KIRMIZI yaniyor -> hukum VERILMEZ" % yol)
    if not kirmizi:
        return None, ("KANONIK KAPI OLU/BOZUK (%s): kayitsiz yeni gecis "
                      "YAKALANMIYOR -> '0 isabet' hukmu ATFEDILEMEZ" % yol)
    return modul, None


def _git(kok, *args):
    """(rc, stdout_bytes, stderr_metin). Ortam SCRUB'LI: kanca baglaminda miras
    alinan GIT_DIR acik `-C kok` hedefini SESSIZCE ezerdi. TEK ISTISNA
    GIT_INDEX_FILE'dir — bkz. `kanca_ortami` ve yukaridaki K70 gerekcesi:
    pathspec/`-a` commit'lerinde OLCULECEK index O DEGISKENDEDIR."""
    try:
        p = subprocess.run(["git", "-C", kok] + list(args), capture_output=True,
                           env=kanca_ortami(), timeout=120)
    except OSError as e:
        return 127, b"", "git calistirilamadi: %s" % e
    except subprocess.TimeoutExpired:
        return 124, b"", "git 120 sn icinde yanit vermedi"
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace").strip()


def stage_taban(kok):
    """(taban, hata) — `git diff --cached` icin taban: HEAD, yoksa BOS AGAC."""
    rc, _o, _h = _git(kok, "rev-parse", "--verify", "--quiet", "HEAD")
    if rc == 0:
        return "HEAD", None
    rc2, _o2, hata2 = _git(kok, "cat-file", "-e", BOS_AGAC + "^{tree}")
    if rc2 != 0:
        return None, ("HEAD YOK ve BOS AGAC nesnesi de okunamadi (rc=%d): %s"
                      % (rc2, hata2))
    return BOS_AGAC, None


def stage_yollari(kok):
    """(yollar, hata) — bu commit'e GIREN repo-goreli yollar (INDEX ekseni)."""
    taban, hata = stage_taban(kok)
    if hata:
        return None, hata
    rc, cikti, hata_m = _git(kok, "diff", "--cached", "--name-only", "-z",
                             DIFF_SUZGECI, taban)
    if rc != 0:
        return None, ("`git diff --cached` DUSTU (rc=%d): %s — stage OLCULEMEDI"
                      % (rc, hata_m))
    yollar = []
    for ham in cikti.split(b"\0"):
        if not ham:
            continue
        try:
            yollar.append(ham.decode("utf-8"))
        except UnicodeDecodeError:
            return None, ("INDEKSTE UTF-8 COZULEMEYEN YOL var (%r) -> evren "
                          "belirsiz, hukum VERILMEZ" % ham[:60])
    return yollar, None


def stage_icerigi(kok, yol):
    """(icerik|None, hata) — yolun INDEKSTEKI icerigi.

    icerik None + hata None = metin DEGIL (binary/UTF-8 cozulemiyor) -> ATLA.
    Kanonik kapinin `_oku()` davranisi da AYNIDIR: bu desen yalniz metinde
    anlamlidir."""
    rc, ham, hata_m = _git(kok, "cat-file", "blob", ":" + yol)
    if rc != 0:
        return None, ("INDEKSTEN OKUNAMADI (%s, rc=%d): %s — 'temiz' DEGIL, "
                      "OLCULEMEDI" % (yol, rc, hata_m))
    try:
        return ham.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, None


def index_taramasi(kok, modul):
    """(ihlaller, taranan_sayi, atlanan_sayi, hata) — INDEX kesisiminin hukmu."""
    yollar, hata = stage_yollari(kok)
    if hata:
        return None, 0, 0, hata
    ciftler = []
    atlanan = 0
    for yol in yollar:
        if yol == modul.KENDI_YOLU:
            # Kanonik kapi KENDI dosyasini tarama disi birakir (deseni TANIMLAMAK
            # icin TASIMAK ZORUNDADIR); index kolu ayni istisnayi TASIR, KOPYALAMAZ.
            atlanan += 1
            continue
        icerik, oku_hatasi = stage_icerigi(kok, yol)
        if oku_hatasi:
            return None, 0, 0, oku_hatasi
        if icerik is None:
            atlanan += 1
            continue
        ciftler.append((yol, icerik))
    return modul.tara(ciftler), len(ciftler), atlanan, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kok", metavar="YOL", default=None,
                    help="INDEKSI olculecek agac (varsayilan: BETIGIN agaci)")
    args = ap.parse_args()

    modul, hata = kapi_modulu()
    if hata:
        print("IC RAPOR ADI KAPISI (INDEX KOLU): OLCULEMEDI (fail-closed KIRMIZI)",
              file=sys.stderr)
        print(hata, file=sys.stderr)
        return RC_OLCULEMEDI

    # Kok cozumu de KANONIK: `kok_coz` fail-closed'dir (bayraksiz + cwd BASKA
    # agac -> hukum VERILMEZ). Ikinci bir kok mantigi YAZILMAZ.
    kok, kok_hatasi = modul.kok_coz(args.kok, os.getcwd())
    if kok_hatasi:
        print("IC RAPOR ADI KAPISI (INDEX KOLU): OLCULEMEDI (fail-closed KIRMIZI)",
              file=sys.stderr)
        print(kok_hatasi, file=sys.stderr)
        return RC_OLCULEMEDI

    ihlaller, sayi, atlanan, tarama_hatasi = index_taramasi(kok, modul)
    if tarama_hatasi:
        print("IC RAPOR ADI KAPISI (INDEX KOLU): OLCULEMEDI (fail-closed KIRMIZI)",
              file=sys.stderr)
        print(tarama_hatasi, file=sys.stderr)
        return RC_OLCULEMEDI

    # 🔴 OLCULEN EVREN HER KOSUMDA (yesilde de) BASILIR: bir "temiz" hukmu
    # sessizce baska bir agaca/kumeye atfedilemesin.
    print("IC RAPOR ADI KAPISI (INDEX KOLU): olculen agac = %s "
          "(stage'de %d metin dosyasi tarandi, %d atlandi)" % (kok, sayi, atlanan))
    if sayi == 0:
        # ON-ELEME SESSIZ DEGIL: atlama nedeni her seferinde BASILIR
        # (sessiz atlama = sessiz yesil).
        print("IC RAPOR ADI KAPISI (INDEX KOLU): stage'de olculecek metin dosyasi "
              "YOK -> bu commit bu eksende bir sey degistirmiyor.")
        return RC_TEMIZ
    if not ihlaller:
        print("IC RAPOR ADI KAPISI (INDEX KOLU): temiz (0 muafiyet-disi isabet).")
        return RC_TEMIZ

    print("IC RAPOR ADI KAPISI (INDEX KOLU): %d muafiyet-disi isabet "
          "(STAGE'LENMIS icerik):" % len(ihlaller))
    for yol, satir_no, satir in ihlaller:
        print("  %s:%d: %s" % (yol, satir_no, satir.strip()))
    print()
    print("Bu ad PUBLIC repoda ic is akisini gorunur kilar ve ayni satir CI'da")
    print("(deploy.yml serit-a3) BLOKLAYICI kapiyi kirmizi yakar -> YAYIN DURUR.")
    print("COZUM: yorum/docstring METNINDEN dosya adini kaldir, anlamini koruyarak")
    print("genel ifadeyle yeniden yaz (or. 'muhendis raporunda'). Fiilen kullanilan")
    print("kod / delegasyon speci ise tools/%s icindeki _MUAFIYET_GOVDESI'ne"
          % KAPI_DOSYA)
    print("GEREKCEYLE ekle. Defterdeki bir satirsa DEVAM-ARSIV.md'ye (git DISI) TASI.")
    return RC_IHLAL


if __name__ == "__main__":
    sys.exit(main())
