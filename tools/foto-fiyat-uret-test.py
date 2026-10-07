#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FOTO FIYAT URETECI kabul testi (tools/foto-fiyat-uret.py). PARA sinifi: hata SESSIZ olur
(yanlis satir canliya yazilirsa siparis normal akar, fiyat yanlis tahsil edilir).

  F1 CANLI ESI   : canli = plaket 60..300 x1000 (25 satir) -> plaket fark 0 · litofan 13 eklenecek ·
                   G2 6 D turu: isimlik 20 · qr 12 · logo 18 · muhur 9 · sablon 20 · yapboz 10 eklenecek (G2b: 100–190)
                   (80..200, adim 10, mm x 1000) · ARALIK_DISI 0 · DELETE 0 · rc 0
  F2 ARALIK DISI : canlida plaket 50/65/310 + manifest disi tur -> plaket SILINECEK 3 (DELETE 3) ·
                   YABANCI 1 ve yabanciya DELETE YOK
  F3 DEGISECEK   : canlida plaket 120 = 44900 -> DEGISECEK 1, SQL 120000'e gunceller
  F4 KURU YAZMAZ : sahte `npx` PATH'te: fikstur koluyla wrangler cagrisi 0; fikstursuz kolda
                   yalniz SELECT (`--command`), `--file` 0; canli okunamazsa rc 3 HAL=OLCULEMEDI
  F5 FORMUL      : bilinmeyen formul -> rc 1, SQL basilmaz
MUTANTLAR (araç kopyasi gecici dizinde; agaca yazim YOK): M1 fiyat x100 · M2 adim yok sayildi ·
M3 silinecek dusuruldu · M4 KURU kapisi silindi -> hedef grup KIRMIZI; M0 yorum -> hepsi YESIL.
Son satir `SURVIVOR=<n>`. CIKIS: 0 yesil · 1 kirmizi.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "foto-fiyat-uret.py")


def wrangler_json(satirlar):
    return json.dumps([{"results": satirlar, "success": True, "meta": {}}])


def plaket_canli():
    return [{"tur": "plaket", "olcu_mm": mm, "fiyat_kurus": mm * 1000} for mm in range(60, 301, 10)]


def kos(arac, gecici, satirlar=None, argumanlar=(), kok=KOK, sahte_npx=True):
    """Araci kosar. Doner: (rc, stdout, npx_cagrilari[list])."""
    env = dict(os.environ)
    iz = os.path.join(gecici, "npx-iz.txt")
    if os.path.exists(iz):
        os.unlink(iz)
    if sahte_npx:
        bin_d = os.path.join(gecici, "bin")
        os.makedirs(bin_d, exist_ok=True)
        npx = os.path.join(bin_d, "npx")
        with open(npx, "w") as f:
            f.write("#!/bin/sh\necho \"$*\" >> '%s'\necho 'baglanti yok' >&2\nexit 1\n" % iz)
        os.chmod(npx, stat.S_IRWXU)
        env["PATH"] = bin_d + os.pathsep + env.get("PATH", "")
    komut = [sys.executable, arac, "--kok", kok] + list(argumanlar)
    if satirlar is not None:
        fx = os.path.join(gecici, "canli.json")
        with open(fx, "w") as f:
            f.write(wrangler_json(satirlar))
        komut += ["--canli-json", fx]
    p = subprocess.run(komut, capture_output=True, text=True, env=env)
    cagri = open(iz).read().splitlines() if os.path.exists(iz) else []
    return p.returncode, p.stdout, cagri


def alan(cikti, tur):
    for s in cikti.splitlines():
        if s.startswith("TUR=%s " % tur):
            return dict(x.split("=", 1) for x in s.split())
    return {}


def ozet(cikti):
    for s in cikti.splitlines():
        if s.startswith("YABANCI="):
            return dict(x.split("=", 1) for x in s.split())
    return {}


def senaryolar(arac, gecici):
    s = {}
    # F1
    rc, o, c = kos(arac, gecici, plaket_canli())
    p, l, z = alan(o, "plaket"), alan(o, "litofan"), ozet(o)
    ins = [x for x in o.splitlines() if x.startswith("INSERT")]
    beklenen_l = ["('litofan', %d, %d," % (mm, mm * 1000) for mm in range(80, 201, 10)]
    # G2 (7 Eki 2026): 6 D turu, mimar kararindaki satir sayilari (aralik / 10 mm adim).
    g2 = {"isimlik": (60, 250, 20), "qr": (40, 150, 12), "logo": (30, 200, 18), "muhur": (20, 100, 9),
          "sablon": (60, 250, 20), "yapboz": (100, 190, 10)}  # G2b: 280 -> 190 (tek plaka)
    g2_ok = all(alan(o, k).get("PLAN") == str(n) and alan(o, k).get("EKLENECEK") == str(n) and
                all(any("('%s', %d, %d," % (k, mm, mm * 1000) in x for x in ins) for mm in range(a, b + 1, 10))
                for k, (a, b, n) in g2.items())
    toplam = 13 + sum(n for _, _, n in g2.values())
    s["F1"] = (rc == 0 and p.get("PLAN") == "25" and p.get("CANLI") == "25" and p.get("EKLENECEK") == "0" and
               p.get("SILINECEK") == "0" and p.get("DEGISECEK") == "0" and l.get("PLAN") == "13" and
               l.get("EKLENECEK") == "13" and z.get("ARALIK_DISI") == "0" and z.get("FARK_TOPLAM") == str(toplam) and
               len(ins) == toplam and g2_ok and all(any(b in x for x in ins) for b in beklenen_l) and
               not any("'plaket'" in x for x in ins) and "DELETE" not in o and z.get("KIP") == "KURU")
    # F2
    canli = plaket_canli() + [{"tur": "plaket", "olcu_mm": 50, "fiyat_kurus": 50000},
                              {"tur": "plaket", "olcu_mm": 65, "fiyat_kurus": 65000},
                              {"tur": "plaket", "olcu_mm": 310, "fiyat_kurus": 310000},
                              {"tur": "anahtarlik", "olcu_mm": 100, "fiyat_kurus": 100000}]
    rc, o, c = kos(arac, gecici, canli)
    p, z = alan(o, "plaket"), ozet(o)
    dele = [x for x in o.splitlines() if x.startswith("DELETE")]
    s["F2"] = (rc == 0 and p.get("SILINECEK") == "3" and len(dele) == 3 and z.get("YABANCI") == "1" and
               not any("anahtarlik" in x for x in dele) and
               all(any("olcu_mm = %d;" % mm in x for x in dele) for mm in (50, 65, 310)))
    # F3
    canli = [dict(r, fiyat_kurus=44900) if r["olcu_mm"] == 120 else r for r in plaket_canli()]
    rc, o, c = kos(arac, gecici, canli)
    p = alan(o, "plaket")
    s["F3"] = (rc == 0 and p.get("DEGISECEK") == "1" and p.get("EKLENECEK") == "0" and
               any(x.startswith("INSERT") and "('plaket', 120, 120000," in x for x in o.splitlines()))
    # F4
    rc1, o1, c1 = kos(arac, gecici, plaket_canli())
    rc2, o2, c2 = kos(arac, gecici, None)
    s["F4"] = (rc1 == 0 and c1 == [] and rc2 == 3 and "HAL=OLCULEMEDI" in o2 and len(c2) == 1 and
               "--command" in c2[0] and "SELECT" in c2[0] and not any("--file" in x for x in c2) and
               "INSERT" not in o2)
    # F5
    kk = os.path.join(gecici, "kok-f5")
    os.makedirs(kk, exist_ok=True)
    veri = open(os.path.join(KOK, "foto-uretim-veri.js"), encoding="utf-8").read()
    with open(os.path.join(kk, "foto-uretim-veri.js"), "w", encoding="utf-8") as f:
        f.write(veri.replace('formul: "mm_x_10tl", adim_mm: 10', 'formul: "bilinmez", adim_mm: 10'))
    rc, o, c = kos(arac, gecici, plaket_canli(), kok=kk)
    s["F5"] = rc == 1 and "INSERT" not in o and "formul" in o
    return s


MUTANTLAR = [
    ("M1 fiyat formulu x100", "return mm * 1000", "return mm * 100000", ["F1", "F2", "F3", "F4"]),  # 300 mm -> 10M ust siniri asar, KURU da rc 1
    ("M2 adim yok sayildi", "mm += adim", "mm += 1", ["F1", "F2", "F3"]),
    ("M3 silinecek dusuruldu", '"silinecek": sorted(ck - pk),', '"silinecek": [],', ["F2"]),
    ("M4 KURU kapisi silindi", "if not a.uygula or not sql:", "if not sql:", ["F1", "F2", "F3", "F4"]),
    ("M0 kontrol (yorum)", "# Manifesti tarayici dosyasindan okur", "# manifest okunur", []),
]


def main():
    hata = 0
    gecici = tempfile.mkdtemp(prefix="foto-fiyat-test-")
    try:
        s = senaryolar(ARAC, gecici)
        for k in sorted(s):
            print(("✅ " if s[k] else "❌ ") + k)
            hata += 0 if s[k] else 1
        kaynak = open(ARAC, encoding="utf-8").read()
        survivor = 0
        for ad, capa, yerine, hedef in MUTANTLAR:
            if kaynak.count(capa) != 1:
                print("❌ %s capa kayip/coklu" % ad)
                hata += 1
                continue
            mk = os.path.join(gecici, "mutant.py")
            with open(mk, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, yerine, 1))
            m = senaryolar(mk, gecici)
            kirmizi = sorted(x for x in m if not m[x])
            tuttu = kirmizi == sorted(hedef)
            print(("✅ " if tuttu else "❌ ") + "%s -> KIRMIZI %s (beklenen %s)" % (ad, kirmizi, sorted(hedef)))
            if not tuttu:
                hata += 1
                if hedef and not set(hedef) & set(kirmizi):
                    survivor += 1
        print("SURVIVOR=%d" % survivor)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print("SONUC: %s (%d hata)" % ("YESIL" if hata == 0 else "KIRMIZI", hata))
    return 0 if hata == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
