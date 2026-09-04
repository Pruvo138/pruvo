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
  * CEVRIM (K341, 28 Agu): `--kapanislari-isle` KAPANIS KONUMUNDAKI BEKLEYEN jetonu
    ISLENMIS bicime cevirir ve o bloklari rotasyona ACAR. Kilidi ACAN kol artik
    ARACTADIR, mimarin ELINDE DEGIL. Bkz. "K341 CEVRIM KOLU" bolumu.

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

🔴 ACIK CIP — KAPANISSIZ `BASLIYORUM` BLOGU TASINMAZ (K329, 27-28 Agu 2026)
OLCULEN VAKA (iki kez): cip `KraL-NobetTuru-27Agu` 23:30'da kutuya `BASLIYORUM` blogunu yazdi;
23:38'de BASKA bir cipin bu araci kosumu (342 -> 222 satir) o blogu CIP HALA KOSARKEN
`mimar-posta-kutusu-arsiv.md:52842`'ye tasidi. Kayip YOK (`lossless` dogru calisti) ama canli
kutu artik ACIK cipi GOSTERMIYOR: "su an kim kosuyor" sorusunun cevabi arsive dustu. 28 Agu'da
ayni sey ikinci kez oldu ve `KraL-OnarimZinciri-28Agu` tasinacak UC blogun kapanisli oldugunu
TEK TEK ELLE dogrulamak zorunda kaldi — yani veto ARACTA degil, INSANIN DIKKATINDEYDI.
SINIF: K313g'nin kardesi. K313g "isi BITMIS ama Okan HENUZ ARSIVLEMEMIS" blogu korur; K329
"isi HENUZ BITMEMIS" blogu korur. Ikisi AYRI eksendir ve AYRI SAYILARLA basilir — tek kovaya
konursa ucuncu hal yutulur ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
CARE: basliginda `BASLIYORUM` gecen bir blok, ESLESEN KAPANISI kutuda YOKSA rotasyona GIRMEZ.
ESLESTIRME EKSENI = CIP ADI, blok siniri DEGIL (olculdu: ayni cipin `BASLIYORUM` ve kapanis
bloklari kutuda AYRI YERLERDE durur — `MaCiT-MarinMwEkleD1-28Agu` kapanisi 100. satirda,
`BASLIYORUM`u 125. satirdaydi). Ad, BASLIK satirindaki ILK backtick'li `<Ev>-<Is>` jetonudur.
Bir blok su iki yoldan BIRIYLE o cipin KAPANISI sayilir: basliginda `SAYILI KAPANIS` gecer,
YA DA blogun KAPANIS KONUMUNDA kapanis jetonu (BEKLEYEN ya da ISLENMIS) vardir.
YANLIS ESLESME KAPALIDIR: eslesme ADIN BIREBIR ESITLIGIDIR — bir blogun basliginda cipin adi
GECMESI onu o cipin kapanisi YAPMAZ (olculdu: `## … 🔍 MaCiT bagimsiz dogrulama: <ad> cip-raporu
DOGRULANDI` blogu adi tasir ama kapanis DEGILDIR).
KONUM OLCUTU (K318 KOL-1'in kardesi): `BASLIYORUM` yalniz BASLIK satirinda sayilir. Govdedeki
anma (bu kurali TARTISAN raporlar, kapanis sayan olcum bloklari — canli kutuda bugun IKI TANE
vardi) veto URETMEZ; sayilir ve `basliyorum_govde_anmasi=` diye BASILIR.
FAIL-CLOSED: basliginda `BASLIYORUM` gecen ama CIP ADI CIKARILAMAYAN blok da KORUNUR
(`sinif=ACIK_ADSIZ`) — "bilmiyorsam tasimam".
SESSIZ ATLAMA YASAK: atlanan her blok CIP ADIYLA basilir (`ACIK_BASLIYORUM_ADLARI=`), 0 ile n
AYNI SATIRDAN okunur. Kutu tavan ustunde kalirsa sebebi GORUNUR.
KILITLENME YOK (kabul ③): kapanisi OLAN `BASLIYORUM` blogu YINE TASINIR ve korumali blok
K318 KOL-2 uyarinca YERINDE ATLANIR — veto kuyrugu rehin ALMAZ.
KAPANISIN SAHIBI (K359-B, 2 Eyl 2026): eslesme ADIN BIREBIR ESITLIGI oldugu icin "bu kapanis
KIMIN" sorusu kritiktir. Ad once DAR (backtick'li) okunur; DAR cikarim BOS donerse GEVSEK ad
ancak blok O ADLA IMZALIYSA (`— <ad>` satir-basi imzasi) kabul edilir. ANMAK ile SAHIPLENMEK
ayri sinifdir; imza sarti gevsetmenin SERBEST BIRAKMA yonune akmasini kapatir.

🔴 SIRA DEGISMEZLIGI ARTIK YOK — ESKI IDDIA YANLIS CIKTI (2 Eyl 2026, canli olcum). Eski metin
"kutu YENI->ESKI siralidir, kapanis daima `BASLIYORUM`un USTUNDE durur, rotasyon DIPTEN sectigi
icin 'kapanis arsivde, `BASLIYORUM` kutuda kilitli' hali DOGAMAZ" diyordu. Kutuda tam o hal
olculdu (kutu :107 acilis KILITLI, arsiv :59559 kapanis TASINMIS): (a) K318 KOL-2 uyarinca
rotasyon SABIT blogu YERINDE ATLAYIP onun USTUNDEKI (daha YENI) bloklara devam eder — yani
acilisi atlarken KAPANISINI tasiyabilir; (b) su seviyesi ciftin ORTASINDAN gecebilir. Bu yuzden
degismezlik ARTIK BIR VARSAYIM DEGIL, ZORLANAN BIR KURALDIR: CIFT BUTUNLUGU kolu, acilisi
kutuda KALACAK bir KAPANISI rotasyona ALMAZ (`CIFT_KORUMASI=` ile ADIYLA basilir) ve denetim
kolu (D18) bir sizinti olursa KIRMIZI yakar. Cip kapanis YAZMADAN olurse blok kalir — ZATEN
ISTENEN budur.

YAZMA SIRASI — NEDEN ONCE ARSIV: iki ayri dosya tek islemde atomik yazilamaz. Once ARSIV
(ekleme), sonra KUTU (kisaltma) yazilir. Ikisinin arasinda cokme olursa sonuc MUKERRER
icerik olur (arsivde var, kutuda da duruyor) — geri alinabilir. Ters sirada sonuc KAYIP
olurdu. Fail-toward-duplication, asla fail-toward-loss.

SENTETIK ARIZA ENJEKSIYONU (yalniz nobetci icin): PRUVO_KUTU_ARSIVLE_ARIZA ortam
degiskeni set edilmediginde HICBIR ETKISI YOKTUR. Set edildiginde aday metinler
dogrulamadan ONCE kasten bozulur; kabul testi boylece "lossless dogrulamasi GERCEKTEN
kirmizi yakiyor mu" sorusunu OLCEBILIR (dogrulamayi silen mutant KIRMIZI yanar).
Degerler: arsiv-satir-dus | kutu-satir-dus | arsiv-onek-boz | arsiv-sira-boz |
          koruma-jeton-sizdir | kutu-blok-dus | basliyorum-sizdir |
          cift-bolunmesi-sizdir |
          cevrim-satir-dus | cevrim-govde-cevir | cevrim-icerik-boz

Kullanim:
    python3 tools/kutu-arsivle.py --kuru
    python3 tools/kutu-arsivle.py
    python3 tools/kutu-arsivle.py --tavan 300 --koru 3
    python3 tools/kutu-arsivle.py --kutu /yol/kutu.md --arsiv /yol/arsiv.md
    python3 tools/kutu-arsivle.py --kapanislari-isle --kuru   # once GOR
    python3 tools/kutu-arsivle.py --kapanislari-isle          # sonra UYGULA
"""
import argparse
import fcntl
import os
import re
import sys
import tempfile

# 🔴 TAVAN OKAN'IN HEDEFININ ALTINDA KALIR (K353, 29 Agu 2026 — olculdu).
# ESKI DEGER 300'DU ve Okan'in emrettigi hedef 250'ydi. Ikisi arasindaki BANT
# aracin KOR ALANIYDI: kutu 298 satirken `--kapanislari-isle` kosuldu ve arac
# `HUKUM=TAVAN_ALTINDA rc=0 once_satir=298 tavan=300 tasinacak_blok=0` dedi —
# yani EMREDILDIGI HALDE INERT kaldi, cunku kendi tavani emrin hedefinin
# USTUNDEYDI. Kutu 250-300 bandinda hedefi asmis ama arac icin "temiz"di.
# SINIF: [[onarim-kolu-zarar-esiginin-arkasinda]] — CEZA esigi ile ONARIM esigi
# ayni/yanlis sirada olunca yordamin emrettigi komut sessizce hicbir sey yapmaz.
# CARE: tavan = emrin hedefi (250); su seviyesi ONDAN TURETILIR ve DAIMA ALTINDA
# kalir (asagidaki SU_SEVIYESI_ORANI). Iki esik AYRI kalir: tavan CEZA noktasi
# (kapi burada kirmizi yakar), su seviyesi ONARIM hedefi (rotasyon buraya iner).
# Ikisi esitlenirse rotasyon tavanda durur, bir sonraki blok yeniden asar ve
# kilit geri gelir — bedeli 29 Agu'da olculdu.
VARSAYILAN_TAVAN = 250
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
                   "D15", "D16", "D17")

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


# ------------------------------------------------------- K341 CEVRIM KOLU (--kapanislari-isle)
# 🔴 NEDEN VAR (Okan, 28 Agu 2026, baglayici): "16 kapanis blogunun 15'i ARSIVLENEBILIRIM
# satiri tasiyor, HEPSI arsive iner" — yani bekleyen kapanislar ISLENMIS SAYILIR. K313g
# korumasi bu bloklari dogru sekilde kilitliyordu; kilidi acan CEVRIM ise ARACTA YOKTU ve
# elle yapiliyordu. ELLE YAPILAN CEVRIM ERTESI GUN GERI GELIR: kutu her gun bekleyen
# kapanislarla dolar, her gun bir mimar elle 13 satir duzenler, ve o duzenleme kutuya
# `Write`/`Edit` ile dokunmaktir — yani [[ortak-kutu-silinebilir-kurtarma-disiplini]]
# kaza sinifinin ta kendisini her gun tekrar acar. Cevrim ARACIN ICINDE olmali, kilit
# altinda, DOGRULAMALI ve fail-closed.
#
# NE YAPAR: KAPANIS KONUMUNDAKI `BEKLEYEN_JETON` -> `ISLENMIS_JETON`. Baska HICBIR SEY.
# NE YAPMAZ (uc dokunulmazlik, ucu de ayri iddiayla olculur):
#   * GOVDE ANMASI — jeton blogun icinde geciyor ama kapanis konumunda degilse
#     DOKUNULMAZ (K318 KOL-1 ile AYNI olcut, AYNI fonksiyondan: korumali_bloklar()).
#   * FAIL_CLOSED — blok yapisi ayristirilamadiysa (kapanmamis cit, icerik satiri yok)
#     DOKUNULMAZ. "Bilmiyorsam tasimam"in kardesi: bilmiyorsam CEVIRMEM.
#   * KAPANIS SATIRININ GERI KALANI — satirda jeton disinda tek bayt degismez.
#
# TEK KAYNAK: cevrilecek satirlar `korumali_bloklar()`den TURER; ikinci bir "bu blok
# bekliyor mu" testi yazilmaz ([[ikiz-tanim-sessiz-ayrisma]]). Cevrim kolu olurse
# bloklar KORUMALI kalir ve rotasyona ACILMAZ -> kabul testi KIRMIZI yanar.
def cevrilecek_kapanislar(satirlar, baslar):
    """([(blok_idx, satir_idx0, eski_satir)], atlanan_fail_closed, govde_anmasi).

    Yalnizca sinif=="KAPANIS" cevrilir. sinif=="FAIL_CLOSED" ATLANIR ve SAYILIR —
    sessizce yutulmaz, cikitida ADIYLA basilir.
    """
    bulgu, govde_anmasi = korumali_bloklar(satirlar, baslar)
    cikti = []
    atlanan = []
    for blok_idx, satir_no, ozet, sinif in bulgu:
        if sinif != "KAPANIS":
            atlanan.append((blok_idx, satir_no, ozet, sinif))
            continue
        cikti.append((blok_idx, satir_no - 1, satirlar[satir_no - 1]))
    return cikti, atlanan, govde_anmasi


def cevir(kutu_metin):
    """(yeni_metin, cevrilen, atlanan, govde_anmasi, hata).

    `cevrilen` = [(blok_idx, satir_idx0, eski_satir, yeni_satir)].
    Hata dolu donerse cagiran HICBIR SEY YAZMAZ.
    """
    satirlar = kutu_metin.splitlines(keepends=True)
    fm_son, hata = frontmatter_sonu(satirlar)
    if hata:
        return None, [], [], 0, hata
    baslar = blok_baslari(satirlar, fm_son)
    if not baslar:
        return kutu_metin, [], [], 0, None
    adaylar, atlanan, govde_anmasi = cevrilecek_kapanislar(satirlar, baslar)
    yeni = list(satirlar)
    cevrilen = []
    for blok_idx, idx, eski in adaylar:
        yeni_satir = eski.replace(BEKLEYEN_JETON, ISLENMIS_JETON)
        yeni[idx] = yeni_satir
        cevrilen.append((blok_idx, idx, eski, yeni_satir))
    return "".join(yeni), cevrilen, atlanan, govde_anmasi, None


def cevrim_ariza_uygula(yeni_metin, cevrilen):
    """SENTETIK ARIZA — yalniz PRUVO_KUTU_ARSIVLE_ARIZA set ise (cevrim kolu icin).

    `ariza_uygula()`nin kardesi: enjekte edilen her ariza sinifini `dogrula_cevrim()`
    YAKALAMAK ZORUNDADIR. Dogrulama silinirse bu arizalar SESSIZCE diske yazilir ->
    kabul testi KIRMIZI yanar.
    """
    ariza = os.environ.get("PRUVO_KUTU_ARSIVLE_ARIZA", "").strip()
    if not ariza or not ariza.startswith("cevrim-"):
        return yeni_metin, None
    s = yeni_metin.splitlines(keepends=True)
    if ariza == "cevrim-satir-dus":
        # CEVRIM sirasinda bir satir ucuruldu = KAYIP (C1/C2 yakalamali).
        return "".join(s[:-1]), None
    if ariza == "cevrim-govde-cevir":
        # GOVDE ANMASI da cevrildi = DOKUNULMAZLIK ihlali (C2 yakalamali).
        j = 0
        while j < len(s):
            if BEKLEYEN_JETON in s[j]:
                s[j] = s[j].replace(BEKLEYEN_JETON, ISLENMIS_JETON)
                return "".join(s), None
            j += 1
        return "".join(s), "ARIZA UYGULANAMADI: cevrilecek govde anmasi YOK"
    if ariza == "cevrim-icerik-boz":
        # Cevrimle ILGISIZ bir satir degisti (C2 yakalamali).
        j = 0
        while j < len(s):
            if s[j].strip() and BEKLEYEN_JETON not in s[j] and ISLENMIS_JETON not in s[j]:
                s[j] = "BOZULDU " + s[j]
                return "".join(s), None
            j += 1
        return "".join(s), "ARIZA UYGULANAMADI: bozulacak notr satir YOK"
    return yeni_metin, "BILINMEYEN cevrim ariza kodu: %s" % ariza


# `dogrula_cevrim()`in BASTIGI iddia eksenleri — `iddia=N` BURADAN turer, elle yazilmaz.
CEVRIM_IDDIA_EKSENLERI = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")


def dogrula_cevrim(eski_metin, yeni_metin, cevrilen, atlanan):
    """KAYIPSIZLIK + DOKUNULMAZLIK iddialari. Bos liste = GECTI, dolu = HICBIR SEY YAZMA.

    🔴 CEVRIM KOLUNUN OMURGASI. Silinirse arac "kutuya sessizce dokunan" bir duzenleyiciye
    doner — tam da kacinilmak istenen sey ([[ortak-kutu-silinebilir-kurtarma-disiplini]]).
    """
    h = []
    e = eski_metin.splitlines(keepends=True)
    y = yeni_metin.splitlines(keepends=True)
    cevrilen_idx = {}
    for _bi, idx, eskisi, yenisi in cevrilen:
        cevrilen_idx[idx] = (eskisi, yenisi)

    # C1 — SATIR SAYISI DEGISMEZ. Cevrim yerinde bir DIZGE ikamesidir, satir eklemez/siler.
    if len(e) != len(y):
        h.append("C1 SATIR SAYISI DEGISTI: once=%d sonra=%d (cevrim satir ekleyemez/silemez)"
                 % (len(e), len(y)))
        return h  # hizalama bozuk -> C2 anlamsiz olur
    # C2 — DOKUNULMAZLIK: cevrilen satirlar DISINDA her satir BIREBIR ayni.
    ihlal = []
    j = 0
    while j < len(e):
        if j not in cevrilen_idx and e[j] != y[j]:
            ihlal.append((j + 1, e[j].strip()[:60], y[j].strip()[:60]))
        j += 1
    if ihlal:
        h.append("C2 CEVRIM DISI SATIR DEGISTI (%d adet, ilk: satir %d %r -> %r) — "
                 "cevrim YALNIZ kapanis satirina dokunur"
                 % (len(ihlal), ihlal[0][0], ihlal[0][1], ihlal[0][2]))
    # C3 — CEVRILEN SATIR YALNIZ JETONDA degisti (satirin geri kalani birebir).
    for _bi, idx, eskisi, yenisi in cevrilen:
        if idx >= len(y):
            h.append("C3 cevrilen satir indeksi TASTI: %d" % idx)
            continue
        if y[idx] != yenisi:
            h.append("C3 cevrilen satir diskteki adayla UYUSMUYOR (satir %d)" % (idx + 1))
        if eskisi.replace(BEKLEYEN_JETON, ISLENMIS_JETON) != yenisi:
            h.append("C3 cevrim JETON IKAMESINDEN FAZLASINI yapti (satir %d): %r -> %r"
                     % (idx + 1, eskisi.strip()[:60], yenisi.strip()[:60]))
        if BEKLEYEN_JETON in yenisi:
            h.append("C3 cevrilen satirda BEKLEYEN jeton HALA duruyor (satir %d)" % (idx + 1))
        if ISLENMIS_JETON not in yenisi:
            h.append("C3 cevrilen satirda ISLENMIS jeton YOK (satir %d)" % (idx + 1))
    # C4 — BAYT ARITMETIGI TURETILIR: delta, satir bazindaki ikamelerin toplamina ESIT.
    bek_delta = 0
    for _bi, _idx, eskisi, yenisi in cevrilen:
        bek_delta += len(yenisi.encode("utf-8")) - len(eskisi.encode("utf-8"))
    ger_delta = len(yeni_metin.encode("utf-8")) - len(eski_metin.encode("utf-8"))
    if bek_delta != ger_delta:
        h.append("C4 BAYT DELTASI TUTMADI: beklenen=%d gercek=%d (cevrim disi bayt degisti)"
                 % (bek_delta, ger_delta))
    # C5 — BLOK YAPISI DEGISMEZ: blok sayisi ve BASLIK satirlari birebir.
    if blok_sayisi(eski_metin) != blok_sayisi(yeni_metin):
        h.append("C5 BLOK SAYISI DEGISTI: once=%d sonra=%d"
                 % (blok_sayisi(eski_metin), blok_sayisi(yeni_metin)))
    eb = [x for x in e if BLOK_RE.match(x)]
    yb = [x for x in y if BLOK_RE.match(x)]
    if eb != yb:
        h.append("C5 BASLIK SATIRLARI DEGISTI (cevrim baslik satirina dokunamaz)")
    # C6 — KOL GERCEKTEN ISLEDI: cevrilen bloklar artik KORUMALI DEGIL.
    #      Bu iddia cevrimin AMACINI olcer: "kilit acildi mi". Kol olurse burasi ates alir.
    y_fm, y_hata = frontmatter_sonu(y)
    if y_hata:
        h.append("C6 cevrilmis metnin frontmatter'i AYRISTIRILAMADI: %s" % y_hata)
    else:
        y_baslar = blok_baslari(y, y_fm)
        y_korumali, _y_govde = korumali_bloklar(y, y_baslar)
        hala = set(bi for bi, _sn, _oz, sinif in y_korumali if sinif == "KAPANIS")
        cevrilen_bloklar = set(bi for bi, _i, _e, _y in cevrilen)
        kesisim = hala & cevrilen_bloklar
        if kesisim:
            h.append("C6 CEVRILEN BLOK HALA KORUMALI (rotasyona ACILMADI): blok %s"
                     % ",".join(str(x + 1) for x in sorted(kesisim)))
    # C7 — BEKLEYEN JETON SAYISI tam olarak cevrilen kadar DUSTU (ne fazla ne eksik).
    dusen = 0
    for _bi, _idx, eskisi, yenisi in cevrilen:
        dusen += eskisi.count(BEKLEYEN_JETON) - yenisi.count(BEKLEYEN_JETON)
    if eski_metin.count(BEKLEYEN_JETON) - yeni_metin.count(BEKLEYEN_JETON) != dusen:
        h.append("C7 BEKLEYEN JETON SAYISI beklenenden FARKLI dustu: once=%d sonra=%d "
                 "beklenen_dusus=%d"
                 % (eski_metin.count(BEKLEYEN_JETON), yeni_metin.count(BEKLEYEN_JETON),
                    dusen))
    # C8 — YAPISAL BUTUNLUK GERILEMEDI: oksuz govde sayisi ARTMADI (K310 ekseni).
    if len(oksuz_govdeler(yeni_metin)) > len(oksuz_govdeler(eski_metin)):
        h.append("C8 OKSUZ GOVDE SAYISI ARTTI: once=%d sonra=%d"
                 % (len(oksuz_govdeler(eski_metin)), len(oksuz_govdeler(yeni_metin))))
    # ATLANAN, iddia URETMEZ ama SAYILIR — cagiran onu ADIYLA basar (sessiz atlama yasak).
    del atlanan
    return h


# ---------------------------------------------------------------- K329 ACIK CIP KOLU
# 🔴 KAPANISSIZ `BASLIYORUM` = ACIK CIP. Gerekce ve olculen vaka: modul basligindaki
# "ACIK CIP" blogu. Bu bolum o kolun TEK KAYNAGIDIR; ikinci bir "acik mi" testi
# HICBIR YERDE yazilmaz ([[ikiz-tanim-sessiz-ayrisma]]).
BASLIYORUM_JETON = "BASLIYORUM"
KAPANIS_BASLIK_JETON = "SAYILI KAPANIS"

# Kutu Turkce yazilir ve AYNI jeton hem Turkce hem ASCII sarmalda gecer (canli olcum:
# `BAŞLIYORUM` ve `BASLIYORUM`, `SAYILI KAPANIŞ` ve `SAYILI KAPANIS` ayni gun ayni
# kutuda). Dar bir desen sarmallarin bir kismini kacirir ve tam da onarmaya calistigimiz
# kaybi uretir -> karsilastirma DAIMA sadelestirilmis metin uzerinde yapilir.
_TR_SADE = str.maketrans({
    "Ç": "C", "ç": "C", "Ğ": "G", "ğ": "G", "İ": "I", "ı": "I",
    "Ö": "O", "ö": "O", "Ş": "S", "ş": "S", "Ü": "U", "ü": "U",
})

# CIP ADI = baslik satirindaki ILK backtick'li `<Ev>-<Is>` jetonu. Ayirt edici sart
# ADIN SEKLIDIR: tire ICERIR, bosluk/egik-cizgi/nokta ICERMEZ. Boylece ayni baslikta
# gecen dosya yollari (`tools/kutu-arsivle.py`), commit sha'lari (`e59c0bcc`) ve
# vurgu isaretleri ad SANILMAZ. Ad CIKARILAMAZSA blok KORUNUR (fail-closed).
CIP_ADI_RE = re.compile(r"`([^`\n]+)`")
_AD_YASAK = (" ", "\t", "/", ".", ",", "*", "(", ")", ":", "`")

# 🔴 GEVSEK AD — YALNIZ ACIK BLOGU ADLANDIRMAK ICIN (28 Agu, ucuncu canli vaka).
# Olculen: uc gercek vakadan BIRI adini backtick'siz yazmisti
# (`## 2026-08-28 — KraL-K333-SabahPATH-28Agu · **BASLIYORUM**`, arsiv :53553). Dar
# cikarim onu `ACIK_ADSIZ` sayardi — blok yine KORUNURDU (fail-closed dogru calisir)
# ama "atladigini ADIYLA bas" sarti yalnizca baslik ozetiyle karsilanirdi ve blok
# kapanisi gelse bile ACILAMAZDI.
# 🔴 ASIMETRI KASITLIDIR VE TEK YONLUDUR: gevsek cikarim YALNIZ `BASLIYORUM` blogunu
# adlandirirken kullanilir; KAPANAN cip adlari DAIMA DAR (backtick'li) cikarimla
# toplanir. Boylece gevsetmenin uretebilecegi tek hata "yanlis ada bakip blogu
# KORUMAK"tir — belirsizlik daima KORUMA yonune duser, ASLA serbest birakma yonune.
# Sekil sarti: en az IKI tire + en az bir BUYUK harf + en az bir RAKAM. `2026-08-28`
# (buyuk harf yok) ve `cip-raporu` (rakam yok) bu suzgecten GECMEZ.
GEVSEK_AD_RE = re.compile(r"(?<![`\w-])([A-Za-z][\w]*-[\w]+-[\w-]+)(?![\w-])")


def sadelestir(metin):
    """Turkce harfleri ASCII'ye katlar + BUYUK HARFE cevirir (jeton karsilastirmasi icin)."""
    return metin.translate(_TR_SADE).upper()


def cip_adi(baslik):
    """Baslik satirindaki ILK backtick'li CIP ADI jetonu, yoksa None (DAR cikarim).

    KARAR EKSENI BUDUR: hem `kapanan_cipler()` hem acik blogun eslestirmesi bu adi
    okur. Backtick sarti bilerek DARDIR — ayni baslikta gecen dosya yollari
    (`tools/kutu-arsivle.py`), commit sha'lari (`e59c0bcc`) ad SANILMAZ.
    """
    for aday in CIP_ADI_RE.findall(baslik):
        ad = aday.strip()
        if len(ad) < 5 or "-" not in ad:
            continue
        if any(k in ad for k in _AD_YASAK):
            continue
        return ad
    return None


def gevsek_cip_adi(baslik):
    """Backtick'siz yazilmis CIP ADI adayi, yoksa None. Bkz. GEVSEK_AD_RE asimetrisi.

    🔴 Bu ad KAPANAN kumesine ASLA girmez; yalnizca ACIK blogu adlandirir.
    """
    for aday in GEVSEK_AD_RE.findall(baslik):
        ad = aday.strip()
        if ad.count("-") < 2 or len(ad) < 8:
            continue
        if not any(k.isupper() for k in ad) or not any(k.isdigit() for k in ad):
            continue
        return ad
    return None


# ------------------------------------------------------- K359 ROL OLCUTU (1 Eyl 2026)
# 🔴 OLCULEN VAKA (canli kutu, 1 Eyl, blok 15): bir KAPANIS blogunun basligi meshguliyet
# olcumunu ANLATIRKEN `"MaCiT-* başlıyorum" notu yok` cumlesini tasiyordu. ALT-DIZGE
# olcutu o ALINTIYI marker sandi ve KAPANISIN KENDISI "acik cip" sayilip kutuda
# SONSUZA KADAR kilitlendi (kapanis blogu asla rotasyona giremez).
# ONARIM: jeton ROL olarak aranir — TIRNAK ICINDEKI gecis ALINTIDIR, marker DEGILDIR.
# 🔴 DARLIK SARTI (K329'u OLDURMEMEK icin): "marker olmak icin kalin sarmal ya da 🚧
# SART" demek GERCEK acik cipleri SERBEST BIRAKIRDI — v36'nin ① sarmali (arsiv :52842)
# GERCEK bir vakadir ve duz `BASLIYORUM` yazar. Bu yuzden kalin sarmal / 🚧 rolu
# TARTISMASIZ KILAR (tirnak elemesi onlari iptal EDEMEZ), ama YOKLUKLARI marker'i
# gecersiz KILMAZ: tirnak DISINDA gecen jeton ROLDUR. Yani bu olcut ESKI davranisin
# ALT KUMESIDIR ve yalnizca "SADECE tirnak icinde gecen" hali eler.
BASLIYORUM_KALIN = "**" + BASLIYORUM_JETON
BASLIYORUM_ISARETI = "🚧"
_TIRNAK_RE = re.compile("\"[^\"\n]*\"|“[^”\n]*”")


def tirnak_disi(metin):
    """KAPANMIS tirnak ciftlerini metinden cikarir (ROL olcutu icin).

    Yalniz KAPANMIS cift silinir; tek/acik tirnak OLDUGU GIBI kalir -> belirsizlik
    yine KORUMA yonundedir (jeton yerinde kalir, blok ACIK sayilir).
    """
    return _TIRNAK_RE.sub(" ", metin)


def basliyorum_rolu(metin):
    """`BASLIYORUM` jetonu bu metinde MARKER ROLUNDE mi geciyor? (K359)"""
    sade = sadelestir(metin)
    if BASLIYORUM_JETON not in sade:
        return False
    if BASLIYORUM_KALIN in sade or BASLIYORUM_ISARETI in metin:
        return True
    return BASLIYORUM_JETON in sadelestir(tirnak_disi(metin))


# --------------------------------------------- K360-C KONUM OLCUTU (4 Eyl 2026)
# 🔴 OLCULEN VAKA (canli kutu, 4 Eyl, blok 16): MaCiT'in 13. cron DUZELTME blogu
# TUM raporunu TEK `## ` BASLIK SATIRINA yaziyor (953 karakter). O anlatinin
# icinde, 632. karakterde, PROZA olarak `BAŞLIYORUM` gecer:
#   "... dilim-19 chip mailbox'a BAŞLIYORUM notu düşürmemiş (disiplin ihlali) ..."
# Blogun basliginda ne 🚧 ne `**BASLIYORUM` vardir ve gecis TIRNAK DISINDADIR ->
# K359'un ROL olcutu onu MARKER sandi. Ardindan `cip_adi()` ayni dev satirdaki ILK
# backtick'li tireli jetonu ad diye topladi: `non-fast-forward` — bir git HATA
# DIZGESI. Sonuc: cip OLMAYAN bir blok, cip OLMAYAN bir adla "acik cip" sayildi.
# 🔴 SINIF: K359 jetonun ROLUNU sorar (alinti mi?), bu kol KONUMUNU sorar (bildirim
# mi, anlati mi?). Ikisi AYRI eksendir; biri otekini TUKETMEZ.
# 🔴 GENISLETME TUZAGI VE DARLIK SARTI: "marker olmak icin 🚧 ya da kalin sarmal
# SART" demek K329'u oldururdu — v36'nin ① sarmali (arsiv :52842) ve 27 Agu'nun
# `## 2026-08-27 — BASLIYORUM · cip `KraL-NobetTuru-27Agu`` blogu GERCEK vakalardir
# ve duz `BASLIYORUM` yazarlar. Bu yuzden 🚧/kalin sarmal olcutu TARTISMASIZ KILAR
# (KONUM elemesi onlari iptal EDEMEZ); YOKLUKLARINDA jeton BASLIGIN BAS KISMINDA
# olmalidir.
# 🔴 TAVAN NEREDEN GELDI (tahmin degil, olcum): canli kutu + arsivin TAMAMI taranarak
# `basliyorum_rolu` TRUE donen 272 baslik cikarildi; 145'i 🚧/kalin tasiyor (bu kolun
# MENZILI DISI), 127'si sade. Sade kumede GERCEK cip acilis bildirimlerinin EN BUYUK
# jeton konumu **76**'dir; 200'un USTUNDEKI her gecis (238, 501, 632, 635, 705, 728,
# 784, 1232) dev cron raporlarinin ICINDEKI ANLATIDIR. Tavan bu BOSLUGA konur:
# gercek en-buyugun 2.6 KATI, kutudaki yanlis pozitifin (632) 3.2 KATI ALTINDA.
# Belirsizlik yine KORUMA yonundedir — tavanin ALTI marker SAYILIR.
KONUM_TAVANI = 200


def basliyorum_baslikta(baslik):
    """BASLIK SATIRI bir cip ACILIS BILDIRIMI mi? (K359 ROL + K360-C KONUM)

    🔴 YALNIZ BASLIK icindir. Govde metni icin `basliyorum_rolu()` kullanilir:
    orada "konum" diye bir sey yoktur ve o kol zaten veto URETMEZ (`govde_anmasi`).
    """
    if not basliyorum_rolu(baslik):
        return False
    sade = sadelestir(baslik)
    if BASLIYORUM_KALIN in sade or BASLIYORUM_ISARETI in baslik:
        return True                      # 🚧 / kalin sarmal TARTISMASIZ KILAR
    return sade.find(BASLIYORUM_JETON) <= KONUM_TAVANI


# --------------------------------------------- K359 UCUNCU KAPANIS KOLU (1 Eyl 2026)
# 🔴 OLCULEN VAKA: MaCiT cron'u kapanisini `## … — ✅ MaCiT 11. cron `macit-parti-surucusu`
# **KAPANDI (delta=0, gate-only) …**` diye yaziyor — sayili, GERCEK bir kapanis; ama ne
# `SAYILI KAPANIS` basligi ne de kapanis JETONU var. Arac gormedigi icin o adin DOKUZ
# `BASLIYORUM` blogu kutuda kilitli kaldi.
# 🔴 GENISLETME TUZAGI: CIPLAK `KAPANDI` kapanis SAYILMAZ. K329'un varlik sebebi "is
# bitmeden `BASLIYORUM` blogunun arsive kacmasi"ni onlemekti; kolu gevsetmek tam da o
# nobetciyi oldurur. UC SART BIRDEN aranir, biri bile eksikse kapanis DEGILDIR:
#   ① kapanis DURUM isareti (`✅`)  ② `KAPANDI` sozu (TIRNAK DISINDA)  ③ CIP ADI (DAR).
KAPANIS_DURUM_ISARETI = "✅"
KAPANIS_SOZU = "KAPANDI"


def kapanis_baslik_ucbirlik(baslik):
    """UC SART BIRDEN saglaniyorsa baslik bir CIP KAPANISIDIR (K359). Yoksa HAYIR."""
    if KAPANIS_DURUM_ISARETI not in baslik:
        return False
    if KAPANIS_SOZU not in sadelestir(tirnak_disi(baslik)):
        return False
    return cip_adi(baslik) is not None


def blok_kapanis_mi(satirlar, bas, son):
    """(kapanis_mi, hata) — blok bir CIP KAPANISI mi?

    UC YOLDAN BIRI YETER (canli kutuda UCU DE gecmektedir):
      * BASLIK satirinda `SAYILI KAPANIS` geciyor,
      * BASLIK satiri UC SARTI BIRDEN tasiyor (`✅` + `KAPANDI` + CIP ADI) — K359;
        biri bile eksikse bu kol SUSAR (bkz. `kapanis_baslik_ucbirlik`),
      * blogun KAPANIS KONUMUNDA kapanis jetonu var — BEKLEYEN **ya da** ISLENMIS.
        Ikisi de "is BITTI" demektir; aralarindaki fark Okan'in ARSIVLEYIP
        arsivlemedigidir ve K329 acisindan ONEMSIZDIR (K313g o ayrimi zaten kendi
        ekseninde tutuyor — burada tekrar edilirse iki kol sessizce ayrisir).
    Kapanis konumu AYRISTIRILAMAZSA hata dondurulur ve blok kapanis SAYILMAZ; yani
    belirsizlik yine KORUMA yonundedir (o cipin `BASLIYORUM`u acik kalir).
    """
    if son <= bas:
        return False, "BOS BLOK ARALIGI (bas=%d son=%d)" % (bas, son)
    if KAPANIS_BASLIK_JETON in sadelestir(satirlar[bas]):
        return True, None
    if kapanis_baslik_ucbirlik(satirlar[bas]):
        return True, None
    idx, hata = kapanis_satiri(satirlar, bas, son)
    if hata is not None:
        return False, hata
    if BEKLEYEN_JETON in satirlar[idx] or ISLENMIS_JETON in satirlar[idx]:
        return True, None
    return False, None


# ------------------------------------- K359-B KUSUR A: KAPANIS ADI (2 Eyl 2026)
# 🔴 OLCULEN VAKA (canli kutu :107 + arsiv :59559, mimar ELIYLE gosterdi): cip
# `KraL-UrunSilmeButonu-2Eyl` kapanisini
#   `## 2026-09-02 — ✅ KraL-UrunSilmeButonu-2Eyl (çip: …) **SAYILI KAPANIŞ — …**`
# diye BACKTICK'SIZ yazdi. `blok_kapanis_mi()` blogu KAPANIS SAYDI (`SAYILI KAPANIS`
# jetonu var) ama `kapanan_cipler()` sahibini DAR cikarimla aradi -> `cip_adi()=None`
# -> ad kumeye HIC GIRMEDI. Ayni cipin `BASLIYORUM` blogu ise GEVSEK cikarimla
# adlandirilmisti (`ACIK_GEVSEK_AD`). Yani ACILIS ile KAPANIS AYRI ALFABEDEN okundu:
# blok, kapanisi kutuda DURURKEN "ESLESEN KAPANIS kutuda YOK" diye kilitlendi.
# 🔴 ASIMETRI KALDIRILMADI, ONAY SARTINA BAGLANDI. Eski gerekce dogruydu: kapanis
# adini gevsetmek "belirsizligi SERBEST BIRAKMA yonune" akitir — adi ANAN her kapanis
# baska bir cipi acardi. Bu yuzden GEVSEK kapanis adi ancak blok O ADLA IMZALIYSA
# (`— <ad>` satir-basi imzasi, kutu geleneginin sahiplik isareti) kabul edilir. ANMAK
# ile IMZALAMAK ayri sinifdir: proza icinde gecen ad, baska cipin kapanisi ve govdede
# anilan ad IMZA URETMEZ -> serbest birakma yonu KAPALI KALIR (4 negatif fikstur).
def _imzada_geciyor(satirlar, bas, son, ad):
    """`ad` blogun IMZA satirlarindan birinde BUTUN JETON olarak geciyor mu?"""
    desen = re.compile(r"(?<![\w-])" + re.escape(ad) + r"(?![\w-])")
    j = bas
    while j < son:
        if IMZA_RE.match(satirlar[j]) and desen.search(satirlar[j]):
            return True
        j += 1
    return False


def kapanis_cip_adi(satirlar, bas, son):
    """KAPANIS blogunun SAHIBI cip adi — DAR once, sonra IMZA ONAYLI GEVSEK.

    🔴 TEK KAYNAK: `kapanan_cipler()` (K329 eslestirmesi) ve `kapanis_bloklari()`
    (K359-B cift butunlugu) AYNI adi okur; ikinci bir "bu kapanis kimin" testi
    HICBIR YERDE yazilmaz ([[ikiz-tanim-sessiz-ayrisma]]).

    🔴 K360-A: bu fonksiyon artik `kapanis_kimlikleri()`nin BIRINCIL adini dondurur —
    kimligin TEK KAYNAGI odur. Ikinci bir cikarim burada YAZILMAZ, yoksa iki kol
    sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]]).
    """
    adlar = kapanis_kimlikleri(satirlar, bas, son)
    return adlar[0] if adlar else None


# ------------------------------------------- K360-A AD EKSENI AYRISMASI (4 Eyl 2026)
# 🔴 OLCULEN VAKA (mimar ELIYLE, IKI GERCEK CIP, IKI TERS YONDE):
#   (1) `KraL-Tamirci-3Eyl` — ACILIS  (kutu :10)  `🚧 KraL-Tamirci-3Eyl (çip: friendly-carson-1440e3)`
#                             -> dar=None, gevsek=`KraL-Tamirci-3Eyl`
#       KAPANIS (arsiv :60464) `✅ KraL-Tamirci-3Eyl (çip `friendly-carson-1440e3`)`
#                             -> dar=`friendly-carson-1440e3`
#   (2) `KraL-TamirciMerge-3Eyl` — ACILIS  (kutu :8) dar=`trusting-khorana-8c616a`
#       KAPANIS (arsiv :61186) -> dar=None, gevsek=`KraL-TamirciMerge-3Eyl`
# Ayni cip, ayni baslikta IKI kimlik tasir: INSAN ADI (`KraL-Tamirci-3Eyl`) ve
# OTURUM/AGAC KIMLIGI (`friendly-carson-1440e3`). Eski kod her yanda TEK ad secip
# durdugu icin acilis bir alfabeden, kapanis OTEKINDEN okundu ve anahtarlar AYRISTI.
# 🔴 CARE: kimlik TEK AD DEGIL, AD KUMESIDIR. Iki yan da URETEBILDIGI TUM adlari verir;
# eslesme KESISIM BOS DEGIL sartidir.
# 🔴 K359-B ASIMETRISI KALDIRILMADI: kapanis tarafinda GEVSEK ad hala IMZA ONAYI ister
# (`— <ad>` satir-basi imzasi). Boylece "adi ANAN her kapanis baska bir cipi acar"
# sinifi KAPALI kalir; ANMAK ile IMZALAMAK ayri sinif olarak durur (negatif fiksturler
# c ve d bunu olcer). Olculdu: bes gercek kapanisin BESI de imza sartini gecer.
def cip_kimlikleri(baslik):
    """ACILIS basliginin URETEBILECEGI TUM cip kimlikleri (sirali, tekil).

    DAR (backtick'li) ad ONCE gelir — birincil kimlik odur; GEVSEK ad ikincidir.
    """
    adlar = []
    dar = cip_adi(baslik)
    if dar:
        adlar.append(dar)
    gevsek = gevsek_cip_adi(baslik)
    if gevsek and gevsek not in adlar:
        adlar.append(gevsek)
    return tuple(adlar)


def kapanis_kimlikleri(satirlar, bas, son):
    """KAPANIS blogunun TUM kimlikleri — DAR serbest, GEVSEK yalniz IMZA ONAYIYLA.

    🔴 TEK KAYNAK: `kapanan_cipler()`, `kapanis_bloklari()` ve K359-B cift butunlugu
    AYNI kimlikleri okur; ikinci bir "bu kapanis kimin" testi HICBIR YERDE yazilmaz
    ([[ikiz-tanim-sessiz-ayrisma]]).
    """
    adlar = []
    dar = cip_adi(satirlar[bas])
    if dar:
        adlar.append(dar)
    gevsek = gevsek_cip_adi(satirlar[bas])
    if (gevsek and gevsek not in adlar
            and _imzada_geciyor(satirlar, bas, son, gevsek)):
        adlar.append(gevsek)
    return tuple(adlar)


def kapanis_bloklari(satirlar, baslar):
    """{blok_idx: (ad, ...)} — KAPANIS olan ve SAHIBI cikarilabilen bloklar (TEK KAYNAK).

    Deger bir KIMLIK DEMETIDIR (K360-A); ilk eleman birincil addir ve basimda o gecer.
    """
    esleme = {}
    araliklar = blok_araliklari(satirlar, baslar)
    i = 0
    while i < len(araliklar):
        bas, son = araliklar[i]
        kapanis, _hata = blok_kapanis_mi(satirlar, bas, son)
        if kapanis:
            adlar = kapanis_kimlikleri(satirlar, bas, son)
            if adlar:
                esleme[i] = adlar
        i += 1
    return esleme


def basliyorum_adlari(satirlar, baslar):
    """{blok_idx: ad} — BASLIYORUM MARKER ROLUNDEKI, adi cikarilabilen bloklar.

    🔴 Blogun ACIK olup olmadigina BAKMAZ. Cift butunlugu (K359-B) "bu ADIN ACILISI
    kutuda KALIYOR mu" diye sorar; "acik mi" AYRI sorudur ve `acik_cip_bloklari()`
    onu ayri eksende cevaplar ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    """
    esleme = {}
    araliklar = blok_araliklari(satirlar, baslar)
    i = 0
    while i < len(araliklar):
        bas, _son = araliklar[i]
        baslik = satirlar[bas]
        if basliyorum_baslikta(baslik):
            adlar = cip_kimlikleri(baslik)
            if adlar:
                esleme[i] = adlar
        i += 1
    return esleme


def kapanan_cipler(satirlar, baslar):
    """Bu METINDE kapanisi bulunan TUM cip kimlikleri (kume).

    🔴 IMZA SABIT: `tools/arsiv-kapisi.py::K4` bu fonksiyonu ISIMLE cagirir ve KUME
    bekler ([[hukum-tuketen-kapi-total-hukum-ister]]). Donen kume K360-A ile GENISLEDI
    (bir kapanis artik hem DAR hem IMZA-ONAYLI GEVSEK adini verir) — bu, kapinin
    "bu cip kapandi mi" sorusunu AYNI kimlik ekseninden cevaplamasi demektir.
    """
    kume = set()
    for adlar in kapanis_bloklari(satirlar, baslar).values():
        kume.update(adlar)
    return kume


# --------------------------------------- K360-B DUZLEM AYRISMASI (4 Eyl 2026)
# 🔴 OLCULEN VAKA (mimar ELIYLE, DORT gercek ad): `ArTisT-KutuEmri-31Agu`,
# `KraL-K359-KutuEslesme`, `KraL-UrunSilmeButonu-2Eyl`, `macit-parti-surucusu` —
# ACILIS kutuda, KAPANIS ARSIVDE. Eslestirme yalniz kutuya baktigi icin bu bloklar
# "kapanisi YOK" sayilip kutuda SONSUZA KADAR kilitlendi. Kutu 250 satir tavaninda
# bir PENCEREdir; kapanislar dogal olarak ondan once arsive akar.
# 🔴 MIMAR HUKMU (KraL, 4 Eyl): care kapanislari arsivden kutuya GERI TASIMAK DEGILDIR
# (kutuyu sisirir, kotayi geri kilitler, sirayi bozar). Kimlik CIFTTIR, duzlem degil:
# kapi "bu cip kapandi mi" sorusunu cevaplarken ARSIVE DE BAKAR.
# 🔴 FAIL-CLOSED: arsiv okunamiyor/bozuksa cip KAPANMAMIS sayilir (blok DURUR).
#    Kayit uretilmez -> hicbir blok serbest kalmaz. Fail-open YASAKTIR.
# 🔴🔴 TEKRAR EDEN AD TEHLIKESI: `macit-parti-surucusu` AYNI ADLA 18 kez acilan bir
# CRON'dur ve arsivde 13 ESKI kapanisi vardir. Naif "arsivde adi geciyorsa kapandi"
# kurali CANLI bir cipin acilisini rotasyona atardi — tam da kacindigimiz kayip.
# Bu yuzden serbest birakma IKI SARTA baglidir:
#   ① ZAMAN SIRALI — arsivdeki kapanis, kutudaki acilistan DAHA ESKI OLAMAZ.
#   ② TUKETIMLI    — bir kapanis kaydi BIR acilisi acar; en YENI acilis en YENI
#                    kapanisi TUKETIR, geriye kalan acilislar kendi kapanislarini
#                    ARAMAK ZORUNDADIR. Olculen sonuc: MaCiT 17. cron (kapanisi
#                    arsivde) SERBEST kalir, 18. cron (kapanisi YOK) KILITLI kalir.
# 🔴 ZAMAN OLCUSU NEREDEN: baslik onekindeki `## YYYY-MM-DD` — kutu geleneginin TEK
# katı biciminde yazdigi alan (canli olcum: kutuda 21/21, arsivde 2849/2888 baslik
# ayristirilir). `~HH:MM` SERBEST yazilir (`~05:0x`, `~07:xZ`, `~06-08:xZ`) ve ancak
# IKI YAN DA tam sayisal yazmissa karsilastirmaya girer; aksi halde GUN ekseninde
# kalinir. Ayni gun + belirsiz saat = "daha eski DEGIL" sayilir (esitlik KORUMA
# yonunde okunur), cokluk tehlikesini TUKETIM kolu kapatir.
# 🔴 MENZIL: bu zaman kapisi YALNIZ ARSIV kaynakli kapanislara uygulanir. Kutu-ici
# eslestirme (K329/K359-B) DEGISMEDI — orasi 250 satirlik dar bir penceredir ve
# davranisi 377 iddiayla civilidir.
TARIH_BASLIK_RE = re.compile(r"^##\s+(\d{4})-(\d{2})-(\d{2})")
SAAT_BASLIK_RE = re.compile(r"^##\s+\d{4}-\d{2}-\d{2}\s*[—\-]?\s*~?\s*(\d{2}):(\d{2})")


def blok_zamani(baslik):
    """(gun, dakika) — gun `YYYYMMDD` tamsayisi, dakika gun-ici dakika ya da None.

    Gun AYRISTIRILAMAZSA (None, None) doner ve o blok ZAMAN SIRASINA GIREMEZ:
    arsiv kolu onu serbest BIRAKMAZ (fail-closed).
    """
    m = TARIH_BASLIK_RE.match(baslik)
    if not m:
        return None, None
    gun = int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
    s = SAAT_BASLIK_RE.match(baslik)
    if not s:
        return gun, None
    saat, dakika = int(s.group(1)), int(s.group(2))
    if saat > 23 or dakika > 59:
        return gun, None
    return gun, saat * 60 + dakika


def _kapanis_daha_eski_degil(acilis_z, kapanis_z):
    """Kapanis, acilistan DAHA ESKI DEGIL mi? Gun ayristirilamazsa DAIMA False."""
    a_gun, a_dk = acilis_z
    k_gun, k_dk = kapanis_z
    if a_gun is None or k_gun is None:
        return False                                  # fail-closed
    if k_gun != a_gun:
        return k_gun > a_gun
    if a_dk is None or k_dk is None:
        return True            # ayni gun, saat BELIRSIZ -> esitlik KORUMA yonunde
    return k_dk >= a_dk


def arsiv_kapanis_kayitlari(arsiv_metin):
    """({ad: [(gun, dakika), ...]}, hata) — ARSIVDEKI kapanislarin kimlik+zamani.

    🔴 FAIL-CLOSED: metin yok/bos/bozuk frontmatter ise ({}, sebep) doner. Bos kayit
    hicbir blogu serbest BIRAKMAZ; yani "arsiv okunamadi" hali "cip KAPANMAMIS"
    hukmune akar ve cagiran sebebi ADIYLA basar (sessiz atlama YASAK).
    """
    if arsiv_metin is None or arsiv_metin == "":
        return {}, "arsiv YOK ya da BOS -> arsiv duzlemi OLCULMEDI (fail-closed)"
    satirlar = arsiv_metin.splitlines(keepends=True)
    fm, hata = frontmatter_sonu(satirlar)
    if hata or fm is None:
        return {}, ("arsiv frontmatter'i BOZUK -> arsiv duzlemi OLCULMEDI "
                    "(fail-closed): %s" % (hata or "?"))
    baslar = blok_baslari(satirlar, fm)
    kayitlar = {}
    for idx, adlar in kapanis_bloklari(satirlar, baslar).items():
        zaman = blok_zamani(satirlar[baslar[idx]])
        for ad in adlar:
            kayitlar.setdefault(ad, []).append(zaman)
    return kayitlar, None


def arsiv_serbest(satirlar, baslar, acik, arsiv_kayitlari):
    """{blok_idx: (ad, kapanis_zamani)} — ARSIVDEKI kapanisla serbest kalan acilislar.

    🔴 TEK KAYNAK: `acik_cip_bloklari()` bununla filtreler, `planla()` bununla RAPOR
    eder. Ikinci bir "arsivde kapandi mi" testi HICBIR YERDE yazilmaz
    ([[ikiz-tanim-sessiz-ayrisma]]).
    """
    if not arsiv_kayitlari:
        return {}
    # Havuz: her ad icin kapanis zamanlari, EN YENI once.
    havuz = {}
    for ad, zamanlar in arsiv_kayitlari.items():
        havuz[ad] = sorted(
            [z for z in zamanlar if z[0] is not None],
            key=lambda z: (z[0], -1 if z[1] is None else z[1]), reverse=True)
    # Adaylar: acilis EN YENI once (zaman), esitlikte kutu sirasi (kucuk indeks = yeni).
    # 🔴 ADAYIN TUM KIMLIKLERI aranir, yalniz BIRINCILI degil. Olculen vaka:
    # `KraL-TamirciMerge-3Eyl` acilisinin BIRINCIL kimligi `trusting-khorana-8c616a`
    # (backtick'li), arsivdeki kapanisi ise GEVSEK adla imzali. Tek ada bakmak K360-A
    # onarimini tam da bu blokta bosa dusururdu.
    adaylar = []
    for (idx, ad, _ozet, _sinif) in acik:
        if not ad:
            continue
        adlar = cip_kimlikleri(satirlar[baslar[idx]])
        if adlar:
            adaylar.append((idx, adlar, blok_zamani(satirlar[baslar[idx]])))
    adaylar.sort(key=lambda t: (t[2][0] if t[2][0] is not None else -1,
                                -1 if t[2][1] is None else t[2][1], -t[0]),
                 reverse=True)
    serbest = {}
    for (idx, adlar, acilis_z) in adaylar:
        bulundu = False
        for ad in adlar:
            liste = havuz.get(ad)
            if not liste:
                continue
            j = 0
            while j < len(liste):
                if _kapanis_daha_eski_degil(acilis_z, liste[j]):
                    # TUKET: bir kapanis kaydi BIR acilisi acar.
                    serbest[idx] = (ad, liste.pop(j))
                    bulundu = True
                    break
                j += 1
            if bulundu:
                break
    return serbest


def acik_cip_bloklari(satirlar, baslar, kapanan=None, arsiv_kayitlari=None):
    """([(blok_idx, ad, ozet, sinif)], kapanmis, govde_anmasi, kapanan) — TEK KAYNAK.

    🔴 ICRA kolu (`planla`) ve DENETIM kolu (`dogrula` D17) BU fonksiyonu cagirir.
    DENETIM kolu `kapanan` kumesini DISARIDAN alir: tasinan metin TEK BASINA
    okundugunda cipin kapanisi (kutuda kalmis olabilecegi icin) GORUNMEZ ve denetim
    ICRADAN AYRISIP masum bir tasimayi kirmiziya yakardi. Karar ANINDAKI kutu, iki
    kol icin de TEK TABANDIR.

    KORUMALI UC sinif:
      "ACIK_BASLIYORUM" — baslikta `BASLIYORUM` MARKER ROLUNDE var (K359: tirnak
                          icindeki gecis ALINTIDIR), cipin kapanisi kutuda YOK.
      "ACIK_GEVSEK_AD"  — ad backtick'siz yazilmis, GEVSEK cikarimla okundu (gercek
                          vaka, arsiv :53553); eslestirme yine yapilir.
      "ACIK_ADSIZ"      — baslikta `BASLIYORUM` var ama CIP ADI hic cikarilamadi.
    SAYILAN ama KORUMASIZ iki hal (GIZLENMEZ, donus degeriyle basilir):
      `kapanmis`      — `BASLIYORUM` blogu, kapanisi VAR -> rotasyona ACIK.
      `govde_anmasi`  — `BASLIYORUM` yalniz GOVDEDE geciyor -> veto URETMEZ.
    """
    araliklar = blok_araliklari(satirlar, baslar)
    if kapanan is None:
        kapanan = kapanan_cipler(satirlar, baslar)
    acik = []
    kapanmis = 0
    govde_anmasi = 0
    i = 0
    while i < len(araliklar):
        bas, son = araliklar[i]
        baslik = satirlar[bas]
        if not basliyorum_baslikta(baslik):
            # KONUM (K360-C) ya da ROL (K359) olcutunden DUSEN baslik, jetonu
            # govdesinde tasiyor olabilir: o hal SAYILIR ama veto URETMEZ.
            if basliyorum_rolu("".join(satirlar[bas:son])):
                govde_anmasi += 1
            i += 1
            continue
        adlar = cip_kimlikleri(baslik)
        if not adlar:
            acik.append((i, None, baslik.strip()[:70], "ACIK_ADSIZ"))
        elif [a for a in adlar if a in kapanan]:
            kapanmis += 1
        else:
            # SINIF, adin HANGI EKSENDEN okundugunu soyler (dar mi, gevsek mi) —
            # sayilar ayri kovalarda kalsin diye.
            sinif = ("ACIK_BASLIYORUM" if cip_adi(baslik)
                     else "ACIK_GEVSEK_AD")
            acik.append((i, adlar[0], baslik.strip()[:70], sinif))
        i += 1

    # 🔴 K360-B DUZLEM KOLU — ARSIVE DE BAKILIR (mimar hukmu, 4 Eyl).
    if arsiv_kayitlari:
        serbest = arsiv_serbest(satirlar, baslar, acik, arsiv_kayitlari)
        if serbest:
            acik = [t for t in acik if t[0] not in serbest]
            kapanmis += len(serbest)
    return acik, kapanmis, govde_anmasi, kapanan


def sabit_indeksler(blok_sayisi_, koru, korumali_indeksler, acik_indeksler=()):
    """ROTASYONA GIRMEYECEK blok indeksleri kumesi — TEK KAYNAK.

    UC kaynaktan TURER, elle kopyalanmaz:
      * `koru` TABANI: en ustteki `koru` blok her zaman dokunulmaz,
      * KORUMA (K313g): bekleyen kapanis jetonu tasiyan blok, NEREDE OLURSA OLSUN,
      * ACIK CIP (K329): kapanissiz `BASLIYORUM` blogu, NEREDE OLURSA OLSUN.
    🔴 K318 KOL-2: hicbiri ALTINDAKI bloklari REHIN ALMAZ — kume bir ARALIK degil,
    ayrik bir KUMEDIR; rotasyon sabit blogu YERINDE ATLAR.
    """
    sabit = set(range(min(koru, blok_sayisi_)))
    sabit.update(korumali_indeksler)
    sabit.update(acik_indeksler)
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
        # ACIK CIP KOLU (K329) — K313g'den AYRI KOVA, AYRI SAYI
        self.acik_cip = []                 # [(blok_idx, ad, ozet, sinif)]
        self.kapanmis_basliyorum = 0       # kapanisi BULUNAN `BASLIYORUM` blogu
        self.basliyorum_govde_anmasi = 0   # `BASLIYORUM` yalniz GOVDEDE geciyor
        self.acik_kilitledi = 0            # `koru` tabaninin ALTINDA kalan acik cip
        self.kapanan_adlar = set()         # denetim kolunun (D17) okudugu TABAN
        # ARSIV DUZLEMI (K360-B) — K329'dan AYRI KOVA, AYRI SAYI
        self.arsiv_serbest = {}            # {blok_idx: (ad, kapanis_zamani)}
        self.arsiv_kayitlari = {}          # denetim kolunun (D17) okudugu ARSIV TABANI
        self.arsiv_hatasi = None           # arsiv OLCULEMEDIYSE sebebi (fail-closed)
        # CIFT BUTUNLUGU (K359-B) — K329'dan AYRI KOVA, AYRI SAYI
        self.cift_korumasi = []            # [(blok_idx, ad, sebep)] — pinlenen KAPANIS


def planla(kutu_metin, tavan, koru, arsiv_kayitlari=None):
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

    # 🔴 ACIK CIP KOLU (K329) — AYRI EKSEN, AYRI SAYI. `koru` tabani ve K313g ile
    # ayni kumeye AKAR ama ayni SAYIYA akmaz: sinif adini kol adi olarak basmak
    # ucuncu hali yutar ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    # 🔴 K360-B: ARSIV DUZLEMI de okunur. `arsiv_serbest` ONCE ayri cagrilir ki
    # serbest kalan bloklar RAPOR EDILEBILSIN — filtreleme ve rapor AYNI
    # fonksiyondan turer, ikinci bir hesap YOKTUR.
    p.arsiv_kayitlari = arsiv_kayitlari or {}
    acik_ham, _kh, _gh, p.kapanan_adlar = acik_cip_bloklari(satirlar, baslar)
    p.arsiv_serbest = arsiv_serbest(satirlar, baslar, acik_ham, arsiv_kayitlari or {})
    (p.acik_cip, p.kapanmis_basliyorum, p.basliyorum_govde_anmasi,
     p.kapanan_adlar) = acik_cip_bloklari(satirlar, baslar,
                                          arsiv_kayitlari=arsiv_kayitlari)
    acik_idx = [b for b, _a, _o, _k in p.acik_cip]
    p.acik_kilitledi = len([b for b in acik_idx if b >= koru])

    p.sabit = sabit_indeksler(len(baslar), koru, korumali_idx, acik_idx)

    # 🔴 CIFT BUTUNLUGU KOLU (K359-B KUSUR B, 2 Eyl 2026) — SECIMDEN ONCE.
    # OLCULEN VAKA: `KraL-UrunSilmeButonu-2Eyl`in ACILISI (kusur A yuzunden) ACIK
    # sayilip YERINDE ATLANDI; rotasyon onun USTUNDEKI bloklara devam edip AYNI CIPIN
    # KAPANISINI arsive tasidi (arsiv :59559). Sonuc: acilis artik HICBIR ZAMAN
    # eslesemez -> kutuda KALICI OLU SLOT. Bu kol o cifti bolunmez kilar.
    # 🔴 IKI SEKILDEN HANGISI SECILDI VE NEDEN: "cifti BIRLIKTE tasi" DEGIL,
    # "acilisi kalan bir KAPANISI TASIMAYI REDDET" secildi. Gerekce: cifti birlikte
    # tasimak, kapanisi TANINMAMIS (yani "hala kosuyor" gorunen) bir cipin
    # `BASLIYORUM` blogunu Okan'in bakacagi yuzeyden kaldirirdi — K329'un VARLIK
    # SEBEBININ ta kendisi. Belirsizlik daima KORUMA yonune duser; maliyeti yalnizca
    # kutunun bir tur DAHA AZ kuculmesidir ve o sayi `cift_korumasi=` ile BASILIR.
    # 🔴 KONUM SARTI DA OLCUTE DAHIL: secim EN BUYUK indeksten (EN ESKIDEN) yukari
    # yurur. Acilisi KAPANISTAN SONRA (daha buyuk indekste) olan bir cift, su
    # seviyesi ARADA kesilirse yine bolunur — bu yuzden "acilis SABIT kumede" sarti
    # TEK BASINA YETMEZ; `o < c` (acilis DAHA YENI konumda) hali de pinlenir.
    p.cift_korumasi = []
    if baslar:
        kapanis_sahipleri = kapanis_bloklari(satirlar, baslar)
        acilis_sahipleri = basliyorum_adlari(satirlar, baslar)
        for c in sorted(kapanis_sahipleri):
            if c in p.sabit:
                continue
            adlar = kapanis_sahipleri[c]
            ad = adlar[0]
            for o in sorted(acilis_sahipleri):
                # 🔴 K360-A: esleme KESISIMDIR, birebir esitlik DEGIL. Cift butunlugu
                # ile K329 eslestirmesi AYNI kimlik ekseninden okumazsa iki kol
                # sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]]).
                ortak = [x for x in acilis_sahipleri[o] if x in adlar]
                if not ortak:
                    continue
                ad = ortak[0]
                if o in p.sabit:
                    sebep = "ACILIS_SABIT"
                elif o < c:
                    sebep = "ACILIS_DAHA_YENI"
                else:
                    continue
                p.cift_korumasi.append((c, ad, sebep))
                break
        p.sabit = p.sabit | set(c for c, _ad, _s in p.cift_korumasi)

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
        # K329: ACIK CIP de bir GORUNURLUK korumasidir; kota kapisi (K318 KOL-3)
        # tam olarak "arac ISI KASITLI OLARAK yapmiyor" halini tuketir ve bu hal
        # odur. Bu yuzden AYNI hukme akar — ama SAYILARI ayri basilir.
        p.koruma_tuttu = (p.korumali_kilitledi + p.acik_kilitledi
                          + len([c for c, _a, _s in p.cift_korumasi
                                 if c >= koru])) > 0
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
        p.yerinde_atlanan = len([b for b in (korumali_idx + acik_idx)
                                 if b > secilenler[0]])
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
    elif ariza == "basliyorum-sizdir":
        # 🔴 K329 DENETIM KOLUNUN OLCU ALETI: planla() dogru calissa bile, tasinan
        # metne KAPANISSIZ bir `BASLIYORUM` blogu SIZARSA D17 bunu YAKALAMAK
        # ZORUNDADIR. D17 silinirse bu ariza sessizce diske yazilir -> kabul testi
        # KIRMIZI yanar. (Baska iddialar da atesler; kabul testi bu yuzden kirmiziyi
        # ADIYLA arar, "kirmizi geldi" ile yetinmez — [[K182]] hedef-kol atfi.)
        blok = ("## 2026-08-28 — 🚀 %s · cip `ZzZ-Sizinti-28Agu`\n"
                "\n"
                "sentetik sizinti govdesi\n"
                "\n" % BASLIYORUM_JETON)
        yeni_arsiv = yeni_arsiv + blok
        ek = ek + blok
    elif ariza == "cift-bolunmesi-sizdir":
        # 🔴 K359-B DENETIM KOLUNUN OLCU ALETI: planla() dogru calissa bile, tasinan
        # metne ACILISI KUTUDA KALAN bir cipin KAPANIS blogu SIZARSA D18 bunu
        # YAKALAMAK ZORUNDADIR. D18 silinirse ariza sessizce diske yazilir, o acilis
        # bir daha ASLA eslesemez ve kutuda KALICI OLU SLOT dogar -> kabul testi
        # KIRMIZI yanar. (Baska iddialar da atesler; kabul testi kirmiziyi ADIYLA
        # arar, "kirmizi geldi" ile yetinmez — [[K182]] hedef-kol atfi.)
        s = yeni_kutu.splitlines(keepends=True)
        kalanlar = basliyorum_adlari(s, blok_baslari(s))
        if not kalanlar:
            return (yeni_kutu, ek, yeni_arsiv,
                    "ARIZA UYGULANAMADI: kutuda ADI CIKARILABILIR `%s` blogu YOK"
                    % BASLIYORUM_JETON)
        kalan_ad = kalanlar[sorted(kalanlar)[0]][0]     # K360-A: kimlik DEMETI
        blok = ("## 2026-08-28 — ✅ sentetik `%s` **KAPANDI (sentetik sizinti)**\n"
                "\n"
                "sentetik cift-bolunmesi govdesi\n"
                "\n" % kalan_ad)
        yeni_arsiv = yeni_arsiv + blok
        ek = ek + blok
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

    # ---------------------------------------------------------------- K329 ekseni
    # 17. 🔴 ACIK CIP — TASINAN METINDE KAPANISSIZ `BASLIYORUM` BLOGU OLAMAZ.
    #     planla() ICRA eder (blogu sabit kumeye koyar), bu iddia DENETLER. Ikisi
    #     AYNI `acik_cip_bloklari()` fonksiyonunu cagirir; `kapanan` kumesi karar
    #     ANINDAKI KUTUDAN gelir (plan.kapanan_adlar) — tasinan metin tek basina
    #     okunsaydi kutuda KALAN kapanislar gorunmez, denetim ICRADAN AYRISIR ve
    #     mesru bir tasimayi kalici kirmiziya cevirirdi ([[ikiz-tanim-sessiz-ayrisma]]).
    # 🔴 K360-B: ARSIV TABANI da KARAR ANINDAN gelir (`plan.arsiv_kayitlari`).
    # Denetim arsivi kendi basina okusaydi (ya da HIC okumasaydi) ICRADAN AYRISIR ve
    # arsivde kapanisi bulunan mesru bir tasimayi kalici kirmiziya cevirirdi — tam
    # olarak `kapanan` kumesinin disaridan verilme gerekcesi ([[ikiz-tanim-sessiz-ayrisma]]).
    ek_acik, _ek_kapanmis, _ek_govde, _ek_adlar = acik_cip_bloklari(
        ek_satir_ke, blok_baslari(ek_satir_ke), kapanan=plan.kapanan_adlar,
        arsiv_kayitlari=plan.arsiv_kayitlari)
    for _bi, ad, ozet, sinif in ek_acik:
        h.append("D17 ACIK CIP IHLALI (%s): tasinan metinde ESLESEN KAPANISI OLMAYAN "
                 "bir `%s` blogu var (cip `%s`) -> cip HALA KOSUYOR olabilir ve "
                 "'su an kim kosuyor' sorusunun cevabi Okan'in bakacagi yuzeyden "
                 "GORUNMEZ olurdu. Fail-closed: hicbir sey yazilmadi. | %s"
                 % (sinif, BASLIYORUM_JETON, ad or "AD_YOK", ozet))

    # ---------------------------------------------------------- K359-B CIFT ekseni
    # 18. 🔴 CIFT BUTUNLUGU — TASINAN METINDE, ACILISI KUTUDA KALAN BIR KAPANIS OLAMAZ.
    #     planla() ICRA eder (kapanisi sabit kumeye koyar), bu iddia DENETLER. Ikisi
    #     AYNI `kapanis_bloklari()`/`basliyorum_adlari()` fonksiyonlarini cagirir.
    #     Kirmizi yanarsa gerileme "sessiz olu slot" degil "gurultulu duraklama"dir:
    #     acilisi kutuda kalan bir kapanis arsive giderse o acilis ARTIK HICBIR ZAMAN
    #     eslesemez ve blok kutuda SONSUZA KADAR kilitli kalir (olculen vaka).
    yk_satir_ke = yeni_kutu.splitlines(keepends=True)
    # 🔴 K360-A: kalan acilislarin TUM kimlikleri duz bir kumeye acilir ve kapanis
    # kimlikleriyle KESISTIRILIR — cift butunlugu ile K329 eslestirmesi AYNI eksenden
    # okumalidir, yoksa bir kol otekinin gormedigi cifti boler.
    kalan_acilis = set()
    for adlar in basliyorum_adlari(
            yk_satir_ke,
            blok_baslari(yk_satir_ke, frontmatter_sonu(yk_satir_ke)[0] or 0)).values():
        kalan_acilis.update(adlar)
    ek_kapanis = kapanis_bloklari(ek_satir_ke, blok_baslari(ek_satir_ke))
    for _bi, kap_adlar in sorted(ek_kapanis.items()):
        ortak = [x for x in kap_adlar if x in kalan_acilis]
        kap_ad = ortak[0] if ortak else kap_adlar[0]
        if ortak:
            h.append("D18 CIFT BOLUNMESI: tasinan metinde cip `%s` KAPANISI var ama "
                     "AYNI CIPIN `%s` blogu kutuda KALIYOR -> acilis bir daha ASLA "
                     "eslesemez ve kutuda KALICI OLU SLOT olurdu. Fail-closed: "
                     "hicbir sey yazilmadi." % (kap_ad, BASLIYORUM_JETON))

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
# === K324 (27 Agu 2026) — ESIK, YAZIM HIZINA YETISMIYORDU ==================
# OLCULEN ARIZA (27 Agu, canli kutu): rotasyon gun icinde IKI KEZ atesledi
# (570->220 ve 331->230) ve kutu HER IKISINDEN SONRA yeniden tasti — aksam
# olcumu 333 satir / tavan 300. Sebep tavanin kucuklugu DEGIL, TETIGIN YERI:
# kanonik rotasyon yalniz `pre-push` kancasindan kosuyor, yani kutu ancak
# "biri PUSH edince" doner. Oysa kutuya yazan sey PUSH degil, cipin kapanis
# BLOGUDUR; iki push arasinda onlarca blok birikebiliyor ve tavan asimi
# GUN BOYU KALICI oluyor.
#
# CARE (tavan BUYUTULMEDEN): rotasyonu YAZIMA baglayan ikinci bir tetik.
# `--yaz-sonrasi <duzenlenen_yol>` bir PostToolUse kancasindan cagrilir;
# kutuya her yazimdan SONRA kosar ve tavan asilmissa AYNI kanonik rotasyonu
# AYNI --tavan/--koru ile atesler.
#
# 🔴 UC SART, ucu de bu kolun GEVSETME OLMADIGINI garanti eder:
#  (1) TAVAN/KORU DEGISMEZ — ikinci bir esik tanimlanmaz, ayni main() govdesi
#      bayraksiz yeniden cagrilir ([[ikiz-tanim-sessiz-ayrisma]]).
#  (2) HEDEF SARTI — duzenlenen dosya KUTU degilse hicbir sey yapilmaz; kol
#      baska hicbir dosyaya dokunmaz.
#  (3) FAIL-OPEN — bu kol bir YAZIM kancasinda kosar. Kirmizi donerse
#      mimarin `Edit`i bloklanir ve kutu YAZILAMAZ hale gelir; o yuzden kol
#      her halde rc=0 doner ve gercek rc'yi `YAZ_SONRASI_IC_RC=` ile BASAR
#      (yutmaz, gorunur kilar).
def _kanca_stdin_yolu():
    """PostToolUse kancasinin stdin JSON'undan duzenlenen dosya yolunu cikarir.

    AYRI BIR SARMALAYICI DOSYA ACILMAZ: kanca dogrudan bu araci cagirir
    (`--yaz-sonrasi -`). Ikinci bir betik, ikinci bir bakim yuzeyi ve
    kablolamada ikinci bir yol demektir; kanca ne kadar az parcadan
    olusursa o kadar az sessizce kopar.
    """
    import json
    ham = sys.stdin.read()
    veri = json.loads(ham)
    girdi = veri.get("tool_input") or {}
    yol = girdi.get("file_path") or girdi.get("notebook_path") or ""
    if not yol:
        raise ValueError("kanca stdin'inde file_path YOK")
    return yol


def _yaz_sonrasi_kolu(argv, yaz_sonrasi_yolu, kutu_yolu, tavan):
    """Yazim tetikli rotasyon kolu. HER ZAMAN RC_OK doner (fail-open)."""
    try:
        if yaz_sonrasi_yolu == "-":
            yaz_sonrasi_yolu = _kanca_stdin_yolu()
        hedef = os.path.abspath(os.path.expanduser(yaz_sonrasi_yolu))
        if hedef != kutu_yolu:
            print("YAZ_SONRASI=ATLANDI sebep=hedef-kutu-degil hedef=%s" % hedef)
            return RC_OK
        if not os.path.exists(kutu_yolu):
            print("YAZ_SONRASI=ATLANDI sebep=kutu-yok")
            return RC_OK
        with open(kutu_yolu, "rb") as f:
            satir = len(f.read().splitlines())
        if satir <= tavan:
            print("YAZ_SONRASI=ATLANDI sebep=tavan-altinda satir=%d tavan=%d"
                  % (satir, tavan))
            return RC_OK
        # ATESLE: AYNI govde, AYNI esik — yalnizca kendi bayragi cikarilir.
        temiz = []
        atla = False
        for parca in argv:
            if atla:
                atla = False
                continue
            if parca == "--yaz-sonrasi":
                atla = True
                continue
            if parca.startswith("--yaz-sonrasi="):
                continue
            temiz.append(parca)
        print("YAZ_SONRASI=ATESLEDI once_satir=%d tavan=%d" % (satir, tavan))
        ic_rc = main(temiz)
        with open(kutu_yolu, "rb") as f:
            sonra = len(f.read().splitlines())
        print("YAZ_SONRASI_IC_RC=%s once_satir=%d sonra_satir=%d"
              % (ic_rc, satir, sonra))
    except Exception as hata:                              # noqa: BLE001
        # (3) FAIL-OPEN: yazim kancasi ASLA bloklanmaz; sebep GORUNUR kalir.
        print("YAZ_SONRASI=OLCULEMEDI sebep=%s" % type(hata).__name__)
        print("  ayrinti: %s" % str(hata)[:200])
    return RC_OK


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
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
    ap.add_argument("--kapanislari-isle", action="store_true",
                    help="K341: KAPANIS KONUMUNDAKI `%s` jetonunu `%s` bicimine cevirir "
                         "ve o bloklari rotasyona ACAR. Rotasyondan ONCE, AYNI KILIT "
                         "altinda calisir. GOVDE ANMASI ve AYRISTIRILAMAYAN blok "
                         "DOKUNULMAZ. Dogrulama (C1-C8) gecmezse HICBIR SEY yazilmaz. "
                         "Okan kurali ⑤ geregi bu cevrim 'Okan arsivledi' hukmudur — "
                         "bayrak KOSULSUZ degil, CAGIRANIN hukmuyle verilir."
                         % (BEKLEYEN_JETON, ISLENMIS_JETON))
    ap.add_argument("--yaz-sonrasi", default=None, metavar="DUZENLENEN_YOL",
                    help="K324: YAZIM TETIKLI rotasyon. Kutuya bir blok EKLENDIKTEN "
                         "hemen sonra cagrilmak icindir (PostToolUse kancasi). "
                         "DUZENLENEN_YOL kutu DEGILSE ya da kutu tavan ALTINDAYSA "
                         "hicbir sey yapmaz. TAVANI DEGISTIRMEZ — ayni kanonik "
                         "rotasyonu ayni --tavan/--koru ile koşturur. FAIL-OPEN: "
                         "her hâlde rc=0 doner, yazim islemini ASLA bloklamaz. "
                         "DEGER `-` ise yol PostToolUse kancasinin stdin JSON'undan "
                         "okunur (ayri sarmalayici betik GEREKMEZ).")
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

    # K324: YAZIM TETIKLI kol — karar burada verilir (kutu yolu cozuldukten
    # sonra, KILIT alinmadan once). Atesleyecekse ayni main() bayraksiz
    # yeniden cagrilir; ikinci bir rotasyon govdesi ACILMAZ.
    if a.yaz_sonrasi is not None:
        return _yaz_sonrasi_kolu(argv, a.yaz_sonrasi, kutu_yolu, a.tavan)

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

        # 🔴 K341 CEVRIM KOLU — ROTASYONDAN ONCE, AYNI KILIT ALTINDA. Sira zorunlu:
        # cevrim korumayi KALDIRIR, rotasyon o kalkmis korumayla planlar. Ters sirada
        # cevrim ancak ERTESI kosumda ise yarardi (bugunku el isinin ta kendisi).
        cevrim_yazilmali = False
        cevrilen = []
        disk_once_bayt = len(kutu_metin.encode("utf-8"))
        if a.kapanislari_isle:
            yeni_kutu_cevrim, cevrilen, cev_atlanan, cev_govde, chata = cevir(kutu_metin)
            if chata:
                print("KIRMIZI (cevrim: bozuk/yarim kutu): %s" % chata)
                return RC_KIRMIZI
            yeni_kutu_cevrim, ahata = cevrim_ariza_uygula(yeni_kutu_cevrim, cevrilen)
            if ahata:
                print("KIRMIZI: %s" % ahata)
                return RC_KIRMIZI
            chatalar = dogrula_cevrim(kutu_metin, yeni_kutu_cevrim, cevrilen, cev_atlanan)
            print("CEVRIM=%d atlanan_fail_closed=%d govde_anmasi=%d "
                  "bayt_once=%d bayt_sonra=%d delta=%+d  [KAPI]"
                  % (len(cevrilen), len(cev_atlanan), cev_govde, disk_once_bayt,
                     len(yeni_kutu_cevrim.encode("utf-8")),
                     len(yeni_kutu_cevrim.encode("utf-8")) - disk_once_bayt))
            for blok_idx, idx, eskisi, _yenisi in cevrilen:
                print("  ✓ CEVRILDI blok %d (satir %d): %s -> %s | %s"
                      % (blok_idx + 1, idx + 1, BEKLEYEN_JETON, ISLENMIS_JETON,
                         eskisi.strip()[:70]))
            # 🔴 SESSIZ ATLAMA YASAK: cevrilMEYEN korumali blok ADIYLA/SINIFIYLA basilir,
            # yoksa "13 vardi 11 cevrildi" farki gorunmez ve kutu sebepsiz tavan ustunde kalir.
            for blok_idx, satir_no, ozet, sinif in cev_atlanan:
                print("  ! CEVRILMEDI blok %d (satir %d, sinif=%s): blok yapisi "
                      "AYRISTIRILAMADI -> DOKUNULMADI (fail-closed) | %s"
                      % (blok_idx + 1, satir_no, sinif, ozet))
            if cev_govde:
                print("  · CEVRIM GOVDE ANMASI=%d blok: jeton KAPANIS KONUMUNDA DEGIL -> "
                      "DOKUNULMADI (K318 KOL-1 ile AYNI olcut)" % cev_govde)
            if chatalar:
                print("CEVRIM DOGRULAMASI KIRMIZI — HICBIR SEY YAZILMADI:")
                for x in chatalar:
                    print("  - %s" % x)
                return RC_KIRMIZI
            print("cevrim_dogrulama=GECTI (iddia=%d, cevrilen=%d, atlanan=%d)"
                  % (len(CEVRIM_IDDIA_EKSENLERI), len(cevrilen), len(cev_atlanan)))
            if cevrilen:
                kutu_metin = yeni_kutu_cevrim
                cevrim_yazilmali = True
        else:
            print("CEVRIM=0 kip=KAPALI (--kapanislari-isle verilmedi)  [KAPI]")

        # 🔴 K360-B ARSIV DUZLEMI — kapanislar kutudan once arsive akar; "bu cip
        # kapandi mi" sorusu IKI DUZLEMDEN de cevaplanir. FAIL-CLOSED: okunamazsa
        # kayit URETILMEZ (hicbir blok serbest kalmaz) ve sebep ADIYLA basilir.
        ars_kayit, ars_hata = arsiv_kapanis_kayitlari(arsiv_metin)
        p = planla(kutu_metin, a.tavan, a.koru, arsiv_kayitlari=ars_kayit)
        p.arsiv_hatasi = ars_hata
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

        # 🔴 K329 ACIK CIP KOLU — HER kosumda basilir, is olsa da olmasa da; 0 ile n
        # AYNI SATIRDAN okunur. "Sessizce atlamak" YASAK: atlanan blok CIP ADIYLA
        # basilir, cunku kutu tavan ustunde kalirsa SEBEBI gorunmelidir.
        print("ACIK_BASLIYORUM=%d kapanmis_basliyorum=%d basliyorum_govde_anmasi=%d "
              "kilitledi=%d  [KAPI]"
              % (len(p.acik_cip), p.kapanmis_basliyorum, p.basliyorum_govde_anmasi,
                 p.acik_kilitledi))
        print("ACIK_BASLIYORUM_ADLARI=%s"
              % (",".join((ad or "AD_YOK") for _b, ad, _o, _k in p.acik_cip) or "-"))
        for blok_idx, ad, ornek, sinif in p.acik_cip:
            print("  * ACIK CIP blok %d/%d (sinif=%s): cip `%s` — ESLESEN KAPANIS "
                  "kutuda YOK -> blok ROTASYONA GIRMEZ (YERINDE ATLANDI) | %s"
                  % (blok_idx + 1, p.blok_toplam, sinif, ad or "AD_YOK", ornek))
        if p.basliyorum_govde_anmasi:
            print("  · BASLIYORUM GOVDE ANMASI=%d blok: jeton blogun ICINDE geciyor ama "
                  "BASLIK satirinda DEGIL -> veto URETMEZ (K329 konum olcutu), blok "
                  "rotasyona ACIK." % p.basliyorum_govde_anmasi)
        # 🔴 K360-B ARSIV DUZLEMI — HER kosumda basilir, is olsa da olmasa da.
        # K329'dan AYRI SAYI: orada "kapanisi HICBIR YERDE yok" denir, burada
        # "kapanisi ARSIVDE bulundu" denir. Ayni satirdan okunursa ucuncu hal yutulur
        # ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
        print("ARSIV_SERBEST=%d arsiv_kapanan_ad=%d  [KAPI]"
              % (len(p.arsiv_serbest), len(p.arsiv_kayitlari)))
        print("ARSIV_SERBEST_ADLARI=%s"
              % (",".join(ad for ad, _z in
                          [p.arsiv_serbest[k] for k in sorted(p.arsiv_serbest)])
                 or "-"))
        for blok_idx in sorted(p.arsiv_serbest):
            ad, zaman = p.arsiv_serbest[blok_idx]
            print("  * ARSIV SERBEST blok %d/%d: cip `%s` — ESLESEN KAPANIS ARSIVDE "
                  "BULUNDU (kapanis gun=%s dk=%s, acilistan DAHA ESKI DEGIL, kayit "
                  "TUKETILDI) -> blok rotasyona ACIK"
                  % (blok_idx + 1, p.blok_toplam, ad, zaman[0], zaman[1]))
        if p.arsiv_hatasi:
            print("  · ARSIV OLCULEMEDI (FAIL-CLOSED, hicbir blok serbest BIRAKILMADI): "
                  "%s" % p.arsiv_hatasi)
        # 🔴 K359-B CIFT BUTUNLUGU — HER kosumda basilir, is olsa da olmasa da.
        # K329'dan AYRI SAYI: orada "kapanisi YOK" denir, burada "kapanisi VAR ama
        # acilisi kutuda kaliyor" denir. Ikisi ayni satirdan okunursa ucuncu hal
        # yutulur ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
        print("CIFT_KORUMASI=%d  [KAPI]" % len(p.cift_korumasi))
        for blok_idx, ad, sebep in p.cift_korumasi:
            print("  * CIFT KORUMASI blok %d/%d (sebep=%s): cip `%s` KAPANISI — AYNI "
                  "CIPIN `%s` blogu kutuda KALIYOR -> kapanis ROTASYONA GIRMEZ "
                  "(cift BOLUNMEZ; bolunseydi acilis bir daha ASLA eslesemezdi)"
                  % (blok_idx + 1, p.blok_toplam, sebep, ad, BASLIYORUM_JETON))
        if p.acik_cip:
            print("NE YAPILMALI: bu cip(ler) sayili KAPANISINI kutuya YAZSIN "
                  "(`SAYILI KAPANIS` basligi ya da kapanis jetonu); ayni ADLA bir "
                  "kapanis blogu goruldugu anda `BASLIYORUM` blogu rotasyona ACILIR.")

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
                    print("HUKUM=KORUMA_TUTTU rc=0 sebep=bekleyen kapanis blogu ve/veya "
                          "ACIK CIP blogu rotasyona GIRMEZ (KORUMALI_BEKLEYEN=%d "
                          "kilitledi=%d · ACIK_BASLIYORUM=%d kilitledi=%d, taban "
                          "koru=%d). Kutu tavanin USTUNDE kalabilir — GORUNURLUK kota "
                          "kirmizisina tercih edilir (Okan kurali ⑤); hal GIZLENMEDI, "
                          "BASILDI."
                          % (len(p.korumali), p.korumali_kilitledi,
                             len(p.acik_cip), p.acik_kilitledi, a.koru))
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
            # 🔴 K341: TASIMA YOKSA BILE CEVRIM YAZILIR. Cevrim rotasyondan BAGIMSIZ bir
            # is birimidir (jetonu isaretler); tasima olmadi diye onu YUTMAK, ertesi
            # kosumda ayni eli tekrar gerektirirdi — kalemin ta kendisi.
            if cevrim_yazilmali and not a.kuru:
                atomik_yaz(kutu_yolu, kutu_metin)
                print("YAZILDI: %d kapanis jetonu CEVRILDI (tasima yok)" % len(cevrilen))
            elif cevrim_yazilmali:
                print("KURU KIP — cevrim de yazilmadi (%d jeton) " % len(cevrilen))
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
        elif (p.korumali_kilitledi + p.acik_kilitledi) > 0:
            print("HUKUM=KORUMA_TUTTU_KISMI rc=0 sebep=%d bekleyen kapanis + %d ACIK "
                  "CIP blogu YERINDE ATLANDI ve kutuda kaldi; tasinabilen %d blok "
                  "tasindi ama kutu (%d satir) tavanin (%d) USTUNDE kaldi"
                  % (p.korumali_kilitledi, p.acik_kilitledi, p.tasinacak_blok,
                     p.sonra_satir, a.tavan))
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
        print("YAZILDI: %d blok / %d satir arsive tasindi (cevrilen kapanis jetonu=%d; "
              "kutu diskte %d -> %d bayt)"
              % (p.tasinacak_blok, p.tasinan_satir, len(cevrilen), disk_once_bayt,
                 len(yeni_kutu.encode("utf-8"))))
        return RC_OK
    finally:
        kilit_birak(kilit)


if __name__ == "__main__":
    sys.exit(main())
