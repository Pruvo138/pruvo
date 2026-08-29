#!/usr/bin/env python3
"""K304 BAYATLIK KOLU — mimar icra kapisinin kurulu hali kaynaktan geride mi?

MENZIL = CAGRI YERI ([[kapinin-menzili-cagri-yeridir]]). Iki cagri yeri vardir ve
IKISI DE ADIYLA yazilidir:

  1. `--ev <ev_koku>`  : O EVIN KENDI kanca zincirinden (PreToolUse) cagrilir. Kirmizi
     yanan ev, bayat kopyayi TASIYAN evdir — blokaj orada dogar, orada olur. Blast
     radius: yalnizca o ev.
  2. `--filo`          : KraL evinden, mimar/nobet raporu. Tum evleri basar.

OLCUM EKSENI: sha256 (metin). DOSYA BOYUTU HICBIR YERDE OLCUT DEGILDIR — brief'in
sarti; boyut esitligi icerik esitligi degildir.

FAIL-CLOSED: sinif cikarilamayan her hal (YOK / OKUNAMADI) KIRMIZIDIR. Sessiz gecis YOK.

rc: 0 = tum olculen evler yesil · 1 = en az bir ev kirmizi · 2 = kullanim hatasi.
Kanca modunda ('--kanca' ile birlikte) rc=1 yerine PreToolUse deny JSON'u basilir.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi_dagitim as KD  # noqa: E402


def satir(ad, kok, sinif, kurulu, beklenen):
    return (
        "EV=" + ad
        + " SINIF=" + sinif
        + " KURULU_SHA=" + (kurulu[:12] if kurulu else "-")
        + " BEKLENEN_SHA=" + (beklenen[:12] if beklenen else "-")
        + " YOL=" + kok
    )


def deny(neden):
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": neden,
        }
    }, ensure_ascii=False) + "\n")
    sys.exit(0)


def ev_kaydi(kok):
    hedef = os.path.normpath(kok)
    for ad, ev_kok, goreli, mod in KD.EVLER:
        if os.path.normpath(ev_kok) == hedef:
            return (ad, ev_kok, goreli, mod)
    return None


def main(argv):
    kanca = "--kanca" in argv
    argv = [a for a in argv if a != "--kanca"]

    if "--kaynak" in argv:
        # KAYNAK EVI KOLU — CI'da kosan tek anlamli olcum: govde VAR, DERLENIYOR ve
        # CAPA SOZLESMESI ayakta (iki capa TAM BIR KEZ). Capa kirilirsa bes evin shim'i
        # fail-closed DENY'a duser; bu adim o kirilmayi PUSH'tan once yakalar.
        kayitlar = KD.filo([e for e in KD.EVLER if e[3] == "kaynak"])
    elif "--filo" in argv:
        kayitlar = KD.filo()
    elif "--ev" in argv:
        i = argv.index("--ev")
        if i + 1 >= len(argv):
            sys.stderr.write("KULLANIM: --ev <ev_koku>\n")
            return 2
        kayit = ev_kaydi(argv[i + 1])
        if kayit is None:
            # Tanimsiz ev = fail-closed. Bilinmeyen bir kok icin 'yesil' demek,
            # olculmemise yesil demektir.
            mesaj = ("K304 BAYATLIK KOLU: '" + argv[i + 1] + "' tanimli ev degil "
                     "(tools/kapi_dagitim.py:EVLER). Fail-closed.")
            if kanca:
                deny(mesaj)
            sys.stderr.write(mesaj + "\n")
            return 1
        kayitlar = KD.filo([kayit])
    else:
        sys.stderr.write(__doc__ + "\n")
        return 2

    kirmizi = []
    for ad, kok, _goreli, _mod, sinif, kurulu, beklenen in kayitlar:
        print(satir(ad, kok, sinif, kurulu, beklenen))
        if sinif not in KD.YESIL_SINIFLAR:
            kirmizi.append((ad, kok, sinif))

    print("OLCULEN_EV=" + str(len(kayitlar))
          + " YESIL=" + str(len(kayitlar) - len(kirmizi))
          + " KIRMIZI=" + str(len(kirmizi)))
    try:
        print("KAYNAK_SHA=" + KD.sha256_dosya(KD.KAYNAK)[:12] + " KAYNAK=" + KD.KAYNAK)
    except Exception as hata:
        print("KAYNAK_SHA=OKUNAMADI (" + repr(hata) + ")")
        kirmizi.append(("KAYNAK", KD.KAYNAK, KD.OKUNAMADI))

    if not kirmizi:
        print("HUKUM=GUNCEL")
        return 0

    print("HUKUM=BAYAT ADLAR=" + ",".join(ad + ":" + sinif for ad, _k, sinif in kirmizi))
    if kanca:
        deny(
            "K304 BAYATLIK KOLU KIRMIZI — bu evdeki mimar icra kapisi tek kaynaktan "
            "GERIDE ya da hic kurulu degil: "
            + "; ".join(ad + " " + sinif for ad, _k, sinif in kirmizi)
            + ". Bu halde kapinin verdigi HER hukum olculemez. COZUM (bu evin mimari "
              "kendi evinde kosturur): python3 "
            + KD.KAYNAK_KOK + "/tools/kapi-dagitim-kur.py --ev <ev_koku> --uygula"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
