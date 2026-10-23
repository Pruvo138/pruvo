#!/usr/bin/env python3
"""KVKK riza bandi ESITLIK testi (BaBa 22 Eki 17:1x + 16:4x (a)).

    python3 tools/riza-bandi-esitlik-test.py

Bant 6 yerde durur: tools/build.py::GA_BANNER_SNIPPET (uretilen her sayfa) + 5 statik sayfa
(index / iletisim / sss / gizlilik / hakkimizda). Bu test bandin KAYNAK metnini okur (ag YOK,
build YOK) ve su iddialari fail-closed olcer:

  E1 6 kopyanin bant blogu (yorum basligi -> bant </script>) BAYT-ESIT; kopya sayisi TAM 6.
  E2 .pco-kabul ve .pco-ret bildirimleri ESIT: padding · font-size · font-weight ·
     border-radius · min-height · min-width (ayni boyut, ayni yukseklik).
  E3 Reddet DOLU dugme: background:none/transparent YOK, text-decoration:underline YOK;
     Kabul ve Reddet'in ikisi de AA (>= 4.5:1) yazi/zemin kontrastli (renkler farkli olabilir);
     iki dugmenin background'unun bant zeminine (#pruvo-cerez-onay background) karsi kontrasti
     ESIT gorunurlukte: oran(Reddet)/oran(Kabul) in [0.9 ; 1.1]; Reddet background NOTR (R=G=B).
  E4 Yerlesim: masaustunde iki dugme AYNI .pco-btns kabinda yan yana (flex, column DEGIL),
     DOM'da Kabul once; <=600px'te ikisi de width:100%.
  E5 x dugmesi: aria-label "Kapat (reddet)"; tiklamasi kaydet("ret", ...) + rizaYayinla()
     cagirir (Reddet ile AYNI yol); Reddet de kaydet("ret") + rizaYayinla(). Bantta scroll/
     dokunma dinleyicisi YOK (kaydirma/gezinme riza SAYILMAZ).
  E6 Metin: bant paragrafinda "ölçüm" + "reklam" + "Google" + "Meta" + /gizlilik/ baglantisi;
     telefon/e-posta YOK.
  E7 Snippet (uretilen sayfalar) pruvoAtifRiza'yi typeof KORUMALI cagirir (Reddet atif
     verisini de siler; fonksiyon yoksa no-op).
  E8 Sayac beacon'i: kaydet() karar localStorage'a YAZILDIKTAN sonra TEK rizaSay() cagirir;
     rizaSay TEK sendBeacon("/api/shop/riza", JSON.stringify({k: k})) — govdede kimlik/ref/URL YOK.

Mutantlar (bellekte, IZOLE: hicbir dosya yazilmaz) her biri yalniz beklenen eksen(ler)i
kirmiziya cevirmeli; SURVIVOR = beklenen ekseni kirmiziya CEVIRMEYEN mutant sayisi.
Cikis: tum eksenler yesil + SURVIVOR=0 -> rc=0, aksi rc=1.
"""
import ast
import hashlib
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAYFALAR = ("index.html", "iletisim/index.html", "sss/index.html",
            "gizlilik/index.html", "hakkimizda/index.html")
SNIPPET = "tools/build.py::GA_BANNER_SNIPPET"
BLOK_BAS = "<!-- KVKK çerez onay banner"
KONTRAST_ESIK = (0.9, 1.1)            # oran(Reddet zemin) / oran(Kabul zemin)
ESIT_ALANLAR = ("padding", "font-size", "font-weight", "border-radius", "min-height", "min-width")
METIN_JETONLARI = ("ölçüm", "reklam", "Google", "Meta")


class Olculemedi(Exception):
    pass


# ------------------------------------------------------------------ kaynak okuma
def snippet_oku(kok):
    yol = os.path.join(kok, "tools", "build.py")
    with open(yol, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    for dugum in agac.body:
        if (isinstance(dugum, ast.Assign) and len(dugum.targets) == 1
                and getattr(dugum.targets[0], "id", None) == "GA_BANNER_SNIPPET"):
            return ast.literal_eval(dugum.value)
    raise Olculemedi("GA_BANNER_SNIPPET build.py'de BULUNAMADI")


def bant_blogu(metin, ad):
    """Yorum basligindan bandin </script>'ine kadar. Birden fazla ya da hic -> OLCULEMEDI."""
    n = metin.count(BLOK_BAS)
    if n != 1:
        raise Olculemedi("%s: bant basligi %d kez (TAM 1 beklenir)" % (ad, n))
    i = metin.index(BLOK_BAS)
    j = metin.find('var ANAHTAR = "pruvo_onay_analitik"', i)
    k = metin.find("</script>", j)
    if j < 0 or k < 0:
        raise Olculemedi("%s: bant betigi kapanmiyor" % ad)
    return metin[i:k + len("</script>")]


def bloklari_oku(kok):
    bloklar = {SNIPPET: bant_blogu(snippet_oku(kok), SNIPPET)}
    for rel in SAYFALAR:
        with open(os.path.join(kok, rel), encoding="utf-8") as f:
            bloklar[rel] = bant_blogu(f.read(), rel)
    return bloklar


# ------------------------------------------------------------------ CSS cozumleme
def css_kurallari(blok):
    """[(medya, secici, {ozellik: deger})] — tek seviye @media destekli, yorumlar soyulur."""
    m = re.search(r"<style>(.*?)</style>", blok, re.S)
    if not m:
        return []
    css = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    kurallar, i, medya = [], 0, None
    while i < len(css):
        ac = css.find("{", i)
        kapa = css.find("}", i)
        if kapa != -1 and (ac == -1 or kapa < ac):     # @media kapanisi
            medya, i = None, kapa + 1
            continue
        if ac == -1:
            break
        secici = css[i:ac].strip()
        if secici.startswith("@media"):
            medya, i = secici, ac + 1
            continue
        son = css.find("}", ac)
        govde = css[ac + 1:son]
        bildirim = {}
        for parca in govde.split(";"):
            if ":" in parca:
                k, v = parca.split(":", 1)
                bildirim[k.strip().lower()] = " ".join(v.split()).lower()
        for s in secici.split(","):
            kurallar.append((medya, " ".join(s.split()), bildirim))
        i = son + 1
    return kurallar


def bildirimler(kurallar, secici, medya_ici=False):
    sonuc = {}
    for medya, s, b in kurallar:
        if s == secici and ((medya is not None) == medya_ici):
            sonuc.update(b)
    return sonuc


def _kanal(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def rgb(hexrenk):
    h = hexrenk.strip().lower().lstrip("#")
    if re.fullmatch(r"[0-9a-f]{3}", h):
        h = "".join(ch * 2 for ch in h)
    if not re.fullmatch(r"[0-9a-f]{6}", h):
        return None                                   # hex olmayan renk -> olculemez (fail-closed)
    return tuple(int(h[x:x + 2], 16) for x in (0, 2, 4))


def parlaklik(hexrenk):
    c = rgb(hexrenk)
    if c is None:
        return None
    r, g, b = c
    return 0.2126 * _kanal(r) + 0.7152 * _kanal(g) + 0.0722 * _kanal(b)


def kontrast(on, arka):
    a, b = parlaklik(on), parlaklik(arka)
    if a is None or b is None:
        return 0.0
    a, b = max(a, b), min(a, b)
    return (a + 0.05) / (b + 0.05)


def zemin_kontrasti(kur):
    """(kabul, ret, ret/kabul) — iki dugme background'unun bant zeminine karsi WCAG orani."""
    zemin = bildirimler(kur, "#pruvo-cerez-onay")
    z = zemin.get("background", zemin.get("background-color", ""))
    ok = [kontrast(bildirimler(kur, "#pruvo-cerez-onay .pco-%s" % d).get(
              "background", bildirimler(kur, "#pruvo-cerez-onay .pco-%s" % d).get("background-color", "")), z)
          for d in ("kabul", "ret")]
    return ok[0], ok[1], (ok[1] / ok[0] if ok[0] else 0.0)


# ------------------------------------------------------------------ eksenler
def olc(bloklar):
    """{eksen: [hata,...]} — bos liste = yesil."""
    h = {e: [] for e in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")}
    adlar = sorted(bloklar)
    if len(bloklar) != 6:
        h["E1"].append("kopya sayisi %d (TAM 6 beklenir)" % len(bloklar))
    ozetler = {ad: hashlib.sha1(bloklar[ad].encode("utf-8")).hexdigest()[:8] for ad in adlar}
    if len(set(ozetler.values())) != 1:
        h["E1"].append("bant bloklari BAYT-ESIT degil: %s" % ", ".join(
            "%s=%s" % (a, ozetler[a]) for a in adlar))

    for ad in adlar:
        blok = bloklar[ad]
        kur = css_kurallari(blok)
        kabul = bildirimler(kur, "#pruvo-cerez-onay .pco-kabul")
        ret = bildirimler(kur, "#pruvo-cerez-onay .pco-ret")
        # E2 esit bildirim
        for alan in ESIT_ALANLAR:
            if alan not in kabul or alan not in ret or kabul[alan] != ret[alan]:
                h["E2"].append("%s: %s esit degil (kabul=%r ret=%r)"
                               % (ad, alan, kabul.get(alan), ret.get(alan)))
        # E3 dolu dugme + AA
        rb = ret.get("background", ret.get("background-color", ""))
        if rb in ("", "none", "transparent") or "none" in rb.split():
            h["E3"].append("%s: Reddet DOLU degil (background=%r)" % (ad, rb))
        if "underline" in ret.get("text-decoration", ""):
            h["E3"].append("%s: Reddet baglanti gorunumunde (text-decoration:underline)" % ad)
        for etiket, b in (("Kabul", kabul), ("Reddet", ret)):
            arka = b.get("background", b.get("background-color", ""))
            oran = kontrast(b.get("color", ""), arka)
            if oran < 4.5:
                h["E3"].append("%s: %s kontrasti %.2f < 4.5 (color=%r bg=%r)"
                               % (ad, etiket, oran, b.get("color"), arka))
        zk, zr, zo = zemin_kontrasti(kur)
        if not (KONTRAST_ESIK[0] <= zo <= KONTRAST_ESIK[1]):
            h["E3"].append("%s: zemin kontrasti esit degil (kabul=%.2f ret=%.2f oran=%.3f, [%.1f;%.1f] disi)"
                           % (ad, zk, zr, zo, KONTRAST_ESIK[0], KONTRAST_ESIK[1]))
        rc = rgb(rb)
        if rc is None or len(set(rc)) != 1:
            h["E3"].append("%s: Reddet background notr degil (R=G=B beklenir, %r)" % (ad, rb))
        # E4 yerlesim
        kab = bildirimler(kur, "#pruvo-cerez-onay .pco-btns")
        if kab.get("display") != "flex" or kab.get("flex-direction", "row") != "row":
            h["E4"].append("%s: masaustu dugme kabi yan yana flex degil (%r)" % (ad, kab))
        m = re.search(r'<div class="pco-btns">(.*?)</div>', blok, re.S)
        ic = m.group(1) if m else ""
        i_k, i_r = ic.find('id="pco-kabul"'), ic.find('id="pco-ret"')
        if i_k < 0 or i_r < 0 or i_k > i_r:
            h["E4"].append("%s: Kabul+Reddet ayni .pco-btns kabinda degil ya da sira ters" % ad)
        if not re.search(r'<button type="button" class="pco-ret" id="pco-ret">', ic):
            h["E4"].append("%s: Reddet <button> degil" % ad)
        mk = bildirimler(kur, "#pruvo-cerez-onay .pco-kabul", medya_ici=True)
        mr = bildirimler(kur, "#pruvo-cerez-onay .pco-ret", medya_ici=True)
        if mk.get("width") != "100%" or mr.get("width") != "100%":
            h["E4"].append("%s: mobilde ikisi de tam genislik degil (kabul=%r ret=%r)"
                           % (ad, mk.get("width"), mr.get("width")))
        # E5 x = ret yolu, kaydirma riza degil
        if not re.search(r'<button type="button" class="pco-kapat" id="pco-kapat" '
                         r'aria-label="Kapat \(reddet\)">', blok):
            h["E5"].append('%s: x dugmesi (aria-label "Kapat (reddet)") YOK' % ad)
        js = blok[blok.find("<script>"):]
        kx = re.search(r'kapat\.addEventListener\("click", function\(\)\{(.*?)\}\);', js, re.S)
        if not kx or not re.search(r'kaydet\("ret"(, "kapat")?\);\s*rizaYayinla\(\);', kx.group(1)):
            h["E5"].append("%s: x tiklamasi kaydet(\"ret\") + rizaYayinla() yolunu cagirmiyor" % ad)
        rx = re.search(r'ret\.addEventListener\("click", function\(\)\{(.*?)\}\);', js, re.S)
        if not rx or not re.search(r'kaydet\("ret"\);\s*rizaYayinla\(\);', rx.group(1)):
            h["E5"].append("%s: Reddet tiklamasi kaydet(\"ret\") + rizaYayinla() degil" % ad)
        if re.search(r'addEventListener\(\s*["\'](scroll|wheel|touchmove|touchstart)', js):
            h["E5"].append("%s: bantta kaydirma/dokunma dinleyicisi var (gezinme riza SAYILAMAZ)" % ad)
        # E6 metin
        p = re.search(r'<div id="pruvo-cerez-onay"[^>]*>.*?<p>(.*?)</p>', blok, re.S)
        metin = p.group(1) if p else ""
        for jeton in METIN_JETONLARI:
            if jeton.lower() not in metin.lower():
                h["E6"].append("%s: bant metninde %r YOK" % (ad, jeton))
        if '<a href="/gizlilik/">' not in metin:
            h["E6"].append("%s: bant metni /gizlilik/'e baglanmiyor" % ad)
        if re.search(r"\d{3}[\s.-]?\d{3}[\s.-]?\d{2}|@[a-z0-9-]+\.", metin):
            h["E6"].append("%s: bant metninde telefon/e-posta benzeri dizi" % ad)
        # E7 pruvoAtifRiza typeof korumali
        if 'if(typeof window.pruvoAtifRiza === "function"){ window.pruvoAtifRiza(); }' not in js:
            h["E7"].append("%s: pruvoAtifRiza typeof korumali cagrisi YOK" % ad)
        # E8 sayac beacon'i
        kd = re.search(r"function kaydet\(deger, sayac\)\{(.*?)\n", js)
        govde = kd.group(1) if kd else ""
        i_yaz = govde.find("localStorage.setItem(ANAHTAR, deger)")
        i_say = govde.find("rizaSay(sayac || deger)")
        if i_yaz < 0 or i_say < 0 or i_say < i_yaz or govde.count("rizaSay(") != 1:
            h["E8"].append("%s: kaydet() karar yazildiktan SONRA tek rizaSay cagirmiyor" % ad)
        rs = re.search(r"function rizaSay\(k\)\{(.*?)\n", js)
        rsg = rs.group(1) if rs else ""
        if (rsg.count("sendBeacon(") != 1 or js.count("/api/shop/riza") != 1
                or 'navigator.sendBeacon("/api/shop/riza", JSON.stringify({k: k}))' not in rsg):
            h["E8"].append("%s: rizaSay tek sendBeacon(\"/api/shop/riza\", {k}) degil" % ad)
        if re.search(r"location|referrer|cookie|userAgent|href", rsg):
            h["E8"].append("%s: rizaSay govdesinde kimlik/ref/URL kaynagi var" % ad)
    return h


# ------------------------------------------------------------------ mutantlar
def _hepsine(bloklar, eski, yeni):
    out = {}
    for ad, b in bloklar.items():
        if b.count(eski) != 1:
            raise Olculemedi("mutant capasi %s'te %d kez: %r" % (ad, b.count(eski), eski[:50]))
        out[ad] = b.replace(eski, yeni)
    return out


def _birine(bloklar, ad, eski, yeni):
    out = dict(bloklar)
    if out[ad].count(eski) != 1:
        raise Olculemedi("mutant capasi %s'te bulunamadi: %r" % (ad, eski[:50]))
    out[ad] = out[ad].replace(eski, yeni)
    return out


RET_CSS = ("#pruvo-cerez-onay .pco-ret{background:#707070;color:#fff;padding:12px 28px;\n"
           "    font-size:15px;font-weight:700;border-radius:8px;min-width:128px;min-height:46px}")
MUTANTLAR = (
    ("M1 Reddet baglanti gorunumune doner (6 kopyada)", {"E3"},
     lambda b: _hepsine(b, RET_CSS, RET_CSS.replace(
         "background:#707070;color:#fff", "background:none;color:#dbe4f2").replace(
         "min-height:46px}", "min-height:46px;text-decoration:underline}"))),
    ("M2 bir sayfa farkli (iletisim'de tek bayt)", {"E1"},
     lambda b: _birine(b, "iletisim/index.html", "Ayrıntı:", "Ayrıntı :")),
    ("M3 Reddet dolgusu Kabul'den kucuk (6 kopyada)", {"E2"},
     lambda b: _hepsine(b, RET_CSS, RET_CSS.replace("padding:12px 28px", "padding:12px 10px"))),
    ("M4 x tiklamasi Kabul yazar (6 kopyada)", {"E5"},
     lambda b: _hepsine(b, 'kaydet("ret", "kapat"); rizaYayinla();',
                        'kaydet("kabul", "kapat"); rizaYayinla();')),
    ("M5 metinden Meta duser (6 kopyada)", {"E6"},
     lambda b: _hepsine(b, "(Google ve Meta)", "(Google)")),
    ("M6 snippet pruvoAtifRiza'yi cagirmaz (6 kopyada)", {"E7"},
     lambda b: _hepsine(b, 'if(typeof window.pruvoAtifRiza === "function"){ window.pruvoAtifRiza(); } ', "")),
    ("M7 beacon govdesine URL eklenir (6 kopyada)", {"E8"},
     lambda b: _hepsine(b, "JSON.stringify({k: k})", "JSON.stringify({k: k, u: location.href})")),
    ("M8 mobilde Reddet tam genislik degil (6 kopyada)", {"E4"},
     lambda b: _hepsine(b, "    #pruvo-cerez-onay .pco-ret{width:100%}\n", "")),
    ("M9 kaydirma riza sayilir (6 kopyada)", {"E5"},
     lambda b: _hepsine(b, "  bannerTazele(); if(!el.hidden)",
                        '  window.addEventListener("scroll", function(){ kaydet("kabul"); });\n'
                        "  bannerTazele(); if(!el.hidden)")),
    ("M10 Reddet eski acik zemin #e9eef6 (6 kopyada)", {"E3"},
     lambda b: _hepsine(b, RET_CSS, RET_CSS.replace(
         "background:#707070;color:#fff", "background:#e9eef6;color:#12294d"))),
    ("M11 Reddet cok koyu #4a4a4a (6 kopyada)", {"E3"},
     lambda b: _hepsine(b, RET_CSS, RET_CSS.replace("background:#707070", "background:#4a4a4a"))),
    ("M12 Reddet renkli ama esit kontrastli #6c7078 (6 kopyada)", {"E3"},
     lambda b: _hepsine(b, RET_CSS, RET_CSS.replace("background:#707070", "background:#6c7078"))),
)


def main():
    try:
        bloklar = bloklari_oku(KOK)
    except (Olculemedi, OSError) as hata:
        print("OLCULEMEDI: %s" % hata)
        return 1
    print("riza bandi esitlik testi — %d kopya" % len(bloklar))
    for ad in sorted(bloklar):
        print("  %s  sha1=%s  %d bayt" % (ad, hashlib.sha1(bloklar[ad].encode("utf-8")).hexdigest()[:8],
                                         len(bloklar[ad])))
    h = olc(bloklar)
    kirmizi = 0
    for e in sorted(h):
        if h[e]:
            kirmizi += 1
            print("  ❌ %s %s" % (e, h[e][0]) + (" (+%d)" % (len(h[e]) - 1) if len(h[e]) > 1 else ""))
        else:
            print("  ✅ %s" % e)
    print("EKSEN %d/%d yesil" % (len(h) - kirmizi, len(h)))
    zk, zr, zo = zemin_kontrasti(css_kurallari(bloklar[SNIPPET]))
    print("E3_KONTRAST kabul=%.3f ret=%.3f oran=%.3f" % (zk, zr, zo))

    survivor, eksik = 0, 0
    for ad, beklenen, uygula in MUTANTLAR:
        try:
            mb = uygula(bloklar)
        except Olculemedi as hata:
            print("  ❌ %s -> %s" % (ad, hata))
            eksik += 1
            continue
        kir = {e for e, v in olc(mb).items() if v}
        if not beklenen <= kir:
            survivor += 1
        tamam = kir == beklenen
        if not tamam:
            eksik += 1
        print("  %s %s -> KIRMIZI %s (beklenen %s)"
              % ("✅" if tamam else "❌", ad, sorted(kir), sorted(beklenen)))
    print("MUTANT %d/%d SURVIVOR=%d" % (len(MUTANTLAR) - eksik, len(MUTANTLAR), survivor))
    ok = kirmizi == 0 and survivor == 0 and eksik == 0
    print("SONUC: %s" % ("YESIL — 6 kopya ESIT, tum eksenler yesil" if ok else "KIRMIZI"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
