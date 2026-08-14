#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABS KAPISI — MUTASYON BATARYASI (nobetci olu mu?).

    python3 tools/abs-kapisi-mutasyon.py

NE YAPAR: `shop/test/abs-kapisi.mjs` kabul testinin ONCE-KIRMIZI kanitini uretir.
Her mutant, kaynagin GECICI KOPYASINA uygulanir ve test o kopyaya ortam degiskeniyle
yonlendirilir; DEPO DOSYASI HIC DEGISMEZ (bas/son sha256 karsilastirilir).

🔴 NEDEN VAR: "testler yesil" tek basina bir sey soylemez — once yesilin NEYI olctugu
sorulur ([[test-hatali-davranisi-kutsar]]). Anlatilan batarya kanit degildir; bu betik
kaniti YENIDEN URETILEBILIR kilar ([[mutasyon-kaniti-yeniden-uretilebilir]]).

MUTANTLAR (hepsi KIRMIZI bekler):
  N1  ABS katsayisi ELLE sabit (50), ASA'dan turemez          -> vaka 1
  N2  kategori suzgeci Worker'dan kaldirilir (yalniz UI)      -> vaka 5
  N3  haric listesinden "Dekorasyon" cikarilir                -> vaka 4
  N4  kategori cozulemezse ABS GOSTERILIR (fail-open)         -> vaka 7
  N5  Skan Art konfigur malzemelerine ABS eklenir             -> vaka 8
  N6  Karbon Katkili site:true yapilir                        -> vaka 9
KONTROLLER (YESIL bekler):
  K0  yalnizca yorum satiri degistirilir (davranis AYNI)
  K1  daraltilmis urunler.json (mutasyonsuz) — N5'in fiksturu kendi basina masum

CIKIS KODU: 0 = tum mutantlar kirmizi + tum kontroller yesil · 1 = eksik oldurme ·
3 = olculemedi (node/kaynak yok, depo dosyasi degismis).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST = os.path.join(KOK, "shop", "test", "abs-kapisi.mjs")
SECENEKLER = os.path.join(KOK, "secenekler.js")
SHOP_SRC = os.path.join(KOK, "shop", "src")
URUNLER = os.path.join(KOK, "urunler.json")
FILAMENTLER = os.path.join(KOK, "tools", "filamentler.json")

IZLENEN = [SECENEKLER, os.path.join(SHOP_SRC, "index.js"), URUNLER, FILAMENTLER,
           os.path.join(KOK, "tools", "build.py")]


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def damga():
    return {y: sha(y) for y in IZLENEN}


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def yaz(yol, metin):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def testi_kostur(cevre):
    ortam = dict(os.environ)
    ortam.update(cevre)
    p = subprocess.run(["node", TEST], cwd=KOK, env=ortam,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cikti = p.stdout.decode("utf-8", "replace")
    kirmizi = [s.strip()[2:].strip() for s in cikti.split("\n") if s.strip().startswith("❌")]
    return p.returncode, kirmizi, cikti


# ---------------------------------------------------------------- mutant kurucular
def m_secenekler(gecici, donusum, etiket):
    """secenekler.js'in mutant kopyasi -> {PRUVO_ABS_SECENEKLER: <yol>}"""
    kaynak = oku(SECENEKLER)
    yeni = donusum(kaynak)
    if yeni == kaynak:
        raise SystemExit("MUTASYON UYGULANAMADI (%s): capa bulunamadi — betik bayat." % etiket)
    yol = os.path.join(gecici, "secenekler.js")
    yaz(yol, yeni)
    return {"PRUVO_ABS_SECENEKLER": yol}


def m_index(gecici, donusum, etiket):
    """shop/src'in mutant kopyasi (yalniz index.js degisir) -> {PRUVO_ABS_SHOP_SRC: <dizin>}"""
    hedef = os.path.join(gecici, "src")
    shutil.copytree(SHOP_SRC, hedef)
    yol = os.path.join(hedef, "index.js")
    kaynak = oku(yol)
    yeni = donusum(kaynak)
    if yeni == kaynak:
        raise SystemExit("MUTASYON UYGULANAMADI (%s): capa bulunamadi — betik bayat." % etiket)
    yaz(yol, yeni)
    return {"PRUVO_ABS_SHOP_SRC": hedef}


def _konfigur_urunler():
    with open(URUNLER, encoding="utf-8") as f:
        return [u for u in json.load(f) if u.get("konfigur")]


def m_urunler(gecici, abs_ekle):
    """DARALTILMIS urunler.json (yalniz konfigur urunleri). abs_ekle=True ise ilkine ABS sizar.

    Tam katalogun kopyasi CIKARILMAZ: gereksiz ~30 MB gecici dosya uretmemek icin
    (disk kurali) ve testin bu setinin okudugu TEK sey konfigur kolu oldugu icin."""
    urunler = _konfigur_urunler()
    if abs_ekle:
        if not urunler:
            raise SystemExit("MUTASYON UYGULANAMADI (N5): konfigur urunu yok.")
        urunler[0]["konfigur"]["malzemeler"].append({"ad": "ABS", "katsayi": 1.6})
    yol = os.path.join(gecici, "urunler.json")
    yaz(yol, json.dumps(urunler, ensure_ascii=False))
    return {"PRUVO_ABS_URUNLER": yol}


def m_filamentler(gecici):
    """filamentler.json kopyasi: Karbon Katkili site:true (kapsam sizmasi mutanti)."""
    with open(FILAMENTLER, encoding="utf-8") as f:
        ref = json.load(f)
    bulundu = 0
    for fil in ref["filamentler"]:
        if fil["ad"] == "Karbon Katkılı":
            fil["site"] = True
            bulundu += 1
    if bulundu != 1:
        raise SystemExit("MUTASYON UYGULANAMADI (N6): Karbon kaydi bulunamadi.")
    yol = os.path.join(gecici, "filamentler.json")
    yaz(yol, json.dumps(ref, ensure_ascii=False, indent=2) + "\n")
    return {"PRUVO_ABS_FILAMENTLER": yol}


# ---------------------------------------------------------------- donusumler
def d_n1(s):
    """ABS katsayisi ELLE sabit; turetme haritasi bosaltilir."""
    s = s.replace('var FILAMENT_TUREME = { "ABS": "ASA" };', "var FILAMENT_TUREME = {};")
    return s.replace('var FILAMENT_FARK = { "PLA": 0, "PETG": 30, "ASA": 60, "TPU": 55 };',
                     'var FILAMENT_FARK = { "PLA": 0, "PETG": 30, "ASA": 60, "TPU": 55, '
                     '"ABS": 50 };')


def d_n2(s):
    """Kategori suzgeci Worker'dan kalkar (UI'da kalir) — olculen 'gizlemek yetmez' sinifi."""
    bas = s.find("    if (!SECENEK.malzemeKategoriUygunMu(k.malzeme, u.kategori)) {")
    if bas < 0:
        return s
    son = s.find("    }\n", bas)
    if son < 0:
        return s
    return s[:bas] + s[son + len("    }\n"):]


def d_n3(s):
    return s.replace('"ABS": ["Ev", "Ofis", "Dekorasyon", "Skan Art", "Oyun/Hobi"]',
                     '"ABS": ["Ev", "Ofis", "Skan Art", "Oyun/Hobi"]')


def d_n4(s):
    """Kategori cozulemezse ABS GOSTERILIR (fail-open yon)."""
    return s.replace(
        'if (typeof kategori !== "string" || !_kategoriTaninirMi(kategori)) { return false; }',
        'if (typeof kategori !== "string" || !_kategoriTaninirMi(kategori)) { return true; }')


def d_k0(s):
    """KONTROL: yalniz yorum degisir — davranis AYNI kalmali (batarya yanlis-pozitif vermesin)."""
    return s.replace("// PLA taban (fark yok); yüzdeler PLA fiyatına göre ek maliyet.",
                     "// PLA taban (fark yok); yuzdeler PLA fiyatina gore ek maliyet. [K0 kontrol]")


# ---------------------------------------------------------------- kosum
def main():
    if not os.path.exists(TEST):
        print("ÖLÇÜLEMEDİ: kabul testi yok -> %s" % TEST)
        return 3
    bas = damga()

    mutantlar = [
        ("N1", "ABS katsayisi elle sabit (50), ASA'dan turemez", "KIRMIZI",
         lambda g: m_secenekler(g, d_n1, "N1")),
        ("N2", "kategori suzgeci Worker'dan kaldirildi", "KIRMIZI",
         lambda g: m_index(g, d_n2, "N2")),
        ("N3", "haric listesinden Dekorasyon cikarildi", "KIRMIZI",
         lambda g: m_secenekler(g, d_n3, "N3")),
        ("N4", "kategori cozulemezse ABS GOSTERILIR (fail-open)", "KIRMIZI",
         lambda g: m_secenekler(g, d_n4, "N4")),
        ("N5", "Skan Art konfigur malzemelerine ABS eklendi", "KIRMIZI",
         lambda g: m_urunler(g, True)),
        ("N6", "Karbon Katkili site:true", "KIRMIZI",
         lambda g: m_filamentler(g)),
        ("K0", "yalnizca yorum degisti (kontrol)", "YESIL",
         lambda g: m_secenekler(g, d_k0, "K0")),
        ("K1", "daraltilmis urunler.json, mutasyon YOK (kontrol)", "YESIL",
         lambda g: m_urunler(g, False)),
    ]

    sonuclar = []
    for ad, aciklama, beklenen, kurucu in mutantlar:
        gecici = tempfile.mkdtemp(prefix="pruvo-abs-mut-%s-" % ad)
        try:
            cevre = kurucu(gecici)
            rc, kirmizi, cikti = testi_kostur(cevre)
            gerceklesen = "YESIL" if rc == 0 else ("KIRMIZI" if rc == 1 else "OLCULEMEDI(rc=%d)" % rc)
            tamam = gerceklesen == beklenen
            sonuclar.append((ad, aciklama, beklenen, gerceklesen, tamam, kirmizi, cikti))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    son = damga()
    print("")
    print("=" * 78)
    print("ABS KAPISI — MUTASYON BATARYASI")
    print("=" * 78)
    for ad, aciklama, beklenen, gerceklesen, tamam, kirmizi, cikti in sonuclar:
        isaret = "✅" if tamam else "❌"
        print("%s %-3s %-52s bekl=%-7s ger=%s" % (isaret, ad, aciklama[:52], beklenen,
                                                  gerceklesen))
        if kirmizi:
            for k in kirmizi[:4]:
                print("        ↳ %s" % k[:110])
            if len(kirmizi) > 4:
                print("        ↳ ... (+%d kirmizi iddia)" % (len(kirmizi) - 4))
        if not tamam and not kirmizi:
            print("        ↳ SON 15 SATIR:")
            for s in cikti.strip().split("\n")[-15:]:
                print("          %s" % s[:110])

    oldurulen = sum(1 for s in sonuclar if s[2] == "KIRMIZI" and s[4])
    kirmiziBeklenen = sum(1 for s in sonuclar if s[2] == "KIRMIZI")
    kontrolYesil = sum(1 for s in sonuclar if s[2] == "YESIL" and s[4])
    kontrolSayisi = sum(1 for s in sonuclar if s[2] == "YESIL")

    print("")
    if son != bas:
        farkli = [os.path.relpath(y, KOK) for y in IZLENEN if bas[y] != son[y]]
        print("🔴 DEPO DOSYASI DEGISMIS (batarya kirli): %s" % ", ".join(farkli))
        return 3
    print("DEPO KAYNAKLARI DEGISMEDI (bas/son sha256 birebir): %d dosya" % len(IZLENEN))
    print("MUTANT_KIRMIZI=%d/%d KONTROL_YESIL=%d/%d"
          % (oldurulen, kirmiziBeklenen, kontrolYesil, kontrolSayisi))
    return 0 if (oldurulen == kirmiziBeklenen and kontrolYesil == kontrolSayisi) else 1


if __name__ == "__main__":
    sys.exit(main())
