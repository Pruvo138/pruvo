#!/usr/bin/env python3
"""gorsel_mukerrer_kapisi.py — ALGISAL (perceptual) mukerrer gorsel kapisi.

NEDEN: urun ekleme/backfill hattinda "mukerrer URL 0" olcusu yalniz STRING esitligi
olcer, GORSEL mukerrerligini DEGIL. Backfill'de bir urune eklenen aday gorsel, ayni
urunde ZATEN YAYINDA olan bir gorselin ALGISAL IKIZI olabilir (yeniden sikistirilmis,
hafif kirpilmis, parlaklik oynamis ayni foto) -> string farkli, GORSEL ayni.
Bu kapi dHash (256-bit) + hamming mesafesi ile o ikizleri yakalar.

Yontem MaCiT'in salt-okunur risk olcumundeki dHash ile AYNI (16x16 -> 256 bit,
komsu-piksel parlaklik farki). MaCiT betigi (pruvo-jenerator/olcum/gorsel_kapisi.py)
repoda commit'li DEGIL; bu betik BAGIMSIZ uygulanmistir. Iki betik ileride birlestirilebilir.

ESIK: hamming <= 12 (256 bit uzerinde). Kaynak: MaCiT'in kusur raporu (ARAC-KUSURLARI-KRAL.md
madde d) 73 algisal ikizi "hamming<=12" ile olctu; kapi ayni esikle hizali. (MaCiT'in
mukerrer_kontrol.py risk-probe'u daha SIKI 6 kullanir; kapi RAPORDAKI olcumle -- eklenen
ikizleri elemek -- 12 secer, boylece raporlanan tum ikizler yakalanir.)

KUTUPHANE: goruntu decode icin Pillow (PIL) kullanir. Site kodunda "harici lib yok"
kurali gecerlidir; tools/*.py icin GECERLI DEGIL (araclar zaten sips/PIL kullanir).
PIL yoksa kapi FAIL-OPEN calisir (hicbir seyi elemez) ama GORUNUR uyari basar -- yeni
bir kapi mevcut akisi SESSIZ bozmamali; olcum yapilamiyorsa bunu bagirir.

Kullanim (CLI):
  python3 tools/gorsel_mukerrer_kapisi.py --aday a1.jpg a2.jpg --mevcut y1.jpg y2.jpg
  python3 tools/gorsel_mukerrer_kapisi.py --aday-dizin .thing-cache/12345 --mevcut y1.jpg
Cikis kodu: 0 = mukerrer yok, 1 = mukerrer bulundu, 2 = PIL yok (olculemedi).

Kullanim (modul):
  from gorsel_mukerrer_kapisi import filtrele, mukerrer_mi, dhash, DHASH_ESIK
  sonuc = filtrele(aday_yollar, mevcut_yollar)   # {'gecen','elenen','olculemeyen'}
"""
import argparse
import os
import sys

try:
    from PIL import Image
    PIL_VAR = True
except ImportError:
    PIL_VAR = False

HS = 16               # 16x16 -> 256 bitlik dHash (8x8'e gore cok daha ayirt edici)
DHASH_ESIK = 12       # hamming <= 12 / 256 bit = algisal IKIZ (bkz ust not)


def dhash(path, hs=HS):
    """Bir gorselin 256-bit dHash'ini (int) dondurur; decode edilemezse None.

    Grayscale + (hs+1)x hs yeniden boyutlandirma + yatay komsu-piksel parlaklik farki.
    Kutuphaneden bagimsiz saf hesap; yalniz decode icin PIL gerekir."""
    if not PIL_VAR:
        return None
    try:
        im = Image.open(path).convert("L").resize((hs + 1, hs))
    except Exception:
        return None
    px = list(im.getdata())
    bits = 0
    n = 0
    for r in range(hs):
        for c in range(hs):
            left = px[r * (hs + 1) + c]
            right = px[r * (hs + 1) + c + 1]
            bits |= (1 if left > right else 0) << n
            n += 1
    return bits


def hamming(a, b):
    """Iki dHash arasindaki bit farki sayisi."""
    return bin(a ^ b).count("1")


def mukerrer_mi(aday_hash, ref_hashler, esik=DHASH_ESIK):
    """aday_hash, ref_hashler icindeki herhangi biriyle hamming<=esik ise (True, en_yakin_hamming, idx).
    Degilse (False, en_yakin_hamming|None, None). ref bos ise (False, None, None)."""
    en_iyi = None
    en_idx = None
    for i, h in enumerate(ref_hashler):
        if h is None:
            continue
        d = hamming(aday_hash, h)
        if en_iyi is None or d < en_iyi:
            en_iyi = d
            en_idx = i
    if en_iyi is not None and en_iyi <= esik:
        return True, en_iyi, en_idx
    return False, en_iyi, None


def filtrele(aday_yollar, mevcut_yollar=(), esik=DHASH_ESIK):
    """Aday gorselleri hem MEVCUT (yayindaki) gorsellerle hem BIRBIRLERIYLE karsilastirir.

    Bir aday, mevcut bir gorselin ya da onceden KABUL edilmis bir adayin algisal ikizi ise
    ELENIR. Boylece hem "yayinda zaten var" (backfill defect d) hem "ayni foto iki kez secildi"
    (birebir ikiz) yakalanir.

    PIL yoksa FAIL-OPEN: tum adaylar 'gecen'e girer, 'pil_yok' bayragi True olur.

    Doner: {
      'gecen':   [yol, ...],                                   # eklenecek gorseller
      'elenen':  [{'aday':yol,'ikiz':yol,'hamming':d,'kaynak':'yayin'|'aday'}, ...],
      'olculemeyen': [yol, ...],   # decode edilemeyen adaylar (FAIL-OPEN: gecen'e de eklenir)
      'pil_yok': bool,
    }
    """
    if not PIL_VAR:
        return {"gecen": list(aday_yollar), "elenen": [], "olculemeyen": [],
                "pil_yok": True}

    mevcut_h = [(y, dhash(y)) for y in mevcut_yollar]
    gecen = []
    elenen = []
    olculemeyen = []
    kabul_h = []          # bu partide KABUL edilmis adaylarin (yol, hash)'i (running set)

    for y in aday_yollar:
        h = dhash(y)
        if h is None:
            # Decode edilemeyen aday: gateleyemeyiz -> FAIL-OPEN (gecir) ama isaretle.
            olculemeyen.append(y)
            gecen.append(y)
            continue
        # Once yayindaki gorseller (kaynak='yayin'), sonra bu partide kabul edilenler (kaynak='aday').
        ikiz_yol = None
        ikiz_d = None
        kaynak = None
        for ry, rh in mevcut_h:
            if rh is None:
                continue
            d = hamming(h, rh)
            if ikiz_d is None or d < ikiz_d:
                ikiz_d, ikiz_yol, kaynak = d, ry, "yayin"
        for ky, kh in kabul_h:
            d = hamming(h, kh)
            if ikiz_d is None or d < ikiz_d:
                ikiz_d, ikiz_yol, kaynak = d, ky, "aday"
        if ikiz_d is not None and ikiz_d <= esik:
            elenen.append({"aday": y, "ikiz": ikiz_yol, "hamming": ikiz_d, "kaynak": kaynak})
        else:
            gecen.append(y)
            kabul_h.append((y, h))

    return {"gecen": gecen, "elenen": elenen, "olculemeyen": olculemeyen, "pil_yok": False}


def secili_temizle(cache_dir, secili_adlar, mevcut_yollar=(), esik=DHASH_ESIK):
    """Ekleme hatti icin ince sarmalayici: cache dizinindeki secili DOSYA ADLARINI
    (gN.jpg) algisal mukerrerlerden arindirir. Sirayi KORUR. Doner (temiz_adlar, sonuc).

    mevcut_yollar: urunun YAYINDAKI gorsellerinin YEREL kopyalari (varsa) -> backfill'de
    aday, yayindaki ile karsilastirilir. Yeni urunde bos gecilir (yalniz aday-ici dedup).
    """
    yollar = [os.path.join(cache_dir, a) for a in secili_adlar]
    sonuc = filtrele(yollar, mevcut_yollar, esik)
    gecen_set = set(sonuc["gecen"])
    temiz = [a for a in secili_adlar if os.path.join(cache_dir, a) in gecen_set]
    return temiz, sonuc


def _topla_adaylar(args):
    adaylar = list(args.aday or [])
    if args.aday_dizin:
        d = args.aday_dizin
        for a in sorted(os.listdir(d)):
            if a.lower().endswith((".jpg", ".jpeg", ".png")):
                adaylar.append(os.path.join(d, a))
    return adaylar


def main():
    ap = argparse.ArgumentParser(description="Algisal mukerrer gorsel kapisi (dHash + hamming)")
    ap.add_argument("--aday", nargs="*", help="aday gorsel yollari")
    ap.add_argument("--aday-dizin", help="icindeki tum jpg/png'leri aday al")
    ap.add_argument("--mevcut", nargs="*", default=[], help="urunun YAYINDAKI gorselleri (yerel kopya)")
    ap.add_argument("--esik", type=int, default=DHASH_ESIK, help="hamming esigi (varsayilan %d)" % DHASH_ESIK)
    args = ap.parse_args()

    if not PIL_VAR:
        print("PIL YOK -> algisal mukerrer olcumu YAPILAMADI (FAIL-OPEN).", file=sys.stderr)
        return 2

    adaylar = _topla_adaylar(args)
    if not adaylar:
        print("aday gorsel yok (--aday veya --aday-dizin ver).", file=sys.stderr)
        return 2

    sonuc = filtrele(adaylar, args.mevcut, args.esik)
    print("aday: %d | mevcut(yayin): %d | esik: hamming<=%d / %d bit"
          % (len(adaylar), len(args.mevcut), args.esik, HS * HS))
    print("GECEN : %d" % len(sonuc["gecen"]))
    print("ELENEN: %d (algisal ikiz)" % len(sonuc["elenen"]))
    for e in sonuc["elenen"]:
        print("  ELE %s ~ %s (%s, hamming=%d)"
              % (os.path.basename(e["aday"]), os.path.basename(e["ikiz"]), e["kaynak"], e["hamming"]))
    if sonuc["olculemeyen"]:
        print("OLCULEMEYEN (decode yok, FAIL-OPEN gecti): %d" % len(sonuc["olculemeyen"]))
    return 1 if sonuc["elenen"] else 0


if __name__ == "__main__":
    sys.exit(main())
