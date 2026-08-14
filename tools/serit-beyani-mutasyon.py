#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/serit-beyani-mutasyon.py — SERIT TURETIMI (T1) + ISTISNA (T2) MUTASYON BATARYASI.

NE OLCER: tools/is-akisi-kapisi.py :: serit turetimi 4 oldurucu mutanta (U1-U4) karsi
kapali mi + kontrol mutanti yesil mi. KABUL = `--kendini-test` CIKIS KODU: oldurucu
mutant KIRMIZI yanmali, kontrol (yorum) mutanti YESIL kalmali.

VAKALAR (spec SPEC-serit-beyani-sinif.md KABUL TESTI — `--kendini-test` icinde OLMCULUR,
bu dosya yalniz MUTANTLARI kosturur):
  1) deploy.yml'de yeni kapi adimi  -> SERIT A, beyan GEREKMEZ, YESIL
  2) nobet.yml'de yeni kapi adimi   -> SERIT B, beyan GEREKMEZ, YESIL
  3) nobet.yml'de BLOKLAYICI yargilanmasi gereken adim -> istisna VARSA gecer, YOKSA KIRMIZI
  4) gerekcesiz istisna             -> KIRMIZI
  5) iki workflow'da gecen adim     -> her biri kendi job'una gore
  6) bilinmeyen workflow            -> fail-closed KIRMIZI

🔴 YONTEM (in-place + sha256 geri donme): mutant KANONIK KAYNAGA GECICI uygulanir,
`--kendini-test` ALT SUREÇ olarak kosar, kaynak HEMEN `finally` ile birebir geri konur.
Kosum sonunda kaynak bayt-ozdes (sha256) dogrulanir; araya giren hata bile kaynagi
kirli birakamaz ([[mutasyon-diske-yazma-tuzagi]] — geri konan kaynak is urunu DEGILDIR).

    python3 tools/serit-beyani-mutasyon.py   # 0 = 4/4 mutant KIRMIZI + kontrol YESIL
"""
import hashlib
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF_AD = "is-akisi-kapisi.py"
HEDEF = os.path.join(TOOLS, HEDEF_AD)

KIRMIZI_IZ = "SONUC: KIRMIZI"
YESIL_IZ = "SONUC: YESIL"

# (ad, eski, yeni, KIRMIZI_beklenir_mi)
# 🔴 Her capa KANONIK KAYNAKTA TAM BIR KEZ gecmeli; yoksa batarya HICBIR SEY olcmuyordur.
MUTANTLAR = [
    ("U1) T1 turetimi kaldirildi (nobet dosyalari 'bilinmeyen' sayilir)",
     "    if ad is not None and ad in NOBET_DOSYALARI:",
     "    if ad is not None and False:",
     True),
    ("U2) istisna gerekcesiz kabul edildi (bos gerekce gecti)",
     "        if not (isinstance(gerekce, str) and gerekce.strip()):\n"
     "            hatalar.append(\"SERIT_B GEREKCESIZ giris (bos gerekce): %s\" % etiket)",
     "        if False:\n"
     "            hatalar.append(\"SERIT_B GEREKCESIZ giris (bos gerekce): %s\" % etiket)",
     True),
    ("U3) bilinmeyen workflow A varsayildi (fail-open)",
     "        if cagrilar and serit_b_joblar is None:",
     "        if False:",
     True),
    ("U4) bloklamayan job'daki BLOKLAYICI kapi kosulsuz mesru sayildi",
     "        if istisnasiz:",
     "        if False:",
     True),
    ("K)  KONTROL MUTANTI (yorum degisti) — YESIL kalmali",
     '            # "yayini BLOKLAMAYAN job" sebebi artik BEYAN GEREKTIRMEZ (T1) — yalnizca',
     '            # "yayini BLOKLAMAYAN job" sebebi artik BEYAN GEREKTIRMEZ (T1, kontrol) — yalnizca',
     False),
]


def alt_kosum():
    """Kanonik yoldan `--kendini-test`i ALT SUREÇ olarak kosar (taze surec, modul cache YOK)."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, HEDEF, "--kendini-test"],
                          capture_output=True, text=True, env=env, timeout=300)


def main():
    with open(HEDEF, "rb") as f:
        orijinal = f.read()
    ozet = hashlib.sha256(orijinal).hexdigest()
    print("KANONIK_KAYNAK=%s sha256=%s" % (HEDEF_AD, ozet))

    def geri_koy():
        with open(HEDEF, "wb") as f:
            f.write(orijinal)

    # KONTROL KOSUMU (mutasyonsuz) -> YESIL olmali; yoksa batarya "olcuyor" diye yalan soyler.
    try:
        r0 = alt_kosum()
    except Exception as e:  # noqa: BLE001
        print("KONTROL KOSUMU KOSULAMADI (%s: %s)" % (type(e).__name__, e))
        return 2
    if r0.returncode != 0 or YESIL_IZ not in r0.stdout:
        print("KONTROL KOSUMU YESIL DEGIL (rc=%d) — once --kendini-test'i temizle"
              % r0.returncode)
        print(r0.stdout[-2000:])
        return 2

    fails = []
    kirmizi_yanan = 0
    beklenen = sum(1 for m in MUTANTLAR if m[3])
    kontrol = None
    for ad, eski, yeni, kirmizi_bekle in MUTANTLAR:
        src = orijinal.decode("utf-8")
        adet = src.count(eski)
        if adet != 1:
            print("  FAIL  %s -> CAPA %d kez (1 olmali); UYGULANMADI" % (ad, adet))
            fails.append(ad)
            continue
        mut = src.replace(eski, yeni, 1)
        if mut == src:
            print("  FAIL  %s -> mutasyon metni DEGISTIRMEDI" % ad)
            fails.append(ad)
            continue
        r = None
        try:
            with open(HEDEF, "w", encoding="utf-8") as f:
                f.write(mut)
            r = alt_kosum()
        except Exception as e:  # noqa: BLE001
            print("  FAIL  %s -> ALTKOSUM COKTU: %s: %s" % (ad, type(e).__name__, e))
            fails.append(ad)
        finally:
            geri_koy()
        if r is None:
            continue
        yesil, kirmizi = YESIL_IZ in r.stdout, KIRMIZI_IZ in r.stdout
        if kirmizi_bekle:
            ok = kirmizi and r.returncode != 0
            if ok:
                kirmizi_yanan += 1
            etiket = ("KIRMIZI ✅" if ok else
                      ("COKTU (kirmiziyla karismaz)" if not yesil and not kirmizi
                       else "YESIL ❌ MUTANT SAG KALDI"))
            print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, etiket))
            if not ok:
                fails.append(ad)
                print("        rc=%d stderr: %s" % (r.returncode, (r.stderr or "")[-300:]))
        else:
            kontrol = "YESIL" if (yesil and r.returncode == 0) else "KIRMIZI"
            ok = kontrol == "YESIL"
            print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol))
            if not ok:
                fails.append(ad + " (kontrol mutanti kirmizi: batarya olcmuyor)")
                print(r.stdout[-1500:])

    # Kaynak birebir geri dondu mu (sha256).
    with open(HEDEF, "rb") as f:
        sonra = f.read()
    sha_ok = sonra == orijinal

    print("\nMUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s  KAYNAK_SHA=%s"
          % (kirmizi_yanan, beklenen, kontrol or "KOSULMADI",
             "BIREBIR" if sha_ok else "BOZUK"))
    if fails:
        print("SONUC: MUTASYON KIRMIZI ❌ (%d)" % len(fails))
        return 1
    print("SONUC: MUTASYON YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
