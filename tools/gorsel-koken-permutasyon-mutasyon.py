#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — gorsel_koken.py TETIK (2) cok-kume olcutu FAIL-CLOSED mi?

NEDEN VAR (OLCULDU, 11 Agu 2026)
--------------------------------
`tools/gorsel_koken.py` bir FIGUR urununun (kategori "Skan Art") sayfa gorsellerinin
GERCEK STL'den turedigine dair koken kaniti olmadan yayina GIRMESINI engeller.
Tetik (2) eskiden LISTE esitligiyle olculuyordu:
    elif e.get("gorseller") != g:
Bu, korunan olayla (bir gorselin yayina GIRMESI) ayni sey DEGILDIR: ayni URL
kumesinin saf PERMUTASYONU da "degisim" sayiliyordu. Okan'in "konfigur kapak
gorseli siyaha alinacak" emri tam olarak bir permutasyondur — galeride ZATEN
yayinda olan siyah gorsel kapaga tasinir, hicbir yeni bayt yayinlanmaz — ve
15/15 urunde kapi kirmizi yaniyordu (olculdu: hepsi "koken manifesti YOK").

🔴 ONARIMIN KENDISI DE BIR RISKTIR: bir tetigi "daha dar" yapmak, fail-closed bir
kapiyi fail-open'a cevirmenin en ucuz yoludur ([[duzeltme-fail-open-cevirebilir]]).
Bu yuzden batarya TEK YONLU DEGILDIR — permutasyon muafiyetinin YANINDA, kapinin
GERCEKTEN korudugu her ekseni AYRI AYRI olcer:
    B1  PERMUTASYON MUAF   ayni URL'ler farkli sirada -> tetiklemez (onarimin amaci)
    B2  EKLEME             yeni URL girdi            -> TETIKLER
    B3  SILME              URL cikti                 -> TETIKLER
    B4  DEGISTIRME         ayni UZUNLUK, farkli URL  -> TETIKLER (en kritik eksen)
    B5  TEKRAR SAYISI      [A,A,B] vs [A,B,B]        -> TETIKLER (kume DEGIL, cok-kume)
    B6  YENI URUN          kol (1) hala canli mi
    B7  KATEGORI CEVIRME   permutasyon kol (3)'u ELE GECIRMIYOR mu
    B8  COZULEMEDI         kanonik anahtar uretilemezse "degismemis" DENMIYOR mu

🔴 B4 ve B5 bilerek AYRI: "ayni uzunluk" ve "ayni kume ama farkli tekrar" iki farkli
zayif implementasyonun (uzunluk karsilastirmasi · set()) tam olarak kacacagi
deliklerdir. B8 ise fail-closed yonunu olcer — cozemedigi girdide kapi ACILMAZ.

🔴 JETONLAR AYRIK: kollar tetikleyenler() ciktisinin KIMLIGINE bakar ([] vs ["x"]),
ortak bir govde metnine DEGIL ([[maskeleme-kismi-kapatma]]).

🔴 BYTECODE ONBELLEGI BAGISIKLIGI ([[mutasyon-bytecode-onbellegi]]): hicbir mutasyon
DISKE YAZILMAZ. Kaynak okunur, BELLEKTE degistirilir, exec(compile(...)) ile ayri bir
modul sozlugunde kosar. Her mutant icin capanin TAM 1 kez gectigi, eski metnin gittigi
ve yeni metnin geldigi UCU DE olculur; kosum sonunda canli dosyanin sha256'si bas=son
karsilastirilir.

FIKSTURLER SENTETIKTIR: katalog (urunler.json) OKUNMAZ, koken manifest DIZINI
OKUNMAZ, disk gezilmez — tetikleyenler() saf fonksiyondur. CI fresh checkout'unda
YAPISAL kirmizi vermez.

KONTROL MUTANTI olculen eksenin ICINDEN secildi: fail-closed kolundaki simetrik OR'un
operand SIRASI degistirilir (`a is None or b is None` -> `b is None or a is None`).
Ayni satira dokunur, davranis TANIM GEREGI ayni -> YESIL kalmali. Kalmazsa batarya
"her degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur ([[beyan-edilmis-survivor]]).

Calistir:  python3 tools/gorsel-koken-permutasyon-mutasyon.py   (0 = gecti, 1 = kaldi)
"""
import hashlib
import os
import sys
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "gorsel_koken.py")

# --------------------------------------------------------------------- fiksturler
# Gercek kayitlarin SEKLINI taklit eder ([[nobetci-fikstur-sekli]]): R2 mutlak URL'i,
# renk ekli dosya adi. Gercek bir urunun URL'i DEGILDIR (sentetik "x-" onek).
G_GRI = "https://media.pruvo3d.com/urunler/x-gri-1.jpg"
G_SIYAH = "https://media.pruvo3d.com/urunler/x-siyah-2.jpg"
G_BEYAZ = "https://media.pruvo3d.com/urunler/x-beyaz-3.jpg"
G_YENI = "https://media.pruvo3d.com/urunler/x-capasiz-4.jpg"

KAT = "Skan Art"

# json.dumps'in COZEMEDIGI oge (set) — liste esitligi ise bunu "esit" gorur.
# B8 tam olarak bu ikilikte yasar: LISTE-ESIT ama KANONIK ANAHTAR YOK.
_COZULEMEZ = [{"kaynak": {1, 2}}]


def _urun(gorseller, kategori=KAT):
    return {"id": "x", "kategori": kategori, "gorseller": list(gorseller)}


def _tetik(mod, eski_g, yeni_g, eski_kat=KAT, yeni_kat=KAT):
    return mod.tetikleyenler({"x": _urun(eski_g, eski_kat)},
                             {"x": _urun(yeni_g, yeni_kat)})


# ------------------------------------------------------------------------ iddialar
def b1_permutasyon_muaf(mod):
    """Ayni URL'ler farkli sirada -> koken kaniti ISTENMEZ (onarimin ta kendisi)."""
    t = _tetik(mod, [G_GRI, G_SIYAH, G_BEYAZ], [G_SIYAH, G_GRI, G_BEYAZ])
    return t == [], "tetik=%r (beklenen [])" % (t,)


def b2_ekleme(mod):
    """Yeni URL GIRDI -> TETIKLER (fail-closed)."""
    t = _tetik(mod, [G_GRI, G_SIYAH], [G_GRI, G_SIYAH, G_YENI])
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


def b3_silme(mod):
    """URL CIKTI -> TETIKLER."""
    t = _tetik(mod, [G_GRI, G_SIYAH, G_BEYAZ], [G_GRI, G_SIYAH])
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


def b4_degistirme(mod):
    """AYNI UZUNLUK, farkli URL -> TETIKLER (uzunluk karsilastirmasi bu deligi kacirir)."""
    t = _tetik(mod, [G_GRI, G_SIYAH, G_BEYAZ], [G_GRI, G_YENI, G_BEYAZ])
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


def b5_tekrar_sayisi(mod):
    """[A,A,B] -> [A,B,B]: KUME ayni, COK-KUME farkli -> TETIKLER."""
    t = _tetik(mod, [G_GRI, G_GRI, G_SIYAH], [G_GRI, G_SIYAH, G_SIYAH])
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


def b6_yeni_urun(mod):
    """Kol (1): urun katalogda YOK -> TETIKLER."""
    t = mod.tetikleyenler({}, {"x": _urun([G_GRI, G_SIYAH])})
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


def b7_kategori_cevirme(mod):
    """Kol (3): permutasyon muafiyeti kategori kolunu ELE GECIRMEZ."""
    t = _tetik(mod, [G_GRI, G_SIYAH], [G_SIYAH, G_GRI], eski_kat="Dekorasyon")
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


def b8_cozulemedi_fail_closed(mod):
    """LISTE-ESIT ama kanonik anahtar YOK -> "degismemis" DENMEZ, TETIKLER."""
    t = _tetik(mod, _COZULEMEZ, list(_COZULEMEZ))
    return t == ["x"], "tetik=%r (beklenen ['x'])" % (t,)


IDDIALAR = [
    ("B1 PERMUTASYON MUAF (ayni URL'ler, farkli sira -> tetiklemez)", b1_permutasyon_muaf),
    ("B2 EKLEME          (yeni URL girdi -> TETIKLER)", b2_ekleme),
    ("B3 SILME           (URL cikti -> TETIKLER)", b3_silme),
    ("B4 DEGISTIRME      (ayni uzunluk, farkli URL -> TETIKLER)", b4_degistirme),
    ("B5 TEKRAR SAYISI   (kume degil COK-KUME -> TETIKLER)", b5_tekrar_sayisi),
    ("B6 YENI URUN       (kol 1 canli)", b6_yeni_urun),
    ("B7 KATEGORI CEVIRME(kol 3 ele gecirilmedi)", b7_kategori_cevirme),
    ("B8 COZULEMEDI      (kanonik anahtar yoksa fail-closed)", b8_cozulemedi_fail_closed),
]

# ------------------------------------------------------------------------ mutantlar
_COK_KUME_GOVDE = (
        "        return tuple(sorted(json.dumps(x, sort_keys=True, ensure_ascii=False)\n"
        "                            for x in gorseller))\n")

_KARAR_GOVDE = (
    "    a = cok_kume(eski_g)\n"
    "    b = cok_kume(yeni_g)\n"
    "    if a is None or b is None:\n"
    "        return True\n"
    "    return a != b\n")

_FAIL_CLOSED_KOLU = (
    "    if a is None or b is None:\n"
    "        return True\n")

_KOL1 = ("        if not isinstance(e, dict):\n"
         "            tetik.append(pid)                     # 1. yeni urun\n")

_KOL3 = ("        elif e.get(\"kategori\") != KATEGORI:\n"
         "            tetik.append(pid)                     # 3. kategori Skan Art'a cevrildi\n")

MUTANTLAR = [
    ("M-1 COK-KUME -> KUME (set): tekrar sayisi silindi",
     _COK_KUME_GOVDE,
     "        return tuple(sorted(set(json.dumps(x, sort_keys=True, ensure_ascii=False)\n"
     "                                for x in gorseller)))\n",
     True, "B5"),
    ("M-2 FAIL-OPEN: gorsel kumesi HIC degismedi sayildi",
     _KARAR_GOVDE,
     "    a = cok_kume(eski_g)\n"
     "    b = cok_kume(yeni_g)\n"
     "    return False\n",
     True, "B2/B3/B4/B5/B8"),
    ("M-3 COZULEMEDI kolu SESSIZ GECISE cevrildi (cozemedim = degismemis)",
     _FAIL_CLOSED_KOLU,
     "    if a is None or b is None:\n"
     "        return False\n",
     True, "B8"),
    ("M-4 KOL 3 OLDURULDU (kategori Skan Art'a cevirme kacar)",
     _KOL3,
     "        elif False:\n"
     "            tetik.append(pid)                     # 3. KOL OLDURULDU\n",
     True, "B7"),
    ("M-5 KOL 1 OLDURULDU (yeni urun kacar)",
     _KOL1,
     "        if not isinstance(e, dict):\n"
     "            pass                                  # 1. KOL OLDURULDU\n",
     True, "B6"),
    ("M-6 POZITIF KOL OLDURULDU: LISTE esitligine geri donuldu (permutasyon yine tetikler)",
     "    return a != b\n",
     "    return list(eski_g or []) != list(yeni_g or [])\n",
     True, "B1"),
    ("M-7 KONTROL: simetrik OR operand SIRASI degisti (davranis DEGISMEZ) — YESIL kalmali",
     _FAIL_CLOSED_KOLU,
     "    if b is None or a is None:\n"
     "        return True\n",
     False, "-"),
]


# --------------------------------------------------------------------------- kosum
def kaynak_oku():
    with open(HEDEF, encoding="utf-8") as f:
        return f.read()


def modul_yukle(src, etiket):
    """Kaynagi BELLEKTE modul olarak calistirir. DISKE YAZILMAZ -> __pycache__ YOK."""
    mod = types.ModuleType("gorsel_koken_mutant_" + etiket)
    mod.__file__ = HEDEF
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, "<gorsel_koken %s>" % etiket, "exec"), mod.__dict__)
    return mod


def mutasyon_uygula(src, eski, yeni):
    """(mutant_kaynak, hata) — uygulandigini UC eksende olcer."""
    n = src.count(eski)
    if n != 1:
        return None, "capa kaynakta %d kez geciyor (1 olmali) — gorsel_koken.py degismis" % n
    mut = src.replace(eski, yeni, 1)
    if mut == src:
        return None, "mutasyon metni DEGISTIRMEDI"
    if eski in mut:
        return None, "eski metin mutantta HALA var (mutasyon uygulanmadi)"
    if yeni and yeni not in mut:
        return None, "yeni metin mutantta YOK"
    return mut, None


def iddialari_kos(mod):
    """[(ad, durum, detay)] — durum: PASS | FAIL | COKTU."""
    sonuc = []
    for ad, fn in IDDIALAR:
        try:
            ok, detay = fn(mod)
        except Exception as e:                                   # noqa: BLE001
            sonuc.append((ad, "COKTU", "%s: %s" % (type(e).__name__, e)))
            continue
        sonuc.append((ad, "PASS" if ok else "FAIL", detay))
    return sonuc


def main():
    if not os.path.exists(HEDEF):
        print("KIRMIZI: hedef bulunamadi: %s" % HEDEF)
        return 1
    src = kaynak_oku()
    bas_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    fails = []

    print("=== KONTROL KOSUMU (mutasyonsuz) — %d/%d iddia PASS olmali"
          % (len(IDDIALAR), len(IDDIALAR)))
    kontrol = iddialari_kos(modul_yukle(src, "kontrol"))
    for ad, durum, detay in kontrol:
        print("  %-6s %s" % (durum, ad))
        if durum != "PASS":
            print("        %s" % detay[:400])
            fails.append("mutasyonsuz kosumda %s -> %s" % (ad, durum))

    print("\n=== MUTANTLAR (oldurucu olanlar en az 1 iddiayi FAIL etmeli)")
    kirmizi = 0
    beklenen = sum(1 for m in MUTANTLAR if m[3])
    kontrol_mutant = None
    for ad, eski, yeni, kirmizi_bekle, kol in MUTANTLAR:
        mut, hata = mutasyon_uygula(src, eski, yeni)
        if hata:
            print("  FAIL   %s -> MUTASYON UYGULANAMADI: %s" % (ad, hata))
            fails.append(ad + " (uygulanamadi)")
            continue
        try:
            mod = modul_yukle(mut, "mut")
        except Exception as e:                                   # noqa: BLE001
            print("  FAIL   %s -> MUTANT YUKLENEMEDI (%s: %s) — cokme KIRMIZI SAYILMAZ"
                  % (ad, type(e).__name__, e))
            fails.append(ad + " (yuklenemedi)")
            continue
        sonuc = iddialari_kos(mod)
        dusen = [s[0].split()[0] for s in sonuc if s[1] == "FAIL"]
        coken = [s[0].split()[0] for s in sonuc if s[1] == "COKTU"]
        if kirmizi_bekle:
            ok = bool(dusen) and not coken
            if ok:
                kirmizi += 1
            print("  %-6s %s" % ("PASS" if ok else "FAIL", ad))
            print("         beklenen kol: %s | DUSEN: %s | COKEN: %s"
                  % (kol, ", ".join(dusen) or "-", ", ".join(coken) or "-"))
            if not ok:
                fails.append(ad + (" (cokme kirmiziyla karismasin)" if coken
                                   else " (mutant YAKALANMADI — iddia OLU)"))
        else:
            ok = not dusen and not coken
            kontrol_mutant = "YESIL" if ok else "KIRMIZI"
            print("  %-6s %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol_mutant))
            if not ok:
                print("         DUSEN: %s | COKEN: %s"
                      % (", ".join(dusen) or "-", ", ".join(coken) or "-"))
                fails.append(ad + " (kontrol mutanti kirmizi yandi: batarya olcmuyor)")

    son_sha = hashlib.sha256(kaynak_oku().encode("utf-8")).hexdigest()
    if son_sha != bas_sha:
        fails.append("canli gorsel_koken.py DEGISTI (bas!=son sha256)")
    print("\ncanli dosya sha256 bas=son: %s (mutasyon diske YAZILMADI)"
          % ("EVET ✔" if son_sha == bas_sha else "HAYIR ✘"))
    print("MUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
          % (kirmizi, beklenen, kontrol_mutant or "KOSULMADI"))
    if fails:
        print("SONUC: KIRMIZI ❌  (%d)" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("SONUC: YESIL ✅ — permutasyon muafiyeti CANLI ve kapi ekleme/silme/"
          "degistirme/tekrar-sayisi/kategori/cozulemedi eksenlerinde FAIL-CLOSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
