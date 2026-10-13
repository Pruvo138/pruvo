#!/usr/bin/env python3
"""ISCI URUN KAPISI (13 Eki 2026, guvenlik-isci-urun-kapisi).

OLCULEN KUSUR: m3 iscisi `uretim-organizer-faz5b1` `BITIS rc=0 hal=SAGLIKLI`
yazdi ama HIC urun uretmedi (galeri dizini bos). isci.sh hukmu yalniz
motorun zarfindan (`isci-hal-cozucu.py`) okuyordu; isin URUNUNE bakmiyordu.

Kaynak: pruvo `tools/isci-urun-kapisi.py`; kurulu kopya
`~/.claude/cron/isci-urun-kapisi.py` (isci.sh cagirir). Kabul:
`tools/isci-urun-kapisi-test.py`.

Spec satir basinda `URUN_YOLU=<glob>` (birden cok olabilir; `~`, mutlak ya da
EV kokune gore goreli). Iki adim:

  basla --spec S --ev E
      -> `ZAMAN=<epoch>` `SAYI=<n|->`  (kosum BASINDA olcum)
  bitis --spec S --ev E --zaman T --baslangic-sayi N --hal H --rc R
      -> `HAL=<son hal>` `RC=<son rc>` `URUN=<n|->` `SATIR=<log satiri>`

Sayilan urun: glob eslesmesi (dizinse icindeki dosyalar), BOS OLMAYAN ve
mtime >= ZAMAN olan dosya. Eski cikti yeni kosumu YESIL yapmaz.

Hukum:
  * spec'te URUN_YOLU yok -> hal/rc AYNEN + `URUN_KAPISI=OLCULEMEDI-URUN`.
  * rc != 0 ya da hal motor/tavan hatasi -> motorun hukmu KORUNUR (BOS ezmez).
  * rc == 0, hal SAGLIKLI|OLCULEMEDI, urun 0 -> `HAL=BOS` + `RC=1`.
  * urun > 0 -> hal/rc AYNEN, `urun=<n>`.

ISCI AGACI/DALI EKSENI (13 Eki 2026, guvenlik-isci-urun-agac). Olculen: isci
`--ev` ana checkout ile cagrilir ama kendi git worktree'sini acip orada
calisir, dali push'lar; goreli URUN_YOLU yalniz EV'de aranirdi -> urun dalda
varken `hal=BOS urun=0` (2/2 sahte). EV'de eslesme yoksa GORELI desen ayni
deponun su eksenlerinde de olculur (mutlak desen DEGISMEZ, yalniz EV):
  * agac:<ad> -- `git worktree list` agaclarindan kosum sirasinda (>= ZAMAN)
    OLUSAN ya da HEAD'i degisen agac; sayilan: agacta kirli/izlenmeyen ve
    mtime >= ZAMAN dosya ya da kosum sirasinda commit'lenen dosya.
  * dal:<ref> -- committerdate >= ZAMAN olan yerel dal; sayilan: kosum
    sirasindaki commit'lerde degisen VE `merge-base(EV HEAD, ref)..ref`
    farkinda kalan, ref'te BOS OLMAYAN dosya.
Taze checkout'un eski dosyasi (mtime yeni ama icerik degismemis) SAYILMAZ.
git calismazsa eksen 0 sayar (fail-closed: BOS kalir). Bulunan eksen
`SATIR=` icinde `eksen=ev|agac:<ad>|dal:<ref>|yok` olarak basilir.
"""
import glob
import os
import re
import subprocess
import sys
import time

ANAHTAR = "URUN_YOLU="
# BOS yalniz motorun "basarili" (ya da hukumsuz) dedigi kosumu ezer.
EZILEBILIR_HALLER = {"SAGLIKLI", "OLCULEMEDI"}


def urun_yollari(spec):
    yollar = []
    with open(spec, encoding="utf-8", errors="replace") as f:
        for satir in f:
            if not satir.startswith(ANAHTAR):
                continue
            deger = satir[len(ANAHTAR):].strip().strip("`'\"").strip()
            if deger:
                yollar.append(deger)
    return yollar


def _mutlak(desen, ev):
    desen = os.path.expanduser(desen)
    if not os.path.isabs(desen):
        desen = os.path.join(ev, desen)
    return desen


def urun_say(yollar, ev, zaman):
    """Bos olmayan ve mtime >= zaman olan dosya sayisi (zaman None: hepsi)."""
    dosyalar = set()
    for desen in yollar:
        for yol in glob.glob(_mutlak(desen, ev), recursive=True):
            if os.path.isdir(yol):
                for kok, _, adlar in os.walk(yol):
                    for ad in adlar:
                        dosyalar.add(os.path.join(kok, ad))
            else:
                dosyalar.add(yol)
    n = 0
    for yol in dosyalar:
        try:
            st = os.stat(yol)
        except OSError:
            continue
        if st.st_size <= 0:
            continue
        if zaman is not None and st.st_mtime < zaman:
            continue
        n += 1
    return n


# ------------------------------------------------- isci agaci / dali ekseni
# Ust ortamdan (kanca ici vb.) gelen GIT_DIR/GIT_WORK_TREE `-C` yolunu ezer.
_GIT_ORTAM_SIL = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                  "GIT_PREFIX", "GIT_NAMESPACE")


def _git(kok, *arg):
    """git ciktisi; hata/zaman asiminda None (cagiran 0 sayar)."""
    ortam = {k: v for k, v in os.environ.items() if k not in _GIT_ORTAM_SIL}
    ortam["GIT_OPTIONAL_LOCKS"] = "0"  # olcum: yabanci agacin index'ine YAZMA
    try:
        p = subprocess.run(["git", "-C", kok, "-c", "core.quotepath=off"] + list(arg),
                           capture_output=True, text=True, timeout=30, env=ortam)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def _satirlar(metin):
    return [s for s in (metin or "").splitlines() if s.strip()]


def _desen_re(desen):
    """glob deseni -> depo-goreli yol regex'i (`*` `/` gecmez, `**` gecer)."""
    parcalar = desen.split("/")
    re_ = ""
    for i, p in enumerate(parcalar):
        son = i == len(parcalar) - 1
        if p == "**":
            re_ += ".*" if son else "(?:[^/]+/)*"
            continue
        j = 0
        while j < len(p):
            c = p[j]
            if c == "*":
                re_ += "[^/]*"
            elif c == "?":
                re_ += "[^/]"
            elif c == "[" and "]" in p[j + 2:]:
                k = p.index("]", j + 2)
                sinif = p[j + 1:k]
                if sinif.startswith("!"):
                    sinif = "^" + sinif[1:]
                re_ += "[" + sinif.replace("\\", "\\\\") + "]"
                j = k
            else:
                re_ += re.escape(c)
            j += 1
        if not son:
            re_ += "/"
    return re.compile(re_ + r"\Z")


def _eslesir(yol, desenler):
    """Yol desene ya da desene uyan bir DIZININ altina dusuyor mu."""
    parcalar = yol.split("/")
    for d in desenler:
        for k in range(len(parcalar), 0, -1):
            if d.match("/".join(parcalar[:k])):
                return True
    return False


def _goreli_desenler(yollar):
    desenler = []
    for d in yollar:
        if os.path.isabs(os.path.expanduser(d)):
            continue  # mutlak URUN_YOLU yalniz EV'de (davranis degismez)
        while d.startswith("./"):
            d = d[2:]
        desenler.append(_desen_re(d))
    return desenler


def _kosumda_commitlenen(kok, uc, zaman):
    """uc'tan erisilen, committer zamani >= zaman olan commit'lerin dosyalari."""
    cikti = _git(kok, "log", "--max-age=%d" % int(zaman), "--no-renames",
                 "--format=", "--name-only", uc)
    return set(_satirlar(cikti))


def _tabandan_fark(kok, ev_bas, uc):
    taban = _git(kok, "merge-base", ev_bas, uc) if ev_bas else None
    if not taban:
        return None
    return set(_satirlar(_git(kok, "diff", "--no-renames", "--name-only",
                              taban.strip(), uc)))


def _uc_yeni(kok, uc, zaman, desenler, ev_bas):
    """uc'ta (commit) kosum sirasinda commit'lenmis, tabandan farkli, bos
    olmayan ve desene uyan dosyalar."""
    adaylar = {y for y in _kosumda_commitlenen(kok, uc, zaman) if _eslesir(y, desenler)}
    if not adaylar:
        return set()
    fark = _tabandan_fark(kok, ev_bas, uc)
    if fark is None:
        return set()
    bulunan = set()
    for y in sorted(adaylar & fark):
        boy = _git(kok, "cat-file", "-s", "%s:%s" % (uc, y))
        if boy and boy.strip().isdigit() and int(boy.strip()) > 0:
            bulunan.add(y)
    return bulunan


def _mtime(yol):
    try:
        return os.stat(yol).st_mtime
    except OSError:
        return None


def _agac_aktif(agac, zaman):
    """Agac kosum sirasinda olustu ya da HEAD'i degisti mi."""
    gitdir = _git(agac, "rev-parse", "--absolute-git-dir")
    izler = [os.path.join(agac, ".git")]
    if gitdir:
        g = gitdir.strip()
        izler += [os.path.join(g, "HEAD"), os.path.join(g, "logs", "HEAD")]
    if any((m is not None and m >= zaman) for m in map(_mtime, izler)):
        return True
    ct = _git(agac, "log", "-1", "--format=%ct", "HEAD")
    return bool(ct and ct.strip().isdigit() and int(ct.strip()) >= int(zaman))


def _agac_say(agac, zaman, desenler, ev_bas):
    bulunan = set()
    kirli = _git(agac, "status", "--porcelain", "-uall", "--no-renames")
    for s in _satirlar(kirli):
        y = s[3:]
        if not _eslesir(y, desenler):
            continue
        m = os.path.join(agac, y)
        try:
            st = os.stat(m)
        except OSError:
            continue
        if os.path.isfile(m) and st.st_size > 0 and st.st_mtime >= zaman:
            bulunan.add(y)
    bulunan |= _uc_yeni(agac, "HEAD", zaman, desenler, ev_bas)
    return bulunan


def _ad(metin):
    return metin.replace(" ", "%20").replace(",", "%2C")


def isci_eksenleri(yollar, ev, zaman):
    """EV disindaki agac/dal eksenleri: ([eksen etiketi], {goreli yol})."""
    desenler = _goreli_desenler(yollar)
    if not desenler or _git(ev, "rev-parse", "--git-dir") is None:
        return [], set()
    ev_bas = (_git(ev, "rev-parse", "HEAD") or "").strip()
    ev_gercek = os.path.realpath(ev)
    eksenler, toplam = [], set()
    agaclar = [s[len("worktree "):] for s in _satirlar(_git(ev, "worktree", "list", "--porcelain"))
               if s.startswith("worktree ")]
    for agac in agaclar:
        if os.path.realpath(agac) == ev_gercek or not os.path.isdir(agac):
            continue
        if not _agac_aktif(agac, zaman):
            continue
        b = _agac_say(agac, zaman, desenler, ev_bas)
        if b:
            eksenler.append("agac:" + _ad(os.path.basename(agac.rstrip("/"))))
            toplam |= b
    for s in _satirlar(_git(ev, "for-each-ref", "--format=%(refname) %(committerdate:unix)",
                            "refs/heads")):
        ref, _, ct = s.rpartition(" ")
        if not ct.isdigit() or int(ct) < int(zaman):
            continue
        b = _uc_yeni(ev, ref, zaman, desenler, ev_bas)
        if b:
            eksenler.append("dal:" + _ad(ref))
            toplam |= b
    return eksenler, toplam


def _arg(argv, ad, varsayilan=None):
    if ad in argv:
        i = argv.index(ad)
        if i + 1 < len(argv):
            return argv[i + 1]
    return varsayilan


def basla(argv):
    spec, ev = _arg(argv, "--spec"), _arg(argv, "--ev", os.getcwd())
    zaman = time.time()
    yollar = urun_yollari(spec)
    sayi = urun_say(yollar, ev, None) if yollar else "-"
    print("ZAMAN=%.6f" % zaman)
    print("SAYI=%s" % sayi)
    return 0


def bitis(argv):
    spec, ev = _arg(argv, "--spec"), _arg(argv, "--ev", os.getcwd())
    zaman = float(_arg(argv, "--zaman"))
    bas_sayi = _arg(argv, "--baslangic-sayi", "-")
    hal = _arg(argv, "--hal", "OLCULEMEDI")
    rc = int(_arg(argv, "--rc"))
    yollar = urun_yollari(spec)
    if not yollar:
        print("HAL=%s" % hal)
        print("RC=%d" % rc)
        print("URUN=-")
        print("SATIR=URUN_KAPISI=OLCULEMEDI-URUN sebep=spec-urun-yolu-yok")
        return 0
    n = urun_say(yollar, ev, zaman)
    eksen = "ev" if n > 0 else "yok"
    if n == 0:
        eksenler, bulunan = isci_eksenleri(yollar, ev, zaman)
        if bulunan:
            n, eksen = len(bulunan), ",".join(eksenler)
    yol_alani = ",".join(y.replace(" ", "%20") for y in yollar)
    if n == 0 and rc == 0 and hal in EZILEBILIR_HALLER:
        print("HAL=BOS")
        print("RC=1")
        print("URUN=0")
        print("SATIR=URUN_KAPISI=BOS sebep=urun-yok onceki_hal=%s urun=0 "
              "urun_baslangic=%s eksen=yok urun_yolu=%s" % (hal, bas_sayi, yol_alani))
        return 0
    karar = "VAR" if n > 0 else "KORUNDU"
    print("HAL=%s" % hal)
    print("RC=%d" % rc)
    print("URUN=%d" % n)
    print("SATIR=URUN_KAPISI=%s urun=%d urun_baslangic=%s eksen=%s urun_yolu=%s"
          % (karar, n, bas_sayi, eksen, yol_alani))
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in ("basla", "bitis"):
        print("Kullanim: isci-urun-kapisi.py basla|bitis --spec S --ev E ...",
              file=sys.stderr)
        return 2
    try:
        return basla(argv[2:]) if argv[1] == "basla" else bitis(argv[2:])
    except Exception as e:  # cagiran (isci.sh) rc!=0'i OLCULEMEDI-ARAC sayar
        print("URUN_KAPISI_HATA %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
