#!/usr/bin/env python3
"""`cip-kapanis-kancasi.py` KABUL BATARYASI — davranissal, gercek subprocess.

Bu kanca BES EVIN her oturumunda kosar. Iki ayri felaket kipi var ve IKISI de
burada olculur:
  (a) BLOKLAMASI GEREKIRKEN GECIRIR -> yarim cip sessizce kapanir, is kaybolur.
  (b) GECMESI GEREKIRKEN BLOKLAR    -> mimar oturumlari / hatali girdi filoyu
      kilitler; kanca catlarsa da ayni sonuc.
Her vaka POZITIF ve NEGATIF yonuyle yazilir; tek yon = olu nobetci.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.realpath(__file__))
KANCA = os.path.join(KOK, "cip-kapanis-kancasi.py")
SAYAC_DIZIN = os.path.expanduser("~/.claude/cron/.cip-kapanis-sayaci")


def _ak():
    spec = importlib.util.spec_from_file_location(
        "_arsiv_kapisi", os.path.join(KOK, "arsiv-kapisi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kancayi_kos(veri, kanca=KANCA, kutu=None):
    argv = [sys.executable, kanca]
    if kutu:
        argv += ["--kutu", kutu]
    # Kanca KOPYASI gecici dizinde kosarken yaninda `arsiv-kapisi.py` YOKTUR;
    # kanonik `tools/` ortamla soylenir, yoksa kopya fail-open gecer ve mutasyon
    # turu tabaniyla birlikte coker (5 Eyl'de olculdu).
    ortam = dict(os.environ, PRUVO_KANONIK_TOOLS=KOK)
    s = subprocess.run(argv, input=json.dumps(veri),
                       capture_output=True, text=True, timeout=180, env=ortam)
    blokladi = False
    sebep = ""
    for satir in s.stdout.splitlines():
        satir = satir.strip()
        if not satir.startswith("{"):
            continue
        try:
            k = json.loads(satir)
        except ValueError:
            continue
        if k.get("decision") == "block":
            blokladi = True
            sebep = k.get("reason", "")
    return s.returncode, blokladi, sebep, s.stdout, s.stderr


def _sayaci_temizle(sid):
    try:
        os.remove(os.path.join(SAYAC_DIZIN, "%s.txt" % sid))
    except OSError:
        pass


def kos(kanca=KANCA, sessiz=False):
    ak = _ak()
    gecti = kirmizi = iddia = 0

    def check(ad, kosul):
        nonlocal gecti, kirmizi, iddia
        iddia += 1
        if kosul:
            gecti += 1
            if not sessiz:
                print("  [OK] %s" % ad)
        else:
            kirmizi += 1
            if not sessiz:
                print("  [KIRMIZI] %s" % ad)

    # --- fikstur: KIRMIZI cip agaci (kapanis yok) --------------------------
    kok = os.path.realpath(tempfile.mkdtemp(prefix="kanca-test-"))
    try:
        repo_k, hedef_k, kutu_k, _c = ak._kur_fikstur(kok + "/kirmizi", kapanis=False)
        repo_y, hedef_y, kutu_y, _c2 = ak._kur_fikstur(kok + "/yesil")

        # V1 POZITIF: kirmizi cip agaci -> BLOKLA
        sid = "test-v1"
        _sayaci_temizle(sid)
        rc, blok, sebep, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": hedef_k, "stop_hook_active": False}, kanca=kanca, kutu=kutu_k)
        check("V1 kirmizi cip -> BLOKLADI", blok)
        check("V1 rc=0 (blok exit koduyla degil JSON'la)", rc == 0)
        check("V1 sebep KIRMIZI kolu adiyla anar", "KAPANIS_YOK" in sebep)
        _sayaci_temizle(sid)

        # V2 NEGATIF: YESIL cip agaci -> GECIR
        sid = "test-v2"
        _sayaci_temizle(sid)
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": hedef_y, "stop_hook_active": False}, kanca=kanca, kutu=kutu_y)
        check("V2 yesil cip -> GECIRDI (yanlis-pozitif nobetcisi)", not blok)
        _sayaci_temizle(sid)

        # V3 NEGATIF: stop_hook_active -> ASLA blokla (dongu emniyeti)
        sid = "test-v3"
        _sayaci_temizle(sid)
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": hedef_k, "stop_hook_active": True}, kanca=kanca, kutu=kutu_k)
        check("V3 stop_hook_active=True -> GECIRDI", not blok)
        _sayaci_temizle(sid)

        # V4 NEGATIF: ANA checkout (mimar oturumu) -> GECIR
        sid = "test-v4"
        _sayaci_temizle(sid)
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": repo_k, "stop_hook_active": False}, kanca=kanca, kutu=kutu_k)
        check("V4 ana checkout -> GECIRDI (mimar cip degil)", not blok)
        _sayaci_temizle(sid)

        # V5 TAVAN: ayni oturum TAVAN kez bloklanir, sonrasi GECER
        sid = "test-v5"
        _sayaci_temizle(sid)
        bloklar = []
        for _ in range(4):
            _rc, blok, _s, _o, _e = kancayi_kos(
                {"session_id": sid, "cwd": hedef_k, "stop_hook_active": False},
                kanca=kanca, kutu=kutu_k)
            bloklar.append(blok)
        check("V5 tavan: ilk iki cagri blokladi", bloklar[0] and bloklar[1])
        check("V5 tavan: 3. ve 4. cagri GECTI (sonsuz dongu YOK)",
              (not bloklar[2]) and (not bloklar[3]))
        _sayaci_temizle(sid)

        # V6 FAIL-OPEN: bozuk stdin -> ne catla ne blokla
        rc, blok, _s, _o, _e = kancayi_kos_ham("bu JSON degil{{", kanca)
        check("V6 bozuk stdin -> rc=0", rc == 0)
        check("V6 bozuk stdin -> BLOKLAMADI", not blok)

        # V7 FAIL-OPEN: cwd yok
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": "test-v7", "cwd": "/var/empty/yok", "stop_hook_active": False},
            kanca=kanca)
        check("V7 cwd yok -> GECIRDI", not blok)
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    if not sessiz:
        print("\nIDDIA=%d GECTI=%d KIRMIZI=%d" % (iddia, gecti, kirmizi))
        print("KABUL %s" % ("YESIL" if kirmizi == 0 else "KIRMIZI"))
    return kirmizi == 0


def kancayi_kos_ham(ham, kanca=KANCA):
    s = subprocess.run([sys.executable, kanca], input=ham,
                       capture_output=True, text=True, timeout=120)
    blokladi = '"block"' in s.stdout
    return s.returncode, blokladi, "", s.stdout, s.stderr


MUTANTLAR = (
    ("M1 dongu-emniyetini-kaldir", "V3",
     '    if veri.get("stop_hook_active"):\n        return _gecti(',
     '    if False:\n        return _gecti('),
    ("M2 ana-checkout-muafiyetini-kaldir", "V4",
     '    if ana:\n        return _gecti("ana checkout',
     '    if False:\n        return _gecti("ana checkout'),
    ("M3 tavani-kaldir", "V5",
     '    if kac >= TAVAN:\n        return _gecti(',
     '    if False:\n        return _gecti('),
    ("M4 yesili-de-blokla", "V2",
     '    if s.returncode == RC_YESIL:\n        return _gecti("kapi YESIL")',
     '    if False:\n        return _gecti("kapi YESIL")'),
)


def mutasyon():
    with open(KANCA, encoding="utf-8") as f:
        taban = f.read()
    kok = os.path.realpath(tempfile.mkdtemp(prefix="kanca-mut-"))
    kirmizi = 0
    print("MUTASYON — kopya uzerinde, canli kanca DEGISMEZ")
    try:
        kontrol = os.path.join(kok, "kontrol.py")
        with open(kontrol, "w", encoding="utf-8") as f:
            f.write(taban)
        ok = kos(kontrol, sessiz=True)
        print("  [%s] MK kontrol (mutantsiz kopya) -> %s"
              % ("OK" if ok else "KIRMIZI", "YESIL" if ok else "KIRMIZI"))
        if not ok:
            # 🔴 OLCULMUS SAHTE YESIL (5 Eyl, CI hali): kontrol KIRMIZI oldugu halde
            # tur devam edip 4 mutantin 4'unu "OLDU" diye BASIYORDU — oysa hepsinin
            # kirmizisi mutantin degil, TABANIN kirmizisiydi. Taban kirmiziyken
            # mutant hukmu VERILEMEZ ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
            print("\n!! TABAN KIRMIZI — mutasyon turu KOSMAZ (once bataryayi yesile "
                  "getir). Bu turda OLCULEN mutant sayisi 0.")
            print("MUTANT=0/%d KIRMIZI=1 (TABAN)" % len(MUTANTLAR))
            print("MUTASYON OLCULEMEDI")
            return False

        for ad, hedef, capa, yeni in MUTANTLAR:
            if taban.count(capa) != 1:
                print("  [KIRMIZI] %-34s CAPA ULASMADI (count=%d)"
                      % (ad, taban.count(capa)))
                kirmizi += 1
                continue
            yol = os.path.join(kok, ad.split()[0] + ".py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(taban.replace(capa, yeni))
            oldu = not kos(yol, sessiz=True)
            print("  [%s] %-34s hedef vaka=%-4s %s"
                  % ("OK" if oldu else "KIRMIZI", ad, hedef,
                     "-> mutant OLDU" if oldu else "-> mutant ULASMADI"))
            if not oldu:
                kirmizi += 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print("\nMUTANT=%d KIRMIZI=%d" % (len(MUTANTLAR) + 1, kirmizi))
    print("MUTASYON %s" % ("YESIL" if kirmizi == 0 else "KIRMIZI"))
    return kirmizi == 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(0 if mutasyon() else 1)
    sys.exit(0 if kos() else 1)
