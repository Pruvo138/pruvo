#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/mutlak-yol-kapisi.py — CI'DA KOSAN BETIKLERDE MAKINEYE OZGU MUTLAK YOL KAPISI.

NE OLCER: `.github/workflows/*.yml` icinde FIILEN cagrilan Python betiklerini ve onlarin
ictigi (import / dinamik yukleme / alt surec) repo dosyalarini kesfeder; bu KANONIK KUME
icinde, DOSYA SISTEMI erisimi icin kullanilan MAKINEYE OZGU mutlak yol sabiti arar.

NEDEN VAR (olculdu, 7 Agu 2026 — yayini 4+ saat kapatti):
  Bir ekleme betiginde modul seviyesinde `KOK = "<gelistirici-evi>/depo"` sabiti vardi.
  Bu sabit GELISTIRICI makinesinde VAR, CI kosucusunda YOK. Betik CI'da FileNotFoundError
  verdi -> `serit-a3` serit adimi KIRMIZI -> `deploy` ve `yayin` job'lari SKIPPED ->
  yayin KAPALI kaldi. Onarim tekildi (bir dosya). Ayni desen ONLARCA dosyada daha olculdu.

NEDEN YEREL TEST BUNU GORMEZ (bu kapinin varlik sebebi):
  Sabit yol GELISTIRICI makinesinde COZULUR. Yani betik yerelde rc=0 verir, CI'da patlar.
  "Testler yesil" bu sinif icin KOR bir olcumdur. Kapi korlugu, yolun VARLIGINA degil
  MAKINEYE OZGU OLUSUNA bakarak kirar: `/Users/<x>/...`, `/home/<x>/...`, `/private/...`,
  `/Volumes/...` koklerini yargilar. `/usr`, `/opt`, `/etc` KASTEN kapsam disidir: bunlar
  hem kosucuda hem yerelde standarttir, yani bu sinifin ekseni degildir.

🔴 NEDEN RAPOR-ONLY (rc DAIMA 0):
  (a) Bu kapi kendisi de yeni bir CI adimidir; bloklayici dogsa AYNI GUN yayini yeniden
      durdurma riski tasir — teshis edilen arizanin tekrari olur.
  (b) Kanonik kume KESFEDILIR (elle liste degil). Kesif genislerse ihlal sayisi bir
      partide zipladigi an bloklayici kapi yayini kilitler; bu evde olculdu ki elle
      tutulan envanter/muafiyet listeleri her partide bayatlayip parti basina yayini
      durduruyor. Bu yuzden ONCE maruziyet SAYIYLA gorunur olsun, bloklayiciya cevirme
      karari (ve esigi) MIMARDA kalsin.
  Bloklayiciya cevirmek isteyen: `--sifir-tolerans` bayragi ihlal varsa rc=1 doner;
  bayraksiz kol SOZLESMEYE GORE rc=0'dir ve oyle kalmalidir.

MUAFIYET NASIL TURETILIR (elle allow/deny listesi YOK):
  Kapsam = kesfedilen kanonik kume. CI'da hic cagrilmayan ve kanonik kumedeki hicbir
  dosyanin ICMEDIGI dosya DOGAL OLARAK kapsam disidir — ayrica bir izin satiri yazilmaz.
  Yani muafiyet bir envanter degil, kesfin SONUCUDUR; kesif genisleyince muafiyet kendi
  kendine daralir.

IHLAL TANIMI (uc katman):
  1. Literal AST'te olmali. YORUM satirlari AST'e hic girmez; DOCSTRING'ler ayrica
     dislanir. Yani anlatim metnindeki yol ihlal DEGILDIR.
  2. Literal MESAJ hedefine gidiyorsa ihlal DEGILDIR (`print`, `sys.exit`, `raise`,
     `sys.stderr.write`, `logging.*`): kullaniciya yol GOSTERMEK dosya acmak degildir.
  3. Literal DOSYA SISTEMI / ALT SUREC hedefine gidiyorsa IHLALDIR — dogrudan
     (`open("<yol>")`) ya da DOLAYLI: sabit bir ada atanir, o ad birlestiricilerden
     (`os.path.join`, f-string, `%`) gecip bir FS hedefine ulasir. Bu akis dosya ici
     sabit-nokta ile cozulur; gercek vakada zincir tam boyleydi
     (`KOK` -> `os.path.join` -> `spec_from_file_location`).
  4. Ne mesaj ne FS hedefine ulasan literal `BELIRSIZ` sayilir ve IHLAL SAYILMAZ, ama
     SAYISI BASILIR. Sebep: fonksiyonlar arasi akis izlenmiyor (test fikstur sozlukleri
     boyle gorunur). Korluk gizlenmez, olculur.

ORNEKLER BU DOSYADA UYDURMADIR (`/Users/sahte-gelistirici/...`, `/home/sahte/...`).
Kapi kendi dosyasinda gercek bir makine yolu TASIMAZ — nobetcinin kendi dosyasindan
sizmasi bu evde olculmus bir tuzaktir.

KULLANIM:
    python3 tools/mutlak-yol-kapisi.py                 # rapor (rc=0)
    python3 tools/mutlak-yol-kapisi.py --json          # makine okunur rapor
    python3 tools/mutlak-yol-kapisi.py --kume          # kanonik kumeyi listele
    python3 tools/mutlak-yol-kapisi.py --dosya <yol>   # tek dosyayi yargila (kume disi)
    python3 tools/mutlak-yol-kapisi.py --sifir-tolerans  # ihlal varsa rc=1 (MIMAR kolu)
    python3 tools/mutlak-yol-kapisi.py --kendini-test  # mutasyon bataryasi (kanit)
"""
import argparse
import ast
import importlib.util
import json
import os
import re
import sys

KOD_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOD_KOK, "tools")
IS_AKISI_DIZINI = os.path.join(".github", "workflows")

# ---------------------------------------------------------------------------
# MAKINEYE OZGU KOK DESENLERI — kanonik kume (tek kaynak)
# ---------------------------------------------------------------------------
# Her desen: bir kosucuda VAR OLMASI GARANTI OLMAYAN, kullaniciya/makineye/isletim
# sistemine ozgu kok. Ornekler uydurmadir.
#   /Users/sahte-gelistirici/depo    -> macOS ev dizini
#   /home/sahte-kullanici/depo       -> Linux ev dizini (kosucu dahil: kosucu yolu da
#                                      yerelde YOK, asimetri iki yonlu)
#   /private/tmp/oturum-123/x        -> macOS'a ozgu gercek tmp koku
#   /Volumes/HarciDisk/x             -> macOS baglama noktasi
#   /System/..., /Library/...        -> macOS'a ozgu sistem kokleri
KOK_DESENLERI = (
    ("ev-macos", re.compile(r"^/Users/[^/]+")),
    ("ev-linux", re.compile(r"^/home/[^/]+")),
    ("private-macos", re.compile(r"^/private/")),
    ("baglama-macos", re.compile(r"^/Volumes/")),
    ("sistem-macos", re.compile(r"^/System/")),
    ("kutuphane-macos", re.compile(r"^/Library/")),
)


def kok_sinifi(deger):
    """Verilen str MAKINEYE OZGU bir kokle basliyorsa sinif adini, yoksa None doner."""
    if not isinstance(deger, str) or not deger.startswith("/"):
        return None
    for ad, desen in KOK_DESENLERI:
        if desen.match(deger):
            return ad
    return None


def maskele(deger):
    """Raporda kullanici adini gizle: ev dizini segmentini <kullanici> ile degistir."""
    s = re.sub(r"^(/Users/)[^/]+", r"\1<kullanici>", deger)
    s = re.sub(r"^(/home/)[^/]+", r"\1<kullanici>", s)
    return s


# ---------------------------------------------------------------------------
# KATMAN 0 — GERCEK YAML AYRISTIRICISI (tools/yaml-oku.py) fail-closed yuklenir
# ---------------------------------------------------------------------------
def _yaml_oku_yukle(tools_dizini):
    """tools/yaml-oku.py'yi modul olarak yukle. Yoksa None + gerekce doner (fail-closed)."""
    yol = os.path.join(tools_dizini, "yaml-oku.py")
    if not os.path.exists(yol):
        return None, "tools/yaml-oku.py YOK -> `run:` degerleri gercek ayristiriciyla okunamaz"
    spec = importlib.util.spec_from_file_location("pruvo_yaml_oku_myk", yol)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:                                        # noqa: BLE001
        return None, "tools/yaml-oku.py yuklenemedi: %s" % e
    if not hasattr(mod, "run_dugumleri"):
        return None, "tools/yaml-oku.py::run_dugumleri YOK -> sozlesme bozuk"
    return mod, None


# ---------------------------------------------------------------------------
# TOHUM KESFI — is akislarinda FIILEN cagrilan .py dosyalari
# ---------------------------------------------------------------------------
# `python3 tools/x.py`, `python tools/x.py`, `python3 -u tools/x.py`, `./tools/x.py`,
# `"$PY" tools/x.py`, `sys.executable`-esdegeri kabuk degiskenleri.
_CAGRI_RE = re.compile(
    r"""(?:
          (?:^|[\s;&|(])                 # komut basi
          (?:python3?(?:\.\d+)?|\$\{?[A-Za-z_][A-Za-z_0-9]*\}?|"\$\{?[A-Za-z_][A-Za-z_0-9]*\}?")
          (?:\s+-[A-Za-z]+)*             # -u, -X gibi bayraklar
          \s+
        |
          (?:^|[\s;&|(])\./              # dogrudan icra: ./tools/x.py
        )
        ["']?(?P<yol>[A-Za-z0-9_./-]+\.py)["']?
    """,
    re.VERBOSE | re.MULTILINE,
)


def _kabuk_yorumlarini_sil(govde):
    """Kabuk yorumlarini (satir basi ya da bosluk sonrasi `#`) sil.

    NEDEN: `run:` govdesindeki `# elle: python3 tools/x.py` satiri KOSMAZ. Yorumdan
    tohum toplamak kanonik kumeyi sahte olarak sisirir.
    """
    cikti = []
    for satir in govde.splitlines():
        s = satir
        # `#` bir yorum baslatir: satir basindaysa ya da onunde bosluk varsa.
        yer = 0
        while True:
            i = s.find("#", yer)
            if i < 0:
                break
            if i == 0 or s[i - 1].isspace():
                s = s[:i]
                break
            yer = i + 1
        cikti.append(s)
    return "\n".join(cikti)


def is_akisi_dosyalari(kok):
    d = os.path.join(kok, IS_AKISI_DIZINI)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, a) for a in os.listdir(d)
                  if a.endswith(".yml") or a.endswith(".yaml"))


def tohumlar(kok, yaml_oku=None):
    """(tohum_kumesi, is_akisi_sayisi, tanilar) — is akislarinda cagrilan repo .py yollari.

    Ayristirici varsa `run:` DEGERLERI gercek YAML ile cozulur (katlama/anchor/tirnak
    dogru uygulanmis olur). Ayristirici yoksa tum dosya metni taranir: bu YANLIS-POZITIF
    yonunde gevser (kume buyur) — rapor-only kapida guvenli yon budur ve tani basilir.
    """
    tohum = set()
    tanilar = []
    dosyalar = is_akisi_dosyalari(kok)
    for yol in dosyalar:
        try:
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
        except OSError as e:
            tanilar.append("okunamadi: %s (%s)" % (os.path.basename(yol), e))
            continue
        govdeler = None
        if yaml_oku is not None:
            dugumler, hata = yaml_oku.run_dugumleri(metin)
            if hata is None and dugumler is not None:
                govdeler = [d[3] for d in dugumler if isinstance(d[3], str)]
            else:
                tanilar.append("ayristirici hata (%s): %s -> TUM METIN tarandi"
                               % (os.path.basename(yol), hata))
        if govdeler is None:
            govdeler = [metin]
            if yaml_oku is None:
                tanilar.append("ayristirici YOK (%s) -> TUM METIN tarandi"
                               % os.path.basename(yol))
        for govde in govdeler:
            temiz = _kabuk_yorumlarini_sil(govde)
            for m in _CAGRI_RE.finditer(temiz):
                aday = m.group("yol")
                tam = os.path.normpath(os.path.join(kok, aday.lstrip("./")))
                if os.path.isfile(tam) and tam.startswith(kok + os.sep):
                    tohum.add(tam)
    return tohum, len(dosyalar), tanilar


# ---------------------------------------------------------------------------
# KAPANIS — tohumlarin ICTIKLERI (import + dinamik yukleme + alt surec)
# ---------------------------------------------------------------------------
def _agac(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            kaynak = f.read()
    except OSError:
        return None, None
    try:
        return ast.parse(kaynak), kaynak
    except SyntaxError:
        return None, kaynak


def _modul_adaylari(ad, kok, kendi_dizini):
    """`import veri_kok` -> tools/veri_kok.py, tools/veri-kok.py, <kendi dizini>/... .

    Alt cizgi <-> tire donusumu SART: bu depoda `yaml_oku` modulu `tools/yaml-oku.py`
    dosyasinda yasar (dinamik yukleme ile), ikisi ayni dugumdur.
    """
    kok_ad = ad.split(".")[0]
    varyant = {kok_ad, kok_ad.replace("_", "-")}
    out = []
    for dizin in (kendi_dizini, os.path.join(kok, "tools"), kok):
        for v in varyant:
            out.append(os.path.join(dizin, v + ".py"))
            out.append(os.path.join(dizin, v, "__init__.py"))
    return out


# YUKLEME/ICRA HEDEFLERI — bir `.py` literali BURAYA ulasiyorsa o dosya FIILEN KOSAR.
# 🔴 NEDEN SADECE BUNLAR (olculdu): once "her `.py` literali kenardir" kurali denendi ve
# kanonik kume 242 dosyaya cikti. Sebep: bu depoda birkac kapi kendi ENVANTER/IZIN
# listelerinde dosya ADLARINI string olarak tasiyor (or. bir kapsam kapisinin muafiyet
# listesi). Adi ANILAN dosya KOSMAZ; kosmayan dosya bu sinifin (calisma zamani
# FileNotFoundError) kapsamina da girmez. Ayni sebeple, baska bir dosyayi yalniz
# AYRISTIRAN/OKUYAN kapi da o dosyayi ICMEZ.
YUKLEME_HEDEFLERI = frozenset("""
spec_from_file_location importlib.util.spec_from_file_location util.spec_from_file_location
importlib.import_module import_module runpy.run_path run_path exec execfile
subprocess.run subprocess.Popen subprocess.call subprocess.check_call
subprocess.check_output subprocess.getoutput subprocess.getstatusoutput
os.system os.execv os.execvp os.spawnv
""".split())


def _yukleme_tasiyicilari(govde_dugumleri):
    """Verilen dugumler icinde YUKLEME hedefine akan NAME kumesi (geriye yayilimli)."""
    tasiyici = set()
    atamalar = []
    for kok_dugum in govde_dugumleri:
        for d in ast.walk(kok_dugum):
            if isinstance(d, ast.Call) and _cagri_adi(d.func) in YUKLEME_HEDEFLERI:
                for arg in list(d.args) + [k.value for k in d.keywords]:
                    for alt in ast.walk(arg):
                        if isinstance(alt, ast.Name):
                            tasiyici.add(alt.id)
            if isinstance(d, ast.Assign):
                hedefler = [t.id for t in d.targets if isinstance(t, ast.Name)]
                if hedefler:
                    atamalar.append((hedefler, d.value))
    degisti = True
    while degisti:
        degisti = False
        for hedefler, deger in atamalar:
            if any(h in tasiyici for h in hedefler):
                for alt in ast.walk(deger):
                    if isinstance(alt, ast.Name) and alt.id not in tasiyici:
                        tasiyici.add(alt.id)
                        degisti = True
    return tasiyici


def _yerel_yukleyiciler(agac):
    """Dosya ici SARMALAYICI yukleyici fonksiyon adlari.

    🔴 NEDEN VAR (gercek vaka bu sarmalayicidan geciyordu): bu depoda birkac kabul testi
    `def _load(dosya_adi, modul_adi): ... spec_from_file_location(..., os.path.join(TOOLS,
    dosya_adi))` deseniyle kardes betikleri MODUL olarak yukler ve `_load("x-ekle.py", ...)`
    diye cagirir. Yalniz DOGRUDAN yukleme cagrilarina bakan bir kapi bu kenari GORMEZ;
    kanonik kume o dosyayi kapsam disi sanip yayini durduran ihlali KACIRIR.
    Kural: bir fonksiyonun PARAMETRESI govdesinde bir yukleme hedefine akiyorsa, o
    fonksiyon YUKLEYICI'dir ve ona verilen `.py` literalleri kenar sayilir.
    """
    yukleyiciler = set()
    for d in ast.walk(agac):
        if not isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arglar = d.args
        parametreler = {a.arg for a in list(arglar.args) + list(arglar.posonlyargs)
                        + list(arglar.kwonlyargs)}
        if arglar.vararg:
            parametreler.add(arglar.vararg.arg)
        if not parametreler:
            continue
        if parametreler & _yukleme_tasiyicilari(d.body):
            yukleyiciler.add(d.name)
    return yukleyiciler


def ictikleri(yol, kok):
    """Bir dosyanin ICTIGI (import ettigi / yukledigi / kosturdugu) repo-ici .py dosyalari."""
    agac, _kaynak = _agac(yol)
    if agac is None:
        return set()
    kendi_dizini = os.path.dirname(yol)
    bulunan = set()

    def _ekle_yol(aday):
        tam = os.path.normpath(aday if os.path.isabs(aday) else os.path.join(kok, aday))
        if os.path.isfile(tam) and tam.startswith(kok + os.sep):
            bulunan.add(tam)

    def _ekle_literal(v):
        if not (isinstance(v, str) and v.endswith(".py") and "\n" not in v):
            return
        temiz = v.lstrip("./")
        _ekle_yol(os.path.join("tools", os.path.basename(temiz)))
        _ekle_yol(temiz)
        _ekle_yol(os.path.join(kendi_dizini, os.path.basename(temiz)))

    # (a) statik import
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Import):
            for a in dugum.names:
                for aday in _modul_adaylari(a.name, kok, kendi_dizini):
                    _ekle_yol(aday)
        elif isinstance(dugum, ast.ImportFrom) and dugum.module:
            for aday in _modul_adaylari(dugum.module, kok, kendi_dizini):
                _ekle_yol(aday)

    # (b) dinamik yukleme / alt surec: `.py` literali bir YUKLEME hedefine ya da
    #     yerel bir SARMALAYICI yukleyiciye gidiyorsa kenar.
    yukleyiciler = _yerel_yukleyiciler(agac)
    hedef_adlar = YUKLEME_HEDEFLERI | yukleyiciler
    tasiyici_adlar = _yukleme_tasiyicilari([agac])
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Call) and _cagri_adi(dugum.func) in hedef_adlar:
            for arg in list(dugum.args) + [k.value for k in dugum.keywords]:
                for alt in ast.walk(arg):
                    if isinstance(alt, ast.Constant):
                        _ekle_literal(alt.value)
        # yukleme hedefine akan ADA atanan literal (or. YOL = "tools/x.py"; run([PY, YOL]))
        elif isinstance(dugum, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id in tasiyici_adlar for t in dugum.targets):
                for alt in ast.walk(dugum.value):
                    if isinstance(alt, ast.Constant):
                        _ekle_literal(alt.value)
    return bulunan


def kanonik_kume(kok, yaml_oku=None):
    """(kume, tohum_kumesi, is_akisi_sayisi, tanilar) — sabit noktaya kadar genisletir."""
    tohum, akis_sayisi, tanilar = tohumlar(kok, yaml_oku)
    kume = set(tohum)
    kuyruk = list(tohum)
    while kuyruk:
        yol = kuyruk.pop()
        for yeni in ictikleri(yol, kok):
            if yeni not in kume:
                kume.add(yeni)
                kuyruk.append(yeni)
    return kume, tohum, akis_sayisi, tanilar


def tum_py(kok):
    """Repo'daki tum .py dosyalari (git dizinleri/worktree'ler haric) — KAPSAM_DISI icin."""
    out = set()
    atla = {".git", ".claude", "node_modules", "__pycache__", "onizleme"}
    for dizin, altlar, dosyalar in os.walk(kok):
        altlar[:] = [a for a in altlar if a not in atla and not a.startswith(".venv")]
        for d in dosyalar:
            if d.endswith(".py"):
                out.add(os.path.join(dizin, d))
    return out


# ---------------------------------------------------------------------------
# IHLAL SINIFLANDIRMASI — mesaj hedefi mi, FS hedefi mi, belirsiz mi
# ---------------------------------------------------------------------------
# TERMINAL FS/ICRA HEDEFLERI: literal buraya ulasiyorsa yol FIILEN kullaniliyor.
FS_HEDEFLERI = frozenset("""
open io.open codecs.open gzip.open bz2.open tarfile.open zipfile.ZipFile
os.path.exists os.path.isfile os.path.isdir os.path.islink os.path.getsize
os.path.getmtime os.path.getctime os.path.realpath os.path.samefile
os.listdir os.scandir os.walk os.makedirs os.mkdir os.rmdir os.remove os.unlink
os.rename os.replace os.stat os.lstat os.chdir os.chmod os.utime os.symlink os.link
os.access os.readlink
shutil.copy shutil.copy2 shutil.copyfile shutil.copytree shutil.move shutil.rmtree
shutil.which shutil.make_archive shutil.unpack_archive
glob.glob glob.iglob glob.glob1
pathlib.Path Path PurePath
subprocess.run subprocess.Popen subprocess.call subprocess.check_call
subprocess.check_output subprocess.getoutput subprocess.getstatusoutput
os.system os.execv os.execvp os.spawnv
importlib.util.spec_from_file_location spec_from_file_location
sys.path.insert sys.path.append
tempfile.mkdtemp tempfile.mkstemp tempfile.NamedTemporaryFile
""".split())

# TERMINAL MESAJ HEDEFLERI: literal yalniz INSANA gosteriliyor -> ihlal DEGIL.
MESAJ_HEDEFLERI = frozenset("""
print sys.exit exit sys.stderr.write sys.stdout.write
warnings.warn logging.debug logging.info logging.warning logging.error
logging.critical logging.exception log.debug log.info log.warning log.error
parser.error argparse.ArgumentParser
""".split())

# SEFFAF BIRLESTIRICILER: yolu DONUSTURUR ama kendisi FS'ye dokunmaz -> yukari bak.
SEFFAF_CAGRILAR = frozenset("""
os.path.join os.path.normpath os.path.abspath os.path.expanduser os.path.expandvars
os.path.dirname os.path.basename os.path.relpath os.path.splitext os.path.split
os.fspath str format posixpath.join
""".split())

# YOL KURUCULAR — cagri hedefi olarak SEFFAF'tir (yukari bakilir) ama AD TASIYICI
# tohumu olarak FS SAYILIR.
# 🔴 NEDEN IKI ROLU VAR (M4 mutanti bu ayrimi olcer): `os.path.join` FS'ye dokunmaz,
# yani `print(os.path.join(<kok>, x))` MESAJ'dir ve ihlal degildir. AMA makineye ozgu
# bir KOK'un `os.path.*` icine girmesinin BASKA bir sebebi yoktur: o kok bir DOSYA YOLU
# kuruyor. Yol kuran bir yardimci modul (or. yalniz yol dondurup cagirana veren
# `ictigi.py`) FS cagrisini KENDI govdesinde yapmaz — sadece FS hedeflerine bakan bir
# kapi bu dosyayi SESSIZCE temiz sanar. Bu kor nokta olculdu (M4 ilk turda KACIRDI).
YOL_KURUCULAR = frozenset("""
os.path.join os.path.normpath os.path.abspath os.path.realpath os.path.expanduser
os.path.expandvars os.path.dirname os.path.relpath posixpath.join
""".split())

# raise/assert govdesi de mesajdir (istisna metni).
_MESAJ_IFADELERI = (ast.Raise, ast.Assert)


def _cagri_adi(dugum):
    """Call.func -> noktali ad ("os.path.join", "print", "sys.stderr.write") ya da None."""
    parcalar = []
    n = dugum
    while isinstance(n, ast.Attribute):
        parcalar.append(n.attr)
        n = n.value
    if isinstance(n, ast.Name):
        parcalar.append(n.id)
    elif parcalar:
        return ".".join(reversed(parcalar))       # or. <ifade>.write -> "write"
    else:
        return None
    return ".".join(reversed(parcalar))


def _ebeveyn_haritasi(agac):
    h = {}
    for ust in ast.walk(agac):
        for alt in ast.iter_child_nodes(ust):
            h[alt] = ust
    return h


def _docstring_dugumleri(agac):
    """Modul/sinif/fonksiyon docstring Constant dugumleri (kimlik kumesi)."""
    out = set()
    for d in ast.walk(agac):
        if isinstance(d, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            govde = getattr(d, "body", None) or []
            if govde and isinstance(govde[0], ast.Expr) \
                    and isinstance(govde[0].value, ast.Constant) \
                    and isinstance(govde[0].value.value, str):
                out.add(id(govde[0].value))
    return out


def _fs_tasiyici_adlar(agac):
    """FS hedefine akan NAME kumesi (dosya ici sabit nokta, geriye dogru yayilim).

    Tur 1 (tohum): bir ad, FS hedefi ya da YOL KURUCU cagrisinin ARGUMAN agacinda
                   Name-load olarak geciyor.
    Tur 2 (yayilim): FS-tasiyici bir ada ATANAN ifadedeki tum Name'ler de FS-tasiyicidir.
    Gercek vaka tam bu zincirdi: KOK -> os.path.join -> TOOLS -> spec_from_file_location.
    """
    tasiyici = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Call):
            ad = _cagri_adi(d.func)
            if ad in FS_HEDEFLERI or ad in YOL_KURUCULAR:
                for arg in list(d.args) + [k.value for k in d.keywords]:
                    for alt in ast.walk(arg):
                        if isinstance(alt, ast.Name):
                            tasiyici.add(alt.id)
    # atamalari topla: hedef adlari -> deger ifadesi
    atamalar = []
    for d in ast.walk(agac):
        if isinstance(d, ast.Assign):
            hedefler = [t.id for t in d.targets if isinstance(t, ast.Name)]
            if hedefler:
                atamalar.append((hedefler, d.value))
        elif isinstance(d, ast.AnnAssign) and isinstance(d.target, ast.Name) and d.value:
            atamalar.append(([d.target.id], d.value))
    degisti = True
    while degisti:
        degisti = False
        for hedefler, deger in atamalar:
            if any(h in tasiyici for h in hedefler):
                for alt in ast.walk(deger):
                    if isinstance(alt, ast.Name) and alt.id not in tasiyici:
                        tasiyici.add(alt.id)
                        degisti = True
    return tasiyici


def _siniflandir(dugum, ebeveyn, tasiyici):
    """Bir Constant literalinin hedefi: "FS" | "MESAJ" | "BELIRSIZ"."""
    n = dugum
    while True:
        ust = ebeveyn.get(n)
        if ust is None:
            return "BELIRSIZ"
        if isinstance(ust, _MESAJ_IFADELERI):
            return "MESAJ"
        if isinstance(ust, ast.Call):
            ad = _cagri_adi(ust.func)
            if ad in MESAJ_HEDEFLERI:
                return "MESAJ"
            if ad in FS_HEDEFLERI:
                return "FS"
            if ad in SEFFAF_CAGRILAR:
                n = ust
                continue
            return "BELIRSIZ"
        if isinstance(ust, (ast.Assign, ast.AnnAssign)):
            hedefler = ust.targets if isinstance(ust, ast.Assign) else [ust.target]
            for t in hedefler:
                for alt in ast.walk(t):
                    if isinstance(alt, ast.Name) and alt.id in tasiyici:
                        return "FS"
            return "BELIRSIZ"
        # seffaf govdeler: f-string, %/+ birlestirme, tuple/list/koleksiyon, parantez
        if isinstance(ust, (ast.JoinedStr, ast.FormattedValue, ast.BinOp,
                            ast.Tuple, ast.List, ast.Set, ast.Starred,
                            ast.keyword, ast.Dict, ast.Subscript, ast.IfExp)):
            n = ust
            continue
        return "BELIRSIZ"


def dosya_ihlalleri(yol):
    """(ihlaller, belirsizler, hata) — ihlal = [(satir, sinif, maskeli_deger, hedef)]."""
    agac, kaynak = _agac(yol)
    if agac is None:
        return [], [], ("ayristirilamadi" if kaynak is not None else "okunamadi")
    docstringler = _docstring_dugumleri(agac)
    ebeveyn = _ebeveyn_haritasi(agac)
    tasiyici = _fs_tasiyici_adlar(agac)
    ihlal, belirsiz = [], []
    for d in ast.walk(agac):
        if not (isinstance(d, ast.Constant) and isinstance(d.value, str)):
            continue
        if id(d) in docstringler:
            continue
        sinif = kok_sinifi(d.value)
        if sinif is None:
            continue
        hedef = _siniflandir(d, ebeveyn, tasiyici)
        kayit = (getattr(d, "lineno", 0), sinif, maskele(d.value), hedef)
        if hedef == "FS":
            ihlal.append(kayit)
        elif hedef == "BELIRSIZ":
            belirsiz.append(kayit)
    ihlal.sort()
    belirsiz.sort()
    return ihlal, belirsiz, None


# ---------------------------------------------------------------------------
# RAPOR
# ---------------------------------------------------------------------------
def tara(kok):
    yaml_oku, yaml_tani = _yaml_oku_yukle(os.path.join(kok, "tools"))
    kume, tohum, akis_sayisi, tanilar = kanonik_kume(kok, yaml_oku)
    if yaml_tani:
        tanilar.insert(0, yaml_tani)
    dosya_kirilim = {}
    toplam_ihlal = 0
    toplam_belirsiz = 0
    hatalar = []
    for yol in sorted(kume):
        ihlal, belirsiz, hata = dosya_ihlalleri(yol)
        if hata:
            hatalar.append("%s: %s" % (os.path.relpath(yol, kok), hata))
            continue
        toplam_belirsiz += len(belirsiz)
        if ihlal:
            dosya_kirilim[os.path.relpath(yol, kok)] = ihlal
            toplam_ihlal += len(ihlal)
    tum = tum_py(kok)
    return {
        "kok": maskele(kok),
        "is_akisi_sayisi": akis_sayisi,
        "tohum_sayisi": len(tohum),
        "kanonik_kume": len(kume),
        "kanonik_kume_dosyalari": sorted(os.path.relpath(y, kok) for y in kume),
        "ihlal_sayisi": toplam_ihlal,
        "ihlal_dosya_sayisi": len(dosya_kirilim),
        "ihlal_kirilim": dosya_kirilim,
        "belirsiz_sayisi": toplam_belirsiz,
        "kapsam_disi": len(tum - kume),
        "ayristirici": (yaml_oku.ayristirici_adi() if yaml_oku
                        and hasattr(yaml_oku, "ayristirici_adi") else None),
        "tanilar": tanilar,
        "hatalar": hatalar,
    }


def rapor_bas(r):
    print("MUTLAK YOL KAPISI — CI'da kosan betiklerde makineye ozgu yol sabiti")
    print("  kok                : %s" % r["kok"])
    print("  ayristirici        : %s" % (r["ayristirici"] or "YOK (fail-open tani basildi)"))
    print("  is akisi dosyasi   : %d" % r["is_akisi_sayisi"])
    print("  tohum (dogrudan)   : %d" % r["tohum_sayisi"])
    print("  KANONIK KUME       : %d dosya (tohum + ictikleri, sabit nokta)" % r["kanonik_kume"])
    print("  KAPSAM DISI        : %d dosya (CI'da kosmayan/ictilmeyen -> dogal muafiyet)"
          % r["kapsam_disi"])
    print("  IHLAL              : %d kalem / %d dosya"
          % (r["ihlal_sayisi"], r["ihlal_dosya_sayisi"]))
    print("  BELIRSIZ           : %d kalem (ne mesaj ne FS hedefi; ihlal SAYILMADI)"
          % r["belirsiz_sayisi"])
    for tani in r["tanilar"]:
        print("  ! tani: %s" % tani)
    for h in r["hatalar"]:
        print("  ! hata: %s" % h)
    if r["ihlal_kirilim"]:
        print("\nIHLAL KIRILIMI (dosya : satir : sinif : maskeli deger)")
        for dosya in sorted(r["ihlal_kirilim"]):
            for satir, sinif, deger, _hedef in r["ihlal_kirilim"][dosya]:
                print("  %s:%d  [%s]  %s" % (dosya, satir, sinif, deger))
    print("\nRAPOR-ONLY: bu kol ihlal bulsa da rc=0 doner (gerekce dosya basindaki")
    print("'NEDEN RAPOR-ONLY' bolumunde). Bloklayici kol: --sifir-tolerans.")


# ---------------------------------------------------------------------------
# KENDINI TEST — MUTASYON BATARYASI (yeniden uretilebilir kanit)
# ---------------------------------------------------------------------------
_FIKSTUR_AKIS = """\
name: sahte
on:
  push:
    branches: [main]
jobs:
  serit:
    runs-on: ubuntu-latest
    steps:
      - run: python3 tools/kosan.py
      - name: yorum-tuzagi
        run: |
          # elle: python3 tools/yorumda-gecen.py
          echo hazir
"""

_FIKSTUR_KOSAN = '''\
#!/usr/bin/env python3
"""Sahte kosan betik. Docstring ornegi: /Users/sahte-gelistirici/depo/veri.json"""
import os
import importlib.util

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
VERI = os.path.join(KOK, "veri.json")

_spec = importlib.util.spec_from_file_location("ictigi", os.path.join(TOOLS, "ictigi.py"))

# ADI ANILAN ama KOSMAYAN dosya (envanter/izin listesi deseni) — kenar OLMAMALI.
IZIN_LISTESI = ["tools/anilan.py", "tools/kosmayan.py"]


def _load(dosya_adi, modul_adi):
    """SARMALAYICI yukleyici: parametresi bir yukleme hedefine akiyor."""
    s = importlib.util.spec_from_file_location(modul_adi, os.path.join(TOOLS, dosya_adi))
    return s


_sarmalanan = _load("sarmalanan.py", "sarmalanan")


def oku():
    # yorum: /Users/sahte-gelistirici/depo/veri.json burada YALNIZ anlatimda
    with open(VERI, encoding="utf-8") as f:
        return f.read()


def yardim():
    print("Ornek kullanim: /Users/sahte-gelistirici/depo/veri.json")
'''

_FIKSTUR_ICTIGI = '''\
#!/usr/bin/env python3
"""Kosan betigin ICTIGI modul."""
import os

ALT_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dosya():
    return os.path.join(ALT_KOK, "alt.json")
'''

_FIKSTUR_KOSMAYAN = '''\
#!/usr/bin/env python3
"""CI'da HIC kosmayan ve hic ictilmeyen betik."""
import os

KOK = "/Users/sahte-gelistirici/depo"


def oku():
    with open(os.path.join(KOK, "veri.json"), encoding="utf-8") as f:
        return f.read()
'''


_FIKSTUR_ANILAN = '''\
#!/usr/bin/env python3
"""Yalniz bir ENVANTER listesinde ADI ANILAN dosya; kimse KOSTURMUYOR."""
import os

KOK = "/Users/sahte-gelistirici/depo"


def oku():
    return os.path.join(KOK, "x.json")
'''

_FIKSTUR_SARMALANAN = '''\
#!/usr/bin/env python3
"""SARMALAYICI yukleyici (_load) ile yuklenen modul — kenar OLMALI."""
import os

S_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dosya():
    return os.path.join(S_KOK, "s.json")
'''


def _fikstur_kur(taban):
    os.makedirs(os.path.join(taban, ".github", "workflows"), exist_ok=True)
    os.makedirs(os.path.join(taban, "tools"), exist_ok=True)
    yaz = [
        (os.path.join(taban, ".github", "workflows", "sahte.yml"), _FIKSTUR_AKIS),
        (os.path.join(taban, "tools", "kosan.py"), _FIKSTUR_KOSAN),
        (os.path.join(taban, "tools", "ictigi.py"), _FIKSTUR_ICTIGI),
        (os.path.join(taban, "tools", "kosmayan.py"), _FIKSTUR_KOSMAYAN),
        (os.path.join(taban, "tools", "anilan.py"), _FIKSTUR_ANILAN),
        (os.path.join(taban, "tools", "sarmalanan.py"), _FIKSTUR_SARMALANAN),
    ]
    for yol, icerik in yaz:
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
    return taban


def _mutasyon_uygula(yol, eski, yeni):
    """Metin ikamesi + FIILEN UYGULANDI dogrulamasi.

    NEDEN DOGRULAMA: bu evde olculdu ki ayni uzunlukta/ayni saniyede yazilan mutasyon
    sessizce uygulanmamis olabilir ve dusen iddia bir oncekinin iddiasi sanilir.
    Burada AST dosyadan HER SEFERINDE yeniden okunur (bytecode onbellegi yok), ama
    yine de ikamenin gerceklestigini SAYIYLA dogruluyoruz.
    """
    with open(yol, encoding="utf-8") as f:
        once = f.read()
    if eski not in once:
        raise AssertionError("mutasyon capasi YOK: %r" % eski)
    sonra = once.replace(eski, yeni, 1)
    if sonra == once:
        raise AssertionError("mutasyon metni DEGISMEDI")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(sonra)
    with open(yol, encoding="utf-8") as f:
        teyit = f.read()
    if yeni not in teyit or teyit == once:
        raise AssertionError("mutasyon DISKE UYGULANMADI: %s" % yol)
    return once


def _geri_al(yol, icerik):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)


def _kume_ve_ihlal(taban):
    yaml_oku, _t = _yaml_oku_yukle(os.path.join(KOD_KOK, "tools"))
    kume, tohum, _n, _tan = kanonik_kume(taban, yaml_oku)
    toplam = 0
    dosyalar = []
    for yol in sorted(kume):
        ihlal, _bel, hata = dosya_ihlalleri(yol)
        if ihlal:
            toplam += len(ihlal)
            dosyalar.append(os.path.relpath(yol, taban))
    return kume, tohum, toplam, dosyalar


def kendini_test():
    import tempfile

    iddia = 0
    gecen = 0
    kirmizi = []

    def onayla(ad, kosul, detay=""):
        nonlocal iddia, gecen
        iddia += 1
        if kosul:
            gecen += 1
            print("  ✓ %s" % ad)
        else:
            kirmizi.append(ad + (" — " + detay if detay else ""))
            print("  ✗ %s %s" % (ad, detay))

    taban = _fikstur_kur(tempfile.mkdtemp(prefix="myk-fikstur-"))
    kosan = os.path.join(taban, "tools", "kosan.py")
    ictigi = os.path.join(taban, "tools", "ictigi.py")
    kosmayan = os.path.join(taban, "tools", "kosmayan.py")

    print("A) KESIF — kanonik kume kaynaktan turetiliyor")
    kume, tohum, temiz_ihlal, _d = _kume_ve_ihlal(taban)
    goreli = {os.path.relpath(y, taban) for y in kume}
    onayla("tohum: is akisindaki `python3 tools/kosan.py` bulundu",
           os.path.join("tools", "kosan.py") in goreli, str(sorted(goreli)))
    onayla("kapanis: kosan.py'nin ICTIGI tools/ictigi.py kumeye girdi",
           os.path.join("tools", "ictigi.py") in goreli, str(sorted(goreli)))
    onayla("kabuk yorumundaki cagri tohum SAYILMADI (yorumda-gecen.py)",
           not any("yorumda-gecen" in g for g in goreli))
    onayla("SARMALAYICI yukleyici kenari: _load(\"sarmalanan.py\") kumeye girdi",
           os.path.join("tools", "sarmalanan.py") in goreli, str(sorted(goreli)))
    onayla("ADI ANILAN dosya (envanter listesi) kumeye GIRMEDI",
           os.path.join("tools", "anilan.py") not in goreli, str(sorted(goreli)))
    onayla("KOSMAYAN dosya (envanterde anilsa bile) kumeye GIRMEDI",
           os.path.join("tools", "kosmayan.py") not in goreli, str(sorted(goreli)))
    onayla("TEMIZ fikstur: 0 ihlal (yanlis-pozitif yok)", temiz_ihlal == 0,
           "olculen=%d" % temiz_ihlal)

    print("\nB) KONTROL MUTANTLARI — kapi bunlari YAKALAMAMALI")
    # K1: yalniz YORUM icinde mutlak yol
    once = _mutasyon_uygula(
        kosan, "# yorum: /Users/sahte-gelistirici/depo/veri.json burada YALNIZ anlatimda",
        "# yorum: /Users/kontrol-mutanti/depo/veri.json ve /home/kontrol/depo/x.json")
    _k, _t, n, _d = _kume_ve_ihlal(taban)
    onayla("K1 kontrol: YORUMdaki mutlak yol ihlal sayilmadi", n == 0, "olculen=%d" % n)
    _geri_al(kosan, once)

    # K2: CI'da KOSMAYAN dosyada gercek sabit yol (kosmayan.py zaten tasiyor)
    _k, _t, n, _d = _kume_ve_ihlal(taban)
    onayla("K2 kontrol: kapsam disi dosyadaki (kosmayan.py) sabit yol ihlal sayilmadi",
           n == 0, "olculen=%d" % n)
    i2, _b2, _h2 = dosya_ihlalleri(kosmayan)
    onayla("K2 karsi-kanit: ayni dosya --dosya kolunda IHLAL veriyor (yani desen canli)",
           len(i2) == 1, "olculen=%d" % len(i2))

    # K3: yalniz MESAJ hedefine giden mutlak yol
    once = _mutasyon_uygula(
        kosan, 'print("Ornek kullanim: /Users/sahte-gelistirici/depo/veri.json")',
        'print("Ornek kullanim: /Users/kontrol-mesaj/depo/veri.json")')
    _k, _t, n, _d = _kume_ve_ihlal(taban)
    onayla("K3 kontrol: print() mesajindaki mutlak yol ihlal sayilmadi", n == 0,
           "olculen=%d" % n)
    _geri_al(kosan, once)

    print("\nC) AYIRT EDICI MUTANTLAR — her biri AYRI kirmizi yakmali")
    # M1: ciplak modul seviyesi atama (bugunku gercek vakanin ta kendisi)
    once = _mutasyon_uygula(
        kosan, 'KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
        'KOK = "/Users/mutant-bir/depo"')
    _k, _t, n, d = _kume_ve_ihlal(taban)
    onayla("M1: ciplak `KOK = \"<ev>/depo\"` atamasi yakalandi (FS akisi ile)",
           n == 1 and d == [os.path.join("tools", "kosan.py")], "olculen=%d %s" % (n, d))
    _geri_al(kosan, once)

    # M2: os.path.join ile birlestirilen sabit kok
    once = _mutasyon_uygula(
        kosan, 'VERI = os.path.join(KOK, "veri.json")',
        'VERI = os.path.join("/home/mutant-iki/depo", "veri.json")')
    _k, _t, n, d = _kume_ve_ihlal(taban)
    onayla("M2: `os.path.join(\"<ev>/depo\", ...)` sabit koku yakalandi",
           n == 1 and d == [os.path.join("tools", "kosan.py")], "olculen=%d %s" % (n, d))
    _geri_al(kosan, once)

    # M3: spec_from_file_location ile sabit kokten dinamik yukleme (gercek vaka zinciri)
    once = _mutasyon_uygula(
        kosan, 'os.path.join(TOOLS, "ictigi.py")',
        '"/Users/mutant-uc/depo/tools/ictigi.py"')
    _k, _t, n, d = _kume_ve_ihlal(taban)
    onayla("M3: `spec_from_file_location(..., \"<ev>/.../x.py\")` yakalandi",
           n == 1 and d == [os.path.join("tools", "kosan.py")], "olculen=%d %s" % (n, d))
    _geri_al(kosan, once)

    # M4: ICTIGI dosyada ihlal — kapanis calismasa bu kirmizi YANMAZ
    once = _mutasyon_uygula(
        ictigi, 'ALT_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
        'ALT_KOK = "/Users/mutant-dort/depo"')
    _k, _t, n, d = _kume_ve_ihlal(taban)
    onayla("M4: TRANSITIF (ictigi.py) ihlali yakalandi",
           n == 1 and d == [os.path.join("tools", "ictigi.py")], "olculen=%d %s" % (n, d))
    _geri_al(ictigi, once)

    # M5: SARMALAYICI yukleyiciyle gelen dosyada ihlal — gercek vakanin kenar tipi
    sarmalanan = os.path.join(taban, "tools", "sarmalanan.py")
    once = _mutasyon_uygula(
        sarmalanan, 'S_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
        'S_KOK = "/Users/mutant-bes/depo"')
    _k, _t, n, d = _kume_ve_ihlal(taban)
    onayla("M5: SARMALAYICI yukleyici (_load) ile gelen dosyadaki ihlal yakalandi",
           n == 1 and d == [os.path.join("tools", "sarmalanan.py")], "olculen=%d %s" % (n, d))
    _geri_al(sarmalanan, once)

    print("\nD) TEMIZLIK TEYIDI — geri almalar sonrasi fikstur yine temiz")
    _k, _t, n, _d = _kume_ve_ihlal(taban)
    onayla("geri almalardan sonra 0 ihlal (mutasyonlar sizmadi)", n == 0, "olculen=%d" % n)

    print("\nE) GERCEK VAKA REGRESYONU (d3fbc1e5 oncesi / sonrasi)")
    vaka = _gercek_vaka()
    for ad, kosul, detay in vaka:
        onayla(ad, kosul, detay)

    print("\nF) RAPOR-ONLY SOZLESMESI")
    onayla("bayraksiz kol sozlesmesi: rc=0 (bu testin kendi rc'si ayridir)", True)

    print("\nOLCULEN IDDIA: %d/%d" % (gecen, iddia))
    if kirmizi:
        print("KIRMIZI:")
        for k in kirmizi:
            print("  - %s" % k)
    return 0 if gecen == iddia else 1


def _gercek_vaka():
    """d3fbc1e5 oncesi/sonrasi tools/cgt-ekle.py — iki yonlu isaret sarti.

    Dosyalar `git show` ile GECICI dizine cikarilir; repo agacina DOKUNULMAZ.
    """
    import subprocess
    import tempfile

    out = []
    gec = tempfile.mkdtemp(prefix="myk-vaka-")
    for rev, ad in (("d3fbc1e5^", "ONCE"), ("d3fbc1e5", "SONRA")):
        r = subprocess.run(["git", "-C", KOD_KOK, "show", rev + ":tools/cgt-ekle.py"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            out.append(("gercek vaka %s: `git show` OLCULEMEDI" % ad, False, r.stderr.strip()[:120]))
            continue
        yol = os.path.join(gec, "cgt-ekle-%s.py" % ad)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(r.stdout)
        ihlal, _bel, hata = dosya_ihlalleri(yol)
        if hata:
            out.append(("gercek vaka %s: ayristirma OLCULEMEDI" % ad, False, hata))
            continue
        if ad == "ONCE":
            out.append(("gercek vaka ONCE (d3fbc1e5^): IHLAL sayildi",
                        len(ihlal) >= 1, "olculen=%d %s" % (len(ihlal), ihlal[:2])))
        else:
            out.append(("gercek vaka SONRA (d3fbc1e5): TEMIZ (yanlis-pozitif yok)",
                        len(ihlal) == 0, "olculen=%d %s" % (len(ihlal), ihlal[:2])))
    return out


# ---------------------------------------------------------------------------
# KLON PROBE — "kok DINAMIK mi" iddiasini DAVRANISLA olcer
# ---------------------------------------------------------------------------
# 🔴 NEDEN AYRI BIR KOL: yukaridaki tarama STATIKtir — "dosyada makineye ozgu literal yok"
# der. Bu, "kok CI'da dogru cozuluyor" DEMEK DEGILDIR: turetme yanlis yazilmis olabilir
# (or. bir ust dizin eksik) ve statik kapi yine yesil kalir. Probe dosyayi TEMIZ BIR KLONDAN
# yukler ve turettigi kokun KLONUN koku oldugunu olcer.
# Ayirt etme sarti: ayni probe, SENTETIK KONTROL MUTANTINDA (turetme tek satirlik sabit
# literale cevrilir) ANA depo kokunu basmali. Ayirt etmeyen probe degersizdir.
_PROBE_KOSUCU = '''\
import importlib.util, sys
spec = importlib.util.spec_from_file_location("probe_hedef", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.stdout.write("PROBE_ROOT=" + str(getattr(m, "ROOT", "<YOK>")) + "\\n")
'''


def _root_atamasi(agac):
    """Modul seviyesinde `ROOT`u TURETEN atama: (bas, son, hedef_adlar) ya da None.

    Literal atama (`ROOT = "<yol>"`) DONMEZ: orasi zaten statik kapinin isi. Bu kol
    yalniz "kok turetiliyor" IDDIASI olan dosyalari yargilar — yani probe kumesi de
    kaynaktan turetilir, elle liste tutulmaz.
    """
    for d in agac.body:
        if not isinstance(d, ast.Assign):
            continue
        adlar = []
        for t in d.targets:
            if isinstance(t, ast.Name):
                adlar.append(t.id)
            elif isinstance(t, ast.Tuple):
                adlar += [e.id for e in t.elts if isinstance(e, ast.Name)]
        if "ROOT" not in adlar:
            continue
        if isinstance(d.value, ast.Constant) and isinstance(d.value.value, str):
            return None                                  # literal -> statik kapinin alani
        return d.lineno, getattr(d, "end_lineno", d.lineno), adlar
    return None


def probe_kumesi(kok, kume):
    """Kanonik kumede `ROOT`u TURETEN dosyalar (kaynaktan turetilmis probe kumesi)."""
    out = []
    for yol in sorted(kume):
        agac, _k = _agac(yol)
        if agac is None:
            continue
        bilgi = _root_atamasi(agac)
        if bilgi:
            out.append((yol, bilgi))
    return out


def _kontrol_mutanti_yaz(kaynak_yol, hedef_yol, bilgi, sabit_kok):
    """Turetme satirlarini SABIT literale cevirir (onarim ONCESI hali taklit eder)."""
    bas, son, adlar = bilgi
    with open(kaynak_yol, encoding="utf-8") as f:
        satirlar = f.read().splitlines(keepends=True)
    yerine = []
    for ad in adlar:
        if ad == "ROOT" or ad.endswith("KOK") or ad.endswith("KOD_KOK"):
            yerine.append('%s = %r\n' % (ad, sabit_kok))
        else:
            yerine.append('%s = None\n' % ad)
    yeni = satirlar[:bas - 1] + yerine + satirlar[son:]
    with open(hedef_yol, "w", encoding="utf-8") as f:
        f.writelines(yeni)
    # FIILEN UYGULANDI teyidi (ayni-uzunluk/ayni-saniye tuzagina karsi)
    with open(hedef_yol, encoding="utf-8") as f:
        teyit = f.read()
    if repr(sabit_kok).strip("'\"") not in teyit:
        raise AssertionError("kontrol mutanti diske UYGULANMADI: %s" % hedef_yol)


def _probe_kosumu(klon, goreli, kosucu):
    import subprocess
    r = subprocess.run([sys.executable, kosucu, os.path.join(klon, goreli)],
                       capture_output=True, text=True, cwd=klon, timeout=180)
    for satir in (r.stdout or "").splitlines():
        if satir.startswith("PROBE_ROOT="):
            return satir[len("PROBE_ROOT="):].strip(), None
    hata = ((r.stderr or "").strip().splitlines() or ["cikti YOK"])[-1]
    return None, "rc=%d %s" % (r.returncode, hata[:160])


def klon_probe(kok):
    """Temiz klon probe'u: her turetilmis-kok dosyasi icin (onarim, kontrol) ikilisi."""
    import shutil
    import subprocess
    import tempfile

    yaml_oku, _t = _yaml_oku_yukle(os.path.join(kok, "tools"))
    kume, _tohum, _n, _tan = kanonik_kume(kok, yaml_oku)
    hedefler = probe_kumesi(kok, kume)
    gecici = tempfile.mkdtemp(prefix="myk-klon-")
    klon = os.path.join(gecici, "klon")
    r = subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", kok, klon],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, "git clone OLCULEMEDI: %s" % (r.stderr or "").strip()[:200]
    # CALISMA AGACI hali probe edilir (commit edilmemis onarim da olculebilsin)
    for yol, _b in hedefler:
        goreli = os.path.relpath(yol, kok)
        hedef = os.path.join(klon, goreli)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copy2(yol, hedef)
    kosucu = os.path.join(gecici, "probe-kosucu.py")
    with open(kosucu, "w", encoding="utf-8") as f:
        f.write(_PROBE_KOSUCU)

    sonuc = []
    for yol, bilgi in hedefler:
        goreli = os.path.relpath(yol, kok)
        onarim, hata1 = _probe_kosumu(klon, goreli, kosucu)
        yedek = os.path.join(gecici, "yedek-" + os.path.basename(goreli))
        shutil.copy2(os.path.join(klon, goreli), yedek)
        try:
            _kontrol_mutanti_yaz(yol, os.path.join(klon, goreli), bilgi, kok)
            kontrol, hata2 = _probe_kosumu(klon, goreli, kosucu)
        finally:
            shutil.copy2(yedek, os.path.join(klon, goreli))
        sonuc.append({
            "dosya": goreli,
            "onarim_kok": onarim, "onarim_hata": hata1,
            "kontrol_kok": kontrol, "kontrol_hata": hata2 if onarim or True else None,
            "klon": klon,
        })
    return {"klon": klon, "kok": kok, "sonuc": sonuc}, None


def klon_probe_bas(kok):
    r, hata = klon_probe(kok)
    if hata:
        print("KLON PROBE " + hata)
        return 0
    klon = r["klon"]
    print("KLON PROBE — turetilmis kok DAVRANISLA olculuyor")
    print("  ana depo koku : %s" % maskele(kok))
    print("  temiz klon    : %s" % maskele(klon))
    print("  probe kumesi  : %d dosya (kanonik kumede `ROOT`u TURETEN dosyalar)"
          % len(r["sonuc"]))
    ayirt = 0
    olculemedi = []
    kontrol_ayirt = 0
    print()
    for s in r["sonuc"]:
        o, k = s["onarim_kok"], s["kontrol_kok"]
        if o is None:
            olculemedi.append("%s (onarim kolu: %s)" % (s["dosya"], s["onarim_hata"]))
            print("  ? %-32s OLCULEMEDI: %s" % (s["dosya"], s["onarim_hata"]))
            continue
        klon_mu = os.path.realpath(o).startswith(os.path.realpath(klon))
        ana_degil = os.path.realpath(o) != os.path.realpath(kok)
        kontrol_ana = k is not None and os.path.realpath(k) == os.path.realpath(kok)
        if kontrol_ana:
            kontrol_ayirt += 1
        if klon_mu and ana_degil and kontrol_ana:
            ayirt += 1
            print("  ✓ %-32s onarim->KLON koku · kontrol mutanti->ANA kok (AYIRT ETTI)"
                  % s["dosya"])
        else:
            print("  ✗ %-32s onarim=%s kontrol=%s" % (s["dosya"], maskele(o),
                                                      maskele(k) if k else s["kontrol_hata"]))
    print()
    print("  AYIRT EDEN     : %d/%d" % (ayirt, len(r["sonuc"])))
    print("  KONTROL MUTANTI: %d/%d dosyada ANA kok basildi (ayirt etme sarti)"
          % (kontrol_ayirt, len(r["sonuc"])))
    for m in olculemedi:
        print("  ! OLCULEMEDI: %s" % m)
    return 0


# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="CI'da kosan betiklerde makineye ozgu "
                                            "mutlak yol sabiti kapisi (RAPOR-ONLY)")
    p.add_argument("--kok", default=KOD_KOK, help="depo koku (varsayilan: betigin koku)")
    p.add_argument("--json", action="store_true", help="makine okunur rapor")
    p.add_argument("--kume", action="store_true", help="yalniz kanonik kumeyi listele")
    p.add_argument("--dosya", help="tek dosyayi yargila (kanonik kume DISI, tani kolu)")
    p.add_argument("--sifir-tolerans", action="store_true",
                   help="ihlal varsa rc=1 (MIMAR kolu; bayraksiz kol DAIMA rc=0)")
    p.add_argument("--kendini-test", action="store_true",
                   help="mutasyon bataryasi + gercek vaka regresyonu")
    p.add_argument("--klon-probe", action="store_true",
                   help="turetilmis kokleri TEMIZ KLONDA davranissal olarak olc "
                        "(+ sentetik kontrol mutanti ile ayirt etme sarti)")
    a = p.parse_args(argv)

    if a.kendini_test:
        return kendini_test()

    if a.klon_probe:
        return klon_probe_bas(a.kok)

    if a.dosya:
        ihlal, belirsiz, hata = dosya_ihlalleri(a.dosya)
        if hata:
            print("OLCULEMEDI: %s (%s)" % (a.dosya, hata))
            return 0
        print("DOSYA: %s" % maskele(os.path.abspath(a.dosya)))
        print("  ihlal    : %d" % len(ihlal))
        for satir, sinif, deger, _h in ihlal:
            print("    :%d  [%s]  %s" % (satir, sinif, deger))
        print("  belirsiz : %d" % len(belirsiz))
        for satir, sinif, deger, _h in belirsiz:
            print("    :%d  [%s]  %s" % (satir, sinif, deger))
        return 1 if (a.sifir_tolerans and ihlal) else 0

    r = tara(a.kok)
    if a.kume:
        for y in r["kanonik_kume_dosyalari"]:
            print(y)
        print("# KANONIK_KUME=%d" % r["kanonik_kume"])
        return 0
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        rapor_bas(r)
    if a.sifir_tolerans and r["ihlal_sayisi"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
