#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K309 DILIM-2A — MENZIL_DISI kalemlerin `kabul:` alanini KALEM duzeyinde olcer.

Dilim-1 `KABUL_VAR=31` sayisini BLOK duzeyinde uretmisti (bir blokta birden cok id
varsa hepsi sayiliyordu, ayrica serbest cumleyle yazilmis "kabul: ..." metinleri de
sayiliyordu). Bu betik ayni sayiyi KALEM duzeyine indirir:

  * `kabul:` alani MAKINE-OKUNUR sayilir ancak ve ancak alan bir KOMUT JETONU ile
    baslarsa (`python3` ya da `node`) — defterin kendi kurali:
    "komut jetonuyla baslamayan alan bos kabul edilir".
  * Alan, ayni blok icinde KENDISINDEN ONCE gelen SON id'ye baglanir (okuma sirasi).
    Onunde id yoksa blogun ILK id'sine baglanir.

Cikti: ham JSON + insan-okunur dokum. Sayilari dosyadan `grep`/`cat` ile okuyun;
betigin kendi prozasi kanit degildir.
"""
import io
import json
import os
import re
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "kalem_senkron_kapisi", os.path.join(BURASI, "kalem-senkron-kapisi.py"))
KSK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(KSK)

MEMORY = os.path.expanduser("~/.claude/projects/-Users-okan-dev-pruvo/memory")
# 🔴 KANONIK ANA CHECKOUT — worktree DEGIL. `DEVAM-ARSIV.md` git DISIDIR ve linked
# worktree'de HIC YOKTUR; betik worktree'den kosarsa o duzlem sessizce bos olcuulur
# ([[worktree-izlenmeyen-dosya-hukmu-degistirir]]). Duzlem yolu agactan TURETILMEZ.
REPO = "/Users/okan/dev/pruvo"
os.environ.setdefault("PRUVO_KALEM_DEVAM", os.path.join(REPO, "DEVAM.md"))

DUZLEMLER = [
    ("DEVAM.md", os.path.join(REPO, "DEVAM.md")),
    ("DEVAM-ARSIV.md", os.path.join(REPO, "DEVAM-ARSIV.md")),
    ("kutu", os.path.join(MEMORY, "mimar-posta-kutusu.md")),
    ("kutu-arsiv", os.path.join(MEMORY, "mimar-posta-kutusu-arsiv.md")),
]

# MAKINE-OKUNUR `kabul:` alani: komut jetonuyla BASLAR.
# Kabuk metakarakteri tasiyan alanlar AYRICA isaretlenir (defter kurali: yok).
KOMUT_RE = re.compile(
    r"kabul\s*:\s*`?\s*((?:python3|node)\s+[^\n`|]+)", re.I)
ID_RE = re.compile(r"\bK(\d+)")


def _oku(yol):
    with io.open(yol, encoding="utf-8", errors="replace") as f:
        return f.read()


def _blok_indeksi(metin):
    """[(bas, bit)] — kapinin kendi blok bolumlemesiyle AYNI (tek kaynak)."""
    return [(b, s) for b, s, _t in KSK._bloklar(metin)]


def tara(etiket, yol, menzil_disi):
    """Bir duzlemde makine-okunur `kabul:` alanlarini bulup id'ye baglar."""
    if not os.path.exists(yol):
        return {"duzlem": etiket, "yol": yol, "OKUNAMADI": True, "bulgular": []}
    metin = _oku(yol)
    bloklar = _blok_indeksi(metin)
    # Hizli arama icin blok sinirlarini sirali tut
    bulgular = []
    for m in KOMUT_RE.finditer(metin):
        mutlak = m.start()
        # Bu offset hangi blokta?
        blok_bas, blok_bit = 0, len(metin)
        for b, s in bloklar:
            if b <= mutlak < s:
                blok_bas, blok_bit = b, s
                break
        blok = metin[blok_bas:blok_bit]
        yerel = mutlak - blok_bas
        # Blok icinde, alandan ONCE gelen SON id
        sahip = None
        for im in ID_RE.finditer(blok):
            if im.start() < yerel:
                sahip = "K" + im.group(1)
            else:
                break
        if sahip is None:
            im = ID_RE.search(blok)
            sahip = ("K" + im.group(1)) if im else None
        komut = m.group(1).strip().rstrip("`").strip()
        bulgular.append({
            "sahip_id": sahip,
            "komut": komut,
            "satir": metin.count("\n", 0, mutlak) + 1,
            "menzil_disi_mi": bool(sahip and sahip in menzil_disi),
            "metakarakter": bool(re.search(r"[;&|><$(){}]", komut)),
            "blok_metni": blok.strip(),
        })
    return {"duzlem": etiket, "yol": yol, "OKUNAMADI": False, "bulgular": bulgular}


def main():
    o = KSK.olc()
    menzil_disi = set(o["menzil_disi_ids"])
    sonuc = {
        "menzil_disi_sayi": o["menzil_disi"],
        "menzil_disi_ids": o["menzil_disi_ids"],
        "kaynak_dogrusu_satir": o["kaynak_dogrusu_satir"],
        "kaynak_dogrusu_benzersiz_id": o["kaynak_dogrusu_benzersiz_id"],
        "devam_md_benzersiz_id": o["devam_md_benzersiz_id"],
        "duzlemler": [],
    }
    kalem_kabul = {}   # id -> [ {duzlem, komut, satir} ]
    okunamayan = []
    for etiket, yol in DUZLEMLER:
        d = tara(etiket, yol, menzil_disi)
        if d["OKUNAMADI"]:
            okunamayan.append("%s (%s)" % (etiket, yol))
        sonuc["duzlemler"].append({
            "duzlem": etiket, "OKUNAMADI": d["OKUNAMADI"],
            "toplam_makine_kabul": len(d["bulgular"]),
            "menzil_disi_isabet": sum(1 for b in d["bulgular"] if b["menzil_disi_mi"]),
        })
        for b in d["bulgular"]:
            if not b["menzil_disi_mi"]:
                continue
            kalem_kabul.setdefault(b["sahip_id"], []).append({
                "duzlem": etiket, "komut": b["komut"], "satir": b["satir"],
                "metakarakter": b["metakarakter"], "blok_metni": b["blok_metni"],
            })

    sonuc["KALEM_DUZEYI_KABUL_VAR"] = len(kalem_kabul)
    sonuc["KALEM_DUZEYI_KABUL_YOK"] = o["menzil_disi"] - len(kalem_kabul)
    sonuc["kalem_kabul"] = kalem_kabul

    # Dilim-1'in BLOK duzeyi sayisini AYNI kosumda yeniden uret (kiyas icin).
    blok_duzeyi = sum(1 for kid, v in o["menzil_disi_kayit"].items() if v["kabul_var"])
    sonuc["BLOK_DUZEYI_KABUL_VAR_dilim1_yontemi"] = blok_duzeyi

    ham = os.path.join(BURASI, "k309d2-olcum-ham.json")
    with io.open(ham, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    # Rapor AYNI ANDA dosyaya dokulur — isci prozasina degil bu dosyaya bakilir.
    rapor_yolu = os.path.join(BURASI, "k309d2-olcum-rapor.txt")
    _rf = io.open(rapor_yolu, "w", encoding="utf-8")

    def yaz(satir=""):
        sys.stdout.write(satir + "\n")
        _rf.write(satir + "\n")

    print = yaz  # noqa: A001

    print("=== K309 DILIM-2A KALEM DUZEYI OLCUM ===")
    print("MENZIL_DISI=%d" % o["menzil_disi"])
    print("BLOK_DUZEYI_KABUL_VAR(dilim1 yontemi, UST SINIR)=%d" % blok_duzeyi)
    print("KALEM_DUZEYI_KABUL_VAR=%d" % len(kalem_kabul))
    print("KALEM_DUZEYI_KABUL_YOK=%d" % (o["menzil_disi"] - len(kalem_kabul)))
    print("--- duzlem kirilimi ---")
    for d in sonuc["duzlemler"]:
        print("DUZLEM %-16s makine_kabul_toplam=%-4d menzil_disi_isabet=%-3d okunamadi=%s"
              % (d["duzlem"], d["toplam_makine_kabul"], d["menzil_disi_isabet"],
                 d["OKUNAMADI"]))
    print("--- KALEM DUZEYI ISABETLER ---")
    for kid in sorted(kalem_kabul, key=lambda k: int(k[1:])):
        for v in kalem_kabul[kid]:
            print("KALEM %-6s duzlem=%-14s satir=%-6d meta=%-5s komut=%s"
                  % (kid, v["duzlem"], v["satir"], v["metakarakter"], v["komut"]))
    print("HAM=%s" % ham)
    print("RAPOR=%s" % rapor_yolu)
    # 🔴 FAIL-CLOSED: bir duzlem okunamadiysa SAYI EKSIKTIR. Okunamayan duzlem
    # YESIL DEGILDIR — sifir-disi rc ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
    if okunamayan:
        print("OLCULEMEDI — su duzlem(ler) OKUNAMADI: %s" % "; ".join(okunamayan))
        print("BITIS rc=3 (eksik duzlem = eksik sayi, yesil DEGIL)")
        _rf.close()
        return 3
    print("BITIS rc=0")
    _rf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
