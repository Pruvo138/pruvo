#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kosucu-gecici-agac-test.py — foto kosucusu gecici-agac sarmalayicisinin kabul testi.

IZOLE: sahte bare repo + GERIDE ve KIRLI sahte ana checkout + sahte kosucu. GERCEK ev
yoluna hicbir yazim/silme YOK (PRUVO_KOSUCU_ANA / _D_KOK env override).

Kurulum, canli arizanin (14 Eki 2026) birebir modelidir: ana checkout origin/main'in
GERISINDE (v1 commit'li) ve calisma agaci KIRLI (v2), origin/main ise IKINCI bir
klondan push'lanmis v3'tur. Dogru sarmalayici v3'u kosar.

IDDIALAR:
  I1 origin/main'deki surum (v3) kosar — ne ana HEAD (v1) ne kirli agac (v2)
  I2 cikista gecici agac YOK (AGAC=... SILINDI=<n>KB; hicbir `*.noindex` ART) + log satiri
  I3 ic rc (4) disari aynen gecer
  I4 --log ic kosucuya da GECER (kosucunun HAL= satiri log'a dusmeye devam eder)
  I5 kuyruk BOS -> TAM agac ACILMAZ: `HAL=BOS rc=0`, rc=0, silinen kucuk (<1 MB),
     asil kosucu HIC kosmaz (MOCK_YOKLAMA=bos)
  I6 yoklama OLCULEMEZ -> rc=4, asil kosucu HIC kosmaz, is KUYRUKTA kalir
     (fail-closed; MOCK_YOKLAMA=hata)
  I7 3 ardisik BOS sonrasi geri cekilme: 4. kosum D1'e UĞRAMAZ (aralik 600) —
     durum `bos=3`, `KOSUCU_ERTELENDI ... aralik=600`, `HAL=BOS rc=0`
  I8 IS gorulunce aralik 120'ye doner: durum `bos=0`, ertesi kosum ERTELEMEZ
  I9 dizin adi `.noindex` ile biter (Spotlight indekslemez) ve ayni SHA icin YENIDEN
     KULLANILIR (ikinci kosum arsiv YAPMAZ)

MUTASYON KANITI (sarmalayicinin KOPYASINA delik acilir; listelenen iddia KIRMIZI olmali,
sabit "OLDU" satiri BASILMAZ — her mutant KOSTURULUR):
  M1 archive origin/main yerine HEAD          -> I1
  M2 kosucu ana checkout'tan calistirilir      -> I1
  M3 fetch yapilmaz (bayat origin/main)        -> I1
  M4 cikista rm -rf yok                        -> I2
  M5 ic rc yutulur                             -> I3
  M6 --log ic kosucudan sokulur                -> I4
  M7 BOS'ta tam agac yine de acilir            -> I5
  M8 yoklama hatasi BOS sayilir (fail-closed kirilir) -> I6
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_ortami import sentetik_git  # noqa: E402

WRAPPER = Path(__file__).resolve().parent / "kosucu-gecici-agac.sh"
DESEN = "gecici-XXXXXX"


def _mock(etiket):
    """Sahte kosucu. `--kuyruk-yokla` -> MOCK_YOKLAMA: is (varsayilan, rc=0) | bos (rc=10) |
    hata (rc=4). Normal kosu: SURUM=<etiket> + MOCK_RC. --log verilirse oraya HAL=MOCK ekler."""
    return f"""#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
if '--kuyruk-yokla' in a:
    m = os.environ.get('MOCK_YOKLAMA', 'is')
    print('YOKLAMA=' + m)
    if m == 'bos':
        print('HAL=BOS rc=0'); sys.exit(10)
    if m == 'hata':
        print('HAL=OLCULEMEDI sebep=d1 rc=4'); sys.exit(4)
    print('HAL=KUYRUKTA is=1 rc=0'); sys.exit(0)
if '--log' in a:
    with open(a[a.index('--log') + 1], 'a') as f:
        f.write('HAL=MOCK {etiket}' + chr(10))
print('SURUM={etiket}')
sys.exit(int(os.environ.get('MOCK_RC', '0')))
""".encode()


def _git(kok, *args):
    sentetik_git(str(kok), *args, check=True, capture_output=True, text=True)


def _kur(kok):
    bare = kok / "bare.git"
    bare.mkdir()
    _git(bare, "init", "-q", "--bare", "--initial-branch=main")
    ana = kok / "ana"
    (ana / "tools").mkdir(parents=True)
    (ana / "shop").mkdir()
    (ana / "tools" / "foto-uretec-kosucu.py").write_bytes(_mock("v1"))
    # Yoklama arsivinin dort dosyasi (tam agacin ~232 KB'lik dilimi) — sarmalayici bunlari ister.
    (ana / "shop" / "wrangler.toml").write_text('name = "sahte"\n', encoding="utf-8")
    (ana / "shop" / "wrangler.onizleme.toml").write_text('name = "sahte-onizleme"\n', encoding="utf-8")
    (ana / "foto-uretim-veri.js").write_text("module.exports = { turler: [] };\n", encoding="utf-8")
    _git(ana, "init", "-q", "-b", "main")
    _git(ana, "config", "user.name", "t")
    _git(ana, "config", "user.email", "t@example.invalid")
    _git(ana, "add", ".")
    _git(ana, "commit", "-q", "-m", "v1")
    _git(ana, "remote", "add", "origin", str(bare))
    _git(ana, "push", "-q", "origin", "main")
    # ikinci klon origin/main'i v3'e ilerletir; ana checkout GERIDE kalir
    klon = kok / "klon"
    _git(kok, "clone", "-q", str(bare), str(klon))
    _git(klon, "config", "user.name", "t")
    _git(klon, "config", "user.email", "t@example.invalid")
    (klon / "tools" / "foto-uretec-kosucu.py").write_bytes(_mock("v3"))
    _git(klon, "commit", "-q", "-am", "v3")
    _git(klon, "push", "-q", "origin", "main")
    # ana checkout KIRLI (commit'siz v2)
    (ana / "tools" / "foto-uretec-kosucu.py").write_bytes(_mock("v2"))
    return ana


def _kos(wrapper, ana, tmp, log, rc=None, yoklama=None):
    env = dict(os.environ, PRUVO_KOSUCU_ANA=str(ana), PRUVO_KOSUCU_D_KOK=str(tmp),
               PRUVO_KOSUCU_D_DESEN=DESEN)
    if rc is not None:
        env["MOCK_RC"] = str(rc)
    if yoklama is not None:
        env["MOCK_YOKLAMA"] = yoklama
    return subprocess.run(["bash", str(wrapper), "--uygula", "--log", str(log)],
                          capture_output=True, text=True, env=env)


def _agac_log(log):
    satirlar = log.read_text().splitlines() if log.exists() else []
    agac = [x for x in satirlar if "AGAC=" in x]
    return agac[-1] if agac else ""


def _silindi_kb(son):
    for parca in son.split():
        if parca.startswith("SILINDI="):
            return int(parca.split("=", 1)[1].replace("KB", "") or 0)
    return -1


def _bos_sayi(tmp):
    yol = tmp / ("%s-durum-canli.txt" % DESEN)
    return yol.read_text().strip() if yol.exists() else ""


def iddialari_kos(wrapper):
    """{etiket: (gecti, ayrinti)} — her iddia grubu kendi izole kokunu kurar ve siler."""
    s = {}
    kok = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-test-"))
    try:
        ana = _kur(kok)
        tmp = kok / "tmp"
        tmp.mkdir()
        log = kok / "kosucu.log"
        p = _kos(wrapper, ana, tmp, log)
        s["I1"] = ("SURUM=v3" in p.stdout and p.returncode == 0, p.stdout.strip() + p.stderr.strip())
        son = _agac_log(log)
        yol = son.split("AGAC=", 1)[1].split(" ", 1)[0] if "AGAC=" in son else ""
        art = sorted(x.name for x in tmp.iterdir() if x.name.endswith(".noindex"))
        s["I2"] = (bool(yol) and "SILINDI=" in son and "KB" in son and not Path(yol).exists()
                   and not art, "%s art=%s" % (son, art))
        satirlar = log.read_text().splitlines() if log.exists() else []
        s["I4"] = (any(x.startswith("HAL=MOCK") for x in satirlar), "log=%r" % satirlar)
        s["I9"] = (yol.endswith(".noindex") and "YOKLAMA=is" in p.stdout
                   and "SURUM=v3" in p.stdout, "yol=%s" % yol)
        p4 = _kos(wrapper, ana, tmp, log, rc=4)
        s["I3"] = (p4.returncode == 4, "rc=%d" % p4.returncode)
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    # I5/I6 — her biri kendi izole koku (durum sayaci sifirdan)
    for ad, yoklama, bekle_rc, bekle_son in (("I5", "bos", 0, "HAL=BOS rc=0"), ("I6", "hata", 4, None)):
        kok = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-test-"))
        try:
            ana = _kur(kok)
            tmp = kok / "tmp"
            tmp.mkdir()
            log = kok / "kosucu.log"
            p = _kos(wrapper, ana, tmp, log, yoklama=yoklama)
            son = _agac_log(log)
            kalan = [x.name for x in tmp.iterdir() if x.name.endswith(".noindex")]
            kosul = (p.returncode == bekle_rc and "SURUM=" not in p.stdout and not kalan
                     and _silindi_kb(son) < 1024)
            if bekle_son is not None:
                kosul = kosul and p.stdout.strip().splitlines()[-1:] == [bekle_son]
            s[ad] = (kosul, "rc=%d kb=%d art=%s out=%r" % (p.returncode, _silindi_kb(son), kalan,
                                                          p.stdout.strip()[-120:]))
        finally:
            shutil.rmtree(kok, ignore_errors=True)

    # I7/I8 — ayni izole kok, sirali (durum sayaci zaman icinde olusur)
    kok = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-test-"))
    try:
        ana = _kur(kok)
        tmp = kok / "tmp"
        tmp.mkdir()
        log = kok / "kosucu.log"
        for _ in range(3):
            _kos(wrapper, ana, tmp, log, yoklama="bos")
        durum3 = _bos_sayi(tmp)
        p = _kos(wrapper, ana, tmp, log, yoklama="bos")
        satirlar = p.stdout.strip().splitlines()
        s["I7"] = (durum3.startswith("bos=3") and "YOKLAMA=" not in p.stdout and p.returncode == 0
                   and satirlar[-1:] == ["HAL=BOS rc=0"] and "aralik=600s" in p.stdout,
                   "durum=%r out=%r" % (durum3, p.stdout.strip()[-160:]))
        # Geri cekilme penceresi gecmis sayilir (700 sn > 600): yoklama YINE calisir ve is
        # gorulunce sayac sifirlanir -> aralik 120'ye doner.
        durum = tmp / ("%s-durum-canli.txt" % DESEN)
        durum.write_text("bos=3 son=%d\n" % (int(time.time()) - 700), encoding="utf-8")
        pi = _kos(wrapper, ana, tmp, log, yoklama="is")
        durum0 = _bos_sayi(tmp)
        s["I8"] = (durum0.startswith("bos=0") and "YOKLAMA=is" in pi.stdout
                   and "KOSUCU_ERTELENDI" not in pi.stdout and "SURUM=v3" in pi.stdout,
                   "durum=%r out=%r" % (durum0, pi.stdout.strip()[-160:]))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return s


MUTANTLAR = [
    ("M1 archive origin/main yerine HEAD",
     [('archive "$SHA"', 'archive HEAD')], ["I1"]),
    ("M2 kosucu ana checkout'tan calistirilir",
     [('python3 "$D/tools/', 'python3 "$ANA_KOK/tools/'),
      ('python3 "$D/tools/', 'python3 "$ANA_KOK/tools/')], ["I1"]),
    ("M3 fetch yapilmaz (bayat origin/main)",
     [('fetch -q origin main', 'fetch -q origin YOK-DAL')], ["I1"]),
    ("M4 cikista gecici dizin silinmez",
     [('    if [[ -n "$D" ]]; then rm -rf "$D"; fi\n', '')], ["I2"]),
    ("M5 ic rc yutulur",
     [('exit $RC', 'exit 0')], ["I3"]),
    ("M6 --log ic kosucudan sokulur",
     [('        ARGS+=("$1" "$2")\n', '')], ["I4"]),
    ("M7 BOS'ta tam agac yine de acilir",
     [('if [[ "$BOS_ERKEN_CIKIS" == "1" ]]; then\n    exit 0\nfi', '')], ["I5"]),
    ("M8 yoklama hatasi BOS sayilir (fail-closed kirilir)",
     [('        exit "$YOKLAMA_RC"',
       '        durum_yaz "$((BOS_SAYISI + 1))"\n        BOS_ERKEN_CIKIS=1')], ["I6"]),
]


def mutant_kos(yama, beklenen):
    kaynak = WRAPPER.read_text()
    for bul, koy in yama:
        if bul not in kaynak:
            return False, "MUTASYON UYGULANAMADI: %r" % bul
        kaynak = kaynak.replace(bul, koy, 1)
    d = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-mutant-"))
    try:
        kopya = d / "kosucu-gecici-agac.sh"
        kopya.write_text(kaynak)
        s = iddialari_kos(kopya)
        hayatta = [e for e in beklenen if s[e][0]]
        return not hayatta, ("hayatta: %s" % ",".join(hayatta)) if hayatta else "kirmizi: %s" % ",".join(beklenen)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    s = iddialari_kos(WRAPPER)
    gecen = 0
    for e in ("I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9"):
        gecti, ayrinti = s[e]
        gecen += int(gecti)
        print("%s %s%s" % ("GECTI" if gecti else "KALDI", e, "" if gecti else " — " + ayrinti))
    print("SONUC %d/%d" % (gecen, 9))
    if gecen != 9:
        print("MUTASYON ATLANDI: taban kirmizi (kirmizi tabanda mutant olumu kanit degildir)")
        return 1
    olen = 0
    for ad, yama, beklenen in MUTANTLAR:
        oldu, ayrinti = mutant_kos(yama, beklenen)
        olen += int(oldu)
        print("%s %s (%s)" % ("OLDU  " if oldu else "KALDI ", ad, ayrinti))
    print("MUTANT %d/%d OLDU" % (olen, len(MUTANTLAR)))
    return 0 if olen == len(MUTANTLAR) else 1


if __name__ == "__main__":
    sys.exit(main())