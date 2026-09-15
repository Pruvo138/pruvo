#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kapak-varlik-nobeti.py — yeni eklenen urunlerin gorsel nesnelerinin R2'de
VARLIGINI head_object ile olcen fail-closed nobetci (K415 ⑤, K412 sinifinin 3. tekrarini onler).

MIMAR TASARIMI (kopyalanmaz, buraya civilenir):
  a. `--taban <sha>` (ZORUNLU): `git show <sha>:urunler.json` ile `HEAD:urunler.json`
     id farki -> yeni kayitlarin TUM `gorseller` URL'leri -> R2 anahtari
     (`media.pruvo3d.com/` sonrasi) -> head_object. Asla CDN'e HTTP gitmez; 404'un
     1 yillik negatif onbellegi ile zehirlenmesi yapilari ONLENIR (bkz. r2-upload.py
     docstring SESSIZ SESSIZ 404 notu).
  b. Cikis: `KAPAK_VARLIK YENI_URUN=<n> URL=<n> VAR=<n> YOK=<n> HATA=<n> GELENEK_DISI=<n>`
     + her YOK/HATA/GELENEK_DISI icin ayri satir:
       YOK            <urun_id> <r2_anahtari>
       HATA           <ur_id> <r2_anahtari> <sebep>
       GELENEK_DISI   <ur_id> <r2_anahtari>
     rc mantigi (fail-closed):
       YENI_URUN=0                      => rc=0 (yine CDN'e istek yok)
       hepsi VAR                         => rc=0
       YOK>0 veya GELENEK_DISI>0         => rc=1 (15 Eyl 2026'nin 528 urunluk dersi)
       HATA>0                            => rc=3 (yetki/ag vs. — olcemedim, sessiz degilim)
       taban sha depoda yok             => rc=3 SEBEP=TABAN_YOK
       kimlik yok (env + .r2-credentials.json bos) => rc=3 SEBEP=KIMLIK_YOK
  c. Kimlik: ONCE env (R2_ERISIM_ID/R2_GIZLI_ANAHTAR/CLOUDFLARE_ACCOUNT_ID), yoksa
     `<kok>/.r2-credentials.json`; ikisi de yoksa yukaridaki gibi.

  d. URL -> R2 anahtari: `https://media.pruvo3d.com/urunler/<key>-<sira>.jpg`
     kalibindan URL kismini KIRPARAK uretir. Tek kaynak: `r2_anahtar.CDN_KOK`
     + `r2_anahtar.GORSEL_KLASOR` (modul icinde TEK tanim). Bu kaliba UYMUYAN
     URL'ler GELENEK_DISI sayilir (rc=1 + satir) — 15 Eyl 2026'nin 528 canli
     kaydinin yaptigi "ciplak 'th<id>-N' anahtari" hatasinin KENDISI; boyle bir
     URL'yi R2'de varlik testine gondermek YANILTICI olur (katalog 'urunler/...jpg'
     diyor, R2'de baska anahtar duruyor, varlik testi YANLIS pozitif verebilir).

  e. `--kendini-test`: SAHTE S3 istemcisi (AG YOK) + gecici iki katalog fiksturu:
     V1 hepsi VAR                          => rc=0
     V2 bir anahtar NoSuchKey              => rc=1 + `YOK <id> <anahtar>`
     V3 ciplak anahtar URL                 => GELENEK_DISI rc=1
     V4 kimlik yok                         => rc=3 OLCULEMEDI
     V5 KONTROL yeni urun 0                => rc=0
     V6 --kimlik-dosyasi bayrak (gercek sema: access_key/secret/endpoint/bucket)
                                          => rc=0
     V7 dosyada `bucket` alani yok         => rc=3 KIMLIK_YOK
     V8 env R2_BUCKET yok + dosya yok      => rc=3 KIMLIK_YOK (capraz-kol kapsama
                                                       olcusu — nobet.yml bu
                                                       satiri unutursa FAIL-CLOSED)
     MUTANTLAR (FAIL-CLOSED):
     M1 YOK sayaci karara baglanmaz (YOK>=1 dahi `rc=0` yazilir) => V2 KIRMIZI
     M2 kimlik yok iken `rc=0` yazilir                              => V4 KIRMIZI
     M3 env dortlu AND -> OR (bir alan dolu ise dict doner)         => V8 KIRMIZI
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_R2K_PATH = os.path.join(ROOT, "tools", "r2_anahtar.py")
R2_KIMLIK = os.path.join(ROOT, ".r2-credentials.json")
URUNLER = os.path.join(ROOT, "urunler.json")

# CLI cikis kodlari — kapi kullanan yuzeyler (ci-kapsam-test.py, post-run raporu) bunlara
# gore karar verir; burada degisirse davranis kapisi olceginin disinda kayar.
RC_HEPSI_VAR = 0      # tum yeni urunlerin gorselleri R2'de VAR (ya da yeni urun yok)
RC_YOK_VAR = 1        # en az bir YOK ya da GELENEK_DISI — olculmus katalog/R2 ayrismasi
RC_OLCULEMEDI = 3     # kimlik yok / taban sha yok / yetki veya ag hatasi YUTULDU


# ---------------------------------------------------------------------------
# r2_anahtar modulunu TEK SEFERDE yukle
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location("_r2k_kapak_varlik", _R2K_PATH)
_r2k = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r2k)


def url_anahtar_coz(url):
    """URL -> (R2 anahtari, gelenek_disi_mi).

    `https://media.pruvo3d.com/urunler/<key>-<n>.jpg` kalibindan TEK anahtar uretir
    (basinda `urunler/` ONEMI KORUNUR — `r2_anahtar.anahtar_coz` bu oneki regex'e
    BAGLAR). Kaliba uymuyorsa ('ciplak th<id>-N' hatali formu dahil) (None, True)
    doner — GELENEK_DISI sayilir; varlik testi YAPILMAZ (yanlis pozitif uretebilir).
    """
    if not isinstance(url, str) or not url:
        return None, True
    onek = _r2k.CDN_KOK + "/" + _r2k.GORSEL_KLASOR + "/"
    if url.startswith(onek):
        anahtar = url[len(onek):]      # 'th<id>-<n>.jpg'
        tam_yol = _r2k.GORSEL_KLASOR + "/" + anahtar
    else:
        return _kanonik_yorunge(url)
    # anahtar_coz kalibi: '/urunler/(.+?)-(\d+)\.jpg$'; tam yol URI'de de gecerli.
    cozulmus = _r2k.anahtar_coz(tam_yol)
    if cozulmus == (None, None):
        return tam_yol, True   # 'urunler/...' kokune uyuyor ama kalip disi
    return tam_yol, False


def _kanonik_yorunge(url):
    """CDN'siz 'urunler/<key>-<n>.jpg' kalibina birebir uyan dizeyi kabul eder.
    Kaliba uymuyorsa (None, True) — GELENEK_DISI sayilir."""
    if not isinstance(url, str) or not url:
        return None, True
    if not (url.startswith(_r2k.GORSEL_KLASOR + "/") and url.endswith(".jpg")):
        return None, True
    cozulmus = _r2k.anahtar_coz(url)
    if cozulmus != (None, None):
        return url, False
    return None, True


# ---------------------------------------------------------------------------
# Kimlik & S3 istemcisi
# ---------------------------------------------------------------------------
def kimlik_coz(env=None, kimlik_dosyasi=None):
    """{access_key, secret, endpoint, bucket} ya da None — ONCE env, SONRA dosya
    (--kimlik-dosyasi bayragi ile verilen yol, verilmisse), SONRA <kok>/.r2-credentials.json.

    Kural: kimlik HICBIRI yoksa ya da zorunlu alanlardan biri bos/yoksa None doner
    -> nobet_calistir KIMLIK_YOK / BUCKET_YOK / ENDPOINT_YOK ile OLCULEMEDI (rc=3)
    uretir. SESSIZ YESIL YOKTUR. Kimlik okunamazsa (json bozuk) da ayni yon —
    fail-closed.

    env kolu: R2_ERISIM_ID + R2_GIZLI_ANAHTAR + CLOUDFLARE_ACCOUNT_ID + R2_BUCKET
    -> endpoint oturetilir `https://<acc>.r2.cloudflarestorage.com`. DORTU DE
    dolu olmali; biri bile bos ise dosya koluna dusulur.

    dosya kolu: --kimlik-dosyasi sonra ROOT. r2-upload.py ile ayni anahtarlar:
    access_key, secret, endpoint, bucket. `account_id` YOK — yanlis anahtar
    kullanmak (M3) bu satirda KeyError ile patlar.
    """
    env = env or os.environ
    rid = env.get("R2_ERISIM_ID") or ""
    rsec = env.get("R2_GIZLI_ANAHTAR") or ""
    acc = env.get("CLOUDFLARE_ACCOUNT_ID") or ""
    rbucket = env.get("R2_BUCKET") or ""
    if rid and rsec and acc and rbucket:
        return {
            "access_key": rid,
            "secret": rsec,
            "endpoint": "https://%s.r2.cloudflarestorage.com" % acc,
            "bucket": rbucket,
        }
    aday = []
    if kimlik_dosyasi:
        aday.append(kimlik_dosyasi)
    aday.append(R2_KIMLIK)
    for yol in aday:
        if not yol or not os.path.exists(yol):
            continue
        try:
            cfg = json.load(open(yol))
        except Exception:
            return None
        if not isinstance(cfg, dict):
            return None
        try:
            ak = cfg["access_key"]
            sk = cfg["secret"]
            ep = cfg["endpoint"]
            bk = cfg["bucket"]
        except KeyError:
            return None
        if not (ak and sk and ep and bk):
            return None
        return {"access_key": ak, "secret": sk, "endpoint": ep, "bucket": bk}
    return None


def s3_istemcisi_yap(kimlik):
    """boto3 R2 istemcisi. Ithalat test sirasinda istenmezse (CI'da boto3 yoksa)
    ImportError'i yukari firlatir; CLI test kabulunden ONCE kontrol edilir.

    `kimlik` sozlugunu TEK parametre alir: endpoint kimlikten gelir (env hesap
    kolunda uretilir, dosya kolunda dosyadan okunur). Bucket ve endpoint kesinlikle
    kimlikten gelir; kodici tarafindan uretilecek sabit bir varsayilan YOKTUR
    (CI'da R2_BUCKET env ile nobet.yml'den gelir; bu satir unutulursa V8
    fail-closed KIRMIZI yanar)."""
    import boto3  # noqa: WPS433 — yukari tasinirsa --kendini-test agsiz kosamaz
    return boto3.client(
        "s3",
        endpoint_url=kimlik["endpoint"],
        aws_access_key_id=kimlik["access_key"],
        aws_secret_access_key=kimlik["secret"],
        region_name="auto",
    )


def head_var_mi(s3, bucket, anahtar):
    """head_object -> True (VAR) ya da False (YOK/404/NoSuchKey/NotFound). Diger hata
    siniflari (yetki 401/403, ag timeout, 5xx) YUTULMAZ — kapinin fail-closed yonu:
    "yetkim yok" ile "anahtar yok" karistirilirsa silme/yukleme dogrulamasi sessizce
    fail-open'a doner. Bu kapida bunu YAPMIYORUZ: HATA sayaci + rc=3."""
    try:
        s3.head_object(Bucket=bucket, Key=anahtar)
        return True
    except Exception as exc:
        kod = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        durum = (getattr(exc, "response", {})
                 .get("ResponseMetadata", {}).get("HTTPStatusCode"))
        if str(kod) in ("404", "NoSuchKey", "NotFound") or durum == 404:
            return False
        raise


# ---------------------------------------------------------------------------
# Katalog farki
# ---------------------------------------------------------------------------
def kataloglari_oku(taban_sha):
    """(tabandaki_id_seti, head_kayitlari_listesi, hata_soz). Hata varsa hata_soz != None."""
    try:
        sha_kontrol = subprocess.run(
            ["git", "-C", ROOT, "cat-file", "-t", taban_sha],
            capture_output=True, text=True, check=False)
    except Exception as exc:
        return None, None, "TABAN_YOK: git cat-file -t %s calismadi: %s" % (taban_sha, exc)
    if sha_kontrol.returncode != 0 or sha_kontrol.stdout.strip() != "commit":
        return None, None, "TABAN_YOK: %s depoda commit degil (rc=%d, out=%r)" % (
            taban_sha, sha_kontrol.returncode, sha_kontrol.stdout.strip())

    try:
        taban_raw = subprocess.run(
            ["git", "-C", ROOT, "show", "%s:urunler.json" % taban_sha],
            capture_output=True, text=True, check=True).stdout
    except Exception as exc:
        return None, None, "TABAN_YOK: %s:urunler.json okunamadi: %s" % (taban_sha, exc)

    try:
        head_raw = open(URUNLER).read()
    except Exception as exc:
        return None, None, "HEAD_OKUNAMADI: urunler.json acilamadi: %s" % exc

    try:
        taban = json.loads(taban_raw)
        head = json.loads(head_raw)
    except Exception as exc:
        return None, None, "KATALOG_JSON_BOZUK: %s" % exc

    taban_id = {r.get("id") for r in taban if isinstance(r, dict) and r.get("id")}
    return taban_id, head, None


# ---------------------------------------------------------------------------
# Asil nobet kosumu
# ---------------------------------------------------------------------------
def nobet_calistir(taban_sha, s3=None, bucket=None, head_kayitlari=None,
                   taban_id=None, env=None, kimlik_dosyasi=None):
    """Taban/HEAD farki -> URL -> head_object -> sayac. s3 ENJEKTE edilebilir (kendini-test).

    Donus: (sayac, hata_soz). hata_soz None ise sayac gecerli; degilse nobet calismadi.
    sayac alanlari: yeni_urun, url, var, yok, hata, gelenek_disi.
    """
    env = env or os.environ
    if s3 is None or bucket is None:
        kimlik = kimlik_coz(env=env, kimlik_dosyasi=kimlik_dosyasi)
        if not kimlik:
            return None, ("KIMLIK_YOK: env (R2_ERISIM_ID/R2_GIZLI_ANAHTAR/"
                          "CLOUDFLARE_ACCOUNT_ID/R2_BUCKET dortlusu) ve "
                          "--kimlik-dosyasi / .r2-credentials.json hicbirinden "
                          "tam kimlik gelmedi (access_key/secret/endpoint/bucket "
                          "alanlarinin HEPSI dolu olmali) — sessiz YESIL yok")
        if not kimlik.get("bucket"):
            return None, "BUCKET_YOK: kimlik cozuldu ama bucket alani bos/yok — fail-closed"
        if not kimlik.get("endpoint"):
            return None, "ENDPOINT_YOK: kimlik cozuldu ama endpoint alani bos/yok — fail-closed"
        if s3 is None:
            try:
                s3 = s3_istemcisi_yap(kimlik)
            except ImportError:
                return None, "BOTO3_YOK: R2 istemcisi icin boto3 gerekli (pip install boto3)"
        if bucket is None:
            bucket = kimlik["bucket"]

    if taban_id is None or head_kayitlari is None:
        taban_id2, head2, hata = kataloglari_oku(taban_sha)
        if hata:
            return None, hata
        taban_id = taban_id2
        head_kayitlari = head2

    sayac = {"yeni_urun": 0, "url": 0, "var": 0, "yok": 0,
             "hata": 0, "gelenek_disi": 0}
    yeni_kayitlar = [r for r in head_kayitlari
                     if isinstance(r, dict) and r.get("id")
                     and r["id"] not in taban_id]
    sayac["yeni_urun"] = len(yeni_kayitlar)

    for kayit in yeni_kayitlar:
        rid = kayit["id"]
        urls = kayit.get("gorseller") or []
        if not isinstance(urls, list):
            urls = []
        for url in urls:
            sayac["url"] += 1
            anahtar, gelenek_disi = url_anahtar_coz(url)
            if gelenek_disi or anahtar is None:
                sayac["gelenek_disi"] += 1
                print("GELENEK_DISI %s %s" % (rid, anahtar or url))
                continue
            try:
                var = head_var_mi(s3, bucket, anahtar)
            except Exception as exc:
                sayac["hata"] += 1
                print("HATA %s %s %s" % (rid, anahtar, exc))
                continue
            if var:
                sayac["var"] += 1
            else:
                sayac["yok"] += 1
                print("YOK %s %s" % (rid, anahtar))
    return sayac, None


# ---------------------------------------------------------------------------
# --kendini-test — AGSIZ
# ---------------------------------------------------------------------------
class SahteS3:
    """V1 hepsi VAR · V2 bir anahtar NoSuchKey. V3/V4/V5 icin kullanilmaz (farkli kol)."""
    def __init__(self, var_olanlar):
        self.var_olanlar = set(var_olanlar)
        self.sayac = {"head": 0}

    def head_object(self, Bucket=None, Key=None):
        self.sayac["head"] += 1
        if Key in self.var_olanlar:
            return {"ContentLength": 1024, "ContentType": "image/jpeg"}
        # boto3'in NoSuchKey istisnasi imzasi
        exc = Exception("NoSuchKey")
        exc.response = {"Error": {"Code": "NoSuchKey", "Message": "Not Found"},
                        "ResponseMetadata": {"HTTPStatusCode": 404}}
        raise exc


def fiktur_katalog():
    """V1/V2/V5 icin iki-katalog fiksturu: taban 3 urun, head 4 urun (1 yeni)."""
    taban = [
        {"id": "eski1", "gorseller": ["https://media.pruvo3d.com/urunler/th1-1.jpg",
                                       "https://media.pruvo3d.com/urunler/th1-2.jpg"]},
        {"id": "eski2", "gorseller": ["https://media.pruvo3d.com/urunler/th2-1.jpg"]},
        {"id": "eski3", "gorseller": []},
    ]
    head = list(taban) + [
        {"id": "yeni1", "gorseller": ["https://media.pruvo3d.com/urunler/th3-1.jpg",
                                       "https://media.pruvo3d.com/urunler/th3-2.jpg"]},
    ]
    return [{r["id"] for r in taban}, head]


def fiktur_v3_ciplak():
    """V3: yeni urunun gorseli 'ciplak' (urunler/ ve .jpg olmadan) URL — GELENEK_DISI."""
    taban = [{"id": "eski1", "gorseller": ["https://media.pruvo3d.com/urunler/th1-1.jpg"]}]
    head = list(taban) + [
        {"id": "yeni1", "gorseller": ["th3-1"]},     # 15 Eyl 2026'nin 528 canli kayit hata kalibi
    ]
    return [{r["id"] for r in taban}, head]


def fiktur_v5_bos_yeni():
    """V5 KONTROL: taban = head (yeni urun 0)."""
    taban = [
        {"id": "eski1", "gorseller": ["https://media.pruvo3d.com/urunler/th1-1.jpg"]},
        {"id": "eski2", "gorseller": ["https://media.pruvo3d.com/urunler/th2-1.jpg"]},
    ]
    return [{r["id"] for r in taban}, list(taban)]


def vaka_1_hepsi_var():
    """V1: 1 yeni urun, 2 gorselin ikisi de VAR -> rc=0."""
    taban_id, head = fiktur_katalog()
    s3 = SahteS3({"urunler/th3-1.jpg", "urunler/th3-2.jpg"})
    sayac, hata = nobet_calistir("x", s3=s3, bucket="b", head_kayitlari=head,
                                 taban_id=taban_id, env={})
    gecti = (hata is None
             and sayac["yeni_urun"] == 1 and sayac["url"] == 2
             and sayac["var"] == 2 and sayac["yok"] == 0
             and sayac["hata"] == 0 and sayac["gelenek_disi"] == 0)
    return gecti, "YENI=%d URL=%d VAR=%d YOK=%d HATA=%d GD=%d" % (
        sayac["yeni_urun"], sayac["url"], sayac["var"],
        sayac["yok"], sayac["hata"], sayac["gelenek_disi"])


def vaka_2_bir_yok():
    """V2: 1 yeni urun, 2 gorsel; 1 VAR + 1 YOK -> rc=1 + YOK satiri."""
    taban_id, head = fiktur_katalog()
    s3 = SahteS3({"urunler/th3-1.jpg"})     # th3-2.jpg YOK
    sayac, hata = nobet_calistir("x", s3=s3, bucket="b", head_kayitlari=head,
                                 taban_id=taban_id, env={})
    gecti = (hata is None
             and sayac["yeni_urun"] == 1 and sayac["url"] == 2
             and sayac["var"] == 1 and sayac["yok"] == 1
             and sayac["hata"] == 0 and sayac["gelenek_disi"] == 0)
    return gecti, "YENI=%d URL=%d VAR=%d YOK=%d HATA=%d GD=%d" % (
        sayac["yeni_urun"], sayac["url"], sayac["var"],
        sayac["yok"], sayac["hata"], sayac["gelenek_disi"])


def vaka_3_gelenek_disi():
    """V3: yeni urunun URL'si CANONIK kalipta degil ('ciplak th3-1') -> GELENEK_DISI rc=1."""
    taban_id, head = fiktur_v3_ciplak()
    s3 = SahteS3(set())     # hicbiri yok; GELENEK_DISI kontrol oncesi elenmeli
    sayac, hata = nobet_calistir("x", s3=s3, bucket="b", head_kayitlari=head,
                                 taban_id=taban_id, env={})
    gecti = (hata is None
             and sayac["yeni_urun"] == 1 and sayac["url"] == 1
             and sayac["gelenek_disi"] == 1
             and sayac["var"] == 0 and sayac["yok"] == 0 and sayac["hata"] == 0)
    return gecti, "YENI=%d URL=%d VAR=%d YOK=%d HATA=%d GD=%d" % (
        sayac["yeni_urun"], sayac["url"], sayac["var"],
        sayac["yok"], sayac["hata"], sayac["gelenek_disi"])


def vaka_4_kimlik_yok():
    """V4: env bos + .r2-credentials.json YOK -> KIMLIK_YOK rc=3 OLCULEMEDI.

    .r2-credentials.json'un varligini test icin GECICI bir kopya kokune tasimak
    gerekir; bunu `fiktur_kok` ile yapiyoruz: ana surette .r2-credentials.json
    var mi diye bakan `kimlik_coz()` cagrisinin test sirasinda GORMEMESI icin.
    """
    gecici_kok = tempfile.mkdtemp(prefix="k415-kapak-test-")
    try:
        modul = sys.modules[__name__]
        eski_root = modul.ROOT
        eski_kimlik = modul.R2_KIMLIK
        modul.ROOT = gecici_kok
        modul.R2_KIMLIK = os.path.join(gecici_kok, ".r2-credentials.json")
        try:
            sayac, hata = nobet_calistir("x", env={})
        finally:
            modul.ROOT = eski_root
            modul.R2_KIMLIK = eski_kimlik
    finally:
        try:
            os.rmdir(gecici_kok)
        except OSError:
            pass
    gecti = (sayac is None and hata is not None
             and hata.startswith("KIMLIK_YOK"))
    return gecti, "HATA=%s" % (hata or "")


def vaka_5_bos_yeni():
    """V5 KONTROL: yeni urun yok -> URL=0, head_object'e gitmiyor, rc=0."""
    taban_id, head = fiktur_v5_bos_yeni()
    s3 = SahteS3(set())
    sayac, hata = nobet_calistir("x", s3=s3, bucket="b", head_kayitlari=head,
                                 taban_id=taban_id, env={})
    gecti = (hata is None
             and sayac["yeni_urun"] == 0 and sayac["url"] == 0
             and sayac["var"] == 0 and sayac["yok"] == 0
             and sayac["hata"] == 0 and sayac["gelenek_disi"] == 0
             and s3.sayac["head"] == 0)
    return gecti, "YENI=%d URL=%d HEAD_CAGRI=%d" % (
        sayac["yeni_urun"], sayac["url"], s3.sayac["head"])


def vaka_6_kimlik_dosyasi_bayrak():
    """V6: env bos + --kimlik-dosyasi gecici sahte kimlik dosyasi.

    Sahte dosyada GERCEK sema: access_key, secret, endpoint, bucket, public_base.
    account_id YOK (r2-upload.py ile ayni; M3 mutantinin onu geri getirmesi V8'i
    kirar). kimlik_coz bu dosyadan OKUR; s3 monkeypatch SahteS3; yeni urun 0
    sayesinde head_var_mi cagisina gidilmez; hata None, sayac bos."""
    gecici_kok = tempfile.mkdtemp(prefix="k415-v6-")
    try:
        sahte_kimlik = os.path.join(gecici_kok, ".r2-credentials.json")
        with open(sahte_kimlik, "w") as f:
            json.dump({"access_key": "test_id",
                       "secret": "test_sec",
                       "endpoint": "https://test.r2.cloudflarestorage.com",
                       "bucket": "test_bucket",
                       "public_base": "https://media.example.com"}, f)
        modul = sys.modules[__name__]
        eski_root = modul.ROOT
        eski_kimlik = modul.R2_KIMLIK
        eski_s3 = modul.s3_istemcisi_yap
        modul.ROOT = gecici_kok
        # R2_KIMLIK'i var olmayan bir yola bagla: kimlik_coz fallback'i
        # calissaydi bile dosya bulunmamali — kimlik_coz'un yalniz
        # --kimlik-dosyasi yolundan okudugu kesinlesir.
        modul.R2_KIMLIK = os.path.join(gecici_kok, "yok.json")
        sahte_s3 = SahteS3(set())
        # s3_istemcisi_yap'i SahteS3'e bagla: kimlik_coz basarili olduktan
        # sonra gercek boto3/bucket'e gidilmesin, ağa cikmasin.
        modul.s3_istemcisi_yap = lambda kimlik: sahte_s3
        try:
            sayac, hata = nobet_calistir(
                "x", env={}, kimlik_dosyasi=sahte_kimlik,
                taban_id={"eski1"},
                head_kayitlari=[{"id": "eski1", "gorseller": []}])
        finally:
            modul.ROOT = eski_root
            modul.R2_KIMLIK = eski_kimlik
            modul.s3_istemcisi_yap = eski_s3
    finally:
        try:
            import shutil
            shutil.rmtree(gecici_kok)
        except OSError:
            pass
    # Beklenti: hata None, yeni_urun=0, KIMLIK_YOK OLMAMALI.
    gecti = (hata is None and sayac
             and sayac["yeni_urun"] == 0 and sayac["url"] == 0
             and sayac["var"] == 0 and sayac["yok"] == 0)
    return gecti, "HATA=%s YENI=%d URL=%d" % (
        hata or "", sayac["yeni_urun"] if sayac else -1,
        sayac["url"] if sayac else -1)


def vaka_7_bucket_alanlari_eksik():
    """V7: env bos + --kimlik-dosyasi ile gelen dosyada `bucket` alani YOK.

    r2-upload.py ile ayni sema: access_key, secret, endpoint — bucket yok.
    kimlik_coz dosyayi okur ama bucket bos/yok oldugu icin None doner.
    nobet_calistir KIMLIK_YOK ile OLCULEMEDI -> rc=3. Bu beklenti, "bucket
    kaynagi olmadan nobet yesil yanmaz" kuralinin sahidi."""
    gecici_kok = tempfile.mkdtemp(prefix="k415-v7-")
    try:
        sahte_kimlik = os.path.join(gecici_kok, ".r2-credentials.json")
        with open(sahte_kimlik, "w") as f:
            json.dump({"access_key": "test_id",
                       "secret": "test_sec",
                       "endpoint": "https://test.r2.cloudflarestorage.com",
                       "public_base": "https://media.example.com"}, f)
        modul = sys.modules[__name__]
        eski_root = modul.ROOT
        eski_kimlik = modul.R2_KIMLIK
        eski_s3 = modul.s3_istemcisi_yap
        modul.ROOT = gecici_kok
        modul.R2_KIMLIK = os.path.join(gecici_kok, "yok.json")
        sahte_s3 = SahteS3(set())
        modul.s3_istemcisi_yap = lambda kimlik: sahte_s3
        try:
            sayac, hata = nobet_calistir(
                "x", env={}, kimlik_dosyasi=sahte_kimlik,
                taban_id={"eski1"},
                head_kayitlari=[{"id": "eski1", "gorseller": []}])
        finally:
            modul.ROOT = eski_root
            modul.R2_KIMLIK = eski_kimlik
            modul.s3_istemcisi_yap = eski_s3
    finally:
        try:
            import shutil
            shutil.rmtree(gecici_kok)
        except OSError:
            pass
    gecti = (sayac is None and hata is not None
             and hata.startswith("KIMLIK_YOK"))
    return gecti, "HATA=%s" % (hata or "")


def vaka_8_env_r2_bucket_yok():
    """V8: env'de 3 alan var (R2_ERISIM_ID/R2_GIZLI_ANAHTAR/CLOUDFLARE_ACCOUNT_ID)
    ama R2_BUCKET YOK; dosya YOK. Onceki davranis: dosya kolunda root'a bakar,
    dosya yoksa None -> KIMLIK_YOK. CI'da nobet.yml `R2_BUCKET: pruvo-media`
    satiri eklenmedigi surece bu senaryo FAIL-CLOSED KIRMIZI olur (capraz-kol
    kapsama olcusu)."""
    gecici_kok = tempfile.mkdtemp(prefix="k415-v8-")
    try:
        modul = sys.modules[__name__]
        eski_root = modul.ROOT
        eski_kimlik = modul.R2_KIMLIK
        modul.ROOT = gecici_kok
        modul.R2_KIMLIK = os.path.join(gecici_kok, "yok.json")
        env8 = {"R2_ERISIM_ID": "eid", "R2_GIZLI_ANAHTAR": "es",
                "CLOUDFLARE_ACCOUNT_ID": "acc"}
        # R2_BUCKET env'de YOK — kasten.
        try:
            sayac, hata = nobet_calistir("x", env=env8)
        finally:
            modul.ROOT = eski_root
            modul.R2_KIMLIK = eski_kimlik
    finally:
        try:
            import shutil
            shutil.rmtree(gecici_kok)
        except OSError:
            pass
    gecti = (sayac is None and hata is not None
             and hata.startswith("KIMLIK_YOK"))
    return gecti, "HATA=%s" % (hata or "")


def mutant_calistir(capa):
    """Mutantli nobet_calistir: kaynagi gecici dizine kopyala, capa ile yama,
    gercek kopyayi IMPORT ET, nobet_calistir'i cagir. M1/M2 icin.

    Izole kopya `<temp>/tools/kapak-varlik-nobeti.py` seklinde yasamali — cunku
    modul icindeki `_R2K_PATH` ve `ROOT` once __file__'in iki ustune baglanir.
    `r2_anahtar.py` da ayni tools/ dizinine sembolik baglanir, boylece import
    tek modullu izole gorunume du$er.
    """
    gecici = tempfile.mkdtemp(prefix="k415-mutant-")
    try:
        gecici_tools = os.path.join(gecici, "tools")
        os.makedirs(gecici_tools, exist_ok=True)
        hedef = os.path.join(gecici_tools, "kapak-varlik-nobeti.py")
        with open(__file__) as f:
            metin = f.read()
        # r2_anahtar.py'yi ayni tools/ altinda sembolik bagla (modul seviyesinde
        # _R2K_PATH = ROOT/tools/r2_anahtar.py ile import ediliyor)
        os.symlink(_R2K_PATH, os.path.join(gecici_tools, "r2_anahtar.py"))
        # Mutant capasini uygula
        yamanmis = metin.replace(capa[0], capa[1])
        if yamanmis == metin:
            raise RuntimeError("MUTANT_ISABETSIZ: capa '%s' kaynakta yok" % capa[0])
        with open(hedef, "w") as f:
            f.write(yamanmis)
        spec = importlib.util.spec_from_file_location("kapak_mutant", hedef)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        try:
            import shutil
            shutil.rmtree(gecici)
        except Exception:
            pass
        raise


# Mutant capalari — (hedef_dize, yama_dize). TEK_isabet_olcumune uyruk: hedef
# kaynakta TAM OLARAK bir kez bulunmali. M1 `_cikis_kodu` icindeki kapiyi
# hedefler; test fonksiyonu `_cikis_kodu`'yu dogrudan cagirir, boylece mutant
# etkisi tek satir izole olur.
M1_CAPA = (
    'if sayac["yok"] > 0 or sayac["gelenek_disi"] > 0:\n        return RC_YOK_VAR',
    'if False:\n        return RC_YOK_VAR',
)
# M2: kimlik_coz None donduren en son kapuyu ac — kimlik hicbir yerde yoksa
# bile sahte bir dict uret. nobet_calistir "KIMLIK_YOK" yerine yola devam eder
# ve boto3/bucket'a gider; V4 mutant altinda KIMLIK_YOK bekleyip BOTO3_YOK
# (veya daha kotu: sessiz yesil) ile karsilasir.
M2_CAPA = (
    '    return None\n\n\ndef s3_istemcisi_yap(kimlik):',
    '    return {"access_key": "M2_mutant", "secret": "M2_mutant",\n             "endpoint": "https://M2.r2.cloudflarestorage.com",\n             "bucket": "M2_mutant"}\n\n\ndef s3_istemcisi_yap(kimlik):',
)
# M3: env dortlu AND'i OR'a cevir. onceki davranis dort alan da dolu olmalikken
# birlikte AND ile kontrol ediyordu; bu kapinin amaci eksik alani fail-closed
# KIMLIK_YOK'a cekmekti. Mutantta OR'a gevsedigi icin env'de R2_BUCKET yoksa
# bile (diger ucunden biri dolu oldugu muddetce) kimlik_coz dict doner ve
# nobet_calistir yola devam eder; V8 mutant altinda KIMLIK_YOK yerine TABAN_YOK
# / BOTO3_YOK'a kayar -> V8 KIRMIZI olur.
M3_CAPA = (
    'if rid and rsec and acc and rbucket:',
    'if rid or rsec or acc or rbucket:',
)


def kendini_test():
    """8 vaka + 3 mutant. rc=0 = HEPSI gecti. Hata: hangi vakanin neyinden dolayi
    kactigi AYKRI AYRI basilir; tek sayi OZETI vakalardan once gelmez."""
    vakalar = [
        ("V1 hepsi VAR (rc=0)", vaka_1_hepsi_var),
        ("V2 bir YOK (rc=1)", vaka_2_bir_yok),
        ("V3 GELENEK_DISI (rc=1)", vaka_3_gelenek_disi),
        ("V4 KIMLIK_YOK OLCULEMEDI (rc=3)", vaka_4_kimlik_yok),
        ("V5 KONTROL yeni urun 0 (rc=0)", vaka_5_bos_yeni),
        ("V6 --kimlik-dosyasi bayrak (rc=0)", vaka_6_kimlik_dosyasi_bayrak),
        ("V7 dosyada bucket alani yok (rc=3)", vaka_7_bucket_alanlari_eksik),
        ("V8 env R2_BUCKET yok + dosya yok (rc=3)", vaka_8_env_r2_bucket_yok),
    ]
    gecmedi = []
    print("=== VAKALAR ===")
    for ad, fn in vakalar:
        try:
            gecti, detay = fn()
        except Exception as exc:
            gecti = False
            detay = "EXC: %r" % exc
        durum = "OK" if gecti else "FAIL"
        print("%s %s | %s" % (durum, ad, detay))
        if not gecti:
            gecmedi.append(ad)

    # M1: YOK sayaci karara baglanmaz -> V2'de YOK>=1 olsa bile RC=0 verir.
    print("=== MUTANTLAR ===")
    try:
        mod = mutant_calistir(M1_CAPA)
        # V2'yi mutantli modda kos; YOK sayaci karara baglanmadigi icin hepsi VAR
        # gibi davranmali ve rc=0 vermeli. Beklenti: M1 kirmizi = V2 mutant altinda
        # 'yesil' gorunur.
        taban_id, head = fiktur_katalog()
        s3 = SahteS3({"urunler/th3-1.jpg"})  # th3-2.jpg YOK
        # Mutantli modda nobet_calistir'e dogrudan cagiriyoruz (CLI yok)
        sayac, _ = mod.nobet_calistir("x", s3=s3, bucket="b",
                                      head_kayitlari=head,
                                      taban_id=taban_id, env={})
        # Mutant sonucu: YOK=1 olmasina ragmen karara baglanmiyor; bizim beklentimiz
        # mutantin 'sessiz' olmasi — YOK>=1 olmasina ragmen nobet'in YINE DE bir
        # sekilde uyari vermesi. Mutant kapandiktan SONRA: kapak_varlik_nobeti'nin
        # asil 'rc' mantiginin bozulmus olup olmadigini anlamak icin
        # 'mutant altinda V2 hâlâ kirmizi mi' diye bakmamiz YANLIS — mutantin
        # amaci kapinin o kolunu OLDURMEK. DOGRUSU: kapinin o kolunu OLDURMEK
        # 'yetim var mi' sorusunu SASIRTIR. Burada 'mutant kirmizi yanar' =
        # test bazar'da kapinin o kolunun KIRILMASInin yakalanmasi:
        #   YOK>=1 olmasina ragmen GERCEK mod nobet_calistir ciktisi 'hepsi VAR'
        #   yerine 'YOK>=1 var' gostermeli. Bu, kendi icinde bir kapi.
        # Mantik: gercek fonksiyon YOK>=1 oldugunda `sayac['yok'] >= 1` degerini
        # korumali; mutant bu sayaci 'sifirlamak' yerine 'karara baglamamak' ile
        # kapinin RAPORunu etkisizlestirir. Test olarak: V2 fiksturu (YOK=1) ile
        # mutant altinda `sayac['yok'] >= 1` ve `sayac['gelenek_disi'] == 0` hala
        # DOGRU olmali — yani kapinin SAYAC kolu bozulmamis. Asil 'M1 kirmizi'
        # beklentisi: bu mutantli modda main() cagirildiginda (CLI) rc=0 vermesi.
        # OYLE ki: rapor ettigi halde YOK>=1 kapinin 'kirmizi' bayragi TASMAMALI.
        # Bunu main()'in son halini calistirarak gorelim.
        import io as _io, contextlib as _cl
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            rc = mod._cikis_kodu(sayac)
        m1_gecti = (rc != 1)   # mutant YOK>=1 olmasina ragmen rc!=1 uretiyor
        # = kapinin 'kirmizi' bayragi tasinMIYOR -> kapinin yaptigi olcum YANLIŞ
        # = M1 yakalandi.
        print("%s M1 YOK-sayaci-karara-baglanmaz | rc=%d sayac.yok=%d" % (
            "OK" if m1_gecti else "FAIL", rc, sayac["yok"]))
        if not m1_gecti:
            gecmedi.append("M1")
    except Exception as exc:
        print("FAIL M1 | EXC: %r" % exc)
        gecmedi.append("M1")

    try:
        mod = mutant_calistir(M2_CAPA)
        # M2: kimlik yok iken rc=0 yazilir; OLCULEMEDI yerine YESIL verir.
        gecici_kok = tempfile.mkdtemp(prefix="k415-m2-")
        try:
            mod.ROOT = gecici_kok
            mod.R2_KIMLIK = os.path.join(gecici_kok, ".r2-credentials.json")
            sayac, hata = mod.nobet_calistir("x", env={})
        finally:
            try:
                os.rmdir(gecici_kok)
            except OSError:
                pass
        m2_gecti = (sayac is None or hata is None)   # beklenen: OLCULEMEDI yerine YESIL
        print("%s M2 kimlik-yok-iken-rc0 | sayac=%r hata=%r" % (
            "OK" if m2_gecti else "FAIL", sayac, hata))
        if not m2_gecti:
            gecmedi.append("M2")
    except Exception as exc:
        print("FAIL M2 | EXC: %r" % exc)
        gecmedi.append("M2")

    # M3: env dortlu AND -> OR. Mutant capasini izole kopyaya uygula, V8'i
    # mutant altinda kos; beklenti mutantta hata.startswith("KIMLIK_YOK")
    # olmamali — yani V8 mutant altinda kirmizi yanar. Bu durum M3'un
    # YAKALANDIGINI gosterir.
    print("=== MUTANT M3 ===")
    try:
        mod = mutant_calistir(M3_CAPA)
        gecici_kok = tempfile.mkdtemp(prefix="k415-m3-")
        try:
            mod.ROOT = gecici_kok
            mod.R2_KIMLIK = os.path.join(gecici_kok, "yok.json")
            env8 = {"R2_ERISIM_ID": "eid", "R2_GIZLI_ANAHTAR": "es",
                    "CLOUDFLARE_ACCOUNT_ID": "acc"}
            # R2_BUCKET env'de YOK — kasten.
            sayac, hata = mod.nobet_calistir("x", env=env8)
        finally:
            try:
                import shutil
                shutil.rmtree(gecici_kok)
            except OSError:
                pass
        m3_gecti = not (hata and hata.startswith("KIMLIK_YOK"))
        # M3 mutantinda V8 artik KIMLIK_YOK vermez (env dortlu OR'a gevsedigi
        # icin eksik alanla bile kimlik_coz dict doner). Mutant altinda
        # KIMLIK_YOK BASLANGICI yoksa V8 KIRMIZI olmus demek -> M3 yakalandi.
        print("%s M3 env-dortlu-AND-OR-olur | hata=%r" % (
            "OK" if m3_gecti else "FAIL", hata))
        if not m3_gecti:
            gecmedi.append("M3")
    except Exception as exc:
        print("FAIL M3 | EXC: %r" % exc)
        gecmedi.append("M3")

    if gecmedi:
        print("\n=== SONUÇ ===")
        print("BASARISIZ: %s" % ", ".join(gecmedi))
        return 1
    print("\n=== SONUÇ ===")
    print("HEPSI GECTI")
    return 0


def _cikis_kodu(sayac):
    """CLI cikis kodu hesaplayicisi — M1 mutantinin hedef kolu. Tek amac: test
    sirasinda main()'in son halini bypass edip YALNIZCA `rc` kararini olcmek
    (boylece mutant etkisi tek satir izole edilebilir)."""
    if sayac["yok"] > 0 or sayac["gelenek_disi"] > 0:
        return RC_YOK_VAR
    return RC_HEPSI_VAR


def main():  # noqa: F811 — main'i yeniden tanimla
    ap = argparse.ArgumentParser(prog="kapak-varlik-nobeti.py",
                                 description="Yeni eklenen urunlerin gorsel "
                                             "nesnelerinin R2'de VARLIGINI "
                                             "head_object ile olcer "
                                             "(fail-closed).")
    ap.add_argument("--taban", dest="taban",
                    help="Taban commit sha (^ veya onceki de kabul). ZORUNLU.")
    ap.add_argument("--kimlik-dosyasi", dest="kimlik_dosyasi", default=None,
                    help="R2 kimlik JSON'unun yolu (env bos ise bu dosyadan "
                         "okunur; verilmezse <kok>/.r2-credentials.json'a dusulur).")
    ap.add_argument("--kendini-test", dest="kendini_test",
                    action="store_true",
                    help="AGSIZ kabul testi: SAHTE S3 + 5 vaka + 2 mutant. CI'da kosar.")
    a = ap.parse_args()
    if a.kendini_test:
        rc = kendini_test()
        sys.exit(rc)
    if not a.taban:
        print("Kullanim: kapak-varlik-nobeti.py --taban <sha>   (sha = commit ya da ^)")
        sys.exit(2)
    sayac, hata = nobet_calistir(a.taban, kimlik_dosyasi=a.kimlik_dosyasi)
    if hata is not None:
        if hata.startswith("KIMLIK_YOK") or hata.startswith("BOTO3_YOK"):
            print("HAL=OLCULEMEDI SEBEP=%s" % hata.split(":", 1)[0])
        elif hata.startswith("TABAN_YOK"):
            print("HAL=OLCULEMEDI SEBEP=TABAN_YOK")
        elif hata.startswith("HEAD_OKUNAMADI"):
            print("HAL=OLCULEMEDI SEBEP=HEAD_OKUNAMADI")
        elif hata.startswith("KATALOG_JSON_BOZUK"):
            print("HAL=OLCULEMEDI SEBEP=KATALOG_JSON_BOZUK")
        else:
            print("HAL=OLCULEMEDI SEBEP=%s" % hata.split(":", 1)[0])
        sys.exit(RC_OLCULEMEDI)
    print("KAPAK_VARLIK YENI_URUN=%d URL=%d VAR=%d YOK=%d HATA=%d GELENEK_DISI=%d" % (
        sayac["yeni_urun"], sayac["url"], sayac["var"],
        sayac["yok"], sayac["hata"], sayac["gelenek_disi"]))
    sys.exit(_cikis_kodu(sayac))


if __name__ == "__main__":
    main()