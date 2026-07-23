#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKAN ART KABUL TESTI — gizli dekor alt-serisi kategorisi + ana sayfa banner'i.

"Skan Art" (Okan, 23 Tem) = Iskandinav tasarim dilli dekor/heykel alt-serisi. Kategori
davranisi sari seri ("Jeneratör") ile BIREBIR ayni sinif: ana nav'da GIZLI, ana sayfaya
kendi BANNER'iyle girilir, ?kategori= derin linki/arama/urun sayfasi calisir.

Bu dosya o kararin KALICI NOBETCISI. Olctugu maddeler:
  (a) "Skan Art" gizli-kategori listesinin HER IKI kaynaginda (tools/build.py NAV_GIZLI +
      index.html GIZLI_KATEGORILER) ve AYNI sira indeksinde.
  (b) NAV CIPI YOK + DERIN LINK VAR — kaynak-metni degil DAVRANIS olculur: renderCats()
      ve applyUrlParams() index.html'den AYIKLANIP node ile GERCEKTEN kosturulur
      (sahte DOM/location).
  (c) FONKSIYONEL_KATEGORILER'de (tools/build.py + secenekler.js IKISINDE) VE
      secenekler.js'in KENDI davranisi node ile olculur: fonksiyonelMi("Skan Art") true,
      satirOzeti malzeme KATSAYISINI uyguluyor (para etkisi).
  (d) Kompakt kart duzeni UC ayri fiksturle olculur:
      (d1) kurt urununun URETILEN sayfasi (bugunku gercek kayit — konfigur'lu),
      (d2) SENTETIK semasiz/konfigursuz Skan Art urunu — kompakt duzeni SADECE
           FONKSIYONEL_KATEGORILER uyeligi tasir,
      (d3) URETIM HATTI: build.py'nin ANA main() dongusu bir KUM HAVUZUNDA kosturulur ve
           urun/<kurt-id>/index.html'in DISKTE olustugu + sitemap.xml'de kurt URL'inin
           bulundugu olculur. [24 Tem curutme: main() dongusune "gizli kategoriyi atla"
           satiri konunca kurt sayfasi HIC uretilmiyordu (urun/ 9508 -> 9486) ama test
           yesildi; urun/ dizini TAMAMEN silinince de yesildi.]
  (e) Kurt urununun kategorisi "Skan Art", govdesi degismemis (SHA256 capasi) VE
      katalogdaki Skan Art urun SAYISI capali.
  (f) Ana sayfa banner'i — POZITIF GORUNURLUK OLCUMU (yasakli-bildirim listesi DEGIL):
      banner ROOT'una uygulanan efektif CSS kurallari secici eslesmesiyle (etiket + id +
      sinif + OZNITELIK secicisi + :not/:is/:where) toplanir, ozgulluk+kaynak sirasina gore
      cozulur ve asgari gecerli durum dogrulanir (display != none, visibility gorunur,
      opacity >= 0.9, pozitif hesaplanan yukseklik, ekran ici konum, kirpma yok).
      Banner ailesinin renk paleti var(--ad) DOLAYIMI COZULEREK taranir; 8/4/6/3 haneli
      hex + rgb()/hsl() + CSS renk adlari kapsanir, modern renk notasyonu (oklch/lab/lch/
      color()/color-mix) banner ailesinde FAIL-CLOSED YASAK.
      Banner metni marka kurallarina uyar ("3D baski" YOK, sehir adi YOK — CLAUDE.md).
      renderGrid'in goster/gizle KABLOSU node'da GERCEKTEN kosturulur (kaynak-metni kalibi
      degil): ana gorunumde display === "", kategori/arama/marka gorunumunde "none".
      Banner HEDEFI de davranisla olculur: banner'in GERCEK href'i applyUrlParams'a
      verilir ve activeCat "Skan Art" oluyor mu diye bakilir ("+" kodlamasi de gecerlidir).
      [24 Tem curutme — kapatilan KACAKLAR: ':root{--skan-acc:#f5c518}' + 'background:
      var(--skan-acc)' · '#ffd400ff' / '#ffd400CC' / 'oklch(0.86 0.17 95)' ·
      'a[id="skanBanner"]{display:none}' · 'min-height:0;height:0;overflow:hidden' ·
      'position:absolute;left:-9999px' · toggle blogu dururken hemen ardina
      'getElementById("skanBanner").style.display="none"' eklemek.
      Kapatilan YANLIS-KIRMIZILAR: '@media(max-width:400px){.skan-banner-ust{display:none}}'
      (cocuk ETIKET gizlemek mesru — olduren-bildirim taramasi artik YALNIZ ROOT'a bakar) ·
      href="/?kategori=Skan+Art" (davranissal olarak AYNI).]
  (g) Merchant feed taksonomisi: GOOGLE_PRODUCT_CATEGORY'de "Skan Art" var.
  (h) Filament tavsiyesi: filamentler.json kategoriTavsiye'de "Skan Art" var ve uretilen
      sayfada "Tavsiyemiz" rozeti duruyor.
  (i) Iki kelimeli kategori adi URL'e YUZDE-KODLU giriyor (breadcrumb + JSON-LD).
  (j) ILGILI URUNLER bolumu AYAKTA: ince alt-seride build.AKRABA_KATEGORI yedegi devrede.
  (k) Skan Art kategorisindeki HER urun `konfigur` alani TASIR.
      NEDEN: shop odeme Worker'i secenekler.js'i BUNDLE'a gommuyor ve deploy.yml onu
      YAYINLAMIYOR -> canli worker "Skan Art"i bilmez, konfigursuz bir Skan Art urununde
      malzeme/renk katsayisi SESSIZCE DUSER (olculdu: ASA + ozel renk 27.600 yerine
      15.000 kurus). Worker bundle drift'i kapanana dek bu madde fail-closed emniyet.

Ag YOK, repo dosyasina YAZMAZ (d3 kum havuzu gecici dizinde), build.py'den ONCE kosabilir.
NODE GEREKIR (davranis bolumleri) — CI'da setup-node kurulu ve node yoksa test FAIL-CLOSED
kirmizi yanar. Yerelde node yoksa acik uyariyla atlamak icin: SKAN_ART_NODE_ATLA=1.
Kullanim:  python3 tools/test-skan-art.py     (0 = gecti, 1 = kirmizi)
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build  # noqa: E402
import filament_ortak  # noqa: E402

KATEGORI = "Skan Art"
PID = "kurt-heykeli-serit-dekoratif-figur"
# (e) capasi: kurt kaydinin KATEGORI DISI govdesinin SHA256'si (json, sort_keys, ayirici ",:").
# 23 Tem, kategori tasinmasi aninda olculdu. Bu capa bilerek degistirilecekse (or. fiyat
# guncellenirse) yeni deger duzelt.py cikisiyla birlikte BURAYA yazilir — sessiz oynama olmaz.
KURT_GOVDE_SHA256 = "5a77966f32e373f52504c1cbfb587de21c03910d1791fd8d7a9d408e5b6b3f89"
KURT_ALANLAR = {"aciklama", "baslik", "fiyat", "gorseller", "id", "kategori", "konfigur", "marka"}
# (e) KAPSAM capasi: katalogda kac urun "Skan Art"ta. Yeni Skan Art urunu eklenince BILEREK
# guncellenir; toptan/kazara kategori tasinmasi (olculen curutme: 168 Dekorasyon urununun
# hepsi birden) bu sayiyi bozar ve kapi kirmizi yanar.
SKAN_ART_URUN_SAYISI = 1

INDEX = os.path.join(ROOT, "index.html")
SECENEKLER = os.path.join(ROOT, "secenekler.js")
FILAMENTLER = os.path.join(TOOLS, "filamentler.json")
URUNLER = os.path.join(ROOT, "urunler.json")

HATALAR = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)


def bitir():
    print("=" * 70)
    if HATALAR:
        print("SONUC: %d KIRMIZI ❌" % len(HATALAR))
        for h in HATALAR:
            print("  - " + h)
        sys.exit(1)
    print("SONUC: GECTI ✅ (Skan Art kategorisi + banner + kurt urunu kabul kriterleri saglandi)")
    sys.exit(0)


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def js_liste(metin, desen, etiket):
    """JS/Python kaynagindaki tek satirlik dizi literalini JSON olarak ayristir."""
    m = re.search(desen, metin, re.M)
    if not m:
        HATALAR.append("%s bulunamadi (yapi degisti mi?)" % etiket)
        return None
    try:
        return json.loads("[" + m.group(1) + "]")
    except json.JSONDecodeError as e:
        HATALAR.append("%s ayristirilamadi: %s" % (etiket, e))
        return None


def js_bildirim(metin, desen, etiket):
    """`var X = ...;` bildiriminin TAM kaynak satirini dondur (node harness'ine gomulur)."""
    m = re.search(desen, metin, re.M)
    if not m:
        HATALAR.append("%s bildirimi bulunamadi (yapi degisti mi?)" % etiket)
        return ""
    return m.group(0)


def js_fonksiyon(metin, ad):
    """`function <ad>(...){...}` govdesini SUSLU PARANTEZ SAYARAK ayikla (regex degil:
    ic blok/nesne literali fonksiyonu erken kesmesin)."""
    m = re.search(r"function\s+%s\s*\(" % re.escape(ad), metin)
    if not m:
        HATALAR.append("function %s bulunamadi (yapi degisti mi?)" % ad)
        return ""
    i = metin.find("{", m.end())
    if i == -1:
        HATALAR.append("function %s govdesi acilmiyor" % ad)
        return ""
    derinlik, k = 1, i + 1
    while k < len(metin) and derinlik:
        if metin[k] == "{":
            derinlik += 1
        elif metin[k] == "}":
            derinlik -= 1
        k += 1
    if derinlik:
        HATALAR.append("function %s govdesi kapanmiyor" % ad)
        return ""
    return metin[m.start():k]


# ================================================================== CSS ALTYAPISI
def css_bloklari(html_metin):
    """index.html'deki TUM <style> bloklarinin govdesini birlestir."""
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html_metin, re.S))


def css_kurallari(css):
    """(secici, bildirimler, medya) uclusu. @media/@supports gibi sarmalayicilarin ICI de
    duz listeye acilir -> kural dosyanin NERESINDE olursa olsun taranir (pencere YOK).
    `medya` = ic ice @-kosullarinin listesi (bos liste = kosulsuz kural)."""
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
    """Parantez/koseli-parantez/tirnak derinligi 0 iken `ayirici`den bol."""
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
    """`a:b;c:d` -> [(ozellik, deger, onemli)] (sira korunur, kucuk harf ozellik adi)."""
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
COZULEMEYEN_SECICI = []          # ayristirilamayan AMA banner ailesine deyen seciciler

# Durum sahte-siniflari: eslesme KOSULLU ama fail-closed EŞLEŞMIŞ sayilir
# (`#skanBanner:hover{display:none}` banner'i pratikte oldurur).
DURUM_PCLS = {"hover", "focus", "focus-visible", "focus-within", "active", "visited",
              "link", "any-link", "target", "lang", "dir"}
# Bu sahte-siniflar banner ROOT'una (bir <a> elemani) HICBIR ZAMAN uymaz.
UYMAZ_PCLS = {"root", "before", "after", "disabled", "checked", "required", "invalid", "valid"}
LISTE_PCLS = {"is", "where", "matches", "any", "-webkit-any", "-moz-any"}
SAHTE_ELEMAN = {"before", "after", "first-line", "first-letter", "marker", "backdrop",
                "selection", "placeholder", "file-selector-button"}


def _bilesikler(sec):
    """Seciciyi kombinatorlerden bolup TUM bilesenleri dondurur (sonuncusu = SUBJECT)."""
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
    """Tek bilesigi (kombinatorsuz parca) yapiya cevir; ayristirilamazsa None."""
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
    """`[href^="/?kategori"]` gibi oznitelik secicisini kok elemaniyla esle."""
    m = re.match(r'^\s*([-\w]+)\s*(?:([~|^$*]?=)\s*("([^"]*)"|\'([^\']*)\'|[^\s\]]+)'
                 r'\s*([iIsS])?\s*)?$', ifade)
    if not m:
        return None            # ayristirilamadi -> arayan fail-closed karar verir
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


def bilesik_esler(bl, kok):
    """Tek bilesik banner ROOT'una uyuyor mu? True/False/None(=cozulemedi)."""
    d = bilesik_ayristir(bl)
    if d is None:
        return None
    if d["psel"]:
        return False           # ::before/::after AYRI bir kutu — ROOT'u oldurmez
    if d["etiket"] and d["etiket"] != kok["etiket"]:
        return False
    if d["id"] and d["id"] != kok["oz"].get("id"):
        return False
    if not d["sinif"] <= kok["sinif"]:
        return False
    for ifade in d["oz"]:
        r = _oz_esler(ifade, kok)
        if r is None:
            return None
        if not r:
            return False
    for ad, arg in d["pcls"]:
        if ad in DURUM_PCLS:
            continue           # fail-closed: durum sahte-sinifi ESLESMIS sayilir
        if ad in UYMAZ_PCLS:
            return False
        if ad == "not":
            if arg is None:
                return None
            ic = [secici_esler(p, kok) for p in _derinlik_bol(arg, ",")]
            if any(x is None for x in ic):
                return None
            if any(ic):
                return False
            continue
        if ad in LISTE_PCLS:
            if arg is None:
                return None
            ic = [secici_esler(p, kok) for p in _derinlik_bol(arg, ",")]
            if any(x is None for x in ic):
                return None
            if not any(ic):
                return False
            continue
        return None            # :nth-child vb. -> cozulemedi (fail-closed karar arayanda)
    return True


def secici_esler(secici, kok):
    """Virgulsuz TEK secici: SUBJECT (son) bilesigi ROOT'a uyuyor mu?"""
    bl = _bilesikler(secici.strip())
    if not bl:
        return False
    return bilesik_esler(bl[-1], kok)


def ozgulluk(secici):
    """(id, sinif+oz+pcls, etiket+psel) — kabaca CSS ozgullugu."""
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


def kok_kurallari(kurallar, kok):
    """Banner ROOT'una GERCEKTEN uygulanan kurallar: [(sira, ozgulluk, secici, govde)].
    Ayristirilamayan AMA banner ailesine deyen secici -> COZULEMEYEN_SECICI (fail-closed).

    ⚠️ DURUST SINIR: bu motor yalniz ROOT elemanini modeller, ATA zincirini modellemez.
    Bu yuzden COK BILESENLI (`.onay-kutu a` gibi) bir secici ancak banner jetonu tasiyorsa
    ROOT'a uygulanmis sayilir; jetonsuz torun secicileri ATLANIR — yoksa `.onay-kutu a`
    gibi bambaska bir bilesenin kurali banner'a sahte-kirmizi yazardi. Tek bilesenli
    seciciler (`a`, `*`, `.skan-banner`, `a[id="skanBanner"]`) her zaman degerlendirilir."""
    out = []
    for sira, (secici, govde, _medya) in enumerate(kurallar):
        for tek in _derinlik_bol(secici, ","):
            tek = tek.strip()
            if not tek:
                continue
            if len(_bilesikler(tek)) > 1 and not BANNER_JETON.search(tek):
                continue
            r = secici_esler(tek, kok)
            if r is None:
                if BANNER_JETON.search(tek) or "skanBanner" in tek:
                    COZULEMEYEN_SECICI.append(tek)
                continue
            if r:
                out.append((sira, ozgulluk(tek), tek, govde))
    return out


def etkin_stil(kok_kural_listesi, inline_govde=""):
    """Kaskad: (onemli, ozgulluk, sira) en buyuk kazanir. -> {ozellik: (deger, secici)}"""
    aday = {}
    for sira, spec, secici, govde in kok_kural_listesi:
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
    """TUM kurallardaki `--ad: deger` tanimlarini topla (son tanim kazanir)."""
    tanim = {}
    for secici, govde, _medya in kurallar:
        for ad, deger, _onemli in bildirimleri_ayristir(govde):
            if ad.startswith("--"):
                tanim[ad] = deger
    return tanim


def var_coz(metin, tanimlar, derinlik=0):
    """var(--ad[, yedek]) dolayimini (ic ice dahil) coz. -> (cozulmus, cozulemeyenler)"""
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
# Sari/altin ailesinden CSS renk ADLARI. Bu liste KURATORLU: uyelik = sari sayilir
# (pastel uyeler lemonchiffon/papayawhip doygunluk esigine takiliyordu — 24 Tem kacagi).
SARI_ADLAR = {
    "yellow", "gold", "goldenrod", "darkgoldenrod", "palegoldenrod",
    "khaki", "darkkhaki", "lightyellow", "lemonchiffon", "cornsilk",
    "moccasin", "papayawhip", "blanchedalmond", "navajowhite", "wheat",
    "greenyellow", "yellowgreen",
}
SARI_KELIME = re.compile(r"yellow|gold(?:en)?|amber|sar[ıi]\b", re.I)
# 8/4 haneli (alfali) hex de yakalanir; alternatifler EN UZUNDAN siralidir, alfa ATILIR.
HEX = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b")
RGB_FN = re.compile(r"\brgba?\(\s*([\d.]+)(%?)[\s,/]+([\d.]+)(%?)[\s,/]+([\d.]+)(%?)", re.I)
HSL_FN = re.compile(r"\bhsla?\(\s*([\d.]+)(?:deg)?[\s,/]+([\d.]+)%[\s,/]+([\d.]+)%", re.I)
AD_FN = re.compile(r"\b(%s)\b" % "|".join(sorted(SARI_ADLAR, key=len, reverse=True)), re.I)
# Cozemedigimiz modern renk notasyonlari: banner ailesinde FAIL-CLOSED YASAK
# (24 Tem kacagi: 'oklch(0.86 0.17 95)' saf sari, hicbir tarayiciya takilmiyordu).
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
    """Sari kusagi. IKI dal:
       1) doygun sari  : hue 40-70 + doygunluk >= .35 + koyu degil
       2) PASTEL sari  : hue 40-70 + parlaklik yuksek (max >= 200) — doygunluk esigi
          krem/pastel sarilari (or. #fff8c0) kaciriyordu (24 Tem)."""
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
    """Metin parcasindaki SARI izleri: hex(8/6/4/3) + rgb()/rgba() + hsl()/hsla() +
    CSS renk adi + sari kelimesi + COZULEMEYEN modern renk notasyonu.
    YORUMLAR once elenir: CSS/HTML yorumu boyanmaz — "SARI KESINLIKLE YOK" gibi bir
    KURAL notunun testi kirmiziya cekmesi sahte pozitif olurdu."""
    parca = YORUM.sub(" ", parca)
    bulgu = []
    for m in HEX.finditer(parca):
        ham = m.group(1)
        if len(ham) in (3, 4):
            ham = "".join(c * 2 for c in ham[:3])
        else:
            ham = ham[:6]                       # 8 haneli -> alfa atilir
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
        bulgu.append(m.group(1))                # liste KURATORLU -> uyelik = sari
    for m in SARI_KELIME.finditer(parca):
        bulgu.append(m.group(0))
    for m in MODERN_RENK.finditer(parca):
        bulgu.append("COZULEMEYEN renk notasyonu: %s() — banner ailesinde YASAK" % m.group(1))
    # ayni bulgu birden cok tarayicidan gelebilir (gold hem ad hem kelime) -> tekille
    return sorted(set(bulgu))


# ---------------------------------------------------------------- gorunurluk olcumu
def _uzunluk_px(deger):
    """CSS uzunlugunu kabaca px'e cevir; cozulemezse None. (vh/vw 800x1280 varsayimi.)"""
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


def gorunurluk_sorunlari(etkin):
    """POZITIF olcum: banner ROOT'unun ASGARI gecerli gorunur durumu saglaniyor mu?"""
    s = []

    def dg(ad):
        return etkin[ad][0] if ad in etkin else None

    def kaynak(ad):
        return etkin[ad][1] if ad in etkin else "-"

    if (dg("display") or "").strip().lower() == "none":
        s.append("display:none  [%s]" % kaynak("display"))
    if (dg("visibility") or "").strip().lower() in ("hidden", "collapse"):
        s.append("visibility:%s  [%s]" % (dg("visibility"), kaynak("visibility")))
    if (dg("pointer-events") or "").strip().lower() == "none":
        s.append("pointer-events:none  [%s]" % kaynak("pointer-events"))
    if (dg("content-visibility") or "").strip().lower() == "hidden":
        s.append("content-visibility:hidden  [%s]" % kaynak("content-visibility"))

    op = dg("opacity")
    if op is not None:
        ham = op.strip()
        try:
            deger = float(ham[:-1]) / 100.0 if ham.endswith("%") else float(ham)
        except ValueError:
            deger = None
        if deger is None:
            s.append("opacity cozulemedi: %r  [%s]" % (op, kaynak("opacity")))
        elif deger < 0.9:
            s.append("opacity %s < 0.9  [%s]" % (ham, kaynak("opacity")))

    mh = _uzunluk_px(dg("min-height"))
    hh = _uzunluk_px(dg("height"))
    mx = _uzunluk_px(dg("max-height"))
    if mx is not None and mx <= 0:
        s.append("max-height:%s (kutu sifirlanir)  [%s]" % (dg("max-height"), kaynak("max-height")))
    if (mh is None or mh <= 0) and (hh is None or hh <= 0):
        s.append("banner ROOT'unda POZITIF hesaplanan yukseklik YOK "
                 "(min-height=%r, height=%r)" % (dg("min-height"), dg("height")))

    pos = (dg("position") or "").strip().lower()
    if pos in ("absolute", "fixed"):
        for yon in ("left", "top", "right", "bottom"):
            pv = _uzunluk_px(dg(yon))
            if pv is not None and pv <= -1000:
                s.append("%s:%s + position:%s -> ekran disi  [%s]"
                         % (yon, dg(yon), pos, kaynak(yon)))

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


def node_kos(kaynak, etiket):
    """Gecici .js dosyasi yazip node ile kosar; stdout'un SON satirini JSON ayristirir."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(kaynak)
        yol = f.name
    try:
        r = subprocess.run(["node", yol], capture_output=True, text=True)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        kontrol(False, "%s node ile kosuyor (stderr: %s)"
                % (etiket, (r.stderr.strip()[:300] or "-")))
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        kontrol(False, "%s node ciktisi JSON degil: %r" % (etiket, r.stdout[:200]))
        return None


# ================================================================== okumalar
index_html = oku(INDEX)
secenekler_js = oku(SECENEKLER)

print("SKAN ART KABUL TESTI")
print("=" * 70)

# ---------------------------------------------------------------- (a) gizli liste paritesi
print("(a) gizli kategori listesi — iki kaynak, ayni sira")
i_giz = js_liste(index_html, r"var\s+GIZLI_KATEGORILER\s*=\s*\[(.*?)\]", "index.html GIZLI_KATEGORILER")
b_giz = list(build.NAV_GIZLI)
kontrol(i_giz is not None and i_giz == b_giz,
        "index.html GIZLI_KATEGORILER == tools/build.py NAV_GIZLI (%s / %s)" % (i_giz, b_giz))
kontrol(KATEGORI in b_giz, '"%s" tools/build.py NAV_GIZLI icinde' % KATEGORI)
kontrol(i_giz is not None and KATEGORI in i_giz, '"%s" index.html GIZLI_KATEGORILER icinde' % KATEGORI)
if i_giz and KATEGORI in i_giz and KATEGORI in b_giz:
    kontrol(i_giz.index(KATEGORI) == b_giz.index(KATEGORI),
            "sira indeksi iki kaynakta ayni (%d)" % b_giz.index(KATEGORI))

# ---------------------------------------------------------------- (b) liste uyeligi (on sart)
print("(b) nav cipi YOK, derin link VAR — once liste uyeligi")
i_cat = js_liste(index_html, r"var\s+CATEGORIES\s*=\s*\[(.*?)\]", "index.html CATEGORIES")
kontrol(i_cat is not None and KATEGORI not in i_cat,
        '"%s" GORUNUR index.html CATEGORIES listesinde DEGIL' % KATEGORI)
kontrol(KATEGORI not in build.CATEGORIES,
        '"%s" GORUNUR tools/build.py CATEGORIES listesinde DEGIL' % KATEGORI)

# ---------------------------------------------------------------- (c) FONKSIYONEL parite
print("(c) FONKSIYONEL_KATEGORILER — build.py + secenekler.js")
s_fonk = js_liste(secenekler_js, r"var\s+FONKSIYONEL_KATEGORILER\s*=\s*\[(.*?)\]",
                  "secenekler.js FONKSIYONEL_KATEGORILER")
b_fonk = list(build.FONKSIYONEL_KATEGORILER)
kontrol(KATEGORI in b_fonk, '"%s" tools/build.py FONKSIYONEL_KATEGORILER icinde' % KATEGORI)
kontrol(s_fonk is not None and KATEGORI in s_fonk,
        '"%s" secenekler.js FONKSIYONEL_KATEGORILER icinde' % KATEGORI)
kontrol(s_fonk is not None and s_fonk == b_fonk,
        "iki FONKSIYONEL_KATEGORILER kopyasi BIREBIR ayni (bu paritenin baska nobetcisi yok)")

# ---------------------------------------------------------------- (e) urun kaydi
print("(e) kurt urunu — kategori tasindi, govde degismedi, KAPSAM tek urun")
with open(URUNLER, encoding="utf-8") as f:
    katalog = json.load(f)
kurtlar = [u for u in katalog if u.get("id") == PID]
kontrol(len(kurtlar) == 1, "%s katalogda TEK kayit" % PID)
if not kurtlar:
    print("SONUC: KALDI ❌ (urun bulunamadi, kalan maddeler olculemedi)")
    sys.exit(1)
kurt = kurtlar[0]
kontrol(kurt.get("kategori") == KATEGORI, 'kategori == "%s" (bulunan: %r)' % (KATEGORI, kurt.get("kategori")))
kontrol(set(kurt.keys()) == KURT_ALANLAR,
        "alan kumesi degismemis (%s)" % sorted(kurt.keys()))
govde = {k: v for k, v in kurt.items() if k != "kategori"}
ham = json.dumps(govde, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
sha = hashlib.sha256(ham.encode("utf-8")).hexdigest()
kontrol(sha == KURT_GOVDE_SHA256,
        "kategori disi govde SHA256 capasi tutuyor (%s)" % sha[:16])
skan_urunler = [u for u in katalog if u.get("kategori") == KATEGORI]
kontrol(len(skan_urunler) == SKAN_ART_URUN_SAYISI,
        "katalogda %s urun sayisi capasi == %d (bulunan: %d) — toptan kategori tasimasi kapali"
        % (KATEGORI, SKAN_ART_URUN_SAYISI, len(skan_urunler)))

# ---------------------------------------------------------------- (k) konfigur ZORUNLU
# NEDEN (tek satir): shop odeme Worker'i secenekler.js'i BUNDLE'a gommuyor + deploy.yml onu
# yayinlamiyor -> canli worker "Skan Art"i bilmiyor; konfigursuz bir Skan Art urununde
# malzeme/renk katsayisi sessizce DUSER (olculdu: ASA + ozel renk 27.600 yerine 15.000 kurus).
print("(k) Skan Art urunlerinde `konfigur` ZORUNLU — worker bundle drift emniyeti")
konfigursuz = [u.get("id") for u in skan_urunler if not u.get("konfigur")]
kontrol(not konfigursuz,
        "her Skan Art urunu `konfigur` tasiyor (konfigursuz: %s) — worker secenekler.js'i "
        "bundle'a gommedigi icin konfigursuz urunde malzeme/renk katsayisi CANLIDA duser"
        % (konfigursuz or "-"))

# ---------------------------------------------------------------- (d1) gercek kurt sayfasi
print("(d1) kurt sayfasi (gercek kayit — konfigur'lu) — kompakt kart, genis-buton YOK")
html = build.render_product(kurt, katalog)
KOMPAKT = ['class="eylem-ikonlar"', 'ikon-btn ikon-sepet', 'ikon-btn ikon-wa', 'opsiyon-adet-eylem']
for isaret in KOMPAKT:
    kontrol(html.count(isaret) == 1, "kompakt kart isareti VAR: %s" % isaret)
FALLBACK = ['<span class="cart-label">Sepete Ekle</span>', 'class="order-wa"']
for isaret in FALLBACK:
    kontrol(html.count(isaret) == 0, "eski genis-buton isareti YOK: %s" % isaret)

# ---------------------------------------------------------------- (d2) FONKSIYONEL fiksturu
# ⚠️ NEDEN SENTETIK: bugunku TEK Skan Art urunu (kurt) `konfigur` alanli. build.py'de
# kart_secim = bool(sema) or (fonksiyonel and not parametrik and not konfigur) ve
# `if kart_secim or konfigur:` -> konfigur yolu kompakt duzeni ZATEN veriyor. Yani (d1)
# FONKSIYONEL_KATEGORILER uyeligini HIC olcmuyor (olculdu 23 Tem: "Skan Art" listeden
# silinince kurt sayfasi BAYT-OZDES kaliyor).
print("(d2) sentetik semasiz/konfigursuz Skan Art urunu — FONKSIYONEL uyeliginin nobeti")
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
    kontrol(html_f.count(isaret) == 1, "sentetik sayfada kompakt isaret VAR: %s" % isaret)
for isaret in FALLBACK:
    kontrol(html_f.count(isaret) == 0, "sentetik sayfada genis-buton isareti YOK: %s" % isaret)
kontrol("var KART_SECIM = true;" in html_f,
        "sentetik sayfada KART_SECIM bayragi ACIK (malzeme karti secimi kablolu)")

# ---------------------------------------------------------------- (d3) URETIM HATTI
# ⚠️ NEDEN KUM HAVUZU: (d1)/(d2) yalniz render_product()'i cagiriyor; build.py'nin ANA
# main() dongusunu HIC gecmiyor. Olculdu (24 Tem): main() dongusune "gizli kategoriyi atla"
# satiri konunca kurt sayfasi uretilmiyordu (urun/ 9508 -> 9486) ve urun/ dizini tamamen
# silindiginde de test YESIL kaliyordu. Burada build.py GERCEKTEN kosturulur; ROOT gecici
# bir sembolik-link ciftligidir -> repoya TEK BAYT yazilmaz.
print("(d3) uretim hatti — build.py main() kum havuzunda kosuyor, sayfa DISKTE mi")


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
        # Kucuk katalog: kurt + ilgili-urun havuzu icin birkac Dekorasyon urunu.
        alt = [kurt] + [u for u in katalog if u.get("kategori") == "Dekorasyon"][:8]
        with open(os.path.join(kum, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump(alt, f, ensure_ascii=False)
        r = subprocess.run([sys.executable, os.path.join(kum, "tools", "build.py")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None, None, "build.py cikis kodu %d (stderr: %s)" % (
                r.returncode, r.stderr.strip()[-300:] or "-")
        sayfa_yolu = os.path.join(kum, "urun", PID, "index.html")
        if not os.path.isfile(sayfa_yolu):
            return None, None, "urun/%s/index.html DISKTE URETILMEDI (main() dongusu urunu atladi mi?)" % PID
        with open(sayfa_yolu, encoding="utf-8") as f:
            sayfa = f.read()
        sm_yolu = os.path.join(kum, "sitemap.xml")
        if not os.path.isfile(sm_yolu):
            return sayfa, None, "sitemap.xml uretilmedi"
        with open(sm_yolu, encoding="utf-8") as f:
            return sayfa, f.read(), None
    finally:
        shutil.rmtree(kum, ignore_errors=True)


u_sayfa, u_sitemap, u_hata = uretim_hatti_olc()
kontrol(u_hata is None,
        "build.py main() kum havuzunda kurt sayfasini DISKE yazdi (hata: %s)" % (u_hata or "-"))
if u_sayfa:
    for isaret in KOMPAKT:
        kontrol(u_sayfa.count(isaret) == 1,
                "URETILEN dosyada kompakt kart isareti VAR: %s" % isaret)
    kontrol('<section class="related">' in u_sayfa,
            "URETILEN dosyada ilgili urunler bolumu VAR")
if u_sitemap:
    kontrol(build.product_url(PID) in u_sitemap,
            "sitemap.xml'de kurt URL'i VAR (%s)" % build.product_url(PID))

# ---------------------------------------------------------------- (j) ilgili urunler
print("(j) ilgili urunler bolumu — ince alt-seride yedek havuz")
kontrol('<section class="related">' in html,
        'kurt sayfasinda <section class="related"> VAR (ic linkler ayakta)')
rel_adet = html.count('class="rel-card"')
kontrol(rel_adet >= build.REL_EN_AZ,
        "kurt sayfasinda rel-card sayisi >= %d (bulunan: %d)" % (build.REL_EN_AZ, rel_adet))
kontrol(build.AKRABA_KATEGORI.get(KATEGORI) == "Dekorasyon",
        'build.AKRABA_KATEGORI["%s"] == "Dekorasyon" (yedek havuz kablolu)' % KATEGORI)

# ---------------------------------------------------------------- (h) filament tavsiyesi
print("(h) filament tavsiyesi — kategori haritasi + sayfadaki rozet")
with open(FILAMENTLER, encoding="utf-8") as f:
    filref = json.load(f)
kontrol(KATEGORI in filref.get("kategoriTavsiye", {}),
        'filamentler.json kategoriTavsiye["%s"] tanimli' % KATEGORI)
kontrol(bool(filament_ortak.tavsiyeler(KATEGORI)),
        "filament_ortak.tavsiyeler(%r) bos DEGIL -> %r" % (KATEGORI, filament_ortak.tavsiyeler(KATEGORI)))
kontrol("fil-cip tavsiyeli" in html, 'urun sayfasinda "Tavsiyemiz" rozetli filament cipi var')

# ---------------------------------------------------------------- (i) URL kodlamasi
print("(i) iki kelimeli kategori adi URL'de yuzde-kodlu")
kontrol("?kategori=" + KATEGORI not in html,
        "sayfada HAM BOSLUKLU '?kategori=%s' URL'i YOK" % KATEGORI)
kontrol("?kategori=Skan%20Art" in html, "yuzde-kodlu '?kategori=Skan%20Art' URL'i VAR")
ld_bloklar = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
bread = None
for blok in ld_bloklar:
    obj = json.loads(blok)
    if obj.get("@type") == "BreadcrumbList":
        bread = obj
kontrol(bread is not None, "JSON-LD BreadcrumbList ayristirilabildi")
if bread:
    item = [x for x in bread["itemListElement"] if x.get("position") == 2][0]
    kontrol(" " not in item["item"], "BreadcrumbList item URL'inde ham bosluk YOK: %s" % item["item"])
    kontrol(item.get("name") == KATEGORI, 'BreadcrumbList adi "%s"' % KATEGORI)

# ---------------------------------------------------------------- (g) merchant feed
print("(g) Merchant feed taksonomisi")
kontrol(KATEGORI in build.GOOGLE_PRODUCT_CATEGORY,
        'GOOGLE_PRODUCT_CATEGORY["%s"] tanimli -> %r'
        % (KATEGORI, build.GOOGLE_PRODUCT_CATEGORY.get(KATEGORI)))
feed_xml, feed_adet = build.render_merchant_feed([kurt])
kontrol(feed_adet == 1, "kurt urunu feed'e giriyor (fiyatli + gorselli + parametrik degil)")
kontrol("<g:google_product_category>Home &amp; Garden &gt; Decor</g:google_product_category>" in feed_xml,
        "feed satirinda g:google_product_category basiliyor")
kontrol("<g:product_type>%s</g:product_type>" % KATEGORI in feed_xml,
        "feed g:product_type == %s" % KATEGORI)

# ---------------------------------------------------------------- (f) ana sayfa banner
print("(f) ana sayfa Skan Art banner'i — varlik, hedef, POZITIF GORUNURLUK, palet, marka dili")
m_ban = re.search(r'<a id="skanBanner"[^>]*>.*?</a>', index_html, re.S)
kontrol(m_ban is not None, 'index.html icinde <a id="skanBanner"> blogu var')
banner_html = m_ban.group(0) if m_ban else ""
m_ac = re.search(r'<a id="skanBanner"[^>]*>', banner_html)
banner_ac = m_ac.group(0) if m_ac else ""
BANNER_OZ = {ad.lower(): deger for ad, deger in
             re.findall(r'([-\w]+)\s*=\s*"([^"]*)"', banner_ac)}
KOK = {
    "etiket": "a",
    "oz": BANNER_OZ,
    "sinif": set(BANNER_OZ.get("class", "").split()),
}
kontrol(KOK["oz"].get("id") == "skanBanner" and "skan-banner" in KOK["sinif"],
        "banner ROOT elemani ayristirildi (id=%r, sinif=%s)"
        % (KOK["oz"].get("id"), sorted(KOK["sinif"])))

m_main = re.search(r"<main>(.*?)</main>", index_html, re.S)
kontrol(m_main is not None and 'id="skanBanner"' in m_main.group(1),
        "banner <main> icinde (ana sayfa vitrininin ustunde)")

# --- CSS: kurallar + ozel ozellik (var) tanimlari + ROOT kaskadi
css_hepsi = css_bloklari(index_html)
tum_kurallar = css_kurallari(css_hepsi)
VAR_TANIM = ozel_ozellik_tanimlari(tum_kurallar)
b_kurallar = [(s, d) for (s, d, _m) in tum_kurallar if BANNER_JETON.search(s)]
kontrol(len(b_kurallar) >= 6,
        "banner ailesi CSS kurallari bulundu (%d kural: %s)"
        % (len(b_kurallar), ", ".join(s for s, _ in b_kurallar[:4]) + " ..."))
kontrol(any(".skan-banner" in s for s, _ in b_kurallar),
        "kurallar arasinda .skan-banner secicisi var (blok tumden silinmemis)")

kok_kural = kok_kurallari(tum_kurallar, KOK)
kontrol(not COZULEMEYEN_SECICI,
        "banner ailesine deyen TUM seciciler ayristirilabildi (FAIL-CLOSED; cozulemeyen: %s)"
        % (sorted(set(COZULEMEYEN_SECICI)) or "-"))
kontrol(len(kok_kural) >= 2,
        "banner ROOT'una uygulanan kural bulundu (%d: %s)"
        % (len(kok_kural), [s for _, _, s, _ in kok_kural][:6]))

inline_stil = BANNER_OZ.get("style", "")
ETKIN = etkin_stil(kok_kural, inline_stil)
sorunlar = gorunurluk_sorunlari(ETKIN)
kontrol(not sorunlar,
        "banner ROOT'u POZITIF gorunurluk olcumunu geciyor (sorun: %s)" % (sorunlar or "-"))

if re.search(r"<a id=\"skanBanner\"[^>]*\shidden(?:\s|>|=)", banner_ac):
    kontrol(False, "banner HTML'inde `hidden` ozniteligi VAR")
kontrol(BANNER_OZ.get("aria-hidden") != "true", 'banner HTML\'inde aria-hidden="true" YOK')

# --- Metin sarmalayici cocuk: KOSULSUZ (medya disi) display:none = banner'i bosaltir.
# ⚠️ Cocuk ETIKET/-ust/-btn gizlemek (ozellikle @media icinde) MESRU responsive tasarimdir
# ve buraya GIRMEZ (24 Tem yanlis-kirmizi vakasi: @media(max-width:400px){.skan-banner-ust
# {display:none}} nobetciyi kirmiziya cekiyordu).
metin_olduren = []
for secici, govde, medya in tum_kurallar:
    if medya:
        continue
    if not re.search(r"\.(?:skan|jen)-banner-text\b", secici):
        continue
    if re.search(r"display\s*:\s*none", govde, re.I):
        metin_olduren.append(secici)
kontrol(not metin_olduren,
        "banner metin sarmalayicisi KOSULSUZ gizlenmemis (bulunan: %s)" % (metin_olduren or "-"))

# --- SARI TARAMASI: banner HTML + banner ailesinin TUM CSS kurallari, var() COZULEREK
bulgu = sari_bulgular(banner_html)
cozulemeyen_var = []
for sec, bildirimler in b_kurallar:
    cozulmus, eksik = var_coz(bildirimler, VAR_TANIM)
    cozulemeyen_var.extend(eksik)
    for b in sari_bulgular(cozulmus):
        bulgu.append("%s -> %s" % (sec, b))
kontrol(not cozulemeyen_var,
        "banner ailesindeki HER var(--ad) cozulebildi (FAIL-CLOSED; cozulemeyen: %s)"
        % (sorted(set(cozulemeyen_var)) or "-"))
kontrol(not bulgu, "banner HTML + banner ailesi CSS'inde SARI token YOK (var() cozumlu; "
        "bulunan: %s)" % (sorted(set(bulgu)) or "-"))
kontrol(any("var(--red)" in d for s, d in b_kurallar if ".skan-banner" in s),
        "banner marka paletini kullaniyor (kirmizi aksan var(--red))")

# --- MARKA/COGRAFYA DILI: banner metni + ana sayfanin GORUNUR pazarlama govdesi
kontrol(not yasak_ifadeler(banner_html),
        "banner metninde yasak ifade YOK (bulunan: %s)" % (yasak_ifadeler(banner_html) or "-"))
main_govde = m_main.group(1) if m_main else ""
main_gorunur = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ",
                      main_govde, flags=re.S)
main_yasak = yasak_ifadeler(main_gorunur)
kontrol(not main_yasak,
        "ana sayfanin GORUNUR <main> govdesinde yasak ifade YOK "
        "(JSON-LD/script haric — bulunan: %s)" % (main_yasak or "-"))

# ================================================================== DAVRANIS (node)
print("(b/c/f) DAVRANIS bolumu — index.html + secenekler.js node ile GERCEKTEN kosuyor")
if not node_var_mi():
    if os.environ.get("GITHUB_ACTIONS"):
        kontrol(False, "CI'da node var (FAIL-CLOSED: setup-node eksik/bozuk)")
        bitir()
    if os.environ.get("SKAN_ART_NODE_ATLA") == "1":
        print("UYARI: node yok + SKAN_ART_NODE_ATLA=1 → davranis bolumu ACIK uyariyla atlandi "
              "(yalniz kaynak/uretim kontrolleri kostu).")
        bitir()
    kontrol(False, "node bulundu (yerelde kur ya da SKAN_ART_NODE_ATLA=1 ile acik uyariyla atla)")
    bitir()

cat_src = js_bildirim(index_html, r"^\s*var\s+CATEGORIES\s*=.*$", "index.html CATEGORIES")
giz_src = js_bildirim(index_html, r"^\s*var\s+GIZLI_KATEGORILER\s*=.*$", "index.html GIZLI_KATEGORILER")
rendercats_src = js_fonksiyon(index_html, "renderCats")
applyurl_src = js_fonksiyon(index_html, "applyUrlParams")
rendergrid_src = js_fonksiyon(index_html, "renderGrid")

# --- (b1) renderCats: cip listesi GERCEKTEN ne uretiyor
IKON = "<EV-IKONU>"
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

s1 = node_kos(b1, "(b1) renderCats") if rendercats_src else None
if s1:
    cips = s1["cips"]
    beklenen = [IKON] + s1["cat"]
    kontrol(cips == beklenen,
            "renderCats() cip listesi TAM olarak ev-ikonu + CATEGORIES (%d cip; fazlalik: %s)"
            % (len(cips), [c for c in cips if c not in beklenen] or "-"))
    sizanlar = [g for g in s1["gizli"] if g in cips]
    kontrol(not sizanlar,
            "GIZLI kategorilerin HICBIRI nav cipi olarak basilmiyor (sizan: %s)" % (sizanlar or "-"))
    kontrol(KATEGORI not in cips, '"%s" nav cipi olarak basilmiyor' % KATEGORI)

# --- (b2) applyUrlParams: derin link GERCEKTEN activeCat'i set ediyor mu
# ⚠️ Banner HEDEFI de BURADAN olculur: href METNINI kalibla karsilastirmak yerine banner'in
# GERCEK href'inin sorgu dizesi applyUrlParams'a verilir. Boylece "/?kategori=Skan+Art"
# (URLSearchParams "+"i bosluga cozer) DAVRANISSAL olarak esdeger sayilir — 24 Tem
# yanlis-kirmizi vakasi.
banner_href = BANNER_OZ.get("href", "")
banner_qs = banner_href[banner_href.find("?"):] if "?" in banner_href else ""
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
  banner: dene(__BANNERQS__),
  jen: dene("?kategori=Jenerat%C3%B6r"),
  dekor: dene("?kategori=Dekorasyon"),
  uydurma: dene("?kategori=BoyleBirKategoriYok")
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__APPLYURL__", applyurl_src) \
   .replace("__BANNERQS__", json.dumps(banner_qs))

s2 = node_kos(b2, "(b2) applyUrlParams") if applyurl_src else None
if s2:
    kontrol(s2["skan"] == KATEGORI,
            '?kategori=Skan%%20Art derin linki activeCat\'i "%s" yapiyor (bulunan: %r)'
            % (KATEGORI, s2["skan"]))
    kontrol(s2["banner"] == KATEGORI,
            'banner\'in GERCEK href\'i (%r) DAVRANISSAL olarak "%s" kategorisini aciyor '
            "(bulunan: %r) — banner tiklamasinin TEK girisi"
            % (banner_href, KATEGORI, s2["banner"]))
    kontrol(s2["jen"] == "Jeneratör", "?kategori=Jeneratör derin linki calismaya devam ediyor")
    kontrol(s2["dekor"] == "Dekorasyon", "gorunur kategori derin linki calisiyor (Dekorasyon)")
    kontrol(s2["uydurma"] == "Tümü",
            "tanimsiz kategori derin linki YOK SAYILIYOR (beyaz liste hala yuk tasiyor)")

# --- (f2) renderGrid goster/gizle KABLOSU: kaynak-metni degil GERCEK KOSUM
# ⚠️ 24 Tem kacagi: toggle blogu AYNEN dururken hemen ardina
# `document.getElementById("skanBanner").style.display="none"` eklenince eski (regex)
# nobetci YESIL yaniyordu. Artik renderGrid TAMAMEN kosturulur ve display'in SON degeri
# olculur -> sonradan gelen her override yakalanir.
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
  marka: olc("Tümü", "", "Audi"),
  jenAna: (function(){ var r = olc("Tümü", "", "Tümü"); return ("jenBanner" in kayit) ? kayit["jenBanner"] : "__HIC-DOKUNULMADI__"; })()
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__RENDERGRID__", rendergrid_src)

s4 = node_kos(b4, "(f2) renderGrid banner toggle") if rendergrid_src else None
if s4:
    kontrol(s4["ana"] == "",
            'renderGrid ANA gorunumde skanBanner display === "" (bulunan: %r) '
            "— GERCEK kosum, kaynak-metni degil" % s4["ana"])
    kontrol(s4["kategori"] == "none",
            'KATEGORI gorunumunde skanBanner display === "none" (bulunan: %r)' % s4["kategori"])
    kontrol(s4["arama"] == "none",
            'ARAMA gorunumunde skanBanner display === "none" (bulunan: %r)' % s4["arama"])
    kontrol(s4["marka"] == "none",
            'MARKA gorunumunde skanBanner display === "none" (bulunan: %r)' % s4["marka"])
    kontrol(s4["jenAna"] == "",
            'emsal bozulmamis: jenBanner de ANA gorunumde display === "" (bulunan: %r)' % s4["jenAna"])

# --- (c2) secenekler.js davranisi: fonksiyonelMi + satirOzeti (para etkisi)
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

s3 = node_kos(b3, "(c2) secenekler.js")
if s3:
    kontrol(s3["fonk"] is True,
            'PRUVO_SECENEK.fonksiyonelMi("%s") === true (bulunan: %r)' % (KATEGORI, s3["fonk"]))
    kontrol(s3["fonkDekor"] is True, 'fonksiyonelMi("Dekorasyon") === true (emsal bozulmamis)')
    kontrol(s3["fonkYok"] is False, "fonksiyonelMi(tanimsiz kategori) === false (liste yuk tasiyor)")
    kontrol("Malzeme: PETG (+%30)" in (s3["detay"] or ""),
            "satirOzeti Skan Art satirina malzeme/renk detayini yaziyor (bulunan: %r)" % s3["detay"])
    # 1.000 TL × PETG (+%30) = 1.300,00 TL; adet 2 -> 260000 kurus. fonksiyonelMi bypass
    # edilirse katsayi UYGULANMAZ ve 200000 kurus tahsil edilir (sessiz eksik tahsilat).
    kontrol(s3["kurus"] == 260000,
            "malzeme KATSAYISI uygulaniyor: 2 × (1.000 TL +%%30) = 260000 kurus (bulunan: %r)"
            % s3["kurus"])

bitir()
