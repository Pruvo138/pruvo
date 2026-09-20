#!/usr/bin/env python3
"""KABUL + KOK NEDEN olcumu: `mimar-icra-kapisi.py` KARDES EV kolu (19 Eyl 2026).

ARIZA (olculdu 19 Eyl, MaCiT cipleri — mimar-posta-kutusu.md):
    CIP, `pruvo/.claude/worktrees/...` altinda (KraL govdesi kosar):
        python3 /Users/okan/dev/pruvo-hasat/olcum/hasat_gorsel_indir.py --marka X
        -> DENY (R2: repo DISINA cozulen yol)
    AYNI GUN, AYNI SINIF IS — Sony pilot dilimi, oturum koku /Users/okan/dev/pruvo-hasat
    (MaCiT SHIM'i kosar; shim REPO_ONEKI'yi kendi evine cevirir):
        python3 olcum/hasat_ekle.py ...   -> ALLOW (hedef O EVDE repo ICI)
Yani hukum ISE degil OTURUMUN ACILDIGI EVE bagliydi. Bu batarya iki sey yapar:
  (A) KOK NEDEN TABLOSU — ayni cagriyi KraL govdesi ve MaCiT-shim'i ESDEGERI uzerinde
      kosturur; "ev ekseni" farkini SAYIYLA gosterir (tahmin degil, olcum).
  (B) KABUL VAKALARI — K-KARDES-EV kolunun davranisi: cip ACIK, ANA KAPALI, menzil
      kayitli ev kokleriyle SINIRLI, `python3 -c` her rolde KAPALI, ve MENZIL ACIGI
      (sarmalayici sinifi) ADIYLA raporlanir.
  (C) MUTANT — izin kolunu ANA role genisleten kopya: ANA kontrol vakasi KIRMIZI yanar.

HERMETIK: kendi gecici worktree'sini kurar (git kaydi), sahte shim'i tempdir'e yazar,
bitince HEPSINI siler. `/Users/okan/dev/pruvo-hasat` diskte OLMAK ZORUNDA DEGILDIR —
kural `kapi_dagitim.EVLER` tablosundan turer, dosya VARLIGI olculmez (CI'da da kosar).

Kullanim:
    python3 tools/kardes-ev-kapisi-test.py            # repodaki kapiyi olcer
    python3 tools/kardes-ev-kapisi-test.py /baska/tools
Cikis: 0 = her vaka gecti, 1 = en az bir vaka KIRMIZI ya da KOSULAMADI.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gecici_worktree  # noqa: E402

TOOLS = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(
    os.path.abspath(__file__))
ICRA = os.path.join(TOOLS, "mimar-icra-kapisi.py")
# Kardes ev koku: TEK KAYNAK kapi_dagitim.EVLER — burada ikinci liste tutulmaz.
sys.path.insert(0, TOOLS)
import kapi_dagitim as KD  # noqa: E402

# 🔴 19 EYL 2026 22:29Z ARIZASI (run 35473498152, main `9e1dfecb`): burada
# `REPO = "/Users/okan/dev/pruvo"` SABITI duruyordu. Yerel Mac'te 19/19 YESIL,
# GitHub kosucusunda ILK zamanlanmis koşumda KIRMIZI:
#     CEVRE: gecici worktree kurulamadi -> fatal: cannot change to
#     '/Users/okan/dev/pruvo': No such file or directory
# Bu dosyanin kendi docstring'i "CI'da da kosar" diyordu; beyan OLCULMEMISTI.
# Kok artik TEK KAYNAKTAN turer: `kapi_dagitim.KAYNAK_KOK` canli makinede
# `/Users/okan/dev/pruvo`, kosucuda checkout kokudur (ikinci sabit BURADA TUTULMAZ).
# Sinifin nobetcisi: `tools/ci-sabit-canli-yol-kapisi.py`.
REPO = os.path.normpath(KD.KAYNAK_KOK)

KARDES_EV = None
for _ad, _kok, _yol, _mod in KD.EVLER:
    if os.path.normpath(_kok) != os.path.normpath(KD.KAYNAK_KOK):
        KARDES_EV = os.path.normpath(_kok)
        break

TRANSCRIPT_KOK = os.path.expanduser("~/.claude/projects")
DISARI = os.path.join(tempfile.gettempdir(), "pruvo-kardes-ev-disari")


def damga(yol):
    """Kapidan BAGIMSIZ damga yazimi (ASCII): alfanumerik olmayan her karakter '-'."""
    return "".join(k if (("a" <= k <= "z") or ("A" <= k <= "Z") or ("0" <= k <= "9"))
                   else "-" for k in yol)


def kapiya_ver(kapi, komut, cwd, payload_eki):
    """PreToolUse JSON'unu stdin'den besler. Doner: (karar, stderr)."""
    if not os.path.exists(kapi):
        return "EKSIK-KANCA", kapi
    yuk = {
        "session_id": "kardes-ev-test",
        "cwd": cwd,
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut},
    }
    yuk.update(payload_eki or {})
    ortam = dict(os.environ)
    for anahtar in ("CLAUDE_PROJECT_DIR", "PRUVO_ISCI_KOSUMU", "PRUVO_CLAUDE_ISCI_IZNI"):
        ortam.pop(anahtar, None)
    sonuc = subprocess.run([sys.executable, kapi], input=json.dumps(yuk),
                           capture_output=True, text=True, env=ortam)
    if sonuc.returncode != 0:
        return "COKTU", (sonuc.stderr or "")[:200]
    cikti = (sonuc.stdout or "").strip()
    if not cikti:
        if "MIMAR-KAPISI allow" in (sonuc.stderr or ""):
            return "allow", sonuc.stderr or ""
        return "IZSIZ-ALLOW", sonuc.stderr or ""
    try:
        veri = json.loads(cikti)
    except Exception:                                       # noqa: BLE001
        return "PARSE-HATASI", cikti[:200]
    hso = veri.get("hookSpecificOutput") or {}
    return hso.get("permissionDecision", "allow"), (hso.get("permissionDecisionReason") or "")


def shim_yaz(hedef_dosya, ev_koku):
    """MaCiT/HocA evindeki SHIM'in esdegeri: govdeyi okur, capayi EVE cevirir, exec eder.
    (Kalip birebir `kapi_dagitim.py` shim'inden alinmistir — ikinci bir kapi govdesi
    yazilmaz, KAYNAK ayni dosyadir.)"""
    govde = (
        "import sys\n"
        "KAYNAK = %r\n"
        "TOOLS = %r\n"
        "with open(KAYNAK, encoding='utf-8') as f:\n"
        "    _m = f.read()\n"
        "_m = _m.replace(%r, 'REPO_ONEKI = \"%s/\"')\n"
        "_m = _m.replace(%r, 'GIT_WORKTREE_KAYIT = \"%s/.git/worktrees\"')\n"
        "if TOOLS not in sys.path:\n"
        "    sys.path.insert(0, TOOLS)\n"
        "exec(compile(_m, KAYNAK, 'exec'),\n"
        "     {'__name__': '__main__', '__file__': KAYNAK, '__builtins__': __builtins__})\n"
    ) % (ICRA, TOOLS, KD.CAPA_REPO, ev_koku, KD.CAPA_WT, ev_koku)
    with open(hedef_dosya, "w", encoding="utf-8") as f:
        f.write(govde)
    return hedef_dosya


def mutant_kopya(kok, yamalar):
    """Izole mutant kopya: kapi + yanindaki moduller kopyalanir, ADLI satir(lar) yamalanir.

    `yamalar`: [(eski, yeni), ...]. Her ankraj TAM BIR KEZ eslesmeli; eslesmezse mutant
    KOSULMAZ ve sebep ADIYLA doner (bayat ankraj sessizce yesillenmez)."""
    os.makedirs(kok, exist_ok=True)
    for ad in os.listdir(TOOLS):
        if ad.endswith(".py"):
            try:
                shutil.copyfile(os.path.join(TOOLS, ad), os.path.join(kok, ad))
            except Exception:                               # noqa: BLE001
                pass
    hedef = os.path.join(kok, "mimar-icra-kapisi.py")
    with open(hedef, encoding="utf-8") as f:
        metin = f.read()
    for eski, yeni in yamalar + EV_CAPALARI:
        if metin.count(eski) != 1:
            return None, "BAYAT ANKRAJ (%d vurus): %s" % (
                metin.count(eski), eski.strip()[:70])
        metin = metin.replace(eski, yeni)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(metin)
    return hedef, None


# 🔴 20 EYL 2026 — IKINCI KAT (run 35497808434, dal koşumu): sabit `REPO` onarildikten
# SONRA gecici worktree kuruldu ama 19 vakanin 6'si KIRMIZI kaldi (B1/B10/B11/B12/C1/C2):
# kapi GOVDESININ KENDI sabitleri (`REPO_ONEKI` + `GIT_WORKTREE_KAYIT`) hala Mac yolunu
# gosterdigi icin K318 ROL EKSENI cip agacini TANIMADI -> her cip vakasi ANA sayilip
# reddedildi. Govde sabitleri PRODUKSIYON kaynagidir ve kapi_dagitim shim'i onlari METIN
# olarak degistirir; bu yuzden onlara DOKUNULMAZ — test, KraL govdesini de tam olarak
# shim'in yaptigi gibi OLCULEN EVE cevirir. Canli Mac'te REPO == CANLI_KOK oldugu icin
# degisim BIREBIR AYNI metni uretir (davranis degismez), kosucuda checkout kokune duser.
EV_CAPALARI = [
    (KD.CAPA_REPO, 'REPO_ONEKI = "%s/"' % REPO),
    (KD.CAPA_WT, 'GIT_WORKTREE_KAYIT = "%s/.git/worktrees"' % REPO),
]


R2_CAGRI = "        if disari and _kardes_ev_muaf(argumanlar, cwd, cip):\n"
F_CAGRI = ("        if not repo_ici(betik, cwd) and "
           "_kardes_ev_muaf(argumanlar, cwd, cip):\n")


SONUC = []


def kaydet(ad, gecti, olculen, beklenen, not_=""):
    SONUC.append((ad, gecti, olculen, beklenen, not_))
    print("{}  {:<52} olculen={:<12} beklenen={:<8} {}".format(
        "✅" if gecti else "🔴", ad[:52], str(olculen)[:12], str(beklenen), not_[:70]))


def main():
    if KARDES_EV is None:
        print("KOSULAMADI: kapi_dagitim.EVLER icinde kardes ev koku YOK.")
        return 1
    temel = gecici_worktree.damgali_mkdtemp("pruvo-kardes-ev-")
    wt = os.path.join(temel, "kayitli-wt")
    kurulum = gecici_worktree.kaydet(REPO, wt, "--no-checkout", "--detach",
                                     commitish="HEAD")
    if kurulum.returncode != 0 or not os.path.isdir(wt):
        print("CEVRE: gecici worktree kurulamadi -> " +
              (kurulum.stderr or "?").strip()[-200:])
        shutil.rmtree(temel, ignore_errors=True)
        return 1
    wt = os.path.normpath(wt)
    # KraL GOVDESI de OLCULEN EVE cevrilir (yukaridaki EV_CAPALARI notu): Mac'te
    # birebir ayni metin, kosucuda checkout koku. Boylece K318 rol ekseni gecici
    # worktree'yi KAYITLI cip agaci olarak TANIR ve cip/ANA ayrimi gercekten olculur.
    KRAL_GOVDE = shim_yaz(os.path.join(temel, "govde-kral.py"), REPO)
    CIP = {"transcript_path": TRANSCRIPT_KOK + "/" + damga(wt) + "/oturum.jsonl",
           "cwd": wt}
    ANA = {"transcript_path": TRANSCRIPT_KOK + "/" + damga(REPO) + "/oturum.jsonl"}
    KARDES_ARAC = KARDES_EV + "/olcum/hasat_ekle.py"
    KOMUT = "python3 " + KARDES_ARAC + " --marka sony"

    try:
        # ================= (A) KOK NEDEN: EV EKSENI =================
        print("=" * 100)
        print("(A) KOK NEDEN — AYNI CAGRI, IKI EV. Kardes ev koku: " + KARDES_EV)
        print("=" * 100)
        kral, _ = kapiya_ver(KRAL_GOVDE, KOMUT, wt, CIP)
        shim = shim_yaz(os.path.join(temel, "shim-kardes-ev.py"), KARDES_EV)
        # Shim evinde ayni cagri GORELI yazimla gelir (Sony pilotunun bicimi).
        macit, _ = kapiya_ver(shim, "python3 olcum/hasat_ekle.py --marka sony",
                              KARDES_EV, {"transcript_path":
                                          TRANSCRIPT_KOK + "/" + damga(KARDES_EV) +
                                          "/oturum.jsonl"})
        print("    KraL govdesi (cip, mutlak yol)      -> " + kral)
        print("    KARDES EV shim'i (ANA, goreli yol)  -> " + macit)
        kaydet("A1 kardes ev SHIM'inde ayni is ACIK (Sony pilotunun yolu)",
               macit == "allow", macit, "allow",
               "shim REPO_ONEKI'yi eve cevirir -> hedef O EVDE repo ICI")

        # ================= (B) KABUL VAKALARI =================
        print("=" * 100)
        print("(B) KABUL — K-KARDES-EV kolu")
        print("=" * 100)
        vakalar = [
            ("B1 CIP x kardes ev betigi -> IZIN (ASIL vaka)",
             KOMUT, wt, CIP, "allow", "KARDES-EV("),
            ("B2 ANA x AYNI cagri -> RED (gevsetme DEGIL)",
             KOMUT, REPO, ANA, "deny", None),
            ("B3 damga YOK (rol OLCULEMEDI) -> RED (fail-closed)",
             KOMUT, REPO, {}, "deny", None),
            ("B4 CIP x kardes ev + ev DISI yan argüman -> RED",
             KOMUT + " --spec " + DISARI + "/spec.md", wt, CIP, "deny", None),
            ("B5 CIP x '<ev_koku>-sahte' onek tuzagi -> RED",
             "python3 " + KARDES_EV + "-sahte/olcum/x.py", wt, CIP, "deny", None),
            ("B6 CIP x kayitsiz repo-disi kok -> RED (menzil ev kumesiyle SINIRLI)",
             "python3 " + DISARI + "/analiz.py", wt, CIP, "deny", None),
            ("B7 CIP x python3 -c (sarmalayici satir-ici) -> RED",
             "python3 -c \"import sys; sys.path.insert(0, '" + KARDES_EV + "/olcum')\"",
             wt, CIP, "deny", None),
            ("B8 ANA x python3 -c -> RED",
             "python3 -c \"import os\"", REPO, ANA, "deny", None),
            ("B9 KONTROL: ANA x curl -> RED (degismedi)",
             "curl -s https://pruvo3d.com/", REPO, ANA, "deny", None),
            ("B10 KONTROL: CIP x curl -> IZIN (11 Eyl davranisi, degismedi)",
             "curl -s https://pruvo3d.com/", wt, CIP, "allow", None),
            ("B11 KONTROL: CIP x repo-ici arac -> IZIN (degismedi)",
             "python3 " + REPO + "/tools/durum.py", wt, CIP, "allow", None),
            # B12 — `..` ILE KARDES EVE INEN CAGRI. K332'nin 817 vakasi bu hedefi
            # "duzlemden KACIS" diye REDDEDIYORDU; 19 Eyl'den sonra hukmu veren kol
            # KARDES-EV'dir ve karar IZIN'dir. Karar DIZGEDEN degil COZULMUS yoldan
            # cikar (`_coz` normpath uygular), yani `..` bir KACAMAK degildir: ayni
            # hedefe duz yazimla (B1) zaten erisilir. 817 kendi iddiasini (duzlemden
            # kacis) HICBIR kayitli ev kokune dusmeyen bir hedefle olcmeye devam eder.
            # 20 Eyl: yazim `~/.claude/cron/../../dev/<ev>` idi; HOME'a bagliydi ve
            # kosucuda (`/home/runner`) BASKA bir yere cozuluyordu -> vaka ev eksenini
            # degil ORTAMI olcuyordu. Ayni eksen (`..` ICEREN, kayitli ev kokune
            # COZULEN yol) HOME'dan BAGIMSIZ yazildi.
            ("B12 CIP x '..' ile kardes eve inen yol -> IZIN (hukum KARDES-EV kolundan)",
             "python3 " + KARDES_EV + "/../" + os.path.basename(KARDES_EV) +
             "/olcum/hasat_ekle.py", wt, CIP, "allow", "KARDES-EV("),
        ]
        for ad, komut, cwd, yuk, beklenen, iz_capasi in vakalar:
            olculen, iz = kapiya_ver(KRAL_GOVDE, komut, cwd, yuk)
            gecti = olculen == beklenen
            not_ = ""
            if gecti and iz_capasi:
                if iz_capasi not in iz:
                    gecti = False
                    not_ = "IZ YOK: " + iz_capasi
            if not gecti and not not_:
                not_ = iz.strip().replace("\n", " ")[:70]
            kaydet(ad, gecti, olculen, beklenen, not_)

        # ================= (C) MENZIL ACIGI GORUNUR MU =================
        print("=" * 100)
        print("(C) MENZIL — kapi ARGUMAN eksenini olcer; dosya ICERIGI menzil DISI")
        print("=" * 100)
        sarmalayici = os.path.join(wt, "sarmalayici-olcum.py")
        with open(sarmalayici, "w", encoding="utf-8") as f:
            f.write("import sys\n"
                    "sys.path.insert(0, \"" + KARDES_EV + "/olcum\")\n"
                    "import hasat_ekle\n")
        masum = os.path.join(wt, "masum-olcum.py")
        with open(masum, "w", encoding="utf-8") as f:
            f.write("print('olcum')\n")
        olculen, iz = kapiya_ver(KRAL_GOVDE, "python3 " + sarmalayici, wt, CIP)
        kaydet("C1 sarmalayici GECER (acik KAPATILMADI, bu kol REDDETMEZ)",
               olculen == "allow", olculen, "allow")
        kaydet("C2 sarmalayici ADIYLA raporlanir (SARMALAYICI-ACIGI)",
               "SARMALAYICI-ACIGI" in iz, "SARMALAYICI-ACIGI" in iz, True,
               "" if "SARMALAYICI-ACIGI" in iz else iz.strip().replace("\n", " ")[:70])
        _o2, iz2 = kapiya_ver(KRAL_GOVDE, "python3 " + masum, wt, CIP)
        kaydet("C3 KONTROL: sarmalayici OLMAYAN betik iz URETMEZ (gurultu yok)",
               "SARMALAYICI-ACIGI" not in iz2, "SARMALAYICI-ACIGI" in iz2, False)

        # ================= (D) MUTANT =================
        print("=" * 100)
        print("(D) MUTANT — izin kolu ANA role GENISLETILIRSE kontrol vakasi KIRMIZI")
        print("=" * 100)
        mut_kok = os.path.join(temel, "mutant-ana")
        # IKI cagri yeri birden ANA'ya acilir: tek kolu acmak YETMEZ (F kolu yine
        # reddeder) — bu, K332'nin MR7 dersinin bu koldaki karsiligidir.
        mut, hata = mutant_kopya(mut_kok, [
            (R2_CAGRI, R2_CAGRI.replace("cwd, cip)", "cwd, True)")),
            (F_CAGRI, F_CAGRI.replace("cwd, cip)", "cwd, True)")),
        ])
        if hata:
            kaydet("D1 MUTANT ANA-GENISLEME", False, hata, "ankraj saglam")
        else:
            m_ana, _ = kapiya_ver(mut, KOMUT, REPO, ANA)
            kaydet("D1 MUTANT ANA-GENISLEME -> B2 vakasi KIRMIZI yanar",
                   m_ana == "allow", m_ana, "allow",
                   "mutantta ANA acilir; TEMIZ kopyada B2 deny olmali")
        mut2_kok = os.path.join(temel, "mutant-rolsuz")
        mut2, hata2 = mutant_kopya(mut2_kok, [
            (R2_CAGRI, R2_CAGRI.replace("cwd, cip)", "cwd, False)"))])
        if hata2:
            kaydet("D2 MUTANT ROL-DUSER", False, hata2, "ankraj saglam")
        else:
            m_cip, _ = kapiya_ver(mut2, KOMUT, wt, CIP)
            kaydet("D2 MUTANT ROL-DUSER (R2) -> B1 vakasi KIRMIZI yanar",
                   m_cip == "deny", m_cip, "deny",
                   "R2 kolu rol parametresini TUKETMEZSE cip yine RED alir")
        mut3_kok = os.path.join(temel, "mutant-f-kolu")
        mut3, hata3 = mutant_kopya(mut3_kok, [
            (F_CAGRI, F_CAGRI.replace("cwd, cip)", "cwd, False)"))])
        if hata3:
            kaydet("D3 MUTANT F-KOLU", False, hata3, "ankraj saglam")
        else:
            m_f, _ = kapiya_ver(mut3, KOMUT, wt, CIP)
            kaydet("D3 MUTANT F-KOLU DUSER -> R2 gecse de betik kolu reddeder",
                   m_f == "deny", m_f, "deny", "iki cagri yeri de TUKETILMELI")
    finally:
        hata = gecici_worktree.kaldir(REPO, wt)
        shutil.rmtree(temel, ignore_errors=True)
        if hata:
            print("TEMIZLIK UYARISI: " + str(hata)[:200])

    kirmizi = [a for a, g, _o, _b, _n in SONUC if not g]
    print("=" * 100)
    print("SONUC: {}/{} gecti | KIRMIZI={}".format(
        len(SONUC) - len(kirmizi), len(SONUC), kirmizi if kirmizi else 0))
    print("=" * 100)
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
