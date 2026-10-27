#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""siparis-kampanya-oku.py kabul + mutant testi (agsiz, sqlite fiksturu, <2 s).

BaBa tik 244 D kabul kumesi: fikstur + mutant ("etiket bos -> atif-yok, OLCULEMEDI degil").
Mutantlar ARACIN IZOLE KOPYASINDA kosar (tempdir); canli govde DEGISMEZ.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "siparis-kampanya-oku.py")
GUN = "2026-10-26"
GIZLI_AD = "Gizli Musteri Adi"
GIZLI_TEL = "905550001122"

# (siparis_no, tarih, durum, kanal, tutar, kargo, atif)
SATIRLAR = [
    ("PR-1", "2026-10-26T10:19:42.078Z", "uretimde", "site", 320000, 0, '{"ref":"REF:GS-GY-AB12"}'),
    ("PR-2", "2026-10-26T14:32:35.207Z", "bekliyor", "site", 72000, 25000, '{"ref":"REF:OG-G0-CD34"}'),
    ("PR-3", "2026-10-26T01:00:00.000Z", "odendi", "site", 10000, 0, '{"ref":"REF:GS-FIG-EF56"}'),
    ("PR-4", "2026-10-26T02:00:00.000Z", "tamamlandi", "site", 20000, 0, '{"ref":"REF:GS-YP-GH78"}'),
    ("PR-5", "2026-10-26T03:00:00.000Z", "kargolandi", "site", 30000, 0, '{"ref":"REF:GS-UC-IJ90"}'),
    ("PR-6", "2026-10-26T04:00:00.000Z", "odendi", "site", 40000, 0, '{"ref":"REF:GS-BYP-KL12"}'),
    ("PR-7", "2026-10-26T05:00:00.000Z", "odendi", "site", 50000, 0, '{}'),
    ("PR-8", "2026-10-26T06:00:00.000Z", "odendi", "site", 60000, 0, ''),
    ("PR-9", "2026-10-26T07:00:00.000Z", "odendi", "whatsapp", 70000, 0, ''),
    ("PR-10", "2026-10-26T08:00:00.000Z", "iptal", "site", 80000, 0, '{"ref":"REF:GS-GY-MN34"}'),
    ("PR-11", "2026-10-26T09:00:00.000Z", "odendi", "site", 90000, 0, '{"ref":"bozuk"}'),
    # GUN DISI — sayilmamali
    ("PR-12", "2026-10-25T23:59:59.999Z", "odendi", "site", 99900, 0, '{"ref":"REF:GS-GY-OP56"}'),
    ("PR-13", "2026-10-27T00:00:00.000Z", "odendi", "site", 99900, 0, '{"ref":"REF:GS-GY-QR78"}'),
]

BEKLENEN = [
    "D1_SIPARIS gun=2026-10-26 odenmis=9/6900.00 bekleyen=1/970.00 iptal=1/800.00 TOPLAM=11",
    "SIPARIS_KAMPANYA gun=2026-10-26 figur-arama=1/100.00 gclid=1/3200.00 "
    "yeniden-pazarlama=1/200.00 ucretli-diger=1/300.00 ucretli-grup=1/400.00 organik=0/0.00 "
    "whatsapp=1/700.00 atif-yok=3/2000.00",
    "SIPARIS_BEKLEYEN gun=2026-10-26 figur-arama=0/0.00 gclid=0/0.00 yeniden-pazarlama=0/0.00 "
    "ucretli-diger=0/0.00 ucretli-grup=0/0.00 organik=1/970.00 whatsapp=0/0.00 atif-yok=0/0.00",
]

gecti = 0
kaldi = 0
SESSIZ = False          # mutant kosumunda beklenen kirmizilar basilmaz (yanlis okunmasin)


def iddia(kosul, ad, detay=""):
    global gecti, kaldi
    if kosul:
        gecti += 1
        if not SESSIZ:
            print("  ✅ " + ad)
    else:
        kaldi += 1
        if not SESSIZ:
            print("  ❌ " + ad + ((" | " + detay) if detay else ""))


def vt_kur(dizin, satirlar):
    yol = os.path.join(dizin, "t.db")
    c = sqlite3.connect(yol)
    c.execute("CREATE TABLE siparisler (siparis_no TEXT, tarih TEXT, durum TEXT, kanal TEXT, "
              "tutar_kurus INTEGER, kargo_kurus INTEGER, atif TEXT, musteri_ad TEXT, "
              "musteri_tel TEXT, musteri_notu TEXT)")
    for s in satirlar:
        c.execute("INSERT INTO siparisler VALUES (?,?,?,?,?,?,?,?,?,?)",
                  s + (GIZLI_AD, GIZLI_TEL, "gizli not"))
    c.commit()
    c.close()
    return yol


def kos(arac, *arg):
    p = subprocess.run([sys.executable, arac] + list(arg), capture_output=True, text=True,
                       timeout=60)
    return p.returncode, p.stdout


def suit(arac, dizin, sessiz=False):
    """Kabul vakalari. Dondurur: kalan iddia sayisi (mutant icin)."""
    global gecti, kaldi
    once_g, once_k = gecti, kaldi
    vt = vt_kur(dizin, SATIRLAR)

    rc, out = kos(arac, "--gun", GUN, "--vt", vt)
    satir = [s for s in out.splitlines() if s.strip()]
    iddia(rc == 0, "V1 rc=0", out)
    iddia(satir == BEKLENEN, "V1 uc satir BIREBIR (sinif + tutar + gun penceresi)",
          "\n".join(satir))
    iddia("atif-yok=3/2000.00" in out and "OLCULEMEDI" not in out,
          "V2 bos etiket ('{}', '', kalip disi) -> atif-yok, OLCULEMEDI DEGIL")
    iddia("whatsapp=1/700.00" in out, "V3 kanal=whatsapp -> whatsapp (atif bos olsa da)")
    iddia(GIZLI_AD not in out and GIZLI_TEL not in out and "PR-" not in out,
          "V4 ciktida musteri adi/tel/siparis no YOK")

    bos = vt_kur(tempfile.mkdtemp(dir=dizin), [])
    rc, out = kos(arac, "--gun", GUN, "--vt", bos)
    iddia(rc == 0 and "TOPLAM=0" in out, "V5 siparis yok -> rc 0 + sifir satiri", out)

    rc, out = kos(arac, "--gun", "2026-1-7", "--vt", vt)
    iddia(rc == 2 and "sebep=GUN-BICIMI" in out, "V6 bicim disi gun -> rc 2", out)

    js = os.path.join(dizin, "bozuk.json")
    with open(js, "w") as f:
        json.dump([{"results": [{"durum": "odendi"}]}], f)
    rc, out = kos(arac, "--gun", GUN, "--d1-json", js)
    iddia(rc == 3 and "sebep=D1-SEKIL" in out, "V7 eksik alanli D1 cevabi -> rc 3 D1-SEKIL", out)

    garip = vt_kur(tempfile.mkdtemp(dir=dizin),
                   [("PR-X", "2026-10-26T01:00:00Z", "uzayda", "site", 1, 0, "")])
    rc, out = kos(arac, "--gun", GUN, "--vt", garip)
    iddia(rc == 3 and "BILINMEYEN-DURUM" in out, "V8 bilinmeyen durum -> rc 3 (sessiz siniflama yok)",
          out)

    zarf = os.path.join(dizin, "zarf.json")
    with open(zarf, "w") as f:
        json.dump([{"results": [{"durum": "odendi", "kanal": "site", "tutar_kurus": 100,
                                 "kargo_kurus": 0, "ref": "REF:GS-YP-AAAA"}], "success": True}], f)
    rc, out = kos(arac, "--gun", GUN, "--d1-json", zarf)
    iddia(rc == 0 and "yeniden-pazarlama=1/1.00" in out, "V9 canli zarf ayristiricisi (liste)", out)
    return kaldi - once_k


MUTANTLAR = [
    ("MA etiket bos -> OLCULEMEDI (BaBa tik 244 D kabul mutanti)",
     '        return "atif-yok"\n', '        return "OLCULEMEDI"\n'),
    ("MB YP haritadan duser (yeniden-pazarlama ucretli-grup olur)",
     '"YP": "yeniden-pazarlama",', ""),
    ("MC bekliyor odenmis sayilir",
     'ODENMIS = frozenset(("odendi", ', 'ODENMIS = frozenset(("bekliyor", "odendi", '),
    ("MD whatsapp kanali okunmaz (atif-yok'a duser)",
     '    if (kanal or "").strip().lower() == "whatsapp":\n',
     '    if False:\n'),
    ("ME gun filtresi kalkar (gun disi siparis sayilir)",
     "WHERE substr(tarih, 1, 10) = ", "WHERE 1 = 1 OR substr(tarih, 1, 10) = "),
    ("MG json_valid korumasi kalkar (atif '' olan gun OLCULEMEDI'ye duser)",
     "CASE WHEN json_valid(atif) THEN json_extract(atif, '$.ref') END AS ref ",
     "json_extract(atif, '$.ref') AS ref "),
    ("MF bilinmeyen durum sessizce bekleyen sayilir",
     '            raise DurumHatasi(durum or "<bos>")\n',
     '            kova, sk = ozet["bekleyen"], bek[s]\n'),
]


def mutant_kos():
    kaynak = open(ARAC, encoding="utf-8").read()
    olu = 0
    for ad, ara, yaz in MUTANTLAR:
        if kaynak.count(ara) != 1:
            iddia(False, "MUTANT capasi bulunamadi/tekil degil: " + ad)
            continue
        d = tempfile.mkdtemp(prefix="sko-mut-")
        try:
            kopya = os.path.join(d, "siparis-kampanya-oku.py")
            govde = kaynak.replace(ara, yaz)
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(govde)
            print("\n▶ " + ad)
            global gecti, kaldi, SESSIZ
            g0, k0 = gecti, kaldi
            SESSIZ = True
            try:
                yakalandi = suit(kopya, d) > 0
            finally:
                SESSIZ = False
            gecti, kaldi = g0, k0                     # mutant iddialari sayaca girmez
            iddia(yakalandi, "MUTANT OLDU: " + ad)
            olu += 1 if yakalandi else 0
        finally:
            shutil.rmtree(d, ignore_errors=True)      # yalniz kendi tempdir'imiz
    return olu


def main():
    d = tempfile.mkdtemp(prefix="sko-")
    try:
        print("▶ KABUL (canli govde)")
        suit(ARAC, d)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    olu = mutant_kos()
    print("\nSONUC: iddia %d gecti | %d KALDI · mutant %d/%d OLU" % (
        gecti, kaldi, olu, len(MUTANTLAR)))
    return 0 if kaldi == 0 and olu == len(MUTANTLAR) else 1


if __name__ == "__main__":
    sys.exit(main())
