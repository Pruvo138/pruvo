#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN GECIKME NOBETCISI (tools/yayin-gecikme-nobeti.py) MUTASYON HARNESS'I.

NE ISE YARAR: nobetcinin YESIL yanmasi hicbir sey kanitlamaz. Kanit, nobetciyi
BOZUNCA fikstur kabulunun KIRMIZI yanmasidir (mutasyon) VE bozulmamis halinin
YESIL kalmasidir (yanlis-pozitif kontrolu / A0).

🔴 MUTASYON DAIMA GECICI KOPYAYA uygulanir. Canli dosyayi bozup `finally` ile geri
alma deseni bu evde YASAK: tek bir kesinti calisma agacinda MUTANT birakir. Burada
gecici bir dizine (a) nobetcinin KOPYASI, (b) fikstur dizininin KOPYASI yazilir;
tools/ agacina HICBIR YAZMA yapilmaz.

HER MUTANT GERCEK BIR BOZULMADIR (canliya sizabilecek turden):
  M1 esik gevsetme        — alarm esikleri devre disi birakilirsa tikanma sessizlesir
  M2 OLCULEMEDI -> YESIL  — ag/yetki yoklugu "sorun yok" diye okunursa nobetci olur
  M3 iptal = hata         — eszamanlilik iptali TIKANMA sayilirsa normal gun kirmizi
                            yanar (yanlis alarm -> nobetci kapatilir)
  M4 birikme sifirlama    — ahead_by okunmazsa bekleyen icerik GORUNMEZ olur
  M5 zincir durmuyor      — zincir basarida DURMAZSA pencere boyu hatalar toplanir
  M6 kosan kosum = iptal  — henuz kosan kosum "iptal" sayilirsa aclik uydurulur
  M7 sekil dogrulamasi yok— API alani kaybolsa bile nobetci tahmin yurutur
  M8 ACLIK'ta VE -> VEYA  — tek basina iptal zinciri alarm uretir (kural 4 ihlali)
  M9 yas tabani kaldirma  — `--ff-only` ile alinan ESKI tarihli commit'ler yasi
                            sisirir; taban kalkarsa mesru merge yanlis alarm uretir

KABUL: her mutant icin `--kendini-test` KIRMIZI (rc != 0) olmali VE beklenen KURBAN
fikstur(ler)den en az biri kirmizi satirda ADIYLA gecmeli (isaret sarti — mutant
"kaza eseri" baska bir yerden kirmizi yakip gecmis sayilmasin).

Ag YOK. Cikis: 0 = tum mutantlar yakalandi, 1 = en az biri SESSIZ GECTI.
Kullanim: python3 tools/yayin-gecikme-mutasyon.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
NOBETCI = os.path.join(TOOLS, "yayin-gecikme-nobeti.py")
FIKSTUR = os.path.join(TOOLS, "fikstur", "yayin-gecikme")

# (ad, [(bulunacak, yerine), ...], [kurban fikstur adlari])
MUTANTLAR = [
    ("M1 esik gevsetme",
     # Capalar SATIR BASINA sabitlenir: ayni metin modul dokumaninda da geciyor
     # (esik gerekceleri orada yaziyor) ve capa belirsizlesirdi.
     [("\nTIKALI_YAS_DK = 75\n", "\nTIKALI_YAS_DK = 100000\n"),
      ("\nTIKALI_HATA_ZINCIR = 4\n", "\nTIKALI_HATA_ZINCIR = 999\n")],
     ["bugun-tikali", "karisik-tikanma"]),

    ("M2 OLCULEMEDI -> YESIL",
     [("        return \"OLCULEMEDI\", SINIF_RC[\"OLCULEMEDI\"], [str(e)], None",
       "        return \"AKIYOR\", 0, [str(e)], None")],
     ["agsiz", "yetkisiz"]),

    ("M3 iptal = hata",
     [("HATA_SONUCLARI = (\"failure\", \"startup_failure\", \"timed_out\", "
       "\"action_required\")",
       "HATA_SONUCLARI = (\"failure\", \"startup_failure\", \"timed_out\", "
       "\"action_required\", \"cancelled\")")],
     ["iptal-firtinasi-taze", "aclik", "guncel-hic-bekleyen-yok"]),

    ("M4 birikme sifirlama",
     [("    geride = g[\"ahead_by\"]", "    geride = 0")],
     ["bugun-tikali", "gecikme-birikme", "aclik"]),

    ("M5 zincir basarida DURMUYOR",
     [("            else:\n                break\n        return n",
       "            else:\n                continue\n        return n")],
     ["dagilmis-hatalar-saglikli", "normal", "iptal-firtinasi-taze"]),

    ("M6 kosan kosum = iptal",
     [("    tamam = [k for k in kosumlar if k.get(\"status\") == TAMAMLANDI]",
       "    tamam = list(kosumlar)")],
     ["iptal-firtinasi-taze", "normal", "aclik"]),

    ("M7 sekil dogrulamasi yok",
     [("KOSUM_ZORUNLU = (\"id\", \"status\", \"conclusion\", \"created_at\", "
       "\"run_started_at\",\n                 \"updated_at\", \"head_sha\", \"event\")",
       "KOSUM_ZORUNLU = ()")],
     ["bozuk-sekil"]),

    ("M8 ACLIK'ta VE -> VEYA",
     [("    if ai >= ACLIK_IPTAL_ZINCIR and yas >= GECIKME_YAS_DK:",
       "    if ai >= ACLIK_IPTAL_ZINCIR or yas >= GECIKME_YAS_DK:")],
     ["iptal-firtinasi-taze", "gecikme-yas"]),

    ("M9 yas tabani kaldirma",
     [("        baslangic = max(en_eski, olcum[\"son_basarili_baslangic\"])",
       "        baslangic = en_eski")],
     ["ff-only-eski-tarihli"]),
]


def ayna_kur(hedef, ustyazim_kaynak=None):
    """Gecici aynaya nobetci + fikstur KOPYALARI. Kaynak agaca YAZMA YOKTUR."""
    os.makedirs(hedef, exist_ok=True)
    shutil.copy2(ustyazim_kaynak or NOBETCI,
                 os.path.join(hedef, "yayin-gecikme-nobeti.py"))
    shutil.copytree(FIKSTUR, os.path.join(hedef, "fikstur", "yayin-gecikme"))
    return os.path.join(hedef, "yayin-gecikme-nobeti.py")


def kos(betik):
    p = subprocess.run([sys.executable, betik, "--kendini-test"],
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    with open(NOBETCI, encoding="utf-8") as f:
        kaynak = f.read()

    kusur = []
    yakalanan = 0
    tmp = tempfile.mkdtemp(prefix="yayin-gecikme-mutasyon-")
    try:
        # --- A0: MUTASYONSUZ ayna YESIL olmali (harness "hep kirmizi" degil) -----
        temiz = ayna_kur(os.path.join(tmp, "a0"))
        rc, cikti = kos(temiz)
        if rc != 0:
            kusur.append("A0 TABAN: mutasyonsuz ayna KIRMIZI (rc %d) — mutasyon "
                         "sonuclari anlamsiz olur:\n%s" % (rc, cikti[-800:]))
            print("A0 TABAN  ✘ mutasyonsuz ayna kirmizi")
        else:
            print("A0 TABAN  ✔ mutasyonsuz ayna YESIL (yanlis-pozitif yok)")

        # --- MUTANTLAR ----------------------------------------------------------
        for i, (ad, degisimler, kurbanlar) in enumerate(MUTANTLAR):
            govde = kaynak
            for bul, koy in degisimler:
                if bul not in govde:
                    kusur.append("%s: CAPA BULUNAMADI (%r) — mutasyon uygulanamadi, "
                                 "kaynak degismis olabilir (bayat harness)"
                                 % (ad, bul[:60]))
                    govde = None
                    break
                if govde.count(bul) != 1:
                    kusur.append("%s: capa %d kez geciyor — mutasyon BELIRSIZ"
                                 % (ad, govde.count(bul)))
                    govde = None
                    break
                govde = govde.replace(bul, koy, 1)
            if govde is None:
                print("%-26s ✘ capa sorunu" % ad)
                continue

            dizin = os.path.join(tmp, "m%d" % i)
            os.makedirs(dizin)
            mutant_kaynak = os.path.join(dizin, "_mutant-kaynak.py")
            with open(mutant_kaynak, "w", encoding="utf-8") as f:
                f.write(govde)
            betik = ayna_kur(os.path.join(dizin, "ayna"), mutant_kaynak)

            rc, cikti = kos(betik)
            isaret = [k for k in kurbanlar if k in cikti and "✘ %s" % k in cikti]
            if rc == 0:
                kusur.append("%s: SESSIZ GECTI (rc 0) — bu bozulma CI'dan/panodan "
                             "gecebilir" % ad)
                print("%-26s ✘ SESSIZ GECTI" % ad)
            elif not isaret:
                kusur.append("%s: kirmizi yandi ama beklenen KURBAN fiksturlerin "
                             "(%s) hicbiri kirmizi degil — kaza eseri kirmizi olabilir"
                             % (ad, ", ".join(kurbanlar)))
                print("%-26s ✘ isaret sarti karsilanmadi" % ad)
            else:
                yakalanan += 1
                print("%-26s ✔ yakalandi (kurban: %s)" % (ad, ", ".join(isaret)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    print("MUTASYON: %d/%d yakalandi" % (yakalanan, len(MUTANTLAR)))
    for k in kusur:
        print("  ✘ %s" % k)
    return 1 if kusur else 0


if __name__ == "__main__":
    sys.exit(main())
