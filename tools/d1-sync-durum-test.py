#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — d1-sync.py --durum FAIL-LOUD teyidi.

  python3 tools/d1-sync-durum-test.py

Wrangler/ag/D1 GEREKMEZ: d1-sync importlib ile yuklenir; SAF durum_uyumlu() dogrudan,
--durum cikis kodu ise sorgu() monkeypatch + gecici urunler.json ile SINANIR (canli D1'e
DOKUNMAZ). Amac: D1 sayisi urunler.json'daki benzersiz id sayisiyla UYUMSUZ oldugunda
--durum exit 1 (fail-loud), uyumluysa exit 0 (temiz donus) — 'insan gormeden gecmesin'.
"""
import importlib.util
import json
import os
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

gecen = [0]
kalan = [0]


def yukle_modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + detay if detay else ""))


def fake_sorgu_uret(d1_sayisi):
    """sorgu() yerine gecen sahte: COUNT sorgusuna d1_sayisi, senkron sorgusuna tek satir."""
    def _f(sql):
        if "COUNT(*)" in sql:
            return [{"results": [{"n": d1_sayisi}]}]
        if "senkron" in sql:
            return [{"results": [{"anahtar": "urun_sayisi", "deger": str(d1_sayisi)}]}]
        return [{"results": []}]
    return _f


def durum_cikis(d1, urunler_listesi, d1_sayisi):
    """--durum'u OFFLINE kosar (sorgu + URUNLER monkeypatch), cikis kodunu dondur.
    Donen: 0 = temiz donus (uyumlu) · 1 = sys.exit ile fail-loud (uyumsuz)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(urunler_listesi, f)
        yol = f.name
    eski_sorgu, eski_urunler, eski_argv = d1.sorgu, d1.URUNLER, sys.argv
    try:
        d1.sorgu = fake_sorgu_uret(d1_sayisi)
        d1.URUNLER = yol
        sys.argv = ["d1-sync.py", "--durum"]
        try:
            d1.main()
            return 0                       # sys.exit CAGRILMADI -> uyumlu
        except SystemExit as e:
            # sys.exit(str) -> code bir metin (mesaj) = basarisizlik (exit 1);
            # sys.exit(None/0) -> temiz. Kodu POSIX cikis koduna cevir.
            c = e.code
            if c is None or c == 0:
                return 0
            return 1 if not isinstance(c, int) else c
    finally:
        d1.sorgu, d1.URUNLER, sys.argv = eski_sorgu, eski_urunler, eski_argv
        os.unlink(yol)


def main():
    d1 = yukle_modul("d1_sync", "d1-sync.py")

    # ── (1) SAF durum_uyumlu() — D1'e/dosyaya dokunmadan ──────────────────────
    dogrula("durum_uyumlu esit -> True", d1.durum_uyumlu(100, 100) is True)
    dogrula("durum_uyumlu D1 eksik -> False", d1.durum_uyumlu(99, 100) is False)
    dogrula("durum_uyumlu D1 fazla (silme propage olmadi) -> False",
            d1.durum_uyumlu(101, 100) is False)
    dogrula("durum_uyumlu D1 None (okunamadi) -> False (fail-loud)",
            d1.durum_uyumlu(None, 100) is False)
    dogrula("durum_uyumlu D1 sayisi metin ('100') -> True",
            d1.durum_uyumlu("100", 100) is True)
    dogrula("durum_uyumlu sifir/sifir -> True (bos katalog tutarli)",
            d1.durum_uyumlu(0, 0) is True)

    # ── (2) --durum cikis kodu — sorgu() + URUNLER monkeypatch (D1'e DOKUNMAZ) ──
    # 4 elemanli liste ama 3 BENZERSIZ id ('c' mukerrer) -> beklenen D1 satiri = 3.
    urunler = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "c"}]

    dogrula("--durum UYUMLU (D1=3 == benzersiz 3) -> exit 0",
            durum_cikis(d1, urunler, 3) == 0)
    dogrula("--durum UYUMSUZ (D1=2 < benzersiz 3) -> exit 1 (fail-loud)",
            durum_cikis(d1, urunler, 2) == 1)
    dogrula("--durum UYUMSUZ (D1=4 > benzersiz 3, silme kacti) -> exit 1",
            durum_cikis(d1, urunler, 4) == 1)
    dogrula("--durum mukerrer id LISTE uzunluguyla degil BENZERSIZ ile kiyaslar "
            "(D1=4 == liste uzunlugu ama exit 1)",
            durum_cikis(d1, urunler, 4) == 1)
    dogrula("--durum D1 okunamadi (COUNT None) -> exit 1",
            durum_cikis(d1, urunler, None) == 1)

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()
