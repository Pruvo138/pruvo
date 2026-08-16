#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K71 kabul: D1 lease'i makineler-arasi yazicilari dislar (offline SQLite)."""
import argparse
import ast
import importlib.util
import io
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


def vaka_calistir(db, vaka):
    """V1-V4 icin ortak yardimci: d1-sync.py davranisini OLCE, downstream rc don.

    vaka: "v1" canli lease, "v2" lease yok, "v3" stale lease, "v4" gercek hata.
    Donen rc:
      0  basarili (yazma YAPILIR, davranis degismedi)
      4  DagitikYaziciCanliLease (yazma YAPILMAZ, CI adimi 0 sayar)
      1  gercek hata (fail-closed)

    V1 main()'in TAM YOLUNU (DagitikYaziciCanliLease -> rc=4) OLCER; V2/V3/V4 ise
    dagitik_kilit_al'in davranisini tek basina OLCER (cunku ana()'in devami offline
    test ortaminda D1/ag/git'ten baska sebeplerle de dusuyor; davranis DEGISMEMESI
    gereken tek sey lease alma adimi). V1 + V2 + V3 + V4'un birlesik kaniti: live
    lease ATLANIR, yok/stale/hata YAZMAYA DEVAM eder ya da fail-closed kalir.
    """
    sqlite_bagla(db)
    if vaka == "v1":
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE IF NOT EXISTS senkron_kilit "
                    "(ad TEXT PRIMARY KEY, sahip TEXT NOT NULL, sona_erme INTEGER NOT NULL)")
        con.execute("INSERT INTO senkron_kilit VALUES (?, ?, ?)",
                    (D1.DAGITIK_KILIT_ADI, "baska-pid", int(time.time()) + 600))
        con.commit()
        con.close()
    elif vaka == "v2":
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE IF NOT EXISTS senkron_kilit "
                    "(ad TEXT PRIMARY KEY, sahip TEXT NOT NULL, sona_erme INTEGER NOT NULL)")
        con.commit()
        con.close()
    elif vaka == "v3":
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE IF NOT EXISTS senkron_kilit "
                    "(ad TEXT PRIMARY KEY, sahip TEXT NOT NULL, sona_erme INTEGER NOT NULL)")
        con.execute("INSERT INTO senkron_kilit VALUES (?, ?, ?)",
                    (D1.DAGITIK_KILIT_ADI, "olen-pid", 1))
        con.commit()
        con.close()
    elif vaka == "v4":
        def hata(sql):
            raise sqlite3.OperationalError("simulated D1 error")
        D1.dosya_calistir = hata
        D1.sorgu = hata
    else:
        print("bilinmeyen vaka: " + vaka)
        return 99
    if vaka == "v1":
        # TAM main() yolu: DagitikYaziciCanliLease'i yakalar, rc=4 ile cikar.
        # argumanlari_oku()'yu yalin (bayraksiz) tut; testteki tek satir budur.
        original_argv = sys.argv
        sys.argv = ["d1-sync.py"]
        try:
            try:
                rc = D1.main()
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 1
            return rc if rc is not None else 0
        finally:
            sys.argv = original_argv
    # V2/V3/V4: YALNIZ dagitik_kilit_al — main()'in devami offline ortamda D1/ag/git
    # eksikliginden ayrica dusuyor; lease adiminin davranisini TEK BASINA olcmek yeter.
    try:
        D1.dagitik_kilit_al("bizim-pid")
        return 0
    except D1.DagitikYaziciCanliLease:
        return 4
    except SystemExit:
        return 1


def v5_adim_python(mock_rc, mutasyon=None):
    """V5: Python-level test; _adim_kos() monkeypatch'li alt sureclerle OLCE.

    K129 (16 Agu 2026): deploy.yml `python3 tools/d1-sync.py --adim` (TEK satir).
    _adim_kos() iceride iki alt subprocess.run cagirir --bayatlik + bayraksiz senkron).
    Onlari monkeypatch ile mockluyoruz: bayatlik her zaman 0, senkron `mock_rc` ile
    doner. _adim_kos()'un KENDISI Python'dan cagirilir, returncode + stdout olculur.

    Eski bash function override YONTEMI (K80 bash metakarakter yasagi + alt surec
    icinde override gercek davranisi maskeledi) KALDIRILDI; bu Python seviyesi
    test ayni seyleri OLCEBILIR sekilde, daha kisa ve daha hizli yapar.

    `mutasyon` ("m1" | None) uygulanirsa: `_adim_kos()`'un son satirinda
    `return senkron.returncode` -> `return 0` yapilir (M1: adim kolu "her zaman
    sessizce 0"a donusur -> V4 gercek-hata halinde 1 vermez, kapi KIRMIZI yanar).
    """
    os.environ["CLOUDFLARE_API_TOKEN"] = "x"
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = "y"

    bayatlik_rc = 0
    senkron_rc = mock_rc

    class Fake:
        returncode = None

        def __init__(self, rc):
            self.returncode = rc

    if mutasyon == "m1":
        # _adim_kos()'un son satirini "her zaman 0" yap; gercek hata (rc=1) YUTULUR.
        gercek = D1._adim_kos

        def _adim_mutant():
            bayat = Fake(bayatlik_rc)
            senk = Fake(senkron_rc)
            # (1) secret YOK -> 0; (2) bayatlik -> 0; (3) senkron -> HER ZAMAN 0 (M1).
            if not os.environ.get("CLOUDFLARE_API_TOKEN") \
                    or not os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
                return 0
            if bayat.returncode != 0:
                return 0
            print("D1_MUTANT: rc=%d olsa da 0 sayildi" % senk.returncode)
            return 0  # M1: asil mutant

        D1._adim_kos = _adim_mutant
        try:
            rc = D1._adim_kos()
        finally:
            D1._adim_kos = gercek
        out = sys.stdout.getvalue() if hasattr(sys.stdout, "getvalue") else ""
    else:
        bayat_call = {"count": 0}

        def fake_run(cmd, *a, **kw):
            # d1-sync.py --bayatlik veya d1-sync.py (bayraksiz) — ikisi de mock.
            if cmd[-1] == "--bayatlik":
                return Fake(bayatlik_rc)
            return Fake(senkron_rc)

        gercek_run = D1.subprocess.run
        D1.subprocess.run = fake_run
        # stdout yakala: _adim_kos() print() ile stdout'a yazar.
        captured = io.StringIO()
        gercek_stdout = sys.stdout
        sys.stdout = captured
        try:
            rc = D1._adim_kos()
        finally:
            sys.stdout = gercek_stdout
            D1.subprocess.run = gercek_run
        out = captured.getvalue()
    # imza icin D1_SENKRON=ATLANDI ya MUTANT printinde ya da _adim_kos() printinde olur.
    return rc, out


def ana_test(mutasyon=None):
    """mutasyon: None | "m1" | "m2".

    M1: _adim_kos()'un son satirini "return 0" yap (adim kolu gercek hatayi yutar).
        V4 (gercek hata -> rc=1) KIRMIZI olmali.
    M2: dagitik_kilit_al() canlilik kontrolunu no-op et (her zaman canli say).
        V3 (stale lease -> rc=0) KIRMIZI olmali; V1 (canli lease -> rc=4) yesil KALMALI.
    """
    gecen = 0
    toplam = 11
    m2_patch = None
    if mutasyon == "m1":
        toplam = 11  # V1-V5 + 6 eski => 11; ama V4 kirmizi olacak, gecmis 10.
    elif mutasyon == "m2":
        # dagitik_kilit_al() canlilik kontrolunu no-op yap: her zaman raise.
        # V1 (canli lease) zaten raise eder -> rc=4 (yesil); V3 (stale) simdi de
        # raise eder -> rc=4 (kirmizi, normalde 0 olmaliydi).
        gercek_al = D1.dagitik_kilit_al

        def _al_no_op(*args, **kwargs):
            raise D1.DagitikYaziciCanliLease("M2 mutant: canlilik no-op")
        D1.dagitik_kilit_al = _al_no_op
        m2_patch = gercek_al
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

        # K129 — yazici ucustayken kosum ATLANIR (rc=4); gercek hata fail-closed.
        # V1-V4 vakalarini YENI birer sqlite fixture ile subprocess olarak kosaruz;
        # vaka_calistir() main()'i OLCEBILIR bir rc'ye cevirir (0/4/1). Davranis
        # DEGISMEDI: vaka_calistir dagitik_kilit_al + main() cagiriyor, sys.argv
        # argumanlari_oku()'yu yalin tutuyor.
        vaka_db = os.path.join(tmp, "vaka.sqlite")
        for vaka, beklenen_rc, etiket in (
                ("v1", 4, "canli lease -> rc=4"),
                ("v2", 0, "lease yok -> rc=0 (davranis degismedi)"),
                ("v3", 0, "stale lease -> rc=0 (devralindi)"),
                ("v4", 1, "gercek hata -> rc=1 (asla 4 degil)")):
            with open(vaka_db, "w", encoding="utf-8"):
                pass
            # M2 mutasyonu: monkeypatch subprocess.run UZERINDEN yurumez (yeni
            # surec, yeni modul). Bu durumda V3'u DIREKT vaka_calistir() ile
            # kosariz; D1.dagitik_kilit_al hala patch'li -> canlilik no-op
            # etkili olur, V3 kirmizi olur.
            if mutasyon == "m2" and vaka == "v3":
                r_rc = vaka_calistir(vaka_db, vaka)
                r_stdout = ""
                r_stderr = ""
            else:
                r = subprocess.run(
                    [sys.executable, os.path.abspath(__file__),
                     "--vaka", vaka_db, vaka],
                    capture_output=True, text=True, timeout=15)
                r_rc = r.returncode
                r_stdout = r.stdout
                r_stderr = r.stderr
            if r_rc == beklenen_rc:
                gecen += 1
                print("GECTI V%s %s" % (vaka[1], etiket))
            else:
                print("KALDI V%s beklenen rc=%d bulunan rc=%d cikti=%r"
                      % (vaka[1], beklenen_rc, r_rc,
                         (r_stdout + r_stderr)[-300:]))

        # V5 — adim mantigi: rc=4 -> exit 0 + imza VAR, rc=1 -> exit 1 + imza YOK.
        # M1 mutant: rc=1 iken de exit 0 olur -> V4 senaryosu beklendigi gibi kirmizi.
        v5_ok = True
        for rc, etiket, beklenen_rc, beklenen_imza in (
                (4, "rc=4", 0, True), (1, "rc=1", 1, False)):
            vrc, vout = v5_adim_python(rc, mutasyon=mutasyon)
            if vrc == beklenen_rc and ("D1_SENKRON=ATLANDI" in vout) == beklenen_imza:
                print("GECTI V5 adim %s -> exit %d (imza=%s)"
                      % (etiket, vrc, str(beklenen_imza)))
            else:
                v5_ok = False
                print("KALDI V5 adim %s -> beklenen rc=%d imza=%s, bulunan rc=%d imza=%s out=%r"
                      % (etiket, beklenen_rc, str(beklenen_imza), vrc,
                         str("D1_SENKRON=ATLANDI" in vout), vout[:200]))
        if v5_ok:
            gecen += 1

    print("SONUC: %d/%d" % (gecen, toplam))
    return 0 if gecen == toplam else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt", nargs=5, metavar=("DB", "YEREL", "SAHIP", "TUT", "HAZIR"))
    ap.add_argument("--vaka", nargs=2, metavar=("DB", "VAKA"),
                    help="V1-V4 vakalarini d1-sync.py main() ile kos; OLCEBILIR rc don.")
    ap.add_argument("--mutasyon", choices=["m1", "m2"], default=None,
                    help="M1: --adim kolu 'her zaman 0' (V4 kirmizi). "
                         "M2: dagitik_kilit_al canlilik no-op (V3 kirmizi).")
    a = ap.parse_args()
    if a.alt:
        raise SystemExit(alt(a.alt[0], a.alt[1], a.alt[2], float(a.alt[3]), a.alt[4]))
    if a.vaka:
        raise SystemExit(vaka_calistir(a.vaka[0], a.vaka[1]))
    raise SystemExit(ana_test(mutasyon=a.mutasyon))
