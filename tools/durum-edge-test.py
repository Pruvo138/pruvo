#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EDGE_KATALOG ESIGI SAYACI KABUL TESTLERI -- spec-durum-edge-sayaci.md.

    python3 tools/durum-edge-test.py

  1. Gercek repo: `python3 tools/durum.py` ciktisinda EDGE_KATALOG bolumu var +
     raporlanan urun sayisi urunler.json'daki BENZERSIZ id sayisiyla (bu test
     dosyasi BAGIMSIZ olarak sayar, durum.urunler_sayisi CAGIRMAZ) birebir ayni.
  2. Sahte KUCUK urunler.json (tmp dosya -- GERCEK urunler.json'a hic DOKUNULMAZ,
     yol parametreyle verilir) ile 3 senaryo:
       2a) esik alti          -> hicbir satirda ⚠ yok
       2b) 10000+ (hazirlik)  -> hazirlik satirinda ⚠, flip/mecburi'de yok
       2c) 12000+ (flip)      -> hazirlik VE flip satirinda ⚠, mecburi'de yok
  3. Once-kirmizi kaniti: EDGE_HAZIRLIK sabiti CALISMA ANINDA mutasyona ugrarsa
     (durum.EDGE_HAZIRLIK degistirilir) ayni girdi icin siniflandirma BOZULUR
     -- sabitin gercekten kullanildigini kanitlar. Mutasyon finally'de GERI ALINIR.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import durum  # noqa: E402

SONUC = []


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("✅" if gecti else "❌", no, ad,
                                   (" | " + detay) if detay else ""), flush=True)


def _sahte_urunler_yaz(tmp, ad, adet):
    yol = os.path.join(tmp, ad)
    veri = [{"id": "sahte-urun-%d" % i, "baslik": "x"} for i in range(adet)]
    with open(yol, "w") as f:
        json.dump(veri, f)
    return yol


def _urun_sayisi_bagimsiz(yol):
    """durum.urunler_sayisi'ni COGALTMAZ -- ayri bir yoldan sayar (test kendi
    kendini dogrulamasin diye)."""
    with open(yol, "r", errors="replace") as f:
        veri = json.load(f)
    idler = set(u["id"] for u in veri if isinstance(u, dict) and "id" in u)
    return len(idler)


def test_1_gercek_repo():
    urun_yolu = os.path.join(durum.ana_repo(ROOT), "urunler.json")
    once_mtime = os.path.getmtime(urun_yolu)
    bagimsiz = _urun_sayisi_bagimsiz(urun_yolu)

    p = subprocess.run([sys.executable, os.path.join(TOOLS, "durum.py")],
                       capture_output=True, text=True)
    sonra_mtime = os.path.getmtime(urun_yolu)
    m = re.search(r"^\s*urun:\s*(\d+)", p.stdout, re.MULTILINE)
    raporlanan = int(m.group(1)) if m else None

    kayit(1, "durum.py EDGE_KATALOG bolumu var + urun sayisi BAGIMSIZ sayimla ayni",
          p.returncode == 0 and "EDGE_KATALOG" in p.stdout and raporlanan == bagimsiz,
          "bagimsiz=%s raporlanan=%s exit=%d" % (bagimsiz, raporlanan, p.returncode))
    kayit("1b", "durum.py urunler.json'a DOKUNMADI (mtime degismedi -- salt-okunur)",
          once_mtime == sonra_mtime,
          "once=%s sonra=%s" % (once_mtime, sonra_mtime))
    return p.stdout


def test_2_esik_senaryolari(tmp):
    # 2a) esik alti
    yol_alti = _sahte_urunler_yaz(tmp, "sahte-alti.json", 500)
    sayi_alti = durum.urunler_sayisi(yol_alti)
    satir_alti = "\n".join(durum.edge_satirlari(durum.edge_esigi(sayi_alti)))
    kayit("2a", "esik alti (500) -> hicbir satirda ⚠ yok",
          sayi_alti == 500 and "⚠" not in satir_alti,
          "sayi=%d" % sayi_alti)

    # 2b) hazirlik esigi+
    yol_haz = _sahte_urunler_yaz(tmp, "sahte-hazirlik.json", 10250)
    sayi_haz = durum.urunler_sayisi(yol_haz)
    e_haz = durum.edge_esigi(sayi_haz)
    satir_haz = "\n".join(durum.edge_satirlari(e_haz))
    kayit("2b", "10250 -> hazirlik satirinda ⚠, flip/mecburi'de YOK",
          e_haz["hazirlik"]["asildi"] is True
          and e_haz["flip"]["asildi"] is False
          and e_haz["mecburi"]["asildi"] is False
          and "⚠ hazirlik" in satir_haz
          and "⚠ flip" not in satir_haz,
          "sayi=%d satir=%r" % (sayi_haz, satir_haz.splitlines()[0]))

    # 2c) flip esigi+
    yol_flip = _sahte_urunler_yaz(tmp, "sahte-flip.json", 12300)
    sayi_flip = durum.urunler_sayisi(yol_flip)
    e_flip = durum.edge_esigi(sayi_flip)
    satir_flip = "\n".join(durum.edge_satirlari(e_flip))
    kayit("2c", "12300 -> hazirlik VE flip satirinda ⚠, mecburi'de YOK",
          e_flip["hazirlik"]["asildi"] is True
          and e_flip["flip"]["asildi"] is True
          and e_flip["mecburi"]["asildi"] is False
          and "⚠ hazirlik" in satir_flip
          and "⚠ flip" in satir_flip
          and "⚠ mecburi" not in satir_flip,
          "sayi=%d satir=%r" % (sayi_flip, satir_flip.splitlines()[0]))


def test_3_kirmizi_mutasyon():
    """EDGE_HAZIRLIK sabiti gercekten kullaniliyor mu? Once-kirmizi kaniti:
    sabiti CALISMA ANINDA yanlis bir degere cek, ayni girdi (10250) artik
    hazirlik esigini AŞMAMIS gibi siniflansin -- bu YANLIS sonuc, sabitin
    load-bearing oldugunu kanitlar. Sonra ORIJINAL degere geri don ve dogru
    sonucun geri geldigini dogrula."""
    orijinal = durum.EDGE_HAZIRLIK
    try:
        once = durum.edge_esigi(10250)["hazirlik"]["asildi"]
        durum.EDGE_HAZIRLIK = 999999  # <-- MUTASYON: esik kasten bozuldu
        sonra = durum.edge_esigi(10250)["hazirlik"]["asildi"]
        kayit(3, "EDGE_HAZIRLIK mutasyonu siniflandirmayi BOZUYOR (once-kirmizi kaniti)",
              once is True and sonra is False,
              "mutasyon-oncesi asildi=%s | mutasyon-sonrasi asildi=%s" % (once, sonra))
    finally:
        durum.EDGE_HAZIRLIK = orijinal
    geri = durum.edge_esigi(10250)["hazirlik"]["asildi"]
    kayit("3b", "mutasyon GERI ALINDI -- orijinal sabitle dogru sonuc geri geldi",
          geri is True, "geri-alindi asildi=%s" % geri)


def main():
    print("\nEDGE_KATALOG ESIGI SAYACI KABUL TESTLERI\n")
    cikti = test_1_gercek_repo()

    tmp = tempfile.mkdtemp(prefix="durum-edge-test-")
    try:
        test_2_esik_senaryolari(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    test_3_kirmizi_mutasyon()

    # sizinti kapisi: bu bolum sadece SAYI basar, sir/urun icerigi DOKMEZ
    kayit("4", "EDGE_KATALOG ciktisi sadece sayi/esik basiyor (urun baslik/id sizmiyor)",
          "sahte-urun-" not in cikti, "cikti uzunlugu=%d" % len(cikti))

    basarisiz = [s for s in SONUC if not s[2]]
    print("\n%s  %d/%d test gecti\n"
          % ("✅ HEPSI YESIL" if not basarisiz else "❌ KIRMIZI",
             len(SONUC) - len(basarisiz), len(SONUC)))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
