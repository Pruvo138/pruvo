#!/usr/bin/env python3
"""MOTOR KAPISI — kabul + mutant (BaBa 12 Eki 20:5x hukmu, guvenlik).

OLCULEN VAKA (12 Eki 2026): pruvo'da birincil (m3) 15 / Claude 20 kosum;
Claude'un 20/20'si `onarim-*` etiketliydi — pahali kat mekanik onarima
akiyordu, m3-once kurali yalniz yazili bir istekti.

`~/.claude/cron/isci.sh` MOTOR-KAPISI kolu kazandi (motor secimi + karantina
SONRA, motor sureci ONCE): Claude ailesi motorlar (`claude`, `claude-api`)
yalniz etiket `MOTOR_KAPISI_BEYAZ_LISTE` onekiyle basliyorsa GECER; aksi
`HAL=MOTOR-RED rc=1`, motor CAGRILMAZ. TEK istisna m3-once: ayni etiketle son
24 sa icinde bir m3 kosumu BITIS rc!=0 ya da hal=BOS ile dustuyse GECER
(`sebep=m3-dustu`; BASLANGIC<->BITIS `pid=` ile eslesir). m3 ETKILENMEZ.
Beyaz liste isci.sh'te TEK satirdir; bu test o satiri OKUR (kopya TUTMAZ).

VAKALAR (her biri izole CRON_KOKU + sahte claude/m3 ikilisi; GERCEK motor YOK):
  V1 claude + onarim-x -> rc 1 + HAL=MOTOR-RED log satiri TAM 1 + motor CAGRILMADI
     + stderr'de m3 ile dogru cagri bicimi
  V2 sentetik log: 2 sa once ayni etiketle m3 BASLANGIC+BITIS rc=1 -> GECER
     (sebep=m3-dustu); ayni sey rc=0 hal=BOS ile de GECER
  V3 claude + <her beyaz liste oneki>x (guvenlik-x dahil) -> GECER
  V4 m3 BITIS rc=0 (basarili) -> RED surer
  V5 m3 kosumu 30 sa once rc=1 -> RED (24 sa disi)
  V6 minimax-m3 + onarim-x -> kapi ETKILEMEZ (motor cagrildi, kapi satiri yok)
  V7 claude-api + onarim-x -> RED
  V8 `logo-` (21 Eki, BaBa — gorsel/logo yargisi iscisi): claude + logo-gorsel-yargi
     -> GECER (sebep=beyaz-liste); tiresiz `logox` -> RED (onek TIRE dahil eslesir)
MUTANTLAR (izole kopya; mutant OLMELI = ilgili vaka KIRMIZI yanmali):
  M1 beyaz liste kontrolu kaldirilir (her etiket gecer) -> V1 KIRMIZI
  M2 24 sa penceresi kaldirilir -> V5 KIRMIZI
  M3 `logo-` beyaz listeden cikarilir -> V8 KIRMIZI (logo- etiketi RED alir)

IZOLASYON: gercek isci.log / karantina / anahtar dosyalarina DOKUNULMAZ —
izole kokte yalniz `*.py`, `*.zsh` ve `isci-baglam` SEMBOLIK baglanir
(tools/isci-gh-tavan-test.py deseni); isci.log izole kokte sentetik dogar.
HOME sahte (claude kolu icin sahte 108 baytlik `.ci-token`); ortam MINIMAL.
Gecici agac is sonunda silinir.

KOSUM:  python3 tools/isci-motor-kapisi-test.py
CIKTI:  VAKA=<ad> ... SONUC=GECTI|KALDI · MUTANT=<ad> ... SONUC=OLDU|YASADI
        son satir: MOTOR-KAPISI VAKA=<g>/8 MUTANT=<o>/3 (rc 0 yalniz 8/8 + 3/3)
CI'da canli hat yoktur -> ONKOSUL_YOK + rc 3 (isci-*-test ailesinin kanonu).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

GERCEK_CRON = "/Users/okan/.claude/cron"
GERCEK_ISCI = os.path.join(GERCEK_CRON, "isci.sh")
GERCEK_SABITLER = os.path.join(GERCEK_CRON, "isci-sabitler.zsh")
TMP_ONEK = "motor-kapisi-test-"

BEYAZ_LISTE_RE = re.compile(r"^MOTOR_KAPISI_BEYAZ_LISTE=\(([^)]*)\)$", re.M)
M1_CAPA = ('    if [[ "$ETIKET" == "$MOTOR_KAPISI_ONEK"* ]]; then\n',
           "    if true; then\n")
M2_CAPA = ("        if simdi - ts > PENCERE:\n            continue\n", "")
M3_CAPA = ("olcum-canli- logo-)\n", "olcum-canli-)\n")
LOGO_ETIKET = "logo-gorsel-yargi"
M3_AD = "minimax-m3"
SAHTE_PID = "424242"

SAHTE_CLAUDE = r'''#!%(py)s
# Sahte motor (claude/m3 kollarinin ikisi de bu ikiliyi cagirir): GERCEK API
# CAGRISI YAPMAZ, yalniz cagrildigini kaydeder.
import os, sys
with open(os.path.join(os.environ["SAHTE_IZ"], "motor-cagrildi"), "a") as f:
    f.write("CAGRILDI\n")
sys.exit(0)
'''


def _yaz(yol, metin, kip=0o600):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    os.chmod(yol, kip)


def _izole_kok_kur(tmp, govde):
    """Izole CRON_KOKU: kod sembolik bagli, durum dosyalari izole, isci.sh=govde."""
    kok = os.path.join(tmp, "cron")
    os.makedirs(kok)
    for ad in os.listdir(GERCEK_CRON):
        if ad == "isci-sabitler.zsh" or ad.startswith("."):
            continue
        if ad.endswith((".py", ".zsh")) or ad == "isci-baglam":
            os.symlink(os.path.join(GERCEK_CRON, ad), os.path.join(kok, ad))
    with open(GERCEK_SABITLER, encoding="utf-8") as f:
        sabitler = f.read()
    civili = sabitler.replace("CRON_KOKU=" + GERCEK_CRON, "CRON_KOKU=" + kok, 1)
    if civili == sabitler:
        return None
    _yaz(os.path.join(kok, "isci-sabitler.zsh"), civili)
    _yaz(os.path.join(kok, "isci.sh"), govde, 0o755)
    _yaz(os.path.join(kok, "isci.log"), "")
    _yaz(os.path.join(kok, ".minimax-anahtar"), "sahte-anahtar-yalnizca-test\n")
    return kok


def _ortak_kur(tmp):
    """Sahte HOME (+ .ci-token), sahte motor ikilisi, ev."""
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".claude", "cron"))
    _yaz(os.path.join(home, ".claude", "cron", ".ci-token"), "sk-ant-oat" + "0" * 98)
    bin_d = os.path.join(tmp, "bin")
    os.makedirs(bin_d)
    _yaz(os.path.join(bin_d, "claude"), SAHTE_CLAUDE % {"py": sys.executable}, 0o755)
    ev = os.path.join(tmp, "ev")
    os.makedirs(ev)
    return home, bin_d, ev


def _ts(saat_once):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - saat_once * 3600))


def _m3_log(etiket, saat_once, rc, hal):
    """Sentetik isci.log: ayni etiketle bir m3 kosumu (BASLANGIC + BITIS, pid eslesir)."""
    ts = _ts(saat_once)
    return ("=== %s BASLANGIC motor=%s ev=ev etiket=%s butce=1 model=sahte pid=%s ===\n"
            "=== %s BITIS rc=%d sure=5 hal=%s pid=%s ===\n"
            % (ts, M3_AD, etiket, SAHTE_PID, ts, rc, hal, SAHTE_PID))


def _kos(tmp, kok, ortak, ad, motor="claude", etiket="onarim-x", log_tohum=""):
    home, bin_d, ev = ortak
    iz = os.path.join(tmp, "iz-" + ad)
    os.makedirs(iz)
    spec = os.path.join(tmp, "spec-%s.md" % ad)
    _yaz(spec, "# test spec\n")
    ortam = {
        "HOME": home, "USER": os.environ.get("USER", "okan"),
        "LANG": "en_US.UTF-8", "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "PATH": "/usr/bin:/bin", "CRON_KOKU": kok,
        "PRUVO_ISCI_CLAUDE_BIN": os.path.join(bin_d, "claude"),
        "SAHTE_IZ": iz,
    }
    log = os.path.join(kok, "isci.log")
    _yaz(log, log_tohum)
    p = subprocess.run([os.path.join(kok, "isci.sh"), motor, ev, spec, etiket],
                       capture_output=True, text=True, env=ortam, timeout=300)
    with open(log, encoding="utf-8", errors="replace") as f:
        log_metni = f.read()
    return {
        "rc": p.returncode, "stderr": p.stderr or "", "log": log_metni,
        "motor": os.path.exists(os.path.join(iz, "motor-cagrildi")),
        "motor_adi": motor, "etiket": etiket,
    }


def _red_satirlari(log):
    return [s for s in log.splitlines() if s.startswith("=== ") and " HAL=MOTOR-RED " in s]


def _gecti_satirlari(log):
    return [s for s in log.splitlines() if s.startswith("MOTOR_KAPISI=GECTI ")]


# ---------------------------------------------------------------- olcutler
def red_olcut(r):
    hata = []
    if r["rc"] != 1:
        hata.append("rc=%d" % r["rc"])
    satirlar = _red_satirlari(r["log"])
    beklenen = " motor=%s ev=" % r["motor_adi"]
    if (len(satirlar) != 1 or beklenen not in satirlar[0]
            or (" etiket=%s sebep=beyaz-liste-disi rc=1" % r["etiket"]) not in satirlar[0]):
        hata.append("HAL=MOTOR-RED log satiri=%d" % len(satirlar))
    if r["motor"]:
        hata.append("motor CAGRILDI")
    if "HAL=MOTOR-RED" not in r["stderr"] or ("isci.sh %s " % M3_AD) not in r["stderr"] \
            or r["etiket"] not in r["stderr"]:
        hata.append("stderr dogru cagri bicimi yok")
    if _gecti_satirlari(r["log"]):
        hata.append("MOTOR_KAPISI=GECTI basildi")
    return hata


def gecer_olcut(sebep):
    def olc(r):
        hata = []
        if _red_satirlari(r["log"]) or "MOTOR-RED" in r["stderr"]:
            hata.append("HAL=MOTOR-RED basildi rc=%d" % r["rc"])
        if not r["motor"]:
            hata.append("motor cagrilmadi rc=%d" % r["rc"])
        g = _gecti_satirlari(r["log"])
        if len(g) != 1 or (" sebep=%s" % sebep) not in g[0] \
                or (" etiket=%s " % r["etiket"]) not in g[0] + " ":
            hata.append("MOTOR_KAPISI=GECTI sebep=%s satiri=%d" % (sebep, len(g)))
        return hata
    return olc


def etkilenmez_olcut(r):
    hata = []
    if _red_satirlari(r["log"]) or "MOTOR-RED" in r["stderr"]:
        hata.append("HAL=MOTOR-RED basildi")
    if _gecti_satirlari(r["log"]) or "MOTOR_KAPISI" in r["log"]:
        hata.append("kapi satiri basildi")
    if not r["motor"]:
        hata.append("motor cagrilmadi rc=%d" % r["rc"])
    return hata


def _mutant(govde, capa):
    eski, yeni = capa
    return govde.replace(eski, yeni, 1) if govde.count(eski) == 1 else None


def _guvenli_sil(yol):
    gercek = os.path.realpath(yol)
    if not os.path.basename(gercek).startswith(TMP_ONEK):
        print("TEMIZLIK_ATLANDI: gecici olmayan yol " + gercek)
        return
    for korunan in (GERCEK_CRON, os.path.expanduser("~/dev"),
                    os.path.expanduser("~/.claude/projects")):
        if gercek == korunan or gercek.startswith(korunan + os.sep):
            print("TEMIZLIK_ATLANDI: korunan agac " + gercek)
            return
    shutil.rmtree(gercek, ignore_errors=True)


def _yaz_sonuc(ad, hata):
    print("VAKA=%s OLCULEN=%s SONUC=%s" % (ad, "; ".join(hata) or "beklenen",
                                          "KALDI" if hata else "GECTI"))


def main():
    if not os.path.isfile(GERCEK_ISCI) or not os.path.isfile(GERCEK_SABITLER):
        print("ONKOSUL_YOK: canli isci hatti yok (" + GERCEK_CRON + ")")
        print("MOTOR-KAPISI VAKA=OLCULEMEDI — bu kapi YEREL kosulur, CI'da DEGIL")
        return 3
    with open(GERCEK_ISCI, encoding="utf-8") as f:
        govde = f.read()
    tanimlar = BEYAZ_LISTE_RE.findall(govde)
    onekler = tanimlar[0].split() if len(tanimlar) == 1 else []
    if not onekler or "guvenlik-" not in onekler or any("onarim-x".startswith(o) for o in onekler):
        print("VAKA=kurulum OLCULEN=BEYAZ_LISTE_TANIMI=%r SONUC=KALDI" % tanimlar)
        print("MOTOR-KAPISI VAKA=0/8 MUTANT=0/3")
        return 1
    print("BEYAZ_LISTE=" + " ".join(onekler) + " (isci.sh tanimindan okundu)")
    tmp = tempfile.mkdtemp(prefix=TMP_ONEK)
    vaka_gecti = 0
    mutant_oldu = 0
    try:
        ortak = _ortak_kur(tmp)
        canli_tmp = os.path.join(tmp, "canli")
        kok = _izole_kok_kur(canli_tmp, govde)
        if kok is None:
            print("VAKA=kurulum OLCULEN=SABITLER_CAPASI_TUTMADI SONUC=KALDI")
            return 1

        def kos(ad, **kw):
            return _kos(canli_tmp, kok, ortak, ad, **kw)

        v2 = gecer_olcut("m3-dustu m3_pid=" + SAHTE_PID)
        v2_hata = v2(kos("v2", log_tohum=_m3_log("onarim-x", 2, 1, "HATA")))
        v2_hata += ["hal=BOS: " + h for h in
                    v2(kos("v2-bos", log_tohum=_m3_log("onarim-x", 2, 0, "BOS")))]
        v3_hata = []
        for i, onek in enumerate(onekler):
            v3_hata += ["%sx: %s" % (onek, h) for h in
                        gecer_olcut("beyaz-liste")(kos("v3-%d" % i, etiket=onek + "x"))]
        sonuc = [
            ("V1", red_olcut(kos("v1"))),
            ("V2", v2_hata),
            ("V3", v3_hata),
            ("V4", red_olcut(kos("v4", log_tohum=_m3_log("onarim-x", 2, 0, "TAMAM")))),
            ("V5", red_olcut(kos("v5", log_tohum=_m3_log("onarim-x", 30, 1, "HATA")))),
            ("V6", etkilenmez_olcut(kos("v6", motor=M3_AD))),
            ("V7", red_olcut(kos("v7", motor="claude-api"))),
            ("V8", (([] if "logo-" in onekler else ["logo- beyaz listede YOK"])
                    + gecer_olcut("beyaz-liste")(kos("v8", etiket=LOGO_ETIKET))
                    + ["logox: " + h for h in red_olcut(kos("v8-tiresiz", etiket="logox"))])),
        ]
        for ad, hata in sonuc:
            _yaz_sonuc(ad, hata)
            vaka_gecti += not hata

        # Mutantlar: ayri izole kok, canli govde DEGISMEZ.
        for ad, capa, senaryo, olcut in (
                ("M1", M1_CAPA, dict(), red_olcut),
                ("M2", M2_CAPA, dict(log_tohum=_m3_log("onarim-x", 30, 1, "HATA")), red_olcut),
                ("M3", M3_CAPA, dict(etiket=LOGO_ETIKET), gecer_olcut("beyaz-liste"))):
            m_govde = _mutant(govde, capa)
            m_tmp = os.path.join(tmp, "mutant-" + ad)
            m_kok = _izole_kok_kur(m_tmp, m_govde) if m_govde else None
            if m_kok is None:
                print("MUTANT=%s OLCULEN=CAPA_TUTMADI SONUC=YASADI" % ad)
                continue
            hata = olcut(_kos(m_tmp, m_kok, ortak, ad.lower(), **senaryo))
            # Mutant OLDU = olcut KIRMIZI yandi (vaka mutanti yakaladi).
            print("MUTANT=%s OLCULEN=%s SONUC=%s" % (
                ad, "; ".join(hata) or "vaka-yesil", "OLDU" if hata else "YASADI"))
            mutant_oldu += bool(hata)
    finally:
        _guvenli_sil(tmp)
    print("MOTOR-KAPISI VAKA=%d/8 MUTANT=%d/3" % (vaka_gecti, mutant_oldu))
    return 0 if vaka_gecti == 8 and mutant_oldu == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
