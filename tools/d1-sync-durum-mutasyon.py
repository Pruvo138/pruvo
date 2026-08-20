#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — TURETILMIS KOLON EKSENI (4. eksen) GERCEK ihlali yakiyor mu?

  Kapi: tools/d1-sync-durum-test.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu repoda durur; kabul CIKIS KODU degil
OLCULEN IDDIA SAYISI + ISARET SARTIDIR (cokme kirmiziyla karisir).

NEYI OLCER: 6 Agu'da olculen sessiz hata sinifini. `marka_arama` (ve kardesleri) urun_hash'in
KAPSAMI DISINDADIR; hedefli UPDATE ile senkronlanirlar. --durum'un uc ekseni de (SAYI/SEMA/
ICERIK) bu kolonlara KOR oldugu icin canli kolon BAYAT iken (Honda 1898, olmasi gereken 1979)
UCU DE YESIL yaniyordu. Asagidaki OLDURUCU mutantlarin her biri o korlugu GERI GETIRIR:
  * ekseni sessizlestiren mutantlar (M1, M4, M6, M11, M12) — eksen fiilen bagli mi
  * fail-closed'i acan mutantlar (M2, M3, M5, M9, M10) — "bilmiyorum" YESIL sayilir mi
  * uretici govdeyi bozan mutantlar (M7, M8) — kolonun degeri HAM `marka[]`e cokerse
KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali; yoksa kapi "her degisiklige
kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

CAPA DISIPLINI: her mutant capasinin kaynak dosyada TAM BIR KEZ gecmesi SART. Gecmezse
sonuc "YESIL" degil "CAPA-YOK"tur (mutant uygulanamadan yesil sayilmasi bataryayi kor eder).

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi
O AYNADAN kosulur. CANLI D1'e / aga DOKUNULMAZ (kapi tamamen offline).

Calistir:  python3 tools/d1-sync-durum-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "d1-sync-durum-test.py"
# K237 §4 (20 Agu) — IKINCI KAPI. `sayac_onar()` YAZMA yolundadir; `--durum` kapisi o govdeyi
# HIC calistirmaz, dolayisiyla onun mutantlari bu kapiya baglanirsa TAUTOLOJIK "YESIL" verir
# ([[ad-iki-rolde-mutanti-golgeler]]: mutantin YASAMASI "kol saglam" degil "kol OLCULEMEDI"
# demektir). Bu yuzden kapiyi MUTANT secer: onarim kolunun mutantlari d1-sync'in kendi
# `--kendini-test` bataryasina (deploy.yml CI adimi) baglanir.
KAPI_KENDINI = ("d1-sync.py", "--kendini-test")
VARSAYILAN_KAPI = (KAPI_ADI,)

# Bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir. Saglam kosum 45 GECTI basar;
# en cok iddia dusuren OLDURUCU bile 25'in ustunde kalir. Esik, kapinin erken cikip
# birkac kontrol basarak "kirmizi" gorunmesini AYIRT ETMEK icindir.
TABAN_GECTI = 25

# (ad, dosya [TOOLS'a gore], eski, yeni, beklenen)
MUTANTLAR = [
    # ── OLDURUCU: ekseni SESSIZLESTIREN mutantlar ───────────────────────────────
    ("OLDURUCU M1 BAYAT/OLCULEMEDI sorun satirini URETME (eksen basar, sesi cikmaz)",
     "d1-sync.py",
     "    satirlar = []\n"
     "    for h in hal:\n"
     "        if h[\"hal\"] == TK_BAYAT:",
     "    satirlar = []\n"
     "    for h in []:\n"
     "        if h[\"hal\"] == TK_BAYAT:", "KIRMIZI"),
    ("OLDURUCU M2 FAIL-CLOSED'I AC — OLCULEMEDI sorun sayilmasin (yesile yazilir)",
     "d1-sync.py",
     "        elif h[\"hal\"] == TK_OLCULEMEDI:",
     "        elif False:", "KIRMIZI"),
    ("OLDURUCU M3 URETEMEYEN GOVDEYI SESSIZCE YESIL SAY (bugunku sessiz hatanin ta kendisi)",
     "d1-sync.py",
     "            _olculemedi(\"URETICI GOVDE hedef uretemedi: %s\" % (sebep or \"harita None\"))\n"
     "            continue",
     "            out.append({\"kolon\": kolon, \"hal\": TK_GUNCEL, \"sayi\": 0,\n"
     "                        \"sebep\": None, \"coz\": coz, \"ornek\": []})\n"
     "            continue", "KIRMIZI"),
    ("OLDURUCU M4 CIKIS KODUNU KOPAR — eksen BASAR ama `sorunlar`a girmez",
     "d1-sync.py",
     "                sorunlar.append(\n"
     "                    \"TURETILMIS KOLON EKSENI: %d kolon BAYAT/OLCULEMEDI (ayrinti yukarida) \"\n"
     "                    \"— SAYI, SEMA ve ICERIK eksenlerinin UCU DE bu hale KORDUR.\"\n"
     "                    % len(turetilmis_sorun))",
     "                pass", "KIRMIZI"),
    ("OLDURUCU M5 KOLON CANLIDA YOKKEN GUNCEL DE (sema kosmadan yesil)",
     "d1-sync.py",
     "            _olculemedi(\"kolon CANLI tabloda YOK (--sema kosmadi)\")",
     "            out.append({\"kolon\": kolon, \"hal\": TK_GUNCEL, \"sayi\": 0,\n"
     "                        \"sebep\": None, \"coz\": coz, \"ornek\": []})", "KIRMIZI"),
    ("OLDURUCU M6 KAPSAM ACIGINI KORLESTIR (yeni kolon sessizce siniflandirilmamis kalir)",
     "d1-sync.py",
     "    kapsanan = HASH_KAPSAMI | {k[\"kolon\"] for k in kayit} | set(EKSEN_DISI)\n"
     "    return sorted(k for k in tablo_kolonlari if k not in kapsanan)",
     "    return []", "KIRMIZI"),
    ("OLDURUCU M11 PLAN'I NO-OP YAP — fark ARANMAZ, kolon DAIMA GUNCEL gorunur",
     "d1-sync.py",
     "            plan = k[\"plan\"](urunler, hedefler, mevcutlar[kolon], izleme)",
     "            plan = []", "KIRMIZI"),
    ("OLDURUCU M12 EKSENI HER KOSUMDA ATLA (--hizli bayragi her zaman aciksin)",
     "d1-sync.py",
     "        if a.hizli:\n"
     "            print(\"!! TURETILMIS KOLON EKSENI ATLANDI (--hizli): konfigur/taban_fiyat/\"",
     "        if True:\n"
     "            print(\"!! TURETILMIS KOLON EKSENI ATLANDI (--hizli): konfigur/taban_fiyat/\"",
     "KIRMIZI"),
    # ── OLDURUCU: fail-closed / kapsam BEYANI ───────────────────────────────────
    ("OLDURUCU M9 TABAN SEMASI OKUNAMAYINCA SESSIZ YESIL (bos harita = 'dokunma')",
     "d1-sync.py",
     "    if not harita:\n"
     "        return None, (\"jenerator/urunler semasi BOS/okunamadi (%s) — taban fiyat hedefi \"\n"
     "                      \"URETILEMEDI\" % JEN_URUN_DIR)\n"
     "    return harita, None",
     "    return harita, None", "KIRMIZI"),
    ("OLDURUCU M10 CANLI DEGERI HIC OKUMA (her kolon OLCULEMEDI'ye duser, teyit anlamsizlasir)",
     "d1-sync.py",
     "    kolonlar = [k[\"kolon\"] for k in kayit if k[\"kolon\"] in tablo_kolonlari]\n"
     "    if not kolonlar:\n"
     "        return {}",
     "    kolonlar = [k[\"kolon\"] for k in kayit if k[\"kolon\"] in tablo_kolonlari]\n"
     "    if True:\n"
     "        return {}", "KIRMIZI"),
    ("OLDURUCU M7 KAPSAM BEYANINI YALANLA — marka_arama'yi hash kapsaminda GOSTER",
     "d1-sync.py",
     "HASH_KAPSAMI = frozenset(KOLONLAR) | {\"id\"}",
     "HASH_KAPSAMI = frozenset(KOLONLAR) | {\"id\", \"marka_arama\"}", "KIRMIZI"),
    # ── OLDURUCU: URETICI GOVDE (kolonun DEGERI) ────────────────────────────────
    # Mimar hukmu: "kolonu ham `marka[]`dan yeniden hesaplayan mutant KIRMIZI olmali".
    # OLCULDU (20.850 urunluk canli katalog): ham `marka[]` capalarin YARISINI tutar —
    # Honda 1979 = 1979 (tutar) ama Grom 15 ≠ 44 ve Vauxhall 71 ≠ 493. Yani "ham esitlik
    # yeterli" sanisi capa secimine gore SESSIZCE gecerdi.
    ("OLDURUCU M8 KOLONU HAM `marka[]`DAN HESAPLA (uyelik + baslik kolu duser)",
     "d1-sync.py",
     "        uyeler = mmb.marka_uyelikleri(u.get(\"marka\") or [], evren, ek)\n"
     "        baslik_uyum = arama.baslik_marka_uyumlari(u.get(\"baslik\"), kanon)\n"
     "        adaylar = list(uyeler) + [m for m in baslik_uyum if m not in uyeler]",
     "        uyeler = list(u.get(\"marka\") or [])\n"
     "        baslik_uyum = []\n"
     "        adaylar = list(uyeler)", "KIRMIZI"),
    ("OLDURUCU M13 ALIAS KOLUNU DUSUR (uc `?q=Vauxhall`i cozemez; canlida 493 urun)",
     "d1-sync.py",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)",
     "        pass", "KIRMIZI"),

    # ── K237 SAYAC EKSENI (20 Agu) — `--durum` kapisina bagli OLDURUCULER ───────
    # OLCULEN OLAY: D1'de 29602 satir varken senkron.urun_sayisi 29573'te DONUK kaldi ve
    # SAYI + ICERIK eksenleri YESIL yandi (ikisi de sayacin KENDISINI kiyaslamiyordu).
    ("OLDURUCU M13 SAYAC EKSENINI SESSIZLESTIR (kiyas hep 'uyumlu' der)",
     "d1-sync.py",
     "        if sayac_uyumlu(n, urun_sayisi_kayit):",
     "        if True or sayac_uyumlu(n, urun_sayisi_kayit):", "KIRMIZI"),
    ("OLDURUCU M14 SAYAC FAIL-CLOSED'I AC (satir YOK / D1 okunamadi -> 'uyumlu' sayilir)",
     "d1-sync.py",
     "    if d1_sayisi is None or senkron_urun_sayisi is None:\n"
     "        return False",
     "    if d1_sayisi is None or senkron_urun_sayisi is None:\n"
     "        return True", "KIRMIZI"),
    ("OLDURUCU M15 SAYAC ESITLIGINI KALDIR (her deger uyumlu)",
     "d1-sync.py",
     "        return int(d1_sayisi) == int(senkron_urun_sayisi)",
     "        return True", "KIRMIZI"),

    # ── K237 SAYAC ONARIM KOLU (§3) — `--kendini-test` kapisina bagli OLDURUCULER ─
    # Bu iki mutant BILEREK ikinci kapiya baglidir: onarim YAZMA yolundadir, `--durum`
    # kapisi o govdeyi hic calistirmaz (yukaridaki KAPI_KENDINI notuna bak).
    ("OLDURUCU M16 SAYAC ONARIMINI KALDIR (bayat sayac 'degisiklik yok' kolunda KALICI olur)",
     "d1-sync.py",
     "        onarildi = sayac_onar()",
     "        onarildi = False", "KIRMIZI", KAPI_KENDINI),
    ("OLDURUCU M17 ONARIM MALIYET KOLUNU BOZ (sayac DOGRUYKEN de yazar)",
     "d1-sync.py",
     "    if sayac_uyumlu(n, mevcut):\n"
     "        return False",
     "    if False:\n"
     "        return False", "KIRMIZI", KAPI_KENDINI),

    # ── KONTROL: iddia edilmeyen eksen / davranissiz yazim / satir sirasi ───────
    ("KONTROL K1 davranissiz yazim (turetilmis_eksen: out = [] -> list())",
     "d1-sync.py",
     "    kayit = TURETILMIS_KAYIT if kayit is None else kayit\n"
     "    out = []\n"
     "    for k in kayit:",
     "    kayit = TURETILMIS_KAYIT if kayit is None else kayit\n"
     "    out = list()\n"
     "    for k in kayit:", "YESIL"),
    ("KONTROL K2 davranissiz yazim (izleme = [] -> list())",
     "d1-sync.py",
     "        izleme = []\n        try:",
     "        izleme = list()\n        try:", "YESIL"),
    ("KONTROL K3 SATIR SIRASI (kapsam_acigi cagrisi eksenden ONCE hesaplansin)",
     "d1-sync.py",
     "            thal = turetilmis_eksen(urunler, tablo_kolonlari,\n"
     "                                    turetilmis_mevcut(tablo_kolonlari))\n"
     "            acik = kapsam_acigi(tablo_kolonlari)",
     "            acik = kapsam_acigi(tablo_kolonlari)\n"
     "            thal = turetilmis_eksen(urunler, tablo_kolonlari,\n"
     "                                    turetilmis_mevcut(tablo_kolonlari))", "YESIL"),
    ("KONTROL K4 iddia edilmeyen eksen (EKSEN_DISI gerekce METNI — davranis degismez)",
     "d1-sync.py",
     "    \"rid\": \"SQLite rowid — urunler.json'dan TURETILMEZ, kiyaslanacak bir hedefi yok\",",
     "    \"rid\": \"SQLite rowid (dahili) — urunler.json'dan TURETILMEZ, hedefi yok\",",
     "YESIL"),
    ("KONTROL K5 ILGISIZ KOLON (konfigur senkronu aciklama yorumu)",
     "d1-sync.py",
     "# ─── KONFIGUR SEMASI (D1 feed'i — Worker bundle'inin ikizi) ──────────────────",
     "# ─── KONFIGUR SEMASI (D1 feed'i — Worker bundle'inin IKIZI) ──────────────────",
     "YESIL"),
    # K237 kontrolleri: SAYAC ekseninde ve onarim kolunda DAVRANISSIZ degisiklik YESIL
    # kalmali — yoksa iki yeni eksen "her degisiklige kirmizi yanan" gurultu olurdu.
    ("KONTROL K6 SAYAC EKSENI aciklama yorumu (davranis degismez)",
     "d1-sync.py",
     "        # ── SAYAC EKSENI (K237, 20 Agu) — senkron.urun_sayisi D1 COUNT(*)'una ESIT mi? ──",
     "        # ── SAYAC EKSENI (K237, 20 Agu) — senkron.urun_sayisi D1 COUNT(*)'una ESIT MI? ──",
     "YESIL"),
    ("KONTROL K7 ONARIM davranissiz yazim (if X: -> if X is True:)",
     "d1-sync.py",
     "    if sayac_uyumlu(n, mevcut):",
     "    if sayac_uyumlu(n, mevcut) is True:", "YESIL", KAPI_KENDINI),
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
    tmp = tempfile.mkdtemp(prefix="d1-sync-durum-mutasyon-")
    sonuc = []
    try:
        for mutant in MUTANTLAR:
            ad, dosya, eski, yeni, beklenen = mutant[:5]
            # 6. alan (opsiyonel) = bu mutantin KAPISI. Verilmezse varsayilan --durum kapisi.
            kapi = mutant[5] if len(mutant) > 5 else VARSAYILAN_KAPI
            kaynak_yolu = os.path.normpath(os.path.join(TOOLS, dosya))
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                # 🔴 CAPA TAM BIR KEZ ESLESMELI. Kaymissa "mutant uygulanamadi" YESIL
                # sayilmaz; kanit OLCULEMEDI'dir.
                sonuc.append((ad, kapi[0], beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(os.path.join(tmp, str(len(sonuc))))
            hedef = os.path.normpath(os.path.join(kok, "tools", dosya))
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run(
                [sys.executable, os.path.join(kok, "tools", kapi[0])] + list(kapi[1:]),
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
            sonuc.append((ad, kapi[0], beklenen,
                          "%s (KALDI=%d GECTI=%d)" % (gozlem, fail, gecti)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # KAPI HER SATIRDA BASILIR: bir mutantin hangi kapiya bagli oldugu GORUNMEZSE, yanlis
    # kapiya bagli (dolayisiyla olculemeyen) bir mutant "YESIL" diye okunur.
    print("\nMUTASYON SONUCU (kapilar: tools/%s · tools/%s %s)"
          % (KAPI_ADI, KAPI_KENDINI[0], " ".join(KAPI_KENDINI[1:])))
    kalan = 0
    for ad, kapi_adi, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-88s kapi=%-22s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, kapi_adi, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
