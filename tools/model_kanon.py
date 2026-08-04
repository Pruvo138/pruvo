#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KANONİK MARKA/MODEL EŞLEMESİ — index.html'deki TEK KAYNAK bloğunun Python tarafı.

  python3 tools/model_kanon.py "F150" "Peugeot 206" ...     # elle bakış (marka: Ford varsayılır)

NEDEN VAR (ölçülen sessiz hata, 3 Ağu — [[ikiz-tanim-sessiz-ayrisma]]):
katlama/kanonikleştirme İKİ AYRI yerde, İKİ AYRI kuralla yaşıyordu:
  * sayfa üreteci (tools/marka_model_build.py): `_canon`, `_strip_marka_oneki`, `_ALIAS`,
    `MARKA_ALIAS` — "F150"/"F-150" AYNI model, "Vauxhall" = Opel.
  * ana sayfa filtresi (index.html): model ekseninde HAM eşitlik, marka ekseninde
    alias TANIMAYAN katlama.
Sonuç 429 marka-model çiftinde ölçüldü: 123 çiftte sayfa dar, 32 çiftte filtre dar,
366 ürün etkileniyor. İki yüzey de kendi içinde tutarlı göründüğü için kimse hata GÖRMÜYOR.

ÇÖZÜM — İKİNCİ TABLO YAZILMAZ: tablolar (`MARKA_ALIAS`, `MODEL_ALIAS`) ve kural
(`modelKanon`/`modelOnekSiyir`/`modelAnahtar`) index.html'deki KANONİK MODEL EŞLEMESİ
bloğunda yaşar; bu modül onları AYIKLAR ve Python tarafına birebir yansıtır. Ayrışma
tools/model-uyelik-kapisi.py tarafından GERÇEK JS node ile koşturularak fail-closed ölçülür
(iki dilde iki gövde kaçınılmaz; ölçülmeyen ayrışma kaçınılmaz DEĞİL).

FAIL-CLOSED: blok ya da tablolar okunamazsa SystemExit — sessizce boş tabloya düşmek
"hiç alias yok" demektir ve sayfa/filtre yeniden ayrışırdı.
"""
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX = os.path.join(ROOT, "index.html")

BLOK_BAS = "// --- KANONİK MODEL EŞLEMESİ BAŞ"
BLOK_SON = "// --- KANONİK MODEL EŞLEMESİ SON ---"

# index.html modelKanon() ile BİREBİR (JS: MODEL_TR + toLowerCase + ayıraç atma).
_TR = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
       "â": "a", "î": "i", "û": "u"}
_AYIRAC = re.compile(r"[\s\-\._/]")


def _dizi_ayikla(kaynak, ad):
    """`var <ad> = [ "a", "b", ... ];` literalini listeye çevirir (fail-closed)."""
    m = re.search(r"var\s+" + ad + r"\s*=\s*\[(.*?)\]\s*;", kaynak, re.S)
    if not m:
        raise SystemExit("HATA: index.html'de %s dizisi YOK — bileşik marka koruması "
                         "türetilemez (fail-closed: korumasız devam etmek 'Volvo Penta' "
                         "gibi bağımsız markaları marka+model diye bölerdi)." % ad)
    govde = re.sub(r"//[^\n]*", "", m.group(1))
    return re.findall(r'"([^"]+)"', govde)


def _obje_ayikla(kaynak, ad):
    """`var <ad> = { "a":"b", ... };` literalini sözlüğe çevirir (fail-closed)."""
    m = re.search(r"var\s+" + ad + r"\s*=\s*\{(.*?)\}\s*;", kaynak, re.S)
    if not m:
        raise SystemExit("HATA: index.html'de %s tablosu YOK — kanonik eşleme tek kaynağı "
                         "bozuk (fail-closed: alias'sız devam etmek sayfa ile filtreyi "
                         "sessizce ayrıştırırdı)." % ad)
    govde = re.sub(r"//[^\n]*", "", m.group(1))
    return dict(re.findall(r'"([^"]*)"\s*:\s*"([^"]*)"', govde))


def blok(index_html):
    """index.html'deki KANONİK MODEL EŞLEMESİ bloğunun GÖVDESİ (node koşumu bunu yükler)."""
    bas = index_html.find(BLOK_BAS)
    son = index_html.find(BLOK_SON)
    if bas == -1 or son == -1 or son <= bas:
        raise SystemExit("HATA: index.html'de KANONİK MODEL EŞLEMESİ bloğu bulunamadı "
                         "(marker'lar silinmiş/taşınmış) — ayrışma ölçülemez.")
    return index_html[index_html.index("\n", bas) + 1:son]


def bilesik_markalar(index_html):
    """ÇOK KELİMELİ kanonik marka adları — bölünmemesi gereken jetonlar.

    OTORİTE `tools/arama.py` KAPALI MARKA KÜMESİ'dir (UYUM_MARKA_IZINLI ∪ URETICI_MARKA);
    index.html'deki dizi onun AYNASIDIR (JS'in çalışma anında ihtiyacı var, arama.py'yi
    okuyamaz). Ayna ile otoritenin ayrışması tools/model-uyelik-kapisi.py'de fail-closed
    ölçülür — ikinci bir küratörlük kararı BURADA VERİLMEZ."""
    return _dizi_ayikla(index_html, "BILESIK_MARKA")


def bilesik_marka_mi(deger, bilesik_normlu):
    """index.html bilesikMarkaMi() portu (karşılaştırma markaNorm düzeyinde)."""
    return _marka_norm(deger) in bilesik_normlu


def _marka_norm(s):
    """index.html markaNorm() portu — bileşik marka karşılaştırması için."""
    n = (s or "").replace("I", "ı").replace("İ", "i").lower()
    for a, b in (("ı", "i"), ("ç", "c"), ("ğ", "g"), ("ö", "o"),
                 ("ş", "s"), ("ü", "u"), ("â", "a"), ("î", "i"),
                 ("é", "e"), ("è", "e"), ("ë", "e"), ("ä", "a")):
        n = n.replace(a, b)
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    return re.sub(r"\s+", " ", n).strip()


def tablolar(index_html):
    """(MARKA_ALIAS, MODEL_ALIAS) — index.html'den AYIKLANIR, kopya TUTULMAZ.
    MODEL_ALIAS anahtarı "<kanonik marka>|<kanon>" biçimindedir."""
    blok(index_html)                      # blok yoksa fail-closed (tablolar da güvenilmez)
    marka = _obje_ayikla(index_html, "MARKA_ALIAS")
    ham_model = _obje_ayikla(index_html, "MODEL_ALIAS")
    model = {}
    for k, v in ham_model.items():
        if "|" not in k:
            raise SystemExit("HATA: MODEL_ALIAS anahtarı '<marka>|<kanon>' değil: %r" % k)
        mk, canon = k.split("|", 1)
        model[(mk, canon)] = v
    return marka, model


def kanon(s):
    """index.html modelKanon() portu: küçük harf + TR sadeleştirme + ayıraç atma.
    'F-150'/'F150'/'F 150' -> 'f150'; 'S-Max'/'S-MAX' -> 'smax'."""
    t = (s or "").strip().lower()
    t = "".join(_TR.get(ch, ch) for ch in t)
    return _AYIRAC.sub("", t)


def onek_siyir(marka, s, evren):
    """index.html modelOnekSiyir() portu. `evren`: taninmis_mi + katla taşıyan marka evreni.
    'Peugeot 206'->'206' · 'Vauxhall Astra' (Opel)->'Astra' · değer tümüyle marka ise ''.
    ÇOK KELİMELİ kanonik marka adı ('Volvo Penta') BÖLÜNMEZ — evren.bilesik_normlu."""
    t = (s or "").strip()
    if not marka or not t:
        return t
    # FAIL-CLOSED: öznitelik YOKSA AttributeError — `getattr(..., bos_kume)` yazsaydık
    # koruma sessizce kapanır ve bileşik marka yeniden bölünürdü.
    if _marka_norm(t) in evren.bilesik_normlu:
        return t
    toks = t.split()
    for k in range(len(toks), 0, -1):
        onek = " ".join(toks[:k])
        if evren.taninmis_mi(onek) and evren.katla(onek) == marka:
            return " ".join(toks[k:]).strip()
    return t


def kusak_tablolari(index_html):
    """(KUSAK_DONANIM, KUSAK_DISI) — index.html'den AYIKLANIR, kopya TUTULMAZ.

    KUSAK_DONANIM: kapalı donanım/rozet soneki listesi ("gti", "st", ...).
    KUSAK_DISI   : "<marka>|<ham jeton>" biçiminde FARKLI ARAÇ istisnaları (otorite
                   tools/arama.py KUSAK_DISI_JETON; burası JS'in okuduğu ayna).
    FAIL-CLOSED: dizi yoksa SystemExit — sessizce boş listeye düşmek, sayfa tarafını
    filtreden ayrıştırır (donanım soneki katlanmaz) ya da istisnayı iptal eder."""
    blok(index_html)                      # blok yoksa fail-closed
    return (_dizi_ayikla(index_html, "KUSAK_DONANIM"),
            _dizi_ayikla(index_html, "KUSAK_DISI"),
            _dizi_ayikla(index_html, "KUSAK_ESLEME"))


_KUSAK_SAYI = re.compile(r"^\d{1,2}$")
_KUSAK_MK = re.compile(r"^mk\.?\d{1,2}$")
_KUSAK_ROMEN = re.compile(r"^(i|ii|iii|iv|v|vi|vii|viii|ix|x)$")
_KUSAK_HARF = re.compile(r"^[a-z]$")


def kusak_sonek_mi(w, donanim):
    """index.html kusakSonekMi() portu — kelime KUŞAK/DONANIM soneki mi?
    '4'/'Mk4'/'IV'/'H'/'ST' evet · 'Life'/'Cabrio'/'E-Tech'/'125' hayır."""
    t = (w or "").lower()
    if _KUSAK_SAYI.match(t) or _KUSAK_MK.match(t) or _KUSAK_ROMEN.match(t) \
            or _KUSAK_HARF.match(t):
        return True
    return t in set(x.lower() for x in donanim)


def kusak_esleme_tabani(marka, s, esleme):
    """index.html kusakEslemeTabani() portu — küratörlü (marka, jeton) -> taban model adı."""
    onek = (marka or "") + "|" + (s or "") + "|"
    for kayit in esleme:
        if kayit.startswith(onek):
            return kayit[len(onek):]
    return ""


def kusak_tabanlari(marka, s, evren, model_alias, donanim, disi, esleme=()):
    """index.html kusakTabanlari() portu: [(taban_anahtarı, kuşak etiketi)] UZUN tabandan
    kısaya. Boş liste = jeton bir kuşak varyantı DEĞİL.

    🔴 TEK YÖNLÜ: kusak_tabanlari('Golf') boştur — taban jeton varyanta katlanmaz.
    🔴 KELİME SINIRI: bölme yalnız gerçek boşlukta olur ('Golf 4' evet, 'Golfr' hayır).
    🔴 KÜRATÖRLÜ BAĞ gramerden ÖNCE gelir ('T4' -> Transporter; gramer bunu göremez)."""
    ham = (s or "").strip()
    if not marka or not ham or ((marka + "|" + ham) in set(disi)):
        return []
    eslenen = kusak_esleme_tabani(marka, ham, esleme)
    if eslenen:
        ea = anahtar(marka, eslenen, evren, model_alias)
        return [(ea, ham)] if ea else []
    kalan = onek_siyir(marka, ham, evren)
    if not kalan:
        return []
    toks = kalan.split()
    out = []
    i = len(toks)
    while i > 1 and kusak_sonek_mi(toks[i - 1], donanim):
        i -= 1
        a = anahtar(marka, " ".join(toks[:i]), evren, model_alias)
        if a:
            out.append((a, " ".join(toks[i:])))
    return out


def anahtar(marka, s, evren, model_alias):
    """index.html modelAnahtar() portu: önek sıyır + kanon + semantik alias.
    BOŞ dönerse eşleşme kurulmaz (fail-closed: '' == '' ile marka geneli dönmesin)."""
    k = kanon(onek_siyir(marka, s, evren))
    if not k:
        return ""
    return model_alias.get((marka, k), k) if marka else k


def _index_oku():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


# Modül düzeyi tablolar (geriye dönük okuyucular için; ayıklama fail-closed).
MARKA_ALIAS, MODEL_ALIAS = tablolar(_index_oku())
KUSAK_DONANIM, KUSAK_DISI, KUSAK_ESLEME = kusak_tablolari(_index_oku())


if __name__ == "__main__":
    import importlib.util

    _s = importlib.util.spec_from_file_location("mm_kanon_cli",
                                                os.path.join(TOOLS, "marka_model_build.py"))
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    _e = _m.MarkaEvreni(_index_oku())
    _marka = os.environ.get("PRUVO_KANON_MARKA", "Ford")
    print("MARKA_ALIAS=%s · MODEL_ALIAS=%s" % (MARKA_ALIAS, MODEL_ALIAS))
    for arg in sys.argv[1:]:
        print("%-22s kanon=%-14s anahtar(%s)=%s"
              % (arg, kanon(arg), _marka, anahtar(_marka, arg, _e, MODEL_ALIAS)))
