#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LISANS-IFSA KAPISI — ozgun (bizim tasarimimiz) urunde `lisans`/atif sizintisi = KIRMIZI.

NEDEN VAR (vaka, 9 Eki 2026): bir ozgun-urun partisinde 14 urun public `urunler.json`'a
`lisans` blogu "kendi-tasarim" ile girdi. `tools/build.py::attribution_html()` bu blogu
sayfaya "Licensed under kendi-tasarim." diye basacakti (ic etiket + atif ifsasi). Yayindan
ONCE elle yakalandi; hicbir kapi kirmizi yakmamisti. Kural (CLAUDE.md "PARA EL DEGISTIRDI
MI?"): bizim tasarimimiz / ozgun urun -> ATIF ve `lisans` YOK; yalniz ucretsiz CC BY
kaynakli urun `lisans`+atif TASIR (o SILINMEZ — bu kapi onu ODULLENDIRMEZ, kontrol vakasi).

NEDEN AYRI DOSYA (ata-lisans-kapisi.py'ye kol DEGIL): o kapi turev kaydin ATA ZINCIRINI
platform API'sinden cozer (ag ekseni, kaynak-platform lisansi). Bu kapi YEREL veri
degismezidir (gizli kayit x public kayit x build ciktisi). Ortak mantik KOPYALANMAZ:
  * ozgun ayiricisi  = `tools/denetim-kapisi.py::_ATIF_KENDI_TUR` (TEK kaynak, import)
  * atif ureticisi   = `tools/build.py::attribution_html` (sayfaya basan GERCEK fonksiyon)

AYIRICI (olculdu, 9 Eki 2026): public `urunler.json`'da ozgun urunu ayiran alan YOK (ozgun
kayit ile ucretli-uyelik kaydi ayni alan kumesini tasir). Deterministik ayirici YALNIZ gizli
`.urun-kaynaklari.json` kaydinin `tur` alanidir: `tur in _ATIF_KENDI_TUR` -> ozgun.

KOLLAR:
  (a) ozgun urunde public `lisans` anahtari VAR (bos/null dahil)        -> KIRMIZI
  (b) urunde HERHANGI bir alanda ic etiket dizgesi ("kendi-tasarim" /
      "PRUVO (kendi", buyuk-kucuk duyarsiz). TUM katalog taranir: ic
      etiket hangi urunde gorunse ifsadir (ozgun kumesinin ust kumesi). -> KIRMIZI
  (c) `attribution_html(ozgun_urun)` bos DEGIL                          -> KIRMIZI
  (d) ozgun OLMAYAN urunun `lisans`i bu kapinin ekseninde DEGIL (CC BY urun YESIL kalir).

FAIL-CLOSED (yesil SAYILMAZ, rc 2 = OLCULEMEDI):
  * urunler.json / gizli kayit okunamadi ya da ayristirilamadi
  * urunler.json dizi degil, kayit sozluk degil ya da `id` yok
  * gizli kayit nesne degil
  * ayirici HICBIR urun secmedi (ozgun=0) — ayirici alanin adi/bicimi degisirse kapi
    sessizce "0 ozgun, 0 ihlal" diyemesin
  * gizli kayit YOK ve `--kaynaksiz` VERILMEDI

KAYNAKSIZ KIP (`--kaynaksiz`, CI SERIT B): gizli kayit CI'da YOK (gitignore). Menzil
BEYANLI daraltilir: yalniz (b) kolu (public veriyle tam olculur) kosar, son satir
`ozgun=OLCULEMEDI ... kapsam=kaynaksiz` basar. (a)/(c) yerelde (pre-push) olculur.

VERI YAZMAZ. Cikti STDOUT; son satir:
  LISANS_IFSA ozgun=<n> ihlal=<n> rc=<0|1>
  LISANS_IFSA ozgun=OLCULEMEDI ihlal=<n> rc=<0|1> kapsam=kaynaksiz
  LISANS_IFSA OLCULEMEDI sebep=<...> rc=2
Kabul testi: tools/lisans-ifsa-kapisi-test.py (vakalar + bellek-ici mutantlar).
"""
import argparse
import importlib.util
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_KOD_KOK = os.path.dirname(_HERE)

IC_ETIKET_RE = re.compile(r"kendi-tasarim|pruvo \(kendi", re.IGNORECASE)


class Olculemedi(Exception):
    pass


def _yukle(dosya_adi, modul_adi):
    """tools/ altindaki tireli dosyayi modul olarak yukler (repo geneli desen)."""
    spec = importlib.util.spec_from_file_location(modul_adi, os.path.join(_HERE, dosya_adi))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kendi_turleri():
    return frozenset(_yukle("denetim-kapisi.py", "lisans_ifsa_denetim")._ATIF_KENDI_TUR)


def gercek_atif():
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import build
    return build.attribution_html


def ozgun_mu(kayit, turler):
    if not isinstance(kayit, dict):
        return False
    return str(kayit.get("tur") or "").strip().lower() in turler


def _dizgeler(deger):
    if isinstance(deger, str):
        yield deger
    elif isinstance(deger, dict):
        for k, v in deger.items():
            yield str(k)
            yield from _dizgeler(v)
    elif isinstance(deger, list):
        for v in deger:
            yield from _dizgeler(v)


def ic_etiket_var(urun):
    return any(IC_ETIKET_RE.search(s) for s in _dizgeler(urun))


def _ayristir(metin, ad):
    try:
        return json.loads(metin)
    except (ValueError, TypeError) as e:
        raise Olculemedi("%s ayristirilamadi (%s)" % (ad, type(e).__name__))


def denetle(urunler_metni, kaynaklar_metni, turler, atif_fn):
    """Doner (ozgun_sayisi|None, ihlaller[(kol, id, ayrinti)]). kaynaklar_metni None ->
    kaynaksiz kip (yalniz kol b). Olcemedigi her halde Olculemedi firlatir."""
    urunler = _ayristir(urunler_metni, "urunler.json")
    if not isinstance(urunler, list):
        raise Olculemedi("urunler.json dizi degil")
    for p in urunler:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not p.get("id"):
            raise Olculemedi("urunler.json kaydi sozluk degil ya da id yok")
    ihlaller = []
    for p in urunler:
        if ic_etiket_var(p): ihlaller.append(("b", p["id"], "ic etiket dizgesi"))  # KOL-B
    if kaynaklar_metni is None:
        return None, ihlaller
    kaynaklar = _ayristir(kaynaklar_metni, ".urun-kaynaklari.json")
    if not isinstance(kaynaklar, dict):
        raise Olculemedi(".urun-kaynaklari.json nesne degil")
    ozgunler = [p for p in urunler if ozgun_mu(kaynaklar.get(p["id"]), turler)]  # AYIRICI
    if not ozgunler: raise Olculemedi("ayirici hicbir urun secmedi (ozgun=0)")  # SIFIR-KORUMA
    for p in ozgunler:
        if "lisans" in p: ihlaller.append(("a", p["id"], "public lisans alani var"))  # KOL-A
        atif = atif_fn(p)
        if atif: ihlaller.append(("c", p["id"], "atif %d bayt" % len(atif.encode("utf-8"))))  # KOL-C
    return len(ozgunler), ihlaller


def kos(urunler_metni, kaynaklar_metni, kaynaksiz=False, turler=None, atif_fn=None):
    """Doner (rc, satirlar). Dosya OKUMAZ — test bellekten besler."""
    try:
        turler = kendi_turleri() if turler is None else turler
        atif_fn = gercek_atif() if atif_fn is None else atif_fn  # ATIF-BAGI
        if kaynaklar_metni is None and not kaynaksiz:
            raise Olculemedi("gizli kaynak kaydi yok (--kaynaksiz verilmedi)")
        ozgun, ihlaller = denetle(urunler_metni, None if kaynaksiz else kaynaklar_metni,
                                  turler, atif_fn)
    except Olculemedi as e:
        return 2, ["LISANS_IFSA OLCULEMEDI sebep=%s rc=2" % str(e).replace(" ", "_")]
    satirlar = ["LISANS_IFSA IHLAL kol=%s id=%s (%s)" % i for i in ihlaller]
    rc = 1 if ihlaller else 0  # RC
    if ozgun is None:
        satirlar.append("LISANS_IFSA ozgun=OLCULEMEDI ihlal=%d rc=%d kapsam=kaynaksiz"
                        % (len(ihlaller), rc))
    else:
        satirlar.append("LISANS_IFSA ozgun=%d ihlal=%d rc=%d" % (ozgun, len(ihlaller), rc))
    return rc, satirlar


def _oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise Olculemedi("%s okunamadi (%s)" % (os.path.basename(yol), type(e).__name__))


def _veri_kok():
    vk = _yukle("veri_kok.py", "lisans_ifsa_veri_kok")
    _kod, veri, _uyari = vk.cozumle(os.path.abspath(__file__))
    return veri


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ozgun urunde lisans/atif ifsa kapisi (veri YAZMAZ)")
    ap.add_argument("--urunler", help="urunler.json yolu (varsayilan: bu agacin kopyasi)")
    ap.add_argument("--kaynaklar", help=".urun-kaynaklari.json yolu (varsayilan: veri koku)")
    ap.add_argument("--kaynaksiz", action="store_true",
                    help="gizli kayitsiz BEYANLI dar menzil: yalniz kol (b) (CI SERIT B)")
    a = ap.parse_args(argv)
    try:
        urunler_metni = _oku(a.urunler or os.path.join(_KOD_KOK, "urunler.json"))
        kaynaklar_metni = None
        if not a.kaynaksiz:
            yol = a.kaynaklar or os.path.join(_veri_kok(), ".urun-kaynaklari.json")
            if os.path.exists(yol) or a.kaynaklar:
                kaynaklar_metni = _oku(yol)
    except Olculemedi as e:
        print("LISANS_IFSA OLCULEMEDI sebep=%s rc=2" % str(e).replace(" ", "_"))
        return 2
    rc, satirlar = kos(urunler_metni, kaynaklar_metni, kaynaksiz=a.kaynaksiz)
    for s in satirlar:
        print(s)
    return rc


if __name__ == "__main__":
    sys.exit(main())
