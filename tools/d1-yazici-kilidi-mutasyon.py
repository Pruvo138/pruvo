#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — D1 YAZICI KILIDI (K49) gercek ihlali yakiyor mu?

  Kapi: tools/d1-yazici-kilidi-test.py
  Calistir: python3 tools/d1-yazici-kilidi-mutasyon.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu repoda durur ve CI'da kosar.

NEYI OLCER: kilit kolunu bozan her mutant, K49'un kok nedenini (iki eszamanli tam-katalog
yazicisi) GERI GETIRIR:
  * OLDURUCU M1  — kilit HIC ALINMAZ (kapinin kablosu)
  * OLDURUCU M2  — ret rc'si YUTULUR (fail-closed -> fail-open; "durdum" der, kosar)
  * OLDURUCU M3  — CANLI PID OLU SAYILIR (devralma kolunun fail-open kenari)
  * OLDURUCU M4  — BLOKLAYAN flock (fail-slow = fail-open: yazici asilir, sirayla kosar)
  * OLDURUCU M5  — ikinci kat (kayit CANLI mi) sokulur
  * OLDURUCU M6  — kilit birakilirken SAHIP KAYDI temizlenmez (bayat kayit birikir)
KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali; kalmazsa batarya bir tautoloji
ya da "her degisiklige kirmizi yanan" gurultu kaynagidir, nobetci degil.

CAPA DISIPLINI: her capa kaynak dosyada TAM BIR KEZ gecmeli. Gecmezse sonuc "YESIL"
degil "CAPA-YOK"tur (uygulanamayan mutant yesil sayilirsa batarya kor olur).

NASIL: mutant DAIMA KOPYAYA uygulanir. ROOT'un tamami gecici bir dizine SYMLINK'lenir,
mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi O AYNADAN kosulur —
calisma agacina artik dosya BIRAKILMAZ ([[mutasyon-diske-yazma-tuzagi]]).
CANLI D1'e / aga DOKUNULMAZ (kapi tamamen offline).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "d1-yazici-kilidi-test.py"

# Bunun altina dusen kosum "kirmizi" degil COKME'dir. Saglam kosum 27 GECTI basar; en cok
# iddia dusuren OLDURUCU (M1) bile 15'in ustunde kalir. Esik, kapinin erken cokup
# "kirmizi" gorunmesini AYIRT ETMEK icindir.
TABAN_GECTI = 12

# (ad, dosya [TOOLS'a gore], eski, yeni, beklenen)
MUTANTLAR = [
    # ── OLDURUCU ────────────────────────────────────────────────────────────────
    ("OLDURUCU M1 KILIT HIC ALINMAZ (K49 ONCESI hal: iki yazici serbest)",
     "d1-sync.py",
     "    if a.sema or a.seq_normalize or not (a.durum or a.kuru):\n"
     "        yazici_kilidi_al(",
     "    if False:\n"
     "        yazici_kilidi_al(", "KIRMIZI"),
    ("OLDURUCU M2 RC YUTULUR — ret mesaji basilir ama cikis SIFIR (fail-open)",
     "d1-sync.py",
     "    sys.stderr.write(mesaj.rstrip() + \"\\n\")\n"
     "    sys.stderr.flush()\n"
     "    sys.exit(KILIT_MESGUL_RC)",
     "    sys.stderr.write(mesaj.rstrip() + \"\\n\")\n"
     "    sys.stderr.flush()\n"
     "    sys.exit(0)", "KIRMIZI"),
    ("OLDURUCU M3 CANLI PID OLU SAYILIR (devralma 'muhtemelen olmustur'e duser)",
     "d1-sync.py",
     "    except OSError:\n"
     "        return True          # OLCULEMEDI -> olu SAYILMAZ\n"
     "    return True",
     "    except OSError:\n"
     "        return True          # OLCULEMEDI -> olu SAYILMAZ\n"
     "    return False", "KIRMIZI"),
    ("OLDURUCU M4 BLOKLAYAN flock — fail-slow (yazici asilir, sonra SIRAYLA kosar)",
     "d1-sync.py",
     "            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)",
     "            fcntl.flock(fd, fcntl.LOCK_EX)", "KIRMIZI"),
    ("OLDURUCU M5 IKINCI KAT SOKULUR — kayit CANLI PID gosterse de devral",
     "d1-sync.py",
     "    if sahip is not None and sahip != os.getpid() and pid_yasiyor(sahip):",
     "    if False:", "KIRMIZI"),
    ("OLDURUCU M6 BIRAKIRKEN SAHIP KAYDI TEMIZLENMEZ (bayat kayit birikir)",
     "d1-sync.py",
     "    fd, _yol = tutucu\n"
     "    _KILIT_TUTUCU[0] = None\n"
     "    try:\n"
     "        os.ftruncate(fd, 0)\n"
     "    except OSError:\n"
     "        pass",
     "    fd, _yol = tutucu\n"
     "    _KILIT_TUTUCU[0] = None\n"
     "    try:\n"
     "        pass\n"
     "    except OSError:\n"
     "        pass", "KIRMIZI"),

    # ── KONTROL: iddia EDILMEYEN eksen — batarya tautoloji olmasin ──────────────
    ("KONTROL K1 YOKLAMA ARALIGI (0,25 -> 0,20 sn; hukum degismez)",
     "d1-sync.py",
     "KILIT_YOKLAMA_SN = 0.25",
     "KILIT_YOKLAMA_SN = 0.20", "YESIL"),
    ("KONTROL K2 SAHIP KAYDINDAKI makine alani str() ile sarilir (deger ayni)",
     "d1-sync.py",
     "        \"makine\": socket.gethostname(),",
     "        \"makine\": str(socket.gethostname()),", "YESIL"),
    ("KONTROL K3 YORUM METNI (kilit blogu basligi) — davranis degismez",
     "d1-sync.py",
     "# YAZICI KILIDI — IKI ESZAMANLI YAZICI MESRU SATIR SILDIRIR",
     "# YAZICI KILIDI — IKI ESZAMANLI YAZICI MESRU SATIRI SILDIRIR", "YESIL"),
    ("KONTROL K4 argv kaydinin uzunluk siniri (12 -> 16 jeton; kilit hukmu ayni)",
     "d1-sync.py",
     "        \"argv\": sys.argv[1:][:12],",
     "        \"argv\": sys.argv[1:][:16],", "YESIL"),
]


def ayna_kur(tmp):
    """ROOT'un SALT OKUNUR aynasi: tools/ gercek bir dizin (icindekiler symlink), digerleri
    dogrudan symlink. Kapi kendi TOOLS/ROOT'unu bu aynadan cozer."""
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def main():
    tmp = tempfile.mkdtemp(prefix="d1-yazici-kilidi-mutasyon-")
    sonuc = []
    try:
        for ad, dosya, eski, yeni, beklenen in MUTANTLAR:
            kaynak_yolu = os.path.normpath(os.path.join(TOOLS, dosya))
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(os.path.join(tmp, str(len(sonuc))))
            hedef = os.path.normpath(os.path.join(kok, "tools", dosya))
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI_ADI)],
                               capture_output=True, text=True, cwd=kok, timeout=600)
            cikti = r.stdout + r.stderr
            fail = len(re.findall(r"^ *KALDI ", cikti, re.M))
            gecti = len(re.findall(r"^ *GECTI ", cikti, re.M))
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode,
                                               cikti.strip().split("\n")[-1][:90])
            elif r.returncode == 1 and fail == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif gecti < TABAN_GECTI:
                gozlem = "COKME(olculen GECTI sayisi dusuk: %d)" % gecti
            else:
                gozlem = "KIRMIZI" if r.returncode == 1 else "YESIL"
            sonuc.append((ad, beklenen, "%s (KALDI=%d GECTI=%d)" % (gozlem, fail, gecti)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: tools/%s)" % KAPI_ADI)
    kalan = 0
    oldurulen = 0
    olduruculer = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        if beklenen == "KIRMIZI":
            olduruculer += 1
            oldurulen += 1 if tamam else 0
        print("  %s  %-78s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    print("\nOLDURULEN=%d/%d  ·  KONTROL_MUTANT=%s"
          % (oldurulen, olduruculer,
             "YESIL" if all(g.startswith("YESIL")
                            for _a, b, g in sonuc if b == "YESIL") else "KIRMIZI"))
    if kalan:
        print("SONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("SONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
