#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K309 dilim-2A — kalemlerin `kabul:` KOMUTLARINI FIILEN kosturur.

Hukum YALNIZ kosan komutun rc'sinden okunur. "Kodda onarilmis gorunuyor" ya da
yorum satiri kapatma gerekcesi DEGILDIR ([[aracin-teshis-cumlesi-olcum-degil]]).

Her komut icin: rc + stdout/stderr TAM dokum (ayri dosya) + SON satir.
Calistirilamayan komut (dosya yok, bagimlilik yok) => OLCULEMEDI, sessiz yesil YOK.
"""
import io
import json
import os
import subprocess
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/okan/dev/pruvo"          # 🔴 KANONIK ana checkout (worktree DEGIL)
CIKTI = os.path.join(BURASI, "k309d2-kosum")

# (etiket, kalem_id, komut listesi, aciklama)
KOSUMLAR = [
    ("K140a", "K140", ["python3", "tools/marka-invaryant-kapisi.py"],
     "kalemin kendi olcutu: 7 model jetonu DUSMUS VE `Rover` DURUYOR VE mutasyon 4/4. "
     "🔴 Kalemin metni AYNEN: 'Hedef rc=0 DEGIL dogru kirmizi'."),
    ("K140b", "K140", ["python3", "tools/marka-invaryant-mutasyon.py"],
     "K140 olcutunun 3. kolu: mutasyon 4/4."),
    ("K152", "K152", ["python3", "tools/koken-bul.py", "--eksik"],
     "olcut: `EKSIK` DUSER (taban EKSIK=259) VE `--kendini-test` rc=0."),
    ("K161", "K161", ["python3", "tools/denetim-kapisi.py", "--tum-katalog", "--envanter"],
     "olcut: vurus <=21."),
    ("K188", "K188", ["python3", "/Users/okan/dev/pruvo/tools/yedekle-test.py"],
     "olcut: `YEDEK=TAM/YARIM` jetonu FIKSTURLE olculmus olmali."),
    ("REG", "-", ["python3", "tools/kalem-senkron-kapisi.py", "--kendini-test"],
     "dilim-1 bataryasi regresyonu (bozulmadi mi)."),
]

TAVAN_SN = 900


def main():
    if not os.path.isdir(CIKTI):
        os.makedirs(CIKTI)
    sonuc = []
    for etiket, kid, komut, aciklama in KOSUMLAR:
        dosya = os.path.join(CIKTI, "%s.txt" % etiket)
        kayit = {"etiket": etiket, "kalem": kid, "komut": " ".join(komut),
                 "olcut": aciklama, "cikti_dosyasi": dosya}
        try:
            p = subprocess.run(komut, cwd=REPO, capture_output=True,
                               text=True, timeout=TAVAN_SN)
            ham = (p.stdout or "") + (("\n--- STDERR ---\n" + p.stderr) if p.stderr else "")
            kayit["rc"] = p.returncode
            kayit["OLCULEMEDI"] = False
        except FileNotFoundError as e:
            ham = "OLCULEMEDI — komut/yorumlayici BULUNAMADI: %s" % e
            kayit["rc"] = None
            kayit["OLCULEMEDI"] = True
            kayit["sebep"] = "FileNotFoundError: %s" % e
        except subprocess.TimeoutExpired:
            ham = "OLCULEMEDI — %d sn tavani asildi." % TAVAN_SN
            kayit["rc"] = None
            kayit["OLCULEMEDI"] = True
            kayit["sebep"] = "TIMEOUT %ds" % TAVAN_SN
        with io.open(dosya, "w", encoding="utf-8") as f:
            f.write(ham)
        satirlar = [s for s in ham.splitlines() if s.strip()]
        kayit["son_satir"] = satirlar[-1] if satirlar else "(cikti BOS)"
        kayit["satir_sayisi"] = len(satirlar)
        sonuc.append(kayit)

    ham_json = os.path.join(BURASI, "k309d2-kosum-ham.json")
    with io.open(ham_json, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    rapor = os.path.join(BURASI, "k309d2-kosum-rapor.txt")
    with io.open(rapor, "w", encoding="utf-8") as rf:
        def yaz(s=""):
            sys.stdout.write(s + "\n")
            rf.write(s + "\n")
        yaz("=== K309 DILIM-2A KABUL KOSUMLARI ===")
        for k in sonuc:
            yaz("")
            yaz("ETIKET=%s KALEM=%s" % (k["etiket"], k["kalem"]))
            yaz("  KOMUT=%s" % k["komut"])
            yaz("  RC=%s  OLCULEMEDI=%s  SATIR=%d"
                % (k["rc"], k["OLCULEMEDI"], k["satir_sayisi"]))
            yaz("  SON_SATIR=%s" % k["son_satir"])
            yaz("  DOSYA=%s" % k["cikti_dosyasi"])
        yaz("")
        yaz("BITIS rc=0 (kosum tamam; HUKUM her kalemin KENDI olcutunden okunur)")
    print("RAPOR=%s" % rapor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
