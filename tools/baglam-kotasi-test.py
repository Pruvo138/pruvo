#!/usr/bin/env python3
"""`baglam-kotasi-kapisi.py` kabul testi.

ESIKLER — OKAN EMRI (6 Eyl 2026): RED = 500 tur / 450K. UYARI esigi emirde ACIKCA
YOK, kapinin mevcut tasarim mesafesinden TURETILDI (red'den 50 tur ve 150K once):
450 tur / 300K. Bu dosya sayilari KAPIDAN IMPORT ETMEZ, ELDE CIVILER — import etseydi
sabitin degismesi testi de birlikte kaydirir ve mutant olmezdi.

ISKELE YOK: kapi GERCEK alt surec olarak kosturulur, stdin'e gercek PreToolUse yuku
verilir, cikti gercek hook protokoluyle okunur. Transkript SENTETIKTIR (gecici dizinde)
— gercek oturum transkriptine DOKUNULMAZ.
Mutant DISKE degil GECICI kopyaya yazilir; her mutant BENZERSIZ ada + `-B`
(`PYTHONDONTWRITEBYTECODE`) ile kosar (ayni ada yazilan mutantlar CPython bytecode
onbelleginden BIRINCININ kodunu kosturup sahte "KACTI" uretiyordu). Sonunda kaynak
sha'si ONCE==SONRA olculur; gercek ev yoluna silme YAPILMAZ.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

BURASI = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(BURASI, "baglam-kotasi-kapisi.py")

# ── CIVILENEN ESIKLER (kapidan TURETILMEZ) ────────────────────────────────────────
RED_TUR, RED_JETON = 500, 450_000
UYARI_TUR, UYARI_JETON = 450, 300_000

gecti, kaldi = [], []


def iddia(ad, kosul, tani=""):
    (gecti if kosul else kaldi).append(ad)
    print("  %s %s%s" % ("✅" if kosul else "❌", ad,
                         ("  — " + str(tani)[:220]) if not kosul else ""))


def transkript_yaz(kok, tur, baglam, kod_write=0, ad="transkript.jsonl"):
    """Sentetik .jsonl: `tur` asistan mesaji; SON mesajin usage'i `baglam`."""
    if not os.path.isdir(kok):
        os.makedirs(kok, exist_ok=True)
    yol = os.path.join(kok, ad)
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
    """(karar, metin) — karar allow/deny; metin RED gerekcesi ya da stderr."""
    yuk = json.dumps({"tool_name": arac, "tool_input": girdi,
                      "transcript_path": transkript})
    cevre = dict(os.environ)
    cevre["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-B", betik or KAPI], input=yuk,
                       capture_output=True, text=True, timeout=60, env=cevre)
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

# ── FIKSTURLER: her biri BIR esik iddiasini tasir ─────────────────────────────────
F = {}


def fikstur_kur(kok):
    F["alt"] = transkript_yaz(kok, tur=100, baglam=120_000, ad="alt.jsonl")
    # RED sinirinin BIR ALTI — iki eksen AYRI
    F["red_jeton_alti"] = transkript_yaz(kok, tur=120, baglam=449_000,
                                         ad="red-jeton-alti.jsonl")
    F["red_tur_alti"] = transkript_yaz(kok, tur=499, baglam=90_000,
                                       ad="red-tur-alti.jsonl")
    # RED sinirinin TAM USTU — iki eksen AYRI (VEYA kolu)
    F["red_jeton"] = transkript_yaz(kok, tur=120, baglam=450_000, ad="red-jeton.jsonl")
    F["red_tur"] = transkript_yaz(kok, tur=500, baglam=90_000, ad="red-tur.jsonl")
    # UYARI esigi — tam ustu (iki eksen) ve BIR ALTI (ikisi birden)
    F["uyari_tur"] = transkript_yaz(kok, tur=450, baglam=100_000, ad="uyari-tur.jsonl")
    F["uyari_jeton"] = transkript_yaz(kok, tur=100, baglam=300_000,
                                      ad="uyari-jeton.jsonl")
    F["uyari_yok"] = transkript_yaz(kok, tur=449, baglam=299_000, ad="uyari-yok.jsonl")
    # Mekanik kol
    F["mekanik"] = transkript_yaz(kok, tur=60, baglam=100_000, kod_write=16,
                                  ad="mekanik.jsonl")
    F["mekanik_alti"] = transkript_yaz(kok, tur=60, baglam=100_000, kod_write=14,
                                       ad="mekanik-alti.jsonl")


def vaka1():
    print("\n[1] ESIK ALTI — kapi GECIRIR (yanlis pozitif nobeti)")
    for ad, arac, girdi in (("kod Write", "Write", KOD_WRITE),
                            ("agir Bash", "Bash", AGIR),
                            ("defter Write", "Write", DEFTER_WRITE)):
        karar, metin = kos(arac, girdi, F["alt"])
        iddia("1-%s -> IZIN (100 tur/120K, esik altinda kapi karismaz)" % ad,
              karar == "allow", "karar=%s" % karar)
    iddia("1d esik altinda UYARI satiri da BASILMAZ",
          "UYARI" not in kos("Write", KOD_WRITE, F["alt"])[1], "stderr doldu")


def vaka2():
    print("\n[2] RED SINIRI — 499 tur / 449K RED DEGIL, 500 tur / 450K RED")
    karar, _s = kos("Write", KOD_WRITE, F["red_jeton_alti"])
    iddia("2a 449K (RED tavani %dK) + kod Write -> IZIN (RED YOK)" % (RED_JETON // 1000),
          karar == "allow", "karar=%s" % karar)
    karar, _s = kos("Write", KOD_WRITE, F["red_tur_alti"])
    iddia("2b 499 tur (RED tavani %d) + kod Write -> IZIN (RED YOK)" % RED_TUR,
          karar == "allow", "karar=%s" % karar)

    karar, sebep = kos("Write", KOD_WRITE, F["red_jeton"])
    iddia("2c 450K JETON ekseni + kod Write -> RED", karar == "deny", "karar=%s" % karar)
    iddia("2d red gerekcesi SAYIYI ve careyi soyluyor (450K/500 + /clear)",
          "450K" in sebep and "500" in sebep and "/clear" in sebep and "KAPANIS" in sebep,
          sebep)
    karar, _s = kos("Bash", AGIR, F["red_jeton"])
    iddia("2e 450K + agir Bash -> RED", karar == "deny", "karar=%s" % karar)

    karar, sebep = kos("Write", KOD_WRITE, F["red_tur"])
    iddia("2f 500 TUR ekseni (baglam 90K, jeton esigi TETIKLENMEDI) -> RED "
          "(iki eksen VEYA ile bagli)", karar == "deny", "karar=%s" % karar)
    iddia("2g tur ekseninin gerekcesi tur SAYISINI basiyor", "tur=500" in sebep, sebep)


def vaka3():
    print("\n[3] KAPANIS MUAFIYETI — RED esiginde koruma korudugunu DURDURMAZ")
    for ad, arac, girdi in (("DEVAM.md Write", "Write", DEFTER_WRITE),
                            ("kutu Write", "Write", KUTU_WRITE),
                            ("git commit", "Bash", COMMIT),
                            ("grep (olcum)", "Bash", OLCUM),
                            ("Read", "Read", {"file_path": "/tmp/x"})):
        for eksen in ("red_jeton", "red_tur"):
            karar, _s = kos(arac, girdi, F[eksen])
            iddia("3-%s @%s -> IZIN (kapanis sinifi)" % (ad, eksen), karar == "allow",
                  "karar=%s" % karar)


def vaka4():
    print("\n[4] UYARI ESIGI — 450 tur / 300K yanar, 449 tur / 299K yanmaz")
    karar, err = kos("Write", KOD_WRITE, F["uyari_tur"])
    iddia("4a 450 TUR -> IZIN + UYARI satiri", karar == "allow" and "UYARI" in err,
          "karar=%s err=%s" % (karar, err))
    karar, err = kos("Write", KOD_WRITE, F["uyari_jeton"])
    iddia("4b 300K JETON -> IZIN + UYARI satiri", karar == "allow" and "UYARI" in err,
          "karar=%s err=%s" % (karar, err))
    iddia("4c uyari satiri YENI tavanlari basiyor (uyari %d/%dK, red %d/%dK)"
          % (UYARI_TUR, UYARI_JETON // 1000, RED_TUR, RED_JETON // 1000),
          ("uyari %d" % UYARI_TUR) in err and ("red %d" % RED_TUR) in err
          and ("uyari %dK" % (UYARI_JETON // 1000)) in err
          and ("red %dK" % (RED_JETON // 1000)) in err, err)
    karar, err = kos("Write", KOD_WRITE, F["uyari_yok"])
    iddia("4d 449 tur / 299K -> IZIN ve UYARI YOK (esik gercekten %d/%dK)"
          % (UYARI_TUR, UYARI_JETON // 1000),
          karar == "allow" and "UYARI" not in err, "karar=%s err=%s" % (karar, err))


def vaka5():
    print("\n[5] MEKANIK KOL — kod/test Write >=15 -> ucuz kata")
    karar, sebep = kos("Write", KOD_WRITE, F["mekanik"])
    iddia("5a 16 kod Write sonrasi yeni kod Write -> RED", karar == "deny",
          "karar=%s" % karar)
    iddia("5b gerekce ucuz kat cagrisini ADIYLA veriyor",
          "isci.sh" in sebep and "minimax-m3" in sebep, sebep)
    karar, _s = kos("Write", DEFTER_WRITE, F["mekanik"])
    iddia("5c AYNI oturumda DEFTER Write -> IZIN (mekanik kol defteri kesmez)",
          karar == "allow", "karar=%s" % karar)
    karar, _s = kos("Write", KOD_WRITE, F["mekanik_alti"])
    iddia("5d 14 Write (tavan ALTI) -> IZIN (esik gercekten 15)", karar == "allow",
          "karar=%s" % karar)


def vaka6(kok):
    print("\n[6] OLCULEMEDI — fail-open ama SESSIZ DEGIL")
    karar, err = kos("Write", KOD_WRITE, os.path.join(kok, "yok.jsonl"))
    iddia("6a transkript YOKken kapi GECIRIR (yanlis pozitif filoyu kilitlemez)",
          karar == "allow", "karar=%s" % karar)
    iddia("6b `OLCULEMEDI` ADIYLA basildi (sessiz bypass DEGIL)",
          "OLCULEMEDI" in err, err)


# ── MUTASYON TURU ─────────────────────────────────────────────────────────────────
# Her ÖLDÜRÜCÜ mutant, YUKARIDAKI iddialardan BIRINI adiyla hedefler; taban ile ayni
# sonucu veren mutant "HEDEFE ULASMADI" diye KIRMIZI yanar.
MUTANTLAR = [
    ("M1", "OLDURUCU", "RED_JETON = 450_000\n", "RED_JETON = 350_000\n",
     "2a — 449K RED DEGIL iddiasi GERCEKTEN 450K sabitine baglimi",
     [("Write", KOD_WRITE, "red_jeton_alti", "deny")]),
    ("M2", "OLDURUCU", "RED_TUR = 500\n", "RED_TUR = 400\n",
     "2b — 499 tur RED DEGIL iddiasi GERCEKTEN 500 sabitine baglimi",
     [("Write", KOD_WRITE, "red_tur_alti", "deny")]),
    ("M3", "OLDURUCU", "    if tur >= RED_TUR or baglam >= RED_JETON:\n",
     "    if False:\n",
     "2c/2f — RED kolu kaldirilinca 450K ve 500 tur GECMELI",
     [("Write", KOD_WRITE, "red_jeton", "allow*"),
      ("Write", KOD_WRITE, "red_tur", "allow*")]),
    ("M4", "OLDURUCU", "    if tur >= RED_TUR or baglam >= RED_JETON:\n",
     "    if tur >= RED_TUR and baglam >= RED_JETON:\n",
     "2c/2f — VEYA kolu: AND yapilinca TEK eksenli fikstur RED'den DUSER",
     [("Write", KOD_WRITE, "red_jeton", "allow*"),
      ("Write", KOD_WRITE, "red_tur", "allow*")]),
    ("M5", "OLDURUCU", "        if not kapanis_sinifi_mi(arac, girdi):\n",
     "        if True:\n",
     "3 — kapanis muafiyeti kaldirilinca DEFTER Write REDDEDILMELI",
     [("Write", DEFTER_WRITE, "red_jeton", "deny"),
      ("Bash", COMMIT, "red_tur", "deny")]),
    ("M6", "OLDURUCU", "UYARI_JETON = 300_000\n", "UYARI_JETON = 200_000\n",
     "4d — 299K'da UYARI YOK iddiasi GERCEKTEN 300K sabitine baglimi",
     [("Write", KOD_WRITE, "uyari_yok", "allow+UYARI")]),
    ("M7", "OLDURUCU", "UYARI_TUR = 450\n", "UYARI_TUR = 350\n",
     "4d — 449 turda UYARI YOK iddiasi GERCEKTEN 450 sabitine baglimi",
     [("Write", KOD_WRITE, "uyari_yok", "allow+UYARI")]),
    ("M8", "KONTROL", '"sayiyla yaz, /clear."',
     '"sayiyla yaz, /clear. (kontrol metni)"',
     "yalniz teshis METNI degisir -> HICBIR iddia degismemeli", None),
]

# Kontrol mutantinin AYNI kalmasi gereken davranis izi.
# "allow"  = izin VE uyari satiri YOK · "allow+UYARI" = izin VE uyari VAR
# "allow*" = yalniz karar olculur (uyari kolu bu iddianin konusu degil)
KONTROL_IZI = [("Write", KOD_WRITE, "red_jeton", "deny"),
               ("Write", KOD_WRITE, "red_tur", "deny"),
               ("Write", KOD_WRITE, "red_jeton_alti", "allow+UYARI"),
               ("Write", KOD_WRITE, "red_tur_alti", "allow+UYARI"),
               ("Write", DEFTER_WRITE, "red_jeton", "allow*"),
               ("Write", KOD_WRITE, "uyari_tur", "allow+UYARI"),
               ("Write", KOD_WRITE, "uyari_jeton", "allow+UYARI"),
               ("Write", KOD_WRITE, "uyari_yok", "allow"),
               ("Write", KOD_WRITE, "alt", "allow"),
               ("Write", KOD_WRITE, "mekanik", "deny")]


def _bekleneni_karsila(arac, girdi, fikstur, beklenen, betik):
    karar, metin = kos(arac, girdi, F[fikstur], betik=betik)
    if beklenen == "allow+UYARI":
        return (karar == "allow" and "UYARI" in metin), "karar=%s metin=%s" % (karar, metin[:80])
    if beklenen == "allow":
        return (karar == "allow" and "UYARI" not in metin), "karar=%s metin=%s" % (karar, metin[:80])
    if beklenen == "allow*":
        return (karar == "allow"), "karar=%s" % karar
    return (karar == beklenen), "karar=%s" % karar


def mutasyon(kaynak, tmp):
    print("\n[7] MUTASYON TURU — %d mutant (%d OLDURUCU + 1 KONTROL)"
          % (len(MUTANTLAR), len(MUTANTLAR) - 1))
    oldu = 0
    for ad, sinif, capa, yeni, hedef, izler in MUTANTLAR:
        n = kaynak.count(capa)
        if n != 1:
            iddia("7-%s capasi TEK kez TUTMADI (OLCULEMEDI)" % ad, False, "bulunan=%d" % n)
            continue
        if capa in yeni:
            iddia("7-%s capasi YENI dizgenin ICINDE (cogaltma tuzagi)" % ad, False, capa)
            continue
        yol = os.path.join(tmp, "mutant-%s-%s.py" % (ad, uuid.uuid4().hex[:8]))
        with io.open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(capa, yeni))
        if sinif == "KONTROL":
            tum, tani = True, ""
            for arac, girdi, fikstur, beklenen in KONTROL_IZI:
                ok, t = _bekleneni_karsila(arac, girdi, fikstur, beklenen, yol)
                if not ok:
                    tum, tani = False, "%s@%s -> %s" % (arac, fikstur, t)
                    break
            iddia("7-%s [KONTROL] %s (davranis izi %d nokta AYNI)"
                  % (ad, hedef, len(KONTROL_IZI)), tum, tani)
            continue
        tum, tani = True, ""
        for arac, girdi, fikstur, beklenen in izler:
            ok, t = _bekleneni_karsila(arac, girdi, fikstur, beklenen, yol)
            if not ok:
                tum, tani = False, "%s@%s bekleniyordu=%s %s — mutant HEDEFE ULASMADI" % (
                    arac, fikstur, beklenen, t)
                break
        if tum:
            oldu += 1
        iddia("7-%s [OLDURUCU] %s" % (ad, hedef), tum, tani)
    return oldu


def main():
    print("BAGLAM KOTASI KAPISI — KABUL TESTI (RED %d tur / %dK · UYARI %d tur / %dK)"
          % (RED_TUR, RED_JETON // 1000, UYARI_TUR, UYARI_JETON // 1000))
    with io.open(KAPI, encoding="utf-8") as f:
        kaynak = f.read()
    sha_once = hashlib.sha256(kaynak.encode()).hexdigest()

    # Kapinin CANLI sabitleri bu testin civilediklerine ESIT mi? (bayat kopya nobeti)
    for ad, deger in (("RED_TUR", RED_TUR), ("RED_JETON", RED_JETON),
                      ("UYARI_TUR", UYARI_TUR), ("UYARI_JETON", UYARI_JETON)):
        beklenen = "\n%s = %s\n" % (ad, "%d" % deger if deger < 1000
                                    else "{:_}".format(deger))
        iddia("0-%s kaynakta TAM olarak civilenen deger" % ad,
              kaynak.count(beklenen) == 1, "aranan=%r" % beklenen)

    kok = tempfile.mkdtemp(prefix="baglam-kotasi-kt-")
    tmp = tempfile.mkdtemp(prefix="baglam-mutant-")
    try:
        fikstur_kur(kok)
        vaka1()
        vaka2()
        vaka3()
        vaka4()
        vaka5()
        vaka6(kok)
        oldu = mutasyon(kaynak, tmp)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)

    with io.open(KAPI, encoding="utf-8") as f:
        iddia("8 MUTANT gercek kapiya YAZILMADI (sha256 once==sonra)",
              hashlib.sha256(f.read().encode()).hexdigest() == sha_once)

    print("\n" + "-" * 70)
    print("MUTANT: OLDU=%d / OLDURUCU=%d · KACAN=%d"
          % (oldu, len(MUTANTLAR) - 1, len(MUTANTLAR) - 1 - oldu))
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (len(gecti) + len(kaldi), len(gecti), len(kaldi)))
    if kaldi:
        print("DUSENLER=" + ",".join(kaldi))
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
