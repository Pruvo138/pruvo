#!/usr/bin/env python3
"""`baglam-kotasi-kapisi.py` kabul testi (BaBa emri, 4 Eyl 2026 — 3 vaka + mutant).

ISKELE YOK: kapi GERCEK alt surec olarak kosturulur, stdin'e gercek PreToolUse yuku
verilir, cikti gercek hook protokoluyle okunur. Transkript SENTETIKTIR (gecici dizinde)
— gercek oturum transkriptine DOKUNULMAZ.
Mutant DISKE degil GECICI kopyaya yazilir; sonunda kaynak sha'si ONCE==SONRA olculur.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(BURASI, "baglam-kotasi-kapisi.py")

gecti, kaldi = [], []


def iddia(ad, kosul, tani=""):
    (gecti if kosul else kaldi).append(ad)
    print("  %s %s%s" % ("✅" if kosul else "❌", ad,
                         ("  — " + str(tani)[:220]) if not kosul else ""))


def transkript_yaz(kok, tur, baglam, kod_write=0):
    """Sentetik .jsonl: `tur` asistan mesaji; SON mesajin usage'i `baglam`."""
    yol = os.path.join(kok, "transkript.jsonl")
    with io.open(yol, "w", encoding="utf-8") as f:
        for i in range(tur):
            icerik = []
            if i < kod_write:
                icerik.append({"type": "tool_use", "name": "Write",
                               "input": {"file_path": "/Users/okan/dev/pruvo/tools/x%d.py" % i}})
            son = (i == tur - 1)
            kayit = {"type": "assistant", "message": {
                "content": icerik,
                "usage": {"input_tokens": 10,
                          "cache_read_input_tokens": (baglam - 10) if son else 0,
                          "cache_creation_input_tokens": 0}}}
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return yol


def kos(arac, girdi, transkript, betik=None):
    yuk = json.dumps({"tool_name": arac, "tool_input": girdi,
                      "transcript_path": transkript})
    p = subprocess.run([sys.executable, betik or KAPI], input=yuk,
                       capture_output=True, text=True, timeout=60)
    ham = (p.stdout or "").strip()
    if not ham:
        return "allow", (p.stderr or "").strip()
    try:
        veri = json.loads(ham)
    except ValueError:
        return "allow", ham
    ozel = veri.get("hookSpecificOutput") or {}
    return ozel.get("permissionDecision", "allow"), ozel.get("permissionDecisionReason", "")


KOD_WRITE = {"file_path": "/Users/okan/dev/pruvo/tools/yeni-arac.py", "content": "x"}
DEFTER_WRITE = {"file_path": "/Users/okan/dev/pruvo/DEVAM.md", "content": "x"}
KUTU_WRITE = {"file_path": "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/"
                           "memory/mimar-posta-kutusu.md", "content": "x"}
COMMIT = {"command": "git -C /Users/okan/dev/pruvo commit -F -"}
OLCUM = {"command": "grep -n 'x' tools/a.py"}
AGIR = {"command": "python3 tools/agir-is.py --tum-katalog"}


def vaka1(kok):
    print("\n[1] ESIK ALTI — kapi GECIRIR (yanlis pozitif nobeti)")
    t = transkript_yaz(kok, tur=100, baglam=120_000)
    for ad, arac, girdi in (("kod Write", "Write", KOD_WRITE),
                            ("agir Bash", "Bash", AGIR),
                            ("defter Write", "Write", DEFTER_WRITE)):
        karar, _s = kos(arac, girdi, t)
        iddia("1-%s -> IZIN (esik altinda kapi karismaz)" % ad, karar == "allow",
              "karar=%s" % karar)


def vaka2(kok):
    print("\n[2] RED ESIGI — YALNIZ kapanis sinifi gecer")
    t_jeton = transkript_yaz(kok, tur=120, baglam=260_000)      # jeton ekseni tetikler
    t_tur = transkript_yaz(os.path.join(kok, "b"), tur=420, baglam=90_000)  # tur ekseni

    karar, sebep = kos("Write", KOD_WRITE, t_jeton)
    iddia("2a >=250K baglam + kod Write -> RED", karar == "deny", "karar=%s" % karar)
    iddia("2b red gerekcesi SAYIYI ve careyi soyluyor",
          "260K" in sebep and "/clear" in sebep and "KAPANIS" in sebep, sebep)
    karar, _s = kos("Bash", AGIR, t_jeton)
    iddia("2c >=250K + agir Bash -> RED", karar == "deny", "karar=%s" % karar)

    # 🔴 KAPI KORUDUGUNU DURDURMAMALI: kapanis araclari GECMELI
    for ad, arac, girdi in (("DEVAM.md Write", "Write", DEFTER_WRITE),
                            ("kutu Write", "Write", KUTU_WRITE),
                            ("git commit", "Bash", COMMIT),
                            ("grep (olcum)", "Bash", OLCUM),
                            ("Read", "Read", {"file_path": "/tmp/x"})):
        karar, _s = kos(arac, girdi, t_jeton)
        iddia("2d-%s -> IZIN (kapanis sinifi)" % ad, karar == "allow", "karar=%s" % karar)

    karar, sebep = kos("Write", KOD_WRITE, t_tur)
    iddia("2e >=400 TUR (baglam dusukken) -> RED (iki eksen VEYA ile bagli)",
          karar == "deny", "karar=%s" % karar)
    iddia("2f tur ekseninin gerekcesi tur SAYISINI basiyor", "tur=420" in sebep, sebep)


def vaka3(kok):
    print("\n[3] MEKANIK KOL — kod/test Write >=15 -> ucuz kata")
    t = transkript_yaz(kok, tur=60, baglam=100_000, kod_write=16)
    karar, sebep = kos("Write", KOD_WRITE, t)
    iddia("3a 16 kod Write sonrasi yeni kod Write -> RED", karar == "deny",
          "karar=%s" % karar)
    iddia("3b gerekce ucuz kat cagrisini ADIYLA veriyor",
          "isci.sh" in sebep and "minimax-m3" in sebep, sebep)
    karar, _s = kos("Write", DEFTER_WRITE, t)
    iddia("3c AYNI oturumda DEFTER Write -> IZIN (mekanik kol defteri kesmez)",
          karar == "allow", "karar=%s" % karar)
    t2 = transkript_yaz(os.path.join(kok, "c"), tur=60, baglam=100_000, kod_write=14)
    karar, _s = kos("Write", KOD_WRITE, t2)
    iddia("3d 14 Write (tavan ALTI) -> IZIN (esik gercekten 15)", karar == "allow",
          "karar=%s" % karar)


def vaka4(kok):
    print("\n[4] OLCULEMEDI — fail-open ama SESSIZ DEGIL")
    karar, err = kos("Write", KOD_WRITE, os.path.join(kok, "yok.jsonl"))
    iddia("4a transkript YOKken kapi GECIRIR (yanlis pozitif filoyu kilitlemez)",
          karar == "allow", "karar=%s" % karar)
    iddia("4b `OLCULEMEDI` ADIYLA basildi (sessiz bypass DEGIL)",
          "OLCULEMEDI" in err, err)


def mutant(kok):
    print("\n[5] MUTANT [OLDURUCU] + KONTROL")
    with io.open(KAPI, encoding="utf-8") as f:
        kaynak = f.read()
    sha_once = hashlib.sha256(kaynak.encode()).hexdigest()
    t = transkript_yaz(os.path.join(kok, "m"), tur=120, baglam=260_000)
    tmp = tempfile.mkdtemp(prefix="baglam-mutant-")
    try:
        # M1 [OLDURUCU]: RED esigi devre disi -> 2a GECMELI (esik yuku tasiyor mu?)
        capa1 = "    if tur >= RED_TUR or baglam >= RED_JETON:\n"
        if kaynak.count(capa1) != 1:
            iddia("5a M1 capasi TEK kez TUTMADI (OLCULEMEDI)", False,
                  "bulunan=%d" % kaynak.count(capa1))
        else:
            m1 = os.path.join(tmp, "m1.py")
            with io.open(m1, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa1, "    if False:\n"))
            karar, _s = kos("Write", KOD_WRITE, t, betik=m1)
            iddia("5a M1 [OLDURUCU] RED esigi kaldirilinca kod Write GECIYOR "
                  "(2a'yi kirmizi yapan sey GERCEKTEN esik)", karar == "allow",
                  "karar=%s — mutant HEDEFE ULASMADI" % karar)

        # M2 [OLDURUCU]: kapanis muafiyeti devre disi -> 2d GECMEMELI
        capa2 = "        if not kapanis_sinifi_mi(arac, girdi):\n"
        if kaynak.count(capa2) != 1:
            iddia("5b M2 capasi TEK kez TUTMADI (OLCULEMEDI)", False,
                  "bulunan=%d" % kaynak.count(capa2))
        else:
            m2 = os.path.join(tmp, "m2.py")
            with io.open(m2, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa2, "        if True:\n"))
            karar, _s = kos("Write", DEFTER_WRITE, t, betik=m2)
            iddia("5b M2 [OLDURUCU] kapanis muafiyeti kaldirilinca DEFTER Write "
                  "REDDEDILIYOR (muafiyet yuk tasiyor — koruma korudugunu durdurmuyor)",
                  karar == "deny", "karar=%s — mutant HEDEFE ULASMADI" % karar)

        # M3 [KONTROL]: yalniz uyari METNI degisir -> davranis AYNI
        capa3 = '"BAGLAM KOTASI — UYARI: tur=%d (uyari %d, red %d)'
        if kaynak.count(capa3) != 1:
            iddia("5c M3 capasi TEK kez TUTMADI (OLCULEMEDI)", False,
                  "bulunan=%d" % kaynak.count(capa3))
        else:
            m3 = os.path.join(tmp, "m3.py")
            with io.open(m3, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa3, '"BAGLAM KOTASI — METIN DEGISTI: tur=%d '
                                              '(uyari %d, red %d)'))
            k1, _ = kos("Write", KOD_WRITE, t, betik=m3)
            k2, _ = kos("Write", DEFTER_WRITE, t, betik=m3)
            iddia("5c M3 [KONTROL] yalniz teshis metni -> davranis DEGISMEDI "
                  "(batarya gurultulu degil)", k1 == "deny" and k2 == "allow",
                  "kod=%s defter=%s" % (k1, k2))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with io.open(KAPI, encoding="utf-8") as f:
        iddia("5d MUTANT gercek kapiya YAZILMADI (sha256 once==sonra)",
              hashlib.sha256(f.read().encode()).hexdigest() == sha_once)


def main():
    print("BAGLAM KOTASI KAPISI — KABUL TESTI")
    kok = tempfile.mkdtemp(prefix="baglam-kotasi-kt-")
    for alt in ("b", "c", "m"):
        os.makedirs(os.path.join(kok, alt), exist_ok=True)
    try:
        vaka1(kok)
        vaka2(kok)
        vaka3(kok)
        vaka4(kok)
        mutant(kok)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print("\n" + "-" * 70)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (len(gecti) + len(kaldi), len(gecti), len(kaldi)))
    if kaldi:
        print("DUSENLER=" + ",".join(kaldi))
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
