#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rel-card halka seciminin sentetik kabul ve bellek-ici mutasyon bataryasi."""

import ast
import importlib.util
import os
import sys
import types


TOOLS = os.path.dirname(os.path.abspath(__file__))
BUILD_PATH = os.path.join(TOOLS, "build.py")


def modul_yukle(ad, kaynak=None):
    sys.path.insert(0, TOOLS)
    if kaynak is None:
        spec = importlib.util.spec_from_file_location(ad, BUILD_PATH)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[ad] = mod
        spec.loader.exec_module(mod)
        return mod
    mod = types.ModuleType(ad)
    mod.__file__ = BUILD_PATH
    mod.__package__ = ""
    sys.modules[ad] = mod
    exec(compile(kaynak, BUILD_PATH, "exec"), mod.__dict__)
    return mod


def urun(no, kategori="Otomobil", marka=None):
    return {
        "id": "urun-%03d" % no,
        "kategori": kategori,
        "marka": list(marka or []),
    }


def hedefler(secici, katalog):
    return {
        p["id"]: [x["id"] for x in secici(p, katalog)]
        for p in katalog
    }


def iddialar(secici):
    buyuk = [urun(i, marka=["A" if i < 12 else "B"]) for i in range(24)]
    kucuk = [urun(i, marka=["A"]) for i in range(5)]
    buyuk_hedef = hedefler(secici, buyuk)
    kucuk_hedef = hedefler(secici, kucuk)

    t1 = (all(len(v) == 8 for v in buyuk_hedef.values())
          and all(len(v) == 4 for v in kucuk_hedef.values()))
    t2 = all(pid not in rel for pid, rel in buyuk_hedef.items())
    t3 = all(len(rel) == len(set(rel)) for rel in buyuk_hedef.values())

    iki_yuz = [urun(i, marka=[]) for i in range(200)]
    iki_yuz_hedef = hedefler(secici, iki_yuz)
    link_alan = {hedef for rel in iki_yuz_hedef.values() for hedef in rel}
    t4 = len(link_alan) == 200

    marka_katalog = [urun(i, marka=["A"]) for i in range(12)]
    marka_katalog += [urun(100 + i, marka=["B"]) for i in range(12)]
    marka_hedef = hedefler(secici, marka_katalog)
    urun_marka = {p["id"]: p["marka"][0] for p in marka_katalog}
    t5 = all(all(urun_marka[hedef] == urun_marka[pid] for hedef in rel)
             for pid, rel in marka_hedef.items())
    t6 = hedefler(secici, buyuk) == hedefler(secici, buyuk)
    return [t1, t2, t3, t4, t5, t6]


def mutant_modul_yukle():
    with open(BUILD_PATH, encoding="utf-8") as f:
        kaynak = f.read()
    agac = ast.parse(kaynak)
    dugum = next(x for x in agac.body
                 if isinstance(x, ast.FunctionDef) and x.name == "rel_card_sec")
    satirlar = kaynak.splitlines(keepends=True)
    mutant = (
        "def rel_card_sec(p, all_products, limit=8):\n"
        "    pid = p[\"id\"]\n"
        "    kategori = p.get(\"kategori\")\n"
        "    return [x for x in all_products\n"
        "            if x.get(\"kategori\") == kategori and x[\"id\"] != pid][:limit]\n"
    )
    mutant_kaynak = "".join(satirlar[:dugum.lineno - 1])
    mutant_kaynak += mutant
    mutant_kaynak += "".join(satirlar[dugum.end_lineno:])
    return modul_yukle("pruvo_build_rel_card_mutant", mutant_kaynak)


def main():
    build = modul_yukle("pruvo_build_rel_card")
    sonuclar = iddialar(build.rel_card_sec)
    mutant = mutant_modul_yukle()
    mutant_sonuclar = iddialar(mutant.rel_card_sec)
    t7 = (not all(mutant_sonuclar)) and (not mutant_sonuclar[3])
    tumu = sonuclar + [t7]
    dusen = sum(not sonuc for sonuc in tumu)
    print("VAKA=7 DUSEN=%d" % dusen)
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
