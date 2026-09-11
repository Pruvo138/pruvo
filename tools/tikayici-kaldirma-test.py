#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIKAYICI KALDIRMA — KABUL BATARYASI (Okan emri, 11 Eyl 2026) — BIRLESTIRILMIS.

OKAN EMRI: "tum tikayicilari kaldir". Kaldirilan sey **REDDETME YETKISIDIR,
OLCUM DEGIL**: teshis satiri stderr'e yazilmaya DEVAM eder, cikis kodu 0 olur
(`HUKUM=RED` -> `HUKUM=RAPOR`).

=== BIRLESTIRME GEREKCESI (Okan 11 Eyl 2026, iki dilim) =========================
Iki dilim AYNI dosyayi yazdi; biri secmek digerinin kapisini olcumsuz birakir.
  DILIM 1 (isci hatti, main'de): K1..K7 KOLLARI — N2B parti kapisi · Claude-isci
    reddi · tur zorlamasi · worktree tavani. 7 KOL, hepsi `--kol` ile secilebilir.
  DILIM 2 (mimar kapilari, dal'da): M1..M4 KALEMLERI — mimar-icra-kapisi ·
    mimar-kod-kilidi · komut-stili-kapisi · defter/kutu/hafiza kotalari (500).
    52 VAKA, hepsi kaydet() ile sayilir.

=== NEDEN AYRI BATARYA: parti-kapisi.py --kendini-test =============================
[[fail-closed-kol-arkasindaki-kolu-maskeler]]: parti-kapisi.py --kendini-test
"red uretiyor mu" eksenini olcer. Bu dosya TERS ekseni olcer: "artik hicbir
cagriyi reddetmiyor ama teshisi HALA basiyor mu". Ikisi ayni dosyaya konursa
kaldirma isi kendi bekcisini de susturur.

=== MUTASYON DISIPLINI ============================================================
[[mutant-canli-govdede-yasamaz]]: mutant yuku uretim dosyasina yazilirsa bir
tur unutuldugunda kapi SESSIZCE geri doner. Her mutant gecici bir dizine KOPYA
cikarir, kopyayi metinsel olarak bozar ve olcumu KOPYAYA karsi kosar. Uretim
dosyasina TEK BAYT yazilmaz.
[[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]: her yamanin CAPASI
burada ACIKCA yazilir; capa kaynakta BULUNAMAZSA mutant `CAPA_YOK` ile COKER
(sessizce "yanmadi" demez).
[[mutant-kopyasi-cokerse-izin-okunur]]: yamasiz kopya YESIL olmali; olmazsa
olculen sey mutant degil KOPYANIN KENDISIDIR.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
KAPI = os.path.join(KOK, "tools", "parti-kapisi.py")
ISCI_SH = os.path.expanduser("~/.claude/cron/isci.sh")
RAPOR_JETON = "RAPOR"
ANA_DAMGA = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/kabul.jsonl"

# Iki dilimin sayaclari:
#   kol_sonuclar = [(ad, ok, satirlar)]   — main K1..K7 icin
#   sonuclar     = [(ad, gecti, olc, bek, not)] — dal M1..M4 (52 kayit)
kol_sonuclar = []
sonuclar = []


# ==============================================================================
# DILIM 1 — ISCI HATTI KOLLARI (main branch surumundan; 7 KOL)
# ==============================================================================
_MUT_KAPI_YAMALARI = {
    # Reddetme yolu GERI KONUR: `kanca` yine `deny` JSON'u basar.
    "MUT-DENY-GERI": (
        '    if sonuc["HUKUM"] == HUKUM_RAPOR:\n'
        "        # 🔴 ESKIDEN BURASI `_reddet(...)` IDI.",
        '    if sonuc["HUKUM"] == HUKUM_RAPOR:\n'
        "        import json as _j\n"
        "        print(_j.dumps({\"hookSpecificOutput\": {\n"
        "            \"hookEventName\": \"PreToolUse\",\n"
        "            \"permissionDecision\": \"deny\",\n"
        "            \"permissionDecisionReason\": hukum_satiri(sonuc)}},\n"
        "            ensure_ascii=False))\n"
        "        return 0\n"
        "        # 🔴 ESKIDEN BURASI `_reddet(...)` IDI.",
    ),
    # `--isci-kapi` yine sifir-disi rc doner (isci.sh orada `exit 3` ederdi).
    "MUT-RC-GERI": (
        '        sys.stdout.write(hukum_satiri(sonuc) + "\\n")\n'
        "        return RC_GECER\n",
        '        sys.stdout.write(hukum_satiri(sonuc) + "\\n")\n'
        "        return 1\n",
    ),
    # TESHIS SUSTURULUR: hukum satiri basilmaz (sayi kaybolur).
    "MUT-SESSIZ": (
        '        sys.stderr.write("%s\\n" % hukum_satiri(sonuc))\n'
        "        return 0\n",
        "        return 0\n",
    ),
    # Muafiyet kacis yolu GERI KONUR (ikinci kural kopyasi).
    "MUT-KACIS-GERI": (
        "N2B_OLCULEMEDI_JETON = \"N2B-OLCULEMEDI\"",
        "N2B_OLCULEMEDI_JETON = \"N2B-OLCULEMEDI\"\n"
        "MUAF_ETIKET_ONEKLERI = (\"tamir\", \"onarim\", \"kabul\")",
    ),
}


def _mutant_kapi(mutant):
    """Uretim kapisinin IZOLE, bozulmus bir kopyasini yazar; yolunu doner."""
    capa, yeni = _MUT_KAPI_YAMALARI[mutant]
    kaynak = open(KAPI, "r", encoding="utf-8").read()
    if kaynak.count(capa) != 1:
        raise SystemExit(
            "MUTANT %s CAPA-YOK: capa kaynakta %d kez gecti (beklenen 1). "
            "Mutant NEYI yamadigini bilmiyor -> olcum GECERSIZ."
            % (mutant, kaynak.count(capa)))
    dizin = tempfile.mkdtemp(prefix="tikayici-mutant-")
    hedef = os.path.join(dizin, "parti-kapisi.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(capa, yeni))
    # T4 kardesi: uretim kapisi kardes yoksa KANONIK yola duser, sorun yok.
    return hedef

# ------------------------------------------------------------------------------
# BUGUN REDDEDILEN GIRDILER — TABAN ve KABUL ayni listeden kosar.
# 🔴 Liste TEK KAYNAK: taban olcumu de kabul olcumu de burayi okur, boylece
# "taban baska girdiyle alindi" kacamagi kapanir.
# ------------------------------------------------------------------------------
KANCA_VAKALARI = [
    # (ad, komut, aciklama)
    ("A", 'grep -n "parti-kapisi\\|N2B" /Users/okan/.claude/cron/isci.sh',
     "mimarin BU turda yedigi salt-okuma grep (tirnak icinde borular)"),
    ("B", 'grep -rn "isci.sh" /Users/okan/dev/pruvo/tools',
     "etiketsiz salt-okuma tarama"),
    ("C", 'python3 /Users/okan/.claude/cron/isci.sh minimax-m3 '
          '/Users/okan/dev/pruvo /tmp/spec.md yeni-parti',
     "YORUMLAYICI ile muaf-DISI etiketli GERCEK is baslatma"),
    ("D", '/Users/okan/.claude/cron/isci.sh minimax-m3 /Users/okan/dev/pruvo '
          '/tmp/spec.md yeni-parti',
     "DIREKT cagri, muaf-DISI etiket"),
    ("E", 'echo "" | /Users/okan/.claude/cron/isci.sh minimax-m3 '
          '/Users/okan/dev/pruvo /tmp/spec.md onarim-tikayici-kabul',
     "boru onekli onarim cagrisi (eski `echo \"\" |` tuzagi)"),
]

# --isci-kapi yuzeyi: (etiket, aciklama)
ISCI_KAPI_VAKALARI = [
    ("yeni-parti", "muaf-DISI etiket"),
    ("", "etiket OKUNAMADI kovasi"),
    ("onarim-tikayici-kabul", "muaf onekli etiket"),
]

# Teshis alanlari: kaldirma sonrasi AYNEN durmali (sayi kaybolursa sikayet bir
# daha olculemez — bugun tam bu oldu, `grep -c N2B isci.log` = 0).
TESHIS_ALANLARI = ("KOL=", "EV=", "ACIK=", "SEBEP=")


def _kapi_yolu(mutant):
    """Mutant varsa IZOLE bozulmus kopya, yoksa URETIM kapisi."""
    if mutant and mutant in _MUT_KAPI_YAMALARI:
        return _mutant_kapi(mutant)
    return KAPI


def _kanca_kosumu(komut, cwd=KOK, mutant=None):
    """--kanca yuzeyini kosar. Doner: (karar, hukum_satiri, stderr, rc)."""
    girdi = json.dumps({"tool_name": "Bash", "cwd": cwd,
                        "tool_input": {"command": komut}})
    argv = [sys.executable, _kapi_yolu(mutant), "--kanca"]
    p = subprocess.run(argv, input=girdi, capture_output=True, text=True)
    karar = "GECER"
    gerekce = ""
    if p.stdout.strip():
        try:
            hso = json.loads(p.stdout).get("hookSpecificOutput", {})
            karar = hso.get("permissionDecision", "?")
            gerekce = hso.get("permissionDecisionReason", "")
        except ValueError:
            karar = "JSON-DEGIL"
    # 🔴 Hukum satiri IKI yerden de aranir: RED yolunda JSON gerekcesinde,
    # RAPOR yolunda stderr'de. Tek yerden aranirsa TABAN olcumu "hukum satiri
    # YOK" diye yalan soyler ve kaldirmanin ONCESI kayda gecmez.
    ham = gerekce + "\n" + p.stderr
    hukum = [s for s in ham.splitlines() if s.startswith("N2B HUKUM=")]
    return karar, (hukum[0] if hukum else ""), ham, p.returncode


def _isci_kapi_kosumu(etiket, mutant=None):
    argv = [sys.executable, _kapi_yolu(mutant), "--isci-kapi", "minimax-m3",
            KOK, "/tmp/spec.md", etiket]
    p = subprocess.run(argv, capture_output=True, text=True)
    ham = p.stdout + p.stderr
    hukum = [s for s in ham.splitlines() if s.startswith("N2B HUKUM=")]
    return (hukum[0] if hukum else ""), p.returncode, ham


# ------------------------------------------------------------------------------
# K1 — --kanca yuzeyi hicbir cagriyi REDDETMEZ, teshis KORUNUR
# ------------------------------------------------------------------------------
def k1_kanca(mutant=None):
    satirlar = []
    deny = 0
    hukumsuz = 0
    for ad, komut, aciklama in KANCA_VAKALARI:
        karar, hukum, err, rc = _kanca_kosumu(komut, mutant=mutant)
        if karar == "deny":
            deny += 1
        # Teshis zorunlulugu YALNIZ kapiya tabi (YENI is) kovasinda aranir;
        # SUREN/OKUMA kollari zaten sessiz gecerdi, onlari bozmadik.
        tabi = "SEBEP=" in hukum
        if tabi and not all(alan in hukum for alan in TESHIS_ALANLARI):
            hukumsuz += 1
        satirlar.append("    | VAKA %s karar=%-6s rc=%d  %s"
                        % (ad, karar, rc, hukum or "(hukum satiri YOK)"))
        satirlar.append("    |        %s" % aciklama)
    # Kapiya tabi olan (YENI) vakalarin HEPSI hukum satiri basmali.
    tabi_sayi = sum(1 for s in satirlar if "N2B HUKUM=" in s)
    ok = (deny == 0 and hukumsuz == 0 and tabi_sayi >= 3)
    satirlar.insert(0, "    | deny=%d (beklenen 0) · teshis EKSIK=%d (beklenen 0)"
                       " · hukum satiri basan vaka=%d (beklenen >=3)"
                    % (deny, hukumsuz, tabi_sayi))
    return ok, satirlar


# ------------------------------------------------------------------------------
# K2 — --isci-kapi yuzeyi rc=0, teshis KORUNUR
# ------------------------------------------------------------------------------
def k2_isci_kapi(mutant=None):
    satirlar = []
    kotu_rc = 0
    hukumsuz = 0
    for etiket, aciklama in ISCI_KAPI_VAKALARI:
        hukum, rc, ham = _isci_kapi_kosumu(etiket, mutant=mutant)
        if rc != 0:
            kotu_rc += 1
        if not hukum or not all(a in hukum for a in TESHIS_ALANLARI):
            hukumsuz += 1
        satirlar.append("    | ETIKET=%-24r rc=%d  %s"
                        % (etiket, rc, hukum or "(hukum satiri YOK)"))
        satirlar.append("    |        %s" % aciklama)
    ok = (kotu_rc == 0 and hukumsuz == 0)
    satirlar.insert(0, "    | rc!=0 sayisi=%d (beklenen 0) · teshis EKSIK=%d "
                       "(beklenen 0)" % (kotu_rc, hukumsuz))
    return ok, satirlar


# ------------------------------------------------------------------------------
# K3 — MUAF_ETIKET_ONEKLERI kacis yolu SILINDI, ikinci kopya birakilmadi
# ------------------------------------------------------------------------------
# 🔴 IKI YONLU + NON-GROWTH ([[grep-sifir-nobetcisi-yasak-kaydinda-oludur]]):
# tek yonlu "grep==0" nobetcisi, ad hem ATIF hem YASAK olabildigi icin oludur.
# Bu kol (a) yasak sembolun KOD govdesinde OLMADIGINI (b) kapinin HALA
# yasadigini (hukum satiri basiyor) birlikte olcer.
YASAK_SEMBOLLER = ("MUAF_ETIKET_ONEKLERI", "N2B_MUAF_JETON")


def _kod_satirlari(yol):
    """Yorum ve docstring DISI satirlar. Kaba ama tek yonlu: yorumda gecen ad
    'kacis yolu hala var' kaniti DEGILDIR, kodda gecen ad kanittir."""
    ham = open(yol, "r", encoding="utf-8").read()
    # docstring'leri kabaca dus
    ham = re.sub(r'"""(?:.|\n)*?"""', "", ham)
    ham = re.sub(r"'''(?:.|\n)*?'''", "", ham)
    out = []
    for i, s in enumerate(ham.splitlines(), 1):
        g = s.strip()
        if not g or g.startswith("#"):
            continue
        out.append((i, s))
    return out


def k3_kacis_yolu(mutant=None):
    satirlar = []
    bulgu = []
    yol = _kapi_yolu(mutant)
    for no, s in _kod_satirlari(yol):
        for sembol in YASAK_SEMBOLLER:
            if sembol in s:
                bulgu.append("%s:%d %s" % (os.path.basename(yol), no,
                                           s.strip()[:90]))
    for b in bulgu[:8]:
        satirlar.append("    | %s" % b)
    satirlar.insert(0, "    | kod govdesinde yasak sembol sayisi=%d (beklenen 0)"
                    % len(bulgu))
    return (len(bulgu) == 0), satirlar


# ------------------------------------------------------------------------------
# ORTAK — kaynak okuma + metin mutasyonu (DOSYAYA YAZMADAN)
# ------------------------------------------------------------------------------
# 🔴 K4/K5/K6 kolları KAYNAK METNI olcer, dosyayi DEGISTIRMEZ. Mutant yuku
# bellekteki dizgeye uygulanir: [[mutant-canli-govdede-yasamaz]].
ICRA_KAPISI = os.path.join(KOK, "tools", "mimar-icra-kapisi.py")
BEKCI = os.path.expanduser("~/.claude/cron/isci-tur-bekcisi.py")
WORKTREE_NOBETI = os.path.join(KOK, "tools", "worktree-tavan-nobeti.py")


NOBET_KAPISI = os.path.expanduser("~/.claude/cron/nobet-kapi.py")


def _metin(yol):
    try:
        return open(yol, "r", encoding="utf-8").read()
    except OSError:
        return None


def _mutasyon(metin, eski, yeni, mutant):
    """Metin ustunde CAPALI mutasyon. 🔴 Capa yoksa SESSIZ GECMEZ, COKER.

    [[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]: capasi kaymis bir
    mutant hicbir sey degistirmez, vaka YESIL kalir ve bu "kol saglam" diye
    OKUNUR. Yanlis sonuc tam tersidir: kol OLCULMEDI.
    """
    if metin.count(eski) < 1:
        raise SystemExit(
            "MUTANT %s CAPA-YOK: %r kaynakta bulunamadi -> kol OLCULMEDI"
            % (mutant, eski[:70]))
    return metin.replace(eski, yeni)


def _kod_govdesi(metin):
    """Yorum ve docstring DISI satirlar: (satir_no, satir).

    🔴 SATIR NO KAYNAK METINDEKI GERCEK NUMARADIR. Ilk surumde docstring'ler
    SILINEREK numaralandiriliyordu; donen `no` kirpilmis metne aitti ve
    cagiran onu HAM metne indeksleyince YANLIS PENCEREYI okuyordu —
    `MUT-TUR-ZORLAMASI-GERI` mutanti tam bu yuzden KOR kaldi (kesme kolu geri
    kondu, kol yine YESIL yandi). Docstring satirlari artik SILINMIYOR,
    BOSALTILIYOR: numaralar korunur.
    """
    ham = re.sub(r'"""(?:.|\n)*?"""',
                 lambda m: "\n" * m.group(0).count("\n"), metin)
    ham = re.sub(r"'''(?:.|\n)*?'''",
                 lambda m: "\n" * m.group(0).count("\n"), ham)
    out = []
    for i, s in enumerate(ham.splitlines(), 1):
        g = s.strip()
        if not g or g.startswith("#"):
            continue
        out.append((i, s))
    return out


# ------------------------------------------------------------------------------
# K4 — Claude iscisi KraL+MaCiT'te KOSULSUZ RED etmiyor
# ------------------------------------------------------------------------------
def k4_claude_isci(mutant=None):
    metin = _metin(ICRA_KAPISI)
    satirlar = []
    if metin is None:
        return None, ["    | OLCULEMEDI: %s okunamadi" % ICRA_KAPISI]
    if mutant == "MUT-CLAUDE-RED-GERI":
        # Reddetme yolu GERI KONUR (izole metinde).
        metin = metin.replace(
            "        _sert_blok_tanisi(\"isci.sh-claude\")",
            "        return _sert_blok_gerekcesi()")
    # (a) KOSULSUZ RED izi: SERT_BLOK kolundan `return <gerekce>` donen satir.
    red_izleri = []
    for no, s in _kod_govdesi(metin):
        if re.search(r"return\s+_sert_blok_gerekcesi\s*\(", s):
            red_izleri.append("%s:%d %s"
                              % (os.path.basename(ICRA_KAPISI), no, s.strip()))
    # (b) RAPOR kolu YERINDE mi? (teshis susturulmadi)
    rapor_izi = ("MOTOR-SECIMI=claude" in metin
                 and "_sert_blok_tanisi" in metin)
    for b in red_izleri[:8]:
        satirlar.append("    | 🔴 KOSULSUZ RED izi: %s" % b)
    satirlar.insert(0, "    | SERT_BLOK `return` sayisi=%d (beklenen 0) · "
                       "MOTOR-SECIMI RAPOR izi=%s"
                    % (len(red_izleri), "VAR" if rapor_izi else "🔴 YOK"))
    return (not red_izleri and rapor_izi), satirlar


# ------------------------------------------------------------------------------
# K5 — ASILMA zaman asimi KALDI · isi ortasindan kesen TUR ZORLAMASI YOK
# ------------------------------------------------------------------------------
# 🔴 SPEC KALEM 3'UN AYRIMI BURADA SAYIYA DONUSUR. Iki ayak AYNI kosumda:
#   ① `--azami-sn` MUTLAK SURE kolu KESMEYE DEVAM ETMELI (gercek kilitlenme)
#   ② TUR SAYISINA bagli kesme OLMAMALI (uretken isi ortasindan kesmek)
# Tek ayak olculseydi "hepsini kaldirdim" da "hicbirini kaldirmadim" da ayni
# yesili verirdi.
def k5_tur_tavani(mutant=None):
    """🔴 IKI DOSYA, IKI EKSEN — ayrim KODDAN okundu, spec'ten DEGIL.

    OLCULEN GERCEK (11 Eyl, bu turda): `isci-tur-bekcisi.py`nin `--azami-sn`
    kolu HICBIR ZAMAN OLDURMEDI — `BEKCI=SURE_TAVANI` yazip `return 0` eder,
    yani bekci cekilir, kosum SURER. Bekcideki TEK oldurme yolu TUR SAYISINA
    bagli olandi ve kaldirilan O'dur.
    GERCEK ASILMA KESICISI BASKA DOSYADADIR: `nobet-kapi.py`
    `TUR_ZAMAN_ASIMI_SN=1500` (ilerlemeyen tur) / `TUR_ONARIM_ZAMAN_ASIMI_SN`
    (ilerleyen tur). O kol ZAMAN eksenlidir, tur saymaz ve DOKUNULMADI.
    """
    bekci = _metin(BEKCI)
    nobet = _metin(NOBET_KAPISI)
    satirlar = []
    if bekci is None:
        return None, ["    | OLCULEMEDI: %s okunamadi" % BEKCI]
    if nobet is None:
        return None, ["    | OLCULEMEDI: %s okunamadi" % NOBET_KAPISI]
    if mutant == "MUT-ASILMA-KESICI-SILINDI":
        # ① ZAMAN eksenli asilma kesicisi SUSTURULUR (baska dosyada).
        nobet = _mutasyon(nobet, "TUR_ZAMAN_ASIMI_SN = 1500",
                          "TUR_ZAMAN_ASIMI_SN_KALDIRILDI = 1500", mutant)
    if mutant == "MUT-TUR-ZORLAMASI-GERI":
        # ② TUR eksenli kesme GERI KONUR.
        bekci = _mutasyon(
            bekci,
            "if son_tur >= args.tavan and not tavan_raporlandi:",
            "if son_tur >= args.tavan:\n"
            "                        _pid_kes(args.pid, kok_pid_korunsun=True)\n"
            "                        return 0\n"
            "                    if False:", mutant)

    # ① ASILMA (ZAMAN) kolu — KALMALI.
    asilma_esigi = bool(re.search(r"^TUR_ZAMAN_ASIMI_SN\s*=\s*\d+", nobet,
                                  re.M))
    asilma_onarim = bool(re.search(r"^TUR_ONARIM_ZAMAN_ASIMI_SN\s*=\s*\d+",
                                   nobet, re.M))
    # ② TUR (SAYI) kolunda kesme/cikma OLMAMALI.
    tur_kesme = []
    bekci_satirlari = bekci.splitlines()
    for no, s in _kod_govdesi(bekci):
        if not re.search(r"son_tur\s*>=\s*args\.tavan", s):
            continue
        pencere = "\n".join(bekci_satirlari[no:no + 6])
        if re.search(r"_pid_kes\(|^\s+return\s", pencere, re.M):
            tur_kesme.append("%s:%d %s"
                             % (os.path.basename(BEKCI), no, s.strip()[:80]))
    tur_raporu = "BEKCI=TUR_TAVANI_ASILDI" in bekci
    for b in tur_kesme[:8]:
        satirlar.append("    | 🔴 TUR ZORLAMASI (kesme kolu GERI GELDI): %s" % b)
    satirlar.insert(0,
                    "    | ① ASILMA kolu / ZAMAN ekseni (nobet-kapi.py): "
                    "TUR_ZAMAN_ASIMI_SN=%s · TUR_ONARIM_ZAMAN_ASIMI_SN=%s "
                    "(ikisi de VAR olmali — DOKUNULMADI)"
                    % ("VAR" if asilma_esigi else "🔴 YOK",
                       "VAR" if asilma_onarim else "🔴 YOK"))
    satirlar.insert(1,
                    "    | ② TUR kolu / SAYI ekseni (isci-tur-bekcisi.py): "
                    "kesme sayisi=%d (beklenen 0) · RAPOR jetonu=%s"
                    % (len(tur_kesme), "VAR" if tur_raporu else "🔴 YOK"))
    return (asilma_esigi and asilma_onarim and not tur_kesme
            and tur_raporu), satirlar


# ------------------------------------------------------------------------------
# K6 — worktree SAYI ekseni UYARMIYOR; ARTIK olcusu RAPOR olarak DURUYOR
# ------------------------------------------------------------------------------
def k6_worktree(mutant=None):
    metin = _metin(WORKTREE_NOBETI)
    satirlar = []
    if metin is None:
        return None, ["    | OLCULEMEDI: %s okunamadi" % WORKTREE_NOBETI]
    if mutant == "MUT-WORKTREE-SAYI-GERI":
        metin = _mutasyon(
            metin, 'satirlar.append("WORKTREE SAYI=%d TAVAN=%d',
            'satirlar.append("!! UYARI: WORKTREE TAVANI ASILDI — ROL=MIMAR")\n'
            '        satirlar.append("WORKTREE SAYI=%d TAVAN=%d', mutant)
    if mutant == "MUT-ARTIK-SUSTURULDU":
        # 🔴 ARTIK olcusu IKI satirda gecer (ozet + detay). Yalniz birini
        # susturmak kolu KIRMIZI yakmazdi — mutant IKISINI birden susturur,
        # yoksa "ARTIK_AGAC" alt-dizesi detay satirinda YASAR ve kol kor kalir.
        metin = _mutasyon(metin, "ARTIK_AGAC=%d", "GIZLI_OLCU=%d", mutant)
        metin = _mutasyon(metin, "ARTIK_AGAC AGAC=%s", "GIZLI_OLCU AGAC=%s",
                          mutant)
    # 🔴🔴 IKI YONLU AYRIM ([[grep-sifir-nobetcisi-yasak-kaydinda-oludur]]):
    # "UYARI: WORKTREE TAVANI ASILDI" dizgesi bu dosyada IKI ROLDE gecer —
    #   (Y) YASAK  : uyariyi rapora BASAN satir (`satirlar.append(...)`)
    #   (A) ATIF   : uyarinin GERI GELMEDIGINI olcen NOBETCI satirlari
    #                (`if ... in p.stdout` / `_uyari_var` yardimcisi)
    # Tek yonlu `grep==0` nobetcisi (A)'yi da sayar ve SAHTE KIRMIZI verir —
    # ilk surumde tam bu oldu (3 bulgu, ucu de nobetciydi). Daha kotusu ters
    # yonde OLUR: biri nobetcileri silse "0 bulgu" YESIL yanardi.
    # Bu yuzden ayrim: (Y) SIFIR olmali, (A) TABANIN ALTINA DUSMEMELI.
    ATIF_TABANI = 3           # bugun olculdu: _uyari_var + 2 kendini-test kolu
    yasak = []
    atif = []
    for no, s in _kod_govdesi(metin):
        if "UYARI: WORKTREE TAVANI ASILDI" not in s:
            continue
        kayit = "%s:%d %s" % (os.path.basename(WORKTREE_NOBETI), no,
                              s.strip()[:90])
        if "satirlar.append" in s:
            yasak.append(kayit)       # uyariyi FIILEN BASAN satir
        else:
            atif.append(kayit)        # uyarinin yoklugunu OLCEN satir
    # 🔴 ARTIK olcusu de IKI ROLDE gecer: BASAN satir (`satirlar.append`) ve
    # onu ARAYAN nobetci (`if "ARTIK_AGAC=" not in p.stdout`). `in metin`
    # demek ikisini ayirt ETMEZ — nobetci satiri tek basina olcuyu "VAR"
    # gosterirdi ve susturma mutanti KOR kalirdi (olculdu).
    # 🔴 `satirlar.append` ile ayni SATIRDA olmasi SART DEGIL: cagri coklu
    # satira yayilir. Ayrim ROLDEN yapilir — nobetci satirlari raporun
    # CIKTISINI (`p.stdout`) ya da `hatalar` listesini anar; BASAN satir anmaz.
    # 🔴 Nobetci satirlari raporun CIKTISINI okur — degisken adi `p.stdout`
    # DA olabilir `w2.stdout` DA. Suzgec `.stdout` uzerinden kurulur; ada
    # bagli suzgec (`p.stdout`) W2/W3/W4 nobetcilerini "BASAN satir" sayip
    # susturma mutantini KOR birakiyordu (olculdu).
    artik = any("ARTIK_AGAC=" in s and ".stdout" not in s
                and "hatalar.append" not in s
                for _n, s in _kod_govdesi(metin))
    ozet = "WORKTREE SAYI=%d TAVAN=%d" in metin      # okuyucular kirilmadi
    for b in yasak[:8]:
        satirlar.append("    | 🔴 UYARIYI BASAN satir: %s" % b)
    for b in atif[:4]:
        satirlar.append("    | (nobetci) %s" % b)
    satirlar.insert(0,
                    "    | UYARIYI BASAN satir=%d (beklenen 0) · NOBETCI "
                    "atfi=%d (taban %d, ALTINA DUSMEMELI) · ARTIK_AGAC=%s · "
                    "ozet satiri KORUNDU=%s"
                    % (len(yasak), len(atif), ATIF_TABANI,
                       "VAR" if artik else "🔴 YOK",
                       "EVET" if ozet else "🔴 HAYIR"))
    return (not yasak and len(atif) >= ATIF_TABANI and artik
            and ozet), satirlar


# ------------------------------------------------------------------------------
# K7 — MENZIL: KURULU HER KOPYA yeni surumu aldi mi?
# ------------------------------------------------------------------------------
# 🔴🔴 [[onarim-kaynaga-yazildi-evlerde-canli-degil]] — 20 Agu'da onarim
# KAYNAGA yazildi, 4/4 ev KILITLI kaldi cunku evlerdeki KOPYALAR eskiydi.
# Bu kapi evlere `<ev>/.claude/parti-kapisi.py` olarak KOPYALANIR ve `isci.sh`
# AYRICA main checkout'taki kanonik kopyayi cagirir. Kaynagi duzeltmek CANLI
# davranisi DEGISTIRMEZ; bu kol her kopyayi ADIYLA sayar.
# Kol BLOKLAYICI DEGILDIR — bulgu RAPOR'dur; merge/dagitim hukmu mimardadir.
KURULU_KOPYALAR = [
    "/Users/okan/dev/pruvo/tools/parti-kapisi.py",          # isci.sh'in cagirdigi
    "/Users/okan/dev/pruvo-hasat/.claude/parti-kapisi.py",
    "/Users/okan/dev/pruvo-bot/.claude/parti-kapisi.py",
    "/Users/okan/dev/pruvo-jenerator/.claude/parti-kapisi.py",
    "/Users/okan/dev/pruvo-pazarlama/.claude/parti-kapisi.py",
    "/Users/okan/dev/pruvo-advisor/.claude/parti-kapisi.py",
]
# Yeni sozlesmenin makine-aranabilir IMZASI (dizge DEGIL, DAVRANIS capasi):
# reddetme yolu SILINDI ⇒ `_reddet(` YOK · hukum sozlugu RAPOR ⇒ jeton VAR.
YENI_SURUM_IMZASI = "HUKUM_RAPOR"
ESKI_SURUM_IMZASI = "def _reddet("


def k7_menzil(mutant=None):
    satirlar = []
    yeni, eski, yok = [], [], []
    for yol in KURULU_KOPYALAR:
        metin = _metin(yol)
        if metin is None:
            yok.append(yol)
            satirlar.append("    | YOK      %s" % yol)
            continue
        if YENI_SURUM_IMZASI in metin and ESKI_SURUM_IMZASI not in metin:
            yeni.append(yol)
            isaret, sinif = "YENI", "reddetmez"
        else:
            eski.append(yol)
            isaret, sinif = "🔴 ESKI", "HALA REDDEDIYOR"
        satirlar.append("    | %-8s %s  (%s · %d bayt)"
                        % (isaret, yol, sinif, len(metin)))
    satirlar.insert(0,
                    "    | kurulu kopya=%d · YENI surum=%d · 🔴 ESKI surum=%d "
                    "· dosya YOK=%d"
                    % (len(KURULU_KOPYALAR), len(yeni), len(eski), len(yok)))
    satirlar.append("    | 🔴 HUKUM: bu kol RAPOR'dur, KIRMIZI YAKMAZ. Kaynak "
                    "dalda duzeldi; CANLI olmasi merge + "
                    "`mimar-kapi-kur.py --parti-kapisi --uygula` ister "
                    "(mimar kapisi).")
    # Bilerek DAIMA GECER: menzil bir OLCUM kolu, bir kapi DEGIL. Kaldirma
    # isinin kendisi bir kapi kurmamalidir ([[kapi-supurmesi-29agu]]).
    return True, satirlar


KOLLAR = [
    ("K1", "N2B --kanca: hicbir cagri REDDEDILMEZ, teshis KORUNUR", k1_kanca),
    ("K2", "N2B --isci-kapi: rc=0, teshis KORUNUR", k2_isci_kapi),
    ("K3", "MUAF_ETIKET_ONEKLERI kacis yolu SILINDI (ikinci kopya yok)",
     k3_kacis_yolu),
    ("K4", "Claude iscisi KraL+MaCiT'te kosulsuz RED etmiyor", k4_claude_isci),
    ("K5", "asilma kesicisi KALDI · tur/dilim ZORLAMASI YOK", k5_tur_tavani),
    ("K6", "worktree SAYI ekseni yok · ARTIK olcusu RAPOR", k6_worktree),
    ("K7", "MENZIL — kurulu her kopya (RAPOR, bloklamaz)", k7_menzil),
]

# Mutant -> hangi kolun KIRMIZI yanmasi beklenir.
# 🔴 HER KALEM ICIN EN AZ 1 MUTANT (spec kabul §3), ve her mutant IKI
# oldurme yolundan birini temsil eder: (a) reddetme yolu GERI KONUR,
# (b) teshis SUSTURULUR. Ikisi de vakayi KIRMIZI yakmalidir.
MUTANT_HEDEFI = {
    # KALEM 1 — N2B parti kapisi (izole kopyada)
    "MUT-DENY-GERI": "K1",              # (a) kanca yine `deny` basar
    "MUT-SESSIZ": "K1",                 # (b) hukum satiri susturulur
    "MUT-RC-GERI": "K2",                # (a) isci-kapi yine sifir-disi rc
    "MUT-KACIS-GERI": "K3",             # (a) muafiyet listesi geri konur
    # KALEM 2/3/4 — isci.sh duzlemi (metin uzerinde, dosyaya YAZILMADAN)
    "MUT-CLAUDE-RED-GERI": "K4",
    "MUT-ASILMA-KESICI-SILINDI": "K5",   # (b) ASILMA korumasi susturulur
    "MUT-TUR-ZORLAMASI-GERI": "K5",      # (a) tur kesmesi geri konur
    "MUT-WORKTREE-SAYI-GERI": "K6",      # (a) sayi uyarisi geri konur
    "MUT-ARTIK-SUSTURULDU": "K6",        # (b) ARTIK olcusu susturulur
}


def kos(mutant=None, sadece=None):
    print("=" * 78)
    print("TIKAYICI KALDIRMA — KABUL BATARYASI%s"
          % ("   MUTANT=%s" % mutant if mutant else ""))
    print("=" * 78)
    kirmizi = []
    olculemedi = []
    for ad, baslik, fn in KOLLAR:
        if sadece and ad != sadece:
            continue
        ok, satirlar = fn(mutant=mutant)
        hal = "GECTI" if ok else ("OLCULEMEDI" if ok is None else "KUSUR")
        print("KOL %s %s: %s" % (ad, baslik, hal))
        for s in satirlar:
            print(s)
        if ok is None:
            olculemedi.append(ad)
        elif not ok:
            kirmizi.append(ad)
    print("")
    print("KIRMIZI=%s · OLCULEMEDI=%s · KOL SAYISI=%d"
          % (",".join(kirmizi) or "-", ",".join(olculemedi) or "-",
             len(KOLLAR) if not sadece else 1))
    return kirmizi, olculemedi


def mutant_bataryasi():
    """Her mutant HEDEF kolunu KIRMIZI yakmali. Yakmayan mutant = kor kol."""
    print("=" * 78)
    print("MUTANT BATARYASI — her mutant hedef kolunu KIRMIZI yakmali")
    print("=" * 78)
    gecen = 0
    kor = []
    for mut, hedef in sorted(MUTANT_HEDEFI.items()):
        fn = dict((a, f) for a, _b, f in KOLLAR)[hedef]
        ok, _s = fn(mutant=mut)
        yandi = (ok is False)
        print("  MUTANT %-28s hedef=%s  ->  %s"
              % (mut, hedef, "KIRMIZI (dogru)" if yandi
                 else "YANMADI (KOR KOL!)"))
        if yandi:
            gecen += 1
        else:
            kor.append(mut)
    print("")
    print("MUTANT=%d/%d  KOR=%s" % (gecen, len(MUTANT_HEDEFI),
                                    ",".join(kor) or "-"))
    return kor




# ==============================================================================
# DILIM 2 — MIMAR KAPILARI KALEMLERI (dal branch surumunden; 52 VAKA)
# ==============================================================================
def kaydet(ad, gecti, olculen, beklenen, not_=""):
    sonuclar.append((ad, gecti, str(olculen), str(beklenen), not_))


# ---------------------------------------------------------------------------
# IZOLE KOPYA + CAPA DOGRULAMALI MUTASYON
# ---------------------------------------------------------------------------
def izole_kopya():
    """tools/*.py'yi gecici bir dizine kopyalar; (dizin, tools_yolu) doner.

    Yalniz .py kopyalanir: kapilar birbirini ADLA import eder (mimar_kimlik,
    serbest_cagrilar), veri dosyalarina ihtiyac YOKTUR ve tam kopya yavas olurdu.
    """
    d = tempfile.mkdtemp(prefix="tikayici-kabul-")
    ht = os.path.join(d, "tools")
    os.makedirs(ht)
    for ad in os.listdir(TOOLS):
        if ad.endswith(".py"):
            shutil.copy2(os.path.join(TOOLS, ad), os.path.join(ht, ad))
    return d, ht


def yama(tools_yolu, dosya, capa, yerine, etiket):
    """Izole kopyada `capa` -> `yerine`. CAPA YOKSA (None, sebep) doner.

    Donus: (True, "") uygulandi · (False, sebep) uygulanmadi.
    """
    yol = os.path.join(tools_yolu, dosya)
    try:
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
    except OSError as e:
        return False, "kopya okunamadi: %s" % e
    if capa not in metin:
        return False, "CAPA_YOK (%s icinde bulunamadi) etiket=%s" % (dosya, etiket)
    sayi = metin.count(capa)
    metin = metin.replace(capa, yerine)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return True, "capa x%d" % sayi


# ---------------------------------------------------------------------------
# KAPI CAGRISI (PreToolUse)
# ---------------------------------------------------------------------------
def kapiya_ver(kapi_yolu, girdi):
    p = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(girdi),
                       capture_output=True, text=True)
    s = (p.stdout or "").strip()
    karar = None
    if s:
        try:
            karar = (json.loads(s).get("hookSpecificOutput") or {}).get(
                "permissionDecision")
        except Exception:
            karar = "COZULEMEDI"
    return ("RED" if karar == "deny" else "GECER"), p.stderr, p.returncode


def bash_girdi(komut, damga=ANA_DAMGA):
    return {"tool_name": "Bash", "tool_input": {"command": komut},
            "cwd": KOK, "transcript_path": damga, "session_id": "kabul-bataryasi"}


def yaz_girdi(yol, damga=ANA_DAMGA):
    return {"tool_name": "Write", "tool_input": {"file_path": yol, "content": "x\n"},
            "cwd": KOK, "transcript_path": damga, "session_id": "kabul-bataryasi"}


# ===========================================================================
# KALEM 1 — MIMAR ICRA KAPISI
# ===========================================================================
K1_OLCUM_CAPA = """        if ad in OLCUM_KOMUTLARI:
            iz_bas("OLCUM-SERBEST rol=" + ("CIP" if cip else "ANA") +
                   " sinif=OLCUM/TARAMA komut=" + ad)"""

K1_RED_GERI = """        if ad in OLCUM_KOMUTLARI and not cip:
            reddet("olcum / dosya-tarama komutu (" + ad + ").")"""

K1_TESHIS_SUSTU = """        if ad in OLCUM_KOMUTLARI:
            pass"""


def kalem1(tools_yolu, etiket):
    """(sed GECER mi, teshis VAR mi)"""
    kapi = os.path.join(tools_yolu, "mimar-icra-kapisi.py")
    karar, err, rc = kapiya_ver(kapi, bash_girdi("sed -n '1,5p' DEVAM.md"))
    teshis = "OLCUM-SERBEST" in err and "rol=ANA" in err and "komut=sed" in err
    return karar, teshis, rc


def kalem1_kos():
    # --- TABAN: canli govde (yamasiz) ---
    karar, teshis, rc = kalem1(TOOLS, "TABAN")
    kaydet("K1 TABAN  sed ANA -> GECER", karar == "GECER" and rc == 0, karar, "GECER")
    kaydet("K1 TABAN  teshis stderr'de (rol+sinif+komut)", teshis, teshis, True)

    # --- KONTROL: izole kopya yamasiz da YESIL olmali ---
    d, ht = izole_kopya()
    try:
        karar, teshis, rc = kalem1(ht, "KONTROL")
        kaydet("K1 KONTROL izole kopya yamasiz -> GECER",
               karar == "GECER" and teshis, karar, "GECER")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 1a: REDDETME YOLU GERI KONUR -> vaka KIRMIZI olmali ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-icra-kapisi.py", K1_OLCUM_CAPA, K1_RED_GERI,
                        "K1_RED_GERI")
        if not ok:
            kaydet("K1 MUTANT M1a RED-GERI", False, notu, "capa uygulanmali")
        else:
            karar, _t, _rc = kalem1(ht, "M1a")
            kaydet("K1 MUTANT M1a RED-GERI -> vaka KIRMIZI", karar == "RED",
                   karar, "RED", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 1b: TESHIS SUSTURULUR -> vaka KIRMIZI olmali ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-icra-kapisi.py", K1_OLCUM_CAPA, K1_TESHIS_SUSTU,
                        "K1_TESHIS_SUSTU")
        if not ok:
            kaydet("K1 MUTANT M1b TESHIS-SUSTU", False, notu, "capa uygulanmali")
        else:
            karar, teshis, _rc = kalem1(ht, "M1b")
            # Karar GECER kalir ama TESHIS KAYBOLUR -> vaka KIRMIZI.
            kaydet("K1 MUTANT M1b TESHIS-SUSTU -> teshis vakasi KIRMIZI",
                   teshis is False, "teshis=%s" % teshis, "teshis=False", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- KAPSAM: acilmamasi gerekenler AYNEN RED ---
    for ad, komut in (("python3 -c satir-ici kod", "python3 -c 'import os'"),
                      ("repo DISI betik", "python3 /private/tmp/x/kotu.py"),
                      ("curl (emirde anilmadi)", "curl -s https://pruvo3d.com")):
        karar, _e, _rc = kapiya_ver(os.path.join(TOOLS, "mimar-icra-kapisi.py"),
                                    bash_girdi(komut))
        kaydet("K1 KAPSAM  %s -> RED KALIR" % ad, karar == "RED", karar, "RED")


# ===========================================================================
# KALEM 2 — MIMAR KOD-KILIDI
# ===========================================================================
K2_CAPA = """if fp.lower().endswith(ICRA_UZANTILARI):
    _kod_yazimi_kaydet(girdi, fp)
    iz_bas("MIMAR-KOD-YAZDI " + fp)
    sys.exit(0)"""

K2_RED_GERI = """if fp.lower().endswith(ICRA_UZANTILARI):
    reddet("MIMAR KOD-KILIDI — CALISTIRILABILIR BETIK YAZARLIGI YASAK.")"""

K2_SAYAC_SUSTU = """if fp.lower().endswith(ICRA_UZANTILARI):
    iz_bas("MIMAR-KOD-YAZDI " + fp)
    sys.exit(0)"""

K2_PY = "/private/tmp/claude-501/x/scratchpad/kabul-olcum.py"


def kalem2_yaz(tools_yolu, oturum):
    kapi = os.path.join(tools_yolu, "mimar-kod-kilidi.py")
    g = yaz_girdi(K2_PY)
    g["session_id"] = oturum
    return kapiya_ver(kapi, g)


def kalem2_rapor(tools_yolu, oturum):
    kapi = os.path.join(tools_yolu, "mimar-kod-kilidi.py")
    p = subprocess.run([sys.executable, kapi, "--rapor", "--oturum", oturum,
                        "--temizle"], capture_output=True, text=True)
    for satir in (p.stdout or "").splitlines():
        if satir.startswith("MIMAR_KOD_YAZDI="):
            try:
                return int(satir.split("=", 1)[1].split()[0])
            except (ValueError, IndexError):
                return None
    return None


def kalem2_kos():
    # --- TABAN ---
    karar, err, rc = kalem2_yaz(TOOLS, "kabul-taban")
    kaydet("K2 TABAN  scratchpad .py -> GECER", karar == "GECER" and rc == 0,
           karar, "GECER")
    kaydet("K2 TABAN  teshis MIMAR-KOD-YAZDI stderr'de", "MIMAR-KOD-YAZDI" in err,
           "MIMAR-KOD-YAZDI" in err, True)
    n = kalem2_rapor(TOOLS, "kabul-taban")
    kaydet("K2 TABAN  MIMAR_KOD_YAZDI=1 dosya", n == 1, n, 1)

    # --- KONTROL ---
    d, ht = izole_kopya()
    try:
        karar, err, _rc = kalem2_yaz(ht, "kabul-kontrol")
        kalem2_rapor(ht, "kabul-kontrol")
        kaydet("K2 KONTROL izole kopya yamasiz -> GECER", karar == "GECER",
               karar, "GECER")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 2a: REDDETME GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-kod-kilidi.py", K2_CAPA, K2_RED_GERI, "K2_RED_GERI")
        if not ok:
            kaydet("K2 MUTANT M2a RED-GERI", False, notu, "capa uygulanmali")
        else:
            karar, _e, _rc = kalem2_yaz(ht, "kabul-m2a")
            kaydet("K2 MUTANT M2a RED-GERI -> vaka KIRMIZI", karar == "RED",
                   karar, "RED", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 2b: SAYAC SUSTURULUR (gorunurluk olur) ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "mimar-kod-kilidi.py", K2_CAPA, K2_SAYAC_SUSTU,
                        "K2_SAYAC_SUSTU")
        if not ok:
            kaydet("K2 MUTANT M2b SAYAC-SUSTU", False, notu, "capa uygulanmali")
        else:
            kalem2_yaz(ht, "kabul-m2b")
            n = kalem2_rapor(ht, "kabul-m2b")
            kaydet("K2 MUTANT M2b SAYAC-SUSTU -> MIMAR_KOD_YAZDI=0 (vaka KIRMIZI)",
                   n == 0, n, 0, notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- NOBETCILER: AYNEN RED ---
    # 🔴 CAPA ANA CHECKOUT'TUR, `KOK` DEGIL — OLCULDU (11 Eyl, bu batarya kendi
    # kusurunu yakaladi): vakalari `os.path.join(KOK, ...)` ile yazdigimda DORDU
    # GECER dondu. Sebep REGRESYON DEGIL, YANLIS CAPA: kilidin 2. adimi
    # (`worktree_ici`) worktree yollarini ZATEN muaf tutar ve bu davranis 20 Tem'den
    # beri BOYLE ("worktree kopyalari serbesttir" — kaynaktaki vaka 72). Kilit
    # yalnizca ANA CHECKOUT yollarini korur (`REPO_ONEKI` suzgeci, adim 6), o yuzden
    # nobetci vakasi ORAYA nisanlanir ([[spec-mutlak-yol-yanlis-agaci-olcer]] sinifi).
    ANA = "/Users/okan/dev/pruvo/"
    kapi = os.path.join(TOOLS, "mimar-kod-kilidi.py")
    for ad, yol in (
            ("urunler.json", ANA + "urunler.json"),
            (".urun-kaynaklari.json", ANA + ".urun-kaynaklari.json"),
            ("CEKIRDEK urunler-guard.py", ANA + "tools/urunler-guard.py"),
            ("kapi ADI kalkani", ANA + "baska/mimar-icra-kapisi.py"),
            ("index.html", ANA + "index.html"),
            ("settings.json", ANA + ".claude/settings.json")):
        karar, _e, _rc = kapiya_ver(kapi, yaz_girdi(yol))
        kaydet("K2 NOBETCI %s -> RED KALIR" % ad, karar == "RED", karar, "RED")

    # --- WORKTREE MUAFIYETI: OLCULUR, KAZA OLMAZ ---
    # Bu muafiyet ONCEDEN VARDI ve bu is onu DEGISTIRMEDI. Vaka olarak yazilir ki
    # bir gun sessizce kapanirsa (ya da yanlislikla ANA checkout'a genislerse)
    # batarya ADIYLA yansin.
    karar, _e, _rc = kapiya_ver(kapi, yaz_girdi(os.path.join(KOK, "urunler.json")))
    kaydet("K2 MUAFIYET worktree urunler.json -> GECER (onceden de boyleydi)",
           karar == "GECER", karar, "GECER")


# ===========================================================================
# KALEM 3 — KOMUT STILI KAPISI
# ===========================================================================
K3_CAPA = "bulunan = [ad for desen, ad, sinif in YASAK if re.search(desen, TARAMA[sinif])]"
K3_TIRNAK_KOR = "bulunan = [ad for desen, ad, sinif in YASAK if re.search(desen, komut)]"
K3_RED_CAPA = """if bulunan:
    sys.stderr.write("""
K3_RED_GERI = """if bulunan:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": "KOMUT STILI KAPISI: " + ", ".join(bulunan)}},
        ensure_ascii=False))
    sys.exit(0)
if bulunan:
    sys.stderr.write("""

K3_METIN = 'git commit -m "kutu 250 -> 500 oldu"'
K3_GERCEK = "python3 tools/durum.py > /tmp/x.txt"
K3_DOLAR = 'echo "x=$?"'


def k3(tools_yolu, komut):
    kapi = os.path.join(tools_yolu, "komut-stili-kapisi.py")
    karar, err, rc = kapiya_ver(kapi, bash_girdi(komut))
    return karar, ("KOMUT STILI UYARISI" in err), rc


def kalem3_kos():
    # --- TABAN ---
    karar, uyari, rc = k3(TOOLS, K3_METIN)
    kaydet("K3 TABAN  metin ici '->' -> GECER, UYARI YOK",
           karar == "GECER" and not uyari and rc == 0,
           "%s/uyari=%s" % (karar, uyari), "GECER/uyari=False")
    karar, uyari, _rc = k3(TOOLS, K3_GERCEK)
    kaydet("K3 TABAN  GERCEK yonlendirme -> GECER ama UYARI VAR",
           karar == "GECER" and uyari, "%s/uyari=%s" % (karar, uyari),
           "GECER/uyari=True")
    karar, uyari, _rc = k3(TOOLS, K3_DOLAR)
    kaydet("K3 TABAN  cift tirnakta $ GENISLER -> GECER + UYARI (POSIX)",
           karar == "GECER" and uyari, "%s/uyari=%s" % (karar, uyari),
           "GECER/uyari=True")
    karar, uyari, _rc = k3(TOOLS, "ls /Users/okan/dev/pruvo")
    kaydet("K3 TABAN  duz komut -> GECER, UYARI YOK",
           karar == "GECER" and not uyari, "%s/uyari=%s" % (karar, uyari),
           "GECER/uyari=False")

    # --- TIRNAK MASKELEME KENAR VAKALARI ---
    # 🔴 Maskeleme bir AYRISTIRICIDIR; ayristiricilarin arizasi kenarlarda dogar.
    # Her vaka POSIX kabuk semantigine gore YAZILDI, tahmine gore DEGIL.
    for komut, uyari_bekle, not_ in (
            # tek tirnak: `$` GENISLEMEZ -> uyari YOK
            ("echo 'fiyat $HOME degil metin'", False, "tek tirnakta $ literal"),
            # cift tirnak: `$` GENISLER -> uyari VAR
            ('echo "ev $HOME"', True, "cift tirnakta $ genisler"),
            # kacisli $ : genislemez -> uyari YOK
            ('echo "fiyat \\$500"', False, "kacisli \\$ genislemez"),
            # tek tirnak icinde `>` : literal -> uyari YOK
            ("git commit -m 'A > B tasindi'", False, "tek tirnakta > literal"),
            # cift tirnak icinde `>` : literal -> uyari YOK
            ('git commit -m "A > B tasindi"', False, "cift tirnakta > literal"),
            # tirnak DISINDA gercek yonlendirme -> uyari VAR
            ("ls > /tmp/x.txt", True, "tirnak disi gercek yonlendirme"),
            # KAPANMAMIS tirnak: kalan kisim metin sayilir (fail-safe) -> uyari YOK
            ('echo "kapanmamis > metin', False, "kapanmamis tirnak fail-safe"),
            # tirnakli metinden SONRA gercek yonlendirme -> uyari VAR
            ('echo "metin > degil" > /tmp/x.txt', True, "metin sonrasi gercek >"),
    ):
        karar, uyari, _rc = k3(TOOLS, komut)
        kaydet("K3 TIRNAK  %s" % not_,
               karar == "GECER" and uyari == uyari_bekle,
               "%s/uyari=%s" % (karar, uyari),
               "GECER/uyari=%s" % uyari_bekle)

    # --- KONTROL ---
    d, ht = izole_kopya()
    try:
        karar, uyari, _rc = k3(ht, K3_METIN)
        kaydet("K3 KONTROL izole kopya yamasiz -> GECER/uyari=False",
               karar == "GECER" and not uyari, "%s/uyari=%s" % (karar, uyari),
               "GECER/uyari=False")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 3a: REDDETME GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "komut-stili-kapisi.py", K3_RED_CAPA, K3_RED_GERI,
                        "K3_RED_GERI")
        if not ok:
            kaydet("K3 MUTANT M3a RED-GERI", False, notu, "capa uygulanmali")
        else:
            karar, _u, _rc = k3(ht, K3_GERCEK)
            kaydet("K3 MUTANT M3a RED-GERI -> vaka KIRMIZI", karar == "RED",
                   karar, "RED", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 3b: TIRNAK DUYARLILIGI KOR EDILIR ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "komut-stili-kapisi.py", K3_CAPA, K3_TIRNAK_KOR,
                        "K3_TIRNAK_KOR")
        if not ok:
            kaydet("K3 MUTANT M3b TIRNAK-KOR", False, notu, "capa uygulanmali")
        else:
            karar, uyari, _rc = k3(ht, K3_METIN)
            kaydet("K3 MUTANT M3b TIRNAK-KOR -> metin vakasi UYARI URETIR (KIRMIZI)",
                   uyari is True, "uyari=%s" % uyari, "uyari=True", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# KALEM 4 — DEFTER / KUTU / HAFIZA KOTASI
# ===========================================================================
def modul_yukle(ad, yol):
    import importlib.util
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def k4_taban_olc(tools_yolu):
    """(TAVAN_SATIR, kutu VARSAYILAN_TAVAN, hafiza SATIR, bayt_hukum)"""
    t = modul_yukle("k4_taban_%d" % abs(hash(tools_yolu)),
                    os.path.join(tools_yolu, "defter-kota-taban.py"))
    ka = modul_yukle("k4_kutu_%d" % abs(hash(tools_yolu)),
                     os.path.join(tools_yolu, "kutu-arsivle.py"))
    ha = modul_yukle("k4_haf_%d" % abs(hash(tools_yolu)),
                     os.path.join(tools_yolu, "hafiza-indeks-arsivle.py"))
    return t, ka, ha


def kalem4_kos():
    t, ka, ha = k4_taban_olc(TOOLS)

    # --- TABAN: SAYILAR ---
    kaydet("K4 TABAN  DEVAM.md TAVAN_SATIR=500", t.TAVAN_SATIR == 500,
           t.TAVAN_SATIR, 500)
    kaydet("K4 TABAN  kutu VARSAYILAN_TAVAN=500", ka.VARSAYILAN_TAVAN == 500,
           ka.VARSAYILAN_TAVAN, 500)
    kaydet("K4 TABAN  hafiza VARSAYILAN_TAVAN_SATIR=500",
           ha.VARSAYILAN_TAVAN_SATIR == 500, ha.VARSAYILAN_TAVAN_SATIR, 500)

    # --- TABAN: BAYT EKSENI HUKUM VERMEZ ---
    kaydet("K4 TABAN  BAYT_HUKUM_VERIR=False", t.BAYT_HUKUM_VERIR is False,
           t.BAYT_HUKUM_VERIR, False)
    asi, eksen, _s, _b = t.tavan_asi_mi(100, t.TAVAN_BAYT + 5000)
    kaydet("K4 TABAN  satir ALTINDA + bayt USTUNDE -> ASMADI, eksen BAYT_RAPOR",
           asi is False and eksen == "BAYT_RAPOR", "asi=%s eksen=%s" % (asi, eksen),
           "asi=False eksen=BAYT_RAPOR")
    asi, eksen, _s, _b = t.tavan_asi_mi(t.TAVAN_SATIR + 1, 100)
    kaydet("K4 TABAN  satir USTUNDE -> ASTI, eksen SATIR (kapi HALA durdurur)",
           asi is True and eksen == "SATIR", "asi=%s eksen=%s" % (asi, eksen),
           "asi=True eksen=SATIR")

    # --- TABAN: HAFIZA ekseni de bayta HUKUM VERMEZ ---
    dk = modul_yukle("k4_kapi", os.path.join(TOOLS, "defter-kota-kapisi.py"))
    hal = dk.hafiza_hali(True, True, True, 100, 99999, 500, 16384)
    kaydet("K4 TABAN  hafiza: bayt USTUNDE + satir ALTINDA -> HAFIZA_YESIL",
           hal == dk.HAFIZA_YESIL, hal, dk.HAFIZA_YESIL)
    hal = dk.hafiza_hali(True, True, True, 501, 100, 500, 16384)
    kaydet("K4 TABAN  hafiza: satir USTUNDE -> HAFIZA_ASILDI",
           hal == dk.HAFIZA_ASILDI, hal, dk.HAFIZA_ASILDI)

    # --- TABAN: KORUMALI iki yonlu esleme ---
    satirlar = [
        "## 2026-09-10 — BaBa (KORUMALI: BaBa kapatir) **A**", "govde",
        "## 2026-09-10 — BaBa (bilgi, KORUMALI değil) **B**", "govde",
        "## 2026-09-10 — BaBa (KORUMALI DEGIL) **C**", "govde",
        "## 2026-09-10 — BaBa (duz baslik) **D**", "govde KORUMALI kelimesi",
    ]
    baslar = ka.blok_baslari(satirlar)
    bulgu, govde, dustu, olumsuz = ka.korumali_etiketli_bloklar(satirlar, baslar)
    kaydet("K4 TABAN  KORUMALI veto=1 (yalniz gercek etiket)", len(bulgu) == 1,
           len(bulgu), 1)
    kaydet("K4 TABAN  ETIKET_OLUMSUZ=2 ('değil' + 'DEGIL', TR-guvenli)",
           len(olumsuz) == 2, len(olumsuz), 2)
    kaydet("K4 TABAN  govde anmasi=1 (BASLIKTA degil -> veto YOK)", govde == 1,
           govde, 1)
    kaydet("K4 TABAN  etiket_olumsuzlandi_mi('... KORUMALI değil)') True",
           ka.etiket_olumsuzlandi_mi("x (bilgi, KORUMALI değil) y") is True,
           True, True)
    kaydet("K4 TABAN  NON-GROWTH: duz 'KORUMALI:' etiketi olumsuz SAYILMAZ",
           ka.etiket_olumsuzlandi_mi("x (KORUMALI: BaBa kapatir) y") is False,
           False, False)

    # --- MUTANT 4a: BAYT HUKMU GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "defter-kota-taban.py", "BAYT_HUKUM_VERIR = False",
                        "BAYT_HUKUM_VERIR = True", "K4_BAYT_HUKUM_GERI")
        if not ok:
            kaydet("K4 MUTANT M4a BAYT-HUKUM-GERI", False, notu, "capa uygulanmali")
        else:
            tm = modul_yukle("k4_m4a", os.path.join(ht, "defter-kota-taban.py"))
            asi, eksen, _s, _b = tm.tavan_asi_mi(100, tm.TAVAN_BAYT + 5000)
            kaydet("K4 MUTANT M4a BAYT-HUKUM-GERI -> bayt vakasi KIRMIZI (asi=True)",
                   asi is True and eksen == "BAYT", "asi=%s eksen=%s" % (asi, eksen),
                   "asi=True eksen=BAYT", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 4b: KUTU TAVANI 250'YE GERI ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "kutu-arsivle.py", "VARSAYILAN_TAVAN = 500",
                        "VARSAYILAN_TAVAN = 250", "K4_TAVAN_GERI")
        if not ok:
            kaydet("K4 MUTANT M4b TAVAN-GERI", False, notu, "capa uygulanmali")
        else:
            kam = modul_yukle("k4_m4b", os.path.join(ht, "kutu-arsivle.py"))
            hal = dk.kutu_hali(True, True, True, 293, kam.VARSAYILAN_TAVAN)
            kaydet("K4 MUTANT M4b TAVAN-GERI -> 293 satir KUTU_ASILDI (KIRMIZI)",
                   hal == dk.KUTU_ASILDI, hal, dk.KUTU_ASILDI, notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- MUTANT 4c: OLUMSUZLAMA KOLU KOR EDILIR ---
    d, ht = izole_kopya()
    try:
        ok, notu = yama(ht, "kutu-arsivle.py",
                        "    return bool(ETIKET_OLUMSUZ_DESENI.search(_tr_normalize(baslik)))",
                        "    return False", "K4_OLUMSUZ_KOR")
        if not ok:
            kaydet("K4 MUTANT M4c OLUMSUZ-KOR", False, notu, "capa uygulanmali")
        else:
            kam = modul_yukle("k4_m4c", os.path.join(ht, "kutu-arsivle.py"))
            b2, _g2, _d2, o2 = kam.korumali_etiketli_bloklar(satirlar, baslar)
            kaydet("K4 MUTANT M4c OLUMSUZ-KOR -> veto 1->3, ETIKET_OLUMSUZ=0 (KIRMIZI)",
                   len(b2) == 3 and len(o2) == 0,
                   "veto=%d olumsuz=%d" % (len(b2), len(o2)), "veto=3 olumsuz=0", notu)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ===========================================================================



# ==============================================================================
# BIRLESTIRILMIS MAIN — DILIM 1 KOL + DILIM 2 KALEM, AYRI AYRI BAS, OZET TOPLA
# ==============================================================================
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutant", default=None,
                    help="(DILIM 1) belirli bir mutant ile kos")
    ap.add_argument("--kol", default=None,
                    help="(DILIM 1) yalniz bu kolu kos")
    ap.add_argument("--mutant-bataryasi", action="store_true",
                    help="(DILIM 1) tum mutantlari hedef kolu KIRMIZI yakar mi")
    a = ap.parse_args(argv)

    # --- DILIM 1: ISCI HATTI KOLLARI (K1..K7) ---
    print("=" * 100)
    print("DILIM 1 — ISCI HATTI KOLLARI (main branch surumu)")
    print("=" * 100)
    kirmizi = []
    olculemedi = []
    for ad, baslik, fn in KOLLAR:
        if a.kol and ad != a.kol:
            continue
        ok, satirlar = fn(mutant=a.mutant)
        hal = "GECTI" if ok else ("OLCULEMEDI" if ok is None else "KUSUR")
        print("KOL %s %s: %s" % (ad, baslik, hal))
        for s in satirlar:
            print(s)
        if ok is None:
            olculemedi.append(ad)
        elif not ok:
            kirmizi.append(ad)
    kol_sayisi = len(KOLLAR)
    print("")
    print("D1 KIRMIZI=%s · OLCULEMEDI=%s · KOL SAYISI=%d"
          % (",".join(kirmizi) or "-", ",".join(olculemedi) or "-", kol_sayisi))

    # --- DILIM 2: MIMAR KAPILARI KALEMLERI (M1..M4) ---
    if a.mutant is None and not a.mutant_bataryasi and not a.kol:
        print("")
        print("=" * 100)
        print("DILIM 2 — MIMAR KAPILARI KALEMLERI (dal branch surumu)")
        print("=" * 100)
        print("KOK = " + KOK)
        print("=" * 100)
        kalem1_kos()
        kalem2_kos()
        kalem3_kos()
        kalem4_kos()
        gecen = sum(1 for s in sonuclar if s[1])
        for ad, gecti, olculen, beklenen, notu in sonuclar:
            print("%s  %-62s olculen=%-28s beklenen=%s%s"
                  % ("\u2705" if gecti else "\u274c", ad, olculen, beklenen,
                     ("  [" + notu + "]") if notu else ""))
        print("=" * 100)
        print("D2 VAKA %d/%d GECTI" % (gecen, len(sonuclar)))

    # --- OZET ---
    print("")
    print("=" * 100)
    print("BIRLESTIRME OZETI: A=%d KOL + B=%d VAKA = A+B=%d"
          % (kol_sayisi, len(sonuclar), kol_sayisi + len(sonuclar)))
    print("=" * 100)

    # Mutant kosumunda BEKLENEN hal KIRMIZI'dir.
    if a.mutant:
        return 0 if kirmizi else 1
    # Mutant bataryasi: kor kol varsa 1.
    if a.mutant_bataryasi:
        kor = mutant_bataryasi()
        return 1 if kor else 0
    return 1 if (kirmizi or olculemedi) else 0


if __name__ == "__main__":
    sys.exit(main())
