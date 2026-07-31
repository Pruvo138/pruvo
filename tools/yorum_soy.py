#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YORUM SOYUCU — yayin kopyasindan (tarayiciya INEN metinden) yorumlari cikarir.

NEDEN VAR (yapisal cozum, 31 Tem 2026):
  tools/yayin-ic-dil-kapisi.py bir SAVUNMA katmanidir: yayin ciktisinin YORUM
  yuzeyinde ic gelistirici dili bulursa YAYINI DURDURUR. Ama o kapi ancak
  yakalar — bir sonraki yorum yine ayni tuzaga duser ve yayin durur. Asil cozum
  yorumun tarayiciya HIC INMEMESIDIR: kaynakta tam muhendislik dokumantasyonu
  KALIR (mimar/muhendis okur), yayin kopyasindan SOYULUR.
  Olculdu (build.py ciktisinin tamami, 15.588 yayin dosyasi): 1.027,9 MB yayin
  metninin 143,4 MB'i (%13,9) YORUM. Tipik urun sayfasi 68,7 KB'in 9,7 KB'i.

🔴 SOZLESME: DAVRANIS DEGISMEZ.
  * Tek satirlik yorum (//...) govdesi silinir, SONUNDAKI satir sonu KALIR.
  * Blok yorum (/*...*/) icinde satir sonu VARSA yerine AYNI SAYIDA "\n" konur.
    Sebep: spec geregi icinde LineTerminator gecen bir MultiLineComment, ASI
    (otomatik noktali virgul) icin satir sonu SAYILIR. Bosluga cevirmek
    `return/*\n*/x` gibi bir yerde davranisi DEGISTIRIRDI.
  * Satir sonu TASIMAYAN blok yorum yerine TEK BOSLUK konur (token birlesmesin:
    `a/*x*/b` -> `a b`, ASLA `ab`).
  Boylece satir NUMARALARI da korunur (yigin izleri kaymaz).

BEYAN EDILEN SINIR (kapsam disi — bilerek):
  1. `<script>` etiketi YALNIZ tur'u JS olan (type yok / text/javascript /
     application/javascript / module) bloklarda soyulur. JSON-LD
     (application/ld+json), `text/template` vb. bloklara DOKUNULMAZ: onlar JS
     DEGILDIR, JS lexer'i orada anlamsizdir.
  2. HTML kosullu yorumu (`<!--[if ...`) KORUNUR.
  3. `<script>/<style>/<textarea>/<title>` ham-metin bolgelerinde HTML yorumu
     ARANMAZ (spec: orada `<!--` yorum degil, metindir).
  4. Elle yazilmis 4 statik yasal sayfa (hakkimizda/iletisim/sss/gizlilik)
     build.py tarafindan SOYULMAZ — onlar commit'li kaynaktir ve
     tools/yasal-sayfa-drift-kapisi.py bayt-esitlik ister. Onlarin nobetcisi
     tools/yayin-ic-dil-kapisi.py'dir (ic-dil ekseni). Bu sinir kasitlidir.
  5. ATLANAN (kacan) iki HTML sekli — OLCULDU 31 Tem, ikisi de "yorum KALIR",
     hicbiri "kod bozulur" DEGIL (soyucu fail-safe tarafa duser):
       a. HTML yorumunun ICINDE `<script>` gecerse (`<!-- <script>…</script> -->`)
          o HTML yorumu SOYULMAZ (ham-metin taramasi once eslesir).
          Ölçüldü: govde bozulmaz, yalniz yorum kalir.
       b. `<script data-x="a>b">` gibi ozniteliginde `>` tasiyan etiket: etiket
          siniri yanlis okunur, o blogun JS yorumu SOYULMAZ.
     IKISI DE SESSIZ DEGIL: kalan yorum yayin ciktisinda durur ve
     tools/yayin-ic-dil-kapisi.py o yuzeyi olcer -> ic dil tasiyorsa CI KIRMIZI.
     Yani soyma bir yeri kacirirsa savunma katmani hala nobettedir.

BAGIMSIZ IKINCI GOZ (fail-closed): build.py her _yayin/<x>.js kopyasini
  `node --check`'ten gecirir. Bu lexer'in regex/bolme SEZGISI bir gun yanilirsa
  bozuk cikti YAYINLANMADAN build durur (bkz. build.py:_yayin_js_sozdizimi).

JS LEXER — neden naif regex OLMAZ:
  Dizge/sablon/regex literali icindeki `//` ya da `/*` YORUM DEGILDIR
  ("https://...", /[/*]/, `a /* b */ c`). Naif soyma KODU BOZAR. Bu lexer
  dizge (' " `), sablon icindeki ${...} yuvalamasi ve regex literali farkindadir;
  regex/bolme ayrimi ONCEKI ANLAMLI JETONA bakar (noktalama + JS anahtar
  sozcukleri).

Kullanim (kutuphane):
    from yorum_soy import js_soy, css_soy, html_soy
Kendini test:
    python3 tools/yorum_soy.py --kendini-test
"""
import re
import sys

# ---------------------------------------------------------------- JS lexer
# `/` bir REGEX baslatir mi? Onceki anlamli jeton bu kumedeyse EVET.
_REGEX_ONCESI_NOKTALAMA = set("(,=:[!&|?{};+-*%~^<>")
# Anahtar sozcukten SONRA gelen `/` daima regex'tir (`return /a/.test(x)`).
_REGEX_ONCESI_ANAHTAR = frozenset((
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "throw", "case", "do", "else", "yield", "await", "print",
))
# `)` SONRASI `/`: kural cift yonlu ve ikisi de gercek kodda gecer —
#   `(a + b) / c`        -> BOLME  (parantez bir DEGERI kapatir)
#   `if (x) /re/.test(s)` -> REGEX  (parantez bir KOSUL basligini kapatir)
# Ayrim, o parantezi ACAN jetondan gelir: basliksa (if/while/for/with) regex,
# degilse bolme. Bu ayrim olmadan `if (x) /[//]/` gibi bir satirda regex icindeki
# `//` YORUM sanilip satirin kalani SILINIRDI (kod bozulur).
_BASLIK_PARANTEZI = frozenset(("if", "while", "for", "with"))
_AD_KARAKTERI = re.compile(r"[A-Za-z0-9_$]")


def js_yorum_araliklari(kaynak):
    """[(bas, son, tur)] — JS kaynagindaki yorumlarin indeks araliklari; tur:
    "satir" (`//` ... satir sonundan ONCE) | "blok" (`/*` ... `*/` dahil).
    Dizge/sablon/regex literalleri ATLANIR.
    """
    araliklar = []
    i, n = 0, len(kaynak)
    onceki = ""          # son anlamli karakter
    onceki_ad = ""       # son anlamli TANIMLAYICI (anahtar sozcuk ayrimi icin)
    # Sablon literali yuvalanmasi: ${ ... } icinde yeniden kod baslar.
    sablon_yigini = []   # her eleman: acik suslu parantez sayaci
    paren_yigini = []    # her `(` icin onunde duran tanimlayici (if/while/for/with?)
    son_paren = ""       # en son KAPANAN parantezi acan jeton
    while i < n:
        c = kaynak[i]
        ikili = kaynak[i:i + 2]

        # --- sablon ${...} icindeyken suslu parantez sayimi
        if sablon_yigini and c == "{" and ikili != "/*":
            sablon_yigini[-1] += 1
        elif sablon_yigini and c == "}":
            if sablon_yigini[-1] == 0:
                # ${...} kapandi -> sablon govdesine geri don
                sablon_yigini.pop()
                i = _sablon_devam(kaynak, i + 1, sablon_yigini)
                onceki, onceki_ad = "`", ""
                continue
            sablon_yigini[-1] -= 1

        if ikili == "//":
            j = kaynak.find("\n", i)
            j = n if j < 0 else j
            araliklar.append((i, j, "satir"))
            i = j
            continue
        if ikili == "/*":
            j = kaynak.find("*/", i + 2)
            j = n if j < 0 else j + 2
            araliklar.append((i, j, "blok"))
            i = j
            continue
        if c in "\"'":
            i = _dizge_atla(kaynak, i)
            onceki, onceki_ad = c, ""
            continue
        if c == "`":
            i = _sablon_devam(kaynak, i + 1, sablon_yigini)
            onceki, onceki_ad = "`", ""
            continue
        if c == "/":
            if onceki in _REGEX_ONCESI_NOKTALAMA or onceki_ad in _REGEX_ONCESI_ANAHTAR \
                    or onceki == "" or (onceki == ")" and son_paren in _BASLIK_PARANTEZI):
                i = _regex_atla(kaynak, i)
                onceki, onceki_ad = "/", ""
                continue
            onceki, onceki_ad = "/", ""
            i += 1
            continue
        if c == "(":
            paren_yigini.append(onceki_ad)
            onceki, onceki_ad = "(", ""
            i += 1
            continue
        if c == ")":
            son_paren = paren_yigini.pop() if paren_yigini else ""
            onceki, onceki_ad = ")", ""
            i += 1
            continue
        if _AD_KARAKTERI.match(c):
            j = i
            while j < n and _AD_KARAKTERI.match(kaynak[j]):
                j += 1
            onceki_ad = kaynak[i:j]
            onceki = kaynak[j - 1]
            i = j
            continue
        if not c.isspace():
            onceki, onceki_ad = c, ""
        i += 1
    return araliklar


def _dizge_atla(kaynak, i):
    """kaynak[i] tirnak ile baslayan dizgeyi atlar; kapanistan SONRAKI indeksi doner."""
    q = kaynak[i]
    n = len(kaynak)
    i += 1
    while i < n:
        if kaynak[i] == "\\":
            i += 2
            continue
        if kaynak[i] == q:
            return i + 1
        i += 1
    return n


def _sablon_devam(kaynak, i, sablon_yigini):
    """Sablon literali GOVDESINI tarar. `${` gorunce yigina basar ve kodun devam
    edecegi indeksi doner; sablon duz kapanirsa kapanistan sonraki indeksi doner."""
    n = len(kaynak)
    while i < n:
        if kaynak[i] == "\\":
            i += 2
            continue
        if kaynak[i:i + 2] == "${":
            sablon_yigini.append(0)
            return i + 2
        if kaynak[i] == "`":
            return i + 1
        i += 1
    return n


def _regex_atla(kaynak, i):
    """kaynak[i] == '/' regex literalini atlar; kapanis + bayraklardan sonraki indeksi doner."""
    n = len(kaynak)
    i += 1
    sinif = False
    while i < n:
        c = kaynak[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            sinif = True
        elif c == "]":
            sinif = False
        elif c == "\n":
            return i                       # kapanmamis regex: satirda biter (bozuk kod)
        elif c == "/" and not sinif:
            i += 1
            while i < n and _AD_KARAKTERI.match(kaynak[i]):
                i += 1                     # bayraklar (gimsuy)
            return i
        i += 1
    return n


def _araliklari_sil(kaynak, araliklar):
    """Verilen yorum araliklarini DAVRANIS KORUYARAK cikarir.

    satir yorumu (`//`)  -> BOS dize (aralik satir sonundan ONCE biter; o satir
                            sonu zaten jetonlari ayirir, bosluk gerekmez)
    cok satirli blok     -> icindeki satir sonu SAYISI kadar "\n" (ASI korunur:
                            spec'e gore satir sonu tasiyan blok yorum
                            LineTerminator SAYILIR)
    tek satirlik blok    -> TEK BOSLUK (token birlesmesini onler: a/*x*/b -> a b)
    """
    if not araliklar:
        return kaynak
    parcalar = []
    son = 0
    for bas, bit, tur in araliklar:
        parcalar.append(kaynak[son:bas])
        if tur == "satir":
            parcalar.append("")
        else:
            satir = kaynak[bas:bit].count("\n")
            parcalar.append("\n" * satir if satir else " ")
        son = bit
    parcalar.append(kaynak[son:])
    return "".join(parcalar)


def js_soy(kaynak):
    """JS kaynagindan yorumlari cikarir (davranis + satir numarasi korunur)."""
    return _araliklari_sil(kaynak, js_yorum_araliklari(kaynak))


# ---------------------------------------------------------------- CSS lexer
def css_yorum_araliklari(kaynak):
    """[(bas, son, tur)] — CSS yorumlari. Dizge ('/") ve url(...) icindekiler ATLANIR."""
    araliklar = []
    i, n = 0, len(kaynak)
    while i < n:
        c = kaynak[i]
        if kaynak[i:i + 2] == "/*":
            j = kaynak.find("*/", i + 2)
            j = n if j < 0 else j + 2
            araliklar.append((i, j, "blok"))
            i = j
            continue
        if c in "\"'":
            i = _dizge_atla(kaynak, i)
            continue
        if kaynak[i:i + 4].lower() == "url(":
            j = kaynak.find(")", i + 4)
            i = n if j < 0 else j + 1
            continue
        i += 1
    return araliklar


def css_soy(kaynak):
    return _araliklari_sil(kaynak, css_yorum_araliklari(kaynak))


# ---------------------------------------------------------------- HTML
# Ham-metin (raw text) elemanlari: icinde `<!--` YORUM DEGILDIR.
_HAM_METIN = ("script", "style", "textarea", "title")
_HAM_ACILIS = re.compile(r"<(script|style|textarea|title)\b([^>]*)>", re.I)
_JS_TURU = re.compile(
    r"""type\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)
_JS_GECERLI = frozenset((
    "", "text/javascript", "application/javascript", "module",
    "text/ecmascript", "application/ecmascript", "text/jscript",
))


def _script_turu_js_mi(oznitelikler):
    m = _JS_TURU.search(oznitelikler or "")
    if not m:
        return True                              # type yok -> klasik JS
    tur = (m.group(1) or m.group(2) or m.group(3) or "").strip().lower()
    return tur in _JS_GECERLI


def html_soy(kaynak):
    """HTML yayin kopyasindan yorumlari cikarir:
       * HTML yorumu <!-- ... --> (kosullu yorum `<!--[if` KORUNUR)
       * <style> icindeki CSS yorumlari
       * <script> icindeki JS yorumlari (YALNIZ JS tur'unde)
       Ham-metin bolgelerinde HTML yorumu ARANMAZ."""
    cikti = []
    i, n = 0, len(kaynak)
    while i < n:
        m = _HAM_ACILIS.search(kaynak, i)
        if not m:
            cikti.append(_html_yorum_soy(kaynak[i:]))
            break
        cikti.append(_html_yorum_soy(kaynak[i:m.start()]))
        etiket = m.group(1).lower()
        oznitelik = m.group(2)
        kapanis = re.compile(r"</%s\s*>" % etiket, re.I)
        km = kapanis.search(kaynak, m.end())
        son = km.start() if km else n
        govde = kaynak[m.end():son]
        if etiket == "style":
            govde = css_soy(govde)
        elif etiket == "script" and _script_turu_js_mi(oznitelik):
            govde = js_soy(govde)
        cikti.append(m.group(0))
        cikti.append(govde)
        if km:
            cikti.append(km.group(0))
            i = km.end()
        else:
            i = n
    return "".join(cikti)


_HTML_YORUM = re.compile(r"<!--(.*?)-->", re.S)


def _html_yorum_soy(parca):
    def _degistir(m):
        if m.group(1).lstrip().startswith("["):      # kosullu yorum -> KORU
            return m.group(0)
        return "\n" * m.group(0).count("\n")
    return _HTML_YORUM.sub(_degistir, parca)


def soy(yol_veya_uzanti, metin):
    """Uzantiya gore dogru soyucuyu secer."""
    if yol_veya_uzanti.endswith(".js"):
        return js_soy(metin)
    if yol_veya_uzanti.endswith(".css"):
        return css_soy(metin)
    return html_soy(metin)


# ------------------------------------------------------------ kendini test
_IDDIA = []


def _iddia(ad, kosul, ek=""):
    _IDDIA.append((ad, bool(kosul), ek))


def kendini_test():                                                # noqa: C901
    # ---- A. TEMEL SOYMA
    _iddia("A1 // yorumu silinir, satir sonu KALIR",
           js_soy("var a=1; // not\nvar b=2;\n") == "var a=1; \nvar b=2;\n",
           repr(js_soy("var a=1; // not\nvar b=2;\n")))
    _iddia("A2 tek satirlik blok yorum -> TEK BOSLUK (token birlesmez)",
           js_soy("a/*x*/b") == "a b", repr(js_soy("a/*x*/b")))
    _iddia("A3 cok satirli blok yorum -> AYNI SAYIDA satir sonu (ASI korunur)",
           js_soy("return/*\n\n*/x") == "return\n\nx", repr(js_soy("return/*\n\n*/x")))
    _iddia("A4 yorumsuz kaynak DEGISMEZ",
           js_soy("var a = 1;\n") == "var a = 1;\n")

    # ---- B. DIZGE / SABLON / REGEX BAGISIKLIGI (naif regex'in KIRDIGI yerler)
    kt = 'var u = "https://pruvo3d.com/a"; // yorum\n'
    _iddia("B1 dizge icindeki // YORUM DEGIL",
           js_soy(kt) == 'var u = "https://pruvo3d.com/a"; \n', repr(js_soy(kt)))
    kt = "var s = 'a /* b */ c';\n"
    _iddia("B2 tek tirnakli dizge icindeki /* */ YORUM DEGIL", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var t = `sablon /* icinde */ metin`;\n"
    _iddia("B3 sablon icindeki /* */ YORUM DEGIL", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var r = /[/*]/;\n"
    _iddia("B4 regex SINIFI icindeki /* YORUM DEGIL", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var r = /http:\\/\\/x/;\n"
    _iddia("B5 regex icindeki \\/\\/ YORUM DEGIL", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "if (a) return /ab\\/\\/c/.test(s);\n"
    _iddia("B6 `return` SONRASI / regex'tir (bolme degil)", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var x = a / b; // bolme\n"
    _iddia("B7 gercek BOLME regex sanilmaz",
           js_soy(kt) == "var x = a / b; \n", repr(js_soy(kt)))
    kt = "var t = `dis ${ \"ic // dizge\" } son`;\n"
    _iddia("B8 sablon ${} icindeki dizgede // YORUM DEGIL", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var t = `a ${ b } c`; // son\n"
    _iddia("B9 sablon ${} KAPANDIKTAN sonra govde yeniden sablondur",
           js_soy(kt) == "var t = `a ${ b } c`; \n", repr(js_soy(kt)))
    kt = "var t = `a ${ `ic ${ x } tek` } b`;\n"
    _iddia("B10 YUVALANMIS sablon bozulmaz", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var t = `a ${ {k:1} } b`;\n"
    _iddia("B11 sablon ${} icindeki obje suslusu kapanisi yanlis okumaz",
           js_soy(kt) == kt, repr(js_soy(kt)))
    kt = 'var s = "kacisli \\" tirnak // degil";\n'
    _iddia("B12 kacisli tirnak dizgeyi erken kapatmaz", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var t = `sablon\niki satir`; /* yorum */\n"
    _iddia("B13 cok satirli sablon govdesi korunur",
           js_soy(kt) == "var t = `sablon\niki satir`;  \n", repr(js_soy(kt)))

    # ---- B2. `)` SONRASI `/` — BOLME mi REGEX mi (parantezi ACAN jetondan)
    #      Bu aile 31 Tem'de EKLENDI: onceki surum `if (x) /[//]/` satirinda regex
    #      icindeki `//`yi YORUM sanip satirin kalanini SILIYORDU (sessiz kod bozma).
    kt = "if (x) /[//]/.test(s); // yorum\n"
    _iddia("B14 KOSUL parantezinden sonra `/` REGEX'tir (icindeki // yorum DEGIL)",
           js_soy(kt) == "if (x) /[//]/.test(s); \n", repr(js_soy(kt)))
    kt = "while (i--) /a\\/*b/.test(s);\n"
    _iddia("B15 while(...) sonrasi regex icindeki /* yorum DEGIL",
           js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "for (;;) /[/*]/.exec(s);\n"
    _iddia("B16 for(...) sonrasi regex icindeki /* yorum DEGIL", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var y = (a + b) / c; // bolme\n"
    _iddia("B17 DEGER parantezinden sonra `/` BOLME'dir (regex sanilmaz)",
           js_soy(kt) == "var y = (a + b) / c; \n", repr(js_soy(kt)))
    kt = "var y = f(a) / 2; // bolme\n"
    _iddia("B18 fonksiyon cagrisindan sonra `/` BOLME'dir",
           js_soy(kt) == "var y = f(a) / 2; \n", repr(js_soy(kt)))
    kt = "if (a) { x(); } /[//]/.test(s);\n"
    _iddia("B19 blok kapanisindan sonra `/` REGEX'tir", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var r = /a/.test(s) / 2; // bolme\n"
    _iddia("B20 regex SONRASI bolme dogru okunur",
           js_soy(kt) == "var r = /a/.test(s) / 2; \n", repr(js_soy(kt)))
    kt = "if (f(g(x))) /[//]/.test(s);\n"
    _iddia("B21 IC ICE parantezde baslik jetonu KAYBOLMAZ", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = 'var s = "a\\\\"; // yorum\n'
    _iddia("B22 kacisli TERS BOLU ile biten dizge erken kapanmaz",
           js_soy(kt) == 'var s = "a\\\\"; \n', repr(js_soy(kt)))
    kt = "var t = `a ${ /[/]/.test(x) } b`; // son\n"
    _iddia("B23 sablon ${} icindeki REGEX bozulmaz",
           js_soy(kt) == "var t = `a ${ /[/]/.test(x) } b`; \n", repr(js_soy(kt)))
    kt = 'var t = `a ${ "}" } b`;\n'
    _iddia("B24 sablon ${} icindeki dizgedeki } kapanis sanilmaz", js_soy(kt) == kt, repr(js_soy(kt)))
    kt = "var u = 'http://a//b'; var v = 'x'; // son\n"
    _iddia("B25 dizgedeki cift // sonrasi KOD hayatta kalir",
           js_soy(kt) == "var u = 'http://a//b'; var v = 'x'; \n", repr(js_soy(kt)))

    # ---- C. SABLON ICINDE GERCEK yorum (kod bolgesinde) SOYULUR
    kt = "var t = `a ${ b /* not */ } c`;\n"
    _iddia("C1 sablon ${} KOD bolgesindeki yorum SOYULUR",
           js_soy(kt) == "var t = `a ${ b   } c`;\n", repr(js_soy(kt)))

    # ---- D. CSS
    _iddia("D1 CSS yorumu silinir",
           css_soy(".a{color:red} /* not */\n") == ".a{color:red}  \n",
           repr(css_soy(".a{color:red} /* not */\n")))
    kt = '.a::after{content:"/*"}\n'
    _iddia("D2 CSS dizgesi icindeki /* YORUM DEGIL", css_soy(kt) == kt, repr(css_soy(kt)))
    kt = '.a{background:url(/img/a_/*_b.png)}\n'
    _iddia("D3 url() icindeki /* YORUM DEGIL", css_soy(kt) == kt, repr(css_soy(kt)))

    # ---- E. HTML
    kt = "<body><!-- not --><p>x</p></body>"
    _iddia("E1 HTML yorumu silinir",
           html_soy(kt) == "<body><p>x</p></body>", repr(html_soy(kt)))
    kt = "<!--[if IE]><p>x</p><![endif]-->"
    _iddia("E2 KOSULLU yorum KORUNUR", html_soy(kt) == kt, repr(html_soy(kt)))
    kt = '<script type="application/ld+json">{"a":"b//c","d":"/*x*/"}</script>'
    _iddia("E3 JSON-LD blogu DOKUNULMAZ", html_soy(kt) == kt, repr(html_soy(kt)))
    kt = '<script>var a=1; // not\n</script>'
    _iddia("E4 JS <script> yorumu SOYULUR",
           html_soy(kt) == '<script>var a=1; \n</script>', repr(html_soy(kt)))
    kt = '<script type="module">var a=1; /* n */ var b=2;</script>'
    _iddia("E5 type=module JS sayilir",
           html_soy(kt) == '<script type="module">var a=1;   var b=2;</script>', repr(html_soy(kt)))
    kt = '<style>.a{color:red}/* n */</style>'
    _iddia("E6 <style> CSS yorumu SOYULUR",
           html_soy(kt) == '<style>.a{color:red} </style>', repr(html_soy(kt)))
    kt = '<textarea><!-- bu METIN --></textarea>'
    _iddia("E7 <textarea> ham metni DOKUNULMAZ", html_soy(kt) == kt, repr(html_soy(kt)))
    kt = '<script>var s = "<!-- dizge -->";</script>'
    _iddia("E8 <script> icindeki <!-- HTML yorumu SANILMAZ",
           html_soy(kt) == kt, repr(html_soy(kt)))
    kt = '<title><!-- baslik --></title>'
    _iddia("E9 <title> ham metni DOKUNULMAZ", html_soy(kt) == kt, repr(html_soy(kt)))
    kt = "<p>a</p>\n<!-- cok\nsatirli\nyorum -->\n<p>b</p>"
    _iddia("E10 cok satirli HTML yorumu -> satir sayisi korunur",
           html_soy(kt) == "<p>a</p>\n\n\n\n<p>b</p>", repr(html_soy(kt)))

    # ---- F. IDEMPOTENS + YORUM SAYISI 0
    ornek = ('<html><head><style>/* a */.x{color:red}</style></head><body>'
             '<!-- b --><script>var u="//x"; // c\n/* d */var v=1;</script>'
             '<script type="application/ld+json">{"u":"https://a/b"}</script></body></html>')
    bir = html_soy(ornek)
    _iddia("F1 soyma IDEMPOTENT (ikinci gecis DEGISTIRMEZ)", html_soy(bir) == bir)
    _iddia("F2 soyulmus JS'te yorum araligi KALMAZ",
           js_yorum_araliklari(js_soy('var u="//x"; // c\n/* d */var v=1;')) == [])

    # ---- G. GERI ALINAMAZ BOZULMA NOBETI: soyulmus metin ORIJINALIN ALT DIZISI
    #        (yalniz SILME + bosluk/satir sonu; hicbir yeni karakter uydurulmaz)
    def _yalniz_silme(orj, yeni):
        it = iter(orj)
        return all(any(c == o for o in it) for c in yeni.replace("\n", "").replace(" ", ""))
    _iddia("G1 soyulmus govde orijinalin ALT DIZISI (yeni karakter uydurulmaz)",
           _yalniz_silme(ornek, bir))

    gecen = sum(1 for _a, k, _e in _IDDIA if k)
    for ad, k, ek in _IDDIA:
        print("  %s %s%s" % ("OK  " if k else "HATA", ad, ("   [%s]" % ek) if not k else ""))
    print("\nkendini-test: %d/%d" % (gecen, len(_IDDIA)))
    return 0 if gecen == len(_IDDIA) else 1


if __name__ == "__main__":
    if "--kendini-test" in sys.argv[1:]:
        sys.exit(kendini_test())
    sys.stdout.write(soy(sys.argv[1] if len(sys.argv) > 1 else ".html",
                         sys.stdin.read()))
