#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — r2-upload.py `cdn_siz_readback` GERCEKTEN olculuyor mu?

"r2-upload-test.py yesil" tek basina kanit DEGILDIR ([[test-hatali-davranisi-kutsar]]).
Bu surucu CDN'SIZ varlik/readback kapisinin her eksenini TEK TEK bozar ve her bozmanin
kabul testini KIRMIZI yaktigini OLCER (kabul testi = r2-upload-test.py icindeki
CDN_A/B/C vakalari). Davranisi DEGISTIRMEYEN bir KONTROL mutanti da kosulur: o YESIL
kalmali — kalmazsa batarya "her degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur
([[beyan-edilmis-survivor]]).

Bozulan eksenler (hepsi negatif-onbellek arizasinin sinifindan, 14 Agu 2026 OLCULDU):
  1. FAIL-OPEN: yetki/ag hatasi 'yok' sanildi (raise -> False) -> "yok" ile "yetkim yok"
     karisir, readback sahte-yeşil "eksik" der.
  2. 404 -> VAR: olmayan nesne VAR sayildi (False -> True) -> CDN 404'unu dogrulamak
     yerine "var" der, negatif-onbellek TESPIT EDILEMEZ.
  3. KONTROL: docstring degisikligi (davranis DEGISMEZ) -> YESIL kalmali.

Mutasyon DAIMA gecici AYNA dizinine uygulanir (tools/ symlink'lenir, yalniz mutasyona
ugrayan dosya gercek kopya olur). Canli tools/ dizinine YAZILMAZ; kabul testi zaten
SAHTE S3 kullanir, gercek R2'ye/CDN'e NE OKUMA NE YAZMA gider.
Cokme (traceback) KIRMIZI SAYILMAZ: kabul testinin KENDI "SONUC:" satiri aranir
([[mutasyon-kaniti-yeniden-uretilebilir]]).

Calistir:  python3 tools/r2-cdn-negatif-onbellek-mutasyon.py   (0 = gecti, 1 = kaldi)
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KABUL = "r2-upload-test.py"
HEDEF = "r2-upload.py"

YESIL_IZ = "SONUC: TUM VAKALAR GECTI"
KIRMIZI_IZ = "SONUC: BASARISIZ"

# (ad, dosya, aranan_metin, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("1) FAIL-OPEN: yetki/ag hatasi 'yok' sanildi (raise -> False)",
     HEDEF,
     "        raise  # CDN_SIZ_FAIL_CLOSED: yetki/ag hatasi 'yok' sanilmaz",
     "        return False, None, None  # CDN_SIZ_FAIL_CLOSED: yetki/ag hatasi 'yok' sanilmaz",
     True),
    ("2) 404 -> VAR: olmayan nesne VAR sayildi (False -> True)",
     HEDEF,
     "            return False, None, None  # CDN_SIZ_YOK: nesne gercekten yok",
     "            return True, None, None  # CDN_SIZ_YOK: nesne gercekten yok",
     True),
    ("3) KONTROL MUTANTI (docstring — davranis DEGISMEZ) — YESIL kalmali",
     HEDEF,
     "R2 nesnesinin CDN'SIZ (S3 API) varlik + icerik sondasi -> (var, uzunluk, tip).",
     "R2 nesnesinin CDN'SIZ (S3 API) varlik + icerik sondasi v2 -> (var, uzunluk, tip).",
     False),
]


def ayna_kur():
    """tools/ symlink aynasi -> gecici kok doner (canli agaca YAZILMAZ)."""
    kok = tempfile.mkdtemp(prefix="r2-cdn-neg-mut-")
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
            print("        rc=%d  stdout: %s" % (r.returncode, (r.stdout or "")[-400:]))
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
