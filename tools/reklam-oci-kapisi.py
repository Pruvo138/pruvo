#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REKLAM OCI KAPISI — satin almanin Google Ads'e GONDERILEBILIR kaldigini FIILEN kosturur.

NEDEN VAR (olculdu, 21 Eyl 2026): Ads panelinde 1-21 Eyl purchase **0** (son Ads purchase
30 Agu) iken GA4 ayni pencerede **21 gercek purchase** sayiyordu. `reklam_ref_gclid` halkasi
10/10 YESILDI — yani "hangi reklamdan geldi" sorusu CEVAPLANABILIYORDU; eksik olan CEVABI
GONDEREN adimdi. O adim (tools/reklam-oci-yukleyici.py) artik var ve bu kapi onun YASADIGINI
her push'ta olcer.

SESSIZ-HATA SINIFI, PARA: bu hat koparsa hicbir sey patlamaz — siparis normal akar, musteri
etkilenmez, tek degisen sey reklam harcamasinin KOR kalmasidir (Ads teklif algoritmasi
donusum gormedigi icin butceyi yanlis yere surer). Tam da bu yuzden kapi gerekir.

OLCULEN BES IDDIA (cip sartnamesi (a)-(e); her biri ADIYLA basilir):
  (a) GOVDE MUSTERI VERISI TASIMIYOR — gonderilen JSON'da e-posta/telefon/ad/adres/hash
      alani YOK; anahtar kumesi POZITIF beyaz listeye BIREBIR esit (Enhanced Conversions
      Okan tarafindan REDDEDILDI; hash'li olsa bile musteri verisi Google'a GITMEZ).
  (b) AYNI SIPARIS IKI KEZ GONDERILMEZ — kuyruklama iki kez kosar, yukleme iki kez kosar;
      Google ucuna giden conversion sayisi 1 kalir.
  (c) KIMLIK YOKKEN rc != 0 VE HICBIR ISTEK CIKMAZ — sahte tasiyicinin istek sayaci 0.
  (d) BASARISIZ YUKLEME `yuklendi_mi` ISARETLEMEZ ve satir TEKRAR DENENEBILIR kalir.
  (e) TUTAR ve PARA BIRIMI siparisteki degerle BIREBIR (kurus -> TRY, kargo DAHIL —
      shop/src/olcum.js purchaseOlayi() ile ayni kural).
Ustune dort YAPISAL bacak: (f) kanonik semada tablo VAR · (g) goc defterinde indeks VAR ·
(h) JOIN gercek sqlite'ta gercekten esliyor · (i) yukleyicide sirlar log'a BASILMIYOR.

NASIL OLCER — TAKLIT DEGIL, GERCEK KOD:
  * sema `tools/d1-sema.sql`den OKUNUR ve gercek sqlite'a yuklenir (tablo kanondan
    cikarsa INSERT "no such table" ile duser — jeton taramasi bunu goremezdi),
  * kuyruklama + yukleme GERCEK `tools/reklam-oci-yukleyici.py` fonksiyonlariyla kosar,
  * Google ucu SAHTEDIR (tasiyici dikisi aletin KENDI govdesinde yasar) — AG YOK, canli
    D1 YOK, wrangler YOK, GERCEK KIMLIK YOK.

DAR EKSEN: urun/fiyat/gorsel/kategori degisikligi, ILGISIZ bir tablonun semasi bu kapiyi
KIRMIZI YAKMAZ — `--kendini-test` K0 kolu bunu OLCER.

FAIL-CLOSED: modul import edilemiyor / sema okunamiyor / sqlite JSON1 yok -> OLCULEMEDI +
exit 3 ("yesil" DEGIL, [[olculemedi-bypass-degil-menzil-daraltmasi]]).

KULLANIM:
    python3 tools/reklam-oci-kapisi.py                 # KAPI (CI): bacak koparsa exit 1
    python3 tools/reklam-oci-kapisi.py --kendini-test  # oldurucu mutantlar + K0 kontrol
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SEMA_VARSAYILAN = os.path.join(TOOLS, "d1-sema.sql")
YUKLEYICI_VARSAYILAN = os.path.join(TOOLS, "reklam-oci-yukleyici.py")
D1_SYNC = os.path.join(TOOLS, "d1-sync.py")

RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 3

# Fikstur sabitleri — REF landing kanonigine (attribution-ref.js REF_RE / shop/src/ref.js
# REF_KALIBI) UYAR; uymayan deger sunucuda fail-closed duser ve halka zaten kopuk olurdu.
REF_DEGERI = "REF:GS-OCI-Q7M4"
GCLID_DEGERI = "Cj0KCQ-OCI-TEST-GCLID"
SIPARIS_NO = "PR-260921-101500-A1B"
SIPARIS_NO_ATIFSIZ = "PR-260921-110000-B2C"   # atif='' (dogrudan geldi) — (k1) yuku
TUTAR_KURUS = 43290          # 432,90 TL urun
KARGO_KURUS = 25000          # 250,00 TL kargo -> tahsilat 68290 kurus = 682,90 TL
BEKLENEN_TRY = 682.90
ODENDI_ISO = "2026-09-21T10:15:00.000Z"
BEKLENEN_ZAMAN = "2026-09-21 10:15:00+03:00"

# Sahte kimlik — GERCEK DEGIL, hicbir yere gitmez (tasiyici sahte). Degerler kasten
# "sir gibi" uzun: (i) bacaginda log/hata metinlerinde GORUNMEDIKLERI olculur.
#
# 🔴 BU SOZLUK ALAN KUMESININ TANIMI DEGIL, yalnizca FIKSTUR DEGERLERIDIR. Kumenin
# TEK KAYNAGI `reklam-oci-yukleyici.py::KIMLIK_ALANLARI`; (c3) bacagi bu sozlugun
# o kaynagi TAM KAPSADIGINI olcer. Kaynaga yeni bir ZORUNLU alan eklenirse fikstur
# sessizce eksik kalmaz — kapi KIRMIZI yanar.
# `GOOGLE_ADS_DEVELOPER_TOKEN` artik ZORUNLU DEGIL (9 Eyl 2026'da emekli edildi) ama
# fiksturde KALIR: (i1b) "kurulu jeton YALNIZ BASLIKTA tasinir" ve (i1c) "jeton yokken
# baslik HIC OLUSMAZ" bacaklari IKI YONU de olcer.
SAHTE_ORTAM = {
    "GOOGLE_ADS_DEVELOPER_TOKEN": "SAHTE-DEV-TOKEN-0123456789",
    "GOOGLE_ADS_CLIENT_ID": "sahte-istemci.apps.googleusercontent.com",
    "GOOGLE_ADS_CLIENT_SECRET": "SAHTE-ISTEMCI-SIRRI-0123456789",
    "GOOGLE_ADS_REFRESH_TOKEN": "1//SAHTE-REFRESH-TOKEN-0123456789",
    "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
    "GOOGLE_ADS_CONVERSION_ACTION_ID": "987654321",
}


class Olculemedi(Exception):
    pass


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def modul_yukle(ad, yol):
    """Tire tasiyan dosya adini importlib ile yukle (duz `import` calismaz)."""
    try:
        spec = importlib.util.spec_from_file_location(ad, yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        raise Olculemedi("modul yuklenemedi (%s): %s" % (yol, e))


def create_blok(sema_metni, tablo):
    """d1-sema.sql'den `CREATE TABLE IF NOT EXISTS <tablo> (...);` blogu (yoksa None)."""
    m = re.search(r"CREATE TABLE IF NOT EXISTS %s\s*\(.*?\n\);" % re.escape(tablo),
                  sema_metni, re.S)
    return m.group(0) if m else None


def sql_yorumsuz(s):
    return "\n".join(x for x in s.splitlines() if not x.strip().startswith("--"))


# ══════════════════════════════════════════════════════════════════════════════
# SAHTE GOOGLE UCU — ag YOK. Yukleyicinin KENDI tasiyici dikisine takilir.
# ══════════════════════════════════════════════════════════════════════════════
class SahteTasiyici(object):
    """Google OAuth + uploadClickConversions taklidi. Gonderilen HER govdeyi SAKLAR.

    `yukleme_hatasi` acilirsa uc HTTP 400 doner -> (d) iddiasinin yuku budur.
    """

    def __init__(self, yukleme_hatasi=False):
        self.istekler = []              # [(url, govde, basliklar)]
        self.yukleme_hatasi = yukleme_hatasi

    @property
    def gonderilen_conversionlar(self):
        c = []
        for url, govde, _b in self.istekler:
            if "uploadClickConversions" in url:
                c.extend(govde.get("conversions") or [])
        return c

    def istek(self, url, govde, basliklar, bicim="json"):
        self.istekler.append((url, govde, dict(basliklar or {})))
        if "oauth2" in url:
            return 200, json.dumps({"access_token": "SAHTE-ERISIM-JETONU",
                                    "expires_in": 3600})
        if "uploadClickConversions" in url:
            if self.yukleme_hatasi:
                return 400, json.dumps({"error": {"message": "SAHTE UC: kasitli hata"}})
            n = len(govde.get("conversions") or [])
            return 200, json.dumps({"results": [
                {"conversionAction": "customers/1234567890/conversionActions/987654321",
                 "conversionDateTime": BEKLENEN_ZAMAN} for _ in range(n)]})
        return 404, "{}"


# ══════════════════════════════════════════════════════════════════════════════
# FIKSTUR — GERCEK semadan kurulan GERCEK sqlite
# ══════════════════════════════════════════════════════════════════════════════
def vt_kur(yol, sema_metni, ref_yaz=True, gclid=GCLID_DEGERI, durum="tamamlandi"):
    """`siparisler` + `reklam_ref_gclid` + `reklam_oci_kuyruk` bloklarini KANONDAN kur.

    🔴 Blok bulunamazsa KURULMAZ: hukmu sqlite verir ("no such table"), bu fonksiyon
    degil. Mutant bir tabloyu semadan silince kapi ORADA kirmizi yanar.
    """
    conn = sqlite3.connect(yol)
    try:
        conn.execute("SELECT json_extract('{\"a\":1}', '$.a')")
    except sqlite3.OperationalError as e:
        conn.close()
        raise Olculemedi("sqlite JSON1 yok: %s" % e)
    for tablo in ("siparisler", "reklam_ref_gclid", "reklam_oci_kuyruk"):
        blok = create_blok(sema_metni, tablo)
        if blok:
            conn.executescript(sql_yorumsuz(blok))
    atif = json.dumps({"ref": REF_DEGERI, "utm_source": "google", "utm_medium": "cpc"})
    # 🔴 BOS `atif` SATIRI FIKSTURE BILEREK KONUR: kolon `NOT NULL DEFAULT ''`tir ve
    # dogrudan/ic gezinmeyle gelen sipariste deger BOS DIZEDIR. Canli D1 bu satirda
    # `json_extract('', '$.ref')` cagrisini SQLITE_ERROR ile REDDEDER (yerel sqlite
    # sessizce NULL doner) -> kalkansiz sorgu boyle bir siparis odendigi GUN kuyrugu
    # KOMPLE DURDURUR. Bu satir (k1) bacaginin yukudur.
    gecmis = json.dumps([{"d": "odendi", "z": ODENDI_ISO, "o": 1}])
    try:
        conn.execute(
            "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, "
            "kargo_kurus, urunler, atif, durum_gecmisi, kanal) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (SIPARIS_NO, "tok-oci-1", "2026-09-21T10:14:00.000Z", durum, TUTAR_KURUS,
             KARGO_KURUS, "[]", atif, gecmis, "site"))
        conn.execute(
            "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, "
            "kargo_kurus, urunler, atif, durum_gecmisi, kanal) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (SIPARIS_NO_ATIFSIZ, "tok-oci-2", "2026-09-21T11:00:00.000Z", durum, 10000,
             0, "[]", "", gecmis, "site"))
        if ref_yaz:
            conn.execute(
                "INSERT INTO reklam_ref_gclid (ref, gclid, gbraid, wbraid, grup, src, "
                "ts, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (REF_DEGERI, gclid, None, None, "OCI", "GS", 1789000000000,
                 1789000000000))
        conn.commit()
    except sqlite3.OperationalError as e:
        conn.close()
        raise Olculemedi("fikstur yazilamadi (sema eksik olabilir): %s" % e)
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# KAPI
# ══════════════════════════════════════════════════════════════════════════════
def kapi(sema_yolu=SEMA_VARSAYILAN, yukleyici_yolu=YUKLEYICI_VARSAYILAN, sessiz=False):
    """Dokuz bacagi da FIILEN kosturur. Doner: RC_YESIL | RC_KIRMIZI | RC_OLCULEMEDI."""
    kirmizi = []
    ham = []

    def iddia(ad, kosul, ayrinti=""):
        if kosul:
            ham.append("  ✅ " + ad)
        else:
            kirmizi.append(ad)
            ham.append("  ❌ " + ad + ((" — " + str(ayrinti)) if ayrinti else ""))

    try:
        sema = oku(sema_yolu)
    except OSError as e:
        print("OLCULEMEDI: sema okunamadi: %s" % e)
        return RC_OLCULEMEDI
    y = modul_yukle("oci_yukleyici_kapi", yukleyici_yolu)

    # ── (f) YAPISAL: tablo KANONIK semada -------------------------------------
    blok = create_blok(sema, y.TABLO)
    iddia("(f) `%s` KANONIK semada tanimli (tools/d1-sema.sql)" % y.TABLO, bool(blok))
    if blok:
        eksik_kolon = [k for k in ("siparis_no", "click_id", "click_tur", "donusum_adi",
                                   "tutar_kurus", "para_birimi", "donusum_zamani",
                                   "yuklendi_mi", "deneme_sayisi", "son_hata",
                                   "yuklenme_zamani", "olusturuldu") if k not in blok]
        iddia("(f2) kuyruk kolonlarinin HEPSI semada (yukleme durumu ol culebilir)"
              .replace("ol culebilir", "olculebilir"),
              not eksik_kolon, "eksik: " + ", ".join(eksik_kolon))

    # ── (g) YAPISAL: indeks GOC kayit defterinde -------------------------------
    # 🔴 `d1-sync.py` DAIMA CANLI AGACTAN okunur (mutant kopyasindan DEGIL): bu bacak
    # kayit defterinin ve SQL kacis sozlesmesinin GERCEK halini olcer.
    try:
        d1 = modul_yukle("d1_sync_oci_kapi", D1_SYNC)
        kayit = [ix for ix in d1.GOC_INDEKS if ix["tablo"] == y.TABLO]
        iddia("(g) `%s` indeksi d1-sync.py GOC_INDEKS defterinde (canli hal olculebilir)"
              % y.TABLO, bool(kayit), "kayit yok")

        # ── (j) SQL KACIS SOZLESMESI: iki tanim AYRISAMAZ ---------------------
        # Yukleyici `q()`yi KENDI govdesinde tasir (import bagimliligi izole kopyayi
        # cokertiyordu — mutant kaniti sahte oluyordu). Ayrisma riski BURADA, dusmanca
        # girdilerle OLCULUR: biri degisip oteki kalirsa CI KIRMIZI yanar.
        girdiler = [None, "", "a", "a'b", "''", "O'Neill", "\\", "%s", "0", "REF:GS-A-1",
                    "tek ' tirnak ve \"cift\"", "ç ğ ı ö ş ü", "a''b'''c"]
        ayrisan = [g for g in girdiler if y.q(g) != d1.q(g)]
        iddia("(j) yukleyici q() ile d1-sync.py::q %d dusmanca girdide BIREBIR ayni "
              "(SQL kacis sozlesmesi ayrisamaz)" % len(girdiler),
              not ayrisan, "ayrisan: %r" % (ayrisan[:3],))
    except Olculemedi as e:
        iddia("(g) GOC_INDEKS defteri okunabildi", False, e)

    gec = tempfile.mkdtemp(prefix="oci-kapi-")
    try:
        vt_yolu = os.path.join(gec, "oci.sqlite")
        try:
            vt_kur(vt_yolu, sema)
        except Olculemedi as e:
            print("\n".join(ham))
            print("OLCULEMEDI: fikstur kurulamadi -> %s" % e)
            return RC_OLCULEMEDI

        vt = y.YerelVt(vt_yolu)

        def bacaklar():
            # ── (h) JOIN: siparis -> REF -> tiklama kimligi ---------------------
            adaylar = vt.sorgu(y.aday_sql())
            iddia("(h) odenmis siparis GERCEK JOIN ile tiklama kimligine eslesti "
                  "(json_extract(atif,'$.ref') == reklam_ref_gclid.ref)",
                  len(adaylar) == 1 and (adaylar[0].get("gclid") == GCLID_DEGERI),
                  "aday=%d" % len(adaylar))

            # ── (k) BOS `atif` KALKANI — CANLI D1'de OLCULEN AYRIM ---------------
            # (k1) DAVRANIS: fiksturde `atif=''` olan ODENMIS bir siparis VAR; aday
            #      sorgusu COKMEDEN kosmali ve o satiri ELEMELI.
            iddia("(k1) `atif=''` olan odenmis siparis sorguyu COKERTMEDI ve adaylardan "
                  "ELENDI (dogrudan gelen musteri kuyrugu durduramaz)",
                  len(adaylar) == 1
                  and all(a["siparis_no"] != SIPARIS_NO_ATIFSIZ for a in adaylar),
                  "aday=%s" % [a["siparis_no"] for a in adaylar])
            # (k2) YAPISAL — ve bu bacagin SINIRI ACIKCA YAZILIDIR: asil ariza
            #      MOTOR FARKINDADIR, mantikta DEGIL. Canli D1 `json_extract('', ...)`
            #      cagrisini `SQLITE_ERROR [7500] malformed JSON` ile REDDEDER; yerel
            #      sqlite AYNI cagriya sessizce NULL doner. Yani (k1) yerelde kalkan
            #      OLMASA DA yesil kalir -> tek basina YETMEZ. Kalkanin VARLIGI bu
            #      yuzden JETON ekseninde olculur; gerekcesi canlida olculmustur
            #      (kalkansiz sorgu 'iptal' kumesinde CANLIDA HATA verdi, kalkanli
            #      ayni kumede 12 satir dondu).
            iddia("(k2) aday sorgusu `json_valid` kalkanini TASIYOR "
                  "(D1 <-> sqlite ayrimi yerelde taklit EDILEMEZ — jeton ekseni)",
                  "json_valid" in y.ADAY_SQL, y.ADAY_SQL[:120])

            # ── (b1) KUYRUKLAMA IDEMPOTENS: iki kez kos, 1 satir --------------
            d1k = y.kuyrukla(vt, simdi_ms=1789000001000)
            d2k = y.kuyrukla(vt, simdi_ms=1789000002000)
            kuyruk_n = vt.sorgu("SELECT COUNT(*) AS n FROM %s" % y.TABLO)[0]["n"]
            iddia("(b1) ayni siparis IKI kuyruklama kosumunda da TEK satir "
                  "(INSERT OR IGNORE + siparis_no PK)",
                  d1k["eklenen"] == 1 and kuyruk_n == 1,
                  "1.kosum eklenen=%s · 2.kosum aday=%s · satir=%s"
                  % (d1k["eklenen"], d2k["aday"], kuyruk_n))

            # ── (e) TUTAR + PARA BIRIMI birebir -------------------------------
            k = vt.sorgu("SELECT * FROM %s" % y.TABLO)[0]
            iddia("(e) tutar siparisteki tahsilatla BIREBIR (urun+kargo=%d kurus) ve "
                  "para birimi TRY" % (TUTAR_KURUS + KARGO_KURUS),
                  k["tutar_kurus"] == TUTAR_KURUS + KARGO_KURUS
                  and k["para_birimi"] == "TRY",
                  "tutar=%s para=%s" % (k["tutar_kurus"], k["para_birimi"]))
            iddia("(e2) donusum zamani 'odendi' damgasindan uretildi (%s)"
                  % BEKLENEN_ZAMAN,
                  k["donusum_zamani"] == BEKLENEN_ZAMAN, k["donusum_zamani"])

            # ── (c) KIMLIK YOKKEN: rc != 0 ve SIFIR istek ---------------------
            bos_tasiyici = SahteTasiyici()
            kimlik_yok, eksik = y.kimlik_coz({})
            rc_kimliksiz, dk = y.yukle(vt, kimlik_yok, bos_tasiyici, sessiz=True)
            iddia("(c) KIMLIK YOKKEN rc != 0 (HAL=KIMLIK-YOK) ve HICBIR ISTEK CIKMADI",
                  kimlik_yok is None and rc_kimliksiz == y.RC_KIMLIK_YOK
                  and len(bos_tasiyici.istekler) == 0 and dk["istek"] == 0,
                  "rc=%s istek=%d eksik=%d" % (rc_kimliksiz, len(bos_tasiyici.istekler),
                                               len(eksik)))
            hala_bekleyen = vt.sorgu(
                "SELECT COUNT(*) AS n FROM %s WHERE yuklendi_mi = 0" % y.TABLO)[0]["n"]
            iddia("(c2) kimliksiz kosum kuyrugu BOZMADI (satir BEKLEYEN kaldi)",
                  hala_bekleyen == 1, "bekleyen=%s" % hala_bekleyen)

            # ── (c3) FIKSTUR TEK KAYNAGI TAM KAPSIYOR -------------------------
            # Alan kumesi bu dosyada ELLE YAZILMAZ; `KIMLIK_ALANLARI`dan TURETILIR.
            # Kaynaga yeni bir ZORUNLU alan eklenip fikstur guncellenmezse asagidaki
            # butun kimlikli bacaklar (d/b/i) SESSIZCE "kimlik yok" yoluna duser ve
            # kapi yine de yesil gorunurdu — bu bacak o yolu kapatir.
            kapsanmayan = [ad for ad in y.ZORUNLU_ALAN_ADLARI if not SAHTE_ORTAM.get(ad)]
            iddia("(c3) SAHTE_ORTAM fiksturu `KIMLIK_ALANLARI` TEK KAYNAGINI tam "
                  "kapsiyor (%d zorunlu alan)" % len(y.ZORUNLU_ALAN_ADLARI),
                  not kapsanmayan and len(eksik) == len(y.ZORUNLU_ALAN_ADLARI),
                  "kapsanmayan=%s · bos ortamda eksik=%d (beklenen %d)"
                  % (kapsanmayan, len(eksik), len(y.ZORUNLU_ALAN_ADLARI)))
            iddia("(c4) EMEKLI alan ZORUNLU kumede DEGIL, SECMELI kumede VE hala "
                  "GIZLI sinifinda (kurulu eski jeton maskelenir)",
                  "GOOGLE_ADS_DEVELOPER_TOKEN" not in y.ZORUNLU_ALAN_ADLARI
                  and "GOOGLE_ADS_DEVELOPER_TOKEN" in y.KIMLIK_SECMELI
                  and "GOOGLE_ADS_DEVELOPER_TOKEN" in y.GIZLI_ALANLAR,
                  "zorunlu=%s secmeli=%s gizli=%s"
                  % ("GOOGLE_ADS_DEVELOPER_TOKEN" in y.ZORUNLU_ALAN_ADLARI,
                     "GOOGLE_ADS_DEVELOPER_TOKEN" in y.KIMLIK_SECMELI,
                     "GOOGLE_ADS_DEVELOPER_TOKEN" in y.GIZLI_ALANLAR))

            # ── (d) BASARISIZ YUKLEME: isaretlemez, tekrar denenebilir --------
            kimlik, _ = y.kimlik_coz(SAHTE_ORTAM)
            kotu = SahteTasiyici(yukleme_hatasi=True)
            rc_kotu, dd = y.yukle(vt, kimlik, kotu, simdi_ms=1789000003000, sessiz=True)
            s = vt.sorgu("SELECT * FROM %s" % y.TABLO)[0]
            iddia("(d) BASARISIZ yukleme `yuklendi_mi` ISARETLEMEDI, deneme_sayisi artti "
                  "ve son_hata yazildi -> satir TEKRAR DENENEBILIR",
                  rc_kotu == y.RC_KIRMIZI and s["yuklendi_mi"] == 0
                  and s["deneme_sayisi"] == 1 and bool(s["son_hata"])
                  and s["yuklenme_zamani"] is None,
                  "rc=%s yuklendi=%s deneme=%s hata=%r" %
                  (rc_kotu, s["yuklendi_mi"], s["deneme_sayisi"], (s["son_hata"] or "")[:60]))
            iddia("(d2) basarisizliktan sonra satir hala BEKLEYEN listesinde",
                  len(y.bekleyenler(vt)) == 1, "bekleyen=%d" % len(y.bekleyenler(vt)))

            # ── BASARILI YUKLEME + (a) govde denetimi -------------------------
            iyi = SahteTasiyici()
            rc_iyi, di = y.yukle(vt, kimlik, iyi, simdi_ms=1789000004000, sessiz=True)
            gonderilen = iyi.gonderilen_conversionlar
            iddia("yukleme BASARILI (rc=0) ve TEK conversion gonderildi",
                  rc_iyi == y.RC_YESIL and len(gonderilen) == 1,
                  "rc=%s gonderilen=%d" % (rc_iyi, len(gonderilen)))

            if gonderilen:
                g = gonderilen[0]
                anahtarlar = set(g.keys())
                beklenen = {"gclid", "conversionAction", "conversionDateTime",
                            "conversionValue", "currencyCode"}
                iddia("(a) GOVDE ANAHTARLARI beyaz listeye BIREBIR esit "
                      "(tiklama kimligi · donusum eylemi · zaman · tutar · para birimi)",
                      anahtarlar == beklenen,
                      "govdede: %s" % sorted(anahtarlar))
                ihlal = y.govde_ihlalleri(g)
                iddia("(a2) GOVDEDE MUSTERI VERISI ALANI YOK "
                      "(e-posta/telefon/ad/adres/hash — Enhanced Conversions REDDEDILDI)",
                      not ihlal, "; ".join(ihlal))
                metin = json.dumps(g)
                iddia("(a3) govde METNINDE musteri verisi jetonu gecmiyor",
                      not [j for j in ("@", "musteri_", "hashed") if j in metin], metin[:160])
                iddia("(e3) gonderilen tutar TRY ondaligina BIREBIR cevrildi (%s)"
                      % BEKLENEN_TRY,
                      abs(float(g.get("conversionValue", 0)) - BEKLENEN_TRY) < 1e-9
                      and g.get("currencyCode") == "TRY",
                      "value=%s currency=%s" % (g.get("conversionValue"),
                                                g.get("currencyCode")))

            # ── (b2) AYNI SIPARIS IKI KEZ GONDERILMEZ -------------------------
            tekrar = SahteTasiyici()
            rc_tekrar, dt = y.yukle(vt, kimlik, tekrar, simdi_ms=1789000005000,
                                    sessiz=True)
            y.kuyrukla(vt, simdi_ms=1789000006000)      # doldurucu tekrar kossa bile
            tekrar2 = SahteTasiyici()
            y.yukle(vt, kimlik, tekrar2, simdi_ms=1789000007000, sessiz=True)
            iddia("(b) AYNI SIPARIS IKINCI KEZ GONDERILMEDI (yuklendi_mi=1 sonrasi "
                  "yukleme ucune 0 conversion gitti; kuyruklama tekrar kossa bile)",
                  rc_tekrar == y.RC_YESIL
                  and len(tekrar.gonderilen_conversionlar) == 0
                  and len(tekrar2.gonderilen_conversionlar) == 0,
                  "1.tekrar=%d 2.tekrar=%d" % (len(tekrar.gonderilen_conversionlar),
                                               len(tekrar2.gonderilen_conversionlar)))
            son = vt.sorgu("SELECT * FROM %s" % y.TABLO)[0]
            iddia("(b3) basarili satirda yuklendi_mi=1 ve yuklenme_zamani YAZILDI",
                  son["yuklendi_mi"] == 1 and son["yuklenme_zamani"] == 1789000004000,
                  "yuklendi=%s zaman=%s" % (son["yuklendi_mi"], son["yuklenme_zamani"]))

            # ── (i) SIR SIZINTISI: GIZLI sinifi kayda/govdeye DUSMUYOR ---------
            # 🔴 EKSEN AYRIMI: `GIZLI_ALANLAR` (developer token / OAuth istemci + sirri /
            # refresh token) govdede ASLA bulunmaz; `TANIMLAYICI_ALANLAR` (musteri ve
            # donusum kimligi) `conversionAction` kaynak adinin ZORUNLU parcasidir ve
            # govdede BULUNMAK ZORUNDADIR. Ikisini tek kumede saymak yanlis-eksenli bir
            # sizinti iddiasi uretir (bu kapi ilk kosumda tam da onu yakaladi).
            sirlar = [SAHTE_ORTAM[k] for k in y.GIZLI_ALANLAR if SAHTE_ORTAM.get(k)]
            govde_metni = json.dumps([g for _u, g, _b in iyi.istekler
                                      if isinstance(g, dict) and "conversions" in g])
            sizinti_govde = [k for k in y.GIZLI_ALANLAR
                             if SAHTE_ORTAM.get(k) and SAHTE_ORTAM[k] in govde_metni]
            iddia("(i) yukleme GOVDESINDE GIZLI kimlik alani YOK "
                  "(developer token / istemci sirri / refresh token)",
                  not sizinti_govde, "sizan: %s" % sizinti_govde)
            basliklar = [b for u, _g, b in iyi.istekler if "uploadClickConversions" in u]
            iddia("(i1b) developer token YALNIZ BASLIKTA tasindi "
                  "(govdeye DEGIL, URL'ye DEGIL)",
                  bool(basliklar)
                  and basliklar[0].get("developer-token")
                  == SAHTE_ORTAM["GOOGLE_ADS_DEVELOPER_TOKEN"]
                  and SAHTE_ORTAM["GOOGLE_ADS_DEVELOPER_TOKEN"] not in govde_metni
                  and not [u for u, _g, _b in iyi.istekler
                           if SAHTE_ORTAM["GOOGLE_ADS_DEVELOPER_TOKEN"] in u],
                  "baslik=%s" % (sorted(basliklar[0]) if basliklar else None))

            # ── (i1c) EMEKLI ALAN, TERS YON: jeton YOKKEN baslik HIC OLUSMAZ ----
            # 🔴 (i1b) yalniz "kurulu jeton nereye gidiyor"u olcer; bugunku GERCEK
            # hal jetonun HIC OLMAMASIDIR (Google 9 Eyl 2026'da uretimi durdurdu).
            # Olculmezse iki ariza sessiz kalirdi: (1) alan zorunlu sanilip kimlik
            # DUSER -> hat sonsuza kadar fail-closed; (2) baslik kosulsuz eklenip
            # `developer-token: ""` gider -> 400.
            vt2 = None
            try:
                vt2_yolu = os.path.join(gec, "oci-jetonsuz.sqlite")
                vt_kur(vt2_yolu, sema)
                vt2 = y.YerelVt(vt2_yolu)
                y.kuyrukla(vt2, simdi_ms=1789000008000)
                ortam_jetonsuz = dict(SAHTE_ORTAM)
                ortam_jetonsuz.pop("GOOGLE_ADS_DEVELOPER_TOKEN", None)
                kimlik2, eksik2 = y.kimlik_coz(ortam_jetonsuz)
                tasiyici2 = SahteTasiyici()
                rc2, _dj = y.yukle(vt2, kimlik2, tasiyici2, simdi_ms=1789000009000,
                                   sessiz=True)
                bas2 = [b for u, _g, b in tasiyici2.istekler
                        if "uploadClickConversions" in u]
                iddia("(i1c) `developer token` YOKKEN kimlik DUSMUYOR, yukleme GECIYOR "
                      "ve `developer-token` basligi HIC OLUSMUYOR (bos baslik = 400)",
                      kimlik2 is not None and not eksik2 and rc2 == y.RC_YESIL
                      and bool(bas2) and "developer-token" not in bas2[0],
                      "kimlik=%s eksik=%s rc=%s baslik=%s"
                      % (kimlik2 is not None, eksik2, rc2,
                         sorted(bas2[0]) if bas2 else None))
            except Olculemedi as e:
                iddia("(i1c) jetonsuz fikstur kurulabildi", False, e)
            finally:
                if vt2 is not None:
                    vt2.kapat()

            kayit_metni = json.dumps([dict(r) for r in vt.sorgu(
                "SELECT siparis_no, son_hata FROM %s" % y.TABLO)])
            iddia("(i2) D1 kaydindaki `son_hata` metninde kimlik sirri YOK "
                  "(gizle() suzgeci)",
                  not [s for s in sirlar if s in kayit_metni], kayit_metni[:160])
            maske = y.gizle("token=%s son" % SAHTE_ORTAM["GOOGLE_ADS_REFRESH_TOKEN"],
                            kimlik.sirlar())
            iddia("(i3) gizle() sir degerini metinden SILIYOR",
                  SAHTE_ORTAM["GOOGLE_ADS_REFRESH_TOKEN"] not in maske
                  and "***" in maske, maske)

            # ── (b4) IDEMPOTENS'IN ASIL YUKU: `INSERT OR IGNORE` --------------
            # 🔴 BU BACAK ILK SURUMDE YOKTU ve kapi SAHTE GUVEN veriyordu: mutant
            # `INSERT OR IGNORE`i `INSERT OR REPLACE` yapinca kapi YESIL kaliyordu.
            # Sebep olculdu: aday sorgusu zaten yuklenmis siparisi `LEFT JOIN ...
            # IS NULL` ile ELIYOR -> ikinci `kuyrukla()` kosumunda INSERT'e HIC
            # GELINMIYOR, yani OR IGNORE'in yuku SINANMIYOR. Gercek risk suradadir:
            # aday suzgeci bir gun gevserse (ya da satir elle yeniden kuyruklanirsa)
            # OR REPLACE `yuklendi_mi=1`i SIFIRLAR ve AYNI DONUSUM IKINCI KEZ
            # Google'a gider (ciro iki katina cikmis gorunur). Bu yuzden ekleme SQL'i
            # DOGRUDAN, suzgeci ATLAYARAK kosturulur.
            aday0 = vt.sorgu(y.aday_sql().replace("AND k.siparis_no IS NULL", ""))
            _sebep, tekrar_kayit = y.kuyruk_satiri(aday0[0], 1789000008000)
            vt.calistir(y.ekleme_sql([tekrar_kayit]))
            s3 = vt.sorgu("SELECT * FROM %s" % y.TABLO)[0]
            iddia("(b4) YUKLENMIS satir icin ekleme SQL'i TEKRAR kossa bile "
                  "`yuklendi_mi` EZILMEDI (INSERT OR IGNORE) -> ikinci gonderim YOK",
                  s3["yuklendi_mi"] == 1 and len(y.bekleyenler(vt)) == 0
                  and vt.sorgu("SELECT COUNT(*) AS n FROM %s" % y.TABLO)[0]["n"] == 1,
                  "yuklendi=%s bekleyen=%d" % (s3["yuklendi_mi"], len(y.bekleyenler(vt))))

        try:
            bacaklar()
        except Exception as e:
            # 🔴 COKME "OLCULMEDI" DEGIL, KIRMIZIDIR — ama SESSIZ degil, ADIYLA.
            # Olculdu: iki oldurucu mutant (kimlik kolu oldurulmus · kuyruk tablosu
            # semadan silinmis) kapiyi HUKUMSUZ cokertiyordu; o halde gercek CI
            # kosumu izlenmeyen bir istisnayla duser ve hangi bacagin koptugu
            # GORUNMEZDI. Artik cokme de bir bacaktir ve adi basilir.
            iddia("KOSUM TAMAMLANDI — hicbir bacak ISTISNAYLA COKMEDI", False,
                  "%s: %s" % (type(e).__name__, str(e)[:140]))
        finally:
            vt.kapat()
    finally:
        shutil.rmtree(gec, ignore_errors=True)

    if not sessiz:
        print("REKLAM OCI KAPISI — gerceklesen satin alma -> Google Ads (OCI)")
        print("\n".join(ham))
        print("-" * 70)
        if kirmizi:
            print("SONUC: KIRMIZI ❌ — %d bacak kopuk: %s"
                  % (len(kirmizi), "; ".join(kirmizi)))
            print("  Hat koparsa hicbir sey patlamaz: siparis normal akar, musteri")
            print("  etkilenmez — yalnizca Google donusumu GORMEZ ve butce kor surulur.")
        else:
            print("SONUC: YESIL ✅ — kuyruk/gonderim yolunun dokuz bacagi da FIILEN kosturuldu.")
    return RC_KIRMIZI if kirmizi else RC_YESIL


# ══════════════════════════════════════════════════════════════════════════════
# KENDINI TEST — OLDURUCU MUTANTLAR (izole KOPYADA; canli govdeye DOKUNULMAZ)
# ══════════════════════════════════════════════════════════════════════════════
def _fikstur(gec, sema_donusum=None, yukleyici_donusum=None):
    """Gercek dosyalarin KOPYASI (istege bagli mutasyonla). (sema_yolu, yukleyici_yolu)."""
    sema_y = os.path.join(gec, "d1-sema.sql")
    yuk_y = os.path.join(gec, "reklam-oci-yukleyici.py")
    s = oku(SEMA_VARSAYILAN)
    u = oku(YUKLEYICI_VARSAYILAN)
    if sema_donusum:
        s = sema_donusum(s)
    if yukleyici_donusum:
        u = yukleyici_donusum(u)
    with open(sema_y, "w", encoding="utf-8") as f:
        f.write(s)
    with open(yuk_y, "w", encoding="utf-8") as f:
        f.write(u)
    return sema_y, yuk_y


def _tablo_sil(tablo):
    def d(metin):
        blok = create_blok(metin, tablo)
        if not blok:
            raise Olculemedi("MUTASYON CAPASI YOK: CREATE TABLE " + tablo)
        return metin.replace(blok, "")
    return d


def _capa_degistir(capa, yerine):
    """🔴 CAPA TEKIL OLMALI: iki kez gecen capa mutanti OLCUMSUZ birakir (harness bayat
    bildirir, 'yesil' demez) — [[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]."""
    def d(metin):
        if metin.count(capa) != 1:
            raise Olculemedi("MUTASYON CAPASI YOK/COK (%d): %s"
                             % (metin.count(capa), capa[:70]))
        return metin.replace(capa, yerine)
    return d


# Mutant capalari — hepsi yukleyicinin GERCEK govdesinde TEK kez gecer.
CAPA_PII = '        "currencyCode": satir["para_birimi"],'
MUT_PII = ('        "currencyCode": satir["para_birimi"],\n'
           '        "userIdentifiers": [{"hashedEmail": "abc123"}],')
CAPA_IDEMPOTENS = '        "INSERT OR IGNORE INTO %s (siparis_no, click_id, click_tur, '
MUT_IDEMPOTENS = '        "INSERT OR REPLACE INTO %s (siparis_no, click_id, click_tur, '
CAPA_KIMLIK = "    if kimlik is None:\n        return RC_KIMLIK_YOK,"
MUT_KIMLIK = "    if kimlik is None and False:\n        return RC_KIMLIK_YOK,"
CAPA_BEKLEYEN = "WHERE yuklendi_mi = 0 ORDER BY olusturuldu LIMIT %d"
MUT_BEKLEYEN = "ORDER BY olusturuldu LIMIT %d"
CAPA_HATA = ('    return ("UPDATE %s SET deneme_sayisi = deneme_sayisi + 1, son_hata = %s "\n'
             '            "WHERE siparis_no = %s;" % (TABLO, q((hata or "")[:400]), q(siparis_no)))')
MUT_HATA = ('    return ("UPDATE %s SET yuklendi_mi = 1, deneme_sayisi = deneme_sayisi + 1, '
            'son_hata = %s "\n'
            '            "WHERE siparis_no = %s;" % (TABLO, q((hata or "")[:400]), q(siparis_no)))')
CAPA_TUTAR = ('    return int(satir.get("tutar_kurus") or 0) + '
              'int(satir.get("kargo_kurus") or 0)')
MUT_TUTAR = '    return int(satir.get("tutar_kurus") or 0)'
CAPA_GIZLE = "            s = s.replace(sir, \"***\")"
MUT_GIZLE = "            s = s"
CAPA_KACIS = '    return "\'" + str(s).replace("\'", "\'\'") + "\'"'
MUT_KACIS = '    return "\'" + str(s) + "\'"'
CAPA_KALKAN = ("  ON r.ref = CASE WHEN json_valid(s.atif)\n"
               "                  THEN json_extract(s.atif, '$.ref') ELSE NULL END")
MUT_KALKAN = "  ON r.ref = json_extract(s.atif, '$.ref')"


def kendini_test():
    """Her iddianin YUK TASIDIGI, onu oldurmesi GEREKEN mutantin KIRMIZI yakmasiyla olculur.

    🔴 MUTASYON DAIMA IZOLE KOPYADA: canli agac dosyalari ACILMAZ bile (kopyalar
    tempfile'da uretilir ve kosum sonunda SILINIR). K0 kolu ters yonu olcer — ilgisiz
    bir degisiklik kapiyi KIRMIZI YAKMAMALI.
    """
    ham = ["REKLAM OCI KAPISI — KENDINI TEST (oldurucu mutantlar + K0)"]
    hata = 0
    vakalar = [
        ("P0 MUTASYONSUZ TABAN — gercek dosyalar", None, None, RC_YESIL),
        ("MU1 (a) govdeye MUSTERI VERISI eklendi (hashedEmail / userIdentifiers)",
         None, _capa_degistir(CAPA_PII, MUT_PII), RC_KIRMIZI),
        ("MU2 (b) idempotens oldu: INSERT OR IGNORE -> INSERT OR REPLACE",
         None, _capa_degistir(CAPA_IDEMPOTENS, MUT_IDEMPOTENS), RC_KIRMIZI),
        ("MU3 (c) kimlik yoklugu kolu oldu (kimliksiz de gondermeye calisir)",
         None, _capa_degistir(CAPA_KIMLIK, MUT_KIMLIK), RC_KIRMIZI),
        ("MU4 (b) bekleyen suzgeci oldu: yuklenmis satir TEKRAR gonderilir",
         None, _capa_degistir(CAPA_BEKLEYEN, MUT_BEKLEYEN), RC_KIRMIZI),
        ("MU5 (d) basarisiz yukleme `yuklendi_mi` ISARETLIYOR (sessiz kayip)",
         None, _capa_degistir(CAPA_HATA, MUT_HATA), RC_KIRMIZI),
        ("MU6 (e) tutar kargoyu DUSURUYOR (GA4 ile ayrisma)",
         None, _capa_degistir(CAPA_TUTAR, MUT_TUTAR), RC_KIRMIZI),
        ("MU7 (i) gizle() sir maskelemesi oldu",
         None, _capa_degistir(CAPA_GIZLE, MUT_GIZLE), RC_KIRMIZI),
        ("MU8 (j) SQL tek-tirnak kacisi oldu (d1-sync.py::q ile AYRISMA)",
         None, _capa_degistir(CAPA_KACIS, MUT_KACIS), RC_KIRMIZI),
        ("MU9 (k) `json_valid` kalkani SOKULDU (canlida 'malformed JSON' sinifi)",
         None, _capa_degistir(CAPA_KALKAN, MUT_KALKAN), RC_KIRMIZI),
        ("MU9b (f) `reklam_oci_kuyruk` KANONIK SEMADAN SILINDI",
         _tablo_sil("reklam_oci_kuyruk"), None, RC_KIRMIZI),
        # 🔴 BEKLENEN HUKUM OLCULMUS HALDIR, TEMENNI DEGIL: JOIN'in KARSI tarafi
        # semadan silinince fikstur KURULAMAZ -> kapi FAIL-CLOSED `OLCULEMEDI` der
        # (exit 3). Bu YESIL DEGILDIR ve dogru davranistir; "kirmizi bekliyordum"
        # diye gevsetilmez ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
        ("MU10 (h) `reklam_ref_gclid` semadan silindi -> fikstur kurulamaz (OLCULEMEDI)",
         _tablo_sil("reklam_ref_gclid"), None, RC_OLCULEMEDI),
        ("K0 KONTROL — ILGISIZ tablo (`talepler`) semadan silindi: kapi YESIL KALMALI "
         "(dar eksen; komsuyu kirmiziya yakmaz)",
         _tablo_sil("talepler"), None, RC_YESIL),
    ]

    for ad, sd, ud, beklenen in vakalar:
        gec = tempfile.mkdtemp(prefix="oci-mut-")
        try:
            try:
                sema_y, yuk_y = _fikstur(gec, sd, ud)
            except Olculemedi as e:
                hata += 1
                ham.append("  ❌ HARNESS BAYAT: %s -> %s" % (ad, e))
                continue
            try:
                rc = kapi(sema_y, yuk_y, sessiz=True)
            except Exception as e:
                # 🔴 COKME "KIRMIZI" SAYILMAZ — HARNESS BAYATLIGIDIR.
                # Olculdu (bu kapinin ilk kendini-test kosumu): izole kopya
                # `tools/d1-sync.py`yi bulamayip cokunce SEKIZ oldurucu mutantin
                # SEKIZI de AYNI ILGISIZ sebeple "kirmizi" yandi ve mutant kaniti
                # SAHTE oldu. Cokmeyi kirmiziya saymak o sahteligi KUTSAR
                # ([[mutant-kopyasi-cokerse-izin-okunur]]) -> burada kosum BAYAT
                # ilan edilir ve kendini-test KIRMIZI doner.
                hata += 1
                ham.append("  ❌ HARNESS BAYAT (mutant kopya coktu): %s -> %s"
                           % (ad, str(e)[:110]))
                continue
            if rc == beklenen:
                ham.append("  ✅ %s -> rc=%d" % (ad, rc))
            else:
                hata += 1
                ham.append("  ❌ %s -> rc=%d (beklenen %d)" % (ad, rc, beklenen))
        finally:
            shutil.rmtree(gec, ignore_errors=True)
            ham.append("     (kopya silindi: %s var mi -> %s)"
                       % (os.path.basename(gec), os.path.exists(gec)))

    print("\n".join(ham))
    print("-" * 70)
    if hata:
        print("SONUC: KIRMIZI ❌ — %d vaka beklenen hukmu vermedi" % hata)
        return RC_KIRMIZI
    print("SONUC: YESIL ✅ (kendini test) — %d vaka; her oldurucu mutant KIRMIZI, "
          "ilgisiz degisiklik YESIL." % len(vakalar))
    return RC_YESIL


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true", dest="kendini",
                    help="oldurucu mutantlar + dar eksen (K0) kontrolu")
    ap.add_argument("--sema", default=SEMA_VARSAYILAN)
    ap.add_argument("--yukleyici", default=YUKLEYICI_VARSAYILAN)
    a = ap.parse_args()
    try:
        if a.kendini:
            return kendini_test()
        return kapi(a.sema, a.yukleyici)
    except Olculemedi as e:
        print("OLCULEMEDI: %s" % e)
        return RC_OLCULEMEDI


if __name__ == "__main__":
    sys.exit(main())
