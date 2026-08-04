#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-kablolama-test.py — kanca KABLOLAMASININ kabul testi.

Olculen iddialar (hepsi GERCEK `git` ile, SENTETIK depolarda; gercek depoya ve
gercek `~/.gitconfig`'e DOKUNULMAZ):

  VAKA 1 — FAIL-OPEN KAPANDI (UCTAN UCA, gercek `git commit`)
    Guard'i sifir-disi donduren bir senaryo kurulur. AYNI senaryo iki govdeyle
    kosar ve IKISI DE OLCULUR:
      * ESKI govde (`.git/hooks/pre-commit`in 4 Agu 2026 oncesi hali,
        `python3 "$guard" ... >/dev/null 2>&1 || true`)  -> commit GECER (rc=0)
      * IZLENEN govde (tools/kancalar/pre-commit)         -> commit DURUR (rc!=0)
        ve GEREKCE gorunur (guard'in mesaji ciktida gecer).
    "Once gecti, sonra durdu" iki ayri SAYIYLA gosterilir; tek tarafli olcum
    "zaten hep boyleydi" ihtimalini disarida birakmaz.

  VAKA 2 — KURULUM FAIL-CLOSED
    Kurulamayan her hal sifir-disi cikis + SEBEP: izlenen kanca dizini YOK ·
    dizin var ama kanca EKSIK · kurulmamis depoda `--dogrula`. Sessiz "kuruldu"
    YOKTUR: yazimdan sonra etkin deger git'ten YENIDEN okunur.

  🔴 VAKA 3 — PAYLASILAN/GLOBAL CONFIG KIRLENMEDI
    Bu depoda OLCULMUS tuzak: worktree'de BAYRAKSIZ (ve hatta `--local`)
    `git config core.hooksPath` PAYLASILAN `.git/config`e yazar ve TUM
    kancalari oldurur ([[kanca-sessiz-devre-disi]]). Kurulum betigi gecici bir
    depoda kosturulur; global/system config dosyalarinin ve KOMSU bir deponun
    `.git/config`inin sha256'si ONCE=SONRA olculur. Ayrica LINKED WORKTREE'den
    kosum: yazilan dosya ANA checkout'un `.git/config`idir (KASITLI hedef),
    worktree'nin `config.worktree`si KIRLENMEZ ve deger asla oldurucu degildir.
    MU1 (`--local` -> `--global`) bu vakayi KIRMIZI yakar.

  VAKA 4 — NOBETCI AYIRT EDICI (her eksen icin OLDURUCU + tek degiskenli KONTROL)
    kablolama yok · kanca x-bitsiz · `|| true` geri gelmis · guard cagrisi
    silinmis · rc HIC kontrol edilmiyor -> KIRMIZI; saglikli hal -> YESIL.
    🔴 YANLIS-POZITIF KONTROLU: BEYAN EDILMIS fail-open bloklar (yedekle.py,
    kutu-arsivle.py, d1-sync.py) `|| true` tasidiklari halde YESIL kalmali.

  VAKA 5 — CI HALI (yanlis-pozitif butcesi)
    CI checkout'unda kablolama KURULU DEGILDIR. `--ci` halinde eksen K
    OLCULEMEDI olarak ILAN EDILIR (raporda GORUNUR) ve cikis kodunu ETKILEMEZ
    -> rc=0, yayin durmaz. KONTROL: ayni `--ci` halinde izlenen govdeye
    `|| true` enjekte edilirse rc=1 (CI hali bir SESSIZ GECIS deligi degildir).

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
# Mutasyon turunda KOPYALANACAK yardimci dosyalar (nobetci bunlari IMPORT eder).
YARDIMCILAR = ("kanca-nobeti.py", "icra-suzgeci.py")
KANCA_KAYNAGI = os.path.join(TOOLS, "kancalar")

# ---------------------------------------------------------------------------
# 🔴 ESKI GOVDE — `.git/hooks/pre-commit`in 4 Agu 2026 ONCESI hali (birebir).
# Bu bir FIKSTURDUR: "once fail-open'di" iddiasinin KOSULARAK kanitlanmasi icin
# durur. Degistirilmez; onarimin ONCE tarafi budur.
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

# Guard'in REDDETME senaryosu: sifir-disi + stderr'e AYIRT EDICI gerekce.
GUARD_REDDEDER = """#!/usr/bin/env python3
import sys
sys.stderr.write("GUARD-REDDETTI: provenans cozulemedi (sentetik senaryo)\\n")
sys.exit(3)
"""
GECER = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"


# ---------------------------------------------------------------------------
# ALTYAPI
# ---------------------------------------------------------------------------
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

    🔴 NEDEN SART: MU1 mutanti (`--local` -> `--global`) GERCEK `~/.gitconfig`e
    yazardi. Mutasyon turu KULLANICININ makinesini kirletemez; bu yuzden
    mutant da olcum de bu sahte katmanlarda kosar ve kirlenme ORADA olculur."""
    ortam = dict(os.environ)
    ortam["HOME"] = ev
    ortam["XDG_CONFIG_HOME"] = os.path.join(ev, "xdg")
    ortam["GIT_CONFIG_GLOBAL"] = os.path.join(ev, "gitconfig-global")
    ortam["GIT_CONFIG_SYSTEM"] = os.path.join(ev, "gitconfig-system")
    ortam["GIT_CONFIG_NOSYSTEM"] = "0"
    os.makedirs(ortam["XDG_CONFIG_HOME"], exist_ok=True)
    return ortam


def depo_kur(kok, kancalar_kaynagi=KANCA_KAYNAGI, guard=GECER, ortam=None):
    """Izlenen tools/kancalar + sentetik nobetci araclari olan sentetik depo."""
    os.makedirs(kok, exist_ok=True)
    g(kok, "init", "-q", "-b", "main", env=ortam, zorunlu=True)
    g(kok, "config", "user.email", "t@t", env=ortam)
    g(kok, "config", "user.name", "T", env=ortam)
    yaz(os.path.join(kok, "tools", "urunler-guard.py"), guard, True)
    yaz(os.path.join(kok, "tools", "mukerrer-kontrol.py"), GECER, True)
    yaz(os.path.join(kok, "tools", "mimar-commit-kapisi.py"), GECER, True)
    yaz(os.path.join(kok, "tools", "commit-mesaji-kapisi.py"), GECER, True)
    yaz(os.path.join(kok, "tools", "gecmis-geri-donus-kapisi.py"), GECER, True)
    yaz(os.path.join(kok, "tools", "yedekle.py"), GECER, True)
    yaz(os.path.join(kok, "tools", "kutu-arsivle.py"), GECER, True)
    yaz(os.path.join(kok, "tools", "d1-sync.py"), GECER, True)
    if kancalar_kaynagi:
        hedef = os.path.join(kok, "tools", "kancalar")
        os.makedirs(hedef, exist_ok=True)
        for ad in sorted(os.listdir(kancalar_kaynagi)):
            shutil.copy2(os.path.join(kancalar_kaynagi, ad), os.path.join(hedef, ad))
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


def nobetci_yukle(tools_dizini):
    yol = os.path.join(tools_dizini, "kanca-kablolama-nobeti.py")
    spec = importlib.util.spec_from_file_location("pruvo_kablolama_nobetci_test", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_kablolama_nobetci_test"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# VAKALAR
# ---------------------------------------------------------------------------
def kos_vakalar(tools_dizini, ayrintili=True):
    s = Sayac()
    kur_yolu = os.path.join(tools_dizini, "kanca-kur.py")
    nobetci = nobetci_yukle(tools_dizini)
    kok = tempfile.mkdtemp(prefix="kanca-kablolama-test-")

    # 🔴 HER VAKA KENDI global/system KATMANINDA KOSAR. Tek ortak sahte HOME ile
    # OLCULDU ki VAKA 2'nin basarili kurulumu (MU1 mutantinda `--global`) sahte
    # global config'i ONCEDEN kirletiyor; VAKA 3 "once" anlik goruntusunu ondan
    # SONRA aliyor ve `once == sonra` cikiyordu -> KIRLENME ASSERTION'I MUTANTI
    # KOR EDIYORDU ([[fikstur-degeri-mutasyon-koru]]). Izolasyon vaka basinadir.
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
        # ================= VAKA 1: FAIL-OPEN ONCE / SONRA =====================
        if ayrintili:
            print("VAKA 1 — fail-open ONCE/SONRA (gercek git commit)")
        sonuclar = {}
        for etiket_govde, govde in (
                ("eski", ESKI_PRE_COMMIT),
                ("izlenen", open(os.path.join(KANCA_KAYNAGI, "pre-commit"),
                                 encoding="utf-8").read())):
            d = depo_kur(os.path.join(kok, "v1-" + etiket_govde),
                         guard=GUARD_REDDEDER, ortam=ortam)
            kancalar = os.path.join(d, ".git", "hooks")
            yaz(os.path.join(kancalar, "pre-commit"), govde, True)
            yaz(os.path.join(d, "a.txt"), "degisti\n")
            g(d, "add", "a.txt", env=ortam)
            rc, cikti, hata = g(d, "commit", "-m", "ikinci", env=ortam)
            sonuclar[etiket_govde] = (rc, cikti + hata)
            if ayrintili:
                print("    %-8s govde -> commit rc=%d" % (etiket_govde, rc))

        s.bekle("V1.eski-gecer", sonuclar["eski"][0] == 0,
                "ESKI govde (`|| true`) ile guard REDDETTIGI HALDE commit GECMELI "
                "(fail-open kaniti); rc=%d geldi" % sonuclar["eski"][0])
        s.bekle("V1.eski-gerekce-yutulur", "GUARD-REDDETTI" not in sonuclar["eski"][1],
                "ESKI govde gerekceyi YUTMALI (>/dev/null 2>&1) — fikstur dogru "
                "kurulmus olmali")
        s.bekle("V1.izlenen-bloklar", sonuclar["izlenen"][0] != 0,
                "IZLENEN govde ile commit DURMALI; rc=%d geldi (cikti: %r)"
                % (sonuclar["izlenen"][0], sonuclar["izlenen"][1][-200:]))
        s.bekle("V1.gerekce-gorunur", "GUARD-REDDETTI" in sonuclar["izlenen"][1],
                "IZLENEN govde guard'in GEREKCESINI gostermeli; cikti: %r"
                % sonuclar["izlenen"][1][-200:])

        # KONTROL (tek degisken): guard KABUL ederse izlenen govde commit'i
        # DURDURMAMALI — yoksa "her seyi bloklayan" bir kanca da yesil gorunurdu.
        d = depo_kur(os.path.join(kok, "v1-kontrol"), guard=GECER, ortam=ortam)
        yaz(os.path.join(d, ".git", "hooks", "pre-commit"),
            open(os.path.join(KANCA_KAYNAGI, "pre-commit"), encoding="utf-8").read(), True)
        yaz(os.path.join(d, "a.txt"), "degisti\n")
        g(d, "add", "a.txt", env=ortam)
        rc_k, _o, _e = g(d, "commit", "-m", "kontrol", env=ortam)
        s.bekle("V1.kontrol-gecer", rc_k == 0,
                "guard KABUL edince izlenen govde commit'i GECIRMELI; rc=%d" % rc_k)

        # ================= VAKA 2: KURULUM FAIL-CLOSED ========================
        if ayrintili:
            print("VAKA 2 — kurulum fail-closed")
        # (a) izlenen kanca dizini YOK
        d = depo_kur(os.path.join(kok, "v2a"), kancalar_kaynagi=None, ortam=ortam)
        rc, cikti = kur_kos(d)
        s.bekle("V2.dizin-yok-rc", rc != 0,
                "izlenen kanca dizini YOKken kurulum SIFIR-DISI cikmali; rc=%d" % rc)
        s.bekle("V2.dizin-yok-sebep", "kanca dizini YOK" in cikti,
                "sebep BASILMALI; cikti: %r" % cikti[-200:])
        # (b) dizin var ama bir kanca EKSIK
        d = depo_kur(os.path.join(kok, "v2b"), ortam=ortam)
        os.remove(os.path.join(d, "tools", "kancalar", "pre-push"))
        rc, cikti = kur_kos(d)
        s.bekle("V2.eksik-kanca-rc", rc != 0,
                "EKSIK kanca varken kurulum SIFIR-DISI cikmali; rc=%d" % rc)
        s.bekle("V2.eksik-kanca-sebep", "EKSIK kanca" in cikti,
                "eksik kanca adi BASILMALI; cikti: %r" % cikti[-200:])
        # (c) kurulmamis depoda --dogrula: "kuruldu" VARSAYILMAZ
        d = depo_kur(os.path.join(kok, "v2c"), ortam=ortam)
        rc, cikti = kur_kos(d, "--dogrula")
        s.bekle("V2.kurulmamis-dogrula-rc", rc != 0,
                "kurulu OLMAYAN depoda --dogrula SIFIR-DISI cikmali; rc=%d" % rc)
        # (d) SAGLIKLI kurulum + IDEMPOTENS (yanlis-pozitif kontrolu)
        d = depo_kur(os.path.join(kok, "v2d"), ortam=ortam)
        rc1, cikti1 = kur_kos(d)
        s.bekle("V2.kurulum-basarili", rc1 == 0,
                "saglikli depoda kurulum BASARILI olmali; rc=%d cikti=%r"
                % (rc1, cikti1[-300:]))
        _rc, deger, _e = g(d, "config", "--get", "core.hooksPath", env=ortam)
        s.bekle("V2.deger-goreli", deger == "tools/kancalar",
                "yazilan deger GORELI `tools/kancalar` olmali; %r geldi" % deger)
        rc2, cikti2 = kur_kos(d)
        s.bekle("V2.idempotent", rc2 == 0 and "DEGISIKLIK YOK" in cikti2,
                "ikinci kosum IDEMPOTENT olmali; rc=%d cikti=%r" % (rc2, cikti2[-200:]))

        # ================= VAKA 3: PAYLASILAN CONFIG KIRLENMEDI ===============
        if ayrintili:
            print("VAKA 3 — paylasilan/global config kirlenmedi")
        o3 = yeni_ortam("v3")          # TAZE global/system katmani (bkz. yeni_ortam)
        komsu = depo_kur(os.path.join(kok, "v3-komsu"), ortam=o3)
        hedef = depo_kur(os.path.join(kok, "v3-hedef"), ortam=o3)
        once = {
            "global": sha256(o3["GIT_CONFIG_GLOBAL"]),
            "system": sha256(o3["GIT_CONFIG_SYSTEM"]),
            "komsu": sha256(os.path.join(komsu, ".git", "config")),
        }
        s.bekle("V3.taze-katman", once["global"] == "YOK" and once["system"] == "YOK",
                "TUZAK KURULUMU: VAKA 3 TAZE bir global/system katmaninda baslamali "
                "(onceki vakalarin kirlenmesi mutanti KOR EDERDI); once=%s" % once)
        rc, cikti = kur_kos(hedef, env=o3)
        s.bekle("V3.kurulum-basarili", rc == 0,
                "hedef depoya kurulum basarili olmali; rc=%d cikti=%r" % (rc, cikti[-300:]))
        sonra = {
            "global": sha256(o3["GIT_CONFIG_GLOBAL"]),
            "system": sha256(o3["GIT_CONFIG_SYSTEM"]),
            "komsu": sha256(os.path.join(komsu, ".git", "config")),
        }
        s.bekle("V3.global-kirlenmedi", once["global"] == sonra["global"],
                "GLOBAL config DEGISMEMELI (once=%s sonra=%s) — `--global` kapsami "
                "makinedeki TUM depolari kirletirdi" % (once["global"][:12], sonra["global"][:12]))
        s.bekle("V3.system-kirlenmedi", once["system"] == sonra["system"],
                "SYSTEM config DEGISMEMELI (once=%s sonra=%s)"
                % (once["system"][:12], sonra["system"][:12]))
        s.bekle("V3.komsu-kirlenmedi", once["komsu"] == sonra["komsu"],
                "KOMSU deponun .git/config'i DEGISMEMELI (once=%s sonra=%s)"
                % (once["komsu"][:12], sonra["komsu"][:12]))

        # (b) LINKED WORKTREE'den kosum: hedef ANA checkout'tur (KASITLI), ama
        #     worktree'nin config.worktree'si KIRLENMEZ ve deger OLDURUCU DEGILDIR.
        ana = depo_kur(os.path.join(kok, "v3-ana"), ortam=o3)
        g(ana, "config", "extensions.worktreeConfig", "true", env=o3, zorunlu=True)
        wt = os.path.join(kok, "v3-wt")
        g(ana, "worktree", "add", "-q", wt, "-b", "dal", env=o3, zorunlu=True)
        cw = os.path.join(ana, ".git", "worktrees", os.path.basename(wt), "config.worktree")
        cw_once = sha256(cw)
        rc, cikti = kur_kos(wt, env=o3)
        s.bekle("V3.worktreeden-kurulur", rc == 0,
                "worktree'den kosum basarili olmali; rc=%d cikti=%r" % (rc, cikti[-300:]))
        s.bekle("V3.worktree-config-kirlenmedi", cw_once == sha256(cw),
                "worktree'nin config.worktree'si DEGISMEMELI (once=%s sonra=%s)"
                % (cw_once[:12], sha256(cw)[:12]))
        paylasilan = open(os.path.join(ana, ".git", "config"), encoding="utf-8").read()
        s.bekle("V3.ana-config-hedeflendi", "hooksPath" in paylasilan,
                "worktree'den kosum ANA checkout'un .git/config'ine yazmali (KASITLI "
                "hedef); yazilmamis")
        s.bekle("V3.deger-oldurucu-degil",
                "/dev/null" not in paylasilan and "tools/kancalar" in paylasilan,
                "yazilan deger OLDURUCU olmamali ve izlenen dizini gostermeli")
        # Yol karsilastirmasi REALPATH uzerinden: macOS'ta /var -> /private/var
        # symlink'i yuzunden git'in dondurdugu yol fikstur yolundan farklidir.
        s.bekle("V3.hedef-basildi",
                ("config --local core.hooksPath tools/kancalar" in cikti
                 and os.path.realpath(ana) in cikti),
                "kurulum YAZDIGI KOMUTU (kapsam bayragi + hedef depo) BASMALI; "
                "cikti: %r" % cikti[-400:])

        # ================= VAKA 4: NOBETCI AYIRT EDICI ========================
        if ayrintili:
            print("VAKA 4 — nobetci ayirt edici (oldurucu + kontrol)")

        # 🔴 NOBETCI IC-SUREC KOSAR ve `git`i os.environ ile cagirir; fikstur ise
        # SAHTE bir global/system katmaninda kuruldu. Ikisi AYRI katman okursa
        # olcum fiksturun kurdugu dunyayi degil MAKINENIN dunyasini yargilar
        # (gercek `~/.gitconfig`inde core.hooksPath olan bir gelistiricide bu
        # vaka yanlis hukum verirdi). Olcum SIRASINDA ayni katmana baglanir.
        def hukum(depo, ci=False, env=None):
            env = env or o4
            yedek = {k: os.environ.get(k) for k in
                     ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL",
                      "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")}
            os.environ.update({k: env[k] for k in yedek})
            try:
                b = nobetci.denetle(depo, ci=ci, kaynak_kok=depo)
                return nobetci.genel_hal(b), nobetci.cikis_kodu(b, ci), b
            finally:
                for k, v in yedek.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

        o4 = yeni_ortam("v4")          # VAKA 4 de TAZE katmanda kosar

        def kurulu_depo(ad, **kw):
            d = depo_kur(os.path.join(kok, ad), ortam=kw.pop("ortam", o4), **kw)
            rc, c = kur_kos(d, env=o4)
            if rc != 0:
                raise RuntimeError("fikstur kurulamadi: %s -> %s" % (ad, c[-300:]))
            return d

        # (kontrol) SAGLIKLI + KURULU -> YESIL
        saglikli = kurulu_depo("v4-saglikli")
        h, rc, b = hukum(saglikli)
        s.bekle("V4.saglikli-yesil", h == nobetci.YESIL and rc == 0,
                "saglikli+kurulu depo YESIL olmali; %s (rc=%d) -> %s"
                % (h, rc, [(e, x) for e, x, _m in b if x != nobetci.YESIL]))
        # 🔴 YANLIS-POZITIF: pre-push'taki BEYAN EDILMIS fail-open bloklar
        # (`yedekle.py ... || true` vb.) yesil kalmali.
        pp = open(os.path.join(saglikli, "tools", "kancalar", "pre-push"),
                  encoding="utf-8").read()
        s.bekle("V4.beyanli-failopen-fiksturde", "|| true" in pp or ">/dev/null 2>&1" in pp,
                "TUZAK KURULUMU: pre-push fiksturunde beyan edilmis fail-open deyim "
                "GECMELI (yoksa yanlis-pozitif ekseni olculmemis olur)")

        # (oldurucu 1) kablolama YOK
        d = depo_kur(os.path.join(kok, "v4-kablosuz"), ortam=o4)
        h, rc, b = hukum(d)
        s.bekle("V4.kablolamasiz-kirmizi",
                any(e == "k) kablolama" and x == nobetci.KIRMIZI for e, x, _m in b) and rc != 0,
                "kablolama kurulu DEGILKEN eksen K KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        # (oldurucu 2) kanca x-BITSIZ
        d = kurulu_depo("v4-xbitsiz")
        os.chmod(os.path.join(d, "tools", "kancalar", "pre-commit"), 0o644)
        h, rc, b = hukum(d)
        s.bekle("V4.xbitsiz-kirmizi", h == nobetci.KIRMIZI and rc != 0,
                "x-bitsiz kanca KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        # (oldurucu 3) `|| true` GERI GELMIS
        d = kurulu_depo("v4-yutma")
        y = os.path.join(d, "tools", "kancalar", "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('python3 "$pruvo_guard" --tetik commit\n',
                             'python3 "$pruvo_guard" --tetik commit >/dev/null 2>&1 || true\n')
        s.bekle("V4.yutma-mutant-uygulandi", yeni != govde,
                "mutant fiilen uygulanmali (desen bulunmali)")
        yaz(y, yeni, True)
        h, rc, b = hukum(d)
        s.bekle("V4.yutma-kirmizi",
                any(e.startswith("y) pre-commit -> tools/urunler-guard.py")
                    and x == nobetci.KIRMIZI for e, x, _m in b) and rc != 0,
                "`|| true` geri gelince eksen Y KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        # (oldurucu 4) cagri SILINMIS
        d = kurulu_depo("v4-cagrisiz")
        y = os.path.join(d, "tools", "kancalar", "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('python3 "$pruvo_guard" --tetik commit\n',
                             '# python3 "$pruvo_guard" --tetik commit\n')
        s.bekle("V4.cagrisiz-mutant-uygulandi", yeni != govde, "mutant uygulanmali")
        yaz(y, yeni, True)
        h, rc, b = hukum(d)
        s.bekle("V4.cagrisiz-kirmizi", h == nobetci.KIRMIZI and rc != 0,
                "cagri yoruma alininca KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        # (oldurucu 5) cagri DURUYOR, `|| true` YOK, ama rc HIC kontrol edilmiyor
        # 🔴 EKSEN B: yutma deseni listesinden kacan her fail-open'i yakalayan kol.
        d = kurulu_depo("v4-rcsiz")
        y = os.path.join(d, "tools", "kancalar", "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('pruvo_guard_rc=$?\n', 'pruvo_guard_rc=0\n')
        s.bekle("V4.rcsiz-mutant-uygulandi", yeni != govde, "mutant uygulanmali")
        yaz(y, yeni, True)
        # 🔴 TUZAK KURULUMU, SATIR EKSENINDE: govdenin BASLIK YORUMU tarihsel
        # fail-open satiri ORNEK olarak alintiladigi icin "govdede `|| true`
        # gecmesin" demek YANLIS olurdu ([[nobetci-kendi-dosyasinda-sizinti]]).
        # Olculen sey CAGRI SATIRIDIR: cagri duruyor, uzerinde yutma deyimi YOK.
        _cagri_satirlari = [l for l in yeni.splitlines()
                            if 'python3 "$pruvo_guard"' in l and not l.strip().startswith("#")]
        s.bekle("V4.rcsiz-cagri-duruyor",
                len(_cagri_satirlari) == 1
                and "|| true" not in _cagri_satirlari[0]
                and "/dev/null" not in _cagri_satirlari[0],
                "TUZAK KURULUMU: cagri satiri DURMALI ve uzerinde yutma deyimi "
                "OLMAMALI (yalniz eksen B ayirt edebilsin); satirlar=%r"
                % _cagri_satirlari)
        h, rc, b = hukum(d)
        s.bekle("V4.rc-kontrolsuz-kirmizi",
                any(e.startswith("y) pre-commit -> tools/urunler-guard.py")
                    and x == nobetci.KIRMIZI for e, x, _m in b) and rc != 0,
                "rc HIC kontrol edilmiyorsa KIRMIZI olmali; %s (rc=%d)" % (h, rc))

        # ================= VAKA 5: CI HALI ====================================
        if ayrintili:
            print("VAKA 5 — CI hali (yanlis-pozitif butcesi)")
        o5 = yeni_ortam("v5")
        d = depo_kur(os.path.join(kok, "v5-ci"), ortam=o5)   # KABLOLAMA YOK
        h, rc, b = hukum(d, ci=True, env=o5)
        s.bekle("V5.ci-rc-sifir", rc == 0,
                "CI halinde (kablolama kurulu degil) rc=0 olmali — yoksa her yayin "
                "durur; rc=%d, kirmizilar=%s"
                % (rc, [(e, m) for e, x, m in b if x == nobetci.KIRMIZI]))
        s.bekle("V5.ci-kablolama-ilan",
                any(e == "k) kablolama" and x == nobetci.OLCULEMEDI for e, x, _m in b),
                "CI halinde eksen K OLCULEMEDI olarak ILAN EDILMELI (sessizce "
                "atlanmamali)")
        # KONTROL: CI hali bir SESSIZ GECIS deligi degil — kaynakta `|| true` -> rc=1
        y = os.path.join(d, "tools", "kancalar", "pre-commit")
        govde = open(y, encoding="utf-8").read()
        yaz(y, govde.replace('python3 "$pruvo_guard" --tetik commit\n',
                             'python3 "$pruvo_guard" --tetik commit || true\n'), True)
        h2, rc2, _b2 = hukum(d, ci=True, env=o5)
        s.bekle("V5.ci-yutma-kirmizi", rc2 != 0,
                "CI halinde de izlenen kaynaktaki `|| true` KIRMIZI yakmali; rc=%d" % rc2)

    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return s


# ---------------------------------------------------------------------------
# MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosyalar DEGISMEZ
# ---------------------------------------------------------------------------
# Her mutant, KIRMIZI yakmasi beklenen iddia etiketlerinin TAM KUMESINI beyan
# eder. Driver TAM ESITLIK arar: eksik oldurme de FAZLA oldurme de KIRMIZI'dir
# (fazla oldurme, eksenlerin birbirine sizdigini gosterir).
MUTANTLAR = (
    # 🔴 MU1 BILEREK GENIS BIR MUTANTTIR ve imzasi 5 etikettir. Kapsam bayragini
    # makine capina cikarmak TEK bir ekseni degil "deger BU DEPONUN config'ine
    # indi mi" varsayimina dayanan HER ekseni devirir; imza OLCULEREK sabitlendi
    # (tahminle DEGIL — ilk beyan 2 etiketti, kosum 5 gosterdi ve fark bu dosyada
    # IKI GERCEK fikstur hatasi buldu: paylasilan sahte HOME'un onceki vakalarca
    # kirletilmesi ve olcumun fiksturden BASKA bir config katmanini okumasi).
    #   V3.global-kirlenmedi     -> makine capindaki katman FIILEN kirlendi
    #   V3.hedef-basildi         -> basilan komutta artik `--local` yok
    #   V3.ana-config-hedeflendi -> deger ANA checkout'un .git/config'ine INMEDI
    #   V3.deger-oldurucu-degil  -> ayni sebeple ana config'de izlenen yol YOK
    #   V4.kablolamasiz-kirmizi  -> EN PAHALI SONUC: global katman yuzunden
    #      HIC KURULMAMIS bir depo da "kurulu" gorunur; nobetci kurulmamis hali
    #      artik ayirt edemez (sessiz yesil).
    ("MU1 kur: KAPSAM --local -> --global (makine capinda kirlenme)",
     "kanca-kur.py", 'KAPSAM = "--local"', 'KAPSAM = "--global"',
     frozenset({"V3.global-kirlenmedi", "V3.hedef-basildi",
                "V3.ana-config-hedeflendi", "V3.deger-oldurucu-degil",
                "V4.kablolamasiz-kirmizi"})),

    ("MU2 kur: fail-closed devrilir (Hata -> cikis 0)",
     "kanca-kur.py",
     '            print("🔴 KURULAMADI: %s" % e, file=sys.stderr)\n            return 1',
     '            print("🔴 KURULAMADI: %s" % e, file=sys.stderr)\n            return 0',
     frozenset({"V2.dizin-yok-rc", "V2.eksik-kanca-rc"})),

    ("MU3 kur: kur->DOGRULA halkasi kirilir (kurulmamis hal yesil sayilir)",
     "kanca-kur.py",
     '        bulgular.append(("kablolama", False,',
     '        bulgular.append(("kablolama", True,',
     frozenset({"V2.kurulmamis-dogrula-rc"})),

    ("MU4 nobetci: YUTMA deseni listesi bosaltilir (`|| true` kabul edilir)",
     "kanca-kablolama-nobeti.py",
     "    for desen, tarif in YUTMA_DESENLERI:",
     "    for desen, tarif in ():",
     frozenset({"V4.yutma-kirmizi", "V5.ci-yutma-kirmizi"})),

    ("MU5 nobetci: EKSEN B oldurulur (rc kontrolu aranmaz)",
     "kanca-kablolama-nobeti.py",
     "def bloklama_hukmu(etkili, indeks, ham):",
     "def bloklama_hukmu(etkili, indeks, ham):\n    return True, None",
     frozenset({"V4.rc-kontrolsuz-kirmizi"})),

    ("MU6 nobetci: EKSEN K oldurulur (ayarsiz hooksPath yesil sayilir)",
     "kanca-kablolama-nobeti.py",
     '    if deger is None:\n        return ("k) kablolama", KIRMIZI,',
     '    if deger is None:\n        return ("k) kablolama", YESIL,',
     frozenset({"V4.kablolamasiz-kirmizi"})),

    ("N1 ILGISIZ: yorum eklenir (davranis degismez)",
     "kanca-kablolama-nobeti.py",
     "def genel_hal(bulgular):",
     "# (ilgisiz mutasyon: davranis degismez)\ndef genel_hal(bulgular):",
     frozenset()),
)


def _canli_dosyalar():
    return [KUR, NOBETCI] + [os.path.join(TOOLS, a) for a in YARDIMCILAR] + \
           [os.path.join(KANCA_KAYNAGI, a) for a in sorted(os.listdir(KANCA_KAYNAGI))]


def mutasyon_turu():
    print("MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosyalar DEGISMEZ")
    once = {y: sha256(y) for y in _canli_dosyalar()}

    # TABAN: mutasyonsuz kosum. Iddia sayisi ve kirmizi kume buradan gelir.
    taban = subprocess.run([sys.executable, os.path.abspath(__file__), "--sessiz"],
                           capture_output=True, text=True, timeout=900)
    taban_cikti = taban.stdout + taban.stderr
    taban_iddia = _iddia_sayisi(taban_cikti)
    print("  TABAN: rc=%d iddia=%s kirmizi=%s"
          % (taban.returncode, taban_iddia, _kirmizi_kume(taban_cikti) or "{}"))
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
            print("  🔴 %-64s DESEN YOK" % ad[:64])
            continue
        gecici = tempfile.mkdtemp(prefix="kanca-kablolama-mut-")
        try:
            ht = os.path.join(gecici, "tools")
            os.makedirs(ht)
            for a in (os.path.basename(KUR), os.path.basename(NOBETCI)) + YARDIMCILAR:
                shutil.copy2(os.path.join(TOOLS, a), os.path.join(ht, a))
            with open(os.path.join(ht, dosya), "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.abspath(__file__),
                                "--tools", ht, "--sessiz"],
                               capture_output=True, text=True, timeout=900)
            cikti = p.stdout + p.stderr
            gelen = _kirmizi_kume(cikti)
            iddia = _iddia_sayisi(cikti)
            coktu = "Traceback" in cikti
            tamam = (gelen == beklenen) and not coktu and iddia == taban_iddia
            print("  %s %-64s rc=%d iddia=%s kirmizi=%s"
                  % ("✅" if tamam else "🔴", ad[:64], p.returncode, iddia,
                     sorted(gelen) or "{}"))
            if gelen != beklenen:
                kirmizi.append("%s :: KUME ESIT DEGIL — beklenen=%s gelen=%s"
                               % (ad, sorted(beklenen), sorted(gelen)))
            if coktu:
                kirmizi.append("%s :: COKTU (Traceback) — mutant KIRMIZI yakmali, "
                               "COKMEMELI: %s" % (ad, cikti[-300:]))
            if iddia != taban_iddia:
                kirmizi.append("%s :: IDDIA SAYISI DEGISTI (taban=%s mutant=%s) — "
                               "suite kisalmis, olculen yuzey kucuklu"
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
