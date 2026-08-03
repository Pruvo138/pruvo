#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — ana sayfa CIP SATIRLARI (MARKA · GRUP · MODEL): capraz daralir, OLU UC vermez.

  python3 tools/cip-indeks-test.py              # kabul (CI'da bloklayici)
  python3 tools/cip-indeks-test.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/cip-indeks-test.py --kok /yol   # BASKA agactan oku (mutasyon icin)

NEDEN VAR (olculen musteri sikayeti, 2 Agu — canli): `Marin` + `Bujiler` secili, 136 urun,
hepsi ayni marka bujisi. Buna ragmen MARKA satiri hala Mercury/Volvo/Yamaha/Jeanneau/
Beneteau/GoPro/Zodiac gosteriyordu; hicbirinin Bujiler grubunda urunu YOK. Musteri
tiklarsa 0 urun goruyordu. Kok neden: cip evrenleri KATEGORIDEN turetiliyordu, o anki
FILTRELENMIS kumeden degil. Sabit/kartezyen menude bosluk orani: Marin %86,2 ·
Motosiklet %72 · Otomobil %58.

OLCULEN SESSIZ-HATA SINIFLARI (bu kapinin varlik sebebi):
  1. "cip GORUNUR, TIKLANIR, liste DEGISMEZ" — DOM'da cip aramak bu sinifi GORMEZ.
  2. "cip gosterilir ama 0 urun verir" (olu uc) — sayi degisir, MUSTERI BOS EKRAN gorur.
  3. "uc parametreyi SESSIZCE YOK SAYAR" — olculdu: /katalog?marka=BMW&model=E46 ->
     toplam 1673 = marka toplaminin AYNISI. Istemci kabul ederse musteri YANLIS liste gorur.
  4. "satir KENDI secimiyle daralir" — kullanici filtreyi DEGISTIREMEZ hale gelir.
Bu yuzden HER iddianin KONTROL EKSENI vardir: sayi DEGISMELI, uydurma deger 0 DONMELI,
donen kayitlarin DEGERI secilene esit OLMALI, gorunen HER cip TEK TEK tiklanip >0
olculmeli (ORNEKLEME YOK).

MIMARI: hukum burada, ICRA tools/cip-indeks-kosum.js'te (index.html'in GERCEK inline
scripti node:vm'de kosar; kod KOPYALANMAZ). Kosum dosyasi bilerek "-test.js" ADINDA DEGIL:
ci-kapsam kesfi ikinci bir CI girisi beklemesin.

CIP INDEKSI UYDURULMAZ: fikstur katalogu burada tanimlanir, GERCEK uretec
(tools/cip-indeks.py) onun uzerinde calistirilir ve cikti kosuma verilir. Uretecte ya da
istemcide bir mutasyon otekini de kirmizi yakar (tek olcum, iki taraf).

AGA CIKMAZ, DISKE YAZMAZ: fetch sahtedir; index.html / urunler.json yalnizca OKUNUR.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)
KOSUM = os.path.join(DIR, "cip-indeks-kosum.js")

# 🔴 IDDIA SAYISI SOZLESMESI (olcut ESIT, ">=" DEGIL): kosum dosyasindan bir iddia
# SESSIZCE dusurulurse ya da bir mod hic kosmazsa kapi KIRMIZI yanar.
BEKLENEN_IDDIA = 91


_EVREN_BELLEK = {}


def evren_taninmis(index_metni, ci, ad):
    """`ad` index.html'in TANINMIS_MARKALAR listesinde mi (kuratorluk ekseni icin)."""
    if "e" not in _EVREN_BELLEK:
        _EVREN_BELLEK["e"] = ci.MarkaEvreni(index_metni)
    return _EVREN_BELLEK["e"].taninmis_mi(ad)


def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- FIKSTUR
# KUCUK ve ELLE SAYILABILIR. Her iddia beklenen sayiyi KENDI hesaplar (kosum tarafinda
# katalogtan), sabit gomulmez. Markalar TANINMIS_MARKALAR'da AYNEN yazilidir.
#   Otomobil/BMW  20 urun: Motor Bolumu 12 (E46 5 · E36 4 · modelsiz 3) + Aydinlatma 8
#                          (E46 3 · modelsiz 5)   -> E46=8, E36=4  (2 model, ikisi de >=3)
#   Otomobil/Ford 16 urun: hepsi Motor Bolumu; Focus 9 + HAM "E36" tasiyan 3 + modelsiz 4
#                          -> tek gecerli model (Focus) => marka >=2 model SARTINI GECMEZ
#                          -> Ford'da MODEL SATIRI CIZILMEZ; ayrica "E36" etiketi BMW
#                             disinda da gectigi icin BELIRSIZ olur (indeks `x` DUSER)
#   Otomobil/Opel 10 urun: Aydinlatma  -> <15 esigi: CIP OLMAZ
#   Marin/Mercury 18 urun: Motor Parcalari    (Pervaneler'de HIC urunu YOK)
#   Marin/Yamaha  16 urun: Pervaneler         (Motor Parcalari'nda HIC urunu YOK)
def fikstur():
    urunler = []

    def ekle(pid, kategori, altkategori, marka, uyum):
        urunler.append({
            "id": pid, "kategori": kategori, "altkategori": altkategori,
            "marka": list(marka), "uyum": list(uyum),
            "baslik": "Test " + pid, "aciklama": "aciklama " + pid, "fiyat": "100 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/" + pid + ".jpg"],
        })

    for i in range(1, 6):
        ekle("bmw-mb-e46-%d" % i, "Otomobil", "Motor Bölümü", ["BMW", "E46"],
             [{"marka": "BMW", "model": "E46"}])
    for i in range(1, 5):
        ekle("bmw-mb-e36-%d" % i, "Otomobil", "Motor Bölümü", ["BMW", "E36"],
             [{"marka": "BMW", "model": "E36"}])
    for i in range(1, 4):
        ekle("bmw-mb-x-%d" % i, "Otomobil", "Motor Bölümü", ["BMW"], [{"marka": "BMW"}])
    # E60: 2 urun -> ESIK_MODEL (3) ALTINDA. Cip OLMAMALI. Bu kayit ESIK MUTANTININ
    # olduruculugunu saglar (esik 1'e dusurulurse E60 cip olur ve E0 kirmizi yanar).
    for i in range(1, 3):
        ekle("bmw-mb-e60-%d" % i, "Otomobil", "Motor Bölümü", ["BMW", "E60"],
             [{"marka": "BMW", "model": "E60"}])
    for i in range(1, 4):
        ekle("bmw-ay-e46-%d" % i, "Otomobil", "Aydınlatma", ["BMW", "E46"],
             [{"marka": "BMW", "model": "E46"}])
    for i in range(1, 6):
        ekle("bmw-ay-x-%d" % i, "Otomobil", "Aydınlatma", ["BMW"], [{"marka": "BMW"}])

    for i in range(1, 10):
        ekle("ford-mb-focus-%d" % i, "Otomobil", "Motor Bölümü", ["Ford", "Focus"],
             [{"marka": "Ford", "model": "Focus"}])
    for i in range(1, 4):
        ekle("ford-mb-e36-%d" % i, "Otomobil", "Motor Bölümü", ["Ford", "E36"],
             [{"marka": "Ford"}])
    for i in range(1, 5):
        ekle("ford-mb-x-%d" % i, "Otomobil", "Motor Bölümü", ["Ford"], [{"marka": "Ford"}])

    for i in range(1, 11):
        ekle("opel-ay-%d" % i, "Otomobil", "Aydınlatma", ["Opel"], [{"marka": "Opel"}])

    for i in range(1, 19):
        ekle("mercury-mp-%d" % i, "Marin", "Motor Parçaları", ["Mercury"], [])
    for i in range(1, 17):
        ekle("yamaha-pv-%d" % i, "Marin", "Pervaneler", ["Yamaha"], [])
    # UC ETIKETI EKSENI (olculen CANLI hata, 3 Agu): Marin'de HAM etiket "Volvo Penta";
    # kanonik "Volvo" bu kategoride HAM olarak HIC gecmez. Cip "Volvo" yazar, UC ise ham
    # etiketle TAM eslesir (katlamaz) -> kanonik gonderilirse 0 doner = OLU UC.
    # KENDI GRUBUNDA durur ("Anotlar") ki mevcut Motor Parçaları/Pervaneler daralma
    # iddialarinin beklenen degerleri DEGISMESIN.
    # 15 urun = ESIK_MARKA siniri (cip olur). KONTROL EKSENI ayni fikstordedir:
    # Mercury/Yamaha'da kanonik = ham -> `e` DOGMAMALI (davranis bayt-ayni kalmali).
    for i in range(1, 16):
        ekle("volvopenta-an-%d" % i, "Marin", "Anotlar", ["Volvo Penta"], [])
    # KURATORLUK KAPSAM ESIGI EKSENI (ESIK_UYUM_KAPSAM) — POZITIF ve KONTROL ayni fiksturde.
    #   Marin    : `uyum` kapsami %0  -> GEVSEK  -> TANINMAYAN "Teleflex" (15) CIP OLMALI
    #   Otomobil : `uyum` kapsami %100 -> KURATORLU -> TANINMAYAN "Denso" (16) CIP OLMAMALI
    # Tek yon yazilsaydi "kuratorlugu her yerde kaldir" mutanti YESIL gecerdi; iki yon
    # birlikte esigin KENDISINI olcer (esigi 0'a ya da 1'e kaydiran mutant birini kirar).
    for i in range(1, 16):
        ekle("teleflex-fl-%d" % i, "Marin", "Filtreler", ["Teleflex"], [])
    for i in range(1, 17):
        ekle("denso-mb-%d" % i, "Otomobil", "Motor Bölümü", ["Denso"],
             [{"marka": "Denso"}])
    return urunler


# ---------------------------------------------------------------- CSS OLCUMU
# Mobil cip satiri KAYDIRILABILIR TEK SATIR olmali. Bu eksen node kosumunda OLCULEMEZ
# (DOM taklidinde yerlesim yok), bu yuzden kural KAYNAK CSS'ten AYIKLANIR: dar ekran
# medya blogundaki `.brand-chips` kurali sarma KAPALI + yatay kaydirma ACIK olmali.
# (Gercek piksel olcumu — 375px'te ilk kartin y'si — tarayicida yapilir ve raporlanir.)
def mobil_cip_kurali(index_metni):
    m = re.search(r"@media\(max-width:640px\)\{\s*\n\s*\.brand-row\{(.*?)^  \}$",
                  index_metni, re.S | re.M)
    if not m:
        return None
    govde = m.group(1)
    k = re.search(r"\.brand-chips\{(.*?)\}", govde, re.S)
    if not k:
        return None
    bildirimler = {}
    for parca in k.group(1).split(";"):
        if ":" in parca:
            ad, deger = parca.split(":", 1)
            bildirimler[ad.strip()] = deger.strip()
    return bildirimler


# ---------------------------------------------------------------- KABUL
def kabul(kok):
    kaldi = []
    # 🔴 SAYAC KODA GOMULMEZ: burada eskiden `toplam = len(iddialar) + 14` yaziyordu ve
    # python tarafina iddia eklendikce BAYATLADI (olculdu: gercek 18 iken 14 yaziyordu ->
    # rapor eksik sayi basiyordu). Sayi artik SAYILARAK uretilir.
    gecen = []

    def dogrula(ad, kosul, detay=""):
        if kosul:
            gecen.append(ad)
            print("  GECTI %s%s" % (ad, (" — " + detay) if detay else ""))
        else:
            kaldi.append(ad)
            print("  KALDI %s%s" % (ad, (" — " + detay) if detay else ""))

    ci = _modul(os.path.join(kok, "tools", "cip-indeks.py"), "cip_indeks_kabul")
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_metni = f.read()

    # --- A) GERCEK KATALOG: indeks esikleri + SIFIR kombinasyon YOK -----------
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        gercek = json.load(f)
    ix = ci.indeks_uret(gercek, index_metni)
    marka_ihlal, model_ihlal, sifir, tek_model = [], [], [], []
    for kat, kd in ix["kat"].items():
        for mk, d in kd.items():
            if d["n"] < ci.ESIK_MARKA:
                marka_ihlal.append("%s/%s=%d" % (kat, mk, d["n"]))
            for k, n in d["a"].items():
                if n <= 0:
                    sifir.append("%s/%s/alt%s" % (kat, mk, k))
            if d["m"] and len(d["m"]) < ci.EN_AZ_MODEL:
                tek_model.append("%s/%s=%d" % (kat, mk, len(d["m"])))
            for md, y in d["m"].items():
                if y["n"] < ci.ESIK_MODEL:
                    model_ihlal.append("%s/%s/%s=%d" % (kat, mk, md, y["n"]))
                for k, n in y["a"].items():
                    if n <= 0:
                        sifir.append("%s/%s/%s/alt%s" % (kat, mk, md, k))
    toplam_marka = sum(len(v) for v in ix["kat"].values())
    toplam_model = sum(len(x["m"]) for v in ix["kat"].values() for x in v.values())
    print("  GERCEK KATALOG: %d urun -> %d kategori · %d marka · %d model"
          % (len(gercek), len(ix["kat"]), toplam_marka, toplam_model))
    dogrula("A1 HER MARKA CIPI >= %d URUN" % ci.ESIK_MARKA, not marka_ihlal,
            "marka=%d ihlal=%d %s" % (toplam_marka, len(marka_ihlal), marka_ihlal[:3]))
    dogrula("A2 HER MODEL CIPI >= %d URUN" % ci.ESIK_MODEL, not model_ihlal,
            "model=%d ihlal=%d %s" % (toplam_model, len(model_ihlal), model_ihlal[:3]))
    dogrula("A3 MODELLI HER MARKADA >= %d MODEL" % ci.EN_AZ_MODEL, not tek_model,
            "ihlal=%d %s" % (len(tek_model), tek_model[:3]))
    dogrula("A4 INDEKSTE SIFIRLI KOMBINASYON YOK (olu uc tasinmaz)", not sifir,
            "sifir=%d %s" % (len(sifir), sifir[:3]))
    dogrula("A5 INDEKS BOS DEGIL (fail-closed: bos indeks = daralma yok)",
            toplam_marka > 0 and toplam_model > 0 and len(ix["alt"]) > 0,
            "marka=%d model=%d alt=%d" % (toplam_marka, toplam_model, len(ix["alt"])))

    # --- A6/A7) UC MARKA ETIKETI: gorunen cip UCTA da >0 olmali -------------
    # 🔴 UC SIMULATORU YAZILMAZ (bu depoda olculdu: fikstur ucu taklit ederse test
    # uretimi degil KENDI varsayimini aynalar). Iddia dogrudan KATALOG uzerinde
    # kurulur: ucun sozlesmesi CANLI olculdu — HAM etiketle TAM eslesir, katlamaz
    # (tools/cip-indeks.py :: modul docstring'i). O halde istemcinin gonderecegi etiketin
    # o kategoride HAM olarak >0 urunde gecmesi GEREK VE YETER.
    ham_sayim = {}   # (kat, HAM etiket) -> n   (URUN bazli, cip sayimiyla ayni birim)
    for u in gercek:
        k = (u.get("kategori") or "").strip()
        for ham in set((x or "").strip() for x in (u.get("marka") or []) if (x or "").strip()):
            ham_sayim[(k, ham)] = ham_sayim.get((k, ham), 0) + 1
    olu, sapan = [], []
    for kat, kd in ix["kat"].items():
        for mk, d in kd.items():
            etiket = d.get("e", mk)          # istemcinin gonderecegi etiket
            n = ham_sayim.get((kat, etiket), 0)
            if n <= 0:
                olu.append("%s/%s->'%s'=0" % (kat, mk, etiket))
            if "e" in d and d["e"] == mk:
                sapan.append("%s/%s: `e` kanonige esit (gereksiz bayt)" % (kat, mk))
    dogrula("A6 GORUNEN HER MARKA CIPININ UC ETIKETI KATALOGDA >0 (olu uc YOK)",
            not olu, "cip=%d olu=%d %s" % (toplam_marka, len(olu), olu[:3]))
    # --- A8/A9) KURATORLUK KAPSAM ESIGI: kural VERIDEN, kategori ADINDAN degil ----
    # A6 NOTU: bu eksen YEREL katalogu olcer. `yayinda` D1'e ait bir kolondur ve
    # urunler.json'da YOKTUR -> yeni parti urunler yayin penceresinde iken uc onlari
    # HENUZ gostermez. A6'nin yesili "etiket dogru", "uc bugun >0 donuyor" DEGILDIR.
    kaps = ci.uyum_kapsami(gercek)
    gevsek_ihlal, kuratorlu_ihlal = [], []
    for kat, kd in ix["kat"].items():
        kuratorlu_mu = kaps.get(kat, 0.0) >= ci.ESIK_UYUM_KAPSAM
        for mk in kd:
            if kuratorlu_mu and not evren_taninmis(index_metni, ci, mk):
                kuratorlu_ihlal.append("%s/%s (kapsam %.1f%%)" % (kat, mk, 100 * kaps.get(kat, 0)))
            if (not kuratorlu_mu) and not evren_taninmis(index_metni, ci, mk):
                gevsek_ihlal.append("%s/%s" % (kat, mk))
    dogrula("A8 KURATORLU KATEGORIDE (uyum kapsami >= %.0f%%) HER CIP TANINMIS MARKA"
            % (100 * ci.ESIK_UYUM_KAPSAM), not kuratorlu_ihlal,
            "ihlal=%d %s" % (len(kuratorlu_ihlal), kuratorlu_ihlal[:3]))
    dogrula("A9 KONTROL: GEVSEK KATEGORIDE TANINMAYAN URETICI CIPI VAR (kural etkili)",
            len(gevsek_ihlal) > 0,
            "gevsek kategorilerde tanınmayan cip=%d %s" % (len(gevsek_ihlal), gevsek_ihlal[:4]))

    dogrula("A7 `e` YALNIZ KANONIK HAM OLARAK YOKKEN YAZILIR (gereksiz alan yok)",
            not sapan, "e-tasiyan=%d sapan=%d %s"
            % (sum(1 for kd in ix["kat"].values() for d in kd.values() if "e" in d),
               len(sapan), sapan[:3]))

    # --- B) YAYIN KOPYASINA ENJEKSIYON GERCEKTEN OLUYOR ---------------------
    # Kaynak index.html'de indeks YOKTUR (bilerek); build.py yayin kopyasina gomer.
    # Enjeksiyon kopmusssa capraz daralma canlida SESSIZCE kaybolurdu.
    gomulu = ci.enjekte(index_metni, ix)
    dogrula("B1 ENJEKSIYON YAYIN KOPYASINA INDEKSI GOMER",
            "window.PRUVO_CIP_INDEKS=" in gomulu and gomulu.count("</head>") >= 1 and
            gomulu.index("window.PRUVO_CIP_INDEKS=") < gomulu.index("</head>"),
            "%d bayt buyudu" % (len(gomulu) - len(index_metni)))
    # Kaynakta yalniz OKUMA gecer (cipIndeks()); ATAMA gecmemeli — atama gecseydi indeks
    # kaynak dosyaya gomulmus olurdu ve her urun partisi onu bayatlatirdi.
    dogrula("B2 KAYNAK index.html'de INDEKS ATAMASI YOK (urun partisi blogu bayatlatmasin)",
            "window.PRUVO_CIP_INDEKS=" not in index_metni.replace(" ", ""),
            "kaynak temiz (yalniz okuma var)")
    with open(os.path.join(kok, "tools", "build.py"), encoding="utf-8") as f:
        build_metni = f.read()
    dogrula("B3 build.py YAYIN KOPYASINDA ENJEKTORU CAGIRIYOR",
            "cip_indeks.enjekte(" in build_metni and
            "yayin_index(marka_sonuc, products)" in build_metni,
            "kablolama yerinde")

    # --- C) MOBIL CIP SATIRI: kaydirilabilir tek satir ----------------------
    kural = mobil_cip_kurali(index_metni)
    dogrula("C1 DAR EKRANDA CIP SATIRI SARMAZ (flex-wrap:nowrap)",
            bool(kural) and kural.get("flex-wrap") == "nowrap",
            "kural=%s" % (kural if kural else "BULUNAMADI"))
    dogrula("C2 DAR EKRANDA CIP SATIRI YATAY KAYDIRILIR (overflow-x)",
            bool(kural) and kural.get("overflow-x") in ("auto", "scroll"),
            "overflow-x=%s" % (kural.get("overflow-x") if kural else "-"))
    dogrula("C3 CIPLER KUCULMEZ (flex:0 0 auto) — kaydirma yerine sikismasin",
            bool(re.search(r"@media\(max-width:640px\)\{.*?\.brand-chips > \*\{\s*flex:0 0 auto;",
                           index_metni, re.S)), "")
    dogrula("C4 SECILI CIP GORUNUR KILINIR (scrollIntoView, uc satirda da)",
            index_metni.count("seciliCipiGorunurKil(el);") >= 3,
            "cagri=%d" % index_metni.count("seciliCipiGorunurKil(el);"))

    # --- D) ARAMA METNI (hs) DEGISMEDI --------------------------------------
    # Marka/model arama metnine EKLENIRSE site<->Ege paritesi SESSIZCE ayrisir.
    hs = re.search(r"p\._hs = norm\(\[(.*?)\]\.join", index_metni, re.S)
    dogrula("D1 ARAMA METNINE (hs) MODEL EKLENMEDI",
            bool(hs) and "uyum" not in hs.group(1) and "activeModel" not in hs.group(1),
            (hs.group(1).strip().replace("\n", " ")[:110] if hs else "hs BULUNAMADI"))

    # --- E..) DAVRANIS KOSUMU (node) ----------------------------------------
    kat = fikstur()
    fix = ci.indeks_uret(kat, index_metni)
    print("  FIKSTUR: %d urun -> %d kategori · %d marka · %d model"
          % (len(kat), len(fix["kat"]),
             sum(len(v) for v in fix["kat"].values()),
             sum(len(x["m"]) for v in fix["kat"].values() for x in v.values())))
    # Fikstur INDEKSI beklenen sekilde mi (kosum iddialarinin on-kosulu)?
    oto = fix["kat"].get("Otomobil", {})
    # Beklenen: markalar {BMW, Ford} (Opel <15 -> YOK) · BMW modelleri {E46, E36}
    # (E60 2 urun -> ESIK_MODEL altinda, cip DEGIL) · Ford 0 model (tek gecerli model
    # Focus -> EN_AZ_MODEL sartini gecmez).
    dogrula("E0 FIKSTUR INDEKSI BEKLENEN SEKILDE (BMW E46+E36, E60 esik alti, Ford 0, Opel yok)",
            set(oto.keys()) == {"BMW", "Ford"} and
            set(oto.get("BMW", {}).get("m", {})) == {"E46", "E36"} and
            oto.get("Ford", {}).get("m") == {},
            "markalar=%s BMW modelleri=%s" % (sorted(oto), sorted(oto.get("BMW", {}).get("m", {}))))
    # UC ETIKETI — POZITIF ve KONTROL ekseni AYNI fiksturde (tek yon = olu nobetci).
    mar = fix["kat"].get("Marin", {})
    dogrula("E0b FIKSTUR UC ETIKETI: katlanmis cipte `e` DOGAR, kanonik=ham olanda DOGMAZ",
            mar.get("Volvo", {}).get("e") == "Volvo Penta" and
            "e" not in mar.get("Mercury", {}) and "e" not in mar.get("Yamaha", {}),
            "Volvo.e=%s Mercury.e=%s Yamaha.e=%s"
            % (mar.get("Volvo", {}).get("e"), mar.get("Mercury", {}).get("e"),
               mar.get("Yamaha", {}).get("e")))
    # KURATORLUK KAPSAM ESIGI — POZITIF + KONTROL ayni fiksturde, tek yon YETMEZ.
    fkaps = ci.uyum_kapsami(kat)
    dogrula("E0c FIKSTUR KAPSAMI BEKLENEN (Marin gevsek, Otomobil kuratorlu)",
            fkaps.get("Marin", 1.0) < ci.ESIK_UYUM_KAPSAM
            and fkaps.get("Otomobil", 0.0) >= ci.ESIK_UYUM_KAPSAM,
            "Marin=%.0f%% Otomobil=%.0f%% esik=%.0f%%"
            % (100 * fkaps.get("Marin", 0), 100 * fkaps.get("Otomobil", 0),
               100 * ci.ESIK_UYUM_KAPSAM))
    dogrula("E0d GEVSEK KATEGORIDE TANINMAYAN URETICI CIP OLUR (Marin/Teleflex 15)",
            "Teleflex" in mar and mar.get("Teleflex", {}).get("n") == 15,
            "Marin cipleri=%s" % sorted(mar))
    dogrula("E0e KONTROL: KURATORLU KATEGORIDE TANINMAYAN URETICI CIP OLMAZ (Otomobil/Denso 16)",
            "Denso" not in oto,
            "Otomobil cipleri=%s (Denso yerel sayim=%d)"
            % (sorted(oto), len([u for u in kat if u["kategori"] == "Otomobil"
                                 and "Denso" in u["marka"]])))

    fd1, kat_yol = tempfile.mkstemp(prefix="pruvo-cip-katalog-", suffix=".json")
    with os.fdopen(fd1, "w", encoding="utf-8") as f:
        json.dump(kat, f, ensure_ascii=False)
    fd2, ix_yol = tempfile.mkstemp(prefix="pruvo-cip-indeks-", suffix=".json")
    with os.fdopen(fd2, "w", encoding="utf-8") as f:
        json.dump(fix, f, ensure_ascii=False)
    try:
        p = subprocess.run(["node", os.path.join(kok, "tools", "cip-indeks-kosum.js"),
                            "--kok", kok, "--katalog", kat_yol, "--indeks", ix_yol],
                           capture_output=True, text=True)
    finally:
        os.unlink(kat_yol)
        os.unlink(ix_yol)

    if p.returncode != 0 or not p.stdout.strip():
        print("  KALDI KOSUM CALISTIRILAMADI — rc=%d" % p.returncode)
        print("     " + ((p.stderr or "").strip().splitlines() or [""])[-1][:400])
        return 1
    try:
        sonuc = json.loads(p.stdout)
    except ValueError as e:
        print("  KALDI KOSUM CIKTISI COZULEMEDI — %s" % e)
        return 1

    iddialar = sonuc.get("iddialar", [])
    for it in iddialar:
        dogrula(it["ad"], it["gecti"], it.get("detay", ""))

    dogrula("Z IDDIA SAYISI SOZLESMESI (== %d)" % BEKLENEN_IDDIA,
            len(iddialar) == BEKLENEN_IDDIA, "kosan=%d" % len(iddialar))

    toplam = len(gecen) + len(kaldi)
    if kaldi:
        print("\nSONUC: %d/%d iddia KALDI" % (len(kaldi), toplam))
        return 1
    print("\nSONUC: %d/%d iddia GECTI ✔" % (toplam, toplam))
    return 0


# ---------------------------------------------------------------- MUTASYON
# (dosya, eski, yeni, beklenen, aciklama)
MUTANTLAR = [
    # NOT (3 Agu): iki capa TASINDI — model yuklemi `modelEsler()`e bagli tek kaynak oldu
    # (bkz. tools/model-uyelik-kapisi.py). Mutantin ANLATTIGI ihlal AYNI; "capa bayat"
    # gozlemi kanit degildir, o yuzden capalar guncellendi.
    ("index.html",
     'var modelOk = activeModel === "Tümü" ||\n        modelEsler(p.marka, activeModel, hedefMarka);',
     'var modelOk = true;', "KIRMIZI",
     "MODEL FILTRESINI KALDIR (yerel): cip tiklanir, liste DEGISMEZ"),
    ("index.html",
     '    if(activeModel !== "Tümü"){ p.set("model", activeModel); }',
     '    if(false){ p.set("model", activeModel); }', "KIRMIZI",
     "EDGE MODEL PARAMETRESINI DUSUR: Worker suzmez, canlida liste daralmaz"),
    ("index.html", '    if(mdl){ activeModel = mdl; }', '    if(false){ activeModel = mdl; }',
     "KIRMIZI", "URL OKUMASINI KALDIR: paylasilan link model secimini tasimaz"),
    ("index.html",
     'if(activeModel !== "Tümü"){ params.set("model", activeModel); }',
     'if(false){ params.set("model", activeModel); }', "KIRMIZI",
     "URL YAZMAYI KALDIR: secim paylasilamaz, round-trip kirilir"),
    ("index.html",
     '    var ixMarka = indeksMarkalar(activeCat, activeAlt, "Tümü");\n    if(ixMarka){',
     '    var ixMarka = indeksMarkalar(activeCat, activeAlt, "Tümü");\n    if(false){',
     "KIRMIZI",
     "MARKA SATIRINDA CAPRAZ DARALMAYI KALDIR: Bujiler'de bos markalar geri gelir (olu uc)"),
    ("index.html",
     '    var ixGrup = indeksGruplar(activeCat, activeBrand, activeModel);\n    if(ixGrup){',
     '    var ixGrup = indeksGruplar(activeCat, activeBrand, activeModel);\n    if(false){',
     "KIRMIZI",
     "GRUP SATIRINDA CAPRAZ DARALMAYI KALDIR: markada urunu olmayan grup gosterilir"),
    ("index.html",
     '      liste = liste.filter(function(a){ return (ixGrup[a] || 0) > 0; });',
     '      liste = liste.filter(function(a){ return (ixGrup[a] || 0) > 0 && (activeAlt === "Tümü" || a === activeAlt); });',
     "KIRMIZI",
     "SATIR KENDI SECIMIYLE DE DARALSIN: kullanici baska gruba GECEMEZ"),
    ("index.html",
     '    if(secili !== "Tümü" && liste.indexOf(secili) === -1){ return liste.concat([secili]); }',
     '    if(false){ return liste.concat([secili]); }', "KIRMIZI",
     "SECILI CIPI GIZLE: daralmada dusen secim geri alinamaz"),
    ("index.html",
     '        var sapan = edgeSuzgecSapmasi(d.urunler || []);',
     '        var sapan = null;', "KIRMIZI",
     "FAIL-OPEN: uc suzmediyse liste SESSIZCE kabul edilir (musteri yanlis liste gorur)"),
    ("index.html",
     '        if(activeModel !== "Tümü" && !modelEsler(mk, activeModel, hedefMarka)){ return "model"; }',
     '        if(false){ return "model"; }', "KIRMIZI",
     "GUARD'IN MODEL EKSENINI KALDIR: yalniz marka dogrulanir, model fail-open kalir"),
    ("index.html",
     '      modelRowEl.style.display =\n        (activeCat !== "Tümü" && activeBrand !== "Tümü" && modelSatiriVar()) ? "" : "none";',
     '      modelRowEl.style.display = (activeCat !== "Tümü") ? "" : "none";', "KIRMIZI",
     "MODEL SATIRINI HER KATEGORIDE GOSTER: marka secili degilken BOS KUTU"),
    ("index.html", '      overflow-x:auto;', '      overflow-x:visible;', "KIRMIZI",
     "MOBIL KAYDIRMAYI KALDIR: 18 cip yine 8 satira sarar, ilk kart ekran disina duser"),
    ("index.html", '    .brand-chips{\n      flex-wrap:nowrap;', '    .brand-chips{\n      flex-wrap:wrap;',
     "KIRMIZI", "MOBIL TEK SATIRI KALDIR: sarma geri gelir"),
    ("cip-indeks.py", "ESIK_MARKA = 15", "ESIK_MARKA = 1", "KIRMIZI",
     "MARKA ESIGINI KALDIR: <15 urunlu kuyruk marka cip olur (bos ikili orani %58,7'ye ciker)"),
    ("cip-indeks.py", "EN_AZ_MODEL = 2", "EN_AZ_MODEL = 1", "KIRMIZI",
     "TEK MODELLI MARKADA DA MODEL SATIRI: anlamsiz tek-cipli satir dogar"),
    ("cip-indeks.py", "ESIK_MODEL = 3", "ESIK_MODEL = 1", "KIRMIZI",
     "MODEL ESIGINI KALDIR: 1-2 urunlu model cipleri (Otomobil'de %76,5'i <5 urun)"),
    ("index.html",
     '        if(Object.prototype.toString.call(mk) !== "[object Array]"){\n          return "olculemedi";           // kart marka taşımıyor → doğrulanamaz\n        }',
     '        mk = mk || [];   // olculemedi dali kaldirildi', "KIRMIZI",
     "'OLCEMEDIM'I YESIL SAY: kart marka tasimazsa dogrulama atlanir, fail-open acilir"),
    # --- UC MARKA ETIKETI EKSENI (cip KATLANMIS <-> uc HAM) -----------------
    ("index.html",
     '    if(activeBrand !== "Tümü"){ p.set("marka", ucMarkaEtiketi(activeCat, activeBrand)); }',
     '    if(activeBrand !== "Tümü"){ p.set("marka", activeBrand); }', "KIRMIZI",
     "ISTEMCI KANONIGI GONDERSIN: uc katlamaz -> gorunen cip 0 urun (olculen canli hata)"),
    ("cip-indeks.py",
     "    if not hamlar or kanonik in hamlar:\n        return None",
     "    return None", "KIRMIZI",
     "UC ETIKETINI URETME: `e` hic dogmaz, katlanmis cip yine olu uc olur"),
    ("cip-indeks.py",
     '            e = uc_etiketi(kat_marka_ham.get((kat, mk), {}), mk)\n            if e is not None:',
     '            e = uc_etiketi(kat_marka_ham.get((kat, mk), {}), mk)\n            if False:',
     "KIRMIZI",
     "ETIKETI INDEKSE YAZMA: uretec dogru hesaplar, istemciye HIC ulasmaz (kablolama kopar)"),
    ("cip-indeks.py",
     "    if not hamlar or kanonik in hamlar:\n        return None\n    return sorted(hamlar.items(), key=lambda t: (-t[1], t[0]))[0][0]",
     "    if not hamlar:\n        return None\n    return sorted(hamlar.items(), key=lambda t: (-t[1], t[0]))[0][0]",
     "KIRMIZI",
     "HER MARKAYA `e` YAZ: kanonik=ham olanda da alan dogar (gereksiz bayt + kontrol ekseni duser)"),
    # --- KURATORLUK KAPSAM ESIGI EKSENI (ESIK_UYUM_KAPSAM) -------------------
    ("cip-indeks.py", "ESIK_UYUM_KAPSAM = 0.50", "ESIK_UYUM_KAPSAM = 1.01", "KIRMIZI",
     "ESIGI TAVANA CEK: HER kategori gevser -> arac kategorilerinde model kodlari cip olur"),
    ("cip-indeks.py", "ESIK_UYUM_KAPSAM = 0.50", "ESIK_UYUM_KAPSAM = 0.0", "KIRMIZI",
     "ESIGI TABANA CEK: hicbir kategori gevsemez -> Marin uretici cipleri geri kaybolur"),
    ("cip-indeks.py",
     "        if (evren.taninmis_mi(kan) or not kuratorluk) and kan not in out:",
     "        if evren.taninmis_mi(kan) and kan not in out:", "KIRMIZI",
     "KURATORLUGU HER ZAMAN UYGULA: kapsam kolu OLU kalir (bugunku hataya geri donus)"),
    ("cip-indeks.py",
     "    return dict((k, v >= ESIK_UYUM_KAPSAM) for k, v in uyum_kapsami(urunler).items())",
     "    return dict((k, False) for k, v in uyum_kapsami(urunler).items())", "KIRMIZI",
     "KURATORLUGU HER YERDE KALDIR: Otomobil'de tanınmayan deger cip olur (sisme)"),
    # --- KONTROL MUTANTLARI (YESIL bekleniyor) — iddialar ILGISIZ degisikliklere
    # PINLENMIS mi? Yesil kalmazlarsa kapi asiri-baglanmistir ([[kapi-kapsam-eksen-secimi]]).
    ("index.html", '.brand-btn:hover{border-color:var(--navy-2)}',
     '.brand-btn:hover{border-color:var(--gray-line)}', "YESIL",
     "ILGISIZ: cip hover rengi — davranisa DOKUNMAZ"),
    ("index.html", 'var PAGE_SIZE = 24;', 'var PAGE_SIZE = 12;', "YESIL",
     "ILGISIZ: sayfa boyu — iddialar sayfalama sabitine PINLENMEMELI"),
    ("cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "ILGISIZ: indeks surum alani — cip davranisina DOKUNMAZ"),
]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _hedef(tmp, dosya):
    return os.path.join(tmp, "tools", dosya) if dosya.endswith(".py") \
        else os.path.join(tmp, dosya)


def _kopya_kur():
    """index.html + tools/ KOPYALANIR (mutant oraya yazilir), kalani SYMLINK."""
    tmp = tempfile.mkdtemp(prefix="pruvo-cip-indeks-mut-")
    shutil.copytree(os.path.join(GERCEK_KOK, "tools"), os.path.join(tmp, "tools"))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git", ".claude"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                          capture_output=True, text=True)


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    izlenen = [os.path.join(GERCEK_KOK, "index.html"),
               os.path.join(GERCEK_KOK, "tools", "cip-indeks.py"),
               os.path.join(GERCEK_KOK, "tools", "cip-indeks-kosum.js"),
               os.path.join(GERCEK_KOK, "urunler.json")]
    once = {y: _sha(y) for y in izlenen}
    basarisiz = []

    # M00 MUTASYONSUZ KONTROL — harness saglam mi (yoksa tum KIRMIZI'lar YALANCI).
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s"
          % ("OK  " if p0.returncode == 0 else "HATA",
             "YESIL" if p0.returncode == 0 else "KIRMIZI"))
    if p0.returncode != 0:
        for s in (p0.stdout or "").splitlines():
            if s.strip().startswith("KALDI"):
                print("     " + s.strip()[:200])
        print("     " + ((p0.stderr or "").strip().splitlines() or [""])[-1][:300])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)

    uygulanan = 0
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = _kopya_kur()
        hedef = _hedef(tmp, dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        sayi = metin.count(eski)
        # 🔴 CAPA KAYMASI = KIRMIZI, "gecti" DEGIL: eslesmeyen capa o ekseni OLCMEMISTIR.
        if sayi != 1:
            basarisiz.append("M%02d CAPA BAYAT (%d eslesme) %s" % (i, sayi, dosya))
            print("  HATA M%02d [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, sayi, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni, 1))
        uygulanan += 1
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        if goruldu != beklenen:
            basarisiz.append("M%02d %s: beklenen %s, goruldu %s" % (i, dosya, beklenen, goruldu))
        # 🔴 KIRMIZI YETMEZ, ADLI IDDIA SART: mutant COKEREK de rc!=0 verebilir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("M%02d %s: KIRMIZI ama HICBIR iddia KALDI demedi (cokme)" % (i, dosya))
        print("  %s M%02d [%s] %s -> %s (%d iddia kirmizi) | %s"
              % ("OK  " if goruldu == beklenen else "HATA", i, beklenen, dosya, goruldu,
                 len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:170])
        shutil.rmtree(tmp, ignore_errors=True)

    sonra = {y: _sha(y) for y in izlenen}
    bozuk = [os.path.basename(y) for y in once if once[y] != sonra[y]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    print("  MUTANT FIILEN UYGULANDI: %d/%d" % (uygulanan, len(MUTANTLAR)))
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK, help="agac (mutasyon kopyasi icin)")
    ap.add_argument("--mutasyon", action="store_true", help="cift yonlu mutasyon (elle)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== CIP SATIRLARI (MARKA · GRUP · MODEL) KAPISI (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())
