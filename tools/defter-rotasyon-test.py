#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-rotasyon-test.py — Fikstur + mutant + pre-commit RED provasi.

Gercek DEVAM.md / DEVAM-ARSIV.md / pre-commit uzerinde CALISMAZ; tempfile
altinda sentetik veri kurar. Cikti son satiri:

    FIKSTUR=<g/t> YENI_VAKA=<n> MUTANT=<OLDU|RED|...> RED_RC=<n> KONTROL_RC=<n> KAPSAM_RC=<n> CARE_SATIRI=<VAR|YOK> SAYAC_YOL=<yol> SAYAC_SATIR=<n>
"""
import os
import shutil
import subprocess
import sys
import tempfile


TOOLS = os.path.dirname(os.path.abspath(__file__))
ROTASYON = os.path.join(TOOLS, "defter-rotasyon.py")
PRE_COMMIT_KAYNAK = os.path.join(TOOLS, "kancalar", "pre-commit")


def _mutant_taban_kopyala(tmp):
    """K178: mutant tek kaynaktan (defter-kota-taban.py) okur; temp dir'e
    de kopyalanmali yoksa import_rc=1 ile mutantlar SURVIVOR olur."""
    taban = os.path.join(TOOLS, "defter-kota-taban.py")
    if os.path.exists(taban):
        import shutil
        shutil.copy(taban, os.path.join(tmp, "defter-kota-taban.py"))


def _fikstur_defter():
    return (
        "# Baslik bolgesi\n"
        "Bu kisim asla tasinmamalidir.\n"
        "\n"
        "## A — OTURUM KAPANISI 2026-08-10 ✅\n"
        "- Satir 1\n"
        "- Satir 2\n"
        "\n"
        "## B — ACIK KALEMLER\n"
        "- Bu blokta 🔴 acik isaretci var, kalmali.\n"
        "\n"
        "## C — X KAPANDI ✅\n"
        "- Bu blok kapanis isaretcisi tasiyor, tasinmali.\n"
        "\n"
        "## D — OKAN'DA\n"
        "- Bu blokta acik isaretci var, kalmali.\n"
        "\n"
        "## E — Y KAPANDI ✅ ama 🔧 yapilacak\n"
        "- Hem kapanis hem acik isaretci iceren karisik blok, kalmali.\n"
    )


def _kur(tmp, tarih="2026-08-16"):
    defter = os.path.join(tmp, "DEVAM.md")
    arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write(_fikstur_defter())
    with open(arsiv, "w", encoding="utf-8") as f:
        f.write("## Eski arsiv basligi\n- Eski kayit\n")
    return defter, arsiv, tarih


def _kostur(defter, arsiv, tarih="2026-08-16"):
    r = subprocess.run(
        [sys.executable, ROTASYON, defter, arsiv, "--tarih", tarih],
        capture_output=True, text=True)
    return r


def _bloklar(metin):
    """Baslik bolgesi haric blok basliklarini sirayla dondur."""
    basladi = False
    basliklar = []
    for satir in metin.splitlines():
        if satir.startswith("## "):
            basladi = True
            basliklar.append(satir)
        elif not basladi:
            continue
    return basliklar


def fikstur_test():
    hatalar = []
    kontrol = 0

    with tempfile.TemporaryDirectory() as tmp:
        defter, arsiv, tarih = _kur(tmp)
        eski_defter = open(defter, encoding="utf-8").read()
        eski_arsiv = open(arsiv, encoding="utf-8").read()

        r = _kostur(defter, arsiv, tarih)
        if r.returncode != 0:
            hatalar.append("F1 rotasyon basarisiz (rc=%d): %s" % (r.returncode, r.stderr))
            return hatalar, kontrol

        yeni_defter = open(defter, encoding="utf-8").read()
        yeni_arsiv = open(arsiv, encoding="utf-8").read()

        # F1: tasinanlar dogru (A, C)
        kontrol += 1
        arsiv_basliklar = _bloklar(yeni_arsiv)
        if not (any("A — OTURUM KAPANISI" in b for b in arsiv_basliklar) and
                any("C — X KAPANDI" in b for b in arsiv_basliklar)):
            hatalar.append("F1 tasinanlar yanlis: arsiv basliklari %r" % arsiv_basliklar)
        if any("B — ACIK KALEMLER" in b for b in arsiv_basliklar):
            hatalar.append("F1 B blogu yanlislikla tasindi")
        if any("D — OKAN'DA" in b for b in arsiv_basliklar):
            hatalar.append("F1 D blogu yanlislikla tasindi")
        if any("E — Y KAPANDI" in b for b in arsiv_basliklar):
            hatalar.append("F1 E blogu yanlislikla tasindi")

        # F2: kalanlar yerinde ve sirasi bozulmamis
        kontrol += 1
        defter_basliklar = _bloklar(yeni_defter)
        beklenen = [
            "## B — ACIK KALEMLER",
            "## D — OKAN'DA",
            "## E — Y KAPANDI ✅ ama 🔧 yapilacak",
        ]
        if defter_basliklar != beklenen:
            hatalar.append("F2 kalanlar sirasi bozuk: %r (beklenen %r)" % (
                defter_basliklar, beklenen))

        # F3: arsiv buyudu
        kontrol += 1
        if len(yeni_arsiv.encode("utf-8")) <= len(eski_arsiv.encode("utf-8")):
            hatalar.append("F3 arsiv buyumedu")

        # F4: defterden cikarilan icerik arsive eklenmis (kayip yok).
        kontrol += 1
        defter_azalma = len(eski_defter.encode("utf-8")) - len(yeni_defter.encode("utf-8"))
        arsiv_artis = len(yeni_arsiv.encode("utf-8")) - len(eski_arsiv.encode("utf-8"))
        if arsiv_artis < defter_azalma:
            hatalar.append("F4 icerik kayboldu: defter -%d bayt, arsiv +%d bayt" % (
                defter_azalma, arsiv_artis))

        # F5: tasinacak blok yokken dosyalar degismemeli
        kontrol += 1
        with tempfile.TemporaryDirectory() as tmp2:
            defter2 = os.path.join(tmp2, "DEVAM.md")
            arsiv2 = os.path.join(tmp2, "DEVAM-ARSIV.md")
            with open(defter2, "w", encoding="utf-8") as f:
                f.write("# Baslik\n## A — ACIK KALEMLER\n- 🔴 acik\n")
            with open(arsiv2, "w", encoding="utf-8") as f:
                f.write("## Eski\n- kayit\n")
            r2 = _kostur(defter2, arsiv2, tarih)
            if r2.returncode != 0:
                hatalar.append("F5 rc != 0: %s" % r2.stderr)
            d2_ici = open(defter2, encoding="utf-8").read()
            a2_ici = open(arsiv2, encoding="utf-8").read()
            if d2_ici != "# Baslik\n## A — ACIK KALEMLER\n- 🔴 acik\n":
                hatalar.append("F5 defter degisti (tasinacak yokken)")
            if a2_ici != "## Eski\n- kayit\n":
                hatalar.append("F5 arsiv degisti (tasinacak yokken)")

        # F6: baslik bolgesi hic tasinmadi
        kontrol += 1
        if "Baslik bolgesi" not in yeni_defter:
            hatalar.append("F6 baslik bolgesi defterden kayboldu")
        if "Baslik bolgesi" in yeni_arsiv:
            hatalar.append("F6 baslik bolgesi arsive gecti")

    return hatalar, kontrol


def _yaz_ve_calistir(tmp, defter_icerik, arsiv_icerik=None, tarih="2026-08-16"):
    """Sentetik defter+arsiv yaz, rotasyonu calistir, sonuclari dondur.

    Donus: (rc, stdout, yeni_defter, yeni_arsiv).
    """
    defter = os.path.join(tmp, "DEVAM.md")
    arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write(defter_icerik)
    with open(arsiv, "w", encoding="utf-8") as f:
        f.write(arsiv_icerik if arsiv_icerik is not None else "")
    r = _kostur(defter, arsiv, tarih)
    yeni_defter = open(defter, encoding="utf-8").read()
    yeni_arsiv = open(arsiv, encoding="utf-8").read()
    return r.returncode, r.stdout, yeni_defter, yeni_arsiv


def _son_satirdaki_sayiyi_al(stdout, jeton):
    """Son cikti satirindan <jeton>=<n> degerini cek (yoksa 0)."""
    for satir in (stdout or "").splitlines()[::-1]:
        if satir.startswith("TASINAN="):
            parca = [p for p in satir.split() if p.startswith(jeton + "=")]
            if parca:
                try:
                    return int(parca[0].split("=", 1)[1])
                except ValueError:
                    return 0
    return 0


def madde_test():
    """Madde granulu vakalari (V1-V9 + K128 yenileri V10-V14). Tek tek kontrol listesi."""
    hatalar = []
    gecen = 0
    kontrol = 14  # V1..V14

    # ----- V1 POZ -------------------------------------------------------
    # Acik blok icinde kapali madde TASINIR.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "# Baslik bolgesi\n"
            "\n"
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔴 genel acik\n"
            "- ✅ **K1 KAPANDI** detay\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V1 rotasyon basarisiz rc=%d: %s" % (rc, stdout))
        else:
            v1_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            v1_blok = _son_satirdaki_sayiyi_al(stdout, "TASINAN")
            if v1_madde != 1 or v1_blok != 0:
                hatalar.append("V1 sayac yanlis: TASINAN=%d TASINAN_MADDE=%d (beklenen 0/1)" % (
                    v1_blok, v1_madde))
            elif "K1 KAPANDI" not in yeni_arsiv:
                hatalar.append("V1 KAPANDI maddesi arsive gecmedi")
            elif "K1 KAPANDI" in yeni_defter:
                hatalar.append("V1 KAPANDI maddesi defterde kaldi")
            elif "🔴 genel acik" not in yeni_defter:
                hatalar.append("V1 acik madde yanlislikla tasindi")
            else:
                gecen += 1

    # ----- V2 NEG -------------------------------------------------------
    # Acik blok icinde acik madde TASINMAZ.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔧 **K2:** devam ediyor\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V2 rotasyon basarisiz rc=%d" % rc)
        else:
            v2_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v2_madde != 0:
                hatalar.append("V2 acik madde tasindi TASINAN_MADDE=%d" % v2_madde)
            elif "K2:" not in yeni_defter:
                hatalar.append("V2 acik madde defterden kayboldu")
            elif "K2:" in yeni_arsiv:
                hatalar.append("V2 acik madde arsive gecti")
            else:
                gecen += 1

    # ----- V3 NEG (karisik) ---------------------------------------------
    # Ayni maddede hem KAPANDI hem 🔧 -> TASINMAZ (suphede kalir).
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- ✅ K3 KAPANDI ama 🔧 hala acik\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V3 rotasyon basarisiz rc=%d" % rc)
        else:
            v3_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v3_madde != 0:
                hatalar.append("V3 karisik madde tasindi TASINAN_MADDE=%d" % v3_madde)
            elif "K3 KAPANDI ama" not in yeni_defter:
                hatalar.append("V3 karisik madde defterden kayboldu")
            elif "K3 KAPANDI ama" in yeni_arsiv:
                hatalar.append("V3 karisik madde arsive gecti")
            else:
                gecen += 1

    # ----- V4 POZ (cok satirli) -----------------------------------------
    # Kapali madde devam satirlariyla TUMUYLE tasinir, komsu acik
    # maddenin ilk satiri KESILMEZ.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔧 **K2:** acik satir 1\n"
            "- ✅ **K1 KAPANDI** detay\n"
            "  devam satiri 2\n"
            "  devam satiri 3\n"
            "- 🔧 **K4:** diger acik satir 1\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V4 rotasyon basarisiz rc=%d: %s" % (rc, stdout))
        else:
            v4_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v4_madde != 1:
                hatalar.append("V4 cok satirli kapali tasinmadi TASINAN_MADDE=%d" % v4_madde)
            elif "K1 KAPANDI" not in yeni_arsiv or "devam satiri 3" not in yeni_arsiv:
                hatalar.append("V4 kapali madde devam satirlariyla arsive gecmedi")
            elif "🔧 **K2:** acik satir 1" not in yeni_defter:
                hatalar.append("V4 acik K2'nin ilk satiri kesildi")
            elif "🔧 **K4:** diger acik satir 1" not in yeni_defter:
                hatalar.append("V4 acik K4'un ilk satiri kesildi")
            elif "K1 KAPANDI" in yeni_defter:
                hatalar.append("V4 kapali madde defterde kaldi")
            else:
                gecen += 1

    # ----- V5 NEG (mukerrer yok) ----------------------------------------
    # Blok granulu zaten tasiyorsa, madde kolu AYNI icerigi 2. kez
    # tasimamali. Burada blok KAPANDI isaretci tasir ve hic ACIK
    # isaretci yok -> blok olarak tasinir; madde kolu bos.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## A — KAPANDI ✅\n"
            "- ✅ **K1 KAPANDI** detay\n"
            "- ✅ **K2 KAPANDI** detay\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V5 rotasyon basarisiz rc=%d" % rc)
        else:
            v5_blok = _son_satirdaki_sayiyi_al(stdout, "TASINAN")
            v5_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v5_blok != 1:
                hatalar.append("V5 blok tasinmadi TASINAN=%d (beklenen 1)" % v5_blok)
            elif v5_madde != 0:
                hatalar.append("V5 mukerrer TASINAN_MADDE=%d (beklenen 0, blok zaten tasindi)" % v5_madde)
            else:
                # K1 ve K2 hem blok hem arsivde 1 kez gorunmeli.
                arsiv_ici = open(os.path.join(tmp, "DEVAM-ARSIV.md"), encoding="utf-8").read()
                k1_say = arsiv_ici.count("K1 KAPANDI")
                k2_say = arsiv_ici.count("K2 KAPANDI")
                if k1_say != 1 or k2_say != 1:
                    hatalar.append("V5 mukerrer: K1=%d K2=%d (her biri 1 olmali)" % (k1_say, k2_say))
                else:
                    gecen += 1

    # ----- V6 NEG (sonraki blog basligi tasinmaz) -----------------------
    # Acik blogun son kapali maddesi tasinir; bir sonraki blogun basligi
    # (`## C — ...`) yanlislikla tasinmamali.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- ✅ **K_last KAPANDI** detay\n"
            "\n"
            "## C — SONRAKI BLOG 🔴\n"
            "- acik icerik\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V6 rotasyon basarisiz rc=%d" % rc)
        else:
            v6_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v6_madde != 1:
                hatalar.append("V6 son kapali tasinmadi TASINAN_MADDE=%d" % v6_madde)
            elif "## C — SONRAKI BLOG" not in yeni_defter:
                hatalar.append("V6 sonraki blog basligi defterden kayboldu")
            elif "## C — SONRAKI BLOG" in yeni_arsiv:
                hatalar.append("V6 sonraki blog basligi arsive gecti")
            elif "- acik icerik" not in yeni_defter:
                hatalar.append("V6 sonraki blog govdesi kesildi")
            else:
                gecen += 1

    # ----- V7 NEG (arsiv indeksi TASINMAZ) ------------------------------
    # Acik bloktaki "- KAPANDI (arsivde): K91 · K101." gosteren indeks
    # satiri ARSIV'E isaret eder; madde-veto ile TASINMAZ (KUSUR-1).
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔧 **K5:** acik\n"
            "- KAPANDI (arsivde): K91 · K101.\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V7 rotasyon basarisiz rc=%d" % rc)
        else:
            v7_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v7_madde != 0:
                hatalar.append("V7 arsiv indeksi tasindi TASINAN_MADDE=%d (beklenen 0)" % v7_madde)
            elif "KAPANDI (arsivde): K91" not in yeni_defter:
                hatalar.append("V7 arsiv indeksi defterden kayboldu")
            elif "KAPANDI (arsivde): K91" in yeni_arsiv:
                hatalar.append("V7 arsiv indeksi arsive gecti")
            elif "**K5:**" not in yeni_defter:
                hatalar.append("V7 acik K5 yanlislikla tasindi")
            else:
                gecen += 1

    # ----- V8 POZ (ACIKLAMA veto ETMEZ) ---------------------------------
    # "ACIKLAMA" kelimesi "ACIK" ciplak alt-dize olarak eslesir; kelime-
    # sinirli aramayla bu yanlis veto kalkmali (KUSUR-2). Baslikta
    # KAPANDI var, govdede baska acik isaretci yok -> TASINIR.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## D — Y KAPANDI ✅\n"
            "- ACIKLAMA: is bitti, ek bilgi.\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V8 rotasyon basarisiz rc=%d" % rc)
        else:
            v8_blok = _son_satirdaki_sayiyi_al(stdout, "TASINAN")
            if v8_blok != 1:
                hatalar.append("V8 ACIKLAMA yuzunden blok tasinmadi TASINAN=%d (beklenen 1)" % v8_blok)
            elif "ACIKLAMA" in yeni_defter:
                hatalar.append("V8 ACIKLAMA blogu defterde kaldi")
            elif "ACIKLAMA" not in yeni_arsiv:
                hatalar.append("V8 ACIKLAMA blogu arsive gecmedi")
            else:
                gecen += 1

    # ----- V9 NEG (ACIK kelime-sinirli veto EDER) -----------------------
    # Govdede " ACIK " (boslukla cevrili, tek basina kelime) gecen
    # kapali gorunumlu blok TASINMAZ: kelime-sinirli ACIK veto eder.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## D — Y KAPANDI ✅\n"
            "- bu satirda ACIK kelimesi gecen acik bir kalem\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V9 rotasyon basarisiz rc=%d" % rc)
        else:
            v9_blok = _son_satirdaki_sayiyi_al(stdout, "TASINAN")
            if v9_blok != 0:
                hatalar.append("V9 ACIK kelimesi vetosuna ragmen blok tasindi TASINAN=%d (beklenen 0)" % v9_blok)
            elif "ACIK kelimesi" not in yeni_defter:
                hatalar.append("V9 blok defterden kayboldu")
            elif "ACIK kelimesi" in yeni_arsiv:
                hatalar.append("V9 blok arsive gecti")
            else:
                gecen += 1

    # ----- V10 NEG (CANLI VAKANIN FIKSTURU; K128) -----------------------
    # ## OKAN'DA blogundaki `- Eski yedek klasorunu ... karari.` maddesinin
    # devam satirinda `(Motor tarifesi kalemi 16 Agu'da KAPANDI: ...)` atfi
    # gecir; konum sarti yalnizca ILK SATIRA baktigi icin bu madde
    # TASINMAZ (ilk satir `- 🔧 Eski yedek...` ile basliyor; kapanis jetonu
    # ilk anlamli kelime degil).
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## OKAN'DA\n"
            "- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum "
            "eylemi silme karari.\n"
            "  (Motor tarifesi kalemi 16 Agu'da KAPANDI: kimi + minimax-m3 "
            "ust aboneligine gecildi.)\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V10 rotasyon basarisiz rc=%d" % rc)
        else:
            v10_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            v10_blok = _son_satirdaki_sayiyi_al(stdout, "TASINAN")
            if v10_madde != 0 or v10_blok != 0:
                hatalar.append(
                    "V10 ACIK Okan maddesi tasindi TASINAN=%d TASINAN_MADDE=%d "
                    "(beklenen 0/0; KAPANDI devam satirinda)" % (v10_blok, v10_madde))
            elif "Eski yedek klasorunu" not in yeni_defter:
                hatalar.append("V10 Eski yedek satiri defterden kayboldu")
            elif "Motor tarifesi kalemi" in yeni_arsiv:
                hatalar.append("V10 acik Okan maddesi (devam satiriyla) arsive gecti")
            elif "Motor tarifesi kalemi" not in yeni_defter:
                hatalar.append("V10 devam satiri kayipsiz durmali (defterde)")
            else:
                gecen += 1

    # ----- V11 NEG (kapanis kelimesi ORTADA; K128) ----------------------
    # `- Bu is devam ediyor; K91 KAPANDI diye referans veriyoruz.` —
    # kapanis jetonu ilk anlamli kelime degil; konum sarti tasinmamali
    # soyluyor.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- Bu is devam ediyor; K91 KAPANDI diye referans veriyoruz.\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V11 rotasyon basarisiz rc=%d" % rc)
        else:
            v11_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v11_madde != 0:
                hatalar.append(
                    "V11 KAPANDI ortada olmasina ragmen tasindi TASINAN_MADDE=%d" % v11_madde)
            elif "K91 KAPANDI diye referans" not in yeni_defter:
                hatalar.append("V11 acik madde defterden kayboldu")
            elif "K91 KAPANDI" in yeni_arsiv:
                hatalar.append("V11 acik madde arsive gecti")
            else:
                gecen += 1

    # ----- V12 POZ (`- ✅ **... KAPANDI ...`); K128 konum sarti ---------
    # `- ✅ **K1 KAPANDI**` formu zaten V1'de gecmistir; burada K127
    # davranisinin K128 konum sartiyla KORUNDUGUNU ayrica dogruluyoruz.
    # Konum sarti: `- ` sonrasi ilk anlamli jeton `✅`.
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔴 genel acik\n"
            "- ✅ **K120 KAPANDI (16 Agu, merge 5df50d78):** gizli kaynak "
            "kaydi artik izleme disi.\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V12 rotasyon basarisiz rc=%d" % rc)
        else:
            v12_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v12_madde != 1:
                hatalar.append("V12 - ✅ **... KAPANDI tasinmadi TASINAN_MADDE=%d" % v12_madde)
            elif "K120 KAPANDI" not in yeni_arsiv:
                hatalar.append("V12 KAPANDI maddesi arsive gecmedi")
            elif "K120 KAPANDI" in yeni_defter:
                hatalar.append("V12 KAPANDI maddesi defterde kaldi")
            else:
                gecen += 1

    # ----- V13 POZ (yalin `- KAPANDI ...`); K128 -------------------------
    # `- KAPANDI (K2): is bitti` formu. Konum sarti: `- ` sonrasi ilk
    # anlamli kelime `KAPANDI`. Arsiv veto YOK (metinde 'arsivde' yok);
    # dolayisiyla TASINIR. AYNI vakada `- KAPANDI (arsivde): ...` indeks
    # satiri tasinmaz (V7 ile cakismiyor; iki kural birlikte calisir).
    with tempfile.TemporaryDirectory() as tmp:
        defter = (
            "## B — ACIK KALEMLER 🔴\n"
            "- KAPANDI (K2): is bitti, ek bilgi.\n"
        )
        rc, stdout, yeni_defter, yeni_arsiv = _yaz_ve_calistir(tmp, defter)

        if rc != 0:
            hatalar.append("V13 rotasyon basarisiz rc=%d" % rc)
        else:
            v13_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
            if v13_madde != 1:
                hatalar.append("V13 yalin - KAPANDI tasinmadi TASINAN_MADDE=%d" % v13_madde)
            elif "KAPANDI (K2)" not in yeni_arsiv:
                hatalar.append("V13 KAPANDI (K2) arsive gecmedi")
            elif "KAPANDI (K2)" in yeni_defter:
                hatalar.append("V13 KAPANDI (K2) defterde kaldi")
            else:
                gecen += 1

    # ----- V14 (GORUNURLUK); K128 ---------------------------------------
    # Tasima yapilan kosumda stdout'ta `TASINAN-MADDE:` satiri VAR ve
    # tasinan maddenin ilk satirini (kirpilmis 100 kar.) icerir; hicbir
    # sey tasinmayan kosumda YOK.
    with tempfile.TemporaryDirectory() as tmp:
        # (a) Tasima var → TASINAN-MADDE: satir beklene.
        defter_tasima = (
            "## B — ACIK KALEMLER 🔴\n"
            "- ✅ **K1 KAPANDI** detay metni\n"
            "  devam satiri 2\n"
        )
        rc_a, stdout_a, yeni_defter_a, yeni_arsiv_a = _yaz_ve_calistir(tmp, defter_tasima)
        tasinan_satirlari = [
            s for s in (stdout_a or "").splitlines()
            if s.startswith("TASINAN-MADDE:")
        ]
        # (b) Tasima yok → TASINAN-MADDE: satir YOK.
        defter_yok = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔧 **K2:** devam ediyor\n"
        )
        rc_b, stdout_b, yeni_defter_b, yeni_arsiv_b = _yaz_ve_calistir(tmp, defter_yok)
        yok_satirlari = [
            s for s in (stdout_b or "").splitlines()
            if s.startswith("TASINAN-MADDE:")
        ]

        if rc_a != 0 or rc_b != 0:
            hatalar.append("V14 rotasyon basarisiz rc_a=%d rc_b=%d" % (rc_a, rc_b))
        elif len(tasinan_satirlari) != 1:
            hatalar.append(
                "V14 tasima kosumunda TASINAN-MADDE: satir sayisi=%d (beklenen 1): %r"
                % (len(tasinan_satirlari), tasinan_satirlari))
        elif "K1 KAPANDI" not in tasinan_satirlari[0]:
            hatalar.append(
                "V14 TASINAN-MADDE: satiri tasinan maddenin ilk satirini icermiyor: %r"
                % tasinan_satirlari[0])
        elif len(tasinan_satirlari[0]) > len("TASINAN-MADDE: ") + 100:
            hatalar.append("V14 TASINAN-MADDE: satiri 100 kar. asmis: %r" % tasinan_satirlari[0])
        elif len(yok_satirlari) != 0:
            hatalar.append(
                "V14 tasima yok kosumunda TASINAN-MADDE: satiri YAZILDI: %r" % yok_satirlari)
        else:
            gecen += 1

    return hatalar, gecen, kontrol


def tavan_test():
    """V-A/V-B/V-C: --tavan-sayi + --tavan-bayt tavan-bagli rotasyon.

    V-A: defter tavanin USTUNDE + kapali madde VAR → tavan altina INER.
    V-B: defter tavanin USTUNDE + kapali madde YOK → fail-loud (sessizce
         acik kalem arsive GITMEZ; rc != 0 ve stderr FAIL_LOUD icerir).
    V-C: defter tavanin ALTINDA → NO-OP (bayt-bayt ayni, arsiv dokunulmaz).
    """
    hatalar = []
    gecen = 0
    kontrol = 3

    # ----- V-A: tavan ustunde + kapali madde VAR → tavan altina iner -----
    with tempfile.TemporaryDirectory() as tmp:
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        # 12 kapali madde + 4 acik = 16 madde. Kapali olanlar tasiyabilir
        # olmali ve tavan altina dusmeli.
        kapali_satirlar = "\n".join(
            "- ✅ **K%02d KAPANDI** detay" % i for i in range(1, 13))
        acik_satirlar = "\n".join(
            "- 🔧 **A%02d:** acik kalem" % i for i in range(1, 5))
        icerik = (
            "# Baslik bolgesi\n\n"
            "## ACIK KALEMLER 🔴\n" + acik_satirlar + "\n\n"
            "## KAPALI SERI ✅\n" + kapali_satirlar + "\n"
        )
        with open(defter, "w", encoding="utf-8") as f:
            f.write(icerik)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        eski_defter_bayt = os.path.getsize(defter)
        eski_arsiv_bayt = os.path.getsize(arsiv)
        # Tavan dusuk secildi (5); dosya 21 satir, tavan ustunde.
        # Kapali blogun tamami tasininca defter 8 satira inmeli (5 < 8 DEGIL
        # — tavan kontrolu dosya SON halinde tavan altinda olmalI). Daha
        # dusuk tavan: kapali blog tasindiktan sonra kalan 8 satir tavanin
        # ustunde, o yuzden tavan 7 olarak secildi. Aciklarin tamami
        # (4 madde + 1 baslik + 1 govde satirlari) = 6-7 satir; kapali
        # blog tasininca 8 civari. tavan=10 secildi: dosya tavan altinda
        # olur (21 -> 8 < 10). Boylelikle tavan tek geciste altina dusuyor.
        r = subprocess.run(
            [sys.executable, ROTASYON, defter, arsiv,
             "--tarih", "2026-08-16",
             "--tavan-sayi", "10"],
            capture_output=True, text=True)
        if r.returncode != 0:
            hatalar.append("V-A rotasyon basarisiz rc=%d: %s" % (r.returncode, r.stderr))
        else:
            yeni_defter_bayt = os.path.getsize(defter)
            yeni_arsiv_bayt = os.path.getsize(arsiv)
            yeni_defter_satir = len(open(defter, "rb").read().splitlines())
            # KAPANDI iceren hicbir madde defterde kalmamali.
            defter_ici = open(defter, encoding="utf-8").read()
            if "KAPANDI" in defter_ici:
                hatalar.append("V-A kapali madde defterde kaldi")
            elif yeni_defter_satir > 10:
                hatalar.append("V-A tavan altina inmedi (satir=%d, tavan=10)" %
                               yeni_defter_satir)
            elif yeni_arsiv_bayt <= eski_arsiv_bayt:
                hatalar.append("V-A arsiv buyumedi (kayipsizlik)")
            elif yeni_defter_bayt >= eski_defter_bayt:
                hatalar.append("V-A defter kuculmedi")
            elif "TAVAN_BASARILI" not in r.stdout:
                hatalar.append("V-A TAVAN_BASARILI yok: stdout=%r" % r.stdout)
            else:
                gecen += 1

    # ----- V-B: tavan ustunde + kapali madde YOK → fail-loud -------------
    with tempfile.TemporaryDirectory() as tmp:
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        # YALNIZ acik icerik; kapali yok. Tavan 4 (defter ~7 satir).
        icerik = (
            "# Baslik bolgesi\n\n"
            "## ACIK KALEMLER 🔴\n"
            "- 🔧 **A01:** acik 1\n"
            "- 🔧 **A02:** acik 2\n"
            "- 🔧 **A03:** acik 3\n"
            "- 🔧 **A04:** acik 4\n"
            "- 🔧 **A05:** acik 5\n"
        )
        with open(defter, "w", encoding="utf-8") as f:
            f.write(icerik)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        eski_defter_icerik = open(defter, encoding="utf-8").read()
        eski_arsiv_icerik = open(arsiv, encoding="utf-8").read()
        r = subprocess.run(
            [sys.executable, ROTASYON, defter, arsiv,
             "--tarih", "2026-08-16",
             "--tavan-sayi", "4"],
            capture_output=True, text=True)
        yeni_defter_icerik = open(defter, encoding="utf-8").read()
        yeni_arsiv_icerik = open(arsiv, encoding="utf-8").read()
        if r.returncode == 0:
            hatalar.append("V-B fail-loud vermedi (rc=0): %s" % r.stdout)
        elif yeni_defter_icerik != eski_defter_icerik:
            hatalar.append("V-B defter degisti (kapali icerik yoktu)")
        elif yeni_arsiv_icerik != eski_arsiv_icerik:
            hatalar.append("V-B arsiv degisti (kapali icerik yoktu)")
        elif "TAVAN_FAIL_LOUD" not in r.stderr and "KAYIP:" not in r.stderr:
            # K181d: acik kalemler K### kimliksiz ise yeni I2 KAYIP mesaji
            # basar (FAIL_LOUD yerine); her iki mesaj da fail-loud muamelesi.
            hatalar.append("V-B stderr FAIL_LOUD/KAYIP yok: %s" % r.stderr)
        elif "A01" in yeni_arsiv_icerik or "A02" in yeni_arsiv_icerik:
            hatalar.append("V-B acik kalem arsive gecti (sessiz kayip)")
        else:
            gecen += 1

    # ----- V-C: tavan altinda → NO-OP -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        icerik = (
            "# Baslik\n\n"
            "## ACIK 🔴\n"
            "- 🔧 **A01:** acik\n"
            "- ✅ **K01 KAPANDI** detay\n"
        )
        with open(defter, "w", encoding="utf-8") as f:
            f.write(icerik)
        arsiv_icerik = "## Eski\n- eski\n"
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write(arsiv_icerik)
        # Tavan 100; dosya cok altinda. NO-OP.
        r = subprocess.run(
            [sys.executable, ROTASYON, defter, arsiv,
             "--tarih", "2026-08-16",
             "--tavan-sayi", "100"],
            capture_output=True, text=True)
        yeni_defter = open(defter, "rb").read()
        yeni_arsiv = open(arsiv, encoding="utf-8").read()
        if r.returncode != 0:
            hatalar.append("V-C rotasyon basarisiz rc=%d: %s" % (r.returncode, r.stderr))
        elif yeni_defter.decode("utf-8") != icerik:
            hatalar.append("V-C defter bayt-bayt ayni degil")
        elif yeni_arsiv != arsiv_icerik:
            hatalar.append("V-C arsiv bayt-bayt ayni degil")
        elif "TAVAN=DOLU_NO_OP" not in r.stdout:
            hatalar.append("V-C NO-OP isareti yok: stdout=%r" % r.stdout)
        else:
            gecen += 1

    return hatalar, gecen, kontrol


def mutant_test():
    """M1: tum acik jeton kontrolleri no-op -> E blogu yanlis tasir.

    `_acik_eslesiyor` govdesi bosaltilir; boylece E blogunun
    (`## E — Y KAPANDI ✅ ama 🔧 yapilacak`) hem acik jetonu (🔧,
    YAPILACAK) hem kapama isaretcisi tasiyan kismi acik vetosuz
    oldugu icin KAPANDI yuzunden tasir. F1/F2 kirilir.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    eski = ("    if _HARF_JETON_RE.search(metin):\n"
            "        return True\n"
            "    for jeton in _EMOJI_JETONLAR:\n"
            "        if jeton in metin:\n"
            "            return True\n"
            "    return False\n")
    yeni = "    return False  # M1 mutant: tum acik jeton kontrolleri no-op\n"
    if eski not in govde:
        return None, "MUTANT CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-defter-rotasyon.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(_fikstur_defter())
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("## Eski arsiv basligi\n- Eski kayit\n")

        r = subprocess.run(
            [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
            capture_output=True, text=True)

        if r.returncode != 0:
            return True, "mutant kirmizi yandi (rc=%d)" % r.returncode

        yeni_defter = open(defter, encoding="utf-8").read()
        yeni_arsiv = open(arsiv, encoding="utf-8").read()
        arsiv_basliklar = _bloklar(yeni_arsiv)
        defter_basliklar = _bloklar(yeni_defter)

        bozuk = False
        sebep = []
        if not (any("A — OTURUM KAPANISI" in b for b in arsiv_basliklar) and
                any("C — X KAPANDI" in b for b in arsiv_basliklar)):
            bozuk = True
            sebep.append("A/C tasinmadi")
        if any("B — ACIK KALEMLER" in b for b in arsiv_basliklar):
            bozuk = True
            sebep.append("B tasindi")
        if any("D — OKAN'DA" in b for b in arsiv_basliklar):
            bozuk = True
            sebep.append("D tasindi")
        if any("E — Y KAPANDI" in b for b in arsiv_basliklar):
            bozuk = True
            sebep.append("E tasindi")
        if defter_basliklar != []:
            bozuk = True
            sebep.append("defterde kalanlar yanlis: %r" % defter_basliklar)

        if bozuk:
            return True, "mutant F1/F2'yi bozdu (%s)" % "; ".join(sebep)
        return False, "mutant F1/F2'yi bozMADI (SURVIVOR)"


def mutant_m2_test():
    """M2: madde sinirini 'bir sonraki `- `' yerine 'blok sonu' yap.

    Yani `_maddeleri_isle()` icindeki `not govde[j].startswith("- ")` kosulu
    kaldirilir; boylece ilk madde blogun tum govdesini yutar. Kapali+acik
    karisik bir maddede veto devreye girer ve hicbir madde tasinmaz.
    V4 (cok satirli kapali tasinmali) ve V6 (son kapali tasinmali) kirilir.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    eski = "    while j < n and not govde[j].startswith(\"- \"):\n"
    yeni = "    while j < n:  # mutant M2: madde siniri blok sonu\n"
    if eski not in govde:
        return None, "MUTANT CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    sonuclar = []
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-m2.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        # V4 fiksturu — M2 ile tasinmamali (komsu acik ile karisip veto).
        defter_v4 = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔧 **K2:** acik satir 1\n"
            "- ✅ **K1 KAPANDI** detay\n"
            "  devam satiri 2\n"
            "  devam satiri 3\n"
            "- 🔧 **K4:** diger acik satir 1\n"
        )
        rc, stdout, _, _ = _yaz_ve_calistir(tmp, defter_v4)
        v4_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
        sonuclar.append(("V4", v4_madde, 0, "cok satirli kapali M2 ile tasindi"))

        # V6 fiksturu — son kapali M2 ile tasinmamali.
        defter_v6 = (
            "## B — ACIK KALEMLER 🔴\n"
            "- ✅ **K_last KAPANDI** detay\n"
            "\n"
            "## C — SONRAKI BLOG 🔴\n"
            "- acik icerik\n"
        )
        rc, stdout, _, _ = _yaz_ve_calistir(tmp, defter_v6)
        v6_madde = _son_satirdaki_sayiyi_al(stdout, "TASINAN_MADDE")
        sonuclar.append(("V6", v6_madde, 0, "son kapali M2 ile tasindi"))

    kirildi = sum(1 for _, g, b, _ in sonuclar if g != b)
    toplam = len(sonuclar)
    if kirildi >= 1:
        return True, "M2 V4/V6'yi bozdu (%d/%d): %s" % (
            kirildi, toplam,
            "; ".join("%s g=%d b=%d" % (ad, g, b) for ad, g, b, _ in sonuclar))
    return False, "M2 hicbir vakayi bozMADI (SURVIVOR)"


def mutant_m3_test():
    """M3: bayt esitligi kontrolunu no-op yap -> her rotasyon rollback.

    `_dogru` ifadesi `False` ile degistirilir; boylece her transferden
    sonra dosyalar geri yazilir. V1 (kapali madde tasinmali), V5 (blok
    tasinmali) gibi rotasyon bekleyen vakalardan en az biri kirilir.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    # Eski: cok satirli `dogru = (...)` formunu hedefliyoruz; kaynak
    # kodda tek satir halinde `dogru = (` ile basliyor.
    eski = "    dogru = (\n"
    yeni = "    dogru = (False)  # mutant M3: bayt esitligi no-op\n        and False\n"
    if eski not in govde:
        return None, "MUTANT M3 CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    sonuclar = []
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-m3.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        # V1 fiksturu — kapali madde M3 ile arsive GECMEMELI (rollback).
        defter_v1 = (
            "## B — ACIK KALEMLER 🔴\n"
            "- 🔴 genel acik\n"
            "- ✅ **K1 KAPANDI** detay\n"
        )
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(defter_v1)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        r = subprocess.run(
            [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
            capture_output=True, text=True)
        v1_madde = _son_satirdaki_sayiyi_al(r.stdout, "TASINAN_MADDE")
        yeni_defter = open(defter, encoding="utf-8").read()
        v1_arsivde = "K1 KAPANDI" in open(arsiv, encoding="utf-8").read()
        # Beklenen: rollback oldu icin K1 KAPANDI arsive gecmedi VE
        # TASINAN_MADDE=0 yazildi (cikti satirinda). Aralarin hepsi
        # bos; bunlar transfer-sinyalleri.
        sonuclar.append(("V1", v1_madde, 0, v1_arsivde))

        # Mevcut F1 fiksturu — A ve C bloglari tasinmali. M3 ile hicbiri
        # tasinmamali.
        defter_f1 = _fikstur_defter()
        defter2 = os.path.join(tmp, "DEVAM.md")
        arsiv2 = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter2, "w", encoding="utf-8") as f:
            f.write(defter_f1)
        with open(arsiv2, "w", encoding="utf-8") as f:
            f.write("## Eski arsiv basligi\n- Eski kayit\n")
        r2 = subprocess.run(
            [sys.executable, mutant_yol, defter2, arsiv2, "--tarih", "2026-08-16"],
            capture_output=True, text=True)
        yeni_arsiv_f1 = open(arsiv2, encoding="utf-8").read()
        f1_tasindi = ("A — OTURUM KAPANISI" in yeni_arsiv_f1 or
                      "C — X KAPANDI" in yeni_arsiv_f1)
        sonuclar.append(("F1", f1_tasindi, True, False))

    kirildi = sum(1 for _, g, b, _ in sonuclar if g != b)
    toplam = len(sonuclar)
    if kirildi >= 1:
        return True, "M3 vakalari bozdu (%d/%d): %s" % (
            kirildi, toplam,
            "; ".join("%s g=%r b=%r" % (ad, g, b) for ad, g, b, _ in sonuclar))
    return False, "M3 hicbir vakayi bozMADI (SURVIVOR)"


def mutant_m4_test():
    """M4: arsiv veto kaldirilirsa -> V7 (arsiv indeksi) tasinir.

    `_madde_arsiv_vetolu` no-op edilir; boylece
    `- KAPANDI (arsivde): K91 · K101.` satiri kapama isaretcisi
    tasiyan bir madde olarak tasinir. V7 beklenen sonucunu (TASINMAZ)
    kaybeder.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    eski = ("    kucuk = metin.lower()\n"
            "    return any(d in kucuk for d in MADDE_VETO_DESENLERI)\n")
    yeni = "    return False  # M4 mutant: arsiv veto no-op\n"
    if eski not in govde:
        return None, "MUTANT M4 CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-m4.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        # V7 fiksturu — arsiv indeksi satir. M4 ile bu madde tasinmali
        # (veto kalktigi icin KAPANDI yakalar).
        defter_v7 = (
            "## B — ACIK KALEMLER 🔴\n"
            "- KAPANDI (arsivde): K91 · K101.\n"
        )
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(defter_v7)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        r = subprocess.run(
            [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
            capture_output=True, text=True)
        if r.returncode != 0:
            return None, "M4 mutant rc=%d (calistirilamadi)" % r.returncode
        v7_madde = _son_satirdaki_sayiyi_al(r.stdout, "TASINAN_MADDE")
        if v7_madde == 1:
            return True, "M4 V7'yi bozdu (TASINAN_MADDE=1; arsiv indeksi tasindi)"
        return False, "M4 V7'yi bozMADI (SURVIVOR, TASINAN_MADDE=%d)" % v7_madde


def mutant_m5_test():
    """M5: kelime-siniri kaldirilirsa -> V8 (ACIKLAMA) yanlislikla tasinmaz.

    `_HARF_JETON_RE` icindeki `\b...\b` kelime sinirlari kaldirilir;
    boylece ACIK jetonu alt-dize olarak aranir ve ACIKLAMA kelimesi
    yanlis veto tetikler. V8 (ACIKLAMA iceren kapali blok TASINIR)
    bu mutant ile TASINMAZ.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    eski = ("_HARF_JETON_RE = re.compile(\n"
            "    r\"\\b(?:\" + \"|\".join(\n"
            "        re.escape(j) for j in ACIK_ISARETCILER if any(c.isalpha() for c in j)\n"
            "    ) + r\")\\b\"\n"
            ")\n")
    yeni = ("_HARF_JETON_RE = re.compile(\n"
            "    r\"(?:\" + \"|\".join(\n"
            "        re.escape(j) for j in ACIK_ISARETCILER if any(c.isalpha() for c in j)\n"
            "    ) + r\")\"  # M5 mutant: \\b kelime sinirlari kaldirildi\n"
            ")\n")
    if eski not in govde:
        return None, "MUTANT M5 CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-m5.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        # V8 fiksturu — ACIKLAMA iceren kapali blok. M5 ile ACIKLAMA
        # "ACIK" alt-dizesini yanlislikla veto eder ve blok TASINMAZ.
        defter_v8 = (
            "## D — Y KAPANDI ✅\n"
            "- ACIKLAMA: is bitti, ek bilgi.\n"
        )
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(defter_v8)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        r = subprocess.run(
            [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
            capture_output=True, text=True)
        if r.returncode != 0:
            return None, "M5 mutant rc=%d (calistirilamadi)" % r.returncode
        v8_blok = _son_satirdaki_sayiyi_al(r.stdout, "TASINAN")
        if v8_blok == 0:
            return True, "M5 V8'i bozdu (TASINAN=0; ACIKLAMA yuzunden blok tasinmadi)"
        return False, "M5 V8'i bozMADI (SURVIVOR, TASINAN=%d)" % v8_blok


def mutant_m6_test():
    """M6: konum sarti no-op (yine 'metinde herhangi bir yerde') -> V10/V11 KIRMIZI.

    `_ilk_satirda_kapanis` govdesini eski davranisa (substring arama)
    donusturur; boylece K128 konum sarti baypas edilir ve V10 (`- 🔧 Eski
    yedek...` devam satirinda `KAPANDI` atfi olan ACIK madde) ile V11
    (`- Bu is devam ediyor; K91 KAPANDI diye...` kapanis ortada) yanlis
    tasinir. V10/V11 beklenen sonucunu (TASINMAZ) kaybeder.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    # M6 capa: `_ilk_satirda_kapanis` icindeki tek-return `if not ...: return False`.
    # Bu satiri silip yerine eski davranis (substring arama) koy.
    eski = "    if not _ilk_satirda_kapanis(metin):\n        return False\n"
    yeni = ("    # M6 mutant: konum sarti no-op; eski substring arama.\n"
            "    for _isaretci in KAPANIS_ISARETCILER:\n"
            "        if _isaretci in metin:\n"
            "            return True\n"
            "    return False\n")
    if eski not in govde:
        return None, "MUTANT M6 CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    sonuclar = []
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-m6.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        # V10 fiksturu — Eski yedek Okan kalemi. M6 ile devam satiri
        # parantezindeki KAPANDI yakalar ve madde TASINIR (yanlis).
        defter_v10 = (
            "## OKAN'DA\n"
            "- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum "
            "eylemi silme karari.\n"
            "  (Motor tarifesi kalemi 16 Agu'da KAPANDI: kimi + minimax-m3 "
            "ust aboneligine gecildi.)\n"
        )
        def _calistir_mutantla(defter_icerik, arsiv_icerik=""):
            defter = os.path.join(tmp, "DEVAM.md")
            arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
            with open(defter, "w", encoding="utf-8") as f:
                f.write(defter_icerik)
            with open(arsiv, "w", encoding="utf-8") as f:
                f.write(arsiv_icerik)
            r = subprocess.run(
                [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
                capture_output=True, text=True)
            if r.returncode != 0:
                return None
            return _son_satirdaki_sayiyi_al(r.stdout, "TASINAN_MADDE")

        # V10 fiksturu — Eski yedek Okan kalemi. Ilk satirda � acik
        # jetonu var; `_acik_eslesiyor` once devreye girer. M6 ile bile
        # madde TASINMAZ — V10 bu mutant ile ayirt edilEMEZ. V11 ile
        # birlikte degerlendirilir.
        defter_v10 = (
            "## OKAN'DA\n"
            "- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum "
            "eylemi silme karari.\n"
            "  (Motor tarifesi kalemi 16 Agu'da KAPANDI: kimi + minimax-m3 "
            "ust aboneligine gecildi.)\n"
        )
        v10_madde = _calistir_mutantla(defter_v10)
        if v10_madde is None:
            return None, "M6 mutant V10 calistirilamadi"
        sonuclar.append(("V10", v10_madde, 0, "Eski yedek M6 ile tasindi"))

        # V11 fiksturu — kapanis ortada, ACIK jetonu yok. M6 ile KAPANDI
        # substring'i yakalar ve madde TASINIR (yanlis).
        defter_v11 = (
            "## B — ACIK KALEMLER\n"
            "- Bu is devam ediyor; K91 KAPANDI diye referans veriyoruz.\n"
        )
        v11_madde = _calistir_mutantla(defter_v11)
        if v11_madde is None:
            return None, "M6 mutant V11 calistirilamadi"
        sonuclar.append(("V11", v11_madde, 0, "kapanis ortada M6 ile tasindi"))

    kirildi = sum(1 for _, g, b, _ in sonuclar if g != b)
    toplam = len(sonuclar)
    if kirildi >= 1:
        return True, "M6 V10/V11'i bozdu (%d/%d): %s" % (
            kirildi, toplam,
            "; ".join("%s g=%d b=%d" % (ad, g, b) for ad, g, b, _ in sonuclar))
    return False, "M6 hicbir vakayi bozMADI (SURVIVOR)"


def mutant_m7_test():
    """M7: gorunurluk basimini sil -> V14 KIRMIZI.

    `TASINAN-BLOK` ve `TASINAN-MADDE` basimini iceren 6-satirlik blogu
    bosaltir; boylece operator ne gittigini GOREMEZ. V14 beklenen
    sonucunu (tasima kosumunda `TASINAN-MADDE:` satiri VAR) kaybeder.
    """
    with open(ROTASYON, encoding="utf-8") as f:
        govde = f.read()

    # M6 capa: gorunurluk basim blogu — `for` dongusu + iki `print`.
    eski = (
        "    for blok in tasinacak_bloklar:\n"
        "        print(\"TASINAN-BLOK: %s\" % blok[\"baslik\"])\n"
        "    for madde in tasinacak_maddeler:\n"
        "        ilk = madde.split(\"\\n\", 1)[0]\n"
        "        if len(ilk) > 100:\n"
        "            ilk = ilk[:100]\n"
        "        print(\"TASINAN-MADDE: %s\" % ilk)\n"
    )
    yeni = "    # M7 mutant: gorunurluk basimi silindi\n"
    if eski not in govde:
        return None, "MUTANT M7 CAPA BULUNAMADI: %r" % eski

    mutant_govde = govde.replace(eski, yeni, 1)
    with tempfile.TemporaryDirectory() as tmp:
        mutant_yol = os.path.join(tmp, "mutant-m7.py")
        _mutant_taban_kopyala(tmp)
        with open(mutant_yol, "w", encoding="utf-8") as f:
            f.write(mutant_govde)

        # V14 fiksturu — tasima olan kosum. M7 ile stdout'ta
        # `TASINAN-MADDE:` satiri YAZILMAZ.
        defter_v14 = (
            "## B — ACIK KALEMLER 🔴\n"
            "- ✅ **K1 KAPANDI** detay metni\n"
            "  devam satiri 2\n"
        )
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(defter_v14)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        r = subprocess.run(
            [sys.executable, mutant_yol, defter, arsiv, "--tarih", "2026-08-16"],
            capture_output=True, text=True)
        if r.returncode != 0:
            return None, "M7 mutant rc=%d (calistirilamadi)" % r.returncode
        tasinan_satirlari = [
            s for s in (r.stdout or "").splitlines()
            if s.startswith("TASINAN-MADDE:")
        ]
        if len(tasinan_satirlari) == 0:
            return True, "M7 V14'u bozdu (TASINAN-MADDE: satiri YOK; gorunurluk sustu)"
        return False, "M7 V14'u bozMADI (SURVIVOR, %d sat)" % len(tasinan_satirlari)


# ---------------------------------------------------------------------------
# RED PROVASI (pre-commit)
# ---------------------------------------------------------------------------
def _git(kok, args, capture=True, env=None):
    # KANONIK sentetik git (fikstur-git-sizinti-kapisi sozlesmesi): miras GIT_*
    # kesif baglami scrub'lanir; cagri yerinin env'i ek_ortam olarak biner
    # (kesif adlari ek_ortam'dan da ayiklanir — git_ortami.sentetik_git).
    from git_ortami import sentetik_git
    return sentetik_git(kok, *args, ek_ortam=env,
                        capture_output=capture, text=True)


def _devam_olustur(tmp, satir):
    yol = os.path.join(tmp, "DEVAM.md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("# Defter\n")
        for i in range(1, satir):
            f.write("- Satir %d\n" % i)
    return yol


MINIMAL_PRE_COMMIT = """#!/bin/sh
# Test kancasi: yalnizca defter kota kolunu calistirir.
pruvo_kok=$(git rev-parse --show-toplevel 2>/dev/null)
python3 "$pruvo_kok/tools/defter-kota-kapisi.py" "$pruvo_kok"
pruvo_defter_kota_rc=$?
if [ "$pruvo_defter_kota_rc" -ne 0 ]; then
  exit 1
fi
exit 0
"""


def _sentetik_depo(tmp, sayac_yol):
    _git(tmp, ["init", "-q", "-b", "main"], capture=False)
    _git(tmp, ["config", "user.email", "test@ornek.gecersiz"], capture=False)
    _git(tmp, ["config", "user.name", "Test Kullanici"], capture=False)
    # Kanca icin sadece defter-kota-kapisi.py'yi tools altina koy.
    kanca_tools = os.path.join(tmp, "tools")
    os.makedirs(kanca_tools, exist_ok=True)
    shutil.copy(os.path.join(TOOLS, "defter-kota-kapisi.py"),
                os.path.join(kanca_tools, "defter-kota-kapisi.py"))
    # K178: tek kaynaktan (defter-kota-taban.py) okuyan kapinin de ihtiyaci.
    taban_yol = os.path.join(TOOLS, "defter-kota-taban.py")
    if os.path.exists(taban_yol):
        shutil.copy(taban_yol, os.path.join(kanca_tools, "defter-kota-taban.py"))
    kanca_dizin = os.path.join(tmp, ".git", "hooks")
    os.makedirs(kanca_dizin, exist_ok=True)
    kanca_yol = os.path.join(kanca_dizin, "pre-commit")
    with open(kanca_yol, "w", encoding="utf-8") as f:
        f.write(MINIMAL_PRE_COMMIT)
    os.chmod(kanca_yol, 0o755)
    # Betigin kendi ROOT'unu sentetik depo olarak gormesi icin ortam degiskeni.
    os.environ["PRUVO_DEFTER_KOTA_SAYAC"] = sayac_yol
    return tmp


def red_provasi():
    with tempfile.TemporaryDirectory() as tmp:
        sayac_yol = os.path.join(tmp, "bypass.tsv")
        _sentetik_depo(tmp, sayac_yol)

        # README.md ilk commit
        with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("# depo\n")
        _git(tmp, ["add", "README.md"], capture=False)
        _git(tmp, ["commit", "-q", "-m", "ilk"], capture=False)

        # RED vakasi: 131 satirlik DEVAM.md staged
        _devam_olustur(tmp, 131)
        _git(tmp, ["add", "DEVAM.md"], capture=False)
        r_red = _git(tmp, ["commit", "-m", "red test"])

        # KONTROL vakasi: 129 satirlik DEVAM.md staged
        _devam_olustur(tmp, 129)
        _git(tmp, ["add", "DEVAM.md"], capture=False)
        r_kontrol = _git(tmp, ["commit", "-m", "kontrol test"])

        # KAPSAM vakasi: 131 satirlik DEVAM.md stage disi, baska dosya commit
        _devam_olustur(tmp, 131)
        with open(os.path.join(tmp, "diger.txt"), "w", encoding="utf-8") as f:
            f.write("baska dosya\n")
        _git(tmp, ["add", "diger.txt"], capture=False)
        r_kapsam = _git(tmp, ["commit", "-m", "kapsam test"])

        sayac_satir = 0
        if os.path.exists(sayac_yol):
            with open(sayac_yol, encoding="utf-8") as f:
                sayac_satir = sum(1 for _ in f)

        return r_red, r_kontrol, r_kapsam, sayac_yol, sayac_satir


def main():
    hatalar, kontrol = fikstur_test()
    madde_hatalar, madde_gecen, madde_kontrol = madde_test()
    hatalar.extend(madde_hatalar)
    kontrol += madde_kontrol
    tavan_hatalar, tavan_gecen, tavan_kontrol = tavan_test()
    hatalar.extend(tavan_hatalar)
    kontrol += tavan_kontrol

    mutant_oldu, mutant_mesaj = mutant_test()
    mutant_m2_oldu, mutant_m2_mesaj = mutant_m2_test()
    mutant_m3_oldu, mutant_m3_mesaj = mutant_m3_test()
    mutant_m4_oldu, mutant_m4_mesaj = mutant_m4_test()
    mutant_m5_oldu, mutant_m5_mesaj = mutant_m5_test()
    mutant_m6_oldu, mutant_m6_mesaj = mutant_m6_test()
    mutant_m7_oldu, mutant_m7_mesaj = mutant_m7_test()

    r_red, r_kontrol, r_kapsam, sayac_yol, sayac_satir = red_provasi()

    red_rc = r_red.returncode
    kontrol_rc = r_kontrol.returncode
    kapsam_rc = r_kapsam.returncode
    cikti = (r_red.stdout or "") + (r_red.stderr or "")
    care_var = "VAR" if "DEFTER KOTASI ASILDI" in cikti and "CARE:" in cikti else "YOK"

    for h in hatalar:
        print("  ✗ %s" % h, file=sys.stderr)

    # RED provasi iddialari
    if red_rc == 0:
        print("  ✗ RED vakasi RED vermedi (rc=0)", file=sys.stderr)
        hatalar.append("RED vakasi RED vermedi")
    if kontrol_rc != 0:
        print("  ✗ KONTROL vakasi yanlis-pozitif (rc=%d): %s" % (
            kontrol_rc, r_kontrol.stderr), file=sys.stderr)
        hatalar.append("KONTROL vakasi yanlis-pozitif")
    if kapsam_rc != 0:
        print("  ✗ KAPSAM vakasi stage-disini engelledi (rc=%d): %s" % (
            kapsam_rc, r_kapsam.stderr), file=sys.stderr)
        hatalar.append("KAPSAM vakasi stage-disini engelledi")
    if care_var != "VAR":
        print("  ✗ CARE satiri yok; RED ciktisi: %s" % cikti, file=sys.stderr)
        hatalar.append("CARE satiri yok")
    if sayac_satir < 1:
        print("  ✗ Bypass sayaci yazilmadi (%s)" % sayac_yol, file=sys.stderr)
        hatalar.append("bypass sayaci yazilmadi")

    # Mutant durumlari
    mutant_durum = "OLDU" if mutant_oldu else "SURVIVOR"
    m2_durum = "OLDU" if mutant_m2_oldu else "SURVIVOR"
    m3_durum = "OLDU" if mutant_m3_oldu else "SURVIVOR"
    m4_durum = "OLDU" if mutant_m4_oldu else "SURVIVOR"
    m5_durum = "OLDU" if mutant_m5_oldu else "SURVIVOR"
    m6_durum = "OLDU" if mutant_m6_oldu else "SURVIVOR"
    m7_durum = "OLDU" if mutant_m7_oldu else "SURVIVOR"
    mutant_oldu_toplam = sum(1 for x in (
        mutant_oldu, mutant_m2_oldu, mutant_m3_oldu,
        mutant_m4_oldu, mutant_m5_oldu,
        mutant_m6_oldu, mutant_m7_oldu,
    ) if x)
    mutant_toplam = 7

    gecen = kontrol - len(hatalar)
    print("FIKSTUR=%d/%d YENI_VAKA=%d/%d MUTANT=%s,M2=%s,M3=%s,M4=%s,M5=%s,M6=%s,M7=%s(%d/%d) RED_RC=%d KONTROL_RC=%d KAPSAM_RC=%d CARE_SATIRI=%s SAYAC_YOL=%s SAYAC_SATIR=%d"
          % (gecen, kontrol, madde_gecen, madde_kontrol,
             mutant_durum, m2_durum, m3_durum, m4_durum, m5_durum,
             m6_durum, m7_durum,
             mutant_oldu_toplam, mutant_toplam,
             red_rc, kontrol_rc, kapsam_rc, care_var, sayac_yol, sayac_satir))

    if hatalar:
        if not mutant_oldu:
            print("M1 MUTANT DETAY: %s" % mutant_mesaj, file=sys.stderr)
        if not mutant_m2_oldu:
            print("M2 MUTANT DETAY: %s" % mutant_m2_mesaj, file=sys.stderr)
        if not mutant_m3_oldu:
            print("M3 MUTANT DETAY: %s" % mutant_m3_mesaj, file=sys.stderr)
        if not mutant_m4_oldu:
            print("M4 MUTANT DETAY: %s" % mutant_m4_mesaj, file=sys.stderr)
        if not mutant_m5_oldu:
            print("M5 MUTANT DETAY: %s" % mutant_m5_mesaj, file=sys.stderr)
        if not mutant_m6_oldu:
            print("M6 MUTANT DETAY: %s" % mutant_m6_mesaj, file=sys.stderr)
        if not mutant_m7_oldu:
            print("M7 MUTANT DETAY: %s" % mutant_m7_mesaj, file=sys.stderr)
        return 1
    if mutant_oldu_toplam < mutant_toplam:
        if not mutant_oldu:
            print("M1 MUTANT DETAY: %s" % mutant_mesaj, file=sys.stderr)
        if not mutant_m2_oldu:
            print("M2 MUTANT DETAY: %s" % mutant_m2_mesaj, file=sys.stderr)
        if not mutant_m3_oldu:
            print("M3 MUTANT DETAY: %s" % mutant_m3_mesaj, file=sys.stderr)
        if not mutant_m4_oldu:
            print("M4 MUTANT DETAY: %s" % mutant_m4_mesaj, file=sys.stderr)
        if not mutant_m5_oldu:
            print("M5 MUTANT DETAY: %s" % mutant_m5_mesaj, file=sys.stderr)
        if not mutant_m6_oldu:
            print("M6 MUTANT DETAY: %s" % mutant_m6_mesaj, file=sys.stderr)
        if not mutant_m7_oldu:
            print("M7 MUTANT DETAY: %s" % mutant_m7_mesaj, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
