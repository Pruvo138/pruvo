#!/usr/bin/env python3
"""EV-SHIM KOLU — kabul + mutant (BaBa 24 Eki 11:0x yol (c), 11:3x one alindi).

OLCULEN VAKA (24 Eki 2026, OTeLLa 11:1x): `~/.claude/cron/isci.sh` motorun PATH'ini
`GH_SHIM : sabit PATH` diye kuruyordu (satir 3 sabit PATH + GH-TAVAN-SHIM satiri);
cagiran evin python3/node sarmalayicisi (test sayaci) isciye HIC ulasmiyordu.

`isci.sh` EV-SHIM kolu: `ISCI_EV_SHIM_DIZINI` yalniz mutlak · var · sahibi kullanici ·
g-w/o-w yok · ':' icermiyorsa `GH_SHIM : EV : sabit PATH` sirasiyla girer; aksi yok
sayilir + log `EV_SHIM=RED sebep=<...>`. GH shim DAIMA onde (gh tavani delinmez).
Degisken yoksa PATH dizgesi oncekiyle AYNI.

VAKALAR (izole CRON_KOKU + sahte claude + sahte gh; isci-gh-tavan-test fiksturu):
  E1  degisken yok -> PATH == GH_SHIM:<sabit PATH>, EV_SHIM satiri YOK
  E2  gecerli dizin -> PATH == GH_SHIM:EV:<sabit PATH>, ev python3 sayaci iz >= 1
  E3a goreli yol      -> yok sayilir + EV_SHIM=RED sebep=goreli
  E3b dizin yok       -> yok sayilir + EV_SHIM=RED sebep=dizin-yok
  E3c g+w dizin       -> yok sayilir + EV_SHIM=RED sebep=yazilabilir-g-o
  E3d ':' iceren yol  -> yok sayilir + EV_SHIM=RED sebep=iki-nokta
  E4  ev dizininde `gh` da var, 21 cagri -> 20'si GH shim uzerinden sahte gh'ye, 21. rc 1
      HAL=GH-TAVAN, ev `gh`'si HIC cagrilmaz
MUTANTLAR (izole kopya; OLMELI):
  MA ev eki PATH'ten silinir         -> E2 KIRMIZI (sayac iz 0)
  MB ev shim GH shim'in ONUNE alinir -> E4 KIRMIZI (gh tavani delinir)
  MC g-w/o-w kontrolu kaldirilir     -> E3c KIRMIZI

KOSUM:  python3 tools/isci-ev-shim-test.py
CIKTI:  son satir: EV-SHIM VAKA=<g>/7 MUTANT=<o>/3 (rc 0 yalniz 7/7 + 3/3)
CI'da canli hat yoktur -> ONKOSUL_YOK + rc 3 (isci-*-test ailesinin kanonu).
"""
import importlib.util
import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "isci_gh_tavan_test", os.path.join(_HERE, "isci-gh-tavan-test.py"))
GT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GT)

TMP_ONEK = "ev-shim-test-"
EK_SATIRI = '\nCLAUDE_ENV+=(PATH="$GH_SHIM_DIZINI:${EV_SHIM_EKI}$PATH")\n'
MA_CAPA = (EK_SATIRI, '\nCLAUDE_ENV+=(PATH="$GH_SHIM_DIZINI:$PATH")\n')
MB_CAPA = (EK_SATIRI, '\nCLAUDE_ENV+=(PATH="${EV_SHIM_EKI}$GH_SHIM_DIZINI:$PATH")\n')
MC_CAPA = ("    elif (( (8#$EV_SHIM_KIP & 8#022) != 0 )); then EV_SHIM_SEBEP=yazilabilir-g-o\n",
           "")

# Sahte motor: gh-tavan fiksturune ek olarak PATH uzerinden `python3` cagirir (evin
# sarmalayicisi boyle sayilir). GERCEK API CAGRISI YAPMAZ.
SAHTE_CLAUDE = r'''#!%(py)s
import json, os, subprocess, sys
iz = os.environ["SAHTE_IZ"]
with open(os.path.join(iz, "claude-cagrildi"), "a") as f:
    f.write("CAGRILDI\n")
with open(os.path.join(iz, "argv-ortam.json"), "w") as f:
    json.dump({"argv": sys.argv[1:], "ortam": dict(os.environ)}, f)
subprocess.run(["python3", "-c", "pass"])
sonuc = []
for i in range(int(os.environ.get("SAHTE_GH_SAYI", "0"))):
    p = subprocess.run(["gh", "api", "sahte/%%d" %% (i + 1)], capture_output=True, text=True)
    sonuc.append({"rc": p.returncode, "stderr": p.stderr})
with open(os.path.join(iz, "gh-sonuc.json"), "w") as f:
    json.dump(sonuc, f)
sys.exit(0)
'''

EV_PYTHON = '''#!/bin/sh
echo iz >> "%(sayac)s"
exec "%(py)s" "$@"
'''

EV_GH = '''#!/bin/sh
echo "$*" >> "%(iz)s"
exit 0
'''


def _sabit_path(govde):
    m = re.search(r'^export PATH="([^"]+)"', govde, re.M)
    return m.group(1) if m else None


def _ev_kur(tmp, ad, kip=0o700, gh=False):
    ev = os.path.join(tmp, "evshim-" + ad)
    os.makedirs(ev)
    sayac = os.path.join(tmp, "sayac-" + ad)
    GT._yaz(os.path.join(ev, "python3"), EV_PYTHON % {"sayac": sayac, "py": sys.executable},
            0o755)
    ev_gh_iz = os.path.join(tmp, "evgh-" + ad)
    if gh:
        GT._yaz(os.path.join(ev, "gh"), EV_GH % {"iz": ev_gh_iz}, 0o755)
    os.chmod(ev, kip)
    return ev, sayac, ev_gh_iz


def _satir_say(yol):
    if not os.path.exists(yol):
        return 0
    with open(yol, encoding="utf-8") as f:
        return len(f.read().splitlines())


def _path(r):
    return ((r["iz"] or {}).get("ortam") or {}).get("PATH", "")


def _gh_shim_mi(parca, kok):
    return parca.startswith(os.path.join(kok, ".isci-gh-shim."))


def e1(r, kok, sabit):
    hata = []
    p = _path(r).split(":", 1)
    if len(p) != 2 or not _gh_shim_mi(p[0], kok) or p[1] != sabit:
        hata.append("PATH=%s" % _path(r))
    if "EV_SHIM" in r["log"]:
        hata.append("EV_SHIM satiri basildi")
    return hata


def e2(r, kok, sabit, ev, sayac):
    hata = []
    p = _path(r).split(":", 2)
    if len(p) != 3 or not _gh_shim_mi(p[0], kok) or p[1] != ev or p[2] != sabit:
        hata.append("PATH=%s" % _path(r))
    if _satir_say(sayac) < 1:
        hata.append("ev sayac iz=0")
    if "EV_SHIM=RED" in r["log"]:
        hata.append("RED basildi")
    return hata


def e3(r, kok, sabit, sebep):
    hata = e1(dict(r, log=""), kok, sabit)
    if ("EV_SHIM=RED sebep=%s" % sebep) not in r["log"]:
        hata.append("RED sebep=%s satiri yok" % sebep)
    return hata


def e4(r, ev_gh_iz):
    hata = GT.v2(r)
    n = _satir_say(ev_gh_iz)
    if n:
        hata.append("ev gh cagrildi=%d" % n)
    return hata


def _vakalar(tmp, kok, ortak, sabit, kos):
    """[(ad, hata)] — her vaka kendi ev dizinini kurar."""
    out = []
    out.append(("E1", e1(kos("e1"), kok, sabit)))
    ev, sayac, _ = _ev_kur(tmp, "e2")
    out.append(("E2", e2(kos("e2", ek_ortam={"ISCI_EV_SHIM_DIZINI": ev}), kok, sabit, ev, sayac)))
    out.append(("E3a", e3(kos("e3a", ek_ortam={"ISCI_EV_SHIM_DIZINI": "evshim-goreli"}),
                          kok, sabit, "goreli")))
    out.append(("E3b", e3(kos("e3b", ek_ortam={"ISCI_EV_SHIM_DIZINI":
                                                os.path.join(tmp, "olmayan-dizin")}),
                          kok, sabit, "dizin-yok")))
    ev_gw, _, _ = _ev_kur(tmp, "e3c", kip=0o775)
    out.append(("E3c", e3(kos("e3c", ek_ortam={"ISCI_EV_SHIM_DIZINI": ev_gw}),
                          kok, sabit, "yazilabilir-g-o")))
    out.append(("E3d", e3(kos("e3d", ek_ortam={"ISCI_EV_SHIM_DIZINI": ev + ":/usr/bin"}),
                          kok, sabit, "iki-nokta")))
    ev4, _, ev_gh_iz = _ev_kur(tmp, "e4", gh=True)
    out.append(("E4", e4(kos("e4", gh_sayi=21, ek_ortam={"ISCI_EV_SHIM_DIZINI": ev4}),
                         ev_gh_iz)))
    return out


def _guvenli_sil(yol):
    gercek = os.path.realpath(yol)
    if not os.path.basename(gercek).startswith(TMP_ONEK):
        print("TEMIZLIK_ATLANDI: gecici olmayan yol " + gercek)
        return
    shutil.rmtree(gercek, ignore_errors=True)


def main():
    if not os.path.isfile(GT.GERCEK_ISCI) or not os.path.isfile(GT.GERCEK_SABITLER):
        print("ONKOSUL_YOK: canli isci hatti yok (" + GT.GERCEK_CRON + ")")
        print("EV-SHIM VAKA=OLCULEMEDI — bu kapi YEREL kosulur, CI'da DEGIL")
        return 3
    # --govde <yol>: canliya KURULMADAN once aday govde olculur (kurulum kosan isci 0 iken).
    govde_yolu = sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == "--govde" else GT.GERCEK_ISCI
    with open(govde_yolu, encoding="utf-8") as f:
        govde = f.read()
    sabit = _sabit_path(govde)
    tmp = tempfile.mkdtemp(prefix=TMP_ONEK)
    vaka_gecti = mutant_oldu = 0
    try:
        if sabit is None or govde.count(EK_SATIRI) != 1:
            print("VAKA=kurulum OLCULEN=EV_SHIM_CAPASI_TUTMADI SONUC=KALDI")
            return 1
        ortak = GT._ortak_kur(tmp)
        GT._yaz(os.path.join(ortak[1], "claude"), SAHTE_CLAUDE % {"py": sys.executable}, 0o755)

        def kur(alt, g):
            t = os.path.join(tmp, alt)
            k = GT._izole_kok_kur(t, g)
            return t, k, (lambda ad, **kw: GT._kos(t, k, ortak, ad, **kw))

        c_tmp, kok, kos = kur("canli", govde)
        if kok is None:
            print("VAKA=kurulum OLCULEN=SABITLER_CAPASI_TUTMADI SONUC=KALDI")
            return 1
        for ad, hata in _vakalar(c_tmp, kok, ortak, sabit, kos):
            GT._yaz_sonuc("VAKA", ad, hata)
            vaka_gecti += not hata

        for ad, capa, hedef in (("MA", MA_CAPA, "E2"), ("MB", MB_CAPA, "E4"),
                                ("MC", MC_CAPA, "E3c")):
            m_govde = GT._mutant(govde, capa)
            if m_govde is None:
                print("MUTANT=%s OLCULEN=CAPA_TUTMADI SONUC=YASADI" % ad)
                continue
            m_tmp, m_kok, m_kos = kur("mutant-" + ad, m_govde)
            sonuc = dict(_vakalar(m_tmp, m_kok, ortak, sabit, m_kos))
            hata = sonuc[hedef]
            print("MUTANT=%s HEDEF=%s OLCULEN=%s SONUC=%s" % (
                ad, hedef, "; ".join(hata) or "vaka-yesil", "OLDU" if hata else "YASADI"))
            mutant_oldu += bool(hata)
    finally:
        _guvenli_sil(tmp)
    print("EV-SHIM VAKA=%d/7 MUTANT=%d/3" % (vaka_gecti, mutant_oldu))
    return 0 if vaka_gecti == 7 and mutant_oldu == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
