#!/usr/bin/env python3
"""KIRMIZI-MUTASYON KANIT PROTOKOLU — mimar kapilari.

Ilke (memory/kapi-disiplin-ilkesi.md): hicbir testi KIRMIZI yakmayan kural NOBETSIZDIR;
ya test eklenir ya kural kaldirilir. Bu arac her kural icin o kurali devre disi birakan
bir mutasyon uygular ve kabul testinin GERCEKTEN kirmizi yandigini olcer.

Calisma sekli: kapi dosyalari GECICI bir dizine (tempfile.mkdtemp) KOPYALANIR, kopyada
TEK bir mutasyon uygulanir, sonra "python3 tools/mimar-kilit-test.py <mutasyon-dizini>"
kosturulup KIRMIZI vaka numaralari toplanir. ANA REPOYA ve CANLI KANCALARA DOKUNULMAZ.
Bitiminde gecici dizin silinir.

20 Tem ONARIMI: mutasyon dizini eskiden <repo>/.mutasyon idi ve .gitignore'da DEGILDI —
arac ana repo calisma agacini kirletiyordu. Artik sistem gecici dizinine yazilir.

Cikis kodu 0 = her mutasyon beklenen esigi tutturdu, 1 = en az biri tutturamadi.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
MUTASYON_KOK = None  # main() icinde tempfile.mkdtemp ile doldurulur
TEST = os.path.join(TOOLS, "mimar-kilit-test.py")

KAPI_DOSYALARI = (
    "mimar-kod-kilidi.py",
    "mimar-icra-kapisi.py",
    "mimar-commit-kapisi.py",
    "mimar-kapi-kur.py",
    "mimar-kilit-test.py",
)

KILIT = "mimar-kod-kilidi.py"
ICRA = "mimar-icra-kapisi.py"
CMT = "mimar-commit-kapisi.py"
KUR = "mimar-kapi-kur.py"

CEKIRDEK_NOBETCILERI = (
    '    # NOBETCILER (kapiyi yalanci yapabilen dosyalar)\n'
    '    "/Users/okan/dev/pruvo/tools/mimar-kapi-mutasyon-test.py",\n'
    '    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi-test.py",\n'
    '    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi-mutasyon.py",\n'
    '    "/Users/okan/dev/pruvo/tools/kapi-envanteri.py",\n'
    '    "/Users/okan/dev/pruvo/tools/urunler-guard.py",\n'
    '    # CANLI KABLO\n'
    '    "/Users/okan/dev/pruvo/.git/hooks/pre-commit",\n'
)

KIMLIK_GOVDE = (
    '    aid = girdi.get("agent_id")\n'
    '    if isinstance(aid, str) and aid.strip():\n'
    '        return "ISCI"\n'
    '    return "MIMAR"\n'
)

# M12'de kod-kilidi kancasi silinir → TUM Write/Edit/MultiEdit "allow" vakalari
# KIRMIZI yanmali. Bugunku (eski) test bunlari 34/34 YESIL yakiyordu: stdout bos
# oldugu icin "allow" sayiyordu. Fail-open korlugunun kanit vakalari:
YAZMA_ALLOW_VAKALARI = [7, 8, 9, 10, 26, 28, 60, 62, 64, 65, 72, 73, 74, 75, 82, 83, 97, 98]


def yama(dizin, dosya, eski, yeni, zorunlu=True):
    yol = os.path.join(dizin, dosya)
    with open(yol, encoding="utf-8") as f:
        ham = f.read()
    if eski not in ham:
        if zorunlu:
            raise SystemExit("MUTASYON ANKRAJI BULUNAMADI: " + dosya + " <- " + eski[:60])
        return
    with open(yol, "w", encoding="utf-8") as f:
        f.write(ham.replace(eski, yeni, 1))


def kimligi_sabitle(dizin, deger):
    for dosya in (KILIT, ICRA):
        yama(dizin, dosya, KIMLIK_GOVDE, '    return "' + deger + '"\n')


def cekirdegi_bosalt(dizin):
    yama(dizin, KILIT, "def kimlik(girdi):", "CEKIRDEK = set()\n\n\ndef kimlik(girdi):")


def uzantilari_bosalt(dizin):
    yama(dizin, KILIT, 'REPO_ONEKI = "/Users/okan/dev/pruvo/"',
         'REPO_ONEKI = "/Users/okan/dev/pruvo/"\nICRA_UZANTILARI = ()')


def kayit_bos_kume(dizin):
    for dosya in (KILIT, ICRA):
        yama(dizin, dosya, "    kokler = set()\n    try:",
             "    return set()\n    kokler = set()\n    try:")


# (ad, uygulayici, aciklama, beklenen_kirmizi_kumesi, tam_esitlik_mi, asgari_sayi)
MUTASYONLAR = [
    ("M1", lambda d: kimligi_sabitle(d, "ISCI"),
     "kimlik() daima ISCI (kimlik ekseni komple acilir)",
     {1, 6, 19, 30, 45, 80, 81}, False, 8),
    ("M2", lambda d: kimligi_sabitle(d, "MIMAR"),
     "kimlik() daima MIMAR (isci muafiyeti komple kapanir)",
     {60, 61, 64, 65, 66, 67, 73, 74, 75}, False, 8),
    ("M3", lambda d: yama(d, KILIT, "    if yol.startswith(WT_ONEK):",
                          '    if "/.claude/worktrees/" in yol:'),
     "worktree_ici() ONEK testi ALT-DIZE'ye geri alinir",
     {80, 81}, True, 2),
    ("M4", kayit_bos_kume,
     "kayitli_worktree_kokleri() bos kume dondurur",
     {83, 88}, False, 2),
    ("M5", cekirdegi_bosalt,
     "kod-kilidi CEKIRDEK listesi bosaltilir",
     {68, 69, 70, 71}, False, 4),
    ("M6", lambda d: (cekirdegi_bosalt(d), uzantilari_bosalt(d)),
     "IKILI: CEKIRDEK + ICRA_UZANTILARI birlikte bosaltilir",
     {68, 69, 70, 71, 1, 2, 19}, False, 7),
    ("M7", uzantilari_bosalt,
     "ICRA_UZANTILARI bosaltilir (tek) — basename kalkani sinanir",
     {1, 2, 19}, False, 3),
    ("M8", lambda d: yama(
        d, ICRA,
        "                if hedefler:\n"
        "                    if all(repo_ici(h, cwd) for h in hedefler):\n"
        "                        continue\n"
        "                elif repo_ici(cwd, cwd):\n"
        "                    continue\n",
        "                continue\n"),
     "TEST_MODULLERI repo-ici sarti kaldirilir (ayrik + bitisik yazim birlikte)",
     {87, 92, 94}, True, 3),
    ("M9", lambda d: yama(d, CMT,
                          "    basename = _basename(yol)\n"
                          "    if not basename or basename in VERI_BASENAME:\n"
                          "        return False\n",
                          "    return False\n"
                          "    basename = _basename(yol)\n"
                          "    if not basename or basename in VERI_BASENAME:\n"
                          "        return False\n"),
     "commit kapisi kaynak_mi() daima False (daraltma da coker)",
     {102, 107, 108}, False, 3),
    ("M10", lambda d: yama(d, CMT, "    try:\n        for ad in SEQUENCER_DOSYA:",
                           "    return True\n    try:\n        for ad in SEQUENCER_DOSYA:"),
     "commit kapisi sequencer kontrolu daima True",
     {100, 102}, False, 2),
    ("M11", lambda d: yama(d, CMT, "return uzanti.lower() in KAYNAK_UZANTI",
                           "return uzanti in KAYNAK_UZANTI"),
     "commit kapisi uzanti karsilastirmasindan lower() kaldirilir",
     {102}, True, 1),
    ("M12", lambda d: os.remove(os.path.join(d, KILIT)),
     "kod-kilidi kancasi SILINIR (fail-open korlugu sinavi)",
     set(YAZMA_ALLOW_VAKALARI), False, len(YAZMA_ALLOW_VAKALARI)),
    ("M13", lambda d: yama(
        d, ICRA,
        "                hedefler = test_hedefleri(argumanlar[i + 2:])",
        '                hedefler = [t for t in argumanlar[i + 2:] if not t.startswith("-")]'),
     "BITISIK-degerli bayrak ayristirmasi geri alinir ('-' ile baslayan token elenir)",
     {92, 95}, True, 2),
    ("M14", lambda d: yama(
        d, KUR,
        '    print("BASH_ZINCIRI_ICRA=" + ("var" if bash_var else "yok"))',
        '    bash_var = yazma_var = precommit_var = True\n'
        '    print("BASH_ZINCIRI_ICRA=" + ("var" if bash_var else "yok"))'),
     "kablo raporcusu (kur.py durum()) daima 'var' der — YALANCI RAPORCU",
     {111}, True, 1),
    ("M15", lambda d: yama(d, KILIT, CEKIRDEK_NOBETCILERI, ""),
     "CEKIRDEK genisletmesi geri alinir (nobetciler korumasiz kalir)",
     {76, 77, 78, 79, 96}, True, 5),
]

# M7'de basename kalkani (blocked listesindeki mimar-*.py kayitlari) vakalari 4 ve 5'i
# hala korumali — yani bu iki vaka YESIL kalmali. Tekli mutasyonda maskelenen kalkanin
# gercekten test edildiginin kaniti M6'dir.
M7_YESIL_KALMALI = {4, 5}


def mutasyonu_kostur(ad, uygulayici):
    dizin = os.path.join(MUTASYON_KOK, ad)
    if os.path.exists(dizin):
        shutil.rmtree(dizin)
    os.makedirs(dizin)
    for dosya in KAPI_DOSYALARI:
        shutil.copyfile(os.path.join(TOOLS, dosya), os.path.join(dizin, dosya))
    uygulayici(dizin)

    sonuc = subprocess.run(
        [sys.executable, TEST, dizin], capture_output=True, text=True,
    )
    kirmizi = set()
    for satir in (sonuc.stdout or "").splitlines():
        m = re.match(r"\s*vaka (\d+):", satir)
        if m:
            kirmizi.add(int(m.group(1)))
    return kirmizi


def main():
    global MUTASYON_KOK
    MUTASYON_KOK = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-kapi-mutasyon-"))
    print("MUTASYON DIZINI (gecici): " + MUTASYON_KOK)

    basarisiz = []
    try:
        for ad, uygulayici, aciklama, beklenen, tam, asgari in MUTASYONLAR:
            kirmizi = mutasyonu_kostur(ad, uygulayici)
            eksik = beklenen - kirmizi
            tamam = (not eksik) and len(kirmizi) >= asgari
            if tam and kirmizi != beklenen:
                tamam = False
            if ad == "M7" and (M7_YESIL_KALMALI & kirmizi):
                tamam = False
                aciklama += " [basename kalkani DELINDI: " + str(sorted(M7_YESIL_KALMALI & kirmizi)) + "]"
            if not kirmizi:
                tamam = False
                aciklama += " [NOBETSIZ BOLGE: sifir kirmizi]"
            print("MUTASYON {:<4} | kirmizi={:<3} | vakalar={} | BEKLENEN>={} {} | {}".format(
                ad, len(kirmizi), sorted(kirmizi), asgari,
                ("== " + str(sorted(beklenen))) if tam else ("uzerinde " + str(sorted(beklenen))),
                "GECTI" if tamam else "KALDI"))
            print("          {} | {}".format(aciklama, "eksik=" + str(sorted(eksik)) if eksik else "eksik=yok"))
            if not tamam:
                basarisiz.append(ad)
    finally:
        shutil.rmtree(MUTASYON_KOK, ignore_errors=True)

    print("")
    if basarisiz:
        print("SONUC: KIRMIZI — esigi tutturamayan mutasyonlar: " + ", ".join(basarisiz))
        sys.exit(1)
    print("SONUC: {}/{} mutasyonun HEPSI kabul testini kirmizi yakti.".format(
        len(MUTASYONLAR), len(MUTASYONLAR)))
    sys.exit(0)


main()
