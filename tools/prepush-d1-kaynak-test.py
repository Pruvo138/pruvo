#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — pre-push kancasi D1 senkronunu PUSH EDILEN COMMIT'ten mi besliyor?

  python3 tools/prepush-d1-kaynak-test.py

SORUN (olculen kusur, 9 Agu 2026):
`tools/kancalar/pre-push` d1-sync.py'yi BAYRAKSIZ cagiriyordu; d1-sync bayraksiz kosunca
katalogu CALISMA AGACINDAKI urunler.json'dan okur. Bes ev (KraL · MaCiT · KaaN · ArTisT ·
HocA) ayni checkout'u paylasiyor: bir oturumun YARIM parti urun degisikligi agacta dururken
BASKA bir oturum push ederse o yarim parti CANLI D1'e (Ege'nin okudugu katalog) yazilirdi —
ve hicbir sey kirmizi yakmaz, push YESIL doner. `--head` bayragi bu amacla MEVCUTTU ama
kancaya BAGLANMAMISTI.

BU TESTIN OLCTUGU SEY — DAVRANIS, BEYAN DEGIL:
Sentetik GERCEK git depolarinda (calisan uzak + kurulu kanca) GERCEK `git push` kosulur;
senkronun FIILEN okudugu katalog kaydedilir ve icerigi olculur. Kabuk taklidi YOK.

  A. commit'lenmemis urun senkrona GIRMEZ · commit'li urun GIRER (kontrol ayagi — yoksa
     "hicbir sey senkronlanmiyor" mutanti yesil gecerdi).
  B. KONTROL MUTANTI: cagridan bayrak sokulunce A KIRMIZI yanar (yanmazsa test hicbir sey
     olcmuyor demektir).
  C. KOPRU: `git push origin dal:main` — push edilen sha HEAD DEGIL. `--head` orada YANLIS
     agaci okurdu; kanca `--kaynak` ile push edilen commit'i cikarir.
  D. FAIL-CLOSED: katalog push edilen commit'ten cikarilamazsa senkron HIC kosmaz (calisma
     agacina SESSIZCE dusmez) ve push BLOKLANMAZ.
  E. SURE TAVANI: her gercek push <= 30 sn (fail-slow = fail-open; asili kalan kol iptal
     edilir ve kapi hic olculmez).

CANLI D1'e / wrangler'a / AGA DOKUNMAZ: sentetik depodaki `tools/d1-sync.py` bir KAYIT
stub'idir; kaynak secimini GERCEK d1-sync.py'nin `kaynak_coz()` fonksiyonuna delege eder
(fikstur gercek davranisi taklit etmek zorunda degil — gercegini CAGIRIR), sonra yalnizca
okudugu katalogu diske yazar.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
KANCA_KAYNAGI = os.path.join(TOOLS, "kancalar", "pre-push")
GERCEK_SYNC = os.path.join(TOOLS, "d1-sync.py")
SURE_TAVANI = 30.0

gecen = [0]
kalan = [0]
sureler = []


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + detay if detay else ""))


# ── sentetik depo yardimcilari ────────────────────────────────────────────────
def _temiz_env():
    """GIT_* degiskenlerini SIL: bu test bir kanca icinden kosarsa (ya da baska bir
    git surecinin altinda) miras alinan GIT_DIR sentetik depoyu ANA depoya baglar."""
    env = dict(os.environ)
    for anahtar in list(env):
        if anahtar.startswith("GIT_"):
            del env[anahtar]
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["HOME"] = env.get("PRUVO_TEST_HOME", env.get("HOME", "/tmp"))
    return env


def _git(kok, *args, **kw):
    return subprocess.run(["git"] + list(args), cwd=kok, capture_output=True,
                          text=True, env=_temiz_env(), timeout=kw.get("zaman", 120))


def _urun(uid):
    return {"id": uid, "baslik": "urun %s" % uid, "kategori": "Oyun/Hobi", "marka": [],
            "fiyat": "100 TL", "gorseller": ["https://media.example/%s-1.jpg" % uid],
            "aciklama": "aciklama %s" % uid}


def _katalog_yaz(kok, idler):
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([_urun(u) for u in idler], f, ensure_ascii=False)


def _yaz(yol, metin, calistirilabilir=False):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    if calistirilabilir:
        os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


_KAPI_STUB = "#!/usr/bin/env python3\nimport sys\nsys.stdin.read()\nsys.exit(0)\n"

_KAYIT_STUB = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SENTETIK KAYIT STUB'I — canli D1'e DOKUNMAZ.
Kaynak secimini GERCEK d1-sync.py'ye delege eder (taklit DEGIL), okudugu katalogu yazar."""
import argparse
import importlib.util
import json
import os
import sys

GERCEK = %(gercek)r
KAYIT = %(kayit)r

spec = importlib.util.spec_from_file_location("gercek_d1_sync", GERCEK)
m = importlib.util.module_from_spec(spec)
sys.modules["gercek_d1_sync"] = m
spec.loader.exec_module(m)

kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m.KOK = kok
m.URUNLER = os.path.join(kok, "urunler.json")

ap = argparse.ArgumentParser()
ap.add_argument("--kaynak", default=None)
ap.add_argument("--head", action="store_true")
a, _artan = ap.parse_known_args()

# FAIL-CLOSED yol GERCEK fonksiyonda: cozulemezse sys.exit -> KAYIT YAZILMAZ.
yol, beyan, _gecici = m.kaynak_coz(a.kaynak, a.head)
if yol is None:
    yol, beyan = m.URUNLER, "calisma agaci"
with open(yol, encoding="utf-8") as f:
    d = json.load(f)
with open(KAYIT, "w", encoding="utf-8") as f:
    json.dump({"argv": sys.argv[1:], "beyan": beyan,
               "idler": [u.get("id") for u in d]}, f, ensure_ascii=False)
print("KAYIT: %%s" %% beyan)
'''


def fikstur_kur(tmp, ad, kanca_govdesi=None):
    """GERCEK git deposu + GERCEK uzak (bare) + KURULU pre-push kancasi.
    Doner: (depo_yolu, kayit_yolu)."""
    depo = os.path.join(tmp, ad)
    uzak = os.path.join(tmp, ad + "-uzak.git")
    kayit = os.path.join(tmp, ad + "-kayit.json")      # depo DISINDA: agaci kirletmez
    os.makedirs(depo)
    _git(tmp, "init", "-q", "--bare", uzak)
    _git(uzak, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(depo, "init", "-q")
    _git(depo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(depo, "config", "user.email", "t@t")
    _git(depo, "config", "user.name", "t")
    _git(depo, "remote", "add", "origin", uzak)

    # Kancanin fail-closed on-kapilari: sentetik depoda stub (bu test onlari olcmez).
    _yaz(os.path.join(depo, "tools", "ci-kapsam-test.py"), _KAPI_STUB)
    _yaz(os.path.join(depo, "tools", "gecmis-geri-donus-kapisi.py"), _KAPI_STUB)
    _yaz(os.path.join(depo, "tools", "d1-sync.py"),
         _KAYIT_STUB % {"gercek": GERCEK_SYNC, "kayit": kayit})

    govde = kanca_govdesi if kanca_govdesi is not None else \
        open(KANCA_KAYNAGI, encoding="utf-8").read()
    _yaz(os.path.join(depo, ".git", "hooks", "pre-push"), govde, calistirilabilir=True)

    _katalog_yaz(depo, ["u-taban"])
    _git(depo, "add", "-A")
    _git(depo, "commit", "-q", "-m", "taban")
    _git(depo, "push", "-q", "origin", "main")
    if os.path.exists(kayit):
        os.unlink(kayit)                                # taban push'unun kaydi SAYILMAZ
    return depo, kayit


def push_et(depo, *arglar):
    """GERCEK push. Doner: (rc, cikti, sure)."""
    t0 = time.time()
    p = _git(depo, "push", *(arglar or ("origin", "main")))
    sure = time.time() - t0
    sureler.append((depo, sure))
    return p.returncode, (p.stdout or "") + (p.stderr or ""), sure


def kayit_oku(kayit):
    if not os.path.exists(kayit):
        return None
    with open(kayit, encoding="utf-8") as f:
        return json.load(f)


tmp = tempfile.mkdtemp(prefix="prepush-d1-kaynak-")
try:
    # ══ A) DAVRANIS AYAGI — GERCEK push, commit'siz urun senkrona GIRMEZ ══════════
    print("\n[A] DAVRANIS — gercek push: commit'lenmemis urun senkrona GIRIYOR mu?")
    depo_a, kayit_a = fikstur_kur(tmp, "a")
    _katalog_yaz(depo_a, ["u-commitli", "u-taban"])
    _git(depo_a, "add", "urunler.json")
    _git(depo_a, "commit", "-q", "-m", "commitli urun")
    # 🔴 FIKSTUR AYIRT EDICI OLMAK ZORUNDA: agac commit'ten SAPMALI, yoksa iki kaynak
    # ayni sonucu verir ve eksen sessizce olculmez olur ([[fikstur-degeri-mutasyon-koru]]).
    _katalog_yaz(depo_a, ["u-COMMITSIZ", "u-commitli", "u-taban"])
    rc_a, cikti_a, sure_a = push_et(depo_a)
    kyt_a = kayit_oku(kayit_a)
    dogrula("A0 push BASARILI (rc=0) — kanca yayini bloklamadi", rc_a == 0,
            "rc=%d %s" % (rc_a, cikti_a[-300:]))
    dogrula("A1 senkron FIILEN kostu (kayit yazildi) — 'hic kosmadi' mutanti burada duser",
            kyt_a is not None, "kayit YOK")
    if kyt_a:
        dogrula("A2 🔴 commit'lenmemis urun senkrona GIRMEDI (okunan: %s)" % kyt_a["idler"],
                "u-COMMITSIZ" not in kyt_a["idler"], str(kyt_a["idler"]))
        dogrula("A3 KONTROL AYAGI: commit'li urun GIRDI (senkron bos degil)",
                "u-commitli" in kyt_a["idler"] and "u-taban" in kyt_a["idler"],
                str(kyt_a["idler"]))
        dogrula("A4 kanca bayragi FIILEN gecirdi (argv=%s)" % kyt_a["argv"],
                "--head" in kyt_a["argv"], str(kyt_a["argv"]))
        dogrula("A5 kaynak beyani COMMIT'LI HEAD diyor (operator hangi agactan "
                "kostugunu GORUR): %s" % kyt_a["beyan"], "HEAD" in kyt_a["beyan"],
                kyt_a["beyan"])

    # KONTROL AYAGI 2 — ayni urun COMMIT'lenince senkrona GIRER (tek yon olculseydi
    # "hep bos senkronluyor" mutanti de gecerdi).
    os.unlink(kayit_a)
    _git(depo_a, "add", "urunler.json")
    _git(depo_a, "commit", "-q", "-m", "artik commitli")
    rc_a2, cikti_a2, _ = push_et(depo_a)
    kyt_a2 = kayit_oku(kayit_a)
    dogrula("A6 KONTROL: AYNI urun commit'lenip push edilince senkrona GIRDI",
            rc_a2 == 0 and kyt_a2 is not None and "u-COMMITSIZ" in kyt_a2["idler"],
            "rc=%d kayit=%s" % (rc_a2, kyt_a2 and kyt_a2["idler"]))

    # ══ B) KONTROL MUTANTI — bayrak sokulunce A KIRMIZI yanmali ══════════════════
    print("\n[B] KONTROL MUTANTI — cagridan bayrak sokulunce eksen KIRMIZI yaniyor mu?")
    ham = open(KANCA_KAYNAGI, encoding="utf-8").read()
    mutant = ham.replace('if python3 "$sync" "$@"; then', 'if python3 "$sync"; then')
    dogrula("B0 mutasyon FIILEN uygulandi (govde degisti) — uygulanmayan mutant "
            "'oldurulmus' sanilirdi", mutant != ham,
            "cagri satiri bulunamadi: 'if python3 \"$sync\" \"$@\"; then'")
    depo_b, kayit_b = fikstur_kur(tmp, "b", kanca_govdesi=mutant)
    _katalog_yaz(depo_b, ["u-commitli", "u-taban"])
    _git(depo_b, "add", "urunler.json")
    _git(depo_b, "commit", "-q", "-m", "commitli urun")
    _katalog_yaz(depo_b, ["u-COMMITSIZ", "u-commitli", "u-taban"])
    rc_b, _cikti_b, _ = push_et(depo_b)
    kyt_b = kayit_oku(kayit_b)
    dogrula("B1 🔴 MUTANT: bayraksiz cagri commit'lenmemis urunu senkrona SOKUYOR "
            "(eski kusur birebir ureriyor) — A2 bu mutantta KIRMIZI yanardi",
            rc_b == 0 and kyt_b is not None and "u-COMMITSIZ" in kyt_b["idler"],
            "rc=%d kayit=%s" % (rc_b, kyt_b and kyt_b["idler"]))
    dogrula("B2 MUTANTTA argv BOS (bayrak fiilen kaybolmus)",
            kyt_b is not None and kyt_b["argv"] == [], str(kyt_b and kyt_b["argv"]))

    # ══ C) KOPRU — push edilen sha HEAD DEGIL (`git push origin dal:main`) ════════
    print("\n[C] KOPRU — push edilen sha HEAD degil: `--head` YANLIS agaci okurdu")
    depo_c, kayit_c = fikstur_kur(tmp, "c")
    _git(depo_c, "checkout", "-q", "-b", "dal")
    _katalog_yaz(depo_c, ["u-DALDA", "u-taban"])
    _git(depo_c, "add", "urunler.json")
    _git(depo_c, "commit", "-q", "-m", "dal urunu")
    _git(depo_c, "checkout", "-q", "main")              # HEAD = main (u-DALDA YOK)
    _katalog_yaz(depo_c, ["u-COMMITSIZ", "u-taban"])    # agac ayrica KIRLI
    rc_c, cikti_c, _ = push_et(depo_c, "origin", "dal:main")
    kyt_c = kayit_oku(kayit_c)
    dogrula("C0 push BASARILI (rc=0)", rc_c == 0, "rc=%d %s" % (rc_c, cikti_c[-300:]))
    dogrula("C1 senkron kostu ve PUSH EDILEN commit'i okudu (u-DALDA VAR)",
            kyt_c is not None and "u-DALDA" in kyt_c["idler"],
            str(kyt_c and kyt_c["idler"]))
    dogrula("C2 🔴 KIRLI AGAC yine GIRMEDI (u-COMMITSIZ YOK)",
            kyt_c is not None and "u-COMMITSIZ" not in kyt_c["idler"],
            str(kyt_c and kyt_c["idler"]))
    dogrula("C3 bu kolda kanca `--kaynak` kullandi (`--head` HEAD=main'i okurdu, "
            "u-DALDA'yi KACIRIRDI): argv=%s" % (kyt_c and kyt_c["argv"]),
            kyt_c is not None and "--kaynak" in kyt_c["argv"] and
            "--head" not in kyt_c["argv"], str(kyt_c and kyt_c["argv"]))

    # ══ D) FAIL-CLOSED — kaynak cozulemezse senkron KOSMAZ, agaca DUSMEZ ══════════
    print("\n[D] FAIL-CLOSED — push edilen commit'ten katalog cikarilamazsa")
    depo_d, kayit_d = fikstur_kur(tmp, "d")
    _git(depo_d, "rm", "-q", "urunler.json")
    _git(depo_d, "commit", "-q", "-m", "katalog silindi")
    _katalog_yaz(depo_d, ["u-AGACTA-KALDI"])            # agacta HALA katalog var
    rc_d, cikti_d, _ = push_et(depo_d)
    kyt_d = kayit_oku(kayit_d)
    dogrula("D1 🔴 kaynak cozulemedi -> senkron CALISMA AGACINA DUSMEDI (kayit YOK)",
            kyt_d is None, str(kyt_d and kyt_d["idler"]))
    dogrula("D2 fail-closed kol push'u BLOKLAMADI (bu blok fail-open'dir, rc=0)",
            rc_d == 0, "rc=%d %s" % (rc_d, cikti_d[-300:]))

    # D3 — KOPRU kolunun fail-closed'i (kancanin KENDI kodu; D1 d1-sync'in kodu).
    depo_d2, kayit_d2 = fikstur_kur(tmp, "d2")
    _git(depo_d2, "checkout", "-q", "-b", "dal2")
    _git(depo_d2, "rm", "-q", "urunler.json")
    _git(depo_d2, "commit", "-q", "-m", "dalda katalog silindi")
    _git(depo_d2, "checkout", "-q", "main")
    _katalog_yaz(depo_d2, ["u-AGACTA-KALDI"])
    rc_d2, cikti_d2, _ = push_et(depo_d2, "origin", "dal2:main")
    kyt_d2 = kayit_oku(kayit_d2)
    dogrula("D3 KOPRU kolu da fail-closed: kayit YOK ve kanca ATLANDI gerekcesini BASTI",
            kyt_d2 is None and "D1 SENKRONU ATLANDI" in cikti_d2,
            "rc=%d kayit=%s cikti=%s" % (rc_d2, kyt_d2, cikti_d2[-300:]))
    dogrula("D4 KOPRU fail-closed kolu push'u BLOKLAMADI (rc=0)", rc_d2 == 0,
            "rc=%d" % rc_d2)

    # ══ E) SURE TAVANI — fail-slow = fail-open ═══════════════════════════════════
    print("\n[E] SURE — asili kalan kol iptal edilir, kapi HIC olculmez")
    en_uzun = max(s for _d, s in sureler) if sureler else 0.0
    dogrula("E1 her gercek push <= %.0f sn (olculen en uzun: %.1f sn, %d push)"
            % (SURE_TAVANI, en_uzun, len(sureler)), en_uzun <= SURE_TAVANI,
            "%.1f sn" % en_uzun)

    # ══ F) KAYNAK CAPASI (ucuz, yapisal) ═════════════════════════════════════════
    print("\n[F] KAYNAK CAPASI — izlenen kanca kaynagi")
    dogrula("F1 izlenen kaynakta HER IKI kol da var (--head + --kaynak)",
            "--head" in ham and "--kaynak" in ham)
    dogrula("F2 bayat beyan yok: eski 'calisma agacindaki urunler.json'u okur' NOTU "
            "kaldirilmis", "calisma agacindaki urunler.json'u okur" not in ham)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nNE OLCULMEDI (beyan):")
print("  1. CANLI D1: sentetik depodaki d1-sync bir KAYIT stub'idir (kaynak secimini")
print("     GERCEK kaynak_coz()'e delege eder, ama D1'e YAZMAZ). Yazma yolunun kendisi")
print("     tools/d1-kaynak-test.py + tools/d1-sync-durum-test.py eksenlerindedir.")
print("  2. Kancanin ON kapilari (ci-kapsam, gecmis-geri-donus) burada STUB'dir; onlarin")
print("     kablolamasi tools/kanca-kablolama-nobeti.py'de olculur.")
print("  3. Kurulu kopyanin izlenen kaynakla ayni olmasi burada olculmez -> ")
print("     tools/kanca-nobeti.py + kanca-kur.py --tazele.")

print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
sys.exit(1 if kalan[0] else 0)
