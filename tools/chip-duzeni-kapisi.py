#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K185 chip düzeni nöbetçisi.

Bu kapı oturum panelini değil, defterdeki açık CHIP kalemlerinin izlenebilir
olup olmadığını ölçer: chip adı bilinen ev ile başlamalı ve posta kutusunda
başlangıç/kapanış izi bulunmalıdır.
"""
import argparse
import importlib.util
import os
import re
import sys


YESIL = "YESIL"
KIRMIZI = "KIRMIZI"
OLCULEMEDI = "OLCULEMEDI"
KAPSAM_DISI = "KAPSAM_DISI"
ISARET = {YESIL: "✅", KIRMIZI: "🔴", OLCULEMEDI: "⚪", KAPSAM_DISI: "▫️"}

# Kabul testi bu demeti sözleşme olarak okur; ad değişiklikleri çökme yerine
# ölçülemedi hükmü üretmelidir.
SOZLESME = ("YESIL", "KIRMIZI", "OLCULEMEDI", "KAPSAM_DISI", "ev_onek_hukmu",
            "kutu_iz_hukmu", "chipleri_kesfet", "denetle", "cikis_kodu",
            "EV_BILINEN_YUKLE")

CHIP_TOKEN_RE = re.compile(r"\bCHIP\b")  # CHIP_MUTANT_M5_DISCOVERY
IZ_RE = re.compile(r"(?:BASLIYORUM|BAŞLIYORUM|KAPANIS|KAPANIŞ)", re.IGNORECASE)
KIMLIK_RE = re.compile(r"\bK\d+\b", re.IGNORECASE)


def _repo_koku():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        os.pardir))


def EV_BILINEN_YUKLE():
    """Ev kümesini sahiplik kapısından tek kaynak olarak yükler."""
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sahiplik-kapisi.py")
    if not os.path.isfile(yol):
        raise RuntimeError("sahiplik-kapisi.py yok")
    spec = importlib.util.spec_from_file_location("pruvo_sahiplik_chip", yol)
    if spec is None or spec.loader is None:
        raise RuntimeError("sahiplik-kapisi.py yüklenemedi")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "EV_BILINEN"):
        raise RuntimeError("EV_BILINEN yok")
    return set(mod.EV_BILINEN)


def _acik_bolge(defter):
    satirlar = defter.splitlines()
    bas = None
    for i, satir in enumerate(satirlar):
        if re.match(r"^## ACIK KALEMLER(?:\s|$)", satir):
            bas = i + 1
            break
    if bas is None:
        return None
    son = len(satirlar)
    for i in range(bas, len(satirlar)):
        if satirlar[i].startswith("## "):
            son = i
            break
    return satirlar[bas:son]


def chipleri_kesfet(defter):
    """Açık kalem bölgesinden CHIP kalemlerini ve kalem sayılarını çıkarır."""
    bolge = _acik_bolge(defter)
    if bolge is None:
        return None, None, None
    kalemler = [satir for satir in bolge if satir.startswith("- ")]
    chipler = []
    adsizlar = []
    for satir in kalemler:
        token = CHIP_TOKEN_RE.search(satir)
        if token is None:
            continue
        tirnak = re.match(r"[ \t]*`([^`]+)`", satir[token.end():])  # CHIP_MUTANT_M8_ADJACENCY
        if tirnak is None:
            adsizlar.append({"satir": satir})  # CHIP_MUTANT_M7_ADSIZ
            continue
        chipler.append({"ad": tirnak.group(1), "satir": satir,
                        "kimlikler": tuple(x.upper() for x in KIMLIK_RE.findall(satir))})
    return kalemler, chipler, adsizlar


def _ev_onek_gecerli(chip_adi, evler):
    if "-" not in chip_adi:
        return False
    ev, is_metni = chip_adi.split("-", 1)
    return ev in evler and bool(is_metni.strip())


def ev_onek_hukmu(chip_adi, evler):
    return _ev_onek_gecerli(chip_adi, evler)  # CHIP_MUTANT_M1_PREFIX


def kutu_iz_hukmu(chip_adi, kimlikler, kutu):
    if kutu is None:
        return True
    ad = chip_adi.casefold()
    iz_var = False
    for satir in kutu.splitlines():
        iz = IZ_RE.search(satir) is not None
        if iz and (ad in satir.casefold() or
                   any(kimlik.casefold() in satir.casefold() for kimlik in kimlikler)):
            iz_var = True
    return iz_var  # CHIP_MUTANT_M2_TRACE


def _olculemedi_sonucu(gerekce):
    return {"hal": OLCULEMEDI, "rc": 2, "kalem": 0, "chip": 0,
            "adsiz": 0, "onek_kirmizi": 0, "iz_kirmizi": 0, "items": [],
            "adsiz_items": [],
            "kutu_kapsam_dis": False, "gerekce": gerekce}


def _denetle_metin(defter, kutu, evler):
    if defter is None:
        return _olculemedi_sonucu("defter okunamadı")
    kalemler, chipler, adsizlar = chipleri_kesfet(defter)
    if kalemler is None:
        return _olculemedi_sonucu("ACIK KALEMLER bölgesi yok")
    if not kalemler:
        return _olculemedi_sonucu("açık kalem sayısı 0 ölçüm değildir")
    onek_kirmizi = 0
    iz_kirmizi = 0
    items = []
    for chip in chipler:
        onek = ev_onek_hukmu(chip["ad"], evler)
        iz = kutu_iz_hukmu(chip["ad"], chip["kimlikler"], kutu)
        if not onek:
            onek_kirmizi += 1
        if kutu is not None and not iz:
            iz_kirmizi += 1
        items.append((chip["ad"], onek, iz))
    kutu_kapsam_dis = kutu is None
    if kutu_kapsam_dis:
        # CHIP_MUTANT_M6_SCOPE
        kutu_kapsam_dis = True
    if adsizlar:
        hal, rc = KIRMIZI, 1
    elif not chipler:
        hal, rc = YESIL, 0
        hal, rc = YESIL, 0
    elif onek_kirmizi or iz_kirmizi:
        hal, rc = KIRMIZI, 1
    else:
        hal, rc = YESIL, 0
    return {"hal": hal, "rc": rc, "kalem": len(kalemler), "chip": len(chipler),
            "adsiz": len(adsizlar),
            "onek_kirmizi": onek_kirmizi, "iz_kirmizi": iz_kirmizi,
            "items": items, "adsiz_items": adsizlar,
            "kutu_kapsam_dis": kutu_kapsam_dis,
            "gerekce": "ölçüm tamamlandı"}


def denetle(defter_yolu, kutu_yolu, evler=None):
    """Dosyaları okuyup makine-okunur sonuç sözlüğü döndürür."""
    if not _canary():  # CHIP_MUTANT_M5_CANARY
        return _olculemedi_sonucu("kesif motoru bozuk")
    try:
        evler = EV_BILINEN_YUKLE() if evler is None else set(evler)
    except Exception as hata:  # noqa: BLE001 — fail-closed ölçülemedi
        return _olculemedi_sonucu("EV_BILINEN çözülemedi: %s" % hata)
    try:
        with open(defter_yolu, encoding="utf-8") as dosya:
            defter = dosya.read()
    except (OSError, UnicodeError):
        return _olculemedi_sonucu("defter dosyası okunamadı")  # CHIP_MUTANT_M4_FAIL_CLOSED
    kutu = None
    if kutu_yolu:
        try:
            with open(kutu_yolu, encoding="utf-8") as dosya:
                kutu = dosya.read()
        except (OSError, UnicodeError):
            kutu = None
    return _denetle_metin(defter, kutu, evler)


def cikis_kodu(sonuc):
    return int(sonuc["rc"])


def _canary():
    fikstur = ("## ACIK KALEMLER\n"
               "- CHIP `KraL-canary bir`\n"
               "- CHIP `HocA-canary iki`\n"
               "## SONRA\n")
    kalemler, chipler, adsizlar = chipleri_kesfet(fikstur)
    return (len(kalemler or ()) == 2 and len(chipler or ()) == 2 and
            len(adsizlar or ()) == 0)


def kendini_test():
    gecen = 0
    toplam = 0
    if _canary():
        gecen += 1
    toplam += 1
    evler = {"KraL", "HocA"}
    yesil = _denetle_metin("## ACIK KALEMLER\n- CHIP `KraL-yesil`\n## SONRA\n",
                           "BASLIYORUM KraL-yesil", evler)
    kirmizi = _denetle_metin("## ACIK KALEMLER\n- CHIP `ZzZ-kirmizi`\n## SONRA\n",
                             "BASLIYORUM ZzZ-kirmizi", evler)
    olculemedi = _denetle_metin(None, "", evler)
    kapsam = _denetle_metin("## ACIK KALEMLER\n- CHIP `KraL-kapsam`\n## SONRA\n",
                            None, evler)
    beklenen = ((yesil["hal"], yesil["rc"]) == (YESIL, 0),
                (kirmizi["hal"], kirmizi["rc"]) == (KIRMIZI, 1),
                (olculemedi["hal"], olculemedi["rc"]) == (OLCULEMEDI, 2),
                (kapsam["hal"], kapsam["rc"], kapsam["kutu_kapsam_dis"]) ==
                (YESIL, 0, True))
    gecen += sum(bool(x) for x in beklenen)
    toplam += len(beklenen)
    print("KENDINI_TEST=%d/%d" % (gecen, toplam))
    return 0 if gecen == toplam else 1


def _yaz(sonuc):
    for ad, onek, iz in sonuc["items"]:
        neden = "ev öneki %s" % ("uygun" if onek else "uygunsuz")
        if sonuc["kutu_kapsam_dis"]:
            neden += "; kutu dosyası kapsam dışında"
        else:
            neden += "; kutu izi %s" % ("var" if iz else "yok")
        print("%s %s — %s" %
              (ISARET[YESIL if onek and (iz or sonuc["kutu_kapsam_dis"]) else KIRMIZI],
               ad, neden))
    for _adsiz in sonuc.get("adsiz_items", ()):
        print("🔴 ADSIZ — CHIP kalemi ADSIZ — <Ev>-<Is> biçiminde backtick'li ad yok")
    if sonuc["chip"] == 0 and sonuc["kalem"] > 0:
        print("CHIP=0 — açık kalemlerde CHIP kalemi yok")
    kapsam = " KUTU_KAPSAM_DISI" if sonuc["kutu_kapsam_dis"] else ""  # CHIP_MUTANT_M3_SCOPE_OUTPUT
    print("CHIP DUZENI: %s (cikis %d) KALEM=%d CHIP=%d ADSIZ=%d ONEK_KIRMIZI=%d IZ_KIRMIZI=%d%s" %
          (sonuc["hal"], sonuc["rc"], sonuc["kalem"], sonuc["chip"],
           sonuc["adsiz"], sonuc["onek_kirmizi"], sonuc["iz_kirmizi"], kapsam))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--defter")
    parser.add_argument("--kutu")
    parser.add_argument("--kendini-test", action="store_true")
    args = parser.parse_args(argv)
    if args.kendini_test:
        return kendini_test()
    kok = _repo_koku()
    defter = args.defter or os.path.join(kok, "DEVAM.md")
    kutu = args.kutu or os.path.expanduser(
        "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")
    sonuc = denetle(defter, kutu)
    _yaz(sonuc)
    return cikis_kodu(sonuc)


if __name__ == "__main__":
    sys.exit(main())
