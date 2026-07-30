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

OZ-NOBETCILER (her kipte, `--kendini-test` dahil BLOKLAYICI kosar)
  * oz_nobetci()                     paket_denetle govdesi inert mi (5 fikstur)
  * cagri_nobeti_kendini_test()      gercek cagri satiri nobetcisi inert mi
  * surumlu_anahtar_kendini_test()   surumlu anahtar nobetcisinin 4+3 ekseni
      (a) sabit s3 nesne yolu · (b) yukleyici surumsuz anahtara yaziyor mu
      (c) BAYAT VARSAYILAN (30 Tem): paket_anahtar girdisinde varsayilan OLMAMALI
      (d) BOS GIRDI KAPISI (30 Tem): varsayilan olmadigi icin bos girdi gelebilir,
          is akisi bos anahtarla DEVAM ETMEMELI
  * geri_okuma_nobeti()              YUKLEYICI GERI OKUMA YARISI (30 Tem): yayilma
      gecikmesinde (~18-24 s olculdu) yeniden deneniyor mu · butce dolunca SESSIZ
      FAIL-OPEN yapmiyor mu · sha karsilastirmasi hala KIRMIZI mi · bayat dosya
      "nesne var" sayilmiyor mu · butce olculen pencerenin 2 katinin altina inmemis mi

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
# (d) BOS GIRDI KAPISI capasi — is akisi bos anahtarla devam ETMEMELI. Dar alt-dize
#     (parser taklidi YOK): kabuk kosulu ve cikis. Bkz. surumlu_anahtar_nobeti (d).
BOS_GIRDI_CAPASI = '[ -z "$PAKET_ANAHTAR" ]'


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

    🔴 30 Tem 2026'DAN ITIBAREN BU DEGER `None` OLMALIDIR. Varsayilan BILEREK KALDIRILDI
    (bkz. surumlu_anahtar_nobeti (c)): bayat bir varsayilan (v6 = 2-renk parca aileleri
    OLMAYAN paket) ile tetiklenen is akisi yanlis imaji SESSIZCE derliyordu. Bu fonksiyon
    artik iki ise yarar: (1) `--r2` kipinde anahtari OTOMATIK belirlemek MUMKUN DEGIL ->
    `--anahtar` ACIKCA istenir (main icinde fail-closed sys.exit), (2) nobetci (c) ekseni
    bu fonksiyonu FIILEN cagirip "varsayilan geri gelmis mi" diye olcer (metin arama
    DEGIL, DAVRANIS)."""
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
        ile test edilebilir, yorum/dizim degisikliginden etkilenmez).
    (c) BAYAT VARSAYILAN (30 Tem 2026): paket_anahtar girdisinin VARSAYILANI OLMAMALI.
        OLCULEN TUZAK: varsayilan `onizleme/paket-v6.tar.gz` idi ve v6 paketi 2-renk
        parca ailelerini (#govde / #yazi) TASIMIYOR. Is akisi varsayilanla tetiklenirse
        parcasiz imaj derlenir ve HICBIR ADIM KIRMIZI VERMEZ (metin eslem + paket
        tazelik kapilari ACIK aile eslemini main'den yeniden uretir; duman adimi taban
        aileyi derler) -> yanlis imaj SESSIZCE yayinlanir. Bu eksen de DAVRANIS olcer:
        yml_varsayilan_anahtar() FIILEN cagrilir.
    (d) BOS GIRDI KAPISI: varsayilan kaldirildigi icin bos girdiyle tetiklenme MUMKUN;
        is akisi bos anahtarla DEVAM ETMEMELI. `[ -z "$PAKET_ANAHTAR" ]` kapisi
        durmali. Bu eksen METIN capasidir (kabuk davranisi YAML'dan calistirilamaz);
        KABUL EDILEN BEDEL: yorum icindeki bir mensiyon da "duruyor" sayilir
        ([[kapi-disiplin-ilkesi]] — kapi disiplin cihazidir, hapishane degil)."""
    hata = []
    if yml_metin is None:
        if not os.path.exists(IMAJ_YML):
            return False, ["onizleme-imaj.yml bulunamadi: %s" % IMAJ_YML]
        with open(IMAJ_YML, encoding="utf-8") as f:
            yml_metin = f.read()
    varsayilan = yml_varsayilan_anahtar(yml_metin)
    if varsayilan:
        hata.append("BAYAT VARSAYILAN GERI GELDI: onizleme-imaj.yml paket_anahtar "
                    "girdisinin varsayilani %r -> is akisi GIRDI VERILMEDEN "
                    "tetiklenirse bu (bayatlayabilen) anahtardan imaj derler ve hicbir "
                    "adim KIRMIZI vermez (2-renk parca aileleri olmayan paketle SESSIZ "
                    "yanlis imaj). Varsayilani KALDIRIN (required: true yeter); anahtari "
                    "her tetiklemede python3 tools/onizleme-paket-yukle.py ciktisindan "
                    "girin." % varsayilan)
    if BOS_GIRDI_CAPASI not in yml_metin:
        hata.append("BOS GIRDI KAPISI YOK: onizleme-imaj.yml'de %r gecmiyor -> varsayilan "
                    "olmadigi icin girdi BOS gelebilir ve is akisi bos anahtarla devam "
                    "eder (s3 dizin yolu cekilir / paket bos kalir -> sessiz yanlis imaj). "
                    "GERI KOY: paketi ceken adimin basina bos-anahtar kontrolu + exit 1."
                    % BOS_GIRDI_CAPASI)
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
    fault-injection ile (yukleyici ekseni gercek fonksiyon yerine sahte uretici alir).

    30 Tem: (c) BAYAT VARSAYILAN ve (d) BOS GIRDI KAPISI eksenleri eklendi. Fikstur
    SENTETIKTIR (gercek dosya degismekle bayatlamaz) ama girdi blogu gercek YAML
    girintisini taklit eder cunku (c) ekseni yml_varsayilan_anahtar() ayristiricisini
    FIILEN kosar."""
    hata = []
    girdi_bloksuz = (
        "on:\n  workflow_dispatch:\n    inputs:\n      paket_anahtar:\n"
        '        description: "R2 paket anahtari"\n'
        "        type: string\n"
        "        required: true\n"
        "      push_et:\n"
        "        type: boolean\n")
    kapi = ('        run: |\n'
            '          if ' + BOS_GIRDI_CAPASI + '; then\n'
            '            echo "::error::anahtar BOS"\n'
            '            exit 1\n'
            '          fi\n'
            '          aws s3 cp "s3://' + BUCKET + '/$PAKET_ANAHTAR" paket.tar.gz\n')
    iyi_yml = (girdi_bloksuz
               + '        env:\n          PAKET_ANAHTAR: ${{ inputs.paket_anahtar }}\n'
               + kapi)
    kotu_yml = (girdi_bloksuz
                + '        run: aws s3 cp "s3://' + BUCKET +
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
    # (c) BAYAT VARSAYILAN — girdiye varsayilan geri konursa KIRMIZI olmali.
    varsayilanli = iyi_yml.replace(
        "        required: true\n",
        '        required: true\n        default: "onizleme/paket-v6.tar.gz"\n', 1)
    ok, _ = surumlu_anahtar_nobeti(varsayilanli, iyi_uretici)
    if ok:
        hata.append("INERT (varsayilan ekseni): paket_anahtar girdisine varsayilan "
                    "konmus YAML'da YESIL dedi -> bayat varsayilan sessizce geri gelebilir")
    # POZITIF karsi-kontrol: ayristirici GERCEKTEN okuyor mu (aksi halde ustteki iddia
    # "hep None doner" diye sahte-yesil olurdu).
    if yml_varsayilan_anahtar(varsayilanli) != "onizleme/paket-v6.tar.gz":
        hata.append("VARSAYILAN AYRISTIRICISI SAGIR: sentetik varsayilan okunamadi (%r) "
                    "-> (c) ekseni hep None gorup sahte-yesil yanar"
                    % yml_varsayilan_anahtar(varsayilanli))
    if yml_varsayilan_anahtar(iyi_yml) is not None:
        hata.append("VARSAYILAN AYRISTIRICISI HAYALET: varsayilansiz fiksturde deger "
                    "buldu (%r)" % yml_varsayilan_anahtar(iyi_yml))
    # (d) BOS GIRDI KAPISI — kapi silinirse KIRMIZI olmali.
    ok, _ = surumlu_anahtar_nobeti(iyi_yml.replace(BOS_GIRDI_CAPASI, '[ -n "$BASKA" ]'),
                                   iyi_uretici)
    if ok:
        hata.append("INERT (bos girdi ekseni): bos-anahtar kapisi olmayan YAML'da "
                    "YESIL dedi -> varsayilansiz girdi bos gelirse is akisi devam eder")
    return (not hata), hata


def geri_okuma_nobeti():
    """GERI OKUMA YENIDEN DENEME NOBETI (30 Tem 2026) — yukleyicinin R2 dogrulamasi
    yayilma yarisini KAYBETMIYOR ama SESSIZ FAIL-OPEN de yapmiyor mu.

    OLCULEN ARIZA: yeni R2 anahtarinin yayilmasi ~18-24 s surebiliyor; eski kod geri
    okumayi ANINDA + TEK DENEME yapiyordu -> saglam yukleme SAHTE KIRMIZI olculuyordu.
    Onarim yeniden deneme ekledi; bu nobetci onarimin ters yone (sessiz yesile)
    kacmadigini da olcer.

    YONTEM: ag/wrangler YOK — PAKET.geri_oku_dogrula()'ya sahte `get` ve `bekle`
    ENJEKTE edilir (metin capasi degil DAVRANIS olcumu)."""
    hata = []
    gecici = tempfile.mkdtemp(prefix="geri-okuma-nobeti-")
    try:
        arsiv = os.path.join(gecici, "paket.tar.gz")
        with open(arsiv, "wb") as f:
            f.write(b"DOGRU-PAKET-ICERIGI")
        dogru = open(arsiv, "rb").read()
        geri = os.path.join(gecici, "geri.tar.gz")

        def sahte(plan):
            """plan: [(rc, yazilacak_bayt_ya_da_None), ...] — sirayla uygulanir; liste
            biterse son giris tekrarlanir."""
            durum = {"n": 0}

            def get(_anahtar, hedef):
                i = min(durum["n"], len(plan) - 1)
                durum["n"] += 1
                rc, icerik = plan[i]
                if icerik is not None:
                    with open(hedef, "wb") as f:
                        f.write(icerik)
                return rc
            return get, durum

        beklemeler = []
        bekle = beklemeler.append

        # (1) POZITIF: ilk denemede dogru icerik -> ok, deneme=1, HIC beklenmemis.
        get, durum = sahte([(0, dogru)])
        del beklemeler[:]
        ok, gecmis, deneme, sn, sha = PAKET.geri_oku_dogrula(
            "k", arsiv, geri, get=get, bekle=bekle)
        if not (ok and deneme == 1 and sn == 0.0 and not beklemeler):
            hata.append("(1) POZITIF BOZUK: ilk denemede dogru icerik -> ok=%s deneme=%s "
                        "beklenen_sn=%s (1 deneme, 0 s olmali; gecmis=%r)"
                        % (ok, deneme, sn, gecmis))

        # (2) YAYILMA GECIKMESI (OLCULEN GERCEK SENARYO): ilk 3 `get` nesneyi
        #     bulamiyor, 4. deneme dogru icerikle geliyor -> BASARIYLA tamamlanmali.
        get, durum = sahte([(1, None), (1, None), (1, None), (0, dogru)])
        del beklemeler[:]
        ok, gecmis, deneme, sn, sha = PAKET.geri_oku_dogrula(
            "k", arsiv, geri, get=get, bekle=bekle)
        if not (ok and deneme == 4):
            hata.append("(2) YAYILMA YARISI KAYBEDILDI: ilk 3 `get` bos donunce yukleme "
                        "basarisiz sayildi (ok=%s deneme=%s) -> saglam yukleme SAHTE "
                        "KIRMIZI olculur (gecmis=%r)" % (ok, deneme, gecmis))
        if ok and sum(beklemeler) <= 0:
            hata.append("(2) BEKLEME YOK: yeniden denemeler arasinda hic beklenmedi -> "
                        "yayilma penceresi kapatilmiyor, sadece hizlica tekrar deniyor")

        # (3) BUTCE ASIMI -> SESSIZ FAIL-OPEN OLMAZ: hic gorunmezse KIRMIZI.
        get, durum = sahte([(1, None)])
        del beklemeler[:]
        ok, gecmis, deneme, sn, sha = PAKET.geri_oku_dogrula(
            "k", arsiv, geri, get=get, bekle=bekle)
        if ok or sha is not None:
            hata.append("(3) SESSIZ FAIL-OPEN: nesne hic gorunmedigi halde dogrulama "
                        "BASARILI sayildi (ok=%s sha=%r)" % (ok, sha))
        if deneme != len(PAKET.GERI_OKUMA_ARALIKLARI) + 1:
            hata.append("(3) DENEME SAYISI TUTMUYOR: %d deneme olculdu, %d bekleniyordu "
                        "(1 + aralik sayisi)"
                        % (deneme, len(PAKET.GERI_OKUMA_ARALIKLARI) + 1))

        # (4) SHA UYUSMAZLIGI (asil sessiz-uzerine-yazma arizasi) HALA KIRMIZI mi.
        get, durum = sahte([(0, b"BAYAT-V5-ICERIGI")])
        del beklemeler[:]
        ok, gecmis, deneme, sn, sha = PAKET.geri_oku_dogrula(
            "k", arsiv, geri, get=get, bekle=bekle)
        if ok:
            hata.append("(4) SHA KARSILASTIRMASI OLU: R2'de BAYAT icerik varken dogrulama "
                        "YESIL dedi -> sessiz uzerine-yazma arizasi geri gecer")
        if sha is None:
            hata.append("(4) TESHIS KAYBI: uyusmazlikta son sha rapor edilmedi -> teshis "
                        "'nesne yok' ile karisir (yanlis cozum onerilir)")

        # (5) BAYAT DOSYA SAVUNMASI: 1. deneme rc!=0 ama DOGRU baytlari birakti;
        #     sonraki denemeler nesneyi bulamiyor (dosya yazmiyor). Denemeden once
        #     hedef SILINMEZSE onceki turun dosyasi "nesne var" gibi okunur -> YESIL.
        get, durum = sahte([(1, dogru), (0, None)])
        del beklemeler[:]
        ok, gecmis, deneme, sn, sha = PAKET.geri_oku_dogrula(
            "k", arsiv, geri, get=get, bekle=bekle)
        if ok:
            hata.append("(5) BAYAT DOSYA KACAGI: onceki denemenin biraktigi dosya "
                        "'R2'de nesne var' sayildi -> nesne olmadan YESIL yanar "
                        "(geri_oku_dogrula her denemeden ONCE hedefi SILMELI)")

        # (6) BUTCE TABANI: olculen yayilma penceresi ~24 s; butce en az 2 KATI olmali.
        butce = sum(PAKET.GERI_OKUMA_ARALIKLARI)
        if butce < 48.0:
            hata.append("(6) BUTCE KUCULTULMUS: toplam yeniden deneme butcesi %.0f s -> "
                        "olculen yayilma penceresinin (~24 s) iki katinin ALTINDA; sahte "
                        "kirmizi geri gelir" % butce)
    finally:
        subprocess.run(["rm", "-rf", gecici])
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
    ok6, h6 = geri_okuma_nobeti()
    oz_yesil = ok1 and ok2 and ok4 and ok6
    print("OZ-NOBETCI: %s" % ("YESIL" if oz_yesil else "KIRMIZI"))
    for h in h1 + h2 + h4 + h6:
        print("  ❌ %s" % h)
    if args.kendini_test:
        sys.exit(0 if oz_yesil else 1)

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
    kirmizi = bool(sorunlar) or not (oz_yesil and ok3 and ok5)
    print("SONUC: %s" % ("KIRMIZI" if kirmizi else "YESIL"))
    sys.exit(1 if kirmizi else 0)


if __name__ == "__main__":
    main()
