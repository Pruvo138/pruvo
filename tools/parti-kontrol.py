#!/usr/bin/env python3
"""parti-kontrol.py — toplu urun ekleme PARTISININ kabul testi.

PARTI = working-tree urunler.json'da olup `git show HEAD:urunler.json` ciktisinda
OLMAYAN id'ler (yeni stage'lenmis urunler). Bu arac SADECE partiyi denetler;
HEAD'de zaten var olan urunlere dokunmaz (onlar urunler-guard.py'nin isi).

Her yeni urun icin kontroller:
  1. id kebab-case ve bos degil
  2. baslik bos degil
  3. kategori gecerli kategori listesinde
  4. marka alani liste tipinde
  5. gorseller >= 1 eleman ve hepsi https://media.pruvo3d.com/ ile baslar
  6. aciklamada "3d bask" gecmez (buyuk/kucuk harf duyarsiz)
  7. fiyat: parametrik=true ise BOS; degilse "<sayi> TL" biciminde
  8. aciklamada "mm" iceren bir olcu ifadesi (ISTISNA: .urun-kaynaklari.json'da
     tur=="satin-alma" olan urunlerde olcu aranmaz)
  9. lisans alani VARSA dict ve icindeki "tur" bos degil

Bulgu varsa her biri "SORUN <id>: <aciklama>" satiriyla yazilir, cikis 1.
Temizse "parti temiz: N yeni urun kontrol edildi", cikis 0.
Yeni urun yoksa "parti yok: working tree = HEAD", cikis 0.

--test: gercek dosyalara dokunmadan her kontrolun yakalama+gecme yolunu sinar.
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAKLAR = os.path.join(ROOT, ".urun-kaynaklari.json")

KATEGORILER = {
    "Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev", "Ofis",
    "Elektronik", "Kamera", "Bahce", "Bahçe", "Dekorasyon", "Oyun/Hobi",
}
# NOT: "Bahce" ve "Bahçe" birlikte tutuluyor cunku canli kategori adi "Bahçe"
# (Turkce), ancak ASCII yazilmis veriye de tolerans; asil dogrulama Turkce ad.

MEDYA_ONEK = "https://media.pruvo3d.com/"

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FIYAT_RE = re.compile(r"^\d[\d.,]* TL$")
_OLCU_RE = re.compile(r"\d[\d\s.,×xX*+-]*mm\b", re.IGNORECASE)


def _git(*args):
    """git -C ROOT <args> -> (rc, stdout_bytes). Hata yutulur."""
    try:
        p = subprocess.run(["git", "-C", ROOT, *args], capture_output=True)
        return p.returncode, p.stdout
    except Exception:
        return 1, b""


def _head_ids():
    """HEAD:urunler.json'daki id kumesi; okunamazsa None (parti belirlenemez)."""
    rc, out = _git("show", "HEAD:urunler.json")
    if rc != 0:
        return None
    try:
        urunler = json.loads(out.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(urunler, list):
        return None
    return {
        u.get("id") for u in urunler
        if isinstance(u, dict) and u.get("id") is not None
    }


def _kaynaklari_oku(path):
    """Kaynak haritasi yoksa veya bozuksa sessizce bos sozluk dondurur."""
    try:
        with open(path, encoding="utf-8") as f:
            kaynaklar = json.load(f)
    except (OSError, ValueError):
        return {}
    return kaynaklar if isinstance(kaynaklar, dict) else {}


def _satin_alma_mi(kayit):
    """Kaynak kaydi tur=="satin-alma" olan bir dict ise True.

    Kayit str/dict/list bicimlerinde olabilir; SADECE dict'te "tur" anahtarina
    bakilir, diger bicimlerde olcu istisnasi UYGULANMAZ.
    """
    return isinstance(kayit, dict) and kayit.get("tur") == "satin-alma"


def _denetle_urun(urun, gosterim_id, kaynaklar):
    """Tek bir yeni urun icin bulgu (aciklama) listesi dondurur."""
    bulgular = []

    # 1. id kebab-case ve bos degil
    urun_id = urun.get("id")
    if not isinstance(urun_id, str) or not _KEBAB_RE.match(urun_id):
        bulgular.append("id kebab-case degil veya bos: %r" % (urun_id,))

    # 2. baslik bos degil
    baslik = urun.get("baslik")
    if not isinstance(baslik, str) or not baslik.strip():
        bulgular.append("baslik bos")

    # 3. kategori gecerli
    kategori = urun.get("kategori")
    if kategori not in KATEGORILER:
        bulgular.append("kategori gecersiz: %r" % (kategori,))

    # 4. marka liste tipinde
    if not isinstance(urun.get("marka"), list):
        bulgular.append("marka liste tipinde degil")

    # 5. gorseller >= 1 ve hepsi media.pruvo3d.com ile baslar
    gorseller = urun.get("gorseller")
    if not isinstance(gorseller, list) or not gorseller:
        bulgular.append("gorseller bos veya liste degil")
    else:
        for g in gorseller:
            if not isinstance(g, str) or not g.startswith(MEDYA_ONEK):
                bulgular.append("gorsel media.pruvo3d.com ile baslamiyor: %r" % (g,))

    # 6. aciklamada "3d bask" gecmez
    aciklama = urun.get("aciklama")
    aciklama_str = aciklama if isinstance(aciklama, str) else ""
    if "3d bask" in aciklama_str.lower():
        bulgular.append("aciklamada '3d bask' geciyor")

    # 7. fiyat kurali
    parametrik = bool(urun.get("parametrik"))
    fiyat = urun.get("fiyat", "")
    fiyat_str = fiyat if isinstance(fiyat, str) else str(fiyat)
    if parametrik:
        if fiyat_str.strip():
            bulgular.append("parametrik urunde fiyat bos degil: %r" % (fiyat,))
    else:
        if not _FIYAT_RE.match(fiyat_str):
            bulgular.append("fiyat '<sayi> TL' biciminde degil: %r" % (fiyat,))

    # 8. olcu (mm) ifadesi — satin-alma urunlerinde aranmaz
    if not _satin_alma_mi(kaynaklar.get(gosterim_id)):
        if not _OLCU_RE.search(aciklama_str):
            bulgular.append("aciklamada olcu (mm) ifadesi yok")

    # 9. lisans VARSA dict ve tur dolu
    if "lisans" in urun:
        lisans = urun.get("lisans")
        if not isinstance(lisans, dict):
            bulgular.append("lisans dict degil")
        else:
            tur = lisans.get("tur")
            if not isinstance(tur, str) or not tur.strip():
                bulgular.append("lisans.tur bos")

    return bulgular


def _yeni_urunler(urunler, head_ids):
    """(gosterim_id, urun) ciftlerinden parti; HEAD'de olmayan id'ler."""
    parti = []
    for sira, urun in enumerate(urunler):
        if not isinstance(urun, dict):
            continue
        urun_id = urun.get("id")
        if urun_id in head_ids:
            continue  # HEAD'de var -> mevcut urun, parti disi (guard'in isi)
        gosterim_id = urun_id if isinstance(urun_id, str) and urun_id else "#%d" % (sira + 1)
        parti.append((gosterim_id, urun))
    return parti


def _parti_denetle(urunler, head_ids, kaynaklar):
    """Parti bulgularini [(gosterim_id, aciklama), ...] olarak dondurur; ayrica
    (bulgular, parti_boyu). head_ids None ise parti belirlenemez -> (None, None)."""
    if head_ids is None:
        return None, None
    parti = _yeni_urunler(urunler, head_ids)
    bulgular = []
    for gosterim_id, urun in parti:
        for aciklama in _denetle_urun(urun, gosterim_id, kaynaklar):
            bulgular.append((gosterim_id, aciklama))
    return bulgular, len(parti)


# ---------------------------------------------------------------------------
# --test: her kontrolun yakalama (fail) + gecme (pass) yolunu bellek icinde sina
# ---------------------------------------------------------------------------

def _gecerli_urun():
    """Tum kontrollerden gecen ornek urun (sablon)."""
    return {
        "id": "ornek-parca-braketi",
        "kategori": "Otomobil",
        "marka": ["Audi"],
        "baslik": "Ornek Parca Braketi",
        "aciklama": "Dayanikli braket. Yaklasik dis olculer: 40 x 25 x 10 mm.",
        "fiyat": "850 TL",
        "gorseller": ["https://media.pruvo3d.com/urunler/ornek-1.jpg"],
    }


def _oz_sinama():
    kaynaklar = {}  # varsayilan: bos kaynak haritasi

    def bulgu(urun, kaynaklar=kaynaklar, gid=None):
        u = dict(_gecerli_urun())
        u.update(urun)
        gosterim = gid if gid is not None else u.get("id") or "#1"
        return _denetle_urun(u, gosterim, kaynaklar)

    def yakalar(desen, **degisiklik):
        """degisiklik uygulaninca 'desen' iceren bir bulgu cikmali."""
        return any(desen in b for b in bulgu(degisiklik))

    def temiz(**degisiklik):
        """degisiklik uygulaninca hic bulgu cikmamali."""
        return not bulgu(degisiklik)

    kontroller = [
        # sablonun kendisi temiz olmali
        ("sablon temiz", temiz()),

        # 1. id
        ("id yakala (bos)", yakalar("id kebab-case", id="")),
        ("id yakala (bosluk)", yakalar("id kebab-case", id="Ornek Parca")),
        ("id yakala (buyuk harf)", yakalar("id kebab-case", id="Ornek-Parca")),
        ("id yakala (bitis tire)", yakalar("id kebab-case", id="ornek-parca-")),
        ("id gec", temiz(id="ornek-parca-2")),

        # 2. baslik
        ("baslik yakala (bos)", yakalar("baslik bos", baslik="")),
        ("baslik yakala (bosluk)", yakalar("baslik bos", baslik="   ")),
        ("baslik gec", temiz(baslik="Bir Baslik")),

        # 3. kategori
        ("kategori yakala", yakalar("kategori gecersiz", kategori="Uzay")),
        ("kategori yakala (yok)", yakalar("kategori gecersiz", kategori=None)),
        ("kategori gec", temiz(kategori="Tamirat")),

        # 4. marka
        ("marka yakala (str)", yakalar("marka liste", marka="Audi")),
        ("marka yakala (yok)", yakalar("marka liste", marka=None)),
        ("marka gec (bos liste)", temiz(marka=[])),

        # 5. gorseller
        ("gorsel yakala (bos)", yakalar("gorseller bos", gorseller=[])),
        ("gorsel yakala (liste degil)", yakalar("gorseller bos", gorseller="x")),
        ("gorsel yakala (yanlis host)",
         yakalar("baslamiyor", gorseller=["https://example.com/x.jpg"])),
        ("gorsel gec (coklu)", temiz(gorseller=[
            "https://media.pruvo3d.com/urunler/a-1.jpg",
            "https://media.pruvo3d.com/urunler/a-2.jpg",
        ])),

        # 6. 3d bask
        ("3dbask yakala", yakalar(
            "3d bask", aciklama="Bu urun 3D baski ile uretilir. 10 mm.")),
        ("3dbask yakala (kucuk)", yakalar(
            "3d bask", aciklama="3d baski parcasi. 10 mm.")),
        ("3dbask gec", temiz(aciklama="Ozel uretim parca. 10 mm.")),

        # 7. fiyat
        ("fiyat yakala (bos)", yakalar("<sayi> TL", fiyat="")),
        ("fiyat yakala (bicimsiz)", yakalar("<sayi> TL", fiyat="ucretsiz")),
        ("fiyat yakala (eksik TL)", yakalar("<sayi> TL", fiyat="850")),
        ("fiyat gec", temiz(fiyat="1.250 TL")),
        ("parametrik fiyat yakala",
         yakalar("parametrik urunde fiyat", parametrik=True, fiyat="500 TL")),
        ("parametrik fiyat gec", temiz(parametrik=True, fiyat="")),

        # 8. olcu (mm)
        ("olcu yakala", yakalar(
            "olcu (mm)", aciklama="Guzel bir parca, olcusuz aciklama.")),
        ("olcu gec", temiz(aciklama="Boyut: 12 x 8 x 5 mm dayanikli.")),

        # 9. lisans
        ("lisans yakala (dict degil)",
         yakalar("lisans dict degil", lisans="CC BY 4.0")),
        ("lisans yakala (tur bos)",
         yakalar("lisans.tur bos", lisans={"tasarimci": "x", "tur": ""})),
        ("lisans yakala (tur yok)",
         yakalar("lisans.tur bos", lisans={"tasarimci": "x"})),
        ("lisans gec", temiz(lisans={"tasarimci": "x", "tur": "CC BY 4.0"})),
        ("lisans yok gec", temiz()),  # lisans alani hic yok -> sorun degil
    ]

    # 8b. satin-alma istisnasi: olcu yoksa bile kaynak tur=satin-alma ise gecer
    olcusuz = {"aciklama": "Hazir alinmis parca, olcu satiri yok."}
    kayit_satin = {"olcusuz-urun": {"tur": "satin-alma", "link": "http://x"}}
    kontroller.append((
        "satin-alma istisnasi gec",
        not any("olcu (mm)" in b for b in bulgu(
            olcusuz, kaynaklar=kayit_satin, gid="olcusuz-urun")),
    ))
    # ayni urun satin-alma DEGILSE olcu yoklugu yakalanmali (istisna dar)
    kayit_cc = {"olcusuz-urun": {"tur": "ucretsiz-cc", "link": "http://x"}}
    kontroller.append((
        "satin-alma disi olcu yakala",
        any("olcu (mm)" in b for b in bulgu(
            olcusuz, kaynaklar=kayit_cc, gid="olcusuz-urun")),
    ))
    # kayit str/list bicimindeyse istisna UYGULANMAZ -> olcu yoklugu yakalanir
    kayit_str = {"olcusuz-urun": "https://ornek.test/model"}
    kontroller.append((
        "str kayit istisnasiz",
        any("olcu (mm)" in b for b in bulgu(
            olcusuz, kaynaklar=kayit_str, gid="olcusuz-urun")),
    ))

    # kaynak dosyasi yok/bozuk -> sessizce bos harita, cokme yok
    with_bad = _kaynaklari_oku(os.path.join(ROOT, "yok-boyle-dosya-parti.json"))
    kontroller.append(("kaynak dosyasi yok -> bos", with_bad == {}))

    # parti belirleme: HEAD'de olmayan id'ler yeni sayilir
    urunler = [
        {"id": "eski-urun", "baslik": "Eski"},
        _gecerli_urun(),
    ]
    head = {"eski-urun"}
    bulgular, boyut = _parti_denetle(urunler, head, kaynaklar)
    kontroller.append(("parti sadece yeni urun", boyut == 1 and bulgular == []))

    # yeni urun yoksa parti bos
    _, boyut_bos = _parti_denetle([{"id": "eski-urun"}], {"eski-urun"}, kaynaklar)
    kontroller.append(("parti bos", boyut_bos == 0))

    # HEAD okunamazsa (None) parti belirlenemez
    bnone, cnone = _parti_denetle(urunler, None, kaynaklar)
    kontroller.append(("head yok -> belirlenemez", bnone is None and cnone is None))

    # partide bulgu varsa (gid, aciklama) olarak raporlanir
    kotu = dict(_gecerli_urun())
    kotu["id"] = "yeni-kotu"
    kotu["kategori"] = "Uzay"
    b2, _ = _parti_denetle([{"id": "eski-urun"}, kotu], {"eski-urun"}, kaynaklar)
    kontroller.append((
        "partide bulgu raporlanir",
        any(gid == "yeni-kotu" and "kategori" in msg for gid, msg in (b2 or [])),
    ))

    hatalar = [ad for ad, gecti in kontroller if not gecti]
    if hatalar:
        for ad in hatalar:
            print("TEST KALDI: %s" % ad, file=sys.stderr)
        return 1
    print("TEST GECTI")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true",
                    help="bellek ici oz-sinamayi calistir (gercek dosyaya dokunmaz)")
    args = ap.parse_args()

    if args.test:
        return _oz_sinama()

    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
    except (OSError, ValueError) as e:
        print("HATA: urunler.json okunamadi: %s" % e, file=sys.stderr)
        return 2
    if not isinstance(urunler, list):
        print("HATA: urunler.json bir dizi degil.", file=sys.stderr)
        return 2

    head_ids = _head_ids()
    if head_ids is None:
        print("parti belirlenemedi: HEAD:urunler.json okunamadi")
        return 0

    kaynaklar = _kaynaklari_oku(KAYNAKLAR)
    bulgular, boyut = _parti_denetle(urunler, head_ids, kaynaklar)

    if boyut == 0:
        print("parti yok: working tree = HEAD")
        return 0

    if bulgular:
        for gosterim_id, aciklama in bulgular:
            print("SORUN %s: %s" % (gosterim_id, aciklama))
        return 1

    print("parti temiz: %d yeni urun kontrol edildi" % boyut)
    return 0


if __name__ == "__main__":
    sys.exit(main())
