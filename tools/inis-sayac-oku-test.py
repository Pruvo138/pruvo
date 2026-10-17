#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/inis-sayac-oku.py (D1 inis_sayac gunluk okuyucu).

KABUL SORUSU: "bu satiri silsem hangi vaka kirmizi yanar?"
Cevap her vaka/mutant icin yorumda. IKI kol:

  A) VAKALAR — araci DEGISTIRMEDEN sqlite fikstur uzerinde davranis olcer.
     Ag YOK, canli D1'e DOKUNMAZ.
  B) MUTANTLAR — araci IZOLE KOPYADA bozar, KIRMIZI yanmasini bekler.
     Kopya `tempfile.mkdtemp` altinda; gercek ev yoluna DOKUNULMAZ, silinen yalniz
     testin KENDI urettigi gecici dizindir (FILO DERSI 4 Eyl: yuk yikici olamaz).

Kosum (borusuz):  python3 tools/inis-sayac-oku-test.py

Son satir: KABUL <g>/8 MUTANT <m>/4  (YESIL icin 8/8 + 4/4; rc=0).
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True                            # hedef repoya __pycache__ yazma

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(ROOT, "tools", "inis-sayac-oku.py")

# 🔴 Tekil satir beklenen REGEX: alan sirasi ve n>=0 SABIT.
# Beklenen degerler asagidaki fiksturdan cikarildi (elle hesaplanmis, govde degisirse test yanar).
SATIR_RE = re.compile(
    r"^INIS gun=(?P<gun>\d{4}-\d{2}-\d{2})"
    r" UTM_FB=(?P<fb>\d+) UTM_IG=(?P<ig>\d+) UTM_G=(?P<g>\d+)"
    r" UTM_GEO=(?P<geo>\d+) UTM_DIGER=(?P<diger>\d+) TOPLAM=(?P<toplam>\d+)\s*$"
)


def _vt_kur(tmp, satirlar):
    """Fikstur sqlite olusturur. PRIMARY KEY (gun,kaynak,kampanya) ile birebir."""
    yol = os.path.join(tmp, "inis.db")
    conn = sqlite3.connect(yol)
    try:
        conn.executescript(
            "CREATE TABLE IF NOT EXISTS inis_sayac ("
            "gun TEXT NOT NULL, kaynak TEXT NOT NULL, "
            "kampanya TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (gun,kaynak,kampanya));"
        )
        conn.executemany(
            "INSERT OR REPLACE INTO inis_sayac (gun, kaynak, kampanya, n) "
            "VALUES (?, ?, ?, ?);",
            satirlar,
        )
        conn.commit()
    finally:
        conn.close()
    return yol


def _sqlite_olustur_bos(tmp):
    """Bos VT (V3 icin): tablo kurulu ama hic satir yok."""
    yol = os.path.join(tmp, "bos.db")
    conn = sqlite3.connect(yol)
    try:
        conn.executescript(
            "CREATE TABLE IF NOT EXISTS inis_sayac ("
            "gun TEXT NOT NULL, kaynak TEXT NOT NULL, "
            "kampanya TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (gun,kaynak,kampanya));"
        )
        conn.commit()
    finally:
        conn.close()
    return yol


# ── V1 fiksturu — karisik kaynaklar; sinif toplamlari birebir ───────────────
# google 12 (1+3+8)  · bing 3 (GEO)
# facebook 7 (1+6) + fb 4 + meta 5 = 16 (FB)
# instagram 2 + ig 9 = 11 (IG)
# tiktok 4 (DIGER)
# TOPLAM = 12+3+16+11+4 = 46
F1_SATIRLAR = [
    ("2026-10-17", "google",  "search-brand",     1),
    ("2026-10-17", "google",  "search-genel",     3),
    ("2026-10-17", "google",  "display",          8),
    ("2026-10-17", "bing",    "search-genel",     3),
    ("2026-10-17", "facebook","ret-lal",          1),
    ("2026-10-17", "facebook","ret-cat-101",      6),
    ("2026-10-17", "fb",      "awareness",        4),
    ("2026-10-17", "meta",    "ret-lal",          5),
    ("2026-10-17", "instagram","ret-cat-101",     2),
    ("2026-10-17", "ig",      "awareness",        9),
    ("2026-10-17", "tiktok",  "ugc",              4),
]
F1_BEK = {"fb": 16, "ig": 11, "g": 12, "geo": 3, "diger": 4, "toplam": 46}

# ── V2 fiksturu — baska gun satirlari var; gun=2026-10-17 icin sayilmaz ────
F2_SATIRLAR = F1_SATIRLAR + [
    ("2026-10-18", "google",  "search-brand",     99),
    ("2026-10-18", "facebook","ret-lal",          99),
    ("2026-10-18", "instagram","ret-cat-101",     99),
    ("2026-10-18", "bing",    "search-genel",     99),
    ("2026-10-18", "tiktok",  "ugc",              99),
]
# 2026-10-17 toplamlari = V1 ile birebir ayni (46).
F2_BEK = {"fb": 16, "ig": 11, "g": 12, "geo": 3, "diger": 4, "toplam": 46}


# ══════════════════════════════════════════════════════════════════════════════
# KOSUM
# ══════════════════════════════════════════════════════════════════════════════
def kos(arac, args=None, vt=None, gun=None):
    """Araci ALT SUREC olarak kosar; (rc, stdout+stderr) doner. rc BORUSUZ okunur."""
    cmd = [sys.executable, arac]
    if vt is not None:
        cmd += ["--vt", vt]
    if gun is not None:
        cmd += ["--gun", gun]
    if args:
        cmd += list(args)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _ilk_satir_ciz(cikti):
    """Standart INIS satirini parse et -> dict (gun=str, sayisal alanlar=int) ya da None."""
    m = SATIR_RE.search(cikti.splitlines()[0] if cikti else "")
    if not m:
        return None
    d = m.groupdict()
    return {"gun": d["gun"], **{k: int(v) for k, v in d.items() if k != "gun"}}


# ══════════════════════════════════════════════════════════════════════════════
# IZOLE MUTANT KOPYASI
# ══════════════════════════════════════════════════════════════════════════════
def izole_kopya(tmp):
    """Araci gecici dizine kopyalar. MUTANT CANLI GOVDEDE YASAMAZ: bozulan dosya
    repodaki degil, BU kopyadir."""
    hedef = os.path.join(tmp, "inis-sayac-oku.py")
    shutil.copyfile(ARAC, hedef)
    return hedef


def mutasyonla(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1:
        raise AssertionError(
            "MUTANT CAPASI BAYAT: %r govdede %d kez gecti (1 bekleniyordu) — "
            "capa kaynaktan tazelenmeli" % (eski, govde.count(eski))
        )
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni))


# ══════════════════════════════════════════════════════════════════════════════
# VAKALAR
# ══════════════════════════════════════════════════════════════════════════════
def vakalar_kos(gccer, hata):
    with tempfile.TemporaryDirectory(prefix="inis-vaka-") as tmp:
        # ── V1: karisik satirlar -> sinif toplamlari birebir ────────────────
        vt = _vt_kur(tmp, F1_SATIRLAR)
        rc, cikti = kos(ARAC, vt=vt, gun="2026-10-17")
        bek = _ilk_satir_ciz(cikti)
        if rc == 0 and bek and bek["gun"] == "2026-10-17" and all(
            bek[k] == F1_BEK[k] for k in ("fb", "ig", "g", "geo", "diger", "toplam")
        ):
            gccer.append("V1")
        else:
            hata.append("V1 karisik satirlar sinif toplamlari yanlis: rc=%d\n  bek=%s\n  olculen=%s\n  cikti=%r"
                        % (rc, F1_BEK, bek, cikti[:300]))

        # ── V2: baska gun satirlari sayilmaz ─────────────────────────────────
        vt2 = _vt_kur(tmp, F2_SATIRLAR)
        rc, cikti = kos(ARAC, vt=vt2, gun="2026-10-17")
        bek = _ilk_satir_ciz(cikti)
        if rc == 0 and bek and all(
            bek[k] == F2_BEK[k] for k in ("fb", "ig", "g", "geo", "diger", "toplam")
        ):
            gccer.append("V2")
        else:
            hata.append("V2 gun suzgeci yanlis: rc=%d\n  bek=%s\n  olculen=%s\n  cikti=%r"
                        % (rc, F2_BEK, bek, cikti[:300]))

        # ── V3: bos gun -> hepsi 0, rc=0 ────────────────────────────────────
        vt3 = _sqlite_olustur_bos(tmp)
        rc, cikti = kos(ARAC, vt=vt3, gun="2026-10-17")
        bek = _ilk_satir_ciz(cikti)
        if (rc == 0 and bek and all(
            bek[k] == 0 for k in ("fb", "ig", "g", "geo", "diger", "toplam")
        )):
            gccer.append("V3")
        else:
            hata.append("V3 bos gun sifir vermedi: rc=%d\n  olculen=%s\n  cikti=%r"
                        % (rc, bek, cikti[:300]))

        # ── V4: --gun bicim disi -> rc=2, INIS=OLCULEMEDI ───────────────────
        rc, cikti = kos(ARAC, vt=vt3, gun="2026-1-7")
        if rc == 2 and "INIS=OLCULEMEDI sebep=GUN-BICIMI" in cikti:
            gccer.append("V4")
        else:
            hata.append("V4 gun bicimi yanlis (rc=%d bek 2):\n  cikti=%r"
                        % (rc, cikti[:300]))

        # ── V5: vt acilamaz -> rc=3, '0' BASILMAMALI ────────────────────────
        rc, cikti = kos(ARAC, vt="/private/tmp/var-olmayan-inis-sayac-x9y8.db",
                        gun="2026-10-17")
        if rc == 3 and "INIS=OLCULEMEDI sebep=D1" in cikti and "TOPLAM=0" not in cikti:
            gccer.append("V5")
        else:
            hata.append("V5 vt acilmaz sessiz 0 vermemeli (rc=%d bek 3, 'TOPLAM=0' YOK):\n  cikti=%r"
                        % (rc, cikti[:300]))

        # ── V6: --kampanya -> (kaynak, kampanya, n) n azalan ────────────────
        # F1'deki 11 satirdan n azalan sirayla: 9 (ig/awareness) birinci, 8 (google/display),
        # 6 (facebook/ret-cat-101), 5 (meta/ret-lal), 4 (fb/awareness), 3 (google/search-genel),
        # 3 (bing/search-genel), 2 (instagram/ret-cat-101), 1 (google/search-brand),
        # 1 (facebook/ret-lal), 4 (tiktok/ugc) -- BING ve google.search-genel esit (3),
        # TikTok 4. Net sirayi hesaba KATMAYIZ; sadece n'in azalan oldugunu ve
        # tum 11 satirin mevcut oldugunu olceriz.
        rc, cikti = kos(ARAC, vt=vt, gun="2026-10-17", args=["--kampanya"])
        satirlar = cikti.splitlines()
        alt = [s for s in satirlar if s.startswith("  ")]
        if rc != 0 or len(alt) != len(F1_SATIRLAR):
            hata.append("V6 --kampanya 11 alt satir yok: rc=%d, len(alt)=%d\n  cikti=%r"
                        % (rc, len(alt), cikti[:400]))
        else:
            alt_n = [int(s.split()[2]) for s in alt]
            if alt_n != sorted(alt_n, reverse=True):
                hata.append("V6 --kampanya n azalan sirayla degil:\n  alt=%r" % alt)
            else:
                # Beklenen 11 (kaynak, kampanya, n) cumlesinin HEPSI cikti icinde var.
                bek_satirlar = set()
                for gun, kaynak, kamp, n in F1_SATIRLAR:
                    bek_satirlar.add("  %s %s %s\n" % (kaynak, kamp, n))
                if all(s + "\n" in cikti for s in {x.strip() for x in bek_satirlar}):
                    gccer.append("V6")
                else:
                    hata.append("V6 --kampanya beklenen cumlelerden biri yok:\n  beklenen=%r\n  cikti=%r"
                                % (sorted(bek_satirlar), alt))

        # ── V7: CANLI D1 SEKLI — wrangler zarf LISTESI -> F1 toplamlari ──────
        # 17 Eki olculdu: eski ayristirici liste zarfini satir sandi, canlida 25 inis
        # varken TOPLAM=0 basti. V1-V6 yalniz sqlite kolunu olcuyordu (bu yol kordu).
        yol7 = _d1_json_yaz(tmp, "v7.json", _d1_zarfi(F1_SATIRLAR))
        rc, cikti = kos(ARAC, args=["--d1-json", yol7], gun="2026-10-17")
        bek = _ilk_satir_ciz(cikti)
        if rc == 0 and bek and all(
            bek[k] == F1_BEK[k] for k in ("fb", "ig", "g", "geo", "diger", "toplam")
        ):
            gccer.append("V7")
        else:
            hata.append("V7 wrangler zarf listesi yanlis sayildi: rc=%d\n  bek=%s\n  olculen=%s\n  cikti=%r"
                        % (rc, F1_BEK, bek, cikti[:300]))

        # ── V8: bozuk sekil (results yok / satir alani eksik) -> rc=3, 0 YOK ─
        bozuklar = [[{"success": True}], [], [{"results": [{"kaynak": "google"}]}]]
        v8_ok = True
        for i, bozuk in enumerate(bozuklar):
            yol8 = _d1_json_yaz(tmp, "v8-%d.json" % i, bozuk)
            rc, cikti = kos(ARAC, args=["--d1-json", yol8], gun="2026-10-17")
            if not (rc == 3 and "INIS=OLCULEMEDI sebep=D1-SEKIL" in cikti
                    and "TOPLAM=" not in cikti):
                v8_ok = False
                hata.append("V8 bozuk D1 sekli #%d sessiz gecti (rc=%d bek 3):\n  cikti=%r"
                            % (i, rc, cikti[:300]))
        if v8_ok:
            gccer.append("V8")


def _d1_zarfi(satirlar):
    """wrangler `d1 execute --json` cevabinin GERCEK sekli (17 Eki canli cevaptan)."""
    return [{
        "results": [{"kaynak": k, "kampanya": c, "n": n} for _g, k, c, n in satirlar],
        "success": True,
        "meta": {"changes": 0, "rows_read": len(satirlar), "rows_written": 0},
    }]


def _d1_json_yaz(tmp, ad, veri):
    yol = os.path.join(tmp, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f)
    return yol


# ══════════════════════════════════════════════════════════════════════════════
# MUTANTLAR (izole kopya)
# ══════════════════════════════════════════════════════════════════════════════
def mutantlar_kos(gccer, hata):
    tmp = tempfile.mkdtemp(prefix="inis-mutant-")
    try:
        # Negatif kontrol: BOZULMADAN kopya YESIL.
        kopya = izole_kopya(tmp)
        with tempfile.TemporaryDirectory(prefix="inis-mutant-neg-") as neg_tmp:
            vt = _vt_kur(neg_tmp, F1_SATIRLAR)
            rc, cikti = kos(kopya, vt=vt, gun="2026-10-17")
            bek = _ilk_satir_ciz(cikti)
            if rc == 0 and bek and bek["toplam"] == 46:
                gccer.append("MNEG")
            else:
                hata.append("NEGATIF KONTROL: bozulmamis kopya YESIL degil (rc=%d)\n  bek.toplam=46\n  olculen=%s\n  cikti=%r"
                            % (rc, bek, cikti[:400]))

        # ── M1: gun suzgeci kalkar -> V2 KIRMIZI (baska gun satirlari sayilir) ─
        # Capa: sqlite SQL'indeki WHERE gun=? tamamen kaldirilir (tekil gecis).
        k = izole_kopya(tmp)
        mutasyonla(k,
                   'sql = "SELECT kaynak, kampanya, n FROM inis_sayac WHERE gun=?"',
                   'sql = "SELECT kaynak, kampanya, n FROM inis_sayac"')
        with tempfile.TemporaryDirectory(prefix="inis-m1-") as m_tmp:
            vt_m = _vt_kur(m_tmp, F2_SATIRLAR)
            rc, cikti = kos(k, vt=vt_m, gun="2026-10-17")
            bek = _ilk_satir_ciz(cikti)
            # Canli govdede bek.toplam=46; mutantta V2'nin baska gun satirlari eklendigi
            # icin toplam > 46 olur (en az +4*99 = 396).
            if rc != 0 or not bek or bek["toplam"] > 46:
                gccer.append("M1")
            else:
                hata.append("M1 gun suzgeci kalkti ama toplam AYNI (rc=%d, toplam=%s) — V2 GECMEDI\n  cikti=%r"
                            % (rc, bek.get("toplam") if bek else None, cikti[:300]))

        # ── M2: `meta` FB'den cikar -> V1 KIRMIZI (FB=16 yerine 11) ────────
        # Not: meta 5 sayilmadigi icin DIGER'a dusmez (kaynak beyaz listede taninmiyor
        # ve DIGER sinifina gidiyor); TOPLAM AYNI kalir (46), ama FB 11 olur.
        k = izole_kopya(tmp)
        mutasyonla(k, 'FB = ("facebook", "fb", "meta")',
                   'FB = ("facebook", "fb")')
        with tempfile.TemporaryDirectory(prefix="inis-m2-") as m_tmp:
            vt_m = _vt_kur(m_tmp, F1_SATIRLAR)
            rc, cikti = kos(k, vt=vt_m, gun="2026-10-17")
            bek = _ilk_satir_ciz(cikti)
            # Canli govdede FB=16; mutantta FB=11 (5 eksik) — bu ayrim YETERLI.
            if rc != 0 or not bek or bek["fb"] == 11:
                gccer.append("M2")
            else:
                hata.append("M2 meta FB'den cikarilmadi (rc=%d, fb=%s, toplam=%s)\n  cikti=%r"
                            % (rc, bek.get("fb") if bek else None,
                               bek.get("toplam") if bek else None,
                               cikti[:300]))

        # ── M3: hata kolunda 0 basar -> V5 KIRMIZI (sessiz 0 sizintisi) ───────
        # Capa: except blogunda "INIS=OLCULEMEDI sebep=D1" -> "TOPLAM=0".
        k = izole_kopya(tmp)
        mutasyonla(k, 'sys.stdout.write("INIS=OLCULEMEDI sebep=D1\\n")',
                   'sys.stdout.write("TOPLAM=0\\n")')
        # Not: dosyada ters-slag olarak "\\n" var; capa da ayni sekilde.
        with tempfile.TemporaryDirectory(prefix="inis-m3-") as m_tmp:
            rc, cikti = kos(k, vt="/private/tmp/var-olmayan-inis-sayac-z9y8.db",
                            gun="2026-10-17")
            if rc != 0 and "TOPLAM=0" in cikti and "INIS=OLCULEMEDI" not in cikti:
                gccer.append("M3")
            else:
                hata.append("M3 hata kolunda sessiz 0 basmadi (rc=%d, 'TOPLAM=0' YOK):\n  cikti=%r"
                            % (rc, cikti[:300]))

        # ── M4: 17 Eki oncesi ayristirici geri gelir -> V7 KIRMIZI ───────────
        # Capa: zarf listesini acan dongu yerine liste AYNEN satir diye doner.
        k = izole_kopya(tmp)
        mutasyonla(k, "    satirlar = []\n    for zarf in raw:",
                   "    return raw\n    satirlar = []\n    for zarf in raw:")
        with tempfile.TemporaryDirectory(prefix="inis-m4-") as m_tmp:
            yol = _d1_json_yaz(m_tmp, "m4.json", _d1_zarfi(F1_SATIRLAR))
            rc, cikti = kos(k, args=["--d1-json", yol], gun="2026-10-17")
            bek = _ilk_satir_ciz(cikti)
            if not (rc == 0 and bek and bek["toplam"] == 46):
                gccer.append("M4")
            else:
                hata.append("M4 eski ayristirici geri geldi ama V7 YESIL kaldi (toplam=46)\n  cikti=%r"
                            % cikti[:300])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANA
# ══════════════════════════════════════════════════════════════════════════════
def main():
    gccer = []
    hata = []

    vakalar_kos(gccer, hata)
    mutantlar_kos(gccer, hata)

    # Filtreleme: V1..V8 ve M1..M4 disindaki etiketler (MNEG/NEG) sayima GIRMEZ.
    vakalar = [g for g in gccer if g.startswith("V")]
    mutantlar = [g for g in gccer if g.startswith("M") and g[1:].isdigit()]

    print("VAKA_GECEN=%d  VAKA_HATA=%d" % (len(vakalar), 8 - len(vakalar)))
    print("MUTANT_GECEN=%d MUTANT_HATA=%d" % (len(mutantlar), 4 - len(mutantlar)))
    for h in hata:
        print("KIRMIZI: %s" % h)
    print("KABUL %d/8 MUTANT %d/4" % (len(vakalar), len(mutantlar)))
    if hata:
        print("HAL=KIRMIZI")
        return 1
    if len(vakalar) != 8 or len(mutantlar) != 4:
        print("HAL=KIRMIZI")
        return 1
    print("HAL=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())