#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTANT CANLI YAZIM KAPISI — mutasyon surucusu `finally`de EV dosyasina yazamaz.

🔴 NEDEN (7 Eki 2026): mutasyon suruculeri mutanti CANLI kaynaga yazip `finally` ile geri
aliyordu. `finally` SIGKILL'de (CI iptali, zaman asimi, paralel oturum) KOSMAZ: ev dosyasi
MUTANT halde kalir ve kardes kapilar onu kendi kirmizisi sanar
([[mutant-canli-govdede-yasamaz]]). Onarim kalibi `mutasyon_kopya.kopyada_kos` /
`kopya_kok` + `gercek_dosya`: mutant yalniz gecici kopyaya yazilir. Bu kapi SINIFI kapatir:
yeni bir surucu eski kalibi geri getirirse KIRMIZI yanar.

NE OLCER (AST, calistirmadan): `tools/*mutasyon*.py` + `tools/*mutant*.py` icindeki her
`try ... finally` govdesinde
  (a) dogrudan bir YAZIM cagrisi (open w/a/x/+ · write_text/write_bytes · os.remove/unlink/
      rename/replace/utime/truncate · shutil.copy*/move/rmtree), ya da
  (b) yazim yapan YEREL fonksiyon cagrisi (modul ya da ic ice tanim; derinlik <= 3,
      parametreler cagri yerindeki argumanlara baglanir)
bulunur ve yazim HEDEFI ifadesinin kaynak kumesi cozulur (atama/dongu/with/parametre/yerel
fonksiyon donusu uzerinden gecisli):
  · kumede gecici kok izi (mkdtemp, mkstemp, TemporaryDirectory, kopya_kok, gercek_dosya,
    kopyada_kos ...) varsa  -> IZOLE (sayilmaz),
  · yoksa ve kumede canli kok (ROOT, TOOLS, KOK, REPO, __file__) varsa -> CANLI YAZIM (sayilir),
  · ikisi de yoksa -> BELIRSIZ (bilgi satiri, sayilmaz).

HUKUM: SAYI = muafiyetsiz CANLI YAZIM yapan surucu sayisi; SAYI=0 -> rc 0.
  rc 1 = SAYI>0 ya da muafiyet kaydi bozuk (gerekcesiz / bayat).
  rc 2 = OLCULEMEDI (taranan dosya yok ya da ayristirilamayan dosya var) — fail-closed.

SINIR (beyanli): `atexit`/`signal` tabanli geri alma ve `finally` DISINDAKI yaz->geri-al
deseni sayilmaz; hedef kumesinde hem canli kok hem gecici iz varsa IZOLE sayilir.

KULLANIM
    python3 tools/mutant-canli-yazim-kapisi.py               # gercek repo
    python3 tools/mutant-canli-yazim-kapisi.py --kok <dizin> # fikstur dizini (test)
"""
import ast
import fnmatch
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
DESENLER = ("*mutasyon*.py", "*mutant*.py")
CANLI_KOKLER = frozenset(("ROOT", "TOOLS", "KOK", "REPO", "__file__"))
GECICI_IZLER = frozenset(("mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile",
                          "gettempdir", "kopya_kok", "gercek_dosya", "kopyada_kos"))
DERINLIK = 3

# Beyanli muafiyet: {"dosya.py": "gerekce"}. Gerekcesiz ya da artik ihlal etmeyen giris
# KIRMIZI'dir (bayat muafiyet sessizce yer tutmaz).
MUAFIYET = {
    "k3-cikti-kok-mutasyon.py":
        "7 Eki 2026 mutant-izole-2 taramasinin buldugu 5. surucu (spec'in 4 hedefi DISINDA): "
        "finally -> cleanup_build_outputs() WORKTREE yasal sayfalarini HEAD'den yeniden "
        "yazar + build ciktilarini siler. Onarim ayri dilim (mutant-izole-3); onarilinca "
        "bu kayit BAYAT olur ve kapi silinmesini ister.",
}

_OS_YAZIM = frozenset(("remove", "unlink", "rename", "replace", "renames", "utime",
                       "truncate", "rmdir", "removedirs"))
_SHUTIL_HEDEF1 = frozenset(("copy", "copy2", "copyfile", "copytree", "move", "copymode",
                            "copystat"))
_YOL_YAZIM = frozenset(("write_text", "write_bytes", "unlink", "touch", "rmdir"))


# ------------------------------------------------------------------ kapsam modeli
class Kapsam:
    """Bir modul ya da fonksiyon govdesi: ad -> [baglayan ifade], yerel fonksiyonlar."""

    def __init__(self, dugum, ust=None):
        self.dugum, self.ust = dugum, ust
        self.baglar, self.fonks, self.parametreler = {}, {}, set()
        if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = dugum.args
            for p in a.posonlyargs + a.args + a.kwonlyargs:
                self.parametreler.add(p.arg)
            for p in (a.vararg, a.kwarg):
                if p is not None:
                    self.parametreler.add(p.arg)
        govde = dugum.body if isinstance(dugum.body, list) else [dugum.body]
        for d in govde:
            self._topla(d)

    def _bagla(self, hedef, deger):
        for n in ast.walk(hedef):
            if isinstance(n, ast.Name):
                self.baglar.setdefault(n.id, []).append(deger)

    def _topla(self, d):
        # Ic ice fonksiyon govdesine INME (kendi kapsami var); yalniz adini kaydet.
        if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.fonks[d.name] = d
            return
        if isinstance(d, ast.ClassDef):
            return
        if isinstance(d, ast.Assign):
            for h in d.targets:
                self._bagla(h, d.value)
        elif isinstance(d, (ast.AnnAssign, ast.AugAssign)) and d.value is not None:
            self._bagla(d.target, d.value)
        elif isinstance(d, ast.NamedExpr):
            self._bagla(d.target, d.value)
        elif isinstance(d, (ast.For, ast.AsyncFor)):
            self._bagla(d.target, d.iter)
        elif isinstance(d, (ast.With, ast.AsyncWith)):
            for o in d.items:
                if o.optional_vars is not None:
                    self._bagla(o.optional_vars, o.context_expr)
        elif isinstance(d, ast.comprehension):
            self._bagla(d.target, d.iter)
        for c in ast.iter_child_nodes(d):
            if isinstance(c, (ast.stmt, ast.comprehension, ast.NamedExpr)) or \
               isinstance(c, ast.expr):
                self._topla(c)

    def fonk_bul(self, ad):
        k = self
        while k is not None:
            if ad in k.fonks:
                return k.fonks[ad], k
            k = k.ust
        return None, None

    def bag_bul(self, ad):
        k = self
        while k is not None:
            if ad in k.baglar or ad in k.parametreler:
                return k
            k = k.ust
        return None


class Cozucu:
    """Bir hedef ifadenin gecisli kaynak ATOM kumesi (Name id'leri + Attribute adlari)."""

    def __init__(self):
        self.kapsamlar = {}

    def kapsam(self, dugum, ust):
        anahtar = id(dugum)
        if anahtar not in self.kapsamlar:
            self.kapsamlar[anahtar] = Kapsam(dugum, ust)
        return self.kapsamlar[anahtar]

    def atomlar(self, ifade, kapsam, baglam, ziyaret=None):
        """`baglam` = {param_adi: (arguman_ifadesi, cagiran_kapsam, cagiran_baglam)}."""
        ziyaret = set() if ziyaret is None else ziyaret
        out = set()
        for n in ast.walk(ifade):
            if isinstance(n, ast.Attribute):
                out.add(n.attr)
            elif isinstance(n, ast.Name):
                out.add(n.id)
                out |= self._ad(n.id, kapsam, baglam, ziyaret)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                fonk, fk = kapsam.fonk_bul(n.func.id)
                if fonk is not None and ("ret", id(fonk)) not in ziyaret:
                    ziyaret.add(("ret", id(fonk)))
                    ic = self.kapsam(fonk, fk)
                    for r in ast.walk(fonk):
                        if isinstance(r, ast.Return) and r.value is not None:
                            out |= self.atomlar(r.value, ic, {}, ziyaret)
        return out

    def _ad(self, ad, kapsam, baglam, ziyaret):
        sahip = kapsam.bag_bul(ad)
        if sahip is None:
            return set()
        anahtar = (ad, id(sahip.dugum))
        if anahtar in ziyaret:
            return set()
        ziyaret.add(anahtar)
        out = set()
        if ad in sahip.parametreler and sahip is kapsam and ad in baglam:
            arg, ck, cb = baglam[ad]
            out |= self.atomlar(arg, ck, cb, ziyaret)
        for deger in sahip.baglar.get(ad, ()):
            out |= self.atomlar(deger, sahip, baglam if sahip is kapsam else {}, ziyaret)
        return out


# ------------------------------------------------------------------ yazim tespiti
def _sabit_dize(d):
    return d.value if isinstance(d, ast.Constant) and isinstance(d.value, str) else None


def yazim_hedefleri(cagri):
    """Cagri bir YAZIM ise hedef yol ifadelerini doner, degilse []."""
    f = cagri.func
    ad = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
    sahip = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else None
    if ad == "open" and sahip in (None, "io", "codecs"):
        kip = None
        if len(cagri.args) >= 2:
            kip = cagri.args[1]
        for k in cagri.keywords:
            if k.arg == "mode":
                kip = k.value
        if kip is None:
            return []
        dize = _sabit_dize(kip)
        if dize is not None and not any(c in dize for c in "wax+"):
            return []
        return cagri.args[:1]
    if sahip == "os" and ad in _OS_YAZIM:
        return list(cagri.args[:2])
    if sahip == "shutil" and ad == "rmtree":
        return cagri.args[:1]
    if sahip == "shutil" and ad in _SHUTIL_HEDEF1:
        return cagri.args[1:2]
    if isinstance(f, ast.Attribute) and ad in _YOL_YAZIM and sahip not in ("os", "shutil"):
        return [f.value]
    return []


def finally_ihlalleri(agac, cozucu):
    """[(satir, aciklama)] — finally govdesinden (dogrudan ya da yerel cagriyla) CANLI yazim."""
    ihlal, belirsiz = [], []
    modul = cozucu.kapsam(agac, None)

    def kapsam_zinciri(dugum, k):
        for c in ast.iter_child_nodes(dugum):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from kapsam_zinciri(c, cozucu.kapsam(c, k))
            else:
                if isinstance(c, ast.Try) and c.finalbody:
                    yield c, k
                yield from kapsam_zinciri(c, k)

    def tara(govde_dugumleri, k, baglam, yol, derinlik, gorulen):
        for st in govde_dugumleri:
            for n in ast.walk(st):
                if not isinstance(n, ast.Call):
                    continue
                for hedef in yazim_hedefleri(n):
                    atom = cozucu.atomlar(hedef, k, baglam)
                    etiket = "%s satir %d: %s" % (yol, n.lineno, ast.unparse(hedef)[:70])
                    if atom & GECICI_IZLER:
                        continue
                    if atom & CANLI_KOKLER:
                        ihlal.append(etiket)
                    else:
                        belirsiz.append(etiket)
                if isinstance(n.func, ast.Name) and derinlik < DERINLIK:
                    fonk, fk = k.fonk_bul(n.func.id)
                    if fonk is None or id(fonk) in gorulen:
                        continue
                    ic = cozucu.kapsam(fonk, fk)
                    yeni_baglam = {}
                    params = [p.arg for p in fonk.args.posonlyargs + fonk.args.args]
                    for p, a in zip(params, n.args):
                        yeni_baglam[p] = (a, k, baglam)
                    for kw in n.keywords:
                        if kw.arg:
                            yeni_baglam[kw.arg] = (kw.value, k, baglam)
                    tara(fonk.body, ic, yeni_baglam, "%s -> %s()" % (yol, fonk.name),
                         derinlik + 1, gorulen | {id(fonk)})

    for dene, k in kapsam_zinciri(agac, modul):
        tara(dene.finalbody, k, {}, "finally@%d" % dene.lineno, 0, frozenset())
    return ihlal, belirsiz


def suruculer(kok):
    adlar = sorted(a for a in os.listdir(kok)
                   if a.endswith(".py") and any(fnmatch.fnmatch(a, d) for d in DESENLER))
    return [a for a in adlar if a != os.path.basename(__file__)]


def main(argv):
    kok = TOOLS
    if "--kok" in argv:
        kok = os.path.abspath(argv[argv.index("--kok") + 1])
    adlar = suruculer(kok)
    # Muafiyet yalniz GERCEK repo icindir; fikstur dizininde (--kok) uygulanmaz.
    muafiyet = MUAFIYET if os.path.realpath(kok) == os.path.realpath(TOOLS) else {}
    print("MUTANT CANLI YAZIM KAPISI — %s" % kok)
    if not adlar:
        print("OLCULEMEDI: taranacak surucu YOK (desen %s)" % ", ".join(DESENLER))
        return 2
    sayi, bozuk, olculemedi, belirsiz_say = [], [], [], 0
    for ad in adlar:
        try:
            with open(os.path.join(kok, ad), encoding="utf-8") as f:
                agac = ast.parse(f.read(), filename=ad)
        except (SyntaxError, UnicodeDecodeError, ValueError) as e:
            olculemedi.append("%s: %s" % (ad, e))
            continue
        ihlal, belirsiz = finally_ihlalleri(agac, Cozucu())
        belirsiz_say += len(belirsiz)
        for b in belirsiz:
            print("  ·  BELIRSIZ %s :: %s" % (ad, b))
        if ad in muafiyet:
            if not str(muafiyet[ad]).strip():
                bozuk.append("%s: muafiyet GEREKCESIZ" % ad)
            elif not ihlal:
                bozuk.append("%s: BAYAT muafiyet (artik canli yazim yok) — kaydi sil" % ad)
            else:
                print("  ⚪ MUAF %s (%d yazim) — %s" % (ad, len(ihlal), muafiyet[ad]))
            continue
        if ihlal:
            sayi.append(ad)
            print("  🔴 %s" % ad)
            for i in ihlal:
                print("       %s" % i)
    for ad in sorted(set(muafiyet) - set(adlar)):
        bozuk.append("%s: muafiyet var ama dosya taranan kumede YOK — kaydi sil" % ad)
    for o in olculemedi:
        print("  ⚪ OLCULEMEDI %s" % o)
    for b in bozuk:
        print("  🔴 MUAFIYET %s" % b)
    print("-" * 70)
    print("TARANAN=%d  SAYI=%d  MUAF=%d  BELIRSIZ=%d  OLCULEMEDI=%d"
          % (len(adlar), len(sayi), len(muafiyet), belirsiz_say, len(olculemedi)))
    if olculemedi:
        print("SONUC: OLCULEMEDI ⚪")
        return 2
    if sayi or bozuk:
        print("SONUC: KIRMIZI ❌ — finally'de canli agaca yazan surucu var "
              "(kalip: mutasyon_kopya.kopyada_kos)")
        return 1
    print("SONUC: YESIL ✅ — hicbir surucu finally'de canli agaca yazmiyor")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
