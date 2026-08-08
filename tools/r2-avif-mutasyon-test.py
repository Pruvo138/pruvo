#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — R2 R1 SIHIRLI-BAYT WHITELIST'I (AVIF ekseni) GERCEKTEN olculuyor mu?

9 Agu 2026'da r2-upload.py::R1 whitelist'i AVIF'e ACILDI. Whitelist GENISLETMEK, fail-closed
bir kapiyi sessizce fail-open'a cevirmenin en ucuz yoludur: `ftyp` GENEL bir ISO-BMFF kutu
basligidir ve mp4/mov/heic de tasir -> "AVIF destegi ekledim" diyen tek satirlik bir gevsetme
kapiyi HER ISO-BMFF govdesine acar ve kimse kirmizi gormez.

"r2-upload-test.py yesil" tek basina kanit DEGILDIR: yesil, testin neyi olctugune baglidir
([[test-hatali-davranisi-kutsar]]). Bu surucu AVIF kabulunun her eksenini TEK TEK bozar ve her
bozmanin kabul testini KIRMIZI yaktigini OLCER. Ayrica davranisi DEGISTIRMEYEN bir KONTROL
mutanti kosulur: o YESIL kalmali — kalmazsa batarya "her degisiklikte kirmizi" demektir ve
hicbir sey olcmuyordur ([[beyan-edilmis-survivor]] · [[fikstur-degeri-mutasyon-koru]]).

🔴 KONTROL MUTANTI OLCULEN EKSENIN ICINDEN SECILDI: `AVIF_MARKALARI` demetinin SIRASI
degistirilir. Ayni tabloya dokunur (yani "mutasyon alakasiz yere dustu" degildir) ama uyelik
testi (`in`) sirasiz oldugu icin davranis DEGISMEZ -> YESIL kalmali.

Bozulan eksenler:
  1. MARKA kontrolu KALKTI (`ftyp` tek basina yeterli sayildi) -> mp4/heic KABUL edilirdi
  2. Marka kumesi HEIF'e genisledi (fail-open yonu: whitelist gevsemesi)
  3. OFSET kontrolu gevsedi (sabit offset yerine ARAMA) -> `ftypavif` govdenin herhangi bir
     yerinde gecince kabul edilirdi
  4. Marka esitligi PREFIX'e dondu -> kesik/uydurma marka kabul edilirdi
  5. AVIF kolu tamamen DUSTU (regresyon: gercek AVIF yeniden reddedilir)
  6. `.avif` UZANTI esleme kolu DUSTU -> R3 uzanti/govde uyusmazlik uyarisi susardi
  7. KONTROL: davranis DEGISMEYEN degisiklik -> YESIL kalmali

Mutasyon DAIMA gecici bir AYNA dizinine uygulanir (tools/ symlink'lenir, yalniz mutasyona
ugrayan dosya gercek kopya olur). Canli tools/ dizinine YAZILMAZ; kabul testi zaten MOCK S3
kullanir, gercek R2'ye NE OKUMA NE YAZMA gider.
Cokme (traceback) KIRMIZI SAYILMAZ: kabul testinin KENDI "SONUC:" satiri aranir
([[mutasyon-kaniti-yeniden-uretilebilir]]).

Calistir:  python3 tools/r2-avif-mutasyon-test.py   (0 = gecti, 1 = kaldi)
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

_AVIF_KOL = ('    if len(data) >= 12 and data[4:8] == b"ftyp" '
             'and data[8:12] in AVIF_MARKALARI:')

# (ad, dosya, aranan_metin, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("1) MARKA kontrolu KALKTI (`ftyp` tek basina yeterli — mp4/mov/heic acilirdi)",
     HEDEF,
     _AVIF_KOL,
     '    if len(data) >= 12 and data[4:8] == b"ftyp":',
     True),
    ("2) marka kumesi HEIF'e genisledi (whitelist fail-open yonunde gevsedi)",
     HEDEF,
     'AVIF_MARKALARI = (b"avif", b"avis")',
     'AVIF_MARKALARI = (b"avif", b"avis", b"heic", b"mp42")',
     True),
    ("3) OFSET kontrolu gevsedi (sabit offset yerine govdede ARAMA)",
     HEDEF,
     _AVIF_KOL,
     '    if len(data) >= 12 and any(data.find(b"ftyp" + _m) >= 0 '
     'for _m in AVIF_MARKALARI):',
     True),
    ("4) marka esitligi PREFIX'e dondu (kesik/uydurma marka kabul edilirdi)",
     HEDEF,
     _AVIF_KOL,
     '    if len(data) >= 12 and data[4:8] == b"ftyp" '
     'and data[8:10] in (b"av",):',
     True),
    # 🔴 CAPA IKI SATIRLIK: `        return "avif"` tek basina format_belirle VE
    # uzanti_format icinde IKI KEZ geciyor -> tek satirlik capa "1 olmali" kontrolune
    # takilir ve mutant SESSIZCE uygulanamaz olurdu.
    ("5) AVIF kolu tamamen DUSTU (regresyon — gercek AVIF yine reddedilir)",
     HEDEF,
     _AVIF_KOL + '\n        return "avif"\n',
     _AVIF_KOL + "\n        pass\n",
     True),
    ("6) `.avif` UZANTI esleme kolu DUSTU (R3 uyusmazlik uyarisi susardi)",
     HEDEF,
     '    if k.endswith(".avif"):\n        return "avif"\n',
     '    if False:\n        return "avif"\n',
     True),
    ("7) KONTROL MUTANTI (marka demetinin SIRASI degisti — davranis DEGISMEZ) — YESIL kalmali",
     HEDEF,
     'AVIF_MARKALARI = (b"avif", b"avis")',
     'AVIF_MARKALARI = (b"avis", b"avif")',
     False),
]


def ayna_kur():
    """tools/ symlink aynasi -> gecici kok doner (canli agaca YAZILMAZ)."""
    kok = tempfile.mkdtemp(prefix="r2-avif-mut-")
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
