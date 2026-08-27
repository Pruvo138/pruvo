#!/usr/bin/env python3
"""K324 ON-OLCUM PROBU (SALT OKUMA) — defterin rotasyon vetolarini SAYIYLA doker.

Hicbir dosyaya YAZMAZ (cikti dosyasi haric, o da git DISI olmalidir).
Amaci tek: "veto mantigi defterin TAMAMINI kilitliyor" iddiasini
HIPOTEZ olmaktan cikarip kova kova SAYIYA cevirmek.

Uc olcek ayni defter uzerinde yan yana basilir:
  (1) BLOK  — bugunku `--isaretciye-indir` birimi (_indirme_vetosu)
  (2) MADDE — bugunku `- ` madde birimi (_madde_sinifi)
  (3) HAL-SEGMENT — HIPOTEZ: satir basinda hal jetonu (✅/🟢/🔴/🔧/🟠/🟡)
      ile baslayan PARAGRAF birimi. Defterin ikinci yazim notasyonudur ve
      bugunku madde ayiklayici onu HIC gormez (yalniz `- ` bakar).

Kullanim (tek komut, bayraksiz calisir):
  python3 /tam/yol/tools/k324-kota-prob.py --cikti /git-disi/yol/prob.txt
"""
import argparse
import importlib.util
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))


def _rotasyon_modulu():
    yol = os.path.join(BURASI, "defter-rotasyon.py")
    spec = importlib.util.spec_from_file_location("defter_rotasyon", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _rotasyon_modulu()

# HIPOTEZ birimi: satir BASINDA duran hal jetonu yeni bir segment acar.
# Kume, aracin KENDI jeton kaynaklarindan TURETILIR — ikinci tablo ACILMAZ.
HAL_JETONLARI = tuple(dict.fromkeys(
    [j for j in R.KAPANIS_ISARETCILER if not any(c.isalpha() for c in j)]
    + list(R._EMOJI_JETONLAR)
    + ["🟢"]
))


def _bayt(metin):
    return len(metin.encode("utf-8"))


def _segmentle(govde):
    """Govdeyi HAL-SEGMENT birimlerine ayir.

    Segment = satir basinda hal jetonu tasiyan satir + ondan sonraki, satir
    basinda hal jetonu TASIMAYAN ve `- ` ile BASLAMAYAN devam satirlari.
    `- ` maddeleri bu ayiklayicinin DISINDA kalir (onlar madde birimidir).
    Doner: [(tur, satirlar)] — tur ∈ {"HAL", "MADDE", "DUZ"}
    """
    parcalar = []
    i = 0
    n = len(govde)
    while i < n:
        satir = govde[i]
        if satir.startswith("- "):
            blok = [satir]
            j = i + 1
            while j < n and not govde[j].startswith("- ") and not _hal_baslangici(govde[j]):
                blok.append(govde[j])
                j += 1
            parcalar.append(("MADDE", blok))
            i = j
        elif _hal_baslangici(satir):
            blok = [satir]
            j = i + 1
            while j < n and not govde[j].startswith("- ") and not _hal_baslangici(govde[j]):
                blok.append(govde[j])
                j += 1
            parcalar.append(("HAL", blok))
            i = j
        else:
            parcalar.append(("DUZ", [satir]))
            i += 1
    return parcalar


def _hal_baslangici(satir):
    s = satir.lstrip()
    return any(s.startswith(j) for j in HAL_JETONLARI)


def _segment_sinifi(metin):
    """HAL-SEGMENT icin sinif — MADDE yuklemleriyle AYNI kaynaklardan.

    Tek fark: madde yuklemleri `- ` onekini sart kosar. Segmenti gecici
    olarak `- ` ONEKLI hale getirip AYNI fonksiyonlari cagiriyoruz; boylece
    ikinci bir hukum tablosu URETILMEZ (bu bir PROBdur, hukum degil).
    """
    sahte = "- " + metin
    return R._madde_sinifi(sahte), R._madde_tasinir_mi(sahte)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--defter", default="/Users/okan/dev/pruvo/DEVAM.md")
    ap.add_argument("--cikti", required=True,
                    help="ham cikti dosyasi (git DISI bir yol olmali)")
    a = ap.parse_args(argv)

    with open(a.defter, "rb") as f:
        ham = f.read()
    metin = ham.decode("utf-8")
    satirlar = metin.splitlines()

    L = []
    P = L.append
    P("=== K324 ON-OLCUM PROBU (SALT OKUMA) ===")
    P("DEFTER=%s" % a.defter)
    P("DOSYA_SATIR=%d DOSYA_BAYT=%d" % (len(satirlar), len(ham)))
    P("TAVAN_SATIR=%s TAVAN_BAYT=%s" % (R.TAVAN_SATIR, R.TAVAN_BAYT))
    P("HAL_JETONLARI=%s" % " ".join(HAL_JETONLARI))
    P("")

    baslik_bolgesi, bloklar = R._bloklari_ayir(metin)
    P("BASLIK_BOLGESI_SATIR=%d BLOK=%d" % (len(baslik_bolgesi), len(bloklar)))
    P("")

    # ---------- OLCEK 1: BLOK ----------
    P("--- OLCEK-1 BLOK (bugunku --isaretciye-indir birimi) ---")
    blok_indirilebilir_bayt = 0
    for i, b in enumerate(bloklar):
        bm = R._blok_metni(b)
        veto = R._indirme_vetosu(b)
        P("BLOK[%d] bayt=%d satir=%d korumali=%s kapsayici=%s tasinir=%s"
          % (i, _bayt(bm), 1 + len(b["govde"]),
             R._blok_korumali_mi(b), R._blok_kapsayici_mi(b), R._tasinir_mi(b)))
        P("        baslik=%s" % b["baslik"][:96])
        P("        indirme_vetosu=%s" % (veto if veto else "YOK (INDIRILEBILIR)"))
        if veto is None:
            blok_indirilebilir_bayt += _bayt(bm)
    P("OLCEK1_INDIRILEBILIR_BLOK_BAYT=%d" % blok_indirilebilir_bayt)
    P("")

    # ---------- OLCEK 2: MADDE (bugunku) ----------
    P("--- OLCEK-2 MADDE (bugunku `- ` birimi) ---")
    import collections
    kova = collections.Counter()
    madde_tasinabilir_bayt = 0
    madde_sayisi = 0
    for i, b in enumerate(bloklar):
        yerel = collections.Counter()
        _kalan, tasinacak = R._maddeleri_isle(list(b["govde"]), yerel, [])
        madde_sayisi += sum(yerel.values())
        kova.update(yerel)
        for t in tasinacak:
            madde_tasinabilir_bayt += _bayt(t)
        if sum(yerel.values()):
            P("BLOK[%d] madde=%d %s tasinacak=%d" % (
                i, sum(yerel.values()),
                " ".join("%s=%d" % (k, yerel.get(k, 0)) for k in R.MADDE_KOVALARI),
                len(tasinacak)))
    P("OLCEK2_MADDE_TOPLAM=%d %s" % (
        madde_sayisi, " ".join("%s=%d" % (k, kova.get(k, 0)) for k in R.MADDE_KOVALARI)))
    P("OLCEK2_TASINABILIR_BAYT=%d" % madde_tasinabilir_bayt)
    P("")

    # ---------- OLCEK 3: HAL-SEGMENT (hipotez) ----------
    P("--- OLCEK-3 HAL-SEGMENT (HIPOTEZ birimi) ---")
    seg_kova = collections.Counter()
    seg_tasinabilir_bayt = 0
    seg_gorunmez_bayt = 0     # bugunku ayiklayicinin HIC gormedigi bayt
    for i, b in enumerate(bloklar):
        parcalar = _segmentle(list(b["govde"]))
        hal_sayisi = sum(1 for t, _s in parcalar if t == "HAL")
        if not hal_sayisi:
            continue
        P("BLOK[%d] hal_segment=%d  baslik=%s" % (i, hal_sayisi, b["baslik"][:64]))
        for tur, sat in parcalar:
            if tur != "HAL":
                continue
            m = "\n".join(sat)
            sinif, tasinir = _segment_sinifi(m)
            seg_kova[sinif] += 1
            seg_gorunmez_bayt += _bayt(m)
            if tasinir:
                seg_tasinabilir_bayt += _bayt(m)
            sebep = R._ortak_satir_sebebi("- " + m)
            P("   SEG sinif=%-16s tasinir=%-5s bayt=%-5d ilk=%s"
              % (sinif, tasinir, _bayt(m), sat[0][:70]))
            if sebep:
                P("       SEBEP: %s" % sebep[:150])
    P("OLCEK3_SEGMENT_TOPLAM=%d %s" % (
        sum(seg_kova.values()),
        " ".join("%s=%d" % (k, seg_kova.get(k, 0)) for k in R.MADDE_KOVALARI)))
    P("OLCEK3_TASINABILIR_BAYT=%d" % seg_tasinabilir_bayt)
    P("OLCEK3_BUGUN_GORUNMEZ_BAYT=%d" % seg_gorunmez_bayt)
    P("")

    # ---------- HEDEF MUHASEBESI ----------
    hedef = 11500
    P("--- HEDEF MUHASEBESI ---")
    P("SIMDI_BAYT=%d HEDEF_BAYT=%d GEREKEN_DUSUS=%d"
      % (len(ham), hedef, max(0, len(ham) - hedef)))
    P("OLCEK2_ILE_KARSILANAN=%d" % madde_tasinabilir_bayt)
    P("OLCEK2+OLCEK3_ILE_KARSILANAN=%d" % (madde_tasinabilir_bayt + seg_tasinabilir_bayt))
    P("=== PROB SONU ===")

    cikti = "\n".join(L) + "\n"
    with open(a.cikti, "w", encoding="utf-8") as f:
        f.write(cikti)
    sys.stdout.write(cikti)
    return 0


if __name__ == "__main__":
    sys.exit(main())
