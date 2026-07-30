#!/usr/bin/env python3
"""
Kabul testi — tools/r2-upload.py doğrulama kalkanı (R1-R4).

CANLI R2'ye GİTMEZ: S3 client MOCK'lanır (FakeS3), kimlik/side-effect YOKTUR.
put_object yakalanır; head_object sahte ContentLength döndürür → deterministik.

Koşum:  python3 /Users/okan/dev/pruvo/tools/r2-upload-test.py
Beklenen: tüm vakalar geçer, exit 0.

Vakalar (SPEC A-I):
  A geçerli JPEG            → GEÇER, ContentType image/jpeg, readback OK
  B geçerli PNG            → GEÇER, ContentType image/png
  C 0-bayt dosya           → REDDEDİLİR (R1 boyut)
  D Cloudflare-403 HTML    → REDDEDİLİR (R1 magic yok; boyut > eşik)
  E kesik/çöp (>1KB)       → REDDEDİLİR (R1 magic yok)
  F .jpg ad + PNG gövde    → YÜKLENİR + stderr LOUD uyarı + ContentType image/png (R3)
  G kısmi PUT (readback ContentLength yanlış) → REDDEDİLİR (R4)
  H uzantısız ad + 403-HTML gövde → REDDEDİLİR (R1 magic yok)
  I uzantısız ad + JPEG magic     → GEÇER, ContentType image/jpeg

R5 SİLME KAPISI (sil_ve_dogrula) — SESSİZ SİLME sınıfı, 30 Tem 2026'da canlıda üretildi:
  J silme gerçekten uyguladı            → "silindi-dogrulandi", doğrulama silmeden SONRA koştu
  K silme SESSİZCE etkisiz (nesne durur)→ RAISE (KIRMIZI)  ← kalemin ta kendisi
  L nesne zaten yoktu                   → "zaten-yoktu" ve sil() HİÇ ÇAĞRILMAZ (sahte "silindi" yok)
  M yayılma: 1. kontrolde var, 2.'de yok→ "silindi-dogrulandi" (yeniden deneme fail-open DEĞİL)
  N ÇÜRÜTME (fault injection): doğrulama silmeden ÖNCEYE alınırsa K vakası YEŞİL yanar mı?
    → çağrı SIRASI ölçülür; sıra bozulursa test KALIR (nöbetçinin nöbetçisi)
  O varlık sondası YETKİ hatası yutmuyor → hata yukarı fırlar (404 ile karıştırılmaz)

K1 ÜYELİK-KALDIRMA YOLU (tools/uyelik-cek.py) — Bucket Lock 409, 30 Tem 2026:
  P 409'da ürün YİNE DE kaldırılır  → tek R2 hatası tüm kaldırmayı İPTAL ETMEZ (asıl kalem)
  Q hepsi 409                       → kaldirma yine de HER ürün için koştu (sıra ölçülür)
  R kuyruk kalıcılığı               → anahtar+sebep dosyaya yazıldı, tekrar denemede deneme=2
  S kuyruk süpürücüsü (K2)          → silinen düşer, silinemeyen SEBEBİYLE kalır
  T denetim artıkları (K4)          → iki lock artığı kuyruğa harmanlandı (idempotent)
  U hatasız yol                     → kuyruk BOŞ kalır, sahte "kuyruga alindi" yok
Bu vakalar AĞSIZDIR: R2 silme fonksiyonu ve duzelt.py çağrısı ENJEKTE edilir; gerçek
R2'ye ne silme ne yazma isteği gider, urunler.json'a DOKUNULMAZ.
"""
import sys, os, io, json, tempfile, importlib.util

MOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2-upload.py")

_spec = importlib.util.spec_from_file_location("r2_upload_mod", MOD_PATH)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

UYELIK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uyelik-cek.py")
_spec_u = importlib.util.spec_from_file_location("uyelik_cek_mod", UYELIK_PATH)
uyelik = importlib.util.module_from_spec(_spec_u)
_spec_u.loader.exec_module(uyelik)

BUCKET = "test-bucket"

# --- Deterministik görsel gövdeleri ------------------------------------------
JPEG_OK = b"\xff\xd8\xff\xe0" + b"\x00" * 3000                 # geçerli JPEG magic + boyut
PNG_OK = b"\x89PNG\r\n\x1a\n" + b"\x00" * 3000                 # geçerli PNG magic + boyut
WEBP_OK = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 3000  # geçerli WebP magic
ZERO = b""                                                     # 0-bayt
HTML_403 = (b"<!DOCTYPE html><html><head><title>403 Forbidden</title></head>"
            b"<body>error 1010 cloudflare</body></html>" + b"x" * 2000)  # >1KB, magic YOK
GARBAGE = bytes(range(256)) * 8                                # 2048B, magic YOK


class FakeS3:
    """put_object'i yakalar; head_object sahte ContentLength döndürür. Ağ yok."""
    def __init__(self, readback_len=None):
        self.puts = []
        self._readback_len = readback_len  # None → son put gövdesinin boyutunu yansıt (dürüst readback)

    def put_object(self, Bucket, Key, Body, ContentType):
        self.puts.append({"Bucket": Bucket, "Key": Key, "len": len(Body), "ContentType": ContentType})

    def head_object(self, Bucket, Key):
        if self._readback_len is not None:
            length = self._readback_len
        else:
            length = None
            for p in reversed(self.puts):
                if p["Key"] == Key:
                    length = p["len"]
                    break
        return {"ContentLength": length}


class _StderrYakala:
    """with bloğu boyunca stderr'i yakalar."""
    def __enter__(self):
        self._old = sys.stderr
        self.buf = io.StringIO()
        sys.stderr = self.buf
        return self

    def __exit__(self, *a):
        sys.stderr = self._old
        return False


# --- Minik test koşucusu ------------------------------------------------------
_gecti = 0
_kaldi = 0


def onayla(kosul, etiket):
    global _gecti, _kaldi
    if kosul:
        _gecti += 1
        print("  [GECTI] " + etiket)
    else:
        _kaldi += 1
        print("  [KALDI] " + etiket)


def reddedilir_mi(s3, key, data):
    """dogrula_ve_yukle RAISE ediyor mu? (True = reddedildi)."""
    try:
        mod.dogrula_ve_yukle(s3, BUCKET, key, data)
        return False
    except Exception:
        return True


# --- Vakalar A-I --------------------------------------------------------------
def vaka_A():
    s3 = FakeS3()
    ct = mod.dogrula_ve_yukle(s3, BUCKET, "urunler/a-1.jpg", JPEG_OK)
    onayla(ct == "image/jpeg", "A: geçerli JPEG ContentType image/jpeg")
    onayla(len(s3.puts) == 1 and s3.puts[0]["ContentType"] == "image/jpeg", "A: put image/jpeg ile çağrıldı")
    onayla(s3.puts[0]["len"] == len(JPEG_OK), "A: readback boyut eşleşti (geçti)")


def vaka_B():
    s3 = FakeS3()
    ct = mod.dogrula_ve_yukle(s3, BUCKET, "urunler/b-1.png", PNG_OK)
    onayla(ct == "image/png", "B: geçerli PNG ContentType image/png")
    onayla(s3.puts[0]["ContentType"] == "image/png", "B: put image/png ile çağrıldı")


def vaka_B2_webp():
    s3 = FakeS3()
    ct = mod.dogrula_ve_yukle(s3, BUCKET, "urunler/b2-1.webp", WEBP_OK)
    onayla(ct == "image/webp", "B2: geçerli WebP ContentType image/webp (bonus)")


def vaka_C():
    s3 = FakeS3()
    red = reddedilir_mi(s3, "urunler/c-1.jpg", ZERO)
    onayla(red, "C: 0-bayt REDDEDİLDİ (R1 boyut)")
    onayla(len(s3.puts) == 0, "C: put ÇAĞRILMADI (fail-closed önce)")


def vaka_D():
    s3 = FakeS3()
    red = reddedilir_mi(s3, "urunler/d-1.jpg", HTML_403)
    onayla(red, "D: 403-HTML gövdesi REDDEDİLDİ (R1 magic yok)")
    onayla(len(s3.puts) == 0, "D: put ÇAĞRILMADI")


def vaka_E():
    s3 = FakeS3()
    red = reddedilir_mi(s3, "urunler/e-1.jpg", GARBAGE)
    onayla(red, "E: çöp (>1KB, magic yok) REDDEDİLDİ (R1)")
    onayla(len(s3.puts) == 0, "E: put ÇAĞRILMADI")


def vaka_F():
    s3 = FakeS3()
    with _StderrYakala() as cap:
        ct = mod.dogrula_ve_yukle(s3, BUCKET, "urunler/f-1.jpg", PNG_OK)  # .jpg ad ama PNG gövde
    uyari = cap.buf.getvalue()
    onayla(ct == "image/png", "F: uyuşmazlıkta ContentType GERÇEK formata (image/png)")
    onayla(len(s3.puts) == 1, "F: yine de yüklendi (hard-reject YOK)")
    onayla("UYARI" in uyari and "PNG" in uyari, "F: stderr LOUD uyarı basıldı")


def vaka_G():
    # put başarılı ama R2 readback ContentLength yanlış → kısmi PUT
    s3 = FakeS3(readback_len=17)
    red = reddedilir_mi(s3, "urunler/g-1.jpg", JPEG_OK)
    onayla(red, "G: readback boyut yanlış REDDEDİLDİ (R4)")
    onayla(len(s3.puts) == 1, "G: put ÇAĞRILDI ama readback yakaladı")


def vaka_H():
    s3 = FakeS3()
    hata = None
    try:
        mod.dogrula_ve_yukle(s3, BUCKET, "urunler/boga-p1", HTML_403)
    except Exception as exc:
        hata = exc
    onayla(isinstance(hata, ValueError) and str(hata).startswith("R1 red:"),
           "H: uzantısız anahtar + 403-HTML R1 ile REDDEDİLDİ")
    onayla(len(s3.puts) == 0, "H: put ÇAĞRILMADI (fail-closed önce)")


def vaka_I():
    s3 = FakeS3()
    ct = mod.dogrula_ve_yukle(s3, BUCKET, "urunler/boga-p1", JPEG_OK)
    onayla(ct == "image/jpeg", "I: uzantısız anahtar + JPEG magic ContentType image/jpeg")
    onayla(len(s3.puts) == 1 and s3.puts[0]["ContentType"] == "image/jpeg",
           "I: put image/jpeg ile çağrıldı")


# --- R5 SİLME KAPISI: J-O ------------------------------------------------------
class SahteKova:
    """Ağsız R2 taklidi. `sessiz` = silme çağrısı BAŞARILI görünür ama nesneyi
    KALDIRMAZ (30 Tem'de canlıda ölçülen sessiz-silme davranışı).
    `gecikme` = nesne ancak N. varlık kontrolünde kaybolur (yayılma/önbellek).
    Her çağrı `izler` listesine yazılır → çağrı SIRASI ölçülebilir (vaka N)."""

    def __init__(self, anahtarlar=(), sessiz=False, gecikme=0, var_mi_hata=None):
        self.nesneler = set(anahtarlar)
        self.sessiz = sessiz
        self.gecikme = gecikme
        self.var_mi_hata = var_mi_hata
        self.izler = []
        self.silindi_sayisi = 0
        self._silme_sonrasi_kontrol = 0

    def var_mi(self, key):
        self.izler.append(("var_mi", key))
        if self.var_mi_hata is not None:
            raise self.var_mi_hata
        if self.silindi_sayisi and not self.sessiz:
            self._silme_sonrasi_kontrol += 1
            if self._silme_sonrasi_kontrol <= self.gecikme:
                return True          # henüz görünmüyor (bayat okuma)
            return False
        return key in self.nesneler

    def sil(self, key):
        self.izler.append(("sil", key))
        self.silindi_sayisi += 1
        if not self.sessiz:
            self.nesneler.discard(key)
        # sessiz=True: çağrı hata VERMEZ ama nesne DURUR (sessiz başarı)


def _bekleme_yok(_saniye):
    return None


def vaka_J():
    kova = SahteKova(["urunler/j-1.jpg"])
    sonuc = mod.sil_ve_dogrula("urunler/j-1.jpg", kova.var_mi, kova.sil, bekle=_bekleme_yok)
    onayla(sonuc == "silindi-dogrulandi", "J: gerçek silme 'silindi-dogrulandi' döndü")
    onayla(("sil", "urunler/j-1.jpg") in kova.izler, "J: sil() çağrıldı")


def vaka_K():
    kova = SahteKova(["urunler/k-1.jpg"], sessiz=True)
    hata = None
    try:
        mod.sil_ve_dogrula("urunler/k-1.jpg", kova.var_mi, kova.sil, bekle=_bekleme_yok)
    except Exception as exc:
        hata = exc
    onayla(isinstance(hata, ValueError) and str(hata).startswith("R5 red:"),
           "K: SESSİZ silme (nesne duruyor) KIRMIZI yandı — RAISE")
    onayla("urunler/k-1.jpg" in kova.nesneler, "K: nesne gerçekten duruyordu (senaryo doğru)")


def vaka_L():
    kova = SahteKova([])                       # anahtar yok
    sonuc = mod.sil_ve_dogrula("urunler/l-1.jpg", kova.var_mi, kova.sil, bekle=_bekleme_yok)
    onayla(sonuc == "zaten-yoktu", "L: olmayan anahtar 'zaten-yoktu' (sahte 'silindi' YOK)")
    onayla(all(iz[0] != "sil" for iz in kova.izler), "L: sil() HİÇ çağrılmadı")


def vaka_M():
    kova = SahteKova(["urunler/m-1.jpg"], gecikme=1)   # ilk kontrolde hâlâ görünüyor
    sonuc = mod.sil_ve_dogrula("urunler/m-1.jpg", kova.var_mi, kova.sil, bekle=_bekleme_yok)
    onayla(sonuc == "silindi-dogrulandi", "M: yayılma gecikmesi yeniden denemeyle geçildi")
    kontroller = [i for i, iz in enumerate(kova.izler) if iz[0] == "var_mi"]
    sil_i = [i for i, iz in enumerate(kova.izler) if iz[0] == "sil"][0]
    onayla(len([i for i in kontroller if i > sil_i]) >= 2,
           "M: silmeden SONRA en az 2 bağımsız kontrol yapıldı")


def vaka_N_curutme():
    """Nöbetçinin nöbetçisi: doğrulama silmeden SONRA koşmazsa K vakası sahte-yeşil yanar.
    Burada çağrı SIRASI ölçülür — 'sil'den sonra en az bir 'var_mi' ŞART."""
    kova = SahteKova(["urunler/n-1.jpg"])
    mod.sil_ve_dogrula("urunler/n-1.jpg", kova.var_mi, kova.sil, bekle=_bekleme_yok)
    turler = [iz[0] for iz in kova.izler]
    sil_i = turler.index("sil")
    onayla("var_mi" in turler[sil_i + 1:],
           "N: doğrulama SİLMEDEN SONRA koştu (sıra bozulursa bu KALIR)")
    onayla(turler[:sil_i] == ["var_mi"],
           "N: silmeden ÖNCE de tek bir varlık ölçümü var (L vakasının dayanağı)")


def vaka_O_yetki():
    """Varlık sondası 403/yetki hatasını 'nesne yok' sanmamalı (fail-open olurdu)."""
    class SahteYetkiHatasi(Exception):
        pass
    hata_ornegi = SahteYetkiHatasi("AccessDenied")
    hata_ornegi.response = {"Error": {"Code": "AccessDenied"},
                            "ResponseMetadata": {"HTTPStatusCode": 403}}

    class SahteS3:
        def head_object(self, Bucket, Key):
            raise hata_ornegi

    var_mi = mod.s3_var_mi(SahteS3(), "kova")
    yakalandi = None
    try:
        var_mi("urunler/o-1.jpg")
    except Exception as exc:
        yakalandi = exc
    onayla(yakalandi is hata_ornegi, "O: yetki hatası YUTULMADI, yukarı fırladı")

    # 404 ise düzgünce False dönmeli (yanlış-kırmızı üretmesin)
    yok = SahteYetkiHatasi("NoSuchKey")
    yok.response = {"Error": {"Code": "NoSuchKey"},
                    "ResponseMetadata": {"HTTPStatusCode": 404}}

    class Sahte404:
        def head_object(self, Bucket, Key):
            raise yok

    onayla(mod.s3_var_mi(Sahte404(), "kova")("x") is False,
           "O: gerçek 404 False döndü (yanlış-kırmızı yok)")


# --- K1 ÜYELİK-KALDIRMA YOLU: P-U ---------------------------------------------
BASE = "https://media.pruvo3d.com/"


class Lock409(Exception):
    """R2 Bucket Lock reddi (HTTP 409 ObjectLockedByBucketPolicy) taklidi."""
    def __init__(self, key):
        Exception.__init__(self, "An error occurred (ObjectLockedByBucketPolicy) when "
                                 "calling the DeleteObject operation: %s" % key)


def _urun(uid, n=2):
    return {"id": uid, "gorseller": [BASE + "urunler/%s-%d.jpg" % (uid, i)
                                     for i in range(1, n + 1)]}


class SahteKaldirma:
    """duzelt.py --sil yerine geçer; çağrı SIRASINI izler (vaka Q'nun dayanağı)."""
    def __init__(self, izler, patlayan=()):
        self.izler = izler
        self.patlayan = set(patlayan)

    def __call__(self, uid):
        self.izler.append(("kaldir", uid))
        if uid in self.patlayan:
            raise RuntimeError("duzelt.py cikis kodu 1")


def _kuyruk_yolu(ad="kuyruk.json"):
    d = tempfile.mkdtemp(prefix="pruvo-kuyruk-")
    return os.path.join(d, ad)


def _sessiz(*_a, **_k):
    return None


def vaka_P_409_urun_yine_kalkar():
    """ASIL KALEM: ilk görselde 409 → eskiden betik patlar, ürün canlıda kalırdı."""
    izler = []
    hedef = [_urun("kilitli-a"), _urun("kilitli-b")]
    ilk = hedef[0]["gorseller"][0][len(BASE):]

    def sil_ve_dogrula(key):
        izler.append(("r2", key))
        if key == ilk:
            raise Lock409(key)
        return "silindi-dogrulandi"

    yol = _kuyruk_yolu()
    sonuc = uyelik.kaldirma_akisi(hedef, SahteKaldirma(izler), base=BASE,
                                  sil_ve_dogrula=sil_ve_dogrula,
                                  kuyruk_yolu=yol, yaz=_sessiz)
    onayla(sonuc["kaldirilan"] == ["kilitli-a", "kilitli-b"],
           "P: 409'a RAGMEN her iki urun de urunler.json'dan kaldirildi")
    onayla(sonuc["r2_kuyruk"] == [ilk], "P: yalnizca 409 alan anahtar kuyruga alindi")
    onayla(len(sonuc["r2_basarili"]) == 3, "P: 409 sonrasi DIGER gorseller silinmeye devam etti")
    kayit = [k for k in json.load(open(yol, encoding="utf-8")) if k["anahtar"] == ilk]
    onayla(len(kayit) == 1 and "ObjectLockedByBucketPolicy" in kayit[0]["sebep"],
           "P: kuyruk kaydinda SEBEP (409) yaziyor")
    onayla(kayit[0]["urun"] == "kilitli-a", "P: kuyruk kaydi hangi urunden geldigini tasiyor")


def vaka_Q_hepsi_409():
    """Kova geneli lock: TÜM silmeler 409 → kaldırma adımına yine de ULAŞILIR."""
    izler = []
    hedef = [_urun("hep-a"), _urun("hep-b"), _urun("hep-c")]

    def sil_ve_dogrula(key):
        izler.append(("r2", key))
        raise Lock409(key)

    sonuc = uyelik.kaldirma_akisi(hedef, SahteKaldirma(izler), base=BASE,
                                  sil_ve_dogrula=sil_ve_dogrula,
                                  kuyruk_yolu=_kuyruk_yolu(), yaz=_sessiz)
    kaldirilanlar = [iz for iz in izler if iz[0] == "kaldir"]
    onayla(len(kaldirilanlar) == 3, "Q: her R2 silmesi patlarken bile 3 urunun 3'u de kaldirildi")
    onayla(len(sonuc["r2_kuyruk"]) == 6 and not sonuc["r2_basarili"],
           "Q: 6 gorselin 6'si da kuyruga alindi, sahte 'silindi' YOK")
    turler = [iz[0] for iz in izler]
    onayla(turler.index("kaldir") > 0 and set(turler[:turler.index("kaldir")]) == {"r2"},
           "Q: sira DOGRU — once R2 denemesi, SONRA kaldirma (sira bozulursa bu KALIR)")


def vaka_R_kuyruk_kalici():
    yol = _kuyruk_yolu()
    uyelik.kuyruga_ekle("urunler/r-1.jpg", "Lock409: kilitli", urun="r", yol=yol)
    uyelik.kuyruga_ekle("urunler/r-1.jpg", "Lock409: hala kilitli", urun="r", yol=yol)
    kayitlar = json.load(open(yol, encoding="utf-8"))
    onayla(len(kayitlar) == 1, "R: ayni anahtar TEKILLESTIRILDI (kuyruk sismiyor)")
    onayla(kayitlar[0]["deneme"] == 2 and kayitlar[0]["sebep"] == "Lock409: hala kilitli",
           "R: deneme sayaci ve son sebep guncellendi")


def vaka_S_kuyruk_supurucu():
    """K2: retention dolunca süpür — silinen düşer, silinemeyen sebebiyle KALIR."""
    yol = _kuyruk_yolu()
    uyelik.kuyruga_ekle("urunler/s-acildi.jpg", "Lock409", urun="s", yol=yol)
    uyelik.kuyruga_ekle("urunler/s-kilitli.jpg", "Lock409", urun="s", yol=yol)

    def sil_ve_dogrula(key):
        if key.endswith("s-kilitli.jpg"):
            raise Lock409(key)
        return "silindi-dogrulandi"

    dusen, kalan = uyelik.kuyruk_supur(sil_ve_dogrula, kuyruk_yolu=yol, yaz=_sessiz)
    kalan_anahtarlar = {k["anahtar"] for k in json.load(open(yol, encoding="utf-8"))}
    onayla("urunler/s-acildi.jpg" in dusen, "S: retention dolan anahtar silindi ve kuyruktan DUSTU")
    onayla("urunler/s-acildi.jpg" not in kalan_anahtarlar, "S: dusen anahtar dosyadan da silindi")
    onayla("urunler/s-kilitli.jpg" in kalan_anahtarlar,
           "S: hala kilitli anahtar kuyrukta KALDI (sessizce kaybolmadi)")
    kilitli = [k for k in kalan if k["anahtar"] == "urunler/s-kilitli.jpg"][0]
    onayla("ObjectLockedByBucketPolicy" in kilitli["sebep"] and kilitli["deneme"] == 2,
           "S: kalan kaydin sebebi ve deneme sayaci guncellendi")


def vaka_T_denetim_artiklari():
    """K4: lock yüzünden silinemeyen iki denetim sondası kuyruğa harmanlanır."""
    yol = _kuyruk_yolu()
    uyelik.denetim_artiklarini_harmanla(yol=yol)
    once = {k["anahtar"] for k in json.load(open(yol, encoding="utf-8"))}
    uyelik.denetim_artiklarini_harmanla(yol=yol)                  # idempotens
    sonra = json.load(open(yol, encoding="utf-8"))
    beklenen = {a for a, _s in uyelik.DENETIM_ARTIKLARI}
    onayla(beklenen and beklenen <= once, "T: denetim artiklari kuyruga eklendi")
    onayla("urunler/lock-sonda-30tem-88930b3b.jpg" in once
           and "denetim/lock-kapsam-sonda-30tem-7c98a1db.jpg" in once,
           "T: 30 Tem lock sondasi + kapsam sondasi anahtarlari kuyrukta")
    onayla(len(sonra) == len(once), "T: ikinci harmanlama MUKERRER kayit uretmedi")


def vaka_U_hatasiz_yol():
    """Yanlış-kırmızı nöbeti: hata yokken kuyruk BOŞ kalmalı."""
    izler = []
    hedef = [_urun("temiz-a")]
    yol = _kuyruk_yolu()
    sonuc = uyelik.kaldirma_akisi(hedef, SahteKaldirma(izler), base=BASE,
                                  sil_ve_dogrula=lambda k: "silindi-dogrulandi",
                                  kuyruk_yolu=yol, yaz=_sessiz)
    onayla(sonuc["r2_kuyruk"] == [] and not os.path.exists(yol),
           "U: hatasiz yolda kuyruk dosyasi HIC olusmadi")
    onayla(sonuc["kaldirilan"] == ["temiz-a"] and not sonuc["kaldirilamayan"],
           "U: urun kaldirildi, kaldirilamayan YOK")


def main():
    print("== r2-upload doğrulama kabul testi ==")
    for fn in (vaka_A, vaka_B, vaka_B2_webp, vaka_C, vaka_D, vaka_E, vaka_F, vaka_G,
               vaka_H, vaka_I,
               vaka_J, vaka_K, vaka_L, vaka_M, vaka_N_curutme, vaka_O_yetki,
               vaka_P_409_urun_yine_kalkar, vaka_Q_hepsi_409, vaka_R_kuyruk_kalici,
               vaka_S_kuyruk_supurucu, vaka_T_denetim_artiklari, vaka_U_hatasiz_yol):
        fn()
    print("---")
    print("GECTI=%d  KALDI=%d" % (_gecti, _kaldi))
    if _kaldi:
        print("SONUC: BASARISIZ")
        sys.exit(1)
    print("SONUC: TUM VAKALAR GECTI (exit 0)")
    sys.exit(0)


if __name__ == "__main__":
    main()
