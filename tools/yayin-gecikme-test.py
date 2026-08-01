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
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
NOBETCI_YOL = "tools/yayin-gecikme-nobeti.py"
BU_TEST_YOL = "tools/yayin-gecikme-test.py"
DEPLOY = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

# Fikstur envanteri TABANI — buyuyebilir, ALTINA DUSEMEZ (bkz. modul basligi).
FIKSTUR_TABANI = 15
ZORUNLU_SINIFLAR = ("AKIYOR", "GECIKME", "TIKALI", "ACLIK", "OLCULEMEDI")

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

    basarisiz = [a for a, g, _ in SONUC if not g]
    print("")
    print("SONUC: %d/%d gecti" % (len(SONUC) - len(basarisiz), len(SONUC)))
    for a in basarisiz:
        print("  ✘ %s" % a)
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
