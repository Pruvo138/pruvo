#!/usr/bin/env python3
"""ISCI-SARMALAYICI KAPISI — 6 EV DAGITIM KANITI (hermetik, gercek evlere DOKUNMAZ).

NEDEN VAR (memory/mutasyon-kaniti-yeniden-uretilebilir.md): "dagitim komutu hazir"
ANLATILAN bir iddiadir; kanit YENIDEN URETILEBILIR olmali. 'mimar-kapi-kur.py
--isci-kapisi' kuru kosumunun "ENJEKTE EDILECEK" demesi TEK BASINA kanit DEGILDIR —
o yalnizca zorunlu SEMBOLLERIN varligini olcer, enjeksiyonun DERLENDIGINI ve canli
fiksturleri GECTIGINI olcmez.

NE YAPAR: her kardes evin kapi dosyasini GECICI bir "sahte ev" dizinine KOPYALAR,
kopyaya kurali enjekte eder (_eve_isci_enjekte, uygula=True), enjeksiyon sonrasi
compile + CANLI FIKSTUR bataryasini kosturur ve dizini siler.

🔴 GERCEK EVLERE YAZILMAZ: kardes evler baska mimarlarin mulkudur; fiili dagitim
'python3 tools/mimar-kapi-kur.py --isci-kapisi --uygula' ile MIMAR ONAYINDAN sonra
yapilir. Bu betik o komutun GECECEGINI onceden olcer.

Cikis kodu 0 = her kardes evin KOPYASINDA enjeksiyon + fikstur GECTI.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(TOOLS, "mimar-kapi-kur.py")


def _kur_modulu():
    spec = importlib.util.spec_from_file_location("mimar_kapi_kur", KUR)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _enjeksiyon_gecti(durum, damga_var):
    return durum in ("KURULDU", "ZATEN TAM") and damga_var


def _bozuk_damga_negatif_nobeti(kur):
    ad, gercek_kok, _g, _mod = next(ev for ev in kur.CODEX_EVLER if ev[0] == "BaBa")
    goreli, _kablo = kur._kapi_yolu_olc(gercek_kok)
    sahte = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-bozuk-damga-"))
    hedef = os.path.join(sahte, goreli)
    try:
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copyfile(os.path.join(gercek_kok, goreli), hedef)
        with open(hedef, encoding="utf-8") as dosya:
            metin = dosya.read()
        metin = metin.replace(kur.ISCI_DAMGA, 'ISCI_KURAL_SURUMU = "BOZUK"')
        with open(hedef, "w", encoding="utf-8") as dosya:
            dosya.write(metin)
        with open(hedef, encoding="utf-8") as dosya:
            damga_var = kur.ISCI_DAMGA in dosya.read()
        gecti = _enjeksiyon_gecti("ZATEN TAM", damga_var)
        print("BOZUK DAMGA NEGATIF NOBETI: ev={} durum=ZATEN TAM damga={} sonuc={}".format(
            ad, "var" if damga_var else "YOK", "YESIL" if gecti else "KIRMIZI"))
        return 1 if gecti else 0
    finally:
        shutil.rmtree(sahte, ignore_errors=True)


def main():
    if not os.path.exists(KUR):
        print("KUR ARACI YOK: " + KUR)
        sys.exit(2)
    kur = _kur_modulu()
    if "--bozuk-damga-test" in sys.argv[1:]:
        sys.exit(_bozuk_damga_negatif_nobeti(kur))

    # Evler KANONIK KAYNAKTAN gelir (CODEX_EVLER) — bu betik ikinci bir ev listesi
    # TUTMAZ (memory/ikiz-tanim-sessiz-ayrisma.md). 'kaynak' modlu ev (KraL) atlanir:
    # orada kural commit'li dosyada yasar, enjekte EDILMEZ.
    hedefler = [(ad, kok) for ad, kok, _g, mod in kur.CODEX_EVLER if mod == "enjekte"]

    print("ISCI-SARMALAYICI DAGITIM KANITI (hermetik) — DAMGA: " + kur.ISCI_DAMGA)
    print("HEDEF EV: {} (kaynak modlu ev atlanir)".format(len(hedefler)))
    print("")

    kirmizi = []
    for ad, gercek_kok in hedefler:
        if not os.path.isdir(gercek_kok):
            print("{:<7} EV YOK: {}".format(ad, gercek_kok))
            kirmizi.append(ad)
            continue
        goreli, _kablo = kur._kapi_yolu_olc(gercek_kok)
        if goreli is None:
            print("{:<7} KAPI YOLU OLCULEMEDI".format(ad))
            kirmizi.append(ad)
            continue
        kaynak = os.path.join(gercek_kok, goreli)
        sahte_taban = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-isci-dagitim-"))
        # Ev kimligi REPO_ONEKI'nin son bileseninden cikar; hermetik kopya da gercek ev
        # basename'ini korumali, yoksa MaCiT yanlislikla kume-disi gorunur.
        sahte = os.path.join(sahte_taban, os.path.basename(gercek_kok))
        hedef = os.path.join(sahte, goreli)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copyfile(kaynak, hedef)
        rapor = []
        try:
            agent_durum, _ = kur._eve_agent_enjekte(ad, sahte, goreli, True, rapor)
            if agent_durum not in ("KURULDU", "ZATEN TAM"):
                durum = "AGENT ONKOSULU: " + agent_durum
            else:
                durum, _ = kur._eve_isci_enjekte(ad, sahte, goreli, True, rapor)
        except Exception as hata:
            durum = "ISTISNA: " + repr(hata)[:110]
        try:
            with open(hedef, encoding="utf-8") as f:
                damga_var = kur.ISCI_DAMGA in f.read()
        except Exception:
            damga_var = False
        gecti = _enjeksiyon_gecti(durum, damga_var)
        print("{:<7} {:<34} enjeksiyon={:<24} damga={:<4} {}".format(
            ad, goreli, durum, "var" if damga_var else "YOK",
            "OK" if gecti else "KIRMIZI"))
        for satir in rapor:
            if "GERI ALINDI" in satir or "EKSIK" in satir:
                print("        " + satir.strip())
        if not gecti:
            kirmizi.append(ad)
        shutil.rmtree(sahte_taban, ignore_errors=True)

    print("")
    print("KANIT: {}/{} kardes evin KOPYASINDA enjeksiyon + canli fikstur GECTI".format(
        len(hedefler) - len(kirmizi), len(hedefler)))
    if kirmizi:
        print("KIRMIZI EV: " + ", ".join(kirmizi))
        sys.exit(1)
    print("FIILI DAGITIM (mimar onayi ile): "
          "python3 /Users/okan/dev/pruvo/tools/mimar-kapi-kur.py --isci-kapisi --uygula")
    sys.exit(0)


if __name__ == "__main__":
    main()
