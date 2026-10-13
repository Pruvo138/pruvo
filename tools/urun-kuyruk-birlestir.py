#!/usr/bin/env python3
"""urun-kuyruk-birlestir.py — `urun-kuyruk` dalini saatte 1 main'e alan karar+icra araci.

NEDEN VAR (12 Eki 2026, BaBa "YAYIN ACLIGI" hukmu): urun push'lari 4-5 dk arayla main'e
iniyordu; deploy.yml (`concurrency: pages`) bekleyen kosumu her yeni push'ta iptal etti
(son 7 kosumun 6'si cancelled) ve `d1-sync --adim` DELETE'i ucta hic kosamadi -> silinen
12 urun D1'de yayinda=1 kaldi. Urun verisi artik `urun-kuyruk` dalina gider; bu arac
(.github/workflows/urun-kuyruk.yml, saatte 1) onu main'e alir -> urunden dogan Pages <=1/saat.

KARAR SIRASI (her sonuc TEK cikti satiri, `KUYRUK=` ile baslar):
  0. kuyruk dali yok -> KUYRUK=BOS sebep=dal-yok rc0 (Pages anlamsiz; fetch yok).
  1. fetch + main/kuYRUK SHA. kuyruk main'in gerisinde/ata -> KUYRUK=BOS sebep=geride rc0.
  2. deploy.yml'in bitmemis kosumu VAR + kuyruk en eski merge-disiniz commit YASI < ACIK_DK
     -> KUYRUK=BEKLE rc0 (git'e HIC dokunulmaz). YAS >= ACIK_DK ise BEKLE ATLANIR: bu
     "aclik" kolu, kuyruk Pages sebebiyle saatlerce beklemis olmasin (13 Eki 2026 olay
     detay: ~70 dk); aclik=1 bekleme_dk=<n> BIRLESTI/DISPATCH-HATA satirinin SONUNA eklenir.
  3. main kuyrugun atasi -> aday = kuyruk ucu (ff); degilse aday = main + kuyruk merge
     commit'i (ilk ebeveyn main). Cakisma -> abort, KUYRUK=CAKISMA rc1 (main degismez).
  4. kuyrugun main'e getirecegi NET fark ya da tek tek merge-disi commit'leri
     IZINLI_YOLLAR disina cikiyor -> KUYRUK=RED sebep=yabanci-yol rc1 (main degismez).
  4b. (K441) aday'da YENI olan bir `parametrik:true` kayit icin `jenerator/urunler/<id>.json`
     ADAY AGACINDA yoksa -> KUYRUK=RED sebep=semasiz-parametrik ids=<...> rc1 (main degismez).
     Kural tools/parametrik_sema.py'de (denetim-kapisi KAPI 12 ile TEK KAYNAK). Kuyruk yalniz
     urunler.json tasir (sema = kod, yabanci-yol RED) -> SIRA: ONCE sema main'e, SONRA kayit
     kuyruga; sema main'e inene dek kaydi kuyruga SOKMA.
  5. aday main'e ff push (force YOK). Non-ff red (yaris) -> taze fetch, TUM karar BIR KEZ
     daha (Pages kontrolu dahil); ikinci red -> KUYRUK=YARIS rc1.
  6. push-tetikli is akislari workflow_dispatch ile atesler (GITHUB_TOKEN push'u `push`
     tetigini CALISTIRMAZ — emsal tools/panel-uygulayici.py::deploy_tetikle; deploy.yml
     `on.push: branches: [main]` var, ama GITHUB_TOKEN push'u tetiklemez; bu yuzden aclik
     kolu Pages kosarken de dispatch EDER, `pages` concurrency + cancel-in-progress:false
     calisan kosumu BITIRIR, bizim dispatches SIRAYA girer). Liste .github/workflows'tan
     TURETILIR (dispatch_listesi); dispatch hatasi -> rc1.
  7. kuyruk dali adaya ff ile esitlenir (en iyi caba; red -> KUYRUK_SENKRON=ATLANDI, rc
     degismez: kuyruk main'in atasi kalir, sonraki tur BOS ya da yeniden merge eder).
     Main kuyruktan ONCE itilir: kuyruga giden ref main'in degisikliklerini (ornegin
     .github/workflows) tasiyabilir ve GITHUB_TOKEN'in `workflows` izni yoktur; o red
     main'i asla durdurmamali.

PROVA KORUMASI: is-akisi-kapisi K80 yeni CI adimini (bu araci) pre-push'ta ve CI'da gecici
agacta KOSTURUR (`PRUVO_K80_IC_KOSUM=1`) -> o kosum KUYRUK=PROVA rc0 ile hicbir sey yapmadan
doner. Gercek icra yalniz GITHUB_WORKFLOW == IS_AKISI_ADI iken (ya da test kokunde) olur;
baska her baglam KUYRUK=RED sebep=baglam-disi rc1 (yerelde yanlislikla kosup main'e itmez).

ORTAM: PRUVO_KUYRUK_GH / PRUVO_KUYRUK_GIT sahte ikili (test, AG YOK) ·
PRUVO_KUYRUK_TEST_KOK git islemlerinin yapildigi gecici klon (test modu) ·
PRUVO_KUYRUK_DEPO is akisi + yaml-oku kaynagi (varsayilan: bu dosyanin deposu).
Kabul: tools/urun-kuyruk-test.py (nobet.yml serit-b).
"""
import importlib.util
import json
import os
import subprocess
import sys
import time

DEPO = os.environ.get("PRUVO_KUYRUK_DEPO") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
GH = os.environ.get("PRUVO_KUYRUK_GH", "gh")
GIT = os.environ.get("PRUVO_KUYRUK_GIT", "git")
TEST_KOK = os.environ.get("PRUVO_KUYRUK_TEST_KOK", "")

IS_AKISI_ADI = "Urun kuyrugu birlestirici"
UZAK = "origin"
MAIN = "main"
KUYRUK = "urun-kuyruk"
PAGES_IS_AKISI = "deploy.yml"
# KUYRUK ACLIGI esigi (dk). Pages kosarken kuyruktaki en eski merge-disiniz commit bu
# kadar eski ise BEKLE yerine birleştirici DEVAM eder (13 Eki 2026, olay: kuyruk ucu
# 06:26'da geldi, Pages 06:26 + 06:57 kosumlarinda iptal yerine surdu, birlestiik 07:35
# = ~70 dk aclik). PRUVO_KUYRUK_ACLIK_DK ortam degiskeni ile test kapsaminda dusurulebilir.
ACIK_DK = int(os.environ.get("PRUVO_KUYRUK_ACLIK_DK", "45"))  # MUTANT-CAPA:ESIK
# Urun verisi yollari — OLCULDU (12 Eki, `git log origin/main --since=2026-09-20
# --no-merges --grep=^urun --name-only`): 46 urun commit'i yalniz bu iki yolu degistirdi
# (urunler.json 44 · arsiv/urunler-arsiv.json 2). Gorsel R2'de, git'e girmez; SEO/sitemap
# CI'da uretilir. Bunun disindaki her yol KOD'dur ve kuyruktan main'e GECMEZ.
IZINLI_YOLLAR = frozenset({"urunler.json", "arsiv/urunler-arsiv.json"})
# Push-tetikli ama BILEREK dispatch EDILMEYEN is akislari (gerekce ZORUNLU).
DISPATCH_HARIC = {
    "nobet.yml": ("dispatch kolu her kosuma KENDI concurrency grubunu verir "
                  "(github.run_id) -> saatte bir ~93 dk SERIT B kosumu = G9 maliyet sinifi; "
                  "`47 */4` schedule kolu urun verisini zaten kapsar"),
    "urun-kuyruk.yml": ("KENDISI — push tetigi `urun-kuyruk` dalinda (main'de DEGIL); "
                        "dispatch kendini atesleme dongusu olurdu"),
}
BITMEMIS = {"queued", "in_progress", "waiting", "requested", "pending"}
KIMLIK = ["-c", "user.name=urun-kuyruk", "-c", "user.email=urun-kuyruk@pruvo3d.com",
          "-c", "commit.gpgsign=false"]


class Dur(Exception):
    def __init__(self, satir, rc):
        super().__init__(satir)
        self.satir, self.rc = satir, rc


def git(*args, kontrol=True):
    p = subprocess.run([GIT, "-C", TEST_KOK or DEPO] + list(args),
                       capture_output=True, text=True)
    if kontrol and p.returncode != 0:
        raise Dur("KUYRUK=OLCULEMEDI sebep=git-%s" % args[0], 2)
    return p


def gh(*args):
    depo = os.environ.get("GITHUB_REPOSITORY")
    return subprocess.run([GH] + list(args) + (["-R", depo] if depo else []),
                          capture_output=True, text=True)


def yaml_oku():
    spec = importlib.util.spec_from_file_location(
        "yaml_oku", os.path.join(DEPO, "tools", "yaml-oku.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dispatch_listesi():
    """(dispatch, atlanan) — push tetikli is akislari .github/workflows'tan TURETILIR.
    urun-kuyruk.yml DISINDA depodaki her `push` tetigi `branches: [main]`dir (batarya
    V15 bunu dispatch edilen her dosyanin METNINDE capraz olcer); dispatch `--ref main`.
    workflow_dispatch'i olmayan push is akisi atesLENEMEZ -> atlanan (sebep yazilir)."""
    yo = yaml_oku()
    dizin = os.path.join(DEPO, ".github", "workflows")
    dispatch, atlanan = [], []
    for ad in sorted(os.listdir(dizin)):
        if not ad.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(dizin, ad), encoding="utf-8") as f:
            tetik, hata = yo.tetikleyiciler(f.read())
        if hata:
            raise Dur("KUYRUK=OLCULEMEDI sebep=yaml-%s" % ad, 2)
        if "push" not in tetik:
            continue
        if ad in DISPATCH_HARIC:
            atlanan.append("%s(haric)" % ad)
        elif "workflow_dispatch" not in tetik:
            atlanan.append("%s(dispatch-yok)" % ad)
        else:
            dispatch.append(ad)
    if PAGES_IS_AKISI not in dispatch:
        raise Dur("KUYRUK=OLCULEMEDI sebep=pages-dispatch-turetilemedi", 2)
    # Pages ONCE atesler (urun verisinin canliya cikan tek yolu).
    dispatch.sort(key=lambda a: a != PAGES_IS_AKISI)
    return dispatch, atlanan


def pages_bitmemis():
    p = gh("run", "list", "--workflow", PAGES_IS_AKISI, "--limit", "20",
           "--json", "status,databaseId")
    if p.returncode != 0:
        raise Dur("KUYRUK=OLCULEMEDI sebep=gh-run-list", 2)
    try:
        kosumlar = json.loads(p.stdout or "[]")
    except ValueError:
        raise Dur("KUYRUK=OLCULEMEDI sebep=gh-json", 2)
    return [k for k in kosumlar if k.get("status") in BITMEMIS]


def ata_mi(a, b):
    return git("merge-base", "--is-ancestor", a, b, kontrol=False).returncode == 0


def kuyruk_yasi_dk():
    """origin/main..origin/urun-kuyruk'un en eski commit committer zamaninin YASI (dk).

    Origin refleri ONCESINDE fetch edilmis olmali (Pages kararindan onceki tek fetch
    bunu yapar). Hata/bos durumda 0 doner -> BEKLE yolu AYNI (güvenli yönde).
    `git log --format=%ct ... | tail -1`: log en yeniden en eskiye siralanir, tail -1
    EN ESKI commitin committer zaman damgasini verir.
    """
    try:
        satir = git("log", "--format=%ct",
                    "%s/%s..%s/%s" % (UZAK, MAIN, UZAK, KUYRUK),
                    kontrol=False).stdout.strip()
    except Dur:
        return 0
    if not satir:
        return 0
    try:
        en_eski = int(satir.split()[-1])
    except ValueError:
        return 0
    return max(0, (int(time.time()) - en_eski) // 60)


def yabanci_yollar(main_sha, aday, kuyruk_sha):
    """Net fark (main -> aday) VE kuyrugun tek tek merge-disi commit'leri izinli mi.
    Ikinci eksen: ekleyip geri alan commit net farkta gorunmez ama main tarihine girer."""
    net = git("diff", "--name-only", main_sha, aday).stdout.split()
    tek = git("log", "--no-merges", "--format=", "--name-only",
              "%s..%s" % (main_sha, kuyruk_sha)).stdout.split()
    return sorted(set(net + tek) - IZINLI_YOLLAR)


def _parametrik_sema_modulu():
    """Kural TEK KAYNAKTA (tools/parametrik_sema.py; denetim-kapisi KAPI 12 de onu cagirir)."""
    spec = importlib.util.spec_from_file_location(
        "parametrik_sema", os.path.join(DEPO, "tools", "parametrik_sema.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parametrikler(sha):
    """`sha` agacindaki urunler.json'da parametrik kayitlar -> {id: kayit}.
    Okunamaz/ayristirilamaz/liste degil -> OLCULEMEDI rc2 (belirsizlik 'sema var' DEMEZ)."""
    p = git("show", "%s:urunler.json" % sha, kontrol=False)
    if p.returncode != 0:
        raise Dur("KUYRUK=OLCULEMEDI sebep=urunler-json-okunamadi sha=%s" % sha[:12], 2)
    try:
        veri = json.loads(p.stdout)
    except ValueError:
        veri = None
    if not isinstance(veri, list):
        raise Dur("KUYRUK=OLCULEMEDI sebep=urunler-json-ayristirilamadi sha=%s" % sha[:12], 2)
    return {u.get("id"): u for u in veri if isinstance(u, dict) and u.get("parametrik")}


def semasiz_parametrikler(main_sha, aday):
    """K441: aday'da YENI olan (main'de parametrik OLMAYAN) parametrik kayitlardan sema dosyasi
    ADAY AGACINDA bulunmayanlar -> [(id, gerekce)]. Urun verisi (urunler.json) net farkta yoksa
    bakilmaz. Onceden main'de duran kayit (gecmis borc) TETIKLEMEZ — bu kapi ILERI-YONLUDUR.
    NEDEN BURADA: --commit-farki CI kapisi kaydi main'e GIRDIKTEN SONRA gorur ve sonraki commit
    'onceden var' sayar; kaydi main'e sokmadan durdurabilecek TEK nokta bu birlestiricidir."""
    if "urunler.json" not in git("diff", "--name-only", main_sha, aday).stdout.split():
        return []
    onceki = _parametrikler(main_sha)
    yeni = _parametrikler(aday)
    yeni_idler = {i for i in yeni if i not in onceki}
    if not yeni_idler:
        return []
    mod = _parametrik_sema_modulu()
    return mod.semasizlar(
        [yeni[i] for i in yeni_idler],
        lambda yol: git("cat-file", "-e", "%s:%s" % (aday, yol), kontrol=False).returncode == 0)


def tur(dispatch):
    """Tek karar+icra turu. Doner: (satir, rc) ya da "YARIS"."""
    # Kuyruk yoksa Pages anlamsiz (fetch de anlamsiz) — dogrudan BOS.
    if not git("ls-remote", "--heads", UZAK, KUYRUK).stdout.strip():
        return "KUYRUK=BOS sebep=dal-yok", 0
    git("fetch", "--quiet", UZAK,
        "+refs/heads/%s:refs/remotes/%s/%s" % (MAIN, UZAK, MAIN),
        "+refs/heads/%s:refs/remotes/%s/%s" % (KUYRUK, UZAK, KUYRUK))
    main_sha = git("rev-parse", "%s/%s" % (UZAK, MAIN)).stdout.strip()
    kuyruk_sha = git("rev-parse", "%s/%s" % (UZAK, KUYRUK)).stdout.strip()
    if ata_mi(kuyruk_sha, main_sha):
        return "KUYRUK=BOS sebep=geride", 0  # MUTANT-CAPA:BOS
    aclik_bilgi = ""
    bitmemis = pages_bitmemis()
    if bitmemis:  # MUTANT-CAPA:ACIK
        yas_dk = kuyruk_yasi_dk()
        if yas_dk < ACIK_DK:
            return "KUYRUK=BEKLE pages=%s" % bitmemis[0].get("databaseId"), 0
        aclik_bilgi = " aclik=1 bekleme_dk=%d" % yas_dk
    if ata_mi(main_sha, kuyruk_sha):
        aday, yol = kuyruk_sha, "ff"
    else:
        git("checkout", "--quiet", "--detach", main_sha)
        m = git(*KIMLIK, "merge", "--no-ff", "--no-edit", "-m",
                "urun-kuyruk: %s -> %s birlestirme" % (KUYRUK, MAIN), kuyruk_sha,
                kontrol=False)
        if m.returncode != 0:
            git("merge", "--abort", kontrol=False)
            return "KUYRUK=CAKISMA main=%s kuyruk=%s" % (main_sha[:12], kuyruk_sha[:12]), 1
        aday, yol = git("rev-parse", "HEAD").stdout.strip(), "merge"
    yabanci = yabanci_yollar(main_sha, aday, kuyruk_sha)
    if yabanci:  # MUTANT-CAPA:YOL
        return "KUYRUK=RED sebep=yabanci-yol yollar=%s" % ",".join(yabanci[:5]), 1
    semasiz = semasiz_parametrikler(main_sha, aday)
    if semasiz:  # MUTANT-CAPA:SEMA
        return "KUYRUK=RED sebep=semasiz-parametrik ids=%s" % ",".join(
            str(i) for i, _ in semasiz[:5]), 1
    p = git("push", "--porcelain", UZAK, "%s:refs/heads/%s" % (aday, MAIN), kontrol=False)
    if p.returncode != 0:
        # Yalniz non-ff red YARIS'tir; yetki/ag hatasi tekrar denenmez (OLCULEMEDI).
        cikti = p.stdout + p.stderr
        if "[rejected]" in cikti or "non-fast-forward" in cikti or "fetch first" in cikti:
            return "YARIS"
        return "KUYRUK=OLCULEMEDI sebep=git-push main=%s" % main_sha[:12], 2
    hatali = [ad for ad in dispatch if gh("workflow", "run", ad, "--ref", MAIN).returncode != 0]
    if aday != kuyruk_sha:
        s = git("push", "--porcelain", UZAK, "%s:refs/heads/%s" % (aday, KUYRUK), kontrol=False)
        if s.returncode != 0:
            print("KUYRUK_SENKRON=ATLANDI (kuyruk main'in atasi kaldi; sonraki tur birlestirir)")
    if hatali:
        return ("KUYRUK=DISPATCH-HATA sha=%s is-akisi=%s (main itildi, yayin TETIKLENMEDI)%s"
                % (aday[:12], ",".join(hatali), aclik_bilgi)), 1
    return "KUYRUK=BIRLESTI sha=%s yol=%s dispatch=%s%s" % (
        aday[:12], yol, ",".join(dispatch), aclik_bilgi), 0


def calis():
    if os.environ.get("PRUVO_K80_IC_KOSUM"):
        return "KUYRUK=PROVA (K80 ic kosumu: hicbir sey yapilmadi)", 0
    if not TEST_KOK and os.environ.get("GITHUB_WORKFLOW") != IS_AKISI_ADI:
        return "KUYRUK=RED sebep=baglam-disi (yalniz '%s' is akisinda icra eder)" % IS_AKISI_ADI, 1
    dispatch, atlanan = dispatch_listesi()
    if atlanan:
        print("KUYRUK_DISPATCH_ATLANAN=%s" % ",".join(atlanan))
    for deneme in (1, 2):
        sonuc = tur(dispatch)
        if sonuc != "YARIS":
            return sonuc
        print("KUYRUK_YARIS deneme=%d: main push'u reddedildi, taze fetch ile yeniden" % deneme)
    return "KUYRUK=YARIS (iki deneme de reddedildi; main degismedi)", 1


def main():
    try:
        satir, rc = calis()
    except Dur as d:
        satir, rc = d.satir, d.rc
    print(satir)
    ozet = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet and not TEST_KOK:
        with open(ozet, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
