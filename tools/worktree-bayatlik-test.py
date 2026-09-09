#!/usr/bin/env python3
"""KABUL BATARYASI — tools/worktree-kapi-bayatlik-kapisi.py

Hermetik bir "ev" deposu kurar (gercek git deposu + gercek worktree), harness'in
.claude/ kopyalamasini TAKLIT eder ve arizayi kasten uretir. Kapinin CANLI
govdesine DOKUNULMAZ; mutantlar izole bir KOPYAYA uygulanir
[[mutant-canli-govdede-yasamaz]].

Her mutant iki sey kanitlar:
  (1) CAPA BULUNDU  — yama gercekten uygulandi (metin degisti), sessiz no-op degil
      [[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]
  (2) HEDEF KOL OLDU — mutantla, KIRMIZI olmasi gereken vaka YESILE doner

Kontrol mutanti (kozmetik) hicbir vakayi degistirmemeli; degistirirse batarya
kendi capasini yanlis yere nisanlamis demektir [[artik-yuzey-mutant-dedektorunu-korlestirir]].

KOSUM:  python3 tools/worktree-bayatlik-test.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(ROOT, "worktree-kapi-bayatlik-kapisi.py")

KAPI_V1 = "#!/usr/bin/env python3\n# ornek kapi GOVDE-V1\nraise SystemExit(0)\n"
KAPI_V2 = "#!/usr/bin/env python3\n# ornek kapi GOVDE-V2 (ANA checkout'ta CANLI)\nraise SystemExit(0)\n"

AYAR_TAM = """{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python3 \\"${CLAUDE_PROJECT_DIR:-.}/tools/ornek-kapisi.py\\""},
        {"type": "command", "command": "python3 \\"${CLAUDE_PROJECT_DIR:-.}/tools/ikinci-kapisi.py\\""}
      ]}
    ]
  }
}
"""

AYAR_EKSIK = """{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python3 \\"${CLAUDE_PROJECT_DIR:-.}/tools/ornek-kapisi.py\\""}
      ]}
    ]
  }
}
"""


def _git(kok, *a):
    r = subprocess.run(("git", "-C", kok) + a, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git %s -> rc=%d\n%s" % (" ".join(a), r.returncode, r.stderr))
    return r.stdout


def _yaz(yol, metin):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def ev_kur(taban, canli=True):
    """Gercek git deposu + gercek worktree. realpath SART: macOS'ta /tmp bir
    symlink'tir ve git yollari cozerek dondurur [[sentetik-git-fiksturunde-realpath-sart]].

    canli=True  -> agacta main'de OLMAYAN commit var  => CANLI siniflanir
    canli=False -> agacin ucu main'e esit             => ARTIK siniflanir
    """
    ev = os.path.realpath(os.path.join(taban, "ev"))
    os.makedirs(ev)
    _git(ev, "init", "-q", "-b", "main")
    _git(ev, "config", "user.email", "t@t")
    _git(ev, "config", "user.name", "T")
    _yaz(os.path.join(ev, "tools", "ornek-kapisi.py"), KAPI_V1)
    _yaz(os.path.join(ev, "tools", "ikinci-kapisi.py"), KAPI_V1)
    _yaz(os.path.join(ev, ".claude", "settings.json"), AYAR_TAM)
    _yaz(os.path.join(ev, ".gitignore"), ".claude/\n")
    _git(ev, "add", "-A")
    _git(ev, "commit", "-q", "-m", "taban")

    wt = os.path.realpath(os.path.join(taban, "agac"))
    _git(ev, "worktree", "add", "-q", "-b", "cip", wt)
    # Harness .claude/'i worktree'ye KOPYALAR (ignore edildigi icin git getirmez).
    shutil.copytree(os.path.join(ev, ".claude"), os.path.join(wt, ".claude"))
    if canli:
        # CANLI sinifina sokmak icin agaca main'de OLMAYAN bir commit koy.
        # Fikstur dizininde koklenmis surec YOKTUR, dolayisiyla canlilik
        # hukmu IKINCI kanita (ata olmayan uc) dayanir. Bu yapilmazsa uc
        # main'e esit olur, agac ARTIK siniflanir ve V2/V3 SAHTE-YESIL olurdu.
        _yaz(os.path.join(wt, "cip-isi.txt"), "bekleyen is\n")
        _git(wt, "add", "-A")
        _git(wt, "commit", "-q", "-m", "cip commiti (main'de YOK)")
    return ev, wt


def kapiyi_kos(kapi_yolu, ev):
    r = subprocess.run([sys.executable, kapi_yolu, "--ev", ev, "--sessiz"],
                       capture_output=True, text=True)
    sayilar = {}
    for anahtar in ("EKSEN-A_SAPAN", "EKSEN-B_FARK", "OLCULEMEDI",
                    "ARTIK_AGAC", "ARTIK_BULGU"):
        m = re.search(r"^%s=(\d+)$" % re.escape(anahtar), r.stdout, re.M)
        sayilar[anahtar] = int(m.group(1)) if m else None
    m = re.search(r"^HAL=(\w+)$", r.stdout, re.M)
    sayilar["HAL"] = m.group(1) if m else None
    sayilar["rc"] = r.returncode
    sayilar["_ham"] = r.stdout + r.stderr
    return sayilar


# ------------------------------------------------------------------- vakalar
def vaka_temiz(taban):
    ev, wt = ev_kur(taban)
    return ev


def vaka_govde_bayat(taban):
    """ANA checkout'un DISKINDE kapi V2'ye guncellenir; worktree V1'de kalir.
    Gercekte bunu skip-worktree + taze worktree checkout'u uretir."""
    ev, wt = ev_kur(taban)
    _yaz(os.path.join(ev, "tools", "ornek-kapisi.py"), KAPI_V2)
    return ev


def vaka_baglanti_dustu(taban):
    """Worktree'nin kablolamasi ana checkout'tan ESKI: bir kapi HIC bagli degil."""
    ev, wt = ev_kur(taban)
    _yaz(os.path.join(wt, ".claude", "settings.json"), AYAR_EKSIK)
    return ev


def vaka_settings_yok(taban):
    ev, wt = ev_kur(taban)
    os.remove(os.path.join(wt, ".claude", "settings.json"))
    return ev


def vaka_settings_bozuk(taban):
    ev, wt = ev_kur(taban)
    _yaz(os.path.join(wt, ".claude", "settings.json"), "{ bu JSON degil ,,, ")
    return ev


def vaka_ana_settings_bozuk(taban):
    """ANA checkout'un kablolamasi okunamiyor.

    Bu vaka OLCULEMEDI kolunu YALNIZ BASINA yakar (A=0, B=0). V4/V5'te
    EKSEN-B de yandigi icin komsu kol OLCULEMEDI mutantini MASKELIYORDU
    [[fail-closed-kol-arkasindaki-kolu-maskeler]] — kol izole edilmeden
    oldurulup oldurulmedigi olculemez."""
    ev, wt = ev_kur(taban)
    _yaz(os.path.join(ev, ".claude", "settings.json"), "{{{ bozuk ")
    return ev


def vaka_artik_agac(taban):
    """ARTIK agac: koklenmis surec YOK + ucu main'in ATASI (icerik main'de).

    Ayni BAYATLIK V2'de KIRMIZI yakiyor; burada yalnizca ARTIK_BULGU'ya
    yazilmali ve rc=0 KALMALI. Aksi halde bitmis cip agaclari canli
    kirmizilari bogar ([[sizinti-nobetcisi-canli-olu-ayrimi]])."""
    ev, wt = ev_kur(taban, canli=False)
    _yaz(os.path.join(ev, "tools", "ornek-kapisi.py"), KAPI_V2)
    return ev


def vaka_artik_kablolama_dustu(taban):
    """ARTIK agacin kablolamasi HIC yok: yine rc=0, yalniz ARTIK_BULGU."""
    ev, wt = ev_kur(taban, canli=False)
    os.remove(os.path.join(wt, ".claude", "settings.json"))
    return ev


# vaka adi -> (kurucu, beklenen_kirmizi_mi, hangi_eksen)
VAKALAR = [
    ("V1-TEMIZ",           vaka_temiz,            False, None),
    ("V2-GOVDE-BAYAT",     vaka_govde_bayat,      True,  "EKSEN-A_SAPAN"),
    ("V3-BAGLANTI-DUSTU",  vaka_baglanti_dustu,   True,  "EKSEN-B_FARK"),
    ("V4-SETTINGS-YOK",    vaka_settings_yok,     True,  "OLCULEMEDI"),
    ("V5-SETTINGS-BOZUK",  vaka_settings_bozuk,   True,  "OLCULEMEDI"),
    ("V6-ANA-AYAR-BOZUK",  vaka_ana_settings_bozuk, True, "OLCULEMEDI"),
    # ARTIK kovasi: BULGU var ama rc=0 — kirmizi beklenmez, sayac beklenir.
    ("V7-ARTIK-BAYAT",     vaka_artik_agac,        False, "ARTIK_BULGU"),
    ("V8-ARTIK-KABLO-YOK", vaka_artik_kablolama_dustu, False, "ARTIK_BULGU"),
]


def bataryayi_kos(kapi_yolu):
    """{vaka: sayilar}"""
    sonuc = {}
    for ad, kurucu, _k, _e in VAKALAR:
        taban = tempfile.mkdtemp(prefix="wtbayat-")
        try:
            ev = kurucu(taban)
            sonuc[ad] = kapiyi_kos(kapi_yolu, ev)
        finally:
            shutil.rmtree(taban, ignore_errors=True)
    return sonuc


# ------------------------------------------------------------------ mutantlar
# (ad, capa, yeni, oldurmesi_beklenen_vaka)  — capa CANLI govdede AYNEN gecmeli
MUTANTLAR = [
    ("M1-EKSEN-A-KOR",
     "                if s_wt != s_ana:",
     "                if False:",
     "V2-GOVDE-BAYAT"),
    ("M2-EKSEN-B-KOR",
     "        dusen = ana_kume - wt_kume",
     "        dusen = set()",
     "V3-BAGLANTI-DUSTU"),
    # CAPA COK SATIRLI: `return 0, 0, 1, satirlar` govdede IKI kez gecer
    # (worktree-list arizasi + ana-ayar arizasi). Tek satirlik capa ILK
    # gecisi yamalar ve YANLIS kolu olcerdi [[ad-iki-rolde-mutanti-golgeler]].
    ("M3-FAIL-OPEN",
     '        satirlar.append("%-18s ANA-SETTINGS HAL=%s  (OLCULEMEDI)" % (ev_adi, ana_hal))\n'
     "        return 0, 0, 1, 0, 0, satirlar",
     '        satirlar.append("%-18s ANA-SETTINGS HAL=%s  (OLCULEMEDI)" % (ev_adi, ana_hal))\n'
     "        return 0, 0, 0, 0, 0, satirlar",
     "V6-ANA-AYAR-BOZUK"),
    # M4: canlilik kolu HER agaci ARTIK sayarsa, CANLI bir agactaki gercek
    # bayatlik rc'den duser = SAHTE YESIL. Bu, CANLI/OLU ayrimini eklerken
    # acilan en tehlikeli delik; kol civilenmeden eksen olculmus sayilmaz.
    ("M4-HEPSI-ARTIK",
     '        olu = (hayat == "ARTIK")',
     "        olu = True",
     "V2-GOVDE-BAYAT"),
    # M5: ters yon — hicbir agac ARTIK sayilmazsa ARTIK kovasi BOS kalir ve
    # bitmis agaclar canli kirmiziya karisir (V7 KIRMIZI'ya doner).
    ("M5-HIC-ARTIK-YOK",
     '        olu = (hayat == "ARTIK")',
     "        olu = False",
     "V7-ARTIK-BAYAT"),
]

KONTROL = ("K1-KOZMETIK",
           '    """(eksen_a, eksen_b, olculemedi, satirlar)"""',
           '    """(eksen_a, eksen_b, olculemedi, satirlar) — kozmetik kontrol"""')


def mutant_uygula(kaynak, hedef_dizin, capa, yeni):
    with open(kaynak, encoding="utf-8") as f:
        metin = f.read()
    if capa not in metin:
        return None, "CAPA-BULUNAMADI"
    yeni_metin = metin.replace(capa, yeni, 1)
    if yeni_metin == metin:
        return None, "METIN-DEGISMEDI"
    hedef = os.path.join(hedef_dizin, os.path.basename(kaynak))
    _yaz(hedef, yeni_metin)
    return hedef, None


def main():
    print("=" * 66)
    print("KABUL BATARYASI — worktree-kapi-bayatlik-kapisi.py")
    print("=" * 66)
    if not os.path.exists(KAPI):
        print("KAPI YOK: %s" % KAPI)
        return 1

    basarisiz = 0

    # --- 1) TABAN: canli govde, bes vaka ---------------------------------
    print("\n[1] TABAN (canli govde)")
    taban = bataryayi_kos(KAPI)
    for ad, _k, kirmizi_mi, eksen in VAKALAR:
        s = taban[ad]
        bekle = "KIRMIZI" if kirmizi_mi else "TEMIZ"
        gercek = "KIRMIZI" if s["rc"] != 0 else "TEMIZ"
        ok = (gercek == bekle)
        # DOGRU kova yanmali — hem KIRMIZI vakalarda hem ARTIK vakalarinda.
        # ARTIK vakalari rc=0 ama ARTIK_BULGU>=1 olmali: yalniz rc'ye bakan
        # kol, kapinin bulguyu HIC gormemesiyle ARTIK'a yazmasini ayirt etmez.
        if ok and eksen:
            ok = (s.get(eksen) or 0) >= 1
        if not ok:
            basarisiz += 1
        print("    %-20s rc=%-2s A=%-2s B=%-2s OLC=%-2s ART=%-2s/%-2s HAL=%-8s bekle=%-8s %s"
              % (ad, s["rc"], s["EKSEN-A_SAPAN"], s["EKSEN-B_FARK"],
                 s["OLCULEMEDI"], s["ARTIK_AGAC"], s["ARTIK_BULGU"],
                 s["HAL"], bekle, "OK" if ok else "### KIRIK"))

    # --- 2) MUTANTLAR ------------------------------------------------------
    print("\n[2] MUTANTLAR (izole kopyada; canli govdeye DOKUNULMAZ)")
    for ad, capa, yeni, hedef_vaka in MUTANTLAR:
        d = tempfile.mkdtemp(prefix="wtbayat-mut-")
        try:
            kopya, hata = mutant_uygula(KAPI, d, capa, yeni)
            if hata:
                basarisiz += 1
                print("    %-16s ### MUTANT ULASMADI (%s) — capa canli govdede YOK"
                      % (ad, hata))
                continue
            mut = bataryayi_kos(kopya)
            t_rc = taban[hedef_vaka]["rc"]
            m_rc = mut[hedef_vaka]["rc"]
            # Hedef kol OLDU MU: mutant o vakanin HUKMUNU DEGISTIRMELI.
            # Yon-bagimsiz olmali: fail-open mutantlari KIRMIZI->YESIL,
            # fail-closed (ARTIK kovasini bosaltan) mutantlari YESIL->KIRMIZI
            # cevirir. Yalniz ilk yonu arayan olcut, ARTIK kolunu HIC olcmez
            # ve M5 sessizce "oldurmedi" gorunurdu.
            oldurdu = (t_rc != m_rc)
            # Mutant hicbir seyi degistirmediyse ULASMAMIS demektir
            ayni = all(mut[v]["rc"] == taban[v]["rc"] for v, _a, _b, _c in VAKALAR)
            if ayni:
                basarisiz += 1
                print("    %-16s ### MUTANT ULASMADI (tum vakalar tabanla AYNI)" % ad)
                continue
            if not oldurdu:
                basarisiz += 1
            print("    %-16s hedef=%-18s taban_rc=%s mutant_rc=%s  %s"
                  % (ad, hedef_vaka, t_rc, m_rc,
                     "OLDURDU ✅" if oldurdu else "### OLDURMEDI"))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    # --- 3) KONTROL --------------------------------------------------------
    print("\n[3] KONTROL MUTANTI (kozmetik — hicbir vakayi DEGISTIRMEMELI)")
    ad, capa, yeni = KONTROL
    d = tempfile.mkdtemp(prefix="wtbayat-kon-")
    try:
        kopya, hata = mutant_uygula(KAPI, d, capa, yeni)
        if hata:
            basarisiz += 1
            print("    %-16s ### CAPA BULUNAMADI (%s)" % (ad, hata))
        else:
            kon = bataryayi_kos(kopya)
            sapan = [v for v, _a, _b, _c in VAKALAR if kon[v]["rc"] != taban[v]["rc"]]
            if sapan:
                basarisiz += 1
                print("    %-16s ### KIRLI KONTROL — sapan vaka: %s" % (ad, ",".join(sapan)))
            else:
                # Sayi VAKALAR'dan TURETILIR; elle yazilan sabit vaka eklenince
                # sessizce bayatlar [[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]]
                print("    %-16s TEMIZ ✅ (%d/%d vaka tabanla ozdes)"
                      % (ad, len(VAKALAR), len(VAKALAR)))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n" + "=" * 66)
    print("BASARISIZ_KALEM=%d" % basarisiz)
    print("SONUC: %s" % ("YESIL ✅" if basarisiz == 0 else "KIRMIZI ❌"))
    print("=" * 66)
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
