#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — parite kaydi kuculme/gerileme kabul testi GERCEKTEN olcuyor mu?

"parite-kayit-test.py yesil" tek basina kanit DEGILDIR: yesil, testin neyi olctugune
baglidir ([[test-hatali-davranisi-kutsar]]). Bu surucu YAZAR (kuculme reddi) ve OKUYUCU
(gerileme ekseni) yollarini TEK TEK bozar ve her bozmanin kabul testini KIRMIZI
yaktigini OLCER. Davranisi DEGISTIRMEYEN bir KONTROL mutanti da kosulur: o YESIL
kalmali — kalmazsa batarya "her degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur
([[beyan-edilmis-survivor]]).

Bozulan eksenler:
  1. kuculme reddi KALKTI (eski SET davranisi geri geldi)
  2. bayrak kapisi TERSE dondu (bayraksiz kosum kuculuyor)
  3. --kuru-prova NO-OP'a dondu (kuru prova YAZIYOR)
  4. TAVAN kaynagi dustu (yalniz mevcut kayda bakiliyor — elle dusurup atlatilabilir)
  5. OKUYUCUDA gerileme karsilastirmasi olduruldu (dusus KIRMIZI yakmiyor)
  6. OKUYUCUDA tavan yoklugu SESSIZ gecildi (OLCULEMEDI yerine YESIL)
  7. kontrol mutanti sayilari kanit sayilmiyor (M3 12971 -> 1 serbest)
  8. CLI bayrak VARSAYILANI True'ya kaydi (bayrak kapisi olu)
  9. KONTROL: davranis DEGISMEYEN degisiklik -> YESIL kalmali

Mutasyon DAIMA gecici bir AYNA dizinine uygulanir (tools/ ve jenerator/test/ symlink'lenir,
yalniz mutasyona ugrayan dosya gercek kopya olur). Canli agaca YAZILMAZ; kabul testi
zaten SENTETIK gecici kok kullanir, canli parite kaydi hicbir kolda ACILMAZ.
Cokme (traceback) KIRMIZI SAYILMAZ: kabul testinin KENDI "SONUC:" satiri aranir
([[mutasyon-kaniti-yeniden-uretilebilir]]).

Calistir:  python3 tools/parite-kayit-mutasyon-test.py   (0 = gecti, 1 = kaldi)
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
JEN_TEST = os.path.join(ROOT, "jenerator", "test")
KABUL = "parite-kayit-test.py"
HEDEF = "tools/parite_kaydi.py"
SURUCU = "jenerator/test/rulman-uretilebilirlik-olcum.py"

# (ad, repo-rel dosya, aranan_metin, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("1) kuculme reddi KALKTI (eski SET davranisi — gercek ariza)",
     HEDEF,
     "    if kucultmeler and not ezmeye_izin_ver:",
     "    if False:",
     True),
    ("2) bayrak kapisi TERSE dondu (bayraksiz kosum kuculuyor)",
     HEDEF,
     "    if kucultmeler and not ezmeye_izin_ver:",
     "    if kucultmeler and ezmeye_izin_ver:",
     True),
    ("3) --kuru-prova NO-OP'a dondu (kuru prova YAZIYOR)",
     HEDEF,
     "    if kuru_prova:",
     "    if False:",
     True),
    ("4) TAVAN kaynagi dustu (yalniz mevcut kayda bakiliyor)",
     HEDEF,
     '        for kaynak, ref in (("kayit", eski_s.get(ad)), ("tavan", tavan.get(ad))):',
     '        for kaynak, ref in (("kayit", eski_s.get(ad)),):',
     True),
    ("5) OKUYUCUDA gerileme karsilastirmasi olduruldu",
     HEDEF,
     "        if v < ref:",
     "        if False:",
     True),
    ("6) OKUYUCUDA tavan yoklugu SESSIZ gecildi (OLCULEMEDI yerine devam)",
     HEDEF,
     "    if not isinstance(tavan, dict) or not tavan:",
     "    if False:",
     True),
    ("7) kontrol mutanti sayilari kanit SAYILMIYOR (M3 12971 -> 1 serbest)",
     HEDEF,
     '            if isaret == ">0" and isinstance(mut.get(ad), int) \\',
     '            if False and isinstance(mut.get(ad), int) \\',
     True),
    ("8) CLI bayrak VARSAYILANI True (bayrak kapisi olu)",
     SURUCU,
     '    ap.add_argument("--ezmeye-izin-ver", dest="ezmeye_izin_ver", action="store_true",',
     '    ap.add_argument("--ezmeye-izin-ver", dest="ezmeye_izin_ver", action="store_false", default=True,',
     True),
    ("9) KONTROL MUTANTI (davranis DEGISMEZ) — YESIL kalmali",
     HEDEF,
     "    for ad in sorted(tavan):",
     "    for ad in sorted(tavan.keys()):",
     False),
]


def _symlink_dizin(kaynak_dizin, hedef_dizin):
    os.makedirs(hedef_dizin, exist_ok=True)
    for ad in os.listdir(kaynak_dizin):
        kaynak = os.path.join(kaynak_dizin, ad)
        if os.path.isfile(kaynak):
            os.symlink(kaynak, os.path.join(hedef_dizin, ad))


def ayna_kur():
    """tools/ + jenerator/test/ symlink aynasi -> gecici kok (canli agaca YAZILMAZ)."""
    kok = tempfile.mkdtemp(prefix="parite-kayit-mut-")
    _symlink_dizin(TOOLS, os.path.join(kok, "tools"))
    _symlink_dizin(JEN_TEST, os.path.join(kok, "jenerator", "test"))
    return kok


def kabul_kos(kok):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, os.path.join(kok, "tools", KABUL)],
                          capture_output=True, text=True, env=env, timeout=300)


def mutasyon_uygula(kok, rel, eski, yeni):
    """Symlink'i GERCEK (mutasyonlu) kopyayla degistir. Uygulandigini OLCER."""
    hedef = os.path.join(kok, *rel.split("/"))
    src = open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()
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
for ad, rel, eski, yeni, kirmizi_bekle in MUTANTLAR:
    kok = ayna_kur()
    _, hata = mutasyon_uygula(kok, rel, eski, yeni)
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
