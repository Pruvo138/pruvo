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
            "urun-a": {"baski": "6-8 duvar, %15 doluluk", "uyelik": "koolm"},
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

    # ═══ DIFF-UPSERT THRASH ONARIMI (2026-07-18) — asil kabul kriterleri ══════════
    # ESKI TASARIM (hatali, bu testin eski hali onu MUHURLUYORDU): baski hash'e karisiyordu.
    # baski yalnizca gizli .urun-kaynaklari.json'da; YEREL onu gorur, CI (gitignore) GORMEZ ->
    # yerel "baski'li hash", CI "baski'siz hash" yazip her push'ta ~3.700 urunu birbirine
    # EZDIRIYORDU (12 urunluk batch'te ~7.400 D1 yazma = neredeyse tam rebuild; 100.000/gun
    # limitine kosuyordu). Ustelik baski KOLONLAR'daydi -> CI baski'yi '' yapip D1'den siliyordu
    # (canlida olculdu: 7381 satirin HEPSINDE baski=''). Asil sart: (a) hash iki ortamda AYNI,
    # (b) degisiklik yoksa HIC yazma, (c) baski AYRI + yalniz gerekince + CI silmeden.
    import importlib
    sys.path.insert(0, os.path.join(KOK, "tools"))
    arama = importlib.import_module("arama")

    dogrula("etkin_hash KALDIRILDI (baski artik hash'e karismaz)", not hasattr(d1, "etkin_hash"))

    u1 = {"id": "a", "baslik": "A", "kategori": "Ev", "marka": ["X"], "fiyat": "10 TL",
          "gorseller": ["g1.jpg"], "aciklama": "ac"}
    u2 = {"id": "b", "baslik": "B", "kategori": "Ofis", "marka": [], "fiyat": "20 TL"}
    urunler = [u2, u1]   # dizi basi = en yeni
    # D1 GUNCEL: hash = baski'SIZ urun_hash, baski da dogru. 'a'nin baskisi var, 'b'nin yok.
    mevcut = {"a": (arama.urun_hash(u1), "6-8 duvar"), "b": (arama.urun_hash(u2), "")}
    baskilar = {"a": "6-8 duvar"}   # yerelin gordugu baski = D1'dekiyle AYNI

    # (a) DEGISIKLIK YOK -> plan tamamen bos = SIFIR yazma (thrash bitti).
    y, d, bg, s, g = d1.diff_plan(urunler, mevcut, baskilar, True, 2)
    dogrula("KABUL degisiklik yok -> yeni/degisen/baski/silinen HEPSI bos (0 yazma)",
            y == [] and d == [] and bg == [] and s == [],
            "y=%d d=%d bg=%d s=%d" % (len(y), len(d), len(bg), len(s)))

    # (b) ASIL BUG: YEREL (baski VAR) ile CI (baski dosyasi YOK) AYNI content planini uretir.
    #     Eskiden yerel 'a'yi hep "degismis" gorurdu (baski'li hash != D1 baski'siz). Artik gormez.
    y_ci, d_ci, bg_ci, s_ci, _ = d1.diff_plan(urunler, mevcut, {}, False, 2)  # CI: baski bos + yetki yok
    dogrula("YEREL==CI content plani (baski thrash'i bitti)",
            (len(y), len(d), len(s)) == (len(y_ci), len(d_ci), len(s_ci)) == (0, 0, 0),
            "yerel=(%d,%d,%d) ci=(%d,%d,%d)" % (len(y), len(d), len(s), len(y_ci), len(d_ci), len(s_ci)))
    dogrula("CI baski'ya HIC dokunmaz (silmez/ezmez)", bg_ci == [], str(bg_ci))

    # (c) baski FIILEN degisince -> tam 1 baski UPDATE, content YENIDEN YAZILMAZ.
    y3, d3, bg3, s3, _ = d1.diff_plan(urunler, mevcut, {"a": "12 duvar, %30"}, True, 2)
    dogrula("baski degisti -> 1 baski UPDATE + 0 content yazma",
            y3 == [] and d3 == [] and s3 == [] and len(bg3) == 1
            and bg3[0] == "UPDATE urunler SET baski='12 duvar, %30' WHERE id='a';", "bg=%s" % bg3)

    # (d) ICERIK degisince -> 1 content UPDATE; baski AYNIYSA ekstra baski yazma YOK.
    u1b = dict(u1, fiyat="99 TL")   # fiyat -> hash degisir
    y4, d4, bg4, s4, _ = d1.diff_plan([u2, u1b], mevcut, baskilar, True, 2)
    dogrula("icerik degisti -> 1 content UPDATE, baski ayni -> 0 baski yazma",
            y4 == [] and len(d4) == 1 and bg4 == [] and s4 == [], "d=%d bg=%d" % (len(d4), len(bg4)))

    # (e) YENI urun -> INSERT (baski VALUES'ta gomulu); ayri baski UPDATE URETILMEZ.
    u_yeni = {"id": "c", "baslik": "C", "kategori": "Ev", "marka": [], "fiyat": "5 TL"}
    y5, d5, bg5, s5, _ = d1.diff_plan([u_yeni] + urunler, mevcut, dict(baskilar, c="PLA"), True, 2)
    dogrula("yeni urun -> 1 INSERT (baski INSERT'te), ayri baski UPDATE yok",
            len(y5) == 1 and bg5 == [] and "'PLA'" in y5[0], "y=%s" % y5[:1])

    # (f) SILINEN: urunler.json'dan cikan D1 satiri silinen'e duser.
    y6, d6, bg6, s6, _ = d1.diff_plan([u1], mevcut, baskilar, True, 2)  # 'b' artik yok
    dogrula("silinen urun tespit edilir", s6 == ["b"], str(s6))

    # --- satir_sql: baski INSERT VALUES'ta AMA ON CONFLICT SET'te DEGIL (CI ezemesin) ---
    sql = d1.satir_sql(u1, 5, arama.haystack(u1), arama.urun_hash(u1), "6-8 duvar")
    dogrula("satir_sql INSERT'te baski kolonu var", ",baski)VALUES" in sql.replace(" ", ""), sql[:120])
    dogrula("satir_sql baski degeri INSERT VALUES'ta gomulu", "'6-8 duvar'" in sql)
    dogrula("KOLONLAR ON CONFLICT'te baski GUNCELLEMEZ (CI baski'yi silemez)",
            "baski" not in d1.KOLONLAR)
    conflict = sql.split("ON CONFLICT", 1)[1]
    dogrula("ON CONFLICT SET'te 'baski=' YOK", "baski=" not in conflict, conflict[:200])
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
        "gorsel-atif-urun": {"link": "https://www.cgtrader.com/3d-print-models/x", "kaynak": "CGTrader"},
    }
    esle, cakisan_kumesi = r2.kaynak_esleme(gizli_kayit_sahte)
    dogrula("kaynak_esleme tekil thingiverse eslesir", esle.get("1002858") == "mapped-urun",
            repr(esle.get("1002858")))
    dogrula("kaynak_esleme printables 'pr' onekiyle eslesir (thingiverse'den AYRI ad uzayi)",
            esle.get("pr2000000") == "printables-urun", repr(esle.get("pr2000000")))
    dogrula("kaynak_esleme ayni kaynak-id iki urune baglanirsa cakisan",
            "3000000" in cakisan_kumesi and "3000000" not in esle,
            "esle=%s cakisan=%s" % (esle.get("3000000"), cakisan_kumesi))
    dogrula("kaynak_esleme CGTrader/diger kaynaklar goz ardi edilir (id cikarilmaz)",
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

    # --- MIMAR MIKRO PAKETI (17 Tem gece): PARALEL YUKLEME (--paralel N) ---
    #     SORUN: dosya basina ayri wrangler sureci sirali ~6 sn -> 8.784 dosya ~14 saat.
    #     COZUM: N eszamanli yukleyici, ama manifest'e TEK YAZICI (main) yazar.
    #     KANIT: (neg-kontrol) serilestirilmemis oku-degistir-yaz IKI is parcacigi kayit
    #     KAYBEDER; (a) gercek kos(paralel=4) 20 dosyada HIC kaybetmez; (b) 2. kosum
    #     yuklendi=0; (c) paralel=1 eski davranisla birebir; (olcum) paralel ~1/4 sure.
    import threading
    import time as _time

    # (neg-kontrol) DETERMINISTIK yaris: iki is parcacigi ayni BAYAT snapshot'i okur
    # (barrier ile garanti), sonra yazar -> ikinci yazim birinciyi EZER, kayit KAYBOLUR.
    # Bu tam olarak .urun-kaynaklari.json'da yasanan sinif (259 kayip). Tasarimin bunu
    # ONLEMESI gerek: tek-yazici -> hic yaris yok.
    neg_dizin = tempfile.mkdtemp(prefix="stl-neg-")
    neg_manifest = os.path.join(neg_dizin, ".manifest.json")
    r2.manifest_yaz(neg_manifest, {})
    bariyer = threading.Barrier(2)

    def _naif_yaz(anahtar, veri):
        m = r2.manifest_oku(neg_manifest)   # ikisi de bos/bayat kopyayi okur
        bariyer.wait()                      # her ikisi de eski snapshot'ta bulusur
        m[anahtar] = veri
        r2.manifest_yaz(neg_manifest, m)    # atomik AMA serilestirilmemis -> lost update

    t1 = threading.Thread(target=_naif_yaz, args=("stl/a/a.stl", {"sha1": "1", "boyut": 1}))
    t2 = threading.Thread(target=_naif_yaz, args=("stl/b/b.stl", {"sha1": "2", "boyut": 2}))
    t1.start(); t2.start(); t1.join(); t2.join()
    neg_sonuc = r2.manifest_oku(neg_manifest)
    dogrula("NEG-KONTROL: serilestirilmemis paralel yazim kayit KAYBEDER (yaris kaniti)",
            len(neg_sonuc) == 1, "manifest=%s (2 beklerdik, 1 = kayip kanitlandi)" % neg_sonuc)
    shutil.rmtree(neg_dizin)

    # 20 sahte dosya + YAVAS (0.2 sn) sahte yukleyici
    par_dizin = tempfile.mkdtemp(prefix="stl-par-")
    par_idler = set()
    for i in range(20):
        with open(os.path.join(par_dizin, "urun%02d.stl" % i), "wb") as f:
            f.write(b"icerik-%d" % i)
    par_idler = {"urun%02d" % i for i in range(20)}
    par_manifest = os.path.join(par_dizin, ".manifest.json")
    kilit = threading.Lock()
    yuklenen_par = []

    def yavas_yukle(yerel, anahtar):
        _time.sleep(0.2)
        with kilit:
            yuklenen_par.append(anahtar)
        return True

    t0 = _time.time()
    yp, ap, hp, cp = r2.kos(par_dizin, par_idler, par_manifest, kuru=False,
                            yukle_fn=yavas_yukle, paralel=4)
    par_sure = _time.time() - t0
    manifest_par = r2.manifest_oku(par_manifest)
    dogrula("(a) paralel=4: 20 dosyanin HEPSI yuklendi + manifest'te (KAYIP YOK)",
            yp == 20 and ap == 0 and len(yuklenen_par) == 20 and len(manifest_par) == 20,
            "y=%s a=%s yuklenen=%d manifest=%d" % (yp, ap, len(yuklenen_par), len(manifest_par)))

    # (b) ikinci kosum: hepsi manifest'te -> yuklendi=0
    yuklenen_par.clear()
    yp2, ap2, _, _ = r2.kos(par_dizin, par_idler, par_manifest, kuru=False,
                            yukle_fn=yavas_yukle, paralel=4)
    dogrula("(b) 2. kosum paralel: yuklendi=0 atlandi=20 (IDEMPOTENS)",
            yp2 == 0 and ap2 == 20 and yuklenen_par == [],
            "y=%s a=%s yeni-yukleme=%d" % (yp2, ap2, len(yuklenen_par)))

    # (olcum) paralel 4 suresi sirali (20*0.2=4.0 sn) yerine ~1/4 (~1.0 sn) olmali.
    # KABA SINIR: sirali/2'nin ALTINDA (=2.0 sn) -> paralellik fiilen calisiyor.
    dogrula("(olcum) paralel=4 suresi sirali'nin cok altinda (~1/4)",
            par_sure < 2.0, "par_sure=%.2f sn (sirali beklenen ~4.0, sinir <2.0)" % par_sure)

    # (c) paralel=1 eski davranisla BIREBIR: ayni sayilar, ayni manifest, ayni yukleme kumesi
    seri_dizin = tempfile.mkdtemp(prefix="stl-seri-")
    for i in range(20):
        with open(os.path.join(seri_dizin, "urun%02d.stl" % i), "wb") as f:
            f.write(b"icerik-%d" % i)
    seri_manifest = os.path.join(seri_dizin, ".manifest.json")
    yuklenen_seri = []

    def hizli_yukle(yerel, anahtar):
        yuklenen_seri.append(anahtar)
        return True

    ys, as_, hs, cs = r2.kos(seri_dizin, par_idler, seri_manifest, kuru=False,
                             yukle_fn=hizli_yukle, paralel=1)
    dogrula("(c) paralel=1 sayimlar eski davranisla ayni (y=20 a=0)",
            ys == 20 and as_ == 0 and len(yuklenen_seri) == 20,
            "y=%s a=%s" % (ys, as_))
    dogrula("(c) paralel=1 manifest paralel=4 ile AYNI anahtar kumesini uretir",
            set(r2.manifest_oku(seri_manifest)) == set(manifest_par),
            "seri=%d par=%d" % (len(r2.manifest_oku(seri_manifest)), len(manifest_par)))
    shutil.rmtree(par_dizin)
    shutil.rmtree(seri_dizin)

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()
