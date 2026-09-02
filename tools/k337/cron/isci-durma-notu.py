#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K337 — DURMA NOTU YAZICISI (28 Agu 2026, cip KraL-K337Butce-28Agu).

NEDEN VAR
---------
Tur tavani kesildiginde isci.sh `--resume` ile bir KAPANIS CAGRISI yapip
isciye "durma noktasi yaz" diyordu. Butce tavani kesildiginde ise HICBIR
sey yazilmiyordu: is nerede kaldi, hangi adim bitti, devami nasil
yazilir -- bilinmiyordu (K337 taban olcumu, 28 Agu: 2 kesinti / 0 not).

Bu arac, kapanis yordaminin DETERMINISTIK yarisidir: cagri hic
kosmasa/dusse bile diskte BAYT>0 bir not kalir. LLM kapanis cagrisi
notu ZENGINLESTIRIR, YERINE GECMEZ.

🔴 OLCULMUS DERS ([[isci-tur-tavani-1500sn]] 27 Agu eki): butce tavani
ISI OLDURMEZ, KAPANISI KESER -- kesilen turun commit'i cogu zaman
DUSMUSTUR. Bu yuzden notun en onemli bolumu turun kendi iddiasi degil,
AGACIN OLCULEN HALIDIR: `git log` + `git status` + uzak dal farki.
`rc=1` gorup "is yapilmadi" demek YANLIS teshistir; not bunu yazili
olarak soyler.

Kullanim:
    isci-durma-notu.py --hedef <yol> --hal <HAL> --ev <kok> --etiket <e>
        --spec <yol> --oturum <id> --tur-cikti <yol> --rc <n>
        --sure <sn> --butce <usd> [--kuyruk <satir>]

Cikis: 0 = not yazildi (bayt>0) · 2 = yazilamadi.
"""

import argparse
import datetime
import os
import subprocess
import sys

KUYRUK_VARSAYILAN = 60

# HAL -> notun basligindaki insan cumlesi (tek kaynak).
HAL_CUMLESI = {
    "BUTCE_TAVANI": "KOSUM BUTCE TAVANINDA KESILDI (para bitti; motor SAGLAM)",
    "TUR_TAVANI": "KOSUM TUR TAVANINDA KESILDI (zaman/tur asimi)",
    "ICRA_HATASI": "KOSUM ICRA HATASIYLA DUSTU",
    "HATALI_SONUC": "KOSUM HATALI SONUC ZARFIYLA DONDU",
    "YAPISAL_CIKTI_HATASI": "KOSUM YAPISAL CIKTI HATASIYLA DUSTU",
    "OLCULEMEDI": "KOSUMUN HALI OLCULEMEDI (zarf yok)",
    "BILINMEYEN_HAL": "KOSUM TANINMAYAN BIR HALLE DONDU",
}


def _kos(argv, cwd=None):
    """Kucuk bir komut kosar; hata halinde ADIYLA bir dize doner."""
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=30)
    except Exception as e:  # noqa: BLE001
        return "OLCULEMEDI (%s)" % type(e).__name__
    cikti = (p.stdout or "").strip()
    if p.returncode != 0 and not cikti:
        return "OLCULEMEDI (rc=%d)" % p.returncode
    return cikti or "(bos)"


def agac_hali(ev):
    if not ev or not os.path.isdir(os.path.join(ev, ".git")):
        # worktree'de .git bir DOSYADIR; ikisini de kabul et
        if not (ev and os.path.exists(os.path.join(ev, ".git"))):
            return {"dal": "OLCULEMEDI (git yok)", "son_commit": "OLCULEMEDI",
                    "durum": "OLCULEMEDI", "uzak_fark": "OLCULEMEDI"}
    return {
        "dal": _kos(["git", "rev-parse", "--abbrev-ref", "HEAD"], ev),
        "son_commit": _kos(["git", "log", "--oneline", "-3"], ev),
        "durum": _kos(["git", "status", "--short"], ev),
        "uzak_fark": _kos(
            ["git", "log", "--oneline", "-3", "@{u}..HEAD"], ev),
    }


def kuyruk(yol, satir_sayisi):
    if not yol or not os.path.isfile(yol):
        return "OLCULEMEDI (tur ciktisi yok: %s)" % (yol or "-")
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            satirlar = f.read().splitlines()
    except OSError as e:
        return "OLCULEMEDI (%s)" % type(e).__name__
    if not satirlar:
        return "(tur ciktisi BOS)"
    return "\n".join(satirlar[-satir_sayisi:])


def not_metni(ns):
    simdi = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    agac = agac_hali(ns.ev)
    cumle = HAL_CUMLESI.get(ns.hal, "KOSUM %s HALIYLE DURDU" % ns.hal)
    return """# DURMA NOTU — %(etiket)s

**Uretildi:** %(simdi)s · **HAL:** `%(hal)s` · **rc:** `%(rc)s` · **sure:** `%(sure)s sn` · **butce tavani:** `%(butce)s USD`

> %(cumle)s

## (1) BU TUR NEREDE KALDI — AGACIN OLCULEN HALI
🔴 Turun kendi iddiasi DEGIL, agactan OKUNAN sudur. Butce tavani
kapanisi keser, isi degil: commit cogu zaman DUSMUSTUR.

- **ev:** `%(ev)s`
- **dal:** `%(dal)s`
- **son 3 commit:**
```
%(son_commit)s
```
- **calisma agaci (`git status --short`):**
```
%(durum)s
```
- **uzaga GITMEMIS commit'ler (`@{u}..HEAD`):**
```
%(uzak_fark)s
```

## (2) TAMAMLANAN ADIM — KANIT NEREDE
- **spec:** `%(spec)s`
- **oturum kimligi:** `%(oturum)s`
- **turun tam ciktisi:** `%(tur_cikti)s`
- **son %(kuyruk_sayisi)d satir:**
```
%(kuyruk)s
```

## (3) DEVAMI NASIL YAZILIR
1. ONCE agaci OKU: yukaridaki `son 3 commit` + `git status` -- is
   buyuk ihtimalle DURUYOR.
2. Spec'i, YAPILMIS adimlari CIKARARAK yeniden dilimle. Ayni spec'i
   ayni haliyle tekrar kosturmak yapilan isi TEKRAR ettirir.
3. Yeni dilim, kalan tek isi tarif etsin; kabul olcutu ayni kalsin.

## (4) IDEMPOTENS NOTU
- Yeniden kosuldugunda **BASTAN BASLAMA**: bu notun (1) bolumundeki
  commit'ler zaten inmistir.
- Ayni yamayi ikinci kez uygulamak icerigi COGALTABILIR
  (`capa subset yeni` sinifi) -- once `--durum`/`--kuru` ile OLC.
- Sayaclari ELLE sifirlama; kesinti motorun sagligi hakkinda HICBIR
  sey soylemez.
""" % {
        "etiket": ns.etiket, "simdi": simdi, "hal": ns.hal, "rc": ns.rc,
        "sure": ns.sure, "butce": ns.butce, "cumle": cumle, "ev": ns.ev,
        "dal": agac["dal"], "son_commit": agac["son_commit"],
        "durum": agac["durum"], "uzak_fark": agac["uzak_fark"],
        "spec": ns.spec, "oturum": ns.oturum or "yok",
        "tur_cikti": ns.tur_cikti or "yok",
        "kuyruk_sayisi": ns.kuyruk,
        "kuyruk": kuyruk(ns.tur_cikti, ns.kuyruk),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--hedef", required=True)
    ap.add_argument("--hal", required=True)
    ap.add_argument("--ev", default="")
    ap.add_argument("--etiket", default="etiketsiz")
    ap.add_argument("--spec", default="")
    ap.add_argument("--oturum", default="")
    ap.add_argument("--tur-cikti", dest="tur_cikti", default="")
    ap.add_argument("--rc", default="?")
    ap.add_argument("--sure", default="?")
    ap.add_argument("--butce", default="?")
    ap.add_argument("--kuyruk", type=int, default=KUYRUK_VARSAYILAN)
    ns = ap.parse_args(argv)

    metin = not_metni(ns)
    dizin = os.path.dirname(ns.hedef)
    if dizin:
        try:
            os.makedirs(dizin, exist_ok=True)
        except OSError as e:
            sys.stderr.write("HATA: durma notu dizini acilamadi: %s\n" % e)
            return 2
    try:
        with open(ns.hedef, "w", encoding="utf-8") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(ns.hedef, 0o600)
    except OSError as e:
        sys.stderr.write("HATA: durma notu yazilamadi: %s\n" % e)
        return 2
    bayt = os.path.getsize(ns.hedef)
    print("DURMA_NOTU hal=%s yol=%s bayt=%d" % (ns.hal, ns.hedef, bayt))
    return 0 if bayt > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
