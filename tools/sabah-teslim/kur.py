#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SABAH+TESLIM KURUCUSU — deterministik, fail-loud, capa-dogrulamali.

`~/.claude/cron/` SURUM KONTROLU DISIDIR: her dosya once
`.yedek-sabahteslim-<UTC>` olarak kopyalanir, sonra CAPA ile yamanir.
🔴 CAPA BULUNAMAZSA HICBIR SEY YAZILMAZ (fail-closed) — "yamadim sanirim"
bir kurulum hukmu degildir. Kurucu ayrica IDEMPOTENTTIR: yama zaten
uygulanmissa TEKRAR uygulamaz ve bunu ADIYLA basar (C3 dersi).

Kosum:  python3 <bu dosya>            -> kur
        python3 <bu dosya> --kuru     -> ne yapacagini bas, YAZMA
        python3 <bu dosya> --geri-al  -> yedeklerden geri sar
"""

import argparse
import os
import py_compile
import shutil
import subprocess
import sys
import time

WT = os.path.dirname(os.path.abspath(__file__))
CRON = "/Users/okan/.claude/cron"
DAMGA = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
YEDEK_SONEKI = ".yedek-sabahteslim-" + DAMGA

CIKTI_DIZINI = "/private/tmp/pruvo-sabah-teslim"
HAM = os.path.join(CIKTI_DIZINI, "kurulum.log")

sys.path.insert(0, WT)


def _blok(dosya_adi, ad):
    """Yama metnini worktree'deki kaynak dosyadan OKUR (ikiz tanim yok)."""
    yol = os.path.join(WT, dosya_adi)
    kap = {}
    with open(yol, encoding="utf-8") as f:
        exec(compile(f.read(), yol, "exec"), kap)
    return kap[ad]


# ---------------------------------------------------------------- YAMALAR
# (hedef_dosya, capa, yeni_metin, "EKLE"|"DEGISTIR", aciklama)

def yamalar():
    teslim = _blok("teslim-blok.py", "TESLIM_BLOGU")
    kabul = _blok("kabul-blok.py", "KABUL_BLOGU")

    Y = []

    # === cip_dogum_bekcisi.py ===
    Y.append(("cip_dogum_bekcisi.py",
              "import datetime as dt\nimport os\nimport re\nimport subprocess\nimport time\n",
              "import argparse\nimport datetime as dt\nimport os\nimport re\n"
              "import subprocess\nimport sys\nimport time\n",
              "argparse+sys import (teslim kolu CLI'si icin)"))

    Y.append(("cip_dogum_bekcisi.py",
              'KANALLAR = ("YOK", "terminal-notifier", "osascript")\nBILDIRIM_KANALI = "YOK"\n',
              'KANALLAR = ("YOK", "terminal-notifier", "osascript", "cip")\n'
              '# 🔴 27 Agu 2026 OKAN KARARI: teslim kanali CIP. Gerekce OLCULMUS —\n'
              '# bugun Okan\'a ULASTIGI KANITLANMIS tek kanal paneldir.\n'
              'BILDIRIM_KANALI = "cip"\n',
              "BILDIRIM_KANALI: YOK -> cip"))

    # --- TESLIM_KOLLARI: IHTAR gunde 2 kosuma cikti + TAVAN TURETILDI
    Y.append(("cip_dogum_bekcisi.py",
              'TESLIM_KOLLARI = (\n'
              '    {"id": "IHTAR",\n'
              '     "kanca": "/Users/okan/.claude/scheduled-tasks/gunluk-mimar-ihtar/SKILL.md",\n'
              '     "jeton": "ADIM 0 — ÇİP-DOĞUM BEKÇİSİ",\n'
              '     # gunde 1 kosum (15:00) -> 30 saat = bir kacirilan kosum + pay\n'
              '     "tavan_saat": 30},\n'
              '    {"id": "TEFTIS",\n'
              '     "kanca": "/Users/okan/.claude/scheduled-tasks/teftis-takip/SKILL.md",\n'
              '     # 🔴 AYRI JETON: teftis-takip\'in KENDI "ADIM 0"i (erteleme kontrolu) zaten\n'
              '     # var; ayni jetonu kullanmak iki blogu birbirine karistirir.\n'
              '     "jeton": "ADIM 00 — ÇİP-DOĞUM BEKÇİSİ",\n'
              '     # gunde 2 kosum (17:00, 23:00); en genis bosluk 18 saat -> 30 saat pay birakir\n'
              '     "tavan_saat": 30},\n'
              ')\n',

              '# 🔴 27 AGU 2026 — TAVAN TURETILIR, ELLE KOPYALANMAZ.\n'
              '# Sinif [[K316]] ile AYNI: turetilebilir bir degerin elle kopyalanmasi ve\n'
              '# kaynagindan sessizce ayrismasi. Her kolun TEK KAYNAGI kendi `saatler`\n'
              '# demetidir; tavan ondan HESAPLANIR:\n'
              '#     tavan = EN GENIS SESSIZLIK PENCERESI + PAY\n'
              '# Bir kacirilan kosum en genis bosluk kadar sessizlik uretir; PAY makine\n'
              '# uykusu/jitter payidir. DOGRULAMA (regresyon YOK — sayilar DEGISMEDI):\n'
              '#     TEFTIS (17,23) -> bosluklar 6/18 -> 18+12 = 30  (ESKI SABIT ILE AYNI)\n'
              '#     IHTAR  ( 9,15) -> bosluklar 6/18 -> 18+12 = 30  (ESKI SABIT ILE AYNI)\n'
              '# Degisen sey SAYI degil, gerekcenin TEK KAYNAGA baglanmasidir.\n'
              'TESLIM_PAY_SAAT = 12\n\n'
              '# 🔴 SABAH SAATI ESIKTEN TURER — IKIZ SAYI YOK. Kol esikten ONCE atesLERSE\n'
              '# (or. 08:59) hukum PENCERE_DISI olur ve sabah SESSIZ gecer; bu, 27 Agu\n'
              '# arizasinin kardesidir. Baglama burada YAPISAL olarak kapatilir.\n'
              'TESLIM_SABAH_SAATI = ESIK_SAAT\n\n\n'
              'def en_genis_bosluk(saatler):\n'
              '    """Gunluk kosum saatlerinden EN GENIS sessizlik penceresi (saat)."""\n'
              '    s = sorted({int(h) % 24 for h in saatler})\n'
              '    if len(s) <= 1:\n'
              '        return 24.0\n'
              '    araliklar = [s[i + 1] - s[i] for i in range(len(s) - 1)]\n'
              '    araliklar.append(24 - s[-1] + s[0])\n'
              '    return float(max(araliklar))\n\n\n'
              'def kol_tavani(saatler, pay=None):\n'
              '    """TEK FORMUL. `tavan_saat` alani BUNDAN doldurulur, elle YAZILMAZ."""\n'
              '    return en_genis_bosluk(saatler) + (TESLIM_PAY_SAAT if pay is None else pay)\n\n\n'
              'TESLIM_KOLLARI = (\n'
              '    {"id": "IHTAR",\n'
              '     "kanca": "/Users/okan/.claude/scheduled-tasks/gunluk-mimar-ihtar/SKILL.md",\n'
              '     "jeton": "ADIM 0 — ÇİP-DOĞUM BEKÇİSİ",\n'
              '     # 🔴 27 Agu 2026 OKAN TASARIMI: IHTAR gunde 1 -> 2 kosum.\n'
              '     #   09:00 = SABAH gozden gecirmesi (bugunun cipi dogdu mu) — TESLIM KOLU\n'
              '     #   15:00 = mevcut gunluk mimar ihtari\n'
              '     # Sabah saati `TESLIM_SABAH_SAATI` (= ESIK_SAAT) uzerinden gelir.\n'
              '     "saatler": (TESLIM_SABAH_SAATI, 15),\n'
              '     "tavan_saat": kol_tavani((TESLIM_SABAH_SAATI, 15))},\n'
              '    {"id": "TEFTIS",\n'
              '     "kanca": "/Users/okan/.claude/scheduled-tasks/teftis-takip/SKILL.md",\n'
              '     # 🔴 AYRI JETON: teftis-takip\'in KENDI "ADIM 0"i (erteleme kontrolu) zaten\n'
              '     # var; ayni jetonu kullanmak iki blogu birbirine karistirir.\n'
              '     "jeton": "ADIM 00 — ÇİP-DOĞUM BEKÇİSİ",\n'
              '     "saatler": (17, 23),\n'
              '     "tavan_saat": kol_tavani((17, 23))},\n'
              ')\n',
              "TESLIM_KOLLARI: IHTAR 09+15, tavan TURETILDI (30 -> 30, regresyon yok)"))

    Y.append(("cip_dogum_bekcisi.py",
              "    kanal = kanal or BILDIRIM_KANALI\n\n    if kanal == \"YOK\":\n",
              "    kanal = kanal or BILDIRIM_KANALI\n\n"
              "    if kanal == \"cip\":\n"
              "        # 🔴 Bu SUREC cip DOGURAMAZ (cipi yalniz bir Claude oturumu\n"
              "        # yaratabilir). Teslim `teslim_karari`/`teslim_kaydet` kolunda.\n"
              "        # SOMUT rc doner: `rc=None` bir daha YAZILMAZ.\n"
              "        return 0, (\"KANAL=cip — teslim RUTIN kolunda \"\n"
              "                   \"(`cip_dogum_bekcisi.py --teslim-karari`)\")\n\n"
              "    if kanal == \"YOK\":\n",
              "uygulama_bildirimi: cip kolu (rc=None yerine SOMUT rc)"))

    Y.append(("cip_dogum_bekcisi.py",
              '    anahtar = "%s%s" % (anahtar_oneki, str(k.get("tarih") or "-").replace("-", ""))\n'
              "    kazandi, damga_yolu = _damga_koy(anahtar, simdi, damga_dizini)\n",
              '    anahtar = "%s%s" % (anahtar_oneki, str(k.get("tarih") or "-").replace("-", ""))\n\n'
              '    if kanal == "cip":\n'
              "        # 🔴 DAMGA TUKETILMEZ. Damga 'bugun TESLIM EDILDI' jetonudur ve onu\n"
              "        # yalniz teslim kolu koyar. Bu kol gunde 96 kez kosar; damgayi\n"
              "        # burada yakmak sabah rutinini MUKERRER'e dusurup teslimi SONSUZA\n"
              "        # KADAR engellerdi — 26/27 Agu'da fiilen yasanan hal budur.\n"
              '        bos["anahtar"] = anahtar\n'
              '        bos["rc"] = 0\n'
              '        bos["teslim"] = "TESLIM_KOLUNDA"\n'
              '        bos["ayrinti"] = ("KANAL=cip — hukum KIRMIZI, teslim RUTIN kolunda; "\n'
              '                          "damga TUKETILMEDI")\n'
              "        return bos\n\n"
              "    kazandi, damga_yolu = _damga_koy(anahtar, simdi, damga_dizini)\n",
              "bildir(): cip kolunda damga TUKETILMEZ"))

    Y.append(("cip_dogum_bekcisi.py",
              'if __name__ == "__main__":\n'
              "    import sys\n"
              '    _kuru = "--kuru" in sys.argv\n'
              "    _s = kol(kuru=_kuru)\n"
              '    print(_s["ozet"] + " kanit=%s boyut=%s" % (_s.get("kanit_adi"), _s.get("boyut")))\n'
              "    sys.exit(1 if kirmizi_mi(_s) else 0)\n",
              teslim.lstrip("\n"),
              "TESLIM KOLU blogu + yeni CLI"))

    # === bekci-kabul.py ===
    Y.append(("bekci-kabul.py",
              "# ---------------------------------------------------------------------- ana\n",
              kabul.strip("\n") + "\n\n\n"
              "# ---------------------------------------------------------------------- ana\n",
              "H — teslim (KANAL=cip) bataryasi"))

    # === bekci-kur.py — BASLIK SOZLESMENIN DEGISEN ALANINI GORMELIYDI ===
    # 🔴 OLCULDU (27 Agu): IHTAR gunde 1 -> 2 kosuma cikti, ama URETILEN baslik
    # DEGISMEDI — cunku satir bicimi `kosum saatleri` alanini HIC RENDER ETMIYOR
    # ve tavan (turetme sayesinde) 30'da kaldi. Yani sozlesme degisti, "sozlesmeden
    # uretilen" baslik bunu GOSTEREMEDI. Bu, K240'in kendi sinifidir bir kat
    # asagida: deger URETILIYOR, tuketicisi YOK. Alan basliga EKLENIR.
    Y.append(("bekci-kur.py",
              '        tavanlar.append(float(kol.get("tavan_saat") or taban_tavan))\n',
              '        tavanlar.append(float(kol.get("tavan_saat") or taban_tavan))\n'
              '        # 27 Agu: kosum saatleri de RENDER EDILIR — tavan bu saatlerden\n'
              '        # TURETILIR, dolayisiyla saatler degisip tavan ayni kalabilir\n'
              '        # (IHTAR 15 -> 9,15 tam olarak boyle oldu). Saatler basilmazsa\n'
              '        # sozlesme degisimi basliktan OKUNAMAZ.\n'
              '        saatler.append(",".join("%02d" % int(h)\n'
              '                                for h in (kol.get("saatler") or ()))\n'
              '                       or "-")\n',
              "bekci-kur.py: kosum saatleri toplanir"))

    Y.append(("bekci-kur.py",
              '    g1 = max(len(s) for s in kimlikler)\n',
              '    g0 = max([len(s) for s in saatler] or [1])\n'
              '    g1 = max(len(s) for s in kimlikler)\n',
              "bekci-kur.py: saat sutunu genisligi"))

    Y.append(("bekci-kur.py",
              '        "# Kollar — kol | zamanlanmis gorev | damga bicimi | bayatlik tavani:",\n'
              '    ]\n'
              '    for kimlik, gorev, damga, tavan in zip(kimlikler, gorevler, damgalar, tavanlar):\n'
              '        satirlar.append("#   %-*s | %-*s | %-*s | %g sa"\n'
              '                        % (g1, kimlik, g2, gorev, g3, damga, tavan))\n',

              '        "# Kollar — kol | zamanlanmis gorev | damga bicimi | kosum | tavan:",\n'
              '    ]\n'
              '    for kimlik, gorev, damga, tavan, saat in zip(\n'
              '            kimlikler, gorevler, damgalar, tavanlar, saatler):\n'
              '        satirlar.append("#   %-*s | %-*s | %-*s | %-*s | %g sa"\n'
              '                        % (g1, kimlik, g2, gorev, g3, damga, g0, saat, tavan))\n',
              "bekci-kur.py: baslik satiri kosum saatlerini GOSTERIR"))

    Y.append(("bekci-kur.py",
              "    kimlikler, gorevler, damgalar, tavanlar = [], [], [], []\n",
              "    kimlikler, gorevler, damgalar, tavanlar = [], [], [], []\n"
              "    saatler = []\n",
              "bekci-kur.py: saatler listesi"))

    # 🔴 K7 CAPASI, TESLIM_KOLLARI DEGISINCE COKTU — ve bu tam olarak K7'nin
    # KENDI olctugu siniftir ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]):
    # capa kaynaktan ELLE KOPYALANMIS bir parcaydi, kaynak degisince sessizce
    # `adet=0` verdi ve vaka `OLCULEMEDI`ye dustu. Capa yeni kuyruga HIZALANIR
    # ve eklenen ucuncu kol da `kol_tavani()`den TURETIR — yani K7 artik
    # "elle sabit" bir kol EKLEMEZ, kendi olctugu kurala kendisi uyar.
    Y.append(("bekci-kabul.py",
              'UCUNCU_KOL_ANKOR = \'\'\'     "tavan_saat": 30},\n'
              ')\n'
              "'''\n"
              'UCUNCU_KOL_YENI = \'\'\'     "tavan_saat": 30},\n'
              '    {"id": "UCUNCU",\n'
              '     "kanca": "/Users/okan/.claude/scheduled-tasks/ucuncu-kol/SKILL.md",\n'
              '     "jeton": "ADIM 000 — ÇİP-DOĞUM BEKÇİSİ",\n'
              '     "tavan_saat": 42},\n'
              ')\n'
              "'''\n",

              '# 🔴 UCUNCU KOLUN SAATLERI TEK KAYNAK: hem enjekte edilen kaynak\n'
              '# metni hem de K7 BEKLENTISI bundan uretilir. Eskiden beklenti\n'
              '# `"42 sa"` diye ELLE KOPYALANMISTI ve `TESLIM_KOLLARI` degisir\n'
              '# degismez vaka sessizce kirmiziya dondu — K7 tam da bu sinifi\n'
              '# olcuyordu, kendisi ona yakalandi.\n'
              'UCUNCU_KOL_SAATLERI = (3,)\n'
              'UCUNCU_KOL_ANKOR = \'\'\'     "saatler": (17, 23),\n'
              '     "tavan_saat": kol_tavani((17, 23))},\n'
              ')\n'
              "'''\n"
              "UCUNCU_KOL_YENI = ('''     \"saatler\": (17, 23),\n"
              '     "tavan_saat": kol_tavani((17, 23))},\n'
              '    {"id": "UCUNCU",\n'
              '     "kanca": "/Users/okan/.claude/scheduled-tasks/ucuncu-kol/SKILL.md",\n'
              '     "jeton": "ADIM 000 — ÇİP-DOĞUM BEKÇİSİ",\n'
              '     "saatler": %r,\n'
              '     "tavan_saat": kol_tavani(%r)},\n'
              ')\n'
              "''' % (UCUNCU_KOL_SAATLERI, UCUNCU_KOL_SAATLERI))\n",
              "K7 capasi HIZALANDI + ucuncu kol saatleri TEK KAYNAK"))

    Y.append(("bekci-kabul.py",
              '            eksik = [j for j in ("UCUNCU", "KOSTU=UCUNCU@<ISO>Z", "42 sa",\n'
              '                                 "SAG_<n>/3_OLU", "3 teslim kolu")\n'
              '                     if j not in b7]\n',
              '            # 🔴 BEKLENEN TAVAN DA TURETILIR (27 Agu): sabit "42 sa"\n'
              '            # aracin formulunden KOPARILMIS bir ikizdi. Beklenti artik\n'
              '            # aracin KENDI `kol_tavani()`sinden okunur — kaynak degisince\n'
              '            # vaka kendiliginden hizalanir, sessizce kirmiziya donmez.\n'
              '            _uc_tavan = modul_yukle(\n'
              '                MODUL, "cdb_k7_tavan", (CRON,)).kol_tavani(UCUNCU_KOL_SAATLERI)\n'
              '            eksik = [j for j in ("UCUNCU", "KOSTU=UCUNCU@<ISO>Z",\n'
              '                                 "%g sa" % _uc_tavan,\n'
              '                                 "SAG_<n>/3_OLU", "3 teslim kolu")\n'
              '                     if j not in b7]\n',
              "K7 beklenen tavani TURETILDI (elle '42 sa' KALKTI)"))

    Y.append(("bekci-kabul.py",
              '    ap.add_argument("--faz", choices=("taban", "tam", "yuzey", "yon"), default="tam")\n',
              '    ap.add_argument("--faz",\n'
              '                    choices=("taban", "tam", "yuzey", "yon", "teslim"),\n'
              '                    default="tam")\n',
              "--faz teslim secenegi"))

    Y.append(("bekci-kabul.py",
              '    elif args.faz == "yuzey":\n',
              '    elif args.faz == "teslim":\n'
              "        # 27 Agu dar seridi: yalniz TESLIM (KANAL=cip). Ag YOK, canli\n"
              "        # damga/log/spec duzlemine DOKUNMAZ — tamami fiksturdur.\n"
              "        if not os.path.isfile(MODUL):\n"
              '            print("HATA: modul kurulu DEGIL -> %s" % MODUL)\n'
              "            return 2\n"
              "        teslim_cip_bataryasi()\n"
              '    elif args.faz == "yuzey":\n',
              "main(): --faz teslim dali"))

    Y.append(("bekci-kabul.py",
              "        bayat_yuzey_bataryasi()\n"
              "        yon_ayrimi_bataryasi()\n"
              '        regresyon("SONRA — kurulum sonrasi (TABAN ile kiyaslanir)", tabanla_kiyasla=True)\n',
              "        bayat_yuzey_bataryasi()\n"
              "        yon_ayrimi_bataryasi()\n"
              "        teslim_cip_bataryasi()\n"
              '        regresyon("SONRA — kurulum sonrasi (TABAN ile kiyaslanir)", tabanla_kiyasla=True)\n',
              "main(): tam fazina teslim bataryasi eklendi"))

    return Y


# --------------------------------------------------------------------- ana

def dosya_oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def kur(kuru=False):
    os.makedirs(CIKTI_DIZINI, exist_ok=True)
    satirlar = []

    def yaz(s):
        satirlar.append(s)
        print(s)

    yaz("SABAH+TESLIM KURULUMU — %s  kuru=%d" % (DAMGA, int(kuru)))

    # --- 1) TAM KOPYA dosyalar (worktree -> cron)
    tam_kopya = [("kral-sabah.py", 0o700), ("sabah-kabul.py", 0o700)]
    for ad, mod in tam_kopya:
        kaynak = os.path.join(WT, ad)
        hedef = os.path.join(CRON, ad)
        var = os.path.isfile(hedef)
        ayni = var and dosya_oku(kaynak) == dosya_oku(hedef)
        yaz("KOPYA %-18s var=%d ayni=%d kaynak_bayt=%d" % (
            ad, int(var), int(ayni), os.path.getsize(kaynak)))
        if kuru or ayni:
            continue
        if var:
            shutil.copy2(hedef, hedef + YEDEK_SONEKI)
            yaz("  YEDEK=%s" % (hedef + YEDEK_SONEKI))
        shutil.copy2(kaynak, hedef)
        os.chmod(hedef, mod)
        yaz("  YAZILDI=%s bayt=%d" % (hedef, os.path.getsize(hedef)))

    # --- 2) CAPALI YAMALAR
    Y = yamalar()
    hedefler = sorted({y[0] for y in Y})
    metinler = {h: dosya_oku(os.path.join(CRON, h)) for h in hedefler}
    yedeklendi = set()
    uygulanan = 0
    zaten = 0
    dusen = []

    cogalmis = 0
    for hedef, capa, yeni, aciklama in Y:
        metin = metinler[hedef]
        capa_adedi = metin.count(capa)
        yeni_adedi = metin.count(yeni)

        # 🔴 27 Agu 2026 — `KraL-SabahYorumlayici-27Agu` / K320: IDEMPOTENS
        # OLCUTU SONUC EKSENINDEN OKUNUR. Eski kol soyleydi:
        #     zaten_var = metin.count(yeni) >= 1
        #     if zaten_var and capa_adedi == 0: ZATEN
        # `capa_adedi == 0` sarti EKLEME tipi yamalarda ASLA saglanmaz, cunku
        # o yamalarda `capa` eklenen metnin ICINDE durur (capa ⊂ yeni) →
        # kurulumdan SONRA da capa_adedi == 1 kalir → akis her kosumda
        # UYGULA'ya iner → ICERIK COGALIR. Kusur `--geri-al`li kosum
        # yordamiyla maskelenmisti; ARGUMANSIZ IKINCI KOSUM idempotens kanitidir.
        # Dogru soru "capa tuketildi mi" DEGIL, "HEDEF METIN BIR KEZ VAR MI".
        if yeni_adedi == 1:
            zaten += 1
            yaz("YAMA  [ZATEN] %-14s %s  (capa_adedi=%d — capa ⊂ yeni ise 1 KALIR)"
                % (hedef, aciklama, capa_adedi))
            continue
        if yeni_adedi > 1:
            # Onceki COGALTAN kosumlarin birakabilecegi hal: sessizce
            # "zaten kurulu" DEMEYIZ, fail-closed'a dusuruz.
            cogalmis += 1
            dusen.append("%s :: %s (COGALMIS yeni_adedi=%d)" % (hedef, aciklama, yeni_adedi))
            yaz("YAMA  [COGALMIS] %-12s %s  yeni_adedi=%d" % (hedef, aciklama, yeni_adedi))
            continue
        if capa_adedi != 1:
            dusen.append("%s :: %s (capa_adedi=%d)" % (hedef, aciklama, capa_adedi))
            yaz("YAMA  [CAPA_YOK] %-12s %s  capa_adedi=%d" % (hedef, aciklama, capa_adedi))
            continue
        metinler[hedef] = metin.replace(capa, yeni, 1)
        uygulanan += 1
        yaz("YAMA  [UYGULANDI] %-10s %s" % (hedef, aciklama))

    yaz("YAMA_OZET toplam=%d uygulanan=%d zaten=%d capa_yok=%d cogalmis=%d" % (
        len(Y), uygulanan, zaten, len(dusen) - cogalmis, cogalmis))

    if dusen:
        # 🔴 FAIL-CLOSED: tek bir capa bile bulunamazsa HICBIR SEY yazilmaz.
        yaz("🔴 CAPA COKMESI — HICBIR DOSYA YAZILMADI:")
        for d in dusen:
            yaz("   - %s" % d)
        _dosyaya_yaz(satirlar)
        return 3

    if kuru:
        yaz("KURU: yazim YAPILMADI.")
        _dosyaya_yaz(satirlar)
        return 0

    for hedef in hedefler:
        yol = os.path.join(CRON, hedef)
        if metinler[hedef] == dosya_oku(yol):
            yaz("YAZIM [DEGISIKLIK_YOK] %s" % hedef)
            continue
        if hedef not in yedeklendi:
            shutil.copy2(yol, yol + YEDEK_SONEKI)
            yedeklendi.add(hedef)
            yaz("YEDEK=%s" % (yol + YEDEK_SONEKI))
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metinler[hedef])
        yaz("YAZILDI=%s bayt=%d" % (yol, os.path.getsize(yol)))

    # --- 3) py_compile (fail-loud)
    derlenen = ["kral-sabah.py", "sabah-kabul.py", "cip_dogum_bekcisi.py",
                "bekci-kabul.py", "bekci-kur.py"]
    hata = 0
    for ad in derlenen:
        yol = os.path.join(CRON, ad)
        try:
            py_compile.compile(yol, cfile=os.path.join(CIKTI_DIZINI, ad + "c"),
                               doraise=True)
            yaz("DERLEME %-24s OK" % ad)
        except Exception as e:
            hata += 1
            yaz("DERLEME %-24s HATA %s: %s" % (ad, type(e).__name__, str(e)[:200]))
    yaz("DERLEME_OZET dosya=%d hata=%d" % (len(derlenen), hata))
    _dosyaya_yaz(satirlar)
    return 1 if hata else 0


def geri_al():
    """En YENI `.yedek-sabahteslim-*` kopyalarindan geri sar."""
    import glob
    n = 0
    for ad in ("kral-sabah.py", "sabah-kabul.py", "cip_dogum_bekcisi.py",
               "bekci-kabul.py", "bekci-kur.py"):
        adaylar = sorted(glob.glob(os.path.join(CRON, ad + ".yedek-sabahteslim-*")))
        if not adaylar:
            print("GERI_AL %-24s YEDEK_YOK" % ad)
            continue
        shutil.copy2(adaylar[-1], os.path.join(CRON, ad))
        print("GERI_AL %-24s <- %s" % (ad, os.path.basename(adaylar[-1])))
        n += 1
    print("GERI_AL_OZET=%d" % n)
    return 0


def _dosyaya_yaz(satirlar):
    with open(HAM, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print("HAM=%s" % HAM)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--geri-al", action="store_true")
    # 🔴 Idempotens FIKSTURU icin: kurucuyu CANLI duzleme (`~/.claude/cron/`)
    # dokunmadan, tek kullanimlik bir kopya uzerinde kosturabilmek sart —
    # yoksa "ikinci kosum icerigi cogaltiyor mu" sorusu ancak canli dosyalari
    # bozarak olculebilirdi.
    ap.add_argument("--cron-dizin", default=None,
                    help="hedef dizin (varsayilan ~/.claude/cron) — YALNIZ fikstur icin")
    ap.add_argument("--cikti-dizin", default=None,
                    help="kurulum log dizini (varsayilan /private/tmp/pruvo-sabah-teslim)")
    a = ap.parse_args()
    if a.cron_dizin:
        CRON = os.path.abspath(a.cron_dizin)
    if a.cikti_dizin:
        CIKTI_DIZINI = os.path.abspath(a.cikti_dizin)
        HAM = os.path.join(CIKTI_DIZINI, "kurulum.log")
    sys.exit(geri_al() if a.geri_al else kur(a.kuru))
