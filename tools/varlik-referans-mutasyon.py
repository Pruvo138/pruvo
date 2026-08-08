#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — kiyas referansi kaydinin BOZUK sekilleri GERCEKTEN rc=2 mi veriyor.

    python3 tools/varlik-referans-mutasyon.py

NEDEN REPODA DURUYOR: anlatilan bir batarya kanit degildir
([[mutasyon-kaniti-yeniden-uretilebilir]]). CI ADIMI DEGILDIR — kapinin kendi ic
nobetcisi (`varlik-test.py::referans_hukmu_dogrula`, HER kosumda) hukmu ayrica olcer;
burasi hukmun UCTAN UCA (gercek dosya + gercek kapi cikis kodu) karsiligini olcer.

🔴 OLCULEN ARIZA (8 Agu 2026): gecerlilik IKI ayri yerde, IKI ayri kuralla tanimliydi
(kayit okuyucusu + kapinin kendi yeniden-ayristirmasi). Aradaki bosluktan IKI sekil
FAIL-OPEN geciyordu:
  · `"ref":"abc"`  -> rc=0 VE ekrana `KAYITLI aa1146605f` yaziyordu (YANLIS BEYAN)
  · kayit bir JSON DIZISI -> rc=0 VE "kayit dosyasi YOK" diyordu (dosya VARDI)
Ikisi de burada VAKA olarak durur: "bozuk kayit" tek sekille denenirse sinif kapanmaz
([[tekil-yama-sinifi-kapatmaz]]).

KABUL (iki yonlu):
  · VAKALAR'daki her bozuk sekil TEK BASINA rc=2 (OLCULEMEDI) vermeli.
    🔴 SAYI METINDE SABIT YAZILMAZ: 8 Agu 2026'da bu satir ile son rapor satiri "bes bozuk
    sekil" diyordu, oysa M1..M6 = ALTI vaka kosuyordu. Bayat sayi bu depoda yanlis guven
    verir ([[hukum-yanlis-birimde]]); rapor satiri artik len(VAKALAR)'dan TURETILIR.
  · COKME KIRMIZI SAYILMAZ: rc=2 sart, ayrica raporda GECERSIZ teshisi aranir; traceback
    ya da baska bir rc "mutant dustu" DEMEK DEGILDIR.
  · KONTROL: gecerli kayit rc=0 KALMALI — yoksa batarya "her kaydi reddet" halinden
    ayirt edilemez ve kapi kullanilamaz olurdu.

CANLI DOSYA: yedeklenir, her vakadan sonra ve `finally`de GERI YUKLENIR; kosum sonunda
sha256 ile geri yuklendigi DOGRULANIR (dogrulanamazsa fail-loud).
Kapi `--ornek 1` ile kosulur (hukum ornek sayisindan BAGIMSIZ, sure ~10x kisalir).
"""

import hashlib
import io
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "varlik-test.py")
KAYIT = os.path.join(TOOLS, "varlik-referans.json")

GECERLI = None   # kosum basinda canli dosyadan okunur (tohum SHA'si oradan gelir)

# (ad, kayit_metni, beklenen_rc)
VAKALAR = [
    ("M1 'ref' cok kisa (\"abc\") — 8 Agu FAIL-OPEN", '{"ref": "abc"}\n', 2),
    ("M2 kayit bir JSON DIZISI — 8 Agu FAIL-OPEN", '[{"ref": "aa1146605f"}]\n', 2),
    ("M3 'ref' sayi", '{"ref": 12345}\n', 2),
    ("M4 'ref' alani YOK", '{"tazelendi": "2026-08-02"}\n', 2),
    ("M5 bozuk JSON metni", "{ bozuk ][\n", 2),
    ("M6 'ref' depoda cozulemiyor", '{"ref": "0123456789abcdef0123"}\n', 2),
]


def sha(yol):
    with io.open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kos():
    return subprocess.run([sys.executable, KAPI, "--ornek", "1"],
                          capture_output=True, text=True)


def yaz(metin):
    with io.open(KAYIT, "w", encoding="utf-8") as f:
        f.write(metin)


def main():
    if not os.path.isfile(KAYIT):
        print("OLCULEMEDI: kayit dosyasi yok -> %s" % KAYIT)
        return 3
    baslangic_sha = sha(KAYIT)
    yedek = tempfile.mkstemp(prefix="varlik-referans-yedek-")[1]
    with io.open(KAYIT, encoding="utf-8") as f:
        ilk = f.read()
    with io.open(yedek, "w", encoding="utf-8") as f:
        f.write(ilk)

    dusen, gecti = [], 0
    try:
        # KONTROL once: batarya "hep kirmizi" olamaz.
        k = kos()
        if k.returncode != 0:
            print("TABAN KIRMIZI: gecerli kayitla kapi rc=%d (mutasyon oncesi)"
                  % k.returncode)
            print(k.stdout[-1200:])
            return 1
        print("  ok  KONTROL gecerli kayit -> rc=0")
        gecti += 1

        for ad, metin, beklenen in VAKALAR:
            yaz(metin)
            r = kos()
            cikti = (r.stdout or "") + (r.stderr or "")
            cokme = "Traceback" in (r.stderr or "")
            teshis = "kaydi GECERSIZ" in cikti
            ok = (r.returncode == beklenen) and teshis and not cokme
            if ok:
                gecti += 1
                print("  ok  %s -> rc=%d (GECERSIZ teshisi VAR)" % (ad, r.returncode))
            else:
                dusen.append("%s: rc=%d (beklenen %d) teshis=%s cokme=%s"
                             % (ad, r.returncode, beklenen, teshis, cokme))
                print("  FAIL %s -> rc=%d teshis=%s cokme=%s"
                      % (ad, r.returncode, teshis, cokme))
            yaz(ilk)
    finally:
        yaz(ilk)

    if sha(KAYIT) != baslangic_sha:
        print("🔴 KAYIT GERI YUKLENEMEDI — canli dosya DEGISMIS kaldi: %s" % KAYIT)
        return 1
    print("-" * 70)
    print("  canli kayit geri yuklendi (sha256 bas=son) · yedek: %s" % yedek)
    print("MUTANT=%d/%d  KONTROL=%s" % (len(VAKALAR) - len(dusen), len(VAKALAR),
                                        "YESIL" if gecti else "KIRMIZI"))
    if dusen:
        for d in dusen:
            print("  · %s" % d)
        return 1
    print("SONUC: YESIL ✅ — %d bozuk sekil de TEK BASINA rc=2, kontrol rc=0."
          % len(VAKALAR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
