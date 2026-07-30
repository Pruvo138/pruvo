#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IKI GOVDE GEOMETRI OLCUMU — 2-renk yazi sozlesmesinin MESH kaniti.

🔴 OPENSCAD GEREKTIRIR (yalniz --url kipi): bu betigin OLCUM kipi CALISAN bir
derleyiciye (onizleme/derleyici/server.py ya da CI'da imajin konteyneri) HTTP ile
konusur. Gelistirme Mac'inde openscad SIGABRT verdigi icin YEREL KOSULMAZ; yeri
.github/workflows/onizleme-imaj.yml (imaj duman adiminin hemen ardindan, konteyner
ayaktayken).
`--kendini-test` kipi AG/OPENSCAD ISTEMEZ: iddia mantigi FIKSTUR sayilarla surulur
(bkz. kendini_test) ve --url kipinin ICINDEN de BLOKLAYICI olarak cagrilir.

NE OLCER (ucgen/bbox/hacim — hepsi GERCEK mesh uzerinde):
  1. AYRISMA
     1a yazi govdesinin ucgen sayisi > 0 (yazi GERCEKTEN ayri bir govde).
     1b govde (yazisiz) mesh'inde z > Frame_Depth+tol ucgen YOK (yazi orada DEGIL).
     1c govde mesh'i, taban ailenin Caption_Text="" haliyle BIREBIR AYNI (ayni SHA-256):
        cerceve.scad'de Caption_Fit="existing" oldugu icin dis olcu yazidan bagimsiz —
        yani "yazisiz cerceve" tanimi TEK ve tutarli.
  2. HIZALAMA (kaydirma SIFIR)
     2a yazi bbox'inin x/y araligi govde bbox'inin x/y araliginin ICINDE.
     2b yazi z_min ile govde z_max farki, uretecin bilincli boolean bindirmesine
        (0,02 mm) TAM ESIT -> yazi govdenin UST YUZUNE oturur, havada/gomulu degil.
     2c iki govdenin ORTAK bbox'i, tek govdeli (Output="frame") mesh'in bbox'i ile
        AYNI (tol 1e-3 mm): birlesim, tek govdenin isgal ettigi hacmi asmaz/eksiltmez.
     2d yazinin TEPESI govdenin ust yuzunun USTUNDE (kabartma GERCEKTEN var; yazi
        govdenin icine gomulu ya da sifir yukseklikli degil).
  3. ESDEGERLIK (hacim — polihedral katinin hacmi UCGENLEMEDEN BAGIMSIZDIR)
     3a hacim: V(govde) + V(yazi) - V(bindirme) ~= V(tek govde), bagil sapma <= 1e-4.
        V(bindirme) ust sinirini yazi tabani alani x 0,02 mm ile tahmin ederiz.
     3b V(govde) < V(tek) < V(govde) + V(yazi): birlesim govdeyi KAPSAR (yani yazi
        birlesime GIRMIS) ve bindirme > 0 oldugu icin toplamdan KUCUKTUR.
     3c 0 < V(bindirme) <= V(yazi): bindirme TAHMIN EDICISI (yazi_taban_alani x 0,02)
        anlamli bir deger uretiyor. Bu iddia 3a'yi MASKELEMEYE karsi korur — sisirilmis
        bir V(bindirme) 3a'yi sahte-yesil yakabilirdi.
  4. BELIRLENIMCILIK / METIN BAGLANTISI
     4a ayni yazi -> ayni SHA (her uc cikti icin).
     4b farkli yazi -> yazi govdesi DEGISIR; govde (yazisiz) DEGISMEZ.
  5. GERIYE DONUK UYUM
     5a Output="frame" (parcasiz) ciktisi, --taban-sha ile verilen referansla AYNI
        (referans verilmezse bu iddia ATLANIR ve rapora "OLCULEMEDI" yazilir).

🔴 KALDIRILAN IDDIA — GERI KOYMAYIN (mimar karari 30 Tem 2026):
    "3b tek govde ucgen sayisi <= govde + yazi toplami"
  Bu iddia MATEMATIKSEL OLARAK YANLISTI ve ilk gercek icrasinda (betik + CI cagrisi
  ayni commit'te geldigi icin bugune dek HIC kosmamisti) KIRMIZI yandi:
    olculen -> tek=1696 ucgen, govde+yazi=1304+384=1688 ucgen; 1696 <= 1688 DEGIL
    (+8 ucgen, %0,47) — IMAJ SAGLAMDI (/saglik 25 aileyi #govde/#yazi dahil listeledi).
  Sebep: CGAL/OpenSCAD birlesiminde yazinin ayak izi cercevenin UST YUZUYLE kesisir;
  o yuz kesisim egrisi boyunca YENIDEN UCGENLENIR ve facet EKLEYEBILIR.
  Neden "payli sinir" da konmadi: ucgen sayisi bir MESHER ARTEFAKTIDIR, geometrik
  degismez degil. "8 facet payi" gibi bir sihirli sayi OpenSCAD/CGAL surumu ya da
  geometri degisince kayar ve gelecekte TUM EKIBIN yayinini durduran sahte kirmizi
  uretir. Yerine 3a SIKILASTIRILDI (5e-3 -> 1e-4), 3b/3c/2d eklendi ve 2b paylı
  araliktan TAM ESITLIGE cevrildi — hepsi ucgenlemeden BAGIMSIZ olculer.
  (kendini_test icinde `eski_3b_geri_gelmemeli()` bu predikatin gercek sayilarla
   KIRMIZI oldugunu her kosumda olcer.)

NE OLCMEZ: onbellek anahtarini/worker yonlendirmesini (onizleme/test/iki-govde-kabul.mjs),
eslem/-D tarafini (tools/iki-govde-kapisi.py), baskinin fiziksel yapismasini, fiyati.

Kullanim:
  python3 onizleme/test/iki-govde-olcum.py --url http://127.0.0.1:18080
  python3 onizleme/test/iki-govde-olcum.py --url ... --taban-sha <sha256>
  python3 onizleme/test/iki-govde-olcum.py --kendini-test     # AGSIZ, openscad'siz
"""
import argparse
import hashlib
import json
import struct
import sys
import urllib.request

AILE = "olcuye-ozel-cerceve"
PARAM = {"acilik_eni": 100, "acilik_boyu": 150, "kenar_genisligi": 12,
         "derinlik": 5.2, "kenar_stili": "chamfer", "yazi": "OKAN"}
PARAM_B = dict(PARAM, yazi="ZZZZZZZZ")
DERINLIK = PARAM["derinlik"]
BINDIRME = 0.02          # cerceve.scad _Boolean_Overlap
TOL = 1e-3               # uzunluk toleransi (mm)

# HACIM TOLERANSI (bagil) — NEDEN 1e-4:
#   * OLCULEN sapma (30 Tem, gercek imaj): 33422,8 + 91,2 - 1,49 = 33512,51 ile
#     V(tek)=33512,5 arasinda bagil sapma 3,0e-7 -> 1e-4 esigin ~330 KATI altinda,
#     yani yanlis-pozitif payi genis.
#   * ALT SINIR (kacirmamasi gerekenler): yazi birlesime HIC girmezse sapma
#     91,2/33512,5 = 2,7e-3 (esigin 27 kati) -> YAKALANIR. Dort harfli fiksturde TEK
#     harf duserse ~22,8/33512,5 = 6,8e-4 (esigin ~7 kati) -> YAKALANIR.
#   * ESKI DEGER 5e-3 (%0,5) BUNLARIN IKISINI DE KACIRIYORDU: yazinin TAMAMEN
#     dusmesi bile 2,7e-3 < 5e-3 oldugu icin YESIL yanardi. Sikilastirmanin somut
#     kazanci budur.
#   * Neden daha da sikilmadi: hacim polihedral katida ucgenlemeden bagimsizdir ama
#     V(bindirme) bir UST SINIR TAHMINIDIR (yazi_taban_alani x 0,02) ve font
#     konturunun tessellasyonu OpenSCAD surumleri arasinda degisebilir. 1e-4 hem
#     olculen sapmanin 330 kati ustunde hem de tek-harf kaybini yakalar.
HACIM_TOL = 1e-4


def derle(url, aile, parametreler):
    govde = json.dumps({"aile": aile, "parametreler": parametreler}).encode("utf-8")
    istek = urllib.request.Request(url.rstrip("/") + "/derle", data=govde,
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=120) as c:
        return c.read()


def stl_coz(ham):
    """binary STL -> (ucgen listesi, sha256). Ucgen = 3 kose (x,y,z)."""
    adet = struct.unpack_from("<I", ham, 80)[0]
    if 84 + adet * 50 != len(ham):
        sys.exit("STL binary degil / bozuk (%d bayt, %d ucgen)" % (len(ham), adet))
    ucgenler = []
    o = 84
    for _ in range(adet):
        o += 12
        kose = []
        for _k in range(3):
            kose.append(struct.unpack_from("<3f", ham, o))
            o += 12
        o += 2
        ucgenler.append(kose)
    return ucgenler, hashlib.sha256(ham).hexdigest()


def bbox(ucgenler):
    az = [float("inf")] * 3
    cok = [float("-inf")] * 3
    for u in ucgenler:
        for p in u:
            for k in range(3):
                az[k] = min(az[k], p[k])
                cok[k] = max(cok[k], p[k])
    return az, cok


def hacim(ucgenler):
    """Kapali yuzeyin isaretli hacmi (tetrahedron toplami), mm^3."""
    t = 0.0
    for (a, b, c) in ucgenler:
        t += (a[0] * (b[1] * c[2] - b[2] * c[1])
              - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return abs(t) / 6.0


def yazi_taban_alani(ucgenler, z):
    """z duzlemine (yazi tabani) YAKIN, asagi bakan ucgenlerin alani — bindirme
    hacminin ust sinirini tahmin etmek icin."""
    toplam = 0.0
    for (a, b, c) in ucgenler:
        if max(a[2], b[2], c[2]) > z + 1e-3:
            continue
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = c[0] - a[0], c[1] - a[1]
        toplam += abs(ux * vy - uy * vx) / 2.0
    return toplam


# ---------------------------------------------------------------------------
# IDDIA CEKIRDEGI — SAF FONKSIYON (ag/dosya/openscad YOK).
# Boylece iddia mantigi FIKSTUR sayilarla (kendini_test) olculebilir; mesh uretimi
# CI'daki konteynerde kalir.
# ---------------------------------------------------------------------------
OLCUM_ALANLARI = (
    "ucgen_tek", "ucgen_govde", "ucgen_yazi", "ucgen_yazisiz", "ust_ucgen",
    "bbox_govde", "bbox_yazi", "bbox_tek",
    "hacim_tek", "hacim_govde", "hacim_yazi", "hacim_bindirme",
    "sha_tek", "sha_govde", "sha_yazi", "sha_yazisiz",
    "sha_yazi2", "sha_yaziB", "sha_govdeB",
)


def iddialari_olc(veri):
    """(iddialar, olculemedi) — iddialar = [(ad, kosul_bool, detay_metni), ...].

    FAIL-CLOSED: beklenen olcum alanlarindan biri EKSIKSE iddia listesi degil bir
    ValueError uretilir (eksik alan sessizce "yok sayilip" iddia atlanamaz)."""
    eksik = [a for a in OLCUM_ALANLARI if a not in veri]
    if eksik:
        raise ValueError("OLCUM ALANI EKSIK: %s -> iddia atlanamaz (fail-closed)"
                         % ", ".join(eksik))
    iddialar = []
    olculemedi = []

    def olc(ad, kosul, detay=""):
        iddialar.append((ad, bool(kosul), detay))

    gaz, gcok = veri["bbox_govde"]
    yaz, ycok = veri["bbox_yazi"]
    taz, tcok = veri["bbox_tek"]

    # 1) AYRISMA
    olc("1a yazi govdesi BOS DEGIL", veri["ucgen_yazi"] > 0,
        "%d ucgen" % veri["ucgen_yazi"])
    olc("1b govde mesh'inde yazi yuksekliginde ucgen YOK", veri["ust_ucgen"] == 0,
        "z>%.2f ucgen sayisi = %d" % (DERINLIK, veri["ust_ucgen"]))
    olc("1c govde == taban ailenin yazisiz hali (ayni SHA)",
        veri["sha_govde"] == veri["sha_yazisiz"],
        "govde=%s yazisiz=%s" % (veri["sha_govde"][:16], veri["sha_yazisiz"][:16]))

    # 2) HIZALAMA
    olc("2a yazi bbox'i govde bbox'inin x/y ICINDE",
        yaz[0] >= gaz[0] - TOL and ycok[0] <= gcok[0] + TOL and
        yaz[1] >= gaz[1] - TOL and ycok[1] <= gcok[1] + TOL,
        "yazi x[%.3f..%.3f] y[%.3f..%.3f] / govde x[%.3f..%.3f] y[%.3f..%.3f]"
        % (yaz[0], ycok[0], yaz[1], ycok[1], gaz[0], gcok[0], gaz[1], gcok[1]))
    # 🔴 SIKILASTIRILDI (30 Tem): eski hali `-BINDIRME-TOL <= fark <= TOL` idi, yani
    # ARALIK olcuyordu ve fark=0 (bindirme HIC UYGULANMAMIS, yazi yuze sadece TEGET)
    # halini de YESIL sayiyordu. Yeni iddia farkin uretecin TASARIM BINDIRMESINE
    # (cerceve.scad _Boolean_Overlap = 0,02) TAM ESIT olmasini ister.
    z_bosluk = yaz[2] - gcok[2]
    olc("2b yazi tabani govde ust yuzune TAM bindirme kadar gomulu",
        abs(z_bosluk + BINDIRME) <= TOL,
        "yazi z_min=%.4f  govde z_max=%.4f  fark=%.4f  beklenen=%.4f (tasarim "
        "bindirmesi)" % (yaz[2], gcok[2], z_bosluk, -BINDIRME))
    ortak_az = [min(gaz[k], yaz[k]) for k in range(3)]
    ortak_cok = [max(gcok[k], ycok[k]) for k in range(3)]
    olc("2c govde+yazi ORTAK bbox'i tek govdeninkiyle AYNI",
        all(abs(ortak_az[k] - taz[k]) <= TOL and abs(ortak_cok[k] - tcok[k]) <= TOL
            for k in range(3)),
        "ortak=[%s] tek=[%s]"
        % (", ".join("%.3f..%.3f" % (ortak_az[k], ortak_cok[k]) for k in range(3)),
           ", ".join("%.3f..%.3f" % (taz[k], tcok[k]) for k in range(3))))
    olc("2d yazi TEPESI govde ust yuzunun USTUNDE (kabartma var)",
        ycok[2] > gcok[2] + TOL,
        "yazi z_max=%.4f  govde z_max=%.4f  kabartma=%.4f mm"
        % (ycok[2], gcok[2], ycok[2] - gcok[2]))

    # 3) ESDEGERLIK — HACIM (ucgenlemeden BAGIMSIZ)
    v_tek, v_govde = veri["hacim_tek"], veri["hacim_govde"]
    v_yazi, v_bindirme = veri["hacim_yazi"], veri["hacim_bindirme"]
    beklenen = v_govde + v_yazi - v_bindirme
    sapma = abs(beklenen - v_tek) / max(abs(v_tek), 1e-9)
    olc("3a hacim esdegerligi V(govde)+V(yazi)-V(bindirme) ~= V(tek)",
        sapma <= HACIM_TOL,
        "tek=%.1f  govde=%.1f  yazi=%.1f  bindirme~%.2f  bagil sapma=%.7f%% "
        "(tol %.5f%%)" % (v_tek, v_govde, v_yazi, v_bindirme,
                          sapma * 100, HACIM_TOL * 100))
    olc("3b V(govde) < V(tek) < V(govde)+V(yazi) (birlesim govdeyi KAPSAR, bindirme>0)",
        v_govde < v_tek < v_govde + v_yazi,
        "%.1f < %.1f < %.1f" % (v_govde, v_tek, v_govde + v_yazi))
    olc("3c bindirme tahmini anlamli: 0 < V(bindirme) <= V(yazi)",
        0.0 < v_bindirme <= v_yazi,
        "bindirme=%.4f  yazi=%.1f" % (v_bindirme, v_yazi))

    # 4) BELIRLENIMCILIK / METIN BAGLANTISI
    olc("4a ayni yazi -> AYNI cikti (belirlenimcilik)",
        veri["sha_yazi2"] == veri["sha_yazi"], veri["sha_yazi"][:16])
    olc("4b farkli yazi -> YAZI govdesi degisir",
        veri["sha_yaziB"] != veri["sha_yazi"],
        "%s -> %s" % (veri["sha_yazi"][:12], veri["sha_yaziB"][:12]))
    olc("4c farkli yazi -> GOVDE (yazisiz) DEGISMEZ",
        veri["sha_govdeB"] == veri["sha_govde"], veri["sha_govde"][:16])

    # 5) GERIYE DONUK UYUM
    taban = veri.get("taban_sha")
    if taban:
        olc("5a Output=frame ciktisi referansla AYNI", veri["sha_tek"] == taban,
            "cari=%s referans=%s" % (veri["sha_tek"][:16], taban[:16]))
    else:
        olculemedi.append("5a geriye donuk SHA (--taban-sha verilmedi)")
    return iddialar, olculemedi


# ---------------------------------------------------------------------------
# KENDINI TEST — iddia mantigi FIKSTURLE olculur (openscad/ag YOK).
# ---------------------------------------------------------------------------
# FIKSTUR = 30 Tem 2026'da GERCEK imajda (konteyner ayakta, gercek openscad)
# olculen sayilar. Kaynak: mimarin ilettigi duman kosumu raporu.
#   ucgen        : tek=1696 · govde+yazi=1688 (govde 1304 + yazi 384)
#   hacim (mm^3) : tek=33512,5 · govde=33422,8 · yazi=91,2 · bindirme~1,49
#   hizalama     : yazi z_min - govde z_max = -0,0200 (tasarim bindirmesi 0,02)
# 🔴 DURUSTLUK BEYANI: ucgen TOPLAMI (1688) ve V(...) / hizalama degerleri RAPOR
# EDILEN GERCEK olcumlerdir. govde/yazi ucgen AYRIMI (1304/384) toplamdan ve ayri
# olculmus yazisiz-cerceve ucgen sayisindan (1304) turetilmistir. bbox koseleri ve
# SHA dizeleri rapor edilmedigi icin SENTETIKTIR: cerceve parametreleriyle (acilik
# 100x150, kenar 12 -> dis 124x174, derinlik 5,2) ve OLCULEN hizalama farkiyla
# (-0,0200 -> yazi z_min = 5,18) TUTARLI secildi. Iddia MANTIGI bunlarla olculur;
# gercek mesh olcumu CI'da (--url) yapilir.
FIKSTUR = {
    "ucgen_tek": 1696, "ucgen_govde": 1304, "ucgen_yazi": 384,
    "ucgen_yazisiz": 1304, "ust_ucgen": 0,
    "bbox_govde": ([-62.0, -87.0, 0.0], [62.0, 87.0, 5.2]),
    "bbox_yazi": ([-30.0, -80.5, 5.18], [30.0, -70.5, 6.38]),
    "bbox_tek": ([-62.0, -87.0, 0.0], [62.0, 87.0, 6.38]),
    "hacim_tek": 33512.5, "hacim_govde": 33422.8, "hacim_yazi": 91.2,
    "hacim_bindirme": 1.49,
    "sha_tek": "a" * 64, "sha_govde": "b" * 64, "sha_yazi": "c" * 64,
    "sha_yazisiz": "b" * 64,
    "sha_yazi2": "c" * 64, "sha_yaziB": "d" * 64, "sha_govdeB": "b" * 64,
    "taban_sha": None,
}


def _mutant(**degisiklik):
    yeni = dict(FIKSTUR)
    yeni.update(degisiklik)
    return yeni


# (ad, mutant_veri, KIRMIZI_yanmasi_beklenen_iddia_oneki)
MUTANTLAR = (
    # 1) HACIM KORUNUMU: yazi birlesime HIC girmedi (V(tek) = V(govde)). Gercek
    #    dunyadaki bicim: Output="frame" caption'i dusuruyor.
    ("hacim korunumu bozuldu — yazi birlesime girmedi (V(tek)=V(govde))",
     _mutant(hacim_tek=33422.8), "3a"),
    # 2) BBOX KAYDI: birlesimin bbox'i iki govdenin ortak bbox'undan BUYUK.
    ("bbox kaydi — tek govde bbox z_max sisti (6,38 -> 7,00)",
     _mutant(bbox_tek=([-62.0, -87.0, 0.0], [62.0, 87.0, 7.0])), "2c"),
    # 3) BBOX KAYDI (x/y): yazi cercevenin DISINA kaydi.
    ("bbox kaydi — yazi x araligi govdenin DISINA cikti (+40 mm)",
     _mutant(bbox_yazi=([10.0, -80.5, 5.18], [70.0, -70.5, 6.38])), "2a"),
    # 4) HIZALAMA: bindirme UYGULANMAMIS (fark 0). ⚠️ ESKI 2b ARALIK IDDIASI BU
    #    HALI YESIL SAYIYORDU (-0,02-tol <= 0 <= tol) -> sikilastirmanin somut kazanci.
    ("hizalama bindirmeden sapti — bindirme uygulanmamis (fark 0,0000)",
     _mutant(bbox_yazi=([-30.0, -80.5, 5.2], [30.0, -70.5, 6.4]),
             bbox_tek=([-62.0, -87.0, 0.0], [62.0, 87.0, 6.4])), "2b"),
    # 5) #govde SHA'si degisti -> yazisiz taban ile ayrisma.
    ("#govde SHA'si yazisiz tabandan ayristi",
     _mutant(sha_govde="e" * 64, sha_govdeB="e" * 64), "1c"),
    # 6) BELIRLENIMCILIK: ayni girdi iki farkli cikti.
    ("belirlenimcilik bozuldu — ayni yazi iki farkli SHA",
     _mutant(sha_yazi2="f" * 64), "4a"),
    # 7) METIN BAGLANTISI: farkli yazi ayni govdeyi uretti (29 Tem sessiz teslimat
    #    hatasinin ta kendisi).
    ("metin baglantisi koptu — farkli yazi AYNI yazi govdesi",
     _mutant(sha_yaziB="c" * 64), "4b"),
    # 8) KABARTMA YOK: yazi govdenin ust yuzunu asmiyor.
    ("kabartma yok — yazi tepesi govde ust yuzuyle ayni",
     _mutant(bbox_yazi=([-30.0, -80.5, 5.18], [30.0, -70.5, 5.2]),
             bbox_tek=([-62.0, -87.0, 0.0], [62.0, 87.0, 5.2])), "2d"),
    # 9) MASKELEME: bindirme tahmini sisirilirse 3a sahte-yesil yakabilirdi.
    ("bindirme tahmini sisti (yazidan buyuk) — 3a maskeleme denemesi",
     _mutant(hacim_bindirme=182.4), "3c"),
)


def eski_3b_predikati(veri):
    """KALDIRILAN IDDIA — eski ucgen-sayisi predikati. Iddia listesine GIRMEZ;
    yalnizca "gercek sayilarla KIRMIZI, yani geri koyulursa CI yanar" olcumu icin
    tutulur. Boylece kaldirma karari her kosumda GEREKCELENIR.

    veri disaridan gelir (sabit FIKSTUR'e kilitlenmez): kendini_test onu HEM gercek
    sayilarla (KIRMIZI beklenir) HEM sentetik bir karsi-ornekle (YESIL beklenir)
    surer -> govde `return False` gibi sabit bir degere cevrilirse karsi-ornek iddiasi
    duser (M-G kacagi kapatildi, olculdu 30 Tem)."""
    tek = veri["ucgen_tek"]
    toplam = veri["ucgen_govde"] + veri["ucgen_yazi"]
    return (tek <= toplam), "%d <= %d" % (tek, toplam)


def kendini_test(ayrintili=False):
    """(hatalar, iddia_sayisi) — iddia mantigi GERCEKTEN olcuyor mu.

    POZITIF: 30 Tem'de olculen gercek sayilarla TUM iddialar YESIL olmali.
    NEGATIF: 9 mutantin her biri BEKLENEN iddiayi KIRMIZI yakmali (govde no-op
    yapilirsa ya da bir iddia silinirse bunlar birden duser).
    KALDIRILAN IDDIA: eski ucgen predikati gercek sayilarla KIRMIZI olmali."""
    hatalar = []
    iddia = 0

    # POZITIF
    iddia += 1
    try:
        iddialar, olculemedi = iddialari_olc(FIKSTUR)
    except ValueError as e:
        return ["POZITIF OLCULEMEDI: %s" % e], iddia
    dusen = [a for a, k, d in iddialar if not k]
    if dusen:
        hatalar.append("POZITIF YANDI (YANLIS-POZITIF): gercek olculen sayilarla %d "
                       "iddia dustu -> %s" % (len(dusen), "; ".join(dusen)))
    if ayrintili:
        for ad, kosul, detay in iddialar:
            print(("  [OK ] " if kosul else "  [KIRMIZI] ") + ad
                  + (" -> " + detay if detay else ""))
        for o in olculemedi:
            print("  [OLCULEMEDI] " + o)

    # POZITIF-KAPSAM: iddia sayisi belli bir tabanin ALTINA dusmemeli (bir iddia
    # sessizce silinirse mutant listesi hala yesil kalabilir — bu iddia onu yakalar).
    iddia += 1
    if len(iddialar) < 13:
        hatalar.append("IDDIA SAYISI DUSTU: %d iddia olculdu, en az 13 bekleniyor "
                       "(1a/1b/1c · 2a/2b/2c/2d · 3a/3b/3c · 4a/4b/4c) -> bir iddia "
                       "silinmis olabilir" % len(iddialar))

    # FAIL-CLOSED: eksik alan sessizce atlanmamali.
    iddia += 1
    kirpik = dict(FIKSTUR)
    del kirpik["hacim_yazi"]
    try:
        iddialari_olc(kirpik)
        hatalar.append("FAIL-CLOSED DELIGI: eksik olcum alaniyla (hacim_yazi) iddia "
                       "olcumu HATA VERMEDI -> eksik veri sessizce yok sayilabilir")
    except ValueError:
        pass

    # NEGATIF
    for ad, mutant, beklenen_onek in MUTANTLAR:
        iddia += 1
        try:
            m_iddialar, _ = iddialari_olc(mutant)
        except ValueError as e:
            hatalar.append("NEGATIF OLCULEMEDI (%s): %s" % (ad, e))
            continue
        kirmizilar = [a for a, k, d in m_iddialar if not k]
        if not any(a.startswith(beklenen_onek) for a in kirmizilar):
            hatalar.append("NEGATIF SESSIZ: %r mutasyonunda %s iddiasi KIRMIZI "
                           "yanmadi (kirmizilar: %s) -> nobetci bu bicimde OLU"
                           % (ad, beklenen_onek, "; ".join(kirmizilar) or "YOK"))
        elif ayrintili:
            print("  [MUTANT KIRMIZI] %s -> %s" % (beklenen_onek, ad))

    # KALDIRILAN IDDIA — iki yon (predikat gercekten DEGERLENDIRILIYOR mu).
    iddia += 2
    eski_yesil, detay = eski_3b_predikati(FIKSTUR)
    karsi_yesil, karsi_detay = eski_3b_predikati(_mutant(ucgen_tek=1600))
    if eski_yesil:
        hatalar.append("KALDIRILAN IDDIA NOBETI BAYAT: eski ucgen predikati (%s) "
                       "gercek sayilarla YESIL -> fikstur degismis; kaldirma "
                       "gerekcesini yeniden olcun" % detay)
    if not karsi_yesil:
        hatalar.append("KALDIRILAN IDDIA NOBETI SABIT: eski predikat karsi-ornekte de "
                       "(%s) KIRMIZI dedi -> govde degerlendirilmiyor, sabit bir deger "
                       "donuyor olabilir" % karsi_detay)
    if not eski_yesil and karsi_yesil and ayrintili:
        print("  [KALDIRILAN 3b] gercek sayilarla KIRMIZI: %s -> geri koyulursa "
              "CI yanar" % detay)
    return hatalar, iddia


# ---------------------------------------------------------------------------
def olcumu_topla(url, taban_sha=None):
    """GERCEK derleyiciden (openscad) olcum toplar -> iddialari_olc() girdisi."""
    ham_tek = derle(url, AILE, PARAM)
    ham_govde = derle(url, AILE + "#govde", PARAM)
    ham_yazi = derle(url, AILE + "#yazi", PARAM)
    ham_yazisiz = derle(url, AILE, dict(PARAM, yazi=""))

    tek, sha_tek = stl_coz(ham_tek)
    govde, sha_govde = stl_coz(ham_govde)
    yazi, sha_yazi = stl_coz(ham_yazi)
    yazisiz, sha_yazisiz = stl_coz(ham_yazisiz)

    yaz, ycok = bbox(yazi)
    ust = [u for u in govde if max(p[2] for p in u) > DERINLIK + 1e-3]
    return {
        "ucgen_tek": len(tek), "ucgen_govde": len(govde), "ucgen_yazi": len(yazi),
        "ucgen_yazisiz": len(yazisiz), "ust_ucgen": len(ust),
        "bbox_govde": bbox(govde), "bbox_yazi": (yaz, ycok), "bbox_tek": bbox(tek),
        "hacim_tek": hacim(tek), "hacim_govde": hacim(govde),
        "hacim_yazi": hacim(yazi),
        "hacim_bindirme": yazi_taban_alani(yazi, yaz[2]) * BINDIRME,
        "sha_tek": sha_tek, "sha_govde": sha_govde, "sha_yazi": sha_yazi,
        "sha_yazisiz": sha_yazisiz,
        "sha_yazi2": hashlib.sha256(derle(url, AILE + "#yazi", PARAM)).hexdigest(),
        "sha_yaziB": hashlib.sha256(derle(url, AILE + "#yazi", PARAM_B)).hexdigest(),
        "sha_govdeB": hashlib.sha256(derle(url, AILE + "#govde", PARAM_B)).hexdigest(),
        "taban_sha": taban_sha,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="calisan derleyici (or. http://127.0.0.1:18080)")
    ap.add_argument("--taban-sha", help="Output=frame ciktisinin beklenen SHA-256 "
                                       "(geriye donuk uyum)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="iddia mantigini FIKSTURLE olcer (openscad/ag GEREKMEZ); "
                         "--url kipinin icinden de BLOKLAYICI olarak kosar")
    args = ap.parse_args()

    # 🔴 TEK CAGRI NOKTASI: kendini_test() BURADA cagrilir ve iki kol da bu sonucu
    # kullanir -> `--kendini-test` adimi silinse bile bloklayici (--url) kolda yasar.
    kt_hata, kt_iddia = kendini_test(ayrintili=args.kendini_test)

    if args.kendini_test:
        print("IKI GOVDE OLCUMU — IDDIA MANTIGI KENDINI TESTI (%d iddia)" % kt_iddia)
        if kt_hata:
            for h in kt_hata:
                print("  ❌ " + h)
            print("SONUC: KIRMIZI ❌")
            return 1
        print("  ✅ POZITIF: 30 Tem'de olculen GERCEK sayilarla 13 iddia YESIL")
        print("  ✅ NEGATIF: %d mutant beklenen iddiayi KIRMIZI yakiyor" % len(MUTANTLAR))
        print("  ✅ FAIL-CLOSED: eksik olcum alani sessizce yok sayilmiyor")
        print("  ✅ KALDIRILAN 3b: eski ucgen predikati gercek sayilarla KIRMIZI")
        print("SONUC: YESIL ✅")
        return 0

    if not args.url:
        print("--url ya da --kendini-test verin.")
        return 2

    hatalar = []
    for h in kt_hata:
        hatalar.append("KENDINI-TEST: " + h)

    veri = olcumu_topla(args.url, args.taban_sha)
    iddialar, olculemedi = iddialari_olc(veri)

    print("== IKI GOVDE GEOMETRI OLCUMU ==")
    print("ucgen: tek=%d  govde=%d  yazi=%d  yazisiz(frame)=%d"
          % (veri["ucgen_tek"], veri["ucgen_govde"], veri["ucgen_yazi"],
             veri["ucgen_yazisiz"]))
    for ad, kosul, detay in iddialar:
        print(("  [OK ] " if kosul else "  [KIRMIZI] ") + ad
              + (" -> " + detay if detay else ""))
        if not kosul:
            hatalar.append(ad)
    for o in olculemedi:
        print("  [OLCULEMEDI] %s -> referans: %s" % (o, veri["sha_tek"]))

    print("\n== OLCUMLER ==")
    print("   tek govde SHA : %s" % veri["sha_tek"])
    print("   govde SHA     : %s" % veri["sha_govde"])
    print("   yazi SHA      : %s" % veri["sha_yazi"])
    print("   hacim (mm^3)  : tek=%.1f govde=%.1f yazi=%.1f"
          % (veri["hacim_tek"], veri["hacim_govde"], veri["hacim_yazi"]))
    print("   kendini-test  : %d iddia, %d sorun" % (kt_iddia, len(kt_hata)))
    if olculemedi:
        print("   OLCULEMEDI    : " + "; ".join(olculemedi))
    print("\nSONUC: " + ("KIRMIZI (%d iddia dustu)" % len(hatalar) if hatalar
                         else "YESIL"))
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
