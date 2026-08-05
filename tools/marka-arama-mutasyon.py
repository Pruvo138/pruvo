#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — `marka_arama` kabul testi GERCEK ihlali yakiyor mu?

  Kapi: tools/marka-arama-d1-test.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu repoda durur, kabul CIKIS KODU degil
OLCULEN IDDIA SAYISI + ISARET SARTIDIR (cokme kirmiziyla karisir).

BU KAPININ EN BUYUK RISKI TOTOLOJIDIR: kolonun degeri de, testin REFERANSI da ayni
yuklemden (arama.marka_sorgusu_esler) turer. Referans BASKA BIR GOVDEDEN
(marka-invaryant-kapisi.olc) alinarak bu risk daraltildi; asagidaki OLDURUCU mutantlar
kalan yuzeyi olcer:
  * yuklemi SERBEST METNE ceviren mutant (M1) — bugunku uc davranisi. Kolon "Havalandirma"yi
    Haval'a baglar, "Mandali"yi MAN'a. Kirmizi yanmazsa kapi HICBIR SEY olcmuyor demektir.
  * `marka_arama = marka_kanon` yapan mutant (M2) — BASLIK kolu FIILEN olculuyor mu.
  * TERSI (M3): yalniz baslik kolu — `marka_arama ⊇ marka_kanon` sozlesmesi FIILEN olculuyor mu.
  * sema/plan/fail-closed eksenleri (M4-M8) — her biri kendi iddiasini TEK BASINA dusurur
    ([[beyan-edilmis-survivor]]: katmanlarin VEYA'si degil, TEKIL eksen olculur).
KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali — yoksa kapi "her degisiklige
kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

CAPA DISIPLINI: her mutant capasinin kaynak dosyada TAM BIR KEZ gecmesi SART. Gecmezse
sonuc "YESIL" degil "CAPA-YOK"tur (mutant uygulanamadan yesil sayilmasi, bataryayi sessizce
kor ederdi).

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi
O AYNADAN kosulur.

Calistir:  python3 tools/marka-arama-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "marka-arama-d1-test.py"

# Bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir. Saglam kosum 46 GECTI basar;
# en cok iddia dusuren OLDURUCU (M8, fail-closed dali) 40'in ustunde kalir. Esik, kapinin
# erken cikip birkac kontrol basarak "kirmizi" gorunmesini AYIRT ETMEK icindir.
TABAN_GECTI = 30

# (ad, dosya [TOOLS'a gore], eski, yeni, beklenen)
MUTANTLAR = [
    # ── OLDURUCU: yuklemin KENDISI ──────────────────────────────────────────────
    ("OLDURUCU M1 YUKLEMI SERBEST METNE CEVIR (bugunku uc davranisi: alt-dize)",
     "d1-sync.py",
     "        deger = [m for m in adaylar\n"
     "                 if arama.marka_sorgusu_esler(m, uyeler, baslik_uyum)]",
     "        deger = [m for m in evren.taninmis\n"
     "                 if arama.esles(arama.haystack(u), arama.tokenlar(m))]",
     "KIRMIZI"),
    ("OLDURUCU M2 marka_arama = marka_kanon (BASLIK kolunu at)",
     "d1-sync.py",
     "        adaylar = list(uyeler) + [m for m in baslik_uyum if m not in uyeler]",
     "        adaylar = list(uyeler)", "KIRMIZI"),
    ("OLDURUCU M3 UYELIK kolunu at (yalniz baslik) — ⊇ sozlesmesi olculuyor mu",
     "d1-sync.py",
     "        adaylar = list(uyeler) + [m for m in baslik_uyum if m not in uyeler]",
     "        adaylar = list(baslik_uyum)", "KIRMIZI"),
    ("OLDURUCU M4 COK KELIMELI MARKAYI BOL — pencere 1 kelime (Land Rover -> Rover)",
     "arama.py",
     "        for k in range(min(MARKA_BASLIK_AZAMI_KELIME, n - i), 0, -1):",
     "        for k in range(min(1, n - i), 0, -1):", "KIRMIZI"),
    # ── OLDURUCU: senkron makinesi ──────────────────────────────────────────────
    ("OLDURUCU M5 PLAN NO-OP — hedefli UPDATE uretilmesin (kolon SONSUZA DEK '[]')",
     "d1-sync.py",
     "    return sema_plan(\"marka_arama\", urunler, aramalar, mevcut_arama, izleme,\n"
     "                     varsayilan=\"[]\")",
     "    return []", "KIRMIZI"),
    ("OLDURUCU M6 SEMA SIRASI KAPISINI AC — SELECT kolonu KOSULSUZ istesin",
     "d1-sync.py",
     "                + (\", marka_arama\" if marka_arama_kolonu else \"\"))",
     "                + \", marka_arama\")", "KIRMIZI"),
    ("OLDURUCU M7 KOLONU ZORUNLU YAP (yoklugu TUM senkronu dusurur)",
     "d1-sync.py",
     "ZORUNLU_KOLONLAR = [\"tur\", \"stokta\", \"uyum\"]",
     "ZORUNLU_KOLONLAR = [\"tur\", \"stokta\", \"uyum\", \"marka_arama\"]", "KIRMIZI"),
    ("OLDURUCU M8 FAIL-CLOSED'I AC — tek kaynak okunamayinca SESSIZ bos harita don",
     "d1-sync.py",
     "    mmb, evren, ek, sebep = marka_kaynaklari(urunler)\n"
     "    if sebep:\n"
     "        return {}, sebep\n"
     "    ek_normlu = mmb.ek_marka_normlu(ek)",
     "    mmb, evren, ek, sebep = marka_kaynaklari(urunler)\n"
     "    if sebep:\n"
     "        return {}, None\n"
     "    ek_normlu = mmb.ek_marka_normlu(ek)", "KIRMIZI"),
    ("OLDURUCU M9 ALTER DEFAULT'unu '' YAP (uc JSON.parse'i kosulsuz uygulayamaz)",
     "d1-sync.py",
     "    (\"marka_arama\", \"TEXT NOT NULL DEFAULT '[]'\"),",
     "    (\"marka_arama\", \"TEXT NOT NULL DEFAULT ''\"),", "KIRMIZI"),
    ("OLDURUCU M10 KATLAMAYI KAPAT — uyelik ham degerden dogsun (Volvo Penta artik Volvo degil)",
     "marka_model_build.py",
     "        kan = evren.katla((x or \"\").strip())",
     "        kan = (x or \"\").strip()", "KIRMIZI"),
    # ── KONTROL: iddia edilmeyen eksen / davranissiz yazim ──────────────────────
    ("KONTROL K1 davranissiz yazim (harita = {} -> dict())",
     "d1-sync.py",
     "    harita = {}\n    for u in urunler:\n"
     "        if not isinstance(u, dict):\n            continue\n"
     "        uid = u.get(\"id\")\n        if not uid:\n            continue\n"
     "        uyeler = mmb.marka_uyelikleri(u.get(\"marka\") or [], evren, ek)\n"
     "        baslik_uyum = arama.baslik_marka_uyumlari(u.get(\"baslik\"), kanon)",
     "    harita = dict()\n    for u in urunler:\n"
     "        if not isinstance(u, dict):\n            continue\n"
     "        uid = u.get(\"id\")\n        if not uid:\n            continue\n"
     "        uyeler = mmb.marka_uyelikleri(u.get(\"marka\") or [], evren, ek)\n"
     "        baslik_uyum = arama.baslik_marka_uyumlari(u.get(\"baslik\"), kanon)",
     "YESIL"),
    ("KONTROL K2 iddia edilmeyen eksen (sema aciklama metni)",
     "d1-sema.sql",
     "  -- MARKA ARAMA UYELIGI (5 Agu 2026)",
     "  -- MARKA ARAMA UYELIGI  (5 Agu 2026)", "YESIL"),
    ("KONTROL K3 davranissiz yazim (baslik jetonlamasinda uyumlar = [] -> list())",
     "arama.py",
     "    uyumlar = []\n    i, n = 0, len(kel)",
     "    uyumlar = list()\n    i, n = 0, len(kel)", "YESIL"),
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
    tmp = tempfile.mkdtemp(prefix="marka-arama-mutasyon-")
    sonuc = []
    try:
        for ad, dosya, eski, yeni, beklenen in MUTANTLAR:
            kaynak_yolu = os.path.normpath(os.path.join(TOOLS, dosya))
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                # 🔴 CAPA TAM BIR KEZ ESLESMELI. Kaymissa "mutant uygulanamadi" YESIL
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
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-86s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
