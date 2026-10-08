#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""izin-manifest-tuket.py — post-commit: izin manifestlerinden YALNIZ TUKETILEN girdileri sil.

NEDEN VAR (7 Eki 2026, olculdu, 2 vaka): iki ev ayni urunler.json'a yaziyordu. A
`duzelt.py` ile .urunler-duzelt-izin.json'a izin yazdi, commit'lemeden B kendi commit'ini
atti -> post-commit uc manifesti KOSULSUZ `rm -f` etti -> urunler-guard A'nin duzeltmesini
"izinsiz" sayip HEAD'e geri aldi (yazim kaybi). Artik post-commit bu araci cagirir ve
her manifestten yalniz yeni HEAD'de TUKETILMIS girdiler cikar:

  duzelt  {id: {alan: deger | {"__alan_sil__": true}}}
          alan TUKETILDI <=> HEAD'deki kaydin o alani manifest degerine ESIT
          (alan silme: HEAD kaydinda alan YOK). Alan duzeyinde cikarilir; bos kalan id duser.
  sil     [id, ...]
          TUKETILDI <=> id HEAD'de YOK.
          🔴 Silme manifesti DEGER-bagli DEGIL, id-bagli genel izindir (guard yalniz
          `uid in sil_izin` bakar). Bu yuzden TUKETILMEMIS girdi YALNIZ working-tree'de o id
          FIILEN silinmis duruyorsa (bekleyen, commit'lenmemis silme) YASAR; working-tree'de
          id duruyorsa girdi BAYATTIR ve duser (eski kosulsuz temizlikle ayni sonuc). Boylece
          kalan girdi zaten var olan silmeden baska bir seyi mesrulastiramaz.
  rename  {eski: yeni}
          TUKETILDI <=> yeni HEAD'de VAR ve eski HEAD'de YOK. (Guard rename'i yapisal olarak
          dogrular: hedef kayit eski kaydin id disinda bayt-anlamsal kopyasi olmali.)

Kalan girdi varsa dosya kalan girdilerle ATOMIK yeniden yazilir (tmp + os.replace,
.urunler.lock flock altinda); hic girdi kalmadiysa dosya silinir.

FAIL-SAFE: HEAD okunamaz/bozuk, manifest bozuk/beklenmeyen tip, kilit alinamaz veya
herhangi bir istisna -> O DOSYAYA DOKUNULMAZ (izin yasar; guard deger-bagli okur).
Cikis kodu her zaman 0 (post-commit commit'i geri alamaz); ozet stderr'e yazilir.

Kullanim:  python3 tools/izin-manifest-tuket.py --kok <worktree koku>
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time

DUZELT = ".urunler-duzelt-izin.json"
SIL = ".urunler-sil-izin.json"
RENAME = ".urunler-id-rename-izin.json"
LOCK = ".urunler.lock"
KILIT_SURE = 30.0


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _bas(msg):
    print("izin-manifest-tuket: %s" % msg, file=sys.stderr)


def _katalog_head(kok):
    """HEAD:urunler.json -> {id: kayit} (tekrarlanan id'ler ayri kumede) | None."""
    try:
        p = subprocess.run(["git", "-C", kok, "show", "HEAD:urunler.json"],
                           capture_output=True, timeout=30)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    try:
        liste = json.loads(p.stdout.decode("utf-8"))
    except ValueError:
        return None
    if not isinstance(liste, list):
        return None
    return _by_id(liste)


def _katalog_wt(kok):
    try:
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            liste = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(liste, list):
        return None
    return _by_id(liste)


def _by_id(liste):
    by_id, tekrar = {}, set()
    for p in liste:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            if p["id"] in by_id:
                tekrar.add(p["id"])
            by_id[p["id"]] = p
    return by_id, tekrar


def _oku(yol):
    """(durum, veri): ("yok", None) | ("var", obj) | ("bozuk", None)."""
    if not os.path.exists(yol):
        return "yok", None
    try:
        with open(yol, encoding="utf-8") as f:
            return "var", json.load(f)
    except (OSError, ValueError):
        return "bozuk", None


def _yaz(yol, obj):
    tmp = yol + ".tmp-" + str(os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, yol)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def tuket_duzelt(m, head):
    """(kalan, tuketilen_sayisi) | None (tip beklenmedik -> dokunma)."""
    if not isinstance(m, dict):
        return None
    by_id, tekrar = head
    kalan, n = {}, 0
    for uid, alanlar in m.items():
        if not isinstance(alanlar, dict):
            kalan[uid] = alanlar
            continue
        kayit = by_id.get(uid) if uid not in tekrar else None
        yeni = {}
        for alan, deger in alanlar.items():
            tuketildi = False
            if kayit is not None:
                if isinstance(deger, dict) and deger.get("__alan_sil__") is True:
                    tuketildi = alan not in kayit
                else:
                    tuketildi = alan in kayit and _canon(kayit[alan]) == _canon(deger)
            if tuketildi:
                n += 1
            else:
                yeni[alan] = deger
        if yeni:
            kalan[uid] = yeni
    return kalan, n


def tuket_sil(m, head, wt):
    if not isinstance(m, list):
        return None
    by_id, _ = head
    kalan, n = [], 0
    for uid in m:
        if not isinstance(uid, str):
            kalan.append(uid)
            continue
        if uid not in by_id:
            n += 1  # tuketildi
        elif wt is not None and uid not in wt[0]:
            kalan.append(uid)  # bekleyen silme: WT'de fiilen silinmis
        elif wt is None:
            kalan.append(uid)  # WT okunamadi -> fail-safe: yasat
        else:
            n += 1  # BAYAT: WT'de id duruyor, id-bagli izin yasatilmaz
    return kalan, n


def tuket_rename(m, head):
    if not isinstance(m, dict):
        return None
    by_id, _ = head
    kalan, n = {}, 0
    for eski, yeni in m.items():
        if isinstance(yeni, str) and yeni in by_id and eski not in by_id:
            n += 1
        else:
            kalan[eski] = yeni
    return kalan, n


def _isle(kok, ad, fn):
    yol = os.path.join(kok, ad)
    durum, veri = _oku(yol)
    if durum == "yok":
        return
    if durum == "bozuk":
        _bas("%s BOZUK — dokunulmadi" % ad)
        return
    sonuc = fn(veri)
    if sonuc is None:
        _bas("%s beklenmeyen tip — dokunulmadi" % ad)
        return
    kalan, n = sonuc
    if n == 0:
        _bas("%s tuketilen=0 kalan=%d" % (ad, len(kalan)))
        return
    if kalan:
        _yaz(yol, kalan)
    else:
        os.remove(yol)
    _bas("%s tuketilen=%d kalan=%d%s" % (ad, n, len(kalan), "" if kalan else " (silindi)"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", required=True)
    args = ap.parse_args(argv)
    kok = os.path.abspath(args.kok)
    if not any(os.path.exists(os.path.join(kok, a)) for a in (DUZELT, SIL, RENAME)):
        return 0
    try:
        lockf = open(os.path.join(kok, LOCK), "a")
    except OSError:
        _bas("kilit dosyasi acilamadi — dokunulmadi")
        return 0
    try:
        bitis = time.time() + KILIT_SURE
        while True:
            try:
                fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.time() > bitis:
                    _bas(".urunler.lock alinamadi — dokunulmadi")
                    return 0
                time.sleep(0.2)
        head = _katalog_head(kok)
        if head is None:
            _bas("HEAD:urunler.json okunamadi — dokunulmadi")
            return 0
        wt = _katalog_wt(kok)
        for ad, fn in ((DUZELT, lambda m: tuket_duzelt(m, head)),
                       (SIL, lambda m: tuket_sil(m, head, wt)),
                       (RENAME, lambda m: tuket_rename(m, head))):
            try:
                _isle(kok, ad, fn)
            except Exception as e:  # fail-safe: tek dosyanin hatasi digerini durdurmaz
                _bas("%s hata (%s) — dokunulmadi" % (ad, type(e).__name__))
    finally:
        try:
            fcntl.flock(lockf, fcntl.LOCK_UN)
        finally:
            lockf.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        _bas("beklenmeyen hata (%s) — dokunulmadi" % type(e).__name__)
        sys.exit(0)
