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
     2e YAZI GOVDESININ x/y AYAK IZI, TEK GOVDEDEKI KABARTMANIN AYAK IZIYLE AYNI
        (tol HIZA_TOL). Referans: tek govde (Output="frame") mesh'inde z>derinlik+1e-3
        olan ucgenler — 1b govde mesh'inde bu yukseklikte ucgen OLMADIGINI olctugu
        icin bu alt-kume YALNIZ kabartmadir. Iki govde baskida BIRBIRINE OTURACAK,
        yani yazinin cerceveye gore yatay konumu tek-govdeli referansla ayni olmali.
     2f yazinin x/y ayak izi govdenin UST YUZUNUN (z=derinlik duzlemi) icinde: yazi
        pah/kavis bandina binmiyor, duz yuzeye basiyor.
  ⚠️ 2a/2c BUNU GORMEZ (30 Tem'de bagimsiz curutmeyle OLCULDU): 2a yalniz KAPSANMA
     olcer, 2c'nin ortak bbox'i x/y'de cerceveye domine olur ve saf oteleme HICBIR
     hacmi degistirmez -> yazi ayak izi icinde 1 mm de 30 mm de kaysa 13 iddia YESIL
     yaniyordu. 2e/2f bu kor noktayi kapatir; kanit MUTANTLAR listesindeki 8 oteleme
     mutantidir (dorduncu alani True -> o mutasyonlarda YALNIZ 2e/2f yanmali, yani
     eski 13 iddianin bu sinifa KOR oldugu her kosumda yeniden olculur).
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
🟡 YATAY KONUMDA HALA OLCULMEYEN (durustluk beyani): 2e iki govdenin BIRBIRINE gore
konumunu (baskida oturma sarti) olcer; iki govde BIRLIKTE ayni miktarda kaydirilirsa
2e KOR kalir — o hali yalniz 2f (ust yuzun disina tasma) yakalar. "Yazi alt kenar
yerine acikligin uzerine geldi" gibi ust yuz ICINDE kalan ortak kayma OLCULEMEDI:
ayak izinin altinda cerceve MALZEMESI olup olmadigini olcmek nokta-ucgen kaplama
hesabi ister (ayri paket; ust yuz ucgenlerinden kaplama testi).

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

# YATAY (x/y) HIZA TOLERANSI — NEDEN 0,02 mm (2e):
#   * BEKLENEN SAPMA SIFIR: cerceve.scad'de tek govdenin kabartmasi ile ayri yazi
#     govdesi AYNI ifadeden gelir (caption_solid(height=Caption_Depth+_Boolean_Overlap,
#     bottom_z=_Total_Depth-_Boolean_Overlap)); birlesim kabartmanin kose
#     koordinatlarini TASIMAZ. Yani 2e'nin olctugu iki bbox ayni cift-duyarlikli
#     sayilardan uretilir.
#   * GURULTU UST SINIRI: binary STL float32 tutar; |x|<=64 mm'de 1 ULP = 64*2^-24
#     = 3,8e-6 mm (ayni double'dan gelen iki float32 BIREBIR ayni cikar, farkli
#     yuvarlanirsa en fazla 1 ULP). 0,02 mm bunun ~2600 KATI -> sahte kirmizi payi.
#   * NEDEN DAHA DA GEVSEK DEGIL: 0,02 mm, 0,2 mm katman yuksekliginin 1/10'u ve
#     0,4 mm nozul capinin 1/20'si; 2-renk baskida bu buyuklukteki bir kayma zaten
#     goze gorunmez. Ureteci degistiren bilincli bir konum karari asla 0,02..0,1 mm
#     araliginda olmaz (kenar payi/margin adimlari mm mertebesinde).
#   * 🔴 DURUSTLUK: bu esik yuzunden 0,02 mm ALTINDAKI yatay kaymayi GORMEZ.
#     Olculen duyarlilik siniri her kosumda duyarlilik_olc() ile yeniden olculur ve
#     esikten sapmasi KIRMIZI yanar (esik gevsetilirse nobetci duser).
HIZA_TOL = 0.02


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


def ust_ucgenler(ucgenler, duzlem):
    """duzlem'in USTUNE tasan ucgenler (kabartma). Saf fonksiyon — kendini_test
    sentetik mini-mesh'le surer (yoksa asil olcum yolu olcusuz kalirdi)."""
    return [u for u in ucgenler if max(p[2] for p in u) > duzlem + 1e-3]


def duzlem_ucgenleri(ucgenler, duzlem):
    """TAMAMI duzlem seviyesinde (ya da uzerinde) kalan ucgenler = UST YUZ."""
    return [u for u in ucgenler if min(p[2] for p in u) > duzlem - 1e-3]


def ucgen_alt_kumesi_mi(alt, ana):
    """alt mesh'in HER ucgeni ana mesh'te var mi. WIRING NOBETI: 2e'nin referans
    alt-kumesi yanlislikla BASKA bir mesh'ten (or. yazi govdesinden) ayiklanirsa 2e
    kendi kendini karsilastirir ve SAHTE YESIL yanardi; bu kontrol o hatayi yakalar
    (yazi govdesinin duvar ucgenleri z=derinlik-0,02'de basladigi icin birlesimde
    AYNI koordinatlarla bulunmaz)."""
    ana_kume = {tuple(map(tuple, u)) for u in ana}
    return all(tuple(map(tuple, u)) in ana_kume for u in alt)


def bbox_veya_none(ucgenler):
    """Bos alt-kumede None doner (bbox() +/-inf uretip iddiayi sessizce yesile
    cevirmesin). None = "bu alt-kume mesh'te YOK" ve iddia tarafinda KIRMIZI'dir."""
    return bbox(ucgenler) if ucgenler else None


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
    "bbox_govde", "bbox_yazi", "bbox_tek", "bbox_ust_tek", "bbox_ust_yuz_govde",
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

    # 🔴 2e — YATAY (x/y) KONUM KOR NOKTASI KAPATILDI (30 Tem).
    # Referans = TEK govde mesh'inin z>derinlik+1e-3 alt-kumesi. 1b, GOVDE mesh'inde
    # bu yukseklikte ucgen olmadigini olctugu icin (ve 1c govdeyi yazisiz tabana
    # kilitledigi icin) bu alt-kume yalnizca KABARTMA'dir. Oteleme hicbir hacmi
    # degistirmedigi icin 3a/3b/3c, kapsanma olctugu icin 2a, cerceveye domine
    # oldugu icin 2c bu hatayi GORMUYORDU.
    ust_tek = veri["bbox_ust_tek"]
    if ust_tek is None:
        olc("2e yazi ayak izi TEK govdedeki kabartmanin ayak iziyle AYNI", False,
            "TEK govde mesh'inde z>%.3f ucgen YOK -> birlesimde kabartma bulunamadi "
            "(fail-closed KIRMIZI)" % (DERINLIK + 1e-3))
    else:
        uaz, ucok = ust_tek
        yatay_sapma = max(abs(uaz[0] - yaz[0]), abs(ucok[0] - ycok[0]),
                          abs(uaz[1] - yaz[1]), abs(ucok[1] - ycok[1]))
        olc("2e yazi ayak izi TEK govdedeki kabartmanin ayak iziyle AYNI",
            yatay_sapma <= HIZA_TOL,
            "yazi x[%.4f..%.4f] y[%.4f..%.4f] / tek-kabartma x[%.4f..%.4f] "
            "y[%.4f..%.4f] -> en buyuk yatay sapma=%.5f mm (tol %.3f)"
            % (yaz[0], ycok[0], yaz[1], ycok[1], uaz[0], ucok[0], uaz[1], ucok[1],
               yatay_sapma, HIZA_TOL))

    # 2f — yazi DUZ ust yuze mi basiyor (pah/kavis bandina tasmis mi).
    # Hedef bbox = govde mesh'inin z>derinlik-1e-3 alt-kumesi (ust yuz). Kavisli
    # kenar stillerinde (rounded/concave/ogee) tepeye TEGET ucgenler de bu kumeye
    # girip hedefi BUYUTEBILIR -> iddia o stillerde GEVSER, asla sahte kirmizi
    # yanmaz. En sikisi pah/duz stillerde (CI'da olculen parametre = chamfer).
    ust_yuz = veri["bbox_ust_yuz_govde"]
    if ust_yuz is None:
        olc("2f yazi ayak izi govdenin UST YUZUNUN icinde", False,
            "govde mesh'inde z>%.3f (ust yuz) ucgen YOK -> ust yuz olculemedi "
            "(fail-closed KIRMIZI)" % (DERINLIK - 1e-3))
    else:
        faz, fcok = ust_yuz
        olc("2f yazi ayak izi govdenin UST YUZUNUN icinde",
            yaz[0] >= faz[0] - TOL and ycok[0] <= fcok[0] + TOL and
            yaz[1] >= faz[1] - TOL and ycok[1] <= fcok[1] + TOL,
            "yazi x[%.3f..%.3f] y[%.3f..%.3f] / ust yuz x[%.3f..%.3f] y[%.3f..%.3f]"
            % (yaz[0], ycok[0], yaz[1], ycok[1], faz[0], fcok[0], faz[1], fcok[1]))

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
# 🔴 EK DURUSTLUK BEYANI (30 Tem, 2e/2f alanlari): asagidaki iki alan da SENTETIK,
# cerceve.scad'in KENDI cebirinden turetildi (gercek mesh'ten OLCULMEDI):
#   bbox_ust_tek        = yazi bbox'inin x/y'si (tanim geregi ayni ayak izi),
#                         z araligi [derinlik .. derinlik+kabartma] (birlesimde
#                         kabartmanin duzlem altinda kalan 0,02 mm'si kirpilir).
#   bbox_ust_yuz_govde  = dis bbox, kenar_stili="chamfer" + Edge_Size=1,6 icin
#                         ust yuz ice cekilmesiyle: 62-1,6=60,4 · 87-1,6=85,4
#                         (styled_rounded_prism: treated_size = size - 2*edge_size).
FIKSTUR = {
    "ucgen_tek": 1696, "ucgen_govde": 1304, "ucgen_yazi": 384,
    "ucgen_yazisiz": 1304, "ust_ucgen": 0,
    "bbox_govde": ([-62.0, -87.0, 0.0], [62.0, 87.0, 5.2]),
    "bbox_yazi": ([-30.0, -80.5, 5.18], [30.0, -70.5, 6.38]),
    "bbox_tek": ([-62.0, -87.0, 0.0], [62.0, 87.0, 6.38]),
    "bbox_ust_tek": ([-30.0, -80.5, 5.2], [30.0, -70.5, 6.38]),
    "bbox_ust_yuz_govde": ([-60.4, -85.4, 5.2], [60.4, 85.4, 5.2]),
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


def _otele(bbox_ciftli, dx, dy):
    (az, cok) = bbox_ciftli
    return ([az[0] + dx, az[1] + dy, az[2]], [cok[0] + dx, cok[1] + dy, cok[2]])


def _oteleme_mutanti(dx, dy, tek_de=False):
    """Yaziyi x/y'de oteler. tek_de=True ise TEK govdedeki kabartmayi da ayni kadar
    oteler (iki govde BIRLIKTE kaymis hali -> 2e kor, 2f gorur)."""
    d = {"bbox_yazi": _otele(FIKSTUR["bbox_yazi"], dx, dy)}
    if tek_de:
        d["bbox_ust_tek"] = _otele(FIKSTUR["bbox_ust_tek"], dx, dy)
    return _mutant(**d)


# 2e/2f'den ONCE var olan 13 iddianin GORMEDIGI mutasyon sinifi: yaziyi cerceve ayak
# izi ICINDE oteleyen saf paralel kaydirma. Bu listedeki her mutant icin kendini_test
# "KIRMIZI yananlarin HEPSI YENI_IDDIA_ONEKLERI'nden" sartini da olcer -> hem kor
# noktanin gercekten yeni iddialarla kapandigi, hem mutasyonun saf oteleme oldugu
# (yani ONCE-KIRMIZI kaniti) her kosumda yeniden olculur.
YENI_IDDIA_ONEKLERI = ("2e", "2f")
# 🔴 KAPSAM GENISLETME TUZAGI: YENI_IDDIA_ONEKLERI'ne eski bir onek eklenirse
# "yalniz yeni iddia yaniyor" sarti ANLAMSIZLASIR (pozitif nobetci sessizce olur —
# bu repoda ayni sinif daha once iki kez olculdu). Asagidaki liste iki kumenin AYRIK
# kaldigini olcmek icindir; kendini_test hem cakismayi hem siniflanmamis iddiayi yakar.
ESKI_IDDIA_ONEKLERI = ("1a", "1b", "1c", "2a", "2b", "2c", "2d",
                       "3a", "3b", "3c", "4a", "4b", "4c")

# (ad, mutant_veri, KIRMIZI_yanmasi_beklenen_iddia_oneki, yalniz_yeni_iddia_gormeli)
MUTANTLAR = (
    # 1) HACIM KORUNUMU: yazi birlesime HIC girmedi (V(tek) = V(govde)). Gercek
    #    dunyadaki bicim: Output="frame" caption'i dusuruyor.
    ("hacim korunumu bozuldu — yazi birlesime girmedi (V(tek)=V(govde))",
     _mutant(hacim_tek=33422.8), "3a", False),
    # 2) BBOX KAYDI: birlesimin bbox'i iki govdenin ortak bbox'undan BUYUK.
    ("bbox kaydi — tek govde bbox z_max sisti (6,38 -> 7,00)",
     _mutant(bbox_tek=([-62.0, -87.0, 0.0], [62.0, 87.0, 7.0])), "2c", False),
    # 3) BBOX KAYDI (x/y): yazi cercevenin DISINA kaydi.
    ("bbox kaydi — yazi x araligi govdenin DISINA cikti (+40 mm)",
     _mutant(bbox_yazi=([10.0, -80.5, 5.18], [70.0, -70.5, 6.38])), "2a", False),
    # 4) HIZALAMA: bindirme UYGULANMAMIS (fark 0). ⚠️ ESKI 2b ARALIK IDDIASI BU
    #    HALI YESIL SAYIYORDU (-0,02-tol <= 0 <= tol) -> sikilastirmanin somut kazanci.
    ("hizalama bindirmeden sapti — bindirme uygulanmamis (fark 0,0000)",
     _mutant(bbox_yazi=([-30.0, -80.5, 5.2], [30.0, -70.5, 6.4]),
             bbox_tek=([-62.0, -87.0, 0.0], [62.0, 87.0, 6.4])), "2b", False),
    # 5) #govde SHA'si degisti -> yazisiz taban ile ayrisma.
    ("#govde SHA'si yazisiz tabandan ayristi",
     _mutant(sha_govde="e" * 64, sha_govdeB="e" * 64), "1c", False),
    # 6) BELIRLENIMCILIK: ayni girdi iki farkli cikti.
    ("belirlenimcilik bozuldu — ayni yazi iki farkli SHA",
     _mutant(sha_yazi2="f" * 64), "4a", False),
    # 7) METIN BAGLANTISI: farkli yazi ayni govdeyi uretti (29 Tem sessiz teslimat
    #    hatasinin ta kendisi).
    ("metin baglantisi koptu — farkli yazi AYNI yazi govdesi",
     _mutant(sha_yaziB="c" * 64), "4b", False),
    # 8) KABARTMA YOK: yazi govdenin ust yuzunu asmiyor.
    ("kabartma yok — yazi tepesi govde ust yuzuyle ayni",
     _mutant(bbox_yazi=([-30.0, -80.5, 5.18], [30.0, -70.5, 5.2]),
             bbox_tek=([-62.0, -87.0, 0.0], [62.0, 87.0, 5.2])), "2d", False),
    # 9) MASKELEME: bindirme tahmini sisirilirse 3a sahte-yesil yakabilirdi.
    ("bindirme tahmini sisti (yazidan buyuk) — 3a maskeleme denemesi",
     _mutant(hacim_bindirme=182.4), "3c", False),
    # ---- 10..17) YATAY (x/y) OTELEME — 30 Tem'e kadar 13 iddianin TAMAMI YESIL
    # yaniyordu (bagimsiz curutmede olculdu). Dorduncu alan True: bu mutasyonlarda
    # KIRMIZI yananlarin HEPSI yeni iddia (2e/2f) olmali; eski bir iddia da yanarsa
    # mutasyon "saf oteleme" degildir ve kor-nokta kaniti gecersizdir.
    ("yatay kayma — yazi +1 mm x otelendi (ayak izi ICINDE)",
     _oteleme_mutanti(1.0, 0.0), "2e", True),
    ("yatay kayma — yazi -1 mm y otelendi (ayak izi ICINDE)",
     _oteleme_mutanti(0.0, -1.0), "2e", True),
    ("yatay kayma — yazi +30 mm x otelendi (yarim cerceve boyu)",
     _oteleme_mutanti(30.0, 0.0), "2e", True),
    ("yatay kayma — yazi KARSI KENARA gecti (alt kenar -> ust kenar, +151 mm y)",
     _oteleme_mutanti(0.0, 151.0), "2e", True),
    ("yatay kayma — yazi KOSEYE kaydi (+30 mm x, +151 mm y)",
     _oteleme_mutanti(30.0, 151.0), "2e", True),
    ("yatay kayma — yazi UST YUZDEN TASTI (pah bandina bindi, +32 mm x)",
     _oteleme_mutanti(32.0, 0.0), "2f", True),
    ("iki govde BIRLIKTE kaydi (tek+yazi ayni oteleme) — 2e KOR, 2f gormeli",
     _oteleme_mutanti(32.0, 0.0, tek_de=True), "2f", True),
    ("TEK govdede kabartma YOK (z>derinlik alt-kumesi bos) — fail-closed",
     _mutant(bbox_ust_tek=None), "2e", True),
)


# ---------------------------------------------------------------------------
# YANLIS-POZITIF SUITI — MESRU parametre senaryolari (hicbir iddia yanmamali).
# 🔴 DURUSTLUK BEYANI: bu senaryolarin sayilari GERCEK MESH'TEN OLCULMEDI (bu
# makinede openscad SIGABRT verdigi icin yerelde mesh uretilemez).
#   * GEOMETRIK degerler cerceve.scad'in KENDI cebirinin BIREBIR aynasidir; her
#     satirin yaninda kaynak degisken adi yazili (_Opening_Size, _Outer_Size,
#     _Resolved_Edge_Size, _Caption_Profile_Inset, _Caption_Length_Min/Max,
#     _Caption_Band_Outer/Inner, resolved_size, axis_center, _Caption_Cross_Center).
#   * SENTETIK olan: harf basina birim genislik (0,62 em) ve harf yuksekligi
#     (0,72 em) — gercek textmetrics(Liberation Sans Bold) degerleri elde YOK.
#   * TURETILMIS olan: hacimler (3a/3b/3c'yi saglayacak bicimde hesaplanir) ->
#     bu suit HACIM iddialarini SINAMAZ; amaci 2e/2f + 2a/2b/2c/2d'nin farkli
#     olcu / derinlik / kenar stili / yazi uzunlugu / yazi boyunda SAHTE KIRMIZI
#     yakip yakmadigini olcmektir.
#   * bbox koseleri float32'ye KUANTALANIR (binary STL float32 tutar) ve tek
#     govdedeki kabartma ile ayri yazi govdesi arasina +/-2e-5 mm mesher gurultusu
#     ENJEKTE edilir -> HIZA_TOL'un gurultu payi olculur.
KLR = 0.1              # Opening_Clearance
DIS_KAVIS = 4.0        # Outer_Rounding
KENAR_BOYU = 1.6       # Edge_Size
PAY_X = 1.5            # Caption_Margin.x
PAY_Y = 2.0            # Caption_Margin.y
KABARTMA = 1.2         # Caption_Depth
BIRIM_EN = 0.62        # SENTETIK: harf basina em genisligi
BIRIM_BOY = 0.72       # SENTETIK: buyuk harf em yuksekligi
MIN_DUVAR = 1.0        # _Minimum_Wall
GURULTU = 2e-5         # enjekte edilen mesher gurultusu (mm)


def _f32(x):
    """double -> float32 -> double (binary STL'in kaybini birebir taklit eder)."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def mesru_senaryo(ad, acilik_en, acilik_boy, kenar, derinlik, stil, harf, yazi_boyu):
    """cerceve.scad cebirinden MESRU (kusursuz) bir olcum seti uretir."""
    acik = (acilik_en + 2 * KLR, acilik_boy + 2 * KLR)              # _Opening_Size
    dis = (acik[0] + 2 * kenar, acik[1] + 2 * kenar)                # _Outer_Size
    dis_kavis = min(DIS_KAVIS, min(dis) / 2)              # _Resolved_Outer_Rounding
    azami_kenar = min(derinlik - BINDIRME, kenar - MIN_DUVAR)         # _Max_Edge_Size
    kenar_b = max(0.0, min(KENAR_BOYU, azami_kenar))             # _Resolved_Edge_Size
    ic_cekme = 0.0 if stil == "flat" else kenar_b            # _Caption_Profile_Inset
    yuz_kavis = max(0.0, dis_kavis - ic_cekme)               # _Caption_Face_Rounding
    birim_en = BIRIM_EN * harf                                # _Caption_Unit_Size.x
    boy_min = -dis[0] / 2 + ic_cekme + PAY_X + yuz_kavis      # _Caption_Length_Min
    boy_max = dis[0] / 2 - ic_cekme - PAY_X - yuz_kavis       # _Caption_Length_Max
    bant_dis = -dis[1] / 2 + ic_cekme                        # _Caption_Band_Outer
    bant_ic = -acik[1] / 2                                   # _Caption_Band_Inner
    boy_bos = boy_max - boy_min                            # _Caption_Length_Available
    enine_bos = abs(bant_ic - bant_dis) - 2 * PAY_Y         # _Caption_Cross_Available
    if boy_bos <= 0 or enine_bos <= 0:
        raise ValueError("senaryo uretilemez, cerceve.scad assert'i yanardi: " + ad)
    olcek = min(yazi_boyu, boy_bos / birim_en, enine_bos / BIRIM_BOY)  # resolved_size
    yazi_en = birim_en * olcek
    yazi_yuk = BIRIM_BOY * olcek
    eksen = (boy_min + boy_max) / 2.0                                 # axis_center
    enine_merkez = (bant_ic + bant_dis) / 2.0             # _Caption_Cross_Center

    yaz = [_f32(eksen - yazi_en / 2), _f32(enine_merkez - yazi_yuk / 2),
           _f32(derinlik - BINDIRME)]
    ycok = [_f32(eksen + yazi_en / 2), _f32(enine_merkez + yazi_yuk / 2),
            _f32(derinlik + KABARTMA)]
    gaz = [_f32(-dis[0] / 2), _f32(-dis[1] / 2), 0.0]
    gcok = [_f32(dis[0] / 2), _f32(dis[1] / 2), _f32(derinlik)]
    # tek govdedeki kabartma: AYNI ayak izi (+ enjekte gurultu), tabani duzlemde kirpik
    uaz = [_f32(yaz[0] + GURULTU), _f32(yaz[1] - GURULTU), _f32(derinlik)]
    ucok = [_f32(ycok[0] - GURULTU), _f32(ycok[1] + GURULTU), ycok[2]]
    # TURETILMIS hacimler (3a tam saglanir; bu suit hacim iddialarini SINAMAZ)
    v_govde = (dis[0] * dis[1] - acik[0] * acik[1]) * derinlik * 0.97
    murekkep = 0.55 * yazi_en * yazi_yuk
    v_yazi = murekkep * (KABARTMA + BINDIRME)
    v_bindirme = murekkep * BINDIRME
    return (ad, {
        "ucgen_tek": 1304 + 96 * harf + 8, "ucgen_govde": 1304,
        "ucgen_yazi": 96 * harf, "ucgen_yazisiz": 1304, "ust_ucgen": 0,
        "bbox_govde": (gaz, gcok), "bbox_yazi": (yaz, ycok),
        "bbox_tek": (gaz, [gcok[0], gcok[1], ycok[2]]),
        "bbox_ust_tek": (uaz, ucok),
        "bbox_ust_yuz_govde": ([_f32(gaz[0] + ic_cekme), _f32(gaz[1] + ic_cekme),
                                gcok[2]],
                               [_f32(gcok[0] - ic_cekme), _f32(gcok[1] - ic_cekme),
                                gcok[2]]),
        "hacim_tek": v_govde + v_yazi - v_bindirme, "hacim_govde": v_govde,
        "hacim_yazi": v_yazi, "hacim_bindirme": v_bindirme,
        "sha_tek": "1" * 64, "sha_govde": "2" * 64, "sha_yazi": "3" * 64,
        "sha_yazisiz": "2" * 64, "sha_yazi2": "3" * 64, "sha_yaziB": "4" * 64,
        "sha_govdeB": "2" * 64, "taban_sha": None,
    })


MESRU_SENARYOLAR = (
    mesru_senaryo("kucuk cerceve 40x60 · kenar 12 · 5,2 mm · chamfer · 6 harf · 8",
                  40, 60, 12, 5.2, "chamfer", 6, 8.0),
    mesru_senaryo("buyuk cerceve 300x400 · kenar 25 · 20 mm · flat · 30 harf · 8",
                  300, 400, 25, 20.0, "flat", 30, 8.0),
    mesru_senaryo("sig derinlik 100x150 · kenar 12 · 2,5 mm · concave · 1 harf · 8",
                  100, 150, 12, 2.5, "concave", 1, 8.0),
    mesru_senaryo("ince kenar 120x180 · kenar 8 · 3 mm · rounded · 12 harf · 5",
                  120, 180, 8, 3.0, "rounded", 12, 5.0),
    mesru_senaryo("geniz kenar 200x200 · kenar 30 · 10 mm · ogee · 24 harf · 12",
                  200, 200, 30, 10.0, "ogee", 24, 12.0),
    mesru_senaryo("kademe kenar 60x90 · kenar 15 · 6 mm · stepped · 4 harf · 8",
                  60, 90, 15, 6.0, "stepped", 4, 8.0),
    mesru_senaryo("CI parametresi · KUCUK font 100x150 · 5,2 mm · chamfer · 4 harf · 4",
                  100, 150, 12, 5.2, "chamfer", 4, 4.0),
    mesru_senaryo("yatay cerceve 150x100 · kenar 10 · 4 mm · flat · 18 harf · 6",
                  150, 100, 10, 4.0, "flat", 18, 6.0),
)


# SENTETIK MINI-MESH — ayiklama fonksiyonlarini (ust_ucgenler / duzlem_ucgenleri)
# openscad'siz surmek icin. 5,2 mm'lik bir plaka (ust yuz z=5,2, yan duvar 0..5,2) +
# uzerinde x[2..4] y[1..3] ayak izli 1,2 mm kabartma. GERCEK MESH DEGIL, elle yazildi.
MINI_GOVDE = [
    [(-10.0, -10.0, 5.2), (10.0, -10.0, 5.2), (10.0, 10.0, 5.2)],   # ust yuz
    [(-10.0, -10.0, 5.2), (10.0, 10.0, 5.2), (-10.0, 10.0, 5.2)],   # ust yuz
    [(-10.0, -10.0, 0.0), (10.0, -10.0, 0.0), (10.0, -10.0, 5.2)],  # yan duvar
    [(-10.0, -10.0, 0.0), (10.0, -10.0, 0.0), (10.0, 10.0, 0.0)],   # alt yuz
]
MINI_KABARTMA = [
    [(2.0, 1.0, 5.2), (4.0, 1.0, 5.2), (4.0, 1.0, 6.4)],            # yazi duvari
    [(2.0, 1.0, 6.4), (4.0, 1.0, 6.4), (4.0, 3.0, 6.4)],            # yazi tepesi
    [(2.0, 1.0, 6.4), (4.0, 3.0, 6.4), (2.0, 3.0, 6.4)],            # yazi tepesi
]


def ayiklama_kendini_test():
    """(hatalar) — ayiklama fonksiyonlari GERCEKTEN ayikliyor mu (sentetik mesh)."""
    h = []
    tek_mesh = MINI_GOVDE + MINI_KABARTMA
    kabartma = ust_ucgenler(tek_mesh, 5.2)
    if len(kabartma) != len(MINI_KABARTMA):
        h.append("AYIKLAMA (ust_ucgenler): tek mesh'te %d kabartma ucgeni ayiklandi, "
                 "%d bekleniyor -> duzlem suzgeci bozuk"
                 % (len(kabartma), len(MINI_KABARTMA)))
    kb = bbox_veya_none(kabartma)
    if kb is None or abs(kb[0][0] - 2.0) > 1e-9 or abs(kb[1][0] - 4.0) > 1e-9 \
            or abs(kb[0][1] - 1.0) > 1e-9 or abs(kb[1][1] - 3.0) > 1e-9:
        h.append("AYIKLAMA (kabartma bbox): x/y [2..4]x[1..3] bekleniyordu, olculen %r"
                 % (kb,))
    if ust_ucgenler(MINI_GOVDE, 5.2):
        h.append("AYIKLAMA: yazisiz plakada duzlem USTUNDE ucgen bulundu -> suzgec "
                 "duzlemin kendisini de aliyor (1b/2e sahte deger uretir)")
    ust_yuz = duzlem_ucgenleri(MINI_GOVDE, 5.2)
    if len(ust_yuz) != 2:
        h.append("AYIKLAMA (duzlem_ucgenleri): %d ust yuz ucgeni ayiklandi, 2 "
                 "bekleniyor -> yan duvar/alt yuz de kumeye giriyor" % len(ust_yuz))
    fb = bbox_veya_none(ust_yuz)
    if fb is None or abs(fb[0][0] + 10.0) > 1e-9 or abs(fb[1][1] - 10.0) > 1e-9:
        h.append("AYIKLAMA (ust yuz bbox): [-10..10]^2 bekleniyordu, olculen %r" % (fb,))
    if bbox_veya_none([]) is not None:
        h.append("AYIKLAMA: bos alt-kume None DONMUYOR -> bbox +/-inf uretip iddiayi "
                 "sessizce yesile cevirebilir")
    # WIRING NOBETI iki yon: dogru mesh'te GECER, yanlis mesh'te YAKALAR.
    if not ucgen_alt_kumesi_mi(kabartma, tek_mesh):
        h.append("WIRING NOBETI SAHTE KIRMIZI: kabartma ucgenleri kendi mesh'inin "
                 "alt kumesi sayilmadi")
    if ucgen_alt_kumesi_mi(MINI_KABARTMA, MINI_GOVDE):
        h.append("WIRING NOBETI OLU: yabanci mesh'ten ayiklanmis alt-kume 'ayni "
                 "mesh' sayildi -> 2e yanlis mesh'le sahte-yesil yanabilir")
    return h


def duyarlilik_olc(taban=None, en_kucuk=1e-7, en_buyuk=4.0, tur=64):
    """2e'nin GORDUGU en kucuk x otelemesini (mm) ikili aramayla OLCER.
    Donus: sinir_mm (2e'yi KIRMIZI yakan en kucuk oteleme) ya da None (2e OLU)."""
    veri = taban if taban is not None else FIKSTUR

    def kirmizi(d):
        m = dict(veri)
        m["bbox_yazi"] = _otele(veri["bbox_yazi"], d, 0.0)
        iddialar, _ = iddialari_olc(m)
        return any(ad.startswith("2e") and not kosul for ad, kosul, _d in iddialar)

    if kirmizi(en_kucuk):
        return en_kucuk          # esik gurultu seviyesinde -> sahte kirmizi riski
    if not kirmizi(en_buyuk):
        return None              # 4 mm oteleme bile gorunmuyor -> nobetci OLU
    alt, ust = en_kucuk, en_buyuk
    for _ in range(tur):
        orta = (alt + ust) / 2.0
        if kirmizi(orta):
            ust = orta
        else:
            alt = orta
    return ust


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
    NEGATIF: her mutant BEKLENEN iddiayi KIRMIZI yakmali (govde no-op yapilirsa ya da
      bir iddia silinirse bunlar birden duser). Oteleme mutantlarinda EK SART: kirmizi
      yananlarin hepsi YENI iddia (2e/2f) olmali -> mutasyonun saf oteleme oldugu, yani
      13 eski iddianin bu sinifa KOR oldugu her kosumda yeniden olculur.
    YANLIS-POZITIF: MESRU_SENARYOLAR'in hicbirinde iddia yanmamali.
    DUYARLILIK: 2e'nin gordugu en kucuk oteleme OLCULUR ve HIZA_TOL ile ayni olmali.
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
    if len(iddialar) < 15:
        hatalar.append("IDDIA SAYISI DUSTU: %d iddia olculdu, en az 15 bekleniyor "
                       "(1a/1b/1c · 2a/2b/2c/2d/2e/2f · 3a/3b/3c · 4a/4b/4c) -> bir "
                       "iddia silinmis olabilir" % len(iddialar))

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
    for ad, mutant, beklenen_onek, yalniz_yeni in MUTANTLAR:
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
        # ONCE-KIRMIZI KANITI: saf oteleme mutasyonunda YALNIZ yeni iddialar (2e/2f)
        # yanmali. Eski bir iddia da yaniyorsa mutasyon saf oteleme DEGIL, yani
        # "13 iddia bu sinifa kor" olcumu artik gecerli degil.
        if yalniz_yeni:
            iddia += 1
            eskiler = [a for a in kirmizilar
                       if not a.startswith(YENI_IDDIA_ONEKLERI)]
            if eskiler:
                hatalar.append("KOR NOKTA KANITI DUSTU: %r mutasyonunda ESKI iddialar "
                               "da KIRMIZI yandi (%s) -> mutasyon saf yatay oteleme "
                               "degil; kaniti yeniden kurun"
                               % (ad, "; ".join(eskiler)))

    # YANLIS-POZITIF — mesru senaryolarda 0 iddia yanmali (sahte kirmizi = imaj
    # yayini imkansiz = tum ekibin yayini durur).
    for ad, senaryo in MESRU_SENARYOLAR:
        iddia += 1
        try:
            s_iddialar, _ = iddialari_olc(senaryo)
        except ValueError as e:
            hatalar.append("MESRU SENARYO OLCULEMEDI (%s): %s" % (ad, e))
            continue
        s_dusen = [a for a, k, d in s_iddialar if not k]
        if s_dusen:
            hatalar.append("SAHTE KIRMIZI (%s): mesru senaryoda %d iddia dustu -> %s"
                           % (ad, len(s_dusen), "; ".join(s_dusen)))
        elif ayrintili:
            print("  [MESRU YESIL] %s" % ad)

    # DUYARLILIK — 2e'nin gordugu en kucuk oteleme OLCULUR (beyan edilen HIZA_TOL ile
    # ayni olmali). Esik gevsetilirse ya da iddia sabitlenirse bu iki iddia duser.
    iddia += 2
    sinir = duyarlilik_olc()
    if sinir is None:
        hatalar.append("2e OLU: 4 mm'lik yatay oteleme bile KIRMIZI yakmadi -> "
                       "iddia degerlendirilmiyor olabilir")
    elif abs(sinir - HIZA_TOL) > HIZA_TOL * 0.02:
        hatalar.append("DUYARLILIK KAYDI: olculen 2e siniri %.6f mm, beyan edilen "
                       "HIZA_TOL %.6f mm -> betikteki durustluk beyani bayat"
                       % (sinir, HIZA_TOL))
    elif ayrintili:
        print("  [DUYARLILIK] 2e olculen sinir = %.5f mm (beyan HIZA_TOL=%.5f mm); "
              "bu degerin ALTINDAKI yatay kaymayi GORMEZ" % (sinir, HIZA_TOL))
    # DUYARLILIK OLCUMU SABIT MI: zaten 0,5 mm kayik bir tabanda sinir ~0 olmali
    # (taban HALIHAZIRDA kirmizi). duyarlilik_olc govdesi sabit bir deger donerse
    # (or. `return HIZA_TOL`) bu karsi-ornek duser.
    iddia += 1
    kayik = duyarlilik_olc(taban=_mutant(
        bbox_ust_tek=_otele(FIKSTUR["bbox_ust_tek"], 0.5, 0.0)))
    if kayik is None or kayik > HIZA_TOL / 2:
        hatalar.append("DUYARLILIK OLCUMU SABIT: 0,5 mm KAYIK tabanda olculen sinir "
                       "%r -> ~0 bekleniyordu (taban zaten KIRMIZI); duyarlilik_olc "
                       "gercekten olcmuyor olabilir" % (kayik,))

    # KOR NOKTA KANITININ KAPSAMI: yeni/eski onek kumeleri AYRIK ve TAM olmali.
    iddia += 2
    cakisan = sorted(set(YENI_IDDIA_ONEKLERI) & set(ESKI_IDDIA_ONEKLERI))
    if cakisan or not YENI_IDDIA_ONEKLERI:
        hatalar.append("KOR NOKTA KANITI SULANDIRILDI: YENI_IDDIA_ONEKLERI eski "
                       "iddialari da kapsiyor (%s) -> 'oteleme mutasyonunda YALNIZ "
                       "yeni iddia yaniyor' sarti anlamsizlasir"
                       % (", ".join(cakisan) or "kume BOS"))
    olculen_onekler = {a.split()[0] for a, k, d in iddialar}
    siniflanmamis = sorted(olculen_onekler - set(ESKI_IDDIA_ONEKLERI)
                           - set(YENI_IDDIA_ONEKLERI))
    kayip = sorted(set(ESKI_IDDIA_ONEKLERI) - olculen_onekler)
    if siniflanmamis or kayip:
        hatalar.append("ONEK KUMESI BAYAT: siniflanmamis iddia(lar) %s · olculmeyen "
                       "eski onek(ler) %s -> kor nokta kaniti eksik iddia uzerinden "
                       "yurur" % (siniflanmamis or "-", kayip or "-"))

    if not 1e-3 <= HIZA_TOL <= 0.05:
        hatalar.append("HIZA_TOL BANDI: %.5f mm makul bandin disinda (0,001..0,05 mm; "
                       "alt sinir float32 gurultusunun ~100 kati, ust sinir 0,2 mm "
                       "katman yuksekliginin 1/4'u)" % HIZA_TOL)

    # AYIKLAMA — 2e/2f'nin girdilerini ureten suzgecler sentetik mesh'le olculur
    # (asil olcum yolu; hatasi CI'da "kabartma bulunamadi" diye gorunur ama yanlis
    # mesh'ten ayiklama SESSIZ kalabilirdi).
    iddia += 1
    for h in ayiklama_kendini_test():
        hatalar.append(h)

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
    ust = ust_ucgenler(govde, DERINLIK)
    # 2e/2f'nin girdileri — YENI HTTP ISTEGI YOK, zaten indirilmis mesh'lerden.
    #   tek_ust      : TEK govdede derinlik duzleminin USTUNDE kalan ucgenler.
    #                  1b bu yukseklikte GOVDE ucgeni olmadigini olcer -> alt-kume
    #                  yalniz kabartma. Kabartmanin ust yuzu tek basina ayak izinin
    #                  TAMAMINI x/y'de kapsar, yani bbox'i = yazinin ayak izi.
    #   govde_ust_yuz: GOVDE mesh'inin derinlik duzlemindeki ucgenleri (ust yuz);
    #                  pah/kavis/kademe islemleri ust yuzu ice cektigi icin bu bbox
    #                  dis bbox'tan KUCUKTUR (chamfer'da kenar_boyu kadar).
    tek_ust = ust_ucgenler(tek, DERINLIK)
    govde_ust_yuz = duzlem_ucgenleri(govde, DERINLIK)
    if not ucgen_alt_kumesi_mi(tek_ust, tek):
        sys.exit("WIRING HATASI: 2e referans alt-kumesi TEK govde mesh'inin ucgenleri "
                 "DEGIL -> yanlis mesh'ten ayiklaniyor (fail-closed)")
    if not ucgen_alt_kumesi_mi(govde_ust_yuz, govde):
        sys.exit("WIRING HATASI: 2f ust yuz alt-kumesi GOVDE mesh'inin ucgenleri "
                 "DEGIL -> yanlis mesh'ten ayiklaniyor (fail-closed)")
    return {
        "ucgen_tek": len(tek), "ucgen_govde": len(govde), "ucgen_yazi": len(yazi),
        "ucgen_yazisiz": len(yazisiz), "ust_ucgen": len(ust),
        "bbox_govde": bbox(govde), "bbox_yazi": (yaz, ycok), "bbox_tek": bbox(tek),
        "bbox_ust_tek": bbox_veya_none(tek_ust),
        "bbox_ust_yuz_govde": bbox_veya_none(govde_ust_yuz),
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
        print("  ✅ POZITIF: 30 Tem'de olculen GERCEK sayilarla 15 iddia YESIL")
        print("  ✅ NEGATIF: %d mutant beklenen iddiayi KIRMIZI yakiyor "
              "(%d'i saf yatay oteleme; onlarda YALNIZ 2e/2f yaniyor)"
              % (len(MUTANTLAR), sum(1 for m in MUTANTLAR if m[3])))
        print("  ✅ YANLIS-POZITIF: %d mesru senaryoda 0 iddia yandi"
              % len(MESRU_SENARYOLAR))
        print("  ✅ AYIKLAMA: ust_ucgenler/duzlem_ucgenleri sentetik mesh'te dogru "
              "alt-kumeyi veriyor")
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
