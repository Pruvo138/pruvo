#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — R2 EZME KAPISI (r2-upload.py R6) GERCEKTEN olculuyor mu?

"r2-upload-test.py yesil" tek basina kanit DEGILDIR: yesil, testin neyi olctugune
baglidir ([[test-hatali-davranisi-kutsar]]). Bu surucu ezme kapisinin her eksenini TEK
TEK bozar ve her bozmanin kabul testini KIRMIZI yaktigini OLCER. Ayrica davranisi
DEGISTIRMEYEN bir KONTROL mutanti kosulur: o YESIL kalmali — kalmazsa batarya "her
degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur ([[beyan-edilmis-survivor]]).

Bozulan eksenler (hepsi gercek arizanin sinifindan — bu depoda BIR KEZ gerceklesti,
[[gorsel-anahtar-cakismasi]] · [[r2-sessiz-uzerine-yazma]]):
  1. varlik sondasi KALKTI (yazmadan once "var mi" HIC sorulmuyor — eski davranis)
  2. bayrak kapisi TERSE dondu (bayraksiz kosum eziyor, bayrakli kosum reddediyor)
  3. --kuru-prova NO-OP'a dondu (kuru prova yaziyor)
  4. kosullu yazma (IfNoneMatch) DUSTU (yaris penceresi sessizce acildi)
  5. 412 on-kosul ihlali "desteklenmiyor" sayildi (yaris ezmesi yutuldu)
  6. --ezmeye-izin-ver argparse VARSAYILANI True'ya kaydi (bayrak kapisi olu)
  7. KONTROL: davranis DEGISMEYEN degisiklik -> YESIL kalmali

Mutasyon DAIMA gecici bir AYNA dizinine uygulanir (tools/ symlink'lenir, yalniz mutasyona
ugrayan dosya gercek kopya olur). Canli tools/ dizinine YAZILMAZ; kabul testi zaten
MOCK S3 kullanir, gercek R2'ye NE OKUMA NE YAZMA gider.
Cokme (traceback) KIRMIZI SAYILMAZ: kabul testinin KENDI "SONUC:" satiri aranir
([[mutasyon-kaniti-yeniden-uretilebilir]]).

Calistir:  python3 tools/r2-ezme-mutasyon-test.py   (0 = gecti, 1 = kaldi)
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KABUL = "r2-upload-test.py"
HEDEF = "r2-upload.py"

YESIL_IZ = "SONUC: TUM VAKALAR GECTI"
KIRMIZI_IZ = "SONUC: BASARISIZ"

# (ad, dosya, aranan_metin, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("1) varlik sondasi KALKTI (yazmadan once 'var mi' sorulmuyor — gercek ariza)",
     HEDEF,
     "    mevcut = var_mi(key)                          # R6 sonda (yazmadan ONCE)",
     "    mevcut = False                                # R6 sonda (yazmadan ONCE)",
     True),
    ("2) bayrak kapisi TERSE dondu (bayraksiz kosum eziyor)",
     HEDEF,
     "    if mevcut and not ezmeye_izin_ver:",
     "    if mevcut and ezmeye_izin_ver:",
     True),
    ("3) --kuru-prova NO-OP'a dondu (kuru prova YAZIYOR)",
     HEDEF,
     "    if kuru_prova:",
     "    if False:",
     True),
    ("4) kosullu yazma DUSTU (IfNoneMatch gonderilmiyor — yaris penceresi acildi)",
     HEDEF,
     '                          IfNoneMatch="*")',
     "                          IfNoneMatch=None)",
     True),
    ("5) 412 on-kosul ihlali 'desteklenmiyor' sayildi (yaris ezmesi yutuldu)",
     HEDEF,
     "            if _onkosul_ihlali(exc):",
     "            if False:",
     True),
    ("6) --ezmeye-izin-ver argparse VARSAYILANI True (bayrak kapisi olu)",
     HEDEF,
     '    ap.add_argument("--ezmeye-izin-ver", dest="ezmeye_izin_ver", action="store_true",',
     '    ap.add_argument("--ezmeye-izin-ver", dest="ezmeye_izin_ver", action="store_false", default=True,',
     True),
    ("7) KONTROL MUTANTI (davranis DEGISMEZ) — YESIL kalmali",
     HEDEF,
     "        local, key = args[i], args[i + 1]",
     "        key, local = args[i + 1], args[i]",
     False),
]


def ayna_kur():
    """tools/ symlink aynasi -> gecici kok doner (canli agaca YAZILMAZ)."""
    kok = tempfile.mkdtemp(prefix="r2-ezme-mut-")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        if os.path.isfile(kaynak):
            os.symlink(kaynak, os.path.join(kok, "tools", ad))
    return kok


def kabul_kos(kok):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, os.path.join(kok, "tools", KABUL)],
                          capture_output=True, text=True, env=env, timeout=300)


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
_temiz = _r.returncode == 0 and YESIL_IZ in _r.stdout
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
    yesil = YESIL_IZ in r.stdout
    kirmizi = KIRMIZI_IZ in r.stdout
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
