#!/usr/bin/env python3
"""K304-BOOTSTRAP KABUL BATARYASI — kapi dagitim KURUCUSUNUN adli serbest kolu.

OLCULEN ARIZA (28 Agu 2026, KraL-HasatKapiKurulum-28Agu): `kapi-dagitim-kur.py --ev
<kardes_ev>` HICBIR evde mimar eliyle kosturulamiyordu — KraL'da R2 (argumanlarda repo
DISI yol), kardes evde R2 + F (kurucunun KENDISI o evin agacinin disinda). Yani YENI
kapiyi kuracak komut, KURULMAMIS/BAYAT eski kapi tarafindan bloke ediliyordu.

🔴 MEKANIZMA SENTETIK EVLERDE OLCULUR — CANLI MAKINEYE BAGLI DEGILDIR.
Batarya iki sentetik ev kurar (gercek `git init` + gercek `git worktree add`), kapi
govdesini o evlere HOMELER ve vakalari orada kosturur. Boylece ayni olcum hem bu
makinede hem GitHub kosucusunda YAPILIR. Canli filo (gercek kardes evler + kurulu shim)
AYRI ve ISIMLI bir koldur: evler yoksa `OLCULEMEDI` basar — sessiz yesil DONMEZ
([[olculemedi-bypass-degil-menzil-daraltmasi]]).

NE OLCULUR:
  ① kurucu cagrisi serbest kolda tanimli — R2 kolu (kaynak evi) + F kolu (kardes ev)
  ② MUTANT: tanim dusunce cagri RED'e doner; mutantin HEDEF KOLU oldurdugu, denyin
     GEREKCESI okunarak AYRICA kanitlanir (K182)
  ③ muafiyet DIZGE eslemesiyle degil CAGRI YERIYLE olculur (V4B + M3)
  ④ GEVSEME YOK: muafiyet yalniz bu kurucuyu kapsar (V2·V3·V4A·V4B·V5·V6·V7)

rc: 0 = tum vakalar + mutantlar + KONTROL beklendigi gibi · 1 = en az biri dustu.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(BURASI, "mimar-icra-kapisi.py")

# Kanonik govdedeki iki EV CAPASI — shim bunlari eve cevirir; sentetik ev fiksturu AYNI
# donusumu uygular (ikinci bir renderer YAZILMAZ).
CAPA_REPO = 'REPO_ONEKI = "/Users/okan/dev/pruvo/"'
CAPA_WT = 'GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"'

sys.path.insert(0, BURASI)
import kapi_dagitim as KD  # noqa: E402
from mimar_kimlik import _proje_damgasi  # noqa: E402

# Kayitli bir EV KOKU — muafiyetin izinli kumesi bundan turer. Dizinin DISKTE olmasi
# GEREKMEZ (kural yol kumesini olcer, dosya sistemini degil) — bu yuzden CI'da da gecerli.
KAYITLI_EV = None
for _ad, _kok, _g, _m in KD.EVLER:
    if _ad == "MaCiT":
        KAYITLI_EV = os.path.normpath(_kok)


def _git(kok, *argv):
    subprocess.run(["git", "-C", kok] + list(argv), check=True,
                   capture_output=True, text=True)


def sentetik_ev(tmp, ad, kurucu_tasi):
    """GERCEK git deposu + GERCEK worktree olan sentetik bir ev kurar.

    Doner: (ev_koku, cip_koku). ROL EKSENI (K318) `.git/worktrees` kaydini okudugu icin
    worktree TAKLIT EDILMEZ, gercekten acilir.

    kurucu_tasi=True ise ev, kanonik kurucunun bir kopyasini KENDI agacinda tasir ve
    modul kopyasinin KAYNAK_KOK'u bu eve civilenir -> R2 kolu (kurucu repo ICINDE,
    arguman DISARIDA) burada olculur. False ise ev, kurucuyu DISARIDAN cagirir -> F kolu.
    """
    kok = os.path.join(tmp, ad)
    os.makedirs(os.path.join(kok, "tools"))
    _git(os.path.dirname(kok) if False else tmp, "init", "-q", ad)
    _git(kok, "config", "user.email", "t@t")
    _git(kok, "config", "user.name", "t")
    with open(os.path.join(kok, "tohum.txt"), "w") as f:
        f.write("x\n")
    _git(kok, "add", "-A")
    _git(kok, "commit", "-qm", "tohum")
    cip = os.path.join(kok, ".claude", "worktrees", "cip-" + ad)
    os.makedirs(os.path.dirname(cip), exist_ok=True)
    _git(kok, "worktree", "add", "-q", "-b", "dal-" + ad, cip)

    shutil.copy2(os.path.join(BURASI, "mimar_kimlik.py"),
                 os.path.join(kok, "tools", "mimar_kimlik.py"))
    with open(os.path.join(BURASI, "kapi_dagitim.py"), encoding="utf-8") as f:
        modul = f.read()
    if kurucu_tasi:
        # KAYNAK_KOK'u bu eve civile: kanonik kurucu bu evin AGACINDA yasiyor sayilir.
        modul = modul.replace('CANLI_KOK = "/Users/okan/dev/pruvo"',
                              'CANLI_KOK = ' + repr(kok))
        with open(os.path.join(kok, "tools", "kapi-dagitim-kur.py"), "w") as f:
            f.write("# sentetik kurucu (yol capasi; kapi yalnizca YOLU cozer)\n")
    else:
        modul = modul.replace('CANLI_KOK = "/Users/okan/dev/pruvo"',
                              'CANLI_KOK = ' + repr(os.path.join(tmp, "kaynak-ev")))
    with open(os.path.join(kok, "tools", "kapi_dagitim.py"), "w") as f:
        f.write(modul)
    return kok, cip


def ev_govdesi(kaynak_yolu, hedef_yolu, ev_koku):
    """Kapi govdesini bir eve HOMELER — shim'in yaptigi donusumun BIREBIR aynisi."""
    with open(kaynak_yolu, encoding="utf-8") as f:
        metin = f.read()
    if metin.count(CAPA_REPO) != 1 or metin.count(CAPA_WT) != 1:
        raise RuntimeError("EV CAPALARI TAM BIR KEZ degil — fikstur kurulamaz")
    metin = metin.replace(CAPA_REPO, 'REPO_ONEKI = "' + ev_koku + '/"')
    metin = metin.replace(CAPA_WT,
                          'GIT_WORKTREE_KAYIT = "' + ev_koku + '/.git/worktrees"')
    with open(hedef_yolu, "w", encoding="utf-8") as f:
        f.write(metin)
    return hedef_yolu


def yuk(komut, cwd, cip_koku=None):
    g = {"tool_name": "Bash", "tool_input": {"command": komut}, "cwd": cwd}
    if cip_koku:
        g["transcript_path"] = ("/Users/okan/.claude/projects/"
                                + _proje_damgasi(cip_koku) + "/oturum.jsonl")
    return g


def kos(kapi, girdi, ek_yol):
    # Govde kopyalari gecici dizinde yasar; `mimar_kimlik` import'u kendi dizinini
    # sys.path'te sanar. PYTHONPATH verilmezse kopya IMPORT'ta coker, stdout BOS kalir ve
    # "izin" gibi OKUNUR — mutant, oldurmedigi bir kolu oldurmus GORUNUR.
    cevre = dict(os.environ)
    cevre["PYTHONPATH"] = ek_yol + os.pathsep + cevre.get("PYTHONPATH", "")
    p = subprocess.run([sys.executable, kapi], input=json.dumps(girdi),
                       capture_output=True, text=True, timeout=60, env=cevre)
    if not p.stdout.strip():
        # BOS stdout tek basina IZIN DEGILDIR; yalniz rc=0 ise izindir. Aksi halde kapi
        # COKMUSTUR (kapinin kendi 'stdout bos => allow' fail-open korlugu dersi).
        if p.returncode != 0:
            return ("COKTU", (p.stderr or "").strip()[-200:])
        return ("izin", "")
    try:
        veri = json.loads(p.stdout)
    except Exception:
        return ("COZULEMEDI", p.stdout[:200])
    h = veri.get("hookSpecificOutput") or {}
    if h.get("permissionDecision") == "deny":
        return ("deny", h.get("permissionDecisionReason") or "")
    return ("izin", "")


MUTANTLAR = (
    ("M1_R2_KOLU_DUSER",
     "if disari and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "if False and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "V1_R2_KAYNAK_EVI", "repo DIŞINA çözülen"),
    ("M2_F_KOLU_DUSER",
     "if not repo_ici(betik, cwd) and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "if False and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "V1F_F_KARDES_EV", "repo DIŞINDAKİ bir betiği"),
    ("M3_DIZGE_ESLEMESINE_DONER",
     "if betik is None or _coz(betik, cwd) != kurucu:",
     "if betik is None or os.path.basename(betik) != os.path.basename(kurucu):",
     "V4B_AGAC_ICI_TAKLIT", None),
)

KONTROL_MUTANTI = ("KONTROL_YORUM",
                   "# E2/R2) YOL TARAMASI",
                   "# E2/R2) YOL TARAMASI (kontrol mutanti — davranis DEGISMEZ)")


def vakalar(kaynak_ev, kaynak_cip, kardes_ev, kardes_cip):
    kurucu = os.path.join(kaynak_ev, "tools", "kapi-dagitim-kur.py")
    taklit = os.path.join(kaynak_ev, "tools", "sahte-kur.py")
    agac_ici_taklit = os.path.join(kaynak_cip, "tools", "kapi-dagitim-kur.py")
    return (
        # ① SERBEST KOL — iki cagri yeri de ADIYLA olculur
        ("V1_R2_KAYNAK_EVI", "kaynak",
         yuk("python3 " + kurucu + " --ev " + KAYITLI_EV, kaynak_cip, kaynak_cip),
         "izin"),
        ("V1F_F_KARDES_EV", "kardes",
         yuk("python3 " + kurucu + " --ev " + KAYITLI_EV, kardes_cip, kardes_cip),
         "izin"),
        # ④ GEVSEME YOK
        ("V2_ANA_OTURUM", "kaynak",
         yuk("python3 " + kurucu + " --ev " + KAYITLI_EV, kaynak_ev), "deny"),
        ("V3_KAYITSIZ_EV", "kaynak",
         yuk("python3 " + kurucu + " --ev /private/tmp/sahte-ev", kaynak_cip,
             kaynak_cip), "deny"),
        ("V4A_BASKA_ADLI_ARAC", "kaynak",
         yuk("python3 " + taklit + " --ev " + KAYITLI_EV, kaynak_cip, kaynak_cip),
         "deny"),
        # 🔴 V4B — MUAFIYETIN CAPASI: kurucunun WORKTREE KOPYASI muafiyeti DEVRALMAZ.
        # Kopya repo ICINDEDIR, yani 2. adim onu ELEMEZ; onu eleyen TEK sey 1. adimdaki
        # KANONIK YOL TAM ESITLIGIDIR. Basename eslemesine donen bir kapi burada IZIN
        # verirdi — o an her dal, kurucuyu kendi agacinda degistirip kardes evlere yazma
        # yetkisi devsirebilirdi.
        ("V4B_AGAC_ICI_TAKLIT", "kaynak",
         yuk("python3 " + agac_ici_taklit + " --ev " + KAYITLI_EV, kaynak_cip,
             kaynak_cip), "deny"),
        ("V5_SATIR_ICI", "kaynak",
         yuk('python3 -c "1" ' + kurucu, kaynak_cip, kaynak_cip), "deny"),
        ("V6_TEHLIKELI_ENV", "kaynak",
         yuk("PYTHONPATH=/private/tmp python3 " + kurucu + " --ev " + KAYITLI_EV,
             kaynak_cip, kaynak_cip), "deny"),
        ("V7_REPO_DISI_BETIK", "kaynak",
         yuk("python3 /private/tmp/x.py", kaynak_cip, kaynak_cip), "deny"),
        ("KONTROL_LS", "kaynak", yuk("ls", kaynak_cip, kaynak_cip), "izin"),
    )


def batarya(kapilar, yollar, vaka_listesi, basli=False):
    dusen, gozlem = [], {}
    for ad, secici, girdi, beklenen in vaka_listesi:
        h, neden = kos(kapilar[secici], girdi, yollar[secici])
        gozlem[ad] = (h, neden)
        ok = (h == beklenen)
        if not ok:
            dusen.append(ad)
        if basli:
            print("  " + ad + " beklenen=" + beklenen + " gozlenen=" + h
                  + ("" if ok else "   <== DUSTU"))
    return dusen, gozlem


def canli_filo_kolu():
    """AYRI, ISIMLI kol: gercek kardes evdeki KURULU shim'i surer.

    Kurucunun kendi 'FIKSTUR=3/3' cumlesi ONUN IDDIASIDIR, benim olcumum degil
    ([[aracin-teshis-cumlesi-olcum-degil]]). Evler yoksa (CI) OLCULEMEDI — sessiz yesil
    DONMEZ, ve bu kol rc'yi tek basina YESILE cevirmez."""
    yol = KD.kurulu_yol("/Users/okan/dev/pruvo-hasat", ".claude/mimar-icra-kapisi.py")
    kayit = "/Users/okan/dev/pruvo-hasat/.git/worktrees"
    if not os.path.exists(yol) or not os.path.isdir(kayit):
        print("  CANLI_FILO=OLCULEMEDI (kardes ev bu makinede yok — CI kosucusu)")
        return []
    cip = None
    for ad in sorted(os.listdir(kayit)):
        try:
            with open(os.path.join(kayit, ad, "gitdir"), encoding="utf-8") as f:
                icerik = f.read().strip()
        except OSError:
            continue
        if icerik:
            cip = os.path.normpath(os.path.dirname(icerik))
            break
    if cip is None:
        print("  CANLI_FILO=OLCULEMEDI (kayitli worktree yok)")
        return []
    vaka = (
        ("S1_ALLOW_ls", yuk("ls", "/Users/okan/dev/pruvo-hasat"), "izin"),
        ("S2_DENY_satir_ici", yuk('python3 -c "1"', cip, cip), "deny"),
        ("S3_DENY_repo_disi", yuk("python3 /private/tmp/x.py", cip, cip), "deny"),
        ("S4_DENY_ana_oturum",
         yuk("python3 /Users/okan/dev/pruvo-hasat/tools/a.py",
             "/Users/okan/dev/pruvo-hasat"), "deny"),
        ("S5_CIP_arac_serbest", yuk("python3 " + cip + "/tools/a.py", cip, cip), "izin"),
    )
    print("  KURULU_SHIM=" + yol + " BAYT=" + str(os.path.getsize(yol)))
    dusen = []
    for ad, girdi, beklenen in vaka:
        h, _n = kos(yol, girdi, BURASI)
        ok = (h == beklenen)
        if not ok:
            dusen.append(ad)
        print("    " + ad + " beklenen=" + beklenen + " gozlenen=" + h
              + ("" if ok else "   <== DUSTU"))
    return dusen


def main():
    if KAYITLI_EV is None:
        print("HUKUM=OLCULEMEDI (kapi_dagitim.EVLER'de MaCiT kaydi yok)")
        return 1
    # 🔴 realpath ZORUNLU: macOS'ta /var -> /private/var sembolik baglantidir. git,
    # worktree kaydina COZULMUS yolu yazar; fikstur cozulmemis yolu kullanirsa ROL
    # EKSENI'nin proje damgasi TUTMAZ ve vaka, kapinin kusuru gibi gorunen bir FIKSTUR
    # kusurundan duser. (Bu, ilk kosumda birebir olculdu.)
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="k304-bootstrap-"))
    try:
        kaynak_ev, kaynak_cip = sentetik_ev(tmp, "kaynak-ev", True)
        kardes_ev, kardes_cip = sentetik_ev(tmp, "kardes-ev", False)
        with open(os.path.join(kaynak_ev, "tools", "sahte-kur.py"), "w") as f:
            f.write("# ayni dizinde, BASKA adli arac\n")
        os.makedirs(os.path.join(kaynak_cip, "tools"), exist_ok=True)
        with open(os.path.join(kaynak_cip, "tools", "kapi-dagitim-kur.py"), "w") as f:
            f.write("# kurucunun AGAC ICI (worktree) kopyasi\n")

        kapilar = {
            "kaynak": ev_govdesi(KAPI, os.path.join(tmp, "g-kaynak.py"), kaynak_ev),
            "kardes": ev_govdesi(KAPI, os.path.join(tmp, "g-kardes.py"), kardes_ev),
        }
        yollar = {"kaynak": os.path.join(kaynak_ev, "tools"),
                  "kardes": os.path.join(kardes_ev, "tools")}
        vaka_listesi = vakalar(kaynak_ev, kaynak_cip, kardes_ev, kardes_cip)

        print("FIKSTUR kaynak_ev=" + kaynak_ev)
        print("FIKSTUR kardes_ev=" + kardes_ev)
        print("FIKSTUR kayitli_ev_capasi=" + KAYITLI_EV)
        print("=== TABAN (sentetik evler — CI'da da kosar) ===")
        dusen, _g = batarya(kapilar, yollar, vaka_listesi, basli=True)
        print("TABAN VAKA=" + str(len(vaka_listesi)) + " DUSEN=" + str(len(dusen)))
        if dusen:
            print("HUKUM=TABAN_KIRMIZI " + ",".join(dusen))
            return 1

        with open(KAPI, encoding="utf-8") as f:
            temiz = f.read()

        print("=== MUTANTLAR (hedef-kol atifli) ===")
        olen = atif_tam = 0
        for ad, eski, yeni, hedef, atif in MUTANTLAR:
            if temiz.count(eski) != 1:
                print("  " + ad + " CAPA_TUTMADI (kaynakta " + str(temiz.count(eski))
                      + " kez) — kapsam sessizce daralmaz, RED")
                return 1
            mut = os.path.join(tmp, ad + ".py")
            with open(mut, "w", encoding="utf-8") as f:
                f.write(temiz.replace(eski, yeni))
            mk = {
                "kaynak": ev_govdesi(mut, os.path.join(tmp, ad + "-k.py"), kaynak_ev),
                "kardes": ev_govdesi(mut, os.path.join(tmp, ad + "-s.py"), kardes_ev),
            }
            md, mg = batarya(mk, yollar, vaka_listesi)
            oldu = hedef in md
            olen += 1 if oldu else 0
            # K182 — HEDEF KOL ATFI: mutant 'bir sey kirmadi', TAM O KOLU kirdi.
            atif_ok = (atif in (mg[hedef][1] or "")) if atif else oldu
            atif_tam += 1 if atif_ok else 0
            print("  " + ad + " hedef=" + hedef + " oldu=" + ("EVET" if oldu else "HAYIR")
                  + " hedef_kol_atfi=" + ("TAM" if atif_ok else "TUTMADI")
                  + " yan_dusen=" + ",".join(a for a in md if a != hedef))
            if not oldu or not atif_ok:
                print("HUKUM=MUTANT_YASADI " + ad)
                return 1

        kon = os.path.join(tmp, "kontrol.py")
        with open(kon, "w", encoding="utf-8") as f:
            f.write(temiz.replace(KONTROL_MUTANTI[1], KONTROL_MUTANTI[2], 1))
        kk = {"kaynak": ev_govdesi(kon, os.path.join(tmp, "kon-k.py"), kaynak_ev),
              "kardes": ev_govdesi(kon, os.path.join(tmp, "kon-s.py"), kardes_ev)}
        kd, _ = batarya(kk, yollar, vaka_listesi)
        print("  " + KONTROL_MUTANTI[0] + " dusen=" + str(len(kd)) + " (YESIL kalmali)")
        if kd:
            print("HUKUM=KONTROL_KIRMIZI " + ",".join(kd))
            return 1

        print("=== CANLI FILO (ayri kol; CI'da OLCULEMEDI) ===")
        canli_dusen = canli_filo_kolu()
        if canli_dusen:
            print("HUKUM=CANLI_FILO_KIRMIZI " + ",".join(canli_dusen))
            return 1

        print("VAKA=" + str(len(vaka_listesi)) + " DUSEN=0 MUTANT_OLEN=" + str(olen)
              + "/" + str(len(MUTANTLAR)) + " ATIF=" + str(atif_tam) + "/"
              + str(len(MUTANTLAR)) + " KONTROL=YESIL")
        print("HUKUM=GECTI")
        return 0
    finally:
        for _ad in ("kaynak-ev", "kardes-ev"):
            _k = os.path.join(tmp, _ad)
            if os.path.isdir(_k):
                subprocess.run(["git", "-C", _k, "worktree", "prune"],
                               capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print("GECICI_SILINDI=" + str(not os.path.exists(tmp)) + " YOL=" + tmp)


if __name__ == "__main__":
    sys.exit(main())
