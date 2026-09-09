#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LCP KAPISI — B KOLU SEBEP TURETIMI kabul testi + mutasyon bataryasi.

NE OLCER (7 Eyl 2026, cip KraL-Tamirci-7Eyl):
  `lcp-onculuk-kapisi.py` B kolu, mutant sayisi esigin altina dustugunde eskiden
  SABIT "capalar bayatlamis" teshisi basiyordu. O teshis HIC OLCULMUYORDU ve
  okuyucuyu YANLIS DUZLEME yonlendiriyordu: 7 Eyl canli vakasinda ariza icerik
  duzlemindeydi (commit `63a48f7a` foto-slider'i sokerken preload+fetchpriority'yi
  goturdu), kapi ise "kapi govdesi curudu" diyordu.

  Bu test iki sozlesmeyi CIVILER:
    S1  Eksik mutantin sebebi TABLODAN + OLCULEN on-kosuldan TURETILIR:
        eksen ham metinde YOK  -> ICERIK-TUREVI  (yonlendirme: index.html)
        eksen ham metinde VAR  -> CAPA-BAYAT     (yonlendirme: kapi govdesi)
    S2  Capa TUTMAYAN mutant taramasi erken return'un ARKASINA DUSMEZ
        ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).

MUTANTLAR canli govdeye DEGIL, benzersiz adli IZOLE KOPYAYA uygulanir
([[mutant-canli-govdede-yasamaz]]); sys.dont_write_bytecode ile .pyc birakilmaz.

Cikis: 0 = YESIL · 1 = KIRMIZI (vaka dustu / mutant KACTI) · 2 = OLCULEMEDI
"""
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAPI = os.path.join(KOK, "tools", "lcp-onculuk-kapisi.py")
KOD_KIRMIZI, KOD_OLCULEMEDI = 1, 2


def yukle(yol, ad=None):
    ad = ad or ("lcpk_" + uuid.uuid4().hex[:10])
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- fikstur
def taban_metin():
    """Kapinin OKUDUGU canli index.html — taban budur, uydurma fikstur DEGIL."""
    return io.open(os.path.join(KOK, "index.html"), encoding="utf-8").read()


def icerigi_tamamla(ham):
    """preload + fetchpriority'yi GERI koyar (5 Eyl oncesi hale denk sentetik taban).
    Boylece 'icerik tam' kolunu da olcebiliriz."""
    mp = re.search(r"<picture\b.*?</picture>", ham, re.S)
    if not mp:
        return None
    blok = mp.group(0)
    avif = (re.search(r'<source[^>]*type="image/avif"[^>]*srcset="([^"]+)"', blok)
            or re.search(r'<source[^>]*srcset="([^"]+)"[^>]*type="image/avif"', blok))
    if not avif:
        return None
    sizes = re.search(r'sizes="([^"]+)"', blok)
    yeni = re.sub(r"<img ", '<img fetchpriority="high" ', blok, count=1)
    sent = ham.replace(blok, yeni, 1)
    preload = ('<link rel="preload" as="image" imagesrcset="%s" imagesizes="%s" '
               'type="image/avif">\n' % (avif.group(1), sizes.group(1) if sizes else "100vw"))
    return re.sub(r"</head>", preload + "</head>", sent, count=1)


# ---------------------------------------------------------------- vakalar
def vakalar(mod):
    """(ad, gecti_mi, aciklama) uretir."""
    sonuc = []
    ham = taban_metin()

    # V1 — canli taban (9 Eyl 2026 GUNCELLENDI, K392): vitrin 5 Eyl'de METNE cevrildi
    # (`63a48f7a`), yani sayfada eager gorsel LCP adayi YOK. Preload/fetchpriority
    # eksenleri artik "ICERIK EKSIK" degil, KAPSAM DISI — ucuncu kova. Eski vaka
    # ikisini ayni sayardi ve kapiyi DOGRU davranista kirmiziya yakiyordu.
    mut = mod.mutantlar(ham)
    icerik, bayat, kapsam = mod.eksik_mutant_sebebi(ham, mut)
    sonuc.append((
        "V1 canli taban: eksik mutantlarin HEPSI KAPSAM DISI (icerik=0, bayat=0)",
        len(kapsam) > 0 and len(icerik) == 0 and len(bayat) == 0,
        "kapsam=%d icerik=%d bayat=%d uretilen=%d"
        % (len(kapsam), len(icerik), len(bayat), len(mut))))

    # V1b — MENZIL DARALTMASI BIR BYPASS DEGIL: aday YOKKEN de batarya BOS kalmaz
    # ve daraltilmis esik TAM esikten kucuktur ama SIFIR degildir.
    hal0 = mod.on_kosul_hali(ham)
    dar = mod.beklenen_mutant_sayisi(hal0)
    sonuc.append((
        "V1b menzil daralinca esik KUCULUR ama batarya BOSALMAZ (0 < dar < tam)",
        (not hal0["gorsel-lcp-adayi"]) and 0 < dar < mod.BEKLENEN_MUTANT
        and len(mut) >= dar,
        "aday=%s dar=%d tam=%d uretilen=%d"
        % (hal0["gorsel-lcp-adayi"], dar, mod.BEKLENEN_MUTANT, len(mut))))

    # V2 — esik tabloya BAGLI mi? DAVRANISLA olculur: tablosu 1 satir BUYUTULMUS
    #      bir kopya import edilir; esik de 1 artmali. Sabit sayi ("magic 12")
    #      bu vakayi GECEMEZ. Kaynak dizgesi DEGIL davranis olculur.
    v2_gecti, v2_not = esik_tabloya_bagli_mi(mod)
    sonuc.append(("V2 esik tabloyu TAKIP eder (tablo+1 -> esik+1)", v2_gecti, v2_not))

    # V3 — on-kosul olcumu canli metinle UYUSUR (iddia degil)
    hal = mod.on_kosul_hali(ham)
    _h, sayim = mod.tara(ham)
    sonuc.append((
        "V3 on_kosul_hali olculen sayimla uyusur (preload/fetchpriority)",
        hal["preload"] == (sayim.get("preload_image", 0) > 0)
        and hal["fetchpriority"] == (sayim.get("fetchpriority_high", 0) > 0),
        "hal=%s sayim preload=%s fp=%s" % (
            {k: hal[k] for k in ("preload", "fetchpriority")},
            sayim.get("preload_image"), sayim.get("fetchpriority_high"))))

    # V4 — icerik TAMAMLANINCA 12/12 uretilir ve eksik sebebi KALMAZ
    tam = icerigi_tamamla(ham)
    if tam is None:
        sonuc.append(("V4 icerik tam: 12/12 mutant", None, "OLCULEMEDI: <picture>/AVIF capasi bulunamadi"))
    else:
        mut2 = mod.mutantlar(tam)
        ic2, ba2, kd2 = mod.eksik_mutant_sebebi(tam, mut2)
        sonuc.append((
            "V4 icerik TAMAMLANINCA TAM esik uretilir, eksik sebebi KALMAZ "
            "(kapsam-disi de 0'a duser — menzil ACILIR)",
            len(mut2) == mod.BEKLENEN_MUTANT and not ic2 and not ba2 and not kd2,
            "uretilen=%d/%d icerik=%d bayat=%d kapsam-disi=%d"
            % (len(mut2), mod.BEKLENEN_MUTANT, len(ic2), len(ba2), len(kd2))))

    # V5 — CAPA-BAYAT kolu GERCEKTEN ayirt eder: icerik TAM ama tablo bilinmeyen
    #      bir mutant ilan ederse (kapi govdesi onu uretemiyor) -> CAPA-BAYAT
    if tam is not None:
        eski = dict(mod.MUTANT_ON_KOSUL)
        try:
            mod.MUTANT_ON_KOSUL["M99"] = "preload"   # eksen VAR, mutant YOK
            ic3, ba3, _kd3 = mod.eksik_mutant_sebebi(tam, mod.mutantlar(tam))
            gecti = (("M99", "preload") in ba3) and not ic3
        finally:
            mod.MUTANT_ON_KOSUL.clear()
            mod.MUTANT_ON_KOSUL.update(eski)
        sonuc.append((
            "V5 eksen VAR + mutant YOK -> CAPA-BAYAT (ICERIK'e YAZILMAZ)",
            gecti, "bayat=%s icerik=%s" % (ba3, ic3)))

    # V5b — ICERIK-TUREVI kolunun KENDI vakasi (9 Eyl 2026, K392). V1 artik ucuncu
    #       kovaya dustugu icin "ICERIK-TUREVI gercekten uretiliyor mu" sorusunun
    #       ayri bir vakasi olmali; yoksa siniflamayi ters ceviren mutant (MA)
    #       hicbir vakayi dusuremez ve KACAR ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
    #       Kurgu: menzil ACIK (icerik tam) ama MENZILE BAGLI OLMAYAN bir eksen
    #       (preconnect) metinden SILINMIS -> o eksenin mutantlari ICERIK-TUREVI.
    if tam is not None:
        tam_precsiz = re.sub(r'<link\b[^>]*\brel="preconnect"[^>]*>\s*', "", tam)
        eski = dict(mod.MUTANT_ON_KOSUL)
        try:
            mod.MUTANT_ON_KOSUL["M97"] = "preconnect"
            ic4, ba4, kd4 = mod.eksik_mutant_sebebi(tam_precsiz,
                                                    mod.mutantlar(tam_precsiz))
        finally:
            mod.MUTANT_ON_KOSUL.clear()
            mod.MUTANT_ON_KOSUL.update(eski)
        hal4 = mod.on_kosul_hali(tam_precsiz)
        sonuc.append((
            "V5b eksen METINDE YOK + menzil ACIK -> ICERIK-TUREVI (BAYAT'a yazilmaz)",
            (not hal4["preconnect"]) and ("M97", "preconnect") in ic4
            and ("M97", "preconnect") not in ba4
            and ("M97", "preconnect") not in kd4,
            "preconnect_hal=%s icerik=%s bayat=%s kapsam=%s"
            % (hal4["preconnect"], ic4, ba4, kd4)))

    # V6 — S2 DAVRANIS testi: mutant sayisi esigin ALTINDA iken bile capa TUTMAYAN
    #      mutant RAPORLANIR mi? Eski hal erken return ile bunu maskeliyordu.
    #      Kapinin KENDI main()'i kosulur; dizge/kaynak taramasi DEGIL.
    v6_gecti, v6_not = maskeleme_kalkti_mi(mod)
    sonuc.append(("V6 esik ALTINDA da 'capa tutmayan' mutant RAPORLANIR", v6_gecti, v6_not))

    return sonuc


def esik_tabloya_bagli_mi(mod):
    """Modulun KENDI kaynagindan tablosu 1 satir buyutulmus kopya import eder."""
    kaynak_yol = getattr(mod, "__file__", None) or KAPI
    ham = io.open(kaynak_yol, encoding="utf-8").read()
    capa = '    "K1": "-",\n'
    if capa not in ham:
        return None, "OLCULEMEDI: tablo capasi bulunamadi"
    buyuk = ham.replace(capa, capa + '    "M98": "preload",\n', 1)
    gecici = tempfile.mkdtemp(prefix="lcp-esik-")
    try:
        yol = os.path.join(gecici, "lcpk_%s.py" % uuid.uuid4().hex[:10])
        io.open(yol, "w", encoding="utf-8").write(buyuk)
        k = yukle(yol)
        return (k.BEKLENEN_MUTANT == len(k.MUTANT_ON_KOSUL) == mod.BEKLENEN_MUTANT + 1,
                "tablo=%d esik=%d (taban esik=%d)"
                % (len(k.MUTANT_ON_KOSUL), k.BEKLENEN_MUTANT, mod.BEKLENEN_MUTANT))
    except Exception as exc:                                  # noqa: BLE001
        return None, "OLCULEMEDI: %s" % type(exc).__name__
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def maskeleme_kalkti_mi(mod):
    """mut<esik yolunda capa-tutmayan mutantin ciktiya DUSTUGUNU olcer."""
    import contextlib

    ham = taban_metin()
    gercek = mod.mutantlar

    def sahte(metin):
        liste = list(gercek(metin))[:3]          # esigin ALTINDA kalsin
        liste.append(("MX SAHTE capa tutmayan", metin, True))   # bozuk == ham
        return liste

    gecici = tempfile.mkdtemp(prefix="lcp-mask-")
    eski_index, eski_mut = mod.INDEX, mod.mutantlar
    try:
        yol = os.path.join(gecici, "index.html")
        io.open(yol, "w", encoding="utf-8").write(ham)
        mod.INDEX, mod.mutantlar = yol, sahte
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            rc = mod.main()
        cikti = tampon.getvalue()
        return ("MX SAHTE capa tutmayan" in cikti and rc == KOD_OLCULEMEDI,
                "rc=%s · 'MX SAHTE' ciktida=%s" % (rc, "MX SAHTE capa tutmayan" in cikti))
    except Exception as exc:                                  # noqa: BLE001
        return None, "OLCULEMEDI: %s" % type(exc).__name__
    finally:
        mod.INDEX, mod.mutantlar = eski_index, eski_mut
        shutil.rmtree(gecici, ignore_errors=True)


# ---------------------------------------------------------------- mutantlar
MUTANTLAR = [
    # 9 Eyl 2026 (K392): siniflama IKI kovadan UCE cikti; MA'nin capasi yeni govdeye
    # nisanlandi. MA hala AYNI iddiayi olcer: "ICERIK-TUREVI ile CAPA-BAYAT ayrimi
    # GERCEKTEN yapiliyor mu" — ters cevrilince V1/V5 tabandan SAPMALI.
    ("MA sinif ters cevrildi: her eksik CAPA-BAYAT sayilir",
     "        elif not hal.get(eksen, True):\n            icerik.append((kimlik, eksen))",
     "        elif not hal.get(eksen, True):\n            bayat.append((kimlik, eksen))"),
    # MA2 UCUNCU KOVA KAPATILIR: kapsam-disi kolu sokulunce menzil daraltmasi
    # yok olur ve canli taban yeniden "ICERIK EKSIK" sanilir (5-9 Eyl arizasi).
    ("MA2 ucuncu kova SOKULUR (kapsam-disi -> icerik-turevi)",
     "        if eksen in MENZILE_BAGLI_EKSEN and not hal.get(\"gorsel-lcp-adayi\", True):\n"
     "            kapsam_disi.append((kimlik, eksen))",
     "        if False:\n"
     "            kapsam_disi.append((kimlik, eksen))"),
    ("MB on_kosul_hali korlesti: her eksen VAR der",
     "return {\"preload\": pre, \"fetchpriority\": yuksek, \"preconnect\": prec,",
     "return {\"preload\": True, \"fetchpriority\": True, \"preconnect\": True,"),
    ("MC esik tablodan KOPARILDI (magic 12 geri kondu)",
     "BEKLENEN_MUTANT = len(MUTANT_ON_KOSUL)",
     "BEKLENEN_MUTANT = 12"),
    ("MD capa-tutmayan taramasi erken return'un ARKASINA itildi (maskeleme geri geldi)",
     "    tutmayan = [ad for ad, bozuk, _k in mut if bozuk == ham]\n",
     ""),
]
KONTROL = ("K1 KONTROL — olcum yuzeyine dokunmayan yorum degisti (YESIL kalmali)",
           "# --- 7 Eyl 2026: B KOLUNUN SEBEP TURETIMI ---",
           "# --- 7 Eyl 2026: B kolunun sebep turetimi ---")


def mutantli_kosum(ad, capa, yeni, gecici, taban):
    """OLDURME OLCUTU = TABANDAN SAPMA.

    🔴 Bir vakanin GECTI -> OLCULEMEDI'ye dusmesi de OLDURMEDIR. Onceki hal yalniz
    `is False` sayiyordu; mutant probu COKERTINCE (NameError) vaka OLCULEMEDI'ye
    dusuyor ve mutant SAG kaliyordu — olcememeyi gecmis saymak
    ([[fail-closed-kol-arkasindaki-kolu-maskeler]])."""
    ham = io.open(KAPI, encoding="utf-8").read()
    if capa not in ham:
        return None, "CAPA TUTMADI (metin bulunamadi)"
    bozuk = ham.replace(capa, yeni, 1)
    if bozuk == ham:
        return None, "MUTASYON UYGULANMADI"
    yol = os.path.join(gecici, "lcpk_%s.py" % uuid.uuid4().hex[:10])
    io.open(yol, "w", encoding="utf-8").write(bozuk)
    try:
        mod = yukle(yol)
    except Exception as exc:                                  # noqa: BLE001
        return True, "import COKTU (yakalandi): %s" % type(exc).__name__
    try:
        vs = vakalar(mod)
    except Exception as exc:                                  # noqa: BLE001
        return True, "vaka COKTU (yakalandi): %s" % type(exc).__name__
    sapan = []
    for vad, gecti, _acik in vs:
        if taban.get(vad) is True and gecti is not True:
            sapan.append("%s->%s" % (vad[:30], "DUSTU" if gecti is False else "OLCULEMEDI"))
    return (bool(sapan), "tabandan sapan: %s" % (", ".join(sapan) or "YOK"))


def main():
    print("=" * 78)
    print("LCP B-KOLU SEBEP TURETIMI — kabul + mutasyon (cip KraL-Tamirci-7Eyl)")
    print("=" * 78)
    if not os.path.isfile(KAPI):
        print("OLCULEMEDI: %s yok" % KAPI)
        return KOD_OLCULEMEDI

    canli = yukle(KAPI)
    print("A) KABUL VAKALARI")
    vs = vakalar(canli)
    dusen, olculemeyen = [], []
    for ad, gecti, acik in vs:
        if gecti is None:
            olculemeyen.append(ad)
            print("   🟠 OLCULEMEDI %-62s %s" % (ad, acik))
        elif gecti:
            print("   ✅ GECTI      %-62s %s" % (ad, acik))
        else:
            dusen.append(ad)
            print("   ❌ DUSTU      %-62s %s" % (ad, acik))

    taban = dict((ad, gecti) for ad, gecti, _a in vs)
    print("B) MUTASYON BATARYASI (izole kopya; canli govdeye YAMA YOK)")
    print("   oldurme olcutu = TABANDAN SAPMA (GECTI->DUSTU *veya* GECTI->OLCULEMEDI)")
    gecici = tempfile.mkdtemp(prefix="lcp-sebep-mut-")
    kacan = []
    try:
        for ad, capa, yeni in MUTANTLAR:
            yakalandi, not_ = mutantli_kosum(ad, capa, yeni, gecici, taban)
            if yakalandi is None:
                kacan.append("%s (%s)" % (ad, not_))
                print("   ❌ OLCULEMEDI %-58s %s" % (ad[:58], not_))
            elif yakalandi:
                print("   ✅ OLDU       %-58s %s" % (ad[:58], not_))
            else:
                kacan.append("%s (KACTI — %s)" % (ad, not_))
                print("   ❌ KACTI      %-58s %s" % (ad[:58], not_))
        kad, kcapa, kyeni = KONTROL
        kyakalandi, knot = mutantli_kosum(kad, kcapa, kyeni, gecici, taban)
        if kyakalandi is False:
            print("   ✅ KONTROL    %-58s YESIL kaldi" % kad[:58])
        else:
            kacan.append("%s (KONTROL yanlis KIRMIZI: %s)" % (kad, knot))
            print("   ❌ KONTROL    %-58s %s" % (kad[:58], knot))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("-" * 78)
    if olculemeyen and not dusen and not kacan:
        print("SONUC: OLCULEMEDI 🟠 — %d vaka olculemedi" % len(olculemeyen))
        return KOD_OLCULEMEDI
    if dusen or kacan:
        print("SONUC: KIRMIZI ❌ — %d vaka dustu · %d mutant kacti"
              % (len(dusen), len(kacan)))
        for x in dusen + kacan:
            print("   %s" % x)
        return KOD_KIRMIZI
    print("SONUC: YESIL ✅ — %d vaka + %d oldurucu mutant + 1 kontrol"
          % (len(vs), len(MUTANTLAR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
