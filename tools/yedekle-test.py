#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/yedekle.py'nin SKILL KAPSAMI + SIR NOBETI.

NEDEN VAR: ~/.claude/skills (merge-kapisi + ege-diyalog) GIT DISINDA, tek kopya bu makinede.
yedekle.py onu Drive'a tasiyan tek yol. Iki sessiz-hata sinifi var:
  (A) KAPSAM CURUMESI — skills bloku bozulur/silinir, arac YINE "bitti" der, disk kaybinda
      mutasyon-kanitli dal-olc.py + kabul-test.py topluca gider (kimse fark etmez).
  (B) SIR SIZINTISI — skills agaci vetted degil; oraya dusen bir jeton/anahtar yedek klasorune
      (paylasilabilir Drive) tasinir.
Bu yuzden IKI iddianin da KIRMIZI-MUTASYON kaniti var: kapsami/nobeti devre disi birakan
mutant surumde ilgili kontrol KIRMIZI yanmalidir; yanmazsa kontrol olcmuyor demektir.

Kosum:  python3 tools/yedekle-test.py
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")

# Skill agacinda BULUNMASI zorunlu iki dosya (26 Tem'de mutasyon kanitiyla sertlestirildi).
ZORUNLU = ("merge-kapisi/scripts/dal-olc.py", "merge-kapisi/evals/kabul-test.py")

# Sentetik sir fikstur govdesi — GERCEK anahtar DEGIL, imza tanima testi icin.
SAHTE_ANAHTAR = ("-----BEGIN RSA PRIVATE KEY-----\n"
                 "SAHTE-FIKSTUR-VERISI-GERCEK-ANAHTAR-DEGIL\n"
                 "-----END RSA PRIVATE KEY-----\n")

SONUC = []


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok), ayrinti))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mutant_yaz(dizin, degisimler, ad="mutant.py"):
    """yedekle.py'nin mutasyonlu kopyasini uretir. Capa bulunamazsa (kod degismis)
    RuntimeError -> testin kendisi KIRMIZI yanar (bayat mutasyon capasi sessizce gecmesin)."""
    with open(YEDEKLE, encoding="utf-8") as f:
        kaynak = f.read()
    for eski, yeni in degisimler:
        if eski not in kaynak:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r" % eski)
        kaynak = kaynak.replace(eski, yeni, 1)
    hedef = os.path.join(dizin, ad)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak)
    # yedekle.py import aninda kardes drive_yolu'yu cagirir -> yanina kopyala.
    shutil.copy2(DRIVE_YOLU, os.path.join(dizin, "drive_yolu.py"))
    return hedef


def fikstur_kur(kok):
    """Sentetik skills agaci: 1 normal dosya + 3 sir + 1 turetilmis gurultu."""
    os.makedirs(os.path.join(kok, "ornek-skill", "notlar"), exist_ok=True)
    os.makedirs(os.path.join(kok, "ornek-skill", "scripts", "__pycache__"), exist_ok=True)
    with open(os.path.join(kok, "ornek-skill", "SKILL.md"), "w") as f:
        f.write("# normal skill icerigi\n")
    with open(os.path.join(kok, "ornek-skill", ".r2-credentials.json"), "w") as f:
        f.write('{"access_key_id":"SAHTE","secret_access_key":"SAHTE"}\n')
    with open(os.path.join(kok, "ornek-skill", "notlar", "gizli-token.txt"), "w") as f:
        f.write("sahte-jeton-govdesi\n")
    with open(os.path.join(kok, "ornek-skill", "kurulum.md"), "w") as f:
        f.write("kurulum notlari\n" + SAHTE_ANAHTAR)
    with open(os.path.join(kok, "ornek-skill", "scripts", "__pycache__", "x.pyc"), "wb") as f:
        f.write(b"\x00\x01derlenmis")
    return {
        "normal": "ornek-skill/SKILL.md",
        "sirlar": ["ornek-skill/.r2-credentials.json",
                   "ornek-skill/notlar/gizli-token.txt",
                   "ornek-skill/kurulum.md"],
    }


def main():
    yedekle = modul_yukle(YEDEKLE, "yedekle_gercek")

    # ---------------- 1) KAPSAM (gercek agac) ----------------
    print("\n1) KAPSAM — gercek ~/.claude/skills agaci planda mi?")
    dahil, haric, gurultu = yedekle.skills_plani()
    if not os.path.isdir(yedekle.SKILLS):
        kontrol("skills dizini var", False, yedekle.SKILLS + " YOK (bu makinede olcum yapilamaz)")
    else:
        kontrol("skills dizini var", True, "%d dahil / %d haric / %d gurultu"
                % (len(dahil), len(haric), len(gurultu)))
        for z in ZORUNLU:
            kontrol("planda: " + z, z in dahil)
        kontrol("gurultu (pyc/__pycache__) plana GIRMEDI",
                not any(g.endswith(".pyc") for g in dahil))
        kontrol("gercek agacta sir nobeti ELEMESI yok (temiz agac)", not haric,
                "elenen: " + ", ".join(g for g, _ in haric) if haric else "")

    # ---------------- 2) KURU KOSUM (ucdan uca, YAZMAZ) ----------------
    print("\n2) KURU KOSUM — --kuru listeler, hicbir sey yazmaz")
    r = subprocess.run([sys.executable, YEDEKLE, "--kuru"], capture_output=True, text=True)
    kontrol("--kuru exit 0", r.returncode == 0, "rc=%d" % r.returncode)
    kontrol("cikti 'KURU KOSUM' diyor", "KURU KOSUM" in r.stdout)
    for z in ZORUNLU:
        kontrol("kuru listede: skills/" + z, ("skills/" + z) in r.stdout)
    kontrol("kuru kosumda 'bitti ->' YOK (gercek yedek calismadi)", "bitti ->" not in r.stdout)

    # ---------------- 3) KIRMIZI MUTASYON: skills kapsam disi ----------------
    print("\n3) KIRMIZI-MUTASYON (kapsam) — skills plandan cikarilirsa kontrol kirmizi mi?")
    with tempfile.TemporaryDirectory() as td:
        mut = mutant_yaz(td, [("    dahil, haric, gurultu = skills_plani()",
                               "    dahil, haric, gurultu = [], [], []  # MUTANT")])
        rm = subprocess.run([sys.executable, mut, "--kuru"], capture_output=True, text=True)
        kontrol("mutant kosuyor (exit 0)", rm.returncode == 0, "rc=%d" % rm.returncode)
        eksik = [z for z in ZORUNLU if ("skills/" + z) not in rm.stdout]
        kontrol("MUTANTTA zorunlu skill dosyalari listede YOK (kontrol KIRMIZI yanardi)",
                len(eksik) == len(ZORUNLU), "kayip: %d/%d" % (len(eksik), len(ZORUNLU)))

    # ---------------- 4) SIR NOBETI (sentetik) ----------------
    print("\n4) SIR NOBETI — sentetik sir dosyalari pakete GIRMEMELI")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        f = fikstur_kur(kok)
        d, h, g = yedekle.skills_plani(kok=kok)
        h_yollar = [y for y, _ in h]
        kontrol("normal dosya planda", f["normal"] in d)
        for s in f["sirlar"]:
            kontrol("sir pakete GIRMEDI: " + s, s not in d)
            kontrol("sir SEBEPLE raporlandi: " + s, s in h_yollar)
        kontrol("pyc gurultu olarak ayrildi", not any(x.endswith(".pyc") for x in d + h_yollar))
        sebepler = " | ".join(s for _, s in h)
        kontrol("sebep metni sirrin KENDISINI icermiyor",
                "SAHTE-FIKSTUR-VERISI" not in sebepler and "sahte-jeton-govdesi" not in sebepler,
                sebepler)

    # ---------------- 5) KIRMIZI MUTASYON: sir nobeti devre disi ----------------
    print("\n5) KIRMIZI-MUTASYON (sir nobeti) — nobet kapatilirsa sirlar sizar mi?")
    with tempfile.TemporaryDirectory() as td:
        mut = mutant_yaz(td, [("            sebep = sir_sebebi(tam, ad)",
                               "            sebep = None  # MUTANT")])
        mmod = modul_yukle(mut, "yedekle_mutant_sir")
        kok = os.path.join(td, "skills")
        f = fikstur_kur(kok)
        d, h, _g = mmod.skills_plani(kok=kok)
        sizan = [s for s in f["sirlar"] if s in d]
        kontrol("MUTANTTA sirlar pakete SIZDI (kontrol KIRMIZI yanardi)",
                len(sizan) == len(f["sirlar"]), "sizan: %d/%d" % (len(sizan), len(f["sirlar"])))

    # ---------------- 6) IDEMPOTENS ----------------
    print("\n6) IDEMPOTENS — iki kez kosmak mukerrer yigmaz/bozmaz")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        hedef = os.path.join(td, "backup-skills")
        fikstur_kur(kok)
        d, h, _g = yedekle.skills_plani(kok=kok)
        y1, b1 = yedekle.skills_yaz(kok, hedef, d, h)
        kume1 = sorted(os.path.relpath(os.path.join(kk, a), hedef)
                       for kk, _, aa in os.walk(hedef) for a in aa)
        y2, b2 = yedekle.skills_yaz(kok, hedef, d, h)
        kume2 = sorted(os.path.relpath(os.path.join(kk, a), hedef)
                       for kk, _, aa in os.walk(hedef) for a in aa)
        kontrol("iki kosumda ayni dosya kumesi", kume1 == kume2, "%d dosya" % len(kume2))
        kontrol("yazilan sayisi sabit", y1 == y2 == len(d), "%d/%d/%d" % (y1, y2, len(d)))
        kontrol("hedefte sir dosyasi YOK",
                not any(x.endswith(".r2-credentials.json") or "token" in x for x in kume2))

    # ---------------- 7) BAYAT SIR KOPYASI NOBETI ----------------
    print("\n7) BAYAT SIR NOBETI — filtresiz eski surumun biraktigi kopya yakalaniyor mu?")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        hedef = os.path.join(td, "backup-skills")
        fikstur_kur(kok)
        d, h, _g = yedekle.skills_plani(kok=kok)
        # Eski (filtresiz copytree) surumun birakacagi kopyayi taklit et:
        eski = os.path.join(hedef, "ornek-skill", ".r2-credentials.json")
        os.makedirs(os.path.dirname(eski), exist_ok=True)
        with open(eski, "w") as fh:
            fh.write("eski sizmis kopya\n")
        _y, bayat = yedekle.skills_yaz(kok, hedef, d, h, sir_temizle=False)
        kontrol("bayat sir kopyasi TESPIT edildi", eski in bayat, "%d bulundu" % len(bayat))
        kontrol("varsayilan SILMEZ (veri silme elle onaylanir)", os.path.exists(eski))
        _y, bayat2 = yedekle.skills_yaz(kok, hedef, d, h, sir_temizle=True)
        kontrol("--sir-temizle ile SILINDI", not os.path.exists(eski))

    # ---------------- 8) BILINMEYEN BAYRAK = FAIL-CLOSED ----------------
    print("\n8) FAIL-CLOSED — yazim hatasi olan bayrak GERCEK yedek baslatmasin")
    r = subprocess.run([sys.executable, YEDEKLE, "--kuruu"], capture_output=True, text=True)
    kontrol("bilinmeyen bayrak exit != 0", r.returncode != 0, "rc=%d" % r.returncode)
    kontrol("bilinmeyen bayrakta yedek CALISMADI",
            "bitti ->" not in r.stdout and "yedek:" not in r.stdout)

    # ---------------- OZET ----------------
    kirmizi = [a for a, ok, _ in SONUC if not ok]
    print("\n" + "=" * 70)
    print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    if kirmizi:
        for a in kirmizi:
            print("  ❌ " + a)
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
