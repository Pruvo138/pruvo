#!/usr/bin/env python3
"""K304 — bir EVE mimar icra kapisi SHIM'ini kurar (kopya DEGIL, shim).

🔴 BU ARACI HER EVIN KENDI MIMARI KENDI EVINDE KOSTURUR. KraL kardes depoya YAZMAZ;
bu betik KraL'da yasar cunku govde orada yasar, ama `--uygula` hedefi HER ZAMAN
komut satirinda ADIYLA verilen evdir ve o evin mimarinin karari altindadir.

Desen mevcut kurucularla AYNI: DAR + IDEMPOTENT + YEDEKLI + FAIL-CLOSED.
  * once <dosya>.yedek-<zaman> alinir (EV ICINDE, /tmp'de degil),
  * shim yazilir, DERLENIR, sonra UC CANLI FIKSTUR gercek alt-surecle kosturulur:
      F1 ALLOW  : Bash 'ls'                       -> izin (stdout BOS)
      F2 DENY   : Bash 'python3 -c "1"'           -> deny (satir-ici kod kurali)
      F3 EV EKSENI: mcp__Claude_Browser__navigate -> TARAYICI_ACIK_EVLER'e gore
                    deny/izin. Bu fikstur SHIM'IN DOGRU EVE HOMELENDIGINI olcer:
                    ayni govde, ev degisince BASKA hukum verir.
  * herhangi biri tutmazsa O EV DERHAL YEDEKTEN GERI ALINIR (yanlis-pozitif bir evin
    TUM oturumunu durdurur),
  * kardes repoya commit YOK.

KULLANIM:
    python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kur.py --ev /Users/okan/dev/pruvo-hasat
    python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kur.py --ev /Users/okan/dev/pruvo-hasat --uygula

Kurulumdan sonra olcum (ayni evde, rc=0 beklenir):
    python3 /Users/okan/dev/pruvo/tools/kapi-dagitim-kapisi.py --ev /Users/okan/dev/pruvo-hasat
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi_dagitim as KD  # noqa: E402

def tarayici_acik_evler(kaynak_metin):
    """F3'un beklentisi KAYNAKTAN TURETILIR — ikinci bir liste TUTULMAZ
    ([[ikiz-tanim-sessiz-ayrisma]]). Ayristirilamazsa None doner (fail-closed:
    fikstur 'OLCULEMEDI' sayilir ve kurulum GERI ALINIR)."""
    for satir_ in kaynak_metin.splitlines():
        if satir_.startswith("TARAYICI_ACIK_EVLER"):
            ic = satir_.split("=", 1)[1]
            return tuple(p.strip().strip('"').strip("'")
                         for p in ic.strip().strip("()").split(",") if p.strip())
    return None


def _kos(yol, girdi):
    p = subprocess.run(
        [sys.executable, yol],
        input=json.dumps(girdi),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return p.stdout.strip(), p.stderr.strip(), p.returncode


def _deny_mi(stdout):
    if not stdout:
        return False
    try:
        veri = json.loads(stdout)
    except Exception:
        return False
    return (veri.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny"


def fikstur_kos(yol, ev_koku, acik_evler):
    """UC fikstur. Doner: (gecti_mi, [satir, ...])."""
    ev_adi_dizin = os.path.basename(os.path.normpath(ev_koku))
    izler = []
    tamam = True
    if acik_evler is None:
        return (False, ["F3_EV_EKSENI OLCULEMEDI — kaynaktan TARAYICI_ACIK_EVLER "
                        "ayristirilamadi; fail-closed."])

    so, se, rc = _kos(yol, {"tool_name": "Bash",
                            "tool_input": {"command": "ls"},
                            "cwd": ev_koku})
    ok = (not _deny_mi(so)) and rc == 0
    izler.append("F1_ALLOW(ls) beklenen=izin gozlenen=" +
                 ("deny" if _deny_mi(so) else "izin") + " rc=" + str(rc) +
                 " iz=" + (se.splitlines()[-1] if se else "-"))
    tamam = tamam and ok

    so, se, rc = _kos(yol, {"tool_name": "Bash",
                            "tool_input": {"command": 'python3 -c "1"'},
                            "cwd": ev_koku})
    ok = _deny_mi(so) and rc == 0
    izler.append("F2_DENY(satir-ici) beklenen=deny gozlenen=" +
                 ("deny" if _deny_mi(so) else "izin") + " rc=" + str(rc))
    tamam = tamam and ok

    beklenen_deny = ev_adi_dizin not in acik_evler
    so, se, rc = _kos(yol, {"tool_name": "mcp__Claude_Browser__navigate",
                            "tool_input": {"url": "https://pruvo3d.com"},
                            "cwd": ev_koku})
    gozlenen_deny = _deny_mi(so)
    ok = (gozlenen_deny == beklenen_deny) and rc == 0
    izler.append("F3_EV_EKSENI(mcp tarayici) ev=" + ev_adi_dizin +
                 " beklenen=" + ("deny" if beklenen_deny else "izin") +
                 " gozlenen=" + ("deny" if gozlenen_deny else "izin") +
                 " rc=" + str(rc))
    tamam = tamam and ok

    return tamam, izler


def main(argv):
    if "--ev" not in argv:
        sys.stderr.write(__doc__ + "\n")
        return 2
    i = argv.index("--ev")
    if i + 1 >= len(argv):
        sys.stderr.write("KULLANIM: --ev <ev_koku> [--uygula]\n")
        return 2
    hedef = os.path.normpath(argv[i + 1])
    uygula = "--uygula" in argv

    kayit = None
    for ad, kok, goreli, mod in KD.EVLER:
        if os.path.normpath(kok) == hedef:
            kayit = (ad, kok, goreli, mod)
    if kayit is None:
        sys.stderr.write("TANIMSIZ EV: " + hedef + " (tools/kapi_dagitim.py:EVLER)\n")
        return 2
    ad, kok, goreli, mod = kayit
    if mod == "kaynak":
        print("EV=" + ad + " MOD=kaynak — govdenin kendi evi, shim KURULMAZ.")
        return 0

    yol = KD.kurulu_yol(kok, goreli)
    metin = KD.shim_metni(ad, kok)
    beklenen = KD.sha256_metin(metin)
    sinif, kurulu, _b = KD.siniflandir(ad, kok, goreli, mod)

    print("EV=" + ad + " YOL=" + yol)
    print("MEVCUT_SINIF=" + sinif + " KURULU_SHA=" + (kurulu[:12] if kurulu else "-"))
    print("BEKLENEN_SHA=" + beklenen[:12] + " BAYT=" + str(len(metin.encode("utf-8"))))

    kaynak_metin = KD.kaynak_metni()
    c1, c2 = KD.capa_sayilari(kaynak_metin)
    print("KAYNAK_CAPA repo=" + str(c1) + " worktree=" + str(c2) +
          " KAYNAK_SHA=" + KD.sha256_metin(kaynak_metin)[:12])
    if (c1, c2) != (1, 1):
        print("HUKUM=KURULMAZ (kaynak capalari TAM BIR KEZ degil — fail-closed)")
        return 1

    if sinif == KD.GUNCEL:
        print("HUKUM=ZATEN_GUNCEL (idempotent, dokunulmadi)")
        return 0
    if not uygula:
        print("HUKUM=KURU (uygulamak icin --uygula ekle)")
        return 0

    yedek = None
    if os.path.exists(yol):
        yedek = yol + ".yedek-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(yol, yedek)
        print("YEDEK=" + yedek)

    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)

    try:
        compile(metin, yol, "exec")
        derlendi = True
    except Exception as hata:
        derlendi = False
        print("DERLEME=DUSTU " + repr(hata))

    gecti, izler = (False, ["DERLEME dustu — fikstur kosulmadi"])
    if derlendi:
        gecti, izler = fikstur_kos(yol, kok, tarayici_acik_evler(kaynak_metin))
    for iz in izler:
        print("  " + iz)

    if not (derlendi and gecti):
        if yedek:
            shutil.copy2(yedek, yol)
            print("HUKUM=GERI_ALINDI (yedekten) — ev DEGISMEDI")
        else:
            os.remove(yol)
            print("HUKUM=GERI_ALINDI (dosya kaldirildi) — ev DEGISMEDI")
        return 1

    # GIT IZLEME DURUMU — SALT BILGI, hicbir sey degistirilmez. Bazi evlerde bu dosya
    # 'skip-worktree' ile izleniyor, bazilarinda .git/info/exclude ile disarida; evin
    # mimari kendi deposunda ne yapacagina kendisi karar verir.
    try:
        p = subprocess.run(["git", "-C", kok, "ls-files", "-v", "--", goreli],
                           capture_output=True, text=True, timeout=30)
        satir_ = (p.stdout or "").strip()
        print("GIT_IZLEME=" + (satir_ if satir_ else "izlenmiyor"))
    except Exception as hata:
        print("GIT_IZLEME=OLCULEMEDI " + repr(hata))

    sinif2, kurulu2, _b2 = KD.siniflandir(ad, kok, goreli, mod)
    print("SONRA_SINIF=" + sinif2 + " KURULU_SHA=" + (kurulu2[:12] if kurulu2 else "-"))
    print("HUKUM=KURULDU FIKSTUR=3/3")
    return 0 if sinif2 == KD.GUNCEL else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
