#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EGE TAVAN PAYI — FILAMENT EKLEME SIMULASYONU (kac filament daha sigar?).

NEDEN VAR: ege-bilgi.md'nin "MALZEME KAPSAMI" blogu tools/filamentler.json'dan URETILIR
(tools/ege-malzeme.py). Yeni bir filament eklemek bu blogu buyutur ve dosya
pruvo-bot/worker/src/index.js:2658'deki `.slice(0, 6000)` tavanina yaklasir. Tavan asilirsa
IKI ayri zarar birden olur:
  (1) tools/ege-bilgi-tavan-test.py CI'da KIRMIZI yanar -> deploy.yml `build` isi duser ->
      TUM EKIBIN yayini blokelenir (o an filamentle hic ilgisi olmayan bir dal dahil);
  (2) tavan asildigi halde kapi bir sebeple susarsa Ege'nin metni SESSIZCE kirpilir ve
      musteriye EKSIK/YANLIS beyan gider (kirpma logsuz, uyarisiz).
Bu araci filamentler.json'a dokunmadan ONCE kostur: "N filament eklersem tavan tutuyor mu?"

🔴 GUVENLIK: canli dosyalara YAZILMAZ. Butun simulasyon gecici bir agac kopyasinda doner
(T/tools/*.py + T/tools/filamentler.json + T/ege-bilgi.md); tools/ege-malzeme.py yolundan
ROOT turettigi icin kopya agacta kosunca KOPYAYI gunceller. Betik, canli uc dosyanin
sha256'sini BASTA ve SONDA olcup esitligi dogrular -> "yazmadim" iddiasi OLCULUR, beyan
edilmez ([[mutasyon-diske-yazma-tuzagi]]).

OLCU: JS String.slice UTF-16 kod birimi sayar; hukum kapinin (ege-bilgi-tavan-test.py)
KENDI degerlendir()'inden gelir — burada ikinci bir tavan mantigi YAZILMAZ (ikiz tanim
sessizce ayrisir: [[ikiz-tanim-sessiz-ayrisma]]).

SENTETIK FILAMENT KOTUMSERDIR: mevcut EN UZUN "site": true kaleminin alan uzunluklari
taban alinir (bugun TPU). Ortalama kalem alinsaydi simulasyon gercek riski KUCUK gosterirdi.

Kullanim:
    python3 tools/ege-tavan-pay-simulasyon.py
    python3 tools/ege-tavan-pay-simulasyon.py --adetler 0,1,3,5,8
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
CANLI = {
    "ege-bilgi.md": os.path.join(ROOT, "ege-bilgi.md"),
    "tools/filamentler.json": os.path.join(TOOLS, "filamentler.json"),
    "tools/ege-malzeme.py": os.path.join(TOOLS, "ege-malzeme.py"),
}
KAPI = os.path.join(TOOLS, "ege-bilgi-tavan-test.py")


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kapi_yukle():
    """Kapiyi MODUL olarak yukle — TAVAN/GUVENLIK_MARJI/degerlendir TEK KAYNAKTAN."""
    if not os.path.exists(KAPI):
        sys.exit("FAIL-CLOSED: %s YOK — tavan hukmu olculemez." % KAPI)
    spec = importlib.util.spec_from_file_location("ege_tavan_kapi", KAPI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for ad in ("TAVAN", "GUVENLIK_MARJI", "degerlendir", "utf16_birim"):
        if not hasattr(mod, ad):
            sys.exit("FAIL-CLOSED: kapida %s YOK — sozlesme degismis." % ad)
    return mod


def site_kalemi(ref, kip):
    """Sentetik sablon. kip='en-uzun' KOTUMSER (varsayilan), 'en-kisa' IYIMSER SINIR.

    Iki ucu da olcmek gerekir: tek bir "ortalama" sayi, gercek bir kalemin 141 birim
    tuttugu halde "95 birim" sanmaya yol acar ve pay hesabini SESSIZCE sisirir."""
    adaylar = [f for f in ref["filamentler"] if f.get("site")]
    if not adaylar:
        sys.exit("FAIL-CLOSED: filamentler.json'da 'site': true kalem YOK.")
    olcu = lambda f: len(json.dumps(f, ensure_ascii=False))
    return (max if kip == "en-uzun" else min)(adaylar, key=olcu)


def sentetik(sablon, i):
    """Sablonla AYNI alan uzunluklarinda sahte filament (adlar benzersiz)."""
    y = dict(sablon)
    y["ad"] = "ZZ%d" % i
    y.pop("uzunAd", None)
    y["uzunAd"] = ("%s (sentetik-%d)" % (sablon.get("uzunAd") or sablon["ad"], i))
    return y


def kur(gecici, ref_mutant):
    """Gecici agac: T/tools/{ege-malzeme.py, filament_ortak.py, filamentler.json} + T/ege-bilgi.md"""
    t_tools = os.path.join(gecici, "tools")
    os.makedirs(t_tools, exist_ok=True)
    for ad in ("ege-malzeme.py", "filament_ortak.py"):
        shutil.copy2(os.path.join(TOOLS, ad), os.path.join(t_tools, ad))
    with io.open(os.path.join(t_tools, "filamentler.json"), "w", encoding="utf-8") as f:
        json.dump(ref_mutant, f, ensure_ascii=False, indent=2)
    t_md = os.path.join(gecici, "ege-bilgi.md")
    shutil.copy2(CANLI["ege-bilgi.md"], t_md)
    return os.path.join(t_tools, "ege-malzeme.py"), t_md


def uret(uretici_yol):
    """Kopya agactaki ege-malzeme.py'yi MODUL olarak kosur (alt surec yok, cikti sessiz)."""
    spec = importlib.util.spec_from_file_location("ege_malzeme_kopya_%s"
                                                  % abs(hash(uretici_yol)), uretici_yol)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(uretici_yol))
    try:
        spec.loader.exec_module(mod)
        eski_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            mod.main()
        finally:
            sys.stdout = eski_stdout
    finally:
        sys.path.pop(0)
        for ad in ("filament_ortak",):
            sys.modules.pop(ad, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adetler", default="0,1,3,5",
                    help="simule edilecek EK filament sayilari (virgul ile)")
    ap.add_argument("--sablon", default="en-uzun", choices=("en-uzun", "en-kisa"),
                    help="sentetik kalem boyu: en-uzun = KOTUMSER (varsayilan)")
    args = ap.parse_args()
    adetler = [int(x) for x in args.adetler.split(",") if x.strip() != ""]

    kapi = kapi_yukle()
    bas_sha = {k: sha(v) for k, v in CANLI.items()}

    with io.open(CANLI["tools/filamentler.json"], encoding="utf-8") as f:
        ref = json.load(f)
    sablon = site_kalemi(ref, args.sablon)

    print("EGE TAVAN PAYI — FILAMENT EKLEME SIMULASYONU")
    print("  TAVAN            : %d UTF-16 birimi (kapidan okundu)" % kapi.TAVAN)
    print("  GUVENLIK_MARJI   : %d (kapidan okundu)" % kapi.GUVENLIK_MARJI)
    print("  Sentetik sablon  : %r (%s 'site': true kalem%s)"
          % (sablon.get("uzunAd") or sablon["ad"], args.sablon,
             " — KOTUMSER" if args.sablon == "en-uzun" else " — IYIMSER SINIR"))
    print("  Canli dosyalara YAZILMAZ; her kosum gecici agac kopyasinda doner.")
    print("-" * 92)
    print("  %-5s %-10s %-8s %-9s %-8s %s" % ("EK", "UZUNLUK", "PAY", "MARJINAL", "KAPI", "HUKUM"))
    print("-" * 92)

    onceki = None
    satirlar = []
    for n in adetler:
        mutant = json.loads(json.dumps(ref, ensure_ascii=False))
        for i in range(1, n + 1):
            mutant["filamentler"].append(sentetik(sablon, i))
        gecici = tempfile.mkdtemp(prefix="ege-pay-sim-")
        try:
            uretici, t_md = kur(gecici, mutant)
            uret(uretici)
            kod, rapor = kapi.degerlendir(t_md)
            with io.open(t_md, encoding="utf-8") as f:
                uz = kapi.utf16_birim(f.read())
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
        pay = kapi.TAVAN - uz
        marj = "-" if onceki is None else "%+d" % (uz - onceki)
        onceki = uz
        durum = "KIRMIZI" if kod != 0 else ("UYARILI" if "DAR PAY" in "\n".join(rapor)
                                            else "YESIL")
        hukum = next((s.strip() for s in rapor if s.strip().startswith("SONUC")), "?")
        print("  %-5d %-10d %-8d %-9s %-8s %s" % (n, uz, pay, marj, durum, hukum[:34]))
        satirlar.append((n, uz, pay, kod, durum))

    print("-" * 92)
    son_sha = {k: sha(v) for k, v in CANLI.items()}
    bozulan = [k for k in CANLI if bas_sha[k] != son_sha[k]]
    if bozulan:
        print("  ❌ CANLI DOSYA DEGISTI: %s — simulasyon canliya YAZDI, bu bir KAZADIR." % bozulan)
        return 1
    print("  ✅ Canli dosyalarin sha256'si BAS = SON (%s) — hicbirine yazilmadi."
          % ", ".join(sorted(CANLI)))

    # KAC KALEM SIGAR — marjinal maliyetten degil, OLCULEN kosumlardan turetilir.
    sigan = [n for n, _, _, kod, _ in satirlar if kod == 0]
    if len(satirlar) > 1:
        marjinal = (satirlar[-1][1] - satirlar[0][1]) / float(satirlar[-1][0] - satirlar[0][0]) \
            if satirlar[-1][0] != satirlar[0][0] else 0
        print("  Kalem BASINA marjinal maliyet (%s sablon): %.1f UTF-16 birimi"
              % (args.sablon, marjinal))
    print("  Tavani ASMADAN eklenebilen EK kalem (olculen adetler icinde): %s"
          % (max(sigan) if sigan else "0"))

    kirmizi = [n for n, _, _, kod, _ in satirlar if kod != 0]
    if kirmizi:
        print("  ⚠️  TAVAN ASILAN EK FILAMENT SAYILARI: %s -> bu kadar kalem eklenmeden "
              "ONCE yer acilmali (bkz. tools/ege-malzeme.py sikistirma notlari)." % kirmizi)
    else:
        print("  Simule edilen hicbir adette tavan asilmadi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
