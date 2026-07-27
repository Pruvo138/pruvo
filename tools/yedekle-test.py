#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/yedekle.py'nin SKILL KAPSAMI + SIR NOBETI + ESZAMANLILIK KILIDI.

NEDEN VAR: ~/.claude/skills (merge-kapisi + ege-diyalog) GIT DISINDA, tek kopya bu makinede.
yedekle.py onu Drive'a tasiyan tek yol. Uc sessiz-hata sinifi var:
  (A) KAPSAM CURUMESI — skills bloku bozulur/silinir, arac YINE "bitti" der, disk kaybinda
      mutasyon-kanitli dal-olc.py + kabul-test.py topluca gider (kimse fark etmez).
  (B) SIR SIZINTISI — skills agaci vetted degil; oraya dusen bir jeton/anahtar yedek klasorune
      (paylasilabilir Drive) tasinir.
  (C) ESZAMANLI YAZMA — yedekle.py her push'ta kosuyor, bu repoda paralel oturum NORMAL;
      kilitsiz iki kosum AYNI hedefe yazar, sonda damga yine "tam" der. Pano "taze"
      derken yedek karismis olabilir (bolum 13-15).
Bu yuzden her iddianin KIRMIZI-MUTASYON ya da davranissal kaniti var: kontrolu devre disi
birakan mutant surumde ilgili kontrol KIRMIZI yanmalidir; yanmazsa kontrol olcmuyor demektir.

⚠️ GERCEK HEDEFE YAZILMAZ: 13-15 tamamen izole ortamda kosar (sahte HOME + sahte git
deposu + drive_yolu STUB'u). Bolum 15 gercek Drive damgasinin bayt bayt DEGISMEDIGINI
ayrica kanitlar.

Kosum:  python3 tools/yedekle-test.py
"""
import fcntl
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")

# Skill agacinda BULUNMASI zorunlu iki dosya (26 Tem'de mutasyon kanitiyla sertlestirildi).
ZORUNLU = ("merge-kapisi/scripts/dal-olc.py", "merge-kapisi/evals/kabul-test.py")

# Sentetik sir fikstur govdesi — GERCEK anahtar DEGIL, imza tanima testi icin.
#
# 🔴 E2 — FIKSTUR IKI PARCALI KURULUR (27 Tem). shop/test/kabul.js `test6SirTaramasi`
# tum repoda `git grep -nIE "BEGIN [A-Z ]*PRIVATE KEY"` kosar; bu SATIR BAZLI bir
# taramadir ve fikstur tek satirda tam bicimde yazilinca 1 isabet vererek shop kabul
# testini KIRMIZI tutuyordu. Cozum tarayiciyi ZAYIFLATMAK/muaf tutmak DEGIL (o zaman
# gercek bir anahtar da kacardi): dize IKI parcaya bolunur -> hicbir KAYNAK SATIRI
# desene uymaz, CALISMA ANINDAKI dize ise BIREBIR AYNI kalir (yedekle.SIR_IMZALARI
# "ozel anahtar blogu" imzasi ayni sekilde yakalar; 4. bolum bunu olcer).
_ANAHTAR_KUYRUK = " KEY-----"
SAHTE_ANAHTAR = ("-----BEGIN RSA PRIVATE" + _ANAHTAR_KUYRUK + "\n"
                 "SAHTE-FIKSTUR-VERISI-GERCEK-ANAHTAR-DEGIL\n"
                 "-----END RSA PRIVATE" + _ANAHTAR_KUYRUK + "\n")

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


def izole_ortam(td, yedekle, memory_adet=40, skills_adet=20):
    """GERCEK Drive'a/HOME'a DOKUNMAYAN tam izole kosum ortami.

    - kok   : sahte git deposu -> yedekle.py'nin ROOT'u (ve `.yedek.lock`) buraya duser
    - HOME  : sahte ev -> MEMORY + SKILLS expanduser ile buraya duser
    - hedef : td/drive/Pruvo/backup (drive_yolu STUB'u; gercek mount ASLA cozulmez)
    Beklenen repo dosyalari yedekle.REPO_BEKLENEN'den okunur (fikstur bayatlamasin)."""
    kok = os.path.join(td, "repo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(YEDEKLE, os.path.join(kok, "tools", "yedekle.py"))
    pruvo = os.path.join(td, "drive", "Pruvo")
    os.makedirs(pruvo)
    with open(os.path.join(kok, "tools", "drive_yolu.py"), "w") as f:
        f.write('DESEN = "/olmayan-mount/*/STL"\n'
                'def stl_dizini(sessiz=False):\n    return %r\n'
                'def pruvo_dizini(sessiz=False):\n    return %r\n'
                % (os.path.join(pruvo, "STL"), pruvo))
    subprocess.run(["git", "-C", kok, "init", "-q"], capture_output=True)
    for ad in yedekle.REPO_BEKLENEN:
        with open(os.path.join(kok, ad), "w") as f:
            f.write("izole test icerigi: %s\n" % ad)
    ev = os.path.join(td, "ev")
    mem = os.path.join(ev, ".claude", "projects", "-Users-okan-dev-pruvo", "memory")
    sk = os.path.join(ev, ".claude", "skills", "ornek-skill")
    os.makedirs(mem)
    os.makedirs(sk)
    for i in range(memory_adet):
        with open(os.path.join(mem, "not-%03d.md" % i), "w") as f:
            f.write("hafiza kaydi %d\n" % i)
    for i in range(skills_adet):
        with open(os.path.join(sk, "adim-%03d.md" % i), "w") as f:
            f.write("skill adimi %d\n" % i)
    ortam = dict(os.environ)
    ortam["HOME"] = ev
    return {"kok": kok, "betik": os.path.join(kok, "tools", "yedekle.py"),
            "ev": ev, "pruvo": pruvo, "hedef": os.path.join(pruvo, "backup"),
            "kilit": os.path.join(kok, yedekle.KILIT_ADI), "ortam": ortam,
            "memory_adet": memory_adet, "skills_adet": skills_adet}


def izole_kos(o, *bayraklar):
    return subprocess.run([sys.executable, o["betik"]] + list(bayraklar),
                          capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])


def izole_imza(o):
    """KUM HAVUZUNUN kendi kaynak imzasi — kum havuzunun KENDI yedekle.py'si ve sahte
    HOME'u ile olculur (gercek makinenin ~/.claude'u KARISMAZ). dict ya da None.
    Pano ucu testlerinde `durum._canli_kaynak_imzasi` yerine bu verilir; aksi halde
    pano gercek makineyi olcer ve kum havuzu damgasiyla karsilastirma anlamsiz olur."""
    r = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util,json;"
         "spec=importlib.util.spec_from_file_location('y', %r);"
         "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
         "print(json.dumps(m.kaynak_imzasi()))" % o["betik"]],
        capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])
    try:
        veri = json.loads(r.stdout.strip())
    except ValueError:
        return None
    return veri if isinstance(veri, dict) else None


def izole_baslat(o, *bayraklar):
    return subprocess.Popen([sys.executable, o["betik"]] + list(bayraklar),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            env=o["ortam"], cwd=o["kok"])


def hedef_dosyalari(hedef):
    if not os.path.isdir(hedef):
        return []
    return sorted(os.path.relpath(os.path.join(d, a), hedef)
                  for d, _alt, adlar in os.walk(hedef) for a in adlar)


def damga_json(hedef, ad=".son-yedek.json"):
    try:
        with open(os.path.join(hedef, ad), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def atlama_json(hedef):
    """Atlama kaydi AYRI dosyada (yazici sinifi ayri; bkz. yedekle.ATLAMA_ADI)."""
    return damga_json(hedef, ".son-yedek-atlama.json")


def birlesik_json(hedef):
    """Panonun gordugu birlesik gorunum: damga + atlama kaydi (durum.py ile ayni kural)."""
    d = dict(damga_json(hedef) or {})
    d.update({k: v for k, v in (atlama_json(hedef) or {}).items()
              if k.startswith("son_atlama")})
    return d


def _gercek_pruvo_dizini_saltokunur():
    """GERCEK Drive'daki .../Pruvo dizinini SALT-OKUNUR cozer (ya da None).

    🔴 NEDEN drive_yolu'nun KENDI cozuculeri CAGRILMAZ (27 Tem): ust sarmalayici
    STL cozucusune duser ve kayitli yol BAYATSA `.stl-backup-dir`i DUZELTIR —
    yani GERCEK REPOYA YAZAR (drive_yolu.ROOT sabit "/Users/okan/dev/pruvo",
    worktree'de bile ana checkout'u gosterir). Bir KABUL TESTININ gercek repoya
    yazmasi kabul edilemez: bu makinede kayitli yol bugun gecerli oldugu icin
    yazma tetiklenmiyordu, mount adi degistigi gun sessizce tetiklenecekti
    (hesap yeniden adlandirmasi bu depoda 15 Tem'de YASANDI).
    Burada yalniz OKUNUR: kayitli yol + drive_yolu.DESEN glob'u (durum.py'nin
    yedek_dizini() ile ayni salt-okunur deseni)."""
    adaylar = []
    try:
        sys.path.insert(0, TOOLS)
        import drive_yolu
        desen = drive_yolu.DESEN
        cfg = drive_yolu.CFG
    except Exception:
        return None
    try:
        if os.path.isfile(cfg):
            with open(cfg, "r", errors="replace") as f:
                kayitli = f.read().strip()
            if kayitli:
                adaylar.append(kayitli)
    except OSError:
        pass
    try:
        adaylar += sorted(glob.glob(desen))
    except OSError:
        pass
    for stl in adaylar:
        ust = os.path.dirname(stl.rstrip("/"))
        try:
            if os.path.isdir(ust):
                return ust
        except OSError:
            continue
    return None


def gercek_kritik_parmakizi(yedekle):
    """Test SONUNDA aynen durmasi gereken GERCEK dosyalarin bayt+mtime parmak izi.
    Doner: {etiket: (yol, (bayt, mtime) | None)}  — dosya yoksa deger None.

    Kapsam BILEREK iki dosya: (a) Drive'daki tazelik damgasi (testin hedefine
    yazmadiginin kaniti), (b) repo kokundeki `.stl-backup-dir` (drive_yolu'nun
    YAZDIGI tek dosya — E2/K5 onariminin nobetcisi)."""
    izler = {}
    pruvo = _gercek_pruvo_dizini_saltokunur()
    izler["damga"] = (os.path.join(pruvo, "backup", yedekle.DAMGA_ADI)
                      if pruvo else None, None)
    try:
        sys.path.insert(0, TOOLS)
        import drive_yolu
        izler[".stl-backup-dir"] = (drive_yolu.CFG, None)
    except Exception:
        izler[".stl-backup-dir"] = (None, None)
    for etiket, (yol, _x) in list(izler.items()):
        if not yol:
            continue
        try:
            with open(yol, "rb") as f:
                izler[etiket] = (yol, (f.read(), os.path.getmtime(yol)))
        except OSError:
            izler[etiket] = (yol, None)
    return izler


def main():
    yedekle = modul_yukle(YEDEKLE, "yedekle_gercek")
    izler_once = gercek_kritik_parmakizi(yedekle)

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
        # 🔴 E2 NOBETCISI: iki parcali kurulan fikstur, ICERIK IMZASI yoluyla
        # elenmeye DEVAM ediyor mu? (ad deseni degil — kurulum.md masum bir ad.)
        # Bu kontrol olmadan "fiksturu bol" onarimi imza tanimayi sessizce olduruyor
        # olabilirdi ve 4. bolum yine yesil yanardi (ad deseni yeterdi sanilirdi).
        kurulum_sebep = dict(h).get("ornek-skill/kurulum.md", "")
        kontrol("iki parcali fikstur ICERIK IMZASI ile elendi (ad deseniyle DEGIL)",
                "icerik imzasi" in kurulum_sebep and "ozel anahtar" in kurulum_sebep,
                kurulum_sebep)
        # (beklenen dizeler de PARCALI kurulur — bu satirlar taramaya yem olmasin)
        kontrol("calisma anindaki fikstur dizesi TAM bicimde (bolme sizdirmadi)",
                SAHTE_ANAHTAR.startswith("-----BEGIN RSA PRIVATE" + _ANAHTAR_KUYRUK + "\n")
                and SAHTE_ANAHTAR.rstrip().endswith("-----END RSA PRIVATE"
                                                    + _ANAHTAR_KUYRUK),
                repr(SAHTE_ANAHTAR[:34]))

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

    # ---------------- 9) TAZELIK DAMGASI + UCUZ MOD ----------------
    print("\n9) DAMGA + --gerekliyse — pano bunu okur, hook bunu kullanir")
    with tempfile.TemporaryDirectory() as td:
        kontrol("damga yoksa None (patlamaz)", yedekle.damga_oku(td) is None)
        yedekle.damga_yaz(td, {"memory": 5, "skills": 3, "repo": 2, "skills_haric": 0})
        d = yedekle.damga_oku(td)
        kontrol("damga yazilip okunuyor", isinstance(d, dict) and d.get("skills") == 3)
        kontrol("damgada zaman VAR", isinstance(d.get("zaman"), (int, float)))
        with open(os.path.join(td, yedekle.DAMGA_ADI), "w") as fh:
            fh.write("{bozuk")
        kontrol("bozuk damga None doner", yedekle.damga_oku(td) is None)
    # gerekli_mi: FAIL-OPEN — atlamak KANITA bagli, yedeklemek varsayilan
    kontrol("damga yok  -> YEDEKLE", yedekle.gerekli_mi(None, 100) is True)
    kontrol("damga bozuk-> YEDEKLE", yedekle.gerekli_mi({"zaman": "abc"}, 100) is True)
    kontrol("mtime olculemedi -> YEDEKLE", yedekle.gerekli_mi({"zaman": 100}, None) is True)
    kontrol("kaynak damgadan YENI -> YEDEKLE", yedekle.gerekli_mi({"zaman": 100}, 150) is True)
    kontrol("kaynak damgadan ESKI -> ATLA", yedekle.gerekli_mi({"zaman": 100}, 50) is False)
    kontrol("--gerekliyse gecerli bayrak", "--gerekliyse" in yedekle.BAYRAKLAR)
    kontrol("en_yeni_kaynak_mtime sayi donduruyor",
            isinstance(yedekle.en_yeni_kaynak_mtime(), float))

    # ---------------- 10) F1: KOK ANA AGACA COZULUYOR MU ----------------
    print("\n10) F1 SAHTE TAZELIK — kok WORKTREE'den de ANA agaci gostermeli")
    wt = os.path.abspath(os.path.join(TOOLS, ".."))    # bu betik bir worktree'de kosuyor olabilir
    ana = yedekle.ana_calisma_agaci(wt)
    # Bagimsiz ayirt edici: ANA agacta .git bir DIZIN, worktree'de bir DOSYA.
    kontrol("cozulen kok ANA agac (.git DIZIN)", os.path.isdir(os.path.join(ana, ".git")), ana)
    kontrol("modul ROOT'u da ANA agac", yedekle.ROOT == ana, yedekle.ROOT)
    eksik = yedekle.repo_eksikleri()
    kontrol("beklenen repo dosyalarinin HEPSI bulundu (kismi yedek YOK)", eksik == [],
            "eksik: %s" % (eksik or "-"))
    kontrol("_repo_dosyalari 4 dosya donduruyor", len(yedekle._repo_dosyalari(False)) == 4,
            str(len(yedekle._repo_dosyalari(False))))
    with tempfile.TemporaryDirectory() as td:
        mut = mutant_yaz(td, [("        if p.returncode == 0 and ortak:",
                               "        if False:  # MUTANT: git cozumu devre disi")])
        mmod = modul_yukle(mut, "yedekle_mutant_kok")
        kontrol("MUTANTTA kok WORKTREE'ye dusuyor (kontrol KIRMIZI yanardi)",
                mmod.ana_calisma_agaci(wt) == wt, mmod.ana_calisma_agaci(wt))

    # ---------------- 11) F1: KISMI YEDEK DAMGASI ----------------
    print("\n11) F1 — eksik dosya varsa TAM GUVEN damgasi ATILMAMALI")
    with tempfile.TemporaryDirectory() as td:
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 2},
                          eksik=[".urun-kaynaklari.json", "DEVAM-ARSIV.md"])
        d = yedekle.damga_oku(td)
        kontrol("damga tam=False", d.get("tam") is False)
        kontrol("eksik listesi damgada", d.get("eksik") == [".urun-kaynaklari.json",
                                                           "DEVAM-ARSIV.md"])
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 4}, eksik=[])
        kontrol("eksiksiz kosumda tam=True", yedekle.damga_oku(td).get("tam") is True)

    # ---------------- 12) F4: BUDANAN DIZIN RAPORLANIYOR MU ----------------
    print("\n12) F4 — budanan gurultu dizini SESSIZCE yutulmamali")
    with tempfile.TemporaryDirectory() as td:
        kok = os.path.join(td, "skills")
        fikstur_kur(kok)                                   # __pycache__/x.pyc iceriyor
        _d, _h, g = yedekle.skills_plani(kok=kok)
        kontrol("budanan dizin gurultu listesinde", any("__pycache__" in x for x in g),
                str(g))
        kontrol("dizin oldugu belirtiliyor", any("(dizin budandi)" in x for x in g))

    # ---------------- 13) KILIT: DETERMINISTIK KARSILIKLI DISLAMA ----------------
    print("\n13) KILIT — kilit BASKASINDAYKEN kosum ATLAR, damga YALAN SOYLEMEZ")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        kontrol("test hedefi gecici dizinde (gercek Drive DEGIL)",
                o["hedef"].startswith(td), o["hedef"])
        kilitci = open(o["kilit"], "a+")               # "kosan yedek" taklidi
        fcntl.flock(kilitci, fcntl.LOCK_EX)
        sahip_bas = time.time()
        kilitci.write(yedekle._sahip_imzasi(sahip_bas, pid=999999))
        kilitci.flush()
        r = izole_kos(o, "--gerekliyse")
        kontrol("kilit doluyken exit 0 (FAIL-OPEN: push bloklanmaz)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, r.stderr.strip()[:80]))
        kontrol("cikti 'yedek ATLANDI' diyor", "yedek ATLANDI" in r.stdout,
                r.stdout.strip().splitlines()[0] if r.stdout.strip() else "(bos)")
        kontrol("ATLANAN kosum HICBIR dosya kopyalamadi (yalniz atlama kaydi)",
                "bitti ->" not in r.stdout and hedef_dosyalari(o["hedef"]) ==
                [".son-yedek-atlama.json"], str(hedef_dosyalari(o["hedef"])))
        kontrol("ATLANAN kosum DAMGAYA hic dokunmadi (damga YOK)",
                damga_json(o["hedef"]) is None)
        d = atlama_json(o["hedef"]) or {}
        kontrol("atlama kaydinda TAM GUVEN alani YOK ('zaman' yok)", "zaman" not in d,
                str(sorted(d)))
        kontrol("atlama kaydi VAR", isinstance(d.get("son_atlama"), float))
        kontrol("atlama sebebi yazili", "baska yedek kosuyordu" in
                str(d.get("son_atlama_sebep")), str(d.get("son_atlama_sebep"))[:70])
        kontrol("kaynak degismemisken atlama KAPSANDI (pano bosuna uyarmaz)",
                d.get("son_atlama_kapsandi") is True, str(d.get("son_atlama_kapsandi")))
        kontrol("beklenen SAHIBIN baslangici TAM HASSAS kaydedildi",
                d.get("son_atlama_sahip_baslangici") == sahip_bas,
                "%r vs %r" % (d.get("son_atlama_sahip_baslangici"), sahip_bas))

        # 13a) KAPSANMAYAN atlama: kilit tutulurken kaynak DEGISIRSE uyari SART
        time.sleep(0.02)
        with open(os.path.join(o["ev"], ".claude", "projects",
                               "-Users-okan-dev-pruvo", "memory", "not-000.md"), "w") as fh:
            fh.write("kilit tutulurken YENI degisiklik\n")
        r3 = izole_kos(o, "--gerekliyse")
        d3 = atlama_json(o["hedef"]) or {}
        kontrol("kilit tutulurken degisen kaynak -> atlama KAPSANMADI",
                d3.get("son_atlama_kapsandi") is False, str(d3.get("son_atlama_kapsandi")))
        kontrol("kapsanmayan atlamada cikti UYARIYOR",
                "KAPSAMAYABILIR" in r3.stdout, r3.stdout.strip().splitlines()[-1][:80])
        kontrol("kapsanmayan atlamada da exit 0 (fail-open)", r3.returncode == 0)

        # kilit birakilinca ayni ortam NORMAL calismali (regresyon)
        fcntl.flock(kilitci, fcntl.LOCK_UN)
        kilitci.close()
        r2 = izole_kos(o)
        # +2: damga + (onceki atlamadan kalan) atlama kaydi
        bekle = o["memory_adet"] + o["skills_adet"] + len(yedekle.REPO_BEKLENEN) + 2
        gercek_dosya = hedef_dosyalari(o["hedef"])
        kontrol("kilit birakilinca yedek GERCEKTEN alindi (exit 0 + 'bitti ->')",
                r2.returncode == 0 and "bitti ->" in r2.stdout, "rc=%d" % r2.returncode)
        kontrol("hedefte beklenen dosya sayisi", len(gercek_dosya) == bekle,
                "%d/%d" % (len(gercek_dosya), bekle))
        d2 = damga_json(o["hedef"]) or {}
        kontrol("damga tam=True + sayilar dogru",
                d2.get("tam") is True and d2.get("memory") == o["memory_adet"]
                and d2.get("skills") == o["skills_adet"],
                "memory=%s skills=%s" % (d2.get("memory"), d2.get("skills")))
        kontrol("onceki ATLAMA kaydi KORUNDU (tamamlanan kosum onu silmez)",
                isinstance((atlama_json(o["hedef"]) or {}).get("son_atlama"), float))
        kontrol("gecici damga dosyasi kalmadi",
                not any(".tmp-" in x for x in gercek_dosya))

    # ---------------- 13e) IMZA HASSASIYETI (flake kaynagi) ----------------
    # Curutucu olcumu: imza `%.3f` ile yuvarlanirken karsilastirma tam hassas mtime
    # ile yapiliyordu -> 200 denemenin 94'u (%47) YANLIS karar; yedekle-test 16
    # kosumun 6'sinda kirmizi. Burada 2000 ornekte YANLIS KARAR 0 olmali.
    print("\n13e) IMZA HASSASIYETI — 2000 ornek, yanlis karar 0 (flake kapisi)")
    taban = time.time()
    sapmalar = (0.0, 1e-6, -1e-6, 1e-4, -1e-4)
    yanlis_yeni = yanlis_eski = tur_kaybi = 0
    for i in range(2000):
        t = taban + i * 0.000173                      # ms-alti kaymalari tarar
        coz = yedekle._imza_coz(yedekle._sahip_imzasi(t, pid=1))[1]
        if coz != t:
            tur_kaybi += 1
        eski_coz = yedekle._imza_coz("pid=1 baslangic=%.3f iso=x" % t)[1]  # ESKI bicim
        for s in sapmalar:
            dogru = yedekle.atlama_kapsandi_mi(t, t + s)
            if yedekle.atlama_kapsandi_mi(coz, t + s) is not dogru:
                yanlis_yeni += 1
            if yedekle.atlama_kapsandi_mi(eski_coz, t + s) is not dogru:
                yanlis_eski += 1
    kontrol("imza TAM tur-donusu yapiyor (float(repr(x)) == x)", tur_kaybi == 0,
            "%d/2000 kayip" % tur_kaybi)
    kontrol("2000 ornek x 5 sapma = 10000 kararda YANLIS 0", yanlis_yeni == 0,
            "yanlis=%d/10000" % yanlis_yeni)
    kontrol("ESKI %.3f bicimi AYNI fikstürde yaniliyordu (kontrol olcuyor)",
            yanlis_eski > 0, "eski bicim yanlis=%d/10000 (%.0f%%)"
            % (yanlis_eski, 100.0 * yanlis_eski / 10000))

    # ---------------- 13f) SAHIP ASILDI/OLDU -> PANO SUSMAMALI ----------------
    # Curutucu senaryosu: kaynak degisti -> SONRA bir yedek kilidi aldi (kapsandi=True)
    # -> sahip asildi/oldu, damgayi HIC yazmadi. Dosya yedekte YOK ama eski damga
    # "taze" gorunuyor. Pano UYARMAK ZORUNDA.
    print("\n13f) SAHIP BITIRMEDI — 'kapsandi' tek basina yeter mi? (pano ucu)")
    sys.path.insert(0, TOOLS)
    durum = modul_yukle(os.path.join(TOOLS, "durum.py"), "durum_kilit_kontrol")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        r0 = izole_kos(o)                              # 1) gercek bir yedek tamamlandi
        kontrol("hazirlik: ilk yedek tamamlandi", "bitti ->" in r0.stdout)
        d0 = damga_json(o["hedef"]) or {}
        taze_once = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
        kontrol("hazirlik: pano bu noktada TAZE", taze_once[0].strip().startswith("taze:"),
                taze_once[0])
        time.sleep(0.02)
        with open(os.path.join(o["ev"], ".claude", "projects",     # 2) KAYNAK DEGISTI
                               "-Users-okan-dev-pruvo", "memory", "not-001.md"), "w") as fh:
            fh.write("yedeklenmesi GEREKEN yeni icerik\n")
        time.sleep(0.02)
        asili = open(o["kilit"], "a+")                 # 3) sahip kilidi aldi ve ASILDI
        fcntl.flock(asili, fcntl.LOCK_EX)
        asili.truncate(0)
        asili.write(yedekle._sahip_imzasi(time.time(), pid=999999))
        asili.flush()
        r1 = izole_kos(o, "--gerekliyse")              # 4) push atladi
        d1 = birlesik_json(o["hedef"])
        sat = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
        print("     --- pano ciktisi (sahip bitirmedi) ---")
        for s in sat:
            print("    " + s)
        kontrol("atlama 'kapsandi' olctu (degisiklik sahipten ONCE)",
                d1.get("son_atlama_kapsandi") is True, str(d1.get("son_atlama_kapsandi")))
        kontrol("damganin `baslangic`i HALA ilk kosumun (sahip yazmadi)",
                d1.get("baslangic") == d0.get("baslangic"))
        kontrol("🔴 PANO SUSMUYOR: 'taze' DEMIYOR", not sat[0].strip().startswith("taze:"),
                sat[0])
        kontrol("pano sahibin bitirmedigini SOYLUYOR",
                "HIC YAZMADI" in sat[0] and "ATLANDI" in sat[0])
        kontrol("atlanan kosum yine exit 0 (fail-open bozulmadi)", r1.returncode == 0)
        # sahip serbest kalip GERCEKTEN kosunca uyari kendi kendine kapanmali
        fcntl.flock(asili, fcntl.LOCK_UN)
        asili.close()
        izole_kos(o)
        sat2 = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
        kontrol("gercek kosumdan sonra uyari KENDILIGINDEN kapandi",
                sat2[0].strip().startswith("taze:"), sat2[0])

    # ---------------- 13g) K1: ISTISNA YOLUNDA `bitti=` YAZILMAZ ----------------
    # 🔴 TUR-4'TE OLCULEN MERGE BLOKLAYICI KUSUR: main()'in `finally` blogu istisna
    # yolunda DA `bitti=` yaziyordu -> durum.kilit_durumu izi 'yok' sayiyor, pano
    # "YARIM KALMIS YEDEK" DEMIYOR, damga da eski kaldigi icin "taze" diyordu. Yani
    # kilidin EN SIK hata biciminde (kosum ortada cokuyor: disk dolu, Drive cevabi
    # kesiliyor, kill) dalin getirdigi nobetci OLUYDU ve hicbir test bunu civilemiyordu.
    # Asagisi GERCEK ICRA ile olcer: izole kopya kopyalama ORTASINDA istisna atar.
    print("\n13g) K1 — kosum ORTADA COKERSE iz `bitti=` TASIMAZ, pano 'yarim' der")
    # COKME NOKTASI: memory kopyalandiktan SONRA, skills kopyalanmadan ONCE ->
    # yedek GERCEKTEN yarim kalir (skills degisikligi hedefe HIC girmez).
    COKME_CAPA = "    yazilan = 0\n    if os.path.isdir(SKILLS):"
    COKME = ('    raise RuntimeError("TEST: kosum ortasinda cokme")\n'
             "    yazilan = 0\n    if os.path.isdir(SKILLS):")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        r0 = izole_kos(o)                              # 1) saglam kosum: damga olussun
        kontrol("13g hazirlik: ilk yedek tamamlandi", "bitti ->" in r0.stdout)
        iz0 = ""
        with open(o["kilit"], encoding="utf-8", errors="replace") as fh:
            iz0 = fh.read(256).strip()
        kontrol("13g: BASARILI kosumun izi `bitti=` TASIYOR (pozitif nobetci)",
                "bitti=" in iz0 and "hata=" not in iz0, iz0[-60:])
        kontrol("13g: basarili kosumdan sonra kilit hali 'yok' (pano SESSIZ)",
                durum.kilit_durumu(o["kok"])["hal"] == "yok"
                and durum.kilit_satirlari(durum.kilit_durumu(o["kok"])) == [],
                durum.kilit_durumu(o["kok"])["hal"])

        # 2) KAYNAK DEGISTI ve kosum ORTADA PATLADI -> gercek veri kaybi
        time.sleep(0.02)
        sk = os.path.join(o["ev"], ".claude", "skills", "ornek-skill")
        with open(os.path.join(sk, "kritik-yeni.md"), "w") as fh:
            fh.write("YEDEGE GIRMESI GEREKEN icerik\n")
        with open(o["betik"], encoding="utf-8") as fh:
            gov = fh.read()
        if COKME_CAPA not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r"
                               % COKME_CAPA)
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(COKME_CAPA, COKME, 1))
        r1 = izole_kos(o)
        iz1 = ""
        with open(o["kilit"], encoding="utf-8", errors="replace") as fh:
            iz1 = fh.read(256).strip()
        kd = durum.kilit_durumu(o["kok"])
        sat_k = durum.kilit_satirlari(kd)
        print("     --- pano ciktisi (kosum ortada coktu) ---")
        for s in (sat_k or ["(BOS)"]):
            print("    " + s)
        kontrol("13g: coken kosum exit!=0 (hata gizlenmiyor)", r1.returncode != 0,
                "rc=%d" % r1.returncode)
        kontrol("🔴 13g: ISTISNA yolunda iz `bitti=` TASIMIYOR",
                "bitti=" not in iz1, iz1[-70:])
        kontrol("13g: iz teshis icin `hata=` tasiyor (pid+baslangic korunuyor)",
                "hata=" in iz1 and "pid=" in iz1 and "baslangic=" in iz1, iz1[-70:])
        kontrol("🔴 13g: pano hali 'yarim' (kosum ortasinda kesilmis)",
                kd["hal"] == "yarim", kd["hal"])
        kontrol("13g: pano '⚠⚠ YARIM KALMIS YEDEK' diyor",
                bool(sat_k) and "YARIM KALMIS" in sat_k[0],
                (sat_k[0][:80] if sat_k else "(BOS)"))
        kontrol("13g: degisiklik GERCEKTEN yedege girmedi (kayip gercek)",
                not os.path.exists(os.path.join(o["hedef"], "skills", "ornek-skill",
                                                "kritik-yeni.md")))

        # 3) KIRMIZI-MUTASYON: istisna yolunda `bitti=` GERI gelirse pano SUSAR
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(COKME_CAPA, COKME, 1).replace(
                "                if basardi:\n"
                "                    imza = _sahip_imzasi(baslangic, bitti=simdi)\n"
                "                else:\n"
                "                    imza = _sahip_imzasi(baslangic, hata=simdi)",
                "                imza = _sahip_imzasi(baslangic, bitti=simdi)"
                "  # MUTANT: hep bitti", 1))
        izole_kos(o)
        iz_m = ""
        with open(o["kilit"], encoding="utf-8", errors="replace") as fh:
            iz_m = fh.read(256).strip()
        kd_m = durum.kilit_durumu(o["kok"])
        kontrol("MUTANTTA (hep bitti=) coken kosum TEMIZ gorunuyor, pano SUSUYOR "
                "(kontrol KIRMIZI yanardi)",
                "bitti=" in iz_m and kd_m["hal"] == "yok"
                and durum.kilit_satirlari(kd_m) == [],
                "hal=%s iz=%s" % (kd_m["hal"], iz_m[-50:]))

    # ---------------- 13i) KILIT CALINAMAZ (K1 regresyon nobeti) ----------------
    # K1 onarimi `bitti=`/`hata=` isaretlerini degistirdi. Isaretler bir KOLAYLIKTIR
    # (pano teshisi); KARSILIKLI DISLAMA cekirdekteki flock'tadir. Bir sey (bayat arac,
    # elle duzenleme, kotu niyetli iz) dosyaya SAHTE `bitti=` yazsa bile kilit
    # CALINAMAMALI: kilit gercekten tutuluyorken yeni kosum YINE atlamak zorunda.
    print("\n13i) KILIT CALINAMAZ — sahte `bitti=` izi flock'u DELMEZ")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        kilitci = open(o["kilit"], "a+")
        fcntl.flock(kilitci, fcntl.LOCK_EX)               # kilit GERCEKTEN tutuluyor
        kilitci.truncate(0)
        kilitci.write("pid=1 baslangic=%r iso=TEST bitti=%r\n"   # SAHTE temiz-birakma izi
                      % (time.time() - 7200, time.time()))
        kilitci.flush()
        r_c = izole_kos(o, "--gerekliyse")
        kontrol("sahte `bitti=` izine RAGMEN kosum ATLADI (flock cekirdekte)",
                r_c.returncode == 0 and "yedek ATLANDI" in r_c.stdout
                and "bitti ->" not in r_c.stdout,
                "rc=%d %s" % (r_c.returncode,
                              (r_c.stdout.strip().splitlines() or ["(bos)"])[0][:60]))
        kontrol("sahte iz hedefe yedek YAZDIRMADI (damga YOK)",
                damga_json(o["hedef"]) is None)
        fcntl.flock(kilitci, fcntl.LOCK_UN)
        kilitci.close()
        r_c2 = izole_kos(o, "--gerekliyse")
        kontrol("kilit gercekten birakilinca ayni kosum YEDEKLIYOR (kontrol olu degil)",
                "bitti ->" in r_c2.stdout, "rc=%d" % r_c2.returncode)

    # ---------------- 13h) K1 BIRIM: kilit_birak basari bayragi ----------------
    print("\n13h) K1 BIRIMI — kilit_birak(basardi=) fail-closed varsayilan")
    with tempfile.TemporaryDirectory() as td:
        yol = os.path.join(td, ".yedek.lock")
        hal, fd, bas = yedekle.kilit_al(yol)
        yedekle.kilit_birak(fd, baslangic=bas, basardi=True)
        kontrol("basardi=True -> iz `bitti=` tasiyor", "bitti=" in open(yol).read())
        hal, fd, bas = yedekle.kilit_al(yol)
        yedekle.kilit_birak(fd, baslangic=bas, basardi=False)
        iz = open(yol).read()
        kontrol("basardi=False -> `bitti=` YOK, `hata=` VAR",
                "bitti=" not in iz and "hata=" in iz, iz.strip()[-60:])
        hal, fd, bas = yedekle.kilit_al(yol)
        yedekle.kilit_birak(fd, baslangic=bas)          # bayrak VERILMEDI
        kontrol("bayrak verilmezse FAIL-CLOSED (`bitti=` yazilmaz)",
                "bitti=" not in open(yol).read(), open(yol).read().strip()[-60:])
        kontrol("main() basari bayragini kilit_birak'a GERCEKTEN veriyor (kablolama)",
                "basardi=basardi" in open(YEDEKLE, encoding="utf-8").read())

    # ---------------- 13c) atlama_kapsandi_mi SAF FONKSIYON (fail-closed) -------
    print("\n13c) KAPSAMA KARARI — olcemedigimiz her hal 'kapsanmadi' (fail-closed)")
    kontrol("kaynak sahip baslangicindan ESKI -> kapsandi",
            yedekle.atlama_kapsandi_mi(100.0, 50.0) is True)
    kontrol("kaynak sahip baslangiciyla AYNI -> kapsandi",
            yedekle.atlama_kapsandi_mi(100.0, 100.0) is True)
    kontrol("kaynak sahip baslangicindan YENI -> KAPSANMADI",
            yedekle.atlama_kapsandi_mi(100.0, 150.0) is False)
    kontrol("sahip baslangici bilinmiyor -> KAPSANMADI",
            yedekle.atlama_kapsandi_mi(None, 150.0) is False)
    kontrol("kaynak mtime olculemedi -> KAPSANMADI",
            yedekle.atlama_kapsandi_mi(100.0, None) is False)

    # ---------------- 13d) kilit_al/kilit_birak BIRIM DAVRANISI ----------------
    print("\n13d) KILIT BIRIMI — al/birak, ikinci alis MESGUL, kurulamayan yol FAIL-OPEN")
    with tempfile.TemporaryDirectory() as td:
        yol = os.path.join(td, ".yedek.lock")
        hal1, fd1, _b1 = yedekle.kilit_al(yol)
        kontrol("bos kilit ALINIYOR", hal1 == "alindi" and fd1 is not None, hal1)
        hal2, fd2, bilgi2 = yedekle.kilit_al(yol)
        kontrol("tutulurken ikinci alis MESGUL", hal2 == "mesgul" and fd2 is None, hal2)
        kontrol("sahip imzasi (pid+baslangic) okunabiliyor",
                "pid=%d" % os.getpid() in bilgi2[0] and isinstance(bilgi2[2], float),
                bilgi2[0][:60])
        # Alt sinir -1: time.time() MONOTON DEGIL; sahip imzasi ile okuma arasinda
        # milisaniye altinda negatif fark olculebiliyor (olculdu: -0,0003 sn). Yas
        # yalniz "asili sahip" (>1 saat) uyarisinda kullanildigi icin zararsiz.
        kontrol("sahip yasi hesaplaniyor (~0 sn)",
                isinstance(bilgi2[1], float) and -1 <= bilgi2[1] < 5, str(bilgi2[1]))
        yedekle.kilit_birak(fd1)
        hal3, fd3, _b3 = yedekle.kilit_al(yol)
        kontrol("birakilinca yeniden ALINIYOR", hal3 == "alindi", hal3)
        yedekle.kilit_birak(fd3)
        kontrol("kilit dosyasi SILINMEDI (inode yarisi onlenir)", os.path.exists(yol))
        kontrol("birakilan kilidin icerigi temizlendi (bayat sahip yaniltmasin)",
                open(yol).read().strip() == "")
        hal4, fd4, bilgi4 = yedekle.kilit_al(os.path.join(td, "olmayan-dizin", "x.lock"))
        kontrol("acilamayan kilit yolu -> 'kurulamadi' (FAIL-OPEN, yedek yine alinir)",
                hal4 == "kurulamadi" and fd4 is None, "%s / %s" % (hal4, str(bilgi4)[:50]))
        kontrol("kilit_birak(None) patlamiyor", yedekle.kilit_birak(None) is None)
        # kilitsiz kosum damgada ISARETLENIR (pano not duser)
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 4}, kilitsiz=True)
        kontrol("kilitsiz kosum damgada isaretli",
                yedekle.damga_oku(td).get("kilitsiz") is True)
        yedekle.damga_yaz(td, {"memory": 1, "skills": 1, "repo": 4})
        kontrol("kilitli kosumda isaret YOK", "kilitsiz" not in yedekle.damga_oku(td))
        kontrol("damgada baslangic alani var (gerekli_mi + pano referansi)",
                isinstance(yedekle.damga_oku(td).get("baslangic"), float))
        kontrol("gerekli_mi ARTIK baslangici referans aliyor",
                yedekle.gerekli_mi({"zaman": 200, "baslangic": 100}, 150) is True
                and yedekle.gerekli_mi({"zaman": 200, "baslangic": 100}, 90) is False)

    # ---------------- 13b) KIRMIZI-MUTASYON: kilit devre disi ----------------
    print("\n13b) KIRMIZI-MUTASYON — kilit kaldirilirsa eszamanli kosum GECER mi?")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        # kilit_al DAIMA 'alindi' der (mutant): kilitli hedefe ikinci kosum yine yazar
        with open(o["betik"], encoding="utf-8") as f:
            gov = f.read()
        capa = '    hal, kilit_fd, kilit_bilgi = kilit_al()'
        if capa not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r" % capa)
        with open(o["betik"], "w", encoding="utf-8") as f:
            f.write(gov.replace(capa, '    hal, kilit_fd, kilit_bilgi = ("alindi", None, None)'
                                       '  # MUTANT', 1))
        kilitci = open(o["kilit"], "a+")
        fcntl.flock(kilitci, fcntl.LOCK_EX)
        rm = izole_kos(o, "--gerekliyse")
        fcntl.flock(kilitci, fcntl.LOCK_UN)
        kilitci.close()
        kontrol("MUTANTTA kilit dinlenmedi, yedek YINE yazildi (kontrol KIRMIZI yanardi)",
                "bitti ->" in rm.stdout and "yedek ATLANDI" not in rm.stdout,
                "rc=%d" % rm.returncode)

    # ---------------- 14) ESZAMANLILIK: iki kosum AYNI ANDA ----------------
    print("\n14) ESZAMANLILIK — 3 turda 2'ser kosum: biri yedekler, obur ATLAR")
    tur_sonuc = []
    for tur in range(3):
        with tempfile.TemporaryDirectory() as td:
            o = izole_ortam(td, yedekle, memory_adet=400, skills_adet=150)
            p1, p2 = izole_baslat(o), izole_baslat(o)
            c1 = p1.communicate()
            c2 = p2.communicate()
            ciktilar = [c1[0], c2[0]]
            kodlar = [p1.returncode, p2.returncode]
            yazan = sum(1 for c in ciktilar if "bitti ->" in c)
            atlayan = sum(1 for c in ciktilar if "yedek ATLANDI" in c)
            dosyalar = hedef_dosyalari(o["hedef"])
            # +2: damga + atlama kaydi (atlayan kosum kendi dosyasina yazar)
            bekle = o["memory_adet"] + o["skills_adet"] + len(yedekle.REPO_BEKLENEN) + 2
            d = birlesik_json(o["hedef"])
            tur_sonuc.append({
                "yazan": yazan, "atlayan": atlayan, "kodlar": kodlar,
                "dosya": len(dosyalar), "bekle": bekle, "damga": d,
                "artik": [x for x in dosyalar if ".tmp-" in x],
                "pano": durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var")),
            })
    for i, t in enumerate(tur_sonuc, 1):
        kontrol("tur%d: TAM 1 kosum yedekledi, 1 kosum ATLADI" % i,
                t["yazan"] == 1 and t["atlayan"] == 1,
                "yazan=%d atlayan=%d" % (t["yazan"], t["atlayan"]))
        kontrol("tur%d: IKI kosum da exit 0 (push bloklanmadi)" % i, t["kodlar"] == [0, 0],
                str(t["kodlar"]))
        kontrol("tur%d: hedefte yarim/karismis cikti YOK (%d dosya)" % (i, t["dosya"]),
                t["dosya"] == t["bekle"] and not t["artik"],
                "beklenen %d, artik %s" % (t["bekle"], t["artik"] or "-"))
        kontrol("tur%d: damga TAM OLARAK BIR tam kosum bildiriyor" % i,
                t["damga"].get("tam") is True
                and t["damga"].get("memory") == 400 and t["damga"].get("skills") == 150,
                "tam=%s memory=%s skills=%s" % (t["damga"].get("tam"),
                                                t["damga"].get("memory"),
                                                t["damga"].get("skills")))
        kontrol("tur%d: ATLAYAN kosum kendi kaydinda iz birakti" % i,
                isinstance(t["damga"].get("son_atlama"), float)
                and isinstance(t["damga"].get("baslangic"), float))
        # Eszamanli ciftte kaynak DEGISMEZ -> atlama kapsanir; pano her paralel
        # push'ta bosuna sariya donmemeli (gurultulu pano = olu pano).
        kontrol("tur%d: atlama KAPSANDI olarak isaretlendi (bos uyari yok)" % i,
                t["damga"].get("son_atlama_kapsandi") is True,
                str(t["damga"].get("son_atlama_kapsandi")))
        kontrol("tur%d: beklenen sahip damgayi YAZDI (baslangic == sahip baslangici)" % i,
                t["damga"].get("baslangic") == t["damga"].get("son_atlama_sahip_baslangici"),
                "%r vs %r" % (t["damga"].get("baslangic"),
                              t["damga"].get("son_atlama_sahip_baslangici")))
        kontrol("tur%d: PANO SUSUYOR (normal eszamanli ciftte bos uyari yok)" % i,
                t["pano"][0].strip().startswith("taze:"), t["pano"][0])

    # ---------------- 14b) GERCEK URETIM YOLU: paralel `--gerekliyse` cifti ----
    # 🔴 Bolum 14 SENTETIK ciftti (kaynak taze, tam kopyalama). Baskin GERCEK yol
    # iki paralel push = `--gerekliyse` + KAYNAKTA DEGISIKLIK YOK. Curutucu bu yolda
    # 20/20 YAPISKAN yanlis "⚠⚠ KISMI YEDEK" olctu. Iki bagimsiz sebep vardi:
    #   (F1) kilit_birak dosyayi BOSALTIYORDU -> atlayan kosum sahibi tanimlayamiyor,
    #   (F2) GUNCEL yolu damga YAZMIYORDU     -> "sahip bitirdi mi" TANIM GEREGI hayir.
    # Ikisi de kapatildi; asagida gercek yolun yanlis-uyari sayisi 0 olmali.
    print("\n14b) GERCEK YOL — paralel `--gerekliyse` cifti (kaynak DEGISMEDI)")

    def paralel_gerekliyse(o, tur_sayisi):
        """Doner: (yanlis_uyari, sahip_okunamadi, kod_hatasi, ornek_satir)."""
        yanlis = okunamadi = kod_hatasi = 0
        ornek = ""
        for _ in range(tur_sayisi):
            p1, p2 = izole_baslat(o, "--gerekliyse"), izole_baslat(o, "--gerekliyse")
            c1, c2 = p1.communicate(), p2.communicate()
            if p1.returncode != 0 or p2.returncode != 0:
                kod_hatasi += 1
            if any("sahip bilgisi yok" in c for c in (c1[0], c2[0])):
                okunamadi += 1
            sat = durum.yedek_satirlari(durum.yedek_durumu(o["hedef"], "var"))
            if not sat[0].strip().startswith("taze:"):
                yanlis += 1
                ornek = ornek or sat[0].strip()
        return yanlis, okunamadi, kod_hatasi, ornek

    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        izole_kos(o)                                   # ilk tam yedek (damga olussun)
        yanlis, okunamadi, kod_hatasi, ornek = paralel_gerekliyse(o, 20)
        kontrol("🔢 20 paralel `--gerekliyse` cifti: YANLIS UYARI 0",
                yanlis == 0, "yanlis=%d/20  %s" % (yanlis, ornek[:80]))
        kontrol("20 ciftte 'sahip bilgisi yok' 0 (kilit izi okunabiliyor)",
                okunamadi == 0, "okunamadi=%d/20" % okunamadi)
        kontrol("20 ciftte exit!=0 yok (fail-open)", kod_hatasi == 0,
                "hata=%d/20" % kod_hatasi)
        d = damga_json(o["hedef"]) or {}
        kontrol("GUNCEL yolu damgayi DOGRULADI (baslangic ilerledi, zaman DOKUNULMADI)",
                isinstance(d.get("dogrulandi_iso"), str)
                and d.get("baslangic", 0) > d.get("zaman", 0),
                "baslangic-zaman=%.3f sn" % (d.get("baslangic", 0) - d.get("zaman", 0)))
        kontrol("dogrulama sayaclara/tamlik iddiasina DOKUNMADI",
                d.get("tam") is True and d.get("memory") == o["memory_adet"]
                and d.get("skills") == o["skills_adet"],
                "memory=%s skills=%s" % (d.get("memory"), d.get("skills")))

    # 14c) IKI DUZELTME DE GEREKLI MI? (birini kapatip ayni fiksturu olc)
    print("\n14c) HER IKI DUZELTME DE GEREKLI — birini kapatinca yanlis uyari donuyor mu?")
    for etiket, capa, yerine in (
            ("F1 kapali (kilit izi bosaltiliyor)",
             '                os.write(fd, imza.encode("utf-8"))',
             "                pass  # MUTANT: iz birakma"),
            ("F2 kapali (GUNCEL yolu damga yazmiyor)",
             "            tazelendi = damga_tazele(backup, baslangic, imza=bas_imza, "
             "kilitsiz=kilitsiz)",
             "            tazelendi = False  # MUTANT")):
        with tempfile.TemporaryDirectory() as td:
            o = izole_ortam(td, yedekle)
            with open(o["betik"], encoding="utf-8") as f:
                gov = f.read()
            if capa not in gov:
                raise RuntimeError("MUTASYON CAPASI BULUNAMADI: %r" % capa)
            with open(o["betik"], "w", encoding="utf-8") as f:
                f.write(gov.replace(capa, yerine, 1))
            izole_kos(o)
            m_yanlis, m_okunamadi, _h, m_ornek = paralel_gerekliyse(o, 10)
            kontrol("MUTANT [%s] -> yanlis uyari GERI GELDI" % etiket,
                    m_yanlis > 0, "yanlis=%d/10 sahip-okunamadi=%d/10  %s"
                    % (m_yanlis, m_okunamadi, m_ornek[:60]))

    # ---------------- 14d) K3: "DEGISIKLIK YOK" != "YEDEK BAYAT" ----------------
    # Tur-4 kusuru: `--gerekliyse` GUNCEL yolu `zaman`i ILERLETMEDIGI icin degismeyen
    # bir sistemde pano 2 gun sonra BOSUNA "⚠⚠ YEDEK BAYAT" diyordu; ayrica `kilitsiz`
    # notu MIRAS alinip yapisiyordu. Onarim: kosum OLCUMUNU damgaya yazar
    # (`dogrulandi` + `dogrulama_imzasi`) ve pano onu KENDISI dogrular.
    print("\n14d) K3 — IMZA BIRIMI + dogrulama kaydi + `kilitsiz` KOSUM-YEREL")
    imza_simdi = yedekle.kaynak_imzasi()
    kontrol("kaynak_imzasi adet/bayt/mtime donduruyor",
            isinstance(imza_simdi, dict)
            and isinstance(imza_simdi.get("adet"), int) and imza_simdi["adet"] > 0
            and isinstance(imza_simdi.get("bayt"), int)
            and isinstance(imza_simdi.get("mtime"), float),
            str(imza_simdi))
    kontrol("kaynak_imzasi mtime'i en_yeni_kaynak_mtime ile AYNI (tek gezinme kodu)",
            imza_simdi["mtime"] == yedekle.en_yeni_kaynak_mtime())
    kontrol("imza_esit_mi ayni imzada True", yedekle.imza_esit_mi(
        {"adet": 3, "bayt": 9, "mtime": 1.5}, {"adet": 3, "bayt": 9, "mtime": 1.5}) is True)
    for alan in ("adet", "bayt", "mtime"):
        bozuk = {"adet": 3, "bayt": 9, "mtime": 1.5}
        bozuk[alan] = 99
        kontrol("imza_esit_mi '%s' eksenindeki degisimi YAKALIYOR" % alan,
                yedekle.imza_esit_mi({"adet": 3, "bayt": 9, "mtime": 1.5}, bozuk) is False)
    kontrol("imza_esit_mi eksik/bozuk imzada fail-closed (False)",
            yedekle.imza_esit_mi(None, {"adet": 3, "bayt": 9, "mtime": 1.5}) is False
            and yedekle.imza_esit_mi({"adet": 3}, {"adet": 3}) is False)
    kontrol("gerekli_mi: imzalar FARKLIYSA mtime 'eski' dese bile YEDEKLE",
            yedekle.gerekli_mi({"zaman": 100, "baslangic": 100,
                                "kaynak_imzasi": {"adet": 3, "bayt": 9, "mtime": 50.0}},
                               50, imza={"adet": 3, "bayt": 10, "mtime": 50.0}) is True)
    kontrol("gerekli_mi: imzalar AYNIYSA (ve mtime eski) yine ATLA",
            yedekle.gerekli_mi({"zaman": 100, "baslangic": 100,
                                "kaynak_imzasi": {"adet": 3, "bayt": 9, "mtime": 50.0}},
                               50, imza={"adet": 3, "bayt": 9, "mtime": 50.0}) is False)

    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        izole_kos(o)                                   # tam yedek: kaynak_imzasi olussun
        d0 = damga_json(o["hedef"]) or {}
        kontrol("tam kosum damgaya `kaynak_imzasi` yaziyor",
                yedekle.imza_esit_mi(d0.get("kaynak_imzasi"), d0.get("kaynak_imzasi"))
                and isinstance(d0.get("kaynak_imzasi"), dict), str(d0.get("kaynak_imzasi")))
        r_g = izole_kos(o, "--gerekliyse")
        d1 = damga_json(o["hedef"]) or {}
        kontrol("GUNCEL yolu 'atla' dedi", "yedek GUNCEL" in r_g.stdout,
                r_g.stdout.strip().splitlines()[0][:70] if r_g.stdout.strip() else "")
        kontrol("GUNCEL yolu `dogrulandi` + `dogrulama_imzasi` yaziyor",
                isinstance(d1.get("dogrulandi"), float)
                and yedekle.imza_esit_mi(d1.get("dogrulama_imzasi"),
                                         d1.get("kaynak_imzasi")),
                "dogrulandi=%s" % (d1.get("dogrulandi") is not None))
        kontrol("GUNCEL yolu `zaman`a ve sayaclara DOKUNMADI",
                d1.get("zaman") == d0.get("zaman") and d1.get("memory") == d0.get("memory"))

        # PANO UCU: damgayi 3 gun geriye al (esik asilmis gibi) -> pano BAYAT DEMEMELI
        eski = dict(d1)
        eski["zaman"] = time.time() - 3 * 86400
        with open(os.path.join(o["hedef"], yedekle.DAMGA_ADI), "w", encoding="utf-8") as fh:
            json.dump(eski, fh)
        # 🔴 K5 (6. tur): pano artik KAYNAKLARIN SU ANKI imzasini da olcuyor. Burada
        # kaynaklar IZOLE KUM HAVUZUNDA (sahte HOME + sahte repo); panonun kendi
        # `_canli_kaynak_imzasi`i ise GERCEK makineyi olcer -> karsilastirma anlamsiz
        # olurdu. O yuzden olcum KUM HAVUZUNUN KENDI yedekle.py'siyle yapilir ve
        # panoya verilir: uctan uca zincir (yazici -> damga -> pano) gercekten olculur.
        _kum_imza = izole_imza(o)
        kontrol("hazirlik: kum havuzunun canli imzasi OLCULDU (fikstur ISIRIYOR)",
                isinstance(_kum_imza, dict) and _kum_imza.get("adet", 0) > 0,
                str(_kum_imza))
        _pano_gercek_canli = durum._canli_kaynak_imzasi
        durum._canli_kaynak_imzasi = lambda: {"kok": o["kok"], "adaylar": [_kum_imza]}
        try:
            dd = durum.yedek_durumu(o["hedef"], "var")
            sat = durum.yedek_satirlari(dd)
            print("     --- pano ciktisi (3 gun eski ama DOGRULANMIS) ---")
            for s in sat:
                print("    " + s)
            kontrol("🔴 K3: 3 gun eski ama dogrulanmis yedek 'guncel' "
                    "(BOSUNA BAYAT DEMIYOR)",
                    dd["hal"] == "guncel" and "GÜNCEL" in sat[0]
                    and not any("BAYAT" in s for s in sat), dd["hal"])
            # 🔴 K5 UCTAN UCA: kum havuzunda GERCEK bir dosya degisince (mtime KORUNARAK)
            # ayni damga artik GUNCEL SAYILMAZ — kardes kosum damgaya HIC DOKUNMASA da.
            _degisen = os.path.join(o["ev"], ".claude", "projects",
                                    "-Users-okan-dev-pruvo", "memory", "not-001.md")
            _st = os.stat(_degisen)
            with open(_degisen, "w") as fh:
                fh.write("mtime KORUNARAK buyutulmus icerik (K5 uctan uca nobeti)\n")
            os.utime(_degisen, (_st.st_atime, _st.st_mtime))     # mtime GERI alindi
            _kum_imza2 = izole_imza(o)
            kontrol("K5 hazirlik: mtime KORUNMUS degisim imzayi DEGISTIRDI (bayt ekseni)",
                    isinstance(_kum_imza2, dict)
                    and _kum_imza2.get("bayt") != _kum_imza.get("bayt")
                    and _kum_imza2.get("mtime") == _kum_imza.get("mtime"),
                    "%s -> %s" % (_kum_imza.get("bayt"), (_kum_imza2 or {}).get("bayt")))
            durum._canli_kaynak_imzasi = lambda: {"kok": o["kok"],
                                                  "adaylar": [_kum_imza2]}
            dd2 = durum.yedek_durumu(o["hedef"], "var")
            sat2 = durum.yedek_satirlari(dd2)
            kontrol("🔴 K5 UCTAN UCA: kaynak degisti + damgaya kimse dokunmadi -> "
                    "pano GUNCEL DEMIYOR",
                    dd2["hal"] == "kapsam-degisti" and "GÜNCEL" not in sat2[0]
                    and "KAPSAMIYOR" in sat2[0], "%s | %s" % (dd2["hal"], sat2[0][:70]))
        finally:
            durum._canli_kaynak_imzasi = _pano_gercek_canli

        # SESSIZ-YESIL NOBETI: kaynak GERCEKTEN degisirse ayni damga GUNCEL SAYILMAZ
        with open(os.path.join(o["ev"], ".claude", "projects",
                               "-Users-okan-dev-pruvo", "memory", "yeni-dosya.md"), "w") as fh:
            fh.write("yeni icerik\n")
        imza_yeni = None
        r_y = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util,json,sys;"
             "spec=importlib.util.spec_from_file_location('y', %r);"
             "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
             "print(json.dumps(m.kaynak_imzasi()))" % o["betik"]],
            capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])
        try:
            imza_yeni = json.loads(r_y.stdout.strip())
        except ValueError:
            imza_yeni = None
        kontrol("yeni dosya kaynak imzasini DEGISTIRDI (adet arttı)",
                isinstance(imza_yeni, dict)
                and imza_yeni.get("adet", 0) > (d1.get("kaynak_imzasi") or {}).get("adet", 0),
                "%s -> %s" % ((d1.get("kaynak_imzasi") or {}).get("adet"),
                              (imza_yeni or {}).get("adet")))
        r_g2 = izole_kos(o, "--gerekliyse")
        kontrol("degisiklikten sonra `--gerekliyse` GERCEKTEN yedekliyor (atlamiyor)",
                "bitti ->" in r_g2.stdout and "yedek GUNCEL" not in r_g2.stdout,
                r_g2.stdout.strip().splitlines()[-1][:60] if r_g2.stdout.strip() else "")

        # MTIME KORUNARAK yapilan icerik degisikligi de yakalanmali (imza `bayt` ekseni)
        hedef_md = os.path.join(o["ev"], ".claude", "projects",
                                "-Users-okan-dev-pruvo", "memory", "not-000.md")
        st = os.stat(hedef_md)
        with open(hedef_md, "w") as fh:
            fh.write("mtime KORUNARAK buyutulmus icerik — bayt ekseni bunu gormeli\n")
        os.utime(hedef_md, (st.st_atime, st.st_mtime))     # mtime GERI alindi
        r_g3 = izole_kos(o, "--gerekliyse")
        kontrol("🔴 mtime KORUNMUS icerik degisikligi ATLANMIYOR (bayt ekseni isiriyor)",
                "bitti ->" in r_g3.stdout and "yedek GUNCEL" not in r_g3.stdout,
                r_g3.stdout.strip().splitlines()[-1][:60] if r_g3.stdout.strip() else "")

        # `kilitsiz` KOSUM-YEREL: miras bayrak dogrulama kosumunda TEMIZLENIR
        d_k = damga_json(o["hedef"]) or {}
        d_k["kilitsiz"] = True
        with open(os.path.join(o["hedef"], yedekle.DAMGA_ADI), "w", encoding="utf-8") as fh:
            json.dump(d_k, fh)
        kontrol("hazirlik: damgada miras `kilitsiz` bayragi VAR",
                (damga_json(o["hedef"]) or {}).get("kilitsiz") is True)
        izole_kos(o, "--gerekliyse")
        kontrol("🔴 K3: kilitli dogrulama kosumu MIRAS `kilitsiz` notunu TEMIZLIYOR",
                "kilitsiz" not in (damga_json(o["hedef"]) or {}),
                str(sorted(damga_json(o["hedef"]) or {})))
        kontrol("pano yapiskan KILITSIZ notunu artik BASMIYOR",
                not any("KILITSIZ" in s for s in durum.yedek_satirlari(
                    durum.yedek_durumu(o["hedef"], "var"))))

    # 14e) KIRMIZI-MUTASYON: dogrulama imzasi yazilmazsa pano GUNCEL DEMEMELI
    print("\n14e) K3 KIRMIZI-MUTASYON — imza yazilmazsa yesil iddia URETILMEZ")
    with tempfile.TemporaryDirectory() as td:
        o = izole_ortam(td, yedekle)
        with open(o["betik"], encoding="utf-8") as fh:
            gov = fh.read()
        capa = '        veri["dogrulama_imzasi"] = imza'
        if capa not in gov:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI: %r" % capa)
        with open(o["betik"], "w", encoding="utf-8") as fh:
            fh.write(gov.replace(capa, "        pass  # MUTANT: imza yazilmiyor", 1))
        izole_kos(o)
        izole_kos(o, "--gerekliyse")
        d_m = damga_json(o["hedef"]) or {}
        d_m["zaman"] = time.time() - 3 * 86400
        with open(os.path.join(o["hedef"], yedekle.DAMGA_ADI), "w", encoding="utf-8") as fh:
            json.dump(d_m, fh)
        dd_m = durum.yedek_durumu(o["hedef"], "var")
        sat_m = durum.yedek_satirlari(dd_m)
        kontrol("MUTANTTA (imzasiz dogrulama) pano GUNCEL DEMIYOR -> OLCULEMEDI/BAYAT",
                dd_m["hal"] in ("dogrulama-olculemedi", "bayat")
                and "GÜNCEL" not in sat_m[0], "%s | %s" % (dd_m["hal"], sat_m[0][:60]))

    # ---------------- 15) GERCEK HEDEF DOKUNULMADI ----------------
    print("\n15) IZOLASYON KANITI — gercek Drive damgasi + .stl-backup-dir DEGISMEDI")
    izler_sonra = gercek_kritik_parmakizi(yedekle)
    d_yol, d_once = izler_once["damga"]
    kontrol("gercek damga yolu ile test yolu FARKLI",
            d_yol is None or not d_yol.startswith(tempfile.gettempdir()), str(d_yol))
    for etiket in sorted(izler_once):
        y1, v1 = izler_once[etiket]
        y2, v2 = izler_sonra[etiket]
        kontrol("GERCEK %s bayt+mtime AYNI (test yazmadi)" % etiket,
                y1 == y2 and v1 == v2,
                "%s" % ("yok (cozulemedi)" if v1 is None else "degismedi"))
    # 🔴 FAIL-CLOSED KABLOLAMA NOBETCISI (K5): gercek yola YAZAN yol (drive_yolu.
    # stl_dizini / pruvo_dizini) bu testin KAYNAGINDA cagrilmamali. Yukaridaki
    # bayt-esitlik kontrolu yalniz BUGUNKU ortamda (kayitli yol gecerli) yesil
    # yanar; yol bayatladigi gun yazma sessizce geri gelirdi.
    # ⚠️ IGNELER PARCALI kurulur: tek parca yazilsa bu satirin KENDISI eslesir
    # (kapi kendi kaynagini tarar) ve kontrol sonsuza dek sahte-kirmizi yanar.
    kendi_govde = open(__file__, encoding="utf-8").read()
    igneler = ("drive_yolu." + "stl_dizini(", "drive_yolu." + "pruvo_dizini(")
    yazan_cagri = [c for c in igneler if c in kendi_govde]
    kontrol("test GERCEK yola YAZAN cozucuyu HIC cagirmiyor (fail-closed)",
            not yazan_cagri, "bulunan: %s" % (yazan_cagri or "-"))
    # Kontrolun OLU olmadiginin kaniti: ayni arama, GERCEKTEN cagiran yedekle.py'de
    # ISABET vermeli (yoksa "igne hic eslesmiyor" diye sessizce yesil kalirdi).
    kontrol("igne olu DEGIL: ayni arama yedekle.py'de ISABET veriyor",
            any(c in open(YEDEKLE, encoding="utf-8").read() for c in igneler))
    if d_once:
        try:
            eski = json.loads(d_once[0].decode("utf-8"))
            kontrol("gercek damga sayaclari korundu",
                    isinstance(eski.get("memory"), int),
                    "memory=%s skills=%s repo=%s" % (eski.get("memory"), eski.get("skills"),
                                                     eski.get("repo")))
        except ValueError:
            kontrol("gercek damga JSON okunabilir", False)

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
