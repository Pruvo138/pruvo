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
import re
import subprocess
import sys
import tarfile
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SEMA_DIZIN = os.path.join(ROOT, "jenerator", "urunler")
IMAJ_YML = os.path.join(ROOT, ".github", "workflows", "onizleme-imaj.yml")
BUCKET = "pruvo-ozel"

# GERCEK CAGRI SATIRI CAPASI — bu metin onizleme-imaj.yml'de GECMEZSE kapi olmustur.
# Duz alt-dize aramasi (jetonlama/YAML ayristirmasi YOK): bu depoda "akilli" capa
# denemeleri mesru yazimlari sahte-kirmizi yakti ([[mimar-kapi-parser-taklidi]]).
# KABUL EDILEN BEDEL: yorum icindeki bir mensiyon da "duruyor" sayilir — kapi disiplin
# cihazidir, hapishane degil ([[kapi-disiplin-ilkesi]]).
CAGRI_CAPASI = "tools/paket-tazelik-kapisi.py --paket"

# SURUMLU ANAHTAR NOBETI capalari (Okan/mimar karari 29 Tem 2026).
# Sabit "guncel" takma adina yazma TERK EDILDI: R2'de VAR OLAN anahtarin uzerine yazma
# "Upload complete." + RC=0 basip nesneyi DEGISTIRMIYOR (4 deneme, sha256 birebir ayni).
# Takma ad geri gelirse CI onarilmis main'e ragmen BAYAT eslemle imaj derler (sessiz hata).
# (a) is akisi ekseni — METIN capasi (YAML'da davranis calistirilamaz). Capa DAR secildi:
#     yasak olan sey "s3 nesne yolunun SABIT yazilmasi"; yorum icinde gecen anahtar ADI
#     tetiklemez ([[mimar-kapi-parser-taklidi]]: parser taklidi yapma, dar alt-dize kullan).
SABIT_NESNE_YOLU = "s3://" + BUCKET + "/onizleme/"
GIRDI_CAPASI = "PAKET_ANAHTAR"
# (b) yukleyici ekseni — METIN DEGIL DAVRANIS: yuklenecek_anahtarlar() dogrudan cagrilir.
SURUM_ORNEKLERI = (6, 7, 41)


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


def yml_varsayilan_anahtar(yml_metin=None):
    """onizleme-imaj.yml'deki paket_anahtar girdisinin VARSAYILANI (fail-closed: yoksa None).
    `--r2` kipi bunu kullanir -> yerel elle olcum CI'nin GERCEKTEN cektigi anahtari olcer."""
    if yml_metin is None:
        if not os.path.exists(IMAJ_YML):
            return None
        with open(IMAJ_YML, encoding="utf-8") as f:
            yml_metin = f.read()
    blok = re.search(r"\n\s*paket_anahtar:\s*\n((?:\s+\S.*\n|\s*\n)+?)(?=\s*\w+:\s*\n)",
                     yml_metin)
    if not blok:
        return None
    m = re.search(r'^\s*default:\s*"?([^"\n]+?)"?\s*$', blok.group(1), re.M)
    return m.group(1) if m else None


def surumlu_anahtar_nobeti(yml_metin=None, anahtar_uretici=None):
    """SURUMLU ANAHTAR NOBETI — "uzerine yazma" deseni geri sizdi mi (iki eksen).

    (a) IS AKISI: onizleme-imaj.yml paketi SABIT bir s3 nesne yolundan cekmemeli;
        anahtar workflow_dispatch girdisinden gelmeli (PAKET_ANAHTAR).
    (b) YUKLEYICI: tools/onizleme-paket-yukle.py YALNIZ surumlu anahtara yazmali.
        Bu eksen METIN ARAMAZ — yuklenecek_anahtarlar() FIILEN cagrilir (fault-injection
        ile test edilebilir, yorum/dizim degisikliginden etkilenmez)."""
    hata = []
    if yml_metin is None:
        if not os.path.exists(IMAJ_YML):
            return False, ["onizleme-imaj.yml bulunamadi: %s" % IMAJ_YML]
        with open(IMAJ_YML, encoding="utf-8") as f:
            yml_metin = f.read()
    if SABIT_NESNE_YOLU in yml_metin:
        hata.append("SABIT NESNE YOLU GERI GELDI: onizleme-imaj.yml icinde %r geciyor -> "
                    "CI surumlu girdi yerine sabit anahtardan cekiyor; o anahtarin uzerine "
                    "yazma SESSIZCE basarisiz oldugu icin BAYAT paketle imaj derlenir. "
                    "Anahtari inputs.paket_anahtar'dan alin." % SABIT_NESNE_YOLU)
    if GIRDI_CAPASI not in yml_metin:
        hata.append("GIRDI CAPASI YOK: onizleme-imaj.yml'de %r gecmiyor -> paket anahtari "
                    "workflow_dispatch girdisinden GELMIYOR (fail-closed kontrol de yok)."
                    % GIRDI_CAPASI)
    uretici = anahtar_uretici or PAKET.yuklenecek_anahtarlar
    for surum in SURUM_ORNEKLERI:
        gelen = list(uretici(surum))
        beklenen = ["onizleme/paket-v%d.tar.gz" % surum]
        if gelen != beklenen:
            fazla = [a for a in gelen if a not in beklenen]
            hata.append("YUKLEYICI SURUMSUZ ANAHTARA YAZIYOR (v%d): beklenen %s, uretilen %s"
                        "%s -> var olan anahtarin uzerine yazma bu bucket'ta sessizce "
                        "basarisiz; CI bayat paket ceker."
                        % (surum, beklenen, gelen,
                           (" [fazladan: %s]" % fazla) if fazla else ""))
            break
    return (not hata), hata


def surumlu_anahtar_kendini_test():
    """Nobetcinin KENDISI inert mi — POZITIF ve NEGATIF yon ayri ayri, capadan BAGIMSIZ
    fault-injection ile (yukleyici ekseni gercek fonksiyon yerine sahte uretici alir)."""
    hata = []
    iyi_yml = ('        env:\n          PAKET_ANAHTAR: ${{ inputs.paket_anahtar }}\n'
               '        run: aws s3 cp "s3://' + BUCKET + '/$PAKET_ANAHTAR" paket.tar.gz\n')
    kotu_yml = ('        run: aws s3 cp "s3://' + BUCKET +
                '/onizleme/paket-guncel.tar.gz" paket.tar.gz\n')
    iyi_uretici = lambda s: ["onizleme/paket-v%d.tar.gz" % s]
    kotu_uretici = lambda s: ["onizleme/paket-v%d.tar.gz" % s,
                              "onizleme/paket-guncel.tar.gz"]

    ok, tani = surumlu_anahtar_nobeti(iyi_yml, iyi_uretici)
    if not ok:
        hata.append("YANLIS-POZITIF: dogru kurulumda KIRMIZI dedi (%s)" % tani)
    ok, _ = surumlu_anahtar_nobeti(kotu_yml, iyi_uretici)
    if ok:
        hata.append("INERT (is akisi ekseni): sabit s3 nesne yolundan ceken YAML'da YESIL dedi")
    ok, _ = surumlu_anahtar_nobeti(iyi_yml.replace("PAKET_ANAHTAR", "SABIT"), iyi_uretici)
    if ok:
        hata.append("INERT (girdi ekseni): PAKET_ANAHTAR gecmeyen YAML'da YESIL dedi")
    ok, _ = surumlu_anahtar_nobeti(iyi_yml, kotu_uretici)
    if ok:
        hata.append("INERT (yukleyici ekseni): sabit takma ada da yazan yukleyicide YESIL dedi")
    return (not hata), hata


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
    ap.add_argument("--anahtar", default=None,
                    help="R2 nesne anahtari (--r2 ile; varsayilan onizleme-imaj.yml'deki "
                         "paket_anahtar girdisinin varsayilani)")
    ap.add_argument("--kendini-test", action="store_true", help="yalniz oz-nobetciler")
    args = ap.parse_args()

    ok1, h1 = oz_nobetci()
    ok2, h2 = cagri_nobeti_kendini_test()
    ok4, h4 = surumlu_anahtar_kendini_test()
    print("OZ-NOBETCI: %s" % ("YESIL" if (ok1 and ok2 and ok4) else "KIRMIZI"))
    for h in h1 + h2 + h4:
        print("  ❌ %s" % h)
    if args.kendini_test:
        sys.exit(0 if (ok1 and ok2 and ok4) else 1)

    ok3, h3 = cagri_satiri_nobeti()
    print("CAGRI SATIRI (onizleme-imaj.yml): %s" % ("VAR" if ok3 else "YOK"))
    for h in h3:
        print("  ❌ %s" % h)

    ok5, h5 = surumlu_anahtar_nobeti()
    print("SURUMLU ANAHTAR (uzerine yazma terk edildi): %s"
          % ("TAMAM" if ok5 else "IHLAL"))
    for h in h5:
        print("  ❌ %s" % h)

    sorunlar = []
    if args.paket or args.r2:
        gecici = None
        try:
            if args.r2:
                anahtar = args.anahtar or yml_varsayilan_anahtar()
                if not anahtar:
                    sys.exit("R2 anahtari BELIRLENEMEDI: onizleme-imaj.yml'de paket_anahtar "
                             "varsayilani okunamadi -> --anahtar ile ACIKCA verin "
                             "(fail-closed: tahmin edilmez).")
                gecici = tempfile.mkdtemp(prefix="paket-tazelik-")
                dizin = r2_cek(gecici, anahtar)
                print("PAKET KAYNAGI: r2://%s/%s" % (BUCKET, anahtar))
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
    kirmizi = bool(sorunlar) or not (ok1 and ok2 and ok3 and ok4 and ok5)
    print("SONUC: %s" % ("KIRMIZI" if kirmizi else "YESIL"))
    sys.exit(1 if kirmizi else 0)


if __name__ == "__main__":
    main()
