#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCEK OLCUMU — "yuzlerce konfigurlu urun" hedefinde ESKI YOL (bundle) vs YENI YOL (D1).

  python3 tools/konfigur-olcek-olcum.py            # varsayilan 500 urun projeksiyonu
  python3 tools/konfigur-olcek-olcum.py --adet 1000

NEDEN: Okan hedefi "belki yuzlerce konfigurlu urun". Karar bugunku 17'ye gore degil, o
olcege gore verilmeli. Bu arac AGA/D1'e DOKUNMAZ; gercek artefakt + gercek urunler.json
bayt olcumlerinden dogrusal projeksiyon yapar ve iki yolu yan yana koyar.

OLCULEN EKSENLER
  1. D1 YAZMA     — senkron basina UPDATE sayisi (hedefli plan) ve gunluk yazma butcesine orani.
  2. WORKER OKUMA — fiyat sorgusunun tasidigi ek bayt (sepetteki KALEM sayisina bagli;
                    katalog buyuklugunden BAGIMSIZ oldugu gosterilir).
  3. BUNDLE       — eski yolda Worker script'ine eklenen bayt + gereken ELLE deploy sayisi.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
ARTEFAKT = os.path.join(KOK, "shop", "src", "konfigurlar.js")

# Olculen gerceklik (CLAUDE.md / fizibilite raporu): hesap Workers Paid; son 24 saatte
# 59.610 satir yazma gozlendi. Gunluk butce referansi olarak bu kullanilir (ucretsiz planin
# 100.000 tavani BAYAT — bkz. CLAUDE.md).
GUNLUK_GOZLENEN_YAZMA = 59610
# Worker script boyut siniri (Cloudflare Workers Paid): 10 MB sikistirilmis.
WORKER_SINIR_BAYT = 10 * 1024 * 1024


def yukle(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adet", type=int, default=500, help="projeksiyon urun adedi")
    a = ap.parse_args()

    d1 = yukle("d1_sync_olcek", "d1-sync.py")
    urunler = json.load(open(URUNLER, encoding="utf-8"))
    harita, _ = d1.konfigur_haritasi_d1(urunler)
    n = len(harita)
    if not n:
        sys.exit("konfigurlu urun bulunamadi")

    # --- kanonik (D1) bayt olcumu -------------------------------------------------
    kanonik = [len(v.encode("utf-8")) for v in harita.values()]
    kan_ort = sum(kanonik) / n
    kan_max = max(kanonik)

    # --- bundle (eski yol) bayt olcumu --------------------------------------------
    art_ham = open(ARTEFAKT, encoding="utf-8").read()
    art_bayt = len(art_ham.encode("utf-8"))
    m = re.search(r"const VERI = (\{.*?\});\n", art_ham, re.S)
    veri_bayt = len(m.group(1).encode("utf-8")) if m else art_bayt
    bundle_urun_basi = veri_bayt / n

    hedef = a.adet
    print("KONFIGUR OLCEK OLCUMU — bugun %d urun, projeksiyon %d urun" % (n, hedef))
    print("=" * 72)
    print("KAYNAK OLCUMLER (gercek dosyalar)")
    print("  konfigurlu urun (urunler.json)      : %d" % n)
    print("  kanonik JSON / urun (D1'e yazilan)  : ort %.0f B, max %d B" % (kan_ort, kan_max))
    print("  bundle VERI blogu (konfigurlar.js)  : %d B toplam, %.0f B/urun (indent=2)"
          % (veri_bayt, bundle_urun_basi))
    print("  artefakt dosyasi toplam             : %d B" % art_bayt)

    print("")
    print("1) D1 YAZMA — hedefli UPDATE (sema_plan/konfigur_plan)")
    ilk = hedef                       # ilk doldurma: her urune 1 UPDATE
    rutin = 1                         # rutin: 1 yeni urun = 1 UPDATE
    print("  ilk doldurma (%d urun)              : %d UPDATE = gunluk gozlenen yazmanin %%%.3f"
          % (hedef, ilk, 100.0 * ilk / GUNLUK_GOZLENEN_YAZMA))
    print("  bugunku 17 urunun ilk doldurmasi    : 17 UPDATE = %%%.3f"
          % (100.0 * 17 / GUNLUK_GOZLENEN_YAZMA))
    print("  rutin: 1 yeni konfigurlu urun       : %d UPDATE = %%%.5f"
          % (rutin, 100.0 * rutin / GUNLUK_GOZLENEN_YAZMA))
    print("  degisiklik YOKKEN her senkron       : 0 UPDATE (idempotent — kanonik + diff)")
    print("  konfigursuz ~%d urun               : 0 UPDATE (hedef ''=varsayilan)"
          % (len(urunler) - n))
    print("  -> OLCEK HUKMU: %d urunde bile tek seferlik %%%.3f; onemsiz."
          % (hedef, 100.0 * ilk / GUNLUK_GOZLENEN_YAZMA))

    print("")
    print("2) WORKER OKUMA — /api/shop/fiyat + /baslat")
    print("  ek SORGU sayisi                     : 0 (konfigur MEVCUT SELECT'e kolon olarak eklendi)")
    print("  ek round-trip                       : 0 (sepetiFiyatla zaten D1'e gidiyor)")
    print("  ek bayt / SEPET KALEMI              : ~%.0f B (yalniz konfigurlu kalem; digeri 0 B)"
          % kan_ort)
    print("  3 kalemlik konfigur sepeti          : ~%.0f B" % (3 * kan_ort))
    print("  KATALOG BUYUKLUGUNE BAGIMLILIK      : YOK — SELECT ... WHERE id IN (sepet id'leri);")
    print("                                        satir sayisi sepetteki KALEM sayisi kadar.")
    print("  -> %d urunde de 1.000.000 urunde de ayni: O(sepet), O(katalog) DEGIL." % hedef)

    print("")
    print("3) BUNDLE — ESKI YOL vs YENI YOL (gecisin gerekcesi)")
    eski = bundle_urun_basi * hedef
    print("  ESKI YOL (%d urun):" % hedef)
    print("    konfigurlar.js VERI blogu         : ~%.0f B (%.2f MB) — Worker script'ine GIRER"
          % (eski, eski / 1048576.0))
    print("    Worker script siniri kullanimi    : ~%%%.2f (%d MB sinir, sikistirmadan ONCE)"
          % (100.0 * eski / WORKER_SINIR_BAYT, WORKER_SINIR_BAYT // 1048576))
    print("    ELLE artefakt uretimi             : her yeni urunde 1 (atlanirsa urun karta KAPALI)")
    print("    ELLE wrangler deploy              : her yeni urunde 1 (atlanirsa ayni pencere)")
    print("    -> %d urun = %d elle adim; 30 Tem'de 2 tanesi atlandi (biri urunu kapali birakti,"
          % (hedef, 2 * hedef))
    print("       digeri CI'i durdurup 23 urunun yayinini blokladi).")
    print("  YENI YOL (%d urun):" % hedef)
    print("    Worker script'ine eklenen bayt    : 0 B (sema bundle'da DEGIL, D1 satirinda)")
    print("    ELLE artefakt uretimi             : 0")
    print("    ELLE wrangler deploy              : 0 (pre-push hook zaten senkronluyor)")
    print("    D1 depolama                       : ~%.0f B toplam (%.2f MB) — 63,5 MB'lik DB'de onemsiz"
          % (kan_ort * hedef, kan_ort * hedef / 1048576.0))
    print("    -> ELLE ADIM: %d -> 0. Gecisin karsiligi bu." % (2 * hedef))

    print("")
    print("NOT (FAZ 3 golge modu): bugun fiyat HALA bundle'dan hesaplanir; yukaridaki 'yeni yol'")
    print("     kazanci FAZ 4 (cevirme) ile fiilen alinir. Bu tablo o kararin girdisidir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
