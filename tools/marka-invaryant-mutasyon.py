#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — marka invaryanti kapilari gercek ihlali yakiyor mu? (IKI SERIT)

  SERIT 1 (varsayilan kapi): tools/marka-invaryant-kapisi.py — OLCUM/model tarafi.
  SERIT 2 (kapi: marka-liste-test.py): index.html MARKA SORGUSU blogu — ISTEMCI tarafi.
  SERIT 3 (varsayilan kapi): DINAMIK CAPA SECIMININ KENDISI (M12-M14, K5).
Iki govde serit SART: marka sorgusu kurali IKI GOVDEDE yasar. Yalniz Python seridi mutasyona
ugratilsaydi, musterinin tarayicisindaki gerileme KANITSIZ kalirdi ([[ikiz-tanim-sessiz-ayrisma]]).
Ucuncu serit 5 Agu'da eklendi: capa artik sabit id degil, kosum aninda olculen havuzdan
DETERMINISTIK secilir; secim mekanizmasinin kendisi mutasyona ugratilmazsa "capa gecti"
diyerek iddia sessizce kaybolabilirdi.

🔴 UCUNCU BEKLENTI DEGERI — "OLCULEMEDI": fail-closed cikisin (rc=2) KANITI. Yalnizca
CIVILI SEBEP DIZGESI ciktida gorulurse kill sayilir; aksi halde COKME'dir. Boylece rastgele
bir istisna "olculemedi" damgasiyla yesile donusemez.


NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR ([[mutasyon-kaniti-yeniden-uretilebilir]]).
Kapinin en buyuk riski TOTOLOJI'dir: iki ucu da AYNI fonksiyondan turetilirse kapi her zaman
yesil yanar ve hicbir sey olcmez. Buradaki OLDURUCU mutantlar tam o hali kurar (uc modelini
sayfa yuklemine cevir, arama modelini sayfa kumesine cevir) ve kapinin KIRMIZI yanmasini
sart kosar. KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali — yoksa kapi "her
degisiklige kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi
O AYNADAN kosulur. Gercek tools/ agacina HICBIR SEY yazilmaz.

🔴 COKME KIRMIZIYLA KARISTIRILMAZ: rc 0/1 disi, "kirmizi ama olculen FAIL yok" ya da
olculen PASS sayisi tabanin altina dusmus kosum COKME sayilir — coken mutant "oldurulmus"
DEGILDIR.

Kabul: her OLDURUCU KIRMIZI + her KONTROL YESIL. Koşum ~15 sn.

Calistir:  python3 tools/marka-invaryant-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "marka-invaryant-kapisi.py"
# 🔴 IKINCI SERIT (5 Agu): marka sorgusu kurali IKI GOVDEDE yasar — Python (invaryant kapisi)
# ve index.html (musterinin tarayicisi). Yalnizca Python serididi mutasyona ugratmak,
# ISTEMCI gerilemesini KANITSIZ birakirdi; ikiz pariteyi olcen kapi tools/marka-liste-test.py
# oldugu icin index.html mutantlari O KAPIYLA kosulur.
LISTE_KAPI = "marka-liste-test.py"
# Bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir. Kapi basina olculur: saglam
# kosumda invaryant kapisi 38, marka-liste-test 59 PASS basar; en cok iddia dusuren
# OLDURUCU (M13, capa sayisini sifirlar) 28'de kaliyor. Esik, kapinin erken cikip birkac
# kontrol basarak "kirmizi" gorunmesini AYIRT ETMEK icindir.
# NOT: beklenen "OLCULEMEDI" olan mutant bu esige TABI DEGILDIR — fail-closed cikis
# TASARIM GEREGI erken doner (az PASS basar); onun kaniti CIVILI SEBEP DIZGESIDIR.
TABAN_PASS = {KAPI_ADI: 25, LISTE_KAPI: 40}

# (ad, mutasyona ugrayan dosya [ROOT'a gore], eski, yeni, beklenen[, kosulacak kapi])
MUTANTLAR = [
    ("OLDURUCU M1 KATLAMAYI KAPAT — uyelik ham degerden dogsun (Volvo Penta artik Volvo degil)",
     "marka_model_build.py",
     "        kan = evren.katla((x or \"\").strip())",
     "        kan = (x or \"\").strip()", "KIRMIZI"),
    ("OLDURUCU M2 KANONU KAPAT — uctaki ?marka= modelini ham esitlige cevir",
     KAPI_ADI,
     "        filtre = {pid for pid in uyelik if marka in uyelik[pid]}",
     "        filtre = {p[\"id\"] for p in urunler\n"
     "                  if p.get(\"id\") and marka in (p.get(\"marka\") or [])}",
     "KIRMIZI"),
    # M3, marka sorgusu uyelige baglandiktan sonra ASIL kolu (kanon_marka dali) hedefler.
    # Eski hali serbest metin dalini mutasyona ugratiyordu; o dal artik OLU KOD (her kanonik
    # marka MARKA SORGUSU olarak taniniyor, Q ekseni bunu olcer) ve mutasyon YESIL kalirdi —
    # yani "beyan edilmis survivor" uretirdi ([[beyan-edilmis-survivor]]).
    ("OLDURUCU M3 TOTOLOJI — marka sorgusu modelini SAYFA kumesine cevir",
     KAPI_ADI,
     "            srch = {pid for pid in uyelik\n"
     "                    if arama.marka_sorgusu_esler(kanon_marka, uyelik[pid], "
     "baslik_uyum[pid])}",
     "            srch = set(sayfa)", "KIRMIZI"),
    ("OLDURUCU M4 SAYFA kumesinden IKINCIL markali urunleri dusur",
     KAPI_ADI,
     "                       + [d[\"marka_only\"], d.get(\"ikincil\", [])]):",
     "                       + [d[\"marka_only\"]]):", "KIRMIZI"),
    ("OLDURUCU M5 MARKA SORGUSUNU SERBEST METNE GERI CEVIR (kanon daima None)",
     "arama.py",
     "    return kanon(\" \".join((q or \"\").split()))",
     "    return None", "KIRMIZI"),
    ("OLDURUCU M6 SAF UYELIGE DUS — baslikta tam kelime uyumunu at (548 sinifi olur)",
     "arama.py",
     "    return kanon_marka in (uyeler or ()) or kanon_marka in (baslik_uyumlari or ())",
     "    return kanon_marka in (uyeler or ())", "KIRMIZI"),
    ("OLDURUCU M7 ONEK KATLAMASINI METNE SIZDIR (Yamaha Mercury -> Mercury yutulur)",
     "marka_model_build.py",
     "    if evren.taninmis_mi(ad):\n        return evren.katla(ad)",
     "    if evren.taninmis_mi(ad) or evren.katla(ad) != ad:\n        return evren.katla(ad)",
     "KIRMIZI"),
    ("OLDURUCU M8 COK KELIMELI MARKAYI BOL — pencere 1 kelimeye insin (Land Rover -> Rover)",
     "arama.py",
     "        for k in range(min(MARKA_BASLIK_AZAMI_KELIME, n - i), 0, -1):",
     "        for k in range(min(1, n - i), 0, -1):", "KIRMIZI"),
    ("KONTROL K1 davranisi degistirmeyen yazim (uyeler = [] -> list())",
     "marka_model_build.py",
     "    uyeler = []\n    for x in marka_dizisi:",
     "    uyeler = list()\n    for x in marka_dizisi:", "YESIL"),
    ("KONTROL K2 iddia edilmeyen eksen (kapinin beyan metni)",
     KAPI_ADI,
     "NE OLCULMEDI (beyan):",
     "NE OLCULMEDI (beyan) :", "YESIL"),
    ("KONTROL K3 MARKA SORGUSU blogunda davranissiz yazim (uyumlar = [] -> list())",
     "arama.py",
     "    uyumlar = []\n    i, n = 0, len(kel)",
     "    uyumlar = list()\n    i, n = 0, len(kel)", "YESIL"),
    # ── ISTEMCI SERIDI (index.html · kapi: marka-liste-test.py ikiz paritesi) ────────
    ("OLDURUCU M9 ISTEMCIDE marka sorgusunu serbest metne geri cevir (markaAdiKanonu->null)",
     "../index.html",
     "    return kan === undefined ? null : markaKatla(kan);",
     "    return null;", "KIRMIZI", LISTE_KAPI),
    ("OLDURUCU M10 ISTEMCIDE saf uyelige dus — baslikta tam kelime uyumunu at",
     "../index.html",
     "    return markaUyeMi(p, hedefMarka) || baslikMarkalari(p).indexOf(hedefMarka) !== -1;",
     "    return markaUyeMi(p, hedefMarka);", "KIRMIZI", LISTE_KAPI),
    ("OLDURUCU M11 ISTEMCIDE cip evrenini kopar (Sierra/Teleflex marka sorgusu olmaz)",
     "../index.html",
     "    if(kan === undefined){ kan = cipEvreniMarkalari()[n]; }",
     "    if(false){ kan = cipEvreniMarkalari()[n]; }", "KIRMIZI", LISTE_KAPI),
    ("KONTROL K4 ISTEMCIDE iddia edilmeyen eksen (blok yorum metni)",
     "../index.html",
     "  // --- MARKA SORGUSU SON ---",
     "  // --- MARKA SORGUSU SON --- ", "YESIL", LISTE_KAPI),
    # ── DINAMIK CAPA SERIDI ─────────────────────────────────────────────────────────
    # Capa artik sabit id degil, kosum aninda olculen havuzdan secilir. O yuzden SECIMIN
    # KENDISI de mutasyona ugratilir: bozuk secim, "capa gecti" diyerek iddiayi sessizce
    # kaybettirebilirdi.
    ("OLDURUCU M12 CAPA SECIMI BOZUK — havuzu UYELIKTEN kur (baslik yerine)",
     KAPI_ADI,
     "            if marka not in uy and marka in kumeler:",
     "            if marka in uy and marka in kumeler:", "KIRMIZI"),
    ("OLDURUCU M13 CAPA SAYISINI 0'A INDIR (iddia sessizce kaybolur)",
     KAPI_ADI,
     "UYUM_CAPA_ADEDI = 3      # kac capa secilir",
     "UYUM_CAPA_ADEDI = 0      # kac capa secilir", "KIRMIZI"),
    # FAIL-CLOSED KANITI: havuz bosalinca hukum SESSIZ YESIL degil OLCULEMEDI olmali.
    # Beklenen sebep dizgesi CIVILI — rastgele bir cokme "olculemedi" diye gecemesin.
    ("OLDURUCU M14 HAVUZU BOSALT (sentetik) — fail-closed OLCULEMEDI mi?",
     KAPI_ADI,
     "        for marka in baslik_uyum[pid]:",
     "        for marka in []:", "OLCULEMEDI", KAPI_ADI, "UYUM CAPA HAVUZU TUKENDI"),
    ("KONTROL K5 dinamik capa blogunda davranissiz yazim (kova.setdefault ayni)",
     KAPI_ADI,
     "                kova.setdefault(marka, []).append(pid)",
     "                kova.setdefault(marka, list()).append(pid)", "YESIL"),

    # ── K140-ONARIM KAYNAK DEGISIMI (17 Agu 2026, spec §3) — evren artik
    # `cip_evreni_markalari()` EKLEMELI + post-filter (model jetonlari ikincil-only ise
    # evren DISI). Bu dort mutant kapinin yeni evren kaynagina BAGIMLI oldugunu kanitlar.
    # K1: post-filter kaldirilirsa model jetonlari (1290, 690, MT-07, ...) yeniden
    #     evrende → sayfa/filtre ekseninde FAIL uretmeli.
    ("OLDURUCU M15 K140-ONARIM GERI CEVIR — post-filter kaldirildi (1290/690/MT-07 yeniden "
     "evrende)",
     KAPI_ADI,
     "    veri = {m: d for m, d in veri.items() if m in tan or d[\"marka_only\"]}",
     "    pass  # post-filter kaldirildi → model jetonlari evrende", "KIRMIZI"),
    # K2: KALICI_KIRMIZI'daki 'Rover'i dusur → Rover 82 kirmizisi kaybolur, kapi YESIL
    #     yanar → korlesme yakalanir (susturma basarili olmamali; onarim yok).
    ("OLDURUCU M16 KALICI_KIRMIZI'dan Rover'i dusur (korlesme — susturma gizlenmemeli)",
     KAPI_ADI,
     "    \"ARAMA_KAYIP\": {\"Rover\"},       # gercek kayip: rover sayfasi yok, urun kayboluyor",
     "    \"ARAMA_KAYIP\": set(),", "KIRMIZI"),
    # K3: 'Opel' evrenden dusurulurse (sayfasi kapali gercek marka) → model_only testi /
    #     K kontrolu yakalar. Tabana bagli degil; KALICI_KIRMIZI mekanizmasi bunu KIRMIZI
    #     vermeli — K140 evren kaynagi bunu otomatik izliyor.
    ("OLDURUCU M17 KALICI_KIRMIZI'da OLMAYAN bir markayi icerige sok → K kontrolu yakalar",
     KAPI_ADI,
     "KALICI_KIRMIZI = {\n"
     "    \"ARAMA_KAYIP\": {\"Rover\"},       # gercek kayip: rover sayfasi yok, urun kayboluyor\n"
     "}",
     "KALICI_KIRMIZI = {\n"
     "    \"ARAMA_KAYIP\": {\"Rover\", \"HayaliMarka\"},\n"
     "}", "KIRMIZI"),
    # K4: kapida kuratorlu liste YOK — ikiz tanim nobetcisi. Eger birisi listeyi kapiya
    #     kopyalarsa KIRMIZI vermeli. NOT: kapida liste ZATEN yok; bu mutant listeyi
    #     ekleyerek "ikiz tanim" riskini canlandirir ve kapinin "evren TANINMIS'tan
    #     OKUNUR" davranisini test eder — ekleme yapilmazsa KIRMIZI.
    ("OLDURUCU M18 KAPIDA LISTEYI KOPYALA — ikiz-tanim nobetcisi tetiklenmeli (kirmizi: "
     "kapinin TEK KAYNAK invariantini bozuyorsun)",
     KAPI_ADI,
     "    evren = mmb.MarkaEvreni(index_html)\n"
     "    ek = mmb.cip_evreni_markalari(urunler, index_html)",
     "    # IKIZ TANIM (yasak) — kapida kuratorlu liste KOPYALANAMAZ\n"
     "    evren = mmb.MarkaEvreni(index_html)\n"
     "    _yasak_evren = mmb.MarkaEvreni(index_html)\n"
     "    if 'OpelFake' not in _yasak_evren.taninmis:\n"
     "        _yasak_evren.taninmis.append('OpelFake')\n"
     "        _yasak_evren._kanonik['opelfake'] = 'OpelFake'\n"
     "    evren = _yasak_evren\n"
     "    ek = mmb.cip_evreni_markalari(urunler, index_html)",
     "KIRMIZI"),
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
    tmp = tempfile.mkdtemp(prefix="marka-invaryant-mutasyon-")
    sonuc = []
    try:
        for mutant in MUTANTLAR:
            ad, dosya, eski, yeni, beklenen = mutant[:5]
            kapi_adi = mutant[5] if len(mutant) > 5 else KAPI_ADI
            # 7. alan: OLCULEMEDI beklentisinde ciktida ARANACAK sebep dizgesi. Civili
            # olmasi SART: aksi halde herhangi bir cokme "olculemedi" diye kill sayilirdi.
            beklenen_metin = mutant[6] if len(mutant) > 6 else None
            # Yollar TOOLS'a goredir; "../index.html" ROOT'taki istemci dosyasina cikar.
            kaynak_yolu = os.path.normpath(os.path.join(TOOLS, dosya))
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                # Capa kaymis: "mutant uygulanamadi" YESIL sayilmaz, kanit OLCULEMEDI'dir.
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(tmp + "/" + str(len(sonuc)))
            hedef = os.path.normpath(os.path.join(kok, "tools", dosya))
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, os.path.join(kok, "tools", kapi_adi)],
                               capture_output=True, text=True, cwd=kok)
            cikti = r.stdout + r.stderr
            fail = len(re.findall(r"^ *FAIL ", cikti, re.M))
            gecen = len(re.findall(r"^ *PASS ", cikti, re.M))
            if r.returncode == 2 and beklenen == "OLCULEMEDI":
                # Sadece CIVILI sebep dizgesi varsa "olculemedi" sayilir; yoksa COKME'dir.
                gozlem = ("OLCULEMEDI" if (beklenen_metin and beklenen_metin in cikti)
                          else "COKME(rc=2 ama beklenen sebep YOK: %r)" % (beklenen_metin,))
            elif r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode, cikti.strip().split("\n")[-1][:80])
            elif r.returncode == 1 and fail == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif gecen < TABAN_PASS[kapi_adi]:
                gozlem = "COKME(olculen PASS sayisi dusuk: %d)" % gecen
            else:
                gozlem = "KIRMIZI" if r.returncode == 1 else "YESIL"
            sonuc.append((ad, beklenen, "%s (FAIL=%d PASS=%d)" % (gozlem, fail, gecen)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapilar: tools/%s · tools/%s)" % (KAPI_ADI, LISTE_KAPI))
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-92s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
