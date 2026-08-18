#!/usr/bin/env python3
"""Gizli kaynak defterinde eksik uretici linkini tamamlar.

Yalnizca `.urun-kaynaklari.json` yazar; `urunler.json`'a dokunulmaz.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s\"'<>]+")
TRIM_RE = re.compile(r"[.,;:;)\]}\"']+$")

BEYAN_ELDE_YOK = {
    "bmw-arka-koltuk-destek-klipsi-52209099555",
    "bmw-torpido-trim-klipsi-51458266814",
    "masaustu-mengene-kelepceli",
    "volvo-m56-aks-ke-esi-akma-aparat-9995541",
    "volvo-xc70-bagaj-ask-s-30740567",
}

LINK_BEKLENMEZ_TUR = {
    "ozgun-tasarim",
    "ozgun-model-okan",
    "yedek-parca",
    "kendi-tasarim",
}


def cikar_url(metin):
    """Metinden ilk URL'yi ayikla; yoksa None don."""
    if not isinstance(metin, str):
        return None
    eslesme = URL_RE.search(metin)
    if not eslesme:
        return None
    url = eslesme.group(0)
    url = TRIM_RE.sub("", url)
    return url


def sha256_dosya(yol):
    h = hashlib.sha256()
    try:
        with open(yol, "rb") as f:
            for parca in iter(lambda: f.read(65536), b""):
                h.update(parca)
    except FileNotFoundError:
        return None
    return h.hexdigest()


def host_uyusuyor(kaynak, url):
    """URL host'u kaynak platformuyla uyusuyorsa True."""
    if not isinstance(kaynak, str) or not isinstance(url, str):
        return False
    try:
        host = urlparse(url).hostname
    except Exception:
        return False
    if not host:
        return False
    return host.lower().split(".")[0] == kaynak.lower().split(".")[0]


def link_beklenmez(deger):
    """§1b yapisal imzalarindan biri tutuyorsa True."""
    if not isinstance(deger, dict):
        return False
    # Imza 1: fiziksel satin alma
    if deger.get("alis_fiyati") is not None and deger.get("alt_tur") is not None:
        return True
    # Imza 2: kendi uretimimiz
    if deger.get("tur") in LINK_BEKLENMEZ_TUR:
        return True
    return False


def siniflandir(kayitlar):
    nottan = 0
    dizgeden = 0
    varyantta = 0
    link_beklenmez_say = 0
    host_uyusmaz = 0
    elde_yok = set()
    bozuk = 0
    onarilabilir = {}  # id -> (eylem, url, orijinal)

    for id_, deger in kayitlar.items():
        if isinstance(deger, str):
            orijinal = deger.strip()
            url = cikar_url(orijinal)
            if url and orijinal.startswith(url):
                dizgeden += 1
                onarilabilir[id_] = ("dizge", url, orijinal)
            else:
                bozuk += 1
            continue

        if not isinstance(deger, dict):
            bozuk += 1
            continue

        mevcut_link = deger.get("link") or ""
        if mevcut_link:
            continue

        not_metni = deger.get("not") or ""
        url_not = cikar_url(not_metni)
        kaynak = deger.get("kaynak", "")
        if url_not:
            if not host_uyusuyor(kaynak, url_not):
                host_uyusmaz += 1
                continue
            nottan += 1
            onarilabilir[id_] = ("not", url_not, None)
            continue

        varyantlar = deger.get("varyantlar")
        if isinstance(varyantlar, list) and varyantlar:
            hepsi_url = True
            for v in varyantlar:
                if not isinstance(v, dict) or not cikar_url(v.get("kaynak", "")):
                    hepsi_url = False
                    break
            if hepsi_url:
                varyantta += 1
                continue

        if link_beklenmez(deger):
            link_beklenmez_say += 1
            continue

        elde_yok.add(id_)

    linksiz_obje = 0
    for deger in kayitlar.values():
        if isinstance(deger, dict) and not (deger.get("link") or ""):
            linksiz_obje += 1

    return {
        "kayit": len(kayitlar),
        "linksiz_obje": linksiz_obje,
        "nottan": nottan,
        "dizgeden": dizgeden,
        "varyantta": varyantta,
        "link_beklenmez": link_beklenmez_say,
        "host_uyusmaz": host_uyusmaz,
        "elde_yok": elde_yok,
        "bozuk": bozuk,
        "onarilabilir": onarilabilir,
    }


def rapor_satir(sonuc, uygula=False, onarilan=None):
    parcalar = [
        f"KAYIT={sonuc['kayit']}",
        f"LINKSIZ_OBJE={sonuc['linksiz_obje']}",
        f"NOTTAN={sonuc['nottan']}",
        f"DIZGEDEN={sonuc['dizgeden']}",
        f"VARYANTTA_KAYITLI={sonuc['varyantta']}",
        f"LINK_BEKLENMEZ={sonuc['link_beklenmez']}",
        f"ELDE_YOK={len(sonuc['elde_yok'])}",
        f"BOZUK={sonuc['bozuk']}",
    ]
    if uygula:
        parcalar.append(
            f"ONARILAN={onarilan if onarilan is not None else len(sonuc['onarilabilir'])}"
        )
        parcalar.append("PUBLIC_DOSYA_DOKUNULMADI=EVET")
    return " ".join(parcalar)


def main():
    aciklama = argparse.ArgumentParser(
        description="Gizli kaynak defterinde eksik uretici linkini tamamlar."
    )
    aciklama.add_argument(
        "--defter",
        default=None,
        help=".urun-kaynaklari.json yolu (varsayilan: repo kokundeki gizli dosya)",
    )
    aciklama.add_argument(
        "--uygula",
        action="store_true",
        help="Yazma modu; verilmediyse yalnizca kontrol yapar.",
    )
    aciklama.add_argument(
        "--kendini-test",
        action="store_true",
        help="Kabul testini calistir.",
    )
    secenekler = aciklama.parse_args()

    if secenekler.kendini_test:
        test_betik = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "kaynak-link-test.py"
        )
        return subprocess.run([sys.executable, test_betik]).returncode

    repo_koku = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if secenekler.defter:
        defter_yolu = os.path.abspath(secenekler.defter)
    else:
        defter_yolu = os.path.join(repo_koku, ".urun-kaynaklari.json")

    defter_dizini = os.path.dirname(defter_yolu)
    kilit_yolu = os.path.join(defter_dizini, ".urunler.lock")
    urunler_yolu = os.path.join(defter_dizini, "urunler.json")

    if not os.path.exists(defter_yolu):
        print(f"🔴 DEFTER_YOK: {defter_yolu}", file=sys.stderr)
        return 2

    lock_fd = open(kilit_yolu, "a+")
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
    try:
        sha_once = sha256_dosya(urunler_yolu)

        with open(defter_yolu, "r", encoding="utf-8") as f:
            kayitlar = json.load(f)

        ilk = siniflandir(kayitlar)

        if not secenekler.uygula:
            print(rapor_satir(ilk))
            if ilk["elde_yok"] != BEYAN_ELDE_YOK:
                fazla = ilk["elde_yok"] - BEYAN_ELDE_YOK
                eksi = BEYAN_ELDE_YOK - ilk["elde_yok"]
                if fazla:
                    print(f"🔴 BEYAN_DISI_ELDE_YOK: {len(fazla)}", file=sys.stderr)
                if eksi:
                    print(f"🔴 BEYAN_KARSILIGI_YOK: {len(eksi)}", file=sys.stderr)
                print("HUKUM=KIRMIZI")
                return 1
            if ilk["nottan"] or ilk["dizgeden"] or ilk["bozuk"] or ilk["host_uyusmaz"]:
                print("HUKUM=EKSIK")
                return 1
            print("HUKUM=TAM")
            return 0

        # Test icin yarismayi acik hale getiren gecikme (sadece env verildiginde)
        # Siniflandirma ile kilit altinda yeniden okuma ARASINA konur ki test
        # sureci yaris penceresinde defteri degistirebilsin. Mutant (M5) bu
        # yeniden okumayi kaldirirsa, yaris penceresindeki degisikligi gormez.
        if os.environ.get("PRUVO_KAYNAK_LINK_RACE_TEST"):
            time.sleep(0.2)

        # Uygula modu: kilit altinda yeniden oku (yarismaya karsi)
        with open(defter_yolu, "r", encoding="utf-8") as f:
            kayitlar = json.load(f)

        onarilan = 0
        for id_, (eylem, url, orijinal) in ilk["onarilabilir"].items():
            mevcut = kayitlar.get(id_)
            if isinstance(mevcut, dict):
                if not (mevcut.get("link") or ""):
                    kayitlar[id_]["link"] = url
                    onarilan += 1
            elif isinstance(mevcut, str):
                yeni = {"link": url}
                if orijinal and orijinal != url:
                    yeni["not"] = orijinal
                kayitlar[id_] = yeni
                onarilan += 1

        fd, tmp_yolu = tempfile.mkstemp(
            prefix=f"tmp-{os.getpid()}-", dir=defter_dizini
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(kayitlar, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp_yolu, defter_yolu)
            tmp_yolu = None
        finally:
            if tmp_yolu and os.path.exists(tmp_yolu):
                os.unlink(tmp_yolu)

        # Yazim sonrasi teyit (ayni kilit altinda)
        with open(defter_yolu, "r", encoding="utf-8") as f:
            kayitlar = json.load(f)
        son = siniflandir(kayitlar)

        sha_sonra = sha256_dosya(urunler_yolu)
        if sha_once != sha_sonra:
            print(f"🔴 urunler.json DEGISTI", file=sys.stderr)
            print(f"  once={sha_once}", file=sys.stderr)
            print(f"  sonra={sha_sonra}", file=sys.stderr)
            print("HUKUM=KIRMIZI")
            return 3

        if son["kayit"] < ilk["kayit"]:
            print(f"🔴 KAYIT_AZALDI: once={ilk['kayit']} sonra={son['kayit']}", file=sys.stderr)
            print("HUKUM=KIRMIZI")
            return 4

        print(rapor_satir(son, uygula=True, onarilan=onarilan))
        if son["elde_yok"] != BEYAN_ELDE_YOK:
            fazla = son["elde_yok"] - BEYAN_ELDE_YOK
            eksi = BEYAN_ELDE_YOK - son["elde_yok"]
            if fazla:
                print(f"🔴 BEYAN_DISI_ELDE_YOK: {len(fazla)}", file=sys.stderr)
            if eksi:
                print(f"🔴 BEYAN_KARSILIGI_YOK: {len(eksi)}", file=sys.stderr)
            print("HUKUM=KIRMIZI")
            return 1
        if son["nottan"] or son["dizgeden"] or son["bozuk"]:
            print("HUKUM=KIRMIZI")
            return 1
        print("HUKUM=TAM")
        return 0
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    sys.exit(main())
