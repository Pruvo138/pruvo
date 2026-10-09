#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sentetik git depolarini kanonik ortam yardimcisina zorlayan fail-closed kapi."""
import ast
import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
YARDIMCI = os.path.join(TOOLS, "git_ortami.py")


# Depo YAZAN git alt komutlari. `config` yalniz okuma bayragi YOKSA yazma sayilir.
YAZAN_ALT = ("init", "clone", "update-ref")
CONFIG_OKUMA = ("--get", "--get-all", "--get-regexp", "--list", "-l", "--show-origin",
                "--show-scope", "--name-only")
DOGRUDAN = ("subprocess.run", "subprocess.call", "subprocess.check_call",
            "subprocess.check_output", "subprocess.Popen")
# Gecici dizin kaniti: hedef ifadesi bu cagrilardan TURER.
GECICI_IZ = ("tempfile.", "mkdtemp", "gettempdir", "TemporaryDirectory")
# GIT_* scrub kaniti: env ifadesi kanonik scrub'dan ya da GIT_ onek filtresinden TURER.
SCRUB_IZ = ("git_ortami", 'startswith("GIT_")', "startswith('GIT_')",
            "GIT_BAGLAM_DEGISKENLERI")


def _ad(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return _ad(n.value) + "." + n.attr
    return ""


def _yazan_mi(sabitler):
    if any(a in sabitler for a in YAZAN_ALT):
        return True
    return "config" in sabitler and not any(b in sabitler for b in CONFIG_OKUMA)


def _metin(dugum):
    # `ast.get_source_segment` her cagrida TUM kaynagi yeniden boler (karesel; olculdu
    # 63 sn). `unparse` dugum boyutunda dogrusaldir; tirnaklar tek tirnaga normallesir.
    try:
        return ast.unparse(dugum)
    except Exception:  # noqa: BLE001  (bilinmeyen dugum -> iz yok sayilir, fail-closed)
        return ""


def _turev_adlar(agac, izler):
    """Atamasi `izler`den birini tasiyan adlar + onlardan turetilenler (sabit nokta)."""
    atamalar = []
    for n in ast.walk(agac):
        if isinstance(n, ast.Assign):
            hedefler, deger = n.targets, n.value
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.value is not None:
            hedefler, deger = [n.target], n.value
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            hedefler, deger = [n.optional_vars], n.context_expr
        else:
            continue
        adlar = {x.id for h in hedefler for x in ast.walk(h) if isinstance(x, ast.Name)}
        atamalar.append((adlar, _metin(deger),
                         {x.id for x in ast.walk(deger) if isinstance(x, ast.Name)}))
    kume = set()
    degisti = True
    while degisti:
        degisti = False
        for adlar, metin, kullanilan in atamalar:
            if adlar - kume and (any(i in metin for i in izler) or kullanilan & kume):
                kume |= adlar
                degisti = True
    return kume


def _dogrudan_guvenli(n, agac, onbellek):
    """Dogrudan (kanonik yardimcisiz) YAZAN git cagrisi YALNIZ hedefi gecici dizinden
    turuyorsa VE env'i GIT_* scrub'indan turuyorsa guvenlidir. Gecici hedef TEK BASINA
    YETMEZ: miras GIT_DIR varken `git init <gecici>` GERCEK depoyu yeniden kurar
    (9 Eki 2026, core.bare=true kazasi)."""
    env = [k.value for k in n.keywords if k.arg == "env"]
    if not env:
        return False
    if not onbellek:
        onbellek["gecici"] = _turev_adlar(agac, GECICI_IZ)
        onbellek["scrub"] = _turev_adlar(agac, SCRUB_IZ)
    gecici, scrub = onbellek["gecici"], onbellek["scrub"]
    env_metin = _metin(env[0])
    env_adlar = {x.id for x in ast.walk(env[0]) if isinstance(x, ast.Name)}
    if not (any(i in env_metin for i in SCRUB_IZ) or env_adlar & scrub):
        return False
    hedef = list(n.args) + [k.value for k in n.keywords if k.arg == "cwd"]
    for h in hedef:
        if any(i in _metin(h) for i in GECICI_IZ):
            return True
        if {x.id for x in ast.walk(h) if isinstance(x, ast.Name)} & gecici:
            return True
    return False


def sinifla(yol):
    try:
        kaynak = open(yol, encoding="utf-8").read()
        agac = ast.parse(kaynak, filename=yol)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return "OLCULEMEDI", "kaynak ayrisamadi: %s" % exc
    # Muafiyet dosya adindan degil, kanonik yardimci taniminin kendisinden TURETILIR.
    tanimlar = {n.name for n in ast.walk(agac) if isinstance(n, (ast.FunctionDef,
                                                                 ast.AsyncFunctionDef))}
    if "sentetik_git" in tanimlar:
        govdeler = {n.name: ast.get_source_segment(kaynak, n) or ""
                    for n in ast.walk(agac) if isinstance(n, ast.FunctionDef)}
        git_ort = govdeler.get("git_ortami", "")
        sentetik = govdeler.get("sentetik_git", "")
        if ("os.environ.copy()" not in git_ort or ".pop(ad, None)" not in git_ort
                or ".pop(ad, None)" not in sentetik or "cwd=calisma_dizini" not in sentetik):
            return "OLCULEMEDI", "kanonik yardimcinin kopya/scrub/cwd garantisi eksik"
        return "MUAF", "kanonik yardimci tanimi"
    onbellek = {}  # turev ad kumeleri yalniz dogrudan yazan cagri varsa hesaplanir
    kurucu = []
    belirsiz = []
    sizan = []
    kullaniyor = False
    for n in ast.walk(agac):
        if isinstance(n, (ast.Name, ast.Attribute)) and _ad(n).endswith("sentetik_git"):
            kullaniyor = True
        if not isinstance(n, ast.Call):
            continue
        sabitler = [x.value for x in ast.walk(n)
                    if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        if _yazan_mi(sabitler):
            cagri = _ad(n.func)
            if cagri.endswith("sentetik_git"):
                kurucu.append((n.lineno, "kanonik"))
            elif cagri in DOGRUDAN and "git" in sabitler:
                kurucu.append((n.lineno, "dogrudan"))
                # Cagri BAZINDA hukum: dosyanin baska yerde kanonik yardimciyi kullanmasi
                # bu cagriyi AKLAMAZ.
                if not _dogrudan_guvenli(n, agac, onbellek):
                    sizan.append(n.lineno)
            elif (cagri.split(".")[-1] in ("g", "_git", "git", "kos", "_kos")
                  and ("init" in sabitler or "clone" in sabitler)):
                # Dolayli kol yalniz DEPO KURUCUSUNU sorar: sarmalayicidan gecen
                # `config`/`update-ref` uretim yazimidir (or. kanca-kur hooksPath).
                belirsiz.append(n.lineno)
    if not kurucu and not belirsiz:
        return "KAPSAM_DISI", "sentetik git depo kurucusu yok"
    if sizan:
        return "SIZDIRIYOR", ("dogrudan yazan git cagrisi gecici hedef + GIT_* scrub "
                              "kanitsiz: satir %s" % sizan[0])
    if belirsiz and not kullaniyor:
        return "OLCULEMEDI", "dolayli git kurucusunun ortami kanitlanamadi: satir %s" % belirsiz[0]
    return "TEMIZ", "sentetik git yalniz kanonik yardimciyla cagriliyor"


def tara(tools=TOOLS):
    sonuc = []
    for ad in sorted(os.listdir(tools)):
        if ad.endswith(".py"):
            sonuc.append((ad, *sinifla(os.path.join(tools, ad))))
    return sonuc


def kendini_test():
    vakalar = {
        "sizdiran.py": ('import subprocess\nsubprocess.run(["git","init","x"])\n', "SIZDIRIYOR"),
        "temiz.py": ('from git_ortami import sentetik_git\nsentetik_git("x","init")\n', "TEMIZ"),
        "kapsam.py": ('print("git yok")\n', "KAPSAM_DISI"),
        "dolayli_temiz.py": ('import git_ortami as g\ndef kur():\n g.sentetik_git("x","init")\n', "TEMIZ"),
        "belirsiz.py": ('def g(*a): pass\ng("init")\n', "OLCULEMEDI"),
        # 9 Eki 2026 olayinin bicimi: hedef GECICI ama env miras -> GIT_DIR gercek depoya iner.
        "mkdtemp_mirasli.py": ('import subprocess,tempfile\nd=tempfile.mkdtemp()\n'
                               'subprocess.run(["git","init","-q",d])\n', "SIZDIRIYOR"),
        # Cagri bazinda: dosyanin baska yerde kanonik yardimciyi kullanmasi aklamaz.
        "karisik.py": ('from git_ortami import sentetik_git\nsentetik_git("x","init")\n'
                       'import subprocess\nsubprocess.run(["git","init"],cwd="/x")\n',
                       "SIZDIRIYOR"),
        "config_yaz.py": ('import subprocess\n'
                          'subprocess.run(["git","config","core.bare","true"])\n', "SIZDIRIYOR"),
        "update_ref.py": ('import subprocess\nsubprocess.run(["git","update-ref",'
                          '"refs/remotes/origin/x","HEAD"])\n', "SIZDIRIYOR"),
        "config_oku.py": ('import subprocess\n'
                          'subprocess.run(["git","config","--get","core.bare"])\n', "KAPSAM_DISI"),
        "scrub_gecici.py": ('import os,subprocess,tempfile\nd=tempfile.mkdtemp()\n'
                            'a=os.path.join(d,"ana")\n'
                            't={k:v for k,v in os.environ.items() if not k.startswith("GIT_")}\n'
                            'subprocess.run(["git","init","-q",a],env=t)\n', "TEMIZ"),
        "scrub_gercek.py": ('import os,subprocess\n'
                            't={k:v for k,v in os.environ.items() if not k.startswith("GIT_")}\n'
                            'subprocess.run(["git","init","-q","/Users/x/depo"],env=t)\n',
                            "SIZDIRIYOR"),
        "gecici_env_yok.py": ('import subprocess,tempfile\n'
                              'with tempfile.TemporaryDirectory() as d:\n'
                              ' subprocess.run(["git","update-ref","refs/x","HEAD"],cwd=d)\n',
                              "SIZDIRIYOR"),
        "yardimci.py": ('import os\ndef git_ortami():\n o=os.environ.copy()\n'
                         ' for ad in ("GIT_DIR",): o.pop(ad, None)\n return o\n'
                         'def sentetik_git(calisma_dizini,*a):\n o=git_ortami()\n'
                         ' for ad in ("GIT_DIR",): o.pop(ad, None)\n'
                         ' return run(a, cwd=calisma_dizini)\n', "MUAF"),
    }
    iddia = 0
    with tempfile.TemporaryDirectory(prefix="pruvo-fikstur-kapi-") as d:
        for ad, (govde, beklenen) in vakalar.items():
            yol = os.path.join(d, ad)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde)
            olculen, sebep = sinifla(yol)
            iddia += 1
            print("%s %s beklenen=%s olculen=%s (%s)" %
                  ("OK" if olculen == beklenen else "FAIL", ad, beklenen, olculen, sebep))
            if olculen != beklenen:
                return 1
    print("SONUC: YESIL — iddia %d" % iddia)
    return 0


def main():
    if "--kendini-test" in sys.argv[1:]:
        return kendini_test()
    argv = sys.argv[1:]
    dizin = TOOLS
    if "--dizin" in argv:
        i = argv.index("--dizin")
        if i + 1 >= len(argv) or not os.path.isdir(argv[i + 1]):
            print("SONUC: OLCULEMEDI — --dizin gecerli bir dizin degil")
            return 2
        dizin = argv[i + 1]
    kirmizi = 0
    for ad, durum, sebep in tara(dizin):
        if durum in ("SIZDIRIYOR", "OLCULEMEDI"):
            kirmizi += 1
            print("KIRMIZI %s: %s — %s" % (durum, ad, sebep))
    if kirmizi:
        print("SONUC: KIRMIZI — %d dosya" % kirmizi)
        return 1
    print("SONUC: YESIL — sentetik git fiksturleri kanonik")
    return 0


if __name__ == "__main__":
    sys.exit(main())
