#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — `gramer-artigi-kapisi.py` KISALTMA muafiyetinin kanit hatti.

NEDEN VAR: `cift-noktalama` kolunun `\\.\\s*,` dali 2 gunde IKI kez (5 Agu sira
sayisi, 7 Agu kisaltma) tum ekibin yayinini durdurdu. Kol gevsetildi; gevsetmenin
YANLIS yapilmis hali GERCEK gramer enkazini SESSIZCE gecirir — yani bu kapinin
"yesil"i tek basina kanit degildir. Anlatilan batarya kanit degildir: surucu
REPODA durur ve yeniden kosulabilir.

KABUL: cikis kodu degil, OLDURULEN MUTANT SAYISI + isaret sarti. Her mutant icin
  * metin ikamesi GERCEKTEN uygulandi mi (bulunamayan/mukerrer ikame = HATA,
    oldurulmus SAYILMAZ — "mutasyon uygulanmadi" tuzagi),
  * oldurme isareti dogru mu (oz-test mutantinda rc=1 YETMEZ, en az bir 🔴 iddia
    satiri sart; cokme kirmiziyla karisir).

Kullanim:
    python3 tools/gramer-kisaltma-mutasyon.py          # batarya
    python3 tools/gramer-kisaltma-mutasyon.py --ayrinti
Cikis kodu: 0 = TUM mutantlar olduruldu · 1 = hayatta kalan/hatali mutant var.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "gramer-artigi-kapisi.py")
KATALOG = os.path.join(ROOT, "urunler.json")

# 🔴 OLDURME EKSENI CANLI VERIYE BAGLANMAZ (7 Agu 2026, olculdu): M1 once "CANLI
#    katalogda rc 1" ekseniyle yazilmisti. Paralel bir oturum ayni saatte urun
#    METNINI degistirip tuzagi ('vb.,') katalogdan CIKARINCA M1 SESSIZCE HAYATTA
#    KALDI (8/8 -> 7/8): mutant hala bozuktu ama onu OLDUREN girdi veriden
#    silinmisti. Kabul kaniti baskasinin veri duzlemine bagimli olamaz -> oldurme
#    girdisi artik BETIGIN KENDI FIKSTURUDUR.
#
# (etiket, eski_metin, yeni_metin, oldurme_ekseni)
#   oldurme_ekseni: "kapi_fikstur" -> betigin URETTIGI fikstur katalogda rc 1
#                   "oztest"       -> oz-test rc 1 + en az bir 🔴 iddia
#                   "failclosed"   -> import aninda fail-closed mesaji basmali
MUTANTLAR = (
    ("M1 kanonik kume BOSALTILDI",
     "vb vd vs bkz br or ör orn örn orj md age yak yakl dk sn no nr mm cm",
     "",
     "kapi_fikstur"),
    ("M2 muafiyet HER `X.,` icin acik (kol tamamen olu)",
     "    return jeton.isdigit() or jeton.lower() in KISALTMALAR",
     "    return True",
     "oztest"),
    ("M3 GENEL gevsetme: harf onceli her sey muaf",
     "    return jeton.isdigit() or jeton.lower() in KISALTMALAR",
     "    return jeton.isdigit() or jeton.isalpha()",
     "oztest"),
    ("M4 RAKAM (sira sayisi) muafiyeti dusuruldu",
     "    return jeton.isdigit() or jeton.lower() in KISALTMALAR",
     "    return jeton.lower() in KISALTMALAR",
     "oztest"),
    ("M5 `\\.\\s*,` dali koldan SILINDI",
     r'("cift-noktalama", r",\s*,|;\s*[;.]|\.\s*,|,\s*\.",',
     r'("cift-noktalama", r",\s*,|;\s*[;.]|,\s*\.",',
     "oztest"),
    ("M6 kume ASIRI genis (cekimli kelime iceri alindi)",
     "vb vd vs bkz br or ör orn örn orj md age yak yakl dk sn no nr mm cm",
     "vb vd vs bkz br or ör orn örn orj md age yak yakl dk sn no nr mm cm düzdür zxq",
     "oztest"),
    ("M7 muafiyet kablosu kopuk (desen adi yanlis)",
     '    "cift-noktalama": _nokta_virgul_muaf,',
     '    "cift-noktalamaa": _nokta_virgul_muaf,',
     "failclosed"),
    ("M8 satirda YALNIZ ilk isabete bakilir (maskeleme)",
     "        for m in rx.finditer(satir):",
     "        for m in list(rx.finditer(satir))[:1]:",
     "oztest"),
)

FAILCLOSED_IMZA = "_MUAFIYET'te tanimsiz desen adi"


def _kos(yol, args):
    p = subprocess.run([sys.executable, yol] + args, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


_IDDIA_RE = re.compile(r"oz-test YESIL: (\d+) iddia|OZ-TEST KIRMIZI: \d+/(\d+) iddia")


def _iddia_sayisi(cikti):
    """KANONIK iddia adedi — betigin KENDI bastigi sayi. Satir saymak (proxy)
    ic ice kosumlarin '✅ TEMIZ' satirlarini da yutar, birim kayar."""
    m = _IDDIA_RE.search(cikti)
    if not m:
        return -1                       # olculemedi; sessizce 0 sayma
    return int(m.group(1) or m.group(2))


def _kirmizi_iddia(cikti):
    return sum(1 for s in cikti.splitlines() if s.strip().startswith("🔴"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ayrinti", action="store_true")
    args = ap.parse_args()

    with open(KAPI, encoding="utf-8") as f:
        kaynak = f.read()

    olduruldu = 0
    hatali = []
    with tempfile.TemporaryDirectory() as d:
        # --- OLDURME FIKSTURU: kanonik kisaltma + virgul tasiyan, TABAN KUME'yi
        #     asan sentetik katalog. Canli urunler.json'dan BAGIMSIZ (bkz. M1 notu).
        fikstur = os.path.join(d, "fikstur_katalog.json")
        kayitlar = [{"id": "temiz%d" % i,
                     "aciklama": "Kapak gövdeye vidayla sabitlenir."}
                    for i in range(1200)]
        kayitlar[600] = {
            "id": "kisaltma-tuzagi",
            "aciklama": "Bardaklığa 0,33 litrelik ince konserve kutularının "
                        "(Redbull vb., 54mm çap) sığdırılmasını sağlar.",
        }
        with open(fikstur, "w", encoding="utf-8") as f:
            json.dump(kayitlar, f, ensure_ascii=False)

        # --- KONTROL: mutasyonsuz kopya YESIL olmali (batarya kendi kendini yanlis
        #     yere kirmizi yakmiyor mu). Bu bir mutant DEGIL, tabandir. Fikstur de
        #     YESIL olmali: aksi halde M1'in kirmizisi mutasyondan DEGIL bozuk
        #     fiksturden gelirdi (kontrol mutantinin kendi kontrolu).
        taban = os.path.join(d, "taban_kapi.py")
        shutil.copyfile(KAPI, taban)
        t_rc, t_out = _kos(taban, ["--kendini-test"])
        k_rc, k_out = _kos(taban, ["--dosya", KATALOG])
        f_rc, f_out = _kos(taban, ["--dosya", fikstur])
        taban_iddia = _iddia_sayisi(t_out)
        print("TABAN (mutasyonsuz): oz-test rc=%d iddia=%d · canli kapi rc=%d "
              "· fikstur kapi rc=%d" % (t_rc, taban_iddia, k_rc, f_rc))
        if t_rc != 0 or k_rc != 0 or f_rc != 0:
            print("🔴 TABAN KIRMIZI — batarya anlamsiz, once kapiyi duzelt.")
            return 1

        print("-- MUTASYON BATARYASI (%d mutant)" % len(MUTANTLAR))
        for etiket, eski, yeni, eksen in MUTANTLAR:
            n = kaynak.count(eski)
            if n != 1:
                hatali.append("%s: ikame metni %d kez bulundu (1 olmali)" % (etiket, n))
                print("   🟠 HATA %-52s ikame bulunamadi/mukerrer (%d)" % (etiket, n))
                continue
            mut = kaynak.replace(eski, yeni)
            if mut == kaynak:
                hatali.append("%s: mutasyon UYGULANMADI" % etiket)
                print("   🟠 HATA %-52s mutasyon uygulanmadi" % etiket)
                continue
            yol = os.path.join(d, "mutant_%d.py" % (olduruldu + len(hatali) + 1))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(mut)

            if eksen == "kapi_fikstur":
                rc, out = _kos(yol, ["--dosya", fikstur])
                oldu = (rc == 1 and "IHLAL" in out)
                isaret = "fikstur kapi rc=%d" % rc
            elif eksen == "failclosed":
                rc, out = _kos(yol, ["--kendini-test"])
                oldu = (rc != 0 and FAILCLOSED_IMZA in out)
                isaret = "rc=%d fail-closed imzasi=%s" % (rc, FAILCLOSED_IMZA in out)
            else:
                rc, out = _kos(yol, ["--kendini-test"])
                kirmizi = _kirmizi_iddia(out)
                # rc=1 TEK BASINA yetmez: cokme de 1 verir. Kirmizi IDDIA sart.
                oldu = (rc == 1 and kirmizi >= 1)
                isaret = "oz-test rc=%d kirmizi_iddia=%d iddia=%d" % (
                    rc, kirmizi, _iddia_sayisi(out))

            print("   %s %-52s %s" % ("✅ OLDU " if oldu else "🔴 YASADI", etiket, isaret))
            if oldu:
                olduruldu += 1
            else:
                hatali.append("%s: HAYATTA KALDI (%s)" % (etiket, isaret))
            if args.ayrinti:
                print("      " + out.strip().replace("\n", "\n      ")[:1200])

    print()
    print("MUTASYON SONUCU: %d/%d olduruldu · taban oz-test iddia=%d"
          % (olduruldu, len(MUTANTLAR), taban_iddia))
    if hatali:
        for h in hatali:
            print("   - " + h)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
