#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTAK KUTUDA ILERI SAAT OLCUM KOLU (BaBa 11 Eki 2026 01:03 sinif kapisi) — SALT-OKUNUR.

    python3 tools/kutu-saat-nobeti.py
    python3 tools/kutu-saat-nobeti.py --kutu <yol> --simdi "YYYY-MM-DD HH:MM"

NEDEN VAR (olculdu, 3. tekrar): kutu blok basliklari `## YYYY-MM-DD HH:MM` ya da
`## YYYY-MM-DD HH:Mx` (`01:2x` = 01:20-01:29) bicimindedir. Bazi evler basliga `date`'ten
ILERI saat yaziyor (`date` 01:03 iken TeKiN `01:2x`). Ileri saat kutunun zaman sirasini
bozar, "cevap bekleyen" yasini kucultur ve kapanis/acilis sirasini yalanlar.

KURAL (tolerans YOK): basligin ALT SINIRI (`HH:Mx` -> HH:M0, `HH:MM` -> kendisi)
`--simdi`'den (dakika hassasiyetinde) BUYUKSE baslik ILERI'dir. `(b)` gibi ekler serbest.
Ayrismayan `## ` basligi ILERI SAYILMAZ, `AYRISMAYAN=<n>` olarak ayrica basilir.

KOPYA YOK: cit-duyarli blok basi tanimi `kutu-arsivle.py::blok_baslari`, okuma
`::oku`, frontmatter `::frontmatter_sonu`; yukleyici `kutu-oksuz-nobeti.py::_arsivle_modulu`
deseniyle ayni (bu dosyanin YANINDAN yuklenir). Burada yeniden tanimlanmaz.

CIKTI: ilk satir birebir `KUTU_ILERI_SAAT=<n>` (olculemediyse `OLCULEMEDI`, kutunun
dizini makinede yoksa `MAKINEDE_YOK`; olcemeyince ASLA 0 basilmaz). Her ihlal:
`ILERI ev=<ad> baslik=<tarih saat> simdi=<YYYY-MM-DD HH:MM> fark_dk=<n> satir=<n>`.
Son satir `AYRISMAYAN=<n>`.

CIKIS KODU: 0 temiz / MAKINEDE_YOK · 1 KIRMIZI (n>0) · 2 OLCULEMEDI (dosya yok,
okunamaz, UTF-8 degil, yarim frontmatter, bozuk `--simdi`, sahip arac yuklenemedi).
"""
import datetime
import importlib.util
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))

RC_TEMIZ = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 2

# Ev kumesi: `mimar_kimlik.py` bir ev kumesi TASIMIYOR (yalniz motor/rol); bu yuzden sabit.
EVLER = ("KraL", "MaCiT", "TeKiN", "ArTisT", "BaBa", "OTeLLa", "EyLüL", "FaR")

BASLIK_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) (\d{2}):(\d)([0-9xX])(?!\d)")
SIMDI_BICIM = "%Y-%m-%d %H:%M"
AYRAC = " — "


def _arsivle_modulu():
    """(modul, hata). tools/kutu-arsivle.py'yi bu dosyanin YANINDAN yukler."""
    yol = os.path.join(TOOLS, "kutu-arsivle.py")
    if not os.path.exists(yol):
        return None, "tools/kutu-arsivle.py YOK (blok basi tanimi sahibi)"
    try:
        spec = importlib.util.spec_from_file_location("kutu_arsivle_saat", yol)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    except Exception as e:
        return None, "kutu-arsivle.py yuklenemedi: %s: %s" % (type(e).__name__, e)
    return m, None


def alt_sinir(satir):
    """Basligin alt siniri (datetime) ve gorunen metni; ayrismazsa (None, None)."""
    b = BASLIK_RE.match(satir)
    if not b:
        return None, None
    tarih, saat, onlar, birler = b.groups()
    dakika = int(onlar) * 10 + (0 if birler in "xX" else int(birler))
    try:
        an = datetime.datetime.strptime(tarih, "%Y-%m-%d").replace(
            hour=int(saat), minute=dakika)
    except ValueError:
        return None, None
    return an, "%s %s:%s%s" % (tarih, saat, onlar, birler)


def ev_adi(satir):
    """Ilk ` — `'dan sonraki metinde EN ONCE gecen bilinen ev adi; yoksa BILINMIYOR."""
    i = satir.find(AYRAC)
    if i < 0:
        return "BILINMIYOR"
    kuyruk = satir[i + len(AYRAC):]
    en_iyi = None
    for ev in EVLER:
        j = kuyruk.find(ev)
        if j >= 0 and (en_iyi is None or j < en_iyi[0]):
            en_iyi = (j, ev)
    return en_iyi[1] if en_iyi else "BILINMIYOR"


def olc(kutu_yolu, simdi):
    """{hal, ihlaller, ayrismayan, hata}. hal: TEMIZ|ILERI|OLCULEMEDI|MAKINEDE_YOK."""
    sonuc = {"hal": "OLCULEMEDI", "ihlaller": [], "ayrismayan": None, "hata": None}
    m, hata = _arsivle_modulu()
    if m is None:
        sonuc["hata"] = hata
        return sonuc
    yol = kutu_yolu or m.KUTU_VARSAYILAN
    if not os.path.exists(yol) and not os.path.isdir(os.path.dirname(os.path.abspath(yol))):
        sonuc["hal"] = "MAKINEDE_YOK"
        sonuc["hata"] = "kutu dizini bu makinede yok: %s" % yol
        return sonuc
    metin, hata = m.oku(yol)
    if metin is None:
        sonuc["hata"] = hata
        return sonuc
    satirlar = metin.splitlines(keepends=True)
    fm_son, fm_hata = m.frontmatter_sonu(satirlar)
    if fm_hata:
        sonuc["hata"] = fm_hata
        return sonuc
    ayrismayan = 0
    for idx in m.blok_baslari(satirlar, fm_son):
        satir = satirlar[idx].rstrip("\n")
        an, gorunen = alt_sinir(satir)
        if an is None:
            ayrismayan += 1
            continue
        if an > simdi:
            fark = int((an - simdi).total_seconds() // 60)
            sonuc["ihlaller"].append((ev_adi(satir), gorunen, fark, idx + 1))
    sonuc["ayrismayan"] = ayrismayan
    sonuc["hal"] = "ILERI" if sonuc["ihlaller"] else "TEMIZ"
    return sonuc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    kutu = None
    simdi = datetime.datetime.now().replace(second=0, microsecond=0)
    try:
        if "--kutu" in argv:
            kutu = argv[argv.index("--kutu") + 1]
        if "--simdi" in argv:
            simdi = datetime.datetime.strptime(argv[argv.index("--simdi") + 1], SIMDI_BICIM)
    except (IndexError, ValueError) as e:
        print("KUTU_ILERI_SAAT=OLCULEMEDI")
        print("OLCULEMEDI: arguman bozuk (--kutu <yol> / --simdi \"YYYY-MM-DD HH:MM\"): %s" % e)
        print("AYRISMAYAN=OLCULEMEDI")
        return RC_OLCULEMEDI
    s = olc(kutu, simdi)
    if s["hal"] == "MAKINEDE_YOK":
        print("KUTU_ILERI_SAAT=MAKINEDE_YOK")
        print("MAKINEDE_YOK: %s -> bu makinenin kutusu degil; olculmedi" % s["hata"])
        print("AYRISMAYAN=MAKINEDE_YOK")
        return RC_TEMIZ
    if s["hal"] == "OLCULEMEDI":
        print("KUTU_ILERI_SAAT=OLCULEMEDI")
        print("OLCULEMEDI: %s" % s["hata"])
        print("AYRISMAYAN=OLCULEMEDI")
        return RC_OLCULEMEDI
    print("KUTU_ILERI_SAAT=%d" % len(s["ihlaller"]))
    damga = simdi.strftime(SIMDI_BICIM)
    for ev, gorunen, fark, satir_no in s["ihlaller"]:
        print("ILERI ev=%s baslik=%s simdi=%s fark_dk=%d satir=%d"
              % (ev, gorunen, damga, fark, satir_no))
    print("AYRISMAYAN=%d" % s["ayrismayan"])
    return RC_KIRMIZI if s["ihlaller"] else RC_TEMIZ


if __name__ == "__main__":
    sys.exit(main())
