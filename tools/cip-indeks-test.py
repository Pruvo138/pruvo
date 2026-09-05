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

# === 27 AGU 2026 (K328) — M3-B ZENGINLESTIRME CIVISI: SAYI DEGIL AD ==============
# 🔴 SAYI BIR ANLIK GORUNTUDUR, AD BIR IDDIADIR. Bugun ayni depoda bunun bedeli
# olculdu: `shop/test/uretim-kaynak.mjs` yetki yuzeyini SAYIYLA civilemisti
# (`KOL_TABANI = 10`); 24 Agu'da mesru bir uc eklenince (`POST /yonet/havale-onay`)
# civi bayatladi ve yetki-yuzeyi nobetcisi UC GUN hic hukum vermedi. Ayni hata burada
# tekrarlanmasin: `cip \ sayfa` farkinin BUYUKLUGU degil, HANGI KOVALARDA oldugu civili.
# Kumeye YENI bir ad girerse KIRMIZI (yeni bir ayrisma dogdu, hukum gerekir);
# kumeden bir ad DUSERSE de KIRMIZI (civi bayatladi ya da davranis sessizce degisti).
#
# BUGUNKU TEK UYE — olculdu (761 dugum, replikasyon kapiyla BIREBIR):
#   ('Otomobil', 'Citroen', 'ami') -> citroen-ami-6-i-ayd-nlatma-anahtar-par-as
#   `Ami` (2020 EV) ile `Ami 6` (1960'lar) KARDES MODEL; urunun kendi jeton kovasi
#   `ami6`, ama cipin BASLIK kolu basliktaki "Ami"yi tam kelime yakalayip onu `ami`
#   kovasina da yaziyor. Sayfa ureticisi yazmiyor. Bu bir ONTOLOJI sorusudur (kardes
#   model ↔ sasi kodu/pazarlama adi ayrimi) ve mekanik kuralla cozulemez — o yuzden
#   ONARILMADI, CIVILENDI: buyurse gorunur olsun.
M3_ZENGIN_CIVI = frozenset({("Otomobil", "Citroen", "ami")})


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
    d1 = _modul(os.path.join(kok, "tools", "d1-sync.py"), "d1_sync_cip_kabul")
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_metni = f.read()

    # --- A) GERCEK KATALOG: indeks esikleri + SIFIR kombinasyon YOK -----------
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        gercek = json.load(f)
    # K328: cip UYELIK kovasi — sayan kolun KENDISI doldurur (ikinci turetim YOK).
    cip_uyelik = {}
    ix = ci.indeks_uret(gercek, index_metni, uyelik=cip_uyelik)
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

    # --- G) BISIKLET MARKA EKSENI (Okan emri 5 Eyl: "farkli markalari da ekle") ----
    # OLCULEN ENGEL BEYAZ LISTE DEGIL, VERIYDI: Bisiklet'te `uyum` kapsami 0,0046 —
    # ESIK_UYUM_KAPSAM'in (0,50) COK altinda, yani TANINMIS_MARKALAR kuratorlugu bu
    # kategoride ZATEN uygulanmiyor; listeye marka eklemek Bisiklet'te HICBIR SEY
    # degistirmezdi. Gercek eksik `marka` alaniydi: 2.618 urunun yalniz 27'sinde (%1,0)
    # doluydu ve esigi gecen TEK deger `Yamaha` 18 idi -> kategoride 1 marka cipi.
    # BASLIK ekseninde esigi gecen ama `marka`ya YAZILMAMIS gercek markalar olculdu
    # (Garmin 68 · GoPro 67 · Samsung 20 · Shimano 17) ve TAM JETON eslesmesiyle
    # (arama.nrm -> bosluga bol -> kume uyeligi) 167 urune backfill edildi.
    #
    # 🔴 G3/G4 ALT-DIZE KOLUDUR, SUS PAYI DEGIL: ayni backfill ALT DIZE ile yapilsaydi
    # `Mini` 17 urunle esigi gecer ve Bisiklet'te bir marka cipi DOGARDI — oysa oradaki
    # "mini" bir SIFATTIR ("mini pompa", "iPad Mini", "Supernova M99 Mini Pro",
    # "Xiaomi Mini Hoparlor"), araba markasi DEGIL. G3 cip duzeyinde, G4 URUN duzeyinde
    # (NON-GROWTH) olcer: G4 esigin ALTINDA kalan sizintiyi da yakar.
    BISIKLET_MARKA_TABANI = ["Garmin", "GoPro", "Samsung", "Shimano", "Yamaha"]
    bis_cip = ix["kat"].get("Bisiklet", {})
    eksik_bis = [m for m in BISIKLET_MARKA_TABANI if m not in bis_cip]
    dogrula("G1 BISIKLET MARKA CIPI >= %d (taban kume EKSIKSIZ)" % len(BISIKLET_MARKA_TABANI),
            not eksik_bis and len(bis_cip) >= len(BISIKLET_MARKA_TABANI),
            "cip=%d eksik=%s -> %s"
            % (len(bis_cip), eksik_bis or "YOK",
               sorted(((k, v["n"]) for k, v in bis_cip.items()), key=lambda t: -t[1])))
    bis_esik_alti = ["%s=%d" % (m, bis_cip[m]["n"]) for m in BISIKLET_MARKA_TABANI
                     if m in bis_cip and bis_cip[m]["n"] < ci.ESIK_MARKA]
    dogrula("G2 TABAN KUMESININ HER CIPI >= %d URUN TASIYOR" % ci.ESIK_MARKA,
            not bis_esik_alti, "esik alti=%s" % (bis_esik_alti or "YOK"))
    dogrula("G3 `Mini` BISIKLET MARKA CIPI DEGIL (alt-dize eslesmesi kolu)",
            "Mini" not in bis_cip,
            "Bisiklet cipleri=%s" % sorted(bis_cip.keys()))
    bis_mini_urun = [u.get("id") for u in gercek
                     if (u.get("kategori") or "").strip() == "Bisiklet"
                     and any((x or "").strip().lower() == "mini"
                             for x in (u.get("marka") or []))]
    dogrula("G4 NON-GROWTH: BISIKLET'TE HICBIR URUN `marka`da `Mini` TASIMAZ",
            not bis_mini_urun,
            "tasiyan=%d %s" % (len(bis_mini_urun), bis_mini_urun[:3]))

    # --- A6/A7) UC MARKA ETIKETI: gorunen cip UCTA da >0 olmali -------------
    # 🔴 UC YUKLEMI ELLE YAZILMAZ. Worker artik D1 `marka_kanon` uyeligini okur;
    # ayna da AYNI hedefi ureten d1-sync.marka_kanon_haritasi()ndan turer. Ham `marka[]`
    # esitligini burada yeniden yazmak, uretim kanonige tasindigi halde aynayi bayat
    # birakirdi ([[ikiz-tanim-sessiz-ayrisma]]; 12 Agu'da olculen regresyon).
    marka_kanon, marka_kanon_sebep = d1.marka_kanon_haritasi(gercek)
    if marka_kanon_sebep:
        print("  KALDI A6 UC MARKA KANONU TURETILEMEDI — %s" % marka_kanon_sebep)
        return 1
    kanon_sayim = {}   # (kat, KANONIK etiket) -> n (D1 marka_kanon hedefinin aynisi)
    for u in gercek:
        k = (u.get("kategori") or "").strip()
        for kan in set(json.loads(marka_kanon.get(u.get("id"), "[]"))):
            kanon_sayim[(k, kan)] = kanon_sayim.get((k, kan), 0) + 1
    olu, sapan = [], []
    for kat, kd in ix["kat"].items():
        for mk, d in kd.items():
            etiket = mk                       # istemcinin gonderecegi kanonik etiket
            n = kanon_sayim.get((kat, etiket), 0)
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

    # --- M) MODEL CIPI KANONIKLESTIRME EKSENI (4 Agu) -----------------------
    # OLCULEN CANLI HATA (Okan ana sayfada gordu): model cipleri HAM jetondu; sayfa
    # ureticisinin kanoniklestirmesi CIP SATIRINA UYGULANMIYORDU. Peugeot secili iken satir
    # `206` ile `Peugeot 206`yi AYRI AYRI, `PSA` ve `iPhone`u MODEL diye, `DS`i (bagimsiz
    # marque) ve `Berlingo`yu (Citroen rozeti) Peugeot MODELI diye gosteriyordu.
    # OLCULDU (17.914 urun): 5 mukerrer grup · 12 model-olmayan cip · 479 cipin 73'unde
    # cip sayisi ile SAYFA sayisi FARKLI (cip 206 -> 52, sayfa 206 -> 58).
    #
    # 🔴 IDDIA GERCEK KATALOG UZERINDE KURULUR (fikstur uzerinde DEGIL): kusur veriden
    # dogdu; kucuk fiksture tasinsaydi mutantlar veriye degil fikstore nisan alirdi.
    # 🔴 KARSILASTIRMA TARAFI SAYFA URETECIDIR (marka_model_build) — ikinci bir "dogru sayi"
    # formulu YAZILMAZ; iki taraf ayrisirsa MUSTERI iki farkli sayi gorur.
    mmb = _modul(os.path.join(kok, "tools", "marka_model_build.py"), "mmb_cip_kabul")
    mevren = mmb.MarkaEvreni(index_metni)
    # `cip_evreni_markalari` CAGRILMAZ: o fonksiyon indeksi BIR KEZ DAHA uretirdi (olculdu:
    # +18 sn). Dondurdugu deger ZATEN elimizdeki indeksin marka kumesidir — ayni tanim,
    # ikinci kosum yok (kaynak yine indeks; ikinci bir kural YAZILMADI).
    _ek = set(b for kd in ix["kat"].values() for b in kd)
    _veri = mmb.gruplandir(gercek, mevren, _ek)
    sayfa_kova = {}     # (marka, canon) -> {kategori: {urun id}}
    sayfa_yayim = set()
    for _marka, _d in _veri.items():
        for _canon, _g in _d["gruplar"].items():
            _kats = {}
            for _p in _g["urunler"]:
                _kats.setdefault((_p.get("kategori") or "").strip(), set()).add(_p.get("id"))
            sayfa_kova[(_marka, _canon)] = _kats
            if mmb.yayimlanir_mi(_g):
                sayfa_yayim.add((_marka, _canon))
    marka_sayfa_ids = {}
    for _marka, _d in _veri.items():
        _ids = set()
        for _g in _d["gruplar"].values():
            _ids |= set(_p.get("id") for _p in _g["urunler"])
        _ids |= set(_p.get("id") for _p in (_d["marka_only"] + _d.get("ikincil", [])))
        marka_sayfa_ids[_marka] = _ids

    mukerrer, jeton_ihlal, sayfasiz = [], [], []
    kayip_uye, zengin_kova = [], set()          # K328: KOL A bulgulari · KOL B kovalari
    cip_canon = {}      # (kat, marka) -> {canon: cip adi}
    for kat, kd in ix["kat"].items():
        for mk, d in kd.items():
            gorulen = cip_canon.setdefault((kat, mk), {})
            for md, y in d["m"].items():
                canon = mevren.model_anahtari(mk, md)
                if not canon:
                    jeton_ihlal.append("%s/%s/%s: anahtar BOS" % (kat, mk, md))
                    continue
                if canon in gorulen:
                    mukerrer.append("%s/%s: '%s' + '%s' -> %s"
                                    % (kat, mk, gorulen[canon], md, canon))
                gorulen[canon] = md
                # (b)/(c) sinifi: marka jetonu · model-olmayan cift · rozet disi cift
                if mmb.marka_jetonu_mu(md, mevren):
                    jeton_ihlal.append("%s/%s/%s: MARKA/grup jetonu" % (kat, mk, md))
                if mmb.model_olmayan_cift_mi(mk, md):
                    jeton_ihlal.append("%s/%s/%s: MODEL OLMAYAN cift" % (kat, mk, md))
                if (mk, canon) in mmb.ROZET_DISI:
                    jeton_ihlal.append("%s/%s/%s: ROZET DISI cift" % (kat, mk, md))
                # (d) sinifi: KAPSAMA (K328). Eski iddia `cip_n == sayfa_n` idi ve
                # TABAN OLARAK YANLISTI — asagidaki M3 blogunun basindaki gerekceye bak.
                _kats = sayfa_kova.get((mk, canon))
                _sayfa_ids = set(_kats.get(kat, ())) if _kats else set()
                _cip_ids = cip_uyelik.get((kat, mk, canon), set())
                if _sayfa_ids - _cip_ids:                       # KOL A — musteri guvencesi
                    kayip_uye.append("%s/%s/%s: sayfada VAR cipte YOK -> %s"
                                     % (kat, mk, md, sorted(_sayfa_ids - _cip_ids)))
                if _cip_ids - _sayfa_ids:                       # KOL B — zenginlestirme
                    zengin_kova.add((kat, mk, canon))
                if (mk, canon) not in sayfa_yayim:
                    sayfasiz.append("%s/%s/%s" % (kat, mk, md))
    dogrula("M1 MODEL CIPI MUKERRER YOK (ayni kanonik degere iki cip dusmez)",
            not mukerrer, "model=%d mukerrer=%d %s"
            % (toplam_model, len(mukerrer), mukerrer[:3]))
    dogrula("M2 MODEL CIPI MODEL-OLMAYAN JETON TASIMAZ (marka/grup/rozet elenmis)",
            not jeton_ihlal, "ihlal=%d %s" % (len(jeton_ihlal), jeton_ihlal[:3]))
    # === 27 AGU 2026 (K328) — M3 ARTIK IKI KOLLU KAPSAMA (eski `==` KALDIRILDI) ======
    # 🔴 ESKI IDDIA TABAN OLARAK YANLISTI: `cip_n == sayfa_n`. Cip uyeligi IKI koldan
    # dogar (jeton ∪ BASLIK), sayfa ureticisi KENDI kuralindan; ikisi 433 kovada
    # 2211 uyelikte BILEREK ayrisir ve o ayrisma MESRUDUR (olculdu 27 Agu:
    # `w204`->`cclass`, `w639`->`vito|viano`, `w169`->`aclass` — sasi kodu ↔ pazarlama
    # adi zenginlestirmesi). Boyle bir yerde `==` iddia etmek, kapinin 761 dugumun
    # 760'inda SANS ESERI yesil yanmasi demekti; yesilligi sansa bagli kapi kapi degildir.
    # 🔴 YENI IDDIA ESKISINDEN GUCLUDUR, GEVSETME DEGIL: `==` tek bir sayiyi kiyasliyordu;
    # KOL A + KOL B birlikte UYE KUMESINI iki yonden birden baglar.
    #   KOL A (MUSTERI GUVENCESI): `sayfa \ cip` BOS olmali. Bos degilse sayfada gorunen
    #     bir urun cip suzgecinde KAYBOLUYOR demektir — gercek zarar, KIRMIZI.
    #     Olculdu 27 Agu: 761 dugumun 761'inde BOS.
    #   KOL B (ZENGINLESTIRME MUHASEBESI): `cip \ sayfa` farki AD KUMESIYLE civilenir,
    #     SAYIYLA degil. Sayi bir anlik goruntudur; ad kumesi degisince KIRMIZI yanar.
    #     Bugunku tek uye: ('Otomobil','Citroen','ami') — `Ami` ile `Ami 6` KARDES MODEL
    #     ve cipin BASLIK kolu "Ami"yi tam kelime yakaliyor. Kume BUYURSE hukum gerekir.
    # Sinir: bu tur YALNIZ IDDIAYI degistirdi; `cip-indeks.py`nin katlama koluna ve
    # `urunler.json`a DOKUNULMADI.
    dogrula("M3-A KAPSAMA: sayfada VAR olan her urun CIPTE DE VAR (musteri guvencesi)",
            not kayip_uye, "model=%d kayip_kova=%d %s"
            % (toplam_model, len(kayip_uye), kayip_uye[:3]))
    _zengin_fazla = sorted(zengin_kova - M3_ZENGIN_CIVI)
    _zengin_eksik = sorted(M3_ZENGIN_CIVI - zengin_kova)
    dogrula("M3-B ZENGINLESTIRME KUMESI CIVILI (ad ile, sayi ile DEGIL)",
            not _zengin_fazla and not _zengin_eksik,
            "civi=%d olculen=%d YENI=%s KAYBOLAN=%s"
            % (len(M3_ZENGIN_CIVI), len(zengin_kova), _zengin_fazla, _zengin_eksik))
    # 🔴 M3-B NOBETI — MUTASYON BATARYASINDA DEGIL, BURADA (sebep: `_kok_kostur` CANLI
    # test dosyasini kosturdugu icin testin KENDI sabitine mutant uygulanamiyor; K328②/③
    # bu yuzden KALDIRILDI). Iddia IKI YONLU ve civinin YUK TASIDIGINI olcer:
    #   (a) olculen kume BOS OLMAMALI — bos olsaydi `{ami}` civisi ile bos olcum
    #       birbirini goturur ve M3-B "yesil" gorunurken hicbir sey baglamazdi;
    #   (b) civi BOSALTILSA hukum KIRMIZI olurdu (`zengin_kova - frozenset()` dolu).
    # Ikisi ayni olguyu iki yonden yazar: `zengin_kova` bugun DOLU, o yuzden civi canli.
    dogrula("M3-B NOBET: civi YUK TASIYOR (olculen kume BOS DEGIL; bosaltilsa KIRMIZI)",
            bool(zengin_kova) and bool(zengin_kova - frozenset()),
            "olculen=%d ornek=%s" % (len(zengin_kova), sorted(zengin_kova)[:2]))
    dogrula("M4 HER MODEL CIPININ YAYIMLANAN SAYFASI VAR (olu cip yok)",
            not sayfasiz, "sayfasiz=%d %s" % (len(sayfasiz), sayfasiz[:3]))

    # M9 — CIP ETIKETI == SAYFA DISPLAY'I (TEK KAYNAK; 4 Agu, kararsiz jeton SINIF 1).
    # cip-indeks modul docstring'i "CIP ETIKETI = sayfa basligiyla AYNI kanonik gosterim
    # (tek kaynak, ikinci secim YOK)" DIYORDU ama hicbir iddia bunu OLCMUYORDU: M3 yalniz
    # SAYIYI karsilastiriyor, M1 yalniz mukerrer canon'a bakiyor. Iki taraf ETIKETTE
    # ayrissaydi musteri ana sayfada bir ad, sayfada BASKA bir ad gorurdu ve cipin urettigi
    # `?model=<etiket>` istegi de o adla giderdi ([[ikiz-tanim-sessiz-ayrisma]]).
    # 🔴 SINIF 1 BAGI: `K`/`K Serisi` gibi CIPLAK-TEK-HARF ailelerinde ad, kuratorlu
    # gosterim zorlamasindan gelir (marka_model_build._KANONIK_GOSTERIM); zorlama yalniz BIR
    # tarafta uygulansaydi cip "K", sayfa "K Serisi" derdi. Bu iddia o ayrismayi olcer.
    etiket_sapan = []
    for kat, kd in ix["kat"].items():
        for mk, d in kd.items():
            for md in d["m"]:
                canon = mevren.model_anahtari(mk, md)
                _g = (_veri.get(mk) or {}).get("gruplar", {}).get(canon)
                _dsp = (_g or {}).get("display")
                if _dsp != md:
                    etiket_sapan.append("%s/%s: cip=%r sayfa=%r (canon=%s)"
                                        % (kat, mk, md, _dsp, canon))
    dogrula("M9 CIP ETIKETI == SAYFA DISPLAY'I (kanonik gosterim TEK KAYNAK)",
            not etiket_sapan, "model=%d sapan=%d %s"
            % (toplam_model, len(etiket_sapan), etiket_sapan[:3]))

    # M5 — ASIRI ELEME NOBETI (M2'nin TERS yonu). Marka-KOR bir eleme baska markadaki
    # GERCEK modeli oldururdu (or. "DS" kor elenirse /marka/citroen/ds/ cipi de OLURDU,
    # oysa Citroen DS gercek bir modeldir). Yuklem: YAYIMLANAN + uyum BAGI olan + cip
    # esiklerini gecen her model CIP OLMALI.
    # 🔴 `uyum` BAGI SARTI: cip evreninin sayfa evreninden FAZLADAN bir on kosulu vardir —
    # marka<->model bagini yalniz `uyum` cifti kurar (bkz. cip-indeks modul docstring'i).
    # Bu sart olmadan iddia 66 sahte ihlal basiyordu (or. Citroen/ami: sayfada 15 urun,
    # uyum bagi YOK). Bag BURADA BAGIMSIZ hesaplanir (uretecin `cift` kumesi CAGRILMAZ) ki
    # iddia uretecin kendi tanimini aynalamasin.
    _cip_evreni = ci.MarkaEvreni(index_metni)
    _kuratorlu = ci.kuratorluk_kolu(gercek)
    bagli = set()
    for u in gercek:
        _kat = (u.get("kategori") or "").strip()
        _uyeler = ci.markalari(u, _cip_evreni, kuratorluk=_kuratorlu.get(_kat, True))
        for oge in (u.get("uyum") or []):
            _mk = _cip_evreni.katla((oge.get("marka") or "").strip())
            _md = (oge.get("model") or "").strip()
            if not _md or _mk not in _uyeler:
                continue
            _c = mevren.model_anahtari(_mk, _md)
            if _c:
                bagli.add((_kat, _mk, _c))
    eksik_cip = []
    for (mk, canon) in sayfa_yayim:
        for kat, ids in sayfa_kova[(mk, canon)].items():
            kd = ix["kat"].get(kat) or {}
            if mk not in kd or len(ids) < ci.ESIK_MODEL:
                continue
            if len(kd[mk]["m"]) < ci.EN_AZ_MODEL or (kat, mk, canon) not in bagli:
                continue
            if canon not in cip_canon.get((kat, mk), {}):
                eksik_cip.append("%s/%s/%s (%d urun)" % (kat, mk, canon, len(ids)))
    dogrula("M5 ESIGI GECEN HER YAYIMLANAN MODEL CIP OLUR (asiri eleme yok)",
            not eksik_cip, "eksik=%d %s" % (len(eksik_cip), eksik_cip[:3]))

    # M6 — UC MODEL ETIKETI: uc `model` parametresini `uyum[].model` alaninda suzuyor
    # (olculdu CANLI: model=F-Serisi -> 0 · model=F-Series -> 8). Istemcinin gonderecegi
    # etiket o kategoride uyum[].model olarak GECMELI, yoksa cip OLU UC.
    uyum_sayim = {}
    for u in gercek:
        k = (u.get("kategori") or "").strip()
        for oge in (u.get("uyum") or []):
            md = (oge.get("model") or "").strip()
            if md:
                uyum_sayim[(k, md)] = uyum_sayim.get((k, md), 0) + 1
    olu_model = []
    for kat, kd in ix["kat"].items():
        for mk, d in kd.items():
            for md, y in d["m"].items():
                etiket = y.get("e", md)
                if uyum_sayim.get((kat, etiket), 0) <= 0:
                    olu_model.append("%s/%s/%s->'%s'=0" % (kat, mk, md, etiket))
    dogrula("M6 GORUNEN HER MODEL CIPININ UC ETIKETI KATALOGDA >0 (olu uc YOK)",
            not olu_model, "model=%d olu=%d %s"
            % (toplam_model, len(olu_model), olu_model[:3]))

    # M7 KONTROL — katlama GERCEKTEN is yapiyor mu (dejenere olcum degil): en az bir cip,
    # HAM esitligin sayacagindan DAHA COK urun sayiyor olmali. Bu iddia olmadan "katlamayi
    # tumuyle kaldir" mutanti M1/M3'u de birlikte kaydirip yesil kalabilirdi.
    ham_model_sayim = {}
    for u in gercek:
        k = (u.get("kategori") or "").strip()
        for ham in set((x or "").strip() for x in (u.get("marka") or []) if (x or "").strip()):
            ham_model_sayim[(k, ham)] = ham_model_sayim.get((k, ham), 0) + 1
    katlayan = [(kat, mk, md, y["n"], ham_model_sayim.get((kat, md), 0))
                for kat, kd in ix["kat"].items() for mk, d in kd.items()
                for md, y in d["m"].items() if y["n"] > ham_model_sayim.get((kat, md), 0)]
    dogrula("M7 KONTROL: KATLAMA IS YAPIYOR (ham esitlikten COK sayan cip VAR)",
            len(katlayan) > 0, "katlayan cip=%d ornek=%s" % (len(katlayan), katlayan[:2]))

    # M8 — KABLOLAMA: `e` uretilse de istemci onu GONDERMEZSE cip yine olu uc olur.
    # M6 INDEKSI olcer, bu iddia YOLU olcer (B3'un marka ekseninde yaptiginin aynisi).
    # Davranissal olcum JS kosumunda YAPILAMADI: fikstur Otomobil marka cip listesine yeni
    # bir marka eklemeden bu vakayi tasiyamiyor ve o liste baska 8 iddianin beklenen
    # degerine PINLI. Bu yuzden eksen BURADA kablolama olarak olculur — raporda boyle gecer.
    dogrula("M8 ISTEMCI UCA `e` MODEL ETIKETINI GONDERIR (kablolama)",
            'p.set("model", ucModelEtiketi(activeCat, activeBrand, activeModel));' in index_metni
            and 'function ucModelEtiketi(' in index_metni
            and 'kd[marka].m[model]' in index_metni,
            "edgeIstek -> ucModelEtiketi -> indeks `e`")

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

    # Davranis kosumunun sahte Worker'i de ayni D1 hedefini okur. Harita Python'da
    # URETIM KAYNAGINDAN turetilir; JS tarafinda ikinci bir marka katlama govdesi yoktur.
    fix_marka_kanon, fix_marka_kanon_sebep = d1.marka_kanon_haritasi(kat)
    if fix_marka_kanon_sebep:
        print("  KALDI FIKSTUR UC MARKA KANONU TURETILEMEDI — %s" % fix_marka_kanon_sebep)
        return 1

    fd1, kat_yol = tempfile.mkstemp(prefix="pruvo-cip-katalog-", suffix=".json")
    with os.fdopen(fd1, "w", encoding="utf-8") as f:
        json.dump(kat, f, ensure_ascii=False)
    fd2, ix_yol = tempfile.mkstemp(prefix="pruvo-cip-indeks-", suffix=".json")
    with os.fdopen(fd2, "w", encoding="utf-8") as f:
        json.dump(fix, f, ensure_ascii=False)
    fd3, marka_kanon_yol = tempfile.mkstemp(prefix="pruvo-cip-marka-kanon-", suffix=".json")
    with os.fdopen(fd3, "w", encoding="utf-8") as f:
        json.dump(fix_marka_kanon, f, ensure_ascii=False)
    try:
        p = subprocess.run(["node", os.path.join(kok, "tools", "cip-indeks-kosum.js"),
                            "--kok", kok, "--katalog", kat_yol, "--indeks", ix_yol,
                            "--marka-kanon", marka_kanon_yol],
                           capture_output=True, text=True)
    finally:
        os.unlink(kat_yol)
        os.unlink(ix_yol)
        os.unlink(marka_kanon_yol)

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
     '    if(activeModel !== "Tümü"){\n      p.set("model", ucModelEtiketi(activeCat, activeBrand, activeModel));\n    }',
     '    if(false){\n      p.set("model", ucModelEtiketi(activeCat, activeBrand, activeModel));\n    }',
     "KIRMIZI",
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
    # --- UC MARKA UYELIGI EKSENI (D1 kanonu; ham ayna BAYAT) -----------------
    ("cip-indeks-kosum.js",
     '    if (marka && yoksay !== "marka" &&\n'
     '        (MARKA_KANON[p.id] || []).indexOf(marka) === -1) { return false; }',
     '    if (marka && yoksay !== "marka" && HAM(p).indexOf(marka) === -1) { return false; }',
     "KIRMIZI",
     "EDGE AYNASINI ESKI HAM ESITLIGE DONDUR: kanonik Volvo cipi yine olu uc olur"),
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
    # --- K328 M3 IKI KOLLU KAPSAMA (mimar sarti: uc mutant, ucuncusu KONTROL) ----
    # ① KOL A, GENIS MENZIL: JETON kolunun uyelik kaydini sustur -> o yoldan gelen her
    #    uyelik duser. Bu, "sayfada gorunen urun cip suzgecinde KAYBOLUYOR" halinin
    #    KATALOG OLCEGINDEKI halidir.
    #    🔴 ILK YAZIMDA "KOL B de kizarir, bu kasitli" demistim — OLCUM BUNU CURUTTU:
    #    BASLIK kolunun kaydi YERINDE kaldigi icin `cip \ sayfa` DEGISMIYOR ve KOL B
    #    YESIL kaliyor. Olculen: `kayip_kova=761`, kirmizi iddia sayisi 1 (yalniz M3-A).
    #    Yani ① de A'yi ISOLE ediyor; ④'ten farki MENZIL (761 kova ↔ 1 kova), sinif degil.
    ("cip-indeks.py",
     "                if uyelik is not None:                  # K328: SAYAN kol kaydeder\n"
     "                    uyelik.setdefault((kat, b, canon), set()).add(u.get(\"id\"))\n",
     "",
     "KIRMIZI",
     "K328① UYELIK KAYDINI SUSTUR: `sayfa \\ cip` patlar -> KOL A KIRMIZI "
     "(musteri guvencesi kolu yuk tasiyor mu)"),
    # ② KOL B: civili ad kumesinden `ami` DUSURULUR -> olculen kume cividen BUYUK
    #    gorunur ve "YENI ayrisma dogdu" hukmu yanar. KOL A ETKILENMEZ (ayrim kaniti).
    # 🔴 K328② ve ③ KALDIRILDI — YAPISAL OLARAK OLCULEMEZLER, OLCULDU:
    # `_kok_kostur()` (satir 911) mutant KOPYAYI degil `os.path.abspath(__file__)`i,
    # yani CANLI test dosyasini kosturur; kopyaya yalnizca `--kok` ile ISARET eder.
    # Dolayisiyla `cip-indeks-test.py`ye uygulanan bir mutant test davranisini HIC
    # degistirmez. Olculdu (27 Agu): ② `MUTANT FIILEN UYGULANDI 40/40` oldugu halde
    # sonuc YESIL (0 iddia kirmizi) — mutant uygulandi ama OLCULEMEDI; ③ ise ayni
    # sebeple SAHTE YESIL veriyordu (kontrol vakasi hicbir sey kanitlamiyordu).
    # Bu tabloda BIRAKMAK, ikisini de kalici yalanci yapardi ([[kabul-fiksturu-yasagi-kutsar]]).
    # KOL B'nin nobeti mutasyon bataryasinda DEGIL, testin ICINDE iki yonlu iddia
    # olarak durur (asagida "M3-B NOBET"); mutant yoklugu ADIYLA raporlanir.
    # ④ KOL A'NIN TEKIL AYRIM MUTANTI (mimar sarti): kaydi SUSTURMA — TEK BIR uyeligi
    #    dusur. O urun `sayfa`da kalir, `cip` kaydindan cikar -> KOL A KIRMIZI, KOL B
    #    YESIL (cip \ sayfa DEGISMEZ). ①'in aksine bu mutant iki kolu birden bozmaz,
    #    yani A'nin bagimsizligini KANITLAR. Kosucu dusen iddialari ADIYLA bastigi icin
    #    ayrim ciktidan okunur (`oldu[:3]`).
    ("cip-indeks.py",
     "                if uyelik is not None:                  # K328: SAYAN kol kaydeder\n"
     "                    uyelik.setdefault((kat, b, canon), set()).add(u.get(\"id\"))\n",
     "                if uyelik is not None and u.get(\"id\") != "
     "\"citroen-ami-kap-kilidi-bo-luk-kapa\":\n"
     "                    uyelik.setdefault((kat, b, canon), set()).add(u.get(\"id\"))\n",
     "KIRMIZI",
     "K328④ TEK UYELIGI DUSUR: o urun sayfada VAR cipte YOK -> KOL A KIRMIZI, "
     "KOL B YESIL (A'nin BAGIMSIZ ayrim kaniti)"),
    # ③ KONTROL: davranis DEGISTIRMEYEN bir dokunus YESIL kalmali. Bugun `varlik-test`te
    #    bunun TERSINI yasadik (hicbir sey degismedigi halde kapi kirmizi yaniyordu);
    #    kontrol vakasi olmadan ①/② kirmizisi "her degisiklige kizariyor" ile karisir.
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
    # --- MODEL CIPI KANONIKLESTIRME EKSENI (4 Agu) ---------------------------
    # 🔴 KANIT: bu mutantlar EKLENMEDEN ONCE batarya bu sinifi GORMUYORDU — model cipleri
    # HAM jetondu ve hicbir iddia "cip evreni sayfa evreniyle ayni mi" diye SORMUYORDU.
    # 🔴 (a) HEM ANAHTAR HEM YAZIM ham'a cevrilir. Yalniz anahtari bozmak COKME uretirdi
    # (iki canon AYNI gosterime duser -> cakisma fail-closed'i atesler) ve "KIRMIZI ama
    # hicbir iddia KALDI demedi" sayilirdi; mutant olculen bir IDDIAYI kirmali.
    ("cip-indeks.py",
     "    return (k, kalan, tuple(taban for taban, _e in mevren.kusak_tabanlari(marka, t)\n"
     "                            if taban != k))",
     "    _mk = _model_kanon.kanon(t)\n"
     "    return (_mk, t, tuple(taban for taban, _e in mevren.kusak_tabanlari(marka, t)\n"
     "                          if taban != _mk))", "KIRMIZI",
     "(a) CIP KANONIKLESTIRMESINI KALDIR: onek siyirma + alias duser -> '206' ile "
     "'Peugeot 206' yine AYRI cip (olculen canli hata geri gelir)"),
    ("cip-indeks.py",
     "    k = mevren.model_anahtari(marka, t)\n    if not k or k == _model_kanon.kanon(marka):",
     "    k = _model_kanon.kanon(t.split()[0])\n    if not k or k == _model_kanon.kanon(marka):",
     "KIRMIZI",
     "(b) FARKLI ARACLARI BIRLESTIR: ilk kelimeye katla -> 'Zafira Life' Zafira'ya, "
     "'Grand Vitara' Vitara'ya... duser; cip iki ayri araci tek kutuya yigar"),
    # 🔴 IDDIA EDILMEYEN EKSEN — DURUST KAYIT ([[beyan-edilmis-survivor]], olculdu 4 Agu):
    # "MARKA JETONU (PSA/VAG/Geo) CIP OLMAZ" ekseni BU KAPIDA iddia SAYILMIYOR. Denendi:
    #   * `_jeton_uyeligi`deki `marka_jetonu_mu` guardini dusuren mutant YESIL kaldi
    #     (batarya koşumu: 1/36 tutmadi) — cunku `indeks_uret`in BAG (cift) dongusu ayni
    #     yargiyi ikinci kez uyguluyor, jeton bagsiz kalinca cip zaten dogmuyor.
    #   * Tersi de dogru: yalniz BAG dongusundeki guardi dusurmek de cip uretmiyor
    #     (uyelik tarafi eliyor). Yani IKI KATMAN da TEK BASINA gozlenemiyor.
    #   * Ortak kaynagi (`marka_model_build.marka_jetonu_mu` -> False) bozan mutant ise
    #     M2'nin OKUDUGU yuklemi de bozar (totoloji) — kapi kendi lehine buker.
    # Bu eksen BAGIMSIZ oracle ile tools/model-uyelik-kapisi.py :: K7'de olculuyor (yargi
    # arama.py KAPALI MARKA KUMESI'nden AYRI okunur) ve orada oldurucu mutanti VAR.
    # Ayirt edici mutanti olmayan eksen burada AYRI IDDIA olarak SAYILMAZ; M2 bu kapida
    # ROZET_DISI + MODEL_OLMAYAN_CIFT eksenini tasir ve o eksen (c) mutantiyla oldurulebiliyor.
    # 🔴 (c) MARKA-KOR ELEME: OLCULDU (4 Agu) — koru MODEL_OLMAYAN_CIFT uzerinden yapmak
    # bugunku katalogda 0 cip olduruyor (ESDEGER mutant, yesil kalirdi). Ayirt edici olan
    # ROZET_DISI ekseni: kor yapilinca `(Peugeot, ds)` denial'i `(Citroen, DS)`i, `(Audi,
    # golf)` denial'i `(Volkswagen, Golf)`u oldururuyor — TAM olarak "baska markada gercek
    # bir modeli oldurme" sinifi (4 cip: VW Golf, Skoda Octavia, Citroen Berlingo, Citroen DS).
    ("cip-indeks.py",
     "        if (k[1], k[2]) in _mmb.ROZET_DISI or _mmb.model_olmayan_cift_mi(k[1], mm_ad[k]):\n"
     "            return True",
     "        if any(_c == k[2] for _m, _c in _mmb.ROZET_DISI) \\\n"
     "                or _mmb.model_olmayan_cift_mi(k[1], mm_ad[k]):\n"
     "            return True", "KIRMIZI",
     "(c) ELEMEYI MARKA-KOR YAP: marka ekseni dusunce BASKA markadaki GERCEK model de olur "
     "(VW Golf · Skoda Octavia · Citroen Berlingo · Citroen DS); M5 asiri-eleme ekseni"),
    ("cip-indeks.py",
     "            for canon in (tam | katlanan):",
     "            for canon in tam:", "KIRMIZI",
     "(d) CIP SAYISINI SAYFADAN AYIR: kusak katlamasi sayimdan duser -> cip 'Focus' 297 "
     "der, sayfa 305 gosterir (olculen 73 sapmali cip sinifi)"),
    ("index.html",
     '      p.set("model", ucModelEtiketi(activeCat, activeBrand, activeModel));',
     '      p.set("model", activeModel);', "KIRMIZI",
     "(e) ISTEMCI KANONIGI GONDERSIN (model): uc katlamaz -> 'F-Serisi'/'5 E-Tech' cipleri "
     "0 urun dondurur (olculen canli: model=F-Serisi -> 0, model=F-Series -> 8)"),
    # --- CIP ETIKETI TEK KAYNAK EKSENI — M9 (4 Agu, kararsiz jeton SINIF 1) ---
    # 🔴 KANIT: bu mutant EKLENMEDEN ONCE batarya bu sinifi GORMUYORDU — etiket secimini
    # degistiren mutant SAYILARI (M3) ve CANON'lari (M1) bozmadigi icin YESIL geciyordu;
    # oysa musteri ana sayfada bir ad, model sayfasinda BASKA bir ad gorurdu.
    # OLCULDU: en-az-sik yazima cevirmek 3 cipin adini kaydiriyor (Yamaha DT125/DT 125 ·
    # Yamaha YZF-R1/YZF R1 · Toyota Hilux/HiLux).
    # ⚠️ KURATORLU GOSTERIMI (_KANONIK_GOSTERIM) YOK SAYAN mutant BUGUN ESDEGERDIR (olculdu:
    # 0 cip degisir — tek uyesi Ford|fserisi ve orada en sik yazim zaten "F-Serisi"). O yuzden
    # bataryaya KONMADI; `K Serisi` gibi 1-1 sıklıklı aileler zorlamaya BAGLIDIR ve o eksen
    # tools/model-uyelik-kapisi.py :: K20'de OLDURUCU mutantla (M30) olculur.
    ("cip-indeks.py",
     "    return sorted(kalanlar.items(), key=lambda t: (-t[1], t[0]))[0][0]",
     "    return sorted(kalanlar.items(), key=lambda t: (t[1], t[0]))[0][0]", "KIRMIZI",
     "CIP ETIKETINI SAYFADAN AYIR: cip kendi yazimini secer -> ana sayfada 'DT 125', model "
     "sayfasinda 'DT125' (M9 tek kaynak ekseni)"),
    # --- KONTROL MUTANTLARI (YESIL bekleniyor) — iddialar ILGISIZ degisikliklere
    # PINLENMIS mi? Yesil kalmazlarsa kapi asiri-baglanmistir ([[kapi-kapsam-eksen-secimi]]).
    ("index.html", '.brand-btn:hover{border-color:var(--navy-2)}',
     '.brand-btn:hover{border-color:var(--gray-line)}', "YESIL",
     "ILGISIZ: cip hover rengi — davranisa DOKUNMAZ"),
    ("index.html", 'var PAGE_SIZE = 24;', 'var PAGE_SIZE = 12;', "YESIL",
     "ILGISIZ: sayfa boyu — iddialar sayfalama sabitine PINLENMEMELI"),
    ("cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "ILGISIZ: indeks surum alani — cip davranisina DOKUNMAZ"),
    ("cip-indeks.py",
     "    for (kat, mk, canon) in sorted(gecerli_model):",
     "    for (kat, mk, canon) in sorted(gecerli_model, reverse=True):", "YESIL",
     "KONTROL: cip montaj SIRASI degisir, KUME ve SAYILAR degismez -> iddia bozulmamali "
     "(daima-kirmizi bir M-ekseni boylece ayirt edilir)"),
    ("cip-indeks.py",
     '    mm_uyum = {}            # (kat, marka, CANON) -> {uyum[].model yazimi: n} (uc etiketi)',
     '    mm_uyum = dict()        # (kat, marka, CANON) -> {uyum[].model yazimi: n} (uc etiketi)',
     "YESIL",
     "KONTROL: esdeger sozluk kurulusu — davranis birebir ayni"),
]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _hedef(tmp, dosya):
    return os.path.join(tmp, dosya) if dosya == "index.html" \
        else os.path.join(tmp, "tools", dosya)


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
