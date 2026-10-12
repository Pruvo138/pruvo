#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/wrangler-log-kapisi.py — wrangler ALT SURECI cagiran her yer disk logunu kapatiyor mu?

SORUN (12 Eki 2026, K440): `~/.wrangler/logs` gun icinde buyuyordu (352 -> 368); logu kapatan
tek yer `tools/d1-sync.py::wrangler_ortami()` idi. Elle cikarilan envanter 16 yer saydi ama
EKSIKTI ([[elle-tutulan-ev-kumesi-3-kez-bayatladi-diskten-turetilir]]) — bu kapi evreni TURETIR:

  PYTHON (AST): `subprocess.run/Popen/check_output/check_call/call` cagrilari; komut ifadesi
    wrangler'a cozulurse (dogrudan dizge, liste elemani `npx`+`wrangler@4`, ad -> atama,
    `self.x` -> atama, yerel fonksiyon donusu, PARAMETRE -> ayni dosyadaki cagri yerinin
    argumani) CAGRI sayilir. KANIT: `env=` ifadesi `wrangler_ortami(...)` cagrisina cozulur ve
    o ad `wrangler_ortam` modulunden gelir (ya da yerel tanim, gecerli `WRANGLER_LOG_KAPALI`
    sabitine dayanir). Yardimcinin CANLI degeri ayrica olculur: `"false"` degilse HICBIR
    yardimci kaniti gecmez.
  JS/MJS: `child_process`ten gelen `spawn/spawnSync/execFile/execFileSync/exec/execSync`;
    arguman metni (ad -> bildirim, sarmalayici fonksiyon parametresi -> cagri yerleri) wrangler
    jetonu tasirsa CAGRI. KANIT: secenek metninde (ya da cozulen adin bildiriminde)
    `WRANGLER_WRITE_LOGS: "false"`.

Kapsam: izlenen (git ls-files; depo degilse dizin yurumesi) `.py/.js/.mjs`; `.github/` (CI
kosucusu, disk tutmaz) DISI — ayrica sayilir. Jeton = KOMUT bicimi: liste elemani
`wrangler` / `wrangler@<surum>` / `.../wrangler` ya da kabuk dizgesinde `wrangler <altkomut>`
(`wrangler-log-nobetcisi.py`, `wrangler.toml`, "wrangler kilitlendi" mesaji SAYILMAZ).

Cikti: `WRANGLER_CAGRI=<n> LOG_KAPALI=<n> LOG_ACIK=<n> CI_DISI=<n>`; acik yer varsa
`WRANGLER_LOG_ACIK=<n>` + dosya:satir listesi, rc=1. `--kok <dizin>` baska agaci olcer,
`--liste` tum cagri yerlerini basar.
"""
import argparse
import ast
import importlib.util
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from git_ortami import git_ortami  # noqa: E402 — miras git baglami `-C`yi ezmesin

# KOMUT jetonu (veri degil): liste elemani `wrangler`/`wrangler@4`/`.../.bin/wrangler` ya da kabuk
# dizgesinde `wrangler[@v] <altkomut>`. "wrangler kilitlendi" gibi MESAJ dizgesi komut SAYILMAZ
# (sayilsaydi wrangler ciktisini isleyen her fonksiyonun donusu komut gibi yayilirdi).
ELEMAN_JETON = re.compile(r"^(?:\S*/)?wrangler(?:@[\w.^~*-]+)?$")
KABUK_JETON = re.compile(r"(?:^|[\s;&|(/])wrangler(?:@[\w.^~*-]+)?\s+(?:d1|r2|kv|deploy|dev|secret|versions|"
                         r"deployments|pages|whoami|tail|containers|login|queues|types|workflows|hyperdrive|"
                         r"vectorize|dispatch-namespace)\b")
JS_DIZGE = re.compile(r"""(["'`])((?:\\.|(?!\1).)*)\1""", re.S)
SP_FONK = {"run", "Popen", "check_output", "check_call", "call"}
JS_FONK = {"spawn", "spawnSync", "execFile", "execFileSync", "exec", "execSync"}
JS_KANIT = re.compile(r"""WRANGLER_WRITE_LOGS["']?\s*:\s*["']false["']""")
YARDIMCI_AD = "wrangler_ortami"
YARDIMCI_MODUL = "wrangler_ortam"
KAPSAM_DISI_ONEK = (".github/",)
DERINLIK = 6  # ad -> bildirim -> sarmalayici parametresi -> cagri yeri zinciri icin yeter
# Bu cagrilarin ARGUMANLARI donus degerine akar (komut listesi kurar); digerlerinin argumani
# komut DEGIL veridir (`subprocess.run([... git ...]).stdout` gibi) ve izlenmez.
SEFFAF = {"list", "tuple", "sorted", "str", "dict", "join", "split", "format", "copy", "get", "strip"}
JS_GLOBAL = {"JSON", "path", "fs", "process", "Object", "Math", "String", "Number", "Array", "console",
             "require", "Buffer", "os", "Date", "Error", "Promise", "Boolean", "RegExp", "Set", "Map",
             "true", "false", "null", "undefined", "new", "return", "typeof", "await", "async",
             "function", "const", "let", "var", "if", "else", "this", "of", "in"}


def jeton_var(dizge):
    """Tek bir dizge DEGERI wrangler komut jetonu mu."""
    d = (dizge or "").strip()
    return bool(ELEMAN_JETON.match(d) or KABUK_JETON.search(d))


def js_jeton_var(metin):
    """JS kaynak parcasindaki dizge literallerinden biri komut jetonu mu."""
    return any(jeton_var(m.group(2)) for m in JS_DIZGE.finditer(metin or ""))


# --------------------------------------------------------------------------- dosya evreni
def dosyalar(kok):
    if os.path.exists(os.path.join(kok, ".git")):
        r = subprocess.run(["git", "-C", kok, "ls-files", "-z"], capture_output=True, text=True,
                           env=git_ortami())
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            raise SystemExit("OLCULEMEDI: git ls-files rc=%d" % r.returncode)
        yollar = [y for y in r.stdout.split("\0") if y]
    else:
        yollar = []
        for d, alt, ds in os.walk(kok):
            alt[:] = [a for a in alt if a not in (".git", "node_modules", "__pycache__")]
            for a in ds:
                yollar.append(os.path.relpath(os.path.join(d, a), kok))
    return sorted(y for y in yollar if y.endswith((".py", ".js", ".mjs")))


# --------------------------------------------------------------------------- Python
class PyModul:
    def __init__(self, yol, kaynak, yardimci_canli):
        self.yol = yol
        self.canli = yardimci_canli
        self.agac = ast.parse(kaynak, filename=yol)
        self.kapsam = {}                 # dugum -> kapsayan fonksiyon (ya da None)
        self._kapsamla(self.agac, None)
        self.sp_ad = {"subprocess"}      # import subprocess [as x]
        self.sp_fonk = set()             # from subprocess import run [as x]
        self.yardimci_import = set()     # from wrangler_ortam import wrangler_ortami [as x]
        self.yardimci_modul = set()      # import wrangler_ortam [as x]
        self.sabit_import = False
        self.fonk = {}                   # ad -> [FunctionDef]
        self.ad_atama = {}               # ad -> [(deger, kapsam)]
        self.nitelik_atama = {}          # self.<nitelik> -> [(deger, kapsam)]
        self.cagri = {}                  # cagrilan ad -> [Call]
        self.memo = {}
        for d in ast.walk(self.agac):
            k = self.kapsam.get(d)
            if isinstance(d, ast.Import):
                for a in d.names:
                    if a.name == "subprocess":
                        self.sp_ad.add(a.asname or a.name)
                    if a.name == YARDIMCI_MODUL:
                        self.yardimci_modul.add(a.asname or a.name)
            elif isinstance(d, ast.ImportFrom):
                for a in d.names:
                    if d.module == "subprocess" and a.name in SP_FONK:
                        self.sp_fonk.add(a.asname or a.name)
                    if d.module == YARDIMCI_MODUL and a.name == YARDIMCI_AD:
                        self.yardimci_import.add(a.asname or a.name)
                    if d.module == YARDIMCI_MODUL and a.name == "WRANGLER_LOG_KAPALI":
                        self.sabit_import = True
            elif isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.fonk.setdefault(d.name, []).append(d)
            elif isinstance(d, (ast.Assign, ast.AugAssign, ast.AnnAssign)) and d.value is not None:
                hedefler = d.targets if isinstance(d, ast.Assign) else [d.target]
                for h in hedefler:
                    if isinstance(h, ast.Attribute):
                        self.nitelik_atama.setdefault(h.attr, []).append((d.value, k))
                    for t in ast.walk(h):
                        if isinstance(t, ast.Name):
                            self.ad_atama.setdefault(t.id, []).append((d.value, k))
            elif isinstance(d, ast.Call):
                f = d.func
                # fonksiyon cagri yeri: `ad(...)` ya da `self.ad(...)`; `subprocess.run` gibi baska
                # nesnenin yontemi yerel `def run`a BAGLANMAZ
                ad = f.id if isinstance(f, ast.Name) else (
                    f.attr if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                    and f.value.id in ("self", "cls") else None)
                if ad:
                    self.cagri.setdefault(ad, []).append(d)
                if (isinstance(f, ast.Attribute) and f.attr in ("append", "extend", "insert")
                        and isinstance(f.value, ast.Name)):
                    self.ad_atama.setdefault(f.value.id, []).extend((a, k) for a in d.args)

    @staticmethod
    def _yuru(ifade):
        """ast.walk; ama SEFFAF olmayan cagrinin argumanlarina inmez (onlar komut degil veridir)."""
        yigin = [ifade]
        while yigin:
            d = yigin.pop()
            yield d
            if isinstance(d, ast.Call):
                f = d.func
                ad = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
                yigin.append(f)
                if ad in SEFFAF:
                    yigin.extend(d.args)
                    yigin.extend(k.value for k in d.keywords)
            elif isinstance(d, (ast.Lambda, ast.FunctionDef)):
                continue
            else:
                yigin.extend(ast.iter_child_nodes(d))

    def _kapsamla(self, dugum, kapsam):
        for c in ast.iter_child_nodes(dugum):
            self.kapsam[c] = kapsam
            yeni = c if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) else kapsam
            self._kapsamla(c, yeni)

    def sp_cagrisi_mi(self, c):
        f = c.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            return f.attr in SP_FONK and f.value.id in self.sp_ad
        return isinstance(f, ast.Name) and f.id in self.sp_fonk

    def atamalar(self, ad, kapsam):
        """Kapsayan fonksiyonda atanmissa yalniz oradakiler, degilse modul duzeyi (komsu
        fonksiyonun ayni adli yereli KARISMAZ)."""
        hepsi = self.ad_atama.get(ad, [])
        yakin = [x for x in hepsi if kapsam is not None and x[1] is kapsam]
        return yakin or [x for x in hepsi if x[1] is None]

    @staticmethod
    def param_konumu(fonk, ad):
        if fonk is None or isinstance(fonk, ast.Lambda):
            return None
        for i, a in enumerate(fonk.args.posonlyargs + fonk.args.args):
            if a.arg == ad:
                return (i, ad)
        if any(a.arg == ad for a in fonk.args.kwonlyargs):
            return (None, ad)
        return None

    def cagri_argumani(self, cagri, fonk, konum):
        i, ad = konum
        for k in cagri.keywords:
            if k.arg == ad:
                return k.value
        if i is None:
            return None
        yontem = (isinstance(cagri.func, ast.Attribute) and fonk.args.args
                  and fonk.args.args[0].arg in ("self", "cls"))
        j = i - 1 if yontem else i
        if 0 <= j < len(cagri.args) and not any(isinstance(a, ast.Starred) for a in cagri.args[:j + 1]):
            return cagri.args[j]
        return None

    def varsayilan(self, fonk, konum):
        i, ad = konum
        a = fonk.args
        if i is not None:
            k = i - (len(a.posonlyargs + a.args) - len(a.defaults))
            return a.defaults[k] if 0 <= k < len(a.defaults) else None
        return next((v for arg, v in zip(a.kwonlyargs, a.kw_defaults) if arg.arg == ad), None)

    def _coz(self, tur, ifade, kapsam, yaprak, tum_cagri, derinlik=0):
        """Ifade `yaprak` kosulunu saglayan bir dugume cozuluyor mu (ad -> atama, self.x -> atama,
        parametre -> ayni dosyadaki cagri yerleri, yerel fonksiyon -> return). Dongu korumali memo."""
        if ifade is None or derinlik > DERINLIK:
            return False
        anahtar = (tur, id(ifade), id(kapsam))
        if anahtar in self.memo:
            return self.memo[anahtar]
        self.memo[anahtar] = False  # dongu: cozumdeyken tekrar gelirse olumsuz
        sonuc = False
        for d in self._yuru(ifade):
            if yaprak(d):
                sonuc = True
            elif isinstance(d, ast.Name) and isinstance(d.ctx, ast.Load):
                konum = self.param_konumu(kapsam, d.id)
                if konum is not None:
                    # parametrenin DEGER KAYNAKLARI: cagri yerinde gecen arguman + fonksiyon icindeki
                    # yeniden atama (`if ort is None: ort = ...`) + (yeniden atama yoksa ve bir cagri
                    # yeri gecmiyorsa) varsayilan deger
                    kaynak, eksik = [], False
                    for c in self.cagri.get(kapsam.name, []):
                        a = self.cagri_argumani(c, kapsam, konum)
                        if a is None:
                            eksik = True
                        else:
                            kaynak.append((a, self.kapsam.get(c)))
                    yerel = [x for x in self.ad_atama.get(d.id, []) if x[1] is kapsam]
                    kaynak += yerel
                    if (eksik or not kaynak) and not yerel:
                        kaynak.append((self.varsayilan(kapsam, konum), None))
                    sonuclar = [self._coz(tur, v, k, yaprak, tum_cagri, derinlik + 1) for v, k in kaynak]
                    # kanit: TUM kaynaklar kanitli olmali (biri log acik ortam verirse ACIK)
                    sonuc = all(sonuclar) if tum_cagri else any(sonuclar)
                else:
                    sonuc = any(self._coz(tur, v, k, yaprak, tum_cagri, derinlik + 1) for v, k in self.atamalar(d.id, kapsam))
            elif isinstance(d, ast.Attribute) and isinstance(d.value, ast.Name) and d.value.id in ("self", "cls"):
                sonuc = any(self._coz(tur, v, k, yaprak, tum_cagri, derinlik + 1) for v, k in self.nitelik_atama.get(d.attr, []))
            elif isinstance(d, ast.Call) and not tum_cagri:
                ad = d.func.id if isinstance(d.func, ast.Name) else (
                    d.func.attr if isinstance(d.func, ast.Attribute) else None)
                sonuc = any(self._coz(tur, r.value, fd, yaprak, tum_cagri, derinlik + 1)
                            for fd in self.fonk.get(ad, []) for r in ast.walk(fd) if isinstance(r, ast.Return))
            if sonuc:
                break
        self.memo[anahtar] = sonuc
        return sonuc

    def wrangler_mi(self, ifade, kapsam):
        return self._coz("w", ifade, kapsam,
                         lambda d: isinstance(d, ast.Constant) and isinstance(d.value, str) and jeton_var(d.value),
                         False)

    def yerel_yardimci_gecerli(self):
        """Yerel `def wrangler_ortami` + log kapatan `WRANGLER_LOG_KAPALI` (import ya da literal)."""
        tanimlar = self.fonk.get(YARDIMCI_AD)
        if not tanimlar or not all(any(isinstance(n, ast.Name) and n.id == "WRANGLER_LOG_KAPALI"
                                       for n in ast.walk(fd)) for fd in tanimlar):
            return False
        return self.sabit_gecerli()

    def sabit_gecerli(self):
        """Moduldeki `WRANGLER_LOG_KAPALI` log kapatiyor mu (yardimcidan import + canli, ya da literal)."""
        if self.sabit_import:
            return self.canli
        for d in self.agac.body:
            if isinstance(d, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WRANGLER_LOG_KAPALI"
                                                 for t in d.targets):
                try:
                    return ast.literal_eval(d.value) == {"WRANGLER_WRITE_LOGS": "false"}
                except ValueError:
                    return False
        return False

    def _yardimci_cagrisi(self, d):
        if not isinstance(d, ast.Call):
            return False
        f = d.func
        # import kaniti ancak yardimcinin CANLI degeri dogruysa gecer
        if isinstance(f, ast.Name) and f.id in self.yardimci_import:
            return self.canli
        if (isinstance(f, ast.Attribute) and f.attr == YARDIMCI_AD and isinstance(f.value, ast.Name)
                and f.value.id in self.yardimci_modul):
            return self.canli
        return isinstance(f, ast.Name) and f.id == YARDIMCI_AD and self.yerel_yardimci_gecerli()

    def _kanit_yapragi(self, d):
        """Yardimci cagrisi ya da gecerli sabitin acilimi: `dict(..., **WRANGLER_LOG_KAPALI)`."""
        if self._yardimci_cagrisi(d):
            return True
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dict":
            return any(k.arg is None and isinstance(k.value, ast.Name) and k.value.id == "WRANGLER_LOG_KAPALI"
                       for k in d.keywords) and self.sabit_gecerli()
        if isinstance(d, ast.Dict):
            return any(k is None and isinstance(v, ast.Name) and v.id == "WRANGLER_LOG_KAPALI"
                       for k, v in zip(d.keys, d.values)) and self.sabit_gecerli()
        return False

    def kanitli_mi(self, ifade, kapsam):
        return self._coz("k", ifade, kapsam, self._kanit_yapragi, True)


def py_tara(yol, kaynak, yardimci_canli):
    try:
        m = PyModul(yol, kaynak, yardimci_canli)
    except SyntaxError:
        return []
    sonuc = []
    for d in ast.walk(m.agac):
        if not (isinstance(d, ast.Call) and m.sp_cagrisi_mi(d)):
            continue
        kapsam = m.kapsam.get(d)
        komut = d.args[0] if d.args else next((k.value for k in d.keywords if k.arg == "args"), None)
        if not m.wrangler_mi(komut, kapsam):
            continue
        env = next((k.value for k in d.keywords if k.arg == "env"), None)
        sonuc.append({"yol": yol, "satir": d.lineno, "dil": "py",
                      "kapali": env is not None and m.kanitli_mi(env, kapsam)})
    return sonuc


# --------------------------------------------------------------------------- JS
def _yorumsuz(metin):
    """Yorumlari ayni uzunlukta bosluga cevirir (satir numaralari korunur)."""
    cikti, i, n = [], 0, len(metin)
    while i < n:
        c = metin[i]
        if c in "\"'`":
            j = i + 1
            while j < n and metin[j] != c:
                j += 2 if metin[j] == "\\" else 1
            cikti.append(metin[i:j + 1])
            i = j + 1
        elif metin.startswith("//", i):
            j = metin.find("\n", i)
            j = n if j < 0 else j
            cikti.append(" " * (j - i))
            i = j
        elif metin.startswith("/*", i):
            j = metin.find("*/", i + 2)
            j = n if j < 0 else j + 2
            cikti.append(re.sub(r"[^\n]", " ", metin[i:j]))
            i = j
        else:
            cikti.append(c)
            i += 1
    return "".join(cikti)


def _kapanis(metin, ac):
    """`metin[ac]` acan parantez/suslu; eslesen kapanisin indeksi (dizgeleri atlar)."""
    esler = {"(": ")", "{": "}", "[": "]"}
    yigin, i, n = [], ac, len(metin)
    while i < n:
        c = metin[i]
        if c in "\"'`":
            j = i + 1
            while j < n and metin[j] != c:
                j += 2 if metin[j] == "\\" else 1
            i = j + 1
            continue
        if c in esler:
            yigin.append(esler[c])
        elif yigin and c == yigin[-1]:
            yigin.pop()
            if not yigin:
                return i
        i += 1
    return n


def _ifade_sonu(metin, bas):
    """`bas`tan baslayan ifadenin (derinlik 0'da `;` ya da bos satir) sonu."""
    i, n = bas, len(metin)
    while i < n:
        c = metin[i]
        if c in "([{":
            i = _kapanis(metin, i) + 1
            continue
        if c in "\"'`":
            j = i + 1
            while j < n and metin[j] != c:
                j += 2 if metin[j] == "\\" else 1
            i = j + 1
            continue
        if c == ";" or (c == "\n" and not metin[bas:i].rstrip().endswith((",", "+", "=", "(", "?", ":", "&&", "||"))):
            return i
        i += 1
    return n


TANIM = r"(?:const|let|var)\s+"
KELIME = re.compile(r"[A-Za-z_$][\w$]*")


class JsModul:
    def __init__(self, yol, kaynak):
        self.yol = yol
        self.metin = _yorumsuz(kaynak)
        self.memo, self._bildirim = {}, None
        cp = r"""(?:require\(\s*["'](?:node:)?child_process["']\s*\))"""
        self.uye = set(re.findall(TANIM + r"([A-Za-z_$][\w$]*)\s*=\s*" + cp, self.metin))
        self.uye |= set(re.findall(r"import\s+(?:\*\s+as\s+)?([A-Za-z_$][\w$]*)\s+from\s+[\"'](?:node:)?child_process[\"']",
                                   self.metin))
        self.ad = {}
        bloklar = re.findall(TANIM + r"\{([^}]*)\}\s*=\s*" + cp, self.metin)
        bloklar += re.findall(r"import\s*\{([^}]*)\}\s*from\s*[\"'](?:node:)?child_process[\"']", self.metin)
        for blok in bloklar:
            for parca in blok.split(","):
                p = re.split(r"\s*(?::|\bas\b)\s*", parca.strip())
                if p and p[0] in JS_FONK:
                    self.ad[p[-1]] = p[0]
        self.fonklar = []  # (ad, parametreler, govde_bas, govde_son)
        for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(", self.metin):
            self._fonk_ekle(m.group(1), m.end() - 1)
        for m in re.finditer(TANIM + r"([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\s*[\w$]*\s*)?\(", self.metin):
            self._fonk_ekle(m.group(1), m.end() - 1)

    def _fonk_ekle(self, ad, par_ac):
        par_kap = _kapanis(self.metin, par_ac)
        sonra = self.metin[par_kap + 1:par_kap + 12]
        g = re.match(r"\s*(?:=>\s*)?\{", sonra)
        if not g:
            return
        govde = par_kap + 1 + g.end() - 1
        params = [p.split("=")[0].strip().lstrip(".") for p in self.metin[par_ac + 1:par_kap].split(",")]
        self.fonklar.append((ad, [p for p in params if p], govde, _kapanis(self.metin, govde)))

    def satir(self, i):
        return self.metin.count("\n", 0, i) + 1

    def cagrilar(self):
        uye = "|".join(re.escape(u) for u in self.uye)
        desenler = []
        if self.ad:
            desenler.append(r"(?<![\w$.])(" + "|".join(re.escape(a) for a in self.ad) + r")\s*\(")
        if uye:
            desenler.append(r"(?<![\w$.])(?:" + uye + r")\s*\.\s*(" + "|".join(JS_FONK) + r")\s*\(")
        for d in desenler:
            for m in re.finditer(d, self.metin):
                ac = m.end() - 1
                yield ac, self.metin[ac + 1:_kapanis(self.metin, ac)]

    def kapsayan(self, i):
        aday = [f for f in self.fonklar if f[2] < i < f[3]]
        return min(aday, key=lambda f: f[3] - f[2]) if aday else None

    def bildirim(self, ad):
        """`ad`in bildirim (const/let/var, yapi bozma) + atama/push/concat metinleri (tek gecis indeksi)."""
        if self._bildirim is None:
            ix = {}
            for m in re.finditer(TANIM + r"(\{[^}]*\}|\[[^\]]*\]|[A-Za-z_$][\w$]*)\s*=(?![=>])", self.metin):
                govde = self.metin[m.end():_ifade_sonu(self.metin, m.end())]
                for ad_ in KELIME.findall(re.sub(r":\s*[A-Za-z_$][\w$]*", "", m.group(1))
                                         if m.group(1)[0] in "{[" else m.group(1)):
                    ix.setdefault(ad_, []).append(govde)
            for m in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*(?:\.\s*(?:push|unshift|concat)\s*\(|\+?=(?![=>]))",
                                 self.metin):
                if re.search(r"(?:const|let|var)\s+$", self.metin[max(0, m.start() - 8):m.start()]):
                    continue
                if self.metin[m.end() - 1] == "(":
                    govde = self.metin[m.end():_kapanis(self.metin, m.end() - 1)]
                else:
                    govde = self.metin[m.end():_ifade_sonu(self.metin, m.end())]
                ix.setdefault(m.group(1), []).append(govde)
            self._bildirim = ix
        return self._bildirim.get(ad, [])

    def _coz(self, tur, metin, konum, kosul, tum_cagri, derinlik=0):
        if kosul(metin):
            return True
        if derinlik >= DERINLIK:
            return False
        f = self.kapsayan(konum)
        # nesne anahtari (`ad:`) ve nitelik (`.ad`) cozulmez; yalniz serbest adlar
        serbest = re.sub(r"(?<![\w$.])[A-Za-z_$][\w$]*\s*:(?!:)", " ", JS_DIZGE.sub(" ", metin))
        for ad in sorted(set(re.findall(r"(?<![\w$.])[A-Za-z_$][\w$]*", serbest))):
            if ad in JS_FONK or ad in JS_GLOBAL or ad in self.uye:
                continue
            anahtar = (tur, ad, f[2] if f else -1, derinlik)
            if anahtar not in self.memo:
                self.memo[anahtar] = False  # dongu korumasi
                self.memo[anahtar] = self._ad_coz(tur, ad, f, konum, kosul, tum_cagri, derinlik + 1)
            if self.memo[anahtar]:
                return True
        return False

    def _ad_coz(self, tur, ad, f, konum, kosul, tum_cagri, derinlik):
        if f and ad in f[1]:
            k = f[1].index(ad)
            sonuclar = []
            for m in re.finditer(r"(?<![\w$.])" + re.escape(f[0]) + r"\s*\(", self.metin):
                if re.search(r"function\s*$", self.metin[max(0, m.start() - 12):m.start()]):
                    continue  # tanimin kendisi, cagri degil
                ac = m.end() - 1
                arglar = _argumanlar(self.metin[ac + 1:_kapanis(self.metin, ac)])
                sonuclar.append(k < len(arglar) and self._coz(tur, arglar[k], ac, kosul, tum_cagri, derinlik))
            return (bool(sonuclar) and all(sonuclar)) if tum_cagri else any(sonuclar)
        return any(self._coz(tur, b, konum, kosul, tum_cagri, derinlik) for b in self.bildirim(ad))

    def wrangler_mi(self, arg, konum):
        return self._coz("w", arg, konum, js_jeton_var, False)

    def kanitli_mi(self, arg, konum):
        return self._coz("k", arg, konum, lambda t: bool(JS_KANIT.search(t)), True)


def _argumanlar(metin):
    sonuc, bas, i, n = [], 0, 0, len(metin)
    while i < n:
        c = metin[i]
        if c in "([{":
            i = _kapanis(metin, i) + 1
            continue
        if c in "\"'`":
            j = i + 1
            while j < n and metin[j] != c:
                j += 2 if metin[j] == "\\" else 1
            i = j + 1
            continue
        if c == ",":
            sonuc.append(metin[bas:i])
            bas = i + 1
        i += 1
    sonuc.append(metin[bas:])
    return [s.strip() for s in sonuc]


def js_tara(yol, kaynak):
    m = JsModul(yol, kaynak)
    sonuc = []
    for ac, arg in m.cagrilar():
        if not m.wrangler_mi(arg, ac):
            continue
        sonuc.append({"yol": yol, "satir": m.satir(ac), "dil": "js", "kapali": m.kanitli_mi(arg, ac)})
    return sonuc


# --------------------------------------------------------------------------- yardimci canli degeri
def yardimci_canli_mi(kok):
    """`tools/wrangler_ortam.py` gercekten `WRANGLER_WRITE_LOGS=false` veriyor mu (calistirarak)."""
    yol = os.path.join(kok, "tools", YARDIMCI_MODUL + ".py")
    if not os.path.isfile(yol):
        return False, "yardimci yok: tools/%s.py" % YARDIMCI_MODUL
    try:
        spec = importlib.util.spec_from_file_location("_wrangler_ortam_olcum", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ort = mod.wrangler_ortami({"KORUNAN": "1"})
    except Exception as e:  # noqa: BLE001 — her dusus = kanit yok
        return False, "yardimci coktu: %s" % e
    if ort.get("WRANGLER_WRITE_LOGS") != "false" or ort.get("KORUNAN") != "1":
        return False, "yardimci log kapatmiyor/env korumuyor: %r" % ort
    return True, ""


def turet(kok):
    canli, neden = yardimci_canli_mi(kok)
    cagrilar, ci = [], 0
    for yol in dosyalar(kok):
        tam = os.path.join(kok, yol)
        try:
            with open(tam, encoding="utf-8") as f:
                kaynak = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if "wrangler" not in kaynak:
            continue
        bulgu = py_tara(yol, kaynak, canli) if yol.endswith(".py") else js_tara(yol, kaynak)
        if yol.startswith(KAPSAM_DISI_ONEK):
            ci += len(bulgu)
            continue
        cagrilar.extend(bulgu)
    return cagrilar, ci, canli, neden


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kok", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()
    cagrilar, ci, canli, neden = turet(os.path.abspath(a.kok))
    acik = [c for c in cagrilar if not c["kapali"]]
    if not canli:
        print("YARDIMCI_GECERSIZ: " + neden)
    if a.liste:
        for c in cagrilar:
            print("%s %s:%d" % ("KAPALI" if c["kapali"] else "ACIK  ", c["yol"], c["satir"]))
    print("WRANGLER_CAGRI=%d LOG_KAPALI=%d LOG_ACIK=%d CI_DISI=%d"
          % (len(cagrilar), len(cagrilar) - len(acik), len(acik), ci))
    if acik:
        print("WRANGLER_LOG_ACIK=%d" % len(acik))
        for c in acik:
            print("  %s:%d" % (c["yol"], c["satir"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
