#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO marka -> model hiyerarşik gezinme jeneratörü (PİLOT: Ford + BMW).

NEDEN VAR (27 Tem, kök-sorun): ürün sayfaları Google'da KEŞFEDİLMİYOR — iç link yok +
sitemap bayat. Bu modül marka -> model -> ürün CRAWLABLE (SSR, düz <a href>) bir hiyerarşi
üretir; her seçim gerçek bir URL'e gider, içerik ilk yüklemede HTML'de, her sayfa sitemap'e
<lastmod> ile girer. Ayrıca model sayfalarına "bulamadın -> WhatsApp'tan üretelim" bespoke
hunisi basar (attribution-ref.js REF akışıyla ölçülür).

ADDITIVE + İZOLE: build.py bunu main()'de ÇAĞIRIR; kendi urun/ + içerik akışına dokunmaz.
urunler.json DEĞİŞMEZ — normalize BUILD ANINDA kanonik-eşleme (map) ile yapılır (spec §3).

Girdi: (products, ctx). ctx build.py'nin verdiği yardımcılar/sabitler sözlüğü (esc, SITE,
TODAY, snippet'ler, PAGE_CSS, product_url, ...). Dönüş: (sitemap_kayitlari, ust_dizinler).
  sitemap_kayitlari = [(loc, priority, changefreq), ...]  (build.py render_sitemap'e verir)
  ust_dizinler      = ["marka"]  (build.py yayın-içerik-dizinleri manifestine ekler -> deploy kopyalar)

Marka kuralları (CLAUDE.md — ihlal=sessiz hata): "3D baskı/baskı/yazıcı/filament" GEÇMEZ ->
"özel tasarım üretim"/"ölçüye özel"; şehir adı GEÇMEZ; tedarikçi/üreteç/tasarımcı adı GEÇMEZ;
"her renk" YOK -> "farklı renk seçenekleri"; telefon yalnız +90 545 138 6526. Kabul kapısı:
tools/marka-model-test.py.
"""
import os
import re
import json
from urllib.parse import quote
from collections import Counter

WHATSAPP = "905451386526"
WA_TEL_GORUNUR = "+90 545 138 6526"
ESIK = 3                       # model sayfası + marka sayfası yalnız >= ESIK ürünlü için (spec §3.4)

# Marka-düzeyi alias (TANINMIS içinde ayrı yazılan ama AYNI markanın adları). Vauxhall = Opel'in
# İngiltere adı → tek marka sayfası. (MINI/Mini, KIA/Kia gibi büyük/küçük ikizleri markaNorm
# case-fold ile zaten birleşir; bu tablo yalnız markaNorm'un yakalayamadığı ad-eşitlikleri içindir.)
MARKA_ALIAS = {"Vauxhall": "Opel"}

# Türkçe harf -> ascii (slug/canon için)
_TR = {"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
       "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
       "â": "a", "î": "i", "û": "u"}


def _ascii_lower(s):
    s = (s or "").strip().lower()
    return "".join(_TR.get(ch, ch) for ch in s)


def _canon(s):
    """Gruplama anahtarı: küçük harf + boşluk/tire/nokta/alt-çizgi at (spec §3.1).
    'F-150'/'F150'/'F 150' -> 'f150'; 'S-Max'/'S-MAX' -> 'smax'."""
    return re.sub(r"[\s\-\._/]", "", _ascii_lower(s))


def _slug(s):
    """URL slug'ı: küçük harf, alfanümerik dışı -> tek '-'. 'F-150'->'f-150',
    'Focus ST'->'focus-st', 'i3'->'i3', '1 Serisi'->'1-serisi'.
    '+' anlamlıdır (Peugeot 206+ != 206) -> 'plus'; yoksa iki farklı model AYNI URL'e düşer."""
    s = _ascii_lower(s).replace("+", " plus ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _strip_marka_oneki(marka, model_ham, evren):
    """marka[1] modelinin BAŞINDAKI gereksiz marka token'ını sıyır (kanonik marka'ya katlanan):
    'Peugeot 206'->'206', 'Renault 5 E-Tech'->'5 E-Tech', 'Alfa Romeo Giulia'->'Giulia',
    'Vauxhall Astra' (Opel)->'Astra'. TAM-TOKEN eşleşme (en uzun marka öneki önce) + folded marka
    ile aynı olma şartı — substring/yanlış-marka sıyrılmaz. Model TÜMÜYLE markaysa '' döner
    (çağıran marka-only sayar). Böylece 'peugeot206'->'206' mükerreri BİRLEŞİR (spec §9.1),
    'Peugeot Peugeot 206' gibi çift-marka H1 doğmaz. urunler.json DEĞİŞMEZ (yalnız build-anı)."""
    toks = model_ham.split()
    for k in range(len(toks), 0, -1):
        onek = " ".join(toks[:k])
        if evren.taninmis_mi(onek) and evren.katla(onek) == marka:
            return " ".join(toks[k:]).strip()
    return model_ham


# ---- Marka evreni: anasayfa çip küratörlüğü (index.html TANINMIS_MARKALAR) TEK KAYNAK ----
# Çip↔sayfa slug'ı BİREBİR tutsun diye marka listesi + katlama mantığı index.html'den AYIKLANIR
# (kopya tutulmaz; drift olmaz). norm/markaNorm/markaKatla index.html'deki JS ile BİREBİR port.
def _norm(s):
    """index.html norm() portu: Türkçe-duyarlı küçük harf + aksan sadeleştirme."""
    s = (s or "").replace("I", "ı").replace("İ", "i").lower()
    for a, b in (("ı", "i"), ("ç", "c"), ("ğ", "g"), ("ö", "o"),
                 ("ş", "s"), ("ü", "u"), ("â", "a"), ("î", "i")):
        s = s.replace(a, b)
    return s


def _marka_norm(s):
    """index.html markaNorm() portu: norm + é/è/ë->e, ä->a + ayıraç ('and'/&/+) sadeleştirme."""
    n = _norm(s)
    for a, b in (("é", "e"), ("è", "e"), ("ë", "e"), ("ä", "a")):
        n = n.replace(a, b)
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    return re.sub(r"\s+", " ", n).strip()


class MarkaEvreni:
    """index.html'den ayıklanmış marka küratörlüğü: TANINMIS liste + katlama + chip limiti."""

    def __init__(self, index_html):
        m = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", index_html, re.S)
        if not m:
            raise SystemExit("HATA: index.html'de TANINMIS_MARKALAR bulunamadı "
                             "(marka çip küratörlüğü tek kaynağı bozuk).")
        self.taninmis = re.findall(r'"([^"]+)"', m.group(1))
        lm = re.search(r"var MARKA_LIMIT = (\d+);", index_html)
        self.limit = int(lm.group(1)) if lm else 32
        self._kanonik = {}
        for x in self.taninmis:
            self._kanonik[_marka_norm(x)] = x
        self._normlu = [_marka_norm(x) for x in self.taninmis]

    def taninmis_mi(self, m):
        return _marka_norm(m) in self._kanonik

    def katla(self, m):
        """index.html markaKatla() portu + marka-düzeyi alias (Vauxhall->Opel)."""
        n = _marka_norm(m)
        base = self._kanonik.get(n)
        if base is None:
            base = m
            for i, mn in enumerate(self._normlu):
                if n.startswith(mn + " ") or n.startswith(mn + "-"):
                    base = self.taninmis[i]
                    break
        return MARKA_ALIAS.get(base, base)


# Semantik alias (canon_key yakalayamayan TR/EN birleşmeleri, spec §3.1). Pilot: F-Series -> F-Serisi.
_ALIAS = {
    ("Ford", "fseries"): "fserisi",
}

# Kanonik gösterim zorlaması (collision gruplarında doğru yazım — sıklıktan bağımsız, deterministik).
_KANONIK_GOSTERIM = {
    ("Ford", "f150"): "F-150",
    ("Ford", "f250"): "F-250",
    ("Ford", "cmax"): "C-Max",
    ("Ford", "smax"): "S-Max",
    ("Ford", "ecosport"): "EcoSport",
    ("Ford", "e350"): "E-350",
    ("Ford", "f150lightning"): "F-150 Lightning",
    ("Ford", "fserisi"): "F-Serisi",
}

# ---- Pilot model-özel gövde copy (seo/marka-model-pilot-ilan-paketi.md — BİREBİR) ----
# (marka, canon_key) -> {"h1":.., "giris":.., "huni":..}
_PILOT_COPY = {
    ("Ford", "focus"): {
        "h1": "Ford Focus Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Ford Focus'un yıllar içinde kırılan ya da artık bulunamayan plastik parçalarını mı arıyorsunuz? İç trim klipsleri, torpido kapakları, cam kriko dişlisi, konsol tutamakları, ayna braketleri ve kablo kanalları gibi küçük ama aracı zorlayan Focus parçalarını ölçüye özel üretiyoruz. Piyasada kalmayan ya da yalnızca komple set halinde satılan parçaları tek tek, elinizdeki numuneye göre yeniden üretiyoruz — sıradan plastikten değil, parçanın çalışacağı yere göre doğru malzemeden.",
        "huni": "Aradığınız Ford Focus parçasını burada bulamadıysanız üretemeyeceğimiz anlamına gelmez. Kırık ya da eski parçayı bize getirin, ölçelim, doğru malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. Parçanızın fotoğrafını WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına gönderin.",
    },
    ("Ford", "f150"): {
        "h1": "Ford F-150 Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Ford F-150 için bulunamayan ya da kırılan plastik parçaları arıyorsanız doğru yerdesiniz. Ön ızgara bağlantı tırnakları, kaput ve far klipsleri, kasa ve bagaj mandalları, iç konsol parçaları, bardaklık ve kablo kanalları gibi F-150 parçalarını ölçüye özel üretiyoruz. İthal olduğu için ülke genelinde zor bulunan ya da uzun süre beklenen parçaları, elinizdeki numuneden birebir yeniden üretiyoruz.",
        "huni": "F-150 parçanızı listemizde göremediyseniz vazgeçmeyin. Kırık ya da eski parçayı getirin, ölçelim, kullanılacağı yere uygun dayanıklı malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. Numunenizin fotoğrafını WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına iletin.",
    },
    ("Ford", "fiesta"): {
        "h1": "Ford Fiesta Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Ford Fiesta'nın küçük ama can sıkan kırık parçalarını mı arıyorsunuz? Kapı kolu mekanizmaları, cam kriko dişlileri, iç trim klipsleri, torpido ve konsol kapakları, havalandırma ızgarası kanatçıkları gibi Fiesta parçalarını ölçüye özel üretiyoruz. Model eskidikçe piyasadan kalkan bu parçaları elinizdeki numuneye göre tek tek yeniden üretiyoruz.",
        "huni": "Aradığınız Fiesta parçası sitede yoksa üretemeyeceğimiz anlamına gelmez. Kırık parçayı bize ulaştırın, ölçelim, doğru malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. Parçanızın fotoğrafını WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına gönderin.",
    },
    ("Ford", "maverick"): {
        "h1": "Ford Maverick Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Ford Maverick için orijinali zor bulunan iç ve dış plastik parçaları arıyorsanız doğru yerdesiniz. Konsol ve bardaklık modülleri, kasa aksesuar bağlantıları, kapı cebi klipsleri, torpido kapakları ve kablo kanalları gibi Maverick parçalarını ölçüye özel üretiyoruz. Yeni nesil bir model olduğu için yan sanayisi henüz oturmamış bu parçaları, numunenizden birebir yeniden üretiyoruz.",
        "huni": "Maverick parçanızı burada bulamadıysanız bizimle konuşun. Elinizdeki parçayı getirin, ölçelim, çalışacağı yere göre doğru malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. Fotoğrafı WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına iletin.",
    },
    ("Ford", "ranger"): {
        "h1": "Ford Ranger Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Ford Ranger'ın arazi ve iş koşullarında zorlanan plastik parçalarını mı arıyorsunuz? Kasa mandalları ve kilit dilleri, çamurluk ve marşpiyel klipsleri, ön ızgara tırnakları, konsol parçaları ve bağlantı braketleri gibi Ranger parçalarını ölçüye özel üretiyoruz. Arazi ve yük altında kırılan bu parçaları, dayanıklı malzeme seçenekleriyle elinizdeki numuneden yeniden üretiyoruz.",
        "huni": "Ranger parçanız listede yoksa üretemeyeceğimiz anlamına gelmez. Kırık ya da eski parçayı getirin, ölçelim, yük ve dış koşula uygun malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. Numunenizin fotoğrafını WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına gönderin.",
    },
    ("Ford", "transit"): {
        "h1": "Ford Transit Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Ford Transit ve ticari filonuz için sürekli kırılan plastik parçaları mı arıyorsunuz? Kargo bölmesi mandalları, kapı kolu ve menteşe parçaları, konsol ve gösterge çevresi kapakları, kablo kanalları ve raf/bağlantı braketleri gibi Transit parçalarını ölçüye özel üretiyoruz. Yoğun kullanımdan yıpranan ya da artık bulunamayan bu parçaları, numunenizden birebir ve doğru malzemeyle yeniden üretiyoruz.",
        "huni": "Transit'iniz küçük bir parça yüzünden beklemesin. Kırık parçayı getirin ya da fotoğraflayın, ölçelim, dayanıklı malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına yazın, hızlıca dönelim.",
    },
    ("BMW", "e46"): {
        "h1": "BMW E46 Yedek Parça — Ölçüye Özel Üretim",
        "giris": "BMW E46 sahiplerinin en çok zorlandığı yer, artık üretilmeyen küçük plastik parçalardır: kırılan kapı kolu, yerinden çıkan iç trim klipsi, sararıp kırılan havalandırma ızgarası kanatçığı ya da torpido menteşesi. Piyasada bulunamayan bu model-özel parçaları, elinizdeki numuneden milimetrik ölçüp ölçüye özel üretiyoruz. Isıya ve güneşe maruz kalan iç aksam için PETG ve ASA gibi dayanıklı malzeme, daha yüksek mukavemet gereken noktalar için karbon/cam fiber takviyeli seçenekler sunuyoruz; farklı renk seçenekleriyle orijinal dokusuna yakın durur.",
        "huni": "Aradığınız E46 parçasını sitede bulamadıysanız durmayın: kırık ya da eksik parçayı bize getirin, ölçelim ve ölçüye özel üretelim. Ölçü sizden, üretim bizden. Parçanızın fotoğrafını WhatsApp " + WA_TEL_GORUNUR + "'ya gönderin, aynı gün dönüş yapalım.",
    },
    ("BMW", "e36"): {
        "h1": "BMW E36 Yedek Parça — Ölçüye Özel Üretim",
        "giris": "1990'ların BMW E36'sında plastik aksam yıllara yenik düşer; kapı çıta klipsi, konsol parçaları, havalandırma yönlendirici kanatçığı ve tutucular çoğu yerde artık bulunamaz. Bu kırılan, sararan ve piyasada tükenen model-özel parçaları elinizdeki örnekten ölçüye özel üretiyoruz. Kabin içi parçalar için ısıya ve UV'ye dayanıklı malzeme seçer, yük taşıyan bağlantılar için karbon/cam fiber takviyeli seçenekleri konuşuruz.",
        "huni": "E36 için aradığınız parça listede yoksa: numuneyi getirin, ölçelim, ölçüye özel üretelim. Ölçü sizden, üretim bizden. WhatsApp " + WA_TEL_GORUNUR + "'dan parçanızın fotoğrafını iletin.",
    },
    ("BMW", "e30"): {
        "h1": "BMW E30 Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Klasik BMW E30, restorasyon severlerin gözdesidir; ama tam da bu yüzden orijinal plastik parçaları neredeyse tükenmiş durumdadır. Kırılan ızgara tutucusu, kapı paneli klipsi, iç aksam kapakları ve nadir küçük parçalar için artık sıfır yedek bulmak çok zor. Elinizdeki tek sağlam örnekten milimetrik ölçü alıp bu model-özel parçaları ölçüye özel üretiyoruz; klasik aracın dokusuna uygun, güneşe ve ısıya dayanıklı malzemeyle.",
        "huni": "E30 restorasyonunuzda eksik kalan parçayı sitede bulamadıysanız: örneği bize ulaştırın, ölçelim, ölçüye özel üretelim. Ölçü sizden, üretim bizden. WhatsApp " + WA_TEL_GORUNUR + "'ya yazın.",
    },
    ("BMW", "e39"): {
        "h1": "BMW E39 Yedek Parça — Ölçüye Özel Üretim",
        "giris": "BMW E39 5 Serisi'nde en sık kırılan parça, herkesin bildiği havalandırma ızgarası kanatçığı ve kapı kolu mekanizmasının plastik parçalarıdır. Torpido kapağı, konsol tutucuları ve iç trim klipsleri de zamanla kırılıp piyasadan kalkar. Bu bulunamayan model-özel parçaları elinizdeki numuneden ölçüye özel üretiyoruz; kabin sıcaklığına ve güneşe dayanıklı malzeme, gereken yerde karbon/cam fiber takviyeli seçeneklerle.",
        "huni": "E39 için aradığınız parça sitede yoksa: kırık parçayı getirin, ölçelim, ölçüye özel üretelim. Ölçü sizden, üretim bizden. Fotoğrafı WhatsApp " + WA_TEL_GORUNUR + "'ya gönderin.",
    },
    ("BMW", "r1200gs"): {
        "h1": "BMW R1200GS Yedek Parça — Ölçüye Özel Üretim",
        "giris": "BMW R1200GS gibi uzun yol motosikletlerinde düşme, titreşim ve güneş plastik aksamı yıpratır; kırılan ön kaporta parçası, far ve sinyal braketi, el koruma bağlantısı ve çeşitli plastik kılıf parçaları çoğu zaman zor bulunur ya da pahalıdır. Bu model-özel parçaları elinizdeki örnekten ölçüye özel üretiyoruz. Açığa dayanıklı ASA, daha yüksek mukavemet gereken braketlerde karbon/cam fiber takviyeli malzeme seçeneği sunar; parçanın taşıyacağı yükü açıkça konuşur, yük-dışı ve hafif kullanıma uygun olanı öneririz.",
        "huni": "R1200GS'nizde kırılan plastik parçayı sitede bulamadıysanız: numuneyi getirin, ölçelim, doğru malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. WhatsApp " + WA_TEL_GORUNUR + "'ya fotoğraf gönderin.",
    },
    ("BMW", "i3"): {
        "h1": "BMW i3 Yedek Parça — Ölçüye Özel Üretim",
        "giris": "Az sayıda üretilen BMW i3'te küçük bir iç plastik parça bile bulmak uzun bir bekleyişe dönüşebiliyor; kırılan iç trim klipsi, bardaklık ve konsol parçaları, kapak tutucuları için model-özel yedek çoğu yerde yok. Elinizdeki kırık parçayı milimetrik ölçüp ölçüye özel üretiyoruz. Kabin içinde göze batmaması için farklı renk seçenekleri, ısı ve UV'ye dayanıklı malzeme sunuyoruz.",
        "huni": "i3 için aradığınız parça sitede yoksa: kırık parçayı bize getirin, ölçelim, ölçüye özel üretelim. Ölçü sizden, üretim bizden. WhatsApp " + WA_TEL_GORUNUR + "'dan fotoğrafı iletin.",
    },
}

# Marka-özel kısa açıklama (özgün intro için)
_MARKA_GIRIS = {
    "Ford": "Ford'un kırılan ya da artık bulunamayan iç ve dış plastik parçalarını modele göre ölçüye özel üretiyoruz. Modelinizi seçin; klips, tutamak, kapak, braket ve bağlantı gibi parçaları elinizdeki numuneden birebir, çalışacağı yere göre doğru malzemeyle yeniden üretelim.",
    "BMW": "BMW'nin üretimden kalkmış ya da piyasada bulunamayan model-özel plastik parçalarını ölçüye özel üretiyoruz. Modelinizi seçin; kırılan kapı kolu, iç trim klipsi, havalandırma kanatçığı, braket ve kaporta parçalarını numunenizden milimetrik ölçüp doğru malzemeyle yeniden üretelim.",
}


# --------------------------------------------------------------------- veri gruplama
def gruplandir(products, evren):
    """Katalogdaki TANINMIS markaları (marka[0], KATLANMIŞ kanonik) topla:
    kanonik_marka -> {"marka_only":[p...], "gruplar":{canon:{...}}}.
    Grup: {"display":str, "slug":str, "canon":str, "urunler":[p...]}. urunler.json DEĞİŞMEZ.
    Yalnız TANINMIS markalar (anasayfa çip evreni) dahil; model/motor kodu marka[0] atlanır."""
    veri = {}
    for p in products:
        m = p.get("marka") or []
        if not m:
            continue
        ham0 = m[0]
        if not evren.taninmis_mi(ham0):
            continue
        marka = evren.katla(ham0)               # kanonik marka (Mercedes-Benz->Mercedes, Vauxhall->Opel)
        d = veri.get(marka)
        if d is None:
            d = {"marka_only": [], "gruplar": {}, "_spelling": {}}
            veri[marka] = d
        if len(m) < 2 or not (m[1] or "").strip():
            d["marka_only"].append(p)
            continue
        model_ham = _strip_marka_oneki(marka, m[1].strip(), evren)
        if not model_ham:                        # marka[1] tümüyle marka -> marka-only say
            d["marka_only"].append(p)
            continue
        canon = _canon(model_ham)
        canon = _ALIAS.get((marka, canon), canon)
        g = d["gruplar"].get(canon)
        if g is None:
            g = {"canon": canon, "urunler": []}
            d["gruplar"][canon] = g
            d["_spelling"][canon] = Counter()
        g["urunler"].append(p)
        d["_spelling"][canon][model_ham] += 1

    # kanonik gösterim + slug
    for marka, d in veri.items():
        for canon, g in d["gruplar"].items():
            display = _KANONIK_GOSTERIM.get((marka, canon))
            if not display:
                display = d["_spelling"][canon].most_common(1)[0][0]
            g["display"] = display
            g["slug"] = _slug(display)
    return veri


# --------------------------------------------------------------------- HTML yardımcıları
_MM_CSS = """
  .content.mm{max-width:1000px}
  .mm-bc{font-size:13px;color:#8996ad;margin:0 0 14px}
  .mm-bc a{color:var(--navy-2);text-decoration:none}
  .mm-bc a:hover{text-decoration:underline}
  .mm-models{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 8px}
  .mm-model-btn{display:inline-flex;align-items:baseline;gap:7px;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:9px;padding:9px 14px;text-decoration:none;
    color:var(--navy);font-weight:600;font-size:15px}
  .mm-model-btn:hover{border-color:var(--navy-2);background:#fff}
  .mm-model-btn .adet{color:#8996ad;font-weight:500;font-size:12.5px}
  .mm-grid{list-style:none;padding:0;margin:14px 0;display:grid;
    grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px}
  .mm-grid li{margin:0}
  .mm-grid a{display:block;padding:9px 12px;border:1px solid var(--gray-line);border-radius:8px;
    color:#39434f;text-decoration:none;font-size:13.5px;line-height:1.4;background:#fff}
  .mm-grid a:hover{border-color:var(--navy-2);color:var(--navy)}
  .mm-huni{margin:26px 0 6px;padding:18px 20px;border:1px solid var(--gray-line);
    border-radius:12px;background:var(--gray-card)}
  .mm-huni h2{margin:0 0 8px;font-size:18px;color:var(--navy)}
  .mm-huni p{margin:0 0 14px}
  .mm-wa{display:inline-flex;align-items:center;gap:8px;background:#25d366;color:#fff;
    font-weight:700;font-size:15px;text-decoration:none;border-radius:10px;padding:11px 20px}
  .mm-wa:hover{background:#1fb959}
  .mm-sec-h{font-size:16px;color:var(--navy);margin:26px 0 4px}
"""


def _wa_href(esc, prefill):
    """wa.me hedef href — SSR percent-kodlu (boşluk=%20). REF'i attribution-ref.js paid'de
    text sonuna EKLER (organikte eklemez); statik href temiz kalır (huni spec)."""
    return esc("https://wa.me/" + WHATSAPP + "?text=" + quote(prefill))


def _huni_blok(esc, baslik, govde, prefill, cta):
    return (
        '<div class="mm-huni">'
        '<h2>' + esc(baslik) + '</h2>'
        '<p>' + esc(govde) + '</p>'
        '<a class="mm-wa" href="' + _wa_href(esc, prefill) + '" target="_blank" '
        'rel="noopener">' + esc(cta) + '</a>'
        '</div>'
    )


def _shell(ctx, title, canonical_url, description, breadcrumb_ld, collection_ld, body_html):
    esc = ctx["esc"]
    css = ctx["PAGE_CSS"] + _MM_CSS
    return ctx["surumle_scriptler"](u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{ga_head}
{meta_head}
{attribution_head}
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PRUVO">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<script type="application/ld+json">{collection_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<style>{css}</style>
</head>
<body>
<header>
  <div class="header-inner">
    <a class="brand-link" href="/">
      <div class="brand">PRUVO</div>
      <div class="brand-sub">Endüstriyel Parça Üretimi</div>
    </a>
    <a class="top-back" href="/">&larr; Tüm Ürünler</a>
  </div>
</header>

<main class="content mm">
{body}
</main>

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi
  {foot_nav}
  {pay_band}
</footer>
{pv_js}
{ga_banner}
</body>
</html>
""".format(
        title=esc(title) + " — PRUVO",
        desc=esc(description),
        ogtitle=esc(title),
        url=esc(canonical_url),
        favicon=ctx["FAVICON"],
        css=css,
        body=body_html,
        foot_nav=ctx["FOOT_NAV_HTML"],
        pay_band=ctx["PAY_BAND_HTML"],
        pv_js=ctx["PV_SCRIPT_HTML"],
        ga_head=ctx["GA_HEAD_SNIPPET"],
        meta_head=ctx["META_HEAD_SNIPPET"],
        attribution_head=ctx["attribution_head_snippet"](),
        ga_banner=ctx["GA_BANNER_SNIPPET"],
        collection_ld=collection_ld,
        breadcrumb_ld=breadcrumb_ld,
    ))


def _ld(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _urun_grid(ctx, urunler):
    esc = ctx["esc"]
    product_url = ctx["product_url"]
    parts = []
    for p in urunler:
        pid = p.get("id")
        if not pid:
            continue
        parts.append('<li><a href="%s">%s</a></li>'
                     % (esc(product_url(pid)), esc((p.get("baslik") or "").strip() or pid)))
    if not parts:
        return ""
    return '<ul class="mm-grid">' + "".join(parts) + "</ul>"


def _itemlist(ctx, urunler, limit=None):
    product_url = ctx["product_url"]
    ogeler = []
    i = 0
    for p in urunler:
        pid = p.get("id")
        if not pid:
            continue
        i += 1
        ogeler.append({"@type": "ListItem", "position": i,
                       "url": product_url(pid), "name": (p.get("baslik") or "").strip() or pid})
        if limit and i >= limit:
            break
    return ogeler


# --------------------------------------------------------------------- sayfa üreticileri
def _model_sayfasi(ctx, marka, g):
    esc = ctx["esc"]
    SITE = ctx["SITE"]
    display = g["display"]
    marka_slug = _slug(marka)
    url = SITE + "/marka/" + marka_slug + "/" + g["slug"] + "/"
    marka_url = SITE + "/marka/" + marka_slug + "/"
    copy = _PILOT_COPY.get((marka, g["canon"]))

    if copy:
        h1 = copy["h1"]
        giris = copy["giris"]
        huni_govde = copy["huni"]
    else:
        h1 = marka + " " + display + " Yedek Parça — Ölçüye Özel Üretim"
        giris = (marka + " " + display + " için kırılan ya da artık bulunamayan plastik "
                 "parçaları mı arıyorsunuz? Klipsler, kapak ve tutamaklar, dişliler, "
                 "braketler, kablo kanalları ve bağlantı parçaları gibi küçük ama önemli "
                 + display + " parçalarını ölçüye özel üretiyoruz. Piyasada kalmayan bu "
                 "parçaları elinizdeki numuneden birebir, sıradan plastikten değil parçanın "
                 "çalışacağı yere göre doğru malzemeden, farklı renk seçenekleriyle yeniden "
                 "üretiyoruz.")
        huni_govde = ("Aradığınız " + marka + " " + display + " parçasını listede "
                      "bulamadıysanız üretemeyeceğimiz anlamına gelmez. Kırık ya da eski "
                      "parçayı bize getirin ya da fotoğraflayın; milimetrik ölçüp, "
                      "çalışacağı yere göre doğru malzemeyle ölçüye özel üretelim. Ölçü "
                      "sizden, üretim bizden. Parçanızın fotoğrafını WhatsApp'tan "
                      + WA_TEL_GORUNUR + " numarasına gönderin.")

    n = len(g["urunler"])
    description = (marka + " " + display + " için bulunamayan ya da kırılan plastik yedek "
                  "parçaları numunenizden ölçüye özel üretiyoruz. " + str(n) + " parça "
                  "listeleniyor; bulamadığınızı WhatsApp'tan üretelim.")

    prefill = ("Merhaba, " + marka + " " + display + " için bir parça arıyorum, sitede "
               "bulamadım. Elimdeki numuneyi ölçüp ölçüye özel üretebilir misiniz? "
               "Fotoğrafını iletiyorum.")

    # breadcrumb (görünür)
    bc = ('<nav class="mm-bc" aria-label="breadcrumb"><a href="/">Ana Sayfa</a> &rsaquo; '
          '<a href="' + esc(marka_url) + '">' + esc(marka) + '</a> &rsaquo; '
          + esc(display) + '</nav>')

    huni = _huni_blok(esc, marka + " " + display + " parçanızı bulamadınız mı?",
                      huni_govde, prefill, "WhatsApp'tan Yazın")

    body = (bc
            + '<h1>' + esc(h1) + '</h1>'
            + '<p class="lead">' + esc(giris) + '</p>'
            + '<h2 class="mm-sec-h">' + esc(display) + ' parçaları (' + str(n) + ')</h2>'
            + _urun_grid(ctx, g["urunler"])
            + huni)

    breadcrumb_ld = _ld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": marka, "item": marka_url},
            {"@type": "ListItem", "position": 3, "name": marka + " " + display, "item": url},
        ],
    })
    collection_ld = _ld({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": h1, "url": url, "description": description,
        "mainEntity": {"@type": "ItemList", "numberOfItems": n,
                       "itemListElement": _itemlist(ctx, g["urunler"])},
    })
    html = _shell(ctx, h1, url, description, breadcrumb_ld, collection_ld, body)
    return url, html


def _marka_sayfasi(ctx, marka, d, buyuk_gruplar, kucuk_urunler):
    esc = ctx["esc"]
    SITE = ctx["SITE"]
    marka_slug = _slug(marka)
    url = SITE + "/marka/" + marka_slug + "/"

    h1 = marka + " Yedek Parça — Ölçüye Özel Üretim"
    toplam = sum(len(g["urunler"]) for g in buyuk_gruplar) + len(kucuk_urunler) + len(d["marka_only"])
    giris = _MARKA_GIRIS.get(marka, (
        marka + " için kırılan ya da artık bulunamayan plastik parçaları modele göre ölçüye "
        "özel üretiyoruz. Modelinizi seçin; klips, kapak, tutamak, dişli, braket ve bağlantı "
        "gibi parçaları elinizdeki numuneden birebir, çalışacağı yere göre doğru malzemeyle "
        "yeniden üretelim. Ölçü sizden, üretim bizden."))
    description = (marka + " yedek parçaları: modele göre gezinin, kırılan ya da bulunamayan "
                   "parçayı ölçüye özel üretelim. " + str(len(buyuk_gruplar)) + " model, "
                   + str(toplam) + " parça listeleniyor.")

    bc = ('<nav class="mm-bc" aria-label="breadcrumb"><a href="/">Ana Sayfa</a> &rsaquo; '
          '<a href="/marka/">Markalar</a> &rsaquo; ' + esc(marka) + '</nav>')

    # model butonları (>= ESIK)
    btns = []
    for g in buyuk_gruplar:
        murl = "/marka/" + marka_slug + "/" + g["slug"] + "/"
        btns.append('<a class="mm-model-btn" href="%s">%s<span class="adet">%d parça</span></a>'
                    % (esc(murl), esc(g["display"]), len(g["urunler"])))
    model_html = '<div class="mm-models">' + "".join(btns) + "</div>" if btns else ""

    # diğer parçalar: <ESIK modeller + yalnız-marka ürünler (hepsi crawlable link)
    diger = list(kucuk_urunler) + list(d["marka_only"])
    diger_html = ""
    if diger:
        diger_html = ('<h2 class="mm-sec-h">Diğer ' + esc(marka)
                      + ' parçaları (' + str(len(diger)) + ')</h2>'
                      + _urun_grid(ctx, diger))

    prefill = ("Merhaba, " + marka + " için bir parça arıyorum, sitede bulamadım. Elimdeki "
               "numuneyi ölçüp ölçüye özel üretebilir misiniz?")
    huni_govde = (marka + " için aradığınız parçayı sitede bulamadıysanız ya da modelinizi "
                  "listede göremediyseniz bizimle konuşun. Elinizdeki kırık veya eski parçayı "
                  "ölçüp, çalışacağı yere göre doğru malzemeyle ölçüye özel üretiyoruz. Ölçü "
                  "sizden, üretim bizden. Parçanızın fotoğrafını WhatsApp'tan "
                  + WA_TEL_GORUNUR + " numarasına gönderin.")
    huni = _huni_blok(esc, marka + " parçanızı bulamadınız mı?", huni_govde, prefill,
                      "WhatsApp'tan Yazın")

    body = (bc
            + '<h1>' + esc(h1) + '</h1>'
            + '<p class="lead">' + esc(giris) + '</p>'
            + ('<h2 class="mm-sec-h">Modele göre seçin</h2>' if btns else "")
            + model_html
            + diger_html
            + huni)

    breadcrumb_ld = _ld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Markalar", "item": SITE + "/marka/"},
            {"@type": "ListItem", "position": 3, "name": marka, "item": url},
        ],
    })
    # ItemList = model sayfaları (crawl hedefleri)
    model_items = [{"@type": "ListItem", "position": i + 1,
                    "url": SITE + "/marka/" + marka_slug + "/" + g["slug"] + "/",
                    "name": marka + " " + g["display"]}
                   for i, g in enumerate(buyuk_gruplar)]
    collection_ld = _ld({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": h1, "url": url, "description": description,
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(model_items),
                       "itemListElement": model_items},
    })
    html = _shell(ctx, h1, url, description, breadcrumb_ld, collection_ld, body)
    return url, html


def _marka_index(ctx, ozet):
    """/marka/ — marka dizini (tüm üretilen markalar). ozet = [(marka, marka_url, model_sayisi, parca_sayisi), ...]"""
    esc = ctx["esc"]
    SITE = ctx["SITE"]
    url = SITE + "/marka/"
    h1 = "Markaya ve Modele Göre Yedek Parça"
    description = ("Markanızı ve modelinizi seçin; kırılan ya da bulunamayan plastik yedek "
                   "parçayı numunenizden ölçüye özel üretelim. Ölçü sizden, üretim bizden.")
    bc = '<nav class="mm-bc" aria-label="breadcrumb"><a href="/">Ana Sayfa</a> &rsaquo; Markalar</nav>'
    btns = []
    for marka, marka_url, msay, psay in ozet:
        btns.append('<a class="mm-model-btn" href="%s">%s<span class="adet">%d model · %d parça</span></a>'
                    % (esc("/marka/" + _slug(marka) + "/"), esc(marka), msay, psay))
    body = (bc
            + '<h1>' + esc(h1) + '</h1>'
            + '<p class="lead">' + esc(description) + '</p>'
            + '<div class="mm-models">' + "".join(btns) + '</div>')
    breadcrumb_ld = _ld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Markalar", "item": url},
        ],
    })
    items = [{"@type": "ListItem", "position": i + 1, "url": marka_url, "name": marka}
             for i, (marka, marka_url, _m, _p) in enumerate(ozet)]
    collection_ld = _ld({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": h1, "url": url, "description": description,
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": items},
    })
    return url, _shell(ctx, h1, url, description, breadcrumb_ld, collection_ld, body)


def _chip_link_html(esc, marka, slug, aktif=False):
    """SSR anasayfa marka çipi: JS-siz curl'de görünen düz <a> (discovery kök-fix)."""
    return ('<a class="brand-btn brand-link%s" href="/marka/%s/">%s</a>'
            % (" active" if aktif else "", esc(slug), esc(marka)))


# --------------------------------------------------------------------- ana giriş
def uret(products, ctx):
    """Anasayfa çip-marka evrenindeki (index.html TANINMIS_MARKALAR) TÜM markalar için
    /marka/<marka>/ (+ >=3-ürünlü model sayfaları) üretir. ctx['ROOT']/index.html'den marka
    listesini AYIKLAR (çip↔sayfa slug birebir). urunler.json DEĞİŞMEZ.
    Dönüş: {"sitemap":[...], "dizinler":["marka"], "chip_links":"<a..>", "slug_map":{marka:slug},
            "sayim":{...}, "chip_markalar":[...], "sayfasiz_cipler":[...]}."""
    ROOT = ctx["ROOT"]
    SITE = ctx["SITE"]
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        evren = MarkaEvreni(f.read())
    veri = gruplandir(products, evren)

    def yaz(url, html):
        yol = url[len(SITE):].strip("/")          # "marka/ford/focus"
        klasor = os.path.join(ROOT, *yol.split("/"))
        os.makedirs(klasor, exist_ok=True)
        with open(os.path.join(klasor, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    # Marka sayfası eşiği: >= ESIK toplam ürünlü kanonik markalar (ince marka sayfası olmasın).
    marka_toplam = {marka: (sum(len(g["urunler"]) for g in d["gruplar"].values())
                            + len(d["marka_only"]))
                    for marka, d in veri.items()}
    sayfali_markalar = sorted([m for m, t in marka_toplam.items() if t >= ESIK],
                              key=lambda m: (-marka_toplam[m], m))

    sitemap = []
    slug_gorulen = {}   # (marka_slug, model_slug) -> canon (model collision nöbeti)
    marka_slug_gorulen = {}   # marka_slug -> marka (marka slug collision nöbeti)
    slug_map = {}       # kanonik marka -> slug (JS çip linki için; yalnız sayfası olan markalar)
    sayim = {}
    index_ozet = []

    for marka in sayfali_markalar:
        d = veri[marka]
        marka_slug = _slug(marka)
        if marka_slug in marka_slug_gorulen and marka_slug_gorulen[marka_slug] != marka:
            raise SystemExit("HATA: marka slug collision — %s hem %r hem %r (folding bozuk)."
                             % (marka_slug, marka_slug_gorulen[marka_slug], marka))
        marka_slug_gorulen[marka_slug] = marka
        slug_map[marka] = marka_slug

        gruplar = list(d["gruplar"].values())
        for g in gruplar:
            anahtar = (marka_slug, g["slug"])
            if anahtar in slug_gorulen and slug_gorulen[anahtar] != g["canon"]:
                raise SystemExit(
                    "HATA: marka/model slug collision — %s/%s hem %r hem %r canon'a düşüyor "
                    "(normalize-map bozuk)." % (marka_slug, g["slug"],
                                                slug_gorulen[anahtar], g["canon"]))
            slug_gorulen[anahtar] = g["canon"]

        buyuk = sorted([g for g in gruplar if len(g["urunler"]) >= ESIK],
                       key=lambda g: (-len(g["urunler"]), g["slug"]))
        kucuk_urunler = []
        for g in gruplar:
            if len(g["urunler"]) < ESIK:
                kucuk_urunler.extend(g["urunler"])

        murl, mhtml = _marka_sayfasi(ctx, marka, d, buyuk, kucuk_urunler)
        yaz(murl, mhtml)
        sitemap.append((murl, "0.7", "weekly"))

        for g in buyuk:
            url, html = _model_sayfasi(ctx, marka, g)
            yaz(url, html)
            sitemap.append((url, "0.7", "weekly"))

        sayim[marka] = {"marka_sayfasi": 1, "model_sayfasi": len(buyuk),
                        "toplam_parca": marka_toplam[marka]}
        index_ozet.append((marka, murl, len(buyuk), marka_toplam[marka]))

    # /marka/ index (tüm üretilen markalar)
    iurl, ihtml = _marka_index(ctx, index_ozet)
    yaz(iurl, ihtml)
    sitemap.append((iurl, "0.6", "weekly"))

    # Anasayfa çipleri: JS sortedBrands ile AYNI = TANINMIS + ürün sayısına göre azalan, top MARKA_LIMIT.
    # Yalnız SAYFASI OLAN markalar link olur; sayfası olmayan (çok nadir, <3 ürün) NOT'a düşer.
    chip_sirasi = sorted(marka_toplam.keys(), key=lambda m: (-marka_toplam[m], m))
    chip_markalar = chip_sirasi[:evren.limit]
    chip_links = "".join(_chip_link_html(ctx["esc"], m, slug_map[m])
                         for m in chip_markalar if m in slug_map)
    sayfasiz_cipler = [m for m in chip_markalar if m not in slug_map]

    ctx.setdefault("_mm_sayim", {}).update(sayim)
    return {
        "sitemap": sitemap,
        "dizinler": ["marka"],
        "chip_links": chip_links,
        "slug_map": slug_map,
        "chip_markalar": chip_markalar,
        "sayfasiz_cipler": sayfasiz_cipler,
        "sayim": sayim,
        "marka_sayfasi_sayisi": len(sayfali_markalar),
        "model_sayfasi_sayisi": sum(s["model_sayfasi"] for s in sayim.values()),
    }
