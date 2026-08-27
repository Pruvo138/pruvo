#!/usr/bin/env python3
"""K304 dagitim/bayatlik duzleminin KABUL TESTI — vakalar + mutasyon bataryasi.

Hicbir vaka gercek kardes eve YAZMAZ: butun yazma islemleri bu betigin actigi FIKSTUR
EVLERINDE (tempdir) olur; gercek evler yalnizca OKUNUR (V0 ve eski-kopya fiksturu).

Uretim kodunda 'test ise sunu yap' kolu YOKTUR: fikstur evleri, modulun tempdir'e
alinmis KOPYASINDA `EVLER` ezilerek taninir (modul_dizini_kur).

Kosum:
    python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-test.py
    python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-test.py --mutasyon
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
import kapi_dagitim as KD  # noqa: E402

KAPI = os.path.join(BURASI, "kapi-dagitim-kapisi.py")
KUR = os.path.join(BURASI, "kapi-dagitim-kur.py")
ESKI_KOPYA_KAYNAGI = "/Users/okan/dev/pruvo-advisor/.claude/mimar-icra-kapisi.py"

SONUC = []
OLCULEMEDI = []


def olculemedi(ad, sebep):
    """Ortam yuzunden KOSULAMAYAN vaka. Sessizce yesile SAYILMAZ, ADIYLA basilir
    ([[olculemedi-bypass-degil-menzil-daraltmasi]])."""
    OLCULEMEDI.append(ad + " — " + sebep)


def eski_kopya():
    """DONMUS (shim OLMAYAN) bir govde metni. Doner: (metin, kaynak_adi, gercek_mi).

    Canli makinede GERCEK bayat kopya (BaBa evi) okunur — bu, K318 ROL kolunu
    TASIMAYAN gercek bir bayat govdedir. CI kosucusunda o dosya YOKTUR; orada kanonik
    govdenin kendisi kullanilir: shim OLMADIGI icin ESKI_KOPYA sinifina duser (sinif
    ekseni olculur) ama ROL kolunu TASIDIGI icin V7 kosulamaz."""
    if os.path.exists(ESKI_KOPYA_KAYNAGI):
        with open(ESKI_KOPYA_KAYNAGI, encoding="utf-8") as f:
            return f.read(), ESKI_KOPYA_KAYNAGI, True
    with open(KD.KAYNAK, encoding="utf-8") as f:
        return f.read(), KD.KAYNAK + " (CI vekili)", False


def iddia(ad, beklenen, gozlenen):
    gecti = beklenen == gozlenen
    SONUC.append((ad, gecti, beklenen, gozlenen))
    return gecti


def kos(argv, girdi=None):
    p = subprocess.run(
        [sys.executable] + argv,
        input=(json.dumps(girdi) if girdi is not None else ""),
        capture_output=True, text=True, timeout=180,
    )
    return p.stdout, p.stderr, p.returncode


def deny_mi(stdout):
    try:
        veri = json.loads(stdout.strip())
    except Exception:
        return False
    return (veri.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny"


def fikstur_ev(kok, ad_dizin, worktree_adi=None):
    """Sahte ev: <kok>/<ad_dizin>/.claude + .git/worktrees kaydi.
    Doner: (ev_koku, worktree_koku ya da None)."""
    ev = os.path.join(kok, ad_dizin)
    os.makedirs(os.path.join(ev, ".claude"), exist_ok=True)
    os.makedirs(os.path.join(ev, ".git", "worktrees"), exist_ok=True)
    wt = None
    if worktree_adi:
        wt = os.path.join(ev, ".claude", "worktrees", worktree_adi)
        os.makedirs(wt, exist_ok=True)
        kayit = os.path.join(ev, ".git", "worktrees", worktree_adi)
        os.makedirs(kayit, exist_ok=True)
        with open(os.path.join(kayit, "gitdir"), "w", encoding="utf-8") as f:
            f.write(os.path.join(wt, ".git") + "\n")
    return ev, wt


def temiz_modul_metni():
    with open(os.path.join(BURASI, "kapi_dagitim.py"), encoding="utf-8") as f:
        return f.read()


KOPYALANAN = ("kapi_dagitim.py", "kapi-dagitim-kapisi.py", "kapi-dagitim-kur.py",
              "mimar-kapi-kur.py", "mimar_kimlik.py")


def modul_dizini_kur(tmp, ad, kayitlar, mutasyon=None, mutasyon_dosyasi=None):
    """Fikstur evlerini taniyan (ve istege bagli MUTANTLANMIS) bir ARAC DIZINI.

    Uretim koduna test kancasi eklemek yerine araclarin KOPYASI uzerinde calisilir:
    `EVLER` fikstur evleriyle ezilir, mutasyon adi verilen DOSYAYA uygulanir.
    Doner: (kapi_yolu, kur_yolu, dizin) ya da mutasyon capasi tam bir kez yoksa None."""
    dizin = os.path.join(tmp, "mod-" + ad)
    os.makedirs(dizin, exist_ok=True)
    hedef_dosya = mutasyon_dosyasi or "kapi_dagitim.py"
    for dosya in KOPYALANAN:
        kaynak = os.path.join(BURASI, dosya)
        with open(kaynak, encoding="utf-8") as f:
            metin = f.read()
        if mutasyon is not None and dosya == hedef_dosya:
            eski_p, yeni_p = mutasyon
            if metin.count(eski_p) != 1:
                return None
            metin = metin.replace(eski_p, yeni_p)
        if dosya == "kapi_dagitim.py":
            metin += ("\n\n# === TEST DIZINI: EVLER fikstur evleriyle EZILDI ===\n"
                      "EVLER = (\n"
                      + "".join("    " + repr(k) + ",\n" for k in kayitlar) + ")\n")
        with open(os.path.join(dizin, dosya), "w", encoding="utf-8") as f:
            f.write(metin)
    return (os.path.join(dizin, "kapi-dagitim-kapisi.py"),
            os.path.join(dizin, "kapi-dagitim-kur.py"), dizin)


def cip_girdisi(worktree_koku, komut):
    damga = "".join(k if k.isalnum() else "-" for k in worktree_koku)
    return {
        "tool_name": "Bash",
        "tool_input": {"command": komut},
        "cwd": worktree_koku,
        "transcript_path": "/Users/okan/.claude/projects/" + damga + "/oturum.jsonl",
    }


def tarayici_girdisi(ev):
    return {"tool_name": "mcp__Claude_Browser__navigate",
            "tool_input": {"url": "https://pruvo3d.com"}, "cwd": ev}


# ======================= ANA BATARYA (mutasyona TABI) =======================

def batarya(kok, etiket="", mutasyon=None, mutasyon_dosyasi=None):
    """V1..V3, V5, V6b, V8. `mutasyon` verilirse MUTANTLANMIS modulle kosar (K182)."""
    os.makedirs(kok, exist_ok=True)
    ev_kapali, _ = fikstur_ev(kok, "pruvo-advisor", "test-wt-1")   # tarayici KAPALI ev
    ev_acik, _ = fikstur_ev(kok, "pruvo-hasat")                    # tarayici ACIK ev
    ev_fc, _ = fikstur_ev(kok, "pruvo-jenerator")                  # fail-closed vakasi

    eski, _kaynak_adi, _gercek = eski_kopya()
    hedef = os.path.join(ev_kapali, ".claude", "mimar-icra-kapisi.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(eski)

    ev_kaynak = os.path.join(kok, "sahte-kaynak-evi")
    os.makedirs(os.path.join(ev_kaynak, "tools"), exist_ok=True)
    kayitlar = (
        ("KraL", KD.KAYNAK_KOK, "tools/mimar-icra-kapisi.py", "kaynak"),
        ("F_KAPALI", ev_kapali, ".claude/mimar-icra-kapisi.py", "shim"),
        ("F_ACIK", ev_acik, ".claude/mimar-icra-kapisi.py", "shim"),
        ("F_FC", ev_fc, ".claude/mimar-icra-kapisi.py", "shim"),
        ("F_KAYNAK", ev_kaynak, "tools/mimar-icra-kapisi.py", "kaynak"),
    )
    kuruldu = modul_dizini_kur(kok, "m" + etiket.replace("/", ""), kayitlar,
                               mutasyon, mutasyon_dosyasi)
    if kuruldu is None:
        iddia(etiket + "MUTASYON_CAPASI tam bir kez", True, False)
        return None
    kapi, kur, arac_dizini = kuruldu

    # --- V1: DONMUS eski kopya KIRMIZI ---
    so, _se, rc = kos([kapi, "--ev", ev_kapali])
    iddia(etiket + "V1a eski kopya rc=1", 1, rc)
    iddia(etiket + "V1b sinif ESKI_KOPYA", True, "SINIF=ESKI_KOPYA" in so)

    # --- V2: kurulum (uc canli fikstur) ve YESIL ---
    so2, _se, rc2 = kos([kur, "--ev", ev_kapali, "--uygula"])
    iddia(etiket + "V2a kurulum rc=0", 0, rc2)
    iddia(etiket + "V2b FIKSTUR 3/3", True, "HUKUM=KURULDU FIKSTUR=3/3" in so2)
    so3, _se, rc3 = kos([kapi, "--ev", ev_kapali])
    iddia(etiket + "V2c kurulum sonrasi rc=0", 0, rc3)
    iddia(etiket + "V2d sinif GUNCEL", True, "SINIF=GUNCEL" in so3)

    if not os.path.exists(hedef):
        iddia(etiket + "V2e shim dosyasi yerinde", True, False)
        return None
    with open(hedef, encoding="utf-8") as f:
        saglam = f.read()

    # --- V3: kurulu shim'e TEK kelimelik, UZUNLUK KORUYAN mutant ---
    bozuk = saglam.replace("ELLE DUZENLENMEZ", "ELLA DUZENLENMEZ")
    iddia(etiket + "V3a uzunluk korundu", len(saglam), len(bozuk))
    iddia(etiket + "V3b metin degisti", True, bozuk != saglam)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(bozuk)
    so4, _se, rc4 = kos([kapi, "--ev", ev_kapali])
    iddia(etiket + "V3c mutant rc=1", 1, rc4)
    iddia(etiket + "V3d sinif SHIM_BAYAT", True, "SINIF=SHIM_BAYAT" in so4)

    # --- V3e/f: GERI ALINCA YESILE DONER ---
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(saglam)
    so5, _se, rc5 = kos([kapi, "--ev", ev_kapali])
    iddia(etiket + "V3e geri alinca rc=0", 0, rc5)
    iddia(etiket + "V3f geri alinca GUNCEL", True, "SINIF=GUNCEL" in so5)

    # --- V8: IDEMPOTENS ---
    so6, _se, _rc = kos([kur, "--ev", ev_kapali, "--uygula"])
    iddia(etiket + "V8 ikinci kurulum ZATEN_GUNCEL", True, "HUKUM=ZATEN_GUNCEL" in so6)

    # --- V5: AYNI GOVDE, FARKLI EV, FARKLI HUKUM (dogru eve homelenme) ---
    kos([kur, "--ev", ev_acik, "--uygula"])
    acik_yol = os.path.join(ev_acik, ".claude", "mimar-icra-kapisi.py")
    if os.path.exists(acik_yol):
        so_a, se_a, _rc = kos([acik_yol], girdi=tarayici_girdisi(ev_acik))
        iddia(etiket + "V5a acik ev (pruvo-hasat) tarayici IZIN", False, deny_mi(so_a))
        iddia(etiket + "V5c shim izi stderr'de", True, "MIMAR-KAPISI shim" in se_a)
    else:
        iddia(etiket + "V5a acik ev (pruvo-hasat) tarayici IZIN", False, True)
        iddia(etiket + "V5c shim izi stderr'de", True, False)
    so_k, _se, _rc = kos([hedef], girdi=tarayici_girdisi(ev_kapali))
    iddia(etiket + "V5b kapali ev tarayici DENY", True, deny_mi(so_k))

    # --- V6b: FAIL-CLOSED — capa TAM BIR KEZ degilse exec YOK ---
    kos([kur, "--ev", ev_fc, "--uygula"])
    fc_yol = os.path.join(ev_fc, ".claude", "mimar-icra-kapisi.py")
    if os.path.exists(fc_yol):
        sahte = os.path.join(kok, "sahte-cift-capa.py")
        with open(sahte, "w", encoding="utf-8") as f:
            f.write(KD.CAPA_REPO + "\n" + KD.CAPA_REPO + "\n" + KD.CAPA_WT + "\n")
        with open(fc_yol, encoding="utf-8") as f:
            fc_metin = f.read()
        fc_metin = fc_metin.replace('KAYNAK = "' + KD.KAYNAK + '"',
                                    'KAYNAK = "' + sahte + '"')
        with open(fc_yol, "w", encoding="utf-8") as f:
            f.write(fc_metin)
        so_fc, _se, _rc = kos([fc_yol], girdi={"tool_name": "Bash",
                                               "tool_input": {"command": "ls"},
                                               "cwd": ev_fc})
        iddia(etiket + "V6b cift capa -> DENY", True, deny_mi(so_fc))
    else:
        iddia(etiket + "V6b cift capa -> DENY", True, False)

    # --- V10: KAYNAK EVI CAPA SOZLESMESI (capa 1'den saparsa BES EV kararir) ---
    kaynak_yol = os.path.join(ev_kaynak, "tools", "mimar-icra-kapisi.py")
    with open(KD.KAYNAK, encoding="utf-8") as f:
        govde = f.read()
    with open(kaynak_yol, "w", encoding="utf-8") as f:
        f.write(govde)
    so_k1, _se, rc_k1 = kos([kapi, "--ev", ev_kaynak])
    iddia(etiket + "V10a saglam govde rc=0", 0, rc_k1)
    iddia(etiket + "V10b sinif KAYNAK", True, "SINIF=KAYNAK " in so_k1)
    with open(kaynak_yol, "w", encoding="utf-8") as f:
        f.write(govde + "\n" + KD.CAPA_REPO + "\n")
    so_k2, _se, rc_k2 = kos([kapi, "--ev", ev_kaynak])
    iddia(etiket + "V10c cift capa rc=1", 1, rc_k2)
    iddia(etiket + "V10d sinif CAPA_KIRIK", True, "SINIF=CAPA_KIRIK" in so_k2)

    # --- V9: ESKI DAGITICI SHIM'IN UZERINE YAZAMAZ ---
    v9_shim_uzerine_yazma(os.path.join(kok, "v9"), arac_dizini, etiket)

    return {"ev_kapali": ev_kapali, "saglam": saglam, "eski": eski}


# ======================= MUTASYONA TABI OLMAYAN VAKALAR =======================

def v0_gercek_filo():
    """V0 — GERCEK evler, SALT OKUMA. Canli makinede kosar; CI'da OLCULEMEDI."""
    eksik = [ad for ad, kok, _g, _m in KD.EVLER if not os.path.isdir(kok)]
    if eksik:
        olculemedi("V0 gercek filo", "bu makinede olmayan evler: " + ",".join(eksik))
        return "(V0 OLCULEMEDI)"
    so, _se, rc = kos([KAPI, "--filo"])
    iddia("V0a gercek filo rc (bugunku taban)", 1, rc)
    iddia("V0b KraL SINIF=KAYNAK", True, "EV=KraL SINIF=KAYNAK" in so)
    iddia("V0c bes ev ESKI_KOPYA", 5, so.count("SINIF=ESKI_KOPYA"))
    return so


def v6ac(kok):
    """V6a kaynak YOK -> DENY · V6c tanimsiz ev -> rc=1."""
    ev, _ = fikstur_ev(kok, "pruvo-bot")
    yol = os.path.join(ev, ".claude", "mimar-icra-kapisi.py")
    metin = KD.shim_metni("F_YOK", ev).replace(
        'KAYNAK = "' + KD.KAYNAK + '"',
        'KAYNAK = "' + os.path.join(kok, "olmayan-kaynak.py") + '"')
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    so, _se, rc = kos([yol], girdi={"tool_name": "Bash",
                                    "tool_input": {"command": "ls"}, "cwd": ev})
    iddia("V6a kaynak yoksa DENY", True, deny_mi(so))
    iddia("V6a2 rc=0 (kanca sozlesmesi korunur)", 0, rc)
    _so, _se, rc2 = kos([KAPI, "--ev", os.path.join(kok, "hic-boyle-ev-yok")])
    iddia("V6c tanimsiz ev rc=1 (fail-closed)", 1, rc2)


def v9_shim_uzerine_yazma(kok, arac_dizini=None, etiket=""):
    """V9 — ESKI DAGITICI SHIM'IN UZERINE YAZAMAZ (yeniden bayatlama yolu kapali).

    `tools/mimar-kapi-kur.py:_yaz` merkezi yazicidir; butun enjeksiyon modlari oradan
    gecer. Kol iki yonlu olculur: shim'in uzerine DONMUS govde YAZILAMAZ (RuntimeError),
    ama shim'in uzerine SHIM yazilabilir ve alakasiz dosya etkilenmez."""
    import importlib.util
    dizin = arac_dizini or BURASI
    yol_kur = os.path.join(dizin, "mimar-kapi-kur.py")
    spec = importlib.util.spec_from_file_location(
        "mimar_kapi_kur_test_" + str(abs(hash(dizin))), yol_kur)
    modul = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modul)
    except Exception as hata:
        iddia(etiket + "V9 dagitici import", True, "import DUSTU: " + repr(hata))
        return
    os.makedirs(kok, exist_ok=True)
    hedef = os.path.join(kok, "mimar-icra-kapisi.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(KD.shim_metni("F_V9", os.path.join(kok, "pruvo-advisor")))

    engellendi = False
    try:
        modul._yaz(hedef, "# DONMUS GOVDE KOPYASI\nprint('eski')\n")
    except RuntimeError:
        engellendi = True
    iddia(etiket + "V9a shim uzerine DONMUS govde YAZILAMAZ", True, engellendi)
    with open(hedef, encoding="utf-8") as f:
        iddia(etiket + "V9b shim dosyasi DEGISMEDI", True, KD.SHIM_IMZASI in f.read())

    yeni_shim = KD.shim_metni("F_V9B", os.path.join(kok, "pruvo-bot"))
    modul._yaz(hedef, yeni_shim)
    with open(hedef, encoding="utf-8") as f:
        iddia(etiket + "V9c shim uzerine SHIM yazilabilir", yeni_shim, f.read())

    alakasiz = os.path.join(kok, "settings.json")
    modul._yaz(alakasiz, "{}\n")
    iddia(etiket + "V9d alakasiz dosya etkilenmez", True, os.path.exists(alakasiz))


def v7_macit_blokaji(kok, eski):
    """V7 — MaCiT'in ASIL BLOKAJI: cip oturumunda K318 ROL kolu.
    Eski DONMUS kopyada ROL ekseni YOK -> cip'te bile RED. Shim'de govde canli -> CIP."""
    if "rol_ekseni" in eski:
        olculemedi("V7 MaCiT blokaji",
                   "elde DONMUS-ve-ROL-KOLSUZ govde YOK (CI vekili ROL kolunu tasiyor)")
        return None, None
    ev, wt = fikstur_ev(kok, "pruvo-hasat-cip", "cip-wt")
    yol = os.path.join(ev, ".claude", "mimar-icra-kapisi.py")
    girdi = cip_girdisi(wt, "python3 " + os.path.join(wt, "olcum.py"))

    with open(yol, "w", encoding="utf-8") as f:
        f.write(eski)
    so_eski, _se, _rc = kos([yol], girdi=girdi)

    with open(yol, "w", encoding="utf-8") as f:
        f.write(KD.shim_metni("F_CIP", ev))
    so_yeni, se_yeni, _rc = kos([yol], girdi=girdi)

    iddia("V7a eski DONMUS kopya cip'i REDDEDER", True, deny_mi(so_eski))
    iddia("V7b shim cip'e IZIN VERIR", False, deny_mi(so_yeni))
    iddia("V7c shim izinde CIP rolu gorunur", True, "CIP(" in se_yeni)
    return so_eski, so_yeni


# ============================== MUTASYON ==============================
# (ad, aciklama, (capa, yeni), HEDEF KOL) — hedef None ise KONTROL mutantidir.
MUTANTLAR = (
    ("M1_boyut_ekseni",
     "sha esitligi yerine BOYUT esitligi (brief'in ACIKCA reddettigi eksen)",
     ("    if kurulu == beklenen:\n        return (GUNCEL, kurulu, beklenen)",
      "    if len(icerik) == len(beklenen_metin):\n"
      "        return (GUNCEL, kurulu, beklenen)"),
     "V3c"),
    ("M2_capa_kolu_kapali",
     "shim'in capa-sayisi fail-closed kolu kaldirilir",
     ("if _metin.count(CAPA_REPO) != 1 or _metin.count(CAPA_WT) != 1:",
      "if False:"),
     "V6b"),
    ("M3_ev_capasi_uygulanmaz",
     "shim REPO_ONEKI capasini UYGULAMAZ (kapi YANLIS eve homelenir)",
     ("_metin = _metin.replace(CAPA_REPO, ",
      "_metin = _metin.replace('K304-CAPA-BULUNMAZ', "),
     "V2b"),
    ("M4_KONTROL_yorum",
     "KONTROL: yalniz bir yorum cumlesi degisir — hicbir kol OLMEMELI",
     ("Bu modul TEK KAYNAKTIR", "Bu modul (kontrol mutanti) TEK KAYNAKTIR"),
     None),
    ("M6_kaynak_capa_kolu_kapali",
     "kaynak evinde CAPA SOZLESMESI olcumu sokulur (bes evi karartan kirilma gorunmez)",
     ("        if capa_sayilari(icerik) != (1, 1):\n"
      "            return (CAPA_KIRIK, kurulu, None)\n", ""),
     "V10d"),
    ("M5_shim_koruma_kapali",
     "eski dagiticinin SHIM KORUNDU kolu sokulur (yeniden bayatlama yolu acilir)",
     ("    _shim_uzerine_yazma_kapisi(yol, metin)\n", ""),
     "V9a", "mimar-kapi-kur.py"),
)


def mutasyon_bataryasi(tmp):
    olcum = []
    for kayit in MUTANTLAR:
        ad, aciklama, capa, hedef_kol = kayit[:4]
        hedef_dosya = kayit[4] if len(kayit) > 4 else None
        onceki = list(SONUC)
        del SONUC[:]
        try:
            batarya(os.path.join(tmp, "mut-" + ad), etiket=ad + "/", mutasyon=capa,
                    mutasyon_dosyasi=hedef_dosya)
        except Exception as hata:
            SONUC.append((ad + "/KOSUM_COKTU", False, "kosum", repr(hata)))
        dusenler = [s[0] for s in SONUC if not s[1]]
        del SONUC[:]
        SONUC.extend(onceki)
        olcum.append((ad, "OLDU" if dusenler else "YASADI", aciklama, hedef_kol,
                      dusenler))
    return olcum


def main(argv):
    mutasyon = "--mutasyon" in argv
    tmp = tempfile.mkdtemp(prefix="pruvo-k304-")
    try:
        v0 = v0_gercek_filo()
        d = batarya(os.path.join(tmp, "taban"))
        v6ac(os.path.join(tmp, "fc"))
        if d:
            v7_macit_blokaji(os.path.join(tmp, "v7"), d["eski"])

        dusen = [s for s in SONUC if not s[1]]
        print("=== VAKALAR ===")
        for ad, gecti, bekl, gozl in SONUC:
            if not gecti:
                print("  DUSTU " + ad + " beklenen=" + repr(bekl) +
                      " gozlenen=" + repr(gozl))
        print("IDDIA=" + str(len(SONUC)) + " DUSEN=" + str(len(dusen))
              + " OLCULEMEDI=" + str(len(OLCULEMEDI)))
        for satir_ in OLCULEMEDI:
            print("  OLCULEMEDI " + satir_)
        rc = 1 if dusen else 0

        if mutasyon:
            print("=== MUTASYON ===")
            olcum = mutasyon_bataryasi(tmp)
            oldu = 0
            atif = 0
            for ad, hal, _acik, hedef_kol, dusenler in olcum:
                beklenen_hal = "YASADI" if hedef_kol is None else "OLDU"
                if hal == "OLDU":
                    oldu += 1
                dogru = (hal == beklenen_hal)
                if not dogru:
                    rc = 1
                hedef_tuttu = True
                if hedef_kol:
                    hedef_tuttu = any(hedef_kol in x for x in dusenler)
                    if hedef_tuttu:
                        atif += 1
                    else:
                        rc = 1
                print(("  " if (dogru and hedef_tuttu) else "  X ") + ad + " -> " + hal
                      + " (beklenen " + beklenen_hal + ")"
                      + (" hedef=" + hedef_kol if hedef_kol else " KONTROL")
                      + (" olen=" + ",".join(dusenler[:6]) if dusenler else ""))
            print("MUTANT=" + str(len(MUTANTLAR)) + " OLDU=" + str(oldu)
                  + " HEDEF_KOL_ATFI=" + str(atif) + "/"
                  + str(sum(1 for m in MUTANTLAR if m[3]))
                  + " KONTROL_YASADI="
                  + str(sum(1 for a, h, _c, k, _d in olcum
                            if k is None and h == "YASADI")) + "/"
                  + str(sum(1 for m in MUTANTLAR if m[3] is None)))

        print("--- V0 gercek filo ciktisi ---")
        print(v0.strip())
        print("HUKUM=" + ("YESIL" if rc == 0 else "KIRMIZI"))
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
