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


def mutant_yaz(dizin, eski, yeni, ad="durum_mutant.py"):  # noqa: D401 (bkz. asagi)
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

    # ---------------- 6e) N2: ILK SATIR DURUMU SOYLUYOR MU ----------------
    print("\n6e) N2 — goz gezdiren ILK SATIRDAN yanlis sonuca VARAMAMALI")
    with tempfile.TemporaryDirectory() as td:
        # (a) tam + taze + icerik tutuyor -> tek mesru "taze" hali
        a = damga_kur(os.path.join(td, "a"), 60, memory=1, skills=1)
        for alt in ("memory", "skills"):
            os.makedirs(os.path.join(a, alt))
            with open(os.path.join(a, alt, "d.txt"), "w") as f:
                f.write("x")
        bas_a = durum.yedek_satirlari(durum.yedek_durumu(a, "var"))[0]
        kontrol("(a) tam-taze ILK SATIR 'taze'", bas_a.strip().startswith("taze:"), bas_a)

        # (b) kismi yedek
        b = damga_kur(os.path.join(td, "b"), 60, tam=False, eksik=[".urun-kaynaklari.json"])
        bas_b = durum.yedek_satirlari(durum.yedek_durumu(b, "var"))[0]
        kontrol("(b) kismi ILK SATIR 'KISMI YEDEK'", "KISMI YEDEK" in bas_b, bas_b)
        kontrol("(b) ILK SATIR 'taze' DEMIYOR", "taze:" not in bas_b)

        # (c) icerik eksik
        c = damga_kur(os.path.join(td, "c"), 60, memory=0, skills=5)
        bas_c = durum.yedek_satirlari(durum.yedek_durumu(c, "var"))[0]
        kontrol("(c) icerik-eksik ILK SATIR 'ICERIK EKSIK'", "ICERIK EKSIK" in bas_c, bas_c)
        kontrol("(c) ILK SATIR 'taze' DEMIYOR", "taze:" not in bas_c)

        # (d) gelecek tarihli
        d4 = damga_kur(os.path.join(td, "d"), -3600)
        bas_d = durum.yedek_satirlari(durum.yedek_durumu(d4, "var"))[0]
        kontrol("(d) gelecek-tarihli ILK SATIR 'ŞÜPHELİ'", "ŞÜPHELİ" in bas_d, bas_d)
        kontrol("(d) ILK SATIR 'taze' DEMIYOR", "taze:" not in bas_d)

        # bayat + kismi birlikte: baslik uyariyor, digeri de kaybolmuyor
        e = damga_kur(os.path.join(td, "e"), 3 * 86400, tam=False, eksik=["DEVAM-ARSIV.md"])
        sat_e = durum.yedek_satirlari(durum.yedek_durumu(e, "var"))
        kontrol("(e) bayat+kismi: baslik BAYAT, kismi da raporlu",
                "BAYAT" in sat_e[0] and any("KISMI YEDEK" in s for s in sat_e[1:]))

    # ---------------- 6g) ATLANAN KOSUM (kilit) ----------------
    # yedekle.py kilidi alamazsa hicbir sey kopyalamaz; damgaya yalniz `son_atlama*`
    # yazar. Pano bu hali TAZE SAYMAMALI — ama KAPSANMIS atlamada da bosuna
    # uyarmamali (her paralel push'ta sari pano = kimsenin bakmadigi pano).
    print("\n6g) ATLANAN KOSUM — kapsanmayan atlama uyarir, kapsanan SUSAR")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        # (a) KAPSANMAYAN atlama: son tam kosum bitti, SONRA bir kosum atlandi
        a = damga_kur(os.path.join(td, "a"), 600, baslangic=simdi - 660,
                      son_atlama=simdi - 300, son_atlama_iso="2026-07-26 12:00:00",
                      son_atlama_sebep="baska yedek kosuyordu (pid=1234)",
                      son_atlama_kapsandi=False)
        sat_a = durum.yedek_satirlari(durum.yedek_durumu(a, "var"))
        print("     --- pano ciktisi (a) ---")
        for s in sat_a:
            print("    " + s)
        kontrol("(a) ILK SATIR 'taze' DEMIYOR", "taze:" not in sat_a[0], sat_a[0])
        kontrol("(a) mevcut sozluk: 'KISMI YEDEK' + 'ATLANDI'",
                "KISMI YEDEK" in sat_a[0] and "ATLANDI" in sat_a[0])
        kontrol("(a) sebep ve zaman yaziyor",
                "2026-07-26 12:00:00" in sat_a[0] and "baska yedek" in sat_a[0])
        kontrol("(a) ne yapilacagi yazili", "tools/yedekle.py" in " ".join(sat_a))

        # (b) KAPSANAN atlama + sahip damgayi YAZDI (eszamanli push cifti): uyari YOK
        b = damga_kur(os.path.join(td, "b"), 600, baslangic=simdi - 660,
                      son_atlama=simdi - 300, son_atlama_kapsandi=True,
                      son_atlama_sahip_baslangici=simdi - 660)
        sat_b = durum.yedek_satirlari(durum.yedek_durumu(b, "var"))
        kontrol("(b) kapsanan + sahip bitirmis atlamada pano SUSUYOR ('taze')",
                sat_b[0].strip().startswith("taze:") and not any("ATLANDI" in s for s in sat_b),
                sat_b[0])

        # (b2) 🔴 KAPSANAN ama sahip damgayi HIC YAZMAMIS (asildi/oldu) -> UYARI SART
        b2 = damga_kur(os.path.join(td, "b2"), 600, baslangic=simdi - 660,
                       son_atlama=simdi - 300, son_atlama_kapsandi=True,
                       son_atlama_sahip_baslangici=simdi - 400)   # damga ondan ESKI
        sat_b2 = durum.yedek_satirlari(durum.yedek_durumu(b2, "var"))
        kontrol("(b2) sahip bitirmemisken 'kapsandi' SUSTURMUYOR",
                not sat_b2[0].strip().startswith("taze:") and "ATLANDI" in sat_b2[0],
                sat_b2[0])
        kontrol("(b2) sebep aciklikla yaziyor", "HIC YAZMADI" in sat_b2[0])

        # (b3) sahip alani HIC YOK (cozulemez) -> fail-closed UYAR
        b3 = damga_kur(os.path.join(td, "b3"), 600, baslangic=simdi - 660,
                       son_atlama=simdi - 300, son_atlama_kapsandi=True)
        kontrol("(b3) sahip alani yoksa fail-closed UYARIYOR",
                "ATLANDI" in durum.yedek_satirlari(durum.yedek_durumu(b3, "var"))[0])

        # (c) ESKI atlama: sonrasinda TAM bir kosum BASLADI -> kendi kendine temizlenir
        c = damga_kur(os.path.join(td, "c"), 60, baslangic=simdi - 120,
                      son_atlama=simdi - 3000, son_atlama_kapsandi=False)
        sat_c = durum.yedek_satirlari(durum.yedek_durumu(c, "var"))
        kontrol("(c) sonraki tam kosum atlamayi KAPATIR (uyari yok)",
                sat_c[0].strip().startswith("taze:"), sat_c[0])

        # (d) HIC yedek yokken atlanan kosum: damgada `zaman` YOK -> ÖLÇÜLEMEDİ
        d6 = os.path.join(td, "d")
        os.makedirs(d6)
        with open(os.path.join(d6, ".son-yedek.json"), "w") as fh:
            json.dump({"son_atlama": simdi, "son_atlama_iso": "TEST",
                       "son_atlama_sebep": "baska yedek kosuyordu",
                       "son_atlama_kapsandi": False}, fh)
        dd = durum.yedek_durumu(d6, "var")
        sat_d = durum.yedek_satirlari(dd)
        print("     --- pano ciktisi (d) ---")
        for s in sat_d:
            print("    " + s)
        kontrol("(d) atlama-only damga 'damgasiz' sayiliyor", dd["hal"] == "damgasiz",
                dd["hal"])
        kontrol("(d) 'taze' DEMIYOR + ÖLÇÜLEMEDİ diyor",
                "taze:" not in " ".join(sat_d) and "ÖLÇÜLEMEDİ" in " ".join(sat_d))

        # (e) KILITSIZ kosum notu
        e = damga_kur(os.path.join(td, "e"), 60, baslangic=simdi - 120, kilitsiz=True)
        kontrol("(e) kilitsiz kosum panoda NOT olarak gorunuyor",
                any("KILITSIZ" in s for s in durum.yedek_satirlari(durum.yedek_durumu(e, "var"))))

        # (f) KIRMIZI-MUTASYON 1: atlama kontrolu tumden kaldirilirsa (a) TAZE olur
        mut = mutant_yaz(td,
                         "                and atlama > _ref\n"
                         '                and not (dmg.get("son_atlama_kapsandi") is True '
                         'and _sahip_bitti))',
                         '                and False)  # MUTANT: atlama gorulmuyor',
                         ad="durum_mutant_atlama.py")
        mmod = modul_yukle(mut, "durum_mutant_atlama")
        m_sat = mmod.yedek_satirlari(mmod.yedek_durumu(a, "var"))
        kontrol("MUTANTTA atlanan yedek 'taze' gorunuyor (kontrol KIRMIZI yanardi)",
                m_sat[0].strip().startswith("taze:"), m_sat[0])

        # (g) KIRMIZI-MUTASYON 2: SAHIP COZUMU kaldirilirsa (b2) sessizce TAZE olur
        #     = curutucunun buldugu sessiz veri kaybi yolu, geri gelirse yakalanir.
        mut2 = mutant_yaz(td,
                          "    _sahip_bitti = (isinstance(_sahip, (int, float)) and "
                          "isinstance(_ref, (int, float))\n"
                          "                    and _ref >= _sahip)",
                          "    _sahip_bitti = True  # MUTANT: sahip bitirdi VARSAYILIYOR",
                          ad="durum_mutant_sahip.py")
        mmod2 = modul_yukle(mut2, "durum_mutant_sahip")
        m2 = mmod2.yedek_satirlari(mmod2.yedek_durumu(b2, "var"))
        kontrol("MUTANTTA (varsayim) asili sahip 'taze' gorunuyor (kontrol KIRMIZI yanardi)",
                m2[0].strip().startswith("taze:"), m2[0])

    # ---------------- 6h) YEDEK KILIDI PANODA ----------------
    # Atlama push aninda %100 SESSIZ (pre-push blogu stdout+stderr'i yutar, atlama
    # exit 0). Saatlerdir asili kilit yalnizca BURADA gorunur.
    print("\n6h) KILIT PANODA — asili/yarim kilit GORUNUR, normal kilit SESSIZ")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        kok = os.path.join(td, "repo")
        os.makedirs(kok)
        yol = os.path.join(kok, ".yedek.lock")
        kontrol("kilit dosyasi YOK -> hal 'yok', satir YOK",
                durum.kilit_durumu(kok)["hal"] == "yok"
                and durum.kilit_satirlari(durum.kilit_durumu(kok)) == [])
        with open(yol, "w") as fh:
            fh.write("")
        kontrol("bos kilit (birakilmis) -> hal 'yok', satir YOK",
                durum.kilit_durumu(kok)["hal"] == "yok"
                and durum.kilit_satirlari(durum.kilit_durumu(kok)) == [])
        # canli sahip, yas kucuk -> NORMAL: pano susar (gurultu yapmaz)
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST\n" % (os.getpid(), simdi))
        d_norm = durum.kilit_durumu(kok)
        kontrol("canli + yeni kilit -> 'tutuluyor', satir YOK",
                d_norm["hal"] == "tutuluyor" and durum.kilit_satirlari(d_norm) == [],
                d_norm["hal"])
        # 2 saattir tutan CANLI sahip -> UYARI
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST\n" % (os.getpid(), simdi - 7200))
        d_asili = durum.kilit_durumu(kok)
        sat_asili = durum.kilit_satirlari(d_asili)
        print("     --- pano ciktisi (kilit 2 saattir asili) ---")
        for s in sat_asili:
            print("    " + s)
        kontrol("2 saatlik canli kilit -> hal 'asili'", d_asili["hal"] == "asili",
                d_asili["hal"])
        kontrol("pano SURESINI ve pid'i SOYLUYOR",
                "2.0 saattir" in sat_asili[0] and str(os.getpid()) in sat_asili[0])
        kontrol("pano 'yedekler ATLANIYOR' diyor", "ATLANIYOR" in sat_asili[0])
        kontrol("pano kilidi KIRMA talimati vermiyor, elle kontrol diyor",
                "KIRILMAZ" in sat_asili[1])
        # OLU sahip: yarim kalmis kosum izi
        with open(yol, "w") as fh:
            fh.write("pid=999999 baslangic=%r iso=TEST\n" % (simdi - 60))
        d_yarim = durum.kilit_durumu(kok)
        kontrol("olu pid -> hal 'yarim' (kosum ortasinda kesilmis)",
                d_yarim["hal"] == "yarim" and d_yarim["canli"] is False, d_yarim["hal"])
        kontrol("yarim kilit panoda UYARIYOR",
                "YARIM KALMIS" in durum.kilit_satirlari(d_yarim)[0])
        # bozuk imza
        with open(yol, "w") as fh:
            fh.write("bozuk satir\n")
        kontrol("bozuk imza -> 'okunamadi', pano yine konusuyor",
                durum.kilit_durumu(kok)["hal"] == "okunamadi"
                and "COZULEMEDI" in durum.kilit_satirlari(durum.kilit_durumu(kok))[0])
        # esik SABITI gercekten kullaniliyor mu (olu sabit nobetcisi)
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST\n" % (os.getpid(), simdi - 60))
        kontrol("esik 10 sn'ye cekilince ayni kilit 'asili' oluyor",
                durum.kilit_durumu(kok, esik=10)["hal"] == "asili")
        # iki dosyadaki esik/ad AYNI mi (surukleme nobetcisi)
        yedekle_mod = modul_yukle(os.path.join(TOOLS, "yedekle.py"), "yedekle_esik")
        kontrol("kilit ADI iki dosyada ayni",
                durum.YEDEK_KILIT_ADI == yedekle_mod.KILIT_ADI, durum.YEDEK_KILIT_ADI)
        kontrol("asili esigi iki dosyada ayni",
                durum.YEDEK_KILIT_ASILI == yedekle_mod.KILIT_UYARI_YASI,
                "%s / %s" % (durum.YEDEK_KILIT_ASILI, yedekle_mod.KILIT_UYARI_YASI))
        # pano ana akisi kilidi GERCEKTEN cagiriyor mu (kablolama nobetcisi)
        gov = open(DURUM, encoding="utf-8").read()
        kontrol("main() kilit satirlarini ekliyor", "kilit_satirlari(kilit_durumu(kok))" in gov)

    # ---------------- 6f) N3: ZAMAN ASIMI — PANO ASILMAZ ----------------
    print("\n6f) N3 — Drive yanit vermezse pano BEKLEMEZ")
    with tempfile.TemporaryDirectory() as td:
        b = damga_kur(os.path.join(td, "backup"), 60)
        eski_say, eski_asim = durum._agac_say, durum.YEDEK_ZAMAN_ASIMI

        def asili_say(dizin):                      # yanit vermeyen mount taklidi
            time.sleep(2.0)
            return 0

        try:
            durum._agac_say = asili_say
            durum.YEDEK_ZAMAN_ASIMI = 0.2
            bas = time.time()
            sonuc, asildi = durum.zaman_asimiyla(
                lambda: durum.yedek_satirlari(durum.yedek_durumu(b, "var")))
            sure = time.time() - bas
            kontrol("zaman asimina DUSTU", asildi is True)
            kontrol("sure SINIRLI (<1 sn)", sure < 1.0, "%.3f sn" % sure)
            kontrol("sonuc dondurulmedi (terk edildi)", sonuc is None)

            # KIRMIZI-MUTASYON: zaman asimi kaldirilirsa asili mount panoyu bekletir
            mut = mutant_yaz(td,
                             "    ip = threading.Thread(target=sar, daemon=True)",
                             "    sar()  # MUTANT: zaman asimi YOK\n"
                             "    return kutu.get('sonuc'), False\n"
                             "    ip = threading.Thread(target=sar, daemon=True)",
                             ad="durum_mutant_asim.py")
            mmod = modul_yukle(mut, "durum_mutant_asim")
            mmod._agac_say = asili_say
            mmod.YEDEK_ZAMAN_ASIMI = 0.2
            bas = time.time()
            _s, m_asildi = mmod.zaman_asimiyla(
                lambda: mmod.yedek_satirlari(mmod.yedek_durumu(b, "var")))
            m_sure = time.time() - bas
            kontrol("MUTANTTA zaman asimi YOK (asili mount panoyu bekletti)",
                    m_asildi is False and m_sure >= 1.5, "%.3f sn" % m_sure)
        finally:
            durum._agac_say, durum.YEDEK_ZAMAN_ASIMI = eski_say, eski_asim
        kontrol("saglam olcum zaman asimina DUSMUYOR",
                durum.zaman_asimiyla(lambda: "ok") == ("ok", False))
        kontrol("varsayilan zaman asimi makul (1-30 sn)",
                1 <= durum.YEDEK_ZAMAN_ASIMI <= 30, str(durum.YEDEK_ZAMAN_ASIMI))
        # KABLOLAMA NOBETCISI: yardimci VAR ama main() onu KULLANMIYORSA yukaridaki
        # davranissal kanit anlamsizdir (gercek Drive'i asili yapamadigimiz icin
        # uctan uca olculemiyor) -> kaynak capasiyla baglanti dogrulanir.
        gov = open(DURUM, encoding="utf-8").read()
        kontrol("main() olcumu zaman_asimiyla ile sariyor", "zaman_asimiyla(_olc)" in gov)
        kontrol("zaman asimi mesaji panoda tanimli", "Drive yanit vermiyor" in gov)

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
