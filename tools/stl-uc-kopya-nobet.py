#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stl-uc-kopya-nobet.py — "her STL'in kopyasi hem Drive'da hem R2'de" kuralini OLCEN nobetci.

NEDEN VAR (13-14 Agu 2026 olcumu). Kural Okan tarafindan YAZILIYDI ama OLCEN kimse yoktu:
13 Agu kapanisinda `SADECE_DRIVE=9` (hepsi 113 baytlik hasat stub'i, zararsiz) idi;
14 Agu sabahi ayni sayi **183**'e cikmisti. Aradaki ~174 gercek uretim dosyasi Drive'a
yedeklendi ama R2'ye HIC gitmedi ve bunu kimse gormedi — cunku kurali sayiyla basan bir
kapi yoktu. Bu dosya o bosluktur ([[tekil-yama-sinifi-kapatmaz]] degil, SINIF kapisi:
sapmanin BUYUMESINI olcer, tek tek dosyayi degil).

DORT KOVA (evren = yerel `stl/` calisma klasoru snapshot'i; gerekce asagida):
    HER_IKISINDE  — R2'de VE Drive'da  -> saglikli
    SADECE_R2     — R2'de var, Drive'da yok -> SARI (yedek eksik; musteri ETKILENMEZ)
    SADECE_DRIVE  — Drive'da var, R2'de yok -> ESIK ustunde KIRMIZI (musteri yolu kirik:
                    yonetim paneli uretim dosyasini `/stl-liste?id=` ile R2'DEN ceker)
    HICBIRINDE    — ne R2 ne Drive -> HER ZAMAN KIRMIZI (dosya YALNIZ bu makinede; `stl/`
                    gecici calisma klasorudur, silinirse dosya tamamen kaybolur)

🔴 EVREN SECIMI VE GEREKCESI (olculdu, 14 Agu; secenekler tek tek tartildi):
  - `urunler.json` (katalog, 26.781 urun): urun basina STL LISTESI TUTMAZ -> denetlenecek
    dosya evrenini URETEMEZ. Reddedildi.
  - `.stl-r2-manifest.json` (10.828 kayit): canli R2'de 12.421 nesne var, yani manifest
    **1.652 nesne EKSIK**. Tek kanonik alinsaydi R2'de FIILEN duran 1.652 dosya "yok"
    gorunur, nobetci yanlis kirmizi yakardi ([[nobetci-kanonik-kaynagi-tek-eksende]]).
    Reddedildi — R2 varligi CANLI LISTEDEN olculur, manifestten DEGIL.
  - **SECILEN: yerel `stl/` snapshot'i**, R2 (canli liste) ve Drive yalnizca VARLIK
    SORGUSU olarak. Gerekce: `HICBIRINDE` kovasi — yani tek-kopya kaybi, en agir sinif —
    ancak bu evrende TANIMLIDIR (R2'yi evren alirsan "hicbirinde" mantiken bos kumedir).
    Ayrica yukleme KUYRUGU zaten bu klasordur; kural burada kirilir, burada olculmelidir.
  🔴 KOR NOKTASI (bilerek kabul edildi, gizlenmiyor): R2'ye yuklenip YERELDEN SILINMIS bir
    dosyanin Drive kopyasi sonradan kaybolursa bu nobetci GORMEZ (evrende degildir).
    O eksen icin ikincil olcum basilir: R2_TOPLAM / DRIVE_TOPLAM / R2_DRIVE_YEDEKSIZ
    (canli R2 nesnelerinden Drive'da basename karsiligi olmayanlar) — RAPORLANIR, HUKUM
    VERMEZ (esigi olculmedi; sayiyla hukum vermek [[hukum-yanlis-birimde]] olurdu).

🔴 ESIK SIFIR DEGIL, SAYIDAN TURETILDI: hasat ile yukleme arasinda MESRU bir pencere var
  (dosya once inip Drive'a yedeklenir, yukleyici parti sonunda kosar). Olculen hasat hizi
  ~7 dosya/dk (14 Agu, 03:00-03:15 penceresinde `stl/` 612->756). ESIK=20 ~= 3 dakikalik
  hasat: bundan uzun bir gecikme "ucustaki parti" degil TIKANMIS HAT'tir. Kontrol: gecen
  hafta saglikli kapanista SADECE_DRIVE=9 (hepsi stub) idi -> esik gunluk gurultuye
  duyarsiz; ariza gunu 183 idi -> esik ariza sinifini YAKALAR. Elle dosya listesi
  TUTULMAZ (liste bayatlar, [[envanter-drift-parti-basina]]).

🔴 STUB / SAHTE DOSYA SAYIMA GIRMEZ: hasat sirasinda API rate-limit yaniti 113 baytlik
  metin dosyasi olarak `.stl` adiyla diske dusuyor ("You can only send 300 requests..."").
  Bunlar uretim dosyasi DEGILDIR; STL/3MF imzasi dogrulanmadan hicbir dosya kovaya girmez.
  Sayilari `STUB=<n>` olarak AYRI basilir (bunlar yeniden hasat kalemidir).

🔴 FAIL-CLOSED: R2 listeleme reddedilirse (`AccessDenied` — olculdu: ana `.r2-credentials.json`
  tokeni yalniz medya nesnelerine kapsamli, ozel kovada List 403 verir) ya da Drive mount'u
  yoksa nobetci SIFIR BASMAZ: `HUKUM=OLCULEMEDI` der ve rc=3 doner
  ([["olculdu" diyen hukum kanit ister]] · [[fail-slow-fail-opendir]]).

🔴 IKIZ TANIM YOK: yerel dosya adindan R2 anahtarini turetme mantigi burada YENIDEN
  YAZILMAZ; `tools/stl-r2-yukle.py::siniflandir` TEK KAYNAK olarak import edilir. Anahtar
  gelenegi orada degisirse nobetci ayni turda onu izler ([[ikiz-tanim-sessiz-ayrisma]]).

KOSUM (~13 sn olculdu: 13 ag cagrisi; hasat partisi sonunda kosmaya uygun):
    python3 tools/stl-uc-kopya-nobet.py            # HUKUM + rc (0 yesil/sari, 1 kirmizi, 3 olculemedi)
    python3 tools/stl-uc-kopya-nobet.py --durum    # yalniz rapor (kirmizi yakmaz)
    python3 tools/stl-uc-kopya-nobet.py --esik 20  # esigi ez (varsayilan 20)
CI'ya BLOKLAYICI EKLENMEZ: ag + kimlik ister, kosucuda sahte kirmizi uretir
([[isci-sandbox-agi-sahte-kirmizi]]). Yeri: onarim el kitabi + hasat partisi sonu.
"""

import argparse
import importlib.util
import json
import os
import struct
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
KOVA = "pruvo-ozel"
ONEK = "stl"
KIMLIK_OZEL = os.path.join(REPO, ".r2-credentials.json.ozel")
KIMLIK_ANA = os.path.join(REPO, ".r2-credentials.json")
VARSAYILAN_ESIK = 20
UZANTILAR = (".stl", ".3mf")


class OlcumHatasi(RuntimeError):
    """Olcum YAPILAMADI (ag/izin/mount). Sahte sifir basmak yerine bu firlatilir."""


# ---------------------------------------------------------------- tek kaynak: anahtar turetme

def _yukleyici():
    """`tools/stl-r2-yukle.py`'yi modul olarak yukler — anahtar turetme TEK KAYNAK.
    Dosya adi tire icerdigi icin normal `import` ile alinamaz."""
    yol = os.path.join(TOOLS, "stl-r2-yukle.py")
    spec = importlib.util.spec_from_file_location("stl_r2_yukle_nobet", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- STL/3MF imzasi (stub eleme)

def stl_gecerli(yol):
    """Dosya GERCEK bir uretim dosyasi mi? (stub/rate-limit metni ELENIR)

    SAF karar, tahmin YOK — uc kabul yolu:
      1) `.3mf` -> ZIP imzasi (`PK\\x03\\x04`); 3MF bir zip konteyneridir.
      2) binary STL -> 80 baytlik baslik + 4 bayt ucgen sayisi ve
         `boyut == 84 + 50 * ucgen` (tutarli ucgen sayisi).
      3) ASCII STL -> bas bosluklardan sonra `solid` ile baslar.
    Once binary'e bakilir: bazi binary STL basliklari da "solid" ile baslar, ters sirada
    yanlis siniflandirilirdi. Hicbirine uymayan dosya (or. 113 baytlik API hata metni)
    GECERSIZ sayilir ve hicbir kovaya girmez."""
    try:
        boyut = os.path.getsize(yol)
        with open(yol, "rb") as f:
            bas = f.read(84)
    except OSError:
        return False
    uz = os.path.splitext(yol)[1].lower()
    if uz == ".3mf":
        return bas[:4] == b"PK\x03\x04"
    if len(bas) == 84:
        (ucgen,) = struct.unpack("<I", bas[80:84])
        if boyut == 84 + 50 * ucgen and ucgen > 0:
            return True
    return bas.lstrip()[:5].lower() == b"solid"


# ---------------------------------------------------------------- kaynak indeksleri

def _s3_istemci():
    """`pruvo-ozel` kovasini LISTELEYEBILEN S3 istemcisi.

    Anahtarlar `.r2-credentials.json.ozel`'den (ozel kova kapsamli token). Ucnokta o
    dosyada yoksa ANA `.r2-credentials.json`'dan alinir (ayni Cloudflare hesabi).
    🔴 SIR LOGLANMAZ: hata metinlerinde yalniz ALAN ADI ve DOSYA YOLU gecer, DEGER GECMEZ."""
    try:
        import boto3
    except ImportError as e:
        raise OlcumHatasi("boto3 kurulu degil (pip3 install boto3) — R2 listelenemez") from e

    def _oku(yol):
        try:
            with open(yol, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    ozel, ana = _oku(KIMLIK_OZEL), _oku(KIMLIK_ANA)
    anahtar = ozel.get("access_key_id") or ozel.get("access_key")
    gizli = ozel.get("secret_access_key") or ozel.get("secret")
    ucnokta = ozel.get("endpoint") or ana.get("endpoint")
    eksik = [ad for ad, deger in (("access_key_id", anahtar), ("secret_access_key", gizli),
                                  ("endpoint", ucnokta)) if not deger]
    if eksik:
        raise OlcumHatasi("R2 kimligi eksik (%s); beklenen dosya: %s"
                          % (", ".join(eksik), KIMLIK_OZEL))
    return boto3.client("s3", endpoint_url=ucnokta, aws_access_key_id=anahtar,
                        aws_secret_access_key=gizli, region_name="auto")


def r2_listele(istemci_fn=_s3_istemci, kova=KOVA, onek=ONEK):
    """Canli `pruvo-ozel/stl/` nesne anahtarlarini dondurur (set).

    🔴 FAIL-CLOSED: izin/ag reddinde BOS KUME DONMEZ, OlcumHatasi firlatir. Bos kume
    donmek "her sey SADECE_DRIVE" demek olurdu — ya da (daha kotusu) cagiran taraf onu
    "R2 bos, sorun yok" diye yutardi. Sahte sifir YASAK."""
    try:
        istemci = istemci_fn()
        anahtarlar = set()
        jeton = None
        while True:
            arg = {"Bucket": kova, "Prefix": onek + "/", "MaxKeys": 1000}
            if jeton:
                arg["ContinuationToken"] = jeton
            yanit = istemci.list_objects_v2(**arg)
            for nesne in yanit.get("Contents", []):
                anahtarlar.add(nesne["Key"])
            if not yanit.get("IsTruncated"):
                break
            jeton = yanit.get("NextContinuationToken")
            if not jeton:
                break
        return anahtarlar
    except OlcumHatasi:
        raise
    except Exception as e:                                            # noqa: BLE001
        raise OlcumHatasi("R2 listeleme basarisiz/reddedildi (%s: %s)"
                          % (type(e).__name__, str(e)[:200])) from e


def drive_indeksle(dizin):
    """Drive STL klasorunun dosya ADLARI (basename) kumesi. Drive DUZ klasordur, orijinal
    dosya adini korur — bu yuzden eslesme basename uzerindendir (olculdu: 745 kesisen
    dosyanin 745'inde sha256 birebir esti, isim eslemesi 0 yanlis-pozitif verdi).

    🔴 FAIL-CLOSED: mount yoksa bos kume DONMEZ (yoksa her dosya "SADECE_R2" gorunur ve
    nobetci sessizce yesil yanardi)."""
    if not dizin or not os.path.isdir(dizin):
        raise OlcumHatasi("Drive STL klasoru bulunamadi (Drive uygulamasi acik mi?): %s"
                          % (dizin or "(yol cozulemedi)"))
    adlar = set()
    for kok, _dizinler, dosyalar in os.walk(dizin):
        for ad in dosyalar:
            if os.path.splitext(ad)[1].lower() in UZANTILAR:
                adlar.add(ad)
    return adlar


def yerel_tara(dizin, yukleyici=None):
    """Yerel `stl/` snapshot'ini kayitlara cevirir: [{ad, anahtar, gecerli}].

    `anahtar` = R2'de OLMASI GEREKEN anahtar; TEK KAYNAK `stl-r2-yukle.py::siniflandir`
    (onek urun-id ya da gizli kaynak-id eslemesinden cozulur). Cozulemeyen dosyalarda
    None kalir — o dosya icin R2 varligi yalnizca basename ile aranir."""
    if not os.path.isdir(dizin):
        raise OlcumHatasi("yerel STL klasoru yok: %s" % dizin)
    yuk = yukleyici or _yukleyici()
    dosyalar = sorted(a for a in os.listdir(dizin)
                      if os.path.isfile(os.path.join(dizin, a)))
    idler = yuk.urun_idleri()
    esle, cakisan = yuk.kaynak_esleme_yukle(yuk.KAYNAKLAR)
    hedefler, _hatali, _cak = yuk.siniflandir(dosyalar, idler, esle, cakisan)
    anahtar_esle = dict(hedefler)
    kayitlar = []
    for ad in dosyalar:
        if os.path.splitext(ad)[1].lower() not in UZANTILAR:
            continue
        kayitlar.append({"ad": ad,
                         "anahtar": anahtar_esle.get(ad),
                         "gecerli": stl_gecerli(os.path.join(dizin, ad))})
    return kayitlar


# ---------------------------------------------------------------- kovalama + hukum

def kovala(kayitlar, r2_anahtarlar, drive_adlari):
    """SAF fonksiyon. Dort kovayi sayar; STUB/gecersiz dosya HICBIR kovaya girmez.

    R2 varligi IKI yollu (olculdu: yalniz anahtar-cozumu 46 gercek dosyayi kaciriyordu —
    katalog/kaynak kaydi zamanla degistigi icin anahtar drift eder):
      1) cozulen kanonik anahtar canli R2 anahtar kumesinde,
      2) YA DA dosyanin TAM adi bir R2 nesnesinin basename'i (tarihsel `_eslesmeyen/`
         yuklemeleri orijinal adi korur). Parca adi ile eslesme DENENMEZ — `body.stl`
         gibi adlar yuzlerce urunde tekrar eder, yanlis-pozitif uretirdi."""
    r2_basename = {a.rsplit("/", 1)[-1] for a in r2_anahtarlar}
    sayim = {"HER_IKISINDE": 0, "SADECE_R2": 0, "SADECE_DRIVE": 0, "HICBIRINDE": 0}
    listeler = {ad: [] for ad in sayim}
    stub = []
    for kayit in kayitlar:
        if not kayit["gecerli"]:
            stub.append(kayit["ad"])
            continue
        anahtar = kayit.get("anahtar")
        r2 = (anahtar is not None and anahtar in r2_anahtarlar) or kayit["ad"] in r2_basename
        drive = kayit["ad"] in drive_adlari
        if r2 and drive:
            kova = "HER_IKISINDE"
        elif r2:
            kova = "SADECE_R2"
        elif drive:
            kova = "SADECE_DRIVE"
        else:
            kova = "HICBIRINDE"
        sayim[kova] += 1
        listeler[kova].append(kayit["ad"])
    return {"sayim": sayim, "listeler": listeler, "stub": stub,
            "toplam": len(kayitlar)}


def hukum(sayim, esik):
    """SAF fonksiyon. (durum, sebepler, rc) dondurur.

    KIRMIZI kollari:
      - HICBIRINDE > 0        -> tek-kopya kaybi (en agir; esik YOK, 1 dosya bile kirmizi)
      - SADECE_DRIVE > esik   -> musteri yolu kirik (panel R2'den ceker)
    SARI (rc=0, uyari): SADECE_R2 > 0 -> Drive yedegi eksik; veri kaybi riski ama musteri
    ETKILENMEZ. Tek basina kirmizi YAKMAZ (yoksa mesru hasat penceresi her parti sonunda
    yayini durdururdu)."""
    sebepler = []
    if sayim["HICBIRINDE"] > 0:
        sebepler.append("HICBIRINDE=%d — dosya ne R2'de ne Drive'da; TEK KOPYA bu makinede "
                        "(stl/ gecici klasordur, silinirse dosya kaybolur)"
                        % sayim["HICBIRINDE"])
    if sayim["SADECE_DRIVE"] > esik:
        sebepler.append("SADECE_DRIVE=%d > ESIK=%d — Drive'da yedekli ama R2'de YOK; "
                        "yonetim paneli uretim dosyasini R2'den ceker, siparis gelirse "
                        "dosya PANELDE GORUNMEZ" % (sayim["SADECE_DRIVE"], esik))
    if sebepler:
        return "KIRMIZI", sebepler, 1
    if sayim["SADECE_R2"] > 0:
        return "SARI", ["SADECE_R2=%d — R2'de var, Drive yedegi YOK (musteri etkilenmez, "
                        "veri kaybi riski)" % sayim["SADECE_R2"]], 0
    return "YESIL", [], 0


# ---------------------------------------------------------------- kosum

def kos(dizin, drive_dizin, esik=VARSAYILAN_ESIK, istemci_fn=_s3_istemci,
        durum_modu=False, yaz=print, yukleyici=None):
    """Tam olcum + hukum. rc: 0 yesil/sari · 1 kirmizi · 3 OLCULEMEDI.
    `--durum` modunda kirmizi kol rc'yi 0 birakir (rapor kolu), OLCULEMEDI ise HER IKI
    modda da rc!=0 doner — olculemeyen bir eksen icin "rapor" da uretilemez."""
    try:
        kayitlar = yerel_tara(dizin, yukleyici=yukleyici)
        r2_anahtarlar = r2_listele(istemci_fn=istemci_fn)
        drive_adlari = drive_indeksle(drive_dizin)
    except OlcumHatasi as e:
        yaz("HUKUM=OLCULEMEDI — %s" % e)
        yaz("KABUL: HUKUM=OLCULEMEDI (sahte sifir BASILMADI)")
        return 3

    sonuc = kovala(kayitlar, r2_anahtarlar, drive_adlari)
    sayim = sonuc["sayim"]
    r2_basename = {a.rsplit("/", 1)[-1] for a in r2_anahtarlar}
    yedeksiz = len(r2_basename - drive_adlari)

    yaz("YEREL_STL=%d · STUB=%d (uretim dosyasi DEGIL, sayima girmedi)"
        % (sonuc["toplam"], len(sonuc["stub"])))
    for ad in ("HER_IKISINDE", "SADECE_R2", "SADECE_DRIVE", "HICBIRINDE"):
        yaz("  %-13s = %d" % (ad, sayim[ad]))
    yaz("IKINCIL (raporlanir, HUKUM VERMEZ — evren kor noktasi): R2_TOPLAM=%d "
        "DRIVE_TOPLAM=%d R2_DRIVE_YEDEKSIZ=%d"
        % (len(r2_anahtarlar), len(drive_adlari), yedeksiz))

    durum, sebepler, rc = hukum(sayim, esik)
    for s in sebepler:
        yaz("  ! " + s)
    for kova in ("SADECE_DRIVE", "HICBIRINDE", "SADECE_R2"):
        if sonuc["listeler"][kova]:
            ornek = sonuc["listeler"][kova][:5]
            yaz("  ornek %s: %s%s" % (kova, ", ".join(ornek),
                                      " ..." if len(sonuc["listeler"][kova]) > 5 else ""))
    yaz("KABUL: HER_IKISINDE=%d SADECE_R2=%d SADECE_DRIVE=%d HICBIRINDE=%d STUB=%d "
        "ESIK=%d HUKUM=%s" % (sayim["HER_IKISINDE"], sayim["SADECE_R2"],
                              sayim["SADECE_DRIVE"], sayim["HICBIRINDE"],
                              len(sonuc["stub"]), esik, durum))
    return 0 if durum_modu else rc


def _drive_yolu():
    yol = os.path.join(TOOLS, "drive_yolu.py")
    spec = importlib.util.spec_from_file_location("drive_yolu_nobet", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.stl_dizini(sessiz=True)


def main():
    ap = argparse.ArgumentParser(description="STL uc-kopya (yerel/Drive/R2) nobetcisi")
    ap.add_argument("--durum", action="store_true",
                    help="yalniz rapor — kirmizi kol rc'yi bozmaz (OLCULEMEDI haric)")
    ap.add_argument("--esik", type=int, default=VARSAYILAN_ESIK,
                    help="SADECE_DRIVE kirmizi esigi (varsayilan %d)" % VARSAYILAN_ESIK)
    ap.add_argument("--dizin", default=os.path.join(REPO, "stl"))
    ap.add_argument("--drive-dizin", default=None)
    a = ap.parse_args()
    drive = a.drive_dizin if a.drive_dizin is not None else _drive_yolu()
    return kos(a.dizin, drive, esik=a.esik, durum_modu=a.durum)


if __name__ == "__main__":
    sys.exit(main())
