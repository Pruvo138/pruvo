#!/usr/bin/env python3
"""Printables (Prusa) GraphQL API ortak cekirdegi — Thingiverse yardimcilarinin esdegeri.

Printables'in RESMI REST API'si YOK; site `https://api.printables.com/graphql/` GraphQL
endpoint'ini kullanir. TOKEN GEREKMEZ — arama + metadata + gorseller + STL INDIRME public.

STL indirme: `getDownloadLink` mutation'i login OLMADAN calisir (test edildi, ok:true),
`files.printables.com` uzerinde 24 saat gecerli imzali link verir. Yani Thingiverse'teki gibi
otomatik STL cekip olcebiliyoruz (bkz. download_stl / tools/printables-fetch.py).

Import edilebilir (from printables_api import ...) DEGIL — dosya adinda '-' var; bunun yerine
diger araclar bu modulu `runpy`/subprocess yerine kendi kopyasiyla degil, ortak fonksiyonlari
kullanmak isterse: `import importlib.util` ile yukler. Basitlik icin arama/meta araclari
kendi kucuk gql() sarmalayicisini tutar; buradaki degerler (ENDPOINT, MEDIA, lisans kurali)
tek dog­ruluk kaynagidir.
"""
import json, os, re, struct, sys, urllib.request, zipfile, io
import xml.etree.ElementTree as ET

# Bbox saglik esikleri TEK KAYNAKTAN gelir (K287) — bu dosyada esik SAYISI YOKTUR.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olcu_saglik
import olcu_parca

ENDPOINT = "https://api.printables.com/graphql/"
MEDIA = "https://media.printables.com/"   # + filePath  ->  tam gorsel URL'si

# Yedek parca vitrinine UYMAYAN gurultu (thing-ara.py ile ayni liste — birlikte guncelle).
# LOGO + MERCH: marka logosu/amblemini biz baskiyla URETEN urunler — telif/marka hakki riski
# nedeniyle POPULERLIK BILE DELMEZ, her zaman elenir (Okan, 2026-07-14). Ilke: logonun kaynak
# gorselinde gorunmesi degil, logoyu BASKIYLA uretmemiz sorunludur; bu yuzden logo-tasiyan
# aksesuar/merch formlari (anahtarlik/duvar-askisi/plaket/trofe...) da hep elenir.
# NOT: cok-dilli terimler eklendi (kacan yabanci basliklar: Llavero, Schlusselanhanger, ecusson).
# Model-adi CAKISMASI olanlar bilerek DISARIDA (Opel "Insignia", Suzuki "Escudo" -> gecerli parca).
COP_LOGO = (
    # cok dilli logo/amblem/rozet
    "logo", "logos", "emblem", "emblems", "emblema", "embleme", "emblème",
    "badge", "nameplate", "name plate", "symbol", "monogram", "logotipo",
    "ecusson", "écusson", "insigne", "blason", "abzeichen", "wappen",
    "stemma", "distintivo", "amblem",
    # markaya ozel sembol adlari (metinde gecerse logo demektir)
    "roundel", "hood ornament", "prancing horse", "trident", "pentastar",
    # 2026-08-04 EKLENDI (curutme bulgusu): logoyu HALK DILIYLE adlandiran basliklar
    # eksikti. Buraya YALNIZ TEK ANLAMLI (cok kelimeli/yabanci) sembol adlari girer —
    # bunlar global eler ve mesru parca adiyla CAKISMAZ (olculdu: katalogda 0 yanlis-pozitif).
    # Tek kelimelik BELIRSIZ sembol adlari (star/shield/propeller/wings...) bilerek
    # BURAYA KONMADI -> COP_SEMBOL_ADI, yalniz duvar-susu baglaminda.
    "four rings", "three pointed star", "three-pointed star", "cavallino",
    "winged b", "quadrifoglio", "scudetto", "chevron logo",
    # 2026-08-04 (2. curutme turu, B2): ayni olcutle atlanmis 13 sembol adi. Kapi
    # "listede OLMAYAN sembol adi + kanit sozcugu" ile 75 denemede 70 kacak olctu.
    # Bunlar da TEK ANLAMLI: 13'unun de KATALOG VURUSU 0 (18.080 kayit, baslik+aciklama
    # tarandi) -> global elemeleri mesru urunu vurmaz. Belirsizler (star 156, bull 14,
    # shield 6) BILEREK baglamda kalir; "propeller" katalogda 0 olsa da EN metinde
    # gercek marin parca adi (pervane) oldugu icin global'e ALINMADI.
    "bowtie", "bow tie", "biscione", "scorpion", "pleiades", "blitz",
    "coat of arms", "leaper", "ram head", "three diamonds", "winged arrow",
    "tri shield", "prancing pony",
)
# Marka markasini SERGILEYEN/tasiyan aksesuar-merch formlari — logo reprodüksiyonu sayilir,
# POPULERLIK DELMEZ (cok dilli anahtarlik + duvar susu/plaket/trofe/rozet).
COP_MERCH = (
    "keychain", "key chain", "keychains", "keyring", "key ring", "keyfob", "key fob",
    "keytag", "key tag", "keyholder", "key holder", "keyhanger", "key hanger",
    "llavero", "porte-cle", "porte cle", "porte-clef", "porte-cles", "porte cles",
    "porte-clé", "porte-clés", "porte clé", "porte clés", "porte-clefs",
    "schlusselanhanger", "schluesselanhanger", "schlüsselanhänger",
    "portachiavi", "chaveiro", "anahtarlik",
    "wall hanging", "wall plaque",
    "plaque", "trophy", "ornament", "pendant", "charm",
    "letters", "lettering", "sticker", "coaster", "fridge magnet", "magnet", "keycap",
)
# KOSULLU merch (duvar susu): VARSAYILAN **ELE** — supheli olan REDDEDILIR. Yalniz metinde
# POZITIF SILUET KANITI varsa (ve logo/wordmark/sembol sinyali YOKSA) gecer.
#
# 🔴 NEDEN BOYLE (curutuldu, 2026-08-04): once bu terimleri "logo/wordmark sinyali varsa ele,
#    yoksa gecir" diye gevsettim. O hal kapiyi FAIL-CLOSED'dan FAIL-OPEN'a cevirdi: logoyu
#    HALK DILIYLE adlandiran basliklar (Audi rings / Mercedes star / Peugeot lion /
#    Ferrari cavallino / Porsche crest / BMW propeller ...) base'de ELENIYORDU, gevsetmede
#    ELENMIYORDU — 15/19 baslik sizdi. Mekanizma: "wall art" kosulsuz elerken COP_LOGO'nun
#    EKSIKLIGI yuk tasimiyordu; gevsetme butun yuku o eksik listeye devretti.
#    LISTE KOVALAMAK cozum DEGIL (her marka icin ayri sembol adi = sonsuz yaris) ->
#    varsayilan RED'e donduruldu, gevsetme POZITIF KANITA baglandi.
#   🚫 POLITIKA (Okan, 2026-07-20) baglayici: baskida LOGO/wordmark tasiyan urun EKLENMEZ.
#   ⚠️ IKINCI KATMAN SAYILMAZ: gorsel kapisi BU DEPODA DOGRULANAMIYOR -> "savunma derinligi"
#      kanit degildir; metin kapisi TEK BASINA fail-closed olmak zorunda.
#   ⚠️ "wall decor" LISTEDE OLMAK ZORUNDA: is_merch ALT-DIZE bakar, "wall decoration" metni
#      "wall decor" girdisini de tetikler; eksik birakilirsa kural SESSIZ NO-OP olur.
COP_MERCH_KOSULLU = (
    "wall art", "wall arts", "wall decor", "wall decoration",
)
# POZITIF SILUET KANITI — kosullu duvar-susu sinifinda RED'i YALNIZ bu deler.
# Liste UYDURULMADI: 9 canli Printables sorgusundan 233 benzersiz gercek baslik cekildi,
# duvar-susu terimi gecen 228 baslikta olculen frekans (2026-08-04):
#     silhouette 97 · line art 12 · outline 4 · stencil 1 · side view 1
# ("silouette"/"silhoutte" gibi yanlis yazimlar 0 kez gecti -> listeye ALINMADI.)
# Turkce karsiliklari kendi basliklarimiz icin eklendi.
COP_SILUET_KANITI = (
    "silhouette", "silhouettes", "siluet", "silüet",
    "outline", "line art", "lineart", "stencil", "side view", "profile view",
)
# WORDMARK sinyali: marka ADI'nin HARF olarak basildigini gosteren terimler. COP_LOGO'da
# olmayanlar burada (COP_MERCH'teki "letters"/"lettering" zaten kosulsuz eler).
COP_WORDMARK = (
    "wordmark", "word mark", "typography", "typeface", "schriftzug", "script",
)
# Marka SEMBOLUNU halk diliyle adlandiran sozcukler. YALNIZ kosullu duvar-susu baglaminda
# olculur — GLOBAL COP_LOGO'ya konmaz, cunku tek basina COK GENIS: "propeller" bizim GERCEK
# marin urunumuz (pervane), "shield/star/wings" gercek parca adlari. Baglam disinda global
# eleme yapsalardi mesru urunleri sessizce elerlerdi (olculdu; rapora yazildi).
# Bu katman, siluet KANITI tasiyan ama yine de logoyu adlandiran basligi yakalar:
#   "Audi four rings silhouette wall art" -> KANIT var ama SEMBOL ADI var -> ELE.
COP_SEMBOL_ADI = (
    "rings", "four rings", "star", "stars", "three pointed star", "three-pointed star",
    "lion", "cavallino", "shield", "crest", "propeller", "bull", "wreath",
    "winged b", "wings", "ellipses", "chevron", "chevrons", "scudetto", "quadrifoglio",
)
# Populerlik DELEBILIR gurultu (olcek modeli/minyatur) — cok talep goren biri yine de alinir.
COP_OTHER = ("miniature", "diecast", "die-cast", "diorama", "scale model",
             "1:18", "1:24", "1:32", "1:43", "1:64", "1/18", "1/24", "1/43", "kit card")
COP_FIREARM = (
    "m-lok", "mlok", "magpul", "moe grip", "moe stock", "ctr stock",
    "magwell", "cheek riser", "cheek-riser", "pistol brace", "pistol-brace",
    "picatinny", "handguard", "ar-15", "ar15", "buffer tube",
    "lower receiver", "upper receiver", "pmag",
)
COP = COP_LOGO + COP_MERCH + COP_OTHER + COP_FIREARM

# POPULERLIK: cok talep goren urun (asagidaki esigi asan) COP_OTHER/yasakli olsa bile ALINIR
# ve aramada EN UST onceligi alir. LOGO icin bu istisna GECERSIZ (asagida is_logo ile ayri
# kontrol edilir). (NC lisans esigi de AYRI ve delinmez — yasal kisit.)
POP_DL = 3000        # >= bu kadar indirme  -> populer
POP_LIKE = 400       # >= bu kadar begeni   -> populer


def populer(dl, likes):
    return (dl or 0) >= POP_DL or (likes or 0) >= POP_LIKE


def is_logo(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_LOGO)


def is_wordmark(name):
    """Baslik marka ADININ HARF olarak basildigini gosteren bir sinyal tasiyor mu?"""
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_WORDMARK)


def is_sembol_adi(name):
    """Baslik marka SEMBOLUNU halk diliyle adlandiriyor mu (rings/star/lion/crest...)?
    ⚠️ YALNIZ kosullu duvar-susu baglaminda cagrilir; global eleme icin COK GENIS."""
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_SEMBOL_ADI)


def is_siluet_kaniti(name):
    """Baslik POZITIF siluet kaniti tasiyor mu (silhouette/outline/line art...)?"""
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_SILUET_KANITI)


def is_merch(name):
    """Marka-logolu aksesuar/merch formu mu (anahtarlik/askı/plaket/trofe...)?
    LOGO gibi: populerlik DELMEZ.

    Iki katman:
      * COP_MERCH         -> tek basina eler (kosulsuz).
      * COP_MERCH_KOSULLU -> **VARSAYILAN ELER (fail-closed)**; RED'i yalniz POZITIF SILUET
        KANITI deler, o da logo/wordmark/sembol-adi sinyali YOKKEN.

          'Nissan GTR wall art'                       -> ELENIR (kanit YOK; supheli = RED)
          'Car silhouette wall art - Ford Mustang'    -> GECER  (kanit VAR, sinyal yok)
          'Audi rings wall art'                       -> ELENIR (sembol adi)
          'Audi four rings silhouette wall art'       -> ELENIR (kanit var AMA sembol adi var)
          'Nissan logo wall art' / '... wordmark ...' -> ELENIR

    Sira onemli: once logo/wordmark/sembol (RED kazanir), sonra kanit araniyor."""
    n = " " + (name or "").lower() + " "
    if any(c in n for c in COP_MERCH):
        return True
    if any(c in n for c in COP_MERCH_KOSULLU):
        if is_logo(name) or is_wordmark(name) or is_sembol_adi(name):
            return True                      # logo/wordmark/sembol -> her hal ELE
        return not is_siluet_kaniti(name)    # KANIT yoksa ELE (fail-closed varsayilan)
    return False


def is_firearm(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_FIREARM)


def is_nobypass(name):
    """Populerligin DELEMEDIGI eleme: logo/amblem VEYA marka-merch formu."""
    return is_logo(name) or is_merch(name) or is_firearm(name)


_HDRS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Origin": "https://www.printables.com",
    "Referer": "https://www.printables.com/",
}


def gql(query, variables=None):
    """GraphQL sorgusu calistir, `data`'yi dondur (hata varsa exception)."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers=_HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    if d.get("errors"):
        raise RuntimeError(d["errors"][0].get("message", "GraphQL hata"))
    return d["data"]


def img_url(file_path):
    return MEDIA + file_path.lstrip("/")


def is_cop(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP)


def satilabilir(abbr):
    """Lisans kisaltmasi ticari satisa uygun mu? BEYAZ LISTE / FAIL-CLOSED: SADECE bilinen
    ticari-satilabilir lisanslar True doner; tanimadigimiz her lisans False (yanlis satmaktansa
    atla). Eski hali FAIL-OPEN idi ("Standard Digital File" ve bilinmeyen lisanslar True donuyordu)
    -> satilamaz urunler otomatik stage'e giriyordu (Ford+Yamaha partileri, 2026-07-18).

    Printables API'nin DONDURDUGU gercek `abbreviation` degerleri (2026-07-18 canli olcum):
      SATILABILIR : CC-BY, CC-BY-SA, CC-BY-ND, CC0, GPL 3.0, GPL 2.0, LGPL, BSD
      SATILAMAZ   : CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND, "Standard Digital File", "OCL v1"
    Not: GPL surumleri BOSLUK ile gelir ("GPL 3.0", tire degil); ayirici hem '-' hem bosluk.

    Kurallar:
      * NC (NonCommercial) tokeni varsa -> False (guvenlik agi; beyaz liste zaten elerdi).
      * CC0 / Public Domain -> True.
      * CC-BY aileleri (NC haric): CC-BY, CC-BY-SA, CC-BY-ND -> True.
      * Yazilim lisanslari GPL / LGPL / MIT / BSD -> True.
      * "Standard Digital File" (Printables satis-lisansi), "OCL v*" (Prusa Open Community License;
        uretilen urunun satisi ayri anlasma olmadan yasak — prusa3d.com/OCL_v1.pdf), bos, ve
        BASKA HER SEY -> False (fail-closed)."""
    a = (abbr or "").upper().strip()
    if not a:
        return False
    toks = set(re.split(r"[-\s]+", a))        # "CC-BY-NC-SA"->{CC,BY,NC,SA}; "GPL 3.0"->{GPL,3.0}
    if "NC" in toks:                          # NonCommercial -> asla satilamaz
        return False
    if "CC0" in toks or "PUBLIC" in toks:     # CC0 / Public Domain
        return True
    if "CC" in toks and "BY" in toks:         # CC-BY, CC-BY-SA, CC-BY-ND (NC yukarida elendi)
        return True
    if toks & {"GPL", "LGPL", "MIT", "BSD"}:  # ticari-serbest yazilim lisanslari
        return True
    return False                              # Standard Digital File, OCL, bilinmeyen -> FAIL-CLOSED


def tr_lower(s):
    """Turkce-duyarli kucuk harf: 'I'->'ı', 'İ'->'i', sonra lower().
    Python str.lower() 'I'->'i' (yanlis) ve 'İ'->'i̇' (birlesik nokta) uretir; marka
    kelime-siniri karsilastirmasi icin once bu duzeltme sart.

    ⚠️ BU FONKSIYON TURKCE METIN ICINDIR ve DEGISMEZ: denetim-kapisi.py /
    yayin-ic-dil-kapisi.py Turkce govde tarar, 'I'->'ı' orada DOGRU davranistir.
    Yabanci (latin) marka adi kacagi icin ayri katlama vardir -> latin_lower()."""
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def latin_lower(s):
    """YABANCI (latin) kucuk harf: 'İ'->'i', gerisi Python varsayilani ('I'->'i').

    Neden ayri: tr_lower 'I'->'ı' cevirir; bu Turkce metinde dogru, ama TUMU-BUYUK
    yazilmis LATIN marka adinda YANLIS -> 'NISSAN' -> 'nıssan' olur ve 'nissan' ile
    eslesmez (canlida IKI KEZ olculdu: Nissan x MakerWorld ve Nissan x Printables
    hasatlari, 2026-08-04). 'İ'->'i' burada da elle yapilir; cunku Python'un
    'İ'.lower() cevabi 'i'+U+0307 (birlesik nokta) olup kelime eslesmesini bozar."""
    return (s or "").replace("İ", "i").lower()


def marka_katlamalari(marka):
    """Bir marka adi icin denenecek (katlanmis_marka, katlama_fonksiyonu) ciftleri.

    TEK KAYNAK: marka eslesmesi yapan HER arac (marka_kelime_gecer, makerworld-ara
    marka_geciyor, ...) katlama kuralini buradan alir — ikiz tanim sessizce ayrismasin.

    KURAL (dar tutuldu, serbest metne UYGULANMAZ):
      * Her zaman Turkce katlama (tr_lower) denenir.
      * EK OLARAK latin katlama (latin_lower) SADECE marka adi Turkce'ye ozgu nokta
        ayrimini TASIMIYORSA denenir; yani ham marka adinda 'ı' ya da 'İ' YOKSA.
        'nissan'/'mini'/'fiat' -> latin katlama da denenir (TUMU-BUYUK baslik yakalanir).
        'ışık'/'İzmir'        -> SADECE Turkce katlama; I/ı ayrimi KORUNUR.
    Boylece 'kısa kollu' basligi 'kisa' markasiyla HALA eslesmez (iki katlamada da
    ı != i); yani duzeltme "aksani soy" degildir, yalnizca I/i belirsizligini acar.

    ⚠️ Katlanmis marka adlari AYNI ciksa bile ikinci cift ATILMAZ: eslesme METNI de
    katlar, ve fark METINDE dogar ('nissan'=='nissan' ama 'NISSAN'->'nıssan' vs
    'nissan'). Ihtiyacsiz sanip dedup eklemek kusuru geri getirir (bu turda olculdu)."""
    ham = marka or ""
    ciftler = [(tr_lower(ham).strip(), tr_lower)]
    if "ı" not in ham and "İ" not in ham:
        ciftler.append((latin_lower(ham).strip(), latin_lower))
    return ciftler


def marka_kelime_gecer(baslik, marka):
    r"""Baslikta MARKA TAM KELIME olarak (\bMARKA\b, Turkce-duyarli, buyuk/kucuk duyarsiz)
    geciyor mu? Amac: marka aramasinda ALT-DIZE gurultusunu kaynakta elemek.

      'Ford'  -> 'Ford Focus konsol' GECER; 'Oxford box'/'afford'/'Food tray' ELENIR.
      'NISSAN GTR' + 'nissan' -> GECER (latin katlama; bkz. marka_katlamalari).

    marka bos ya da <2 karakterse filtre UYGULANMAZ (True doner) — asiri eleme onlenir.
    Turkce harfler (ç ş ğ ı ö ü) Unicode modda \w oldugundan \b sinirlari dogru calisir."""
    ciftler = marka_katlamalari(marka)
    if len(ciftler[0][0]) < 2:
        return True
    for m, katla in ciftler:
        if re.search(r"\b%s\b" % re.escape(m), katla(baslik), re.UNICODE):
            return True
    return False


def model_url(pid, slug=None):
    return "https://www.printables.com/model/%s%s" % (pid, ("-" + slug) if slug else "")


def cc_turu(abbr):
    """Lisans kisaltmasindan urunler.json 'lisans.tur' degeri (atif icin). Atif gerekmiyorsa None.
    CC0/public domain/GPL/BSD/standart -> None; CC-BY* -> ilgili CC metni."""
    a = (abbr or "").upper()
    if "CC0" in a or "PUBLIC" in a:
        return None
    if a.startswith("CC-BY") or a.startswith("CC BY"):
        if "SA" in a.split("-"):
            return "CC BY-SA 4.0"
        if "ND" in a.split("-"):
            return "CC BY-ND 4.0"
        return "CC BY 4.0"
    return None


# --- PARCA (bagli bilesen) ayrimi -> TEK KAYNAK: tools/olcu_parca.py ----------
# 🔴 OLCU EN BUYUK PARCA UZERINDEN verilir (dosya bbox'i DEGIL). Hukum, olculen
# gerekce (canli onbellekte cok-parcali dosya %20,2; sapma ort. %21,8 / en kotu
# %70,6) ve algoritma `tools/olcu_parca.py` bas yorumundadir. Buraya IKINCI GOVDE
# YAZILMAZ: K287'de saglik hukmunun alti kopyasi "AYNI karar" diye iddia ederken
# sessizce ayrismisti; nobetcisi tools/olcu-en-buyuk-parca-test.py TEK KAYNAK kolu.
en_buyuk_parca_boyu = olcu_parca.en_buyuk_parca_boyu


def stl_bbox(path):
    """STL dosyasinin sinir kutusu olcusu (mm, buyukten kucuge, tam sayi liste) ya da None.
    HTML/bozuk dosyalari eler. Binary STL BIRIM BEYANI TASIMAZ -> en buyuk boyut belirsiz-birim
    bolgesindeyse (< 2 birim) olcu KAYNAK-DOGRULANAMAZ; uydurma yerine None doner (fail-closed).

    OLCU EN BUYUK PARCA UZERINDEN verilir (bkz `_parca_kutulari` bas notu): bir .stl
    icinde tabla dizilmis birden cok govde varsa dosya-bbox'i URUNUN olcusu DEGILDIR."""
    with open(path, "rb") as f:
        data = f.read()
    head = data[:512].lstrip().lower()
    if head.startswith(b"<") or b"<html" in head or b"just a moment" in head:
        return None
    xs, ys, zs = [], [], []
    # BINARY-ONCE tespit: aritmetik kesin, "solid" basligina GUVENME. Binary STL =
    # 80 bayt baslik + uint32 ucgen sayisi (n) + n*50 bayt govde. n>0 VE len==84+n*50
    # TAM eslesirse header'da duz metin "solid ..." (Fusion360/SolidWorks export) olsa
    # DA binary parse et -- boylece binary cop ASCII sanilip sessizce yanlis bbox uretmez.
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if n > 0 and 84 + n * 50 == len(data):
            off = 84
            for _ in range(n):
                if off + 48 > len(data):
                    break
                v = struct.unpack("<12f", data[off:off + 48]); off += 50
                for j in range(3, 12, 3):
                    xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    # Binary degilse ASCII yolu (DEGISMEDEN): "vertex" satirlarindan koordinat topla.
    if not xs and (b"vertex" in data[:2000] or data[:5].lower() == b"solid"):
        for line in data.decode("utf-8", "ignore").splitlines():
            p = line.strip().split()
            if len(p) == 4 and p[0] == "vertex":
                try:
                    xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
                except ValueError:
                    pass
    if not xs:
        return None
    d = sorted(en_buyuk_parca_boyu(xs, ys, zs, kaynak=path), reverse=True)
    # SAGLIK HUKMU tools/olcu_saglik.py'de (kucuk uc = belirsiz birim · buyuk uc = orta
    # boyut tavani). STL birim beyani TASIMAZ -> birim_beyanli=False.
    return olcu_saglik.suz(d)


# 3MF spec'i birim serbest birakir; olcuyu mm'ye cevirmek icin carpan.
# unit yoksa spec varsayilani millimeter.
_3MF_BIRIM_MM = {"micron": 0.001, "millimeter": 1.0, "centimeter": 10.0,
                 "inch": 25.4, "foot": 304.8, "meter": 1000.0}

# 4x4 birim matris (satir-vektor bilesigi icin notr eleman).
_3MF_BIRIM_MAT = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]


def _yerel(tag):
    """ElementTree '{namespace}tag' -> 'tag' (namespace-bagimsiz karsilastirma icin)."""
    return tag.rsplit("}", 1)[-1]


def _oznitelik(el, ad):
    """Namespace onekli/oneksiz oznitelik degeri ( or. production ext'teki p:path)."""
    v = el.get(ad)
    if v is not None:
        return v
    for k, val in el.attrib.items():
        if k.rsplit("}", 1)[-1] == ad:
            return val
    return None


def _matris(metin):
    """3MF transform ozniteligi -> 4x4 matris. 12 sayi satir-major afin: m00 m01 m02
    m10 m11 m12 m20 m21 m22 m30 m31 m32 (son uc = oteleme). Hatali/eksikse None."""
    s = (metin or "").split()
    if len(s) != 12:
        return None
    try:
        m = [float(x) for x in s]
    except ValueError:
        return None
    return [[m[0], m[1], m[2], 0.0],
            [m[3], m[4], m[5], 0.0],
            [m[6], m[7], m[8], 0.0],
            [m[9], m[10], m[11], 1.0]]


def _carp(A, B):
    """4x4 bileske (satir-vektor gelenegi: once A sonra B uygulanir)."""
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _uygula(M, x, y, z):
    """[x y z 1] @ M -> (x', y', z') (3MF'de noktalar satir-vektor)."""
    return (x * M[0][0] + y * M[1][0] + z * M[2][0] + M[3][0],
            x * M[0][1] + y * M[1][1] + z * M[2][1] + M[3][1],
            x * M[0][2] + y * M[1][2] + z * M[2][2] + M[3][2])


def bbox_3mf(path):
    """3MF sinir kutusu olcusu (mm, buyukten kucuge liste) ya da None — STL yoksa yedek olcum.

    Bambu-Studio tarzi cok-.model arsivlerinde geometri 3D/Objects/*.model altindadir; kok
    3D/3dmodel.model yalniz montaj (build item + component referanslari) tutar, vertex icermez.
    Bu yuzden arsivdeki TUM .model uyeleri parse edilir, (dosya, object id) -> element haritasi
    kurulur, <build> item'larindan baslayip component zincirini (p:path ile baska .model'e
    referans + transform matrisleri) coza coza DONUSTURULMUS vertex'lerin birlesik min/max'i
    alinir. build/item yoksa ya da cozum bir seye ulasamazsa tum .model'lerdeki HAM vertex'lerin
    (transform'suz) birlesigine duser. Cikti her zaman MM (dosya birimi ne olursa olsun)."""
    try:
        modeller = {}   # normalize yol (bas '/' yok) -> ET root
        with zipfile.ZipFile(path) as z:
            adlar = [n for n in z.namelist() if n.lower().endswith(".model")]
            if not adlar:
                return None
            for n in adlar:
                try:
                    modeller[n.lstrip("/")] = ET.fromstring(z.read(n))
                except ET.ParseError:
                    pass
        if not modeller:
            return None

        def _build_el(root):
            for ch in root:
                if _yerel(ch.tag) == "build":
                    return ch
            return None

        # Birim: kok modelin (build item'i olan) unit'i — spec model-genelinde tanimli.
        # Okumazsan metre 1000x kucuk cikar, inch/cm MAKUL GORUNEN ama yanlis sayi uretir.
        kok = None
        for root in modeller.values():
            b = _build_el(root)
            if b is not None and list(b):
                kok = root
                break
        if kok is None:
            kok = next(iter(modeller.values()))
        bm = kok.get("unit") or "millimeter"
        carpan = _3MF_BIRIM_MM.get(bm.lower())
        if carpan is None:
            return None                  # tanimadigimiz birim -> uydurma, olcusuz birak

        # her .model icin object id -> element haritasi
        objeler = {}
        for yol, root in modeller.items():
            h = {}
            for obj in root.iter():
                if _yerel(obj.tag) == "object" and obj.get("id") is not None:
                    h[obj.get("id")] = obj
            objeler[yol] = h

        xs, ys, zs = [], [], []
        # 🔴 PARCA AYRIMI (2026-09-03): 3MF'de yapisal parca birimi <build><item>'dir —
        # tabla dizilmis her govde ayri bir item'dir. Her item'in bbox'i AYRI tutulur ve
        # olcu EN BUYUK item'dan verilir; eskiden TUM item'larin BIRLESIK min/max'i
        # aliniyordu, yani "tabla olcusu" urunun olcusu diye yaziliyordu.
        # 🔴 BEYAN EDILEN SINIR: bir item'in ICINDE hala birden cok kopuk govde olabilir;
        # item-ici bagli-bilesen ayrimi YAPILMAZ (3MF yolunda ucgen indisleri toplanmiyor,
        # yalniz vertex'ler). STL/OBJ yolunda ayrim bilesen duzeyindedir. Bu sinir bilinerek
        # birakildi: item duzeyi 3MF'in KENDI parca modelidir, tahmin degil.
        item_kutulari = []

        def _vertices_el(obj):
            for ch in obj:
                if _yerel(ch.tag) == "mesh":
                    for gch in ch:
                        if _yerel(gch.tag) == "vertices":
                            return gch
            return None

        def _coz(yol, oid, M, derinlik):
            if derinlik > 50:            # dongusel referansa karsi tavan
                return
            obj = objeler.get(yol, {}).get(oid)
            if obj is None:
                return
            vs = _vertices_el(obj)
            if vs is not None:
                for vx in vs:
                    if _yerel(vx.tag) != "vertex":
                        continue
                    try:
                        x = float(vx.get("x")); y = float(vx.get("y")); z = float(vx.get("z"))
                    except (TypeError, ValueError):
                        continue
                    px, py, pz = _uygula(M, x, y, z)
                    xs.append(px); ys.append(py); zs.append(pz)
            for ch in obj:
                if _yerel(ch.tag) != "components":
                    continue
                for comp in ch:
                    if _yerel(comp.tag) != "component":
                        continue
                    cid = comp.get("objectid")
                    if cid is None:
                        continue
                    cyol = _oznitelik(comp, "path")      # baska .model'e referans olabilir
                    cyol = cyol.lstrip("/") if cyol else yol
                    T = _matris(comp.get("transform")) or _3MF_BIRIM_MAT
                    _coz(cyol, cid, _carp(T, M), derinlik + 1)

        # build item'lardan transform zincirini cozerek dolas
        for yol, root in modeller.items():
            b = _build_el(root)
            if b is None:
                continue
            for item in b:
                if _yerel(item.tag) != "item" or item.get("objectid") is None:
                    continue
                T = _matris(item.get("transform")) or _3MF_BIRIM_MAT
                onceki = len(xs)
                _coz(yol, item.get("objectid"), T, 0)
                if len(xs) > onceki:                      # bu item'in KENDI bbox'i
                    ix, iy, iz = xs[onceki:], ys[onceki:], zs[onceki:]
                    item_kutulari.append((max(ix) - min(ix), max(iy) - min(iy),
                                          max(iz) - min(iz)))

        # geri-dusus: cozum bos donduyse tum modellerin ham vertex'leri (transform'suz)
        if not xs:
            for root in modeller.values():
                for vx in root.iter():
                    if _yerel(vx.tag) != "vertex":
                        continue
                    try:
                        x = float(vx.get("x")); y = float(vx.get("y")); z = float(vx.get("z"))
                    except (TypeError, ValueError):
                        continue
                    xs.append(x); ys.append(y); zs.append(z)
        if not xs:
            return None

        # OLCU EN BUYUK PARCA'dan: build item'i cozulduyse en buyuk HACIMLI item,
        # cozulemediyse (ham-vertex geri-dususu) dosya birlesigi.
        if item_kutulari:
            ham = max(item_kutulari, key=lambda k: (k[0] * k[1] * k[2], k[0]))
        else:
            ham = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        d = sorted([ham[0] * carpan, ham[1] * carpan, ham[2] * carpan], reverse=True)
        # 3MF `unit` BEYAN EDER (carpan yukarida uygulandi) -> belirsiz-birim kolu MUAF.
        return olcu_saglik.suz(d, birim_beyanli=True)
    except Exception:
        return None                      # sozlesme: hicbir durumda firlatma, olcemezsen None


def obj_bbox(path):
    """Wavefront .OBJ sinir kutusu olcusu (mm, buyukten kucuge, tam sayi liste) ya da None.

    Neden var: Printables'ta bazi modeller SADECE .obj tasiyor (olculen gercek kayitlar:
    733167 "Nissan bonnet clip", 196889 "300ZX console blank" — ikisinde de tek dosya .obj).
    Eskiden model_bbox bunlari stl_bbox'a yonlendiriyordu, o da None donuyordu; olcu kapisi
    otomatik olcemiyor, ELLE kurtariliyordu (2026-08-04).

    Bicim: 'v X Y Z [W]' satirlari koordinattir. 'vt' (doku) ve 'vn' (normal) satirlari
    koordinat DEGILDIR ve sayilmaz — ilk jeton TAM 'v' olmali.

    stl_bbox ile AYNI fail-closed korumalari — ve 25 Agu 2026'dan beri "ayni" bir IDDIA
    degil, TEK KAYNAK: saglik hukmu `tools/olcu_saglik.py`den gelir (K287; kopyalanan
    esiklerin sessizce ayrismasi orada olculdu).
      * HTML/hata sayfasi -> None
      * OBJ de BIRIM BEYANI TASIMAZ -> belirsiz-birim kolu UYGULANIR (x1000 tahmini YOK)"""
    with open(path, "rb") as f:
        data = f.read()
    head = data[:512].lstrip().lower()
    if head.startswith(b"<") or b"<html" in head or b"just a moment" in head:
        return None
    xs, ys, zs = [], [], []
    yuzler = []                              # PARCA ayrimi icin: her yuzun vertex indisleri
    for line in data.decode("utf-8", "ignore").splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v" and len(p) >= 4:      # 'vt'/'vn' TAM esitlikle elenir
            try:
                xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
            except ValueError:
                continue
        elif p[0] == "f" and len(p) >= 4:
            # 'f v', 'f v/vt', 'f v//vn', 'f v/vt/vn' — ilk alan vertex indisi.
            # OBJ indisleri 1-tabanli; NEGATIF indis dosya sonundan geriye sayar.
            idx = []
            for jeton in p[1:]:
                try:
                    i = int(jeton.split("/")[0])
                except ValueError:
                    idx = []
                    break
                idx.append(i)
            if len(idx) >= 3:
                yuzler.append(idx)
    if not xs:
        return None
    # 🔴 OLCU EN BUYUK PARCA UZERINDEN (stl_bbox ile AYNI hukum, ayni yardimci).
    # OBJ'de parca = `f` yuzleriyle birbirine bagli vertex kumesi. Yuz satiri YOKSA
    # (salt nokta bulutu) parca ayrimi yapilamaz -> dosya-bbox'i AYNEN korunur.
    if yuzler:
        n = len(xs)
        ucgen_x, ucgen_y, ucgen_z = [], [], []
        for idx in yuzler:
            coz = []
            for i in idx:
                j = (i - 1) if i > 0 else (n + i)      # negatif indis: sondan geri
                if 0 <= j < n:
                    coz.append(j)
            for k in range(1, len(coz) - 1):           # yuz -> ucgen yelpazesi
                for j in (coz[0], coz[k], coz[k + 1]):
                    ucgen_x.append(xs[j]); ucgen_y.append(ys[j]); ucgen_z.append(zs[j])
        if ucgen_x:
            d = sorted(en_buyuk_parca_boyu(ucgen_x, ucgen_y, ucgen_z, kaynak=path),
                       reverse=True)
            return olcu_saglik.suz(d)
    d = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)
    return olcu_saglik.suz(d)


def model_bbox(path):
    """Uzantiya gore doğru olcum fonksiyonuna yonlendirir (.stl / .3mf / .obj)."""
    p = path.lower()
    if p.endswith(".3mf"):
        return bbox_3mf(path)
    if p.endswith(".obj"):
        return obj_bbox(path)
    return stl_bbox(path)


def strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "", flags=re.I)
    s = re.sub(r"</p>", "\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


SEARCH_Q = """
query S($q: String!, $limit: Int!, $offset: Int, $ordering: SearchChoicesEnum, $licenses: [ID]) {
  searchPrints2(query: $q, limit: $limit, offset: $offset, ordering: $ordering, licenses: $licenses) {
    totalCount
    items {
      id name slug downloadCount likesCount ratingAvg filesCount imagesCount
      license { name abbreviation }
      user { publicUsername }
      image { filePath }
    }
  }
}
"""

DETAIL_Q = """
query D($id: ID!) {
  print(id: $id) {
    id name slug summary description
    license { name abbreviation }
    user { publicUsername }
    filesCount imagesCount downloadCount likesCount ratingAvg thingiverseLink
    images { id order filePath }
    stls { id name fileSize }
  }
}
"""


DL_M = """
mutation DL($printId: ID!, $files: [DownloadFileInput], $source: DownloadSourceEnum!) {
  getDownloadLink(printId: $printId, files: $files, source: $source) {
    ok
    errors { field messages }
    output { link ttl count }
  }
}
"""


def search(term, limit=30, offset=0, ordering="popular", licenses=None):
    """Model ara; `licenses` Printables arayuzundeki lisans ID listesidir."""
    variables = {"q": term, "limit": limit, "offset": offset, "ordering": ordering,
                 "licenses": licenses}
    return gql(SEARCH_Q, variables)["searchPrints2"]


def detail(pid):
    return gql(DETAIL_Q, {"id": str(pid)})["print"]


def download_link(print_id, file_ids, file_type="stl"):
    """getDownloadLink mutation'i — imzali (24s TTL) indirme URL'si dondurur. Login GEREKMEZ.
    file_ids: tek dosyada tek eleman -> tek dosyanin STL linki; birden fazla -> ZIP paketi."""
    v = {"printId": str(print_id), "source": "model_detail",
         "files": [{"fileType": file_type, "ids": [str(i) for i in file_ids]}]}
    r = gql(DL_M, v)["getDownloadLink"]
    if not r.get("ok"):
        raise RuntimeError("getDownloadLink basarisiz: %s" % (r.get("errors")))
    return r["output"]["link"]


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _HDRS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _is_stl_bytes(blob):
    """Indirilen baytlarin GERCEKTEN STL olup olmadigini dogrular. Printables bazen .stl
    uzantili dosya icin sessizce bir PNG kucuk resim donduruyor (Suzuki partisinde
    yakalandi, 2026-07-16) - bu da olcusuz/yanlis-olculu urun stage edilmesine yol acar.
    ASCII STL: "solid" ile baslar. Binary STL: 80 bayt basligin ardindan gelen uint32
    ucgen sayisi, kalan bayt uzunlugunu (n*50) tam karsilamalidir."""
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return False
    if blob[:5].lower() == b"solid":
        return True
    if len(blob) >= 84:
        (n,) = struct.unpack("<I", blob[80:84])
        if n > 0 and 84 + n * 50 == len(blob):
            return True
    return False


def _is_obj_bytes(blob):
    """Indirilen baytlar GERCEKTEN Wavefront OBJ mi? _is_stl_bytes ile ayni amac: Printables
    bazen .stl/.obj uzantili dosya yerine sessizce PNG kucuk resim donduruyor. OBJ metindir
    ve en az bir 'v X Y Z' kose satiri tasimalidir."""
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return False
    bas = blob[:512].lstrip().lower()
    if bas.startswith(b"<") or b"<html" in bas:
        return False
    metin = blob[:200000].decode("utf-8", "ignore")
    for line in metin.splitlines():
        p = line.split()
        if len(p) >= 4 and p[0] == "v":
            try:
                float(p[1]); float(p[2]); float(p[3])
                return True
            except ValueError:
                continue
    return False


def download_stl(print_id, save_path_noext):
    """Modelin EN BUYUK gercek dosyasini indirir. Tercih sirasi: .stl -> .3mf -> .obj
    (step gibi CAD/baski-disi formatlar alinmaz). save_path_noext + dogru uzanti ile yazar.
    Doner: (gercek_dosya_adi, kaydedilen_yol, bayt_uzunlugu). Uygun dosya yoksa RuntimeError.

    .obj EN SONA konur, cunku .stl/.3mf dilimleyiciye dogrudan girer; .obj yalnizca OLCU
    kapisini besleyebilsin diye kabul edilir. Eskiden .obj tumden reddediliyordu ve tek
    dosyasi .obj olan gercek kayitlar (733167, 196889) elle kurtariliyordu (2026-08-04)."""
    d = detail(print_id)
    files = d.get("stls") or []
    stls = [s for s in files if (s.get("name") or "").lower().endswith(".stl")]
    threemf = [s for s in files if (s.get("name") or "").lower().endswith(".3mf")]
    objs = [s for s in files if (s.get("name") or "").lower().endswith(".obj")]
    pool = stls or threemf or objs
    if not pool:
        raise RuntimeError("bu modelde .stl/.3mf/.obj yok (sadece step/cad olabilir)")
    pool.sort(key=lambda s: s.get("fileSize") or 0, reverse=True)  # en buyuk = ana parca
    chosen = pool[0]
    ext = ".stl" if stls else (".3mf" if threemf else ".obj")
    save_path = save_path_noext + ext
    link = download_link(print_id, [chosen["id"]], "stl")
    blob = http_get(link)
    if ext == ".stl" and not _is_stl_bytes(blob):
        raise RuntimeError("indirilen dosya STL degil (Printables PNG/baska format donmus olabilir): %s" % chosen["name"])
    if ext == ".obj" and not _is_obj_bytes(blob):
        raise RuntimeError("indirilen dosya OBJ degil (Printables PNG/baska format donmus olabilir): %s" % chosen["name"])
    with open(save_path, "wb") as w:
        w.write(blob)
    return chosen["name"], save_path, len(blob)


if __name__ == "__main__":
    # Hizli duman testi
    r = search("renault", limit=3)
    print("toplam:", r["totalCount"])
    for it in r["items"]:
        print(" ", it["id"], it["license"]["abbreviation"], it["name"][:50])
