#!/usr/bin/env python3
"""panel-uygulayici.py — panel_ustyazim KUYRUGUNU urunler.json TABANINA isleyen TEK uygulayici.

TASARIM (mimar hakem hukmu, 29 Agu 2026 — kutu ~00:1xZ blogu):
  * Panel (yonetim ekrani "Urunler" sekmesi) urunler.json'a ASLA yazmaz; D1
    `panel_ustyazim` tablosuna hal='beklemede' SATIR yazar (yazma KUYRUGU).
  * Git'e yazan TEK kol BU ARACTIR ve yalniz CI'da kosar
    (.github/workflows/panel-uygulayici.yml, concurrency=1). Ikinci bir merge
    noktasi (kenar-yeniden-yazim / public ustyazim ucu) BILEREK YOKTUR.
  * Taban yazimi `tools/duzelt.py --toplu` uzerinden gider — mevcut urunu
    degistirmenin TEK mesru yolu odur; guard izin manifesti, aciklama olcu-satiri
    korumasi, uyum/marka turetimi ve ticari-hal kurallari ORADAN miras alinir
    (ikinci kopya yazilmadi).
  * urunler.json TEK okuma kaynagi KALIR: site fiyati/JSON-LD, uygulayicinin
    commit'i push'lanip Build & deploy kosunca TABANDAN dogar.

ALAN BEYAZ LISTESI UYGULAYICININ ICINDEDIR (ayri bir kapida degil — hakem hukmu):
  fiyat | baslik | aciklama. Gizli alanlar (kaynak link, uyelik, STL yeri) bu
  kuyruktan tabana HICBIR yoldan inmez. Parametrik (sari seri) urunun fiyati BOS
  kalir (taban fiyat semadan gelir) -> fiyat ustyazimi REDDEDILIR.

HAL UC DEGERLIDIR: beklemede -> islendi | hata(sebep). Islenemeyen satir SESSIZCE
dusmez; sebep adiyla satira yazilir ve panel kuyruk gorunumunde gorunur.

SIRA (crash-guvenli, en-az-bir-kez + idempotent):
  oku -> sinifla -> hatalari damgala -> duzelt --toplu -> commit -> PUSH ->
  islendi damgala. Push'tan ONCE hicbir satir islendi OLMAZ; push sonrasi damga
  yarim kalirsa satirlar beklemede kalir, bir sonraki kosum ayni degeri yeniden
  uygular (diff bos -> commit yok) ve damgayi tamamlar.

KIPLER:
  --uygula        CI kosum kipi. Secret yoksa (K80 is-akisi probu dahil) exit 0,
                  hicbir sey okumaz/yazmaz — bu bir kapi degil AKTUATORDUR,
                  "secret yok" ariza degil "is yok" demektir.
  --durum         Salt-okuma: kuyruk sayilari (hal kirilimi).
  --kendini-test  Offline kabul: sentetik git deposu (duzelt-toplu-test.sahte_repo
                  TEK KAYNAK fiksturu) + sqlite kuyruk + 2 mutant + KONTROL.

TEST DIKISLERI (canli kosumda KAPALI, acilirsa GURULTULU basilir):
  PANEL_UYG_TEST_SQLITE=<yol>  D1 yerine yerel sqlite dosyasi (D1 zaten SQLite'tir).
  PANEL_UYG_KOK=<yol>          repo koku yerine fikstur agaci.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request

ARAC_YOLU = os.path.abspath(__file__)
VARSAYILAN_KOK = os.path.dirname(os.path.dirname(ARAC_YOLU))
SEMA_DOSYASI = os.path.join(os.path.dirname(ARAC_YOLU), "panel-ustyazim-sema.sql")

# Beyaz liste + deger kurallari — OTORITE BURADADIR. Worker (shop/src/yonet.js)
# ayni kurali erken-uyari olarak uygular; ayrisirsa satir burada hal='hata' olur,
# yani drift sessiz kalamaz (gorunur yuzey: panel kuyruk ekrani + bu aracin cikti
# satiri).
ALAN_BEYAZ_LISTESI = ("fiyat", "baslik", "aciklama")
# Katalog fiyat sozlesmesi "N TL" (olculdu 30 Agu: 30626/31264 kayit bu bicimde;
# legacy "N.N TL" YENI yazima acilmaz — kanonik bicime yakinsansin).
FIYAT_BICIMI = re.compile(r"^[1-9][0-9]{0,5} TL$")
DEGER_TAVANI = {"fiyat": 20, "baslik": 200, "aciklama": 4000}
KONTROL_KARAKTERI = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def simdi_utc():
    # UTC ZORUNLU — gun/saat anahtarini yerel saatten alan sayac gecede sahte
    # sifir basar (onarim-durum vakasi, 28 Agu).
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── kuyruk erisimi: canli (wrangler, d1-sync istemcisi) / test (sqlite) ─────────

KUYRUK_KOLONLARI = "id, urun_id, alan, deger, yazan, ts"


class TabloYok(Exception):
    pass


class WranglerKuyruk:
    """Canli D1. Istemci d1-sync.py'den IMPORT edilir (ikinci wrangler kopyasi yok)."""

    def __init__(self, kok):
        self.d1 = _modul_yukle(os.path.join(kok, "tools", "d1-sync.py"), "pruvo_d1_sync")

    def _sorgu(self, sql):
        try:
            return self.d1.sorgu(sql)
        except SystemExit as e:
            if "no such table" in str(e):
                raise TabloYok(str(e))
            raise

    def beklemede_oku(self):
        r = self._sorgu("SELECT %s FROM panel_ustyazim WHERE hal='beklemede' ORDER BY id"
                        % KUYRUK_KOLONLARI)
        satirlar = []
        for blok in r:
            satirlar.extend((blok.get("results") or []))
        return satirlar

    def sayilar(self):
        r = self._sorgu("SELECT hal, COUNT(*) AS adet FROM panel_ustyazim GROUP BY hal")
        cikti = {}
        for blok in r:
            for s in (blok.get("results") or []):
                cikti[s["hal"]] = s["adet"]
        return cikti

    def damgala(self, kayitlar):
        # kayitlar: [(id, hal, sebep|None, commit|None)] — tek --file kosumu.
        if not kayitlar:
            return
        q = self.d1.q
        ts = simdi_utc()
        sql = []
        for kid, hal, sebep, commit in kayitlar:
            sql.append(
                "UPDATE panel_ustyazim SET hal=%s, sebep=%s, islendi_ts=%s,"
                " islendi_commit=%s WHERE id=%d AND hal='beklemede';"
                % (q(hal), q(sebep), q(ts), q(commit), int(kid)))
        self.d1.dosya_calistir("\n".join(sql))


class SqliteKuyruk:
    """Test dikisi: ayni SQL semantigi (D1 = SQLite) yerel dosyada."""

    def __init__(self, yol):
        print("PANEL_UYGULAYICI: TEST KIPI (sqlite=%s) — canli D1'e DOKUNULMUYOR" % yol)
        self.db = sqlite3.connect(yol)
        self.db.row_factory = sqlite3.Row

    def beklemede_oku(self):
        try:
            r = self.db.execute("SELECT %s FROM panel_ustyazim WHERE hal='beklemede'"
                                " ORDER BY id" % KUYRUK_KOLONLARI)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                raise TabloYok(str(e))
            raise
        return [dict(s) for s in r.fetchall()]

    def sayilar(self):
        r = self.db.execute("SELECT hal, COUNT(*) AS adet FROM panel_ustyazim GROUP BY hal")
        return {s["hal"]: s["adet"] for s in r.fetchall()}

    def damgala(self, kayitlar):
        ts = simdi_utc()
        for kid, hal, sebep, commit in kayitlar:
            self.db.execute(
                "UPDATE panel_ustyazim SET hal=?, sebep=?, islendi_ts=?,"
                " islendi_commit=? WHERE id=? AND hal='beklemede'",
                (hal, sebep, ts, commit, int(kid)))
        self.db.commit()


def kuyruk_ac(kok):
    test_db = os.environ.get("PANEL_UYG_TEST_SQLITE")
    if test_db:
        return SqliteKuyruk(test_db)
    return WranglerKuyruk(kok)


# ── git yardimcilari ─────────────────────────────────────────────────────────────

def git(kok, args, kontrol=True):
    p = subprocess.run(["git", "-C", kok] + args, capture_output=True, text=True)
    if kontrol and p.returncode != 0:
        raise RuntimeError("git %s rc=%d\n%s" % (" ".join(args), p.returncode,
                                                 (p.stdout + p.stderr)[-800:]))
    return p


def uca_tazele(kok):
    git(kok, ["fetch", "origin", "main"])
    git(kok, ["checkout", "-q", "-B", "main", "FETCH_HEAD"])


# ── siniflama ────────────────────────────────────────────────────────────────────

def satir_sebebi(satir, katalog):
    """Gecersizse sebep dizesi, gecerliyse None. Kurallarin TEK kaynagi burasi."""
    alan = satir.get("alan")
    deger = satir.get("deger")
    uid = satir.get("urun_id")
    if alan not in ALAN_BEYAZ_LISTESI:
        return "ALAN_BEYAZ_LISTE_DISI"
    if not isinstance(deger, str) or not deger.strip():
        return "DEGER_BOS"
    if len(deger) > DEGER_TAVANI[alan]:
        return "DEGER_UZUN"
    kontrol_metni = deger.replace("\n", "") if alan == "aciklama" else deger
    if "\n" in kontrol_metni or KONTROL_KARAKTERI.search(deger):
        return "DEGER_KONTROL_KARAKTERI"
    if alan == "fiyat" and not FIYAT_BICIMI.match(deger):
        return "FIYAT_BICIMI"
    kayit = katalog.get(uid)
    if kayit is None:
        return "URUN_YOK"
    if alan == "fiyat" and kayit.get("parametrik") is True:
        # Sari seri: fiyat BOS kalir, taban fiyat semadan basilir (kapi zorlar).
        return "PARAMETRIK_FIYAT"
    return None


def sinifla(satirlar, katalog):
    """(uygulanacak[satir], hata[(satir, sebep)], zaten_esit[satir]) doner.
    Ayni (urun_id, alan) icin EN YENI satir kazanir; eskisi hata kovasina
    YERINE_YENISI:<id> ile duser (uygulanmadigi halde 'islendi' DENMEZ)."""
    en_yeni = {}
    for s in satirlar:
        anahtar = (s.get("urun_id"), s.get("alan"))
        if anahtar not in en_yeni or int(s["id"]) > int(en_yeni[anahtar]["id"]):
            en_yeni[anahtar] = s
    uygulanacak, hata, zaten_esit = [], [], []
    for s in satirlar:
        kazanan = en_yeni[(s.get("urun_id"), s.get("alan"))]
        if int(s["id"]) != int(kazanan["id"]):
            hata.append((s, "YERINE_YENISI:%d" % int(kazanan["id"])))
            continue
        sebep = satir_sebebi(s, katalog)
        if sebep:
            hata.append((s, sebep))
        elif katalog[s["urun_id"]].get(s["alan"]) == s["deger"]:
            zaten_esit.append(s)
        else:
            uygulanacak.append(s)
    return uygulanacak, hata, zaten_esit


# ── taban yazimi (duzelt --toplu) ───────────────────────────────────────────────

def duzelt_kos(kok, islemler):
    """tools/duzelt.py --toplu; (rc, cikti) doner. Taban yaziminin TEK yolu."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(islemler, f, ensure_ascii=False)
        yol = f.name
    try:
        p = subprocess.run([sys.executable, os.path.join(kok, "tools", "duzelt.py"),
                            "--toplu", yol], cwd=kok, capture_output=True, text=True)
        return p.returncode, (p.stdout + p.stderr)
    finally:
        os.unlink(yol)


def tabana_isle(kok, uygulanacak, hata):
    """duzelt --toplu; toplu RED olursa satir satir daralt (tek bozuk satir tum
    kuyrugu KILITLEMESIN — atomiklik duzelt'in kendi cagrisi duzeyinde kalir).
    Uygulanabilenlerin listesini dondurur; dusenler hata kovasina eklenir."""
    if not uygulanacak:
        return []
    islemler = [{"id": s["urun_id"], "alan": s["alan"], "deger": s["deger"]}
                for s in uygulanacak]
    rc, cikti = duzelt_kos(kok, islemler)
    if rc == 0:
        return list(uygulanacak)
    print("PANEL_UYGULAYICI: toplu duzelt rc=%d — satir satir daraltiliyor" % rc)
    uygulanan = []
    for s in uygulanacak:
        rc1, cikti1 = duzelt_kos(kok, [{"id": s["urun_id"], "alan": s["alan"],
                                        "deger": s["deger"]}])
        if rc1 == 0:
            uygulanan.append(s)
        else:
            ozet = " | ".join(cikti1.strip().splitlines()[-2:])[:180]
            hata.append((s, "DUZELT_RED:rc=%d %s" % (rc1, ozet)))
    return uygulanan


# ── deploy tetigi ────────────────────────────────────────────────────────────────

def deploy_tetikle():
    """GITHUB_TOKEN push'u deploy.yml'i TETIKLEMEZ (GitHub ozyineleme korumasi;
    istisna workflow_dispatch/repository_dispatch). Bu yuzden commit CI'dan
    itildiyse Build & deploy BURADAN workflow_dispatch ile cagrilir — yoksa fiyat
    main'e girer ama canliya HIC cikmazdi (sessiz sinif). Yerel push'ta gerek yok
    (push olayi zaten tetikler)."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return "YEREL_GEREKSIZ"
    jeton = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    depo = os.environ.get("GITHUB_REPOSITORY")
    if not jeton or not depo:
        return "JETON_YOK"
    istek = urllib.request.Request(
        "https://api.github.com/repos/%s/actions/workflows/deploy.yml/dispatches" % depo,
        data=json.dumps({"ref": "main"}).encode("utf-8"),
        headers={"Authorization": "Bearer " + jeton,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "pruvo-panel-uygulayici"},
        method="POST")
    try:
        with urllib.request.urlopen(istek, timeout=30) as c:
            return "GONDERILDI_%d" % c.status
    except Exception as e:
        return "HATA:%s" % str(e)[:120]


# ── ana akis ─────────────────────────────────────────────────────────────────────

def uygula():
    kok = os.environ.get("PANEL_UYG_KOK") or VARSAYILAN_KOK
    test_kipi = bool(os.environ.get("PANEL_UYG_TEST_SQLITE"))
    if test_kipi and os.environ.get("PANEL_UYG_KOK") is None:
        print("PANEL_UYGULAYICI: TEST kipinde PANEL_UYG_KOK zorunlu (gercek repoya yazilmaz)")
        return 2
    if not test_kipi and not (os.environ.get("CLOUDFLARE_API_TOKEN")
                              and os.environ.get("CLOUDFLARE_ACCOUNT_ID")):
        # Aktuator, kapi degil: secret'siz ortam (K80 is-akisi probu, yerel prova)
        # "is yok" demektir — hicbir sey okunmaz/yazilmaz, yesil cikilir.
        print("PANEL_UYGULAYICI: SECRET_YOK — okuma/yazma yapilmadi (rc=0)")
        return 0

    kuyruk = kuyruk_ac(kok)
    try:
        satirlar = kuyruk.beklemede_oku()
    except TabloYok:
        print("PANEL_UYGULAYICI: TABLO_YOK — sema kosulmamis (tools/panel-ustyazim-sema.sql); is yok")
        return 0
    if not satirlar:
        print("PANEL_UYGULAYICI: beklemede=0 — is yok")
        return 0

    uca_tazele(kok)
    taban_once = git(kok, ["rev-parse", "HEAD"]).stdout.strip()

    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        katalog = {u.get("id"): u for u in json.load(f)}

    uygulanacak, hata, zaten_esit = sinifla(satirlar, katalog)
    # Hata damgasi push'a BAGLI DEGIL — once yazilir ki bozuk satir kuyrugu tikamasin.
    kuyruk.damgala([(s["id"], "hata", sebep, None) for s, sebep in hata])

    commit_sha = None
    if uygulanacak:
        push_ok = False
        for deneme in range(3):
            if deneme:
                uca_tazele(kok)
                with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
                    katalog = {u.get("id"): u for u in json.load(f)}
                uygulanacak, ek_hata, ek_esit = sinifla(uygulanacak, katalog)
                kuyruk.damgala([(s["id"], "hata", sebep, None) for s, sebep in ek_hata])
                zaten_esit.extend(ek_esit)
            uygulanan = tabana_isle(kok, uygulanacak, hata)
            uygulanacak = uygulanan
            if not uygulanan:
                push_ok = True  # yazacak bir sey kalmadi; push gereksiz
                break
            fark = git(kok, ["diff", "--quiet", "--", "urunler.json"], kontrol=False)
            if fark.returncode == 0:
                push_ok = True
                break
            sayim = {}
            for s in uygulanan:
                sayim[s["alan"]] = sayim.get(s["alan"], 0) + 1
            ozet = " ".join("%s=%d" % (a, n) for a, n in sorted(sayim.items()))
            git(kok, ["add", "urunler.json"])
            # Kimlik bayragi: CI runner'inda global git kimligi yok; -c yereli asmaz.
            git(kok, ["-c", "user.email=panel@pruvo3d.com",
                      "-c", "user.name=panel-uygulayici", "commit", "-q", "-m",
                      "panel: %d ustyazim tabana islendi (%s)" % (len(uygulanan), ozet)])
            p = git(kok, ["push", "origin", "HEAD:main"], kontrol=False)
            if p.returncode == 0:
                commit_sha = git(kok, ["rev-parse", "HEAD"]).stdout.strip()
                push_ok = True
                break
            print("PANEL_UYGULAYICI: push reddi (deneme %d) — uca tazelenip yeniden"
                  % (deneme + 1))
        if not push_ok:
            # Satirlar BILEREK beklemede birakildi: islendi damgasi ancak push'tan
            # sonra atilir; bir sonraki kosum ayni degerleri yeniden uygular.
            print("PANEL_UYGULAYICI: PUSH_OLMADI — satirlar beklemede birakildi (rc=1)")
            return 1  # PUSH-OLMADI-KOLU

    hedef_commit = commit_sha or taban_once
    damga = [(s["id"], "islendi", None, hedef_commit) for s in uygulanacak]
    damga += [(s["id"], "islendi", "TABAN_ZATEN_ESIT", hedef_commit) for s in zaten_esit]
    kuyruk.damgala(damga)

    tetik = deploy_tetikle() if commit_sha else "COMMIT_YOK"
    print("PANEL_UYGULAYICI: beklemede=%d islendi=%d hata=%d commit=%s deploy_tetik=%s"
          % (len(satirlar), len(uygulanacak) + len(zaten_esit), len(hata),
             commit_sha or "-", tetik))
    if commit_sha and tetik.startswith("HATA"):
        # Commit main'de ama yayin tetigi dusmus: kirmizi GORUNUR olsun — fiyat
        # bir sonraki push/deploy'a kadar canliya cikmaz.
        return 1
    return 0


def durum():
    kok = os.environ.get("PANEL_UYG_KOK") or VARSAYILAN_KOK
    if not os.environ.get("PANEL_UYG_TEST_SQLITE") and not (
            os.environ.get("CLOUDFLARE_API_TOKEN")
            and os.environ.get("CLOUDFLARE_ACCOUNT_ID")):
        print("PANEL_UYGULAYICI: SECRET_YOK — durum OLCULEMEDI")
        return 2
    try:
        sayilar = kuyruk_ac(kok).sayilar()
    except TabloYok:
        print("PANEL_UYGULAYICI: TABLO_YOK — sema kosulmamis")
        return 2
    print("PANEL_UYGULAYICI durum: " + (" ".join(
        "%s=%d" % (h, sayilar.get(h, 0)) for h in ("beklemede", "islendi", "hata"))
        or "bos"))
    return 0


# ── kendini-test ─────────────────────────────────────────────────────────────────

def _fikstur_kur(tmp, katalog_ek=None):
    """Sentetik repo (duzelt-toplu-test.sahte_repo TEK KAYNAK) + gercek git +
    yerel bare uzak + sqlite kuyruk. (repo, bare, db_yolu) doner."""
    dt = _modul_yukle(os.path.join(VARSAYILAN_KOK, "tools", "duzelt-toplu-test.py"),
                      "pruvo_duzelt_toplu_test")
    katalog = json.loads(json.dumps(dt.KATALOG))
    katalog.append({"id": "test-parametrik", "kategori": "Jeneratör", "marka": [],
                    "baslik": "Test Parametrik", "aciklama": "olcuye ozel",
                    "fiyat": "", "parametrik": True, "gorseller": []})
    if katalog_ek:
        katalog.extend(katalog_ek)
    repo = os.path.realpath(dt.sahte_repo(katalog))  # realpath: sentetik git fiksturu sarti
    bare = os.path.realpath(tempfile.mkdtemp(prefix="panel-uyg-bare-", dir=tmp))
    subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
    for k in (["init", "-q"], ["config", "user.email", "test@pruvo.test"],
              ["config", "user.name", "panel-uyg-test"], ["add", "-A"],
              ["commit", "-q", "-m", "taban"], ["remote", "add", "origin", bare],
              ["push", "-q", "origin", "HEAD:main"]):
        subprocess.run(["git", "-C", repo] + k, check=True, capture_output=True)
    # Bare uzagin HEAD'i main'e cevrilir — yoksa `git clone` (V11 yaris fiksturu)
    # "remote HEAD refers to nonexistent ref" ile checkout'suz dusebilir.
    subprocess.run(["git", "-C", bare, "symbolic-ref", "HEAD", "refs/heads/main"],
                   check=True, capture_output=True)
    db = os.path.join(tmp, "kuyruk-%s.sqlite" % os.path.basename(repo))
    with open(SEMA_DOSYASI, encoding="utf-8") as f:
        sema = f.read()
    b = sqlite3.connect(db)
    b.executescript(sema)
    b.close()
    return repo, bare, db


def _satir_ekle(db, urun_id, alan, deger):
    b = sqlite3.connect(db)
    b.execute("INSERT INTO panel_ustyazim (urun_id, alan, deger, yazan, ts, hal)"
              " VALUES (?,?,?,?,?,'beklemede')",
              (urun_id, alan, deger, "test", simdi_utc()))
    b.commit()
    son = b.execute("SELECT MAX(id) FROM panel_ustyazim").fetchone()[0]
    b.close()
    return son


def _kuyruk_dok(db):
    b = sqlite3.connect(db)
    b.row_factory = sqlite3.Row
    r = [dict(s) for s in b.execute(
        "SELECT id, urun_id, alan, deger, hal, sebep, islendi_commit"
        " FROM panel_ustyazim ORDER BY id").fetchall()]
    b.close()
    return r


def _uygulayici_kos(arac, repo, db):
    ort = dict(os.environ)
    ort.pop("CLOUDFLARE_API_TOKEN", None)
    ort.pop("CLOUDFLARE_ACCOUNT_ID", None)
    ort.pop("GITHUB_ACTIONS", None)
    ort["PANEL_UYG_TEST_SQLITE"] = db
    ort["PANEL_UYG_KOK"] = repo
    p = subprocess.run([sys.executable, arac, "--uygula"], env=ort,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _katalog_oku(repo):
    with open(os.path.join(repo, "urunler.json"), encoding="utf-8") as f:
        return {u["id"]: u for u in json.load(f)}


def kendini_test():
    vaka, dusen = 0, []

    def ol(ad, kosul, detay=""):
        nonlocal vaka
        vaka += 1
        if kosul:
            print("  OK   " + ad)
        else:
            print("  HATA %s %s" % (ad, detay[:300]))
            dusen.append(ad)

    tmp = tempfile.mkdtemp(prefix="panel-uyg-test-")
    try:
        # ── V1: gecerli fiyat+baslik -> tabana islenir, TEK commit push'lanir,
        #        diff tam o alanlar, satirlar islendi+commit damgali.
        repo, bare, db = _fikstur_kur(tmp)
        _satir_ekle(db, "test-urun-1", "fiyat", "150 TL")
        _satir_ekle(db, "test-urun-2", "baslik", "Test Urun 2 Yeni Ad")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo, db)
        kat = _katalog_oku(repo)
        dok = _kuyruk_dok(db)
        uzak_sha = subprocess.run(["git", "-C", bare, "rev-parse", "main"],
                                  capture_output=True, text=True).stdout.strip()
        yerel_sha = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                                   capture_output=True, text=True).stdout.strip()
        ol("V1a rc=0", rc == 0, cikti)
        ol("V1b fiyat tabana islendi", kat["test-urun-1"]["fiyat"] == "150 TL")
        ol("V1c baslik tabana islendi", kat["test-urun-2"]["baslik"] == "Test Urun 2 Yeni Ad")
        ol("V1d dokunulmayan alanlar ayni", kat["test-urun-1"]["baslik"] == "Test Urun 1"
           and kat["test-urun-3"]["fiyat"] == "300 TL")
        ol("V1e push uzaga ulasti (uzak=yerel HEAD)", uzak_sha == yerel_sha and uzak_sha)
        ol("V1f iki satir da islendi + commit damgali",
           all(s["hal"] == "islendi" and s["islendi_commit"] == yerel_sha for s in dok), str(dok))

        # ── V2: beyaz liste disi alan (kategori duzelt'te MESRU ama kuyrukta YASAK)
        #        -> hal=hata ALAN_BEYAZ_LISTE_DISI, taban commit'i OLUSMAZ.
        repo2, bare2, db2 = _fikstur_kur(tmp)
        _satir_ekle(db2, "test-urun-1", "kategori", "Ofis")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo2, db2)
        kat = _katalog_oku(repo2)
        dok = _kuyruk_dok(db2)
        ol("V2a rc=0 (hata satiri kosumu dusurmez)", rc == 0, cikti)
        ol("V2b kategori DEGISMEDI", kat["test-urun-1"]["kategori"] == "Marin")
        ol("V2c satir hal=hata sebep=ALAN_BEYAZ_LISTE_DISI",
           dok[0]["hal"] == "hata" and dok[0]["sebep"] == "ALAN_BEYAZ_LISTE_DISI", str(dok))

        # ── V3-V5: bicim/parametrik/yok-urun kollari (ayni fiksturde uc satir).
        repo3, bare3, db3 = _fikstur_kur(tmp)
        _satir_ekle(db3, "test-urun-1", "fiyat", "abc")
        _satir_ekle(db3, "test-parametrik", "fiyat", "500 TL")
        _satir_ekle(db3, "olmayan-urun", "fiyat", "100 TL")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo3, db3)
        dok = _kuyruk_dok(db3)
        sebepler = {s["urun_id"]: s["sebep"] for s in dok}
        ol("V3 bozuk fiyat bicimi -> FIYAT_BICIMI", sebepler.get("test-urun-1") == "FIYAT_BICIMI")
        ol("V4 parametrik fiyat -> PARAMETRIK_FIYAT",
           sebepler.get("test-parametrik") == "PARAMETRIK_FIYAT")
        ol("V5 katalogda olmayan id -> URUN_YOK", sebepler.get("olmayan-urun") == "URUN_YOK")
        ol("V3b uc satir da hal=hata, taban degismedi",
           all(s["hal"] == "hata" for s in dok)
           and _katalog_oku(repo3)["test-urun-1"]["fiyat"] == "100 TL")

        # ── V6: ayni (urun, alan) iki satir -> yalniz EN YENI uygulanir; eskisi
        #        hata YERINE_YENISI (uygulanmayana 'islendi' denmez).
        repo4, bare4, db4 = _fikstur_kur(tmp)
        eski = _satir_ekle(db4, "test-urun-1", "fiyat", "111 TL")
        yeni = _satir_ekle(db4, "test-urun-1", "fiyat", "222 TL")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo4, db4)
        kat = _katalog_oku(repo4)
        dok = {s["id"]: s for s in _kuyruk_dok(db4)}
        ol("V6a en yeni deger tabanda", kat["test-urun-1"]["fiyat"] == "222 TL")
        ol("V6b eski satir hata YERINE_YENISI",
           dok[eski]["hal"] == "hata" and dok[eski]["sebep"] == "YERINE_YENISI:%d" % yeni)
        ol("V6c yeni satir islendi", dok[yeni]["hal"] == "islendi")

        # ── V7: taban zaten esit -> commit YOK, satir islendi TABAN_ZATEN_ESIT.
        repo5, bare5, db5 = _fikstur_kur(tmp)
        once_sha = subprocess.run(["git", "-C", bare5, "rev-parse", "main"],
                                  capture_output=True, text=True).stdout.strip()
        _satir_ekle(db5, "test-urun-1", "fiyat", "100 TL")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo5, db5)
        sonra_sha = subprocess.run(["git", "-C", bare5, "rev-parse", "main"],
                                   capture_output=True, text=True).stdout.strip()
        dok = _kuyruk_dok(db5)
        ol("V7a commit uretilmedi (uzak SHA ayni)", once_sha == sonra_sha)
        ol("V7b satir islendi sebep=TABAN_ZATEN_ESIT",
           dok[0]["hal"] == "islendi" and dok[0]["sebep"] == "TABAN_ZATEN_ESIT", str(dok))

        # ── V8: bos kuyruk -> rc 0, dokunma yok.
        repo6, bare6, db6 = _fikstur_kur(tmp)
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo6, db6)
        ol("V8 bos kuyruk rc=0 + 'is yok'", rc == 0 and "is yok" in cikti, cikti)

        # ── V9: canli kip + secret yok -> rc 0, ag/git denemesi yok (K80 probu).
        ort = dict(os.environ)
        for a in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
                  "PANEL_UYG_TEST_SQLITE", "PANEL_UYG_KOK"):
            ort.pop(a, None)
        p = subprocess.run([sys.executable, ARAC_YOLU, "--uygula"], env=ort,
                           capture_output=True, text=True)
        ol("V9 secretsiz canli kip rc=0 SECRET_YOK", p.returncode == 0
           and "SECRET_YOK" in p.stdout, p.stdout + p.stderr)

        # ── V10: push DUSERSE satirlar beklemede kalir, rc=1 (islendi damgasi
        #        push'tan once ATILMAZ). YALNIZ push URL'i bozulur — fetch calisir,
        #        yoksa kosum uca-tazelede duser ve PUSH koluna HIC ulasilmazdi
        #        (mutant da ulasamazdi: tabanla ayni kosum mutanti olduremez).
        repo7, bare7, db7 = _fikstur_kur(tmp)
        subprocess.run(["git", "-C", repo7, "remote", "set-url", "--push", "origin",
                        os.path.join(tmp, "olmayan-uzak")], check=True)
        _satir_ekle(db7, "test-urun-1", "fiyat", "150 TL")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo7, db7)
        dok = _kuyruk_dok(db7)
        ol("V10a push dusunce rc!=0", rc != 0, cikti)
        ol("V10b satir hala beklemede", dok[0]["hal"] == "beklemede", str(dok))

        # ── V11: yaris — uzak, kosum baslamadan ILERI gitmis (baska push) ->
        #        uca tazele sonrasi yine dogru tabana islenir.
        repo8, bare8, db8 = _fikstur_kur(tmp)
        yaris = os.path.realpath(tempfile.mkdtemp(prefix="panel-uyg-yaris-", dir=tmp))
        subprocess.run(["git", "clone", "-q", bare8, yaris], check=True)
        with open(os.path.join(yaris, "NOT.txt"), "w", encoding="utf-8") as f:
            f.write("yabanci commit\n")
        for k in (["config", "user.email", "y@t"], ["config", "user.name", "y"],
                  ["add", "-A"], ["commit", "-q", "-m", "yabanci"],
                  ["push", "-q", "origin", "HEAD:main"]):
            subprocess.run(["git", "-C", yaris] + k, check=True, capture_output=True)
        _satir_ekle(db8, "test-urun-1", "fiyat", "175 TL")
        rc, cikti = _uygulayici_kos(ARAC_YOLU, repo8, db8)
        kat = _katalog_oku(repo8)
        ol("V11 yabanci push sonrasi tazele+isle (fiyat tabanda, rc=0)",
           rc == 0 and kat["test-urun-1"]["fiyat"] == "175 TL", cikti)

        # ── MUTANTLAR: canli govdeye DOKUNULMAZ; gecici KOPYA mutasyonlanir.
        #    Once kopyanin KONTROL kosumu (mutasyonsuz, ayni argumanlar) yesil olmali.
        with open(ARAC_YOLU, encoding="utf-8") as f:
            govde = f.read()
        mutant_sonuc = []

        # KONTROL: bayt-esit kopya V1 senaryosunu ayni sekilde gecmeli.
        kopya = os.path.join(tmp, "kopya-kontrol.py")
        with open(kopya, "w", encoding="utf-8") as f:
            f.write(govde)
        repoK, bareK, dbK = _fikstur_kur(tmp)
        _satir_ekle(dbK, "test-urun-1", "fiyat", "150 TL")
        rcK, ciktiK = _uygulayici_kos(kopya, repoK, dbK)
        kontrol_yesil = (rcK == 0 and _katalog_oku(repoK)["test-urun-1"]["fiyat"] == "150 TL")
        ol("KONTROL bayt-esit kopya yesil", kontrol_yesil, ciktiK)

        # M1-beyaz-liste-kalkar: hedef kol = ALAN_BEYAZ_LISTE_DISI (V2 sinifi).
        # Capa PARCALI kurulur — tek literal olsaydi bu test dosyasinin kendi
        # satiri da sayilir, CAPA_SAYISI=2 cikardi (olculmus sinif: mutant capasi
        # kendi CAPA satirinda gecmez).
        capa1 = "if alan not in " + "ALAN_BEYAZ_LISTESI:"
        ol("M1 capasi canli govdede tekil", govde.count(capa1) == 1)
        m1 = os.path.join(tmp, "mutant-m1.py")
        with open(m1, "w", encoding="utf-8") as f:
            f.write(govde.replace(capa1, "if False:"))
        repoM1, bareM1, dbM1 = _fikstur_kur(tmp)
        _satir_ekle(dbM1, "test-urun-1", "kategori", "Ofis")
        rc1, cikti1 = _uygulayici_kos(m1, repoM1, dbM1)
        katM1 = _katalog_oku(repoM1)
        m1_oldu = katM1["test-urun-1"]["kategori"] != "Marin" or all(
            s["sebep"] != "ALAN_BEYAZ_LISTE_DISI" for s in _kuyruk_dok(dbM1))
        mutant_sonuc.append(("M1-beyaz-liste-kalkar", m1_oldu, "ALAN_BEYAZ_LISTE_DISI"))
        ol("M1 mutant V2 iddiasini dusurdu (beyaz liste kolu canli)", m1_oldu, cikti1)

        # M2-islendi-pushtan-once: hedef kol = PUSH-OLMADI (V10 sinifi). Capa yine
        # parcali; fikstur V10 ile ayni sekilde YALNIZ push URL'ini bozar ki mutant
        # koda FIILEN ulassin.
        capa2 = "return 1  # PUSH-OLMADI" + "-KOLU"
        ol("M2 capasi canli govdede tekil", govde.count(capa2) == 1)
        m2 = os.path.join(tmp, "mutant-m2.py")
        with open(m2, "w", encoding="utf-8") as f:
            f.write(govde.replace(capa2, "push_ok = True  # susturuldu"))
        repoM2, bareM2, dbM2 = _fikstur_kur(tmp)
        subprocess.run(["git", "-C", repoM2, "remote", "set-url", "--push", "origin",
                        os.path.join(tmp, "olmayan-uzak-2")], check=True)
        _satir_ekle(dbM2, "test-urun-1", "fiyat", "150 TL")
        rc2, cikti2 = _uygulayici_kos(m2, repoM2, dbM2)
        dokM2 = _kuyruk_dok(dbM2)
        m2_oldu = any(s["hal"] == "islendi" for s in dokM2) or rc2 == 0
        mutant_sonuc.append(("M2-islendi-pushtan-once", m2_oldu, "PUSH-OLMADI"))
        ol("M2 mutant V10 iddiasini dusurdu (push oncesi islendi yakalanir)", m2_oldu, cikti2)

        olen = sum(1 for _, oldu, _ in mutant_sonuc if oldu)
        print("SONUC: VAKA=%d DUSEN=%d MUTANT=%d/%d KONTROL=%s"
              % (vaka, len(dusen), olen, len(mutant_sonuc),
                 "YESIL" if kontrol_yesil else "KIRMIZI"))
        for ad, oldu, hedef in mutant_sonuc:
            print("  MUTANT %s hedef=%s %s" % (ad, hedef, "OLDU" if oldu else "KACTI"))
        return 0 if (not dusen and olen == len(mutant_sonuc) and kontrol_yesil) else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    if a.durum:
        return durum()
    if a.uygula:
        return uygula()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
