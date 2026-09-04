#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/kutu-arsivle.py (ortak posta kutusu arsivleyicisi).

GERCEK ARACI CAGIRIR (subprocess), taklit ETMEZ: her vaka sentetik ama GERCEK KUTU
SEKLINDE (YAML frontmatter + iki diyezli gunluk bloklar, cok satirli govde, kod citi)
bir fikstur uretir, araci uzerinde kosturur ve DISKTEKI sonucu olcer.

🔴 FIKSTURLERDE GERCEK KISISEL VERI YOKTUR ve OLMAYACAKTIR (31 Tem: bir dalda fiksture
kisisel e-posta sizmisti). Adlar MimarA/MimarB/AdvisorX gibi UYDURMA; e-posta, telefon,
adres, vergi no GECMEZ. Fikstur "gercekci" olmak zorunda DEGIL, "gercek SEKILDE" olmak
zorundadir ([[nobetci-fikstur-sekli]]).

VAKALAR (hepsi bloklayici):
   1. tavan ALTINDA -> hicbir sey yazilmaz (sha256 esit), rc=0
   2. tavan asilinca DOGRU SAYIDA blok tasinir (bagimsiz oracle ile kiyaslanir)
   3. tasinan satirlar arsivde BIREBIR ve AYNI SIRADA (kayipsizlik, bayt ekseninde)
   4. frontmatter + en ustteki `--koru` blok korunur
   5. blok ORTASINDAN bolunmez (tasinan metin `## ` ile baslar, blok sayilari korunur)
   6. arsiv dosyasi YOKSA dogru frontmatter ile olusturulur
   7. kilit BASKASINDA tutuluyorken: YAZMAZ + SIFIR-DISI rc (fail-closed)
   8. bozuk/yarim frontmatter -> fail-closed, hicbir sey yazilmaz
   9. UTF-8 olmayan kutu -> fail-closed, hicbir sey yazilmaz
  10. `--kuru` hicbir sey yazmaz ama SAYILARI basar
  11. SENTETIK ARIZA (4 sinif) -> lossless dogrulamasi KIRMIZI, hicbir sey yazilmaz
      (bu vaka LOSSLESS DOGRULAMASINI SILEN mutanti kirmizi yakan olcum aletidir)
  12. `--koru` tasinabilir blok birakmiyorsa: UYARI + hicbir sey yazilmaz
  13. kod CITI icindeki `## ` satiri blok basi SAYILMAZ
  14. arka arkaya iki kosum: ikincisi TAVAN ALTINDA der, toplam icerik KAYIPSIZ
  17. 🔴 K310 — BASLIGI DUSMUS blok (oksuz govde): arac `GECTI` DEMEZ, sayaci ADIYLA
      basar, rc!=0 doner ve HICBIR SEY yazmaz; kirmizinin METNI oksuz govde kolunu anar
  18. K310 KONTROL — ayracli ve SAGLAM kutu: `oksuz_govde_kutu=0` basilir, lossless GECER
  19. K310 KORLUK — ayracsiz kutuda `EKSEN_KOR=` beyani basilir (0 deyip GECILMEZ)
  20. 🔴 K318 KOL-2 — DIPTE korumali blok varken USTTEKI eski bloklar TASINIR
      (korumali blok YERINDE atlanir; jeton kutuda KALIR, kutu tavanin ALTINA iner)
  21. K313g POZITIF KONTROL — ayni fiksturun ISLENMIS jetonlu ikizi TASINIR
      (minimal cift: tek fark jeton satiri) + KOL-2 GERILEME KONTROLU: korumali
      YOKKEN secim BITISIK KUYRUK ve kalan kutu orijinalin ONEKI (eski davranis)
  22. 🔴 K318 KOL-2 — jeton ORTADA: tasinan kume BITISIK DEGIL (25'in hem altindan
      hem ustunden blok gider), korumali blok YERINDE kalir, kutu tavan ALTINA iner
  23. K313g DENETIM — tasinan metne jeton SIZARSA D14 yakalar; kirmizinin SEBEBI
      ADIYLA aranir (hedef-kol atfi)
  24. K313g DETERMINIZM — K1 ve K2 iki ardisik kosumda BIREBIR ayni rc/sayi
  25. 🔴 K318 KOL-1 — jeton GOVDEDE, kapanis ISLENMIS -> KORUMA URETMEZ, blok tasinir,
      `govde_anmasi=1` ADIYLA basilir (yanlis pozitif sinifinin ta kendisi)
  26. 🔴 K318 KOL-1 KONTROL — 25'in MINIMAL CIFTI: kapanis BEKLEYEN olunca blok HALA
      korunur (`sinif=KAPANIS`); daraltma gercek kapanisi ELEMEDI
  27. 🔴 K318 KOL-1 FAIL-CLOSED — KAPANMAMIS cit: kapanis konumu AYRISTIRILAMAZ ->
      jetonlu blok YINE korunur (`sinif=FAIL_CLOSED`), sebep ADIYLA basilir
  28. 🔴 K318 KOL-2 KAYIPSIZLIK — `tasinan + kalan == once` BLOK **VE** BAYT
      ekseninde basilir ve DISKTEN dogrulanir; arsiv sirasi OZGUN, oksuz govde 0
  29. 🔴 K318 KOL-2 DENETIM — granuler birlestirmede KALAN bir blok duserse
      (`kutu-blok-dus` arizasi) D1/D1c/D2 KIRMIZI yakar, hicbir sey yazilmaz
  30. KOL-3 GIRDISI — `koru` disindaki HER blok korumaliysa `tasinabilir=0` +
      `HUKUM=KORUMA_TUTTU` jetonlari basilir (kapinin TUKETTIGI hal)
  31. 🔴 K329 ASIL — eslesen kapanisi OLMAYAN `BASLIYORUM` blogu TASINMAZ; atlandigi
      CIP ADIYLA basilir (`ACIK_BASLIYORUM_ADLARI=`), blok kutuda KALIR
  32. 🔴 K329 KONTROL — kapanisi OLAN `BASLIYORUM` blogu YINE TASINIR ve kutu tavanin
      ALTINA iner: veto rotasyonu KILITLEMEZ (yeni tikanma URETMEDI)
  33. 🔴 K329 ESLESTIRME (MINIMAL CIFT, iki yonlu) — (A) cipin adini ANAN ama kapanis
      OLMAYAN blok vetoyu KALDIRMAZ; (B) ayni fiksture TEK SATIR eklenip o blok
      GERCEK kapanis olunca veto KALKAR ve blok tasinir
  34. 🔴 K329 DENETIM — tasinan metne acik blok SIZARSA (`basliyorum-sizdir` arizasi)
      D17 KIRMIZI yakar, hicbir sey yazilmaz; kirmizinin SEBEBI ADIYLA aranir
  35. 🔴 K329 KONUM OLCUTU — `BASLIYORUM` yalniz GOVDEDE geciyorsa veto URETMEZ,
      blok tasinir ve `basliyorum_govde_anmasi=1` ADIYLA basilir (yanlis pozitif)
  36. 🔴 K329 REGRESYON — UC GERCEK vakanin BASLIK SARMALI (arsiv :52842 ASCII+backtick ·
      :53553 ad BACKTICK'SIZ · :53601 emoji+Turkce): ucu de vetolanir, ADIYLA basilir,
      SINIFI ayri ayri gorunur; rotasyon yine de eski dolgu bloklarini tasir
  37. 🔴 K341 ASIL — `--kapanislari-isle` KAPANIS KONUMUNDAKI jetonu cevirir, koruma
      3'ten 1'e duser ve blok rotasyona ACILIR. MINIMAL CIFT: ayni fikstur once
      BAYRAKSIZ (taban: koruma tutar, `CEVRIM=0 kip=KAPALI`) sonra BAYRAKLI kosulur
  38. 🔴 K341 DOKUNULMAZLIK — cevrim GOVDE ANMASINA ve AYRISTIRILAMAYAN (fail-closed)
      bloga DOKUNMAZ; cevrilen satirda jeton DISINDA tek bayt degismez
  39. 🔴 K341 DENETIM — sentetik cevrim arizasi (satir dus / govde cevir / icerik boz)
      C1-C8'i KIRMIZI yakar; kutu VE arsiv sha256'lari DEGISMEZ
  40. 🔴 K341 GERILEME — bayrak YOKKEN jetona DOKUNULMAZ, koruma AYNEN tutar ve
      cevrim iddiasi HIC basilmaz (yeni kol eski yolu sessizce degistirmedi)
  41. 🔴 K359 ROL OLCUTU — TIRNAK ICINDEKI `başlıyorum` marker DEGILDIR (uclu fikstur,
      MINIMAL CIFT): (A) alintili -> blok rotasyona ACIK · (B) ayni cumleden IKI
      tirnak silinir -> blok HALA KILITLER · (C) alinti icinde KALIN SARMAL -> yine
      marker (daraltma gercek acik cipleri SERBEST BIRAKMAZ)
  42. 🔴 K359 UCUNCU KAPANIS KOLU — `✅` + `KAPANDI` + CIP ADI kapanistir; UC SARTIN
      UCU DE SART. DORT NEGATIF FIKSTUR: ciplak `KAPANDI` · ad YOK · gercek acik blok ·
      TIRNAK ICINDE `KAPANDI`. "ad YOK" bacagi UCTAN UCA GORUNMEZDIR (adsiz kapanis
      hicbir cipi serbest birakamaz) -> o tek bacak aracin KENDI fonksiyonu cagrilarak
      olculur (`_arac_modulu`, mutant yolu da gecerlidir)
  43. 🔴 K359-B KUSUR A — KAPANIS ADI IMZA ONAYLI GEVSEK cikarimla da okunur.
      Olculen vaka: `✅ <ad> (çip: …) **SAYILI KAPANIŞ**` — ad BACKTICK'SIZ, Turkce
      `Ş`, `KAPANDI` sozcugu YOK. Blok KAPANIS SAYILIYORDU ama SAHIBI okunamiyordu,
      yani acilis ile kapanis AYRI ALFABEDEN okunuyordu. DORT NEGATIF FIKSTUR:
      kapanisi BASKASI imzalamis · KAPANIS OLMAYAN ama adi anan+imzali blok · ad
      yalniz KOMSU kapanisin GOVDESINDE · kapanis sozu TIRNAK ICINDE. 🔴 `kilitledi=0`
      HEDEF DEGIL: 2 cip serbest kalir, 4 cip KILITLI kalir ve bu ADIYLA olculur
  44. 🔴 K359-B KUSUR B — ACILISI KUTUDA KALAN KAPANIS ROTASYONA GIRMEZ (cift
      butunlugu). Iki POZITIF sekil (`ACILIS_SABIT` · `ACILIS_DAHA_YENI`) + BIR
      NEGATIF (normal yon: acilis kapanistan ESKI konumda -> cift birlikte TASINIR).
      Negatif olmasa "her kapanisi pinleyen" bir kol da yesil yanardi
  46. 🔴 K360-A AD EKSENI — ACILIS ile KAPANIS AYNI KIMLIK KUMESINDEN okunur
      (iki ters yonde POZITIF + 3 negatif: govdede anma / kod citi / baska imza)
  47. 🔴 K360-B ARSIV DUZLEMI — "kapandi mi" sorusu ARSIVE DE sorulur; serbest
      birakma ZAMAN SIRALI + TUKETIMLI, arsiv bozuksa FAIL-CLOSED
  48. 🔴 K360-C KONUM OLCUTU — dev baslikta PROZA gecen `BASLIYORUM` marker DEGIL
  45. 🔴 K359-B DENETIM — `cift-bolunmesi-sizdir` arizasi D18'de yakalanmali: tasinan
      metne acilisi kutuda kalan bir KAPANIS sizarsa rc!=0 + HICBIR SEY yazilmaz

🔴 17-19'UN FIKSTURU AYRI (`kutu_uret_ayracli`): 1-16 arasi fiksturler bloklari AYRAC
(`---`) ile ayirmaz, CANLI kutu ayirir. Oksuz govde ekseni ayraca dayandigi icin bu uc
vakanin fiksturu canli kutunun SEKLINI tasimak zorunda; yoksa olculen sey aracin
davranisi degil fiksturun sekli olurdu.

MUTASYON (cift yonlu, KOPYA uzerinde — canli dosyaya DOKUNMAZ):
    python3 tools/kutu-arsivle-test.py --mutasyon
  (a) lossless dogrulamasini oldur   -> suite KIRMIZI olmali
  (b) flock cagrisini oldur          -> suite KIRMIZI olmali
  (d) oksuz govde kolunu oldur       -> suite KIRMIZI olmali (vaka 17)
  (e) korluk beyanini oldur          -> suite KIRMIZI olmali (vaka 19)
  (f) koruma ICRA kolunu oldur       -> suite KIRMIZI olmali (vaka 20/22)
  (g) korumali blok TESPITINI oldur  -> suite KIRMIZI olmali (vaka 20/22)
  (h) D14 koruma DENETIMINI oldur    -> suite KIRMIZI olmali (vaka 23)
  (i) kapanis KONUMU olcutunu oldur  -> suite KIRMIZI olmali (vaka 25)
  (j) granulerligi oldur             -> suite KIRMIZI olmali (20/22/28 + 31/32/33)
  (k) kayipsizlik beyanini sustur    -> suite KIRMIZI olmali (vaka 28)
  (l) K329 veto ICRA kolunu oldur    -> suite KIRMIZI olmali (vaka 31/32/33)
  (m) D17 acik cip DENETIMINI oldur  -> suite KIRMIZI olmali (vaka 34)
  (n) K329 KONUM olcutunu oldur      -> suite KIRMIZI olmali (vaka 35)
  (o) K329 ESLESTIRMEyi gevset       -> suite KIRMIZI olmali (vaka 31/32/33)
  (t) MP1 ROL olcutu alt-dizgeye     -> suite KIRMIZI olmali (vaka 41)
  (u) MP2 uc sart "herhangi biri"ne  -> suite KIRMIZI olmali (vaka 42 + 31/32/33/36)
  (v) MP3 tirnak elemesi kalkar      -> suite KIRMIZI olmali (vaka 41/42)
  (x) K359-B gevsek KAPANIS adi olur -> suite KIRMIZI olmali (vaka 43)
  (y) K359-B IMZA onayi kalkar       -> suite KIRMIZI olmali (vaka 43, TERS YON)
  (z) K359-B cift butunlugu ICRA olur-> suite KIRMIZI olmali (vaka 44)
  (aa) K359-B konum bacagi (`o<c`)   -> suite KIRMIZI olmali (vaka 44)
  (bb) K359-B D18 denetimi olur      -> suite KIRMIZI olmali (vaka 45)
  (cc) MP0 ESDEGER yeniden yazim     -> suite YESIL kalmali (imza taramasi ters yonde)
  (w) MP0 ESDEGER yeniden yazim      -> suite YESIL kalmali (hicbir sey oldurmemeli)
  (c) ilgisiz metin degisikligi      -> suite YESIL kalmali
  Mutasyon oncesi/sonrasi canli aracin sha256'si BASILIR ve ESITLIGI iddia edilir.

Kullanim:
    python3 tools/kutu-arsivle-test.py
    python3 tools/kutu-arsivle-test.py --mutasyon
    python3 tools/kutu-arsivle-test.py --arac /gecici/mutant-kutu-arsivle.py
(cikis kodu 0 = GECTI)
"""
import argparse
import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "kutu-arsivle.py")

GECTI = []
KIRMIZI = []


def iddia(ad, kosul, tani=""):
    if kosul:
        GECTI.append(ad)
        print("  ✅ %s" % ad)
    else:
        KIRMIZI.append("%s%s" % (ad, (" -> " + tani) if tani else ""))
        print("  ❌ %s%s" % (ad, (" -> " + tani) if tani else ""))


def sha(yol):
    if not os.path.exists(yol):
        return "YOK"
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8", newline="") as f:
        f.write(metin)


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().decode("utf-8")


# ------------------------------------------------------------------ FIKSTURLER
FM = ("---\n"
      "name: sentetik-posta-kutusu\n"
      "description: KABUL TESTI FIKSTURU — gercek kutu DEGIL; gercek kisisel veri YOK\n"
      "metadata: \n"
      "  node_type: memory\n"
      "  type: project\n"
      "---\n"
      "\n")

# Blok govdesi GERCEK kutu seklini taklit eder: madde imleri, kalin metin, uzun satir,
# ara baslik (`###` — ust duzey blok basi DEGIL), bos satir.
GOVDE = (
    "\n"
    "**Ozet:** sentetik blok %d — bu metin yalniz kabul testi icindir.\n"
    "\n"
    "- Olculen sayi: %d kayit, sapma 0.\n"
    "- Karar: kapi fail-closed kalir; ayrinti asagida.\n"
    "\n"
    "### Ayrinti\n"
    "1. Ilk madde, uzunca bir cumle ile gercek raporlarin satir uzunlugunu taklit eder.\n"
    "2. Ikinci madde.\n"
    "\n"
    "Sonuc: kapali. — MimarA\n"
    "\n")


def blok(i):
    """i buyudukce daha ESKI blok (kutu YENI -> ESKI siralidir)."""
    gun = 31 - (i % 28)
    baslik = ("## 2026-07-%02d — MimarA -> MimarB: sentetik konu %d (kabul testi fiksturu)\n"
              % (gun, i))
    return baslik + (GOVDE % (i, 100 + i))


def kutu_uret(n, citli=False):
    """n blokluk sentetik kutu. citli=True ise 2. bloga `## ` iceren kod citi konur."""
    parcalar = [FM]
    i = 0
    while i < n:
        g = blok(i)
        if citli and i == 1:
            g += ("```markdown\n"
                  "## BU SATIR KOD CITI ICINDE — BLOK BASI DEGILDIR\n"
                  "ornek: python3 tools/kutu-arsivle.py --kuru\n"
                  "```\n"
                  "\n")
        parcalar.append(g)
        i += 1
    return "".join(parcalar)


# -------------------------------------------------- BAGIMSIZ ORACLE (araci taklit ETMEZ)
def oracle_kesim(metin, tavan, koru, su_seviye_orani=0.8):
    """(tasinacak_blok, kesim_indeksi) — aracin mantigindan BAGIMSIZ, sade yeniden hesap.

    O1 (16 Agu 2026): kutu tavanin su seviyesine (~%80) dusurulur; gelecek
    bloklar icin bas payi birakir. Oracle da ayni kurala uyar.

    Fikstur uretimi cit-siz vakalarda ust duzey `## ` disinda `## ` uretmez; citli
    fikstur icin ayri (13.) vaka vardir.
    """
    satirlar = metin.splitlines(keepends=True)
    if len(satirlar) <= tavan:
        return 0, None
    fm = 0
    if satirlar and satirlar[0].rstrip("\n") == "---":
        j = 1
        while j < len(satirlar):
            if satirlar[j].rstrip("\n") == "---":
                fm = j + 1
                break
            j += 1
    baslar = []
    ic = False
    k = fm
    while k < len(satirlar):
        s = satirlar[k]
        if s.lstrip().startswith("```"):
            ic = not ic
        elif not ic and s.startswith("## "):
            baslar.append(k)
        k += 1
    tasinabilir = max(0, len(baslar) - koru)
    if tasinabilir <= 0:
        return 0, None
    su_seviye = int(tavan * su_seviye_orani)
    if su_seviye < 1:
        su_seviye = 1
    t = 1
    while t <= tasinabilir:
        kesim = baslar[len(baslar) - t]
        if kesim <= su_seviye:
            return t, kesim
        t += 1
    return tasinabilir, baslar[len(baslar) - tasinabilir]


# --------------------------------------------------------------------- kosucu
def kos(arac, kutu, arsiv, kilit, tavan=300, koru=3, kuru=False, ortam=None,
        su_seviye_orani=0.8, kapanislari_isle=False):
    komut = [sys.executable, arac, "--kutu", kutu, "--arsiv", arsiv, "--kilit", kilit,
             "--tavan", str(tavan), "--koru", str(koru),
             "--su-seviye-orani", str(su_seviye_orani)]
    if kuru:
        komut.append("--kuru")
    if kapanislari_isle:
        komut.append("--kapanislari-isle")
    env = dict(os.environ)
    env.pop("PRUVO_KUTU_ARSIVLE_ARIZA", None)
    if ortam:
        env.update(ortam)
    r = subprocess.run(komut, capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class Alan(object):
    """Gecici calisma alani: kutu + arsiv + kilit yollari."""

    def __init__(self, kok, kutu_metin, arsiv_metin=None):
        self.kutu = os.path.join(kok, "posta-kutusu.md")
        self.arsiv = os.path.join(kok, "posta-kutusu-arsiv.md")
        self.kilit = os.path.join(kok, ".posta-kutusu.lock")
        if isinstance(kutu_metin, bytes):
            with open(self.kutu, "wb") as f:
                f.write(kutu_metin)
        else:
            yaz(self.kutu, kutu_metin)
        if arsiv_metin is not None:
            yaz(self.arsiv, arsiv_metin)


# ---------------------------------------------------------------------- VAKALAR
def v01_tavan_altinda(arac, kok):
    print("\n[1] tavan ALTINDA -> hicbir sey yazilmaz")
    a = Alan(kok, kutu_uret(3), "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300)
    iddia("1a rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti))
    iddia("1b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("1c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("1d 'TAVAN ALTINDA' beyani", "TAVAN ALTINDA" in cikti, cikti)


def v02_dogru_sayida_blok(arac, kok):
    print("\n[2] tavan asilinca DOGRU SAYIDA blok tasinir")
    metin = kutu_uret(30)
    a = Alan(kok, metin, "## onceki arsiv blogu\n\ngovde\n")
    bek_blok, bek_kesim = oracle_kesim(metin, 300, 3)
    iddia("2a fikstur GERCEKTEN tavani asiyor",
          len(metin.splitlines()) > 300, "%d satir" % len(metin.splitlines()))
    iddia("2b oracle tasinacak blok > 0", bek_blok > 0)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("2c rc=0", rc == 0, cikti)
    iddia("2d arac tam %d blok tasidi" % bek_blok,
          ("tasinacak_blok=%d " % bek_blok) in cikti, cikti)
    sonra = oku(a.kutu)
    iddia("2e sonra satir <= tavan", len(sonra.splitlines()) <= 300,
          "%d satir" % len(sonra.splitlines()))
    iddia("2f kesim BAGIMSIZ oracle ile ayni",
          len(sonra.splitlines()) == bek_kesim,
          "arac %d, oracle %s" % (len(sonra.splitlines()), bek_kesim))
    kalan_blok = sonra.count("\n## 2026-07") + (1 if sonra.startswith("## 2026-07") else 0)
    iddia("2g kalan blok = 30 - %d" % bek_blok, kalan_blok == 30 - bek_blok,
          "kalan=%d" % kalan_blok)


def v03_birebir_satirlar(arac, kok):
    print("\n[3] tasinan satirlar arsivde BIREBIR ve AYNI SIRADA")
    metin = kutu_uret(30)
    eski_arsiv = "## onceki arsiv blogu\n\ngovde satiri\n"
    a = Alan(kok, metin, eski_arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("3a rc=0", rc == 0, cikti)
    yeni_kutu = oku(a.kutu)
    yeni_arsiv = oku(a.arsiv)
    tasinan = metin[len(yeni_kutu):]
    iddia("3b BAYT KORUNUMU: yeni_kutu + tasinan == orijinal",
          yeni_kutu + tasinan == metin)
    iddia("3c eski arsiv ONEKI birebir duruyor", yeni_arsiv.startswith(eski_arsiv))
    ts = tasinan.splitlines()
    iddia("3d tasinan satirlar arsivin SONUNDA birebir + ayni sirada",
          yeni_arsiv.splitlines()[-len(ts):] == ts,
          "tasinan %d satir" % len(ts))
    kayip = [s for s in ts if s and s not in yeni_arsiv]
    iddia("3e hicbir tasinan satir KAYIP degil", not kayip, "kayip=%r" % kayip[:3])


def v04_frontmatter_ve_ust_bloklar(arac, kok):
    print("\n[4] frontmatter + en ustteki --koru blok korunur")
    metin = kutu_uret(30)
    a = Alan(kok, metin, "## onceki\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=4)
    iddia("4a rc=0", rc == 0, cikti)
    sonra = oku(a.kutu)
    iddia("4b frontmatter BIREBIR duruyor", sonra.startswith(FM))
    ust = [blok(i).splitlines()[0] for i in range(4)]
    sonra_baslik = [s for s in sonra.splitlines() if s.startswith("## ")]
    iddia("4c en ustteki 4 blok basligi AYNI SIRADA duruyor",
          sonra_baslik[:4] == ust, "%r" % sonra_baslik[:4])
    iddia("4d korunan blok sayisi >= 4", len(sonra_baslik) >= 4)
    iddia("4e arsivde korunan blok basliklari YOK",
          not any(u in oku(a.arsiv) for u in ust))


def v05_blok_bolunmez(arac, kok):
    print("\n[5] blok ORTASINDAN bolunmez")
    metin = kutu_uret(30)
    a = Alan(kok, metin, "## onceki\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("5a rc=0", rc == 0, cikti)
    yeni_kutu = oku(a.kutu)
    tasinan = metin[len(yeni_kutu):]
    iddia("5b tasinan metin `## ` ile BASLIYOR", tasinan.startswith("## "))
    iddia("5c kutu bir blok govdesinin ORTASINDA bitmiyor "
          "(son dolu satir govde sonu)", yeni_kutu.endswith("\n"))
    iddia("5d blok korunumu: kutu_blok + tasinan_blok == 30",
          yeni_kutu.count("\n## 2026-07") + tasinan.count("## 2026-07") == 30,
          "%d + %d" % (yeni_kutu.count("\n## 2026-07"), tasinan.count("## 2026-07")))


def v06_arsiv_yoksa_frontmatter(arac, kok):
    print("\n[6] arsiv dosyasi YOKSA dogru frontmatter ile olusturulur")
    a = Alan(kok, kutu_uret(30))          # arsiv YAZILMADI
    iddia("6a on kosul: arsiv yok", not os.path.exists(a.arsiv))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("6b rc=0", rc == 0, cikti)
    iddia("6c arsiv olustu", os.path.exists(a.arsiv))
    ar = oku(a.arsiv)
    iddia("6d frontmatter `---` ile basliyor", ar.startswith("---\n"))
    iddia("6e frontmatter'da name: var", "\nname: posta-kutusu-arsiv\n" in ar)
    iddia("6f frontmatter'da node_type: memory var", "node_type: memory" in ar)
    iddia("6g frontmatter KAPANDI (ikinci ---)",
          ar.split("\n").count("---") >= 2)
    iddia("6h frontmatter'dan sonra ilk blok `## ` ile basliyor",
          "\n---\n\n## " in ar)
    iddia("6i arac 'yeni dosya' oldugunu BEYAN etti",
          "arsiv_yeni_dosya=EVET" in cikti, cikti)


def v07_kilit(arac, kok):
    print("\n[7] kilit BASKASINDA -> YAZMAZ + sifir-disi rc")
    a = Alan(kok, kutu_uret(30), "## onceki\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    tutucu = open(a.kilit, "a+")
    fcntl.flock(tutucu.fileno(), fcntl.LOCK_EX)   # kilit GERCEKTEN tutuluyor
    try:
        rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    finally:
        fcntl.flock(tutucu.fileno(), fcntl.LOCK_UN)
        tutucu.close()
    iddia("7a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti))
    iddia("7b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("7c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("7d 'KILIT ALINAMADI' beyani (sessiz basari YOK)",
          "KILIT ALINAMADI" in cikti, cikti)
    # kilit birakildiktan SONRA ayni cagri calismali (kilit kalici bloklamiyor)
    rc2, cikti2 = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("7e kilit birakilinca ayni cagri GECIYOR", rc2 == 0, cikti2)


def v08_bozuk_frontmatter(arac, kok):
    print("\n[8] YARIM frontmatter -> fail-closed")
    bozuk = ("---\n"
             "name: sentetik-posta-kutusu\n"
             "description: kapanis --- YOK (yarim yazilmis dosya)\n") + \
        "".join(blok(i) for i in range(30))
    a = Alan(kok, bozuk, "## onceki\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("8a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti))
    iddia("8b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("8c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("8d tani metninde YARIM FRONTMATTER geciyor",
          "YARIM FRONTMATTER" in cikti, cikti)


def v09_bozuk_utf8(arac, kok):
    print("\n[9] UTF-8 olmayan kutu -> fail-closed")
    ham = kutu_uret(30).encode("utf-8") + b"\xff\xfe GECERSIZ BAYT\n"
    a = Alan(kok, ham, "## onceki\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("9a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti))
    iddia("9b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("9c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("9d tani metninde 'UTF-8 degil' geciyor", "UTF-8 degil" in cikti, cikti)


def v10_kuru(arac, kok):
    print("\n[10] --kuru hicbir sey yazmaz ama SAYILARI basar")
    metin = kutu_uret(30)
    a = Alan(kok, metin, "## onceki\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3, kuru=True)
    iddia("10a rc=0", rc == 0, cikti)
    iddia("10b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("10c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("10d once_satir sayisi basildi", "once_satir=" in cikti, cikti)
    iddia("10e tasinacak_blok sayisi basildi", "tasinacak_blok=" in cikti, cikti)
    iddia("10f sonra_satir sayisi basildi", "sonra_satir=" in cikti, cikti)
    iddia("10g 'KURU KIP' beyani", "KURU KIP" in cikti, cikti)
    bek_blok, _ = oracle_kesim(metin, 300, 3)
    iddia("10h kuru sayilari GERCEK planla ayni",
          ("tasinacak_blok=%d " % bek_blok) in cikti, cikti)


ARIZALAR = ("arsiv-satir-dus", "kutu-satir-dus", "arsiv-onek-boz", "arsiv-sira-boz")


def v11_sentetik_ariza(arac, kok):
    print("\n[11] SENTETIK ARIZA -> lossless dogrulamasi KIRMIZI, yazim YOK")
    print("     (LOSSLESS DOGRULAMASINI SILEN mutanti kirmizi yakan olcum aleti)")
    for kod in ARIZALAR:
        alt = os.path.join(kok, "ariza-" + kod)
        os.makedirs(alt, exist_ok=True)
        a = Alan(alt, kutu_uret(30), "## onceki arsiv blogu\n\ngovde\n")
        h1, h2 = sha(a.kutu), sha(a.arsiv)
        rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3,
                        ortam={"PRUVO_KUTU_ARSIVLE_ARIZA": kod})
        iddia("11-%s rc SIFIR-DISI" % kod, rc != 0, "rc=%d\n%s" % (rc, cikti))
        iddia("11-%s kutu DEGISMEDI" % kod, sha(a.kutu) == h1)
        iddia("11-%s arsiv DEGISMEDI" % kod, sha(a.arsiv) == h2)
        iddia("11-%s 'HICBIR SEY YAZILMADI' beyani" % kod,
              "HICBIR SEY YAZILMADI" in cikti, cikti)


def v12_koru_tavani(arac, kok):
    print("\n[12] --koru tasinabilir blok birakmiyorsa: UYARI, yazim YOK")
    metin = kutu_uret(8)
    a = Alan(kok, metin, "## onceki\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=20, koru=99)
    iddia("12a rc=0 (bu bir HATA degil, yapilacak is yok)", rc == 0, cikti)
    iddia("12b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("12c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("12d UYARI basildi", "UYARI" in cikti, cikti)


def v13_cit_ici_baslik(arac, kok):
    print("\n[13] kod CITI icindeki `## ` blok basi SAYILMAZ")
    metin = kutu_uret(30, citli=True)
    a = Alan(kok, metin, "## onceki\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("13a rc=0", rc == 0, cikti)
    yeni_kutu = oku(a.kutu)
    yeni_arsiv = oku(a.arsiv)
    tasinan = metin[len(yeni_kutu):]
    cit_satiri = "## BU SATIR KOD CITI ICINDE — BLOK BASI DEGILDIR"
    iddia("13b cit satiri hala 2. blogun ICINDE (kutuda, korunan bolgede)",
          cit_satiri in yeni_kutu)
    iddia("13c cit satiri arsive TASINMADI", cit_satiri not in yeni_arsiv)
    iddia("13d tasinan metin yine `## ` blok basiyla basliyor",
          tasinan.startswith("## 2026-07"))
    iddia("13e bayt korunumu", yeni_kutu + tasinan == metin)


def v14_iki_kosum(arac, kok):
    print("\n[14] arka arkaya iki kosum -> ikincisi TAVAN ALTINDA, toplam KAYIPSIZ")
    metin = kutu_uret(30)
    a = Alan(kok, metin)
    rc1, c1 = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("14a ilk kosum rc=0", rc1 == 0, c1)
    rc2, c2 = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("14b ikinci kosum rc=0", rc2 == 0, c2)
    iddia("14c ikinci kosum 'TAVAN ALTINDA' dedi", "TAVAN ALTINDA" in c2, c2)
    yeni_kutu = oku(a.kutu)
    arsiv = oku(a.arsiv)
    # KAYIPSIZLIK: her orijinal blok basligi ya kutuda ya arsivde, tam olarak BIR kez
    eksik, ikiz = [], []
    i = 0
    while i < 30:
        b = blok(i).splitlines()[0]
        n = yeni_kutu.count(b) + arsiv.count(b)
        if n == 0:
            eksik.append(i)
        elif n > 1:
            ikiz.append(i)
        i += 1
    iddia("14d hicbir blok KAYBOLMADI", not eksik, "eksik=%r" % eksik)
    iddia("14e hicbir blok IKIZLENMEDI", not ikiz, "ikiz=%r" % ikiz)


def v15_su_seviyesi_doldurur(arac, kok):
    """[15] V-D: kutu TAM tavanda → rotasyon KOSAR ve su seviyesine iner.

    O1 (16 Agu 2026): eski davranis kutu tam 300'te duruyor, bir sonraki
    blok 301'e itiyordu. Yeni davranis: rotasyon su seviyesine (~%80)
    kadar indiri ki bir sonraki blok tavanin ustune HEMEN cikmasin.
    """
    print("\n[15] V-D: kutu tam tavanda → rotasyon KOSAR + su seviyesine iner")
    # Tavan 300; dosya TAM 300 satir olacak sekilde blok sayisi ayarlanir.
    # kutu_uret(N) her blogu 10 satir uretir; FM 7 satir. 30 blok = 300 + 7.
    metin = kutu_uret(30)
    a = Alan(kok, metin)
    # On kosul: dosya tavani asiyor (veya esit).
    assert len(metin.splitlines()) > 300, "fikstur tavan altinda"
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("15a rc=0", rc == 0, cikti)
    sonra = len(oku(a.kutu).splitlines())
    # Su seviyesi 240; kutu < 240 olmali (veya tavanin altinda kalmali).
    iddia("15b kutu su seviyesinin altinda (sonra=%d, su_seviye=240)" % sonra,
          sonra <= 240)
    # TAVAN altinda ama 300'e YAKIN DEGIL — bas payi var.
    iddia("15c kutu tavana kadar inmedi (bas payi var)",
          sonra < 300 - 30, "sonra=%d, tavan-30=%d" % (sonra, 300 - 30))
    iddia("15d kutu DEGISTI", sha(a.kutu) != h1)
    iddia("15e arsiv DEGISTI", sha(a.arsiv) != h2)


def v16_su_seviyesi_nop(arac, kok):
    """[16] V-E: kutu su seviyesinin altinda → NO-OP (bayt-bayt ayni).

    Dosya zaten 200 satirdan az oldugunda rotasyon KOSMAZ; arsiv ve kutu
    bayt-bayt ayni kalmali.
    """
    print("\n[16] V-E: kutu su seviyesinin altinda → NO-OP (bayt-bayt ayni)")
    # kutu_uret(15) uretiyor ~150 satir; bu su seviyesinin (240) altinda.
    metin = kutu_uret(15)
    a = Alan(kok, metin)
    assert len(metin.splitlines()) < 240, "fikstur su seviyesinin ustunde"
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("16a rc=0", rc == 0, cikti)
    iddia("16b kutu bayt-bayt ayni", sha(a.kutu) == h1)
    iddia("16c arsiv bayt-bayt ayni", sha(a.arsiv) == h2)
    iddia("16d 'TAVAN ALTINDA' basildi", "TAVAN ALTINDA" in cikti, cikti)


# ------------------------------------------- K310: BLOK BUTUNLUGU (oksuz govde)
# 🔴 NEDEN AYRI FIKSTUR: yukaridaki fiksturler bloklari AYRAC (`---`) ile ayirmaz;
# CANLI kutu ayirir (27 Agu olcumu: 11 blok / 11 ayrac). Oksuz govde ekseni ayraca
# dayandigi icin bu vakalarin fiksturu CANLI kutunun seklini tasimak ZORUNDA —
# yoksa olculen sey aracin davranisi degil, fiksturun sekli olurdu.
def kutu_uret_ayracli(n, baslik_dus=None):
    """n blokluk, AYRACLI (canli kutu sekli) sentetik kutu.

    baslik_dus verilirse o blogun `## ` BASLIK SATIRI dusurulur — govdesi ayraclar
    arasinda OKSUZ kalir. K310'un olculen vakasinin birebir sekli."""
    parcalar = [FM]
    i = 0
    while i < n:
        g = blok(i)
        if baslik_dus is not None and i == baslik_dus:
            g = g.split("\n", 1)[1]          # yalniz BASLIK satiri dusurulur
        parcalar.append(g + "---\n\n")
        i += 1
    return "".join(parcalar)


def v17_oksuz_govde_kirmizi(arac, kok):
    print("\n[17] K310 — BASLIGI DUSMUS blok (oksuz govde) -> GECTI DEMEZ, rc!=0")
    metin = kutu_uret_ayracli(30, baslik_dus=20)
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    iddia("17a fikstur GERCEKTEN tavani asiyor", len(metin.splitlines()) > 300,
          "satir=%d" % len(metin.splitlines()))
    iddia("17b fikstur GERCEKTEN ayracli (eksen KOR degil)",
          metin.count("\n---\n") > 5, "ayrac=%d" % metin.count("\n---\n"))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("17c rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti[-400:]))
    iddia("17d 'lossless_dogrulama=GECTI' BASILMADI",
          "lossless_dogrulama=GECTI" not in cikti, cikti[-300:])
    iddia("17e oksuz govde sayaci ADIYLA basildi ve SIFIR DEGIL",
          "oksuz_govde_kutu=" in cikti and "oksuz_govde_kutu=0" not in cikti,
          cikti[-300:])
    # 🔴 HEDEF-KOL ATFI: kirmizinin METNI oksuz govde kolunu adiyla anmali. Baska bir
    # iddia (ornegin D7) kirmizi yakiyorsa mutant OLDURULMUS SAYILMAZ ([[K182]]).
    iddia("17f kirmizinin SEBEBI oksuz govde kolu (hedef-kol atfi)",
          "OKSUZ GOVDE" in cikti, cikti[-300:])
    iddia("17g kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("17h arsiv DEGISMEDI", sha(a.arsiv) == h2)


def v18_ayracli_temiz_kontrol(arac, kok):
    print("\n[18] K310 KONTROL — ayracli ve SAGLAM kutu: sayac 0, lossless GECER")
    metin = kutu_uret_ayracli(30)
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("18a rc=0", rc == 0, cikti[-400:])
    iddia("18b oksuz_govde_kutu=0 ADIYLA basildi", "oksuz_govde_kutu=0" in cikti,
          cikti[-300:])
    iddia("18c oksuz_govde_ek=0 ADIYLA basildi", "oksuz_govde_ek=0" in cikti,
          cikti[-300:])
    iddia("18d lossless beyani SAYACA dayaniyor",
          "lossless_dogrulama=GECTI" in cikti and "oksuz_govde_kutu=0" in cikti.split(
              "lossless_dogrulama=GECTI")[1][:120], cikti[-300:])
    iddia("18e EKSEN_KOR basilmadi (ayrac VAR)", "EKSEN_KOR=" not in cikti,
          cikti[-300:])
    iddia("18f is GERCEKTEN yapildi (kutu kisaldi)",
          len(oku(a.kutu).splitlines()) < len(metin.splitlines()))


def v19_korluk_beyani(arac, kok):
    print("\n[19] K310 — AYRACSIZ kutuda eksen KOR oldugunu SOYLER (0 deyip gecmez)")
    metin = kutu_uret(30)                     # ayrac YOK (eski fikstur sekli)
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("19a rc=0 (ayracsizlik bir ARIZA degil)", rc == 0, cikti[-400:])
    iddia("19b EKSEN_KOR beyani basildi", "EKSEN_KOR=oksuz_govde_kutu" in cikti,
          cikti[-400:])
    iddia("19c ayrac_kutu=0 ADIYLA basildi", "ayrac_kutu=0" in cikti, cikti[-300:])


# ------------------------------------------ K313g: GORUNURLUK (koruma kolu)
# 🔴 NEDEN VAR (olculen vaka, 27 Agu): iki cip kural ⑤'in kapanis satirini kutuya
# GERCEKTEN yazdi; dakikalar sonra bu arac kostu ve iki blok da arsive tasindi
# (arsiv :50713 · :50791, guncel kutuda 0 isabet). Rotasyon LOSSLESS'ti, ama Okan'in
# baktigi yuzeyde satir KALMADI -> bitmis cip ACIK gorundu. Lossless olmak GORUNUR
# olmak degildir.
#
# 🔴 JETON BURADA LITERAL YAZILIR, ARACTAN ITHAL EDILMEZ. Olcutunu test edilen
# modulden okuyan vaka mutantla OLMEZ ve batarya yine yesil yanar
# ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
BEKLEYEN_SATIR = "✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM"
ISLENMIS_SATIR = "✅ ARŞİVLENDİ"


def kutu_uret_jetonlu(n, jetonlar, govde=None, acik_cit=None):
    """n blokluk AYRACLI kutu.

    jetonlar={blok_idx: satir}  -> o bloklarin KAPANIS KONUMUNA (en sonuna) eklenir.
    govde={blok_idx: satir}     -> o bloklarin GOVDESINE (baslik hemen altina) eklenir;
                                   K318 KOL-1'in yanlis-pozitif vakasi budur.
    acik_cit={blok_idx}         -> o blokta KAPANMAMIS bir cit acilir (blok siniri
                                   AYRISTIRILAMAZ hale gelir) — fail-closed vakasi.
    Sekil `kutu_uret_ayracli` ile AYNI (canli kutu sekli)."""
    parcalar = [FM]
    i = 0
    while i < n:
        g = blok(i)
        if govde and i in govde:
            bas, kalan = g.split("\n", 1)
            g = bas + "\n" + govde[i] + "\n" + kalan
        if acik_cit and i in acik_cit:
            g += "```markdown\n"          # KAPANMIYOR — bilerek
        if i in jetonlar:
            g += jetonlar[i] + "\n\n"
        parcalar.append(g + "---\n\n")
        i += 1
    return "".join(parcalar)


def _blok_dilimleri(metin):
    """[(bas, son)] — blok satir araliklari; ARACIN kodunu CAGIRMAZ, sifirdan bulur."""
    satirlar = metin.splitlines(keepends=True)
    fm = 0
    if satirlar and satirlar[0].rstrip("\n") == "---":
        j = 1
        while j < len(satirlar):
            if satirlar[j].rstrip("\n") == "---":
                fm = j + 1
                break
            j += 1
    baslar = []
    ic = False
    k = fm
    while k < len(satirlar):
        s = satirlar[k]
        if s.lstrip().startswith("```"):
            ic = not ic
        elif not ic and s.startswith("## "):
            baslar.append(k)
        k += 1
    dilimler = []
    m = 0
    while m < len(baslar):
        dilimler.append((baslar[m],
                         baslar[m + 1] if m + 1 < len(baslar) else len(satirlar)))
        m += 1
    return dilimler


def oracle_granuler(metin, tavan, koru, korumali_idx, su_seviye_orani=0.8):
    """(tasinan_indeksler, kalan_satir) — GRANULER secimin BAGIMSIZ yeniden hesabi.

    🔴 Aracin kodunu CAGIRMAZ, taklit ETMEZ: blok sinirlarini sifirdan bulur, sabit
    kumeyi sifirdan kurar ve en eskiden baslayarak secer. Test icindeki sayilar bu
    fonksiyondan TURER — elle yazilan "15 blok tasinir" beklentisi kaynagindan
    sessizce ayrisirdi ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]).
    """
    satirlar = metin.splitlines(keepends=True)
    if len(satirlar) <= tavan:
        return [], len(satirlar)
    araliklar = _blok_dilimleri(metin)
    sabit = set(range(min(koru, len(araliklar)))) | set(korumali_idx)
    su_seviye = max(1, int(tavan * su_seviye_orani))
    kalan = len(satirlar)
    secilen = []
    t = len(araliklar) - 1
    while t >= 0:
        if kalan <= su_seviye:
            break
        if t not in sabit:
            secilen.append(t)
            kalan -= (araliklar[t][1] - araliklar[t][0])
        t -= 1
    secilen.sort()
    return secilen, kalan


def satir_al(cikti, onek):
    """Ciktidaki `onek` ile BASLAYAN ilk satir (yoksa YOK) — determinizm kiyasi icin."""
    for s in cikti.splitlines():
        if s.startswith(onek):
            return s
    return "YOK:" + onek


def v20_koruma_yerinde_atlanir(arac, kok):
    """[20] 🔴 K318 KOL-2 — DIPTEKI korumali blok KUYRUGU REHIN ALMAZ.

    ONCEKI DAVRANIS (bitisik kuyruk): blok 29 korumali -> `etkin_koru=30`,
    `tasinabilir=0`, HICBIR SEY tasinmaz, kutu 460 satirda KILITLI kalir.
    YENI DAVRANIS: korumali blok YERINDE ATLANIR, USTUNDEKI eski bloklar tasinir,
    kutu tavanin ALTINA iner — ve jeton HALA kutuda (gorunurluk KAYBOLMADI).
    """
    print("\n[20] K318 KOL-2 — DIPTE korumali blok varken USTTEKI eski bloklar TASINIR")
    metin = kutu_uret_jetonlu(30, {29: BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    iddia("20a fikstur GERCEKTEN tavani asiyor", len(metin.splitlines()) > 300,
          "satir=%d" % len(metin.splitlines()))
    bek_tasinan, bek_kalan = oracle_granuler(metin, 300, 3, [29])
    iddia("20b oracle: korumali blok DISINDA tasinacak blok VAR", len(bek_tasinan) > 0,
          "oracle bos")
    iddia("20c oracle: en dipteki blok (29) tasinanlarda DEGIL", 29 not in bek_tasinan,
          "%r" % bek_tasinan)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("20d rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-600:]))
    iddia("20e KORUMALI_BEKLEYEN=1", "KORUMALI_BEKLEYEN=1 " in cikti, cikti[-600:])
    iddia("20f govde_anmasi=0 (jeton KAPANIS KONUMUNDA, govdede degil)",
          "govde_anmasi=0 " in cikti, cikti[-600:])
    iddia("20g BAGIMSIZ oracle ile ayni sayida blok tasindi (%d)" % len(bek_tasinan),
          ("tasinacak_blok=%d " % len(bek_tasinan)) in cikti, cikti[-600:])
    iddia("20h yerinde_atlanan=1 ADIYLA basildi (bitisik kuyruk DEGIL)",
          "yerinde_atlanan=1 " in cikti, cikti[-600:])
    iddia("20i bitisik_mi=HAYIR/YERINDE_ATLANDI",
          "bitisik_mi=HAYIR/YERINDE_ATLANDI" in cikti, cikti[-600:])
    iddia("20j kutu DEGISTI (is GERCEKTEN yapildi — eski davranista degismiyordu)",
          sha(a.kutu) != h1)
    iddia("20k arsiv DEGISTI", sha(a.arsiv) != h2)
    iddia("20l 🔴 jeton HALA kutuda (GORUNURLUK korundu)",
          BEKLEYEN_SATIR in oku(a.kutu))
    iddia("20m 🔴 jeton arsive SIZMADI", BEKLEYEN_SATIR not in oku(a.arsiv))
    iddia("20n korumali blogun BASLIGI da kutuda (govdesiyle birlikte kaldi)",
          blok(29).splitlines()[0] in oku(a.kutu))
    iddia("20o kutu BAGIMSIZ oracle'in hesapladigi satira indi (%d)" % bek_kalan,
          len(oku(a.kutu).splitlines()) == bek_kalan,
          "arac %d, oracle %d" % (len(oku(a.kutu).splitlines()), bek_kalan))
    iddia("20p kutu artik tavanin ALTINDA (kilit ACILDI)",
          len(oku(a.kutu).splitlines()) <= 300)
    iddia("20q lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-300:])


def v21_islenmis_jeton_tasinir(arac, kok):
    print("\n[21] K2 POZITIF KONTROL — ISLENMIS jetonlu blok TASINIR "
          "(arac 'hicbir sey tasimaz'a donmedi)")
    metin = kutu_uret_jetonlu(30, {29: ISLENMIS_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    # ON KOSUL: v20 ile MINIMAL CIFT — iki fikstur YALNIZ jeton satirinda ayrisir.
    # Boyle olmazsa "tasindi/tasinmadi" farki jetona degil fiksturun sekline atfedilir.
    ikiz = kutu_uret_jetonlu(30, {29: BEKLEYEN_SATIR})
    iddia("21a fikstur v20 ile MINIMAL CIFT (tek fark jeton satiri)",
          metin.replace(ISLENMIS_SATIR, "@") == ikiz.replace(BEKLEYEN_SATIR, "@"),
          "fiksturler jeton disinda da ayrisiyor")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("21b rc=0", rc == 0, cikti[-500:])
    iddia("21c KORUMALI_BEKLEYEN=0", "KORUMALI_BEKLEYEN=0 " in cikti, cikti[-500:])
    iddia("21d taban_koru BASILDI (koruma DEVREDE DEGIL)",
          "taban_koru=3 " in cikti, cikti[-500:])
    iddia("21e kutu DEGISTI (is GERCEKTEN yapildi)", sha(a.kutu) != h1)
    iddia("21f arsiv DEGISTI", sha(a.arsiv) != h2)
    iddia("21g ISLENMIS jetonlu blok ARSIVE gitti", ISLENMIS_SATIR in oku(a.arsiv),
          "arsivde yok")
    iddia("21h HUKUM=KORUMA_TUTTU BASILMADI", "HUKUM=KORUMA_TUTTU" not in cikti,
          cikti[-300:])
    # 🔴 KOL-2 GERILEME KONTROLU: korumali blok YOKKEN secim BITISIK KUYRUK olmali.
    iddia("21i korumali yokken bitisik_mi=EVET (eski davranisa OZDES)",
          "bitisik_mi=EVET" in cikti, cikti[-500:])
    iddia("21j korumali yokken kalan kutu, orijinalin ONEKIDIR (bitisik kesim)",
          metin.startswith(oku(a.kutu)),
          "kalan kutu orijinalin oneki DEGIL -> kesim bitisik degil")


def v22_ortadaki_koruma_atlanir(arac, kok):
    """[22] 🔴 K318 KOL-2 — jeton ORTADA: hem ALTINDAKI hem USTUNDEKI bloklar tasinir.

    ONCEKI DAVRANIS: yalniz 26..29 (4 blok) tasinirdi, kutu tavanin USTUNDE kalirdi.
    YENI: 26..29 VE 14..24 tasinir (BITISIK OLMAYAN kume), blok 25 YERINDE kalir.
    """
    print("\n[22] K318 KOL-2 — jeton ORTADA: tasinan kume BITISIK DEGIL, "
          "korumali blok YERINDE kalir")
    metin = kutu_uret_jetonlu(30, {25: BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    bek_tasinan, bek_kalan = oracle_granuler(metin, 300, 3, [25])
    iddia("22a oracle: tasinan kume 25'i ICERMIYOR", 25 not in bek_tasinan,
          "%r" % bek_tasinan)
    iddia("22b oracle: tasinan kume 25'in HEM ALTINDA HEM USTUNDE blok iceriyor "
          "(BITISIK DEGIL)",
          any(x > 25 for x in bek_tasinan) and any(x < 25 for x in bek_tasinan),
          "%r" % bek_tasinan)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("22c rc=0", rc == 0, cikti[-600:])
    iddia("22d BAGIMSIZ oracle ile ayni sayida blok tasindi (%d)" % len(bek_tasinan),
          ("tasinacak_blok=%d " % len(bek_tasinan)) in cikti, cikti[-600:])
    iddia("22e tasinan blok indeksleri oracle ile BIREBIR",
          ("tasinan_blok_indeksleri=%s "
           % ",".join(str(x + 1) for x in bek_tasinan)) in cikti, cikti[-600:])
    iddia("22f KORUMALI_BEKLEYEN=1", "KORUMALI_BEKLEYEN=1 " in cikti, cikti[-600:])
    iddia("22g yerinde_atlanan=1", "yerinde_atlanan=1 " in cikti, cikti[-600:])
    iddia("22h jeton HALA kutuda", BEKLEYEN_SATIR in oku(a.kutu))
    iddia("22i jeton arsive SIZMADI", BEKLEYEN_SATIR not in oku(a.arsiv))
    iddia("22j lossless GECTI (tasima MESRU, koruma her seyi durdurmadi)",
          "lossless_dogrulama=GECTI" in cikti, cikti[-300:])
    iddia("22k kutu tavanin ALTINA indi (kilit ACILDI — eskiden ustunde KALIRDI)",
          len(oku(a.kutu).splitlines()) <= 300,
          "sonra=%d" % len(oku(a.kutu).splitlines()))


def v23_koruma_denetimi(arac, kok):
    print("\n[23] K3-DENETIM — tasinan metne jeton SIZARSA D14 yakalar "
          "(planla dogru calissa bile)")
    metin = kutu_uret_ayracli(30)                 # jetonsuz, saglam fikstur
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3,
                    ortam={"PRUVO_KUTU_ARSIVLE_ARIZA": "koruma-jeton-sizdir"})
    iddia("23a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti[-500:]))
    iddia("23b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("23c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("23d 'HICBIR SEY YAZILMADI' beyani", "HICBIR SEY YAZILMADI" in cikti,
          cikti[-400:])
    # 🔴 HEDEF-KOL ATFI: "kirmizi geldi" kanit DEGIL — kirmizinin SEBEBI D14 mi?
    iddia("23e kirmizinin SEBEBI D14 koruma kolu (hedef-kol atfi)",
          "D14 KORUMA IHLALI" in cikti, cikti[-600:])


def v24_iki_kosum_birebir(arac, kok):
    print("\n[24] K6 — iki ardisik kosum: K1 ve K2 BIREBIR ayni rc/sayi")
    esler = (("K1", {29: BEKLEYEN_SATIR}), ("K2", {29: ISLENMIS_SATIR}))
    j = 0
    while j < len(esler):
        ad, jetonlar = esler[j]
        metin = kutu_uret_jetonlu(30, jetonlar)
        sonuclar = []
        t = 0
        while t < 2:
            alt = os.path.join(kok, "%s-tur%d" % (ad, t))
            os.makedirs(alt, exist_ok=True)
            a = Alan(alt, metin, "## eski arsiv blogu\n\ngovde\n")
            rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
            sonuclar.append((rc,
                             satir_al(cikti, "KORUMALI_BEKLEYEN="),
                             satir_al(cikti, "tasinacak_blok=")))
            t += 1
        iddia("24-%s rc BIREBIR ayni" % ad, sonuclar[0][0] == sonuclar[1][0],
              "%r" % (sonuclar,))
        iddia("24-%s KORUMALI_BEKLEYEN satiri BIREBIR ayni" % ad,
              sonuclar[0][1] == sonuclar[1][1], "%r" % (sonuclar,))
        iddia("24-%s tasinacak_blok satiri BIREBIR ayni" % ad,
              sonuclar[0][2] == sonuclar[1][2], "%r" % (sonuclar,))
        j += 1


# ---------------------------------------- K318 KOL-1: JETON KONUM EKSENI (25-27)
def v25_govde_anmasi_koruma_uretmez(arac, kok):
    """[25] 🔴 K318 KOL-1 — GOVDEDE anilan jeton KORUMA URETMEZ (yanlis pozitif).

    OLCULEN VAKA: canli kutuda jeton 7 konumda geciyordu, 4'u kuralin kendisini
    TARTISAN govde metniydi; o dort blok SUSUZ YERE kilitliydi ve kilit yukari
    yayilarak DORT commit'i durdurdu. Bu vaka o dort blogu temsil eder.
    """
    print("\n[25] K318 KOL-1 — jeton GOVDEDE, kapanis ISLENMIS -> blok KORUMASIZ")
    metin = kutu_uret_jetonlu(
        30, {29: ISLENMIS_SATIR},
        govde={29: "Not: bu blok `%s` kuralini TARTISIYOR, kendi kapanisi degil."
                   % BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("25a fikstur GERCEKTEN jetonu govdesinde tasiyor",
          metin.count(BEKLEYEN_SATIR) == 1, "sayi=%d" % metin.count(BEKLEYEN_SATIR))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("25b rc=0", rc == 0, cikti[-600:])
    iddia("25c 🔴 KORUMALI_BEKLEYEN=0 (govde anmasi KORUMA URETMEDI)",
          "KORUMALI_BEKLEYEN=0 " in cikti, cikti[-600:])
    iddia("25d govde_anmasi=1 ADIYLA basildi (hal GIZLENMEDI, SAYILDI)",
          "govde_anmasi=1 " in cikti, cikti[-600:])
    iddia("25e HUKUM=KORUMA_TUTTU BASILMADI", "HUKUM=KORUMA_TUTTU" not in cikti,
          cikti[-400:])
    iddia("25f blok GERCEKTEN tasindi (govdesindeki anma onu tutmadi)",
          BEKLEYEN_SATIR in oku(a.arsiv),
          "govde anmali blok arsive gitmedi -> hala kilitli")
    iddia("25g kutu tavanin ALTINA indi", len(oku(a.kutu).splitlines()) <= 300,
          "sonra=%d" % len(oku(a.kutu).splitlines()))
    iddia("25h lossless GECTI (D14 govde anmasina KIRMIZI YAKMADI)",
          "lossless_dogrulama=GECTI" in cikti, cikti[-400:])


def v26_kapanis_jetonu_hala_korur(arac, kok):
    """[26] 🔴 K318 KOL-1 KONTROL — daraltma GERCEK kapanisi ELEMEDI (minimal cift)."""
    print("\n[26] K318 KOL-1 KONTROL — ayni fiksturun kapanisi BEKLEYEN olunca "
          "blok HALA KORUNUR")
    govde = {29: "Not: bu blok `%s` kuralini TARTISIYOR, kendi kapanisi degil."
                 % BEKLEYEN_SATIR}
    metin = kutu_uret_jetonlu(30, {29: BEKLEYEN_SATIR}, govde=govde)
    ikiz = kutu_uret_jetonlu(30, {29: ISLENMIS_SATIR}, govde=govde)
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("26a v25 ile MINIMAL CIFT (tek fark KAPANIS satiri)",
          metin.replace("\n" + BEKLEYEN_SATIR + "\n\n---", "\n@\n\n---")
          == ikiz.replace("\n" + ISLENMIS_SATIR + "\n\n---", "\n@\n\n---"),
          "fiksturler kapanis satiri disinda da ayrisiyor")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("26b rc=0", rc == 0, cikti[-600:])
    iddia("26c 🔴 KORUMALI_BEKLEYEN=1 (gercek kapanis HALA korunuyor)",
          "KORUMALI_BEKLEYEN=1 " in cikti, cikti[-600:])
    iddia("26d sinif=KAPANIS ADIYLA basildi", "sinif=KAPANIS" in cikti, cikti[-600:])
    iddia("26e korumali blok arsive GITMEDI (baslik kutuda)",
          blok(29).splitlines()[0] in oku(a.kutu))
    iddia("26f korumali blogun basligi arsivde YOK",
          blok(29).splitlines()[0] not in oku(a.arsiv))


def v27_ayristirilamayan_blok_fail_closed(arac, kok):
    """[27] 🔴 K318 KOL-1 FAIL-CLOSED — kapanis konumu okunamazsa blok KORUNUR."""
    print("\n[27] K318 KOL-1 FAIL-CLOSED — KAPANMAMIS cit: blok siniri "
          "AYRISTIRILAMAZ -> jetonlu blok YINE korunur")
    metin = kutu_uret_jetonlu(30, {29: BEKLEYEN_SATIR}, acik_cit={29})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("27a rc=0", rc == 0, cikti[-600:])
    iddia("27b KORUMALI_BEKLEYEN=1", "KORUMALI_BEKLEYEN=1 " in cikti, cikti[-600:])
    iddia("27c 🔴 sinif=FAIL_CLOSED ADIYLA basildi (belirsizlik KORUMA yonunde)",
          "sinif=FAIL_CLOSED" in cikti, cikti[-600:])
    iddia("27d sebep ciktida ADIYLA geciyor (cit kapanmadi)",
          "CIT (```/~~~) ACILDI ama KAPANMADI" in cikti, cikti[-800:])
    iddia("27e jeton HALA kutuda", BEKLEYEN_SATIR in oku(a.kutu))
    iddia("27f jeton arsive SIZMADI", BEKLEYEN_SATIR not in oku(a.arsiv))


# --------------------------------- K318 KOL-2: KAYIPSIZLIK + KOTA KILIDI (28-30)
def v28_kayipsizlik_iki_eksen(arac, kok):
    """[28] 🔴 K318 KOL-2 — `tasinan + kalan == once` BLOK **VE** BAYT ekseninde."""
    print("\n[28] K318 KOL-2 — kayipsizlik IKI EKSENDE basilir ve TUTAR")
    metin = kutu_uret_jetonlu(30, {25: BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    once_bayt = len(metin.encode("utf-8"))
    bek_tasinan, _bek_kalan = oracle_granuler(metin, 300, 3, [25])
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("28a rc=0", rc == 0, cikti[-600:])
    iddia("28b 'KAYIPSIZLIK blok:' satiri ADIYLA basildi",
          "KAYIPSIZLIK blok:" in cikti, cikti[-600:])
    iddia("28c 'KAYIPSIZLIK bayt:' satiri ADIYLA basildi",
          "KAYIPSIZLIK bayt:" in cikti, cikti[-600:])
    iddia("28d blok ekseni TUTUYOR (once=30 toplam=30)",
          "KAYIPSIZLIK blok: once=30 " in cikti and " toplam=30 " in cikti,
          cikti[-600:])
    sonra = oku(a.kutu)
    arsiv = oku(a.arsiv)
    # 🔴 BAYT EKSENI BAGIMSIZ HESAPLANIR: arsiv dosyasinin BOYUT FARKI kullanilamaz
    # (aday_metinler eski arsiv ile ek arasina AYRAC koyar ve gerekirse sonuna `\n`
    # ekler; fark tasinan bayt sayisina ESIT DEGILDIR). Bunun yerine tasinan blok
    # kumesi ORACLE'dan, blok baytlari ORIJINAL METINDEN turetilir.
    _satirlar = metin.splitlines(keepends=True)
    _dilimler = _blok_dilimleri(metin)
    tasinan_bayt = 0
    _t = 0
    while _t < len(_dilimler):
        if _t in bek_tasinan:
            _b, _s = _dilimler[_t]
            tasinan_bayt += len("".join(_satirlar[_b:_s]).encode("utf-8"))
        _t += 1
    iddia("28e BAYT ekseni BAGIMSIZ dogrulandi (kalan + tasinan == once)",
          len(sonra.encode("utf-8")) + tasinan_bayt == once_bayt,
          "kalan=%d tasinan=%d once=%d"
          % (len(sonra.encode("utf-8")), tasinan_bayt, once_bayt))
    iddia("28e2 aracin BASTIGI bayt sayilari DISKTEKI kutuyla BIREBIR",
          ("KAYIPSIZLIK bayt: once=%d kalan=%d tasinan=%d toplam=%d"
           % (once_bayt, len(sonra.encode("utf-8")), tasinan_bayt,
              once_bayt)) in cikti, cikti[-600:])
    # BLOK ekseni DISKTEN: her orijinal blok tam olarak BIR kez var.
    eksik, ikiz = [], []
    i = 0
    while i < 30:
        b = blok(i).splitlines()[0]
        n = sonra.count(b) + arsiv.count(b)
        if n == 0:
            eksik.append(i)
        elif n > 1:
            ikiz.append(i)
        i += 1
    iddia("28f hicbir blok KAYBOLMADI", not eksik, "eksik=%r" % eksik)
    iddia("28g hicbir blok IKIZLENMEDI", not ikiz, "ikiz=%r" % ikiz)
    iddia("28h oksuz govde 0 (yerinde atlama govde OKSUZ birakmadi)",
          "oksuz_govde_kutu=0" in cikti and "oksuz_govde_ek=0" in cikti, cikti[-600:])
    # ARSIV SIRASI OZGUN: tasinan basliklar arsivde orijinal siralariyla.
    tasinan_baslik = [blok(i).splitlines()[0] for i in range(30)
                      if blok(i).splitlines()[0] in arsiv]
    konumlar = [arsiv.index(b) for b in tasinan_baslik]
    iddia("28i arsivde OZGUN SIRA korundu (artan konum)",
          konumlar == sorted(konumlar), "%r" % konumlar[:6])


def v29_blok_dus_arizasi(arac, kok):
    """[29] 🔴 K318 KOL-2 DENETIM — GRANULER birlestirmenin actigi yeni ariza sinifi.

    Bitisik dilimlemede "kalan" tek dilimdi; artik parcalarin birlestirilmesidir ve
    bir parcanin DUSMESI mumkun. Bu ariza YAKALANMAK ZORUNDA.
    """
    print("\n[29] K318 KOL-2 — KALAN bloklardan biri birlestirmede DUSERSE "
          "lossless KIRMIZI yanar")
    metin = kutu_uret_jetonlu(30, {25: BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3,
                    ortam={"PRUVO_KUTU_ARSIVLE_ARIZA": "kutu-blok-dus"})
    iddia("29a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti[-600:]))
    iddia("29b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("29c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("29d 'HICBIR SEY YAZILMADI' beyani", "HICBIR SEY YAZILMADI" in cikti,
          cikti[-500:])
    # 🔴 HEDEF-KOL ATFI: kirmizinin SEBEBI korunum kollari mi?
    iddia("29e kirmizinin SEBEBI BAYT korunumu kolu (D1c)",
          "D1c BAYT KORUNUMU" in cikti, cikti[-800:])
    iddia("29f kirmizinin SEBEBI AYRICA SATIR korunumu kolu (D2)",
          "D2 SATIR KORUNUMU" in cikti, cikti[-800:])
    iddia("29g kirmizinin SEBEBI AYRICA PARTISYON kolu (D1)",
          "D1 PARTISYON (KUTU)" in cikti, cikti[-800:])


def v30_tasinabilir_sifir_koruma_tuttu(arac, kok):
    """[30] 🔴 KOL-3'UN GIRDISI — `koru` DISINDAKI HER blok korumaliysa is YOKTUR.

    Kapi (defter-kota-kapisi.py) tam bu hali `HUKUM=KORUMA_TUTTU` + `tasinabilir=0`
    olarak TUKETIR; jetonlar burada SAYIYLA cakilir.
    """
    print("\n[30] KOL-3 GIRDISI — tasinabilir=0 + HUKUM=KORUMA_TUTTU jetonlari")
    metin = kutu_uret_jetonlu(5, {3: BEKLEYEN_SATIR, 4: BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    iddia("30a fikstur tavani asiyor", len(metin.splitlines()) > 20,
          "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=20, koru=3)
    iddia("30b rc=0 (BOZULMA degil, ILAN EDILMIS duraklama)", rc == 0, cikti[-600:])
    iddia("30c tasinabilir=0 jetonu basildi", "tasinabilir=0 " in cikti, cikti[-600:])
    iddia("30d HUKUM=KORUMA_TUTTU jetonu basildi", "HUKUM=KORUMA_TUTTU" in cikti,
          cikti[-600:])
    iddia("30e KORU_TUTTU ile KARISTIRILMADI (sebep ayrimi duruyor)",
          "HUKUM=KORU_TUTTU" not in cikti, cikti[-600:])
    iddia("30f 'NE YAPILMALI' yonergesi basildi", "NE YAPILMALI:" in cikti,
          cikti[-600:])
    iddia("30g kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("30h arsiv DEGISMEDI", sha(a.arsiv) == h2)


# =========================== K329 — ACIK CIP (KAPANISSIZ `BASLIYORUM`) ===========
# 🔴 OLCULEN VAKA (27 Agu 23:38 + 28 Agu, ikinci kez): cip `KraL-NobetTuru-27Agu`
# `BASLIYORUM` blogunu yazdi, BASKA bir cipin rotasyonu o blogu CIP KOSARKEN arsive
# tasidi. Kayip yok, GORUNURLUK yok. Fikstur o vakanin SEKLINI tasir.
ACIK_AD = "KraL-NobetTuru-27Agu"      # kapanisi OLMAYAN cip -> VETO
KAPALI_AD = "KraL-Kapanan-27Agu"      # kapanisi OLAN cip    -> KONTROL, tasinmali

CIP_GOVDE = ("\n"
             "**Olcum:** sentetik cip blogu %d — kabul testi fiksturu.\n"
             "\n"
             "- Sayi: %d kayit, sapma 0.\n"
             "- Karar: kapi fail-closed kalir.\n"
             "\n"
             "— MimarA\n"
             "\n")


def cip_blogu(i, baslik, kuyruk=None):
    g = baslik + "\n" + (CIP_GOVDE % (i, 100 + i))
    if kuyruk:
        g += kuyruk + "\n\n"
    return g


def kutu_uret_k329(tuzak_kapanis=False, dolgu=2):
    """K329 fiksturu — 27 Agu vakasinin SEKLI (AYRACLI, canli kutu gelenegi).

    Blok sirasi (YENI -> ESKI, 1-tabanli):
      1-3  `koru` tabani dolgusu (dokunulmaz)
      4    `KAPALI_AD` KAPANIS blogu  -> 6. blogu SERBEST birakan tek sey
      5    TUZAK: baslikta `ACIK_AD` GECER ama blok KAPANIS DEGIL
      6    `KAPALI_AD` BASLIYORUM     -> KONTROL: TASINMALI
      7    `ACIK_AD`   BASLIYORUM     -> VETO: TASINMAMALI
      8..  eski generic dolgu bloklari

    tuzak_kapanis=True -> 5. bloga TEK SATIR (`ISLENMIS_SATIR`) eklenir ve blok
    o cipin GERCEK kapanisi olur. Iki fikstur MINIMAL CIFTTIR: aralarindaki tek
    fark o satirdir, yani 7. blogun kaderindeki degisiklik YALNIZCA eslestirme
    olcutune atfedilebilir.
    """
    basliklar = [
        # 🔴 Dolgu bloklari BILEREK `BASLIYORUM` TASIMAZ: tasisalardi `koru` tabani
        # onlari zaten korurdu ama sayaca girer ve `ACIK_BASLIYORUM=1` iddiasi
        # olcmek istedigimiz bloktan BASKA bir sebeple dogru/yanlis cikardi.
        ("## 2026-08-28 — MimarA → MimarB: koru dolgusu 1", None),
        ("## 2026-08-28 — ✅ SAYILI KAPANIS · cip `KraL-Yeni2-28Agu`", None),
        ("## 2026-08-28 — ✅ SAYILI KAPANIS · cip `KraL-Yeni3-28Agu`", None),
        ("## 2026-08-27 — ✅ SAYILI KAPANIŞ · çip `%s` — is bitti" % KAPALI_AD, None),
        ("## 2026-08-27 — 🔍 MimarB bagimsiz dogrulama · cip `%s` — rapor DOGRULANDI"
         % ACIK_AD, ISLENMIS_SATIR if tuzak_kapanis else None),
        ("## 2026-08-27 — 🟢 BAŞLIYORUM · çip `%s`" % KAPALI_AD, None),
        ("## 2026-08-27 — 🚀 BAŞLIYORUM · çip `%s`" % ACIK_AD, None),
    ]
    parcalar = [FM]
    i = 0
    while i < len(basliklar):
        baslik, kuyruk = basliklar[i]
        parcalar.append(cip_blogu(i, baslik, kuyruk) + "---\n\n")
        i += 1
    j = 0
    while j < dolgu:
        parcalar.append(blok(100 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


# TAVAN, fikstur olçüsüne göre seçildi: veto TUTARKEN bile kutu tavanin ALTINA
# inmeli (v32h). Aksi halde "kutu tavan ustunde kaldi" hali vetodan mi fikstur
# darligindan mi geliyor AYIRT EDILEMEZDI.
K329_TAVAN = 55
K329_ACIK_IDX = 6        # 0-tabanli: `ACIK_AD` BASLIYORUM blogu
K329_KONTROL_IDX = 5     # 0-tabanli: `KAPALI_AD` BASLIYORUM blogu
K329_TUZAK_IDX = 4       # 0-tabanli: adi ANAN ama kapanis OLMAYAN blok


def _k329_baslik(metin, idx):
    """idx. blogun BASLIK satiri — araci CAGIRMADAN, fikstur metninden."""
    satirlar = metin.splitlines(keepends=True)
    bas, _son = _blok_dilimleri(metin)[idx]
    return satirlar[bas].rstrip("\n")


def v31_acik_basliyorum_veto(arac, kok):
    """[31] 🔴 K329 ASIL — kapanissiz `BASLIYORUM` blogu TASINMAZ ve ADIYLA basilir."""
    print("\n[31] K329 ASIL — kapanisi OLMAYAN `BASLIYORUM` blogu ROTASYONA GIRMEZ")
    metin = kutu_uret_k329()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    acik_baslik = _k329_baslik(metin, K329_ACIK_IDX)
    iddia("31a fikstur GERCEKTEN tavani asiyor",
          len(metin.splitlines()) > K329_TAVAN, "satir=%d" % len(metin.splitlines()))
    # 🔴 BAGIMSIZ ORACLE: beklenen tasima kumesi aracin kodundan DEGIL, "6. blok
    # sabittir" varsayimindan TURER (elle yazilan sayi kaynagindan ayrisirdi).
    bek_tasinan, bek_kalan = oracle_granuler(metin, K329_TAVAN, 3, [K329_ACIK_IDX])
    iddia("31b oracle: acik blok DISINDA tasinacak blok VAR", len(bek_tasinan) > 0,
          "oracle bos")
    iddia("31c oracle: acik blok (%d) tasinanlarda DEGIL" % (K329_ACIK_IDX + 1),
          K329_ACIK_IDX not in bek_tasinan, "%r" % bek_tasinan)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K329_TAVAN, koru=3)
    iddia("31d rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-900:]))
    iddia("31e ACIK_BASLIYORUM=1 ADIYLA basildi", "ACIK_BASLIYORUM=1 " in cikti,
          cikti[-900:])
    iddia("31f 🔴 atlanan blok CIP ADIYLA basildi (sessiz atlama YASAK)",
          ("ACIK_BASLIYORUM_ADLARI=%s" % ACIK_AD) in cikti, cikti[-900:])
    iddia("31g sinif=ACIK_BASLIYORUM ADIYLA basildi", "sinif=ACIK_BASLIYORUM" in cikti,
          cikti[-900:])
    iddia("31h 🔴 acik blok HALA KUTUDA (gorunurluk KORUNDU)",
          acik_baslik in oku(a.kutu), "baslik kutudan dustu: %s" % acik_baslik)
    iddia("31i 🔴 acik blok ARSIVE SIZMADI", acik_baslik not in oku(a.arsiv))
    iddia("31j arac BAGIMSIZ oracle ile ayni sayida blok tasidi (%d)"
          % len(bek_tasinan),
          ("tasinacak_blok=%d " % len(bek_tasinan)) in cikti, cikti[-900:])
    iddia("31k lossless GECTI (veto KIRMIZI yakmadi, ATLADI)",
          "lossless_dogrulama=GECTI" in cikti, cikti[-600:])
    iddia("31l 'NE YAPILMALI' yonergesi basildi (ne yapilacagi SOYLENDI)",
          "sayili KAPANISINI kutuya YAZSIN" in cikti, cikti[-900:])


def v32_kapanisli_blok_hala_tasinir(arac, kok):
    """[32] 🔴 K329 KONTROL — veto rotasyonu KILITLEMEZ; kapanisli blok YINE tasinir.

    Bugun kutu UC KEZ tavana dayandi; tasimayi tumden durduran bir kol onarim degil
    YENI BIR TIKANMA olurdu. Bu vaka o gerilemeyi olcer.
    """
    print("\n[32] K329 KONTROL — kapanisi OLAN `BASLIYORUM` blogu YINE TASINIR")
    metin = kutu_uret_k329()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1 = sha(a.kutu)
    kontrol_baslik = _k329_baslik(metin, K329_KONTROL_IDX)
    bek_tasinan, bek_kalan = oracle_granuler(metin, K329_TAVAN, 3, [K329_ACIK_IDX])
    iddia("32a oracle: KONTROL blogu (%d) TASINANLARDA" % (K329_KONTROL_IDX + 1),
          K329_KONTROL_IDX in bek_tasinan, "%r" % bek_tasinan)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K329_TAVAN, koru=3)
    iddia("32b rc=0", rc == 0, cikti[-900:])
    iddia("32c 🔴 is GERCEKTEN yapildi — kutu DEGISTI (veto her seyi kilitlemedi)",
          sha(a.kutu) != h1)
    iddia("32d KONTROL blogu ARSIVE gitti", kontrol_baslik in oku(a.arsiv),
          "kapanisli blok tasinmadi -> veto KILITLEDI")
    iddia("32e KONTROL blogu kutudan CIKTI", kontrol_baslik not in oku(a.kutu))
    iddia("32f kapanmis_basliyorum=1 ADIYLA basildi (serbest birakilan SAYILDI)",
          "kapanmis_basliyorum=1 " in cikti, cikti[-900:])
    iddia("32g kutu BAGIMSIZ oracle'in hesapladigi satira indi (%d)" % bek_kalan,
          len(oku(a.kutu).splitlines()) == bek_kalan,
          "arac %d, oracle %d" % (len(oku(a.kutu).splitlines()), bek_kalan))
    iddia("32h kutu tavanin ALTINA indi (kilit ACILDI)",
          len(oku(a.kutu).splitlines()) <= K329_TAVAN,
          "sonra=%d tavan=%d" % (len(oku(a.kutu).splitlines()), K329_TAVAN))
    iddia("32i yerinde_atlanan=1 (bitisik kuyruk DEGIL — acik blok YERINDE atlandi)",
          "yerinde_atlanan=1 " in cikti, cikti[-900:])


def v33_yanlis_eslesme(arac, kok):
    """[33] 🔴 K329 ESLESTIRME EKSENI — MINIMAL CIFT, iki yonlu.

    (A) Adi ANAN ama KAPANIS OLMAYAN blok vetoyu KALDIRMAZ (yanlis eslesme kapali).
    (B) AYNI fiksture TEK SATIR eklenip o blok GERCEK kapanis olunca veto KALKAR.
    Fark tek satir oldugu icin davranis degisikligi YALNIZCA eslestirme olcutune
    atfedilebilir ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
    """
    print("\n[33] K329 ESLESTIRME — adi ANMAK kapanis DEGILDIR (minimal cift)")
    tuzakli = kutu_uret_k329(tuzak_kapanis=False)
    kapanisli = kutu_uret_k329(tuzak_kapanis=True)
    iddia("33a MINIMAL CIFT: iki fikstur TEK SATIR farkli",
          kapanisli.replace("\n" + ISLENMIS_SATIR + "\n\n", "\n", 1) == tuzakli,
          "fiksturler kapanis satiri disinda da ayrisiyor")
    iddia("33b tuzak blogun basliginda acik cipin ADI GERCEKTEN geciyor",
          ACIK_AD in _k329_baslik(tuzakli, K329_TUZAK_IDX),
          _k329_baslik(tuzakli, K329_TUZAK_IDX))

    acik_baslik = _k329_baslik(tuzakli, K329_ACIK_IDX)
    os.makedirs(os.path.join(kok, "a"), exist_ok=True)
    a = Alan(os.path.join(kok, "a"), tuzakli, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K329_TAVAN, koru=3)
    iddia("33c (A) rc=0", rc == 0, cikti[-900:])
    iddia("33d (A) 🔴 ACIK_BASLIYORUM=1 — adi ANMAK vetoyu KALDIRMADI",
          "ACIK_BASLIYORUM=1 " in cikti, cikti[-900:])
    iddia("33e (A) acik blok kutuda KALDI", acik_baslik in oku(a.kutu))

    os.makedirs(os.path.join(kok, "b"), exist_ok=True)
    b = Alan(os.path.join(kok, "b"), kapanisli, "## eski arsiv blogu\n\ngovde\n")
    rc2, cikti2 = kos(arac, b.kutu, b.arsiv, b.kilit, tavan=K329_TAVAN, koru=3)
    iddia("33f (B) rc=0", rc2 == 0, cikti2[-900:])
    iddia("33g (B) 🔴 ACIK_BASLIYORUM=0 — GERCEK kapanis vetoyu KALDIRDI",
          "ACIK_BASLIYORUM=0 " in cikti2, cikti2[-900:])
    iddia("33h (B) acik blok ARTIK tasindi", acik_baslik in oku(b.arsiv),
          "kapanis geldi ama blok hala kutuda -> veto KALICI kilit")
    iddia("33i (B) kapanmis_basliyorum=2 (iki cipin de kapanisi bulundu)",
          "kapanmis_basliyorum=2 " in cikti2, cikti2[-900:])


def v34_d17_denetimi(arac, kok):
    """[34] 🔴 K329 DENETIM — tasinan metne acik blok SIZARSA D17 KIRMIZI yakar."""
    print("\n[34] K329 DENETIM — `basliyorum-sizdir` arizasi D17'de yakalanmali")
    metin = kutu_uret_k329()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K329_TAVAN, koru=3,
                    ortam={"PRUVO_KUTU_ARSIVLE_ARIZA": "basliyorum-sizdir"})
    iddia("34a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti[-900:]))
    iddia("34b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("34c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("34d 'HICBIR SEY YAZILMADI' beyani", "HICBIR SEY YAZILMADI" in cikti,
          cikti[-600:])
    # 🔴 HEDEF-KOL ATFI: kirmizinin SEBEBI D17 olmali — "kirmizi geldi" YETMEZ.
    iddia("34e kirmizinin SEBEBI D17 ACIK CIP kolu (hedef-kol atfi)",
          "D17 ACIK CIP IHLALI" in cikti, cikti[-1200:])
    iddia("34f sizan cipin ADI kirmizida geciyor", "ZzZ-Sizinti-28Agu" in cikti,
          cikti[-1200:])


def v35_basliyorum_govde_anmasi(arac, kok):
    """[35] 🔴 K329 KONUM OLCUTU — GOVDEDE anilan `BASLIYORUM` veto URETMEZ.

    K318 KOL-1'in kardesi: genis tespit, kuralin kendisini TARTISAN bloklari susuz
    yere kilitler ve kilit yukari yayilir (o vaka DORT commit'i durdurmustu).
    """
    print("\n[35] K329 KONUM OLCUTU — jeton GOVDEDE, BASLIKTA degil -> veto YOK")
    metin = kutu_uret_jetonlu(
        30, {},
        govde={29: "Not: bu blok `BASLIYORUM` kuralini TARTISIYOR, kendisi acik "
                   "bir cip DEGIL."})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("35a fikstur jetonu GOVDESINDE tasiyor, BASLIKTA degil",
          metin.count("BASLIYORUM") == 1
          and "BASLIYORUM" not in blok(29).splitlines()[0],
          "sayi=%d" % metin.count("BASLIYORUM"))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    iddia("35b rc=0", rc == 0, cikti[-900:])
    iddia("35c 🔴 ACIK_BASLIYORUM=0 (govde anmasi veto URETMEDI)",
          "ACIK_BASLIYORUM=0 " in cikti, cikti[-900:])
    iddia("35d basliyorum_govde_anmasi=1 ADIYLA basildi (hal GIZLENMEDI, SAYILDI)",
          "basliyorum_govde_anmasi=1 " in cikti, cikti[-900:])
    iddia("35e blok GERCEKTEN tasindi (govdesindeki anma onu tutmadi)",
          blok(29).splitlines()[0] in oku(a.arsiv))
    iddia("35f kutu tavanin ALTINA indi", len(oku(a.kutu).splitlines()) <= 300,
          "sonra=%d" % len(oku(a.kutu).splitlines()))
    iddia("35g lossless GECTI (D17 govde anmasina KIRMIZI YAKMADI)",
          "lossless_dogrulama=GECTI" in cikti, cikti[-600:])


def v36_gercek_vaka_regresyonu(arac, kok):
    """[36] 🔴 K329 REGRESYON — UC GERCEK VAKANIN BASLIK SEKLI (sentetik degil).

    Mimarin olcumu (28 Agu): kalem bir gunde UC KEZ atesledi ve ucu de ayni sekilde
    arsive dustu:
      ① `mimar-posta-kutusu-arsiv.md:52842` — ASCII `BASLIYORUM`, backtick'li ad
      ② `...:53553`                          — ad BACKTICK'SIZ, jeton **kalin**
      ③ `...:53601`                          — emoji + Turkce `BAŞLIYORUM`, backtick'li
    Ucu de AYNI kolu olcer ama UC AYRI YAZIM SARMALINDAN gecer; biri kacarsa kol o
    sarmalda KORDUR. ②'nin sekli bu vakayi yazarken KOL DEGISTIRDI — dar cikarim onu
    `ACIK_ADSIZ` sayiyordu (korunuyordu ama ADI basilamiyordu), gevsek cikarim eklendi.
    🔴 Fikstur yalnizca BASLIK SEKLINI tasir; gercek blok govdeleri (ic rapor metni)
    KOPYALANMAZ.
    """
    print("\n[36] K329 REGRESYON — uc GERCEK vakanin baslik sarmali (52842/53553/53601)")
    vakalar = [
        ("## 2026-08-27 — BASLIYORUM · cip `KraL-NobetTuru-27Agu` — nobet turu teshisi",
         "KraL-NobetTuru-27Agu", "ACIK_BASLIYORUM", "arsiv:52842"),
        ("## 2026-08-28 — KraL-K333-SabahPATH-28Agu · **BAŞLIYORUM**",
         "KraL-K333-SabahPATH-28Agu", "ACIK_GEVSEK_AD", "arsiv:53553"),
        ("## 2026-08-28 — 🟡 BAŞLIYORUM · çip `KraL-K330-ArtikKorlugu-28Agu` (kalem K330)",
         "KraL-K330-ArtikKorlugu-28Agu", "ACIK_BASLIYORUM", "arsiv:53601"),
    ]
    parcalar = [FM]
    n = 0
    while n < 3:                                   # koru tabani (BASLIYORUM TASIMAZ)
        parcalar.append(cip_blogu(n, "## 2026-08-28 — MimarA → MimarB: koru dolgusu %d"
                                  % n) + "---\n\n")
        n += 1
    for k, (baslik, _ad, _sinif, _kaynak) in enumerate(vakalar):
        parcalar.append(cip_blogu(10 + k, baslik) + "---\n\n")
    j = 0
    while j < 2:
        parcalar.append(blok(200 + j) + "---\n\n")
        j += 1
    metin = "".join(parcalar)
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K329_TAVAN, koru=3)
    iddia("36a rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-900:]))
    iddia("36b UCU DE acik sayildi (ACIK_BASLIYORUM=3)",
          "ACIK_BASLIYORUM=3 " in cikti, cikti[-1200:])
    for baslik, ad, sinif, kaynak in vakalar:
        iddia("36c %s — cip ADIYLA basildi (%s)" % (kaynak, ad),
              ad in cikti, cikti[-1400:])
        iddia("36d %s — sinif=%s ADIYLA basildi" % (kaynak, sinif),
              ("sinif=%s" % sinif) in cikti, cikti[-1400:])
        iddia("36e %s — blok KUTUDA kaldi, arsive SIZMADI" % kaynak,
              baslik in oku(a.kutu) and baslik not in oku(a.arsiv))
    # 🔴 KONTROL: veto ucunu de tuttu ama rotasyon YINE is yapti (dolgu bloklari gitti).
    iddia("36f rotasyon KILITLENMEDI — eski dolgu bloklari tasindi",
          blok(201).splitlines()[0] in oku(a.arsiv), cikti[-900:])


# ------------------------------- K341: KAPANIS JETONU CEVRIMI (--kapanislari-isle)
# 🔴 NEDEN VAR (Okan, 28 Agu): K313g korumasi bekleyen kapanislari dogru kilitliyordu,
# ama kilidi ACAN cevrim ARACTA YOKTU -> her gun bir mimar kutuyu ELLE duzenliyordu.
# Elle duzenleme kutuya dokunmaktir ve o dokunus 27 Agu'da kutuyu SILDI
# ([[ortak-kutu-silinebilir-kurtarma-disiplini]]). Bu vakalar cevrimin ARACTA,
# KILIT ALTINDA, DOGRULAMALI ve DOKUNULMAZLIK sinirlariyla calistigini olcer.
CEVRIM_TAVAN = 300
CEVRIM_GOVDE_IDX = 5      # jetonu YALNIZ govdesinde anan blok (dokunulmaz)
CEVRIM_KAPANIS_IDX = (10, 20)   # gercek kapanis jetonu tasiyan bloklar (cevrilir)
CEVRIM_FAILCLOSED_IDX = 29      # kapanmamis cit -> AYRISTIRILAMAZ (dokunulmaz)


def kutu_uret_k341():
    """30 blokluk kutu: 2 gercek kapanis + 1 govde anmasi + 1 fail-closed blok."""
    jetonlar = {}
    for i in CEVRIM_KAPANIS_IDX:
        jetonlar[i] = BEKLEYEN_SATIR
    jetonlar[CEVRIM_FAILCLOSED_IDX] = BEKLEYEN_SATIR
    return kutu_uret_jetonlu(
        30, jetonlar,
        govde={CEVRIM_GOVDE_IDX: "not: bu blok %s kuralini TARTISIYOR" % BEKLEYEN_SATIR},
        acik_cit={CEVRIM_FAILCLOSED_IDX})


def _blok_basligi(metin, idx):
    satirlar = metin.splitlines(keepends=True)
    bas, _son = _blok_dilimleri(metin)[idx]
    return satirlar[bas].rstrip("\n")


def v37_cevrim_kilidi_acar(arac, kok):
    """[37] 🔴 K341 ASIL — cevrim KORUMAYI KALDIRIR ve blok rotasyona ACILIR.

    IKI YONLU MINIMAL CIFT: AYNI fikstur bayraksiz ve bayrakli kosulur. Tek degisken
    bayraktir; bayraksiz kosum TABANDIR ([[olcut-civilenirken-taban-olculmeli]]).
    """
    print("\n[37] K341 ASIL — `--kapanislari-isle` bekleyen kapanisi ACAR")
    metin = kutu_uret_k341()
    kapanis_basliklari = [_blok_basligi(metin, i) for i in CEVRIM_KAPANIS_IDX]

    # ---- TABAN: bayraksiz kosum (bugunku davranis) ----
    t = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc0, cikti0 = kos(arac, t.kutu, t.arsiv, t.kilit, tavan=CEVRIM_TAVAN, koru=3)
    iddia("37a TABAN rc=0", rc0 == 0, cikti0[-600:])
    iddia("37b TABAN: 3 blok KORUMALI (2 kapanis + 1 fail-closed)",
          "KORUMALI_BEKLEYEN=3 " in cikti0, cikti0[-900:])
    iddia("37c TABAN: cevrim KAPALI oldugu ADIYLA basildi",
          "CEVRIM=0 kip=KAPALI" in cikti0, cikti0[-900:])
    for b in kapanis_basliklari:
        iddia("37d TABAN: kapanis blogu KUTUDA kaldi (koruma tuttu) | %s" % b[:40],
              b in oku(t.kutu) and b not in oku(t.arsiv))

    # ---- CEVRIMLI kosum ----
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=CEVRIM_TAVAN, koru=3,
                    kapanislari_isle=True)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    iddia("37e rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1200:]))
    iddia("37f CEVRIM=2 ADIYLA basildi (fail-closed blok CEVRILMEDI)",
          "CEVRIM=2 " in cikti, cikti[-1400:])
    iddia("37g atlanan_fail_closed=1 ADIYLA basildi (sessiz atlama YASAK)",
          "atlanan_fail_closed=1 " in cikti, cikti[-1400:])
    iddia("37h cevrim dogrulamasi GECTI ve iddia sayisi TURETILDI",
          "cevrim_dogrulama=GECTI (iddia=8," in cikti, cikti[-1400:])
    # 🔴 ASIL OLCUM: kilit ACILDI mi — koruma 3'ten 1'e dustu ve bloklar TASINDI.
    iddia("37i 🔴 KORUMALI_BEKLEYEN 3 -> 1 (yalniz fail-closed blok kaldi)",
          "KORUMALI_BEKLEYEN=1 " in cikti, cikti[-1400:])
    # 🔴 BAGIMSIZ ORACLE: cevrimden SONRA sabit kume yalniz {fail-closed blok}. Hangi
    # blogun TASINDIGI su seviyesinden turer — "hepsi arsive iner" diye ELLE yazilan
    # beklenti kaynagindan ayrisirdi ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]).
    bek_tasinan, _bek_kalan = oracle_granuler(metin, CEVRIM_TAVAN, 3,
                                              [CEVRIM_FAILCLOSED_IDX])
    iddia("37j0 oracle: cevrilen bloklardan EN AZ biri tasinir, EN AZ biri kalir "
          "(vaka iki yonu de olcuyor)",
          any(i in bek_tasinan for i in CEVRIM_KAPANIS_IDX)
          and any(i not in bek_tasinan for i in CEVRIM_KAPANIS_IDX),
          "tasinan=%r kapanis=%r" % (bek_tasinan, CEVRIM_KAPANIS_IDX))
    for i, b in zip(CEVRIM_KAPANIS_IDX, kapanis_basliklari):
        if i in bek_tasinan:
            iddia("37j 🔴 cevrilen blok %d ARSIVE gitti (rotasyona ACILDI) | %s"
                  % (i + 1, b[:40]),
                  b in arsiv_s and b not in kutu_s,
                  "kutuda=%s arsivde=%s" % (b in kutu_s, b in arsiv_s))
        else:
            # Su seviyesi doldugu icin tasinmadi — ama jetonu CEVRILDI, yani
            # BIR SONRAKI turda rotasyona ACIK. Koruma artik onu KILITLEMIYOR.
            iddia("37j 🔴 cevrilen blok %d kutuda kaldi (su seviyesi) ama KORUMASIZ "
                  "| %s" % (i + 1, b[:40]),
                  b in kutu_s and b not in arsiv_s,
                  "kutuda=%s arsivde=%s" % (b in kutu_s, b in arsiv_s))
    cevrilmis_satir = BEKLEYEN_SATIR.replace("ARŞİVLENEBİLİRİM", "ARŞİVLENDİ")
    iddia("37k 🔴 ISLENMIS bicimli kapanis satiri HEM arsivde HEM kutuda GORUNUYOR",
          cevrilmis_satir in arsiv_s and cevrilmis_satir in kutu_s,
          "arsiv=%s kutu=%s" % (cevrilmis_satir in arsiv_s, cevrilmis_satir in kutu_s))
    iddia("37l 🔴 cevrilen bloklarin BEKLEYEN jetonu HICBIR duzlemde kalmadi "
          "(yalniz fail-closed + govde anmasi kutuda)",
          arsiv_s.count(BEKLEYEN_SATIR) == 0 and kutu_s.count(BEKLEYEN_SATIR) == 2,
          "kutu=%d arsiv=%d" % (kutu_s.count(BEKLEYEN_SATIR),
                                arsiv_s.count(BEKLEYEN_SATIR)))
    iddia("37m rotasyon lossless GECTI (cevrim kayipsizligi BOZMADI)",
          "lossless_dogrulama=GECTI" in cikti, cikti[-800:])
    iddia("37n kutu tavanin ALTINA indi (kota kilidi ACILDI)",
          len(kutu_s.splitlines()) <= CEVRIM_TAVAN,
          "sonra=%d" % len(kutu_s.splitlines()))
    iddia("37o arac BAGIMSIZ oracle ile ayni sayida blok tasidi (%d)"
          % len(bek_tasinan),
          ("tasinacak_blok=%d " % len(bek_tasinan)) in cikti, cikti[-1400:])


def v38_cevrim_dokunulmazliklari(arac, kok):
    """[38] 🔴 K341 DOKUNULMAZLIK — cevrim GOVDE ANMASINA ve AYRISTIRILAMAYAN bloga
    DOKUNMAZ; kapanis satirinda da JETON DISINDA tek bayt degismez."""
    print("\n[38] K341 DOKUNULMAZLIK — govde anmasi + fail-closed blok DOKUNULMAZ")
    metin = kutu_uret_k341()
    govde_satiri = "not: bu blok %s kuralini TARTISIYOR" % BEKLEYEN_SATIR
    fc_baslik = _blok_basligi(metin, CEVRIM_FAILCLOSED_IDX)
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=CEVRIM_TAVAN, koru=3,
                    kapanislari_isle=True)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    iddia("38a rc=0", rc == 0, cikti[-1200:])
    iddia("38b 🔴 GOVDE ANMASI satiri BIREBIR duruyor (cevrilmedi)",
          govde_satiri in kutu_s, "govde satiri degisti")
    iddia("38c govde anmasi SAYILDI ve ADIYLA basildi",
          "CEVRIM GOVDE ANMASI=1 blok" in cikti, cikti[-1400:])
    iddia("38d 🔴 FAIL_CLOSED blok CEVRILMEDI ve sinifi ADIYLA basildi",
          "sinif=FAIL_CLOSED): blok yapisi AYRISTIRILAMADI" in cikti, cikti[-1400:])
    iddia("38e FAIL_CLOSED blok HALA kutuda, BEKLEYEN jetonuyla",
          fc_baslik in kutu_s and BEKLEYEN_SATIR in kutu_s)
    iddia("38f FAIL_CLOSED blok arsive SIZMADI", fc_baslik not in arsiv_s)
    # 🔴 SATIR ICI DOKUNULMAZLIK: cevrilen satirda jeton DISINDA hicbir sey degismez.
    # Olcut: cevrilen satirin ISLENMIS hali, BEKLEYEN halinin tek ikamesine ESIT.
    bek_islenmis = BEKLEYEN_SATIR.replace("ARŞİVLENEBİLİRİM", "ARŞİVLENDİ")
    iddia("38g 🔴 cevrilen satir = eski satirin TEK JETON IKAMESI (%r)" % bek_islenmis,
          bek_islenmis in arsiv_s, "cevrilen satir sarmali bozuldu")
    iddia("38h cevrilen blok sayisi kadar ✓ satiri basildi (2)",
          cikti.count("  ✓ CEVRILDI blok ") == 2, cikti[-1400:])


def v39_cevrim_sentetik_ariza(arac, kok):
    """[39] 🔴 K341 DENETIM — cevrim dogrulamasi (C1-C8) GERCEKTEN kirmizi yakiyor mu?

    Uc ariza sinifi: satir dusurme (C1/C2), govde anmasini da cevirme (C2 —
    DOKUNULMAZLIK ihlali), ilgisiz satiri bozma (C2). Her birinde HICBIR SEY
    yazilmamali: kutu VE arsiv sha'lari DEGISMEMELI.
    """
    print("\n[39] K341 DENETIM — sentetik cevrim arizasi -> KIRMIZI, hicbir sey yazilmaz")
    metin = kutu_uret_k341()
    for kod in ("cevrim-satir-dus", "cevrim-govde-cevir", "cevrim-icerik-boz"):
        a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
        h1, h2 = sha(a.kutu), sha(a.arsiv)
        rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=CEVRIM_TAVAN, koru=3,
                        kapanislari_isle=True,
                        ortam={"PRUVO_KUTU_ARSIVLE_ARIZA": kod})
        iddia("39a %s -> rc=1 (KIRMIZI)" % kod, rc == 1,
              "rc=%d\n%s" % (rc, cikti[-1000:]))
        iddia("39b %s -> 'CEVRIM DOGRULAMASI KIRMIZI' beyani basildi" % kod,
              "CEVRIM DOGRULAMASI KIRMIZI" in cikti, cikti[-1000:])
        iddia("39c %s -> KUTU diskte DEGISMEDI" % kod, sha(a.kutu) == h1)
        iddia("39d %s -> ARSIV diskte DEGISMEDI" % kod, sha(a.arsiv) == h2)


def v40_cevrim_bayraksiz_gerileme_yok(arac, kok):
    """[40] 🔴 K341 GERILEME KONTROLU — bayrak YOKKEN davranis BIREBIR eskisi gibi.

    Yeni bir kol eklemenin en sessiz bedeli, eski yolun farkinda olmadan degismesidir.
    Bu vaka bayraksiz kosumun jetona DOKUNMADIGINI ve korumanin AYNEN tuttugunu olcer.
    """
    print("\n[40] K341 GERILEME — bayraksiz kosum jetona DOKUNMAZ")
    metin = kutu_uret_jetonlu(30, {29: BEKLEYEN_SATIR})
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=300, koru=3)
    kutu_s = oku(a.kutu)
    iddia("40a rc=0", rc == 0, cikti[-600:])
    iddia("40b BEKLEYEN jeton BIREBIR duruyor (cevrim CALISMADI)",
          BEKLEYEN_SATIR in kutu_s and ISLENMIS_SATIR not in kutu_s)
    iddia("40c KORUMALI_BEKLEYEN=1 (koruma AYNEN tutuyor)",
          "KORUMALI_BEKLEYEN=1 " in cikti, cikti[-900:])
    iddia("40d CEVRIM=0 kip=KAPALI basildi (0 ile n AYNI SATIRDAN okunur)",
          "CEVRIM=0 kip=KAPALI" in cikti, cikti[-900:])
    iddia("40e cevrim iddiasi HIC basilmadi (kol calismadi)",
          "cevrim_dogrulama=" not in cikti, cikti[-900:])


# ============ K359 — ROL OLCUTU + UCUNCU KAPANIS KOLU (1 Eyl 2026) ==============
# 🔴 OLCULEN IKI VAKA (canli kutu, 1 Eyl, 302 satir / 28 blok — mimar blok blok saydi):
#   A) blok 15 (satir 110) bir KAPANIS blogudur; basligi meshguliyet olcumunu
#      ANLATIRKEN `"MaCiT-* başlıyorum" notu yok` cumlesini tasir. ALT-DIZGE olcutu o
#      ALINTIYI marker sandi -> KAPANISIN KENDISI "acik cip" sayildi ve kutuda
#      SONSUZA KADAR kilitlendi (kapanis blogu asla rotasyona giremez).
#   B) MaCiT cron'u kapanisini `✅ … `ad` **KAPANDI (delta=0, gate-only)**` diye yazar
#      — sayili, GERCEK bir kapanis; ama ne `SAYILI KAPANIS` basligi ne kapanis JETONU
#      var. Arac gormedi -> o adin DOKUZ blogu kilitli kaldi (satir 46/49/80/83/113/
#      116/130/133/135; kapanislari satir 49/83/110).
# 🔴 FIKSTUR yalnizca BASLIK SEKLINI tasir; gercek blok govdeleri KOPYALANMAZ ve
# gercek cip adlari kullanilmaz (MimarM/MimarN/MimarQ/MimarR/MimarS uydurmadir).
K359_TAVAN = 55

# --- (A) ROL EKSENI: ayni cumle, TEK fark tirnak ---------------------------------
_ALINTI_ONEK = ("## 2026-08-31 — 🔍 MimarB teftis turu — mukerrer oturum YOK "
                "(kutuda son 2 saatte ")
_ALINTI_SONEK = " notu yok)."
K359_BASLIK_ALINTILI = _ALINTI_ONEK + '"MimarQ-* başlıyorum"' + _ALINTI_SONEK
K359_BASLIK_CIPLAK = _ALINTI_ONEK + "MimarQ-* başlıyorum" + _ALINTI_SONEK
K359_BASLIK_KALIN_ALINTILI = (_ALINTI_ONEK + '"MimarQ-* **BAŞLIYORUM**"'
                              + _ALINTI_SONEK)

# --- (B) UCUNCU KAPANIS KOLU + DORT NEGATIF FIKSTUR ------------------------------
K359_POZ_AD = "MimarM-Cron-31Agu"      # `✅` + `KAPANDI` + AD -> kapanis, veto KALKAR
K359_NEG1_AD = "MimarN-Cron-31Agu"     # `✅` YOK -> CIPLAK `KAPANDI` kapanis DEGIL
K359_NEG3_AD = "MimarS-Acik-30Agu"     # gercek acik cip -> HALA kilitler
K359_NEG4_AD = "MimarR-Tirnak-30Agu"   # `KAPANDI` TIRNAK ICINDE -> kapanis DEGIL

K359_POZ_KAPANIS = ("## 2026-08-31 — ✅ MimarM 5. cron `%s` **KAPANDI (delta=0, "
                    "gate-only) — yapisal kilit ayni.**" % K359_POZ_AD)
K359_NEG1_KAPANIS = ("## 2026-08-31 — 🔒 MimarN 4. cron `%s` **KAPANDI (delta=0, "
                     "gate-only) — yapisal kilit ayni.**" % K359_NEG1_AD)
K359_NEG2_ADSIZ = "## 2026-08-31 — ✅ BaBa teftis turu — 3 KAPANDI · 1 YENI"
K359_NEG4_BASLIK = ('## 2026-08-30 — ✅ MimarR (`%s`) **BAŞLIYORUM** — ust blokta '
                    '"KAPANDI" yaziyor ama bu is SURUYOR.' % K359_NEG4_AD)
K359_NEG3_BASLIK = ("## 2026-08-30 — 🚧 MimarS (`%s`) **BAŞLIYORUM** — kapanisi HIC "
                    "yazilmadi." % K359_NEG3_AD)
K359_POZ_ACIK = ("## 2026-08-30 — 🚧 MimarM 5. cron (`%s`) **BAŞLIYORUM: yapisal "
                 "kilit ayni.**" % K359_POZ_AD)
K359_NEG1_ACIK = ("## 2026-08-30 — 🚧 MimarN 4. cron (`%s`) **BAŞLIYORUM: yapisal "
                  "kilit ayni.**" % K359_NEG1_AD)


def kutu_uret_k359_rol(baslik):
    """3 koru dolgusu + 2 eski dolgu + EN DIPTE `baslik` blogu. Tek degisken BASLIK."""
    parcalar = [FM]
    n = 0
    while n < 3:
        parcalar.append(cip_blogu(n, "## 2026-08-31 — MimarA → MimarB: koru dolgusu %d"
                                  % n) + "---\n\n")
        n += 1
    j = 0
    while j < 2:
        parcalar.append(blok(300 + j) + "---\n\n")
        j += 1
    parcalar.append(cip_blogu(9, baslik) + "---\n\n")
    return "".join(parcalar)


def kutu_uret_k359_kapanis():
    """UCUNCU KAPANIS KOLUNUN fikstru: 1 pozitif + 4 negatif sekil, YENI -> ESKI."""
    basliklar = [
        "## 2026-08-31 — MimarA → MimarB: koru dolgusu 0",
        "## 2026-08-31 — MimarA → MimarB: koru dolgusu 1",
        "## 2026-08-31 — MimarA → MimarB: koru dolgusu 2",
        K359_POZ_KAPANIS,
        K359_NEG1_KAPANIS,
        K359_NEG2_ADSIZ,
        K359_NEG4_BASLIK,
        K359_NEG3_BASLIK,
        K359_POZ_ACIK,
        K359_NEG1_ACIK,
    ]
    parcalar = [FM]
    i = 0
    while i < len(basliklar):
        parcalar.append(cip_blogu(i, basliklar[i]) + "---\n\n")
        i += 1
    j = 0
    while j < 2:
        parcalar.append(blok(400 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def _arac_modulu(arac):
    """Test edilen aracin KENDI fonksiyonlarini yukler (mutant yolu da gecerlidir).

    🔴 TAKLIT DEGIL, ISKELE DEGIL: modul TEST EDILEN DOSYADAN yuklenir, yani mutant
    uygulandiginda bu eksen de mutanti GORUR. Neden gerekli: uc-sartin "CIP ADI"
    bacagi UCTAN UCA GORUNMEZDIR — adi CIKARILAMAYAN bir kapanis hicbir cipi serbest
    birakamaz, yani `--kuru` ciktisi o bacak dusse de AYNI kalir. O bacak ancak aracin
    kendi fonksiyonu cagrilarak olculebilir ([[kabul-fiksturu-yasagi-kutsar]] tuzagina
    dusmemek icin bacak SUSTURULMADI, OLCULEBILIR YERE tasindi).
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("arac_altinda_test", arac)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def v41_rol_olcutu_alinti(arac, kok):
    """[41] 🔴 K359 KUSUR A — TIRNAK ICINDEKI jeton MARKER DEGILDIR (uclu fikstur).

    (A) alintili baslik  -> marker DEGIL, blok rotasyona ACIK
    (B) MINIMAL CIFT: ayni cumleden IKI tirnak silinir -> marker, blok KILITLER
    (C) alinti icinde bile KALIN SARMAL -> marker (guclu rol; daraltma gercek acik
        cipleri SERBEST BIRAKMAZ — K329'un nobetcisi yasiyor)
    """
    print("\n[41] K359 ROL OLCUTU — tirnak icindeki `başlıyorum` marker DEGIL")
    alintili = kutu_uret_k359_rol(K359_BASLIK_ALINTILI)
    ciplak = kutu_uret_k359_rol(K359_BASLIK_CIPLAK)
    kalin = kutu_uret_k359_rol(K359_BASLIK_KALIN_ALINTILI)
    iddia("41a MINIMAL CIFT: (A) ve (B) yalniz IKI tirnak karakteri kadar farkli",
          alintili.replace('"', "") == ciplak,
          "fiksturler tirnak disinda da ayrisiyor")
    iddia("41b (A) fikstur tavani GERCEKTEN asiyor",
          len(alintili.splitlines()) > K359_TAVAN,
          "satir=%d" % len(alintili.splitlines()))

    os.makedirs(os.path.join(kok, "a"), exist_ok=True)
    a = Alan(os.path.join(kok, "a"), alintili, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K359_TAVAN, koru=3)
    iddia("41c (A) rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-900:]))
    iddia("41d (A) 🔴 ACIK_BASLIYORUM=0 — ALINTI marker SAYILMADI",
          "ACIK_BASLIYORUM=0 " in cikti, cikti[-1200:])
    iddia("41e (A) basliyorum_govde_anmasi=0 (alinti GOVDE ANMASINA da dusmedi)",
          "basliyorum_govde_anmasi=0 " in cikti, cikti[-1200:])
    iddia("41f (A) 🔴 blok GERCEKTEN tasindi (kilit ACILDI)",
          K359_BASLIK_ALINTILI in oku(a.arsiv),
          "blok hala kutuda -> alinti kilitlemeye devam ediyor")
    iddia("41g (A) blok kutudan CIKTI", K359_BASLIK_ALINTILI not in oku(a.kutu))

    os.makedirs(os.path.join(kok, "b"), exist_ok=True)
    b = Alan(os.path.join(kok, "b"), ciplak, "## eski arsiv blogu\n\ngovde\n")
    rc2, cikti2 = kos(arac, b.kutu, b.arsiv, b.kilit, tavan=K359_TAVAN, koru=3)
    iddia("41h (B) rc=0", rc2 == 0, cikti2[-900:])
    iddia("41i (B) 🔴 ACIK_BASLIYORUM=1 — TIRNAKSIZ jeton HALA marker (gevsetme YOK)",
          "ACIK_BASLIYORUM=1 " in cikti2, cikti2[-1200:])
    iddia("41j (B) blok KUTUDA kaldi (gercek acik blok HALA kilitler)",
          K359_BASLIK_CIPLAK in oku(b.kutu), "acik blok arsive kacti")
    iddia("41k (B) blok ARSIVE SIZMADI", K359_BASLIK_CIPLAK not in oku(b.arsiv))

    os.makedirs(os.path.join(kok, "c"), exist_ok=True)
    c = Alan(os.path.join(kok, "c"), kalin, "## eski arsiv blogu\n\ngovde\n")
    rc3, cikti3 = kos(arac, c.kutu, c.arsiv, c.kilit, tavan=K359_TAVAN, koru=3)
    iddia("41l (C) rc=0", rc3 == 0, cikti3[-900:])
    iddia("41m (C) 🔴 ACIK_BASLIYORUM=1 — KALIN SARMAL rolu tirnak IPTAL EDEMEZ",
          "ACIK_BASLIYORUM=1 " in cikti3, cikti3[-1200:])
    iddia("41n (C) blok KUTUDA kaldi", K359_BASLIK_KALIN_ALINTILI in oku(c.kutu))


def v42_ucuncu_kapanis_kolu(arac, kok):
    """[42] 🔴 K359 KUSUR B — `✅`+`KAPANDI`+AD kapanistir; UC SARTIN UCU DE SART.

    DORT NEGATIF FIKSTUR (isin emniyet cekirdegi — K329'u OLDURMEMEK icin):
      N1 ciplak `KAPANDI`, `✅` YOK          -> kapanis DEGIL (o cip HALA kilitli)
      N2 `✅`+`KAPANDI` ama CIP ADI YOK      -> kapanis DEGIL (birim ekseni)
      N3 gercek acik blok, kapanisi YOK      -> HALA kilitler
      N4 `KAPANDI` TIRNAK ICINDE             -> kapanis DEGIL (o cip HALA kilitli)
    """
    print("\n[42] K359 UCUNCU KAPANIS KOLU — uc sart BIRDEN (4 negatif fikstur)")
    metin = kutu_uret_k359_kapanis()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("42a fikstur tavani GERCEKTEN asiyor", len(metin.splitlines()) > K359_TAVAN,
          "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K359_TAVAN, koru=3)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    iddia("42b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-900:]))

    # POZITIF: MaCiT bicimindeki kapanis TANINDI -> o cipin BASLIYORUM'u SERBEST
    adlar = satir_al(cikti, "ACIK_BASLIYORUM_ADLARI=")
    iddia("42c 🔴 POZITIF: `%s` ACIK AD LISTESINDEN CIKTI" % K359_POZ_AD,
          K359_POZ_AD not in adlar, adlar)
    iddia("42d 🔴 POZITIF: kapanan cipin BASLIYORUM blogu ARSIVE gitti",
          K359_POZ_ACIK in arsiv_s, "blok hala kutuda -> kapanis TANINMADI")
    iddia("42e kapanmis_basliyorum=1 ADIYLA basildi (serbest birakilan SAYILDI)",
          "kapanmis_basliyorum=1 " in cikti, cikti[-1200:])

    # N1 — CIPLAK `KAPANDI` (✅ YOK) kapanis SAYILMAZ
    iddia("42f 🔴 N1: `✅` YOK -> ciplak `KAPANDI` kapanis SAYILMADI, `%s` ACIK kaldi"
          % K359_NEG1_AD, K359_NEG1_AD in adlar, adlar)
    iddia("42g 🔴 N1: o cipin BASLIYORUM blogu KUTUDA kaldi",
          K359_NEG1_ACIK in kutu_s and K359_NEG1_ACIK not in arsiv_s,
          "ciplak KAPANDI blogu serbest birakti -> K329 nobetcisi OLDU")
    # N3 — gercek acik blok HALA kilitler
    iddia("42h 🔴 N3: kapanisi HIC olmayan `%s` ACIK kaldi" % K359_NEG3_AD,
          K359_NEG3_AD in adlar, adlar)
    iddia("42i 🔴 N3: blok KUTUDA kaldi, arsive SIZMADI",
          K359_NEG3_BASLIK in kutu_s and K359_NEG3_BASLIK not in arsiv_s)
    # N4 — TIRNAK ICINDEKI `KAPANDI` kapanis SAYILMAZ
    iddia("42j 🔴 N4: tirnak icindeki `KAPANDI` kapanis SAYILMADI, `%s` ACIK kaldi"
          % K359_NEG4_AD, K359_NEG4_AD in adlar, adlar)
    iddia("42k 🔴 N4: blok KUTUDA kaldi, arsive SIZMADI",
          K359_NEG4_BASLIK in kutu_s and K359_NEG4_BASLIK not in arsiv_s)
    iddia("42l ACIK_BASLIYORUM=3 (N1+N3+N4; POZITIF serbest birakildi)",
          "ACIK_BASLIYORUM=3 " in cikti, cikti[-1400:])
    iddia("42m lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-900:])

    # 🔴 BIRIM EKSENI — aracin KENDI fonksiyonu (bkz. `_arac_modulu` gerekcesi).
    try:
        mod = _arac_modulu(arac)
        olcut = mod.kapanis_baslik_ucbirlik
    except Exception as exc:                                  # noqa: BLE001
        iddia("42n BIRIM: arac modulu yuklendi", False, "%r" % (exc,))
        return
    iddia("42n BIRIM: POZITIF baslik (✅+KAPANDI+AD) kapanis SAYILDI",
          olcut(K359_POZ_KAPANIS) is True, K359_POZ_KAPANIS)
    iddia("42o 🔴 BIRIM N1: `✅` YOK -> kapanis DEGIL",
          olcut(K359_NEG1_KAPANIS) is False, K359_NEG1_KAPANIS)
    iddia("42p 🔴 BIRIM N2: CIP ADI YOK -> kapanis DEGIL (uctan uca GORUNMEZ eksen)",
          olcut(K359_NEG2_ADSIZ) is False, K359_NEG2_ADSIZ)
    iddia("42q 🔴 BIRIM N4: `KAPANDI` TIRNAK ICINDE -> kapanis DEGIL",
          olcut(K359_NEG4_BASLIK) is False, K359_NEG4_BASLIK)
    iddia("42r 🔴 BIRIM: `KAPANDI` sozu HIC yoksa -> kapanis DEGIL",
          olcut("## 2026-08-31 — ✅ MimarM `%s` **SAYILI OLCUM**" % K359_POZ_AD)
          is False)


# ================ K359-B — KAPANIS ADI (A) + CIFT BUTUNLUGU (B) (2 Eyl 2026) ======
# 🔴 OLCULEN IKI VAKA (canli kutu 2 Eyl, mimar ELIYLE gosterdi):
#   A) `KraL-UrunSilmeButonu-2Eyl` kapanisi
#      `## … — ✅ <ad> (çip: …) **SAYILI KAPANIŞ — …**` seklindeydi: BACKTICK'SIZ ad,
#      Turkce `Ş`, `KAPANDI` sozcugu YOK. Arac blogu KAPANIS SAYDI ama sahibini DAR
#      cikarimla aradi -> ad kumeye GIRMEDI -> ayni cipin `BASLIYORUM` blogu, kapanisi
#      kutuda DURURKEN "ESLESEN KAPANIS kutuda YOK" diye kilitlendi.
#   B) O acilis YERINDE ATLANIRKEN rotasyon onun USTUNDEKI bloklara devam etti ve AYNI
#      CIPIN KAPANISINI arsive tasidi (arsiv :59559) -> acilis artik HICBIR ZAMAN
#      eslesemez: kutuda KALICI OLU SLOT.
# 🔴 FIKSTUR yalnizca BASLIK/IMZA SEKLINI tasir; gercek govdeler KOPYALANMAZ, gercek
# cip adlari KULLANILMAZ (MimarT/MimarU/MimarV/MimarW/MimarY/MimarZ uydurmadir).
K359B_TAVAN = 55

# --- (A) KAPANIS ADI: 1 POZITIF SEKIL + 1 REGRESYON + 4 NEGATIF -------------------
K359B_POZ_AD = "MimarT-UrunSil-2Eyl"     # backticksiz ad + IMZA -> kapanis SAYILIR
K359B_REG_AD = "MimarU-Cron-2Eyl"        # backtick'li ad (eski yol) -> AYNEN calisir
K359B_N1_AD = "MimarN1-Imzasiz-2Eyl"     # kapanis BASKASI tarafindan IMZALI -> HAYIR
K359B_N2_AD = "MimarN2-Prozada-2Eyl"     # adi ANAN ama KAPANIS OLMAYAN blok -> HAYIR
K359B_N3_AD = "MimarN3-Govdede-2Eyl"     # ad yalniz GOVDEDE geciyor -> HAYIR
K359B_N4_AD = "MimarN4-Tirnakli-2Eyl"    # `KAPANDI` TIRNAK ICINDE -> HAYIR

# POZITIF: gercek vakanin BIREBIR SEKLI (Turkce `Ş`, `KAPANDI` sozcugu YOK, ad
# BACKTICK'SIZ) + blogun kendi IMZASI ayni ad.
K359B_POZ_KAPANIS = ("## 2026-09-02 — ✅ %s (çip: sentetik-cip-a1 · model: X) "
                     "**SAYILI KAPANIŞ — is bitti, sayilar asagida.**" % K359B_POZ_AD)
K359B_POZ_ACIK = ("## 2026-09-02 — 🚧 %s (çip: sentetik-cip-a1 · model: X) "
                  "**BAŞLIYORUM: sentetik is.**" % K359B_POZ_AD)
K359B_REG_KAPANIS = ("## 2026-09-02 — ✅ MimarU 5. cron `%s` **KAPANDI (delta=0, "
                     "gate-only) — yapisal kilit ayni.**" % K359B_REG_AD)
K359B_REG_ACIK = ("## 2026-09-02 — 🚧 MimarU 5. cron (`%s`) **BAŞLIYORUM: yapisal "
                  "kilit ayni.**" % K359B_REG_AD)
# N1 — kapanis SEKLI TAM ama blogu BASKASI imzalamis: ANMAK != SAHIPLENMEK.
K359B_N1_KAPANIS = ("## 2026-09-02 — ✅ %s **SAYILI KAPANIŞ — devralan mimar "
                    "kapatti.**" % K359B_N1_AD)
K359B_N1_ACIK = "## 2026-09-02 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K359B_N1_AD
# N2 — blogu O CIP IMZALAMIS ve adi baslikta GECIYOR ama blok KAPANIS DEGIL.
K359B_N2_RAPOR = ("## 2026-09-02 — 🔍 %s ara raporu — olcum surdu, karar YOK."
                  % K359B_N2_AD)
K359B_N2_ACIK = "## 2026-09-02 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K359B_N2_AD
# N3 — GERCEK bir kapanis ama BASKA cipin; N3'un adi yalniz GOVDEDE anilir.
K359B_N3_KAPANIS = ("## 2026-09-02 — ✅ MimarZ-Komsu-2Eyl **SAYILI KAPANIŞ — komsu "
                    "is bitti.**")
K359B_N3_ACIK = "## 2026-09-02 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K359B_N3_AD
# N4 — ad + IMZA var ama kapanis sozu TIRNAK ICINDE: blok KAPANIS DEGIL.
K359B_N4_KAPANIS = ('## 2026-09-02 — ✅ %s ara notu — ust blokta "KAPANDI" yaziyor '
                    'ama bu is SURUYOR.' % K359B_N4_AD)
K359B_N4_ACIK = "## 2026-09-02 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K359B_N4_AD


def imzali_blok(i, baslik, imza):
    """Blok govdesi + SATIR BASI imzasi (`— <imza>`) — kutu geleneginin sahiplik isareti."""
    return cip_blogu(i, baslik) + "— %s\n\n" % imza


def kutu_uret_k359b_ad():
    """(A) fiksturu: kapanislar USTTE, acilislar ALTTA (kutu gelenegi: YENI -> ESKI)."""
    parcalar = [FM]
    sira = [
        ("## 2026-09-02 — MimarA → MimarB: koru dolgusu 0", "MimarA"),
        ("## 2026-09-02 — MimarA → MimarB: koru dolgusu 1", "MimarA"),
        ("## 2026-09-02 — MimarA → MimarB: koru dolgusu 2", "MimarA"),
        (K359B_POZ_KAPANIS, K359B_POZ_AD),      # IMZA = ad -> SAHIPLENME
        (K359B_REG_KAPANIS, "MimarU"),          # backtick'li: imza gerekmez
        (K359B_N1_KAPANIS, "MimarZ-Devralan"),  # IMZA BASKASI -> kapanis SAYILMAZ
        (K359B_N2_RAPOR, K359B_N2_AD),          # KAPANIS DEGIL
        (K359B_N3_KAPANIS, "MimarZ-Komsu-2Eyl"),
        (K359B_N4_KAPANIS, K359B_N4_AD),        # TIRNAK -> kapanis DEGIL
        (K359B_POZ_ACIK, K359B_POZ_AD),
        (K359B_REG_ACIK, "MimarU"),
        (K359B_N1_ACIK, K359B_N1_AD),
        (K359B_N2_ACIK, K359B_N2_AD),
        (K359B_N3_ACIK, K359B_N3_AD),
        (K359B_N4_ACIK, K359B_N4_AD),
    ]
    i = 0
    while i < len(sira):
        baslik, imza = sira[i]
        # N3'un adi, KOMSU cipin kapanis blogunun GOVDESINDE anilir (gercek tuzak).
        kuyruk = None
        if baslik == K359B_N3_KAPANIS:
            kuyruk = "not: `%s` isi ayrica surmektedir." % K359B_N3_AD
        parcalar.append(cip_blogu(i, baslik, kuyruk) + "— %s\n\n" % imza + "---\n\n")
        i += 1
    j = 0
    while j < 2:
        parcalar.append(blok(500 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def v43_kapanis_adi_imza_onayli(arac, kok):
    """[43] 🔴 K359-B KUSUR A — BACKTICK'SIZ kapanis adi IMZA ONAYIYLA okunur.

    POZITIF (gercek vakanin sekli): `✅ <ad> … **SAYILI KAPANIŞ**`, ad BACKTICK'SIZ,
    blok O ADLA IMZALI -> kapanis SAYILIR, cipin `BASLIYORUM` blogu SERBEST KALIR.
    REGRESYON: backtick'li `✅ … `ad` … **KAPANDI**` sekli AYNEN calismaya devam eder.
    DORT NEGATIF (gevsetme SERBEST BIRAKMA yonune AKMASIN diye):
      N1 kapanis sekli TAM ama blogu BASKASI imzalamis -> kapanis DEGIL
      N2 blogu O CIP imzalamis ama blok KAPANIS DEGIL   -> kapanis DEGIL
      N3 ad yalniz KOMSU kapanisin GOVDESINDE aniliyor  -> kapanis DEGIL
      N4 kapanis sozu TIRNAK ICINDE                     -> kapanis DEGIL
    🔴 `kilitledi=0` HEDEF DEGIL: bu fiksturde 2 cip SERBEST KALIR, 4 cip KILITLI
    KALIR. Hepsi duserse kol GEVSEMISTIR — 43g o hali ADIYLA yakalar.
    """
    print("\n[43] K359-B KAPANIS ADI — backticksiz ad + IMZA ONAYI (4 negatif fikstur)")
    metin = kutu_uret_k359b_ad()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("43a fikstur tavani GERCEKTEN asiyor",
          len(metin.splitlines()) > K359B_TAVAN, "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K359B_TAVAN, koru=3)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    adlar = satir_al(cikti, "ACIK_BASLIYORUM_ADLARI=")
    iddia("43b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1200:]))

    # POZITIF — GERCEK VAKANIN SEKLI
    iddia("43c 🔴 POZITIF: backticksiz+IMZALI `SAYILI KAPANIŞ` TANINDI, `%s` ACIK "
          "AD LISTESINDEN CIKTI" % K359B_POZ_AD, K359B_POZ_AD not in adlar, adlar)
    iddia("43d 🔴 POZITIF: o cipin `BASLIYORUM` blogu GERCEKTEN arsive gitti",
          K359B_POZ_ACIK in arsiv_s and K359B_POZ_ACIK not in kutu_s,
          "blok hala kutuda -> kapanis TANINMADI")
    # REGRESYON — eski (backtick'li) yol OLMEDI
    iddia("43e REGRESYON: backtick'li `KAPANDI` sekli AYNEN calisiyor (`%s` serbest)"
          % K359B_REG_AD, K359B_REG_AD not in adlar, adlar)
    iddia("43f REGRESYON: o cipin `BASLIYORUM` blogu arsive gitti",
          K359B_REG_ACIK in arsiv_s)

    # DORT NEGATIF — hicbiri SERBEST BIRAKMAMALI
    iddia("43g 🔴 N1: kapanisi BASKASI imzalamis -> `%s` ACIK KALDI (ANMAK != "
          "SAHIPLENMEK)" % K359B_N1_AD, K359B_N1_AD in adlar, adlar)
    iddia("43h 🔴 N1: acilis blogu KUTUDA kaldi, arsive SIZMADI",
          K359B_N1_ACIK in kutu_s and K359B_N1_ACIK not in arsiv_s)
    iddia("43i 🔴 N2: KAPANIS OLMAYAN (adi ANAN + O CIP imzali) blok serbest BIRAKMADI"
          " -> `%s` ACIK KALDI" % K359B_N2_AD, K359B_N2_AD in adlar, adlar)
    iddia("43j 🔴 N2: acilis blogu KUTUDA kaldi",
          K359B_N2_ACIK in kutu_s and K359B_N2_ACIK not in arsiv_s)
    iddia("43k 🔴 N3: ad yalniz KOMSU kapanisin GOVDESINDE aniliyor -> `%s` ACIK KALDI"
          % K359B_N3_AD, K359B_N3_AD in adlar, adlar)
    iddia("43l 🔴 N3: acilis blogu KUTUDA kaldi",
          K359B_N3_ACIK in kutu_s and K359B_N3_ACIK not in arsiv_s)
    iddia("43m 🔴 N4: kapanis sozu TIRNAK ICINDE -> `%s` ACIK KALDI" % K359B_N4_AD,
          K359B_N4_AD in adlar, adlar)
    iddia("43n 🔴 N4: acilis blogu KUTUDA kaldi",
          K359B_N4_ACIK in kutu_s and K359B_N4_ACIK not in arsiv_s)
    iddia("43o 🔴 kilitledi=0 HEDEF DEGIL: TAM 4 cip ACIK kaldi (2 serbest, 4 kilitli)",
          "ACIK_BASLIYORUM=4 " in cikti, cikti[-1600:])
    iddia("43p kapanmis_basliyorum=2 ADIYLA basildi (serbest birakilan SAYILDI)",
          "kapanmis_basliyorum=2 " in cikti, cikti[-1600:])
    iddia("43q lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-900:])

    # 🔴 BIRIM EKSENI — aracin KENDI fonksiyonu (mutant yolu da gecerlidir).
    try:
        mod = _arac_modulu(arac)
        olcut = mod.kapanis_cip_adi
    except Exception as exc:                                  # noqa: BLE001
        iddia("43r BIRIM: arac modulu yuklendi", False, "%r" % (exc,))
        return

    def _ad(baslik, imza):
        s = (baslik + "\n" + (CIP_GOVDE % (0, 100)) + "— %s\n" % imza).splitlines(
            keepends=True)
        return olcut(s, 0, len(s))

    iddia("43r BIRIM POZITIF: backticksiz ad + AYNI ADLA IMZA -> ad OKUNDU",
          _ad(K359B_POZ_KAPANIS, K359B_POZ_AD) == K359B_POZ_AD,
          "%r" % (_ad(K359B_POZ_KAPANIS, K359B_POZ_AD),))
    iddia("43s 🔴 BIRIM N1: ayni baslik, IMZA BASKASI -> ad OKUNMADI (None)",
          _ad(K359B_POZ_KAPANIS, "MimarZ-Devralan") is None,
          "%r" % (_ad(K359B_POZ_KAPANIS, "MimarZ-Devralan"),))
    iddia("43t 🔴 BIRIM MINIMAL CIFT: 43r ile 43s arasindaki TEK fark IMZA satiridir",
          K359B_POZ_KAPANIS == K359B_POZ_KAPANIS)
    iddia("43u BIRIM REGRESYON: backtick'li ad IMZA ARANMADAN okunur",
          _ad(K359B_REG_KAPANIS, "MimarU") == K359B_REG_AD,
          "%r" % (_ad(K359B_REG_KAPANIS, "MimarU"),))
    govdede = (K359B_POZ_KAPANIS + "\nnot: bu is — %s tarafindan surduruluyor.\n"
               % K359B_POZ_AD).splitlines(keepends=True)
    iddia("43v 🔴 BIRIM: IMZA satir BASINDA degilse (govde icinde) ad OKUNMAZ",
          olcut(govdede, 0, len(govdede)) is None,
          "%r" % (olcut(govdede, 0, len(govdede)),))


# --- (B) CIFT BUTUNLUGU: acilisi kutuda kalan KAPANIS TASINMAZ --------------------
K359B_B1_AD = "MimarV-Cift-2Eyl"      # ACILIS_DAHA_YENI (o < c) -> kapanis PINLENIR
K359B_B2_AD = "MimarW-Koru-2Eyl"      # ACILIS_SABIT (`koru` tabaninda) -> PINLENIR
K359B_BN_AD = "MimarY-Normal-2Eyl"    # NORMAL yon (o > c) -> kapanis TASINIR

K359B_B1_ACIK = "## 2026-09-02 — 🚧 MimarV (`%s`) **BAŞLIYORUM: is.**" % K359B_B1_AD
K359B_B1_KAPANIS = ("## 2026-09-01 — ✅ MimarV (`%s`) **KAPANDI (delta=0)**"
                    % K359B_B1_AD)
K359B_B2_ACIK = "## 2026-09-02 — 🚧 MimarW (`%s`) **BAŞLIYORUM: is.**" % K359B_B2_AD
K359B_B2_KAPANIS = ("## 2026-09-01 — ✅ MimarW (`%s`) **KAPANDI (delta=0)**"
                    % K359B_B2_AD)
K359B_BN_KAPANIS = ("## 2026-09-01 — ✅ MimarY (`%s`) **KAPANDI (delta=0)**"
                    % K359B_BN_AD)
K359B_BN_ACIK = "## 2026-08-30 — 🚧 MimarY (`%s`) **BAŞLIYORUM: is.**" % K359B_BN_AD

# 🔴 (B) ICIN AYRI TAVAN — ELLE CIVILENDI, sonuca gore secilmedi: fikstur 141 satir,
# bloklar 0-7 = 11'er satir, 8-10 = 15'er satir. su_seviye = int(100*0.8) = 80; secim
# 10,9,8,7 ve (6/5 PINLI atlanip) 4'u alir, kalan 74 <= 80 oldugu icin B1 ACILISINDAN
# (blok 3) ONCE DURUR. Boylece "kapanis PINLENDI" iddiasi, acilisin da tasinmis
# olmasindan BAGIMSIZ okunur ve cift GERCEKTEN bolunmemis olur.
K359B_CIFT_TAVAN = 100


def kutu_uret_k359b_cift():
    """(B) fiksturu — blok sirasi (YENI -> ESKI, 0-tabanli):

      0  koru dolgusu
      1  B2 ACILIS  (`koru` tabaninda -> SABIT)
      2  koru dolgusu
      3  B1 ACILIS  (tasinabilir, ama KAPANISINDAN DAHA YENI konumda)
      4  BN KAPANIS (acilisi 7'de, yani o > c -> NORMAL yon, TASINMALI)
      5  B1 KAPANIS (acilisi 3'te, o < c -> PINLENMELI)
      6  B2 KAPANIS (acilisi 1'de, SABIT -> PINLENMELI)
      7  BN ACILIS  (tasinabilir)
      8+ eski dolgu
    """
    basliklar = [
        "## 2026-09-02 — MimarA → MimarB: koru dolgusu 0",
        K359B_B2_ACIK,
        "## 2026-09-02 — MimarA → MimarB: koru dolgusu 2",
        K359B_B1_ACIK,
        K359B_BN_KAPANIS,
        K359B_B1_KAPANIS,
        K359B_B2_KAPANIS,
        K359B_BN_ACIK,
    ]
    parcalar = [FM]
    i = 0
    while i < len(basliklar):
        parcalar.append(cip_blogu(i, basliklar[i]) + "---\n\n")
        i += 1
    j = 0
    while j < 3:
        parcalar.append(blok(600 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def v44_cift_butunlugu(arac, kok):
    """[44] 🔴 K359-B KUSUR B — ACILISI KUTUDA KALAN KAPANIS ARSIVE TASINMAZ.

    Olculen zarar: acilis YERINDE ATLANIRKEN rotasyon onun USTUNDEKI bloklara devam
    edip AYNI CIPIN KAPANISINI arsive tasidi -> acilis bir daha ASLA eslesemez, kutuda
    KALICI OLU SLOT. Iki POZITIF sekil (`ACILIS_SABIT` + `ACILIS_DAHA_YENI`) ve BIR
    NEGATIF (NORMAL yon: acilis kapanistan ESKI konumda -> kapanis TASINIR) ayni
    fiksturde olculur: `CIFT_KORUMASI` her kapanisi pinleyen bir kol OLMAMALI.
    """
    print("\n[44] K359-B CIFT BUTUNLUGU — acilisi kalan KAPANIS rotasyona GIRMEZ")
    metin = kutu_uret_k359b_cift()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("44a fikstur tavani GERCEKTEN asiyor",
          len(metin.splitlines()) > K359B_CIFT_TAVAN,
          "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K359B_CIFT_TAVAN, koru=3)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    iddia("44b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1400:]))
    iddia("44c 🔴 CIFT_KORUMASI=2 ADIYLA basildi (SESSIZ ATLAMA YASAK)",
          "CIFT_KORUMASI=2 " in cikti, cikti[-1800:])
    iddia("44d 🔴 sebep ACILIS_SABIT ADIYLA basildi",
          "sebep=ACILIS_SABIT" in cikti, cikti[-1800:])
    iddia("44e 🔴 sebep ACILIS_DAHA_YENI ADIYLA basildi",
          "sebep=ACILIS_DAHA_YENI" in cikti, cikti[-1800:])

    # POZITIF 1 — ACILIS_DAHA_YENI: kapanis KUTUDA kaldi, cift BOLUNMEDI
    iddia("44f 🔴 B1: kapanis KUTUDA kaldi, arsive SIZMADI",
          K359B_B1_KAPANIS in kutu_s and K359B_B1_KAPANIS not in arsiv_s,
          "kapanis arsive kacti -> acilis bir daha eslesemez (OLU SLOT)")
    iddia("44g 🔴 B1: acilis da KUTUDA -> cift BOLUNMEDI",
          K359B_B1_ACIK in kutu_s)
    # POZITIF 2 — ACILIS_SABIT (`koru` tabani)
    iddia("44h 🔴 B2: kapanis KUTUDA kaldi, arsive SIZMADI",
          K359B_B2_KAPANIS in kutu_s and K359B_B2_KAPANIS not in arsiv_s)
    iddia("44i 🔴 B2: acilis `koru` tabaninda KUTUDA", K359B_B2_ACIK in kutu_s)
    # NEGATIF — NORMAL yon: kol HER kapanisi pinlemez
    iddia("44j 🔴 NEGATIF: NORMAL yondeki (acilisi DAHA ESKI) kapanis TASINDI",
          K359B_BN_KAPANIS in arsiv_s and K359B_BN_KAPANIS not in kutu_s,
          "kol her kapanisi pinliyor -> rotasyon KILITLENIR")
    iddia("44k 🔴 NEGATIF: o ciftin acilisi da TASINDI (cift birlikte dustu)",
          K359B_BN_ACIK in arsiv_s and K359B_BN_ACIK not in kutu_s)
    # 🔴 Rotasyon GERCEKTEN is yapti: kol "her seyi pinleyip durdum" ile "cifti
    # koruyup geri kalani tasidim"i AYIRT EDILEBILIR kilmali. Sayi ONCEDEN civilendi
    # (bkz. K359B_CIFT_TAVAN gerekcesi): tasinan kume {10,9,8,7,4} = 5 blok.
    iddia("44l rotasyon GERCEKTEN is yapti — tasinacak_blok=5 (onceden civili)",
          "tasinacak_blok=5 " in cikti, satir_al(cikti, "tasinacak_blok="))
    iddia("44n kutu tavanin ALTINA indi (cift korumasi rotasyonu KILITLEMEDI)",
          "HUKUM=TAMAM" in cikti or "sonra_satir=74" in cikti, cikti[-900:])
    iddia("44m lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-900:])


def v45_d18_denetimi(arac, kok):
    """[45] 🔴 K359-B DENETIM — `cift-bolunmesi-sizdir` arizasi D18'de yakalanmali.

    ICRA kolu (planla) dogru calissa bile, tasinan metne ACILISI KUTUDA KALAN bir
    KAPANIS blogu SIZARSA denetim KIRMIZI YAKMALI ve HICBIR SEY yazilmamali.
    """
    print("\n[45] K359-B DENETIM — `cift-bolunmesi-sizdir` arizasi D18'de yakalanmali")
    metin = kutu_uret_k359b_cift()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    h1, h2 = sha(a.kutu), sha(a.arsiv)
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K359B_CIFT_TAVAN, koru=3,
                    ortam={"PRUVO_KUTU_ARSIVLE_ARIZA": "cift-bolunmesi-sizdir"})
    iddia("45a rc SIFIR-DISI", rc != 0, "rc=%d\n%s" % (rc, cikti[-1200:]))
    iddia("45b kutu DEGISMEDI", sha(a.kutu) == h1)
    iddia("45c arsiv DEGISMEDI", sha(a.arsiv) == h2)
    iddia("45d 'HICBIR SEY YAZILMADI' beyani", "HICBIR SEY YAZILMADI" in cikti,
          cikti[-700:])
    # 🔴 HEDEF-KOL ATFI: kirmizinin SEBEBI D18 olmali — "kirmizi geldi" YETMEZ.
    iddia("45e kirmizinin SEBEBI D18 CIFT BOLUNMESI kolu (hedef-kol atfi)",
          "D18 CIFT BOLUNMESI" in cikti, cikti[-1600:])
    iddia("45f sizan ciftin CIP ADI kirmizida geciyor",
          (K359B_B2_AD in cikti or K359B_B1_AD in cikti), cikti[-1600:])


# ============================================================ K360 (4 Eyl 2026)
# 🔴 SINIF: bir cipin "KAPANDI mi" sorusu AD BIREBIR ESITLIGIYLE cevaplaniyordu.
# Ayni cip acilis ve kapanis basliklarinda IKI FARKLI ANAHTAR uretince eslesme HIC
# kurulmuyor ve `BASLIYORUM` blogu sonsuza dek "acik" gorunuyordu. UC AYRI KOL, UC
# AYRI FIKSTUR (tek fikstur uc kolu birden KUTSAYAMAZ):
#   46 = K360-A AD EKSENI   (dar/backtickli ad  <-> gevsek ad ayrismasi)
#   47 = K360-B DUZLEM      (kapanis ARSIVDE, acilis kutuda)  + ZAMAN + TUKETIM
#   48 = K360-C KONUM       (dev baslikta PROZA `BASLIYORUM` marker sanildi)
# 🔴 FIKSTURLER yalnizca gercek vakalarin SEKLINI tasir; gercek cip adlari ve gercek
# govdeler KULLANILMAZ (MimarP1/MimarP2/MimarN5.. uydurmadir), kisisel veri GECMEZ.
K360_TAVAN = 55

# --- (A) AD EKSENI: 2 POZITIF (IKI TERS YON) + 3 NEGATIF -------------------------
# Gercek vaka 1: acilis GEVSEK adli, kapanis BACKTICK'li oturum kimlikli.
K360A_P1_AD = "MimarP1-Tamirci-4Eyl"
K360A_P1_OTURUM = "sentetik-oturum-p1a1"      # gevsek suzgecten GECMEZ (buyuk harf yok)
# Gercek vaka 2: TERS YON — acilis BACKTICK'li, kapanis GEVSEK adli.
K360A_P2_AD = "MimarP2-Merge-4Eyl"
K360A_P2_OTURUM = "sentetik-oturum-p2b2"
K360A_N5_AD = "MimarN5-Anilan-4Eyl"           # adi BASKA cipin GOVDESINDE aniliyor
K360A_N6_AD = "MimarN6-Citli-4Eyl"            # kapanisi KOD CITI icinde
K360A_N7_AD = "MimarN7-Baskasi-4Eyl"          # kapanisini BASKASI imzalamis

K360A_P1_ACIK = ("## 2026-09-03 — 🚧 %s (çip: %s) **BAŞLIYORUM: sentetik is.**"
                 % (K360A_P1_AD, K360A_P1_OTURUM))
K360A_P1_KAPANIS = ("## 2026-09-03 — ✅ %s (çip `%s`) **SAYILI KAPANIŞ — bitti.**"
                    % (K360A_P1_AD, K360A_P1_OTURUM))
K360A_P2_ACIK = ("## 2026-09-03 — 🚧 %s (çip `%s`) **BAŞLIYORUM: sentetik is.**"
                 % (K360A_P2_AD, K360A_P2_OTURUM))
K360A_P2_KAPANIS = ("## 2026-09-03 — ✅ %s **SAYILI KAPANIŞ — bitti.**" % K360A_P2_AD)
K360A_N5_ACIK = "## 2026-09-03 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K360A_N5_AD
K360A_N6_ACIK = "## 2026-09-03 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K360A_N6_AD
K360A_N7_ACIK = "## 2026-09-03 — 🚧 %s **BAŞLIYORUM: sentetik is.**" % K360A_N7_AD
# N5 — GERCEK bir kapanis ama BASKA cipin; N5'in adi yalniz GOVDEDE anilir.
K360A_KOMSU_KAPANIS = ("## 2026-09-03 — ✅ MimarZ-Komsu-4Eyl **SAYILI KAPANIŞ — komsu "
                       "is bitti.**")
# N6 — kapanis SEKLI TAM ama KOD CITI icinde: blok basi DEGILDIR, kapanis DEGILDIR.
K360A_CIT_RAPOR = "## 2026-09-03 — 🔍 MimarZ-Ornek-4Eyl ara raporu — ornek cikti asagida."
K360A_CIT_KUYRUK = (
    "```markdown\n"
    "## 2026-09-03 — ✅ %s (çip `sentetik-oturum-n6c3`) **SAYILI KAPANIŞ — ornek.**\n"
    "— %s\n"
    "```" % (K360A_N6_AD, K360A_N6_AD))
# N7 — kapanis SEKLI TAM, ad GEVSEK, ama blogu BASKASI imzalamis -> SAHIPLENME YOK.
K360A_N7_KAPANIS = ("## 2026-09-03 — ✅ %s **SAYILI KAPANIŞ — devralan mimar kapatti.**"
                    % K360A_N7_AD)


def kutu_uret_k360a():
    """(A) fiksturu: kapanislar USTTE, acilislar ALTTA (kutu gelenegi: YENI -> ESKI)."""
    sira = [
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 0", "MimarA", None),
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 1", "MimarA", None),
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 2", "MimarA", None),
        (K360A_P1_KAPANIS, K360A_P1_AD, None),          # IMZA = ad -> GEVSEK ONAYLANIR
        (K360A_P2_KAPANIS, K360A_P2_AD, None),          # IMZA = ad -> GEVSEK ONAYLANIR
        (K360A_N7_KAPANIS, "MimarZ-Devralan", None),    # IMZA BASKASI -> kapanis DEGIL
        (K360A_KOMSU_KAPANIS, "MimarZ-Komsu-4Eyl",
         "not: `%s` isi ayrica surmektedir." % K360A_N5_AD),
        (K360A_CIT_RAPOR, "MimarZ-Ornek-4Eyl", K360A_CIT_KUYRUK),
        (K360A_P1_ACIK, K360A_P1_AD, None),
        (K360A_P2_ACIK, K360A_P2_AD, None),
        (K360A_N5_ACIK, K360A_N5_AD, None),
        (K360A_N6_ACIK, K360A_N6_AD, None),
        (K360A_N7_ACIK, K360A_N7_AD, None),
    ]
    parcalar = [FM]
    i = 0
    while i < len(sira):
        baslik, imza, kuyruk = sira[i]
        parcalar.append(cip_blogu(i, baslik, kuyruk) + "— %s\n\n" % imza + "---\n\n")
        i += 1
    j = 0
    while j < 2:
        parcalar.append(blok(700 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def v46_ad_ekseni_ayrismasi(arac, kok):
    """[46] 🔴 K360-A — ACILIS ile KAPANIS AYNI KIMLIK KUMESINDEN okunur.

    IKI POZITIF, IKI TERS YONDE (gercek vakalarin sekli):
      P1 acilis GEVSEK adli / kapanis BACKTICK'li oturum kimlikli
      P2 acilis BACKTICK'li oturum kimlikli / kapanis GEVSEK adli
    Eski kod her yanda TEK ad secip durdugu icin IKISI DE eslesmiyordu.
    UC NEGATIF (gevsetme SERBEST BIRAKMA yonune AKMASIN diye):
      N5 ad yalniz BASKA cipin kapanis GOVDESINDE aniliyor -> kapanis DEGIL
      N6 kapanis SEKLI TAM ama KOD CITI icinde                -> kapanis DEGIL
      N7 kapanis SEKLI TAM ama blogu BASKASI imzalamis        -> kapanis DEGIL
    🔴 `kilitledi=0` HEDEF DEGIL: 2 cip SERBEST, 3 cip KILITLI kalir.
    """
    print("\n[46] K360-A AD EKSENI — iki ters yonde eslesme + 3 negatif fikstur")
    metin = kutu_uret_k360a()
    a = Alan(kok, metin, "## eski arsiv blogu\n\ngovde\n")
    iddia("46a fikstur tavani GERCEKTEN asiyor",
          len(metin.splitlines()) > K360_TAVAN, "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K360_TAVAN, koru=3)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    adlar = satir_al(cikti, "ACIK_BASLIYORUM_ADLARI=")
    iddia("46b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1200:]))

    iddia("46c 🔴 P1: acilis GEVSEK / kapanis BACKTICK'li -> `%s` ACIK LISTESINDEN CIKTI"
          % K360A_P1_AD, K360A_P1_AD not in adlar, adlar)
    iddia("46d 🔴 P1: o cipin `BASLIYORUM` blogu GERCEKTEN arsive gitti",
          K360A_P1_ACIK in arsiv_s and K360A_P1_ACIK not in kutu_s,
          "blok hala kutuda -> eslesme kurulmadi")
    iddia("46e 🔴 P2 (TERS YON): acilis BACKTICK'li / kapanis GEVSEK -> `%s` CIKTI"
          % K360A_P2_AD, K360A_P2_AD not in adlar, adlar)
    iddia("46f 🔴 P2: o cipin `BASLIYORUM` blogu GERCEKTEN arsive gitti",
          K360A_P2_ACIK in arsiv_s and K360A_P2_ACIK not in kutu_s,
          "blok hala kutuda -> ters yon eslesmedi")

    iddia("46g 🔴 N5: ad yalniz KOMSU kapanisin GOVDESINDE -> `%s` ACIK KALDI"
          % K360A_N5_AD, K360A_N5_AD in adlar, adlar)
    iddia("46h 🔴 N5: acilis blogu KUTUDA kaldi, arsive SIZMADI",
          K360A_N5_ACIK in kutu_s and K360A_N5_ACIK not in arsiv_s)
    iddia("46i 🔴 N6: kapanis KOD CITI icinde -> `%s` ACIK KALDI" % K360A_N6_AD,
          K360A_N6_AD in adlar, adlar)
    iddia("46j 🔴 N6: acilis blogu KUTUDA kaldi",
          K360A_N6_ACIK in kutu_s and K360A_N6_ACIK not in arsiv_s)
    iddia("46k 🔴 N7: kapanisi BASKASI imzalamis -> `%s` ACIK KALDI (ANMAK != "
          "SAHIPLENMEK)" % K360A_N7_AD, K360A_N7_AD in adlar, adlar)
    iddia("46l 🔴 N7: acilis blogu KUTUDA kaldi",
          K360A_N7_ACIK in kutu_s and K360A_N7_ACIK not in arsiv_s)
    iddia("46m 🔴 kilitledi=0 HEDEF DEGIL: TAM 3 cip ACIK kaldi (2 serbest, 3 kilitli)",
          "ACIK_BASLIYORUM=3 " in cikti, cikti[-1800:])
    iddia("46n kapanmis_basliyorum=2 ADIYLA basildi", "kapanmis_basliyorum=2 " in cikti,
          cikti[-1800:])
    iddia("46o lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-900:])

    # 🔴 BIRIM EKSENI — aracin KENDI fonksiyonlari (mutant yolu da gecerlidir).
    try:
        mod = _arac_modulu(arac)
    except Exception as exc:                                  # noqa: BLE001
        iddia("46p BIRIM: arac modulu yuklendi", False, "%r" % (exc,))
        return
    iddia("46p 🔴 BIRIM: GEVSEK acilis basligi IKI kimlik degil BIR uretir",
          mod.cip_kimlikleri(K360A_P1_ACIK) == (K360A_P1_AD,),
          "%r" % (mod.cip_kimlikleri(K360A_P1_ACIK),))
    iddia("46q 🔴 BIRIM: BACKTICK'li acilis basligi IKI kimlik URETIR (dar ONCE)",
          mod.cip_kimlikleri(K360A_P2_ACIK) == (K360A_P2_OTURUM, K360A_P2_AD),
          "%r" % (mod.cip_kimlikleri(K360A_P2_ACIK),))

    def _kap(baslik, imza):
        s = (baslik + "\n" + (CIP_GOVDE % (0, 100)) + "— %s\n" % imza).splitlines(
            keepends=True)
        return mod.kapanis_kimlikleri(s, 0, len(s))

    iddia("46r 🔴 BIRIM: BACKTICK'li kapanis + AYNI ADLA IMZA -> IKI kimlik",
          _kap(K360A_P1_KAPANIS, K360A_P1_AD) == (K360A_P1_OTURUM, K360A_P1_AD),
          "%r" % (_kap(K360A_P1_KAPANIS, K360A_P1_AD),))
    iddia("46s 🔴 BIRIM MINIMAL CIFT: ayni baslik, IMZA BASKASI -> GEVSEK kimlik DUSER",
          _kap(K360A_P1_KAPANIS, "MimarZ-Devralan") == (K360A_P1_OTURUM,),
          "%r" % (_kap(K360A_P1_KAPANIS, "MimarZ-Devralan"),))
    iddia("46t 🔴 BIRIM: 46r ile 46s arasindaki TEK fark IMZA satiridir "
          "(gevsetme serbest birakma yonune AKMIYOR)", True)


# --- (B) DUZLEM: kapanis ARSIVDE + ZAMAN SIRASI + TUKETIM ------------------------
K360B_POZ_AD = "MimarQ-Arsivde-4Eyl"      # kapanisi ARSIVDE -> SERBEST KALMALI
K360B_REP_AD = "MimarR-Cron-4Eyl"         # TEKRAR EDEN AD (cron) — iki acilis, BIR kapanis

K360B_POZ_ACIK = ("## 2026-09-03 — 🚧 MimarQ (`%s`) **BAŞLIYORUM: sentetik is.**"
                  % K360B_POZ_AD)
K360B_POZ_KAPANIS = ("## 2026-09-03 — ✅ MimarQ (`%s`) **SAYILI KAPANIŞ — bitti.**"
                     % K360B_POZ_AD)
# TEKRAR EDEN AD — acilislar AYNI ADLA, FARKLI GUNDE. Arsivde YALNIZ ESKI kapanis var.
K360B_REP_YENI = ("## 2026-09-03 — 🚧 MimarR 2. cron (`%s`) **BAŞLIYORUM: yapisal "
                  "kilit ayni.**" % K360B_REP_AD)
K360B_REP_ESKI = ("## 2026-09-01 — 🚧 MimarR 1a. cron (`%s`) **BAŞLIYORUM: yapisal "
                  "kilit ayni.**" % K360B_REP_AD)
# 🔴 TUKETIM KOLUNUN OLCU ALETI: AYNI GUNDE ikinci bir acilis. ZAMAN olcutu bunu
# da GECIRIR (ayni gun, belirsiz saat); onu kilitli tutan TEK sey, kapanis
# kaydinin ONCEKI acilis tarafindan TUKETILMIS olmasidir. Bu bacak olmadan
# `ad)` mutanti (TUKETIM kaldirildi) YESIL kaliyordu — olculdu, sonra eklendi.
K360B_REP_ESKI2 = ("## 2026-09-01 — 🚧 MimarR 1b. cron (`%s`) **BAŞLIYORUM: yapisal "
                   "kilit ayni.**" % K360B_REP_AD)
K360B_REP_KAPANIS = ("## 2026-09-01 — ✅ MimarR 1. cron (`%s`) **KAPANDI (delta=0).**"
                     % K360B_REP_AD)


def arsiv_uret_k360b(bozuk=False):
    """ARSIV fiksturu: POZ kapanisi + REP'in YALNIZ ESKI kapanisi.

    bozuk=True -> frontmatter ACILIR ama KAPANMAZ (yarim/bozuk arsiv): fail-closed
    kolunun olcu aletidir.
    """
    # 🔴 BOZUK bacakta AYRAC (`---`) KULLANILMAZ: bir ayrac frontmatter'i KAZARA
    # KAPATIR ve fikstur "bozuk" olmaktan cikar (ilk yazimda tam bu oldu, olculdu).
    if bozuk:
        onek = "---\nname: sentetik-arsiv\n"        # KAPANIS `---` YOK -> YARIM
        ayrac = ""
    else:
        onek = "---\nname: sentetik-arsiv\n---\n\n"
        ayrac = "---\n\n"
    parcalar = [onek]
    parcalar.append(cip_blogu(900, K360B_POZ_KAPANIS) + "— %s\n\n" % K360B_POZ_AD
                    + ayrac)
    parcalar.append(cip_blogu(901, K360B_REP_KAPANIS) + "— MimarR\n\n" + ayrac)
    return "".join(parcalar)


def kutu_uret_k360b():
    """(B) fiksturu — acilislar kutuda, kapanislarin HICBIRI kutuda DEGIL."""
    sira = [
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 0", "MimarA"),
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 1", "MimarA"),
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 2", "MimarA"),
        (K360B_POZ_ACIK, K360B_POZ_AD),
        (K360B_REP_YENI, "MimarR"),
        (K360B_REP_ESKI, "MimarR"),
        (K360B_REP_ESKI2, "MimarR"),
    ]
    parcalar = [FM]
    i = 0
    while i < len(sira):
        baslik, imza = sira[i]
        parcalar.append(cip_blogu(i, baslik) + "— %s\n\n" % imza + "---\n\n")
        i += 1
    j = 0
    while j < 3:
        parcalar.append(blok(800 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def v47_arsiv_duzlemi(arac, kok):
    """[47] 🔴 K360-B — "bu cip kapandi mi" sorusu ARSIVE DE SORULUR.

    POZITIF: kapanis ARSIVDE -> acilis SERBEST kalir (kutu 250 satirlik bir
    PENCEREdir; kapanislar dogal olarak ondan once arsive akar).
    NEGATIF-1 (TEKRAR EDEN AD): `MimarR-Cron-4Eyl` AYNI ADLA IKI kez acilmis, arsivde
      YALNIZ ESKI kapanisi var. ESKI kapanis YENI acilisi ACAMAZ (zaman sirasi) ve
      TEK kapanis IKI acilisi ACAMAZ (tuketim). Naif "arsivde adi geciyorsa kapandi"
      kurali CANLI bir cipin acilisini rotasyona atardi — tam da kacindigimiz kayip.
    NEGATIF-2 (FAIL-CLOSED): arsiv frontmatter'i BOZUKSA hicbir kayit uretilmez,
      TUM acilislar KILITLI kalir ve sebep ADIYLA basilir. Fail-open YASAK.
    """
    print("\n[47] K360-B ARSIV DUZLEMI — zaman sirasi + tuketim + fail-closed")
    metin = kutu_uret_k360b()
    a = Alan(kok, metin, arsiv_uret_k360b())
    iddia("47a fikstur tavani GERCEKTEN asiyor",
          len(metin.splitlines()) > K360_TAVAN, "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K360_TAVAN, koru=3)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    adlar = satir_al(cikti, "ACIK_BASLIYORUM_ADLARI=")
    serbest = satir_al(cikti, "ARSIV_SERBEST_ADLARI=")
    iddia("47b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1500:]))

    iddia("47c 🔴 POZITIF: kapanisi ARSIVDE olan `%s` ACIK LISTESINDEN CIKTI"
          % K360B_POZ_AD, K360B_POZ_AD not in adlar, adlar)
    iddia("47d 🔴 POZITIF: `%s` ARSIV_SERBEST_ADLARI'nda ADIYLA basildi"
          % K360B_POZ_AD, K360B_POZ_AD in serbest, serbest)
    iddia("47e 🔴 POZITIF: o cipin `BASLIYORUM` blogu GERCEKTEN arsive gitti",
          K360B_POZ_ACIK in arsiv_s and K360B_POZ_ACIK not in kutu_s,
          "blok hala kutuda -> arsiv duzlemi okunmadi")

    iddia("47f 🔴 NEGATIF-1 (ZAMAN): ESKI kapanis YENI acilisi ACMADI — 2. cron "
          "blogu KUTUDA kaldi", K360B_REP_YENI in kutu_s and K360B_REP_YENI not in arsiv_s,
          "yeni acilis arsive kacti = CANLI CIP KAYBI")
    iddia("47g 🔴 NEGATIF-1: `%s` HALA ACIK listesinde (tekrar eden ad TUKENMEDI)"
          % K360B_REP_AD, K360B_REP_AD in adlar, adlar)
    iddia("47h 🔴 NEGATIF-1 (TUKETIM): ESKI acilis ise SERBEST kaldi — TEK kapanis "
          "TAM BIR acilis acti", K360B_REP_ESKI in arsiv_s and K360B_REP_ESKI not in kutu_s,
          "eski acilis da kilitli kaldi -> tuketim kolu hic calismadi")
    iddia("47h2 🔴 NEGATIF-1 (TUKETIM): AYNI GUNDEKI IKINCI acilis KILITLI kaldi "
          "— TEK kapanis IKI acilis ACAMAZ",
          K360B_REP_ESKI2 in kutu_s and K360B_REP_ESKI2 not in arsiv_s,
          "ikinci acilis da serbest kaldi -> bir kapanis SINIRSIZ acilis aciyor")
    iddia("47i 🔴 ARSIV_SERBEST=2 (POZ + REP-1a), UCUNCU serbest YOK",
          "ARSIV_SERBEST=2 " in cikti, cikti[-1800:])
    iddia("47j 🔴 kilitledi=0 HEDEF DEGIL: TAM 2 cip ACIK kaldi (REP-2 zaman "
          "kolundan, REP-1b tuketim kolundan)",
          "ACIK_BASLIYORUM=2 " in cikti, cikti[-1800:])
    iddia("47k lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-900:])

    # --- NEGATIF-2: ARSIV BOZUK -> FAIL-CLOSED (ayri alan, KURU kosum) -----------
    kok2 = os.path.join(kok, "bozuk")
    os.makedirs(kok2, exist_ok=True)
    b = Alan(kok2, metin, arsiv_uret_k360b(bozuk=True))
    h1, h2 = sha(b.kutu), sha(b.arsiv)
    rc2, cikti2 = kos(arac, b.kutu, b.arsiv, b.kilit, tavan=K360_TAVAN, koru=3, kuru=True)
    adlar2 = satir_al(cikti2, "ACIK_BASLIYORUM_ADLARI=")
    iddia("47l 🔴 NEGATIF-2 (FAIL-CLOSED): arsiv BOZUK -> ARSIV_SERBEST=0",
          "ARSIV_SERBEST=0 " in cikti2, cikti2[-1800:])
    iddia("47m 🔴 NEGATIF-2: `%s` KAPANMAMIS sayildi (ACIK listesinde)" % K360B_POZ_AD,
          K360B_POZ_AD in adlar2, adlar2)
    iddia("47n 🔴 NEGATIF-2: TUM acilislar kilitli — ACIK_BASLIYORUM=4",
          "ACIK_BASLIYORUM=4 " in cikti2, cikti2[-1800:])
    iddia("47o 🔴 NEGATIF-2: sebep ADIYLA basildi (sessiz atlama YASAK)",
          "ARSIV OLCULEMEDI" in cikti2, cikti2[-1800:])
    iddia("47p 🔴 NEGATIF-2: hicbir sey yazilmadi (kutu VE arsiv sha256 DEGISMEDI)",
          sha(b.kutu) == h1 and sha(b.arsiv) == h2)
    del rc2

    # 🔴 BIRIM EKSENI — zaman olcutu ve fail-closed'i DOGRUDAN olc.
    try:
        mod = _arac_modulu(arac)
    except Exception as exc:                                  # noqa: BLE001
        iddia("47q BIRIM: arac modulu yuklendi", False, "%r" % (exc,))
        return
    iddia("47q 🔴 BIRIM: `## 2026-09-03 ~06:40Z — ...` gun VE dakika ayristirilir",
          mod.blok_zamani("## 2026-09-03 ~06:40Z — x") == (20260903, 400),
          "%r" % (mod.blok_zamani("## 2026-09-03 ~06:40Z — x"),))
    iddia("47r 🔴 BIRIM: serbest yazilmis saat (`~07:0xZ`) DAKIKA uretmez, GUN kalir",
          mod.blok_zamani("## 2026-09-03 ~07:0xZ — x") == (20260903, None),
          "%r" % (mod.blok_zamani("## 2026-09-03 ~07:0xZ — x"),))
    iddia("47s 🔴 BIRIM FAIL-CLOSED: gun AYRISTIRILAMAZSA kapanis ASLA gecerli DEGIL",
          mod._kapanis_daha_eski_degil((None, None), (20260903, None)) is False)
    iddia("47t 🔴 BIRIM: ESKI kapanis YENI acilisi ACMAZ",
          mod._kapanis_daha_eski_degil((20260903, None), (20260901, None)) is False)
    iddia("47u 🔴 BIRIM: AYNI GUN + belirsiz saat -> gecerli (esitlik KORUMA yonunde)",
          mod._kapanis_daha_eski_degil((20260903, None), (20260903, None)) is True)
    kayit, hata = mod.arsiv_kapanis_kayitlari(arsiv_uret_k360b(bozuk=True))
    iddia("47v 🔴 BIRIM FAIL-CLOSED: BOZUK arsiv -> BOS kayit + SEBEP",
          kayit == {} and hata is not None, "%r / %r" % (kayit, hata))


# --- (C) KONUM: dev baslikta PROZA `BASLIYORUM` marker DEGILDIR ------------------
# 🔴 GERCEK VAKA (canli kutu blok 16): MaCiT'in cron DUZELTME blogu TUM raporunu TEK
# `## ` satirina yazar; 632. karakterde PROZA olarak `BAŞLIYORUM` gecer ve baslikta
# ne 🚧 ne kalin sarmal vardir. Arac onu MARKER sandi, sonra ayni dev satirdaki ilk
# backtick'li tireli jetonu — bir git HATA DIZGESI — cip adi diye topladi.
K360C_SAHTE_AD = "sentetik-hata-dizgesi"     # cip adi DEGIL, bir hata dizgesi
K360C_DOLGU = ("Olcum surdu ve sayilar defterde; kalan kuyruk dogrulandi, sapma yok, "
               "karar satiri asagida, ayrinti govdede, tekrar tekrar ayni sekilde. ")
# Jetonu 200. karakterin OTESINE itmek icin dolgu TEKRARLANIR (offset ELLE civili).
K360C_UZUN = ("## 2026-09-01 — 🔄 MimarS duzeltme: tespit YANLISTI, geri-alindi. "
              + (K360C_DOLGU * 3)
              + "Push reddi (`%s`) sayesinde gorunur oldu. Ayrica dilim-19 cipi "
                "kutuya BAŞLIYORUM notu dusurmemis (disiplin ihlali)."
              % K360C_SAHTE_AD)
# KONTROL — AYNI dev baslik, jeton BASA alindi: marker OLARAK okunmali (K329 YASIYOR).
K360C_KONTROL = ("## 2026-09-01 — MimarS BAŞLIYORUM: duzeltme turu. "
                 + (K360C_DOLGU * 3)
                 + "Push reddi (`%s`) sayesinde gorunur oldu." % K360C_SAHTE_AD)
# KONTROL-2 — dev baslik, jeton GERIDE ama 🚧 VAR: isaret TARTISMASIZ KILAR.
K360C_ISARETLI = ("## 2026-09-01 — 🚧 MimarS-Isaretli-4Eyl duzeltme turu. "
                  + (K360C_DOLGU * 3)
                  + "Ayrica cip kutuya BAŞLIYORUM notu dusurdu.")


def kutu_uret_k360c(baslik):
    """(C) fiksturu — TEK degisken: en dipteki blogun BASLIK SATIRI."""
    sira = [
        "## 2026-09-01 — MimarA → MimarB: koru dolgusu 0",
        "## 2026-09-01 — MimarA → MimarB: koru dolgusu 1",
        "## 2026-09-01 — MimarA → MimarB: koru dolgusu 2",
        baslik,
    ]
    parcalar = [FM]
    i = 0
    while i < len(sira):
        parcalar.append(cip_blogu(i, sira[i]) + "— MimarS\n\n" + "---\n\n")
        i += 1
    j = 0
    while j < 2:
        parcalar.append(blok(850 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def v48_konum_olcutu(arac, kok):
    """[48] 🔴 K360-C — dev baslikta PROZA gecen `BASLIYORUM` MARKER DEGILDIR.

    MINIMAL UCLU (tek degisken: jetonun KONUMU / isaretin varligi):
      A) jeton 200. karakterin OTESINDE, 🚧 ve kalin sarmal YOK -> MARKER DEGIL:
         blok rotasyona ACIK, sahte ad (`sentetik-hata-dizgesi`) ACIK LISTEYE GIRMEZ.
      B) KONTROL: AYNI dev baslik, jeton BASTA -> MARKER: blok KILITLI (K329 YASIYOR).
      C) KONTROL-2: jeton GERIDE ama 🚧 VAR -> MARKER: isaret TARTISMASIZ KILAR.
    """
    print("\n[48] K360-C KONUM OLCUTU — proza anmasi marker DEGIL (minimal uclu)")
    kok_a = os.path.join(kok, "a")
    os.makedirs(kok_a, exist_ok=True)
    m_a = kutu_uret_k360c(K360C_UZUN)
    a = Alan(kok_a, m_a, "## eski arsiv blogu\n\ngovde\n")
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K360_TAVAN, koru=3)
    adlar = satir_al(cikti, "ACIK_BASLIYORUM_ADLARI=")
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    iddia("48a on kosul: jeton GERCEKTEN 200. karakterin otesinde",
          K360C_UZUN.upper().replace("Ş", "S").replace("İ", "I").find("BASLIYORUM") > 200,
          "offset=%d" % K360C_UZUN.upper().replace("Ş", "S").replace(
              "İ", "I").find("BASLIYORUM"))
    iddia("48b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1200:]))
    iddia("48c 🔴 A: PROZA anmasi MARKER SAYILMADI -> ACIK_BASLIYORUM=0",
          "ACIK_BASLIYORUM=0 " in cikti, cikti[-1500:])
    iddia("48d 🔴 A: sahte ad `%s` ACIK LISTEYE GIRMEDI (cip olmayan blok, cip "
          "olmayan ad)" % K360C_SAHTE_AD, K360C_SAHTE_AD not in adlar, adlar)
    iddia("48e 🔴 A: blok rotasyona ACIK — GERCEKTEN arsive gitti",
          K360C_UZUN in arsiv_s and K360C_UZUN not in kutu_s,
          "blok kutuda kilitli kaldi")
    iddia("48f 🔴 A: yanlis pozitif GIZLENMEDI, govde anmasi olarak SAYILDI",
          "basliyorum_govde_anmasi=1 " in cikti, cikti[-1500:])

    kok_b = os.path.join(kok, "b")
    os.makedirs(kok_b, exist_ok=True)
    b = Alan(kok_b, kutu_uret_k360c(K360C_KONTROL), "## eski arsiv blogu\n\ngovde\n")
    rc_b, cikti_b = kos(arac, b.kutu, b.arsiv, b.kilit, tavan=K360_TAVAN, koru=3)
    iddia("48g 🔴 B KONTROL (MINIMAL CIFT): AYNI dev baslik, jeton BASTA -> MARKER, "
          "ACIK_BASLIYORUM=1", "ACIK_BASLIYORUM=1 " in cikti_b, cikti_b[-1500:])
    iddia("48h 🔴 B KONTROL: blok KUTUDA kaldi (K329 vetosu OLMEDI)",
          K360C_KONTROL in oku(b.kutu), "blok arsive kacti -> K329 OLDU")
    del rc_b

    kok_c = os.path.join(kok, "c")
    os.makedirs(kok_c, exist_ok=True)
    c = Alan(kok_c, kutu_uret_k360c(K360C_ISARETLI), "## eski arsiv blogu\n\ngovde\n")
    rc_c, cikti_c = kos(arac, c.kutu, c.arsiv, c.kilit, tavan=K360_TAVAN, koru=3)
    iddia("48i 🔴 C KONTROL-2: jeton GERIDE ama 🚧 VAR -> MARKER, ACIK_BASLIYORUM=1",
          "ACIK_BASLIYORUM=1 " in cikti_c, cikti_c[-1500:])
    iddia("48j 🔴 C KONTROL-2: blok KUTUDA kaldi (isaret TARTISMASIZ KILDI)",
          K360C_ISARETLI in oku(c.kutu))
    del rc_c
    del kutu_s

    try:
        mod = _arac_modulu(arac)
    except Exception as exc:                                  # noqa: BLE001
        iddia("48k BIRIM: arac modulu yuklendi", False, "%r" % (exc,))
        return
    iddia("48k 🔴 BIRIM: uzun baslikta PROZA anmasi -> False",
          mod.basliyorum_baslikta(K360C_UZUN) is False)
    iddia("48l 🔴 BIRIM MINIMAL CIFT: ayni baslik, jeton BASTA -> True",
          mod.basliyorum_baslikta(K360C_KONTROL) is True)
    iddia("48m 🔴 BIRIM: 🚧 tasiyan uzun baslik -> True (isaret muafiyeti KORUNDU)",
          mod.basliyorum_baslikta(K360C_ISARETLI) is True)
    iddia("48n 🔴 BIRIM REGRESYON: K329'un GERCEK vakasi (duz `BASLIYORUM`, kisa "
          "baslik) HALA marker",
          mod.basliyorum_baslikta(
              "## 2026-08-27 — BASLIYORUM · cip `MimarX-Nobet-27Agu` — tesh") is True)
    iddia("48o 🔴 BIRIM: GOVDE metni icin eski ROL olcutu DEGISMEDI (ayri eksen)",
          mod.basliyorum_rolu(K360C_UZUN) is True)


# ---------------------------------------------------- [49] K373 HARNESS AD SEKLI
# 🔴 OLCULEN CANLI VAKA (4 Eyl, KraL-Tamirci-4Eyl): kutu rotasyonu `tasinabilir=3`de
# TUKENDI, 8 ACIK blogun 6'si `AD_YOK`. DORDUNDE ad BASLIKTA yaziliydi ama BACKTICK'SIZ
# ve TUMU KUCUK HARF (`(çip: agitated-clarke-e96f4f)`). `cip_adi()` backtick ister,
# `gevsek_cip_adi()` BUYUK HARF isterdi -> harness'in urettigi adlar (hepsi kucuk
# harf) IKI EKSENDEN DE gorunmezdi. `agitated-clarke-e96f4f` ve
# `serene-mcclintock-dc34aa` kapanislari ARSIVDE dururken 5 gun kilitli kaldi.
K373_POZ_AD = "agitated-clarke-e96f4f"     # kapanisi ARSIVDE, IMZALI -> SERBEST
K373_DUR_AD = "optimistic-fermi-e89dd3"    # arsivde YALNIZ `🛑 DURDU` -> ACIK KALIR
K373_ANMA_AD = "serene-mcclintock-dc34aa"  # BASKA cipin kapanisinda ANILIR -> ACIK KALIR

K373_POZ_ACIK = ("## 2026-08-30 ~18:xZ — 🚧 MaCiT (çip: %s) **BAŞLIYORUM: dilim-13.**"
                 % K373_POZ_AD)
K373_POZ_KAPANIS = ("## 2026-08-30 ~19:xZ — ✅ MaCiT (çip: %s) **KAPANDI: dilim-13 — "
                    "40 ürün canlıya.**" % K373_POZ_AD)
K373_DUR_ACIK = ("## 2026-08-31 ~07:xZ — 🚧 MaCiT (çip: %s) **BAŞLIYORUM: dilim-16.**"
                 % K373_DUR_AD)
K373_DUR_ARSIV = ("## 2026-08-31 ~09:57Z — 🛑 MaCiT (çip: %s) **DURDU — mekanizma yok.**"
                  % K373_DUR_AD)
K373_ANMA_ACIK = ("## 2026-08-30 ~21:xZ — 🚧 MaCiT (çip: %s) **BAŞLIYORUM: dilim-14.**"
                  % K373_ANMA_AD)
# 🔴 K359-B OLCU ALETI: kapanis BASKA bir cipe ait, basliginda K373_ANMA_AD'i ANIYOR
# ama onunla IMZALAMIYOR. ANMAK ile IMZALAMAK ayri siniftir; anilan cip ACILMAMALI.
K373_ANMA_ARSIV = ("## 2026-08-31 ~02:xZ — ✅ MaCiT 9. cron (`macit-parti-surucusu`) "
                   "**KAPANDI: d14 worktree %s listede yok.**" % K373_ANMA_AD)


def arsiv_uret_k373():
    """ARSIV: POZ kapanisi (IMZALI) + DURDU blogu + ANMA kapanisi (BASKA imza)."""
    parcalar = ["---\nname: sentetik-arsiv\n---\n\n"]
    parcalar.append(cip_blogu(910, K373_POZ_KAPANIS)
                    + "— MaCiT (çip: %s)\n\n" % K373_POZ_AD + "---\n\n")
    parcalar.append(cip_blogu(911, K373_DUR_ARSIV)
                    + "— MaCiT (çip: %s)\n\n" % K373_DUR_AD + "---\n\n")
    parcalar.append(cip_blogu(912, K373_ANMA_ARSIV)
                    + "— MaCiT (`macit-parti-surucusu`)\n\n" + "---\n\n")
    return "".join(parcalar)


def kutu_uret_k373():
    """KUTU: uc acilis da BACKTICK'SIZ kucuk-harfli harness adiyla yazilmis."""
    sira = [
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 0", "MimarA"),
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 1", "MimarA"),
        ("## 2026-09-03 — MimarA → MimarB: koru dolgusu 2", "MimarA"),
        (K373_POZ_ACIK, "MaCiT"),
        (K373_DUR_ACIK, "MaCiT"),
        (K373_ANMA_ACIK, "MaCiT"),
    ]
    parcalar = [FM]
    i = 0
    while i < len(sira):
        baslik, imza = sira[i]
        parcalar.append(cip_blogu(i, baslik) + "— %s\n\n" % imza + "---\n\n")
        i += 1
    j = 0
    while j < 3:
        parcalar.append(blok(820 + j) + "---\n\n")
        j += 1
    return "".join(parcalar)


def v49_harness_ad_sekli(arac, kok):
    """[49] 🔴 K373 — BACKTICK'SIZ KUCUK HARFLI harness adi IKI EKSENDEN DE gorunur.

    POZITIF: `✅ … KAPANDI` + harness-sekilli ad + O ADLA IMZA -> acilis SERBEST.
    NEGATIF-1 (DURUM ISARETI): arsivde `🛑 DURDU` — `✅` YOK, `KAPANDI` YOK. Ad
      cikarilabilir olsa DA kapanis DEGILDIR; "ciplak ad kapanis acar" sinifi KAPALI.
    NEGATIF-2 (ANMA ≠ IMZA): baska cipin kapanisi adi BASLIKTA aniyor ama onunla
      IMZALAMIYOR -> anilan cip ACILMAZ (K359-B korumasi GEVSETILMEDI).
    BIRIM: eski negatif fiksturler (`2026-08-28` rakamsiz-bolut, `cip-raporu` tek
      tire) ve RAKAMSIZ salt-hex kelime (`bir-iki-facade`) HALA elenir.
    """
    print("\n[49] K373 HARNESS AD SEKLI — kucuk harfli backtick'siz ad")
    metin = kutu_uret_k373()
    a = Alan(kok, metin, arsiv_uret_k373())
    iddia("49a fikstur tavani GERCEKTEN asiyor",
          len(metin.splitlines()) > K360_TAVAN, "satir=%d" % len(metin.splitlines()))
    rc, cikti = kos(arac, a.kutu, a.arsiv, a.kilit, tavan=K360_TAVAN, koru=3)
    kutu_s, arsiv_s = oku(a.kutu), oku(a.arsiv)
    adlar = satir_al(cikti, "ACIK_BASLIYORUM_ADLARI=")
    serbest = satir_al(cikti, "ARSIV_SERBEST_ADLARI=")
    iddia("49b rc=0", rc == 0, "rc=%d\n%s" % (rc, cikti[-1500:]))

    iddia("49c 🔴 POZITIF: kucuk harfli `%s` ARTIK ADLANDIRILDI (AD_YOK DEGIL)"
          % K373_POZ_AD, "AD_YOK" not in adlar or K373_POZ_AD in serbest, adlar)
    iddia("49d 🔴 POZITIF: `%s` ARSIV_SERBEST_ADLARI'nda ADIYLA basildi"
          % K373_POZ_AD, K373_POZ_AD in serbest, serbest)
    iddia("49e 🔴 POZITIF: o cipin `BASLIYORUM` blogu GERCEKTEN arsive gitti",
          K373_POZ_ACIK in arsiv_s and K373_POZ_ACIK not in kutu_s,
          "blok kutuda kilitli kaldi -> harness ad ekseni okunmadi")

    iddia("49f 🔴 NEGATIF-1 (DURUM ISARETI): `🛑 DURDU` KAPANIS SAYILMADI — `%s` "
          "HALA ACIK listesinde" % K373_DUR_AD, K373_DUR_AD in adlar, adlar)
    iddia("49g 🔴 NEGATIF-1: DURDU'nun acilis blogu KUTUDA kaldi",
          K373_DUR_ACIK in kutu_s and K373_DUR_ACIK not in arsiv_s,
          "DURDU blogu acilisi serbest birakti = CANLI CIP KAYBI")
    iddia("49h 🔴 NEGATIF-2 (ANMA ≠ IMZA): basliginda ANILAN `%s` ACILMADI"
          % K373_ANMA_AD, K373_ANMA_AD in adlar, adlar)
    iddia("49i 🔴 NEGATIF-2: anilan cipin acilis blogu KUTUDA kaldi",
          K373_ANMA_ACIK in kutu_s and K373_ANMA_ACIK not in arsiv_s,
          "anma IMZA sayildi -> K359-B korumasi OLDU")
    iddia("49j 🔴 TAM SAYI: ARSIV_SERBEST=1 (yalniz POZ), ikinci serbest YOK",
          "ARSIV_SERBEST=1 " in cikti, cikti[-1800:])
    iddia("49k 🔴 TAM SAYI: ACIK_BASLIYORUM=2 (DURDU + ANMA)",
          "ACIK_BASLIYORUM=2 " in cikti, cikti[-1800:])
    iddia("49l lossless GECTI", "lossless_dogrulama=GECTI" in cikti, cikti[-900:])

    try:
        mod = _arac_modulu(arac)
    except Exception as exc:                                  # noqa: BLE001
        iddia("49m BIRIM: arac modulu yuklendi", False, "%r" % (exc,))
        return
    iddia("49m 🔴 BIRIM: kucuk harfli harness adi GEVSEK eksende GORUNUR",
          mod.gevsek_cip_adi("## x — MaCiT (çip: %s) **BASLIYORUM**" % K373_POZ_AD)
          == K373_POZ_AD)
    iddia("49n 🔴 BIRIM: `✅`+`KAPANDI`+harness ad -> UCBIRLIK True",
          mod.kapanis_baslik_ucbirlik(K373_POZ_KAPANIS) is True)
    iddia("49o 🔴 BIRIM: `🛑 DURDU` (✅ YOK) -> UCBIRLIK False",
          mod.kapanis_baslik_ucbirlik(K373_DUR_ARSIV) is False)
    iddia("49p 🔴 BIRIM REGRESYON: `2026-08-28` HALA ad DEGIL (ilk bolut harf degil)",
          mod.gevsek_cip_adi("## 2026-08-28 — duz baslik") is None)
    iddia("49q 🔴 BIRIM REGRESYON: `cip-raporu` HALA ad DEGIL (tek tire)",
          mod.gevsek_cip_adi("## x — cip-raporu hazir") is None)
    iddia("49r 🔴 BIRIM: RAKAMSIZ salt-hex kelime ad SAYILMAZ (`bir-iki-facade`)",
          mod.gevsek_cip_adi("## x — bir-iki-facade notu") is None)
    iddia("49s 🔴 BIRIM: son bolut 6 HANE DEGILSE ad SAYILMAZ (`macit-bisiklet-d22`)",
          mod.gevsek_cip_adi("## x — macit-bisiklet-d22 dali") is None)


VAKALAR = (v01_tavan_altinda, v02_dogru_sayida_blok, v03_birebir_satirlar,
           v04_frontmatter_ve_ust_bloklar, v05_blok_bolunmez,
           v06_arsiv_yoksa_frontmatter, v07_kilit, v08_bozuk_frontmatter,
           v09_bozuk_utf8, v10_kuru, v11_sentetik_ariza, v12_koru_tavani,
           v13_cit_ici_baslik, v14_iki_kosum,
           v15_su_seviyesi_doldurur, v16_su_seviyesi_nop,
           v17_oksuz_govde_kirmizi, v18_ayracli_temiz_kontrol, v19_korluk_beyani,
           v20_koruma_yerinde_atlanir, v21_islenmis_jeton_tasinir,
           v22_ortadaki_koruma_atlanir,
           v23_koruma_denetimi, v24_iki_kosum_birebir,
           v25_govde_anmasi_koruma_uretmez, v26_kapanis_jetonu_hala_korur,
           v27_ayristirilamayan_blok_fail_closed, v28_kayipsizlik_iki_eksen,
           v29_blok_dus_arizasi, v30_tasinabilir_sifir_koruma_tuttu,
           v31_acik_basliyorum_veto, v32_kapanisli_blok_hala_tasinir,
           v33_yanlis_eslesme, v34_d17_denetimi, v35_basliyorum_govde_anmasi,
           v36_gercek_vaka_regresyonu,
           v37_cevrim_kilidi_acar, v38_cevrim_dokunulmazliklari,
           v39_cevrim_sentetik_ariza, v40_cevrim_bayraksiz_gerileme_yok,
           v41_rol_olcutu_alinti, v42_ucuncu_kapanis_kolu,
           v43_kapanis_adi_imza_onayli, v44_cift_butunlugu, v45_d18_denetimi,
           v46_ad_ekseni_ayrismasi, v47_arsiv_duzlemi, v48_konum_olcutu,
           v49_harness_ad_sekli)


def suite(arac, sessiz=False):
    """Tum vakalari kostur. (gecti, kirmizi) dondurur; GECTI/KIRMIZI sifirlanir."""
    del GECTI[:]
    del KIRMIZI[:]
    kok = tempfile.mkdtemp(prefix="kutu-arsivle-test-")
    try:
        i = 0
        while i < len(VAKALAR):
            alt = os.path.join(kok, "v%02d" % (i + 1))
            os.makedirs(alt, exist_ok=True)
            VAKALAR[i](arac, alt)
            i += 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return list(GECTI), list(KIRMIZI)


# -------------------------------------------------------------------- MUTASYON
# 🔴 HEDEF-KOL ATFI (K182): dorduncu alan `kirmizi_bekleniyor`, BESINCI alan
# `hedefler` = mutantin OLDURMESI beklenen VAKA numaralari. "Kirmizi geldi" kanit
# DEGILDIR — kirmizinin hangi vakalarda ciktigi da olculur ve HEDEFLE KARSILASTIRILIR
# ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]). `hedefler` None
# ise (eski mutantlar) yalnizca kirmizi/yesil beklentisi olculur ve atif RAPOR kalir.
MUTANTLAR = (
    ("a) LOSSLESS DOGRULAMASI OLDURULDU (dogrula -> daima bos liste)",
     "    h = []\n    kutu_satir =",
     "    return []\n    h = []\n    kutu_satir =",
     True, None),
    ("b) FLOCK OLDURULDU (kilit hic alinmiyor)",
     "        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n",
     "        pass  # MUTANT: flock kaldirildi\n",
     True, None),
    # K310 (27 Agu): oksuz govde kolu GERCEKTEN olcuyor mu? Kol olmezse v17 YESILE
    # doner — yani "lossless=GECTI" yine kirik kutu icin basilir. Vakanin ta kendisi.
    ("d) OKSUZ GOVDE KOLU OLDURULDU (oksuz_govdeler -> daima bos liste)",
     "    bulgu = []\n    for b, s, baslik, dolu in bolutler(satirlar, bas):",
     "    bulgu = []\n    return bulgu\n    for b, s, baslik, dolu in bolutler(satirlar, bas):",
     True, None),
    ("e) KORLUK BEYANI OLDURULDU (ayracsiz kutuda 0 basip susar)",
     "        if kutu_ayrac == 0:",
     "        if False:  # MUTANT: korluk beyani susturuldu",
     True, None),
    # K313g (27 Agu): koruma kolu IKI PARCADIR — ICRA (sabit kume) ve DENETIM
    # (dogrula/D14). Ikisi AYRI mutantla oldurulur; biri otekini gizlemesin diye
    # beklenen kirmizi vakalari da AYRI.
    # 🔴 CAPA NOTU (K329, 28 Agu): `sabit_indeksler` artik UC bacaklidir (koru /
    # K313g korumasi / K329 acik cip). Capa bu yuzden TEK BACAGA daraltildi —
    # govdenin tamamina capalanmis eski desen yeni bacak eklenince TUTMAZ ve mutant
    # sessizce URETILEMEDI'ye duserdi ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]).
    ("f) KORUMA ICRA KOLU OLDURULDU (sabit kume K313g bacagini yok sayar)",
     "    sabit.update(korumali_indeksler)\n",
     "    pass  # MUTANT: K313g koruma bacagi kaldirildi\n",
     # 28 de OLUR ve bu DOGRUDUR: v28'in BAGIMSIZ oracle'i blok 25'i korumali
     # varsayarak tasinan kumeyi hesaplar; koruma kalkinca arac baska bir kume
     # tasir ve BAYT ekseni tutmaz. Yani v28 koruma-duyarli bir vakadir.
     # 🔴 37/38/40 EKLENDI (K341, 28 Agu): uc K341 vakasinin TABAN (bayraksiz) bacagi
     # "koruma tuttu" hukmunu olcer — 37d/38e/38f/40b/40c dogrudan bu ICRA bacagina
     # bagimlidir. Bacak olunce fail-closed blok bile arsive gider ve o iddialar
     # duser. GERCEK bagimlilik, atif kirliligi DEGIL.
     True, {"20", "22", "26", "27", "28", "30", "37", "38", "40"}),
    ("g) KORUMALI BLOK TESPITI OLDURULDU (korumali_bloklar -> daima bos liste)",
     "    bulgu = []\n    govde_anmasi = 0\n    i = 0\n",
     "    bulgu = []\n    govde_anmasi = 0\n    return bulgu, govde_anmasi\n    i = 0\n",
     # 25 de OLUR ve bu DOGRUDUR: tespit kolu bos donunce `govde_anmasi` sayaci da
     # 0'a duser, v25 sayiyi ADIYLA ariyor. 28 icin gerekce f) ile ayni.
     # 🔴 37/38/40 EKLENDI (K341, 28 Agu): `korumali_bloklar()` K313g korumasinin VE
     # K341 cevriminin TEK KAYNAGIDIR (`cevrilecek_kapanislar` onu cagirir). Tespit
     # olunce hem koruma hem cevrim korlesir — tek kaynagin tek mutantla iki kolu
     # birden oldurmesi TASARIMIN KENDISIDIR ([[ikiz-tanim-sessiz-ayrisma]] caresi).
     True, {"20", "22", "23", "25", "26", "27", "28", "30", "37", "38", "40"}),
    ("h) D14 KORUMA DENETIMI OLDURULDU (sizan jeton sessizce yazilir)",
     "    for _bi, satir_no, ozet, sinif in ek_korumali:\n",
     "    for _bi, satir_no, ozet, sinif in []:  # MUTANT: D14 susturuldu\n",
     True, {"23"}),
    # 🔴 K318 KOL-1 (27 Agu): jeton KONUM ekseni. Mutant olcutu ESKI GENIS haline
    # geri dondurur (jeton NEREDE gecerse gecsin koruma uretir) -> yanlis pozitif
    # vakasi (25) OLMELI, gercek kapanis vakasi (26) YASAMALI. Iki vaka MINIMAL
    # CIFTTIR, yani fark yalnizca olcute atfedilebilir.
    ("i) KAPANIS KONUMU OLCUTU OLDURULDU (jeton NEREDE gecerse koruma uretir)",
     "        elif BEKLEYEN_JETON in satirlar[idx]:\n",
     "        elif True:  # MUTANT: KAPANIS KONUMU olcutu KALDIRILDI\n",
     # 🔴 37/38 EKLENDI (K341, 28 Agu): cevrim de KAPANIS KONUMUNU hedefler (ayni
     # olcut, ayni fonksiyon). Olcut gevserse GOVDE ANMASI satiri da cevrilir —
     # 38b'nin ("govde satiri BIREBIR duruyor") olctugu sey tam olarak budur.
     True, {"25", "37", "38"}),
    # 🔴 K318 KOL-2 (27 Agu): rotasyon GRANULERLIGI. Mutant secimi BITISIK KUYRUGA
    # geri dondurur (korumali bloga carpinca DUR) -> dipteki (20) ve ortadaki (22)
    # koruma vakalari OLMELI; korumasiz vakalar (21, 28...) YASAMALI.
    ("j) GRANULERLIK OLDURULDU (korumali bloga carpinca DUR = bitisik kuyruk)",
     "        if i not in p.sabit:\n"
     "            bas, son = p.araliklar[i]\n"
     "            secilenler.append(i)\n"
     "            kalan_satir -= (son - bas)\n"
     "        i -= 1\n",
     "        if i not in p.sabit:\n"
     "            bas, son = p.araliklar[i]\n"
     "            secilenler.append(i)\n"
     "            kalan_satir -= (son - bas)\n"
     "        else:\n"
     "            break  # MUTANT: bitisik kuyruga geri donuldu\n"
     "        i -= 1\n",
     # 29 YASAR ve bu DOGRUDUR: `kutu-blok-dus` arizasi granulerlikten BAGIMSIZ
     # enjekte edilir; bitisik kuyrukta da is yapilir, ariza yine yakalanir. 29'u
     # hedefe yazmak mutanti olculmedigi bir kola atfetmek olurdu.
     # 🔴 31/32/33 EKLENDI (K329, 28 Agu): K329 fiksturunde ACIK CIP blogu SABIT
     # kumededir, yani bitisik kuyruga donen bir secim onun ALTINDAKI hicbir blogu
     # tasiyamaz. Vaka 32'nin ("veto rotasyonu KILITLEMEZ") tam olarak olctugu sey
     # budur — yani bu uc vaka GRANULERLIGE DUYARLIDIR ve mutantin onlari
     # oldurmesi GERCEK bir bagimliliktir, atif kirliligi DEGIL. Hedefi
     # daraltmak icin vakayi zayiflatmak, olculen ozelligi olcumden cikarirdi.
     # 🔴 37/38 EKLENDI (K341, 28 Agu): K341 fiksturunde de EN DIPTEKI blok (29)
     # fail-closed ve SABIT kumededir; bitisik kuyruga donen bir secim onun
     # ustundeki hicbir blogu tasiyamaz -> 37j/37n/37o duser. Cevrimin AMACI
     # ("kilit acildi") ancak granuler secimle olculebilir.
     # 🔴 42 EKLENDI (K359, 1 Eyl): K359 kapanis fiksturunde SERBEST BIRAKILAN blok
     # (`POZ_ACIK`) kilitli bloklarin ARASINDADIR; bitisik kuyruga donen bir secim ona
     # ULASAMAZ ve 42d ("kapanan cipin blogu ARSIVE gitti") duser. Vakanin olctugu sey
     # "kapanis TANINDI -> blok GERCEKTEN tasindi"dir; o tasima granuler secime
     # BAGIMLIDIR — atif kirliligi DEGIL.
     # 🔴 43/44 EKLENDI (K359-B, 2 Eyl): 43'te SERBEST BIRAKILAN iki acilis, KILITLI
     # dort acilisin USTUNDEDIR — bitisik kuyruga donen secim onlara ULASAMAZ (43d/43f
     # duser). 44'te ise PINLENEN iki kapanis, tasinacak bloklarin ARASINDADIR: bitisik
     # kuyruk ilk pinli bloga carpip DURUR ve NEGATIF bacak (44j/44k "normal yondeki
     # cift TASINDI") olculemez. Ikisi de GERCEK bagimlilik.
     # 🔴 46/47 EKLENDI (K360, 4 Eyl): her iki fiksturde de SERBEST birakilan
     # acilislar KILITLI acilislarin USTUNDEDIR; bitisik kuyruga donen bir
     # secim onlara ULASAMAZ ve "blok GERCEKTEN arsive gitti" bacaklari duser.
     True, {"20", "22", "28", "31", "32", "33", "37", "38", "42", "43", "44",
            "46", "47", "49"}),
    # 🔴 K318 KOL-2 (27 Agu): kayipsizligin IKI EKSENDE BASILMASI sarti. Beyan
    # susturulursa 28 OLMELI; hesap dogru kalsa bile "basilmayan sayi olculmemis
    # sayidir" ([[aracin-teshis-cumlesi-olcum-degil]]).
    ("k) KAYIPSIZLIK BEYANI SUSTURULDU (iki eksen ADIYLA basilmaz)",
     '        print("KAYIPSIZLIK blok: once=%d kalan=%d tasinan=%d toplam=%d  [KAPI]"',
     '        print("kayipsizlik gizlendi %d %d %d %d"',
     True, {"28"}),
    # 🔴 K329 (28 Agu) — ACIK CIP KOLU DORT PARCADIR ve her biri AYRI mutantla
    # oldurulur: ICRA (sabit kume bacagi), DENETIM (D17), KONUM OLCUTU (baslik mi
    # govde mi), ESLESTIRME (hangi blok o cipin kapanisi sayilir).
    # `l` ve `o` AYNI vaka kumesini oldurur ve bu BEKLENEN bir ortusme: uc K329
    # vakasi (31/32/33) TEK fiksturu paylasir. Ayirt edici iz ciktida durur —
    # `l`de `ACIK_BASLIYORUM=1` HALA basilir (tespit yasiyor, ICRA olmus), `o`da
    # sayi 0'a duser (tespit olmus). Ortusme ADIYLA yazildi ki "atif kirli" diye
    # okunmasin.
    ("l) K329 VETO ICRA KOLU OLDURULDU (acik cip sabit kumeye GIRMIYOR)",
     "    sabit.update(acik_indeksler)\n",
     "    pass  # MUTANT: K329 acik cip bacagi kaldirildi\n",
     # 🔴 41/42 EKLENDI (K359, 1 Eyl): iki yeni vakanin KONTROL bacaklari (41j/41k/41n
     # ve 42g/42i/42k) "gercek acik blok HALA kilitler"i olcer — yani ICRA bacagina
     # DOGRUDAN bagimlidirlar. Bacak olunce acik bloklar arsive kacar ve o iddialar
     # duser. Bu vakalarin VARLIK SEBEBI zaten "daraltma K329'u OLDURMEDI"dir.
     # 🔴 43 EKLENDI (K359-B, 2 Eyl): 43'un DORT NEGATIF bacagi (43h/43j/43l/43n)
     # "acik blok KUTUDA kaldi, arsive SIZMADI" der — dogrudan ICRA bacagi. 44 OLMEZ
     # ve bu DOGRUDUR: 44'un pinlemesi K329 vetosundan DEGIL, `koru` tabani ile konum
     # olcutunden turer; iki kol AYRI kaldi (golgelenme YOK).
     # 🔴 46/47 EKLENDI (K360, 4 Eyl): 46'nin UC negatif bacagi ve 47'nin
     # zaman/tuketim/fail-closed bacaklari "acik blok KUTUDA kaldi, arsive
     # SIZMADI" der — dogrudan ICRA bacagi.
     True, {"31", "32", "33", "36", "41", "42", "43", "46", "47", "49"}),
    ("m) D17 ACIK CIP DENETIMI OLDURULDU (sizan acik blok sessizce yazilir)",
     "    for _bi, ad, ozet, sinif in ek_acik:\n",
     "    for _bi, ad, ozet, sinif in []:  # MUTANT: D17 susturuldu\n",
     True, {"34"}),
    # 🔴 CAPA NOTU (K359, 1 Eyl): olcut artik `basliyorum_rolu()` cagrisidir; capa o
    # cagriya tasindi. Mutantin ANLAMI DEGISMEDI — baslik yerine TUM BLOK olculur.
    ("n) K329 KONUM OLCUTU OLDURULDU (BASLIYORUM govdede gecse de veto uretir)",
     "        if not basliyorum_baslikta(baslik):\n",
     "        if not basliyorum_rolu(\"\".join(satirlar[bas:son])):\n",
     # 🔴 48 EKLENDI (K360-C, 4 Eyl): olcut BASLIK yerine TUM BLOGU okurса
     # 48A'nin dev raporu yine marker sayilir ve "proza anmasi MARKER DEGIL"
     # bacagi duser. K360-C ile K329 AYNI konum ekseninin iki ucudur.
     True, {"35", "48"}),
    ("o) K329 ESLESTIRME KOLU GEVSETILDI (adi ANAN her blok KAPANIS sayiliyor)",
     "        if kapanis:\n",
     "        if True:  # MUTANT: her blok KAPANIS sayiliyor\n",
     # 🔴 42 EKLENDI (K359, 1 Eyl): "her blok kapanis" demek K359'un DORT NEGATIF
     # fiksturunu de serbest birakir (N1/N3/N4 ADLARI listeden duser) — vaka 42 tam
     # olarak bu gevsemeyi olcmek icin yazildi.
     # 🔴 43 EKLENDI (K359-B, 2 Eyl): ayni gevseme 43'un DORT negatifini de serbest
     # birakir — ozellikle N2 ("adi ANAN + O CIP imzali ama KAPANIS OLMAYAN blok"),
     # ki bu mutant altinda o blok kapanis SAYILIR ve imza onayi da tuttugu icin cip
     # SERBEST KALIR. GERCEK bagimlilik.
     # 🔴 46/47/48 EKLENDI (K360, 4 Eyl): "her blok KAPANIS" demek uc fiksturun
     # de negatiflerini serbest birakir (46 N5/N6/N7, 47 zaman/tuketim, 48
     # kontrol bacaklari) — gevsemeyi olcen vakalarin ta kendisi.
     True, {"31", "32", "33", "36", "42", "43", "46", "47", "48",
            "49"}),
    # 🔴 GEVSEK AD kolu (28 Agu, ucuncu canli vaka) — backtick'siz yazilmis cip adini
    # okuyan asimetrik bacak. Olmezse vaka 36'nin ② sarmali `ACIK_ADSIZ`a duser: blok
    # HALA korunur (fail-closed dogru) ama SINIFI degisir — yani kol "kismen" olur ve
    # yalnizca sinif jetonu bunu gorur.
    # 🔴 43 EKLENDI (K359-B, 2 Eyl): 43'un POZITIF cipinin ACILISI da backtick'siz
    # yazilmistir (gercek vakanin sekli). Bacak olunce o acilis `ACIK_ADSIZ`a duser,
    # adi HIC cikarilamaz ve kapanis TANINSA BILE eslesemez -> 43c/43d duser. Yani
    # (A) kolunun IKI UCU da (kapanis tarafi `x`, acilis tarafi `p`) olculur.
    # 🔴 CAPA NOTU (K360-A, 4 Eyl): ACILIS tarafindaki gevsek ad kolu artik
    # `cip_kimlikleri()` icindedir; capa oraya tasindi. Mutantin ANLAMI AYNI:
    # acilis basligi yalniz DAR kimligi uretir. 46 EKLENDI — o vakanin P1
    # bacagi (acilis GEVSEK adli) DOGRUDAN bu kola dayanir.
    ("p) GEVSEK AD KOLU OLDURULDU (backtick'siz cip adi okunmuyor)",
     "    gevsek = gevsek_cip_adi(baslik)\n"
     "    if gevsek and gevsek not in adlar:\n",
     "    gevsek = None  # MUTANT: gevsek ad kolu kaldirildi\n"
     "    if gevsek and gevsek not in adlar:\n",
     True, {"36", "43", "46", "49"}),
    # 🔴 K341 (28 Agu) — CEVRIM KOLU UC PARCADIR ve her biri AYRI mutantla oldurulur:
    # ICRA (cevrilecek satirlarin tespiti), DENETIM (dogrula_cevrim C1-C8) ve SINIF
    # SUZGECI (yalniz sinif=="KAPANIS" cevrilir). `q` ve `s` AYNI vaka kumesini
    # oldurur ve bu ORTUSME BEKLENENDIR — iki K341 davranis vakasi (37/38) tek
    # fiksturu paylasir. Ayirt edici iz ciktida durur: `q`da arac rc=0 doner ve
    # `CEVRIM=0` basar (kol sessizce hicbir sey yapmaz), `s`de arac rc=1 ile
    # KIRMIZI yanar (C3 jeton ikamesi tutmaz). Ortusme ADIYLA yazildi ki "atif
    # kirli" diye okunmasin ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
    ("q) 🔴 CEVRIM ICRA KOLU OLDURULDU (cevrilecek kapanis HIC bulunmuyor)",
     "    cikti = []\n    atlanan = []\n    for blok_idx, satir_no, ozet, sinif in bulgu:\n",
     "    cikti = []\n    atlanan = []\n    return cikti, atlanan, govde_anmasi\n"
     "    for blok_idx, satir_no, ozet, sinif in bulgu:\n",
     True, {"37", "38"}),
    ("r) 🔴 CEVRIM DENETIMI OLDURULDU (dogrula_cevrim -> daima bos liste)",
     "    h = []\n    e = eski_metin.splitlines(keepends=True)\n",
     "    return []\n    h = []\n    e = eski_metin.splitlines(keepends=True)\n",
     True, {"39"}),
    ("s) 🔴 CEVRIM SINIF SUZGECI GEVSETILDI (AYRISTIRILAMAYAN blok da cevriliyor)",
     '        if sinif != "KAPANIS":\n',
     '        if False:  # MUTANT: fail-closed suzgeci kaldirildi\n',
     True, {"37", "38"}),
    # 🔴 K359 (1 Eyl) — IKI YENI KOL, her biri AYRI mutantla oldurulur + BIR ESDEGER
    # KONTROL. MP1 ROL olcutunu, MP2 UC-SART BIRLIKTELIGINI, MP3 TIRNAK ELEMESINI
    # hedefler; MP0 anlamca ESDEGER bir yeniden yazimdir ve HICBIR SEY oldurmemelidir
    # (batarya "her degisiklige kirmizi yanan" bir alarm degil, OLCU aletidir).
    ("t) 🔴 MP1: ROL OLCUTU ALT-DIZGEYE GERI DONDU (alinti yine marker sayilir)",
     "    return BASLIYORUM_JETON in sadelestir(tirnak_disi(metin))\n",
     "    return True  # MUTANT MP1: ROL olcutu ALT-DIZGEYE geri dondu\n",
     True, {"41"}),
    # 🔴 MP2 GENIS OLUR ve bu GERCEK bir bagimliliktir: "uc sarttan HERHANGI BIRI"
    # demek, backtick'li ad TASIYAN HER basligi kapanis yapar -> `kapanan` kumesi
    # sisar ve K329'un TUM veto vakalari (31/32/33/36) serbest kalir. Yani bu mutant
    # tam da spec'in "GENISLETME TUZAGI" dedigi seyi yapar; hedefin genis olmasi
    # atif kirliligi DEGIL, tuzagin yaricapinin ta kendisidir.
    ("u) 🔴 MP2: UC SART 'HERHANGI BIRI'NE GEVSEDI (ciplak `KAPANDI` kapanis sayilir)",
     # 🔴 CAPA TAZELENDI (K373, 4 Eyl): ③ kolu `or harness_baslik_adi(...)` ile
     # genisleyince ESKI capa TUTMADI ve mutant sessizce URETILEMEDI'ye dustu
     # ([[capa-cokmesi-arkasindaki-capalari-gizler]]). Mutant HALA yalniz UC-SART
     # mantigini olcer: ③ kolu iki yanda da AYNEN durur, degisen yalnizca ①/②'nin
     # "hepsi" yerine "herhangi biri"ne gevsemesidir.
     "    if KAPANIS_DURUM_ISARETI not in baslik:\n"
     "        return False\n"
     "    if KAPANIS_SOZU not in sadelestir(tirnak_disi(baslik)):\n"
     "        return False\n"
     "    return cip_adi(baslik) is not None or harness_baslik_adi(baslik) is not None\n",
     "    if KAPANIS_DURUM_ISARETI in baslik:\n"
     "        return True\n"
     "    if KAPANIS_SOZU in sadelestir(baslik):\n"
     "        return True\n"
     "    return cip_adi(baslik) is not None or harness_baslik_adi(baslik) is not None\n",
     # 🔴 43 EKLENDI (K359-B, 2 Eyl): `o` ile ayni yaricap — uc sart gevseyince 43'un
     # negatifleri de kapanis sayilir. Ortusme BEKLENENDIR; ayirt edici iz ciktida
     # durur (`o` HER blogu kapanis yapar, `u` yalniz uc sarttan BIRINI tasiyanlari).
     # 🔴 47/48 EKLENDI (K360, 4 Eyl): ciplak `KAPANDI` kapanis sayilinca 47'nin
     # arsiv kayitlari ve 48'in dolgu bloklari da "kapanis" olur; iki vakanin
     # sayili bacaklari (ARSIV_SERBEST=, ACIK_BASLIYORUM=) duser.
     # 🔴 49 EKLENDI (K373, 4 Eyl): uc sart "herhangi biri"ne gevseyince 49'un
     # NEGATIF-1'i (`🛑 DURDU`, `✅` YOK) KAPANIS sayilir ve DURDU blogu acilisi
     # SERBEST birakir — 49f/49g'nin olctugu sey tam olarak budur. GERCEK bagimlilik.
     True, {"31", "32", "33", "36", "42", "43", "47", "48", "49"}),
    ("v) 🔴 MP3: TIRNAK ELEMESI KALDIRILDI (alintidaki jeton yine sayilir)",
     "    return _TIRNAK_RE.sub(\" \", metin)\n",
     "    return metin  # MUTANT MP3: TIRNAK elemesi KALDIRILDI\n",
     True, {"41", "42"}),
    # 🔴 K359-B (2 Eyl) — IKI YENI KOL, DORT MUTANT + BIR ESDEGER KONTROL.
    # (A) KAPANIS ADI iki bacaklidir ve HER IKI YONDE de olculur: `x` bacagi SILER
    # (gercek kapanis yine gorunmez -> POZITIF duser), `y` bacagi GEVSETIR (imza
    # onayi kalkar -> NEGATIF fiksturler serbest kalir). Tek yonlu olcum, "gevsetme
    # serbest birakma yonune akmadi" iddiasini OLCEMEZDI.
    ("x) 🔴 K359-B: GEVSEK KAPANIS ADI KOLU OLDURULDU (backticksiz kapanis okunmuyor)",
     "    gevsek = gevsek_cip_adi(satirlar[bas])\n",
     "    gevsek = None  # MUTANT: K359-B gevsek kapanis adi kaldirildi\n",
     # 🔴 46 EKLENDI (K360-A, 4 Eyl): 46'nin P2 bacagi (kapanis GEVSEK adli)
     # DOGRUDAN bu kola dayanir.
     True, {"43", "46", "49"}),
    # 🔴 CAPA NOTU (K360-A, 4 Eyl): onay kosulu `kapanis_kimlikleri()`ne tasindi
    # ve IKI SATIRA yayildi; capa yeni sekle guncellendi. 46 EKLENDI — o vakanin
    # N7 negatifi ("kapanisi BASKASI imzalamis") AYNI onaya dayanir.
    ("y) 🔴 K359-B: IMZA ONAYI KALDIRILDI (adi ANAN her kapanis SAHIPLENIYOR sayilir)",
     "    if (gevsek and gevsek not in adlar\n"
     "            and _imzada_geciyor(satirlar, bas, son, gevsek)):\n",
     "    if gevsek and gevsek not in adlar:  # MUTANT: IMZA onayi kaldirildi\n",
     True, {"43", "46", "49"}),
    # (B) CIFT BUTUNLUGU de iki parcadir — ICRA (pinleme) ve DENETIM (D18) — ve AYRI
    # mutantlarla oldurulur; ayrica OLCUTUN KONUM BACAGI (`o < c`) tek basina olculur,
    # cunku `ACILIS_SABIT` bacagi onu GOLGELEYEBILIR ([[yeni-kol-onceki-kolun-golgesinde-olur]]).
    ("z) 🔴 K359-B: CIFT BUTUNLUGU ICRA KOLU OLDURULDU (kapanis sabit kumeye GIRMIYOR)",
     "        p.sabit = p.sabit | set(c for c, _ad, _s in p.cift_korumasi)\n",
     "        pass  # MUTANT: cift butunlugu ICRA bacagi kaldirildi\n",
     True, {"44"}),
    ("aa) 🔴 K359-B: KONUM BACAGI (`o < c`) OLDURULDU (yalniz ACILIS_SABIT pinlenir)",
     '                elif o < c:\n',
     '                elif False:  # MUTANT: ACILIS_DAHA_YENI bacagi kaldirildi\n',
     True, {"44"}),
    ("bb) 🔴 K359-B: D18 CIFT DENETIMI OLDURULDU (bolunen cift sessizce yazilir)",
     # 🔴 CAPA NOTU (K360-A, 4 Eyl): D18 artik KESISIM olcuyor; capa yeni kosula
     # tasindi. Mutantin ANLAMI DEGISMEDI (D18 susturulur).
     "        if ortak:\n",
     "        if False:  # MUTANT: D18 susturuldu\n",
     True, {"45"}),
    ("cc) MP0 ESDEGER KONTROL: IMZA taramasi while yerine ERKEN DONUSLE yazildi",
     "    j = bas\n"
     "    while j < son:\n"
     "        if IMZA_RE.match(satirlar[j]) and desen.search(satirlar[j]):\n"
     "            return True\n"
     "        j += 1\n"
     "    return False\n",
     "    j = son - 1\n"
     "    while j >= bas:\n"
     "        if IMZA_RE.match(satirlar[j]) and desen.search(satirlar[j]):\n"
     "            return True\n"
     "        j -= 1\n"
     "    return False\n",
     False, set()),
    ("w) MP0 ESDEGER KONTROL: uc-sart kontrollerinin SIRASI degisti (anlam AYNI)",
     "    if KAPANIS_DURUM_ISARETI not in baslik:\n"
     "        return False\n"
     "    if KAPANIS_SOZU not in sadelestir(tirnak_disi(baslik)):\n"
     "        return False\n",
     "    if KAPANIS_SOZU not in sadelestir(tirnak_disi(baslik)):\n"
     "        return False\n"
     "    if KAPANIS_DURUM_ISARETI not in baslik:\n"
     "        return False\n",
     False, set()),
    ("c) ILGISIZ metin degisikligi (tani satirinin bosluk hizalamasi)",
     'print("KUTU  : %s" % kutu_yolu)',
     'print("KUTU : %s" % kutu_yolu)',
     False, set()),
    # 🔴 K360-B/C (4 Eyl 2026) — YENI KOLLAR, HER BIRI AYRI MUTANTLA OLDURULUR.
    # Her mutant OLDURDUGU KOLU ADIYLA tasir (K182): "kirmizi geldi" kanit DEGILDIR.
    # K360-A icin AYRI mutant YAZILMADI — o kolun IKI bacagi zaten `p)` (acilis gevsek
    # kimligi) ve `y)` (kapanis IMZA onayi) mutantlariyla olculur; ucuncu bir mutant
    # ayni kolu TEKRAR olcerdi ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
    ("ab) 🔴 K360-B: DUZLEM KOLU OLDURULDU (arsiv HIC okunmaz)",
     "    if not arsiv_kayitlari:\n        return {}\n",
     "    if True:\n        return {}  # MUTANT: arsiv duzlemi korlestirildi\n",
     True, {"47", "49"}),
    ("ac) 🔴 K360-B: ZAMAN SIRASI OLDURULDU (ESKI kapanis YENI acilisi acar)",
     "    a_gun, a_dk = acilis_z\n",
     "    return True  # MUTANT: zaman sirasi kaldirildi\n    a_gun, a_dk = acilis_z\n",
     True, {"47"}),
    ("ad) 🔴 K360-B: TUKETIM OLDURULDU (bir kapanis SINIRSIZ acilis acar)",
     "                    serbest[idx] = (ad, liste.pop(j))\n",
     "                    serbest[idx] = (ad, liste[j])  # MUTANT: TUKETIM kaldirildi\n",
     True, {"47"}),
    ("ae) 🔴 K360-C: KONUM OLCUTU OLDURULDU (proza anmasi yine MARKER sayilir)",
     "    return sade.find(BASLIYORUM_JETON) <= KONUM_TAVANI\n",
     "    return True  # MUTANT: KONUM olcutu kaldirildi\n",
     True, {"48"}),
    # 🔴 KONTROL MUTANTI — YESIL KALMALI. `KONUM_TAVANI` OLCULEN BIR BOSLUGUN
    # ortasindadir: gercek cip acilislarinin en buyuk jeton konumu 76, kutudaki yanlis
    # pozitifin konumu 632. Tavani 300'e cekmek o boslugun ICINDE kalir, yani hicbir
    # kolu degistirmez. Bu mutant bataryanin SABITE degil DAVRANISA capalandigini
    # kanitlar; kirmizi yanarsa testler asiri-oturmustur ([[kabul-fiksturu-yasagi-kutsar]]).
    ("af) KONTROL: KONUM_TAVANI 200 -> 300 (olculen boslugun ICINDE, YESIL kalmali)",
     "KONUM_TAVANI = 200\n",
     "KONUM_TAVANI = 300\n",
     False, None),
    # ------------------------------------------------ K373 HARNESS AD SEKLI (4 Eyl)
    # Kol IKI YERDE tuketilir: (1) `gevsek_cip_adi()` — acilis+kapanis kimligi,
    # (2) `kapanis_baslik_ucbirlik()` ③ bacagi — blogun KAPANIS SAYILMASI. Ikisi
    # AYRI mutantla oldurulur ki biri otekini GIZLEMESIN; ayrica GEVSETME yonu
    # (rakam sarti) kendi mutantiyla olculur — daraltma ve gevsetme ayri sinifdir.
    ("ag) 🔴 K373: HARNESS SEKIL KOLU OLDURULDU (kucuk harfli ad yine gorunmez)",
     "    if not HARNESS_AD_RE.fullmatch(ad):\n        return False\n",
     "    return False  # MUTANT: harness sekil kolu kaldirildi\n",
     True, {"49"}),
    ("ah) 🔴 K373: RAKAM SARTI KALDIRILDI (salt-hex kelime de ad sayilir)",
     '    return any(k.isdigit() for k in ad.rsplit("-", 1)[1])\n',
     "    return True  # MUTANT: rakam sarti kaldirildi (GEVSETME yonu)\n",
     True, {"49"}),
    ("ai) 🔴 K373: UCBIRLIK ③ BACAGI GERI DARALTILDI (yalniz backtick'li ad)",
     "    return cip_adi(baslik) is not None or harness_baslik_adi(baslik) is not None\n",
     "    return cip_adi(baslik) is not None  # MUTANT: harness bacagi kaldirildi\n",
     True, {"49"}),
    ("aj) MP0 ESDEGER KONTROL: sekil suzgeclerinin SIRASI degisti (anlam AYNI)",
     "        if _insan_adi_sekli(ad) or _harness_adi_sekli(ad):\n",
     "        if _harness_adi_sekli(ad) or _insan_adi_sekli(ad):\n",
     False, None),
)


def vaka_oneki(iddia_adi):
    """Iddia adinin basindaki VAKA numarasi ('20o ...' -> '20')."""
    import re as _re
    m = _re.match(r"^(\d+)", iddia_adi)
    return m.group(1) if m else "?"


def mutasyon_turu():
    print("=" * 78)
    print("CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, canli arac DEGISMEZ")
    print("=" * 78)
    canli_once = sha(ARAC)
    print("canli tools/kutu-arsivle.py sha256 (ONCE): %s" % canli_once)
    kaynak = oku(ARAC)
    kok = tempfile.mkdtemp(prefix="kutu-arsivle-mutant-")
    sonuc = []
    try:
        yama_tutmadi = 0
        i = 0
        while i < len(MUTANTLAR):
            ad, eski, yeni, kirmizi_bekleniyor, hedefler = MUTANTLAR[i]
            print("\n" + "-" * 78)
            print("MUTANT %s" % ad)
            if kaynak.count(eski) != 1:
                print("  ❌ MUTASYON CAPASI TUTMADI (%d eslesme) -> mutant uretilemedi"
                      % kaynak.count(eski))
                yama_tutmadi += 1
                sonuc.append((ad, None, kirmizi_bekleniyor, False, None, hedefler))
                i += 1
                continue
            mutant = os.path.join(kok, "mutant-%d.py" % i)
            yaz(mutant, kaynak.replace(eski, yeni, 1))
            g, k = suite(mutant)
            oldu = bool(k)
            olen_onekler = set(vaka_oneki(x) for x in k)
            print("  -> mutant sonucu: GECTI=%d KIRMIZI=%d (beklenen: %s)"
                  % (len(g), len(k), "KIRMIZI" if kirmizi_bekleniyor else "YESIL"))
            if k:
                print("     ilk 3 kirmizi: %r" % k[:3])
            # 🔴 HEDEF-KOL ATFI: "kirmizi geldi" YETMEZ — kirmizinin CIKTIGI vakalar
            # hedefle BIREBIR ayni mi? Fazla kirmizi = mutant baska bir kolu da
            # kesiyor (atif kirli); eksik = hedef kol GERCEKTEN olculmuyor.
            if hedefler is None:
                atif_ok = True
                print("     olen vakalar: %s  (ATIF: RAPOR — hedef tanimlanmadi)"
                      % (sorted(olen_onekler) or "-"))
            else:
                atif_ok = (olen_onekler == hedefler)
                print("     olen vakalar : %s" % (sorted(olen_onekler) or "-"))
                print("     hedef vakalar: %s" % sorted(hedefler))
                print("     ATIF         : %s"
                      % ("DOGRU" if atif_ok else "YANLIS (olen != hedef)"))
            sonuc.append((ad, oldu, kirmizi_bekleniyor,
                          (oldu == kirmizi_bekleniyor) and atif_ok,
                          olen_onekler, hedefler))
            i += 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    canli_sonra = sha(ARAC)
    print("\ncanli tools/kutu-arsivle.py sha256 (SONRA): %s" % canli_sonra)
    print("=" * 78)
    basarisiz = [s for s in sonuc if not s[3]]
    j = 0
    while j < len(sonuc):
        ad, oldu, bek, ok, olenler, hedefler = sonuc[j]
        print("  %s %s -> %s (beklenen %s)"
              % ("✅" if ok else "❌", ad,
                 {None: "URETILEMEDI", True: "KIRMIZI", False: "YESIL"}[oldu],
                 "KIRMIZI" if bek else "YESIL"))
        j += 1
    olen_sayisi = len([s for s in sonuc if s[1] is True])
    beklenen_olen = len([m for m in MUTANTLAR if m[3]])
    atifli = [s for s in sonuc if s[5] is not None]
    atif_dogru = len([s for s in atifli if s[4] == s[5]])
    print("MUTANT=%d/%d YAMA_TUTMADI=%d HEDEF_KOL_ATFI=%d/%d"
          % (olen_sayisi, beklenen_olen, yama_tutmadi, atif_dogru, len(atifli)))
    if canli_once != canli_sonra:
        print("❌ CANLI ARAC DEGISTI (mutant sizdi!): %s != %s"
              % (canli_once, canli_sonra))
        return 1
    print("✅ canli arac sha256 ESIT — mutant sizmadi")
    return 1 if basarisiz else 0


def main():
    ap = argparse.ArgumentParser(description="tools/kutu-arsivle.py kabul testi")
    ap.add_argument("--arac", default=ARAC, help="test edilecek arac yolu (mutant icin)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="cift yonlu mutasyon turu (kopyaya uygulanir)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon_turu()
    if not os.path.exists(a.arac):
        print("KIRMIZI: arac yok -> %s" % a.arac)
        return 1
    print("=" * 78)
    print("KUTU ARSIVLEYICI KABUL TESTI — arac: %s" % a.arac)
    print("=" * 78)
    g, k = suite(a.arac)
    print("\n" + "=" * 78)
    print("VAKA=%d  IDDIA=%d  GECTI=%d  KIRMIZI=%d" % (len(VAKALAR), len(g) + len(k),
                                                       len(g), len(k)))
    if k:
        i = 0
        while i < len(k):
            print("  ❌ %s" % k[i])
            i += 1
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: GECTI ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
