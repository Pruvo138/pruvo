#!/usr/bin/env python3
"""ID-rename yolunun 6 iddiali kabul testi ve 5 oldurucu mutanti."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KOD_KILIDI = os.path.join(TOOLS, "mimar-kod-kilidi.py")
KIMLIK = os.path.join(TOOLS, "mimar_kimlik.py")
GUARD = os.path.join(TOOLS, "urunler-guard.py")
DUZELT = os.path.join(TOOLS, "duzelt.py")
HEDEF = "/Users/okan/dev/pruvo/index.html"
MOTOR_ENV = "PRUVO_ISCI_KOSUMU"


def _modul(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _hook(kod_kilidi, kimlik_yolu, motor_yok=False, motor=None):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop(MOTOR_ENV, None)
    if not motor_yok:
        env[MOTOR_ENV] = motor if motor is not None else ""
    # Mutant kopyasinda importun ayni dizindeki ortak kaynaktan gelmesini saglar.
    env["PYTHONPATH"] = os.path.dirname(kimlik_yolu)
    payload = json.dumps({"tool_input": {"file_path": HEDEF}})
    return subprocess.run([sys.executable, kod_kilidi], input=payload, text=True,
                          capture_output=True, env=env, check=False)


def _deny(p):
    return '"permissionDecision": "deny"' in p.stdout


def _allow(p):
    return not _deny(p) and "allow ISCI" in p.stderr


def _yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def _duzelt_yapilandir(modul, kok):
    modul.ROOT = kok
    modul.URUNLER = os.path.join(kok, "urunler.json")
    modul.KAYNAKLAR = os.path.join(kok, ".urun-kaynaklari.json")
    modul.LOCK = os.path.join(kok, ".urunler.lock")
    modul.MANIFEST = os.path.join(kok, ".urunler-duzelt-izin.json")
    modul.MANIFEST_SIL = os.path.join(kok, ".urunler-sil-izin.json")
    modul.MANIFEST_ID_RENAME = os.path.join(kok, ".urunler-id-rename-izin.json")
    modul.LOG = os.path.join(kok, ".urunler-guard.log")


def _guard_yapilandir(modul, kok, head):
    modul.ROOT = kok
    modul.URUNLER = os.path.join(kok, "urunler.json")
    modul.LOCK = os.path.join(kok, ".urunler.lock")
    modul.MANIFEST = os.path.join(kok, ".urunler-duzelt-izin.json")
    modul.MANIFEST_SIL = os.path.join(kok, ".urunler-sil-izin.json")
    modul.MANIFEST_ID_RENAME = os.path.join(kok, ".urunler-id-rename-izin.json")
    modul.LOG = os.path.join(kok, ".urunler-guard.log")
    modul._merge_head = lambda: None
    modul._katalog = lambda ref: ("var", copy.deepcopy(head))
    modul._git = lambda *args: (0, b"")


def _ornek(uid="eski-id"):
    return {"id": uid, "kategori": "Ev", "marka": [], "baslik": "Ornek",
            "aciklama": "Ornek parca", "fiyat": "100 TL", "gorseller": []}


def _rename_sonucu(guard_yolu=GUARD):
    with tempfile.TemporaryDirectory(prefix="pruvo-id-rename-") as kok:
        head = [_ornek()]
        _yaz(os.path.join(kok, "urunler.json"), head)
        _yaz(os.path.join(kok, ".urun-kaynaklari.json"),
             {"eski-id": {"kaynak_id": "ornek-1"}})
        duzelt = _modul("duzelt_id_test", DUZELT)
        _duzelt_yapilandir(duzelt, kok)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = duzelt._id_yeniden_adlandir("eski-id", "yeni-id")
        guard = _modul("guard_id_test", guard_yolu)
        _guard_yapilandir(guard, kok, head)
        with contextlib.redirect_stderr(io.StringIO()):
            guard_rc = guard.heal("test")
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(kok, ".urun-kaynaklari.json"), encoding="utf-8") as f:
            kaynaklar = json.load(f)
        ids = [p.get("id") for p in urunler]
        return (rc == 0 and guard_rc == "tamam" and ids == ["yeni-id"]
                and "eski-id" not in kaynaklar and "yeni-id" in kaynaklar)


def _silme_yakalandi(guard_yolu=GUARD):
    with tempfile.TemporaryDirectory(prefix="pruvo-id-silme-") as kok:
        head = [_ornek()]
        _yaz(os.path.join(kok, "urunler.json"), [])
        guard = _modul("guard_silme_test", guard_yolu)
        _guard_yapilandir(guard, kok, head)
        with contextlib.redirect_stderr(io.StringIO()):
            guard.heal("test")
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        return [p.get("id") for p in urunler] == ["eski-id"]


def _ascii_disi_reddedildi():
    with tempfile.TemporaryDirectory(prefix="pruvo-id-ascii-") as kok:
        head = [_ornek()]
        yol = os.path.join(kok, "urunler.json")
        _yaz(yol, head)
        once = open(yol, "rb").read()
        duzelt = _modul("duzelt_ascii_test", DUZELT)
        _duzelt_yapilandir(duzelt, kok)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = duzelt._id_yeniden_adlandir("eski-id", "yeni-ölcu")
        sonra = open(yol, "rb").read()
        return rc != 0 and once == sonra and not os.path.exists(duzelt.MANIFEST_ID_RENAME)


def iddialar():
    return [
        ("A1", _allow(_hook(KOD_KILIDI, KIMLIK, motor="deepseek-flash"))),
        ("A2", _deny(_hook(KOD_KILIDI, KIMLIK, motor_yok=True))),
        ("A3", _deny(_hook(KOD_KILIDI, KIMLIK, motor=""))
         and _deny(_hook(KOD_KILIDI, KIMLIK, motor="bilinmeyen"))),
        ("A4", _rename_sonucu()),
        ("A5", _silme_yakalandi()),
        ("A6", _ascii_disi_reddedildi()),
    ]


def _metin_mutanti(kaynak, eski, yeni, hedef):
    metin = open(kaynak, encoding="utf-8").read()
    if eski not in metin:
        raise RuntimeError("mutant capasi bulunamadi: %s" % eski)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(metin.replace(eski, yeni, 1))


def mutantlar():
    sonuc = []
    with tempfile.TemporaryDirectory(prefix="pruvo-id-mutant-") as kok:
        kilit = os.path.join(kok, "mimar-kod-kilidi.py")
        kimlik = os.path.join(kok, "mimar_kimlik.py")
        shutil.copy2(KOD_KILIDI, kilit)

        _metin_mutanti(KIMLIK, "if motor in ISCI_MOTORLARI:",
                       "if False and motor in ISCI_MOTORLARI:", kimlik)
        sonuc.append(("M1", 0 if _allow(_hook(kilit, kimlik, motor="deepseek-flash")) else 1))

        shutil.copy2(KIMLIK, kimlik)
        _metin_mutanti(KOD_KILIDI, 'if kimlik(girdi) == "ISCI":', "if True:", kilit)
        sonuc.append(("M2", 0 if _deny(_hook(kilit, kimlik, motor_yok=True)) else 1))

        shutil.copy2(KOD_KILIDI, kilit)
        _metin_mutanti(KIMLIK, "if motor in ISCI_MOTORLARI:",
                       "if motor is not None:", kimlik)
        sonuc.append(("M3", 0 if _deny(_hook(kilit, kimlik, motor="bilinmeyen")) else 1))

        mutant_guard = os.path.join(kok, "urunler-guard-m4.py")
        _metin_mutanti(GUARD, "if uid in id_rename:\n            continue",
                       "if False and uid in id_rename:\n            continue", mutant_guard)
        sonuc.append(("M4", 0 if _rename_sonucu(mutant_guard) else 1))

        mutant_guard = os.path.join(kok, "urunler-guard-m5.py")
        _metin_mutanti(GUARD, "        silinen.append(uid)\n",
                       "        pass  # MUTANT: gercek silmeyi yakalama\n", mutant_guard)
        sonuc.append(("M5", 0 if _silme_yakalandi(mutant_guard) else 1))
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true")
    args = ap.parse_args()
    if args.mutasyon:
        sonuclar = mutantlar()
        for ad, rc in sonuclar:
            print("%s rc=%d %s" % (ad, rc, "KIRMIZI" if rc else "YAKALANMADI"))
        oldurulen = sum(1 for _ad, rc in sonuclar if rc != 0)
        print("SONUC: %d/%d mutant OLDURULDU" % (oldurulen, len(sonuclar)))
        return 0 if oldurulen == len(sonuclar) else 1

    sonuclar = iddialar()
    for ad, gecti in sonuclar:
        print("%s: %s" % (ad, "GECTI" if gecti else "KALDI"))
    gecen = sum(1 for _ad, gecti in sonuclar if gecti)
    print("SONUC: %d/%d iddia GECTI" % (gecen, len(sonuclar)))
    return 0 if gecen == len(sonuclar) else 1


if __name__ == "__main__":
    sys.exit(main())
