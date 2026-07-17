#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jenerator-tasi.py — TÜM parametrik (sarı seri) ürünleri gizli "Jeneratör" kategorisine
taşır (Okan kararı, 17 Tem gece). urunler.json'a guard'a takılmadan yazmanın meşru yolu
olan tools/duzelt.py'yi ürün başına çağırır (SIRALI — paralel yazar çakışması yok).

Kullanım (mimar, merge sırasında; ya da mühendis worktree'de test için):
  python3 tools/jenerator-tasi.py            # önce ne yapacağını yazar, sonra uygular
  python3 tools/jenerator-tasi.py --kuru     # sadece listeler, DOKUNMAZ (kuru koşu)

Notlar:
- Zaten "Jeneratör" olan ürün atlanır (ikinci koşu zararsız — idempotent).
- Kategori değişikliği arama metnine (haystack/D1) girer: push sonrası pre-push hook
  D1'i senkronlar; parite testleri (site+ege) senkron SONRASI yeniden koşulmalı.
- Yeni ürün akışı: bundan sonra parametrik ürün eklerken kategori doğrudan
  "Jeneratör" yazılır (CLAUDE.md sarı seri kuralı mimar merge'inde güncellenecek).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
DUZELT = os.path.join(ROOT, "tools", "duzelt.py")
HEDEF = "Jeneratör"


def main():
    kuru = "--kuru" in sys.argv[1:]
    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)

    adaylar = [u for u in urunler if u.get("parametrik") and u.get("kategori") != HEDEF]
    zaten = [u for u in urunler if u.get("parametrik") and u.get("kategori") == HEDEF]

    print("Parametrik ürün: %d (taşınacak %d, zaten %s olan %d)"
          % (len(adaylar) + len(zaten), len(adaylar), HEDEF, len(zaten)))
    for u in adaylar:
        print("  %-40s %s -> %s" % (u["id"], u.get("kategori"), HEDEF))
    if kuru:
        print("KURU KOŞU — dokunulmadı.")
        return
    if not adaylar:
        print("Taşınacak ürün yok. ✅")
        return

    for u in adaylar:
        sonuc = subprocess.run(
            [sys.executable, DUZELT, u["id"], "--alan", "kategori", "--deger", HEDEF],
            capture_output=True, text=True)
        if sonuc.returncode != 0:
            print("HATA: %s taşınamadı:\n%s%s" % (u["id"], sonuc.stdout, sonuc.stderr))
            sys.exit(1)

    # doğrulama: taşıma sonrası hiçbir parametrik ürün HEDEF dışında kalmamalı
    with open(URUNLER, encoding="utf-8") as f:
        kalan = [u["id"] for u in json.load(f)
                 if u.get("parametrik") and u.get("kategori") != HEDEF]
    if kalan:
        print("HATA: taşınamayan ürünler: %s" % ", ".join(kalan))
        sys.exit(1)
    print("%d ürün %s kategorisine taşındı. ✅ (push sonrası: D1 senkron + parite tekrarı)"
          % (len(adaylar), HEDEF))


if __name__ == "__main__":
    main()
