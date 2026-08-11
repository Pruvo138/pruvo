#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — gorsel_koken.py KOKEN DIZINI BIRLESTIRMESI fail-closed mi?

NEDEN VAR (OLCULDU, 12 Agu 2026)
--------------------------------
`tools/gorsel_koken.py` eskiden manifest dizinini `manifest_dizini()` ile seciyordu:
VAR OLAN ILK dizin kazaniyor, digerlerine HIC BAKILMIYORDU. Olcum:

    kol                          secilen dizin                        manifest  YESIL  KIRMIZI
    bugunku hal                  pruvo/urun-gorsel-koken                   2       0      16
    GORSEL_KOKEN_DIR=jenerator   pruvo-jenerator/urun-gorsel-koken        12       5      11

Yani kapi, korudugu olayi (koken kaniti VAR MI) degil DIZIN SIRASINI olcuyordu ve
kaniti GERCEKTEN OLAN 5 urun bile eklenemiyordu (zorlama CI'da degil YAZIM aninda:
urun-ekle.py merge_safe -> gk.zorla -> KokenIhlali -> hicbir sey yazilmadan cikis).
Onarim: dizinler BIRLESTIRILDI (`manifest_yollari` TUM var olan dizinleri tarar).

🔴 ONARIMIN KENDISI RISKTIR ([[duzeltme-fail-open-cevirebilir]]): "daha cok yerde ara"
demek, kapiyi gevsetmenin en ucuz yoludur. Bu yuzden batarya TEK YONLU DEGILDIR —
birlestirmenin YANINDA kapinin korudugu her ekseni AYRI olcer:

    B1  GOLGELEME KALKTI   manifest YALNIZ ikinci dizinde  -> GECER (onarimin amaci)
    B2  MANIFESTSIZ        hicbir dizinde manifest yok     -> BLOCK (kapi GEVSEMEDI)
    B3  CELISKI            iki dizinde FARKLI manifest     -> BLOCK (sessiz cozum YOK)
    B4  AYNI ICERIK        iki dizinde KANONIK AYNI        -> GECER + kazanan = oncelik
    B5  YEREL DIZIN        manifest YALNIZ ilk dizinde     -> GECER (eski yol bozulmadi)
    B6  DIZIN YOK          hicbir koken dizini yok          -> BLOCK (ayri gerekce)
    B7  SINIF AYRIMI       "manifest yok" != "kaynak dosya yok" (rapor sayilari ayrik)
    B8  BOZUK MANIFEST     parse edilemeyen kopya           -> BLOCK (fail-closed)

🔴 B2/B3/B6/B8 bilerek AYRI GEREKCE olcer: hepsini tek "block" jetonuna baglamak,
bir kolu oldurup digerinin metnine sigan mutanti YESIL gecirirdi
([[maskeleme-kismi-kapatma]]). B7 raporun ayrik sayilarini kilitler: 11 kirmizinin
10'u "manifest hic yok", 1'i "manifest var ama kaynak_stl diskte yok" — bu iki sinif
KaaN icin bambaska is kalemidir ve tek sayida toplanirsa gorunmez
([[hukum-yanlis-birimde]]).

🔴 BYTECODE ONBELLEGI BAGISIKLIGI ([[mutasyon-bytecode-onbellegi]]): hicbir mutasyon
DISKE YAZILMAZ. Kaynak okunur, BELLEKTE degistirilir, exec(compile(...)) ile ayri bir
modul sozlugunde kosar. Her mutant icin capanin TAM 1 kez gectigi, eski metnin gittigi
ve yeni metnin geldigi UCU DE olculur; kosum sonunda canli dosyanin sha256'si bas=son
karsilastirilir.

FIKSTUR GERCEK DEGIL, GECICI: katalog (urunler.json) OKUNMAZ, gercek koken dizinleri
OKUNMAZ, gercek R2 URL'i kullanilmaz. Depo DISINDA (tempfile) iki-depo duzeni kurulur
(<tmp>/pruvo + <tmp>/pruvo-jenerator), sentetik STL/PNG yazilir, kosum sonunda silinir.
Fikstur GERCEK CIKTININ SEKLINI taklit eder ([[nobetci-fikstur-sekli]]): binary STL
ucgen sayaci tutarli, PNG sihirli sayisi gercek, dosya adlari renk/parca ekli.
$GORSEL_KOKEN_DIR kosum boyunca TEMIZLENIR — cevre degiskeni sizmasi hukmu bozar.

KONTROL MUTANTI olculen eksenin ICINDEN secildi: celiski olcutunun kanonik anahtar
ureticisindeki `except (TypeError, ValueError)` demetinin SIRASI degistirilir. Ayni
satira dokunur, davranis TANIM GEREGI ayni -> YESIL kalmali. Kalmazsa batarya "her
degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur ([[beyan-edilmis-survivor]]).

Calistir:  python3 tools/gorsel-koken-dizin-mutasyon.py   (0 = gecti, 1 = kaldi)
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "gorsel_koken.py")

KAT = "Skan Art"
KOK = None            # <tmp>/pruvo            (kurulum() doldurur)
YALITILMIS_KOK = None  # <tmp>/yalitilmis/kok  (hicbir koken dizini YOK)
DIZIN_A = None         # <tmp>/pruvo/urun-gorsel-koken
DIZIN_B = None         # <tmp>/pruvo-jenerator/urun-gorsel-koken

# Yayinlanan gorsel URL'leri (sentetik host; gercek media.pruvo3d.com anahtari DEGIL).
ONEK = "https://ornek.gecersiz/urunler/"
GORSELLER = {
    "yalniz-b": [ONEK + "yalniz-b-p1.jpg", ONEK + "yalniz-b-p2.jpg"],
    "yalniz-a": [ONEK + "yalniz-a-p1.jpg"],
    "ayni-iki": [ONEK + "ayni-iki-p1.jpg"],
    "celisen": [ONEK + "celisen-p1.jpg"],
    "manifestsiz": [ONEK + "manifestsiz-p1.jpg"],
    "stl-yok": [ONEK + "stl-yok-p1.jpg"],
    "bozuk": [ONEK + "bozuk-p1.jpg"],
}


# ------------------------------------------------------------------- fikstur
def _stl_yaz(yol):
    """Gecerli binary STL: 80 bayt baslik + ucgen sayaci(1) + 1 ucgen(50) = 134 bayt."""
    with open(yol, "wb") as f:
        f.write(b"PRUVO SENTETIK FIKSTUR".ljust(80, b"\x00"))
        f.write((1).to_bytes(4, "little"))
        f.write(b"\x00" * 50)


def _png_yaz(yol):
    """Gercek PNG sihirli sayisi + ASGARI_RENDER_BAYT esigini asan govde."""
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(b"\x00" * 4096)


def _manifest(stl, ciftler):
    return {"kaynak_stl": stl,
            "gorseller": [{"dosya": d, "taban_render": t} for d, t in ciftler]}


def _yaz_json(yol, veri, indent=2, sort_keys=False):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=indent, sort_keys=sort_keys)


def kurulum():
    """Depo DISINDA iki-depo duzeni kurar; tmp kokunu dondurur."""
    global KOK, YALITILMIS_KOK, DIZIN_A, DIZIN_B
    tmp = tempfile.mkdtemp(prefix="koken-dizin-mutasyon-")
    KOK = os.path.join(tmp, "pruvo")
    DIZIN_A = os.path.join(KOK, "urun-gorsel-koken")
    DIZIN_B = os.path.join(tmp, "pruvo-jenerator", "urun-gorsel-koken")
    YALITILMIS_KOK = os.path.join(tmp, "yalitilmis", "kok")
    varliklar = os.path.join(tmp, "varliklar")
    for d in (DIZIN_A, DIZIN_B, YALITILMIS_KOK, varliklar):
        os.makedirs(d)

    stl = os.path.join(varliklar, "figur-baski-hazir.stl")
    _stl_yaz(stl)
    render = {}
    for ad in ("yalniz-b-p1", "yalniz-b-p2", "yalniz-a-p1", "ayni-iki-p1",
               "celisen-p1", "celisen-p1-ALTERNATIF", "stl-yok-p1", "bozuk-p1"):
        yol = os.path.join(varliklar, "taban-" + ad + ".png")
        _png_yaz(yol)
        render[ad] = yol

    # B1 — YALNIZ ikinci dizinde (golgelemenin oldurdugu kol; KaaN'in gercek hali).
    _yaz_json(os.path.join(DIZIN_B, "yalniz-b.json"),
              _manifest(stl, [("yalniz-b-p1.jpg", render["yalniz-b-p1"]),
                              ("yalniz-b-p2.jpg", render["yalniz-b-p2"])]))
    # B5 — YALNIZ ilk dizinde (onarim eski yolu bozmadi mi).
    _yaz_json(os.path.join(DIZIN_A, "yalniz-a.json"),
              _manifest(stl, [("yalniz-a-p1.jpg", render["yalniz-a-p1"])]))
    # B4 — IKI dizinde, KANONIK AYNI: anahtar sirasi ve girinti BILEREK farkli yazilir,
    # cunku celiski olcutu BAYT degil ICERIK kimligi olmalidir.
    ayni = _manifest(stl, [("ayni-iki-p1.jpg", render["ayni-iki-p1"])])
    _yaz_json(os.path.join(DIZIN_A, "ayni-iki.json"), ayni, indent=2, sort_keys=False)
    _yaz_json(os.path.join(DIZIN_B, "ayni-iki.json"), ayni, indent=4, sort_keys=True)
    # B3 — IKI dizinde, FARKLI taban_render (hangisi urunun gercek kokeni? BILINEMEZ).
    _yaz_json(os.path.join(DIZIN_A, "celisen.json"),
              _manifest(stl, [("celisen-p1.jpg", render["celisen-p1"])]))
    _yaz_json(os.path.join(DIZIN_B, "celisen.json"),
              _manifest(stl, [("celisen-p1.jpg", render["celisen-p1-ALTERNATIF"])]))
    # B7 — manifest VAR, kaynak_stl diskte YOK (capa-serit-dekoratif-figur'un sinifi).
    _yaz_json(os.path.join(DIZIN_B, "stl-yok.json"),
              _manifest(os.path.join(varliklar, "silinmis-kaynak.stl"),
                        [("stl-yok-p1.jpg", render["stl-yok-p1"])]))
    # B8 — parse edilemeyen kopya.
    with open(os.path.join(DIZIN_B, "bozuk.json"), "w", encoding="utf-8") as f:
        f.write("{ bu gecerli JSON degil")
    # "manifestsiz" icin HICBIR dizine dosya yazilmaz.
    return tmp


# ------------------------------------------------------------------- iddialar
def _dogrula(mod, pid, kok=None):
    return mod.manifest_dogrula(pid, GORSELLER[pid], kok if kok else KOK)


def b1_golgeleme_kalkti(mod):
    """Manifest YALNIZ ikinci dizinde -> GECER (ilk dizin var olsa bile)."""
    sebep, _k = _dogrula(mod, "yalniz-b")
    return sebep is None, "sebep=%r (beklenen None)" % (sebep,)


def b2_manifestsiz_block(mod):
    """Hicbir dizinde manifest yok -> BLOCK, gerekce MANIFEST YOKLUGU."""
    sebep, _k = _dogrula(mod, "manifestsiz")
    ok = isinstance(sebep, str) and "koken manifesti YOK" in sebep
    return ok, "sebep=%r (beklenen 'koken manifesti YOK' iceren blok)" % (sebep,)


def b3_celiski_block(mod):
    """Iki dizinde FARKLI manifest -> BLOCK, gerekce CELISKI (sessiz cozum YOK)."""
    sebep, _k = _dogrula(mod, "celisen")
    ok = isinstance(sebep, str) and "CELISEN" in sebep
    return ok, "sebep=%r (beklenen 'CELISEN' iceren blok)" % (sebep,)


def b4_ayni_icerik_gecer(mod):
    """Iki dizinde KANONIK AYNI -> GECER; kazanan ONCELIK sirasindaki ilk dizin."""
    sebep, kanit = _dogrula(mod, "ayni-iki")
    if sebep is not None:
        return False, "sebep=%r (beklenen None)" % (sebep,)
    beklenen = os.path.join(DIZIN_A, "ayni-iki.json")
    ok = any(beklenen in k for k in kanit)
    return ok, "kanit=%r (beklenen kazanan %s)" % (kanit[:1], beklenen)


def b5_yerel_dizin_okunuyor(mod):
    """Manifest YALNIZ ilk dizinde -> GECER (onarim eski yolu bozmadi)."""
    sebep, _k = _dogrula(mod, "yalniz-a")
    return sebep is None, "sebep=%r (beklenen None)" % (sebep,)


def b6_dizin_yok_block(mod):
    """Hicbir koken dizini yok -> BLOCK, gerekce DIZIN yoklugu (ayri kalem)."""
    sebep, _k = _dogrula(mod, "manifestsiz", kok=YALITILMIS_KOK)
    ok = isinstance(sebep, str) and "DIZINI bulunamadi" in sebep
    return ok, "sebep=%r (beklenen 'DIZINI bulunamadi' iceren blok)" % (sebep,)


def b7_sinif_ayrimi(mod):
    """"manifest hic yok" ile "kaynak dosyasi kayip" AYRI sinif olmali."""
    s_yok, _a = _dogrula(mod, "manifestsiz")
    s_stl, _b = _dogrula(mod, "stl-yok")
    if not isinstance(s_yok, str) or not isinstance(s_stl, str):
        return False, "iki kol da BLOCK olmali: %r / %r" % (s_yok, s_stl)
    a = mod.ihlal_sinifi(s_yok)
    b = mod.ihlal_sinifi(s_stl)
    ok = a == "manifest-yok" and b == "kaynak-dosya-yok"
    return ok, "sinif(manifestsiz)=%r sinif(stl-yok)=%r (beklenen 'manifest-yok'/'kaynak-dosya-yok')" % (a, b)


def b8_bozuk_manifest_block(mod):
    """Parse edilemeyen kopya -> BLOCK (fail-closed; 'okuyamadim' GECIS DEGIL)."""
    sebep, _k = _dogrula(mod, "bozuk")
    ok = isinstance(sebep, str) and "parse edilemiyor" in sebep
    return ok, "sebep=%r (beklenen 'parse edilemiyor' iceren blok)" % (sebep,)


IDDIALAR = [
    ("B1 GOLGELEME KALKTI (manifest yalniz 2. dizinde -> GECER)", b1_golgeleme_kalkti),
    ("B2 MANIFESTSIZ      (hicbir dizinde yok -> BLOCK)", b2_manifestsiz_block),
    ("B3 CELISKI          (iki dizinde farkli -> BLOCK)", b3_celiski_block),
    ("B4 AYNI ICERIK      (kanonik esit -> GECER, kazanan = oncelik)", b4_ayni_icerik_gecer),
    ("B5 YEREL DIZIN      (manifest yalniz 1. dizinde -> GECER)", b5_yerel_dizin_okunuyor),
    ("B6 DIZIN YOK        (hic koken dizini yok -> BLOCK, ayri gerekce)", b6_dizin_yok_block),
    ("B7 SINIF AYRIMI     (manifest-yok != kaynak-dosya-yok)", b7_sinif_ayrimi),
    ("B8 BOZUK MANIFEST   (parse edilemiyor -> BLOCK)", b8_bozuk_manifest_block),
]

# ------------------------------------------------------------------ mutantlar
_KAPI_GUARDI = ("    yol, man, sebep = manifest_yukle(pid, kok)\n"
                "    if sebep is not None:\n"
                "        return sebep, []\n")

_TARAMA_DONGUSU = "    for d in var_olan_dizinler(kok):\n"

_TARAMA_GOVDESI = ("        if os.path.isfile(yol):\n"
                   "            bulunan.append(yol)\n")

_CELISKI_KOLU = "        if len(anahtarlar) > 1:\n"

_DIZIN_KOLU = "    if not dizinler:\n"

_SINIF_SATIRI = ('    ("kaynak-dosya-yok", ("kaynak_stl diskte YOK", '
                 '"taban_render (STL render) diskte YOK")),\n')

_KANONIK_GOVDE = ("        return json.dumps(man, sort_keys=True, ensure_ascii=False)\n"
                  "    except (TypeError, ValueError):\n"
                  "        return None\n")

MUTANTLAR = [
    ("M-1 FAIL-OPEN: eksik/celisen koken kaniti SESSIZCE GECIYOR (manifestsiz urun eklenir)",
     _KAPI_GUARDI,
     "    yol, man, sebep = manifest_yukle(pid, kok)\n"
     "    if sebep is not None:\n"
     "        return None, [\"koken kaniti ARANMADI\"]\n",
     True, "B2/B3/B6/B8"),
    ("M-2 GOLGELEME GERI GELDI: yalniz VAR OLAN ILK dizin taraniyor",
     _TARAMA_DONGUSU,
     "    for d in var_olan_dizinler(kok)[:1]:\n",
     True, "B1"),
    ("M-3 CELISKI SESSIZCE COZULUYOR (iki farkli manifestten ilki kazaniyor)",
     _CELISKI_KOLU,
     "        if False:\n",
     True, "B3"),
    ("M-4 SINIF AYRIMI SILINDI: kaynak dosyasi kayip da 'manifest yok' sayiliyor",
     _SINIF_SATIRI,
     '    ("manifest-yok", ("kaynak_stl diskte YOK", '
     '"taban_render (STL render) diskte YOK")),\n',
     True, "B7"),
    ("M-5 DIZIN-YOK KOLU OLDURULDU (ayri gerekce kaybolur)",
     _DIZIN_KOLU,
     "    if False:\n",
     True, "B6"),
    ("M-6 POZITIF KOL OLDURULDU: bulunan manifest hic toplanmiyor (gecerli kanit REDDEDILIR)",
     _TARAMA_GOVDESI,
     "        if os.path.isfile(yol) and False:\n"
     "            bulunan.append(yol)\n",
     True, "B1/B4/B5"),
    ("M-7 KONTROL: except demetinin SIRASI degisti (davranis DEGISMEZ) — YESIL kalmali",
     _KANONIK_GOVDE,
     "        return json.dumps(man, sort_keys=True, ensure_ascii=False)\n"
     "    except (ValueError, TypeError):\n"
     "        return None\n",
     False, "-"),
]


# ----------------------------------------------------------------------- kosum
def kaynak_oku():
    with open(HEDEF, encoding="utf-8") as f:
        return f.read()


def modul_yukle(src, etiket):
    """Kaynagi BELLEKTE modul olarak calistirir. DISKE YAZILMAZ -> __pycache__ YOK."""
    mod = types.ModuleType("gorsel_koken_dizin_mutant_" + etiket)
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
    # Cevre degiskeni sizmasi hukmu bozar: kosum boyunca TEMIZ.
    onceki_env = os.environ.pop("GORSEL_KOKEN_DIR", None)
    tmp = kurulum()
    try:
        src = kaynak_oku()
        bas_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
        fails = []

        print("fikstur: %s  (depo DISINDA, kosum sonunda silinir)" % tmp)
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
            except Exception as e:                               # noqa: BLE001
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
        print("SONUC: YESIL ✅ — koken dizinleri BIRLESTIRILDI; manifestsiz/celisen/"
              "bozuk/dizinsiz kollarda kapi FAIL-CLOSED.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if onceki_env is not None:
            os.environ["GORSEL_KOKEN_DIR"] = onceki_env


if __name__ == "__main__":
    sys.exit(main())
