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
"""
import sys, os, io, importlib.util

MOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2-upload.py")

_spec = importlib.util.spec_from_file_location("r2_upload_mod", MOD_PATH)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

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


def main():
    print("== r2-upload doğrulama kabul testi ==")
    for fn in (vaka_A, vaka_B, vaka_B2_webp, vaka_C, vaka_D, vaka_E, vaka_F, vaka_G,
               vaka_H, vaka_I):
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
