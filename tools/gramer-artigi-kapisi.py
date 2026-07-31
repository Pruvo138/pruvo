#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GRAMER ARTIGI KAPISI — katalog metnine TOPLU YENIDEN YAZIM'in biraktigi enkaz.

NEYI KORUR (olculmus sessiz hata, 31 Tem 2026 / madde 46):
  332 kayitlik uretim-sureci temizliginde metinler `duzelt.py --toplu` ile TOPLU
  yeniden yazildi. Yeniden yazim kural tabanlidir ve kurali tetikleyen kelime
  cumleden CIKARILINCA geride GRAMERSIZ ENKAZ kalir. Isci yazmadan ONCE dar diff'i
  ELLE okudugu icin iki tanesi yakalandi:
      "En ince bolgesi yla olculur"        (ek kelimeden bosluklа KOPMUS)
      "dik konumda ve uretilir"            (baglac bosa dusmus)
  O turda yazilan nobetci ISCININ SCRATCHPAD'INDE kaldi, repoya HIC girmedi ->
  bir sonraki toplu yazimda ayni enkaz SESSIZCE canliya cikardi. Bu dosya o
  nobetcinin kalici hali + o turda KACAN eksenin (cumle-ICI yetim ek) eklenmis hali.

IDDIA (bloklayici): urunler.json'daki HER kaydin `baslik` + `aciklama` alaninda
  gramer-artigi vurusu = 0.

IKI EKSEN:
  A) YENIDEN YAZIM ENKAZI — bosa dusmus baglac/edat, cift noktalama, bosluk-once-
     noktalama, bos parantez, satir sonunda asili "ve"/virgul, madde isaretinden
     hemen sonra noktalama, noktalamaya yapisik YETIM EK.
  B) CUMLE-ICI YETIM EK (YENI, 31 Tem) — Turkce ek kelimeden bosluklа AYRILMIS,
     kendi basina bir jeton olarak duruyor: "bolgesi yla", "kapagi nin", "delik ten".
     A ekseni bunu YALNIZ noktalamaya bitisikken goruyordu (`\\b(yla|la|...)\\b[,.]`),
     cumle ICINDE kacan hali OLCULDU ve kapsam disiydi.

🔴 YANLIS-POZITIF NOBETI — B EKSENININ ELEME KURALLARI (hepsi CANLI KATALOG UZERINDE
   olculdu; ham sayilar bu dosyanin altindaki `_OLCUM_31TEM` sabitinde):
  1. AYIRICI GERCEKTEN BOSLUK OLMALI. Kesme isareti/tire ile BITISIK ek MESRUDUR
     ("WhatsApp'tan", "Line'i", "379926'nin"). Bu kural olmadan olculdu: 4257 aday
     -> 1824'e dustu; tek basina 2433 YANLIS-POZITIF eliyor (en buyugu: kataloğun
     her kaydindaki "WhatsApp'tan bize yazin" satiri = 1881 vurus).
  2. "de" / "da" KUME DISI. Turkce'de BAGLAC olarak AYRI yazilir ("hem de",
     "amaclarla da kullanilabilir") ve bulunma ekinden ancak ANLAMLA ayrilir —
     kural olarak yazilamaz. Olculdu: 1197 vurusun tamami mesru baglac.
  3. TEK HARFLI ekler (a, e, i, i, u, u) KUME DISI. Olculdu: 28 vurus, TAMAMI
     mesru — marka/model adi ("VW e UP", "Audi e tron", "Mitsubishi i MiEV",
     "4 e Drive") ve profil harfi ("GO9 u tipi" = U tipi). Endustriyel metinde
     tek harf cogunlukla KESIT HARFIDIR (U profil, L koseband, T kanal).
  4. "ne" (soru sozcugu) ve "su" (isim) KUME DISI — ek gorunumlu tam kelimeler.
  5. "ya"/"ye" SARTLI: ardindan "da/de/ya/ne" gelirse ("ya da", "ya ... ya")
     ya da AYNI CUMLEDE ikinci bir "ya"/"ne" varsa sayilmaz. Olculdu: 599 "ya"
     vurusunun tamami "ya da" idi -> kural sonrasi 0.
  6. "ta/te/tan/ten" SARTLI: bunlar ayni zamanda TAM KELIMEDIR ("ta ki", "tan
     vakti", "ten rengi"). Yalniz onceki kelime SERT SESSIZ ile bitiyorsa (yani
     -ta/-te/-tan/-ten ekinin ses uyumu GERCEKTEN gecerliyken) sayilir.
  7. "ile" HIC KUME DE DEGILDIR — mustakil edattir, ayri yazilmasi DOGRUDUR.

NE IDDIA ETMEZ (bilincli kapsam disi, KAYITLI):
  * ANLAM dogrulugu. "Kapagi nin" yakalanir; "kapagin nin" (yanlis ek) yakalanmaz.
    Turkce ek/anlam yargisi kural olarak yazilamaz — bu kapi YALNIZ KOPMUS ek arar.
  * SATIR BASINDAKI yetim ek (onceki satirdan kopmus). Ek, yapisacagi kelimeyi
    AYNI SATIRDA bulmak zorundadir (idx >= 1); satirlar arasi tasima aranmaz.
  * Yabanci dil / cevrilmemis blok (ayri eksen), uretim-sureci ifsasi
    (tools/denetim-kapisi.py), yayin ciktisi yorum yuzeyi (tools/yayin-ic-dil-kapisi.py).

KAPSAM (fail-closed): urunler.json TAMAMI, ORNEKLEME YOK. TABAN KUME kontrolu —
  dosya bir DIZI olmali ve >= TABAN_ASGARI kayit tasimali; tasimiyorsa OLCULEMEDI
  (cikis 3). Yani "0 vurus" YESIL'i bos/bozuk dosyadan gelemez.

Kullanim:
    python3 tools/gramer-artigi-kapisi.py                 # olcum (bloklayici)
    python3 tools/gramer-artigi-kapisi.py --dosya <yol>   # baska bir katalog kopyasi
    python3 tools/gramer-artigi-kapisi.py --liste         # ihlalleri tek tek bas (rapor)
    python3 tools/gramer-artigi-kapisi.py --kendini-test  # ic nobetci (katalog GEREKMEZ)

Cikis kodu: 0 = temiz · 1 = IHLAL · 3 = OLCULEMEDI (katalog yok/bozuk/taban alti).
"""
import argparse
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
URUNLER = os.path.join(ROOT, "urunler.json")

# Katalog bugun 15.558 kayit. Taban, kismi/bozuk bir dosyanin sessizce "0 vurus"
# YESIL'i uretmesini imkansiz kilar (kapsam kaybi = OLCULEMEDI, yesil DEGIL).
TABAN_ASGARI = 1000

ALANLAR = ("baslik", "aciklama")

# Olculmus ham sayilar (31 Tem 2026, canli urunler.json = 15.558 kayit). Eleme
# kurallarinin BEDELI burada yazilidir; kural gevsetilecekse once bu tablo okunur.
_OLCUM_31TEM = {
    "kayit": 15558,
    "B_ham_aday": 4257,          # hicbir eleme yokken
    "B_bitisik_elenince": 1824,  # kesme/tire ile bitisik olanlar dusunce
    "B_de_da": 1197,             # baglac — tamami mesru
    "B_ya": 599,                 # tamami "ya da" — tamami mesru
    "B_tek_harf": 28,            # e-tron / i-MiEV / e-UP / U tipi — tamami mesru
    "B_kalan_ihlal": 0,          # kurallar uygulandiktan sonra
}


# --------------------------------------------------------------------- A ekseni
# YENIDEN YAZIM ENKAZI. Her desenin yaninda NEDEN dar oldugu yazilidir.
#
# ⚠️ "ile uretilir" HAM HALDE KULLANILAMAZ: canli katalogda 42 MESRU cumle var
#    ("Orijinali kauclu olan parca TPU ile uretilir") — orada "ile"nin oznesi
#    (malzeme) YERINDE. Artik hali, "ile"nin ONUNDE hicbir sey KALMAMASIDIR
#    (satir/cumle basi ya da virgulden hemen sonra). Desen o hale daraltildi;
#    daraltma sonrasi katalog vurusu 42 -> 0.
# ⚠️ Yetim-ek-noktalama deseninde "da"/"de" YOKTUR: "sunulsa da," MESRU baglactir
#    (olculdu: tek yanlis-pozitif tam olarak buydu).
_ARTIK = (
    ("asili-ve-uretilir", r"\bve\s+üretilir",
     "baglacin oncesi bosalmis: '... ve uretilir'"),
    # ⚠️ [İIi]le: cumle basinda edat BUYUK harfle baslar ("İle üretilir.") —
    #    duz kucuk harfli desen o mutanti KACIRIYORDU (oz-testte olculdu).
    ("asili-ile", r"(?:^|(?<=[.;,]))\s*[İIi]le\s+üretilir\b",
     "edatin oncesi bosalmis: cumle/virgul basinda '... ile uretilir'"),
    # ⚠️ "ile" VIRGULDEN once MESRUDUR (dar tutuldu): "Cercevesi lazer tarama ile,
    #    kapak kismi modellenerek hazirlanmistir" — paralel yapida edat virgule
    #    dayanir. Canli katalogda olculdu: gevsek desen 2 YANLIS-POZITIF veriyordu.
    #    "ve"/"veya" icin ayni yumusatma YOK: onlar virgul oncesinde de artiktir.
    ("asili-baglac", r"\bve\s*[.;,]|\bveya\s*[.;,]|\bile\s*[.;](?:\s|$)",
     "baglac/edat noktalamaya carpmis"),
    ("cift-noktalama", r",\s*,|;\s*[;.]|\.\s*,|,\s*\.",
     "art arda noktalama"),
    ("bosluk-once-noktalama", r"\s[,;]|\s\.(?:\s|$)",
     "noktalamadan once bosluk"),
    ("bos-parantez", r"\(\s*\)",
     "icerigi silinmis parantez"),
    ("cift-bosluk", r"[ \t]{2,}",
     "silinen kelimeden kalan cift bosluk"),
    ("madde-basi-noktalama", r"^\s*[-•*]\s*[.,;]",
     "madde isaretinden hemen sonra noktalama"),
    ("satir-sonu-asili", r"(?:[,;]|\bve|\bveya|\bile)\s*$",
     "satir asili baglac/virgulle bitmis"),
    ("yetim-ek-noktalama",
     r"(?<![\wçğıöşüâîûÇĞİÖŞÜ])(?:yla|yle|la|le|ta|te|nda|nde|nin|nın|nun|nün)"
     r"(?![\wçğıöşüâîûÇĞİÖŞÜ])[,.]",
     "ek kelimeden kopup noktalamaya yapismis"),
)
ARTIK_RE = tuple((ad, re.compile(p, re.UNICODE), neden) for ad, p, neden in _ARTIK)


# --------------------------------------------------------------------- B ekseni
# CUMLE-ICI YETIM EK. Kume, Turkce'de TEK BASINA KELIME OLMAYAN eklerden kurulur.
#
# ⚠️ "s-" AILESI (sini/sunu/suyla/sıyla...) KUME DISI BIRAKILDI: bir kismi TAM
#    TURKCE KELIMEDIR — "su" (isim), "suyla" (su+yla, BITISIK yazilir), "sunu"
#    (isim), "sini" (isim). Canli katalogda olculdu: "Motor bolumunu tatli suyla
#    temizlemek" cumlesi tek basina 1 YANLIS-POZITIF veriyordu. Bu aile, kazandirdigi
#    kapsamdan (nadir "kapak siyla" hatasi) daha COK yanlis-pozitif getiriyor.
_EK_KESIN = set("""
yla yle la le na nin nun nı ni nu yı yi yu dan den lar ler
nda nde ndan nden ları leri larına lerine
ından inden undan ünden ında inde unda ünde
""".split())
_EK_KESIN |= {"nın", "nün", "nü", "yü", "nı", "yı"}

# Ek gorunumlu ama TAM KELIME de olabilen ekler -> ses uyumu SARTI aranir.
_EK_SERT_SESSIZ_SARTLI = {"ta", "te", "tan", "ten"}
# Baglac/soru kalibi riski tasiyanlar -> komsu jeton SARTI aranir.
_EK_KOMSU_SARTLI = {"ya", "ye"}

_SERT_SESSIZ = set("pçtkfhsş")

# KUME DISI (gerekce docstring'de, olculmus): baglac "de/da", soru "ne",
# isim "su", mustakil edat "ile", tum tek harfliler.
_KUME_DISI = {"de", "da", "ne", "su", "ile", "ki", "mi", "mı", "mu", "mü"}

_HARF = "0-9A-Za-zÇĞİIÖŞÜçğıiöşüÂÎÛâîû"
_JETON_RE = re.compile("[" + _HARF + "]+", re.UNICODE)
_CUMLE_AYIRICI = re.compile(r"[.!?;]")


def _jetonlar(satir):
    return [(m.group(0), m.start(), m.end()) for m in _JETON_RE.finditer(satir)]


def _cumle_parcasi(satir, konum):
    """Jetonun icinde bulundugu cumle parcasi (ya/ne kalibi nobetleri icin)."""
    bas = 0
    son = len(satir)
    for m in _CUMLE_AYIRICI.finditer(satir):
        if m.end() <= konum:
            bas = m.end()
        elif m.start() > konum:
            son = m.start()
            break
    return satir[bas:son]


def yetim_ek_bulgulari(satir):
    """B ekseni: (jeton, baglam) listesi. Eleme kurallari docstring'de."""
    out = []
    jt = _jetonlar(satir)
    for idx in range(1, len(jt)):
        t, a, b = jt[idx]
        if t != t.lower():                     # BUYUK harf -> marka/kisaltma, ek degil
            continue
        if t in _KUME_DISI:
            continue

        ara = satir[jt[idx - 1][2]:a]
        if ara == "" or ara.strip() != "":
            # kesme isareti / tire ile BITISIK ("WhatsApp'tan") -> mesru
            continue

        onceki = jt[idx - 1][0]
        sonraki = jt[idx + 1][0].lower() if idx + 1 < len(jt) else ""

        if t in _EK_SERT_SESSIZ_SARTLI:
            if not onceki or onceki[-1].lower() not in _SERT_SESSIZ:
                continue                      # "ta ki", "ten rengi" — ses uyumu yok
        elif t in _EK_KOMSU_SARTLI:
            if sonraki in ("da", "de", "ya", "ne"):
                continue                      # "ya da" / "ya ... ya"
            # ⚠️ BOSLUKLA PADLE: "Ya siyah ya beyaz" cumlesinde bastaki "ya"nin
            #    onunde bosluk YOKTUR; padlenmezse sayim 1 cikar ve kalip nobeti
            #    calismaz (oz-testte olculdu: 1 YANLIS-POZITIF).
            parca = " " + _cumle_parcasi(satir, a).lower() + " "
            if parca.count(" ya ") + parca.count(" ne ") > 1:
                continue                      # "ya X ya Y" / "ne X ne Y" kalibi
        elif t not in _EK_KESIN:
            continue

        out.append((t, satir[max(0, a - 40):min(len(satir), b + 40)]))
    return out


# ------------------------------------------------------------------ tarama
def satir_bulgulari(satir):
    """Bir metin satirindaki TUM bulgular: [(eksen, ad, baglam)]."""
    bulgu = []
    for ad, rx, _neden in ARTIK_RE:
        m = rx.search(satir)
        if m:
            bulgu.append(("A", ad, satir[max(0, m.start() - 40):m.end() + 40]))
    for jeton, baglam in yetim_ek_bulgulari(satir):
        bulgu.append(("B", "yetim-ek:" + jeton, baglam))
    return bulgu


def kayit_bulgulari(kayit):
    bulgu = []
    for alan in ALANLAR:
        s = kayit.get(alan)
        if not isinstance(s, str):
            continue
        for satir in s.split("\n"):
            for eksen, ad, baglam in satir_bulgulari(satir):
                bulgu.append((alan, eksen, ad, baglam))
    return bulgu


def katalog_yukle(yol):
    if not os.path.exists(yol):
        return None, "katalog bulunamadi: " + yol
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except Exception as e:                                   # noqa: BLE001
        return None, "katalog okunamadi (%s)" % e
    if not isinstance(veri, list):
        return None, "katalog DIZI degil"
    return veri, None


def kos(yol=None, liste=False, taban=TABAN_ASGARI):
    yol = yol or URUNLER
    veri, hata = katalog_yukle(yol)
    if hata:
        print("🟠 OLCULEMEDI: " + hata)
        return 3
    if len(veri) < taban:
        print("🟠 OLCULEMEDI: TABAN KUME alti — %d kayit (asgari %d). Kismi/bozuk "
              "dosyadan gelen '0 vurus' YESIL sayilmaz." % (len(veri), taban))
        return 3

    ihlal = []
    for kayit in veri:
        if not isinstance(kayit, dict):
            continue
        for alan, eksen, ad, baglam in kayit_bulgulari(kayit):
            ihlal.append((kayit.get("id"), alan, eksen, ad, baglam))

    print("GRAMER ARTIGI KAPISI — %d kayit tarandi (%s)" % (len(veri), os.path.basename(yol)))
    if not ihlal:
        print("✅ TEMIZ: gramer artigi vurusu 0 (A ekseni %d desen · B ekseni yetim ek)"
              % len(ARTIK_RE))
        return 0

    a_say = sum(1 for x in ihlal if x[2] == "A")
    b_say = sum(1 for x in ihlal if x[2] == "B")
    kayit_say = len({x[0] for x in ihlal})
    print("🔴 IHLAL: %d vurus / %d kayit (A=%d · B=%d)" % (len(ihlal), kayit_say, a_say, b_say))
    for kid, alan, eksen, ad, baglam in (ihlal if liste else ihlal[:40]):
        print("   [%s] %-28s %-22s %r" % (eksen, kid, ad, baglam))
    if not liste and len(ihlal) > 40:
        print("   ... (+%d; tamami icin --liste)" % (len(ihlal) - 40))
    return 1


# ------------------------------------------------------------------ oz-nobetci
# 8 SENTETIK BOZUK (8/8 KIRMIZI olmali) — madde-46'da GERCEKTEN olusan enkaz
# siniflari + kacan cumle-ici yetim ek ekseni.
_BOZUK = (
    ("B1 cumle-ici yetim ek (madde 46'da KACAN eksen)",
     "En ince bölgesi yla ölçülür."),
    ("B2 yetim ek ortada (iyelik+ilgi)",
     "Kapağı nin çapı 40 mm ölçülür."),
    ("B3 yetim ayrilma eki",
     "Delik ten geçen cıvata sabitlenir."),
    ("B4 sert sessiz sonrasi yetim -ta",
     "Braket ta konumlanan yuva vardır."),
    ("A1 bosa dusmus baglac",
     "Dik konumda ve üretilir."),
    ("A2 cumle basinda asili edat",
     "İle üretilir."),
    ("A3 noktalamaya yapismis yetim ek",
     "Gövde yüzeyine yla, sabitlenir."),
    ("A4 cift noktalama + bos parantez",
     "Montaj yüzeyi ( ) düzdür,, sabit kalır."),
)

# 12 MESRU (yanlis-pozitif 0 olmali) — ozellikle "de/da" baglaci, "ya da", "ile".
_MESRU = (
    "Hem de küçük alanlarda kullanılabilir.",
    "Ofis ya da atölye masasında kullanılır.",
    "Kayak ya da snowboard ekipmanına uyar.",
    "Bu amaçlarla da kullanılabilir.",
    "Orijinali kauçuk olan parça TPU ile üretilir.",
    "Sipariş için WhatsApp'tan bize yazın.",
    "379926'nın yerine geçen bir yuvadır.",
    "Line'ı içine alan bir kanal açılmıştır.",
    "VW e UP ve Audi e tron modellerine uyar.",
    "Mitsubishi i MiEV kokpitine takılır.",
    "GO9 u tipi montaj ayağıyla gelir.",
    "Yaklaşık dış ölçüler: 25 × 25 × 15 mm.",
    "Ta ki cıvata oturana kadar bastırılır.",
    "Ten rengi yüzey tercih edilebilir.",
    "Ya siyah ya beyaz yüzeyle uyumludur.",
    "Kapak, gövdeye vidayla sabitlenir; conta ile birlikte kullanılır.",
    # 🔴 Bu iki cumle CANLI KATALOGDAN alindi: ilk turda kapi bunlari KIRMIZI
    #    yakti (2 + 1 yanlis-pozitif) ve kural daraltildi. Nobetci burada durur ki
    #    kural bir daha gevsetilirse oz-test KIRMIZI yansin.
    "Çerçevesi lazer tarama ile, kapak kısmı modellenerek hazırlanmıştır.",
    "Motor bölümünü tatlı suyla temizlemek için kullanılan bağlantı kitidir.",
    "PA66+GF30 veya POM malzeme ile, malzeme çekmesi hesaba katılarak üretilir.",
)


_IDDIA = [0]          # oz-testte SAYILAN iddia adedi (elle sabit YOK — kaymasin)


def _olc(hatalar, etiket, kosul):
    _IDDIA[0] += 1
    print(("   ✅ " if kosul else "   🔴 ") + etiket)
    if not kosul:
        hatalar.append(etiket)


def kendini_test():
    """IC NOBETCI: pozitif eksen (8 sentetik bozuk) + negatif eksen (16 mesru)
    + TABAN KUME fail-closed + kapinin GOVDESI inert olamaz (mutasyon)."""
    hatalar = []

    print("-- (1) POZITIF EKSEN: sentetik bozuk cumleler KIRMIZI yanmali")
    for etiket, cumle in _BOZUK:
        _olc(hatalar, "%s -> yakalandi (%r)" % (etiket, cumle),
             bool(satir_bulgulari(cumle)))

    print("-- (2) NEGATIF EKSEN: mesru cumlelerde YANLIS-POZITIF 0")
    for cumle in _MESRU:
        b = satir_bulgulari(cumle)
        _olc(hatalar, "mesru: %r%s" % (cumle, ("  << " + repr(b)) if b else ""), not b)

    print("-- (3) B EKSENI ELEME KURALLARI tek tek")
    _olc(hatalar, "3a kesme isaretiyle BITISIK ek sayilmaz ('WhatsApp'tan')",
         not yetim_ek_bulgulari("WhatsApp'tan bize yazın"))
    _olc(hatalar, "3b ayni ek BOSLUKLA ayrilinca sayilir ('WhatsApp tan')",
         bool(yetim_ek_bulgulari("WhatsApp tan bize yazın")))
    _olc(hatalar, "3c 'de/da' baglaci HIC sayilmaz",
         not yetim_ek_bulgulari("bunun için de kullanılır ve şunun da yanına")),
    _olc(hatalar, "3d tek harfli ek sayilmaz ('Audi e tron')",
         not yetim_ek_bulgulari("Audi e tron sahibi"))
    _olc(hatalar, "3e 'ya' ardindan 'da' gelirse sayilmaz",
         not yetim_ek_bulgulari("ofis ya da atölye"))
    _olc(hatalar, "3f 'ya' TEK BASINA yetim kalirsa sayilir ('kapağı ya takılır')",
         bool(yetim_ek_bulgulari("kapağı ya takılır")))
    _olc(hatalar, "3g yumusak sessiz sonrasi 'ta' sayilmaz (ses uyumu yok)",
         not yetim_ek_bulgulari("gövde ta ki oturana kadar"))
    _olc(hatalar, "3h sert sessiz sonrasi 'ta' sayilir",
         bool(yetim_ek_bulgulari("braket ta konumlanan yuva")))
    _olc(hatalar, "3i BUYUK harfli jeton ek sayilmaz ('U tipi', 'LA')",
         not yetim_ek_bulgulari("montaj U tipi LA yuvası"))
    _olc(hatalar, "3j satirin ILK jetonu ek olsa bile sayilmaz (kapsam disi, kayitli)",
         not yetim_ek_bulgulari("yla ölçülür"))

    print("-- (4) A EKSENI daraltmasi (mesru malzeme cumlesi vs asili edat)")
    _olc(hatalar, "4a 'TPU ile üretilir' MESRU (42 canli kayit)",
         not satir_bulgulari("Orijinali kauçuk olan parça TPU ile üretilir."))
    _olc(hatalar, "4b cumle basinda 'ile üretilir' ARTIK",
         bool(satir_bulgulari("İle üretilir.")))
    _olc(hatalar, "4c virgulden sonra 'ile üretilir' ARTIK",
         bool(satir_bulgulari("Gövde dayanıklıdır, ile üretilir.")))
    _olc(hatalar, "4d 'sunulsa da,' MESRU baglac (olculmus tek yanlis-pozitif)",
         not satir_bulgulari("Tasarım ilk deneme olarak sunulsa da, sapmaları azaltır."))
    _olc(hatalar, "4e cumle SONUNDA asili 'ile.' hala ARTIK",
         bool(satir_bulgulari("Gövde dayanıklı bir yapı ile.")))
    _olc(hatalar, "4f asili 've,' virgul oncesinde de ARTIK",
         bool(satir_bulgulari("Kapak sabitlenir ve, gövde oturur.")))

    print("-- (5) FAIL-CLOSED: taban kume alti / bozuk katalog OLCULEMEDI (3) verir")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        bos = os.path.join(d, "bos.json")
        with open(bos, "w", encoding="utf-8") as f:
            json.dump([{"id": "x", "aciklama": "temiz"}], f)
        _olc(hatalar, "5a taban alti katalog -> cikis 3", kos(bos) == 3)
        bozuk = os.path.join(d, "bozuk.json")
        with open(bozuk, "w", encoding="utf-8") as f:
            f.write("{bozuk")
        _olc(hatalar, "5b bozuk JSON -> cikis 3", kos(bozuk) == 3)
        _olc(hatalar, "5c olmayan dosya -> cikis 3", kos(os.path.join(d, "yok.json")) == 3)

        print("-- (6) MUTASYON: tek bozuk kayit tasiyan katalog KIRMIZI yanmali")
        n = TABAN_ASGARI + 5
        temiz = [{"id": "t%d" % i, "aciklama": "Kapak gövdeye vidayla sabitlenir."}
                 for i in range(n)]
        t_yol = os.path.join(d, "temiz.json")
        with open(t_yol, "w", encoding="utf-8") as f:
            json.dump(temiz, f, ensure_ascii=False)
        _olc(hatalar, "6a %d temiz kayit -> cikis 0" % n, kos(t_yol) == 0)
        for etiket, cumle in _BOZUK:
            mutant = list(temiz)
            mutant[len(mutant) // 2] = {"id": "mutant", "aciklama": cumle}
            m_yol = os.path.join(d, "mutant.json")
            with open(m_yol, "w", encoding="utf-8") as f:
                json.dump(mutant, f, ensure_ascii=False)
            _olc(hatalar, "6b mutant [%s] -> cikis 1" % etiket, kos(m_yol) == 1)
        # baslik alani da taraniyor mu (alan korlugu nobeti)
        mutant = list(temiz)
        mutant[3] = {"id": "mutant-baslik", "baslik": "Kapağı nin Yuvası",
                     "aciklama": "Temiz."}
        m_yol = os.path.join(d, "mutant2.json")
        with open(m_yol, "w", encoding="utf-8") as f:
            json.dump(mutant, f, ensure_ascii=False)
        _olc(hatalar, "6c `baslik` alani da taraniyor -> cikis 1", kos(m_yol) == 1)

    print()
    if hatalar:
        print("🔴 OZ-TEST KIRMIZI: %d iddia dustu" % len(hatalar))
        for h in hatalar:
            print("   - " + h)
        return 1
    print("✅ oz-test YESIL: %d iddia (pozitif %d sentetik bozuk · negatif %d mesru "
          "cumle · %d mutant katalog)" % (_IDDIA[0], len(_BOZUK), len(_MESRU), len(_BOZUK) + 1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dosya")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--kendini-test", action="store_true")
    args = ap.parse_args()
    if args.kendini_test:
        sys.exit(kendini_test())
    sys.exit(kos(args.dosya, liste=args.liste))


if __name__ == "__main__":
    main()
