#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VARLIK KAPISI — tekrar eden CSS/JS'in icerik-adresli same-origin dosyaya tasinmasi.

NEDEN VAR (olculdu, 2 Agu 2026): urun sayfasinin ~%86'si her sayfada BIREBIR ayni
bayttı; gomulu CSS+JS sayfanin ucte ikisiydi. 16.874 urunde toplam yayin ~1,03 GB ve
GitHub Pages siniri ~1 GB. Bloklar /varlik/<ad>-<sha256-ilk10>.<uz> dosyalarina tasindi.
Bu tasimanin IKI hata sinifi SESSIZDIR ve ikisi de bu depoda YASANDI:
  (1) ONBELLEK: ayni adin ustune yazmak -> tarayici BAYAT CSS/JS servis eder
      ([[r2-sessiz-uzerine-yazma]], [[gorsel-anahtar-cakismasi]]). Ad icerikten TUREMELI.
  (2) IKIZ TANIM: satir-ici "kritik cekirdek" ile harici dosyanin AYRI metinler olmasi
      -> sessizce ayrisirlar ([[ikiz-tanim-sessiz-ayrisma]]). Cekirdek kaynagin DILIMI
      olmali, ikinci kopya DEGIL.
Ucuncu sinif: kirik referans (sayfadaki ad ile dosyanin adi ayrisirsa sayfa CIPLAK kalir)
ve sessiz kayip (harici dosyaya blogun bir kismi yazilmaz).

KABUL EKSENLERI (spec 4. bolum):
  1  ESKI uretici ile YENI uretici ciktisi, CSS/JS bloklari DISINDA bayt-esit.
  1b Urune ozel VERI (URUN / URUN_SEMA / URUN_KONFIGUR) eski ile bayt-esit.
  2  Harici dosyaya cikan CSS + JS icerigi eski gomulu icerikle esit (kayip/eklenti yok).
  3  Sayfa sayisi degismedi; her sayfa hala uretiliyor (ornek uzerinde sayiyla).
  4  Yeni ortalama sayfa bayti OLCULDU ve eskisinden DUSUK.
  5  Yeni toplam yayin tahmini (ortalama x katalog + varlik dosyalari) OLCULDU ve dusuk.
  6  Icerik degismezse uretilen dosya ADI AYNI kalir (gereksiz cache-miss yok).
  7  Icerik BIR BAYT degisirse dosya adi DEGISIR (bayat varlik servis edilemez).
  8  Sayfadaki referans ile diskteki dosyanin adi BIREBIR ayni + ad dosyanin
     BAYTLARINDAN yeniden turetilebiliyor (kirik referans = ciplak sayfa).
  9  IKIZ YOK: satir-ici cekirdek + harici kalan = KAYNAGIN TA KENDISI; cekirdek
     bolgesini bozan bir mutant satir-ici ciktiyi da DEGISTIRIR.
 10  FAIL-CLOSED: varlik uretilemezse (bos govde / sinir isareti yok / yazilamayan
     dizin) build DURUR; sessizce ciplak sayfa URETMEZ.

ESKI URETICI NEREDEN GELIR: git gecmisinde `varlik_adres`i ICERMEYEN en son
tools/build.py. Boylece kiyas kendi kendini dogrulamaz ([[anahat-referans-tautolojisi]]).
Depo SIG (shallow) ise eksen 1/1b/2 OLCULEMEDI olur ve kapi rc 2 ile DURDURUR — yesile
donmez (deploy.yml `fetch-depth: 0` zorunlu on-kosuldur).

Kullanim:
    python3 tools/varlik-test.py
    python3 tools/varlik-test.py --ornek 12
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build                                                             # noqa: E402
import yorum_soy                                                         # noqa: E402

HATALAR = []
BILGI = []
OLCULEMEDI = []


def bekle(kosul, mesaj):
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


# --------------------------------------------------------------------- yardimcilar
_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
_SCRIPT_RE = re.compile(r"<script([^>]*)>(.*?)</script>", re.S)
_SCRIPT_SRC_RE = re.compile(r"<script[^>]*\ssrc=\"([^\"]+)\"[^>]*>\s*</script>")
_CSS_LINK_RE = re.compile(r"<link rel=\"stylesheet\" href=\"([^\"]+)\">")
_URUN_VERI_RE = re.compile(r"^var (URUN|URUN_SEMA|URUN_KONFIGUR|URUN_KART_SECIM) = (.*);$", re.M)


def _js_mi(oznitelikler):
    return yorum_soy._script_turu_js_mi(oznitelikler)


# --------------------------------------------------------- eksen 2: BILEREK degisen satirlar
# Eksen 2'nin IDDIASI: "varliga tasima sirasinda icerik KAYBOLMADI/EKLENMEDI".
# Kiyas nesnesi git gecmisindeki ESKI uretici oldugu icin, o commit'ten BU YANA yapilan
# HER MESRU icerik degisikligi de bu eksende kayip/eklenti gibi gorunur. Ikisi ayni sey
# DEGILDIR ve karistirilirsa eksen 2 "sayfa JS'i bir daha asla degismesin" kuralina doner.
# Bu yuzden BILEREK degisen satirlar BURADA, GEREKCESIYLE ve DAR desenle listelenir.
# 🔴 DAR TUTULACAK: her giris tek bir olayi anlatir; genel desen (ornegin butun `de(...)`
# cagrilari) YAZILMAZ — o, gercek bir icerik kaybini da maskelerdi.
BILEREK_DEGISEN = (
    # KART_SECIM: sabit deger yerine sayfadaki veriden okunur oldu.
    ("var KART_SECIM =", "kart secim verisi sabitten sayfa verisine tasindi"),
    ("var URUN_KART_SECIM =", "kart secim verisi sabitten sayfa verisine tasindi"),
    # 2026-08-03: uretilemez secenekte basilan MUSTERI METNI duzeltildi. Eski metin
    # "siparis verebilirsiniz, uretim etkilenmez" diyordu; o bolge OLCULDU ve uretim
    # ucunda karsiligi YOK (satis kapisi da ayni gun kapatildi). Bu bir ICERIK
    # duzeltmesidir, varliga tasima kaybi DEGIL. Iki cagri yeri de ayni cumleyi tasir.
    ("Bu seçenekle 3D önizleme şimdilik sunulamıyor",
     "uretilemez secenek metni duzeltildi — ESKI cumle (kiyas commit'inde)"),
    ("Bu seçenek üretim hattımızda henüz karşılanmıyor",
     "uretilemez secenek metni duzeltildi — YENI cumle"),
)

# TAM SATIR eslesmeli girisler. NEDEN AYRI: yukaridaki liste ALT DIZE arar; ayirt edici
# alt dizesi OLMAYAN satirlar (ornegin yalnizca kapanis suslu parantezden olusan `}}}`)
# alt dize olarak yazilirsa o dizeyi ICEREN her satiri — yani gercek bir icerik kaybini
# da — maskelerdi. Tam satir eslesmesi mumkun olan EN DAR bicimdir.
# 2026-08-03 (45f30fd7): onizleme kisit YARGISI satir-ici dongudan cikarilip
# secenekler.js `onizlemeKisitIhlali()` TEK KAYNAGINA tasindi (ayni fonksiyonu Worker
# sema kapisi da cagirir). Satir-ici dongunun satirlari sayfa JS'inden GERCEKTEN cikti;
# bu bir varliga-tasima kaybi DEGIL, bilerek yapilan bir tek-kaynak refaktoru.
# Kisit yargisinin kendi iddiasi ayri kapida olculur: tools/onizleme-kisit-kosul-test.py.
BILEREK_DEGISEN_TAM = (
    # ESKI: satir-ici kisit dongusu (kiyas commit'inde)
    ("if(kis){ for(var ad in kis){ if(Object.prototype.hasOwnProperty.call(kis,ad)){",
     "kisit dongusu tek kaynaga tasindi — ESKI dongu basi"),
    ("var v=s.parametreler[ad];", "kisit dongusu tek kaynaga tasindi — ESKI deger okuma"),
    ("if(v!==undefined && kis[ad].indexOf(v)<0){",
     "kisit dongusu tek kaynaga tasindi — ESKI ihlal kosulu"),
    ("}}}", "kisit dongusu tek kaynaga tasindi — ESKI dongu kapanisi"),
    # YENI: tek kaynaktaki fonksiyona cagri
    ("var kisitFn=window.PRUVO_SECENEK&&PRUVO_SECENEK.onizlemeKisitIhlali;",
     "kisit dongusu tek kaynaga tasindi — YENI fonksiyon referansi (yoksa fail-closed)"),
    ("if(kis&&(!kisitFn||kisitFn(kis,s.parametreler))){",
     "kisit dongusu tek kaynaga tasindi — YENI ihlal kosulu"),
)

_BILEREK_TAM = frozenset(d for d, _g in BILEREK_DEGISEN_TAM)


def _bilerek_degisti(satir):
    s = satir.strip()
    if s in _BILEREK_TAM:
        return True
    for desen, _gerekce in BILEREK_DEGISEN:
        if desen in s:
            return True
    return False


def iskelet(html):
    """Sayfanin CSS/JS YUZEYI CIKARILMIS hali: metin, meta, JSON-LD, gorsel URL'leri,
    kirilim... yani tasima isinin DOKUNMAMASI gereken her sey. JSON-LD script'i JS
    DEGILDIR -> KALIR (yapisal veri bu eksende olculur).
    CSS/JS yuzeyi tamamen SILINIR (yerine isaret konmaz): blok sayisi bilerek degisti
    (bir <script> gomulu iken iki referansa bolundu) — bu eksenin iddiasi blok SAYISI
    degil, bloklar DISINDAKI baytlarin ayni kalmasidir. Geriye kalan bos satir yiginlari
    tek satira indirilir; metin/oznitelik baytlari AYNEN kiyaslanir."""
    s = _STYLE_RE.sub("", html)

    def _s(m):
        return "" if _js_mi(m.group(1)) else m.group(0)
    s = _SCRIPT_RE.sub(_s, s)
    s = _SCRIPT_SRC_RE.sub("", s)
    s = _CSS_LINK_RE.sub("", s)
    return re.sub(r"\n[ \t]*(?:\n[ \t]*)+", "\n", s)


def js_govdeleri(html):
    return [m.group(2) for m in _SCRIPT_RE.finditer(html) if _js_mi(m.group(1))]


def css_govdeleri(html):
    return _STYLE_RE.findall(html)


def satir_cantasi(metin):
    """Sirali olmayan 'kayip/eklenti var mi' olcusu: bosluk-normalize edilmis, bos
    olmayan satirlarin cok-kumesi. Blok sayfadan cikip dosyaya tasinirken SIRA degisir
    ama HICBIR SATIR kaybolmaz/eklenmez — olculen iddia budur."""
    from collections import Counter
    return Counter(p for p in (s.strip() for s in metin.split("\n")) if p)


def urun_verisi(html):
    return dict((m.group(1), m.group(2)) for m in _URUN_VERI_RE.finditer(html))


# --------------------------------------------------------------------- eski uretici
def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def eski_ref():
    """`varlik_adres`i ICERMEYEN en son tools/build.py commit'i (tautoloji karsiti)."""
    log = git("log", "--format=%H", "-n", "500", "--", "tools/build.py")
    if not log:
        return None
    for sha in log.split():
        icerik = git("show", sha + ":tools/build.py")
        if icerik is None:
            continue
        if "varlik_adres" not in icerik:
            return sha
    return None


def eski_kok_kur(tmp, ref):
    """`ref`teki build.py'yi tmp'ye acar; diger girdileri guncel ROOT'a symlink.

    Kiyas yalniz varlik tasimasindan onceki URETICIYI sabitler. Tum `tools/` agacini
    eski ref'ten almak, sonradan genisleyen taksonomi gibi build.py disi kurallari da
    geri sarar ve varlik tasimasiyla ilgisiz sahte bayt farklari uretir.
    """
    p = subprocess.run(["git", "-C", ROOT, "archive", ref, "tools/build.py"],
                       capture_output=True)
    if p.returncode != 0:
        return False
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as t:
        t.extractall(tmp)
    tmp_tools = os.path.join(tmp, "tools")
    for ad in os.listdir(TOOLS):
        if ad == "build.py":
            continue
        os.symlink(os.path.join(TOOLS, ad), os.path.join(tmp_tools, ad))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(tmp, ad))
    return os.path.isfile(os.path.join(tmp, "tools", "build.py"))


_SURUCU = u'''import json, os, sys
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KOK, "tools"))
import build
idler = json.load(open(sys.argv[1], encoding="utf-8"))
with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
    urunler = json.load(f)
harita = dict((p["id"], p) for p in urunler)
cikti = dict((i, build.render_product(harita[i], urunler, None)) for i in idler)
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(cikti, f)
'''


def eski_render(tmp, idler):
    """ESKI build.py'yi AYRI SURECTE kosturur (modul adlari carpismasin)."""
    surucu = os.path.join(tmp, "_surucu.py")
    with io.open(surucu, "w", encoding="utf-8") as f:
        f.write(_SURUCU)
    gid = os.path.join(tmp, "_idler.json")
    gout = os.path.join(tmp, "_cikti.json")
    with io.open(gid, "w", encoding="utf-8") as f:
        json.dump(idler, f)
    p = subprocess.run([sys.executable, surucu, gid, gout], capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stderr or "")[-1200:]
    with io.open(gout, encoding="utf-8") as f:
        return json.load(f), ""


# --------------------------------------------------------------------- ornek
EKSENLER = (
    ("parametrik", lambda p: bool(p.get("parametrik"))),
    ("semali", lambda p: bool(build.konf_sema(p.get("id")))),
    ("konfigurlu", lambda p: bool(p.get("konfigur"))),
    ("fiziksel", lambda p: bool(p.get("tur"))),
    ("altkategorili", lambda p: bool(p.get("altkategori"))),
    ("lisansli", lambda p: bool(p.get("lisans"))),
    ("gorselsiz", lambda p: not p.get("gorseller")),
    ("markasiz", lambda p: not p.get("marka")),
    ("sade", lambda p: True),
)


def ornek_sec(urunler, hedef):
    secim, gorulen = [], set()
    for ad, kosul in EKSENLER:
        for p in urunler:
            if p["id"] in gorulen:
                continue
            try:
                uygun = kosul(p)
            except Exception:
                uygun = False
            if uygun:
                secim.append((ad, p))
                gorulen.add(p["id"])
                break
    adim = max(1, len(urunler) // max(1, hedef))
    i = 0
    while len(secim) < hedef and i < len(urunler):
        p = urunler[i]
        if p["id"] not in gorulen:
            secim.append(("dolgu", p))
            gorulen.add(p["id"])
        i += adim
    return secim[:hedef]


# --------------------------------------------------------------------- kosum
def main():
    hedef = 12
    if "--ornek" in sys.argv:
        hedef = int(sys.argv[sys.argv.index("--ornek") + 1])

    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    secim = ornek_sec(urunler, hedef)
    idler = [p["id"] for _, p in secim]
    BILGI.append("ornek: %d urun (%s)" % (len(secim), ", ".join(a for a, _ in secim)))

    # varlik dizinini sifirdan uret (bayat dosya olcume karismasin)
    if os.path.isdir(build.VARLIK_DIR):
        shutil.rmtree(build.VARLIK_DIR)
    build._VARLIK_ONBELLEK.clear()

    yeni = {}
    for _, p in secim:
        yeni[p["id"]] = build.render_product(p, urunler, None)

    # ---------------------------------------------------------------- 3
    bekle(len(yeni) == len(secim), "3 sayfa sayisi degisti: %d/%d" % (len(yeni), len(secim)))
    for pid, h in yeni.items():
        bekle(len(h) > 2000 and "<h1>" in h and '"@type":"Product"' in h,
              "3 %s: sayfa uretilmedi/eksik (h1 + Product JSON-LD yok)" % pid)

    # ---------------------------------------------------------------- 8
    for pid, h in yeni.items():
        refler = [u for u in (_CSS_LINK_RE.findall(h) + _SCRIPT_SRC_RE.findall(h))
                  if u.startswith(build.VARLIK_URL_ONEK)]
        if not bekle(len(refler) >= 2,
                     "8 %s: /varlik/ referansi < 2 (css + js beklenir) -> %r" % (pid, refler)):
            continue
        for u in refler:
            ad = u[len(build.VARLIK_URL_ONEK):]
            yol = os.path.join(build.VARLIK_DIR, ad)
            if not bekle(os.path.isfile(yol), "8 %s: referans edilen varlik DISKTE YOK: %s"
                         % (pid, ad)):
                continue
            with io.open(yol, encoding="utf-8") as f:
                govde = f.read()
            beklenen = "%s-%s%s" % (ad.rsplit("-", 1)[0], build.varlik_hash(govde),
                                    os.path.splitext(ad)[1])
            bekle(beklenen == ad,
                  "8 %s: dosya adi kendi BAYTLARINDAN turemiyor (%s != %s)"
                  % (pid, ad, beklenen))
        bekle("<style>" in h, "8 %s: satir-ici kritik cekirdek <style> yok" % pid)

    # ---------------------------------------------------------------- 6 + 7
    ornek_css = "a{color:red}\n"
    u1 = build.varlik_adres("test", "css", ornek_css)
    u2 = build.varlik_adres("test", "css", ornek_css)
    bekle(u1 == u2, "6 ayni icerik FARKLI ad uretti (%s != %s) — gereksiz cache-miss" % (u1, u2))
    u3 = build.varlik_adres("test", "css", ornek_css + "b{color:blue}\n")
    bekle(u1 != u3, "7 icerik degisti ama ad AYNI kaldi (%s) — BAYAT varlik servis edilir" % u1)
    # eksen 7'nin GERCEK yuzeydeki hali: HARICI dosyaya giden CSS'in tek karakteri
    # degisince sayfadaki CSS adresi degismeli. Capa bilerek KRITIK CEKIRDEGIN DISINDA
    # (kalan bolgede) secilir — cekirdekteki capa harici dosyayi zaten degistirmezdi.
    asil_css = build.PAGE_CSS
    try:
        css_ref_once = _CSS_LINK_RE.findall(next(iter(yeni.values())))
        build.PAGE_CSS = asil_css.replace(".help-cta-btn:hover{background:#1ebe5a}",
                                          ".help-cta-btn:hover{background:#1ebe5b}")
        bekle(build.PAGE_CSS != asil_css, "7 mutasyon capasi PAGE_CSS'te bulunamadi (help-cta-btn)")
        h2 = build.render_product(secim[0][1], urunler, None)
        css_ref_sonra = _CSS_LINK_RE.findall(h2)
        bekle(css_ref_once != css_ref_sonra,
              "7 PAGE_CSS bir bayt degisti ama sayfadaki CSS adresi AYNI (%r)" % css_ref_once)
    finally:
        build.PAGE_CSS = asil_css

    # ---------------------------------------------------------------- 9 (ikiz yok)
    cekirdek, kalan = build.css_bol(build.PAGE_CSS)
    bekle(cekirdek + build.KRITIK_CSS_SINIRI + kalan == build.PAGE_CSS,
          "9 cekirdek + sinir + kalan KAYNAGA esit degil — satir-ici blok kaynagin DILIMI degil")
    try:
        capa = "--navy:#12294d"
        bekle(capa in cekirdek, "9 mutasyon capasi kritik cekirdekte yok (%s)" % capa)
        build.PAGE_CSS = asil_css.replace(capa, "--navy:#12294e")
        h3 = build.render_product(secim[0][1], urunler, None)
        eski_ici = css_govdeleri(yeni[secim[0][1]["id"]])[0]
        yeni_ici = css_govdeleri(h3)[0]
        bekle(eski_ici != yeni_ici,
              "9 IKIZ TANIM: kritik cekirdek KAYNAKTAN turemiyor — kaynagi bozan mutant "
              "satir-ici ciktiyi DEGISTIRMEDI")
    finally:
        build.PAGE_CSS = asil_css

    # ---------------------------------------------------------------- 10 (fail-closed)
    def patlar(fn, ad):
        try:
            fn()
        except Exception:
            return True
        HATALAR.append("10 FAIL-OPEN: %s hata vermedi (sessizce ciplak sayfa uretilirdi)" % ad)
        return False

    patlar(lambda: build.varlik_adres("test", "css", "   \n  "), "bos govde")
    patlar(lambda: build.varlik_adres("test", "xml", "x"), "bilinmeyen uzanti")
    patlar(lambda: build.css_bol("a{color:red}"), "sinir isareti olmayan CSS")
    try:
        build.PAGE_CSS = asil_css.replace(build.KRITIK_CSS_SINIRI, "")
        patlar(lambda: build.render_product(secim[0][1], urunler, None),
               "sinir isareti silinmis PAGE_CSS ile render_product")
    finally:
        build.PAGE_CSS = asil_css
    eski_dir = build.VARLIK_DIR
    try:
        build.VARLIK_DIR = os.path.join(ROOT, "urunler.json", "olmaz")   # dosya altinda dizin
        patlar(lambda: build.varlik_adres("test", "css", "a{color:red}\n"), "yazilamayan dizin")
    finally:
        build.VARLIK_DIR = eski_dir

    # varlik dizinini olcum icin temizle-yeniden uret (test artifaktlari cikmasin)
    shutil.rmtree(build.VARLIK_DIR, ignore_errors=True)
    build._VARLIK_ONBELLEK.clear()
    yeni = {}
    for _, p in secim:
        yeni[p["id"]] = build.render_product(p, urunler, None)

    # ---------------------------------------------------------------- 1 / 1b / 2 / 4 / 5
    ref = eski_ref()
    if ref is None:
        OLCULEMEDI.append("1/1b/2 ESKI uretici bulunamadi (SIG depo ya da yeniden yazilmis "
                          "gecmis) — esdegerlik ve ortalama-dusus eksenleri OLCULEMEDI")
    else:
        tmp = tempfile.mkdtemp(prefix="varlik-eski-")
        try:
            if not eski_kok_kur(tmp, ref):
                OLCULEMEDI.append("1/1b/2 eski agac kurulamadi (%s)" % ref[:10])
            else:
                eski, hata = eski_render(tmp, idler)
                if eski is None:
                    OLCULEMEDI.append("1/1b/2 eski uretici kosmadi: %s" % hata)
                else:
                    olc(eski, yeni, secim, urunler, ref)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    rapor()


def olc(eski, yeni, secim, urunler, ref):
    # ------------------------------------------------------------------ 1
    for pid in yeni:
        bekle(iskelet(eski[pid]) == iskelet(yeni[pid]),
              "1 %s: CSS/JS DISINDA bayt farki var (metin/meta/JSON-LD/kirilim degismis)" % pid)
        bekle(urun_verisi(eski[pid]).get("URUN") == urun_verisi(yeni[pid]).get("URUN"),
              "1b %s: URUN verisi ayristi" % pid)
        for ad in ("URUN_SEMA", "URUN_KONFIGUR"):
            bekle(urun_verisi(eski[pid]).get(ad) == urun_verisi(yeni[pid]).get(ad),
                  "1b %s: %s verisi ayristi" % (pid, ad))

    # ------------------------------------------------------------------ 2 (CSS: BAYT-ESIT)
    pid0 = secim[0][1]["id"]
    e_css = css_govdeleri(eski[pid0])
    y_css = css_govdeleri(yeni[pid0])
    y_ref = [u for u in _CSS_LINK_RE.findall(yeni[pid0]) if u.startswith(build.VARLIK_URL_ONEK)]
    harici = ""
    for u in y_ref:
        with io.open(os.path.join(build.VARLIK_DIR, u[len(build.VARLIK_URL_ONEK):]),
                     encoding="utf-8") as f:
            harici += f.read()
    bekle(e_css and y_css, "2 CSS govdesi bulunamadi (olcum bosa dustu)")
    if e_css and y_css:
        bekle(y_css[0] + harici == e_css[0],
              "2 CSS KAYIP/EKLENTI: satir-ici cekirdek + harici dosya, eski gomulu CSS'e "
              "BAYT-ESIT degil (%d + %d != %d)"
              % (len(y_css[0]), len(harici), len(e_css[0])))
        # sayfaya ozel ek <style> bloklari da aynen durmali
        bekle(e_css[1:] == y_css[1:], "2 sayfaya ozel satir-ici <style> bloklari ayristi")

    # ------------------------------------------------------------------ 2 (JS: kayip/eklenti yok)
    for pid in yeni:
        e_js = "\n".join(js_govdeleri(eski[pid]))
        y_js = "\n".join(js_govdeleri(yeni[pid]))
        for u in _SCRIPT_SRC_RE.findall(yeni[pid]):
            if not u.startswith(build.VARLIK_URL_ONEK):
                continue
            with io.open(os.path.join(build.VARLIK_DIR, u[len(build.VARLIK_URL_ONEK):]),
                         encoding="utf-8") as f:
                y_js += "\n" + f.read()
        ec, yc = satir_cantasi(e_js), satir_cantasi(y_js)
        kayip = [k for k in sorted((ec - yc).elements()) if not _bilerek_degisti(k)]
        eklenti = [k for k in sorted((yc - ec).elements()) if not _bilerek_degisti(k)]
        bekle(not kayip, "2 %s: JS KAYIP (%d satir) ilk: %r" % (pid, len(kayip), kayip[:2]))
        bekle(not eklenti, "2 %s: JS EKLENTI (%d satir) ilk: %r" % (pid, len(eklenti), eklenti[:2]))

    # ------------------------------------------------------------------ 4 / 5
    n = float(len(yeni))
    e_ort = sum(len(eski[p].encode("utf-8")) for p in yeni) / n
    y_ort = sum(len(yeni[p].encode("utf-8")) for p in yeni) / n
    vbayt = sum(os.path.getsize(os.path.join(build.VARLIK_DIR, a))
                for a in os.listdir(build.VARLIK_DIR))
    katalog = len(urunler)
    e_gb = e_ort * katalog / 1e9
    y_gb = (y_ort * katalog + vbayt) / 1e9
    bekle(y_ort < e_ort * 0.85,
          "4 ortalama sayfa bayti yeterince dusmedi: %.0f -> %.0f" % (e_ort, y_ort))
    bekle(y_gb < e_gb, "5 toplam yayin tahmini dusmedi: %.3f -> %.3f GB" % (e_gb, y_gb))
    BILGI.append("kiyas referansi: %s" % ref[:10])
    BILGI.append("ORTALAMA sayfa bayti: %.0f -> %.0f (%.1f%% dusus)"
                 % (e_ort, y_ort, 100.0 * (e_ort - y_ort) / e_ort))
    BILGI.append("TOPLAM yayin tahmini (%d urun): %.3f GB -> %.3f GB (varlik %d bayt)"
                 % (katalog, e_gb, y_gb, vbayt))


def rapor():
    for b in BILGI:
        print("  · " + b)
    if OLCULEMEDI:
        for o in OLCULEMEDI:
            print("OLCULEMEDI: " + o)
    if HATALAR:
        print("\nKIRMIZI (%d):" % len(HATALAR))
        for h in HATALAR:
            print("  - " + h)
        sys.exit(1)
    if OLCULEMEDI:
        print("\nOLCULEMEDI -> yesil DEGIL (rc 2)")
        sys.exit(2)
    print("\nOK: varlik kapisi — 10 eksen yesil.")


if __name__ == "__main__":
    main()
