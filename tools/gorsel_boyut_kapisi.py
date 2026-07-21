#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gorsel_boyut_kapisi.py — ASGARI GORSEL BOYUTU kapisi (urun EKLEME hattinda).

NEDEN VAR (olculmus gercek vaka): urun id=alfa-romeo-166-yak-t-kapa-ask-s icin R2'ye
yuklenen kapak gorseli 1000x88 -> Google Merchant "resim cok kucuk" reddi. Bugun boyle
bir kapi YOK: tools/gorsel_mukerrer_kapisi.py yalniz ALGISAL MUKERRERLIK olcer, boyut
bakmaz. Ince serit / banner kirpigi bir gorsel R2'ye cikip feed'e girebiliyor.

🔴 YER SECIMI — CI'YA/BUILD'E KONMAZ: 7769 gorseli her build'de agdan cekmek kabul
edilemez (feed sadece URL tasir, dosya yereldeyken olculmelidir). Kapi, gorselin HENUZ
YERELDE oldugu tek yere konur: ekleme/yukleme hatti (urun-ekle.py / printables-ekle.py /
makerworld-ekle.py), R2 upload'dan HEMEN ONCE, gorsel_mukerrer_kapisi cagrisinin yanina.

ESIKLER:
  * ASGARI = 100 px — her iki kenar >= 100 degilse gorsel ELENIR (Merchant'in kesin alt
    siniri; altindaki gorsel zaten reddedilir, R2'ye yuklemek bos maliyet).
  * UYARI_KENAR = 800 px — kisa kenar 800'un altindaysa UYARI basilir ama ELENMEZ
    (Merchant 'onerilen' esigi; katalogda cok sayida 600-800 kenarli mesru gorsel var).

🔴 FAIL-CLOSED DEGIL, FAIL-LOUD: boyut OKUNAMAZSA gorsel ELENMEZ; 'olculemeyen'e yazilir
ve stderr'e GORUNUR uyari basilir. Yeni bir kapi MaCiT'in ekleme akisini SESSIZCE
oldurmemeli; olcemedigimiz seyi reddetmek de 'olctuk' demek olurdu.

KUTUPHANE: harici bagimlilik EKLENMEZ. Boyut, saf Python ile dosya BASLIKLARINDAN okunur
(JPEG SOFn / PNG IHDR / WebP VP8-VP8L-VP8X / GIF). Yalniz basliktan okunamayan bir format
gelirse, kardes modulun ZATEN kullandigi PIL'e (bkz gorsel_mukerrer_kapisi.py) yedek olarak
dusulur — YENI bir cozum yazilmaz, var olan kullanilir. PIL yoksa sonuc 'olculemeyen'dir.

Kullanim (CLI):
  python3 tools/gorsel_boyut_kapisi.py --gorsel a.jpg b.png
  python3 tools/gorsel_boyut_kapisi.py --dizin .thing-cache/12345
Cikis kodu: 0 = elenen yok (uyari olabilir), 1 = en az bir gorsel ASGARI'nin altinda,
            2 = kullanim hatasi.

Kullanim (modul):
  from gorsel_boyut_kapisi import boyut, filtrele, secili_ele, ASGARI
"""
import argparse
import os
import struct
import sys

ASGARI = 100          # px — her iki kenar; altinda ELENIR (Merchant kesin alt siniri)
UYARI_KENAR = 800     # px — kisa kenar; altinda UYARI (elenmez)


# ---------------------------------------------------------------- baslik okuyucular
def _png(b):
    if len(b) >= 24 and b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR":
        w, h = struct.unpack(">II", b[16:24])
        return int(w), int(h)
    return None


def _gif(b):
    if len(b) >= 10 and b[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", b[6:10])
        return int(w), int(h)
    return None


def _webp(b):
    # Uzunluk kontrolu DAL BASINA yapilir: VP8L basligi 25 bayta sigar, VP8/VP8X 30 ister.
    # (Tek bir 'len(b) < 30' kapisi kucuk VP8L dosyalarini sessizce OLCULEMEZ yapardi.)
    if len(b) < 16 or b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        return None
    tur = b[12:16]
    if tur == b"VP8X" and len(b) >= 30:      # genisletilmis: tuval boyutu (24 bit, -1)
        w = b[24] | (b[25] << 8) | (b[26] << 16)
        h = b[27] | (b[28] << 8) | (b[29] << 16)
        return w + 1, h + 1
    if tur == b"VP8L" and len(b) >= 25:      # kayipsiz: 14+14 bit, -1
        if b[20] != 0x2F:
            return None
        bits = struct.unpack("<I", b[21:25])[0]
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if tur == b"VP8 " and len(b) >= 30:      # kayipli: senkron kodu 9d 01 2a
        if b[23:26] != b"\x9d\x01\x2a":
            return None
        w, h = struct.unpack("<HH", b[26:30])
        return w & 0x3FFF, h & 0x3FFF
    return None


def _jpeg(b):
    """JPEG SOFn segmentinden (C0-CF; C4=DHT, C8=JPG, CC=DAC HARIC) yukseklik/genislik."""
    if len(b) < 4 or b[0] != 0xFF or b[1] != 0xD8:
        return None
    i = 2
    n = len(b)
    while i + 3 < n:
        if b[i] != 0xFF:                     # senkron kaybi -> guvenli cikis
            i += 1
            continue
        m = b[i + 1]
        if m == 0xFF:                        # dolgu baytlari
            i += 1
            continue
        if m in (0x01,) or 0xD0 <= m <= 0xD9:   # uzunluksuz (TEM/RSTn/SOI/EOI)
            i += 2
            continue
        if i + 3 >= n:
            return None
        seg = struct.unpack(">H", b[i + 2:i + 4])[0]
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            if i + 9 > n:
                return None
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return int(w), int(h)
        if m == 0xDA:                        # SOS -> goruntu verisi basladi, SOF yok
            return None
        if seg < 2:
            return None
        i += 2 + seg
    return None


_OKUYUCULAR = (_png, _gif, _webp, _jpeg)


def _pil_boyut(yol):
    """Yedek yol: kardes modulun ZATEN kullandigi PIL (yeni bagimlilik DEGIL)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(yol) as im:
            return int(im.size[0]), int(im.size[1])
    except Exception:
        return None


def boyut(yol, bas_bayt=65536):
    """(genislik, yukseklik) ya da OLCULEMEDIYSE None.

    Once dosya BASLIGI okunur (saf Python, harici lib yok); baslik cozulemezse PIL'e
    dusulur. Dosyanin tamami OKUNMAZ (varsayilan ilk 64 KiB yeterli — SOFn baslikta)."""
    try:
        with open(yol, "rb") as f:
            b = f.read(bas_bayt)
    except OSError:
        return None
    for oku in _OKUYUCULAR:
        try:
            r = oku(b)
        except (struct.error, IndexError):
            r = None
        if r and r[0] > 0 and r[1] > 0:
            return r
    return _pil_boyut(yol)


# ---------------------------------------------------------------- kapi
def filtrele(yollar, asgari=ASGARI, uyari_kenar=UYARI_KENAR):
    """Doner: {
        'gecen':       [yol, ...],
        'elenen':      [{'yol','en','boy','sebep'}, ...],   # kenar < asgari
        'uyari':       [{'yol','en','boy'}, ...],           # kisa kenar < uyari_kenar (gecti)
        'olculemeyen': [yol, ...],                          # FAIL-LOUD: gecer + uyari basilir
      }"""
    gecen, elenen, uyari, olculemeyen = [], [], [], []
    for y in yollar:
        wh = boyut(y)
        if wh is None:
            olculemeyen.append(y)
            gecen.append(y)                  # FAIL-LOUD: olcemedigimizi REDDETMEYIZ
            continue
        w, h = wh
        if w < asgari or h < asgari:
            elenen.append({"yol": y, "en": w, "boy": h,
                           "sebep": "kenar < %d px (Merchant asgari)" % asgari})
            continue
        if min(w, h) < uyari_kenar:
            uyari.append({"yol": y, "en": w, "boy": h})
        gecen.append(y)
    return {"gecen": gecen, "elenen": elenen, "uyari": uyari, "olculemeyen": olculemeyen}


def secili_ele(cache_dir, secili_adlar, asgari=ASGARI, uyari_kenar=UYARI_KENAR):
    """Ekleme hatti icin ince sarmalayici (gorsel_mukerrer_kapisi.secili_temizle ile AYNI
    imza deseni): cache dizinindeki secili DOSYA ADLARINDAN cok kucuk olanlari duser,
    SIRAYI KORUR. Doner (temiz_adlar, sonuc).

    Elenen/olculemeyen durumlar stderr'e GORUNUR sekilde basilir (FAIL-LOUD)."""
    yollar = [os.path.join(cache_dir, a) for a in secili_adlar]
    sonuc = filtrele(yollar, asgari, uyari_kenar)
    gecen = set(sonuc["gecen"])
    temiz = [a for a in secili_adlar if os.path.join(cache_dir, a) in gecen]
    for e in sonuc["elenen"]:
        print("GORSEL BOYUT KAPISI: ELENDI %s (%dx%d) — %s"
              % (os.path.basename(e["yol"]), e["en"], e["boy"], e["sebep"]), file=sys.stderr)
    for u in sonuc["uyari"]:
        print("GORSEL BOYUT KAPISI: UYARI %s (%dx%d) — kisa kenar < %d px (Merchant onerisi)"
              % (os.path.basename(u["yol"]), u["en"], u["boy"], uyari_kenar), file=sys.stderr)
    for y in sonuc["olculemeyen"]:
        print("GORSEL BOYUT KAPISI: OLCULEMEDI %s — boyut okunamadi, gorsel GECIRILDI "
              "(fail-loud)" % os.path.basename(y), file=sys.stderr)
    return temiz, sonuc


def main():
    ap = argparse.ArgumentParser(description="Asgari gorsel boyutu kapisi (ekleme hatti)")
    ap.add_argument("--gorsel", nargs="*", help="gorsel yollari")
    ap.add_argument("--dizin", help="icindeki tum jpg/png/webp/gif'leri al")
    ap.add_argument("--asgari", type=int, default=ASGARI)
    ap.add_argument("--uyari-kenar", type=int, default=UYARI_KENAR)
    args = ap.parse_args()

    yollar = list(args.gorsel or [])
    if args.dizin:
        for a in sorted(os.listdir(args.dizin)):
            if a.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                yollar.append(os.path.join(args.dizin, a))
    if not yollar:
        print("gorsel yok (--gorsel ya da --dizin ver).", file=sys.stderr)
        return 2

    s = filtrele(yollar, args.asgari, args.uyari_kenar)
    print("gorsel: %d | asgari: %dx%d | uyari kenari: %d"
          % (len(yollar), args.asgari, args.asgari, args.uyari_kenar))
    print("GECEN : %d" % len(s["gecen"]))
    print("ELENEN: %d" % len(s["elenen"]))
    for e in s["elenen"]:
        print("  ELE %s (%dx%d) — %s" % (os.path.basename(e["yol"]), e["en"], e["boy"], e["sebep"]))
    for u in s["uyari"]:
        print("  UYARI %s (%dx%d) kisa kenar < %d" % (os.path.basename(u["yol"]), u["en"], u["boy"], args.uyari_kenar))
    if s["olculemeyen"]:
        print("OLCULEMEYEN (fail-loud, gecti): %d" % len(s["olculemeyen"]))
    return 1 if s["elenen"] else 0


if __name__ == "__main__":
    sys.exit(main())
