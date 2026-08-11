#!/usr/bin/env python3
"""MUTASYON BATARYASI — `deploy-aclik-kapisi.py` GECICI AG SINIFI ekseni.

NEDEN VAR (11 Agu 2026): "Paket tazeligi alarmi" is akisinin `yayin-nabzi` isinde
`python3 tools/deploy-aclik-kapisi.py --canli` adimi rc=2 (OLCULEMEDI) ile dustu.
Ham log satiri (kosum 31513300170):

    ⚪ OLCULEMEDI — `gh api repos/Pruvo138/pruvo/actions/runs/31507501450/jobs
    ?per_page=100` rc=1: Get "https://api.github.com/...": tls: failed to verify
    certificate: x509: certificate is not valid for any names, but wanted to match
    api.github.com

E4 ekseni tek turda 21'e kadar `gh api` cagirir; bunlardan BIRI gecici bir TLS/ag
arizasina denk gelince TUM tur kirmizi yaniyordu. Onarim: GECICI sinifta sinirli
yeniden deneme. Onarim GEVSETME DEGILDIR — bu batarya bunu KOSARAK kanitlar:
her mutant kapinin kendini-testini KIRMIZI yakmali, KONTROL mutanti YESIL kalmali
([[mutasyon-kaniti-yeniden-uretilebilir]] — anlatilan degil KOSULAN kanit).

KULLANIM
    python3 tools/deploy-aclik-gh-mutasyon.py        # rc 0 = batarya temiz
"""
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
ARAC = os.path.join(TOOLS, "deploy-aclik-kapisi.py")

# (ad, capa, mutant). Capa dosyada BULUNAMAZSA mutant "hicbir sey olcmedi" sayilir ve
# batarya KIRMIZI doner — sessiz capa kaymasi yesil gecmez.
MUTANTLAR = (
    ("MUT-A geri-alma (gecici sinif hep False)",
     "    return any(iz in d for iz in GECICI_AG_IZLERI)",
     "    return False"),
    ("MUT-B gevsetme (her hata gecici sayilir)",
     "    return any(iz in d for iz in GECICI_AG_IZLERI)",
     "    return True"),
    ("MUT-C fail-open (tukenince bos govde doner)",
     '    raise OlcumHatasi("%s [%d/%d deneme]" % (son, deneme, GH_DENEME_TAVANI))',
     "    return {}"),
    ("MUT-D beklemesiz (3 deneme ayni anda tukenir)",
     "            uyu(GH_BEKLEME_SN[min(deneme - 1, len(GH_BEKLEME_SN) - 1)])",
     "            uyu(0)"),
    ("MUT-E sekil hatasi da gecici sayilir",
     '                    raise OlcumHatasi("`gh api %s` ciktisi JSON degil: %s"'
     " % (yol, e))",
     '                    son = "`gh api %s` ciktisi JSON degil: %s" % (yol, e)\n'
     "                    gecici = True"),
)

# KONTROL MUTANTI: eksenle ALAKASIZ bir sabit. Kapi buna KIRMIZI yanarsa "her
# degisiklige bagiran" bir gurultu kaynagidir, kanit degeri kalmaz.
KONTROL = ("KONTROL M0 (alakasiz sabit: CANLI_PENCERE)",
           "CANLI_PENCERE = 30", "CANLI_PENCERE = 29")


def _kendini_test():
    p = subprocess.run([sys.executable, ARAC, "--kendini-test"],
                       capture_output=True, text=True, cwd=ROOT)
    ilk = ""
    for satir in p.stdout.splitlines():
        if satir.strip().startswith("GH-RETRY"):
            ilk = satir.strip()
            break
    return p.returncode, ilk


def main():
    with open(ARAC, encoding="utf-8") as f:
        ozgun = f.read()
    dusen = 0
    print("MUTASYON BATARYASI — deploy-aclik-kapisi.py :: GECICI AG SINIFI")
    for ad, capa, mutant in MUTANTLAR:
        if capa not in ozgun:
            print("  🔴 %-46s CAPA KAYMIS — mutant HICBIR SEY olcmedi" % ad)
            dusen += 1
            continue
        with open(ARAC, "w", encoding="utf-8") as f:
            f.write(ozgun.replace(capa, mutant, 1))
        try:
            rc, ilk = _kendini_test()
        finally:
            with open(ARAC, "w", encoding="utf-8") as f:
                f.write(ozgun)
        if rc == 0:
            print("  🔴 %-46s YESIL KALDI — eksen bu mutanti GORMUYOR" % ad)
            dusen += 1
        else:
            print("  ✅ %-46s rc=%d · %s" % (ad, rc, ilk[:100]))

    ad, capa, mutant = KONTROL
    if capa not in ozgun:
        print("  🔴 %-46s CAPA KAYMIS" % ad)
        dusen += 1
    else:
        with open(ARAC, "w", encoding="utf-8") as f:
            f.write(ozgun.replace(capa, mutant, 1))
        try:
            rc, _ = _kendini_test()
        finally:
            with open(ARAC, "w", encoding="utf-8") as f:
                f.write(ozgun)
        if rc == 0:
            print("  ✅ %-46s YESIL KALDI — kapi gurultu kaynagi degil" % ad)
        else:
            print("  🔴 %-46s KIRMIZI YANDI — kapi alakasiz degisiklige bagiriyor" % ad)
            dusen += 1

    print("SONUC: %d mutant + 1 kontrol · dusen=%d" % (len(MUTANTLAR), dusen))
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
