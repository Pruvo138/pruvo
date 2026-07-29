#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PAKET TAZELIK KAPISI — R2'deki derleme paketi MAIN'deki eslemi TASIYOR MU.

OLCULEN DELIK (29 Tem 2026): "main yesil / canli bozuk".
  Musteri metnini derleyiciye tasiyan eslem onarimi main'e girdi (4addb58d) ve
  tools/metin-eslem-test.py TAM kapsamda YESIL yandi. AMA imaj, eslemi main'den
  DEGIL R2'deki gizli paketten (pruvo-ozel/onizleme/paket-guncel.tar.gz) alir.
  O paket v5'te DONMUSTU: `olcuye-ozel-cerceve` metin_eslem=0, `olcuye-ozel-damga-kase`
  metin_eslem=0 + `sabit` icinde Text="PRUVO...". Yani CI o gun tetiklense AYNI BOZUK
  imaj yeniden derlenirdi ve 350 TL'lik kase herkese sabit "PRUVO" basmaya devam ederdi.
  HICBIR nobetci "paket main'i tasiyor mu" diye SORMUYORDU:
    * tools/metin-eslem-test.py ACIK aileleri (cerceve dahil) esleminden DEGIL, HER
      KOSUMDA main kaynagindan YENIDEN URETIR -> paket bayat olsa da YESIL yanar.
    * deploy.yml kosumunda gizli eslem yoktur -> kase/jeton ⚪ OLCULEMEDI sayilir.
  Bu kapi tam o soruyu sorar ve KIRMIZI yanar.

KIPLER
  --paket <dizin>   PAKETI OLC (bloklayici). Gercek cagri satiri:
                    .github/workflows/onizleme-imaj.yml, paket cekildikten hemen
                    SONRA / imaj derlenmeden ONCE.
  --r2 [--anahtar K] R2'den paketi CEKIP olc (yerel/elle; ag + wrangler oturumu ister).
  (bayraksiz)       OFFLINE kip — deploy.yml adimi: oz-nobetciler + "gercek cagri
                    satiri duruyor mu" nobeti. Gizli paket YOKTUR, paket ekseni
                    ⚪ OLCULEMEDI diye ILAN EDILIR (sessiz yesil degil).

KAPSAM DISIPLINI (bilincli): bloklayici PAKET olcumu YALNIZ onizleme-imaj.yml'de kosar
  -> bayat paket TUM SITE yayinini durdurmaz (urun ekleme/CSS gibi rutin degisiklikler
  bu kapiyi goremez bile). deploy.yml'de kosan OFFLINE kip yalnizca iki seye bakar:
  kendi sentetik fiksturlerine ve onizleme-imaj.yml METNINE. Baska hicbir depo dosyasi
  okunmaz -> alakasiz duzenlemede yanlis-pozitif URETEMEZ ([[kapi-kapsam-eksen-secimi]]).

IDDIALAR (paket kipi)
  K1 ACIK PARITE: ACIK_AILELER'in (bizim ureteclerimiz) paketteki eslem blogu, main'in
     PUBLIC kaynaklarindan (jenerator/test/esleme + jenerator/urunler) URETILEN blokla
     BIREBIR ayni mi. Bayat paket burada yakalanir. Kopya mantik YOK: beklenen blok
     tools/onizleme-paket-yukle.py'nin KENDI acik_eslem_uret'iyle uretilir.
  K2 METIN INVARYANTI (gizli aileler dahil): semasinda `tip:"metin"` parametresi olan
     ve PAKETTE bulunan her aile icin paket eslemi bos-olmayan `ortak.metin` tasimali ve
     ayni scad degiskeni `sabit`te OLMAMALI (sabit en son uygulanir, musteri metnini EZER).
     Gizli-eslem ailesi (kase) main'den turetilemez; bu invaryant onu da kapsar.

NE KANITLAMAZ: metnin STL'e DOGRU basildigini (o, onizleme-imaj.yml "metin farklilasma"
  dumaninin isi — gercek openscad), paketteki .scad govdelerinin tazeligini (yalniz eslem
  karsilastirilir), imajin deploy edildigini.

KIRMIZI-MUTASYON: python3 tools/paket-tazelik-kapisi.py --kendini-test
Kullanim:
  python3 tools/paket-tazelik-kapisi.py
  python3 tools/paket-tazelik-kapisi.py --paket onizleme/derleyici/paket-ozel
  python3 tools/paket-tazelik-kapisi.py --r2
"""
import argparse
import glob
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SEMA_DIZIN = os.path.join(ROOT, "jenerator", "urunler")
IMAJ_YML = os.path.join(ROOT, ".github", "workflows", "onizleme-imaj.yml")
BUCKET = "pruvo-ozel"
R2_ANAHTAR = "onizleme/paket-guncel.tar.gz"

# GERCEK CAGRI SATIRI CAPASI — bu metin onizleme-imaj.yml'de GECMEZSE kapi olmustur.
# Duz alt-dize aramasi (jetonlama/YAML ayristirmasi YOK): bu depoda "akilli" capa
# denemeleri mesru yazimlari sahte-kirmizi yakti ([[mimar-kapi-parser-taklidi]]).
# KABUL EDILEN BEDEL: yorum icindeki bir mensiyon da "duruyor" sayilir — kapi disiplin
# cihazidir, hapishane degil ([[kapi-disiplin-ilkesi]]).
CAGRI_CAPASI = "tools/paket-tazelik-kapisi.py --paket"


def _modul(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PAKET = _modul("pruvo_onizleme_paket", os.path.join(TOOLS, "onizleme-paket-yukle.py"))


# ---------------------------------------------------------------- olcum cekirdegi

def beklenen_acik():
    """{aile: eslem_blogu} — MAIN'in public kaynaklarindan uretilen ACIK aile eslemleri."""
    beklenen = {}
    for aile, ad in sorted(PAKET.ACIK_AILELER.items()):
        urun_id, blok, _scad = PAKET.acik_eslem_uret(ad)
        if urun_id != aile:
            sys.exit("ACIK_AILELER tutarsiz: %s != %s" % (urun_id, aile))
        beklenen[aile] = blok
    return beklenen


def metin_semalari():
    """{aile: [metin parametre adlari]} — jenerator/urunler DIZIN TARAMASI (elle liste YOK)."""
    bulunan = {}
    for yol in sorted(glob.glob(os.path.join(SEMA_DIZIN, "*.json"))):
        with open(yol, encoding="utf-8") as f:
            sema = json.load(f)
        metinler = [p["ad"] for p in sema.get("parametreler", [])
                    if p.get("tip") == "metin"]
        if metinler:
            bulunan[sema["id"]] = metinler
    return bulunan


def _fark_ozeti(beklenen, gelen):
    """Iki eslem blogunun HANGI alanlarda ayristigini kisa metin olarak dondurur
    (icerik degeri BASILMAZ: paket sirdir — yalniz alan adlari + sayilar)."""
    farklar = []
    for anahtar in sorted(set(beklenen) | set(gelen)):
        b, g = beklenen.get(anahtar), gelen.get(anahtar)
        if b == g:
            continue
        if anahtar == "ortak" and isinstance(b, dict) and isinstance(g, dict):
            for alt in sorted(set(b) | set(g)):
                if b.get(alt) != g.get(alt):
                    farklar.append("ortak.%s (beklenen %d anahtar, pakette %d)"
                                   % (alt, len(b.get(alt) or {}), len(g.get(alt) or {})))
        else:
            farklar.append(anahtar)
    return ", ".join(farklar) or "(fark alan bazinda cozulemedi)"


def paket_denetle(paket_aileler, beklenen, metin_adlari, yaz=None):
    """(sorunlar, ozet) — SAF fonksiyon (dosya/ag OKUMAZ), oz-nobetciler bunu surer."""
    yaz = yaz or (lambda s: None)
    sorunlar = []
    ozet = {"k1_gecen": 0, "k1_kalan": 0, "k1_eksik": 0,
            "k2_gecen": 0, "k2_kalan": 0, "k2_olculemedi": 0}

    for aile in sorted(beklenen):
        gelen = paket_aileler.get(aile)
        if gelen is None:
            ozet["k1_eksik"] += 1
            sorunlar.append("K1 AILE PAKETTE YOK: %s -> paket main'in ureteclerini "
                            "tasimiyor (imaj o aileyi 404 aile-yok ile reddeder)" % aile)
            yaz("  ❌ %s — pakette YOK" % aile)
        elif gelen == beklenen[aile]:
            ozet["k1_gecen"] += 1
            yaz("  ✅ %s — paket eslemi main ile AYNI" % aile)
        else:
            ozet["k1_kalan"] += 1
            sorunlar.append("K1 BAYAT PAKET: %s eslemi main'den SAPIYOR (%s) -> paketi "
                            "tazeleyin: python3 tools/onizleme-paket-yukle.py"
                            % (aile, _fark_ozeti(beklenen[aile], gelen)))
            yaz("  ❌ %s — SAPMA: %s" % (aile, _fark_ozeti(beklenen[aile], gelen)))

    for aile in sorted(metin_adlari):
        gelen = paket_aileler.get(aile)
        if gelen is None:
            ozet["k2_olculemedi"] += 1
            yaz("  ⚪ %s — metin semasi var ama pakette aile YOK (olculemedi)" % aile)
            continue
        ortak = gelen.get("ortak") or {}
        metin = ortak.get("metin") or {}
        sabit = ortak.get("sabit") or {}
        cakisan = sorted(set(metin) & set(sabit))
        if not metin:
            ozet["k2_kalan"] += 1
            sorunlar.append("K2 METIN DUSUYOR: %s paket eslemi `metin` blogu TASIMIYOR -> "
                            "musteri ne yazarsa yazsin AYNI govde uretilir (%s)"
                            % (aile, ", ".join(metin_adlari[aile])))
            yaz("  ❌ %s — paket esleminde `metin` blogu YOK" % aile)
        elif cakisan:
            ozet["k2_kalan"] += 1
            sorunlar.append("K2 SABIT EZIYOR: %s -> %s hem `metin`de hem `sabit`te; `sabit` "
                            "en son uygulanir ve musteri metnini SESSIZCE ezer"
                            % (aile, ", ".join(cakisan)))
            yaz("  ❌ %s — `sabit` musteri metnini eziyor: %s" % (aile, ", ".join(cakisan)))
        else:
            ozet["k2_gecen"] += 1
            yaz("  ✅ %s — paket eslemi musteri metnini tasiyor (%s)"
                % (aile, ", ".join(sorted(metin))))
    return sorunlar, ozet


# ---------------------------------------------------------------- paket kaynaklari

def eslem_oku(paket_dizin):
    yol = os.path.join(paket_dizin, "eslem-ozel.json")
    if not os.path.exists(yol):
        sys.exit("paket esleminde eslem-ozel.json YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    return veri.get("aileler") or {}, veri.get("surum")


def r2_cek(hedef_dizin, anahtar):
    """R2'den paketi ceker (yerel wrangler oturumu; token gerekmez)."""
    arsiv = os.path.join(hedef_dizin, "paket.tar.gz")
    komut = ["npx", "wrangler", "r2", "object", "get",
             BUCKET + "/" + anahtar, "--file", arsiv, "--remote"]
    proc = subprocess.run(komut, cwd=ROOT, capture_output=True)
    if proc.returncode != 0 or not os.path.exists(arsiv):
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        sys.exit("R2'den cekilemedi: r2://%s/%s (wrangler oturumu acik mi?)"
                 % (BUCKET, anahtar))
    ac = os.path.join(hedef_dizin, "paket")
    os.makedirs(ac, exist_ok=True)
    with tarfile.open(arsiv, "r:gz") as tar:
        tar.extractall(ac)
    return ac


# ---------------------------------------------------------------- oz-nobetciler

_SEMA_METIN = {"zzz-sentetik": ["yazi"]}
_BEKLENEN = {"zzz-sentetik": {
    "scad": "x.scad", "secici": None, "varyantlar": None,
    "ortak": {"sayisal": {"B": {"terimler": {"boy": 1}}},
              "metin": {"Yazi": {"param": "yazi"}}, "sabit": {}}}}


def oz_nobetci():
    """GOVDE-INERTLIK NOBETCISI — paket_denetle GERCEKTEN olcuyor mu (5 fikstur).
    Hem YAKALAMA hem YANLIS-POZITIF yonu olculur; govde tek yone sabitlenirse yanar."""
    hata = []

    # (1) TEMIZ paket -> sorun YOK (yanlis-pozitif yonu)
    s, _ = paket_denetle(dict(_BEKLENEN), _BEKLENEN, _SEMA_METIN)
    if s:
        hata.append("(1) TEMIZ paket sorunlu sayildi (yanlis-pozitif): %s" % s)

    # (2) BAYAT paket: metin blogu dusmus (cerceve v5 hali) -> K1 + K2 yanmali
    bayat = json.loads(json.dumps(_BEKLENEN))
    del bayat["zzz-sentetik"]["ortak"]["metin"]
    s, _ = paket_denetle(bayat, _BEKLENEN, _SEMA_METIN)
    if not any(x.startswith("K1") for x in s):
        hata.append("(2) BAYAT paket K1'i tetiklemedi -> parite olcumu inert")
    if not any(x.startswith("K2") for x in s):
        hata.append("(2) BAYAT paket K2'yi tetiklemedi -> metin invaryanti inert")

    # (3) Metin `sabit`e kacmis (kase v5 hali: Text="PRUVO") -> K2 yanmali
    ezen = json.loads(json.dumps(_BEKLENEN))
    ezen["zzz-sentetik"]["ortak"]["sabit"] = {"Yazi": "PRUVO"}
    s, _ = paket_denetle(ezen, _BEKLENEN, _SEMA_METIN)
    if not any("K2 SABIT EZIYOR" in x for x in s):
        hata.append("(3) `sabit` ezmesi yakalanmadi -> K2 sira/ezme halini olcmuyor")

    # (4) Aile pakette HIC yok -> K1 yanmali
    s, _ = paket_denetle({}, _BEKLENEN, _SEMA_METIN)
    if not any("K1 AILE PAKETTE YOK" in x for x in s):
        hata.append("(4) eksik aile yakalanmadi")

    # (5) Metin semasi olan aile pakette yoksa SESSIZ gecmemeli (⚪ sayilmali)
    _s, ozet = paket_denetle({}, {}, _SEMA_METIN)
    if ozet["k2_olculemedi"] != 1:
        hata.append("(5) pakette olmayan metin ailesi ⚪ OLCULEMEDI diye sayilmadi "
                    "(sayac=%d)" % ozet["k2_olculemedi"])
    return (not hata), hata


def cagri_satiri_nobeti(yml_metin=None):
    """GERCEK CAGRI SATIRI NOBETI (mutasyon (b)): bloklayici olcum onizleme-imaj.yml'de
    kosuyor mu. Bu kapi deploy.yml'de kosar, cagri satiri BASKA dosyadadir -> satir
    silinirse kapi sessizce olurdu. ci-kapsam-test.py YALNIZ deploy.yml'e bakar,
    yani bu deligi baska hicbir nobetci kapamaz."""
    if yml_metin is None:
        if not os.path.exists(IMAJ_YML):
            return False, ["onizleme-imaj.yml bulunamadi: %s" % IMAJ_YML]
        with open(IMAJ_YML, encoding="utf-8") as f:
            yml_metin = f.read()
    if CAGRI_CAPASI not in yml_metin:
        return False, ["CAGRI SATIRI YOK: onizleme-imaj.yml'de %r gecmiyor -> bloklayici "
                       "paket olcumu HICBIR yerde kosmuyor (kapi olu). GERI KOY: paket "
                       "cekildikten SONRA / imaj derlenmeden ONCE bir adim." % CAGRI_CAPASI]
    return True, []


def cagri_nobeti_kendini_test():
    """Cagri nobetinin KENDISI inert mi: capasiz metinde KIRMIZI, capali metinde YESIL."""
    hata = []
    ok, _ = cagri_satiri_nobeti("steps:\n  - run: docker build .\n")
    if ok:
        hata.append("cagri nobeti INERT: capasiz YAML'da bile YESIL dedi")
    ok, tani = cagri_satiri_nobeti("  - run: python3 %s onizleme/derleyici/paket-ozel\n"
                                   % CAGRI_CAPASI)
    if not ok:
        hata.append("cagri nobeti YANLIS-POZITIF: capali YAML'da KIRMIZI dedi (%s)" % tani)
    return (not hata), hata


# ---------------------------------------------------------------- giris

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paket", metavar="DIZIN", help="olculecek paket dizini (bloklayici)")
    ap.add_argument("--r2", action="store_true", help="paketi R2'den cekip olc (ag gerekir)")
    ap.add_argument("--anahtar", default=R2_ANAHTAR, help="R2 nesne anahtari (--r2 ile)")
    ap.add_argument("--kendini-test", action="store_true", help="yalniz oz-nobetciler")
    args = ap.parse_args()

    ok1, h1 = oz_nobetci()
    ok2, h2 = cagri_nobeti_kendini_test()
    print("OZ-NOBETCI: %s" % ("YESIL" if (ok1 and ok2) else "KIRMIZI"))
    for h in h1 + h2:
        print("  ❌ %s" % h)
    if args.kendini_test:
        sys.exit(0 if (ok1 and ok2) else 1)

    ok3, h3 = cagri_satiri_nobeti()
    print("CAGRI SATIRI (onizleme-imaj.yml): %s" % ("VAR" if ok3 else "YOK"))
    for h in h3:
        print("  ❌ %s" % h)

    sorunlar = []
    if args.paket or args.r2:
        gecici = None
        try:
            if args.r2:
                gecici = tempfile.mkdtemp(prefix="paket-tazelik-")
                dizin = r2_cek(gecici, args.anahtar)
                print("PAKET KAYNAGI: r2://%s/%s" % (BUCKET, args.anahtar))
            else:
                dizin = args.paket
                print("PAKET KAYNAGI: %s" % dizin)
            paket_aileler, surum = eslem_oku(dizin)
            print("PAKET SURUMU : v%s   (aile: %d)" % (surum, len(paket_aileler)))
            sorunlar, ozet = paket_denetle(paket_aileler, beklenen_acik(),
                                           metin_semalari(), yaz=print)
            print("K1 acik parite: %d gecti, %d saptı, %d aile eksik | "
                  "K2 metin: %d gecti, %d kaldi, %d olculemedi"
                  % (ozet["k1_gecen"], ozet["k1_kalan"], ozet["k1_eksik"],
                     ozet["k2_gecen"], ozet["k2_kalan"], ozet["k2_olculemedi"]))
        finally:
            if gecici:
                subprocess.run(["rm", "-rf", gecici])
    else:
        print("PAKET EKSENI : ⚪ OLCULEMEDI — gizli paket verilmedi (bu kip OFFLINE). "
              "TAM olcum: --paket <dizin> (onizleme-imaj.yml) ya da --r2 (yerel).")

    for s in sorunlar:
        print("  ❌ %s" % s)
    kirmizi = bool(sorunlar) or not (ok1 and ok2 and ok3)
    print("SONUC: %s" % ("KIRMIZI" if kirmizi else "YESIL"))
    sys.exit(1 if kirmizi else 0)


if __name__ == "__main__":
    main()
