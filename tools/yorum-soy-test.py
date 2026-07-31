#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YORUM SOYUCU KIRMIZI-MUTASYON KAPISI — soyucu KODU BOZARSA test kirmizi yanar.

    python3 tools/yorum-soy-test.py
    python3 tools/yorum-soy-test.py --ayrintili

NEDEN VAR (olculmus sessiz-hata sinifi): tools/yorum_soy.py, tarayiciya inen JS/HTML
kopyalarindan yorumlari soyar (build.py -> _yayin/ -> deploy). Soyucunun JS lexer'i
"su `/` regex mi bolme mi", "bu `//` dizge icinde mi", "bu `<!--` <script> govdesinde mi"
gibi SEZGILERE dayanir. Sezgi yanilirsa cikti SOZDIZIMSEL OLARAK GECERLI kalabilir ama
davranisi degisir -> hata odeme yolunda SESSIZDIR. `node --check` (build.py'nin ikinci
gozu) o sinifi GORMEZ.

BU KAPI IKI SEY OLCER:
  1. TUZAK FIKSTURLERI (bagimsiz ikinci goz): yorum_soy.py'nin KENDI kendini-testinden
     AYRI yazilmis, spec'in istedigi tuzak vakalari. Gercek modul hepsini gecmeli.
  2. KIRMIZI MUTASYON: yorum_soy.py KAYNAGINA (bellekte; DEPODAKI DOSYAYA DOKUNULMAZ)
     gercekci kusurlar enjekte edilir. Her mutant EN AZ BIR fikstur tarafindan
     YAKALANMALI. Yakalanmayan mutant = o davranisin nobetcisi YOK demektir -> exit 1.
  3. NO-OP NOBETI: yalnizca bir YORUM satirini degistiren mutant YAKALANMAMALI.
     (Yakalanirsa fiksturler gurultulu/yalanci kirmizidir; kapi kendi olcusunu kaybeder.)
  4. GERCEK VARLIK NOBETI: depodaki yayin JS varliklari fiilen soyulur ve cikti
     (a) orijinalin ALT DIZISI, (b) IDEMPOTENT, (c) node varsa `node --check` rc 0.

🔴 DEPODAKI DOSYA DEGISMEZ: mutasyonlar bellekte exec edilir, diske YAZILMAZ. (Bu betigin
oncesinde `.mut-yedek` dosyalari birakip dosyayi mutasyonlu halde unutan bir kosum
olculdu — 31 Tem, build.py `_yayin_yolu` mutanti calisir halde kalmisti. Bu yuzden
dosya-uzerinde mutasyon YASAK.)
"""
import io
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SOYUCU = os.path.join(TOOLS, "yorum_soy.py")

# Depodaki gercek yayin JS varliklari (build.py SOYULACAK_JS + uretilen ikisi).
GERCEK_VARLIKLAR = ("secenekler.js", "konfigur.js", "jenerator/hacim.js",
                    "jenerator/konfigurator.js", "jenerator/viewer.js")


def modul_yukle(kaynak, ad="yorum_soy_mutant"):
    """Kaynak METNI taze bir modul ad alanina exec eder (diske yazmaz)."""
    ns = {"__name__": ad, "__file__": SOYUCU}
    exec(compile(kaynak, SOYUCU, "exec"), ns)          # noqa: S102 — bilerek
    return ns


# ---------------------------------------------------------------- TUZAK FIKSTURLERI
# (ad, tur, girdi, beklenen_cikti). tur: "js" | "html"
# Bunlar yorum_soy.py'nin kendi iddialarindan BAGIMSIZ yazildi: ayni hatayi iki yerde
# tekrarlamamak icin ifadeler ve vakalar bilerek FARKLI secildi.
FIKSTURLER = [
    ("T1 dizgedeki `//` (URL) yorum sanilmaz",
     "js", 'var u = "https://pruvo3d.com/a"; var k = 1; // son\n',
     'var u = "https://pruvo3d.com/a"; var k = 1; \n'),

    ("T2 regex literali icindeki `/*` blok yorum sanilmaz",
     "js", "var r = x.replace(/[/*]/g, \"\"); var k = 2;\n",
     "var r = x.replace(/[/*]/g, \"\"); var k = 2;\n"),

    ("T3 sablon literali GOVDESINDEKI `//` yorum sanilmaz",
     "js", "var t = `bak // buraya`; var k = 3; // son\n",
     "var t = `bak // buraya`; var k = 3; \n"),

    ("T4 HTML yorumu silinir, govde kalir",
     "html", "<p>a</p><!-- ic not --><p>b</p>\n", "<p>a</p><p>b</p>\n"),

    ("T5 satir sonu OLMADAN biten `//` dosyasi",
     "js", "var k = 5; // son yorum, satir sonu yok", "var k = 5; "),

    ("T6 KOSUL parantezinden sonraki `/` REGEX'tir (icindeki // yorum degil)",
     "js", "if (a) /[//]/.test(s); var k = 6;\n", "if (a) /[//]/.test(s); var k = 6;\n"),

    ("T7 tek tirnakli dizgedeki `//` yorum sanilmaz",
     "js", "var u = 'http://a//b'; var k = 7; // son\n",
     "var u = 'http://a//b'; var k = 7; \n"),

    ("T8 kacisli ters bolu ile biten dizge erken kapanmaz",
     "js", 'var s = "yol\\\\"; var k = 8; // son\n', 'var s = "yol\\\\"; var k = 8; \n'),

    ("T9 sablon ${} KOD bolgesindeki yorum SOYULUR",
     "js", "var t = `a ${ b /* ic */ } c`;\n", "var t = `a ${ b   } c`;\n"),

    ("T10 tek satirlik blok yorum jetonlari BIRLESTIRMEZ",
     "js", "var y = a/* ara */b;\n", "var y = a b;\n"),

    ("T11 cok satirli blok yorumda SATIR SAYISI korunur (ASI)",
     "js", "var a = 1;/* bir\niki\nuc */\nvar b = 2;\n", "var a = 1;\n\n\nvar b = 2;\n"),

    ("T12 <textarea> ham metnindeki `<!--` YORUM DEGIL",
     "html", "<textarea><!-- gorunur --></textarea>\n",
     "<textarea><!-- gorunur --></textarea>\n"),

    ("T13 type=module <script> yorumu SOYULUR",
     "html", '<script type="module">var a = 1; // not\n</script>\n',
     '<script type="module">var a = 1; \n</script>\n'),

    ("T14 DEGER parantezinden sonraki `/` BOLME'dir (regex sanilmaz)",
     "js", "var y = (a + b) / c; var k = 14; // son\n",
     "var y = (a + b) / c; var k = 14; \n"),

    ("T15 JSON-LD blogu DOKUNULMAZ (ham metin, JS degil)",
     "html", '<script type="application/ld+json">{"a":"b // c"}</script>\n',
     '<script type="application/ld+json">{"a":"b // c"}</script>\n'),

    # T16/T17: KACIS ve KARAKTER SINIFI eksenleri. Bu ikisi olmadan M3/M4 mutantlari
    # (31 Tem olcumu) HICBIR fikstur tarafindan yakalanmiyordu -> nobetsiz davranis.
    ("T16 dizgedeki KACISLI TIRNAK dizgeyi erken kapatmaz",
     "js", 'var s = "a\\"b // c"; var k = 16;\n', 'var s = "a\\"b // c"; var k = 16;\n'),

    ("T17 regex KARAKTER SINIFI icindeki ardisik `/` kapanis/yorum sanilmaz",
     "js", "var r = /[///]/.test(s); var k = 17;\n", "var r = /[///]/.test(s); var k = 17;\n"),
]


def fikstur_kos(ns):
    """Modul ad alanini fiksturlere karsi kosar; [(ad, tamam_mi, gercek)] doner."""
    sonuc = []
    for ad, tur, girdi, beklenen in FIKSTURLER:
        fn = ns.get("js_soy") if tur == "js" else ns.get("html_soy")
        try:
            gercek = fn(girdi)
        except Exception as e:                                     # noqa: BLE001
            sonuc.append((ad, False, "ISTISNA: %r" % (e,)))
            continue
        sonuc.append((ad, gercek == beklenen, gercek))
    return sonuc


# ------------------------------------------------------------------- MUTASYONLAR
# (ad, eski_metin, yeni_metin). Hepsi yorum_soy.py'de GERCEKTEN duran capalar;
# capa bulunamazsa mutasyon "uygulanamadi" sayilir -> KAPI KIRMIZI (bayat mutant
# sessizce yesil vermez).
MUTASYONLAR = [
    ("M1 `(` sonrasi regex tanimi kalkti (regex bolme sanilir)",
     '_REGEX_ONCESI_NOKTALAMA = set("(,=:[!&|?{};+-*%~^<>")',
     '_REGEX_ONCESI_NOKTALAMA = set(",=:[!&|?{};+-*%~^<>")'),

    ("M2 KOSUL parantezi ayrimi kalkti (`if (x) /re/` bolme sanilir)",
     'or onceki == "" or (onceki == ")" and son_paren in _BASLIK_PARANTEZI):',
     'or onceki == "":'),

    ("M3 dizgede kacis dizisi tek karakter atlanir (kacisli tirnak erken kapatir)",
     '        if kaynak[i] == "\\\\":\n            i += 2\n            continue\n'
     '        if kaynak[i] == q:',
     '        if kaynak[i] == "\\\\":\n            i += 1\n            continue\n'
     '        if kaynak[i] == q:'),

    ("M4 regexte karakter sinifi ([...]) izlenmiyor (sinif icindeki / kapanis sanilir)",
     '        if c == "[":\n            sinif = True',
     '        if c == "[":\n            sinif = False'),

    ("M5 sablon ${...} kod bolgesi taninmiyor",
     'if kaynak[i:i + 2] == "${":',
     'if kaynak[i:i + 2] == "@{":'),

    ("M6 tek tirnakli dizge atlanmiyor (yalniz cift tirnak)",
     '        if c in "\\"\'":\n            i = _dizge_atla(kaynak, i)\n'
     '            onceki, onceki_ad = c, ""',
     '        if c in "\\"":\n            i = _dizge_atla(kaynak, i)\n'
     '            onceki, onceki_ad = c, ""'),

    ("M7 tek satirlik blok yorum BOSLUK birakmiyor (jetonlar birlesir)",
     '            parcalar.append("\\n" * satir if satir else " ")',
     '            parcalar.append("\\n" * satir if satir else "")'),

    ("M8 cok satirli blok yorumda satir sonlari korunmuyor (ASI kayar)",
     '            satir = kaynak[bas:bit].count("\\n")',
     '            satir = 0'),

    ("M9 ham-metin elemanlarindan textarea dusuruldu",
     '_HAM_ACILIS = re.compile(r"<(script|style|textarea|title)\\b([^>]*)>", re.I)',
     '_HAM_ACILIS = re.compile(r"<(script|style|title)\\b([^>]*)>", re.I)'),

    ("M10 type=module JS sayilmiyor (modul script yorumu soyulmaz)",
     '    "", "text/javascript", "application/javascript", "module",',
     '    "", "text/javascript", "application/javascript",'),
]

# NO-OP: yalniz bir YORUM satirini degistirir. YAKALANMAMALI.
NOOP = ("N0 (no-op) yalniz yorum metni degisti",
        "# ---------------------------------------------------------------- JS lexer",
        "# ---------------------------------------------------------------- JS cozumleyici")


def main():
    ayrintili = "--ayrintili" in sys.argv[1:]
    kaynak = io.open(SOYUCU, encoding="utf-8").read()
    hata = 0
    R = []

    # ---- 1) GERCEK MODUL tum fiksturleri gecmeli
    gercek = fikstur_kos(modul_yukle(kaynak, "yorum_soy_gercek"))
    kirik = [(a, g) for a, ok, g in gercek if not ok]
    R.append("FIKSTUR: %d/%d gecti (gercek modul)" % (len(gercek) - len(kirik), len(gercek)))
    for a, g in kirik:
        hata += 1
        R.append("  HATA %s -> %r" % (a, g))

    # ---- 2) KIRMIZI MUTASYON: her mutant EN AZ BIR fikstur tarafindan yakalanmali
    yakalanan = 0
    for ad, eski, yeni in MUTASYONLAR:
        if eski not in kaynak:
            hata += 1
            R.append("  HATA %s -> CAPA BULUNAMADI (mutant bayat; kapi olculemez)" % ad)
            continue
        mutant = kaynak.replace(eski, yeni, 1)
        try:
            ns = modul_yukle(mutant, "yorum_soy_m")
            sonuclar = fikstur_kos(ns)
            dusenler = [a for a, ok, _g in sonuclar if not ok]
        except Exception as e:                                     # noqa: BLE001
            dusenler = ["(yukleme istisnasi: %r)" % (e,)]
        if dusenler:
            yakalanan += 1
            if ayrintili:
                R.append("  OK   %s -> yakalayan: %s" % (ad, ", ".join(dusenler[:3])))
        else:
            hata += 1
            R.append("  HATA %s -> HICBIR FIKSTUR YAKALAMADI (nobetsiz davranis)" % ad)
    R.append("MUTASYON: %d/%d mutant yakalandi (asgari 6 sart)"
             % (yakalanan, len(MUTASYONLAR)))
    if yakalanan < 6:
        hata += 1
        R.append("  HATA yakalanan mutant sayisi 6'nin ALTINDA")

    # ---- 3) NO-OP NOBETI: yorum degisikligi YAKALANMAMALI
    ad, eski, yeni = NOOP
    if eski not in kaynak:
        hata += 1
        R.append("  HATA %s -> CAPA BULUNAMADI" % ad)
    else:
        dusen = [a for a, ok, _g in fikstur_kos(modul_yukle(kaynak.replace(eski, yeni, 1),
                                                            "yorum_soy_noop")) if not ok]
        if dusen:
            hata += 1
            R.append("  HATA %s -> YAKALANDI (%s) — fiksturler gurultulu" % (ad, dusen[0]))
        else:
            R.append("NO-OP: yorum degisikligi yakalanmadi (kapi gurultusuz)")

    # ---- 4) GERCEK VARLIK NOBETI
    ns = modul_yukle(kaynak, "yorum_soy_gercek2")
    js_soy = ns["js_soy"]
    node_var = True
    try:
        subprocess.run(["node", "--version"], capture_output=True)
    except OSError:
        node_var = False
    soyulan, silinen_satir, bayt_fark = 0, 0, 0
    for rel in GERCEK_VARLIKLAR:
        yol = os.path.join(ROOT, rel)
        if not os.path.isfile(yol):
            hata += 1
            R.append("  HATA gercek varlik YOK -> %s" % rel)
            continue
        metin = io.open(yol, encoding="utf-8").read()
        cikti = js_soy(metin)
        soyulan += 1
        bayt_fark += len(metin.encode("utf-8")) - len(cikti.encode("utf-8"))
        silinen_satir += sum(1 for a, b in zip(metin.split("\n"), cikti.split("\n"))
                             if a != b)
        if not alt_dizi_mi(cikti, metin):
            hata += 1
            R.append("  HATA %s -> cikti orijinalin ALT DIZISI degil (karakter uydurulmus)" % rel)
        if js_soy(cikti) != cikti:
            hata += 1
            R.append("  HATA %s -> soyma IDEMPOTENT degil (ikinci gecis degistirdi)" % rel)
        if metin.count("\n") != cikti.count("\n"):
            hata += 1
            R.append("  HATA %s -> satir sayisi degisti (%d -> %d)"
                     % (rel, metin.count("\n"), cikti.count("\n")))
        if node_var and not node_check(cikti):
            hata += 1
            R.append("  HATA %s -> soyulmus cikti `node --check`ten GECMEDI" % rel)
    R.append("GERCEK VARLIK: %d dosya soyuldu | degisen satir=%d | bayt farki=%d | node=%s"
             % (soyulan, silinen_satir, bayt_fark, "var" if node_var else "YOK (atlandi)"))

    print("\n".join(R))
    print("yorum-soy-test: %s" % ("KIRMIZI (%d bulgu)" % hata if hata else "YESIL"))
    return 1 if hata else 0


def alt_dizi_mi(kucuk, buyuk):
    """kucuk, buyuk'un (sirali) ALT DIZISI mi — soyucu yeni karakter uydurmamali."""
    it = iter(buyuk)
    return all(c in it for c in kucuk)


def node_check(metin):
    fd, yol = tempfile.mkstemp(suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(metin)
        p = subprocess.run(["node", "--check", yol], capture_output=True)
        return p.returncode == 0
    finally:
        os.unlink(yol)


if __name__ == "__main__":
    sys.exit(main())
