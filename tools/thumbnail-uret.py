#!/usr/bin/env python3
"""Kapak görseli küçük thumbnail üreteci — bkz. DEVAM.md / görev spec'i."""

import argparse
import importlib.util
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

_kilit = threading.Lock()
_sayac = {"uretilen": 0, "atlanan": 0, "hata": 0}


def thumb_anahtari(key):
    kok, uzanti = os.path.splitext(key)
    return kok + "-thumb" + uzanti


def anahtar_of(url, public_base):
    onek = public_base.rstrip("/") + "/"
    if not url.startswith(onek):
        return None
    return url[len(onek):]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if args.limit is not None and args.limit < 0:
        ap.error("--limit negatif olamaz")

    with open(os.path.join(REPO, ".r2-credentials.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret"],
        region_name="auto",
    )
    var_mi = r2_upload.s3_var_mi(s3, cfg["bucket"])

    with open(os.path.join(REPO, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)

    kapaklar, gorulen = [], set()
    for urun in urunler:
        gorseller = urun.get("gorseller") or []
        if not gorseller or gorseller[0] in gorulen:
            continue
        gorulen.add(gorseller[0])
        kapaklar.append(gorseller[0])
    if args.limit is not None:
        kapaklar = kapaklar[:args.limit]

    toplam = len(kapaklar)
    print("TOPLAM_BENZERSIZ_KAPAK=%d" % toplam, flush=True)

    def gorev(cover):
        try:
            sonuc = bir_urun_isle(
                s3, cfg["bucket"], cfg["public_base"], var_mi, cover
            )
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

    with ThreadPoolExecutor(max_workers=WORKERS) as havuz:
        gelecekler = [havuz.submit(gorev, cover) for cover in kapaklar]
        for _ in as_completed(gelecekler):
            pass

    print(
        "THUMB_URETILEN=%d ATLANAN=%d HATA=%d"
        % (_sayac["uretilen"], _sayac["atlanan"], _sayac["hata"])
    )


if __name__ == "__main__":
    main()
