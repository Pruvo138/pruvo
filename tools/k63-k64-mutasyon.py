#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — K63 (cok kelimeli marka) + K64 (6502 m.11 ayip beyani).

NEDEN VAR: "testler yesil" tek basina kanit degildir; yesilin NEYI olctugu sorulmalidir.
Anlatilan batarya da kanit degildir ([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu
REPODA durur ve yeniden kosulabilir.

KABUL `rc` DEGIL **IDDIA AILESININ IZI**dir: her mutant, OLDURULMESI beklenen aileyi
(`🔴 IZ=<AILE>`) bastirmali. Cokme de rc=1 verir; yanlis aileden gelen kirmizi o ekseni
KANITLAMAZ. Ayrica her eksen icin KONTROL mutanti vardir: masum degisiklikte batarya
YESIL kalmali (asiri-duyarli nobetci de bozuk nobetcidir).

MUTASYON DAIMA KOPYAYA: gercek `tools/` agacina DOKUNULMAZ. Kopya bir gecici dizinde
sembolik baglarla kurulur, yalniz mutasyona ugrayan dosya GERCEK dosya olarak yazilir;
surucu bas/son `tools/` ozetini (sha256) karsilastirir, esit degilse KIRMIZI yanar
(SIGTERM/kesinti dahil agac kirlenmesin).

Kullanim:
    python3 tools/k63-k64-mutasyon.py
    python3 tools/k63-k64-mutasyon.py --ayrinti
Cikis: 0 = tum oldurucu mutantlar olduruldu + kontroller yesil · 1 = aksi.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARA = "makerworld-ara.py"
KAPI = "ayip-beyani-kapisi.py"
K63_TEST = "marka-cok-kelime-test.py"

_IZ_RE = re.compile(r"🔴 IZ=([A-ZÇĞİÖŞÜ0-9\-]+)")

# (etiket, hedef_dosya, kosulan, args, eski, yeni, beklenen_aile)
#   kosulan: mutasyonlu agacta calistirilacak betik
OLDURUCU = (
    # ---------------- K63 · POZITIF ekseni (genisletme gercekten var mi)
    ("K63-M1 ayrac sinifi tek boslupa daraltildi", ARA, K63_TEST, [],
     '_MARKA_AYRAC = r"[\\s\\-_.·]"', '_MARKA_AYRAC = r"[\\s]"', "POZITIF"),
    ("K63-M2 marka adi ayraclardan BOLUNMUYOR (eski tek-parca desen)", ARA, K63_TEST, [],
     'parcalar = [re.escape(p) for p in re.split(_MARKA_AYRAC + "+", m) if p]',
     'parcalar = [re.escape(m)] if m else []', "POZITIF"),
    # ---------------- K63 · NEGATIF ekseni (gurultu kapisi hala kapali mi)
    ("K63-M3 kelime siniri (lookaround) kaldirildi", ARA, K63_TEST, [],
     'return re.compile(r"(?<![%s])%s(?![%s])" % (_KELIME, govde, _KELIME))',
     'return re.compile(govde)', "NEGATIF"),
    ("K63-M4 parcalar arasi ayrac SERBEST METIN oldu (bitisiklik sarti dustu)",
     ARA, K63_TEST, [],
     'govde = (_MARKA_AYRAC + "*").join(parcalar)',
     'govde = ".*".join(parcalar)', "NEGATIF"),
    # ---------------- K63 · KOVA ekseni (telafi yolu acik mi)
    ("K63-M5 elenen_marka yeniden 'gorulen' sayildi", ARA, K63_TEST, [],
     'HUKUMLU_KOVALAR = ("adaylar", "elenen_cop", "elenen_nc", "zaten_ekli")',
     'HUKUMLU_KOVALAR = ("adaylar", "elenen_cop", "elenen_nc", "zaten_ekli", "elenen_marka")',
     "KOVA"),
    ("K63-M6 taniinmayan kova sessizce yutuluyor (fail-open)", ARA, K63_TEST, [],
     '    bilinmeyen = [k for k in havuz if k not in TUM_KOVALAR]\n'
     '    if bilinmeyen:\n'
     '        raise BilinmeyenKova(\n'
     '            "taniinmayan kova(lar): %s -> HUKUMLU_KOVALAR/KARARSIZ_KOVALAR\'da sinifla"\n'
     '            % ", ".join(sorted(bilinmeyen)))\n',
     '    bilinmeyen = []\n', "KOVA"),
    # ---------------- K63 · SABIT ekseni (tek kelimeli marka davranisi)
    ("K63-M7 tek kelimeli markada da bitisiklik gevsetildi", ARA, K63_TEST, [],
     'parcalar = [re.escape(p) for p in re.split(_MARKA_AYRAC + "+", m) if p]',
     'parcalar = [re.escape(p) for p in re.split(_MARKA_AYRAC + "+|(?<=.)(?=.)", m) if p]',
     "SABIT"),
    # ---------------- K64 · KANON-SEMA ekseni
    ("K64-M1 dort secenek sarti kaldirildi", KAPI, KAPI, ["--kendini-test"],
     '    if len(secenekler) != 4:', '    if len(secenekler) < 0:', "KANON-SEMA"),
    ("K64-M2 turetilen cumle secenekleri tasiyor mu denetimi olu", KAPI, KAPI,
     ["--kendini-test"],
     '        if kucult(s) not in c:\n'
     '            hatalar.append("turetilen cumle \'%s\' secenegini TASIMIYOR" % s)\n',
     '        if False:\n'
     '            hatalar.append("turetilen cumle \'%s\' secenegini TASIMIYOR" % s)\n',
     "KANON-SEMA"),
    # ---------------- K64 · KAPSAM ekseni
    ("K64-M3 cayma-yok tetigi koldan dustu", KAPI, KAPI, ["--kendini-test"],
     'return bool(TETIK_CAYMA.search(govde_kucuk)) or bool(TETIK_AYIP.search(govde_kucuk))',
     'return bool(TETIK_AYIP.search(govde_kucuk))', "KAPSAM"),
    ("K64-M4 'ayıp' kelime siniri kaldirildi (kayıp -> ayıp)", KAPI, KAPI,
     ["--kendini-test"],
     'TETIK_AYIP = re.compile(r"(?<![" + _ONEK + r"])ayıp")',
     'TETIK_AYIP = re.compile(r"ayıp")', "KAPSAM"),
    ("K64-M5 bos govde fail-open (OLCULEMEDI atilmiyor)", KAPI, KAPI, ["--kendini-test"],
     '        if not g.strip():\n            raise Olculemedi("bos govde -> %s" % ad)\n',
     '        if not g.strip():\n            continue\n', "KAPSAM"),
    # ---------------- K64 · SAPMA ekseni
    ("K64-M6 sapma hukmu daraltildi: yalniz secenek adedine bakiyor", KAPI, KAPI,
     ["--kendini-test"],
     '        if kanonik not in g:\n',
     '        if not all(kucult(s) in g for s in secenekler[:2]):\n', "SAPMA"),
    ("K64-M7 eksik secenek sebebi adlandirilmiyor", KAPI, KAPI, ["--kendini-test"],
     '    eksik = [s for s in secenekler if kucult(s) not in g]\n',
     '    eksik = []\n', "SAPMA"),
    # ---------------- K64 · TEMIZ-SAYIM ekseni
    ("K64-M8 ozet ikinci sayim noktasindan turuyor", KAPI, KAPI, ["--kendini-test"],
     '    return (len(kapsam), len(sapan), len(kapsam) - len(sapan))',
     '    return (len(kapsam), 0, len(kapsam))', "TEMIZ-SAYIM"),
)

# KONTROL mutantlari: masum degisiklik -> batarya YESIL kalmali.
KONTROL = (
    ("K63-C1 yorum satiri degisti", ARA, K63_TEST, [],
     "# 🔴 COK KELIMELI MARKA KORLUGU (K63, olculdu 12 Agu 2026)",
     "# 🔴 COK KELIMELI MARKA KORLUGU (K63; ayrintili olcum raporda)"),
    ("K63-C2 yerel degisken adi degisti", ARA, K63_TEST, [],
     '    govde = (_MARKA_AYRAC + "*").join(parcalar)\n'
     '    return re.compile(r"(?<![%s])%s(?![%s])" % (_KELIME, govde, _KELIME))',
     '    desen_govdesi = (_MARKA_AYRAC + "*").join(parcalar)\n'
     '    return re.compile(r"(?<![%s])%s(?![%s])" % (_KELIME, desen_govdesi, _KELIME))'),
    ("K64-C1 docstring degisti", KAPI, KAPI, ["--kendini-test"],
     '    """Turkce-duyarli kucultme (I -> ı, İ -> i)."""',
     '    """Turkce-duyarli kucultme (buyuk I noktasiz ı olur)."""'),
    ("K64-C2 ozet satirinin BICIMI degisti (sayilar ayni kaynaktan)", KAPI, KAPI,
     ["--kendini-test"],
     '    print("taranan yuzey: %d" % len(yuzeyler))',
     '    print("taranan yuzey sayisi: %d" % len(yuzeyler))'),
)


def _agac_ozeti():
    h = hashlib.sha256()
    for ad in sorted(os.listdir(TOOLS)):
        yol = os.path.join(TOOLS, ad)
        if not os.path.isfile(yol):
            continue
        h.update(ad.encode("utf-8"))
        with open(yol, "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest()


def _farm(hedef_dizin):
    """tools/ icerigini sembolik baglarla kopyala (gercek agac ASLA yazilmaz)."""
    for ad in os.listdir(TOOLS):
        os.symlink(os.path.join(TOOLS, ad), os.path.join(hedef_dizin, ad))


def _kos(dizin, betik, args):
    p = subprocess.run([sys.executable, os.path.join(dizin, betik)] + args,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _izler(cikti):
    return set(_IZ_RE.findall(cikti))


def _mutant_kur(dizin, hedef, eski, yeni):
    """Hedef dosyanin mutasyonlu KOPYASINI farm'a yaz. Doner: hata mesaji ya da None."""
    with open(os.path.join(TOOLS, hedef), encoding="utf-8") as f:
        kaynak = f.read()
    n = kaynak.count(eski)
    if n != 1:
        return "ikame metni %d kez bulundu (1 olmali)" % n
    mut = kaynak.replace(eski, yeni)
    if mut == kaynak:
        return "mutasyon UYGULANMADI"
    yol = os.path.join(dizin, hedef)
    os.unlink(yol)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mut)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ayrinti", action="store_true")
    args = ap.parse_args()

    bas_ozet = _agac_ozeti()
    olduruldu, hatali = 0, []
    kontrol_yesil, kontrol_hata = 0, []
    izler_by_aile = {}

    kok = tempfile.mkdtemp(prefix="k63k64-")
    try:
        # --- TABAN: mutasyonsuz farm YESIL olmali (batarya kendini yanlis yere yakmasin)
        taban = os.path.join(kok, "taban")
        os.mkdir(taban)
        _farm(taban)
        t1_rc, t1_out = _kos(taban, K63_TEST, [])
        t2_rc, t2_out = _kos(taban, KAPI, ["--kendini-test"])
        print("TABAN (mutasyonsuz): K63 testi rc=%d · K64 oz-test rc=%d" % (t1_rc, t2_rc))
        if t1_rc != 0 or t2_rc != 0:
            print("🔴 TABAN KIRMIZI — batarya anlamsiz.")
            if args.ayrinti:
                print(t1_out[-2000:])
                print(t2_out[-2000:])
            return 1

        print("-- OLDURUCU MUTANTLAR (%d)" % len(OLDURUCU))
        for i, (etiket, hedef, kosulan, kargs, eski, yeni, aile) in enumerate(OLDURUCU):
            d = os.path.join(kok, "m%d" % i)
            os.mkdir(d)
            _farm(d)
            hata = _mutant_kur(d, hedef, eski, yeni)
            if hata:
                hatali.append("%s: %s" % (etiket, hata))
                print("   🟠 HATA  %-62s %s" % (etiket, hata))
                continue
            rc, out = _kos(d, kosulan, kargs)
            gorulen = _izler(out)
            oldu = (rc != 0 and aile in gorulen)
            izler_by_aile.setdefault(aile, []).append(frozenset(gorulen))
            print("   %s %-62s rc=%d iz=%s"
                  % ("✅ OLDU " if oldu else "🔴 YASADI", etiket, rc,
                     ",".join(sorted(gorulen)) or "-"))
            if oldu:
                olduruldu += 1
            else:
                hatali.append("%s: HAYATTA KALDI/YANLIS IZ (rc=%d iz=%s, beklenen %s)"
                              % (etiket, rc, sorted(gorulen), aile))
            if args.ayrinti:
                print("      " + out.strip().replace("\n", "\n      ")[:1200])

        print("-- KONTROL MUTANTLARI (%d) — masum degisiklik YESIL kalmali" % len(KONTROL))
        for i, (etiket, hedef, kosulan, kargs, eski, yeni) in enumerate(KONTROL):
            d = os.path.join(kok, "k%d" % i)
            os.mkdir(d)
            _farm(d)
            hata = _mutant_kur(d, hedef, eski, yeni)
            if hata:
                kontrol_hata.append("%s: %s" % (etiket, hata))
                print("   🟠 HATA  %-62s %s" % (etiket, hata))
                continue
            rc, out = _kos(d, kosulan, kargs)
            if rc == 0 and not _izler(out):
                kontrol_yesil += 1
                print("   ✅ YESIL %-62s rc=0" % etiket)
            else:
                kontrol_hata.append("%s: KIRMIZI YANDI (rc=%d iz=%s)"
                                    % (etiket, rc, sorted(_izler(out))))
                print("   🔴 KIRMIZI %-60s rc=%d iz=%s"
                      % (etiket, rc, ",".join(sorted(_izler(out))) or "-"))
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    son_ozet = _agac_ozeti()
    agac_temiz = (bas_ozet == son_ozet)

    # IZ AYRIMI = iz TOPLU bir kirmizi degil, AYIRT EDICI bir sinyal mi?
    #   (a) her oldurucu mutant KENDI beyan ettigi aileyi bastirdi (hatali listesi bos),
    #   (b) en az iki FARKLI aile fiilen olculdu,
    #   (c) farkli aile beyan eden iki mutantin gozlenen iz kumeleri FARKLI —
    #       yani her mutasyonda ayni tek kirmizi dusmuyor.
    gozlenen = {a: set().union(*v) if v else set() for a, v in izler_by_aile.items()}
    ayirt_edici = (len(gozlenen) >= 2
                   and len(set(frozenset(s) for s in gozlenen.values())) >= 2)
    iz_ayrimi = (not hatali) and ayirt_edici

    print()
    print("MUTANT=%d/%d KONTROL=%s IZ_AYRIMI=%s AGAC_ARTIK=%d"
          % (olduruldu, len(OLDURUCU),
             "YESIL" if (kontrol_yesil == len(KONTROL) and not kontrol_hata) else "KIRMIZI",
             "DOGRU" if iz_ayrimi else "YANLIS",
             0 if agac_temiz else 1))
    for h in hatali + kontrol_hata:
        print("   - " + h)
    if not agac_temiz:
        print("   - 🔴 AGAC KIRLENDI: tools/ ozeti degisti (%s -> %s)"
              % (bas_ozet[:12], son_ozet[:12]))
    if hatali or kontrol_hata or not agac_temiz or not iz_ayrimi:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
