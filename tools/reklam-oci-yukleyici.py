#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REKLAM OCI YUKLEYICI — gerceklesen satin almayi Google Ads'e TIKLAMA KIMLIGIYLE bildirir.

NEDEN VAR (olculdu, iddia degil — 21 Eyl 2026):
  Google Ads panelinde 1-21 Eyl arasi purchase **0** gorunuyordu (son Ads purchase 30 Agu);
  ayni pencerede GA4 **21 gercek purchase** sayiyordu. Uc kirik olculdu, BIRINCISI bu dosyanin
  konusu: Ads'e satin alma sinyali gonderen adim repoda **HIC YOKTU**. `offline conversion |
  googleads | conversionAction` deseni tum repoda 3 vurus veriyordu ve UCU DE YORUMDU
  (shop/src/index.js:141, shop/src/ref.js:7) — ICRA KODU SIFIR. Yani tiklama kimligini
  mukemmel saklasak bile Google'a hicbir sey gitmiyordu.

ZEMIN (yeniden kurulmadi, uzerine kuruldu):
  * `reklam_ref_gclid` tablosu + `idx_reklam_ref_gclid_created` CANLI (K99, 25 Agu).
  * `tools/reklam-ref-halkasi-kapisi.py` 10/10 YESIL — REF halkasinin dort bacagi da FIILEN
    kosuyor: landing REF -> beacon -> D1 -> `json_extract(siparisler.atif,'$.ref')` JOIN'i.
  * gclid siparise DEGIL ayri tabloya yazilir (tasarim); JOIN anahtari `atif.ref`.
  Bu dosya o halkanin EKSIK SON ADIMIDIR: cevabi GONDEREN adim.

OKAN KARARI — BAGLAYICI, TARTISMA YOK (21 Eyl 2026):
  Yol = OCI (Offline Conversion Import, tiklama kimligiyle yukleme).
  🔴 ENHANCED CONVERSIONS REDDEDILDI: musteri verisi (e-posta/telefon/ad/adres) — HASH'LENMIS
  OLSA BILE — Google'a GITMEZ. Gonderilen alanlar YALNIZ sunlardir ve liste POZITIF
  (beyaz-liste) + KAPALIDIR:
      tiklama kimligi (gclid|gbraid|wbraid) · donusum eylemi · zaman damgasi · tutar · para birimi
  `orderId` DAHI GONDERILMEZ: karar besli alan listesini saydi, altincisini degil. Tekillik
  (ayni siparis iki kez gitmesin) BIZIM tarafimizda `reklam_oci_kuyruk.yuklendi_mi` ile
  saglanir -> Google'a ek alan tasimaya GEREK YOK. Bu siniri olcen kol:
  `tools/reklam-oci-kapisi.py` IDDIA (a) — govdede musteri verisi alani gorulurse KIRMIZI.

KIMLIK = OKAN KAPISI (PARA ve SIFRE sinifi):
  developer token / OAuth istemci + refresh token / musteri hesabi kimligi ORTAMDAN ya da
  wrangler secret'tan okunur. Repoya GIRMEZ, log'a BASILMAZ (govde/hata metinleri `gizle()`
  suzgecinden gecer). Kimlik YOKSA arac FAIL-CLOSED durur: `HAL=KIMLIK-YOK` + rc=2 ve
  HICBIR ISTEK CIKMAZ — "0 satir yuklendi" deyip yesil yanmaz (sessiz fail-open sinifi).

IKI ADIM, AYRI KOSAR (biri otekini maskelemesin):
  --kuyrukla : gerceklesen satin alma  JOIN  tiklama kimligi  ->  `reklam_oci_kuyruk` satiri
               (idempotent: siparis_no PRIMARY KEY + INSERT OR IGNORE -> ayni siparis iki kez
               kuyruga GIRMEZ; kimlik bilgisi GEREKMEZ, bu adim Google'a dokunmaz)
  --yukle    : kuyruktaki BEKLEYEN satirlari Google Ads API'sine gonderir (kimlik ZORUNLU)

VERITABANI IKI KOLLU, SQL TEK KAYNAK: canli kol `tools/d1-sync.py`nin wrangler sarmalayicisini
KULLANIR (ikinci bir wrangler kopyasi acilmaz — zaman asimi/kilit/yeniden deneme disiplini
orada yasar), yerel kol duz sqlite3'tur. Iki kol AYNI SQL metnini kosar: `--vt <dosya>` ile
kabul testi ve kuru kosum gercek sorgulari gercek bir motorda calistirir.

KULLANIM:
    python3 tools/reklam-oci-yukleyici.py --durum
    python3 tools/reklam-oci-yukleyici.py --kuyrukla [--kuru]
    python3 tools/reklam-oci-yukleyici.py --yukle [--kuru] [--tavan 200]
    python3 tools/reklam-oci-yukleyici.py --durum --vt /tmp/x.sqlite   # yerel kol

CIKIS KODLARI: 0 YESIL · 1 KIRMIZI (yukleme dustu) · 2 KIMLIK-YOK (fail-closed) ·
3 OLCULEMEDI (veritabanina/semaya ulasilamadi — "yesil" DEGIL).
"""
import argparse
import importlib.util
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SEMA_DOSYA = os.path.join(TOOLS, "d1-sema.sql")

RC_YESIL = 0
RC_KIRMIZI = 1
RC_KIMLIK_YOK = 2
RC_OLCULEMEDI = 3

# HAL jetonlari — kapanis/defter bu kelimeleri ADIYLA arar; degistirilmez.
HAL_YESIL = "HAL=YESIL"
HAL_KIRMIZI = "HAL=KIRMIZI"
HAL_KIMLIK_YOK = "HAL=KIMLIK-YOK"
HAL_OLCULEMEDI = "HAL=OLCULEMEDI"

TABLO = "reklam_oci_kuyruk"

# 🔴 PARA KAPANISI: hangi durumlar "satin alma GERCEKLESTI" sayilir. `odendi` iyzico
# retrieve DOGRULAMASIYLA yazilir (shop/src/index.js donus()) ve siparis oradan ileri
# akar (uretimde -> kargolandi -> tamamlandi). Yalniz 'odendi' arasaydik ilerlemis
# siparisler SESSIZCE kuyruga GIRMEZDI — olculdu: canlida 38 odenmis satirin yalniz 1'i
# hala 'odendi' durumunda, 35'i 'tamamlandi'.
# `iptal` / `incele` / `bekliyor` / `havale-bekliyor` BU KUMEDE DEGILDIR (para gelmedi).
ODENMIS_DURUMLAR = ("odendi", "uretimde", "kargolandi", "tamamlandi")

# Google Ads donusum eyleminin INSAN ADI (kayit icin). Gercek `conversionAction` kaynak adi
# ORTAMDAN gelir (asagidaki KIMLIK_ALANLARI) — id repoya yazilmaz.
DONUSUM_ADI = "PRUVO Satin Alma (OCI)"
PARA_BIRIMI = "TRY"          # ZORUNLU: gonderilmezse Google degeri hesap para biriminde sayar

# ── GOOGLE ADS UCU ────────────────────────────────────────────────────────────
ADS_SURUM = "v21"
ADS_TABAN = "https://googleads.googleapis.com/" + ADS_SURUM
OAUTH_UCU = "https://oauth2.googleapis.com/token"

# 🔴 BEYAZ LISTE — GONDERILEN ALANLARIN TAM KUMESI (Okan karari, 21 Eyl).
# Bir conversion nesnesinde BUNLARIN DISINDA anahtar OLAMAZ. Tiklama kimligi anahtari
# uctur ve bir satirda YALNIZ BIRI bulunur (gclid | gbraid | wbraid).
TIKLAMA_ANAHTARLARI = ("gclid", "gbraid", "wbraid")
GOVDE_ALANLARI = ("conversionAction", "conversionDateTime", "conversionValue", "currencyCode")
IZINLI_ANAHTARLAR = frozenset(TIKLAMA_ANAHTARLARI) | frozenset(GOVDE_ALANLARI)

# 🔴 MUSTERI VERISI JETONLARI — govdede bu jetonlardan biri (kucuk harfe indirgenmis alan
# adi icinde) gorulurse ENHANCED CONVERSIONS'a kaymisiz demektir. Kapi bunu ADIYLA arar;
# liste beyaz-listenin YEDEGI degil, IKINCI eksenidir (beyaz liste "ne var"i, bu "ne asla
# olmamali"yi olcer — biri gevsetilirse oteki hala yakalar).
MUSTERI_VERISI_JETONLARI = (
    "email", "eposta", "phone", "telefon", "hashed", "hash", "address", "adres",
    "firstname", "lastname", "ad", "soyad", "userident", "postal", "zip", "street",
    "city", "country", "name",
)


class Olculemedi(Exception):
    """Olcum yapilamadi — 'yesil' DEGIL ([[olculemedi-bypass-degil-menzil-daraltmasi]])."""


# ══════════════════════════════════════════════════════════════════════════════
# KIMLIK — OKAN KAPISI (SIFRE sinifi). Degerler ASLA basilmaz.
# ══════════════════════════════════════════════════════════════════════════════
# (ortam degiskeni, insan adi) — SIRA red metnindeki sirayi da belirler.
KIMLIK_ALANLARI = (
    ("GOOGLE_ADS_DEVELOPER_TOKEN", "developer token"),
    ("GOOGLE_ADS_CLIENT_ID", "OAuth istemci kimligi"),
    ("GOOGLE_ADS_CLIENT_SECRET", "OAuth istemci sirri"),
    ("GOOGLE_ADS_REFRESH_TOKEN", "OAuth refresh token"),
    ("GOOGLE_ADS_CUSTOMER_ID", "musteri hesabi kimligi (10 hane, tiresiz)"),
    ("GOOGLE_ADS_CONVERSION_ACTION_ID", "donusum eylemi kimligi (sayisal)"),
)
# Istege bagli: MCC (yonetici hesap) altindan cagriliyorsa.
KIMLIK_SECMELI = ("GOOGLE_ADS_LOGIN_CUSTOMER_ID",)

# 🔴 IKI SINIF, AYNI KUTUDA DEGIL — ilk kosumda kapi bunu bana KIRMIZI yakarak ogretti:
#   GIZLI  : SIFRE sinifi. Yalniz OAuth token takasinda (govde) ve `developer-token`
#            basliginda bulunur; donusum GOVDESINDE, log'da, D1 kaydinda ASLA gorunmez.
#   TANIMLAYICI: hesap/donusum kimligi. `conversionAction` kaynak adinin ve URL'nin
#            ZORUNLU parcasidir -> govdede GORUNMEK ZORUNDADIR, sir DEGILDIR.
# Ikisini tek kumede "sir" saymak, govdede gorunmesi GEREKEN tanimlayiciyi sizinti
# sanan YANLIS EKSENLI bir iddia uretir (olculdu: (i) bacagi ilk kosumda tam da
# bu yuzden kirmizi yandi). Maskeleme ve sizinti olcumu artik GIZLI kumesini kullanir.
GIZLI_ALANLAR = ("GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
                 "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN")
TANIMLAYICI_ALANLAR = ("GOOGLE_ADS_CUSTOMER_ID", "GOOGLE_ADS_CONVERSION_ACTION_ID",
                       "GOOGLE_ADS_LOGIN_CUSTOMER_ID")


class Kimlik(object):
    """Google Ads kimligi. Degerleri TASIR, BASMAZ — `__repr__` bile maskelidir."""

    def __init__(self, degerler):
        self.d = dict(degerler)

    def __repr__(self):                                    # pragma: no cover (savunma)
        return "<Kimlik alan=%d (degerler MASKELI)>" % len(self.d)

    __str__ = __repr__

    @property
    def musteri_id(self):
        return re.sub(r"\D", "", self.d["GOOGLE_ADS_CUSTOMER_ID"])

    @property
    def donusum_kaynak_adi(self):
        """Google `conversionAction` kaynak adi: customers/<cid>/conversionActions/<id>."""
        return "customers/%s/conversionActions/%s" % (
            self.musteri_id, re.sub(r"\D", "", self.d["GOOGLE_ADS_CONVERSION_ACTION_ID"]))

    def sirlar(self):
        """Log/hata metinlerinden SILINECEK degerler — YALNIZ GIZLI sinifi.

        Uzundan kisaya siralanir: kisa bir sir uzun bir sirrin ALT DIZESI ise once
        uzunu maskelenmeli, yoksa geriye "***<kuyruk>" gibi kismi sizinti kalirdi.
        Tanimlayicilar (musteri/donusum kimligi) BU KUMEDE DEGILDIR — govdede ve
        URL'de gorunmeleri ZORUNLUDUR ve maskelenirlerse hata metni okunamaz olur.
        """
        return sorted((self.d[k] for k in GIZLI_ALANLAR if self.d.get(k)),
                      key=len, reverse=True)


def kimlik_coz(ortam=None):
    """Ortamdan kimligi coz. Doner: (Kimlik|None, eksik_alan_adlari).

    🔴 FAIL-CLOSED: TEK bir alan eksikse kimlik YOKTUR. "Bir kismi var, deneyelim" yolu
    ACILMAZ — yarim kimlikle atilan istek 401/403 doner ve satirlari `son_hata` ile
    kirletir; oysa arizanin adi KIMLIK-YOK'tur ve o ad dogru yeri gosterir.
    """
    o = os.environ if ortam is None else ortam
    degerler, eksik = {}, []
    for ad, _insan in KIMLIK_ALANLARI:
        v = (o.get(ad) or "").strip()
        if v:
            degerler[ad] = v
        else:
            eksik.append(ad)
    for ad in KIMLIK_SECMELI:
        v = (o.get(ad) or "").strip()
        if v:
            degerler[ad] = v
    if eksik:
        return None, eksik
    return Kimlik(degerler), []


def gizle(metin, sirlar):
    """Sir degerlerini metinden SIL. Log/hata yollarinin HEPSI buradan gecer."""
    s = "" if metin is None else str(metin)
    for sir in sirlar or ():
        if sir:
            s = s.replace(sir, "***")
    return s


def kimlik_yok_metni(eksik):
    """FAIL-CLOSED red metni: neyin eksik oldugunu ADIYLA soyler, degerini ISTEMEZ."""
    insan = dict(KIMLIK_ALANLARI)
    satir = [HAL_KIMLIK_YOK + " — Google Ads kimligi EKSIK, HICBIR ISTEK GONDERILMEDI.",
             "  Eksik ortam degiskeni (%d):" % len(eksik)]
    for ad in eksik:
        satir.append("    - %s   (%s)" % (ad, insan.get(ad, "")))
    satir += [
        "  🔴 BU BIR OKAN KAPISIDIR (SIFRE sinifi): degerleri arac URETMEZ, ISTEMEZ,",
        "     panelden ALMAYA CALISMAZ. Okan ortam degiskenine ya da wrangler secret'ina",
        "     koyar; repoya ve log'a HICBIR KOSULDA yazilmaz.",
        "  Kimlik gelene kadar hattin geri kalani CALISIR: `--kuyrukla` ve `--durum`",
        "  kimlik ISTEMEZ; kuyruk dolar, yalnizca gonderim bekler.",
    ]
    return "\n".join(satir)


# ══════════════════════════════════════════════════════════════════════════════
# TASIYICI — ag kolu. Kabul testi bunu DEGISTIRIR, gercek uc DEGISMEZ.
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 ISKELE TESLIM EDILIR ([[kabul-teslim-edilmeyen-iskeleyle-saglanirsa-alet-kor-kalir]]):
# dikis yeri TESTTE degil BU DOSYADA yasar; kabul testi sahte tasiyiciyi buraya takar ve
# TAM YOLU gercek kodla kosturur. Testin kendi kopyasini kosturdugu bir kurgu alete kor
# kalirdi.
class HttpTasiyici(object):
    """Gercek ag kolu (urllib). Doner: (http_kodu, govde_metni)."""

    def __init__(self, zaman_asimi=30):
        self.zaman_asimi = zaman_asimi

    def istek(self, url, govde, basliklar, bicim="json"):
        if bicim == "form":
            veri = urllib.parse.urlencode(govde).encode("utf-8")
            bas = dict(basliklar or {})
            bas["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            veri = json.dumps(govde).encode("utf-8")
            bas = dict(basliklar or {})
            bas["Content-Type"] = "application/json"
        istek = urllib.request.Request(url, data=veri, headers=bas, method="POST")
        try:
            with urllib.request.urlopen(istek, timeout=self.zaman_asimi) as y:
                return y.getcode(), y.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:                              # ag/DNS/TLS
            return 0, "AG HATASI: %s" % e


# ══════════════════════════════════════════════════════════════════════════════
# VERITABANI — iki kol, TEK SQL metni
# ══════════════════════════════════════════════════════════════════════════════
def _d1_modulu():
    """`tools/d1-sync.py`yi importlib ile yukle (ad tire tasir, duz import calismaz).

    SQL metin kacisi (`q`) ORADAN alinir: ikinci bir kacis kopyasi tutulsaydi biri
    guncellenir digeri kalirdi ve ayrisma SESSIZ olurdu.
    """
    yol = os.path.join(TOOLS, "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_oci", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def q(s):
    """SQL metin sabiti — tek tirnak kacisi. `d1-sync.py::q` ile BIREBIR AYNI kural.

    🔴 NEDEN IKINCI GOVDE VAR — VE NEDEN BU "IKINCI KOPYA" DEGIL: ilk surum bu
    fonksiyonu `d1-sync.py`den import ediyordu. Olculdu (kapinin kendi mutant kolu
    yakaladi): o bagimlilik yukleyiciyi KENDI DIZININE CAPALIYOR -> aletin izole bir
    kopyasi (mutant, kabul fiksturu, gecici tani kopyasi) `tools/d1-sync.py`yi
    BULAMIYOR ve COKUYOR. Sonuc yikiciydi: sekiz oldurucu mutantin SEKIZI de AYNI
    ILGISIZ sebeple "kirmizi" yaniyordu -> mutant kaniti SAHTEYDI
    ([[mutant-kopyasi-cokerse-izin-okunur]]).
    Ayrisma riski KAPI ILE kapatildi, import ile degil: `tools/reklam-oci-kapisi.py`
    (j) bacagi bu govdeyi GERCEK `d1-sync.py::q` ile dusmanca girdiler uzerinde
    KARSILASTIRIR; iki tanim ayrisirsa CI KIRMIZI yanar. Sozlesme OLCULUR, umut edilmez.
    """
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


class YerelVt(object):
    """sqlite3 kolu — kabul testi, kuru kosum ve yerel tani. Gercek SQL motoru kosar."""

    ad = "sqlite"

    def __init__(self, yol):
        self.yol = yol
        self.conn = sqlite3.connect(yol)
        self.conn.row_factory = sqlite3.Row

    def sorgu(self, sql):
        return [dict(r) for r in self.conn.execute(sql).fetchall()]

    def calistir(self, sql_metin):
        self.conn.executescript(sql_metin)
        self.conn.commit()

    def kapat(self):
        self.conn.close()


class D1Vt(object):
    """Canli kol — `d1-sync.py`nin wrangler sarmalayicisini KULLANIR (ikinci kopya YOK)."""

    ad = "D1"

    def __init__(self):
        self.d1 = _d1_modulu()

    def sorgu(self, sql):
        r = self.d1.sorgu(sql)
        return (r[0].get("results") or []) if r else []

    def calistir(self, sql_metin):
        self.d1.dosya_calistir(sql_metin)

    def kapat(self):
        pass


def vt_ac(vt_yolu=None):
    """`--vt` verildiyse yerel sqlite, verilmediyse CANLI D1. Acilmazsa OLCULEMEDI."""
    try:
        return YerelVt(vt_yolu) if vt_yolu else D1Vt()
    except Exception as e:
        raise Olculemedi("veritabani acilamadi (%s): %s" % (vt_yolu or "D1", e))


# ══════════════════════════════════════════════════════════════════════════════
# KUYRUK DOLDURMA — gerceklesen satin alma JOIN tiklama kimligi
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 `json_valid` KALKANI KEYFI DEGIL — CANLI D1'DE OLCULDU (21 Eyl 2026):
#   `siparisler.atif` kolonu `NOT NULL DEFAULT ''`tir; atif yakalanmamis sipariste deger
#   BOS DIZEDIR. Canli D1 `json_extract('', '$.ref')` cagrisinda TUM SORGUYU
#   `SQLITE_ERROR [code: 7500] malformed JSON` ile REDDEDER; YEREL sqlite ise ayni cagriya
#   sessizce NULL doner. Yani kalkansiz sorgu "yerelde YESIL, canlida KIRMIZI" sinifindadir
#   ve testle YAKALANAMAZ.
#   Olculen canli hal: 59 siparisin 2'sinde `atif=''` (ikisi de 'iptal'), odenmis kumede
#   BUGUN 0 -> sorgu SANS ESERI calisiyordu. Dogrudan/ic gezinmeyle gelen (REF'siz) bir
#   siparis 'odendi'ye gectigi GUN bu kuyruk komple DURURDU.
#   CASE kullanilir, WHERE'e yazilmaz: SQLite CASE'i KISA DEVRE degerlendirir, WHERE
#   yan tumcesinin JOIN kosulundan ONCE kosacagi ise GARANTI DEGILDIR.
ADAY_SQL = """
SELECT s.siparis_no      AS siparis_no,
       s.tarih           AS tarih,
       s.durum_gecmisi   AS durum_gecmisi,
       s.tutar_kurus     AS tutar_kurus,
       s.kargo_kurus     AS kargo_kurus,
       r.gclid           AS gclid,
       r.gbraid          AS gbraid,
       r.wbraid          AS wbraid,
       r.src             AS src
FROM siparisler s
JOIN reklam_ref_gclid r
  ON r.ref = CASE WHEN json_valid(s.atif)
                  THEN json_extract(s.atif, '$.ref') ELSE NULL END
LEFT JOIN {tablo} k ON k.siparis_no = s.siparis_no
WHERE s.durum IN ({durumlar})
  AND k.siparis_no IS NULL
ORDER BY s.tarih
""".strip()


def aday_sql():
    return ADAY_SQL.format(tablo=TABLO,
                           durumlar=", ".join(q(d) for d in ODENMIS_DURUMLAR))


def tiklama_kimligi(satir):
    """(tur, deger) — gclid > gbraid > wbraid onceligi. Hicbiri yoksa (None, None).

    🔴 ONCELIK KEYFI DEGIL: bir oturumda birden fazla kimlik varsa Google'in kendi
    onceligi gclid'dir; gbraid/wbraid yalniz gclid YOKKEN anlamlidir (iOS/app kollari).
    """
    for tur in TIKLAMA_ANAHTARLARI:
        v = (satir.get(tur) or "").strip()
        if v:
            return tur, v
    return None, None


def donusum_zamani(satir, dilim="+03:00"):
    """Google `conversionDateTime`: 'yyyy-mm-dd hh:mm:ss+03:00'.

    KAYNAK SIRASI: (1) `durum_gecmisi` icindeki 'odendi' damgasi — paranin GERCEKTEN
    dustugu an, (2) yoksa `tarih` (siparis acilis ani). Ikisi de cozulemezse None ->
    satir kuyruga GIRMEZ (zamansiz donusum Google tarafinda REDDEDILIR; uydurma damga
    atif penceresini kaydirir).
    """
    ham = None
    gecmis = satir.get("durum_gecmisi") or ""
    if gecmis:
        try:
            for kayit in json.loads(gecmis):
                if isinstance(kayit, dict) and kayit.get("d") == "odendi" and kayit.get("z"):
                    ham = kayit["z"]
                    break
        except (ValueError, TypeError):
            ham = None
    if not ham:
        ham = satir.get("tarih") or ""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", str(ham))
    if not m:
        return None
    return "%s %s%s" % (m.group(1), m.group(2), dilim)


def tahsilat_kurus(satir):
    """GERCEK tahsilat = urun + kargo (kurus tamsayisi).

    🔴 TEK KAYNAK HIZASI: shop/src/olcum.js purchaseOlayi() ile BIREBIR ayni kural
    (`tutar_kurus + kargo_kurus`). Ayrisirsa GA4 bir ciroyu, Ads baskasini gorur ve
    iki panel arasindaki fark kimseye KIRMIZI yanmadan buyur.
    """
    return int(satir.get("tutar_kurus") or 0) + int(satir.get("kargo_kurus") or 0)


def kurus_try(kurus):
    """Kurus tamsayisi -> TRY ondalik SAYI (43290 -> 432.9). olcum.js kurusTRY ile ayni."""
    return int(round(float(kurus))) / 100.0


def kuyruk_satiri(aday, simdi_ms):
    """Aday satirdan kuyruk kaydi uret. Uygun degilse (sebep, None) doner."""
    tur, deger = tiklama_kimligi(aday)
    if not deger:
        return "tiklama-kimligi-yok", None
    zaman = donusum_zamani(aday)
    if not zaman:
        return "zaman-cozulemedi", None
    tutar = tahsilat_kurus(aday)
    if tutar <= 0:
        return "tutar-sifir", None
    return None, {
        "siparis_no": aday["siparis_no"],
        "click_id": deger,
        "click_tur": tur,
        "donusum_adi": DONUSUM_ADI,
        "tutar_kurus": tutar,
        "para_birimi": PARA_BIRIMI,
        "donusum_zamani": zaman,
        "olusturuldu": int(simdi_ms),
    }


def ekleme_sql(kayitlar):
    """INSERT OR IGNORE metni — idempotens siparis_no PRIMARY KEY'inden gelir.

    🔴 `INSERT OR IGNORE` + PK = ayni siparis ikinci kez KUYRUGA GIRMEZ; zaten yuklenmis
    bir satirin `yuklendi_mi` bayragi da EZILMEZ (UPDATE degil, IGNORE).
    """
    if not kayitlar:
        return ""
    satirlar = []
    for k in kayitlar:
        satirlar.append(
            "INSERT OR IGNORE INTO %s (siparis_no, click_id, click_tur, donusum_adi, "
            "tutar_kurus, para_birimi, donusum_zamani, yuklendi_mi, deneme_sayisi, "
            "son_hata, yuklenme_zamani, olusturuldu) VALUES (%s, %s, %s, %s, %d, %s, %s, "
            "0, 0, '', NULL, %d);"
            % (TABLO, q(k["siparis_no"]), q(k["click_id"]), q(k["click_tur"]),
               q(k["donusum_adi"]), k["tutar_kurus"], q(k["para_birimi"]),
               q(k["donusum_zamani"]), k["olusturuldu"]))
    return "\n".join(satirlar)


def kuyrukla(vt, simdi_ms=None, kuru=False):
    """Adaylari kuyruga al. Doner: dokum sozlugu (SAYIYLA)."""
    simdi_ms = int(time.time() * 1000) if simdi_ms is None else int(simdi_ms)
    adaylar = vt.sorgu(aday_sql())
    kayitlar, elenen = [], {}
    for a in adaylar:
        sebep, kayit = kuyruk_satiri(a, simdi_ms)
        if kayit:
            kayitlar.append(kayit)
        else:
            elenen[sebep] = elenen.get(sebep, 0) + 1
    sql = ekleme_sql(kayitlar)
    if sql and not kuru:
        vt.calistir(sql)
    return {"aday": len(adaylar), "eklenen": len(kayitlar), "elenen": elenen, "kuru": kuru}


# ══════════════════════════════════════════════════════════════════════════════
# YUKLEME — Google Ads uploadClickConversions
# ══════════════════════════════════════════════════════════════════════════════
BEKLEYEN_SQL = ("SELECT siparis_no, click_id, click_tur, donusum_adi, tutar_kurus, "
                "para_birimi, donusum_zamani, deneme_sayisi FROM %s "
                "WHERE yuklendi_mi = 0 ORDER BY olusturuldu LIMIT %d")


def bekleyenler(vt, tavan=200):
    return vt.sorgu(BEKLEYEN_SQL % (TABLO, int(tavan)))


def conversion_govdesi(satir, donusum_kaynak_adi):
    """TEK donusum nesnesi. 🔴 ALANLAR BEYAZ LISTE — musteri verisi BURAYA GIRMEZ.

    Anahtar kumesi: {<tiklama anahtari>} | GOVDE_ALANLARI. Baska hicbir anahtar yoktur;
    `orderId` DAHI YOK (Okan karari, 21 Eyl — besli alan listesi KAPALI kumedir).
    """
    tur = satir["click_tur"]
    if tur not in TIKLAMA_ANAHTARLARI:
        raise Olculemedi("bilinmeyen tiklama kimligi turu: %r" % (tur,))
    return {
        tur: satir["click_id"],
        "conversionAction": donusum_kaynak_adi,
        "conversionDateTime": satir["donusum_zamani"],
        "conversionValue": kurus_try(satir["tutar_kurus"]),
        "currencyCode": satir["para_birimi"],
    }


def govde_ihlalleri(govde):
    """Beyaz liste + musteri verisi denetimi. Doner: ihlal metinleri (bos = temiz).

    IKI EKSEN (biri gevsetilirse oteki hala yakalar):
      1. IZINLI_ANAHTARLAR disinda anahtar VAR mi (pozitif beyaz liste),
      2. anahtar adi MUSTERI_VERISI_JETONLARI'ndan birini tasiyor mu (negatif eksen).
    Ic ice sozluk/dizi de taranir: `userIdentifiers: [{hashedEmail: ...}]` tam da boyle
    gelirdi ve yalniz ust seviye bakan bir denetim onu GORMEZDI.
    """
    ihlal = []

    def tara(dugum, yol):
        if isinstance(dugum, dict):
            for k, v in dugum.items():
                kucuk = str(k).lower()
                tam = (yol + "." + str(k)) if yol else str(k)
                if not yol and k not in IZINLI_ANAHTARLAR:
                    ihlal.append("BEYAZ LISTE DISI alan: %s" % tam)
                for jeton in MUSTERI_VERISI_JETONLARI:
                    if jeton in kucuk:
                        ihlal.append("MUSTERI VERISI alani: %s (jeton %r)" % (tam, jeton))
                        break
                tara(v, tam)
        elif isinstance(dugum, list):
            for i, v in enumerate(dugum):
                tara(v, "%s[%d]" % (yol, i))

    tara(govde, "")
    return ihlal


def erisim_jetonu(kimlik, tasiyici):
    """OAuth refresh token -> access token. Doner: (jeton|None, hata_metni)."""
    kod, govde = tasiyici.istek(
        OAUTH_UCU,
        {"client_id": kimlik.d["GOOGLE_ADS_CLIENT_ID"],
         "client_secret": kimlik.d["GOOGLE_ADS_CLIENT_SECRET"],
         "refresh_token": kimlik.d["GOOGLE_ADS_REFRESH_TOKEN"],
         "grant_type": "refresh_token"},
        {}, bicim="form")
    if kod != 200:
        return None, gizle("OAuth %s: %s" % (kod, govde[:300]), kimlik.sirlar())
    try:
        jeton = (json.loads(govde) or {}).get("access_token")
    except ValueError:
        return None, "OAuth yaniti JSON degil"
    if not jeton:
        return None, "OAuth yanitinda access_token YOK"
    return jeton, ""


def yukleme_ucu(kimlik):
    return "%s/customers/%s:uploadClickConversions" % (ADS_TABAN, kimlik.musteri_id)


def sonuc_isaretle_sql(siparis_no, basarili, hata, simdi_ms):
    """Tek satirin sonucunu yaz. 🔴 BASARISIZ satir `yuklendi_mi`yi ISARETLEMEZ.

    Basarisizda yalniz `deneme_sayisi` artar ve `son_hata` yazilir -> satir BEKLEYEN
    kalir ve bir sonraki kosumda TEKRAR DENENIR (sessiz kayip yok).
    """
    if basarili:
        return ("UPDATE %s SET yuklendi_mi = 1, yuklenme_zamani = %d, "
                "deneme_sayisi = deneme_sayisi + 1, son_hata = '' WHERE siparis_no = %s;"
                % (TABLO, int(simdi_ms), q(siparis_no)))
    return ("UPDATE %s SET deneme_sayisi = deneme_sayisi + 1, son_hata = %s "
            "WHERE siparis_no = %s;" % (TABLO, q((hata or "")[:400]), q(siparis_no)))


def yanit_coz(kod, govde, satir_sayisi):
    """Google yanitini satir basina hukme cevir. Doner: (basari_listesi, hata_listesi).

    HTTP 200 DISI -> partinin TAMAMI basarisiz (tek bir satir bile gitmedi sayilir;
    ters varsayim ikiz donusum uretirdi).
    HTTP 200 -> `results[i]` dolu ise o satir gitti; BOS ise (kismi hata) gitmedi.
    """
    if kod != 200:
        hata = "HTTP %s: %s" % (kod, (govde or "")[:300])
        return [False] * satir_sayisi, [hata] * satir_sayisi
    try:
        y = json.loads(govde or "{}") or {}
    except ValueError:
        hata = "yanit JSON degil: %s" % (govde or "")[:200]
        return [False] * satir_sayisi, [hata] * satir_sayisi
    sonuclar = y.get("results") or []
    kismi = y.get("partialFailureError") or {}
    kismi_metin = json.dumps(kismi)[:300] if kismi else "kismi hata (ayrinti yok)"
    basari, hatalar = [], []
    for i in range(satir_sayisi):
        r = sonuclar[i] if i < len(sonuclar) else None
        tamam = bool(r)
        basari.append(tamam)
        hatalar.append("" if tamam else kismi_metin)
    return basari, hatalar


def yukle(vt, kimlik, tasiyici, tavan=200, kuru=False, simdi_ms=None, sessiz=False):
    """Kuyruktaki bekleyenleri gonder. Doner: (rc, dokum).

    🔴 KIMLIK YOKSA: HICBIR ISTEK CIKMAZ ve rc=RC_KIMLIK_YOK. Bu kol `tasiyici`ya
    DOKUNMAZ — kabul testi tam da bunu olcer (sahte tasiyicinin istek sayaci 0 kalmali).
    """
    simdi_ms = int(time.time() * 1000) if simdi_ms is None else int(simdi_ms)
    if kimlik is None:
        return RC_KIMLIK_YOK, {"istek": 0, "gonderilen": 0, "basarili": 0, "basarisiz": 0}
    satirlar = bekleyenler(vt, tavan)
    dokum = {"istek": 0, "gonderilen": len(satirlar), "basarili": 0, "basarisiz": 0,
             "ihlal": [], "kuru": kuru}
    if not satirlar:
        return RC_YESIL, dokum

    govdeler = [conversion_govdesi(s, kimlik.donusum_kaynak_adi) for s in satirlar]
    for g in govdeler:
        dokum["ihlal"].extend(govde_ihlalleri(g))
    if dokum["ihlal"]:
        # 🔴 FAIL-CLOSED: govde sozlesmeyi ihlal ediyorsa GONDERILMEZ. Musteri verisi
        # sizintisi GERI ALINAMAZ; "once gonder sonra bak" yolu YOKTUR.
        return RC_KIRMIZI, dokum
    if kuru:
        dokum["govde_ornegi"] = govdeler[0]
        return RC_YESIL, dokum

    jeton, hata = erisim_jetonu(kimlik, tasiyici)
    dokum["istek"] += 1
    if not jeton:
        yazim = [sonuc_isaretle_sql(s["siparis_no"], False, hata, simdi_ms) for s in satirlar]
        vt.calistir("\n".join(yazim))
        dokum["basarisiz"] = len(satirlar)
        dokum["hata"] = hata
        return RC_KIRMIZI, dokum

    basliklar = {"Authorization": "Bearer " + jeton,
                 "developer-token": kimlik.d["GOOGLE_ADS_DEVELOPER_TOKEN"]}
    if kimlik.d.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"):
        basliklar["login-customer-id"] = re.sub(
            r"\D", "", kimlik.d["GOOGLE_ADS_LOGIN_CUSTOMER_ID"])
    kod, yanit = tasiyici.istek(
        yukleme_ucu(kimlik),
        {"conversions": govdeler, "partialFailure": True},
        basliklar)
    dokum["istek"] += 1
    basari, hatalar = yanit_coz(kod, yanit, len(satirlar))

    yazim = []
    for s, ok, h in zip(satirlar, basari, hatalar):
        yazim.append(sonuc_isaretle_sql(s["siparis_no"], ok,
                                        gizle(h, kimlik.sirlar()), simdi_ms))
        dokum["basarili" if ok else "basarisiz"] += 1
    vt.calistir("\n".join(yazim))
    if not sessiz and dokum["basarisiz"]:
        print(gizle("!! yukleme hatasi: %s" % (hatalar[0] or "")[:300], kimlik.sirlar()))
    return (RC_YESIL if dokum["basarisiz"] == 0 else RC_KIRMIZI), dokum


# ══════════════════════════════════════════════════════════════════════════════
# DURUM
# ══════════════════════════════════════════════════════════════════════════════
DURUM_SQL = ("SELECT COUNT(*) AS toplam, "
             "SUM(CASE WHEN yuklendi_mi = 1 THEN 1 ELSE 0 END) AS yuklendi, "
             "SUM(CASE WHEN yuklendi_mi = 0 THEN 1 ELSE 0 END) AS bekleyen, "
             "SUM(CASE WHEN yuklendi_mi = 0 AND deneme_sayisi > 0 THEN 1 ELSE 0 END) "
             "AS hatali FROM " + TABLO)


def durum(vt):
    d = (vt.sorgu(DURUM_SQL) or [{}])[0]
    aday = len(vt.sorgu(aday_sql()))
    return {"toplam": int(d.get("toplam") or 0),
            "yuklendi": int(d.get("yuklendi") or 0),
            "bekleyen": int(d.get("bekleyen") or 0),
            "hatali": int(d.get("hatali") or 0),
            "kuyruga_girmemis_aday": aday}


# ══════════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kuyrukla", action="store_true",
                    help="gerceklesen satin almalari kuyruga al (kimlik GEREKMEZ)")
    ap.add_argument("--yukle", action="store_true",
                    help="bekleyen kuyrugu Google Ads'e gonder (KIMLIK ZORUNLU)")
    ap.add_argument("--durum", action="store_true", help="kuyruk dokumu (SAYIYLA)")
    ap.add_argument("--kuru", action="store_true",
                    help="yazma/gonderme YOK — ne olacagini basar")
    ap.add_argument("--tavan", type=int, default=200, help="tek kosumda en cok satir")
    ap.add_argument("--vt", default=None,
                    help="yerel sqlite dosyasi (verilmezse CANLI D1)")
    a = ap.parse_args()
    if not (a.kuyrukla or a.yukle or a.durum):
        a.durum = True

    try:
        vt = vt_ac(a.vt)
    except Olculemedi as e:
        print("%s — %s" % (HAL_OLCULEMEDI, e))
        return RC_OLCULEMEDI

    rc = RC_YESIL
    try:
        if a.kuyrukla:
            d = kuyrukla(vt, kuru=a.kuru)
            print("KUYRUKLAMA: aday=%d eklenen=%d%s" %
                  (d["aday"], d["eklenen"], " (KURU — yazilmadi)" if d["kuru"] else ""))
            for sebep, n in sorted(d["elenen"].items()):
                print("  elenen[%s]=%d" % (sebep, n))
        if a.yukle:
            kimlik, eksik = kimlik_coz()
            if kimlik is None:
                print(kimlik_yok_metni(eksik))
                return RC_KIMLIK_YOK
            rc2, d = yukle(vt, kimlik, HttpTasiyici(), tavan=a.tavan, kuru=a.kuru)
            print("YUKLEME: gonderilen=%d basarili=%d basarisiz=%d istek=%d%s" %
                  (d["gonderilen"], d["basarili"], d["basarisiz"], d["istek"],
                   " (KURU)" if d.get("kuru") else ""))
            for i in d.get("ihlal", []):
                print("  🔴 SOZLESME IHLALI: %s" % i)
            rc = rc2 if rc2 != RC_YESIL else rc
        if a.durum:
            d = durum(vt)
            print("KUYRUK (%s): toplam=%d yuklendi=%d bekleyen=%d hatali=%d "
                  "kuyruga_girmemis_aday=%d"
                  % (vt.ad, d["toplam"], d["yuklendi"], d["bekleyen"], d["hatali"],
                     d["kuyruga_girmemis_aday"]))
    except Olculemedi as e:
        print("%s — %s" % (HAL_OLCULEMEDI, e))
        return RC_OLCULEMEDI
    finally:
        vt.kapat()

    print(HAL_YESIL if rc == RC_YESIL else
          (HAL_KIMLIK_YOK if rc == RC_KIMLIK_YOK else HAL_KIRMIZI))
    return rc


if __name__ == "__main__":
    sys.exit(main())
