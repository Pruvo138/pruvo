#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIKAYICI KALDIRMA — `~/.claude/cron/` DUZLEMI ICIN CAPALI YAMA ARACI.

🔴 NEDEN AYRI BIR ARAC: `~/.claude/cron/` **git altinda DEGILDIR**. Elle
duzenleme (a) geri alinamaz, (b) ayni dosyaya dokunan KOMSU CIPIN degisikligini
sessizce ezebilir, (c) "ne degisti" sorusunu cevapsiz birakir. Bu arac ucunu de
kapatir:
  1. Her dosyanin ONCESI kopyasi `emekli-arsiv/<ad>.ONCESI-<damga>` olarak alinir.
  2. Her yama bir CAPA dizgesine baglidir; capa kaynakta TAM 1 KEZ gecmiyorsa
     yama UYGULANMAZ ve arac rc=2 ile DURUR
     ([[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]).
  3. `--kuru` ile hicbir sey yazmadan hangi yamalarin tutacagi OLCULUR.

🔴 KOMSU CIP UYARISI (11 Eyl 2026): `isci.sh` ayni gun IKI cipin menzilinde —
butce tavani `busy-hermann-057e7e`de, tur tavani burada. Bu arac `BUTCE_USD` /
`--max-budget-usd` satirlarina DOKUNMAZ; capalar o bloga hic degmez.

KULLANIM
  python3 tools/tikayici-kaldirma-uygula.py --kuru      # olc, YAZMA
  python3 tools/tikayici-kaldirma-uygula.py --uygula    # yedekle + yaz
"""
import argparse
import os
import shutil
import sys
import time

CRON = os.path.expanduser("~/.claude/cron")
ARSIV = os.path.join(CRON, "emekli-arsiv")
DAMGA = "20260911-tikayici-isci-hatti"

# ------------------------------------------------------------------------------
# YAMALAR — (dosya, ad, capa, yeni_govde)
# 🔴 Her capa BIREBIR ve TEKIL olmalidir. Capa kaymissa yama UYGULANMAZ.
# ------------------------------------------------------------------------------

# KALEM 3 — TUR TAVANI: isi ORTASINDAN kesen zorlama kalkar, ASILMA kesicisi
# (`--azami-sn`) DOKUNULMAZ kalir.
BEKCI_CAPA = """                    if son_tur >= args.tavan:
                        _bekci_cikti_yaz(
                            out,
                            f"BEKCI=KESTI tur={son_tur} tavan={args.tavan}",
                        )
                        # args.pid isci.sh orkestratorudur; kapanis cagrisi
                        # kosabilsin diye kok shell degil, torunlari kesilir.
                        _pid_kes(args.pid, kok_pid_korunsun=True)
                        return 0
"""

BEKCI_YENI = '''                    # 🔴🔴 11 EYL 2026 — OKAN EMRI "tum tikayicilari kaldir".
                    # BU KOL ARTIK KESMIYOR. AYRIM (spec KALEM 3):
                    #   (1) ASILMIS kosumu kesen `--azami-sn` MUTLAK SURE
                    #       tavani YUKARIDA, DEGISMEDEN DURUYOR. Gercek
                    #       kilitlenmeye karsi tek koruma odur ve tur sayisina
                    #       BAKMAZ.
                    #   (2) BU KOL ise TUR sayar — yani URETKEN calismayi.
                    #       45. turda SIGTERM atmak "asilmis kosumu kurtarmak"
                    #       DEGIL, yarim isi ORTASINDAN KESMEKTIR.
                    # 🔴 OLCUM SUSTURULMADI, YALNIZ YAPTIRIM KALKTI: tavan
                    # asildiginda AYNI alanlarla (tur + tavan) bir RAPOR
                    # satiri yazilir ve bekci izlemeye DEVAM eder. Satir bir
                    # KEZ yazilir; her aralikta tekrarlansaydi gunluk suprulur
                    # ve sayim okunamaz hale gelirdi.
                    # 40-tur DILIM kurali `isci.sh` PROMPT_BASI'nda bir ONERI
                    # cumlesi olarak DURUYOR — zorlayici DEGIL.
                    if son_tur >= args.tavan and not tavan_raporlandi:
                        tavan_raporlandi = True
                        _bekci_cikti_yaz(
                            out,
                            f"BEKCI=TUR_TAVANI_ASILDI tur={son_tur} "
                            f"tavan={args.tavan} hukum=RAPOR kesilmedi=1",
                        )
'''

# `tavan_raporlandi` bayragini dongu ONCESINDE tanimla.
BEKCI_BAYRAK_CAPA = """    son_tur = 0
"""
BEKCI_BAYRAK_YENI = """    son_tur = 0
    # 11 Eyl 2026: tur tavani RAPORU bir KEZ yazilir (bkz. asagidaki kol).
    tavan_raporlandi = False
"""

# Bekci BELGESI (docstring): cikti jetonlari bayatlamasin.
BEKCI_BELGE_CAPA = """    BEKCI=KESTI tur=<n> tavan=<n>     (tavan asildi, PID kesildi)
"""
BEKCI_BELGE_YENI = """    BEKCI=TUR_TAVANI_ASILDI tur=<n> tavan=<n> hukum=RAPOR kesilmedi=1
                                      (11 Eyl 2026: tur tavani ARTIK KESMEZ,
                                       yalniz RAPOR eder — Okan emri)
    BEKCI=KESTI ...                   ARTIK URETILMEZ. Jeton yalniz
                                       `isci.sh`in BAYAT okuyucusunda kaldi;
                                       o kol bilerek INERT'tir (bkz. isci.sh
                                       KAPANIS_HALI blogu).
"""

# KALEM 3 (tuketici ayagi) — `isci.sh` artik URETILMEYEN bir jetonu ariyor.
# [[cagri-yeri-envanterden-duserse-onarildi-sanilir]]: olu kol SESSIZ
# birakilmaz; INERT oldugu KAYDA gecirilir ve yeni jeton LOG'a yazilir.
ISCI_KAPANIS_CAPA = """  if [[ "$SON_BEKCI" == BEKCI=KESTI* ]]; then
    KAPANIS_HALI=TUR_TAVANI
    KAPANIS_SEBEBI="tur tavani ${TUR_TAVANI} asildi"
    BEKCI_TUR=$(echo "$SON_BEKCI" | sed -n 's/.*tur=\\([0-9]*\\).*/\\1/p')
  fi
"""
ISCI_KAPANIS_YENI = """  # 🔴 11 EYL 2026 (Okan: "tum tikayicilari kaldir") — BU KOL INERT'TIR.
  # `BEKCI=KESTI` ARTIK URETILMIYOR: tur tavani kesmiyor, RAPOR ediyor.
  # Kol SILINMEDI cunku jeton gecmis gunluklerde ARANIYOR; kosul bilerek
  # yerinde birakildi ve ASLA tutmuyor. Tutarsa bu bir REGRESYONDUR
  # (biri kesme yolunu geri koymus demektir) — o yuzden LOG'a ayri bir
  # uyari satiri dusuyor.
  if [[ "$SON_BEKCI" == BEKCI=KESTI* ]]; then
    echo "🔴 REGRESYON: BEKCI=KESTI uretildi — tur tavani yeniden KESIYOR" >> "$LOG"
    KAPANIS_HALI=TUR_TAVANI
    KAPANIS_SEBEBI="tur tavani ${TUR_TAVANI} asildi"
    BEKCI_TUR=$(echo "$SON_BEKCI" | sed -n 's/.*tur=\\([0-9]*\\).*/\\1/p')
  fi
  # Tavan asildi ama KESILMEDI: kapanis cagrisi ACILMAZ (is suruyor), sayi
  # yine de gunluge gecer — "45 turu gecen kac kosum var" olculebilir kalir.
  if [[ "$SON_BEKCI" == BEKCI=TUR_TAVANI_ASILDI* ]]; then
    echo "TUR_TAVANI_ASILDI_RAPOR ${SON_BEKCI#BEKCI=TUR_TAVANI_ASILDI } kapanis_cagrisi=YOK" >> "$LOG"
  fi
"""

YAMALAR = [
    ("isci-tur-bekcisi.py", "KALEM3-tur-tavani-kesmez",
     BEKCI_CAPA, BEKCI_YENI),
    ("isci-tur-bekcisi.py", "KALEM3-tavan-raporlandi-bayragi",
     BEKCI_BAYRAK_CAPA, BEKCI_BAYRAK_YENI),
    ("isci-tur-bekcisi.py", "KALEM3-belge-jetonlari",
     BEKCI_BELGE_CAPA, BEKCI_BELGE_YENI),
    ("isci.sh", "KALEM3-olu-tuketici-inert-kaydi",
     ISCI_KAPANIS_CAPA, ISCI_KAPANIS_YENI),
]


def _oku(yol):
    with open(yol, "r", encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true",
                    help="olc, HICBIR SEY YAZMA")
    ap.add_argument("--uygula", action="store_true",
                    help="yedekle + yaz")
    ap.add_argument("--dogrula", action="store_true",
                    help="yamali cron dosyalarini DERLE (py_compile) + "
                         "capalarin yerinde oldugunu OLC")
    a = ap.parse_args(argv)
    if not (a.kuru or a.uygula or a.dogrula):
        ap.error("--kuru, --uygula ya da --dogrula verin")

    if a.dogrula:
        # 🔴 Yollar BU ARACIN ICINDE turetilir: mimar oturumunda repo-DISI yol
        # ARGUMANI kapiya takilir. Dogrulama araci da bu yuzden repoda yasar.
        import py_compile
        import subprocess
        kusur = 0
        for dosya in sorted({d for d, _a, _c, _y in YAMALAR}):
            yol = os.path.join(CRON, dosya)
            # 🔴 SOZDIZIM DENETCISI UZANTIYA GORE SECILIR. Ilk surumde `.sh`
            # dosyasi da `py_compile`a veriliyordu ve SAHTE KIRMIZI uretti —
            # denetci yanlissa "kirmizi" kod hakkinda HICBIR SEY soylemez.
            try:
                if dosya.endswith(".py"):
                    py_compile.compile(yol, doraise=True)
                    durum = "DERLENDI (py_compile)"
                else:
                    # zsh: `isci.sh` shebang'i `#!/bin/zsh` (bash DEGIL —
                    # [[batarya-cevresi-degisince-sessizce-olur]]).
                    p = subprocess.run(["zsh", "-n", yol],
                                       capture_output=True, text=True)
                    if p.returncode != 0:
                        raise SyntaxError((p.stderr or "").strip()[:200])
                    durum = "SOZDIZIM OK (zsh -n)"
            except Exception as e:
                durum = "🔴 DERLENMEDI %s: %s" % (type(e).__name__, e)
                kusur += 1
            kaynak = _oku(yol) if os.path.isfile(yol) else ""
            yerinde = sum(1 for _d, _ad, _c, yeni in YAMALAR
                          if _d == dosya and yeni.strip()
                          and yeni in kaynak)
            toplam = sum(1 for _d, _ad, _c, _y in YAMALAR if _d == dosya)
            print("%-28s %s · yama YERINDE=%d/%d"
                  % (dosya, durum, yerinde, toplam))
            if yerinde != toplam:
                kusur += 1
        print("")
        print("KUSUR=%d" % kusur)
        return 1 if kusur else 0

    # dosya -> uygulanacak (ad, capa, yeni) listesi
    gruplar = {}
    for dosya, ad, capa, yeni in YAMALAR:
        gruplar.setdefault(dosya, []).append((ad, capa, yeni))

    print("TIKAYICI KALDIRMA — CAPALI YAMA (%s)"
          % ("KURU KOSUM" if a.kuru else "UYGULA"))
    print("cron koku : %s" % CRON)
    print("")

    kusur = 0
    for dosya, isler in sorted(gruplar.items()):
        yol = os.path.join(CRON, dosya)
        if not os.path.isfile(yol):
            print("🔴 DOSYA YOK: %s" % yol)
            kusur += 1
            continue
        kaynak = _oku(yol)
        yeni_kaynak = kaynak
        satirlar = []
        dosya_kusuru = 0
        for ad, capa, yeni in isler:
            kac = yeni_kaynak.count(capa)
            # 🔴 IDEMPOTANS ONCE OLCULUR: bazi yamalarin capasi yeni govdenin
            # ICINDE de gecer (or. bir satirin ALTINA ekleme yapan yama). Once
            # `capa==1` diye bakilirsa yama HER KOSUMDA yeniden uygulanir ve
            # ikiz tanim uretir. Bu yuzden "zaten uygulanmis mi" ILK sorudur.
            if yeni.strip() and yeni_kaynak.count(yeni) >= 1:
                satirlar.append("   = %-38s ZATEN UYGULANMIS (yeni govde "
                                "YERINDE, capa=%d)" % (ad, kac))
            elif kac == 1:
                yeni_kaynak = yeni_kaynak.replace(capa, yeni)
                satirlar.append("   ✓ %-38s capa=1 (uygulanabilir)" % ad)
            else:
                satirlar.append("   🔴 %-38s CAPA-YOK capa=%d — YAMA "
                                "UYGULANMADI" % (ad, kac))
                dosya_kusuru += 1
        print("%s (%d bayt)" % (dosya, len(kaynak)))
        for s in satirlar:
            print(s)
        kusur += dosya_kusuru
        if dosya_kusuru:
            print("   -> bu dosyaya HICBIR yama yazilmadi (hepsi ya da hicbiri)")
            continue
        if yeni_kaynak == kaynak:
            print("   -> degisiklik YOK")
            continue
        if a.kuru:
            print("   -> KURU: %d bayt -> %d bayt (yazilmadi)"
                  % (len(kaynak), len(yeni_kaynak)))
            continue
        os.makedirs(ARSIV, exist_ok=True)
        yedek = os.path.join(ARSIV, "%s.ONCESI-%s" % (dosya, DAMGA))
        if not os.path.exists(yedek):
            shutil.copy2(yol, yedek)
            print("   -> YEDEK: %s" % yedek)
        else:
            print("   -> YEDEK zaten var (KORUNDU): %s" % yedek)
        kip = os.stat(yol).st_mode
        with open(yol, "w", encoding="utf-8") as f:
            f.write(yeni_kaynak)
        os.chmod(yol, kip)
        print("   -> YAZILDI: %d bayt -> %d bayt"
              % (len(kaynak), len(yeni_kaynak)))
    print("")
    print("KUSUR=%d" % kusur)
    return 1 if kusur else 0


if __name__ == "__main__":
    sys.exit(main())
