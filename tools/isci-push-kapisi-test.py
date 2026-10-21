#!/usr/bin/env python3
"""ISCI PUSH KAPISI — kabul + kablo + mutant (21 Eki 2026, BaBa 14:1x (2)).

OLCULEN VAKA: bir isci spec'teki "main'e push etme" METIN yasagini deldi (hasat
`c2c82514`). Kapi: tools/isci-push-kapisi.sh, tools/kancalar/pre-push 0- bolumunden cagrilir.

VAKALAR (betik ORTAM-MINIMAL kosulur; gercek push/git YOK):
  V1 PRUVO_ISCI_KOSUMU bos                                  -> rc 0 (isci degil)
  V2 isci (minimax-m3, etiket tamir), ISCI_PUSH_IZNI yok    -> rc 1 + "PUSH DURDURULDU"
  V3 isci, ISCI_PUSH_IZNI == etiket (tamir)                 -> rc 0 + "ISCI_PUSH_KAPISI=GECTI"
  V4 isci, ISCI_PUSH_IZNI baska etiket                      -> rc 1 (izin etikete bagli)
  V5 isci, izin dolu ama PRUVO_ISCI_ETIKET bos              -> rc 1
  K1 KABLO: pre-push betigi `|| exit 1` ile cagirir, 0) tazelik bolumunden SONRA,
     0a) bolumunden ONCE; betik yoksa isci kosumunda fail-closed kolu var
MUTANTLAR (gecici kopya; mutant OLMELI = ilgili vaka KIRMIZI):
  M1 betikte son `exit 1` -> `exit 0` (red kolu olur)        -> V2 KIRMIZI
  M2 pre-push'tan betik cagrisi silinir                       -> K1 KIRMIZI

CIKTI: VAKA=<ad> SONUC=GECTI|KALDI · MUTANT=<ad> SONUC=OLDU|YASADI
son satir: ISCI-PUSH-KAPISI VAKA=<g>/6 MUTANT=<o>/2 (rc 0 yalniz 6/6 + 2/2)
"""
import os
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BETIK = os.path.join(KOK, "tools", "isci-push-kapisi.sh")
KANCA = os.path.join(KOK, "tools", "kancalar", "pre-push")
CAGRI = 'sh "$pruvo_pp_kok/tools/isci-push-kapisi.sh" </dev/null || exit 1'
FAIL_CLOSED = 'elif [ -n "${PRUVO_ISCI_KOSUMU:-}" ]; then'
BOLUM_0 = "# --- 0) KOPYA TAZELIGI"
BOLUM_0A = "# --- 0a) SENTETIK GIT SIZINTI KAPISI"


def kos(betik, **ortam):
    env = {"PATH": "/usr/bin:/bin"}
    env.update({k: v for k, v in ortam.items() if v is not None})
    p = subprocess.run(["sh", betik], capture_output=True, text=True, env=env,
                       stdin=subprocess.DEVNULL, timeout=30)
    return p.returncode, p.stderr


def vakalar(betik):
    isci = dict(PRUVO_ISCI_KOSUMU="minimax-m3", PRUVO_ISCI_ETIKET="tamir")
    sonuc = []
    rc, err = kos(betik)
    sonuc.append(("V1", [] if rc == 0 else ["rc=%d" % rc]))
    rc, err = kos(betik, **isci)
    sonuc.append(("V2", [] if rc == 1 and "PUSH DURDURULDU" in err else ["rc=%d" % rc]))
    rc, err = kos(betik, ISCI_PUSH_IZNI="tamir", **isci)
    sonuc.append(("V3", [] if rc == 0 and "ISCI_PUSH_KAPISI=GECTI" in err else ["rc=%d" % rc]))
    rc, err = kos(betik, ISCI_PUSH_IZNI="baska-is", **isci)
    sonuc.append(("V4", [] if rc == 1 else ["rc=%d" % rc]))
    rc, err = kos(betik, PRUVO_ISCI_KOSUMU="minimax-m3", ISCI_PUSH_IZNI="tamir")
    sonuc.append(("V5", [] if rc == 1 else ["rc=%d" % rc]))
    return sonuc


def kablo(metin):
    hata = []
    i0, i0a, ic = metin.find(BOLUM_0), metin.find(BOLUM_0A), metin.find(CAGRI)
    if ic < 0:
        hata.append("cagri satiri YOK")
    elif not (0 <= i0 < ic < i0a):
        hata.append("cagri sirasi yanlis (0=%d cagri=%d 0a=%d)" % (i0, ic, i0a))
    if FAIL_CLOSED not in metin:
        hata.append("betik-yok fail-closed kolu YOK")
    return hata


def main():
    for yol in (BETIK, KANCA):
        if not os.path.isfile(yol):
            print("VAKA=kurulum OLCULEN=%s YOK SONUC=KALDI" % yol)
            print("ISCI-PUSH-KAPISI VAKA=0/6 MUTANT=0/2")
            return 1
    with open(BETIK, encoding="utf-8") as f:
        betik_metni = f.read()
    with open(KANCA, encoding="utf-8") as f:
        kanca_metni = f.read()

    gecti = 0
    sonuc = vakalar(BETIK) + [("K1", kablo(kanca_metni))]
    for ad, hata in sonuc:
        print("VAKA=%s OLCULEN=%s SONUC=%s" % (ad, "; ".join(hata) or "beklenen",
                                              "KALDI" if hata else "GECTI"))
        gecti += not hata

    oldu = 0
    with tempfile.TemporaryDirectory(prefix="isci-push-kapisi-test-") as tmp:
        son = betik_metni.rfind("exit 1")
        m1 = os.path.join(tmp, "m1.sh")
        with open(m1, "w", encoding="utf-8") as f:
            f.write(betik_metni[:son] + "exit 0" + betik_metni[son + len("exit 1"):])
        v2 = dict(vakalar(m1))["V2"]
        print("MUTANT=M1 OLCULEN=%s SONUC=%s" % ("; ".join(v2) or "vaka-yesil",
                                                "OLDU" if v2 else "YASADI"))
        oldu += bool(v2)
    k1 = kablo(kanca_metni.replace(CAGRI, ":", 1))
    print("MUTANT=M2 OLCULEN=%s SONUC=%s" % ("; ".join(k1) or "vaka-yesil",
                                            "OLDU" if k1 else "YASADI"))
    oldu += bool(k1)

    print("ISCI-PUSH-KAPISI VAKA=%d/6 MUTANT=%d/2" % (gecti, oldu))
    return 0 if gecti == 6 and oldu == 2 else 1


if __name__ == "__main__":
    sys.exit(main())
