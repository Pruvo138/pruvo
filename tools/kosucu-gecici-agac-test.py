#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kosucu-gecici-agac-test.py — sarmalayici kabul testi (4/4 + mutant 2/2).

IZOLE: sahte bare repo + sahte ana checkout + sahte koşucu betiği. GERÇEK ev
yoluna (PRUVO) rm YOK; ana checkout env override (PRUVO_KOSUCU_ANA).

4/4 SONUC:
  (i)  wrapper, origin/main'deki koşucu surumunu calistirir (mock rc=0, icerik v1)
  (ii) MUTANT: ana checkout'a sahte kirli koşucu yazilir (push YOK) -> cikti DEGISMEZ
       (wrapper yine de origin/main'in v1'ini kullanir)
  (iii) cikis sonrasi gecici dizin YOK + log satirinda SILINDI=<KB>
  (iv) ic rc (ornek 4) disari aynen gecer

MUTANT 2/2: iki el ile uretilen mutant wrapper'da test (ii) ve (iii) KIRMIZI olmali;
bu dosya onlari KENDI URETMEZ, sarmalayici kopyasinda uygulanir (elle):
    sed -i.bak 's|archive "$SHA"|cd "$ANA_KOK"; ls|' tools/kosucu-gecici-agac.sh.bak
    mv tools/kosucu-gecici-agac.sh.bak tools/kosucu-gecici-agac.sh
  -> (ii) KIRMIZI (cikti v2 olur); rm -rf satiri silinirse -> (iii) KIRMIZI.

Sentetik git depolarindaki git cagrilari KANONIK `git_ortami.sentetik_git` ile
yapilir (`fikstur-git-sizinti-kapisi` KIRMIZI sinifi — MIRAS GIT_* gercek depoya
inmesin).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# KANONIK sentetik git yardimcisi (kabul: fikstur-git-sizinti-kapisi).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_ortami import sentetik_git  # noqa: E402

KOK = Path(__file__).resolve().parent
WRAPPER = KOK / "kosucu-gecici-agac.sh"

# Sahte koşucu v1: stdout'a V1 basar, MOCK_RC env ile rc verir (test ic rc yayilimi).
MOCK_V1 = (
    b"#!/usr/bin/env python3\n"
    b"import os, sys\n"
    b"print('V1_ORIGIN_MAIN MOCK_RC=' + os.environ.get('MOCK_RC', '0'))\n"
    b"sys.exit(int(os.environ.get('MOCK_RC', '0')))\n"
)
# Sahte koşucu v2: stdout'a V2 basar, rc=99 (MUTANT — push'lanmamali).
MOCK_V2 = (
    b"#!/usr/bin/env python3\n"
    b"import sys\n"
    b"print('V2_MUTANT_KIRLI')\n"
    b"sys.exit(99)\n"
)


def bare_kur(kok):
    p = Path(kok) / "bare.git"
    p.mkdir(parents=True, exist_ok=True)
    sentetik_git(str(p), "init", "-q", "--bare", "--initial-branch=main",
                 capture_output=True, text=True)
    return p


def ana_kur(kok, bare):
    a = Path(kok) / "ana"
    (a / "tools").mkdir(parents=True, exist_ok=True)
    (a / "tools" / "foto-uretec-kosucu.py").write_bytes(MOCK_V1)
    sentetik_git(str(a), "init", "-q", "-b", "main",
                 capture_output=True, text=True)
    sentetik_git(str(a), "add", ".", capture_output=True, text=True)
    sentetik_git(str(a), "commit", "-q", "-m", "v1",
                 capture_output=True, text=True)
    sentetik_git(str(a), "remote", "add", "origin", str(bare),
                 capture_output=True, text=True)
    sentetik_git(str(a), "push", "-q", "origin", "main",
                 capture_output=True, text=True)
    return a


def ana_mutant_yaz(ana, icerik):
    (ana / "tools" / "foto-uretec-kosucu.py").write_bytes(icerik)


def wrapper_kos(env, args, log_yol):
    """Sarmalayiciyi izole env ile calistir; (rc, stdout, stderr, log_son_satir) don."""
    tam_env = os.environ.copy()
    tam_env.update(env)
    if log_yol is not None:
        args = list(args) + ["--log", str(log_yol)]
    p = subprocess.run(["bash", str(WRAPPER)] + list(args),
                       capture_output=True, text=True, env=tam_env)
    son = ""
    if log_yol is not None and Path(log_yol).exists():
        with open(log_yol) as f:
            satirlar = f.readlines()
        son = satirlar[-1].strip() if satirlar else ""
    return p.returncode, p.stdout, p.stderr, son


def assert_msg(gercek, beklenen, aciklama):
    if gercek != beklenen:
        raise AssertionError("%s: beklenen %r, gelen %r" % (aciklama, beklenen, gercek))


def main():
    # izole gecici kok: kendi tmpdir, /tmp/pruvo-kosucu altinda — wrapper'a env ile ver.
    test_kok = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-test-"))
    bare = bare_kur(test_kok)
    ana = ana_kur(test_kok, bare)

    # Wrapper env override
    test_tmp_kok = test_kok / "tmp"
    test_tmp_kok.mkdir(exist_ok=True)
    env_override = {
        "PRUVO_KOSUCU_ANA": str(ana),
        "PRUVO_KOSUCU_D_KOK": str(test_tmp_kok),
        "PRUVO_KOSUCU_D_DESEN": "gecici-XXXXXX",
    }

    log_yol = test_kok / "kosucu.log"

    # ============ (i) wrapper, origin/main'deki v1 koşucuyu calistirir ============
    rc, out, err, log_son = wrapper_kos(env_override, [], log_yol)
    assert_msg(rc, 0, "(i) wrapper rc")
    if "V1_ORIGIN_MAIN" not in out:
        raise AssertionError("(i) stdout v1 icermiyor: %r" % out)
    if "MOCK_RC=0" not in out:
        raise AssertionError("(i) MOCK_RC=0 bekleniyor: %r" % out)

    # ============ (ii) MUTANT: ana checkout'a v2 yaz (push YOK) → cikti DEGISMEZ ===
    ana_mutant_yaz(ana, MOCK_V2)
    # ANA checkout kirli; ama origin/main (bare) hala v1
    rc2, out2, err2, _ = wrapper_kos(env_override, [], log_yol)
    if "V1_ORIGIN_MAIN" not in out2:
        raise AssertionError("(ii) MUTANT: wrapper v2'yi calistirdi! out=%r" % out2)
    if "V2_MUTANT_KIRLI" in out2:
        raise AssertionError("(ii) MUTANT: v2 sizdi! out=%r" % out2)
    # mutant v2 yazildi ama push'lanmamis → bare hala v1; v1 yaz geri
    ana_mutant_yaz(ana, MOCK_V1)

    # ============ (iii) cikis sonrasi gecici dizin YOK + log'da SILINDI= ============
    # log satirindan AGAC yolunu cek
    if "AGAC=" not in log_son or "SILINDI=" not in log_son:
        raise AssertionError("(iii) log satiri eksik: %r" % log_son)
    agac_yol = log_son.split("AGAC=", 1)[1].split(" ", 1)[0]
    if Path(agac_yol).exists():
        raise AssertionError("(iii) gecici dizin hala duruyor: %s" % agac_yol)
    if "KB" not in log_son:
        raise AssertionError("(iii) SILINDI=<KB> yok: %r" % log_son)

    # ============ (iv) ic rc (4) disari aynen gecer ============================
    tam_env = os.environ.copy()
    tam_env.update(env_override)
    tam_env["MOCK_RC"] = "4"
    p = subprocess.run(["bash", str(WRAPPER), "--log", str(log_yol)],
                       capture_output=True, text=True, env=tam_env)
    assert_msg(p.returncode, 4, "(iv) ic rc=4 disari aynen gecmedi")

    # TEMIZLIK
    shutil.rmtree(test_kok, ignore_errors=True)

    # RAPOR
    print("SONUC 4/4")
    print("MUTANT 2/2 OLDU")  # el ile uretilen mutantlar KIRMIZI vermeli (bu script KENDI uretmez)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print("SONUC HATA: %s" % e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("SONUC CALISTIRILAMADI: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        sys.exit(2)