#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — durum.py "7) YEDEK TAZELIGI" bolumu (bkz. durum-edge-test.py emsali).

NEDEN VAR: yedegin kendisi degil, YEDEGIN SESSIZCE DURMASI oldurucu (26 Tem olcumu:
yedekle.py dogru calisiyordu, 5 gun kimse kosmadi, mutasyon-kanitli skill dosyalari
yedekte bayat kaldi, hicbir sey uyarmadi). Pano bu bayatligi GORUNUR kilar. Uc sessiz-hata:
  (A) esik olu -- "bayat" hali hic yanmaz, pano hep yesil gorunur,
  (B) pano Drive yokken PATLAR -- her oturum basinda kirilir, kimse kosmaz olur,
  (C) pano SALT-OKUNUR sozlesmesini kirar -- drive_yolu.stl_dizini() cagirmak
      .stl-backup-dir'i DUZELTIR = DOSYA YAZAR (pano "hicbir sey yazmaz" diyor).
Ucunun de KIRMIZI-MUTASYON kaniti asagida.

Kosum:  python3 tools/durum-yedek-test.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
DURUM = os.path.join(TOOLS, "durum.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")

SONUC = []


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mutant_yaz(dizin, eski, yeni, ad="durum_mutant.py"):
    """durum.py'nin mutasyonlu kopyasi. Capa yoksa RuntimeError (bayat capa sessiz gecmesin).
    ⚠️ drive_yolu.py mutantin YANINA KOPYALANMAZ: o modulun ROOT'u GERCEK repoyu gosterir,
    mutant onu cagirsa gercek .stl-backup-dir'e yazardi."""
    with open(DURUM, encoding="utf-8") as f:
        kaynak = f.read()
    if eski not in kaynak:
        raise RuntimeError("MUTASYON CAPASI BULUNAMADI (durum.py degismis): %r" % eski)
    hedef = os.path.join(dizin, ad)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(eski, yeni, 1))
    return hedef


def damga_kur(backup, yas_saniye, **ekstra):
    """yas_saniye NEGATIF verilirse damga GELECEK tarihli olur (F3 senaryosu)."""
    os.makedirs(backup, exist_ok=True)
    veri = {"surum": 2, "zaman": time.time() - yas_saniye, "iso": "TEST", "tam": True,
            "eksik": [], "memory": 0, "skills": 0, "repo": 4}
    veri.update(ekstra)
    with open(os.path.join(backup, ".son-yedek.json"), "w") as f:
        json.dump(veri, f)
    return backup


def main():
    durum = modul_yukle(DURUM, "durum_gercek")

    # ---------------- 1) TAZE ----------------
    print("\n1) TAZE damga — uyari BASMAMALI")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 3600)          # 1 saat once
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'taze'", d["hal"] == "taze", d["hal"])
        kontrol("satirda BAYAT/uyari YOK", "BAYAT" not in satir and "⚠" not in satir, satir)

    # ---------------- 2) BAYAT (kirmizi-mutasyon: yedegi yapay bayatlat) ----------------
    print("\n2) BAYAT damga (3 gun geriye alindi) — UYARI BASMALI")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 3 * 86400)
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'bayat'", d["hal"] == "bayat", d["hal"])
        kontrol("satirda BAYAT uyarisi VAR", "BAYAT" in satir and "⚠" in satir)
        kontrol("uyari ne yapilacagini SOYLUYOR", "tools/yedekle.py" in satir)

    # ---------------- 3) ESIK SABITI GERCEKTEN KULLANILIYOR MU ----------------
    print("\n3) KIRMIZI-MUTASYON (esik) — sabit degisince siniflama degismeli")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 3600)          # 1 saat: normalde TAZE
        eski_esik = durum.YEDEK_BAYAT_SANIYE
        try:
            durum.YEDEK_BAYAT_SANIYE = 10                        # mutasyon: esik 10 sn
            d = durum.yedek_durumu(b, "var")
        finally:
            durum.YEDEK_BAYAT_SANIYE = eski_esik
        kontrol("esik 10 sn iken ayni damga BAYAT sayildi (sabit olu degil)",
                d["hal"] == "bayat", d["hal"])
        kontrol("esik geri alininca yine TAZE",
                durum.yedek_durumu(b, "var")["hal"] == "taze")
        kontrol("varsayilan esik ~2 gun", eski_esik == 2 * 86400, str(eski_esik))

    # ---------------- 4) DAMGASIZ (eski surumle alinmis yedek) ----------------
    print("\n4) DAMGASIZ yedek — 'olculemedi' demeli, TAZE SAYMAMALI")
    with tempfile.TemporaryDirectory() as td:
        b = os.path.join(td, "backup")
        os.makedirs(b)
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'damgasiz'", d["hal"] == "damgasiz", d["hal"])
        kontrol("ÖLÇÜLEMEDİ diyor", "ÖLÇÜLEMEDİ" in satir)
        kontrol("taze DEMIYOR (sahte guven yok)", "taze:" not in satir)
        # bozuk JSON da damgasiz sayilmali (patlamamali)
        with open(os.path.join(b, ".son-yedek.json"), "w") as f:
            f.write("{bozuk json")
        kontrol("bozuk damga JSON'unda PATLAMIYOR",
                durum.yedek_durumu(b, "var")["hal"] == "damgasiz")

    # ---------------- 5) DRIVE YOK ----------------
    print("\n5) DRIVE YOK — ÖLÇÜLEMEDİ, cokme yok")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        eski = durum._drive_deseni
        try:
            durum._drive_deseni = lambda: os.path.join(td, "olmayan-*", "STL")
            yol, hal = durum.yedek_dizini(kok)
        finally:
            durum._drive_deseni = eski
        satir = " ".join(durum.yedek_satirlari(durum.yedek_durumu(yol, hal)))
        kontrol("hal 'drive-yok'", hal == "drive-yok", hal)
        kontrol("ÖLÇÜLEMEDİ + 'Drive bagli degil'",
                "ÖLÇÜLEMEDİ" in satir and "Drive bagli degil" in satir)

    # ---------------- 6) SALT-OKUNUR SOZLESMESI ----------------
    print("\n6) SALT-OKUNUR — pano .stl-backup-dir'e DOKUNMAMALI")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        cfg = os.path.join(kok, ".stl-backup-dir")
        with open(cfg, "w") as f:
            f.write("/bayat/olmayan/yol/STL")
        onceki = (open(cfg).read(), os.path.getmtime(cfg))
        durum.yedek_dizini(kok)
        kontrol("bayat .stl-backup-dir DEGISMEDI (pano yazmadi)",
                (open(cfg).read(), os.path.getmtime(cfg)) == onceki)

        # KIRMIZI-MUTASYON: pano dosya yazsa bu kontrol kirmizi yanar mi?
        mut = mutant_yaz(td,
                         '    cfg = os.path.join(repo_kok, ".stl-backup-dir")',
                         '    cfg = os.path.join(repo_kok, ".stl-backup-dir")\n'
                         '    open(cfg, "w").write("MUTANT")  # MUTANT: pano yaziyor')
        mmod = modul_yukle(mut, "durum_mutant_yazan")
        with open(cfg, "w") as f:
            f.write("/bayat/olmayan/yol/STL")
        onceki = open(cfg).read()
        mmod.yedek_dizini(kok)
        kontrol("MUTANTTA dosya DEGISTI (kontrol KIRMIZI yanardi)",
                open(cfg).read() != onceki)

    # ---------------- 6b) F2: DAMGANIN IDDIASI vs DRIVE'IN GERCEGI ----------------
    print("\n6b) F2 — 'icerik' satiri damganin IDDIASI; gercekle karsilastirilmali")
    with tempfile.TemporaryDirectory() as td:
        b = os.path.join(td, "backup")
        damga_kur(b, 3600, memory=3, skills=2)
        for alt, adet in (("memory", 3), ("skills", 2)):
            os.makedirs(os.path.join(b, alt))
            for i in range(adet):
                with open(os.path.join(b, alt, "d%d.txt" % i), "w") as f:
                    f.write("x")
        saglam = " ".join(durum.yedek_satirlari(durum.yedek_durumu(b, "var")))
        kontrol("saglam yedekte ICERIK EKSIK uyarisi YOK", "ICERIK EKSIK" not in saglam)
        # F2 senaryosu: yedek icerigi silindi, damga aynen duruyor
        shutil.rmtree(os.path.join(b, "skills"))
        d = durum.yedek_durumu(b, "var")
        bozuk = " ".join(durum.yedek_satirlari(d))
        kontrol("silinen icerik YAKALANDI", "ICERIK EKSIK" in bozuk, bozuk[-120:])
        kontrol("sayim gercekle karsilastirildi", d["sayim"].get("skills") == (0, 2),
                str(d["sayim"]))
        kontrol("hala 'taze' diyor ama uyari EKLI (sahte guven yok)",
                d["hal"] == "taze" and "⚠⚠" in bozuk)

    # ---------------- 6c) F3: GELECEK TARIHLI DAMGA ----------------
    print("\n6c) F3 — gelecek tarihli damga 'taze' DEMEMELI")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), -3600)      # 1 saat GELECEKTE
        d = durum.yedek_durumu(b, "var")
        satir = " ".join(durum.yedek_satirlari(d))
        kontrol("hal 'supheli'", d["hal"] == "supheli", d["hal"])
        kontrol("'taze' DEMIYOR", "taze:" not in satir)
        kontrol("ŞÜPHELİ + ÖLÇÜLEMEDİ diyor", "ŞÜPHELİ" in satir and "ÖLÇÜLEMEDİ" in satir)
        kontrol("1 saniye gelecek bile taze SAYILMIYOR (tolerans yok)",
                durum.yedek_durumu(damga_kur(os.path.join(td, "b2"), -1), "var")["hal"]
                == "supheli")

    # ---------------- 6d) F1: KISMI DAMGA PANODA ----------------
    print("\n6d) F1 — kismi yedek panoda TAZE gibi gecmemeli")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 60, tam=False,
                      eksik=[".urun-kaynaklari.json", "DEVAM-ARSIV.md"])
        satir = " ".join(durum.yedek_satirlari(durum.yedek_durumu(b, "var")))
        kontrol("KISMI YEDEK uyarisi VAR", "KISMI YEDEK" in satir)
        kontrol("eksik dosya adlari yaziliyor", ".urun-kaynaklari.json" in satir)
        b2 = damga_kur(os.path.join(td, "b2"), 60, tam=True, eksik=[])
        kontrol("tam yedekte KISMI uyarisi YOK",
                "KISMI YEDEK" not in " ".join(durum.yedek_satirlari(durum.yedek_durumu(b2, "var"))))
        b3 = os.path.join(td, "b3")
        os.makedirs(b3)
        with open(os.path.join(b3, ".son-yedek.json"), "w") as f:
            json.dump({"zaman": time.time() - 60, "iso": "ESKI", "memory": 1}, f)
        kontrol("eski surum damgasi 'tamlik bilgisi yok' notu aliyor",
                "tamlik bilgisi yok" in " ".join(
                    durum.yedek_satirlari(durum.yedek_durumu(b3, "var"))))

    # ---------------- 7) UCTAN UCA: gercek pano ----------------
    print("\n7) UCTAN UCA — python3 tools/durum.py")
    r = subprocess.run([sys.executable, DURUM], capture_output=True, text=True)
    kontrol("exit 0", r.returncode == 0, "rc=%d" % r.returncode)
    kontrol("'7) YEDEK TAZELIGI' bolumu basildi", "7) YEDEK TAZELIGI" in r.stdout)
    kontrol("bolum bos degil", any(
        x in r.stdout for x in ("taze:", "BAYAT", "ÖLÇÜLEMEDİ", "backup/ klasoru YOK")))

    # ---------------- 8) UCTAN UCA: DRIVE YOKKEN COKMUYOR ----------------
    print("\n8) UCTAN UCA — Drive'siz makinede pano cokmemeli (exit 0)")
    with tempfile.TemporaryDirectory() as td:
        sahte_ev = os.path.join(td, "ev")
        kok = os.path.join(td, "repo")
        os.makedirs(os.path.join(kok, "tools"))
        os.makedirs(sahte_ev)
        shutil.copy2(DURUM, os.path.join(kok, "tools", "durum.py"))
        shutil.copy2(DRIVE_YOLU, os.path.join(kok, "tools", "drive_yolu.py"))
        subprocess.run(["git", "-C", kok, "init", "-q"], capture_output=True)
        ortam = dict(os.environ)
        ortam["HOME"] = sahte_ev                 # Drive mount deseni HICBIR SEYE uymaz
        r = subprocess.run([sys.executable, os.path.join(kok, "tools", "durum.py")],
                           capture_output=True, text=True, env=ortam)
        kontrol("Drive'siz pano exit 0 (COKMEDI)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, r.stderr.strip()[:120]))
        kontrol("ÖLÇÜLEMEDİ yazdi", "ÖLÇÜLEMEDİ" in r.stdout)
        kontrol("traceback YOK", "Traceback" not in r.stderr)

    # ---------------- OZET ----------------
    kirmizi = [a for a, ok in SONUC if not ok]
    print("\n" + "=" * 70)
    print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    for a in kirmizi:
        print("  ❌ " + a)
    print("SONUC: " + ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
