#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/n2b-dagitim-probu.py — DAGITILAN parti kapisini CALISTIRARAK olcer.

NEDEN VAR (20 Agu 2026, canli bloker):
`mimar-kapi-kur.py --parti-kapisi --uygula` her eve `<ev>/.claude/parti-kapisi.py`
kopyaladi ve "KURULDU" yazdi. Kopyanin YANINDA bagimliligi (T4 =
`parti-borc-kapisi.py`) YOKTU; kapi T4'u KARDES dosya olarak ariyordu,
bulamiyordu ve hatayi SESSIZCE yutuyordu -> her ev icin `N2B-OLCULEMEDI`
(fail-closed) -> bes evin ucuz kati (isci.sh) OLDU, sebebi hicbir satirda
gorunmedi. Dagitim raporu yine de yesil okunuyordu.

DERS: "dosya yerinde" ile "kapi kosuyor" AYNI SEY DEGILDIR
([[aracin-teshis-cumlesi-olcum-degil]]) ve bir kapinin menzili CAGRI YERIDIR
([[kapinin-menzili-cagri-yeridir]]) — repo kopyasinin yesil olmasi, EVLERE
DAGITILAN kopya hakkinda HICBIR SEY soylemez.

NE OLCER (her ev icin, SALT OKUMA — hicbir dosya yazilmaz):
  YUZEY-KANCA : kopyaya gercek bir PreToolUse JSON'u verir (mahsur kalan
                cagrinin birebir taklidi: `isci.sh ... <MUAF OLMAYAN ETIKET>`).
                Sinif: GECER | RED (gercek acik kalem) | OLCULEMEDI.
                🔴 OLCULEMEDI = T4 yuklenemiyor = O EVIN ISCI HATTI OLU.
  YUZEY-T4    : kopyayi `--t4-durum` ile kosar (bagimlilik teshisi; onarim
                oncesi surumde bu bayrak YOKTUR ve rc=2 doner — o da olcumdur).

Ev tablosu TEK KAYNAK: `tools/mimar-kapi-kur.py:CODEX_EVLER` (ikinci tablo YOK).

KABUL (calistirilabilir):
  python3 tools/n2b-dagitim-probu.py
    rc=0  <=> OLU_EV=0 VE SINIFLANAMAYAN_EV=0
    rc=1  <=> ikisinden biri >0 (hepsi SATIRLA yazilir — sessiz kirpma yok)
  Kova UCTUR: OLU (T4 kirik) · CANLI (GECER/RED) · SINIFLANAMAYAN (prob
  hukum okuyamadi). Ucuncu kova "canli"ya yazilirsa olcememe basari gibi
  okunur [[iki-kovali-siniflama-ucuncu-sinifi-yutar]].
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys

KURUCU_YOLU = "/Users/okan/dev/pruvo/tools/mimar-kapi-kur.py"
ISCI_SARMALAYICI = "/Users/okan/.claude/cron/isci.sh"
# 🔴 MUAF OLMAYAN etiket sart: muaf etiket (tamir/onarim/kabul/nobet/posta/
# devir) T4'e HIC ugramaz ve prob KORLESIR — yesil gorunur, hicbir sey olcmez.
VARSAYILAN_ETIKET = "d2-2"


def kurucu_yukle(yol):
    spec = importlib.util.spec_from_file_location("pruvo_kurucu", yol)
    if spec is None or spec.loader is None:
        raise ImportError("kurucu spec/loader COZULEMEDI: %s" % yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kanca_probu(kapi, kok, etiket):
    """Kopyayi gercek PreToolUse girdisiyle kosar. -> (sinif, rc, satir)."""
    girdi = {
        "tool_name": "Bash",
        "tool_input": {"command": "%s kimi %s /tmp/spec-prob.md %s"
                                  % (ISCI_SARMALAYICI, kok, etiket)},
        "cwd": kok,
    }
    try:
        p = subprocess.run([sys.executable, kapi, "--kanca"],
                           input=json.dumps(girdi), capture_output=True,
                           text=True, timeout=120)
    except Exception as e:
        return "PROB-COKTU", -1, "%s: %s" % (type(e).__name__, e)
    ham = (p.stdout or "").strip()
    if not ham:
        return "GECER", p.returncode, "(cikti yok = izin)"
    try:
        veri = json.loads(ham)
    except Exception:
        return "COZULEMEDI", p.returncode, ham[:240]
    ozel = veri.get("hookSpecificOutput") or {}
    if ozel.get("permissionDecision") != "deny":
        return "GECER", p.returncode, ham[:240]
    sebep = (ozel.get("permissionDecisionReason") or "").strip()
    ilk = sebep.splitlines()[0] if sebep else "(sebep YOK — sessiz yutma)"
    # 🔴 SINIFLAMA HUKUM JETONUNDAN OKUNUR, SERBEST METINDEN DEGIL.
    # Ilk surum `"OLCULEMEDI" in sebep` diyordu ve KraL'i OLU sandi: RED metni
    # acik kalemleri BASAR, K53'un govdesinde `OLCULEMEDI (rc=3)` geciyordu ->
    # defterdeki bir kelime kapinin HUKMUNU taklit etti (yanlis KIRMIZI).
    # [[aracin-teshis-cumlesi-olcum-degil]] · [[rc-hukmu-kapi-imzasini-ezer]]
    hukumler = [s for s in sebep.splitlines() if s.startswith("N2B HUKUM=")]
    if not hukumler:
        # 🔴 UCUNCU KOVA: siniflanamayan cagri "canli" SAYILMAZ — iki kovali
        # siniflama ucuncu sinifi yutar [[iki-kovali-siniflama-ucuncu-sinifi-yutar]].
        return "HUKUMSUZ", p.returncode, ilk[:300]
    sinif = "OLCULEMEDI" if "KOL=N2B-OLCULEMEDI" in hukumler[-1] else "RED"
    return sinif, p.returncode, "%s || %s" % (hukumler[-1][:200], ilk[:160])


def t4_probu(kapi):
    try:
        p = subprocess.run([sys.executable, kapi, "--t4-durum"],
                           capture_output=True, text=True, timeout=120)
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, e)
    ham = ((p.stdout or "") + (p.stderr or "")).strip().replace("\n", " ⏎ ")
    return p.returncode, (ham[:400] or "(cikti yok)")


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--etiket", default=VARSAYILAN_ETIKET,
                    help="prob etiketi (MUAF OLMAYAN olmali)")
    ap.add_argument("--kurucu", default=KURUCU_YOLU)
    args = ap.parse_args(argv)

    kurucu = kurucu_yukle(args.kurucu)
    print("N2B DAGITIM PROBU — dagitilan kopyalar CALISTIRILARAK olculur")
    print("ev tablosu (tek kaynak): %s" % args.kurucu)
    print("prob etiketi: %s" % args.etiket)
    print("")

    olu, canli, kapisiz, siniflanamayan = [], [], [], []
    for ad, kok, _goreli, mod in kurucu.CODEX_EVLER:
        goreli = ("tools/parti-kapisi.py" if mod == "kaynak"
                  else ".claude/parti-kapisi.py")
        kapi = os.path.join(kok, goreli)
        if not os.path.isdir(kok):
            print("%-7s %-34s EV-YOK" % (ad, kok))
            kapisiz.append(ad)
            continue
        if not os.path.isfile(kapi):
            print("%-7s %-34s KAPI-YOK (%s)" % (ad, kok, goreli))
            kapisiz.append(ad)
            continue
        sinif, rc_k, satir = kanca_probu(kapi, kok, args.etiket)
        rc_t, t4_satir = t4_probu(kapi)
        if sinif == "OLCULEMEDI":
            olu.append(ad)
        elif sinif in ("GECER", "RED"):
            canli.append(ad)
        else:                      # PROB-COKTU / COZULEMEDI / HUKUMSUZ
            siniflanamayan.append("%s(%s)" % (ad, sinif))
        print("%-7s %-34s %s (%d B)"
              % (ad, kok, goreli, os.path.getsize(kapi)))
        print("        YUZEY-KANCA sinif=%-11s rc=%d | %s"
              % (sinif, rc_k, satir))
        print("        YUZEY-T4    rc=%-3d | %s" % (rc_t, t4_satir))
        print("")

    print("-" * 92)
    print("OLU_EV=%d %s" % (len(olu), ",".join(olu) or "-"))
    print("CANLI_EV=%d %s" % (len(canli), ",".join(canli) or "-"))
    print("KAPISIZ_EV=%d %s" % (len(kapisiz), ",".join(kapisiz) or "-"))
    print("SINIFLANAMAYAN_EV=%d %s"
          % (len(siniflanamayan), ",".join(siniflanamayan) or "-"))
    return 0 if not (olu or siniflanamayan) else 1


if __name__ == "__main__":
    sys.exit(main())
