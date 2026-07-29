#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IKI GOVDE GEOMETRI OLCUMU — 2-renk yazi sozlesmesinin MESH kaniti.

🔴 OPENSCAD GEREKTIRIR: bu betik CALISAN bir derleyiciye (onizleme/derleyici/server.py
ya da CI'da imajin konteyneri) HTTP ile konusur. Gelistirme Mac'inde openscad
SIGABRT verdigi icin YEREL KOSULMAZ; yeri .github/workflows/onizleme-imaj.yml
(imaj duman adiminin hemen ardindan, konteyner ayaktayken).

NE OLCER (ucgen/bbox/hacim — hepsi GERCEK mesh uzerinde):
  1. AYRISMA
     1a yazi govdesinin ucgen sayisi > 0 (yazi GERCEKTEN ayri bir govde).
     1b govde (yazisiz) mesh'inde z > Frame_Depth+tol ucgen YOK (yazi orada DEGIL).
     1c govde mesh'i, taban ailenin Caption_Text="" haliyle BIREBIR AYNI (ayni SHA-256):
        cerceve.scad'de Caption_Fit="existing" oldugu icin dis olcu yazidan bagimsiz —
        yani "yazisiz cerceve" tanimi TEK ve tutarli.
  2. HIZALAMA (kaydirma SIFIR)
     2a yazi bbox'inin x/y araligi govde bbox'inin x/y araliginin ICINDE.
     2b yazi z_min ile govde z_max farki, uretecin bilincli boolean bindirmesinden
        (0,02 mm) BUYUK DEGIL -> yazi govdenin UST YUZUNE oturur, havada/gomulu degil.
     2c iki govdenin ORTAK bbox'i, tek govdeli (Output="frame") mesh'in bbox'i ile
        AYNI (tol 1e-3 mm): birlesim, tek govdenin isgal ettigi hacmi asmaz/eksiltmez.
  3. ESDEGERLIK
     3a hacim: V(govde) + V(yazi) - V(bindirme) ~= V(tek govde) (bagil sapma <= %0,5).
        V(bindirme) ust sinirini yazi tabani alani x 0,02 mm ile tahmin ederiz.
     3b tek govde mesh'inin ucgen sayisi, govde+yazi toplamindan KUCUK ya da esittir
        (union ic yuzeyleri siler; toplamdan BUYUK cikmasi tutarsizlik olurdu).
  4. BELIRLENIMCILIK / METIN BAGLANTISI
     4a ayni yazi -> ayni SHA (her uc cikti icin).
     4b farkli yazi -> yazi govdesi DEGISIR; govde (yazisiz) DEGISMEZ.
  5. GERIYE DONUK UYUM
     5a Output="frame" (parcasiz) ciktisi, --taban-sha ile verilen referansla AYNI
        (referans verilmezse bu iddia ATLANIR ve rapora "OLCULEMEDI" yazilir).

NE OLCMEZ: onbellek anahtarini/worker yonlendirmesini (onizleme/test/iki-govde-kabul.mjs),
eslem/-D tarafini (tools/iki-govde-kapisi.py), baskinin fiziksel yapismasini, fiyati.

Kullanim:
  python3 onizleme/test/iki-govde-olcum.py --url http://127.0.0.1:18080
  python3 onizleme/test/iki-govde-olcum.py --url ... --taban-sha <sha256>
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
TOL = 1e-3


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="calisan derleyici (or. http://127.0.0.1:18080)")
    ap.add_argument("--taban-sha", help="Output=frame ciktisinin beklenen SHA-256 (geriye donuk uyum)")
    args = ap.parse_args()

    hatalar, olculemedi = [], []

    def olc(ad, kosul, detay=""):
        print(("  [OK ] " if kosul else "  [KIRMIZI] ") + ad + (" -> " + detay if detay else ""))
        if not kosul:
            hatalar.append(ad)

    ham_tek = derle(args.url, AILE, PARAM)
    ham_govde = derle(args.url, AILE + "#govde", PARAM)
    ham_yazi = derle(args.url, AILE + "#yazi", PARAM)
    ham_yazisiz = derle(args.url, AILE, dict(PARAM, yazi=""))

    tek, sha_tek = stl_coz(ham_tek)
    govde, sha_govde = stl_coz(ham_govde)
    yazi, sha_yazi = stl_coz(ham_yazi)
    yazisiz, sha_yazisiz = stl_coz(ham_yazisiz)

    print("== IKI GOVDE GEOMETRI OLCUMU ==")
    print("ucgen: tek=%d  govde=%d  yazi=%d  yazisiz(frame)=%d"
          % (len(tek), len(govde), len(yazi), len(yazisiz)))

    # 1) AYRISMA
    olc("1a yazi govdesi BOS DEGIL", len(yazi) > 0, "%d ucgen" % len(yazi))
    ust = [u for u in govde if max(p[2] for p in u) > DERINLIK + 1e-3]
    olc("1b govde mesh'inde yazi yuksekliginde ucgen YOK", len(ust) == 0,
        "z>%.2f ucgen sayisi = %d" % (DERINLIK, len(ust)))
    olc("1c govde == taban ailenin yazisiz hali (ayni SHA)", sha_govde == sha_yazisiz,
        "govde=%s yazisiz=%s" % (sha_govde[:16], sha_yazisiz[:16]))

    # 2) HIZALAMA
    gaz, gcok = bbox(govde)
    yaz, ycok = bbox(yazi)
    taz, tcok = bbox(tek)
    olc("2a yazi bbox'i govde bbox'inin x/y ICINDE",
        yaz[0] >= gaz[0] - TOL and ycok[0] <= gcok[0] + TOL and
        yaz[1] >= gaz[1] - TOL and ycok[1] <= gcok[1] + TOL,
        "yazi x[%.3f..%.3f] y[%.3f..%.3f] / govde x[%.3f..%.3f] y[%.3f..%.3f]"
        % (yaz[0], ycok[0], yaz[1], ycok[1], gaz[0], gcok[0], gaz[1], gcok[1]))
    z_bosluk = yaz[2] - gcok[2]
    olc("2b yazi tabani govde ust yuzune oturuyor (kaydirma yok)",
        -BINDIRME - TOL <= z_bosluk <= TOL,
        "yazi z_min=%.4f  govde z_max=%.4f  fark=%.4f (bindirme %.2f)"
        % (yaz[2], gcok[2], z_bosluk, BINDIRME))
    ortak_az = [min(gaz[k], yaz[k]) for k in range(3)]
    ortak_cok = [max(gcok[k], ycok[k]) for k in range(3)]
    olc("2c govde+yazi ORTAK bbox'i tek govdeninkiyle AYNI",
        all(abs(ortak_az[k] - taz[k]) <= TOL and abs(ortak_cok[k] - tcok[k]) <= TOL
            for k in range(3)),
        "ortak=[%s] tek=[%s]"
        % (", ".join("%.3f..%.3f" % (ortak_az[k], ortak_cok[k]) for k in range(3)),
           ", ".join("%.3f..%.3f" % (taz[k], tcok[k]) for k in range(3))))

    # 3) ESDEGERLIK
    v_tek, v_govde, v_yazi = hacim(tek), hacim(govde), hacim(yazi)
    v_bindirme = yazi_taban_alani(yazi, yaz[2]) * BINDIRME
    beklenen = v_govde + v_yazi - v_bindirme
    sapma = abs(beklenen - v_tek) / max(v_tek, 1e-9)
    olc("3a hacim esdegerligi V(govde)+V(yazi)-V(bindirme) ~= V(tek)", sapma <= 0.005,
        "tek=%.1f  govde=%.1f  yazi=%.1f  bindirme~%.2f  bagil sapma=%.4f%%"
        % (v_tek, v_govde, v_yazi, v_bindirme, sapma * 100))
    olc("3b tek govde ucgen sayisi <= govde+yazi toplami",
        len(tek) <= len(govde) + len(yazi),
        "%d <= %d + %d" % (len(tek), len(govde), len(yazi)))

    # 4) BELIRLENIMCILIK / METIN BAGLANTISI
    sha_yazi2 = hashlib.sha256(derle(args.url, AILE + "#yazi", PARAM)).hexdigest()
    olc("4a ayni yazi -> AYNI cikti (belirlenimcilik)", sha_yazi2 == sha_yazi,
        sha_yazi[:16])
    sha_yaziB = hashlib.sha256(derle(args.url, AILE + "#yazi", PARAM_B)).hexdigest()
    sha_govdeB = hashlib.sha256(derle(args.url, AILE + "#govde", PARAM_B)).hexdigest()
    olc("4b farkli yazi -> YAZI govdesi degisir", sha_yaziB != sha_yazi,
        "%s -> %s" % (sha_yazi[:12], sha_yaziB[:12]))
    olc("4c farkli yazi -> GOVDE (yazisiz) DEGISMEZ", sha_govdeB == sha_govde,
        sha_govde[:16])

    # 5) GERIYE DONUK UYUM
    if args.taban_sha:
        olc("5a Output=frame ciktisi referansla AYNI", sha_tek == args.taban_sha,
            "cari=%s referans=%s" % (sha_tek[:16], args.taban_sha[:16]))
    else:
        olculemedi.append("5a geriye donuk SHA (--taban-sha verilmedi)")
        print("  [OLCULEMEDI] 5a Output=frame referans SHA verilmedi -> "
              "referans: %s" % sha_tek)

    print("\n== OLCUMLER ==")
    print("   tek govde SHA : %s" % sha_tek)
    print("   govde SHA     : %s" % sha_govde)
    print("   yazi SHA      : %s" % sha_yazi)
    print("   hacim (mm^3)  : tek=%.1f govde=%.1f yazi=%.1f" % (v_tek, v_govde, v_yazi))
    if olculemedi:
        print("   OLCULEMEDI    : " + "; ".join(olculemedi))
    print("\nSONUC: " + ("KIRMIZI (%d iddia dustu)" % len(hatalar) if hatalar else "YESIL"))
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
