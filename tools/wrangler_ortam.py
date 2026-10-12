#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/wrangler_ortam.py — wrangler ALT SURECI ortaminin TEK yardimcisi (kutuphane modulu).

NE ISE YARAR: wrangler her komutta `~/.wrangler/logs`'a bir debug log dosyasi yazar
(12 Eki 2026: 352 -> 368 dosya, gun icinde buyuyor). `WRANGLER_WRITE_LOGS=false` bu yazimi
kaynakta kapatir (gerekce + wrangler kaynak dogrulamasi: `tools/d1-sync.py::WRANGLER_LOG_KAPALI`).
Bu modul, wrangler'i `subprocess` ile cagiran HER yerin `env=` olarak verdigi ortami uretir:

    from wrangler_ortam import wrangler_ortami
    subprocess.run(["npx", "wrangler", ...], env=wrangler_ortami())          # os.environ + log kapali
    subprocess.run(komut, env=wrangler_ortami(mevcut_env))                   # mevcut env KORUNUR

IKIZ TANIM — OLCULU ([[agents-md-tek-kaynak]]): ayni literal `tools/d1-sync.py::WRANGLER_LOG_KAPALI`da
da durur (d1-sync-tani-mutasyon satirlari ona capali; d1-sync onlarca testte TEK BASINA kopyalanir,
bu module baglanirsa o kopyalar coker). Ayrisma SESSIZ kalamaz: `tools/wrangler-log-kapisi.py`
bu modulun CANLI degerini (calistirarak) ve d1-sync literal'ini ayri ayri `"false"`a karsi olcer;
biri saparsa o yolu kullanan her cagri yeri LOG_ACIK sayilir (rc 1).
Tuketici bu modulu bulamazsa import COKER (gurultulu): araci gecici mini-agaca kopyalayan test
bu dosyayi da kopyalar (`git_ortami.py` emsali). `try/except ImportError -> yerel tanim` YAZILMAZ.

Kapsam nobetcisi: `tools/wrangler-log-kapisi.py` (cagri yerlerini TURETIR, kanitsiz yer = rc 1).
"""
import os

# gerekce + wrangler kaynak dogrulamasi (`shouldLogToDisk`): tools/d1-sync.py::WRANGLER_LOG_KAPALI
WRANGLER_LOG_KAPALI = {"WRANGLER_WRITE_LOGS": "false"}


def wrangler_ortami(taban=None):
    """`taban` (verilmezse os.environ) + disk logu kapali — yeni sozluk, taban DEGISMEZ."""
    return dict(os.environ if taban is None else taban, **WRANGLER_LOG_KAPALI)
