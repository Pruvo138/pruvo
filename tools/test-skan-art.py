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
  (e) Kurt urununun KARAR TASIYAN alanlari: kategori == "Skan Art" + `konfigur` MEVCUT.
      Seri KAPSAMI: yalniz "seri BOS DEGIL (>= 1)". [24 Tem: govde SHA256 capasi + kati
      "== 1" sayi capasi KALDIRILDI; SON TURDA tavan/toplu-tasima capalari da TAMAMEN
      KALDIRILDI — kumulatif olduklari icin seri 21. urune ulastiginda deploy KALICI
      kirmizi oluyordu. urunler.json'un yazari baska bir mimar, kod duzlemi veri duzlemine
      kilitlenmez; yanlis kirmizinin bedeli toplu-tasima riskinden buyuk.]
  (f) Ana sayfa banner'i — POZITIF GORUNURLUK OLCUMU (yasakli-bildirim listesi DEGIL):
      banner ROOT'una uygulanan efektif CSS kurallari secici eslesmesiyle (etiket + id +
      sinif + OZNITELIK secicisi + :not/:is/:where) toplanir, ozgulluk+kaynak sirasina gore
      cozulur ve asgari gecerli durum dogrulanir (display != none, visibility gorunur,
      opacity >= 0.9, pozitif hesaplanan yukseklik, ekran ici konum, kirpma yok).
      Banner ailesinin renk paleti var(--ad) DOLAYIMI COZULEREK taranir; 8/4/6/3 haneli
      hex + rgb()/hsl() + CSS renk adlari kapsanir, modern renk notasyonu (oklch/lab/lch/
      color()/color-mix) banner ailesinde FAIL-CLOSED YASAK.
      [24 Tem SON TUR — KAPI EKSENI ELEMANDAN HEDEF JETONUNA TASINDI: gorunurluk + beyaz
      liste YALNIZ oznesi banner jetonu tasiyan kurallarda olculur (banner ROOT'u bir <a>
      oldugu icin site geneli `a{}`/`*{}` kurallari kaskada giriyor ve banner'la ILGISIZ
      rutin CSS eklemeleri TUM SITE DEPLOY'unu durduruyordu). Beyaz liste yalniz KOSULSUZ
      (medyasiz + durum-sahte-sinifsiz) kaskadda kosar. SARI taramasi YALNIZ skan-banner/
      skanBanner ailesinde kosar — jen-banner PARAMETRIK seridir, orada sari MESRUDUR.
      "var(--red) literali zorunlu" maddesi KALDIRILDI. Bedeller: BILINEN SINIRLAR 4-6.]
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
      [24 Tem SON TUR — kapatilan SINIFLAR:
        · SARI taramasi jetonlu-secici metninden KASKAD CIKTISINA tasindi: banner ROOT'una
          gercekten uygulanan her cozulmus deger taranir -> jetonsuz sinif
          ('.nordik-yama{background:#ffd400}') ve yapisal secici
          ('main > a:nth-of-type(2){background:#ffd400}') artik yakalanir.
        · YUKSEKLIK esigi BANNER_ASGARI_YUKSEKLIK_PX=40 (eskiden yalniz TAM SIFIR):
          'min-height:2px;height:2px;overflow:hidden' ve 'max-height:1px' kapandi.
        · GORUNURLUK kara listeden BEYAZ LISTEYE cevrildi: banner ROOT'unun KOSULSUZ
          kaskadinda beyaz liste disi her ozellik FAIL-CLOSED kirmizi (mask-image, filter,
          backdrop-filter, zoom, translate, rotate ...); ayrica deger denetimleri
          (display:contents, margin-top:-9999px, width:0, font-size:0).
        · YUZDE-23 kacisi: sari taramasi girdiyi once urllib.parse.unquote ile cozer
          (data-URI SVG icindeki fill=%23ffd400); base64 data-URI banner ailesinde YASAK.
        · JS sinifi PAHALI PROXY yerine UCUZ SOZLESME (f3): banner id'lerine index.html
          JS'inde YALNIZ renderGrid toggle blogu dokunabilir; toggle blogu da yalniz
          .style.display yazar. "JS ile gizle" + "JS ile sariya boya" siniflari tek kuralla.
      Kapatilan YANLIS-KIRMIZILAR: '.skan-banner:hover{opacity:.85}' (durum secicisinde
      KISMI opaklik mesru; durum kaskadinda yalniz OLDURUCU kanallar olculur) ·
      '.jen-banner-text a{display:none}' + '.skan-banner-text a.dip-not{display:none}'
      (metin kutusu ICINDEKI ikincil linki gizlemek mesru — kural artik yalniz OZNESI metin
      kutusu olan secicilerde sayilir) · cok bilesenli secicide ata zinciri dogrulanir:
      OZNE ROOT'a uysa bile onundeki bilesen ROOT'un ATASI degilse kural ROOT'a YAZILMAZ.]
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

⚠️ BILINEN SINIRLAR (testin kendi ciktisinin sonunda da basilir): (1) uzak/raster gorsel
icerigi taranamaz, (2) calisma zamaninda uretilen (eval/dinamik) stil kapsam disi, (3) CSS
motoru tarayici degil (kombinator sirasi/@layer/@container tam degerlendirilmez), (4) BU KAPI
BIR DISIPLIN CIHAZIDIR, GUVENLIK SINIRI DEGIL — kazayla bozmayi yakalar, KARARLI bir editoru
durdurmaz (sonsuz gerileme olurdu; sertlestirme 24 Tem itibariyla BITMISTIR).

Ag YOK, repo dosyasina YAZMAZ (d3 kum havuzu gecici dizinde), build.py'den ONCE kosabilir.
NODE GEREKIR (davranis bolumleri) — CI'da setup-node kurulu ve node yoksa test FAIL-CLOSED
kirmizi yanar. Yerelde node yoksa acik uyariyla atlamak icin: SKAN_ART_NODE_ATLA=1.
Kullanim:  python3 tools/test-skan-art.py     (0 = gecti, 1 = kirmizi)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build  # noqa: E402
import filament_ortak  # noqa: E402

KATEGORI = "Skan Art"
PID = "kurt-heykeli-serit-dekoratif-figur"
# (e) KAPSAM capasi — 24 Tem SON TUR: SAYI TAVANI TAMAMEN KALDIRILDI.
# NEDEN (olculdu): TAVAN/TOPLU_ESIK/BILINEN_SAYI ucluSU pratikte KUMULATIF bir capaydi —
# BILINEN_SAYI donmus bir sabit oldugu icin "tek seferde artis" aslinda "TOPLAM sayi"yi
# olcuyordu: seri 20 urunde exit 0, 21 urunde exit 1 ("artis 20 < 20"), 30 urunde exit 1.
# Yani seri 21. urune ulastigi anda deploy KALICI kirmizi olurdu. Yanlis kirmizinin bedeli
# (TUM SITE DEPLOY'unun durmasi) toplu-tasima riskinden BUYUK -> capa yok.
# Geriye tek veri kurali kaldi: seri BOSALMASIN (>= 1) + (k) her Skan Art urunu konfigur tasisin.
SKAN_ART_TABAN = 1             # seri bosalirsa banner bos kategoriye link verir
# (f) Banner ROOT'unun mesru sayilan ASGARI hesaplanan yuksekligi. Bugunku tasarim 168px
# (dar ekranda 168 -> 150px). 40px = mesru "kompakt banner" tabani; altindaki her sey
# (min-height:2px;overflow:hidden gibi) gorunurlugu pratikte oldurur.
BANNER_ASGARI_YUKSEKLIK_PX = 40

INDEX = os.path.join(ROOT, "index.html")
SECENEKLER = os.path.join(ROOT, "secenekler.js")
FILAMENTLER = os.path.join(TOOLS, "filamentler.json")
URUNLER = os.path.join(ROOT, "urunler.json")

HATALAR = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)


BILINEN_SINIRLAR = """
BILINEN SINIRLAR (bu kapinin OLCMEDIGI seyler — durust liste)
  1. UZAK/RASTER ICERIK TARANAMAZ: R2'deki .jpg/.png/.webp ve harici URL'lerin PIKSELLERI
     okunmaz. Banner arka planina sari bir raster gorsel konursa bu kapi GORMEZ.
     (Bugunku Skan Art banner'i bilerek GORSELSIZ saf-CSS'tir — bu sinir o yuzden ucuz.)
  2. CALISMA ZAMANINDA URETILEN STIL KAPSAM DISI: eval / new Function / dinamik <style>
     enjeksiyonu / harici JS / tarayici eklentisi ile uretilen kurallar olculmez. JS
     duzleminde olculen sey KAYNAK SOZLESMESIDIR (banner id'sine yalniz renderGrid toggle
     blogu dokunur) + renderGrid'in sahte DOM'da GERCEK kosumu; sahte DOM tam bir tarayici
     degildir (setTimeout/remove()/cssText gibi yollar yapisal olarak modellenmez).
  3. CSS motoru bir TARAYICI DEGIL: ata zinciri modellenir ama kombinator SIRASI (> + ~),
     kaskad katmanlari (@layer), @container, @scope, @supports dallanmasi ve devralma
     (inheritance) tam degerlendirilmez. Uzunluklar 800x1280 varsayimiyla kabaca px'e cevrilir.
  4. 🔴 SITE GENELI (JETONSUZ) SECICILER GORUNURLUK DENETIMININ DISINDADIR. Kapinin ekseni
     ELEMAN degil HEDEF JETONUDUR: yalniz oznesi skan-banner/skanBanner/jen-banner/jenBanner
     tasiyan kurallar denetlenir. Banner ROOT'u bir <a> oldugu icin `a{display:none}`,
     `*{...}`, `main a{...}` gibi bir kural banner'i teknik olarak gizleyebilir ve bu kapi
     GORMEZ. Bedel BILEREK kabul edildi: ters kurulum (eleman ekseni) banner'la ILGISIZ
     rutin CSS eklemelerinin TUM SITE DEPLOY'unu durdurmasina yol aciyordu (olculdu 24 Tem:
     18 rutin eklemenin 10'u kirmizi). SARI taramasi bu daralmanin disindadir — orada
     jetonsuz/yapisal seciciler de taranir.
  5. jen-banner / jenBanner (PARAMETRIK "sari seri") SARI DENETIMININ DISINDADIR: CLAUDE.md
     "sari yalniz parametrik seri" der, yani o ailede sari MESRUDUR (olculdu 24 Tem:
     `.jen-banner-btn{border-color:#ffd400}` MESRU bir degisiklikti ve nobetciyi kirmiziya
     cekiyordu — marka kuralinin TERSI). AYRIM: Skan Art banner'inin ROOT'u
     `class="jen-banner skan-banner"` tasidigi icin, jen ailesine yazilan bir kural GERCEKTEN
     Skan Art ROOT'una inerse KASKAD katmani onu yine yakalar (olculdu: `.jen-banner
     {background:#ffd400}` KIRMIZI). Disarida kalan sey yalniz jen-e OZEL cocuklardir
     (`.jen-banner-btn`, `.jen-banner-title` ...). Gorunurluk denetimi jen icin TAMAMEN durur.
  6. URUN SAYISI TAVANI YOKTUR. Yalniz "seri bosalmasin (>= 1)" + "her Skan Art urunu
     `konfigur` tasisin" kurallari bloklayicidir. Tek seferde kac urun eklendigi/tasindigi
     OLCULMEZ: kumulatif capa 21. urunde deploy'u kalici kirmiziya cekiyordu, yanlis
     kirmizinin bedeli toplu-tasima riskinden buyuk. (Toplu tasimanin ONEMLI kismi yine de
     yakalanir: tasinan urunler `konfigur` tasimadigi icin (k) maddesi kirmizi yanar —
     olculdu: 168 urunluk toplu tasima KIRMIZI.)
  7. BEYAZ LISTE YALNIZ KOSULSUZ (medyasiz + durum-sahte-sinifsiz) KASKADDA KOSAR. Bir
     @media sarmalayicisi icine yazilan tanimadik ozellik beyaz listeye TAKILMAZ (olculdu:
     `@media(min-width:0px){.skan-banner{mask-image:...}}` ve `{zoom:0}` YESIL gecer; ayni
     bildirimler KOSULSUZ yazilinca KIRMIZI). Bedel bilerek kabul edildi: beyaz liste medya
     dahil kosarken mesru responsive alani cok daraliyordu
     (`@media(max-width:640px){.skan-banner{transform:none}}` yanlis-kirmizi yakiyordu).
     ⚠️ OLDURUCU kanallar (display:none/contents, visibility, opacity==0, sifir/kucuk kutu,
     ekran disina itme, `filter` deger denetimi) @media DAHIL olculmeye devam eder.
  8. BU KAPI BIR DISIPLIN CIHAZIDIR, GUVENLIK SINIRI DEGIL. Amaci, iyi niyetli bir gelecek
     editorunun banner'i KAZAYLA sariya boyamasini / gizlemesini yakalamaktir. Kararli bir
     editor (string parcalama, dinamik id uretimi, jetonsuz secici, ayri dosyaya tasima) bu
     kapiyi ASAR — bunu durdurmak HEDEF DEGIL: sonsuz gerileme olurdu.
""".rstrip()


def bitir():
    print("=" * 70)
    if HATALAR:
        print("SONUC: %d KIRMIZI ❌" % len(HATALAR))
        for h in HATALAR:
            print("  - " + h)
        print(BILINEN_SINIRLAR)
        sys.exit(1)
    print("SONUC: GECTI ✅ (Skan Art kategorisi + banner + kurt urunu kabul kriterleri saglandi)")
    print(BILINEN_SINIRLAR)
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


def bilesik_esler(bl, kok, atalar=None, belirsiz=None):
    """Tek bilesik verilen elemana uyuyor mu? True/False/`belirsiz`(=cozulemedi).

    `belirsiz` cozulemeyen alt-ifadelerde donulen degerdir:
      None -> KESIN mod (gorunurluk olcumu; cozulemeyen kural ROOT'a YAZILMAZ,
              banner jetonu tasiyorsa ayrica COZULEMEYEN_SECICI'ye dusup fail-closed yanar)
      True -> GENIS mod (sari taramasi; yapisal secici `:nth-of-type(2)` ESLESMIS sayilir —
              olculdu 24 Tem: `main > a:nth-of-type(2){background:#ffd400}` gercekten
              banner'i boyuyordu ve KESIN modda kaciyordu)."""
    d = bilesik_ayristir(bl)
    if d is None:
        return belirsiz
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
            return belirsiz
        if not r:
            return False
    for ad, arg in d["pcls"]:
        if ad in DURUM_PCLS:
            continue           # fail-closed: durum sahte-sinifi ESLESMIS sayilir
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
        return belirsiz        # :nth-child vb. -> cozulemedi
    return True


def secici_esler(secici, kok, atalar=None, belirsiz=None):
    """Virgulsuz TEK secici: SUBJECT (son) bilesik ROOT'a uyuyor mu VE onundeki her bilesik
    ROOT'un GERCEK bir atasina uyuyor mu?

    ⚠️ 24 Tem yanlis-kirmizi vakasi: eskiden yalniz SUBJECT olculuyordu; `.jen-banner-text a`
    gibi bir kuralda subject (`a`) ROOT'a uyunca kural ROOT'a YAZILIYORDU — oysa
    `.jen-banner-text` ROOT'un atasi DEGIL (cocugu). Artik ata zinciri gercek HTML'den
    cikarilip dogrulanir: uyamayan bir ata bileseni varsa kural ROOT'a YAZILMAZ."""
    bl = _bilesikler(secici.strip())
    if not bl:
        return False
    r = bilesik_esler(bl[-1], kok, atalar, belirsiz)
    if r is not True:
        return r
    if len(bl) == 1:
        return True
    if atalar is None:
        return belirsiz        # ata modeli yok -> karar veremeyiz
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
    """Secicide :hover/:focus/:active gibi bir DURUM sahte-sinifi var mi?
    Durumsal kural KOSULSUZ degildir: dinlenme halinde banner'a UYGULANMAZ."""
    for bl in _bilesikler(secici.strip()):
        d = bilesik_ayristir(bl)
        if d is None:
            continue
        if any(ad in DURUM_PCLS for ad, _ in d["pcls"]):
            return True
    return False


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
# SARI denetiminin jetonu DAHA DAR: sari YALNIZ parametrik seride (jen-banner) MESRUDUR
# — CLAUDE.md "sarı yalnız parametrik seri". jen ailesi sari taramasinin TAMAMEN disindadir
# (olculdu 24 Tem: `.jen-banner-btn{border-color:#ffd400}` MESRU bir degisiklikti ve
# nobetciyi kirmiziya cekiyordu -> marka kuralinin TERSI).
SARI_JETON = re.compile(r"skan-banner|skanBanner")


def ozne_banner_jetonlu_mu(tek_secici):
    """Secicinin OZNESI (son bilesik) banner jetonunu SINIF/ID/OZNITELIK olarak tasiyor mu?

    🔴 24 Tem SON TUR — KAPI EKSENI ELEMANDAN JETONA TASINDI. Banner ROOT'u bir <a>
    oldugu icin site geneli `a{...}` ve `*{...}` kurallari da onun kaskadina giriyordu:
    banner'la ILGISIZ rutin bir CSS eklemesi (`a{list-style:none}`,
    `*{scrollbar-width:thin}`, `main a{text-rendering:optimizeLegibility}`,
    `@media print{a{page-break-inside:avoid}}`, global reset satirina
    `-webkit-text-size-adjust` eklemek ...) beyaz listeye takilip TUM SITE DEPLOY'unu
    durduruyordu — olculdu: 18 rutin eklemenin 10'u kirmizi.
    Artik GORUNURLUK + BEYAZ LISTE denetimi YALNIZ oznesi banner jetonu tasiyan kurallara
    uygulanir. Jetonsuz secicilerden (*, a, main a, :nth-of-type, yapisal seciciler) gelen
    bildirimler gorunurluk kaskadina GIRMEZ.
    ⚠️ BEDELI (bilerek kabul edildi, BILINEN SINIRLAR'a yazildi): site geneli bir `a{}`
    kurali ile banner gizlenebilir. Bu kapi bir DISIPLIN CIHAZIDIR, guvenlik siniri degil.
    ⚠️ SARI taramasi bu daralmanin DISINDADIR: genis kaskad orada KALIR (sari yakalamak
    ucuz ve yanlis-kirmizi uretmiyor)."""
    bl = _bilesikler(tek_secici.strip())
    if not bl:
        return False
    ozne = bl[-1]
    d = bilesik_ayristir(ozne)
    if d is None:
        return bool(BANNER_JETON.search(ozne))      # cozulemedi -> fail-closed: jeton varsa AL
    if d["id"] and BANNER_JETON.search(d["id"]):
        return True
    if any(BANNER_JETON.search(s) for s in d["sinif"]):
        return True
    if any(BANNER_JETON.search(o) for o in d["oz"]):
        return True                                 # a[id="skanBanner"] gibi
    return any(BANNER_JETON.search(arg or "") for _ad, arg in d["pcls"])  # :is(#skanBanner)


VOID_ETIKET = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
               "meta", "param", "source", "track", "wbr"}


def ata_zinciri(html_metin, hedef_ofset):
    """`hedef_ofset`teki elemanin GERCEK ata zinciri (disdan ice): [{etiket, oz, sinif}].
    <script>/<style> govdeleri once ESIT UZUNLUKTA bosluga cevrilir — JS'teki `a<b`
    ifadesi sahte etiket olarak yigina girmesin."""
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
    """Banner ROOT'una GERCEKTEN uygulanan kurallar:
    [(sira, ozgulluk, secici, govde, durumsal, medyali)].
    Ayristirilamayan AMA banner ailesine deyen secici -> COZULEMEYEN_SECICI (fail-closed).

    `atalar` = ata_zinciri() ciktisi; cok bilesenli secicilerde ONDEKI bilesenler bu
    zincire dogrulanir (bkz. secici_esler)."""
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
    """Kaskad: (onemli, ozgulluk, sira) en buyuk kazanir. -> {ozellik: (deger, secici)}

    `durumu_dahil_et=False` -> :hover/:focus gibi DURUM kurallari DISLANIR; boylece
    banner'in DINLENME halindeki efektif stili olculur (24 Tem yanlis-kirmizi vakasi:
    `.skan-banner:hover{opacity:.85}` kaskadi kazanip dinlenme opakligini eziyordu).

    `medyayi_dahil_et=False` -> @media/@supports sarmalayicisi icindeki kurallar da
    DISLANIR. TABAN kaskadi budur ve POZITIF gereklilikler (yukseklik/genislik tabani)
    YALNIZ ondan olculur. ⚠️ 24 Tem kacagi: `.skan-banner{min-height:2px}` yazildiginda
    `@media(max-width:640px){.skan-banner{min-height:150px}}` kurali kaskadi kazanip
    esigi SAHTE olarak sagliyordu — dar ekran kurali genis ekrani KURTARAMAZ."""
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
    KURAL notunun testi kirmiziya cekmesi sahte pozitif olurdu.
    YUZDE-KODLAMA once cozulur: data-URI SVG icindeki `fill='%23ffd400'` yuzde-23 yuzunden
    hex tarayicisina takilmiyordu (24 Tem kacagi)."""
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


# (C3) BEYAZ LISTE — banner ROOT'unda KOSULSUZ kullanilmasina izin verilen ozellikler.
# Kara liste yerine beyaz liste: "tanimadigim ozellik banner ROOT'unda = ACIKLANMAMIS RISK"
# -> FAIL-CLOSED kirmizi. Boylece tek tek mekanizma degil, bir SINIF kapanir; bugun kacan
# somut ornekler (hepsi olculdu 24 Tem): mask-image, filter:opacity(0), backdrop-filter,
# zoom:0, translate/rotate (mustakil ozellikler), -webkit-box-orient hilesi.
# ⚠️ Beyaz liste yalniz KOSULSUZ kaskada uygulanir: :hover/:focus altindaki tasarim
# denemeleri (transform:translateY(-2px), filter:brightness(1.1) ...) serbest kalir.
IZINLI_KOK_OZELLIKLERI = {
    # -- yerlesim
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
    # -- boyama
    "background", "background-color", "background-image", "background-size",
    "background-position", "background-repeat", "background-attachment", "background-clip",
    "background-origin", "border", "border-top", "border-right", "border-bottom",
    "border-left", "border-color", "border-width", "border-style", "border-radius",
    "border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius",
    "border-bottom-right-radius", "box-shadow", "color", "opacity", "visibility",
    "outline", "outline-color", "outline-offset", "outline-width", "outline-style",
    "accent-color", "isolation",
    # -- tipografi
    "font", "font-family", "font-size", "font-style", "font-weight", "font-variant",
    "line-height", "letter-spacing", "word-spacing", "text-align", "text-decoration",
    "text-decoration-color", "text-decoration-line", "text-indent", "text-shadow",
    "text-transform", "white-space", "word-break", "overflow-wrap", "vertical-align",
    "-webkit-font-smoothing",
    # -- etkilesim / gecis (statik gorunurlugu degistirmez)
    # `filter` beyaz listede AMA degeri ayrica denetlenir (bkz. filtre_sorunlari)
    "filter",
    "cursor", "pointer-events", "content-visibility", "user-select", "-webkit-user-select",
    "-webkit-tap-highlight-color", "touch-action", "appearance", "-webkit-appearance",
    "transition", "transition-property", "transition-duration", "transition-timing-function",
    "transition-delay", "will-change", "contain-intrinsic-size",
}
# Ozellikle YASAK (beyaz listede olmadigi icin zaten kirmizi; okunurluk icin isimlendirildi):
# transform, translate, rotate, scale, perspective, filter, backdrop-filter, mask, mask-image,
# clip, clip-path, zoom, content, contain, mix-blend-mode, shape-outside.

# Banner ROOT'u bir kutu olmali: bu display degerleri kutuyu yok eder / duzeni bozar.
OLDUREN_DISPLAY = {"none", "contents"}

# `filter` beyaz listededir AMA degeri denetlenir: renk/gorunurluk ceviren fonksiyonlar
# (opacity/sepia/saturate/invert/grayscale/hue-rotate/blur) banner ROOT'unda YASAK,
# ince parlaklik/kontrast ayari MESRU (olculdu: filter:brightness(1.02) mesru fikstur,
# filter:opacity(0) ve filter:sepia(1) saturate(6) ise kacaklardi).
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
            s.append("filter:%s() banner ROOT'unda YASAK (gorunurlugu/rengi cevirir)  [%s]"
                     % (ad, kaynak))
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
    """POZITIF olcum: banner ROOT'unun ASGARI gecerli gorunur durumu saglaniyor mu?

    mod="taban"    -> KOSULSUZ + MEDYASIZ kaskad: POZITIF TABANLAR
                      (yukseklik/genislik/font-size esikleri) + BEYAZ LISTE. Dar-ekran
                      kurali genis ekrani kurtaramasin diye ayri olculur.
                      ⚠️ 24 Tem SON TUR: BEYAZ LISTE buraya TASINDI. Eskiden medya DAHIL
                      kaskada uygulaniyordu ve mesru responsive alani cok daraliyordu
                      (olculdu: `@media(max-width:640px){.skan-banner{transform:none}}`
                      yanlis-kirmizi yakiyordu). @media icindeki bildirimler beyaz
                      listeden MUAF; oldurucu kanallar + filtre denetimi medya DAHIL kalir.
    mod="kosulsuz" -> durum-disi (medya DAHIL) kaskad: oldurucu kanallar + ekran disina
                      itme + kirpma + FILTRE denetimi + BEYAZ LISTE.
    mod="durum"    -> :hover/:focus/:active dahil kaskad: YALNIZ OLDURUCU kanallar
                      (display:none/contents, visibility:hidden, opacity == 0).
                      NEDEN: `.skan-banner:hover{opacity:.85}` mesru bir tasarim jesti;
                      kismi opaklik durum secicisinde kirmizi YAKMAZ (24 Tem yanlis-kirmizi)."""
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
        # ---- YALNIZ POZITIF TABANLAR (kosulsuz + medyasiz kaskaddan)
        mh = _uzunluk_px(dg("min-height"))
        hh = _uzunluk_px(dg("height"))
        if (mh is None or mh < E) and (hh is None or hh < E):
            s.append("banner ROOT'unda KOSULSUZ >= %dpx yukseklik YOK "
                     "(min-height=%r [%s], height=%r [%s]) — @media kurali genis ekrani "
                     "KURTARMAZ" % (E, dg("min-height"), kaynak("min-height"),
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
        # --- BEYAZ LISTE (fail-closed): tanimadigimiz her ozellik aciklanmamis risktir.
        # YALNIZ KOSULSUZ (medyasiz + durum-sahte-sinifsiz) kaskadda; @media icindeki
        # bildirimler MUAF (mesru responsive alani).
        for ad in sorted(etkin):
            if ad.startswith("--") or ad in IZINLI_KOK_OZELLIKLERI:
                continue
            s.append("banner ROOT'unda BEYAZ LISTE DISI ozellik: %s:%s  [%s] "
                     "(yerlesim/boyama etkisi denetlenmedi -> fail-closed)"
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

    # OLDURUCU boyut kurallari (medya dahil): kucuk max-height / sifir kutu her ekranda oldurur
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
    # margin ile ekran disina itme (position gerektirmez): margin-top:-9999px
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

    # ⚠️ BEYAZ LISTE burada DEGIL, mod="taban" kaskadinda olculur (24 Tem SON TUR):
    # bu kaskad @media'yi de icerir ve responsive bir `transform:none` beyaz listeye
    # takilip yanlis-kirmizi yakiyordu.
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
print("(e) kurt urunu — KARAR TASIYAN alanlar + seri KAPSAMI (aralik + toplu tasima)")
with open(URUNLER, encoding="utf-8") as f:
    katalog = json.load(f)
kurtlar = [u for u in katalog if u.get("id") == PID]
kontrol(len(kurtlar) == 1, "%s katalogda TEK kayit" % PID)
if not kurtlar:
    print("SONUC: KALDI ❌ (urun bulunamadi, kalan maddeler olculemedi)")
    sys.exit(1)
kurt = kurtlar[0]
# ⚠️ 24 Tem: govde SHA256 capasi + kati alan-kumesi KALDIRILDI. NEDEN: kurt urununde RUTIN
# fiyat/gorsel/aciklama/lisans guncellemesi (MaCiT'in duzelt.py isi) bu bloklayici CI adimini
# kirmiziya cekip TUM SITE DEPLOY'unu durduruyordu. Artik yalniz KARAR TASIYAN alanlar
# dogrulanir: kategori + konfigur varligi. fiyat/gorseller/aciklama/baslik/lisans SERBEST.
kontrol(kurt.get("kategori") == KATEGORI, 'kategori == "%s" (bulunan: %r)' % (KATEGORI, kurt.get("kategori")))
kontrol(bool(kurt.get("konfigur")),
        "kurt kaydinda `konfigur` alani MEVCUT (bulunan: %r) — malzeme/renk katsayisinin "
        "canlida dusmemesi buna bagli" % (kurt.get("konfigur") and "var" or kurt.get("konfigur")))

skan_urunler = [u for u in katalog if u.get("kategori") == KATEGORI]
n_skan = len(skan_urunler)
kontrol(n_skan >= SKAN_ART_TABAN,
        "Skan Art serisi BOS DEGIL (>= %d; bulunan: %d) — banner bos kategoriye link vermiyor"
        % (SKAN_ART_TABAN, n_skan))
# ⚠️ TAVAN + TOPLU-TASIMA capalari 24 Tem SON TURDA KALDIRILDI (bkz. SKAN_ART_TABAN notu):
# kumulatif olduklari icin seri 21. urune ulastiginda deploy'u KALICI kirmiziya cekiyorlardi.

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

# ATA ZINCIRI: cok bilesenli secicilerde ondeki bilesenler bu zincire dogrulanir
# (24 Tem yanlis-kirmizi: `.jen-banner-text a{display:none}` ROOT'a yaziliyordu).
ATALAR = ata_zinciri(index_html, m_ban.start() if m_ban else 0)
kontrol(any(a["etiket"] == "main" for a in ATALAR),
        "banner'in ata zinciri cikarilabildi (%s)"
        % " > ".join(a["etiket"] + ("#" + a["oz"]["id"] if a["oz"].get("id") else "")
                     for a in ATALAR))

kok_kural_tum = kok_kurallari(tum_kurallar, KOK, ATALAR)
kontrol(not COZULEMEYEN_SECICI,
        "banner ailesine deyen TUM seciciler ayristirilabildi (FAIL-CLOSED; cozulemeyen: %s)"
        % (sorted(set(COZULEMEYEN_SECICI)) or "-"))

# 🔴 KAPI EKSENI = HEDEF JETONU (24 Tem SON TUR). Gorunurluk + beyaz liste YALNIZ oznesi
# banner jetonu tasiyan kurallarda olculur; jetonsuz site-geneli seciciler (`a`, `*`,
# `main a`, yapisal seciciler) kaskada GIRMEZ. Gerekcesi ve bedeli: ozne_banner_jetonlu_mu().
kok_kural = [k for k in kok_kural_tum if ozne_banner_jetonlu_mu(k[2])]
jetonsuz_atlanan = [k[2] for k in kok_kural_tum if k not in kok_kural]
kontrol(len(kok_kural) >= 2,
        "banner ROOT'una uygulanan JETONLU kural bulundu (%d: %s | jetonsuz atlanan: %d)"
        % (len(kok_kural), [k[2] for k in kok_kural][:6], len(jetonsuz_atlanan)))

# UC KASKAD (her biri farkli soruya cevap verir):
#  TABAN    = kosulsuz + MEDYASIZ -> POZITIF tabanlar (yukseklik/genislik esikleri)
#  KOSULSUZ = durum-disi, medya DAHIL -> oldurucu kanallar + filtre + BEYAZ LISTE
#  DURUM    = :hover/:focus dahil -> YALNIZ oldurucu kanallar (display/visibility/opacity==0)
inline_stil = BANNER_OZ.get("style", "")
ETKIN_TABAN = etkin_stil(kok_kural, inline_stil, durumu_dahil_et=False, medyayi_dahil_et=False)
ETKIN = etkin_stil(kok_kural, inline_stil, durumu_dahil_et=False)
ETKIN_DURUM = etkin_stil(kok_kural, inline_stil, durumu_dahil_et=True)

taban_sorun = gorunurluk_sorunlari(ETKIN_TABAN, mod="taban")
kontrol(not taban_sorun,
        "banner ROOT'u KOSULSUZ (medyasiz) yukseklik/genislik tabanini sagliyor "
        "(asgari %dpx; sorun: %s)" % (BANNER_ASGARI_YUKSEKLIK_PX, taban_sorun or "-"))
sorunlar = gorunurluk_sorunlari(ETKIN, mod="kosulsuz")
kontrol(not sorunlar,
        "banner ROOT'u DINLENME halinde POZITIF gorunurluk olcumunu geciyor (sorun: %s)"
        % (sorunlar or "-"))
durum_sorun = gorunurluk_sorunlari(ETKIN_DURUM, mod="durum")
kontrol(not durum_sorun,
        "durum secicileri (:hover/:focus/:active) banner'i OLDURMUYOR — kismi opaklik mesru "
        "(sorun: %s)" % (durum_sorun or "-"))

if re.search(r"<a id=\"skanBanner\"[^>]*\shidden(?:\s|>|=)", banner_ac):
    kontrol(False, "banner HTML'inde `hidden` ozniteligi VAR")
kontrol(BANNER_OZ.get("aria-hidden") != "true", 'banner HTML\'inde aria-hidden="true" YOK')

# --- Metin sarmalayici cocuk: KOSULSUZ (medya disi) display:none = banner'i bosaltir.
# ⚠️ Cocuk ETIKET/-ust/-btn gizlemek (ozellikle @media icinde) MESRU responsive tasarimdir
# ve buraya GIRMEZ (24 Tem yanlis-kirmizi vakasi: @media(max-width:400px){.skan-banner-ust
# {display:none}} nobetciyi kirmiziya cekiyordu).
# ⚠️ 24 Tem ikinci yanlis-kirmizi: kural metin KUTUSUNU degil, KUTU ICINDEKI ikincil bir
# linki gizliyorsa (`.jen-banner-text a{display:none}`, `.skan-banner-text a.dip-not{...}`)
# bu MESRUDUR. Artik secici motoruna baglandi: kural yalniz OZNESI (subject bilesigi)
# .skan-banner-text / .jen-banner-text olan secicilerde sayilir; torun ozneleri atlanir.
METIN_SINIFLARI = {"skan-banner-text", "jen-banner-text"}


def metin_kutusu_oznesi_mi(tek_secici):
    bl = _bilesikler(tek_secici.strip())
    if not bl:
        return False
    d = bilesik_ayristir(bl[-1])
    if d is None:
        return bool(re.search(r"\.(?:skan|jen)-banner-text\b", bl[-1]))  # fail-closed
    if d["psel"]:
        return False           # ::before/::after AYRI kutu
    return bool(d["sinif"] & METIN_SINIFLARI)


metin_olduren = []
for secici, govde, medya in tum_kurallar:
    if medya:
        continue
    if not re.search(r"display\s*:\s*none", govde, re.I):
        continue
    for tek in _derinlik_bol(secici, ","):
        if metin_kutusu_oznesi_mi(tek):
            metin_olduren.append(tek.strip())
kontrol(not metin_olduren,
        "banner metin sarmalayicisi KOSULSUZ gizlenmemis (bulunan: %s)" % (metin_olduren or "-"))

# --- SARI TARAMASI: UC katman
#  1) banner HTML'i (inline stil + oznitelikler + metin)
#  2) KASKAD CIKTISI — banner ROOT'una GERCEKTEN uygulanan cozulmus degerler. Bu katman
#     jetonsuz sinif / yapisal secici yollarini kapatir (olculdu 24 Tem: sari_bulgular
#     yalniz "banner jetonu tasiyan kurallarda" tarayinca `.nordik-yama{background:#ffd400}`
#     ve `main > a:nth-of-type(2){background:#ffd400}` KACIYORDU).
#  3) SKAN banner ailesinin jetonlu kurallari — COCUK elemanlar icin EK katman (kaskad
#     yalniz ROOT'u modeller; .skan-banner-title vb. cocuklar buradan taranir).
#     ⚠️ 24 Tem SON TUR: bu katman artik YALNIZ skan-banner/skanBanner ailesini tarar.
#     jen-banner/jenBanner (PARAMETRIK seri = sarinin MESRU evi, CLAUDE.md) sari
#     denetiminin TAMAMEN DISINDADIR — gorunurluk denetimi onlar icin duruyor.
sari_kurallar = [(s, d) for (s, d, _m) in tum_kurallar if SARI_JETON.search(s)]
bulgu = sari_bulgular(banner_html)
cozulemeyen_var = []

# (2) GENIS kaskad: yapisal secici (`:nth-of-type`) ESLESMIS sayilir — sari kanadinda
# fazla-eslesme kabul edilir (banner'i sariya boyayan bir kural hicbir kosulda mesru degil).
kok_kural_genis = kok_kurallari(tum_kurallar, KOK, ATALAR, belirsiz=True,
                                cozulemeyeni_kaydet=False)
ETKIN_GENIS = etkin_stil(kok_kural_genis, inline_stil, durumu_dahil_et=True)
for ad, (deger, sec) in sorted(ETKIN_GENIS.items()):
    cozulmus, eksik = var_coz(deger, VAR_TANIM)
    cozulemeyen_var.extend(eksik)
    for b in sari_bulgular(cozulmus):
        bulgu.append("KASKAD %s{%s:%s} -> %s" % (sec, ad, cozulmus.strip()[:40], b))

# (3) SKAN banner ailesi (cocuklar dahil) — jen ailesi bu taramaya GIRMEZ
for sec, bildirimler in sari_kurallar:
    cozulmus, eksik = var_coz(bildirimler, VAR_TANIM)
    cozulemeyen_var.extend(eksik)
    for b in sari_bulgular(cozulmus):
        bulgu.append("%s -> %s" % (sec, b))
kontrol(not cozulemeyen_var,
        "SKAN banner ailesindeki HER var(--ad) cozulebildi (FAIL-CLOSED: cozulemeyen bir "
        "var() sari taranamaz demektir; cozulemeyen: %s)"
        % (sorted(set(cozulemeyen_var)) or "-"))

# (C4) COZULEMEYEN RENK KAYNAGI: base64 data-URI icindeki rengi hicbir tarayici goremez.
b64_kaynak = []
for etiket, metin in ([("banner HTML", banner_html)]
                      + [("kural " + s, d) for s, d in sari_kurallar]
                      + [("KASKAD " + a, v[0]) for a, v in sorted(ETKIN_GENIS.items())]):
    if re.search(r"url\(\s*['\"]?\s*data:[^)]*;\s*base64", metin, re.I):
        b64_kaynak.append(etiket)
kontrol(not b64_kaynak,
        "SKAN banner ailesinde base64 data-URI YOK (FAIL-CLOSED: icerigi taranamayan renk "
        "kaynagi; bulunan: %s)" % (b64_kaynak or "-"))
kontrol(not bulgu, "banner HTML + SKAN banner ailesi CSS'inde SARI token YOK (var() cozumlu; "
        "bulunan: %s)" % (sorted(set(bulgu)) or "-"))
# ⚠️ "var(--red) LITERALI zorunlu" maddesi 24 Tem SON TURDA KALDIRILDI. NEDEN: CLAUDE.md
# kirmizi aksani TAVSIYE ediyor, ZORUNLU kilmiyor; kural bir LITERAL METIN ariyordu ve
# gorunumu BIREBIR koruyan mesru refactor'lari (`.skan-banner{--skan-accent:#c0392b}` +
# `background:var(--skan-accent)`) ve aksan seridinin kaldirilmasini kirmiziya cekiyordu.

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

# ---------------------------------------------------------------- (f3) KAYNAK SOZLESMESI
# ⚠️ NEDEN SAHTE DOM DEGIL: JS ile gizleme/boyama sinifini sahte DOM'u buyuterek kapatmak
# YAPISAL olarak imkansiz (setTimeout, el.remove(), cssText, classList, Object.assign,
# requestAnimationFrame... hepsi ayri kacak). Bunun yerine UCUZ SOZLESME: banner
# elemanlarina index.html'de SADECE renderGrid'in toggle blogu dokunabilir. Baska bir
# yerden banner id'sine deyen HER satir kirmizi -> "JS ile gizle" + "JS ile sariya boya"
# siniflarinin TAMAMI tek kuralla kapanir. (node/DOM display olcumu IKINCI katman olarak kalir.)
print("(f3) kaynak sozlesmesi — banner id'lerine YALNIZ renderGrid toggle blogu dokunuyor")
rendergrid_src = js_fonksiyon(index_html, "renderGrid")
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


m_tog = re.search(r'\[\s*"(?:jen|skan)Banner"\s*,\s*"(?:jen|skan)Banner"\s*\]\s*'
                  r'\.\s*forEach\s*\(', index_html)
kontrol(m_tog is not None,
        'renderGrid icindeki banner toggle blogu bulundu (["jenBanner","skanBanner"].forEach)')
tog_bas = tog_son = -1
if m_tog:
    tog_bas = m_tog.start()
    tog_son = _dengeli_kapa(index_html, m_tog.end() - 1) or m_tog.end()
    toggle_src = index_html[tog_bas:tog_son]
    rg_ofset = index_html.find(rendergrid_src) if rendergrid_src else -1
    kontrol(rg_ofset != -1 and rg_ofset <= tog_bas < rg_ofset + len(rendergrid_src),
            "toggle blogu renderGrid GOVDESININ icinde (baska fonksiyona tasinmamis)")
    stil_ozellikleri = sorted(set(re.findall(r"\.style\s*\.\s*([-\w]+)\s*=", toggle_src))
                              | set(re.findall(r"\.style\s*\[\s*['\"]([-\w]+)['\"]\s*\]\s*=",
                                               toggle_src)))
    kontrol(stil_ozellikleri == ["display"],
            "toggle blogu YALNIZ .style.display yaziyor (bulunan: %s) — baska bir stil "
            "ozelligi buradan boyanamaz" % (stil_ozellikleri or "-"))
    kontrol(not re.search(r"\.style\s*\.\s*cssText|setAttribute\s*\(\s*['\"]style|"
                          r"classList|\.remove\s*\(\s*\)|Object\.assign", toggle_src),
            "toggle blogunda toplu-stil kacagi YOK (cssText / style ozniteligi / classList / "
            "remove() / Object.assign)")
    kontrol(not sari_bulgular(toggle_src),
            "toggle blogunda SARI token YOK (bulunan: %s)" % (sari_bulgular(toggle_src) or "-"))

sozlesme_disi = []
for m in re.finditer(r"(?:skan|jen)Banner", index_html):
    if not script_icinde(m.start()):
        continue                                   # HTML/CSS duzlemi -> CSS motoru olcuyor
    if tog_bas <= m.start() < tog_son:
        continue
    satir_no = index_html.count("\n", 0, m.start()) + 1
    satir = index_html.splitlines()[satir_no - 1].strip()
    sozlesme_disi.append("satir %d: %s" % (satir_no, satir[:110]))
kontrol(not sozlesme_disi,
        "index.html JS'inde banner id'sine toggle blogu DISINDAN dokunan satir YOK "
        "(bulunan: %s)" % (sozlesme_disi or "-"))

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
applyurl_src = js_fonksiyon(index_html, "applyUrlParams")   # rendergrid_src (f3)'te alindi

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
