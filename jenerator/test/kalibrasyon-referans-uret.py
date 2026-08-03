#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kalibrasyon-senkron.js referans fixture'ini uretir (mimar/muhendis araci).

Konektor + braket + disli (olcuye gore uretec v2 aileleri) + adaptor + kutu +
kavanoz (yeni sari aileler 1. dalga, 2026-07-17) icin sema-gecerli
deterministik parametre setlerini GERCEK openscad render'iyla olcer ve
kalibrasyon-referans.json'a yazar. Referanslar dondurulur: test (node
kalibrasyon-senkron.js) openscad'siz her yerde kosar.

IKI MOTOR YOLU (esleme/<aile>.json `motor` alanindan secilir):
  motor=pruvo  -> PRUVO_SCAD_DIR altindaki uretec + esleme/<aile>.json eslemesi
  motor=uretim -> GIZLI uretim paketi (onizleme-paket-yukle.py --yerel) +
                  eslem-ozel.json eslemesi, -D bayraklari server.py'nin KENDI
                  d_bayraklari'ndan (onizleme derleme yolunun birebir aynisi).
Ikinci yol 3 Agu 2026'da eklendi: rampa `motor=uretim` oldugu halde HICBIR
dondurulmus referansi yoktu; kalibrasyon-senkron.js 3. katmani da onu
`disi_birakilan` sayiyordu. Sonuc: uretim motoruna karsi ailenin hacmini
CI'da olcen TEK BIR KAPI YOKTU ve tirtikli kolundaki yanlis motor sabiti
(1,6 mm2 = PRUVO tirtigi) hicbir yeri kirmizi yakmadan durdu.

Kullanim: python3 jenerator/test/kalibrasyon-referans-uret.py
Ortam: PRUVO_SCAD_DIR (vars. ~/dev/pruvo-jenerator/jeneratorler), PRUVO_OPENSCAD
"""
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
sys.path.insert(0, TEST_DIR)
import dogrula     # noqa: E402
import stl_hacim   # noqa: E402

AILELER = ["konektor", "braket", "disli", "adaptor", "kutu", "kavanoz", "rampa"]
TOHUM = 42
RASTGELE_SET = 6

# 🔴 FIKSTUR KORLUGU NOBETI (olculdu 3 Agu 2026).
# Kapi TOPLAM hacmin %3'une bakar. Bir kolun katkisi toplamin kucuk bir yuzdesiyse
# o koldaki BUYUK bir model hatasi toplamda %3'un ALTINDA kalir ve fikstur mutanti
# kor eder ([[fikstur-degeri-mutasyon-koru.md]]). Rampada tirtik katkisi ancak INCE
# rampada (kucuk yukseklik / buyuk uzunluk) toplamin anlamli bir parcasidir:
#   h=2,  u=245 -> tirtik payi ~%28,6  (kesit sabitinde %10 hata = toplamda ~%2,9)
#   h=50, u=160 -> tirtik payi ~%1,7   (ayni %10 hata = toplamda ~%0,17, GORUNMEZ)
# Bu yuzden rastgele izgaraya BIRAKILMAZ: kolun gorunur oldugu bolge ACIKCA
# fiksture konur, YANINDA ayni olcude duz/basamakli KONTROL setleriyle birlikte
# (kontrol olmadan kirmizi, "kol bozuldu"nun degil "her sey bozuldu"nun kanitidir).
ZORUNLU_SETLER = {
    "rampa": [
        {"genislik": 150, "uzunluk": 245, "yukseklik": 2,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "tirtikli"},
        {"genislik": 60, "uzunluk": 250, "yukseklik": 2,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "tirtikli"},
        {"genislik": 60, "uzunluk": 160, "yukseklik": 6,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "tirtikli"},
        # 🔴 DIK RAMPA — terimin BIRIMINI ayirt eden TEK set (olculdu 3 Agu 2026).
        # Yukaridaki setlerin hepsi kucuk acili (H<<L) ve orada egim boyu ile
        # uzunluk neredeyse esittir: "egim mm'si basina" yerine "uzunluk mm'si
        # basina" yazan bir mutant o setlerde %3'un ALTINDA kalir ve YESIL gecer
        # (batarya bunu once fiilen gosterdi: mutant hayatta kaldi). L=20/H=100'de
        # sec(egim) buyudugu icin ayni birim hatasi toplamda ~%3,15 -> KIRMIZI.
        {"genislik": 150, "uzunluk": 20, "yukseklik": 100,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "tirtikli"},
        # KONTROL kolu — AYNI olculerde, yalniz ust_yuzey farkli
        {"genislik": 150, "uzunluk": 245, "yukseklik": 2,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "duz"},
        {"genislik": 150, "uzunluk": 245, "yukseklik": 2,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "basamakli"},
        {"genislik": 60, "uzunluk": 160, "yukseklik": 6,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "duz"},
        {"genislik": 60, "uzunluk": 160, "yukseklik": 6,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "basamakli"},
        {"genislik": 150, "uzunluk": 20, "yukseklik": 100,
         "egim_yontemi": "yukseklik", "egim_acisi": 15, "ust_yuzey": "duz"},
    ],
}


def sirli_repo():
    """Paketin SIR kaynaklarini (eslem-ozel.json) tasiyan checkout'u bulur.

    Bu dosyalar gitignore'ludur -> WORKTREE'de YOKTUR, yalniz ana checkout'ta
    bulunur. Ana checkout'u sabit yol yazmadan git'in kendisine sordurur
    (--git-common-dir her worktree'de ANA depoyu gosterir)."""
    if os.path.exists(os.path.join(REPO, "onizleme", "derleyici",
                                   "eslem-ozel.json")):
        return REPO
    proc = subprocess.run(
        ["git", "-C", REPO, "rev-parse", "--path-format=absolute",
         "--git-common-dir"], capture_output=True)
    if proc.returncode == 0:
        ana = os.path.dirname(proc.stdout.decode("utf-8").strip())
        if os.path.exists(os.path.join(ana, "onizleme", "derleyici",
                                       "eslem-ozel.json")):
            return ana
    return REPO


def uretim_paketi():
    """GIZLI uretim paketini yerel gecici dizine toplar (eslem-olcum.py ile ayni
    yol). FAIL-CLOSED: toplanamazsa uretim motorlu aile OLCULEMEZ, sessizce
    pruvo yoluna DUSMEZ."""
    hedef = tempfile.mkdtemp(prefix="kalib-uretim-paket-")
    kaynak = sirli_repo()
    proc = subprocess.run(
        [sys.executable, os.path.join(kaynak, "tools", "onizleme-paket-yukle.py"),
         "--yerel", hedef], capture_output=True)
    if proc.returncode != 0:
        sys.exit("uretim paketi toplanamadi (motor=uretim ailesi olculemez):\n%s%s" %
                 (proc.stdout.decode("utf-8", "replace"),
                  proc.stderr.decode("utf-8", "replace")))
    return hedef


def uretim_sunucusu():
    spec = importlib.util.spec_from_file_location(
        "onizleme_server", os.path.join(REPO, "onizleme", "derleyici", "server.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def uretim_hacim(openscad, server, eslem_aile, paket, sset, tmpdir, etiket):
    """motor=uretim ailesi icin gercek uretim motoru render'i -> mm3."""
    bayraklar, sebep = server.d_bayraklari(eslem_aile, sset)
    if bayraklar is None:
        sys.exit("%s: uretim eslemi seti reddetti (%s): %s" %
                 (etiket, sebep, json.dumps(sset, ensure_ascii=False)))
    stl = os.path.join(tmpdir, "%s.stl" % etiket)
    komut = ([openscad, "-o", stl, "--export-format", "binstl"] +
             server.OPENSCAD_EK_BAYRAKLAR + bayraklar +
             [os.path.join(paket, eslem_aile["scad"])])
    proc = subprocess.run(komut, capture_output=True, timeout=600)
    if proc.returncode != 0 or not os.path.exists(stl):
        sys.exit("%s: uretim motoru render hatasi:\n%s" %
                 (etiket, proc.stderr.decode("utf-8", "replace")[-2000:]))
    return stl_hacim.hacim(stl)


def yukle(yol):
    with io.open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    # --aile <ad> [...]: YALNIZ verilen aileleri yeniden olcer ve mevcut dosyaya
    # ISLER; dokunulmayan ailelerin dondurulmus degerleri AYNEN korunur.
    # Sebep: tam yeniden uretim, ilgisiz ailelerin referanslarini da o anki
    # makine/openscad surumune gore SESSIZCE tabana oturtur — yani baska bir
    # ailenin bugunku sapmasini "referansi ona esitleyerek" kutsayabilir.
    hedef_aileler = AILELER
    if "--aile" in sys.argv:
        hedef_aileler = [a for a in sys.argv[sys.argv.index("--aile") + 1:]
                         if not a.startswith("-")]
        bilinmeyen = [a for a in hedef_aileler if a not in AILELER]
        if not hedef_aileler or bilinmeyen:
            sys.exit("--aile: bilinmeyen/eksik aile %s (bilinen: %s)" %
                     (bilinmeyen or "-", ", ".join(AILELER)))

    openscad = dogrula.openscad_yolu()
    scad_dir = dogrula.scad_dizini()
    server = None
    paket = None
    yol = os.path.join(TEST_DIR, "kalibrasyon-referans.json")
    cikti = {"_not": ("Referans hacimler gercek OpenSCAD STL olcumu; "
                      "uretim: kalibrasyon-referans-uret.py, tohum=%d" % TOHUM),
             "aileler": {}}
    if hedef_aileler is not AILELER:
        if not os.path.exists(yol):
            sys.exit("--aile kismi uretim icin mevcut fikstur gerekli: %s" % yol)
        cikti = yukle(yol)
    for aile in hedef_aileler:
        esleme = yukle(os.path.join(TEST_DIR, "esleme", aile + ".json"))
        sema = yukle(os.path.join(TEST_DIR, "..", "urunler",
                                  esleme["urunId"] + ".json"))
        motor = esleme.get("motor", "pruvo")
        eslem_aile = None
        if motor == "uretim":
            if server is None:
                server = uretim_sunucusu()
                paket = uretim_paketi()
            eslem_aile = yukle(os.path.join(
                paket, "eslem-ozel.json"))["aileler"][esleme["urunId"]]
        rnd = random.Random(TOHUM)
        setler = [dogrula.varsayilan_set(sema)]
        setler.extend(ZORUNLU_SETLER.get(aile, []))
        # secim parametrelerinin HER degeri en az bir sette gecsin
        # (disli tipleri gibi dallanan geometriler tek rastgeleye kalmasin)
        for p in sema["parametreler"]:
            if p.get("tip") == "secim":
                for secenek in p["secenekler"]:
                    deger = secenek["deger"] if isinstance(secenek, dict) \
                        else secenek
                    s = dogrula.rastgele_set(sema, rnd)
                    s[p["ad"]] = deger
                    setler.append(s)
        for _ in range(RASTGELE_SET):
            setler.append(dogrula.rastgele_set(sema, rnd))
        kayitlar = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, sset in enumerate(setler):
                etiket = "%s-%d" % (aile, i)
                if motor == "uretim":
                    ref = uretim_hacim(openscad, server, eslem_aile, paket,
                                       sset, tmpdir, etiket)
                else:
                    ref = dogrula.scad_hacim(
                        openscad, os.path.join(scad_dir, esleme["scad"]),
                        esleme, sset, tmpdir, etiket)
                if ref is None:
                    sys.exit("%s set%d: openscad israrla cokuyor" % (aile, i))
                kayitlar.append({"parametreler": sset, "referansMm3": ref})
                print("  %s set%-2d referans=%.1f mm3" % (aile, i, ref))
        cikti["aileler"][aile] = {
            "fonksiyon": esleme["fonksiyon"],
            "urunId": esleme["urunId"],
            "motor": motor,
            "setler": kayitlar,
        }
    with io.open(yol, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=1)
    print("yazildi: %s (%d aile olculdu, dosyada %d aile)" %
          (yol, len(hedef_aileler), len(cikti["aileler"])))


if __name__ == "__main__":
    main()
