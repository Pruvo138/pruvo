# -*- coding: utf-8 -*-
"""Arama metni uretimi — index.html'deki norm() + haystack()'in BIREBIR karsiligi.

Neden ayri dosya: ayni mantik uc yerde lazim (d1-sync.py yazarken, parite testi
dogrularken, Worker /ara sorgularken). Tek kaynak olmazsa uc kopya sessizce
birbirinden ayrilir ve arama sonuclari site ile D1 arasinda ayrisir.

DIKKAT — Turkce buyuk/kucuk harf tuzagi:
  JS  "İ".toLocaleLowerCase("tr") -> "i"
  PY  "İ".lower()                 -> "i" + U+0307 (birlesik nokta) — FARKLI!
  JS  "I".toLocaleLowerCase("tr") -> "ı" (sonra norm onu "i" yapar)
  PY  "I".lower()                 -> "i"
Bu yuzden lower()'dan ONCE I/İ elle cevrilir. Dogrulugu varsayima birakilmadi:
tools/parite-test.js (referansi index.html'in GERCEK kodu olan test) bu ciktiyla
uretilmis D1 indeksini sitenin sonucuyla karsilastirir — burada bir harf kaysa
test kirmizi yanar.
"""

import copy
import hashlib
import json
import os
import re
import unicodedata

_INDEX_YOLU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")


ARAC_ES_ANLAMLI = None
ARAC_ES_ANLAMLI_SINIR = None
_ARAC_ES_ANLAMLI_TAM_JETON = None
# None=henüz denenmedi, True=yüklendi, False=fail-closed. Bu bayrak yükleme
# arızasını görünür kılar; False olduktan sonra aynı koşumda tekrar denenmez.
_ARAC_ES_ANLAMLI_YUKLENDI = None


def _arac_es_anlamli_hazirla():
    """Kanonik araç eş anlamlılarını ilk kullanımda bir kez, fail-closed yükle."""
    global ARAC_ES_ANLAMLI, ARAC_ES_ANLAMLI_SINIR
    global _ARAC_ES_ANLAMLI_TAM_JETON, _ARAC_ES_ANLAMLI_YUKLENDI
    if _ARAC_ES_ANLAMLI_YUKLENDI is not None:
        return _ARAC_ES_ANLAMLI_YUKLENDI

    # Yeniden girişte ya da aşağıdaki herhangi bir arızada genişleme kapalı kalsın.
    _ARAC_ES_ANLAMLI_YUKLENDI = False
    try:
        with open(_INDEX_YOLU, encoding="utf-8") as f:
            kaynak = f.read()
        es = re.findall(r'^\s*var ARAC_ES_ANLAMLI = (\[[^\n]+\]);$', kaynak, re.MULTILINE)
        if len(es) != 1:
            raise RuntimeError("ARAC_ES_ANLAMLI tek kanonik literal olmali")
        deger = json.loads(es[0])
        if deger != ["oto", "otomobil", "araba", "arac"]:
            raise RuntimeError("ARAC_ES_ANLAMLI dar sinifi degisti")
        sinirlar = re.findall(
            r'^\s*var ARAC_ES_ANLAMLI_SINIR = "([^"\n]+)";$', kaynak, re.MULTILINE)
        if len(sinirlar) != 1 or not re.fullmatch(r"\[\^[a-z0-9-]+\]", sinirlar[0]):
            raise RuntimeError("ARAC_ES_ANLAMLI_SINIR turetilemez")
        araclar = tuple(deger)
        sinir = sinirlar[0]
        tam_jeton = re.compile(
            r"(^|%s)(?:%s)(?=$|%s)" % (
                sinir, "|".join(re.escape(t) for t in araclar), sinir))
    except (OSError, UnicodeError, ValueError, RuntimeError, re.error):
        return False

    ARAC_ES_ANLAMLI = araclar
    ARAC_ES_ANLAMLI_SINIR = sinir
    _ARAC_ES_ANLAMLI_TAM_JETON = tam_jeton
    _ARAC_ES_ANLAMLI_YUKLENDI = True
    return True

_HARF = str.maketrans({
    "ı": "i", "ç": "c", "ğ": "g", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i",
})


def norm(s):
    """index.html norm() ile birebir ayni ciktiyi verir."""
    if not s:
        return ""
    # toLocaleLowerCase("tr") taklidi: I -> ı, İ -> i (lower()'dan ONCE)
    s = s.replace("İ", "i").replace("I", "ı")
    return s.lower().translate(_HARF)


def haystack(u):
    """Urunun aranabilir metni — index.html haystack() ile birebir ayni."""
    return norm(" ".join([
        u.get("baslik") or "",
        u.get("aciklama") or "",
        " ".join(u.get("marka") or []),
        u.get("kategori") or "",
        (u.get("id") or "").replace("-", " "),
    ]))


def tokenlar(q):
    """Sorguyu index.html ile ayni sekilde parcalara ayirir + Turkce ek kirpma.

    index.html filtered(): norm(query).split().map(aramaKok) ile BIREBIR. arama_kok
    asagida (L88) tanimli; modul seviyesi ad, cagri aninda cozulur (forward-ref sorun degil).
    DIKKAT: haystack()/urun_hash() DEGISMEZ — sadece SORGU tarafi kok alir, D1 kolonu ayni.
    """
    _arac_es_anlamli_hazirla()
    return [ARAC_ES_ANLAMLI if (ARAC_ES_ANLAMLI and t in ARAC_ES_ANLAMLI) else arama_kok(t)
            for t in norm(q).split() if t]


def esles(hs, tokens):
    """Siteyle ayni: arac sinifi tam jeton, diger tokenlar alt-dize eslesir."""
    return all(bool(_ARAC_ES_ANLAMLI_TAM_JETON.search(hs))
               if isinstance(t, tuple) else t in hs for t in tokens)


# SITE /ara D1 SERBEST-METIN SOZLESMESI — TEK KAYNAK.
#
# `tokenlar()` her zaman bir LISTE dondurur. Listenin her elemani normal bir sorgu
# jetonunda DIZE, dar arac es-anlamli sinifinda ise sinifin TAMAMINI tasiyan TUPLE'dir.
# Ornek: `kapilar` -> ["kapi"], `arac` -> [("oto", "otomobil", "araba", "arac")],
# `arabalar` -> ["araba"] (uyelik kok almadan ONCE sinandigi icin tuple degildir).
#
# D1 sorgusunu olcen araclar SQL/tokenizasyon govdesini yeniden yazmaz; asagidaki iki
# fonksiyonu kosar. Boylece token tipi ya da es-anlamli dali degisirse olcum de ayni
# kanonik kaynaktan degisir. `token_sozlesmesi_dogrula()` ayrica donus sekli bozuldugunda
# iki tarafin birlikte sessizce yesil kalmasini engeller.
D1_KART_ALANLARI = (
    "u.id, u.baslik, u.kategori, u.marka, u.fiyat, u.taban_fiyat, u.gorsel,"
    " u.parametrik, substr(u.aciklama, 1, 160) AS aciklama"
)


def token_sozlesmesi_dogrula(q, tokens):
    """`tokenlar(q)` donusunun kanonik dize/tuple sozlesmesini dogrular.

    Donus tipi ya da es-anlamli yuklemesi bozulursa sessiz dar aramaya donmek yerine
    ValueError uretir. Uretim aramasinin fail-open davranisini degistirmez; bu fonksiyon
    yalniz sozlesmeyi olcen kapilar tarafindan cagrilir.
    """
    if not _arac_es_anlamli_hazirla():
        raise ValueError("arac es-anlamli kanonik kaynaktan yuklenemedi")
    if not isinstance(tokens, list):
        raise ValueError("tokenlar(q) liste dondurmeli: %r" % (type(tokens).__name__,))
    hamlar = [t for t in norm(q).split() if t]
    if len(tokens) != len(hamlar):
        raise ValueError("token adedi ayrismasi: ham=%d donen=%d" % (len(hamlar), len(tokens)))
    for ham, gercek in zip(hamlar, tokens):
        beklenen = ARAC_ES_ANLAMLI if ham in ARAC_ES_ANLAMLI else arama_kok(ham)
        if type(gercek) is not type(beklenen) or gercek != beklenen:
            raise ValueError(
                "token sozlesmesi ayrismasi: ham=%r beklenen=%r (%s) donen=%r (%s)" % (
                    ham, beklenen, type(beklenen).__name__, gercek, type(gercek).__name__))
    return True


def _arac_es_anlamli_glob(uye):
    """Padlenmis D1 hs alaninda siteyle ayni tam-jeton sinirini kurar."""
    return "*" + ARAC_ES_ANLAMLI_SINIR + uye + ARAC_ES_ANLAMLI_SINIR + "*"


def d1_site_sql_kur(tokens, limit, birlesim="cross"):
    """Site-modu D1 serbest-metin SQL'ini ve baglarini kanonik tokenlardan kurar.

    `birlesim`: `cross` canli plan civisi, `join` olay/semantik karsilastirmasi,
    `duz` ise pahali JOIN planini kosmadan ayni kosullari `urunler u` uzerinde olcer.
    Uc sekilde de kosul ve bag uretimi TEK govdedir; yalniz FROM sekli degisir.
    """
    if birlesim not in ("cross", "join", "duz"):
        raise ValueError("bilinmeyen D1 birlesim sekli: %r" % birlesim)
    _arac_es_anlamli_hazirla()
    if tokens and not _ARAC_ES_ANLAMLI_YUKLENDI:
        raise ValueError("arac es-anlamli kanonik kaynaktan yuklenemedi")

    if not tokens or birlesim == "duz":
        kaynak = "urunler u"
    elif birlesim == "cross":
        kaynak = "urunler_fts f CROSS JOIN urunler u ON u.rid = f.rowid"
    else:
        kaynak = "urunler_fts f JOIN urunler u ON u.rid = f.rowid"
    f_hs = "u.hs" if birlesim == "duz" else "f.hs"

    kosul, bag = [], []
    for t in tokens:
        if isinstance(t, tuple):
            if t != ARAC_ES_ANLAMLI:
                raise ValueError("bilinmeyen tuple token sinifi: %r" % (t,))
            kosul.append("(" + " OR ".join(f_hs + " LIKE ?" for _ in t) + ")")
            bag.extend("%" + uye + "%" for uye in t)
            kosul.append("(" + " OR ".join(
                "(' ' || u.hs || ' ') GLOB ?" for _ in t) + ")")
            bag.extend(_arac_es_anlamli_glob(uye) for uye in t)
        elif isinstance(t, str):
            kosul.append(f_hs + " LIKE ?")
            bag.append("%" + t + "%")
            if "%" in t or "_" in t:
                kosul.append("instr(u.hs, ?) > 0")
                bag.append(t)
        else:
            raise ValueError("token dize ya da tuple olmali: %r" % (t,))
    kosul.append("u.yayinda = 1")
    nere = " WHERE " + " AND ".join(kosul)
    return (("SELECT " + D1_KART_ALANLARI + " FROM " + kaynak + nere +
             " ORDER BY u.seq DESC LIMIT ?", bag + [limit]),
            ("SELECT COUNT(*) AS n FROM " + kaynak + nere, list(bag)))


# ─────────────────────────────────────────────────────────────────────────────
# MARKA SORGUSU — marka ADIYLA yapilan sorgu SERBEST METNE degil UYELIK yuklemine baglanir.
#
# OKAN HUKMU: "TUM markalarda sayfa ve arama urun adetlerinin ayni olmasi."
# OLCULEN SESSIZ HATA (4 Agu 2026, katalog 18.312 / 128 kanonik marka): `?q=<marka>` kolu
# alt-DIZE aramasi oldugu icin 79 markada sayfadan FAZLA urun gosteriyordu (6.503 kalem):
#   Havalandirma -> "Haval" (575) · Mandali/manuel -> "MAN" (3.531) · 33mm -> "3M" ·
#   iPad mini -> "Mini" · Land Rover -> "Rover" (91).
# Musteri "MAN" yazip 3.520 sonuc goruyordu; MAN marka SAYFASINDA 4 urun var. Iki yuzey de
# kendi icinde tutarli gorunur, kimse hata BILDIRMEZ = sessiz hata.
#
# 🔴 GECIS KURALI (secim (a), OLCUMLE): UYELIK ∪ BASLIKTA TAM KELIME.
#   Saf uyelik (secim (b)) farki 79 marka/6.507 kalem -> 0/0 yapar AMA baslikta markayi TAM
#   KELIME tasiyip `marka[]` uyeligi OLMAYAN 469 urunu (505 kalem) marka sorgusundan DUSURUR:
#   "Sierra 18-7713 Yamaha/Mercury Deniz Motoru Yakit Filtresi" (marka=['Sierra']),
#   "Suzuki TL1000R Telefon/GoPro Tutucu Adaptoru", "BMW uyumlu TomTom Rider Adaptoru".
#   Bunlar GERCEK uyum ve 125'inin HICBIR marka uyeligi YOK — yani saf uyelikte HICBIR marka
#   sorgusuyla bulunamaz olurlardi: "sayilar esitlendi" derken gercek eslesme kaybedilirdi.
#   Bu yuzden baslik kolu geciste ACIK kalir. Olculen kalan fark: 38 marka / 504 kalem
#   (kalem ekseninde %92,3 dusus). Veri tarafi (marka[] tamamlanmasi) ilerledikce erir.
#
# 🔴 KATLAMA GOVDESI BURADA YAZILMAZ: "bu dizge bir MARKA ADI mi" yargisi `kanon` geri
# cagrisiyla DISARIDAN gelir (tek kaynak: marka_model_build.marka_adi_kanonu -> index.html
# markaKatla portu + cip evreni). Ikinci bir katlama tablosu dogsaydi sessizce ayrisirdi
# ([[ikiz-tanim-sessiz-ayrisma]]).
#
# 🔴 ONEK KATLAMASI YOK (uyelik yukleminin AKSINE): `marka[]` alaninda "Volvo Penta" -> Volvo
# katlanir, ama METINDE "Yamaha Mercury" bir marka adi DEGILDIR — onek katlamasi burada
# calissaydi bigram "yamaha mercury" tek basina "Yamaha"ya katlanir ve "Mercury" jetonu
# YUTULURDU. `kanon` bu yuzden TAM AD eslesmesi yapar.

# Kelime siniri: harf/rakam/`+` DISI her sey ayirac. `+` KORUNUR ("Black+Decker" tek jeton
# kalsin); `À-ɏ` Latin aksanlari icindir ("Citroen" yazimi bolunmesin). Ayni sinif
# index.html MARKA SORGUSU blogunda BIREBIR yazilidir (JS `\w` ASCII-only oldugu icin
# `\w` KULLANILMAZ — kullanilsaydi iki taraf aksanli baslikta sessizce ayrisirdi).
_MARKA_KELIME_BOL = re.compile(r"[^a-z0-9+À-ɏ]+")
# Kac kelimelik marka adi taranir: "Alfa Romeo" (2), "Land Rover" (2), "Raspberry Pi" (2).
# Uc, bugunku en uzun kanonik ada gore SECILDI; buyutmek gurultuyu artirir, kucultmek
# cok kelimeli markayi TEK KELIMEYE bolerdi ("Land Rover" -> "Rover" = baska bir marque).
MARKA_BASLIK_AZAMI_KELIME = 3


def marka_sorgu_kanonu(q, kanon):
    """Sorgunun TAMAMI bir markanin adi mi? -> kanonik ad | None.

    `kanon(dizge) -> kanonik ad | None` disaridan gelir (bkz. blok basi).
    "toyota jant kapagi" -> None (karma sorgu SERBEST METIN kalir; mimar siniri).
    """
    return kanon(" ".join((q or "").split()))


def baslik_marka_uyumlari(baslik, kanon):
    """Baslikta TAM KELIME gecen kanonik markalar. EN UZUN ESLESME ONCE, sonra ilerle.

    Uzun-once SART: "Land Rover" basliginda once bigram denenir; bigram tutunca tekil
    "Rover" URETILMEZ. Olculdu (5 Agu, 18.312 urun): uzun-once kurali olmadan 80 kalem daha
    dogardi ve HEPSI "Rover" idi — yani Land Rover urunleri "Rover" sorgusuna sizardi
    (mimarin "farkli marque ayni ad" sinifi). Donen dizide SIRA baslik sirasidir,
    tekrar tekilleslir.
    """
    kel = [w for w in _MARKA_KELIME_BOL.split(norm(baslik or "")) if w]
    uyumlar = []
    i, n = 0, len(kel)
    while i < n:
        vuruldu = 0
        for k in range(min(MARKA_BASLIK_AZAMI_KELIME, n - i), 0, -1):
            kan = kanon(" ".join(kel[i:i + k]))
            if kan:
                if kan not in uyumlar:
                    uyumlar.append(kan)
                vuruldu = k
                break
        i += vuruldu or 1
    return uyumlar


def marka_sorgusu_esler(kanon_marka, uyeler, baslik_uyumlari):
    """GECIS KURALI — TEK GOVDE: urun, marka sorgusuna UYELIK'ten ya da BASLIKTAKI TAM
    KELIME uyumundan eslesir. Iki girdi de kendi TEK KAYNAGINDAN gelir:
      `uyeler`          = marka_model_build.marka_uyelikleri()  (sayfa/cip ile AYNI yuklem)
      `baslik_uyumlari` = baslik_marka_uyumlari()               (yukarida)
    Bilerek AYRI iki kaynak: ikisi de ayni fonksiyondan turetilseydi olcum totoloji olurdu.
    """
    return kanon_marka in (uyeler or ()) or kanon_marka in (baslik_uyumlari or ())


# ─────────────────────────────────────────────────────────────────────────────
# EGE TARAFI (FAZ 2) — bot'un urunAra()'si sitenin filtered()'indan BASKA bir arama.
# Site: kati AND + alt-dize + katalog sirasi. Ege: es anlamli gruplar + Turkce ek
# kirpma + cift yonlu onek + baslik/govde SKORU. Ikisi ayri normalizasyon kullanir
# (asagidaki nrm alfanumerik olmayani BOSLUGA cevirir, yukaridaki norm cevirmez) —
# bu yuzden ayri kolonlar; tek kolona bindirmek iki aramayi da sessizce bozardi.
#
# Kaynak: pruvo-bot/worker/src/index.js -> nrm(), aramaKok(), ARAMA_EKLER.
# Ikisi ayrisirsa tools/parite-ege.js kirmizi yanar (referans = o dosyanin GERCEK kodu).

_NRM_HARF = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
_NRM_TEMIZ = re.compile(r"[^a-z0-9]+")


def nrm(s):
    """index.js nrm() ile birebir. DIKKAT: â/î burada BILEREK cevrilmez —
    JS de cevirmiyor, [^a-z0-9] onlari bosluga atiyor. Sadik taklit sart."""
    s = (s or "").replace("İ", "i").replace("I", "i").lower()
    return _NRM_TEMIZ.sub(" ", s.translate(_NRM_HARF)).strip()


def marka_kimlikleri(katalog):
    """`urunler.json`'daki `marka` dizilerinden marka/firma KIMLIGI tasima
    OLASILIGI olan degerleri turet — `Ayna`/`Sehpa` gibi bir urunun
    yaninda TEK BASINA tasinan parca-turu etiketlerini elemek, AMA tekil
    ASIL markayi (`Tekil Firma` gibi tekrarsiz) ve tekrarlanan IKINCIL
    firma adini (`Tekrarlanan Firma` gibi >=2 urunde) korumak icin.

    Kural:
      * bir deger marka/firma kimligi sayilir — ya (a) tek basina marka ise
        (`marka` dizisinde TE deger o urune ait) ya da (b) >=2 urunde gecerse;
      * geri kalan (yalnizca ikincil genel ad olarak 1 urunde gecen) elenir.

    Kullanan:
      * tools/altkategori-kapisi.py::B3  (katalog marka x altkategori jetonu)
      * tools/altkategori-sinifla-test.py::T10a  (izinli kume x katalog marka)
    """
    adet = {}
    tek_basina = set()
    for u in katalog or []:
        if not isinstance(u, dict):
            continue
        degerler = {
            m.strip().lower() for m in (u.get("marka") or [])
            if isinstance(m, str) and m.strip()
        }
        for m in degerler:
            adet[m] = adet.get(m, 0) + 1
        if len(degerler) == 1:
            tek_basina.update(degerler)
    return {m for m, n in adet.items() if n >= 2 or m in tek_basina}


# index.js ARAMA_EKLER — SIRA ONEMLI (uzundan kisaya; ilk eslesen ek kirpilir).
ARAMA_EKLER = [
    "lerimiz", "larimiz", "lerim", "larim", "lerin", "larin", "imiz", "iniz", "umuz", "unuz",
    "leri", "lari", "nin", "nun", "den", "dan", "tan", "ten", "ler", "lar", "yle", "yla",
    "si", "su", "yi", "yu", "ye", "ya", "na", "ne", "de", "da", "te", "ta",
    "in", "im", "un", "um", "i", "u", "e", "a", "m", "n",
]


def arama_kok(w):
    """index.js aramaKok() — kalan kok >= 4 harfse tek geciste ek kirpar."""
    for ek in ARAMA_EKLER:
        if len(w) - len(ek) >= 4 and w.endswith(ek):
            return w[:len(w) - len(ek)]
    return w


def koke_cevir(metin):
    """Metnin HER kelimesini kokune cevirip birlestir.

    Neden: urunAra'da "kok esitligi" (mentesem <-> mentesesi) kelime bazli bir kural.
    Kokleri onceden yazmasak, SQL'de her sorgu icin ~50 aday ek denemek gerekirdi
    (kk+ek kombinasyonlari). Kokler kolonda hazir olunca kural TEK bir tam-kelime
    aramasina iner: instr(' '||hs_x_kok||' ', ' '||kk||' ').
    """
    return " ".join(arama_kok(w) for w in metin.split(" ") if w)


def ege_baslik(u):
    """urunAra titlePost kaynagi: aramaTokenlar(u.baslik)."""
    return nrm(u.get("baslik") or "")


def ege_govde(u):
    """urunAra bodyPost kaynagi — index.js'teki dizi SIRASIYLA ayni."""
    return nrm(" ".join([
        u.get("id") or "",
        u.get("baslik") or "",
        u.get("kategori") or "",
        " ".join(u.get("marka") or []),
        u.get("aciklama") or "",
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# TICARI HAL (tur / stokta) — D1'e giden KANONIK degerler.
#
# NEDEN BURADA (arama.py'de) VE NEDEN KANONIK: bu iki alan hem urun_hash'e girer hem
# D1 kolonuna yazilir. Iki yerde AYRI turetilseydi (biri ham deger, digeri normalize)
# hash "degismedi" derken kolon degisir ya da tersi olur -> satir yeniden yazilmaz ve D1
# SESSIZCE eski hali servis eder. Tek fonksiyon = tek kaynak.
#
# 🔴 FAIL-CLOSED YONU — build.py render_product ile AYNI kural:
#   `tur`: SADECE tam "fiziksel" dizesi HAZIR TICARI MAL demektir. Alan YOK ya da
#   taninmayan bir deger ("3d", "Fiziksel", "", None, 0, dizi...) -> "" = OZEL URETIM
#   (katalogun varsayilani, 15.930 baski urunu). Kural "fiziksel ISE isaretle"dir,
#   "3D ISE isaretle" DEGIL -> `tur`suz urunde regresyon 0.
#
#   `stokta`: UC DEGERLI tam sayi. Ikili (0/1) yapilsaydi "alan hic yok" ile "acikca
#   tukendi" AYNI hucreye duserdi ve iki taraflı zarar verirdi: 0'i "tukendi" okuyan uc
#   15.930 ozel-uretim urununu "STOKTA DEGIL" ilan eder (kataloğun tamami olur),
#   0'i "bilinmiyor" okuyan uc ise GERCEKTEN tukenmis fiziksel urunu satar.
#     -1 STOK_BILINMIYOR  alan YOK. Ozel uretim urunlerin normal hali (stok kavrami
#                         UYGULANMAZ; urun siparis uzerine uretilir). Fiziksel bir urunde
#                         gorulurse VERI EKSIKTIR -> uc taraf STOK VAAT ETMEZ.
#      0 STOK_YOK         alan VAR ama true DEGIL (false ya da TANINMAYAN deger).
#                         "STOKTA DEGIL" olarak sunulur.
#      1 STOK_VAR         alan tam olarak boolean true. Tek "stokta" diyebilen deger.
#   Yani "STOKTA" iddiasi YALNIZ 1'den dogar; taninmayan/eksik hicbir sey 1 uretemez
#   (Okan kurali: siparis kaybetmek yanlis vaatten iyidir).
#
# TIP TUZAGI (bilerek `is True` / `isinstance(bool)`): Python'da `True == 1` ve
# `isinstance(True, int)` -> True. `u.get("stokta") == 1` yazsaydik JSON'daki sayi 1 de
# stokta sayilirdi; asagidaki kimlik testi yalniz GERCEK boolean'i gecirir.
_TUR_FIZIKSEL = "fiziksel"
STOK_BILINMIYOR = -1
STOK_YOK = 0
STOK_VAR = 1
# Uc tarafin "STOKTA" diyebilecegi TEK deger kumesi (kabul testi bunu capa alir).
STOK_VAAT_EDILEBILIR = frozenset({STOK_VAR})


def tur_kanonik(u):
    """D1'e yazilan `tur` degeri: "fiziksel" ya da "" (ozel uretim). Fail-closed."""
    return _TUR_FIZIKSEL if u.get("tur") == _TUR_FIZIKSEL else ""


def stokta_kanonik(u):
    """D1'e yazilan `stokta` degeri: -1 bilinmiyor / 0 stokta degil / 1 stokta."""
    if "stokta" not in u:
        return STOK_BILINMIYOR
    return STOK_VAR if u.get("stokta") is True else STOK_YOK


# ─────────────────────────────────────────────────────────────────────────────
# ALT KATEGORI (`altkategori`) — kategori ICINDEKI daraltma etiketi.
#
# NEDEN BURADA (tur/stokta ile AYNI gerekce): bu alan hem urun_hash'e girer hem D1
# kolonuna yazilir. Iki yerde AYRI turetilseydi hash "degismedi" derken kolon degisir
# (ya da tersi) ve D1 SESSIZCE eski degeri servis ederdi. Tek fonksiyon = tek kaynak.
#
# 🔴 IZINLI KUME DONDURULMUS BIR LISTEDIR, urunler.json'dan HER KOSUMDA YENIDEN
# HESAPLANMAZ. Hesaplansaydi kapi TAUTOLOJIYE duserdi: kataloga giren her yeni deger
# kendini otomatik "izinli" yapardi ve kapi hicbir seyi olcmezdi. Liste ASAGIDAKI
# olcumden dondu ve yalnizca bir mimar ELLE genisletir (genisletme de imza nobetinden
# gecmek ZORUNDA — bkz. altkategori_imza_sebebi).
#
# OLCUM (2026-08-01, 16.067 kayitlik katalog): `altkategori` 134 kayitta dolu, hepsi
# kategori "Marin"; 3 tekil deger; hicbir deger birden fazla kategoride gecmiyor;
# hicbiri katalogun tekil marka adlariyla carpismiyor; ucu de imza nobetinden geciyor.
#
# ⚠️ GENISLETME YOLU (kardes mimar icin): duzelt.py bu kumenin DISINDAKI her degeri
# FAIL-CLOSED reddeder — yani yeni bir altkategori once BURAYA eklenir, sonra kataloga
# yazilir. Toplu ekleme yolu (urun-ekle.py) duzelt.py'den GECMEZ: oradan giren yeni bir
# deger tools/altkategori-kapisi.py A ekseninde CI'yi KIRMIZI yakar (olculdu 1 Agu:
# "Pervaneler" tam olarak boyle geldi, 34 kayit).
#
# GENISLETME (2026-08-01, MIMAR KARARI): kume 3 -> 11 degere cikti. Ilk uc deger
# yukaridaki olcumden geldi; kalan sekizi kardes mimarin bekleyen partileri icin ELLE
# eklendi ve yazimlari mimar tarafindan kanoniklestirildi (dogru Turkce, cogul bicim).
# Bunlar HENUZ katalogda kullanilmiyor (olculdu: 134 dolu kayit, 3 tekil deger) — yani
# izinli kume katalogun ONUNDE gidiyor; bu KASITLI, cunku deger once burada olmadan
# kataloga yazilamiyor. Yeni sekiz degerin hicbiri mevcut kayitlarla carpismiyor
# (olculdu: 0) ve on birinin de imza nobetinden gectigi tek tek dogrulandi.
#
# GENISLETME (2026-08-01, MIMAR KARARI, ikinci tur): kume 11 -> 12; "Elektrik" eklendi.
# SEBEP olculdu: kardes mimarin altkategori backfill'i 636 kayit yazdi ama 30 urun
# KARSILIKSIZ kaldi (atesleme bobini, mars motoru/solenoid, distributor rotoru/kapagi,
# kontak anahtari, role, sensor, silecek motoru) — kumede elektrik grubu YOKTU. Eksik
# olan izinli DEGERDI, kapi degil: ayni deger `--toplu` ile denendiginde duzelt.py
# rc=RC_ALTKATEGORI ile REDDETMIS ve urunler.json BYTE-ESIT kalmisti (fail-closed
# dogru calisiyor). Deger olculdu: imza nobeti temiz (sebep None), katalogun 1.678
# tekil marka adiyla carpisma 0. Katalogta HENUZ kullanilmiyor — deger once burada
# olmadan kataloga yazilamadigi icin bu KASITLI (yukaridaki desen).
#
# GENISLETME (2026-08-02, MIMAR KARARI, ucuncu tur): kume 12 -> 60; 1 kategori -> 6.
# SEBEP olculdu: alt kategori tanimli TEK kategori `Marin`di ve katalogun %94'unde alan
# BOSTU — kategori sayfalari yiginla urunle aciliyor, daraltma yuzeyi YOKTU.
#
# EKSEN (K1, mimar karari): grup adi YER / SISTEM / KULLANIM ALANI adlandirir, SEKIL
# DEGIL. OLCULDU (12.481 Otomobil urunu): sekil ekseni (`Kapaklar`, `Klipsler`,
# `Tutucular`) 60 grup uretiyor, urunlerin %88,99'u BIRDEN FAZLA gruba dusuyor, en buyuk
# grup katalogun %37,37'si — yigilmayi cozmuyor, adini degistiriyor. Yer/sistem ekseni:
# 16 grup, cakisma %24,89, en buyuk grup %13,80. Bu yuzden `Kapaklar ve Tapalar` (Marin,
# 240 ham eslesme), `Kablo ve Klipsler` (188), `Standlar` (Ev, 50), `Telefon Tutucuları`
# (Motosiklet, 85) gibi BICIM adlari — kac urun tasirsa tasisin — kumeye ALINMADI.
# Reddedilen adlarin tamami gerekcesiyle tools/altkategori-sinifla.py ADAYLAR tablosunda
# `SEKIL_RED`/`ELENEN` sinifiyla KAYITLIDIR (bir sonraki tur yeniden tartismasin).
#
# ESIKLER (K4): kategori >=100 urun tasimazsa alt kategori ALMAZ — bugun hak eden 6
# kategori asagidadir; `Ofis` 71 · `Bisiklet` 31 · `Bahçe` 25 · `Tamirat` 25 ·
# `Jeneratör` 23 · `Kamera` 21 · `Skan Art` 17 · `Oyun/Hobi` 15 alt kategori ALMAZ ve bu
# bir EKSIKLIK DEGIL KARARDIR. Grup >=15 urun tasimazsa kumeye GIRMEZ (olculdu ve elendi:
# Elektronik `Mutfak Cihazları` 14 -> `Ev ve Mutfak Cihazları` icinde eritildi;
# Dekorasyon `Bardak Altlıkları` 10, `Kitap Destekleri` 5; Ev `Huniler` 11).
#
# 🔴 MARIN'IN MEVCUT 12 DEGERI BAYT OLARAK KORUNDU (K3): 935 kayit onlari kullaniyor,
# ad degistirmek/silmek veriyi bozar ve kapiyi kirar. Uzerine 5 yeni deger EKLENDI.
# Kume ile tools/altkategori-sinifla.py'nin grup tablosu IKIZDIR ve ayrisirsa
# tools/altkategori-sinifla-test.py KIRMIZI yanar (S ekseni) — kume BURADA tek kaynaktir,
# siniflandirici onun ONUNE GECEMEZ (fail-closed: kume disi ad "" olur).
ALTKATEGORI_IZINLI = {
    "Marin": (
        "Boya - Bakım",
        "Bujiler",
        "Dümen ve Kumanda",
        "Elektrik",
        "Filtreler",
        "Motor Parçaları",
        "Motor Yağları",
        "Pervaneler",
        "Sintine ve Ekipmanları",
        "Soğutma",
        "Tutyalar ve Anotlar",
        "Yakıt Sistemi",
        # ── 2 Agu eki (yukaridaki 12 MIRAS deger AYNEN durur) ──
        "Bağlama Ekipmanları",
        "Güverte ve Donanım",
        "Kano ve Kayak",
        "Montaj Ekipmanları",
        "Olta Ekipmanları",
    ),
    "Otomobil": (
        "Aydınlatma",
        "Ayna ve Silecek",
        "Bagaj ve Taşıma",
        # ── 2 Agu (2. tur) eki: TIP ekseni — bkz. altkategori-sinifla.py K5 ──
        "Bardaklık",
        "Dış Aksam",
        "Kapı ve Cam",
        "Klima ve Havalandırma",
        "Koltuk ve Kemer",
        "Konsol ve Torpido",
        # `Montaj ve Bağlantı` -> ADI DEGISTI (K6): "baglanti" tarafina tabloda tek terim
        # dusmuyordu; olculen icerik montaj/kapak/tutucu/klips/tapa/braket.
        "Montaj Parçaları ve Klipsler",
        "Motor Bölümü",
        # `Multimedya ve Elektronik` -> IKIYE BOLUNDU (K7): iki ayri merkez olculdu.
        "Ses ve Multimedya",
        "Sürüş Kumandaları",
        "Tavan ve Güneşlik",
        "Tekerlek ve Jant",
        "Telefon ve Şarj",
        "Yakıt ve Egzoz",
        "İç Aksam",
    ),
    "Motosiklet": (
        "Aydınlatma",
        "Depo ve Yakıt",
        "Elektrik",
        "Fren ve Süspansiyon",
        "Gidon ve Kumandalar",
        "Grenaj ve Kaporta",
        "Gösterge ve Kokpit",
        # Otomobil ile AYNI ad (ortak etiket ilkesi): rename + bolme burada da uygulandi.
        "Montaj Parçaları ve Klipsler",
        "Motor Bölümü",
        "Sele ve Sehpa",
        "Ses ve Multimedya",
        "Tekerlek ve Aktarma",
        "Telefon ve Şarj",
        "Çanta ve Bagaj",
    ),
    "Dekorasyon": (
        "Bitki ve Saksı",
        "Dekoratif Objeler",
        "Duvar ve Raf",
        "Heykel ve Figür",
        "Mum ve Aydınlatma",
        "Servis ve Sunum",
        "Vazo ve Çiçeklik",
    ),
    "Ev": (
        "Banyo",
        "Duvar ve Askı",
        "Mutfak",
        "Saklama ve Düzen",
    ),
    "Elektronik": (
        "Cihaz Parçaları",
        "Ev ve Mutfak Cihazları",
        "Ses ve Müzik",
    ),
}

# ── IMZA NOBETI (depo PUBLIC) ────────────────────────────────────────────────
# Bu degerler bir TEDARIKCI VITRININDEN OLCULEREK turetiliyor. Deger GENEL bir Turkce
# kategori adi olmali ("astar", "yapistirici" gibi); bir satici katalogundan kopyalandigi
# belli olan etiket — marka/firma adi, alan adi, vitrin adi, urun kodu/SKU oneki —
# tedarikci iliskisini ELE VERIR ve public repoya/siteye/D1'e girmemelidir.
#
# KURAL BEYAZ LISTEDIR (kara liste DEGIL): "sunlar yasak" demek, gorulmemis bir imza
# turunu SESSIZCE gecirirdi. Yalnizca su BICIM kabul edilir; disindaki HER SEY supheli:
#   * yalnizca TURK ALFABESI harfleri + bosluk + '-' + '/'  (q/w/x DAHIL DEGIL: Turkce
#     alfabede yok, yabanci marka adlarinin en ucuz sinyali)
#   * RAKAM YOK (urun kodu / SKU / '2K' tipi satici etiketi)
#   * '.' ':' '&' '@' '_' '®' '™' '©' tirnak/parantez YOK (alan adi, ticari isaret, referans)
#   * en fazla 4 kelime, en fazla 40 karakter (vitrin nav etiketi kisadir; uzun dize
#     kopyalanmis satici basligi sinyalidir)
#   * 2+ harfli TAMAMI BUYUK jeton YOK (SKU oneki / kisaltilmis firma adi sinyali)
# Katalog MARKA listesiyle carpisma ekseni burada DEGIL kapida olculur (bu modul
# urunler.json okumaz) — tools/altkategori-kapisi.py B ekseni.
_ALTKAT_HARF = set("abcçdefgğhıijklmnoöprsştuüvyzABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")
_ALTKAT_AYIRAC = set(" -/")
ALTKATEGORI_AZAMI_UZUNLUK = 40
ALTKATEGORI_AZAMI_KELIME = 4


def altkategori_imza_sebebi(deger):
    """Deger tedarikci kimligi ele verebilecek bir IMZA tasiyor mu?

    Dondurur: sebep metni (SUPHELI) ya da None (jenerik/temiz). Fail-closed —
    taninmayan her sey supheli sayilir.
    """
    if not isinstance(deger, str):
        return "metin degil (%s)" % type(deger).__name__
    d = deger.strip()
    if not d:
        return "bos"
    if len(d) > ALTKATEGORI_AZAMI_UZUNLUK:
        return "cok uzun (%d > %d karakter) — kopyalanmis satici basligi sinyali" % (
            len(d), ALTKATEGORI_AZAMI_UZUNLUK)
    kelimeler = d.split()
    if len(kelimeler) > ALTKATEGORI_AZAMI_KELIME:
        return "cok fazla kelime (%d > %d)" % (len(kelimeler), ALTKATEGORI_AZAMI_KELIME)
    for c in d:
        if c in _ALTKAT_HARF or c in _ALTKAT_AYIRAC:
            continue
        if c.isdigit():
            return "rakam iceriyor (%r) — urun kodu/SKU sinyali" % c
        return "izinsiz karakter (%r) — alan adi/ticari isaret/yabanci harf sinyali" % c
    for k in kelimeler:
        harfli = [c for c in k if c in _ALTKAT_HARF]
        if len(harfli) >= 2 and all(c.isupper() for c in harfli):
            return "TAMAMI BUYUK jeton (%r) — SKU oneki/kisaltilmis firma adi sinyali" % k
    return None


def altkategori_metin(deger):
    """`altkategori` alaninin KANONIK metin bicimi — TEK KAYNAK.

    🔴 BU FONKSIYON ILE altkategori_sebebi ARASINDAKI SOZLESME (olculdu 2026-08-01):
    sebebi() KANONIK OLMAYAN her degeri REDDEDER (asagidaki `d != deger` dali), kanonik()
    ise kabul edilen degeri BU fonksiyondan gecirir. Yani "kataloga yazilan metin" ile
    "D1'e giden metin" ayni fonksiyondan turer ve AYRISAMAZ.

    NEDEN SART (olculen kusur): once `strip()` uyelik testinin ICINDE yapiliyordu, bu
    yuzden ' Elektrik' (bastaki bosluk) KABUL EDILIYORDU (rc=0). duzelt.py kataloga HAM
    degeri (' Elektrik') yazarken altkategori_kanonik D1'e KIRPILMIS degeri ('Elektrik')
    gonderiyordu: urunler.json ile D1 arasinda SESSIZ bir metin farki — site ile Ege ayni
    urunu farkli yazimla gorurdu, hicbir hash/senkron ekseni bunu yakalamazdi.
    """
    if not isinstance(deger, str):
        return ""
    return deger.strip()


def altkategori_sebebi(kategori, deger):
    """(kategori, altkategori) ikilisi gecerli mi? Sebep metni ya da None (gecerli).

    BOS/eksik deger GECERLIDIR: alan opsiyoneldir (katalogun ~%99'unda yok).
    """
    if deger is None:
        return None
    if not isinstance(deger, str):
        return "altkategori metin olmali, %s degil" % type(deger).__name__
    d = altkategori_metin(deger)
    # 🔴 FAIL-CLOSED, SESSIZ DUZELTME DEGIL: bosluklu deger kirpilip kabul EDILMEZ,
    # cagirana REDDEDILDIGI soylenir. Alternatifi (kataloga da kirpilmis degeri yazmak)
    # ayni ayrismayi kapatirdi ama kullanicinin YAZDIGINI sessizce degistirirdi; bu evin
    # cizgisi "sessizce duzeltme, soyle". '   ' (yalniz bosluk) da buraya duser: alani
    # bosaltmak icin '' ya da --alan-sil altkategori kullanilir.
    if d != deger:
        return ("KANONIK DEGIL: %r — bas/son bosluk tasiyor; kanonik bicim %r "
                "(alani bosaltmak icin '' ya da --alan-sil altkategori)" % (deger, d))
    if not d:
        return None
    imza = altkategori_imza_sebebi(d)
    if imza:
        return "IMZA NOBETI: %r — %s" % (d, imza)
    izinli = ALTKATEGORI_IZINLI.get(kategori)
    if not izinli:
        return ("kategori %r icin TANIMLI altkategori YOK — izinli kume: %s"
                % (kategori, ", ".join(sorted(ALTKATEGORI_IZINLI)) or "(bos)"))
    if d not in izinli:
        return ("%r kategori %r icin izinli DEGIL — izinli: %s"
                % (d, kategori, ", ".join(izinli)))
    return None


def altkategori_kanonik(u):
    """D1'e yazilan `altkategori` degeri. FAIL-CLOSED: izinli kumede olmayan /
    imza tasiyan / tipi yanlis her deger "" olur.

    Neden fail-closed (tur_kanonik deseni): .git/hooks/pre-push d1-sync'i push'tan
    ONCE kosar, CI kapisi ise push'tan SONRA. Yani bozuk/sizdiran bir deger kapi
    kirmizi yanmadan ONCE D1'e — oradan da Ege'ye ve musteriye — ulasabilirdi.
    "" yazmak urunu KAYBETTIRMEZ (urun kendi kategorisi altinda bulunur), yalnizca
    alt-filtre etiketini dusurur. Sessiz KALMAZ: tools/altkategori-kapisi.py A/B
    eksenleri ayni degeri KIRMIZI yakar.

    KABUL EDILEN deger icin BU FONKSIYON GIRDIYI AYNEN DONDURUR (altkategori_metin ile
    sebebi() ayni kanonik bicimde anlasir) -> katalog metni ile D1 metni BIREBIR AYNI.
    """
    deger = u.get("altkategori")
    if altkategori_sebebi(u.get("kategori"), deger) is not None:
        return ""
    return altkategori_metin(deger)


# ─────────────────────────────────────────────────────────────────────────────
# UYUM EKSENI (`uyum`) — urunun NEYE UYDUGU. Kategori "urun NE" der, uyum "neye takilir".
#
# NEDEN BURADA (altkategori/tur/stokta ile AYNI gerekce): bu alan ileride hem urun_hash'e
# hem D1 kolonuna girecek. Iki yerde AYRI turetilseydi hash "degismedi" derken kolon
# degisir (ya da tersi) ve D1 SESSIZCE eski degeri servis ederdi. Tek fonksiyon = tek kaynak.
#
# 🔴 BU TURDA TUKETICI YOK — bilerek: urun_hash'e KATILMADI, d1-sema/d1-sync'e kolon
# EKLENMEDI, index.html/build.py'ye DOKUNULMADI. Sozluk once main'e iner, parti SONRA
# yazilir; ters sira fail-closed reddedilir (`Elektrik` kaleminde olculdu).
#
# SEMA (tools/paket-uyum-ekseni.md §2): dizi; her oge
#   {"marka": <KAPALI kumeden, ZORUNLU>, "model": <opsiyonel>, "motor": <opsiyonel>,
#    "yil": [bas, son] ya da [], "oem": <opsiyonel>}
# Alan YOKSA / bos dizi ise kayit UYUMSUZDUR — bu GECERLIDIR, hata degil (16.874 kaydin
# tamami bugun boyle; olculdu: `uyum` dolu kayit = 0).
#
# 🔴 K2 — SUPHE DAIMA "MARKA DEGIL" YONUNE DUSER. Modeli yanlislikla marka saymak
# musteriye SAHTE MARKA SAYFASI uretir (geri alinamaz itibar zarari); markayi yanlislikla
# model saymak yalnizca o sayfayi acmaz (gorunmez, geri alinabilir).
#
# ── K3 BUDAMA (olculdu 2026-08-02, 16.874 kayit / 1.704 tekil `marka` jetonu) ─────────
# Girdi bir ONERIDIR: sinyal tabanli siniflandirma 169 marka / 806 model / 729 belirsiz
# verdi. Uc kume asagida TEK TEK yargilanarak ayrildi ve UCU BIRDEN saklanir; birlesimleri
# ONERININ TAMAMINA esittir (kapi bu aritmetigi CALISTIRARAK dogrular) — boylece budama
# karari denetlenebilir ve elenen bir jeton sessizce geri sizamaz.
#
# OLCULEN DUZELTME: mimarin "169'un icinde Focus/F-150/Fiesta/Golf/E46/Mustang gibi acik
# modeller var" beklentisi ADRESINDE DEGILDI — olculdu, o jetonlarin HICBIRI marka
# onerisinde degil (Focus/F-150/Fiesta/Golf/E46/Mustang/Corsa/Mondeo/Transit/Ranger/
# Maverick = `model`, Tacoma/Sierra = `belirsiz`). 169'daki gercek kirlilik baska tipte:
# jenerik kelimeler, standart kodlari, ikiz yazimlar ve PARCA URETICILERI.
#
# AYIRMA OLCUTU (uygulanabilir, tek cumle): jeton bir EV SAHIBI mi adlandiriyor —
# uretilen parcanin TAKILDIGI arac/tekne/motor/makine/cihaz — yoksa TAKILAN sarf/parcanin
# ureticisi mi? "Bu urun <X> ...'a takilir" anlamli ise UYUM; urunun KENDISI o markanin
# malı ise (buji, tutya, yapistirici, temizleyici, zimpara) URETICI.
UYUM_MARKA_IZINLI = frozenset({
    "Abus", "Alfa Romeo", "Anet", "Apple", "Aprilia", "Arora", "Attwood", "Audi",
    "Aukey", "BMW", "BYD", "Bafang", "Baier", "Bajaj", "Baofeng", "Beneteau", "Bentley",
    "Black and Decker", "Borbet", "Briggs & Stratton", "CFMoto", "Cadillac", "Canon",
    "Chrysler", "Citroen", "Cupra", "DJI", "Dacia", "Daewoo", "Datsun", "Dimplex",
    "Ducati", "Dürkopp Adler", "Einhell", "Fiamma", "Flashforge", "Ford", "GMC",
    "Geely", "Grunhelm", "Haval", "Honda", "Hummer", "Husqvarna", "Huter", "Hyundai",
    "IKEA", "Isuzu", "Itiwit", "Iveco", "Jabsco", "Jaguar", "Jawa", "Jeep",
    "John Deere", "KTM", "Kanuni", "Kayo", "Kazuma", "Kuba", "Kärcher", "Lalizas",
    "Lancia", "Land Rover", "Lifetime", "Line 6", "MAN", "Magic Bullet", "Mahindra",
    "Mariner", "Massey Ferguson", "Mazda", "Mercedes", "Mercury", "Miele", "Mini",
    "Minn Kota", "Mitsubishi", "Mondial", "Motoran", "Motorola", "Moulinex", "NODET",
    "Nikon", "Nissan", "OMC", "ObdEleven", "Old Town", "Opel", "Pelican", "Peugeot",
    "Philips", "Porsche", "Prusa", "Puch", "Pössl", "Quechua", "Quicksilver", "Renault",
    "Rial", "Rover", "Rule", "Ryobi", "Saab", "Saeco", "Scania", "Scarlett", "Seaflo",
    "Seat", "Segway", "Sherwood", "Shimano", "Sigma", "Skoda", "Skyteam", "Sodastream",
    "Speeduino", "SsangYong", "Stihl", "Suzuki", "TMC", "Tesla", "Thermomix", "Tofaş",
    "Tohatsu", "Toyota", "Twin Disc", "Vespa", "Vetus", "Volkswagen", "Volvo",
    "Weinsberg", "Xbox", "Xiaomi", "Yamaha", "Yunteng", "Zelmer", "Zodiac", "Zontes",
    # ── MIMAR ELIYLE EKLENEN (asagidaki UYUM_MARKA_MIMAR_EKI ile AYNI 34 jeton) ──
    # 1. tur: paket §2'nin ornek degerleri.
    "Volvo Penta", "Yanmar",
    # 2. tur, A grubu (17) — arac / tekne / deniz motoru markasi. Heuristik bunlari
    # KACIRMISTI; kok sebep olculdu: ev sahibini "baskin tek partneri var" diye model
    # saniyor (`Vauxhall` 71 kaydin 68'inde `Opel` ile geciyor).
    "Chery", "Chevrolet", "Dodge", "Fiat", "Infiniti", "Jeanneau", "Johnson Pump",
    "Kawasaki", "Kia", "Lamborghini", "Lexus", "Maserati", "Mercruiser", "Scion",
    "Smart", "Subaru", "Vauxhall",
    # 2. tur, B grubu (11) — ev sahibi CIHAZ/EKIPMAN ureticisi (kumedeki DJI/Canon/Prusa
    # ile ayni sinif): bir GoPro aparati GoPro'ya TAKILIR. Adetlerin dusuk olmasi (1-12)
    # olcut DEGIL: sozluk "gecerli mi"yi belirler, "sayfasi acilir mi"yi degil — ikincisi
    # paket §4'teki sayfa acma esigi N'in isidir.
    "Anker", "Garmin", "GoPro", "Kenwood", "Krups", "Pioneer", "Raspberry Pi", "Remis",
    "Rode", "Samsung", "Sony",
    # 3. tur, C grubu (4) — mimar karari 5 Agu 2026. Ayni B grubu sinifi: hepsi bir EV
    # SAHIBI cihaz/ekipman ureticisi, parca ONLARA takilir. Katalogdaki agirlik OLCULDU
    # (18.362 urun; `marka` dizisinde TAM yazimla gecen urun / `uyum[].model` alaninda
    # gecen urun) ve her ad TEK TEK gerekcelendirildi — gerekcesiz giris YOK:
    #   `TomTom`  (marka[] 2 · uyum[].model 2 · baslikta 7) GPS/navigasyon cihazi; aparat
    #             TomTom cihazina TAKILIR (sinif: Garmin ile BIREBIR ayni, o zaten kumede).
    #   `Huawei`  (marka[] 1 · uyum[].model 1 · baslikta 2) telefon/tablet ureticisi; kilif
    #             ve tutucu Huawei cihazina TAKILIR (sinif: Apple/Samsung/Xiaomi ile ayni).
    #   `Stanley` (marka[] 2 · uyum[].model 2 · baslikta 3) el aleti/depolama ureticisi;
    #             adaptor Stanley kutusuna/aletine TAKILIR (sinif: Black and Decker,
    #             Einhell, Ryobi, Husqvarna ile ayni — dordu de zaten kumede).
    #   `Webasto` (marka[] 2 · uyum[].model 2 · baslikta 3) park isiticisi/klima ureticisi;
    #             kumanda-braketi ve kanal parcasi Webasto cihazina TAKILIR (sinif: Dimplex,
    #             Truma-benzeri karavan ekipmani; Remis/Fiamma ile ayni raf).
    # 🔴 KUME KAPALI KALIR: dordu de yalnizca BU kumeye ve UYUM_MARKA_MIMAR_EKI'ne girer,
    # yargilanmis bolumleme (izinli−eki / uretici−eki / elenen) DEGISMEZ -> S2 aritmetigi
    # (UYUM_MARKA_ONERI_SAYISI=169) ve UYUM_MARKA_YARGI_IMZA AYNEN korunur. Dordu de bugun
    # UYUM_MARKA_ELENEN'de DEGIL (olculdu) — yani elenmis bir jeton geri SIZMIYOR.
    "Huawei", "Stanley", "TomTom", "Webasto",
})

# 🔴 ONERI DISINDAN, MIMAR ONAYIYLA eklenen jetonlar. AYRI tutulmalari SART: budama
# aritmetigi (S2) "sozluk = yargilanmis oneri" der; onaysiz bir jeton o esitligi kirar.
# Bu kume, esitligi kiran TEK mesru yoldur ve her uyesi ADIYLA kayda gecer.
#
# K2 NETLESTIRILDI (mimar, 2 Agu): "belirsiz jeton VARSAYILAN olarak modeldir; mimar
# ACIK gerekceyle ev-sahibi marka olarak kabul edebilir." Mutlak degil, VARSAYILAN.
#   `Volvo Penta` (51 kayit, Codex `belirsiz`) — deniz motoru markasi. Okan'in talebindeki
#     iki ornekten biri BIREBIR bu; paket §2 ornegi de buna dayaniyor. Kumede olmamasi
#     amiral kullanim durumunun calismamasi demekti.
#   `Yanmar` (7 kayit, Codex `model`) — deniz motoru markasi, paket §2'nin ikinci ornegi.
# Ikisi de bu turun kendi olcutuyle TARTISMASIZ EV SAHIBI: parca onlara TAKILIR.
#
# ⚠️ `Volvo` ile `Volvo Penta` AYRI EV SAHIPLERIDIR (otomobil ile deniz motoru). Tek jetona
# indirilmezler ve model_normalize onlari CAKISTIRMAZ (`volvo` != `volvopenta`) — kapi bunu
# AYRI bir iddia olarak olcer (V13), cunku "Penta" ekini kirpan bir normalizasyon iki farkli
# uyum evrenini sessizce tek sayfaya yigardi.
UYUM_MARKA_MIMAR_EKI = frozenset({
    "Volvo Penta", "Yanmar",
    "Chery", "Chevrolet", "Dodge", "Fiat", "Infiniti", "Jeanneau", "Johnson Pump",
    "Kawasaki", "Kia", "Lamborghini", "Lexus", "Maserati", "Mercruiser", "Scion",
    "Smart", "Subaru", "Vauxhall",
    "Anker", "Garmin", "GoPro", "Kenwood", "Krups", "Pioneer", "Raspberry Pi", "Remis",
    "Rode", "Samsung", "Sony",
    # 3. tur (5 Agu 2026) — gerekce + olculen katalog agirligi UYUM_MARKA_IZINLI'nin
    # "C grubu" blogunda, ad ad yazili. Burada TEKRAR EDILMEZ (ikiz metin yasagi).
    "Huawei", "Stanley", "TomTom", "Webasto",
})

# 🔴 REDDEDILEN ADAYLAR (2 Agu, mimar karari) — kayda geciyor ki bir sonraki tur ayni
# jetonlari yeniden "kesfetmesin" ve karar yeniden tartisilmasin:
#   `PSA` (15) · `VAG` (13)  grup kisaltmasi, marque DEGIL — musteri "VAG parcasi" aramaz
#   `Alpine` (5)             cift anlam: Renault Alpine (marque) / Alpine oto ses (cihaz)
#   `Brodit` (2)             telefon tutucu ureticisi, sinirda
#   `Gurtner` (2)            karburator ureticisi -> URETICI tarafi, uyum ekseni degil
#   `Sierra` (149)           🔴 SOZLUK sorunu DEGIL, VERI sorunu — asagida.
# `Sierra` jetonu IKI FARKLI seyi adlandiriyor ve dogru cozum KAYIT BASINA ayrismadir.
# OLCULDU: 149 kaydin 141'i kategori `Marin`, 8'i `Otomobil`; otomobil tarafindaki
# partnerler `Ford`(4), `Suzuki`(4), `Samurai`(3), `Jimny`(3), `SJ413`(3) — yani orada
# `Sierra` bir MODEL (Ford/GMC/Suzuki Sierra). Marin tarafindaki 141 kayit ise deniz
# yedek parca markasidir. Karar BACKFILL ANINDA verilecek (MaCiT duzlemi), sozlukte degil.
URETICI_MARKA_MIMAR_EKI = frozenset({"Bosch"})

# ─────────────────────────────────────────────────────────────────────────────
# MODEL OLMAYAN JETONLAR — /marka/<marka>/<model>/ SAYFA EVRENI icin (3 Agu, KraL denetimi)
#
# 🔴 NE ICIN: `marka` dizisindeki her jeton model adayidir; bu tablo "bu jeton bir MODEL
# DEGILDIR" yargisini tasir ve tools/marka_model_build.py o kovaya SAYFA ACMAZ. Uyum
# eslemesine, aramaya, D1'e ve `marka` alanina DOKUNMAZ (kayit AYNEN durur; yalnizca o
# jetondan model SAYFASI dogmaz) -> yukaridaki donmus kumelerin aritmetigini KIRMAZ.
#
# 🔴 NEDEN AYRI TABLO, URETICI_MARKA'ya EKLENMEDI: `URETICI_MARKA` uyeligi jetonu
# `uyum[].marka` alaninda GECERSIZ kilar (fail-closed) ve `UYUM_MARKA_ONERI_SAYISI`
# aritmetigine girer; oradaki her ekleme MaCiT'in uyum duzlemini degistirir. Buradaki yargi
# yalnizca SEO sayfa evrenine dairdir. Iliski belgelidir: URETICI_MARKA'nin "ileride
# uretici/parca markasi filtresi gerekirse kaynak burasidir" notunun MODEL ekseni karsiligi.
#
# OLCUM (3 Agu, 17032 urun): ESIK=3'u gecen 70 YENI kovanin 10'u bu jetonlardan doguyordu.
# Her satir DENETIMDE tek tek bakilarak yazildi (urun basliklari okundu), sinifiyla birlikte:
MODEL_OLMAYAN_JETON = {
    # GRUP KISALTMASI — marque DEGIL (yukaridaki "REDDEDILEN ADAYLAR" notunda zaten
    # yargilanmisti; orada YORUM, burada MAKINE OKUR hale geldi).
    "PSA": "grup kisaltmasi (Peugeot-Citroen); musteri 'PSA parcasi' aramaz",
    "VAG": "grup kisaltmasi (VW Audi Group); musteri 'VAG parcasi' aramaz",
    # PARCA/DONANIM URETICISI — parca ONA takilir ama arac MODELI degildir. Kayitlarda
    # gercek model AYRI jeton olarak zaten duruyor (Tundra/Defender/Supra/Tacoma).
    "Carling": "anahtar (switch) ureticisi — Land Rover/Toyota konsol panellerinde gecer",
    "AEM": "gosterge/performans parcasi ureticisi — kayitlarda model 'Supra'",
    "Sprint Booster": "gaz tepki modulu urun markasi — kayitlarda model 'Tacoma'",
    "Roland": "elektronik davul markasi — Yamaha/Alesis ile birlikte gecer, model degil",
    # MARQUE — baska bir markanin ADI, dolayisiyla o markanin MODELI olamaz.
    "Geo": "GM marque'i (Geo Tracker/Metro); Suzuki'nin modeli degil, kardes marka",
    "Mk1": "nesil işareti, rozet değil; <Model> Mk1 biçiminde geçer; hiçbir markada tekil rozet olarak satılmadı (K172, 18 Ağu, KraL hükmü)",
}

MODEL_OLMAYAN_SAYISI = 8
MODEL_OLMAYAN_IMZA = "5cd49e343cc7852b"

# ─────────────────────────────────────────────────────────────────────────────
# ROZET DISI (marka, model) CIFTLERI — /marka/X/M/ sayfasi ACILMAZ (4 Agu, KraL hukmu)
#
# HUKUM: "bir /marka/X/M/ sayfasi ancak M modeli GERCEKTEN X rozetiyle satilmissa acilir."
# Golf hicbir zaman Audi, Octavia hicbir zaman Volkswagen rozetiyle satilmadi; bu kayitlar
# platform/parca uyumudur, ROZET degil.
#
# 🔴 NEDEN YAPISAL KURAL DEGIL DE KURATORLU CIFT TABLOSU (olculdu, 4 Agu — uydurma degil):
# Mimarin onerdigi yazilabilir kural "(a) uyum[].marka==X && uyum[].model==M  YA DA
# (b) marka[0]==X" gercek katalogda TAM 0 cift eliyor: `/marka/audi/golf/` kayitlarinda
# marka[0] ZATEN 'Audi' ve bir kayitta `uyum` fiilen {marka:Audi, model:Golf} DIYOR.
# Yalniz (a)'ya inmek ise 46 cift eliyor ve mimarin ACIKCA korunmasini istedigi sayfalari
# olduruyor (`/marka/toyota/brz/`, `/marka/subaru/gt86/`, `/marka/peugeot/jumper/`,
# `/marka/toyota/107/`, hatta `/marka/ford/f-150/`) — cunku katalogun buyuk kismi `uyum`
# TASIMIYOR. Veri, "Audi+Golf" ile "Subaru+BRZ"yi AYIRT EDEN yapisal bir sinyal ICERMIYOR:
# ikisi de "cok markali uyumluluk listesi"dir; fark otomotiv ROZET bilgisidir.
# Bu yuzden yargi, deponun mevcut deseniyle (MODEL_OLMAYAN_JETON / BILESIK_MARKA_REDDEDILEN)
# KAPALI, GEREKCELI ve KIMLIGI DONMUS bir tabloya yazilir. Genel bir normalizasyon/heuristik
# YAZILMAZ: yazilsaydi mesru rozet ikizlerini (Berlingo/Partner, GT86/BRZ, 107/C1/Aygo,
# Ducato/Jumper/Boxer) sessizce oldururdu.
#
# ⚠️ BUYUME GORUNUR KARARDIR: kimlik donmus (ROZET_DISI_IMZA), sessiz genisleme
# tools/model-uyelik-kapisi.py'de KIRMIZI yakar. Yeni giris = mimar hukmu.
# Eleme URUN KAYBETTIRMEZ: sayfasi acilmayan kovanin urunleri marka sayfasinda ve kendi
# GERCEK model sayfasinda (Golf -> /marka/volkswagen/golf/) durmaya devam eder (kapi olcer).
ROZET_DISI_CIFT = {
    ("Audi", "Golf"): "Golf VW rozetidir; Audi Golf diye bir arac satilmadi (VAG platform "
                      "ortakligi) — gercek sayfa /marka/volkswagen/golf/",
    ("Volkswagen", "Octavia"): "Octavia Skoda rozetidir; VW Octavia diye bir arac satilmadi "
                               "— gercek sayfa /marka/skoda/octavia/",
    # 4 Agu: KUSAK KATLAMASI paketinde ortaya CIKTI (katlamanin URETTIGI bir sayfa degil,
    # katlamanin GORUNUR kildigi mevcut bir bosluk): `Skoda` kovasindaki `Golf` grubunda 4
    # urun ZATEN vardi ama hicbirinin BIRINCIL markasi Skoda olmadigi icin sayfa (sansa
    # bagli olarak) acilmiyordu. `Golf IV` jetonu katlaninca birincili Skoda olan bir urun
    # geldi ve /marka/skoda/golf/ dogdu. Yargi YENI DEGIL, mimarin (Audi, Golf) satirinda
    # yazdigi kuralin AYNISININ kardes marqueye uygulanmasidir: Golf VW rozetidir, VAG
    # platform ortakligi rozet DEGILDIR. Bes urunun tamami /marka/volkswagen/golf/ ve
    # Skoda marka sayfasinda durmaya devam eder (kapi K11 kaybolan=0 olcer).
    ("Skoda", "Golf"): "Golf VW rozetidir; Skoda Golf diye bir arac satilmadi (VAG platform "
                       "ortakligi) — gercek sayfa /marka/volkswagen/golf/",
    # 4 Agu, KraL hukmu (capraz-marka taramasi): CANLIDA duran sayfalar. Berlingo bir
    # CITROEN rozetidir; ayni arac Peugeot'ta `Partner`, Opel'de `Combo` adiyla satilir —
    # "Peugeot Berlingo" / "Opel Berlingo" diye bir arac HIC satilmadi. Emsal birebir
    # (Audi, Golf) satiridir. Urun KAYBOLMAZ: /marka/citroen/berlingo/ ve ilgili marka
    # sayfasinda durmaya devam eder (K11 kaybolan=0 olcer).
    # 🔴 ROZET IKIZI KATLAMASI ACILMADI (Okan/KraL hukmu, olculdu): Berlingo<->Partner<->
    # Rifter ayni arac AMA Opel Combo'nun urunlerinin cogunlugu Berlingo DEGIL (Combo C
    # Corsa tabanli, Combo D Fiat Doblo tabanli); blanket katlama YANLIS PARCA sattirir.
    # Bu tablo yalnizca YANLIS SAYFA dogmasini engeller, ikiz uyumu URETMEZ.
    ("Peugeot", "Berlingo"): "Berlingo Citroen rozetidir; Peugeot'daki karsiligi Partner/"
                             "Rifter — gercek sayfa /marka/citroen/berlingo/",
    # Opel|Berlingo bugun sayfa ACMIYOR (3 urun var ama hicbirinin BIRINCIL markasi Opel
    # degil). ILERIYE DONUK yazildi: envanterdeki veri yazildigi an ESIK'i gecip sessizce
    # dogacakti. Kapi (K19) ayni sinifin YENI uyelerini de KIRMIZI yakar.
    ("Opel", "Berlingo"): "Berlingo Citroen rozetidir; Opel'deki karsiligi Combo — gercek "
                          "sayfa /marka/citroen/berlingo/",
    # DS bagimsiz bir MARQUE'dir (DS Automobiles, 2014'te Citroen'den ayrildi); klasik DS
    # de Citroen rozetidir. "Peugeot DS" diye bir arac HIC satilmadi. CANLIDA duruyordu
    # (/marka/peugeot/ds/, 3 urun) — Okan'in ana sayfa Peugeot cip satirinda GORDUGU jeton.
    ("Peugeot", "DS"): "DS bagimsiz marque (DS Automobiles) / klasik DS Citroen rozetidir; "
                       "Peugeot DS diye bir arac satilmadi — gercek sayfa /marka/citroen/ds/",
    # ─────────────────────────────────────────────────────────────────────────
    # 4 Agu, KraL hukmu — KURAL (tek tek liste DEGIL): "bir /marka/X/M/ sayfasi ancak M
    # modeli GERCEKTEN X rozetiyle satilmissa dogar. Ayni fiziksel arac baska marque'ta
    # BASKA ADLA satiliyorsa, o marque'in sayfasi KENDI adiyla acilir; ikizin adiyla ACILMAZ."
    # Kural K19'un olctugu 41 capraz ciftin 14 "BEKLER" uyesine uygulandi; 14'u de DENY.
    # URUN KAYBOLMAZ (olculdu, kapi K11 ile teyitli): her cift icin urunlerin TAMAMI ayni
    # markanin BASKA bir yayimlanan kovasinda ZATEN duruyor + gercek rozet sayfasinda +
    # marka sayfasinda + aramada. Deny yalnizca "o ad, o markanin altinda SAYFA olmasin".
    # SEVEL hafif ticari ucuzu (Ducato/Jumper/Boxer) — her marque KENDI adiyla acilir:
    ("Fiat", "Boxer"): "Fiat'in rozeti Ducato; Boxer Peugeot'nun — /marka/peugeot/boxer/",
    ("Citroen", "Ducato"): "Citroen'in rozeti Jumper; Ducato Fiat'in — /marka/fiat/ducato/",
    ("Fiat", "Jumper"): "Fiat'in rozeti Ducato; Jumper Citroen'in — /marka/citroen/jumper/",
    ("Peugeot", "Jumper"): "Peugeot'nun rozeti Boxer; Jumper Citroen'in — "
                           "/marka/citroen/jumper/",
    # Hafif ticari ikizler (Berlingo/Partner · Trafic/Vivaro · Expert/Jumpy/Proace):
    ("Citroen", "Partner"): "Citroen'in rozeti Berlingo; Partner Peugeot'nun — "
                            "/marka/peugeot/partner/",
    ("Opel", "Trafic"): "Opel'in rozeti Vivaro; Trafic Renault'nun — /marka/renault/trafic/",
    ("Renault", "Vivaro"): "Renault'nun rozeti Trafic; Vivaro Opel'in — /marka/opel/vivaro/",
    ("Citroen", "Proace"): "Citroen'in rozeti Jumpy/Dispatch; Proace Toyota'nin — "
                           "/marka/toyota/proace/",
    ("Peugeot", "Proace"): "Peugeot'nun rozeti Expert; Proace Toyota'nin — "
                           "/marka/toyota/proace/",
    # Toyota/Subaru ortak kupesi (GT86 · BRZ · Scion FR-S):
    ("Toyota", "BRZ"): "Toyota'nin rozeti GT86/GR86; BRZ Subaru'nun — /marka/subaru/brz/",
    ("Subaru", "GT86"): "Subaru'nun rozeti BRZ; GT86 Toyota'nin — /marka/toyota/gt86/",
    # 🔴 FR-S SAPMASI (mimara raporlandi): FR-S bir SCION rozetidir — katalogda marque olarak
    # YOK. Kural iki ciftin de deny'ini gerektiriyor ve sonucta `frs` canon'u SAHIPSIZ kaliyor
    # (hicbir markada sayfa dogmuyor). OLCULDU: bu 6 tekil urunun TAMAMI zaten `brz` ve/veya
    # `gt86` yayimlanan kovalarinda -> kaybolan 0. Ad kayboluyor, URUN kaybolmuyor.
    ("Toyota", "FR-S"): "FR-S Scion rozetidir; Toyota'nin rozeti GT86 — /marka/toyota/gt86/",
    ("Subaru", "FR-S"): "FR-S Scion rozetidir; Subaru'nun rozeti BRZ — /marka/subaru/brz/",
    # A-segment ucuzu (107 · C1 · Aygo):
    ("Toyota", "C1"): "Toyota'nin rozeti Aygo; C1 Citroen'in — /marka/citroen/c1/",
    # ─────────────────────────────────────────────────────────────────────────
    # 6 Agu, mimar hukmu (ADIM 3 / hukum A — "capraz marka rozeti", 17 cift).
    # Kural AYNEN yukaridaki satirlarin kurali: "/marka/X/M/ sayfasi ancak M modeli
    # GERCEKTEN X rozetiyle satilmissa acilir." Bu 17 cift BASLIK KOLUYLA esigi geciyordu
    # ve yargisiz bekliyordu; hicbiri o markanin KENDI rozeti degil. URUN KAYBOLMAZ:
    # her cift icin urunler marka sayfasinda ve gercek rozet sayfasinda durur (kapi olcer).
    # A-segment ucuzu (107 · C1 · Aygo) — Aygo TOYOTA rozeti:
    ("Citroen", "Aygo"): "Citroen'in rozeti C1; Aygo Toyota'nin — /marka/citroen/c1/",
    ("Peugeot", "Aygo"): "Peugeot'nun rozeti 107; Aygo Toyota'nin — /marka/peugeot/107/",
    # SEVEL hafif ticari ucuzu — her marque KENDI adiyla (Ducato/Jumper/Boxer):
    ("Citroen", "Boxer"): "Citroen'in rozeti Jumper; Boxer Peugeot'nun — "
                          "/marka/peugeot/boxer/",
    ("Peugeot", "Ducato"): "Peugeot'nun rozeti Boxer; Ducato Fiat'in — /marka/fiat/ducato/",
    # Hafif ticari ikizler (Berlingo/Partner/Combo/Rifter · Expert/Jumpy/Scudo/Proace):
    ("Citroen", "Combo"): "Citroen'in rozeti Berlingo; Combo Opel'in — "
                          "/marka/citroen/berlingo/",
    ("Peugeot", "Combo"): "Peugeot'nun rozeti Partner/Rifter; Combo Opel'in — "
                          "/marka/peugeot/partner/",
    ("Citroen", "Rifter"): "Citroen'in rozeti Berlingo; Rifter Peugeot'nun — "
                           "/marka/citroen/berlingo/",
    ("Citroen", "Expert"): "Citroen'in rozeti Jumpy/Dispatch; Expert Peugeot'nun — "
                           "/marka/peugeot/expert/",
    ("Citroen", "Scudo"): "Citroen'in rozeti Jumpy; Scudo Fiat'in — /marka/citroen/jumpy/",
    ("Peugeot", "Scudo"): "Scudo Fiat'in rozetidir; Peugeot'nun karsiligi Expert — "
                          "/marka/peugeot/expert/",
    # Renault/Opel/Nissan hafif ticari (Trafic/Vivaro/Primastar):
    ("Opel", "Primastar"): "Opel'in rozeti Vivaro; Primastar Nissan'in — /marka/opel/vivaro/",
    ("Renault", "Primastar"): "Renault'nun rozeti Trafic; Primastar Nissan'in — "
                              "/marka/renault/trafic/",
    # GM menzil-genisletmeli elektrikli ikizi (Volt/Ampera):
    ("Opel", "Volt"): "Opel'in rozeti Ampera; Volt Chevrolet'nin",
    ("Chevrolet", "Ampera"): "Chevrolet'nin rozeti Volt; Ampera Opel'in",
    # VAG ic ikizler (Golf/Sharan/Alhambra/Citigo/Up):
    ("Seat", "Golf"): "Golf VW rozetidir; Seat Golf diye bir arac satilmadi (VAG platform "
                      "ortakligi) — gercek sayfa /marka/volkswagen/golf/",
    ("Seat", "Sharan"): "Seat'in rozeti Alhambra; Sharan VW'nin — "
                        "/marka/volkswagen/sharan/",
    ("Volkswagen", "Alhambra"): "VW'nin rozeti Sharan; Alhambra Seat'in — "
                                "/marka/seat/alhambra/",
    ("Volkswagen", "CITIGO"): "VW'nin rozeti Up; Citigo Skoda'nin — /marka/skoda/citigo/",
    # 15 Agu, KraL hukmu (K19 capraz-marka): BMW'nin motosiklet aile rozeti GS'tir; `Adventure`
    # GS'in varyant ekidir (R 1250 GS Adventure), BAGIMSIZ bir BMW rozeti DEGIL. `Adventure`
    # ciplak adiyla KTM'nin model ailesidir. Urun KAYBOLMAZ: BMW urunleri /marka/bmw/gs/ ve
    # BMW marka sayfasinda durur (kapi K11 kaybolan=0 olcer). Emsal birebir ("Peugeot","Scudo").
    ("BMW", "Adventure"): "BMW'nin aile rozeti GS; `Adventure` GS'in varyant eki, KTM'nin ise "
                          "model ailesi adi — gercek sayfa /marka/bmw/gs/",
    # ─────────────────────────────────────────────────────────────────────────
    # 18 Agu, K170 (KraL hukmu): 17 YARGISIZ ciftin 7'sini DENY'e aliyor. Kural
    # AYNI: bir /marka/X/M/ sayfasi ancak M modeli GERCEKTEN X rozetiyle satilmissa
    # acar. Bu 7 ciftin hicbirinde o kosul yok. URUN KAYBOLMAZ (K11 kaybolan=0).
    # Alfa Romeo'nun `916` tip/sasi kodu (GTV/Spider 1995-2006) Ducati'nin 916 superbike
    # rozetiyle AD CAKISMASI — gercek 916 sayfasi Ducati'nindir.
    ("Alfa Romeo", "916"): "Alfa Romeo `916` rozetiyle arac SATMADI (tip/sasi kodu); "
                           "urunler Alfa Romeo agacinda durur. `916` model sayfasi Ducati'nindir",
    # PSA C5 Peugeot rozeti degil (eksik kalmis Citroen C5 deny'i — yeni).
    ("Peugeot", "C5"): "C5 Citroen rozetidir; Peugeot C5 diye bir arac satilmadi (PSA "
                       "platform ortakligi) — gercek sayfa /marka/citroen/c5/. Emsal birebir "
                       "(Audi,Golf) satiri. Urunler Peugeot agacinda durur; urun KAYBOLMAZ",
    # C1 Peugeot rozeti degil (eksik kalmis A-segment uclusu deny'i).
    ("Peugeot", "C1"): "Peugeot'nun A-segment rozeti 107/108; C1 Citroen'in — gercek sayfa "
                       "/marka/citroen/c1/. Emsal birebir mevcut (Toyota,C1) satiri. Urunler "
                       "Peugeot agacinda durur; urun KAYBOLMAZ",
    # Piaggio ana marque, GTS/Primavera/PX/Largeframe VESPA rozetleri (4 eksik aile).
    ("Piaggio", "GTS"): "GTS bir VESPA rozetidir; Piaggio ana marque'tir, `Piaggio GTS` diye "
                         "arac satilmadi — gercek sayfa /marka/vespa/gts/. Urunler Piaggio "
                         "agacinda durur; urun KAYBOLMAZ",
    ("Piaggio", "Primavera"): "Primavera VESPA rozetidir — gercek sayfa /marka/vespa/primavera/. "
                               "Urunler Piaggio agacinda durur; urun KAYBOLMAZ",
    ("Piaggio", "PX"): "PX VESPA rozetidir — gercek sayfa /marka/vespa/px/. Urunler Piaggio "
                       "agacinda durur; urun KAYBOLMAZ",
    ("Piaggio", "Largeframe"): "Largeframe VESPA govde aile adidir (Smallframe'in karsiligi), "
                                "Piaggio rozeti DEGIL — gercek sayfa /marka/vespa/largeframe/. "
                                "Urunler Piaggio agacinda durur; urun KAYBOLMAZ",
    ("Piaggio", "Smallframe"): "Smallframe VESPA govde aile adidir (Largeframe'in karsiligi), "
                               "Piaggio rozeti DEGIL — gercek sayfa /marka/vespa/smallframe/. "
                               "Urunler Piaggio agacinda durur; urun KAYBOLMAZ",
    ("Piaggio", "50"): "`Piaggio 50` rozetiyle arac satilmadi; 50/V50 VESPA rozetidir — gercek sayfa "
                       "/marka/vespa/50/. Urunler Piaggio agacinda durur; urun KAYBOLMAZ",
    ("Piaggio", "50 Special"): "50 Special VESPA rozetidir (50'nin donanim rozeti) — gercek sayfa "
                               "/marka/vespa/50special/. Urunler Piaggio agacinda durur; urun KAYBOLMAZ",
}

ROZET_DISI_SAYISI = 49
ROZET_DISI_IMZA = "50b8634d01d4e785"  # K202 sonrasi: kapinin hesabiyla


def rozet_disi_imzasi():
    """Cift kumesinin ANAHTAR kimligi (S2 dersi: SAYI degil KIMLIK)."""
    return hashlib.sha256(
        json.dumps(sorted("%s|%s" % (a, b) for a, b in ROZET_DISI_CIFT), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# CAPRAZ-MARKA (ROZET) IZIN ENVANTERI — ROZET_DISI_CIFT'in ALLOW tarafi (4 Agu, mimar hukmu)
#
# OLCULEN SINIF: `ROZET_DISI_CIFT` bugune kadar ELLE bulunmus ornekleri tutuyordu; yeni bir
# rozet ihlali ancak biri CANLIDA gorunce yakalanabiliyordu. Olculdu (4 Agu, 17914 urun):
# `(Peugeot, Berlingo)` 9 urunle YAYINDA, `(Peugeot, DS)` 3 urunle YAYINDA, `(Opel, Berlingo)`
# 3 urunle ESIK'in DIBINDE bekliyordu — ucu de sessizce dogmustu.
#
# ILERIYE DONUK YUKLEM (kapi: tools/model-uyelik-kapisi.py K19): ayni KANONIK model anahtari
# IKI ya da DAHA COK markada sayfa esigini geciyorsa, o (marka, canon) cifti ya ROZET_DISI_CIFT'te
# (deny) ya BU envanterde (allow) olmak ZORUNDADIR. Ikisinde de yoksa kapi KIRMIZI yanar ve
# karar ister — sessiz sayfa DOGMAZ.
#
# 🔴 KARSILASTIRMA BIRIMI KUME'dir, SAYI DEGIL (DEGISTIRICI_SAYFA_IZNI ile ayni disiplin):
# bir cift olup biri dogunca sayi sabit kalir ve sapma gizlenirdi ([[hukum-yanlis-birimde]]).
#
# 🔴 NEDEN "IKIZI KATLA" DIYE BIR KURAL YAZILMADI (olculdu ve curutuldu): Berlingo/Partner/
# Rifter/Proace City ayni aractir AMA Opel Combo'nun urunlerinin cogunlugu Berlingo DEGIL
# (Combo C Corsa tabanli, Combo D Fiat Doblo tabanli, Combo E gercek ikiz). Blanket katlama
# YANLIS PARCA sattirir. Bu envanter yalnizca YANLIS SAYFA dogmasini engeller; ikiz uyumu
# URETMEZ.
#
# DEGER SINIFI: yalnizca "ROZET" — model o markanin KENDI rozetiyle GERCEKTEN satildi.
# 🔴 "BEKLER" SINIFI KALDIRILDI (4 Agu, KraL hukmu): 14 uyenin tamami mimar kuralina gore
# YARGILANDI ve 14'u de ROZET_DISI_CIFT'e (deny) tasindi. Gecici bir "karar bekliyor" sinifi
# tabloda KALMAZ — yargisiz giris, yargisiz sayfa demektir; kural artik tek ve nettir.
# Yeni bir capraz cift dogarsa K19 KIRMIZI yakar ve kural o cifte de UYGULANIR.
ROZET_CAPRAZ_IZINLI = {
    "Citroen|berlingo": ("ROZET", "Berlingo Citroen'in kendi rozeti"),
    "Peugeot|boxer": ("ROZET", "Peugeot Boxer gercek rozet (SEVEL ucuzu; her marka KENDI adiyla)"),
    "Subaru|brz": ("ROZET", "Subaru BRZ gercek rozet"),
    "Citroen|c1": ("ROZET", "Citroen C1 gercek rozet"),
    "Citroen|ds": ("ROZET", "Klasik Citroen DS + DS marque'inin cikis rozeti"),
    "Fiat|ducato": ("ROZET", "Fiat Ducato gercek rozet"),
    "Dacia|duster": ("ROZET", "Dacia Duster gercek rozet"),
    "Renault|duster": ("ROZET", "Renault Duster bazi pazarlarda gercek rozet (Rusya/Hindistan/"
                                "Brezilya) — ikizin adi DEGIL, KENDI adi"),
    "Volkswagen|golf": ("ROZET", "Golf VW'nin kendi rozeti"),
    "Toyota|gt86": ("ROZET", "Toyota GT86 gercek rozet"),
    "Citroen|jumper": ("ROZET", "Citroen Jumper gercek rozet"),
    "Dacia|logan": ("ROZET", "Dacia Logan gercek rozet"),
    "Renault|logan": ("ROZET", "Renault Logan bazi pazarlarda gercek rozet — KENDI adi"),
    "Skoda|octavia": ("ROZET", "Octavia Skoda'nin kendi rozeti"),
    "Peugeot|partner": ("ROZET", "Peugeot Partner gercek rozet"),
    "Opel|combo": ("ROZET", "Opel Combo Opel'in kendi rozeti (Berlingo/Partner/Rifter kardesi)"),
    "Peugeot|expert": ("ROZET", "Peugeot Expert Peugeot'nun kendi rozeti (Jumpy/Proace kardesi)"),
    "Peugeot|rifter": ("ROZET", "Peugeot Rifter Peugeot'nun kendi rozeti (Berlingo/Partner kardesi)"),
    "Toyota|proace": ("ROZET", "Toyota Proace gercek rozet"),
    "Dacia|sandero": ("ROZET", "Dacia Sandero gercek rozet"),
    "Renault|sandero": ("ROZET", "Renault Sandero bazi pazarlarda gercek rozet — KENDI adi"),
    # Ayni ADI tasiyan AYRI araclar (ikiz DEGIL, ad cakismasi): Ford Sierra (1982 sedan) ile
    # Suzuki Jimny Sierra ayni arac degildir; ikisi de KENDI rozetiyle satildi.
    "Ford|sierra": ("ROZET", "Ford Sierra gercek model (Suzuki Sierra ile IKIZ DEGIL, ad cakismasi)"),
    "Suzuki|sierra": ("ROZET", "Suzuki (Jimny) Sierra gercek model"),
    # 5 Agu, ayni AD CAKISMASI sinifi (emsal birebir Ford|sierra / Suzuki|sierra satiridir).
    # Ford Raptor = F-150/Ranger/Bronco Raptor (kamyonet performans rozeti, 2010->);
    # Yamaha Raptor = YFM660R/YFM700R Raptor (ATV rozeti, 2001->). Ayni fiziksel arac DEGIL,
    # rozet muhendisligi DEGIL, ortak platform DEGIL — sadece ayni ad. Iki sayfa da KENDI
    # rozetiyle dogar. Cift `ecc01a25` veri partisiyle capraz oldu: Ford|raptor kovasi
    # 5 urunle ZATEN yayindaydi, Yamaha|raptor 2 -> 6 urune cikip ESIK'i gecti.
    "Ford|raptor": ("ROZET", "Ford Raptor gercek rozet (F-150/Ranger/Bronco Raptor; Yamaha "
                             "Raptor ATV ile IKIZ DEGIL, ad cakismasi)"),
    "Yamaha|raptor": ("ROZET", "Yamaha Raptor gercek rozet (YFM660R/YFM700R ATV; Ford Raptor "
                               "kamyonetiyle IKIZ DEGIL, ad cakismasi)"),
    "Renault|trafic": ("ROZET", "Renault Trafic gercek rozet"),
    "Opel|vivaro": ("ROZET", "Opel Vivaro gercek rozet"),
    # 5 Agu — BASLIK KOLU acilinca capraz olan cift (Peugeot|107 kovasi ESIK'i gecti).
    # PSA/Toyota ortak platformu: ayni arac UC rozetle satildi (107 / C1 / Aygo).
    "Peugeot|107": ("ROZET", "Peugeot 107 Peugeot'nun KENDI rozeti (C1 ve Aygo kardesleri)"),
    "Toyota|107": ("BEKLER", "Toyota'nin rozeti AYGO'dur; `107` Peugeot rozetidir. Kova "
                             "katalogda ESIK ustunde — ROZET_DISI'ye alinsin mi, mimar hukmu "
                             "bekliyor (deny yazilirsa urunler Toyota agacinda kalir)"),
    # 7 Agu — Nissan/Datsun veri partisiyle capraz olan cift (K19 KIRMIZI yakti).
    # S30 (1969-1978) ihracat pazarlarinda DATSUN 240Z rozetiyle satildi; ureticisi
    # Nissan'dir ve marka bugun ayni araci NISSAN 240Z diye anar. Emsal birebir
    # `Dacia|duster`/`Renault|duster` satirlaridir: ayni arac, IKI GERCEK rozet, iki
    # sayfa. Katalogda iki yazim da GERCEK urun basliklarinda geciyor (ornek:
    # `datsun-240z-...` ve `nissan-240z-alternator-braketi-kapagi`). Nissan kolu ayrica
    # BASLIK_DOGAN_ALLOW'da ZATEN yargilanmisti — bu satir o hukmun capraz eksendeki
    # karsiligidir, YENI bir sayfa acmaz.
    "Datsun|240z": ("ROZET", "Datsun 240Z (S30) ihracat pazarlarinin ORIJINAL rozeti"),
    "Nissan|240z": ("ROZET", "Nissan 240Z ayni S30'un uretici rozeti (Datsun Nissan'in "
                             "ihracat markasidir; ikizin adi DEGIL, KENDI adi)"),
    # ─────────────────────────────────────────────────────────────────────────
    # 7 Agu — K19'un IKIZ TANIMI duzeltilince GORUNUR olan 12 cift.
    # 🔴 BU SATIRLAR HICBIR SAYFA ACMAZ: ROZET_CAPRAZ_IZINLI'yi YALNIZ kapi okur (uretim
    # `yayimlanir_mi` ROZET_DISI deny'ine bakar). Asagidaki kovalarin 12'si de BUGUN ZATEN
    # YAYINDA. Neden simdi gorunuyorlar: K19'un capraz-aday filtresi "baslik-dogan kova
    # BASLIK_DOGAN_ALLOW'da mi" diye soruyordu; 6 Agu'da yargiya H1/H3 KURAL kollari eklendi
    # ama o filtre GUNCELLENMEDI ([[ikiz-tanim-sessiz-ayrisma]]) ve kuralla yargilanan
    # capraz kovalar K19'un olcum yuzeyinden SESSIZCE dusmustu. Filtre 7 Agu'da uc kaynakli
    # hale getirildi; aday kume 45 -> 59 cifte cikti ve bu 12'si yargisiz kaldi.
    # SINIFLAR: emsali BIREBIR olan cift ROZET, gercek hukum gerektiren cift BEKLER.
    "Datsun|260z": ("ROZET", "Datsun 260Z ayni Z ailesi (S30) — emsal birebir `Datsun|240z`"),
    "Nissan|260z": ("ROZET", "Nissan 260Z ureticinin rozeti — emsal birebir `Nissan|240z`"),
    "Datsun|280z": ("ROZET", "Datsun 280Z (S30/S130) — emsal birebir `Datsun|240z`"),
    "Nissan|280z": ("ROZET", "Nissan 280Z ureticinin rozeti — emsal birebir `Nissan|240z`"),
    "Toyota|gr86": ("ROZET", "Toyota GR86 Toyota'nin KENDI rozeti — emsal `Toyota|gt86`"),
    "Ford|fserisi": ("ROZET", "Ford F-Serisi Ford'un KENDI rozeti (BMW F-Serisi ile IKIZ "
                              "DEGIL, ad cakismasi — emsal `Ford|sierra`)"),
    "Mercedes|t1": ("ROZET", "Mercedes T1 gercek tip adi (VW T1 ile IKIZ DEGIL, ad "
                             "cakismasi — emsal `Ford|sierra`/`Suzuki|sierra`)"),
    "Volkswagen|t1": ("ROZET", "VW T1 (Transporter/Type 1 nesli) gercek tip adi — ayni "
                               "ad cakismasi ekseni"),
    "BMW|fserisi": ("BEKLER", "BMW F-Serisi bir SASI NESLI ailesidir (F30/F32...), Ford "
                              "F-Serisi ise kamyonet rozeti. Aile sayfasi mesru mu (emsal "
                              "`BMW|K Serisi`) yoksa ROZET_DISI mi — mimar hukmu bekliyor"),
    "Subaru|gr86": ("BEKLER", "Subaru'nun rozeti BRZ'dir; `GR86` Toyota rozetidir (emsal "
                             "birebir `Toyota|107`). ROZET_DISI'ye alinsin mi — mimar "
                             "hukmu bekliyor (deny yazilirsa urunler Subaru agacinda kalir)"),
    # ─────────────────────────────────────────────────────────────────────────
    # 8 Agu — Lexus veri partisiyle capraz olan cift (K19 KIRMIZI yakti). Emsal birebir
    # `Ford|sierra`/`Suzuki|sierra` ve `Ford|raptor`/`Yamaha|raptor` satirlaridir: AYNI ADI
    # tasiyan AYRI araclar, ikiz DEGIL, rozet muhendisligi DEGIL — sadece AD CAKISMASI.
    # OLCULDU (8 Agu): BMW `GS` kovasi 26 urun, Lexus `GS` kovasi 7 urun (ikisi de ESIK=3
    # ustunde ve BIRINCIL); Citroen `GS` 2 urunle ESIK ALTINDA, sayfa adayi DEGIL.
    # 🔴 TARIHSEL NOT: 4 Agu'da `gs` capraz DEGILDI (BMW 13 / Citroen 1) ve o gun bu satiri
    # yazmak OLU giristi — K19 ileriye donuk bekci olarak tam da bu dogumu yakaladi.
    "BMW|gs": ("ROZET", "BMW GS BMW'nin kendi motosiklet serisi rozeti (R/F/G GS, GS "
                        "Adventure); Lexus GS ile yalniz AD cakismasi var, ayri rozet"),
    "Lexus|gs": ("ROZET", "Lexus GS Lexus'un kendi sedan rozeti (GS300/GS350/GS450h, JDM "
                          "Toyota Aristo); BMW GS ile yalniz AD cakismasi var, ayri rozet"),
    # 10 Agu — Mazda veri partisiyle capraz olan cift (K19 KIRMIZI yakti). `5` iki
    # markanin da kendi model adidir: Mazda 5 kompakt MPV, Renault 5 hatchback. Ayni
    # fiziksel arac, ikiz ya da rozet muhendisligi DEGIL; yalniz AD cakismasidir.
    # OLCULDU: Mazda `5` kovasi 3 urun, Renault `5` kovasi 11 urun; ikisi de ESIK=3
    # ustunde ve BIRINCIL. Emsal birebir BMW|gs / Lexus|gs ciftidir.
    "Mazda|5": ("ROZET", "Mazda 5 Mazda'nin kendi kompakt MPV modelidir; Renault 5 ile "
                         "yalniz AD cakismasi var, ayri model"),
    "Renault|5": ("ROZET", "Renault 5 Renault'nun kendi hatchback modelidir; Mazda 5 ile "
                           "yalniz AD cakismasi var, ayri model"),
    # 10 Agu — Jaguar veri partisiyle capraz olan cift (K19 KIRMIZI yakti, serit-a2 FAILURE,
    # `deploy` SKIPPED). Emsal BIREBIR `Ford|sierra`/`Suzuki|sierra`, `Ford|raptor`/
    # `Yamaha|raptor`, `BMW|gs`/`Lexus|gs` ve `Mazda|5`/`Renault|5` satirlaridir: AYNI ADI
    # tasiyan AYRI araclar — ikiz DEGIL, rozet muhendisligi DEGIL, ortak platform DEGIL;
    # yalniz AD CAKISMASI. Jaguar XJ6 (1968-1997 XJ serisi sedan) ile Yamaha XJ6 (2009->
    # XJ6/Diversion motosikleti) arasinda hicbir teknik iliski yoktur.
    # OLCULDU (10 Agu): Jaguar `XJ6` kovasi 6 urun, Yamaha `XJ6` kovasi 4 urun; ikisi de
    # ESIK=3 ustunde ve BIRINCIL, ikisi de BUGUN ZATEN YAYINDA (bu satirlar YENI SAYFA
    # ACMAZ — envanteri YALNIZ kapi okur, uretim ROZET_DISI deny'ine bakar).
    "Jaguar|xj6": ("ROZET", "Jaguar XJ6 Jaguar'in kendi sedan rozeti (XJ Series 1-3, X300/"
                            "X308); Yamaha XJ6 motosikletiyle yalniz AD cakismasi var"),
    "Yamaha|xj6": ("ROZET", "Yamaha XJ6 Yamaha'nin kendi motosiklet rozeti (XJ6 N/S "
                            "Diversion); Jaguar XJ6 sedaniyla yalniz AD cakismasi var"),
    # ─────────────────────────────────────────────────────────────────────────
    # 14 Agu — marka[] jeton duzeltmesi (Fiat|Scudo + Nissan|Primastar) ile capraz olan
    # ciftler (K19 KIRMIZI yakti, serit-a2 FAILURE, deploy SKIPPED). Scudo FIAT'in kendi
    # hafif ticari rozetidir (Citroen Jumpy / Peugeot Expert / Toyota ProAce kardesleri);
    # Primastar NISSAN'in kendi rozetidir (Renault Trafic / Opel Vivaro kardesi). Iki kol
    # da KENDI adidir -> ROZET (kendi sayfasi dogar). Yanlis-rebadge kolu `Peugeot|scudo`
    # ROZET_DISI_CIFT'e (deny) alindi.
    "Fiat|scudo": ("ROZET", "Fiat Scudo Fiat'in kendi hafif ticari rozeti (Jumpy/Expert/ProAce kardesi)"),
    "Nissan|primastar": ("ROZET", "Nissan Primastar Nissan'in kendi hafif ticari rozeti (Trafic/Vivaro kardesi)"),
    # ─────────────────────────────────────────────────────────────────────────
    # 14 Agu — H2 (jeton sahipligi COK-SAHiPLI, pay >= 1/3) ile capraz olan ciftler. (d)
    # kolundaki capraz-marka susmasi kaldirilinca ayni kanonun iki markadaki sayfa adayligi
    # gorunur oldu. Uc cift de "ad cakismasi" sinifidir (emsal Mazda|5/Renault|5): ikiz ya
    # da rozet muhendisligi DEGIL, AYNI ADI tasiyan AYRI araclar.
    "Mazda|bserisi": ("ROZET", "Mazda B-Serisi Mazda'nin kendi kompakt kamyoneti; Honda B "
                              "Serisi motor ailesiyle yalniz AD cakismasi var, ayri arac"),
    "Honda|bserisi": ("ROZET", "Honda B Serisi Honda'nin kendi motor ailesi (B16/B18/B20); "
                              "Mazda B-Serisi kamyonetiyle yalniz AD cakismasi var"),
    "Hyundai|coupe": ("ROZET", "Hyundai Coupe Hyundai'nin kendi modeli (Tiburon'un Avrupa "
                               "adi); Audi'de 'coupe' gövde tipi kelimesiyle AD cakismasi"),
    "Seat|alhambra": ("ROZET", "Seat Alhambra Seat'in kendi MPV rozeti; VW'nin kardesi "
                              "Sharan'dir (Alhambra VW rozeti DEGIL, o taraf ROZET_DISI)"),
    "Audi|coupe": ("BEKLER", "Audi 'Coupe' bir GOVDE TIPI kelimesidir (Audi 80 B3/B4 coupe); "
                             "ayri bir Audi Coupe (B2/B3) modeli de vardi. ROZET mi MODEL_"
                             "OLMAYAN mi — mimar hukmu bekliyor (Hyundai|Coupe ROZET'tir)"),
    # ───────────────────────────────────────────────────────────────────────────────
    # 15 Agu — KTM x Thingiverse partisiyle capraz olan cift (K19 KIRMIZI yakti, serit-a2 +
    # serit-a3 FAILURE). `Adventure` KTM'nin KENDI model ailesi adidir (KTM serileri: DUKE,
    # RC, ADVENTURE, ENDURO, SUPERMOTO; 390/790/890 Adventure, 1290 Super Adventure, klasik
    # 950/990 Adventure) -> KTM kolu ROZET, kendi sayfasi dogar. BMW'de aile adi GS'tir ve
    # `Adventure` GS'in VARYANT ekidir (R 1250 GS Adventure); BMW yalnizca "Adventure" adiyla
    # rozetlenmis bir motosiklet SATMADI -> BMW kolu ROZET_DISI_CIFT'e (deny) alindi, urunler
    # /marka/bmw/gs/ ve BMW marka sayfasinda durur. Emsal birebir `Fiat|scudo`/`Peugeot|Scudo`.
    "KTM|adventure": ("ROZET", "KTM Adventure KTM'nin kendi model ailesi rozeti (390/790/890 "
                               "Adventure, 1290 Super Adventure, 950/990 Adventure); BMW'de "
                               "'Adventure' GS ailesinin VARYANT ekidir, ayri sinif"),
    # ─────────────────────────────────────────────────────────────────────────
    # 18 Agu, K170 (KraL hukmu): K166'nin kusuru URUN URETMEDI; 17 capraz-marka cifti
    # bugune kadar YARGISIZ bekliyordu (K19 KIRMIZI) — 10 satirla ALLOW (1'i BEKLER).
    # AD CAKISMASI emsalleri: Ford|sierra/Suzuki|sierra, BMW|gs/Lexus·gs, Mazda|5/Renault|5.
    # ETKILENEN_URUN = 0 (K11 kaybolan=0 olcer): sayfasi acilmayan kovanin urunleri ayni
    # markanin gercek rozet sayfasinda / aramada / marka kovasinda durur.
    "Ducati|916": ("ROZET", "Ducati 916 gercek superbike rozeti (1994-1998); Alfa Romeo'nun "
                            "`916` tip/sasi koduyla yalniz AD cakismasi var (emsal Ford|sierra / "
                            "Suzuki|sierra, BMW|gs / Lexus|gs)"),
    "Alfa Romeo|stelvio": ("ROZET", "Alfa Romeo Stelvio gercek SUV rozeti (2016->); Moto Guzzi "
                                    "Stelvio 1200 ile yalniz AD cakismasi (Stelvio Gecidi) — "
                                    "rozet muhendisligi DEGIL"),
    "Moto Guzzi|stelvio": ("ROZET", "Moto Guzzi Stelvio 1200 gercek motosiklet rozeti (2008->); "
                                      "Alfa Romeo Stelvio SUV ile yalniz AD cakismasi, ayri "
                                      "rozet — emsal BMW|gs / Lexus|gs"),
    "Citroen|c5": ("ROZET", "Citroen C5 gercek rozet; Peugeot C5 diye bir arac satilmadi (PSA "
                            "platform ortakligi) — emsal birebir (Audi,Golf) deny satiri"),
    "Toyota|aygo": ("ROZET", "Toyota Aygo gercek rozet (A-segment uclusu 107/C1/Aygo); emsal "
                              "birebir mevcut Peugeot|107 / Citroen|c1 satirlari"),
    "Vespa|gts": ("ROZET", "Vespa GTS gercek rozet"),
    "Vespa|primavera": ("ROZET", "Vespa Primavera gercek rozet"),
    "Vespa|px": ("ROZET", "Vespa PX gercek rozet"),
    "Vespa|largeframe": ("ROZET", "Vespa Largeframe govde AILE adi; emsal birebir mevcut "
                                  "(\"Vespa\",\"Smallframe\")"),
    "Vespa|smallframe": ("ROZET", "Vespa Smallframe govde AILE adi (emsal Vespa|largeframe)"),
    "Vespa|50": ("ROZET", "Vespa 50 / V50 gercek rozet (ikonik tek arac, Vespa altinda TEKIL)"),
    "Vespa|50special": ("ROZET", "Vespa 50 Special gercek rozet (50'nin donanim rozeti)"),
    # Volvomk1 (K170) BEKLER: Ford|mk1 / Volkswagen|mk1 ile AYNI bekleyen hukum uyesi;
    # Mk1 bir NESIL isareti, rozet degil. Uc kol TEK turda, TEK hukumle kapanir -> K172.
}

ROZET_CAPRAZ_IZINLI_SAYISI = 67
ROZET_CAPRAZ_IZINLI_IMZA = "f3ccf9b717a42de5"  # K202 sonrasi: kapinin hesabiyla


def rozet_capraz_imzasi():
    """Envanterin ANAHTAR kimligi — sessiz genisleme/daralma kapida KIRMIZI yakar.
    YALNIZ anahtarlar imzalanir: sinif alani ("ROZET"/"BEKLER") AYRI bir eksende raporlanir;
    tek imzaya baglansaydi sinifi kaydiran mutant bu imzaya sirtini dayardi."""
    return hashlib.sha256(
        json.dumps(sorted(ROZET_CAPRAZ_IZINLI), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]


# 🔴 SINIF EKSENI KENDI IMZASINI TASIR (19 Agu, K202 kabul olcutu 4 — kontrol mutanti).
# OLCULDU: `rozet_capraz_imzasi()` YALNIZ anahtarlari imzaliyor ve "BEKLER" sinifi K19'da
# yalnizca BILGI satiri basiyor (KIRMIZI YAKMIYOR). Dolayisiyla bir satirin sinifini
# ROZET -> BEKLER kaydiran mutant HICBIR kapiyi yakmadan gecerdi: hukum sessizce
# "karar bekliyor"a duser, sayfa ise dogmaya devam ederdi. Anahtar ekseni sizintiyi
# (yargisiz cift) olcer, bu eksen HUKMUN KENDISINI olcer; ikisi AYRI kalir cunku tek
# imzaya baglansaydi sinif mutanti anahtar imzasina sirtini dayardi (yukaridaki not).
# GEREKCE METNI IMZAYA GIRMEZ: yazim duzeltmesi kapiyi yakmasin, HUKUM degisimi yaksin.
ROZET_CAPRAZ_SINIF_IMZA = "4fdb0b0c53f35094"  # K202 sonrasi: kapinin hesabiyla


def rozet_capraz_sinif_imzasi():
    """Envanterin SINIF kimligi: "<anahtar>|<SINIF>" cifti imzalanir (gerekce HARIC)."""
    return hashlib.sha256(
        json.dumps(sorted("%s|%s" % (k, v[0]) for k, v in ROZET_CAPRAZ_IZINLI.items()),
                   ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# KUSAK DISI JETONLAR — gramere UYAN ama AYNI ARAC AILESI OLMAYAN (marka, jeton)
# ciftleri (4 Agu, KraL hukmu; katlama paketinin istisna tablosu)
#
# BAGLAM: index.html KANONIK MODEL ESLEMESI blogundaki `kusakTabanlari()` bir jetonu
# "<taban> <kusak>" diye okur ve KELIME SINIRINDA katlar ("Golf 4" -> Golf, "Astra H" ->
# Astra). Gramer YAPISAL bir kuraldir; kusak sozcugunun ARACIN AYNI AILEDEN olup olmadigini
# bilemez. Bu tablo tam olarak o yargiyi tasir: gramere uysa bile katlanmayacak ciftler.
#
# 🔴 SINIR (Okan hukmu, `Zafira Life` dersi): kusak/donanim varyanti (ayni arac ailesi)
# KATLANIR; farkli arac (ayri platform/rozet) KATLANMAZ. `Zafira Life` bu tabloya
# GIRMEZ — gramer onu ZATEN katlamiyor ("Life" kapali gramerde yok) ve tabloya yazilsaydi
# grameri gevseten bir mutant (donanim listesine "life" eklemek) istisna tarafindan
# ORTULUR, kapi kirmizi YANMAZDI. Iki koruma ayri eksende olcusun diye ayri tutulur.
#
# OLCULDU (4 Agu, 17591 urun): gramer 74 jetonu katliyor; denetimde TEK YANLIS aile bulundu.
KUSAK_DISI_JETON = {
    ("Citroen", "Ami 6"): "Ami 6 (1961) klasik otomobil; `Ami` kovasindaki 15 urun 2020 "
                          "elektrikli dortteker Ami'ye ait — ayni ad, FARKLI arac",
    # 16 Agu, mimar hukumu (K117-B Toyota model kanonu): `AE86` 1983 Corolla Levin/Trueno'dur;
    # modern `86`/`GT86`/`GR86` ailesiyle AYNI ARAC DEGILDIR. Bugun bir katlama YOK, ama
    # yarin bir kural sessizce katlamasin diye kalici deny. (`86`/`GT86`/`GR86` birlestirmesi
    # BU SPEC'IN DISINDA — mimar ayri hukum yazacak.)
    ("Toyota", "AE86"): "AE86 = 1983 Corolla Levin/Trueno (Corolla 4. kusak AE86 sasi kodu); "
                        "modern `86`/`GT86`/`GR86` ailesiyle AYNI ARAC DEGIL — kalici deny",
}

KUSAK_DISI_SAYISI = 2
KUSAK_DISI_IMZA = "e7e4a44338472984"  # arama.kusak_disi_imzasi() ile hesaplandi


def kusak_disi_imzasi():
    """Tablonun ANAHTAR kimligi — sessiz genisleme/daralma kapida KIRMIZI yakar."""
    return hashlib.sha256(
        json.dumps(sorted("%s|%s" % (a, b) for a, b in KUSAK_DISI_JETON), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# MODEL OLMAYAN (marka, jeton) CIFTLERI — /marka/X/M/ sayfasi ACILMAZ (4 Agu, mimar hukmu)
#
# OLCULEN SIZINTI (canlida duruyordu): /marka/ford/focus-st/ (8 urun) ·
# /marka/ford/fiesta-st/ (3) · /marka/ford/ecoboost/ (3). `ST` bir DONANIM PAKETI,
# `EcoBoost` bir MOTOR AILESI — ikisi de MODEL degil; Focus ve Fiesta'yi BOLEREK kendi
# sayfalarini acmislardi.
#
# 🔴 NEDEN DUZ `MODEL_OLMAYAN_JETON`A EKLENMEDI: o kume MARKA-KORDUR. Oraya `GS` yazilsa
# /marka/bmw/gs/ ile /marka/citroen/gs/ BIRLIKTE olurdu, oysa ikisi ayri siniftir. Yargi
# marka-ozeldir -> ROZET_DISI_CIFT deseninde (marka, jeton) cifti tutulur.
#
# 🔴 YUKLEM BILESIK YAZIMI DA KAPSAR: `marka_jetonu_mu("Focus ST")` bugun False donuyordu
# (bilesik yazim hic yakalanmiyordu). Tuketici yuklem hem CIPLAK jetona ("ST", "EcoBoost")
# hem de SON KELIMEYE bakar ("Focus ST" -> "ST").
#
# URUN KAYBOLMAZ: sayfasi kapanan kovanin urunleri (a) kusak katlamasiyla ana modelin
# VARYANT ALT BOLUMUNDE (Focus ST -> /marka/ford/focus/), (b) her halukarda marka
# sayfasinda durur. Kapi bunu OLCER (kaybolan=0).
MODEL_OLMAYAN_CIFT = {
    ("Ford", "ST"): "donanim/performans paketi (Focus ST, Fiesta ST) — model degil; "
                    "urunler ana modelin varyant bolumunde",
    ("Ford", "ST Line"): "gorunum paketi — ST ile ayni sinif, ayri yazim",
    ("Ford", "EcoBoost"): "motor ailesi (1.0/1.5/2.3 EcoBoost) — arac modeli degil",
    # 4 Agu, mimar hukmu (cip satiri taramasi; CANLIDA duran sayfalar):
    # 🔴 IKISI DE MARKA-OZEL yazildi, MODEL_OLMAYAN_JETON'a (marka-KOR) EKLENMEDI:
    #   "iPhone" Apple'in GERCEK model adidir — marka-kor kumeye yazilsaydi ileride
    #   /marka/apple/iphone/ sayfasini da oldururdu; "Electric" ise baska bir markanin
    #   mesru model jetonu olabilir. Yargi yalnizca ARAC markasi altinda gecerlidir.
    ("Peugeot", "iPhone"): "Apple telefon modeli — arac modeli degil; kayitlarda jeton "
                           "telefon tutucusu uyumundan geliyor (CANLIDA /marka/peugeot/iphone/)",
    ("Mitsubishi", "Electric"): "'Mitsubishi Electric' SIRKET adinin ikinci kelimesi (beyaz "
                                "esya/klima kolu) — arac modeli degil; urunler Ev kategorisinde",
    # --- 5 Agu, mimar hukmu: BASLIK KOLU acilinca dogacak olan ve ACIKCA MODEL
    # OLMAYAN kovalar (cihaz/infotainment/aksesuar/govde-tipi/grup adi). Kalici deny:
    # allow envanterine hic girmedikleri icin zaten dogmazlar, buradaki kayit YARGININ
    # kendisidir (yarin baska bir kol ayni jetonu yeniden onerirse sessizce acilmasin).
    ("Audi", "AdBlue"): "dizel egzoz katki sivisi (AdBlue) — arac modeli degil",
    ("Audi", "Coupe"): "govde tipi sozcugu (Audi 80/B2 Coupe) — bagimsiz model adi degil",
    ("BMW", "Adventure"): "GS Adventure donanim/varyant soneki — bagimsiz model degil",
    ("BMW", "Cabrio"): "govde tipi sozcugu (1 Serisi Cabrio) — model degil",
    ("BMW", "Compact"): "govde tipi sozcugu (3 Serisi Compact) — model degil",
    ("BMW", "Connected Ride"): "BMW telefon kizagi AKSESUAR sistemi — arac modeli degil",
    ("Ford", "MK1"): "ciplak kusak degistiricisi (Mk1 Escort/Capri/Transit) — model degil",
    ("Ford", "Sync"): "Ford SYNC infotainment sistemi — arac modeli degil",
    ("Ford", "Truck"): "arac sinifi sozcugu (Ford Truck 1973-1979) — model adi degil",
    ("Opel", "MagSafe"): "Apple manyetik tutucu standardi — arac modeli degil",
    ("Peugeot", "Stellantis"): "sirket/grup adi — arac modeli degil",
    # 6 Agu, mimar hukmu H2: `E-Tech` Renault'nun ELEKTRIFIKASYON/guc aktarma ROZETIDIR
    # (Megane E-Tech, Scenic E-Tech, 5 E-Tech), bagimsiz bir arac modeli DEGIL -> CIPLAK
    # `E-Tech` kovasi (10 urun) SAYFA ACMAZ.
    # 🔴 BILESIK YAZIMLAR KAPANMAZ: `model_olmayan_cift_mi` son-kelime kolu artik YALNIZ
    # KUSAK/DONANIM DEGISTIRICILERINE isler (`ST`, `Mk1`); `E-Tech` degistirici GRAMERINDE
    # DEGIL, bu yuzden `/marka/renault/5-e-tech/` (4 urun) ve `/marka/renault/megane-e-tech/`
    # sayfalari ACIK KALIR. Rozeti tasiyan urunler ayrica taban modele KATLANIR: "Renault 5
    # E-Tech ..." baslikli urunler `/marka/renault/5/` sayfasinda DURUR (turnusol: deny
    # oncesi 14, sonrasi 14 — DUSMEZ).
    ("Renault", "E-Tech"): "elektrifikasyon/guc aktarma rozeti (5 E-Tech, Megane E-Tech) — "
                           "bagimsiz arac modeli degil; urunler taban model sayfasinda kalir",
    ("Skoda", "MagSafe"): "Apple manyetik tutucu standardi — arac modeli degil",
    ("Toyota", "MagSafe"): "Apple manyetik tutucu standardi — arac modeli degil",
    ("Volkswagen", "Cabriolet"): "govde tipi sozcugu — model degil",
    ("Volkswagen", "MK2"): "ciplak kusak degistiricisi — model degil",
    ("Volkswagen", "Mk4"): "ciplak kusak degistiricisi — model degil",
    ("Volkswagen", "iPhone"): "Apple telefon modeli — arac modeli degil (Peugeot emsali)",
    ("Volvo", "MagSafe"): "Apple manyetik tutucu standardi — arac modeli degil",
    ("Volvo", "Sierra"): "deniz yedek parca URETICI markasi (Volvo Penta kayitlarindan) — Volvo'nun modeli degil",
    ("Yamaha", "Quad Lock"): "ucuncu taraf telefon tutucu markasi — Yamaha modeli degil",
    ("Yamaha", "Stage"): "'Stage 2' tuning asamasi ifadesi — model degil",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum B + D — yargisiz kovalarin DENY tarafi):
    # 🔴 `Yamaha|660` CIPLAK SAYIDIR: hangi araci adlandirdigi BELIRSIZ (XT660, MT-660,
    # Raptor 660 …). H1 zaten ciplak sayiyi disarida tutuyor; bu satir hukmu KALICI kilar
    # (yarin bir kol ayni jetonu yeniden onerirse sessizce acilmasin). Tekil giris
    # ACILMADI: 3 urun icin ayri sayfa yargisi verilmedi.
    ("Yamaha", "660"): "ciplak sayi — hangi araci adlandirdigi belirsiz (XT660/Raptor 660); "
                       "arac modeli adi degil, urunler marka sayfasinda kalir",
    # `Westfalia` bir KAMPER DONUSTURUCUSUDUR (Westfalia-Werke); VW Transporter/T3'u
    # donusturur ama VW'nin bir MODELI degildir. Urunler taban model sayfasinda kalir.
    ("Volkswagen", "Westfalia"): "kamper donusturucusu (Westfalia-Werke) — VW'nin arac "
                                 "modeli degil; urunler taban model sayfasinda kalir",
    # 16 Agu, mimar hukumu (K117-B Toyota model kanonu): 6 jeton MODEL DEGIL — sayfalari
    # KAPANIR, urunler taban modelde kalir. Emsaller Ford ST / ST Line / EcoBoost,
    # Yamaha Quad Lock, Volvo Sierra. Yargi marka-ozel.
    ("Toyota", "TRD"): "Toyota Racing Development donanim/performans rozeti — arac modeli "
                       "degil; urunler taban model sayfasinda kalir (Ford ST emsali)",
    ("Toyota", "TRD Pro"): "TRD ile ayni sinif, ayri yazim — arac modeli degil (Ford ST "
                           "Line emsali)",
    ("Toyota", "22RE"): "motor kodu (22R-E) — arac modeli degil (Ford EcoBoost emsali)",
    ("Toyota", "4AGE"): "motor kodu (4A-GE) — arac modeli degil (Ford EcoBoost emsali)",
    ("Toyota", "Scan Gauge"): "ucuncu taraf OBD gosterge markasi (ScanGauge) — Toyota "
                              "modeli degil (Yamaha Quad Lock emsali)",
    ("Toyota", "107"): "`107` Peugeot'nun modelidir (Aygo/C1/107 uclusu ayni araci "
                      "paylasir) — Toyota'nin modeli degil (Volvo Sierra emsali)",
    # 16 Agu, mimar hukumu (K117-C model kanonu — siniflandirmanin MODEL onerilerinin
    # mimar tarafindan REDDEDILEN 5 hatali jetonu, kalici deny):
    ("Toyota", "BRZ"): "BRZ Subaru'nun modeli (Subaru BRZ / Toyota 86 ikizi) — "
                       "Toyota'nin modeli degil",
    ("Subaru", "FR-S"): "FR-S Scion'un modeli (Toyota GT86 / Scion FR-S / Subaru "
                        "BRZ uclusu) — Subaru'nun modeli degil",
    ("Citroen", "107"): "`107` Peugeot'nun modelidir (Aygo/C1/107 uclusu ayni "
                       "araci paylasir) — Citroen'in modeli degil (Toyota|107 emsali)",
    ("Peugeot", "DS"): "DS Automobiles Peugeot'dan AYRI bir markadir — Peugeot'nun "
                      "modeli degil",
    ("Hyundai", "Coupe"): "govde tipi sozcugu (Audi|Coupe emsali) — bagimsiz model "
                          "adi degil",
}

MODEL_OLMAYAN_CIFT_SAYISI = 40
MODEL_OLMAYAN_CIFT_IMZA = "4aa789c556ac2871"  # arama.model_olmayan_cift_imzasi() ile hesaplandi


def model_olmayan_cift_imzasi():
    """Cift kumesinin ANAHTAR kimligi (S2 dersi: SAYI degil KIMLIK)."""
    return hashlib.sha256(
        json.dumps(sorted("%s|%s" % (a, b) for a, b in MODEL_OLMAYAN_CIFT), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# DEGISTIRICI SEKILLI SAYFA IZNI — "<taban> <degistirici>" adli YAYIMLANAN kovalarin
# DONMUS envanteri (4 Agu, mimar hukmu; sizinti ekseninin ALLOW tarafi)
#
# NE ICIN: kusak/donanim SEKILLI bir kova sayfa aciyorsa bu bir KARARDIR — ya mesru bir
# kusak sayfasidir (Astra H, Golf 4: kapanmaz hukmu) ya da bir sizintidir (Focus ST).
# Kapi jeneratoru KOSTURUP yayimlanan (marka, canon) KUMESINI cikarir ve bu envanterle
# BIREBIR karsilastirir. Karsilastirma birimi KUME'dir, SAYI degil: bir sayfa olup biri
# dogunca sayi sabit kalir ve sapma gizlenirdi ([[hukum-yanlis-birimde]]).
#
# YENI GIRIS = MIMAR HUKMU: katalog buyudukce yeni bir degistirici-sekilli kova ESIK'i
# gecerse kapi KIRMIZI yanar ve karar ister (allow'a mi deny'a mi). Sessiz sayfa dogmaz.
DEGISTIRICI_SAYFA_IZNI = {
    "Ford|modelt": "Ford Model T — gercek model adi (T harfi degistirici DEGIL)",
    "Opel|asconac": "Ascona C — mesru kusak sayfasi",
    "Opel|astraf": "Astra F — mesru kusak sayfasi",
    "Opel|astrag": "Astra G — mesru kusak sayfasi",
    "Opel|astrah": "Astra H — mesru kusak sayfasi",
    "Opel|astraj": "Astra J — mesru kusak sayfasi",
    "Opel|astrak": "Astra K — mesru kusak sayfasi",
    "Opel|corsac": "Corsa C — mesru kusak sayfasi",
    "Opel|mantab": "Manta B — mesru kusak sayfasi",
    "Opel|tigraa": "Tigra A — mesru kusak sayfasi",
    "Opel|vectrac": "Vectra C — mesru kusak sayfasi",
    "Renault|megane2": "Megane 2 — mesru kusak sayfasi",
    "Renault|megane3": "Megane 3 — mesru kusak sayfasi",
    "Volkswagen|golf4": "Golf 4 — mesru kusak sayfasi",
    "Volkswagen|golfr": "Golf R — mesru donanim/kusak sayfasi (VW'nin R serisi)",
    "Volkswagen|type2": "VW Type 2 (Bulli) — gercek model adi, Type 1'den AYRI arac",
    "Yamaha|tracer7": "Tracer 7 — gercek model adi (motosiklet hacim kirilimi)",
    # 5 Agu — BASLIK KOLU ile ESIK'i gecen, DEGISTIRICI SEKILLI ama GERCEK model adlari
    # (bu envanter SIZINTI eksenidir; ucunun BASLIK-DOGAN yargisi 7 Agu'dan beri H1/H3
    # KURAL KOLUNDAN gelir — anahtarlari kural seklinde oldugu icin BASLIK_DOGAN_ALLOW'da
    # YAZILI DEGIL, bkz. o tablonun TURETME KURALI).
    "Opel|grandlandx": "Opel Grandland X — gercek model adi (X harfi degistirici DEGIL)",
    "Suzuki|wagonr": "Suzuki Wagon R — gercek model adi (R harfi degistirici DEGIL)",
    "Volkswagen|type1": "VW Type 1 (Beetle) — gercek model adi, Type 2'den AYRI arac",
}

DEGISTIRICI_SAYFA_IZNI_SAYISI = 20
DEGISTIRICI_SAYFA_IZNI_IMZA = "62cb38aacebbaa5f"


def degistirici_izni_imzasi():
    return hashlib.sha256(
        json.dumps(sorted(DEGISTIRICI_SAYFA_IZNI), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# BASLIK KOLUNDAN DOGAN SAYFA IZNI — KURALIN YARGILAYAMADIGI **KALINTI** ENVANTERI
# (5 Agu mimar hukmu: "yargisiz sayfa DOGMAZ" · 7 Agu TURETME HUKMU: kuralin yargiladigi
#  cift BURAYA YAZILMAZ · 7 Agu UYKUDA HUKMU: is yapmayan giris BAYAT DEGILDIR)
#
# NE ICIN: model uyelik yuklemine BASLIKTA TAM KELIME kolu eklendi. Bu kol MEVCUT
# kovalari buyutur (olculdu: 455 sayfa buyudu, 0 kucuLdu) ama bir kismini da ESIK'in
# uzerine tasiyarak YENI SAYFA dogurur. Yeni dogan her kova bir KARARDIR: kimi gercek
# arac modelidir, kimi bir CIHAZ/INFOTAINMENT adidir (`Sync`, `iPhone`, `MagSafe`),
# kimi bir MOTOR AILESI ya da SASI KODUDUR (`M54`, `N47`, `E92`).
#
# 🔴 KURAL FAIL-CLOSED: yargisiz kova SESSIZCE dogmaz. Yargi UC KAYNAKLIDIR ve ikisi
# KURALDIR (marka_model_build.baslik_yargisi_var_mi):
#     (a) BU ENVANTER          — tekil, elle yargilanmis ciftler,
#     (b) H1 sasi/motor kodu   — TEK jeton + en az bir HARF ve en az bir RAKAM,
#     (c) H3 ayri arac adi     — `<taban> <degistirici>`, kuyrugu DONANIM degil.
# Envanterde/kuralda OLMAYAN kova dogmaz — urunu KAYBOLMAZ (marka sayfasinda ve kendi
# gercek model sayfasinda durur; kapi kaybolan=0 olcer).
#
# 🔴 TURETME KURALI (7 Agu, mimar hukmu — 6. tekrari SINIF olarak kapatir):
#   GIRISIN ANAHTARI (b) ya da (c) SEKLINDEYSE O GIRIS BURAYA HIC YAZILMAZ: kural onu
#   ZATEN yargiliyor ve KURAL KOLU KATALOG BUYUDUKCE BAYATLAMAZ. Bu envanter yalnizca
#   kuralin SEKIL OLARAK goremedigi KALINTIYI tasir — uc sinif, hepsi gerekceli:
#     · CIPLAK SAYI          (`86`, `107`, `300`, `340`, `924`; H1'in HARF sartinin disi)
#     · TEK JETON + RAKAMSIZ (`Katana`, `Bora`, `CBR`, `C-Class`; ne H1 ne H3 gorur)
#     · ARAC DISI MUAF       (`Yamaha|P-45`, `Yamaha|Recording Custom`; SEKIL_KURALI_MUAF
#                             kurali o ciftte SUSTURUR, sayfayi yalniz bu giris tasir)
#   OLCULDU (7 Agu, 22.376 urun): 185 kayittan 84'unun ANAHTARI H1/H3 seklindeydi ve giris
#   ISLEVSIZDI -> silindi; asagida 101 kalinti + 1 geri konan (`Mitsubishi|Galant`) = 102.
#   Yayimlanan baslik-dogan sayfa kumesi DEGISMEDI (327 -> 327).
#   Kapi bu borcu K21b ekseninde olcer: anahtari H1/H3 seklinde bir giris KIRMIZI yakar.
#   🔴 OLCUT GIRISIN ANAHTARIDIR, KATALOGTAKI YAZIM DEGIL -> yeni bir urun partisi bu
#   ekseni ASLA kirmizi yakamaz (yasak kume tabana gore turemez).
#
# 🔴 UYKUDA ≠ BAYAT (7 Agu, mimar hukmu — YAYINI 6 PARTI BOYUNCA DURDURAN SINIF):
#   Bir kova jeton yolundan (marka[]/uyum[]) ESIK'i TEK BASINA gecince artik yargiya
#   IHTIYAC DUYMAZ (`baslik_dogan=False`) ve girisi o gun is yapmaz. ESKI olcut
#   (`envanter - yayimlanan_baslik_dogan`) bunu "BAYAT" ilan edip kapiyi KIRMIZI
#   yakiyordu; yani ENVANTERI KATALOG HACMININ FONKSIYONU yapmisti ve her urun partisinde
#   yayini durduruyordu ([[envanter-drift-parti-basina]] · [[tekil-yama-sinifi-kapatmaz]]).
#   HUKUM: giris bir HUKUMDUR, bir SAYAC DEGIL — kova yargiyi sormuyorsa hukum UYKUDADIR
#   (kapi BILGI olarak sayar, KIRMIZI YAKMAZ) ve kova yeniden baslik-dogan olursa sayfayi
#   YINE o hukum tasir. Kirmizi kalan TEK bayatlik: kovanin KENDISI katalogda YOK (OLU) ya
#   da iki giris AYNI kanona cakisiyor — ikisi de katalog hacmine duyarsizdir.
#   ⚠️ 6 Agu ve 7 Agu'da bu yuzden ELLE SILINEN dokuz giris (`Datsun|280Z`, `Honda|VFR 800`,
#   `Nissan|240SX`, `Suzuki|GSF 650`, `Yamaha|FZ1`, `Yamaha|Tracer 900`, `Yamaha|XSR 700`,
#   `Yamaha|XJ 600` H1/H3 kuralindadir — dogru yer kural kolu; `Mitsubishi|Galant` ise
#   TEK JETON RAKAMSIZDIR, yani kural onu GORMEZ: o hukum GEREKSIZ kaybedilmisti ve
#   asagida GERI KONDU (UYKUDA olarak durur, hicbir sayfayi degistirmez).
#
# 🔴 DENY AYRI TUTULUR: "acikca model DEGIL" hukmu MODEL_OLMAYAN_CIFT'e yazilir (kalici,
# marka-ozel); buraya yazilmayan her sey "HENUZ YARGILANMADI" demektir, "reddedildi" degil.
# 🔴 KARSILASTIRMA BIRIMI KUME'dir, SAYI degil (DEGISTIRICI_SAYFA_IZNI ile ayni disiplin).
BASLIK_DOGAN_ALLOW = {
    ("Alfa Romeo", "Alfetta"): "arac/motosiklet model adi",
    ("Alfa Romeo", "Giulietta"): "arac/motosiklet model adi",
    ("Alfa Romeo", "GTV"): "arac/motosiklet model adi",
    ("Alfa Romeo", "Nord"): "arac/motosiklet motor ailesi adi",
    ("Audi", "TT"): "arac/motosiklet model adi",
    ("Chrysler", "300"): "arac/motosiklet model adi",
    ("Chrysler", "Voyager"): "arac/motosiklet model adi",
    ("Citroen", "AX"): "arac/motosiklet model adi",
    ("Citroen", "BX"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum A — capraz marka rozetinin TEK ALLOW'u):
    # `Relay` Jumper'in GERCEK Ingiltere rozetidir (ikizin adi degil, KENDI adi) —
    # emsal birebir `Renault|Duster`/`Renault|Logan` satirlaridir.
    ("Citroen", "Relay"): "Citroen Relay = Jumper'in GERCEK Ingiltere rozeti",
    ("Citroen", "XM"): "arac/motosiklet model adi",
    # 13 Agu DS-4: ZX gercek Citroen modeli (1991-1998); H1/H3 sekil yuklemi rakamsiz tek
    # jetonu tanimiyor, sayfa yayinda ve 3 urun tasiyor — tekil envanter girisi.
    ("Citroen", "ZX"): "arac/motosiklet model adi (tek jeton rakamsiz — kural GORMEZ)",
    ("Fiat", "Doblo"): "arac/motosiklet model adi",
    ("Fiat", "Fiorino"): "arac/motosiklet model adi",
    ("Fiat", "Qubo"): "arac/motosiklet model adi",
    ("Ford", "Connect"): "arac/motosiklet model adi",
    ("Ford", "Contour"): "arac/motosiklet model adi",
    ("Ford", "Cortina"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum D — TEKIL GERCEK MODEL ADI):
    # Transit/Tourneo **Custom** gercek bir model adidir (govde tipi/donanim sozcugu degil).
    ("Ford", "Custom"): "arac/motosiklet model adi (Transit/Tourneo Custom)",
    ("Ford", "Everest"): "arac/motosiklet model adi",
    ("Ford", "Fairlane"): "arac/motosiklet model adi",
    ("Ford", "Galaxy"): "arac/motosiklet model adi",
    ("Ford", "Territory"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum B — CIPLAK AILE ONEKI SAYFA ALIR):
    # `CBR`/`CRF`/`GX` tek bir arac degil bir AILE adidir; musteri parcayi aile adiyla
    # ariyor. Emsal, H3 KURAL KOLUNUN yargiladigi `BMW|K Serisi` ve `2/3/5/6 Serisi`
    # sayfalaridir (aile sayfasi mesru; o ciftler kuralda oldugu icin BURADA YAZILI DEGIL).
    # 🔴 KURAL DEGIL TEKIL GIRIS: sekil kurali (H1/H3) bu jetonlari GORMEZ (tek jeton,
    # rakamsiz) — envanter yalnizca yargilanmis cifti tasir, kural gevsemez.
    ("Honda", "CBR"): "arac/motosiklet AILE adi (CBR serisi)",
    ("Honda", "CR-Z"): "arac/motosiklet model adi",
    ("Honda", "CRF"): "arac/motosiklet AILE adi (CRF serisi)",
    ("Honda", "Dominator"): "arac/motosiklet model adi",
    ("Honda", "Fireblade"): "arac/motosiklet model adi",
    ("Honda", "Forza"): "arac/motosiklet model adi",
    ("Honda", "GX"): "arac/motosiklet AILE adi (GX motor serisi)",
    ("Honda", "HR-V"): "arac/motosiklet model adi",
    ("Honda", "Hornet"): "arac/motosiklet model adi",
    ("Honda", "Clarity"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum D — TEKIL GERCEK MODEL ADI, rakamsiz tek jeton):
    ("Honda", "Legend"): "arac/motosiklet model adi",
    ("Honda", "Magna"): "arac/motosiklet model adi",
    ("Honda", "PCX"): "arac/motosiklet model adi",
    ("Honda", "Prologue"): "arac/motosiklet model adi",
    ("Honda", "Recon"): "arac/motosiklet model adi",
    ("Honda", "Sabre"): "arac/motosiklet model adi",
    ("Honda", "Stepwgn"): "arac/motosiklet model adi",
    ("Honda", "Talon"): "arac/motosiklet model adi",
    ("Honda", "Zoomer"): "arac/motosiklet model adi",
    ("Hyundai", "Accent"): "arac/motosiklet model adi",
    ("Hyundai", "Elantra"): "arac/motosiklet model adi",
    ("Hyundai", "Kona"): "arac/motosiklet model adi",
    ("Hyundai", "Veloster"): "arac/motosiklet model adi",
    ("Jaguar", "S-Type"): "arac/motosiklet model adi",
    ("Kia", "Carnival"): "arac/motosiklet model adi",
    ("Kia", "e-Niro"): "arac/motosiklet model adi",
    ("Kia", "Picanto"): "arac/motosiklet model adi",
    ("Kia", "ProCeed"): "arac/motosiklet model adi",
    ("Kia", "Sedona"): "arac/motosiklet model adi",
    ("Kia", "Spectra"): "arac/motosiklet model adi",
    ("Kia", "Stinger"): "arac/motosiklet model adi",
    ("Mazda", "Demio"): "arac/motosiklet model adi",
    ("Mercedes", "Actros"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum C — MERCEDES SINIF ADLARI):
    # `C-Class` ve `E-Klasse` GERCEK Mercedes sinif adlaridir; birlesecek ikizleri YOK
    # (katalogda `Mercedes|C` ya da `Mercedes|E` kovasi bulunmuyor), o yuzden MODEL_ALIAS
    # degil TEKIL GIRIS ile yargilandilar. `A-Class` ve `V-Class` aileleri MODEL_ALIAS ile
    # birlestigi icin resmi uyelikten (baslik kolu OLMADAN) esigi geciyor ve buraya
    # YAZILMAZ — yazilsaydi envanter BAYAT olurdu (kapi K21 kirmizi yakar).
    ("Mercedes", "C-Class"): "arac/motosiklet model adi (Mercedes C sinifi)",
    ("Mercedes", "CLA"): "arac/motosiklet model adi",
    ("Mercedes", "E-Klasse"): "arac/motosiklet model adi (Mercedes E sinifi)",
    ("Mercedes", "GLK"): "arac/motosiklet model adi",
    ("Mercedes", "GLS"): "arac/motosiklet model adi",
    ("Mercedes", "SLK"): "arac/motosiklet model adi",
    ("Mitsubishi", "ASX"): "arac/motosiklet model adi",
    ("Mitsubishi", "Carisma"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum B): `Evolution` Lancer Evolution AILESIDIR
    # (`Mitsubishi|Lancer Evolution` cifti H3 KURAL KOLUNDA yargilanir, envanterde YAZILI
    # DEGIL) — ciplak aile adi da sayfa alir.
    ("Mitsubishi", "Evolution"): "arac/motosiklet AILE adi (Lancer Evolution)",
    # 🔴 7 Agu GERI KONDU (UYKUDA hukmu): `Galant` TEK JETON + RAKAMSIZDIR, yani H1/H3
    # kurali onu GORMEZ. Giris 7 Agu'da yalnizca "bugun is yapmiyor" diye silinmisti —
    # bayat degil UYKUDA idi. Kova bir gun yeniden baslik-dogan olursa sayfayi bu hukum
    # tasir; bugun hicbir sayfayi degistirmez (olculdu: sayfa kumesi AYNI).
    ("Mitsubishi", "Galant"): "arac/motosiklet model adi (tek jeton rakamsiz — kural GORMEZ)",
    ("Mitsubishi", "Minicab"): "arac/motosiklet model adi",
    ("Mitsubishi", "i-MiEV"): "arac/motosiklet model adi",
    ("Nissan", "Armada"): "arac/motosiklet model adi",
    ("Nissan", "Juke"): "arac/motosiklet model adi",
    ("Nissan", "Maxima"): "arac/motosiklet model adi",
    ("Nissan", "Murano"): "arac/motosiklet model adi",
    ("Nissan", "Rogue"): "arac/motosiklet model adi",
    ("Nissan", "Stagea"): "arac/motosiklet model adi",
    ("Nissan", "Sunny"): "arac/motosiklet model adi",
    ("Nissan", "Terrano"): "arac/motosiklet model adi",
    ("Nissan", "Tsuru"): "arac/motosiklet model adi",
    ("Nissan", "Versa"): "arac/motosiklet model adi",
    ("Peugeot", "1007"): "arac/motosiklet model adi",
    ("Peugeot", "107"): "arac/motosiklet model adi",
    ("Peugeot", "2008"): "arac/motosiklet model adi",
    ("Peugeot", "206+"): "arac/motosiklet model adi",
    ("Peugeot", "405"): "arac/motosiklet model adi",
    ("Peugeot", "407"): "arac/motosiklet model adi",
    ("Peugeot", "508"): "arac/motosiklet model adi",
    ("Peugeot", "Expert"): "arac/motosiklet model adi",
    ("Peugeot", "Traveller"): "arac/motosiklet model adi",
    ("Porsche", "924"): "arac/motosiklet model adi",
    ("Porsche", "964"): "arac/motosiklet model adi",
    ("Porsche", "986"): "arac/motosiklet model adi",
    ("Porsche", "993"): "arac/motosiklet model adi",
    ("Porsche", "Cayenne"): "arac/motosiklet model adi",
    ("Renault", "Arkana"): "arac/motosiklet model adi",
    ("Seat", "Alhambra"): "arac/motosiklet model adi",
    ("Seat", "Altea"): "arac/motosiklet model adi",
    ("Seat", "Cordoba"): "arac/motosiklet model adi",
    ("Skoda", "Rapid"): "arac/motosiklet model adi",
    ("Suzuki", "Boulevard"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum B — CIPLAK AILE ONEKI):
    ("Suzuki", "DR"): "arac/motosiklet AILE adi (DR serisi)",
    ("Suzuki", "Escudo"): "arac/motosiklet model adi",
    ("Suzuki", "Freewind"): "arac/motosiklet model adi",
    ("Suzuki", "GSF"): "arac/motosiklet AILE adi (GSF serisi)",
    ("Suzuki", "GSX"): "arac/motosiklet AILE adi (GSX serisi)",
    ("Suzuki", "Hayabusa"): "arac/motosiklet model adi",
    ("Suzuki", "Katana"): "arac/motosiklet model adi",
    ("Suzuki", "Maruti"): "arac/motosiklet AILE adi",
    ("Suzuki", "RM"): "arac/motosiklet AILE adi (RM/RM-Z kros serisi)",
    ("Subaru", "Sambar"): "arac/motosiklet model adi",
    ("Subaru", "STI"): "arac/motosiklet AILE adi",
    ("Subaru", "XV"): "arac/motosiklet model adi",
    # 🔴 6 Agu, mimar hukmu (ADIM 3 / hukum A — TEKIL GIRIS, KURAL DEGISMEDI):
    # `86` Toyota'nin GERCEK rozetidir (GT86/GR86 kardesleri zaten yayinda) AMA CIPLAK
    # SAYIDIR: H1 sekil kurali ciplak sayiyi DISARIDA tutar ve TUTMAYA DEVAM EDER.
    # Bu satir yalnizca BU cifti acar; `Yamaha|660` gibi diger ciplak sayilar kapali kalir
    # (emsal: `Ford|raptor`/`Yamaha|raptor` ad-cakismasi satirlari — tekil vaka yargisi).
    # Jeton TEHLIKE sinifinda kalir: yalniz marka+model BITISIK ifadeyle eslesir.
    ("Toyota", "86"): "Toyota 86 GERCEK rozet (ciplak sayi — TEKIL giris, H1 kurali disi)",
    ("Toyota", "Matrix"): "arac/motosiklet model adi",
    ("Toyota", "Raize"): "arac/motosiklet model adi",
    ("Toyota", "Starlet"): "arac/motosiklet model adi",
    ("Toyota", "Tercel"): "arac/motosiklet model adi",
    # 16 Agu, mimar hukumu (K117-B Toyota model kanonu): `TRD` Toyota Racing Development
    # donanim/performans ROZETIDIR, bagimsiz arac modeli DEGIL — MODEL_OLMAYAN_CIFT'te deny.
    ("Toyota", "Vitz"): "arac/motosiklet model adi",
    ("Volkswagen", "Bora"): "arac/motosiklet model adi",
    ("Volkswagen", "CC"): "arac/motosiklet model adi",
    ("Volkswagen", "Caravelle"): "arac/motosiklet model adi",
    ("Volkswagen", "Crafter"): "arac/motosiklet model adi",
    ("Volkswagen", "Eos"): "arac/motosiklet model adi",
    ("Volkswagen", "Käfer"): "arac/motosiklet model adi",
    ("Volkswagen", "Multivan"): "arac/motosiklet model adi",
    ("Volkswagen", "Pointer"): "arac/motosiklet model adi",
    ("Volkswagen", "Taos"): "arac/motosiklet model adi",
    ("Volkswagen", "Vento"): "arac/motosiklet model adi",
    # 6 Agu, mimar hukmu (ADIM 3 / hukum D): `Vocho` Beetle'in MEKSIKA lakabidir —
    # gercek bir arac adlandirmasi (emsal `Volkswagen|Käfer` satiri, Almanca lakap).
    ("Volkswagen", "Vocho"): "arac/motosiklet model adi (Beetle'in Meksika adi)",
    ("Volvo", "340"): "arac/motosiklet model adi",
    ("Volvo", "480"): "arac/motosiklet model adi",
    ("Volvo", "Amazon"): "arac/motosiklet model adi",
    ("Yamaha", "Grizzly"): "arac/motosiklet model adi",
    ("Yamaha", "DragStar"): "arac/motosiklet model adi",
    # 🔴 6 Agu, mimar hukmu (ADIM 3 / hukum E — ARAC DISI, TEKIL GIRISLE DOGAR):
    # Yamaha cok-dikey bir markadir; bu iki sayfa GERCEK Yamaha urun modelidir ama ARAC
    # DEGILDIR (P-45 dijital piyano, Recording Custom davul kiti). Sayfalar KALIR — bu
    # katalog arac disi kategorileri de satiyor — ama SEKIL KURALIYLA degil BURADAN dogar:
    # ciftler ayrica SEKIL_KURALI_MUAF'ta ve H1/H3 onlara yargi VERMEZ, boylece kural
    # arka planda rastgele arac disi jetonlara acik kalmaz.
    ("Yamaha", "P-45"): "ARAC DISI urun modeli (dijital piyano) — tekil giris",
    ("Yamaha", "Recording Custom"): "ARAC DISI urun modeli (davul kiti) — tekil giris",
    ("Yamaha", "Seca"): "arac/motosiklet model adi",
    ("Yamaha", "TDM"): "arac/motosiklet AILE adi (TDM serisi)",
    ("Yamaha", "TMAX"): "arac/motosiklet model adi",
    ("Yamaha", "YBR"): "arac/motosiklet model adi",
    ("Yamaha", "XSR"): "arac/motosiklet AILE adi (XSR serisi)",
    ("Yamaha", "XVS"): "arac/motosiklet AILE adi (XVS serisi)",
    # 16 Agu, mimar hukumu (K117-C model kanonu): BASLIK KOLUYLA dogan, >= ESIK(3) urunlu
    # ama yargisiz oldugu icin model listesine hic girmeyen 250 kovadan siniflandirma ile
    # ayiklanan 17 GERCEK MODEL — model listesine girer.
    ("Vespa", "Ciao"): "arac/motosiklet model adi (Piaggio Ciao — Vespa ailesi)",
    ("Vespa", "PX"): "arac/motosiklet model adi",
    ("Vespa", "GTS"): "arac/motosiklet model adi",
    ("Vespa", "Smallframe"): "arac/motosiklet govde AILE adi (Vespa Smallframe)",
    ("Vespa", "Cosa"): "arac/motosiklet model adi",
    ("Vespa", "Bravo"): "arac/motosiklet model adi (Piaggio Bravo — Vespa ailesi)",
    ("Vespa", "Fly"): "arac/motosiklet model adi (Piaggio Fly — Vespa ailesi)",
    ("Vespa", "50"): "arac/motosiklet model adi (Vespa 50 — ikonik tek arac, ciplak "
                    "sayi ama Vespa altinda TEKIL)",
    ("Lexus", "GS"): "arac/motosiklet model adi",
    # `Sierra` Ford'un gercek modelidir; deniz yedek parca ureticisi olarak BASKA
    # markalarda deny (Volvo Sierra emsali) — yargi marka-ozeldir.
    ("Ford", "Sierra"): "arac/motosiklet model adi (Volvo Sierra emsali — yargi "
                        "marka-ozel)",
    ("Mazda", "5"): "arac/motosiklet model adi (Mazda 2/3/6 emsali)",
    # `Duster` Dacia Duster'in Renault yazimidir (ikiz model); tekil girisle dogar.
    ("Renault", "Duster"): "arac/motosiklet model adi (Dacia Duster'in Renault yazimi)",
    ("Renault", "Sandero"): "arac/motosiklet model adi",
    ("Nissan", "Primastar"): "arac/motosiklet model adi",
    # `Genesis` Hyundai'nin 2008-2016 doneminde ayri marka OLMA DAN ONCEki model adidir.
    ("Hyundai", "Genesis"): "arac/motosiklet model adi (marka olmadan onceki adi)",
    ("Peugeot", "203"): "arac/motosiklet model adi",
    ("Yamaha", "Raptor"): "arac/motosiklet model adi (ATV serisi)",
}

BASLIK_DOGAN_ALLOW_SAYISI = 157
BASLIK_DOGAN_ALLOW_IMZA = "8b011d4fd0bcacae"  # arama.baslik_dogan_allow_imzasi() ile hesaplandi


def baslik_dogan_allow_imzasi():
    """Envanterin ANAHTAR kimligi (S2 dersi: SAYI degil KIMLIK)."""
    return hashlib.sha256(
        json.dumps(sorted("%s|%s" % (a, b) for a, b in BASLIK_DOGAN_ALLOW),
                   ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# SEKIL KURALI MUAFIYETI — H1/H3 KURALININ YARGI VERMEDIGI (marka, jeton) ciftleri
# (6 Agu, mimar hukmu — ADIM 3 / hukum E)
#
# NE ICIN: H1 (`sasi_motor_kodu_mu`) ve H3 (`ayri_arac_adi_mi`) ARAC TANIMLAYICISI
# hukmudur ve YAZILABILIR bir kuraldir — ama kural jetonun SEKLINE bakar, "bu bir ARAC
# mi" sorusunu bilemez. Olculdu (6 Agu, 19.999 urun): kural 113 sayfa doguruyor ve
# bunlarin 111'i Otomobil/Motosiklet; IKISI ARAC DISI (Yamaha cok-dikey bir marka):
#   /marka/yamaha/p-45/            (4 urun, Elektronik — dijital piyano; H1 sekli)
#   /marka/yamaha/recording-custom/ (3 urun, Oyun/Hobi — davul kiti; H3 sekli)
#
# 🔴 HUKUM: SAYFALAR KALIR (gercek model, gercek parca, bu katalog arac disi kategorileri
# de satiyor) AMA SEKIL KURALIYLA DEGIL, BASLIK_DOGAN_ALLOW'daki TEKIL GIRISLE dogarlar.
# Bu tablo kuralin yargisini o ciftlerde KAPATIR; boylece kural arka planda rastgele
# arac disi jetonlara acik kalmaz ve her yeni arac disi sayfa MIMAR ONUNE gelir.
#
# 🔴 TEK BASINA SAYFA KAPATMAZ / ACMAZ: muaf bir cift envanterde DE varsa dogar, yoksa
# dogmaz. Ikisi AYRI eksendir ve kapi ikisini AYRI olcer (K22).
# 🔴 KARSILASTIRMA BIRIMI KUME'dir, SAYI degil (ROZET_DISI_CIFT ile ayni disiplin).
SEKIL_KURALI_MUAF = {
    ("Yamaha", "P-45"): "dijital piyano (Elektronik) — H1 sekline uyuyor ama ARAC DEGIL",
    ("Yamaha", "Recording Custom"): "davul kiti (Oyun/Hobi) — H3 sekline uyuyor ama "
                                    "ARAC DEGIL",
}

SEKIL_KURALI_MUAF_SAYISI = 2
SEKIL_KURALI_MUAF_IMZA = "03460dcdcdea42c0"


def sekil_kurali_muaf_imzasi():
    """Muafiyet kumesinin ANAHTAR kimligi (S2 dersi: SAYI degil KIMLIK)."""
    return hashlib.sha256(
        json.dumps(sorted("%s|%s" % (a, b) for a, b in SEKIL_KURALI_MUAF),
                   ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# KURATORLU KUSAK ESLEMESI — gramerin GOREMEDIGI kusak/taban baglari (4 Agu, mimar hukmu)
#
# OLCULEN PARCALANMA: /marka/volkswagen/transporter/ 44 urunle yayindayken /t3/ /t4/ /t5/
# /t6/ sayfalari 97 urunle ONDAN AYRI duruyordu. Ayni arac: "T4 parcasi" arayan musteri
# Transporter sayfasindaki 44 urunu GORMUYOR, tersi de dogru.
#
# 🔴 GRAMER BUNU YAKALAYAMAZ: `T4` jetonu `Transporter` tabanini ICERMIYOR — kelime
# sinirindan turetilebilecek bir bag YOK. Bu yuzden KURATORLU esleme sart; kural
# ROZET_DISI_CIFT / KUSAK_DISI_JETON ile AYNI disiplinde: kapali, gerekceli, kimligi donmus.
#
# 🔴 MARKA-OZEL: Mercedes `T1` (Bremer transporter, ayri arac) VW T1'e KATLANMAZ — tablo
# (marka, jeton) ciftiyle anahtarlandigi icin yapisal olarak imkansiz; kapi ayrica bunu
# oldurucu mutantla olcer.
#
# KANONIK AD CIPLAK JETONDUR (mimar karari, olculdu): `?ara=T4` 74 vs `?ara=Transporter T4`
# 15 (~5:1) — T5 97/15, T6 68/8, T3 64/5. Musteri ciplak kusak jetonunu ariyor; sayfa adi
# ve alt bolum basligi `T4`'tur, `Transporter T4` DEGIL.
KUSAK_ESLEME = {
    ("Volkswagen", "T1"): "Transporter",
    ("Volkswagen", "T2"): "Transporter",
    ("Volkswagen", "T3"): "Transporter",
    ("Volkswagen", "T4"): "Transporter",
    ("Volkswagen", "T5"): "Transporter",
    ("Volkswagen", "T6"): "Transporter",
    # T6.1 = T6 makyajı (ayni arac kusagi); disarida birakilsaydi kendi basina duran
    # ucuncu bir sayfa olurdu. MIMAR ONAYI BEKLIYOR (raporda isaretli).
    ("Volkswagen", "T6.1"): "Transporter",
    # Ayni aracin BILESIK yazimlari — yoksa tek urunluk oksuz kovalar olarak kalirlar.
    ("Volkswagen", "Transporter T5"): "Transporter",
    ("Volkswagen", "T4 Transporter"): "Transporter",
    # 16 Agu, mimar hukumu (K117-B Toyota model kanonu): ayni arac birden cok kovaya
    # bolunmus — taban olculen en buyuk/canli kovadir. Kucuk/kod/spyder jetonlari gramer
    # katlamaz, kuratorlu esleme sart.
    ("Toyota", "SW20"): "MR2",                # MR2 ikinci kusak sasi kodu (W20 = SW20)
    ("Toyota", "MR2 SW20"): "MR2",            # bilesik yazim — yoksa oksuz kova
    ("Toyota", "MR2 Spyder"): "MR2",          # ABD pazar adi (roofless roadster)
    ("Toyota", "Prado"): "Land Cruiser",      # Land Cruiser Prado — ayni arac, kisa adi
    ("Toyota", "Land Cruiser Prado"): "Land Cruiser",  # tam yazim
    ("Toyota", "Land Cruiser 200"): "Land Cruiser",    # J200 kusak sasi kodu
    ("Toyota", "FJ40"): "Land Cruiser",       # klasik Land Cruiser ailesi
    ("Toyota", "Land Cruiser FJ40"): "Land Cruiser",   # tam yazim
    ("Toyota", "T25"): "Avensis",             # Avensis 2. kusak (T250) sasi kodu
    ("Toyota", "T27"): "Avensis",             # Avensis 3. kusak (T270) sasi kodu
}

KUSAK_ESLEME_SAYISI = 19
KUSAK_ESLEME_IMZA = "674916073b452620"  # arama.kusak_esleme_imzasi() ile hesaplandi


def kusak_esleme_imzasi():
    return hashlib.sha256(
        json.dumps(sorted("%s|%s|%s" % (a, b, t) for (a, b), t in KUSAK_ESLEME.items()),
                   ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def model_olmayan_imzasi():
    """Tablonun ANAHTAR kimligi — sessiz buyume/daralma kapida KIRMIZI yakar (S2 dersi:
    SAYI degil KIMLIK; sayiyi sabit tutup uyeyi degistirmek gorunmez kalirdi)."""
    return hashlib.sha256(
        json.dumps(sorted(MODEL_OLMAYAN_JETON), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]

# URETICI EKSENI — GERCEK markalardir ama UYUM ekseni DEGILDIR: bunlar takilan sarf/parcanin
# ureticisidir (buji, tutya, dolgu/yapistirici, tekne boyasi, temizleyici, zimpara, direksiyon
# kablosu). "Bu urun NGK'ya takilir" cumlesi anlamsizdir; "bu urun bir NGK bujisidir" anlamlidir.
# AYRI kume tutulmasinin sebebi: (1) uyum[].marka'da GECERSIZ olmalari fail-closed sart —
# aksi halde "NGK" diye SAHTE bir uyum sayfasi acilir; (2) tek kumede eritilselerdi bu yargi
# kaybolur ve bir sonraki tur onlari yeniden "marka" diye geri koyardi. Bu turda TUKETICISI
# YOKTUR; ileride "uretici/parca markasi" filtresi gerekirse kaynak burasidir.
URETICI_MARKA = frozenset({
    "Bosch",         # 🔴 MIMAR EKI (oneri disi): el aleti = ev sahibi, oto elektrik
                     # parcasi = uretici. Bu CIFT SINIF tam olarak bu kumenin tanimidir;
                     # supheli jeton uyum ekseninde GECERSIZ olur (fail-closed yon).
    "3M",            # zimpara / bant / yapistirici
    "Champion",      # buji (ayrica jeneratör — belirsiz, fail-closed yonu URETICI)
    "Denso",         # buji / elektrik parcasi
    "International", # yat boyasi (AkzoNobel) — ayrica jenerik Ingilizce kelime, capraz-anlamli
    "Martyr",        # tutya / anot
    "NGK",           # buji
    "Nordlinger",    # dolgu / yapistirici
    "Seafirst",      # tekne boyasi
    "Sika",          # dolgu / yapistirici
    "Star Brite",    # tekne bakim kimyasali
    "Teak Wonder",   # tik bakim kimyasali
    "Tecnoseal",     # tutya / anot
    "Teleflex",      # direksiyon/kumanda kablosu (mimarin ornegi)
})

# ELENEN — "marka" onerildi ama MARKA DEGIL (ya da kanonik yazim DEGIL). Kume SAKLANIR ki
# elenmis bir jeton bir sonraki turda sessizce geri sizmasin ve budama aritmetigi
# CALISTIRILABILIR kalsin (kapi: uc kume ayrik + birlesim = 169).
#   jenerik kelime / urun tipi : Generic, Turbo, Motorhome, Android, Victoria
#   motor / donanim adi        : Coyote (Ford 5.0 motoru)
#   standart / kod             : DIN1, CTC
#   tanimsiz tekil jeton       : Canora, DiveTalk, RocketStart, STORM Racing, Toplife
#   jeneriklesmis tur adi      : Mobylette (moped tur adi; Motobecane model hatti)
#   IKIZ YAZIM (K4 kaybeden)   : MINI (Mini=24 > MINI=1) · Mercedes-Benz (Mercedes=1011 >
#                                Mercedes-Benz=21) · Ssangyong (SsangYong=6 > Ssangyong=3)
UYUM_MARKA_ELENEN = frozenset({
    "Android", "CTC", "Canora", "Coyote", "DIN1", "DiveTalk", "Generic", "MINI",
    "Mercedes-Benz", "Mobylette", "Motorhome", "RocketStart", "STORM Racing",
    "Ssangyong", "Toplife", "Turbo", "Victoria",
})

# Codex'in URETTIGI oneri kumesinin buyuklugu. Uc kumenin birlesimi buna ESIT olmali —
# esit degilse ya bir jeton sessizce dusmus ya da sozluge oneride OLMAYAN bir deger
# elle eklenmistir. Ikisi de denetimsiz genisleme, kapi KIRMIZI yakar.
UYUM_MARKA_ONERI_SAYISI = 169

# 🔴 SAYI KORUMASI YETMEZ, KIMLIK KORUMASI SART (bagimsiz curutucu olctu, 2 Agu).
# Onceki hal yalnizca BIRLESIMIN BUYUKLUGUNU sabitliyordu. Bu, bir jetonu ELENEN'den
# cikarip IZINLI'ye TASIMAYI gormuyordu: birlesim sabit kaliyor (200), S1 ayrikligi
# bozulmuyor (jeton TASINDI, kopyalanmadi), S4 ikiz uretmiyor. Curutucu tam olarak bunu
# yapti — `Turbo` ELENEN'den IZINLI'ye tasindi ve kapi YESIL kaldi. Yani "elenen jeton
# sessizce geri sizamaz" iddiasi FIILEN YANLISTI: `Generic`/`Motorhome`/`Coyote` gibi
# bilerek elenmis bir jeton denetimsiz sekilde geri donup SAHTE MARKA SAYFASI acabilirdi
# — K2'nin onlemek icin var oldugu seyin ta kendisi.
#
# Cozum: YARGILANMIS BOLUMLEMENIN kimligi donduruluyor. Imza uc bolumun HER BIRI icin
# AYRI hesaplanir; boylece degisim oldugunda HANGI kovanin oynadigi da gorunur (tek
# birlesik hash "bir sey degisti" der, hangisi oldugunu SOYLEMEZ).
#
# ⚠️ BU IMZA DEGISMEMELI. Yargilanmis bolumleme KAPANMIS bir karardir; sozlugu genisletme
# yolu MIMAR EKI kumeleridir ve onlar imzaya GIRMEZ (yani mesru genisleme imzayi
# BOZMAZ). Imza kirmizi yaniyorsa ya kapanmis bir karar yeniden acilmistir — ki bu
# BILEREK ve GORUNUR yapilmali, imza da elle guncellenmeli — ya da jeton kaymasi vardir.
UYUM_MARKA_YARGI_IMZA = ("8d0bdf607d0079f9", "e6c2f91212ba9f04", "cec09f9fee6f6211")
# Bolum buyuklukleri: imza kirmizi yandiginda okunabilir bir ilk teshis verir.
UYUM_MARKA_YARGI_SAYILARI = (139, 13, 17)


def uyum_yargi_bolumleri():
    """YARGILANMIS bolumleme: (izinli−eki, uretici−eki, elenen). Mimar eki DISARIDA."""
    return (sorted(UYUM_MARKA_IZINLI - UYUM_MARKA_MIMAR_EKI),
            sorted(URETICI_MARKA - URETICI_MARKA_MIMAR_EKI),
            sorted(UYUM_MARKA_ELENEN))


def uyum_yargi_imzasi():
    """Yargilanmis bolumlemenin KIMLIK imzasi — bolum basina bir ozet."""
    return tuple(
        hashlib.sha256(json.dumps(b, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        for b in uyum_yargi_bolumleri())

# `uyum` ogesinde TANINAN alanlar. Kume KAPALI: taninmayan anahtar REDDEDILIR (sessizce
# YUTULMAZ). Yutulsaydi yazim hatasi (`yıl`, `oem_no`) veri kaybi olarak sessizce gecerdi.
UYUM_ALANLARI = ("marka", "model", "motor", "yil", "oem")

# Serbest metin alanlari (model/motor/oem) icin BEYAZ LISTE — kara liste DEGIL:
# gorulmemis bir enjeksiyon bicimi sessizce gecmesin. Olculdu (1.704 jeton): gecen
# ozel karakterler '-' 82, '.' 8, '&' 3, '/' 2, '+' 1; harflerin TAMAMI Latin; en uzun
# jeton 18 karakter, en cok kelime 3.
#
# AYIRAC ile EK ayrimi KASITLI: ayiraca KONUM kurali uygulanir (asagida), eke uygulanmaz.
#   AYIRAC " -./"  yol/slug anlami tasir -> yalniz IKI alfanumerigin ARASINDA durabilir.
#   EK     "+"     yol anlami YOK, mesru model sonekidir (olculdu: `206+` Peugeot modeli).
# '&' BILEREK HICBIRINDE DEGIL (HTML varlik isareti). OLCULEN BEDEL: bu kural katalogun
# 1.704 jetonundan 3'unu reddeder — 'Briggs & Stratton' (zaten KAPALI marka kumesinde,
# serbest metin kuralindan gecmesi GEREKMEZ), 'K&N' (filtre ureticisi, uyum ekseni degil),
# 'Town & Country' (Chrysler modeli — backfill'de ELE kalir, sayiyla raporlanir).
UYUM_SERBEST_AYIRAC = frozenset(" -./")
UYUM_SERBEST_EK = frozenset("+")
UYUM_SERBEST_AZAMI_UZUNLUK = 40
UYUM_SERBEST_AZAMI_KELIME = 5

# `yil` araligi. 0 = ACIK UC ve YALNIZ son elemanda gecerlidir ([2015, 0] = "2015'ten beri").
# [0, 2015] REDDEDILIR: acik BAS diye bir sey yok, 0 orada veri hatasidir.
UYUM_YIL_ACIK_UC = 0
UYUM_YIL_EN_ERKEN = 1900
UYUM_YIL_EN_GEC = 2100

_MODEL_AYIRAC_RE = re.compile(r"[.\-\s]")


def _latin_harf(c):
    """Harf VE Latin yazisinda mi? Kiril/Yunan homoglifi ('А', 'Ѕ') buradan GECMEZ —
    gorunuste ayni, normalize sonucu FARKLI bir jeton uretir (sessiz ikiz uretici)."""
    return c.isalpha() and unicodedata.name(c, "").startswith("LATIN")


def uyum_marka_kanonik(deger):
    """Ham jetonu KANONIK markaya indirir ya da "" (kume disi / bicimsiz).

    🔴 SESSIZ KIRPMA YOK — uyelik testi HAM deger uzerinde yapilir. ' Ford' KABUL EDILMEZ;
    kabul edilseydi (strip() uyelik testinin ICINE alinsaydi) kataloga ' Ford', D1'e 'Ford'
    giderdi: site ile Ege ayni urunu FARKLI yazimla gorurdu ve hicbir hash/senkron ekseni
    bunu yakalamazdi. Bu tam olarak `altkategori`de OLCULEN kusurdur (1 Agu, ' Elektrik').

    KABUL EDILEN deger AYNEN doner -> "kataloga yazilan metin" ile "D1'e giden metin"
    ayrisamaz (ucuncu bir hal yoktur).
    """
    if not isinstance(deger, str):
        return ""
    if deger not in UYUM_MARKA_IZINLI:
        return ""
    return deger


def model_metin(deger):
    """`model`/`motor`/`oem` alanlarinin KANONIK metin bicimi — TEK KAYNAK.

    altkategori_metin ile AYNI SOZLESME: sebebi() kanonik OLMAYAN her degeri REDDEDER,
    kanonik() ise kabul edilen degeri BU fonksiyondan gecirir. Yani katalog metni ile D1
    metni ayni fonksiyondan turer ve AYRISAMAZ.
    """
    if not isinstance(deger, str):
        return ""
    return deger.strip()


def model_normalize(deger):
    """Model IKIZ tespiti icin katlama anahtari — kataloga/D1'e ASLA YAZILMAZ.

    K4: ayni araci anlatan farkli ham yazimlar TEK anahtara duser
    (`F-150` == `F150`, `XSR 700` == `XSR700`, `ID.Buzz` == `ID Buzz`, `Zoé` == `Zoe`),
    ama FARKLI araclar ayrik kalir (`Focus` != `Focuss`).

    Model kumesi ACIK oldugu icin onceden sayilamaz; ikiz ancak KATLAMA ile gorulur.
    Katlama norm()'dan (sitenin TEK kaynagi) turer -> ikinci bir Turkce kucultme kopyasi
    dogmaz. Uzerine NFKD aksan soyme + [.-bosluk] silme gelir.
    """
    m = model_metin(deger)
    if not m:
        return ""
    m = norm(m)
    m = "".join(c for c in unicodedata.normalize("NFKD", m)
                if not unicodedata.combining(c))
    return _MODEL_AYIRAC_RE.sub("", m)


# Kapali kumenin NORMALIZE anahtarlari. Modul yuklenirken BIR KEZ turetilir — kumenin
# KENDISINDEN, ikinci bir liste tutulmaz (ikiz tanim yasagi).
_UYUM_MARKA_ANAHTARLARI = frozenset(model_normalize(m) for m in UYUM_MARKA_IZINLI)


def marka_varyanti_sebebi(ad, deger):
    """model/motor degeri KAPALI kumedeki bir markanin YAZIM VARYANTI mi? Sebep ya da None.

    🔴 NEDEN SART (bu tur olculdu): kumeye `Kia` ve `Smart` girdi; katalogda `KIA` (1) ve
    `SMART` (1) yazimlari da var. Kural olmasaydi backfill `marka: "Kia"` ile `model: "KIA"`
    yazabilir, AYNI gercek iki ayri alanda iki ayri sayfa uretirdi — S4'un sozluk ICINDE
    yasakladigi ikizin marka/model SINIRINDAN sizan hali. Sinir da kapatiliyor.

    OLCUM (16.874 kayit, 1.704 jeton): kumeye duson AMA kanonik olmayan yazim TAM 7 tane —
    `BaoFeng`(1), `Citroën`(4), `Ikea`(2), `KIA`(1), `MINI`(1), `SMART`(1), `Ssangyong`(3).
    Yedisi de gercekten MARKA yazimidir, yani kuralin YANLIS-POZITIFI OLCULEN VERIDE 0.
    """
    n = model_normalize(deger)
    if not n or n not in _UYUM_MARKA_ANAHTARLARI:
        return None
    return ("%s KAPALI marka kumesindeki bir markanin YAZIM VARYANTI (%r -> %r) — marka "
            "`marka` alanina yazilir, model/motor alanina DEGIL" % (ad, deger, n))


# ─────────────────────────────────────────────────────────────────────────────
# BILESIK MARKA ADI — `Mercedes-Benz` -> `Mercedes` (Okan hukmu, tools/paket-bilesik-marka.md)
#
# 🔴 NEDEN AYRI FONKSIYON, `marka_varyanti_sebebi()`'ye EKLENMEDI: yukaridaki 7'li kume
# olculmus bir YAZIM VARYANTI listesidir (`KIA`/`Kia`, `MINI`/`Mini` — ayni adin farkli
# YAZIMI). `Mercedes-Benz` yazim varyanti DEGILDIR: kanonik markayi ICEREN, kendi basina
# dogru yazilmis bir BILESIK ADDIR. Iki kural sinifini tek fonksiyonda eritmek 7'li capayi
# anlamsiz kilardi (MaCiT'in kova ayrimi o capaya dayaniyor). Ayri sinif -> ayri tablo,
# ayri fonksiyon, ayri iddia. Bu blok `marka_varyanti_*`nin BAYRAGINI OKUMAZ ve tersi de
# dogrudur -> iki BAGIMSIZ kod yolu, iki AYRI iddia ([[beyan-edilmis-survivor]]).
#
# 🔴 GENEL NORMALIZASYON YASAK. "Tire/bosluk kirp, iceriyorsa esle" turu bir kural
# YAZILMAZ: mesru jetonlari yer (OLCULEN katalog verisi — `F-150`, `Rolls-Royce`,
# `D2-55`, `206+`, `K5`). Tablo KAPALI ve ELLE yazilmistir; tabloda OLMAYAN bir bilesik ad
# sessizce eslenmez, OLDUGU GIBI kalir (fail-closed = uydurma esleme YOK).
#
# ⚠️ TEK TOHUM. Okan yalnizca bu esitligi verdi. Tablonun buyumesi GORUNUR bir karardir;
# kabul testi tablonun ICERIGINI dondurur, yani sessiz genisleme kapi KIRMIZI yakar.
BILESIK_MARKA_KANONIK = {
    "Mercedes-Benz": "Mercedes",
}


def bilesik_marka_kanonik(deger):
    """Bilesik marka adini KAPALI tablodan kanonik markaya indirir.

    Tabloda YOKSA deger AYNEN doner (uyum_marka_kanonik gibi "" DONDURMEZ: burasi bir
    UYELIK testi degil, bir ESLEME'dir; eslemesi olmayan deger gecerli olabilir).
    Metin olmayan deger de aynen doner -> cagiran taraf tip kontrolunu kaybetmez.
    """
    if not isinstance(deger, str):
        return deger
    return BILESIK_MARKA_KANONIK.get(deger, deger)


def bilesik_marka_sebebi(deger):
    """Deger KANONIKLESTIRILMESI GEREKEN bir bilesik marka adi mi? Sebep ya da None.

    UYELIK testidir (tablonun ANAHTARI mi), esleme sonucuna BAKMAZ: tablonun degeri
    yanlis yazilsa bile "bu deger tabloya tabidir" yargisi ayakta kalir -> iki eksen
    (esleme dogru mu / hangi kayitlar tabloya tabi) ayri ayri olculebilir.
    """
    if not isinstance(deger, str) or deger not in BILESIK_MARKA_KANONIK:
        return None
    return ("%r BILESIK marka adidir ve kanonik markaya indirilir (%r) — kapali tablo, "
            "genel normalizasyon YOK" % (deger, BILESIK_MARKA_KANONIK[deger]))


# ── TABLONUN BUYUME KURALI (2 Agu, ikinci tur — OLCULDU, uydurulmadi) ────────────────
# Birinci tur tabloyu TEK TOHUMLA acti ve "buyume GORUNUR bir karardir" dedi ama buyumenin
# OLCUTUNU yazmadi. Olcut yoksa bir sonraki tur "bu da bilesik ad" diye herhangi bir jetonu
# koyar; kapi yalnizca "tablo degisti" der, DOGRU MU diye SORMAZ.
#
# 🔴 IKI EKSENLI OLCUT (ikisi de gercek katalogda olculur, ikisi de kapida CALISIR):
#   (1) SITE UYUMU — index.html'in KENDI kuratorlu katlamasi (markaKatla / TANINMIS_MARKALAR;
#       Python portu tools/marka_katla.py) jetonu ZATEN ayni kanonik markaya katliyor mu?
#       Katliyorsa tablo yalnizca D1/Ege tarafini siteyle AYNI hale getirir (ayrisma 0).
#       KATLAMIYORSA tablo, katalogu ve D1'i sitenin hukmuyle CELISKIYE sokar — musteri
#       sitede bir sey, Ege'de baskasini gorur ve hicbir alarm calmaz.
#   (2) FAYDA — esleme, kaydin `marka` dizisine kanonik markayi GERCEKTEN kazandiriyor mu?
#       Kazandirmiyorsa (marka zaten ayni kayitta duruyorsa) esleme hicbir sey kazandirmadan
#       yalnizca MODEL belirtecini yok eder.
#
# OLCUM (16.874 kayit, 2 Agu): "kanonik markayi BILESEN olarak iceren" 25 tekil jeton var.
# Biri tabloda (`Mercedes-Benz`: site katliyor ✓, fayda 21 kayit ✓). Kalan 24'un HICBIRI
# olcutu gecmiyor ve asagida SINIFIYLA kayda geciyor — bir sonraki tur ayni jetonlari
# yeniden "kesfetmesin" ve karar yeniden tartisilmasin (UYUM_MARKA_ELENEN deseni).
#
#   AYRISMA (4 jeton / 5 kayit): site KATLAMIYOR -> yazilirsa katalog+D1 site ile ayrisir.
#     `Pajero Mini` (2)  Mitsubishi MODELI; `Mini` marka sayfasina yazilsaydi bir Mitsubishi
#                        parcasi SAHTE bir MINI marka sayfasi acardi (K2'nin onlemek icin
#                        var oldugu sey). Olculdu: markaKatla -> 'Pajero Mini'.
#     `iPad Mini 4` (1)  Apple urunu; ayni sahte-MINI hatasi, daha da acik.
#     `Range Rover` (1)  Land Rover MODELI; `Rover` AYRI bir marque'dir — esleme yanlis
#                        ureticiye baglardi. Kayit zaten `Land Rover` tasiyor.
#     `Formula Renault` (1) Tek koltuklu YARIS SERISI; marque `Renault` ile ayni sey DEGIL.
#                        Site de katlamiyor -> yazim katalogu siteden ayirirdi.
#
#   FAYDASIZ (20 jeton / 40 kayit): site KATLIYOR (olcut 1 ✓) ama kanonik marka ZATEN ayni
#     kaydin `marka` dizisinde -> D1 kazanci OLCULDU ve 0. Bunlar bilesik MARKA ADI degil,
#     "<marka> <model>" bicimindeki MODEL jetonlaridir (`Peugeot 205`, `Volvo 240`,
#     `Renault 5 E-Tech`, `Citroën C1`, `Toyota 86`, `Porsche 944` ...). Eslenselerdi tek
#     etkileri model belirtecini `marka` dizisinden dusurmek olurdu: kazanc 0, kayip gercek.
BILESIK_RED_SINIFLARI = ("AYRISMA", "FAYDASIZ")

BILESIK_MARKA_REDDEDILEN = {
    "Formula Renault": ("Renault", "AYRISMA"),
    "Pajero Mini": ("Mini", "AYRISMA"),
    "Range Rover": ("Rover", "AYRISMA"),
    "iPad Mini 4": ("Mini", "AYRISMA"),
    "Citroen C1": ("Citroen", "FAYDASIZ"),
    "Citroën BX": ("Citroen", "FAYDASIZ"),
    "Citroën C1": ("Citroen", "FAYDASIZ"),
    "Citroën C5": ("Citroen", "FAYDASIZ"),
    "Peugeot 203": ("Peugeot", "FAYDASIZ"),
    "Peugeot 205": ("Peugeot", "FAYDASIZ"),
    "Peugeot 206": ("Peugeot", "FAYDASIZ"),
    "Peugeot 207": ("Peugeot", "FAYDASIZ"),
    "Peugeot 208": ("Peugeot", "FAYDASIZ"),
    "Peugeot 306": ("Peugeot", "FAYDASIZ"),
    "Peugeot 307": ("Peugeot", "FAYDASIZ"),
    "Peugeot 308": ("Peugeot", "FAYDASIZ"),
    "Peugeot 5008": ("Peugeot", "FAYDASIZ"),
    "Porsche 911": ("Porsche", "FAYDASIZ"),
    "Porsche 944": ("Porsche", "FAYDASIZ"),
    "Renault 17": ("Renault", "FAYDASIZ"),
    "Renault 5": ("Renault", "FAYDASIZ"),
    "Renault 5 E-Tech": ("Renault", "FAYDASIZ"),
    "Toyota 86": ("Toyota", "FAYDASIZ"),
    "Volvo 240": ("Volvo", "FAYDASIZ"),
}

# Reddedilen KUMENIN kimligi (S2 dersi: sayiyi sabit tutup uyeyi degistirmek gorunmez
# kalirdi). Yalniz ANAHTARLAR imzalanir — hedef/sinif alanlari AYRI eksenlerde olculur,
# tek imzaya baglansalardi o eksenleri kiran mutant bu imzaya sirtini dayar ve ayirt
# edici olmaktan cikardi ([[beyan-edilmis-survivor]]).
BILESIK_RED_IMZA = "916a9f4285eae12e"
BILESIK_RED_SAYISI = 24

_BILESIK_BILESEN_RE = re.compile(r"[ \-/_.]+")


def bilesik_red_imzasi():
    """Reddedilen aday kumesinin ANAHTAR kimligi — tek satir teshis verir."""
    return hashlib.sha256(
        json.dumps(sorted(BILESIK_MARKA_REDDEDILEN), ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:16]


def bilesik_ad_bileseni(deger):
    """DENETIM EKSENI — jeton, KAPALI marka kumesindeki bir markayi BILESEN olarak mi tasiyor?

    Dondurur: bulunan ham bilesenlerin sirali demeti (bos demet = bilesik aday DEGIL).

    🔴 BU BIR ESLEME KURALI DEGILDIR, BIR TARAMA EKSENIDIR. `bilesik_marka_kanonik()` bu
    fonksiyonu CAGIRMAZ ve cagirmayacak: cagirsaydi paketin acikca YASAKLADIGI genel
    normalizasyonun ta kendisi olurdu ve olculen sahte esleseler dogardi (`Pajero Mini` ->
    `Mini`, `Range Rover` -> `Rover`, `iPad Mini 4` -> `Mini`). Islevi yalnizca kapinin
    gercek katalogda ADAY jetonlari GORUNUR kilmasi ve tablo/red kayitlarinin gercekten bu
    sinifa ait oldugunu dogrulamasidir.

    Anahtarlar `_UYUM_MARKA_ANAHTARLARI`DAN turer (ikinci liste tutulmaz) — kume buyurse
    tarama da buyur, ikiz tanim dogmaz. Jetonun KENDISI kanonik bir markaysa bilesen
    aranmaz (o zaten bilesik ad degil, markanin kendisidir).
    """
    if not isinstance(deger, str) or not deger.strip():
        return ()
    # Jetonun KENDISI kanonik markaysa aday DEGILDIR (`Volvo Penta`, `Land Rover`,
    # `Alfa Romeo`) — bunlar kumenin KENDI uyeleridir. Bu dal olmasaydi `Volvo Penta`
    # "Volvo iceren bilesik ad" diye taranirdi ve tam da `[[uyum-marka-mimar-eki]]`
    # notunun AYRI ev sahibi ilan ettigi jetonu geri katlamaya davet ederdi.
    if model_normalize(deger) in _UYUM_MARKA_ANAHTARLARI:
        return ()
    parcalar = [p for p in _BILESIK_BILESEN_RE.split(deger) if p]
    if len(parcalar) < 2:
        return ()
    bulunan = []
    for i in range(len(parcalar)):
        for j in range(i + 1, len(parcalar) + 1):
            # TUM jetonu kapsayan dilim ATLANIR: o zaman deger bilesik ad degil, markanin
            # KENDISIDIR (`Alfa Romeo`, `Volvo Penta`) — bileseni olmaz.
            if i == 0 and j == len(parcalar):
                continue
            ham = " ".join(parcalar[i:j])
            if model_normalize(ham) in _UYUM_MARKA_ANAHTARLARI and ham not in bulunan:
                bulunan.append(ham)
    return tuple(sorted(bulunan))


def bilesik_marka_fayda_kazanci(katalog, jeton, hedef):
    """Esleme yazilsaydi KAC kaydin `marka` dizisi `hedef` markayi YENI kazanirdi?

    FAYDA ekseninin olculebilir birimi. 0 ise esleme hicbir sey kazandirmaz — yalnizca
    jetonun kendisini (cogunlukla bir MODEL belirtecini) dizi disina iter.
    """
    n = 0
    for u in katalog:
        if not isinstance(u, dict):
            continue
        marka = u.get("marka")
        if isinstance(marka, list) and jeton in marka and hedef not in marka:
            n += 1
    return n


def arama_jetonu_korunuyor(u, jeton):
    """`jeton` sorgusu bu kaydi HALA buluyor mu? (sitenin KENDI ucluşu ile olculur)

    haystack() + tokenlar() + esles() = index.html'in arama yolunun birebir karsiligi.
    Ikinci bir arama kopyasi YAZILMAZ: kopya yazilsaydi "kapida yesil, sitede kayip"
    ayrismasi dogar ve tam da onlemek istedigimiz sessiz kayip olculemez hale gelirdi.
    """
    return esles(haystack(u), tokenlar(jeton))


def bilesik_marka_kanoniklestir(u):
    """Kaydin `marka` dizisinin BILESIK-AD kanoniklestirilmis hali — ARAMA JETONU KAYIPSIZ.

    🔴 BU PAKETIN VARLIK SEBEBI. `marka` yalnizca bir etiket degil, ARAMA METNIDIR
    (haystack() ve ege_govde() onu okur). `Mercedes-Benz` -> `Mercedes` yazildiginda
    "Mercedes-Benz" sorgusu tek bir jetona ayrisir (`mercedes-benz`) ve ALT-DIZE olarak
    aranir; ham yazim kaydin arama metninden tamamen dustuyse urun o sorguyla BULUNAMAZ.
    Hicbir alarm calmaz — sessiz kayip sinifi.

    OLCULDU (16.874 kayit): `marka` alaninda `Mercedes-Benz` tasiyan 21 kayit var; duz
    kanoniklestirme bunlarin 5'inde sorgu jetonunu DUSURUYOR (kalan 16'sinda ham yazim
    baslik/aciklamada oldugu icin ayakta kaliyor).

    KURAL: kanoniklestirme once yapilir, SONRA sonuc kaydin arama metninde OLCULUR. Jeton
    dustuyse ham yazim dizinin SONUNA ARAMA TAKMASI olarak korunur.
      - Kayip YOKSA takma EKLENMEZ -> arama yuzeyi GENISLEMEZ (gereksiz genisleme de bir
        davranis degisikligidir; `Mercedes` tasiyan 1.011 kayit bundan ETKILENMEZ).
      - `marka` cipleri/sayfalari zaten katliyor (index.html markaKatla: `Mercedes-Benz`
        -> `Mercedes`, ayni urunde baz+varyant cifti TEK sayilir) -> takma SAHTE marka
        sayfasi ACMAZ, yalnizca arama metnini korur.
    Bilesik ad TASIMAYAN kayitta cikti girdiyle BIREBIR aynidir (regresyon 0).
    """
    marka = list(u.get("marka") or [])
    yeni, dusen = [], []
    for m in marka:
        k = bilesik_marka_kanonik(m)
        if k != m:
            dusen.append(m)
        if k not in yeni:
            yeni.append(k)
    if not dusen:
        return yeni
    aday = dict(u, marka=yeni)
    for ham in dusen:
        if not arama_jetonu_korunuyor(aday, ham) and ham not in yeni:
            yeni.append(ham)
    return yeni


def _serbest_sebebi(ad, deger):
    """model/motor/oem gibi ACIK metin alani gecerli mi? Sebep metni ya da None.

    BOS/eksik GECERLIDIR (alanlar opsiyonel). Kural BEYAZ LISTEDIR: yalniz Latin harf,
    rakam ve UYUM_SERBEST_AYIRAC gecer -> HTML/SQL benzeri her deger ('<b>', "' OR 1=1--",
    '${x}', ';DROP') ve Latin disi homoglif REDDEDILIR.
    """
    if deger is None:
        return None
    if not isinstance(deger, str):
        return "%s metin olmali, %s degil" % (ad, type(deger).__name__)
    d = model_metin(deger)
    # 🔴 FAIL-CLOSED, SESSIZ DUZELTME DEGIL (altkategori_sebebi ile ayni cizgi).
    if d != deger:
        return ("%s KANONIK DEGIL: %r — bas/son bosluk tasiyor; kanonik bicim %r"
                % (ad, deger, d))
    if not d:
        return None
    if len(d) > UYUM_SERBEST_AZAMI_UZUNLUK:
        return "%s cok uzun (%d > %d karakter)" % (ad, len(d), UYUM_SERBEST_AZAMI_UZUNLUK)
    if len(d.split()) > UYUM_SERBEST_AZAMI_KELIME:
        return "%s cok fazla kelime (%d > %d)" % (ad, len(d.split()),
                                                  UYUM_SERBEST_AZAMI_KELIME)
    govde = False
    for c in d:
        if c.isdigit() or _latin_harf(c):
            govde = True
            continue
        if c in UYUM_SERBEST_AYIRAC or c in UYUM_SERBEST_EK:
            continue
        return ("%s izinsiz karakter (%r) — beyaz liste: Latin harf, rakam, %r"
                % (ad, c, "".join(sorted(UYUM_SERBEST_AYIRAC | UYUM_SERBEST_EK))))
    if not govde:
        return "%s alfanumerik govde tasimiyor (%r)" % (ad, d)
    # 🔴 AYIRAC KONUMU DA KURALDIR — karakter beyaz listesi TEK BASINA YETMEZ (OLCULDU:
    # '../../etc/passwd' yalniz '.', '/' ve harf tasidigi icin karakter suzgecinden GECTI
    # ve V10 ekseni bu turda KIRMIZI yandi). Ayirac ancak IKI alfanumerigin ARASINDA
    # durabilir: bas/son ayirac ve ARDISIK ayirac reddedilir -> '..', '//', './' ve
    # bas/son nokta bicimleri kapanir. Mesru veriyi kesmez (olculdu): 'F-150', '5.0',
    # 'ID.Buzz', '85.12.345/A', 'Quad Lock', '206+' gecer.
    if d[0] in UYUM_SERBEST_AYIRAC or d[-1] in UYUM_SERBEST_AYIRAC:
        return "%s ayirac ile basliyor/bitiyor (%r)" % (ad, d)
    for onceki, simdiki in zip(d, d[1:]):
        if onceki in UYUM_SERBEST_AYIRAC and simdiki in UYUM_SERBEST_AYIRAC:
            return ("%s ARDISIK ayirac (%r) — yol gecisi/bicim bozuklugu sinyali"
                    % (ad, onceki + simdiki))
    return None


def uyum_yil_sebebi(deger):
    """`yil` gecerli mi? Sebep metni ya da None.

    GECERLI: [] (bilinmiyor — UYDURMA YOK) · [bas, son] · [bas, 0] (acik uc).
    GECERSIZ: tek elemanli, ikiden fazla, metin ("2015"), bool (True), ters aralik,
    acik BAS ([0, 2015]), aralik disi yil.
    """
    if deger is None:
        return None
    if not isinstance(deger, list):
        return "yil dizi olmali, %s degil" % type(deger).__name__
    if not deger:
        return None
    if len(deger) != 2:
        return "yil [bas, son] olmali (%d elemanli) — acik uc icin [bas, 0]" % len(deger)
    bas, son = deger
    for ad, v in (("bas", bas), ("son", son)):
        # 🔴 bool BILEREK ELENIR: Python'da isinstance(True, int) -> True. Kontrol
        # olmasaydi [True, False] "[1, 0]" diye GECERDI (stokta_kanonik'teki tuzagin aynisi).
        if isinstance(v, bool) or not isinstance(v, int):
            return "yil %s tam sayi olmali, %r degil" % (ad, v)
    if not (UYUM_YIL_EN_ERKEN <= bas <= UYUM_YIL_EN_GEC):
        return ("yil bas %d araligin disinda (%d–%d) — 0 yalniz SON elemanda acik uctur"
                % (bas, UYUM_YIL_EN_ERKEN, UYUM_YIL_EN_GEC))
    if son == UYUM_YIL_ACIK_UC:
        return None
    if not (UYUM_YIL_EN_ERKEN <= son <= UYUM_YIL_EN_GEC):
        return "yil son %d araligin disinda (%d–%d)" % (son, UYUM_YIL_EN_ERKEN,
                                                        UYUM_YIL_EN_GEC)
    if son < bas:
        return "yil araligi TERS: [%d, %d]" % (bas, son)
    return None


def uyum_ogesi_sebebi(oge):
    """Tek bir `uyum` ogesi gecerli mi? Sebep metni ya da None."""
    if not isinstance(oge, dict):
        return "uyum ogesi sozluk olmali, %s degil" % type(oge).__name__
    fazla = sorted(k for k in oge if k not in UYUM_ALANLARI)
    if fazla:
        return ("taninmayan alan %s — izinli: %s (yazim hatasi sessizce YUTULMAZ)"
                % (fazla, ", ".join(UYUM_ALANLARI)))
    ham = oge.get("marka")
    if uyum_marka_kanonik(ham) == "":
        return ("marka ZORUNLU ve KAPALI kumeden olmali — %r kumede YOK "
                "(kume %d deger; bosluklu/kucuk-buyuk harf farkli yazim da REDDEDILIR)"
                % (ham, len(UYUM_MARKA_IZINLI)))
    for ad in ("model", "motor", "oem"):
        sebep = _serbest_sebebi(ad, oge.get(ad))
        if sebep:
            return sebep
    for ad in ("model", "motor"):
        sebep = marka_varyanti_sebebi(ad, oge.get(ad))
        if sebep:
            return sebep
    return uyum_yil_sebebi(oge.get("yil"))


def marka_uyumdan_turet(u):
    """K5 — `marka` alaninin `uyum`dan TURETILMIS hali (tekil, ilk gorulme sirasinda).

        marka = tekillestir( uyum[].marka + uyum[].model )

    IKIZ TANIM YASAGI: `marka` ile `uyum` ayni gercegi iki yerde tutar ve SESSIZCE
    ayrisir. Kural: `uyum` varsa `marka` ondan TURETILIR, elle yazilmaz.

    🔴 MODEL DE GIRER — KURAL 2 AGU'DA DEGISTI, SEBEBI OLCULDU. Once yalniz
    `uyum[].marka` turetiliyordu. Ama bugunku `marka` alani marka VE model karisimidir
    (olculdu: 6.918 kayit tam 2 elemanli, `["Ford","Focus"]` bicimi) ve `marka`
    haystack()/ege_govde() araciligiyla ARAMA metnine giriyor. Yalniz markadan
    turetseydik backfill iner inmez `Focus` haystack'ten DUSER ve "focus" aramasi
    yalnizca baslik/aciklamadan eslesirdi: SESSIZ bir arama kaybi, hicbir alarm calmaz.
    Model de girince `marka` bugunku anlamini BIREBIR korur -> arama yuzeyi degismez,
    parite riski sifir ve haystack genisletmesi backfill'i BLOKLAMAZ (paket §5'teki
    sira bagimliligi kalkti).

    SIRA KASITLI: her oge icin ONCE marka SONRA model -> bugunku `["marka", "model"]`
    dizilimi korunur. `motor`/`oem` GIRMEZ: bunlar bugun `marka` alaninda yok, eklemek
    arama metnini GENISLETIR ve pariteyi bu sefer TERS yonde kaydirirdi.
    """
    turetilen = []
    for oge in (u.get("uyum") or []):
        if not isinstance(oge, dict):
            continue
        jetonlar = (uyum_marka_kanonik(oge.get("marka")),
                    model_metin(oge.get("model")))
        for deger in jetonlar:
            if deger and deger not in turetilen:
                turetilen.append(deger)
    return turetilen


def uyum_sebebi(u):
    """Kaydin `uyum` alani gecerli mi? Sebep metni ya da None (gecerli).

    ALAN YOK / None / [] -> GECERLI (opsiyonel; bugun 16.874 kaydin TAMAMI boyle).
    """
    deger = u.get("uyum")
    if deger is None:
        return None
    if not isinstance(deger, list):
        return "uyum dizi olmali, %s degil" % type(deger).__name__
    if not deger:
        return None
    for i, oge in enumerate(deger):
        sebep = uyum_ogesi_sebebi(oge)
        if sebep:
            return "uyum[%d]: %s" % (i, sebep)
    imzalar = [json.dumps([o.get(k) for k in UYUM_ALANLARI], ensure_ascii=False,
                          sort_keys=True) for o in deger]
    if len(set(imzalar)) != len(imzalar):
        return "uyum MUKERRER oge tasiyor (%d oge, %d tekil)" % (len(imzalar),
                                                                 len(set(imzalar)))
    # 🔴 K5 IKIZ KAPISI — `uyum` DOLU iken `marka` ondan TURETILMIS olmak ZORUNDA.
    # Siralama da olculur: `marka` bir DIZIDIR, uc onu SIRAYLA gosterir; sira kaymasi
    # da bir ayrismadir. `uyum` bos olan ESKI kayitlarda bu dal HIC calismaz (regresyon 0).
    turetilen = marka_uyumdan_turet(u)
    mevcut = u.get("marka")
    if mevcut != turetilen:
        return ("IKIZ TANIM: `marka` %r, `uyum`dan turetilen %r — `uyum` doluyken "
                "`marka` elle yazilmaz, TURETILIR" % (mevcut, turetilen))
    return None


def uyum_kanonik(u):
    """D1/edge'e gidecek kanonik `uyum` degeri. FAIL-CLOSED: gecersiz her deger [].

    Neden fail-closed (altkategori_kanonik deseni): .git/hooks/pre-push d1-sync'i push'tan
    ONCE kosar, CI kapisi push'tan SONRA — yani bozuk bir deger kapi kirmizi yanmadan once
    D1'e, oradan Ege'ye ve musteriye ulasabilirdi. [] yazmak urunu KAYBETTIRMEZ (urun kendi
    kategorisi altinda bulunur), yalnizca uyum yuzeyini dusurur; tools/uyum-kapisi.py ayni
    degeri KIRMIZI yakar, yani sessiz KALMAZ.

    KABUL EDILEN kayitta girdi AYNEN (derin kopya) doner -> katalog metni ile D1 metni
    BIREBIR AYNI. Derin kopya sart: cagiran donen listeyi degistirirse katalog bozulmamali.
    """
    if uyum_sebebi(u) is not None:
        return []
    return copy.deepcopy(u.get("uyum") or [])


# ─────────────────────────────────────────────────────────────────────────────
# TAVSIYE FILAMENT (`tavsiyeFilament`) — urunun KENDI malzeme onerisi (override).
#
# NE ISE YARAR: filament_ortak.tavsiyeler()/on_secim() bu alani gorurse KATEGORI
# haritasini EZER ve urunun ON-SECILI malzemesi buradan gelir. On-secilen malzeme
# sepet CARPANINI ve ilan edilen TUTARI surer (secenekler.js onSecimMalzeme) — yani
# bu alan bir FIYAT girdisidir, kozmetik bir etiket degil.
#
# NEDEN BURADA (tur/stokta/altkategori/uyum ile AYNI gerekce): alan hem urun_hash'e
# hem D1 kolonuna girer. Iki yerde AYRI turetilseydi hash "degismedi" derken kolon
# degisir (ya da tersi) ve D1 SESSIZCE eski oneriyi servis ederdi. Tek fonksiyon = tek
# kaynak.
#
# 🔴 SIRA YUK TASIR — LISTE SIRALANMAZ: on_secim() KALAN ILK adi secer. Kanoniklestirme
# adina siralamak, "PETG, ASA" yazan bir urunu sessizce ASA'ya cevirirdi (baska carpan,
# baska tutar). Bu yuzden deger AYNEN (derin kopya) tasinir; yalnizca TIP dogrulanir.
#
# 🔴 FAIL-CLOSED YONU BU ALANDA "BOSALT" DEGIL "DUR" — tur/altkategori/uyum'un AKSINE,
# ve bu BILEREK boyle (mimar karari): oradaki alanlarda bozuk deger yalnizca bir KESIF
# yuzeyini dusururdu; burada bozuk deger bir TIP KUSURUDUR ve iki yonu de zararlidir:
#   * sessizce [] yapmak  -> urunun kendi onerisi DUSER, kategori haritasi devreye girer,
#                            baska malzeme on-secilir = ilan edilen tutar sessizce kayar;
#   * sessizce ["PETG"]'e -> yani dizeyi tek elemanli diziye cevirmek, VERI KUSURUNU
#     NORMALIZE etmek         GIZLER ve kusur katalogda kalicilasir.
# Dogru davranis: ISTISNA. Cagiran (d1-sync) bunu KAC KAYITTA HANGI TIP sayisiyla
# raporlayip DURUR; boylece sira kendini dayatir — veri sahibi kaydi duzeltmeden dolum
# tamamlanmaz. Katalog verisinin tek yazari bu ev DEGILDIR; bu yuzden burasi kusuru
# ONARMAZ, GORUNUR KILAR.
class TavsiyeFilamentTipHatasi(ValueError):
    """`tavsiyeFilament` BEKLENEN tipte degil (sessiz normalizasyon YERINE atilir)."""


TAVSIYE_FILAMENT_ALAN = "tavsiyeFilament"
# Tip dokumunde kullanilan ETIKETLER (sayim anahtarlari). "YOK" = alan hic yazilmamis
# (katalogun buyuk cogunlugu; override YOK demektir, kusur DEGIL).
TAVSIYE_FILAMENT_YOK = "YOK"
TAVSIYE_FILAMENT_DIZI = "dizi"

# KATALOG KAYIT SEMASI — alan adlari ve JSON tipleri icin TEK KAYNAK.
#
# Kapi kapsamini bu sozlugun anahtarlarindan TURETIR; alanlari ikinci kez saymaz.
# Alanlar opsiyoneldir: katalogun tarihsel ve urun-sinifi farklari nedeniyle `marka`,
# `lisans`, `parametrik` gibi alanlar her kayitta bulunmaz. Ancak bir alan VARSA tipi
# burada yazan tip olmak zorundadir. Semada olmayan alan sessizce kabul edilmez.
KATALOG_ALAN_TIPLERI = {
    "aciklama": str,
    "altkategori": str,
    "baslik": str,
    "boy_secenekleri": list,
    "fiyat": str,
    "gorseller": list,
    "id": str,
    "kategori": str,
    "konfigur": dict,
    "lisans": dict,
    "marka": list,
    "parametrik": bool,
    "stokta": bool,
    TAVSIYE_FILAMENT_ALAN: list,
    "tur": str,
    "uyum": list,
}


def boy_secenekleri_sebebi(deger):
    """Boy varyantlarini fiyat yoluna girebilecek tek kanonik bicimde dogrula."""
    if type(deger) is not list:
        return "boy_secenekleri dizi olmali, %s degil" % type(deger).__name__
    gorulen = set()
    for i, secenek in enumerate(deger):
        if type(secenek) is not dict:
            return "boy_secenekleri[%d] nesne olmali" % i
        fazla = sorted(set(secenek) - {"etiket", "fark_tl"})
        if fazla:
            return "boy_secenekleri[%d] bilinmeyen alan: %s" % (i, ", ".join(fazla))
        etiket = secenek.get("etiket")
        if type(etiket) is not str or not etiket.strip() or etiket != etiket.strip():
            return "boy_secenekleri[%d].etiket bosluksuz, bos-olmayan metin olmali" % i
        if len(etiket) > 60:
            return "boy_secenekleri[%d].etiket 60 karakteri gecemez" % i
        if etiket in gorulen:
            return "boy_secenekleri etiketleri benzersiz olmali: %r" % etiket
        gorulen.add(etiket)
        fark = secenek.get("fark_tl", 0)
        if type(fark) is not int or fark < 0:
            return "boy_secenekleri[%d].fark_tl negatif-olmayan tam sayi olmali" % i
    return None


def boy_secenekleri_kanonik(u):
    """D1/hash/istemci icin ayni boy secenekleri; kusurda sessizce bosaltma YOK."""
    deger = u.get("boy_secenekleri") or []
    sebep = boy_secenekleri_sebebi(deger)
    if sebep:
        raise ValueError(sebep)
    return [{"etiket": s["etiket"], "fark_tl": s.get("fark_tl", 0)} for s in deger]


def katalog_alan_tip_sebebi(alan, deger):
    """Bir katalog alaninin kanonik JSON tipine uyumsuzluk sebebi ya da None.

    `type(...) is ...` bilerek kullanilir: Python'da bool, int'in alt sinifidir; JSON
    semasinda boolean ile number ayni tip degildir. Bos string ve bos dizi, kendi
    tipleri dogru oldugu icin gecerlidir.
    """
    beklenen = KATALOG_ALAN_TIPLERI.get(alan)
    if beklenen is None:
        return "TIP TANIMI YOK: %s" % alan
    if type(deger) is beklenen:
        if alan == "boy_secenekleri":
            return boy_secenekleri_sebebi(deger)
        return None
    return ("%s alani %s olmali; gorulen tip=%s, gorulen deger=%r"
            % (alan, beklenen.__name__, type(deger).__name__, deger))


def katalog_tip_ihlalleri(kayitlar):
    """Semadan tureyen tum alan-tip ihlalleri; bilinmeyen alan fail-loud'dur."""
    ihlaller = []
    for u in kayitlar:
        if not isinstance(u, dict):
            ihlaller.append((None, "kayit", u,
                             "kayit bir JSON OBJESI degil (%s)" % type(u).__name__))
            continue
        uid = u.get("id")
        for alan, deger in u.items():
            sebep = katalog_alan_tip_sebebi(alan, deger)
            if sebep is None and alan == TAVSIYE_FILAMENT_ALAN:
                for i, oge in enumerate(deger):
                    if not isinstance(oge, str):
                        sebep = "%s[%d] metin olmali, %s degil (deger: %r)" % (
                            alan, i, type(oge).__name__, oge)
                        break
                    if not oge.strip():
                        sebep = "%s[%d] BOS metin — malzeme adi tasimayan oge yazilmaz" % (
                            alan, i)
                        break
            if sebep is not None:
                ihlaller.append((uid, alan, deger, sebep))
    return ihlaller


def tavsiye_filament_tip_etiketi(u):
    """Kaydin `tavsiyeFilament` TIP etiketi — dokum/sayim icin.

    "YOK"  alan hic yazilmamis · "dizi" BEKLENEN tip · aksi halde Python tip adi
    ("str", "dict", "NoneType"...). Bu fonksiyon YARGI VERMEZ, yalnizca SINIFLAR;
    yargi tavsiye_filament_tip_sebebi()'nde.
    """
    if TAVSIYE_FILAMENT_ALAN not in u:
        return TAVSIYE_FILAMENT_YOK
    deger = u[TAVSIYE_FILAMENT_ALAN]
    return TAVSIYE_FILAMENT_DIZI if isinstance(deger, list) else type(deger).__name__


def tavsiye_filament_tip_sebebi(u):
    """Kaydin `tavsiyeFilament` alani BEKLENEN tipte mi? Sebep metni ya da None.

    GECERLI: alan YOK · [] (override yok) · bos olmayan METIN ogelerinden olusan dizi.
    GECERSIZ: dize ("PETG") · None (acikca yazilmis bos deger) · sozluk · sayi ·
              dizi icinde metin OLMAYAN ya da bos/bosluk oge.
    🔴 `None` BILEREK GECERSIZ: "alan yok" ile "alan var ama bos yazilmis" AYNI SEY
    DEGILDIR; ikincisini sessizce birinciye indirmek tam da yasakladigimiz normalizasyon
    olurdu. Olculdu (11 Agu 2026, 25.605 kayit): None yazan kayit 0 -> regresyon riski yok.
    """
    if TAVSIYE_FILAMENT_ALAN not in u:
        return None
    deger = u[TAVSIYE_FILAMENT_ALAN]
    sebep = katalog_alan_tip_sebebi(TAVSIYE_FILAMENT_ALAN, deger)
    if sebep is not None:
        return ("%s — tek elemanli diziye SESSIZCE CEVRILMEZ: kusur katalogda "
                "kalicilasirdi" % sebep)
    for i, oge in enumerate(deger):
        if not isinstance(oge, str):
            return ("%s[%d] metin olmali, %s degil (deger: %r)"
                    % (TAVSIYE_FILAMENT_ALAN, i, type(oge).__name__, oge))
        if not oge.strip():
            return "%s[%d] BOS metin — malzeme adi tasimayan oge yazilmaz" % (
                TAVSIYE_FILAMENT_ALAN, i)
    return None


def tavsiye_filament_kanonik(u):
    """D1'e/hash'e giden `tavsiyeFilament` degeri: dizinin DERIN KOPYASI.

    🔴 FAIL-CLOSED = ISTISNA (yukaridaki blok): tip beklenenden farkliysa
    TavsiyeFilamentTipHatasi atilir. NE bosaltilir NE normalize edilir — cagiran
    (d1-sync.tavsiye_filament_tip_kapisi) sayiyla raporlayip DURUR.

    Derin kopya sart: cagiran donen listeyi degistirirse katalog bozulmamali.
    SIRA KORUNUR (siralanmaz) — ilk oge ON-SECILEN malzemedir, yani bir FIYAT girdisi.
    """
    sebep = tavsiye_filament_tip_sebebi(u)
    if sebep is not None:
        raise TavsiyeFilamentTipHatasi(
            "%s (id=%r)" % (sebep, u.get("id")))
    return copy.deepcopy(u.get(TAVSIYE_FILAMENT_ALAN) or [])


# D1'e yazilan alanlar — biri degisirse satir yeniden yazilir, degismezse yazilmaz.
# (D1 gunluk 100.000 yazma limiti: tam rebuild yerine sadece degiseni yazmak sart.)
def urun_hash(u):
    ozet = json.dumps([
        u.get("id") or "",
        u.get("baslik") or "",
        u.get("kategori") or "",
        u.get("marka") or [],
        u.get("fiyat") or "",
        (u.get("gorseller") or [None])[0],
        bool(u.get("parametrik")),
        haystack(u),
        # FAZ 2: Ege kolonlari. aciklama/ege hash'te YOKTU — "ege" alani degisince
        # satir yeniden yazilmazdi (sessiz eskime). Ikisi de eklendi.
        u.get("aciklama") or "",
        u.get("ege") or "",
        ege_baslik(u),
        ege_govde(u),
        # TICARI HAL: `tur` + `stokta`. HASH'E GIRMESI SART — bu ikisi PUBLIC urunler.json'da
        # yasar (baski'nin aksine CI de gorur) ve D1'e ICERIK UPSERT'i ile yazilir. Hash
        # kapsamasaydi bir urun "tukendi" (stokta true -> false) olarak isaretlendiginde
        # hash AYNI kalir, diff_plan satiri "degismemis" sayar ve D1'e HIC YAZMAZDI:
        # Ege tukenmis urunu STOKTA diye satmaya devam ederdi (sessiz yanlis vaat).
        # KANONIK degerler yazilir (ham degil): D1 kolonuna giden deger ile hash'in gordugu
        # deger AYNI fonksiyondan gelir -> "hash degisti ama kolon degismedi" ayrismasi
        # INSAATAN imkansiz.
        tur_kanonik(u),
        stokta_kanonik(u),
        # ALT KATEGORI: HASH'E GIRMESI SART — alan D1'de bir KESIF yuzeyini besler
        # (kategori icinde daraltma). Hash kapsamasaydi bir urunun altkategorisi
        # degistiginde hash AYNI kalir, diff_plan satiri "degismemis" sayar ve D1'e HIC
        # YAZMAZDI: alt-filtre sessizce bayat kalir, musteri urune ULASAMAZ ve hicbir
        # alarm calmaz. KANONIK deger yazilir (ham degil) -> hash'in gordugu deger ile
        # kolona giden deger AYNI fonksiyondan gelir, ayrisma INSAATAN imkansiz.
        altkategori_kanonik(u),
        # UYUM (arac uyumlulugu): HASH'E GIRMESI SART — alan D1'de Ege'nin cevaplayabildigi
        # bir SORUYU besler ("bu parca Passat B8 2.0 TDI'ye uyar mi"). Hash kapsamasaydi bir
        # urunun uyum listesi degistiginde hash AYNI kalir, diff_plan satiri "degismemis"
        # sayar ve D1'e HIC YAZMAZDI: Ege bayat uyum servis eder, musteriye YANLIS uyum
        # vaadi gider ve hicbir alarm calmaz. tur/stokta/altkategori ile AYNI sinif — alan
        # PUBLIC urunler.json'da yasar, CI de yerel de AYNI degeri gorur ([[d1-baski-hash-
        # thrash]]'in gizli-kayit sorunu burada YOK). KANONIK deger yazilir (ham degil) ->
        # hash'in gordugu deger ile D1 kolonuna giden deger (d1-sync.uyum_metin) AYNI
        # fonksiyondan besleniyor, ayrisma INSAATAN imkansiz.
        uyum_kanonik(u),
        # TAVSIYE FILAMENT: HASH'E GIRMESI SART (MIMAR KARARI, 11 Agu 2026). Alan bir
        # ICERIK alanidir — urunun KENDI malzeme onerisi — ve TURETILMIS DEGILDIR: degeri
        # baska hicbir kurataryadan degil, kaydin kendisinden gelir. Hash disinda
        # birakilsaydi "alan degisti ama urun_hash AYNI" hali dogar, diff_plan satiri
        # "degismemis" sayar ve kolon HICBIR ZAMAN senkronlanmazdi (bu deponun olculmus
        # sessiz-ayrisma sinifi). Bedeli tek seferlik tam-katalog yeniden yazimidir ve o
        # bedel KABUL EDILMISTIR; hedefli-UPDATE (taban_fiyat/konfigur) deseni bu alanda
        # BILEREK KURULMADI. tur/stokta/altkategori/uyum ile AYNI sinif: alan PUBLIC
        # urunler.json'da yasar, CI de yerel de AYNI degeri gorur. KANONIK deger yazilir ->
        # hash'in gordugu deger ile D1 kolonuna giden deger (d1-sync.tavsiye_filament_metin)
        # AYNI fonksiyondan besleniyor, ayrisma INSAATAN imkansiz.
        # 🔴 BU CAGRI TIP KUSURUNDA ISTISNA ATAR (fail-closed): bozuk kayitli bir katalogda
        # hash URETILMEZ, yani bozuk veri D1'e sessizce akamaz.
        tavsiye_filament_kanonik(u),
        # BOY SECENEKLERI: fiyat girdisi D1'e icerik upsert'iyle gider. Hash kapsaminda
        # olmazsa fark/etiket degisimi D1'e yazilmaz ve edge/odeme eski tutari kullanir.
        boy_secenekleri_kanonik(u),
    ], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ozet.encode("utf-8")).hexdigest()[:16]
