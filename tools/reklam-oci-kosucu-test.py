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

BATARYA (dort zorunlu vaka + ek eksenler):
  1. bekleyen=0, kimlik YOK   -> rc 0 · EYLEM=BEKLE · birebir `HAL=KIMLIK-BEKLIYOR BEKLEYEN=0`
  2. bekleyen=3, kimlik YOK   -> rc 1 · EYLEM=ZARAR · yukleme CAGRILMAZ
  3. bekleyen=3, kimlik VAR   -> yukleme DENENIR (kol tam 1 kez cagrilir)
  4. durum OLCULEMEDI (None)  -> rc 3 · EYLEM=OLCULEMEDI · yukleme CAGRILMAZ
  5. durum kolu PATLAR        -> rc 3 (istisna yesile dusmez)
  6. kimlik VAR + yukleme rc=1-> rc 1 (yukleme kirmizisi YUTULMAZ)
  7. bayrak AYRISMASI         -> rc 3 (ikiz tanim sessiz kalamaz)
  8. YAML ikizi == TEK KAYNAK (kaynak ekseni)
  9. EL SIKISMA — `kos()` entegrasyonu (KIRMIZI/OLCULEMEDI yuklemeyi DURDURUR,
     kablolanmamis kol FAIL-CLOSED, kimlik yokken kol HIC CAGRILMAZ)
 10. EL SIKISMA — `reklam-oci-yukleyici.py::el_sikisma` GOVDESI, SAHTE TASIYICIYLA:
     200-beklenen · 403 · bulunamadi · zaman asimi · OAuth kirmizisi/olculemedisi ·
     tip-durum uyumsuzlugu · YAN ETKI YASAGI · `gizle()` maskelemesi

🔴 EL SIKISMA KOLU AG'A CIKMAZ: sahte tasiyici aletin KENDI dikis yerine takilir
(`HttpTasiyici` yerine gecer) ve `el_sikisma()` TAM YOLU gercek kodla kosar. Sahte
tasiyici TESTIN kendi kopyasi olsaydi alet KOR kalirdi
([[kabul-teslim-edilmeyen-iskeleyle-saglanirsa-alet-kor-kalir]]).

MUTANT (izole kopyada; CANLI govde DEGISMEZ — [[mutant-canli-govdede-yasamaz]]):
  her mutant EN AZ BIR vakayi KIRMIZI yakmalidir. `SURVIVOR=0` basilmazsa kabul DUSER.
  🔴 Hangi vakanin oldurdugu CIVILENMEZ — beklenen-kirmizi kumesi taban degisince
  ikinci kat bayatlar ([[mutant-beklenen-kirmizi-kumesi-taban-degisince-ikinci-kat-bayatlar]]).
  🔴 UC AYRI EKSEN, UC AYRI OLDURME HESABI (`eksen` alani): "M" kosucu govdesi ·
  "Y" yukleyici govdesi (el sikisma) · "-" kaynak/YAML. Tek hesapta toplansalardi
  bir eksende KIRMIZI yanan vaka oteki eksenin SAGKALANINI MASKELERDI
  ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).

Kullanim:
  python3 tools/reklam-oci-kosucu-test.py              # batarya + mutant (CI kolu)
  python3 tools/reklam-oci-kosucu-test.py --mutant     # yalniz mutant kolu
"""

import argparse
import importlib.util
import json
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
Y_GERCEK = modul_yukle(YUKLEYICI, "reklam_oci_yukleyici_kabul")
ZORUNLU_ALANLAR = list(Y_GERCEK.ZORUNLU_ALAN_ADLARI)


# ══════════════════════════════════════════════════════════════════════════════
# SAHTE KIMLIK — GERCEK DEGIL. Hicbir yere gitmez (tasiyici de sahtedir).
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 Bu degerler SIR SINIFININ TAKLIDIDIR: `gizle()` vakasi (10i) bunlardan birini
# sahte 403 govdesine KOYAR ve ciktida GORUNMEMESINI olcer. Maskeleme iddiasi,
# maskelenecek bir deger OLMADAN sinanamazdi.
DONUSUM_ID = "987654321"
SAHTE_KIMLIK = {
    "GOOGLE_ADS_CLIENT_ID": "SAHTE-ISTEMCI.apps.googleusercontent.com",
    "GOOGLE_ADS_CLIENT_SECRET": "SAHTE-ISTEMCI-SIRRI",
    "GOOGLE_ADS_REFRESH_TOKEN": "SAHTE-YENILEME-JETONU-1e9c",
    # Tireli yazilir: `musteri_id` turevinin tireleri DUSURDUGU de olculur.
    "GOOGLE_ADS_CUSTOMER_ID": "123-456-7890",
    "GOOGLE_ADS_CONVERSION_ACTION_ID": DONUSUM_ID,
}


def sahte_kimlik(Y):
    return Y.Kimlik(dict(SAHTE_KIMLIK))


def arama_govdesi(kimlik_id=DONUSUM_ID, durum="ENABLED", tip="UPLOAD_CLICKS"):
    """Google `googleAds:search` yanitinin TAKLIDI — alanlar camelCase, id DIZGE."""
    return json.dumps({
        "results": [{"conversionAction": {
            "resourceName": "customers/1234567890/conversionActions/%s" % kimlik_id,
            "id": str(kimlik_id), "status": durum, "type": tip}}],
        "fieldMask": ("conversionAction.id,conversionAction.status,"
                      "conversionAction.type")})


class SahteTasiyici(object):
    """Google ucunun SAHTESI — yukleyicinin KENDI `HttpTasiyici` dikisine takilir.

    HER istegi (url, govde, basliklar) SAKLAR: "yan etki yasagi" iddiasi ancak
    gonderilen istekleri SAYARAK olculebilir, niyet beyaniyla DEGIL.
    """

    def __init__(self, oauth=(200, '{"access_token": "SAHTE-ERISIM-JETONU"}'),
                 arama=None):
        self.oauth = oauth
        self.arama = arama if arama is not None else (200, arama_govdesi())
        self.istekler = []

    @property
    def urller(self):
        return [u for u, _g, _b in self.istekler]

    def istek(self, url, govde, basliklar, bicim="json"):
        self.istekler.append((url, govde, dict(basliklar or {})))
        if "oauth2" in url:
            return self.oauth
        if "googleAds:search" in url:
            return self.arama
        # 🔴 BEKLENMEYEN UC: sahte uc bunu TAKLIT ETMEZ. `uploadClickConversions`
        # buraya duser ve 404 doner — yani el sikisma kolu yukleme ucuna saparsa
        # vaka KIRMIZI yanar, sessizce "calisiyor" gorunmez.
        return 404, '{"error": {"message": "SAHTE UC: beklenmeyen yol"}}'


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


def el_sabit(rc=0, satirlar=None):
    """Sabit donusu olan el sikisma kolu + CAGRILMA SAYACI.

    🔴 Sayac sart: "el sikisma atlandi mi" sorusu rc ile ayirt EDILEMEZ (atlanan kol
    da, yesil donen kol da kosumun rc'sini 0 birakir).
    """
    kayit = {"n": 0}
    varsayilan = ["HAL=EL-SIKISMA-TAMAM — (sahte kol)"]

    def _kol():
        kayit["n"] += 1
        return rc, list(satirlar if satirlar is not None else varsayilan)
    return _kol, kayit


def el_kolu_govdeli(Y, tasiyici):
    """GERCEK `el_sikisma()` govdesini sahte tasiyiciyla kosan kol + sayac."""
    kayit = {"n": 0}

    def _kol():
        kayit["n"] += 1
        return Y.el_sikisma(sahte_kimlik(Y), tasiyici)
    return _kol, kayit


# ══════════════════════════════════════════════════════════════════════════════
# BATARYA — her vaka (ad, gecti_mi, mesaj) doner. M = olculen modul (gercek|mutant)
# ══════════════════════════════════════════════════════════════════════════════
def batarya(M, Y=None):
    """M = olculen KOSUCU modulu · Y = olculen YUKLEYICI modulu (el sikisma govdesi)."""
    Y = Y_GERCEK if Y is None else Y
    sonuc = []

    def ekle(ad, kosul, mesaj, eksen="M"):
        """`eksen` vakanin HANGI GOVDEYE bagli oldugunu soyler: "M" kosucu · "Y"
        yukleyici (el sikisma) · "-" kaynak/YAML (olculen modulden BAGIMSIZ).

        🔴 Bu alan bir MASKELEMEYI onler: kendi ekseni disindaki bir vaka HER
        mutantta ayni sekilde yanar (ya da yanmaz) ve hepsi "oldu" gorunurdu ->
        gercek SAGKALAN gizlenirdi ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
        Mutant kollari yalniz KENDI eksenlerini oldurme hesabina katar; gercek
        bataryada ise UC eksen de tam yetkiyle sayilir ve kirmizi yakar.
        """
        sonuc.append((ad, bool(kosul), mesaj, eksen))

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

    # ── 3. bekleyen=3, kimlik VAR + el sikisma YESIL -> yukleme DENENIR ─────
    yk, say = yukle_sayaci(rc=0)
    el, el_say = el_sabit(rc=0)
    rc, satir, eylem = M.kos(durum_sabit(3), kimlik_sabit(True), yk,
                             el_sikisma_kolu=el)
    ekle("3a yukleme denendi", say["n"] == 1,
         "kimlik varken yukleme %d kez cagrildi (beklenen 1)" % say["n"])
    ekle("3b eylem", eylem == M.EYLEM_YUKLE, "eylem=%s (beklenen YUKLE)" % eylem)
    ekle("3c rc", rc == 0, "basarili yuklemede rc=%d (beklenen 0)" % rc)
    ekle("3d el sikisma KOSTU", el_say["n"] == 1,
         "kimlik varken el sikisma %d kez cagrildi (beklenen 1)" % el_say["n"])
    ekle("3e el sikisma satiri ozette", "HAL=EL-SIKISMA-TAMAM" in "\n".join(satir),
         "yesil el sikisma satiri ozete GIRMIYOR (kanit kaybolur)")

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
    el, _el_say = el_sabit(rc=0)
    rc, satir, eylem = M.kos(durum_sabit(2), kimlik_sabit(True), yk,
                             el_sikisma_kolu=el)
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
             eksen="-")
    else:
        ayrisma = ikiz_ayrismasi(yaml_metni, ZORUNLU_ALANLAR)
        ekle("8a YAML ikizi TEK KAYNAKLA birebir", not ayrisma,
             "KIMLIK_BAYRAK kumesi `KIMLIK_ALANLARI` ile AYRISTI -> %s" % ayrisma,
             eksen="-")
        bayrak_kume = yaml_bayrak_alanlari(yaml_metni) or []
        ekle("8b emekli alan bayrakta DEGIL",
             "GOOGLE_ADS_DEVELOPER_TOKEN" not in bayrak_kume,
             "developer token (9 Eyl 2026'da EMEKLI, artik URETILEMEZ) hala "
             "KIMLIK_BAYRAK'ta -> ifade ASLA 'VAR' olamaz, hat OLU kalir",
             eksen="-")
        ekle("8c ayristirici FIILEN alan buluyor (pozitif kontrol)",
             len(bayrak_kume) == len(set(ZORUNLU_ALANLAR)) and len(bayrak_kume) > 0,
             "bayraktan %d alan ayristirildi (beklenen %d) — 0 ise ikiz kolu KOR, "
             "'ayrisma yok' YESILI sahtedir"
             % (len(bayrak_kume), len(set(ZORUNLU_ALANLAR))),
             eksen="-")

    # ── 9. EL SIKISMA — `kos()` ENTEGRASYONU (kosucu ekseni) ────────────────
    # 🔴 Kapatilan bosluk: 22 Eyl run 35776509904 `HAL=YESIL` bastı ama `istek=0`
    # idi — kimlik KURULU, gercek uca TEK ISTEK BILE CIKMAMIS. Kosum yesildi, "kimlik
    # calisiyor mu" sorusu OLCULMEMISTI.
    yk, say = yukle_sayaci()
    el, el_say = el_sabit(rc=1, satirlar=["HAL=KIRMIZI — EL SIKISMA DUSTU (sahte)"])
    rc, satir, eylem = M.kos(durum_sabit(5), kimlik_sabit(True), yk,
                             el_sikisma_kolu=el)
    ekle("9a el sikisma KIRMIZI -> rc", rc == 1,
         "el sikisma rc=1 iken kosucu rc=%d (beklenen 1)" % rc)
    ekle("9b el sikisma KIRMIZI -> eylem", eylem == M.EYLEM_EL_SIKISMA,
         "eylem=%s (beklenen EL-SIKISMA)" % eylem)
    ekle("9c el sikisma KIRMIZI -> YUKLEME YOK", say["n"] == 0,
         "el sikisma dusmusken yukleme %d kez cagrildi (beklenen 0) — YAN ETKI"
         % say["n"])

    yk, say = yukle_sayaci()
    el, el_say = el_sabit(rc=3, satirlar=["HAL=OLCULEMEDI — EL SIKISMA (sahte)"])
    rc, satir, eylem = M.kos(durum_sabit(5), kimlik_sabit(True), yk,
                             el_sikisma_kolu=el)
    ekle("9d el sikisma OLCULEMEDI -> rc", rc == 3,
         "el sikisma rc=3 iken kosucu rc=%d (beklenen 3 — YESIL DEGIL)" % rc)
    ekle("9e el sikisma OLCULEMEDI -> YUKLEME YOK", say["n"] == 0,
         "olculemedi kolunda yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # 🔴 KABLOLANMAMIS KOL FAIL-CLOSED: "adim yoksa gecmis say" yolu bu aracin var
    # olma sebebine AYKIRIDIR — kosmayan bir adim YESIL GORUNUR.
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(5), kimlik_sabit(True), yk)
    ekle("9f kablolanmamis kol -> rc", rc == 3,
         "el sikisma kolu YOKken kosucu rc=%d (beklenen 3 fail-closed)" % rc)
    ekle("9g kablolanmamis kol -> YUKLEME YOK", say["n"] == 0,
         "kablolanmamis kolda yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # 🔴 POZITIF KONTROL (kosucu ekseni): kimlik EKSIKken el sikisma ATLANIR ve
    # `KIMLIK-BEKLIYOR` bacagi AYNEN korunur. Esigin ONUNE konsaydi burasi kirmizi
    # yanardi ([[onarim-kolu-zarar-esiginin-arkasinda]]).
    yk, say = yukle_sayaci()
    el, el_say = el_sabit(rc=1, satirlar=["HAL=KIRMIZI — cagrilmamaliydi"])
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk,
                             el_sikisma_kolu=el)
    metin = "\n".join(satir)
    ekle("9h kimlik YOK -> el sikisma ATLANDI", el_say["n"] == 0,
         "kimlik yokken el sikisma %d kez cagrildi (beklenen 0)" % el_say["n"])
    ekle("9i kimlik YOK -> BEKLE kolu KORUNDU",
         rc == 0 and eylem == M.EYLEM_BEKLE
         and "HAL=KIMLIK-BEKLIYOR BEKLEYEN=0" in metin,
         "rc=%d eylem=%s (beklenen 0/BEKLE + birebir KIMLIK-BEKLIYOR satiri)"
         % (rc, eylem))

    # ── 9j/9k KIP SECIMI — `--kuru` disinda GERCEK kol secilir ──────────────
    # 🔴 AG'A CIKILMAZ: kimlik alanlari ortamdan GECICI olarak silinir, boylece
    # `gercek_el_sikisma_kolu` daha tasiyiciya DOKUNMADAN fail-closed doner. Bu
    # silme olmasaydi ve biri kimlik env'ini kabul adimina eklerse test GERCEK bir
    # istek atardi — kabul testi uretim ucuna DOKUNAMAZ.
    yedek = {}
    try:
        for _ad in ZORUNLU_ALANLAR:
            if _ad in os.environ:
                yedek[_ad] = os.environ.pop(_ad)
        kuru_rc, kuru_sat = M.secili_el_sikisma_kolu(Y, kuru=True)()
        gercek_rc, _gs = M.secili_el_sikisma_kolu(Y, kuru=False)()
    finally:
        os.environ.update(yedek)
    ekle("9j `--kuru` kolu ATLAR (ag YOK)",
         kuru_rc == 0 and "ATLANDI" in "\n".join(kuru_sat),
         "kuru kol rc=%d satirlar=%s (beklenen 0 + ATLANDI)" % (kuru_rc, kuru_sat))
    ekle("9k `--kuru` DISINDA GERCEK kol secildi",
         gercek_rc == 3,
         "kuru OLMAYAN kol kimliksiz ortamda rc=%d dondu (beklenen 3) — kip secimi "
         "TERS baglanmis olabilir, o zaman CI el sikismayi SESSIZCE atlar"
         % gercek_rc)

    # ── 10. EL SIKISMA GOVDESI — SAHTE TASIYICI, DORT KOL + YAN ETKI + MASKE ─
    # 🔴 Dikis yeri KAYNAK DOSYADA: sahte tasiyici `el_sikisma()`ya ENJEKTE edilir ve
    # TAM YOL gercek kodla kosar.
    kml = sahte_kimlik(Y)

    # (a) 200 + BEKLENEN KAYIT -> YESIL
    t = SahteTasiyici()
    rc_e, sat_e = Y.el_sikisma(kml, t)
    m_e = "\n".join(sat_e)
    ekle("10a 200-beklenen rc", rc_e == 0,
         "200 + beklenen kayit -> rc=%d (beklenen 0)" % rc_e, eksen="Y")
    ekle("10b 200-beklenen HAL jetonu", "HAL=EL-SIKISMA-TAMAM" in m_e,
         "yesil kolda `HAL=EL-SIKISMA-TAMAM` BASILMIYOR", eksen="Y")
    ekle("10c iki istek: OAuth + arama",
         len(t.istekler) == 2 and "oauth2" in t.urller[0]
         and "googleAds:search" in t.urller[1],
         "cikan istekler=%s (beklenen OAuth + googleAds:search)" % t.urller,
         eksen="Y")
    ekle("10d sorgu DONUSUM KIMLIGINI tasiyor",
         DONUSUM_ID in str(t.istekler[1][1].get("query", "")) if len(t.istekler) > 1
         else False,
         "arama govdesi donusum eylemi kimligini TASIMIYOR: %s"
         % (t.istekler[1][1] if len(t.istekler) > 1 else None), eksen="Y")
    ekle("10e arama ucu MUSTERI KIMLIGINI tireSIZ tasiyor",
         "customers/1234567890/googleAds:search" in (t.urller[1] if len(t.urller) > 1
                                                     else ""),
         "arama ucu=%s (beklenen customers/1234567890/googleAds:search)"
         % (t.urller[1] if len(t.urller) > 1 else None), eksen="Y")

    # (b) 403 -> KIRMIZI (erisim duzeyi / hesap yetkisi)
    t403 = SahteTasiyici(arama=(403, json.dumps(
        {"error": {"code": 403, "status": "PERMISSION_DENIED",
                   "message": "The caller does not have permission"}})))
    rc_403, sat_403 = Y.el_sikisma(kml, t403)
    ekle("10f 403 -> KIRMIZI", rc_403 == 1,
         "403 -> rc=%d (beklenen 1)" % rc_403, eksen="Y")
    ekle("10g 403 HAL jetonu", "HAL=KIRMIZI" in "\n".join(sat_403),
         "403 kolunda HAL=KIRMIZI BASILMIYOR", eksen="Y")

    # (c) 200 ama DONUSUM EYLEMI BULUNAMADI -> KIRMIZI
    tbul = SahteTasiyici(arama=(200, json.dumps({"fieldMask": "conversionAction.id"})))
    rc_bul, sat_bul = Y.el_sikisma(kml, tbul)
    ekle("10h bulunamadi -> KIRMIZI", rc_bul == 1,
         "bos `results` -> rc=%d (beklenen 1)" % rc_bul, eksen="Y")
    ekle("10i bulunamadi metni kimligi ADIYLA basiyor",
         DONUSUM_ID in "\n".join(sat_bul),
         "bulunamadi metni donusum eylemi kimligini BASMIYOR", eksen="Y")

    # (d) ZAMAN ASIMI / AG -> OLCULEMEDI (YESIL DEGIL, KIRMIZI DA DEGIL)
    tag = SahteTasiyici(arama=(0, "AG HATASI: <urlopen error timed out>"))
    rc_ag, sat_ag = Y.el_sikisma(kml, tag)
    ekle("10j zaman asimi -> OLCULEMEDI", rc_ag == 3,
         "ag/zaman asimi -> rc=%d (beklenen 3)" % rc_ag, eksen="Y")
    ekle("10k zaman asimi HAL jetonu", "HAL=OLCULEMEDI" in "\n".join(sat_ag),
         "zaman asimi kolunda HAL=OLCULEMEDI BASILMIYOR", eksen="Y")

    # (e) OAuth KIRMIZISI (invalid_grant) — arama DENENMEZ
    toa = SahteTasiyici(oauth=(400, json.dumps(
        {"error": "invalid_grant", "error_description": "Token has been expired"})))
    rc_oa, sat_oa = Y.el_sikisma(kml, toa)
    ekle("10l OAuth 400 -> KIRMIZI", rc_oa == 1,
         "OAuth 400 -> rc=%d (beklenen 1)" % rc_oa, eksen="Y")
    ekle("10m OAuth dusunce arama DENENMEZ", len(toa.istekler) == 1,
         "OAuth dustugu halde %d istek cikti (beklenen 1)" % len(toa.istekler),
         eksen="Y")

    # (f) OAuth AG ARIZASI -> OLCULEMEDI (kod ekseni hata metninden AYIRT EDILEMEZDI)
    toag = SahteTasiyici(oauth=(0, "AG HATASI: name resolution failed"))
    rc_oag, _s = Y.el_sikisma(kml, toag)
    ekle("10n OAuth ag arizasi -> OLCULEMEDI", rc_oag == 3,
         "OAuth ag arizasi -> rc=%d (beklenen 3, KIRMIZI DEGIL)" % rc_oag, eksen="Y")

    # (g) TIP / DURUM YUKLEMEYE UYGUN DEGIL -> KIRMIZI
    ttip = SahteTasiyici(arama=(200, arama_govdesi(durum="REMOVED", tip="WEBPAGE")))
    rc_tip, sat_tip = Y.el_sikisma(kml, ttip)
    m_tip = "\n".join(sat_tip)
    ekle("10o tip/durum uyumsuz -> KIRMIZI", rc_tip == 1,
         "status=REMOVED type=WEBPAGE -> rc=%d (beklenen 1)" % rc_tip, eksen="Y")
    ekle("10p uyumsuzluk ADIYLA basildi",
         "UPLOAD_CLICKS" in m_tip and "ENABLED" in m_tip,
         "uyumsuzluk metni beklenen tip/durumu ADIYLA BASMIYOR", eksen="Y")

    # (h) 🔴🔴 YAN ETKI YASAGI — hicbir kolda `uploadClickConversions` CAGRILMAZ
    tum_urller = (t.urller + t403.urller + tbul.urller + tag.urller
                  + toa.urller + toag.urller + ttip.urller)
    tum_govdeler = [g for kol in (t, t403, tbul, tag, toa, toag, ttip)
                    for _u, g, _b in kol.istekler]
    ekle("10q YAN ETKI YOK: uploadClickConversions CAGRILMADI",
         not any("uploadClickConversions" in u for u in tum_urller),
         "el sikisma kolu YUKLEME UCUNA CIKTI: %s"
         % [u for u in tum_urller if "uploadClickConversions" in u], eksen="Y")
    ekle("10r YAN ETKI YOK: hicbir govdede `conversions` YOK",
         not any(isinstance(g, dict) and "conversions" in g for g in tum_govdeler),
         "el sikisma govdesinde donusum YUKU var — SALT OKUMA IHLALI", eksen="Y")
    ekle("10s YAN ETKI YOK: `validateOnly` ile bile denenmedi",
         not any(isinstance(g, dict) and "validateOnly" in g for g in tum_govdeler),
         "`validateOnly` gonderildi — yan etkisiz kol yazma ucuna DOKUNAMAZ",
         eksen="Y")

    # (i) 🔴 MASKELEME — hata govdesi SIRRI yankilarsa cikti onu TASIYAMAZ
    sir = SAHTE_KIMLIK["GOOGLE_ADS_REFRESH_TOKEN"]
    tsir = SahteTasiyici(arama=(403, json.dumps(
        {"error": {"message": "invalid token %s rejected" % sir}})))
    _rc_sir, sat_sir = Y.el_sikisma(kml, tsir)
    m_sir = "\n".join(sat_sir)
    ekle("10t sir ciktiya SIZMADI", sir not in m_sir,
         "403 govdesindeki refresh token ciktiya SIZDI", eksen="Y")
    ekle("10u maskeleme FIILEN calisti (pozitif kontrol)", "***" in m_sir,
         "maskelenmis deger yok — `gizle()` kolu bu yolda KOSMAMIS olabilir "
         "(iddia KOR)", eksen="Y")

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
    ("M8 el sikisma kirmizisi YUTULDU",
     "        if el_rc != RC_YESIL:",
     "        if False and el_rc != RC_YESIL:"),
    ("M9 kablolanmamis kol yesile dusuruldu",
     "            return RC_OLCULEMEDI, satirlar, EYLEM_EL_SIKISMA",
     "            return RC_YESIL, satirlar, EYLEM_EL_SIKISMA"),
    ("M10 el sikisma adimi KOMPLE KALDIRILDI",
     "        el_rc, el_satirlari = el_sikisma_kolu()",
     "        el_rc, el_satirlari = RC_YESIL, []"),
    ("M11 kip secimi TERS baglandi (CI el sikismayi atlardi)",
     "    if not kuru:\n        return gercek_el_sikisma_kolu(mod)",
     "    if kuru:\n        return gercek_el_sikisma_kolu(mod)"),
]


# ══════════════════════════════════════════════════════════════════════════════
# YUKLEYICI MUTANTLARI — EL SIKISMA GOVDESI (`reklam-oci-yukleyici.py`)
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 Yukaridaki MUTANTLAR yalniz KOSUCU govdesini bozar; el sikismanin HUKMU
# yukleyicide yasar ve o mutantlarin HICBIRI ona dokunmaz. Olculmeseydi yeni
# iddialar KAPSAM YANILSAMASI olurdu: "bu satiri silsem hangi iddia kirmizi yanar?"
# sorusunun cevabi YOK demekti.
MUTANTLAR_Y = [
    ("MY1 403 kolu YESILE dusuruldu",
     "    if k != 200:\n        return RC_KIRMIZI, [",
     "    if k != 200:\n        return RC_YESIL, ["),
    ("MY2 zaman asimi OLCULEMEDI yerine YESIL",
     "    if gecici_kod(k):\n        return RC_OLCULEMEDI, [",
     "    if gecici_kod(k):\n        return RC_YESIL, ["),
    ("MY3 donusum eylemi bulunamadi YESILE dusuruldu",
     "    if bulunan is None:\n        return RC_KIRMIZI, [",
     "    if bulunan is None:\n        return RC_YESIL, ["),
    ("MY4 tip/durum uyumu KALDIRILDI",
     "    if kusur:\n        return RC_KIRMIZI, [",
     "    if False:\n        return RC_KIRMIZI, ["),
    ("MY5 maskeleme el sikisma yolunda susturuldu",
     "        return rc, [gizle(s, sirlar) for s in satirlar]",
     "        return rc, [s for s in satirlar]"),
    ("MY6 gecici kod kumesi bosaltildi (ag arizasi KIRMIZI sayilir)",
     "    return k == 0 or k == 429 or 500 <= k < 600",
     "    return False"),
]


def mutant_y_kolu(dizin):
    """Yukleyici (el sikisma) mutantlari + POZITIF KONTROL. IZOLE kopyada kosar.

    Doner: (olen, sagkalan, toplam). CANLI dosyaya HICBIR yazma YOK.
    """
    olen, sagkalan, toplam = 0, [], 0
    try:
        kaynak = open(YUKLEYICI, encoding="utf-8").read()
        kosucu_govde = open(KOSUCU, encoding="utf-8").read()
    except OSError as e:                              # noqa: BLE001
        return 0, ["YUKLEYICI OKUNAMADI: %s (OLCULEMEDI — YESIL DEGIL)" % e], 0

    M = modul_yukle(KOSUCU, "reklam_oci_kosucu_y_ekseni")
    _ = kosucu_govde

    for i, (ad, eski, yeni) in enumerate(MUTANTLAR_Y):
        toplam += 1
        if eski not in kaynak:
            sagkalan.append("%s — CAPA TUTMADI (kaynak degisti, mutant hedefini "
                            "bulamadi)" % ad)
            continue
        yol = os.path.join(dizin, "mutant_y_%02d.py" % i)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(eski, yeni, 1))
        try:
            MY = modul_yukle(yol, "reklam_oci_yukleyici_mutant_%02d" % i)
        except Exception as e:                        # noqa: BLE001
            print("  ☠️  %-52s (mutant yuklenemedi: %s)" % (ad, e))
            olen += 1
            continue
        try:
            dusen = [v for v in batarya(M, Y=MY) if not v[1] and v[3] == "Y"]
        except Exception as e:                        # noqa: BLE001
            print("  ☠️  %-52s (batarya istisna atti: %s)" % (ad, e))
            olen += 1
            continue
        if dusen:
            print("  ☠️  %-52s (olduren vaka: %s)" % (ad, dusen[0][0]))
            olen += 1
        else:
            sagkalan.append("%s — HICBIR VAKA KIRMIZI YANMADI" % ad)

    # ── K1 POZITIF KONTROL: el sikisma KOMPLE KIRILDI ama kimlik-yok kolu YESIL ──
    # 🔴 BU MUTANT OLDURULMEZ, YESIL KALIR. Olculen sey: el sikisma ZARAR ESIGININ
    # ARKASINDA durur. Esigin ONUNE konsaydi (ya da kimliksiz kolda da cagrilsaydi)
    # bugunku `KIMLIK-BEKLIYOR` bacagi KIRMIZI yanardi ve gurultu fail-open'i geri
    # getirirdi ([[onarim-kolu-zarar-esiginin-arkasinda]]).
    toplam += 1
    ad = "K1 KONTROL el sikisma KIRILDI, kimlik-yok kolu"
    capa = "    return RC_YESIL, [\n        \"%s — OAuth takasi OK"
    if capa not in kaynak:
        sagkalan.append(ad + " — CAPA TUTMADI (yesil kol govdesi degisti)")
    else:
        yol = os.path.join(dizin, "mutant_y_kontrol.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(capa, "    return RC_KIRMIZI, [\n        \"%s — "
                                         "OAuth takasi OK", 1))
        try:
            MY = modul_yukle(yol, "reklam_oci_yukleyici_kontrol")
        except Exception as e:                        # noqa: BLE001
            sagkalan.append(ad + " — KONTROL MODULU YUKLENEMEDI: %s" % e)
        else:
            # 🔴 MUTASYON FIILEN TUTTU MU — "yesil kalan kontrol" ancak mutant
            # GERCEKTEN bozuksa anlamlidir. Tutmadiysa kontrol KIRMIZI degil KORDUR
            # ([[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]]).
            tuttu_rc, _ts = MY.el_sikisma(sahte_kimlik(MY), SahteTasiyici())
            yk, say = yukle_sayaci()
            el, el_say = el_kolu_govdeli(MY, SahteTasiyici())
            rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk,
                                     el_sikisma_kolu=el)
            metin = "\n".join(satir)
            if tuttu_rc == 0:
                sagkalan.append(
                    ad + " — MUTASYON TUTMADI (bozulmus govde SAGLAM kolda hala "
                    "rc=0 donuyor) -> kontrol KIRMIZI DEGIL, KOR")
            elif (rc == 0 and eylem == M.EYLEM_BEKLE and el_say["n"] == 0
                    and say["n"] == 0
                    and "HAL=KIMLIK-BEKLIYOR BEKLEYEN=0" in metin):
                print("  ✅  %-52s (mutasyon TUTTU rc=%d · kimliksiz kolda el "
                      "sikisma ATLANDI, bacak korundu)" % (ad, tuttu_rc))
                olen += 1
            else:
                sagkalan.append(
                    ad + " — KIMLIK-YOK BACAGI BOZULDU: rc=%d eylem=%s "
                    "el_sikisma_cagrisi=%d yukleme_cagrisi=%d"
                    % (rc, eylem, el_say["n"], say["n"]))
    return olen, sagkalan, toplam


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
            # 🔴 YALNIZ KOSUCU EKSENI ("M") oldurme hesabina girer — yukleyici ve
            # kaynak/YAML eksenleri her mutantta ayni yanar (ya da yanmaz), girselerdi
            # SAGKALANI maskelerlerdi.
            dusen = [v for v in batarya(M) if not v[1] and v[3] == "M"]
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

    # 🔴 EL SIKISMA CI'DA ATLANAMAZ: `--kuru` kolu AG'A CIKMAZ, yani kosucuya
    # `--kuru` gecen bir is akisi el sikismayi SESSIZCE devre disi birakir ve
    # "kimlik gercekten calisiyor mu" sorusu YINE olculmemis kalir. Bu satir o
    # atlamayi bir YORUMA degil, OLCUME baglar.
    kuru = [s.strip() for s in m.splitlines()
            if "tools/reklam-oci-kosucu.py" in s and "--kuru" in s]
    if kuru:
        return False, ("is akisi kosucuya `--kuru` geciyor -> EL SIKISMA ATLANIR "
                       "(ag'a cikilmaz): %s" % kuru[0][:120])
    return True, ("is akisi uc adimi da cagiriyor (kuyrukla + kosucu + kabul) "
                  "ve kosucuya `--kuru` GECMIYOR (el sikisma CI'da KOSAR)")


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
        for ad, gecti, mesaj, _eksen in vakalar:
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
        print("  EL SIKISMA MUTANTLARI (yukleyici ekseni + POZITIF KONTROL)")
        y_olen, y_sagkalan, y_toplam = mutant_y_kolu(d)
        print("  KAYNAK/IKIZ MUTANTLARI (tek kaynak + YAML ekseni)")
        k_olen, k_sagkalan, k_toplam = kaynak_mutant_kolu(d)
    sagkalan = list(sagkalan) + list(y_sagkalan) + list(k_sagkalan)
    for s in sagkalan:
        print("  🔴 SAGKALAN: %s" % s)
    print("  MUTANT=%d OLEN=%d SURVIVOR=%d"
          % (len(MUTANTLAR) + y_toplam + k_toplam, olen + y_olen + k_olen,
             len(sagkalan)))
    if sagkalan:
        rc = 1

    print("-" * 70)
    print("SONUC: %s" % ("YESIL ✅" if rc == 0 else "KIRMIZI 🔴"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
