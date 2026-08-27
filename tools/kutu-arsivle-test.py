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
        su_seviye_orani=0.8):
    komut = [sys.executable, arac, "--kutu", kutu, "--arsiv", arsiv, "--kilit", kilit,
             "--tavan", str(tavan), "--koru", str(koru),
             "--su-seviye-orani", str(su_seviye_orani)]
    if kuru:
        komut.append("--kuru")
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
           v29_blok_dus_arizasi, v30_tasinabilir_sifir_koruma_tuttu)


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
    ("f) KORUMA ICRA KOLU OLDURULDU (sabit kume koruma bacagini yok sayar)",
     "    sabit = set(range(min(koru, blok_sayisi_)))\n"
     "    sabit.update(korumali_indeksler)\n    return sabit\n",
     "    sabit = set(range(min(koru, blok_sayisi_)))\n    return sabit\n",
     # 28 de OLUR ve bu DOGRUDUR: v28'in BAGIMSIZ oracle'i blok 25'i korumali
     # varsayarak tasinan kumeyi hesaplar; koruma kalkinca arac baska bir kume
     # tasir ve BAYT ekseni tutmaz. Yani v28 koruma-duyarli bir vakadir.
     True, {"20", "22", "26", "27", "28", "30"}),
    ("g) KORUMALI BLOK TESPITI OLDURULDU (korumali_bloklar -> daima bos liste)",
     "    bulgu = []\n    govde_anmasi = 0\n    i = 0\n",
     "    bulgu = []\n    govde_anmasi = 0\n    return bulgu, govde_anmasi\n    i = 0\n",
     # 25 de OLUR ve bu DOGRUDUR: tespit kolu bos donunce `govde_anmasi` sayaci da
     # 0'a duser, v25 sayiyi ADIYLA ariyor. 28 icin gerekce f) ile ayni.
     True, {"20", "22", "23", "25", "26", "27", "28", "30"}),
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
     True, {"25"}),
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
     True, {"20", "22", "28"}),
    # 🔴 K318 KOL-2 (27 Agu): kayipsizligin IKI EKSENDE BASILMASI sarti. Beyan
    # susturulursa 28 OLMELI; hesap dogru kalsa bile "basilmayan sayi olculmemis
    # sayidir" ([[aracin-teshis-cumlesi-olcum-degil]]).
    ("k) KAYIPSIZLIK BEYANI SUSTURULDU (iki eksen ADIYLA basilmaz)",
     '        print("KAYIPSIZLIK blok: once=%d kalan=%d tasinan=%d toplam=%d  [KAPI]"',
     '        print("kayipsizlik gizlendi %d %d %d %d"',
     True, {"28"}),
    ("c) ILGISIZ metin degisikligi (tani satirinin bosluk hizalamasi)",
     'print("KUTU  : %s" % kutu_yolu)',
     'print("KUTU : %s" % kutu_yolu)',
     False, set()),
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
