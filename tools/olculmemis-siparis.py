#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCULMEMIS SIPARIS TESPITI — odenmis ama Purchase olcumu GITMEMIS siparisleri bulur.

    python3 tools/olculmemis-siparis.py                 # varsayilan esiklerle rapor
    python3 tools/olculmemis-siparis.py --ayrinti        # her siparisin sinifini/sebebini goster
    python3 tools/olculmemis-siparis.py --esik 2026-07-20T01:24:38Z   # iki esigi birden ez
    python3 tools/olculmemis-siparis.py --son 500        # daha genis pencere (varsayilan 200)

CIKIS KODU: kesin kayip varsa 1, yoksa 0 (kapi olarak kullanilabilir).
  ⚠️ build.py'ye / deploy'a BAGLANMAZ — bagimsiz tespit araci; yayini kirmaz.

*** NEDEN VAR ***
`havale-bekliyor -> odendi` gecisi shop/KURULUM.md'deki YEDEK HAM SQL komutuyla yapilirsa
worker kodu HIC calismaz -> Meta CAPI + GA4'e Purchase GITMEZ ve geriye hicbir iz kalmaz.
O ciro reklam raporlarinda GORUNMEZ, Meta "bu reklam satmiyor" diye YANLIS ogrenir. Satis
kaydi ve uretim akisi etkilenmedigi icin kimse fark etmez — bu arac o sessiz bosluga bakar.

*** KAPSAM = SADECE OKUMA ***
D1'e YAZMAZ, Meta/GA4'e olay GONDERMEZ, siparis durumunu DEGISTIRMEZ. wrangler'a giden tek
yol `wrangler_sorgu()`; SELECT disinda bir ifade (ya da ';' / yazma anahtar kelimesi)
gecerse calismadan ValueError firlatir. PII kolonu (ad/tel/eposta/adres) HIC secilmez.

*** OLCUM IZLERI (sema: tools/d1-sema.sql · kod: shop/src/yonet.js + shop/src/index.js) ***
  HAVALE yolu : /api/shop/yonet/durum 'odendi'e cekince durum_gecmisi'ne {"d":"odendi",
                "z":ISO,"o":1} yazar. `o:1` = "Purchase olcumu DENENDI".
  KART yolu   : /api/shop/donus retrieve OK olunca AYNI atomik UPDATE'te hem
                iyzico_odeme_id'yi hem durum_gecmisi'ne AYNI {"o":1} izini yazar ve
                olcumGonder() cagirir. Yani iki akis TEK DESENDE bulusur.
  KART ICIN IKI SINYAL DE KABUL EDILIR (VEYA):
    1) DOGRUDAN iz {"o":1}  — 20 Tem sonrasi kart siparisleri (index.js gecmiseEkle).
    2) DOLAYLI  iyzico_odeme_id DOLU — daha ESKI kart siparisleri. Geriye donuk iz
       YAZILMADI (D1'e yazmak bu aracin kapsami DISI + gecmisi tahrif etmek yanlis),
       o yuzden eski satirlarda tek kanit budur.
  ⚠️ Dolayli sinyal KIRILGAN: iyzico paymentId'yi bos dondurse iyzico_odeme_id de bos kalir.
  Bu yuzden ONCE dogrudan iz aranir; dolayli sinyal yalnizca geriye donuk uyum icindir.
  Kart siparisi 'odendi'ye BASKA yoldan gecemez: /yonet IZINLI tablosunda 'odendi' hedefine
  yalniz 'havale-bekliyor'dan gecilir. Yani kart + 'odendi' + iki sinyal de YOK = worker
  disi (ham SQL) mudahale isareti.

*** IZ "DENENDI" DEMEK, "META ALDI" DEMEK DEGIL (bu arac bunu ISPATLAYAMAZ) ***
`o:1` gonderim SONUCUNDAN ONCE, ayni atomik UPDATE icinde yazilir. olcum.js su meşru
hallerde olayi GONDERMEDEN atlayabilir ve iz yine "1" kalir:
    atlandi:"secret-yok"      META/GA4 anahtari tanimli degil
    atlandi:"user_data-bos"   riza kapisi (fbp yok) -> Meta'ya kimlik gonderilmez
    atlandi:"pencere-disi"    olay 7 gunden eski -> Meta reddeder
Bunlar D1'den AYIRT EDILEMEZ; kanit yalnizca Cloudflare Logs'taki `olcum {...}` satirinda
(kod / events_received / fbtrace_id / atlandi). Bu yuzden izli siparis "KAYIP" DAMGASI
YEMEZ — raporun sonundaki "AYIRT EDILEMEYEN" bolumunde acikca soylenir.
TEK istisna D1'den hesaplanabilir: havale onayi siparis tarihinden 7 GUNDEN gec yapildiysa
Meta olayi kesin reddeder (pencere-disi) — ayri bir UYARI kovasinda raporlanir, GA4 ciroyu
yine kaydettigi icin "kayip" sayilmaz.

*** KANAL SUZGECI — site DISI siparis "kayip" DEGILDIR (yanlis pozitif nobeti) ***
`siparisler.kanal` (DEFAULT 'site') site disi bir uc oldugunu soyler (or. WhatsApp siparis
ucu). O akista tarayici YOKTUR: GA4 client_id / Meta fbp uretilmez, /donus da /yonet/durum
da CALISMAZ -> durum_gecmisi'nde {"o":1} izi HIC OLMAZ. Kolon sorguya girmeseydi bu
siparisler bu araca izsiz "odenmis" gorunur ve HEPSI "olculmemis ciro" alarmina duserdi:
gercek kayiplar sahte alarmlarin arasinda BOGULUR (alarm yorgunlugu = alarmi kapatmak).
  KURAL: kanal ACIKCA site disi ise sinif OLCUM_BEKLENMEZ — kayip SAYILMAZ ama raporda
  AYRI ve SAYILI basilir (sessizce yutmak yeni bir korluk uretirdi: o kanalin cirosunun
  olculup olculmedigi bu araca gorunmez KALIR, ama en azindan NE KADAR oldugu yazar).
  ⚠️ Muafiyet YALNIZ acik degerden dogar: kolon YOKSA (goc kosmadi) ya da deger BOS/NULL
  ise satir SITE kabul edilir ve eskisi gibi denetlenir — "bilmiyorum" bir kaybi GIZLEYEMEZ.
  Kolon henuz canli tabloda olmayabilir (goc `d1-sync.py --sema` ile gelir): SELECT once
  kanal ile denenir, D1 "no such column: kanal" derse kolonsuz SELECT'e DUSULUR (arac
  patlamaz) ve bu hal raporda GURULTULU yazilir.

*** ESIK TARIHI (yanlis pozitif ayiklama) ***
Olcum kodu main'e girmeden ONCE odenmis siparisler dogal olarak izsizdir; onlari "kayip"
saymak PANIGE yol acar. Iki ayri esik var, cunku iki akisin olcumu ayri tarihlerde girdi:
  KART   : f2876024 "Reklam ROI olcumu: sunucu-tarafi Purchase" 2026-07-18 12:48 +03
  HAVALE : edf9d198 "Olcum saglamlastirma: ... havale Purchase"  2026-07-20 04:24 +03
Esik = ilgili kodun MAIN'E GIRDIGI an (deploy ani DEGIL — deploy Okan kapisi, zamani
betikten bilinemez). Merge ile deploy arasindaki siparis GERCEKTEN olculmemistir, o yuzden
esigi merge aninda tutmak dogru tarafta hata yapar; ama sebep "ham SQL" degil "worker henuz
yayinlanmamis" olabilir — bu yuzden arac "ham SQL kullanildi" DEMEZ, "olcum izi yok" der.

⚠️ KART ESIGI, kart yoluna DOGRUDAN iz eklenmesiyle DEGISMEDI (bilincli karar):
sinif kapisi iki sinyali VEYA'lar; dolayli sinyal (iyzico_odeme_id) ESIK_KART'tan beri
kesintisiz vardir, dolayisiyla iz kodunun girdigi tarihe cekilecek YENI bir esige gerek
YOK. Esigi ileri almak, iki tarih arasinda GERCEKTEN olculmemis kart siparislerini
"esik-oncesi" kovasina saklayarak KAYBI GIZLERDI — yanlis tarafta hata olurdu.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
# DB'yi ADIYLA cagiririz (UUID DEGIL). NEDEN (T5 olcumu, 2026-07-22): `npx wrangler@4` YUZER
# pin; CI o an 4.86.0'a cozulunce `d1 execute <UUID>` argumani AD olarak aranir ->
# "Couldn't find DB with name '<uuid>'" exit 1. AD "pruvo-katalog" 4.86.0 VE 4.112.0'da
# (+ bos dizinde) exit 0 -> surumden BAGIMSIZ. Bu betik su an yalniz YEREL kosuyor (CI'da
# degil) ama ayni surum ayrismasina acikti; ada gecirildi (tools/d1-sync.py ile ayni desen).
# UUID sabiti (DB) referans olarak kalir.
DB = "3d99d15e-2342-4c23-9c2d-cb266f19c1ee"  # pruvo-katalog (UUID — referans)
DB_AD = "pruvo-katalog"  # execute yolunda KULLANILAN tanimlayici (surumden bagimsiz)

# --- ESIKLER (yukaridaki "ESIK TARIHI" bolumunun gerekcesi) --------------------
ESIK_KART = "2026-07-18T09:48:34Z"    # f2876024 (+03 12:48:34)
ESIK_HAVALE = "2026-07-20T01:24:38Z"  # edf9d198 (+03 04:24:38)

# Meta CAPI geriye-donuk penceresi (shop/src/olcum.js META_GERIYE_PENCERE_SN ile AYNI).
META_GERIYE_PENCERE_SN = 7 * 24 * 3600

# 'odendi' ve ONDAN TURETILEN durumlar: para alinmis sayilir, olcum beklenir.
# 'iptal' HARIC (ciro degil), 'bekliyor'/'havale-bekliyor'/'basarisiz'/'incele' HARIC
# (henuz odenmedi ya da supheli — olcum beklenmez).
ODENMIS_DURUMLAR = ("odendi", "uretimde", "kargolandi", "tamamlandi")

# PII kolonu YOK — rapor icin gereken teknik alanlar.
KOLONLAR = (
    "siparis_no", "tarih", "durum", "odeme_yontemi",
    "tutar_kurus", "kargo_kurus", "durum_gecmisi", "iyzico_odeme_id", "token",
)

# KANAL kolonu AYRI tutulur: canli tabloda HENUZ OLMAYABILIR (goc `d1-sync.py --sema` ile
# gelir). Kosulsuz KOLONLAR'a konsaydi goc oncesi her kosum "no such column: kanal" ile
# duserdi — tespit araci goc penceresi boyunca OLU kalirdi. Bkz. siparisleri_oku().
KOLON_KANAL = "kanal"

# Site DISI kanalin kanonik olmayan degeri. Kolonun DEFAULT'u 'site'; eski satirlar da
# (goc oncesi acilmis) bu degeri alir.
KANAL_SITE = "site"

# Siniflar
KAYIP = "kayip"                  # odenmis, esik SONRASI, olcum izi YOK -> ciro olculmedi
ESIK_ONCESI = "esik-oncesi"      # olcum kodu yokken odenmis -> tarihsel, kayip SAYILMAZ
OLCULDU = "olculdu"              # olcum DENENDI (ulastigi garanti degil)
# Site DISI kanal (or. WhatsApp siparis ucu): bu akista Purchase olcumu HIC BEKLENMEZ,
# izsizligi bir ARIZA DEGILDIR. Kayip SAYILMAZ; raporda AYRI ve SAYILI basilir.
OLCUM_BEKLENMEZ = "olcum-beklenmez"

try:
    from zoneinfo import ZoneInfo
    YEREL_TZ = ZoneInfo("Europe/Istanbul")
except Exception:  # pragma: no cover
    YEREL_TZ = timezone(timedelta(hours=3))


# ------------------------------------------------------------------ salt-okunur kapi

# Yazma niyeti tasiyan her SQL anahtar kelimesi. Kelime sinirli (\b) — "UPDATED_AT" gibi
# kolon adi yanlislikla yakalanmasin diye degil, tam tersi: yakalamak ISTEDIGIMIZ tek sey
# ifadenin kendisi. Suphede REDDET (fail-closed).
YAZMA_SOZCUKLERI = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|"
    r"PRAGMA|VACUUM|BEGIN|COMMIT|ROLLBACK|REINDEX|ANALYZE)\b",
    re.IGNORECASE,
)


def salt_okunur_dogrula(sql):
    """SELECT disinda HICBIR sey gecirmeyen kapi. Ihlalde ValueError.

    Uc katman: (1) SELECT ile baslamali, (2) ';' yasak (ikinci ifade eklenemesin),
    (3) yazma anahtar kelimesi yasak. Ucu birden gerekli: tek basina "SELECT ile
    baslar" kontrolu "SELECT 1; DROP TABLE x" zincirini gecirir.
    """
    s = (sql or "").strip()
    if not s.upper().startswith("SELECT"):
        raise ValueError("sadece SELECT calistirilir, gelen: %r" % sql)
    if ";" in s:
        raise ValueError("noktali virgul yasak (cok ifadeli SQL): %r" % sql)
    m = YAZMA_SOZCUKLERI.search(s)
    if m:
        raise ValueError("yazma ifadesi reddedildi (%s): %r" % (m.group(0), sql))
    return s


def sql_sorgu(son, kanal=True):
    """Odenmis siparisleri seçen SELECT'i uretir (PII kolonu YOK).

    kanal=True  -> `kanal` kolonu da secilir (goc KOSMUS canli tablo).
    kanal=False -> kolonsuz eski SELECT (goc KOSMAMIS tablo; ayni sorgu 'no such column'
                   ile duserdi). Iki bicim de AYNI fonksiyondan cikar ki ikisi ayrisamasin.
    """
    son = max(int(son), 1)
    durumlar = ", ".join("'%s'" % d for d in ODENMIS_DURUMLAR)
    kolonlar = list(KOLONLAR) + ([KOLON_KANAL] if kanal else [])
    return ("SELECT %s FROM siparisler WHERE durum IN (%s) ORDER BY id DESC LIMIT %d"
            % (", ".join(kolonlar), durumlar, son))


# "kolon yok" hatasini AYIRT EDEN tek kural. Baska HER hata (ag/auth/sozdizimi) fail-loud
# kalmali: hepsini "kolon yok" sayan bir yedek yol, gercek arizayi eski davranisa DUSEREK
# gizlerdi (sessiz hata). Bu yuzden kolon ADI da eslesmek ZORUNDA.
def kolon_yok_mu(ham, kolon):
    """D1/SQLite ciktisi TAM OLARAK bu kolonun yoklugundan mi sikayetci?"""
    return re.search(r"no such column:?\s*(?:\w+\.)?%s\b" % re.escape(kolon),
                     ham or "", re.IGNORECASE) is not None


def wrangler_dene(sql):
    """wrangler d1 execute --remote --json — HATAYI YUTMADAN dondur.

    Doner: (basarili_mi, satirlar, ham_cikti). Kimlik hatasi KALICI kabul edilir ve
    burada sys.exit ile biter (yedek SELECT denemek anlamsiz olurdu).
    """
    sql = salt_okunur_dogrula(sql)
    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB_AD,
             "--remote", "--json", "--command", sql]
    p = subprocess.run(komut, cwd=SHOP, capture_output=True, text=True)
    ham = (p.stdout or "") + (p.stderr or "")

    if "code: 10000" in ham or "Authentication error" in ham:
        sys.exit(
            "D1 KIMLIK HATASI (code 10000) — token/oturum D1'e erisemiyor.\n"
            "  Yerelde 'npx wrangler login' ile giris yapilmis olmali\n"
            "  (tools/d1-sync.py + tools/siparisler.py ile ayni gereksinim)."
        )
    i = p.stdout.find("[")
    if i == -1:
        return False, [], ham
    try:
        veri = json.loads(p.stdout[i:])
    except (ValueError, TypeError):
        return False, [], ham
    if not veri or not veri[0].get("success", False):
        return False, [], ham
    return True, (veri[0].get("results", []) or []), ham


def wrangler_sorgu(sql):
    """wrangler d1 execute (SALT-OKUNUR kapidan gecerek). Hatada FAIL-LOUD."""
    ok, satirlar, ham = wrangler_dene(sql)
    if not ok:
        sys.exit("wrangler sorgusu basarisiz:\n" + ham[-2000:])
    return satirlar


def siparisleri_oku(son):
    """Odenmis siparisleri oku. Doner: (satirlar, kanal_kolonu_var_mi).

    KOLON HENUZ YOKKEN DE CALISIR: once kanal'li SELECT denenir; D1 TAM OLARAK
    "no such column: kanal" derse kolonsuz SELECT'e dusulur (ESKI DAVRANIS korunur).
    Diger her hata fail-loud — yedek yol bir ariza ortu DEGILDIR.
    """
    ok, satirlar, ham = wrangler_dene(sql_sorgu(son, kanal=True))
    if ok:
        return satirlar, True
    if kolon_yok_mu(ham, KOLON_KANAL):
        return wrangler_sorgu(sql_sorgu(son, kanal=False)), False
    sys.exit("wrangler sorgusu basarisiz:\n" + ham[-2000:])


# ------------------------------------------------------------------ zaman / bicim

def iso_sn(iso):
    """ISO 8601 -> epoch saniye. Bozuk/bossa None (cagiran karar verir)."""
    if not iso:
        return None
    s = str(iso)
    s = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def yerel_saat(iso_utc):
    sn = iso_sn(iso_utc)
    if sn is None:
        return str(iso_utc or "?")
    return datetime.fromtimestamp(sn, YEREL_TZ).strftime("%d.%m.%Y %H:%M")


def tl(kurus):
    try:
        lira = (kurus or 0) / 100.0
    except TypeError:
        lira = 0.0
    s = "{:,.2f}".format(lira)
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


# ------------------------------------------------------------------ iz cozumleme

def gecmis_coz(gecmis_json):
    """durum_gecmisi JSON -> liste. Bos/bozuk -> [] (rapor araci, satir yuzunden durmaz)."""
    try:
        g = json.loads(gecmis_json or "[]")
    except (ValueError, TypeError):
        return []
    return g if isinstance(g, list) else []


def olcum_izi_var(gecmis):
    """durum_gecmisi'nde {"o":1} var mi? (havale yolunun 'DENENDI' izi)"""
    return any(isinstance(k, dict) and k.get("o") == 1 for k in gecmis)


def odendi_ani(satir):
    """'odendi'ye gecis ISO damgasi; gecmiste yoksa siparis tarihi (+ 'tahmini' bayragi).

    Doner: (iso, kesin_mi). kesin_mi=False -> gecis ani BILINMIYOR, siparis tarihine
    dusuldu; esik karsilastirmasi bu satirda tahmindir (raporda soylenir).
    """
    for k in gecmis_coz(satir.get("durum_gecmisi")):
        if isinstance(k, dict) and k.get("d") == "odendi" and k.get("z"):
            return k["z"], True
    return satir.get("tarih"), False


def tahsilat(satir):
    return (satir.get("tutar_kurus") or 0) + (satir.get("kargo_kurus") or 0)


def kanal_deger(satir):
    """Satirin ACIK kanal degeri (kucuk harf) ya da None.

    None = "BILINMIYOR": kolon SELECT'e girmedi (goc kosmamis) YA DA deger bos/NULL.
    Bilinmeyen kanal SITE gibi denetlenir — muafiyet YALNIZ acik bir degerden dogar,
    yoksa bos bir kolon tum kayiplari sessizce affederdi.
    """
    if KOLON_KANAL not in satir:
        return None
    d = (satir.get(KOLON_KANAL) or "").strip().lower()
    return d or None


# ------------------------------------------------------------------ siniflandirma

def siniflandir(satir, esik_kart=ESIK_KART, esik_havale=ESIK_HAVALE):
    """Tek siparisi sinifla. Doner: dict(sinif, sebep, an, an_kesin, meta_penceresi_disi).

    KART   : iz = durum_gecmisi'nde {"o":1} (DOGRUDAN) VEYA iyzico_odeme_id DOLU
             (DOLAYLI, eski satirlar icin). Ikisi de yoksa /donus HIC calismamistir.
    HAVALE : iz = durum_gecmisi'nde {"o":1} (/yonet/durum calisti).
    Esik ONCESI her sey ESIK_ONCESI (olcum kodu henuz yoktu) — izin yoklugu normal.
    KANAL  : acikca site DISI ise OLCUM_BEKLENMEZ (esikten de izden de ONCE gelir —
             o akista olcum kodu hic kosmaz, esik karsilastirmasi anlamsizdir).
    """
    yontem = (satir.get("odeme_yontemi") or "kart").strip() or "kart"
    an, an_kesin = odendi_ani(satir)
    an_sn = iso_sn(an)
    esik = esik_havale if yontem == "havale" else esik_kart
    esik_sn = iso_sn(esik)
    kanal = kanal_deger(satir)

    # KANAL KAPISI — EN BASTA. Site disi uctan gelen sipariste tarayici yoktur; Purchase
    # olcumu ne DENENIR ne de BEKLENIR. Bu satirlari esik/iz mantigina sokmak, izsizligi
    # "kayip" diye damgalamak demektir (yanlis pozitif -> alarm yorgunlugu).
    if kanal is not None and kanal != KANAL_SITE:
        return {"sinif": OLCUM_BEKLENMEZ, "an": an, "an_kesin": an_kesin,
                "meta_penceresi_disi": False, "kanal": kanal,
                "sebep": "kanal=%s (site DISI) — bu akista tarayici/olcum kodu yok, "
                         "iz BEKLENMEZ" % kanal}

    # Meta 7-gun penceresi: odeme ani (siparis tarihi) ile onay ani arasi > 7 gun ise
    # Meta olayi KESIN reddeder (olcum.js pencere-disi). D1'den hesaplanabilen tek
    # "gonderildi ama ulasmadi" hali.
    tarih_sn = iso_sn(satir.get("tarih"))
    pencere_disi = bool(
        yontem == "havale" and an_sn and tarih_sn
        and (an_sn - tarih_sn) > META_GERIYE_PENCERE_SN
    )

    if an_sn is None or esik_sn is None or an_sn < esik_sn:
        return {"sinif": ESIK_ONCESI, "an": an, "an_kesin": an_kesin,
                "meta_penceresi_disi": False, "kanal": kanal,
                "sebep": "olcum kodu esikten (%s) once — iz beklenmez" % esik}

    if yontem == "havale":
        if olcum_izi_var(gecmis_coz(satir.get("durum_gecmisi"))):
            return {"sinif": OLCULDU, "an": an, "an_kesin": an_kesin,
                    "meta_penceresi_disi": pencere_disi, "kanal": kanal,
                    "sebep": 'durum_gecmisi izi {"o":1} — olcum DENENDI'}
        return {"sinif": KAYIP, "an": an, "an_kesin": an_kesin,
                "meta_penceresi_disi": pencere_disi, "kanal": kanal,
                "sebep": 'havale onayi worker disindan yapilmis: {"o":1} izi YOK'}

    # kart — ONCE dogrudan iz, sonra (eski satirlar icin) dolayli sinyal.
    if olcum_izi_var(gecmis_coz(satir.get("durum_gecmisi"))):
        return {"sinif": OLCULDU, "an": an, "an_kesin": an_kesin,
                "meta_penceresi_disi": False, "kanal": kanal,
                "sebep": 'durum_gecmisi izi {"o":1} — /donus calisti, olcum DENENDI'}
    if (satir.get("iyzico_odeme_id") or "").strip():
        return {"sinif": OLCULDU, "an": an, "an_kesin": an_kesin,
                "meta_penceresi_disi": False, "kanal": kanal,
                "sebep": "iyzico_odeme_id dolu (DOLAYLI iz; iz kodu oncesi kart siparisi)"
                         " — /donus calisti, olcum DENENDI"}
    return {"sinif": KAYIP, "an": an, "an_kesin": an_kesin,
            "meta_penceresi_disi": False, "kanal": kanal,
            "sebep": "kart siparisi 'odendi' ama ne {\"o\":1} izi ne iyzico_odeme_id var"
                     " — /donus'tan gecmemis"}


# ------------------------------------------------------------------ rapor

def rapor(satirlar, esik_kart=ESIK_KART, esik_havale=ESIK_HAVALE, ayrinti=False,
          kanal_kolonu=None):
    """(metin, ozet) uretir. ozet['kayip_adet'] cikis kodunu belirler.

    kanal_kolonu: SELECT'te kanal kolonu VAR miydi (True/False)? None = bilinmiyor
    (dogrudan cagri / eski test). Rapor bunu ACIKCA basar: kolon yokken TUM satirlar
    site kabul edilmistir ve site disi kanallar bu araca GORUNMEZ.
    """
    kovalar = {KAYIP: [], ESIK_ONCESI: [], OLCULDU: [], OLCUM_BEKLENMEZ: []}
    pencere_uyari = []
    tahmini_an = []
    for s in satirlar:
        k = siniflandir(s, esik_kart, esik_havale)
        kovalar[k["sinif"]].append((s, k))
        if k["meta_penceresi_disi"] and k["sinif"] not in (ESIK_ONCESI, OLCUM_BEKLENMEZ):
            pencere_uyari.append((s, k))
        if not k["an_kesin"] and k["sinif"] == KAYIP:
            tahmini_an.append(s.get("siparis_no"))

    kayip_ciro = sum(tahsilat(s) for s, _ in kovalar[KAYIP])
    onceki_ciro = sum(tahsilat(s) for s, _ in kovalar[ESIK_ONCESI])
    beklenmez_ciro = sum(tahsilat(s) for s, _ in kovalar[OLCUM_BEKLENMEZ])
    # Kanal DAGILIMI: hangi site-disi kanaldan kac siparis / ne kadar ciro. "Kayip degil"
    # demek "gorunmez" demek DEGIL — sayilar burada, kimse "haberim yoktu" diyemesin.
    kanal_dagilim = {}
    for s, k in kovalar[OLCUM_BEKLENMEZ]:
        ad = k.get("kanal") or "?"
        adet, ciro = kanal_dagilim.get(ad, (0, 0))
        kanal_dagilim[ad] = (adet + 1, ciro + tahsilat(s))

    L = []
    A = L.append
    A("=" * 78)
    A("OLCULMEMIS SIPARIS TESPITI — odenmis ama Purchase olcumu izi olmayan siparisler")
    A("=" * 78)
    A("Esik (kart)   : %s   [f2876024 kart Purchase main'e girdi]" % esik_kart)
    A("Esik (havale) : %s   [edf9d198 havale Purchase main'e girdi]" % esik_havale)
    A("Incelenen odenmis siparis: %d  (durum: %s)"
      % (len(satirlar), ", ".join(ODENMIS_DURUMLAR)))
    if kanal_kolonu is True:
        A("Kanal kolonu  : VAR — site DISI kanallar AYRI siniflanir (asagida sayili).")
    elif kanal_kolonu is False:
        A("Kanal kolonu  : YOK (goc `d1-sync.py --sema` henuz kosmadi) — TUM satirlar")
        A("                SITE kabul edildi. Site disi bir uc (or. WhatsApp siparis)")
        A("                zaten olusmus olsaydi bu rapor onu KAYIP diye damgalardi.")
    else:
        A("Kanal kolonu  : BILINMIYOR (rapor dogrudan cagrildi) — acik kanal degeri")
        A("                tasimayan satirlar SITE kabul edildi.")
    A("")
    A("-" * 78)
    A("KAYIP — esik SONRASI odenmis, olcum izi YOK (ciro Meta/GA4'te GORUNMUYOR)")
    A("-" * 78)
    if not kovalar[KAYIP]:
        A("  (yok)")
    else:
        A("  %-24s %-17s %14s  %-7s" % ("SIPARIS NO", "ODENDI (yerel)", "TAHSILAT", "YONTEM"))
        for s, k in kovalar[KAYIP]:
            A("  %-24s %-17s %14s  %-7s%s"
              % (s.get("siparis_no") or "?", yerel_saat(k["an"]), tl(tahsilat(s)),
                 s.get("odeme_yontemi") or "?", "" if k["an_kesin"] else "  (an tahmini)"))
            A("      sebep: %s" % k["sebep"])
    A("")
    A("  >>> TOPLAM KAYIP: %d siparis · %s <<<" % (len(kovalar[KAYIP]), tl(kayip_ciro)))
    A("")

    # ── OLCUM BEKLENMEZ (site DISI kanal) — kayip DEGIL ama GORUNMEZ de degil ──────
    A("-" * 78)
    A("OLCUM BEKLENMEZ — site DISI kanal (or. WhatsApp siparis ucu). O akista tarayici")
    A("YOK: GA4 client_id / Meta fbp uretilmez, /donus + /yonet/durum kosmaz -> {\"o\":1}")
    A("izi HIC olusmaz. Izsizlik ARIZA DEGIL; bu satirlar KAYIP SAYILMAZ.")
    A("⚠️ Ama bu 'olculdu' de DEMEK DEGIL: bu kanalin cirosunun Meta/GA4'e gidip gitmedigi")
    A("   BU ARACIN KAPSAMI DISI. Sayilar gizlenmesin diye asagida ayri basilir.")
    A("-" * 78)
    if not kovalar[OLCUM_BEKLENMEZ]:
        A("  (yok)")
    else:
        for ad in sorted(kanal_dagilim):
            adet, ciro = kanal_dagilim[ad]
            A("  kanal %-12s : %d siparis · %s" % (ad, adet, tl(ciro)))
        A("")
        A("  %-24s %-17s %14s  %-7s %s"
          % ("SIPARIS NO", "ODENDI (yerel)", "TAHSILAT", "YONTEM", "KANAL"))
        for s, k in kovalar[OLCUM_BEKLENMEZ]:
            A("  %-24s %-17s %14s  %-7s %s"
              % (s.get("siparis_no") or "?", yerel_saat(k["an"]), tl(tahsilat(s)),
                 s.get("odeme_yontemi") or "?", k.get("kanal") or "?"))
    A("  ara toplam: %d siparis · %s"
      % (len(kovalar[OLCUM_BEKLENMEZ]), tl(beklenmez_ciro)))
    A("")

    if pencere_uyari:
        A("-" * 78)
        A("UYARI — izi VAR ama Meta 7 GUNLUK PENCERESI disinda (Meta REDDETTI; GA4 ciroyu")
        A("aldi, yalniz saat kaydi kaydi). D1'den hesaplanabilen tek 'ulasmadi' hali.")
        A("-" * 78)
        for s, k in pencere_uyari:
            A("  %-24s siparis %s -> onay %s · %s"
              % (s.get("siparis_no") or "?", yerel_saat(s.get("tarih")),
                 yerel_saat(k["an"]), tl(tahsilat(s))))
        A("")

    A("-" * 78)
    A("ESIK ONCESI — olcum kodu main'e girmeden once odenmis; izsizligi NORMAL, kayip")
    A("SAYILMAZ (tarihsel; geri donuk gonderilemez — Meta 7 gun penceresi zaten kapali).")
    A("-" * 78)
    if not kovalar[ESIK_ONCESI]:
        A("  (yok)")
    else:
        for s, k in kovalar[ESIK_ONCESI]:
            A("  %-24s %-17s %14s  %-7s"
              % (s.get("siparis_no") or "?", yerel_saat(k["an"]), tl(tahsilat(s)),
                 s.get("odeme_yontemi") or "?"))
    A("  ara toplam: %d siparis · %s" % (len(kovalar[ESIK_ONCESI]), tl(onceki_ciro)))
    A("")

    if ayrinti and kovalar[OLCULDU]:
        A("-" * 78)
        A("OLCUM DENENDI (iz var) — ULASTIGI GARANTI DEGIL, asagiya bak")
        A("-" * 78)
        for s, k in kovalar[OLCULDU]:
            A("  %-24s %-17s %14s  %-7s | %s"
              % (s.get("siparis_no") or "?", yerel_saat(k["an"]), tl(tahsilat(s)),
                 s.get("odeme_yontemi") or "?", k["sebep"]))
        A("")

    A("-" * 78)
    A("AYIRT EDILEMEYEN (bu arac ISPATLAYAMAZ — 'kayip' diye damgalanmadi)")
    A("-" * 78)
    A("  · Iz {\"o\":1} / iyzico_odeme_id 'DENENDI' demek, 'Meta/GA4 ALDI' DEMEK DEGIL.")
    A("    olcum.js su mesru hallerde gondermeden atlar, iz yine kalir:")
    A("      atlandi:\"secret-yok\"     META/GA4 anahtari tanimsiz")
    A("      atlandi:\"user_data-bos\"  riza kapisi: fbp yok -> Meta'ya kimlik gitmez")
    A("      atlandi:\"pencere-disi\"   olay 7 gunden eski")
    A("    Ayrica HTTP 4xx/5xx ya da ag hatasi da izi degistirmez (fire-and-forget).")
    A("  · KANIT TEK YERDE: Cloudflare Logs > `olcum {...}` satirlari")
    A("    (kod / events_received / fbtrace_id / atlandi). [observability] acik.")
    A("  · 'olculdu' kovasindaki %d siparisin KACINA gercekten ulasildi: BILINMIYOR."
      % len(kovalar[OLCULDU]))
    A("  · Site DISI kanaldaki %d siparisin (%s) cirosu Meta/GA4'e GITTI MI: bu arac"
      % (len(kovalar[OLCUM_BEKLENMEZ]), tl(beklenmez_ciro)))
    A("    SOYLEYEMEZ — o akisin olcumu (varsa) BASKA bir kodda; burada yalniz SAYILIR.")
    if kanal_kolonu is False:
        A("  · KANAL KOLONU YOK: site disi kanal bu kosumda AYIRT EDILEMEDI (goc kosunca")
        A("    tekrar kos — bugunku 'kayip' sayisi o kanali da iceriyor olabilir).")
    if tahmini_an:
        A("  · 'odendi' gecis ani durum_gecmisi'nde YOK, siparis tarihine dusuldu: %s"
          % ", ".join(tahmini_an))
    A("")
    A("=" * 78)
    if kovalar[KAYIP]:
        A("SONUC: %d OLCULMEMIS SIPARIS · %s ciro Meta/GA4'te GORUNMUYOR  (cikis kodu 1)"
          % (len(kovalar[KAYIP]), tl(kayip_ciro)))
        A("Sebep adayi: havale onayi shop/KURULUM.md'deki YEDEK HAM SQL ile yapildi ya da")
        A("olcumlu worker surumu o an henuz yayinda degildi. Dogru yol: /api/shop/yonet.")
        A("⚠️ GERI DONUK GONDERIM YOK: Meta 7 gunden eski olayi reddeder; bu arac zaten")
        A("   salt-okunur — olay gondermez. Yapilacak is: bundan sonra yonetim sayfasi.")
    else:
        A("SONUC: olculmemis siparis YOK — esik sonrasi odenmis her sipariste olcum izi var.")
        A("       (Iz 'denendi' demek; ulasma kaniti Cloudflare Logs'ta.)  (cikis kodu 0)")
    A("=" * 78)

    ozet = {
        "kayip_adet": len(kovalar[KAYIP]),
        "kayip_ciro_kurus": kayip_ciro,
        "esik_oncesi_adet": len(kovalar[ESIK_ONCESI]),
        "esik_oncesi_ciro_kurus": onceki_ciro,
        "olculdu_adet": len(kovalar[OLCULDU]),
        "olcum_beklenmez_adet": len(kovalar[OLCUM_BEKLENMEZ]),
        "olcum_beklenmez_ciro_kurus": beklenmez_ciro,
        "kanal_dagilimi": {ad: {"adet": a, "ciro_kurus": c}
                           for ad, (a, c) in kanal_dagilim.items()},
        "kanal_kolonu": kanal_kolonu,
        "meta_penceresi_disi_adet": len(pencere_uyari),
        "incelenen": len(satirlar),
    }
    return "\n".join(L), ozet


# ------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--son", type=int, default=200,
                    help="incelenecek son N odenmis siparis (varsayilan 200)")
    ap.add_argument("--esik", default=None,
                    help="ISO damga — HER IKI esigi birden ezer (or. 2026-07-20T01:24:38Z)")
    ap.add_argument("--esik-kart", default=ESIK_KART, help="kart akisi esigi (ISO)")
    ap.add_argument("--esik-havale", default=ESIK_HAVALE, help="havale akisi esigi (ISO)")
    ap.add_argument("--ayrinti", action="store_true",
                    help="olcum izi OLAN siparisleri de listele")
    args = ap.parse_args(argv)

    ek, eh = args.esik_kart, args.esik_havale
    if args.esik:
        ek = eh = args.esik
    for ad, deger in (("--esik-kart", ek), ("--esik-havale", eh)):
        if iso_sn(deger) is None:
            sys.exit("%s cozulemedi (ISO 8601 bekleniyor): %r" % (ad, deger))

    satirlar, kanal_kolonu = siparisleri_oku(args.son)
    if not kanal_kolonu:
        # GURULTULU: sessiz dusus, "kayip" listesine site disi siparislerin sizmasi
        # demektir. Kimse bunu fark etmeden rapora bakmasin.
        print("!! KANAL KOLONU YOK — 'no such column: kanal'; kolonsuz SELECT'e dusuldu")
        print("   (goc henuz kosmadi: python3 tools/d1-sync.py --sema). TUM satirlar SITE")
        print("   kabul edildi; site disi bir uc varsa siparisleri KAYIP gorunur.")
    metin, ozet = rapor(satirlar, ek, eh, args.ayrinti, kanal_kolonu)
    print(metin)
    return 1 if ozet["kayip_adet"] else 0


if __name__ == "__main__":
    sys.exit(main())
