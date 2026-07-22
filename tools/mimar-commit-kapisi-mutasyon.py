#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kirmizi-mutasyon olcumu: mimar-commit-kapisi daraltmasinin nobetcisi var mi?

Dalda HICBIR mutasyon birakmaz: gate dosyasi /tmp'ye KOPYALANIR, kopya mutasyona
ugrar, kabul testi o kopyaya yoneltilir. Gercek gate'e DOKUNULMAZ.

Kullanim:
    python3 tools/mimar-commit-kapisi-mutasyon.py [ONCE_REF]

ONCE_REF = daraltma ONCESI surumu tasiyan git ref'i (varsayilan: HEAD).
DIKKAT — BAYAT TABAN TUZAGI: daraltma commit'lendikten SONRA HEAD artik yeni
surumdur; o zaman ONCE_REF olarak daraltmadan onceki SHA verilmelidir. Ref'in
icerigi bugunku gate ile AYNI cikarsa satir "AYNI-ICERIK" damgalanir ve kanit
sayilmaz (sessiz yesil yerine gorunur uyari).
"""
import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
WT = os.path.dirname(TOOLS)
GATE = os.path.join(TOOLS, "mimar-commit-kapisi.py")
TEST = os.path.join(TOOLS, "mimar-commit-kapisi-test.py")
TMP = tempfile.mkdtemp(prefix="kapi-mutasyon-")

KAYNAK = open(GATE, encoding="utf-8").read()

ONCE_REF = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
ONCE_SURUM = subprocess.run(
    ["git", "-C", WT, "show", ONCE_REF + ":tools/mimar-commit-kapisi.py"],
    capture_output=True, text=True).stdout
ONCE_AYNI = (ONCE_SURUM.strip() == KAYNAK.strip())


def mutasyon_m1(s):
    """Daraltmayi geri al: worker onayi her seyi acsin (eski davranis)."""
    hedef = """    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":
        # DAR bypass: worker onayi YALNIZ veri düzlemini açar. Kaynak varsa reddet.
        if kaynaklar:"""
    yeni = """    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":
        # MUTASYON M1: daraltma devre disi
        if False:"""
    assert hedef in s, "M1 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m2(s):
    """Veri duzlemi korumasini kaldir: env yokken urunler.json bloklanmasin."""
    hedef = "    return kaynak_mi(yol) or veri_mi(yol)"
    yeni = "    return kaynak_mi(yol)  # MUTASYON M2"
    assert hedef in s, "M2 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m3(s):
    """Worktree muafiyetini kaldir."""
    hedef = """    if kok != ANA_REPO:
        return 0"""
    yeni = """    if False:  # MUTASYON M3
        return 0"""
    assert hedef in s, "M3 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m4(s):
    """kaynak_mi icindeki VERI_BASENAME savunma dallanmasini kaldir."""
    hedef = "    if not basename or basename in VERI_BASENAME:"
    yeni = "    if not basename:  # MUTASYON M4"
    assert hedef in s, "M4 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m5(s):
    """Kaynak uzanti kumesinden .py'yi dusur."""
    hedef = 'KAYNAK_UZANTI = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".sql"}'
    yeni = 'KAYNAK_UZANTI = {".js", ".mjs", ".ts", ".html", ".css", ".sql"}  # MUTASYON M5'
    assert hedef in s, "M5 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m6(s):
    """T3 genisletme nobetcisi: veri-duzlemi gecisini VERI-DISI dosyaya genislet
    (kosul 'her staged veri' -> 'staged bos degil'). Beklenen KIRMIZI: 16, 17
    (allow-escape yerine veri-duzlemi-gecis loglanir -> log muhasebesi bozulur)."""
    hedef = "        if staged and len(veriler) == len(staged):"
    yeni = "        if staged:  # MUTASYON M6: genisletme"
    assert hedef in s, "M6 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m7(s):
    """T3 geri-alma nobetcisi: mesru veri partisi yine 'allow-escape' diye loglansin
    (eski davranis). Beklenen KIRMIZI: 1, 2, 3 (escape muhasebesi yine kirlenir)."""
    hedef = '                gitdir, kok, "veri-duzlemi-gecis",'
    yeni = '                gitdir, kok, "allow-escape",  # MUTASYON M7'
    assert hedef in s, "M7 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def kostur(etiket, icerik):
    yol = os.path.join(TMP, "mutant-" + etiket + ".py")
    acik = open(yol, "w", encoding="utf-8")
    acik.write(icerik)
    acik.close()
    sonuc = subprocess.run([sys.executable, TEST, yol], capture_output=True, text=True)
    kirmizi = re.findall(r"^\s*(\d+)\s+exit \d+\s+exit \d+\s+KIRMIZI", sonuc.stdout, re.M)
    return sonuc.returncode, kirmizi


def main():
    once_not = "daraltma ONCESI surum (ref: %s)" % ONCE_REF
    if ONCE_AYNI:
        once_not = "!! AYNI-ICERIK: ref %s bugunku gate ile ayni — KANIT DEGIL" % ONCE_REF
    vakalar = [
        ("ONCE-" + ONCE_REF[:8], ONCE_SURUM, once_not),
        ("M1", mutasyon_m1(KAYNAK), "worker bypass daraltmasi devre disi"),
        ("M2", mutasyon_m2(KAYNAK), "env-yok veri korumasi devre disi"),
        ("M3", mutasyon_m3(KAYNAK), "worktree muafiyeti devre disi"),
        ("M4", mutasyon_m4(KAYNAK), "kaynak_mi VERI istisnasi devre disi"),
        ("M5", mutasyon_m5(KAYNAK), ".py kaynak uzantisi listeden dusuruldu"),
        ("M6", mutasyon_m6(KAYNAK), "T3: gecis veri-DISI dosyaya genisletildi"),
        ("M7", mutasyon_m7(KAYNAK), "T3: gecis yine allow-escape diye loglaniyor"),
    ]
    print("=" * 88)
    print("KIRMIZI-MUTASYON OLCUMU — gate KOPYASI mutasyona ugrar, DAL TEMIZ KALIR")
    print("test : " + TEST)
    print("tmp  : " + TMP)
    print("=" * 88)
    print("{:<16}{:<7}{:<22}{}".format("MUTASYON", "EXIT", "KIRMIZI VAKALAR", "ACIKLAMA"))
    print("-" * 88)
    nobetsiz = []
    for etiket, icerik, aciklama in vakalar:
        rc, kirmizi = kostur(etiket, icerik)
        etiketli = ",".join(kirmizi) if kirmizi else "(YOK - NOBETSIZ)"
        if not kirmizi:
            nobetsiz.append(etiket)
        print("{:<16}{:<7}{:<22}{}".format(etiket, rc, etiketli, aciklama))
    print("-" * 88)
    if nobetsiz:
        print("NOBETSIZ mutasyonlar: " + ", ".join(nobetsiz))
    else:
        print("Her mutasyon en az bir vakayi KIRMIZI yakti.")
    print("Gercek gate degismedi (mutasyon yalniz " + TMP + " altinda).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
