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
TESTDOSYA = "mimar-kilit-test.py"

# B8 (20 Tem): CEKIRDEK'e eklenen CANLI PreToolUse/Bash zinciri nobetcileri.
CEKIRDEK_CANLI_ZINCIR = (
    '    "/Users/okan/dev/pruvo/tools/urunler-guard-hook.py",\n'
    '    "/Users/okan/dev/pruvo/tools/komut-stili-kapisi.py",\n'
)

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
    # M8 KALDIRILDI (22 Tem): betik_siniri/modul_suphesi python '-m' makinesi PY_NODE
    # ALLOWLIST'e devroldu ve gate'ten SILINDI (python mimar tarafinda tek noktada:
    # _py_izinli). O yuzden "betik siniri" mutasyonunun ANKRAJI yok. -m formlari artik
    # allowlist tarafindan reddedilir; sentinel'i ME4/ME5'tir (asagida).
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
    # M10 (20 Tem, R1 nobetcisi) — ESKI HALI "sequencer daima True" idi ve yeni sirada
    # NOBETSIZ kalirdi (istisna zaten korunan dosyayi acmadigi icin hicbir vaka
    # kizarmaz). Yerine REGRESYONUN KENDISI mutasyon olarak uygulanir: sequencer
    # kontrolu main()'in basina, korunan-dosya kontrolunun ONUNE geri tasinir.
    ("M10", lambda d: yama(
        d, CMT,
        '    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":',
        "    if sequencer_suruyor(gitdir):\n"
        "        return 0\n"
        '    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":'),
     "R1 REGRESYONU: sequencer istisnasi main() basina (korunan kontrolun ONUNE) geri alinir",
     {103, 109, 112, 113}, True, 4),
    ("M16", lambda d: yama(d, CMT, "    try:\n        for ad in SEQUENCER_DOSYA:",
                           "    return False\n    try:\n        for ad in SEQUENCER_DOSYA:"),
     "sequencer kontrolu daima False (gurultulu+loglu allow yolu olur)",
     {103}, True, 1),
    ("M11", lambda d: yama(d, CMT, "return uzanti.lower() in KAYNAK_UZANTI",
                           "return uzanti in KAYNAK_UZANTI"),
     "commit kapisi uzanti karsilastirmasindan lower() kaldirilir",
     {102}, True, 1),
    ("M12", lambda d: os.remove(os.path.join(d, KILIT)),
     "kod-kilidi kancasi SILINIR (fail-open korlugu sinavi)",
     set(YAZMA_ALLOW_VAKALARI), False, len(YAZMA_ALLOW_VAKALARI)),
    # M13 (4. tur): R2'de bayrak oneki SOYULMAZ — yalniz HAM okuma kalir. Ham okuma
    # '-s/private/tmp/disari'yi goreli sayip cwd'ye ekler ve repo-ici gorur.
    ("M13", lambda d: yama(
        d, ICRA,
        '            if "/" in t:\n'
        "                adaylar.append(t)\n"
        '                adaylar.append(t[t.index("/"):])\n'
        '            if "=" in t:\n'
        '                adaylar.append(t.split("=", 1)[1])\n',
        '            if "/" in t:\n'
        "                adaylar.append(t)\n"),
     "R2: bayrak oneki soyulmaz (yalniz ham okuma) — bitisik/=li dis yol acilir "
     "(22Tem: dis_yol artik YALNIZ sh/bash icin canli, sentinel sh vakasi 251)",
     {251}, True, 1),
    ("M14", lambda d: yama(
        d, KUR,
        '    print("BASH_ZINCIRI_ICRA=" + ("var" if bash_var else "yok"))',
        '    bash_var = yazma_var = precommit_var = True\n'
        '    print("BASH_ZINCIRI_ICRA=" + ("var" if bash_var else "yok"))'),
     "kablo raporcusu (kur.py durum()) daima 'var' der — YALANCI RAPORCU",
     {111, 114}, True, 2),
    ("M15", lambda d: yama(d, KILIT, CEKIRDEK_NOBETCILERI, ""),
     "CEKIRDEK genisletmesi geri alinir (nobetciler korumasiz kalir)",
     {76, 77, 78, 79, 96}, True, 5),
    # --- 20 Tem SON ONARIM TURU NOBETCILERI ---
    # M17 KALDIRILDI (22 Tem): modul_suphesi ('-m' token taramasi) gate'ten silindi
    # (PY_NODE allowlist devraldi) -> ankraj yok. '-mpip'/'-mtimeit' artik allowlist'ten
    # RED (sentinel ME4).
    # M18 (22 Tem REPOINT): F (betik repo_ici) ARTIK YALNIZ sh/bash icin canli (python
    # short-circuit ile allowlist'e gider). Sentinel: sh vakasi 250 (bash x.sh, cwd repo DISI).
    ("M18", lambda d: yama(d, ICRA,
                           "        if not repo_ici(betik, cwd):",
                           "        if False:"),
     "F: betik repo_ici kontrolu silinir (sh betigi cwd repo DISI acilir)",
     {250}, True, 1),
    # M20 (4. tur): R2 tiresiz token yol kontrolu silinir — bayrak degerleri denetlenir
    # ama duz arguman olarak verilen repo-disi yol acilir.
    ("M20", lambda d: yama(
        d, ICRA,
        '        elif "/" in t or t.startswith("."):\n'
        "            adaylar.append(t)\n",
        "        elif False:\n"
        "            adaylar.append(t)\n"),
     "R2: tiresiz ARGUMAN yol kontrolu silinir (duz repo-disi yol argumani acilir) "
     "(22Tem: sentinel sh vakasi 253)",
     {253}, True, 1),
    ("N1", lambda d: yama(d, KUR,
                          '        matcher = blok.get("matcher") or ""\n'
                          "        if matcher_parcasi not in matcher:\n"
                          "            continue\n",
                          '        matcher = blok.get("matcher") or ""\n'),
     "B5: _zincirde_var() MATCHER kontrolu silinir (dogru kanca, YANLIS matcher)",
     {114}, True, 1),
    ("M19", lambda d: yama(d, KILIT, CEKIRDEK_CANLI_ZINCIR, ""),
     "B8: canli Bash zinciri nobetcileri CEKIRDEK'ten cikarilir",
     {140, 141}, True, 2),
    # --- 22 TEM SERTLESTIRME NOBETCILERI (her yeni rule = bir kirmizi-mutasyon) ---
    ("ME1", lambda d: yama(d, ICRA,
                           "        if ad in OLCUM_KOMUTLARI:\n",
                           "        if False and ad in OLCUM_KOMUTLARI:\n"),
     "22Tem: OLCUM/dosya-tarama denetimi kapatilir (du/ps/find/wc/head/... acilir)",
     {200, 201, 202, 203, 216}, False, 5),
    # ME2 (26 Tem REPOINT): kural artik "codex = RED" degil, "codex ciktisiz = RED".
    # Mutasyon kurali komple kapatir -> bayraksiz cagrilar (25/230/231/235) acilir.
    ("ME2", lambda d: yama(
        d, ICRA,
        '        if codex_karari is not None and codex_karari != "gecer":\n',
        '        if False and codex_karari is not None and codex_karari != "gecer":\n'),
     "26Tem: codex KALITE KAPISI komple kapatilir (bayraksiz codex exec acilir)",
     {25, 230, 231, 235, 264, 265, 266, 267, 268, 269, 270, 275, 277, 278}, False, 14),
    # ME6 (26 Tem, 27 Tem REPOINT): POZITIF yonun nobetcisi — cikti-bayragi muafiyeti
    # silinirse delege KOMPLE kapanir (22 Tem'e geri donus) ve mesru cagrilar kizarir.
    ("ME6", lambda d: yama(
        d, ICRA,
        "    if not _codex_cikti_degerli(kalan[1:]):\n",
        "    if True:\n"),
     "26/27Tem: cikti-bayragi muafiyeti silinir (codex yeniden KOSULSUZ RED)",
     {232, 233, 273, 274}, True, 4),
    ("ME7", lambda d: yama(
        d, ICRA,
        "    if all(t in CODEX_GOZLEM_BAYRAKLARI for t in kalan):\n"
        '        return "gecer"\n',
        "    if False:\n"
        '        return "gecer"\n'),
     "26/27Tem: zararsiz gozlem muafiyeti silinir ('codex --version/-v/-V/-h' reddedilir)",
     {234, 271, 272, 276}, True, 4),
    # ME8 KALDIRILDI (27 Tem): "codex ALLOW yolunda 'continue' YOK" kararinin nobetcisiydi
    # (mutasyon continue ekler -> segmentin kalan denetimleri kapanir). 27 Tem DARALTMASI
    # bu kararin ANLAMINI da ortadan kaldirdi: kural artik yalnizca argv0 basename'i
    # 'codex' olan segmentte calisir; boyle bir segmentte kalan denetimlerin HICBIRI
    # (olcum/curl/A-blogu/YORUMLAYICI) zaten atesleyemez, cunku 'codex' ne olcum komutu,
    # ne ICRA_UZANTILI bir betik, ne de yorumlayicidir. Mutasyon SIFIR kirmizi uretiyordu
    # (NOBETSIZ BOLGE). Yerine gecen nobetci ME9'dur: 'codex + -o serpistirme' saldirisini
    # artik 'continue yok' degil, DARALTMANIN KENDISI imkansiz kiliyor — ve daraltmanin
    # geri alinmasi ME9'da kirmizi yaniyor. (Ayni gerekce: M8/M17 kaldirmalari.)
    # --- 27 TEM SIKILASTIRMA NOBETCILERI ---
    # ME9: DARALTMANIN nobetcisi (TERS yonlu mutasyon — kural GENISLETILIR, ALLOW
    # vakalari kizarir). Genis token taramasi geri gelirse 4 on-var yanlis-pozitif doner.
    ("ME9", lambda d: yama(
        d, ICRA,
        "    if not tokenlar or not _codex_programi(tokenlar[0]):\n"
        "        return None\n",
        '    if not any(os.path.basename(t) == "codex" or "ChatGPT.app" in t\n'
        "               for t in tokenlar):\n"
        "        return None\n"),
     "27Tem: DARALTMA geri alinir (argv0 yerine TUM token taramasi) -> 4 yanlis-pozitif doner",
     {260, 261, 262, 263}, True, 4),
    ("ME10", lambda d: yama(
        d, ICRA,
        "    if kalan[0] != CODEX_IZINLI_ALTKOMUT:\n",
        "    if False and kalan[0] != CODEX_IZINLI_ALTKOMUT:\n"),
     "27Tem: ALT-KOMUT kapisi kapatilir (resume/mcp/login/apply acilir)",
     {264, 265, 266, 275}, True, 4),
    ("ME11", lambda d: yama(
        d, ICRA,
        "            if i + 1 >= len(tokenlar):\n"
        "                return False\n"
        "            deger = tokenlar[i + 1]\n"
        '            if not deger or deger.startswith("-"):\n'
        "                return False\n"
        "            return True\n",
        "            return True\n"),
     "27Tem: AYRIK bayragin DEGER sarti silinir ('codex exec -o' bos bayrakla gecer)",
     {267, 268, 269, 277}, True, 4),
    ("ME12", lambda d: yama(
        d, ICRA,
        "CODEX_GOZLEM_BAYRAKLARI = SURUM_BAYRAKLARI\n",
        'CODEX_GOZLEM_BAYRAKLARI = {"--version", "-V", "--help", "-h"}\n'),
     "27Tem: gozlem SIMETRISI bozulur (eski 4'lu liste; '-v' yeniden reddedilir)",
     {271}, True, 1),
    ("ME13", lambda d: yama(
        d, ICRA,
        "        if t.startswith(CODEX_CIKTI_ONEKI):\n"
        "            return bool(t[len(CODEX_CIKTI_ONEKI):])\n",
        "        if t.startswith(CODEX_CIKTI_ONEKI):\n"
        "            return True\n"),
     "27Tem: ESITLIKLI bicimde BOS deger toleransi ('--output-last-message=' gecer)",
     {270}, True, 1),
    ("ME3", lambda d: yama(d, ICRA,
                           '        if ad in ("curl", "wget"):\n',
                           '        if False and ad in ("curl", "wget"):\n'),
     "22Tem: curl/wget denetimi kapatilir (canli dogrulama acilir)",
     {220, 221}, False, 2),
    ("ME4", lambda d: yama(
        d, ICRA,
        '    if not re.match(r"^python3(\\.\\d+)?$", ad):\n'
        "        return False\n",
        "    return True\n"
        '    if not re.match(r"^python3(\\.\\d+)?$", ad):\n'
        "        return False\n"),
     "22Tem: _py_izinli daima True (tum python/node araclari acilir)",
     {240, 241, 244}, False, 3),
    ("ME5", lambda d: yama(
        d, ICRA,
        "    if ilk == DURUM_YOL:\n"
        "        return len(argumanlar) == 1\n",
        "    if ilk == DURUM_YOL:\n"
        "        return True\n"),
     "22Tem: durum.py EKSTRA argüman toleransi (allowlist tam-esitlik gevser)",
     {129, 241}, False, 2),
]

# CEVRE-ARIZA ENJEKSIYONU (B6-yan): bu iki vaka mutasyonu KOPYALANMIS kabul testine
# uygular ve KOPYAYI kosturur; olculen sey KIRMIZI VAKA degil, takimin CIKIS KODUDUR.
# Sinanan kural: "cevre bozuldu, vaka kosmadi" durumu YESIL YANMAMALI (takim bir merge
# kapisi olarak kullaniliyor).
KENDI_TESTINI_KOSAN = {
    ("C1", lambda d: yama(
        d, TESTDOSYA,
        '    yol = os.path.join(temel, "kayitli-wt")\n',
        '    return None\n    yol = os.path.join(temel, "kayitli-wt")\n'),
     "CEVRE: gecici worktree KURULAMAZ -> CEVRE-ATLANAN>0 iken exit 0 OLMAMALI"),
    ("C2", lambda d: yama(
        d, TESTDOSYA,
        '    if os.path.exists(yol):\n        return ["dizin hala diskte: " + yol]\n'
        "    return None\n",
        '    if os.path.exists(yol):\n        return ["dizin hala diskte: " + yol]\n'
        '    return ["ENJEKTE EDILMIS CEVRE ARIZASI"]\n'),
     "CEVRE: gecici worktree KALDIRILAMADI raporu -> exit 0 OLMAMALI"),
}

# M7'de basename kalkani (blocked listesindeki mimar-*.py kayitlari) vakalari 4 ve 5'i
# hala korumali — yani bu iki vaka YESIL kalmali. Tekli mutasyonda maskelenen kalkanin
# gercekten test edildiginin kaniti M6'dir.
M7_YESIL_KALMALI = {4, 5}


def mutasyonu_kostur(ad, uygulayici, kendi_testi=False):
    """Mutasyonu gecici kopyaya uygular ve kabul testini kosturur.

    kendi_testi=False → ORIJINAL tools/mimar-kilit-test.py kosar (kapi dosyalari
    mutasyonlu): olculen sey KIRMIZI VAKA numaralaridir.
    kendi_testi=True  → KOPYALANMIS (mutasyonlu) kabul testi kosar: olculen sey
    takimin CIKIS KODUDUR (cevre-ariza enjeksiyonu, B6-yan)."""
    dizin = os.path.join(MUTASYON_KOK, ad)
    if os.path.exists(dizin):
        shutil.rmtree(dizin)
    os.makedirs(dizin)
    for dosya in KAPI_DOSYALARI:
        shutil.copyfile(os.path.join(TOOLS, dosya), os.path.join(dizin, dosya))
    uygulayici(dizin)

    kosulacak = os.path.join(dizin, TESTDOSYA) if kendi_testi else TEST
    sonuc = subprocess.run(
        [sys.executable, kosulacak, dizin], capture_output=True, text=True,
    )
    kirmizi = set()
    for satir in (sonuc.stdout or "").splitlines():
        m = re.match(r"\s*vaka (\d+):", satir)
        if m:
            kirmizi.add(int(m.group(1)))
    return kirmizi, sonuc.returncode


def main():
    global MUTASYON_KOK
    MUTASYON_KOK = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-kapi-mutasyon-"))
    print("MUTASYON DIZINI (gecici): " + MUTASYON_KOK)

    basarisiz = []
    try:
        for ad, uygulayici, aciklama, beklenen, tam, asgari in MUTASYONLAR:
            kirmizi, _ = mutasyonu_kostur(ad, uygulayici)
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

        # CEVRE-ARIZA ENJEKSIYONU (B6-yan): kriter cikis kodudur, kirmizi vaka degil.
        for ad, uygulayici, aciklama in sorted(KENDI_TESTINI_KOSAN):
            _, cikis = mutasyonu_kostur(ad, uygulayici, kendi_testi=True)
            tamam = (cikis != 0)
            print("CEVRE-ARIZA {:<3} | exit={} (0 OLMAMALI) | {}".format(
                ad, cikis, "GECTI" if tamam else "KALDI"))
            print("          {}".format(aciklama))
            if not tamam:
                basarisiz.append(ad)
    finally:
        shutil.rmtree(MUTASYON_KOK, ignore_errors=True)
        # C1/C2 enjeksiyonlari gecici worktree kaydi birakmis olabilir — temizle.
        subprocess.run(["git", "-C", KOK, "worktree", "prune"],
                       capture_output=True, text=True)

    toplam = len(MUTASYONLAR) + len(KENDI_TESTINI_KOSAN)
    print("")
    if basarisiz:
        print("SONUC: KIRMIZI — esigi tutturamayan mutasyonlar: " + ", ".join(basarisiz))
        sys.exit(1)
    print("SONUC: {}/{} mutasyonun HEPSI kabul testini kirmizi yakti "
          "({} kural mutasyonu + {} cevre-ariza enjeksiyonu).".format(
              toplam, toplam, len(MUTASYONLAR), len(KENDI_TESTINI_KOSAN)))
    sys.exit(0)


main()
