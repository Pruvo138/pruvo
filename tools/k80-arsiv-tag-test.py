#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K80 menzil onarimi — uzakta ZATEN erisilebilir commit'i gosteren YENI ref kapsam disidir.

OLCULEN KUSUR (26 Eyl 2026, dal triyaji)
────────────────────────────────────────
ESKIMIS `koru/faz3-edge-arama` dalinin ucuna (`27f0a205`, 16 Tem — K80'den ONCE origin'e
gitmis) `arsiv/dal/...` tag'i itilirken pre-push K80 kolu YENI ref satirinda
`(ucun ebeveyni, uc)` araligini kurdu, o commit'in `deploy.yml` `mkdir` adimini "yeni CI
adimi" saydi ve `YENI CI ADIMI OLCULEMEDI` ile push'u her denemede durdurdu. Tag yeni
commit TASIMIYORDU. Sonuc: arsiv tag'i yok -> dal silinemez
([[arsiv-tagi-k80-pre-push-eski-commiti-yeni-ci-adimi-sayar]]).

BU BATARYA NE OLCER
───────────────────
P1 POZITIF   : uzakta dal olarak duran commit'e HAFIF tag -> aralik YOK (kapsam disi).
P2 POZITIF   : ayni commit'e ANOTASYONLU tag (sha = tag nesnesi) -> aralik YOK.
P3 UCTAN UCA : P1 girdisi `yeni_ci_adimi_kontrol`den gecer -> bulgu 0, OLCULEMEDI yok.
               (Kusurun uretildigi sekil: eski commit zincir-ici isine `mkdir` ekler.)
N1 NEGATIF   : itilmemis YENI commit'e yeni dal -> aralik KURULUR (yeni icerik olculur).
N2 NEGATIF   : karisik push (P1 tag + N1 dal) -> YALNIZ N1 araligi kalir.
N3 NEGATIF   : hic uzak-izleme ref'i YOK -> muafiyet VERILMEZ, aralik kurulur.
N4 NEGATIF   : cozulmeyen sha -> OLCULEMEDI (fail-closed devrilmez).
N5 NEGATIF   : itilmemis commit'e TAG (ad muafiyeti YOK) -> aralik kurulur ve P3
               sekli (zincir ici `mkdir`) hala OLCULEMEDI bulgusu uretir.
M1 MUTANT    : kopyada `_k80_uzakta_erisilebilir` -> `return False` (= onarim oncesi main
               davranisi). Beklenen: P1/P2/P3 + N2 (tag araligi geri gelir) KIRMIZI **ve**
               N1/N3/N4/N5 DEGISMEZ (kirmizinin sebebi hedef kola atfedilir).
M2 MUTANT    : kopyada -> `return True` (asiri genis muafiyet). Beklenen: N1/N2/N5 KIRMIZI.

HERMETIK: gecici bir "uzak" (bare) + gecici calisma deposu kurulur, URETIM dosyasi oraya
KOPYALANIR ve importlib ile ITHAL edilir (ikiz tanim YOK). Mutantlar yalniz o KOPYAYA
uygulanir. Canli repoya, canli git'e, aga SIFIR dokunus; ureten temizler.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
URETIM = os.path.join(TOOLS, "is-akisi-kapisi.py")
SUZGEC = os.path.join(TOOLS, "icra-suzgeci.py")
SIFIR = "0" * 40

# Mutasyon capasi: uretim govdesindeki TEK satir. Capa bulunamazsa mutant KURULAMAZ ->
# batarya KIRMIZI (sessizce "mutant yasadi/oldu" demez).
CAPA = 'return _k80_git(["rev-list", "-n", "1", commit, "--not", "--remotes"]).strip() == ""'


def akis(serit_run):
    return (
        "name: deploy\n"
        "on: [push]\n"
        "jobs:\n"
        "  serit:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: python3 tools/serit-test.py\n" + serit_run +
        "  deploy:\n"
        "    needs: [serit]\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: python3 tools/yayin.py\n")


def _git(kok, *a):
    r = subprocess.run(["git", "-C", kok] + list(a), capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError("git %s -> %s" % (" ".join(a), r.stderr.strip()))
    return r.stdout.strip()


def _commit(kok, serit_run, mesaj):
    with open(os.path.join(kok, ".github", "workflows", "deploy.yml"), "w",
              encoding="utf-8") as f:
        f.write(akis(serit_run))
    _git(kok, "add", "-A")
    _git(kok, "commit", "-q", "-m", mesaj)
    return _git(kok, "rev-parse", "HEAD")


class Sahne:
    """uzak(bare) + depo: main(C1) itildi, eski dal (C2, zincir ici `mkdir`) itildi,
    yeni dal (C3) ITILMEDI."""

    def __init__(self, uzak_kur=True, mutant=None):
        self.kok_ust = tempfile.mkdtemp(prefix="pruvo-k80-tag-")
        self.kok = os.path.join(self.kok_ust, "depo")
        uzak = os.path.join(self.kok_ust, "uzak.git")
        os.makedirs(os.path.join(self.kok, "tools"))
        os.makedirs(os.path.join(self.kok, ".github", "workflows"))
        with open(URETIM, encoding="utf-8") as f:
            govde = f.read()
        if mutant is not None:
            if govde.count(CAPA) != 1:
                raise RuntimeError("mutant capasi uretimde tekil degil (%d)" % govde.count(CAPA))
            govde = govde.replace(CAPA, mutant)
        with open(os.path.join(self.kok, "tools", "is-akisi-kapisi.py"), "w",
                  encoding="utf-8") as f:
            f.write(govde)
        shutil.copy2(SUZGEC, os.path.join(self.kok, "tools", "icra-suzgeci.py"))
        for ad in ("serit-test.py", "yayin.py"):
            with open(os.path.join(self.kok, "tools", ad), "w", encoding="utf-8") as f:
                f.write("import sys\nsys.exit(0)\n")
        _git(self.kok, "init", "-q", "-b", "main")
        _git(self.kok, "config", "user.email", "k80tag@pruvo.local")
        _git(self.kok, "config", "user.name", "K80TAG")
        _git(self.kok, "config", "commit.gpgsign", "false")
        _git(self.kok, "config", "tag.gpgsign", "false")
        self.c1 = _commit(self.kok, "", "C1")
        _git(self.kok, "switch", "-q", "-c", "eski")
        # Kusurun URETILDIGI sekil: zincir ici isine olculemeyen `mkdir` adimi.
        self.c2 = _commit(self.kok, "      - run: mkdir -p cikti\n", "C2")
        _git(self.kok, "tag", "hafif-arsiv", self.c2)
        _git(self.kok, "tag", "-a", "-m", "arsiv", "anot-arsiv", self.c2)
        self.anot = _git(self.kok, "rev-parse", "anot-arsiv")
        _git(self.kok, "switch", "-q", "main")
        _git(self.kok, "switch", "-q", "-c", "yeni")
        self.c3 = _commit(self.kok, "      - run: mkdir -p yeni\n", "C3")
        _git(self.kok, "switch", "-q", "main")
        if uzak_kur:
            _git(self.kok_ust, "init", "-q", "--bare", uzak)
            _git(self.kok, "remote", "add", "origin", uzak)
            _git(self.kok, "push", "-q", "--no-verify", "origin", "main", "eski")
            _git(self.kok, "fetch", "-q", "origin")
        self.mod = self._ithal()

    _SAYAC = [0]

    def _ithal(self):
        Sahne._SAYAC[0] += 1
        ad = "k80_tag_kapi_%d" % Sahne._SAYAC[0]
        spec = importlib.util.spec_from_file_location(
            ad, os.path.join(self.kok, "tools", "is-akisi-kapisi.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[ad] = mod
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.modules.pop(ad, None)
        if os.path.realpath(mod.ROOT) != os.path.realpath(self.kok):
            raise RuntimeError("ROOT gecici depoya cozulmedi")
        return mod

    def araliklar(self, satirlar):
        class A:
            base = hedef = None
            pre_push = True
        eski = sys.stdin
        sys.stdin = io.StringIO("".join(s + "\n" for s in satirlar))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return self.mod._k80_araliklar(A())
        finally:
            sys.stdin = eski

    def kontrol(self, satirlar):
        class A:
            base = hedef = None
            pre_push = True
        eski = sys.stdin
        sys.stdin = io.StringIO("".join(s + "\n" for s in satirlar))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return self.mod.yeni_ci_adimi_kontrol(A())
        finally:
            sys.stdin = eski

    def temizle(self):
        shutil.rmtree(self.kok_ust, ignore_errors=True)


def satir(ref, sha):
    return "%s %s %s %s" % (ref, sha, ref, SIFIR)


def vakalar(mutant=None):
    """-> {vaka: (gecti_mi, aciklama)}"""
    s = Sahne(mutant=mutant)
    s0 = None
    sonuc = {}
    try:
        tag = satir("refs/tags/hafif-arsiv", s.c2)
        anot = satir("refs/tags/anot-arsiv", s.anot)
        yeni = satir("refs/heads/yeni", s.c3)
        yeni_tag = satir("refs/tags/yeni-arsiv", s.c3)

        r = s.araliklar([tag])
        sonuc["P1"] = (r == [], "hafif tag -> %r" % r)
        r = s.araliklar([anot])
        sonuc["P2"] = (r == [], "anotasyonlu tag -> %r" % r)
        try:
            b, y, k = s.kontrol([tag])
            sonuc["P3"] = (b == [] and y == 0, "uctan uca bulgu=%d yeni=%d" % (len(b), y))
        except s.mod.Olculemedi as e:
            sonuc["P3"] = (False, "uctan uca OLCULEMEDI: %s" % e)

        c3_ebeveyn = _git(s.kok, "rev-parse", s.c3 + "^")
        r = s.araliklar([yeni])
        sonuc["N1"] = (r == [(c3_ebeveyn, s.c3)], "itilmemis dal -> %r" % r)
        r = s.araliklar([tag, yeni])
        sonuc["N2"] = (r == [(c3_ebeveyn, s.c3)], "karisik push -> %r" % r)
        try:
            b, y, k = s.kontrol([yeni_tag])
            olculemedi = any("OLCULEMEDI" in x for x in b)
            sonuc["N5"] = (y >= 1 and olculemedi,
                           "itilmemis commit'e tag: yeni=%d OLCULEMEDI_bulgu=%s" % (y, olculemedi))
        except s.mod.Olculemedi as e:
            sonuc["N5"] = (True, "itilmemis commit'e tag OLCULEMEDI (fail-closed): %s" % e)
        try:
            s.araliklar([satir("refs/tags/yok", "f" * 40)])
            sonuc["N4"] = (False, "cozulmeyen sha OLCULEMEDI olmadi")
        except s.mod.Olculemedi:
            sonuc["N4"] = (True, "cozulmeyen sha -> OLCULEMEDI")

        s0 = Sahne(uzak_kur=False, mutant=mutant)
        c2_ebeveyn = _git(s0.kok, "rev-parse", s0.c2 + "^")
        r = s0.araliklar([satir("refs/tags/hafif-arsiv", s0.c2)])
        sonuc["N3"] = (r == [(c2_ebeveyn, s0.c2)], "uzak-izleme ref'i yok -> %r" % r)
    finally:
        s.temizle()
        if s0 is not None:
            s0.temizle()
    return sonuc


def main():
    hata = 0
    print("K80 ARSIV-TAG MENZILI — uzakta zaten erisilebilir commit kapsam disi (hermetik)")
    print("-" * 78)
    temel = vakalar()
    for ad in sorted(temel):
        gecti, acik = temel[ad]
        print("%s %-3s %s" % ("✅" if gecti else "❌", ad, acik))
        hata += 0 if gecti else 1

    # M1: onarim oncesi main davranisi. Hedef kol P* KIRMIZI, yan eksen N* DEGISMEZ.
    m1 = vakalar(mutant="return False")
    m1_hedef = all(not m1[v][0] for v in ("P1", "P2", "P3", "N2"))
    m1_yan = all(m1[v][0] for v in ("N1", "N3", "N4", "N5"))
    print("%s M1 mutant (return False = onarim oncesi): P1/P2/P3/N2 KIRMIZI=%s · N1/N3/N4/N5 YESIL=%s"
          % ("✅" if m1_hedef and m1_yan else "❌", m1_hedef, m1_yan))
    for v in sorted(m1):
        if (v in ("P1", "P2", "P3", "N2")) == m1[v][0]:
            print("     M1 sapma %s: %s" % (v, m1[v][1]))
    hata += 0 if (m1_hedef and m1_yan) else 1

    # M2: asiri genis muafiyet. Negatif nobet (N1/N2/N5) KIRMIZI yanmali.
    m2 = vakalar(mutant="return True")
    m2_hedef = all(not m2[v][0] for v in ("N1", "N2", "N5"))
    print("%s M2 mutant (return True = asiri muafiyet): N1/N2/N5 KIRMIZI=%s"
          % ("✅" if m2_hedef else "❌", m2_hedef))
    hata += 0 if m2_hedef else 1

    print("-" * 78)
    print("VAKA=%d DUSEN=%d" % (len(temel) + 2, hata))
    if hata:
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅ — zaten itilmis commit'e ref kapsam disi · yeni icerik hala olculuyor "
          "· iki yonlu mutantla kanitli")
    return 0


if __name__ == "__main__":
    sys.exit(main())
