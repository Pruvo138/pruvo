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
  Y9  EKSEN 3 — YAYINSIZ ZINCIR
  Y10 YAS TABANI 3. ALT SINIR — main'e GIRIS ani (26 Eyl); olculemezse eski taban + not
  Y11 BAYAT DILIM (K429, 1 Eki) — runs ucunun bayat kesitinden KESIN hukum cikmaz: fuzyon +
      bagimsiz tazelik kaniti (commits API) + tavan asilirsa OLCULEMEDI

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
import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
NOBETCI_YOL = "tools/yayin-gecikme-nobeti.py"
BU_TEST_YOL = "tools/yayin-gecikme-test.py"
DEPLOY = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
# 5 Agu 2026: SERIT B adimlari (bloklamayan nobet/alarm) ayri is akisinda.
NOBET = os.path.join(ROOT, ".github", "workflows", "nobet.yml")

# Fikstur envanteri TABANI — buyuyebilir, ALTINA DUSEMEZ (bkz. modul basligi).
# 5 Agu: 21 -> 22 (EKSEN 3 kanarisi `bugun-iki-yayinsiz`; o gecenin GERCEK govdesi).
# 26 Eyl: 22 -> 25 (Y10 main'e giris ani kanarilari A/B/C).
# 1 Eki: 25 -> 32 (Y11 bayat dilim: a/b/c/d + tolerans · bot commit · ek cekim).
FIKSTUR_TABANI = 32
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
    # YAYINSIZ ZINCIR ekseninin kanarisi: 5 Agu gecesinin GERCEK govdesi. O gece IKI
    # hizli eksen de SUSTU (hata zinciri 2'de kaldi / yas 61 dk, TIKALI esigi 65) ve
    # yayin 74 dk durdu. Yanlis-alarm kontrolu FIKSTURDE DEGIL birim iddiadadir
    # (y9_yayinsiz_zinciri): zincir 1 · zincir>=2 ama yas<50 · bekleyen icerik yok.
    "Y9": ("bugun-iki-yayinsiz",),
    # MAIN'E GIRIS ANI ekseninin UC kanarisi (26 Eyl 2026): A yanlis alarmin GERCEK govdesi
    # (sessizlik + taze push -> YESIL), B gercek tikanma yonu (giristen 70 dk -> TIKALI),
    # C kaynak olculemedi (eski taban + OLCULEMEDI notu, sessiz yesil YOK).
    "Y10": ("giris-sessizlik-taze-push", "giris-70dk-yayinsiz", "giris-olculemedi"),
    # BAYAT DILIM ekseninin YEDI fiksturu (K429): dort spec vakasi + uc sinir vakasi.
    "Y11": ("bayat-ilk-cekim-taze-ikinci", "bayat-tum-cekimler", "taze-gercek-tikanma",
            "komit-api-yok-fuzyon", "bayat-taze-commit-tolerans", "bayat-bot-commit-atlanir",
            "bayat-ek-cekim-tavan-icinde"),
}
VAKA_GIRIS_A = "giris-sessizlik-taze-push"
VAKA_GIRIS_B = "giris-70dk-yayinsiz"
VAKA_GIRIS_C = "giris-olculemedi"

# BAYAT DILIM (K429, 1 Eki 2026) — fikstur adlari. (a)-(d) mimar spec'inin dort vakasi;
# gerisi sinir vakalari. HEPSI Y11'e aittir (baska eksende yargilanmaz).
VAKA_BAYAT_A = "bayat-ilk-cekim-taze-ikinci"        # (a) ilk bayat / ikinci taze -> AKIYOR + not
VAKA_BAYAT_B = "bayat-tum-cekimler"                 # (b) hepsi bayat -> OLCULEMEDI, ASLA TIKALI
VAKA_BAYAT_C = "taze-gercek-tikanma"                # (c) taze + gercekten yayinsiz -> TIKALI KALIR
VAKA_BAYAT_D = "komit-api-yok-fuzyon"               # (d) commits API yok -> yalniz fuzyon + ILAN
VAKA_TOLERANS = "bayat-taze-commit-tolerans"        # HEAD <5 dk, kosumu listede yok -> TOLERANS
VAKA_BOT = "bayat-bot-commit-atlanir"               # HEAD bot commit'i -> aday ATLANIR
VAKA_EK_CEKIM = "bayat-ek-cekim-tavan-icinde"       # ilk 3 bayat, 4. taze -> AKIYOR

YANLIS_ALARM_FIKSTURU = "bugun-serit-b-dustu"
KORELME_FIKSTURU = "bugun-build-dustu"
# KABUL VAKALARI (mimar spec'i): (a) saglikli-uzun-kuyruk · (b) takilan kosum ·
# (c) yayin inmiyor · (d) normal dongu.
VAKA_A_SAGLIKLI_KUYRUK = "bugunku-kuyruk-saglikli"
VAKA_B_TAKILAN_KOSUM = "takilan-kosum-bekleyen-yok"
VAKA_C_YAYIN_INMIYOR = "bugun-tikali"
VAKA_D_NORMAL = "normal"

EKSEN_1_ADLARI = ("yas_gecikme", "yas_tikali", "hata_zinciri", "iptal_zinciri", "birikme",
                  "yayinsiz_zinciri")
EKSEN_2_ADI = "sure_tavani"
EKSEN_3_ADI = "yayinsiz_zinciri"

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
def _deploy_cagrilari(suzgec, iak, is_akisi=None):
    """<is_akisi>'ndaki (job_id, yol, argumanlar) uclulerinin listesi.

    `run:` degerleri GERCEK ayristiriciyla cozulur (metin taklidi YOK) ve her satirin
    ANLAMLI bir icra olup olmadigina ortak suzgec (tools/icra-suzgeci.py) karar verir.

    🔴 5 Agu 2026 SERIT AYRIMI: SERIT B adimlari deploy.yml'den nobet.yml'e TASINDI
    (bloklamayan joblarin kirmizisi yayin kosumunun rengini boyamasin diye,
    [[hukum-yanlis-birimde]]). Fonksiyon artik dosya alir: BAGIMSIZLIK iddiasi
    (canli kol yayin is akisinda KOSMASIN) deploy.yml'den, SERIT iddiasi
    (kabul testi bloklamayan seritte KOSSUN) nobet.yml'den olculur.
    """
    yol_ = is_akisi or DEPLOY
    ad_ = os.path.basename(yol_)
    with open(yol_, encoding="utf-8") as f:
        metin = f.read()
    govde, hata = iak.ayristir(metin)
    if govde is None:
        raise RuntimeError("%s ayristirilamadi: %s" % (ad_, hata))
    serit_b, tani = iak._serit_b_joblar(govde, ad_)
    if serit_b is None:
        raise RuntimeError("%s serit B joblari olculemedi: %s" % (ad_, tani))
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
        cagrilar, _d_serit_b = _deploy_cagrilari(suzgec, iak, DEPLOY)
        n_cagrilar, serit_b = _deploy_cagrilari(suzgec, iak, NOBET)
    except Exception as e:                     # noqa: BLE001
        # FAIL-CLOSED: olculemeyen kablolama "sorun yok" DEGILDIR.
        kayit("Y4", "BAGIMSIZLIK olculdu", False, "%s: %s" % (type(e).__name__, e))
        return

    # CANLI kol IKI is akisinda da kosmamali: deploy.yml'de yayini durdururdu,
    # nobet.yml'de ise nobetci OLCTUGU HATTA bagimli hale gelirdi (hat tikandiginda
    # o da kosamaz -> tam ihtiyac aninda susar; 1 Agu'da olculen ariza budur).
    canli = [(j, a) for j, y, a in (cagrilar + n_cagrilar)
             if y == NOBETCI_YOL and "--kendini-test" not in a and "--liste" not in a]
    kayit("Y4", "BAGIMSIZLIK: nobetcinin CANLI OLCUM kolu CI'da (deploy.yml + "
          "nobet.yml) KOSMUYOR", not canli, "ihlal: %s" % (canli if canli else "-"))

    kendi = [(j, a) for j, y, a in n_cagrilar if y == BU_TEST_YOL]
    kayit("Y4", "bu kabul testi nobet.yml'de FIILEN kosuyor (olu nobetci degil)",
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
    ikisi = {"geride": 3, "yas_dk": 1.0, "ardisik_iptal": 0, "ardisik_yayinsiz": 0,
             "ardisik_hata": yg.TIKALI_HATA_ZINCIR + 1, "son_basarili_sha": "abc12345",
             "pencere": 1, "tamamlanan": 1, "taranan": 1,
             "takilan_kosum_dk": yg.KOSUM_OMUR_TAVANI_DK + 10.0, "takilan_kosum_id": 7}
    sinif3, gerekce3 = yg.degerlendir(ikisi)
    kayit("Y8", "IKI eksen birden yandiginda IKI gerekce de raporlaniyor (maskeleme yok)",
          sinif3 == "TIKALI" and len(gerekce3) >= 2
          and any("ARDISIK dusen kosum" in g for g in gerekce3)
          and any("TAMAMLANMADI" in g for g in gerekce3),
          "%s · %d gerekce" % (sinif3, len(gerekce3)))

    # ── KABUL TESTI (14 Agu, mimar hukmu Y1/Y2) — tavan 128 dk'lik BES vaka ──
    # (1) 86,6 dk NORMAL -> ALARM YOK (bugunku sahte alarm sinifi kapanir).
    # (2) 143,5 dk takilan -> ALARM VAR. (3) 169,1 dk -> ALARM VAR.
    # (4) TAM ESIK 128 dk -> `>=` kurali geregi ALARM VAR (dahil; beyan edildi).
    # (5) kosum listesi BOS -> OLCULEMEDI + rc != 0 (fail-closed, sessiz yesil YOK).
    # Bu bes vaka OLDURUCU MUTANTLARIN hedefidir (bkz. tools/yayin-gecikme-mutasyon.py
    # :: V1/V2/V3) — her mutant buradaki TAM BIR vakayi kirmizi yakar.
    def _omur_olcum(dk):
        return {"geride": 0, "yas_dk": 0.0, "ardisik_iptal": 0, "ardisik_hata": 0,
                "ardisik_yayinsiz": 0, "son_basarili_sha": "abc12345", "pencere": 1,
                "tamamlanan": 1, "taranan": 1, "takilan_kosum_dk": dk,
                "takilan_kosum_id": 1}

    kayit("Y8", "KABUL (1) 86,6 dk NORMAL kosum -> ALARM YOK (sahte alarm sinifi kapanir)",
          yg.degerlendir(_omur_olcum(yg.OLCULEN_KOSUM_OMRU_MAX_DK))[0] == "AKIYOR",
          "omur %.1f dk < tavan %d dk" % (yg.OLCULEN_KOSUM_OMRU_MAX_DK,
                                          yg.KOSUM_OMUR_TAVANI_DK))
    kayit("Y8", "KABUL (2) 143,5 dk takilan kosum -> ALARM VAR (gercek takilma yakalanir)",
          yg.degerlendir(_omur_olcum(143.5))[0] == "TIKALI",
          yg.degerlendir(_omur_olcum(143.5))[0])
    kayit("Y8", "KABUL (3) 169,1 dk takilan kosum -> ALARM VAR",
          yg.degerlendir(_omur_olcum(169.1))[0] == "TIKALI",
          yg.degerlendir(_omur_olcum(169.1))[0])
    kayit("Y8", "KABUL (4) TAM esik %d dk -> ALARM VAR (`>=` kurali, esik DAHIL)"
          % yg.KOSUM_OMUR_TAVANI_DK,
          yg.degerlendir(_omur_olcum(float(yg.KOSUM_OMUR_TAVANI_DK)))[0] == "TIKALI",
          "esik %d dahil (>=)" % yg.KOSUM_OMUR_TAVANI_DK)

    def _bos_getir(yol_, zaman_asimi=25, etiket="api"):   # noqa: ARG001
        return {"workflow_runs": []}
    sinif5, rc5, _, _ = yg.olc_ve_degerlendir(getir=_bos_getir)
    kayit("Y8", "KABUL (5) kosum listesi BOS -> OLCULEMEDI + rc!=0 (fail-closed, "
          "sessiz yesil YOK)",
          sinif5 == "OLCULEMEDI" and rc5 != 0, "%s rc %d" % (sinif5, rc5))


# ------------------------------------------------- Y9) EKSEN 3: YAYINSIZ ZINCIR
def _sentetik(yg, **ustyazim):
    """Nobetcinin `olcum` sozlugunun EN KUCUK gecerli hali — eksen izolasyonu icin.
    Alanlar EKSIK BIRAKILMAZ: `eksen_hukumleri` dogrudan indeksler (fail-closed), yani
    yeni bir eksen alani eklendiginde bu yardimci DA guncellenmek zorundadir."""
    taban = {"geride": 3, "yas_dk": 0.0, "ardisik_iptal": 0, "ardisik_hata": 0,
             "ardisik_yayinsiz": 0, "son_basarili_sha": "abc12345", "pencere": 1,
             "tamamlanan": 1, "taranan": 1, "takilan_kosum_dk": None,
             "takilan_kosum_id": None}
    taban.update(ustyazim)
    return taban


def y9_yayinsiz_zinciri(yg):
    """EKSEN 3: "kostu ama YAYINLAMADI" zinciri — 5 Agu'da olculen kor noktanin nobeti.

    O gece IKI hizli eksen de sustu ve yayin 74 dk durdu (nobetci her 15 dk kostu).
    Burada hem ALARMIN DOGDUGU hem NORMAL halde DOGMADIGI ayri ayri olculur.
    """
    # (1) GERCEK GOVDE: 5 Agu 01:13Z tigi -> TIKALI ve hukum YALNIZ eksen 3'ten.
    sinif, beklenen, gerekce, olcum = _fikstur_hukmu(yg, "bugun-iki-yayinsiz")
    eks = olcum.get("eksenler") or {}
    yalniz3 = (eks.get(EKSEN_3_ADI)
               and not eks.get("hata_zinciri") and not eks.get("yas_tikali")
               and not eks.get("iptal_zinciri") and not eks.get("birikme")
               and not eks.get(EKSEN_2_ADI))
    kayit("Y9", "5 Agu GERCEK govdesi: TIKALI ve hukum YALNIZ eksen 3'ten",
          sinif == beklenen == "TIKALI" and yalniz3,
          "%s · yayinsiz=%s yas=%.0f dk · eksenler=%s"
          % (sinif, olcum.get("ardisik_yayinsiz"), olcum.get("yas_dk") or 0,
             sorted(a for a, v in eks.items() if v)))
    kayit("Y9", "gerekce YAYINSIZ zinciri ADIYLA soyluyor (teshis var, sayi var)",
          any("YAYINLAMADI" in g and str(olcum.get("ardisik_yayinsiz")) in g
              for g in gerekce), "; ".join(gerekce)[:100])

    # (2) O GECE MEVCUT ESIKLERIN IKISI DE SUSUYORDU — kor nokta CALISTIRILARAK gosterilir.
    kayit("Y9", "AYNI govde MEVCUT eksenlerin ikisinde de SESSIZ (5 Agu kor noktasi)",
          (olcum.get("ardisik_hata") or 0) < yg.TIKALI_HATA_ZINCIR
          and (olcum.get("yas_dk") or 0) < yg.TIKALI_YAS_DK,
          "hata zinciri %s (esik %d) · yas %.0f dk (esik %d)"
          % (olcum.get("ardisik_hata"), yg.TIKALI_HATA_ZINCIR,
             olcum.get("yas_dk") or 0, yg.TIKALI_YAS_DK))

    # (3) YANLIS-ALARM KAPILARI — ucu de TEK BASINA olculur.
    tek = _sentetik(yg, ardisik_yayinsiz=yg.TIKALI_YAYINSIZ_ZINCIR - 1,
                    yas_dk=yg.GECIKME_YAS_DK + 30.0)
    kayit("Y9", "KONTROL: zincir esigin ALTINDA (%d) -> eksen 3 SESSIZ"
          % (yg.TIKALI_YAYINSIZ_ZINCIR - 1),
          not yg.eksen_hukumleri(tek)[EKSEN_3_ADI])
    taze = _sentetik(yg, ardisik_yayinsiz=yg.TIKALI_YAYINSIZ_ZINCIR + 3,
                     yas_dk=yg.GECIKME_YAS_DK - 1.0)
    kayit("Y9", "KONTROL: zincir uzun ama bekleyen icerik TAZE (yas < %d dk) -> SESSIZ "
          "(olculen bedel: 2,51 -> 0,89 alarm/gun)" % yg.GECIKME_YAS_DK,
          not yg.eksen_hukumleri(taze)[EKSEN_3_ADI])
    bekleyensiz = _sentetik(yg, geride=0, yas_dk=0.0,
                            ardisik_yayinsiz=yg.TIKALI_YAYINSIZ_ZINCIR + 9)
    kayit("Y9", "KONTROL: bekleyen icerik YOKKEN uzun zincir alarm URETMIYOR "
          "(ahead_by kapisi)", yg.degerlendir(bekleyensiz)[0] == "AKIYOR",
          yg.degerlendir(bekleyensiz)[0])

    # (4) MASKELEME YOK: eksen 3 ile hata zinciri AYNI ANDA yanabilir ve IKI gerekce de kalir.
    ikisi = _sentetik(yg, ardisik_hata=yg.TIKALI_HATA_ZINCIR + 1,
                      ardisik_yayinsiz=yg.TIKALI_HATA_ZINCIR + 1,
                      yas_dk=yg.GECIKME_YAS_DK + 5.0)
    _s, ger = yg.degerlendir(ikisi)
    kayit("Y9", "eksen 3 ile hata zinciri birbirini MASKELEMIYOR (iki ayri gerekce)",
          _s == "TIKALI" and any("ARDISIK dusen kosum" in g for g in ger)
          and any("YAYINLAMADI" in g for g in ger), "%s · %d gerekce" % (_s, len(ger)))

    # (5) SINIF SOZLESMESI: `cancelled` zincire GIRMEZ (deponun kendi kanarisi olculdu).
    kayit("Y9", "`cancelled` YAYINSIZ sinifina girmiyor + sinif hata sonuclarini KAPSIYOR",
          "cancelled" not in yg.YAYINSIZ_SONUCLARI
          and not (set(yg.HATA_SONUCLARI) - set(yg.YAYINSIZ_SONUCLARI)),
          "YAYINSIZ_SONUCLARI=%s" % (yg.YAYINSIZ_SONUCLARI,))

    # (6) ESIK OLCULEN TABANIN USTUNDE (sozlesme nobeti ayrica kosar; burada TEK TEK).
    kayit("Y9", "esik olculen saglikli tavanin USTUNDE ve hata zinciri esiginden KUCUK",
          yg.OLCULEN_SAGLIKLI_YAYINSIZ_TAVANI < yg.TIKALI_YAYINSIZ_ZINCIR
          < yg.TIKALI_HATA_ZINCIR,
          "tavan %d < esik %d < hata esigi %d"
          % (yg.OLCULEN_SAGLIKLI_YAYINSIZ_TAVANI, yg.TIKALI_YAYINSIZ_ZINCIR,
             yg.TIKALI_HATA_ZINCIR))


# ------------------------------------------- Y10) YAS TABANI 3. ALT SINIR: MAIN'E GIRIS
def _cli_rc(yg, ad):
    """`--fikstur <ad>` CLI yolunun cikis kodu (borusuz; ciktisi yutulur, rc OKUNUR)."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = yg.main(["--fikstur", ad])
    return rc, tampon.getvalue()


def _dk(simdi, an):
    return (simdi - an).total_seconds() / 60.0


def y10_giris_ani(yg):
    """26 Eyl 2026: taban = max(commit, yayin ani, MAIN'E GIRIS ani); giris olculemezse
    ESKI taban + OLCULEMEDI notu. Uc kanari + ayiklayicinin fail-closed kollari."""
    # (A) GERCEK YANLIS ALARM: sessizlik 63 dk + 13 dk'lik bekleyen commit, deploy kosuyor.
    sinif, beklenen, gerekce, o = _fikstur_hukmu(yg, VAKA_GIRIS_A)
    rc, _ = _cli_rc(yg, VAKA_GIRIS_A)
    kayit("Y10", "A %s: AKIYOR rc=0 (26 Eyl yanlis alarmi kapandi)" % VAKA_GIRIS_A,
          sinif == beklenen == "AKIYOR" and rc == 0,
          "%s rc %d · yas=%.1f dk · %s" % (sinif, rc, o.get("yas_dk") or -1,
                                            "; ".join(gerekce)[:60]))
    giris, simdi_, yayin = o.get("giris_ani"), o.get("simdi"), o.get("yayin_ani")
    # Iddia SAYISI her kosulda AYNI kalir (alan yoksa iki iddia da KIRMIZI yazilir):
    # mutasyon surucusu sayi dususunu "test coktu" diye okur.
    tam = bool(giris and simdi_ and yayin)
    kayit("Y10", "A: yas MAIN'E GIRIS anindan olculuyor (taban adi + sayi)",
          tam and abs((o.get("yas_dk") or 0) - _dk(simdi_, giris)) < 0.5
          and o.get("yas_tabani") == "main'e giris ani",
          "giris %s · olculen %.1f dk · taban=%s · durum=%s"
          % (tam and "%.1f dk" % _dk(simdi_, giris), o.get("yas_dk") or 0,
             o.get("yas_tabani"), o.get("giris_durum")))
    # KANARI YUK TASIYOR MU: ayni govde ESKI tabanla (yayin ani) TIKALI esigini asardi.
    kayit("Y10", "A: ESKI taban (yayin ani) ayni govdede TIKALI esigini asardi "
          "(kanari yuk tasiyor)", tam and _dk(simdi_, yayin) >= yg.TIKALI_YAS_DK,
          "eski taban yasi %s · esik %d"
          % (tam and "%.1f dk" % _dk(simdi_, yayin), yg.TIKALI_YAS_DK))

    # (B) GERCEK TIKANMA: icerik 70 dk once main'e girdi, yayin yok.
    sinif, beklenen, gerekce, o = _fikstur_hukmu(yg, VAKA_GIRIS_B)
    rc, _ = _cli_rc(yg, VAKA_GIRIS_B)
    kayit("Y10", "B %s: TIKALI rc=3 ve hukum yas ekseninden" % VAKA_GIRIS_B,
          sinif == beklenen == "TIKALI" and rc == 3
          and bool((o.get("eksenler") or {}).get("yas_tikali")),
          "%s rc %d · yas=%.1f dk · %s" % (sinif, rc, o.get("yas_dk") or -1,
                                            "; ".join(gerekce)[:60]))
    giris, simdi_ = o.get("giris_ani"), o.get("simdi")
    kayit("Y10", "B: giris = son yayinlanan sha'dan SONRAKI ILK push (en yeni push DEGIL)",
          bool(giris and simdi_) and abs(_dk(simdi_, giris) - 70.0) < 0.5
          and abs((o.get("yas_dk") or 0) - 70.0) < 0.5,
          "giris %s · yas %.1f dk" % (giris and giris.strftime("%H:%M"), o.get("yas_dk") or 0))

    # (C) KAYNAK OLCULEMEDI: eski davranis + OLCULEMEDI notu (sessiz yesil YOK).
    sinif, beklenen, gerekce, o = _fikstur_hukmu(yg, VAKA_GIRIS_C)
    rc, cikti = _cli_rc(yg, VAKA_GIRIS_C)
    # Eski tabanin KENDISI (yayin ani mi, commit tarihi mi) Y7'nin iddiasidir; burada
    # yalniz "giris tabana GIRMEDI, yas A'nin 13 dk'sina DUSMEDI, alarm KALDI" olculur.
    kayit("Y10", "C %s: ESKI davranis — TIKALI rc=3, giris tabana girmedi" % VAKA_GIRIS_C,
          sinif == beklenen == "TIKALI" and rc == 3 and o.get("giris_ani") is None
          and (o.get("yas_dk") or 0) >= yg.TIKALI_YAS_DK,
          "%s rc %d · yas=%.1f dk" % (sinif, rc, o.get("yas_dk") or -1))
    kayit("Y10", "C: OLCULEMEDI notu olcumde + ozet satirinda + gerekcede (ILAN edildi)",
          str(o.get("giris_durum") or "").startswith(yg.GIRIS_OLCULEMEDI)
          and "main'e giris ani: %s" % yg.GIRIS_OLCULEMEDI in cikti
          and any(yg.GIRIS_OLCULEMEDI in g for g in gerekce),
          "durum=%s" % (str(o.get("giris_durum"))[:60],))

    # (D) AYIKLAYICI fail-closed kollari — dogrudan, fikstursuz (kod olgusu).
    import datetime as _dt
    simdi = _dt.datetime(2026, 9, 26, 18, 0, tzinfo=_dt.timezone.utc)
    sablon = {"after": "b" * 40, "before": "a" * 40, "ref": "refs/heads/main",
              "timestamp": "2026-09-26T17:00:00Z", "activity_type": "push"}

    def _patlar_mi(govde):
        try:
            yg.giris_anini_ayikla(govde, "a" * 40, simdi)
        except yg.OlcumHatasi:
            return True
        return False
    kayit("Y10", "ayiklayici: eslesen push YOK / gelecek damga / eksik alan / bos -> "
          "OlcumHatasi (eski tabana duser)",
          _patlar_mi([dict(sablon, before="c" * 40)])
          and _patlar_mi([dict(sablon, timestamp="2026-09-26T18:30:00Z")])
          and _patlar_mi([{k: v for k, v in sablon.items() if k != "before"}])
          and _patlar_mi([]) and _patlar_mi({"x": 1}))
    iki = [dict(sablon, timestamp="2026-09-26T17:30:00Z"),
           dict(sablon, timestamp="2026-09-26T16:40:00Z"),
           dict(sablon, activity_type="branch_deletion", timestamp="2026-09-26T15:00:00Z")]
    g = yg.giris_anini_ayikla(iki, "A" * 40, simdi)
    kayit("Y10", "ayiklayici: birden cok eslesmede EN ESKI alinir, dal silme sayilmaz, "
          "sha buyuk/kucuk harf duyarsiz", g.strftime("%H:%M") == "16:40",
          g.strftime("%H:%M"))


# ------------------------------------------------ Y11) BAYAT DILIM (K429, 1 Eki 2026)
def _olc(yg, ad, ust=None):
    """Fiksturu (istege bagli ust-yazimla) KOSTURUR -> (sinif, rc, gerekce, olcum)."""
    getir, simdi, _beklenen, _ = yg.fikstur_yukle(ad, ust=ust)
    sinif, rc, gerekce, olcum = yg.olc_ve_degerlendir(getir=getir, simdi=simdi)
    return sinif, rc, gerekce, (olcum or {})


def _ozet(yg, olcum):
    return "\n".join(yg._ozet_satirlari(olcum)) if olcum else ""


def _eski_tek_cekim(yg, ad):
    """ESKI davranisi (TEK cekim, tazelik kaniti YOK) yeniden kurar -> (sinif, rc).

    Kanari yuk tasiyor mu sorusunun cevabi: bayat dilim fiksturu, eski kuralla bakilsa gercekten
    KESIN TIKALI verir mi? Vermiyorsa fikstur bayat-dilim sinifini TEMSIL ETMIYOR demektir.
    """
    eski = (yg.CEKIM_MIN, yg.CEKIM_TAVAN)
    yg.CEKIM_MIN = yg.CEKIM_TAVAN = 1
    try:
        sinif, rc, _, _ = _olc(yg, ad, ust={"_komit_hata": "eski davranis: tazelik kaniti YOK"})
    finally:
        yg.CEKIM_MIN, yg.CEKIM_TAVAN = eski
    return sinif, rc


def _bekleme_olcumu(yg, ad, gercek_ag, ust=None):
    """`kosumlari_cek` icinde cagrilan bekleme sureleri. `gercek_ag=True`: `getir is
    api_getir` kolu (time.sleep ESLENIR, gercekten UYUNMAZ); False: fikstur kolu."""
    getir, simdi, _, _ = yg.fikstur_yukle(ad, ust=ust)
    uyku = []
    eski_time, eski_api = yg.time, yg.api_getir
    yg.time = types.SimpleNamespace(sleep=lambda sn: uyku.append(sn))
    if gercek_ag:
        yg.api_getir = getir
    try:
        try:
            yg.kosumlari_cek(getir, simdi)
        except yg.OlcumHatasi:
            pass
    finally:
        yg.time, yg.api_getir = eski_time, eski_api
    return uyku


def _kom_ust(yg, ad, duzenle):
    """Fikstur `komitler` listesinin KOPYASINI `duzenle(liste)` ile degistirip `ust` dondurur."""
    ham = yg._fikstur_ham(ad)
    kom = copy.deepcopy(ham["komitler"])
    duzenle(kom)
    return {"komitler": kom}


def _komut_govdesi(sha, tarih, mesaj="x", yazan="insan", yazan2=None):
    return {"sha": sha, "commit": {"committer": {"date": tarih}, "message": mesaj},
            "author": {"login": yazan}, "committer": {"login": yazan2 or yazan}}


def y11_bayat_dilim(yg):
    """K429: runs ucunun BAYAT kesitinden KESIN hukum cikmaz.

    12/12 kirmizi (`yayin-nabzi` / TIKALI) ayni sinifti: GitHub ayni uca ardisik cagrilarda once
    haftalarca eski, kendi icinde tutarli bir kesit, sonra tazesini verdi. Onarimin iki ayagi
    (fuzyon + bagimsiz tazelik kaniti) ve iki yonlu risk burada olculur: bayat dilim TIKALI
    URETMEZ, ama gercek tikanma da bayat SAYILMAZ.
    """
    # ---- (a) ilk cekim bayat / ikinci taze -> AKIYOR + not ------------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_BAYAT_A)
    d, ozet = o.get("dilim") or {}, _ozet(yg, o)
    kayit("Y11", "(a) ilk cekim bayat / ikinci taze: AKIYOR rc=0 (fuzyon taze nesli kullandi)",
          sinif == "AKIYOR" and rc == 0, "%s rc %d" % (sinif, rc))
    kayit("Y11", "(a) satir `BAYAT DILIM` notunu + KACINCI cekimde taze bulundugunu tasiyor",
          d.get("cekim") == 3 and d.get("bayat_cekim") == 1 and d.get("ilk_taze_cekim") == 2
          and "⚙ BAYAT DILIM" in ozet and "2. cekimde" in ozet,
          "cekim=%s bayat=%s ilk_taze=%s" % (d.get("cekim"), d.get("bayat_cekim"),
                                             d.get("ilk_taze_cekim")))
    ek, ek_rc = _eski_tek_cekim(yg, VAKA_BAYAT_B)
    kayit("Y11", "KANARI YUK TASIYOR: (b)'nin bayat dilimi TEK cekimle bakilinca KESIN TIKALI "
          "(eski davranis = 12/12 kirmizinin sinifi)", ek == "TIKALI" and ek_rc == 3,
          "eski kural: %s rc %s" % (ek, ek_rc))

    # ---- (b) tum cekimler bayat -> OLCULEMEDI rc=2, ASLA TIKALI -------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_BAYAT_B)
    mesaj = " ".join(ger)
    kayit("Y11", "(b) k cekimin HEPSI bayat: OLCULEMEDI rc=2 ve ASLA TIKALI/ACLIK/AKIYOR",
          sinif == "OLCULEMEDI" and rc == 2, "%s rc %d" % (sinif, rc))
    kayit("Y11", "(b) gerekce: `BAYAT DILIM` + cekim sayisi + HEAD sha + KAPATAN OLCUM ADIYLA",
          "BAYAT DILIM" in mesaj and ("%d cekim" % yg.CEKIM_TAVAN) in mesaj
          and "a0a0a0a0" in mesaj and "KAPATAN OLCUM" in mesaj, mesaj[:90])
    # tavan SINIRI: 5. cekimde taze gelirse hukum VAR, 6. cekimde gelirse (tavan asildi) YOK.
    s5, _, _, _ = _olc(yg, VAKA_BAYAT_B,
                       ust={"_cekimler": ["bayat:4"] * (yg.CEKIM_TAVAN - 1) + ["taze"]})
    s6, _, _, _ = _olc(yg, VAKA_BAYAT_B,
                       ust={"_cekimler": ["bayat:4"] * yg.CEKIM_TAVAN + ["taze"]})
    kayit("Y11", "tavan siniri: %d. cekimde taze -> AKIYOR; %d. cekimde taze (tavan ASILDI) -> "
          "OLCULEMEDI" % (yg.CEKIM_TAVAN, yg.CEKIM_TAVAN + 1),
          s5 == "AKIYOR" and s6 == "OLCULEMEDI", "%d.=%s · %d.=%s"
          % (yg.CEKIM_TAVAN, s5, yg.CEKIM_TAVAN + 1, s6))

    # ---- (c) taze + gercekten yayinsiz -> TIKALI KALIR ----------------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_BAYAT_C)
    d, ozet = o.get("dilim") or {}, _ozet(yg, o)
    kayit("Y11", "(c) taze + gercekten yayinsiz (5 hata, 185 dk): TIKALI rc=3 KALIR — "
          "onarim 'bayat say, sus' DEGIL", sinif == "TIKALI" and rc == 3,
          "%s rc %d" % (sinif, rc))
    kayit("Y11", "(c) bagimsiz kanit TAZE, bayat cekim 0, `BAYAT DILIM` notu YOK",
          d.get("durum") == "TAZE" and d.get("bayat_cekim") == 0 and "BAYAT DILIM" not in ozet,
          "durum=%s bayat=%s" % (d.get("durum"), d.get("bayat_cekim")))

    # ---- (d) commits API yok -> yalniz fuzyon + ILAN ------------------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_BAYAT_D)
    d, ozet = o.get("dilim") or {}, _ozet(yg, o)
    kayit("Y11", "(d) commits API yok: fuzyon bayat ilk cekimi YINE duzeltir (pencere TAM) -> "
          "AKIYOR", sinif == "AKIYOR" and rc == 0 and o.get("pencere") == 10,
          "%s rc %d pencere=%s" % (sinif, rc, o.get("pencere")))
    kayit("Y11", "(d) satir `tazelik kaniti: YOK` + hata SINIFI ILAN ediyor (sessiz ikame yok)",
          d.get("durum") == "KANIT_YOK" and d.get("bayat_cekim") is None
          and "tazelik kaniti: YOK" in ozet and "sunucu hatasi" in ozet,
          "durum=%s" % d.get("durum"))

    # ---- sinir: HEAD <5 dk -> TOLERANS (sahte OLCULEMEDI YOK) ---------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_TOLERANS)
    d, ozet = o.get("dilim") or {}, _ozet(yg, o)
    kayit("Y11", "HEAD 5 dk'dan taze, kosumu listede yok: AKIYOR + TOLERANS notu (OLCULEMEDI "
          "DEGIL)", sinif == "AKIYOR" and d.get("durum") == "TOLERANS" and "TOLERANS" in ozet,
          "%s durum=%s" % (sinif, d.get("durum")))
    alt, _, _, o_alt = _olc(yg, VAKA_TOLERANS, ust=_kom_ust(yg,
        VAKA_TOLERANS, lambda k: k[0]["commit"]["committer"].update(date="2026-10-01T14:55:01Z")))
    ust_, _, _, _ = _olc(yg, VAKA_TOLERANS, ust=_kom_ust(yg,
        VAKA_TOLERANS, lambda k: k[0]["commit"]["committer"].update(date="2026-10-01T14:54:59Z")))
    kayit("Y11", "tolerans SINIRI: 4,98 dk -> AKIYOR (TOLERANS) · 5,02 dk -> OLCULEMEDI (BAYAT)",
          alt == "AKIYOR" and (o_alt.get("dilim") or {}).get("durum") == "TOLERANS"
          and ust_ == "OLCULEMEDI", "4,98 dk=%s · 5,02 dk=%s" % (alt, ust_))

    # ---- sinir: bot / [skip ci] commit'i aday OLAMAZ ------------------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_BOT)
    d = o.get("dilim") or {}
    kayit("Y11", "HEAD bot commit'i (kosumu YOK): aday ATLANIR, onceki insan commit'i TAZE -> "
          "AKIYOR (kalici sahte OLCULEMEDI YOK)",
          sinif == "AKIYOR" and d.get("durum") == "TAZE" and d.get("aday_sha") == "a1a1a1a1",
          "%s durum=%s aday=%s" % (sinif, d.get("durum"), d.get("aday_sha")))
    ci, _, _, o_ci = _olc(yg, VAKA_BOT, ust=_kom_ust(yg, VAKA_BOT, lambda k: (
        k[0].update(author={"login": "insan"}, committer={"login": "insan"}),
        k[0]["commit"].update(message="veri senkronu [SKIP CI]"))))
    kayit("Y11", "`[skip ci]` isaretli HEAD (buyuk/kucuk harf duyarsiz) da aday OLAMAZ",
          ci == "AKIYOR" and (o_ci.get("dilim") or {}).get("aday_sha") == "a1a1a1a1", ci)
    insan, _, _, _ = _olc(yg, VAKA_BOT, ust=_kom_ust(yg, VAKA_BOT, lambda k: k[0].update(
        author={"login": "insan"}, committer={"login": "insan"})))
    kayit("Y11", "NEGATIF KONTROL: ayni HEAD INSAN commit'iyse kosumu BEKLENIR -> pencerede yok "
          "-> OLCULEMEDI (bot kurali yuk tasiyor)", insan == "OLCULEMEDI", insan)

    # ---- sinir: ek cekim (tavan icinde) -------------------------------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_EK_CEKIM)
    d, ozet = o.get("dilim") or {}, _ozet(yg, o)
    kayit("Y11", "ilk 3 cekim bayat, 4. taze: AKIYOR + `4. cekimde bulundu` (ek cekim gorunur)",
          sinif == "AKIYOR" and d.get("cekim") == 4 and d.get("bayat_cekim") == 3
          and d.get("ilk_taze_cekim") == 4 and "4. cekimde" in ozet,
          "cekim=%s bayat=%s ilk_taze=%s" % (d.get("cekim"), d.get("bayat_cekim"),
                                             d.get("ilk_taze_cekim")))

    # ---- fuzyon: updated_at'i en YENI nesil kazanir; bayat ILERI uyduramaz --------------
    def _k(kid, olus, durum, sonuc, guncel):
        return {"id": kid, "status": durum, "conclusion": sonuc, "created_at": olus,
                "run_started_at": olus, "updated_at": guncel, "head_sha": "x", "event": "push"}
    bayat_nesil = [_k(1, "2026-10-01T10:00:00Z", "in_progress", None, "2026-10-01T10:05:00Z")]
    taze_nesil = [_k(1, "2026-10-01T10:00:00Z", "completed", "failure", "2026-10-01T10:30:00Z"),
                  _k(2, "2026-10-01T11:00:00Z", "completed", "success", "2026-10-01T11:20:00Z")]
    f1 = yg.kosumlari_fuzyonla([bayat_nesil, taze_nesil])
    f2 = yg.kosumlari_fuzyonla([taze_nesil, bayat_nesil])
    kayit("Y11", "fuzyon: id basina `updated_at` EN YENI nesil kazanir (sira BAGIMSIZ), sonuc "
          "created_at azalan", [k["id"] for k in f1] == [2, 1] and f1 == f2
          and f1[1]["status"] == "completed" and f1[1]["conclusion"] == "failure",
          "ids=%s esit=%s" % ([k["id"] for k in f1], f1 == f2))
    bir_cekim = yg.kosumlari_fuzyonla([bayat_nesil])
    cift = yg.kosumlari_fuzyonla([taze_nesil, taze_nesil])
    kayit("Y11", "fuzyon: bayat nesil ILERI uyduramaz (tek basina yalniz kendi kaydini verir) "
          "ve ayni kosumu iki kez saymaz", bir_cekim == bayat_nesil
          and [k["id"] for k in cift] == [2, 1] and len(cift) == 2,
          "tek cekim ids=%s · cift=%s" % ([k["id"] for k in bir_cekim],
                                          [k["id"] for k in cift]))

    # ---- ayiklayici + yardimcilar -------------------------------------------------------
    import datetime as _dt
    simdi = _dt.datetime(2026, 10, 1, 15, 0, tzinfo=_dt.timezone.utc)
    govde = [_komut_govdesi("AA" * 20, "2026-10-01T14:40:00Z", yazan="x[bot]"),
             _komut_govdesi("BB" * 20, "2026-10-01T14:30:00Z", yazan="insan", yazan2="y[bot]"),
             _komut_govdesi("CC" * 20, "2026-10-01T14:20:00Z", mesaj="a [Skip CI] b"),
             _komut_govdesi("DD" * 20, "2026-10-01T14:10:00Z", yazan=None),
             _komut_govdesi("EE" * 20, "2026-10-01T14:00:00Z")]
    govde[3]["author"] = None            # iliskisiz e-posta: GERCEK `panel:` commit'lerinde null
    k = yg.komitleri_ayikla(govde, simdi)
    kayit("Y11", "komit ayiklayici: bot (author YA DA committer) ve [skip ci] ATLANIR; login "
          "null (iliskisiz e-posta) bot DEGILDIR; sha kucuk harfe cevrilir",
          [x["atlanir"] for x in k] == ["bot", "bot", "ci-atla", None, None]
          and k[0]["sha"] == "aa" * 20 and abs(k[0]["yas_dk"] - 20.0) < 0.01
          and yg.tazelik_adayi(k)["sha"] == "dd" * 20,
          "atlanir=%s" % [x["atlanir"] for x in k])
    ci_hepsi = all(yg.komitleri_ayikla([_komut_govdesi("ab" * 20, "2026-10-01T14:00:00Z",
                                                       mesaj="m %s" % m)], simdi)[0]["atlanir"]
                   for m in yg.CI_ATLAMA_ISARETLERI)
    kayit("Y11", "GitHub'in belgeli bes `skip ci` isaretinin HEPSI taniniyor", ci_hepsi,
          ", ".join(yg.CI_ATLAMA_ISARETLERI))

    def _patlar(g):
        try:
            yg.komitleri_ayikla(g, simdi)
        except yg.OlcumHatasi:
            return True
        return False
    kayit("Y11", "komit ayiklayici FAIL-CLOSED: liste degil / bos / sha-commit eksik / tarih "
          "eksik / bos sha -> OlcumHatasi",
          _patlar({"x": 1}) and _patlar([]) and _patlar([{"sha": "a"}])
          and _patlar([{"sha": "a", "commit": {}}]) and _patlar([{"sha": "a", "commit": {
              "committer": {}}}]) and _patlar([_komut_govdesi("", "2026-10-01T14:00:00Z")]),
          "")
    aday = {"sha": "ab" * 20, "yas_dk": 10.0}
    taze_aday = {"sha": "ab" * 20, "yas_dk": yg.TAZELIK_TOLERANS_DK - 0.1}
    sinir_aday = {"sha": "ab" * 20, "yas_dk": float(yg.TAZELIK_TOLERANS_DK)}
    pencere = [{"head_sha": "AB" * 20}]
    kayit("Y11", "pencere tazeligi: sha var -> TAZE (buyuk/kucuk harf duyarsiz) · yok+eski -> "
          "BAYAT · yok+<5 dk -> TOLERANS · tam 5 dk -> BAYAT · aday yok -> KANIT_YOK",
          yg.pencere_tazeligi(pencere, aday) == "TAZE"
          and yg.pencere_tazeligi([], aday) == "BAYAT"
          and yg.pencere_tazeligi([], taze_aday) == "TOLERANS"
          and yg.pencere_tazeligi([], sinir_aday) == "BAYAT"
          and yg.pencere_tazeligi(pencere, None) == "KANIT_YOK",
          "")

    # ---- pencere KESMESI: fuzyondan sonra PENCERE_KOSUM'a kirpilir ----------------------
    def _cok_getir(yol_, zaman_asimi=25, etiket="api"):     # noqa: ARG001 — imza ayni
        if "/commits?" in yol_:
            return [_komut_govdesi("%040x" % 59, "2026-10-01T14:30:00Z")]
        return {"workflow_runs": [
            {"id": 9000 + i, "status": "completed", "conclusion": "success",
             "created_at": "2026-10-01T13:%02d:00Z" % i, "run_started_at":
             "2026-10-01T13:%02d:00Z" % i, "updated_at": "2026-10-01T13:%02d:30Z" % i,
             "head_sha": "%040x" % i, "event": "push"} for i in range(60)]}
    cok, cok_dilim = yg.kosumlari_cek(_cok_getir, simdi)
    kayit("Y11", "fuzyondan sonra pencere PENCERE_KOSUM'a KIRPILIR (en yeni %d kosum, "
          "created_at azalan)" % yg.PENCERE_KOSUM,
          len(cok) == yg.PENCERE_KOSUM and cok[0]["id"] == 9059
          and cok[-1]["id"] == 9059 - (yg.PENCERE_KOSUM - 1) and cok_dilim["durum"] == "TAZE",
          "n=%d ilk=%s son=%s" % (len(cok), cok[0]["id"], cok[-1]["id"]))

    # ---- cekim mekanigi: URL farkli · bekleme yalniz EK cekimde ve yalniz GERCEK agda ----
    getir, simdi_f, _, _ = yg.fikstur_yukle(VAKA_BAYAT_B)
    yollar = []

    def _kayitli(yol_, zaman_asimi=25, etiket="api"):
        yollar.append(yol_)
        return getir(yol_, zaman_asimi, etiket)
    yg.olc_ve_degerlendir(getir=_kayitli, simdi=simdi_f)
    runs = [y for y in yollar if "/actions/workflows/" in y]
    kayit("Y11", "her cekim FARKLI URL (per_page degisir): bayat yanit URL'ye takilip tekrar "
          "etmez; commits (git) cagrisi ISE runs cekimlerinden ONCE",
          len(runs) == yg.CEKIM_TAVAN and len(set(runs)) == len(runs)
          and yollar and "/commits?" in yollar[0], "runs=%d farkli=%d" % (len(runs),
                                                                        len(set(runs))))
    fikstur_kolu = _bekleme_olcumu(yg, VAKA_BAYAT_B, gercek_ag=False)
    gercek_kol_b = _bekleme_olcumu(yg, VAKA_BAYAT_B, gercek_ag=True)
    gercek_kol_a = _bekleme_olcumu(yg, VAKA_BAYAT_A, gercek_ag=True)
    kayit("Y11", "bekleme: fikstur kolunda HIC; gercek ag kolunda YALNIZ ek cekimlerden once "
          "(%d sn x %d); taze yolda 0" % (yg.CEKIM_ARASI_SN, yg.CEKIM_TAVAN - yg.CEKIM_MIN),
          fikstur_kolu == []
          and gercek_kol_b == [yg.CEKIM_ARASI_SN] * (yg.CEKIM_TAVAN - yg.CEKIM_MIN)
          and gercek_kol_a == [],
          "fikstur=%s gercek(b)=%s gercek(a)=%s" % (fikstur_kolu, gercek_kol_b, gercek_kol_a))

    # ---- kismi cekim hatasi ve tam cekim hatasi -----------------------------------------
    sinif, rc, ger, o = _olc(yg, VAKA_BAYAT_A,
                             ust={"_cekimler": ["hata:gh sunucu hatasi (5xx)", "taze", "taze"]})
    d, ozet = o.get("dilim") or {}, _ozet(yg, o)
    kayit("Y11", "1/3 cekim HATA: kalan cekimle devam + `⚙ 1/3 cekim BASARISIZ` ILAN (hata "
          "sinifi gorunur)", sinif == "AKIYOR" and d.get("hatali") == 1
          and d.get("basarili") == 2 and "⚙ 1/3 cekim BASARISIZ" in ozet
          and "sunucu hatasi" in ozet, "%s hatali=%s" % (sinif, d.get("hatali")))
    sinif, rc, ger, _ = _olc(yg, VAKA_BAYAT_A,
                             ust={"_cekimler": ["hata:ILK-HATA", "hata:IKINCI", "hata:UCUNCU"]})
    kayit("Y11", "HIC cekim basarili degil: OLCULEMEDI rc=2 ve ILK hata AYNEN yukari cikar",
          sinif == "OLCULEMEDI" and rc == 2 and "ILK-HATA" in " ".join(ger)
          and "IKINCI" not in " ".join(ger), " ".join(ger)[:60])

    # ---- sabitler spec'e bagli ----------------------------------------------------------
    kayit("Y11", "sabitler: CEKIM_MIN >= 3 (fuzyon) · CEKIM_TAVAN == 5 · tolerans 5 dk · "
          "tavan > min",
          yg.CEKIM_MIN >= 3 and yg.CEKIM_TAVAN == 5 and yg.CEKIM_TAVAN > yg.CEKIM_MIN
          and yg.TAZELIK_TOLERANS_DK == 5,
          "min=%s tavan=%s tolerans=%s" % (yg.CEKIM_MIN, yg.CEKIM_TAVAN,
                                           yg.TAZELIK_TOLERANS_DK))


# ---------------------------------------------------------------- kosum
IDDIALAR = (("Y1", "EKSEN 1 — bekleyen icerik (yas/zincir/birikme)"),
            ("Y2", "SOZLESME — sinif kodlari + esiklerin olculen tabani"),
            ("Y3", "PANO KABLOSU — durum.py bolum 9"),
            ("Y4", "BAGIMSIZLIK + SERIT — deploy.yml"),
            ("Y5", "IS DUZEYI — yayin yetkilisi `deploy` isi"),
            ("Y6", "TESHIS + SIZINTI — gh stderr"),
            ("Y7", "YAS TABANI — yayin ani"),
            ("Y8", "EKSEN 2 — kosum omur tavani"),
            ("Y9", "EKSEN 3 — yayinsiz zincir (kostu ama yayinlaMADI)"),
            ("Y10", "YAS TABANI 3. ALT SINIR — main'e giris ani (activity)"),
            ("Y11", "BAYAT DILIM — fuzyon + bagimsiz tazelik kaniti (K429)"))


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
                ("Y8", lambda: y8_omur_ekseni(yg)),
                ("Y9", lambda: y9_yayinsiz_zinciri(yg)),
                ("Y10", lambda: y10_giris_ani(yg)),
                ("Y11", lambda: y11_bayat_dilim(yg)))
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
