#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — `tools/reklam-oci-kosucu.py` ZARAR ESIGI kararini GERCEKTEN kosar.

══════════════════════════════════════════════════════════════════════════════
🔴 NEDEN BU TEST YAML METNI OKUMAZ
══════════════════════════════════════════════════════════════════════════════
Zarar esigi `.github/workflows/reklam-oci.yml` kabugunda yasasaydi, bu dosya ancak
YAML metninde bir dizge ARAYABILIRDI. Dizge arayan bir kabul, kararin KENDISINI hic
kosmaz: govde tersine cevrilse bile dizge yerinde durdugu icin YESIL kalirdi — alet
KOR olur ([[kabul-teslim-edilmeyen-iskeleyle-saglanirsa-alet-kor-kalir]]). Bu yuzden
karar `tools/reklam-oci-kosucu.py::karar` icine TASINDI ve burada CAGRILIYOR.

BATARYA (dort zorunlu vaka + uc ek eksen):
  1. bekleyen=0, kimlik YOK   -> rc 0 · EYLEM=BEKLE · birebir `HAL=KIMLIK-BEKLIYOR BEKLEYEN=0`
  2. bekleyen=3, kimlik YOK   -> rc 1 · EYLEM=ZARAR · yukleme CAGRILMAZ
  3. bekleyen=3, kimlik VAR   -> yukleme DENENIR (kol tam 1 kez cagrilir)
  4. durum OLCULEMEDI (None)  -> rc 3 · EYLEM=OLCULEMEDI · yukleme CAGRILMAZ
  5. durum kolu PATLAR        -> rc 3 (istisna yesile dusmez)
  6. kimlik VAR + yukleme rc=1-> rc 1 (yukleme kirmizisi YUTULMAZ)
  7. bayrak AYRISMASI         -> rc 3 (ikiz tanim sessiz kalamaz)

MUTANT (izole kopyada; CANLI govde DEGISMEZ — [[mutant-canli-govdede-yasamaz]]):
  her mutant EN AZ BIR vakayi KIRMIZI yakmalidir. `SURVIVOR=0` basilmazsa kabul DUSER.
  🔴 Hangi vakanin oldurdugu CIVILENMEZ — beklenen-kirmizi kumesi taban degisince
  ikinci kat bayatlar ([[mutant-beklenen-kirmizi-kumesi-taban-degisince-ikinci-kat-bayatlar]]).

Kullanim:
  python3 tools/reklam-oci-kosucu-test.py              # batarya + mutant (CI kolu)
  python3 tools/reklam-oci-kosucu-test.py --mutant     # yalniz mutant kolu
"""

import argparse
import importlib.util
import os
import re
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOSUCU = os.path.join(TOOLS, "reklam-oci-kosucu.py")
YUKLEYICI = os.path.join(TOOLS, "reklam-oci-yukleyici.py")
AKIS = os.path.join(os.path.dirname(TOOLS), ".github", "workflows", "reklam-oci.yml")


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 🔴🔴 ALAN KUMESI ELLE YAZILMAZ — TEK KAYNAKTAN TURETILIR.
# Bu liste bir zamanlar `DORT_ALAN` adiyla elle yaziliydi ve kume dort ayri yerde
# ayri ayri duruyordu. `developer token` emekli edilince (9 Eyl 2026) dordunu elle
# yamamak gerekti: bu depoda OLCULMUS bayatlama sinifidir. Artik kume yalnizca
# `reklam-oci-yukleyici.py::KIMLIK_ALANLARI` icinde yasiyor, burasi onu IMPORT EDER.
ZORUNLU_ALANLAR = list(
    modul_yukle(YUKLEYICI, "reklam_oci_yukleyici_kabul").ZORUNLU_ALAN_ADLARI)


# ══════════════════════════════════════════════════════════════════════════════
# YAML IKIZI — Python'un IMPORT EDEMEDIGI tek yuzey
# ══════════════════════════════════════════════════════════════════════════════
# Is akisindaki `KIMLIK_BAYRAK` ifadesi alan kumesini elle sayar ve Python onu
# import EDEMEZ. Ikizi silemiyoruz; yapabilecegimiz sey SESSIZ AYRISMASINI
# engellemektir: asagidaki kol YAML'in saydigi kumeyi AYRISTIRIR ve TEK KAYNAK
# ile BIREBIR karsilastirir. Bir alan eklenir/silinirse kabul KIRMIZI yanar.
#
# 🔴 Bu kolun kapattigi ASIL ARIZA soyle isliyordu: emekli alan bayraktan
# CIKARILMAZSA ifade ASLA 'VAR' olamaz -> hat merge edilmis olmasina ragmen OLU
# kalir ve hicbir kirmizi yanmaz (kimlik yoklugu tek basina kirmizi DEGIL).
def yaml_bayrak_alanlari(metin):
    """`KIMLIK_BAYRAK:` ifadesindeki `secrets.<AD> != ''` adlarini AYIKLA.

    🔴 MENZIL KASITLI DAR — yalniz bayrak IFADESININ govdesi taranir:
      * asagidaki `env:` bloku alanlari zaten TEK TEK gecirir (gecirmesi de gerekir,
        emekli alan dahil) — orasi bayragin SAYDIGI kume DEGILDIR;
      * yorum satirlari da `secrets.X != ''` yazar (ornek olarak).
    Tum dosyayi taramak bu yuzden YANLIS EKSEN olurdu
    ([[eslesme-anahtari-yanlissa-sifir-bulgu-yesil-sanilir]]).
    Doner: sirali ad listesi. Ifade bulunamazsa `None` (YESIL DEGIL -> OLCULEMEDI).
    """
    govde, topluyor = [], False
    for satir in metin.splitlines():
        cip = satir.lstrip()
        if not topluyor:
            if cip.startswith("#") or not cip.startswith("KIMLIK_BAYRAK:"):
                continue
            topluyor = True
        govde.append(satir)
        if "}}" in satir:
            break
    else:
        # Bayrak hic bulunmadi YA DA ifade `}}` ile KAPANMADI -> OLCULEMEDI.
        return None
    return sorted(set(re.findall(r"secrets\.([A-Za-z0-9_]+)\s*!=\s*''",
                                 "\n".join(govde))))


def ikiz_ayrismasi(yaml_metni, zorunlu):
    """Doner: "" (ayrisma YOK) | ayrismayi ADIYLA soyleyen metin."""
    yaml_kume = yaml_bayrak_alanlari(yaml_metni)
    if yaml_kume is None:
        return "KIMLIK_BAYRAK ifadesi is akisinda BULUNAMADI (OLCULEMEDI)"
    kaynak = sorted(set(zorunlu))
    if yaml_kume == kaynak:
        return ""
    return ("YAML fazlasi=%s · YAML eksigi=%s"
            % (sorted(set(yaml_kume) - set(kaynak)),
               sorted(set(kaynak) - set(yaml_kume))))


# ══════════════════════════════════════════════════════════════════════════════
# KOL SAHTELERI — ag YOK, D1 YOK, secret YOK.
# ══════════════════════════════════════════════════════════════════════════════
def durum_sabit(deger):
    def _kol():
        return deger
    return _kol


def durum_patlar():
    def _kol():
        raise RuntimeError("D1 acilamadi (kasitli — OLCULEMEDI ekseni)")
    return _kol


def kimlik_sabit(tam):
    def _kol():
        return (True, []) if tam else (False, list(ZORUNLU_ALANLAR))
    return _kol


def yukle_sayaci(rc=0, metin="YUKLEME: gonderilen=3 basarili=3 basarisiz=0 istek=1"):
    """Cagrilma SAYISINI tutar — 'denendi mi' sorusu rc ile ayirt EDILEMEZ."""
    kayit = {"n": 0}

    def _kol():
        kayit["n"] += 1
        return rc, metin
    return _kol, kayit


# ══════════════════════════════════════════════════════════════════════════════
# BATARYA — her vaka (ad, gecti_mi, mesaj) doner. M = olculen modul (gercek|mutant)
# ══════════════════════════════════════════════════════════════════════════════
def batarya(M):
    sonuc = []

    def ekle(ad, kosul, mesaj, m_bagimli=True):
        """`m_bagimli=False` -> vaka OLCULEN MODULDEN bagimsizdir (kaynak/YAML ekseni).

        🔴 Bu bayrak bir MASKELEMEYI onler: modulden bagimsiz bir vaka kirmizi
        yanarsa HER mutant da kirmizi yanar ve hepsi "oldu" gorunur -> gercek
        SAGKALAN gizlenirdi ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
        `mutant_kolu` bu vakalari OLDURME hesabina KATMAZ; gercek bataryada ise
        tam yetkiyle sayilir ve kirmizi yakar.
        """
        sonuc.append((ad, bool(kosul), mesaj, bool(m_bagimli)))

    # ── 1. bekleyen=0, kimlik YOK -> YESIL + birebir satir ──────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk)
    metin = "\n".join(satir)
    ekle("1a rc", rc == 0, "bekleyen=0+kimlik yok -> rc=%d (beklenen 0)" % rc)
    ekle("1b eylem", eylem == M.EYLEM_BEKLE,
         "eylem=%s (beklenen BEKLE)" % eylem)
    ekle("1c birebir satir", "HAL=KIMLIK-BEKLIYOR BEKLEYEN=0" in metin,
         "ozet `HAL=KIMLIK-BEKLIYOR BEKLEYEN=0` satirini BASMIYOR")
    ekle("1d yukleme denenmedi", say["n"] == 0,
         "kimlik yokken yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # ── 2. bekleyen=3, kimlik YOK -> ZARAR ESIGI, KIRMIZI ───────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(3), kimlik_sabit(False), yk)
    metin = "\n".join(satir)
    ekle("2a rc", rc == 1, "bekleyen=3+kimlik yok -> rc=%d (beklenen 1)" % rc)
    ekle("2b eylem", eylem == M.EYLEM_ZARAR, "eylem=%s (beklenen ZARAR)" % eylem)
    ekle("2c sayi basildi", "BEKLEYEN=3" in metin,
         "zarar metni BEKLEYEN sayisini BASMIYOR")
    ekle("2d yukleme denenmedi", say["n"] == 0,
         "kimlik yokken yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # ── 3. bekleyen=3, kimlik VAR -> yukleme DENENIR ────────────────────────
    yk, say = yukle_sayaci(rc=0)
    rc, satir, eylem = M.kos(durum_sabit(3), kimlik_sabit(True), yk)
    ekle("3a yukleme denendi", say["n"] == 1,
         "kimlik varken yukleme %d kez cagrildi (beklenen 1)" % say["n"])
    ekle("3b eylem", eylem == M.EYLEM_YUKLE, "eylem=%s (beklenen YUKLE)" % eylem)
    ekle("3c rc", rc == 0, "basarili yuklemede rc=%d (beklenen 0)" % rc)

    # ── 4. durum OLCULEMEDI (None) -> rc 3, YESIL DEGIL ─────────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(None), kimlik_sabit(False), yk)
    ekle("4a rc", rc == 3, "durum None -> rc=%d (beklenen 3)" % rc)
    ekle("4b eylem", eylem == M.EYLEM_OLCULEMEDI,
         "eylem=%s (beklenen OLCULEMEDI)" % eylem)
    ekle("4c yukleme denenmedi", say["n"] == 0,
         "olculemedi kolunda yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # ── 5. durum kolu PATLAR -> istisna YESILE dusmez ───────────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_patlar(), kimlik_sabit(False), yk)
    ekle("5a rc", rc == 3, "durum kolu patladi -> rc=%d (beklenen 3)" % rc)

    # ── 6. kimlik VAR ama yukleme KIRMIZI -> rc YUTULMAZ ────────────────────
    yk, say = yukle_sayaci(rc=1, metin="YUKLEME: basarisiz=2")
    rc, satir, eylem = M.kos(durum_sabit(2), kimlik_sabit(True), yk)
    ekle("6a rc", rc == 1, "yukleme rc=1 iken kosucu rc=%d (beklenen 1)" % rc)

    # ── 7. BAYRAK AYRISMASI -> ikiz tanim sessiz kalamaz ────────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk, bayrak="VAR")
    ekle("7a rc", rc == 3, "bayrak VAR / olcum YOK -> rc=%d (beklenen 3)" % rc)
    ekle("7b yukleme denenmedi", say["n"] == 0,
         "ayrisma kolunda yukleme %d kez cagrildi (beklenen 0)" % say["n"])
    # ayni yonde: bayrak dogruysa karar DEGISMEZ
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk, bayrak="YOK")
    ekle("7c dogru bayrak karari bozmaz", rc == 0 and eylem == M.EYLEM_BEKLE,
         "bayrak YOK iken rc=%d eylem=%s (beklenen 0/BEKLE)" % (rc, eylem))

    # ── 8. OLCULEN IKIZ: YAML `KIMLIK_BAYRAK` == TEK KAYNAK ─────────────────
    # 7. vaka bayragin KOSUM ANINDAKI degerini capraz olcer; bu vaka bayragin
    # TANIMINI olcer. Ikisi ayri eksendir: yanlis alan kumesiyle yazilmis bir
    # bayrak KOSUMDA tutarli gorunur (bayrak YOK, olcum de YOK) ama hat ASLA
    # 'VAR' olamayacagi icin SESSIZCE OLU kalir.
    try:
        yaml_metni = open(AKIS, encoding="utf-8").read()
    except OSError as e:                              # noqa: BLE001
        ekle("8a YAML ikizi okunabildi", False, "is akisi okunamadi: %s" % e,
             m_bagimli=False)
    else:
        ayrisma = ikiz_ayrismasi(yaml_metni, ZORUNLU_ALANLAR)
        ekle("8a YAML ikizi TEK KAYNAKLA birebir", not ayrisma,
             "KIMLIK_BAYRAK kumesi `KIMLIK_ALANLARI` ile AYRISTI -> %s" % ayrisma,
             m_bagimli=False)
        bayrak_kume = yaml_bayrak_alanlari(yaml_metni) or []
        ekle("8b emekli alan bayrakta DEGIL",
             "GOOGLE_ADS_DEVELOPER_TOKEN" not in bayrak_kume,
             "developer token (9 Eyl 2026'da EMEKLI, artik URETILEMEZ) hala "
             "KIMLIK_BAYRAK'ta -> ifade ASLA 'VAR' olamaz, hat OLU kalir",
             m_bagimli=False)
        ekle("8c ayristirici FIILEN alan buluyor (pozitif kontrol)",
             len(bayrak_kume) == len(set(ZORUNLU_ALANLAR)) and len(bayrak_kume) > 0,
             "bayraktan %d alan ayristirildi (beklenen %d) — 0 ise ikiz kolu KOR, "
             "'ayrisma yok' YESILI sahtedir"
             % (len(bayrak_kume), len(set(ZORUNLU_ALANLAR))),
             m_bagimli=False)

    return sonuc


# ══════════════════════════════════════════════════════════════════════════════
# MUTANTLAR — izole kopyada. Her biri EN AZ BIR vakayi oldurmeli.
# ══════════════════════════════════════════════════════════════════════════════
MUTANTLAR = [
    ("M1 zarar esigi gevsetildi (> -> >=)",
     "    if bekleyen > 0:",
     "    if bekleyen >= 0:"),
    ("M2 zarar kolu yesile cevrildi",
     "        return EYLEM_ZARAR, RC_KIRMIZI",
     "        return EYLEM_BEKLE, RC_YESIL"),
    ("M3 zarar esigi komple KALDIRILDI",
     "    if bekleyen > 0:\n        # 🔴 ZARAR ESIGI",
     "    if False:\n        # 🔴 ZARAR ESIGI"),
    ("M4 kimlik kolu ters cevrildi",
     "    if kimlik_tam:\n        return EYLEM_YUKLE, RC_YESIL",
     "    if not kimlik_tam:\n        return EYLEM_YUKLE, RC_YESIL"),
    ("M5 OLCULEMEDI yesile dusuruldu",
     "    if bekleyen is None:\n        return EYLEM_OLCULEMEDI, RC_OLCULEMEDI",
     "    if bekleyen is None:\n        return EYLEM_BEKLE, RC_YESIL"),
    ("M6 bayrak capraz kolu susturuldu",
     "    if b != beklenen:",
     "    if False and b != beklenen:"),
    ("M7 yukleme rc'si yutuldu",
     "        rc, yukleme_metni = yukle_kolu()",
     "        _rc_atildi, yukleme_metni = yukle_kolu()"),
]


# ══════════════════════════════════════════════════════════════════════════════
# KAYNAK / IKIZ MUTANTLARI — yeni iddialarin GERCEKTEN oldurdugunu olcer
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 Yukaridaki MUTANTLAR yalniz `reklam-oci-kosucu.py` govdesini mutasyona ugratir;
# 8a/8b/8c iddialari ise KAYNAK ile YAML ekseninde yasar ve o mutantlarin HICBIRI
# onlara dokunmaz. Olculmeseydi yeni iddialar KAPSAM YANILSAMASI olurdu: "bu satiri
# silsem hangi iddia kirmizi yanar?" sorusunun cevabi YOK demekti.
#
# CANLI DOSYAYA YAZMA YOK: yukleyici IZOLE bir kopyaya yazilir, YAML yalniz BELLEKTE
# degistirilir. Silinecek gercek ev yolu YOKTUR ([[mutant-canli-govdede-yasamaz]]).
_MK1_CAPA = 'KIMLIK_ALANLARI = (\n    ("GOOGLE_ADS_CLIENT_ID"'
_MK1_YERINE = ('KIMLIK_ALANLARI = (\n'
               '    ("GOOGLE_ADS_DEVELOPER_TOKEN", "developer token"),\n'
               '    ("GOOGLE_ADS_CLIENT_ID"')
_MK2_CAPA = "&& secrets.GOOGLE_ADS_CLIENT_SECRET != ''\n"


def kaynak_mutant_kolu(dizin):
    """Doner: (olen_sayisi, sagkalan_listesi, toplam_vaka)."""
    olen, sagkalan, toplam = 0, [], 0
    try:
        yaml_metni = open(AKIS, encoding="utf-8").read()
        kaynak = open(YUKLEYICI, encoding="utf-8").read()
    except OSError as e:                              # noqa: BLE001
        return 0, ["KAYNAK/YAML OKUNAMADI: %s (OLCULEMEDI — YESIL DEGIL)" % e], 0

    # ── MK1: emekli alan `KIMLIK_ALANLARI`na GERI ALINDI (izole kopya) ──────
    toplam += 1
    ad = "MK1 emekli alan KIMLIK_ALANLARI'na geri alindi"
    if _MK1_CAPA not in kaynak:
        sagkalan.append(ad + " — CAPA TUTMADI (kaynak degisti, mutant hedefini bulamadi)")
    else:
        yol = os.path.join(dizin, "mutant_yukleyici.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(_MK1_CAPA, _MK1_YERINE, 1))
        try:
            MY = modul_yukle(yol, "reklam_oci_yukleyici_mk1")
            mutant_zorunlu = list(MY.ZORUNLU_ALAN_ADLARI)
        except Exception as e:                        # noqa: BLE001
            print("  ☠️  %-52s (mutant yuklenemedi: %s)" % (ad, e))
            olen += 1
        else:
            tuttu = "GOOGLE_ADS_DEVELOPER_TOKEN" in mutant_zorunlu
            ayrisma = ikiz_ayrismasi(yaml_metni, mutant_zorunlu)
            if tuttu and ayrisma:
                print("  ☠️  %-52s (ikiz vakasi KIRMIZI: %s)" % (ad, ayrisma))
                olen += 1
            elif not tuttu:
                sagkalan.append(ad + " — MUTASYON TUTMADI (alan zorunlu kumeye girmedi)")
            else:
                sagkalan.append(ad + " — IKIZ VAKASI YESIL KALDI (8a KOR)")

    # ── MK2: YAML bayragindan BASKA bir alan silindi ────────────────────────
    toplam += 1
    ad = "MK2 YAML KIMLIK_BAYRAK'tan CLIENT_SECRET silindi"
    if _MK2_CAPA not in yaml_metni:
        sagkalan.append(ad + " — CAPA TUTMADI (is akisi degisti)")
    else:
        mutant_yaml = yaml_metni.replace(_MK2_CAPA, "", 1)
        ayrisma = ikiz_ayrismasi(mutant_yaml, ZORUNLU_ALANLAR)
        if ayrisma:
            print("  ☠️  %-52s (ikiz vakasi KIRMIZI: %s)" % (ad, ayrisma))
            olen += 1
        else:
            sagkalan.append(ad + " — IKIZ VAKASI YESIL KALDI (8a KOR)")

    # ── K0 KONTROL: ILGISIZ degisiklik ikizi KIRMIZI YAKMAMALI ──────────────
    # 🔴 Menzil kontrolu: ayristirici TUM dosyayi tarasaydi (yanlis eksen), asagidaki
    # YORUM satiri kumeyi kirletir ve kapi ILGISIZ bir degisiklikte kirmizi yanardi.
    toplam += 1
    kirli = yaml_metni.replace(
        "        env:\n",
        "        # ornek yorum: secrets.GOOGLE_ADS_ILGISIZ_ALAN != '' yazilabilir\n"
        "        env:\n", 1)
    if kirli == yaml_metni:
        sagkalan.append("K0 KONTROL — capa tutmadi (env: bloku bulunamadi)")
    elif ikiz_ayrismasi(kirli, ZORUNLU_ALANLAR):
        sagkalan.append("K0 KONTROL — ILGISIZ yorum satiri ikizi KIRMIZI yakti "
                        "(ayristirici menzili COK GENIS)")
    else:
        print("  ✅  %-52s (dar eksen: komsuyu kirmiziya yakmaz)"
              % "K0 KONTROL ilgisiz yorum satiri eklendi")
        olen += 1
    return olen, sagkalan, toplam


def mutant_kolu(govde, dizin):
    """Mutantlari IZOLE dizinde kos. CANLI dosyaya HICBIR yazma YOK."""
    olen, sagkalan = 0, []
    for i, (ad, eski, yeni) in enumerate(MUTANTLAR):
        if eski not in govde:
            sagkalan.append("%s — CAPA TUTMADI (kaynak degisti, mutant hedefini "
                            "bulamadi)" % ad)
            continue
        yol = os.path.join(dizin, "mutant_%02d.py" % i)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(govde.replace(eski, yeni, 1))
        try:
            M = modul_yukle(yol, "reklam_oci_kosucu_mutant_%02d" % i)
        except Exception as e:                    # noqa: BLE001
            # Cokme de OLUM sayilir: bozulmus govde kabul bataryasini GECEMEZ.
            print("  ☠️  %-44s (mutant yuklenemedi: %s)" % (ad, e))
            olen += 1
            continue
        try:
            # 🔴 YALNIZ MODULE BAGLI vakalar oldurme hesabina girer (v[3]) —
            # kaynak/YAML ekseni her mutantta ayni yanar, girseydi SAGKALANI
            # maskelerdi.
            dusen = [v for v in batarya(M) if not v[1] and v[3]]
        except Exception as e:                    # noqa: BLE001
            print("  ☠️  %-44s (batarya istisna atti: %s)" % (ad, e))
            olen += 1
            continue
        if dusen:
            print("  ☠️  %-44s (olduren vaka: %s)" % (ad, dusen[0][0]))
            olen += 1
        else:
            sagkalan.append("%s — HICBIR VAKA KIRMIZI YANMADI" % ad)
    return olen, sagkalan


# ══════════════════════════════════════════════════════════════════════════════
def akis_kablolamasi():
    """Is akisi FIILEN bu aracı cagiriyor mu. Kablolanmamis karar OLU karardir."""
    if not os.path.exists(AKIS):
        return False, "is akisi YOK: %s" % AKIS
    m = open(AKIS, encoding="utf-8").read()
    eksik = [j for j in ("tools/reklam-oci-yukleyici.py --kuyrukla",
                         "tools/reklam-oci-kosucu.py",
                         "tools/reklam-oci-kosucu-test.py",
                         "schedule:", "workflow_dispatch:") if j not in m]
    if eksik:
        return False, "is akisinda eksik: %s" % ", ".join(eksik)
    return True, "is akisi uc adimi da cagiriyor (kuyrukla + kosucu + kabul)"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mutant", action="store_true", help="yalniz mutant kolunu kos")
    a = ap.parse_args(argv)

    govde = open(KOSUCU, encoding="utf-8").read()
    rc = 0

    if not a.mutant:
        print("REKLAM OCI KOSUCU — KABUL BATARYASI")
        M = modul_yukle(KOSUCU, "reklam_oci_kosucu_gercek")
        vakalar = batarya(M)
        dusen = [v for v in vakalar if not v[1]]
        for ad, gecti, mesaj, _m_bagimli in vakalar:
            if not gecti:
                print("  ❌ %-28s %s" % (ad, mesaj))
        print("  VAKA=%d GECEN=%d DUSEN=%d"
              % (len(vakalar), len(vakalar) - len(dusen), len(dusen)))
        if dusen:
            rc = 1

        tamam, mesaj = akis_kablolamasi()
        print("  KABLOLAMA: %s — %s" % ("✅" if tamam else "❌", mesaj))
        if not tamam:
            rc = 1

    print("MUTANT KOLU (izole kopya — canli govde DEGISMEZ)")
    with tempfile.TemporaryDirectory(prefix="oci-kosucu-mutant-") as d:
        olen, sagkalan = mutant_kolu(govde, d)
        print("  KAYNAK/IKIZ MUTANTLARI (tek kaynak + YAML ekseni)")
        k_olen, k_sagkalan, k_toplam = kaynak_mutant_kolu(d)
    sagkalan = list(sagkalan) + list(k_sagkalan)
    for s in sagkalan:
        print("  🔴 SAGKALAN: %s" % s)
    print("  MUTANT=%d OLEN=%d SURVIVOR=%d"
          % (len(MUTANTLAR) + k_toplam, olen + k_olen, len(sagkalan)))
    if sagkalan:
        rc = 1

    print("-" * 70)
    print("SONUC: %s" % ("YESIL ✅" if rc == 0 else "KIRMIZI 🔴"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
