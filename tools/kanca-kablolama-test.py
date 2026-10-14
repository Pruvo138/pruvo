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

  🔴 VAKA 5 — CI HALI + KAPSAM DISI AYRIMI
    `--ci` halinde eksen K/S KAPSAM DISI ilan edilir, rc=0 ve genel_hal YESIL.
    OLCULEMEDI fail-closed'dir: BASKA bir eksen OLCULEMEDI olursa (kanca dosyasi
    okunamiyor) rc=1 (curutucu deligi H — OLCULEMEDI kolu atlarsa gercek ariza
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

  🔴 VAKA 10 — INDIRME KAPISI (14 Eki 2026, olculen olay: eski tabanli agacin
    commit'i baska dalin serdigi YENI pre-push'u eskisiyle ezdi)
      (a) KONTROL: eski kopya + YENI agactan `--tazele` -> yeniden serilir (rc 3).
      (b) yeni kopya + ESKI agactan (ata) `--tazele` -> kopya DEGISMEZ, rc 0,
          UYARI gorunur.
      (c) ayrisik dal (kanca kaynagini yalniz kurulu taraf degistirmis) -> DEGISMEZ.
      (d) uctan uca `git commit`: eski agacin KAPISIZ kanca-kur.py'si kosmaz;
          kanca yanina serilmis araci cagirir -> kopya DEGISMEZ.
      (e) kopya ELLE DUZENLENMISSE (damgadan sapma) -> yeniden serilir (rc 3).
      (f) KIRLI damga (stage'li degisiklikten serim; HEAD yalniz taban): ayni
          tabandaki ve ilgisiz commit'lerle ilerlemis temiz agac EZMEZ; KONTROL:
          kanca kaynagini degistiren ana hat kazanir (takilma yok).
      (g..o) 14 Eki bagimsiz curutucu bulgulari: sahipsiz (detached/amend) damga
          ve agaci silinmis kirli damga eski agaca kapi ACMAZ · kirli damga
          commit'le kesinlesir · derlenmeyen kanca-kur SERILMEZ · git_ortami
          ping-pong YOK · catismada ana hat disi dal ezemez · post-checkout /
          post-merge / pre-push da kurulu araci cagirir · acik kurulum damgalar ·
          miras GIT_DIR silinir.
      (p..t) curutme 2. tur: kirli (yarim) kopya ZAYIF — tabanina esit/yeni
          commit'li agaca yenilir, commit'lenince post-commit kesinlestirir ·
          import'u kosmayan arac (duman testi) SERILMEZ · kurulu arac bozuksa
          kanca agacin aracina duser · ana checkout gerideyken acik kurulum
          indirmez (`--zorla` ezer) · gc'lenmis damga commit'inde ana hat disi
          aday reddedilir · uc kanca da `--depo` ile agacin kendi kaynagini olcer.

Kullanim:
    python3 tools/kanca-kablolama-test.py
    python3 tools/kanca-kablolama-test.py --mutasyon
    python3 tools/kanca-kablolama-test.py --tools <dizin>   # (mutasyon ic kullanimi)
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from git_ortami import sentetik_git

TOOLS = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(TOOLS, "kanca-kur.py")
NOBETCI = os.path.join(TOOLS, "kanca-kablolama-nobeti.py")
# git_ortami.py: kanca-kur.py onu IMPORT eder (mutant dizininde de bulunmali).
YARDIMCILAR = ("kanca-nobeti.py", "icra-suzgeci.py", "git_ortami.py")
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


def _gecici_kok(prefix):
    """🔴 ORTAM YALITIMI: tempfile.mkdtemp KOKU realpath-NORMALIZE eder.

    NEDEN (4 Agu 2026, olculdu): macOS'ta `/var` -> `/private/var` SEMBOLIK
    BAGLIDIR, dolayisiyla `tempfile.mkdtemp()` HAM yol (`/var/...`) doner ama
    `git rev-parse --path-format=absolute` GERCEK yolu (`/private/var/...`)
    verir. Kurulum config'e GERCEK yolu yazar; MU4 mutanti `kurulu_dizin`i
    git-rev-parse'tan gecmeyen HAM `os.path.join(baslangic, ...)`e cevirir ->
    `beklenen` HAM, `deger` GERCEK olur ve YALNIZ raw!=realpath olan ortamda
    (mac) ayrisir. Sonuc: MU4'un oldurdugu kume mac'te `V4.saglikli-yesil`
    iceriyordu, Linux CI'da (`/tmp` bagli DEGIL) icermiyordu -> ayni batarya
    yerelde YESIL, CI'da KIRMIZI. Koku BASTAN realpath'e cozerek raw==realpath
    invaryantini TUM ortamlarda saglar; MU4 artik her yerde AYNI kumeyi oldurur
    ([[ikiz-tanim-sessiz-ayrisma]])."""
    return os.path.realpath(tempfile.mkdtemp(prefix=prefix))


def g(cwd, *args, **kw):
    p = sentetik_git(cwd, *args, capture_output=True, text=True, timeout=60,
                      ek_ortam=kw.get("env"), kimlik_ad="T", kimlik_eposta="t@t")
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


# 🔴 ELLE TUTULAN STUB LISTESI YOK (9 Agu 2026): adlar IZLENEN kanca kaynaklarindan
# TURETILIR. Elle liste her yeni fail-closed kanca adiminda bayatliyor ve fikstur
# drift'i yayini durduruyordu ([[envanter-drift-parti-basina]] ·
# [[tekil-yama-sinifi-kapatmaz]]); main'in `e56705a2`'de `diriltme-kapisi.py` icin
# kaldirdigi sinif tam da budur. Capa: `"$degisken/tools/<ad>.py"` — degisken
# ADINDAN bagimsiz, duz prozadaki "tools/foo.py" YAKALANMAZ.
_KANCA_ARAC_KALIBI = re.compile(
    r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/tools/([A-Za-z0-9_.-]+\.py)")
# STUB SERILMEYENLER: `kanca-kur.py`yi VAKA 8 GERCEK dosya olarak kendisi serer
# (kanca `--tazele` icin gercek mantik sart); stub onu golgelerdi.
_STUB_DISI = ("kanca-kur.py",)


def _kanca_arac_adlari(kanca_kaynagi):
    """Kanca govdelerinin cagirdigi `tools/*.py` adlari (stub serilecek kume).

    FAIL-CLOSED: kume BOS donerse sessizce "0 arac gerekiyormus" DENMEZ — istisna
    atilir ([[olculdu-diyen-hukum-kaniti]])."""
    bulunan = set()
    for ad in sorted(os.listdir(kanca_kaynagi)):
        yol = os.path.join(kanca_kaynagi, ad)
        if not os.path.isfile(yol):
            continue
        with open(yol, encoding="utf-8", errors="replace") as f:
            bulunan.update(_KANCA_ARAC_KALIBI.findall(f.read()))
    bulunan -= set(_STUB_DISI)
    if not bulunan:
        raise RuntimeError(
            "FIKSTUR FAIL-CLOSED: izlenen kanca kaynaklarinda HIC `$kok/tools/*.py` "
            "referansi YOK -> stub listesi TURETILEMEDI. Capa bayatlamis olabilir.")
    return tuple(sorted(bulunan))


def _araclari_ser(kok, kanca_kaynagi):
    """Sentetik depoya stub `tools/*.py` serer (adlar KANONIK kaynaktan turetilir).

    🔴 CAKISMA COZUMU (9 Agu 2026): main `3e7f1b24` AYNI refactor'u bagimsiz yapti
    (`\\btools/(...)\\b` prozadan da yakalar, bos kume kontrolu YOK, `kanca-kur.py`
    da stub'lanir). DALIN SURUMU KORUNDU cunku: (a) capa `$degisken/tools/<ad>.py`
    ATAMA eksenidir -> yorumdaki duz "tools/foo.py" prozasi stub uretmez, (b) bos
    kume FAIL-CLOSED istisna atar (sessiz '0 arac gerekiyormus' YOK), (c)
    `_STUB_DISI` `kanca-kur.py`yi disarida birakir — VAKA 8 onu GERCEK dosya olarak
    kendisi serer, stub golgelerdi. Main'in daha genis regex'ine DONULMEDI.

    Stub'lar fiilen HICBIR IS YAPMAZ; varliklari kancalarin "arac YOK" kolunu
    tetiklememesi icindir."""
    for ad in _kanca_arac_adlari(kanca_kaynagi):
        yaz(os.path.join(kok, "tools", ad), GECER, True)


def depo_kur(kok, kanca_kaynagi, guard=GECER, ortam=None, kancalar=True):
    """Izlenen tools/kancalar + sentetik nobetci araclari olan sentetik depo."""
    os.makedirs(kok, exist_ok=True)
    g(kok, "init", "-q", "-b", "main", env=ortam, zorunlu=True)
    g(kok, "config", "extensions.worktreeConfig", "true", env=ortam)
    _araclari_ser(kok, kanca_kaynagi)
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
    # 🔴 realpath-NORMALIZE: symlinked temp koku (mac /var) MU4 kill kumesini
    # ortama bagimli yapardi -> _gecici_kok raw==realpath invaryantini saglar.
    kok = _gecici_kok("kanca-kablolama-test-")

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

    def gercek_kur_ser(depo):
        """GERCEK kanca-kur.py + import ettigi git_ortami.py (kanca `--tazele`
        icin gercek mantik sart; ikisi birlikte kurulu kopyanin yanina serilir)."""
        for a in ("kanca-kur.py", "git_ortami.py"):
            shutil.copy2(os.path.join(tools_dizini, a), os.path.join(depo, "tools", a))

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
        s.bekle("V5.ci-kablolama-ilan",
                any(e == nobetci.EKSEN_KABLOLAMA and x == nobetci.KAPSAM_DISI
                    for e, x, _m in b),
                "CI halinde eksen K KAPSAM DISI olarak ILAN EDILMELI")
        s.bekle("V5.ci-sapma-ilan",
                any(e == nobetci.EKSEN_SAPMA and x == nobetci.KAPSAM_DISI
                    for e, x, _m in b),
                "CI halinde eksen S KAPSAM DISI olarak ILAN EDILMELI")
        s.bekle("V5.ci-hal-yesil", h == nobetci.YESIL,
                "CI halinde KAPSAM DISI hukum dusurmez -> genel_hal YESIL olmali; %s" % h)
        # 🔴 CURUTUCU DELIGI H (guncel): CI'da HERHANGI bir eksenin OLCULEMEDI'si rc=1.
        dh = depo_kur(os.path.join(kok, "v5-okunamaz"), kanca_kaynagi, ortam=o5)
        okunamaz = os.path.join(dh, "tools", "kancalar", "pre-commit")
        os.chmod(okunamaz, 0o000)
        try:
            hh, rch, bh = hukum(dh, ci=True, env=o5)
            olculemeyenler = [e for e, x, _m in bh if x == nobetci.OLCULEMEDI]
            s.bekle("V5.ci-muafiyet-dar-fikstur", bool(olculemeyenler),
                    "TUZAK KURULUMU: bir eksen OLCULEMEDI olmali "
                    "(yoksa darlik olculmemis olur); bulgular=%s"
                    % [(e, x) for e, x, _m in bh])
            s.bekle("V5.ci-hal-olculemedi", hh == nobetci.OLCULEMEDI,
                    "v5-okunamaz'da genel_hal OLCULEMEDI olmali; %s" % hh)
            mutant_nobetci = os.path.join(tools_dizini, "kanca-kablolama-nobeti.py")
            p_ci = subprocess.run([sys.executable, mutant_nobetci, "--ci", "--depo", dh],
                                  capture_output=True, text=True, env=o5, timeout=60)
            ci_cikti = p_ci.stdout + p_ci.stderr
            if "SONUC:" in ci_cikti:
                sonuc_kismi = ci_cikti.split("SONUC:", 1)[1].splitlines()[0]
                hukum_kelimesi = sonuc_kismi.split("(")[0].split("[")[0].strip()
            else:
                sonuc_kismi = ""
                hukum_kelimesi = "YOK"
            s.bekle("V5.ci-ozet-olculemedi", hukum_kelimesi == nobetci.OLCULEMEDI,
                    "CI ciktisindaki SONUC hukum kelimesi OLCULEMEDI olmali; "
                    "bulunan=%r (satir: %r)" % (hukum_kelimesi, sonuc_kismi))
            s.bekle("V5.ci-muafiyet-dar", rch != 0,
                    "CI'da HERHANGI bir eksen OLCULEMEDI iken rc SIFIR-DISI olmali "
                    "(muafiyet yok); rc=%d" % rch)
        finally:
            os.chmod(okunamaz, 0o644)

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

        # ================= VAKA 8: BAYAT KOPYA (DELIK 1) =====================
        # 🔴 `git pull` izlenen kaynagi guncelleyince kurulan KOPYA bayat kalir
        # ve commit aninda SESSIZCE eski mantigi kosturur. Kanca govdesindeki
        # `--tazele` kolu bunu FAIL-CLOSED yakalamali.
        if ayrintili:
            print("VAKA 8 — bayat kopya (DELIK 1: tazele kolu)")
        o8 = yeni_ortam("v8")

        def bayat_kopya_senaryo(tazele_var):
            """Kaynak degisir, kopya bayat kalir; sonraki commit YENI mantigi
            kosturuyor mu? tazele_var=False ONCE halini (ilk tur) taklit eder."""
            d = depo_kur(os.path.join(kok, "v8-%s" % ("var" if tazele_var else "yok")),
                         kanca_kaynagi, ortam=o8)
            # kanca-kur.py GERCEK dosya (kanca `--tazele` icin onu cagirir)
            gercek_kur_ser(d)
            rc, c = kur_kos(d, env=o8)
            if rc != 0:
                print("    ⚠️ v8 kurulum basarisiz: %s" % c[-200:])
            if not tazele_var:
                # ONCE halini uret: kurulu KOPYANIN pre-commit'inden --tazele
                # blogunu cikar (ilk turda bu blok yoktu).
                kopya = os.path.join(kurulu_yolu(d), "pre-commit")
                g0 = open(kopya, encoding="utf-8").read()
                g1 = re.sub(r"# --- 0\) KOPYA TAZELIGI.*?# --- 1\)", "# --- 1)",
                            g0, flags=re.S)
                yaz(kopya, g1, True)
                # (14 Eki) post-commit'in damga kesinlestirme tazelesi de o turda
                # yoktu -> ONCE halinde o da cikarilir.
                pck = os.path.join(kurulu_yolu(d), "post-commit")
                p0 = open(pck, encoding="utf-8").read()
                yaz(pck, re.sub(r"# KANCA DAMGASI KESINLESTIRME.*?\nfi\n", "", p0,
                                flags=re.S), True)
            # kaynak degisir, kopyaya DOKUNULMAZ
            pc = os.path.join(d, "tools", "kancalar", "pre-commit")
            gg = open(pc, encoding="utf-8").read()
            yaz(pc, gg.replace("#!/bin/sh\n", '#!/bin/sh\necho "YENI-MANTIK" >&2\n', 1), True)
            g(d, "add", "-A", env=o8)
            # commit A: kaynak degisti, kopya bayat. tazele VARsa burada BLOKLANIR.
            rc_a, _oa, _ea = g(d, "commit", "-m", "kaynak guncellendi", env=o8)
            yaz(os.path.join(d, "b.txt"), "y\n")
            g(d, "add", "-A", env=o8)
            rc_b, ob, eb = g(d, "commit", "-m", "dene", env=o8)
            return rc_a, ("YENI-MANTIK" in (ob + eb))

        _a_once, v8_once = bayat_kopya_senaryo(tazele_var=False)
        a_sonra, v8_sonra = bayat_kopya_senaryo(tazele_var=True)
        if ayrintili:
            print("    ONCE (tazele YOK): YENI mantik kostu mu? %s" % v8_once)
            print("    SONRA (tazele VAR): stale-commit rc=%d, YENI mantik kostu mu? %s"
                  % (a_sonra, v8_sonra))
        # ONCE: bayat kopya SESSIZCE eski mantigi kosturur (YENI gorunmez) -> delik
        s.bekle("V8.once-sessiz", v8_once is False,
                "TUZAK KURULUMU: tazele YOKken bayat kopya ESKI mantigi sessizce "
                "kosturmali (delik gosterilsin); YENI gorundu=%s" % v8_once)
        # SONRA-A: bayat kopyayla yapilan commit DURMALI (stale wiring sessizce kosmaz)
        s.bekle("V8.sonra-A-durdu", a_sonra != 0,
                "tazele VARken BAYAT kopyayla yapilan commit DURMALI (rc!=0); "
                "rc=%d" % a_sonra)
        # SONRA-B: tazelendikten sonra bir sonraki commit YENI mantikla kosar
        s.bekle("V8.sonra-yakalandi", v8_sonra is True,
                "tazele VARken bayat kopya tazelenmeli ve sonraki commit YENI "
                "mantikla kosmali; YENI gorundu=%s" % v8_sonra)

        # ================= VAKA 9: GOLGELEYEN WORKTREE (DELIK 2) =============
        # 🔴 Bir linked worktree'nin config.worktree'si kurulan degeri GERCEK bir
        # yola golgeliyorsa, o worktree kurulumdan SONRA da ESKI kancalari
        # kosturur. Kurulum "ETKIN ✅" DEMEMELI; sifir-disi + gercek care.
        if ayrintili:
            print("VAKA 9 — golgeleyen worktree (DELIK 2)")
        o9 = yeni_ortam("v9")
        ana9 = depo_kur(os.path.join(kok, "v9-ana"), kanca_kaynagi, ortam=o9)
        # (KONTROL) golge YOK -> kurulum rc=0
        wt9k = os.path.join(kok, "v9-wt-kontrol")
        g(ana9, "worktree", "add", "-q", wt9k, "-b", "kontrol", env=o9, zorunlu=True)
        rc9k, c9k = kur_kos(wt9k, env=o9)
        s.bekle("V9.golge-yok-rc0", rc9k == 0,
                "KONTROL: golge YOKken worktree'den kurulum rc=0 olmali; rc=%d "
                "cikti=%r" % (rc9k, c9k[-200:]))
        # (OLDURUCU) gercek-yol golge -> kurulum rc!=0 + care
        eski_hooks = os.path.join(kok, "v9-eski-hooks")
        os.makedirs(eski_hooks)
        yaz(os.path.join(eski_hooks, "pre-commit"), GECER, True)
        wt9 = os.path.join(kok, "v9-wt-golge")
        g(ana9, "worktree", "add", "-q", wt9, "-b", "golge", env=o9, zorunlu=True)
        g(wt9, "config", "--worktree", "core.hooksPath", eski_hooks, env=o9, zorunlu=True)
        rc9, c9 = kur_kos(wt9, env=o9)
        s.bekle("V9.golge-rc-sifirdisi", rc9 != 0,
                "gercek-yol golge varken kurulum SIFIR-DISI cikmali (yanlis birimde "
                "'ETKIN ✅' YASAK); rc=%d" % rc9)
        s.bekle("V9.golge-care-basildi",
                "--worktree --unset" in c9 and "GOLGELIYOR" in c9,
                "gercek care BASILMALI (git config --worktree --unset ...); "
                "cikti=%r" % c9[-300:])
        # (KONTROL, tek degisken: /dev/null golge KASITLI izolasyon -> rc=0 + NOT)
        wt9d = os.path.join(kok, "v9-wt-devnull")
        g(ana9, "worktree", "add", "-q", wt9d, "-b", "izole9", env=o9, zorunlu=True)
        g(wt9d, "config", "--worktree", "core.hooksPath", "/dev/null", env=o9, zorunlu=True)
        rc9d, c9d = kur_kos(wt9d, env=o9)
        s.bekle("V9.devnull-golge-rc0", rc9d == 0,
                "/dev/null golgesi KASITLI izolasyondur -> rc=0 olmali (yanlis-pozitif "
                "yok); rc=%d cikti=%r" % (rc9d, c9d[-200:]))

        # ================= VAKA 10: INDIRME KAPISI (14 Eki) ==================
        # 🔴 OLCULEN OLAY: bir dal YENI pre-push serdi; ESKI tabanli baska bir
        # agacin commit'i `--tazele` ile eski kaynagi ustune serdi ("BAYATTI ->
        # yeniden serildi") ve yeni blok TUM evler icin sessizce silindi.
        if ayrintili:
            print("VAKA 10 — indirme kapisi (eski agac yeni kopyayi ezmez)")
        o10 = yeni_ortam("v10")
        ana10 = depo_kur(os.path.join(kok, "v10-ana"), kanca_kaynagi, ortam=o10)
        gercek_kur_ser(ana10)
        g(ana10, "add", "-A", env=o10)
        g(ana10, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "kur",
          env=o10, zorunlu=True)
        rc10k, c10k = kur_kos(ana10, env=o10)
        if rc10k != 0:
            print("    ⚠️ v10 kurulum basarisiz: %s" % c10k[-200:])
        _r, c0_10, _e = g(ana10, "rev-parse", "HEAD", env=o10)
        kurulu10 = kurulu_yolu(ana10)
        pp10 = os.path.join(kurulu10, "pre-push")

        def damga10():
            try:
                with open(os.path.join(kurulu10, ".kaynak-damgasi.json"),
                          encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                return {}

        # (n) acik kurulum da damgalar (yoksa ilk --tazele eskiyi taniyamaz)
        s.bekle("V10.kur-damgalar", damga10().get("commit") == c0_10,
                "acik kurulum kaynak damgasini (commit=%s) yazmali; damga=%r"
                % (c0_10[:12], damga10()))
        wt10 = os.path.join(kok, "v10-wt-eski")
        g(ana10, "worktree", "add", "-q", wt10, "-b", "eski", env=o10, zorunlu=True)
        # ana hatta kanca kaynagi ILERLER: pre-push'a YENI blok
        kaynak_pp = os.path.join(ana10, "tools", "kancalar", "pre-push")
        govde = open(kaynak_pp, encoding="utf-8").read()
        yaz(kaynak_pp, govde.replace("#!/bin/sh\n", "#!/bin/sh\n# YENI-BLOK-V10\n", 1),
            True)
        g(ana10, "add", "-A", env=o10)
        g(ana10, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "yeni blok",
          env=o10, zorunlu=True)

        def kurulu_pp():
            return open(pp10, encoding="utf-8").read() if os.path.isfile(pp10) else ""

        # (a) KONTROL: eski kopya + YENI agac -> yeniden serilir
        rc10a, c10a = kur_kos(ana10, "--tazele", env=o10)
        s.bekle("V10.yeni-agac-serer", rc10a == 3 and "YENI-BLOK-V10" in kurulu_pp(),
                "KONTROL: YENI agactan --tazele eski kopyayi YENIDEN SERMELI (rc 3); "
                "rc=%d cikti=%r" % (rc10a, c10a[-200:]))
        sha_yeni = sha256(pp10)
        # (b) yeni kopya + ESKI agac (ata) -> kopya DEGISMEZ, rc 0 + UYARI
        rc10b, c10b = kur_kos(wt10, "--tazele", env=o10)
        s.bekle("V10.eski-agac-korur", sha256(pp10) == sha_yeni,
                "ESKI agactan --tazele YENI kopyayi EZMEMELI (olculen olay); "
                "rc=%d cikti=%r" % (rc10b, c10b[-200:]))
        s.bekle("V10.eski-agac-rc0-uyari", rc10b == 0 and "UYARI" in c10b,
                "reddedilen indirme rc 0 + GORUNUR UYARI vermeli; rc=%d cikti=%r"
                % (rc10b, c10b[-200:]))
        # (c) ayrisik dal: eski dalda ILGISIZ commit, kanca kaynagini yalniz
        # kurulu taraf degistirmis -> yine DEGISMEZ
        yaz(os.path.join(wt10, "ilgisiz.txt"), "z\n")
        g(wt10, "add", "-A", env=o10)
        g(wt10, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "ilgisiz",
          env=o10, zorunlu=True)
        rc10c, c10c = kur_kos(wt10, "--tazele", env=o10)
        s.bekle("V10.ayrisik-agac-korur", rc10c == 0 and sha256(pp10) == sha_yeni,
                "ayrisik ESKI dal YENI kopyayi EZMEMELI; rc=%d cikti=%r"
                % (rc10c, c10c[-200:]))
        # (o) MIRAS GIT BAGLAMI: linked worktree kancasi GIT_DIR ihrac eder; scrub
        # olmasa aday commit'i YANLIS depodan (yeni HEAD) okunur ve eski icerik
        # "ayni commit" sanilip serilirdi.
        o10g = dict(o10)
        o10g["GIT_DIR"] = os.path.join(ana10, ".git")
        rc10o, c10o = kur_kos(wt10, "--tazele", env=o10g)
        s.bekle("V10.git-baglam-mirasi-silinir",
                rc10o == 0 and sha256(pp10) == sha_yeni,
                "miras GIT_DIR ile kosan eski agac da YENI kopyayi EZMEMELI; rc=%d "
                "cikti=%r" % (rc10o, c10o[-200:]))
        # (d) UCTAN UCA: eski agacin kanca-kur.py'si KAPISIZ eski surum (taklit:
        # kopyayi bozar + rc 3). Kanca yanina serilmis araci cagirmali.
        eski_kur = os.path.join(wt10, "tools", "kanca-kur.py")

        def eski_kur_yaz():
            """Eski (kapisiz) kanca-kur taklidi: GERCEK eski surum gibi `--help`te
            yalniz yardim basar, `--tazele`de kopyayi bozar + rc 3."""
            yaz(eski_kur, "#!/usr/bin/env python3\nimport sys\n"
                          "if '--tazele' in sys.argv:\n"
                          "    open(%r, 'a').write('\\n# ESKI-KUR-EZDI\\n')\n"
                          "    sys.exit(3)\n" % pp10, True)

        eski_kur_yaz()
        yaz(os.path.join(wt10, "d.txt"), "d\n")
        g(wt10, "add", "d.txt", env=o10)
        _rc10d, o10d, e10d = g(wt10, "commit", "-m", "eski agactan commit", env=o10)
        s.bekle("V10.kanca-kurulu-araci-kosar",
                "ESKI-KUR-EZDI" not in kurulu_pp() and sha256(pp10) == sha_yeni
                and "UYARI" in (o10d + e10d),
                "kanca, eski agacin KAPISIZ kanca-kur.py'sini DEGIL kurulu araci "
                "cagirmali (kopya degismez + UYARI); cikti=%r" % (o10d + e10d)[-300:])
        g(wt10, "checkout", "--", "tools/kanca-kur.py", env=o10)
        # (e) kopya ELLE DUZENLENMIS -> gercek sapma, yeniden serilir (rc 3)
        with open(pp10, "a", encoding="utf-8") as f:
            f.write("\n# ELLE-DUZENLEME\n")
        rc10e, c10e = kur_kos(wt10, "--tazele", env=o10)
        s.bekle("V10.elle-duzenleme-serer",
                rc10e == 3 and "ELLE-DUZENLEME" not in kurulu_pp(),
                "damgadan sapmis (elle duzenlenmis) kopya YENIDEN SERILMELI (rc 3); "
                "rc=%d cikti=%r" % (rc10e, c10e[-200:]))
        def ilgisiz_commit(agac, ad):
            yaz(os.path.join(agac, ad), ad + "\n")
            g(agac, "add", "-A", env=o10)
            g(agac, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", ad,
              env=o10, zorunlu=True)

        def head(agac):
            return g(agac, "rev-parse", "HEAD", env=o10)[1]

        # ESKI ATA agac: ilk kurulum commit'inde (c0) duran detached worktree
        wt10a = os.path.join(kok, "v10-wt-ata")
        g(ana10, "worktree", "add", "-q", "--detach", wt10a, c0_10, env=o10,
          zorunlu=True)

        # (f) KIRLI DAMGA (14 Eki curutme 2. tur): pre-commit'teki --tazele
        # stage'li (HENUZ commit'lenmemis) degisikligi serer, HEAD yalniz TABANDIR.
        # Yarim is ZAYIFTIR: tabanindan ESKI agaci reddeder ama ESIT/YENI commit'li
        # agaca yenilir (yarim fail-closed blok tum agaclari durduramasin).
        # Commit'lenince post-commit damgayi kesinlestirir -> commit'li dal
        # icerigi (14 Eki olayi) KORUNUR.
        kur_kos(ana10, "--tazele", env=o10)            # kopya = ana hat (temiz damga)
        wt10k = os.path.join(kok, "v10-wt-kirli")
        g(ana10, "worktree", "add", "-q", wt10k, "-b", "kirli", env=o10, zorunlu=True)
        kpp = os.path.join(wt10k, "tools", "kancalar", "pre-push")
        yaz(kpp, open(kpp, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# KIRLI-BLOK-V10\n", 1), True)
        g(wt10k, "add", "tools/kancalar/pre-push", env=o10)
        rc10f1, c10f1 = kur_kos(wt10k, "--tazele", env=o10)
        s.bekle("V10.kirli-ayni-agac-serer",
                rc10f1 == 3 and "KIRLI-BLOK-V10" in kurulu_pp(),
                "KONTROL: agacin KENDI islenmemis kanca degisikligi serilmeli (rc 3); "
                "rc=%d cikti=%r" % (rc10f1, c10f1[-200:]))
        sha_kirli = sha256(pp10)
        rc10f2, c10f2 = kur_kos(wt10a, "--tazele", env=o10)
        s.bekle("V10.kirli-eski-agac-korur", rc10f2 == 0 and sha256(pp10) == sha_kirli,
                "kirli kopyanin TABANINDAN ESKI agac kopyayi EZMEMELI; rc=%d "
                "cikti=%r" % (rc10f2, c10f2[-200:]))
        ilgisiz_commit(ana10, "ilgisiz2.txt")
        rc10f3, c10f3 = kur_kos(ana10, "--tazele", env=o10)
        s.bekle("V10.kirli-commitli-agaca-yenilir",
                rc10f3 == 3 and "KIRLI-BLOK-V10" not in kurulu_pp(),
                "yarim (kirli) kopya tabanindan YENI commit'li agaca YENILMELI (yarim "
                "fail-closed blok tum agaclari durdurmasin); rc=%d cikti=%r"
                % (rc10f3, c10f3[-200:]))
        # KESINLESME: kirli agac degisikligini GERCEK `git commit`le isler ->
        # post-commit damgayi dal commit'ine ceker; ana hat artik EZEMEZ.
        rc10f5, o10f5, e10f5 = g(wt10k, "commit", "-q", "-m", "kirli blok", env=o10)
        d_f5 = damga10()
        rc10f6, c10f6 = kur_kos(ana10, "--tazele", env=o10)
        s.bekle("V10.commitli-dal-kancasi-korunur",
                rc10f5 == 0 and d_f5.get("commit") == head(wt10k)
                and d_f5.get("kirli") is False and rc10f6 == 0
                and "KIRLI-BLOK-V10" in kurulu_pp(),
                "commit'lenen dal kanca degisikligi post-commit'te damgalanmali ve "
                "ana hat (kanca degistirmeden) onu EZMEMELI; commit rc=%d damga=%r "
                "ana rc=%d cikti=%r" % (rc10f5, {k: d_f5.get(k) for k in ("commit", "kirli")},
                                        rc10f6, (o10f5 + e10f5 + c10f6)[-300:]))
        # KONTROL (gercek catisma): ana hat KANCA kaynagini degistirir -> ana hat
        # kazanir (takilip kalma yok; dal sonra main'i almali).
        apl = os.path.join(ana10, "tools", "kancalar", "pre-push")
        yaz(apl, open(apl, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# ANA-YENI-V10\n", 1), True)
        g(ana10, "add", "-A", env=o10)
        g(ana10, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "ana kanca",
          env=o10, zorunlu=True)
        rc10f4, c10f4 = kur_kos(ana10, "--tazele", env=o10)
        s.bekle("V10.kirli-catisma-ana-kazanir",
                rc10f4 == 3 and "ANA-YENI-V10" in kurulu_pp(),
                "KONTROL: kanca kaynagini degistiren ANA HAT kirli dal kopyasini "
                "yeniden serebilmeli (takilma yok); rc=%d cikti=%r"
                % (rc10f4, c10f4[-200:]))

        # (g) SAHIPSIZ DAMGA (curutme BLOCKER 1): damga HICBIR dalda olmayan bir
        # commit'e (detached worktree; amend de ayni) ilerleyince eski agac --
        # ata da ayrisik da -- yeni kopyayi EZMEMELI.
        wt10d = os.path.join(kok, "v10-wt-detached")
        g(ana10, "worktree", "add", "-q", "--detach", wt10d, "HEAD", env=o10,
          zorunlu=True)
        ilgisiz_commit(wt10d, "det1.txt")
        ilgisiz_commit(wt10d, "det2.txt")
        kur_kos(wt10d, "--tazele", env=o10)            # damga -> detached commit
        sahipsiz = damga10().get("commit") == head(wt10d)
        sha_g = sha256(pp10)
        rc10g1, c10g1 = kur_kos(wt10a, "--tazele", env=o10)
        rc10g2, c10g2 = kur_kos(wt10, "--tazele", env=o10)
        s.bekle("V10.sahipsiz-damga-eski-korur",
                sahipsiz and rc10g1 == 0 and rc10g2 == 0 and sha256(pp10) == sha_g,
                "damga sahipsiz (detached) commit'teyken ATA ve AYRISIK eski agac "
                "kopyayi EZMEMELI; sahipsiz=%s rc=%d/%d cikti=%r"
                % (sahipsiz, rc10g1, rc10g2, (c10g1 + c10g2)[-300:]))

        # (h) KIRLI DAMGA + agaci SILINMIS (curutme BLOCKER 2): dal commit'i atip
        # worktree'si kapanan kirli damga, eski agaca kapi ACMAMALI.
        rc10h00, _c = kur_kos(ana10, env=o10)          # operator: damga -> ana hat
        wt10r = os.path.join(kok, "v10-wt-silinen")
        g(ana10, "worktree", "add", "-q", wt10r, "-b", "silinen", env=o10, zorunlu=True)
        rpp = os.path.join(wt10r, "tools", "kancalar", "pre-push")
        yaz(rpp, open(rpp, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# SILINEN-BLOK-V10\n", 1), True)
        g(wt10r, "add", "-A", env=o10)
        rc10h0, _c = kur_kos(wt10r, "--tazele", env=o10)
        g(wt10r, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "silinen",
          env=o10, zorunlu=True)
        g(ana10, "worktree", "remove", "--force", wt10r, env=o10, zorunlu=True)
        kirli_kaldi = damga10().get("kirli") is True
        sha_h = sha256(pp10)
        rc10h1, c10h1 = kur_kos(wt10a, "--tazele", env=o10)
        rc10h2, c10h2 = kur_kos(wt10, "--tazele", env=o10)
        s.bekle("V10.kirli-agac-silinince-eski-korur",
                rc10h00 == 0 and rc10h0 == 3 and kirli_kaldi and rc10h1 == 0
                and rc10h2 == 0
                and sha256(pp10) == sha_h,
                "agaci silinmis KIRLI damga eski agaca kapi acmamali; serim=%d "
                "kirli=%s rc=%d/%d cikti=%r" % (rc10h0, kirli_kaldi, rc10h1, rc10h2,
                                                (c10h1 + c10h2)[-300:]))

        # (i) kirli damga, degisiklik commit'lenince KESINLESIR (damga temizlenir)
        # terk edilmis kirli kopyadan cikis = OPERATOR'un acik kurulumu (UYARI'da
        # yazan care); --tazele bunu kendiliginden yapmaz.
        rc10i0, _c = kur_kos(ana10, env=o10)
        wt10f = os.path.join(kok, "v10-wt-kesin")
        g(ana10, "worktree", "add", "-q", wt10f, "-b", "kesin", env=o10, zorunlu=True)
        fpp = os.path.join(wt10f, "tools", "kancalar", "pre-push")
        yaz(fpp, open(fpp, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# KESIN-BLOK-V10\n", 1), True)
        g(wt10f, "add", "-A", env=o10)
        kur_kos(wt10f, "--tazele", env=o10)
        kirli_once = damga10().get("kirli")
        g(wt10f, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "kesin",
          env=o10, zorunlu=True)
        kur_kos(wt10f, "--tazele", env=o10)
        d_i = damga10()
        s.bekle("V10.kirli-damga-commitle-kesinlesir",
                rc10i0 == 0 and kirli_once is True and d_i.get("kirli") is False
                and d_i.get("commit") == head(wt10f),
                "stage'li serim kirli damgalanmali, commit'ten sonraki tazele damgayi "
                "TEMIZ + yeni commit'e cekmeli; once=%r sonra=%r" % (kirli_once, d_i))

        # (j) BOZUK kanca-kur.py (curutme #3) kurulu araclarin yanina SERILMEZ:
        # serilseydi TUM agaclarda commit/push rc=1 ile dururdu.
        g(ana10, "-c", "core.hooksPath=/dev/null", "merge", "-q", "--ff-only",
          "kesin", env=o10)
        kur_kos(ana10, "--tazele", env=o10)
        wt10b = os.path.join(kok, "v10-wt-bozuk")
        g(ana10, "worktree", "add", "-q", wt10b, "-b", "bozuk", env=o10, zorunlu=True)
        with open(os.path.join(wt10b, "tools", "kanca-kur.py"), "a",
                  encoding="utf-8") as f:
            f.write("\ndef bozuk(:\n")
        kur_kos(wt10b, "--tazele", env=o10)
        kurulu_kur = os.path.join(kurulu10, "kanca-kur.py")
        p10j = subprocess.run([sys.executable, kurulu_kur, "--tazele", "--depo", ana10],
                              capture_output=True, text=True, timeout=120, env=o10)
        s.bekle("V10.bozuk-arac-serilmez",
                "def bozuk(" not in (open(kurulu_kur, encoding="utf-8").read()
                                     if os.path.isfile(kurulu_kur) else "def bozuk(")
                and p10j.returncode == 0,
                "derlenmeyen kanca-kur.py kurulu kopyaya SERILMEMELI; kurulu arac "
                "rc=%d cikti=%r" % (p10j.returncode, (p10j.stdout + p10j.stderr)[-200:]))
        # (j2) DERLENEN ama kurulu dizinde KOSAMAYAN arac (curutme 2. tur N1/N2:
        # yarim import) da serilmez -> duman testi.
        g(wt10b, "checkout", "--", "tools/kanca-kur.py", env=o10)
        bkur = os.path.join(wt10b, "tools", "kanca-kur.py")
        # import MODUL BASINA (sona eklenen satir `sys.exit(main())`ten sonra kalir
        # ve hic kosmaz -> olcum kor olurdu)
        yaz(bkur, open(bkur, encoding="utf-8").read().replace(
            "\nimport os\n", "\nimport yok_boyle_modul_v10  # noqa\nimport os\n", 1), True)
        kur_kos(wt10b, "--tazele", env=o10)
        p10j2 = subprocess.run([sys.executable, kurulu_kur, "--tazele", "--depo", ana10],
                               capture_output=True, text=True, timeout=120, env=o10)
        s.bekle("V10.kosmayan-arac-serilmez",
                "yok_boyle_modul_v10" not in (open(kurulu_kur, encoding="utf-8").read()
                                             if os.path.isfile(kurulu_kur)
                                             else "yok_boyle_modul_v10")
                and p10j2.returncode == 0,
                "kurulu dizinde import'u KOSAMAYAN kanca-kur.py SERILMEMELI (tum "
                "agaclarin commit'i durur); kurulu arac rc=%d cikti=%r"
                % (p10j2.returncode, (p10j2.stdout + p10j2.stderr)[-200:]))

        # (k) serilen her dosya surumde SAYILIR (curutme #4): yalniz git_ortami.py'yi
        # degistiren ana hat ile ayrisik dal arasinda rc 3 PING-PONG olmamali.
        wt10p = os.path.join(kok, "v10-wt-pingpong")
        g(ana10, "worktree", "add", "-q", wt10p, "-b", "pingpong", env=o10,
          zorunlu=True)
        ilgisiz_commit(wt10p, "pp.txt")
        with open(os.path.join(ana10, "tools", "git_ortami.py"), "a",
                  encoding="utf-8") as f:
            f.write("\n# ana hat degisikligi (V10-k)\n")
        g(ana10, "add", "-A", env=o10)
        g(ana10, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "git_ortami",
          env=o10, zorunlu=True)
        rcs_k = [kur_kos(a, "--tazele", env=o10)[0]
                 for a in (ana10, wt10p, ana10, wt10p)]
        s.bekle("V10.git-ortami-ping-pong-yok", rcs_k == [3, 0, 0, 0],
                "git_ortami.py-only ana hat degisikligi: ana 3, dal 0 (korur), sonra "
                "hep 0 olmali (ping-pong yok); rc dizisi=%r" % rcs_k)

        # (l) CATISMA: iki ayrisik taraf da kanca kaynagini degistirmis -> ana
        # hatta OLMAYAN dal ana hattin kopyasini EZEMEZ.
        wt10t = os.path.join(kok, "v10-wt-catisma")
        g(ana10, "worktree", "add", "-q", wt10t, "-b", "catisma", env=o10,
          zorunlu=True)
        tpp = os.path.join(wt10t, "tools", "kancalar", "pre-push")
        yaz(tpp, open(tpp, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# DAL-CATISMA-V10\n", 1), True)
        g(wt10t, "add", "-A", env=o10)
        g(wt10t, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "dal kanca",
          env=o10, zorunlu=True)
        yaz(apl, open(apl, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# ANA-CATISMA-V10\n", 1), True)
        g(ana10, "add", "-A", env=o10)
        g(ana10, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "ana kanca 2",
          env=o10, zorunlu=True)
        rc10l1, _c = kur_kos(ana10, "--tazele", env=o10)
        rc10l2, c10l2 = kur_kos(wt10t, "--tazele", env=o10)
        s.bekle("V10.catisma-dal-ana-hatti-ezmez",
                rc10l1 == 3 and rc10l2 == 0 and "ANA-CATISMA-V10" in kurulu_pp()
                and "DAL-CATISMA-V10" not in kurulu_pp(),
                "catismada ana hatta OLMAYAN dal ana hattin kopyasini ezmemeli; "
                "rc=%d/%d cikti=%r" % (rc10l1, rc10l2, c10l2[-200:]))

        # (m) UCTAN UCA diger uc kanca da KURULU araci cagirir: eski agacin KAPISIZ
        # kanca-kur.py'si (taklit: her kosumda isaret ekler) KOSMAMALI.
        eski_kur_yaz()

        def isaret():
            return kurulu_pp().count("ESKI-KUR-EZDI")

        n0 = isaret()
        g(wt10, "checkout", "-q", "-b", "v10-pc", env=o10)            # post-checkout
        n1 = isaret()
        ilgisiz_commit(wt10, "pm.txt")
        g(wt10, "-c", "core.hooksPath=/dev/null", "checkout", "-q", "eski", env=o10)
        g(wt10, "merge", "-q", "--ff-only", "v10-pc", env=o10)         # post-merge
        n2 = isaret()
        uzak = os.path.join(kok, "v10-uzak.git")
        g(kok, "init", "-q", "--bare", uzak, env=o10, zorunlu=True)
        g(wt10, "push", "-q", uzak, "eski", env=o10)                   # pre-push
        n3 = isaret()
        g(wt10, "checkout", "--", "tools/kanca-kur.py", env=o10)
        for etiket, once, sonra in (("V10.post-checkout-kurulu-arac", n0, n1),
                                    ("V10.post-merge-kurulu-arac", n1, n2),
                                    ("V10.pre-push-kurulu-arac", n2, n3)):
            s.bekle(etiket, sonra == once,
                    "%s eski agacin KAPISIZ kanca-kur.py'sini DEGIL kurulu araci "
                    "cagirmali; isaret %d -> %d" % (etiket.split(".")[1], once, sonra))

        # (p) --depo: post-checkout / post-merge / pre-push agacin KENDI kaynagini
        # olcer (bayrak dusse kaynak sessizce ANA checkout'a kayar ve worktree'nin
        # yeni kanca degisikligi hic serilmez).
        kur_kos(ana10, env=o10)
        wt10w = os.path.join(kok, "v10-wt-depo")
        g(ana10, "worktree", "add", "-q", wt10w, "-b", "w1", env=o10, zorunlu=True)
        wpp = os.path.join(wt10w, "tools", "kancalar", "pre-push")

        def w_commit(isaret_adi):
            yaz(wpp, open(wpp, encoding="utf-8").read().replace(
                "#!/bin/sh\n", "#!/bin/sh\n# %s\n" % isaret_adi, 1), True)
            g(wt10w, "add", "-A", env=o10)
            g(wt10w, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m",
              isaret_adi, env=o10, zorunlu=True)

        w_commit("W1-V10")
        g(wt10w, "checkout", "-q", "-b", "w2", env=o10)                # post-checkout
        w1_var = "W1-V10" in kurulu_pp()
        w_commit("W2-V10")
        g(wt10w, "-c", "core.hooksPath=/dev/null", "checkout", "-q", "w1", env=o10)
        g(wt10w, "merge", "-q", "--ff-only", "w2", env=o10)            # post-merge
        w2_var = "W2-V10" in kurulu_pp()
        w_commit("W3-V10")
        g(wt10w, "push", "-q", uzak, "w1", env=o10)                    # pre-push
        w3_var = "W3-V10" in kurulu_pp()
        for etiket, var in (("V10.post-checkout-depo-agaci", w1_var),
                            ("V10.post-merge-depo-agaci", w2_var),
                            ("V10.pre-push-depo-agaci", w3_var)):
            s.bekle(etiket, var,
                    "%s agacin KENDI (yeni) kanca degisikligini sermeli (--depo); "
                    "serildi=%s" % (etiket.split(".")[1], var))

        # (q) KURULU ARAC BOZUKSA kanca agacin KENDI aracina duser (curutme 2. tur
        # N1): tek bir bozuk kurulu arac TUM agaclarin commit'ini durdurmamali.
        kur_kos(ana10, "--zorla", env=o10)
        yaz(kurulu_kur, "import yok_boyle_modul_v10\n", True)
        q_dosya = os.path.join(ana10, "q.txt")
        yaz(q_dosya, "q\n")
        g(ana10, "add", "q.txt", env=o10)
        rc10q1, o10q1, e10q1 = g(ana10, "commit", "-q", "-m", "q1", env=o10)
        onarildi = (open(kurulu_kur, encoding="utf-8").read()
                    == open(os.path.join(ana10, "tools", "kanca-kur.py"),
                            encoding="utf-8").read())
        rc10q2, o10q2, e10q2 = g(ana10, "commit", "-q", "-m", "q2", env=o10)
        s.bekle("V10.bozuk-kurulu-arac-agactan-onarilir",
                "agacin kendi araciyla" in (o10q1 + e10q1) and onarildi
                and rc10q2 == 0,
                "kurulu arac kosamazsa kanca agacin aracina dusmeli, kopyayi onarmali "
                "ve sonraki commit GECMELI; onarildi=%s rc2=%d cikti=%r"
                % (onarildi, rc10q2, (o10q1 + e10q1 + o10q2 + e10q2)[-300:]))

        # (r) ACIK KURULUM DA INDIRMEZ (curutme 2. tur N3): ana checkout GERIDEYKEN
        # `kanca-kur.py` reddeder; `--zorla` (operator) ezer.
        wt10z = os.path.join(kok, "v10-wt-zorla")
        g(ana10, "worktree", "add", "-q", wt10z, "-b", "zorla", env=o10, zorunlu=True)
        zpp = os.path.join(wt10z, "tools", "kancalar", "pre-push")
        yaz(zpp, open(zpp, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# ZORLA-V10\n", 1), True)
        g(wt10z, "add", "-A", env=o10)
        g(wt10z, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "zorla",
          env=o10, zorunlu=True)
        rc10r0, _c = kur_kos(wt10z, "--tazele", env=o10)
        rc10r1, c10r1 = kur_kos(ana10, env=o10)
        zorla_kaldi = "ZORLA-V10" in kurulu_pp()
        s.bekle("V10.acik-kurulum-indirmez",
                rc10r0 == 3 and rc10r1 != 0 and zorla_kaldi and "--zorla" in c10r1,
                "geride kalan ana checkout'tan acik kurulum YENI kopyayi EZMEMELI "
                "(rc!=0 + --zorla tarifi); serim=%d rc=%d kaldi=%s cikti=%r"
                % (rc10r0, rc10r1, zorla_kaldi, c10r1[-200:]))
        rc10r2, c10r2 = kur_kos(ana10, "--zorla", env=o10)
        s.bekle("V10.zorla-ezer", rc10r2 == 0 and "ZORLA-V10" not in kurulu_pp(),
                "--zorla operator karariyla ana checkout'tan EZMELI; rc=%d cikti=%r"
                % (rc10r2, c10r2[-200:]))

        # (s) DAMGA COMMIT'I DEPODA YOK (gc; curutme 2. tur N4): ana hat DISI aday
        # kopyaya dokunamaz.
        dyol = os.path.join(kurulu10, ".kaynak-damgasi.json")
        dj = damga10()
        dj["commit"] = "f" * 40
        with open(dyol, "w", encoding="utf-8") as f:
            json.dump(dj, f)
        sha_s = sha256(pp10)
        rc10s, c10s = kur_kos(wt10, "--tazele", env=o10)
        s.bekle("V10.kayip-damga-ana-disi-reddeder",
                rc10s == 0 and sha256(pp10) == sha_s,
                "damga commit'i depoda yokken ana hat DISI agac kopyayi EZMEMELI; "
                "rc=%d cikti=%r" % (rc10s, c10s[-200:]))

        # (t) KIRLI damga + AYRISIK agac (kirli bayraginin TEK BASINA yuk tasidigi
        # kol): tabani B olan yarim kopya, B'ye esit/yeni OLMAYAN ayrisik agaca
        # yenilmez — ayrisik agacin kanca kaynagi ortak atadan beri degismemis olsa
        # bile (yarim degisiklik o agacta YOK).
        kur_kos(ana10, "--zorla", env=o10)
        wt10y = os.path.join(kok, "v10-wt-ayrisik")
        g(ana10, "worktree", "add", "-q", wt10y, "-b", "ayrisik", env=o10, zorunlu=True)
        ilgisiz_commit(wt10y, "y.txt")
        ilgisiz_commit(ana10, "t.txt")
        kur_kos(ana10, "--tazele", env=o10)            # damga -> B (ana hat ucu)
        wt10x = os.path.join(kok, "v10-wt-yarim")
        g(ana10, "worktree", "add", "-q", wt10x, "-b", "yarim", env=o10, zorunlu=True)
        xpp = os.path.join(wt10x, "tools", "kancalar", "pre-push")
        yaz(xpp, open(xpp, encoding="utf-8").read().replace(
            "#!/bin/sh\n", "#!/bin/sh\n# YARIM-V10\n", 1), True)
        g(wt10x, "add", "-A", env=o10)
        rc10t0, _c = kur_kos(wt10x, "--tazele", env=o10)
        sha_t = sha256(pp10)
        rc10t, c10t = kur_kos(wt10y, "--tazele", env=o10)
        s.bekle("V10.kirli-ayrisik-agac-korur",
                rc10t0 == 3 and rc10t == 0 and sha256(pp10) == sha_t
                and "YARIM-V10" in kurulu_pp(),
                "kirli kopyanin tabanina esit/yeni OLMAYAN ayrisik agac onu EZMEMELI; "
                "serim=%d rc=%d cikti=%r" % (rc10t0, rc10t, c10t[-200:]))

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
     frozenset({"V10.acik-kurulum-indirmez", "V2.dizin-yok-rc",
                "V2.eksik-kanca-rc"})),

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
    # 🔴 V4.saglikli-yesil MU4'un TASARLANMIS detektoru DEGILDIR: bu mutantin
    # ASIL oldurdugu eksen "config degeri pruvo-kancalar'i gostermeli" (V2.deger-
    # mutlak + V3.deger-oldurucu-degil). `V4.saglikli-yesil` yalniz raw!=realpath
    # olan ortamda (mac symlinked /var) ARIZI olarak kirmizi yaniyordu; realpath
    # yalitimi (bkz. _gecici_kok) sonrasi TUM ortamlarda YESIL kalir, o yuzden
    # beklenen kumeden CIKARILDI. MU4'un gercek tespiti ZAYIFLAMAZ (6 detektor
    # kalir) ([[hukum-yanlis-birimde]]).
    ("MU4 kur: kurulu dizin ANA agacin izlenen dizinine doner (elenen secenek 2)",
     "kanca-kur.py",
     '    return os.path.join(ortak_git_dizini(baslangic), KURULU_DIZIN_ADI)',
     '    return os.path.join(baslangic, KANCA_DIZINI)',
     frozenset({"V10.acik-kurulum-indirmez", "V10.catisma-dal-ana-hatti-ezmez",
                "V10.commitli-dal-kancasi-korunur", "V10.elle-duzenleme-serer",
                "V10.eski-agac-rc0-uyari", "V10.kanca-kurulu-araci-kosar",
                "V10.kirli-agac-silinince-eski-korur", "V10.kirli-ayni-agac-serer",
                "V10.kirli-ayrisik-agac-korur", "V10.kirli-catisma-ana-kazanir",
                "V10.kirli-commitli-agaca-yenilir",
                "V10.kirli-damga-commitle-kesinlesir",
                "V10.post-checkout-depo-agaci", "V10.post-merge-depo-agaci",
                "V10.pre-push-depo-agaci", "V10.sahipsiz-damga-eski-korur",
                "V10.yeni-agac-serer", "V2.deger-mutlak", "V3.deger-oldurucu-degil",
                "V4.sapma-kirmizi", "V6.saglikli-agac-yesil", "V8.once-sessiz",
                "V8.sonra-A-durdu"})),

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
     frozenset({"V4.yutma-kirmizi"})),

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
                "V4.gerekce-kirmizi", "V5.ci-hal-olculemedi", "V5.ci-hal-yesil",
                "V5.ci-kablolama-ilan", "V5.ci-muafiyet-dar-fikstur",
                "V5.ci-ozet-olculemedi", "V5.ci-sapma-ilan", "V6.ana-saglikli",
                "V6.saglikli-agac-yesil", "V7.izole-worktree-yesil"})),

    # 🔴 MU15 KUSUR 2-a'nin TAM mutanti: config'e yazilan deger ELENEN SECENEK
    # 1'e (GORELI `tools/kancalar`) doner. Kurulu kopya yerinde kalir ama git
    # artik AGACIN icindeki yolu cozer -> `tools/kancalar` TASIMAYAN worktree'de
    # HICBIR kanca kosmaz. `V6.olu-agacta-kanca-kosuyor` bu mutanti oldurur.
    ("MU15 kur: config'e GORELI deger yazilir (KUSUR 2-a, elenen secenek 1)",
     "kanca-kur.py",
     '    rc, _o, hata = _git(kok, "config", KAPSAM, AYAR, kurulu)',
     '    rc, _o, hata = _git(kok, "config", KAPSAM, AYAR, KANCA_DIZINI)',
     frozenset({"V10.bozuk-kurulu-arac-agactan-onarilir",
                "V10.commitli-dal-kancasi-korunur", "V10.kanca-kurulu-araci-kosar",
                "V10.kirli-agac-silinince-eski-korur",
                "V10.kirli-damga-commitle-kesinlesir",
                "V10.post-checkout-kurulu-arac", "V10.post-merge-kurulu-arac",
                "V10.pre-push-kurulu-arac", "V10.zorla-ezer", "V2.deger-mutlak",
                "V2.idempotent", "V2.kurulum-basarili", "V3.deger-oldurucu-degil",
                "V3.kurulum-basarili", "V3.worktreeden-kurulur",
                "V4.gerekce-kirmizi", "V4.rc-kontrolsuz-kirmizi",
                "V4.saglikli-yesil", "V4.sapma-kirmizi", "V4.yutma-kirmizi",
                "V6.ana-saglikli", "V6.kurulum-basarili",
                "V6.olu-agacta-kanca-kosuyor", "V6.saglikli-agac-yesil",
                "V6.yeniden-kurulum", "V7.kurulum-basarili", "V8.once-sessiz",
                "V9.devnull-golge-rc0", "V9.golge-yok-rc0"})),

    # 🔴 MU16a DELIK 1: tazele BAYATSA yeniden SERMEZ -> kopya bayat kalir,
    # commit sonsuza dek bloklanir, YENI mantik hic kosmaz.
    ("MU16a kur: tazele bayatsa YENIDEN SERMEZ (DELIK 1)",
     "kanca-kur.py",
     "    try:\n        _ser(kaynak_dizin, kurulu, kuru=False)\n"
     "    except Hata as e:\n"
     '        return 1, "kopya bayatti ama YENIDEN SERILEMEDI: %s" % e',
     '    pass',
     # (14 Eki olculdu) yeni agac da SERILEMEZ -> V10 kontrol + elle kolu duser
     frozenset({"V10.acik-kurulum-indirmez", "V10.bozuk-arac-serilmez",
                "V10.bozuk-kurulu-arac-agactan-onarilir",
                "V10.catisma-dal-ana-hatti-ezmez",
                "V10.commitli-dal-kancasi-korunur", "V10.elle-duzenleme-serer",
                "V10.eski-agac-rc0-uyari", "V10.git-ortami-ping-pong-yok",
                "V10.kirli-agac-silinince-eski-korur", "V10.kirli-ayni-agac-serer",
                "V10.kirli-ayrisik-agac-korur", "V10.kirli-catisma-ana-kazanir",
                "V10.kirli-damga-commitle-kesinlesir", "V10.kosmayan-arac-serilmez",
                "V10.post-checkout-depo-agaci", "V10.post-merge-depo-agaci",
                "V10.pre-push-depo-agaci", "V10.yeni-agac-serer",
                "V8.sonra-yakalandi"})),

    # 🔴 MU16b DELIK 1: tazele bayat kopyayi YENIDEN SERER ama BAYATTI kodunu
    # bildirmez -> commit DURMAZ, BAYAT wiring o commit'te sessizce kosar.
    ("MU16b kur: tazele bayati BILDIRMEZ (0 doner, DELIK 1 blok kolu)",
     "kanca-kur.py",
     '    return TAZELE_BAYATTI, ("kurulu kopya BAYATTI',
     '    return 0, ("kurulu kopya BAYATTI',
     frozenset({"V10.acik-kurulum-indirmez",
                "V10.bozuk-kurulu-arac-agactan-onarilir",
                "V10.catisma-dal-ana-hatti-ezmez", "V10.elle-duzenleme-serer",
                "V10.git-ortami-ping-pong-yok",
                "V10.kirli-agac-silinince-eski-korur", "V10.kirli-ayni-agac-serer",
                "V10.kirli-ayrisik-agac-korur", "V10.kirli-catisma-ana-kazanir",
                "V10.kirli-commitli-agaca-yenilir", "V10.yeni-agac-serer",
                "V8.sonra-A-durdu"})),

    # 🔴 MU17 DELIK 2: golge kontrolu gercek-yol golgeyi GORMEZDEN gelir.
    ("MU17 kur: golge worktree kontrolu devrilir (DELIK 2)",
     "kanca-kur.py",
     '    return False, ("bu LINKED WORKTREE\'nin config.worktree\'si core.hooksPath\'i "',
     '    return True, ("bu LINKED WORKTREE\'nin config.worktree\'si core.hooksPath\'i "',
     frozenset({"V9.golge-rc-sifirdisi"})),

    # 🔴 MU18 DELIK 2: /dev/null muafiyeti kalkar -> KASITLI izolasyon KIRMIZI
    # yanar (yanlis-pozitif).
    ("MU18 kur: /dev/null izolasyon muafiyeti kalkar (DELIK 2 yanlis-pozitif)",
     "kanca-kur.py",
     '    if os.path.normpath(ham) == os.path.normpath("/dev/null"):',
     '    if False:',
     frozenset({"V9.devnull-golge-rc0"})),

    # 🔴 MU19 INDIRME KAPISI devrilir: ret karari yok sayilir -> eski agac yeni
    # kopyayi ezer (14 Eki'de olculen olay geri gelir).
    ("MU19 kur: indirme kapisi devrilir (eski agac yeni kopyayi ezer)",
     "kanca-kur.py",
     "    if not ser_mi:\n        return 0, (",
     "    if False:\n        return 0, (",
     frozenset({"V10.ayrisik-agac-korur", "V10.catisma-dal-ana-hatti-ezmez",
                "V10.commitli-dal-kancasi-korunur", "V10.eski-agac-korur",
                "V10.eski-agac-rc0-uyari", "V10.git-baglam-mirasi-silinir",
                "V10.git-ortami-ping-pong-yok", "V10.kanca-kurulu-araci-kosar",
                "V10.kayip-damga-ana-disi-reddeder",
                "V10.kirli-agac-silinince-eski-korur",
                "V10.kirli-ayrisik-agac-korur", "V10.kirli-eski-agac-korur",
                "V10.post-merge-kurulu-arac", "V10.pre-push-kurulu-arac",
                "V10.sahipsiz-damga-eski-korur"})),

    # 🔴 MU20 elle duzenleme algisi kalkar -> damgadan sapmis kopya, ESKI agactan
    # bakilinca "eski aday" sayilip KORUNUR (gercek sapma fail-closed degil).
    ("MU20 kur: elle duzenleme (damgadan sapma) algisi kalkar",
     "kanca-kur.py",
     "    if elle:\n        return True, \"kurulu kopya ELLE",
     "    if False:\n        return True, \"kurulu kopya ELLE",
     frozenset({"V10.elle-duzenleme-serer"})),

    # 🔴 MU21 tazele serdikten sonra DAMGALAMAZ -> damga eski commit'te kalir,
    # eski agac "ayni commit" sayilip yeni kopyayi ezer.
    ("MU21 kur: tazele serdikten sonra damgalamaz",
     "kanca-kur.py",
     "    try:\n        damga_yaz(kaynak_dizin, kurulu)\n    except Hata as e:\n"
     "        return 1, \"kopya yeniden serildi ama DAMGALANAMADI",
     "    try:\n        pass\n    except Hata as e:\n"
     "        return 1, \"kopya yeniden serildi ama DAMGALANAMADI",
     frozenset({"V10.acik-kurulum-indirmez", "V10.ayrisik-agac-korur",
                "V10.catisma-dal-ana-hatti-ezmez",
                "V10.commitli-dal-kancasi-korunur", "V10.eski-agac-korur",
                "V10.eski-agac-rc0-uyari", "V10.git-baglam-mirasi-silinir",
                "V10.git-ortami-ping-pong-yok", "V10.kanca-kurulu-araci-kosar",
                "V10.kirli-agac-silinince-eski-korur",
                "V10.kirli-ayrisik-agac-korur",
                "V10.kirli-damga-commitle-kesinlesir", "V10.kirli-eski-agac-korur",
                "V10.post-merge-kurulu-arac", "V10.pre-push-kurulu-arac"})),

    # 🔴 MU23 KIRLI damga yok sayilir -> yarim kopya, tabanina esit/yeni OLMAYAN
    # ayrisik agacca (kanca kaynagi ortak atadan beri degismemis diye) ezilir.
    ("MU23 kur: damganin kirlilik bilgisi yok sayilir",
     "kanca-kur.py",
     '    kirli = damga.get("kirli") is not False\n',
     '    kirli = False\n',
     frozenset({"V10.kirli-ayrisik-agac-korur"})),

    # 🔴 MU24..MU31 + MU22b..d: 14 Eki bagimsiz curutucunun HAYATTA KALAN
    # zararli mutantlari ve iki BLOCKER'in yeniden kurulmasi.
    ("MU24 kur: catisma kolu ana hat sartini birakir (dal her zaman kazanir)",
     "kanca-kur.py",
     "        if aday_ana and not kurulu_ana:",
     "        if True:",
     frozenset({"V10.catisma-dal-ana-hatti-ezmez", "V10.pre-push-kurulu-arac"})),

    ("MU25 kur: git_ortami.py surum yollarindan cikar (ping-pong)",
     "kanca-kur.py",
     'SURUM_YOLLARI = (KANCA_DIZINI,) + tuple("tools/" + a for a in KURULU_ARACLAR)',
     'SURUM_YOLLARI = (KANCA_DIZINI, "tools/kanca-kur.py")',
     frozenset({"V10.git-ortami-ping-pong-yok"})),

    # (MU26 "derleme sarti kalkar" OLCULEREK listeden cikarildi: MU32'nin duman
    # testi sozdizimi bozuk araci da (kosamadigi icin) reddeder -> derleme yalniz
    # ucuz ON-ELEMEDIR; tek basina kaldirilmasi davranissal olarak ESDEGER.)

    ("MU27 kur: _git miras GIT_* baglamini SILMEZ",
     "kanca-kur.py",
     "                           env=git_ortami())",
     "                           env=None)",
     frozenset({"V10.git-baglam-mirasi-silinir", "V10.kanca-kurulu-araci-kosar"})),

    ("MU28 kur: BLOCKER 1 geri gelir (sahipsiz damga kacisi eski-reddinden ONCE)",
     "kanca-kur.py",
     "    if aday == kurulu_c or _ata_mi(agac, aday, kurulu_c):\n"
     "        return False, neden_eski\n",
     "    if not kirli and not _ata_mi(agac, kurulu_c, ANA_DAL):\n"
     "        return True, \"sahipsiz\"\n"
     "    if aday == kurulu_c or _ata_mi(agac, aday, kurulu_c):\n"
     "        return False, neden_eski\n",
     frozenset({"V10.acik-kurulum-indirmez", "V10.commitli-dal-kancasi-korunur",
                "V10.sahipsiz-damga-eski-korur"})),

    # (MU29 "kirli damga KESINLESMEZ" OLCULEREK listeden cikarildi: _damga_ilerlet'in
    # genel "aday damgadan yeni -> yaz" kolu commit sonrasi damgayi zaten TEMIZ
    # yazar; kesinlestirme kolu yalniz "ayni commit, kirlilik geri alinmis" kenar
    # halinde fark eder -> davranissal olarak ESDEGER mutant, delik sayilmaz.)

    ("MU30 kur: acik kurulum damga YAZMAZ",
     "kanca-kur.py",
     "    if not kuru and damgala:\n        damga_yaz(kaynak_dizin, kurulu)",
     "    if not kuru and damgala:\n        pass",
     frozenset({"V10.kayip-damga-ana-disi-reddeder", "V10.kur-damgalar"})),

    ("MU31 kur: BLOCKER 2 geri gelir (kirli+silinmis agac kacisi)",
     "kanca-kur.py",
     "    if aday == kurulu_c or _ata_mi(agac, aday, kurulu_c):\n"
     "        return False, neden_eski\n",
     "    if kirli and not os.path.isdir(damga.get(\"kaynak\") or \"\"):\n"
     "        return True, \"silinmis\"\n"
     "    if aday == kurulu_c or _ata_mi(agac, aday, kurulu_c):\n"
     "        return False, neden_eski\n",
     frozenset({"V10.kirli-agac-silinince-eski-korur"})),

    # 🔴 MU32..MU39: curutme 2. tur (N1-N5) onarimlarinin her kolu TEK BASINA.
    ("MU32 kur: kurulu araclarin DUMAN testi kalkar (kosmayan arac serilir)",
     "kanca-kur.py",
     "            and _araclar_kosar_mi(araclar, kurulu)):",
     "            and True):",
     frozenset({"V10.kosmayan-arac-serilmez"})),

    ("MU33 pre-commit: kurulu arac kosamazsa agacin aracina DUSMEZ",
     "kancalar/pre-commit",
     '  if [ "$pruvo_tazele_rc" != "0" ] && [ "$pruvo_tazele_rc" != "3" ] \\\n',
     "  if false \\\n",
     frozenset({"V10.bozuk-kurulu-arac-agactan-onarilir"})),

    ("MU34 kur: acik kurulumun indirme kapisi kalkar (--zorla'siz ezer)",
     "kanca-kur.py",
     "    if not ser_mi and not zorla:",
     "    if False:",
     frozenset({"V10.acik-kurulum-indirmez"})),

    ("MU35 kur: damga commit'i depoda yokken her aday serer",
     "kanca-kur.py",
     "        if _ata_mi(agac, aday, ANA_DAL):\n"
     "            return True, \"damga commit'i depoda yok; aday ana hatta\"",
     "        if True:\n"
     "            return True, \"damga commit'i depoda yok; aday ana hatta\"",
     frozenset({"V10.kayip-damga-ana-disi-reddeder"})),

    ("MU36 post-checkout: --depo duser (kaynak ANA checkout'a kayar)",
     "kancalar/post-checkout",
     ' --tazele --depo "$HEDEF" >/dev/null 2>&1',
     " --tazele >/dev/null 2>&1",
     frozenset({"V10.post-checkout-depo-agaci"})),

    ("MU37 post-merge: --depo duser (kaynak ANA checkout'a kayar)",
     "kancalar/post-merge",
     ' --tazele --depo "$pruvo_kok" >/dev/null 2>&1; then',
     " --tazele >/dev/null 2>&1; then",
     frozenset({"V10.post-merge-depo-agaci"})),

    ("MU38 pre-push: --depo duser (kaynak ANA checkout'a kayar)",
     "kancalar/pre-push",
     '  python3 "$pruvo_pp_kur" --tazele --depo "$pruvo_pp_kok" </dev/null\n',
     '  python3 "$pruvo_pp_kur" --tazele </dev/null\n',
     frozenset({"V10.pre-push-depo-agaci"})),

    ("MU39 post-commit: damga kesinlestirme kalkar",
     "kancalar/post-commit",
     '  python3 "$pruvo_pc_kur" --tazele --depo "$root" >/dev/null 2>&1\n',
     "  :\n",
     frozenset({"V10.commitli-dal-kancasi-korunur"})),

    ("MU22b post-checkout: kurulu kanca-kur yerine AGACINKI cagrilir",
     "kancalar/post-checkout",
     '[ -f "$(dirname "$0")/kanca-kur.py" ] && pruvo_kur="$(dirname "$0")/kanca-kur.py"\n',
     "",
     # isaret sayaci kumulatif: post-checkout'ta sizan isaret sonraki iki kolu da yakar
     frozenset({"V10.post-checkout-kurulu-arac", "V10.post-merge-kurulu-arac",
                "V10.pre-push-kurulu-arac"})),

    ("MU22c post-merge: kurulu kanca-kur yerine AGACINKI cagrilir",
     "kancalar/post-merge",
     '[ -f "$(dirname "$0")/kanca-kur.py" ] && pruvo_kur="$(dirname "$0")/kanca-kur.py"\n',
     "",
     frozenset({"V10.post-merge-kurulu-arac", "V10.pre-push-kurulu-arac"})),

    ("MU22d pre-push: kurulu kanca-kur yerine AGACINKI cagrilir",
     "kancalar/pre-push",
     '[ -f "$(dirname "$0")/kanca-kur.py" ] && pruvo_pp_kur="$(dirname "$0")/kanca-kur.py"\n',
     "",
     frozenset({"V10.pre-push-kurulu-arac"})),

    # 🔴 MU22 kanca yine AGACIN kanca-kur.py'sini cagirir -> eski agacin KAPISIZ
    # araci paylasilan kopyayi bozar (gecis donemi deligi).
    ("MU22 pre-commit: kurulu kanca-kur yerine AGACINKI cagrilir",
     "kancalar/pre-commit",
     '[ -f "$(dirname "$0")/kanca-kur.py" ] && pruvo_kur="$(dirname "$0")/kanca-kur.py"\n',
     "",
     frozenset({"V10.bozuk-kurulu-arac-agactan-onarilir",
                "V10.kanca-kurulu-araci-kosar"})),

    ("M-K177a nobetci: CI K/S KAPSAM_DISI yerine OLCULEMEDI ilan eder",
     "kanca-kablolama-nobeti.py",
     "return (EKSEN_KABLOLAMA, KAPSAM_DISI,",
     "return (EKSEN_KABLOLAMA, OLCULEMEDI,",
     frozenset({"V5.ci-kablolama-ilan", "V5.ci-hal-yesil"})),

    ("M-K177b nobetci: genel_hal KAPSAM_DISI'yi de hukum dusuren hal sayar",
     "kanca-kablolama-nobeti.py",
     "    if any(h == OLCULEMEDI for _e, h, _m in bulgular):\n        return OLCULEMEDI\n    return YESIL",
     "    if any(h in (OLCULEMEDI, KAPSAM_DISI) for _e, h, _m in bulgular):\n        return OLCULEMEDI\n    return YESIL",
     frozenset({"V5.ci-hal-yesil"})),

    ("M-K177c nobetci: cikis_kodu OLCULEMEDI kolunu atlar",
     "kanca-kablolama-nobeti.py",
     "    if any(h == OLCULEMEDI for _e, h, _m in bulgular):\n        return 1\n    return 0",
     "    return 0",
     frozenset({"V5.ci-muafiyet-dar"})),

    ("M-K177d nobetci: genel_hal OLCULEMEDI'yi YESIL'e yuvarlar",
     "kanca-kablolama-nobeti.py",
     'def genel_hal(bulgular):\n    """🔴 FAIL-CLOSED: OLCULEMEDI asla YESIL\'e YUVARLANMAZ."""\n    if any(h == KIRMIZI for _e, h, _m in bulgular):\n        return KIRMIZI\n    if any(h == OLCULEMEDI for _e, h, _m in bulgular):\n        return OLCULEMEDI',
     'def genel_hal(bulgular):\n    """🔴 FAIL-CLOSED: OLCULEMEDI asla YESIL\'e YUVARLANMAZ."""\n    if any(h == KIRMIZI for _e, h, _m in bulgular):\n        return KIRMIZI\n    if any(h == OLCULEMEDI for _e, h, _m in bulgular):\n        return YESIL',
     frozenset({"V5.ci-hal-olculemedi", "V5.ci-ozet-olculemedi"})),

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


def _ortam_yalitimi_nabzi():
    """🔴 NABIZ: ortam yalitimi (realpath) YERINDE ve YUK TASIYOR mu?

    Bu adimin bulup kapattigi olay: symlinked temp koku (mac `/var` ->
    `/private/var`), MU4 altinda `beklenen` (ham) ile `deger` (realpath)
    arasinda ayrisma yaratip `V4.saglikli-yesil`i YALNIZ mac'te kirmizi
    yakiyordu -> ayni batarya yerelde YESIL, CI'da KIRMIZI. Yalitim `_gecici_kok`
    icindeki `os.path.realpath`tir. Bu nabiz, o yalitim kalkarsa (ya da sembolik
    baglarin ayrismayi sizdirdigi bir ortamda) KIRMIZI yakar.

    Uc iddia:
      (1) HAZARD GERCEK — sembolik-bagli bilesenli HAM yol, hedeften ayrisir
          (yalitim gerekli oldugunun kaniti; her platformda ACIK symlink ile
          zorlanir, ortama bagli DEGIL).
      (2) YALITIM ETKILI — ayni yola `realpath` uygulaninca ayrisma KAPANIR.
      (3) YALITIM FIILEN BAGLI — kos_vakalar'in kullandigi `_gecici_kok` GERCEKTEN
          realpath-normalize dizin doner (raw==realpath). Yalitim satiri
          silinirse mac'te bu iddia KIRMIZI yanar."""
    seg = os.path.join("tools", "kancalar")
    ust = os.path.realpath(tempfile.mkdtemp(prefix="kanca-nabiz-"))
    try:
        gercek = os.path.join(ust, "gercek")
        os.makedirs(gercek)
        bagli = os.path.join(ust, "bagli")
        os.symlink(gercek, bagli)  # bagli -> gercek (ACIK sembolik bag)
        hedef = os.path.normpath(os.path.join(gercek, seg))
        ham = os.path.normpath(os.path.join(bagli, seg))
        assert ham != hedef, (
            "(1) HAZARD fikstürü bozuk: sembolik-bagli HAM yol hedefle AYNI "
            "cikti (ham=%s hedef=%s) -> nabiz ayrismayi olcemiyor" % (ham, hedef))
        yalitimli = os.path.normpath(os.path.join(os.path.realpath(bagli), seg))
        assert yalitimli == hedef, (
            "(2) YALITIM ETKISIZ: realpath sonrasi yol hala ayrisiyor "
            "(yalitimli=%s hedef=%s)" % (yalitimli, hedef))
        k = _gecici_kok("kanca-nabiz-kok-")
        try:
            assert k == os.path.realpath(k), (
                "(3) YALITIM BAGLI DEGIL: _gecici_kok realpath-normalize DEGIL "
                "(k=%s realpath=%s) -> MU4 kill kumesi ortama bagli olur, CI "
                "yesil/yerel kirmizi ayrismasi geri gelir" % (k, os.path.realpath(k)))
        finally:
            shutil.rmtree(k, ignore_errors=True)
    finally:
        shutil.rmtree(ust, ignore_errors=True)


def mutasyon_turu():
    print("MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosyalar DEGISMEZ")
    once = {y: sha256(y) for y in _canli_dosyalar()}
    nabiz_kirmizi = []
    try:
        _ortam_yalitimi_nabzi()
        print("  ORTAM-YALITIMI NABZI: realpath yalitimi YERINDE ✅")
    except AssertionError as e:
        nabiz_kirmizi.append("ORTAM-YALITIMI NABZI KIRMIZI: %s" % e)
        print("  🔴 ORTAM-YALITIMI NABZI: %s" % e)

    taban = subprocess.run([sys.executable, os.path.abspath(__file__), "--sessiz"],
                           capture_output=True, text=True, timeout=1800)
    taban_cikti = taban.stdout + taban.stderr
    taban_iddia = _iddia_sayisi(taban_cikti)
    print("  TABAN: rc=%d iddia=%s kirmizi=%s"
          % (taban.returncode, taban_iddia, sorted(_kirmizi_kume(taban_cikti)) or "{}"))
    kirmizi = list(nabiz_kirmizi)
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
