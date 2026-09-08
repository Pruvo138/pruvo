#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISTEMCI BASLIK KOLU (ADIM 2, 8 Eyl) — KABUL + MUTANT BATARYASI.

NE OLCULUR: `index.html`in GERCEK govdesi (norm + MARKA KURATORLUGU + MARKA SORGUSU +
KANONIK MODEL ESLEMESI bloklari + `edgeSuzgecSapmasi` fonksiyonu) AYIKLANIR ve node ile
kosturulur. Python'a bir "filtre portu" YAZILMAZ — port yazsaydik iddia totolojiye
donerdi ([[beyan-edilmis-survivor]]).

NEDEN VAR (olculen ariza, 8 Eyl): uc (D1 model uyeligi) uyeligi
`marka[] ∪ uyum[].model ∪ BASLIKTA TAM KELIME`den aliyordu, istemci YALNIZ ilkinden.
Fail-closed nobetci farki gorunur arizaya cevirdi: `?marka=Toyota&model=Corolla`
isteginde uc 203 urun donduruyor, donen 24 kartin 0'i istemci yuklemini geciyor ve sayfa
TOPTAN reddediliyordu ("0 urun"). ADIM 2 dogrulama tabanini ucun yuklemine ESITLER.

🔴 NOBETCI OLMEDI EKSENI: bu dosya "kol calisiyor" demekle yetinmez — kolun EKLENMESIYLE
nobetcinin fail-closed yonu KAYBOLMADIGINI da olcer (I2/I4/I5). Gevsetme mutantlari
(M4/M5) tam bu ekseni oldurur.

🔴 IZOLASYON: mutant YALNIZ bellekteki dizgede yasar; `index.html` OKUNUR, hicbir dosya
yazilmaz/silinmez (gecici dosya bile uretilmez — JS node'a STDIN ile verilir). Testte
`rm -rf`/`rmtree`/`unlink` ve gercek ev yolu YOKTUR.

Kosum: python3 tools/model-baslik-istemci-test.py [--kendini-test]
  rc=0 -> tum iddialar GECTI (ve --kendini-test'te her mutant beklenen iddiayi OLDURDU)
"""
import json
import os
import re
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(KOK, "index.html")

# ---------------------------------------------------------------- FIKSTUR (sentetik kartlar)
# 🔴 SENTETIK, KATALOGDAN BAGIMSIZ: gercek katalogtan beslenseydi urun partisi degistiginde
# iddia sessizce baska bir seyi olcerdi. Her satir BIR yuklem kolunu civiler.
KARTLAR = {
    # BASLIK KOLU uyesi — `marka[]`de jeton YOK, baslikta TAM KELIME var (arizanin ta kendisi)
    "A": {"id": "A", "marka": ["Toyota"], "baslik": "Toyota Corolla E120 kapı kolu"},
    # `marka[]` uyesi — bugunku kol (kol eklenince BOZULMAMALI)
    "B": {"id": "B", "marka": ["Toyota", "Corolla"], "baslik": "Kapı kolu"},
    # UYE DEGIL — jeton ne `marka[]`de ne baslikta (nobetcinin YAKALAMASI gereken kart)
    "C": {"id": "C", "marka": ["Toyota"], "baslik": "Toyota Yaris torpido klipsi"},
    # BASLIK YOK — eksen dogrulanamaz; kart ATLANIR, sayfa TOPTAN reddedilmez
    "D": {"id": "D", "marka": ["Toyota"], "baslik": ""},
    # YANLIS MARKA — uc marka suzgecini birakirsa nobetci "marka" der
    "F": {"id": "F", "marka": ["Ford"], "baslik": "Ford Focus MK2 kapı kolu"},
    # TEHLIKE SINIFI (Renault|5): kusak sayisi UYE DEGIL, gercek model UYE
    "E1": {"id": "E1", "marka": ["Renault"], "baslik": "Renault Espace 5 bardaklık"},
    "E2": {"id": "E2", "marka": ["Renault"], "baslik": "Renault 5 E-Tech ayna kapağı"},
    # KATLAMA (Volkswagen|Golf): kusak jetonu TABAN modele duser — baslik kolu bunu EZMEZ
    "G": {"id": "G", "marka": ["Volkswagen", "Golf 4"], "baslik": "Kapı kolu"},
    # ALIAS KAYNAGI + KANON PENCERESI: kova MODEL_ALIAS ile birlesmis ("Mercedes|a",
    # "Mercedes|aklasse" -> "aclass"); istemciye YALNIZ kanonik gosterim gelir. Kaynak
    # anahtar kanon bicimindedir ("aklasse"), basliktaki "A-Klasse" ise IKI kelimedir.
    "M": {"id": "M", "marka": ["Mercedes", "W176"],
          "baslik": "A-Klasse Ses Konferans Halkası (Mercedes W176)"},
    # ALIAS KAYNAGININ DUZ YAZIMI: "Traffic" (yazim ikizi) -> `Trafic` kovasi
    "T": {"id": "T", "marka": ["Renault"], "baslik": "Renault Traffic yan panel klipsi"},
    # MENZIL CAPASI: kanon penceresi istenen GOSTERIME uygulanirsa bu kart yanlislikla
    # uye olur ve istemci SAYFADAN GENIS kalir (olculdu: 30 cift SAYFA_DAR, 205 urun).
    "R": {"id": "R", "marka": ["BMW"], "baslik": "BMW R 1250 GS sele kapağı"},
    # HAM ESITLIK: `marka[]` degeri istenen yazimla BIREBIR. Marka adiyla ayni deger
    # kanon yolunda BOS anahtar uretir (`modelOnekSiyir` markayi siyirir) — o yuzden bu
    # karti YALNIZ ham esitlik kolu tasir; kol dusunce iddia KIRMIZI yanar.
    "H": {"id": "H", "marka": ["Peugeot"], "baslik": "Kapı kolu"},
}

# (ad, aciklama, marka, model, sayfa kartlari, beklenen sapma, beklenen uye id kumesi)
IDDIALAR = [
    ("I1 BASLIK KOLU CANLI (kol olurse KIRMIZI)",
     "baslik-uyesi kart nobetciyi GECER ve uye SAYILIR",
     "Toyota", "Corolla", ["A", "B"], None, {"A", "B"}),
    ("I2 NOBETCI OLMEDI — MODEL EKSENI",
     "jetonu HICBIR kolda tasimayan kart sayfayi REDDETTIRIR",
     "Toyota", "Corolla", ["A", "B", "C"], "model", {"A", "B"}),
    ("I3 BASLIKSIZ KART ATLANIR (sayfa TOPTAN reddedilmez, kart UYE de sayilmaz)",
     "olcemedigin kart atlanir; 'yesil' demek DEGIL",
     "Toyota", "Corolla", ["A", "B", "D"], None, {"A", "B"}),
    ("I4 NOBETCI OLMEDI — MARKA EKSENI",
     "uc yanlis marka dondururse 'marka' sapmasi",
     "Toyota", "Corolla", ["A", "F"], "marka", {"A"}),
    ("I5 UC SUZGECI BIRAKIRSA YAKALANIR",
     "marka+model istegine marka TOPLAMI donerse (2 Agu vakasi) sayfa reddedilir",
     "Toyota", "Corolla", ["C", "A"], "model", {"A"}),
    ("I6 TEHLIKE KORUMASI (kisa/sayisal jeton yalniz marka+model BITISIK esler)",
     "'Renault Espace 5' UYE DEGIL, 'Renault 5 E-Tech' UYE",
     "Renault", "5", ["E2"], None, {"E2"}),
    ("I6b TEHLIKE KORUMASI KIRMIZI YONU",
     "kusak sayisi tasiyan kart sayfayi REDDETTIRIR",
     "Renault", "5", ["E2", "E1"], "model", {"E2"}),
    ("I7 KUSAK KATLAMASI KORUNDU (baslik kolu onun YERINE GECMEZ)",
     "'Golf 4' etiketli urun /golf/ kovasinda kalir",
     "Volkswagen", "Golf", ["G"], None, {"G"}),
    ("I9 ALIAS KAYNAGI + KANON PENCERESI (birlesmis kovada sayfa TOPTAN dusmez)",
     "`?model=A-Class` isteginde 'A-Klasse …' baslikli kart dogrulanir",
     "Mercedes", "A-Class", ["M"], None, {"M"}),
    ("I10 ALIAS KAYNAGININ DUZ YAZIMI ('Traffic' -> Trafic)",
     "yazim ikizi kaynak anahtardan bulunur",
     "Renault", "Trafic", ["T"], None, {"T"}),
    ("I11 KANON PENCERESI MENZILI (istenen GOSTERIME uygulanmaz)",
     "'BMW R 1250 GS' basligi R1250GS kovasina GIRMEZ; girseydi istemci sayfadan GENIS olurdu",
     "BMW", "R1250GS", ["R"], "model", set()),
    ("I8 HAM ESITLIK KORUNDU (asla daralma)",
     "kanon BOS anahtar uretse bile `marka[]` birebir tasiyorsa UYE",
     "Peugeot", "Peugeot", ["H"], None, {"H"}),
]

# (ad, eski dizge, yeni dizge, oldurmesi BEKLENEN iddia onekleri)
MUTANTLAR = [
    ("M1 BASLIK KOLUNU TAMAMEN KALDIR (8 Eyl oncesi davranis)",
     "    return modelBasliktaEsler(urun, model, hedefMarka);   // BAŞLIK KOLU (ADIM 2)",
     "    return false;",
     ("I1", "I3", "I5", "I6")),
    ("M2 TEHLIKE SINIFINI DUSUR (her jeton 'guvenli' sayilsin)",
     "    return !j || j.length <= 3 || /^[0-9]+$/.test(j);",
     "    return !j;",
     ("I6b",)),
    # 🔴 URETIM TUZAGININ BIREBIR KOPYASI (marka_model_build.baslikta_tam_kelime yorumu):
    # bitisikligi "jetondan onceki kelimeleri KATLA, markaya esit mi" diye yazmak.
    # markaKatla ONEK kurali isletir ("renault espace" -> "Renault"), yani koruma SESSIZCE
    # olur. Bu mutant onu gorunur kilar.
    ("M3 BITISIKLIGI markaKatla ILE YAZ (onek katlamasi korumayi sessizce oldurur)",
     "    var adlar = markaYazimlari(marka);\n"
     "    for(var i = 0; i < adlar.length; i++){\n"
     "      var aw = modelKelimeleri(adlar[i]);\n"
     "      if(aw.length && modelAltDizi(baslikKelimeleri, aw.concat(jw))){ return true; }\n"
     "    }\n"
     "    return false;",
     "    for(var i = 0; i < baslikKelimeleri.length; i++){\n"
     "      if(baslikKelimeleri[i] !== jw[0] || i === 0){ continue; }\n"
     "      if(markaKatla(baslikKelimeleri.slice(0, i).join(\" \")) === marka){ return true; }\n"
     "    }\n"
     "    return false;",
     ("I6b",)),
    ("M4 NOBETCIYI GEVSET: her kart 'olcemedim' diye ATLANSIN (fail-open)",
     "          if(!String(k.baslik === null || k.baslik === undefined ? \"\" : k.baslik).trim()){",
     "          if(true){",
     ("I2", "I5", "I6b")),
    ("M5 NOBETCININ MODEL EKSENINI KALDIR",
     "        if(activeModel !== \"Tümü\" && !modelEsler(k, activeModel, hedefMarka)){",
     "        if(false){",
     ("I2", "I5", "I6b")),
    ("M6 KUSAK KATLAMASINI KALDIR (baslik kolu onu telafi ETMEZ)",
     "      var tb = kusakTabanlari(hedefMarka, mk[i]);      // KUŞAK KATLAMASI (tek yönlü)",
     "      var tb = [];",
     ("I7",)),
    ("M7 HAM ESITLIK KOLUNU KALDIR",
     "    if(mk.indexOf(model) !== -1){ return true; }       // BUGÜNKÜ ham eşitlik — asla daralma",
     "    if(false){ return true; }",
     ("I8",)),
    ("M8 MARKA EKSENINI DUSUR (nobetci yalniz modele baksin)",
     "        if(hedefMarka && !markaSorgusuEsler(k, hedefMarka)){",
     "        if(false){",
     ("I4",)),
    ("M9 ALIAS KAYNAK YAZIMLARINI KALDIR (istemci yalniz kanonik gosterimi arar)",
     "      var kaynaklar = modelAliasKaynaklari(mrk, model);",
     "      var kaynaklar = [];",
     ("I9", "I10")),
    ("M10 KANON PENCERESINI KALDIR (ayiracli katalog yazimi bulunamaz)",
     "        if(baslikKanonPenceresi(bw, kaynaklar[j])){ return true; }",
     "        if(false){ return true; }",
     ("I9",)),
    # 🔴 MENZIL MUTANTI: kanon penceresini istenen GOSTERIME de uygula — olculmus
    # over-genisleme (30 cift SAYFA_DAR, 205 urun; kapi K1 KIRMIZI).
    ("M11 KANON PENCERESINI ISTENEN GOSTERIME DE UYGULA (istemci sayfadan GENIS olur)",
     "      if(basliktaTamKelime(bw, mrk, model)){ return true; }",
     "      if(basliktaTamKelime(bw, mrk, model) ||\n"
     "         baslikKanonPenceresi(bw, modelKelimeleri(model).join(\"\"))){ return true; }",
     ("I11",)),
]

HARNESS = r"""
"use strict";
__NORM__
__KURATORLUK__
/* cipIndeks() yayin kopyasina gomulen `window.PRUVO_CIP_INDEKS`ten beslenir; burada
   YOKTUR ve govdenin kendi fail-open dali (indeks yoksa cip evreni BOS) kosar — fikstur
   markalari (Toyota/Ford/Renault/Volkswagen/Peugeot) TANINMIS listede oldugu icin bu
   dalin olculen kollara etkisi yoktur. */
function cipIndeks(){ return null; }
__MARKASORGU__
__MODELKANON__
/* edgeSuzgecSapmasi() GERCEK govdesi. Kategori/grup eksenleri "Tümü" oldugu icin
   bu kosumda susar; olculen sey MODEL ve MARKA kollaridir. */
var activeCat = "Tümü", activeAlt = "Tümü", activeSeri = false;
var activeBrand = "Tümü", activeModel = "Tümü";
function kategoriEsler(){ return true; }
__NOBETCI__
const girdi = __GIRDI__;
const out = [];
for (const t of girdi) {
  activeBrand = t.marka; activeModel = t.model;
  const hedefMarka = markaKatla(t.marka);
  const uyeler = t.kartlar.filter(k => modelEsler(k, t.model, hedefMarka)).map(k => k.id);
  out.push({ad: t.ad, sapma: edgeSuzgecSapmasi(t.kartlar), uyeler: uyeler.sort()});
}
process.stdout.write(JSON.stringify({ok: true, satirlar: out}));
"""


class Olculemedi(Exception):
    pass


def _arasi(kaynak, bas, son, ad):
    b, s = kaynak.find(bas), kaynak.find(son)
    if b == -1 or s == -1 or s <= b:
        raise Olculemedi("index.html %s blogu ayiklanamadi (marker yok/tasinmis)" % ad)
    return kaynak[kaynak.index("\n", b) + 1:s]


def kaynak_uret(index_html):
    """GERCEK JS parcalari + fikstur -> tek kosulabilir kaynak (fail-closed)."""
    m = re.search(r"function norm\(s\)\{[\s\S]*?\n  \}", index_html)
    if not m:
        raise Olculemedi("index.html norm() ayiklanamadi")
    nob = re.search(r"  function edgeSuzgecSapmasi\(kartlar\)\{[\s\S]*?\n  \}", index_html)
    if not nob:
        raise Olculemedi("index.html edgeSuzgecSapmasi() ayiklanamadi")
    kanon = _arasi(index_html, "// --- KANONİK MODEL EŞLEMESİ BAŞ",
                   "// --- KANONİK MODEL EŞLEMESİ SON ---", "KANONIK MODEL ESLEMESI")
    for imza in ("MODEL_BASLIK_YUKLEM", "function modelBasliktaEsler",
                 "function basliktaTamKelime", "function modelTehlikeliMi",
                 "function modelEsler"):
        if imza not in kanon:
            raise Olculemedi("KANONIK MODEL ESLEMESI blogunda %s YOK" % imza)
    girdi = [{"ad": ad, "marka": mk, "model": md,
              "kartlar": [KARTLAR[x] for x in kartlar]}
             for ad, _n, mk, md, kartlar, _s, _u in IDDIALAR]
    return (HARNESS
            .replace("__NORM__", m.group(0))
            .replace("__KURATORLUK__", _arasi(index_html, "// --- MARKA KÜRATÖRLÜĞÜ BAŞ",
                                              "// --- MARKA KÜRATÖRLÜĞÜ SON ---",
                                              "MARKA KURATORLUGU"))
            .replace("__MARKASORGU__", _arasi(index_html, "// --- MARKA SORGUSU BAŞ",
                                              "// --- MARKA SORGUSU SON ---", "MARKA SORGUSU"))
            .replace("__MODELKANON__", kanon)
            .replace("__NOBETCI__", nob.group(0))
            .replace("__GIRDI__", json.dumps(girdi, ensure_ascii=False)))


def kos(js):
    """JS'i node'a STDIN ile verir — gecici dosya URETILMEZ, dolayisiyla SILINMEZ."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        raise Olculemedi("node bulunamadi — GERCEK govde kosturulamaz "
                         "(Python portu yazmak iddiayi totolojiye cevirirdi)")
    p = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, timeout=300)
    if p.returncode != 0 or not (p.stdout or "").strip():
        raise Olculemedi("node kosumu coktu (rc=%d): %s"
                         % (p.returncode, ((p.stderr or "").strip().splitlines() or [""])[-1][:300]))
    veri = json.loads(p.stdout)
    if not veri.get("ok"):
        raise Olculemedi("node kosumu ok=false dondu")
    return dict((s["ad"], s) for s in veri["satirlar"])


def degerlendir(sonuc):
    """-> (gecen adlar, kalan [(ad, detay)])"""
    gecen, kalan = [], []
    for ad, _not, _mk, _md, _kartlar, bek_sapma, bek_uye in IDDIALAR:
        s = sonuc.get(ad)
        if s is None:
            kalan.append((ad, "kosum satiri YOK"))
            continue
        sapma = s.get("sapma")
        uyeler = set(s.get("uyeler") or [])
        if sapma != bek_sapma or uyeler != set(bek_uye):
            kalan.append((ad, "sapma=%s (beklenen %s) · uye=%s (beklenen %s)"
                          % (sapma, bek_sapma, sorted(uyeler), sorted(bek_uye))))
        else:
            gecen.append(ad)
    return gecen, kalan


def main():
    kendini = "--kendini-test" in sys.argv
    with open(INDEX, encoding="utf-8") as f:
        index_html = f.read()
    try:
        js = kaynak_uret(index_html)
        gecen, kalan = degerlendir(kos(js))
    except Olculemedi as e:
        print("OLCULEMEDI: %s" % e)
        print("SONUC: OLCULEMEDI (yesil DEGIL) rc=1")
        return 1

    print("== TABAN ==")
    for ad, aciklama, _mk, _md, _k, _s, _u in IDDIALAR:
        print("  %s %s — %s" % ("GECTI" if ad in gecen else "KALDI", ad, aciklama))
    for ad, detay in kalan:
        print("    %s: %s" % (ad, detay))
    if kalan:
        print("\nSONUC: %d/%d iddia KALDI" % (len(kalan), len(IDDIALAR)))
        return 1
    print("  TABAN: %d/%d iddia GECTI ✔" % (len(gecen), len(IDDIALAR)))

    if not kendini:
        print("\nSONUC: %d/%d iddia GECTI ✔ (mutant bataryasi icin --kendini-test)"
              % (len(gecen), len(IDDIALAR)))
        return 0

    print("\n== MUTANT BATARYASI (mutant YALNIZ bellekteki dizgede; index.html OKUNUR) ==")
    tutmayan = []
    for ad, eski, yeni, bekleyen in MUTANTLAR:
        if index_html.count(eski) != 1:
            tutmayan.append((ad, "CAPA %d kez esletti (1 olmali) — mutant CANLI govdeye "
                                 "ulasmiyor" % index_html.count(eski)))
            print("  KALDI %s — capa tutmadi" % ad)
            continue
        try:
            mg, mk = degerlendir(kos(kaynak_uret(index_html.replace(eski, yeni, 1))))
        except Olculemedi as e:
            tutmayan.append((ad, "mutant kopyasi cokti: %s" % e))
            print("  KALDI %s — kopya cokti" % ad)
            continue
        olen = set(x for x, _d in mk)
        # ONEK esitligi DEGIL, ONEK+BOSLUK: "I6" capasi "I6b" iddiasini YUTMAZ
        # ([[arac-adi-onek-eslesmesi-komsu-araci-keser]]).
        eksik = [b for b in bekleyen if not any(x.startswith(b + " ") for x in olen)]
        fazla_bilgi = "olen=%s" % (sorted(olen) or "-")
        if eksik:
            tutmayan.append((ad, "beklenen iddia OLMEDI: %s · %s" % (eksik, fazla_bilgi)))
            print("  KALDI %s — %s" % (ad, fazla_bilgi))
        else:
            print("  GECTI %s — %s" % (ad, fazla_bilgi))

    print("\nMUTANT: %d/%d beklentiyi tuttu · beklentiyi tutmayan: %d"
          % (len(MUTANTLAR) - len(tutmayan), len(MUTANTLAR), len(tutmayan)))
    for ad, detay in tutmayan:
        print("  %s: %s" % (ad, detay))
    if tutmayan:
        print("\nSONUC: MUTANT BATARYASI KIRMIZI")
        return 1
    print("\nSONUC: %d/%d iddia GECTI ✔ · beklentiyi tutmayan mutant: 0"
          % (len(gecen), len(IDDIALAR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
