#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YONET ANAHTAR/CEREZ KABUL ALT KUMESI (`node shop/test/kabul.js --yonet-cerez`) MUTASYON HARNESS'I.

NE ISE YARAR: bu alt kume bir GUVENLIK kapisidir (siparis yonetimi paneline giris).
"iddialar yesil" tek basina HICBIR SEY kanitlamaz — kanit, korumayi BOZUNCA iddianin
KIRMIZI yanmasidir (mutasyon) VE bozulmamis/ilgisiz refaktorde YESIL kalmasidir
(kontrol mutanti). Bu surucu olmadan, ileride bir iddianin icini bosaltan degisiklik
nobetciyi SESSIZCE oldurur ve kimse fark etmez.

NEDEN VAR: `yonet-anahtar-cerez` dali mutasyon bataryasini RAPORDA anlatti ama
SURUCUYU COMMIT ETMEDI ("python3 <mutasyon surucusu v2>"). Guvenlik kapisinin kaniti
yeniden uretilemez hale gelmisti. Bu dosya o boslugu kapatir; depo konvansiyonu
(tools/yayin-gecikme-mutasyon.py, tools/konfigur-nobet-mutasyon.py,
tools/commit-mesaji-mutasyon.py, tools/gecmis-geri-donus-mutasyon.py) surucunun
REPODA DURMASIDIR.

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Canli shop/src/yonet.js'i bozup `finally`
ile geri alma deseni bu evde YASAK: tek bir kesinti (Ctrl-C, OOM, kota bitmesi)
calisma agacinda MUTANT birakir — yani deploy edilebilir bir ARKA KAPI. Burada gecici
bir dizine kabul testinin ihtiyac duydugu agacin TAM KOPYASI yazilir; kaynak agaca
HICBIR YAZMA yapilmaz, aynada kaynaga giden SYMLINK bulunmadigi olculur, ve kaynak
dosyanin sha256'si basta alinip HER kosumdan sonra + en sonda yeniden dogrulanir.

MUTANTLAR (hepsi GERCEK, canliya sizabilecek bozulmalar; hepsi KIRMIZI yanmali)
  M1 ?anahtar= geri geldi     — isin BAS SEBEBI: anahtar erisim loglarina/Referer'a yazilir
  M2 sabitEsit fail-open      — `String(a || "")`: bos sifre + tanimsiz secret = YETKI
  M3 secret kapisi POST'un    — yonet()'in kapisi giris POST'undan SONRAYA alinir VE
     ARKASINA alindi            girisYap'in kendi kapisi silinir (iki kapi BIRDEN duser)
  M4 ikame DIZESI             — girisEkrani'nda fonksiyon yerine dize: `$\\`` enjeksiyonu
  M5 hiz siniri kalkti        — paylasilan tek anahtara kaba kuvvet serbest
  M6 govde ust siniri kalkti  — anahtarsiz uca sinirsiz govde ayristirma
  M7 cerez adi naive includes — `pruvo_yonet_x=<anahtar>` yakin-iskasi yetki alir
  M8 HttpOnly dusuruldu       — XSS oturum cerezini calabilir
  M9 SameSite=Strict -> Lax   — capraz-site gezinmede cerez gider (CSRF ekseni acilir)
  M10 girisYap'in KENDI secret — savunma derinliginin IC KATMANI duser. 2 Agu'a kadar bu
      kapisi silindi             mutant SURVIVOR'di (K4 adiyla, YESIL beklentisiyle):
                                 alt kume onu HIC olcmuyordu, cunku tek iddia (eski "C22")
                                 istegi yonet() uzerinden gecirip IKI kapinin VEYA'sini
                                 olcuyordu. Iddia C22a (girisYap IZOLE, yonet() bypass) +
                                 C22b (yonet() ust kapisi IZOLE) olarak IKIYE AYRILDI ve
                                 bu mutant artik KIRMIZI yaniyor -> SURVIVOR degil.
  M11 ozellik-kapali KOL      — secret yokken POST / giris EKRANI servis eder (GET hala
      birlestirildi              404): ozellik KAPALIYKEN ucun varligi sizar. C15a'nin
                                 AYIRT EDICI mutanti (tek kirmizi).
  M12 yon404 TEK KAYNAGININ   — kod 404 KORUNUR, govde HTML+<form> olur: tek kaynak oldugu
      govdesine <form> girdi     icin C22a ile C22c BIRLIKTE duser (ayirt edici DEGIL).
  M13 ozellik-kapali TUM      — ust kapi GET'te formsuz 200 doner (POST 404 kalir): ust kapi
      GET'ler formsuz 200        tum yollarda ortak oldugu icin C6a/C6b de duser (ayirt
                                 edici DEGIL).
  M14 ust kapinin KENDI 404   — kod 404 KALIR, yon404 TEK KAYNAGI saglam: yalniz ust kapinin
      govdesine <form> girdi     govdesi kirlenir. C22c'nin AYIRT EDICI mutanti (tek kirmizi).
  M15 ust kapi YALNIZ         — /liste kolu, POST kolu ve govde saglam kalir; yalniz panel
      `GET /`te formsuz 200      kokunun VARLIGI 200'le dogrulanir. C22b'nin AYIRT EDICI
                                 mutanti (tek kirmizi).

  M16 ozellik-kapali root GET  — ILK cagri temiz 404, IKINCI+ cagri giris ekrani. CAGRI
      IKINCI+ cagride sizar      SIRASI sinifinin tasiyicisi (asagi bak).
  M17/M18/M19                  — girisYap'in kendi kapisinin KOD / CEREZ / GOVDE eksenlerini
      girisYap'in uc ekseni      TEK TEK bozar. M18 tam da bu kapinin engelledigi zarardir:
                                 404 ve formsuz govde doner AMA anahtarsiz oturum cerezi BASAR.
  M20/M21 ILK cagri            — soguk baslangic / tembel ilklendirme sinifi: yalniz ILK
      M22/M23 IKINCI+ cagri      ozellik-kapali root GET bozulur (M20 kod, M21 govde); M22/M23
                                 ayni ikiliyi IKINCI+ cagri icin yapar. Dort ordinal-eksen
                                 iddiasinin (C15b/C15c/C22b/C22c) ayirt edicileri bunlardir.
  M24/M25 /liste kolunun       — ozellik-kapali /liste YALNIZ ILK (M24) ya da YALNIZ IKINCI+
      iki ordinali               (M25) cagride siparis listesini anahtarsiz servis eder.
                                 C6a/C6b'nin AYIRT EDICILERI. 2 Agu'da OLCULEREK eklendi:
                                 oncesinde bu iki iddianin ordinal ekseni icin surucude
                                 HICBIR kayit yoktu (C6a/C6b yalniz M13'un yan kirmizisiydi).
  M26 kaba kuvvet gecikmesi    — GIRIS_GECIKME_MS 250 -> 0: basarisiz/bloke her denemedeki
      TAMAMEN kalkti             sabit yavaslatici yok olur. 2 Agu'a kadar bu eksen
                                 OLCULMEMISTI ve mutant SURVIVOR'di (olculdu: cikis 0,
                                 kirmizi 0, iddia 70/70). Alt kumeye C23 eklendi (istenen
                                 setTimeout gecikmesi >= 100 ms; ALT SINIR, ust sinir YOK,
                                 duvar saati DEGIL) -> artik TEK kirmizi.

EKSENE INDIRME (2 Agu, olculdu — "iddia sisirmesi" YAPILMADI). Kural: bir eksen ancak
YALNIZ onu kirmizi yakan bir mutant VARSA kendi iddiasi olur; yoksa iddia EKLENMEZ.
Bugun kural TAM oturuyor: C15a, C15b, C15c, C22a, C22b, C22c, C22d, C22e — sekizinin de
kendi TEK-KIRMIZI mutanti var (sirasiyla M11, M20, M21, M17, M22, M23, M18, M19).
BUNLARA EK olarak C6a/C6b (ozellik-kapali /liste kolunun iki cagri ordinali) de artik TEK
kirmizi yakan ayirt edicilere sahip: M24/M25 (olculdu; YENI IDDIA EKLENMEDI — var olan iki
iddianin ne tuttugu nobet altina alindi).

🔴 CAGRI SIRASI OLCUMUN PARCASIDIR — SONDAYI SILME. Alt kume ozellik-kapali panel kokunu
IKI kez yokluyor: 15. blokta (C15b/C15c) ve 22. blokta (C22b/C22c). Bir ara turda "yuklemleri
ozdes, kopya" denilip 15. bloktaki sonda SILINMISTI. OLCULDU ki bu KAPSAM KAYBIYDI: modul
duzeyi durum Workers'ta istekler ARASI yasar (bu dosyada `girisSayac` zaten oyle), yani
"ilk cagri temiz, ikinci cagri sizdiriyor" sinifi (M16) sonda silinmisken alt kumeyi
YESIL geciyordu. Yuklem ozdesligi argumani DURUMSUZLUGU varsayiyordu ve o varsayim yanlisti.

⚠️ BEYAN BAYATLAMASI (olculdu): sonda geri konunca ust kapiden gecen root GET sayisi 1'den
2'ye cikti ve M14/M15 "tek eksen" olmaktan cikti (her biri iki ordinali birden dusuruyor).
Bunu YENI ESIT olcutu ilk kosumda yakaladi; eski KAPSAR olcutu sessizce PASS verirdi.
M14/M15 genis()e alindi, ordinal ayirt edicileri M20-M23 olarak eklendi.

KONTROL MUTANTLARI (kontrol() ile BEYAN EDILIR; YESIL kalmali — surucu "her sey kirmizi"
diye ucuza gecemesin; ayrica kapinin ILGISIZ refaktorde yanlis alarm uretmedigi olculur)
  K1 sabitEsit'te YEREL DEGISKEN adi degisti (davranis ayni)
  K2 girisYap'a YORUM SATIRI eklendi (davranis ayni)
  K3 anahtarGecerli'de baslik/cerez KONTROL SIRASI takas edildi (iki tasiyici da calisir)
  (K4 EMEKLI: yukaridaki M10'a donustu. Beyan edilmis SURVIVOR'in tehlikesi olculdu —
   "bugun yesil kalmasi normal" demek, o katmanin HIC olculmedigini gizliyordu; iki ayri
   yesil commit iki kapiyi ayri ayri dusurup birlikte anahtarsiz cerez kurulumuna kapi
   acabilirdi. Bir katmanin savunma derinligi oldugu iddiasi ancak o katman TEK BASINA
   olculuyorsa kanittir.)

KABUL — HER KIRMIZI-BEKLENTILI MUTANT ICIN UC SART BIRDEN:
  1. IDDIA SAYISI taban kosumla AYNI. (Cokme kirmiziyla KARISIR: mutant testi
     COKERTIRSE cikis kodu da 1 olur ama hicbir sey OLCULMEMISTIR. Sayi esitligi
     "test sonuna kadar kostu" demektir; bu depoda olculdu — sorgu parametresini geri
     ekleyen mutant ilk turda SONUC satirini hic basmamisti.)
  2. Cikis kodu 1 VE en az bir ❌ satiri.
  3. BEKLENEN IDDIA KODLARININ HEPSI kirmizi satirlarda ADIYLA gecmeli (isaret sarti —
     mutant "kaza eseri" baska bir yerden kirmizi yakip gecmis sayilmasin).
Kontrol mutantlarinda: cikis 0, ❌ yok, IDDIA SAYISI taban ile ayni.

CAPA YOK: taban iddia sayisi KOSUMDA olculur, kodda SABIT DEGILDIR (bugunku sayiyi
yazsak, yarin bir iddia eklenince sahte kirmizi yanardi). Mutant kosumlari o OLCULEN
sayiyla karsilastirilir.

🔴 SURUCUNUN KENDI IKI DELIGI KAPATILDI (2 Agu, bagimsiz curutucu OLCTU):
  (a) VAKUM YESILI — MUTANTLAR bosaltilinca (ya da tek kayda dusurulunce) surucu "0 kosum"
      yapip `TUM MUTANTLAR YAKALANDI ✅` basiyor ve cikis 0 veriyordu. Hicbir sey
      olculmemisken "hepsi yesil" demek, bu nobetcinin kapatmak icin var oldugu kalibin ta
      kendisidir. Artik alt sinir IKI BAGIMSIZ kaynaktan gelir: (1) modul duzeyinde TANIMLI
      her M<n>/K<n> kaydi MUTANTLAR'da KAYITLI olmak zorunda (tek kaynak MODULUN KENDISI —
      yeni kayit eklenince taban KENDILIGINDEN yukselir, elle guncellenecek sayi YOK) ve
      (2) ASGARI_KAYIT/ASGARI_KIRMIZI/ASGARI_KONTROL tabanlari (tanim+kayit BIRLIKTE
      silinirse envanter kucuk kalirdi). Kabul: liste bosaltilinca cikis 1, tek kayit
      birakilinca cikis 1 (ikisi de once 0'di).
  (b) `beklenen=[]` AKLAMASI — sinif `beklenen`in BOSLUGUNDAN turetiliyordu, yani GERCEK
      bir bozulmayi bos beklenenle kaydetmek onu "kontrol" yapiyordu. Yakalanan bir bozulma
      boyle aklanamaz (kirmizi yanar, olculdu), ama SURVIVOR aklanabiliyordu: olculdu ki
      `GIRIS_GECIKME_MS 250 -> 0` beklenen=[] ile eklendiginde surucu "MZ YESIL / TUM
      MUTANTLAR YAKALANDI" basip cikis 0 veriyordu — en tehlikeli hal, cunku olculmemis
      eksen tam da orada gizlenir. Artik sinif BEYAN EDILIR (kontrol() sarmalayicisi):
      kirmizi-beklentili kaydin `beklenen`i BOS OLAMAZ, kontrol kaydininki BOS OLMAK
      ZORUNDA; ikisi de kosumdan ONCE fail-closed suzulur, tuketim yeri de sinifi
      beyandan okur (`if beklenen:` dali KALDIRILDI).

Ag YOK · wrangler YOK · D1 YOK · canli uc YOK (alt kumenin kendisi deterministik).
Bu harness CI'da KOSMAZ — gelistirici/curutucu aracidir.
Kullanim: python3 tools/yonet-cerez-mutasyon.py   (0 = tum mutantlar yakalandi, 1 = kusur)
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEDEF = os.path.join(ROOT, "shop", "src", "yonet.js")
NODE = shutil.which("node")
FAILS = []

# Aynaya TASINAN agac: `--yonet-cerez` kolunun GERCEKTEN dokundugu her sey.
# (kabul.js modul basinda kok secenekler.js'i require eder ve shop/config.json okur;
#  yonet.js -> semalar.js -> jenerator/urunler/*.json, konfigur.js -> kok konfigur.js;
#  C17 iddialari tools/yazdir.py KAYNAGINI okur.)
# ⚠️ Bu kume EKSIK KALIRSA taban kosumu KIRMIZI yanar ve harness DURUR — sessizce
# "olctum" demez. Yani liste bayatlarsa davranis fail-closed'dur.
AYNA_DIZIN = [
    os.path.join("shop", "src"),
    os.path.join("shop", "test"),
    os.path.join("jenerator", "urunler"),
]
AYNA_DOSYA = [
    os.path.join("shop", "config.json"),
    "secenekler.js",
    "konfigur.js",
    os.path.join("tools", "yazdir.py"),
]
# Aynaya girmeyen artefaktlar: yerel sir dosyalari (.dev.vars) ve turetilmis agaclar.
KOPYA_HARIC = shutil.ignore_patterns(".*", "node_modules", "__pycache__")


def check(etiket, kosul, detay=""):
    print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", etiket,
                           ("  -> " + detay) if detay else ""))
    if not kosul:
        FAILS.append(etiket)
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ------------------------------------------------------------------ olcutler
# 🔴 GECERLI OLCUT DEGERLERI TEK KAYNAKTIR. Dosyanin hicbir yerinde "ESIT"/"KAPSAR" dizesi
# ELLE yazilmaz (ne sarmalayicida, ne tuketim yerinde, ne rapor satirinda): ikiz tanim
# sessizce ayrisir. Sarmalayicilar (tek_eksen/esit_kume/genis) bu sabitleri dondurur,
# tuketim yeri yine bu sabitlerle karsilastirir, dogrulayici yine bu demetten uretir.
OLCUT_ESIT = "ESIT"        # kirmizi kume == beyan (fazlalik KUSUR -> capa)
OLCUT_KAPSAR = "KAPSAR"    # beyan ⊆ kirmizi (ek kirmizi BEKLENIR -> capa YOK)
OLCUT_KONTROL = "KONTROL"  # davranis-koruyan refaktor: YESIL kalmali (beklenen BOS olmali)
OLCUTLER = (OLCUT_ESIT, OLCUT_KAPSAR, OLCUT_KONTROL)
KIRMIZI_OLCUTLER = (OLCUT_ESIT, OLCUT_KAPSAR)

# 🔴 KAYIT SINIFI ARTIK BEYAN EDILIR, `beklenen`in BOSLUGUNDAN CIKARILMAZ (2 Agu, olculdu).
# ONCE: sinif "beklenen bos mu?" diye TURETILIYORDU. Bu, GERCEK bir bozulmayi "kontrol" diye
# kaydedip BEDAVA YESIL almanin yoluydu ve olculdu: `GIRIS_GECIKME_MS 250 -> 0` (kaba kuvvet
# yavaslaticisini TAMAMEN kaldiran gercek bir zafiyet) beklenen=[] ile eklendiginde surucu
# "MZ YESIL / TUM MUTANTLAR YAKALANDI" basip cikis 0 veriyordu. Yakalanabilen bir bozulma
# ayni sekilde aklanmaya calisilirsa zaten kirmizi yanar (olculdu: kapi silen mutant -> cikis 1)
# — yani delik TAM OLARAK "SURVIVOR'i kontrol diye etiketlemek"ti; en tehlikeli hal, cunku
# olculmemis eksen tam da orada gizlenir. Artik:
#   - OLCUT_ESIT / OLCUT_KAPSAR (kirmizi-beklentili) kaydin `beklenen`i BOS OLAMAZ,
#   - OLCUT_KONTROL kaydin `beklenen`i BOS OLMAK ZORUNDA,
#   - ikisi de kosumdan ONCE fail-closed suzulur (olcut_dogrula).
# Boylece "kontrol" bir SINIF BEYANIDIR: yazan kisi "bu mutasyon DAVRANISI KORUR" demis olur.

# ------------------------------------------------------------------ mutantlar
# (kod, aciklama, [(bulunacak, yerine), ...], beklenen_kirmizi_iddia_kodlari, OLCUT)
# SINIF `beklenen`in BOSLUGUNDAN CIKARILMAZ, sarmalayiciyla BEYAN EDILIR:
#   tek_eksen/esit_kume/genis -> kirmizi-beklentili (beklenen DOLU olmak ZORUNDA),
#   kontrol                   -> davranis-koruyan refaktor (beklenen BOS olmak ZORUNDA).
#
# 🔴 OLCUT, MUTANTIN KENDI KAYDINDA (asagidaki MUTANTLAR listesinde tek sarmalayiciyla):
#   tek_eksen(...) / esit_kume(...) -> OLCUT_ESIT:  kirmizi kume BEKLENENE ESIT olmali. Bir
#       iddianin "AYIRT EDICI / TEK KIRMIZI" oldugu hukmu ANCAK boyle korunur. Ilk surumde
#       olcut yalnizca KAPSAMA idi (beklenen ⊆ kirmizi): beklenenin USTUNE fazladan iddia
#       kirmizi yansa da mutant PASS veriyordu. Yani "M14 yalniz C22c'yi yakar" gibi TUM
#       ayirt edicilik iddialarimiz nobetci tarafindan HIC olculmuyordu — biri yarin bir
#       iddiayi genisletse ozellik sessizce olur, tek kapi bile kirmizi yanmazdi. Kendini-test
#       yapildi: ayirt edici bir mutanta fazladan iddia kirmizi yaktiran sapma eklendiginde
#       ESIT olcutu KIRMIZI, eski KAPSAR olcutu YESIL veriyor.
#   genis(...) -> OLCUT_KAPSAR:  beklenen ⊆ kirmizi. Kirmizi kumesi beyanindan GENIS OLCULEN
#       (ya da genis olmasi BEKLENEN) bozulmalar icindir; onlarda ek kirmizi capa yapilmaz.
# Kontrol mutantlarinda (beklenen BOS) olcut degeri kullanilmaz — ama YINE DE GECERLI olmak
# ZORUNDADIR (bkz. olcut_dogrula): kayit sekli tek turlu kalsin, "olcutu bos gecince kontrol
# olur" gibi sessiz bir ikinci anlam DOGMASIN.
#
# 🔴 FAIL-CLOSED (2 Agu, olculdu): taninmayan/eksik olcut degeri VARSAYILANA DUSMEZ. Once
# `olcut == "ESIT"` yazan tek bir karsilastirma vardi; degeri "Esit" diye yanlis yazmak
# (buyuk/kucuk harf sapmasi) mutanti SESSIZCE KAPSAR'a dusuruyor ve surucu cikis 0 veriyordu
# — en kati kapimiz bir YAZIM HATASIYLA gevsiyordu, hicbir sey kirmizi yanmadan. Artik:
#   (a) kosumdan ONCE olcut_dogrula() TUM kayitlari suzer; tek bir gecersiz deger bile
#       surucuyu ORADA durdurur (hangi kayitta hangi deger oldugu yazilir),
#   (b) tuketim yerinde de "ne ESIT ne KAPSAR" hali SystemExit'tir (varsayilan dal YOK).
# Kabul: bir kaydin olcutu "Esit" yapilinca cikis 1 (once 0); olcut alani silinince cikis 1.

M1 = ("M1", "?anahtar= sorgu parametresi yolu GERI GELDI (isin bas sebebi)", [(
    """function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {""",
    """function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (sabitEsit(url.searchParams.get("anahtar") || "", env.YONET_ANAHTAR)) { return true; }
  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {""")],
      ["C1", "C16a", "C16b"])

M2 = ("M2", "sabitEsit FAIL-OPEN'a dondu (String(a || \"\") — bos girdide true)", [(
    """export function sabitEsit(a, b) {
  if (typeof a !== "string" || typeof b !== "string") { return false; }
  if (a.length === 0 || b.length === 0) { return false; }
  if (a.length !== b.length) { return false; }""",
    """export function sabitEsit(a, b) {
  a = String(a || "");
  b = String(b || "");
  if (a.length !== b.length) { return false; }""")],
      ["C21a", "C21b", "C21c"])

# yonet()'in secret kapisini POST dagitiminin ARKASINA alir.
# ⚠️ CAPA GUNCELLENDI: `/wa-siparis` blogu ozellik-kapali kapisi ile giris POST'unun
# ARASINA girdi, yani eski TEK PARCALI capa (gate + `const m` + giris POST'u bitisik)
# artik eslesmiyordu ve harness BAYAT duserek 25 mutantin hepsini olcusuz birakiyordu.
# M3'un NIYETI aynen korundu (secret kapisi giris POST'unun ARKASINA alinir); capa iki
# parcaya bolundu ki araya giren bloklardan BAGIMSIZ olsun.
_SIRA_TAKAS_KALDIR = (
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""",
    """  const m = request.method;""")
_SIRA_TAKAS_KOY = (
    """  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }""",
    """  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }
  if (!env.YONET_ANAHTAR) { return yon404(); }""")
# girisYap'in KENDI secret kapisini siler.
_ICKAPI_SIL = (
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
    """  const simdi = Date.now();""")

M3 = ("M3", "secret kapisi giris POST'unun ARKASINA alindi + girisYap'in kendi kapisi silindi",
      [_SIRA_TAKAS_KALDIR, _SIRA_TAKAS_KOY, _ICKAPI_SIL], ["C15a", "C22a", "C22e"])

M4 = ("M4", "girisEkrani'nda ikame FONKSIYONU yerine ikame DIZESI ($` enjeksiyonu)", [(
    """GIRIS_HTML.replace("__EYLEM__", () => yol)""",
    """GIRIS_HTML.replace("__EYLEM__", yol)""")],
      ["C20"])

M5 = ("M5", "giris HIZ SINIRI kaldirildi (kaba kuvvet serbest)", [(
    """  return girisSayac.adet >= GIRIS_TAVAN;
}""",
    """  return false;
}""")],
      ["C18a", "C18b"])

M6 = ("M6", "giris GOVDE UST SINIRI kaldirildi (sinirsiz ayristirma)", [(
    """  const bildirilen = parseInt(request.headers.get("Content-Length") || "", 10);
  if (Number.isFinite(bildirilen) && bildirilen > GIRIS_GOVDE_SINIRI) { return null; }
  if (!request.body) { return ""; }""",
    """  if (!request.body) { return ""; }"""),
    ("""    if (toplam > GIRIS_GOVDE_SINIRI) { try { await okuyucu.cancel(); } catch (e) {} return null; }
""", "")],
      ["C19b"])

M7 = ("M7", "cerez ADI tam esitligi -> naive includes (yakin-iska yetki alir)", [(
    """    if (parca.slice(0, esit).trim() !== CEREZ_ADI) { continue; }""",
    """    if (!parca.includes(CEREZ_ADI)) { continue; }""")],
      ["C5a"])

M8 = ("M8", "Set-Cookie'den HttpOnly dusuruldu (XSS oturum cerezini calabilir)", [(
    """const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Strict; Path=/";""",
    """const CEREZ_BAYRAK = "Secure; SameSite=Strict; Path=/";""")],
      ["C10a", "C12c"])

M9 = ("M9", "SameSite=Strict -> Lax (capraz-site gezinmede cerez gider)", [(
    """const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Strict; Path=/";""",
    """const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Lax; Path=/";""")],
      ["C10c", "C12e"])

K1 = ("K1", "KONTROL: sabitEsit'te yerel degisken adi degisti (davranis AYNI)", [(
    """  let fark = 0;
  for (let i = 0; i < a.length; i++) { fark |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return fark === 0;""",
    """  let farkBiti = 0;
  for (let i = 0; i < a.length; i++) { farkBiti |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return farkBiti === 0;""")],
      [])

K2 = ("K2", "KONTROL: girisYap'a yorum satiri eklendi (davranis AYNI)", [(
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  // kontrol mutanti: yalnizca yorum — davranis degismez.
  const simdi = Date.now();""")],
      [])

K3 = ("K3", "KONTROL: anahtarGecerli'de baslik/cerez kontrol SIRASI takas edildi", [(
    """  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {
    return true;
  }
  return sabitEsit(yonetCereziOku(request), env.YONET_ANAHTAR);""",
    """  if (sabitEsit(yonetCereziOku(request), env.YONET_ANAHTAR)) { return true; }
  return sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR);""")],
      [])

# ESKIDEN K4 (beyan edilmis SURVIVOR, YESIL beklentili). Iddia ikiye ayrilinca (C22a/C22b)
# bu katman TEK BASINA olculur oldu -> artik KIRMIZI beklentilidir. C22b'yi BEKLEMEZ:
# yonet()'in ust kapisi bu mutantta yerinde durdugu icin GET / hala 404 doner (dogru).
M10 = ("M10", "YALNIZ girisYap'in kendi secret kapisi silindi (savunma derinliginin IC katmani)",
       [_ICKAPI_SIL], ["C22a", "C22e"])

# --- OZELLIK-KAPALI (secret yok) KOLUNUN UC EKSENI -----------------------------------
# M11/M12/M13, eski tek-parca C15 iddiasi eksenlerine ayrilirken ARANAN "ayirt edici
# mutant"lardir. Ikisi ayirt edici CIKMADI (M12/M13) ama yine de GERCEK bozulmalardir ve
# surucude DURURLAR: hangi iddianin o ekseni tuttugunu KOSUMDA sabitlerler.

# M11 — C15a'nin AYIRT EDICI mutanti: kapilar SILINMEZ, ozellik-kapali KOL yeniden yazilir
# ("secret yoksa POST'ta da GET'teki gibi giris ekranini gosterelim"). Gercek zarar: ozellik
# KAPALIYKEN /yonet POST'u giris formu servis eder -> ucun varligi sizar. Kapi silen
# mutantlar bu ekseni dusuremiyordu (ust kapi silinse POST girisYap'a duser, ic kapi silinse
# ust kapi yakalar); kacis yolu buydu — bu yuzden C15a KENDI iddiasi olarak durur.
M11 = ("M11", "ozellik-kapali kol BIRLESTIRILDI: secret yok + POST / -> giris EKRANI (GET 404)",
       [("""export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""",
         """export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (!env.YONET_ANAHTAR) {
    return (altYol === "/" && m === "POST") ? girisEkrani(url) : yon404();
  }""")],
       ["C15a"])

# M12 — GOVDE ekseni, TEK KAYNAKTAN: kod 404 KORUNUR, yon404'un KENDISI HTML+<form> olur.
# AYIRT EDICI DEGIL (olculdu): yon404 tek kaynak oldugu icin hem girisYap'in kendi 404'unun
# govdesini (C22e) hem ust kapinin 404'unun govdesini (C22c) ayni anda bozar. Iki govde
# ekseninin AYRI AYRI ayirt edici mutantlari M14 (ust kapi) ve M19 (girisYap). M12 yine de
# durur: tek kaynagin bozulmasi GERCEK bir bozulmadir ve ikisinin BIRLIKTE dustugunu sabitler.
M12 = ("M12", "yon404 TEK KAYNAGININ govdesine <form> enjekte edildi (kod HALA 404)",
       [("""function yon404() { return yjson({ hata: "bulunamadi" }, 404); }""",
         """function yon404() {
  return new Response("<html><body><form action=\\"/ara\\"></form></body></html>", {
    status: 404,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}""")],
       ["C15c", "C22c", "C22e"])

# M13 — KOD ekseni, TUM ozellik-kapali GET'lerde: formsuz 200 doner (POST kolu 404 kalir).
# AYIRT EDICI DEGIL (olculdu): ust kapi TUM yollarda ortak oldugu icin /liste ucunun
# ozellik-kapali iddialarini (C6a/C6b) da dusurur. Kod ekseninin AYIRT EDICI mutanti
# M15'tir (yalniz `GET /`); C6a/C6b'nin ayirt edicileri M24/M25'tir (yalniz /liste, tek
# ordinal). M13 durur: genis bozulmanin genis kirmizi yaktigini sabitler — kirmizi kumesi
# {C15b,C22b,C6a,C6b} olarak OLCULDU ve capalandi (esit_kume).
M13 = ("M13", "ust kapi ozellik-kapali TUM GET'lerde formsuz 200 dondurur (POST kolu 404)",
       [("""export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""",
         """export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (!env.YONET_ANAHTAR) {
    return m === "GET" ? new Response("", { status: 200 }) : yon404();
  }""")],
       ["C15b", "C22b", "C6a", "C6b"])

# M14 — ust kapi KENDI 404'unu uretir ve govdesine <form> girer; KOD 404 KALIR, yon404 TEK
# KAYNAGINA DOKUNULMAZ (o yuzden C22e/girisYap govdesi ayakta). Gercek zarar: ozellik
# KAPALIYKEN panel kokunde giris formu servis edilir -> ucun varligi sizar.
# ⚠️ ESKIDEN tek_eksen(ESIT) BEYAN EDILIYORDU ve BEYAN BAYATLADI: 15. bloktaki ozellik-kapali
# sonda geri konunca ust kapiden gecen root GET SAYISI 1'den 2'ye cikti, mutant her ikisini
# de kirletiyor -> kirmizi kume {C15c, C22c}. Yeni ESIT olcutu bunu ILK kosumda yakaladi
# (eski KAPSAR olcutunde sessizce PASS verirdi). Artik GENIS: ekseni iki cagri ordinalinde
# birden dusuruyor. Tek-ordinal ayirt ediciler M21 (ilk cagri) ve M23 (ikinci+ cagri).
M14 = ("M14", "ust kapinin KENDI 404 govdesine <form> girdi (kod 404, yon404 TEK KAYNAGI saglam)",
       [("""export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }""",
         """export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) {
    return new Response("<html><body><form action=\\"/ara\\"></form></body></html>", {
      status: 404,
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
    });
  }""")],
       ["C15c", "C22c"])

# M15 — ust kapi YALNIZ `GET /`te formsuz 200 doner; /liste kolu 404 kalir (C6a/C6b yesil),
# POST kolu 404 kalir (C15a yesil), govde form icermez (govde eksenleri yesil). Gercek zarar:
# ozellik kapaliyken panel kokunun VARLIGI 200 ile dogrulanir (404 "yok" demeliydi).
# ⚠️ M14 ile AYNI SEBEPTEN tek_eksen BEYANI BAYATLADI (sonda geri konunca iki root GET oldu):
# kirmizi kume {C15b, C22b}. Tek-ordinal ayirt ediciler M20 (ilk cagri) ve M22 (ikinci+).
M15 = ("M15", "ust kapi YALNIZ `GET /`te formsuz 200 doner (diger yollar + POST 404 kalir)",
       [("""export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""",
         """export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (!env.YONET_ANAHTAR) {
    return (altYol === "/" && m === "GET") ? new Response("", { status: 200 }) : yon404();
  }""")],
       ["C15b", "C22b"])

# M16 — 🔴 CAGRI SIRASI SINIFI: ozellik-kapali panel koku ILK GET'te temiz 404 doner, IKINCI
# ve sonraki GET'te giris ekranini sizdirir. Modul duzeyi durum Workers'ta istekler ARASI
# yasar (bu dosyada `girisSayac` zaten oyle), yani bu sinif hayali degil.
# NEDEN IKI SONDA GEREKIR: alt kume ozellik-kapali panel kokunu IKI kez yokluyor — once 15.
# blokta (C15b/C15c), sonra 22. blokta (C22b/C22c). Bir tur once "C22b ile ayni yuklem" diye
# 15. bloktaki sonda SILINMISTI; o halde bu mutant alt kumeyi YESIL geciyordu (olculdu).
# Sondayi geri koyunca ILK cagri temiz kalir, IKINCI cagri sizar -> C22b + C22c kirmizi.
# Bu mutant, sondanin bir daha "gereksiz kopya" diye silinmesini engelleyen nobetcidir.
M16 = ("M16", "ozellik-kapali panel koku IKINCI+ GET'te giris ekrani sizdirir (ILK GET temiz)",
       [("""export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""",
         """let _kapaliKokSayac = 0;
export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (!env.YONET_ANAHTAR) {
    if (altYol === "/" && m === "GET" && ++_kapaliKokSayac > 1) { return girisEkrani(url); }
    return yon404();
  }""")],
       ["C22b", "C22c"])

# --- girisYap'IN KENDI KAPISININ UC EKSENI (C22a / C22d / C22e) ----------------------
# Ucu de AYIRT EDICI: her mutant kapiyi SILMEZ, yalnizca TEK bir ekseni bozar; digerleri
# saglam kaldigi icin alt kumede TEK iddia kirmizi yanar. (Ust kapi yolda olmadigindan —
# C22 blogu girisYap'i DOGRUDAN cagirir — bu mutantlar ust kapi iddialarini etkilemez.)

# M17 — KOD ekseni: kapi 404 yerine bos/cerezsiz 200 doner. Govde formsuz, Set-Cookie yok.
M17 = ("M17", "girisYap kendi kapisi 404 yerine formsuz/cerezsiz 200 doner (KOD ekseni)",
       [("""  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
         """  if (!env.YONET_ANAHTAR) {
    return new Response("", { status: 200, headers: { "Cache-Control": "no-store" } });
  }
  const simdi = Date.now();""")],
       ["C22a"])

# M18 — CEREZ ekseni: kapi DOGRU kodu (404) ve formsuz govdeyi doner AMA oturum cerezini
# BASAR. Tam da bu kapinin engelledigi zarar: ANAHTARSIZ oturum cerezi kurulumu. Bir tur
# once bu eksen icin "ayirt edici mutant ARANMADI" diye kayit dusulmustu; arandi, BULUNDU.
M18 = ("M18", "girisYap kendi kapisi 404 + formsuz govde doner AMA Set-Cookie BASAR (CEREZ ekseni)",
       [("""  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
         """  if (!env.YONET_ANAHTAR) {
    return new Response(JSON.stringify({ hata: "bulunamadi" }), {
      status: 404,
      headers: { "Content-Type": "application/json; charset=utf-8",
                 "Cache-Control": "no-store", "Set-Cookie": yonetCereziKur("1") },
    });
  }
  const simdi = Date.now();""")],
       ["C22d"])

# M19 — GOVDE ekseni: kapi KENDI 404'unu HTML+<form> olarak uretir; kod 404 kalir, cerez
# basilmaz ve yon404 TEK KAYNAGINA DOKUNULMAZ (ona dokunmak C22c'yi de dusururdu — M12).
M19 = ("M19", "girisYap kendi kapisinin 404 govdesi HTML+<form> olur (GOVDE ekseni)",
       [("""  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
         """  if (!env.YONET_ANAHTAR) {
    return new Response("<html><body><form action=\\"/ara\\"></form></body></html>", {
      status: 404,
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  const simdi = Date.now();""")],
       ["C22e"])


# --- ORDINAL-DUYARLI AYIRT EDICILER (M20-M23) ----------------------------------------
# Ozellik-kapali panel koku alt kumede IKI kez yoklaniyor: ILK GET (C15b/C15c) ve IKINCI GET
# (C22b/C22c). M14/M15 gibi "her cagride" bozan mutantlar iki ordinali BIRDEN dusurur, yani
# tek bir iddiayi ayirt EDEMEZ. Asagidaki dort mutant ordinali secer ve TEK ekseni bozar —
# dort iddianin her birinin KENDI ayirt edici mutanti olsun diye. Ikisi de gercek sinif:
#   ILK cagri     = soguk baslangic / tembel ilklendirme (modul durumu ilk istekte hazir degil),
#   IKINCI+ cagri = istekler arasi yasayan modul durumunun kirlenmesi (bkz. `girisSayac`).
_KOK_ANCHOR = ("""export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""")
_FORMSUZ_200 = ("""new Response("", { status: 200, """
                """headers: { "Cache-Control": "no-store" } })""")
_FORMLU_404 = ("""new Response("<html><body><form action=\\"/ara\\"></form></body></html>", """
               """{ status: 404, headers: { "Content-Type": "text/html; charset=utf-8", """
               """"Cache-Control": "no-store" } })""")


def _kok_ordinali(kod, aciklama, kosul, yanit, beklenen):
    """Ozellik-kapali panel koku GET'lerini sayar ve YALNIZ <kosul>u saglayan cagride
    <yanit>i dondurur; diger her sey bugunku gibi yon404()'tur."""
    return (kod, aciklama, [(_KOK_ANCHOR, """let _kokSayac = 0;
export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (!env.YONET_ANAHTAR) {
    if (altYol === "/" && m === "GET" && """ + kosul + """) { return """ + yanit + """; }
    return yon404();
  }""")], beklenen)


M20 = _kok_ordinali(
    "M20", "YALNIZ ILK ozellik-kapali root GET formsuz 200 doner (soguk baslangic; KOD ekseni)",
    "++_kokSayac === 1", _FORMSUZ_200, ["C15b"])
M21 = _kok_ordinali(
    "M21", "YALNIZ ILK ozellik-kapali root GET 404+<form> doner (soguk baslangic; GOVDE ekseni)",
    "++_kokSayac === 1", _FORMLU_404, ["C15c"])
M22 = _kok_ordinali(
    "M22", "YALNIZ IKINCI+ ozellik-kapali root GET formsuz 200 doner (KOD ekseni)",
    "++_kokSayac > 1", _FORMSUZ_200, ["C22b"])
M23 = _kok_ordinali(
    "M23", "YALNIZ IKINCI+ ozellik-kapali root GET 404+<form> doner (GOVDE ekseni)",
    "++_kokSayac > 1", _FORMLU_404, ["C22c"])


# --- /liste KOLUNUN ORDINALLERI (M24/M25) — C6a/C6b'nin AYIRT EDICILERI -------------
# 🔴 KAYIT DUZELTMESI (2 Agu, KENDIM OLCTUM): C6a/C6b'nin ordinal ekseni icin surucude
# HICBIR ayirt edici mutant kaydi YOKTU — C6a/C6b yalnizca GENIS mutantlarin (M13) yan
# kirmizisi olarak goruluyordu, yani "bu iki iddia tek basina neyi tutuyor" OLCULMEMISTI.
# Arandi, BULUNDU ve iki kez arka arkaya olculdu: her biri TEK kirmizi yakiyor, iddia
# sayisi 70/70 (cokme yok). Yapisal sebep: 6. blok ozellik-kapali /liste kolunu IKI AYRI
# cagriyla yokluyor (once dogru CEREZ ile = C6a, sonra dogru BASLIK ile = C6b), yani kol
# hem tasiyici hem de CAGRI ORDINALI ekseninde nobetli.
# GERCEK ZARAR (bu yuzden govdesi bos 200 degil, dogrudan liste()): ozellik KAPALIYKEN
# /yonet/liste siparis listesini — musteri adi/tel/eposta/adres — anahtarsiz servis eder.
# ⚠️ 6. bloktaki IKI cagridan birini "tasiyici farki, gerisi kopya" diye SILME: silinen sey
# yuklem degil CAGRI SAYISIDIR ve asagidaki iki mutanttan biri o anda YESIL gecmeye baslar.
def _liste_ordinali(kod, aciklama, kosul, beklenen):
    """Ozellik-kapali /liste GET'lerini sayar ve YALNIZ <kosul>u saglayan cagride gercek
    liste()'yi servis eder; diger her sey bugunku gibi yon404()'tur."""
    return (kod, aciklama, [(_KOK_ANCHOR, """let _listeSayac = 0;
export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (!env.YONET_ANAHTAR) {
    if (altYol === "/liste" && m === "GET" && """ + kosul + """) { return liste(env, url); }
    return yon404();
  }""")], beklenen)


M24 = _liste_ordinali(
    "M24", "YALNIZ ILK ozellik-kapali /liste GET'i siparis listesini servis eder (cerez kolu)",
    "++_listeSayac === 1", ["C6a"])
M25 = _liste_ordinali(
    "M25", "YALNIZ IKINCI+ ozellik-kapali /liste GET'i siparis listesini servis eder (baslik kolu)",
    "++_listeSayac > 1", ["C6b"])


# --- KABA KUVVET YAVASLATICISI (M26) — C23'un AYIRT EDICI mutanti ---------------------
# 🔴 2 Agu'a kadar OLCULMEMIS EKSEN. Bagimsiz curutucu olctu: `GIRIS_GECIKME_MS` 250 -> 0
# yapilinca (basarisiz/bloke her denemedeki sabit bekleme TAMAMEN kalkar) alt kumede HICBIR
# iddia kirmizi yanmiyordu — SURVIVOR (olculdu: cikis 0, kirmizi 0, iddia 70/70). Yani panelin
# TEK ve PAYLASILAN anahtarini kaba kuvvete karsi yavaslatan katman NOBETSIZDI: biri bu sabiti
# "testler zaten yavasliyor" gerekcesiyle sifirlasa hicbir kapi kirmizi yanmazdi.
# Alt kumeye C23 eklendi (istenen setTimeout gecikmesi >= 100 ms; ALT SINIR, ust sinir YOK,
# duvar saati DEGIL) ve bu mutant onun ayirt edicisidir: kirmizi kume TAM OLARAK {C23}.
M26 = ("M26", "GIRIS_GECIKME_MS 250 -> 0 (kaba kuvvet yavaslaticisi TAMAMEN kalkti)",
       [("const GIRIS_GECIKME_MS = 250;", "const GIRIS_GECIKME_MS = 0;")],
       ["C23"])


def tek_eksen(m):
    """TEK iddia bekleyen AYIRT EDICI mutant -> olcut kume ESITLIGI (fazlalik = KUSUR).
    "Yalniz su iddiayi yakar" hukmu ANCAK boyle nobet altindadir; KAPSAR olcutu fazladan
    kirmiziyi sessizce gecirir."""
    return m + (OLCUT_ESIT,)


def esit_kume(m):
    """Birden COK iddia bekleyen ama kirmizi kumesi TAM OLARAK beyani KADAR OLCULEN mutant.
    tek_eksen ile AYNI olcuttur (tek kaynak: OLCUT_ESIT); ayri ad yalnizca okuyucuya
    "bu 'tek eksen' iddiasi DEGIL, olculmus kume esitligi capasi" der.
    🔴 ESIT'e ancak kirmizi kumesi KARARLI olculen kayit alinir: tekrarli kosumda ayni
    kume cikmali. (Bu dosyada kayitlar birbirini KIRLETEMEZ: `kos()` her kayit icin AYRI
    bir node SURECI baslatir -> modul duzeyi durum — `girisSayac` gibi — her kosumda
    sifirdan baslar. Sira duyarliligi TEK bir kosumun ICINDEDIR, kayitlar arasinda degil.)"""
    return m + (OLCUT_ESIT,)


def genis(m):
    """Kirmizi kumesi beyanindan GENIS olculen/beklenen bozulma -> olcut KAPSAMA
    (beklenen ⊆ kirmizi); ek kirmizi capa yapilmaz. Kararliligi ISPATLANAMAYAN kayit da
    BURADA kalir: yanlis-kirmizinin maliyeti, kacirilan capadan buyuktur."""
    return m + (OLCUT_KAPSAR,)


def kontrol(m):
    """DAVRANIS-KORUYAN refaktor -> YESIL kalmali. 🔴 SINIF BEYANIDIR: eskiden "kontrol"
    olmak `beklenen`in BOS birakilmasindan TURETILIYORDU, yani bir SURVIVOR'i (yakalanmayan
    GERCEK bozulma) beklenen=[] ile kaydedip bedava yesil almak mumkundu (olculdu). Artik
    kirmizi-beklentili kaydin `beklenen`i bos OLAMAZ ve kontrol kaydininki bos OLMAK
    ZORUNDADIR; ikisi de kosumdan ONCE fail-closed suzulur."""
    return m + (OLCUT_KONTROL,)


# 🔴 SARMALAYICI SECIMI OLCULEREK YAPILDI (2 Agu). 14 KAPSAR kaydinin kirmizi kumesi iki
# kez arka arkaya olculdu: 11'i beyanina BIREBIR ESIT cikti (kararli) -> capa alindi
# (esit_kume). Ucu GERCEKTEN kapsama istiyor, KAPSAR kaldi ve sebebi kaydinda yazili:
#   M6 -> +C18a,C18b  (govde siniri kalkinca sinir-ustu POST'lar hiz sayacini besliyor)
#   M8 -> +C10f       (CEREZ_BAYRAK tek kaynak: yonetCereziSil() ayni bayraklari tasiyor)
#   M9 -> +C10f       (ayni sebep)
MUTANTLAR = [
    esit_kume(M1), esit_kume(M2), esit_kume(M3), esit_kume(M4), esit_kume(M5),
    genis(M6),                       # OLCULDU: +C18a,C18b — kapsama GERCEKTEN gerekli
    esit_kume(M7),
    genis(M8), genis(M9),            # OLCULDU: +C10f — kapsama GERCEKTEN gerekli
    esit_kume(M10),
    tek_eksen(M11),
    esit_kume(M12), esit_kume(M13),
    esit_kume(M14), esit_kume(M15),  # BEYAN BAYATLAMISTI (2 ordinal); kume simdi olculu
    tek_eksen(M16),                  # iddiasinin PARCASI: C15b/C15c YESIL kalir
    tek_eksen(M17), tek_eksen(M18), tek_eksen(M19),
    tek_eksen(M20), tek_eksen(M21), tek_eksen(M22), tek_eksen(M23),
    tek_eksen(M24), tek_eksen(M25),
    tek_eksen(M26),                  # OLCULMEMIS eksenin (kaba kuvvet gecikmesi) nobetcisi
    kontrol(K1), kontrol(K2), kontrol(K3),
]

# 🔴 VAKUM YESILI KAPISI (2 Agu, olculdu). MUTANTLAR bosaltilinca surucu "0 kosum" yapip
# `TUM MUTANTLAR YAKALANDI ✅` basiyor ve cikis 0 veriyordu; tek kayit birakilinca da. Yani
# HICBIR SEY olculmemisken "hepsi yesil" — bu turda kapattigimiz kalibin ta kendisi.
# ALT SINIR IKI BAGIMSIZ KAYNAKTAN turetilir (redundans bilincli):
#   (1) ENVANTER — modul duzeyinde TANIMLI her mutant kaydi (M<n>/K<n> adli 4 alanli demet)
#       MUTANTLAR'da KAYITLI olmak zorundadir. Tek kaynak MODULUN KENDISIDIR: yeni mutant
#       tanimlandiginda alt sinir KENDILIGINDEN yukselir, elle guncellenecek sayi YOKTUR
#       (bakim yuku sifir). Ayrica "mutanti tanimladim ama listeye eklemeyi UNUTTUM"
#       sessiz deligini de kapatir — bu delik listeyi bosaltmaktan daha olasidir.
#   (2) ASGARI_KAYIT — envanterden BAGIMSIZ bir TABAN. (1) tek basina yeterli DEGIL: kayit
#       TANIMI ile KAYDI birlikte silinirse envanter kucuk kalir ve yine sessizce gecerdi.
#       Bu sayi TAVAN DEGIL TABANDIR: kayit EKLENDIKCE ARTMASI GEREKMEZ (bakim yuku yok),
#       yalnizca toplu silmeyi yakalar. Dusurulmesi ancak KASITLI bir kapsam kararidir ve
#       o kararin bu satirda gerekcelenmesi gerekir.
# Ayrica ayni kod IKI KEZ kaydedilirse (kopyala-yapistir) sayi sisirilebilirdi: kod
# BENZERSIZLIGI de burada dogrulanir.
ASGARI_KAYIT = 29        # bugun 29 (M1-M26 + K1-K3). TABAN; artirmak ZORUNLU degil.
ASGARI_KIRMIZI = 20      # kirmizi-beklentili kayit tabani (bugun 26)
ASGARI_KONTROL = 3       # K1/K2/K3 — "her sey kirmizi" diye ucuza gecmeyi engelleyen kayitlar


def kayit_envanteri(kapsam):
    """Modul duzeyinde TANIMLI mutant kayitlarini bulur: adi `M<n>`/`K<n>` olan, 4 alanli
    ve ilk alani KENDI ADIYLA ayni olan demetler. (Sarmalayicidan gecmis 5 alanli kayitlar
    burada DEGIL, MUTANTLAR'dadir.)"""
    ad_re = re.compile(r"^[MK]\d+$")
    envanter = {}
    ad_sapmasi = []
    for ad, deger in kapsam.items():
        if not ad_re.match(ad):
            continue
        if not (isinstance(deger, tuple) and len(deger) == 4 and isinstance(deger[0], str)):
            continue
        if deger[0] != ad:
            ad_sapmasi.append("%s kaydinin kodu %r (ad ile kod AYRISMIS — kopyala-yapistir "
                              "kazasi mutanti gorunmez kilar)" % (ad, deger[0]))
            continue
        envanter[deger[0]] = ad
    return envanter, ad_sapmasi


def olcut_dogrula(mutantlar, kapsam=None):
    """🔴 FAIL-CLOSED KAYIT SUZGECI — kosumdan ONCE calisir.
    Kayit sekli (5 alan), olcut degeri, olcut<->beklenen TUTARLILIGI ve KAYIT ENVANTERI
    denetlenir. Herhangi biri tutmuyorsa surucu varsayilana DUSMEZ: kusur listesi doner ve
    cagiran KIRMIZI yakip durur.
    Sebepler (hepsi OLCULDU):
      - olcut bir dize alani; yanlis yazilmasi (or. "Esit") mutanti sessizce en GEVSEK
        olcute dusuruyordu,
      - sinif `beklenen`in BOSLUGUNDAN turetiliyordu; bir SURVIVOR beklenen=[] ile "kontrol"
        diye kaydedilince BEDAVA YESIL aliyordu,
      - liste bosaltilinca / tek kayda dusurulunce surucu "0 kosum" yapip YESIL basiyordu."""
    kusurlar = []
    gorulen = {}
    for sira, kayit in enumerate(mutantlar):
        etiket = "kayit #%d" % sira
        if not isinstance(kayit, tuple) or len(kayit) != 5:
            kusurlar.append(
                "%s: 5 alanli demet DEGIL (uzunluk=%s, ilk alan=%r) — olcut sarmalayicisi "
                "(tek_eksen/esit_kume/genis/kontrol) UNUTULMUS olabilir"
                % (etiket, len(kayit) if hasattr(kayit, "__len__") else "?",
                   kayit[0] if hasattr(kayit, "__getitem__") and len(kayit) else kayit))
            continue
        kod, _aciklama, degisimler, beklenen, olcut = kayit
        etiket = "kayit #%d [%s]" % (sira, kod)
        if kod in gorulen:
            kusurlar.append("%s: kod MUKERRER (once #%d) — ayni kodu iki kez kaydetmek "
                            "kayit sayisini SISIRIR" % (etiket, gorulen[kod]))
        gorulen[kod] = sira
        if olcut not in OLCUTLER:
            kusurlar.append(
                "%s: GECERSIZ olcut %r — taninan degerler: %s. Varsayilana DUSULMEZ; "
                "sarmalayiciyi kullan (tek_eksen/esit_kume -> %s, genis -> %s, kontrol -> %s)"
                % (etiket, olcut, ", ".join(repr(o) for o in OLCUTLER),
                   OLCUT_ESIT, OLCUT_KAPSAR, OLCUT_KONTROL))
        # 🔴 SINIF <-> BEKLENEN TUTARLILIGI: sinif ARTIK BEYAN EDILIR, `beklenen`in
        # boslugundan TURETILMEZ. Iki yon de fail-closed'dur.
        elif olcut in KIRMIZI_OLCUTLER and not beklenen:
            kusurlar.append(
                "%s: KIRMIZI-beklentili (olcut=%s) ama `beklenen` BOS — bu kayit hicbir "
                "iddiayi isaretlemez. GERCEK bir bozulmayi bos beklenenle kaydetmek onu "
                "'kontrol' diye AKLAR (survivor bedava yesil gecer). Ya beklenen iddia "
                "kodlarini YAZ, ya da davranis GERCEKTEN korunuyorsa kontrol() kullan."
                % (etiket, olcut))
        elif olcut == OLCUT_KONTROL and beklenen:
            kusurlar.append(
                "%s: KONTROL kaydi (davranis-koruyan refaktor) ama `beklenen` DOLU (%s) — "
                "kontrol kaydinin kirmizi beklentisi OLAMAZ; kirmizi bekliyorsan "
                "tek_eksen/esit_kume/genis kullan" % (etiket, ",".join(beklenen)))
        if not degisimler:
            kusurlar.append("%s: mutasyon listesi BOS — bu kayit hicbir sey olcmez" % etiket)

    # --- ALT SINIR: "hic olcmeden yesil" YOK ------------------------------------------
    kirmizi_adet = sum(1 for m in mutantlar
                       if isinstance(m, tuple) and len(m) == 5 and m[4] in KIRMIZI_OLCUTLER)
    kontrol_adet = sum(1 for m in mutantlar
                       if isinstance(m, tuple) and len(m) == 5 and m[4] == OLCUT_KONTROL)
    if len(mutantlar) < ASGARI_KAYIT:
        kusurlar.append(
            "KAYIT SAYISI ALT SINIRIN ALTINDA: %d kayit bulundu, taban %d. Surucu bos/kirpik "
            "listeyle 'TUM MUTANTLAR YAKALANDI' DEMEZ — hicbir sey olculmemisken yesil "
            "yanmak, bu nobetcinin kapatmak icin var oldugu kalibin ta kendisidir."
            % (len(mutantlar), ASGARI_KAYIT))
    if kirmizi_adet < ASGARI_KIRMIZI:
        kusurlar.append("KIRMIZI-BEKLENTILI KAYIT SAYISI ALT SINIRIN ALTINDA: %d bulundu, "
                        "taban %d" % (kirmizi_adet, ASGARI_KIRMIZI))
    if kontrol_adet < ASGARI_KONTROL:
        kusurlar.append("KONTROL KAYDI SAYISI ALT SINIRIN ALTINDA: %d bulundu, taban %d "
                        "(kontrol kayitlari olmadan surucu 'her sey kirmizi' diye ucuza "
                        "gecebilir)" % (kontrol_adet, ASGARI_KONTROL))

    # --- ENVANTER: TANIMLI her kayit KAYITLI mi? (alt sinirin ikinci, bagimsiz kaynagi) --
    if kapsam is not None:
        envanter, ad_sapmasi = kayit_envanteri(kapsam)
        kusurlar.extend(ad_sapmasi)
        kayitli = set(gorulen)
        eksik = sorted(set(envanter) - kayitli,
                       key=lambda k: (k[0], int(k[1:]) if k[1:].isdigit() else 0))
        if eksik:
            kusurlar.append(
                "TANIMLI AMA KAYITSIZ MUTANT(LAR): %s — modulde tanimli %d kayittan %d'i "
                "MUTANTLAR listesinde YOK. Bu kayitlar HICBIR SEY olcmez; alt sinir "
                "MODULUN KENDISINDEN turer (elle guncellenecek sayi yoktur)."
                % (", ".join(eksik), len(envanter), len(eksik)))
    return kusurlar


# ------------------------------------------------------------------ ayna
def ayna_kur(hedef_kok):
    """<hedef_kok> = kabul testinin ihtiyac duydugu agacin TAM KOPYASI.
    KAYNAGA GIDEN SYMLINK YOKTUR (symlinks=False + follow_symlinks=True)."""
    for gorece in AYNA_DIZIN:
        shutil.copytree(os.path.join(ROOT, gorece), os.path.join(hedef_kok, gorece),
                        symlinks=False, ignore=KOPYA_HARIC, ignore_dangling_symlinks=True)
    for gorece in AYNA_DOSYA:
        hedef = os.path.join(hedef_kok, gorece)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, gorece), hedef, follow_symlinks=True)


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        for ad in altlar + dosyalar:
            y = os.path.join(dizin, ad)
            if os.path.islink(y):
                bulunan.append(os.path.relpath(y, kok))
    return bulunan


def mutasyonla(pristine, degisimler, kod):
    """Mutasyonu metne uygular. Dayanak bulunamazsa HARNESS BAYATTIR -> gurultulu duser
    (sessizce 'olctum' demek, hic olcmemekten kotudur)."""
    metin = pristine
    for eski, yeni in degisimler:
        if eski not in metin:
            raise SystemExit(
                "HARNESS BAYAT (%s): shop/src/yonet.js icinde mutasyon dayanagi "
                "bulunamadi:\n%r\n(kod degismis olabilir — mutasyonu guncelle; yoksa bu "
                "harness HICBIR SEY olcmuyor demektir)" % (kod, eski[:200]))
        yeni_metin = metin.replace(eski, yeni, 1)
        if yeni_metin == metin:
            raise SystemExit("HARNESS BAYAT (%s): mutasyon metni DEGISTIRMIYOR" % kod)
        metin = yeni_metin
    return metin


IDDIA_RE = re.compile(r"^IDDIA SAYISI:\s*(\d+)\s*$", re.M)
KIRMIZI_RE = re.compile(r"❌ KALDI\s+(\S+)")


def kos(ayna, metin):
    """Ayna icindeki yonet.js'i <metin> ile yazar ve alt kumeyi kosar.
    Doner: (cikis_kodu, iddia_sayisi|None, kirmizi_kodlar, kirmizi_satirlar, cikti_kuyrugu)"""
    with open(os.path.join(ayna, "shop", "src", "yonet.js"), "w", encoding="utf-8") as f:
        f.write(metin)
    r = subprocess.run([NODE, os.path.join(ayna, "shop", "test", "kabul.js"), "--yonet-cerez"],
                       cwd=ayna, capture_output=True, text=True, timeout=300)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    satirlar = [s.strip() for s in cikti.splitlines() if "❌ KALDI" in s]
    kodlar = KIRMIZI_RE.findall(cikti)
    return r.returncode, iddia, kodlar, satirlar, cikti[-1600:]


def main():
    print("YONET ANAHTAR/CEREZ MUTASYON HARNESS'I — `node shop/test/kabul.js --yonet-cerez`")
    if NODE is None:
        raise SystemExit("node bulunamadi (PATH) — bu harness node ister.")
    if not os.path.isfile(HEDEF):
        raise SystemExit("shop/src/yonet.js yok: %s" % HEDEF)

    canli_once = sha(HEDEF)
    with open(HEDEF, encoding="utf-8") as f:
        pristine = f.read()
    print("  hedef: shop/src/yonet.js  sha256=%s…  (%d bayt)"
          % (canli_once[:16], len(pristine.encode("utf-8"))))

    # --- 0a) KAYIT SUZGECI: gecersiz olcut / sinif celiskisi / bos-kirpik liste = KIRMIZI
    # Ayna kurulmadan ONCE kosar: bozuk ya da BOS kayitla yapilan kosum "olculdu" DEGILDIR.
    print("\n0a) OLCUT + SINIF + ALT SINIR KAYITLARI (fail-closed)")
    envanter, _sapma = kayit_envanteri(globals())
    kusurlar = olcut_dogrula(MUTANTLAR, globals())
    check("her kayit 5 alanli, olcutu taninan (%s), sinif<->beklenen tutarli, "
          "TANIMLI kayitlarin hepsi KAYITLI ve sayilar taban ustunde"
          % ", ".join(OLCUTLER), not kusurlar,
          "%d kayit denetlendi (modulde TANIMLI %d; taban %d)%s"
          % (len(MUTANTLAR), len(envanter), ASGARI_KAYIT,
             "" if not kusurlar else "; %d KUSUR" % len(kusurlar)))
    if kusurlar:
        for k in kusurlar:
            print("     ⚠️ " + k)
        print("\n  🔴 KAYIT KUSURU: surucu ne en gevsek olcute SESSIZCE DUSER, ne de BOS/"
              "KIRPIK listeyle 'TUM MUTANTLAR YAKALANDI' der. Kayitlari duzelt; duzeltilene "
              "kadar bu harness HICBIR SEY olcmus SAYILMAZ.")
        return 1

    ayna = tempfile.mkdtemp(prefix="yonet-cerez-mutasyon-")
    try:
        ayna_kur(ayna)

        # --- 0b) AYNA DOKUNULMAZLIGI: kaynaga giden fiziksel yol var mi? ------------
        print("\n0b) AYNA DOKUNULMAZLIGI")
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))
        ayna_hedef = os.path.join(ayna, "shop", "src", "yonet.js")
        check("aynadaki yonet.js gecici dizinde (realpath kaynak agacin DISINDA)",
              os.path.realpath(ayna_hedef).startswith(os.path.realpath(ayna)) and
              os.path.realpath(ayna_hedef) != os.path.realpath(HEDEF),
              os.path.realpath(ayna_hedef))

        # --- 1) TABAN: mutasyonsuz ayna YESIL olmali; iddia sayisi BURADA olculur ---
        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, _t_kod, t_satir, t_kuyruk = kos(ayna, pristine)
        taban_ok = check("taban kosumu YESIL (cikis 0, kirmizi 0)",
                         t_rc == 0 and not t_satir,
                         "cikis=%d kirmizi=%d %s" % (t_rc, len(t_satir),
                                                     t_satir[0][:90] if t_satir else ""))
        if not taban_ok:
            print("\n  --- taban kosumunun ciktisi (son 1600 karakter) ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: ya ayna agaci EKSIK (AYNA_DIZIN/AYNA_DOSYA "
                  "guncellenmeli) ya da alt kume gercekten bozuk. Mutant kosumlari "
                  "ANLAMSIZ olurdu — durduruluyor.")
            return 1
        check("taban IDDIA SAYISI okunabildi (SONUC satiri basildi)",
              t_iddia is not None, "iddia=%s" % t_iddia)
        if t_iddia is None:
            return 1
        print("   TABAN IDDIA SAYISI = %d  (capa DEGIL: kosumda olculdu; mutantlar bu "
              "sayiyla kiyaslanir)" % t_iddia)
        check("taban kosumundan sonra canli yonet.js DEGISMEDI (sha256)",
              sha(HEDEF) == canli_once)

        # --- 2) MUTASYON BATARYASI -------------------------------------------------
        print("\n2) MUTASYON BATARYASI — %d kosum (%d kirmizi-beklentili [%d ESIT olcutlu], "
              "%d kontrol; taban: %d kayit / %d kirmizi / %d kontrol)"
              % (len(MUTANTLAR),
                 sum(1 for m in MUTANTLAR if m[4] in KIRMIZI_OLCUTLER),
                 sum(1 for m in MUTANTLAR if m[4] == OLCUT_ESIT),
                 sum(1 for m in MUTANTLAR if m[4] == OLCUT_KONTROL),
                 ASGARI_KAYIT, ASGARI_KIRMIZI, ASGARI_KONTROL))
        matris = []
        for kod, aciklama, degisimler, beklenen, olcut in MUTANTLAR:
            metin = mutasyonla(pristine, degisimler, kod)
            rc, iddia, kirmizi_kod, kirmizi, kuyruk = kos(ayna, metin)
            sayi_ok = (iddia == t_iddia)
            # 🔴 SINIF KAYITTAN OKUNUR (`beklenen` BOS MU diye BAKILMAZ): "kontrol" bir
            # BEYANDIR. Eski `if beklenen:` dali, beklenen'i bos birakilan GERCEK bir
            # bozulmayi sessizce kontrol sinifina dusuruyordu (olculdu: survivor bedava
            # yesil). olcut_dogrula bu hali zaten kosumdan ONCE reddeder; buradaki dal da
            # ondan BAGIMSIZ olarak sinifi beyandan okur (redundans bilincli).
            if olcut in KIRMIZI_OLCUTLER:
                eksik = [b for b in beklenen if b not in kirmizi_kod]
                # ESIT olcutu: BEKLENENIN USTUNE cikan her kirmizi de KUSURDUR. "Bu mutant
                # yalniz su iddiayi yakar" hukmu ancak boyle nobet altindadir; KAPSAR
                # olcutunde fazlalik sessizce gecerdi.
                # 🔴 VARSAYILAN DAL YOK: taninmayan olcut burada da DURDURUR (olcut_dogrula
                # zaten suzer; bu ikinci kapi, listeyi kosum aninda uretecek bir gelecek
                # degisiklikte de fail-closed kalinsin diyedir).
                if olcut == OLCUT_ESIT:
                    fazla = sorted(set(kirmizi_kod) - set(beklenen))
                elif olcut == OLCUT_KAPSAR:
                    fazla = []
                else:
                    raise SystemExit(
                        "OLCUT TANINMIYOR (%s): %r — taninan degerler: %s. Surucu "
                        "VARSAYILANA DUSMEZ (fail-closed)."
                        % (kod, olcut, ", ".join(repr(o) for o in OLCUTLER)))
                gecti = sayi_ok and rc == 1 and bool(kirmizi) and not eksik and not fazla
                detay = ("cikis=%d iddia=%s/%d kirmizi=%d olcut=%s isaret=%s"
                         % (rc, iddia, t_iddia, len(kirmizi), olcut,
                            "TAM" if not eksik else ("EKSIK:" + ",".join(eksik))))
                if fazla:
                    detay += ("  ⚠️ ESIT OLCUTU: BEKLENMEYEN FAZLA KIRMIZI -> " +
                              ",".join(fazla) + " (bu mutant 'ayirt edici/tek eksen' diye "
                              "BEYAN EDILMISTI; ya beyan ya iddia yanlis)")
                if not sayi_ok:
                    detay += ("  ⚠️ IDDIA SAYISI TUTMUYOR -> mutant testi COKERTMIS "
                              "olabilir; bu 'kirmizi' OLCUM DEGIL")
                beklenti = "KIRMIZI/" + olcut
            elif olcut == OLCUT_KONTROL:
                # KONTROL kaydi da DOGRULANIR: yesil KALMALI (tek bir kirmizi bile KUSUR)
                # ve iddia sayisi taban ile ayni olmali (cokme "yesil" ile karismasin).
                # Beklenen'in BOS oldugu burada da SART: kontrol() disindan gelen bozuk bir
                # kayit sessizce buraya dusmesin (olcut_dogrula zaten reddeder).
                gecti = sayi_ok and rc == 0 and not kirmizi and not beklenen
                detay = ("cikis=%d iddia=%s/%d kirmizi=%d %s"
                         % (rc, iddia, t_iddia, len(kirmizi),
                            kirmizi[0][:90] if kirmizi else ""))
                if beklenen:
                    detay += ("  ⚠️ KONTROL kaydinin beklenen listesi DOLU (%s) — sinif "
                              "beyani ile kayit CELISIYOR" % ",".join(beklenen))
                beklenti = "YESIL"
            else:
                raise SystemExit(
                    "OLCUT TANINMIYOR (%s): %r — taninan degerler: %s. Surucu VARSAYILANA "
                    "DUSMEZ (fail-closed)."
                    % (kod, olcut, ", ".join(repr(o) for o in OLCUTLER)))
            check("%s [%s] %s" % (kod, beklenti, aciklama), gecti, detay)
            if not gecti:
                print("       --- %s ciktisinin kuyrugu ---\n%s" % (kod, kuyruk))
            matris.append((kod, beklenti, rc, iddia, len(kirmizi),
                           ",".join(sorted(set(kirmizi_kod)))[:56] or "-"))
            if sha(HEDEF) != canli_once:
                check("KAYNAK AGAC DEGISTI (ayna kacagi!) [%s]" % kod, False)

        print("\n   --- MUTASYON MATRISI ---")
        print("   %-4s %-14s %-6s %-10s %-8s %s" % ("kod", "beklenti", "cikis", "iddia",
                                                    "kirmizi", "kirmizi iddia kodlari"))
        for kod, beklenti, rc, iddia, adet, kodlar in matris:
            print("   %-4s %-14s %-6d %-10s %-8d %s"
                  % (kod, beklenti, rc, "%s/%d" % (iddia, t_iddia), adet, kodlar))
    finally:
        shutil.rmtree(ayna, ignore_errors=True)

    # --- 3) SON DOKUNULMAZLIK ------------------------------------------------------
    print("\n3) KAYNAK DOKUNULMAZLIGI (sha256, harness sonu)")
    canli_sonra = sha(HEDEF)
    check("shop/src/yonet.js sha256 BASTAKIYLE AYNI (mutant diskte kalmadi)",
          canli_sonra == canli_once,
          "once=%s… sonra=%s…" % (canli_once[:16], canli_sonra[:16]))

    print("\n" + ("SONUC: TUM MUTANTLAR YAKALANDI, KONTROLLER YESIL ✅"
                 if not FAILS else
                 "SONUC: %d KUSUR ❌\n  - %s" % (len(FAILS), "\n  - ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
