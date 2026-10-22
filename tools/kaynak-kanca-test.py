#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kaynak-kanca-test.py — pre-push KAYNAK SENKRON BLOGU kabul testi.

NE OLCER: `tools/kancalar/pre-push` icindeki `>>> KAYNAK SENKRON BLOGU` bolumu
(gizli kaynak kaydi -> D1 `urun_kaynak` senkronu) DOGRU dalda, DOGRU kosulla,
push'u BLOKLAMADAN ve SESSIZ KALMADAN kosuyor mu.

NASIL: bolum kaynak kancadan capalariyla AYIKLANIR (kopya YAZILMAZ), `mktemp -d`
altindaki sentetik bir depoda (`git_ortami.sentetik_git`, gercek depoda `git init`
YOK) SAHTE bir `tools/d1-kaynak-sync.py` ile kosturulur. Gercek D1'e ve gercek
`.urun-kaynaklari.json`'a DOKUNULMAZ; HOME gecici dizine cevrilir (log da oraya).

VAKALAR: urun-kuyruk push -> cagrilir · main push -> cagrilir · baska dal -> cagrilmaz ·
dal silme -> cagrilmaz · kayit yok -> ATLANDI, push gecer · senkron rc!=0 ->
OLCULEMEDI satiri + log, push gecer · --durum patlar -> OLCULEMEDI · silme tavani ->
SILINMEDI, `--silmeye-izin` VERILMEZ · worktree'den push -> ana checkout kaydi ·
her vakada: stdin (ref listesi) sonraki bloklara AYNEN geri acilir, ham arac ciktisi
(link) ekrana DUSMEZ, bolum `exit` icermez, D1 blogundan ONCE durur.

MUTANTLAR (her biri en az bir vakayi KIRMIZI yakmali; yakmazsa test KIRMIZI):
bolum kaldirilir · kayit-yok push'u durdurur · rc!=0 push'u durdurur ·
`--silmeye-izin` verilir · stdin geri acilmaz.

Cikis: 0 = YESIL, 1 = KIRMIZI, 2 = OLCULEMEDI (capa yok / mutant uygulanamadi).
"""

import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "tools"))
from git_ortami import git_ortami, sentetik_git  # noqa: E402

KANCA = os.path.join(KOK, "tools", "kancalar", "pre-push")
BAS = "# >>> KAYNAK SENKRON BLOGU"
SON = "# <<< KAYNAK SENKRON BLOGU <<<"
D1_CAPA = "# urunler.json main'e push edilirken D1'i OTOMATIK senkronla."
SIFIR = "0" * 40
SHA = "1" * 40
SAHTE_LINK = "https://ornek.gecersiz/kaynak/123"

# Sahte arac: argv'yi kaydeder, FAKE_MOD'a gore gercek aracin cikti sozlesmesini taklit eder
# (tools/d1-kaynak-sync.py::durum / senkron). Her ciktiya bir LINK sokulur: kanca ham
# ciktiyi basarsa gizlilik iddiasi KIRMIZI yanar.
SAHTE_ARAC = r'''#!/usr/bin/env python3
import os, sys
with open(os.environ["FAKE_KAYIT"], "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
mod = os.environ.get("FAKE_MOD", "senkron")
link = "__LINK__"
durum = "--durum" in sys.argv
if durum:
    if mod == "durum-hata":
        sys.exit("wrangler patladi " + link)
    print("YEREL_LINK=10\nD1_SATIR=%d\n  kaynak " % (10 if mod == "senkron" else 9) + link)
    print("HUKUM=%s" % ("SENKRON" if mod == "senkron" else "SAPMA"))
    sys.exit(0 if mod == "senkron" else 1)
if mod == "sapma":
    print("PLAN: yerel_link=10 d1_satir=9 ekle=38 guncelle=0 sil=0 " + link)
    print("YAZILDI=38 (ifade=38) SILINDI=0")
    sys.exit(0)
if mod == "silme":
    if "--silmeye-izin" in sys.argv:
        print("YAZILDI=0 (ifade=0) SILINDI=900")
        sys.exit(0)
    sys.exit("\U0001f534 SILME EMNIYETI: 900 satir silinecekti (tavan 500) — DURDU. " + link)
sys.exit("\U0001f534 SENKRON SONRASI SAPMA VAR " + link)
'''.replace("__LINK__", SAHTE_LINK)


def bolum_ayikla(govde):
    """(bolum|None, tani) — capalar arasi metin; capa yoksa FAIL-CLOSED None."""
    b = govde.find(BAS)
    s = govde.find(SON)
    if b < 0 or s < 0 or s < b:
        return None, "capa bulunamadi (%s ... %s)" % (BAS, SON)
    return govde[b:s + len(SON)] + "\n", None


class Fikstur:
    def __init__(self, tmp):
        self.tmp = tmp
        self.ana = os.path.join(tmp, "ana")
        self.agac = os.path.join(tmp, "agac")
        self.home = os.path.join(tmp, "home")
        os.makedirs(os.path.join(self.home, ".claude", "cron"))
        os.makedirs(os.path.join(self.ana, "tools"))
        sentetik_git(tmp, "init", "-q", "-b", "main", self.ana, check=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sentetik_git(self.ana, "commit", "-q", "--allow-empty", "-m", "taban",
                     ayarlar=("-c", "core.hooksPath=/dev/null"), check=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sentetik_git(self.ana, "worktree", "add", "-q", "-b", "is", self.agac,
                     ayarlar=("-c", "core.hooksPath=/dev/null"), check=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(os.path.join(self.ana, "tools", "d1-kaynak-sync.py"), "w") as f:
            f.write(SAHTE_ARAC)
        self.kayit_yolu = os.path.join(self.ana, ".urun-kaynaklari.json")
        self.log = os.path.join(self.home, ".claude", "cron", "kaynak-sync.log")

    def kos(self, bolum, refler, mod="senkron", kayit=True, cwd=None):
        """{rc, out, err, cagri: [argv], geri: str, girdi: str, log: str}"""
        if kayit:
            open(self.kayit_yolu, "w").write("{}\n")
        elif os.path.exists(self.kayit_yolu):
            os.remove(self.kayit_yolu)
        for y in (self.log,):
            if os.path.exists(y):
                os.remove(y)
        cagri_dosya = os.path.join(self.tmp, "cagri.txt")
        geri_dosya = os.path.join(self.tmp, "geri.txt")
        for y in (cagri_dosya, geri_dosya):
            if os.path.exists(y):
                os.remove(y)
        betik = os.path.join(self.tmp, "blok.sh")
        with open(betik, "w") as f:
            f.write(bolum + 'cat > "$PP_GERI"\necho PUSH_GECTI\nexit 0\n')
        girdi = "".join("%s %s %s %s\n" % r for r in refler)
        ort = git_ortami()
        ort.update({"HOME": self.home, "FAKE_MOD": mod, "FAKE_KAYIT": cagri_dosya,
                    "PP_GERI": geri_dosya})
        p = subprocess.run(["sh", betik], input=girdi, capture_output=True, text=True,
                           cwd=cwd or self.ana, env=ort, timeout=60)
        oku = lambda y: open(y).read() if os.path.exists(y) else ""  # noqa: E731
        return {"rc": p.returncode, "out": p.stdout, "err": p.stderr, "girdi": girdi,
                "cagri": [s for s in oku(cagri_dosya).splitlines()],
                "geri": oku(geri_dosya), "log": oku(self.log)}


def ref(uzak, yerel_sha=SHA):
    return ("refs/heads/is", yerel_sha, uzak, SHA)


def ortak_iddialar(r):
    """Her vakada gecerli: push gecer, stdin geri acilir, link sizmaz."""
    hata = []
    if r["rc"] != 0 or "PUSH_GECTI" not in r["out"]:
        hata.append("push DURDU (rc=%d)" % r["rc"])
    if r["geri"] != r["girdi"]:
        hata.append("stdin sonraki bloklara AYNEN geri acilmadi")
    if "://" in r["out"] + r["err"] + r["log"]:
        hata.append("ham arac ciktisi (link) ekrana/loga DUSTU")
    return hata


def vakalar(fx, bolum):
    """[(ad, [hata])] — bos hata listesi = YESIL."""
    sonuc = []

    def vaka(ad, r, ozel):
        sonuc.append((ad, ortak_iddialar(r) + [h for h in ozel if h]))

    r = fx.kos(bolum, [ref("refs/heads/urun-kuyruk")], mod="senkron")
    vaka("V1 urun-kuyruk push -> senkron cagrilir", r, [
        None if r["cagri"] == ["--durum"] else "cagri=%r (beklenen ['--durum'])" % r["cagri"],
        None if "KAYNAK_SYNC=SENKRON eklenen=0" in r["out"] else "SENKRON satiri yok",
    ])
    r = fx.kos(bolum, [ref("refs/heads/main")], mod="sapma")
    vaka("V2 main push + EKSIK -> durum sonra tam senkron", r, [
        None if r["cagri"] == ["--durum", ""] else "cagri=%r (beklenen durum+tam)" % r["cagri"],
        None if "KAYNAK_SYNC=SENKRON eklenen=38" in r["out"] else "eklenen=38 satiri yok",
        None if "KAYNAK_SYNC=SENKRON eklenen=38" in r["log"] else "log satiri yok",
    ])
    r = fx.kos(bolum, [ref("refs/heads/kral/baska-dal")], mod="sapma")
    vaka("V3 baska dal -> cagrilmaz", r, [
        None if not r["cagri"] else "cagrildi: %r" % r["cagri"],
        None if "KAYNAK_SYNC" not in r["out"] + r["err"] else "baska dalda KAYNAK_SYNC basildi",
    ])
    r = fx.kos(bolum, [ref("refs/heads/main", SIFIR)], mod="sapma")
    vaka("V4 dal silme (yerel sha sifir) -> cagrilmaz", r, [
        None if not r["cagri"] else "cagrildi: %r" % r["cagri"],
    ])
    r = fx.kos(bolum, [ref("refs/heads/urun-kuyruk")], mod="sapma", kayit=False)
    vaka("V5 kayit yok -> ATLANDI, push gecer", r, [
        None if not r["cagri"] else "kayit yokken arac cagrildi",
        None if "KAYNAK_SYNC=ATLANDI sebep=kayit-yok" in r["out"] else "ATLANDI satiri yok",
    ])
    r = fx.kos(bolum, [ref("refs/heads/urun-kuyruk")], mod="hata")
    vaka("V6 senkron rc!=0 -> OLCULEMEDI stderr+log, push gecer", r, [
        None if "KAYNAK_SYNC=OLCULEMEDI rc=1 asama=senkron" in r["err"]
        else "stderr'de OLCULEMEDI rc=1 yok",
        None if "KAYNAK_SYNC=OLCULEMEDI rc=1" in r["log"] else "log'da OLCULEMEDI yok",
    ])
    r = fx.kos(bolum, [ref("refs/heads/main")], mod="durum-hata")
    vaka("V7 --durum patlar -> OLCULEMEDI asama=durum", r, [
        None if "KAYNAK_SYNC=OLCULEMEDI rc=1 asama=durum" in r["err"]
        else "stderr'de OLCULEMEDI asama=durum yok",
        None if r["cagri"] == ["--durum"] else "durum patlayinca yazma kolu kostu: %r" % r["cagri"],
    ])
    r = fx.kos(bolum, [ref("refs/heads/urun-kuyruk")], mod="silme")
    vaka("V8 silme tavani -> SILINMEDI, --silmeye-izin verilmez", r, [
        None if not any("--silmeye-izin" in c for c in r["cagri"])
        else "kanca --silmeye-izin VERDI",
        None if "KAYNAK_SYNC=SILME_TAVANI rc=1 silinecek=900 tavan=500 SILINMEDI" in r["err"]
        else "SILME_TAVANI uyarisi yok",
    ])
    r = fx.kos(bolum, [ref("refs/heads/kral/x"), ref("refs/heads/urun-kuyruk")],
               mod="senkron", cwd=fx.agac)
    vaka("V9 worktree'den cok-ref push -> ana checkout kaydi kullanilir", r, [
        None if r["cagri"] == ["--durum"] else "cagri=%r" % r["cagri"],
        None if "KAYNAK_SYNC=SENKRON" in r["out"] else "SENKRON satiri yok",
    ])
    return sonuc


def kablo_iddialari(govde, bolum):
    hata = []
    bi, di = govde.find(BAS), govde.find(D1_CAPA)
    if di < 0 or bi > di:
        hata.append("bolum D1 blogundan ONCE degil (D1 blogu main disinda `exit 0` yapar)")
    for satir in bolum.splitlines():
        s = satir.strip()
        if s.startswith("exit") or " exit " in " %s " % s.split("#")[0]:
            hata.append("bolumde `exit` var (fail-open sozlesmesi): %s" % s)
    return hata


MUTANTLAR = (
    ("M1 bolum kaldirildi", None, None),
    ("M2 kayit-yok push'u durdurur",
     'echo "KAYNAK_SYNC=ATLANDI sebep=kayit-yok"',
     'echo "KAYNAK_SYNC=ATLANDI sebep=kayit-yok"; exit 1'),
    ("M3 rc!=0 push'u durdurur",
     '        echo "$pruvo_ks_sonuc" >&2\n',
     '        echo "$pruvo_ks_sonuc" >&2; exit 1\n'),
    ("M4 --silmeye-izin verilir",
     'pruvo_ks_cikti=$(python3 "$pruvo_ks_arac" </dev/null 2>&1)',
     'pruvo_ks_cikti=$(python3 "$pruvo_ks_arac" --silmeye-izin </dev/null 2>&1)'),
    ("M5 stdin geri acilmaz",
     '  exec 0< "$pruvo_ks_girdi"\n', '  :\n'),
)


def main():
    try:
        govde = open(KANCA, encoding="utf-8").read()
    except OSError as e:
        print("KAYNAK_KANCA_TEST OLCULEMEDI kanca okunamadi: %s" % e)
        return 2
    bolum, tani = bolum_ayikla(govde)
    if bolum is None:
        print("KAYNAK_KANCA_TEST OLCULEMEDI %s" % tani)
        print("SONUC: OLCULEMEDI")
        return 2

    tmp = tempfile.mkdtemp(prefix="kaynak-kanca-")
    try:
        fx = Fikstur(tmp)
        sonuc = vakalar(fx, bolum)
        kablo = kablo_iddialari(govde, bolum)
        sonuc.append(("V10 kablo: bolum D1'den once, `exit` yok", kablo))
        vg = sum(1 for _a, h in sonuc if not h)
        for ad, h in sonuc:
            print("%s %s%s" % ("✅" if not h else "🔴", ad, "" if not h else " — " + "; ".join(h)))

        mg, olculemedi = 0, False
        for ad, eski, yeni in MUTANTLAR:
            if eski is None:
                mutant = ""
            elif bolum.count(eski) != 1:
                print("⚠️ %s — OLCULEMEDI (capa %d kez bulundu)" % (ad, bolum.count(eski)))
                olculemedi = True
                continue
            else:
                mutant = bolum.replace(eski, yeni)
            dusen = [a for a, h in vakalar(fx, mutant) if h]
            if dusen:
                mg += 1
                print("✅ %s — oldu (%d vaka KIRMIZI, ilki: %s)" % (ad, len(dusen), dusen[0]))
            else:
                print("🔴 %s — YASADI (hicbir vaka yakmadi)" % ad)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    vt, mt = len(sonuc), len(MUTANTLAR)
    print("KAYNAK_KANCA_TEST VAKA=%d/%d MUTANT=%d/%d" % (vg, vt, mg, mt))
    if olculemedi:
        print("SONUC: OLCULEMEDI")
        return 2
    if vg == vt and mg == mt:
        print("SONUC: YESIL ✅")
        return 0
    print("SONUC: KIRMIZI 🔴")
    return 1


if __name__ == "__main__":
    sys.exit(main())
