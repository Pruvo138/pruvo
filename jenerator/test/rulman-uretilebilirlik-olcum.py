#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RULMAN URETILEBILIRLIK OLCUMU — semadaki `kisitlar` katsayilarinin DAYANAGI.

NEDEN VAR: olcuye-ozel-rulman semasindaki genislik alt siniri iki "sihirli" sayi
tasir (0,95/3 katsayisi ve bilya icin -0,24 payi). Bunlar TURETILMEDI, uretim
motoruna gercek render atilarak OLCULDU. Olcum yeniden uretilemezse katsayilar
bir sonraki muhendis icin dogrulanamaz bir iddiaya doner -> bu arac o olcumu
tekrar kosar. (Kapali form ANLATILMAZ, OLCULUR.)

OLCULEN KAPALI FORM (2026-08-03, 1600+ render, 0 ayrisma):
    eleman_capi = (dis_cap - ic_cap) / 3 * k     k: bilya 1,00 · makara 0,95 · tutmali 0,75
      makara  uretilir <=> eleman_capi <= genislik
      bilya   uretilir <=> eleman_capi <  genislik + 0,24
      tutmali uretilir <=> DAIMA
Ilan edilen izgaranin %33,9'u (43.085 / 126.945) motorda URETILEMEZ durumdaydi;
sema kapisi (jenerator/konfigurator.js kisitAltSinir) bunlari artik reddediyor.

Kullanim:
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py            # 120 set
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --set 400  # daha genis
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --sema-kapisi
        (semanin KABUL ettigi setleri atar; beklenen: 0 uretilemez)

FAIL-CLOSED: gizli uretim paketi ya da openscad yoksa OLCULEMEDI -> exit 3
("yesil" SAYILMAZ). Motor dosya adi/tedarikci bu dosyada ANILMAZ; eslem
dosyasindan okunur (public depoya sir girmez).
"""
import argparse
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
OLCULEMEDI = 3

K = {"bilya": 1.0, "makara": 0.95, "tutmali": 0.75}


def kapali_form(ic, dis, gen, eleman):
    """OLCULEN uretilebilirlik kurali (semadaki kisitlarin ikizi)."""
    cap = (dis - ic) / 3.0 * K[eleman]
    if eleman == "makara":
        return cap <= gen + 1e-9
    if eleman == "bilya":
        return cap < gen + 0.24 - 1e-9
    return True


def izg(mn, mx, ad):
    n = int(round((mx - mn) / ad))
    return [round(mn + i * ad, 6) for i in range(n + 1)]


def paket_yukle():
    """(server modulu, eslem_ailesi, scad_yolu) — yoksa OLCULEMEDI."""
    # Gizli paket gitignore'ludur -> WORKTREE'de bulunmaz. Ana checkout'u
    # gostermek icin PRUVO_ONIZLEME_DIR (yoksa bu deponun kendi dizini).
    derleyici = os.environ.get("PRUVO_ONIZLEME_DIR",
                               os.path.join(REPO, "onizleme", "derleyici"))
    server_yol = os.path.join(derleyici, "server.py")
    eslem_yol = os.path.join(derleyici, "eslem-ozel.json")
    motor_dir = os.environ.get("PRUVO_UYELIK_DIR",
                               os.path.join(REPO, ".uyelik-kodlar"))
    for yol in (server_yol, eslem_yol):
        if not os.path.exists(yol):
            print("OLCULEMEDI: gizli uretim paketi yok (%s). R2'deki paketten geri alin."
                  % os.path.basename(yol))
            sys.exit(OLCULEMEDI)
    spec = importlib.util.spec_from_file_location("onizleme_server", server_yol)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    eslem = json.load(io.open(eslem_yol, encoding="utf-8"))["aileler"]
    aile = eslem.get("olcuye-ozel-rulman")
    if not aile:
        print("OLCULEMEDI: uretim esleminde olcuye-ozel-rulman yok")
        sys.exit(OLCULEMEDI)
    scad = os.path.join(motor_dir, aile["scad"])
    if not os.path.exists(scad):
        print("OLCULEMEDI: uretim motoru .scad kaynagi yok (%s)" % motor_dir)
        sys.exit(OLCULEMEDI)
    return server, aile, scad


def openscad_yolu():
    sys.path.insert(0, TEST_DIR)
    import dogrula
    return dogrula.openscad_yolu()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=int, default=120)
    ap.add_argument("--tohum", type=int, default=4242)
    ap.add_argument("--sema-kapisi", action="store_true",
                    help="yalniz semanin KABUL ettigi setleri at (beklenen: 0 uretilemez)")
    a = ap.parse_args()

    server, aile, scad = paket_yukle()
    openscad = openscad_yolu()
    if not openscad:
        print("OLCULEMEDI: openscad bulunamadi")
        sys.exit(OLCULEMEDI)

    IC, DIS, GEN = izg(5, 20, .5), izg(28, 60, .5), izg(5, 15, .5)
    BOS, ELE, FL = izg(.1, .3, .05), list(K), ["yok", "var"]
    rnd = random.Random(a.tohum)
    setler = []
    while len(setler) < a.set:
        s = {"ic_cap": rnd.choice(IC), "dis_cap": rnd.choice(DIS),
             "genislik": rnd.choice(GEN), "eleman": rnd.choice(ELE),
             "bosluk": rnd.choice(BOS), "flans": rnd.choice(FL)}
        setler.append(s)

    if a.sema_kapisi:
        p = subprocess.run(
            ["node", "-e",
             "const K=require(process.argv[1]);const s=require(process.argv[2]);"
             "const fs=require('fs');const g=JSON.parse(fs.readFileSync(0,'utf8'));"
             "process.stdout.write(JSON.stringify(g.filter(x=>K.dogrula(s,x).gecerli)));",
             os.path.join(REPO, "jenerator", "konfigurator.js"),
             os.path.join(REPO, "jenerator", "urunler", "olcuye-ozel-rulman.json")],
            input=json.dumps(setler), capture_output=True, text=True)
        if p.returncode != 0:
            print("OLCULEMEDI: sema kapisi kosulamadi: %s" % p.stderr[:300])
            sys.exit(OLCULEMEDI)
        setler = json.loads(p.stdout)
        print("sema kapisindan GECEN set: %d" % len(setler))

    tmp = tempfile.mkdtemp(prefix="rulman-olcum-")
    ayrisma, uretilemez, ok = [], 0, 0
    for i, s in enumerate(setler):
        bayraklar, sebep = server.d_bayraklari(aile, s)
        if bayraklar is None:
            print("  [RET ] eslem kapsami disi: %s" % sebep)
            continue
        stl = os.path.join(tmp, "r%d.stl" % i)
        p = subprocess.run([openscad, "-o", stl, "--export-format", "binstl"] +
                           server.OPENSCAD_EK_BAYRAKLAR + bayraklar + [scad],
                           capture_output=True, timeout=600)
        h = p.stderr.decode("utf-8", "replace")
        gercek = (p.returncode == 0 and os.path.exists(stl))
        if gercek:
            ok += 1
        elif "ERROR: Assertion" in h or "assert" in h.lower():
            uretilemez += 1
        else:
            print("  [HATA] derleme: %s" % h.strip().splitlines()[-1][:120])
            sys.exit(OLCULEMEDI)
        tahmin = kapali_form(s["ic_cap"], s["dis_cap"], s["genislik"], s["eleman"])
        if tahmin != gercek:
            ayrisma.append((s, "kapali-form=%s" % tahmin, "motor=%s" % gercek))

    print("\nOLCUM: %d set | uretilir %d | uretilemez(422) %d" % (len(setler), ok, uretilemez))
    print("KAPALI FORM ile AYRISMA: %d" % len(ayrisma))
    for x in ayrisma[:10]:
        print("  ", x)
    if a.sema_kapisi:
        print("SEMA KAPISI HUKMU: kabul edilen setlerde uretilemez = %d (beklenen 0)"
              % uretilemez)
        sys.exit(1 if uretilemez else 0)
    sys.exit(1 if ayrisma else 0)


if __name__ == "__main__":
    main()
