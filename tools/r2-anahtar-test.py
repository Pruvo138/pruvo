#!/usr/bin/env python3
"""r2-anahtar-test.py — R2 gorsel anahtari turetmenin KABUL TESTI.

Neden: anahtar 4 dosyada satir-ici kopyalanmisti; kopyalar kayarsa iki urunun gorseli ayni
R2 anahtarina yazilir ve biri digerini EZER. Bu test hem kopyalarin dondugunu hem de
TEK KAYNAK modulunun (tools/r2_anahtar.py) YAYINDAKI anahtarlari birebir uretmeye devam
ettigini olcer.

Kosum:  python3 tools/r2-anahtar-test.py     (ag yok, yazma yok, exit 0 = yesil)

Testler:
  (a) 4 cagri yerinde satir-ici anahtar turetme / satir-ici "urunler/%s-%d.jpg" KALMADI
  (b) GERIYE DONUK UYUM — urunler.json'daki gercek gorsel URL'lerinden en az 200 ornek:
      URL'de FIILEN duran anahtar == modulun urettigi anahtar (th/pr/mw/cgt); ESKI 16
      tireli CGTrader anahtari ("cgt-<id>") 7 Agu 2026 KraL hukmuyle artik YENIDEN
      URETILMEZ (canlida oldugu gibi kalir) -> bu test yuzeyinden BILEREK disaridadir
      + TUM anahtarlarda normalize() no-op (mevcut hicbir anahtar kaymaz)
  (c) ASCII-disi / tirnakli / bosluklu girdilerde cikti guvenli ([a-z0-9-]+)
  (d) th/pr/mw/cgt/c3d onekleri birebir (cgt'deki tire 7 Agu 2026 KraL hukmuyle KALKTI,
      kanonik artik tiresiz "cgt"; eski canli "cgt-" anahtar yeniden BASILMAZ)
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(HERE)
URUNLER = os.path.join(KOK, "urunler.json")
ASGARI_ORNEK = 200

_s = importlib.util.spec_from_file_location("r2_anahtar", os.path.join(HERE, "r2_anahtar.py"))
r2k = importlib.util.module_from_spec(_s)
_s.loader.exec_module(r2k)

hatalar = []


def sonuc(ad, ok, detay=""):
    print("%s %s%s" % ("OK  " if ok else "KIRMIZI", ad, ("  -> " + detay) if detay else ""))
    if not ok:
        hatalar.append(ad)


# ----------------------------------------------------------- AKTIF-REFERANS EKSENI
# 🔴 13 Agu 2026 KraL hukmu: kapinin yargi birimi "R2'de duran HER anahtar" DEGIL,
# "urunler.json'da GORSEL OLARAK REFERANS VERILEN anahtar"dir. Referans verilmeyen
# tarihsel/cache anahtari kimseye gorunmez -> KAPSAM DISI (sayilir, yargilanmaz).
# Muafiyet/whitelist listesi YOKTUR: kapsam katalogdan TURER, katalog buyudukce
# kendiliginden dogru kalir.

def referans_anahtarlari(urunler):
    """urunler.json objesinden GORSEL OLARAK REFERANS VERILEN R2 anahtarlarini cikarir.

    Donus: (anahtarlar, bos_gorsel_sayisi)
      anahtarlar        : [(urun_id, anahtar), ...] — cozulen her gorsel URL'si.
      bos_gorsel_sayisi : gorseller[] bos/eksik urun sayisi (kapsam disi; cokmez)."""
    anahtarlar = []
    bos = 0
    for u in urunler:
        if not isinstance(u, dict):
            continue
        gs = u.get("gorseller") or []
        if not gs:
            bos += 1
        for g in gs:
            a, _n = r2k.anahtar_coz(g)
            if a:
                anahtarlar.append((u.get("id", "?"), a))
    return anahtarlar, bos


def kirli_mi(anahtar):
    """Referans verilen anahtar 'kirli' mi? Normalize kurali: [a-z0-9-] disina cikan
    (Turkce harf/bosluk/tirnak/emoji) anahtar yayindaki URL'yi KIRAR -> kirli.
    Bas/son tire TARIHSEL gercektir (ASCII-guvenli, goruntu kirilmaz) -> kirli DEGIL.
    (49 ESKI baslik-slug anahtari sonu tireli; bkz. r2_anahtar.normalize)."""
    return r2k.normalize(anahtar) != anahtar.strip("-")


def yargila(referanslar, tum_anahtarlar=None):
    """AKTIF-REFERANS yargisi. referanslar: [(urun_id, anahtar), ...].

    tum_anahtarlar verilirse (R2 kova listesi) referans VERILMEYEN anahtarlar KAPSAM DISI
    sayilir (yargilanmaz, kirli uretmez). Referans verilen anahtar tum_anahtarlar'da da
    gecse REFERANS AGIR BASAR (kirliyse KIRMIZI).
    Donus: (kirli_liste, kapsam_disi)."""
    referans_kumesi = {a for _uid, a in referanslar}
    kirli = []
    kapsam_disi = 0
    if tum_anahtarlar is None:
        tum_anahtarlar = referans_kumesi      # offline: yalniz referans gorunur
    for a in set(tum_anahtarlar):
        referansli = a in referans_kumesi
        if referansli:
            if kirli_mi(a):
                kirli.append(a)
        else:
            kapsam_disi += 1
    return kirli, kapsam_disi


def tum_anahtarlari_oku(yol):
    """Optional R2 kova anahtar listesi dosyasi (satir basina bir anahtar). Yoksa None.
    Yalniz yerel olcumde (KAPSAM_DISI) kullanilir; CI'da env YOK -> offline kalir."""
    if not yol or not os.path.exists(yol):
        return None
    anahtarlar = []
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            a = satir.strip()
            if a:
                anahtarlar.append(a)
    return anahtarlar


# --------------------------------------------------------------------- (a) kopya kalmadi
CAGRI_YERLERI = ["urun-ekle.py", "printables-ekle.py", "makerworld-ekle.py", "gorsel-cakisma-onar.py"]
# satir-ici anahtar normalizasyonu ya da satir-ici R2 yolu
KOPYA_DESENLERI = [
    re.compile(r"""re\.sub\(\s*r?["']\[\^a-z0-9-\]"""),          # anahtar normalizasyonu kopyasi
    re.compile(r"""["']urunler/%s-%d\.jpg["']"""),                # gorsel yolu kopyasi
    re.compile(r"""\{\s*["']Thingiverse["']\s*:"""),              # onek sozlugu kopyasi
]


def test_a():
    for ad in CAGRI_YERLERI:
        yol = os.path.join(HERE, ad)
        if not os.path.exists(yol):
            sonuc("(a) %s var" % ad, False, "dosya yok")
            continue
        metin = open(yol, encoding="utf-8").read()
        vurus = []
        for i, satir in enumerate(metin.splitlines(), 1):
            if satir.lstrip().startswith("#"):
                continue
            for d in KOPYA_DESENLERI:
                if d.search(satir):
                    vurus.append("%s:%d" % (ad, i))
        sonuc("(a) %s satir-ici anahtar turetme yok" % ad, not vurus, ", ".join(vurus))
        if "r2_anahtar" not in metin:
            sonuc("(a) %s r2_anahtar modulunu kullaniyor" % ad, False, "import yok")
        else:
            sonuc("(a) %s r2_anahtar modulunu kullaniyor" % ad, True)


# ------------------------------------------------------- (b) geriye donuk uyum (EN ONEMLI)
# 🔴 "cgt" (tiresiz) 7 Agu 2026 KraL hukmuyle kanonik. Eski 16 tireli canli anahtar
# ("cgt-<id>") govde cikarilinca basinda tire kalir (isdigit() False) -> asagidaki dongu
# onlari SESSIZCE atlar (yeniden uretme iddia edilmez, degistirilmezler de).
ONEK_PLATFORM = [("cgt", "CGTrader"), ("th", "Thingiverse"), ("pr", "Printables"),
                  ("mw", "MakerWorld"), ("c3d", "Cults3D")]


def test_b():
    if not os.path.exists(URUNLER):
        sonuc("(b) urunler.json bulundu", False, URUNLER)
        return
    urunler = json.load(open(URUNLER, encoding="utf-8"))
    anahtarlar, bos_gorsel = referans_anahtarlari(urunler)
    sonuc("(b) urunler.json'dan anahtar cikarildi", len(anahtarlar) >= ASGARI_ORNEK,
          "%d anahtar (%d bos/eksik gorselli urun)" % (len(anahtarlar), bos_gorsel))

    # b1: kaynak-id tabanli anahtarlar (th/pr/mw/cgt-) modulden BIREBIR uretilebilmeli
    kayan, sayilan = [], 0
    for uid, a in anahtarlar:
        for onek, platform in ONEK_PLATFORM:
            govde = a[len(onek):]
            if a.startswith(onek) and govde.isdigit():
                sayilan += 1
                if r2k.gkey(platform, govde) != a:
                    kayan.append("%s: %s != %s" % (uid, r2k.gkey(platform, govde), a))
                break
    sonuc("(b) kaynak-id anahtarlari yeniden uretiliyor (%d/%d)" % (sayilan - len(kayan), sayilan),
          not kayan and sayilan >= ASGARI_ORNEK,
          ("%d KAYDI: " % len(kayan)) + "; ".join(kayan[:20]) if kayan
          else ("ornek yetersiz (<%d)" % ASGARI_ORNEK if sayilan < ASGARI_ORNEK else ""))

    # b2/b3 -> AKTIF-REFERANS yargisi (13 Agu 2026 KraL hukmu): yalniz REFERANS VERILEN
    # anahtar normalize kuralina gore yargilanir (kirli -> KIRMIZI). Referans VERILMEYEN
    # anahtarlar KAPSAM DISI sayilir (yargilanmaz), sayisi gorunur kalir.
    tum = tum_anahtarlari_oku(os.environ.get("PRUVO_R2_ANAHTAR_LISTESI"))
    kirli, kapsam_disi = yargila(anahtarlar, tum)
    kirli_kume = set(kirli)
    kirli_bas = ["%s: %s" % (uid, a) for uid, a in anahtarlar if a in kirli_kume]
    sonuc("(b) referansli anahtar normalize kuralina uyuyor (KIRMIZI_REFERANS=%d)" % len(kirli),
          not kirli, ("%d KAYDI: " % len(kirli_bas)) + "; ".join(kirli_bas[:20]))
    tireli = sum(1 for _uid, a in anahtarlar if a.strip("-") != a)
    print("     KIRMIZI_REFERANS=%d" % len(kirli))
    print("     KAPSAM_DISI=%d" % kapsam_disi)
    print("     bilgi: sonu/basi tireli tarihsel anahtar sayisi = %d" % tireli)
    if tum is None:
        print("     bilgi: R2 kova listesi verilmedi (PRUVO_R2_ANAHTAR_LISTESI) — KAPSAM_DISI=0")


# ------------------------------------------------------------- (c) ASCII-disi / tirnak / bosluk
ZOR_GIRDILER = [
    "Kapı Kolu Çerçevesi",
    "O'Brien's \"özel\" parça",
    "  bosluklu   baslik  ",
    "ÜÇGEN ŞİMŞEK ĞÖZ",
    "emoji 🚗 var",
    "///---///",
    "Ünlü/Marka: Şoför+Kolu",
]


def test_c():
    for g in ZOR_GIRDILER:
        a = r2k.normalize(g)
        sonuc("(c) normalize guvenli: %r" % g, re.fullmatch(r"[a-z0-9-]*", a) is not None, a)
        s = r2k.urun_slug(g, yedek="yedek")
        sonuc("(c) urun_slug guvenli: %r" % g, re.fullmatch(r"[a-z0-9-]+", s) is not None, s)
    # anahtar ASCII-disi kaynak-id'de bile ASCII kalmali
    a = r2k.gkey("Thingiverse", "12ö34")
    sonuc("(c) gkey ASCII-disi kaynak-id", a == "th12-34", a)
    # yol/URL uretimi
    sonuc("(c) gorsel_yolu", r2k.gorsel_yolu("th123", 2) == "urunler/th123-2.jpg",
          r2k.gorsel_yolu("th123", 2))
    sonuc("(c) gorsel_url", r2k.gorsel_url("pr9", 1) == "https://media.pruvo3d.com/urunler/pr9-1.jpg",
          r2k.gorsel_url("pr9", 1))
    # ASCII-disi uzak URL kacisi (thing-hazirla/gallery ile ayni safe kumesi)
    q = r2k.url_kacir("https://cdn.example.com/ö dosya.jpg?a=1&b=2")
    sonuc("(c) url_kacir ASCII", all(ord(c) < 128 for c in q) and "?a=1&b=2" in q, q)


# ------------------------------------------------------------------------- (d) onekler birebir
def test_d():
    beklenen = [
        ("Thingiverse", "6543210", "th6543210"),
        ("Printables", 1234567, "pr1234567"),
        ("MakerWorld", 998877, "mw998877"),
        ("CGTrader", "6267929", "cgt6267929"),    # 7 Agu 2026 KraL hukmu: tiresiz kanonik
        ("Cults3D", "s2000-console-organizer-v2-0", "c3ds2000-console-organizer-v2-0"),
    ]
    for platform, sid, bek in beklenen:
        a = r2k.gkey(platform, sid)
        sonuc("(d) %s -> %s" % (platform, bek), a == bek, a)
    sonuc("(d) cgt oneki tiresiz (7 Agu 2026 KraL hukmu)",
          r2k.ONEKLER["CGTrader"] == "cgt", r2k.ONEKLER["CGTrader"])
    sonuc("(d) th/pr/mw/c3d onekleri tiresiz",
          (r2k.ONEKLER["Thingiverse"], r2k.ONEKLER["Printables"], r2k.ONEKLER["MakerWorld"],
           r2k.ONEKLER["Cults3D"]) == ("th", "pr", "mw", "c3d"), "")
    sonuc("(d) gkey_ham yedegi", r2k.gkey_ham("!!!") == "!!!" and r2k.gkey_ham("!!!", yedek=False) == "",
          repr(r2k.gkey_ham("!!!")))
    # 7 Agu 2026: bilinmeyen platform artik VARSAYILAN olarak FAIL-CLOSED (once sessizce "x42"
    # uretiyordu — bkz r2_anahtar.BilinmeyenPlatform + modul docstring).
    try:
        r2k.gkey("Bilinmeyen", "42")
        sonuc("(d) bilinmeyen platform varsayilan FAIL-CLOSED (raise)", False, "raise etmedi")
    except r2k.BilinmeyenPlatform:
        sonuc("(d) bilinmeyen platform varsayilan FAIL-CLOSED (raise)", True)
    a = r2k.gkey("Bilinmeyen", "42", bilinmeyen_sessiz=True)
    sonuc("(d) bilinmeyen platform bilinmeyen_sessiz=True ile eski davranis (x42)", a == "x42", a)


# ------------------------------------------------------------------- (e) aktif-referans
def test_e():
    """AKTIF-REFERANS ekseninin kabul vakalari (13 Agu 2026 KraL hukmu).

    Vakalar yargila()/referans_anahtarlari() uzerinde SENTETIK fiksturle kosar — gercek
    R2'ye ag YOK. Kapsam evreni katalogdan turer, elle listeden DEGIL."""
    KIRLI = "bozuk anahtar"     # bosluk -> normalize tireye cevirir -> kirli
    TEMIZ = "temiz-anahtar-1"

    # vaka 1: referansli + kirli -> KIRMIZI
    k, kd = yargila([("p1", KIRLI)], [KIRLI])
    sonuc("(e1) referansli + kirli -> KIRMIZI", set(k) == {KIRLI} and kd == 0,
          "kirli=%r kapsam_disi=%d" % (k, kd))

    # vaka 2: referanssiz + kirli -> GECER (kapsam disi; KAPSAM_DISI artar)
    k, kd = yargila([], [KIRLI])
    sonuc("(e2) referanssiz + kirli -> GECER (kapsam disi)", set(k) == set() and kd == 1,
          "kirli=%r kapsam_disi=%d" % (k, kd))

    # vaka 3: referansli + temiz -> GECER
    k, kd = yargila([("p1", TEMIZ)], [TEMIZ])
    sonuc("(e3) referansli + temiz -> GECER", set(k) == set() and kd == 0,
          "kirli=%r kapsam_disi=%d" % (k, kd))

    # vaka 4: ayni kirli anahtar HEM referansli HEM referanssiz gecerse -> KIRMIZI
    # (referans agir basar; "baska" referanssiz oldugu icin kapsam_disi=1, kirli=1)
    k, kd = yargila([("p1", KIRLI)], [KIRLI, "baska"])
    sonuc("(e4) hem referansli hem referanssiz kirli -> KIRMIZI (referans agir basar)",
          set(k) == {KIRLI} and kd == 1, "kirli=%r kapsam_disi=%d" % (k, kd))

    # vaka 5: gorseller[] bos/eksik urun -> kapi COKMEZ, o urun kapsam disi sayilir
    r_bos, bos1 = referans_anahtarlari([{"id": "x-bos"}])
    r_eksik, bos2 = referans_anahtarlari([{"id": "x-eksik", "gorseller": []}])
    sonuc("(e5) gorseller[] bos/eksik urun cokmez + kapsam disi sayilir",
          r_bos == [] and bos1 == 1 and r_eksik == [] and bos2 == 1,
          "bos=%d eksik=%d" % (bos1, bos2))

    # vaka 6: kapsam evreni katalogdan turer (elle liste YOK) — fiksture yeni referansli
    # kirli anahtar eklenince kapi KENDILIGINDEN kirmizi yakar (liste guncellemesi GEREKMEZ).
    mini = [{"id": "a", "gorseller": ["https://media.pruvo3d.com/urunler/temiz-1.jpg"]}]
    r6, _ = referans_anahtarlari(mini)
    k6, _ = yargila(r6)
    sonuc("(e6a) temiz katalog kirli URETMEZ", set(k6) == set(), "kirli=%r" % k6)
    mini.append({"id": "b", "gorseller": ["https://media.pruvo3d.com/urunler/bozuk anahtar-1.jpg"]})
    r6, _ = referans_anahtarlari(mini)
    k6, _ = yargila(r6)
    sonuc("(e6b) yeni referansli kirli anahtar KENDILIGINDEN kirmizi yakar",
          set(k6) == {KIRLI}, "kirli=%r" % k6)


# ------------------------------------------------------------------- MUTASYON BATARYASI
# 🔴 13 Agu 2026 KraL hukmu: OLDURUCU MUTANT (en az 4) + kontrol. Her mutant test_e'nin
# bir vakasini KIRMIZI yakmali; kontrol mutanti YESIL kalmali. Mutasyon kaynaga (bu dosyaya)
# UYGULANMAZ — exec'lenen mutasyonlu kopya uzerinde kosar, kanonik kaynak birebir kalir.
MUTANTLAR = [
    # (ad, eski_satir, yeni_satir, kirmizi_beklenir_mi)
    # 🔴 eski_satir PARCALARA BOLUNUR (string + string): capa dizesi bu listede HAM
    # gecerse kaynak.count() onu HEM gercek kodda HEM bu listede gorur ve capa TEKIL
    # bulunamaz (olculdu). Bolununce listedeki gecis "eski"nin bitisik halini icermez.
    ("R1 kapsam yine R2 kova listesinden turetildi (referanssiz da yargilanir)",
     "        referansli " + "= a in referans_kumesi", "        referansli = True", True),
    ("R2 referansli kirli anahtar kapsam disi sayildi (fail-open)",
     "                kirli." + "append(a)", "                kapsam_disi += 1", True),
    ("R3 vaka 4'te referanssiz kol agir basti (referansli kirli kapsam disi)",
     "        referansli " + "= a in referans_kumesi", "        referansli = False", True),
    ("R4 gorseller[] bos olunca istisna firlatildi",
     "            bos " + "+= 1", "            raise RuntimeError(\"gorseller bos (mutant)\")", True),
    ("KONTROL davranis degismeyen degisiklik",
     "    kirli " + "= []", "    kirli = list()", False),
]


def mutasyon():
    print("\n=== MUTASYON — her oldurucu mutant test_e'yi KIRMIZI yakmali ===")
    kaynak = open(os.path.join(HERE, "r2-anahtar-test.py"), encoding="utf-8").read()
    kirmizi = 0
    beklenen = 0
    kontrol_yesil = 0
    kontrol_toplam = 0
    for ad, eski, yeni, kirmizi_beklenir in MUTANTLAR:
        if kaynak.count(eski) != 1:
            print("  CAPA HATASI  %s -> %r %d kez gecen (1 olmali)"
                  % (ad, eski[:70], kaynak.count(eski)))
            hatalar.append("mutant capasi: " + ad)
            continue
        mut = kaynak.replace(eski, yeni, 1)
        g = {"__name__": "mutant_cocuk", "__file__": os.path.join(HERE, "r2-anahtar-test.py")}
        istisna = None
        try:
            exec(compile(mut, "mutant_cocuk", "exec"), g)
            g["test_e"]()
        except Exception as e:                      # coken mutant da KIRMIZIdir (vaka 5/R4)
            istisna = e
        hatalar_m = g.get("hatalar", [])
        yandi = bool(istisna) or len(hatalar_m) > 0
        if kirmizi_beklenir:
            beklenen += 1
            if yandi:
                kirmizi += 1
                print("  PASS  %s -> KIRMIZI" % ad)
            else:
                hatalar.append("mutant yakalanmadi: " + ad)
                print("  FAIL  %s -> YESIL KALDI (nobet OLU)" % ad)
        else:
            kontrol_toplam += 1
            if not yandi:
                kontrol_yesil += 1
                print("  PASS  %s -> YESIL" % ad)
            else:
                hatalar.append("kontrol mutanti kirmizi: " + ad)
                print("  FAIL  %s -> KIRMIZI (batarya olcmuyor) %s" % (ad, istisna or ""))
    print("  MUTANT_KIRMIZI=%d/%d  KONTROL_YESIL=%d/%d"
          % (kirmizi, beklenen, kontrol_yesil, kontrol_toplam))
    return kirmizi, beklenen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="mutant turunu da kosar (elle; CI'da kosmaz)")
    a = ap.parse_args()

    if a.mutasyon:
        mutasyon()
        print("")
        if hatalar:
            print("MUTASYON KIRMIZI — %d basarisiz: %s" % (len(hatalar), "; ".join(hatalar)))
            sys.exit(1)
        print("MUTASYON YESIL — hepsi yakalandi")
        return

    test_a()
    test_b()
    test_c()
    test_d()
    test_e()

    print("")
    if hatalar:
        print("KIRMIZI — %d basarisiz: %s" % (len(hatalar), "; ".join(hatalar)))
        sys.exit(1)
    print("YESIL — hepsi gecti")


if __name__ == "__main__":
    main()
