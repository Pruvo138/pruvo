#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ekle-sahiplik-test.py — urunler-guard EKLE SAHIPLIGI kabulu.

NE OLCER (8 Eki 2026): ana checkout'ta A evinin yeni kaydi stage'deyken B evi
kendi kaydini ekleyip commit edince guard rc=0 veriyordu (taban olculdu:
`TABAN_EKLE_SAHIPLIK=REDDETMIYOR`) — B'nin commit'i A'nin kaydini SESSIZCE
tasiyordu. Guard artik INDEX'teki yeni id'leri `.urunler-ekle-izin.json`
({"ev", "idler"}) beyanina ve commit eden eve (`PRUVO_EV` / dal oneki) baglar.

GERCEK VERIYE DOKUNMAZ: her vaka kendi gecici git deposunu kurar; fikstur
urunleri SAHTEDIR. Ag YOK. Gecici dizinler vaka sonunda silinir.

KABUL = TAM 14 `IDDIA:` satiri, kirmizi=0 (olculemeyen iddia KIRMIZI basilir).

Kullanim:
    python3 tools/ekle-sahiplik-test.py                    # vakalar
    python3 tools/ekle-sahiplik-test.py --kaynak <guard>   # mutasyonlu guard'i olc
    python3 tools/ekle-sahiplik-test.py --mutant           # vakalar + mutant turu
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_GUARD = os.path.join(TOOLS, "urunler-guard.py")
EV_SAHIP = os.path.join(TOOLS, "ev-sahip-kapisi.py")
MANIFEST_ADI = ".urunler-ekle-izin.json"

KODLAR = [
    ("S1", "manifestli KENDI kaydi red kipinde GECER (rc=0, yabanci=0 manifestsiz=0)"),
    ("S2", "baska evin stage'deki kaydi rapor kipinde EKLE_SAHIPSIZ basar, rc=0"),
    ("S3", "baska evin stage'deki kaydi red kipinde rc=3, index+WT DEGISMEZ"),
    ("S4", "manifestsiz yeni id: VARSAYILAN (rapor) kipte EKLE_MANIFESTSIZ n=2, rc=0"),
    ("S5", "manifestsiz yeni id: red kipinde rc=3, veri DEGISMEZ"),
    ("S6", "ev uyusmazligi (manifest MaCiT, PRUVO_EV=TeKiN) red: rc=3 + EKLE_YABANCI"),
    ("S7", "ev uyusmazligi rapor kipinde: rc=0 + EKLE_YABANCI + teftis yabanci=1"),
    ("S8", "commit eden ev DAL ONEKINDEN turer: tekin/ dali + TeKiN manifesti GECER"),
    ("S9", "dal oneki manifestle uyusmazsa (macit/ dali, TeKiN manifesti) red rc=3"),
    ("S10", "merge hali: MERGE_HEAD'in getirdigi id YENI sayilmaz (red, manifestsiz rc=0)"),
    ("S11", "merge hali: iki ebeveynde de olmayan id YENI sayilir (red, manifestsiz rc=3)"),
    ("S12", "yalniz WT'de (stage'siz) yeni id commit'e girmez -> sayilmaz (red rc=0)"),
    ("S13", "her kosumda TEK teftis satiri: EKLE_SAHIPLIK=RAPOR yabanci=0 manifestsiz=0"),
    ("S14", "--ekle-tuket: commit'e girmis beyan SILINIR, bekleyen beyan KORUNUR"),
]
DEFTER = {}

# Mutantlar: (ad, capa, yerine). Capa kaynakta TAM 1 kez gecmezse mutant
# OLCULEMEDI sayilir (KIRMIZI) — yanlis yere nisanlanan mutant yesil uretmez.
MUTANTLAR = [
    ("yabanci-id-denetimi-silindi",
     'sahipsiz = [u for u in yeni_idler if u not in manifest["idler"]]',
     "sahipsiz = []"),
    ("red-kipi-rapora-dustu",
     'red_kip = kip_ham == "red"',
     "red_kip = False"),
    ("ev-uyusmazligi-kor",
     'if commit_ev != manifest["ev"]:',
     "if False:"),
    ("manifestsiz-kor",
     "manifestsiz = len(yeni_idler)",
     "manifestsiz = 0"),
]

SIZINTI_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
               "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")
ORTAM_SIL = SIZINTI_ENV + ("PRUVO_EV", "PRUVO_EKLE_SAHIPLIK", "PRUVO_GUARD_ZORLA")


def iddia(kod, kosul, ayrinti=""):
    DEFTER[kod] = (bool(kosul), ayrinti)


def _env(**ek):
    e = {k: v for k, v in os.environ.items() if k not in ORTAM_SIL}
    e.update(GIT_AUTHOR_NAME="Kabul", GIT_AUTHOR_EMAIL="kabul@pruvo.test",
             GIT_COMMITTER_NAME="Kabul", GIT_COMMITTER_EMAIL="kabul@pruvo.test",
             GIT_AUTHOR_DATE="2026-10-08T00:00:00", GIT_COMMITTER_DATE="2026-10-08T00:00:00")
    e.update(ek)
    return e


def _urun(uid):
    return {"id": uid, "kategori": "Ev", "baslik": "Sahte %s" % uid,
            "fiyat": "100 TL", "gorseller": ["https://media.pruvo3d.com/urunler/%s.jpg" % uid]}


def g(kok, *a):
    p = subprocess.run(["git", "-C", kok, *a], capture_output=True, text=True, env=_env())
    return p.returncode, p.stdout + p.stderr


def yaz(kok, ids):
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([_urun(i) for i in ids], f, ensure_ascii=False, indent=2)


def stage(kok, ids):
    yaz(kok, ids)
    g(kok, "add", "urunler.json")


def manifest(kok, ev, idler):
    with open(os.path.join(kok, MANIFEST_ADI), "w", encoding="utf-8") as f:
        json.dump({"ev": ev, "idler": idler}, f)


def iz(kok):
    """(WT sha, INDEX sha) — veri degismedi mi olcumu."""
    with open(os.path.join(kok, "urunler.json"), "rb") as f:
        wt = hashlib.sha256(f.read()).hexdigest()
    return wt, g(kok, "rev-parse", ":urunler.json")[1].strip()


DEPOLAR = []


def kur(guard, dal="main"):
    d = tempfile.mkdtemp(prefix="ekle-sahiplik-")
    DEPOLAR.append(d)
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy(guard, os.path.join(d, "tools", "urunler-guard.py"))
    shutil.copy(EV_SAHIP, os.path.join(d, "tools", "ev-sahip-kapisi.py"))
    g(d, "init", "-q", "-b", dal)
    g(d, "config", "commit.gpgsign", "false")
    yaz(d, ["eski-1", "eski-2"])
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "taban")
    return d


def kos(kok, tetik="commit", **ek):
    p = subprocess.run([sys.executable, os.path.join(kok, "tools", "urunler-guard.py"),
                        "--tetik", tetik], capture_output=True, text=True, env=_env(**ek))
    return p.returncode, p.stderr


def teftis(err):
    return [s for s in err.splitlines() if s.startswith("EKLE_SAHIPLIK=")]


# ------------------------------------------------------------------- vakalar
def v_kendi_kaydi(guard):
    d = kur(guard)
    stage(d, ["m-1", "eski-1", "eski-2"])
    manifest(d, "MaCiT", ["m-1"])
    rc, err = kos(d, PRUVO_EV="MaCiT", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S1", rc == 0 and teftis(err) == ["EKLE_SAHIPLIK=RED yabanci=0 manifestsiz=0"],
          "rc=%d teftis=%s" % (rc, teftis(err)))


def v_yabanci_id(guard):
    d = kur(guard)
    stage(d, ["m-1", "eski-1", "eski-2"])            # MaCiT stage'ledi
    stage(d, ["t-1", "m-1", "eski-1", "eski-2"])     # TeKiN kendi kaydini ekledi
    manifest(d, "TeKiN", ["t-1"])
    rc, err = kos(d, PRUVO_EV="TeKiN")
    iddia("S2", rc == 0 and "EKLE_SAHIPSIZ id=m-1" in err
          and "EKLE_SAHIPSIZ id=t-1" not in err
          and teftis(err) == ["EKLE_SAHIPLIK=RAPOR yabanci=1 manifestsiz=0"],
          "rc=%d teftis=%s" % (rc, teftis(err)))
    once = iz(d)
    rc, err = kos(d, PRUVO_EV="TeKiN", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S3", rc == 3 and "EKLE_SAHIPSIZ id=m-1" in err and iz(d) == once,
          "rc=%d veri_ayni=%s" % (rc, iz(d) == once))


def v_manifestsiz(guard):
    d = kur(guard)
    stage(d, ["a-1", "b-1", "eski-1", "eski-2"])
    rc, err = kos(d, PRUVO_EV="KraL")                 # kip env'i YOK -> varsayilan
    iddia("S4", rc == 0 and "EKLE_MANIFESTSIZ n=2" in err
          and teftis(err) == ["EKLE_SAHIPLIK=RAPOR yabanci=0 manifestsiz=2"],
          "rc=%d teftis=%s" % (rc, teftis(err)))
    once = iz(d)
    rc, err = kos(d, PRUVO_EV="KraL", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S5", rc == 3 and iz(d) == once, "rc=%d veri_ayni=%s" % (rc, iz(d) == once))


def v_ev_uyusmazligi(guard):
    d = kur(guard)
    stage(d, ["m-1", "eski-1", "eski-2"])
    manifest(d, "MaCiT", ["m-1"])
    once = iz(d)
    rc, err = kos(d, PRUVO_EV="TeKiN", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S6", rc == 3 and "EKLE_YABANCI manifest_ev=MaCiT commit_ev=TeKiN" in err
          and iz(d) == once, "rc=%d veri_ayni=%s" % (rc, iz(d) == once))
    rc, err = kos(d, PRUVO_EV="TeKiN")
    iddia("S7", rc == 0 and "EKLE_YABANCI" in err
          and teftis(err) == ["EKLE_SAHIPLIK=RAPOR yabanci=1 manifestsiz=0"],
          "rc=%d teftis=%s" % (rc, teftis(err)))


def v_dal_oneki(guard):
    d = kur(guard, dal="tekin/parti")
    stage(d, ["t-1", "eski-1", "eski-2"])
    manifest(d, "TeKiN", ["t-1"])
    rc, err = kos(d, PRUVO_EKLE_SAHIPLIK="red")
    iddia("S8", rc == 0 and teftis(err) == ["EKLE_SAHIPLIK=RED yabanci=0 manifestsiz=0"],
          "rc=%d teftis=%s" % (rc, teftis(err)))
    g(d, "checkout", "-q", "-b", "macit/parti")
    rc, err = kos(d, PRUVO_EKLE_SAHIPLIK="red")
    iddia("S9", rc == 3 and "commit_ev=MaCiT(dal)" in err, "rc=%d" % rc)


def v_merge(guard):
    d = kur(guard)
    g(d, "branch", "dal")
    yaz(d, ["main-yeni", "eski-1", "eski-2"])
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "main yeni urun")
    g(d, "checkout", "-q", "dal")
    with open(os.path.join(d, "dal-isi.md"), "w") as f:
        f.write("dal\n")
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "dal isi")
    mrc, mout = g(d, "merge", "--no-commit", "--no-ff", "main")
    rc, err = kos(d, PRUVO_EV="KraL", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S10", mrc == 0 and rc == 0
          and teftis(err) == ["EKLE_SAHIPLIK=RED yabanci=0 manifestsiz=0"],
          "merge_rc=%d rc=%d teftis=%s" % (mrc, rc, teftis(err)))
    stage(d, ["merge-ici-yeni", "main-yeni", "eski-1", "eski-2"])
    rc, err = kos(d, PRUVO_EV="KraL", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S11", rc == 3 and "EKLE_MANIFESTSIZ n=1" in err,
          "rc=%d teftis=%s" % (rc, teftis(err)))


def v_yalniz_wt(guard):
    d = kur(guard)
    yaz(d, ["wt-1", "eski-1", "eski-2"])             # stage YOK
    rc, err = kos(d, PRUVO_EV="KraL", PRUVO_EKLE_SAHIPLIK="red")
    iddia("S12", rc == 0 and teftis(err) == ["EKLE_SAHIPLIK=RED yabanci=0 manifestsiz=0"],
          "rc=%d teftis=%s" % (rc, teftis(err)))


def v_teftis(guard):
    d = kur(guard)
    rc, err = kos(d)
    iddia("S13", rc == 0 and teftis(err) == ["EKLE_SAHIPLIK=RAPOR yabanci=0 manifestsiz=0"],
          "rc=%d teftis=%s" % (rc, teftis(err)))


def v_tuket(guard):
    d = kur(guard)
    stage(d, ["m-1", "eski-1", "eski-2"])
    g(d, "commit", "-q", "--no-verify", "-m", "m-1")
    yol = os.path.join(d, MANIFEST_ADI)
    manifest(d, "MaCiT", ["m-1", "m-2"])             # m-2 henuz commit'lenmedi
    p1 = subprocess.run([sys.executable, os.path.join(d, "tools", "urunler-guard.py"),
                         "--ekle-tuket"], capture_output=True, env=_env())
    korundu = os.path.exists(yol)
    manifest(d, "MaCiT", ["m-1"])
    p2 = subprocess.run([sys.executable, os.path.join(d, "tools", "urunler-guard.py"),
                         "--ekle-tuket"], capture_output=True, env=_env())
    iddia("S14", p1.returncode == 0 and p2.returncode == 0 and korundu
          and not os.path.exists(yol),
          "bekleyen_korundu=%s tuketildi=%s" % (korundu, not os.path.exists(yol)))


VAKALAR = [v_kendi_kaydi, v_yabanci_id, v_manifestsiz, v_ev_uyusmazligi,
           v_dal_oneki, v_merge, v_yalniz_wt, v_teftis, v_tuket]


def vakalar(guard):
    for fn in VAKALAR:
        try:
            fn(guard)
        except Exception as e:
            print("  ! vaka %s coktu: %r" % (fn.__name__, e))
    kirmizi = 0
    for kod, aciklama in KODLAR:
        ok, ayrinti = DEFTER.get(kod, (False, "OLCULEMEDI"))
        kirmizi += 0 if ok else 1
        print("IDDIA: %s %s %s%s" % (kod, "YESIL" if ok else "KIRMIZI", aciklama,
                                     ("  |  " + ayrinti) if ayrinti else ""))
    gecen = len(KODLAR) - kirmizi
    print("TOPLAM: iddia=%d kirmizi=%d TEST=%d/%d" % (len(KODLAR), kirmizi, gecen, len(KODLAR)))
    return kirmizi


def mutant_turu(guard):
    with open(guard, encoding="utf-8") as f:
        kaynak = f.read()
    kirmizi = 0
    gecici = tempfile.mkdtemp(prefix="ekle-sahiplik-mutant-")
    try:
        for ad, capa, yerine in MUTANTLAR:
            adet = kaynak.count(capa)
            if adet != 1:
                print("MUTANT: %s OLCULEMEDI capa_adedi=%d" % (ad, adet))
                continue
            yol = os.path.join(gecici, "urunler-guard.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, yerine))
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "--kaynak", yol],
                               capture_output=True, text=True, env=_env())
            yakalandi = p.returncode != 0
            kirmizi += 1 if yakalandi else 0
            kirmizilar = [s.split()[1] for s in p.stdout.splitlines()
                          if s.startswith("IDDIA:") and " KIRMIZI " in s]
            print("MUTANT: %s %s kirmizi_iddialar=%s"
                  % (ad, "KIRMIZI" if yakalandi else "SURVIVOR", ",".join(kirmizilar)))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print("MUTANT=%d/%d SURVIVOR=%d" % (kirmizi, len(MUTANTLAR), len(MUTANTLAR) - kirmizi))
    return kirmizi == len(MUTANTLAR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak", default=VARSAYILAN_GUARD)
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()
    print("URUNLER-GUARD EKLE SAHIPLIGI KABULU  guard=%s" % a.kaynak)
    try:
        kirmizi = vakalar(a.kaynak)
    finally:
        for d in DEPOLAR:
            shutil.rmtree(d, ignore_errors=True)
    ok = kirmizi == 0
    if a.mutant:
        ok = mutant_turu(a.kaynak) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
