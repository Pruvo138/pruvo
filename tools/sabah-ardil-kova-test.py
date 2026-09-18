#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sabah spec'i KIRMIZI SEVİYESİ bataryası — `kral-sabah.py::kirmizi_siniflandir`.

18 Eyl 2026 (KraL-Tamirci-18Eyl): spec `ADET=8` bastı; 3'ü o an ZATEN kapalıydı
(ardılı success), 5'i canlıydı — ikisi aynı sayıya çöküyordu ve satırda SHA yoktu.
Kırmızı artık iş akışı+dal SEVİYESİNDEN (en yeni hükümlü ardıl) okunur.

Her vaka SAF fonksiyonu sahte koşum listesiyle çağırır: gh YOK, ağ YOK, disk
yazımı yalnız tempfile (fake gh + mutant kopyası; TemporaryDirectory temizler).

  V1 ardılı success                     -> KAPANDI, canli=0 kapanan=1
  V2 ardıl yok                          -> CANLI: ardıl hüküm YOK
  V3 ardıl yalnız cancelled             -> CANLI (cancelled hüküm DEĞİL)
  V4 ardıllar failure sonra success     -> KAPANDI (EN YENİ hüküm; liste sırası karışık)
  V5 ardıllar success sonra failure     -> CANLI: ardılı failure
  V6 başka iş akışının success'i        -> kapatmaz (ad ekseni)
  V7 başka dalın success'i              -> kapatmaz (dal ekseni)
  V8 ardıl sürüyor                      -> CANLI ∧ hükümsüz kovasında görünür
  V9 18 Eyl 03:20Z anlık görüntüsü      -> ADET=8 · CANLI=5 · ARDILI_YESIL=3
  V10 bugunun_kirmizilari (fake gh)     -> blok `CANLI=` taşır ∧ ADET TÜM kırmızılar (anlam değişmedi)
  M1 MUTANT ardil_hukum hep None        -> V1 KIRMIZI
  M2 MUTANT ad ekseni düşer             -> V6 KIRMIZI
  M3 MUTANT en-yeni seçimi ilk-bulunan  -> V4 KIRMIZI
  (her mutantta kontrol V2 YEŞİL kalır — hedef-kol atfı)

Koşum: python3 tools/sabah-ardil-kova-test.py   (rc=0 = hepsi beklenen)
"""

import datetime as dt
import importlib.util
import os
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "tools", "sabah-teslim", "kral-sabah.py")

GUN = dt.date(2026, 9, 18)
SB = "Nöbet şeridi (SERIT B — yayını BLOKLAMAZ)"
BD = "Build & deploy to GitHub Pages"

MUTANTLAR = {
    "M1": ("    return en_yeni\n", "    return None  # MUTANT\n", "V1"),
    "M2": ('        if d.get("name") != run.get("name") or d.get("headBranch") != run.get("headBranch"):\n',
           '        if d.get("headBranch") != run.get("headBranch"):  # MUTANT\n', "V6"),
    "M3": ("        if en_yeni_t is None or t > en_yeni_t:\n",
           "        if en_yeni_t is None:  # MUTANT\n", "V4"),
}


def modul_yukle(yol, ad):
    s = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def k(ad, saat, conc, sha, rid, dal="main", durum="completed", gun=GUN):
    return {"name": ad, "headBranch": dal, "status": durum, "conclusion": conc,
            "createdAt": "%sT%sZ" % (gun.isoformat(), saat), "headSha": sha + "0" * 32,
            "databaseId": rid}


def vakalar(mod, gun=GUN):
    s = lambda data: mod.kirmizi_siniflandir(data, gun)
    kk = lambda *a, **kw: k(*a, gun=gun, **kw)
    sonuc = {}

    r, _, c, kp = s([kk(BD, "02:00:00", "success", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V1"] = (c == 0 and kp == 1 and "KAPANDI" in r[0] and "`bbbbbbbb`" in r[0], r)

    r, _, c, kp = s([kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V2"] = (c == 1 and kp == 0 and "CANLI: ardıl hüküm YOK" in r[0], r)

    r, _, c, kp = s([kk(BD, "02:00:00", "cancelled", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    satir = [x for x in r if "run 1 " in x]
    sonuc["V3"] = (c == 2 and kp == 0 and satir and "CANLI: ardıl hüküm YOK" in satir[0], r)

    r, _, c, kp = s([kk(BD, "01:00:00", "failure", "aaaaaaaa", 1),
                     kk(BD, "02:00:00", "failure", "bbbbbbbb", 2),
                     kk(BD, "03:00:00", "success", "cccccccc", 3)])
    satir = [x for x in r if "run 1 " in x]
    sonuc["V4"] = (kp == 2 and c == 0 and satir and "`cccccccc` success" in satir[0], r)

    r, _, c, kp = s([kk(BD, "03:00:00", "failure", "cccccccc", 3),
                     kk(BD, "02:00:00", "success", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    satir = [x for x in r if "run 1 " in x]
    sonuc["V5"] = (satir and "CANLI: ardılı `cccccccc` failure" in satir[0] and c == 2, r)

    r, _, c, kp = s([kk(SB, "02:00:00", "success", "bbbbbbbb", 2),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V6"] = (c == 1 and kp == 0, r)

    r, _, c, kp = s([kk(BD, "02:00:00", "success", "bbbbbbbb", 2, dal="yan-dal"),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V7"] = (c == 1 and kp == 0, r)

    r, h, c, kp = s([kk(BD, "02:00:00", None, "bbbbbbbb", 2, durum="in_progress"),
                     kk(BD, "01:00:00", "failure", "aaaaaaaa", 1)])
    sonuc["V8"] = (c == 1 and len(h) == 1 and "sürüyor" in h[0], (r, h))

    # 18 Eyl 03:20Z anlık görüntüsü (gh run list, main, yeni→eski) — ölçülmüş koşumlar
    gercek = [
        kk(SB, "03:10:24", None, "84a60965", 35302195200, durum="in_progress"),
        kk(BD, "03:10:24", None, "84a60965", 35302195010, durum="in_progress"),
        kk(BD, "01:56:47", "success", "45616be8", 35297362223),
        kk(SB, "01:56:47", "failure", "45616be8", 35297362459),
        kk(SB, "01:35:35", "cancelled", "3e080a2c", 35295949469),
        kk(BD, "01:08:20", "failure", "6f01d13b", 35294096925),
        kk(SB, "01:08:20", "cancelled", "6f01d13b", 35294097073),
        kk(BD, "01:00:26", "cancelled", "fe082f84", 35293542967),
        kk(SB, "01:00:26", "cancelled", "fe082f84", 35293543235),
        kk(SB, "00:58:23", "cancelled", "6a3a6bfb", 35293398171),
        kk(BD, "00:58:22", "cancelled", "6a3a6bfb", 35293397856),
    ]
    r, h, c, kp = s(gercek)
    sonuc["V9"] = (len(r) == 8 and c == 5 and kp == 3 and len(h) == 2, (len(r), c, kp, len(h)))
    return sonuc


def v10_uctan_uca(mod):
    """bugunun_kirmizilari'yi fake gh ile koşar (ağ YOK)."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    import json
    data = [k(BD, "00:00:02", "success", "bbbbbbbb", 2, gun=bugun),
            k(BD, "00:00:01", "failure", "aaaaaaaa", 1, gun=bugun),
            k(SB, "00:00:01", "failure", "cccccccc", 3, gun=bugun)]
    with tempfile.TemporaryDirectory() as td:
        sahte = os.path.join(td, "gh")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write("#!%s\nimport sys\nsys.stdout.write(%r)\n" % (sys.executable, json.dumps(data)))
        os.chmod(sahte, 0o700)
        eski = (mod.gh_yolu, mod._repo_slug)
        mod.gh_yolu = lambda: (sahte, "test")
        mod._repo_slug = lambda: None
        try:
            hukum, blok, adet, _ = mod.bugunun_kirmizilari()
        finally:
            mod.gh_yolu, mod._repo_slug = eski
    ok = (hukum == "OK" and adet == 2 and "**CANLI=1**" in blok and "ARDILI_YESIL=1" in blok)
    return ok, (hukum, adet, blok[:160])


def main():
    mod = modul_yukle(KAYNAK, "kral_sabah_test")
    kirmizi = 0

    for ad, (ok, kanit) in sorted(vakalar(mod).items(), key=lambda x: int(x[0][1:])):
        print("%s %s %s" % ("YESIL " if ok else "KIRMIZI", ad, "" if ok else kanit))
        kirmizi += 0 if ok else 1
    ok, kanit = v10_uctan_uca(mod)
    print("%s V10 %s" % ("YESIL " if ok else "KIRMIZI", "" if ok else kanit))
    kirmizi += 0 if ok else 1

    with open(KAYNAK, encoding="utf-8") as f:
        govde = f.read()
    oldu = 0
    for mad, (capa, yama, hedef) in sorted(MUTANTLAR.items()):
        if govde.count(capa) != 1:
            print("KIRMIZI %s capa adedi=%d (beklenen 1)" % (mad, govde.count(capa)))
            kirmizi += 1
            continue
        with tempfile.TemporaryDirectory() as td:
            yol = os.path.join(td, "kral_sabah_mutant.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde.replace(capa, yama))
            mm = modul_yukle(yol, "kral_sabah_" + mad)
            sonuc = vakalar(mm)
        hedef_dustu = not sonuc[hedef][0]
        kontrol = sonuc["V2"][0]
        ok = hedef_dustu and kontrol
        oldu += 1 if ok else 0
        print("%s %s hedef=%s dustu=%d kontrol_V2=%d" % (
            "YESIL " if ok else "KIRMIZI", mad, hedef, int(hedef_dustu), int(kontrol)))
        kirmizi += 0 if ok else 1

    print("SABAH_ARDIL_KOVA VAKA=10 MUTANT_OLDU=%d/%d KIRMIZI=%d rc=%d" % (
        oldu, len(MUTANTLAR), kirmizi, 1 if kirmizi else 0))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
