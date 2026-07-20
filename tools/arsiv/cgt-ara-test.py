#!/usr/bin/env python3
r"""KABUL TESTI — cgt-ara.py `aday_karari()` (marka-kelime + islevsellik) filtresi.

Amac (CGTrader genel pazar, cop bol): SADECE ISLEVSEL oto/endustriyel parca GECMELI; olcekli
maket arac, oyun/render varlik, karakter/figur/heykel, logo/merch, ve MARKA alt-dize gurultusu
(Oxford/afford) ELENMELI. main() bu ayni fonksiyonu kullanir (tek dogruluk kaynagi).

Kosum:  python3 tools/cgt-ara-test.py   -> tum satirlar ok, son 'TUM TESTLER GECTI'.

ONCE-KIRMIZI (dogrulandi):
  * marka filtresini duz alt-dize (`marka in slug`) yapsan -> Oxford/afford KIRMIZI (yanlis GECER).
  * islevselligi yalniz KATEGORI'ye baglasan -> automotive icindeki '...-125-scale' maket KIRMIZI
    (yanlis GECER); slug 'scale' sinyali onu yakalar.
"""
import importlib.util, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cgt_ara", os.path.join(_HERE, "cgt-ara.py"))
cgt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cgt)

# (marka, url_yolu, aciklama, beklenen_gecer?, not)
CASES = [
    # ---------- GECMELI: islevsel oto/endustriyel/atolye parcasi ----------
    ("ford", "/3d-print-models/hobby-diy/automotive/phone-holder-mount-for-ford-focus",
     "", True, "telefon tutucu = islevsel oto aksesuari"),
    ("ford", "/3d-print-models/hobby-diy/automotive/ford-fiesta-mk7-fuse-box-cover",
     "", True, "sigorta kutusu kapagi (box/cover BILEREK bloklanmadi)"),
    ("ford", "/3d-print-models/hobby-diy/automotive/adapter-to-jack-for-ford-mustang",
     "", True, "kriko adaptoru (gercek CGTrader verisi)"),
    ("ford", "/3d-print-models/hobby-diy/automotive/ford-crown-victoria-headlight-switch-connector",
     "", True, "elektrik konnektoru (gercek veri)"),
    ("bosch", "/3d-print-models/tools-organizers/household-tools/bosch-drill-bit-holder",
     "", True, "matkap ucu tutucu = atolye parcasi"),

    # ---------- ELENMELI: MARKA alt-dize gurultusu (\bMARKA\b tam kelime degil) ----------
    ("ford", "/3d-print-models/hobby-diy/automotive/oxford-diesel-injector-cap",
     "", False, "Ox+ford alt-dize -> marka-alakasiz ELE"),
    ("ford", "/3d-print-models/tools-organizers/household-tools/affordable-tool-tray",
     "", False, "af+ford able alt-dize -> ELE"),

    # ---------- ELENMELI: olcekli/maket arac ----------
    ("ford", "/3d-print-models/miniatures/vehicles/ford-mustang-1965-printable",
     "", False, "miniatures kategori = maket ELE (KATEGORI katmani)"),
    ("ford", "/3d-print-models/hobby-diy/automotive/2013-ford-mustang-drag-racing-125-scale",
     "", False, "automotive AMA slug 'scale' = maket ELE (SINYAL katmani — zor vaka)"),
    ("ford", "/3d-print-models/games-toys/toy/twind-lego-ford-mustang-dark-horse",
     "", False, "games-toys/toy = oyuncak/lego ELE"),

    # ---------- ELENMELI: oyun/render varlik ----------
    ("ford", "/3d-print-models/hobby-diy/automotive/ford-gt-lowpoly-game-asset",
     "Low poly game ready model for rendering in Unreal", False,
     "lowpoly/game/render varlik ELE (slug sinyali)"),
    ("nissan", "/3d-print-models/hobby-diy/automotive/nissan-gtr-highpoly-body",
     "Photoreal model for rendering and games, low poly, rigged", False,
     "render/game varlik ELE (ACIKLAMA sinyali)"),

    # ---------- ELENMELI: karakter/figur/heykel ----------
    ("ford", "/3d-print-models/art/sculpture/harrison-ford-as-indiana-jones",
     "", False, "art/sculpture heykel ELE (gercek veri)"),
    ("ford", "/3d-print-models/hobby-diy/other/ford-mascot-figurine",
     "", False, "figurine sinyali ELE"),

    # ---------- ELENMELI: logo/merch (populerlik DELMEZ) ----------
    ("ford", "/3d-print-models/gadgets/keychains/ford-logo-keychain",
     "", False, "keychains altkategori + logo -> ELE"),
    ("ford", "/3d-print-models/house/decor/ford-mustang-1964-wall-art",
     "", False, "wall art = dekor/merch ELE (gercek veri)"),
    ("ford", "/3d-print-models/house/decor/ford-shelby-cobra-logo-emblem-coaster",
     "", False, "logo+emblem+coaster = merch ELE (gercek veri)"),
]


def main():
    fails = []
    for marka, url, aciklama, bek, aciklama_not in CASES:
        gecer, neden = cgt.aday_karari(url, marka, aciklama)
        durum = "ok" if gecer == bek else "HATA"
        if gecer != bek:
            fails.append((marka, url, gecer, neden, bek, aciklama_not))
        print("  %-4s marka=%-7s gecer=%-5s neden=%-16s | %s"
              % (durum, marka, gecer, ("" if gecer else neden), aciklama_not))
    print()
    if fails:
        print("BASARISIZ — %d senaryo yanlis:" % len(fails))
        for marka, url, gecer, neden, bek, aciklama_not in fails:
            print("  x marka=%s gecer=%s (bek %s) neden=%s | %s\n      %s"
                  % (marka, gecer, bek, neden, aciklama_not, url))
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % len(CASES))


if __name__ == "__main__":
    main()
