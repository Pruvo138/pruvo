#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yayin-erisim-nobeti.py KABUL TESTI — hukum + KUME + KABLOLAMA.

Nobetcinin fiksturleri burada kosar, AMA bu dosyanin asil isi HUKMU EKSEN EKSEN
nobetlemektir: bir yayin-erisim nobetcisi ya YANLIS YERE baglanarak, ya kumesi sessizce
daralarak, ya da METOT (HEAD/GET) ekseninden koreltilerek ise yaramaz hale gelir.

🔴 FIKSTUR GERCEK BIR HTTP SUNUCUSUDUR (gercek soket + gercek yanit satirlari), kendi
varsayimimizi aynalayan bir simulator DEGIL ([[nobetci-fikstur-sekli]]). Govdeler
3 Agu 2026'da CANLIDAN olculen sekli tasir (9 baytlik `Forbidden` duz metin;
ayni yol HEAD'e 200).

🔴 EKSENLER (her IDDIA tam BIR eksene aittir; mutasyon surucusu bu kodlari olcer)
================================================================================
  E1  KUME       — elle liste YOK: kume KAYNAKLARDAN turer, kaynak kaynak SAYILIR,
                   /urun/ eksen disidir, TABAN altina dusen kume OLCULEMEDI'dir
  E2  YONTEM     — GET; HEAD YETMEZ (ayirt edici fikstur: HEAD 200 / GET 403)
  E3  HUKUM      — 200 disi her sey KAPALI · hepsi 200 -> ACIK (yanlis-pozitif yok)
  E4  YONLENDIRME— zincir izlenir: 3xx->200 sapma DEGIL ama raporlanir; dongu/tavan KAPALI
  E5  FAIL-CLOSED— ag/zaman asimi -> OLCULEMEDI (rc 2), YESIL DEGIL; kanit arizayi EZER
  E6  MALIYET    — hiz siniri FIILEN uygulanir · sure olculur · ORNEKLEME YOK ·
                   kapsam SAYIYLA beyan edilir
  E7  KABLOLAMA  — canli kol AYRI cron alarm kolundadir (yayini durduramaz), bu kabul
                   testi deploy.yml serit B'de FIILEN kosar, canli kol deploy.yml'de KOSMAZ
  E8  TEKRAR     — GECICI 5xx (Pages rollout penceresi) kalici kapalidan AYRILIR: 5xx/ag
                   3 kez denenir, 4xx ASLA denenmez, toparlanan URL ⚠️ GECICI olarak
                   RAPORLANIR, tum denemeler basarisizsa hukum AYNEN KAPALI/OLCULEMEDI

Cikis: 0 = hepsi gecti, 1 = en az bir kusur. Dis ag YOK (yalniz 127.0.0.1 fiksturu).
"""
import os
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
NOBETCI_YOL = "tools/yayin-erisim-nobeti.py"
BU_TEST_YOL = "tools/yayin-erisim-test.py"
DEPLOY = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
# 5 Agu 2026: SERIT B adimlari (bloklamayan nobet/alarm) ayri is akisinda.
NOBET = os.path.join(ROOT, ".github", "workflows", "nobet.yml")
ALARM_ADI = "yayin-erisim-alarmi.yml"
ALARM = os.path.join(ROOT, ".github", "workflows", ALARM_ADI)

# Fikstur yol envanteri TABANI — buyuyebilir, ALTINA DUSEMEZ: fikstur listesini
# kucultmek nobetciyi sessizce oldurmenin en ucuz yoludur.
FIKSTUR_TABANI = 11

SATIRLAR = []
KIRMIZI = set()
HATALAR = []


def kayit(kod, ad, gecti, detay=""):
    SATIRLAR.append(("  ✔ " if gecti else "  ✘ ")
                    + "%-3s %s%s" % (kod, ad, ("  — " + detay) if detay else ""))
    if not gecti:
        KIRMIZI.add(kod)
        HATALAR.append("%s %s%s" % (kod, ad, ("  — " + detay) if detay else ""))


def _uykusuz(_sn):
    """Gecici-5xx backoff'unu notrler (bkz. E5): DETERMINISTIK bekleyis, olcum DEGIL.
    Backoff'un DEGERI E8'de AYRICA iddia edilir; burada notrlemek hicbir iddiayi
    korletmez, yalnizca duvar saatini kisaltir."""
    return None


def _modul(ad, yol):
    import importlib.util
    if not os.path.exists(yol):
        raise RuntimeError("%s YOK" % yol)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


# --------------------------------------------------------------- sentetik kaynak agaci
SAYFALAR_SABLONU = """# sentetik fikstur
STATIK_SAYFALAR = %r
CONTENT_PAGES = [(s, "b", "m", lambda: "") for s in %r]
SITEMAP_SLUGS = STATIK_SAYFALAR + [s for s, _b, _m, _f in CONTENT_PAGES]
"""
HUB_SABLONU = "HUB_SLUG = %r\n"


def sentetik_kok(statik, icerik, hub="hub-dizini", sitemap=None, manifest=None):
    kok = tempfile.mkdtemp(prefix="yayin-erisim-kok-")
    os.makedirs(os.path.join(kok, "tools"))
    with open(os.path.join(kok, "tools", "sayfalar.py"), "w", encoding="utf-8") as f:
        f.write(SAYFALAR_SABLONU % (statik, icerik))
    with open(os.path.join(kok, "tools", "landing_hub_build.py"), "w",
              encoding="utf-8") as f:
        f.write(HUB_SABLONU % hub)
    if sitemap is not None:
        govde = "".join("<url><loc>https://pruvo3d.com%s</loc></url>" % u
                        for u in sitemap)
        with open(os.path.join(kok, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write("<?xml version='1.0'?><urlset>%s</urlset>" % govde)
    if manifest is not None:
        with open(os.path.join(kok, "_yayin-icerik-dizinleri.txt"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(manifest) + "\n")
    return kok


def _bol(n, onek="landing"):
    return ["%s-%03d" % (onek, i) for i in range(n)]


# ------------------------------------------------------------------- E1) KUME
def e1_kume(ye):
    # 1) Kume TAM OLARAK kaynaklarin verdigidir (gomulu/elle liste olsaydi FAZLA cikardi).
    kok = sentetik_kok(["hakkimizda"], _bol(300), hub="hub-dizini")
    yollar, kaynaklar = ye.kume_turet(kok=kok)
    beklenen = set(["/hakkimizda/", "/hub-dizini/", "/"]
                   + ["/%s/" % s for s in _bol(300)])
    kayit("E1", "kume TAM OLARAK kaynaklarin verdigi (gomulu/elle URL YOK)",
          set(yollar) == beklenen,
          "fazla=%s eksik=%s" % (sorted(set(yollar) - beklenen)[:3],
                                 sorted(beklenen - set(yollar))[:3]))
    adlar = [k[0].split()[0] for k in kaynaklar]
    kayit("E1", "kaynak beyani K1-K5'i AYRI AYRI sayiyla basiyor",
          adlar[:5] == ["K1", "K2", "K3", "K4", "K5"], "%s" % adlar)

    # 2) /urun/ EKSEN DISI, /marka/ yalniz --kapsam ile (ikinci kopya acilmaz).
    kok2 = sentetik_kok(["hakkimizda"], _bol(300),
                        sitemap=["/urun/x/", "/marka/y/", "/sitemap-ozel/", "/"],
                        manifest=["marka", "hub-dizini"])
    y2, _ = ye.kume_turet(kok=kok2)
    kayit("E1", "/urun/ kumede YOK (eksen siniri: canli-saglik-kapisi K2)",
          not any(y.startswith("/urun/") for y in y2),
          "%s" % [y for y in y2 if y.startswith("/urun/")][:3])
    kayit("E1", "/marka/... varsayilan kapsamda YOK ama manifest ust dizini (/marka/) VAR",
          "/marka/y/" not in y2 and "/marka/" in y2 and "/sitemap-ozel/" in y2,
          "marka koku=%s sitemap ust=%s" % ("/marka/" in y2, "/sitemap-ozel/" in y2))
    y3, _ = ye.kume_turet(kok=kok2, kapsam="tam")
    kayit("E1", "--kapsam tam /marka/ sayfalarini EKLER (yerel sitemap kaynagi)",
          "/marka/y/" in y3 and len(y3) > len(y2), "tam=%d sayfa=%d" % (len(y3), len(y2)))

    # 3) FAIL-CLOSED: collapsed/bos kaynak -> hukum YOK.
    for ad, kok_ in (("kume TABANIN altinda", sentetik_kok(["a"], ["b", "c"])),
                     ("SITEMAP_SLUGS BOS", sentetik_kok([], []))):
        try:
            ye.kume_turet(kok=kok_)
            oldu = "istisna YOK"
        except ye.OlcumHatasi as e:
            oldu = str(e)[:60]
        kayit("E1", "FAIL-CLOSED: %s -> OLCULEMEDI (bos kume 'hepsi acik' DEGIL)" % ad,
              oldu != "istisna YOK", oldu)

    # 4) --kapsam marka yerel sitemap ISTER; yoksa sessizce daralmaz.
    try:
        ye.kume_turet(kok=kok, kapsam="marka")
        oldu = "istisna YOK"
    except ye.OlcumHatasi as e:
        oldu = str(e)[:60]
    kayit("E1", "--kapsam marka sitemap yoksa OLCULEMEDI (sessiz daralma YOK)",
          oldu != "istisna YOK", oldu)

    # 5) GERCEK depo kaynagi: taban USTUNDE ve bugunku uretimle ORTUSUYOR.
    try:
        gercek, gercek_kaynak = ye.kume_turet(kok=ROOT)
        sayfalar = _modul("pruvo_sayfalar_test", os.path.join(TOOLS, "sayfalar.py"))
        bekleniyor = set("/%s/" % s for s in sayfalar.SITEMAP_SLUGS)
        kayit("E1", "GERCEK depo kumesi taban ustunde ve SITEMAP_SLUGS'i TAM kapsiyor",
              len(gercek) >= ye.KUME_TABANI and bekleniyor <= set(gercek),
              "%d URL (taban %d) · K1 %d slug"
              % (len(gercek), ye.KUME_TABANI, len(sayfalar.SITEMAP_SLUGS)))
        kayit("E1", "GERCEK kumede en az bir 'ara' onekli landing VAR (olculen kusur "
              "sinifi kor nokta olmasin)",
              any(y.startswith("/ara") for y in gercek),
              "%s" % [y for y in gercek if y.startswith("/ara")][:2])
        _ = gercek_kaynak
    except ye.OlcumHatasi as e:
        kayit("E1", "GERCEK depo kumesi turetilebiliyor", False, str(e)[:80])


# ------------------------------------------------------------------ E2) YONTEM
def e2_yontem(ye, sunucu):
    kayit("E2", "TEK KAYNAK: YONTEM == 'GET' (HEAD degil)", ye.YONTEM == "GET",
          repr(ye.YONTEM))
    ayirt = "/araba-guneslik-klipsi-yaptirma/"
    kayitlar, _ = ye.olc([ayirt], taban=sunucu.taban, hiz=0)
    sinif, rc, _, _ = ye.degerlendir(kayitlar)
    kayit("E2", "AYIRT EDICI VAKA (HEAD 200 / GET 403) -> KAPALI rc 1",
          sinif == "KAPALI" and rc == 1 and kayitlar[0]["kod"] == 403,
          "%s rc=%d kod=%s" % (sinif, rc, kayitlar[0]["kod"]))
    # KANARI YUK TASIYOR MU: ayni fikstur HEAD ile olculseydi YESIL yanardi.
    h, _ = ye.olc([ayirt], taban=sunucu.taban, hiz=0, yontem="HEAD")
    h_sinif, h_rc, _, _ = ye.degerlendir(h)
    kayit("E2", "KANARI: AYNI URL HEAD ile olculse ACIK cikardi (fikstur yuk tasiyor)",
          h_sinif == "ACIK" and h_rc == 0 and h[0]["kod"] == 200,
          "HEAD -> %s rc=%d kod=%s" % (h_sinif, h_rc, h[0]["kod"]))
    # Metoda DUYARSIZ 403 kontrolu: bu vaka HEAD mutantindan ETKILENMEZ (E3'un capasi).
    t, _ = ye.olc(["/tutarli-403/"], taban=sunucu.taban, hiz=0, yontem="HEAD")
    kayit("E2", "kontrol: metoda DUYARSIZ 403 HEAD ile de KAPALI (E3 capasi bagimsiz)",
          ye.degerlendir(t)[0] == "KAPALI", ye.degerlendir(t)[0])
    # TESHIS de metoda baglidir: HEAD govde GETIRMEZ -> kok neden (9 baytlik `Forbidden`
    # duz metni = worker rotasi imzasi) GORUNMEZ olur. Bu iddia yalniz GET ile gecer.
    g, _ = ye.olc(["/tutarli-403/"], taban=sunucu.taban, hiz=0)
    kayit("E2", "GET govdeyi de getirir -> teshis imzasi ('Forbidden') raporda GORUNUR "
          "(HEAD'de govde YOKTUR, teshis KOR kalirdi)",
          "Forbidden" in (g[0]["govde"] or ""), repr(g[0]["govde"]))


# ------------------------------------------------------------------- E3) HUKUM
def e3_hukum(ye, sunucu):
    kayit("E3", "TEK KAYNAK: ACIK_KODLAR == (200,)", tuple(ye.ACIK_KODLAR) == (200,),
          repr(ye.ACIK_KODLAR))
    kayitlar, _ = ye.olc(["/acik-1/", "/acik-2/", "/hedef/"], taban=sunucu.taban, hiz=0)
    sinif, rc, _, ozet = ye.degerlendir(kayitlar)
    kayit("E3", "KONTROL: hepsi 200 -> ACIK rc 0 (yanlis-pozitif YOK)",
          sinif == "ACIK" and rc == 0 and ozet["sayim"]["ACIK"] == 3,
          "%s rc=%d %s" % (sinif, rc, ozet["sayim"]))
    for yol, kod in (("/yok/", 404), ("/tutarli-403/", 403)):
        k, _ = ye.olc([yol], taban=sunucu.taban, hiz=0)
        s, r, _, _ = ye.degerlendir(k)
        kayit("E3", "OLDURUCU: %s (HTTP %d) -> KAPALI rc 1" % (yol, kod),
              s == "KAPALI" and r == 1 and k[0]["kod"] == kod,
              "%s rc=%d kod=%s" % (s, r, k[0]["kod"]))
    # TESHIS: kapali satir HTTP kodunu ve edge basliklarini TASIR (kok neden aranabilsin).
    # 🔴 GOVDE burada IDDIA EDILMEZ: govde metoda baglidir (HEAD govde getirmez) ve o
    # eksen E2'nindir; buraya koymak E2 mutantini E3'te de yakip eksen ayrimini bulandirir.
    k, _ = ye.olc(["/tutarli-403/"], taban=sunucu.taban, hiz=0)
    _, _, satirlar, _ = ye.degerlendir(k)
    kayit("E3", "kapali satir HTTP kodunu ve edge basliklarini tasiyor (kok neden aranabilir)",
          any("403" in s and "server=" in s for s in satirlar),
          "; ".join(satirlar)[:90])


# ------------------------------------------------------------ E4) YONLENDIRME
def e4_yonlendirme(ye, sunucu):
    k, _ = ye.olc(["/tasindi/"], taban=sunucu.taban, hiz=0)
    sinif, rc, satirlar, ozet = ye.degerlendir(k)
    kayit("E4", "301 -> 200: KAPALI DEGIL (musteri kapiyi acabiliyor)",
          sinif == "ACIK" and rc == 0, "%s rc=%d" % (sinif, rc))
    kayit("E4", "yonlendirme HEDEFIYLE raporlanir (sitemap kanonik URL vermeli)",
          len(ozet["yonlendirme"]) == 1
          and any("/hedef/" in s for s in satirlar), "; ".join(satirlar)[:80])
    k, _ = ye.olc(["/dongu-a/"], taban=sunucu.taban, hiz=0)
    sinif, rc, _, _ = ye.degerlendir(k)
    kayit("E4", "3xx DONGUSU -> KAPALI rc 1", sinif == "KAPALI" and rc == 1
          and k[0]["sinif"] == "DONGU", "%s rc=%d %s" % (sinif, rc, k[0]["sinif"]))
    k, _ = ye.olc(["/uzun-zincir/"], taban=sunucu.taban, hiz=0)
    sinif, _, _, _ = ye.degerlendir(k)
    kayit("E4", "zincir TAVANI asilirsa KAPALI (sonsuz takip YOK)",
          sinif == "KAPALI" and k[0]["sinif"] == "DONGU"
          and len(k[0]["zincir"]) <= ye.YONLENDIRME_TAVANI + 1,
          "%s zincir=%d tavan=%d" % (sinif, len(k[0]["zincir"]),
                                     ye.YONLENDIRME_TAVANI))


# ------------------------------------------------------------- E5) FAIL-CLOSED
def e5_fail_closed(ye, sunucu):
    # 🔴 `uyu=_uykusuz`: ag arizasi artik TEKRARLANIR (E8) ve aradaki backoff DETERMINISTIK
    # bir bekleyistir — GERCEK bir olcum degil. Backoff'un DEGERI E8'de AYRICA iddia edilir;
    # burada notrlenmesi iddiayi degil yalnizca duvar saatini etkiler (sure siniri, ag
    # zaman asiminin FIILEN uygulandigini olcmeye devam eder).
    k, _ = ye.olc(["/acik-1/"], taban=ye.olu_taban(), hiz=0, zaman_asimi=3, uyu=_uykusuz)
    sinif, rc, _, ozet = ye.degerlendir(k)
    kayit("E5", "ag YOK (baglanti reddedildi) -> OLCULEMEDI rc 2, YESIL DEGIL",
          sinif == "OLCULEMEDI" and rc == 2 and len(ozet["ariza"]) == 1,
          "%s rc=%d" % (sinif, rc))

    bas = time.monotonic()
    k, _ = ye.olc(["/yavas/"], taban=sunucu.taban, hiz=0, zaman_asimi=0.4, uyu=_uykusuz)
    sinif, rc, _, _ = ye.degerlendir(k)
    # SURE SINIRI DENEME BASINA TUREIR (ikiz sabit YOK): fikstur 2,0 sn bekler, zaman
    # asimi 0,4 sn. Sinir = deneme x 0,4 + 1,1 sn pay (E8 oncesi TEK denemede 1,5 sn olan
    # sinirin AYNISI, deneme basina). Zaman asimi UYGULANMAZSA her deneme 2,0 sn surer ve
    # bu sinir yine ASILIR -> iddia korelmedi.
    sure_siniri = ye.TEKRAR_SAYISI * 0.4 + 1.1
    kayit("E5", "ZAMAN ASIMI -> OLCULEMEDI rc 2 (gecikmeli uc yesil sayilmaz)",
          sinif == "OLCULEMEDI" and rc == 2 and (time.monotonic() - bas) < sure_siniri,
          "%s rc=%d (%.2f s < %.1f s)" % (sinif, rc, time.monotonic() - bas, sure_siniri))

    kayit("E5", "BOS kume -> OLCULEMEDI (hicbir sey olcmeyen kosum yesil DEGIL)",
          ye.degerlendir([])[0] == "OLCULEMEDI", ye.degerlendir([])[0])

    # KANIT ARIZAYI EZER: kapali kapi varken arac 'olculemedi'ye DUSMEZ, ama ariza da
    # kaybolmaz (iki sayi AYRI AYRI raporlanir).
    # 🔴 KANIT olarak DONGU secildi (durum KODU degil): 403/404'u "acik" sayan bir
    # mutant bu iddiayi da dusururdu ve E3/E5 ayrimi bulanirdi.
    kapali, _ = ye.olc(["/dongu-a/"], taban=sunucu.taban, hiz=0)
    ariza, _ = ye.olc(["/acik-1/"], taban=ye.olu_taban(), hiz=0, zaman_asimi=3,
                      uyu=_uykusuz)
    sinif, rc, _, ozet = ye.degerlendir(kapali + ariza)
    kayit("E5", "KANIT EZER: KAPALI + ARIZA birlikte -> KAPALI rc 1, ariza sayisi DURUYOR",
          sinif == "KAPALI" and rc == 1 and len(ozet["ariza"]) == 1
          and len(ozet["kapali"]) == 1, "%s rc=%d ariza=%d kapali=%d"
          % (sinif, rc, len(ozet["ariza"]), len(ozet["kapali"])))

    # ORNEKLEM: olculen sayi kume sayisindan KUCUKSE 'hepsi acik' denemez.
    acik, _ = ye.olc(["/acik-1/"], taban=sunucu.taban, hiz=0)
    sinif, rc, satirlar, _ = ye.degerlendir(acik, kume_sayisi=10)
    kayit("E5", "KIRPILMIS olcum (1/10) -> OLCULEMEDI + ORNEKLEM satiri",
          sinif == "OLCULEMEDI" and rc == 2
          and any("ORNEKLEM" in s for s in satirlar), "%s rc=%d" % (sinif, rc))

    kayit("E5", "SINIF_RC sozlesmesi: ACIK 0 · KAPALI 1 · OLCULEMEDI 2",
          ye.SINIF_RC == {"ACIK": 0, "KAPALI": 1, "OLCULEMEDI": 2}, repr(ye.SINIF_RC))


# ---------------------------------------------------------------- E6) MALIYET
def e6_maliyet(ye, sunucu):
    uykular = []
    yollar = ["/acik-1/", "/acik-2/", "/hedef/", "/acik-1/"]
    kayitlar, sure = ye.olc(yollar, taban=sunucu.taban, hiz=4.0,
                            uyu=lambda s: uykular.append(s))
    kayit("E6", "HIZ SINIRI FIILEN uygulaniyor (istekler arasi 1/hiz bekleme)",
          len(uykular) == len(yollar) - 1
          and all(abs(u - 0.25) < 1e-9 for u in uykular),
          "%d bekleme · %s" % (len(uykular), uykular[:2]))
    kayit("E6", "ORNEKLEME YOK: kumenin TAMAMI olculuyor",
          len(kayitlar) == len(yollar), "%d/%d" % (len(kayitlar), len(yollar)))
    kayit("E6", "SURE olculuyor (butce karari sayiyla verilsin)",
          isinstance(sure, float) and sure >= 0, "%.3f s" % sure)

    # KAPSAM BEYANI: cikti kume sayisini ve kapsam disini SAYIYLA yazar.
    kok = sentetik_kok(["hakkimizda"], _bol(300))
    yollar2, kaynaklar = ye.kume_turet(kok=kok)
    metin = "\n".join(ye.kaynak_satirlari(kaynaklar, yollar2, "sayfa"))
    kayit("E6", "KAPSAM SAYIYLA beyan ediliyor (birlesim + kapsam disi eksen)",
          "BIRLESIM" in metin and str(len(yollar2)) in metin
          and "KAPSAM DISI" in metin and "/urun/" in metin,
          metin.splitlines()[-2][:70])

    kayit("E6", "fikstur envanteri tabanin ustunde (>= %d)" % FIKSTUR_TABANI,
          len(ye.FIKSTUR_YOLLARI) >= FIKSTUR_TABANI,
          "%d fikstur yolu" % len(ye.FIKSTUR_YOLLARI))


# ------------------------------------------------------- E8) GECICI 5xx TEKRARI
class SahteAg:
    """`_istek` yerine gecen SCRIPTLI ag katmani — GERCEK ISTEK ATILMAZ.

    yanitlar: [("kod", 503), ("hata", "URLError: ..."), ("kod", 200), ...]
    Liste bitince SON yanit tekrarlanir; FAZLADAN cagri sessizce yutulmasin diye her
    vaka ATILAN ISTEK SAYISINI (self.cagri) AYRICA iddia eder — yalnizca sinifi iddia
    etmek "tekrar var mi yok mu" eksenini KOR birakirdi."""

    def __init__(self, yanitlar):
        self.yanitlar = list(yanitlar)
        self.cagri = 0

    def __call__(self, url, yontem=None, zaman_asimi=None, acici=None):
        self.cagri += 1
        tur, deger = self.yanitlar[min(self.cagri - 1, len(self.yanitlar) - 1)]
        if tur == "hata":
            return None, {}, b"", deger
        # 5xx govdesi 8 Agu 2026'da CANLIDAN olculen sekli tasir (GitHub Pages 5xx sayfasi).
        govde = (b"<!DOCTYPE html> <!-- Hello future GitHubber! I bet you're he"
                 if deger >= 500 else b"<!doctype html><title>PRUVO</title>")
        return deger, {"server": "cloudflare", "cf-cache-status": "DYNAMIC"}, govde, None


def _sahte_kosum(ye, yanitlar, yol="/interkom-diafon-ve-kapi-zili-plastik-parca-uretimi/"):
    """(sinif, rc, satirlar, ozet, atilan_istek, backoff_uykulari) — DIS AG YOK."""
    sahte = SahteAg(yanitlar)
    uykular = []
    eski = ye._istek
    ye._istek = sahte
    try:
        kayitlar, _ = ye.olc([yol], taban="http://olcum.fikstur.gecersiz", hiz=0,
                             uyu=lambda s: uykular.append(s))
    finally:
        ye._istek = eski
    sinif, rc, satirlar, ozet = ye.degerlendir(kayitlar)
    return sinif, rc, satirlar, ozet, sahte.cagri, uykular


def _gecici_satiri(satirlar):
    return [s for s in satirlar if s.startswith("⚠️ GECICI")]


def e8_gecici_5xx(ye, sunucu):
    # TEK KAYNAK: tekrar butcesi + SABIT backoff (jitter YOK -> deterministik test).
    kayit("E8", "TEK KAYNAK: TEKRAR_SAYISI == 3 · TEKRAR_BEKLEMELERI == (2.0, 4.0) "
          "(sabit backoff, JITTER YOK)",
          ye.TEKRAR_SAYISI == 3 and tuple(ye.TEKRAR_BEKLEMELERI) == (2.0, 4.0),
          "sayi=%r beklemeler=%r" % (ye.TEKRAR_SAYISI, ye.TEKRAR_BEKLEMELERI))

    # V1 — olculen ariza: Pages rollout penceresinde 503, sonra toparlanma.
    s, rc, satirlar, ozet, cagri, uykular = _sahte_kosum(
        ye, [("kod", 503), ("kod", 503), ("kod", 200)])
    kayit("E8", "V1 503->503->200: ACIK rc 0, ATILAN ISTEK 3, backoff [2.0, 4.0]",
          s == "ACIK" and rc == 0 and cagri == 3 and uykular == [2.0, 4.0],
          "%s rc=%d istek=%d uyku=%s" % (s, rc, cagri, uykular))
    kayit("E8", "V1 SESSIZ YESIL DEGIL: ozette ⚠️ GECICI satiri VAR ve ilk kodu tasiyor",
          len(_gecici_satiri(satirlar)) == 1
          and "ilk HTTP 503" in "".join(_gecici_satiri(satirlar))
          and len(ozet.get("gecici") or []) == 1,
          "; ".join(_gecici_satiri(satirlar))[:90] or "GECICI SATIRI YOK")
    kayit("E8", "V1 HUKUM satiri gecici toparlanmayi SAYIYLA basiyor",
          any(s2.startswith("HUKUM:") and "1 gecici toparlanma" in s2
              for s2 in satirlar),
          "; ".join(s2 for s2 in satirlar if s2.startswith("HUKUM:"))[:90])

    # V2 — GERCEK kesinti: alarm GEVSEMEDI, ucu de 5xx ise hukum AYNEN KAPALI.
    s, rc, satirlar, _, cagri, _ = _sahte_kosum(
        ye, [("kod", 503), ("kod", 503), ("kod", 503)])
    kayit("E8", "V2 503x3 (GERCEK kesinti): KAPALI rc 1, ATILAN ISTEK 3 — alarm "
          "GEVSETILMEDI", s == "KAPALI" and rc == 1 and cagri == 3,
          "%s rc=%d istek=%d" % (s, rc, cagri))
    kayit("E8", "V2 'GECICI' etiketi YOK (toparlanmayan 5xx gecici SAYILMAZ)",
          not _gecici_satiri(satirlar), "; ".join(_gecici_satiri(satirlar))[:80] or "-")

    # V3/V4 — 12 gun sessiz kalan OLCULMUS sinif: 4xx ILK denemede KAPALI, tekrar YOK.
    for kod, ad in ((404, "V3"), (403, "V4")):
        s, rc, satirlar, _, cagri, uykular = _sahte_kosum(ye, [("kod", kod)])
        kayit("E8", "%s %d tek deneme: KAPALI rc 1 ve ATILAN ISTEK 1 — 4xx'e tolerans "
              "EKLENMEDI" % (ad, kod),
              s == "KAPALI" and rc == 1 and cagri == 1 and uykular == [],
              "%s rc=%d istek=%d uyku=%s" % (s, rc, cagri, uykular))

    # V5/V6 — ag hatasi GECICI siniftadir: tekrarlanir, ama toparlanmazsa FAIL-CLOSED.
    s, rc, satirlar, _, cagri, _ = _sahte_kosum(
        ye, [("hata", "URLError: [Errno 61] Connection refused")])
    kayit("E8", "V5 ag hatasi x3: OLCULEMEDI rc 2, ATILAN ISTEK 3 (fail-closed KORUNDU)",
          s == "OLCULEMEDI" and rc == 2 and cagri == 3,
          "%s rc=%d istek=%d" % (s, rc, cagri))
    s, rc, satirlar, _, cagri, _ = _sahte_kosum(
        ye, [("hata", "timeout: The read operation timed out"), ("kod", 200)])
    kayit("E8", "V6 ag hatasi -> 200: ACIK rc 0, ATILAN ISTEK 2, GECICI satiri VAR",
          s == "ACIK" and rc == 0 and cagri == 2 and len(_gecici_satiri(satirlar)) == 1,
          "%s rc=%d istek=%d gecici=%s" % (s, rc, cagri, _gecici_satiri(satirlar)[:1]))

    # V7 KONTROL MUTANTI — saglikli yol YANLISLIKLA "gecici" etiketlenmesin.
    s, rc, satirlar, ozet, cagri, uykular = _sahte_kosum(ye, [("kod", 200)])
    kayit("E8", "V7 KONTROL: ilk denemede 200 -> ACIK rc 0, ATILAN ISTEK 1, GECICI "
          "satiri YOK, backoff YOK",
          s == "ACIK" and rc == 0 and cagri == 1 and not _gecici_satiri(satirlar)
          and uykular == [] and not (ozet.get("gecici") or []),
          "%s rc=%d istek=%d uyku=%s" % (s, rc, cagri, uykular))
    kayit("E8", "V7 HUKUM satiri '0 gecici toparlanma' diyor (sayi UYDURULMUYOR)",
          any(s2.startswith("HUKUM:") and "0 gecici toparlanma" in s2
              for s2 in satirlar),
          "; ".join(s2 for s2 in satirlar if s2.startswith("HUKUM:"))[:90])

    # 🔴 MALIYET: SAGLIKLI kosumda EK ISTEK 0 — GERCEK fikstur sunucusu uzerinde olculur
    # (328 URL'lik canli kosumun suresi degismesin diye; ek maliyet YALNIZ arizali URL'de).
    sayac = {"n": 0}
    eski = ye._istek

    def _sayan(url, yontem=None, zaman_asimi=ye.ZAMAN_ASIMI_VARSAYILAN, acici=None):
        sayac["n"] += 1
        return eski(url, yontem=yontem, zaman_asimi=zaman_asimi, acici=acici)

    uykular = []
    ye._istek = _sayan
    try:
        yollar = ["/acik-1/", "/acik-2/", "/hedef/"]
        kayitlar, _ = ye.olc(yollar, taban=sunucu.taban, hiz=0,
                             uyu=lambda s2: uykular.append(s2))
    finally:
        ye._istek = eski
    s, rc, _, _ = ye.degerlendir(kayitlar)
    kayit("E8", "SAGLIKLI KOSUMDA EK ISTEK 0: 3 URL -> 3 GET, 0 backoff uykusu "
          "(canli kosum suresi DEGISMEDI)",
          s == "ACIK" and rc == 0 and sayac["n"] == len(yollar) and uykular == [],
          "istek=%d/%d uyku=%s" % (sayac["n"], len(yollar), uykular))


# -------------------------------------------------------------- E7) KABLOLAMA
def _cagrilar(iak, suzgec, metin, yollar):
    """(job_id, yol, argumanlar, sebepler) — GERCEK ayristirici + ortak icra suzgeci."""
    cikti = []
    for job_id, _no, _ad, adim_sebep, satir, pipefail in iak.icra_satirlari(metin):
        for yol in yollar:
            hukum, _sebep, argumanlar = suzgec.anlamli_cagri(satir, yol)
            if hukum in (suzgec.EVET, suzgec.OLCULEMEDI):
                sebepler = list(adim_sebep) + iak.satir_sebepleri(satir, yol, pipefail)
                cikti.append((job_id, yol, list(argumanlar or []), sebepler))
    return cikti


def e7_kablolama(ye, iak, suzgec, cron):
    # --- ALARM KOLU: var, cron'lu, YAYINI DURDURAMAZ, canli kolu KOSAR ---------
    if not os.path.exists(ALARM):
        kayit("E7", "alarm is akisi VAR (%s)" % ALARM_ADI, False, "dosya YOK")
        return
    with open(ALARM, encoding="utf-8") as f:
        alarm_metin = f.read()
    govde, hata = iak.ayristir(alarm_metin)
    if govde is None:
        kayit("E7", "alarm is akisi ayristirilabiliyor", False, str(hata)[:80])
        return
    kayit("E7", "alarm is akisi VAR ve ayristirilabiliyor (%s)" % ALARM_ADI, True)

    tetikler = set(iak._tetik_adlari(govde))
    kayit("E7", "🔴 YAYINI DURDURAMAZ: push/pull_request/workflow_call tetikleyicisi YOK",
          bool(tetikler) and not ({"push", "pull_request", "workflow_call"} & tetikler),
          "tetikler=%s" % sorted(tetikler))
    kayit("E7", "cron ile kosuyor (seyrek alarm kolu)", "schedule" in tetikler,
          "tetikler=%s" % sorted(tetikler))
    grup = ((govde.get("concurrency") or {}) if isinstance(govde.get("concurrency"),
                                                           dict) else {}).get("group")
    kayit("E7", "AYRI concurrency grubu (yayin kuyrugunu bekletmez)",
          bool(grup) and grup != "pages", "group=%r" % grup)

    # Cron BICIMI: yogun dakika tuzagi — olcu TEK KAYNAKTAN (cron-nabiz-kapisi).
    try:
        ifadeler = [c for d, c in cron.cron_ifadeleri(os.path.dirname(ALARM))
                    if d == ALARM_ADI]
        dakikalar = cron.dakika_kumesi(ifadeler[0]) if ifadeler else None
        yogun = bool(dakikalar) and bool(dakikalar & cron.YOGUN_DAKIKALAR)
        kayit("E7", "cron dakika alani ACIK LISTE ve YOGUN dakikada DEGIL "
              "(*/n tetiklemesi dusuyor — olculdu)",
              bool(ifadeler) and dakikalar is not None and not yogun,
              "cron=%s dakika=%s" % (ifadeler[:1], sorted(dakikalar or [])))
    except Exception as e:                                 # noqa: BLE001
        kayit("E7", "cron bicimi olculdu (tek kaynak: cron-nabiz-kapisi)", False,
              "%s: %s" % (type(e).__name__, e))

    alarm_cagri = _cagrilar(iak, suzgec, alarm_metin, [NOBETCI_YOL])
    canli = [c for c in alarm_cagri
             if "--kendini-test" not in c[2] and "--liste" not in c[2]]
    kayit("E7", "alarm kolu nobetcinin CANLI (bayraksiz) kolunu FIILEN kosuyor",
          bool(canli), "cagrilar=%s" % [(c[0], c[2]) for c in alarm_cagri])
    etkisiz = [(c[0], c[3]) for c in canli if c[3]]
    kayit("E7", "alarm cagrisi ETKISIZLESTIRILMEMIS (`|| true` / arka plan / boru YOK)",
          not etkisiz, "sebepler=%s" % (etkisiz or "-"))
    # 🔴 METIN TAKLIDI YOK ([[mimar-kapi-parser-taklidi]]): `continue-on-error` YORUMDA
    # gecebilir (bu dosyada geciyor) — hukum GERCEK ayristiricinin verdigi govdeden,
    # job ve ADIM duzeyinde verilir.
    coe = []
    for job_id, job in (govde.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        if iak._dogru_mu(job.get("continue-on-error")):
            coe.append("job:%s" % job_id)
        for i, adim in enumerate(job.get("steps") or [], 1):
            if isinstance(adim, dict) and iak._dogru_mu(adim.get("continue-on-error")):
                coe.append("%s adim %d" % (job_id, i))
    kayit("E7", "alarm is akisinda `continue-on-error` YOK (beyansiz fail-open) — "
          "hukum AYRISTIRICIDAN, yorum metninden DEGIL", not coe, "%s" % (coe or "-"))

    # --- DEPLOY.YML: kabul testi KOSAR (serit B) · CANLI kol KOSMAZ ------------
    with open(DEPLOY, encoding="utf-8") as f:
        deploy_metin = f.read()
    d_govde, d_hata = iak.ayristir(deploy_metin)
    if d_govde is None:
        kayit("E7", "deploy.yml ayristirilabiliyor", False, str(d_hata)[:80])
        return
    serit_b, tani = iak._serit_b_joblar(d_govde)
    if serit_b is None:
        kayit("E7", "serit B joblari olculebildi", False, str(tani)[:80])
        return
    d_cagri = _cagrilar(iak, suzgec, deploy_metin, [NOBETCI_YOL, BU_TEST_YOL])
    d_canli = [c for c in d_cagri if c[1] == NOBETCI_YOL
               and "--kendini-test" not in c[2] and "--liste" not in c[2]]
    kayit("E7", "🔴 BAGIMSIZLIK: nobetcinin CANLI kolu deploy.yml'de KOSMUYOR "
          "(ag'a bagimli kapi TUM EKIBIN yayinini durdururdu)",
          not d_canli, "ihlal=%s" % ([(c[0], c[2]) for c in d_canli] or "-"))
    # 🔴 5 Agu 2026 SERIT AYRIMI: bu kabul testi (bir SERIT B adimi) deploy.yml'den
    # nobet.yml'e TASINDI — bloklamayan joblarin kirmizisi yayin kosumunun rengini
    # boyamasin diye ([[hukum-yanlis-birimde]]). IDDIA DEGISMEDI, ARANAN DOSYA degisti:
    # "kabul testi CI'da FIILEN kosuyor + yayini BLOKLAMAYAN seritte + beyani VAR".
    # Nobet dosyasi okunamazsa fail-closed KIRMIZI.
    try:
        with open(NOBET, encoding="utf-8") as f:
            nobet_metin = f.read()
    except OSError as e:
        kayit("E7", "nobet.yml okunabildi (serit B is akisi)", False, str(e)[:80])
        return
    n_govde, n_hata = iak.ayristir(nobet_metin)
    if n_govde is None:
        kayit("E7", "nobet.yml ayristirilabiliyor", False, str(n_hata)[:80])
        return
    n_serit_b, n_tani = iak._serit_b_joblar(n_govde, "nobet.yml")
    if n_serit_b is None:
        kayit("E7", "nobet.yml serit B joblari olculebildi", False, str(n_tani)[:80])
        return
    n_cagri = _cagrilar(iak, suzgec, nobet_metin, [NOBETCI_YOL, BU_TEST_YOL])
    kendi = [c for c in n_cagri if c[1] == BU_TEST_YOL]
    kayit("E7", "bu kabul testi nobet.yml'de FIILEN kosuyor (olu nobetci degil)",
          bool(kendi), "job(lar)=%s" % (sorted({c[0] for c in kendi}) or "YOK"))
    bloklayan = sorted({c[0] for c in kendi if c[0] not in n_serit_b})
    kayit("E7", "cagri YAYINI BLOKLAMAYAN seritte (serit B)",
          bool(kendi) and not bloklayan, "bloklayan job=%s" % (bloklayan or "-"))
    etkisiz2 = [(c[0], c[3]) for c in kendi if c[3]]
    kayit("E7", "nobet.yml cagrisi ETKISIZLESTIRILMEMIS",
          not etkisiz2, "sebepler=%s" % (etkisiz2 or "-"))
    beyan = getattr(iak, "SERIT_B", {})
    anahtar = ("nobet.yml", "serit-b", BU_TEST_YOL)
    kayit("E7", "serit B beyani is-akisi-kapisi::SERIT_B tablosunda VAR ve GEREKCELI",
          bool((beyan.get(anahtar) or "").strip()),
          (beyan.get(anahtar) or "BEYAN YOK")[:60])


# ---------------------------------------------------------------- kosum
IDDIALAR = (("E1", "KUME — kaynaklardan turer, taban altinda OLCULEMEDI"),
            ("E2", "YONTEM — GET; HEAD yetmez"),
            ("E3", "HUKUM — 200 disi KAPALI, hepsi 200 ACIK"),
            ("E4", "YONLENDIRME — zincir/dongu"),
            ("E5", "FAIL-CLOSED — ag/zaman asimi OLCULEMEDI"),
            ("E6", "MALIYET — hiz siniri, ornekleme yok, kapsam beyani"),
            ("E7", "KABLOLAMA — cron alarm kolu + serit B"),
            ("E8", "TEKRAR — gecici 5xx kalici kapalidan AYRILIR (4xx tekrarsiz)"))


def main():
    print("YAYIN ERISIM NOBETCISI — KABUL TESTI")
    print("-" * 78)
    try:
        ye = _modul("yayin_erisim_nobeti", os.path.join(TOOLS, "yayin-erisim-nobeti.py"))
        iak = _modul("pruvo_is_akisi_kapisi", os.path.join(TOOLS, "is-akisi-kapisi.py"))
        suzgec = _modul("pruvo_icra_suzgeci", os.path.join(TOOLS, "icra-suzgeci.py"))
        cron = _modul("pruvo_cron_nabiz", os.path.join(TOOLS, "cron-nabiz-kapisi.py"))
    except Exception as e:                                 # noqa: BLE001
        print("  ✘ FAIL-CLOSED: gerekli modul yuklenemedi — %s: %s"
              % (type(e).__name__, e))
        print("IDDIA SAYISI: 0")
        print("KIRMIZI IDDIA: %s" % ",".join(k for k, _ in IDDIALAR))
        return 1

    with ye.FiksturSunucu() as sunucu:
        kosumlar = (("E1", lambda: e1_kume(ye)),
                    ("E2", lambda: e2_yontem(ye, sunucu)),
                    ("E3", lambda: e3_hukum(ye, sunucu)),
                    ("E4", lambda: e4_yonlendirme(ye, sunucu)),
                    ("E5", lambda: e5_fail_closed(ye, sunucu)),
                    ("E6", lambda: e6_maliyet(ye, sunucu)),
                    ("E7", lambda: e7_kablolama(ye, iak, suzgec, cron)),
                    ("E8", lambda: e8_gecici_5xx(ye, sunucu)))
        for kod, fn in kosumlar:
            try:
                fn()
            except Exception as e:                         # noqa: BLE001
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
