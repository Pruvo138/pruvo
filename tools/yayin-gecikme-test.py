#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yayin-gecikme-nobeti.py KABUL TESTI — hukum + KABLOLAMA + BAGIMSIZLIK.

Nobetcinin fiksturleri burada kosar, AMA bu dosyanin asil isi HUKMU EKSEN EKSEN
nobetlemektir: bir yayin-gecikme nobetcisi ya YANLIS YERE baglanarak ya da bir ekseni
sessizce koreltilerek ise yaramaz hale gelir.

🔴 EKSENLER (her IDDIA tam BIR eksene aittir; mutasyon surucusu bu kodlari olcer)
================================================================================
  Y1  EKSEN 1 — bekleyen ICERIK: yas/zincir/birikme hukumleri + genel fikstur battaryasi
  Y2  SOZLESME — sinif/cikis kodu ayrimi, esiklerin OLCULEN tabana gore konumu, fail-closed
  Y3  PANO KABLOSU — nobetcinin insana ulastigi TEK rutin yol (tools/durum.py bolum 9)
  Y4  BAGIMSIZLIK + SERIT — canli olcum kolu deploy.yml'de KOSMAZ; kabul testi serit B'de
  Y5  IS DUZEYI — "yayin indi mi" YALNIZ `deploy` isinden okunur (kosum duzeyinden DEGIL)
  Y6  TESHIS + SIZINTI — `gh` stderr'i disari cikmaz, hata SINIFI korunur
  Y7  YAS TABANI — taban `deploy` isinin BITISI (yayin ani); kosumun BASLANGICI DEGIL
  Y8  EKSEN 2 — KOSUM OMUR TAVANI; `ahead_by` kapisinin ONUNDE ve eksen 1'i MASKELEMEZ

Y1/Y5/Y7/Y8 fiksturleri BOLUSUR (asagidaki EKSEN_FIKSTURLERI): her fikstur TAM BIR eksende
yargilanir. Sebep olculdu — hepsini tek bir "fikstur kabulu" iddiasinda toplamak, her
mutantin AYNI iddiayi kirmizi yakmasina ve "hangi eksen oldu" sorusunun cevapsiz
kalmasina yol acar ([[hukum-yanlis-birimde]], [[beyan-edilmis-survivor]]).

Iki bilinen KABLOLAMA olumu ayrica olculur:
  1) BAGIMSIZLIK KAYBI — nobetcinin CANLI OLCUM kolu deploy.yml'e baglanirsa, hat
     tikandigi anda nobetci de kosamaz: tam ihtiyac aninda susar (Y4).
  2) PANO KABLOSUNUN KOPMASI — pano bolumu ya da cagrisi silinirse nobetci "var ama
     kimse bakmiyor" haline duser (Y3).

Ayrica: fikstur envanteri TABANIN ALTINA DUSEMEZ ve BES sinifin (AKIYOR · GECIKME ·
TIKALI · ACLIK · OLCULEMEDI) HER BIRI en az bir fiksturle temsil edilmek zorundadir —
fikstur listesini kucultmek nobetciyi sessizce oldurmenin en ucuz yoludur (Y1).

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
FIKSTUR_TABANI = 21
ZORUNLU_SINIFLAR = ("AKIYOR", "GECIKME", "TIKALI", "ACLIK", "OLCULEMEDI")

# 🔴 FIKSTUR -> EKSEN PAYLASIMI. Burada ADI GECMEYEN her fikstur Y1'e aittir; Y1 bu
# bolunmenin TAM oldugunu (hicbir fikstur sahipsiz kalmadigini) ayrica olcer.
EKSEN_FIKSTURLERI = {
    # IS DUZEYI ekseninin IKI kanarisi — ikisi de 1 Agu 2026'nin GERCEK govdesinden.
    # Biri olmadan digeri tek basina yanlis bir onarimi gecirir:
    #   yanlis-alarm kanarisi yoksa   -> kosum duzeyine geri donus fark edilmez,
    #   korelme kanarisi yoksa        -> "her sey yayinlandi sayilsin" fark edilmez.
    "Y5": ("bugun-serit-b-dustu", "bugun-build-dustu"),
    # YAS TABANI ekseninin IKI kanarisi: biri tabanin YERINI (yayin ani), digeri tabanin
    # VARLIGINI (ff-only ile gelen eski tarihli commit) tutar.
    "Y7": ("bugunku-kuyruk-saglikli", "ff-only-eski-tarihli"),
    # KOSUM OMRU ekseninin IKI kanarisi: biri alarmin DOGDUGUNU, digeri NORMAL omurde
    # DOGMADIGINI (yanlis alarm kapisi) tutar.
    "Y8": ("takilan-kosum-bekleyen-yok", "takilan-kosum-normal"),
}

YANLIS_ALARM_FIKSTURU = "bugun-serit-b-dustu"
KORELME_FIKSTURU = "bugun-build-dustu"
# KABUL VAKALARI (mimar spec'i): (a) saglikli-uzun-kuyruk · (b) takilan kosum ·
# (c) yayin inmiyor · (d) normal dongu.
VAKA_A_SAGLIKLI_KUYRUK = "bugunku-kuyruk-saglikli"
VAKA_B_TAKILAN_KOSUM = "takilan-kosum-bekleyen-yok"
VAKA_C_YAYIN_INMIYOR = "bugun-tikali"
VAKA_D_NORMAL = "normal"

EKSEN_1_ADLARI = ("yas_gecikme", "yas_tikali", "hata_zinciri", "iptal_zinciri", "birikme")
EKSEN_2_ADI = "sure_tavani"

SATIRLAR = []
KIRMIZI = set()          # KIRMIZI YANAN EKSEN KODLARI (mutasyon surucusunun olctugu kume)
HATALAR = []


def kayit(kod, ad, gecti, detay=""):
    SATIRLAR.append(("  ✔ " if gecti else "  ✘ ")
                    + "%-3s %s%s" % (kod, ad, ("  — " + detay) if detay else ""))
    if not gecti:
        KIRMIZI.add(kod)
        HATALAR.append("%s %s%s" % (kod, ad, ("  — " + detay) if detay else ""))


def _modul(ad, yol):
    if not os.path.exists(yol):
        raise RuntimeError("%s YOK" % yol)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _fikstur_hukmu(yg, ad):
    getir, simdi, beklenen, _ = yg.fikstur_yukle(ad)
    sinif, rc, gerekce, olcum = yg.olc_ve_degerlendir(getir=getir, simdi=simdi)
    return sinif, beklenen, gerekce, (olcum or {})


def _eksen_ozeti(olcum):
    eks = olcum.get("eksenler") or {}
    e1 = sorted(a for a in EKSEN_1_ADLARI if eks.get(a))
    return e1, bool(eks.get(EKSEN_2_ADI))


def _sahipli_fiksturler():
    sahipli = {}
    for kod, adlar in EKSEN_FIKSTURLERI.items():
        for a in adlar:
            sahipli[a] = kod
    return sahipli


# ---------------------------------------------------- Y1) EKSEN 1 + genel battarya
def y1_icerik_ekseni(yg):
    adlar = yg.fikstur_adlari()
    kayit("Y1", "fikstur envanteri tabanin ustunde (>= %d)" % FIKSTUR_TABANI,
          len(adlar) >= FIKSTUR_TABANI, "%d fikstur" % len(adlar))

    sahipli = _sahipli_fiksturler()
    yabanci = sorted(a for a in sahipli if a not in adlar)
    kayit("Y1", "eksen paylasimi TAM (her eksen fiksturu diskte var)", not yabanci,
          "eksik: %s" % (yabanci or "-"))

    gorulen = set()
    bozuk, sapan = [], []
    for ad in adlar:
        if ad in sahipli:                      # baska eksende yargilanir
            try:
                _, beklenen, _, _ = _fikstur_hukmu(yg, ad)
                gorulen.add(beklenen)
            except Exception as e:             # noqa: BLE001
                bozuk.append("%s (%s)" % (ad, e))
            continue
        try:
            sinif, beklenen, gerekce, _ = _fikstur_hukmu(yg, ad)
            gorulen.add(beklenen)
            if sinif != beklenen:
                sapan.append("%s: beklenen %s, olculen %s (%s)"
                             % (ad, beklenen, sinif, "; ".join(gerekce)[:90]))
        except Exception as e:                 # noqa: BLE001
            bozuk.append("%s (%s)" % (ad, e))
    kayit("Y1", "genel fikstur battaryasi (Y5/Y7/Y8 disi) hukumleri tutuyor",
          not sapan and not bozuk,
          "sapan=%s bozuk=%s" % (sapan or "-", bozuk or "-"))

    eksik = [s for s in ZORUNLU_SINIFLAR if s not in gorulen]
    kayit("Y1", "BES sinifin hepsi fiksturle temsil ediliyor", not eksik,
          "eksik=%s" % (eksik or "-"))

    # VAKA (c): yayin inmiyor -> EKSEN 1 KIRMIZI, EKSEN 2 TEMIZ.
    sinif, beklenen, _, olcum = _fikstur_hukmu(yg, VAKA_C_YAYIN_INMIYOR)
    e1, e2 = _eksen_ozeti(olcum)
    kayit("Y1", "VAKA (c) %s: TIKALI ve hukum EKSEN 1'den (eksen 2 temiz)"
          % VAKA_C_YAYIN_INMIYOR,
          sinif == "TIKALI" and bool(e1) and not e2,
          "%s · eksen1=%s · eksen2=%s" % (sinif, e1 or "-", e2))

    # VAKA (d): normal dongu -> IKI EKSEN de temiz.
    sinif, beklenen, _, olcum = _fikstur_hukmu(yg, VAKA_D_NORMAL)
    e1, e2 = _eksen_ozeti(olcum)
    kayit("Y1", "VAKA (d) %s: AKIYOR ve IKI eksen de temiz" % VAKA_D_NORMAL,
          sinif == "AKIYOR" and not e1 and not e2,
          "%s · eksen1=%s · eksen2=%s" % (sinif, e1 or "-", e2))


# ---------------------------------------------------------------- Y2) SOZLESME
def y2_sozlesme(yg):
    kusur = yg.sozlesme_kusurlari()
    kayit("Y2", "sozlesme nobetleri TEMIZ (rc ayrimi · esik sirasi · fail-closed)",
          not kusur, "; ".join(kusur)[:160] or "-")
    kayit("Y2", "yas esikleri OLCULEN saglikli tepenin (%.1f dk) USTUNDE"
          % yg.OLCULEN_SAGLIKLI_YAS_TAVANI_DK,
          yg.GECIKME_YAS_DK < yg.TIKALI_YAS_DK
          and yg.TIKALI_YAS_DK > yg.OLCULEN_SAGLIKLI_YAS_TAVANI_DK,
          "uyari %s < alarm %s" % (yg.GECIKME_YAS_DK, yg.TIKALI_YAS_DK))


# ---------------------------------------------------------------- Y3) PANO KABLOSU
def y3_pano_kablosu():
    yol = os.path.join(TOOLS, "durum.py")
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    agac = ast.parse(kaynak)
    main = next((d for d in agac.body
                 if isinstance(d, ast.FunctionDef) and d.name == "main"), None)
    if main is None:
        kayit("Y3", "durum.py::main bulundu", False)
        return
    cagrilar = {n.func.id for n in ast.walk(main)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    kayit("Y3", "durum.py::main bolum 9 fonksiyonunu CAGIRIYOR",
          "_yayin_gecikme_satirlari" in cagrilar,
          "cagrilar: %s" % (sorted(c for c in cagrilar if "yayin" in c) or "yok"))

    basliklar = [n.value for n in ast.walk(main)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and "YAYIN GECIKMESI" in n.value]
    kayit("Y3", "pano bolum basligi yerinde", bool(basliklar),
          basliklar[0].strip() if basliklar else "baslik YOK")

    fonk = next((d for d in agac.body if isinstance(d, ast.FunctionDef)
                 and d.name == "_yayin_gecikme_satirlari"), None)
    govde = ast.get_source_segment(kaynak, fonk) if fonk else ""
    kayit("Y3", "pano hukmu TEK KAYNAKTAN (nobetci dosyasi) yukleniyor",
          bool(govde) and "yayin-gecikme-nobeti.py" in govde,
          "fonksiyon %s" % ("var" if fonk else "YOK"))

    # CANLI kablo: pano cagrisi PATLAMAZ ve bos donmez. `gh` yoksa OLCULEMEDI doner
    # (kabul) — ama SESSIZ kalmaz.
    durum = _modul("durum_pano_testi", yol)
    try:
        satirlar = durum._yayin_gecikme_satirlari()
    except Exception as e:                     # noqa: BLE001
        kayit("Y3", "pano cagrisi patlamiyor", False, "%s: %s" % (type(e).__name__, e))
        return
    ilk = satirlar[0] if satirlar else ""
    kayit("Y3", "pano cagrisi bir SINIF satiri donduruyor",
          bool(satirlar) and (any(s in ilk for s in ZORUNLU_SINIFLAR)
                              or "ÖLÇÜLEMEDİ" in ilk),
          ilk.strip()[:70] if ilk else "BOS")


# ------------------------------------------------- Y4) BAGIMSIZLIK + SERIT
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


def y4_bagimsizlik(suzgec, iak):
    try:
        cagrilar, serit_b = _deploy_cagrilari(suzgec, iak)
    except Exception as e:                     # noqa: BLE001
        # FAIL-CLOSED: olculemeyen kablolama "sorun yok" DEGILDIR.
        kayit("Y4", "BAGIMSIZLIK olculdu", False, "%s: %s" % (type(e).__name__, e))
        return

    canli = [(j, a) for j, y, a in cagrilar
             if y == NOBETCI_YOL and "--kendini-test" not in a and "--liste" not in a]
    kayit("Y4", "BAGIMSIZLIK: nobetcinin CANLI OLCUM kolu deploy.yml'de KOSMUYOR",
          not canli, "ihlal: %s" % (canli if canli else "-"))

    kendi = [(j, a) for j, y, a in cagrilar if y == BU_TEST_YOL]
    kayit("Y4", "bu kabul testi deploy.yml'de FIILEN kosuyor (olu nobetci degil)",
          bool(kendi), "job(lar): %s" % (sorted({j for j, _ in kendi}) or "YOK"))

    bloklayan = sorted({j for j, _ in kendi if j not in serit_b})
    kayit("Y4", "cagri YAYINI BLOKLAMAYAN seritte (serit B)",
          bool(kendi) and not bloklayan, "bloklayan job: %s" % (bloklayan or "-"))


# ------------------------------------------- Y5) IS DUZEYI: "yayin indi mi" kaniti
def y5_is_duzeyi(yg):
    """Kosumun GENEL conclusion'i bu hatta yayin kaniti DEGILDIR (bkz. nobetci basligi)."""
    kusur = yg.is_duzeyi_kusurlari()
    kayit("Y5", "is duzeyi sozlesmesi TEMIZ (etkin sonuc `%s` isinden + fikstur var)"
          % yg.YAYIN_ISI, not kusur, "; ".join(kusur)[:160] or "-")

    try:
        sinif, _, _, olcum = _fikstur_hukmu(yg, YANLIS_ALARM_FIKSTURU)
    except Exception as e:                     # noqa: BLE001
        sinif, olcum = "%s: %s" % (type(e).__name__, e), {}
    kayit("Y5", "genel conclusion=failure ama deploy+yayin basarili -> AKIYOR",
          sinif == "AKIYOR",
          "%s · taban=%s geride=%s" % (sinif, olcum.get("son_basarili_sha"),
                                       olcum.get("geride")))

    try:
        sinif2, _, _, olcum2 = _fikstur_hukmu(yg, KORELME_FIKSTURU)
    except Exception as e:                     # noqa: BLE001
        sinif2, olcum2 = "%s: %s" % (type(e).__name__, e), {}
    # KORELME: bu fiksturde yas (46,9 dk) TIKALI esiginin (65) ALTINDADIR -> hukum
    # YALNIZ hata zincirinden gelebilir. Zincir eksenini korelten bir onarim burada
    # AKIYOR verir ve yakalanir.
    eks2 = olcum2.get("eksenler") or {}
    kayit("Y5", "build dustu / deploy HIC kosmadi (skipped) -> hala TIKALI (yalniz zincirden)",
          sinif2 == "TIKALI" and eks2.get("hata_zinciri") and not eks2.get("yas_tikali"),
          "%s · zincir=%s · yas=%.1f dk (TIKALI yas esigi %d)"
          % (sinif2, olcum2.get("ardisik_hata"), olcum2.get("yas_dk") or 0,
             yg.TIKALI_YAS_DK))

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
    kayit("Y5", "etkin sonuc YALNIZ `deploy` isinden doguyor", not yanlis,
          "sapma: %s" % (yanlis or "-"))

    # Kosum YESIL ama beklenen is adi govdede YOK -> sekil degismis olabilir:
    # sessizce "yayinlamadi" saymak SAHTE KIRMIZI olurdu -> OLCULEMEDI.
    yesil = {"id": 1, "status": "completed", "conclusion": "success"}
    try:
        yg.yayin_taramasi([yesil], lambda k: {"jobs": [
            {"name": "baska-is", "status": "completed", "conclusion": "success",
             "completed_at": "2026-08-02T12:00:00Z"}]})
        sonuc = "istisna YOK"
    except yg.OlcumHatasi as e:
        sonuc = str(e)[:60]
    kayit("Y5", "yesil kosumda `deploy` isi HIC yoksa -> OLCULEMEDI (sahte kirmizi degil)",
          sonuc != "istisna YOK", sonuc)

    # `yayin` isi dusmusse SITE CANLIDIR (hukum degismez) ama bozulma GORUNUR olmali.
    _, _, _, olcum3 = _fikstur_hukmu(yg, YANLIS_ALARM_FIKSTURU)
    satirlar3 = " ".join(yg._ozet_satirlari(dict(olcum3, taslak_isi="failure")))
    kayit("Y5", "`yayin` isi dustuyse raporda GORUNUR (hukum degil, teshis)",
          yg.TASLAK_ISI in satirlar3 and "SITE CANLI" in satirlar3,
          "satir %s" % ("var" if "SITE CANLI" in satirlar3 else "YOK"))


# --------------------------------------- Y6) TESHIS ETIKETI + STDERR SIZINTISI
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


def y6_teshis_ve_sizinti(yg):
    kusur = yg.sizinti_kusurlari()
    kayit("Y6", "sizinti/teshis sozlesmesi TEMIZ", not kusur,
          "; ".join(kusur)[:160] or "-")

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
    kayit("Y6", "hata mesaji CAGRI ETIKETINI tasiyor (runs/jobs/compare ayirt ediliyor)",
          len(etiketli) == 3, "etiketli: %s" % (etiketli or "YOK"))
    kayit("Y6", "ayni metni basan iki uc AYRI mesaj uretiyor",
          mesajlar["runs"] != mesajlar["compare"],
          "runs != compare: %s" % (mesajlar["runs"] != mesajlar["compare"]))

    sizan = [e for e, m in mesajlar.items()
             if gizli in m or "GIZLI-DEPO" in m or "https://" in m]
    kayit("Y6", "`gh` stderr'indeki URL/yol mesaja SIZMIYOR", not sizan,
          "sizan: %s" % (sizan or "-"))
    kayit("Y6", "teshis YOK EDILMEDI: hata SINIFI hala gorunuyor",
          all("404" in m for m in mesajlar.values()), mesajlar["jobs"][:70])

    ozet = yg.gh_hata_sinifi("beklenmedik %s" % gizli)
    kayit("Y6", "taninmayan hata metninin ICERIGI basilmiyor",
          gizli not in ozet and "bayt" in ozet, ozet[:70])


# --------------------------------------------------- Y7) YAS TABANI = YAYIN ANI
def y7_yas_tabani(yg):
    """Taban `deploy` isinin BITISIDIR — kosumun BASLANGICI DEGIL (2 Agu olcumu)."""
    kusur = yg.yas_tabani_kusurlari()
    kayit("Y7", "yas tabani sozlesmesi TEMIZ (fikstur `%s.completed_at` bildiriyor)"
          % yg.YAYIN_ISI, not kusur, "; ".join(kusur)[:160] or "-")

    # VAKA (a): 2 Agu'nun GERCEK yanlis alarmi. Yeni tabanla YESIL — sari bile degil.
    sinif, beklenen, gerekce, olcum = _fikstur_hukmu(yg, VAKA_A_SAGLIKLI_KUYRUK)
    e1, e2 = _eksen_ozeti(olcum)
    kayit("Y7", "VAKA (a) %s: hat saglikli + kuyruk uzun -> AKIYOR (sari bile degil)"
          % VAKA_A_SAGLIKLI_KUYRUK,
          sinif == "AKIYOR" == beklenen and not e1 and not e2,
          "%s · yas=%.1f dk · eksen1=%s · eksen2=%s · %s"
          % (sinif, olcum.get("yas_dk") or 0, e1 or "-", e2, "; ".join(gerekce)[:60]))

    # TABANIN YERI: yas, KOSUM BASLANGICI degil YAYIN ANI uzerinden olculmus olmali.
    # Iki taban da fikstur govdesinden TURETILIR (capa sayi YOK).
    yayin_ani = olcum.get("yayin_ani")
    baslangic = olcum.get("son_basarili_baslangic")
    simdi_ = olcum.get("simdi")
    if yayin_ani and baslangic and simdi_:
        yeni = (simdi_ - yayin_ani).total_seconds() / 60.0
        eski = (simdi_ - baslangic).total_seconds() / 60.0
        # Fikstur en eski bekleyen commit'i kosum BASLANGICINDAN once tutar; boylece
        # ESKI taban = kosum baslangici, YENI taban = yayin ani olur ve ikisi AYRISIR.
        kayit("Y7", "yas YAYIN ANINDAN olculuyor (kosum baslangicindan DEGIL)",
              abs((olcum.get("yas_dk") or 0) - yeni) < 0.5
              and abs(yeni - eski) > 1.0,
              "yeni taban %.1f dk · eski taban %.1f dk · olculen %.1f dk"
              % (yeni, eski, olcum.get("yas_dk") or 0))
        # KANARI YUK TASIYOR MU: eski taban, OLCULEN saglikli tepe yasinin (51,8 dk)
        # USTUNDE bir sayi uretirdi — yani bu govde eski tabanla alarm sinifina duserdi.
        # Karsilastirma AYARLANABILIR esige (TIKALI_YAS_DK) DEGIL, OLCULEN tabana
        # baglanir: yoksa esigi gevseten bir mutant bu iddiayi da kirmizi yakar ve
        # "hangi eksen oldu" cevabi bulanir ([[hukum-yanlis-birimde]]).
        kayit("Y7", "ESKI tabanla ayni govde ALARM sinifina duserdi (kanari yuk tasiyor)",
              eski > yg.OLCULEN_SAGLIKLI_YAS_TAVANI_DK,
              "eski taban yasi %.1f dk > olculen saglikli tepe %.1f dk"
              % (eski, yg.OLCULEN_SAGLIKLI_YAS_TAVANI_DK))
    else:
        kayit("Y7", "yas tabani alanlari olcumde VAR (yayin_ani + baslangic)", False,
              "yayin_ani=%s baslangic=%s" % (yayin_ani, baslangic))

    # TABANIN VARLIGI: `--ff-only` ile gelen ESKI tarihli commit yasi sismemeli.
    sinif2, beklenen2, _, olcum2 = _fikstur_hukmu(yg, "ff-only-eski-tarihli")
    kayit("Y7", "ff-only ile gelen ESKI tarihli commit yasi SISIRMIYOR (taban duruyor)",
          sinif2 == beklenen2 == "AKIYOR",
          "%s · yas=%.1f dk" % (sinif2, olcum2.get("yas_dk") or 0))


# ------------------------------------------------- Y8) EKSEN 2: KOSUM OMUR TAVANI
def y8_omur_ekseni(yg):
    """Takilan kosum ekseni: `ahead_by` kapisinin ONUNDE, eksen 1'den BAGIMSIZ."""
    kusur = yg.omur_ekseni_kusurlari()
    kayit("Y8", "omur ekseni sozlesmesi TEMIZ (kapi onunde + normal omur yakmiyor)",
          not kusur, "; ".join(kusur)[:160] or "-")

    # VAKA (b): kosum basladi, omur tavanini asti -> EKSEN 2 KIRMIZI, EKSEN 1 TEMIZ.
    sinif, beklenen, gerekce, olcum = _fikstur_hukmu(yg, VAKA_B_TAKILAN_KOSUM)
    e1, e2 = _eksen_ozeti(olcum)
    kayit("Y8", "VAKA (b) %s: TIKALI ve hukum YALNIZ eksen 2'den" % VAKA_B_TAKILAN_KOSUM,
          sinif == "TIKALI" == beklenen and e2 and not e1,
          "%s · omur=%.1f dk · eksen1=%s · eksen2=%s"
          % (sinif, olcum.get("takilan_kosum_dk") or 0, e1 or "-", e2))
    kayit("Y8", "VAKA (b) bekleyen commit YOKKEN de hukum veriliyor (ahead_by kapisi onu)",
          not olcum.get("geride"), "geride=%s" % olcum.get("geride"))
    kayit("Y8", "VAKA (b) gerekcede takilan kosum ADIYLA gorunuyor (teshis var)",
          any(str(olcum.get("takilan_kosum_id")) in g for g in gerekce),
          "; ".join(gerekce)[:80])

    # KONTROL: OLCULEN en uzun kosum omru (49,1 dk) alarm URETMEMELI.
    sinif2, beklenen2, _, olcum2 = _fikstur_hukmu(yg, "takilan-kosum-normal")
    e1b, e2b = _eksen_ozeti(olcum2)
    kayit("Y8", "KONTROL takilan-kosum-normal: olculen EN UZUN normal omur alarm URETMIYOR",
          sinif2 == beklenen2 == "AKIYOR" and not e2b and not e1b,
          "%s · omur=%.1f dk (tavan %d) · eksen1=%s"
          % (sinif2, olcum2.get("takilan_kosum_dk") or 0, yg.KOSUM_OMUR_TAVANI_DK,
             e1b or "-"))

    # MASKELEME YOK: eksen 2 yandiginda eksen 1'in gerekcesi KAYBOLMAZ.
    # Eksen 1 BURADA hata zincirinden yakilir (yas'tan degil): yas kullanmak bu iddiayi
    # ACLIK kuralinin (`iptal_zinciri VE yas_gecikme`) mutantlarina da baglardi ve eksen
    # ayrimi bulanirdi.
    ikisi = {"geride": 3, "yas_dk": 1.0, "ardisik_iptal": 0,
             "ardisik_hata": yg.TIKALI_HATA_ZINCIR + 1, "son_basarili_sha": "abc12345",
             "pencere": 1, "tamamlanan": 1, "taranan": 1,
             "takilan_kosum_dk": yg.KOSUM_OMUR_TAVANI_DK + 10.0, "takilan_kosum_id": 7}
    sinif3, gerekce3 = yg.degerlendir(ikisi)
    kayit("Y8", "IKI eksen birden yandiginda IKI gerekce de raporlaniyor (maskeleme yok)",
          sinif3 == "TIKALI" and len(gerekce3) >= 2
          and any("ARDISIK dusen kosum" in g for g in gerekce3)
          and any("TAMAMLANMADI" in g for g in gerekce3),
          "%s · %d gerekce" % (sinif3, len(gerekce3)))


# ---------------------------------------------------------------- kosum
IDDIALAR = (("Y1", "EKSEN 1 — bekleyen icerik (yas/zincir/birikme)"),
            ("Y2", "SOZLESME — sinif kodlari + esiklerin olculen tabani"),
            ("Y3", "PANO KABLOSU — durum.py bolum 9"),
            ("Y4", "BAGIMSIZLIK + SERIT — deploy.yml"),
            ("Y5", "IS DUZEYI — yayin yetkilisi `deploy` isi"),
            ("Y6", "TESHIS + SIZINTI — gh stderr"),
            ("Y7", "YAS TABANI — yayin ani"),
            ("Y8", "EKSEN 2 — kosum omur tavani"))


def main():
    print("YAYIN GECIKME NOBETCISI — KABUL TESTI")
    print("-" * 78)
    try:
        yg = _modul("yayin_gecikme_nobeti", os.path.join(TOOLS,
                                                         "yayin-gecikme-nobeti.py"))
        suzgec = _modul("pruvo_icra_suzgeci", os.path.join(TOOLS, "icra-suzgeci.py"))
        iak = _modul("pruvo_is_akisi_kapisi", os.path.join(TOOLS, "is-akisi-kapisi.py"))
    except Exception as e:                     # noqa: BLE001
        print("  ✘ FAIL-CLOSED: gerekli modul yuklenemedi — %s: %s" % (type(e).__name__, e))
        print("IDDIA SAYISI: 0")
        print("KIRMIZI IDDIA: %s" % ",".join(k for k, _ in IDDIALAR))
        return 1

    # Cokme SESSIZ olmasin ve KIRMIZI ile karismasin: eksen kirmizi kumeye girer ama
    # gerekcesi ACIKCA "COKTU" yazar ([[hukum-yanlis-birimde]]).
    kosumlar = (("Y1", lambda: y1_icerik_ekseni(yg)),
                ("Y2", lambda: y2_sozlesme(yg)),
                ("Y3", y3_pano_kablosu),
                ("Y4", lambda: y4_bagimsizlik(suzgec, iak)),
                ("Y5", lambda: y5_is_duzeyi(yg)),
                ("Y6", lambda: y6_teshis_ve_sizinti(yg)),
                ("Y7", lambda: y7_yas_tabani(yg)),
                ("Y8", lambda: y8_omur_ekseni(yg)))
    for kod, fn in kosumlar:
        try:
            fn()
        except Exception as e:                 # noqa: BLE001
            kayit(kod, "IDDIA COKTU: %s: %s" % (type(e).__name__, e), False)

    for s in SATIRLAR:
        print(s)
    print("-" * 78)
    print("IDDIA SAYISI: %d" % len(SATIRLAR))
    print("KIRMIZI IDDIA: %s" % (",".join(sorted(KIRMIZI)) or "-"))
    print("SONUC: %d/%d gecti" % (len(SATIRLAR) - len(HATALAR), len(SATIRLAR)))
    for h in HATALAR:
        print("  ✘ " + h)
    return 1 if HATALAR else 0


if __name__ == "__main__":
    sys.exit(main())
