#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONIZLEME KISIT KOSUL TESTI — kosullu (`eger`) beyan HER tuketicide AYNI hukmu mu veriyor?

NE KORUR (musteriye basilan cumle):
  secenekler.js ONIZLEME_KISITLAR bir "uretilebilir degerler beyaz listesi"dir. On-kontrol
  ihlal gorurse musteriye "bu secenekle siparis alinmiyor" basilir. Vida ailesinin sema
  kisiti KOSULLUDUR (jenerator/urunler/olcuye-ozel-vida-civata-somun-pul.json:
  `urun_tipi=civata` iken `cap >= 5`). Kosulsuz yazilsaydi mil/somun/pul x M3-M4 bolgesi
  URETILEBILIR oldugu halde bloklanir, yani yanlis bir musteri vaadi basilirdi. Bu test
  kosulun GERCEKTEN tuttugunu ve kosulsuz girdilerin (cetvel/kase/petek) davranisinin
  BIREBIR korundugunu OLCER.

NE OLCER (hepsi node ile FIILEN kosturularak; regex ile "okumus gibi" yapilmaz):
  1. TUKETICI ENVANTERI — ONIZLEME_KISITLAR'i anan IZLENEN her dosya beyan edilmis
     sinifta mi (fail-closed: yeni/kaybolan tuketici KIRMIZI). KARAR sinifi (musteriye
     hukum basan iki yol) tek kaynak fonksiyonu cagirmak ZORUNDA; PARAM-ADI sinifi
     (olcum/duman fiksturleri) kisiti PARAMETRE ADIYLA indeksler — `eger` ancak bir
     semada "eger" adli parametre olsaydi onlara sizardi, o da ayrica olculur.
  2. SEMADAN TURETME — beyan edilen `cap` listesi = cap.gecerliDegerler ∩ (sema kisiti
     min) ve `eger` blogu semadaki `eger` ile AYNI. Elle tutulan ikinci liste yok;
     ayrisma KIRMIZI.
  3. VAKA MATRISI — ayni vaka kumesi UC KATMANDA AYRI AYRI olculur (tek bir "engellendi"
     sonucu katmanlarin VEYA'sidir ve deligi gizler, bkz. [[beyan-edilmis-survivor]]):
       S) SEMA DOGRULAMASI: jenerator/konfigurator.js KONF.dogrula — semanin KENDI
          `kisitlar` blogu (vida: eger civata -> cap>=5) burada zaten uygulanir.
       A) urun sayfasi on-kontrolu: tools/build.py ONIZLEME_JS icindeki GERCEK kaynak
          parcasi cikarilip node'da icra edilir (de(...) cagrildi mi = BLOK).
       B) GERCEK worker: onizleme/src/index.js node'a yuklenir, /api/onizleme/olustur'a
          POST atilir. Uc ayri sonuc AYRI tutulur: BLOK-KISIT:<alan> (400
          onizleme-secenek-kisiti = BU beyanin hukmu), BLOK-SEMA (400 parametre-araligi
          = UST katman zaten kesti), SERBEST (derleyici baglanmadigi icin 503).
     🔴 OLCULEN GOLGE: vida'da S katmani cap<5'i ZATEN kesiyor — worker'da bu beyan
     civata kolunda HIC konusmuyor (civata-M3 vakalari B'de BLOK-SEMA). Beyanin
     olculebilir kendi katkisi (i) `eger` TUTMADIGINDA blok BASMAMASI (pul/mil/somun
     kolu — M1/M2 mutantlari bu vakayi oldurur) ve (ii) kosulsuz girdilerde (cetvel)
     B'de BLOK-KISIT olarak GORUNMESIDIR.
  4. TIP EKSENI — `cap` SAYISAL. Sayfada konfigurator (jenerator/konfigurator.js:457
     degerler(), parseFloat) NUMBER uretir; Worker'da sema kapisi SAF SAYI METNINI de
     ("5") kabul eder (index.js "SIKI TIP KAPISI"). Kati `===`/`indexOf` ile yazilsaydi
     IZINLI ama metin gelen bir deger ("5") listede BULUNAMAZ ve URETILEBILIR bir
     konfigurasyona yanlis vaat basilirdi -> M3 mutanti tam bunu oldurur.
  4b IZGARA — vida ailesinin TAM secim uzayi (4 tip x 11 cap = 44) sayfa on-kontrolunde
     olculur; BLOKLU kume TAM OLARAK {civata-M3, civata-M4} olmali. Tek sayilik olcu:
     beyan hem gereginden fazla (mil/somun/pul yanlis blok) hem eksik (uretilemez
     bolge serbest) blokladiginda KIRMIZI yanar.
  6. KOSUL DEGERI YAZIM HATASI (3 Agu 2026, olculdu ve onarildi) — `eger` blogunun
     SEKLI dogru ama DEGERI semaya gore hicbir girdiyle eslesemiyorsa (dizi, sayi,
     nesne, null, liste disi metin, tanimsiz parametre adi) eski kod girdiyi
     SESSIZCE tumden dusuruyordu: civata-M3 BLOK -> SERBEST, yani uretilemez bir
     konfigurasyona "siparis alinabilir" vaadi. Artik ihlal donuyor. Ayni eksende
     MESRU kullanimin bozulmadigi da olculur: `urun_tipi:"civata"` (bugunku beyan),
     sayisal kosul `cap:5`/`cap:"5"` ve AYIRT EDICI `cap:3`/`cap:"3"` — tip-agnostik
     esleme (5 <-> "5") AYNEN korunur.
  7. BOZUK-BEYAN KOLUNUN MUTANTLARI — 6. eksenin kolu, mesru beyanda hic konusmadigi
     icin ayri bir mutant takimiyla olculur (M4-M8; K2 kontrol mutanti).
  8. SEMASIZ KOL SINIRI — fonksiyon 3. argumansiz cagrilirsa yalniz TIP AILESI
     olculebilir (dizi/nesne/bool/null yakalanir; `secim` parametresine yazilmis 7
     YAKALANMAZ). Docstring'in fazla iddia etmemesi icin bu SINIR da olculur
     ([[nobetci-kendi-dosyasinda-sizinti]]). Iki canli cagri yeri de semayi TASIR:
     Worker sema kapisindan, urun sayfasi satir-ici URUN_SEMA'dan.
  5. MUTANTLAR (daima KOPYAYA; canli agac sha256 basta==sonda):
       M1 `eger` ele alisi kaldirildi (kosul okunmaz)   -> pul/M3 YANLIS bloklanir (alan=cap)
       M2 kosul TUTMAYINCA ihlal sayildi (`eger` beyaz liste gibi) -> pul/M3 YANLIS
          bloklanir (alan=urun_tipi; M1'den ALANIYLA ayrilir)
       M3 deger karsilastirmasi kati `===`e cekildi     -> civata/"5" (metin) YANLIS bloklanir
       K1 KONTROL: yalniz yorum eklendi                 -> tum hukumler DEGISMEZ
       M4 kosul degeri eslesebilirlik kolu oldurulda    -> bozuk beyan yine SESSIZ
       M5 `secim` kolu her degeri kabul eder            -> liste disi kosul degeri sizar
       M6 kosul parametre ADI semaya karsi denetlenmez  -> tanimsiz ad SESSIZCE atlanir
       M7 `sayi` kolunda gecerliDegerler okunmaz        -> asla eslesemeyen cap sizar
       M8 sema 3. arguman yok sayilir                   -> tip ailesine duser, 7 sizar
       K2 KONTROL (bozuk beyan kolu): yalniz yorum      -> tum hukumler DEGISMEZ
     `eger` ANAHTARININ beyaz liste gibi taranmasi AYRI bir mutant DEGILDIR: oldurucu
     vakasi yok (kisit["eger"] icin p["eger"] daima undefined -> atlanir). O eksen
     1c iddiasiyla korunur (hicbir semada "eger" adli parametre yok).

NE OLCMEZ: vida'nin onizlemeye ACILDIGINI (olculdu: `olcuye-ozel-vida-civata-somun-pul`
  secenekler.js ONIZLEME_AILELER listesinde DEGIL -> worker onu bugun 404 ile ceviriyor).
  Worker kolunda aile beyaz listesi FIKSTUR olarak genisletilir; bu, "vida yayinda"
  IDDIASI DEGILDIR — beyanin acilis gunu dogru hukmu vermesini olcer.
  Ayrica: uretim motorunun gercekten M3 civata basip basamadigini (o sema/paket isi),
  satis kapisini (tools/onizleme-vaat-kapisi.py A3) ve DOM'daki konfigurator akisini.

Kosum:  python3 tools/onizleme-kisit-kosul-test.py        (node 20 ZORUNLU; node yoksa
        fail-closed exit 1 — "yesil" degil KIRMIZI). Offline, depoya YAZMAZ.
"""
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
AILE_VIDA = "olcuye-ozel-vida-civata-somun-pul"
AILE_CETVEL = "olcuye-ozel-cetvel"

# ---------------------------------------------------------------- tuketici envanteri
# ONIZLEME_KISITLAR'i anan IZLENEN dosyalar ve SINIFLARI. Yeni bir dosya cikarsa ya da
# beyan edilen biri kaybolursa kapi KIRMIZI yanar (sessiz ayrisma [[ikiz-tanim-sessiz-ayrisma]]).
#   TANIM     : beyanin ve tek-kaynak fonksiyonun yasadigi dosya
#   KARAR     : MUSTERIYE hukum basan yol -> onizlemeKisitIhlali() cagirmak ZORUNDA
#   AD-LISTESI: yalniz Object.keys/urun id'leri okur (parametre degerine bakmaz)
#   PARAM-ADI : kisiti PARAMETRE ADIYLA indeksler (olcum/duman evreni daraltma)
#   FIKSTUR   : kendi sentetik ONIZLEME_KISITLAR metnini yazar
#   IS-AKISI  : yalnizca yorum/adim metni
TUKETICI_BEYANI = {
    "secenekler.js": "TANIM",
    "tools/build.py": "KARAR",
    "onizleme/src/index.js": "KARAR",
    "tools/onizleme-vaat-kapisi.py": "AD-LISTESI",
    "tools/onizleme-kapisi.py": "PARAM-ADI",
    "onizleme/test/eslem-olcum.py": "PARAM-ADI",
    "onizleme/test/kabul.js": "PARAM-ADI",
    "onizleme/test/duman_kabul.py": "FIKSTUR",
    ".github/workflows/deploy.yml": "IS-AKISI",
    ".github/workflows/onizleme-imaj.yml": "IS-AKISI",
    "tools/onizleme-kisit-kosul-test.py": "KENDISI",
}

IDDIA = []          # (ad, gecti_mi, ek)
OLCULEMEDI = []


def iddia(ad, kosul, ek=""):
    IDDIA.append((ad, bool(kosul), ek))
    print(("  [OK  ] " if kosul else "  [KIRMIZI] ") + ad + (" — " + ek if ek else ""))


def olculemedi(ad, sebep):
    OLCULEMEDI.append((ad, sebep))
    print("  [OLCULEMEDI] %s — %s" % (ad, sebep))


def oku(yol):
    with io.open(os.path.join(REPO, yol), encoding="utf-8") as f:
        return f.read()


def sha256(yol):
    h = hashlib.sha256()
    with open(os.path.join(REPO, yol), "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# ---------------------------------------------------------------- 1) envanter

def envanter_olc():
    proc = subprocess.run(["git", "-C", REPO, "grep", "-l", "--untracked",
                           "ONIZLEME_KISITLAR", "--", "."], capture_output=True)
    if proc.returncode not in (0, 1):
        olculemedi("1 TUKETICI ENVANTERI", "git grep calismadi: %s" %
                   proc.stderr.decode("utf-8", "replace")[:200])
        return
    bulunan = set(x for x in proc.stdout.decode("utf-8").split("\n") if x.strip())
    beyan = set(TUKETICI_BEYANI)
    iddia("1a ONIZLEME_KISITLAR tuketici envanteri beyanla BIREBIR",
          bulunan == beyan,
          "yeni=%s kayip=%s (toplam %d)" % (sorted(bulunan - beyan), sorted(beyan - bulunan),
                                            len(bulunan)))
    for yol, sinif in sorted(TUKETICI_BEYANI.items()):
        if sinif != "KARAR":
            continue
        kaynak = oku(yol)
        iddia("1b KARAR tuketicisi tek kaynak fonksiyonu cagiriyor: %s" % yol,
              "onizlemeKisitIhlali(" in kaynak, "")
    # PARAM-ADI sinifinin `eger`e dokunmamasinin OLCUSU: hicbir semada "eger" adli
    # parametre yok (olsaydi o dosyalar `eger` blogunu beyaz liste sanardi).
    egerli = []
    dizin = os.path.join(REPO, "jenerator", "urunler")
    for ad in sorted(os.listdir(dizin)):
        if not ad.endswith(".json"):
            continue
        with io.open(os.path.join(dizin, ad), encoding="utf-8") as f:
            sema = json.load(f)
        for p in sema.get("parametreler") or []:
            if p.get("ad") == "eger":
                egerli.append(ad)
    iddia("1c hicbir semada `eger` ADLI parametre yok (PARAM-ADI tuketicileri korunur)",
          not egerli, "carpisan sema=%s" % egerli)
    # 1d PARAM-ADI sinifi kisiti KOSULSUZ uygular (duman/olcum evrenini daraltirken).
    # Bugun bu SAPMA URETMIYOR: vida'nin sema VARSAYILANLARI (urun_tipi=civata, cap=5)
    # zaten beyaz listede. Varsayilan degisirse bu iddia KIRMIZI yanar ve o tuketicilerin
    # de `eger`i ele almasi gerekir -> sessiz daralma olmaz.
    try:
        yol = os.path.join(TOOLS, "onizleme-kapisi.py")
        spec = importlib.util.spec_from_file_location("_onizleme_kapisi", yol)
        ok = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ok)
        kisitlar = ok._js_sabiti(oku("secenekler.js"), "ONIZLEME_KISITLAR")
        semalar = ok.semalari_tara(os.path.join(REPO, "jenerator", "urunler"))
        sapan = {}
        for aile, kisit in sorted(kisitlar.items()):
            sema = semalar.get(aile)
            if not sema:
                continue
            ham = dict((t["ad"], t.get("varsayilan")) for t in sema.get("parametreler") or [])
            cekilen = ok.varsayilan_parametreler(sema, kisit)
            if "eger" in kisit and any(ham[k] != cekilen[k] for k in ham):
                sapan[aile] = dict((k, [ham[k], cekilen[k]]) for k in ham
                                   if ham[k] != cekilen[k])
        iddia("1d KOSULLU girdi PARAM-ADI tuketicilerinin varsayilan setini SAPTIRMIYOR",
              not sapan, "sapan=%s" % json.dumps(sapan, ensure_ascii=False))
    except Exception as e:                                   # noqa: BLE001 (fail-closed)
        olculemedi("1d PARAM-ADI varsayilan sapmasi",
                   "onizleme-kapisi.py okunamadi: %s" % str(e)[:200])


# ---------------------------------------------------------------- 2) semadan turetme

def beyani_oku():
    """secenekler.js ONIZLEME_KISITLAR sabitini node ile JSON'a cevirir (gercek deger)."""
    proc = subprocess.run(
        ["node", "-e",
         "import(process.argv[1]).then(()=>{"
         "process.stdout.write(JSON.stringify(globalThis.PRUVO_SECENEK.ONIZLEME_KISITLAR));});",
         os.path.join(REPO, "secenekler.js")],
        capture_output=True)
    if proc.returncode != 0:
        return None, proc.stderr.decode("utf-8", "replace")[:300]
    return json.loads(proc.stdout.decode("utf-8")), ""


def semadan_turet():
    with io.open(os.path.join(REPO, "jenerator", "urunler", AILE_VIDA + ".json"),
                 encoding="utf-8") as f:
        sema = json.load(f)
    cap = [p for p in sema["parametreler"] if p["ad"] == "cap"][0]
    kisit = (sema.get("kisitlar") or [])[0]
    izinli = [v for v in cap["gecerliDegerler"] if v >= kisit["min"]]
    return {"eger": kisit["eger"], "cap": izinli}


def turetme_olc(beyan):
    beklenen = semadan_turet()
    var = beyan.get(AILE_VIDA)
    iddia("2a vida beyani semadan TURETILMIS degerlerle BIREBIR (elle ikinci liste yok)",
          var == beklenen, "beyan=%s sema=%s" % (json.dumps(var, sort_keys=True),
                                                 json.dumps(beklenen, sort_keys=True)))
    kosulsuz = dict((k, v) for k, v in beyan.items() if k != AILE_VIDA)
    iddia("2b kosulsuz girdiler DOKUNULMADAN duruyor (geriye uyum)",
          all("eger" not in v for v in kosulsuz.values()) and len(kosulsuz) == 3,
          "girdi=%s" % sorted(kosulsuz))


# ---------------------------------------------------------------- 3) sayfa parcasi

def sayfa_parcasi():
    """tools/build.py ONIZLEME_JS icindeki GERCEK on-kontrol parcasini cikarir
    (dengeli parantez; regexle 'okumus gibi' yapilmaz — parca node'da ICRA edilir)."""
    kaynak = oku("tools/build.py")
    bas = kaynak.index("var kis=(window.PRUVO_SECENEK")
    i = kaynak.index("if(", bas)
    j = kaynak.index("(", i)
    derinlik = 0
    while j < len(kaynak):
        if kaynak[j] == "(":
            derinlik += 1
        elif kaynak[j] == ")":
            derinlik -= 1
            if derinlik == 0:
                break
        j += 1
    k = kaynak.index("{", j)
    derinlik = 0
    son = k
    while son < len(kaynak):
        if kaynak[son] == "{":
            derinlik += 1
        elif kaynak[son] == "}":
            derinlik -= 1
            if derinlik == 0:
                break
        son += 1
    parca = kaynak[bas:son + 1]
    if "de(\"Bu se" not in parca or not parca.rstrip().endswith("}"):
        raise ValueError("on-kontrol parcasi cikarilamadi (build.py yazimi degismis)")
    return parca


# ---------------------------------------------------------------- 3) vaka matrisi

def vida(urun_tipi, cap):
    return {"urun_tipi": urun_tipi, "cap": cap, "boy": 20, "tolerans": 0.2}


def cetvel(tip):
    return {"tip": tip, "sistem": "metrik", "uzunluk": 15, "genislik": 30,
            "kalinlik": 3, "isaret_stili": "oyma"}


# (id, aile, parametreler, {kol: beklenen}, aciklama)
#   S = KONF.dogrula (sema `kisitlar` katmani)  A = sayfa on-kontrolu  B = GERCEK worker
VAKALAR = [
    ("civata-M3-sayi", AILE_VIDA, vida("civata", 3),
     {"S": "GECERSIZ", "A": "BLOK", "B": "BLOK-SEMA"},
     "kosul TUTAR, M3 uretilemez — B'de UST katman keser (golge)"),
    ("civata-M3-metin", AILE_VIDA, vida("civata", "3"),
     {"S": "GECERSIZ", "A": "BLOK", "B": "BLOK-SEMA"},
     "ayni, sayi METNI olarak"),
    ("civata-M5", AILE_VIDA, vida("civata", 5),
     {"S": "GECERLI", "A": "SERBEST", "B": "SERBEST"},
     "kosul tutar, M5 uretilebilir"),
    ("civata-M5-metin", AILE_VIDA, vida("civata", "5"),
     {"S": "GECERLI", "A": "SERBEST", "B": "SERBEST"},
     "TIP EKSENI: izinli deger METIN olarak gelirse de bloklanmaz"),
    ("pul-M3", AILE_VIDA, vida("pul", 3),
     {"S": "GECERLI", "A": "SERBEST", "B": "SERBEST"},
     "YANLIS-POZITIF NOBETCISI: kosul TUTMAZ, uretilebilir"),
    ("mil-M4", AILE_VIDA, vida("mil", 4),
     {"S": "GECERLI", "A": "SERBEST", "B": "SERBEST"}, "kosul TUTMAZ"),
    ("somun-M3-metin", AILE_VIDA, vida("somun", "3"),
     {"S": "GECERLI", "A": "SERBEST", "B": "SERBEST"}, "kosul tutmaz + metin tip"),
    ("cetvel-ucgen", AILE_CETVEL, cetvel("ucgen"),
     {"S": "GECERLI", "A": "BLOK", "B": "BLOK-KISIT:tip"},
     "KOSULSUZ girdi regresyonu — beyanin B'de TEK BASINA olculdugu vaka"),
    ("cetvel-duz", AILE_CETVEL, cetvel("duz"),
     {"S": "GECERLI", "A": "SERBEST", "B": "SERBEST"}, "KOSULSUZ girdi regresyonu"),
]

# IZGARA: vida ailesinin TAM secim uzayi (4 tip x 11 cap = 44). Beyanin dogru
# okundugunun tek sayilik OLCUSU: bloklu kume TAM OLARAK {civata-M3, civata-M4}.
VIDA_TIPLERI = ["civata", "mil", "somun", "pul"]
VIDA_CAPLARI = [3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20]
IZGARA = [("%s-M%s" % (t, c), AILE_VIDA, vida(t, c))
          for t in VIDA_TIPLERI for c in VIDA_CAPLARI]
IZGARA_BEKLENEN_BLOK = ["civata-M3", "civata-M4"]

# ---------------------------------------------------------------- bozuk `eger` KOSUL DEGERI
# Beyanin KODU degil METNI degistirilir: kaynaktaki tek `eger` satiri baska bir kosul
# degeriyle yeniden yazilir. Iddia: eslesmesi SEMAYA gore imkansiz olan bir deger
# girdiyi SESSIZCE dusurmez (fail-closed), mesru bir deger ise bugunku gibi calisir.
KOSUL_CAPA = '      eger: { urun_tipi: "civata" },'

# (ad, `eger` satiri, {vaka: (A beklenen, B beklenen)}, aciklama)
KOSUL_VARYANTLARI = [
    ("dizi   urun_tipi:[\"civata\"]", '      eger: { urun_tipi: ["civata"] },',
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "dizi hicbir secim degeriyle eslesemez -> YAZIM HATASI"),
    ("sayi   urun_tipi:7", "      eger: { urun_tipi: 7 },",
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "secim parametresinde 7 diye bir secenek YOK -> YAZIM HATASI"),
    ("nesne  urun_tipi:{}", "      eger: { urun_tipi: {} },",
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "nesne -> YAZIM HATASI"),
    ("null   urun_tipi:null", "      eger: { urun_tipi: null },",
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "null -> YAZIM HATASI"),
    ("liste-disi urun_tipi:\"civata2\"", '      eger: { urun_tipi: "civata2" },',
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "dogru tip AILESI ama sema seceneklerinde YOK -> YAZIM HATASI"),
    ("tanimsiz parametre adi", '      eger: { urun_tipii: "civata" },',
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "semada boyle bir parametre YOK -> YAZIM HATASI (kosul asla cozulemez)"),
    ("MESRU  urun_tipi:\"civata\"", KOSUL_CAPA,
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("SERBEST", "SERBEST")},
     "BUGUNKU beyan — davranis AYNEN"),
    ("MESRU  cap:5 (sayisal kosul)", "      eger: { cap: 5 },",
     {"civata-M3-sayi": ("SERBEST", "BLOK-SEMA"), "pul-M3": ("SERBEST", "SERBEST"),
      "civata-M5": ("SERBEST", "SERBEST")},
     "sayisal parametre uzerinden kosul CALISIR (M5'te tutar, beyaz liste 5'i gecirir)"),
    ("MESRU  cap:\"5\" (sayisal metin)", '      eger: { cap: "5" },',
     {"civata-M3-sayi": ("SERBEST", "BLOK-SEMA"), "pul-M3": ("SERBEST", "SERBEST"),
      "civata-M5": ("SERBEST", "SERBEST")},
     "TIP-AGNOSTIK esleme korunur: \"5\" ile 5 AYNI hukum"),
    ("MESRU  cap:3 (AYIRT EDICI)", "      eger: { cap: 3 },",
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:cap"),
      "civata-M5": ("SERBEST", "SERBEST")},
     "sayisal kosul TUTUNCA beyaz liste uygulanir (M3 listede yok -> BLOK)"),
    ("MESRU  cap:\"3\" (AYIRT EDICI, metin)", '      eger: { cap: "3" },',
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:cap"),
      "civata-M5": ("SERBEST", "SERBEST")},
     "ayni hukum, sayi METNI olarak — tip-agnostik esleme"),
    ("liste-disi cap:7", "      eger: { cap: 7 },",
     {"civata-M3-sayi": ("BLOK", "BLOK-SEMA"), "pul-M3": ("BLOK", "BLOK-KISIT:eger")},
     "7 semanin gecerliDegerler listesinde YOK -> asla eslesemez -> YAZIM HATASI"),
]

# SEMASIZ KOL (3. arguman verilmezse) — docstring'in BILDIRDIGI sinir. Fikstur
# kisitlari sentetiktir; iddia "yakalanir/yakalanmaz" ayrimidir, hukum degil.
def semasiz_vakalar():
    beyaz = {"cap": [5, 6, 8]}
    p = vida("civata", 3)

    def k(deger):
        d = {"eger": {"urun_tipi": deger}}
        d.update(beyaz)
        return d
    return [
        ("semasiz-dizi", k(["civata"]), p, "eger", "dizi TIP AILESI ile yakalanir"),
        ("semasiz-nesne", k({}), p, "eger", "nesne TIP AILESI ile yakalanir"),
        ("semasiz-null", k(None), p, "eger", "null TIP AILESI ile yakalanir"),
        ("semasiz-bool", k(True), p, "eger", "bool TIP AILESI ile yakalanir"),
        ("semasiz-sayi7", k(7), p, None, "SINIR: dogru aileden yanlis deger YAKALANMAZ"),
        ("semasiz-mesru", k("civata"), p, "cap", "mesru kosul: beyaz liste uygulanir"),
    ]

HARNESS = r"""
import fs from "node:fs";
import { pathToFileURL } from "node:url";

const kfg = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
await import(pathToFileURL(kfg.secenekler).href);
const KONF = (await import(pathToFileURL(kfg.konfigurator).href)).default;
const { SEMALAR } = await import(pathToFileURL(kfg.semalar).href);
const S = globalThis.PRUVO_SECENEK;
// FIKSTUR (iddia DEGIL): vida bugun ONIZLEME_AILELER'de yok -> worker 404 verirdi.
for (const a of kfg.fiksturAileler) {
  if (!S.ONIZLEME_AILELER.includes(a)) { S.ONIZLEME_AILELER.push(a); }
}
const worker = await import(pathToFileURL(kfg.worker).href);

/** Sayfa on-kontrolu. URUN_SEMA sayfada SATIR-ICI durur (build.py `var URUN_SEMA =`)
 *  ve on-kontrol onu kisit fonksiyonuna 3. arguman olarak verir; burada AYNI kaynaktan
 *  (SEMALAR) beslenir — fikstur uydurulmaz. */
function sayfaHukmu(urunId, parametreler) {
  let mesaj = null;
  const fn = new Function("window", "URUN", "s", "kutu", "de", "URUN_SEMA",
                          kfg.sayfaParcasi + "\nreturn 'SERBEST';");
  const r = fn(globalThis, { id: urunId }, { parametreler }, { hidden: true },
               (m) => { mesaj = m; }, SEMALAR.get(urunId) || null);
  if (mesaj !== null) { return { hukum: "BLOK", mesaj: mesaj }; }
  if (r === "SERBEST") { return { hukum: "SERBEST" }; }
  return { hukum: "BELIRSIZ" };
}

let ipSayaci = 0;
async function workerHukmu(aile, parametreler) {
  ipSayaci += 1;
  const istek = new Request("https://pruvo3d.com/api/onizleme/olustur", {
    method: "POST",
    headers: { "Content-Type": "application/json",
               "CF-Connecting-IP": "10.0.0." + ipSayaci },   // hiz siniri karismasin
    body: JSON.stringify({ aile, parametreler }),
  });
  const env = { SITE_URL: "https://pruvo3d.com",
                ONBELLEK: { async get() { return null; }, async put() {} } };
  const yanit = await worker.default.fetch(istek, env);
  let govde = null;
  try { govde = await yanit.json(); } catch (e) { /* binary/bos */ }
  if (yanit.status === 400 && govde && govde.hata === "onizleme-secenek-kisiti") {
    return { hukum: "BLOK-KISIT:" + govde.alan };
  }
  if (yanit.status === 400 && govde && govde.hata === "parametre-araligi") {
    return { hukum: "BLOK-SEMA", alanlar: (govde.alanlar || []).join(",") };
  }
  if (yanit.status === 400 || yanit.status === 404) {
    return { hukum: "OLCUM-HATASI", http: yanit.status, govde: JSON.stringify(govde) };
  }
  return { hukum: "SERBEST", http: yanit.status };
}

/** SEMA KATMANI TEK BASINA: semanin kendi `kisitlar` blogu ne diyor (kisit beyanindan
 *  BAGIMSIZ) — katmanlarin VEYA'si degil, her katman ayri olculsun. */
function semaHukmu(aile, parametreler) {
  const sema = SEMALAR.get(aile);
  if (!sema) { return { hukum: "OLCUM-HATASI", ayrinti: "sema yok: " + aile }; }
  const s = KONF.dogrula(sema, parametreler);
  return s.gecerli ? { hukum: "GECERLI" }
                   : { hukum: "GECERSIZ", alanlar: Object.keys(s.hatalar || {}).join(",") };
}

const cikti = { S: {}, A: {}, B: {}, IZ: {}, SEMASIZ: {} };
for (const v of kfg.vakalar) {
  cikti.S[v.id] = semaHukmu(v.aile, v.parametreler);
  cikti.A[v.id] = sayfaHukmu(v.aile, v.parametreler);
  cikti.B[v.id] = await workerHukmu(v.aile, v.parametreler);
}
// IZGARA: vida ailesinin TAM konfigurasyon uzayi, yalniz sayfa on-kontrolunde
// (worker'a 44 istek atmak bu iddiaya bir sey katmaz — kisit hukmu AYNI fonksiyon).
for (const v of kfg.izgara) { cikti.IZ[v.id] = sayfaHukmu(v.aile, v.parametreler); }
// SEMASIZ KOL: fonksiyon 3. arguman OLMADAN cagrilinca ne garanti ediyor
// (docstring'in "yalniz tip ailesi" siniri — fazla iddia birakilmasin).
for (const v of kfg.semasizVakalar) {
  cikti.SEMASIZ[v.id] = { ihlal: S.onizlemeKisitIhlali(v.kisit, v.parametreler) };
}
process.stdout.write(JSON.stringify(cikti));
"""


def json_gom(kaynak, kaynak_dizin):
    """`import X from "....json";` -> `const X = {...};` (bozuk JSON sessizce sizmaz)."""
    def degistir(m):
        yol = os.path.normpath(os.path.join(kaynak_dizin, m.group(2)))
        with io.open(yol, encoding="utf-8") as f:
            ham = f.read().strip()
        json.loads(ham)
        return "const %s = %s;" % (m.group(1), ham)
    cikti = re.sub(r'^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$',
                   degistir, kaynak, flags=re.M)
    if re.search(r'from\s+"[^"]*\.json"', cikti):
        raise ValueError("JSON import gomulemedi — yukleyici bayat")
    return cikti


def varyant_kos(tmp, ad, secenekler_metni, sayfa, vakalar):
    """Bir secenekler.js varyantini (taban ya da mutant) IKI tuketicide de kosturur."""
    src = os.path.join(REPO, "onizleme", "src")
    shop_src = os.path.join(REPO, "shop", "src")
    sec_yol = os.path.join(tmp, "secenekler-%s.js" % ad)
    with io.open(sec_yol, "w", encoding="utf-8") as f:
        f.write(secenekler_metni)
    index = oku("onizleme/src/index.js")
    yeni = index.replace('from "../../shop/src/semalar.js"', 'from "./semalar.js"')
    yeni = yeni.replace('import "../../secenekler.js";',
                        'import "./secenekler-%s.js";' % ad)
    if yeni == index or ("./secenekler-%s.js" % ad) not in yeni:
        raise ValueError("index.js import yollari bulunamadi — yukleyici bayat")
    idx_yol = os.path.join(tmp, "index-%s.js" % ad)
    with io.open(idx_yol, "w", encoding="utf-8") as f:
        f.write(json_gom(yeni, src))
    kfg = {"secenekler": sec_yol, "worker": idx_yol, "sayfaParcasi": sayfa,
           "konfigurator": os.path.join(REPO, "jenerator", "konfigurator.js"),
           "semalar": os.path.join(tmp, "semalar.js"),
           "fiksturAileler": [AILE_VIDA],
           "vakalar": [{"id": v[0], "aile": v[1], "parametreler": v[2]} for v in vakalar],
           "izgara": [{"id": v[0], "aile": v[1], "parametreler": v[2]} for v in IZGARA],
           "semasizVakalar": [{"id": v[0], "kisit": v[1], "parametreler": v[2]}
                              for v in semasiz_vakalar()]}
    kfg_yol = os.path.join(tmp, "kfg-%s.json" % ad)
    with io.open(kfg_yol, "w", encoding="utf-8") as f:
        f.write(json.dumps(kfg))
    proc = subprocess.run(["node", os.path.join(tmp, "harness.mjs"), kfg_yol],
                          capture_output=True, cwd=REPO)
    if proc.returncode != 0:
        raise RuntimeError("node varyant '%s' rc=%d: %s" %
                           (ad, proc.returncode, proc.stderr.decode("utf-8", "replace")[-800:]))
    return json.loads(proc.stdout.decode("utf-8"))


# ---------------------------------------------------------------- mutantlar

# (ad, eski, yeni, [(vaka, kol, mutantta_beklenen), ...])
MUTANTLAR = [
    ("M1 `eger` ele alisi kaldirildi (kosul hic okunmaz)",
     "    var kosul = kisit[ONIZLEME_KISIT_KOSUL];",
     "    var kosul = undefined;",
     [("pul-M3", "A", "BLOK"), ("pul-M3", "B", "BLOK-KISIT:cap")]),
    ("M2 kosul TUTMAYINCA ihlal sayildi (`eger` beyaz liste gibi)",
     "        if (!kisitDegeriEsit(kosul[k], p[k])) { return null; }",
     "        if (!kisitDegeriEsit(kosul[k], p[k])) { return k; }",
     [("pul-M3", "A", "BLOK"), ("pul-M3", "B", "BLOK-KISIT:urun_tipi")]),
    ("M3 deger karsilastirmasi kati `===` (indexOf gibi)",
     "    if (beyan === deger) { return true; }",
     "    return beyan === deger;",
     [("civata-M5-metin", "A", "BLOK"), ("civata-M5-metin", "B", "BLOK-KISIT:cap")]),
]
KONTROL_MUTANT = ("K1 KONTROL: yalniz yorum eklendi",
                  "  function onizlemeKisitIhlali(kisit, parametreler, sema) {",
                  "  /* kontrol mutanti: anlamsiz yorum */\n"
                  "  function onizlemeKisitIhlali(kisit, parametreler, sema) {")

# ---- BOZUK-KOSUL kolunun mutantlari: kod mutasyonu BOZUK BEYAN uzerinde kosulur.
# Taban beyanla olculemezler (mesru beyanda yeni kol hic konusmaz) — bu yuzden AYRI.
# (ad, eski, yeni, `eger` satiri, [(vaka, kol, mutantta_beklenen)])
KOSUL_MUTANTLARI = [
    ("M4 deger-eslesebilirlik kolu OLDURULDU (yazim hatasi yine sessiz)",
     "        if (!kosulDegeriEslesebilirMi(tanim, kosul[k])) "
     "{ return ONIZLEME_KISIT_KOSUL; }",
     "        if (false) { return ONIZLEME_KISIT_KOSUL; }",
     '      eger: { urun_tipi: ["civata"] },',
     [("civata-M3-sayi", "A", "SERBEST"), ("pul-M3", "A", "SERBEST")]),
    ("M5 `secim` kolu her degeri kabul eder (liste disi deger sizar)",
     "      if (!Array.isArray(tanim.secenekler)) { return false; }",
     "      if (!Array.isArray(tanim.secenekler)) { return false; }\n      return true;",
     '      eger: { urun_tipi: "civata2" },',
     [("civata-M3-sayi", "A", "SERBEST"), ("pul-M3", "A", "SERBEST")]),
    ("M6 kosul parametre ADI semaya karsi denetlenmez",
     "        if (tanimlar && !tanim) { return ONIZLEME_KISIT_KOSUL; }",
     "        if (false) { return ONIZLEME_KISIT_KOSUL; }",
     '      eger: { urun_tipii: "civata" },',
     [("pul-M3", "B", "BLOK-KISIT:cap")]),
    ("M7 `sayi` kolunda gecerliDegerler listesi okunmaz",
     "      if (Array.isArray(tanim.gecerliDegerler)) {",
     "      if (false && Array.isArray(tanim.gecerliDegerler)) {",
     "      eger: { cap: 7 },",
     [("pul-M3", "B", "SERBEST")]),
    ("M8 sema 3. arguman YOK SAYILIR (tip ailesine duser)",
     "      var tanimlar = semaParametreHaritasi(sema);",
     "      var tanimlar = null;",
     "      eger: { urun_tipi: 7 },",
     [("civata-M3-sayi", "A", "SERBEST"), ("pul-M3", "A", "SERBEST")]),
]
KOSUL_KONTROL_MUTANT = (
    "K2 KONTROL (bozuk beyan kolu): yalniz yorum eklendi",
    "  function kosulDegeriEslesebilirMi(tanim, deger) {",
    "  /* kontrol mutanti: anlamsiz yorum */\n"
    "  function kosulDegeriEslesebilirMi(tanim, deger) {")


def main():
    print("ONIZLEME KISIT KOSUL TESTI — kosullu (`eger`) beyan, TUM tuketicilerde")
    izlenen = ["secenekler.js", "tools/build.py", "onizleme/src/index.js"]
    basta = dict((y, sha256(y)) for y in izlenen)
    print("SHA256 BASTA:")
    for y in izlenen:
        print("  %s  %s" % (basta[y], y))

    print("\n[1] TUKETICI ENVANTERI")
    envanter_olc()

    print("\n[2] SEMADAN TURETME")
    beyan, hata = beyani_oku()
    if beyan is None:
        olculemedi("2 SEMADAN TURETME", "node ile secenekler.js okunamadi: %s" % hata)
    else:
        turetme_olc(beyan)

    print("\n[3] VAKA MATRISI (A: sayfa on-kontrolu · B: GERCEK worker)")
    tmp = os.path.join(REPO, "onizleme", "kisit-kosul-tmp-%d" % os.getpid())
    for ad in os.listdir(os.path.join(REPO, "onizleme")):
        if ad.startswith("kisit-kosul-tmp-"):
            shutil.rmtree(os.path.join(REPO, "onizleme", ad), ignore_errors=True)
    os.makedirs(tmp)
    try:
        with io.open(os.path.join(tmp, "harness.mjs"), "w", encoding="utf-8") as f:
            f.write(HARNESS)
        shutil.copyfile(os.path.join(REPO, "onizleme", "src", "derleyici.js"),
                        os.path.join(tmp, "derleyici.js"))
        with io.open(os.path.join(REPO, "shop", "src", "semalar.js"), encoding="utf-8") as f:
            semalar = f.read()
        with io.open(os.path.join(tmp, "semalar.js"), "w", encoding="utf-8") as f:
            f.write(json_gom(semalar, os.path.join(REPO, "shop", "src")))
        sayfa = sayfa_parcasi()
        sec_metni = oku("secenekler.js")

        taban = varyant_kos(tmp, "taban", sec_metni, sayfa, VAKALAR)
        etiket = {"S": "sema dogrulamasi", "A": "sayfa on-kontrolu", "B": "GERCEK worker"}
        for vid, aile, param, beklenenler, aciklama in VAKALAR:
            for kol in ("S", "A", "B"):
                sonuc = taban[kol][vid]
                iddia("3 %s [%s] %s -> %s (%s)" %
                      (kol, etiket[kol], vid, beklenenler[kol], aciklama),
                      sonuc.get("hukum") == beklenenler[kol],
                      "olculen=%s" % json.dumps(sonuc, ensure_ascii=False))
        bloklu = sorted(k for k, v in taban["IZ"].items() if v.get("hukum") == "BLOK")
        iddia("3z IZGARA %d konfigurasyonda BLOKLU kume TAM OLARAK %s" %
              (len(IZGARA), IZGARA_BEKLENEN_BLOK),
              bloklu == IZGARA_BEKLENEN_BLOK and len(taban["IZ"]) == len(IZGARA),
              "bloklu=%s (olculen=%d)" % (bloklu, len(taban["IZ"])))

        print("\n[4] MUTANTLAR (daima KOPYAYA)")
        for sira, (ad, eski, yeni, beklenen_farklar) in enumerate(MUTANTLAR, 1):
            if sec_metni.count(eski) != 1:
                olculemedi(ad, "mutasyon capasi %d kez bulundu (kaynak degismis)" %
                           sec_metni.count(eski))
                continue
            mutant = varyant_kos(tmp, "m%d" % sira, sec_metni.replace(eski, yeni),
                                 sayfa, VAKALAR)
            for vid, kol, mut_beklenen in beklenen_farklar:
                tab = taban[kol][vid].get("hukum")
                mut = mutant[kol][vid].get("hukum")
                iddia("4 %s [%s] mutant OLDU: %s -> %s" % (kol, ad, vid, mut_beklenen),
                      mut == mut_beklenen and mut != tab,
                      "taban=%s mutant=%s" % (tab, mut))
        ad, eski, yeni = KONTROL_MUTANT
        if sec_metni.count(eski) != 1:
            olculemedi(ad, "kontrol capasi %d kez bulundu" % sec_metni.count(eski))
        else:
            kontrol = varyant_kos(tmp, "k1", sec_metni.replace(eski, yeni), sayfa, VAKALAR)
            ayni = all(kontrol[k][v[0]].get("hukum") == taban[k][v[0]].get("hukum")
                       for k in ("S", "A", "B") for v in VAKALAR)
            iddia("4 %s: TUM hukumler DEGISMEDI (batarya asiri duyarli degil)" % ad, ayni,
                  "vaka=%d x 3 kol" % len(VAKALAR))

        # ---------------------------------------------------------- 6) bozuk kosul degeri
        print("\n[6] `eger` KOSUL DEGERI — yazim hatasi girdiyi SESSIZCE dusuruyor mu")
        if sec_metni.count(KOSUL_CAPA) != 1:
            olculemedi("6 KOSUL DEGERI EKSENI",
                       "`eger` satiri %d kez bulundu (kaynak degismis)" %
                       sec_metni.count(KOSUL_CAPA))
        else:
            for sira, (ad, satir, beklenenler, aciklama) in enumerate(KOSUL_VARYANTLARI, 1):
                v = varyant_kos(tmp, "kv%d" % sira, sec_metni.replace(KOSUL_CAPA, satir),
                                sayfa, VAKALAR)
                for vid, (a_bek, b_bek) in sorted(beklenenler.items()):
                    for kol, bek in (("A", a_bek), ("B", b_bek)):
                        s = v[kol][vid]
                        iddia("6 %s [%s] %s -> %s (%s)" % (kol, ad, vid, bek, aciklama),
                              s.get("hukum") == bek,
                              "olculen=%s" % json.dumps(s, ensure_ascii=False))

            print("\n[7] BOZUK-BEYAN KOLUNUN MUTANTLARI (daima KOPYAYA)")
            for sira, (ad, eski, yeni, satir, farklar) in enumerate(KOSUL_MUTANTLARI, 1):
                if sec_metni.count(eski) != 1:
                    olculemedi(ad, "mutasyon capasi %d kez bulundu (kaynak degismis)" %
                               sec_metni.count(eski))
                    continue
                temel = sec_metni.replace(KOSUL_CAPA, satir)
                tab = varyant_kos(tmp, "km%dt" % sira, temel, sayfa, VAKALAR)
                mut = varyant_kos(tmp, "km%dm" % sira, temel.replace(eski, yeni),
                                  sayfa, VAKALAR)
                for vid, kol, mut_bek in farklar:
                    t = tab[kol][vid].get("hukum")
                    m = mut[kol][vid].get("hukum")
                    iddia("7 %s [%s] mutant OLDU: %s -> %s" % (kol, ad, vid, mut_bek),
                          m == mut_bek and m != t, "taban=%s mutant=%s" % (t, m))
            ad, eski, yeni = KOSUL_KONTROL_MUTANT
            if sec_metni.count(eski) != 1:
                olculemedi(ad, "kontrol capasi %d kez bulundu" % sec_metni.count(eski))
            else:
                bozuk = sec_metni.replace(KOSUL_CAPA, '      eger: { urun_tipi: 7 },')
                kt = varyant_kos(tmp, "k2t", bozuk, sayfa, VAKALAR)
                km = varyant_kos(tmp, "k2m", bozuk.replace(eski, yeni), sayfa, VAKALAR)
                ayni2 = all(km[k][v[0]].get("hukum") == kt[k][v[0]].get("hukum")
                            for k in ("S", "A", "B") for v in VAKALAR)
                iddia("7 %s: TUM hukumler DEGISMEDI" % ad, ayni2,
                      "vaka=%d x 3 kol" % len(VAKALAR))

        # ---------------------------------------------------------- 8) semasiz kol siniri
        print("\n[8] SEMASIZ KOL SINIRI (docstring fazla iddia etmiyor mu)")
        for vid, kisit, param, bek, aciklama in semasiz_vakalar():
            olculen = taban["SEMASIZ"][vid]["ihlal"]
            iddia("8 sema VERILMEDEN %s -> ihlal=%s (%s)" % (vid, bek, aciklama),
                  olculen == bek, "olculen=%s" % json.dumps(olculen, ensure_ascii=False))
    except (RuntimeError, ValueError, OSError) as e:
        olculemedi("3/4/6/7/8 VAKA MATRISI + MUTANTLAR", str(e)[:500])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nSHA256 SONDA (canli agaca yazma OLMAMALI):")
    kirli = []
    for y in izlenen:
        s = sha256(y)
        print("  %s  %s" % (s, y))
        if s != basta[y]:
            kirli.append(y)
    iddia("5 mutasyon canli agaca YAZMADI (sha256 basta==sonda)", not kirli,
          "degisen=%s" % kirli)
    artik = [a for a in os.listdir(os.path.join(REPO, "onizleme"))
             if a.startswith("kisit-kosul-tmp-")]
    iddia("5b gecici dizin temizlendi", not artik, "artik=%s" % artik)

    kirmizi = [a for a, ok, _ in IDDIA if not ok]
    print("\nIDDIA=%d  KIRMIZI=%d  OLCULEMEDI=%d" % (len(IDDIA), len(kirmizi), len(OLCULEMEDI)))
    if kirmizi:
        print("KIRMIZI iddialar:")
        for a in kirmizi:
            print("  - " + a)
    return 1 if (kirmizi or OLCULEMEDI) else 0


if __name__ == "__main__":
    sys.exit(main())
