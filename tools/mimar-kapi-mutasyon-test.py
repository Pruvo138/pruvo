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
import ast
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
    "mimar_kimlik.py",
    "mimar-kod-kilidi.py",
    "mimar-icra-kapisi.py",
    "mimar-commit-kapisi.py",
    "mimar-kapi-kur.py",
    "mimar-kilit-test.py",
)

KILIT = "mimar-kod-kilidi.py"
KIMLIKORTAK = "mimar_kimlik.py"
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

KIMLIK_GOVDE_KILIT = (
    'def kimlik(girdi):\n'
    '    return "ISCI" if kimlik_ekseni(girdi) is not None else "MIMAR"\n'
)
KIMLIK_GOVDE_ICRA = (
    'def kimlik(girdi):\n'
    '    return "ISCI" if kimlik_ekseni(girdi) is not None else "MIMAR"\n'
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


def isci_motorlarini_yeniden_sirala(dizin):
    """ISCI_MOTORLARI atamasini kaynaktan bulup davranis-koruyarak dondurur."""
    yol = os.path.join(dizin, KIMLIKORTAK)
    with open(yol, encoding="utf-8") as f:
        ham = f.read()
    try:
        agac = ast.parse(ham, filename=yol)
    except SyntaxError as exc:
        raise SystemExit("ISCI_MOTORLARI KAYNAGI AYRISTIRILAMADI: " + str(exc))
    atamalar = [
        dugum for dugum in ast.walk(agac)
        if isinstance(dugum, ast.Assign)
        and any(isinstance(hedef, ast.Name) and hedef.id == "ISCI_MOTORLARI"
                for hedef in dugum.targets)
    ]
    if len(atamalar) != 1:
        raise SystemExit("ISCI_MOTORLARI ATAMASI TEKIL DEGIL: " + str(len(atamalar)))
    atama = atamalar[0]
    try:
        motorlar = ast.literal_eval(atama.value)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise SystemExit("ISCI_MOTORLARI SABIT BIR DEGER DEGIL: " + str(exc))
    if not isinstance(motorlar, tuple) or len(motorlar) < 2:
        raise SystemExit("ISCI_MOTORLARI EN AZ IKI ELEMANLI TUPLE DEGIL")
    yeni_motorlar = motorlar[1:] + motorlar[:1]
    eski = ast.get_source_segment(ham, atama.value)
    if not eski or yeni_motorlar == motorlar:
        raise SystemExit("ISCI_MOTORLARI DAVRANIS-KORUYAN MUTASYONU URETILEMEDI")
    yama(dizin, KIMLIKORTAK, eski, repr(yeni_motorlar))


def kimligi_sabitle(dizin, deger):
    yama(dizin, KILIT, KIMLIK_GOVDE_KILIT,
         'def kimlik(girdi):\n    return "' + deger + '"\n')
    yama(dizin, ICRA, KIMLIK_GOVDE_ICRA,
         'def kimlik(girdi):\n    return "' + deger + '"\n')


def cekirdegi_bosalt(dizin):
    yama(dizin, KILIT, "def kimlik(girdi):", "CEKIRDEK = set()\n\n\ndef kimlik(girdi):")


def uzantilari_bosalt(dizin):
    yama(dizin, KILIT, 'REPO_ONEKI = "/Users/okan/dev/pruvo/"',
         'REPO_ONEKI = "/Users/okan/dev/pruvo/"\nICRA_UZANTILARI = ()')


def kayit_bos_kume(dizin):
    for dosya in (KILIT, ICRA):
        yama(dizin, dosya, "    kokler = set()\n    try:",
             "    return set()\n    kokler = set()\n    try:")


# ===================== 20 AGU: TARAYICI EKSENI — KAPALI KOL NEREDE OLCULUR ============
# 🔴 OLCULEN TUZAK (bu turda CANLI yakalandi): 20 Agu'da tarayici ekseni EV BAZLI acildi
# ve bu takim KraL evinde, yani tarayiciya ACIK bir evde kosuyor. Acik evde MCP onek
# kumesi HICBIR karari degistirmez — MC1 (kapsam daraltma), MC3 (kapsam tasma) ve MC4
# (kimlik ekseni) 500-504 uzerinden DAVRANISSAL IZ BIRAKMAZ.
#
# 🔴 ILK COZUM DENENDI VE OLCULEREK CURUTULDU: "kopyada hem kapiyi hem kilit testinin
# 500-504 beklentisini cevir" tabani KURMADI. SEBEP: bu arac mutasyon dizinindeki test
# KOPYASINI kosturmaz — ORIJINAL tools/mimar-kilit-test.py'yi kosturup mutasyon dizinini
# ARGUMAN olarak verir (bkz. modul docstring). Yani TESTDOSYA'ya atilan yama HICBIR ZAMAN
# okunmaz; taban 5 sahte kirmizi uretti. Ders: "kopyaya yama attim" != "kosan kod degisti".
#
# 🔴 GECERLI COZUM: kapali kol, kilit testinin KENDI icinde ayri bir blokta yasiyor —
# `tarayici_ev_ekseni_denetim()` (vaka 528-544). O blok kapi dosyasini gecici bir kopyaya
# alir ve `TARAYICI_ACIK_EVLER` satirini IKI YONDE de ZORLAR (acik / kapali), yani kapali
# kolu MUTANTLI kaynak uzerinde olcer. MC1-MC4 bu yuzden ARTIK SADE mutantlardir (taban
# YOK) ve beklenen kirmizi kumeleri 5xx yerine 53x/54x'e tasindi.
TARAYICI_ACIK_KAYNAK = 'TARAYICI_ACIK_EVLER = ("pruvo", "pruvo-hasat")\n'

# 🔴 YAN EKSEN NOBETI (20 Agu): "hedef kol KIRMIZI" tek basina kanit degildir — YAN
# eksenin YESIL kaldigini da olcmek zorundayiz. Aksi halde iki ekseni birden bozan kaba
# bir mutant "ayrim kanitlandi" diye okunur. Kesisim BOS olmalidir; mutant kendi
# ekseninin DISINA tasarsa GECTI YAZILMAZ.
#   MT1 = Claude yasagini acar  -> TARAYICI vakalari YESIL kalmali
#   MT2 = tarayiciyi kapatir    -> CLAUDE-ISCI vakalari YESIL kalmali
YAN_EKSEN_YESIL = {
    "MT1": {500, 501, 502, 503, 504, 528, 530, 531, 532, 533, 534, 535, 536, 537},
    "MT2": {401, 403, 614},
    # 🔴 28 AGU (K340): iki eksen AYRI olmali. ① (env -C / cd normalizasyonu) mutantı
    # ②'yi (betik-ici cagri) KIRLETMEMELI ve tersi; ayrica IKI EKSENIN de KONTROL
    # vakalari (846/847/852) yesil kalmali — kapi "her cagriya yanan alarm" degildir.
    "M_K340_1": {846, 847, 850, 851, 852, 853},
    "M_K340_2": {840, 841, 842, 843, 844, 845, 846, 847, 852},
    "M_K340_3": {840, 846, 847, 850, 851, 852, 853},
    "M_K340_4": {840, 846, 847, 850, 851, 852, 853},
}


# (ad, uygulayici, aciklama, beklenen_kirmizi_kumesi, tam_esitlik_mi, asgari_sayi)
MUTASYONLAR = [
    # === 28 AGU 2026 (K340) — HEDEF-KOL ATIFLI MUTANTLAR (K182) ====================
    # Her mutant TEK BIR KOLU oldurur ve o kolun KENDI vakalarini kirmizi yakar; yan
    # eksen YAN_EKSEN_YESIL ile AYRICA olculur. `tam=True` secildi: kirmizi kume
    # BEKLENENE ESIT olmali — "fazladan kirmizi" da bir ariza sayilir, cunku mutant
    # komsu kolu bozuyorsa eksen ayrimi KANITLANMAMIS demektir.
    ("M_K340_1", lambda d: yama(
        d, ICRA,
        "        if ikinci and ikinci != tokenlar:\n",
        "        if False and ikinci != tokenlar:\n"),
     "K340 ①a: SARMALAYICI IKINCI OKUMASI oldurulur -> 'env -C <dizin> ...' ve "
     "'nice -n 10 ...' segmentleri yeniden TUMDEN atlanir (bayrak degeri argv0 sanilir). "
     "843 BILEREK DISARIDA: '--chdir=<dizin>' esitlikli formunda argv0 zaten 'python3' "
     "okunuyor, onu tutan kol IKINCI OKUMA degil ETKIN CWD kolu (M_K340_3 oldurur)",
     {841, 842, 844}, True, 3),
    ("M_K340_2", lambda d: yama(
        d, ICRA,
        "    for m in BETIK_ICI_EXEC_RE.finditer(kaynak):\n",
        "    for m in []:\n"),
     "K340 ②: BETIK-ICI CAGRI kolu oldurulur -> .py govdesindeki repo-disi cagri "
     "yeniden gorunmez olur (canli vaka: 16 gorsel R2'ye boyle yuklendi). 853 de HEDEF "
     "koldur: kol olunce sinirin `BETIK-ICI-OLCULEMEDI=` izi de kaybolur — yani 'sinir "
     "ADIYLA basilir' iddiasi SUS PAYI DEGIL, yuk tasiyor",
     {850, 851, 853}, True, 3),
    ("M_K340_3", lambda d: yama(
        d, ICRA,
        "    adaylar = []\n\n    def ekle(deger):\n",
        "    adaylar = []\n    return adaylar\n\n    def ekle(deger):\n"),
     "K340 ①b: ETKIN CWD kolu oldurulur (_sarmalayici_cwd_adaylari bos doner) -> "
     "'env -C /private/tmp ...' ve '--chdir=/private/tmp ...' goreceli yolu yine "
     "ORIJINAL cwd'ye cozer ve allowlist'i YANLIS agactan saglar",
     {842, 843}, True, 2),
    ("M_K340_4", lambda d: yama(
        d, ICRA,
        '    if not tokenlar or os.path.basename(tokenlar[0]) != "cd":\n',
        "    if True:\n"),
     "K340 ①c: 'cd <dizin>' okumasi oldurulur -> 'cd /private/tmp && python3 tools/...' "
     "yeniden ORIJINAL cwd'ye cozulur",
     {845}, True, 1),
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
    # 28 AGU (K340) ANKRAJ TAZELEMESI: F kolunun cagrisi artik TEK cwd yerine CWD OKUMA
    # LISTESI aliyor ('cwd' -> 'cwdler'). Ankraj metni tazelendi; mutantin OLDURDUGU KOL
    # ve sentinel vakasi (250) DEGISMEDI.
    ("M18", lambda d: yama(d, ICRA,
                           "        if not repo_ici(betik, cwdler):",
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
                           "        if ad in OLCUM_KOMUTLARI and not cip:\n",
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
     {25, 230, 231, 235, 264, 265, 266, 267, 268, 269, 270, 275, 277, 278,
      279, 280, 283, 285}, False, 18),
    # ME6 (26 Tem, 27 Tem REPOINT): POZITIF yonun nobetcisi — cikti-bayragi muafiyeti
    # silinirse delege KOMPLE kapanir (22 Tem'e geri donus) ve mesru cagrilar kizarir.
    # 17 Agu K159: V3 (902) eklenir — cikti-bayragi muafiyeti silindiginde artik
    # izinli model + pencere ici olan V3 de KOSULSUZ RED'a dusuyor (legitimate capa).
    ("ME6", lambda d: yama(
        d, ICRA,
        "    if not _codex_cikti_degerli(kalan[1:]):\n",
        "    if True:\n"),
     "26/27Tem: cikti-bayragi muafiyeti silinir (codex yeniden KOSULSUZ RED); K159 son kol: "
     "910 yasak model cagrisinin yapisal izin yolunu da eklenen RED'a kat",
     {232, 233, 273, 274, 281, 902, 910}, True, 7),
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
     "27Tem: DARALTMA geri alinir (argv0 yerine TUM token taramasi) -> 6 yanlis-pozitif "
     "doner (27Tem-2 OLCUMU: 282 sarmalayici+kelime, 281 MESRU sarmalanmis '-o' cagrisi "
     "— genis tarama tokenlar[0]='10' oldugu icin alt-komutu 'codex' sanip reddediyor)",
     {260, 261, 262, 263, 281, 282}, True, 6),
    ("ME10", lambda d: yama(
        d, ICRA,
        "    if kalan[0] != CODEX_IZINLI_ALTKOMUT:\n",
        "    if False and kalan[0] != CODEX_IZINLI_ALTKOMUT:\n"),
     "27Tem: ALT-KOMUT kapisi kapatilir (resume/mcp/login/apply acilir)",
     {264, 265, 266, 275}, True, 4),
    ("ME11", lambda d: yama(
        d, ICRA,
        "        if t in CODEX_CIKTI_BAYRAKLARI:\n"
        "            if i + 1 >= len(tokenlar):\n"
        "                return False\n"
        "            return _codex_deger_gecerli(tokenlar[i + 1])\n",
        "        if t in CODEX_CIKTI_BAYRAKLARI:\n"
        "            return True\n"),
     "27Tem: AYRIK bayragin DEGER sarti silinir ('codex exec -o' bos bayrakla gecer)",
     {267, 268, 269, 277, 285}, True, 5),
    ("ME12", lambda d: yama(
        d, ICRA,
        "CODEX_GOZLEM_BAYRAKLARI = SURUM_BAYRAKLARI\n",
        'CODEX_GOZLEM_BAYRAKLARI = {"--version", "-V", "--help", "-h"}\n'),
     "27Tem: gozlem SIMETRISI bozulur (eski 4'lu liste; '-v' yeniden reddedilir)",
     {271}, True, 1),
    ("ME13", lambda d: yama(
        d, ICRA,
        "        if t.startswith(CODEX_CIKTI_ONEKI):\n"
        "            return _codex_deger_gecerli(t[len(CODEX_CIKTI_ONEKI):])\n",
        "        if t.startswith(CODEX_CIKTI_ONEKI):\n"
        "            return True\n"),
     "27Tem: ESITLIKLI bicimde deger DENETIMI komple silinir "
     "('--output-last-message=' ve '=-o' gecer)",
     {270, 279}, True, 2),
    # --- 27 TEM 2. TUR NOBETCILERI (kapatilan iki kusur) ---
    # ME14: KUSUR-1'in TAM nobetcisi — DEGERIN '-' oneki denetimi silinir (bos deger
    # denetimi KALIR). Boylece "deger baska bir bayrak" sinifi acilir; iki bicim birden
    # kizarir (tek kaynak _codex_deger_gecerli oldugunun kaniti).
    ("ME14", lambda d: yama(
        d, ICRA,
        '    if deger.startswith("-"):\n'
        "        return False\n",
        "    if False:\n"
        "        return False\n"),
     "27Tem-2: DEGERIN '-' oneki denetimi silinir (deger BASKA BIR BAYRAK olabilir)",
     {269, 277, 279, 285}, True, 4),
    # ME15: KUSUR-2'nin nobetcisi — IKINCI OKUMA silinir (yalniz ilk okuma kalir);
    # sarmalayici bayrak-degeri sizintisi geri doner. POZITIF vakalar (281/282) YESIL
    # kalmali: mutasyon yalniz sizintiyi acar, mesru cagriyi kapatmaz.
    ("ME15", lambda d: yama(
        d, ICRA,
        "    karar = _codex_karari(tokenlar)\n"
        "    if karar is None:\n"
        "        ikinci = _sarmalayici_ikinci_okuma(parcala(segment))\n"
        "        if ikinci != tokenlar:\n"
        "            karar = _codex_karari(ikinci)\n"
        "    return karar\n",
        "    return _codex_karari(tokenlar)\n"),
     "27Tem-2: SARMALAYICI ikinci okumasi silinir ('nice -n 10 codex exec' acilir)",
     {280, 283}, True, 2),
    ("ME3", lambda d: yama(d, ICRA,
                           '        if ad in ("curl", "wget") and not cip:\n',
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
    # --- 28 TEM AGENT-KAPISI NOBETCILERI (BaBa'nin '-o' turundaki 3-mutant standardi) ---
    # MA1 (a): REGEX KONTROLU silinir — _agent_karari daima "gecer" doner (beyan aranmaz).
    # Sert blokta beyan zaten karar vermez; Okan izniyle eski kurala giren 710/711 acilir.
    ("MA1", lambda d: yama(
        d, ICRA,
        "    if AGENT_MUAFIYET_RE.search(prompt):\n"
        '        return "gecer"\n',
        "    if True:\n"
        '        return "gecer"\n'),
     "28Tem AGENT: beyan REGEX kontrolu silinir (_agent_karari daima 'gecer')",
     {710, 711}, True, 2),
    # MA2 (b): DAIMA-IZIN-VER — main() AGENT kolu reddi hicbir zaman tetiklemez.
    ("MA2", lambda d: yama(
        d, ICRA,
        '        if agent_karari != "gecer":\n',
        "        if False:\n"),
     "28Tem AGENT: main() AGENT kolu daima izin verir (reddet hic tetiklenmez)",
     # 27 AGU (K318): 811 EKLENDI — cip oturumundan gelen beyansiz Agent cagrisi. Vaka
     # ROL ekseninin DISINDA, AGENT kolunda karara baglanir (rol kolu Agent'a HIC
     # ugramaz); bu mutant onu da acmali. Cakinin buyumesi kasitli: "cipte de kapali"
     # iddiasi ancak AGENT kolunu olduren mutant o vakayi da kizartirsa TASIYICIDIR.
     {400, 401, 402, 403, 406, 407, 408, 409, 700, 701, 702, 704, 705, 710, 711, 811},
     True, 16),
    # MA3 (c): agent_id MUAFIYETI TERSINE — ICRA kimlik daima MIMAR (isci muafiyeti duser).
    # Boylece beyansiz ISCI Agent/Task cagrilari (404/405) reddedilir. Tekil dosya (ICRA)
    # patch'i M2'den (KILIT+ICRA birlikte) ayrisir; beklenen AGENT worker vakalaridir.
    ("MA3", lambda d: yama(d, ICRA, KIMLIK_GOVDE_ICRA,
                           'def kimlik(girdi):\n    return "MIMAR"\n'),
     "28Tem AGENT: agent_id muafiyeti tersine (ICRA kimlik MIMAR) — isci Agent/Task RED",
     {404, 405}, False, 2),
    # --- 8 AGU MCP-TARAYICI KAPISI NOBETCILERI (AGENT turundeki 3-mutant standardi + ---
    # --- yanlis-pozitif ekseni icin TERS YONLU bir dorduncu) ---------------------------
    # MC1 (a): KAPSAM DARALTMASI — onek kumesinden 'Claude_Browser' DUSURULUR. Okan'in
    # ismen istedigi mutant. YALNIZ o sunucunun ana-oturum vakalari (501/504) kizarmali;
    # diger iki sunucu (500/502/503) YESIL kalmali — bu AYIRT EDICILIGIN kanitidir
    # (tek tek olculmeyen bir kume mutanti "hepsi birden dustu" ile karisir).
    ("MC1", lambda d: yama(
        d, ICRA,
        '    "mcp__Claude_Browser__",\n', ""),
     "8Agu MCP: onek kumesinden 'Claude_Browser' dusurulur (KAPSAM DELIGI) "
     "[20 Agu: KAPALI KOL blogunda olculur — 531/534]",
     {531, 534}, True, 2),
    # MC2 (b): KURAL KOMPLE KAPATILIR — main() MCP kolu hic tetiklemez. Uc sunucunun
    # TUM ana-oturum vakalari acilir; ISCI (510-512) ve kapsam-disi (520+) YESIL kalir.
    ("MC2", lambda d: yama(
        d, ICRA,
        "    if _mcp_tarayici_mi(tool_name):\n",
        "    if False and _mcp_tarayici_mi(tool_name):\n"),
     "8Agu MCP: main() MCP kolu komple kapatilir (KAPALI evlerde de tarayici serbest "
     "kalir) [20 Agu: KAPALI KOL blogunda olculur — 530-534]",
     {530, 531, 532, 533, 534}, True, 5),
    # MC3 (c): TERS YONLU — tanima daima True. Kapi "her MCP aracini" reddeder; ana-oturum
    # vakalari YESIL kalir ama KAPSAM DISI araclar (520-527) kizarir. Bu, K4'un
    # (yanlis-pozitif = bu depoda yayin durduran sinif) nobetcisidir: kapsami genisleten
    # bir degisiklik sessizce gecemez.
    # NOT (olculdu): mutant once '_mcp_tarayici_mi daima True' idi — o hali tool_name'i
    # "Bash"/"Agent" olan TUM cagrilari da reddediyor ve 43 vaka birden dusuyordu. Toplu
    # dusus AYIRT EDICI DEGILDIR (memory/envanter-drift-parti-basina.md: kontrol
    # mutantlarinin toplu dususu "olduruc" kusur sanilir). Mutant bu yuzden MCP AD UZAYI
    # ICINDE genisletilir: kume tek bir kaba onege ('mcp__') indirgenir.
    ("MC3", lambda d: yama(
        d, ICRA,
        '    "mcp__claude-in-chrome__",\n'
        '    "mcp__Claude_Browser__",\n'
        '    "mcp__Control_Chrome__",\n',
        '    "mcp__",\n'),
     "8Agu MCP: onek kumesi 'mcp__' ile GENISLETILIR (kapsam tasar) -> kapsam-disi "
     "araclar YANLIS-POZITIF RED alir [20 Agu: KAPALI KOL blogunda olculur — 540-544]",
     {540, 541, 542, 543, 544}, True, 5),
    # MC4 (d): KIMLIK EKSENI — kural, main() basindaki TEK ana-oturum tespitinin ONUNE
    # tasinir (yani "ikinci bir tespit uydurmak"in davranissal karsiligi). ISCI cagrilari
    # (510-512) reddedilir; ana-oturum ve kapsam-disi vakalar YESIL kalir. Kural ile
    # kimlik tespitinin AYRISMASI boylece kirmizi yakar.
    # 🔴 MC4 (20 Agu ile YENIDEN NISANLANDI): mutant kurali ISCI muafiyetinin ONUNE tasir
    # ama EV EKSENINI KORUR (`and not _tarayici_ekseni_acik_mi()`). Boylece mutant YALNIZ
    # kimlik eksenini bozar. Ev eksenini de atlayan kaba bir surum 500-504 ve 528'i de
    # kizartirdi ve MT2 ile AYIRT EDILEMEZ hale gelirdi (memory/ad-iki-rolde-mutanti-
    # golgeler.md: ayirt edilemeyen kirmizi kanit degildir). Kimlik ekseni ACIK evde
    # GOZLENEMEZ (muaf olunacak bir red yok), bu yuzden kirmizi YALNIZ kapali kol
    # blogundan gelir: 535-537.
    ("MC4", lambda d: yama(
        d, ICRA,
        '    if kimlik(girdi) == "ISCI":\n',
        '    if (_mcp_tarayici_mi(girdi.get("tool_name") or "")\n'
        '            and not _tarayici_ekseni_acik_mi()):\n'
        '        reddet(MCP_GEREKCE, sonu="")\n'
        '    if kimlik(girdi) == "ISCI":\n'),
     "8Agu MCP: kural ISCI muafiyetinin ONUNE tasinir (isci tarayicisi RED) "
     "[20 Agu: KAPALI KOL blogunda olculur — 535-537]",
     {535, 536, 537}, True, 3),
    # --- 🔴 20 AGU: EKSEN AYRIMI NOBETCILERI (Okan emri: KraL+MaCiT tarayici ACIK) ------
    # Bu iki mutant TEK BIR IDDIAYI olcer: "tarayici ekseni ile Claude-isci ekseni AYRI
    # kumelerdir ve biri otekini surukleyemez." Ikisi ZIT yonde kirmizi yakar; biri
    # hayatta kalirsa eksenler GERCEKTEN ayrilmamis demektir.
    #
    # MT1 (gorev metninde 'M1'): IKI EKSEN BIRLESTIRILIR — SERT_BLOK_EVLER bosaltilir,
    # yani "tarayiciyi actim, ayni listeyi sadelestireyim" hatasinin BIREBIR karsiligi.
    # Claude iscisi / Agent-Task yasagi ACILIR: 401/403 (Agent+Task, gecerli beyan) ve
    # 762 (isci.sh claude + gecerli beyan) allow'a duser -> KIRMIZI.
    # 🔴 TARAYICI VAKALARI (500-504) YESIL KALMALI: mutant tarayiciya DOKUNMAZ. Bu mutant
    # tam da "sessizce ikinci yasagi actim" hatasini yakalar — hicbir yesil test
    # gostermezdi (memory/ad-iki-rolde-mutanti-golgeler.md, K229 M6/M7).
    ("MT1", lambda d: yama(
        d, ICRA,
        'SERT_BLOK_EVLER = ("pruvo", "pruvo-hasat")\n',
        "SERT_BLOK_EVLER = ()\n"),
     "20Agu EKSEN: SERT_BLOK_EVLER bosaltilir (tarayici ekseniyle BIRLESTIRME hatasi) -> "
     "Claude iscisi / Agent-Task yasagi ACILIR; tarayici kolu ETKILENMEZ",
     # TAM ESITLIK YOK (bilerek): sert blok kalkinca PRUVO_CLAUDE_ISCI_IZNI'nin
     # fail-closed nobetcileri de acilir. Iddia "su uc kol MUTLAKA kirmizi" (alt kume) —
     # hangi ek nobetcinin dustugu bu mutantin konusu DEGIL. Yan eksenin YESIL kaldigi
     # ayrica ve ADIYLA olculur (YAN_EKSEN_YESIL).
     # VAKA ID'LERI: 401 (Agent+beyan), 403 (Task+beyan), 614 (isci.sh claude + BEYANLI
     # spec). 614 SATIR NUMARASI DEGIL VAKA NUMARASIDIR — ilk yazimda satir no ile
     # karistirilip 762 yazilmisti ve MT1 "eksik=762" ile KALDI (kapi dogru calisiyordu,
     # BEKLENTI yanlisti). Vaka id'si daima tuple'in ILK alanindan okunur.
     {401, 403, 614}, False, 3),
    # MT2 (gorev metninde 'M2'): TARAYICI ACMA KOLU GERI ALINIR — TARAYICI_ACIK_EVLER
    # bosaltilir. Ana oturum tarayici vakalari (500-504) yeniden RED alir -> KIRMIZI.
    # 🔴 CLAUDE-ISCI VAKALARI (401/403/762) YESIL KALMALI: mutant SERT_BLOK_EVLER'e
    # DOKUNMAZ. MT1 ile MT2'nin kirmizi kumelerinin KESISIMI BOSTUR — atif budur.
    ("MT2", lambda d: yama(
        d, ICRA, TARAYICI_ACIK_KAYNAK, "TARAYICI_ACIK_EVLER = ()\n"),
     "20Agu EKSEN: TARAYICI_ACIK_EVLER bosaltilir (tarayici acma kolu geri alinir) -> "
     "ana oturum tarayicisi yeniden RED; Claude-isci yasagi ETKILENMEZ",
     {500, 501, 502, 503, 504}, True, 5),
    # --- 13 AGU ISCI-SARMALAYICI KAPISI NOBETCILERI (AGENT/MCP turundeki desen) ---
    # Her mutant KURALIN BIR AYAGINI dusurur ve AYIRT EDICI bir kirmizi iz birakir:
    # I1 yol ekseni · I2 motor ekseni · I3 beyan ekseni · I4 fail-closed ekseni.
    # I1: YOL TAM ESITLIGI, os.path.basename esitligine cevrilir. Muafiyet anahtari
    # artik 'isci.sh' ADINA baglanir -> '/tmp/isci.sh' (vaka 620) ALLOW alir. Ayni ADDA
    # BASKA betik repo-disi icra anahtarina donusur; kuralin en pahali deligi budur.
    # 621/622 (benzer/yedek AD) etkilenmez: basename'leri 'isci.sh' DEGIL — mutantin
    # ayirt ediciligi bu kadar dardir.
    ("I1", lambda d: yama(
        d, ICRA,
        "    if argv0 == ISCI_M3_SARMALAYICI_YOLU:\n"
        "        argumanlar = [ISCI_M3_CIVILI_MOTOR] + list(tokenlar[1:])\n"
        "    elif argv0 == ISCI_SARMALAYICI_YOLU:\n",
        "    if os.path.basename(argv0) == os.path.basename(ISCI_M3_SARMALAYICI_YOLU):\n"
        "        argumanlar = [ISCI_M3_CIVILI_MOTOR] + list(tokenlar[1:])\n"
        "    elif os.path.basename(argv0) == os.path.basename(ISCI_SARMALAYICI_YOLU):\n"),
     "13Agu ISCI: yol TAM ESITLIGI basename esitligine cevrilir (YOL SINIRI delinir)",
     {620}, True, 1),
    # I2: MOTOR kapali kumesi kontrolu kaldirilir -> bilinmeyen motor ('gpt-9', vaka 610)
    # gecer. Fail-closed'in tersi: yarin eklenecek her motor kapiyi kendiliginden ACAR.
    ("I2", lambda d: yama(
        d, ICRA,
        "    if motor not in ISCI_MOTORLARI:\n",
        "    if False and motor not in ISCI_MOTORLARI:\n"),
     "13Agu ISCI: MOTOR kapali kume kontrolu kaldirilir (bilinmeyen motor gecer)",
     {610}, True, 1),
    # I3: motor=='claude' BEYAN SARTI kaldirilir -> sarmalayici AGENT-KAPISI'ni atlatan
    # bir ANAHTAR olur (mimar -> 'isci.sh claude' -> surtunmesiz Claude iscisi).
    # IKI vaka birden kizarir: 613 (beyan yok) ve 615 (spec dosyasi hic okunmaz).
    ("I3", lambda d: (
        yama(d, ICRA,
             '    if (motor == "claude" and EV_ADI in SERT_BLOK_EVLER and\n'
             '            os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") != "OKAN"):\n',
             '    if False:\n'),
        yama(d, ICRA,
             '    if motor == "claude":\n',
             '    if False and motor == "claude":\n')),
     "13Agu ISCI: motor=claude sert blok + eski BEYAN SARTI birlikte kaldirilir",
     # 20 AGU (K214) KAPSAM GENISLEMESI: 921/922 mimar-kilit-test.py'nin K214 takimidir
     # ve ikisi de SERT_BLOK kolunu olcer. Bu mutant o kolu OLDURDUGU icin ikisinin de
     # kizarmasi DOGRUDUR — kapsam ARTTI. Beklenen kume elle tasindigi icin vaka
     # eklendiginde BURASI da guncellenmelidir; guncellenmezse mutant "cok kol dustu"
     # diye OLCULEMEDI'ye duser (K214 turunda birebir yasandi: beklenen 5, gelen 7).
     # 923/924 OKAN yetkili cikisini olcer ve bu mutant altinda ALLOW kaldigi icin
     # YESIL kalir — yani I3 ile I5 hala AYRISIR (iki eksen tek ize erimedi).
     # 27 AGU (K318): 810 EKLENDI — cip oturumundan gelen 'isci.sh claude' (beyansiz).
     # ISCI-SARMALAYICI kolu ROL bayragina BAKMAZ; bu mutant o kolu oldurdugu icin cip
     # vakasi da kizarir. Yukaridaki "beklenen kume ELLE tasinir" uyarisinin geregi.
     {613, 614, 615, 707, 712, 810, 921, 922}, True, 8),
    # I4: spec OKUNAMADIGINDA red yerine 'gecer' (FAIL-OPEN). "Beyani olcemedim" yesile
    # doner. I3'ten AYRISIR: 613 (spec OKUNUYOR, beyan yok) YESIL kalir — mutantin
    # kirmizisi yalniz 615'tir, yani iki eksen tek ize erimemistir.
    ("I4", lambda d: yama(
        d, ICRA,
        "        except Exception:\n"
        "            return (\n"
        "                \"isçi sarmalayıcısı 'claude' MOTORUYLA çağrılıyor ama SPEC DOSYASI \"\n",
        "        except Exception:\n"
        '            return "gecer"\n'
        "            return (\n"
        "                \"isçi sarmalayıcısı 'claude' MOTORUYLA çağrılıyor ama SPEC DOSYASI \"\n"),
     "13Agu ISCI: spec okunamadiginda RED yerine 'gecer' (FAIL-OPEN)",
     {712}, True, 1),
    # I5 (TERS YONLU): kural KOMPLE kapatilir -> 13 Agu ONCESI hale donus. Mesru
    # delegasyon cagrilarinin HEPSI yeniden RED alir (olculen delik geri gelir). Tek
    # yonlu nobetci olu nobetcidir: "kural yakaliyor mu" kadar "kural ACIYOR mu" da olculur.
    ("I5", lambda d: yama(
        d, ICRA,
        "        isci_karari = _isci_karari(tokenlar)\n"
        "        if isci_karari is not None:\n",
        "        isci_karari = _isci_karari(tokenlar)\n"
        "        if False and isci_karari is not None:\n"),
     "13Agu ISCI: kural komple kapatilir (13 Agu ONCESI delik geri doner) — mesru "
     "delegasyon cagrilari yeniden RED",
     # 20 AGU (K214) KAPSAM GENISLEMESI: kural KOMPLE kapandigi icin K214 takiminin
     # DORDU DE kizarir — 921/922 (SERT_BLOK bekler, generic red alir) ve 923/924
     # (ALLOW bekler, RED alir). I3'ten farki bu: I3 yalniz claude kollarini oldurur,
     # I5 sarmalayici kuralinin TAMAMINI kapatir, dolayisiyla yetkili cikis da duser.
     # Beklenen kume elle tasinir; vaka eklendiginde guncellenmezse mutant
     # OLCULEMEDI'ye duser (K214 turunda: beklenen 8, gelen 12).
     {600, 601, 602, 603, 604, 631, 708, 709, 921, 922, 923, 924}, True, 12),
    # --- 13 AGU-2 SARMALAYICI KIMLIK EKSENI ---
    # J mutantlari yalniz 650-659 kimlik takiminda kosar. Boylece beklenen kume TAM
    # esitliktir; bir ekseni oldurmenin katalogdaki ilgisiz yuzlerce vakayi topluca
    # dusurmesi kanit diye sunulmaz.
    ("J1", lambda d: yama(
        d, KIMLIKORTAK,
        '    motor = cevre.get("PRUVO_ISCI_KOSUMU")\n'
        '    if motor in ISCI_MOTORLARI:\n'
        '        return "sarmalayici:" + motor\n',
        '    motor = cevre.get("PRUVO_ISCI_KOSUMU")\n'
        '    if False and motor in ISCI_MOTORLARI:\n'
        '        return "sarmalayici:" + motor\n'),
     "13Agu-2 J1: ortam kimlik ekseni komple kaldirilir",
     # 19 AGU (K214): 649 EKLENDI. Kimlik takimina CANLI BIRINCIL kat (`kimi`) vakasi
     # girdi; J1 ekseni komple oldurdugu icin o vaka da DUSMELI. Capa TAM ESITLIK
     # oldugundan yeni kol eklenince burasi da guncellenmezse mutant "esigi tutturamadi"
     # der ve kirmizi, ONARIMI DEGIL EKLEMEYI isaret eder ([[yeni-kol-mutasyon-capasini-ikizler]]).
     {649, 650, 652, 653, 654, 659}, True, 6),
    ("J2", lambda d: yama(
        d, KIMLIKORTAK,
        '    if motor in ISCI_MOTORLARI:\n',
        '    if motor is not None:\n'),
     "13Agu-2 J2: kapali kume kontrolu kaldirilir (env varligi yeter)",
     {655, 656}, True, 2),
    ("J3", lambda d: yama(
        d, KIMLIKORTAK,
        '    if motor in ISCI_MOTORLARI:\n'
        '        return "sarmalayici:" + motor\n',
        '    if motor is None or motor in ISCI_MOTORLARI:\n'
        '        return "sarmalayici:" + (motor or "claude")\n'),
     "13Agu-2 J3: env yokken de sarmalayici ISCI sayilir (MIMAR koluna sizma)",
     {651, 657}, True, 2),
    # --- 17 AGU K159 CODEX SURELI PENCERESI + MODEL KAPISI NOBETCILERI ---
    # Her mutant yeni 4 kuruldan BIRINI dusurur; AYIRT EDICI bir kirmizi iz birakir.
    # M1: model bayragi zorunlulugu kaldirilir -> V1 (900) artik ALLOW olur.
    ("M_K159_1", lambda d: yama(
        d, ICRA,
        '    if not _codex_model_bayrak_var(kalan[1:]):\n',
        '    if False and not _codex_model_bayrak_var(kalan[1:]):\n'),
     "17Agu K159: model bayragi zorunlulugu kaldirilir (bayraksiz codex exec acilir)",
     {900}, True, 1),
    # M2: amiral (CODEX_YASAK_MODELLER) reddi kaldirilir -> V2 (901) artik ALLOW olur.
    ("M_K159_2", lambda d: yama(
        d, ICRA,
        '    if model in CODEX_YASAK_MODELLER:\n',
        '    if False and model in CODEX_YASAK_MODELLER:\n'),
     "17Agu K159: amiral reddi kaldirilir (gpt-5.6-sol amiral gecer); K159 son kol: "
     "910 yasak model RED'i da amiral kapisi kapali olunca ACILIR",
     {901, 910}, True, 2),
    # M3: fail-closed (izinli kume disi) RED kaldirilir -> V5 (904) artik ALLOW olur.
    # Spec'te "fail-open" mutant — bilinmeyen model GECER yapilir.
    ("M_K159_3", lambda d: yama(
        d, ICRA,
        '    if model not in CODEX_IZINLI_MODELLER and model not in CODEX_YASAK_MODELLER:\n',
        '    if False and model not in CODEX_IZINLI_MODELLER and model not in CODEX_YASAK_MODELLER:\n'),
     "17Agu K159: bilinmeyen model fail-OPEN (bilinmeyen model gecer, yarin eklenen acar)",
     {904}, True, 1),
    # M4: pencere/tarih kontrolu kaldirilir -> V6 (905) tarih 21 Agu olsa bile ALLOW.
    # Anchor: pencere kapali kontrolu ONCESINDEKI yorum + satir. _codex_pencere_acik_mi
    # helper taniminda da gectigi icin yorumla TEKILLESTIRILDI (capasi 2 kez gecmez).
    ("M_K159_4", lambda d: yama(
        d, ICRA,
        '    if not _codex_pencere_acik_mi():\n',
        '    if False and not _codex_pencere_acik_mi():\n'),
     "17Agu K159: pencere/tarih kontrolu kaldirilir (21 Agu tarihli codex GECER)",
     {905}, True, 1),
    # === 27 AGU 2026 (K318) — ROL EKSENI NOBETCILERI =========================
    # Her mutant, rol ekseninin FARKLI bir kolunu oldurur ve HEDEF kolun vakalari
    # CAKILI bir kumeyle kirmizi yanar. Kumeler AYNI DEGILDIR — MR2 tekil (ad benzerligi),
    # MR1 'cwd menzili', MR3 pozitif kol, MR5 sinir kollari — hangi kolun oldugu ayrica
    # okunabilsin diye ([[ikinci-gorus-vakasi-birinci-gorusu-tekrar-ederse-totolojidir]]).
    # Kumeler OLCULDU, tahmin edilmedi: ilk turda MR1/MR4/MR5 icin yazdigim cakilar
    # EKSIKTI (MR1'e 807/812, MR5'e iz-iddiasi dusen 5 pozitif vaka, MR4'e 61 vaka daha
    # geldi) ve takim bunlari KIRMIZI yakti; cakilar OLCULEN degere gore duzeltildi.
    #
    # MR1 — OLCUM -> BEYAN: rol, oturum damgasindan degil KAYDIRILABILIR cwd'den okunur
    # (20 Tem'de kaldirilmis regresyonun ta kendisi). Hedef kol: KONTROL/fail-closed.
    # ANA oturum cwd'sini bir worktree'ye kaydirdiginda kapi ACILIR -> 805/806 KIRMIZI.
    ("MR1", lambda d: yama(
        d, KIMLIKORTAK,
        "    yol = girdi.get(ROL_KANALI)\n"
        "    if not isinstance(yol, str) or not yol.strip():\n"
        "        return None\n"
        "    if not worktree_kokleri:\n"
        "        return None\n",
        '    yol = girdi.get("cwd")\n'
        "    if not isinstance(yol, str) or not yol.strip():\n"
        "        return None\n"
        "    if not worktree_kokleri:\n"
        "        return None\n"
        "    for _kok in sorted(worktree_kokleri):\n"
        '        if yol == _kok or yol.startswith(_kok + "/"):\n'
        "            return _kok\n"
        "    return None\n"),
     "K318: rol OLCUMDEN degil BEYANDAN (cwd) okunur -> ANA oturum 'cd worktree' ile acilir",
     # OLCULDU: cwd'si bir worktree'ye kaydirilmis DORT ANA vakasinin hepsi acilir
     # (805 damgasi ANA · 806 damgasiz · 807 alt-dize · 812 kayitsiz uydurma). cwd'si
     # ana checkout olan 800/801 KAPALI KALIR — mutantin menzili tam olarak 'cwd'.
     {805, 806, 807, 812}, True, 4),
    # MR2 — TAM BILESEN esitligi ALT-DIZE'ye gevser. Hedef kol: ad-benzerligi kalkani.
    ("MR2", lambda d: yama(
        d, KIMLIKORTAK,
        "        if adaylar & bilesenler:\n",
        "        if any(a in yol for a in adaylar):\n"),
     "K318: damga karsilastirmasi TAM BILESEN yerine ALT-DIZE olur -> benzer ad acilir",
     {807}, True, 1),
    # MR3 — OLCUM EKSENI BOZULUR (damga kimlik fonksiyonuna cevrilir). Hedef kol: POZITIF.
    # Hat fail-closed'a duser: hicbir cip eslesmez, ANA kollari YESIL kalir. Bu mutantin
    # nobetcisi POZITIF vakalardir — "olculemedi = RED" kolu dogru tarafa dustugu icin.
    ("MR3", lambda d: yama(
        d, KIMLIKORTAK,
        '    return "".join(k if k.isalnum() else "-" for k in yol)\n',
        "    return yol\n"),
     "K318: proje damgasi uretimi bozulur -> hicbir cip olculemez, hat KAPANIR",
     # 28 AGU (K340) KAPSAM BUYUMESI: K340'in CIP-ALLOW vakalari (852 kontrol, 853 sinir
     # izi) da bu mutantin menziline MESRU olarak girdi — damga bozulunca onlar da ANA
     # sayilip RED aliyor. Mutantin ANLAMI degismedi; civili kume kapsamla BIRLIKTE
     # buyutuldu ([[batarya-kapsam-tabani-sayiyla-civilenir]]).
     {802, 803, 804, 813, 814, 852, 853}, True, 7),
    # MR4 — FAIL-CLOSED SOKULUR: damga OLCULEMEDIGINDE ANA yerine ilk worktree koku
    # dondurulur ("OLCULEMEDI = gecis"). Hedef kol: damgasiz baglamlar.
    ("MR4", lambda d: yama(
        d, KIMLIKORTAK,
        "    yol = girdi.get(ROL_KANALI)\n"
        "    if not isinstance(yol, str) or not yol.strip():\n"
        "        return None\n",
        "    yol = girdi.get(ROL_KANALI)\n"
        "    if not isinstance(yol, str) or not yol.strip():\n"
        "        return sorted(worktree_kokleri)[0] if worktree_kokleri else None\n"),
     "K318: damga YOKKEN fail-closed kalkar (olculemedi -> gecis) -> 800/806 acilir",
     # 🔴 TAM ESITLIK KULLANILMAZ VE BU BIR TAVIZ DEGIL, BULGUNUN KENDISIDIR: olculdu,
     # net=63. Kabul takimindaki eski vakalarin hicbiri `transcript_path` TASIMAZ, yani
     # fail-closed kolu kalkinca TUM mimar redleri (olcum, curl, python allowlist, isci
     # sarmalayici...) birden acilir. "OLCULEMEDI = gecis" tekil bir delik degil, kapinin
     # TOPTAN dusmesidir; patlama yaricapi burada gorunur kalsin diye asgari esikle
     # olculur. Hedef kol atfi 800 (damgasiz ANA) + 806 (damgasiz, cwd worktree).
     {800, 806}, False, 2),
    # MR5 — KAPSAM ASIMI: cip kolu ICRA kapisinin TAMAMINI atlar (ISCI gibi TAM muaf).
    # Hedef kol: "kapsam duzeltmesi, GEVSETME degil" siniri. Cipte de kapali kalmasi
    # gereken kollar (Okan emri + repo hijyeni) acilir -> 808/809/810/811 KIRMIZI.
    ("MR5", lambda d: yama(
        d, ICRA,
        '    if kimlik(girdi) == "ISCI":\n'
        "        iz_bas(kimlik_izi(girdi))\n"
        "        sys.exit(0)\n",
        '    if kimlik(girdi) == "ISCI" or rol(girdi) is not None:\n'
        "        iz_bas(kimlik_izi(girdi))\n"
        "        sys.exit(0)\n"),
     "K318: cip main() basinda TAM muaf olur -> Okan emri kollari + repo hijyeni acilir",
     # OLCULDU, IKI ETKI birden ve ikisi de KASITLI olarak cakili:
     #  (a) SINIR kollari acilir: 808 satir-ici kod · 809 repo-disi betik ·
     #      810 isci.sh claude sert blok (Okan emri) · 811 AGENT-KAPISI (Okan emri).
     #  (b) POZITIF vakalarin IZ iddiasi duser: erken cikis 'MIMAR' izi basar, oysa
     #      802/803/804/813/814 'CIP(' izi bekler. Yani iz iddiasi SUS PAYI DEGIL,
     #      yuk tasiyor — kaldirilirsa bu mutant yari korlesirdi.
     #  (c) 28 AGU (K340) KAPSAM BUYUMESI: cip main() basinda TAM muaf olunca K340'in
     #      BETIK-ICI kolu da hic kosmaz -> 850/851 (repo-disi cagri) acilir ve 853'un
     #      OLCULEMEDI izi kaybolur. Mutantin ANLAMI degismedi, menzili olculdu.
     {802, 803, 804, 808, 809, 810, 811, 813, 814, 850, 851, 853}, True, 12),
]

# ===================== KONTROL MUTANTLARI (AYIRT EDICILIK OLCUMU) =====================
# memory/beyan-edilmis-survivor.md + fikstur-degeri-mutasyon-koru.md: "N mutant kirmizi
# yakti" tek basina kanit DEGILDIR — takim her degisiklige kirmizi yaniyor da olabilir.
# Buradaki mutantlar kaynagi GERCEKTEN degistirir ama DAVRANISI degistirmez; kabul testi
# YESIL kalmali (exit 0, SIFIR kirmizi vaka). Biri kirmizi yanarsa takim ayirt edici
# degildir ve MC1-MC4'un kirmizisi da kanit sayilmaz.
# (ad, uygulayici, aciklama)
KONTROL_MUTANTLARI = [
    # 🔴 K8 (28 Agu, K340): ETKI EKSENININ AYIRT EDICILIK kontrolu — kabul ③(c). M_K340_1
    # ve M_K340_2'nin kirmizisi ancak takim "her degisiklige" kizarmiyorsa kanittir.
    # Surum damgasina eklenen KULLANILMAYAN bir sabit davranisi degistirmez; 12 K340
    # vakasinin (840-853) hepsi YESIL kalmali — ozellikle mesru repo-ici cagrilar.
    ("K8", lambda d: yama(
        d, ICRA,
        'K340_KURAL_SURUMU = "28agu-1"\n',
        'K340_KURAL_SURUMU = "28agu-1"\n_K340_KONTROL_MUTANTI = True\n'),
     "K340 etki blogua OLU bir sabit eklenir (davranis degismez) -> YESIL kalmali"),
    ("K1", lambda d: yama(
        d, ICRA,
        '    "mcp__claude-in-chrome__",\n'
        '    "mcp__Claude_Browser__",\n'
        '    "mcp__Control_Chrome__",\n',
        '    "mcp__Control_Chrome__",\n'
        '    "mcp__claude-in-chrome__",\n'
        '    "mcp__Claude_Browser__",\n'),
     "MCP onek kumesi YENIDEN SIRALANIR (ayni kume, ayni karar) -> YESIL kalmali"),
    ("K2", lambda d: yama(
        d, ICRA,
        'MCP_KURAL_SURUMU = "20agu-2"\n',
        'MCP_KURAL_SURUMU = "20agu-2"\n_MCP_KONTROL_MUTANTI = True\n'),
     "MCP blogua OLU bir sabit eklenir (davranis degismez) -> YESIL kalmali"),
    # K3: 13 Agu ISCI blogunun AYIRT EDICILIK kontrolu. I1-I5'in kirmizisi ancak yeni
    # vakalar "her degisiklige" kizarmiyorsa kanittir (memory/beyan-edilmis-survivor.md).
    ("K3", isci_motorlarini_yeniden_sirala,
     "ISCI motor kumesi YENIDEN SIRALANIR (ayni kume, ayni karar) -> YESIL kalmali"),
    # K4: 17 Agu K159 codex blogunun AYIRT EDICILIK kontrolu. M_K159_1..4'un kirmizisi
    # ancak yeni 4 kural "her degisiklige kirmizi yakiyor" degilse kanittir. Surum
    # damgasina eklenen kullanilmayan bir sabit davranisi degistirmez.
    ("K4", lambda d: yama(
        d, ICRA,
        'CODEX_KURAL_SURUMU = "17agu-1"\n',
        'CODEX_KURAL_SURUMU = "17agu-1"\n_K159_KONTROL_MUTANTI = True\n'),
     "17Agu K159 codex blogua OLU bir sabit eklenir (davranis degismez) -> YESIL kalmali"),
    # 🔴 K6 (20 Agu): TARAYICI eksen kumesinin AYIRT EDICILIK kontrolu. MT1/MT2'nin
    # kirmizisi ancak takim "her degisiklige" kizarmiyorsa kanittir. Kumeyi YENIDEN
    # SIRALAMAK ayni kumeyi ve ayni karari verir (uyelik testi 'in', sira DEGIL).
    ("K6", lambda d: yama(
        d, ICRA, TARAYICI_ACIK_KAYNAK,
        'TARAYICI_ACIK_EVLER = ("pruvo-hasat", "pruvo")\n'),
     "TARAYICI_ACIK_EVLER YENIDEN SIRALANIR (ayni kume, ayni karar) -> YESIL kalmali"),
    # 🔴 K7 (27 Agu, K318): ROL EKSENININ AYIRT EDICILIK kontrolu. MR1..MR5'in kirmizisi
    # ancak yeni 15 vaka "her degisiklige" kizarmiyorsa kanittir. Rol blogua OLU bir sabit
    # eklemek kaynagi degistirir, davranisi DEGISTIRMEZ ([[beyan-edilmis-survivor]]).
    ("K7", lambda d: yama(
        d, KIMLIKORTAK,
        'ROL_KANALI = "transcript_path"\n',
        'ROL_KANALI = "transcript_path"\n_ROL_KONTROL_MUTANTI = True\n'),
     "ROL blogua OLU bir sabit eklenir (davranis degismez) -> YESIL kalmali"),
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


# 13 AGU SERT BLOK — uc zorunlu oldurucu. Bunlar ev kapsamını davranissal olcmek icin
# kapiyi dogrudan PreToolUse payload'uyla kosturur; ana kabul takiminin KraL'a civilenmis
# REPO_ONEKI sabiti diger-ev sizintisini tek basina olcemez.
def _sert_tum_evlere_yay(dizin):
    yama(dizin, ICRA,
         'SERT_BLOK_EVLER = ("pruvo", "pruvo-hasat")\n',
         'SERT_BLOK_EVLER = ("pruvo", "pruvo-hasat", "pruvo-jenerator", '
         '"pruvo-pazarlama", "pruvo-bot", "pruvo-advisor")\n')
    yama(dizin, ICRA,
         'REPO_ONEKI = "/Users/okan/dev/pruvo/"\n',
         'REPO_ONEKI = "/Users/okan/dev/pruvo-jenerator/"\n')


SERT_MUTASYONLAR = (
    ("S1", lambda d: yama(
        d, ICRA,
        'SERT_BLOK_EVLER = ("pruvo", "pruvo-hasat")\n',
        'SERT_BLOK_EVLER = ()\n'),
     "sert blok ev kumesi bosaltilir", {}, "deny"),
    ("S2", _sert_tum_evlere_yay,
     "sert blok dort serbest eve sizdirilir (KaaN taklidi)", {}, "allow"),
    ("S3", lambda d: yama(
        d, ICRA,
        'def _agent_karari(girdi):\n'
        '    """28 TEM — AGENT-KAPISI karari (mimar ANA oturumu bir Claude iscisi acarken). Doner:\n',
        'def _agent_karari(girdi):\n'
        '    os.environ["PRUVO_CLAUDE_ISCI_IZNI"] = "OKAN" if '
        'os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") else ""\n'
        '    """28 TEM — AGENT-KAPISI karari (mimar ANA oturumu bir Claude iscisi acarken). Doner:\n'),
     "Okan izninde deger kontrolu kaldirilir; varlik yeterli olur",
     {"PRUVO_CLAUDE_ISCI_IZNI": "evet"}, "deny"),
)


def sert_mutasyonu_kostur(ad, uygulayici, ek_env):
    dizin = os.path.join(MUTASYON_KOK, ad)
    os.makedirs(dizin)
    shutil.copyfile(os.path.join(TOOLS, ICRA), os.path.join(dizin, ICRA))
    shutil.copyfile(os.path.join(TOOLS, KIMLIKORTAK), os.path.join(dizin, KIMLIKORTAK))
    uygulayici(dizin)
    payload = {
        "session_id": "sert-mutasyon",
        "cwd": "/Users/okan/dev/pruvo",
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": "codex-muafiyet: kapi kodu — sessiz-hata"},
    }
    ortam = dict(os.environ)
    ortam.pop("PRUVO_ISCI_KOSUMU", None)
    ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)
    ortam.update(ek_env)
    sonuc = subprocess.run([sys.executable, os.path.join(dizin, ICRA)],
                           input=__import__("json").dumps(payload), capture_output=True,
                           text=True, env=ortam)
    if sonuc.returncode != 0:
        return "COKTU"
    return "deny" if '"permissionDecision": "deny"' in (sonuc.stdout or "") else "allow"


def mutasyonu_kostur(ad, uygulayici, kendi_testi=False, yalniz_kimlik=False):
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
    komut = [sys.executable, kosulacak, dizin]
    if yalniz_kimlik:
        komut.append("--kimlik-ekseni")
    sonuc = subprocess.run(komut, capture_output=True, text=True)
    kirmizi = set()
    for satir in (sonuc.stdout or "").splitlines():
        m = re.match(r"\s*vaka (\d+):", satir)
        if m:
            kirmizi.add(int(m.group(1)))
    return kirmizi, sonuc.returncode


# === 27 AGU 2026 (K318) — TABAN OLCUMU (mutant NE EKLEDI?) ====================
# 🔴 OLCULEN KUSUR (27 Agu, bu turda): takim mutantin kirmizi kumesini HAM okuyordu.
# Kabul testinin MUTASYONSUZ halinde de kirmizi vakalar varsa (bugun 7 tane: 232/233/
# 273/274/281/902/910 — hepsi codex SURELI PENCERESI 'CODEX_PENCERE_BITIS' gectigi icin)
# o sabit kirmizilar HER mutantin kumesine karisiyor ve `tam=True` olan HER mutant
# "KALDI" okunuyordu; KONTROL mutantlari da (sifir kirmizi + exit 0 beklerler) KALDI
# oluyordu. Yani nobetci OLU: hicbir mutant hukum uretemiyordu, ama takim bunu
# "mutasyonlar tutmadi" diye rapor ediyordu — sahte kirmizi, gercek kirmiziyi gizler.
# HUKUM ([[olcut-civilenirken-taban-olculmeli]]): olcut TABANDAN cikarilarak civilenir.
# Mutantin ISARETI = kirmizi_kume - TABAN. TABAN'in KENDISI ayrica ve GORUNUR bildirilir;
# bos degilse takim YINE exit 1 verir — taban kirmizisi 'net yesil' ile YUTULMAZ.
def taban_kirmizisi():
    """MUTASYONSUZ kopyanin kirmizi kumesi + cikis kodu. Uygulayici HICBIR yama yapmaz."""
    return mutasyonu_kostur("TABAN", lambda d: None)


def main():
    global MUTASYON_KOK
    MUTASYON_KOK = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-kapi-mutasyon-"))
    print("MUTASYON DIZINI (gecici): " + MUTASYON_KOK)

    basarisiz = []
    try:
        TABAN, TABAN_CIKIS = taban_kirmizisi()
        print("TABAN (mutasyonsuz kopya) | kirmizi={:<3} | vakalar={} | exit={}".format(
            len(TABAN), sorted(TABAN), TABAN_CIKIS))
        print("          Asagidaki her mutantin ISARETI = kirmizi - TABAN (net). "
              "TABAN bos degilse takim yine KIRMIZI kapanir.")
        for ad, uygulayici, aciklama, beklenen, tam, asgari in MUTASYONLAR:
            ham, _ = mutasyonu_kostur(ad, uygulayici, yalniz_kimlik=ad.startswith("J"))
            kirmizi = ham - TABAN
            eksik = beklenen - kirmizi
            tamam = (not eksik) and len(kirmizi) >= asgari
            if tam and kirmizi != beklenen:
                tamam = False
            # OLCULEMEZ MUTANT: sentinel vakasi ZATEN tabanda kirmizi ise bu mutant
            # hakkinda hukum verilemez. Sessizce yesil SAYILMAZ.
            olculemez = beklenen & TABAN
            if olculemez:
                tamam = False
                aciklama += (" [OLCULEMEZ: sentinel vakalari TABANDA kirmizi: " +
                             str(sorted(olculemez)) + "]")
            # 🔴 20 AGU — YAN EKSEN NOBETI: bir mutantin "hedef kolu kirmizi yakmasi" TEK
            # BASINA kanit degildir; YAN eksenin YESIL kaldigi da AYRI olculmelidir. MT1
            # (Claude yasagini acar) tarayiciya, MT2 (tarayiciyi kapatir) Claude yasagina
            # DOKUNMAMALIDIR. Yan eksen de kizariyorsa mutant "iki ekseni birden bozdu"
            # demektir ve ayrimin kaniti COKER.
            yan = YAN_EKSEN_YESIL.get(ad)
            if yan and (yan & kirmizi):
                tamam = False
                aciklama += (" [YAN EKSEN KIRLENDI: " +
                             str(sorted(yan & kirmizi)) + " — eksen ayrimi KANITLANMADI]")
            if ad == "M7" and (M7_YESIL_KALMALI & kirmizi):
                tamam = False
                aciklama += " [basename kalkani DELINDI: " + str(sorted(M7_YESIL_KALMALI & kirmizi)) + "]"
            if not kirmizi:
                tamam = False
                aciklama += " [NOBETSIZ BOLGE: sifir kirmizi]"
            print("MUTASYON {:<4} | net={:<3} | vakalar={} | BEKLENEN>={} {} | {}".format(
                ad, len(kirmizi), sorted(kirmizi), asgari,
                ("== " + str(sorted(beklenen))) if tam else ("uzerinde " + str(sorted(beklenen))),
                "GECTI" if tamam else "KALDI"))
            print("          {} | {}".format(aciklama, "eksik=" + str(sorted(eksik)) if eksik else "eksik=yok"))
            if not tamam:
                basarisiz.append(ad)

        for ad, uygulayici, aciklama, ek_env, dogru_beklenen in SERT_MUTASYONLAR:
            olculen = sert_mutasyonu_kostur(ad, uygulayici, ek_env)
            olduruldu = olculen != dogru_beklenen
            print("SERT MUTASYON {} | dogru={} mutant={} | {} | {}".format(
                ad, dogru_beklenen, olculen, "GECTI" if olduruldu else "KALDI", aciklama))
            if not olduruldu:
                basarisiz.append(ad)

        # KONTROL MUTANTLARI: kriter TERSTIR — SIFIR kirmizi + exit 0 beklenir. Takimin
        # "her degisiklige kirmizi yaniyor" olmadiginin, yani AYIRT EDICI oldugunun kaniti.
        for ad, uygulayici, aciklama in KONTROL_MUTANTLARI:
            ham, cikis = mutasyonu_kostur(ad, uygulayici)
            kirmizi = ham - TABAN
            # K318: kriter TABANA GORE. Cikis kodu da tabanla karsilastirilir — taban
            # zaten 1 iken "exit 0 bekle" demek kontrol mutantlarini olcumsuz birakirdi.
            tamam = (not kirmizi) and cikis == TABAN_CIKIS
            print("KONTROL {:<4} | net={:<3} | vakalar={} | exit={} (taban exit={} + "
                  "SIFIR net kirmizi BEKLENIR) | {}".format(
                      ad, len(kirmizi), sorted(kirmizi), cikis, TABAN_CIKIS,
                      "GECTI" if tamam else "KALDI"))
            print("          {}".format(aciklama))
            if not tamam:
                basarisiz.append("KONTROL-" + ad)

        # CEVRE-ARIZA ENJEKSIYONU (B6-yan): kriter cikis kodudur, kirmizi vaka degil.
        for ad, uygulayici, aciklama in sorted(KENDI_TESTINI_KOSAN):
            _, cikis = mutasyonu_kostur(ad, uygulayici, kendi_testi=True)
            tamam = (cikis != 0)
            not_ = ""
            if TABAN_CIKIS != 0:
                # K318 GORUNURLUK: taban ZATEN exit 1 iken "exit 0 olmamali" olcutu
                # BOSA DONER — mutant kaldirilsa da yesil yanar. Sessiz yesil YASAK.
                not_ = " [BOSA DONUYOR: taban exit={} — olcut ayirt etmiyor]".format(
                    TABAN_CIKIS)
            print("CEVRE-ARIZA {:<3} | exit={} (0 OLMAMALI) | {}{}".format(
                ad, cikis, "GECTI" if tamam else "KALDI", not_))
            print("          {}".format(aciklama))
            if not tamam:
                basarisiz.append(ad)
    finally:
        shutil.rmtree(MUTASYON_KOK, ignore_errors=True)
        # C1/C2 enjeksiyonlari gecici worktree kaydi birakmis olabilir — temizle.
        subprocess.run(["git", "-C", KOK, "worktree", "prune"],
                       capture_output=True, text=True)

    toplam = (len(MUTASYONLAR) + len(SERT_MUTASYONLAR) + len(KENDI_TESTINI_KOSAN) +
              len(KONTROL_MUTANTLARI))
    print("")
    print("TABAN KIRMIZI (mutasyondan BAGIMSIZ): {} {}".format(
        len(TABAN), sorted(TABAN) or ""))
    if basarisiz:
        print("SONUC: KIRMIZI — esigi tutturamayan mutasyonlar: " + ", ".join(basarisiz))
        sys.exit(1)
    if TABAN:
        # K318: net olcum yesil olsa BILE taban kirmizisi yutulmaz. Mutantlarin hukmu
        # yukarida vaka vaka basildi; burada kapanan sey TABAN'dir, mutasyon degil.
        print("SONUC: KIRMIZI — mutantlarin NET isareti tam ({}/{}) ama TABAN kirmizi: {}. "
              "Kabul testinin MUTASYONSUZ hali once yesillenmeli.".format(
                  len(MUTASYONLAR) + len(SERT_MUTASYONLAR) + len(KENDI_TESTINI_KOSAN) +
                  len(KONTROL_MUTANTLARI),
                  len(MUTASYONLAR) + len(SERT_MUTASYONLAR) + len(KENDI_TESTINI_KOSAN) +
                  len(KONTROL_MUTANTLARI), sorted(TABAN)))
        sys.exit(1)
    print("SONUC: {}/{} mutant beklenen isareti verdi "
          "({} kural mutasyonu KIRMIZI + {} kontrol mutanti YESIL + {} cevre-ariza "
          "enjeksiyonu).".format(
              toplam, toplam, len(MUTASYONLAR) + len(SERT_MUTASYONLAR),
              len(KONTROL_MUTANTLARI),
              len(KENDI_TESTINI_KOSAN)))
    sys.exit(0)


main()
