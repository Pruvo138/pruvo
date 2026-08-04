#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-kablolama-test.py — kanca KABLOLAMASININ kabul testi.

Olculen iddialar (hepsi GERCEK `git` ile, SENTETIK depolarda; gercek depoya ve
gercek `~/.gitconfig`e DOKUNULMAZ):

  VAKA 0 — SOZLESME. Nobetcinin ilan ettigi (SOZLESME) her sabit/fonksiyon
    yerinde mi. 🔴 NEDEN AYRI VAKA: `FAIL_CLOSED` yeniden adlandirildiginda bu
    suite COKEREK oluyordu (Traceback=1, iddia=0) — cokme KIRMIZI SAYILMAZ, o
    eksen OLCULMEMIS demektir. Artik sozlesme ihlali KIRMIZI YAKAR.

  VAKA 1 — FAIL-OPEN KAPANDI (UCTAN UCA, gercek `git commit`)
    Guard'i sifir-disi donduren senaryo, IKI govdeyle, tek degisken:
      * ESKI govde (4 Agu oncesi, `|| true`)  -> commit GECER (rc=0)
      * IZLENEN govde                          -> commit DURUR (rc!=0), guard'in
        gerekcesi VE kancanin KENDI gerekcesi gorunur.
    🔴 KANCANIN KENDI GEREKCESI AYRI IDDIADIR (curutucu deligi B): bloklamak
    fail-loud'un YARISIDIR; kanca sussa commit sessizce durur ve mimar
    `--no-verify`ye yonelir.

  VAKA 2 — KURULUM FAIL-CLOSED + AYIRT EDICI IDEMPOTENS
    Kurulamayan her hal sifir-disi + SEBEP. Idempotens artik cikti metnine
    DEGIL, `.git/config`in sha256'sinin DEGISMEMESINE bakar (curutucu deligi G).

  🔴 VAKA 3 — PAYLASILAN/GLOBAL CONFIG KIRLENMEDI
    Sahte HOME + GIT_CONFIG_GLOBAL/SYSTEM katmanlarinda global · system · KOMSU
    deponun `.git/config`i sha256 once=sonra. Worktree'den kosumda ANA
    checkout'un config'i KASITLI hedeftir, `config.worktree` KIRLENMEZ.

  🔴 VAKA 4 — NOBETCI AYIRT EDICI (her eksen: OLDURUCU + tek degiskenli KONTROL)
    kablolama yok · x-bitsiz kanca · `|| true` · cagri silinmis · rc kontrolsuz ·
    kurulu kopya SAPMIS · gerekce susturulmus. Yanlis-pozitif kontrolu: BEYAN
    EDILMIS fail-open bloklar (yedekle/kutu-arsivle/d1-sync) YESIL kalir.

  🔴 VAKA 5 — CI HALI + MUAFIYETIN DARLIGI
    `--ci` halinde eksen K/S OLCULEMEDI ilan edilir ve rc=0. AMA muafiyet
    DARDIR: BASKA bir eksen OLCULEMEDI olursa (kanca dosyasi okunamiyor) rc=1
    (curutucu deligi H — muafiyet `if ci`e genisletilirse gercek arizalar CI'da
    sessizce gecerdi, [[maskeleme-kismi-kapatma]]).

  🔴 VAKA 6 — OLU AGAC (KUSUR 2, mimar iadesi)
    `tools/kancalar` TASIMAYAN bir worktree'de:
      (a) kancalar FIILEN kosmali (kurulu kopya ortak `.git` altindadir);
          KONTROL = elenen GORELI tasarim, ayni agacta HICBIR kanca kosmaz.
      (b) nobetci O AGACIN icinden kosturulunca dogru hukmu vermeli; olu agacta
          rc sifir-disi. KONTROL = saglikli kurulumda ayni agac YESIL.

  🔴 VAKA 7 — IZOLE AGAC MUAFIYETININ DARLIGI
    `core.hooksPath=/dev/null` bir worktree'nin `config.worktree`sinden gelirse
    MESRU izolasyondur (yesil). AYNI deger PAYLASILAN `.git/config`ten gelirse
    1 Agu'ta olculen OLAYDIR -> KIRMIZI.

Kullanim:
    python3 tools/kanca-kablolama-test.py
    python3 tools/kanca-kablolama-test.py --mutasyon
    python3 tools/kanca-kablolama-test.py --tools <dizin>   # (mutasyon ic kullanimi)
"""
import hashlib
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(TOOLS, "kanca-kur.py")
NOBETCI = os.path.join(TOOLS, "kanca-kablolama-nobeti.py")
YARDIMCILAR = ("kanca-nobeti.py", "icra-suzgeci.py")
KANCA_KAYNAGI = os.path.join(TOOLS, "kancalar")

# ---------------------------------------------------------------------------
# 🔴 ESKI GOVDE — `.git/hooks/pre-commit`in 4 Agu 2026 ONCESI hali (birebir).
# FIKSTURDUR: "once fail-open'di" iddiasinin KOSULARAK kanitlanmasi icin durur.
# ---------------------------------------------------------------------------
ESKI_PRE_COMMIT = """#!/bin/sh
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
guard="$root/tools/urunler-guard.py"
[ -f "$guard" ] || exit 0
python3 "$guard" --tetik commit >/dev/null 2>&1 || true

kontrol="$root/tools/mukerrer-kontrol.py"
if [ -f "$kontrol" ] && [ "$PRUVO_MUKERRER_ATLA" != "1" ]; then
  cikti=$(python3 "$kontrol" 2>&1)
  durum=$?
  if [ $durum -eq 1 ]; then
    echo "$cikti" >&2
    exit 1
  fi
fi

gate="$root/tools/mimar-commit-kapisi.py"
if [ -f "$gate" ]; then
  python3 "$gate" || exit 1
fi
exit 0
"""

GUARD_REDDEDER = """#!/usr/bin/env python3
import sys
sys.stderr.write("GUARD-REDDETTI: provenans cozulemedi (sentetik senaryo)\\n")
sys.exit(3)
"""
GECER = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"


def yaz(yol, metin, x=False):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    if x:
        os.chmod(yol, 0o755)


def sha256(yol):
    if not os.path.exists(yol):
        return "YOK"
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def g(cwd, *args, **kw):
    p = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True,
                       text=True, timeout=60, env=kw.get("env"))
    if kw.get("zorunlu") and p.returncode != 0:
        raise RuntimeError("git %s basarisiz: %s" % (" ".join(args), p.stderr.strip()))
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def izole_ortam(ev):
    """global/system git config katmanlarini SAHTE dosyalara baglar.

    🔴 NEDEN SART: MU1 (`--local` -> `--global`) GERCEK `~/.gitconfig`e yazardi.
    Mutasyon turu KULLANICININ makinesini kirletemez."""
    ortam = dict(os.environ)
    ortam["HOME"] = ev
    ortam["XDG_CONFIG_HOME"] = os.path.join(ev, "xdg")
    ortam["GIT_CONFIG_GLOBAL"] = os.path.join(ev, "gitconfig-global")
    ortam["GIT_CONFIG_SYSTEM"] = os.path.join(ev, "gitconfig-system")
    ortam["GIT_CONFIG_NOSYSTEM"] = "0"
    os.makedirs(ortam["XDG_CONFIG_HOME"], exist_ok=True)
    return ortam


def _araclari_ser(kok):
    for ad in ("urunler-guard.py", "mukerrer-kontrol.py", "mimar-commit-kapisi.py",
               "commit-mesaji-kapisi.py", "gecmis-geri-donus-kapisi.py",
               "yedekle.py", "kutu-arsivle.py", "d1-sync.py"):
        yaz(os.path.join(kok, "tools", ad), GECER, True)


def depo_kur(kok, kanca_kaynagi, guard=GECER, ortam=None, kancalar=True):
    """Izlenen tools/kancalar + sentetik nobetci araclari olan sentetik depo."""
    os.makedirs(kok, exist_ok=True)
    g(kok, "init", "-q", "-b", "main", env=ortam, zorunlu=True)
    g(kok, "config", "user.email", "t@t", env=ortam)
    g(kok, "config", "user.name", "T", env=ortam)
    g(kok, "config", "extensions.worktreeConfig", "true", env=ortam)
    _araclari_ser(kok)
    yaz(os.path.join(kok, "tools", "urunler-guard.py"), guard, True)
    if kancalar:
        hedef = os.path.join(kok, "tools", "kancalar")
        os.makedirs(hedef, exist_ok=True)
        for ad in sorted(os.listdir(kanca_kaynagi)):
            shutil.copy2(os.path.join(kanca_kaynagi, ad), os.path.join(hedef, ad))
            os.chmod(os.path.join(hedef, ad), 0o755)
    yaz(os.path.join(kok, "a.txt"), "x\n")
    g(kok, "add", "-A", env=ortam)
    g(kok, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "ilk", env=ortam)
    return kok


class Sayac(object):
    """Etiketli iddia sayaci. Mutasyon turu KIRMIZI ETIKET KUMESINI karsilastirir."""

    def __init__(self):
        self.iddia = 0
        self.kirmizi = []

    def bekle(self, etiket, kosul, aciklama):
        self.iddia += 1
        if not kosul:
            self.kirmizi.append(etiket)
            print("    🔴 %s :: %s" % (etiket, aciklama))
        return bool(kosul)


def _yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def nobetci_yukle(tools_dizini):
    return _yukle("pruvo_kablolama_nobetci_test",
                  os.path.join(tools_dizini, "kanca-kablolama-nobeti.py"))


def kur_yukle(tools_dizini):
    """Kurulum modulu — KURULU DIZIN YOLU BURADAN SORULUR, kopyalanmaz.

    🔴 NEDEN: fikstur yolunu (`.git/pruvo-kancalar`) teste GOMMEK, kurulum
    yolunu degistiren bir mutantta testi COKERTIYORDU (FileNotFoundError).
    Cokme KIRMIZI SAYILMAZ -> o eksen olculmemis olurdu. Yol TEK KAYNAKTAN
    sorulur; boylece mutant testi coketmez, ILGILI iddiada KIRMIZI yakar."""
    return _yukle("pruvo_kablolama_kur_test",
                  os.path.join(tools_dizini, "kanca-kur.py"))


# ---------------------------------------------------------------------------
def kos_vakalar(tools_dizini, ayrintili=True):
    s = Sayac()
    kur_yolu = os.path.join(tools_dizini, "kanca-kur.py")
    kanca_kaynagi = os.path.join(tools_dizini, "kancalar")
    nobetci = nobetci_yukle(tools_dizini)
    kur_mod = kur_yukle(tools_dizini)
    kok = tempfile.mkdtemp(prefix="kanca-kablolama-test-")

    def kurulu_yolu(depo):
        """Kurulu kanca dizini — TEK KAYNAKTAN (kanca-kur.py) sorulur."""
        try:
            return kur_mod.kurulu_dizin(depo)
        except Exception:
            return os.path.join(depo, ".git", "pruvo-kancalar")

    # 🔴 HER VAKA KENDI global/system KATMANINDA KOSAR. Tek ortak sahte HOME ile
    # OLCULDU ki onceki vakanin kurulumu (MU1'de `--global`) katmani ONCEDEN
    # kirletiyor ve kirlenme iddiasi mutanti KOR EDIYORDU
    # ([[fikstur-degeri-mutasyon-koru]]).
    def yeni_ortam(ad):
        ev = os.path.join(kok, "ev-" + ad)
        os.makedirs(ev, exist_ok=True)
        return izole_ortam(ev)

    ortam = yeni_ortam("v1v2")

    def kur_kos(depo, *ek, **kw):
        p = subprocess.run([sys.executable, kur_yolu, "--depo", depo] + list(ek),
                           capture_output=True, text=True, timeout=120,
                           env=kw.get("env") or ortam)
        return p.returncode, (p.stdout + p.stderr)

    try:
        # ================= VAKA 0: SOZLESME ==================================
        if ayrintili:
            print("VAKA 0 — nobetci sozlesmesi")
        eksik = [a for a in getattr(nobetci, "SOZLESME", ())
                 if not hasattr(nobetci, a)]
        s.bekle("V0.sozlesme", hasattr(nobetci, "SOZLESME") and not eksik,
                "nobetcinin ILAN ETTIGI sozlesme eksiksiz olmali; eksik=%s "
                "(sozlesme ihlali COKME degil KIRMIZI olmali)" % eksik)

        # ================= VAKA 1: FAIL-OPEN ONCE / SONRA =====================
        if ayrintili:
            print("VAKA 1 — fail-open ONCE/SONRA (gercek git commit)")
        sonuclar = {}
        for etiket_govde, govde in (
                ("eski", ESKI_PRE_COMMIT),
                ("izlenen", open(os.path.join(kanca_kaynagi, "pre-commit"),
                                 encoding="utf-8").read())):
            d = depo_kur(os.path.join(kok, "v1-" + etiket_govde), kanca_kaynagi,
                         guard=GUARD_REDDEDER, ortam=ortam)
            yaz(os.path.join(d, ".git", "hooks", "pre-commit"), govde, True)
            yaz(os.path.join(d, "a.txt"), "degisti\n")
            g(d, "add", "a.txt", env=ortam)
            rc, cikti, hata = g(d, "commit", "-m", "ikinci", env=ortam)
            sonuclar[etiket_govde] = (rc, cikti + hata)
            if ayrintili:
                print("    %-8s govde -> commit rc=%d" % (etiket_govde, rc))

        s.bekle("V1.eski-gecer", sonuclar["eski"][0] == 0,
                "ESKI govde (`|| true`) ile guard REDDETTIGI HALDE commit GECMELI "
                "(fail-open kaniti); rc=%d" % sonuclar["eski"][0])
        s.bekle("V1.eski-gerekce-yutulur", "GUARD-REDDETTI" not in sonuclar["eski"][1],
                "ESKI govde gerekceyi YUTMALI (fikstur dogru kurulmus olmali)")
        s.bekle("V1.izlenen-bloklar", sonuclar["izlenen"][0] != 0,
                "IZLENEN govde ile commit DURMALI; rc=%d (cikti: %r)"
                % (sonuclar["izlenen"][0], sonuclar["izlenen"][1][-200:]))
        s.bekle("V1.gerekce-gorunur", "GUARD-REDDETTI" in sonuclar["izlenen"][1],
                "GUARD'in gerekcesi gorunmeli; cikti: %r" % sonuclar["izlenen"][1][-200:])
        # 🔴 CURUTUCU DELIGI B: kancanin KENDI gerekcesi AYRI iddiadir.
        s.bekle("V1.kanca-gerekcesi-gorunur",
                "COMMIT DURDURULDU" in sonuclar["izlenen"][1],
                "KANCANIN KENDI gerekcesi de gorunmeli (bloklamak fail-loud'un "
                "YARISIDIR; kanca susarsa mimar nedeni goremez); cikti: %r"
                % sonuclar["izlenen"][1][-300:])
        d = depo_kur(os.path.join(kok, "v1-kontrol"), kanca_kaynagi, guard=GECER,
                     ortam=ortam)
        yaz(os.path.join(d, ".git", "hooks", "pre-commit"),
            open(os.path.join(kanca_kaynagi, "pre-commit"), encoding="utf-8").read(), True)
        yaz(os.path.join(d, "a.txt"), "degisti\n")
        g(d, "add", "a.txt", env=ortam)
        rc_k, _o, _e = g(d, "commit", "-m", "kontrol", env=ortam)
        s.bekle("V1.kontrol-gecer", rc_k == 0,
                "guard KABUL edince izlenen govde commit'i GECIRMELI; rc=%d" % rc_k)

        # ================= VAKA 2: KURULUM FAIL-CLOSED ========================
        if ayrintili:
            print("VAKA 2 — kurulum fail-closed + ayirt edici idempotens")
        d = depo_kur(os.path.join(kok, "v2a"), kanca_kaynagi, ortam=ortam,
                     kancalar=False)
        rc, cikti = kur_kos(d)
        s.bekle("V2.dizin-yok-rc", rc != 0,
                "izlenen kanca dizini YOKken kurulum SIFIR-DISI cikmali; rc=%d" % rc)
        s.bekle("V2.dizin-yok-sebep", "kanca dizini YOK" in cikti,
                "sebep BASILMALI; cikti: %r" % cikti[-200:])
        d = depo_kur(os.path.join(kok, "v2b"), kanca_kaynagi, ortam=ortam)
        os.remove(os.path.join(d, "tools", "kancalar", "pre-push"))
        rc, cikti = kur_kos(d)
        s.bekle("V2.eksik-kanca-rc", rc != 0,
                "EKSIK kanca varken kurulum SIFIR-DISI cikmali; rc=%d" % rc)
        s.bekle("V2.eksik-kanca-sebep", "EKSIK kanca" in cikti,
                "eksik kanca adi BASILMALI; cikti: %r" % cikti[-200:])
        d = depo_kur(os.path.join(kok, "v2c"), kanca_kaynagi, ortam=ortam)
        rc, cikti = kur_kos(d, "--dogrula")
        s.bekle("V2.kurulmamis-dogrula-rc", rc != 0,
                "kurulu OLMAYAN depoda --dogrula SIFIR-DISI cikmali; rc=%d" % rc)

        d = depo_kur(os.path.join(kok, "v2d"), kanca_kaynagi, ortam=ortam)
        rc1, cikti1 = kur_kos(d)
        s.bekle("V2.kurulum-basarili", rc1 == 0,
                "saglikli depoda kurulum BASARILI olmali; rc=%d cikti=%r"
                % (rc1, cikti1[-400:]))
        _rc, deger, _e = g(d, "config", "--get", "core.hooksPath", env=ortam)
        s.bekle("V2.deger-mutlak", os.path.isabs(deger) and deger.endswith("pruvo-kancalar"),
                "yazilan deger ORTAK .git altindaki kurulu dizinin MUTLAK yolu "
                "olmali; %r geldi" % deger)
        # 🔴 CURUTUCU DELIGI G: idempotens artik CIKTI METNINE degil, config'in
        # sha256'sinin DEGISMEMESINE bakar (metin taklit edilebilir, yazma edilemez).
        # 🔴 CURUTUCU DELIGI G: idempotens CIKTI METNINE bakamaz (metin taklit
        # edilir). sha256 de YETMEZ: git ayni degeri yeniden yazinca ICERIK
        # DEGISMEZ, yalniz DOSYA YENIDEN YAZILIR. Olculen sey YAZMA OLAYIDIR ->
        # mtime_ns. (Olculdu: "her kosum yeniden yazar" mutanti sha256 ile
        # HAYATTA KALIYORDU.)
        cfg = os.path.join(d, ".git", "config")
        cfg_once, mtime_once = sha256(cfg), os.stat(cfg).st_mtime_ns
        rc2, cikti2 = kur_kos(d)
        s.bekle("V2.idempotent",
                rc2 == 0 and sha256(cfg) == cfg_once
                and os.stat(cfg).st_mtime_ns == mtime_once,
                "ikinci kosum config'i YENIDEN YAZMAMALI (sha256 %s->%s, mtime_ns "
                "%s->%s), rc=%d" % (cfg_once[:12], sha256(cfg)[:12], mtime_once,
                                    os.stat(cfg).st_mtime_ns, rc2))

        # ================= VAKA 3: PAYLASILAN CONFIG KIRLENMEDI ===============
        if ayrintili:
            print("VAKA 3 — paylasilan/global config kirlenmedi")
        o3 = yeni_ortam("v3")
        komsu = depo_kur(os.path.join(kok, "v3-komsu"), kanca_kaynagi, ortam=o3)
        hedef = depo_kur(os.path.join(kok, "v3-hedef"), kanca_kaynagi, ortam=o3)
        once = {"global": sha256(o3["GIT_CONFIG_GLOBAL"]),
                "system": sha256(o3["GIT_CONFIG_SYSTEM"]),
                "komsu": sha256(os.path.join(komsu, ".git", "config"))}
        s.bekle("V3.taze-katman", once["global"] == "YOK" and once["system"] == "YOK",
                "TUZAK KURULUMU: VAKA 3 TAZE katmanda baslamali; once=%s" % once)
        rc, cikti = kur_kos(hedef, env=o3)
        s.bekle("V3.kurulum-basarili", rc == 0,
                "hedef depoya kurulum basarili olmali; rc=%d cikti=%r" % (rc, cikti[-400:]))
        sonra = {"global": sha256(o3["GIT_CONFIG_GLOBAL"]),
                 "system": sha256(o3["GIT_CONFIG_SYSTEM"]),
                 "komsu": sha256(os.path.join(komsu, ".git", "config"))}
        s.bekle("V3.global-kirlenmedi", once["global"] == sonra["global"],
                "GLOBAL config DEGISMEMELI (once=%s sonra=%s)"
                % (once["global"][:12], sonra["global"][:12]))
        s.bekle("V3.system-kirlenmedi", once["system"] == sonra["system"],
                "SYSTEM config DEGISMEMELI")
        s.bekle("V3.komsu-kirlenmedi", once["komsu"] == sonra["komsu"],
                "KOMSU deponun .git/config'i DEGISMEMELI")

        ana = depo_kur(os.path.join(kok, "v3-ana"), kanca_kaynagi, ortam=o3)
        wt = os.path.join(kok, "v3-wt")
        g(ana, "worktree", "add", "-q", wt, "-b", "dal", env=o3, zorunlu=True)
        cw = os.path.join(ana, ".git", "worktrees", os.path.basename(wt), "config.worktree")
        cw_once = sha256(cw)
        rc, cikti = kur_kos(wt, env=o3)
        s.bekle("V3.worktreeden-kurulur", rc == 0,
                "worktree'den kosum basarili olmali; rc=%d cikti=%r" % (rc, cikti[-400:]))
        s.bekle("V3.worktree-config-kirlenmedi", cw_once == sha256(cw),
                "worktree'nin config.worktree'si DEGISMEMELI")
        paylasilan = open(os.path.join(ana, ".git", "config"), encoding="utf-8").read()
        s.bekle("V3.ana-config-hedeflendi", "hooksPath" in paylasilan,
                "worktree'den kosum ANA checkout'un .git/config'ine yazmali (KASITLI)")
        s.bekle("V3.deger-oldurucu-degil",
                "/dev/null" not in paylasilan and "pruvo-kancalar" in paylasilan,
                "yazilan deger OLDURUCU olmamali ve kurulu dizini gostermeli")
        s.bekle("V3.hedef-basildi",
                ("config --local core.hooksPath" in cikti
                 and os.path.realpath(ana) in cikti),
                "kurulum YAZDIGI KOMUTU (kapsam bayragi + hedef depo) BASMALI; "
                "cikti: %r" % cikti[-400:])

        # ================= VAKA 4: NOBETCI AYIRT EDICI ========================
        if ayrintili:
            print("VAKA 4 — nobetci ayirt edici (oldurucu + kontrol)")
        o4 = yeni_ortam("v4")

        # 🔴 IC-SUREC olcum, fikstur ortamiyla AYNI config katmanina baglanir;
        # ayrica ISTISNA YUTULMAZ ama COKERTMEZ: sozlesme bozuksa iddialar
        # KIRMIZI yanar, suite Traceback ile OLMEZ (curutucu deligi I).
        def hukum(depo, ci=False, env=None):
            env = env or o4
            yedek = {k: os.environ.get(k) for k in
                     ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL",
                      "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")}
            os.environ.update({k: env[k] for k in yedek})
            try:
                b = nobetci.denetle(depo, ci=ci, kaynak_kok=depo)
                return nobetci.genel_hal(b), nobetci.cikis_kodu(b, ci), b
            except Exception as e:
                print("    ⚠️ nobetci PATLADI (%s: %s) -> iddialar kirmizi yanacak"
                      % (type(e).__name__, e))
                return "PATLADI", 99, []
            finally:
                for k, v in yedek.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

        def kurulu_depo(ad, **kw):
            """🔴 KURULUM BASARISIZ OLSA BILE PATLAMAZ. Fikstur kurulumunda
            `raise` etmek, kurulumu bozan bir mutanti COKME'ye cevirir; cokme
            KIRMIZI SAYILMAZ (o eksen olculmemis olur). Basarisizlik ilgili
            iddialarda dogal olarak kirmizi yanar."""
            d = depo_kur(os.path.join(kok, ad), kanca_kaynagi,
                         ortam=kw.pop("ortam", o4), **kw)
            rc, c = kur_kos(d, env=o4)
            if rc != 0:
                print("    ⚠️ fikstur kurulumu basarisiz (%s, rc=%d): %s"
                      % (ad, rc, c[-200:]))
            return d

        saglikli = kurulu_depo("v4-saglikli")
        h, rc, b = hukum(saglikli)
        s.bekle("V4.saglikli-yesil", h == nobetci.YESIL and rc == 0,
                "saglikli+kurulu depo YESIL olmali; %s (rc=%d) -> %s"
                % (h, rc, [(e, m) for e, x, m in b if x != nobetci.YESIL]))
        pp = open(os.path.join(saglikli, "tools", "kancalar", "pre-push"),
                  encoding="utf-8").read()
        s.bekle("V4.beyanli-failopen-fiksturde", "|| true" in pp or ">/dev/null 2>&1" in pp,
                "TUZAK KURULUMU: pre-push fiksturunde beyan edilmis fail-open deyim "
                "GECMELI (yoksa yanlis-pozitif ekseni olculmemis olur)")

        d = depo_kur(os.path.join(kok, "v4-kablosuz"), kanca_kaynagi, ortam=o4)
        h, rc, b = hukum(d)
        s.bekle("V4.kablolamasiz-kirmizi",
                any(e == nobetci.EKSEN_KABLOLAMA and x == nobetci.KIRMIZI
                    for e, x, _m in b) and rc != 0,
                "kablolama kurulu DEGILKEN eksen K KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        d = kurulu_depo("v4-xbitsiz")
        kurulu = kurulu_yolu(d)
        os.chmod(os.path.join(kurulu, "pre-commit"), 0o644)
        h, rc, b = hukum(d)
        s.bekle("V4.xbitsiz-kirmizi", h == nobetci.KIRMIZI and rc != 0,
                "x-bitsiz kanca KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        d = kurulu_depo("v4-yutma")
        y = os.path.join(kurulu_yolu(d), "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('python3 "$pruvo_guard" --tetik commit\n',
                             'python3 "$pruvo_guard" --tetik commit >/dev/null 2>&1 || true\n')
        s.bekle("V4.yutma-mutant-uygulandi", yeni != govde, "mutant uygulanmali")
        yaz(y, yeni, True)
        h, rc, b = hukum(d)
        s.bekle("V4.yutma-kirmizi",
                any(e.startswith("y) pre-commit -> tools/urunler-guard.py")
                    and x == nobetci.KIRMIZI for e, x, _m in b) and rc != 0,
                "`|| true` geri gelince eksen Y KIRMIZI olmali; %s (rc=%d)" % (h, rc))
        # 🔴 AYNI mutant SAPMA eksenini de yakmali (kurulu kopya kaynaktan sapti)
        s.bekle("V4.sapma-kirmizi",
                any(e == nobetci.EKSEN_SAPMA and x == nobetci.KIRMIZI
                    for e, x, _m in b),
                "kurulu kopya elle degistirilince SAPMA ekseni KIRMIZI olmali")

        d = kurulu_depo("v4-cagrisiz")
        y = os.path.join(kurulu_yolu(d), "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('python3 "$pruvo_guard" --tetik commit\n',
                             '# python3 "$pruvo_guard" --tetik commit\n')
        s.bekle("V4.cagrisiz-mutant-uygulandi", yeni != govde, "mutant uygulanmali")
        yaz(y, yeni, True)
        h, rc, b = hukum(d)
        s.bekle("V4.cagrisiz-kirmizi", h == nobetci.KIRMIZI and rc != 0,
                "cagri yoruma alininca KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        d = kurulu_depo("v4-rcsiz")
        y = os.path.join(kurulu_yolu(d), "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('pruvo_guard_rc=$?\n', 'pruvo_guard_rc=0\n')
        s.bekle("V4.rcsiz-mutant-uygulandi", yeni != govde, "mutant uygulanmali")
        yaz(y, yeni, True)
        _cs = [l for l in yeni.splitlines()
               if 'python3 "$pruvo_guard"' in l and not l.strip().startswith("#")]
        s.bekle("V4.rcsiz-cagri-duruyor",
                len(_cs) == 1 and "|| true" not in _cs[0] and "/dev/null" not in _cs[0],
                "TUZAK KURULUMU: cagri satiri DURMALI ve yutma deyimi OLMAMALI "
                "(yalniz eksen B ayirt edebilsin); satirlar=%r" % _cs)
        h, rc, b = hukum(d)
        s.bekle("V4.rc-kontrolsuz-kirmizi",
                any(e.startswith("y) pre-commit -> tools/urunler-guard.py")
                    and x == nobetci.KIRMIZI for e, x, _m in b) and rc != 0,
                "rc HIC kontrol edilmiyorsa KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        # 🔴 CURUTUCU DELIGI B (nobetci kolu): gerekce susturulursa eksen G kirmizi
        d = kurulu_depo("v4-gerekcesiz")
        y = os.path.join(kurulu_yolu(d), "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace("COMMIT DURDURULDU", "islem bitti").replace(
            "COMMIT ENGELLENDI", "islem bitti")
        s.bekle("V4.gerekcesiz-mutant-uygulandi", yeni != govde, "mutant uygulanmali")
        yaz(y, yeni, True)
        h, rc, b = hukum(d)
        s.bekle("V4.gerekce-kirmizi",
                any(e == "g) pre-commit gerekce" and x == nobetci.KIRMIZI
                    for e, x, _m in b) and rc != 0,
                "kanca kendi gerekcesini basmiyorsa eksen G KIRMIZI olmali; "
                "%s (rc=%d)" % (h, rc))

        # ================= VAKA 5: CI HALI + MUAFIYET DARLIGI =================
        if ayrintili:
            print("VAKA 5 — CI hali + muafiyetin DARLIGI")
        o5 = yeni_ortam("v5")
        d = depo_kur(os.path.join(kok, "v5-ci"), kanca_kaynagi, ortam=o5)
        h, rc, b = hukum(d, ci=True, env=o5)
        s.bekle("V5.ci-rc-sifir", rc == 0,
                "CI halinde (kablolama kurulu degil) rc=0 olmali; rc=%d kirmizilar=%s"
                % (rc, [(e, m) for e, x, m in b if x == nobetci.KIRMIZI]))
        s.bekle("V5.ci-kablolama-ilan",
                any(e == nobetci.EKSEN_KABLOLAMA and x == nobetci.OLCULEMEDI
                    for e, x, _m in b),
                "CI halinde eksen K OLCULEMEDI olarak ILAN EDILMELI")
        # 🔴 CURUTUCU DELIGI H: muafiyet YALNIZ K/S eksenlerini kapsamali.
        # BASKA bir eksen OLCULEMEDI olursa CI'da da rc=1 olmali.
        dh = depo_kur(os.path.join(kok, "v5-okunamaz"), kanca_kaynagi, ortam=o5)
        okunamaz = os.path.join(dh, "tools", "kancalar", "pre-commit")
        os.chmod(okunamaz, 0o000)
        try:
            hh, rch, bh = hukum(dh, ci=True, env=o5)
            olculemeyenler = [e for e, x, _m in bh if x == nobetci.OLCULEMEDI
                              and e not in nobetci._CI_MUAF_EKSENLER]
            s.bekle("V5.ci-muafiyet-dar-fikstur", bool(olculemeyenler),
                    "TUZAK KURULUMU: MUAF OLMAYAN bir eksen OLCULEMEDI olmali "
                    "(yoksa darlik olculmemis olur); bulgular=%s"
                    % [(e, x) for e, x, _m in bh])
            s.bekle("V5.ci-muafiyet-dar", rch != 0,
                    "`--ci` muafiyeti YALNIZ K/S eksenlerini kapsamali: baska bir "
                    "eksen OLCULEMEDI iken rc SIFIR-DISI olmali; rc=%d" % rch)
        finally:
            os.chmod(okunamaz, 0o644)
        y = os.path.join(d, "tools", "kancalar", "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yaz(y, govde.replace('python3 "$pruvo_guard" --tetik commit\n',
                             'python3 "$pruvo_guard" --tetik commit || true\n'), True)
        _h2, rc2, _b2 = hukum(d, ci=True, env=o5)
        s.bekle("V5.ci-yutma-kirmizi", rc2 != 0,
                "CI halinde de izlenen kaynaktaki `|| true` KIRMIZI yakmali; rc=%d" % rc2)

        # ================= VAKA 6: OLU AGAC (KUSUR 2) =========================
        if ayrintili:
            print("VAKA 6 — olu agac (tools/kancalar TASIMAYAN worktree)")
        o6 = yeni_ortam("v6")
        ana6 = depo_kur(os.path.join(kok, "v6-ana"), kanca_kaynagi, ortam=o6)
        # ESKI commit: `tools/` BUTUNUYLE yok (eski bir dalin hali).
        # 🔴 NEDEN TUM `tools/`: kancanin FIILEN kostugunun KANITI, fail-closed
        # pre-commit'in `tools/urunler-guard.py`yi BULAMAYIP durmasi ve gerekce
        # basmasidir. Yalniz `tools/kancalar` silinseydi guard stub'i yerinde
        # kalir, kanca kossa da kosmasa da commit rc=0 verirdi -> vaka AYIRT
        # EDICI OLMAZDI (ilk kosumda tam bu sekilde yanildi ve olculdu).
        g(ana6, "checkout", "-q", "-b", "eskidal", env=o6, zorunlu=True)
        shutil.rmtree(os.path.join(ana6, "tools"))
        g(ana6, "add", "-A", env=o6)
        g(ana6, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m",
          "kancalar YOK", env=o6)
        _rc, eski_sha, _e = g(ana6, "rev-parse", "HEAD", env=o6)
        g(ana6, "checkout", "-q", "main", env=o6, zorunlu=True)

        wt6 = os.path.join(kok, "v6-wt")
        g(ana6, "worktree", "add", "-q", "--detach", wt6, eski_sha, env=o6, zorunlu=True)
        g(wt6, "config", "user.email", "t@t", env=o6)
        g(wt6, "config", "user.name", "T", env=o6)
        s.bekle("V6.olu-agac-fikstur",
                not os.path.isdir(os.path.join(wt6, "tools")),
                "TUZAK KURULUMU: bu worktree'de `tools/` BULUNMAMALI (kancanin "
                "kostugunu ancak guard'i BULAMAYIP durmasi kanitlar)")
        rc, _c = kur_kos(ana6, env=o6)
        s.bekle("V6.kurulum-basarili", rc == 0, "ana6'ya kurulum basarili olmali")

        def commit_dene(agac, etiket):
            yaz(os.path.join(agac, "z-%s.txt" % etiket), os.urandom(4).hex() + "\n")
            g(agac, "add", "-A", env=o6)
            rc, o, e = g(agac, "commit", "-m", "dene-" + etiket, env=o6)
            return rc, (o + e)

        # (a) ÖLDÜRÜCÜ: kancalar olu agacta da FIILEN kosmali. Kanit: kanca
        #     `tools/urunler-guard.py` bulamayip FAIL-CLOSED durur ve gerekce basar.
        rc_olu, cikti_olu = commit_dene(wt6, "secilen")
        s.bekle("V6.olu-agacta-kanca-kosuyor",
                rc_olu != 0 and "COMMIT DURDURULDU" in cikti_olu,
                "tools/kancalar TASIMAYAN agacta da kancalar KOSMALI (kurulu kopya "
                "ORTAK .git altindadir); rc=%d cikti=%r" % (rc_olu, cikti_olu[-300:]))

        # (a-KONTROL, tek degisken): ELENEN goreli tasarim -> ayni agacta HICBIRI
        g(ana6, "config", "--local", "core.hooksPath", "tools/kancalar",
          env=o6, zorunlu=True)
        rc_gor, cikti_gor = commit_dene(wt6, "goreli")
        s.bekle("V6.goreli-tasarim-olu",
                rc_gor == 0 and "COMMIT DURDURULDU" not in cikti_gor,
                "KONTROL: ELENEN goreli tasarimda ayni agacta HICBIR kanca "
                "kosmamali (bu vakanin ayirt edici oldugunu kanitlar); rc=%d"
                % rc_gor)

        # (b) ÖLDÜRÜCÜ: nobetci O AGACIN icinden dogru hukmu vermeli.
        #     Su an goreli (olu) hal kurulu -> KIRMIZI beklenir.
        def hukum6(agac):
            yedek = {k: os.environ.get(k) for k in
                     ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL",
                      "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")}
            os.environ.update({k: o6[k] for k in yedek})
            try:
                b = nobetci.denetle(ana6, ci=False, kaynak_kok=agac)
                return nobetci.genel_hal(b), nobetci.cikis_kodu(b, False), b
            except Exception as e:
                print("    ⚠️ nobetci PATLADI (%s: %s)" % (type(e).__name__, e))
                return "PATLADI", 99, []
            finally:
                for k, v in yedek.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

        # (b) ÖLDÜRÜCÜ: nobetci O AGACIN halini olcmeli, ANA checkout'un degil.
        # 🔴 AYIRT EDICI KURULUM: ANA checkout SAGLIKLI birakilir, YALNIZ
        # worktree kendi `config.worktree`siyle OLU hale getirilir. Boylece
        # "ana checkout'a bakan" bir nobetci YESIL, "bu agaca bakan" nobetci
        # KIRMIZI verir — fark TAM OLARAK olculen eksendir. (Ilk kurulumda ana
        # da bozuktu; o halde mutant HAYATTA KALIYORDU, olculdu.)
        rc, _c = kur_kos(ana6, env=o6)
        s.bekle("V6.yeniden-kurulum", rc == 0, "yeniden kurulum basarili olmali")
        h6b, rc6b, b6b = hukum6(wt6)
        s.bekle("V6.saglikli-agac-yesil", rc6b == 0,
                "KONTROL: saglikli kurulumda AYNI agac yesil olmali; %s rc=%d -> %s"
                % (h6b, rc6b, [(e, m) for e, x, m in b6b if x != nobetci.YESIL]))
        h6a, rc6a, _b6a = hukum6(ana6)
        s.bekle("V6.ana-saglikli", rc6a == 0,
                "TUZAK KURULUMU: ANA checkout SAGLIKLI kalmali; %s rc=%d" % (h6a, rc6a))
        g(wt6, "config", "--worktree", "core.hooksPath",
          os.path.join(kok, "boyle-bir-dizin-yok"), env=o6, zorunlu=True)
        h6c, rc6c, _b6c = hukum6(wt6)
        s.bekle("V6.nobetci-olu-agaci-goruyor", rc6c != 0,
                "nobetci OLU agacin ICINDEN kosturulunca SIFIR-DISI vermeli "
                "(ANA checkout saglikli oldugu halde); %s rc=%d" % (h6c, rc6c))

        # ================= VAKA 7: IZOLE AGAC MUAFIYETI DAR ===================
        if ayrintili:
            print("VAKA 7 — izole agac muafiyetinin DARLIGI")
        o7 = yeni_ortam("v7")
        ana7 = depo_kur(os.path.join(kok, "v7-ana"), kanca_kaynagi, ortam=o7)
        wt7 = os.path.join(kok, "v7-wt")
        g(ana7, "worktree", "add", "-q", wt7, "-b", "izole", env=o7, zorunlu=True)
        rc, _c = kur_kos(ana7, env=o7)
        s.bekle("V7.kurulum-basarili", rc == 0, "ana7'ye kurulum basarili olmali")

        def hukum7(agac):
            yedek = {k: os.environ.get(k) for k in
                     ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL",
                      "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")}
            os.environ.update({k: o7[k] for k in yedek})
            try:
                b = nobetci.denetle(ana7, ci=False, kaynak_kok=agac)
                return nobetci.cikis_kodu(b, False), b
            except Exception as e:
                print("    ⚠️ nobetci PATLADI (%s: %s)" % (type(e).__name__, e))
                return 99, []
            finally:
                for k, v in yedek.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

        g(wt7, "config", "--worktree", "core.hooksPath", "/dev/null",
          env=o7, zorunlu=True)
        rc7, _b7 = hukum7(wt7)
        s.bekle("V7.izole-worktree-yesil", rc7 == 0,
                "config.worktree'den gelen /dev/null KASITLI izolasyondur -> "
                "yanlis-pozitif URETILMEMELI; rc=%d" % rc7)
        # KONTROL (tek degisken: KAYNAK DOSYA): ayni deger PAYLASILAN config'ten
        g(wt7, "config", "--worktree", "--unset", "core.hooksPath", env=o7)
        g(ana7, "config", "--local", "core.hooksPath", "/dev/null", env=o7, zorunlu=True)
        rc7b, _b7b = hukum7(wt7)
        s.bekle("V7.paylasilan-devnull-kirmizi", rc7b != 0,
                "AYNI deger PAYLASILAN .git/config'ten gelirse 1 Agu'ta olculen "
                "OLAYDIR -> KIRMIZI olmali; rc=%d" % rc7b)

    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return s


# ---------------------------------------------------------------------------
# MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosyalar DEGISMEZ
# ---------------------------------------------------------------------------
MUTANTLAR = (
    # 🔴 MU1 BILEREK GENIS. Kapsam bayragini makine capina cikarmak TEK bir
    # ekseni degil "deger BU DEPONUN config'ine indi mi" varsayimina dayanan HER
    # ekseni devirir; imza OLCULEREK sabitlendi (tahminle DEGIL).
    ("MU1 kur: KAPSAM --local -> --global (makine capinda kirlenme)",
     "kanca-kur.py", 'KAPSAM = "--local"', 'KAPSAM = "--global"',
     frozenset({"V3.global-kirlenmedi", "V3.hedef-basildi",
                "V3.ana-config-hedeflendi", "V3.deger-oldurucu-degil",
                "V6.ana-saglikli", "V6.saglikli-agac-yesil",
                "V6.yeniden-kurulum"})),

    ("MU2 kur: fail-closed devrilir (Hata -> cikis 0)",
     "kanca-kur.py",
     '            print("🔴 KURULAMADI: %s" % e, file=sys.stderr)\n            return 1',
     '            print("🔴 KURULAMADI: %s" % e, file=sys.stderr)\n            return 0',
     frozenset({"V2.dizin-yok-rc", "V2.eksik-kanca-rc"})),

    ("MU3 kur: kur->DOGRULA halkasi kirilir",
     "kanca-kur.py",
     '        bulgular.append(("kablolama", False,',
     '        bulgular.append(("kablolama", True,',
     frozenset({"V2.kurulmamis-dogrula-rc"})),

    # 🔴 MU4 KUSUR 2-a: SECILEN mutlak tasarim ELENEN goreli tasarima geri
    # cevrilir -> olu agacta kancalar OLUR.
    # 🔴 MU4 = ELENEN SECENEK 2 (mutlak ama ANA AGACIN icindeki izlenen dizin).
    # Olculdu: bu halde olu worktree'de kancalar YINE KOSAR (yol mutlaktir) —
    # o yuzden `V6.olu-agacta-kanca-kosuyor` bu mutanti OLDURMEZ; secenek 2'yi
    # eleyen sey ana agacin `git checkout`uyla kablolamanin degismesidir.
    # Secenek 1'in (goreli) mutanti MU15'tir.
    ("MU4 kur: kurulu dizin ANA agacin izlenen dizinine doner (elenen secenek 2)",
     "kanca-kur.py",
     '    return os.path.join(ortak_git_dizini(baslangic), KURULU_DIZIN_ADI)',
     '    return os.path.join(baslangic, KANCA_DIZINI)',
     frozenset({"V2.deger-mutlak", "V3.deger-oldurucu-degil",
                "V4.saglikli-yesil", "V4.sapma-kirmizi",
                "V6.saglikli-agac-yesil"})),

    ("MU5 kur: idempotens kirilir (her kosum config'i YENIDEN yazar)",
     "kanca-kur.py",
     '        if os.path.normpath(cozulen) == os.path.normpath(kurulu):\n'
     '            print("  DEGISIKLIK YOK',
     '        if False:\n'
     '            print("  DEGISIKLIK YOK',
     frozenset({"V2.idempotent"})),

    ("MU6 nobetci: YUTMA deseni listesi bosaltilir (`|| true` kabul edilir)",
     "kanca-kablolama-nobeti.py",
     "    for desen, tarif in YUTMA_DESENLERI:",
     "    for desen, tarif in ():",
     frozenset({"V4.yutma-kirmizi", "V5.ci-yutma-kirmizi"})),

    ("MU7 nobetci: EKSEN B oldurulur (rc kontrolu aranmaz)",
     "kanca-kablolama-nobeti.py",
     "def bloklama_hukmu(etkili, indeks, ham):",
     "def bloklama_hukmu(etkili, indeks, ham):\n    return True, None",
     frozenset({"V4.rc-kontrolsuz-kirmizi"})),

    ("MU8 nobetci: EKSEN K oldurulur (ayarsiz hooksPath yesil sayilir)",
     "kanca-kablolama-nobeti.py",
     '        return (EKSEN_KABLOLAMA, KIRMIZI,\n'
     '                "core.hooksPath AYARLI DEGIL',
     '        return (EKSEN_KABLOLAMA, YESIL,\n'
     '                "core.hooksPath AYARLI DEGIL',
     frozenset({"V4.kablolamasiz-kirmizi"})),

    # 🔴 MU9 CURUTUCU DELIGI H: `--ci` muafiyeti TUM OLCULEMEDI'lere genisler.
    ("MU9 nobetci: --ci muafiyeti GENISLER (H)",
     "kanca-kablolama-nobeti.py",
     "        if ci and eksen in _CI_MUAF_EKSENLER:",
     "        if ci:",
     frozenset({"V5.ci-muafiyet-dar"})),

    # 🔴 MU10 KUSUR 2-b: nobetci yine ANA checkout'a bakar.
    ("MU10 nobetci: kosturuldugu agac yerine ANA checkout olculur (KUSUR 2-b)",
     "kanca-kablolama-nobeti.py",
     "    kaynak_kok = kaynak_kok or kok",
     "    kaynak_kok = kok",
     frozenset({"V6.nobetci-olu-agaci-goruyor"})),

    # 🔴 MU11 CURUTUCU DELIGI B (nobetci kolu): gerekce capalari bosaltilir.
    ("MU11 nobetci: GEREKCE capalari bosaltilir (B)",
     "kanca-kablolama-nobeti.py",
     '        capalar = GEREKCE_CAPALARI.get(kanca, ())',
     '        capalar = ()',
     frozenset({"V4.gerekce-kirmizi"})),

    ("MU12 nobetci: SAPMA ekseni oldurulur",
     "kanca-kablolama-nobeti.py",
     '        return (EKSEN_SAPMA, KIRMIZI,',
     '        return (EKSEN_SAPMA, YESIL,',
     frozenset({"V4.sapma-kirmizi"})),

    # 🔴 MU13 izole muafiyeti GENISLER: kaynak dosya kontrolu kalkar ->
    # PAYLASILAN config'ten gelen /dev/null da "mesru izolasyon" sayilir.
    ("MU13 nobetci: izole muafiyeti GENISLER (kaynak dosya kontrolu kalkar)",
     "kanca-kablolama-nobeti.py",
     '    return os.path.basename(dosya) == "config.worktree"',
     '    return True',
     frozenset({"V7.paylasilan-devnull-kirmizi"})),

    # 🔴 MU14 CURUTUCU DELIGI I: sozlesme sabiti yeniden adlandirilir. Suite
    # COKMEMELI, KIRMIZI YAKMALI (cokme kirmizi sayilmaz).
    ("MU14 nobetci: FAIL_CLOSED yeniden adlandirilir (I — cokme degil KIRMIZI)",
     "kanca-kablolama-nobeti.py",
     "FAIL_CLOSED = {\n    (\"pre-commit\", \"tools/urunler-guard.py\"):",
     "FAIL_CLOSED_YENI = {\n    (\"pre-commit\", \"tools/urunler-guard.py\"):",
     # Olculen imza: nobetci her cagrida patlar; `hukum()` bunu YUTMAZ ama
     # COKERTMEZ de -> "rc sifir-disi olmali" diyen iddialar (patlama rc=99)
     # dogal olarak GECER, "yesil olmali" ve "su eksen ilan edilmeli" diyenler
     # KIRMIZI yanar. Dedike detektor V0.sozlesme'dir ve ATESLER.
     frozenset({"V0.sozlesme", "V4.saglikli-yesil", "V4.kablolamasiz-kirmizi",
                "V4.xbitsiz-kirmizi", "V4.yutma-kirmizi", "V4.sapma-kirmizi",
                "V4.cagrisiz-kirmizi", "V4.rc-kontrolsuz-kirmizi",
                "V4.gerekce-kirmizi", "V5.ci-rc-sifir", "V5.ci-kablolama-ilan",
                "V5.ci-muafiyet-dar-fikstur", "V6.ana-saglikli",
                "V6.saglikli-agac-yesil", "V7.izole-worktree-yesil"})),

    # 🔴 MU15 KUSUR 2-a'nin TAM mutanti: config'e yazilan deger ELENEN SECENEK
    # 1'e (GORELI `tools/kancalar`) doner. Kurulu kopya yerinde kalir ama git
    # artik AGACIN icindeki yolu cozer -> `tools/kancalar` TASIMAYAN worktree'de
    # HICBIR kanca kosmaz. `V6.olu-agacta-kanca-kosuyor` bu mutanti oldurur.
    ("MU15 kur: config'e GORELI deger yazilir (KUSUR 2-a, elenen secenek 1)",
     "kanca-kur.py",
     '    rc, _o, hata = _git(kok, "config", KAPSAM, AYAR, kurulu)',
     '    rc, _o, hata = _git(kok, "config", KAPSAM, AYAR, KANCA_DIZINI)',
     frozenset({"V2.kurulum-basarili", "V2.deger-mutlak", "V2.idempotent",
                "V3.kurulum-basarili", "V3.deger-oldurucu-degil",
                "V3.worktreeden-kurulur", "V4.saglikli-yesil",
                "V4.yutma-kirmizi", "V4.sapma-kirmizi",
                "V4.rc-kontrolsuz-kirmizi", "V4.gerekce-kirmizi",
                "V6.kurulum-basarili", "V6.olu-agacta-kanca-kosuyor",
                "V6.yeniden-kurulum", "V6.saglikli-agac-yesil",
                "V6.ana-saglikli", "V7.kurulum-basarili"})),

    ("N1 ILGISIZ: yorum eklenir (davranis degismez)",
     "kanca-kablolama-nobeti.py",
     "def genel_hal(bulgular):",
     "# (ilgisiz mutasyon: davranis degismez)\ndef genel_hal(bulgular):",
     frozenset()),
)


def _canli_dosyalar():
    return [KUR, NOBETCI] + [os.path.join(TOOLS, a) for a in YARDIMCILAR] + \
           [os.path.join(KANCA_KAYNAGI, a) for a in sorted(os.listdir(KANCA_KAYNAGI))]


def _iddia_sayisi(cikti):
    for satir in cikti.splitlines():
        if satir.startswith("IDDIA: "):
            try:
                return int(satir.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def _kirmizi_kume(cikti):
    for satir in cikti.splitlines():
        if satir.startswith("KIRMIZI-ETIKET: "):
            govde = satir[len("KIRMIZI-ETIKET: "):].strip()
            return frozenset(x for x in govde.split(",") if x)
    return frozenset()


def mutasyon_turu():
    print("MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosyalar DEGISMEZ")
    once = {y: sha256(y) for y in _canli_dosyalar()}

    taban = subprocess.run([sys.executable, os.path.abspath(__file__), "--sessiz"],
                           capture_output=True, text=True, timeout=1800)
    taban_cikti = taban.stdout + taban.stderr
    taban_iddia = _iddia_sayisi(taban_cikti)
    print("  TABAN: rc=%d iddia=%s kirmizi=%s"
          % (taban.returncode, taban_iddia, sorted(_kirmizi_kume(taban_cikti)) or "{}"))
    kirmizi = []
    if taban.returncode != 0:
        kirmizi.append("TABAN KIRMIZI — mutasyon turu anlamsiz: %s" % taban_cikti[-500:])
    if taban_iddia is None:
        kirmizi.append("TABAN 'IDDIA:' satiri basmadi")

    for ad, dosya, eski, yeni, beklenen in MUTANTLAR:
        canli = os.path.join(TOOLS, dosya)
        kaynak = open(canli, encoding="utf-8").read()
        if eski not in kaynak:
            kirmizi.append("%s :: DESEN BULUNAMADI (mutant bayat) -> %r" % (ad, eski[:60]))
            print("  🔴 %-66s DESEN YOK" % ad[:66])
            continue
        gecici = tempfile.mkdtemp(prefix="kanca-kablolama-mut-")
        try:
            ht = os.path.join(gecici, "tools")
            os.makedirs(ht)
            for a in (os.path.basename(KUR), os.path.basename(NOBETCI)) + YARDIMCILAR:
                shutil.copy2(os.path.join(TOOLS, a), os.path.join(ht, a))
            shutil.copytree(KANCA_KAYNAGI, os.path.join(ht, "kancalar"))
            with open(os.path.join(ht, dosya), "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.abspath(__file__),
                                "--tools", ht, "--sessiz"],
                               capture_output=True, text=True, timeout=1800)
            cikti = p.stdout + p.stderr
            gelen = _kirmizi_kume(cikti)
            iddia = _iddia_sayisi(cikti)
            coktu = "Traceback" in cikti
            tamam = (gelen == beklenen) and not coktu and iddia == taban_iddia
            print("  %s %-66s rc=%d iddia=%s kirmizi=%d"
                  % ("✅" if tamam else "🔴", ad[:66], p.returncode, iddia, len(gelen)))
            if gelen != beklenen:
                kirmizi.append("%s :: KUME ESIT DEGIL\n      beklenen=%s\n      gelen   =%s"
                               % (ad, sorted(beklenen), sorted(gelen)))
            if coktu:
                kirmizi.append("%s :: COKTU (Traceback) — mutant KIRMIZI yakmali, "
                               "COKMEMELI: %s" % (ad, cikti[-300:]))
            if iddia != taban_iddia:
                kirmizi.append("%s :: IDDIA SAYISI DEGISTI (taban=%s mutant=%s)"
                               % (ad, taban_iddia, iddia))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    bozulan = [y for y, h in once.items() if sha256(y) != h]
    print("\nCANLI DOSYA sha256 (%d dosya): %s"
          % (len(once), "HEPSI ESIT ✅" if not bozulan else "DEGISMIS 🔴 %s" % bozulan))
    if bozulan:
        kirmizi.append("CANLI DOSYA DEGISMIS — mutant sizdi: %s" % bozulan)
    print("\nMUTASYON SONUC: %d mutant, %d kirmizi" % (len(MUTANTLAR), len(kirmizi)))
    for k in kirmizi:
        print("  🔴 " + k)
    return 1 if kirmizi else 0


# ---------------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    if "--mutasyon" in argv:
        return mutasyon_turu()
    tools_dizini = TOOLS
    if "--tools" in argv:
        i = argv.index("--tools")
        if i + 1 >= len(argv):
            print("HATA: --tools bir dizin bekler", file=sys.stderr)
            return 2
        tools_dizini = argv[i + 1]
        del argv[i:i + 2]
    sessiz = "--sessiz" in argv
    bilinmeyen = [a for a in argv if a not in ("--sessiz",)]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    if not sessiz:
        print("KANCA KABLOLAMA KABUL TESTI — tools: %s" % tools_dizini)
    try:
        s = kos_vakalar(tools_dizini, ayrintili=not sessiz)
    except Exception as e:
        import traceback
        print("🔴 SUITE PATLADI (%s: %s)" % (type(e).__name__, e))
        traceback.print_exc()
        return 1
    # 🔴 MUTASYON SOZLESMESI: bu iki satir makine tarafindan okunur.
    print("IDDIA: %d" % s.iddia)
    print("KIRMIZI-ETIKET: %s" % ",".join(sorted(set(s.kirmizi))))
    print("SONUC: " + ("YESIL ✅" if not s.kirmizi else "KIRMIZI 🔴"))
    return 1 if s.kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
