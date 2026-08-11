#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — konfigur-siyah-kapak-kapisi.py GERCEKTEN olcuyor mu?

NEDEN VAR (Okan emri, 11 Agu 2026)
----------------------------------
Konfigur/dekor urunlerinde kapak gorseli siyah, onden secili renk Siyah olacak.
Bu iki sey AYNI seydir: on-secim AYRI bir alanda durmaz, `build.py::
_konfigur_varsayilan_renk` onu KAPAK GORSELINDEN turetir. Dolayisiyla kapagi geri
almak on-secimi de geri alir — SESSIZCE, tek bir alan adi bile degismeden. Kapiyi
korumasiz birakmak, bu regresyonu bir sonraki katalog partisinde gorunmez kilar.

🔴 KAPININ KENDISI IKI KOLLUDUR ve bir kolu oldurmek digerinden GORUNMEZ:
    EKSEN A  turetim SONUCU "Siyah" mi
    EKSEN B  turetim GERCEKTEN kapak gorselinden mi geliyor (rgi["Siyah"] == 0)
(B) olmadan (A) KANDIRILABILIR: renkGorselIndeks bosaltilirsa uretim fonksiyonu
"listenin ilki" koluna duser, renkler[0] "Siyah" oldugu icin yine "Siyah" dondurur —
kapak gri olsa bile. Bu yuzden C2 ve C3 fiksturleri BILEREK birbirinin AYNASI DEGIL:
  C2  capa 0'da AMA renk sirasi yuzunden on-secim "Gri"      -> YALNIZ eksen A yakalar
  C3  on-secim "Siyah" AMA capa YOK (sabit renge kaymis)     -> YALNIZ eksen B yakalar
Tek bir fikstur kullansaydik, iki koldan birini olduren mutant KACARDI
([[fikstur-degeri-mutasyon-koru]]).

🔴 JETONLAR AYRIK: KONFIGUR_KAPAK_TAM · KONFIGUR_KAPAK_IHLAL · OLCULEMEDI. Hicbiri
digerinin alt dizesi degildir ([[maskeleme-kismi-kapatma]]).

🔴 BYTECODE ONBELLEGI BAGISIKLIGI ([[mutasyon-bytecode-onbellegi]]): hicbir mutasyon
DISKE YAZILMAZ. Kaynak okunur, BELLEKTE degistirilir, exec(compile(...)) ile ayri bir
modul sozlugunde kosar. Her mutant icin capanin TAM 1 kez gectigi, eski metnin gittigi
ve yeni metnin geldigi UCU DE olculur; kosum sonunda canli dosyanin sha256'si bas=son
karsilastirilir.

FIKSTURLER SENTETIKTIR: urunler.json OKUNMAZ (kapinin kendi main()'i okur, batarya
DEGIL). tools/build.py OKUNUR — cunku olculen sey tam da URETIM KODUNA capalanmis
olmaktir; kopya bir yuklem yazmak bataryayi anlamsiz kilardi.

KONTROL MUTANTI olculen eksenin ICINDEN secildi: kapsam sayacindaki toplamanin terim
SIRASI degistirilir (toplama degismeli). Ayni satira dokunur, davranis TANIM GEREGI
ayni -> YESIL kalmali ([[beyan-edilmis-survivor]]).

Calistir:  python3 tools/konfigur-siyah-kapak-mutasyon.py   (0 = gecti, 1 = kaldi)
"""
import hashlib
import os
import sys
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "konfigur-siyah-kapak-kapisi.py")

# --------------------------------------------------------------------- fiksturler
# Gercek kayitlarin SEKLINI taklit eder ([[nobetci-fikstur-sekli]]): 6 gorsel, uc renk,
# R2 mutlak URL. Gercek urun DEGIL (sentetik "x-" onek).
def _g(n=6):
    return ["https://media.pruvo3d.com/urunler/x-serit-figur-p%d.jpg" % i
            for i in range(1, n + 1)]


def _urun(uid, renkler, rgi, gorseller=None):
    return {"id": uid, "kategori": "Skan Art", "gorseller": gorseller or _g(),
            "konfigur": {"renkler": list(renkler), "renkGorselIndeks": rgi,
                         "varsayilanMalzeme": "PLA"}}


# GECERLI: kapak siyah, capa 0, on-secim Siyah.
def _gecerli(uid="x-gecerli"):
    return _urun(uid, ["Siyah", "Beyaz", "Gri"], {"Siyah": 0, "Gri": 1, "Beyaz": 2})


# C2 — EKSEN A: capa 0'DA (rgi["Siyah"]==0) ama renk SIRASI yuzunden uretim
# fonksiyonu "Gri" donduruyor. Eksen B bu urunu TEMIZ gorur; yalniz eksen A yakalar.
FIX_EKSEN_A = [_urun("x-sira-gri", ["Gri", "Siyah", "Beyaz"],
                     {"Gri": 0, "Siyah": 0, "Beyaz": 2})]

# C3 — EKSEN B: renkGorselIndeks BOSALTILMIS. Uretim fonksiyonu "listenin ilki"
# koluna duser ve "Siyah" dondurur; eksen A bu urunu TEMIZ gorur. On-secim kapak
# gorselinden KOPMUS, sabit renge baglanmistir — yalniz eksen B yakalar.
FIX_EKSEN_B = [_urun("x-capasiz", ["Siyah", "Beyaz", "Gri"], {})]

# C6 — GERCEK REGRESYON: kapak griye geri alindi (bu is emrinin tersi).
FIX_GRI_KAPAK = [_urun("x-gri-kapak", ["Siyah", "Beyaz", "Gri"],
                       {"Gri": 0, "Siyah": 1, "Beyaz": 2})]

# C4 — COZULEMEZ: renkGorselIndeks OBJE DEGIL (liste).
FIX_OLCULEMEZ = [_urun("x-bozuk", ["Siyah", "Beyaz"], [])]

FIX_POZITIF = [_gecerli("x-1"), _gecerli("x-2"), _gecerli("x-3")]

# C5 — KAPSAM: konfigur alani OLMAYAN urunler sayilmamali.
FIX_KAPSAM = [_gecerli("x-1"),
              {"id": "x-duz", "kategori": "Otomobil", "gorseller": _g(3)},
              {"id": "x-duz2", "kategori": "Ev", "gorseller": _g(2)}]


def _turet(mod):
    fn, sebep = mod.uretim_turetimi()
    if fn is None:
        raise RuntimeError("uretim turetimi cozulemedi: %s" % sebep)
    return fn


# ------------------------------------------------------------------------ iddialar
def c1_pozitif(mod):
    """Gecerli siyah kapakli urunler REDDEDILMIYOR mu?"""
    satir, ihlal, olc, tam = mod.denetle(FIX_POZITIF, _turet(mod))
    return (ihlal == [] and olc == [] and tam == 3 and mod.JETON_TAM in satir), satir


def c2_eksen_a(mod):
    """Capa 0'da ama on-secim 'Gri' -> YALNIZ eksen A yakalar."""
    satir, ihlal, olc, _ = mod.denetle(FIX_EKSEN_A, _turet(mod))
    return (len(ihlal) == 1 and olc == [] and mod.JETON_IHLAL in satir
            and mod.JETON_TAM not in satir), satir


def c3_eksen_b(mod):
    """On-secim 'Siyah' ama KAPAK CAPASI yok -> YALNIZ eksen B yakalar."""
    satir, ihlal, olc, _ = mod.denetle(FIX_EKSEN_B, _turet(mod))
    return (len(ihlal) == 1 and olc == [] and mod.JETON_IHLAL in satir
            and mod.JETON_TAM not in satir), satir


def c4_olculemedi(mod):
    """Cozulemeyen kayitta 'gecti' DENMEZ -> OLCULEMEDI (fail-closed)."""
    satir, ihlal, olc, _ = mod.denetle(FIX_OLCULEMEZ, _turet(mod))
    return (len(olc) == 1 and mod.JETON_OLCULEMEDI in satir
            and mod.JETON_TAM not in satir), satir


def c5_kapsam(mod):
    """konfigur alani OLMAYAN urun kapsam DISI (sayilmaz)."""
    satir, ihlal, olc, tam = mod.denetle(FIX_KAPSAM, _turet(mod))
    return (tam == 1 and ihlal == [] and olc == [] and "1/1" in satir), satir


def c6_gri_kapak(mod):
    """GERCEK REGRESYON: kapak griye geri alindi -> KIRMIZI."""
    satir, ihlal, olc, _ = mod.denetle(FIX_GRI_KAPAK, _turet(mod))
    return (len(ihlal) == 1 and mod.JETON_IHLAL in satir), satir


IDDIALAR = [
    ("C1 POZITIF KOL   (gecerli siyah kapakli urun reddedilmiyor)", c1_pozitif),
    ("C2 EKSEN A       (capa 0 ama on-secim Gri -> IHLAL)", c2_eksen_a),
    ("C3 EKSEN B       (on-secim Siyah ama kapak capasi YOK -> IHLAL)", c3_eksen_b),
    ("C4 OLCULEMEDI    (cozulemeyen kayitta sessiz yesil YOK)", c4_olculemedi),
    ("C5 KAPSAM        (konfigursuz urun sayilmiyor)", c5_kapsam),
    ("C6 GRI KAPAK     (gercek regresyon: kapak geri alindi -> IHLAL)", c6_gri_kapak),
]

# ------------------------------------------------------------------------ mutantlar
_TURETIM_CAGRISI = ("    try:\n"
                    "        renk = turet(k)\n")

_EKSEN_B = ('    ix = rgi.get(BEKLENEN_RENK)\n'
            '    if ix != 0:\n')

_OLCULEMEDI_SATIRI = (
    '    if olculemedi:\n'
    '        satir = ("konfigur on-secim %s: %d/%d urun COZULEMEDI — hukum VERILMEDI "\n'
    '                 "(\'cozemedim = gecti\' sessiz gecisi YASAK)"\n'
    '                 % (JETON_OLCULEMEDI, len(olculemedi), kapsam))\n')

_TAM_KOLU = ('        if durum == "TAM":\n'
             '            tam.append(kayit)\n')

_IHLAL_KOLU = ('        elif durum == "IHLAL":\n'
               '            ihlal.append(kayit)\n')

_KAPSAM_SAYACI = "    kapsam = len(tam) + len(ihlal) + len(olculemedi)\n"

MUTANTLAR = [
    ("N-1 TURETIM URETIM KODUNDAN KOPARILDI (sabit renge baglandi)",
     _TURETIM_CAGRISI,
     "    try:\n"
     "        renk = BEKLENEN_RENK\n",
     True, "C2"),
    ("N-2 EKSEN B SOKULDU (kapak capasi artik olculmuyor)",
     _EKSEN_B,
     '    ix = rgi.get(BEKLENEN_RENK)\n'
     '    if False:\n',
     True, "C3"),
    ("N-3 OLCULEMEDI kolu SESSIZ YESILE cevrildi (cozemedim = gecti)",
     _OLCULEMEDI_SATIRI,
     '    if olculemedi:\n'
     '        satir = ("konfigur on-secim %s: cozulemedi ama sorun yok"\n'
     '                 % JETON_TAM)\n',
     True, "C4"),
    ("N-4 POZITIF KOL OLDURULDU (gecerli urun IHLAL sayildi)",
     _TAM_KOLU,
     '        if durum == "TAM":\n'
     '            ihlal.append(kayit)\n',
     True, "C1"),
    ("N-5 FAIL-OPEN: ihlal listesi HIC doldurulmuyor",
     _IHLAL_KOLU,
     '        elif durum == "IHLAL":\n'
     '            pass\n',
     True, "C2/C3/C6"),
    ("N-6 KONTROL: kapsam toplamasinin terim SIRASI degisti (davranis DEGISMEZ) — YESIL kalmali",
     _KAPSAM_SAYACI,
     "    kapsam = len(olculemedi) + len(ihlal) + len(tam)\n",
     False, "-"),
]


# --------------------------------------------------------------------------- kosum
def kaynak_oku():
    with open(HEDEF, encoding="utf-8") as f:
        return f.read()


def modul_yukle(src, etiket):
    """Kaynagi BELLEKTE modul olarak calistirir. DISKE YAZILMAZ -> __pycache__ YOK."""
    mod = types.ModuleType("konfigur_siyah_kapak_mutant_" + etiket)
    mod.__file__ = HEDEF          # modul icindeki os.path.abspath(__file__) icin sart
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, "<konfigur-siyah-kapak %s>" % etiket, "exec"), mod.__dict__)
    return mod


def mutasyon_uygula(src, eski, yeni):
    """(mutant_kaynak, hata) — uygulandigini UC eksende olcer."""
    n = src.count(eski)
    if n != 1:
        return None, ("capa kaynakta %d kez geciyor (1 olmali) — "
                      "konfigur-siyah-kapak-kapisi.py degismis" % n)
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
        fails.append("canli konfigur-siyah-kapak-kapisi.py DEGISTI (bas!=son sha256)")
    print("\ncanli dosya sha256 bas=son: %s (mutasyon diske YAZILMADI)"
          % ("EVET ✔" if son_sha == bas_sha else "HAYIR ✘"))
    print("MUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
          % (kirmizi, beklenen, kontrol_mutant or "KOSULMADI"))
    if fails:
        print("SONUC: KIRMIZI ❌  (%d)" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("SONUC: YESIL ✅ — kapinin IKI KOLU (turetim sonucu + kapak capasi), "
          "OLCULEMEDI kolu, pozitif kol ve fail-open ekseni AYRI AYRI olculdu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
