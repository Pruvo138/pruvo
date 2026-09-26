#!/usr/bin/env python3
"""PRUVO JEV KALIPLARI — PRUVO evlerinin hazır karar soruları, ORTAK Jev istemcisinin üstünde.

🔴 BU DOSYA ADAPTÖR DEĞİLDİR. Jev'e giden TEK yol ortak istemcidir (J1 hükmü + Okan 26 Eyl
"jev'in önünde engel olmasın"): `/Users/okan/.claude/jev/jev.py` (kaynak
`faralya-pazarlama/tools/jev/jev.py`, EyLüL bakar). Maske · kapalı küme · eşik · insan bandı ·
yedek-yok · kayıt ORADADIR; burada ikinci kopyası YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
Burada yalnız PRUVO'ya özgü olan durur: HANGİ soru, HANGİ seçenekler, HANGİ eşik.

KALIP = {ev, tip, soru, secenekler|olcek, esik}
  esik None ⇒ altın küme HENÜZ ölçülmedi: karar YİNE alınır (iş durmaz) ama sonuç DAİMA
  `insan_onayi: true` + `kalibre: false` döner — oto-karar uydurulmaz (J1 §3d). Ev ≥30 gerçek
  örnekle eşiği ölçünce sayıyı BURAYA yazar ve `JEV-ENVANTER.md`'ye isabeti düşer.

KULLANIM (her PRUVO evinden, tam yolla):
  python3 /Users/okan/dev/pruvo/tools/jev_karar.py --kaliplar
  python3 /Users/okan/dev/pruvo/tools/jev_karar.py --kalip hoca-niyet --metin "BMW E46 vites burcu var mı?"
  python3 /Users/okan/dev/pruvo/tools/jev_karar.py --kalip macit-kategori --metin-dosya /tam/yol.txt
  Python:  sys.path.insert(0, "/Users/okan/dev/pruvo/tools"); import jev_karar
           jev_karar.kalip_karar("hoca-niyet", metin, adlar=[...])

Çıkış: 0 karar döndü (insan onayı dahil) · 2 girdi kusuru · 3 Jev'e ulaşılamadı (ortak istemci rc'si).
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

# Ortak istemci: önce kurulu kanonik yol, yoksa kaynak depo (kurulum henüz yapılmadıysa iş durmasın).
ISTEMCI_YOLLARI = (
    Path("/Users/okan/.claude/jev/jev.py"),
    Path("/Users/okan/dev/faralya-pazarlama/tools/jev/jev.py"),
)
VARSAYILAN_ESIK = 0.8  # kalibre DEĞİLKEN yalnız istemcinin zorunlu alanını doldurur; sonuç insana düşer.

# Kalıplar TEK KAYNAKTAN: tools/jev-kaliplar.json (worker'lar da aynı dosyayı okur).
KALIP_DOSYASI = Path(__file__).resolve().parent / "jev-kaliplar.json"
KALIPLAR: dict[str, dict] = json.loads(KALIP_DOSYASI.read_text(encoding="utf-8"))["kaliplar"]

_istemci = None


def istemci():
    """Ortak Jev istemcisini (modül) yükler. Bulunamazsa ImportError — sessiz yedek YOK."""
    global _istemci
    if _istemci is not None:
        return _istemci
    for yol in ISTEMCI_YOLLARI:
        if yol.is_file():
            spec = importlib.util.spec_from_file_location("jev", str(yol))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _istemci = mod
            return mod
    raise ImportError("ortak Jev istemcisi yok: " + " | ".join(str(y) for y in ISTEMCI_YOLLARI))


def kalip_istegi(ad: str, metin: str, adlar=None) -> dict:
    k = KALIPLAR[ad]
    istek = {"tip": k["tip"], "soru": k["soru"], "metin": metin,
             "esik": k["esik"] if k["esik"] is not None else VARSAYILAN_ESIK}
    if "secenekler" in k:
        istek["secenekler"] = dict(k["secenekler"])
    if "olcek" in k:
        istek["olcek"] = list(k["olcek"])
    if adlar:
        istek["adlar"] = list(adlar)
    return istek


def kalip_karar(ad: str, metin: str, adlar=None, etiket: str | None = None) -> dict:
    """Hazır kalıpla tek karar. Kalibre değilse sonuç DAİMA insan onayına düşer."""
    if ad not in KALIPLAR:
        return {"ok": False, "hata": "girdi", "sebep": "kalip_yok:" + str(ad)}
    k = KALIPLAR[ad]
    sonuc = istemci().karar(kalip_istegi(ad, metin, adlar), etiket=etiket or ("pruvo-" + ad))
    if isinstance(sonuc, dict) and sonuc.get("ok"):
        sonuc["kalip"] = ad
        sonuc["ev"] = k["ev"]
        sonuc["kalibre"] = k["esik"] is not None
        if not sonuc["kalibre"]:
            sonuc["insan_onayi"] = True
    return sonuc


# ───────────────────────────── KENDİNİ TEST (ağsız; sahte istemci)
_SECENEK_ADI = re.compile(r"^[a-z][a-z0-9_]{0,63}$")  # ortak istemcinin SECENEK_ADI kuralı


class _SahteIstemci:
    """Ortak istemcinin `karar` imzası; ağ YOK. Her çağrıyı kaydeder."""

    def __init__(self, insan=False):
        self.insan = insan
        self.cagrilar = []

    def karar(self, istek, etiket=""):
        self.cagrilar.append((istek, etiket))
        alan = istek["tip"]
        deger = {"secim": next(iter(istek.get("secenekler", {"x": 0}))), "puan": 0, "evet": True}[alan]
        return {"ok": True, "tip": alan, alan: deger, "olasilik": 0.99, "insan_onayi": self.insan,
                "motor": "jev", "yol": "sahte", "sebep": "tamam"}


def _kendini_test(kaliplar=None) -> list[str]:
    """Kırmızı iddia listesi döner (boş = yeşil)."""
    global _istemci
    kaliplar = KALIPLAR if kaliplar is None else kaliplar
    kirmizi = []
    eski = _istemci
    try:
        # K1 kalıp kümesi: 5 evin hepsinin en az bir kalıbı var
        evler = {k["ev"] for k in kaliplar.values()}
        if evler != {"HocA", "KraL", "MaCiT", "ArTisT", "TeKiN"}:
            kirmizi.append("K1 ev_kumesi:" + ",".join(sorted(evler)))
        for ad, k in kaliplar.items():
            # K2 şekil: tip + soru + tipe uygun küme; seçenek adları ortak istemci kuralına uyar
            if k.get("tip") not in ("secim", "puan", "evet") or not k.get("soru"):
                kirmizi.append("K2 sekil:" + ad)
            if k.get("tip") == "secim":
                s = k.get("secenekler") or {}
                if not (2 <= len(s) <= 255) or not all(_SECENEK_ADI.match(n) for n in s):
                    kirmizi.append("K2 secenek:" + ad)
            if k.get("tip") == "puan" and not (2 <= len(k.get("olcek") or []) <= 10):
                kirmizi.append("K2 olcek:" + ad)
            # K3 eşik: None ya da (0,5 ; 1]
            e = k.get("esik")
            if e is not None and not (isinstance(e, (int, float)) and 0.5 < e <= 1):
                kirmizi.append("K3 esik:" + ad)
        # K4 kalibre DEĞİL ⇒ istemci insan=false dese de sonuç insan_onayi=true
        _istemci = _SahteIstemci(insan=False)
        ad0 = next(a for a, k in kaliplar.items() if k.get("esik") is None) if any(
            k.get("esik") is None for k in kaliplar.values()) else None
        if ad0:
            s = kalip_karar(ad0, "deneme metni")
            if not (s.get("ok") and s.get("insan_onayi") is True and s.get("kalibre") is False):
                kirmizi.append("K4 kalibre_degil_insana_dusmedi")
            # K5 istek istemciye ZORUNLU eşikle gider (istemci eşiksiz isteği reddeder)
            istek, etiket = _istemci.cagrilar[-1]
            if not isinstance(istek.get("esik"), (int, float)) or not etiket.startswith("pruvo-"):
                kirmizi.append("K5 esik_ya_da_etiket")
        # K6 kalibre kalıp istemcinin insan kararını DEĞİŞTİRMEZ
        _istemci = _SahteIstemci(insan=False)
        kopya = dict(KALIPLAR)
        try:
            KALIPLAR["_test_kalibre"] = {"ev": "KraL", "tip": "evet", "esik": 0.9, "soru": "x?"}
            s = kalip_karar("_test_kalibre", "deneme")
            if s.get("insan_onayi") is not False or s.get("kalibre") is not True:
                kirmizi.append("K6 kalibre_kalip_ezildi")
        finally:
            KALIPLAR.clear()
            KALIPLAR.update(kopya)
        # K7 bilinmeyen kalıp ⇒ girdi hatası, istemci ÇAĞRILMAZ
        _istemci = _SahteIstemci()
        s = kalip_karar("yok-boyle-kalip", "x")
        if s.get("ok") is not False or _istemci.cagrilar:
            kirmizi.append("K7 bilinmeyen_kalip")
    finally:
        _istemci = eski
    return kirmizi


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="PRUVO Jev hazır kalıpları (ortak istemci üstünde)")
    p.add_argument("--kendini-test", action="store_true", help="ağsız kabul (K1–K7)")
    p.add_argument("--kaliplar", action="store_true", help="kalıpları listele")
    p.add_argument("--kalip", help="kalıp adı")
    p.add_argument("--metin")
    p.add_argument("--metin-dosya")
    p.add_argument("--ad", action="append", default=[], help="maskelenecek kişi adı")
    p.add_argument("--etiket")
    a = p.parse_args(argv)

    if a.kendini_test:
        kirmizi = _kendini_test()
        for k in kirmizi:
            print("KIRMIZI " + k)
        print("JEV_KALIP_TEST iddia=7 kalip=%d kirmizi=%d" % (len(KALIPLAR), len(kirmizi)))
        return 1 if kirmizi else 0
    if a.kaliplar:
        for ad, k in KALIPLAR.items():
            print("%-22s ev=%-6s tip=%-5s esik=%s" % (
                ad, k["ev"], k["tip"], k["esik"] if k["esik"] is not None else "KALIBRE_DEGIL"))
        return 0
    if not a.kalip:
        p.print_help()
        return 2
    if a.kalip not in KALIPLAR:
        print(json.dumps({"ok": False, "hata": "girdi", "sebep": "kalip_yok"}, ensure_ascii=False))
        return 2
    if a.metin is not None:
        metin = a.metin
    elif a.metin_dosya:
        metin = Path(a.metin_dosya).read_text(encoding="utf-8")
    else:
        metin = sys.stdin.read()
    try:
        sonuc = kalip_karar(a.kalip, metin, a.ad, a.etiket)
    except ImportError as h:
        print(json.dumps({"ok": False, "hata": "istemci_yok", "sebep": str(h)}, ensure_ascii=False))
        return 3
    print(json.dumps(sonuc, ensure_ascii=False))
    if not sonuc.get("ok"):
        return 2
    return 0 if sonuc.get("motor") == "jev" else 3


if __name__ == "__main__":
    sys.exit(main())
