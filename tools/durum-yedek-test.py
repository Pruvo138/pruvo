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

⚪ ORTAM BAGIMLILIGI — `ps` (K4, 27 Tem): surec KIMLIK dogrulamasini olcen 5 kontrol dis
`ps` binary'sine baglidir. Bu adim deploy.yml'de BLOKLAYICI kosuyor ve `deploy: needs:
build` -> `ps` yoksa kirmizi yanmak TUM pruvo3d.com YAYININI durdururdu. Bu depoda
yanlis-pozitifin butun yayini durdurdugu bir vaka YASANDI ([[kapi-kapsam-eksen-secimi]]).
Karar: `ps` yoksa o kontroller GORUNUR ⚪ OLCULEMEDI olur (ozet satirinda sayilir) ve
cikis kodunu BOZMAZ; kapinin geri kalani BLOKLAYICI kalir.
🔴 SESSIZ YESILE CEVRILMEZ: kapi durum.py'nin KENDI fonksiyonuna degil `ps` BINARY'sinin
varligina bakar (ps_kullanilabilir). Yoksa `_surec_bilgisi`'ni olduren bir mutasyon
"OLCULEMEDI" kilifina girip kacardi — bunun kaniti 6h'deki mutant nobetcidir.

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

# Alt kosum bayragi (K4 nobetcisi kendini `ps`siz PATH ile yeniden cagirir).
ALT_KOSUM = "--ps-yok-alt-kosum"

SONUC = []
OLCULEMEDI = []
PS_BAGIMLI = [0]          # ps'e bagli kontrol SAYISI (ilan; alt kosum bunu dogrular)
PS_VAR = [True]


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def olculemedi(ad, ayrinti=""):
    """GORUNUR olculemedi: cikis kodunu BOZMAZ ama ozette SAYILIR (sessiz atlama YOK)."""
    OLCULEMEDI.append((ad, ayrinti))
    print("  ⚪ ÖLÇÜLEMEDİ  " + ad + (("  — " + ayrinti) if ayrinti else ""))
    return None


def ps_kullanilabilir():
    """`ps` binary'si GERCEKTEN var ve calisiyor mu — durum.py'den BAGIMSIZ olcum.

    🔴 NEDEN durum._surec_bilgisi KULLANILMAZ: kapiyi olculen kodun kendi fonksiyonuna
    baglamak SESSIZ YESIL uretir — o fonksiyonu olduren bir mutasyon "ps yokmus"
    goruntusu verip 5 kontrolu birden OLCULEMEDI'ye kacirirdi. Burada yalniz ORTAM
    sorgulanir; kodun dogrulugu ayri (6h mutant nobetcisi)."""
    yol = shutil.which("ps")
    if not yol:
        return False
    try:
        p = subprocess.run([yol, "-p", str(os.getpid()), "-o", "etime=,comm="],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0 and bool((p.stdout or "").strip())


def ps_kontrol(ad, ok, ayrinti=""):
    """`ps`e BAGIMLI kontrol: binary varsa NORMAL kontrol (kirmizi yanabilir),
    yoksa GORUNUR ⚪ OLCULEMEDI (deploy BLOKLANMAZ). Bkz. modul basligi K4."""
    PS_BAGIMLI[0] += 1
    if PS_VAR[0]:
        return kontrol(ad, ok, ayrinti)
    return olculemedi(ad, "`ps` binary'si yok — surec kimligi olculemez")


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
    PS_VAR[0] = ps_kullanilabilir()
    if not PS_VAR[0]:
        print("⚪ NOT: `ps` binary'si YOK -> surec kimligi kontrolleri OLCULEMEDI "
              "olarak isaretlenecek (deploy BLOKLANMAZ; bkz. modul basligi K4).")
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

        # (b2b) ATLAMA KAYDI AYRI DOSYADAN da okunmali (yeni surum yazicisi orayi kullanir)
        b2b = damga_kur(os.path.join(td, "b2b"), 600, baslangic=simdi - 660)
        with open(os.path.join(b2b, ".son-yedek-atlama.json"), "w") as fh:
            json.dump({"son_atlama": simdi - 300, "son_atlama_iso": "AYRI-DOSYA",
                       "son_atlama_sebep": "baska yedek kosuyordu",
                       "son_atlama_kapsandi": True,
                       "son_atlama_sahip_baslangici": simdi - 400}, fh)
        sat_b2b = durum.yedek_satirlari(durum.yedek_durumu(b2b, "var"))
        kontrol("(b2b) ayri dosyadaki atlama kaydi PANOYA giriyor",
                "ATLANDI" in sat_b2b[0] and "AYRI-DOSYA" in sat_b2b[0], sat_b2b[0][:90])
        # ayni dizinde damga-ici ESKI kopya varsa AYRI DOSYA kazanir (daha yeni yazici)
        b2c = damga_kur(os.path.join(td, "b2c"), 600, baslangic=simdi - 660,
                        son_atlama=simdi - 300, son_atlama_iso="DAMGA-ICI",
                        son_atlama_kapsandi=False)
        with open(os.path.join(b2c, ".son-yedek-atlama.json"), "w") as fh:
            json.dump({"son_atlama": simdi - 900, "son_atlama_iso": "AYRI-DOSYA",
                       "son_atlama_kapsandi": True,
                       "son_atlama_sahip_baslangici": simdi - 1000}, fh)
        sat_b2c = durum.yedek_satirlari(durum.yedek_durumu(b2c, "var"))
        kontrol("(b2c) ayri dosya damga-ici eski kopyayi EZIYOR (uyari yok)",
                sat_b2c[0].strip().startswith("taze:"), sat_b2c[0][:90])

        # (b3) sahip alani HIC YOK (cozulemez) -> fail-closed UYAR
        b3 = damga_kur(os.path.join(td, "b3"), 600, baslangic=simdi - 660,
                       son_atlama=simdi - 300, son_atlama_kapsandi=True)
        kontrol("(b3) sahip alani yoksa fail-closed UYARIYOR",
                "ATLANDI" in durum.yedek_satirlari(durum.yedek_durumu(b3, "var"))[0])

        # (b2d) 🔴 K2: DAMGADAN MIRAS `son_atlama*` FAIL-CLOSED'I SUSTURMAMALI.
        # Fikstur: ayri dosya (yeni yazici) sahibi TANIMLAYAMADI (alan YOK) -> uyari
        # SART. Damgada ise MIRAS kalmis bir `son_atlama_sahip_baslangici` var ve o
        # alan tek basina "sahip bitirdi" hukmu verip uyariyi SUSTURUR. Anahtar-anahtar
        # `update` mirasi birakiyordu; REPLACE semantigi ayri dosya varken damgadan
        # gelen TUM `son_atlama*` alanlarini DUSURUR.
        b2d = damga_kur(os.path.join(td, "b2d"), 600, baslangic=simdi - 660,
                        son_atlama=simdi - 3000, son_atlama_iso="DAMGA-ICI-MIRAS",
                        son_atlama_kapsandi=True,
                        son_atlama_sahip_baslangici=simdi - 5000)   # MIRAS susturucu
        with open(os.path.join(b2d, ".son-yedek-atlama.json"), "w") as fh:
            json.dump({"son_atlama": simdi - 300, "son_atlama_iso": "AYRI-DOSYA",
                       "son_atlama_sebep": "baska yedek kosuyordu",
                       "son_atlama_kapsandi": True}, fh)     # sahip alani BILEREK YOK
        d_b2d = durum.yedek_durumu(b2d, "var")
        sat_b2d = durum.yedek_satirlari(d_b2d)
        kontrol("(b2d) K2: miras `son_atlama_sahip_baslangici` DUSURULDU (replace)",
                "son_atlama_sahip_baslangici" not in (d_b2d["damga"] or {}),
                str(sorted(k for k in (d_b2d["damga"] or {}) if k.startswith("son_atlama"))))
        kontrol("(b2d) K2: miras alan fail-closed uyarisini SUSTURMUYOR",
                not sat_b2d[0].strip().startswith("taze:") and "ATLANDI" in sat_b2d[0],
                sat_b2d[0][:90])
        kontrol("(b2d) uyari AYRI DOSYADAKI kaydi anlatiyor (damga-ici degil)",
                "AYRI-DOSYA" in sat_b2d[0] and "DAMGA-ICI-MIRAS" not in sat_b2d[0],
                sat_b2d[0][:90])
        # KIRMIZI-MUTASYON: `update` semantigine donunce miras alan geri gelir ve susturur
        mut_k2 = mutant_yaz(td,
                            "            damga = {k: v for k, v in damga.items() "
                            'if not k.startswith("son_atlama")}',
                            "            damga = dict(damga)  # MUTANT: update semantigi",
                            ad="durum_mutant_miras.py")
        mmod_k2 = modul_yukle(mut_k2, "durum_mutant_miras")
        m_k2 = mmod_k2.yedek_satirlari(mmod_k2.yedek_durumu(b2d, "var"))
        kontrol("MUTANTTA (update) miras alan panoyu SUSTURUYOR (kontrol KIRMIZI yanardi)",
                m_k2[0].strip().startswith("taze:"), m_k2[0][:90])

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
        # BAGIMLILIK NOBETCISI (K4, 27 Tem): surec kimligi `ps` (procps) ile olculur.
        # `ps` VARSA bu kontrol GERCEKTEN olcer (mutasyonla kirmizi yanar); `ps` YOKSA
        # ⚪ OLCULEMEDI olur ve TUM SITE YAYINI durmaz. Sessiz atlama YOK: ozet sayar.
        ps_kontrol("ps ile surec bilgisi okunabiliyor (kimlik dogrulamasinin on kosulu)",
                   durum._surec_bilgisi(os.getpid())[0] is not None,
                   str(durum._surec_bilgisi(os.getpid())))
        # `bitti=` isaretli iz: kosum DUZGUN bitti, kimse tutmuyor -> SESSIZ
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST bitti=%r\n"
                     % (os.getpid(), simdi - 5, simdi - 4))
        d_bitti = durum.kilit_durumu(kok)
        kontrol("'bitti=' isaretli iz -> hal 'yok', satir YOK (temiz birakma)",
                d_bitti["hal"] == "yok" and durum.kilit_satirlari(d_bitti) == [],
                d_bitti["hal"])
        # canli sahip, yas kucuk -> NORMAL: pano susar (gurultu yapmaz)
        with open(yol, "w") as fh:
            fh.write("pid=%d baslangic=%r iso=TEST\n" % (os.getpid(), simdi))
        d_norm = durum.kilit_durumu(kok)
        kontrol("canli + yeni kilit -> 'tutuluyor', satir YOK",
                d_norm["hal"] == "tutuluyor" and durum.kilit_satirlari(d_norm) == [],
                d_norm["hal"])
        # 2 saattir tutan GERCEKTEN canli sahip -> UYARI
        # (yas simule edilir; surec kimligi DAIMA gercek saatle olculur)
        cocuk = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            with open(yol, "w") as fh:
                fh.write("pid=%d baslangic=%r iso=TEST\n" % (cocuk.pid, time.time()))
            d_asili = durum.kilit_durumu(kok, simdi=time.time() + 7200)
            sat_asili = durum.kilit_satirlari(d_asili)
            print("     --- pano ciktisi (kilit 2 saattir asili) ---")
            for s in sat_asili:
                print("    " + s)
            kontrol("2 saatlik CANLI python sahibi -> hal 'asili'",
                    d_asili["hal"] == "asili", d_asili["hal"])
            kontrol("pano SURESINI ve pid'i SOYLUYOR",
                    "2.0 saattir" in sat_asili[0] and str(cocuk.pid) in sat_asili[0])
            kontrol("pano 'yedekler ATLANIYOR' diyor", "ATLANIYOR" in sat_asili[0])
            kontrol("pano kilidi KIRMA talimati vermiyor, elle kontrol diyor",
                    "KIRILMAZ" in sat_asili[1])
            # ESIK SABITI OLU MU: ayni canli sahip, yas 60 sn -> varsayilan esikte
            # 'tutuluyor', esik 10 sn'ye cekilince 'asili' olmali.
            ileri = time.time() + 60
            kontrol("60 sn'lik kilit varsayilan esikte 'tutuluyor'",
                    durum.kilit_durumu(kok, simdi=ileri)["hal"] == "tutuluyor")
            kontrol("esik 10 sn'ye cekilince ayni kilit 'asili' oluyor",
                    durum.kilit_durumu(kok, simdi=ileri, esik=10)["hal"] == "asili")
        finally:
            cocuk.kill()
            cocuk.wait()
        kontrol("sahip surec olunce ayni iz 'yarim' oluyor",
                durum.kilit_durumu(kok)["hal"] == "yarim")
        # OLU sahip: yarim kalmis kosum izi
        with open(yol, "w") as fh:
            fh.write("pid=999999 baslangic=%r iso=TEST\n" % (simdi - 60))
        d_yarim = durum.kilit_durumu(kok)
        kontrol("olu pid -> hal 'yarim' (kosum ortasinda kesilmis)",
                d_yarim["hal"] == "yarim" and d_yarim["canli"] is False, d_yarim["hal"])
        kontrol("yarim kilit panoda UYARIYOR",
                "YARIM KALMIS" in durum.kilit_satirlari(d_yarim)[0])

        # 🔴 PID YENIDEN KULLANIMI (C) — pid CANLI ama bu kilidin sahibi DEGIL
        # (surec, imzadan SONRA basladi). Pano yanlis SUSMAMALI ve alakasiz sureci
        # "sonlandir" diye GOSTERMEMELI.
        with open(yol, "w") as fh:                       # kendi pid'imiz: python, ama
            fh.write("pid=%d baslangic=%r iso=TEST\n"    # kilit 2 saat once alinmis
                     % (os.getpid(), simdi - 7200))      # -> surec kilitten SONRA basladi
        d_geri = durum.kilit_durumu(kok)
        sat_geri = durum.kilit_satirlari(d_geri)
        ps_kontrol("yeniden kullanilan pid -> 'tutuluyor' DEGIL 'yarim'",
                   d_geri["hal"] == "yarim" and d_geri["canli"] is False, d_geri["hal"])
        ps_kontrol("yeniden kullanilan pid'de 'sonlandir' onerisi YOK",
                   not any("sonlandir" in s for s in sat_geri), " | ".join(sat_geri)[:90])
        # launchd (pid 1): canli ama python DEGIL -> sahip olamaz
        with open(yol, "w") as fh:
            fh.write("pid=1 baslangic=%r iso=TEST\n" % (simdi - 7200))
        d_launchd = durum.kilit_durumu(kok)
        ps_kontrol("pid=1 (launchd) sahip SAYILMIYOR -> 'yarim'",
                   d_launchd["hal"] == "yarim", d_launchd["hal"])
        ps_kontrol("pid=1 icin 'sonlandir' onerisi YOK",
                   not any("sonlandir" in s for s in durum.kilit_satirlari(d_launchd)))
        # KIRMIZI-MUTASYON: kimlik dogrulamasi kaldirilirsa ikisi de yanlis siniflanir
        mut_pid = mutant_yaz(td,
                             '    if komut and "python" not in os.path.basename(komut).lower():\n'
                             "        return False                      "
                             "# baska bir program bu pid'i almis",
                             "    if False:\n        return False  # MUTANT: kimlik yok",
                             ad="durum_mutant_pid.py")
        mmod_pid = modul_yukle(mut_pid, "durum_mutant_pid")
        kontrol("MUTANTTA (kimlik yok) launchd 'asili' gorunuyor (kontrol KIRMIZI yanardi)",
                mmod_pid.kilit_durumu(kok)["hal"] == "asili",
                mmod_pid.kilit_durumu(kok)["hal"])

        # 🔴 K4 SESSIZ-YESIL NOBETCISI: `ps` VARKEN, _surec_bilgisi'ni olduren bir
        # mutasyon "OLCULEMEDI" kilifina KACAMAZ — kimlik kontrolleri KIRMIZI yanar.
        # (Kapi ortama bakiyor, olculen kodun kendi fonksiyonuna DEGIL; bu kontrol
        # o tercihin kanitidir. Mutant `ps`i degil KODU bozar.)
        mut_ps = mutant_yaz(td,
                            "    satir = (p.stdout or \"\").strip()",
                            "    satir = \"\"  # MUTANT: ps ciktisi yok sayiliyor",
                            ad="durum_mutant_ps.py")
        mmod_ps = modul_yukle(mut_ps, "durum_mutant_ps")
        with open(yol, "w") as fh:                       # pid=1: canli ama python DEGIL
            fh.write("pid=1 baslangic=%r iso=TEST\n" % (simdi - 7200))
        ps_kontrol("ps VAR: _surec_bilgisi'ni olduren mutant kimligi KAYBEDIYOR "
                   "(OLCULEMEDI'ye kacamaz)",
                   mmod_ps._surec_bilgisi(os.getpid())[0] is None
                   and mmod_ps.kilit_durumu(kok)["hal"] != "yarim",
                   "mutant hal=%s" % mmod_ps.kilit_durumu(kok)["hal"])
        with open(yol, "w") as fh:                       # 6h'nin bozuk-imza adimina hazirla
            fh.write("pid=1 baslangic=%r iso=TEST\n" % (simdi - 7200))
        # bozuk imza
        with open(yol, "w") as fh:
            fh.write("bozuk satir\n")
        kontrol("bozuk imza -> 'okunamadi', pano yine konusuyor",
                durum.kilit_durumu(kok)["hal"] == "okunamadi"
                and "COZULEMEDI" in durum.kilit_satirlari(durum.kilit_durumu(kok))[0])
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

    # ---------------- 6i) K3: "DEGISIKLIK YOK" != "YEDEK BAYAT" ----------------
    # `--gerekliyse` GUNCEL yolu hicbir sey kopyalamaz -> `zaman` ilerlemez. Degismeyen
    # bir sistemde pano 2 gun sonra BOSUNA "⚠⚠ YEDEK BAYAT" diyordu (gurultulu pano =
    # olu pano). Artik ayrim OLCUMLE yapilir: damgadaki `dogrulandi` + `dogrulama_imzasi`
    # ile kopyanin `kaynak_imzasi` KARSILASTIRILIR. Pano iddiaya GUVENMEZ, DOGRULAR.
    print("\n6i) K3 — dogrulanmis 'degisiklik yok' GUNCEL, dogrulanamayan OLCULEMEDI")
    with tempfile.TemporaryDirectory() as td:
        simdi = time.time()
        imza = {"adet": 133, "bayt": 5771055, "mtime": simdi - 90000}

        # (a) esik asildi AMA taze + ESLESEN dogrulama var -> ✅ GUNCEL
        a = damga_kur(os.path.join(td, "a"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza))
        d_a = durum.yedek_durumu(a, "var")
        sat_a = durum.yedek_satirlari(d_a)
        print("     --- pano ciktisi (K3 a: dogrulanmis guncel) ---")
        for s in sat_a:
            print("    " + s)
        kontrol("(a) hal 'guncel'", d_a["hal"] == "guncel", d_a["hal"])
        kontrol("(a) ILK SATIR '✅ GÜNCEL' + son gercek yedegi SOYLUYOR",
                "GÜNCEL" in sat_a[0] and "son gercek yedek" in sat_a[0], sat_a[0][:90])
        kontrol("(a) BAYAT uyarisi YOK (bosuna uyarmiyor)",
                not any("BAYAT" in s for s in sat_a))
        kontrol("(a) 'taze:' de DEMIYOR (durum ayri: kopyalama gerekmedi)",
                not sat_a[0].strip().startswith("taze:"), sat_a[0][:60])

        # (b) dogrulama VAR ama imzalar FARKLI (kaynak degismis) -> ⚪ OLCULEMEDI
        farkli = dict(imza)
        farkli["bayt"] = imza["bayt"] + 1
        b = damga_kur(os.path.join(td, "b"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=farkli)
        d_b = durum.yedek_durumu(b, "var")
        sat_b = durum.yedek_satirlari(d_b)
        kontrol("(b) imzalar farkli -> hal 'dogrulama-olculemedi'",
                d_b["hal"] == "dogrulama-olculemedi", d_b["hal"])
        kontrol("(b) ÖLÇÜLEMEDİ diyor, GUNCEL/taze DEMIYOR",
                "ÖLÇÜLEMEDİ" in sat_b[0] and "GÜNCEL" not in sat_b[0]
                and not sat_b[0].strip().startswith("taze:"), sat_b[0][:90])
        kontrol("(b) ne yapilacagini SOYLUYOR", "tools/yedekle.py" in " ".join(sat_b))

        # (c) dogrulamanin KENDISI bayat (3 gun once dogrulanmis) -> ⚠⚠ BAYAT
        c = damga_kur(os.path.join(td, "c"), 3 * 86400, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 3 * 86400, dogrulama_imzasi=dict(imza))
        kontrol("(c) bayat dogrulama GUNCEL SAYILMIYOR -> 'bayat'",
                durum.yedek_durumu(c, "var")["hal"] == "bayat",
                durum.yedek_durumu(c, "var")["hal"])

        # (d) dogrulama HIC YOK -> BAYAT (regresyon nobeti: eski davranis korunuyor)
        d_yok = damga_kur(os.path.join(td, "d"), 3 * 86400)
        kontrol("(d) dogrulama yoksa yine 'bayat' (BAYAT hali OLU DEGIL)",
                durum.yedek_durumu(d_yok, "var")["hal"] == "bayat")

        # (e) `dogrulandi` var ama imza alanlari EKSIK -> OLCULEMEDI (sessiz yesil YOK)
        e = damga_kur(os.path.join(td, "e"), 3 * 86400, dogrulandi=simdi - 300)
        kontrol("(e) imza eksikken GUNCEL DEMIYOR -> 'dogrulama-olculemedi'",
                durum.yedek_durumu(e, "var")["hal"] == "dogrulama-olculemedi",
                durum.yedek_durumu(e, "var")["hal"])
        # (e2) imza alanlari SAYI DEGIL (bozuk yazim) -> yine OLCULEMEDI
        e2 = damga_kur(os.path.join(td, "e2"), 3 * 86400,
                       kaynak_imzasi={"adet": "133", "bayt": None, "mtime": True},
                       dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza))
        kontrol("(e2) bozuk imza turleri fail-closed (GUNCEL DEMIYOR)",
                durum.yedek_durumu(e2, "var")["hal"] == "dogrulama-olculemedi",
                durum.yedek_durumu(e2, "var")["hal"])
        # (e3) `dogrulandi` GELECEK tarihli -> yesil verilmez
        e3 = damga_kur(os.path.join(td, "e3"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi + 3600, dogrulama_imzasi=dict(imza))
        kontrol("(e3) gelecek tarihli dogrulama GUNCEL SAYILMIYOR",
                durum.yedek_durumu(e3, "var")["hal"] == "bayat",
                durum.yedek_durumu(e3, "var")["hal"])
        # (e4) 🔴 KARISIK SURUM DELIGI: damgaya EN SON dokunan kosum dogrulamayi
        # YAZMAMISSA yesil verilmez. Fikstur, BAYAT bir kardes worktree'nin ESKI
        # yedekle.py surumuyle kosmasinin BIREBIR izidir: `baslangic` ilerlemis
        # (o kosum damgaya dokundu) ama `dogrulandi` GERIDE kalmis (imza eksenini
        # bilmedigi icin dogrulama yazmadi, eski cifti dict(onceki) ile TASIDI).
        # Olculdu (scratchpad/karisik-surum.py): sart olmadan pano "✅ GUNCEL" diyordu
        # ve mtime KORUNARAK degismis dosya yedekte YOKTU.
        e4 = damga_kur(os.path.join(td, "e4"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi - 3600, dogrulama_imzasi=dict(imza),
                       baslangic=simdi - 300)          # damgaya SONRADAN dokunuldu
        d_e4 = durum.yedek_durumu(e4, "var")
        sat_e4 = durum.yedek_satirlari(d_e4)
        kontrol("(e4) dogrulamadan SONRA damgaya dokunulmussa GUNCEL DEMIYOR",
                d_e4["hal"] == "bayat" and "GÜNCEL" not in sat_e4[0],
                "%s | %s" % (d_e4["hal"], sat_e4[0][:60]))
        # ayni fikstur, `dogrulandi` == `baslangic` (YENI surumun uretecegi hal) -> GUNCEL
        e5 = damga_kur(os.path.join(td, "e5"), 3 * 86400, kaynak_imzasi=dict(imza),
                       dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza),
                       baslangic=simdi - 300)
        kontrol("(e5) dogrulandi == baslangic ise GUNCEL (kontrol asiri-daralmadi)",
                durum.yedek_durumu(e5, "var")["hal"] == "guncel",
                durum.yedek_durumu(e5, "var")["hal"])
        # KIRMIZI-MUTASYON: sart kaldirilirsa (e4) sessizce GUNCEL olur
        mut_e4 = mutant_yaz(td,
                            "    if isinstance(ref, (int, float)) and not "
                            "isinstance(ref, bool) and dogrulandi < ref:\n"
                            "        return None                                   "
                            "# damgaya sonradan BASKASI dokundu",
                            "    if False:\n        return None  # MUTANT: sart yok",
                            ad="durum_mutant_karisik.py")
        mmod_e4 = modul_yukle(mut_e4, "durum_mutant_karisik")
        kontrol("MUTANTTA (karisik surum sarti yok) (e4) GUNCEL gorunuyor "
                "(kontrol KIRMIZI yanardi)",
                mmod_e4.yedek_durumu(e4, "var")["hal"] == "guncel",
                mmod_e4.yedek_durumu(e4, "var")["hal"])

        # (f) esik altinda dogrulama VARSA yine 'taze' (yeni hal eskiyi EZMESIN)
        f = damga_kur(os.path.join(td, "f"), 3600, kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 60, dogrulama_imzasi=dict(imza))
        kontrol("(f) esik ALTINDA hal yine 'taze' (regresyon)",
                durum.yedek_durumu(f, "var")["hal"] == "taze",
                durum.yedek_durumu(f, "var")["hal"])
        # (g) KISMI yedek dogrulanmis olsa BILE basligi kismi uyarisi ALIR
        g = damga_kur(os.path.join(td, "g"), 3 * 86400, tam=False,
                      eksik=["DEVAM-ARSIV.md"], kaynak_imzasi=dict(imza),
                      dogrulandi=simdi - 300, dogrulama_imzasi=dict(imza))
        sat_g = durum.yedek_satirlari(durum.yedek_durumu(g, "var"))
        kontrol("(g) kismi yedek 'GUNCEL' basligina KACMIYOR",
                "KISMI YEDEK" in sat_g[0] and "GÜNCEL" not in sat_g[0], sat_g[0][:90])

        # KIRMIZI-MUTASYON 1: pano imzayi DOGRULAMAYI birakirsa (b) sessizce GUNCEL olur
        mut_g1 = mutant_yaz(td,
                            '    if not _imza_kullanilir(imza) or not _imza_kullanilir(kopya):\n'
                            '        return "olculemedi"',
                            '    if False:\n        return "olculemedi"\n'
                            '    return "guncel"  # MUTANT: iddiaya GUVENIYOR',
                            ad="durum_mutant_dogrulama.py")
        mmod_g1 = modul_yukle(mut_g1, "durum_mutant_dogrulama")
        kontrol("MUTANTTA (iddiaya guven) degismis kaynak GUNCEL gorunuyor "
                "(kontrol KIRMIZI yanardi)",
                mmod_g1.yedek_durumu(b, "var")["hal"] == "guncel",
                mmod_g1.yedek_durumu(b, "var")["hal"])
        # KIRMIZI-MUTASYON 2: 'guncel' hali oldurulurse (a) bosuna BAYAT der
        #   (POZITIF nobetci: yeni hal GERCEKTEN erisilebilir olmali)
        mut_g2 = mutant_yaz(td,
                            '    hal = _dogrulama_hali(damga, simdi, esik)',
                            '    hal = None  # MUTANT: dogrulama gorulmuyor\n'
                            '    _ = _dogrulama_hali',
                            ad="durum_mutant_guncelsiz.py")
        mmod_g2 = modul_yukle(mut_g2, "durum_mutant_guncelsiz")
        kontrol("MUTANTTA (dogrulama korlestirilmis) (a) BOSUNA 'bayat' diyor "
                "(kontrol KIRMIZI yanardi)",
                mmod_g2.yedek_durumu(a, "var")["hal"] == "bayat",
                mmod_g2.yedek_durumu(a, "var")["hal"])

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

    # ---------------- 9) K4: `ps` YOKKEN KAPI YAYINI DURDURMAZ ----------------
    # Kendini `ps`siz bir PATH ile YENIDEN cagirir (gercek ortam yoklugu taklidi).
    # Iddia: cikis 0 + ps'e bagli kontrollerin HEPSI ⚪ OLCULEMEDI olarak GORUNUR.
    # Sayi SABIT YAZILMAZ: alt kosumun kendi ilan ettigi "PS BAGIMLI" sayisiyla
    # OLCULEMEDI sayisi karsilastirilir (veri capasi bayatlamasin).
    if ALT_KOSUM not in sys.argv:
        print("\n9) K4 — `ps` YOKKEN: exit 0 + gorunur ⚪ OLCULEMEDI (yayin durmaz)")
        with tempfile.TemporaryDirectory() as td:
            kutu = os.path.join(td, "bin")
            os.makedirs(kutu)
            git_yolu = shutil.which("git")            # git gerekli (durum.py + fikstur)
            if git_yolu:
                os.symlink(git_yolu, os.path.join(kutu, "git"))
            ortam = dict(os.environ)
            ortam["PATH"] = kutu                      # `ps` PATH'te YOK
            r_ps = subprocess.run([sys.executable, os.path.abspath(__file__), ALT_KOSUM],
                                  capture_output=True, text=True, env=ortam)
            cik = r_ps.stdout

            def _sayi(onek):
                for s in cik.splitlines():
                    if s.startswith(onek):
                        try:
                            return int(s[len(onek):].split()[0])
                        except (ValueError, IndexError):
                            return None
                return None

            kontrol("ps YOKKEN alt kosum exit 0 (TUM SITE YAYINI durmaz)",
                    r_ps.returncode == 0,
                    "rc=%d %s" % (r_ps.returncode, r_ps.stderr.strip()[:100]))
            kontrol("ps YOKKEN alt kosum `ps`i GERCEKTEN bulamadi (fikstur ISIRIYOR)",
                    "PS: YOK" in cik,
                    " ".join(s for s in cik.splitlines() if s.startswith("PS:")))
            kontrol("ps YOKKEN cikti ⚪ ÖLÇÜLEMEDİ basiyor (sessiz yesil DEGIL)",
                    "⚪ ÖLÇÜLEMEDİ" in cik)
            kontrol("ps YOKKEN ozet OLCULEMEDI SAYISINI yaziyor (CI log'unda goze batar)",
                    _sayi("OLCULEMEDI: ") is not None, str(_sayi("OLCULEMEDI: ")))
            kontrol("ps YOKKEN olculemeyen sayisi = ilan edilen ps-bagimli sayisi",
                    _sayi("OLCULEMEDI: ") == _sayi("PS BAGIMLI: ")
                    and (_sayi("PS BAGIMLI: ") or 0) > 0,
                    "olculemedi=%s / ps-bagimli=%s"
                    % (_sayi("OLCULEMEDI: "), _sayi("PS BAGIMLI: ")))
            kontrol("ps YOKKEN kapinin GERI KALANI hala BLOKLAYICI (kirmizi 0 + coklu yesil)",
                    _sayi("KIRMIZI: ") == 0 and (_sayi("GECTI: ") or 0) > 50,
                    "gecti=%s kirmizi=%s" % (_sayi("GECTI: "), _sayi("KIRMIZI: ")))
            kontrol("ps VARKEN bu makinede OLCULEMEDI 0 (kapi burada TAM olcuyor)",
                    PS_VAR[0] and not OLCULEMEDI,
                    "ps=%s olculemedi=%d" % (PS_VAR[0], len(OLCULEMEDI)))

    # ---------------- OZET ----------------
    kirmizi = [a for a, ok in SONUC if not ok]
    print("\n" + "=" * 70)
    # Makine-okunur ozet (alt kosum bunlari ayristirir; sabit sayi YOK).
    print("PS: " + ("VAR" if PS_VAR[0] else "YOK"))
    print("PS BAGIMLI: %d" % PS_BAGIMLI[0])
    print("GECTI: %d" % (len(SONUC) - len(kirmizi)))
    print("KIRMIZI: %d" % len(kirmizi))
    print("OLCULEMEDI: %d" % len(OLCULEMEDI))
    print("TOPLAM %d kontrol, %d kirmizi, %d ⚪ ÖLÇÜLEMEDİ"
          % (len(SONUC), len(kirmizi), len(OLCULEMEDI)))
    for a in kirmizi:
        print("  ❌ " + a)
    for a, ayrinti in OLCULEMEDI:
        print("  ⚪ ÖLÇÜLEMEDİ: %s  (%s)" % (a, ayrinti))
    if OLCULEMEDI:
        print("NOT: ⚪ OLCULEMEDI cikis kodunu BOZMAZ (ortam eksikligi yayini durdurmaz) "
              "ama GORUNURDUR — bkz. modul basligi K4.")
    print("SONUC: " + ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
