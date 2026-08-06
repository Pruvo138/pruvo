#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — tools/ata-lisans-test.py GERCEKTEN olcuyor mu?

"Batarya kostum" ANLATISI KANIT DEGILDIR; surucu REPODA durur ve yeniden kosulabilir
([[mutasyon-kaniti-yeniden-uretilebilir]]). Kabul = cikis kodu degil, HER MUTANTIN
BEKLENEN ISARETI: oldurucu KIRMIZI, kontrol YESIL.

🔴 CANLI AGACA ASLA DOKUNMAZ: tools/ gecici bir dizine KOPYALANIR, mutasyon KOPYAYA
uygulanir, test KOPYADAN kosulur ([[mutasyon-diske-yazma-tuzagi]]).

MUTANTLAR:
  OLDURUCU-1 (host korlugu)  : adaptor_bul() host eslemesini yok sayar -> ata DAIMA ilk
      adaptorden cozulur. AYIRT EDICI vaka (ayni kimlik, farkli host) YESILE doner ->
      test KIRMIZI yanmali. Bu, kapinin YENI eksen (host cozumlemesi) olctugunun kanitidir.
  OLDURUCU-2 (yargi tersine) : satilabilir() hukmu tersine cevrilir (NC gecer, CC-BY ihlal
      sayilir) -> test KIRMIZI yanmali.
  KONTROL-1 (ilgisiz davranis): kuru kosum tavani 40 -> 41. Gercek bir davranis degisikligi
      ama OLCULEN EKSENIN DISINDA -> test YESIL kalmali (batarya her mutasyonu kirmizi
      yakan gurultu makinesi degil).
  KONTROL-2 (ilgisiz metin)   : rapor basligi degisir -> test YESIL kalmali.

Kosum:  python3 tools/ata-lisans-mutasyon.py
Cikti:  her mutant icin beklenen/olculen isaret + son satirda sayiyla hukum.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
KAPI_ADI = "ata-lisans-kapisi.py"
TEST_ADI = "ata-lisans-test.py"

# (ad, aranan, yerine, beklenen_isaret, kanit_metni)
#   beklenen_isaret: "KIRMIZI" | "YESIL"
#   kanit_metni    : mutant KIRMIZI ise ciktinin BASARISIZ dokumunde GECMESI gereken ibare —
#                    "kirmizi yandi" YETMEZ, DOGRU IDDIANIN dustugu kanitlanir.
MUTANTLAR = [
    ("OLDURUCU-1 host korlugu",
     '            if host == h or host.endswith("." + h):',
     '            if True:',
     "KIRMIZI", "AYIRT EDICI"),
    ("OLDURUCU-2 yargi tersine",
     '    if not adaptor.satilabilir(lisans_metni):',
     '    if adaptor.satilabilir(lisans_metni):',
     "KIRMIZI", "POZITIF"),
    ("KONTROL-1 ilgisiz davranis (kuru kosum tavani)",
     'ap.add_argument("--limit", type=int, default=40,',
     'ap.add_argument("--limit", type=int, default=41,',
     "YESIL", None),
    ("KONTROL-2 ilgisiz metin (rapor basligi)",
     'yaz("ATA-LISANS KAPISI — RAPOR KIPI (veri YAZILMAZ, silme UYGULANMAZ)")',
     'yaz("ATA-LISANS KAPISI — rapor (kontrol mutanti)")',
     "YESIL", None),
]


def _agac_kur(tmp):
    """Gecici KOPYA agaci: tools/ + kapinin 'yazmaz' iddiasini olcebilmesi icin
    veri kokunde iki taklit dosya (icerikleri onemsiz; olculen sey DEGISMEMELERI)."""
    hedef_tools = os.path.join(tmp, "tools")
    shutil.copytree(_HERE, hedef_tools)
    with open(os.path.join(tmp, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([{"id": "uydurma", "baslik": "uydurma"}], f)
    with open(os.path.join(tmp, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump({"uydurma": {"kaynak": "uydurma", "link": ""}}, f)
    return hedef_tools


def _kos(tools_dizin):
    r = subprocess.run([sys.executable, os.path.join(tools_dizin, TEST_ADI)],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    hatalar = []
    with tempfile.TemporaryDirectory() as tmp:
        tools_dizin = _agac_kur(tmp)
        kapi_yol = os.path.join(tools_dizin, KAPI_ADI)
        with open(kapi_yol, encoding="utf-8") as f:
            temiz_kaynak = f.read()

        # 0) TABAN: mutasyonsuz kopya YESIL olmali (degilse batarya anlamsizdir)
        rc, cikti = _kos(tools_dizin)
        if rc != 0:
            print("TABAN KIRMIZI — mutasyonsuz kopya gecmedi (rc=%d)" % rc)
            print(cikti[-2000:])
            return 2
        print("  ok   TABAN (mutasyonsuz kopya) YESIL")

        for ad, aranan, yerine, beklenen, kanit in MUTANTLAR:
            adet = temiz_kaynak.count(aranan)
            if adet != 1:
                hatalar.append("%s: capa %d kez gecti (1 olmali) — surucu BAYAT" % (ad, adet))
                print("  HATA %-46s capa sayisi=%d" % (ad, adet))
                continue
            with open(kapi_yol, "w", encoding="utf-8") as f:
                f.write(temiz_kaynak.replace(aranan, yerine))
            rc, cikti = _kos(tools_dizin)
            olculen = "YESIL" if rc == 0 else "KIRMIZI"
            # cokme (import/sozdizim hatasi) KIRMIZI ile karistirilmasin
            coktu = ("Traceback" in cikti and "BASARISIZ" not in cikti)
            # KIRMIZI yetmez: DOGRU iddianin dustugu de olculur (BASARISIZ dokumunde)
            dokum = cikti.split("BASARISIZ", 1)[1] if "BASARISIZ" in cikti else ""
            kanit_ok = True if not kanit else (kanit in dokum)
            ok = (olculen == beklenen) and not coktu and kanit_ok
            if not ok:
                hatalar.append("%s: beklenen %s, olculen %s%s%s"
                               % (ad, beklenen, olculen, " (COKTU)" if coktu else "",
                                  "" if kanit_ok else " (dusen iddia %r DEGIL)" % kanit))
            print("  %-4s %-46s beklenen=%-7s olculen=%-7s%s%s"
                  % ("ok" if ok else "HATA", ad, beklenen, olculen,
                     " COKTU" if coktu else "", "" if kanit_ok else " KANIT-YOK"))
            with open(kapi_yol, "w", encoding="utf-8") as f:
                f.write(temiz_kaynak)

    oldurucu = sum(1 for m in MUTANTLAR if m[3] == "KIRMIZI")
    kontrol = len(MUTANTLAR) - oldurucu
    print("")
    if hatalar:
        print("MUTASYON BATARYASI BASARISIZ — %d/%d mutant beklenen isareti VERMEDI:"
              % (len(hatalar), len(MUTANTLAR)))
        for h in hatalar:
            print("  x %s" % h)
        return 1
    print("MUTASYON BATARYASI GECTI — oldurucu %d/%d KIRMIZI, kontrol %d/%d YESIL."
          % (oldurucu, oldurucu, kontrol, kontrol))
    return 0


if __name__ == "__main__":
    sys.exit(main())
