#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTAK POSTA KUTUSU ARSIVLEYICI — tavani asan kutuyu EN ESKI bloklari TASIYARAK indirir.

NEDEN VAR (olculdu, 31 Tem): mimarlarin ortak posta kutusu
`~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md` tavani <=300 satir.
Bes mimar + advisor gun boyu yazdigi icin elle her budandiginda birkac saat sonra tekrar
siriyor: TEK GUNDE 269 -> 281 -> 306 -> 365 -> 568 satir oldu ve UC KEZ elle budandi.
Elle budama iki sessiz hata sinifi uretir:
  (1) KAYIPLI TASIMA — kardes mimarin yazismasi arsive girmeden ucar, kimse fark etmez
      (kutu kucuk gorunur, "temizlendi" sanilir);
  (2) YARIS — dosyaya AYNI ANDA baska oturumlar yazar; biri okuyup budarken digerinin
      ekledigi blok, budayanin bayat kopyasi geri yazilinca YOK OLUR.
Bu arac ikisini de kapatir: LOSSLESS dogrulama (dogrulama gecmezse HICBIR SEY yazilmaz)
+ flock (kilit alinamazsa fail-closed cikis, "sessiz basari" YOK).

KUTU SEKLI (gercek dosya, taklit degil):
    ---                      <- YAML frontmatter (DOKUNULMAZ)
    name: mimar-posta-kutusu
    ...
    ---
                             <- (varsa) onsoz satirlari (DOKUNULMAZ)
    ## 2026-07-31 — KraL ...  <- EN YENI blok (ust)
    ...govde...
    ## 2026-07-30 — MaCiT ... <- daha ESKI blok
    ...
Blok siralamasi YENI -> ESKI (yeni yazan BASA ekler). Dolayisiyla arsive giden bloklar
dosyanin SONUNDAKI bloklardir ve arsivin SONUNA eklenir (arsiv de yeni->eski kalir).

KURALLAR (hepsi kabul testiyle kilitli — tools/kutu-arsivle-test.py):
  * LOSSLESS: tasinan HER satir arsivde BIREBIR bulunur. Dogrulama BASARISIZSA hicbir
    sey yazilmaz (once dogrula, sonra yaz; kismi yazim YOK).
  * Frontmatter'a ve en ustteki N (varsayilan 3) bloga DOKUNULMAZ.
  * Blok ORTASINDAN bolunmez: kesim daima bir `## ` blok BASIDIR.
  * flock: kilit ALINDIKTAN SONRA okunur (bayat kopyayla yazmamak icin), atomik yazilir
    (gecici dosya + os.replace). Kilit alinamiyorsa exit 3, hicbir sey yazilmaz.
  * `--kuru`: hicbir sey yazmaz, ne yapacagini SAYIYLA basar (dogrulamayi yine kosar).
  * BUTUNLUK (K310, 27 Agu): HER kosumda OKSUZ GOVDE (basliksiz dolu bolut) SAYILIR ve
    ADIYLA BASILIR; sifir degilse `lossless_dogrulama` GECEMEZ ve hicbir sey yazilmaz —
    tasinacak is olmasa bile. Ayrac (`---`) tasimayan bir kutuda bu eksen KORDUR ve
    ciktida `EKSEN_KOR=` diye SOYLENIR (0 basilip "temiz" denmez).

YAZMA SIRASI — NEDEN ONCE ARSIV: iki ayri dosya tek islemde atomik yazilamaz. Once ARSIV
(ekleme), sonra KUTU (kisaltma) yazilir. Ikisinin arasinda cokme olursa sonuc MUKERRER
icerik olur (arsivde var, kutuda da duruyor) — geri alinabilir. Ters sirada sonuc KAYIP
olurdu. Fail-toward-duplication, asla fail-toward-loss.

SENTETIK ARIZA ENJEKSIYONU (yalniz nobetci icin): PRUVO_KUTU_ARSIVLE_ARIZA ortam
degiskeni set edilmediginde HICBIR ETKISI YOKTUR. Set edildiginde aday metinler
dogrulamadan ONCE kasten bozulur; kabul testi boylece "lossless dogrulamasi GERCEKTEN
kirmizi yakiyor mu" sorusunu OLCEBILIR (dogrulamayi silen mutant KIRMIZI yanar).
Degerler: arsiv-satir-dus | kutu-satir-dus | arsiv-onek-boz | arsiv-sira-boz

Kullanim:
    python3 tools/kutu-arsivle.py --kuru
    python3 tools/kutu-arsivle.py
    python3 tools/kutu-arsivle.py --tavan 300 --koru 3
    python3 tools/kutu-arsivle.py --kutu /yol/kutu.md --arsiv /yol/arsiv.md
"""
import argparse
import fcntl
import os
import re
import sys
import tempfile

VARSAYILAN_TAVAN = 300
VARSAYILAN_KORU = 3
# K310: arsiv KUYRUGU (rapor ekseni) varsayilan penceresi. Bugunun tasimalari bu
# pencerenin icindedir; tarihsel arsivin tamami BILEREK kapsam disidir (bkz. AYRAC_RE notu).
VARSAYILAN_ARSIV_KUYRUK = 400
# O1 (16 Agu 2026): rotasyon sonrasi kutu tavanin bu kadarina kadar inmeli.
# 0.8 = tavanin %80'i; gelecek birkac blok icin bas payi.
SU_SEVIYESI_ORANI = 0.8

KUTU_VARSAYILAN = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")
ARSIV_VARSAYILAN = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu-arsiv.md")

RC_OK = 0
RC_KIRMIZI = 1      # bozuk girdi / lossless dogrulamasi gecmedi -> HICBIR SEY yazilmadi
RC_KILIT = 3        # kilit baskasinda -> HICBIR SEY yazilmadi (fail-closed)

# dogrula()'nin BASTIGI iddia eksenleri. `lossless_dogrulama=GECTI (iddia=N)` satirindaki
# N BURADAN turer; elle yazilan sayi kaynagindan ayrisir ve beyan sessizce yalanlanir.
IDDIA_EKSENLERI = ("D1", "D2", "D3", "D4", "D5", "D5b", "D6", "D6b", "D6c", "D7",
                   "D8", "D9", "D10", "D11", "D12", "D13")

BLOK_RE = re.compile(r"^## ")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
# Kutu blok AYRACI: cit DISINDA, tek basina duran yatay cizgi. Kutunun gercek sekli
# (27 Agu olcumu): 11 blok / 11 ayrac — her blogun ARDINDAN bir ayrac gelir.
AYRAC_RE = re.compile(r"^-{3,}[ \t]*$")

# 🔴 K310 (27 Agu 2026) — "lossless_dogrulama=GECTI" BEYANI BLOK BUTUNLUGUNU OLCMUYORDU.
# Olculen olay (26 Agu): `MaCiT-Seat-MW-Ekle` blogunun BASLIGI dustu, GOVDESI kutuda
# oksuz kaldi; arac yine de `lossless_dogrulama=GECTI (iddia=10)` bastı. D1-D10 iddialarinin
# HEPSI bu turun TASIMA ARITMETIGINI olcer (bayt/satir/blok korunumu) — dosyanin YAPISAL
# BUTUNLUGUNU (her govdenin bir basligi var mi) HICBIRI olcmez. Yani ad "lossless" diyor,
# olculen sey "bu turda bir sey kaybettim mi"; "elimdeki zaten kirik mi" sorusu hic
# sorulmuyordu -> kirik kutu sessizce arsive kurekleniyordu.
# CARE: OKSUZ GOVDE = ayraclar arasinda kalan, ICINDE DOLU SATIR OLAN ama `## ` basligi
# TASIMAYAN bolut. Sayilir, ADIYLA BASILIR ve sifir degilse lossless GECEMEZ.
# 🔴 KAPSAM DURUSTLUGU (bilerek dar): kapi yalniz KUTU ve bu turda ARSIVE EKLENEN metin
# uzerinde caliсir. Tarihsel arsiv (50k satir) KARMA yazim gelenegi tasiyor (2333 baslik /
# 479 ayrac: govde ici `---` yatay cizgileri + govde ici `## ` alt basliklari) — orada
# ayrac ekseni YANLIS-POZITIF uretir ve bir hijyen aracini kalici kirmiziya cevirirdi
# ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]). Arsiv KUYRUGU olculur ve BASILIR
# ama cikis kodunu BELIRLEMEZ; hangi eksen kapi hangisi rapor, ciktida yazar.


def bolutler(satirlar, bas=0):
    """Ayracla bolunmus bolutler: [(bas_idx, son_idx_haric, baslik_sayisi, dolu_mu)].

    Cit (```/~~~) icindeki `---` ve `## ` satirlari SAYILMAZ — blok_baslari() ile ayni
    kural, ayni sebep (kod blogu icindeki metin yapi degildir).
    """
    cikti = []
    ic = False
    ilk = bas
    baslik = 0
    dolu = False
    i = bas
    while i < len(satirlar):
        s = satirlar[i]
        if FENCE_RE.match(s):
            ic = not ic
            dolu = True
        elif ic:
            if s.strip():
                dolu = True
        elif AYRAC_RE.match(s):
            cikti.append((ilk, i, baslik, dolu))
            ilk, baslik, dolu = i + 1, 0, False
        elif BLOK_RE.match(s):
            baslik += 1
            dolu = True
        elif s.strip():
            dolu = True
        i += 1
    cikti.append((ilk, len(satirlar), baslik, dolu))
    return cikti


IMZA_RE = re.compile(r"^— \S")


def imza_yigilmasi(metin, fm_atla=True):
    """AYRACTAN BAGIMSIZ ikinci sinyal: bir bolutte >=2 satir-basi imzasi (`— Ad`).

    Kutu geleneginde her blok kendi imzasiyla biter. Iki imza tek bolutte toplaniyorsa
    aralarindaki `## ` basligi dusmus olabilir. Tarihsel arsivde bu gelenek her blokta
    YOK (olculdu: 2333 baslik / 331 imza) -> bu eksen RAPORDUR, kapi DEGILDIR; kalibre
    edilmeden cikis koduna baglanirsa komsuyu kirmiziya yakar.
    """
    satirlar = metin.splitlines(keepends=True)
    bas = 0
    if fm_atla:
        fm_son, hata = frontmatter_sonu(satirlar)
        if not hata and fm_son:
            bas = fm_son
    kac = 0
    for b, s, _baslik, _dolu in bolutler(satirlar, bas):
        imza = 0
        j = b
        while j < s:
            if IMZA_RE.match(satirlar[j]):
                imza += 1
            j += 1
        if imza >= 2:
            kac += 1
    return kac


def ayrac_sayisi(metin, fm_atla=True):
    """Cit disinda duran ayrac (`---`) sayisi. 0 ise OKSUZ GOVDE ekseni KORDUR."""
    satirlar = metin.splitlines(keepends=True)
    bas = 0
    if fm_atla:
        fm_son, hata = frontmatter_sonu(satirlar)
        if not hata and fm_son:
            bas = fm_son
    return max(0, len(bolutler(satirlar, bas)) - 1)


def oksuz_govdeler(metin, fm_atla=True):
    """OKSUZ GOVDE listesi: [(1-indeksli bas satiri, ilk dolu satirin ozeti)].

    OKSUZ GOVDE = dolu ama BASLIKSIZ bolut. Bir blogun basligi dustugunde govdesi tam
    olarak bu hale gelir (K310 vakasi). Bos bolut (ardisik ayraclar, sondaki artik)
    oksuz DEGILDIR — sayi gurultuyle sismesin.
    """
    satirlar = metin.splitlines(keepends=True)
    bas = 0
    if fm_atla:
        fm_son, hata = frontmatter_sonu(satirlar)
        if not hata and fm_son:
            bas = fm_son
    bulgu = []
    for b, s, baslik, dolu in bolutler(satirlar, bas):
        if not dolu or baslik:
            continue
        ornek = ""
        j = b
        while j < s:
            if satirlar[j].strip():
                ornek = satirlar[j].strip()[:70]
                break
            j += 1
        bulgu.append((b + 1, ornek))
    return bulgu


# --------------------------------------------------------------------- okuma
def oku(yol):
    """(metin, hata). Yoksa/okunamiyorsa/UTF-8 degilse metin None."""
    if not os.path.exists(yol):
        return None, "dosya YOK: %s" % yol
    if os.path.isdir(yol):
        return None, "yol bir DIZIN, dosya degil: %s" % yol
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError as e:
        return None, "okunamadi: %s -> %s" % (yol, e)
    try:
        # newline="" -> evrensel satir sonu CEVIRISI YOK; bayt korunumu bozulmasin.
        return ham.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, "UTF-8 degil: %s -> %s" % (yol, e)


# --------------------------------------------------- frontmatter + blok ayrimi
def frontmatter_sonu(satirlar):
    """(fm_son_indeks_haric, hata). Frontmatter yoksa (0, None).

    FAIL-CLOSED: dosya `---` ile BASLIYOR ama kapanis `---` YOKSA bu YARIM/BOZUK bir
    dosyadir (ornegin baska bir yazici tam yazamadan coktu). O halde kesim yapmak
    frontmatter'i govdeye karistirabilir -> hata dondurulur, hicbir sey yazilmaz.
    """
    if not satirlar or satirlar[0].rstrip("\n") != "---":
        return 0, None
    i = 1
    while i < len(satirlar):
        if satirlar[i].rstrip("\n") == "---":
            return i + 1, None
        i += 1
    return None, ("YARIM FRONTMATTER: dosya `---` ile basliyor ama kapanis `---` yok "
                  "-> dosya bozuk/yarim yazilmis olabilir (fail-closed)")


def blok_baslari(satirlar, bas=0):
    """Ust duzey `## ` blok BASI satir indeksleri (kod cit'i icindekiler HARIC).

    CIT (```/~~~) NEDEN ONEMLI: mimar raporlari kod blogu icerir; cit icindeki
    `## yorum` satiri BLOK BASI DEGILDIR. Cit icinde blok basi sayilirsa kesim
    bir kod blogunun ORTASINDAN gecer = bolunmus blok = bozuk markdown.
    """
    baslar = []
    ic = False
    i = bas
    while i < len(satirlar):
        s = satirlar[i]
        if FENCE_RE.match(s):
            ic = not ic
        elif not ic and BLOK_RE.match(s):
            baslar.append(i)
        i += 1
    return baslar


def blok_sayisi(metin):
    """Bir metindeki ust duzey blok sayisi (frontmatter ELENMEDEN — sayim ekseni)."""
    return len(blok_baslari(metin.splitlines(keepends=True)))


# --------------------------------------------------------------------- planlama
class Plan(object):
    def __init__(self):
        self.hata = None
        self.kesim = None          # kutu satir indeksi (bu indeksten SONRASI tasinir)
        self.tasinacak_blok = 0
        self.blok_toplam = 0
        self.korunan = 0
        self.tasinabilir = 0
        self.once_satir = 0
        self.sonra_satir = 0
        self.tasinan_satir = 0
        self.tavan_asili_kaldi = False


def planla(kutu_metin, tavan, koru):
    """Kutuyu tavana indirmek icin SONDAN kac blok tasinacagini hesapla.

    O1 (16 Agu 2026): eski davranis kutu tam tavanda (300) duruyor ve bir
    sonraki blok onu asiyordu. SU SEVIYESI kurali: rotasyon sonrasi kutu
    tavanin altinda bir SU SEVIYESI noktasina inmeli (varsayilan: tavanin
    ~%80'i), boylece yeni gelen birkac blok tavanin ustune HEMEN cikmasin.
    Bu sabit (SU_SEVIYESI_ORANI) ile kontrol edilir; --su-seviye-orani
    bayragiyla degistirilebilir.
    """
    p = Plan()
    satirlar = kutu_metin.splitlines(keepends=True)
    p.once_satir = len(satirlar)
    p.sonra_satir = len(satirlar)

    fm_son, hata = frontmatter_sonu(satirlar)
    if hata:
        p.hata = hata
        return p

    baslar = blok_baslari(satirlar, fm_son)
    p.blok_toplam = len(baslar)
    p.korunan = min(koru, len(baslar))
    p.tasinabilir = max(0, len(baslar) - koru)

    # Su seviyesi: tavanin bu kadarina kadar dus (varsayilan 0.8). Esik
    # mutlak olarak > 0 ve <= 1 olmali.
    su_seviye = int(tavan * SU_SEVIYESI_ORANI)
    if su_seviye < 1:
        su_seviye = 1

    if p.once_satir <= tavan:
        p.kesim = None                      # tavan altinda -> is yok
        return p
    if p.tasinabilir <= 0:
        p.kesim = None
        p.tavan_asili_kaldi = True
        return p

    # Adaylar: baslar[koru:] — en ESKI blok listenin SONUNDA. SONDAN k blok tasi.
    # Hedef: kesim (kalan satir sayisi) <= su_seviye (tavanin %80'i). Bu,
    # gelecek bloklar icin bas gostermesi payi birakir.
    k = 1
    secilen = None
    while k <= p.tasinabilir:
        kesim = baslar[len(baslar) - k]
        secilen = (k, kesim)
        if kesim <= su_seviye:
            break
        k += 1
    k, kesim = secilen
    p.tasinacak_blok = k
    p.kesim = kesim
    p.sonra_satir = kesim
    p.tasinan_satir = len(satirlar) - kesim
    p.tavan_asili_kaldi = kesim > tavan
    return p


# ------------------------------------------------------------------ aday metinler
def arsiv_frontmatter(arsiv_yolu):
    """Arsiv dosyasi YOKKEN uretilecek frontmatter (memory dugum sekli)."""
    ad = os.path.basename(arsiv_yolu)
    if ad.endswith(".md"):
        ad = ad[:-3]
    return (
        "---\n"
        "name: %s\n"
        "description: Mimar posta kutusu ARSIVI — tavan asiminda EN ESKI bloklar "
        "tools/kutu-arsivle.py ile buraya BIREBIR tasinir; okumak icindir, elle "
        "duzenlenmez\n"
        "metadata:\n"
        "  node_type: memory\n"
        "  type: project\n"
        "---\n"
        "\n" % ad)


def aday_metinler(kutu_metin, arsiv_metin, plan, arsiv_yolu):
    """(yeni_kutu, tasinan, ek, yeni_arsiv) — DISKE YAZILMAZ, yalniz uretilir."""
    satirlar = kutu_metin.splitlines(keepends=True)
    yeni_kutu = "".join(satirlar[:plan.kesim])
    tasinan = "".join(satirlar[plan.kesim:])
    ek = tasinan if tasinan.endswith("\n") else tasinan + "\n"
    if arsiv_metin is None or arsiv_metin == "":
        yeni_arsiv = arsiv_frontmatter(arsiv_yolu) + ek
    else:
        if not arsiv_metin.endswith("\n"):
            ayrac = "\n\n"
        elif not arsiv_metin.endswith("\n\n"):
            ayrac = "\n"
        else:
            ayrac = ""
        yeni_arsiv = arsiv_metin + ayrac + ek
    return yeni_kutu, tasinan, ek, yeni_arsiv


def ariza_uygula(yeni_kutu, ek, yeni_arsiv):
    """SENTETIK ARIZA — yalniz PRUVO_KUTU_ARSIVLE_ARIZA set ise. Bkz. modul basligi.

    Bu fonksiyon nobetcinin OLCU ALETIDIR: enjekte edilen her ariza sinifini
    dogrula() YAKALAMAK ZORUNDADIR. Dogrulama silinirse bu arizalar SESSIZCE diske
    yazilir -> kabul testi KIRMIZI yanar (mutasyon a).
    """
    ariza = os.environ.get("PRUVO_KUTU_ARSIVLE_ARIZA", "").strip()
    if not ariza:
        return yeni_kutu, ek, yeni_arsiv, None
    if ariza == "arsiv-satir-dus":
        s = yeni_arsiv.splitlines(keepends=True)
        yeni_arsiv = "".join(s[:-1])           # arsivin SON satiri ucuruldu = KAYIP
    elif ariza == "kutu-satir-dus":
        s = yeni_kutu.splitlines(keepends=True)
        yeni_kutu = "".join(s[:-1])            # kutudan bir satir ucuruldu = KAYIP
    elif ariza == "arsiv-onek-boz":
        yeni_arsiv = "BOZULDU\n" + yeni_arsiv  # eski arsiv icerigi DEGISTI
    elif ariza == "arsiv-sira-boz":
        s = ek.splitlines(keepends=True)
        if len(s) >= 2:
            s[0], s[1] = s[1], s[0]            # tasinan satirlarin SIRASI bozuldu
        yeni_arsiv = yeni_arsiv[:len(yeni_arsiv) - len(ek)] + "".join(s)
        ek = "".join(s)
    else:
        return yeni_kutu, ek, yeni_arsiv, "BILINMEYEN ariza kodu: %s" % ariza
    return yeni_kutu, ek, yeni_arsiv, None


# --------------------------------------------------------------------- dogrulama
def dogrula(kutu_metin, arsiv_metin, yeni_kutu, tasinan, ek, yeni_arsiv, plan, tavan,
            koru):
    """LOSSLESS + butunluk iddialari. Bos liste = GECTI. Dolu liste = HICBIR SEY YAZMA.

    🔴 BU FONKSIYON ARACIN OMURGASIDIR. Silinirse arac "sessizce kaybeden" bir budayiciya
    doner ve kimse fark etmez — kabul testi (sentetik ariza vakalari) tam bunu olcer.
    """
    h = []
    kutu_satir = kutu_metin.splitlines()
    yeni_kutu_satir = yeni_kutu.splitlines()
    tasinan_satir = tasinan.splitlines()
    ek_satir = ek.splitlines()
    yeni_arsiv_satir = yeni_arsiv.splitlines()

    # 1. BAYT KORUNUMU — kutu ikiye bolundu, hicbir bayt eklenmedi/silinmedi.
    if yeni_kutu + tasinan != kutu_metin:
        h.append("D1 BAYT KORUNUMU: yeni_kutu + tasinan != orijinal kutu "
                 "(%d + %d bayt, orijinal %d)"
                 % (len(yeni_kutu), len(tasinan), len(kutu_metin)))

    # 2. SATIR KORUNUMU — satir ekseninde de tam.
    if yeni_kutu_satir + tasinan_satir != kutu_satir:
        h.append("D2 SATIR KORUNUMU: yeni_kutu(%d) + tasinan(%d) != kutu(%d) satir"
                 % (len(yeni_kutu_satir), len(tasinan_satir), len(kutu_satir)))

    # 3. ESKI ARSIV DOKUNULMADI — yalniz EKLEME yapildi.
    eski = arsiv_metin or ""
    if eski and not yeni_arsiv.startswith(eski):
        h.append("D3 ARSIV ONEKI BOZULDU: mevcut arsiv icerigi birebir korunmuyor "
                 "(eski %d bayt)" % len(eski))

    # 4. TASINAN METIN ARSIVIN SONUNDA BIREBIR.
    if not yeni_arsiv.endswith(ek):
        h.append("D4 EK SONDA DEGIL: tasinan blok metni yeni arsivin sonunda birebir yok")

    # 5. SATIR SATIR BIREBIR ESLESME (tasinan her satir arsivde AYNI SIRADA).
    if not ek_satir:
        h.append("D5 BOS EK: tasinacak satir yok ama tasima planlandi")
    elif yeni_arsiv_satir[-len(ek_satir):] != ek_satir:
        h.append("D5 SATIR ESLESMESI: arsivin son %d satiri tasinan satirlarla BIREBIR "
                 "esit degil" % len(ek_satir))

    # 5b. Kutudan CIKAN her satir arsivde var mi (ek yalniz sondaki \n ile farkli olabilir).
    if tasinan_satir != ek_satir:
        h.append("D5b EK SAPMASI: tasinan satirlar ile arsive eklenen satirlar ayristi "
                 "(%d != %d)" % (len(tasinan_satir), len(ek_satir)))

    # 6. BLOK KORUNUMU — hicbir blok yutulmadi/ikizlenmedi.
    b_kutu = blok_sayisi(kutu_metin)
    b_yeni = blok_sayisi(yeni_kutu)
    b_tas = blok_sayisi(tasinan)
    if b_yeni + b_tas != b_kutu:
        h.append("D6 BLOK KORUNUMU: yeni_kutu(%d) + tasinan(%d) != kutu(%d) blok"
                 % (b_yeni, b_tas, b_kutu))
    if b_tas != plan.tasinacak_blok:
        h.append("D6b PLAN SAPMASI: plan %d blok diyor, uretilen metinde %d blok var"
                 % (plan.tasinacak_blok, b_tas))
    b_arsiv_once = blok_sayisi(eski)
    b_arsiv_sonra = blok_sayisi(yeni_arsiv)
    if b_arsiv_sonra != b_arsiv_once + b_tas:
        h.append("D6c ARSIV BLOK KORUNUMU: %d + %d != %d"
                 % (b_arsiv_once, b_tas, b_arsiv_sonra))

    # 7. BLOK ORTASINDAN BOLUNMEDI — kesim bir blok BASI.
    if not tasinan.startswith("## "):
        h.append("D7 BLOK BOLUNDU: tasinan metin `## ` ile baslamiyor -> kesim bir blok "
                 "ORTASINDAN gecmis")

    # 8. FRONTMATTER + KORUNAN BLOKLAR YENI KUTUDA.
    kutu_satirlar_ke = kutu_metin.splitlines(keepends=True)
    fm_son, fm_hata = frontmatter_sonu(kutu_satirlar_ke)
    if fm_hata:
        h.append("D8 FRONTMATTER: %s" % fm_hata)
    elif fm_son:
        fm_metin = "".join(kutu_satirlar_ke[:fm_son])
        if not yeni_kutu.startswith(fm_metin):
            h.append("D8 FRONTMATTER KAYBI: yeni kutu frontmatter ile baslamiyor")
    baslar = blok_baslari(kutu_satirlar_ke, fm_son or 0)
    korunacak = baslar[:min(koru, len(baslar))]
    yeni_baslar = blok_baslari(yeni_kutu.splitlines(keepends=True),
                               fm_son or 0)
    if len(yeni_baslar) < len(korunacak):
        h.append("D9 KORUNAN BLOK KAYBI: en ustteki %d blok korunmali, yeni kutuda %d "
                 "blok var" % (len(korunacak), len(yeni_baslar)))
    else:
        i = 0
        while i < len(korunacak):
            if kutu_satirlar_ke[korunacak[i]] != yeni_kutu.splitlines(
                    keepends=True)[yeni_baslar[i]]:
                h.append("D9 KORUNAN BLOK SAPMASI: %d. korunan blogun basligi degisti" %
                         (i + 1))
                break
            i += 1

    # 10. TAVAN — tasinabilir blok TUKENMEDIYSE tavan saglanmis olmali.
    sonra = len(yeni_kutu_satir)
    if sonra > tavan and plan.tasinacak_blok < plan.tasinabilir:
        h.append("D10 TAVAN: %d satir kaldi (tavan %d) ama %d tasinabilir blogun yalniz "
                 "%d'i tasindi" % (sonra, tavan, plan.tasinabilir, plan.tasinacak_blok))

    # ---------------------------------------------------------------- K310 ekseni
    # 11. OKSUZ GOVDE — KAYNAK KUTU. D1-D10 "bu turda kaybettim mi" diye sorar; bu iddia
    #     "elimdeki zaten kirik mi" diye sorar. Kirik bir kutuyu arsive kureklemek, kaybi
    #     iki dosyaya birden yayar -> once SOYLE, sonra tasi.
    for satir_no, ornek in oksuz_govdeler(kutu_metin):
        h.append("D11 OKSUZ GOVDE (KUTU): %d. satirda BASLIKSIZ dolu bolut -> bir blogun "
                 "`## ` basligi DUSMUS olabilir | ilk satir: %s" % (satir_no, ornek))

    # 12. OKSUZ GOVDE — BU TURDA ARSIVE EKLENEN METIN. Kutu temiz olsa bile kesim/uretim
    #     kolu bir basligi geride birakirsa arsive oksuz govde yazilir; ayri iddia.
    for satir_no, ornek in oksuz_govdeler(ek, fm_atla=False):
        h.append("D12 OKSUZ GOVDE (EK): eklenen metnin %d. satirinda BASLIKSIZ dolu bolut "
                 "| ilk satir: %s" % (satir_no, ornek))

    # 13. BASLIK+GOVDE AYNI DUZLEME GITTI — tasinan HER blogun BASLIK satiri, yeni arsivin
    #     eklenen kuyrugunda BIREBIR duruyor. (D4/D5 metnin sonda oldugunu olcer; bu iddia
    #     BASLIK SAYISINI olcer -> "govde gitti, baslik gitmedi" hali ADIYLA yakalanir.)
    ek_baslik = blok_sayisi(ek)
    if ek_baslik != plan.tasinacak_blok:
        h.append("D13 BASLIK SAYISI: plan %d blok tasiyor ama arsive eklenen metinde %d "
                 "`## ` basligi var -> baslik ile govde AYRI dustu"
                 % (plan.tasinacak_blok, ek_baslik))
    return h


# ------------------------------------------------------------------- kilit + yazma
def arsiv_kuyrugu(arsiv_metin, en_az_satir):
    """(bas_satir_no_1indeksli, kuyruk_metni) — arsivin SON en_az_satir satirini kapsayan,
    BLOK BASINDAN baslayan pencere.

    NEDEN BLOK HIZALI: rastgele bir satirdan kesmek, pencerenin BASINDA yapay bir
    "baslıksız govde" uretir ve raporu YALANLAR. Pencere daima bir `## ` basligindan
    baslar; bulunamazsa dosyanin basindan baslar ve bu ciktida SOYLENIR.
    """
    satirlar = (arsiv_metin or "").splitlines(keepends=True)
    if not satirlar:
        return 1, ""
    hedef = max(0, len(satirlar) - max(0, en_az_satir))
    baslar = blok_baslari(satirlar)
    uygun = [b for b in baslar if b <= hedef]
    bas = uygun[-1] if uygun else (baslar[0] if baslar else 0)
    return bas + 1, "".join(satirlar[bas:])


def kilit_al(yol):
    """(fd, hata) — LOCK_EX|LOCK_NB. Kilit baskasindaysa fd None.

    NEDEN NON-BLOCKING: bu arac kanca/zamanlanmis is icinde de kosabilir; kilidi
    tutan baska bir yazici varken BEKLEMEK degil CEKILMEK dogrudur (o yazici zaten
    kutuyu degistiriyor, bizim plani bayatlatiyor). Sessizce basari donmez -> RC_KILIT.
    """
    try:
        fd = open(yol, "a+")
    except OSError as e:
        return None, "kilit dosyasi acilamadi: %s -> %s" % (yol, e)
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        fd.close()
        return None, "kilit BASKASINDA (%s): %s" % (yol, e)
    return fd, None


def kilit_birak(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    finally:
        fd.close()


def atomik_yaz(yol, metin):
    """Gecici dosya + fsync + os.replace. Kismi/yarim dosya GORUNMEZ."""
    dizin = os.path.dirname(os.path.abspath(yol)) or "."
    kip = None
    if os.path.exists(yol):
        kip = os.stat(yol).st_mode & 0o777
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".kutu-arsivle-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        if kip is not None:
            os.chmod(gecici, kip)
        os.replace(gecici, yol)
        gecici = None
    finally:
        if gecici and os.path.exists(gecici):
            os.unlink(gecici)


# --------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Ortak posta kutusunu tavana indir; en eski bloklari arsive TASI.")
    ap.add_argument("--kutu", default=KUTU_VARSAYILAN)
    ap.add_argument("--arsiv", default=None,
                    help="varsayilan: kutu ile ayni dizinde <ad>-arsiv.md")
    ap.add_argument("--kilit", default=None,
                    help="varsayilan: kutu ile ayni dizinde .<ad>.lock")
    ap.add_argument("--tavan", type=int, default=VARSAYILAN_TAVAN)
    ap.add_argument("--koru", type=int, default=VARSAYILAN_KORU,
                    help="en ustteki kac blok DOKUNULMAZ (varsayilan 3)")
    ap.add_argument("--su-seviye-orani", type=float, default=SU_SEVIYESI_ORANI,
                    help="rotasyon sonrasi kutu tavanin bu kadarina kadar iner "
                         "(varsayilan: 0.8 = %%80). O1 (16 Agu) caresi: gelecek "
                         "bloklar icin bas payi birakir.")
    ap.add_argument("--kuru", action="store_true",
                    help="hicbir sey yazma, ne yapacagini SAYIYLA bas")
    ap.add_argument("--arsiv-kuyruk", type=int, default=VARSAYILAN_ARSIV_KUYRUK,
                    help="arsivin son kac satirinda oksuz govde RAPORLANSIN (blok hizali; "
                         "0 = kapali). RAPOR eksenidir, cikis kodunu BELIRLEMEZ — bkz. "
                         "K310 kapsam notu")
    a = ap.parse_args(argv)

    if a.tavan < 1:
        print("KIRMIZI: --tavan >= 1 olmali")
        return RC_KIRMIZI
    if a.koru < 0:
        print("KIRMIZI: --koru >= 0 olmali")
        return RC_KIRMIZI
    if a.su_seviye_orani <= 0 or a.su_seviye_orani > 1:
        print("KIRMIZI: --su-seviye-orani (0, 1] araliginda olmali")
        return RC_KIRMIZI

    kutu_yolu = os.path.abspath(os.path.expanduser(a.kutu))
    if a.arsiv:
        arsiv_yolu = os.path.abspath(os.path.expanduser(a.arsiv))
    elif kutu_yolu == os.path.abspath(KUTU_VARSAYILAN):
        arsiv_yolu = os.path.abspath(ARSIV_VARSAYILAN)
    else:
        kok = kutu_yolu[:-3] if kutu_yolu.endswith(".md") else kutu_yolu
        arsiv_yolu = kok + "-arsiv.md"
    if a.kilit:
        kilit_yolu = os.path.abspath(os.path.expanduser(a.kilit))
    else:
        kilit_yolu = os.path.join(os.path.dirname(kutu_yolu),
                                  "." + os.path.basename(kutu_yolu) + ".lock")

    print("KUTU  : %s" % kutu_yolu)
    print("ARSIV : %s" % arsiv_yolu)
    print("KILIT : %s" % kilit_yolu)
    print("tavan=%d koru=%d su_seviye_orani=%.2f kip=%s" % (
        a.tavan, a.koru, a.su_seviye_orani, "KURU" if a.kuru else "YAZAR"))

    # 🔴 KILIT ONCE, OKUMA SONRA: bayat kopyayla plan yapip baska bir yazicinin
    # ekledigi blogu ezmemek icin dosya KILIT ALTINDA okunur.
    kilit, khata = kilit_al(kilit_yolu)
    if kilit is None:
        print("KILIT ALINAMADI -> hicbir sey yapilmadi (fail-closed): %s" % khata)
        return RC_KILIT
    try:
        kutu_metin, hata = oku(kutu_yolu)
        if hata:
            print("KIRMIZI (kutu okunamadi): %s" % hata)
            return RC_KIRMIZI
        if os.path.exists(arsiv_yolu):
            arsiv_metin, hata = oku(arsiv_yolu)
            if hata:
                print("KIRMIZI (arsiv okunamadi): %s" % hata)
                return RC_KIRMIZI
            arsiv_var = True
        else:
            arsiv_metin, arsiv_var = None, False

        p = planla(kutu_metin, a.tavan, a.koru)
        p.su_seviye = int(a.tavan * a.su_seviye_orani)
        if p.su_seviye < 1:
            p.su_seviye = 1
        if p.hata:
            print("KIRMIZI (bozuk/yarim kutu): %s" % p.hata)
            return RC_KIRMIZI

        arsiv_once = len((arsiv_metin or "").splitlines())
        print("once_satir=%d blok=%d korunan=%d tasinabilir=%d su_seviye=%d"
              % (p.once_satir, p.blok_toplam, p.korunan, p.tasinabilir,
                 getattr(p, "su_seviye", int(a.tavan * a.su_seviye_orani))))

        # 🔴 K310 — HER KOSUMDA olculur, is olsa da olmasa da. Bu arac kutunun TAMAMINI
        # her push'ta okuyan TEK otomatik gozdur; yapisal butunlugu burada sormamak,
        # hic sormamaktir.
        kutu_oksuz = oksuz_govdeler(kutu_metin)
        kutu_ayrac = ayrac_sayisi(kutu_metin)
        print("oksuz_govde_kutu=%d ayrac_kutu=%d bolut_kutu=%d  [KAPI]"
              % (len(kutu_oksuz), kutu_ayrac, kutu_ayrac + 1))
        for satir_no, ornek in kutu_oksuz:
            print("  ! KUTU %d. satir: BASLIKSIZ dolu bolut | %s" % (satir_no, ornek))
        # 🔴 KORLUK BEYANI — "0" ile "olcemedim" AYNI SAYIYLA basilmaz. Ayracsiz bir
        # kutuda dusen baslik govdeleri birlestirir ve YAPISAL iz birakmaz; bunu 0
        # diye raporlamak K310'un kendi hatasini tekrar etmektir.
        if kutu_ayrac == 0:
            print("EKSEN_KOR=oksuz_govde_kutu sebep=kutuda ayrac (`---`) YOK -> tek bolut; "
                  "dusen baslik bu eksende YAPISAL OLARAK gorunmez (0 = 'temiz' DEGIL, "
                  "'olculemedi')")
        print("imza_yigilmasi_kutu=%d  [RAPOR — ayractan bagimsiz ikinci sinyal; "
              "cikis kodunu BELIRLEMEZ]" % imza_yigilmasi(kutu_metin))
        if a.arsiv_kuyruk > 0:
            k_bas, k_metin = arsiv_kuyrugu(arsiv_metin, a.arsiv_kuyruk)
            k_oksuz = oksuz_govdeler(k_metin, fm_atla=False)
            print("oksuz_govde_arsiv_kuyruk=%d  [RAPOR — kapsam: arsiv satir %d..%d "
                  "(%d satir, blok hizali); cikis kodunu BELIRLEMEZ]"
                  % (len(k_oksuz), k_bas, arsiv_once, arsiv_once - k_bas + 1))
            for satir_no, ornek in k_oksuz:
                print("  ! arsiv kuyrugunda OKSUZ GOVDE (pencere ici satir %d): %s"
                      % (satir_no, ornek))

        if p.kesim is None:
            if p.tavan_asili_kaldi:
                print("UYARI: %d satir tavani (%d) asiyor ama korunan %d blok disinda "
                      "tasinabilir blok YOK -> is yapilmadi"
                      % (p.once_satir, a.tavan, p.korunan))
            else:
                print("tasinacak_blok=0 sonra_satir=%d" % p.once_satir)
                print("TAVAN ALTINDA — is yok")
            # 🔴 "Is yok" BUTUNLUK BEYANI DEGILDIR: tasima olmasa bile kirik kutu
            # SESSIZ GECMEZ (K310'un ta kendisi — arac calisti, yesil dondu, kutu kirikti).
            if kutu_oksuz:
                print("BUTUNLUK KIRMIZI — HICBIR SEY YAZILMADI (tasima zaten yoktu):")
                for satir_no, ornek in kutu_oksuz:
                    print("  - D11 OKSUZ GOVDE (KUTU): %d. satirda BASLIKSIZ dolu bolut "
                          "| ilk satir: %s" % (satir_no, ornek))
                return RC_KIRMIZI
            return RC_OK

        yeni_kutu, tasinan, ek, yeni_arsiv = aday_metinler(
            kutu_metin, arsiv_metin, p, arsiv_yolu)
        yeni_kutu, ek, yeni_arsiv, ahata = ariza_uygula(yeni_kutu, ek, yeni_arsiv)
        if ahata:
            print("KIRMIZI: %s" % ahata)
            return RC_KIRMIZI

        hatalar = dogrula(kutu_metin, arsiv_metin, yeni_kutu, tasinan, ek, yeni_arsiv,
                          p, a.tavan, a.koru)
        print("tasinacak_blok=%d tasinacak_satir=%d sonra_satir=%d sonra_blok=%d"
              % (p.tasinacak_blok, p.tasinan_satir, len(yeni_kutu.splitlines()),
                 blok_sayisi(yeni_kutu)))
        print("arsiv_once_satir=%d arsiv_sonra_satir=%d arsiv_yeni_dosya=%s"
              % (arsiv_once, len(yeni_arsiv.splitlines()), "hayir" if arsiv_var else "EVET"))
        if p.tavan_asili_kaldi:
            print("UYARI: tasinabilir bloklar tukendi, %d satir hala tavanin (%d) ustunde"
                  % (len(yeni_kutu.splitlines()), a.tavan))

        ek_oksuz = oksuz_govdeler(ek, fm_atla=False)
        print("oksuz_govde_ek=%d  [KAPI]" % len(ek_oksuz))

        if hatalar:
            print("LOSSLESS DOGRULAMASI KIRMIZI — HICBIR SEY YAZILMADI:")
            for x in hatalar:
                print("  - %s" % x)
            return RC_KIRMIZI
        # 🔴 K310: beyan artik SAYIYA dayaniyor. `iddia` sayisi ELLE YAZILMAZ —
        # IDDIA_EKSENLERI'nden turer (elle kopyalanan sayi kaynagindan ayrisir sinifi).
        print("lossless_dogrulama=GECTI (iddia=%d, oksuz_govde_kutu=%d, oksuz_govde_ek=%d)"
              % (len(IDDIA_EKSENLERI), len(kutu_oksuz), len(ek_oksuz)))

        if a.kuru:
            print("KURU KIP — hicbir sey yazilmadi")
            return RC_OK

        # ONCE ARSIV, SONRA KUTU (bkz. modul basligi: fail-toward-duplication).
        atomik_yaz(arsiv_yolu, yeni_arsiv)
        atomik_yaz(kutu_yolu, yeni_kutu)
        print("YAZILDI: %d blok / %d satir arsive tasindi" % (p.tasinacak_blok,
                                                              p.tasinan_satir))
        return RC_OK
    finally:
        kilit_birak(kilit)


if __name__ == "__main__":
    sys.exit(main())
