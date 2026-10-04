#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — `kutu-oksuz-nobeti.py` MIMAR ICRA KAPISINDA KARDES EVLERDEN SERBEST, ETRAFI KAPALI.

=== NEDEN VAR (olculmus ariza, 4 Eki 2026 — K424 TUKETICI KOLU) ===
BaBa'nin 09:00 gunluk olcumu (`gunluk-mimar-ihtar/SKILL.md` L85) `kutu-oksuz-nobeti.py`i KraL'in
MUTLAK yoluyla cagirir. BaBa evinin kokunden bakinca o yol repo DISIDIR: kapi R2 ile RED verdi,
ilk kosumda `KUTU_OKSUZ_GOVDE` OLCULEMEDI (4 Eki 09:1x advisor blogu). Care
`tools/serbest_cagrilar.py` SEKILLER'e ADLI `kutu-oksuz` sekli (`repo_disi=True`, SABIT mutlak yol,
yorumlayici kisitli, bayraksiz kova). Ayni sinifin tarif taramasi: advisor tarifinde KraL
`tools/` yoluyla cagrilan BASKA arac YOK (`grep dev/pruvo/tools` tek satir).

NE OLCER (kapinin KARAR fonksiyonu, GERCEK PreToolUse yuku, izole kopya):
  K1 POZITIF — her ev kokunde (tek kaynak `kapi_dagitim.EVLER`, BaBa dahil) ANA oturum damgasiyla
               `python3 <kanonik yol>`, `/opt/homebrew/bin/python3 ...`, `... 2>&1` -> ALLOW.
  K2 NEGATIF — `python3 -c`, curl, benzer ad (`.bak`, `-sahte`), `--kutu <yol>` (yol tasima),
               bayrak, sahte yorumlayici, `;`/`>`/`$()` zinciri, ve KARDES evlerde komsu
               YAZAR arac `kutu-arsivle.py` -> DENY.
  K3 MUTANT  — izole kopyada kural bozulur, ilgili vaka KIRMIZI yanmali (SURVIVOR=0).

🔴 IZOLASYON: hicbir mutant CANLI govdede kosmaz; gercek ev agaclarina YAZILMAZ
([[mutant-canli-govdede-yasamaz]]). Yardimcilar `serbest-kume-ev-ekseni-test.py`den YUKLENIR
(ikinci kopya yazilmaz — [[ikiz-tanim-sessiz-ayrisma]]).

CI-ALT-KUME: kendini-test
"""
import importlib.util
import os
import shutil
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import serbest_cagrilar as SC          # noqa: E402
import kapi_dagitim as KD              # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ev_ekseni_yardimci", os.path.join(TOOLS, "serbest-kume-ev-ekseni-test.py"))
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)

ARAC = SC.KUTU_OKSUZ_YOL
KUTU_ARSIVLE = SC.KUTU_ARSIVLE_YOL
KRAL_KOKU = os.path.normpath(KD.KAYNAK_KOK)
BEKLENEN_EVLER = ("KraL", "MaCiT", "TeKiN", "ArTisT", "HocA", "BaBa")


def _evler():
    return [(ad, os.path.normpath(kok)) for ad, kok, _g, _m in KD.EVLER]


# --- VAKALAR ----------------------------------------------------------------
# POZITIF: (ad, komut, yalniz_kral). yalniz_kral=True: repo-goreli bicim yalniz KraL'da
# repo ICI olur (kardes evde `tools/kutu-oksuz-nobeti.py` o evin KENDI dosyasi olurdu).
POZITIF = (
    ("P1 mutlak yol", "python3 " + ARAC, False),
    ("P2 homebrew yorumlayici", "/opt/homebrew/bin/python3 " + ARAC, False),
    ("P3 2>&1", "python3 " + ARAC + " 2>&1", False),
    ("P4 repo-goreli (KraL)", "python3 tools/kutu-oksuz-nobeti.py", True),
)

# NEGATIF: (ad, komut, yalniz_kardes). yalniz_kardes=True: KraL'da arac repo ICI oldugundan
# kapi zaten gecirir (11 Eyl) — vaka yalniz kardes evlerde anlamlidir.
NEGATIF = (
    ("N1 python3 -c", "python3 -c \"print(1)\"", False),
    ("N2 curl", "curl -s https://ornek.invalid/", False),
    ("N3 benzer ad .bak", "python3 " + ARAC + ".bak", True),
    ("N4 benzer ad -sahte", "python3 " + ARAC[:-3] + "-sahte.py", True),
    ("N5 --kutu yol tasima", "python3 " + ARAC + " --kutu /private/tmp/kutu.md", False),
    ("N6 --kutu yalin", "python3 " + ARAC + " --kutu", True),
    ("N7 bilinmeyen bayrak", "python3 " + ARAC + " --bypass", True),
    ("N8 sahte yorumlayici", "/private/tmp/python3 " + ARAC, True),
    ("N9 tirnak disi ; zinciri", "python3 " + ARAC + "; curl https://ornek.invalid", False),
    ("N10 > yonlendirme", "python3 " + ARAC + " > /tmp/kutu-oksuz.out", False),
    ("N11 $() argumani", "python3 " + ARAC + " \"$(id)\"", True),
    ("N12 komsu YAZAR arac kutu-arsivle (bayraksiz = YAZAR)", "python3 " + KUTU_ARSIVLE, True),
    ("N12b komsu YAZAR arac kutu-arsivle --kuru", "python3 " + KUTU_ARSIVLE + " --kuru", True),
    ("N13 baska KraL araci", "python3 " + SC.REPO_ONEKI + "tools/build.py", True),
)


def _kos(dizin, kok, komut):
    return EV._karar(dizin, kok, komut, damga=EV._ana_damgasi(kok))


def _vakalar(dizin, ad, kok):
    """Bir izole kopyada tum vakalar. Doner: SAPANLAR [(vaka, beklenen, gorulen)]."""
    kral = kok == KRAL_KOKU
    sapan = []
    for vaka, komut, yalniz_kral in POZITIF:
        if yalniz_kral and not kral:
            continue
        g = _kos(dizin, kok, komut)
        if g != "ALLOW":
            sapan.append((ad + " " + vaka, "ALLOW", g))
    for vaka, komut, yalniz_kardes in NEGATIF:
        if yalniz_kardes and kral:
            continue
        g = _kos(dizin, kok, komut)
        if g != "DENY":
            sapan.append((ad + " " + vaka, "DENY", g))
    return sapan


def k1_k2_evler():
    hatalar = []
    adlar = [ad for ad, _k in _evler()]
    for beklenen in BEKLENEN_EVLER:
        if beklenen not in adlar:
            hatalar.append("EV KUMESINDE YOK: " + beklenen)
    for ad, kok in _evler():
        dizin = EV._izole_kopya(kok)
        try:
            for vaka, bek, gor in _vakalar(dizin, ad, kok):
                hatalar.append("%s: beklenen %s, gorulen %s" % (vaka, bek, gor))
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
    print("   VAKA: %d ev x (%d pozitif + %d negatif; KraL/kardes ayrimiyla)"
          % (len(_evler()), len(POZITIF), len(NEGATIF)))
    return hatalar


# --- K3 MUTANTLAR (izole kopya) ----------------------------------------------
_SEKIL = ('    Sekil("kutu-oksuz", KUTU_OKSUZ_YOL, repo_disi=True,\n'
          '          yorumlayicilar=JEV_YORUMLAYICILAR),\n')
# (ad, [(dosya, eski, yeni)], olmesi beklenen vaka on-ekleri). Mutant ancak BEKLENEN
# vakalardan en az biri sapinca OLMUS sayilir; capa bulunamazsa hata (INERT yasak).
MUTANTLAR = (
    ("MK1 sekil tablodan silinir",
     [("serbest_cagrilar.py", _SEKIL, "")], ("P1", "P2", "P3")),
    ("MK2 repo_disi kalkar (kardes evde yanlis dosyaya koklenir)",
     [("serbest_cagrilar.py", 'Sekil("kutu-oksuz", KUTU_OKSUZ_YOL, repo_disi=True,',
       'Sekil("kutu-oksuz", KUTU_OKSUZ_YOL,')], ("P1", "P2", "P3")),
    ("MK3 yorumlayici kisiti kalkar",
     [("serbest_cagrilar.py", "          yorumlayicilar=JEV_YORUMLAYICILAR),\n) + _jev_sekilleri()",
       "          ),\n) + _jev_sekilleri()")], ("N8",)),
    ("MK4 --kutu bayragi serbest kovaya girer",
     [("serbest_cagrilar.py", 'Sekil("kutu-oksuz", KUTU_OKSUZ_YOL, repo_disi=True,',
       'Sekil("kutu-oksuz", KUTU_OKSUZ_YOL, repo_disi=True, serbest=("--kutu",),')],
     ("N6",)),
    ("MK5 arac yolu komsu YAZAR araca kayar (kutu-arsivle acilir)",
     [("serbest_cagrilar.py", 'Sekil("kutu-oksuz", KUTU_OKSUZ_YOL, repo_disi=True,',
       'Sekil("kutu-oksuz", KUTU_ARSIVLE_YOL, repo_disi=True,')], ("N12",)),
)
MUTANT_EVLERI = ("KraL", "BaBa")


def k3_mutantlar():
    hatalar = []
    survivor = 0
    for ad, mutasyonlar, beklenen in MUTANTLAR:
        sapan = []
        for ev_ad, kok in _evler():
            if ev_ad not in MUTANT_EVLERI:
                continue
            try:
                dizin = EV._izole_kopya(kok, mutasyonlar)
            except AssertionError as hata:
                hatalar.append("%s INERT: %s" % (ad, hata))
                break
            try:
                sapan.extend(v for v, _b, _g in _vakalar(dizin, ev_ad, kok))
            finally:
                shutil.rmtree(dizin, ignore_errors=True)
        oldu = [v for v in sapan if v.split(" ", 2)[1] in beklenen]
        print("   %-62s %s  (sapan %d, beklenen-isabet %d)"
              % (ad, "OLDU" if oldu else "SURVIVOR", len(sapan), len(oldu)))
        if not oldu:
            survivor += 1
            hatalar.append("%s SURVIVOR — beklenen vakalar %s yesil kaldi" % (ad, beklenen))
    print("   MUTANT=%d SURVIVOR=%d" % (len(MUTANTLAR), survivor))
    return hatalar


VAKALAR = (
    ("K1+K2 alti ev — pozitif ALLOW, negatif DENY (gercek yuk)", k1_k2_evler),
    ("K3 izole mutantlar — SURVIVOR=0", k3_mutantlar),
)


def main():
    print("=== KUTU-OKSUZ KAPISI — serbest sekil kardes evlerde (K424 tuketici kolu) ===")
    print("EVLER (tek kaynak kapi_dagitim.EVLER): %s" % ", ".join(a for a, _k in _evler()))
    tum = []
    for ad, fn in VAKALAR:
        try:
            hatalar = fn()
        except Exception as hata:
            hatalar = ["%s COKTU: %r" % (ad, hata)]
        print("  %-58s %s" % (ad, "TAMAM" if not hatalar else "KIRMIZI"))
        for h in hatalar:
            print("      - " + h)
        tum.extend(hatalar)
    print("BULGU=%d" % len(tum))
    return 0 if not tum else 1


if __name__ == "__main__":
    sys.exit(main())
