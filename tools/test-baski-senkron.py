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

    # --- stl-r2-yukle siniflandirma (COK-PARCA tasarimi, mimar duzeltme turu):
    #     <id>--<parca>.stl -> stl/<id>/<parca>.stl ; tek <id>.stl -> stl/<id>/<id>.stl ;
    #     onek urunler.json id listesinde DEGILSE hatali-ad (tahmin YOK), MECGER gizli
    #     kaynak-esleme kaynak-id'yi TEKIL bir urune bagliyorsa oraya yonlendirilir. ---
    idler = {"audi-parca", "vw-tutucu"}
    dosyalar = ["audi-parca.stl",                 # tekli -> normalize klasor
                "vw-tutucu--govde.stl",           # cok-parca
                "vw-tutucu--kapak_v2.3MF",        # cok-parca, buyuk uzanti
                "1002858--oil_wrench.STL",        # kaynak-id oneki (id listesinde YOK) -> hatali
                "bilinmeyen-urun.stl",            # tekli ama id yok -> hatali
                "vw-tutucu--.stl",                # bos parca adi -> hatali
                "audi-parca.png", "notlar.txt"]   # uzanti disi -> sessiz atla
    hedefler, hatali, cakisan = r2.siniflandir(dosyalar, idler)
    hedef_anahtarlar = {a for _, a in hedefler}
    dogrula("siniflandir cok-parca anahtarlari",
            hedef_anahtarlar == {"stl/audi-parca/audi-parca.stl",
                                 "stl/vw-tutucu/govde.stl",
                                 "stl/vw-tutucu/kapak_v2.3mf"},
            str(hedef_anahtarlar))
    dogrula("siniflandir hatali-ad raporu (kaynak-id esleme YOKSA + bilinmeyen + bos parca)",
            sorted(hatali) == ["1002858--oil_wrench.STL", "bilinmeyen-urun.stl",
                               "vw-tutucu--.stl"],
            str(hatali))
    dogrula("siniflandir png/txt sessiz atlandi",
            not any("png" in a or "txt" in a for a in hedef_anahtarlar))
    dogrula("siniflandir esleme verilmeyince cakisan bos", cakisan == [], str(cakisan))

    # --- MIMAR PAKETI (17 Tem gece): kaynak-id -> urun-id sozlugu gizli .urun-kaynaklari.json'dan
    #     turetilir (kaynak_esleme, SAF fonksiyon — sahte kayitla test edilir, GERCEK dosya
    #     ACILMAZ). (a) tekil eslesen kaynak-id dogru urune yonlendirilir, orijinal dosya adi
    #     KORUNUR (sadece uzanti kucultulur). (b) BIRDEN FAZLA urune baglanan kaynak-id TAHMIN
    #     EDILMEZ -> cakisan raporu, yuklenmez. (c) hic gecmeyen kaynak-id hatali-ad'da kalir. ---
    gizli_kayit_sahte = {
        "mapped-urun": {"link": "https://www.thingiverse.com/thing:1002858", "kaynak": "Thingiverse"},
        "printables-urun": {"link": "https://www.printables.com/model/2000000-baska-parca", "kaynak": "Printables"},
        # AYNI kaynak-id (thing:3000000) IKI FARKLI urune baglanmis -> cakisma
        "cakisan-urun-a": {"link": "https://www.thingiverse.com/thing:3000000", "kaynak": "Thingiverse"},
        "cakisan-urun-b": {"link": "https://www.thingiverse.com/thing:3000000", "kaynak": "Thingiverse"},
        "gorsel-atif-urun": {"link": "https://www.********.com/3d-print-models/x", "kaynak": "********"},
    }
    esle, cakisan_kumesi = r2.kaynak_esleme(gizli_kayit_sahte)
    dogrula("kaynak_esleme tekil thingiverse eslesir", esle.get("1002858") == "mapped-urun",
            repr(esle.get("1002858")))
    dogrula("kaynak_esleme printables 'pr' onekiyle eslesir (thingiverse'den AYRI ad uzayi)",
            esle.get("pr2000000") == "printables-urun", repr(esle.get("pr2000000")))
    dogrula("kaynak_esleme ayni kaynak-id iki urune baglanirsa cakisan",
            "3000000" in cakisan_kumesi and "3000000" not in esle,
            "esle=%s cakisan=%s" % (esle.get("3000000"), cakisan_kumesi))
    dogrula("kaynak_esleme ********/diger kaynaklar goz ardi edilir (id cikarilmaz)",
            len(esle) == 2 and set(esle) == {"1002858", "pr2000000"}, repr(esle))

    idler_b = {"mapped-urun", "printables-urun", "cakisan-urun-a", "cakisan-urun-b"}
    dosyalar_b = ["1002858--oil_wrench.STL",     # (a) tekil esleme -> mapped-urun
                  "3000000--govde.stl",          # (b) cakisan kaynak-id -> yuklenmez, raporlanir
                  "9999999--parca.stl"]          # (c) hic eslesmeyen -> hatali-ad'da KALIR
    hedefler_b, hatali_b, cakisan_b = r2.siniflandir(dosyalar_b, idler_b, esle, cakisan_kumesi)
    dogrula("(a) kaynak-id'li dosya DOGRU ANAHTARA gider (orijinal dosya adi korunur)",
            hedefler_b == [("1002858--oil_wrench.STL", "stl/mapped-urun/1002858--oil_wrench.stl")],
            str(hedefler_b))
    dogrula("(b) cakisan kaynak-id YUKLENMEZ + ayri raporlanir (hatali-ad'a KARISMAZ)",
            cakisan_b == ["3000000--govde.stl"] and "3000000--govde.stl" not in hatali_b,
            "cakisan=%s hatali=%s" % (cakisan_b, hatali_b))
    dogrula("(c) hic eslesmeyen kaynak-id hâlâ hatali-ad'da",
            hatali_b == ["9999999--parca.stl"], str(hatali_b))

    # kos() de kaynak_esle/kaynak_cakisan'i gecirip UYGULAMALI (uctan uca, sahte yukleyici ile)
    import tempfile as tf2
    kok_dizin_b = tf2.mkdtemp(prefix="stl-kaynak-test-")
    for ad, icerik in [("1002858--oil_wrench.STL", b"X1"), ("3000000--govde.stl", b"X2"),
                        ("9999999--parca.stl", b"X3")]:
        with open(os.path.join(kok_dizin_b, ad), "wb") as f:
            f.write(icerik)
    yuklenen_b = []

    def sahte_yukle_b(yerel, anahtar):
        yuklenen_b.append(anahtar)
        return True

    yb, ab, hb, cb = r2.kos(kok_dizin_b, idler_b, os.path.join(kok_dizin_b, ".manifest.json"),
                             kuru=False, yukle_fn=sahte_yukle_b,
                             kaynak_esle=esle, kaynak_cakisan=cakisan_kumesi)
    dogrula("kos(): sadece eslenen (a) fiilen yuklenir", yb == 1 and
            yuklenen_b == ["stl/mapped-urun/1002858--oil_wrench.stl"],
            "y=%s yuklenen=%s" % (yb, yuklenen_b))
    dogrula("kos(): cakisan + hatali-ad yuklenmeden raporlanir",
            cb == ["3000000--govde.stl"] and hb == ["9999999--parca.stl"],
            "cakisan=%s hatali=%s" % (cb, hb))
    import shutil as sh2
    sh2.rmtree(kok_dizin_b)

    # --- idempotens (mimar duzeltme turu KANITI): ardisik iki kosum — ilki yukler,
    #     IKINCISI atlandi=N yuklendi=0; icerik degisince SADECE o dosya yeniden. ---
    import tempfile as tf
    kok_dizin = tf.mkdtemp(prefix="stl-test-")
    for ad, icerik in [("audi-parca.stl", b"A1"), ("vw-tutucu--govde.stl", b"B1"),
                       ("vw-tutucu--kapak.stl", b"B2")]:
        with open(os.path.join(kok_dizin, ad), "wb") as f:
            f.write(icerik)
    manifest_yol = os.path.join(kok_dizin, ".manifest.json")
    yuklenenler = []

    def sahte_yukle(yerel, anahtar):
        yuklenenler.append(anahtar)
        return True

    y1, a1, h1, c1 = r2.kos(kok_dizin, idler, manifest_yol, kuru=False, yukle_fn=sahte_yukle)
    dogrula("kosum 1: hepsi yuklendi", y1 == 3 and a1 == 0 and h1 == [] and c1 == [] and
            len(yuklenenler) == 3, "y=%s a=%s h=%s c=%s" % (y1, a1, h1, c1))
    y2, a2, h2, c2 = r2.kos(kok_dizin, idler, manifest_yol, kuru=False, yukle_fn=sahte_yukle)
    dogrula("kosum 2: atlandi=N yuklendi=0 (IDEMPOTENS KANITI)",
            y2 == 0 and a2 == 3 and len(yuklenenler) == 3,
            "y=%s a=%s toplam-yukleme=%d" % (y2, a2, len(yuklenenler)))
    # icerik degisti (ayni boyut degil) -> SADECE o dosya yeniden yuklenir
    with open(os.path.join(kok_dizin, "vw-tutucu--govde.stl"), "wb") as f:
        f.write(b"B1-degisti")
    y3, a3, _, _ = r2.kos(kok_dizin, idler, manifest_yol, kuru=False, yukle_fn=sahte_yukle)
    dogrula("kosum 3: sadece degisen yeniden", y3 == 1 and a3 == 2 and
            yuklenenler[-1] == "stl/vw-tutucu/govde.stl",
            "y=%s a=%s son=%s" % (y3, a3, yuklenenler[-1:]))
    # ayni boyutta FARKLI icerik de yakalanir (sha1 kiyasi, boyut degil)
    with open(os.path.join(kok_dizin, "vw-tutucu--kapak.stl"), "wb") as f:
        f.write(b"XY")  # b"B2" ile ayni boyut (2 bayt)
    y4, a4, _, _ = r2.kos(kok_dizin, idler, manifest_yol, kuru=False, yukle_fn=sahte_yukle)
    dogrula("kosum 4: ayni boyut farkli icerik yakalandi (sha1)",
            y4 == 1 and a4 == 2 and yuklenenler[-1] == "stl/vw-tutucu/kapak.stl",
            "y=%s a=%s son=%s" % (y4, a4, yuklenenler[-1:]))
    # kuru kosum manifest'i degistirmez
    y5, a5, _, _ = r2.kos(kok_dizin, idler, manifest_yol, kuru=True, yukle_fn=sahte_yukle)
    dogrula("kuru kosum yazmaz", y5 == 0 and a5 == 3, "y=%s a=%s" % (y5, a5))
    import shutil
    shutil.rmtree(kok_dizin)

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()
