#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thing-meta-fail-loud-test.py — meta.json yazim kolunun FAIL-LOUD kabulu (K400).

NE OLCER (uc eksen):
  A) thing-hazirla.py meta.json yazamazsa SESSIZ GECMEZ: istisna SINIFI + id stderr'e
     duser ve id BASARISIZ sayilir.
  B) rc SOZLESMESI: en az bir id meta.json uretemediyse surec rc!=0 (GERCEK __main__
     yolu, alt surecte olculur — beyan degil).
  C) geri doldurma kolu VAR OLANI EZMEZ (idempotent) ve haritalanamayan semayi
     UYDURMAZ, ADIYLA atlar.

MUTANTLAR (3): her biri ilgili kolu OLDURUR; hayatta kalirsa test KIRMIZI yanar.
  M1  loud arm -> `except Exception: pass`      (sessiz yutma geri gelir)
  M2  `sys.exit(1)` wiring silinir              (rc yalan soyler)
  M3  idempotens kapisi silinir                 (geri doldurma var olani ezer)

IZOLASYON: canli govde ASLA mutasyona ugramaz. Her vaka, tools agacinin TEMP altina
alinmis TAM KOPYASINDA kosar; mutant o KOPYANIN kaynagina yazilir. Fikstur koku
tempfile kokunun ALTINDA olmak ZORUNDA (asagida capalanmis kapi) — bu yuzden yuk
gercek ev yoluna asla `rm`/`replace` uygulayamaz.
"""
import json, os, shutil, subprocess, sys, tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python3"

# thing-hazirla.py'nin import ettigi kardes moduller (izole agaca tasinir).
KARDESLER = ["thing-hazirla.py", "thing-meta-geridoldur.py", "veri_kok.py",
             "baski_ipucu.py", "drive_yolu.py", "olcu_saglik.py", "olcu_parca.py"]

THINGIVERSE_DETAIL = {
    "id": 424242,
    "name": "Test Bracket\nIkinci satir",
    "creator": {"name": "TestDesigner"},
    "license": "Creative Commons - Attribution",
    "description": "Print with 20% infill and PETG for strength.",
}
# Printables semasi: `user` tasir, `creator` YOK -> haritalanamaz olmali.
PRINTABLES_DETAIL = {"id": "p1", "name": "X", "license": "CC-BY", "user": {"publicUsername": "u"}}


def _tempte_mi(yol):
    """FIKSTUR KAPISI: yol tempfile kokunun altinda mi? Degilse yazma/silme YAPILMAZ."""
    kok = os.path.realpath(tempfile.gettempdir())
    return os.path.realpath(yol).startswith(kok + os.sep)


def izole_agac(taban):
    """taban/ (temp) altina sentetik VERI KOKU + tools kopyasi kurar. Git YOK ->
    veri_kok.cozumle() kod kokunu veri koku sayar (bkz veri_kok.py doc)."""
    assert _tempte_mi(taban), "FIKSTUR KAPISI: %s tempfile kokunun altinda degil" % taban
    t = os.path.join(taban, "tools")
    os.makedirs(t, exist_ok=True)
    for f in KARDESLER:
        shutil.copyfile(os.path.join(TOOLS, f), os.path.join(t, f))
    os.makedirs(os.path.join(taban, ".thing-cache"), exist_ok=True)
    return t


def mutasyon(tools_dizini, dosya, eski, yeni):
    """Izole KOPYANIN kaynagina mutant yazar. Capa bulunamazsa vaka OLCULEMEDI sayilir
    (sessiz 'mutant ulasmadi' YOK — bkz mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi)."""
    p = os.path.join(tools_dizini, dosya)
    assert _tempte_mi(p), "FIKSTUR KAPISI: mutant canli govdeye yazilamaz: %s" % p
    s = open(p, encoding="utf-8").read()
    if eski not in s:
        return False
    with open(p, "w", encoding="utf-8") as w:
        w.write(s.replace(eski, yeni, 1))
    return True


def hazirla_kos(tools_dizini, tid, meta_yolu_dizin_yap):
    """Izole thing-hazirla.py'yi ALT SURECTE kosar (agsiz): API cagrisi enjekte edilir.

    Donen: (rc, stdout, stderr). Surucu, modulu KAYNAKTAN yukler -> gercek govde kosar;
    yalniz `api`/`images`/`stls` disariya cikan uclar degistirilir.
    """
    kok = os.path.dirname(tools_dizini)
    d = os.path.join(kok, ".thing-cache", tid)
    os.makedirs(d, exist_ok=True)
    hedef = os.path.join(d, "meta.json")
    if meta_yolu_dizin_yap:
        # GERCEK ariza uretimi: meta.json yerine DIZIN -> os.replace OSError verir.
        os.makedirs(hedef, exist_ok=True)
    surucu = os.path.join(tools_dizini, "_surucu.py")
    with open(surucu, "w", encoding="utf-8") as w:
        w.write(
            "import importlib.util, json, os, sys\n"
            "T = os.path.dirname(os.path.abspath(__file__))\n"
            "sp = importlib.util.spec_from_file_location('th', os.path.join(T, 'thing-hazirla.py'))\n"
            "m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)\n"
            "m.api = lambda url: json.dumps(%s).encode()\n"
            "m.images = lambda tid: []\n"
            "m.stls = lambda tid, uid: (None, 1)\n"
            "b = m.main([%r])\n"
            "if b:\n"
            "    sys.stderr.write('HAL=META-YAZILAMADI id=%%s\\n' %% ','.join(b)); sys.exit(1)\n"
            % (json.dumps(THINGIVERSE_DETAIL), tid))
    r = subprocess.run([PY, surucu], capture_output=True, text=True, cwd=kok)
    return r.returncode, r.stdout, r.stderr


# --------------------------------------------------------------------------- vakalar
def vaka_a_yazim_dususu_gurultulu(tools_dizini):
    rc, out, err = hazirla_kos(tools_dizini, "424242", meta_yolu_dizin_yap=True)
    bulgular = []
    if "meta.json YAZILAMADI" not in err:
        bulgular.append("stderr'de 'meta.json YAZILAMADI' YOK")
    if "424242" not in err:
        bulgular.append("stderr ariza id'sini tasimiyor")
    if "Error" not in err and "error" not in err:
        bulgular.append("stderr istisna SINIFINI tasimiyor")
    if rc == 0:
        bulgular.append("yazim dustu ama rc=0 (basarisiz listesi bos)")
    return bulgular


def vaka_b_saglikli_kosum_yesil(tools_dizini):
    """TABAN: yazim DUSMEZSE meta.json diske duser, rc=0. (Vaka A'nin kirmizisi
    'her kosum kirmizi' olmasin diye — kolun iki yonu de olculur.)"""
    rc, out, err = hazirla_kos(tools_dizini, "515151", meta_yolu_dizin_yap=False)
    kok = os.path.dirname(tools_dizini)
    mp = os.path.join(kok, ".thing-cache", "515151", "meta.json")
    bulgular = []
    if rc != 0:
        bulgular.append("saglikli kosumda rc=%d (stderr=%s)" % (rc, err.strip()[:200]))
    if not os.path.exists(mp):
        bulgular.append("saglikli kosumda meta.json YAZILMADI")
    else:
        m = json.load(open(mp, encoding="utf-8"))
        if m.get("tasarimci") != "TestDesigner":
            bulgular.append("meta alanlari yanlis: %r" % m.get("tasarimci"))
        if "\n" in (m.get("baslik") or ""):
            bulgular.append("baslikta satir sonu temizlenmemis")
    return bulgular


def vaka_c_rc_sozlesmesi(tools_dizini):
    """GERCEK __main__ yolu: token dosyasi YOK -> api() patlar -> basarisiz -> rc=1."""
    kok = os.path.dirname(tools_dizini)
    r = subprocess.run([PY, os.path.join(tools_dizini, "thing-hazirla.py"), "999999"],
                       capture_output=True, text=True, cwd=kok)
    bulgular = []
    if r.returncode == 0:
        bulgular.append("meta.json uretilemedi ama rc=0 (rc sozlesmesi YALAN)")
    if "HAL=META-YAZILAMADI" not in r.stderr:
        bulgular.append("stderr'de HAL=META-YAZILAMADI yok: %r" % r.stderr.strip()[:200])
    return bulgular


def vaka_d_geridoldurma_ezmez(tools_dizini):
    """Idempotens + sema durustlugu."""
    kok = os.path.dirname(tools_dizini)
    cache = os.path.join(kok, ".thing-cache")
    # 1) meta.json ZATEN VAR -> dokunulmamali
    d1 = os.path.join(cache, "thVAR")
    os.makedirs(d1, exist_ok=True)
    with open(os.path.join(d1, "detail.json"), "w") as w:
        json.dump(THINGIVERSE_DETAIL, w)
    with open(os.path.join(d1, "meta.json"), "w") as w:
        json.dump({"baslik": "ELDEKI-NUSHA-DOKUNMA"}, w)
    # 2) meta.json YOK, sema uygun -> yazilmali
    d2 = os.path.join(cache, "thYOK")
    os.makedirs(d2, exist_ok=True)
    with open(os.path.join(d2, "detail.json"), "w") as w:
        json.dump(THINGIVERSE_DETAIL, w)
    open(os.path.join(d2, "g1.jpg"), "wb").write(b"x")
    # 3) haritalanamaz sema -> UYDURULMAMALI
    d3 = os.path.join(cache, "prSEMA")
    os.makedirs(d3, exist_ok=True)
    with open(os.path.join(d3, "detail.json"), "w") as w:
        json.dump(PRINTABLES_DETAIL, w)

    r = subprocess.run([PY, os.path.join(tools_dizini, "thing-meta-geridoldur.py"),
                        "--yaz", "--kok", cache], capture_output=True, text=True, cwd=kok)
    bulgular = []
    if r.returncode != 0:
        bulgular.append("geri doldurma rc=%d: %s" % (r.returncode, r.stderr.strip()[:200]))
    korunan = json.load(open(os.path.join(d1, "meta.json"), encoding="utf-8"))
    if korunan.get("baslik") != "ELDEKI-NUSHA-DOKUNMA":
        bulgular.append("IDEMPOTENS KIRIK: var olan meta.json EZILDI -> %r" % korunan.get("baslik"))
    if not os.path.exists(os.path.join(d2, "meta.json")):
        bulgular.append("eksik meta.json yazilmadi (kol hic calismiyor)")
    else:
        m = json.load(open(os.path.join(d2, "meta.json"), encoding="utf-8"))
        if m.get("gorseller") != ["g1.jpg"]:
            bulgular.append("galeri turetilemedi: %r" % m.get("gorseller"))
    if os.path.exists(os.path.join(d3, "meta.json")):
        bulgular.append("SEMA UYDURMA: haritalanamaz detail.json icin meta.json yazildi")
    return bulgular


VAKALAR = [
    ("A yazim dususu GURULTULU", vaka_a_yazim_dususu_gurultulu),
    ("B saglikli kosum yesil", vaka_b_saglikli_kosum_yesil),
    ("C rc sozlesmesi (gercek __main__)", vaka_c_rc_sozlesmesi),
    ("D geri doldurma EZMEZ + sema durust", vaka_d_geridoldurma_ezmez),
]

MUTANTLAR = [
    ("M1 sessiz yutma geri geldi", "thing-hazirla.py",
     """        except Exception as e:
            sys.stderr.write("=== %s === HATA: meta.json YAZILAMADI (%s: %s) -> %s\\n"
                             % (tid, type(e).__name__, e, mp))
            basarisiz.append(tid)""",
     """        except Exception:
            pass""",
     "A yazim dususu GURULTULU"),
    ("M2 rc wiring silindi", "thing-hazirla.py",
     """    if _basarisiz:
        sys.stderr.write("HAL=META-YAZILAMADI id=%s\\n" % ",".join(_basarisiz))
        sys.exit(1)""",
     "    pass",
     "C rc sozlesmesi (gercek __main__)"),
    ("M3 idempotens kapisi silindi", "thing-meta-geridoldur.py",
     """        if os.path.exists(mp):
            rapor.append((tid, ATLA_VAR, "")); continue""",
     "        pass",
     "D geri doldurma EZMEZ + sema durust"),
]


def main():
    hata = 0
    with tempfile.TemporaryDirectory(prefix="k400-taban-") as taban:
        t = izole_agac(taban)
        print("TABAN (mutantsiz, izole kopya):")
        taban_sonuc = {}
        for ad, fn in VAKALAR:
            b = fn(t)
            taban_sonuc[ad] = b
            print("  %-38s %s" % (ad, "GECTI" if not b else "KIRMIZI: " + "; ".join(b)))
            if b:
                hata = 1
    if hata:
        print("\nTABAN KIRMIZI -> mutant kosumu ANLAMSIZ (bkz taban-kirmizisi-nobetciyi-susturur)")
        return 1

    print("\nMUTANTLAR (her biri kendi vakasini OLDURMELI):")
    for ad, dosya, eski, yeni, hedef_vaka in MUTANTLAR:
        with tempfile.TemporaryDirectory(prefix="k400-mutant-") as taban:
            t = izole_agac(taban)
            if not mutasyon(t, dosya, eski, yeni):
                print("  %-38s OLCULEMEDI: capa bulunamadi (%s)" % (ad, dosya))
                hata = 1
                continue
            fn = dict(VAKALAR)[hedef_vaka]
            b = fn(t)
            if b:
                print("  %-38s OLDU (vaka kirmizi yandi) <- %s" % (ad, hedef_vaka))
            else:
                print("  %-38s HAYATTA! vaka '%s' mutanti GORMEDI" % (ad, hedef_vaka))
                hata = 1
    print("\nSONUC:", "GECTI" if not hata else "KIRMIZI")
    return hata


if __name__ == "__main__":
    sys.exit(main())
