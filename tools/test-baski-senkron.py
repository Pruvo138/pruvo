#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — baski kolonu senkronu (gizli kayittan D1'e) + stl-r2-yukle siniflandirma.

  python3 tools/test-baski-senkron.py

Wrangler/ag GEREKMEZ: d1-sync ve stl-r2-yukle'nin SAF fonksiyonlari importlib ile yuklenip
sinanir. Canli D1'e/R2'ye DOKUNMAZ (spec: toplu yukleme merge sonrasi mimar/maraba isi).
"""
import importlib.util
import json
import os
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yukle_modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + detay if detay else ""))


def main():
    d1 = yukle_modul("d1_sync", "d1-sync.py")
    r2 = yukle_modul("stl_r2", "stl-r2-yukle.py")

    # --- baski_haritasi: gizli kayittan id->baski, "-"/bos atlanir ---
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({
            "urun-a": {"baski": "6-8 duvar, %15 doluluk", "uyelik": "*****"},
            "urun-b": {"baski": "-"},          # placeholder -> atlanmali
            "urun-c": {"baski": ""},           # bos -> atlanmali
            "urun-d": {"link": "x"},           # baski alani yok -> atlanmali
            "urun-e": {"baski": "  PLA 200C  "},  # trim edilmeli
        }, f)
        kaynak_yol = f.name
    eski_kaynak = d1.KAYNAKLAR
    try:
        d1.KAYNAKLAR = kaynak_yol
        harita = d1.baski_haritasi()
    finally:
        d1.KAYNAKLAR = eski_kaynak
        os.unlink(kaynak_yol)

    dogrula("baski_haritasi 'urun-a' dolu", harita.get("urun-a") == "6-8 duvar, %15 doluluk",
            repr(harita.get("urun-a")))
    dogrula("baski_haritasi '-' placeholder atlandi", "urun-b" not in harita)
    dogrula("baski_haritasi bos atlandi", "urun-c" not in harita)
    dogrula("baski_haritasi alansiz atlandi", "urun-d" not in harita)
    dogrula("baski_haritasi trim etti", harita.get("urun-e") == "PLA 200C", repr(harita.get("urun-e")))

    # --- etkin_hash: baski VARSA hash degisir, YOKSA arama.urun_hash ile AYNI ---
    u = {"id": "urun-a", "baslik": "Test", "kategori": "Ev", "marka": [], "fiyat": "100 TL"}
    import importlib
    sys.path.insert(0, os.path.join(KOK, "tools"))
    arama = importlib.import_module("arama")
    ham = arama.urun_hash(u)
    dogrula("baskisiz etkin_hash = arama.urun_hash", d1.etkin_hash(u, "") == ham)
    dogrula("baskili etkin_hash farkli", d1.etkin_hash(u, "6-8 duvar") != ham)
    dogrula("etkin_hash deterministik",
            d1.etkin_hash(u, "6-8 duvar") == d1.etkin_hash(u, "6-8 duvar"))
    dogrula("farkli baski farkli hash",
            d1.etkin_hash(u, "A") != d1.etkin_hash(u, "B"))

    # --- satir_sql: baski degeri dogru kolona yaziliyor + KOLONLAR'da 'baski' var ---
    sql = d1.satir_sql(u, 5, arama.haystack(u), d1.etkin_hash(u, "6-8 duvar"), "6-8 duvar")
    dogrula("satir_sql INSERT'te baski kolonu var", ",baski)VALUES" in sql.replace(" ", ""), sql[:120])
    dogrula("satir_sql baski degeri gomulu", "'6-8 duvar'" in sql)
    dogrula("KOLONLAR ON CONFLICT'te baski gunceller", "baski" in d1.KOLONLAR)
    dogrula("GOC_KOLON urunler.baski",
            any(k[0] == "baski" for k in d1.GOC_KOLON))
    dogrula("GOC_KOLON_SIPARIS kargo/durum_gecmisi",
            {k[0] for k in d1.GOC_KOLON_SIPARIS} >= {"kargo_kodu", "kargo_firma", "durum_gecmisi"})

    # --- stl-r2-yukle siniflandirma: hatali ad TAHMIN EDILMEZ, uzanti filtresi, idempotens ---
    idler = {"audi-parca", "vw-tutucu"}
    dosyalar = ["audi-parca.stl", "vw-tutucu.3mf", "vw-tutucu.STL",  # buyuk uzanti da kabul
                "bilinmeyen-urun.stl", "audi-parca.png", "notlar.txt"]
    hedefler, hatali = r2.siniflandir(dosyalar, idler)
    hedef_anahtarlar = {a for _, a in hedefler}
    dogrula("siniflandir gecerli id'ler yuklenecek",
            hedef_anahtarlar == {"stl/audi-parca.stl", "stl/vw-tutucu.3mf", "stl/vw-tutucu.stl"},
            str(hedef_anahtarlar))
    dogrula("siniflandir hatali ad raporlandi (tahmin yok)", hatali == ["bilinmeyen-urun.stl"],
            str(hatali))
    dogrula("siniflandir png/txt atlandi",
            "stl/audi-parca.png" not in hedef_anahtarlar and "notlar.txt" not in hedef_anahtarlar)

    # idempotens: ayni boyut -> atla, farkli boyut -> yukle, yok -> yukle
    r2_liste = {"stl/audi-parca.stl": 1234}
    dogrula("atlanir: ayni boyut -> True", r2.atlanir("stl/audi-parca.stl", 1234, r2_liste))
    dogrula("atlanir: farkli boyut -> False", not r2.atlanir("stl/audi-parca.stl", 9999, r2_liste))
    dogrula("atlanir: yok -> False", not r2.atlanir("stl/vw-tutucu.3mf", 10, r2_liste))

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()
