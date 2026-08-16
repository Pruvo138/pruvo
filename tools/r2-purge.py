#!/usr/bin/env python3
"""Cloudflare'de R2 medya URL'lerinin kenar onbellegini tekil temizler."""

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request


TOKEN_PATH = pathlib.Path("/Users/okan/.claude/cron/.cf-purge-token")
ZONE_ID = "d3a78b8c8ce2a25c127bf02e728ac7b1"
PURGE_URL = "https://api.cloudflare.com/client/v4/zones/%s/purge_cache" % ZONE_ID
MEDIA_BASE = "https://media.pruvo3d.com/"
GRUP_BOYUTU = 30
ANAHTAR_DESENI = re.compile(r"[A-Za-z0-9._/-]+\Z")


def argumanlari_oku(argv):
    parser = argparse.ArgumentParser(
        description="Cloudflare onbelleginden tekil R2 dosyalarini temizle."
    )
    parser.add_argument("urls", nargs="*", metavar="URL")
    parser.add_argument(
        "--anahtar",
        action="append",
        default=[],
        metavar="R2_ANAHTARI",
        help="R2 anahtarini media.pruvo3d.com URL'sine cevirir; tekrarlanabilir.",
    )
    return parser.parse_args(argv)


def jeton_oku():
    try:
        jeton = TOKEN_PATH.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None
    return jeton or None


def anahtari_url_yap(anahtar):
    parcalar = anahtar.split("/")
    if (
        not anahtar.strip()
        or ANAHTAR_DESENI.fullmatch(anahtar) is None
        or anahtar.startswith("/")
        or anahtar.endswith("/")
        or "//" in anahtar
        or not parcalar
        or any(not parca or parca in (".", "..") for parca in parcalar)
    ):
        raise ValueError("ANAHTAR GECERSIZ")
    return MEDIA_BASE + anahtar


def grup_purge(urls, jeton):
    govde = json.dumps({"files": urls}).encode("utf-8")
    istek = urllib.request.Request(
        PURGE_URL,
        data=govde,
        headers={
            "Authorization": "Bearer %s" % jeton,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(istek) as yanit:
            veri = json.loads(yanit.read().decode("utf-8"))
        return veri.get("success") is True
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            print("YETKISIZ (401)", file=sys.stderr)
        else:
            print("HTTP HATASI (%d)" % exc.code, file=sys.stderr)
    except urllib.error.URLError:
        print("AG HATASI", file=sys.stderr)
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, OSError):
        print("YANIT HATASI", file=sys.stderr)
    return False


def main(argv=None):
    args = argumanlari_oku(argv)
    try:
        anahtar_urlleri = [anahtari_url_yap(anahtar) for anahtar in args.anahtar]
    except ValueError:
        print("ANAHTAR GECERSIZ")
        return 2
    urls = list(args.urls) + anahtar_urlleri

    if not urls:
        print("URL YOK")
        return 2

    jeton = jeton_oku()
    if jeton is None:
        print("JETON YOK")
        return 2

    gruplar = [urls[i:i + GRUP_BOYUTU] for i in range(0, len(urls), GRUP_BOYUTU)]
    basarili = 0
    for sira, grup in enumerate(gruplar, start=1):
        sonuc = grup_purge(grup, jeton)
        basarili += int(sonuc)
        print("GRUP=%d SUCCESS=%s" % (sira, str(sonuc).lower()))

    hata = len(gruplar) - basarili
    print("PURGE_TOPLAM=%d BASARILI=%d HATA=%d" % (len(urls), basarili, hata))
    return 1 if hata else 0


if __name__ == "__main__":
    raise SystemExit(main())
