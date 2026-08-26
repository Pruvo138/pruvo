#!/usr/bin/env python3
"""K306 — `tools/thumbnail-uret.py` ARTIMLI ÖN-ELEME kabul testi (AĞSIZ).

Neyi ölçer (spec'in 7. kabul maddesi):
  ① ÖN-ELEME ARTIMLI: N kapaklı fikstürde atılan GERÇEK `head_object` sayısı N'den
     KÜÇÜK — yani "kapak başına bir sorgu" granülaritesi KALKTI. Sayı BASILIR.
     (Ön-elemenin gerçekten liste sorgusundan beslendiği de ölçülür: LISTE >= 1.)
  ② EMNİYET KORUNDU: `r2_upload.dogrula_ve_yukle`'ye geçen sonda GERÇEK
     `head_object` çağırır — envanter kümesinden/önbellekten BESLENMEZ. Sonda
     çağrının kendisinden YAKALANIR ve ayrı bir anahtarla tetiklenip R2 sayacının
     arttığı ÖLÇÜLÜR (memory/r2-sessiz-uzerine-yazma.md: R6 ezme kapısı listeden
     beslenirse aynı tur içinde bayatlar → sessiz üzerine-yazma).
  ③ ÜRETİM KOLU CANLI: thumb'ı OLMAYAN kapakta `uretilen=1`, OLAN kapakta
     `atlanan=1` — hız "iş yapmamaktan" gelmiyor.
  ④ MUTANT KOLU: ①'i ve ②'yi AYRI AYRI öldüren iki mutant KIRMIZI yanar ve
     komşusunu DÜŞÜRMEZ (iki yönlü ayrım — memory/isci-yesil-tablo-ic-olcumu-bosaltir.md
     tautoloji tuzağı); ilgisiz KONTROL mutantı YEŞİL kalır.

AĞ/R2 KİMLİĞİ İSTEMEZ: `boto3` istemcisi yerine sahte bir S3 kullanılır, `.r2-credentials.json`
okunmaz. Pillow yoksa (CI'da kurulu değil) asgari bir PIL vekili enjekte edilir ve hangi
kipte koşulduğu BASILIR — üretim kolunun ölçümü JPEG kodlamasına DEĞİL, kapağın üretim
dalına yönlendirilip `dogrula_ve_yukle`ye inmesine bakar (kodlama bu işte değişmedi).

Komut: python3 /Users/okan/dev/pruvo/tools/thumbnail-artimli-test.py
"""

import importlib.util
import io
import os
import shutil
import sys
import tempfile
import types


BASE = os.path.dirname(os.path.abspath(__file__))
KAYNAK = os.path.join(BASE, "thumbnail-uret.py")
R2_KAYNAK = os.path.join(BASE, "r2-upload.py")

PUBLIC_BASE = "https://media.pruvo3d.com"
BUCKET = "pruvo-test"


# ---------------------------------------------------------------------------
# PIL: gerçek varsa gerçek, yoksa asgari vekil (CI'da Pillow kurulu DEĞİL)
# ---------------------------------------------------------------------------
def pil_kipi():
    try:
        import PIL  # noqa: F401
        from PIL import Image, ImageOps  # noqa: F401
        return "gercek"
    except Exception:
        pass

    class _Im:
        def __init__(self, size=(600, 600)):
            self.size = size

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def convert(self, _mod):
            return self

        def resize(self, boyut, _ornekleme=None):
            return _Im(boyut)

        def save(self, buf, format=None, quality=None, optimize=None):
            # Geçerli JPEG sihirli-baytı + r2_upload.MIN_BOYUT üstü gövde:
            # doğrulama zinciri (R1) gerçek koşumdaki gibi işlesin.
            buf.write(b"\xff\xd8\xff" + b"\x2a" * 4096)

    class _Resampling:
        LANCZOS = 1

    image = types.ModuleType("PIL.Image")
    image.Resampling = _Resampling
    image.open = lambda _f: _Im()
    imageops = types.ModuleType("PIL.ImageOps")
    imageops.exif_transpose = lambda im: im
    paket = types.ModuleType("PIL")
    paket.Image = image
    paket.ImageOps = imageops
    sys.modules["PIL"] = paket
    sys.modules["PIL.Image"] = image
    sys.modules["PIL.ImageOps"] = imageops
    return "vekil"


PIL_KIPI = pil_kipi()


def ornek_orijinal():
    """Fikstür orijinali: gerçek PIL varsa GERÇEK bir JPEG, yoksa vekil gövde."""
    if PIL_KIPI == "gercek":
        from PIL import Image
        im = Image.frombytes("RGB", (600, 600), os.urandom(600 * 600 * 3))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    return b"\xff\xd8\xff" + b"\x2a" * 8192


ORIJINAL = ornek_orijinal()


# ---------------------------------------------------------------------------
# Sahte S3 — head/list/get/put sayaçlı, sayfalama taklitli
# ---------------------------------------------------------------------------
class Yok404(Exception):
    def __init__(self):
        super().__init__("NoSuchKey")
        self.response = {
            "Error": {"Code": "404", "Message": "Not Found"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }


class SahteS3:
    def __init__(self, mevcut, govdeler):
        self.mevcut = set(mevcut)
        self.govdeler = dict(govdeler)
        self.sayac = {"head": 0, "list": 0, "get": 0, "put": 0}

    def list_objects_v2(self, **kw):
        self.sayac["list"] += 1
        onek = kw.get("Prefix", "")
        maxk = kw.get("MaxKeys", 1000)
        token = kw.get("ContinuationToken")
        bas = int(token) if token else 0
        sonra = kw.get("StartAfter")
        hepsi = sorted(k for k in self.mevcut
                       if k.startswith(onek) and (sonra is None or k > sonra))
        dilim = hepsi[bas:bas + maxk]
        kesik = (bas + maxk) < len(hepsi)
        yanit = {"Contents": [{"Key": k} for k in dilim], "IsTruncated": kesik}
        if kesik:
            yanit["NextContinuationToken"] = str(bas + maxk)
        return yanit

    def head_object(self, Bucket=None, Key=None):
        self.sayac["head"] += 1
        if Key in self.mevcut:
            return {"ContentLength": len(self.govdeler.get(Key, b"")),
                    "ContentType": "image/jpeg"}
        raise Yok404()

    def get_object(self, Bucket=None, Key=None):
        self.sayac["get"] += 1
        if Key not in self.mevcut:
            raise Yok404()
        return {"Body": io.BytesIO(self.govdeler[Key])}

    def put_object(self, Bucket=None, Key=None, Body=None, ContentType=None,
                   **kw):
        self.sayac["put"] += 1
        self.mevcut.add(Key)
        self.govdeler[Key] = Body
        return {}


# ---------------------------------------------------------------------------
# Modül yükleme (mutasyonlu kaynak dahil)
# ---------------------------------------------------------------------------
def modul_yukle(kaynak_metin, gecici_kokler):
    """Kaynağı GEÇİCİ bir dizine yazıp yükler; r2-upload.py sembolik bağla verilir
    (modülün BASE'i kendi dosya yolundan türediği için aynı dizinde olmalı)."""
    kok = tempfile.mkdtemp(prefix="k306-")
    gecici_kokler.append(kok)
    hedef = os.path.join(kok, "thumbnail-uret.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak_metin)
    os.symlink(R2_KAYNAK, os.path.join(kok, "r2-upload.py"))
    spec = importlib.util.spec_from_file_location("k306_thumb_%d" % len(gecici_kokler),
                                                  hedef)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kapak(i):
    return "%s/urunler/k%04d-1.jpg" % (PUBLIC_BASE, i)


def anahtar(i):
    return "urunler/k%04d-1.jpg" % i


def thumb(i):
    return "urunler/k%04d-1-thumb.jpg" % i


# ---------------------------------------------------------------------------
# İDDİALAR — her biri KOMŞUSUNDAN BAĞIMSIZ düşebilir
# ---------------------------------------------------------------------------
N_FIKSTUR = 40


def iddia_1_on_eleme(mod):
    """① N kapağın TAMAMININ thumb'ı varken GERÇEK head sayısı N'den küçük."""
    kapaklar = [kapak(i) for i in range(N_FIKSTUR)]
    mevcut = set()
    govdeler = {}
    for i in range(N_FIKSTUR):
        mevcut.add(anahtar(i))
        mevcut.add(thumb(i))
        govdeler[anahtar(i)] = ORIJINAL
        govdeler[thumb(i)] = ORIJINAL
    s3 = SahteS3(mevcut, govdeler)
    var_mi = mod.r2_upload.s3_var_mi(s3, BUCKET)
    mod.sayaci_sifirla()
    sayac, istek = mod.calistir(s3, BUCKET, PUBLIC_BASE, kapaklar, var_mi)
    detay = ("N=%d HEAD=%d LISTE=%d ATLANAN=%d URETILEN=%d"
             % (N_FIKSTUR, s3.sayac["head"], s3.sayac["list"],
                sayac["atlanan"], sayac["uretilen"]))
    gecti = (s3.sayac["head"] < N_FIKSTUR
             and s3.sayac["list"] >= 1
             and sayac["atlanan"] == N_FIKSTUR
             and sayac["uretilen"] == 0)
    return gecti, detay


def iddia_2_emniyet(mod):
    """② dogrula_ve_yukle'ye geçen sonda GERÇEK head_object'e iniyor."""
    kapaklar = [kapak(0)]
    mevcut = {anahtar(0)}
    govdeler = {anahtar(0): ORIJINAL}
    s3 = SahteS3(mevcut, govdeler)
    var_mi = mod.r2_upload.s3_var_mi(s3, BUCKET)

    yakalanan = {}
    gercek = mod.r2_upload.dogrula_ve_yukle

    def casus(*a, **kw):
        yakalanan["sonda"] = kw.get("var_mi")
        return gercek(*a, **kw)

    mod.r2_upload.dogrula_ve_yukle = casus
    try:
        mod.sayaci_sifirla()
        mod.calistir(s3, BUCKET, PUBLIC_BASE, kapaklar, var_mi)
    finally:
        mod.r2_upload.dogrula_ve_yukle = gercek

    sonda = yakalanan.get("sonda")
    if sonda is None:
        return False, "SONDA_GECILMEDI (dogrula_ve_yukle var_mi almadi)"
    # Sondayı R2'de OLMAYAN taze bir anahtarla tetikle: gerçek head_object'e
    # iniyorsa sahte S3'ün head sayacı TAM 1 artar; küme/önbellek okuyorsa artmaz.
    once = s3.sayac["head"]
    sonuc = sonda("urunler/k306-sonda-probu.jpg")
    sonra = s3.sayac["head"]
    detay = ("SONDA_HEAD_ARTISI=%d (once=%d sonra=%d) SONDA_SONUC=%s"
             % (sonra - once, once, sonra, sonuc))
    return (sonra - once) == 1 and sonuc is False, detay


def iddia_3_uretim(mod):
    """③ thumb'ı olmayan kapak ÜRETİLİR, olan kapak ATLANIR."""
    kapaklar = [kapak(1), kapak(2)]
    mevcut = {anahtar(1), thumb(1), anahtar(2)}      # k0002'nin thumb'ı YOK
    govdeler = {anahtar(1): ORIJINAL, thumb(1): ORIJINAL, anahtar(2): ORIJINAL}
    s3 = SahteS3(mevcut, govdeler)
    var_mi = mod.r2_upload.s3_var_mi(s3, BUCKET)
    mod.sayaci_sifirla()
    sayac, istek = mod.calistir(s3, BUCKET, PUBLIC_BASE, kapaklar, var_mi)
    uretildi = thumb(2) in s3.mevcut
    detay = ("URETILEN=%d ATLANAN=%d HATA=%d PUT=%d THUMB_YAZILDI=%s"
             % (sayac["uretilen"], sayac["atlanan"], sayac["hata"],
                s3.sayac["put"], uretildi))
    gecti = (sayac["uretilen"] == 1 and sayac["atlanan"] == 1
             and sayac["hata"] == 0 and uretildi)
    return gecti, detay


def iddia_4_envanter_kapsami(mod):
    """④ KESİLEN önek alt öneklere bölünüyor ve envanter TAM kapsıyor.

    1000'lik sayfa sınırını aşan bir kova fikstüründe `envanter_topla` hem tüm
    anahtarları getirmeli hem de birden fazla liste çağrısı yapmalı (bölünme
    gerçekten koşmuş olmalı). Eksik envanter üretimi bozmaz (fail-safe: kapak
    aday olur, gerçek sonda ölçer) ama maliyeti geri getirir."""
    n = 2500
    tkeys = ["urunler/z%05d-1-thumb.jpg" % i for i in range(n)]
    s3 = SahteS3(set(tkeys), {})
    sayac = {"liste": 0}
    # TEK önek verilir: 2500 anahtar 1000'lik sayfayı AŞAR, yani BÖLÜNME kolu
    # gerçekten koşmak ZORUNDADIR (önek-başına-tek-anahtar durumunda bu iddia
    # boşalırdı — memory/isci-yesil-tablo-ic-olcumu-bosaltir.md).
    onekler = {"urunler/z"}
    envanter = mod.envanter_topla(s3, BUCKET, onekler,
                                  sirali_tkeys=sorted(tkeys), sayac=sayac)
    eksik = set(tkeys) - envanter
    detay = ("ANAHTAR=%d ONEK=%d LISTE_CAGRISI=%d ENVANTER=%d EKSIK=%d"
             % (n, len(onekler), sayac["liste"], len(envanter), len(eksik)))
    # liste>=3: tek çağrı 1000 anahtar getirir; 2500 anahtarın tamamı ancak
    # bölünmeyle gelebilir. eksik=0: bölünme hiçbir anahtarı düşürmedi.
    return (not eksik) and sayac["liste"] >= 3, detay


IDDIALAR = [
    ("1-on-eleme-artimli", iddia_1_on_eleme),
    ("2-emniyet-gercek-head", iddia_2_emniyet),
    ("3-uretim-kolu-canli", iddia_3_uretim),
    ("4-envanter-tam-kapsam", iddia_4_envanter_kapsami),
]


# ---------------------------------------------------------------------------
# MUTANTLAR — hedef kol ADIYLA yazılır, komşusunu DÜŞÜRMEMELİ
# ---------------------------------------------------------------------------
MUTANTLAR = [
    {
        "ad": "M1-on-eleme-devre-disi",
        "hedef_kol": "calistir(): `adaylar = [... if tkey not in envanter]` "
                     "ON-ELEME SUZGECI",
        "eski": "adaylar = [cover for cover, tkey in ciftler if tkey not in envanter]",
        "yeni": "adaylar = [cover for cover, tkey in ciftler]",
        "dusmeli": {"1-on-eleme-artimli"},
    },
    {
        "ad": "M2-sonda-listeden-beslenir",
        "hedef_kol": "bir_urun_isle(): `dogrula_ve_yukle(..., var_mi=var_mi)` "
                     "GERCEK SONDA ENJEKSIYONU",
        "eski": "r2_upload.dogrula_ve_yukle(s3, bucket, tkey, buf.getvalue(), var_mi=var_mi)",
        "yeni": "r2_upload.dogrula_ve_yukle(s3, bucket, tkey, buf.getvalue(), "
                "var_mi=(lambda _k: False))",
        "dusmeli": {"2-emniyet-gercek-head"},
    },
    {
        "ad": "M3-kesilme-yok-sayilir",
        "hedef_kol": "envanter_topla/bir_sayfa(): `IsTruncated` KOLU "
                     "(sayfa asimi -> bolunme)",
        "eski": "if not yanit.get(\"IsTruncated\"):",
        "yeni": "if True:",
        "dusmeli": {"4-envanter-tam-kapsam"},
    },
    {
        "ad": "M0-KONTROL-ilerleme-modulu",
        "hedef_kol": "calistir(): ILERLEME basim araligi (ILGISIZ KOL)",
        "eski": "if n % 200 == 0:",
        "yeni": "if n % 250 == 0:",
        "dusmeli": set(),
    },
]


def kos(mod):
    sonuc = {}
    for ad, fn in IDDIALAR:
        try:
            gecti, detay = fn(mod)
        except Exception as exc:
            gecti, detay = False, "ISTISNA: %s: %s" % (type(exc).__name__, exc)
        sonuc[ad] = (gecti, detay)
    return sonuc


def main():
    gecici_kokler = []
    rc = 0
    try:
        with open(KAYNAK, encoding="utf-8") as f:
            kaynak = f.read()

        print("K306 ARTIMLI ON-ELEME KABUL TESTI — PIL=%s" % PIL_KIPI)
        print("KAYNAK=%s" % KAYNAK)
        print("")

        # --- TABAN: değiştirilmemiş kaynak, TÜM iddialar GEÇMELİ ---
        taban_mod = modul_yukle(kaynak, gecici_kokler)
        taban = kos(taban_mod)
        gecen = 0
        for ad, _ in IDDIALAR:
            gecti, detay = taban[ad]
            print("TABAN %-24s %s  %s" % (ad, "GECTI" if gecti else "KIRMIZI", detay))
            if gecti:
                gecen += 1
            else:
                rc = 1
        print("TABAN_IDDIA=%d/%d" % (gecen, len(IDDIALAR)))
        print("")

        # --- MUTANTLAR: hedef kol düşmeli, komşu AYAKTA kalmalı ---
        mutant_ok = 0
        kontrol_ok = 0
        mutant_hedefli = [m for m in MUTANTLAR if m["dusmeli"]]
        mutant_kontrol = [m for m in MUTANTLAR if not m["dusmeli"]]
        if not mutant_kontrol:
            print("MUTANT KONTROL MUTANTI YOK — batarya EKSIK")
            rc = 1
        for m in MUTANTLAR:
            if m["eski"] not in kaynak:
                print("MUTANT %-28s CAPA_YOK (kaynak degismis: %r)"
                      % (m["ad"], m["eski"][:60]))
                rc = 1
                continue
            if kaynak.count(m["eski"]) != 1:
                print("MUTANT %-28s CAPA_COKLU (%d kez gecti)"
                      % (m["ad"], kaynak.count(m["eski"])))
                rc = 1
                continue
            mod = modul_yukle(kaynak.replace(m["eski"], m["yeni"]), gecici_kokler)
            r = kos(mod)
            dusen = {ad for ad, _ in IDDIALAR if not r[ad][0]}
            beklenen = m["dusmeli"]
            uygun = dusen == beklenen
            print("MUTANT %-28s HEDEF_KOL=%s" % (m["ad"], m["hedef_kol"]))
            print("       DUSEN=%s BEKLENEN=%s -> %s"
                  % (sorted(dusen) or "-", sorted(beklenen) or "-",
                     "GECTI" if uygun else "KIRMIZI"))
            for ad, _ in IDDIALAR:
                print("       %-24s %-8s %s"
                      % (ad, "KIRMIZI" if ad in dusen else "GECTI", r[ad][1]))
            if uygun:
                if beklenen:
                    mutant_ok += 1
                else:
                    kontrol_ok += 1
            else:
                rc = 1
        print("")
        print("K306-ARTIMLI-KABUL: IDDIA=%d/%d MUTANT=%d/%d KONTROL=%d/%d "
              "PIL=%s RC=%d"
              % (gecen, len(IDDIALAR), mutant_ok, len(mutant_hedefli),
                 kontrol_ok, len(mutant_kontrol), PIL_KIPI, rc))
    finally:
        for kok in gecici_kokler:
            shutil.rmtree(kok, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
