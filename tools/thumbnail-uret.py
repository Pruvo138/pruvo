#!/usr/bin/env python3
"""Kapak görseli küçük thumbnail üreteci — bkz. DEVAM.md / görev spec'i.

K306 (26 Ağu 2026) — SORGU GRANÜLARİTESİ ONARIMI
------------------------------------------------
ÖLÇÜLEN ARIZA: bu araç `urunler.json`'daki HER benzersiz kapak için R2'ye tek tek
`head_object` atıyordu (`var_mi(tkey)`), 10 iş parçacığıyla. `uretilen=0` olsa bile
maliyet SABİT ve katalogla birlikte büyüyor (ölçüm anında 30.366 gidiş-dönüş).
pre-push kancası her main push'unda bunu koşturduğu için tur 600 sn tavanını aştı →
ev `--no-verify`'a kaçtı → denetim kapısı koşmadı → ihlal canlıya gitti → `serit-a3`
kırmızı → `yayin`+`deploy` 6 ardışık koşumda SKIP → canlı site 178 dk geride kaldı.
Yani yavaşlık "çok iş var"dan DEĞİL, **yanlış sorgu granülaritesinden** geliyordu.

ONARIM: kapak-başına-sorgu yerine **TOPLU ENVANTER ÖN-ELEMESİ** (`list_objects_v2`,
önek kollarıyla paralel sayfalama). Envanter HER KOŞUMDA TAZE okunur; diske/belleğe
kalıcı önbellek YAZILMAZ → "bayat önbellek" sınıfı DOĞMAZ.

🔴 DOKUNULMAZ EMNİYET — envanter YALNIZ ÖN-ELEMEDİR:
  * `bir_urun_isle` içindeki `var_mi(tkey)` GERÇEK `head_object` sondasıdır ve KALIR.
  * `r2_upload.dogrula_ve_yukle(..., var_mi=...)`'ye geçen sonda da GERÇEK
    `head_object`'tir (yalnız SAYAÇ ile sarılır; sarmalayıcı koşulsuz devreder,
    hiçbir şey ÖNBELLEKLEMEZ). R6 ezme kapısı listeden BESLENMEZ: liste aynı tur
    içinde bayatlar ve sessiz üzerine-yazma doğar → memory/r2-sessiz-uzerine-yazma.md.
  * Envanterde GÖRÜNEN kapak `atlanan` sayılır (eski davranışın AYNISI); envanterde
    GÖRÜNMEYEN kapak tam yolu (gerçek sonda + üretim) izler. Yani sonuç üçlüsü
    (`uretilen/atlanan/hata`) değişmez, YALNIZ istek sayısı düşer.
  * `WORKERS`, `THUMB_MAX`, `THUMB_KALITE`, JPEG kalite/boyutlandırma ve `--limit`
    sözleşmesi DEĞİŞMEDİ.

Kabul testi (ağsız, R2 kimliği İSTEMEZ): tools/thumbnail-artimli-test.py
"""

import argparse
import bisect
import importlib.util
import io
import json
import os
import sys
import threading
import time
from concurrent.futures import (FIRST_COMPLETED, ThreadPoolExecutor,
                                as_completed, wait)

from PIL import Image, ImageOps


BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(BASE, ".."))

_spec = importlib.util.spec_from_file_location(
    "r2_upload", os.path.join(BASE, "r2-upload.py")
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("r2-upload.py yuklenemedi")
r2_upload = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r2_upload)

THUMB_MAX = 480
THUMB_KALITE = 78
WORKERS = 10

# K306 envanter ön-elemesi: liste sorgusu KAÇ paralel önek koluna bölünecek.
# Tek bir `Prefix=urunler/` sayfalaması SIRALIDIR (ContinuationToken zinciri) ve
# ~120 sayfada duvar saatini yer; ayrık önekler paralel sayfalanabilir.
# 🔴 SAYI ÖLÇÜMDEN GELİYOR (26 Ağu 2026): kapak anahtarlarında ayrık önek sayısı
# `urunler/`+1 karakterde 35, +2'de 210, +3'te 439. Eşik = iş parçacığı sayısı:
# ilk dalga havuzu DOLDURACAK kadar kol açılır, ama gereksiz bölünmeyle toplam
# istek şişirilmez (her önek EN AZ bir istek demektir; +3 seçimi 678 istek
# ürettiyken içerik yalnız ~123 tam sayfaydı). +1'i seçmek ise koca bir
# `urunler/t…` kolunu (katalogun çoğu `th…` Thingiverse anahtarı) tek zincire
# hapsederdi; kalan eğiklik aşağıdaki BÖLÜNME koluyla açılır.
ENVANTER_ASGARI_KOL = 128
# Önek uzunluğu araması bu kadar karakterden fazla UZATILMAZ (aşırı bölünme =
# gereksiz çok istek; her önek en az bir liste çağrısı demektir).
ENVANTER_ONEK_TAVANI = 6
# Kesilen öneği alt öneklere bölerken bu uzunluktan sonrası bölünmez; ardışık
# sayfalamaya düşülür (sonsuz bölünmeye karşı emniyet).
ONEK_UZUNLUK_TAVANI = 80
# Envanter sayfalaması SAF AĞ I/O'sudur (CPU yok, görsel işleme yok) — üretim
# havuzundan AYRI ve daha geniş tutulur. 🔴 `WORKERS` DEĞİŞMEDİ: görsel indirme +
# JPEG kodlama + yükleme hâlâ 10 iş parçacığıyla koşar.
# 🔴 ÖLÇÜLDÜ (26 Ağu): 32 iş parçacığı TEK BAŞINA yetmedi (35,55 sn). Sebep
# botocore'un VARSAYILAN `max_pool_connections=10` HAVUZUDUR — 32 iş parçacığı
# 10 bağlantı için sıraya giriyordu, yani ölçülen paralellik 10'du. Havuz aşağıda
# açıkça büyütülür; iki sayı BİRLİKTE değişmezse iş parçacığı sayısı YALAN OLUR.
ENVANTER_WORKERS = 128

_kilit = threading.Lock()
_sayac = {"uretilen": 0, "atlanan": 0, "hata": 0}


def sayaci_sifirla():
    """Süreç içinde ARDIŞIK koşum (ölçüm/kabul testi) için sayaçları sıfırlar."""
    with _kilit:
        for ad in _sayac:
            _sayac[ad] = 0
    return _sayac


def thumb_anahtari(key):
    kok, uzanti = os.path.splitext(key)
    return kok + "-thumb" + uzanti


def anahtar_of(url, public_base):
    onek = public_base.rstrip("/") + "/"
    if not url.startswith(onek):
        return None
    return url[len(onek):]


def sayan_sonda(var_mi, sayac):
    """`var_mi`yi SAYAÇLA sarar — KOŞULSUZ devreder, HİÇBİR ŞEY önbelleklemez.

    🔴 Bu sarmalayıcı emniyeti DEĞİŞTİRMEZ: `dogrula_ve_yukle`'ye geçen sonda hâlâ
    gerçek `head_object`'e iner. Tek işi ölçüm: kaç GERÇEK sonda atıldı."""
    def sarmal(key):
        with _kilit:
            sayac["head"] += 1
        return var_mi(key)
    return sarmal


def envanter_onekleri(tkeys, asgari_kol=ENVANTER_ASGARI_KOL,
                      tavan=ENVANTER_ONEK_TAVANI):
    """Thumb anahtarlarından liste sorgusu için AYRIK önek kümesi türetir.

    Aynı uzunluktaki önekler ayrıktır ve birleşimleri `tkeys`in TAMAMINI kapsar —
    yani ön-eleme hiçbir kapağı gözden kaçıramaz. Uzunluk, kol sayısı
    `asgari_kol`e ulaşana kadar (ya da `tavan` dolana kadar) büyütülür."""
    tkeys = list(tkeys)
    if not tkeys:
        return set()
    ortak = os.path.commonprefix(tkeys)
    n = len(ortak)
    kume = {ortak} if ortak else set(tkeys)
    for ek in range(1, tavan + 1):
        aday = {t[:n + ek] for t in tkeys}
        kume = aday
        if len(aday) >= asgari_kol:
            break
    return kume


def alt_onekler(onek, sirali_tkeys):
    """KESİLEN bir öneği, ARADIĞIMIZ anahtarlardan türetilen alt öneklere böler.

    Çocuklar `sirali_tkeys`ten türetilir (karakter kümesi TAHMİN EDİLMEZ), yani
    ilgilendiğimiz anahtar uzayının tamamını kapsar. Bölünemezse boş küme döner ve
    çağıran ardışık sayfalamaya düşer."""
    if len(onek) >= ONEK_UZUNLUK_TAVANI:
        return set()
    bas = bisect.bisect_left(sirali_tkeys, onek)
    cocuklar = set()
    for i in range(bas, len(sirali_tkeys)):
        t = sirali_tkeys[i]
        if not t.startswith(onek):
            break
        if len(t) > len(onek):
            cocuklar.add(t[:len(onek) + 1])
    return cocuklar


def envanter_topla(s3, bucket, onekler, sirali_tkeys=(), sayac=None):
    """`list_objects_v2` ile MEVCUT anahtar kümesini toplu çeker (TAZE, önbeleksiz).

    Dönüş: mevcut anahtarların kümesi. Kalıcı hiçbir yere yazılmaz; her koşumda
    yeniden okunur. YALNIZ ön-eleme içindir — R6 ezme kapısının sondası bu kümeden
    BESLENMEZ (bkz. modül başlığı).

    KESİLEN önek ARDIŞIK sayfalanmaz, ALT ÖNEKLERE bölünüp yeniden PARALEL
    listelenir: `ContinuationToken` zinciri sıralıdır ve yoğun bir kolu tek iş
    parçacığına hapseder (ölçüldü: `urunler/th…` katalogun çoğunu taşıyor).

    🔴 FAIL-SAFE YÖN: envanter bir anahtarı GÖZDEN KAÇIRIRSA o kapak ADAY olur ve
    GERÇEK `head_object` sondasına gider — yani eksik envanter YANLIŞ SONUÇ değil,
    yalnız fazladan istek üretir. Ters yön (envanterin olmayan bir anahtarı VAR
    göstermesi) mümkün değildir: küme R2'nin kendi listesinden gelir."""
    bulunan = set()
    kilit = threading.Lock()

    def say():
        if sayac is not None:
            with kilit:
                sayac["liste"] = sayac.get("liste", 0) + 1

    def bir_sayfa(gorev):
        onek, baslangic = gorev
        kw = {"Bucket": bucket, "Prefix": onek, "MaxKeys": 1000}
        if baslangic:
            kw["StartAfter"] = baslangic
        yanit = s3.list_objects_v2(**kw)
        say()
        yerel = [n["Key"] for n in (yanit.get("Contents") or [])]
        if not yanit.get("IsTruncated"):
            return yerel, []
        son = yerel[-1] if yerel else baslangic
        cocuklar = alt_onekler(onek, sirali_tkeys)
        if cocuklar and son:
            # Anahtarlar SIRALI döner: bu sayfa [önek, son] aralığını TAM kapsar.
            # Tamamı `son`un altında kalan alt önek YENİDEN SORULMAZ; kalanlar
            # `StartAfter=son` ile sorulur (mükerrer sayfa çekimi kalkar).
            sonraki = [(c, son) for c in sorted(cocuklar)
                       if not (c <= son and not son.startswith(c))]
            if sonraki:
                return yerel, sonraki
        # Bölünemedi → klasik ardışık sayfalama (fail-safe kuyruk).
        token = yanit.get("NextContinuationToken")
        while token:
            devam = dict(kw)
            devam["ContinuationToken"] = token
            y = s3.list_objects_v2(**devam)
            say()
            yerel.extend(n["Key"] for n in (y.get("Contents") or []))
            token = y.get("NextContinuationToken") if y.get("IsTruncated") else None
        return yerel, []

    if not onekler:
        return bulunan
    # 🔴 BARİYERSİZ: bölünme DALGA DALGA koşturulmaz. Ölçüldü (26 Ağu): dalga
    # bariyerli sürüm 678 isteği 16,71 sn'de bitirdi (~40 istek/sn) — her dalga
    # en yavaş kolunu bekliyordu. Alt önek ÜRETİLDİĞİ AN kuyruğa girer.
    with ThreadPoolExecutor(max_workers=ENVANTER_WORKERS) as havuz:
        bekleyen = {havuz.submit(bir_sayfa, (o, None)) for o in sorted(onekler)}
        while bekleyen:
            biten, bekleyen = wait(bekleyen, return_when=FIRST_COMPLETED)
            for is_ in biten:
                yerel, cocuklar = is_.result()
                bulunan.update(yerel)
                for cocuk in cocuklar:
                    bekleyen.add(havuz.submit(bir_sayfa, cocuk))
    return bulunan


def bir_urun_isle(s3, bucket, public_base, var_mi, cover_url):
    key = anahtar_of(cover_url, public_base)
    if key is None:
        return "atlanan"
    tkey = thumb_anahtari(key)
    if var_mi(tkey):
        return "atlanan"

    orijinal = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    with Image.open(io.BytesIO(orijinal)) as kaynak:
        im = ImageOps.exif_transpose(kaynak).convert("RGB")
    genislik, yukseklik = im.size
    kisa = min(genislik, yukseklik)
    if kisa > THUMB_MAX:
        oran = THUMB_MAX / kisa
        im = im.resize(
            (max(1, round(genislik * oran)), max(1, round(yukseklik * oran))),
            Image.Resampling.LANCZOS,
        )

    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=THUMB_KALITE, optimize=True)
    # var_mi ENJEKTE edilir: R6 ezme kapısı (yükleyicinin içinde) bu betiğin zaten
    # kullandığı BAĞIMSIZ sonda ile ölçsün — ikinci bir yoklama mantığı yazılmaz.
    r2_upload.dogrula_ve_yukle(s3, bucket, tkey, buf.getvalue(), var_mi=var_mi)
    return "uretilen"


def kapaklari_topla(urunler, limit=None):
    """Ürün kayıtlarından BENZERSİZ kapak (gorseller[0]) listesini sırayla çıkarır."""
    kapaklar, gorulen = [], set()
    for urun in urunler:
        gorseller = urun.get("gorseller") or []
        if not gorseller or gorseller[0] in gorulen:
            continue
        gorulen.add(gorseller[0])
        kapaklar.append(gorseller[0])
    if limit is not None:
        kapaklar = kapaklar[:limit]
    return kapaklar


def calistir(s3, bucket, public_base, kapaklar, var_mi):
    """K306 hızlı yol: toplu envanter ön-elemesi → daraltılmış aday kümesi → tam yol.

    `var_mi` GERÇEK sondadır ve adaylara AYNEN uygulanır (emniyet değişmedi).
    Dönüş: (sayac, istek) — `istek` = {"liste": n, "head": n}."""
    istek = {"liste": 0, "head": 0}
    var_mi = sayan_sonda(var_mi, istek)

    toplam = len(kapaklar)
    print("TOPLAM_BENZERSIZ_KAPAK=%d" % toplam, flush=True)

    # 1) public_base DIŞI URL'ler eski kodda da "atlanan"dı ve HİÇ sorgu üretmiyordu.
    ciftler = []
    for cover in kapaklar:
        key = anahtar_of(cover, public_base)
        if key is None:
            with _kilit:
                _sayac["atlanan"] += 1
            continue
        ciftler.append((cover, thumb_anahtari(key)))

    # 2) ÖN-ELEME: kapak-başına head_object YERİNE toplu envanter.
    tkeys = [t for _, t in ciftler]
    onekler = envanter_onekleri(tkeys)
    t0 = time.perf_counter()
    envanter = envanter_topla(s3, bucket, onekler, sirali_tkeys=sorted(tkeys),
                              sayac=istek)
    sure_envanter = time.perf_counter() - t0
    adaylar = [cover for cover, tkey in ciftler if tkey not in envanter]
    onelenen = len(ciftler) - len(adaylar)
    with _kilit:
        _sayac["atlanan"] += onelenen
    print(
        "ENVANTER_ONEK=%d LISTE_ISTEGI=%d ENVANTER_ANAHTAR=%d ONELENEN=%d ADAY=%d"
        % (len(onekler), istek["liste"], len(envanter), onelenen, len(adaylar)),
        flush=True,
    )

    # 3) TAM YOL yalnız adaylara: gerçek sonda + gerekiyorsa üretim.
    def gorev(cover):
        try:
            sonuc = bir_urun_isle(s3, bucket, public_base, var_mi, cover)
        except Exception as exc:
            print("HATA: %s -> %s" % (cover, exc), file=sys.stderr, flush=True)
            sonuc = "hata"
        with _kilit:
            _sayac[sonuc] += 1
            n = _sayac["uretilen"] + _sayac["atlanan"] + _sayac["hata"]
        if n % 200 == 0:
            print(
                "ILERLEME=%d/%d uretilen=%d atlanan=%d hata=%d"
                % (
                    n,
                    toplam,
                    _sayac["uretilen"],
                    _sayac["atlanan"],
                    _sayac["hata"],
                ),
                flush=True,
            )

    t1 = time.perf_counter()
    if adaylar:
        with ThreadPoolExecutor(max_workers=WORKERS) as havuz:
            gelecekler = [havuz.submit(gorev, cover) for cover in adaylar]
            for _ in as_completed(gelecekler):
                pass
    sure_uretim = time.perf_counter() - t1

    print("SURE_ENVANTER=%.2f SURE_URETIM=%.2f" % (sure_envanter, sure_uretim))
    print(
        "THUMB_URETILEN=%d ATLANAN=%d HATA=%d"
        % (_sayac["uretilen"], _sayac["atlanan"], _sayac["hata"])
    )
    print("R2_ISTEK_LISTE=%d R2_ISTEK_HEAD=%d" % (istek["liste"], istek["head"]))
    return _sayac, istek


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if args.limit is not None and args.limit < 0:
        ap.error("--limit negatif olamaz")

    with open(os.path.join(REPO, ".r2-credentials.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    import boto3
    from botocore.config import Config

    # 🔴 HAVUZ İŞ PARÇACIĞI SAYISINDAN KÜÇÜK OLAMAZ. botocore varsayılanı
    # `max_pool_connections=10`'dur; bunu büyütmeden iş parçacığı sayısını
    # büyütmek YALAN paralelliktir (ölçüldü 26 Ağu: 32 iş parçacığı + 10 havuz
    # = 35,55 sn; bağlantı için sıraya girildi).
    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret"],
        region_name="auto",
        config=Config(max_pool_connections=max(WORKERS, ENVANTER_WORKERS),
                      retries={"max_attempts": 8, "mode": "standard"}),
    )
    var_mi = r2_upload.s3_var_mi(s3, cfg["bucket"])

    t0 = time.perf_counter()
    with open(os.path.join(REPO, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    print("SURE_JSON=%.2f" % (time.perf_counter() - t0), flush=True)

    kapaklar = kapaklari_topla(urunler, args.limit)
    calistir(s3, cfg["bucket"], cfg["public_base"], kapaklar, var_mi)


if __name__ == "__main__":
    main()
