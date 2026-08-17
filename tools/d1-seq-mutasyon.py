#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — MID-ARRAY BLOK KOLU (K153) GERCEK ihlali yakiyor mu?

  Kapi: tools/d1-seq-test.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu repoda durur; kabul CIKIS KODU degil
OLCULEN IDDIA SAYISI + ISARET SARTIDIR (cokme kirmiziyla karisir).

NEYI OLCER: K153 seq atamasi. Eski kod ikili bolmeyle 26 ardisik mid-array yeni id icin
~20 adimda boslugu tuketirdi; cozum bloga ORANLI adim (`(yuksek-alt)//(k+1)`) + ALT sinirin
blogun ILK uyesinde sabitlenmesi + `adim < 1` fail-loud. Asagidaki OLDURUCU mutantlar bu
uc kolu da TEK TEK GERI GETIRIR:
  * M1 — blok kolu kaldirildi, ikili bolmeye donuldu  (V1 yakar)
  * M2 — `adim < 1` fail-loud'u kaldirildi             (V2 yakar)
  * M3 — `atanan` monotonlugu bozuldu (blok_i ters)     (V1 yakar)
  * M4 — `_seq_fail_loud` NO-OP kolu eski metne dondu   (V5 yakar)
KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali; yoksa kapi "her degisiklige
kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

CAPA DISIPLINI: her mutant capasinin kaynak dosyada TAM BIR KEZ gecmesi SART. Gecmezse
sonuc "YESIL" degil "CAPA-YOK"tur (mutant uygulanamadan yesil sayilmasi bataryayi kor eder).

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi
O AYNADAN kosulur. CANLI D1'e / aga DOKUNULMAZ (kapi tamamen offline).

Calistir:  python3 tools/d1-seq-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "d1-seq-test.py"

# Bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir. Saglam kosum 10 GECTI basar
# (5 on-kontrol + 5 vaka). Esik, M1'in V1'i mid-crash etmesini KIRMIZI olarak
# sayabilmek icindir — V1 crash'i 5 on-kontrol GECTI'sini yazdirip ardindan SystemExit
# eder; yeterli GECTI sayisi "test kosuldu, bir vaka krildi" anlamina gelir.
TABAN_GECTI = 5

# (ad, dosya [TOOLS'a gore], eski, yeni, beklenen)
MUTANTLAR = [
    # ── OLDURUCU: blok kolunu kaldiran ─────────────────────────────────────────
    ("OLDURUCU M1 mid-array blok kolu kaldirildi (ikili bolmeye donuldu)",
     "d1-sync.py",
     "                elif mid is not None:\n"
     "                    # MID-ARRAY BLOGU (K153): ayni bosluga dusen ardisik yeni id'ler\n"
     "                    # bloga ORANLI yer tuketir. ALT sinir blogun ILK islenen uyesinde\n"
     "                    # SABITLENIR ve blok boyunca degismez; aksi halde ikili bolmeye geri\n"
     "                    # donulur ve ~20 ardisik eklemede bosluk tukenir.\n"
     "                    blok_i, blok_k, grup_id = mid\n"
     "                    if blok_i == 1:\n"
     "                        mid_alt = int(taban)\n"
     "                        aktif_mid_grup = (grup_id, mid_alt)\n"
     "                    else:\n"
     "                        if aktif_mid_grup is None or aktif_mid_grup[0] != grup_id:\n"
     "                            sys.exit(\"!! SEQ mid_blok tutarsizligi: %s\" % uid)\n"
     "                        mid_alt = aktif_mid_grup[1]\n"
     "                    adim = (yuksek - mid_alt) // (blok_k + 1)\n"
     "                    if adim < 1:\n"
     "                        _seq_fail_loud(uid, mid_alt, yuksek, blok_k, urunler, mevcut_seq)\n"
     "                    atanan = mid_alt + blok_i * adim\n"
     "                    if blok_i == blok_k:\n"
     "                        aktif_mid_grup = None",
     "                elif mid is not None:\n"
     "                    # M1: blok kolu kaldirildi, ikili bolmeye donuldu\n"
     "                    atanan = alt + (yuksek - alt) // 2",
     "KIRMIZI"),

    # ── OLDURUCU: fail-closed / kesir yazildi ────────────────────────────────────
    ("OLDURUCU M2 adim<1 fail-loud'u kaldirildi (kesir/0 ile yazilir)",
     "d1-sync.py",
     "                    adim = (yuksek - mid_alt) // (blok_k + 1)\n"
     "                    if adim < 1:\n"
     "                        _seq_fail_loud(uid, mid_alt, yuksek, blok_k, urunler, mevcut_seq)\n"
     "                    atanan = mid_alt + blok_i * adim",
     "                    adim = max(1, (yuksek - mid_alt) // (blok_k + 1))\n"
     "                    atanan = mid_alt + blok_i * adim",
     "KIRMIZI"),

    # ── OLDURUCU: monotonlugu boz ────────────────────────────────────────────────
    ("OLDURUCU M3 atanan monotonlugu bozuldu (blok_i ters cevrildi)",
     "d1-sync.py",
     "                    atanan = mid_alt + blok_i * adim\n"
     "                    if blok_i == blok_k:\n"
     "                        aktif_mid_grup = None",
     "                    atanan = mid_alt + (blok_k - blok_i + 1) * adim\n"
     "                    if blok_i == blok_k:\n"
     "                        aktif_mid_grup = None",
     "KIRMIZI"),

    # ── OLDURUCU: mesaj secimi eski metne ────────────────────────────────────────
    ("OLDURUCU M4 _seq_fail_loud NO-OP kolu eski metne dondu",
     "d1-sync.py",
     "    ifadeler, hata = seq_normalize_plan(urunler, mevcut_seq)\n"
     "    if hata or ifadeler:\n"
     "        sys.exit(\"!! SEQ TAM SAYI ARALIGI TUKENDI: %s (alt=%s ust=%s k=%s). \"\n"
     "                 \"Kesirli seq yazilmaz; once python3 tools/d1-sync.py \"\n"
     "                 \"--seq-normalize kos.\" % (uid, alt, ust, k))\n"
     "    sys.exit(\"!! SEQ TAM SAYI ARALIGI TUKENDI: %s (alt=%s ust=%s k=%s). \"\n"
     "             \"bosluk zaten kanonik; bu bir ARDISIK EKLEME tukenmesidir\" % (uid, alt, ust, k))",
     "    ifadader, hata = seq_normalize_plan(urunler, mevcut_seq)\n"
     "    sys.exit(\"!! SEQ TAM SAYI ARALIGI TUKENDI: %s (alt=%s ust=%s k=%s). \"\n"
     "             \"Kesirli seq yazilmaz; once python3 tools/d1-sync.py \"\n"
     "             \"--seq-normalize kos.\" % (uid, alt, ust, k))",
     "KIRMIZI"),

    # ── KONTROL: davranissiz yazim ──────────────────────────────────────────────
    ("KONTROL K1 davranissiz yazim (docstring'e (K153) etiketi)",
     "d1-sync.py",
     "      icin yeni mesaj basilir: bu bir ARDISIK EKLEME tukenmesidir.\n"
     "    \"\"\"",
     "      icin yeni mesaj basilir: bu bir ARDISIK EKLEME tukenmesidir. (K153)\n"
     "    \"\"\"",
     "YESIL"),
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
    tmp = tempfile.mkdtemp(prefix="d1-seq-mutasyon-")
    sonuc = []
    try:
        for ad, dosya, eski, yeni, beklenen in MUTANTLAR:
            kaynak_yolu = os.path.normpath(os.path.join(TOOLS, dosya))
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                # CAPA TAM BIR KEZ ESLESMELI. Kaymissa "mutant uygulanamadi" YESIL
                # sayilmaz; kanit OLCULEMEDI'dir.
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(os.path.join(tmp, str(len(sonuc))))
            hedef = os.path.normpath(os.path.join(kok, "tools", dosya))
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI_ADI)],
                               capture_output=True, text=True, cwd=kok)
            cikti = r.stdout + r.stderr
            fail = len(re.findall(r"^ *KALDI ", cikti, re.M))
            gecti = len(re.findall(r"^ *GECTI ", cikti, re.M))
            if r.returncode == 0:
                gozlem = "YESIL"
            elif gecti >= TABAN_GECTI:
                # Esik kadar on-kontrol GECTI'si yazildiysa vakalardan biri krildi
                # (M1 SystemExit, digerleri KALDI basar); yeterli "test kosuldu" isareti.
                gozlem = "KIRMIZI"
            else:
                gozlem = "COKME(GECTI=%d < %d)" % (gecti, TABAN_GECTI)
            sonuc.append((ad, beklenen, "%s (KALDI=%d GECTI=%d)" % (gozlem, fail, gecti)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: tools/%s)" % KAPI_ADI)
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-88s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
