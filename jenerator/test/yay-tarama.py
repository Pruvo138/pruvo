#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAY AILESI DETERMINISTIK HACIM TARAMASI (fiyat ekseni).

NEDEN VAR: `dogrula.py` her kosumda RASTGELE tohum kullanir (dogrula.py:500).
Yesil bir kosum "bu tohumda kirmizi yok" demektir, "aile temiz" DEMEZ — yay
ailesinin ucgen kolundaki %3,96'lik sapma tam bu yuzden haftalarca gorunmedi
(olculdu 2026-08-03; tekrar: `dogrula.py yay --set 10 --seed 280903`, set9).
Bu surucu RASTGELE SET KULLANMAZ: semadan turetilen KURAL TABANLI izgarayi
bastan sona tarar, dal (secim parametreleri) basina EN KOTU sapmayi basar.

YER-GERCEGI TEK KAYNAKTAN: OpenSCAD render hacmi `dogrula.py`nin kendi
fonksiyonlariyla olculur (scad_hacim/js_hacimler/openscad_yolu). Ikinci bir
olcum yolu YAZILMAZ — ikiz tanim sessizce ayrisir.

IZGARA SEMADAN TURETILIR (elle enum YAZILMAZ): "secim" parametrelerinin TUM
degerleri; "sayi" parametrelerinin min/orta/max (--yogunluk ile sikilastirilir,
adim izgarasina oturtulur). Sema buyudugunde tarama kendiliginden genisler.

RENDER ONBELLEGI (SURDURULEBILIRLIK): tam izgara 810 render = ~50 dk. Yer-gercegi
AYNI girdide AYNIDIR, o yuzden render hacimleri diske onbelleklenir; anahtar
`sha256(.scad) | openscad surumu | tam -D bayrak listesi`dir — yani .scad ya da
OpenSCAD degisirse onbellek KENDILIGINDEN gecersizlesir (bayat yesil olmaz).
Onbellek her renderdan sonra atomik yazilir: kosum yarida kesilse bile kaldigi
yerden devam eder. Onbellek repo DISINDADIR (gecici dizin).

Kullanim:
  python3 yay-tarama.py                    # tam izgara (yogunluk 3)
  python3 yay-tarama.py --yogunluk 5
  python3 yay-tarama.py --aile yay --sinir 1.0
  python3 yay-tarama.py --onbellek yok     # onbellegi kullanma (her nokta yeniden render)
  python3 yay-tarama.py --kendini-test     # hukum mantigi (OpenSCAD/node GEREKMEZ)

Cikis kodu: 0 = en kotu <= sinir · 1 = sinir asildi · 3 = OLCULEMEDI (yesil sayilmaz).
"""
import argparse
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TEST_DIR)
import dogrula  # noqa: E402  (yer-gercegi yolu TEK KAYNAK)

VARSAYILAN_SINIR = 1.0
OLCULEMEDI_KODU = 3


# ---- IZGARA (semadan turetilir) --------------------------------------------
def sayi_izgarasi(p, yogunluk):
    """min..max arasi `yogunluk` adet nokta; hepsi sema adim izgarasina oturur.
    min ve max DAIMA icerdedir (uc noktalar en kotu sapmanin tipik yeridir)."""
    alt = float(p["min"])
    ust = float(p["max"])
    adim = float(p.get("adim") or 1)
    n = int(math.floor((ust - alt) / adim + 0.5))
    if yogunluk < 2 or n <= 0:
        return [round(alt, 6)]
    degerler = []
    for k in range(yogunluk):
        oran = k / float(yogunluk - 1)
        basamak = int(math.floor(n * oran + 0.5))
        deger = round(alt + basamak * adim, 6)
        if deger not in degerler:
            degerler.append(deger)
    return sorted(degerler)


def secim_degerleri(p):
    return [x["deger"] if isinstance(x, dict) else x for x in p["secenekler"]]


def izgara_uret(sema, yogunluk, eksen_yogunluk=None):
    """Semadan KURAL TABANLI tam izgara (kartezyen carpim).

    `eksen_yogunluk` = {parametre_adi: yogunluk} — TEK bir sayisal ekseni
    sikilastirmak icin (kartezyen carpim patlamasin diye digerleri seyrek
    birakilabilir). Enum eksenleri HER ZAMAN tam taranir, kisilamaz."""
    eksen_yogunluk = eksen_yogunluk or {}
    eksenler = []
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "secim":
            degerler = secim_degerleri(p)
        elif tip == "sayi":
            degerler = sayi_izgarasi(p, eksen_yogunluk.get(p["ad"], yogunluk))
        elif tip == "metin":
            degerler = [p.get("varsayilan", "")]
        else:
            sys.exit("bilinmeyen parametre tipi: %s (%s)" % (tip, p["ad"]))
        eksenler.append((p["ad"], degerler))
    setler = [{}]
    for ad, degerler in eksenler:
        yeni = []
        for taban in setler:
            for d in degerler:
                kopya = dict(taban)
                kopya[ad] = d
                yeni.append(kopya)
        setler = yeni
    return setler


def dal_anahtari(sema, sset):
    """Dal = TUM secim parametrelerinin degeri (semadan turetilir, elle yazilmaz)."""
    return tuple(sset[p["ad"]] for p in sema["parametreler"]
                 if p.get("tip", "sayi") == "secim")


# ---- HUKUM (saf fonksiyon — kendini-test bunu olcer) ------------------------
def ozet(sonuclar, sinir):
    """sonuclar: [(dal, sset, js, ref|None)] -> (tablo, en_kotu|None, olculemedi, cikis).

    FAIL-CLOSED: olculemeyen tek nokta bile YESIL SAYILMAZ; hic olcum yoksa da
    yesil DEGILDIR (sifir olculen set = yesil, bu depoda yasanmis bir delik)."""
    dallar = {}
    olculemedi = []
    for dal, sset, js, ref in sonuclar:
        kayit = dallar.setdefault(dal, {"en_kotu": None, "set": None, "adet": 0,
                                        "olculemedi": 0})
        if ref is None or not ref:
            kayit["olculemedi"] += 1
            olculemedi.append((dal, sset))
            continue
        sapma = abs(js - ref) / ref * 100.0
        kayit["adet"] += 1
        if kayit["en_kotu"] is None or sapma > kayit["en_kotu"]:
            kayit["en_kotu"] = sapma
            kayit["set"] = (sset, js, ref)
    tablo = []
    en_kotu = None
    for dal in sorted(dallar, key=lambda d: tuple(str(x) for x in d)):
        k = dallar[dal]
        tablo.append((dal, k["en_kotu"], k["set"], k["adet"], k["olculemedi"]))
        if k["en_kotu"] is not None and (en_kotu is None or k["en_kotu"] > en_kotu):
            en_kotu = k["en_kotu"]
    if olculemedi or en_kotu is None:
        cikis = OLCULEMEDI_KODU
    elif en_kotu > sinir:
        cikis = 1
    else:
        cikis = 0
    return tablo, en_kotu, olculemedi, cikis


def tabloyu_bas(tablo, en_kotu, olculemedi, sinir, cikis):
    print("\n%-28s %10s %8s %12s  %s" % ("DAL", "EN KOTU %", "NOKTA", "OLCULEMEDI",
                                         "EN KOTU SET"))
    for dal, ek, kayit, adet, olcx in tablo:
        ad = "/".join(str(x) for x in dal)
        if ek is None:
            print("%-28s %10s %8d %12d  -" % (ad, "OLCULEMEDI", adet, olcx))
            continue
        sset, js, ref = kayit
        detay = ", ".join("%s=%s" % (k, v) for k, v in sorted(sset.items())
                          if k not in dal and not isinstance(v, str))
        print("%-28s %10.3f %8d %12d  js=%.1f scad=%.1f  (%s)" % (
            ad, ek, adet, olcx, js, ref, detay))
    if olculemedi:
        print("\nOLCULEMEDI %d nokta — YESIL SAYILMAZ." % len(olculemedi))
    print("\nSINIR=%.2f" % sinir)
    print("ENKOTU=%s" % ("OLCULEMEDI" if en_kotu is None else "%.3f" % en_kotu))
    print("HUKUM=%s (cikis %d)" % (
        {0: "YESIL", 1: "KIRMIZI", OLCULEMEDI_KODU: "OLCULEMEDI"}[cikis], cikis))


# ---- RENDER ONBELLEGI -------------------------------------------------------
def onbellek_kimligi(openscad, scad_yol):
    """Onbellek gecerlilik kimligi: .scad govdesi + OpenSCAD surumu.
    Ikisinden biri degisirse TUM onbellek gecersizdir (bayat yesil olmaz)."""
    with io.open(scad_yol, "rb") as f:
        ozet = hashlib.sha256(f.read()).hexdigest()
    try:
        proc = subprocess.run([openscad, "--version"], capture_output=True, timeout=60)
        surum = (proc.stdout + proc.stderr).decode("utf-8", "replace").strip()
    except Exception as e:                                   # noqa: BLE001
        surum = "surum-okunamadi:%s" % e
    return "%s|%s" % (ozet, surum)


def onbellek_yukle(yol, kimlik):
    if not yol or not os.path.exists(yol):
        return {}
    try:
        with io.open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except Exception:                                        # noqa: BLE001
        return {}
    if veri.get("kimlik") != kimlik:
        return {}
    return veri.get("kayit") or {}


def onbellek_yaz(yol, kimlik, kayit):
    if not yol:
        return
    gecici = "%s.tmp.%d" % (yol, os.getpid())
    with io.open(gecici, "w", encoding="utf-8") as f:
        f.write(json.dumps({"kimlik": kimlik, "kayit": kayit}, ensure_ascii=False))
    os.replace(gecici, yol)


# ---- KOSUM ------------------------------------------------------------------
def tara(aile, yogunluk, sinir, onbellek_yolu, paralel, eksen_yogunluk=None):
    import fcntl
    kilit = open(os.path.join(TEST_DIR, ".dogrula-kilit"), "w")
    fcntl.flock(kilit, fcntl.LOCK_EX)
    proc = subprocess.run([sys.executable, os.path.join(TEST_DIR, "birlestir.py")],
                          capture_output=True)
    if proc.returncode != 0:
        sys.exit("birlestir.py hata:\n%s" % proc.stderr.decode("utf-8", "replace"))

    esleme = dogrula.yukle(os.path.join(dogrula.ESLEME_DIR, aile + ".json"))
    sema = dogrula.yukle(os.path.join(dogrula.URUN_DIR, esleme["urunId"] + ".json"))
    if sema.get("hacimFormulu") != esleme["fonksiyon"]:
        sys.exit("%s: sema.hacimFormulu != esleme.fonksiyon" % aile)
    scad_yol = os.path.join(dogrula.scad_dizini(), esleme["scad"])
    if not os.path.exists(scad_yol):
        sys.exit("scad dosyasi yok: %s" % scad_yol)
    openscad = dogrula.openscad_yolu()

    setler = izgara_uret(sema, yogunluk, eksen_yogunluk)
    kimlik = onbellek_kimligi(openscad, scad_yol)
    kayit = onbellek_yukle(onbellek_yolu, kimlik)
    print("aile=%s  izgara=%d nokta  yogunluk=%d%s  sinir=%%%.2f  onbellek=%s (%d kayit)" % (
        aile, len(setler), yogunluk,
        "".join("  %s=%d" % (k, v) for k, v in sorted((eksen_yogunluk or {}).items())),
        sinir, onbellek_yolu or "yok", len(kayit)))
    js = dogrula.js_hacimler(esleme["fonksiyon"], setler)

    anahtarlar = [" ".join(dogrula.d_bayraklari(esleme, s)) for s in setler]
    eksik = [i for i, a in enumerate(anahtarlar) if a not in kayit]
    print("  onbellekte %d nokta var, %d nokta RENDER edilecek (%d is parcacigi)" % (
        len(setler) - len(eksik), len(eksik), paralel))
    sys.stdout.flush()

    # RENDER PARALEL, SONUC SIRALI: her nokta kendi STL adina yazar (etiket = indeks),
    # onbellek kilit altinda guncellenir -> is parcacigi sayisi SONUCU DEGISTIRMEZ.
    import threading
    kilit_onb = threading.Lock()
    with tempfile.TemporaryDirectory() as tmpdir:
        bitti = [0]

        def render_et(i):
            ref = dogrula.scad_hacim(openscad, scad_yol, esleme, setler[i], tmpdir,
                                     "%s-%d" % (aile, i))
            with kilit_onb:
                bitti[0] += 1
                if ref is not None:
                    kayit[anahtarlar[i]] = ref
                    onbellek_yaz(onbellek_yolu, kimlik, kayit)
                if bitti[0] % 25 == 0 or bitti[0] == len(eksik):
                    print("  ... render %d/%d" % (bitti[0], len(eksik)))
                    sys.stdout.flush()
            return i, ref

        taze = {}
        if eksik:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max(1, paralel)) as havuz:
                for i, ref in havuz.map(render_et, eksik):
                    taze[i] = ref
        sonuclar = [(dal_anahtari(sema, s), s, js[i],
                     kayit.get(anahtarlar[i], taze.get(i)))
                    for i, s in enumerate(setler)]
    tablo, en_kotu, olculemedi, cikis = ozet(sonuclar, sinir)
    tabloyu_bas(tablo, en_kotu, olculemedi, sinir, cikis)
    return cikis


# ---- KENDINI TEST (OpenSCAD/node GEREKTIRMEZ) -------------------------------
def kendini_test():
    """Surucunun KENDI hukum ve izgara mantigi. Iki yon: izgara semayi TAM
    tariyor mu (dar izgara = kor tarama) + hukum fail-closed mi (olculemeyen
    nokta / bos olcum kumesi YESIL SAYILMAZ)."""
    vakalar = []

    def bekle(ad, kosul, detay=""):
        vakalar.append((ad, bool(kosul), detay))

    sema = {"parametreler": [
        {"ad": "tip", "tip": "secim", "secenekler": [
            {"deger": "a"}, {"deger": "b"}, {"deger": "c"}]},
        {"ad": "form", "tip": "secim", "secenekler": ["x", "y"]},
        {"ad": "boy", "tip": "sayi", "min": 40, "max": 120, "adim": 1},
        {"ad": "kalinlik", "tip": "sayi", "min": 1.5, "max": 4, "adim": 0.5},
    ]}

    izgara = izgara_uret(sema, 3)
    bekle("I1 kartezyen tam (3*2*3*3)", len(izgara) == 54, "adet=%d" % len(izgara))
    bekle("I2 secim: TUM enum degerleri taraniyor",
          set(s["tip"] for s in izgara) == set(["a", "b", "c"]) and
          set(s["form"] for s in izgara) == set(["x", "y"]),
          "tip=%s form=%s" % (sorted(set(s["tip"] for s in izgara)),
                              sorted(set(s["form"] for s in izgara))))
    boylar = sorted(set(s["boy"] for s in izgara))
    bekle("I3 sayi: min/orta/max icerde", boylar == [40.0, 80.0, 120.0], "%s" % boylar)
    kal = sorted(set(s["kalinlik"] for s in izgara))
    izgarada = all(abs((v - 1.5) / 0.5 - round((v - 1.5) / 0.5)) < 1e-9 for v in kal)
    bekle("I4 sayi: uc noktalar + TUM degerler adim izgarasinda",
          kal[0] == 1.5 and kal[-1] == 4.0 and len(kal) == 3 and izgarada, "%s" % kal)
    yogun = sorted(set(s["boy"] for s in izgara_uret(sema, 5)))
    bekle("I5 yogunluk artinca izgara SIKLASIR",
          len(yogun) == 5 and yogun[0] == 40.0 and yogun[-1] == 120.0, "%s" % yogun)
    tek = izgara_uret(sema, 1, {"boy": 9})
    boy9 = sorted(set(s["boy"] for s in tek))
    bekle("I5b tek eksen sikilastirilir, digerleri seyrek kalir",
          len(boy9) == 9 and boy9[0] == 40.0 and boy9[-1] == 120.0 and
          len(set(s["kalinlik"] for s in tek)) == 1 and len(tek) == 3 * 2 * 9,
          "boy=%s adet=%d" % (boy9, len(tek)))
    bekle("I5c eksen sikistirmasi ENUM eksenlerini KISMAZ (kor tarama olmaz)",
          set(s["tip"] for s in tek) == set(["a", "b", "c"]) and
          set(s["form"] for s in tek) == set(["x", "y"]))
    bekle("I6 dal anahtari = TUM secim parametreleri",
          dal_anahtari(sema, izgara[0]) == (izgara[0]["tip"], izgara[0]["form"]),
          "%s" % (dal_anahtari(sema, izgara[0]),))

    d1 = ("a", "x")
    d2 = ("b", "y")
    hepsi_yesil = [(d1, {"boy": 40}, 100.0, 100.4), (d2, {"boy": 40}, 100.0, 100.2)]
    tablo, ek, olcx, cikis = ozet(hepsi_yesil, 1.0)
    bekle("H1 temiz kosum YESIL + en kotu dogru dal",
          cikis == 0 and abs(ek - 0.3984) < 1e-3 and len(tablo) == 2,
          "cikis=%s enkotu=%s" % (cikis, ek))
    tablo, ek, olcx, cikis = ozet(
        hepsi_yesil + [(d1, {"boy": 120}, 100.0, 102.5)], 1.0)
    bekle("H2 sinir asilinca KIRMIZI", cikis == 1 and ek > 2.4,
          "cikis=%s enkotu=%s" % (cikis, ek))
    tablo, ek, olcx, cikis = ozet(
        hepsi_yesil + [(d1, {"boy": 120}, 100.0, None)], 1.0)
    bekle("H3 tek olculemeyen nokta YESIL SAYILMAZ (digerleri yesilken)",
          cikis == OLCULEMEDI_KODU and len(olcx) == 1, "cikis=%s" % cikis)
    tablo, ek, olcx, cikis = ozet(
        hepsi_yesil + [(d1, {"boy": 120}, 100.0, 0.0)], 1.0)
    bekle("H4 sifir referans hacim YESIL SAYILMAZ (0'a bolme yerine OLCULEMEDI)",
          cikis == OLCULEMEDI_KODU, "cikis=%s" % cikis)
    tablo, ek, olcx, cikis = ozet([], 1.0)
    bekle("H5 hic olcum yoksa YESIL DEGIL (sifir set = yesil deligi)",
          cikis == OLCULEMEDI_KODU and ek is None, "cikis=%s enkotu=%s" % (cikis, ek))
    tablo, ek, olcx, cikis = ozet(
        [(d1, {"boy": 40}, 100.0, 100.4), (d1, {"boy": 120}, 100.0, 100.9)], 1.0)
    bekle("H6 dal basina EN KOTU (ortalama degil) raporlanir",
          abs(tablo[0][1] - 0.8920) < 1e-3, "dal en kotu=%s" % tablo[0][1])
    tablo, ek, olcx, cikis = ozet(
        [(d1, {"boy": 40}, 100.0, 100.4), (d2, {"boy": 40}, 100.0, None)], 1.0)
    bekle("H7 bir dal tumden olculemedi -> tabloda OLCULEMEDI satiri + cikis 3",
          cikis == OLCULEMEDI_KODU and
          any(satir[1] is None for satir in tablo), "tablo=%s" % (tablo,))

    # --- ONBELLEK: bayat yesil uretemez ---
    tmp = tempfile.mkdtemp(prefix="pruvo-yay-onbellek-")
    yol = os.path.join(tmp, "onb.json")
    onbellek_yaz(yol, "kimlik-A", {"-D x=1": 123.0})
    bekle("O1 ayni kimlikte onbellek okunur",
          onbellek_yukle(yol, "kimlik-A") == {"-D x=1": 123.0},
          "%s" % onbellek_yukle(yol, "kimlik-A"))
    bekle("O2 kimlik degisince onbellek TUMDEN gecersiz (.scad/OpenSCAD degisti)",
          onbellek_yukle(yol, "kimlik-B") == {}, "%s" % onbellek_yukle(yol, "kimlik-B"))
    with io.open(yol, "w", encoding="utf-8") as _f:
        _f.write("{bozuk")
    bekle("O3 bozuk onbellek dosyasi COKERTMEZ, bos sayilir",
          onbellek_yukle(yol, "kimlik-A") == {})
    bekle("O4 onbellek dosyasi yoksa bos", onbellek_yukle(os.path.join(tmp, "yok.json"),
                                                          "kimlik-A") == {})
    import shutil as _sh
    _sh.rmtree(tmp, ignore_errors=True)

    kirmizi = [v for v in vakalar if not v[1]]
    print("YAY TARAMA SURUCUSU — KENDINI TEST: %d/%d YESIL" % (
        len(vakalar) - len(kirmizi), len(vakalar)))
    for ad, yesil, detay in vakalar:
        print("  %s %-52s %s" % ("+" if yesil else "-", ad, detay if not yesil else ""))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aile", default="yay")
    ap.add_argument("--yogunluk", type=int, default=3,
                    help="her sayisal parametre icin izgara nokta sayisi (min..max)")
    ap.add_argument("--sinir", type=float, default=VARSAYILAN_SINIR,
                    help="kabul sinirI (%%). Allowlist esigi 1.0 (mimar hukmu).")
    ap.add_argument("--onbellek", default=os.path.join(
        tempfile.gettempdir(), "pruvo-yay-tarama-onbellek.json"),
        help="render onbellegi yolu ('yok' -> onbelleksiz)")
    ap.add_argument("--paralel", type=int, default=4,
                    help="es zamanli render sayisi (sonucu DEGISTIRMEZ, sureyi kisaltir)")
    ap.add_argument("--yogunluk-eksen", action="append", default=[],
                    metavar="AD=N",
                    help="tek bir sayisal ekseni sikilastir (or. dalga_boyu=41); "
                         "izgara noktalari arasinda gizlenen tepe icin")
    ap.add_argument("--kendini-test", action="store_true")
    args = ap.parse_args()
    if args.kendini_test:
        sys.exit(kendini_test())
    eksen = {}
    for kalem in args.yogunluk_eksen:
        if "=" not in kalem:
            sys.exit("--yogunluk-eksen bicimi: AD=N (alinan: %r)" % kalem)
        ad, deger = kalem.split("=", 1)
        eksen[ad] = int(deger)
    onbellek = None if args.onbellek == "yok" else args.onbellek
    sys.exit(tara(args.aile, args.yogunluk, args.sinir, onbellek, args.paralel, eksen))


if __name__ == "__main__":
    main()
