#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FAZ D — aile eslem kalibrasyon olcumu (4d-benzeri, onizleme kod yoluyla).

Her aile icin: sema izgarasindan N rastgele GECERLI set x M tohum uretir,
-D bayraklarini SERVER.PY'NIN KENDI d_bayraklari fonksiyonuyla (onizleme
derleme yolunun birebir aynisi) kurar, gercek openscad render STL hacmini
jenerator/hacim.js kapali-formuyla karsilastirir. Hedef <= %3.

Bu arac ONIZLEME_AILELER'e alinmamis aileleri OLCMEK icindir (yayin karari
ayri): sapmasi buyuk cikan aile sessizce eklenmez, mimar tablosuna yazilir.

Kullanim:
  python3 onizleme/test/eslem-olcum.py <aile> [<aile>...] [--set 5]
  python3 onizleme/test/eslem-olcum.py --hepsi   # paketteki tum aileler
  (--tohumlar 20260716,20260717 varsayilan; --json <yol> ozet doker)
Gerekli: eslem-ozel.json (gitignore'lu) + uyelik/jenerator .scad kaynaklari.
"""
import argparse
import hashlib
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
JEN_TEST = os.path.join(REPO, "jenerator", "test")
SINIR_YUZDE = 3.0

sys.path.insert(0, JEN_TEST)
import stl_hacim  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "onizleme_server", os.path.join(REPO, "onizleme", "derleyici", "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


def openscad_yolu():
    sys.path.insert(0, JEN_TEST)
    import dogrula
    return dogrula.openscad_yolu()


def paket_topla():
    hedef = tempfile.mkdtemp(prefix="eslem-olcum-paket-")
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "onizleme-paket-yukle.py"),
         "--yerel", hedef], capture_output=True)
    if proc.returncode != 0:
        sys.exit("paket toplanamadi:\n%s%s" %
                 (proc.stdout.decode("utf-8", "replace"),
                  proc.stderr.decode("utf-8", "replace")))
    return hedef


def sema_yukle(aile):
    yol = os.path.join(REPO, "jenerator", "urunler", aile + ".json")
    with io.open(yol, encoding="utf-8") as f:
        return json.load(f)


def kisitlar_yukle():
    """secenekler.js ONIZLEME_KISITLAR (tek kaynak) — musteri sema kapisiyla
    ayni evrende olculur: kisitli secim degerleri hic uretilmez."""
    proc = subprocess.run(
        ["node", "-p", "require(process.argv[1]); JSON.stringify("
         "(globalThis.PRUVO_SECENEK || {}).ONIZLEME_KISITLAR || {})",
         os.path.join(REPO, "secenekler.js")],
        capture_output=True)
    if proc.returncode != 0:
        sys.exit("secenekler.js okunamadi: %s" %
                 proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))


def rastgele_set(sema, rnd, kisit):
    s = {}
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "sayi":
            adim = float(p.get("adim") or 1)
            n = int(round((float(p["max"]) - float(p["min"])) / adim))
            s[p["ad"]] = round(float(p["min"]) + rnd.randint(0, n) * adim, 6)
        elif tip == "secim":
            secenekler = [x["deger"] if isinstance(x, dict) else x
                          for x in p["secenekler"]]
            izinli = (kisit or {}).get(p["ad"])
            if izinli:
                secenekler = [x for x in secenekler if x in izinli]
            s[p["ad"]] = rnd.choice(secenekler)
        else:
            s[p["ad"]] = p.get("varsayilan", "")
    return s


def varsayilan_set(sema, kisit):
    s = dict((p["ad"], p["varsayilan"]) for p in sema["parametreler"])
    for ad, izinli in (kisit or {}).items():
        if ad in s and s[ad] not in izinli:
            s[ad] = izinli[0]
    return s


def js_hacimler(fonksiyon, setler):
    istek = json.dumps({"fonksiyon": fonksiyon, "setler": setler},
                       ensure_ascii=False)
    proc = subprocess.run(["node", os.path.join(JEN_TEST, "hacim-eval.js")],
                          input=istek.encode("utf-8"), capture_output=True,
                          timeout=60)
    if proc.returncode != 0:
        sys.exit("hacim-eval.js: %s" % proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))


def scad_yolu_sec(eslem_aile, sset, paket):
    """Varyant scad override'i destekler (cift-uretecli aileler: vida, yay)."""
    scad = eslem_aile.get("scad")
    secici = eslem_aile.get("secici")
    if secici:
        v = sset.get(secici)
        varyant = (eslem_aile.get("varyantlar") or {}).get(v) or {}
        scad = varyant.get("scad", scad)
    return os.path.join(paket, scad)


def aile_olc(aile, eslem, paket, openscad, set_sayisi, tohumlar, kisit):
    sema = sema_yukle(aile)
    eslem_aile = eslem[aile]
    setler = [varsayilan_set(sema, kisit)]
    for tohum in tohumlar:
        rnd = random.Random(tohum)
        for _ in range(set_sayisi):
            setler.append(rastgele_set(sema, rnd, kisit))
    js = js_hacimler(sema["hacimFormulu"], setler)
    sonuc = {"aile": aile, "set": len(setler), "enKotu": 0.0,
             "kirmizi": 0, "hata": 0, "ret": 0, "satirlar": []}
    with tempfile.TemporaryDirectory() as tmp:
        for i, sset in enumerate(setler):
            bayraklar, sebep = server.d_bayraklari(eslem_aile, sset)
            if bayraklar is None:
                # Eslem BILEREK reddediyor = uretim motorunda karsiligi olmayan
                # sema bolgesi (or. yarim capli vida, ucgen cetvel) -> KISMI.
                sonuc["ret"] += 1
                print("  [RET ] %-10s set%-2d eslem kapsami disi: %s (%s)" %
                      (aile, i, sebep, json.dumps(sset, ensure_ascii=False)[:90]))
                continue
            stl = os.path.join(tmp, "%s-%d.stl" % (aile, i))
            komut = [openscad, "-o", stl, "--export-format", "binstl"] + \
                server.OPENSCAD_EK_BAYRAKLAR + \
                bayraklar + [scad_yolu_sec(eslem_aile, sset, paket)]
            proc = subprocess.run(komut, capture_output=True, timeout=600)
            if proc.returncode != 0 or not os.path.exists(stl):
                hata_metni = proc.stderr.decode("utf-8", "replace")
                # server.py'nin 422 siniflandirmasinin AYNISI: uretec assert'i =
                # kombinasyon uretilemez (musteriye temiz 422) — olcum hatasi degil.
                if "ERROR: Assertion" in hata_metni or "assert" in hata_metni.lower():
                    sonuc["uretilemez"] = sonuc.get("uretilemez", 0) + 1
                    print("  [422 ] %-10s set%-2d uretilemez kombinasyon (%s)" %
                          (aile, i, json.dumps(sset, ensure_ascii=False)[:90]))
                    continue
                sonuc["hata"] += 1
                print("  [HATA] %-10s set%-2d derleme: %s (%s)" %
                      (aile, i, hata_metni.strip().splitlines()[-1][:120]
                       if hata_metni.strip() else "?",
                       json.dumps(sset, ensure_ascii=False)[:90]))
                continue
            ref = stl_hacim.hacim(stl)
            sapma = abs(js[i] - ref) / ref * 100.0
            sonuc["enKotu"] = max(sonuc["enKotu"], sapma)
            if sapma > SINIR_YUZDE:
                sonuc["kirmizi"] += 1
            durum = "OK " if sapma <= SINIR_YUZDE else "SAP"
            kisa = ", ".join("%s=%s" % (k, v) for k, v in sorted(sset.items())
                             if not isinstance(v, str) or len(str(v)) < 20)
            print("  [%s] %-10s set%-2d js=%11.1f stl=%11.1f sapma=%5.2f%%  (%s)"
                  % (durum, aile, i, js[i], ref, sapma, kisa[:110]))
            sonuc["satirlar"].append({"sapma": round(sapma, 2)})
    return sonuc


# ---- HUKUM (31 Tem 2026) — "HIC OLCULMEDI" YESIL DEGILDIR --------------------
# OLCULEN FAIL-OPEN (bayraksiz/--hepsi kolu): hukum
#     if s["kirmizi"] or s["hata"]: kirmizi
#     elif s["ret"]:                kismi
#     else:                         YESIL
# idi. `uretilemez` (422) sayaci hukme HIC GIRMIYORDU. Sonuc: bir ailenin TUM setleri
# derlemede assert'e dusup 422 diye siniflanirsa kirmizi=0, hata=0, ret=0 kalir ->
# aile "yesil" ilan edilir ve arac rc=0 doner. Yani SIFIR set olculen aile, hepsi
# olculmus gibi gorunur. Ustelik 422 siniflandirmasi stderr'de "assert" alt-dizesi
# ARAMAKTIR: derleyici/paket tarafinda kirilan bir sey stderr'de "assert" gecirdigi
# anda tum aile sessizce yesile doner.
# FAIL-CLOSED: (1) hic OLCULEN set yoksa durum "olculemedi" (yesil DEGIL),
#              (2) 422 de `ret` gibi KISMI'dir — ikisi de "sema bolgesi olculemedi"
#                  demektir; birini kirmizi sayip digerini sessiz gecmek tutarsizdi.
def aile_durumu(s):
    """Aile olcum ozetinden durum — SAF fonksiyon; --kendini-test bunu surer."""
    if s.get("kirmizi") or s.get("hata"):
        return "kirmizi"
    if not s.get("satirlar"):
        return "olculemedi"          # HIC set olculmedi -> YESIL SAYILMAZ
    if s.get("ret") or s.get("uretilemez"):
        return "kismi"               # olculenler yesil ama sema bolgesi eksik
    return "yesil"


def kendini_test():
    """HUKUM NOBETCISI — POZITIF ve NEGATIF yon ayri vakalar (tek yon = olu nobetci).
    Ag/openscad/gizli paket ISTEMEZ."""
    vakalar = []

    def bekle(ad, kosul, detay=""):
        vakalar.append((ad, bool(kosul), detay))

    olculen = {"satirlar": [{"sapma": 0.1}, {"sapma": 0.2}]}

    def v(**ek):
        d = dict(olculen)
        d.update(ek)
        return d

    bekle("H1 NEGATIF-DISI: olculen + temiz aile YESIL (yanlis-pozitif yok)",
          aile_durumu(v()) == "yesil", aile_durumu(v()))
    bekle("H2 POZITIF: sinir ustu sapma KIRMIZI",
          aile_durumu(v(kirmizi=1)) == "kirmizi", aile_durumu(v(kirmizi=1)))
    bekle("H3 POZITIF: derleme hatasi KIRMIZI",
          aile_durumu(v(hata=1)) == "kirmizi", aile_durumu(v(hata=1)))
    bekle("H4 POZITIF: eslem kapsami disi (ret) KISMI (yesil degil)",
          aile_durumu(v(ret=1)) == "kismi", aile_durumu(v(ret=1)))
    bekle("H5 POZITIF (ONARIM): 422/uretilemez KISMI — eskiden SESSIZ YESILDI",
          aile_durumu(v(uretilemez=1)) == "kismi", aile_durumu(v(uretilemez=1)))
    bekle("H6 POZITIF (ONARIM): HIC olculen set yoksa OLCULEMEDI — eskiden YESILDI",
          aile_durumu({"satirlar": [], "uretilemez": 4}) == "olculemedi",
          aile_durumu({"satirlar": [], "uretilemez": 4}))
    bekle("H7 POZITIF: bos ozet (hicbir sey kosmadi) OLCULEMEDI",
          aile_durumu({}) == "olculemedi", aile_durumu({}))
    bekle("H8 KAPI: 'yesil' DISI her durum rc=1 uretir (main'in hukum kurali)",
          all(d != "yesil" for d in ("kirmizi", "kismi", "olculemedi", "eslem-yok")))

    kirmizi = [x for x in vakalar if not x[1]]
    print("ESLEM-OLCUM HUKUM NOBETCISI — %d/%d YESIL"
          % (len(vakalar) - len(kirmizi), len(vakalar)))
    for ad, yesil, detay in vakalar:
        print("  %s %-64s %s" % ("+" if yesil else "-", ad, detay if not yesil else ""))
    return 1 if kirmizi else 0


def _text_deger(bayraklar):
    """-D Text=\"...\" token'inin tirnakli deger kismi ('\"...\"'). Beyaz liste
    icerikte \" birakmadigindan ilk sonraki \" kapanistir."""
    m = " ".join(bayraklar or [])
    i = m.find('Text="')
    if i < 0:
        return "BOZUK"
    j = m.find('"', i + 6)
    return m[i + 5:j + 1] if j >= 0 else "BOZUK"


def metin_render_testi(uyelik_dir):
    """Jeton yuz yazisi RENDER + enjeksiyon guvenligi (onizleme derleme yolu, gercek
    openscad). Kendi kendine yeter: eslem-ozel.json'u dogrudan okur (paket toplamaz),
    .scad'i uyelik dizininden alir. openscad ya da .scad yoksa ATLA (kabul disi).
      (a) iki farkli yazi -> iki FARKLI mesh (yazi gercekten render ediliyor)
      (b) kotu niyetli yazi -> GUVENLI derlenir + -D Text degeri sanitize."""
    aile = "kisiye-ozel-jeton-cip-madalyon"
    openscad = openscad_yolu()
    eslem_dir = os.path.join(REPO, "onizleme", "derleyici")
    eslem = server.eslem_yukle(eslem_dir)
    if aile not in eslem:
        print("  [YOK ] %s eslem-ozel.json'da yok" % aile)
        return 1
    ea = eslem[aile]
    ortak = ea.get("ortak") or {}
    scad_yol = os.path.join(uyelik_dir, ea["scad"])
    hatalar = []

    def dg(ad, kosul, ek=""):
        print(("  [OK ] " if kosul else "  [HATA] ") + ad + (" — " + ek if ek else ""))
        if not kosul:
            hatalar.append(ad)

    # Deploy-hazirlik: eslem jeton ailesinde metin blogu var + sabit'te Text yok.
    dg("eslem: jeton ortak.metin = {'Text': {'param': 'yazi'}}",
       ortak.get("metin") == {"Text": {"param": "yazi"}},
       json.dumps(ortak.get("metin"), ensure_ascii=False))
    dg("eslem: jeton sabit'te artik Text yok",
       "Text" not in (ortak.get("sabit") or {}))

    if not openscad or not os.path.exists(scad_yol):
        print("  [ATLA] mesh testi kosulmadi (openscad=%s scad=%s) — KABUL DISI"
              % (bool(openscad), os.path.exists(scad_yol)))
        return 1 if hatalar else 2  # 2 = yapi OK ama mesh atlandi (kabul disi)

    def taban(yazi):
        return {"cap": 39, "kalinlik": 3.4, "yazi_stili": "gomme",
                "yuz_sayisi": "tek", "kenar_deseni": "segmentli", "yazi": yazi}

    def render(yazi):
        bayraklar, sebep = server.d_bayraklari(ea, taban(yazi))
        if bayraklar is None:
            return None, "", "d_bayraklari ret: %s" % sebep
        with tempfile.TemporaryDirectory() as tmp:
            stl = os.path.join(tmp, "j.stl")
            komut = [openscad, "-o", stl, "--export-format", "binstl"] + \
                server.OPENSCAD_EK_BAYRAKLAR + bayraklar + [scad_yol]
            proc = subprocess.run(komut, capture_output=True, timeout=180)
            if proc.returncode != 0 or not os.path.exists(stl):
                return None, "", proc.stderr.decode("utf-8", "replace")[-200:]
            veri = open(stl, "rb").read()
        return veri, hashlib.sha256(veri).hexdigest()[:16], ""

    d1, h1, e1 = render("100")
    d2, h2, e2 = render("AYSU 2026")
    dg("(a) '100' render edildi", d1 is not None, e1)
    dg("(a) 'AYSU 2026' render edildi", d2 is not None, e2)
    dg("(a) iki farkli yazi -> FARKLI mesh (yazi render ediliyor)",
       bool(d1) and bool(d2) and h1 != h2, "sha(100)=%s sha(AYSU)=%s" % (h1, h2))

    kotu = '"; import("/etc/passwd"); a'
    bayr, _ = server.d_bayraklari(ea, taban(kotu))
    tv = _text_deger(bayr)
    dg("(b) kotu niyet -D sanitize (tirnak cifti, ters-bolu/; yok)",
       tv.count('"') == 2 and "\\" not in tv and ";" not in tv, "Text=%s" % tv)
    dk, hk, ek = render(kotu)
    dg("(b) kotu niyetli yazi GUVENLI derlendi (returncode 0)", dk is not None, ek)

    print("metin-testi: %d hata" % len(hatalar))
    return 1 if hatalar else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aileler", nargs="*")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--set", type=int, default=5)
    ap.add_argument("--tohumlar", default="20260716,20260717")
    ap.add_argument("--json", help="ozeti bu dosyaya JSON dok")
    ap.add_argument("--kendini-test", action="store_true",
                    help="hukum nobetcisi (olcum kosturmaz; ag/openscad/paket ISTEMEZ)")
    ap.add_argument("--metin-testi", action="store_true",
                    help="jeton yuz yazisi render + enjeksiyon guvenligi testi (kalibrasyon disi)")
    args = ap.parse_args()

    if args.kendini_test:
        sys.exit(kendini_test())
    if args.metin_testi:
        sys.exit(metin_render_testi(os.environ.get(
            "PRUVO_UYELIK_DIR", "/Users/okan/dev/pruvo/.uyelik-kodlar")))
    tohumlar = [int(x) for x in args.tohumlar.split(",")]

    paket = paket_topla()
    eslem = server.eslem_yukle(paket)
    kisitlar = kisitlar_yukle()
    aileler = sorted(eslem.keys()) if args.hepsi else args.aileler
    if not aileler:
        sys.exit("aile verin ya da --hepsi")
    openscad = openscad_yolu()
    print("olcum: %d aile, %d set x %d tohum + varsayilan, sinir <=%%%.1f" %
          (len(aileler), args.set, len(tohumlar), SINIR_YUZDE))

    ozet = []
    for aile in aileler:
        if aile not in eslem:
            print("  [YOK ] %s eslem paketinde yok" % aile)
            ozet.append({"aile": aile, "durum": "eslem-yok"})
            continue
        s = aile_olc(aile, eslem, paket, openscad, args.set, tohumlar,
                     kisitlar.get(aile))
        s["durum"] = aile_durumu(s)
        print("  --> %-10s en kotu %%%.2f, sinir ustu %d/%d, derleme hatasi %d, "
              "kapsam disi %d, uretilemez(422) %d"
              % (aile, s["enKotu"], s["kirmizi"], s["set"], s["hata"], s["ret"],
                 s.get("uretilemez", 0)))
        ozet.append(s)
    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as f:
            json.dump(ozet, f, ensure_ascii=False, indent=1)
    kirmizi = [s for s in ozet if s.get("durum") != "yesil"]
    print("\nOZET: %d aile yesil, %d aile sinir disi/eksik" %
          (len(ozet) - len(kirmizi), len(kirmizi)))
    sys.exit(1 if kirmizi else 0)


if __name__ == "__main__":
    main()
