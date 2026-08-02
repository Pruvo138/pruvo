#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yayin-gecikme-nobeti.py KABUL TESTI — hukum + KABLOLAMA + BAGIMSIZLIK.

Nobetcinin kendi fikstur kabulu (`--kendini-test`) burada kosar, AMA bu dosyanin asil
isi kablolamayi nobetlemektir: bir yayin-gecikme nobetcisi YANLIS YERE baglanirsa
sessizce ise yaramaz hale gelir. Iki bilinen olum bicimi vardir ve ikisi de burada
olculur:

  1) BAGIMSIZLIK KAYBI — nobetcinin CANLI OLCUM kolu deploy.yml'e baglanirsa, hat
     tikandigi anda nobetci de kosamaz: tam ihtiyac aninda susar. deploy.yml'de
     bayraksiz (olcum yapan) bir cagri BULUNURSA bu test KIRMIZI yanar.
  2) PANO KABLOSUNUN KOPMASI — nobetcinin insana ulastigi TEK rutin yol
     tools/durum.py bolum 9'dur (pano her oturum basi okunur). Bolum ya da cagrisi
     silinirse nobetci "var ama kimse bakmiyor" haline duser; bu da olculur.

Ayrica: fikstur envanteri TABANIN ALTINA DUSEMEZ ve BES sinifin (AKIYOR · GECIKME ·
TIKALI · ACLIK · OLCULEMEDI) HER BIRI en az bir fiksturle temsil edilmek zorundadir —
fikstur listesini kucultmek nobetciyi sessizce oldurmenin en ucuz yoludur.

SERIT: bu dosyanin deploy.yml cagrisi YAYINI BLOKLAMAYAN job'da (serit B) olmalidir.
Gerekce: bu bir "sizintili icerik canliya cikmasin" kapisi DEGIL, bir aracin kendini
sinamasidir; yayini durdurmasi bu depoda olculmus bir zarardir
([[kapi-birikimi-yayin-gecikmesi]]). Beyan: tools/is-akisi-kapisi.py :: SERIT_B.

Ag YOK (fiksturler agsiz; pano cagrisi `gh` yoksa OLCULEMEDI doner ve o da bir
kabuldur). Cikis: 0 = hepsi gecti, 1 = en az bir kusur.
"""
import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
NOBETCI_YOL = "tools/yayin-gecikme-nobeti.py"
BU_TEST_YOL = "tools/yayin-gecikme-test.py"
DEPLOY = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

# Fikstur envanteri TABANI — buyuyebilir, ALTINA DUSEMEZ (bkz. modul basligi).
FIKSTUR_TABANI = 18
ZORUNLU_SINIFLAR = ("AKIYOR", "GECIKME", "TIKALI", "ACLIK", "OLCULEMEDI")

# IS DUZEYI ekseninin IKI kanarisi — ikisi de 1 Agu 2026'nin GERCEK govdesinden.
# Biri olmadan digeri tek basina yanlis bir onarimi gecirir:
#   yanlis-alarm kanarisi yoksa   -> kosum duzeyine geri donus fark edilmez,
#   korelme kanarisi yoksa        -> "her sey yayinlandi sayilsin" fark edilmez.
YANLIS_ALARM_FIKSTURU = "bugun-serit-b-dustu"
KORELME_FIKSTURU = "bugun-build-dustu"

SONUC = []


def kayit(ad, gecti, detay=""):
    SONUC.append((ad, bool(gecti), detay))
    print("  %s %s%s" % ("✔" if gecti else "✘", ad, ("  — " + detay) if detay else ""))


def _modul(ad, yol):
    if not os.path.exists(yol):
        raise RuntimeError("%s YOK" % yol)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- 1) HUKUM
def test_fikstur_kabulu(yg):
    rc = yg.kendini_test(yazdir=False)
    kayit("1a fikstur kabulu (agsiz) YESIL", rc == 0, "rc=%d" % rc)

    adlar = yg.fikstur_adlari()
    kayit("1b fikstur envanteri tabanin ustunde (>= %d)" % FIKSTUR_TABANI,
          len(adlar) >= FIKSTUR_TABANI, "%d fikstur" % len(adlar))

    gorulen = set()
    bozuk = []
    for ad in adlar:
        try:
            _, _, beklenen, _ = yg.fikstur_yukle(ad)
            gorulen.add(beklenen)
        except Exception as e:
            bozuk.append("%s (%s)" % (ad, e))
    eksik = [s for s in ZORUNLU_SINIFLAR if s not in gorulen]
    kayit("1c BES sinifin hepsi fiksturle temsil ediliyor", not eksik and not bozuk,
          "eksik=%s bozuk=%s" % (eksik or "-", bozuk or "-"))


def test_sozlesme(yg):
    kayit("2a OLCULEMEDI cikis kodu YESIL ile karismiyor",
          yg.SINIF_RC["OLCULEMEDI"] != 0, "rc=%d" % yg.SINIF_RC["OLCULEMEDI"])
    kayit("2b her sinifin AYRI cikis kodu var",
          len(set(yg.SINIF_RC.values())) == len(yg.SINIF_RC),
          "%d sinif / %d kod" % (len(yg.SINIF_RC), len(set(yg.SINIF_RC.values()))))
    kayit("2c yas esikleri sirali (uyari < alarm)",
          0 < yg.GECIKME_YAS_DK < yg.TIKALI_YAS_DK,
          "%s < %s" % (yg.GECIKME_YAS_DK, yg.TIKALI_YAS_DK))


# ---------------------------------------------------------------- 3) PANO KABLOSU
def test_pano_kablosu():
    yol = os.path.join(TOOLS, "durum.py")
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    agac = ast.parse(kaynak)
    main = next((d for d in agac.body
                 if isinstance(d, ast.FunctionDef) and d.name == "main"), None)
    if main is None:
        kayit("3a durum.py::main bulundu", False)
        return
    cagrilar = {n.func.id for n in ast.walk(main)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    kayit("3a durum.py::main bolum 9 fonksiyonunu CAGIRIYOR",
          "_yayin_gecikme_satirlari" in cagrilar,
          "cagrilar: %s" % (sorted(c for c in cagrilar if "yayin" in c) or "yok"))

    basliklar = [n.value for n in ast.walk(main)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and "YAYIN GECIKMESI" in n.value]
    kayit("3b pano bolum basligi yerinde", bool(basliklar),
          basliklar[0].strip() if basliklar else "baslik YOK")

    fonk = next((d for d in agac.body if isinstance(d, ast.FunctionDef)
                 and d.name == "_yayin_gecikme_satirlari"), None)
    govde = ast.get_source_segment(kaynak, fonk) if fonk else ""
    kayit("3c pano hukmu TEK KAYNAKTAN (nobetci dosyasi) yukleniyor",
          bool(govde) and "yayin-gecikme-nobeti.py" in govde,
          "fonksiyon %s" % ("var" if fonk else "YOK"))

    # CANLI kablo: pano cagrisi PATLAMAZ ve bos donmez. `gh` yoksa OLCULEMEDI doner
    # (kabul) — ama SESSIZ kalmaz.
    durum = _modul("durum_pano_testi", yol)
    try:
        satirlar = durum._yayin_gecikme_satirlari()
    except Exception as e:
        kayit("3d pano cagrisi patlamiyor", False, "%s: %s" % (type(e).__name__, e))
        return
    ilk = satirlar[0] if satirlar else ""
    kayit("3d pano cagrisi bir SINIF satiri donduruyor",
          bool(satirlar) and any(s in ilk for s in ZORUNLU_SINIFLAR)
          or "ÖLÇÜLEMEDİ" in ilk,
          ilk.strip()[:70] if ilk else "BOS")


# ------------------------------------------------- 4) BAGIMSIZLIK + SERIT
def _deploy_cagrilari(suzgec, iak):
    """deploy.yml'deki (job_id, yol, argumanlar) uclulerinin listesi.

    `run:` degerleri GERCEK ayristiriciyla cozulur (metin taklidi YOK) ve her satirin
    ANLAMLI bir icra olup olmadigina ortak suzgec (tools/icra-suzgeci.py) karar verir.
    """
    with open(DEPLOY, encoding="utf-8") as f:
        metin = f.read()
    govde, hata = iak.ayristir(metin)
    if govde is None:
        raise RuntimeError("deploy.yml ayristirilamadi: %s" % hata)
    serit_b, tani = iak._serit_b_joblar(govde)
    if serit_b is None:
        raise RuntimeError("serit B joblari olculemedi: %s" % tani)
    cikti = []
    for job_id, job in (govde.get("jobs") or {}).items():
        for adim in (job.get("steps") or []):
            calistir = adim.get("run") if isinstance(adim, dict) else None
            if not isinstance(calistir, str):
                continue
            for satir in calistir.splitlines():
                for yol in (NOBETCI_YOL, BU_TEST_YOL):
                    hukum, _, argumanlar = suzgec.anlamli_cagri(satir, yol)
                    if hukum in (suzgec.EVET, suzgec.OLCULEMEDI):
                        cikti.append((job_id, yol, list(argumanlar or [])))
    return cikti, serit_b


def test_bagimsizlik(suzgec, iak):
    try:
        cagrilar, serit_b = _deploy_cagrilari(suzgec, iak)
    except Exception as e:
        # FAIL-CLOSED: olculemeyen kablolama "sorun yok" DEGILDIR.
        kayit("4a BAGIMSIZLIK olculdu", False, "%s: %s" % (type(e).__name__, e))
        return

    canli = [(j, a) for j, y, a in cagrilar
             if y == NOBETCI_YOL and "--kendini-test" not in a and "--liste" not in a]
    kayit("4a BAGIMSIZLIK: nobetcinin CANLI OLCUM kolu deploy.yml'de KOSMUYOR",
          not canli,
          "ihlal: %s" % (canli if canli else "-"))

    kendi = [(j, a) for j, y, a in cagrilar if y == BU_TEST_YOL]
    kayit("4b bu kabul testi deploy.yml'de FIILEN kosuyor (olu nobetci degil)",
          bool(kendi), "job(lar): %s" % (sorted({j for j, _ in kendi}) or "YOK"))

    bloklayan = sorted({j for j, _ in kendi if j not in serit_b})
    kayit("4c cagri YAYINI BLOKLAMAYAN seritte (serit B)",
          bool(kendi) and not bloklayan,
          "bloklayan job: %s" % (bloklayan or "-"))


# ------------------------------------------- 5) IS DUZEYI: "yayin indi mi" kaniti
def _fikstur_hukmu(yg, ad):
    getir, simdi, beklenen, _ = yg.fikstur_yukle(ad)
    sinif, rc, gerekce, olcum = yg.olc_ve_degerlendir(getir=getir, simdi=simdi)
    return sinif, gerekce, olcum


def test_is_duzeyi(yg):
    """Kosumun GENEL conclusion'i bu hatta yayin kaniti DEGILDIR (bkz. nobetci basligi)."""
    ham = {}
    for ad in yg.fikstur_adlari():
        with open(yg.fikstur_yolu(ad), encoding="utf-8") as f:
            ham[ad] = json.load(f)
    is_bildiren = sorted(a for a, v in ham.items() if "_isler" in v)
    kayit("5a is duzeyi FIILEN fiksturleniyor (`_isler` bildiren fikstur var)",
          bool(is_bildiren), "fikstur(ler): %s" % (is_bildiren or "YOK"))

    try:
        sinif, _, olcum = _fikstur_hukmu(yg, YANLIS_ALARM_FIKSTURU)
    except Exception as e:
        sinif, olcum = "%s: %s" % (type(e).__name__, e), None
    kayit("5b genel conclusion=failure ama deploy+yayin basarili -> AKIYOR",
          sinif == "AKIYOR",
          "%s · taban=%s geride=%s" % (sinif, (olcum or {}).get("son_basarili_sha"),
                                       (olcum or {}).get("geride")))

    try:
        sinif2, gerekce2, olcum2 = _fikstur_hukmu(yg, KORELME_FIKSTURU)
    except Exception as e:
        sinif2, gerekce2, olcum2 = "%s: %s" % (type(e).__name__, e), [], None
    # KORELME: bu fiksturde yas (74 dk) TIKALI esiginin (75) ALTINDADIR -> hukum
    # YALNIZ hata zincirinden gelebilir. Zincir eksenini korelten bir onarim burada
    # AKIYOR verir ve yakalanir.
    zincir = (olcum2 or {}).get("ardisik_hata")
    kayit("5c build dustu / deploy HIC kosmadi (skipped) -> hala TIKALI",
          sinif2 == "TIKALI" and zincir >= yg.TIKALI_HATA_ZINCIR,
          "%s · ardisik hata=%s · yas=%.0f dk (TIKALI yas esigi %d)"
          % (sinif2, zincir, (olcum2 or {}).get("yas_dk") or 0, yg.TIKALI_YAS_DK))

    # Birim iddialar: "yayinladi" YALNIZ deploy isinin success'inden dogar.
    vakalar = [
        ({"conclusion": "failure"}, {"deploy": "success", "yayin": "success"}, "success"),
        ({"conclusion": "failure"}, {"deploy": "skipped"}, "failure"),
        ({"conclusion": "failure"}, {"deploy": "failure"}, "failure"),
        ({"conclusion": "cancelled"}, {}, "cancelled"),
        ({"conclusion": "success"}, {"deploy": "skipped"}, "yayinsiz"),
    ]
    yanlis = ["%s+%s->%s (beklenen %s)" % (k["conclusion"], i or "{}",
                                           yg.etkin_sonuc(k, i), b)
              for k, i, b in vakalar if yg.etkin_sonuc(k, i) != b]
    kayit("5d etkin sonuc YALNIZ `deploy` isinden doguyor", not yanlis,
          "sapma: %s" % (yanlis or "-"))

    # Kosum YESIL ama beklenen is adi govdede YOK -> sekil degismis olabilir:
    # sessizce "yayinlamadi" saymak SAHTE KIRMIZI olurdu -> OLCULEMEDI.
    yesil = {"id": 1, "status": "completed", "conclusion": "success"}
    try:
        yg.yayin_taramasi([yesil], lambda k: {"jobs": [
            {"name": "baska-is", "status": "completed", "conclusion": "success"}]})
        sonuc = "istisna YOK"
    except yg.OlcumHatasi as e:
        sonuc = str(e)[:60]
    kayit("5e yesil kosumda `deploy` isi HIC yoksa -> OLCULEMEDI (sahte kirmizi degil)",
          sonuc != "istisna YOK", sonuc)

    # `yayin` isi dusmusse SITE CANLIDIR (hukum degismez) ama bozulma GORUNUR olmali.
    olcum3 = dict((olcum or {}), taslak_isi="failure")
    satirlar3 = " ".join(yg._ozet_satirlari(olcum3)) if olcum else ""
    kayit("5f `yayin` isi dustuyse raporda GORUNUR (hukum degil, teshis)",
          yg.TASLAK_ISI in satirlar3 and "SITE CANLI" in satirlar3,
          "satir %s" % ("var" if "SITE CANLI" in satirlar3 else "YOK"))


# --------------------------------------- 6) TESHIS ETIKETI + STDERR SIZINTISI
def _sahte_gh(dizin, stderr_metni):
    """PATH'e konacak, verilen metni stderr'e basip rc=1 donen sahte `gh`."""
    yol = os.path.join(dizin, "gh")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("import sys\n")
        f.write("sys.stderr.write(%s)\n" % json.dumps(stderr_metni))
        f.write("sys.exit(1)\n")
    os.chmod(yol, 0o755)
    return yol


def test_teshis_ve_sizinti(yg):
    gizli = "https://api.github.com/repos/GIZLI-DEPO/actions/runs/42/jobs?per_page=100"
    dizin = tempfile.mkdtemp(prefix="yayin-gecikme-gh-")
    eski_path = os.environ.get("PATH", "")
    try:
        _sahte_gh(dizin, "gh: Not Found (HTTP 404) %s" % gizli)
        os.environ["PATH"] = dizin + os.pathsep + eski_path
        mesajlar = {}
        for etiket in ("runs", "jobs", "compare"):
            try:
                yg.api_getir("repos/x/y", etiket=etiket)
                mesajlar[etiket] = "(istisna YOK)"
            except yg.OlcumHatasi as e:
                mesajlar[etiket] = str(e)
    finally:
        os.environ["PATH"] = eski_path
        shutil.rmtree(dizin, ignore_errors=True)

    etiketli = [e for e in mesajlar if ("[%s]" % e) in mesajlar[e]]
    kayit("6a hata mesaji CAGRI ETIKETINI tasiyor (runs/jobs/compare ayirt ediliyor)",
          len(etiketli) == 3, "etiketli: %s" % (etiketli or "YOK"))
    kayit("6b ayni metni basan iki uc AYRI mesaj uretiyor",
          mesajlar["runs"] != mesajlar["compare"],
          "runs != compare: %s" % (mesajlar["runs"] != mesajlar["compare"]))

    sizan = [e for e, m in mesajlar.items()
             if gizli in m or "GIZLI-DEPO" in m or "https://" in m]
    kayit("6c `gh` stderr'indeki URL/yol mesaja SIZMIYOR", not sizan,
          "sizan: %s" % (sizan or "-"))
    kayit("6d teshis YOK EDILMEDI: hata SINIFI hala gorunuyor",
          all("404" in m for m in mesajlar.values()),
          mesajlar["jobs"][:70])

    # Taninmayan metin: sinif yok -> icerik BASILMAZ ama olculen boyut bildirilir.
    ozet = yg.gh_hata_sinifi("beklenmedik %s" % gizli)
    kayit("6e taninmayan hata metninin ICERIGI basilmiyor",
          gizli not in ozet and "bayt" in ozet, ozet[:70])


def main():
    print("YAYIN GECIKME NOBETCISI — KABUL TESTI")
    try:
        yg = _modul("yayin_gecikme_nobeti", os.path.join(TOOLS,
                                                         "yayin-gecikme-nobeti.py"))
        suzgec = _modul("pruvo_icra_suzgeci", os.path.join(TOOLS, "icra-suzgeci.py"))
        iak = _modul("pruvo_is_akisi_kapisi", os.path.join(TOOLS, "is-akisi-kapisi.py"))
    except Exception as e:
        print("  ✘ FAIL-CLOSED: gerekli modul yuklenemedi — %s: %s" % (type(e).__name__, e))
        return 1

    test_fikstur_kabulu(yg)
    test_sozlesme(yg)
    test_pano_kablosu()
    test_bagimsizlik(suzgec, iak)
    test_is_duzeyi(yg)
    test_teshis_ve_sizinti(yg)

    basarisiz = [a for a, g, _ in SONUC if not g]
    print("")
    print("SONUC: %d/%d gecti" % (len(SONUC) - len(basarisiz), len(SONUC)))
    for a in basarisiz:
        print("  ✘ %s" % a)
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
