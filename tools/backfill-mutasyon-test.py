#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — backfill koruma kabul testi GERCEKTEN olcuyor mu?

"backfill-koruma-test.py yesil" tek basina kanit degildir: yesil, testin neyi olctugune
baglidir ([[test-hatali-davranisi-kutsar]]). Bu surucu --backfill yazma/koruma yolunu TEK
TEK bozar ve her bozmanin kabul testini KIRMIZI yaktigini OLCER. Ayrica davranisi
DEGISTIRMEYEN bir KONTROL mutanti kosulur: o YESIL kalmali — kalmazsa batarya "her
degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur.

Bozulan eksenler (hepsi gercek arizanin sinifindan):
  1. kucultme korumasi kalkti (eski SET davranisi geri geldi)
  2. None ile 0 ayrimi silindi ("arandi-bos" hucre bos sayildi)
  3. bayrak kapisi acildi (bayraksiz kosum de eziyor)
  4. fail-loud cikis kodu susturuldu (catisma varken exit 0)
  5. yazma yolu no-op'a dondu (koruma "hic yazmama"ya cokerse doldurma da olmez)
  6. marka dedup'i kalkti (ayni urun ayni marka icin iki kez sayildi)

Mutasyon DAIMA gecici bir AYNA dizinine uygulanir (tools/ symlink'lenir, yalniz mutasyona
ugrayan dosya gercek kopya olur). Canli tools/ dizinine YAZILMAZ; kabul testi zaten
SENTETIK fikstur kullanir, canli defter hicbir kolda ACILMAZ.
Cokme (traceback) KIRMIZI SAYILMAZ: kabul testinin KENDI "SONUC:" satiri aranir
([[mutasyon-kaniti-yeniden-uretilebilir]]).

Calistir:  python3 tools/backfill-mutasyon-test.py   (0 = gecti, 1 = kaldi)
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KABUL = "backfill-koruma-test.py"
HEDEF = "marka-kapsama.py"

# (ad, dosya, aranan_metin, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("1) kucultme korumasi KALKTI (her hucre yazilir — gercek ariza)",
     HEDEF,
     "                if mevcut is None:",
     "                if True:",
     True),
    ("2) None ile 0 ayrimi SILINDI ('arandi-bos' hucre bos sayildi)",
     HEDEF,
     "                if mevcut is None:",
     "                if not mevcut:",
     True),
    ("3) bayrak kapisi ACILDI (bayraksiz kosum de eziyor)",
     HEDEF,
     "            if ezmeye_izin_ver:",
     "            if True:",
     True),
    ("4) fail-loud cikis kodu SUSTURULDU (catisma varken exit 0)",
     HEDEF,
     "KOD_CATISMA = 3   #",
     "KOD_CATISMA = 0   #",
     True),
    ("5) yazma yolu NO-OP'a dondu (koruma 'hic yazmama'ya cokerse doldurma olur)",
     HEDEF,
     '    kayit["eklenen"] = int(hedef)',
     '    kayit["eklenen"] = int(kayit.get("eklenen", 0) or 0)',
     True),
    ("6) marka DEDUP'i kalkti (ayni urun ayni marka icin iki kez sayildi)",
     HEDEF,
     "            if kan is None or kan in gorulen:",
     "            if kan is None:",
     True),
    ("7) KONTROL MUTANTI (davranis DEGISMEZ) — YESIL kalmali",
     HEDEF,
     "            for plat in sorted(turetilen[marka]):",
     "            for plat in sorted(turetilen[marka].keys()):",
     False),
]


def ayna_kur():
    """tools/ symlink aynasi + index.html symlink -> gecici kok doner."""
    kok = tempfile.mkdtemp(prefix="backfill-mut-")
    os.makedirs(os.path.join(kok, "tools"))
    os.symlink(os.path.join(ROOT, "index.html"), os.path.join(kok, "index.html"))
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        if os.path.isfile(kaynak):
            os.symlink(kaynak, os.path.join(kok, "tools", ad))
    return kok


def kabul_kos(kok):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", KABUL)],
                       capture_output=True, text=True, env=env, timeout=300)
    return r


def mutasyon_uygula(kok, dosya, eski, yeni):
    """Symlink'i GERCEK (mutasyonlu) kopyayla degistir. Uygulandigini OLCER."""
    hedef = os.path.join(kok, "tools", dosya)
    src = open(os.path.join(TOOLS, dosya), encoding="utf-8").read()
    if src.count(eski) != 1:
        return None, "hedef metin kaynakta %d kez geciyor (1 olmali)" % src.count(eski)
    mut = src.replace(eski, yeni, 1)
    if mut == src:
        return None, "mutasyon metni DEGISTIRMEDI"
    os.unlink(hedef)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(mut)
    diskte = open(hedef, encoding="utf-8").read()
    if diskte != mut:
        return None, "diske yazilan icerik beklenenden farkli"
    if eski in diskte:
        return None, "eski metin HALA diskte (mutasyon uygulanmadi)"
    if yeni and yeni not in diskte:
        return None, "yeni metin diskte YOK"
    return diskte, None


FAILS = []
print("=== KONTROL KOSUMU (mutasyonsuz) — YESIL olmali ===")
_kok = ayna_kur()
_r = kabul_kos(_kok)
_temiz = _r.returncode == 0 and "SONUC: YESIL" in _r.stdout
print("  %s  ayna uzerinde mutasyonsuz kabul testi (rc=%d)"
      % ("PASS" if _temiz else "FAIL", _r.returncode))
if not _temiz:
    FAILS.append("mutasyonsuz ayna kosumu yesil degil")
    print(_r.stdout[-2500:])
    print(_r.stderr[-1500:])
shutil.rmtree(_kok, ignore_errors=True)

print("\n=== MUTANTLAR ===")
kirmizi_yanan = 0
beklenen_kirmizi = sum(1 for m in MUTANTLAR if m[4])
kontrol_sonuc = None
for ad, dosya, eski, yeni, kirmizi_bekle in MUTANTLAR:
    kok = ayna_kur()
    _, hata = mutasyon_uygula(kok, dosya, eski, yeni)
    if hata:
        print("  FAIL  %s -> MUTASYON UYGULANAMADI: %s" % (ad, hata))
        FAILS.append(ad + " (uygulanamadi)")
        shutil.rmtree(kok, ignore_errors=True)
        continue
    r = kabul_kos(kok)
    yesil = "SONUC: YESIL" in r.stdout
    kirmizi = "SONUC: KIRMIZI" in r.stdout
    coktu = not yesil and not kirmizi
    if kirmizi_bekle:
        ok = kirmizi and r.returncode != 0
        if ok:
            kirmizi_yanan += 1
        etiket = "KIRMIZI ✅" if ok else ("COKTU (kirmiziyla karismasin)" if coktu
                                         else "YESIL ❌ (mutant YAKALANMADI)")
        print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, etiket))
        if not ok:
            FAILS.append(ad)
            print("        rc=%d  stderr: %s" % (r.returncode, (r.stderr or "")[-300:]))
    else:
        kontrol_sonuc = "YESIL" if (yesil and r.returncode == 0) else "KIRMIZI"
        ok = kontrol_sonuc == "YESIL"
        print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol_sonuc))
        if not ok:
            FAILS.append(ad + " (kontrol mutanti kirmizi yandi: batarya olcmuyor)")
            print(r.stdout[-1500:])
    shutil.rmtree(kok, ignore_errors=True)

print("\nMUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
      % (kirmizi_yanan, beklenen_kirmizi, kontrol_sonuc or "KOSULMADI"))
if FAILS:
    print("SONUC: KIRMIZI ❌  (%d)" % len(FAILS))
    sys.exit(1)
print("SONUC: YESIL ✅")
sys.exit(0)
