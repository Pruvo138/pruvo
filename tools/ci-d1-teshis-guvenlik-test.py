#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GUVENLIK KABULU — ci-d1-teshis.py ciktisinda SIR SIZMAZ (calistirilabilir test).

NEDEN VAR: teshis sondasi CI'da CLOUDFLARE_API_TOKEN'li ortamda `wrangler d1 list`
kosar; repo PUBLIC ve Actions loglari HERKESE ACIK. Sondanin sozu "cikti yalniz dar
beyaz-liste anahtar=deger satirlaridir; DB adi/UUID/hesap-hex/token asla basilmaz".
Bu test o sozu OLCER: sondaya sahte ZENGIN `d1 list` JSON'u verilir (UUID'ler, DB
adlari, 32-hex hesap kimligi, token benzeri dize), ciktinin YALNIZ izinli satirlardan
olustugu ve sir deseninin 0 kez gectigi dogrulanir. Ayrica cikti kapisi (bas)
dogrudan dusmanca degerlerle cagrilir -> SANSUR donmeli (fail-closed).

CI'da teshis sondasindan ONCE, BLOKLAYICI kosar: kapi bozulursa sonda hic kosmadan
yayin hatti kirmizi yanar. Offline, stdlib, ag/wrangler YOK, ~0.5 s.

Kullanim: python3 tools/ci-d1-teshis-guvenlik-test.py   (exit 0 = YESIL)
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

TOOLS = os.path.dirname(os.path.abspath(__file__))
SONDA = os.path.join(TOOLS, "ci-d1-teshis.py")

SATIR_DESEN = re.compile(r"^[a-z0-9_]+=[A-Za-z0-9.\-]+$")
UUID_DESEN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
UZUN_HEX_DESEN = re.compile(r"[0-9a-fA-F]{20,}")

# Sahte zengin fikstur icin SENTETIK sirlar (gercek degerler degil).
SAHTE_ADLAR = ["cok-gizli-katalog-adi", "musteri-listesi-db", "pruvo-ic-defter"]
SAHTE_UUIDLER = [
    "11111111-2222-3333-4444-555555555555",
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
]
SAHTE_HESAP_HEX = "deadbeefdeadbeefdeadbeefdeadbeef"
SAHTE_TOKEN = "SAHTE-TOKEN-Aa1Bb2Cc3Dd4Ee5Ff6Gg7Hh8Ii9"


def _modul():
    spec = importlib.util.spec_from_file_location("ci_d1_teshis", SONDA)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _hedef():
    m = _modul()
    return m.hedef_db()


def _fikstur(hedef_dahil):
    kayitlar = []
    uuidler = list(SAHTE_UUIDLER)
    hedef = _hedef()
    if hedef_dahil and hedef:
        uuidler.append(hedef)
    for i, u in enumerate(uuidler):
        kayitlar.append({
            "uuid": u,
            "name": SAHTE_ADLAR[i % len(SAHTE_ADLAR)],
            "created_at": "2026-01-01T00:00:00.000Z",
            "version": "production",
            "account": SAHTE_HESAP_HEX,
            "token_izi": SAHTE_TOKEN,
            "num_tables": 7,
        })
    return kayitlar


def _sonda_kostur(json_metin):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(json_metin)
        yol = f.name
    try:
        p = subprocess.run([sys.executable, SONDA, "--liste-json", yol],
                           capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(yol)
    return p.returncode, p.stdout, p.stderr


def _sir_yok(metin, hatalar, baglam):
    """Sir deseni 0: UUID / 20+hex / DB adi / token izi (stdout VE stderr icin)."""
    if UUID_DESEN.search(metin):
        hatalar.append("%s: UUID deseni var (SIZINTI)" % baglam)
    if UZUN_HEX_DESEN.search(metin):
        hatalar.append("%s: 20+ hex deseni var (hesap-id SIZINTISI)" % baglam)
    for ad in SAHTE_ADLAR:
        if ad in metin:
            hatalar.append("%s: DB ADI gecti (SIZINTI): %s" % (baglam, ad))
    if SAHTE_TOKEN in metin:
        hatalar.append("%s: token benzeri dize gecti (SIZINTI)" % baglam)


def _cikti_temiz(cikti, hatalar, baglam):
    """stdout kanali: her satir izinli desen VE sir deseni 0."""
    for satir in cikti.splitlines():
        if not SATIR_DESEN.match(satir):
            hatalar.append("%s: izinsiz cikti satiri: %r" % (baglam, satir[:80]))
    _sir_yok(cikti, hatalar, baglam)


def main():
    hatalar = []

    if not os.path.exists(SONDA):
        sys.exit("sonda yok: " + SONDA)
    hedef = _hedef()

    # --- 1) Zengin fikstur, HEDEF DAHIL -> hedef_gorunur=EVET, sir 0 ---
    kod, cikti, hata_c = _sonda_kostur(json.dumps(_fikstur(hedef_dahil=True)))
    if kod != 0:
        hatalar.append("T1: sonda exit %d (0 beklenirdi)" % kod)
    _cikti_temiz(cikti, hatalar, "T1")
    _sir_yok(hata_c, hatalar, "T1-stderr")  # stderr de Actions loguna duser
    if hedef:
        if "hedef_gorunur=EVET" not in cikti:
            hatalar.append("T1: hedef fiksturde VAR ama hedef_gorunur=EVET basilmadi")
        if ("toplam_db_adedi=%d" % (len(SAHTE_UUIDLER) + 1)) not in cikti:
            hatalar.append("T1: toplam_db_adedi yanlis (beklenen %d)" % (len(SAHTE_UUIDLER) + 1))
    else:
        hatalar.append("T1: d1-sync.py'den hedef okunamadi (hedef_db() None) — "
                       "sonda tek-kaynak baglantisi kopmus")

    # --- 2) Zengin fikstur, HEDEF YOK -> hedef_gorunur=HAYIR, sir 0 ---
    kod, cikti, _ = _sonda_kostur(json.dumps(_fikstur(hedef_dahil=False)))
    if kod != 0:
        hatalar.append("T2: sonda exit %d" % kod)
    _cikti_temiz(cikti, hatalar, "T2")
    if hedef and "hedef_gorunur=HAYIR" not in cikti:
        hatalar.append("T2: hedef fiksturde YOK ama hedef_gorunur=HAYIR basilmadi")

    # --- 3) Bozuk JSON -> cokmez, yine yalniz beyaz-liste satirlari ---
    kod, cikti, _ = _sonda_kostur("wrangler bir seyler soyledi { bozuk json ]]]")
    if kod != 0:
        hatalar.append("T3: bozuk JSON'da sonda exit %d (0 beklenirdi)" % kod)
    _cikti_temiz(cikti, hatalar, "T3")
    if "toplam_db_adedi=-1" not in cikti:
        hatalar.append("T3: bozuk JSON'da toplam_db_adedi=-1 beklenirdi")

    # --- 4) Cikti kapisina (bas) DOGRUDAN dusmanca degerler -> SANSUR ---
    m = _modul()
    dusmanca = [
        ("node_surum", SAHTE_UUIDLER[0]),          # UUID deger
        ("node_surum", SAHTE_HESAP_HEX),           # 32-hex deger
        ("node_surum", "cok-gizli ad'li \"deger"), # izinsiz karakterler
        ("node_surum", "x" * 40),                  # asiri uzun
        ("hic-olmayan-anahtar", "EVET"),           # beyaz-liste disi anahtar
    ]
    for anahtar, deger in dusmanca:
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            m.bas(anahtar, deger)
        satir = tampon.getvalue().strip()
        if "SANSUR" not in satir:
            hatalar.append("T4: kapi dusmanca degeri GECIRDI: %s=%r -> %r"
                           % (anahtar, deger[:20], satir[:60]))
        _cikti_temiz(tampon.getvalue(), hatalar, "T4")

    # --- 5) Kapi mesru degerleri GECIRIYOR (hep-SANSUR sahte-yesili olmasin) ---
    mesru = [("node_surum", "v20.19.4"), ("wrangler_surum", "4.112.0"),
             ("hedef_gorunur", "EVET"), ("d1_list_exit", 0), ("toplam_db_adedi", -1)]
    for anahtar, deger in mesru:
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            m.bas(anahtar, deger)
        beklenen = "%s=%s" % (anahtar, deger)
        if tampon.getvalue().strip() != beklenen:
            hatalar.append("T5: kapi mesru degeri bozdu: %r -> %r"
                           % (beklenen, tampon.getvalue().strip()[:60]))

    print("D1 TESHIS GUVENLIK KABULU")
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1
    print("  ✅ zengin fiksturde sir deseni 0 (UUID/ad/hex/token)")
    print("  ✅ hedef EVET/HAYIR dogru, bozuk JSON cokmuyor")
    print("  ✅ cikti kapisi dusmancayi SANSUR'luyor, mesruyu geciriyor")
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
