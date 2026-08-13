#!/usr/bin/env python3
"""Skan Art kum havuzu ozyineleme kilidi kabul ve mutant testi."""
import ast
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

VARSAYILAN_KAYNAK = os.path.join(os.path.dirname(__file__), "test-skan-art.py")
GEREKLI_ATAMALAR = {"MAKSIMUM_AYNI_DIZIN_DERINLIGI", "KUM_SIR_DESENLER"}
GEREKLI_ISLEVLER = {
    "ayni_ad_derinligi", "uretim_derinligini_dogrula", "_kum_sir_mi",
    "kum_kopya_yoksay", "guvenli_agac_kopyala", "gecici_uretim_koku",
}


def kilidi_yukle(kaynak_yolu):
    with open(kaynak_yolu, encoding="utf-8") as f:
        agac = ast.parse(f.read(), kaynak_yolu)
    dugumler = []
    for dugum in agac.body:
        if isinstance(dugum, (ast.Import, ast.ImportFrom)):
            dugumler.append(dugum)
        elif isinstance(dugum, ast.Assign):
            adlar = {hedef.id for hedef in dugum.targets if isinstance(hedef, ast.Name)}
            if adlar & GEREKLI_ATAMALAR:
                dugumler.append(dugum)
        elif isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if dugum.name in GEREKLI_ISLEVLER:
                dugumler.append(dugum)
    bulunan = {
        dugum.name for dugum in dugumler
        if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if bulunan != GEREKLI_ISLEVLER:
        raise RuntimeError("kilit islevleri eksik: %s" % sorted(GEREKLI_ISLEVLER - bulunan))
    kapsam = {"__file__": kaynak_yolu}
    exec(compile(ast.fix_missing_locations(ast.Module(dugumler, type_ignores=[])),
                 kaynak_yolu, "exec"), kapsam)
    return kapsam


def dosya_yaz(yol, icerik):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)


def agac_olc(kok):
    toplam = 0
    adlar = []
    for dizin, _, dosyalar in os.walk(kok):
        for ad in dosyalar:
            yol = os.path.join(dizin, ad)
            toplam += os.path.getsize(yol)
            adlar.append(os.path.relpath(yol, kok))
    return toplam, sorted(adlar)


def fikstur_hazirla(kok):
    dosya_yaz(os.path.join(kok, "girdi.txt"), "sabit-girdi\n")
    dosya_yaz(os.path.join(kok, "alt", "parca.dat"), "parca\n")
    dosya_yaz(os.path.join(kok, ".r2-credentials.json"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", ".gemini-key"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", ".mmf-token"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", ".uyelik-kodlar"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", ".tedarikci-fiyat"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", ".env.test"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", "private.key"), "SIR\n")
    dosya_yaz(os.path.join(kok, "alt", "api-token.txt"), "SIR\n")


def kabul_kos(kaynak_yolu):
    kilit = kilidi_yukle(kaynak_yolu)
    sonuclar = {}
    with tempfile.TemporaryDirectory(prefix="skan-art-kabul-") as gecici:
        kaynak = os.path.join(gecici, "kaynak")
        hedef = os.path.join(gecici, "hedef")
        os.makedirs(kaynak)
        fikstur_hazirla(kaynak)

        try:
            kilit["guvenli_agac_kopyala"](kaynak, hedef)
            ilk_boyut, ilk_adlar = agac_olc(hedef)
            kilit["guvenli_agac_kopyala"](kaynak, hedef)
            ikinci_boyut, ikinci_adlar = agac_olc(hedef)
            sonuclar["A1"] = ikinci_boyut <= ilk_boyut and ikinci_adlar == ilk_adlar
        except Exception:
            sonuclar["A1"] = False

        try:
            ucuncu = os.path.join(gecici, "head-golge", "head-golge", "head-golge")
            kilit["uretim_derinligini_dogrula"](ucuncu)
            sonuclar["A2"] = False
        except RuntimeError:
            sonuclar["A2"] = True
        except Exception:
            sonuclar["A2"] = False

        sir_adlari = {
            ".r2-credentials.json", ".gemini-key", ".mmf-token", ".uyelik-kodlar",
            ".tedarikci-fiyat", ".env.test", "private.key", "api-token.txt",
        }
        bulunan_sir = []
        if os.path.isdir(hedef):
            for _, _, dosyalar in os.walk(hedef):
                bulunan_sir.extend(ad for ad in dosyalar if ad in sir_adlari)
        sonuclar["A3"] = len(bulunan_sir) == 0

        basari_koku = None
        hata_koku = None
        try:
            with kilit["gecici_uretim_koku"](gecici) as basari_koku:
                dosya_yaz(os.path.join(basari_koku, "cikti.txt"), "tamam\n")
            try:
                with kilit["gecici_uretim_koku"](gecici) as hata_koku:
                    dosya_yaz(os.path.join(hata_koku, "cikti.txt"), "hata\n")
                    raise ValueError("yapay hata")
            except ValueError:
                pass
            sonuclar["A4"] = (
                basari_koku is not None and hata_koku is not None
                and not os.path.exists(basari_koku) and not os.path.exists(hata_koku)
            )
        except Exception:
            sonuclar["A4"] = False

        beklenen = (len("sabit-girdi\n") + len("parca\n"), ["alt/parca.dat", "girdi.txt"])
        sonuclar["A5"] = agac_olc(hedef) == beklenen if os.path.isdir(hedef) else False

        asil_mkdtemp = tempfile.mkdtemp
        sahte_dis_kok = os.path.join(os.path.dirname(tempfile.gettempdir()),
                                     "skan-art-sahte-dis-kok")
        tempfile.mkdtemp = lambda *args, **kwargs: sahte_dis_kok
        try:
            try:
                with kilit["gecici_uretim_koku"]():
                    pass
                sonuclar["A6"] = False
            except RuntimeError:
                sonuclar["A6"] = not os.path.exists(sahte_dis_kok)
            except Exception:
                sonuclar["A6"] = False
        finally:
            tempfile.mkdtemp = asil_mkdtemp

    for ad in ("A1", "A2", "A3", "A4", "A5", "A6"):
        print("%s: %s" % (ad, "GECTI" if sonuclar.get(ad) else "KALDI"))
    gecen = sum(bool(sonuclar.get(ad)) for ad in ("A1", "A2", "A3", "A4", "A5", "A6"))
    print("SONUC: %d/6 iddia %s" % (gecen, "GECTI" if gecen == 6 else "KALDI"))
    return 0 if gecen == 6 else 1


def mutantlari_dogrula(kaynak_yolu):
    with open(kaynak_yolu, encoding="utf-8") as f:
        asil = f.read()
    mutantlar = {
        "M1": (
            "if tekrar > MAKSIMUM_AYNI_DIZIN_DERINLIGI:",
            "if False:", "A2: KALDI",
        ),
        "M2": (
            "if os.path.exists(hedef):\n        return hedef, True",
            "if False:\n        return hedef, True", "A1: KALDI",
        ),
        "M3": (
            "KUM_SIR_DESENLER = (\n    \".*\", \".env*\", \"*.key\", \"*token*\",\n"
            "    \".r2-credentials.json\", \".gemini-key\", \".mmf-token\",\n"
            "    \".uyelik-kodlar\", \".tedarikci-fiyat\",\n)",
            "KUM_SIR_DESENLER = ()", "A3: KALDI",
        ),
        "M4": (
            "if (silinecek_kok == temp_koku\n"
            "                or os.path.commonpath((temp_koku, silinecek_kok)) != temp_koku):\n"
            "            raise RuntimeError(\"gecici uretim koku temp disinda; silinmedi: %s\" % kok)",
            "if False:\n            raise RuntimeError(\"temp koku kalkani kaldirildi\")",
            "A6: KALDI",
        ),
    }
    oldurulen = 0
    with tempfile.TemporaryDirectory(prefix="skan-art-mutant-") as gecici:
        for ad, (eski, yeni, beklenen) in mutantlar.items():
            uygulandi = asil.count(eski) == 1
            mutant = asil.replace(eski, yeni, 1) if uygulandi else asil
            mutant_yolu = os.path.join(gecici, "%s.py" % ad.lower())
            dosya_yaz(mutant_yolu, mutant)
            ortam = dict(os.environ)
            ortam["SKAN_ART_KAYNAK"] = mutant_yolu
            kosum = subprocess.run([sys.executable, os.path.abspath(__file__)],
                                   capture_output=True, text=True, env=ortam)
            oldu = uygulandi and kosum.returncode != 0 and beklenen in kosum.stdout
            oldurulen += int(oldu)
            print("%s: UYGULANDI=%s rc=%d hedef=%s" % (
                ad, "evet" if uygulandi else "hayir", kosum.returncode,
                "KIRMIZI" if oldu else "YAKALANMADI"))
    print("SONUC: %d/4 mutant OLDURULDU" % oldurulen)
    return 0 if oldurulen == 4 else 1


if __name__ == "__main__":
    kaynak = os.environ.get("SKAN_ART_KAYNAK", VARSAYILAN_KAYNAK)
    if "--mutant" in sys.argv:
        raise SystemExit(mutantlari_dogrula(kaynak))
    raise SystemExit(kabul_kos(kaynak))
