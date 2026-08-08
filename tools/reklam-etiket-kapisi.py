#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REKLAM/OLCUM ETIKET KAPSAM NOBETCISI — sayfa sinifi basina fail-closed.

    python3 tools/reklam-etiket-kapisi.py
    python3 tools/reklam-etiket-kapisi.py --kendini-test
    python3 tools/reklam-etiket-kapisi.py --kok /gecici/mutant-agac

NEDEN VAR (olculdu, 8 Agu 2026)
-------------------------------
Google Ads panelinde "Sayfa goruntuleme = Hatali yapilandirilmis" cikinca ilk hipotez
"etiket bazi sayfalarda YOK" idi. Olcum bunu CURUTTU: 23.923/23.923 sayfada etiket vardi.
Ama o olcum ELDE yapildi ve HICBIR YERDE KALICILASMADI -> yarin bir sablondan `{ga_head}`
dusse, bir yasal sayfanin GA blogu ayrissa ya da `url_passthrough` sessizce kalksa
hicbir kirmizi yanmazdi. Bu sinifin hatasi SESSIZDIR: etiket "var" gorunurken atif coker
ve reklam butcesi YANLIS okunur.

NE OLCULUR (sayfa sinifi basina, dort eksen)
--------------------------------------------
  (a) OLCUM ETIKETI     : `G-…` olcum kimligi + gtag/js yuklemesi VAR mi
  (b) RIZA BLOGU        : Consent Mode v2 `default` + dort alan ve KOMUTU
  (c) TASIMA AYARLARI   : `url_passthrough` + `ads_data_redaction` VAR mi
  (d) syncUrl KORUMASI  : ana sayfanin URL senkronu reklam parametrelerini KORUYOR mu
                          (liste TEK kanonik kaynaktan turemis mi)

KANONIK KUME NASIL TURETILIR (elle envanter YOK)
------------------------------------------------
Bu depoda ELLE tutulan envanterler parti basina bayatliyor ve yayini durduruyor
([[envanter-drift-parti-basina]]). Bu yuzden sayfa evreni TURETILIR:

  SINIF A — KAYNAK SAYFALAR : `git ls-files '*.html'` icinden `<!DOCTYPE html>` +
      `<head` + `rel="canonical"` tasiyanlar. (Ana sayfa + elle yazilmis dort yasal
      sayfa; GA bunlara ELLE gomulu, build.py bu blogu yenilemez.)
  SINIF B — URETILEN SAYFA SABLONLARI : izlenen `*.py` icindeki dize sabitlerinden
      AYNI uc izi tasiyanlar (AST ile; kaynak CALISTIRILMAZ). Bunlar 23.923 yayin
      sayfasinin tamaminin sablonudur -> sablonu olcmek sayfayi olcmektir.

🔴 AYIRT EDICI IZ `rel="canonical"` BILEREK SECILDI ve DAIRESEL DEGILDIR: olculdu, bu
depoda `<html>`+`<head>` tasiyan 13 dize sabitinin 4'u gercek yayin sablonu, 9'u kapi
fiksturu / yerel teshis panosu (tools/parity-panel.py) / docstring ornegi. Yalniz gercek
yayin sablonlari kanonik adres basar. Ayirt ediciyi `{ga_head}`'in KENDISINDEN turetmek
tautoloji olurdu (olcmek istedigimiz sey), `rel="canonical"` ise BAGIMSIZ bir ozelliktir.

TEK YONLU NOBETCI OLUDUR: kapsam disi ama BENZER dosyalar (canonical'siz teshis panosu,
parca HTML, fikstur dizesi) REDDEDILMEMELI. Bu eksen `--kendini-test` icinde Y1-Y4
fiksturleriyle nobetlenir; kume BOSALIRSA kapi YESIL degil OLCULEMEDI verir.

CIKIS KODLARI (fail-closed)
---------------------------
  0 = YESIL        her sayfa sinifi dort ekseni de tasiyor
  1 = KIRMIZI      en az bir sinif bir ekseni kaybetmis
  3 = OLCULEMEDI   evren turetilemedi / tek kaynak okunamadi / kume BOS
                   ("olculemeyen sinif YESIL degildir")

Offline, stdlib, ~200 ms. urunler.json OKUNMAZ.
"""

import argparse
import ast
import os
import re
import subprocess
import sys

KOK_VARSAYILAN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

YESIL, KIRMIZI, OLCULEMEDI = 0, 1, 3

# --- Yayin sayfasi AYIRT EDICI IZLERI (yukaridaki gerekce) -------------------
SAYFA_IZLERI = ("<!DOCTYPE html>", "<head", 'rel="canonical"')

# --- Tek kaynak (build.py) icindeki cekirdek blogun capalari ------------------
# Cekirdek = HTML yorumu HARIC calisan GA govdesi. Yorum sayfadan sayfaya degisebilir
# (index.html'de "TEK KAYNAK" notu var), CALISAN govde ise BAYT BAYT ayni olmak zorunda.
CEKIRDEK_BAS = "  window.dataLayer = window.dataLayer || [];"
CEKIRDEK_SON_KALIP = re.compile(r"  gtag\('config', '(G-[A-Z0-9]+)', \{ 'anonymize_ip': true \}\);\n</script>")

RIZA_ALANLARI = ("ad_storage", "ad_user_data", "ad_personalization", "analytics_storage")
TASIMA_AYARLARI = ("url_passthrough", "ads_data_redaction")

# syncUrl'in KORUMAK ZORUNDA oldugu reklam parametreleri (Google Ads + kampanya etiketi).
ZORUNLU_REKLAM_PARAM = ("gclid", "gbraid", "wbraid", "utm_source", "utm_medium",
                        "utm_campaign", "utm_term", "utm_content")

SABLON_CAPASI = "{ga_head}"


class Olculemedi(Exception):
    """Evren turetilemedi / tek kaynak okunamadi -> YESIL HUKMU VERILMEZ."""


# ---------------------------------------------------------------- yardimcilar
def _izlenen(kok, desen):
    """git ls-files — evrenin TEK turetim yolu. Basarisizsa OLCULEMEDI (fail-closed)."""
    try:
        sonuc = subprocess.run(["git", "-C", kok, "ls-files", desen],
                               capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as hata:
        raise Olculemedi("git ls-files calistirilamadi (%s): %s" % (desen, hata))
    if sonuc.returncode != 0:
        raise Olculemedi("git ls-files rc=%d (%s): %s"
                         % (sonuc.returncode, desen, sonuc.stderr.strip()[:200]))
    return [s for s in sonuc.stdout.splitlines() if s.strip()]


def _oku(kok, rel):
    try:
        with open(os.path.join(kok, rel), encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as hata:
        raise Olculemedi("dosya okunamadi: %s (%s)" % (rel, hata))


def _yayin_sayfasi_mi(metin):
    return all(iz in metin for iz in SAYFA_IZLERI)


def kaynak_sayfalar(kok):
    """SINIF A — izlenen HTML dosyalarindan yayin sayfasi olanlar (TURETILIR)."""
    bulunan = []
    for rel in _izlenen(kok, "*.html"):
        metin = _oku(kok, rel)
        if _yayin_sayfasi_mi(metin):
            bulunan.append((rel, metin))
    return bulunan


def sayfa_sablonlari(kok):
    """SINIF B — izlenen .py dosyalarindaki yayin sayfasi SABLONLARI (AST, TURETILIR).

    Kaynak CALISTIRILMAZ; yalnizca dize sabitleri okunur. Ayristirilamayan bir .py
    OLCULEMEDI'dir — sessizce atlanirsa o modulun sablonlari kapsamdan DUSER."""
    bulunan = []
    for rel in _izlenen(kok, "*.py"):
        ham = _oku(kok, rel)
        try:
            agac = ast.parse(ham)
        except SyntaxError as hata:
            raise Olculemedi("python kaynagi ayristirilamadi: %s (%s)" % (rel, hata))
        for dugum in ast.walk(agac):
            if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str):
                if _yayin_sayfasi_mi(dugum.value):
                    bulunan.append((rel, dugum.lineno, dugum.value))
    return bulunan


def _sabit_dize(kok, rel, ad):
    """build.py'den bir modul duzeyi dize sabitini AST ile cek (calistirmadan)."""
    ham = _oku(kok, rel)
    try:
        agac = ast.parse(ham)
    except SyntaxError as hata:
        raise Olculemedi("%s ayristirilamadi: %s" % (rel, hata))
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name) and hedef.id == ad:
                    if isinstance(dugum.value, ast.Constant) and \
                            isinstance(dugum.value.value, str):
                        return dugum.value.value
                    raise Olculemedi("%s::%s dize sabiti DEGIL" % (rel, ad))
    raise Olculemedi("%s icinde %s sabiti bulunamadi" % (rel, ad))


def cekirdek_cikar(snippet):
    """GA blogunun CALISAN govdesi (HTML yorumu haric). Capa yoksa OLCULEMEDI."""
    i = snippet.find(CEKIRDEK_BAS)
    if i == -1:
        raise Olculemedi("GA cekirdek baslangic capasi yok: %r" % CEKIRDEK_BAS)
    eslesme = CEKIRDEK_SON_KALIP.search(snippet, i)
    if eslesme is None:
        raise Olculemedi("GA cekirdek bitis capasi (gtag config) yok")
    return snippet[i:eslesme.end()], eslesme.group(1)


# ------------------------------------------------------- eksen degerlendirmesi
def eksenler(metin, olcum_kimligi):
    """Bir sayfa/snippet metninde dort eksenin durumu -> eksik eksen adlari."""
    eksik = []
    if olcum_kimligi not in metin or "googletagmanager.com/gtag/js" not in metin:
        eksik.append("(a) olcum etiketi")
    riza_var = "'consent', 'default'" in metin or '"consent", "default"' in metin
    if not riza_var or not all(alan in metin for alan in RIZA_ALANLARI):
        eksik.append("(b) riza blogu")
    if not all(ayar in metin for ayar in TASIMA_AYARLARI):
        eksik.append("(c) tasima ayari (%s)"
                     % ", ".join(a for a in TASIMA_AYARLARI if a not in metin))
    return eksik


def _dizi_literali(kaynak, ad):
    """`var <ad> = [ ... ];` icindeki dize ogeleri. Bulunamazsa None."""
    kalip = re.compile(r"var\s+" + re.escape(ad) + r"\s*=\s*\[([^\]]*)\]\s*;")
    eslesme = kalip.search(kaynak)
    if eslesme is None:
        return None
    return re.findall(r'["\']([^"\']+)["\']', eslesme.group(1))


def syncurl_ekseni(index_metin):
    """(d) ekseni — ana sayfanin URL senkronu reklam parametrelerini koruyor mu.

    Uc sart: (1) syncUrl kanonik kaynagi CAGIRIR, (2) kanonik kume sekiz zorunlu
    parametreyi KAPSAR, (3) syncUrl govdesinde IKINCI bir elle yazilmis parametre
    dizisi YOKTUR (ikiz liste sessizce ayrisir)."""
    eksik = []
    i = index_metin.find("  function syncUrl(){")
    if i == -1:
        raise Olculemedi("index.html icinde syncUrl() bulunamadi")
    j = index_metin.find("\n  // seçili kategori + aramaya uyan", i)
    if j == -1:
        raise Olculemedi("syncUrl() govdesinin bitis capasi bulunamadi")
    govde = index_metin[i:j]

    if "PRUVO_ATIF.urlKorunan()" not in govde:
        eksik.append("(d) syncUrl kanonik korunan-parametre kaynagini CAGIRMIYOR")

    yorumsuz = re.sub(r"/\*.*?\*/", "", govde, flags=re.S)
    yorumsuz = re.sub(r"//[^\n]*", "", yorumsuz)
    if re.search(r"\[[^\]]*[\"']gclid[\"'][^\]]*\]", yorumsuz):
        eksik.append("(d) syncUrl govdesinde IKINCI elle yazilmis parametre dizisi var")

    if "urlKorunan: function()" not in index_metin:
        eksik.append("(d) PRUVO_ATIF.urlKorunan() tanimi YOK (tek kanonik kaynak dustu)")
        return eksik, []

    kume = []
    for ad in ("TIK_ALANLARI", "UTM_ALANLARI", "EK_URL_ETIKET"):
        parca = _dizi_literali(index_metin, ad)
        if parca is None:
            raise Olculemedi("index.html icinde %s dizi literali okunamadi" % ad)
        kume.extend(parca)
    kayip = [p for p in ZORUNLU_REKLAM_PARAM if p not in kume]
    if kayip:
        eksik.append("(d) kanonik korunan kume EKSIK: %s" % ", ".join(kayip))
    return eksik, kume


# ------------------------------------------------------------------ ana hukum
def degerlendir(kok):
    """(cikis_kodu, satirlar) dondurur. Istisna FIRLATMAZ (Olculemedi yakalanir)."""
    satir = []
    try:
        snippet = _sabit_dize(kok, "tools/build.py", "GA_HEAD_SNIPPET")
        cekirdek, olcum_kimligi = cekirdek_cikar(snippet)

        sayfalar = kaynak_sayfalar(kok)
        sablonlar = sayfa_sablonlari(kok)
        if not sayfalar:
            raise Olculemedi("SINIF A kumesi BOS — kanonik sayfa evreni turetilemedi")
        if not sablonlar:
            raise Olculemedi("SINIF B kumesi BOS — sayfa sablonu evreni turetilemedi")
    except Olculemedi as hata:
        satir.append("OLCULEMEDI: %s" % hata)
        return OLCULEMEDI, satir

    hata_satir = []

    # --- TEK KAYNAK: build.py snippet'inin KENDISI dort ekseni tasimali -------
    kaynak_eksik = eksenler(snippet, olcum_kimligi)
    satir.append("TEK KAYNAK  tools/build.py::GA_HEAD_SNIPPET  cekirdek %d bayt  olcum %s"
                 % (len(cekirdek), olcum_kimligi))
    if kaynak_eksik:
        hata_satir.append("  ❌ TEK KAYNAK eksik eksen -> %s" % "; ".join(kaynak_eksik))

    # --- SINIF A: kaynak sayfalar --------------------------------------------
    satir.append("SINIF A     kaynak sayfa (turetilen): %d" % len(sayfalar))
    for rel, metin in sayfalar:
        eksik = eksenler(metin, olcum_kimligi)
        if cekirdek not in metin:
            eksik.append("(ikiz) GA cekirdegi tek kaynaktan BAYT BAYT AYRISMIS")
        if eksik:
            hata_satir.append("  ❌ %s -> %s" % (rel, "; ".join(eksik)))
        else:
            satir.append("  ok  %s  (a,b,c + ikiz bayt-birebir)" % rel)

    # --- SINIF B: uretilen sayfa sablonlari ----------------------------------
    satir.append("SINIF B     yayin sayfa sablonu (turetilen): %d" % len(sablonlar))
    for rel, satir_no, sablon in sablonlar:
        if SABLON_CAPASI not in sablon:
            hata_satir.append("  ❌ %s:%d -> sablon `%s` capasini TASIMIYOR "
                              "(uretilen sayfalar etiketsiz cikar)"
                              % (rel, satir_no, SABLON_CAPASI))
        else:
            satir.append("  ok  %s:%d  (%s)" % (rel, satir_no, SABLON_CAPASI))

    # --- SINIF D: ana sayfanin syncUrl korumasi -------------------------------
    try:
        index_metin = _oku(kok, "index.html")
        d_eksik, kume = syncurl_ekseni(index_metin)
    except Olculemedi as hata:
        satir.append("OLCULEMEDI: %s" % hata)
        return OLCULEMEDI, satir
    satir.append("SINIF D     syncUrl korunan parametre: %d (kanonik kume)" % len(kume))
    if d_eksik:
        hata_satir.extend("  ❌ index.html -> %s" % e for e in d_eksik)
    else:
        satir.append("  ok  index.html  (d) %d/%d zorunlu reklam parametresi korunuyor"
                     % (len(ZORUNLU_REKLAM_PARAM), len(ZORUNLU_REKLAM_PARAM)))

    if hata_satir:
        satir.append("-" * 70)
        satir.extend(hata_satir)
        satir.append("SONUC: KIRMIZI ❌  — %d sayfa sinifi/eksen ihlali" % len(hata_satir))
        return KIRMIZI, satir

    satir.append("-" * 70)
    satir.append("SONUC: YESIL ✅  — %d kaynak sayfa + %d yayin sablonu: olcum etiketi · "
                 "riza blogu · tasima ayari · syncUrl korumasi TAM."
                 % (len(sayfalar), len(sablonlar)))
    return YESIL, satir


# ------------------------------------------------------------- IC NOBETCI
# Kapinin KENDI hukmunu sentetik agaclarla olcer. Iki yon de nobetlenir:
#   K* = KIRMIZI yanmali (eksen fiilen dusmus)
#   Y* = YESIL kalmali (benzer ama KAPSAM DISI dosya reddedilmemeli)
#   O* = OLCULEMEDI vermeli (evren turetilemedi)
# Tek yonlu batarya "her degisiklige kirmizi" halini AYIRT EDEMEZ.

_F_SNIPPET = '''<!-- GA4 -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied',
    'wait_for_update': 500
  });
  gtag('set', 'url_passthrough', true);
  gtag('set', 'ads_data_redaction', true);
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TESTFIX01"></script>
<script>
  gtag('js', new Date());
  gtag('config', 'G-TESTFIX01', { 'anonymize_ip': true });
</script>'''

_F_INDEX_KUYRUK = '''
<script>
  var PRUVO_ATIF = (function(){
    var UTM_ALANLARI = ["utm_source","utm_medium","utm_campaign","utm_id"];
    var TIK_ALANLARI = ["fbc","fbclid","gclid","gbraid","wbraid","ttclid","msclkid"];
    var EK_URL_ETIKET = ["utm_term","utm_content"];
    return {
      urlKorunan: function(){
        return TIK_ALANLARI.concat(UTM_ALANLARI, EK_URL_ETIKET);
      }
    };
  })();
  function syncUrl(){
    var params = new URLSearchParams();
    var korunan = PRUVO_ATIF.urlKorunan();
    history.replaceState(null, "", location.pathname);
  }
  // seçili kategori + aramaya uyan ürünlerdeki markalar
</script>
</body></html>
'''


def _fikstur_yaz(dizin, ad, icerik):
    tam = os.path.join(dizin, ad)
    os.makedirs(os.path.dirname(tam), exist_ok=True)
    with open(tam, "w", encoding="utf-8") as f:
        f.write(icerik)


def _sentetik_agac(dizin, snippet=None, index_kuyruk=None, sablon_capa=True,
                   ekler=None, yasal_snippet=None):
    """Gercek agacin SEKLINI taklit eden mini depo (git ls-files calissin diye git init)."""
    snippet = _F_SNIPPET if snippet is None else snippet
    yasal = snippet if yasal_snippet is None else yasal_snippet
    kuyruk = _F_INDEX_KUYRUK if index_kuyruk is None else index_kuyruk

    sablon = ('<!DOCTYPE html>\n<html lang="tr">\n<head>\n'
              + ("{ga_head}\n" if sablon_capa else "")
              + '<link rel="canonical" href="https://pruvo3d.com/urun/x/">\n'
              + "</head><body>{govde}</body></html>")
    build_py = ('GA_HEAD_SNIPPET = """%s"""\n\nURUN_SABLON = """%s"""\n'
                % (snippet, sablon))
    _fikstur_yaz(dizin, "tools/build.py", build_py)
    _fikstur_yaz(dizin, "index.html",
                 '<!DOCTYPE html>\n<html lang="tr">\n<head>\n' + snippet
                 + '\n<link rel="canonical" href="https://pruvo3d.com/">\n</head><body>'
                 + kuyruk)
    _fikstur_yaz(dizin, "sss/index.html",
                 '<!DOCTYPE html>\n<html lang="tr">\n<head>\n' + yasal
                 + '\n<link rel="canonical" href="https://pruvo3d.com/sss/">\n'
                 + "</head><body></body></html>")
    for ad, icerik in (ekler or {}).items():
        _fikstur_yaz(dizin, ad, icerik)

    for komut in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", "-C", dizin] + komut, capture_output=True, text=True)


# Y* — KAPSAM DISI ama BENZER dosyalar. Reddedilirlerse nobetci tek yonlu olur ve her
# mesru bakim duzenlemesi yayini durdurur.
_Y_EKLER = {
    # Y1: kanonik adres BASMAYAN yerel teshis panosu (gercekte tools/parity-panel.py).
    "tools/parity-panel.py": ('PANO = """<!DOCTYPE html>\n<html lang="tr"><head>'
                              '<meta name="viewport" content="width=device-width">'
                              '</head><body>pano</body></html>"""\n'),
    # Y2: kapi fiksturu — <html>+<head> var, kanonik adres YOK.
    "tools/ornek-kapisi.py": ('FIKSTUR = """<!DOCTYPE html><html lang="tr"><head>'
                              '</head><body>x</body></html>"""\n'),
    # Y3: PARCA html (head yok) — izlenen .html ama yayin sayfasi degil.
    "parca.html": "<div class=\"kart\">parca</div>\n",
    # Y4: kanonik adresli ama <head>siz parca sablon.
    "tools/parca_uret.py": ('PARCA = """<link rel="canonical" href="/x/">"""\n'),
}


def _senaryolar():
    return [
        ("K1 olcum etiketi dusurulur (sayfada gtag/js yok)", KIRMIZI,
         dict(snippet=_F_SNIPPET.replace(
             '<script async src="https://www.googletagmanager.com/gtag/js?id=G-TESTFIX01"></script>\n', ""))),
        ("K2 riza blogu dusurulur (ad_storage beyani yok)", KIRMIZI,
         dict(snippet=_F_SNIPPET.replace("    'ad_storage': 'denied',\n", ""))),
        ("K3 url_passthrough dusurulur", KIRMIZI,
         dict(snippet=_F_SNIPPET.replace(
             "  gtag('set', 'url_passthrough', true);\n", ""))),
        ("K4 ads_data_redaction dusurulur", KIRMIZI,
         dict(snippet=_F_SNIPPET.replace(
             "  gtag('set', 'ads_data_redaction', true);\n", ""))),
        ("K5 sablondan {ga_head} capasi dusurulur", KIRMIZI,
         dict(sablon_capa=False)),
        ("K6 yasal sayfanin GA cekirdegi tek kaynaktan AYRISIR", KIRMIZI,
         dict(yasal_snippet=_F_SNIPPET.replace(
             "  gtag('set', 'url_passthrough', true);\n", ""))),
        ("K7 syncUrl kanonik kaynagi cagirmayi birakir", KIRMIZI,
         dict(index_kuyruk=_F_INDEX_KUYRUK.replace(
             "var korunan = PRUVO_ATIF.urlKorunan();",
             'var korunan = ["gclid","utm_source"];'))),
        ("K8 kanonik kume daraltilir (gbraid/wbraid dusurulur)", KIRMIZI,
         dict(index_kuyruk=_F_INDEX_KUYRUK.replace(
             '"fbc","fbclid","gclid","gbraid","wbraid","ttclid","msclkid"',
             '"fbc","fbclid","gclid"'))),
        ("Y0 saglam agac YESIL", YESIL, dict()),
        ("Y1-Y4 kapsam disi benzer dosyalar REDDEDILMEZ", YESIL, dict(ekler=_Y_EKLER)),
    ]


def _kendini_test():
    import shutil
    import tempfile
    gecti, dusen = 0, []

    for ad, beklenen, kwargs in _senaryolar():
        gecici = tempfile.mkdtemp(prefix="reklam-etiket-fikstur-")
        try:
            _sentetik_agac(gecici, **kwargs)
            rc, _ = degerlendir(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
        if rc == beklenen:
            gecti += 1
            print("  ok  %s (rc=%d)" % (ad, rc))
        else:
            dusen.append("%s: beklenen rc=%d, olculen rc=%d" % (ad, beklenen, rc))
            print("  FAIL %s: beklenen rc=%d, olculen rc=%d" % (ad, beklenen, rc))

    # O* — OLCULEMEDI yolu: yesil hukmu VERILMEMELI.
    olculemedi_vakalari = [
        ("O1 build.py YOK -> OLCULEMEDI", lambda d: os.remove(os.path.join(d, "tools/build.py"))),
        ("O2 git deposu DEGIL -> OLCULEMEDI",
         lambda d: shutil.rmtree(os.path.join(d, ".git"), ignore_errors=True)),
        ("O3 hicbir yayin sayfasi YOK -> OLCULEMEDI (kume BOS, YESIL degil)",
         lambda d: [os.remove(os.path.join(d, "index.html")),
                    os.remove(os.path.join(d, "sss/index.html"))]),
    ]
    for ad, bozucu in olculemedi_vakalari:
        gecici = tempfile.mkdtemp(prefix="reklam-etiket-fikstur-")
        try:
            _sentetik_agac(gecici)
            bozucu(gecici)
            rc, _ = degerlendir(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
        if rc == OLCULEMEDI:
            gecti += 1
            print("  ok  %s (rc=%d)" % (ad, rc))
        else:
            dusen.append("%s: beklenen rc=%d, olculen rc=%d" % (ad, OLCULEMEDI, rc))
            print("  FAIL %s: beklenen rc=%d, olculen rc=%d" % (ad, OLCULEMEDI, rc))

    print("-" * 70)
    if dusen:
        print("IC NOBETCI KIRMIZI ❌ — %d vaka dustu / %d gecti" % (len(dusen), gecti))
        for d in dusen:
            print("  · %s" % d)
        return 1
    print("IC NOBETCI YESIL ✅ — %d vaka (kirmizi yon + yanlis-pozitif yonu + "
          "olculemedi yolu)" % gecti)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kok", default=KOK_VARSAYILAN,
                    help="olculecek agacin koku (mutasyon surucusu icin)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="kapinin KENDI hukmunu sentetik fiksturlerle olcer")
    args = ap.parse_args()

    if args.kendini_test:
        return _kendini_test()

    rc, satirlar = degerlendir(args.kok)
    print("REKLAM/OLCUM ETIKET KAPSAM NOBETCISI")
    print("=" * 70)
    for s in satirlar:
        print(s)
    return rc


if __name__ == "__main__":
    sys.exit(main())
