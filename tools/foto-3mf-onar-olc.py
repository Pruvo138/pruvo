#!/usr/bin/env python3
"""FOTO 3MF ONARIM OLCUMU — saglayici renk 3MF'ini TeKiN koprusuyle onarip pruvo'nun KENDI ④ olcusuyle olcer.

NEDEN: figur ④ saglayici 3MF'i manifold-disi (ORNEK-9ba97f662e3f: acik kenar 27, tekrarli yonlu kenar 4350).
TeKiN `uc_mf_onar.py` koprusunu yazdi (dal tekin/3mf-onarim). Bu arac koprunun ciktisini KOSUCUDAN BAGIMSIZ
olarak `foto-ornek-uc-uca.py::uc_mf_olc` ile olcer — ④'un sizdirmaz + eksen kollari. Salt okur: R2'ye YAZMAZ,
D1'e dokunmaz, gecici dizin sonunda silinir.

Kullanim: python3 tools/foto-3mf-onar-olc.py --ornek ORNEK-9ba97f662e3f --tur figur [--kopru-ref 297286b]
Cikis: son satir `ONARIM_OLC tur=.. ornek=.. once=<s>/<n> sonra=<s>/<n> uzun=<mm> hedef=<mm> eksen=<0|1> kopru_rc=<n> HUKUM=<HAZIR|KIRMIZI>`
rc 0 HAZIR · 1 KIRMIZI · 2 girdi/ortam hatasi.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JEN = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
KOPRU_YOL = "jeneratorler/foto/uc_mf_onar.py"


def uu_modul():
    sys.dont_write_bytecode = True
    s = importlib.util.spec_from_file_location("foto_uu", os.path.join(KOK, "tools", "foto-ornek-uc-uca.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def tarama(uu):
    """Onizlemedeki TUM 'hazir' ORNEK satirlarinin model.3mf'ine koprunun TEK DOSYA `--olc`'unu kosar —
    plaket/sehir/D kollarina ayni kapiyi baglamadan ONCE: bugun HAZIR olan hangi tur kapidan gecemez?
    Son satir `TARAMA toplam=<n> gecti=<g> kirmizi=<k> hata=<h>`; rc 0 hepsi gecti · 1 kirmizi var · 2 ortam."""
    kopru = os.path.join(JEN, KOPRU_YOL)
    if not os.path.isfile(kopru):
        print("HATA kopru yok: %s" % kopru)
        return 2
    bulut = uu.Bulut(*uu.hedef_adlari())
    satir = bulut.sql("SELECT siparis_no, kalem, tur FROM foto_uretim WHERE asama = 'hazir' AND siparis_no LIKE "
                      "'ORNEK-%' ORDER BY tur, guncel DESC")
    gorulen, say = set(), {"gecti": 0, "kirmizi": 0, "hata": 0}
    gecici = tempfile.mkdtemp(prefix="foto-tarama-")
    try:
        for r in satir:
            if r["tur"] in gorulen:
                continue  # tur basina en yeni ornek
            gorulen.add(r["tur"])
            yol = os.path.join(gecici, "%s.3mf" % r["tur"])
            if not bulut.al("foto/%s/%s/model.3mf" % (r["siparis_no"], r["kalem"]), yol):
                say["hata"] += 1
                print("TUR %-10s %s HATA r2-get" % (r["tur"], r["siparis_no"]))
                continue
            p = subprocess.run([sys.executable, kopru, "--olc", yol], capture_output=True, text=True, timeout=900)
            try:
                kusur = ",".join(json.loads(p.stdout).get("kabul_kusurlari") or [])
            except ValueError:
                kusur = ((p.stderr or "").strip().splitlines() or ["?"])[-1][:120]
            kova = "gecti" if p.returncode == 0 else ("kirmizi" if p.returncode == 1 else "hata")
            say[kova] += 1
            print("TUR %-10s %s %s rc=%d %s" % (r["tur"], r["siparis_no"], kova.upper(), p.returncode, kusur))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print("TARAMA toplam=%d gecti=%d kirmizi=%d hata=%d" % (len(gorulen), say["gecti"], say["kirmizi"], say["hata"]))
    return 0 if say["kirmizi"] == say["hata"] == 0 else (2 if say["hata"] else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tarama", action="store_true", help="tum hazir ORNEK'lerde kopru --olc (salt okur)")
    ap.add_argument("--ornek", help="ORNEK-<is12> (onizleme R2 foto/<ornek>/0/model.3mf)")
    ap.add_argument("--tur", help="manifest tur kodu (hedef olcu + tolerans)")
    ap.add_argument("--kopru-ref", default="", help="kopru git ref'i (bos = jenerator calisma agaci)")
    a = ap.parse_args(argv)
    uu = uu_modul()
    if a.tarama:
        return tarama(uu)
    if not a.ornek or not a.tur:
        print("HATA --ornek ve --tur gerekli (ya da --tarama)")
        return 2
    man = uu.manifest_oku()
    tur = {t["kod"]: t for t in man["turler"]}.get(a.tur)
    if not tur:
        print("HATA tur yok: %s" % a.tur)
        return 2
    hedef = float(uu.olcu_sec(tur) or 0)
    tol = uu.TOLERANS.get(tur.get("motor"), 0)
    gecici = tempfile.mkdtemp(prefix="foto-onar-")
    try:
        kopru = os.path.join(gecici, "uc_mf_onar.py")
        if a.kopru_ref:
            p = subprocess.run(["git", "-C", JEN, "show", "%s:%s" % (a.kopru_ref, KOPRU_YOL)], capture_output=True)
            if p.returncode != 0:
                print("HATA kopru ref okunamadi: %s" % p.stderr.decode()[-200:])
                return 2
            open(kopru, "wb").write(p.stdout)
        else:
            shutil.copy(os.path.join(JEN, KOPRU_YOL), kopru)
        bulut = uu.Bulut(*uu.hedef_adlari())
        girdi, cikti = os.path.join(gecici, "girdi.3mf"), os.path.join(gecici, "cikti.3mf")
        if not bulut.al("foto/%s/0/model.3mf" % a.ornek, girdi):
            print("HATA r2-get foto/%s/0/model.3mf" % a.ornek)
            return 2
        once = uu.uc_mf_olc(girdi)
        p = subprocess.run([sys.executable, kopru, girdi, cikti], capture_output=True, text=True, timeout=900)
        print("KOPRU rc=%d %s" % (p.returncode, (p.stdout or p.stderr).strip().splitlines()[-1:]))
        sonra = uu.uc_mf_olc(cikti) if p.returncode == 0 and os.path.isfile(cikti) else None
        k = subprocess.run([sys.executable, kopru, "--olc", girdi, cikti], capture_output=True, text=True,
                           timeout=900) if sonra else None
        if k:
            print("KOPRU_OLC rc=%d %s" % (k.returncode, k.stdout.strip().splitlines()[-1:]))
        sd = bool(sonra) and sonra["sizdirmaz_nesne"] == sonra["nesne"] and sonra["nesne"] > 0
        eksen = bool(sonra) and abs(sonra["uzun"] - hedef) <= hedef * tol + 1e-9
        hukum = sd and eksen and p.returncode == 0
        print("ONARIM_OLC tur=%s ornek=%s once=%s/%s sonra=%s/%s uzun=%s hedef=%g±%g%% eksen=%d kopru_rc=%d "
              "kopru_olc_rc=%s HUKUM=%s" % (
                  a.tur, a.ornek, once["sizdirmaz_nesne"] if once else 0, once["nesne"] if once else 0,
                  sonra["sizdirmaz_nesne"] if sonra else 0, sonra["nesne"] if sonra else 0,
                  sonra["uzun"] if sonra else None, hedef, tol * 100, 1 if eksen else 0, p.returncode,
                  k.returncode if k else "-", "HAZIR" if hukum else "KIRMIZI"))
        return 0 if hukum else 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
