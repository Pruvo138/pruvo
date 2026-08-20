#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/nobet-sayac-durustluk-test.py — N4A ③: SAYAC DURUSTLUGU.

Okan'in baglayici cumlesi: *"sozde degil ozde calisan bir sistem istiyorum."*
Bu bataryanin TEK isi su iddiayi makinece imkansiz kilmaktir:

    "USTUSTE_ONARIMSIZ dustu, demek ki bir sey ONARILDI."

Sayac ONARIM OLMADAN dusuyorsa, dususu bir BASARI sanmak yanlistir; ve bir
ajan/insan sayac dosyasini ELLE sifirlarsa, hat "onardi" gorunur ama HICBIR SEY
onarilmamistir. Bu batarya iki yoldan da kirmizi yanar.

🔴 IKIZ TANIM YOK: olculen fonksiyonlar KOPYALANMAZ, uretim dosyasindan
   (`~/.claude/cron/nobet-kapi.py`) ITHAL EDILIR. Modul yuklenemezse ya da
   fonksiyon kaybolursa hukum OLCULEMEDI'dir — sessiz YESIL YOKTUR
   ([[batarya-kapsam-tabani-sayiyla-civilenir]]).

INVARYANT (tek cumle):
    Sayacin DUSMESI yalnizca ayni turda ONARIM>0 ise MESRUDUR.
    (`onarim = kapanan + dagitilan`, nobet-kapi.py'de turetilir.)

🔴 IKI HAL AYRI TUTULUR (CI kosucusu bir kusur DEGILDIR):
    KAPSAM_DISI — uretim dosyasi bu makinede HIC YOK (GitHub runner'inda
                  `~/.claude/cron` yoktur). V1-V6 kosulamaz; MUTANTLAR YINE KOSAR
                  cunku olculen invaryant (`dusus_mesru_mu`) bu dosyanin
                  KENDISINDEDIR, uretime bagli degildir. rc=0.
    OLCULEMEDI  — uretim dosyasi VAR ama yuklenemiyor / isim kaybolmus. rc=2.
Bu ayrimin kendisi de IDDIA DEGIL: H1/H2 kontrolleri iki hali hermetik olarak
olcer (yok dosya -> KAPSAM_DISI · isimsiz dosya -> OLCULEMEDI). Ucuncu kova
ikinciyi yutarsa kapi sessizce korlesirdi.

KABUL (calistirilabilir):
    python3 tools/nobet-sayac-durustluk-test.py
    Okan'in makinesinde : VAKA=6/6 MUTANT=2/2 HEDEF_KOL_ATFI=2/2 HAL=5/5  rc=0
    CI kosucusunda      : VAKA=KAPSAM_DISI MUTANT=2/2 HEDEF_KOL_ATFI=2/2 HAL=5/5  rc=0
🔴 `HAL=5/5` iki hâlin AYRILDIGINI kanitlar (H1..H5). ORTAM DEGISKENI YOKTUR:
   CI kolu, ana yolun kullandigi AYNI saf `hal_karari` fonksiyonu uzerinden
   H3/H4 ile dogrudan olculur; H5 mutanti "OLCULEMEDI'yi KAPSAM_DISI'ya cevir"
   yolunu KIRMIZI yakar. Yani ucuncu kova ikinciyi yutamaz ve bunu SAYI gosterir.

Cikis kodu: 0 = gecti · 1 = kusur · 2 = OLCULEMEDI (uretim var ama olculemiyor).
"""

import importlib.util
import inspect
import json
import os
import shutil
import sys
import tempfile

# 🔴 TEK YOL, ORTAM DEGISKENI YOK (20 Agu, mimar uyarisi uzerine KALDIRILDI).
# Bir ara `PRUVO_N4A_URETIM_YOLU` override'i vardi: "CI kolunu Okan'in
# makinesinde de olcebilmek" icin konmustu. O bir BYPASS KOLUDUR — override'i
# olmayan bir yola set eden herkes (ya da gelecekteki bir is akisi) GERCEK bir
# `OLCULEMEDI`yi sessizce `KAPSAM_DISI`ya dusurup bataryayi yesil yakabilirdi.
# Cozum knob'u KORUMAK degil KALDIRMAK oldu: hal karari SAF bir fonksiyona
# (`hal_karari`) cikarildi ve CI kolu ortam degiskeni olmadan, H3/H4
# kontrolleriyle DOGRUDAN olculuyor. Silahlanacak yuzey ortadan kalkti.
URETIM_YOLU = "/Users/okan/.claude/cron/nobet-kapi.py"

# 🔴 KAPSAM TABANI SAYIYLA CIVILI: bu iki isim uretimden gelmek ZORUNDA.
GEREKEN_ISIMLER = ("ustuste_onarimsiz_sonraki", "ustuste_onarimsiz_guncelle",
                   "ustuste_onarimsiz_oku")
VAKA_TABANI = 6
MUTANT_TABANI = 2
# H1..H5: sebep ayrimi (2) + CI kolu / kapsam kaybi karari (2) + kova-yutma
# mutanti (1). Sayiyla civili: bir kontrol dusarse tally KUCULUR ve gorunur.
HAL_TABANI = 5

RC_GECTI = 0
RC_KUSUR = 1
RC_OLCULEMEDI = 2


def uretim_modulu(yol=URETIM_YOLU):
    """Uretim modulunu ITHAL eder. Basarisizsa (None, sebep) doner.

    Sebep dizesi HAL AYRIMINI tasir: "URETIM DOSYASI YOK" (KAPSAM_DISI) vs
    digerleri (OLCULEMEDI). Cagiran bu iki hali KARISTIRMAZ.
    """
    if not os.path.isfile(yol):
        return None, "URETIM DOSYASI YOK: %s" % yol
    # Uretim modulu KARDES modul ithal ediyor (`import kilit`); cron kokunu
    # sys.path'e almadan `ModuleNotFoundError: No module named 'kilit'` alinir.
    # Olculdu (20 Agu, N4A ilk isci turu): adim 4 tam bu yuzden OLCULEMEDI dondu.
    kok = os.path.dirname(os.path.abspath(yol))
    if kok not in sys.path:
        sys.path.insert(0, kok)
    try:
        ad = "n4a_uretim_nobet_kapi"
        spec = importlib.util.spec_from_file_location(ad, yol)
        if spec is None or spec.loader is None:
            return None, "spec_from_file_location None: %s" % yol
        mod = importlib.util.module_from_spec(spec)
        eski = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.dont_write_bytecode = eski
    except Exception as hata:                                  # noqa: BLE001
        return None, "%s: %s" % (type(hata).__name__, hata)
    eksik = [ad for ad in GEREKEN_ISIMLER if not hasattr(mod, ad)]
    if eksik:
        return None, "URETIMDE EKSIK ISIM: %s" % ",".join(eksik)
    return mod, None


# ------------------------------------------------------------------------------
# INVARYANT — sayacin dususu ne zaman MESRUDUR?
# ------------------------------------------------------------------------------
def dusus_mesru_mu(onceki, sonraki, onarim):
    """Sayacin DUSMESI yalnizca ONARIM>0 ise mesrudur.

    Dusme yoksa (sonraki >= onceki) soru sorulmaz: mesru.
    """
    if sonraki >= onceki:
        return True
    return onarim > 0


def sayac_durustlugu(sonraki_fn, onceki, onarim):
    """Bir `sonraki` uygulamasinin invaryanti bozup bozmadigini olcer.

    Return: (yeni_deger, mesru_mu)
    """
    yeni = sonraki_fn(onceki, onarim)
    return yeni, dusus_mesru_mu(onceki, yeni, onarim)


# --- MUTANTLAR ----------------------------------------------------------------
# M1 SAHTE-DUSUS : onarim olmasa da sayaci sifirlar (hattin "onardim" yalani)
def _mutant_sahte_dusus(onceki, onarim):                       # noqa: ARG001
    return 0


# M2 SESSIZ-ERIME: her turda bir azaltir (yavas ama ayni sinif yalan)
def _mutant_sessiz_erime(onceki, onarim):                      # noqa: ARG001
    return max(0, onceki - 1)


MUTANTLAR = (
    ("M1-SAHTE-DUSUS", _mutant_sahte_dusus),
    ("M2-SESSIZ-ERIME", _mutant_sessiz_erime),
)


def _sayac_yaz_elle(yol, deger):
    """🔴 ELLE SIFIRLAMA TAKLIDI — yasak davranisin ta kendisi (izole dosyada)."""
    with open(yol, "w", encoding="utf-8") as dosya:
        json.dump({"ustuste_onarimsiz": deger}, dosya)
        dosya.write("\n")


def hal_karari(mod, sebep, *, mutant=None):
    """SAF karar: (HAL, rc). Ana yol da kontroller de BUNU cagirir (ikiz yok).

    HAL:
      TAMAM       — uretim yuklendi, tam batarya kosar
      KAPSAM_DISI — uretim dosyasi HIC YOK (CI kosucusu). rc=0 (kusur degil),
                    ama yalnizca V1-V6 icin; mutant cekirdegi yine kosar.
      OLCULEMEDI  — uretim VAR ama yuklenemiyor / isim eksik. rc=2 (KIRMIZI).

    🔴 M3-KOVA-YUTMA mutanti tam burayi hedefler: "olculemedi"yi "kapsam disi"na
    cevirmek, gercek bir kapsam kaybini sessizce yesile boyamaktir.
    """
    if mod is not None:
        return "TAMAM", RC_GECTI
    if mutant == "M3-KOVA-YUTMA":
        return "KAPSAM_DISI", RC_GECTI      # ucuncu kova ikinciyi YUTAR
    if (sebep or "").startswith("URETIM DOSYASI YOK"):
        return "KAPSAM_DISI", RC_GECTI
    return "OLCULEMEDI", RC_OLCULEMEDI


def _sahte_yuk(gecici, kip):
    """Uretim yukleme sonucunu HERMETIK olarak taklit eder: (mod, sebep)."""
    if kip == "yok":
        return uretim_modulu(os.path.join(gecici, "hic-yok", "nobet-kapi.py"))
    if kip == "bozuk":
        yol = os.path.join(gecici, "isimsiz-nobet-kapi.py")
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write("# uretim taklidi: dosya VAR, aranan isimler YOK\nX = 1\n")
        return uretim_modulu(yol)
    raise ValueError(kip)


def hal_kontrolleri(gecici):
    """H1/H2: KAPSAM_DISI ile OLCULEMEDI hallerini HERMETIK olarak ayirir.

    Bu iki kontrol her ortamda kosar. Amaci: CI kolunun (KAPSAM_DISI) sessiz
    bir muafiyet deligine donusmesini engellemek — "dosya yok" ile "dosya var
    ama bozuk" AYNI KOVAYA girerse kapi korlesir ve bunu kimse gormez.
    """
    m1, s1 = _sahte_yuk(gecici, "yok")
    h1 = (m1 is None and s1.startswith("URETIM DOSYASI YOK"))
    m2, s2 = _sahte_yuk(gecici, "bozuk")
    h2 = (m2 is None and s2.startswith("URETIMDE EKSIK ISIM"))
    print("H1 sebep ayrimi: dosya YOK       -> %r %s" % (s1, "✓" if h1 else "✗"))
    print("H2 sebep ayrimi: dosya VAR/isimsiz -> %r %s" % (s2, "✓" if h2 else "✗"))

    # 🔴 H3/H4 — CI KOLU ORTAM DEGISKENI OLMADAN OLCULUR.
    #    Ana yolun kullandigi AYNI saf fonksiyon (`hal_karari`) cagriliyor;
    #    "kosucuda ne olacak" IDDIA degil OLCUM. Knob YOK, dolayisiyla
    #    silahlanacak yuzey de yok.
    hal3, rc3 = hal_karari(m1, s1)
    h3 = (hal3 == "KAPSAM_DISI" and rc3 == RC_GECTI)
    print("H3 CI kolu     : uretim YOK -> HAL=%s rc=%d (beklenen KAPSAM_DISI/0) %s"
          % (hal3, rc3, "✓" if h3 else "✗"))
    hal4, rc4 = hal_karari(m2, s2)
    h4 = (hal4 == "OLCULEMEDI" and rc4 == RC_OLCULEMEDI)
    print("H4 kapsam kaybi: uretim BOZUK -> HAL=%s rc=%d (beklenen OLCULEMEDI/2) %s"
          % (hal4, rc4, "✓" if h4 else "✗"))

    # 🔴 H5 — MUTANT: ucuncu kova ikinciyi YUTARSA kirmizi yanar.
    #    Hedef kol: BOZUK vakasi (OLCULEMEDI -> KAPSAM_DISI'ya kayar mi).
    #    Yan eksen: YOK vakasi mutant altinda DEGISMEMELI (atif temiz olsun).
    m_hal4, m_rc4 = hal_karari(m2, s2, mutant="M3-KOVA-YUTMA")
    m_hal3, m_rc3 = hal_karari(m1, s1, mutant="M3-KOVA-YUTMA")
    hedef_kirmizi = ((hal4, rc4) != (m_hal4, m_rc4))
    yan_yesil = ((hal3, rc3) == (m_hal3, m_rc3))
    h5 = hedef_kirmizi and yan_yesil
    print("H5 MUTANT M3-KOVA-YUTMA:")
    print("   hedef  : BOZUK normal=%s/%d mutant=%s/%d (degismeli) %s"
          % (hal4, rc4, m_hal4, m_rc4, "✓" if hedef_kirmizi else "✗"))
    print("   yan eks: YOK   normal=%s/%d mutant=%s/%d (AYNI kalmali) %s"
          % (hal3, rc3, m_hal3, m_rc3, "✓" if yan_yesil else "✗"))
    print("   ATIF   : %s" % ("hedef kol kirmizi + yan eksen YESIL"
                              if h5 else "KUSUR"))
    return sum(1 for x in (h1, h2, h3, h4, h5) if x)


def mutant_kolu(sonraki_uretim):
    """MUTANTLAR — her ortamda kosar.

    Olculen sey `dusus_mesru_mu` invaryantidir ve o BU DOSYADADIR; uretim
    moduluine bagli DEGILDIR. `sonraki_uretim` verilmisse "negatif" ayagi da
    kosar (kirmizinin sebebi mutant mi, ambiyans mi).
    """
    mutant_gecen = 0
    atif_gecen = 0
    for ad, fn in MUTANTLAR:
        hedef_deger, hedef_mesru = sayac_durustlugu(fn, 105, 0)
        hedef_kirmizi = (hedef_mesru is False)
        kontrol_deger, kontrol_mesru = sayac_durustlugu(fn, 105, 3)
        if sonraki_uretim is not None:
            _u, uretim_mesru = sayac_durustlugu(sonraki_uretim, 105, 0)
            negatif_notu = "URETIM kodu ayni girdide mesru=%s" % uretim_mesru
        else:
            # Uretim yok (CI): negatif ayak REFERANS dogru davranisla kosar.
            _r, uretim_mesru = sayac_durustlugu(
                lambda o, n: (0 if n > 0 else o + 1), 105, 0)
            negatif_notu = ("REFERANS dogru davranis mesru=%s (uretim KAPSAM_DISI)"
                            % uretim_mesru)
        yan_yesil = (kontrol_mesru is True and uretim_mesru is True)

        print("MUTANT %s" % ad)
        print("  hedef  : sonraki(105, onarim=0)=%s mesru=%s (beklenen False) %s"
              % (hedef_deger, hedef_mesru, "✓" if hedef_kirmizi else "✗"))
        print("  kontrol: sonraki(105, onarim=3)=%s mesru=%s (YESIL kalmali) %s"
              % (kontrol_deger, kontrol_mesru, "✓" if kontrol_mesru else "✗"))
        print("  negatif: %s (kirmizinin sebebi MUTANT, ambiyans degil) %s"
              % (negatif_notu, "✓" if uretim_mesru else "✗"))
        if hedef_kirmizi:
            mutant_gecen += 1
            print("  SONUC  : BEKLENDI YAKALANDI (mutant yasamaz)")
        else:
            print("  SONUC  : BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        if hedef_kirmizi and yan_yesil:
            atif_gecen += 1
            print("  ATIF   : hedef kol kirmizi + yan eksen YESIL")
        else:
            print("  ATIF   : KUSUR")
        print("")
    return mutant_gecen, atif_gecen


def kos():
    mod, sebep = uretim_modulu()
    print("N4A SAYAC DURUSTLUGU — KENDINI-TEST")
    print("uretim modulu: %s" % URETIM_YOLU)

    gecici = tempfile.mkdtemp(prefix="n4a-sayac-")
    try:
        hal_gecen = hal_kontrolleri(gecici)
        print("")

        hal, hal_rc = hal_karari(mod, sebep)     # ana yol da AYNI saf fonksiyon
        print("HAL=%s (uretim yuklendi mi: %s)" % (hal, mod is not None))

        if hal == "KAPSAM_DISI":
            # 🔴 CI KOSUCUSU — kusur DEGIL. V1-V6 fiziksel olarak kosulamaz;
            # mutant cekirdegi YINE kosar (invaryant bu dosyada).
            print("  uretim dosyasi bu makinede YOK (CI kosucusu). "
                  "V1-V6 ATLANDI; mutant cekirdegi KOSUYOR. SEBEP=%s" % sebep)
            print("")
            mutant_gecen, atif_gecen = mutant_kolu(None)
            print("VAKA=KAPSAM_DISI MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d HAL=%d/%d"
                  % (mutant_gecen, MUTANT_TABANI, atif_gecen, MUTANT_TABANI,
                     hal_gecen, HAL_TABANI))
            tamam = (mutant_gecen == MUTANT_TABANI
                     and atif_gecen == MUTANT_TABANI and hal_gecen == HAL_TABANI)
            return RC_GECTI if tamam else RC_KUSUR

        if hal == "OLCULEMEDI":
            # Uretim VAR ama olculemiyor -> gercek kapsam kaybi.
            print("HUKUM=OLCULEMEDI SEBEP=%s" % sebep)
            print("VAKA=0/%d MUTANT=0/%d HEDEF_KOL_ATFI=0/%d HAL=%d/%d"
                  % (VAKA_TABANI, MUTANT_TABANI, MUTANT_TABANI, hal_gecen,
                     HAL_TABANI))
            return hal_rc

        sonraki = mod.ustuste_onarimsiz_sonraki
        guncelle = mod.ustuste_onarimsiz_guncelle
        oku = mod.ustuste_onarimsiz_oku

        # ② "sayaci dusuren kod yolu" — IDDIA DEGIL, calisan koddan TURETILIR.
        try:
            kaynak_yolu = inspect.getsourcefile(sonraki)
            _satirlar, ilk_satir = inspect.getsourcelines(sonraki)
            print("sayaci DUSUREN kod yolu: %s:%d  (ustuste_onarimsiz_sonraki)"
                  % (kaynak_yolu, ilk_satir))
        except (OSError, TypeError) as hata:
            print("sayaci DUSUREN kod yolu: OLCULEMEDI (%s)" % hata)
        print("")

        vaka_gecen = 0
        # --- V1: onarimsiz tur -> ARTAR (dusmez) --------------------------
        v1_deger = sonraki(105, 0)
        v1 = (v1_deger == 106)
        print("V1 onarimsiz tur ARTIRIR      : sonraki(105, 0)=%s (beklenen 106) %s"
              % (v1_deger, "✓" if v1 else "✗"))
        vaka_gecen += 1 if v1 else 0

        # --- V2: onarim olan tur -> SIFIRLANIR ----------------------------
        v2_deger = sonraki(105, 1)
        v2 = (v2_deger == 0)
        print("V2 onarimli tur SIFIRLAR      : sonraki(105, 1)=%s (beklenen 0) %s"
              % (v2_deger, "✓" if v2 else "✗"))
        vaka_gecen += 1 if v2 else 0

        # --- V3: GERCEK dosya yolu (atomik yazici) ------------------------
        yol = os.path.join(gecici, "nobet-onarimsiz-sayac.json")
        _sayac_yaz_elle(yol, 105)
        d1 = guncelle(0, yol=yol)
        d2 = guncelle(0, yol=yol)
        d3 = guncelle(2, yol=yol)
        d4 = oku(yol=yol)
        v3 = (d1 == 106 and d2 == 107 and d3 == 0 and d4 == 0)
        print("V3 dosya yolu (atomik)        : 105 -> %s -> %s -> (onarim=2) %s "
              "-> oku %s %s"
              % (d1, d2, d3, d4, "✓" if v3 else "✗"))
        vaka_gecen += 1 if v3 else 0

        # --- V4: INVARYANT uretim kodunda TUTUYOR -------------------------
        _y, m_a = sayac_durustlugu(sonraki, 105, 0)
        _y2, m_b = sayac_durustlugu(sonraki, 105, 3)
        v4 = (m_a is True and m_b is True)
        print("V4 uretim invaryanti TUTAR    : onarimsiz=%s onarimli=%s "
              "(ikisi de mesru olmali) %s" % (m_a, m_b, "✓" if v4 else "✗"))
        vaka_gecen += 1 if v4 else 0

        # --- V5: 🔴 ELLE SIFIRLAMA ONARIM DEGILDIR ------------------------
        #     Dosyayi elle 0 yazmak sayaci "dusurmus" gorunur; ama bir sonraki
        #     onarimsiz tur 1'den devam eder ve invaryant 105 -> 0 gecisini
        #     GAYRIMESRU isaretler. Yani elle sifirlama ONARIM UYDURMAZ.
        yol5 = os.path.join(gecici, "elle.json")
        _sayac_yaz_elle(yol5, 105)
        _sayac_yaz_elle(yol5, 0)                 # <- YASAK HAREKET (taklit)
        sonraki_tur = guncelle(0, yol=yol5)
        elle_mesru = dusus_mesru_mu(105, 0, onarim=0)
        v5 = (sonraki_tur == 1 and elle_mesru is False)
        print("V5 ELLE sifirlama ONARIM DEGIL: elle 105->0 mesru=%s (beklenen "
              "False) · sonraki onarimsiz tur=%s (beklenen 1) %s"
              % (elle_mesru, sonraki_tur, "✓" if v5 else "✗"))
        vaka_gecen += 1 if v5 else 0

        # --- V6: dosya BOZUKSA sifirdan baslar (fail-safe, yalan uretmez) --
        yol6 = os.path.join(gecici, "bozuk.json")
        with open(yol6, "w", encoding="utf-8") as dosya:
            dosya.write("{bozuk")
        v6_deger = oku(yol=yol6)
        v6 = (v6_deger == 0)
        print("V6 bozuk dosya -> 0           : oku()=%s (beklenen 0) %s"
              % (v6_deger, "✓" if v6 else "✗"))
        vaka_gecen += 1 if v6 else 0

        print("")

        # --- MUTANTLAR (uretim VARKEN: negatif ayak gercek uretimle) -------
        mutant_gecen, atif_gecen = mutant_kolu(sonraki)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("VAKA=%d/%d MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d HAL=%d/%d"
          % (vaka_gecen, VAKA_TABANI, mutant_gecen, MUTANT_TABANI,
             atif_gecen, MUTANT_TABANI, hal_gecen, HAL_TABANI))
    tamam = (vaka_gecen == VAKA_TABANI and mutant_gecen == MUTANT_TABANI
             and atif_gecen == MUTANT_TABANI and hal_gecen == HAL_TABANI)
    return RC_GECTI if tamam else RC_KUSUR


if __name__ == "__main__":
    sys.exit(kos())
