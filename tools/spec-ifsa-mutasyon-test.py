#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/spec-ifsa-mutasyon-test.py — tools/spec-ifsa-kapisi.py KABUL BATARYASININ
MUTASYON SURUCUSU. Kapinin BEYAN EDILMIS iddialarinin (bugun 28) her birinin AYIRT
EDICI bir mutantla OLDURULEBILDIGINI olcer.

NEDEN VAR ([[mutasyon-kaniti-yeniden-uretilebilir]]): "batarya kostu" iddiasi KANIT
DEGILDIR; surucu depoda DURMALI ve yeniden kosulabilmelidir. Kabul, cikis kodu degil
OLCULEN SAYIDIR: her mutant TEK bir IDDIA'yi dusurmeli, dusen etiket beyan edilenle
TAM ESIT olmali, iddia sayisi SABIT kalmali ve hicbir mutant COKMEMELIDIR (cokme
kirmiziyla karisir — `Traceback` sayisi 0 olmali).

🔴 CANLI DOSYAYA YAZMAZ. Mutant, kapinin kaynagi GECICI bir dizine KOPYALANIP orada
uygulanir. Surucu, kapinin kaynak sha256'sini ONCE ve SONRA olcer ve esit degilse
KIRMIZI yanar — "yazmadim" iddiasi da OLCULUR.

Kullanim:
    python3 tools/spec-ifsa-mutasyon-test.py            # tum bataryayi kostur
    python3 tools/spec-ifsa-mutasyon-test.py --liste    # mutant<->iddia eslemesini yaz
Cikis kodu: 0 = her mutant TEK KIRMIZI + beyana esit, 1 = sapma, 2 = OLCULEMEDI.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

KAPI = "tools/spec-ifsa-kapisi.py"
MODUL = "tools/git_ortami.py"   # kapinin import ettigi TEK KAYNAK (kopyayla tasinir)
# 22 taban + KOK ekseni 3 ("yanlis agacta yesil" 2 + kanca/worktree 1) + EKO 2
# + F ek tuzagi 1 (11 Agu 2026: Turkce "-sizdir" sol kelime siniri)
BEKLENEN_IDDIA_SAYISI = 28


# (mutant_adi, eski_metin, yeni_metin, dusmesi_beklenen_TEK_iddia)
# Eski metinler kapinin kaynagindan BIREBIR alinir; bulunamazsa surucu KIRMIZI yanar
# (bayat mutant tablosu sessizce yesil gecemez).
MUTANTLAR = (
    # --- EKSEN A ---
    ("MUT-A-KOR", "    for m in _A_KOVA_SOZU.finditer(satir):",
     "    for m in ():", "IDDIA-A1"),
    ("MUT-A-GENIS", '_A_JETON = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")',
     '_A_JETON = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)[^`]*`")',
     "IDDIA-A2"),
    # --- EKSEN B ---
    ("MUT-B-KOR", '_B_ONEK = ("ic-",)', '_B_ONEK = ()\n_B_ISARET = frozenset()',
     "IDDIA-B1"),
    ("MUT-B-GENIS", '            if any(s.startswith(o) for o in _B_ONEK) or \\\n'
                    '                    any(parca in _B_ISARET for parca in re.split(r"[-_.]", s)):\n'
                    '                isaretli = True\n',
     '            if True or any(s.startswith(o) for o in _B_ONEK) or \\\n'
     '                    any(parca in _B_ISARET for parca in re.split(r"[-_.]", s)):\n'
     '                isaretli = True\n',
     "IDDIA-B2"),
    # --- EKSEN C ---
    ("MUT-C-KOR", "    for m in _C_SIR.finditer(satir):\n"
                  "        if _projeye_ozgu_mu(m.group(1)):\n"
                  "            jetonlar.append(m.group(0))\n",
     "    for m in _C_SIR.finditer(satir):\n"
     "        if False:\n"
     "            jetonlar.append(m.group(0))\n",
     "IDDIA-C1"),
    ("MUT-C-GENIS", "    ilk = re.split(r\"[_\\-]\", ad.strip(\"`\"), maxsplit=1)[0].upper()\n"
                    "    return ilk not in _SATICI_JETONLARI",
     "    ilk = re.split(r\"[_\\-]\", ad.strip(\"`\"), maxsplit=1)[0].upper()\n"
     "    return True or ilk not in _SATICI_JETONLARI",
     "IDDIA-C2"),
    # --- EKSEN D ---
    ("MUT-D-KOR", "    for rx in (_D_HOST, _D_DEPO_HOST, _D_HEX32):",
     "    for rx in (_D_DEPO_HOST,):", "IDDIA-D1"),
    ("MUT-D-GENIS",
     '_D_HOST = re.compile(r"\\b[a-z0-9][a-z0-9-]*\\.[a-z0-9][a-z0-9-]*\\.(?:workers|pages)\\.dev\\b", re.I)',
     '_D_HOST = re.compile(r"\\b(?:[a-z0-9][a-z0-9-]*\\.)*(?:workers|pages)\\.dev\\b", re.I)',
     "IDDIA-D2"),
    # --- EKSEN E ---
    ("MUT-E-KOR", "    return _iddia(bool(_E_KANAL.search(satir) and _E_ELLE.search(satir)))",
     "    return _iddia(bool(_E_KANAL.search(satir) and _E_ELLE.search(satir) and False))",
     "IDDIA-E1"),
    ("MUT-E-GENIS", "    return _iddia(bool(_E_KANAL.search(satir) and _E_ELLE.search(satir)))",
     "    return _iddia(bool(_E_KANAL.search(satir) or _E_ELLE.search(satir)))",
     "IDDIA-E2"),
    # --- EKSEN F ---
    ("MUT-F-KOR",
     "    return _iddia(bool(_F_ZAYIFLIK.search(satir) and _F_KAPANMAMIS.search(satir)))",
     "    return _iddia(bool(_F_ZAYIFLIK.search(satir) and _F_KAPANMAMIS.search(satir)\n"
     "                       and False))",
     "IDDIA-F1"),
    # 🔴 MUT-F-GENIS TEK TARAFLIDIR (11 Agu 2026'da `or`dan degistirildi): iki isaret
    # sartini KALDIRIR ama yalniz ZAYIFLIK ayagini birakir. `or` varyanti IDDIA-F2 ile
    # BIRLIKTE IDDIA-F3'u de dusuruyordu (F3 satirlarinin hepsi GERCEK bir KAPANMAMIS
    # jetonu tasir — tasimasalardi daraltmayi OLCEMEZLERDI), yani TEK-KIRMIZI
    # sozlesmesini bozuyordu. Olculen sey ayni: "iki isaret de ZORUNLU" iddiasi.
    ("MUT-F-GENIS",
     "    return _iddia(bool(_F_ZAYIFLIK.search(satir) and _F_KAPANMAMIS.search(satir)))",
     "    return _iddia(bool(_F_ZAYIFLIK.search(satir)))",
     "IDDIA-F2"),
    # MUT-F-BAS-SINIR-KOR: 11 Agu 2026 DARALTMASINI geri alir (sol kelime siniri
    # bosaltilir) -> "-sizdir" ile biten masum Turkce sifatlar yeniden ZAYIFLIK sayilir.
    # Daraltma FAIL-OPEN yondedir; kabul bu yuzden mutasyonla verilir. IDDIA-F1 sol
    # sinirdan BAGIMSIZDIR (sinir kalkinca da vurur), IDDIA-F2 zaten KAPANMAMIS jetonu
    # tasimaz -> TEK KIRMIZI: IDDIA-F3.
    ("MUT-F-BAS-SINIR-KOR", '_BAS_SINIR = r"(?<![^\\W_])"', '_BAS_SINIR = r""',
     "IDDIA-F3"),
    # --- BEYAN yuzeyi (konfigurasyon) ---
    ("MUT-BEYAN-KOR", '    ("A", "depolama-kovasi", _eksen_a, (ANLATIM, BEYAN)),',
     '    ("A", "depolama-kovasi", _eksen_a, (ANLATIM,)),', "IDDIA-BEYAN1"),
    ("MUT-BEYAN-GENIS", '    ("C", "sir-degisken-adi", _eksen_c, (ANLATIM,)),',
     '    ("C", "sir-degisken-adi", _eksen_c, (ANLATIM, BEYAN)),', "IDDIA-BEYAN2"),
    # --- YUZEY ayrimi: ISLEVI GEREGI TASINAN AD ile ANLATILAN TOPOLOJI ---
    ("MUT-YUZEY-KOR", '        if d.startswith("/*"):\n'
                      '            yield i, s, ANLATIM\n'
                      '            if "*/" not in d[2:]:',
     '        if d.startswith("/*"):\n'
     '            yield i, s, ICRA\n'
     '            if "*/" not in d[2:]:', "IDDIA-YUZEY1"),
    ("MUT-YUZEY-GENIS", '        yield (i, s[k + 2:], ANLATIM) if k >= 0 else (i, s, ICRA)',
     '        yield (i, s, ANLATIM)', "IDDIA-YUZEY2"),
    ("MUT-PY-KOR", "        if belge is not None and i in belge:\n"
                   "            yield i, s, ANLATIM\n",
     "        if False:\n"
     "            yield i, s, ANLATIM\n", "IDDIA-YUZEY3"),
    ("MUT-PY-GENIS", "        if belge is not None and i in belge:",
     '        if belge is not None and ("\\"\\"\\"" in s or i in belge):', "IDDIA-YUZEY4"),
    # --- KAPSAM: bilinmeyen uzanti yuzey URETMEZ ---
    ("MUT-KAPSAM-GENIS", "    return iter(())  # kapsam disi uzanti: hic satir uretilmez",
     "    return _yuzey_md(satirlar)", "IDDIA-KAPSAM"),
    # --- EKO ELEMESI: daraltma DARALTIR ama fail-OPEN yapmaz ---
    # MUT-EKO-GENIS, daraltmanin en pahali bozulma yonudur: eleme KOSULSUZ uygulanirsa
    # ICRA yuzeyinde HIC gecmeyen bir jeton da muaf olur ve kapi sessizce olur.
    ("MUT-EKO-GENIS", "    if not jetonlar:\n        return False\n",
     "    if not jetonlar:\n        return False\n    return True\n", "IDDIA-EKO1"),
    ("MUT-EKO-KOR", "    for jeton in jetonlar:\n", "    return False\n    for jeton in jetonlar:\n",
     "IDDIA-EKO2"),
    # --- MUAFIYET: icerik-hash bagi ---
    ("MUT-MUAF-YOL", "    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi",
     "    return any(d == dosya for d, _h in muafiyet_kumesi)", "IDDIA-MUAF1"),
    ("MUT-MUAF-KOR", "    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi",
     "    return False", "IDDIA-MUAF2"),
    # --- MASKE: teshis ciktisi sizdirmasin ---
    ("MUT-MASKE", '    return "  %s:%d  [EKSEN-%s %s]" % (yol, satir_no, kod, adlar[kod])',
     '    return "  %s:%d  [EKSEN-%s %s] %s" % (yol, satir_no, kod, adlar[kod],\n'
     '                                          _satir_metni)', "IDDIA-MASKE"),
    # --- KOK EKSENI: kapi hangi AGACI olctugunu CWD'den almaz ---
    # MUT-KOK-ARG-KOR: acik --kok yok sayilir -> yalniz IDDIA-KOK1 duser
    # (belirsizlik dali bozulmadigi icin IDDIA-KOK2 AYAKTA kalir).
    ("MUT-KOK-ARG-KOR", "    if arg_kok:\n        k = _git_kok(arg_kok)",
     "    if False:\n        k = _git_kok(arg_kok)", "IDDIA-KOK1"),
    # MUT-KOK-CWD-DUS: belirsizlikte fail-closed yerine SESSIZCE cwd'ye dusulur —
    # olculen kusurun ta kendisi -> yalniz IDDIA-KOK2 duser.
    ("MUT-KOK-CWD-DUS", "    if cwd_kok and os.path.realpath(cwd_kok) != os.path.realpath(betik_kok):",
     "    if False:", "IDDIA-KOK2"),
    # MUT-KOK-ORTAM: 6 Agu 2026 onarimini geri alir — git cagrisi MIRAS ALINAN git
    # baglamiyla kosar. Kancasiz ayak (temiz ortam) etkilenmez; yalniz WORKTREE+KANCA
    # vakasi duser -> TEK KIRMIZI: IDDIA-KOK3.
    ("MUT-KOK-ORTAM", "    return git_kok(dizin, git_ortami())",
     "    return git_kok(dizin, os.environ.copy())", "IDDIA-KOK3"),
)

# KONTROL MUTANTLARI — beyan edilmis bir iddiaya ISARET ETMEZLER: davranisi
# DEGISTIRMEYEN degisikliklerdir ve batarya YESIL kalmalidir. Yoksa batarya "ayirt
# edici" degil sadece HASSAS olur (her dokunusta kirmizi yanan bir olcum, hangi
# eksenin olctugunu SOYLEYEMEZ). Bunlar iddia sayimina GIRMEZ.
KONTROL_MUTANTLARI = (
    ("KONTROL-METIN",
     'print("COZUM: satiri ACIP oku (bu rapor metni BILEREK yazmaz — gunluk PUBLIC\'tir).")',
     'print("COZUM: satiri ACIP oku; bu rapor metni bilerek yazmaz (gunluk PUBLIC).")'),
)


def _sha256_dosya(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kos(kaynak_yolu):
    """Verilen kapi kopyasini --kendini-test ile kostur; (dusen_etiketler, iddia_sayisi,
    cokme_var_mi, ham_cikti) dondurur."""
    r = subprocess.run([sys.executable, kaynak_yolu, "--kendini-test"],
                       capture_output=True, text=True)
    cikti = r.stdout + r.stderr
    dusen = set(re.findall(r"^\s*\[FAIL\]\s+(\S+)", cikti, re.M))
    etiketler = re.findall(r"^\s*\[(?:PASS|FAIL)\]\s+(\S+)", cikti, re.M)
    return dusen, len(etiketler), ("Traceback" in cikti), cikti


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--liste", action="store_true", help="mutant<->iddia eslemesini yaz")
    args = ap.parse_args()

    if args.liste:
        print("MUTANT <-> IDDIA ESLEMESI (%d oldurucu / %d iddia + %d KONTROL)"
              % (len(MUTANTLAR), BEKLENEN_IDDIA_SAYISI, len(KONTROL_MUTANTLARI)))
        for ad, _e, _y, iddia in MUTANTLAR:
            print("  %-18s -> %s" % (ad, iddia))
        for ad, _e, _y in KONTROL_MUTANTLARI:
            print("  %-18s -> (KONTROL: hicbir iddia dusmemeli)" % ad)
        return 0

    # 🔴 OLCULECEK KAPI, SURUCUNUN KENDI AGACINDAN bulunur — CWD'DEN DEGIL.
    # 5 Agu 2026 olcumu: kok CWD'den (`git rev-parse --show-toplevel`, argumansiz)
    # turetiliyordu. Ayni surucu, cwd baska bir agacta iken O AGACIN kapi kopyasini
    # olcuyordu: saglam kapi icin "TABAN: 22 iddia / rc=0", BOZUK bir kopya iceren
    # agactan kosuldugunda "TABAN: 0 iddia / rc=1". Yani bir dalin kapiyi bozdugu
    # kosumda surucu ANA CHECKOUT'un saglam kopyasini olcup YESIL yanabilirdi
    # (bu adim CI'da BLOKLAYICIDIR). `-C` ile surucunun kendi dizini sorulur.
    kok = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(__file__)),
                          "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    if not kok:
        print("OLCULEMEDI: git kok dizini bulunamadi")
        return 2
    canli = os.path.join(kok, KAPI)
    if not os.path.exists(canli):
        print("OLCULEMEDI: %s yok" % KAPI)
        return 2
    canli_modul = os.path.join(kok, MODUL)
    if not os.path.exists(canli_modul):
        print("OLCULEMEDI: %s yok (kapi onu import eder; fallback YOK)" % MODUL)
        return 2

    once = _sha256_dosya(canli)
    modul_once = _sha256_dosya(canli_modul)
    with open(canli, "r", encoding="utf-8") as f:
        govde = f.read()

    # TABAN: mutasyonsuz kosum TEMIZ olmali (0 FAIL, beklenen iddia sayisi).
    dusen, sayi, cokme, cikti = _kos(canli)
    hatalar = []
    if dusen or cokme:
        hatalar.append("TABAN kosumu temiz DEGIL: dusen=%s cokme=%s" % (sorted(dusen), cokme))
    if sayi != BEKLENEN_IDDIA_SAYISI:
        hatalar.append("TABAN iddia sayisi %d, beklenen %d (tablo/govde ayrismis)"
                       % (sayi, BEKLENEN_IDDIA_SAYISI))
    print("TABAN: %d iddia, %d dusen, cokme=%s" % (sayi, len(dusen), cokme))

    beyan = {ad: iddia for ad, _e, _y, iddia in MUTANTLAR}
    if len(set(beyan.values())) != len(MUTANTLAR):
        hatalar.append("MUTANTLAR tablosunda IKI mutant AYNI iddiaya isaret ediyor")
    if len(MUTANTLAR) != BEKLENEN_IDDIA_SAYISI:
        hatalar.append("mutant sayisi (%d) iddia sayisindan (%d) FARKLI — her iddianin "
                       "oldurucu mutanti OLMALI" % (len(MUTANTLAR), BEKLENEN_IDDIA_SAYISI))

    with tempfile.TemporaryDirectory() as d:
        # Mutant kopyasi TEK KAYNAK modulunu import eder -> modul de YANINDA olmali.
        # Mutasyon YALNIZ kapi kopyasina uygulanir; modul kopyasi DEGISTIRILMEZ (capa
        # kapinin KENDI cagri yerindedir), canli modul ise hic acilmaz.
        shutil.copyfile(canli_modul, os.path.join(d, os.path.basename(MODUL)))
        for ad, eski, yeni, iddia in MUTANTLAR:
            if govde.count(eski) != 1:
                hatalar.append("%-18s BAYAT: hedef metin kaynakta %d kez geciyor (1 olmali)"
                               % (ad, govde.count(eski)))
                print("  [KIRMIZI] %-18s hedef metin bulunamadi/tekil degil" % ad)
                continue
            hedef = os.path.join(d, "mutant.py")
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni))
            m_dusen, m_sayi, m_cokme, m_cikti = _kos(hedef)
            iyi = (m_dusen == {iddia}) and (m_sayi == BEKLENEN_IDDIA_SAYISI) and not m_cokme
            print("  [%s] %-18s dusen=%s sayi=%d cokme=%s"
                  % ("OLDU" if iyi else "KIRMIZI", ad, sorted(m_dusen) or "-", m_sayi, m_cokme))
            if not iyi:
                hatalar.append("%-18s beklenen TEK KIRMIZI {%s}, olculen %s "
                               "(iddia sayisi %d, cokme %s)"
                               % (ad, iddia, sorted(m_dusen), m_sayi, m_cokme))
                if m_cokme:
                    hatalar.append("   ilk satirlar: %s" % m_cikti.strip().splitlines()[:3])

        for ad, eski, yeni in KONTROL_MUTANTLARI:
            if govde.count(eski) != 1:
                hatalar.append("%-18s BAYAT: hedef metin kaynakta %d kez geciyor (1 olmali)"
                               % (ad, govde.count(eski)))
                print("  [KIRMIZI] %-18s hedef metin bulunamadi/tekil degil" % ad)
                continue
            hedef = os.path.join(d, "mutant.py")
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni))
            k_dusen, k_sayi, k_cokme, _k_cikti = _kos(hedef)
            iyi = (not k_dusen) and (k_sayi == BEKLENEN_IDDIA_SAYISI) and not k_cokme
            print("  [%s] %-18s dusen=%s sayi=%d cokme=%s (KONTROL: YESIL kalmali)"
                  % ("YESIL" if iyi else "SAPMA", ad, sorted(k_dusen) or "-", k_sayi, k_cokme))
            if not iyi:
                hatalar.append("KONTROL mutanti %-18s KIRMIZI yakti (dusen=%s, iddia "
                               "sayisi %d, cokme %s) — batarya ayirt edici degil, HASSAS"
                               % (ad, sorted(k_dusen), k_sayi, k_cokme))

    sonra = _sha256_dosya(canli)
    modul_sonra = _sha256_dosya(canli_modul)
    if once != sonra:
        hatalar.append("🔴 CANLI DOSYA DEGISTI (sha256 once != sonra) — mutasyon araci "
                       "kaynaga YAZMAMALIYDI")
    if modul_once != modul_sonra:
        hatalar.append("🔴 PAYLASILAN MODUL DEGISTI (sha256 once != sonra) — mutasyon "
                       "yalniz KOPYAYA uygulanmaliydi")
    print("CANLI DOSYA sha256 once==sonra: %s" % (once == sonra))
    print("PAYLASILAN MODUL (%s) sha256 once==sonra: %s"
          % (os.path.basename(MODUL), modul_once == modul_sonra))

    if hatalar:
        print()
        print("MUTASYON BATARYASI KIRMIZI (%d sapma):" % len(hatalar))
        for h in hatalar:
            print("  - %s" % h)
        return 1
    print()
    print("MUTASYON BATARYASI YESIL: %d/%d oldurucu mutant TEK KIRMIZI ve beyana TAM "
          "ESIT, %d KONTROL mutanti YESIL; iddia sayisi %d sabit; Traceback 0."
          % (len(MUTANTLAR), len(MUTANTLAR), len(KONTROL_MUTANTLARI),
             BEKLENEN_IDDIA_SAYISI))
    return 0


if __name__ == "__main__":
    sys.exit(main())
