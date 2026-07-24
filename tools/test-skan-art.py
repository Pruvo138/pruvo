#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKAN ART KABUL TESTI — IKI KATMANLI (bloklayici cekirdek + uyari katmani).

"Skan Art" (Okan, 23 Tem) = Iskandinav tasarim dilli dekor/heykel alt-serisi. Kategori
davranisi sari seri ("Jeneratör") ile BIREBIR ayni sinif: ana nav'da GIZLI, ana sayfaya
kendi BANNER'iyle girilir, ?kategori= derin linki/arama/urun sayfasi calisir.

🔴 24 Tem — MIMAR KARARI: KAPININ SEKLI DEGISTI (kapsam daraltma DEGIL, YAPI degisikligi).
TESHIS: bes sertlestirme turunda kapi HER TURDA yeni bir yanlis-kirmizi sinifi uretti
(site geneli a{}/*{} kurallari, modern/logical CSS ozellikleri, :has(), jen-banner koku,
banner metninde "sarı" kelimesi, ucuncu bir seri banner'i...). Sebep YAPISAL: CSS/JS
SEMANTIGI hakkinda akil yuruten bir kapinin yanlis-kirmizi yuzeyi hicbir zaman kapanmaz.
Bu kapi deploy ONCESI bloklayici oldugu icin her yanlis-kirmizi = TUM SITE KARARIYOR.
Onledigi zarar (banner kazara sari/gizli — KOZMETIK, goze carpan, tek commit'le geri
alinir) ile bedeli (site kapanmasi) ORANTISIZ.

────────────────────────────────────────────────────────────────────────────────
KATMAN 1 — BLOKLAYICI CEKIRDEK  (exit != 0 uretebilir)
Yalniz TAM-BELIRLI, YAPISAL, CSS-semantigi ICERMEYEN degismezler. Tam liste — bunlar
VE YALNIZ bunlar bloklayicidir:
  B1. "Skan Art" hem index.html GIZLI_KATEGORILER hem tools/build.py NAV_GIZLI icinde
      VAR ve iki kaynakta AYNI SIRA indeksinde.
  B2. "Skan Art" gizli-nav kumesinde — GORUNUR nav cip kaynaginda (CATEGORIES) DEGIL,
      iki kaynakta da.
  B3. "Skan Art" FONKSIYONEL_KATEGORILER icinde — tools/build.py VE secenekler.js.
  B4. GOOGLE_PRODUCT_CATEGORY["Skan Art"] tanimli (merchant feed taksonomisi).
  B5. kurt urununun kategorisi == "Skan Art".
  B6. kategorisi "Skan Art" olan urun sayisi >= 1 (banner bos kategoriye link vermesin).
  B7. kategorisi "Skan Art" olan HER urun `konfigur` alani TASIR.  ⚠️ PARA EMNIYETI:
      shop odeme Worker'i secenekler.js'i BUNDLE'a gommuyor -> canli worker "Skan Art"i
      bilmez; konfigursuz bir Skan Art urununde malzeme/renk katsayisi SESSIZCE duser
      (olculdu: ASA + ozel renk 27.600 yerine 15.000 kurus). Yanlis-kirmizi yuzeyi YOK:
      urun ya alani tasir ya tasimaz. BLOKLAYICI KALIR.
  B8. index.html'de id="skanBanner" olan bir <a> ELEMANI VAR ve href'i DAVRANIS olarak
      "/?kategori=Skan%20Art"e denk (applyUrlParams node'da kosturulur; "+" kodlamasi da
      gecerli sayilir — duz metin karsilastirmasi YOK).
  B9. build.py'nin ANA urun-yazma yolundan gecerek urun/<kurt-id>/index.html DISKTE
      uretiliyor, icinde kompakt kart isareti var ve sitemap.xml'de URL'i geciyor.
  B10. renderGrid DAVRANISI (node + sahte DOM): ana gorunumde skanBanner display === "",
      kategori/arama/marka gorunumunde "none". Toggle dizisinin KAC elemanli oldugu
      OLCULMEZ — ucuncu bir seri banner'i eklenebilmelidir.

KATMAN 2 — UYARI  (exit koduna ASLA dokunmaz, cikti 0 doner)
Bugunku TUM CSS/JS sezgileri buraya indi: sari taramasi (var() cozumu, hex/notasyon,
%23/base64, kaskad), gorunurluk motoru, beyaz liste, metin-kutusu kontrolu, JS kaynak
sozlesmesi, cozulemeyen-secici fail-closed, renderCats cip listesi, filament rozeti,
URL yuzde-kodlamasi, ilgili urunler, sentetik FONKSIYONEL fiksturu, secenekler.js fiyat
davranisi. Bulgular ciktida "UYARI" basligi altinda ACIKCA basilir (CI loglarinda
gorunur) ama exit 0. Uyari katmanindaki HICBIR kod yolu — istisna/traceback dahil —
exit'i bozamaz: her bolum try/except ile sarilidir.
────────────────────────────────────────────────────────────────────────────────

⚠️ PYC BAYATLIGI (24 Tem, olculmus GERCEK KUSUR): test `import build` yaptigi icin
tools/__pycache__ dolu kaliyordu; AYNI UZUNLUKTA bir mutasyon (NAV_GIZLI sirasini
degistirmek) pyc'nin mtime+boyut damgasini degistirmedigi icin YANLIS YESIL veriyordu.
Cozum: sys.dont_write_bytecode + sys.pycache_prefix (bos gecici dizin) +
importlib.invalidate_caches() + build/filament_ortak modullerinin KAYNAKTAN okunup
exec edilmesi (bytecode onbellegi tamamen devre disi). Kum havuzu alt surecine de
PYTHONDONTWRITEBYTECODE/PYTHONPYCACHEPREFIX gecirilir.

Ag YOK, repo dosyasina YAZMAZ (B9 kum havuzu gecici dizinde), build.py'den ONCE kosabilir.
NODE GEREKIR (B8 + B10) — CI'da setup-node kurulu ve node yoksa CEKIRDEK fail-closed
kirmizi yanar. Yerelde node yoksa acik uyariyla atlamak icin: SKAN_ART_NODE_ATLA=1.
Kullanim:  python3 tools/test-skan-art.py     (0 = cekirdek gecti, 1 = cekirdek kirmizi)
"""
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import types
import urllib.parse

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

# ---------------------------------------------------------------- (D1) PYC BAYATLIGI
# Bytecode onbellegini TAMAMEN devre disi birak: yazma kapali + okuma bos bir gecici
# dizine yonlendirilmis + import onbellegi gecersiz. Boylece AYNI UZUNLUKTA bir kaynak
# mutasyonu (mtime saniye granulasyonuna denk gelse bile) asla eski pyc'den okunmaz.
sys.dont_write_bytecode = True
PYC_YONLENDIRME = os.path.join(tempfile.gettempdir(), "pruvo-skan-art-pyc-yok")
sys.pycache_prefix = PYC_YONLENDIRME
importlib.invalidate_caches()

# Alt sureclere (B9 kum havuzu) da ayni politika gecirilir.
ALT_SUREC_ENV = dict(os.environ)
ALT_SUREC_ENV["PYTHONDONTWRITEBYTECODE"] = "1"
ALT_SUREC_ENV["PYTHONPYCACHEPREFIX"] = PYC_YONLENDIRME


def _kaynaktan_yukle(ad, yol):
    """Modulu KAYNAK DOSYADAN okuyup exec et — pyc onbellegi hic devreye girmez."""
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    modul = types.ModuleType(ad)
    modul.__file__ = yol
    modul.__name__ = ad
    sys.modules[ad] = modul
    exec(compile(kaynak, yol, "exec"), modul.__dict__)
    return modul


filament_ortak = _kaynaktan_yukle("filament_ortak", os.path.join(TOOLS, "filament_ortak.py"))
build = _kaynaktan_yukle("build", os.path.join(TOOLS, "build.py"))

KATEGORI = "Skan Art"
PID = "kurt-heykeli-serit-dekoratif-figur"
SKAN_ART_TABAN = 1             # (B6) seri bosalirsa banner bos kategoriye link verir
# Banner ROOT'unun mesru sayilan asgari hesaplanan yuksekligi (YALNIZ UYARI katmaninda).
BANNER_ASGARI_YUKSEKLIK_PX = 40

INDEX = os.path.join(ROOT, "index.html")
SECENEKLER = os.path.join(ROOT, "secenekler.js")
FILAMENTLER = os.path.join(TOOLS, "filamentler.json")
URUNLER = os.path.join(ROOT, "urunler.json")

HATALAR = []       # KATMAN 1 — exit 1 uretir
UYARILAR = []      # KATMAN 2 — exit'e ASLA dokunmaz


def kontrol(kosul, mesaj):
    """KATMAN 1 (bloklayici cekirdek)."""
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)


def uyari(kosul, mesaj):
    """KATMAN 2 — exit koduna DOKUNMAZ."""
    print(("  ✅ " if kosul else "  ⚠️  UYARI: ") + mesaj)
    if not kosul:
        UYARILAR.append(mesaj)


def _kritik_hata(mesaj):
    print("  ❌ " + mesaj)
    HATALAR.append(mesaj)


def _uyari_hata(mesaj):
    print("  ⚠️  UYARI: " + mesaj)
    UYARILAR.append(mesaj)


BILINEN_SINIRLAR = """
BILINEN SINIRLAR — IKI KATMANLI KAPI (durust liste)

  YAPI. Bu dosya IKI katmandir:
    · KATMAN 1 (BLOKLAYICI CEKIRDEK, exit != 0): B1-B10. Yalniz tam-belirli, yapisal,
      CSS/JS semantigi ICERMEYEN degismezler — liste dosyanin basinda, KAPALI bir kume.
    · KATMAN 2 (UYARI, exit 0): tum CSS/JS sezgileri (sari taramasi, gorunurluk motoru,
      beyaz liste, metin kutusu, JS kaynak sozlesmesi, cozulemeyen secici, renderCats,
      filament, URL kodlamasi, ilgili urunler, fiyat davranisi).

  1. ⚠️ UYARI KATMANI DEPLOY'U DURDURMAZ ve KASITLI BIR EDITORU ENGELLEMEZ. Kozmetik
     drift icin bir HATIRLATMADIR: banner'i kazara sariya boyayan/gizleyen bir degisiklik
     CI logunda "UYARI" satiri olarak gorunur, ama site yayina cikar. Zarar kozmetiktir,
     goze carpar ve tek commit'le geri alinir; buna karsilik yanlis-kirmizinin bedeli TUM
     SITE DEPLOY'unun durmasidir. Bu takas BILEREK yapildi (mimar karari, 24 Tem).
  2. UZAK/RASTER ICERIK TARANAMAZ: R2'deki .jpg/.png/.webp piksellerine bakilmaz.
  3. CALISMA ZAMANINDA URETILEN STIL KAPSAM DISI: eval / new Function / dinamik <style>
     enjeksiyonu / harici JS olculmez.
  4. CSS motoru bir TARAYICI DEGIL: kombinator sirasi (> + ~), @layer, @container, @scope,
     devralma tam degerlendirilmez; uzunluklar 800x1280 varsayimiyla kabaca px'e cevrilir.
     Bu belirsizligin TAMAMI artik UYARI katmanindadir — deploy'u etkilemez.
  5. CEKIRDEK DE BIR GUVENLIK SINIRI DEGIL: B1-B10 yapisal degismezleri olcer, niyeti
     degil. Kararli bir editor kategoriyi/banner'i bilerek kaldirirsa cekirdek kirmizi
     yanar — ama bunu ASMAK isteyen bir editor icin sonsuz gerileme kovalanmaz.
  6. CEKIRDEKTE URUN SAYISI TAVANI YOKTUR: yalniz "seri bosalmasin (>= 1)" (B6) ve
     "her Skan Art urunu `konfigur` tasisin" (B7). Kumulatif capa 21. urunde deploy'u
     kalici kirmiziya cekiyordu. Toplu tasimanin onemli kismi yine B7'ye takilir.
  7. B8/B10 NODE GEREKTIRIR. CI'da node yoksa cekirdek FAIL-CLOSED kirmizi yanar;
     yerelde SKAN_ART_NODE_ATLA=1 ile acik uyariyla atlanabilir (o zaman B8/B10 OLCULMEZ).
""".rstrip()


def bitir():
    print("=" * 70)
    if UYARILAR:
        print("UYARI KATMANI: %d bulgu — ⚠️ EXIT KODUNA DOKUNMAZ, deploy DURMAZ" % len(UYARILAR))
        for u in UYARILAR:
            print("  UYARI: " + u)
    else:
        print("UYARI KATMANI: temiz (0 bulgu)")
    print("-" * 70)
    if HATALAR:
        print("BLOKLAYICI CEKIRDEK: %d KIRMIZI ❌" % len(HATALAR))
        for h in HATALAR:
            print("  - " + h)
        print(BILINEN_SINIRLAR)
        sys.exit(1)
    print("BLOKLAYICI CEKIRDEK: GECTI ✅ (B1-B10 saglandi)")
    print(BILINEN_SINIRLAR)
    sys.exit(0)


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def js_liste(metin, desen, etiket, hata=_kritik_hata):
    """JS/Python kaynagindaki tek satirlik dizi literalini JSON olarak ayristir."""
    m = re.search(desen, metin, re.M)
    if not m:
        hata("%s bulunamadi (yapi degisti mi?)" % etiket)
        return None
    try:
        return json.loads("[" + m.group(1) + "]")
    except json.JSONDecodeError as e:
        hata("%s ayristirilamadi: %s" % (etiket, e))
        return None


def js_bildirim(metin, desen, etiket, hata=_kritik_hata):
    """`var X = ...;` bildiriminin TAM kaynak satirini dondur (node harness'ine gomulur)."""
    m = re.search(desen, metin, re.M)
    if not m:
        hata("%s bildirimi bulunamadi (yapi degisti mi?)" % etiket)
        return ""
    return m.group(0)


def js_fonksiyon(metin, ad, hata=_kritik_hata):
    """`function <ad>(...){...}` govdesini SUSLU PARANTEZ SAYARAK ayikla (regex degil)."""
    m = re.search(r"function\s+%s\s*\(" % re.escape(ad), metin)
    if not m:
        hata("function %s bulunamadi (yapi degisti mi?)" % ad)
        return ""
    i = metin.find("{", m.end())
    if i == -1:
        hata("function %s govdesi acilmiyor" % ad)
        return ""
    derinlik, k = 1, i + 1
    while k < len(metin) and derinlik:
        if metin[k] == "{":
            derinlik += 1
        elif metin[k] == "}":
            derinlik -= 1
        k += 1
    if derinlik:
        hata("function %s govdesi kapanmiyor" % ad)
        return ""
    return metin[m.start():k]


# ================================================================== CSS ALTYAPISI
# ⚠️ Bu bolumun TAMAMI yalniz KATMAN 2 (UYARI) tarafindan kullanilir.
def css_bloklari(html_metin):
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html_metin, re.S))


def css_kurallari(css):
    """(secici, bildirimler, medya) uclusu; @media/@supports icleri duz listeye acilir."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)

    def _ayikla(blok, medya):
        out, i = [], 0
        while True:
            j = blok.find("{", i)
            if j == -1:
                return out
            sec = blok[i:j].strip()
            derinlik, k = 1, j + 1
            while k < len(blok) and derinlik:
                if blok[k] == "{":
                    derinlik += 1
                elif blok[k] == "}":
                    derinlik -= 1
                k += 1
            govde = blok[j + 1:k - 1]
            if sec.startswith("@"):
                out.extend(_ayikla(govde, medya + [sec]))
            else:
                out.append((sec, govde, medya))
            i = k

    return _ayikla(css, [])


def _derinlik_bol(metin, ayirici):
    parca, buf, derinlik, tirnak = [], "", 0, ""
    for ch in metin:
        if tirnak:
            buf += ch
            if ch == tirnak:
                tirnak = ""
            continue
        if ch in "\"'":
            tirnak = ch
            buf += ch
            continue
        if ch in "([":
            derinlik += 1
        elif ch in ")]":
            derinlik -= 1
        if ch == ayirici and derinlik <= 0:
            parca.append(buf)
            buf = ""
        else:
            buf += ch
    parca.append(buf)
    return parca


def bildirimleri_ayristir(govde):
    out = []
    for parca in _derinlik_bol(govde, ";"):
        parca = parca.strip()
        if not parca or ":" not in parca:
            continue
        ad, _, deger = parca.partition(":")
        ad = ad.strip().lower()
        deger = deger.strip()
        onemli = False
        if re.search(r"!\s*important\s*$", deger, re.I):
            onemli = True
            deger = re.sub(r"!\s*important\s*$", "", deger, flags=re.I).strip()
        if ad:
            out.append((ad, deger, onemli))
    return out


# ---------------------------------------------------------------- secici motoru
COZULEMEYEN_SECICI = []

DURUM_PCLS = {"hover", "focus", "focus-visible", "focus-within", "active", "visited",
              "link", "any-link", "target", "lang", "dir"}
UYMAZ_PCLS = {"root", "before", "after", "disabled", "checked", "required", "invalid", "valid"}
LISTE_PCLS = {"is", "where", "matches", "any", "-webkit-any", "-moz-any"}
SAHTE_ELEMAN = {"before", "after", "first-line", "first-letter", "marker", "backdrop",
                "selection", "placeholder", "file-selector-button"}


def _bilesikler(sec):
    out, buf, derinlik, tirnak, i = [], "", 0, "", 0
    while i < len(sec):
        ch = sec[i]
        if tirnak:
            buf += ch
            if ch == tirnak:
                tirnak = ""
            i += 1
            continue
        if ch in "\"'":
            tirnak = ch
            buf += ch
            i += 1
            continue
        if ch in "([":
            derinlik += 1
            buf += ch
        elif ch in ")]":
            derinlik -= 1
            buf += ch
        elif derinlik == 0 and (ch.isspace() or ch in ">+~"):
            if buf:
                out.append(buf)
                buf = ""
            while i < len(sec) and (sec[i].isspace() or sec[i] in ">+~"):
                i += 1
            continue
        else:
            buf += ch
        i += 1
    if buf:
        out.append(buf)
    return out


def bilesik_ayristir(bl):
    d = {"etiket": None, "id": None, "sinif": set(), "oz": [], "psel": [], "pcls": []}
    i = 0
    while i < len(bl):
        c = bl[i]
        if c == "*":
            i += 1
        elif c == "#":
            m = re.match(r"#([\w-]+)", bl[i:])
            if not m:
                return None
            d["id"] = m.group(1)
            i += m.end()
        elif c == ".":
            m = re.match(r"\.([\w-]+)", bl[i:])
            if not m:
                return None
            d["sinif"].add(m.group(1))
            i += m.end()
        elif c == "[":
            j = bl.find("]", i)
            if j == -1:
                return None
            d["oz"].append(bl[i + 1:j])
            i = j + 1
        elif c == ":":
            cift = bl.startswith("::", i)
            i += 2 if cift else 1
            m = re.match(r"[-\w]+", bl[i:])
            if not m:
                return None
            ad = m.group(0).lower()
            i += m.end()
            arg = None
            if i < len(bl) and bl[i] == "(":
                derinlik, k = 1, i + 1
                while k < len(bl) and derinlik:
                    if bl[k] == "(":
                        derinlik += 1
                    elif bl[k] == ")":
                        derinlik -= 1
                    k += 1
                if derinlik:
                    return None
                arg = bl[i + 1:k - 1]
                i = k
            if cift or ad in SAHTE_ELEMAN:
                d["psel"].append((ad, arg))
            else:
                d["pcls"].append((ad, arg))
        else:
            m = re.match(r"[-\w]+", bl[i:])
            if not m:
                return None
            d["etiket"] = m.group(0).lower()
            i += m.end()
    return d


def _oz_esler(ifade, kok):
    m = re.match(r'^\s*([-\w]+)\s*(?:([~|^$*]?=)\s*("([^"]*)"|\'([^\']*)\'|[^\s\]]+)'
                 r'\s*([iIsS])?\s*)?$', ifade)
    if not m:
        return None
    ad = m.group(1).lower()
    varsa = kok["oz"].get(ad)
    if m.group(2) is None:
        return varsa is not None
    if varsa is None:
        return False
    ham = m.group(3)
    beklenen = m.group(4) if m.group(4) is not None else (m.group(5) if m.group(5) is not None else ham)
    if m.group(6) and m.group(6).lower() == "i":
        varsa, beklenen = varsa.lower(), beklenen.lower()
    op = m.group(2)
    if op == "=":
        return varsa == beklenen
    if op == "~=":
        return beklenen in varsa.split()
    if op == "|=":
        return varsa == beklenen or varsa.startswith(beklenen + "-")
    if op == "^=":
        return varsa.startswith(beklenen)
    if op == "$=":
        return varsa.endswith(beklenen)
    if op == "*=":
        return beklenen in varsa
    return None


def bilesik_esler(bl, kok, atalar=None, belirsiz=None):
    d = bilesik_ayristir(bl)
    if d is None:
        return belirsiz
    if d["psel"]:
        return False
    if d["etiket"] and d["etiket"] != kok["etiket"]:
        return False
    if d["id"] and d["id"] != kok["oz"].get("id"):
        return False
    if not d["sinif"] <= kok["sinif"]:
        return False
    for ifade in d["oz"]:
        r = _oz_esler(ifade, kok)
        if r is None:
            return belirsiz
        if not r:
            return False
    for ad, arg in d["pcls"]:
        if ad in DURUM_PCLS:
            continue
        if ad in UYMAZ_PCLS:
            return False
        if ad == "not":
            if arg is None:
                return belirsiz
            ic = [secici_esler(p, kok, atalar, belirsiz) for p in _derinlik_bol(arg, ",")]
            if any(x is None for x in ic):
                return belirsiz
            if any(ic):
                return False
            continue
        if ad in LISTE_PCLS:
            if arg is None:
                return belirsiz
            ic = [secici_esler(p, kok, atalar, belirsiz) for p in _derinlik_bol(arg, ",")]
            if any(x is None for x in ic):
                return belirsiz
            if not any(ic):
                return False
            continue
        return belirsiz
    return True


def secici_esler(secici, kok, atalar=None, belirsiz=None):
    bl = _bilesikler(secici.strip())
    if not bl:
        return False
    r = bilesik_esler(bl[-1], kok, atalar, belirsiz)
    if r is not True:
        return r
    if len(bl) == 1:
        return True
    if atalar is None:
        return belirsiz
    for onceki in bl[:-1]:
        uydu, bulanik = False, False
        for ata in atalar:
            a = bilesik_esler(onceki, ata, None, belirsiz)
            if a is True:
                uydu = True
                break
            if a is None:
                bulanik = True
        if not uydu:
            return belirsiz if bulanik else False
    return True


def durumsal_mi(secici):
    for bl in _bilesikler(secici.strip()):
        d = bilesik_ayristir(bl)
        if d is None:
            continue
        if any(ad in DURUM_PCLS for ad, _ in d["pcls"]):
            return True
    return False


def ozgulluk(secici):
    a = b = c = 0
    for bl in _bilesikler(secici.strip()):
        d = bilesik_ayristir(bl)
        if d is None:
            continue
        a += 1 if d["id"] else 0
        b += len(d["sinif"]) + len(d["oz"]) + len([1 for ad, _ in d["pcls"] if ad != "not"])
        c += (1 if d["etiket"] else 0) + len(d["psel"])
    return (a, b, c)


BANNER_JETON = re.compile(r"skan-banner|jen-banner|skanBanner|jenBanner")
SARI_JETON = re.compile(r"skan-banner|skanBanner")


def ozne_banner_jetonlu_mu(tek_secici):
    bl = _bilesikler(tek_secici.strip())
    if not bl:
        return False
    ozne = bl[-1]
    d = bilesik_ayristir(ozne)
    if d is None:
        return bool(BANNER_JETON.search(ozne))
    if d["id"] and BANNER_JETON.search(d["id"]):
        return True
    if any(BANNER_JETON.search(s) for s in d["sinif"]):
        return True
    if any(BANNER_JETON.search(o) for o in d["oz"]):
        return True
    return any(BANNER_JETON.search(arg or "") for _ad, arg in d["pcls"])


VOID_ETIKET = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
               "meta", "param", "source", "track", "wbr"}


def ata_zinciri(html_metin, hedef_ofset):
    temiz = re.sub(r"(<(?:script|style)\b[^>]*>)(.*?)(</(?:script|style)>)",
                   lambda m: m.group(1) + (" " * len(m.group(2))) + m.group(3),
                   html_metin, flags=re.S | re.I)
    yigin = []
    for m in re.finditer(r"<(/?)([a-zA-Z][-\w]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>", temiz):
        if m.start() >= hedef_ofset:
            break
        kapali, etiket, oz_ham, kendi = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if kapali:
            for i in range(len(yigin) - 1, -1, -1):
                if yigin[i]["etiket"] == etiket:
                    del yigin[i:]
                    break
        elif etiket not in VOID_ETIKET and not kendi:
            oz = {a.lower(): d for a, d in re.findall(r'([-\w]+)\s*=\s*"([^"]*)"', oz_ham)}
            yigin.append({"etiket": etiket, "oz": oz, "sinif": set(oz.get("class", "").split())})
    return yigin


def kok_kurallari(kurallar, kok, atalar, belirsiz=None, cozulemeyeni_kaydet=True):
    out = []
    for sira, (secici, govde, medya) in enumerate(kurallar):
        for tek in _derinlik_bol(secici, ","):
            tek = tek.strip()
            if not tek:
                continue
            r = secici_esler(tek, kok, atalar, belirsiz)
            if r is None:
                if cozulemeyeni_kaydet and (BANNER_JETON.search(tek) or "skanBanner" in tek):
                    COZULEMEYEN_SECICI.append(tek)
                continue
            if r:
                out.append((sira, ozgulluk(tek), tek, govde, durumsal_mi(tek), bool(medya)))
    return out


def etkin_stil(kok_kural_listesi, inline_govde="", durumu_dahil_et=True,
               medyayi_dahil_et=True):
    aday = {}
    for sira, spec, secici, govde, durumsal, medyali in kok_kural_listesi:
        if durumsal and not durumu_dahil_et:
            continue
        if medyali and not medyayi_dahil_et:
            continue
        for ad, deger, onemli in bildirimleri_ayristir(govde):
            anahtar = (1 if onemli else 0, spec, sira)
            if ad not in aday or anahtar > aday[ad][0]:
                aday[ad] = (anahtar, deger, secici)
    for ad, deger, onemli in bildirimleri_ayristir(inline_govde):
        aday[ad] = (((1 if onemli else 0), (9, 9, 9), 10 ** 9), deger, "inline style")
    return {ad: (v[1], v[2]) for ad, v in aday.items()}


# ---------------------------------------------------------------- var() cozumu
VAR_CAGRI = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,([^()]*(?:\([^()]*\)[^()]*)*))?\)")


def ozel_ozellik_tanimlari(kurallar):
    tanim = {}
    for secici, govde, _medya in kurallar:
        for ad, deger, _onemli in bildirimleri_ayristir(govde):
            if ad.startswith("--"):
                tanim[ad] = deger
    return tanim


def var_coz(metin, tanimlar, derinlik=0):
    cozulemeyen = []
    if derinlik > 8:
        return metin, ["var() ic ice cozum derinligi asildi: %s" % metin[:60]]

    def _degistir(m):
        ad, yedek = m.group(1), m.group(2)
        if ad in tanimlar:
            alt, eksik = var_coz(tanimlar[ad], tanimlar, derinlik + 1)
            cozulemeyen.extend(eksik)
            return alt
        if yedek is not None:
            alt, eksik = var_coz(yedek.strip(), tanimlar, derinlik + 1)
            cozulemeyen.extend(eksik)
            return alt
        cozulemeyen.append(ad)
        return " "

    yeni = VAR_CAGRI.sub(_degistir, metin)
    if VAR_CAGRI.search(yeni) and yeni != metin:
        yeni, eksik = var_coz(yeni, tanimlar, derinlik + 1)
        cozulemeyen.extend(eksik)
    return yeni, cozulemeyen


# ---------------------------------------------------------------- sari tarayici
SARI_ADLAR = {
    "yellow", "gold", "goldenrod", "darkgoldenrod", "palegoldenrod",
    "khaki", "darkkhaki", "lightyellow", "lemonchiffon", "cornsilk",
    "moccasin", "papayawhip", "blanchedalmond", "navajowhite", "wheat",
    "greenyellow", "yellowgreen",
}
SARI_KELIME = re.compile(r"yellow|gold(?:en)?|amber|sar[ıi]\b", re.I)
HEX = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b")
RGB_FN = re.compile(r"\brgba?\(\s*([\d.]+)(%?)[\s,/]+([\d.]+)(%?)[\s,/]+([\d.]+)(%?)", re.I)
HSL_FN = re.compile(r"\bhsla?\(\s*([\d.]+)(?:deg)?[\s,/]+([\d.]+)%[\s,/]+([\d.]+)%", re.I)
AD_FN = re.compile(r"\b(%s)\b" % "|".join(sorted(SARI_ADLAR, key=len, reverse=True)), re.I)
MODERN_RENK = re.compile(r"(?<![-\w])(oklch|oklab|lab|lch|hwb|color-mix|color)\s*\(", re.I)
YORUM = re.compile(r"/\*.*?\*/|<!--.*?-->", re.S)


def _hue_sat(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0.0, 0.0
    d = mx - mn
    if mx == r:
        h = (60 * ((g - b) / d)) % 360
    elif mx == g:
        h = 60 * ((b - r) / d) + 120
    else:
        h = 60 * ((r - g) / d) + 240
    return h, d / float(mx)


def _sari_mi(r, g, b):
    h, s = _hue_sat(r, g, b)
    if not (40 <= h <= 70):
        return False
    return (s >= 0.35 and max(r, g, b) >= 120) or max(r, g, b) >= 200


def _hsl_rgb(h, s, l):
    h = (h % 360) / 360.0
    s, l = s / 100.0, l / 100.0
    if s == 0:
        v = int(round(l * 255))
        return v, v, v
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def kanal(t):
        t = t % 1.0
        if t < 1 / 6.0:
            return p + (q - p) * 6 * t
        if t < 0.5:
            return q
        if t < 2 / 3.0:
            return p + (q - p) * (2 / 3.0 - t) * 6
        return p

    return tuple(int(round(kanal(h + o) * 255)) for o in (1 / 3.0, 0.0, -1 / 3.0))


def sari_bulgular(parca):
    parca = YORUM.sub(" ", parca)
    try:
        cozulmus = urllib.parse.unquote(parca)
    except (UnicodeDecodeError, ValueError):
        cozulmus = parca
    if cozulmus != parca:
        parca = parca + "\n" + cozulmus
    bulgu = []
    for m in HEX.finditer(parca):
        ham = m.group(1)
        if len(ham) in (3, 4):
            ham = "".join(c * 2 for c in ham[:3])
        else:
            ham = ham[:6]
        r, g, b = (int(ham[i:i + 2], 16) for i in (0, 2, 4))
        if _sari_mi(r, g, b):
            bulgu.append("#" + ham)
    for m in RGB_FN.finditer(parca):
        try:
            kanallar = []
            for deger, yuzde in ((m.group(1), m.group(2)), (m.group(3), m.group(4)),
                                 (m.group(5), m.group(6))):
                v = float(deger)
                kanallar.append(v * 2.55 if yuzde else v)
        except ValueError:
            continue
        if _sari_mi(*kanallar):
            bulgu.append(m.group(0) + ")")
    for m in HSL_FN.finditer(parca):
        try:
            rgb = _hsl_rgb(float(m.group(1)), float(m.group(2)), float(m.group(3)))
        except ValueError:
            continue
        if _sari_mi(*rgb):
            bulgu.append(m.group(0) + ")")
    for m in AD_FN.finditer(parca):
        bulgu.append(m.group(1))
    for m in SARI_KELIME.finditer(parca):
        bulgu.append(m.group(0))
    for m in MODERN_RENK.finditer(parca):
        bulgu.append("COZULEMEYEN renk notasyonu: %s()" % m.group(1))
    return sorted(set(bulgu))


# ---------------------------------------------------------------- gorunurluk olcumu
def _uzunluk_px(deger):
    if deger is None:
        return None
    v = deger.strip().lower()
    m = re.match(r"^(-?[\d.]+)(px|rem|em|vh|vw|vmin|vmax|%|pt|pc|cm|mm|in|ch|ex)?$", v)
    if not m:
        return None
    try:
        sayi = float(m.group(1))
    except ValueError:
        return None
    birim = m.group(2) or "px"
    carpan = {"px": 1.0, "rem": 16.0, "em": 16.0, "vh": 8.0, "vw": 12.8, "vmin": 8.0,
              "vmax": 12.8, "%": 1.0, "pt": 4 / 3.0, "pc": 16.0, "cm": 37.8,
              "mm": 3.78, "in": 96.0, "ch": 8.0, "ex": 8.0}[birim]
    return sayi * carpan


IZINLI_KOK_OZELLIKLERI = {
    "display", "position", "top", "right", "bottom", "left", "inset", "z-index",
    "overflow", "overflow-x", "overflow-y", "box-sizing", "float", "clear",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left", "margin-inline",
    "margin-block", "padding", "padding-top", "padding-right", "padding-bottom",
    "padding-left", "padding-inline", "padding-block",
    "width", "min-width", "max-width", "height", "min-height", "max-height",
    "align-items", "align-self", "align-content", "justify-content", "justify-items",
    "justify-self", "flex", "flex-basis", "flex-direction", "flex-grow", "flex-shrink",
    "flex-wrap", "order", "gap", "row-gap", "column-gap", "grid-template-columns",
    "grid-template-rows", "aspect-ratio",
    "background", "background-color", "background-image", "background-size",
    "background-position", "background-repeat", "background-attachment", "background-clip",
    "background-origin", "border", "border-top", "border-right", "border-bottom",
    "border-left", "border-color", "border-width", "border-style", "border-radius",
    "border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius",
    "border-bottom-right-radius", "box-shadow", "color", "opacity", "visibility",
    "outline", "outline-color", "outline-offset", "outline-width", "outline-style",
    "accent-color", "isolation",
    "font", "font-family", "font-size", "font-style", "font-weight", "font-variant",
    "line-height", "letter-spacing", "word-spacing", "text-align", "text-decoration",
    "text-decoration-color", "text-decoration-line", "text-indent", "text-shadow",
    "text-transform", "white-space", "word-break", "overflow-wrap", "vertical-align",
    "-webkit-font-smoothing",
    "filter",
    "cursor", "pointer-events", "content-visibility", "user-select", "-webkit-user-select",
    "-webkit-tap-highlight-color", "touch-action", "appearance", "-webkit-appearance",
    "transition", "transition-property", "transition-duration", "transition-timing-function",
    "transition-delay", "will-change", "contain-intrinsic-size",
}
OLDUREN_DISPLAY = {"none", "contents"}
IZINLI_FILTRE_FN = {"brightness", "contrast", "drop-shadow"}
FILTRE_ARALIK = (0.5, 2.0)


def filtre_sorunlari(deger, kaynak):
    s = []
    ham = (deger or "").strip()
    if not ham or ham.lower() == "none":
        return s
    fonksiyonlar = re.findall(r"([-\w]+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", ham)
    if not fonksiyonlar:
        s.append("filter degeri cozulemedi: %r  [%s]" % (ham, kaynak))
        return s
    for ad, arg in fonksiyonlar:
        ad = ad.lower()
        if ad not in IZINLI_FILTRE_FN:
            s.append("filter:%s() banner ROOT'unda beklenmedik  [%s]" % (ad, kaynak))
            continue
        if ad in ("brightness", "contrast"):
            m = re.match(r"^\s*([\d.]+)\s*(%?)\s*$", arg)
            if not m:
                s.append("filter:%s(%s) degeri cozulemedi  [%s]" % (ad, arg.strip(), kaynak))
                continue
            v = float(m.group(1)) / 100.0 if m.group(2) else float(m.group(1))
            if not (FILTRE_ARALIK[0] <= v <= FILTRE_ARALIK[1]):
                s.append("filter:%s(%s) araligin (%s-%s) disinda  [%s]"
                         % (ad, arg.strip(), FILTRE_ARALIK[0], FILTRE_ARALIK[1], kaynak))
    return s


def gorunurluk_sorunlari(etkin, mod="kosulsuz"):
    s = []

    def dg(ad):
        return etkin[ad][0] if ad in etkin else None

    def kaynak(ad):
        return etkin[ad][1] if ad in etkin else "-"

    def sayi(ad):
        ham = (dg(ad) or "").strip()
        if not ham:
            return None
        try:
            return float(ham[:-1]) / 100.0 if ham.endswith("%") else float(ham)
        except ValueError:
            return None

    E = BANNER_ASGARI_YUKSEKLIK_PX
    if mod == "taban":
        mh = _uzunluk_px(dg("min-height"))
        hh = _uzunluk_px(dg("height"))
        if (mh is None or mh < E) and (hh is None or hh < E):
            s.append("banner ROOT'unda KOSULSUZ >= %dpx yukseklik YOK "
                     "(min-height=%r [%s], height=%r [%s])"
                     % (E, dg("min-height"), kaynak("min-height"),
                        dg("height"), kaynak("height")))
        for ad in ("width", "max-width"):
            gv = _uzunluk_px(dg(ad))
            if gv is not None and gv < E:
                s.append("%s:%s < %dpx (banner kutusu kapaniyor)  [%s]"
                         % (ad, dg(ad), E, kaynak(ad)))
        fs = _uzunluk_px(dg("font-size"))
        if fs is not None and fs < 8:
            s.append("font-size:%s (metin sifirlanir)  [%s]"
                     % (dg("font-size"), kaynak("font-size")))
        for ad in sorted(etkin):
            if ad.startswith("--") or ad in IZINLI_KOK_OZELLIKLERI:
                continue
            s.append("banner ROOT'unda BEYAZ LISTE DISI ozellik: %s:%s  [%s]"
                     % (ad, dg(ad), kaynak(ad)))
        return s

    disp = (dg("display") or "").strip().lower()
    if disp in OLDUREN_DISPLAY:
        s.append("display:%s  [%s]" % (disp, kaynak("display")))
    if (dg("visibility") or "").strip().lower() in ("hidden", "collapse"):
        s.append("visibility:%s  [%s]" % (dg("visibility"), kaynak("visibility")))

    op = dg("opacity")
    if op is not None:
        deger = sayi("opacity")
        if deger is None:
            s.append("opacity cozulemedi: %r  [%s]" % (op, kaynak("opacity")))
        elif deger <= 0:
            s.append("opacity %s == 0 (gorunmez)  [%s]" % (op.strip(), kaynak("opacity")))
        elif mod == "kosulsuz" and deger < 0.9:
            s.append("opacity %s < 0.9 (KOSULSUZ kuralda)  [%s]" % (op.strip(), kaynak("opacity")))

    if mod == "durum":
        return s

    if (dg("pointer-events") or "").strip().lower() == "none":
        s.append("pointer-events:none  [%s]" % kaynak("pointer-events"))
    if (dg("content-visibility") or "").strip().lower() == "hidden":
        s.append("content-visibility:hidden  [%s]" % kaynak("content-visibility"))

    mx = _uzunluk_px(dg("max-height"))
    if mx is not None and mx < E:
        s.append("max-height:%s < %dpx asgari banner yuksekligi  [%s]"
                 % (dg("max-height"), E, kaynak("max-height")))
    for ad in ("width", "max-width", "height", "min-height"):
        gv = _uzunluk_px(dg(ad))
        if gv is not None and gv <= 0:
            s.append("%s:%s (kutu sifirlanir)  [%s]" % (ad, dg(ad), kaynak(ad)))
    fs = _uzunluk_px(dg("font-size"))
    if fs is not None and fs < 8:
        s.append("font-size:%s (metin sifirlanir)  [%s]" % (dg("font-size"), kaynak("font-size")))
    s.extend(filtre_sorunlari(dg("filter"), kaynak("filter")))

    pos = (dg("position") or "").strip().lower()
    if pos in ("absolute", "fixed"):
        for yon in ("left", "top", "right", "bottom"):
            pv = _uzunluk_px(dg(yon))
            if pv is not None and pv <= -1000:
                s.append("%s:%s + position:%s -> ekran disi  [%s]"
                         % (yon, dg(yon), pos, kaynak(yon)))
    for ad in ("margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
               "margin-block", "margin-inline"):
        for parca in (dg(ad) or "").split():
            pv = _uzunluk_px(parca)
            if pv is not None and pv <= -1000:
                s.append("%s:%s -> banner ekran disina itiliyor  [%s]"
                         % (ad, dg(ad), kaynak(ad)))
                break

    tr = dg("transform") or ""
    if re.search(r"\bscale[XYZ3d]*\(\s*0*(?:\.0+)?\s*[,)]", tr, re.I):
        s.append("transform scale(0)  [%s]" % kaynak("transform"))
    for m in re.finditer(r"\btranslate[XYZ3d]*\(([^)]*)\)", tr, re.I):
        for parca in m.group(1).split(","):
            pv = _uzunluk_px(parca)
            if pv is not None and (pv <= -1000 or pv >= 3000):
                s.append("transform ekran disi: %s  [%s]" % (m.group(0), kaynak("transform")))
    sc = _uzunluk_px(dg("scale"))
    if sc is not None and sc == 0:
        s.append("scale:0  [%s]" % kaynak("scale"))
    for ad in ("clip-path", "clip"):
        if dg(ad):
            s.append("%s:%s banner ROOT'unda (gorunurlugu kirpar)  [%s]"
                     % (ad, dg(ad), kaynak(ad)))
    return s


# ---------------------------------------------------------------- marka/cografya kurali
YASAK_IFADE = [
    (re.compile(r"3\s*[dD]\s*bask", re.I), '"3D baskı" (marka dili: "özel tasarım üretim")'),
    (re.compile(r"3\s*[dD]\s*print", re.I), '"3D print"'),
    (re.compile(r"[üu]ç\s*boyutlu\s*bask", re.I), '"üç boyutlu baskı"'),
    (re.compile(r"Fethiye|Göcek|Gocek|Muğla|Mugla|Dalaman", re.I), "şehir/coğrafya adı"),
]


def yasak_ifadeler(parca):
    return [etiket for desen, etiket in YASAK_IFADE if desen.search(parca)]


# ---------------------------------------------------------------- node kosucu
def node_var_mi():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def node_kos(kaynak, etiket, bildir=kontrol):
    """Gecici .js dosyasi yazip node ile kosar; stdout'un SON satirini JSON ayristirir."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(kaynak)
        yol = f.name
    try:
        r = subprocess.run(["node", yol], capture_output=True, text=True)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        bildir(False, "%s node ile kosuyor (stderr: %s)"
               % (etiket, (r.stderr.strip()[:300] or "-")))
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        bildir(False, "%s node ciktisi JSON degil: %r" % (etiket, r.stdout[:200]))
        return None


# ================================================================== okumalar
index_html = oku(INDEX)
secenekler_js = oku(SECENEKLER)
with open(URUNLER, encoding="utf-8") as _f:
    katalog = json.load(_f)

print("SKAN ART KABUL TESTI — IKI KATMAN (cekirdek = bloklayici, uyari = exit 0)")
print("=" * 70)
print("KATMAN 1 — BLOKLAYICI CEKIRDEK (B1-B10)")
print("=" * 70)

# ============================================================ B1 — gizli liste paritesi
print("(B1) 'Skan Art' iki gizli-nav kaynaginda ve AYNI sira indeksinde")
i_giz = js_liste(index_html, r"var\s+GIZLI_KATEGORILER\s*=\s*\[(.*?)\]",
                 "index.html GIZLI_KATEGORILER")
b_giz = list(build.NAV_GIZLI)
kontrol(KATEGORI in b_giz, '"%s" tools/build.py NAV_GIZLI icinde (bulunan: %s)' % (KATEGORI, b_giz))
kontrol(i_giz is not None and KATEGORI in i_giz,
        '"%s" index.html GIZLI_KATEGORILER icinde (bulunan: %s)' % (KATEGORI, i_giz))
if i_giz is not None and KATEGORI in i_giz and KATEGORI in b_giz:
    kontrol(i_giz.index(KATEGORI) == b_giz.index(KATEGORI),
            "sira indeksi iki kaynakta AYNI (index.html=%d, build.py=%d)"
            % (i_giz.index(KATEGORI), b_giz.index(KATEGORI)))
else:
    kontrol(False, "sira indeksi karsilastirilamadi (uyelik saglanmadi)")

# ============================================================ B2 — gorunur nav'da DEGIL
print("(B2) 'Skan Art' GORUNUR nav cip kaynaginda DEGIL — iki kaynakta da")
i_cat = js_liste(index_html, r"var\s+CATEGORIES\s*=\s*\[(.*?)\]", "index.html CATEGORIES")
kontrol(i_cat is not None and KATEGORI not in i_cat,
        '"%s" index.html CATEGORIES listesinde DEGIL' % KATEGORI)
kontrol(KATEGORI not in build.CATEGORIES,
        '"%s" tools/build.py CATEGORIES listesinde DEGIL' % KATEGORI)

# ============================================================ B3 — FONKSIYONEL uyeligi
print("(B3) 'Skan Art' FONKSIYONEL_KATEGORILER icinde — build.py + secenekler.js")
s_fonk = js_liste(secenekler_js, r"var\s+FONKSIYONEL_KATEGORILER\s*=\s*\[(.*?)\]",
                  "secenekler.js FONKSIYONEL_KATEGORILER")
kontrol(KATEGORI in build.FONKSIYONEL_KATEGORILER,
        '"%s" tools/build.py FONKSIYONEL_KATEGORILER icinde' % KATEGORI)
kontrol(s_fonk is not None and KATEGORI in s_fonk,
        '"%s" secenekler.js FONKSIYONEL_KATEGORILER icinde' % KATEGORI)

# ============================================================ B4 — feed taksonomisi
print("(B4) merchant feed taksonomisi")
kontrol(KATEGORI in build.GOOGLE_PRODUCT_CATEGORY,
        'GOOGLE_PRODUCT_CATEGORY["%s"] tanimli -> %r'
        % (KATEGORI, build.GOOGLE_PRODUCT_CATEGORY.get(KATEGORI)))

# ============================================================ B5/B6/B7 — urun verisi
print("(B5/B6/B7) urun verisi — kurt kategorisi, seri bos degil, konfigur emniyeti")
kurtlar = [u for u in katalog if u.get("id") == PID]
kontrol(len(kurtlar) == 1, "%s katalogda TEK kayit (bulunan: %d)" % (PID, len(kurtlar)))
kurt = kurtlar[0] if kurtlar else None
kontrol(kurt is not None and kurt.get("kategori") == KATEGORI,
        'kurt urununun kategorisi == "%s" (bulunan: %r)'
        % (KATEGORI, kurt.get("kategori") if kurt else None))

skan_urunler = [u for u in katalog if u.get("kategori") == KATEGORI]
n_skan = len(skan_urunler)
kontrol(n_skan >= SKAN_ART_TABAN,
        "Skan Art serisi BOS DEGIL (>= %d; bulunan: %d)" % (SKAN_ART_TABAN, n_skan))

konfigursuz = [u.get("id") for u in skan_urunler if not u.get("konfigur")]
kontrol(not konfigursuz,
        "her Skan Art urunu `konfigur` tasiyor (konfigursuz: %s) — PARA EMNIYETI: worker "
        "secenekler.js'i bundle'a gommedigi icin konfigursuz urunde malzeme/renk katsayisi "
        "CANLIDA duser" % (konfigursuz or "-"))

if kurt is None:
    print("  ❌ kurt urunu bulunamadi — B8/B9 olculemez")
    bitir()

# ============================================================ B9 — URETIM HATTI
print("(B9) uretim hatti — build.py main() kum havuzunda, sayfa DISKTE + sitemap")


def uretim_hatti_olc():
    """build.py'yi kum havuzunda kostur; (kurt_sayfasi_html, sitemap_xml, hata) dondur."""
    kum = tempfile.mkdtemp(prefix="skan-art-uretim-")
    try:
        uretilen = {"urun", "urunler.json", "sitemap.xml", "robots.txt", "merchant-feed.xml",
                    "index.built.html", "ozet.json", "taban-fiyatlar.js", "filament-veri.js",
                    "_yayin-icerik-dizinleri.txt", ".nojekyll", ".git", ".claude"}
        yazilan_dizin = set(build.STATIK_SAYFALAR)
        for ad in os.listdir(ROOT):
            if ad in uretilen:
                continue
            hedef = os.path.join(kum, ad)
            if ad in yazilan_dizin:              # main() bu dizinlere YAZAR -> gercek kopya
                shutil.copytree(os.path.join(ROOT, ad), hedef)
            else:
                os.symlink(os.path.join(ROOT, ad), hedef)
        alt = [kurt] + [u for u in katalog if u.get("kategori") == "Dekorasyon"][:8]
        with open(os.path.join(kum, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump(alt, f, ensure_ascii=False)
        r = subprocess.run([sys.executable, "-B", os.path.join(kum, "tools", "build.py")],
                           capture_output=True, text=True, env=ALT_SUREC_ENV)
        if r.returncode != 0:
            return None, None, "build.py cikis kodu %d (stderr: %s)" % (
                r.returncode, r.stderr.strip()[-300:] or "-")
        sayfa_yolu = os.path.join(kum, "urun", PID, "index.html")
        if not os.path.isfile(sayfa_yolu):
            return None, None, ("urun/%s/index.html DISKTE URETILMEDI "
                                "(main() dongusu urunu atladi mi?)" % PID)
        with open(sayfa_yolu, encoding="utf-8") as f:
            sayfa = f.read()
        sm_yolu = os.path.join(kum, "sitemap.xml")
        if not os.path.isfile(sm_yolu):
            return sayfa, None, "sitemap.xml uretilmedi"
        with open(sm_yolu, encoding="utf-8") as f:
            return sayfa, f.read(), None
    finally:
        shutil.rmtree(kum, ignore_errors=True)


KOMPAKT = ['class="eylem-ikonlar"', 'ikon-btn ikon-sepet', 'ikon-btn ikon-wa', 'opsiyon-adet-eylem']
FALLBACK = ['<span class="cart-label">Sepete Ekle</span>', 'class="order-wa"']

u_sayfa, u_sitemap, u_hata = uretim_hatti_olc()
kontrol(u_hata is None,
        "build.py main() kum havuzunda kurt sayfasini DISKE yazdi (hata: %s)" % (u_hata or "-"))
if u_sayfa:
    for isaret in KOMPAKT:
        kontrol(u_sayfa.count(isaret) >= 1,
                "URETILEN dosyada kompakt kart isareti VAR: %s" % isaret)
if u_sitemap:
    kontrol(build.product_url(PID) in u_sitemap,
            "sitemap.xml'de kurt URL'i VAR (%s)" % build.product_url(PID))

# ============================================================ B8 — banner ELEMANI + hedefi
print("(B8) ana sayfa banner ELEMANI + href'in DAVRANISSAL hedefi")
m_ban = re.search(r'<a id="skanBanner"[^>]*>.*?</a>', index_html, re.S)
kontrol(m_ban is not None, 'index.html icinde <a id="skanBanner"> ELEMANI var')
banner_html = m_ban.group(0) if m_ban else ""
m_ac = re.search(r'<a id="skanBanner"[^>]*>', banner_html)
banner_ac = m_ac.group(0) if m_ac else ""
BANNER_OZ = {ad.lower(): deger for ad, deger in
             re.findall(r'([-\w]+)\s*=\s*"([^"]*)"', banner_ac)}
banner_href = BANNER_OZ.get("href", "")
banner_qs = banner_href[banner_href.find("?"):] if "?" in banner_href else ""

# ---- node harness kaynaklari (B8 + B10)
cat_src = js_bildirim(index_html, r"^\s*var\s+CATEGORIES\s*=.*$", "index.html CATEGORIES")
giz_src = js_bildirim(index_html, r"^\s*var\s+GIZLI_KATEGORILER\s*=.*$",
                      "index.html GIZLI_KATEGORILER")
applyurl_src = js_fonksiyon(index_html, "applyUrlParams")
rendergrid_src = js_fonksiyon(index_html, "renderGrid")

NODE_VAR = node_var_mi()
NODE_ATLANDI = False
if not NODE_VAR:
    if os.environ.get("GITHUB_ACTIONS"):
        kontrol(False, "CI'da node var (FAIL-CLOSED: setup-node eksik/bozuk) — B8/B10 olculemedi")
    elif os.environ.get("SKAN_ART_NODE_ATLA") == "1":
        NODE_ATLANDI = True
        print("  ⚠️  node yok + SKAN_ART_NODE_ATLA=1 → B8/B10 ACIK uyariyla ATLANDI")
        UYARILAR.append("B8/B10 node yoklugunda atlandi (SKAN_ART_NODE_ATLA=1) — OLCULMEDI")
    else:
        kontrol(False, "node bulundu (yerelde kur ya da SKAN_ART_NODE_ATLA=1 ile atla)")

if NODE_VAR and applyurl_src:
    b2 = r"""
"use strict";
__CAT__
__GIZ__
var activeCat, activeBrand, query;
var searchEl = { value: "" };
var clearEl = { className: "" };
function markaKatla(x){ return x; }
var location = { hash: "", search: "", replace: function(){ throw new Error("beklenmedik yonlendirme"); } };
__APPLYURL__
function dene(qs){
  activeCat = "Tümü"; activeBrand = "Tümü"; query = "";
  location.hash = ""; location.search = qs;
  applyUrlParams();
  return activeCat;
}
console.log(JSON.stringify({
  skan: dene("?kategori=Skan%20Art"),
  banner: dene(__BANNERQS__)
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__APPLYURL__", applyurl_src) \
       .replace("__BANNERQS__", json.dumps(banner_qs))
    s2 = node_kos(b2, "(B8) applyUrlParams")
    if s2:
        kontrol(s2["skan"] == KATEGORI,
                '?kategori=Skan%%20Art derin linki activeCat\'i "%s" yapiyor (bulunan: %r)'
                % (KATEGORI, s2["skan"]))
        kontrol(s2["banner"] == KATEGORI,
                'banner href\'i (%r) DAVRANISSAL olarak "%s" kategorisini aciyor (bulunan: %r)'
                % (banner_href, KATEGORI, s2["banner"]))

# ============================================================ B10 — renderGrid DAVRANISI
print("(B10) renderGrid goster/gizle DAVRANISI (node + sahte DOM)")
if NODE_VAR and rendergrid_src:
    b4 = r"""
"use strict";
__CAT__
__GIZ__
var EDGE_KATALOG = false;
var edgeListe = [], edgeToplam = 0, edgeDurum = "", edgeSayfa = 1;
var PAGE_SIZE = 24, shown = 24;
var HOME_ORDER = [{id:"a"},{id:"b"}];
var activeCat = "Tümü", activeBrand = "Tümü", query = "";
var kayit = {}, elemanlar = {};
function sahteEleman(id){
  var o = { __id:id, style:{}, className:"", textContent:"", innerHTML:"",
            appendChild:function(){}, setAttribute:function(){}, onclick:null, disabled:false };
  Object.defineProperty(o.style, "display", {
    set: function(v){ kayit[id] = v; }, get: function(){ return kayit[id]; }, configurable:true });
  return o;
}
var document = {
  getElementById: function(id){
    if(!(id in elemanlar)){ elemanlar[id] = sahteEleman(id); }
    return elemanlar[id];
  },
  createElement: function(){ return sahteEleman("__yeni__"); }
};
function filtered(){ return [{id:"a"},{id:"b"}]; }
function kartCiz(){ return sahteEleman("__kart__"); }
function renderEdgeDurum(){}
function edgeYukle(){}
__RENDERGRID__
function olc(cat, q, marka){
  kayit = {}; elemanlar = {};
  activeCat = cat; query = q; activeBrand = marka;
  renderGrid();
  return ("skanBanner" in kayit) ? kayit["skanBanner"] : "__HIC-DOKUNULMADI__";
}
console.log(JSON.stringify({
  ana: olc("Tümü", "", "Tümü"),
  kategori: olc("Dekorasyon", "", "Tümü"),
  arama: olc("Tümü", "ahsap", "Tümü"),
  marka: olc("Tümü", "", "Audi")
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__RENDERGRID__", rendergrid_src)
    s4 = node_kos(b4, "(B10) renderGrid banner toggle")
    if s4:
        kontrol(s4["ana"] == "",
                'ANA gorunumde skanBanner display === "" (bulunan: %r)' % s4["ana"])
        kontrol(s4["kategori"] == "none",
                'KATEGORI gorunumunde skanBanner display === "none" (bulunan: %r)' % s4["kategori"])
        kontrol(s4["arama"] == "none",
                'ARAMA gorunumunde skanBanner display === "none" (bulunan: %r)' % s4["arama"])
        kontrol(s4["marka"] == "none",
                'MARKA gorunumunde skanBanner display === "none" (bulunan: %r)' % s4["marka"])

# ================================================================== KATMAN 2 — UYARI
print("")
print("=" * 70)
print("KATMAN 2 — UYARI (bulgular exit koduna DOKUNMAZ; deploy DURMAZ)")
print("=" * 70)


def uyari_bolumu(baslik, fn):
    """Uyari bolumunu KOSUR — HICBIR istisna exit'i bozamaz."""
    print(baslik)
    try:
        fn()
    except Exception as e:                              # noqa: BLE001 — bilerek genis
        mesaj = "bolum '%s' istisna atti (exit'e DOKUNMAZ): %s: %s" % (
            baslik, type(e).__name__, e)
        print("  ⚠️  UYARI: " + mesaj)
        for satir in traceback.format_exc().splitlines()[-6:]:
            print("       | " + satir)
        UYARILAR.append(mesaj)


# ---- ortak paylasilan hesaplamalar (uyari katmani icin)
DURUM = {}


def _u_hazirlik():
    DURUM["KOK"] = {
        "etiket": "a",
        "oz": BANNER_OZ,
        "sinif": set(BANNER_OZ.get("class", "").split()),
    }
    DURUM["css_hepsi"] = css_bloklari(index_html)
    DURUM["tum_kurallar"] = css_kurallari(DURUM["css_hepsi"])
    DURUM["VAR_TANIM"] = ozel_ozellik_tanimlari(DURUM["tum_kurallar"])
    DURUM["ATALAR"] = ata_zinciri(index_html, m_ban.start() if m_ban else 0)
    DURUM["kok_kural_tum"] = kok_kurallari(DURUM["tum_kurallar"], DURUM["KOK"], DURUM["ATALAR"])
    DURUM["kok_kural"] = [k for k in DURUM["kok_kural_tum"] if ozne_banner_jetonlu_mu(k[2])]
    DURUM["inline_stil"] = BANNER_OZ.get("style", "")
    uyari(DURUM["KOK"]["oz"].get("id") == "skanBanner" and "skan-banner" in DURUM["KOK"]["sinif"],
          "banner ROOT elemani ayristirildi (id=%r, sinif=%s)"
          % (DURUM["KOK"]["oz"].get("id"), sorted(DURUM["KOK"]["sinif"])))
    m_main = re.search(r"<main>(.*?)</main>", index_html, re.S)
    DURUM["m_main"] = m_main
    uyari(m_main is not None and 'id="skanBanner"' in m_main.group(1),
          "banner <main> icinde (ana sayfa vitrininin ustunde)")
    b_kurallar = [(s, d) for (s, d, _m) in DURUM["tum_kurallar"] if BANNER_JETON.search(s)]
    DURUM["b_kurallar"] = b_kurallar
    uyari(len(b_kurallar) >= 6,
          "banner ailesi CSS kurallari bulundu (%d kural)" % len(b_kurallar))
    uyari(any(".skan-banner" in s for s, _ in b_kurallar),
          "kurallar arasinda .skan-banner secicisi var (blok tumden silinmemis)")
    uyari(any(a["etiket"] == "main" for a in DURUM["ATALAR"]),
          "banner'in ata zinciri cikarilabildi")
    uyari(not COZULEMEYEN_SECICI,
          "banner ailesine deyen TUM seciciler ayristirilabildi (cozulemeyen: %s)"
          % (sorted(set(COZULEMEYEN_SECICI)) or "-"))
    uyari(len(DURUM["kok_kural"]) >= 2,
          "banner ROOT'una uygulanan JETONLU kural bulundu (%d)" % len(DURUM["kok_kural"]))


def _u_gorunurluk():
    kk, inline = DURUM["kok_kural"], DURUM["inline_stil"]
    etkin_taban = etkin_stil(kk, inline, durumu_dahil_et=False, medyayi_dahil_et=False)
    etkin_kosulsuz = etkin_stil(kk, inline, durumu_dahil_et=False)
    etkin_durum = etkin_stil(kk, inline, durumu_dahil_et=True)
    taban_sorun = gorunurluk_sorunlari(etkin_taban, mod="taban")
    uyari(not taban_sorun,
          "banner ROOT'u KOSULSUZ (medyasiz) yukseklik/genislik + beyaz liste tabanini "
          "sagliyor (sorun: %s)" % (taban_sorun or "-"))
    sorunlar = gorunurluk_sorunlari(etkin_kosulsuz, mod="kosulsuz")
    uyari(not sorunlar,
          "banner ROOT'u DINLENME halinde gorunurluk olcumunu geciyor (sorun: %s)"
          % (sorunlar or "-"))
    durum_sorun = gorunurluk_sorunlari(etkin_durum, mod="durum")
    uyari(not durum_sorun,
          "durum secicileri (:hover/:focus/:active) banner'i OLDURMUYOR (sorun: %s)"
          % (durum_sorun or "-"))
    uyari(not re.search(r"<a id=\"skanBanner\"[^>]*\shidden(?:\s|>|=)", banner_ac),
          "banner HTML'inde `hidden` ozniteligi YOK")
    uyari(BANNER_OZ.get("aria-hidden") != "true", 'banner HTML\'inde aria-hidden="true" YOK')


METIN_SINIFLARI = {"skan-banner-text", "jen-banner-text"}


def metin_kutusu_oznesi_mi(tek_secici):
    bl = _bilesikler(tek_secici.strip())
    if not bl:
        return False
    d = bilesik_ayristir(bl[-1])
    if d is None:
        return bool(re.search(r"\.(?:skan|jen)-banner-text\b", bl[-1]))
    if d["psel"]:
        return False
    return bool(d["sinif"] & METIN_SINIFLARI)


def _u_metin_kutusu():
    metin_olduren = []
    for secici, govde, medya in DURUM["tum_kurallar"]:
        if medya:
            continue
        if not re.search(r"display\s*:\s*none", govde, re.I):
            continue
        for tek in _derinlik_bol(secici, ","):
            if metin_kutusu_oznesi_mi(tek):
                metin_olduren.append(tek.strip())
    uyari(not metin_olduren,
          "banner metin sarmalayicisi KOSULSUZ gizlenmemis (bulunan: %s)" % (metin_olduren or "-"))


def _u_sari():
    tum_kurallar, VAR_TANIM = DURUM["tum_kurallar"], DURUM["VAR_TANIM"]
    sari_kurallar = [(s, d) for (s, d, _m) in tum_kurallar if SARI_JETON.search(s)]
    bulgu = sari_bulgular(banner_html)
    cozulemeyen_var = []
    kok_kural_genis = kok_kurallari(tum_kurallar, DURUM["KOK"], DURUM["ATALAR"],
                                    belirsiz=True, cozulemeyeni_kaydet=False)
    etkin_genis = etkin_stil(kok_kural_genis, DURUM["inline_stil"], durumu_dahil_et=True)
    for ad, (deger, sec) in sorted(etkin_genis.items()):
        cozulmus, eksik = var_coz(deger, VAR_TANIM)
        cozulemeyen_var.extend(eksik)
        for b in sari_bulgular(cozulmus):
            bulgu.append("KASKAD %s{%s:%s} -> %s" % (sec, ad, cozulmus.strip()[:40], b))
    for sec, bildirimler in sari_kurallar:
        cozulmus, eksik = var_coz(bildirimler, VAR_TANIM)
        cozulemeyen_var.extend(eksik)
        for b in sari_bulgular(cozulmus):
            bulgu.append("%s -> %s" % (sec, b))
    uyari(not cozulemeyen_var,
          "SKAN banner ailesindeki HER var(--ad) cozulebildi (cozulemeyen: %s)"
          % (sorted(set(cozulemeyen_var)) or "-"))
    b64_kaynak = []
    for etiket, metin in ([("banner HTML", banner_html)]
                          + [("kural " + s, d) for s, d in sari_kurallar]
                          + [("KASKAD " + a, v[0]) for a, v in sorted(etkin_genis.items())]):
        if re.search(r"url\(\s*['\"]?\s*data:[^)]*;\s*base64", metin, re.I):
            b64_kaynak.append(etiket)
    uyari(not b64_kaynak,
          "SKAN banner ailesinde base64 data-URI YOK (bulunan: %s)" % (b64_kaynak or "-"))
    uyari(not bulgu,
          "banner HTML + SKAN banner ailesi CSS'inde SARI token YOK (bulunan: %s)"
          % (sorted(set(bulgu)) or "-"))


def _u_marka_dili():
    uyari(not yasak_ifadeler(banner_html),
          "banner metninde yasak ifade YOK (bulunan: %s)" % (yasak_ifadeler(banner_html) or "-"))
    m_main = DURUM.get("m_main")
    main_govde = m_main.group(1) if m_main else ""
    main_gorunur = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ",
                          main_govde, flags=re.S)
    main_yasak = yasak_ifadeler(main_gorunur)
    uyari(not main_yasak,
          "ana sayfanin GORUNUR <main> govdesinde yasak ifade YOK (bulunan: %s)"
          % (main_yasak or "-"))


def _u_js_sozlesmesi():
    """JS KAYNAK SOZLESMESI — banner id'lerine yalniz renderGrid toggle blogu dokunsun."""
    SCRIPT_ARALIK = [(m.start(1), m.end(1)) for m in
                     re.finditer(r"<script[^>]*>(.*?)</script>", index_html, re.S | re.I)]

    def script_icinde(ofset):
        return any(a <= ofset < b for a, b in SCRIPT_ARALIK)

    def _dengeli_kapa(metin, acilis_ofseti, ac="(", kapa=")"):
        derinlik, k = 1, acilis_ofseti + 1
        while k < len(metin) and derinlik:
            if metin[k] == ac:
                derinlik += 1
            elif metin[k] == kapa:
                derinlik -= 1
            k += 1
        return None if derinlik else k

    # ⚠️ Dizinin KAC elemanli oldugu OLCULMEZ (ucuncu bir seri banner'i eklenebilmeli):
    # sadece "skanBanner iceren bir dizi .forEach ediliyor mu" aranir.
    m_tog = re.search(r'\[\s*"[^\]]*skanBanner[^\]]*"\s*\]\s*\.\s*forEach\s*\(', index_html)
    uyari(m_tog is not None,
          'renderGrid icinde skanBanner iceren toggle dizisi (.forEach) bulundu')
    tog_bas = tog_son = -1
    if m_tog:
        tog_bas = m_tog.start()
        tog_son = _dengeli_kapa(index_html, m_tog.end() - 1) or m_tog.end()
        toggle_src = index_html[tog_bas:tog_son]
        rg_ofset = index_html.find(rendergrid_src) if rendergrid_src else -1
        uyari(rg_ofset != -1 and rg_ofset <= tog_bas < rg_ofset + len(rendergrid_src),
              "toggle blogu renderGrid GOVDESININ icinde")
        stil_ozellikleri = sorted(set(re.findall(r"\.style\s*\.\s*([-\w]+)\s*=", toggle_src))
                                  | set(re.findall(r"\.style\s*\[\s*['\"]([-\w]+)['\"]\s*\]\s*=",
                                                   toggle_src)))
        uyari(stil_ozellikleri == ["display"],
              "toggle blogu YALNIZ .style.display yaziyor (bulunan: %s)" % (stil_ozellikleri or "-"))
        uyari(not re.search(r"\.style\s*\.\s*cssText|setAttribute\s*\(\s*['\"]style|"
                            r"classList|\.remove\s*\(\s*\)|Object\.assign", toggle_src),
              "toggle blogunda toplu-stil kacagi YOK")
        uyari(not sari_bulgular(toggle_src),
              "toggle blogunda SARI token YOK (bulunan: %s)" % (sari_bulgular(toggle_src) or "-"))
    sozlesme_disi = []
    satirlar = index_html.splitlines()
    for m in re.finditer(r"(?:skan|jen)Banner", index_html):
        if not script_icinde(m.start()):
            continue
        if tog_bas <= m.start() < tog_son:
            continue
        satir_no = index_html.count("\n", 0, m.start()) + 1
        satir = satirlar[satir_no - 1].strip()
        sozlesme_disi.append("satir %d: %s" % (satir_no, satir[:110]))
    uyari(not sozlesme_disi,
          "index.html JS'inde banner id'sine toggle blogu DISINDAN dokunan satir YOK "
          "(bulunan: %s)" % (sozlesme_disi or "-"))


def _u_liste_paritesi():
    uyari(i_giz is not None and i_giz == b_giz,
          "index.html GIZLI_KATEGORILER == tools/build.py NAV_GIZLI (%s / %s)" % (i_giz, b_giz))
    uyari(s_fonk is not None and s_fonk == list(build.FONKSIYONEL_KATEGORILER),
          "iki FONKSIYONEL_KATEGORILER kopyasi BIREBIR ayni")


def _u_urun_sayfasi():
    html = build.render_product(kurt, katalog)
    DURUM["html"] = html
    for isaret in KOMPAKT:
        uyari(html.count(isaret) == 1, "kurt sayfasinda kompakt kart isareti (1 kez): %s" % isaret)
    for isaret in FALLBACK:
        uyari(html.count(isaret) == 0, "kurt sayfasinda eski genis-buton isareti YOK: %s" % isaret)
    SENTETIK = {
        "id": "skan-art-fonksiyonel-nobetci-fiksturu",
        "kategori": KATEGORI,
        "marka": [],
        "baslik": "Nöbetçi fikstürü — şemasız Skan Art ürünü",
        "aciklama": "Yalnız kabul testinde yaşar. Yaklaşık dış ölçüler: 100 × 100 × 100 mm.",
        "fiyat": "900 TL",
        "gorseller": ["https://media.pruvo3d.com/urunler/nobetci-fikstur-1.jpg"],
    }
    html_f = build.render_product(SENTETIK, [SENTETIK])
    for isaret in KOMPAKT:
        uyari(html_f.count(isaret) == 1, "sentetik sayfada kompakt isaret VAR: %s" % isaret)
    for isaret in FALLBACK:
        uyari(html_f.count(isaret) == 0, "sentetik sayfada genis-buton isareti YOK: %s" % isaret)
    uyari("var KART_SECIM = true;" in html_f,
          "sentetik sayfada KART_SECIM bayragi ACIK (malzeme karti secimi kablolu)")
    if u_sayfa:
        uyari('<section class="related">' in u_sayfa,
              "URETILEN dosyada ilgili urunler bolumu VAR")


def _u_ilgili_filament_url():
    html = DURUM.get("html") or build.render_product(kurt, katalog)
    uyari('<section class="related">' in html,
          'kurt sayfasinda <section class="related"> VAR')
    rel_adet = html.count('class="rel-card"')
    uyari(rel_adet >= build.REL_EN_AZ,
          "kurt sayfasinda rel-card sayisi >= %d (bulunan: %d)" % (build.REL_EN_AZ, rel_adet))
    uyari(build.AKRABA_KATEGORI.get(KATEGORI) == "Dekorasyon",
          'build.AKRABA_KATEGORI["%s"] == "Dekorasyon"' % KATEGORI)
    with open(FILAMENTLER, encoding="utf-8") as f:
        filref = json.load(f)
    uyari(KATEGORI in filref.get("kategoriTavsiye", {}),
          'filamentler.json kategoriTavsiye["%s"] tanimli' % KATEGORI)
    uyari(bool(filament_ortak.tavsiyeler(KATEGORI)),
          "filament_ortak.tavsiyeler(%r) bos DEGIL" % KATEGORI)
    uyari("fil-cip tavsiyeli" in html, 'urun sayfasinda "Tavsiyemiz" rozetli filament cipi var')
    uyari("?kategori=" + KATEGORI not in html,
          "sayfada HAM BOSLUKLU '?kategori=%s' URL'i YOK" % KATEGORI)
    uyari("?kategori=Skan%20Art" in html, "yuzde-kodlu '?kategori=Skan%20Art' URL'i VAR")
    ld_bloklar = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    bread = None
    for blok in ld_bloklar:
        obj = json.loads(blok)
        if obj.get("@type") == "BreadcrumbList":
            bread = obj
    uyari(bread is not None, "JSON-LD BreadcrumbList ayristirilabildi")
    if bread:
        item = [x for x in bread["itemListElement"] if x.get("position") == 2][0]
        uyari(" " not in item["item"], "BreadcrumbList item URL'inde ham bosluk YOK")
        uyari(item.get("name") == KATEGORI, 'BreadcrumbList adi "%s"' % KATEGORI)


def _u_feed():
    feed_xml, feed_adet = build.render_merchant_feed([kurt])
    uyari(feed_adet == 1, "kurt urunu feed'e giriyor (fiyatli + gorselli + parametrik degil)")
    uyari("<g:google_product_category>Home &amp; Garden &gt; Decor</g:google_product_category>"
          in feed_xml, "feed satirinda g:google_product_category basiliyor")
    uyari("<g:product_type>%s</g:product_type>" % KATEGORI in feed_xml,
          "feed g:product_type == %s" % KATEGORI)


def _u_node_davranis():
    if not NODE_VAR:
        uyari(False, "node yok — renderCats/secenekler.js davranis uyarilari OLCULMEDI")
        return
    IKON = "<EV-IKONU>"
    rendercats_src = js_fonksiyon(index_html, "renderCats", hata=_uyari_hata)
    if rendercats_src:
        b1 = r"""
"use strict";
__CAT__
__GIZ__
var activeCat = "Tümü";
var cips = [];
var document = {
  getElementById: function(){
    return { set innerHTML(v){}, appendChild: function(b){ cips.push(b.__etiket); } };
  },
  createElement: function(){
    var o = { style:{}, className:"", title:"", __etiket:null, setAttribute:function(){} };
    Object.defineProperty(o, "textContent", {
      set: function(v){ o.__etiket = v; }, get: function(){ return o.__etiket; } });
    Object.defineProperty(o, "innerHTML", {
      set: function(v){ o.__etiket = "__IKON__"; }, get: function(){ return ""; } });
    return o;
  }
};
__RENDERCATS__
renderCats();
console.log(JSON.stringify({ cips: cips, cat: CATEGORIES, gizli: GIZLI_KATEGORILER }));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src) \
           .replace("__RENDERCATS__", rendercats_src).replace("__IKON__", IKON)
        s1 = node_kos(b1, "(u) renderCats", bildir=uyari)
        if s1:
            cips = s1["cips"]
            beklenen = [IKON] + s1["cat"]
            uyari(cips == beklenen,
                  "renderCats() cip listesi TAM olarak ev-ikonu + CATEGORIES (fazlalik: %s)"
                  % ([c for c in cips if c not in beklenen] or "-"))
            sizanlar = [g for g in s1["gizli"] if g in cips]
            uyari(not sizanlar, "GIZLI kategoriler nav cipi olarak basilmiyor (sizan: %s)"
                  % (sizanlar or "-"))
    if applyurl_src:
        b2b = r"""
"use strict";
__CAT__
__GIZ__
var activeCat, activeBrand, query;
var searchEl = { value: "" };
var clearEl = { className: "" };
function markaKatla(x){ return x; }
var location = { hash: "", search: "", replace: function(){ throw new Error("beklenmedik yonlendirme"); } };
__APPLYURL__
function dene(qs){
  activeCat = "Tümü"; activeBrand = "Tümü"; query = "";
  location.hash = ""; location.search = qs;
  applyUrlParams();
  return activeCat;
}
console.log(JSON.stringify({
  jen: dene("?kategori=Jenerat%C3%B6r"),
  dekor: dene("?kategori=Dekorasyon"),
  uydurma: dene("?kategori=BoyleBirKategoriYok")
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__APPLYURL__", applyurl_src)
        s2b = node_kos(b2b, "(u) applyUrlParams emsalleri", bildir=uyari)
        if s2b:
            uyari(s2b["jen"] == "Jeneratör", "?kategori=Jeneratör derin linki calisiyor")
            uyari(s2b["dekor"] == "Dekorasyon", "gorunur kategori derin linki calisiyor")
            uyari(s2b["uydurma"] == "Tümü", "tanimsiz kategori derin linki YOK SAYILIYOR")
    if rendergrid_src:
        b4b = r"""
"use strict";
__CAT__
__GIZ__
var EDGE_KATALOG = false;
var edgeListe = [], edgeToplam = 0, edgeDurum = "", edgeSayfa = 1;
var PAGE_SIZE = 24, shown = 24;
var HOME_ORDER = [{id:"a"},{id:"b"}];
var activeCat = "Tümü", activeBrand = "Tümü", query = "";
var kayit = {}, elemanlar = {};
function sahteEleman(id){
  var o = { __id:id, style:{}, className:"", textContent:"", innerHTML:"",
            appendChild:function(){}, setAttribute:function(){}, onclick:null, disabled:false };
  Object.defineProperty(o.style, "display", {
    set: function(v){ kayit[id] = v; }, get: function(){ return kayit[id]; }, configurable:true });
  return o;
}
var document = {
  getElementById: function(id){
    if(!(id in elemanlar)){ elemanlar[id] = sahteEleman(id); }
    return elemanlar[id];
  },
  createElement: function(){ return sahteEleman("__yeni__"); }
};
function filtered(){ return [{id:"a"},{id:"b"}]; }
function kartCiz(){ return sahteEleman("__kart__"); }
function renderEdgeDurum(){}
function edgeYukle(){}
__RENDERGRID__
kayit = {}; elemanlar = {};
activeCat = "Tümü"; query = ""; activeBrand = "Tümü";
renderGrid();
console.log(JSON.stringify({
  jenAna: ("jenBanner" in kayit) ? kayit["jenBanner"] : "__HIC-DOKUNULMADI__"
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__RENDERGRID__", rendergrid_src)
        s4b = node_kos(b4b, "(u) jenBanner emsali", bildir=uyari)
        if s4b:
            uyari(s4b["jenAna"] == "",
                  'emsal bozulmamis: jenBanner ANA gorunumde display === "" (bulunan: %r)'
                  % s4b["jenAna"])
    b3 = r"""
"use strict";
require(__SECENEKLER__);
var S = globalThis.PRUVO_SECENEK;
var urun = { id: "x", kategori: "Skan Art", fiyat: "1.000 TL" };
var satir = { id: "x", malzeme: "PETG", renk: "Siyah", renk_ozel: "", boy_etiket: null, adet: 2 };
var ozet = S.satirOzeti(urun, satir);
console.log(JSON.stringify({
  fonk: S.fonksiyonelMi("Skan Art"),
  fonkDekor: S.fonksiyonelMi("Dekorasyon"),
  fonkYok: S.fonksiyonelMi("BoyleBirKategoriYok"),
  detay: ozet.detay,
  kurus: ozet.kurus
}));
""".replace("__SECENEKLER__", json.dumps(SECENEKLER))
    s3 = node_kos(b3, "(u) secenekler.js", bildir=uyari)
    if s3:
        uyari(s3["fonk"] is True, 'fonksiyonelMi("%s") === true (bulunan: %r)' % (KATEGORI, s3["fonk"]))
        uyari(s3["fonkDekor"] is True, 'fonksiyonelMi("Dekorasyon") === true (emsal bozulmamis)')
        uyari(s3["fonkYok"] is False, "fonksiyonelMi(tanimsiz kategori) === false")
        uyari("Malzeme: PETG (+%30)" in (s3["detay"] or ""),
              "satirOzeti Skan Art satirina malzeme/renk detayini yaziyor (bulunan: %r)" % s3["detay"])
        uyari(s3["kurus"] == 260000,
              "malzeme KATSAYISI uygulaniyor: 2 × (1.000 TL +%%30) = 260000 kurus (bulunan: %r)"
              % s3["kurus"])


for _baslik, _fn in [
    ("(u1) banner ROOT + CSS altyapisi hazirligi", _u_hazirlik),
    ("(u2) gorunurluk motoru + beyaz liste", _u_gorunurluk),
    ("(u3) metin kutusu kontrolu", _u_metin_kutusu),
    ("(u4) SARI taramasi (var() cozumlu, kaskad + %23 + base64)", _u_sari),
    ("(u5) marka/cografya dili", _u_marka_dili),
    ("(u6) JS kaynak sozlesmesi", _u_js_sozlesmesi),
    ("(u7) liste paritesi (tam liste esitligi)", _u_liste_paritesi),
    ("(u8) urun sayfasi kompakt kart + sentetik FONKSIYONEL fiksturu", _u_urun_sayfasi),
    ("(u9) ilgili urunler + filament + URL kodlamasi", _u_ilgili_filament_url),
    ("(u10) merchant feed satiri", _u_feed),
    ("(u11) node davranis emsalleri (renderCats / derin link / fiyat)", _u_node_davranis),
]:
    uyari_bolumu(_baslik, _fn)

bitir()
