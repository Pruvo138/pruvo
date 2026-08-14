#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K71 kabul: D1 lease'i makineler-arasi yazicilari dislar (offline SQLite)."""
import argparse
import ast
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.path.join(KOK, "tools", "d1-sync.py")
SPEC = importlib.util.spec_from_file_location("d1_sync_dagitik_kilit", YOL)
D1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D1)


def sqlite_bagla(db):
    """Uretim fonksiyonlarini ortak SQLite dosyasina bagla; karar kodu taklit edilmez."""
    def dosya_calistir(sql):
        con = sqlite3.connect(db, timeout=3)
        try:
            once = con.total_changes
            con.executescript(sql)
            con.commit()
            return con.total_changes - once, 0
        finally:
            con.close()

    def sorgu(sql):
        con = sqlite3.connect(db, timeout=3)
        con.row_factory = sqlite3.Row
        try:
            satirlar = [dict(r) for r in con.execute(sql).fetchall()]
            return [{"results": satirlar,
                     "meta": {"rows_read": len(satirlar), "rows_written": 0}}]
        finally:
            con.close()

    D1.dosya_calistir = dosya_calistir
    D1.sorgu = sorgu


def alt(db, yerel_kilit, sahip, tut, hazir):
    sqlite_bagla(db)
    yerel = D1.yazici_kilidi_al(yerel_kilit)
    dagitik = None
    try:
        dagitik = D1.dagitik_kilit_al(sahip)
        if hazir:
            with open(hazir, "w", encoding="utf-8") as f:
                json.dump({"sahip": sahip}, f)
        if tut:
            time.sleep(tut)
        return 0
    except SystemExit as e:
        print(e.code)
        return 23
    finally:
        if dagitik:
            D1.dagitik_kilit_birak(dagitik)
        D1.yazici_kilidi_birak(yerel)


def ana_test():
    gecen = 0
    toplam = 6
    with tempfile.TemporaryDirectory(prefix="pruvo-k71-") as tmp:
        db = os.path.join(tmp, "ortak-d1.sqlite")
        kilit_a = os.path.join(tmp, "makine-a.lock")
        kilit_b = os.path.join(tmp, "makine-b.lock")
        hazir = os.path.join(tmp, "a-hazir.json")
        for yol in (kilit_a, kilit_b):
            with open(yol, "w", encoding="utf-8"):
                pass

        # FARKLI yerel inode'lar: flock makineler-arasi yarisi engelleyemez.
        a = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--alt", db, kilit_a,
             "makine-a", "1.5", hazir], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        son = time.monotonic() + 5
        while not os.path.exists(hazir) and time.monotonic() < son:
            time.sleep(0.02)
        if os.path.exists(hazir):
            gecen += 1
            print("GECTI makine-A farkli yerel flock + ortak D1 lease'ini aldi")
        else:
            print("KALDI makine-A lease alamadi")

        b = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--alt", db, kilit_b,
             "makine-b", "0", ""], capture_output=True, text=True, timeout=5)
        b_metin = b.stdout + b.stderr
        if b.returncode == 23 and "MAKINELER-ARASI" in b_metin:
            gecen += 1
            print("GECTI makine-B'nin yerel flock'u bosken D1 lease'i fail-closed reddetti")
        else:
            print("KALDI ikinci makine reddedilmedi rc=%d cikti=%r"
                  % (b.returncode, b_metin))

        a_out, a_err = a.communicate(timeout=5)
        if a.returncode == 0:
            gecen += 1
            print("GECTI ilk yazici normal cikista yalniz kendi lease'ini birakti")
        else:
            print("KALDI ilk yazici rc=%d cikti=%r" % (a.returncode, a_out + a_err))

        c = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--alt", db, kilit_b,
             "makine-b", "0", ""], capture_output=True, text=True, timeout=5)
        if c.returncode == 0 and "dagitik yazici kilidi ALINDI" in c.stdout:
            gecen += 1
            print("GECTI ilk yazici bitince diger makine lease'i alabildi")
        else:
            print("KALDI lease serbest kalmadi rc=%d cikti=%r"
                  % (c.returncode, c.stdout + c.stderr))

        # Crash kalintisi sonsuz kilit degildir: suresi dolmus sahip atomik devralinir.
        con = sqlite3.connect(db)
        con.execute("INSERT OR REPLACE INTO senkron_kilit(ad,sahip,sona_erme) VALUES (?,?,?)",
                    (D1.DAGITIK_KILIT_ADI, "olen-kosucu", 1))
        con.commit()
        con.close()
        d = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--alt", db, kilit_a,
             "makine-c", "0", ""], capture_output=True, text=True, timeout=5)
        if d.returncode == 0 and "dagitik yazici kilidi ALINDI" in d.stdout:
            gecen += 1
            print("GECTI suresi dolmus crash lease'i atomik devralindi")
        else:
            print("KALDI suresi dolmus lease devralinamadi rc=%d cikti=%r"
                  % (d.returncode, d.stdout + d.stderr))

        # Kablo capasi: cekirdek dogru olsa bile main onu cagirmiyorsa koruma oludur.
        with open(YOL, encoding="utf-8") as f:
            agac = ast.parse(f.read())
        main_dugum = next(n for n in agac.body
                          if isinstance(n, ast.FunctionDef) and n.name == "main")
        cagri_adlari = {n.func.id for n in ast.walk(main_dugum)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        finally_birak = any(
            isinstance(n, ast.Try)
            and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                    and x.func.id == "dagitik_kilit_birak"
                    for x in ast.walk(ast.Module(body=n.finalbody, type_ignores=[])))
            for n in ast.walk(main_dugum))
        ana_dugum = next(n for n in agac.body
                         if isinstance(n, ast.FunctionDef) and n.name == "_main")
        yenile_var = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                         and n.func.id == "dagitik_kilit_yenile"
                         for n in ast.walk(ana_dugum))
        if {"dagitik_kilit_al", "yazici_kilidi_al"} <= cagri_adlari \
                and finally_birak and yenile_var:
            gecen += 1
            print("GECTI main kablosu: yerel+dagitik al, finally birak, yazma-oncesi yenile")
        else:
            print("KALDI main kilit kablosu al=%r finally=%r yenile=%r"
                  % (sorted(cagri_adlari), finally_birak, yenile_var))

    print("SONUC: %d/%d" % (gecen, toplam))
    return 0 if gecen == toplam else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt", nargs=5, metavar=("DB", "YEREL", "SAHIP", "TUT", "HAZIR"))
    a = ap.parse_args()
    if a.alt:
        raise SystemExit(alt(a.alt[0], a.alt[1], a.alt[2], float(a.alt[3]), a.alt[4]))
    raise SystemExit(ana_test())
