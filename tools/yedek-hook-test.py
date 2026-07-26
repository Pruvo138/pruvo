#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — pre-push YEDEK BLOGU (tools/yedek-hook-kur.py).

NEDEN VAR — bu blogun iki oldurucu bozulma bicimi var, ikisi de SESSIZ:
  (A) FAIL-CLOSED'a kaymak: yedek patlar/Drive yoktur, blok exit!=0 doner ve PUSH DURUR.
      Yayini durduran bir yedek kabul edilemez (D1 senkron blogunun emsali de fail-open).
  (B) OLU KONUM: blok, D1 blogunun `exit 0`'larindan SONRAYA kayarsa cogu push'ta HIC
      CALISMAZ — hook "kurulu" gorunur, yedek yine alinmaz (tam da 26 Tem'de yasanan
      "arac dogru, kimse kosmuyor" hatasinin otomasyon kilikli hali).
Ikisinin de kaniti asagida; (A) icin Drive'i ERISILEMEZ yapan gercek bir mutasyonla.

Kosum:  python3 tools/yedek-hook-test.py
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(TOOLS, "yedek-hook-kur.py")
YEDEKLE = os.path.join(TOOLS, "yedekle.py")

# Drive'i ERISILEMEZ yapan mutasyon: yedekle.py'nin cozucusu daima None doner.
DRIVE_STUB = ('DESEN = "/olmayan-mount/*/STL"\n'
              'def stl_dizini(sessiz=False):\n    return None\n'
              'def pruvo_dizini(sessiz=False):\n    return None\n')

SONUC = []


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sahte_repo(td, drive_erisilebilir):
    """Gecici git deposu: tools/yedekle.py gercek, drive_yolu STUB."""
    kok = os.path.join(td, "repo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(YEDEKLE, os.path.join(kok, "tools", "yedekle.py"))
    govde = DRIVE_STUB
    if drive_erisilebilir:
        hedef = os.path.join(td, "drive", "Pruvo")
        os.makedirs(hedef)
        govde = ('DESEN = "/olmayan-mount/*/STL"\n'
                 'def stl_dizini(sessiz=False):\n    return %r\n'
                 'def pruvo_dizini(sessiz=False):\n    return %r\n'
                 % (os.path.join(hedef, "STL"), hedef))
    with open(os.path.join(kok, "tools", "drive_yolu.py"), "w") as f:
        f.write(govde)
    subprocess.run(["git", "-C", kok, "init", "-q"], capture_output=True)
    return kok


def hook_kos(kok, hook_metni):
    """Hook'u sahte repo icinde, pre-push stdin bicimiyle kosar."""
    yol = os.path.join(kok, "pre-push")
    with open(yol, "w") as f:
        f.write(hook_metni)
    os.chmod(yol, 0o755)
    return subprocess.run(
        ["sh", yol, "origin", "git@example.invalid:yok/yok.git"],
        input="refs/heads/dal aaa refs/heads/dal bbb\n",
        capture_output=True, text=True, cwd=kok)


def main():
    kur = modul_yukle(KUR, "yedek_hook_kur")
    blok_hook = "#!/bin/sh\n" + kur.BLOK + "\n"

    # ---------------- 1) URETILEN BLOK: idempotens ----------------
    print("\n1) IDEMPOTENS — iki kez kurmak ikinci kopya YIGMAMALI")
    bir, _ = kur.yeni_icerik(None)
    iki, eylem = kur.yeni_icerik(bir)
    kontrol("ikinci kurulum metni DEGISTIRMEDI", bir == iki, eylem)
    kontrol("blok tek kez geciyor", bir.count(kur.BAS) == 1)
    mevcut = "#!/bin/sh\n# D1 blogu\nexit 0\n"
    eklendi, _ = kur.yeni_icerik(mevcut)
    kontrol("mevcut hook'un govdesi KORUNDU", "# D1 blogu" in eklendi)
    kaldirildi, _ = kur.yeni_icerik(eklendi, kaldir=True)
    kontrol("--kaldir blogu cikarir, govde kalir",
            kur.BAS not in kaldirildi and "# D1 blogu" in kaldirildi)

    # ---------------- 2) KONUM — 'exit 0'lardan ONCE ----------------
    print("\n2) OLU KONUM NOBETI — blok erken 'exit 0'lardan ONCE olmali")
    kontrol("uretilen blok ilk 'exit 0'dan once",
            eklendi.index(kur.BAS) < eklendi.index("exit 0"))
    gercek = None
    p = subprocess.run(["git", "-C", TOOLS, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout.strip():
        yol = os.path.join(p.stdout.strip(), "hooks", "pre-push")
        if os.path.isfile(yol):
            with open(yol, errors="replace") as f:
                gercek = f.read()
    if gercek is None:
        kontrol("bu makinede pre-push kurulu", False, "hook yok — 'python3 tools/yedek-hook-kur.py' kos")
    else:
        kontrol("bu makinede blok KURULU", kur.BAS in gercek)
        if kur.BAS in gercek and "exit 0" in gercek:
            kontrol("kurulu blok ilk 'exit 0'dan ONCE (olu konum degil)",
                    gercek.index(kur.BAS) < gercek.index("exit 0"))
        kontrol("mevcut D1 blogu KORUNMUS", "d1-sync" in gercek)

    # ---------------- 3) FAIL-OPEN: Drive ERISILEMEZ mutasyonu ----------------
    print("\n3) KIRMIZI-MUTASYON (Drive erisilemez) — push yolu YINE DE exit 0 mi?")
    with tempfile.TemporaryDirectory() as td:
        kok = sahte_repo(td, drive_erisilebilir=False)
        r = hook_kos(kok, blok_hook)
        kontrol("Drive yokken hook exit 0 (PUSH DURMAZ)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, r.stderr.strip()[:100]))
        kontrol("basarisizlik SESSIZ degil (uyari basildi)",
                "YEDEK alinamadi" in r.stdout, r.stdout.strip()[:90])
        # Mutasyonun gercekten isirdigini kanitla: ayni yedekle.py dogrudan cagrilinca patlar.
        d = subprocess.run([sys.executable, os.path.join(kok, "tools", "yedekle.py"),
                            "--gerekliyse"], capture_output=True, text=True)
        kontrol("MUTASYON ISIRIYOR: yedekle.py tek basina exit!=0 veriyor",
                d.returncode != 0, "rc=%d" % d.returncode)

    # ---------------- 4) POZITIF KONTROL: Drive varken de exit 0, uyari YOK ----------------
    print("\n4) POZITIF — Drive erisilebilirken uyari basilmamali")
    with tempfile.TemporaryDirectory() as td:
        kok = sahte_repo(td, drive_erisilebilir=True)
        r = hook_kos(kok, blok_hook)
        kontrol("hook exit 0", r.returncode == 0, "rc=%d" % r.returncode)
        kontrol("uyari YOK (yedek basarili)", "YEDEK alinamadi" not in r.stdout,
                r.stdout.strip()[:90])
        kontrol("damga yazildi (yedek gercekten kosdu)",
                os.path.isfile(os.path.join(td, "drive", "Pruvo", "backup", ".son-yedek.json")))

    # ---------------- 5) BLOK ICINDE 'exit' OLMAMALI ----------------
    print("\n5) YAPISAL — blok push'u kesecek 'exit' ICERMEMELI")
    govde = [s.strip() for s in kur.BLOK.splitlines()
             if s.strip() and not s.strip().startswith("#")]
    kontrol("blokta 'exit' yok", not any(s.startswith("exit") or " exit " in s for s in govde))
    kontrol("cagri hata yutucu ile sarili", any("|| true" in s or "if !" in s for s in govde))

    kirmizi = [a for a, ok in SONUC if not ok]
    print("\n" + "=" * 70)
    print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    for a in kirmizi:
        print("  ❌ " + a)
    print("SONUC: " + ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
