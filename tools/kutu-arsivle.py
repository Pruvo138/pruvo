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
  * KORUMA (K313g, 27 Agu): ISLENMEMIS kapanis jetonu tasiyan blok ROTASYONA GIRMEZ.
    Bkz. asagidaki "GORUNURLUK" blogu.
  * JETON KONUMU (K318 KOL-1, 27 Agu): jeton yalniz blogun KAPANIS KONUMUNDA
    bekleyen sayilir; GOVDE ICINDEKI anma koruma URETMEZ. Bkz. "YANLIS POZITIF".
  * GRANULERLIK (K318 KOL-2, 27 Agu): rotasyon BITISIK KUYRUK sartina bagli DEGIL —
    korumali blok YERINDE ATLANIR, altindaki/ustundeki korumasiz eski bloklar tasinir.
    Bkz. "GRANULERLIK".

🔴 GORUNURLUK — LOSSLESS OLMAK GORUNUR OLMAK DEGILDIR (K313g, 27 Agu 2026)
OLCULEN VAKA (mimarin kendi elinden, bugun): iki cip (`KraL-BayatYuzey-27Agu`,
`KraL-K313Sinif-27Agu`) kural ⑤'in istedigi kapanis satirini kutuya GERCEKTEN yazdi
(mimar o an okudu). Dakikalar sonra ayni oturumda bu arac `koru=3` ile kostu ve IKI
BLOK DA arsive tasindi (`mimar-posta-kutusu-arsiv.md:50713` · `:50791`); guncel kutuda
`grep -c` = 0. Rotasyon LOSSLESS'ti — hicbir sey silinmedi — ama Okan arsiv hareketini
PANELDEN/KUTUDAN yapar: satir onun bakacagi HICBIR yuzeyde kalmadi -> is bitmis cip
"ACIK" gorundu, mimar zamani yendi, akis durdu. Bugun ayni sinifta arsive dusen blok
sayisi 5'ti (yukaridaki ikisi + `KraL-TabanKirmizi-27Agu` + `KraL-KorGoz-27Agu` +
`MaCiT-DefterDenetim-27Agu`).
SINIF: K310'un kardesi ([[lossless-beyani-blok-butunlugu-olcmez]]) — beyan DOGRU, ama
olctugu sey ihtiyaci karsilamiyor. Arac, tasidigi blogun HALA ISLEM BEKLEDIGINI bilmiyordu.
CARE (bu modulde, tek kaynak): bir blok ISLENMEMIS kapanis jetonu (BEKLEYEN_JETON)
tasidigi surece KORUMALIDIR — yas/sira/`koru` sayisi bunu EZEMEZ. Jeton ISLENMIS bicime
(ISLENMIS_JETON) cevrilince blok rotasyona ACILIR. Arac bir blogun islenip islenmedigini
BILMIYORSA TASIMAZ (fail-closed; genis tespit = guvenli yon).
KOTA KILIDI ACILMAZ: korunan bloklar yuzunden kutu tavanin ustunde kalabilir. Bu durumda
arac SESSIZCE PES ETMEZ — `KORUMALI_BEKLEYEN=<n>` + `HUKUM=KORUMA_TUTTU` basar ve ne
yapilmasi gerektigini SOYLER. Gorunurluk kota kirmizisina TERCIH EDILIR, ama hal GIZLENMEZ.

🔴 YANLIS POZITIF — GOVDEDEKI ANMA KORUMA URETMEZ (K318 KOL-1, 27 Agu 2026)
OLCULEN VAKA: K313g tespiti BILEREK GENISTI (blogun HER satiri taranir). Bedeli olculdu —
canli kutuda jeton 7 konumda geciyordu ama yalnizca 3'u GERCEK kapanis satiriydi; kalan 4'u
KURALIN KENDISINI TARTISAN govde metniydi (bu modulu anlatan raporlar, kapanis satirlarini
sayan olcum bloklari). Yanlis pozitifler blogu SUSUZ YERE kilitledi ve kilit yukari dogru
yayildi. BEDEL SAYILDI: `tools/defter-kota-kapisi.py` tek gunde DORT ayri commit'i
`KUTU_ASILDI` ile durdurdu; iki dal (13 dosya) commit'lenemedi. UCUNCU TEKRAR -> tekil yama
YASAK ([[ucuncu-tekrar-sinif-kapisi]]), sinif onarildi.
CARE: jeton yalniz blogun KAPANIS KONUMUNDA bekleyen sayilir. KAPANIS KONUMU = blogun SON
ICERIK satiri; sondaki bos satirlar ve `---` ayraci YOK SAYILIR (cit ICINDEKI `---` ayrac
DEGILDIR, o icerik sayilir). Okan kurali ⑤ zaten "kapanisinin EN SONUNA" diyor — olcut
kuralin kendi metnidir, gevsetme degil DARALTMA.
FAIL-CLOSED KORUNDU: blok siniri AYRISTIRILAMAZSA (kapanmamis cit, icerik satiri olmayan
blok) ve blokta jeton GECIYORSA blok yine KORUMALI sayilir — "bilmiyorsam tasimam".
GOVDE ANMASI GIZLENMEZ: kac blogun jetonu yalniz govdesinde tasidigi `govde_anmasi=<n>`
diye HER kosumda basilir (0 ile n ayni satirdan okunur).
TEK KAYNAK: ICRA kolu (planla) ve DENETIM kolu (dogrula D14) AYNI `korumali_bloklar()`
fonksiyonunu cagirir; tanim ikinci bir yere KOPYALANMAZ ([[ikiz-tanim-sessiz-ayrisma]]).

🔴 GRANULERLIK — KORUMALI BLOK KUYRUGU REHIN ALMAZ (K318 KOL-2, 27 Agu 2026)
OLCULEN VAKA: rotasyon BITISIK KUYRUK tasiyordu (tek `kesim` indeksi, sondan k blok). Bu
tasarimda EN DIPTEKI bir korumali blok, tek basina USTUNDEKI HER SEYI kilitler — mesru bir
bekleyen cip (ArTisT) tavan asimini tek basina kalici hale getirdi.
CARE: korumali blok YERINDE ATLANIR. Adaylar `koru` tabanindan asagisi EKSI korumali kume;
en ESKIDEN baslanarak, kutu SU SEVIYESINE inene kadar secilir. Korumali bloklar KUTUDA
KALIR, arsive giden bloklar OZGUN SIRADA (artan blok indeksi = yeni->eski) eklenir.
KAYIPSIZLIK IKI EKSENDE: `tasinan + kalan == once` hem BLOK hem BAYT ekseninde dogrulanir
ve UCU DE BASILIR — tek eksen kabul DEGILDIR ([[lossless-beyani-blok-butunlugu-olcmez]]).
GERILEME YOK: korumali blok YOKKEN secim bitisik kuyruga OZDES duser (D1 partisyonu ve
kabul testi bunu ayrica olcer).

YAZMA SIRASI — NEDEN ONCE ARSIV: iki ayri dosya tek islemde atomik yazilamaz. Once ARSIV
(ekleme), sonra KUTU (kisaltma) yazilir. Ikisinin arasinda cokme olursa sonuc MUKERRER
icerik olur (arsivde var, kutuda da duruyor) — geri alinabilir. Ters sirada sonuc KAYIP
olurdu. Fail-toward-duplication, asla fail-toward-loss.

SENTETIK ARIZA ENJEKSIYONU (yalniz nobetci icin): PRUVO_KUTU_ARSIVLE_ARIZA ortam
degiskeni set edilmediginde HICBIR ETKISI YOKTUR. Set edildiginde aday metinler
dogrulamadan ONCE kasten bozulur; kabul testi boylece "lossless dogrulamasi GERCEKTEN
kirmizi yakiyor mu" sorusunu OLCEBILIR (dogrulamayi silen mutant KIRMIZI yanar).
Degerler: arsiv-satir-dus | kutu-satir-dus | arsiv-onek-boz | arsiv-sira-boz |
          koruma-jeton-sizdir | kutu-blok-dus

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
IDDIA_EKSENLERI = ("D1", "D1b", "D1c", "D2", "D3", "D4", "D5", "D5b", "D6", "D6b",
                   "D6c", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "D14",
                   "D15", "D16")

# 🔴 KAPANIS JETONU — TEK KAYNAK (K313g). Kural ⑤ (Okan, baglayici) isi biten cipin
# kapanisinin SONUNA birebir `✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM` koymasini ister; satir
# YOKSA cip ACIK sayilir. Bu iki sabit o jetonun IKI HALINI adlandirir ve BASKA HICBIR
# YERDE tekrar tanimlanmaz ([[ikiz-tanim-sessiz-ayrisma]]):
#   BEKLEYEN  = cip bitti, Okan HENUZ ARSIVLEMEDI -> blok KORUMALI, rotasyona GIRMEZ.
#   ISLENMIS  = Okan arsivledi, mimar jetonu CEVIRDI -> blok rotasyona ACIK.
# Tespit BILEREK GENISTIR: ayirt edici KELIME aranir, tam cumle degil — cunku jeton
# canli kutuda en az bes farkli sarmalda gecmektedir (`✅ …`, `✅ **…**`, `… — ArTisT`,
# `✅ İŞ BİTTİ (…) — ARŞİVLENEBİLİRİM`, ve `## ` BASLIGININ ICINDE). Dar bir desen bu
# sarmallarin bir kismini kacirir ve tam da onarmaya calistigimiz kaybi uretir.
# YANLIS-POZITIF YONU KASITLIDIR: bir blogun islenip islenmedigi BILINMIYORSA blok
# TASINMAZ (fail-closed). Bedeli tavan asimidir ve o bedel ADIYLA BASILIR.
# Iki kelime ortak on-ek tasimaz ("ARŞİVLENEBİLİRİM" vs "ARŞİVLENDİ"), yani ISLENMIS
# bicim BEKLEYEN desenine ASLA denk gelmez — cevirme islemi tek yonlu ve gerilemesizdir.
BEKLEYEN_JETON = "ARŞİVLENEBİLİRİM"
ISLENMIS_JETON = "ARŞİVLENDİ"

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


# ------------------------------------------------------------------- KORUMA KOLU
def blok_araliklari(satirlar, baslar):
    """[(bas, son_haric)] — her `## ` blogunun satir araligi. Son blok dosya sonuna kadar.

    Blogun ARDINDAN gelen ayrac (`---`) ve bos satirlar BLOGUN ICINDEDIR: bir sonraki
    blogun BASINA kadar her sey o bloga aittir. Bu, tasinan metnin kendi ayracini da
    goturmesini saglar (arsivde bloklar birbirine yapismaz).
    """
    araliklar = []
    i = 0
    while i < len(baslar):
        son = baslar[i + 1] if i + 1 < len(baslar) else len(satirlar)
        araliklar.append((baslar[i], son))
        i += 1
    return araliklar


def kapanis_satiri(satirlar, bas, son):
    """(kapanis_indeksi, hata) — blogun KAPANIS KONUMU = SON ICERIK satiri.

    🔴 K318 KOL-1 TEK KAYNAGI. Okan kurali ⑤: kapanis jetonu blogun EN SONUNA konur.
    Dolayisiyla "bekleyen mi" sorusu blogun SON ICERIK SATIRINA sorulur, govdesine degil.

    Sondan geriye yururken YOK SAYILAN iki sey (ve YALNIZ bu ikisi):
      * bos satir (blok sonu bosluklari),
      * CIT DISINDA duran ayrac satiri (`---`) — blogu bir sonrakinden ayiran cizgi.
    Cit ICINDEKI `---` bir ayrac DEGIL, kod/metin ICERIGIDIR ve atlanmaz; atlansaydi
    tarama gercek icerigin GERISINE kayar, kapanis satirini kacirirdi.

    FAIL-CLOSED iki hal (hata dolu doner):
      * blokta hic ICERIK satiri yok (yalniz bosluk/ayrac),
      * cit ACILDI ama KAPANMADI -> hangi satirin icerik oldugu bilinemez.
    Cagiran bu hallerde blogu KORUMALI sayar (bkz. korumali_bloklar).
    """
    if son <= bas:
        return None, "BOS BLOK ARALIGI (bas=%d son=%d)" % (bas, son)
    cit_ici = []
    ic = False
    j = bas
    while j < son:
        if FENCE_RE.match(satirlar[j]):
            # Cit ACAN satirin KENDISI cit disidir; kapatan satir cit icidir.
            cit_ici.append(ic)
            ic = not ic
        else:
            cit_ici.append(ic)
        j += 1
    if ic:
        return None, "CIT (```/~~~) ACILDI ama KAPANMADI -> blok yapisi AYRISTIRILAMADI"
    j = son - 1
    while j >= bas:
        s = satirlar[j]
        if not s.strip():
            j -= 1
            continue
        if not cit_ici[j - bas] and AYRAC_RE.match(s):
            j -= 1
            continue
        return j, None
    return None, "blokta ICERIK satiri YOK (yalniz bosluk/ayrac)"


def korumali_bloklar(satirlar, baslar):
    """([(blok_idx, satir_no_1indeksli, ozet, sinif)], govde_anmasi) — TEK KAYNAK.

    🔴 BU FONKSIYON HEM ICRA HEM DENETIM KOLUNUN OKUDUGU TEK TANIMDIR. `planla()`
    (icra) ve `dogrula()` D14 (denetim) BUNU cagirir; ikinci bir "jeton var mi"
    testi HICBIR YERDE yazilmaz ([[ikiz-tanim-sessiz-ayrisma]]).

    KORUMALI sayilan iki sinif:
      "KAPANIS"     — blogun KAPANIS KONUMUNDAKI satir BEKLEYEN jeton tasiyor.
      "FAIL_CLOSED" — blokta jeton GECIYOR ama kapanis konumu AYRISTIRILAMADI.
    GOVDE ANMASI korumali DEGILDIR: blokta jeton var, kapanis konumunda YOK -> blok
    rotasyona ACIK. Bu bilgi YUTULMAZ, ikinci donus degeriyle SAYILIR ve basilir.
    """
    bulgu = []
    govde_anmasi = 0
    i = 0
    araliklar = blok_araliklari(satirlar, baslar)
    while i < len(araliklar):
        bas, son = araliklar[i]
        metin = "".join(satirlar[bas:son])
        if BEKLEYEN_JETON not in metin:
            i += 1
            continue
        idx, hata = kapanis_satiri(satirlar, bas, son)
        if hata is not None:
            bulgu.append((i, bas + 1, "AYRISTIRILAMADI: %s" % hata, "FAIL_CLOSED"))
        elif BEKLEYEN_JETON in satirlar[idx]:
            bulgu.append((i, idx + 1, satirlar[idx].strip()[:70], "KAPANIS"))
        else:
            govde_anmasi += 1
        i += 1
    return bulgu, govde_anmasi


def sabit_indeksler(blok_sayisi_, koru, korumali_indeksler):
    """ROTASYONA GIRMEYECEK blok indeksleri kumesi — TEK KAYNAK.

    Iki kaynaktan TURER, elle kopyalanmaz:
      * `koru` TABANI: en ustteki `koru` blok her zaman dokunulmaz,
      * KORUMA: bekleyen kapanis jetonu tasiyan blok, NEREDE OLURSA OLSUN dokunulmaz.
    🔴 K318 KOL-2: korumali blok artik ALTINDAKI bloklari REHIN ALMAZ — kume bir
    ARALIK degil, ayrik bir KUMEDIR; rotasyon korumaliyi YERINDE ATLAR.
    """
    sabit = set(range(min(koru, blok_sayisi_)))
    sabit.update(korumali_indeksler)
    return sabit


# --------------------------------------------------------------------- planlama
class Plan(object):
    def __init__(self):
        self.hata = None
        # 🔴 K318 KOL-2: karar birimi artik tek bir `kesim` INDEKSI degil, tasinacak
        # BLOK INDEKSLERI kumesidir (korumali blok yerinde atlanabilsin diye).
        self.tasinan_bloklar = []   # artan sirada blok indeksleri (ozgun sira)
        self.araliklar = []         # [(bas, son)] her blok icin
        self.onek_son = 0           # frontmatter + onsoz bitis indeksi (baslar[0])
        self.tasinacak_blok = 0
        self.blok_toplam = 0
        self.korunan = 0
        self.tasinabilir = 0
        self.once_satir = 0
        self.sonra_satir = 0
        self.tasinan_satir = 0
        self.once_bayt = 0
        self.sonra_bayt = 0
        self.tasinan_bayt = 0
        self.tavan_asili_kaldi = False
        # KORUMA KOLU (K313g + K318)
        self.korumali = []          # [(blok_idx, satir_no, ozet, sinif)]
        self.govde_anmasi = 0       # jetonu YALNIZ govdesinde anan blok sayisi
        self.sabit = set()          # rotasyona GIRMEYEN blok indeksleri
        self.korumali_kilitledi = 0  # `koru` tabaninin ALTINDA kalip yerinde atlanan
        self.yerinde_atlanan = 0     # tasinanlarin USTUNDE kalan korumali blok sayisi
        self.koruma_tuttu = False    # is YOKLUGUNUN sebebi KORUMA mi


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
    p.once_bayt = len(kutu_metin)
    p.sonra_bayt = len(kutu_metin)

    fm_son, hata = frontmatter_sonu(satirlar)
    if hata:
        p.hata = hata
        return p

    baslar = blok_baslari(satirlar, fm_son)
    p.blok_toplam = len(baslar)
    p.araliklar = blok_araliklari(satirlar, baslar)
    p.onek_son = baslar[0] if baslar else len(satirlar)

    # 🔴 KORUMA KOLU (K313g + K318 KOL-1) — TEK KAYNAK: kapanis konumu olcutu.
    p.korumali, p.govde_anmasi = korumali_bloklar(satirlar, baslar)
    korumali_idx = [b for b, _s, _o, _k in p.korumali]
    p.korumali_kilitledi = len([b for b in korumali_idx if b >= koru])
    p.sabit = sabit_indeksler(len(baslar), koru, korumali_idx)

    p.korunan = len(p.sabit)
    p.tasinabilir = max(0, len(baslar) - len(p.sabit))

    # Su seviyesi: tavanin bu kadarina kadar dus (varsayilan 0.8). Esik
    # mutlak olarak > 0 ve <= 1 olmali.
    su_seviye = int(tavan * SU_SEVIYESI_ORANI)
    if su_seviye < 1:
        su_seviye = 1

    if p.once_satir <= tavan:
        return p                            # tavan altinda -> is yok
    if p.tasinabilir <= 0:
        p.tavan_asili_kaldi = True
        # SEBEP AYRIMI: is yoklugunun sebebi `koru` mu, KORUMA mi? Iki hal ayni
        # ciktiyi basarsa kota kilidi SESSIZ kalir — tam da yasaklanan sey.
        p.koruma_tuttu = p.korumali_kilitledi > 0
        return p

    # 🔴 K318 KOL-2 SECIM — EN ESKIDEN baslanir, KORUMALI blok YERINDE ATLANIR.
    # Korumali blok YOKKEN bu dongu bitisik kuyrugu secer ve eski davranisa OZDES
    # duser (kalan satir sayisi = baslar[n-k]); kabul testi bunu ayrica olcer.
    secilenler = []
    kalan_satir = p.once_satir
    i = len(p.araliklar) - 1
    while i >= 0:
        if kalan_satir <= su_seviye:
            break
        if i not in p.sabit:
            bas, son = p.araliklar[i]
            secilenler.append(i)
            kalan_satir -= (son - bas)
        i -= 1
    secilenler.sort()
    p.tasinan_bloklar = secilenler
    p.tasinacak_blok = len(secilenler)

    yeni_kutu, tasinan = bolumle(kutu_metin, p)
    p.sonra_satir = len(yeni_kutu.splitlines())
    p.tasinan_satir = len(tasinan.splitlines())
    p.sonra_bayt = len(yeni_kutu)
    p.tasinan_bayt = len(tasinan)
    p.tavan_asili_kaldi = p.sonra_satir > tavan
    # Tasinan EN YENI blogun USTUNDE kalan korumali blok sayisi — "yerinde atlandi"
    # halinin SAYISI (0 ise rotasyon bitisik kuyruk olmustur).
    if secilenler:
        p.yerinde_atlanan = len([b for b in korumali_idx if b > secilenler[0]])
    return p


def bolumle(kutu_metin, plan):
    """(yeni_kutu, tasinan) — plani metne uygular. DISKE YAZMAZ, YARGI VERMEZ.

    🔴 Bu fonksiyon TEK BOLME NOKTASIDIR: hem `planla()` (sayilari bilmek icin) hem
    `aday_metinler()` (metni uretmek icin) BUNU cagirir. Ikinci bir bolme kodu
    yazilirsa iki kol sessizce ayrisir ve "plan 4 blok diyor, metinde 3 var" sinifi
    dogar ([[ikiz-tanim-sessiz-ayrisma]]).
    """
    satirlar = kutu_metin.splitlines(keepends=True)
    tasinan_kume = set(plan.tasinan_bloklar)
    kalan = [satirlar[:plan.onek_son]]
    giden = []
    i = 0
    while i < len(plan.araliklar):
        bas, son = plan.araliklar[i]
        (giden if i in tasinan_kume else kalan).append(satirlar[bas:son])
        i += 1
    duz = []
    for parca in kalan:
        duz.extend(parca)
    duz2 = []
    for parca in giden:
        duz2.extend(parca)
    return "".join(duz), "".join(duz2)


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
    yeni_kutu, tasinan = bolumle(kutu_metin, plan)
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
    elif ariza == "koruma-jeton-sizdir":
        # 🔴 K313g DENETIM KOLUNUN OLCU ALETI: planla() dogru calissa bile, tasinan
        # metne ISLENMEMIS bir kapanis jetonu SIZARSA D14 bunu YAKALAMAK ZORUNDADIR.
        # D14 silinirse bu ariza sessizce diske yazilir -> kabul testi KIRMIZI yanar.
        # (D5b de birlikte ateslenir — bu yuzden kabul testi kirmiziyi ADIYLA arar,
        # "kirmizi geldi" ile yetinmez: [[K182]] hedef-kol atfi.)
        satir = "✅ IS BITTI — %s\n" % BEKLEYEN_JETON
        yeni_arsiv = yeni_arsiv + satir
        ek = ek + satir
    elif ariza == "kutu-blok-dus":
        # 🔴 K318 KOL-2 DENETIM KOLUNUN OLCU ALETI: GRANULER birlestirme, bitisik
        # dilimlemenin URETEMEYECEGI yeni bir ariza sinifi acar — KALAN bloklardan
        # birinin birlestirmede DUSMESI. Bitisik kesimde "kalan" tek dilimdi ve
        # boyle bir kayip imkansizdi; artik kalan, parcalarin birlestirilmesidir.
        # Bu ariza D1/D1c/D2/D6 tarafindan YAKALANMAK ZORUNDADIR.
        s = yeni_kutu.splitlines(keepends=True)
        yeni_baslar = blok_baslari(s)
        if len(yeni_baslar) >= 2:
            b1 = yeni_baslar[len(yeni_baslar) - 1]
            yeni_kutu = "".join(s[:b1])        # SON kalan blok sessizce DUSURULDU
    else:
        return yeni_kutu, ek, yeni_arsiv, "BILINMEYEN ariza kodu: %s" % ariza
    return yeni_kutu, ek, yeni_arsiv, None


# --------------------------------------------------------------------- dogrulama
def dogrula(kutu_metin, arsiv_metin, yeni_kutu, tasinan, ek, yeni_arsiv, plan, tavan):
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

    # 1. PARTISYON — orijinal metin, PLANIN BEYAN ETTIGI blok kumesine gore BAGIMSIZ
    #    yeniden bolunur ve uretilen iki metinle BIREBIR karsilastirilir.
    #    🔴 K318 KOL-2: bolunme artik BITISIK olmak zorunda degil, bu yuzden eski
    #    `yeni_kutu + tasinan == kutu_metin` yuklemi ARTIK GECERLI DEGIL; yerine
    #    ayni korunum UC AYRI eksende (partisyon / bayt toplami / satir toplami)
    #    kurulur. Tek eksen kabul DEGILDIR ([[lossless-beyani-blok-butunlugu-olcmez]]).
    bek_kutu, bek_tasinan = bolumle(kutu_metin, plan)
    if bek_kutu != yeni_kutu:
        h.append("D1 PARTISYON (KUTU): uretilen yeni kutu, planin blok kumesinden "
                 "bagimsiz turetilen metinle esit DEGIL (%d != %d bayt)"
                 % (len(yeni_kutu), len(bek_kutu)))
    if bek_tasinan != tasinan:
        h.append("D1b PARTISYON (TASINAN): uretilen tasinan metin, planin blok "
                 "kumesinden bagimsiz turetilen metinle esit DEGIL (%d != %d bayt)"
                 % (len(tasinan), len(bek_tasinan)))

    # 1c. BAYT TOPLAMI — `tasinan + kalan == once`, UTF-8 BAYT ekseninde (karakter
    #     DEGIL: kapi kutuyu gercek baytla olcer, iki yuzey ayni birimden konusur).
    b_once = len(kutu_metin.encode("utf-8"))
    b_kalan = len(yeni_kutu.encode("utf-8"))
    b_tas = len(tasinan.encode("utf-8"))
    if b_kalan + b_tas != b_once:
        h.append("D1c BAYT KORUNUMU: kalan(%d) + tasinan(%d) = %d != once(%d) bayt"
                 % (b_kalan, b_tas, b_kalan + b_tas, b_once))

    # 2. SATIR KORUNUMU — `tasinan + kalan == once`, SATIR ekseninde.
    if len(yeni_kutu_satir) + len(tasinan_satir) != len(kutu_satir):
        h.append("D2 SATIR KORUNUMU: kalan(%d) + tasinan(%d) = %d != once(%d) satir"
                 % (len(yeni_kutu_satir), len(tasinan_satir),
                    len(yeni_kutu_satir) + len(tasinan_satir), len(kutu_satir)))

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
    # 🔴 K318 KOL-2: "korunan" artik en ustteki N blogun ONEKI degil, `plan.sabit`
    # AYRIK KUMESIDIR (koru tabani + nerede olursa olsun korumali bloklar). Iddia:
    # o kumedeki HER blogun BASLIK satiri yeni kutuda BIREBIR duruyor.
    yk_satir = yeni_kutu.splitlines(keepends=True)
    yeni_baslik_satirlari = [yk_satir[b] for b in blok_baslari(yk_satir)]
    eksik = []
    for bi in sorted(plan.sabit):
        if bi >= len(baslar):
            continue
        basl = kutu_satirlar_ke[baslar[bi]]
        if yeni_baslik_satirlari.count(basl) != 1:
            eksik.append((bi, basl.strip()[:60]))
    if eksik:
        for bi, ozet in eksik[:5]:
            h.append("D9 SABIT BLOK KAYBI: rotasyona GIRMEMESI gereken %d. blok yeni "
                     "kutuda tam olarak bir kez BULUNMUYOR | %s" % (bi + 1, ozet))

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

    # ---------------------------------------------------------------- K313g ekseni
    # 14. 🔴 KORUMA — TASINAN METINDE ISLENMEMIS KAPANIS JETONU OLAMAZ.
    #     planla() ICRA eder (kesimi yukari iter), bu iddia DENETLER. Ikisi ayri kol:
    #     icra kolu bozulur/silinirse burasi KIRMIZI yakar ve HICBIR SEY yazilmaz —
    #     yani gerileme "sessiz kayip" degil "gurultulu duraklama" uretir.
    # 🔴 K318 KOL-1: iddia artik "ek'te jeton GECIYOR mu" DEGIL — o olcut GOVDE
    #    ANMASINI da ihlal sayardi ve icra kolundan AYRISIRDI (icra tasir, denetim
    #    kirmizi yakar -> arac kalici kilitlenirdi). DENETIM, ICRANIN OKUDUGU AYNI
    #    fonksiyonu cagirir: tasinan metin BLOKLARINA ayrilir ve KAPANIS KONUMU
    #    olcutu ORADA yeniden uygulanir ([[ikiz-tanim-sessiz-ayrisma]]).
    ek_satir_ke = ek.splitlines(keepends=True)
    ek_korumali, ek_govde = korumali_bloklar(ek_satir_ke, blok_baslari(ek_satir_ke))
    for _bi, satir_no, ozet, sinif in ek_korumali:
        h.append("D14 KORUMA IHLALI (%s): tasinan metnin %d. satirinda ISLENMEMIS "
                 "kapanis jetonu (%s) KAPANIS KONUMUNDA -> blok Okan'in bakacagi "
                 "yuzeyden GORUNMEZ olurdu. Fail-closed: hicbir sey yazilmadi. "
                 "(Jeton `%s` bicimine cevrilince blok rotasyona ACILIR.) | %s"
                 % (sinif, satir_no, BEKLEYEN_JETON, ISLENMIS_JETON, ozet))

    # ---------------------------------------------------------------- K318 KOL-2 ekseni
    # 15/16. SIRA — ozgun sira KORUNDU mu? D1 partisyonu metnin AYNI oldugunu olcer;
    #     bu iki iddia BAGIMSIZ bir eksenden sorar: tasinan basliklar ve kalan basliklar,
    #     orijinal baslik dizisinin (ayri ayri) ALT DIZILERI mi? Blok siralamasi bozan
    #     bir gerileme partisyon kimligini korusa bile burada KIRMIZI yanar.
    orij_baslik = [kutu_satirlar_ke[b] for b in baslar]
    tas_satir_ke = tasinan.splitlines(keepends=True)
    tas_baslik = [tas_satir_ke[b] for b in blok_baslari(tas_satir_ke)]
    if not alt_dizi_mi(tas_baslik, orij_baslik):
        h.append("D15 SIRA (TASINAN): tasinan bloklarin basliklari orijinal sirayi "
                 "KORUMUYOR (%d baslik) -> arsive ozgun sira DISINDA yazilirdi"
                 % len(tas_baslik))
    if not alt_dizi_mi(yeni_baslik_satirlari, orij_baslik):
        h.append("D16 SIRA (KALAN): kutuda kalan bloklarin basliklari orijinal sirayi "
                 "KORUMUYOR (%d baslik)" % len(yeni_baslik_satirlari))
    return h


def alt_dizi_mi(kucuk, buyuk):
    """`kucuk`, `buyuk` dizisinin SIRA KORUYAN bir alt dizisi mi (bitisik olmak zorunda
    degil)."""
    j = 0
    for oge in kucuk:
        while j < len(buyuk) and buyuk[j] != oge:
            j += 1
        if j >= len(buyuk):
            return False
        j += 1
    return True


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
                    help="en ustteki kac blok DOKUNULMAZ (varsayilan 3). TABANDIR: "
                         "bekleyen kapanis jetonu tasiyan blok NEREDE OLURSA OLSUN "
                         "ayrica dokunulmaz sayilir ve YERINDE ATLANIR "
                         "(bkz. KORUMA / sabit_indeksler)")
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

        # 🔴 K313g + K318 KORUMA KOLU — HER kosumda basilir, is olsa da olmasa da.
        # "0" ile "n" ayni satirdan okunur; sayi ADIYLA gecer. `govde_anmasi` de
        # BURADADIR: yanlis pozitiflerin ELENDIGI hal GIZLENMEZ, SAYILIR.
        print("KORUMALI_BEKLEYEN=%d govde_anmasi=%d taban_koru=%d kilitledi=%d "
              "yerinde_atlanan=%d  [KAPI]"
              % (len(p.korumali), p.govde_anmasi, a.koru, p.korumali_kilitledi,
                 p.yerinde_atlanan))
        for blok_idx, satir_no, ornek, sinif in p.korumali:
            print("  * KORUMALI blok %d/%d (satir %d, sinif=%s): ISLENMEMIS kapanis "
                  "jetonu KAPANIS KONUMUNDA | %s"
                  % (blok_idx + 1, p.blok_toplam, satir_no, sinif, ornek))
        if p.govde_anmasi:
            print("  · GOVDE ANMASI=%d blok: jeton blogun ICINDE geciyor ama KAPANIS "
                  "KONUMUNDA DEGIL -> koruma URETMEZ (K318 KOL-1), blok rotasyona ACIK."
                  % p.govde_anmasi)
        if p.korumali:
            print("NE YAPILMALI: bu cip(ler)in kapanisi ISLENSIN (Okan arsivlesin); sonra "
                  "o blokta `%s` -> `%s` cevrilir ve blok rotasyona ACILIR."
                  % (BEKLEYEN_JETON, ISLENMIS_JETON))

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

        if not p.tasinan_bloklar:
            if p.tavan_asili_kaldi:
                print("UYARI: %d satir tavani (%d) asiyor ama korunan %d blok disinda "
                      "tasinabilir blok YOK -> is yapilmadi"
                      % (p.once_satir, a.tavan, p.korunan))
                # 🔴 KOTA KILIDI ACILMAZ, ama GIZLENMEZ: sebep KORUMA ise ADIYLA soylenir.
                # Sessiz pes etme yasak (spec K313g); gorunurluk kota kirmizisina TERCIH
                # EDILIR ve bu tercih her kosumda TEKRAR BASILIR.
                if p.koruma_tuttu:
                    print("HUKUM=KORUMA_TUTTU rc=0 sebep=bekleyen kapanis blogu rotasyona "
                          "GIRMEZ (KORUMALI_BEKLEYEN=%d, kilitledi=%d, taban koru=%d). "
                          "Kutu tavanin USTUNDE kalabilir — GORUNURLUK kota kirmizisina "
                          "tercih edilir (Okan kurali ⑤); hal GIZLENMEDI, BASILDI."
                          % (len(p.korumali), p.korumali_kilitledi, a.koru))
                else:
                    print("HUKUM=KORU_TUTTU rc=0 sebep=--koru %d tasinabilir blok "
                          "birakmiyor (koruma kolu DEVREDE DEGIL)" % a.koru)
            else:
                print("tasinacak_blok=0 sonra_satir=%d" % p.once_satir)
                print("TAVAN ALTINDA — is yok")
                # 🔴 K318 KOL-3: HUKUM EKSENI TOTALDIR. Kapi bu satiri TUKETIR;
                # yalnizca "duraklama" hallerinde basilirsa kapi "HUKUM yok" diye
                # fail-closed bloklar ve masum bir commit durur. Her kosum TAM BIR
                # `HUKUM=` satiri basar — 0 ile n ayni satirdan okunur.
                print("HUKUM=TAVAN_ALTINDA rc=0 once_satir=%d tavan=%d"
                      % (p.once_satir, a.tavan))
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

        # D9 artik `plan.sabit` AYRIK KUMESINI okur (koru tabani + korumali bloklar);
        # ikinci bir sayi parametresi GECMEZ — kume planin kendisinden TURER.
        hatalar = dogrula(kutu_metin, arsiv_metin, yeni_kutu, tasinan, ek, yeni_arsiv,
                          p, a.tavan)
        print("tasinacak_blok=%d tasinacak_satir=%d sonra_satir=%d sonra_blok=%d"
              % (p.tasinacak_blok, p.tasinan_satir, len(yeni_kutu.splitlines()),
                 blok_sayisi(yeni_kutu)))
        # 🔴 K318 KOL-2 KAYIPSIZLIK BEYANI — IKI EKSEN, UC SAYI, HER KOSUMDA.
        # `tasinan + kalan == once` hem BLOK hem BAYT ekseninde BASILIR; tek eksen
        # kabul DEGILDIR. Sayilar dogrula() D1c/D2/D6 tarafindan AYRICA denetlenir.
        print("KAYIPSIZLIK blok: once=%d kalan=%d tasinan=%d toplam=%d  [KAPI]"
              % (p.blok_toplam, blok_sayisi(yeni_kutu), blok_sayisi(tasinan),
                 blok_sayisi(yeni_kutu) + blok_sayisi(tasinan)))
        # 🔴 BAYT DENINCE BAYT: UTF-8 kodlanmis uzunluk. `len(str)` KARAKTER sayar ve
        # bu kutuda (emoji + em-dash) ikisi AYRISIR; kapi kutuyu gercek BAYTLA olcuyor,
        # arac "bayt" derken karakter basarsa iki yuzey sessizce ayrisirdi.
        print("KAYIPSIZLIK bayt: once=%d kalan=%d tasinan=%d toplam=%d  [KAPI]"
              % (len(kutu_metin.encode("utf-8")), len(yeni_kutu.encode("utf-8")),
                 len(tasinan.encode("utf-8")),
                 len(yeni_kutu.encode("utf-8")) + len(tasinan.encode("utf-8"))))
        # 🔴 TEK `HUKUM=` SATIRI — hukum TEK KAYNAKTAN, TEK KEZ basilir. Kapi ilk
        # `HUKUM=` satirini okur; iki satir basmak hangi hukmun tuketildigini
        # BELIRSIZ birakirdi ([[ayni-alan-iki-hukum-biri-sessiz]]).
        if not p.tavan_asili_kaldi:
            print("HUKUM=TASIMA_YAPILABILIR rc=0 tasinacak_blok=%d sonra_satir=%d "
                  "tavan=%d" % (p.tasinacak_blok, p.sonra_satir, a.tavan))
        elif p.korumali_kilitledi > 0:
            print("HUKUM=KORUMA_TUTTU_KISMI rc=0 sebep=%d bekleyen kapanis blogu "
                  "YERINDE ATLANDI ve kutuda kaldi; tasinabilen %d blok tasindi ama "
                  "kutu (%d satir) tavanin (%d) USTUNDE kaldi"
                  % (p.korumali_kilitledi, p.tasinacak_blok, p.sonra_satir, a.tavan))
        else:
            print("HUKUM=TASIMA_YETMEDI rc=0 sebep=tasinabilir bloklar TUKENDI, kutu "
                  "(%d satir) tavanin (%d) USTUNDE kaldi (koruma kolu DEVREDE DEGIL)"
                  % (p.sonra_satir, a.tavan))
        print("tasinan_blok_indeksleri=%s (ozgun sira; bitisik_mi=%s)"
              % (",".join(str(x + 1) for x in p.tasinan_bloklar) or "-",
                 "EVET" if p.yerinde_atlanan == 0 else "HAYIR/YERINDE_ATLANDI"))
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
