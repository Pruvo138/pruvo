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
import importlib.util
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

# guard_olu_mu() invariant'i icin gate MODUL olarak yuklenir (import-zamani yan etki YOK:
# main() yalniz __main__ altinda kosar). VERI_BASENAME / KAYNAK_UZANTI kumelerini OKUR.
_gate_spec = importlib.util.spec_from_file_location("mimar_commit_kapisi_gate", GATE)
GATE_MOD = importlib.util.module_from_spec(_gate_spec)
_gate_spec.loader.exec_module(GATE_MOD)

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
    """Veri duzlemi korumasini kaldir: env yokken urunler.json bloklanmasin.
    (konfig korumasi KORUNUR — bu mutasyon YALNIZ veri_mi'yi dusurur.)"""
    hedef = "    return kaynak_mi(yol) or veri_mi(yol) or konfig_veri_mi(yol)"
    yeni = "    return kaynak_mi(yol) or konfig_veri_mi(yol)  # MUTASYON M2"
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


# M4 KALDIRILDI (25 Tem): "kaynak_mi VERI_BASENAME savunma dallanmasini kaldir" mutasyonu
# NOBETSIZDI (sifir kirmizi). Dal ('if ... or basename in VERI_BASENAME: return False')
# yalniz bir VERI_BASENAME girdisinin uzantisi KAYNAK_UZANTI'da olsaydi davranis
# degistirirdi; VERI_BASENAME'in tamami .json (kaynak-disi) oldugundan uzanti kontrolu
# zaten ayni sonucu verir -> mutasyon hicbir kabul vakasini kizartamaz (kapi-disiplin-ilkesi
# ihlali). Dal, GATE'te savunma-derinligi olarak KALIR (bkz. kaynak_mi docstring). Mutasyon
# yerine guard_olu_mu() invariant'i eklendi: 'olu' varsayim bozulursa (bir veri basename'i
# kaynak uzantisi kazanirsa) MAKINE ile patlar ve GERCEK bir sentinel gerektigini bildirir.


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


def mutasyon_m8(s):
    """T3 2. tur nobetcisi: TEMIZ seridin KOK-TAM-YOL kontrolunu basename'e geri
    dusur (curutucu sinifi: tools/urunler.json / a/b/.urun-kaynaklari.json /
    backslash-adli yol temiz kategoriye girer). Beklenen KIRMIZI: 18, 19, 20."""
    hedef = "    return temiz in VERI_BASENAME"
    yeni = "    return _basename(temiz) in VERI_BASENAME  # MUTASYON M8"
    assert hedef in s, "M8 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m9(s):
    """MUT-KONFIG-GENIS: konfig_veri_mi'yi KOK-TAM-YOL yerine basename-bazli yap
    (blok tarafini konfig icin GENISLETIR: alt-dizin/backslash konfigurlar.js de
    'muaf' sayilir). Beklenen KIRMIZI: 25 (alt-dizin) — worker'da exit 1 yerine 0
    doner. 26 (backslash) da kizarir. Nobetci konfig muafiyetinin DAR (tek tam-yol)
    kalmasini korur."""
    hedef = "    return temiz == KONFIG_VERI_YOL"
    yeni = '    return _basename(yol) == "konfigurlar.js"  # MUTASYON M9'
    assert hedef in s, "M9 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def mutasyon_m10(s):
    """MUT-KONFIG-KALDIR: korunan_mi'den 'or konfig_veri_mi(yol)'u cikar (env YOKKEN
    konfigurlar.js bloklanmasin). Beklenen KIRMIZI: 23 (env-siz konfig commit) —
    exit 1 yerine 0 doner. Nobetci konfig'in env'siz BLOKLU kalmasini korur."""
    hedef = "    return kaynak_mi(yol) or veri_mi(yol) or konfig_veri_mi(yol)"
    yeni = "    return kaynak_mi(yol) or veri_mi(yol)  # MUTASYON M10"
    assert hedef in s, "M10 hedefi bulunamadi"
    return s.replace(hedef, yeni)


def guard_olu_mu():
    """kaynak_mi'deki VERI_BASENAME savunma dalinin 'davranissal olarak OLU' oldugunu
    dogrular (M4 KALDIRILDI gerekcesi). Dal yalniz bir VERI_BASENAME girdisinin uzantisi
    KAYNAK_UZANTI'da olsaydi CANLANIRDI. Doner: guard'i canlandiran (varsa) VERI_BASENAME
    girdileri. BOS liste => dal olu => M4'un olmamasi HAKLI. Dolu liste => dal canli =>
    GERCEK bir kirmizi-mutasyon sentinel'i ISTENIR."""
    return sorted(
        b for b in GATE_MOD.VERI_BASENAME
        if os.path.splitext(b)[1].lower() in GATE_MOD.KAYNAK_UZANTI
    )


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
        # M4 KALDIRILDI (25 Tem) — NOBETSIZDI; yerine guard_olu_mu() invariant'i (bkz. main).
        ("M5", mutasyon_m5(KAYNAK), ".py kaynak uzantisi listeden dusuruldu"),
        ("M6", mutasyon_m6(KAYNAK), "T3: gecis veri-DISI dosyaya genisletildi"),
        ("M7", mutasyon_m7(KAYNAK), "T3: gecis yine allow-escape diye loglaniyor"),
        ("M8", mutasyon_m8(KAYNAK), "T3-2: kok-tam-yol kontrolu basename'e dustu"),
        ("M9", mutasyon_m9(KAYNAK), "KONFIG-GENIS: konfig muafiyeti basename'e dustu"),
        ("M10", mutasyon_m10(KAYNAK), "KONFIG-KALDIR: korunan_mi'den konfig cikti"),
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
        # ONCE-* REFERANS satiridir (mutasyon DEGIL, taban gate): dogru gate sifir kirmizi
        # verir -> NOBETSIZ SAYILMAZ (yoksa varsayilan HEAD kosumu daima kizardi; AYNI-ICERIK
        # durumu zaten ACIKLAMA sutununda ayri isaretlenir). Yalniz GERCEK mutasyonlar sentinel ister.
        referans = etiket.startswith("ONCE-")
        if kirmizi:
            etiketli = ",".join(kirmizi)
        else:
            etiketli = "(REFERANS - taban)" if referans else "(YOK - NOBETSIZ)"
        if not kirmizi and not referans:
            nobetsiz.append(etiket)
        print("{:<16}{:<7}{:<22}{}".format(etiket, rc, etiketli, aciklama))
    print("-" * 88)
    if nobetsiz:
        print("NOBETSIZ mutasyonlar: " + ", ".join(nobetsiz))
    else:
        print("Her mutasyon en az bir vakayi KIRMIZI yakti.")

    # M4 KALDIRILDI yerine: kaynak_mi VERI_BASENAME savunma dalinin 'davranissal olarak
    # olu' varsayimini MAKINE ile dogrula (yalniz yorumla degil). Canli girdi cikarsa dal
    # sentinel ISTER ve bu kosum KIRMIZI doner.
    canli = guard_olu_mu()
    if canli:
        print("!! INVARIANT BOZULDU: VERI_BASENAME artik kaynak-uzantili girdi iceriyor: "
              + ", ".join(canli) + " — kaynak_mi VERI savunma dali CANLANDI; GERCEK bir "
              "kirmizi-mutasyon sentinel'i EKLENMELI (M4'u geri getir).")
    else:
        print("INVARIANT OK: kaynak_mi VERI_BASENAME savunma dali davranissal olarak OLU "
              "(VERI_BASENAME tamamen kaynak-disi) — M4 hakli olarak KALDIRILDI; dal "
              "savunma-derinligi olarak GATE'te kalir.")

    print("Gercek gate degismedi (mutasyon yalniz " + TMP + " altinda).")
    return 1 if (nobetsiz or canli) else 0


if __name__ == "__main__":
    sys.exit(main())
