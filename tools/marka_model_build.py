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


def kategori_evreni(index_html):
    """KAPSAM doğrulaması için GEÇERLİ kategori listesi — index.html'den AYIKLANIR
    (CATEGORIES + GIZLI_KATEGORILER; build.py CATEGORIES+NAV_GIZLI ile birebir eş).
    Kopya TUTULMAZ: kategori eklenince/çıkınca kapsam kapısı kendiliğinden izler.
    Bulunamazsa HATA — fail-closed: sessizce boş listeye düşerse HER kapsam "geçersiz"
    olurdu; jeneratör o durumda hiç sayfa yazmasın."""
    out = []
    for ad in ("CATEGORIES", "GIZLI_KATEGORILER"):
        m = re.search(r"var " + ad + r" = \[(.*?)\];", index_html, re.S)
        if not m:
            raise SystemExit("HATA: index.html'de %s bulunamadı "
                             "(marka kapsamı kategori evreni tek kaynağı bozuk)." % ad)
        out.extend(re.findall(r'"([^"]+)"', m.group(1)))
    if not out:
        raise SystemExit("HATA: index.html kategori evreni BOŞ (kapsam doğrulaması yapılamaz).")
    return out


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
        "huni": "Transit'iniz küçük bir parça yüzünden beklemesin. Kırık parçayı getirin ya da kargoyla gönderin, ölçelim, dayanıklı malzemeyle ölçüye özel üretelim. Ölçü sizden, üretim bizden. WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına yazın, hızlıca dönelim.",
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
def marka_uyelikleri(marka_dizisi, evren):
    """Ürünün marka[] dizisinden ÜYE OLDUĞU kanonik marka sayfalarını çıkarır — index.html
    marka FİLTRESİYLE birebir aynı yüklem: `(p.marka||[]).some(b => markaKatla(b) === hedef)`.
    Yani HER eleman (yalnız marka[0] değil) katlanır, tanınmışsa üyelik doğar; sıra korunur,
    tekrar tekilleşir. İkinci bir katlama tablosu YOK — kaynak evren.katla (index.html portu).

    ÖLÇÜLEN SESSİZ HATA (31 Tem): eski kod üyeliği HAM marka[0] ile ölçüyordu
    (taninmis_mi(ham0)); "Volvo Penta" (21 Marin) ve "Mercedes-Benz" (20) ham hâlde tanınmış
    listede olmadığı için 41 ürün HİÇBİR marka sayfasına girmiyordu — katalogda var, marka
    sayfasında yok, kimse görmüyordu."""
    uyeler = []
    for x in marka_dizisi:
        kan = evren.katla((x or "").strip())
        if kan and evren.taninmis_mi(kan) and kan not in uyeler:
            uyeler.append(kan)
    return uyeler


def marka_mi(deger, evren):
    """marka[1] MODEL mi yoksa (çok markalı uyumluluktan gelen) BAŞKA BİR MARKA mı?
    KATI ölçüt: değerin KENDİSİ tanınmış marka listesinde olmalı ("Citroen", "Vauxhall",
    "Lexus"). "Peugeot 206"/"Volvo 240" gibi marka ÖNEKLİ değerler MODEL kalır — katlanmış
    hâline bakmak model kırılımını (SEO'nun ana ekseni) yok ederdi."""
    return bool((deger or "").strip()) and evren.taninmis_mi(deger.strip())


def marka_urun_sayisi(d):
    """Bir marka kovasının SAYFASINDA görünecek ürün sayısı — TEK KAYNAK.
    Eşik (ESIK), çip sıralaması, sayfa metni ve kabul testleri AYNI bu fonksiyonu çağırır;
    ikinci bir toplama formülü YAZILMAZ (formül kopyası kaçınılmaz olarak ayrışır: 31 Tem'de
    ölçüldü — ikincil ürünler eklenince jeneratör ile testin sayısı ayrıştı)."""
    return (sum(len(g["urunler"]) for g in d["gruplar"].values())
            + len(d["marka_only"]) + len(d.get("ikincil", [])))


def gruplandir(products, evren):
    """Katalogdaki TANINMIS markaları topla:
    kanonik_marka -> {"marka_only":[p...], "ikincil":[p...], "gruplar":{canon:{...}}}.
    Grup: {"display":str, "slug":str, "canon":str, "urunler":[p...]}. urunler.json DEĞİŞMEZ.

    ÜYELİK  : marka_uyelikleri() — index.html filtresiyle birebir (KATLANMIŞ ad; her eleman).
    BİRİNCİL: marka[0]'ın katlanmışı (tanınmıyorsa ilk tanınmış üye). Model kırılımı YALNIZ
              birincil markada açılır; diğer üyeler ürünü "ikincil" olarak listeler.
    MODEL   : yalnız marka[1], ve marka[1] KENDİSİ bir marka DEĞİLSE (marka_mi). Çok markalı
              uyumluluk kaydı ("Peugeot"+"Citroen") anlamsız /marka/peugeot/citroen/ sayfası
              DOĞURMAZ; ürün her iki marka sayfasında da görünür."""
    veri = {}

    def kova(marka):
        d = veri.get(marka)
        if d is None:
            d = {"marka_only": [], "ikincil": [], "gruplar": {}, "_spelling": {}}
            veri[marka] = d
        return d

    for p in products:
        m = p.get("marka") or []
        if not m:
            continue
        uyeler = marka_uyelikleri(m, evren)
        if not uyeler:
            continue
        ham0_kan = evren.katla((m[0] or "").strip())
        birincil = ham0_kan if evren.taninmis_mi(ham0_kan) else uyeler[0]
        d = kova(birincil)
        for kan in uyeler:                       # diğer üye markaların sayfasına da GİR
            if kan != birincil:
                kova(kan)["ikincil"].append(p)
        m1 = (m[1] or "").strip() if len(m) > 1 else ""
        if birincil != ham0_kan or not m1 or marka_mi(m1, evren):
            d["marka_only"].append(p)            # model kırılımı YOK (marka-only / çok markalı)
            continue
        model_ham = _strip_marka_oneki(birincil, m1, evren)
        if not model_ham:                        # marka[1] tümüyle marka -> marka-only say
            d["marka_only"].append(p)
            continue
        marka = birincil
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
  /* Ürün-liste kartı = sitenin STANDART katalog kartı (index.html kartCiz ile BİREBİR sınıf/
     yapı/CSS). Kart CSS'i PAGE_CSS'te YOK (ürün sayfası tek ürün gösterir) -> buraya kopyalandı;
     :root değişkenleri (--radius/--shadow/--navy/--gray-*) PAGE_CSS'te tanımlı. */
  .content.mm .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
    gap:20px;margin:14px 0}
  .content.mm .card{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;
    box-shadow:var(--shadow);transition:transform .15s, box-shadow .15s}
  .content.mm .card:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(18,41,77,.14)}
  .content.mm .card-main{display:flex;flex-direction:column;flex:1;text-decoration:none;
    color:inherit;position:relative}
  .content.mm .card-badge{position:absolute;top:10px;left:10px;z-index:2;background:#f7b500;
    color:#12294d;font-size:11px;font-weight:800;letter-spacing:.3px;padding:5px 11px;
    border-radius:14px;box-shadow:0 2px 7px rgba(0,0,0,.20)}
  .content.mm .card-img{width:100%;aspect-ratio:4/3;object-fit:cover;background:#dbe2ec;display:block}
  .content.mm .card-body{padding:14px 15px 16px;display:flex;flex-direction:column;flex:1}
  .content.mm .card-cat{display:inline-block;align-self:flex-start;background:var(--navy);
    color:#fff;font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;
    padding:3px 9px;border-radius:20px;margin-bottom:9px}
  .content.mm .card-title{font-size:16px;font-weight:700;margin-bottom:6px;line-height:1.3;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .content.mm .card-desc{font-size:13.5px;color:var(--gray-text);margin-bottom:12px;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .content.mm .card-price{font-size:16px;font-weight:800;color:var(--navy);margin-top:auto}
  .content.mm .card-price.empty{color:var(--gray-text);font-weight:600;font-size:13px}
  @media (max-width:520px){
    .content.mm .grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}
  }
  .mm-huni{margin:26px 0 6px;padding:18px 20px;border:1px solid var(--gray-line);
    border-radius:12px;background:var(--gray-card)}
  .mm-huni h2{margin:0 0 8px;font-size:18px;color:var(--navy)}
  .mm-huni p{margin:0 0 14px}
  .mm-wa{display:inline-flex;align-items:center;gap:8px;background:#25d366;color:#fff;
    font-weight:700;font-size:15px;text-decoration:none;border-radius:10px;padding:11px 20px}
  .mm-wa:hover{background:#1fb959}
  .mm-sec-h{font-size:16px;color:var(--navy);margin:26px 0 4px}
  /* KAPSAM şeridi (?kategori=<Kategori> ile gelindiğinde JS açar; kanonik/parametresiz
     sayfada display:none kalır → crawler tam koleksiyonu görür, SEO regresyonu yok). */
  .mm-kapsam{margin:0 0 14px;padding:10px 14px;border:1px solid var(--gray-line);
    border-radius:9px;background:var(--gray-card);font-size:14px;color:var(--navy)}
  .mm-kapsam a{color:var(--navy-2);font-weight:600;margin-left:8px}
  .mm-bos{margin:18px 0;color:var(--gray-text);font-size:15px}
"""


# ---- KAPSAM (marka × kategori) — anasayfa çipinden gelen ?kategori= görünüm parametresi ----
# NEDEN VAR (Okan, 30 Tem — SESSİZ hata): çok-dikeyli markalar (Yamaha 6 dikey, Suzuki 5,
# BMW 4, Volvo 2) tek marka kovasında birleşiyordu; Marin'de Yamaha'ya basan müşteriye
# motosiklet/elektronik parçası çıkıyor, kimse hatayı GÖRMÜYOR, satış sessizce kaybediliyordu.
# KARAR: yeni marka adı UYDURULMAZ ("Yamaha Marine" aramayı böler + Ege eşleşmesini kırar);
# ayırt edici zaten var → marka + kategori ÇİFTİ. Kapsam bir GÖRÜNÜM parametresidir:
#   · kanonik URL /marka/<slug>/ AYNEN kalır (rel=canonical parametresizi gösterir),
#   · sitemap'e YENİ girdi girmez (yeni URL ailesi açılmaz),
#   · parametresiz gelindiğinde sayfaya HİÇ dokunulmaz (crawler tam koleksiyonu görür).
# FAIL-CLOSED: kapsam varken kategorisi bilinmeyen öğe GİZLENİR; geçersiz/bilinmeyen kategori
# HİÇBİR ürünü göstermez (sessizce tüm kataloğu göstermek = sessiz hata).
# Test bu bloğu MARKER'lardan ayıklayıp node ile GERÇEKTEN koşar → tools/marka-kapsam-test.py.
_KAPSAM_JS_BAS = "/* PRUVO MARKA KAPSAMI BAS */"
_KAPSAM_JS_SON = "/* PRUVO MARKA KAPSAMI SON */"

_KAPSAM_JS_GOVDE = r"""
(function(g){
  var KATEGORILER = __KATEGORILER__;
  // ham parametre -> karar. {aktif:kapsam var mı, gecerli:tanınan kategori mi, kategori:ad}
  function coz(ham, gecerliler){
    if(ham === null || ham === undefined || ham === ""){
      return {aktif:false, gecerli:true, kategori:null};
    }
    if(!gecerliler || gecerliler.indexOf(ham) === -1){
      return {aktif:true, gecerli:false, kategori:ham};
    }
    return {aktif:true, gecerli:true, kategori:ham};
  }
  // Tek öğe görünür mü. FAIL-CLOSED: geçersiz kapsam -> hiçbir şey; kategorisi
  // OKUNAMAYAN öğe (data-kat yok/boş) kapsam aktifken GİZLENİR (kaçak yok).
  function gorunur(ogeKat, c){
    if(!c || !c.aktif){ return true; }
    if(!c.gecerli){ return false; }
    if(!ogeKat){ return false; }
    return ogeKat === c.kategori;
  }
  // Model butonunun kapsam içindeki parça sayısı (data-katsay = {"Marin":3,...}).
  // Bozuk/eksik JSON -> 0 (fail-closed; buton gizlenir, yanlış sayı gösterilmez).
  function sayimla(katSayimJson, c){
    var tablo = {};
    try{ tablo = JSON.parse(katSayimJson || "{}") || {}; }catch(e){ tablo = {}; }
    var toplam = 0, k;
    for(k in tablo){
      if(Object.prototype.hasOwnProperty.call(tablo, k)){ toplam += tablo[k]; }
    }
    if(!c || !c.aktif){ return toplam; }
    if(!c.gecerli){ return 0; }
    return tablo[c.kategori] || 0;
  }
  // Kapsamı bir sonraki adıma taşıyan sorgu dizesi (geçersiz kapsam TAŞINMAZ).
  function sorgu(c){
    if(!c || !c.aktif || !c.gecerli){ return ""; }
    return "?kategori=" + encodeURIComponent(c.kategori);
  }
  function yazSayim(dok, sec, deger){
    var el = dok.querySelectorAll(sec), i;
    for(i = 0; i < el.length; i++){ el[i].textContent = String(deger); }
  }
  function uygula(dok, loc){
    var ham = null;
    try{
      ham = new URLSearchParams((loc && loc.search) || "").get("kategori");
    }catch(e){ ham = null; }
    var c = coz(ham, KATEGORILER);
    if(!c.aktif){ return c; }   // KANONİK/parametresiz -> sayfaya DOKUNMA (SEO regresyonu yok)

    var i, kartlar = dok.querySelectorAll(".card[data-kat]"), gorunenKart = 0;
    for(i = 0; i < kartlar.length; i++){
      var ac = gorunur(kartlar[i].getAttribute("data-kat"), c);
      kartlar[i].style.display = ac ? "" : "none";
      if(ac){ gorunenKart++; }
    }
    var btnlar = dok.querySelectorAll(".mm-model-btn[data-katsay]"), gorunenModel = 0;
    for(i = 0; i < btnlar.length; i++){
      var n = sayimla(btnlar[i].getAttribute("data-katsay"), c);
      btnlar[i].style.display = n > 0 ? "" : "none";
      if(n > 0){
        gorunenModel++;
        var ad = btnlar[i].querySelector(".adet");
        if(ad){ ad.textContent = n + " parça"; }
        var h = btnlar[i].getAttribute("href");
        if(h && h.indexOf("?") === -1){ btnlar[i].setAttribute("href", h + sorgu(c)); }
      }
    }
    // kapsam bir sonraki sayfada da sürsün (breadcrumb / marka geri-linki)
    var tasi = dok.querySelectorAll("a[data-kapsam-tasi]");
    for(i = 0; i < tasi.length; i++){
      var ht = tasi[i].getAttribute("href");
      if(ht && ht.indexOf("?") === -1){ tasi[i].setAttribute("href", ht + sorgu(c)); }
    }
    yazSayim(dok, ".mm-sayim-kart", gorunenKart);
    yazSayim(dok, ".mm-sayim-model", gorunenModel);

    // GÖRÜNÜR kapsam şeridi + kapsamı KALDIRMA yolu (kanonik, parametresiz adres).
    // Metin textContent ile yazılır (innerHTML YOK) -> URL'den gelen değer kod olamaz.
    var not = dok.getElementById("kapsamNot");
    if(not){ not.style.display = ""; }
    var metin = dok.getElementById("kapsamNotMetin");
    if(metin){
      metin.textContent = c.gecerli
        ? ("Kapsam: yalnız " + c.kategori + " kategorisi — " + gorunenKart + " parça")
        : ("Geçersiz kapsam: “" + c.kategori + "” bir kategori değil — " +
           "sonuç gösterilmiyor.");
    }
    var sifirla = dok.getElementById("kapsamNotSifirla");
    if(sifirla && loc && loc.pathname){ sifirla.setAttribute("href", loc.pathname); }
    var bos = dok.getElementById("kapsamBos");
    if(bos){ bos.style.display = (gorunenKart === 0 && gorunenModel === 0) ? "" : "none"; }
    return c;
  }
  g.PRUVO_KAPSAM = {coz: coz, gorunur: gorunur, sayimla: sayimla, sorgu: sorgu,
                    uygula: uygula, KATEGORILER: KATEGORILER};
})(typeof window !== "undefined" ? window : globalThis);
"""

_KAPSAM_JS_CAGRI = """
if(typeof window !== "undefined" && window.PRUVO_KAPSAM){
  try{ window.PRUVO_KAPSAM.uygula(document, window.location); }
  catch(e){ console.error("Kapsam uygulanamadi:", e); }
}
"""


def kapsam_scripti(kategoriler):
    """Sayfaya gömülecek KAPSAM scripti (marker'lı; test buradan ayıklayıp node'da koşar)."""
    govde = _KAPSAM_JS_GOVDE.replace(
        "__KATEGORILER__", json.dumps(kategoriler, ensure_ascii=False, separators=(",", ":")))
    return ("<script>" + _KAPSAM_JS_BAS + govde + _KAPSAM_JS_SON
            + _KAPSAM_JS_CAGRI + "</script>")


def _kapsam_not_html(esc):
    """Kapsam şeridi + boş-sonuç uyarısı (SSR'de GİZLİ; yalnız ?kategori= ile JS açar)."""
    return ('<div class="mm-kapsam" id="kapsamNot" style="display:none">'
            '<span id="kapsamNotMetin"></span>'
            '<a id="kapsamNotSifirla" href="./">' + esc("Tüm kategoriler") + '</a>'
            '</div>'
            '<p class="mm-bos" id="kapsamBos" style="display:none">'
            + esc("Bu kapsamda listelenen parça yok. Aradığınızı WhatsApp'tan yazın, "
                  "ölçüye özel üretelim.") + '</p>')


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


def _shell(ctx, title, canonical_url, description, breadcrumb_ld, collection_ld, body_html,
           kapsam_js=""):
    esc = ctx["esc"]
    # Taban CSS artik SAYFAYA GOMULMEZ: kritik cekirdek satir-ici, gerisi icerik-adresli
    # /varlik/sayfa-<hash>.css. _MM_CSS AYRI bir varliga gider -> taban dosya urun/icerik/
    # marka/hub sayfalarinda AYNI dosyadir (ikinci kopya uretilmez).
    stil = ctx["stil_bloklari"](_MM_CSS)
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
{stil}
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
{kapsam_js}
</body>
</html>
""".format(
        title=esc(title) + " — PRUVO",
        desc=esc(description),
        ogtitle=esc(title),
        url=esc(canonical_url),
        favicon=ctx["FAVICON"],
        stil=stil,
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
        kapsam_js=kapsam_js,
    ))


def _ld(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ---- KART-ÖZEL marka-kuralı temizleyicisi (CLAUDE.md "3D BASKI DENMEZ") ----
# YALNIZ kart BAŞLIĞINDA (baslik) çağrılır -> Merchant feed + /urun/ sayfası BYTE aynı kalır
# (build.py marka_temiz / render_merchant_feed / render_product DEĞİŞMEZ). (Kart açıklaması 27 Tem
# KALDIRILDI; temizleyici başlığı /urun/ sayfasıyla tutarlı kılmak için başlıkta korunur.)
#
# 🔴 FAIL-SAFE (çürütücü over-clean bulgusu, 27 Tem): Türkçe "baskı" hem PRINTING hem BASINÇ/press
# demektir (baskı plakası=debriyaj, baskı balata, baskı uygula/altında=basınç, rulman baskısı=press,
# baskıyı hizala=debriyaj). "basıl" hem "üretilir/printed" hem "düğmeye basılır/button-press".
# İLKE: bir basınç/buton anlamını mangle etmektense belirsizi KORU. Bu yüzden BARE "baskı" (tüm
# çekimleri) ve tüm "basma/basmak" ASLA çevrilmez; "basıl" YALNIZ printing bağlamında (buton
# yakınında/önle-engelle-karşı DEĞİL) çevrilir. Çevrilenler = kesin/açık printing:
_KART_BILESIK = [   # bileşik/çok-kelime — açık printing, basınç ambiguity YOK
    (re.compile(r"3\s*[dD]\s*[-\s]?bask[ıi]\w*", re.I), "özel tasarım üretim"),   # 3D baskı/baskılı
    (re.compile(r"3\s*boyutlu\s+bask[ıi]\w*", re.I), "özel tasarım üretim"),
    (re.compile(r"3\s*[dD]\s*print\w*", re.I), "özel tasarım üretim"),
    (re.compile(r"3\s*[dD]\s*yaz[ıi]c[ıi]\w*", re.I), "özel üretim"),             # 3D yazıcı
    (re.compile(r"(desteksiz|destekli)\s+bask[ıi]\w*", re.I), r"\1 üretim"),      # desteksiz/destekli baskı
    (re.compile(r"masa\s*[üu]st[üu]\s+bask[ıi]\w*", re.I), "özel üretim"),        # masaüstü baskı
    (re.compile(r"bask[ıi]\s+(tabla\w*)", re.I), r"üretim \1"),                   # baskı tablası (print-bed)
]
# BUTON/basınç-BASIL koruması: bu bağlamlardaki "basıl" ÇEVRİLMEZ (maskelenir). Cümle içi (nokta
# geçmez); "basılması önerilir" (printing) MASKELENMEZ ('öner' != 'önle'). Sanitize + lint AYNI maskeyi kullanır.
_KART_KORU = [re.compile(p, re.I) for p in (
    r"(?:düğme|buton|korna)\w*[^.]{0,32}?bas[ıi]l\w*",     # düğmeye/butona basılması (button-press)
    r"bas[ıi]l\w*[^.]{0,26}?(?:önle|engelle|karşı)\w*",    # basılmasını önler / basılmaya karşı (button)
)]
# BAĞLAM-DUYARLI bare "baskı" (çürütücü son ayar, 27 Tem): bare "baskı" VARSAYILAN KORUNUR (basınç:
# baskı balata/plakası/uygula/altında/yaparak/hizala), AMA printing SİNYALİ bitişikse ÇEVRİLİR:
# (a) malzeme adı ÖNCE (PLA/PETG/ABS/PA/PC/ASA/TPU/reçine/naylon) · (b) doluluk/infill/ölçek ÖNCE ·
# (c) hassas/test/kolay/hızlı/düz/dikey/yatay ÖNCE · (d) SONRA printing-tavsiyesi (önerilir/yeterli/
# gerektirir/kalitesi/ayarı/çözünürlüğü/hassasiyeti). Ölçüldü: 79 printing-"baskı" yakalanır, 21 basınç
# "baskı" DOKUNULMAZ, örtüşme 0. Basınç kolokasyonu bu sinyallerden hiçbirini taşımaz -> güvenli.
_PRINT_SIG = (r"(?:pla|petg|abs|asa|tpu|pa-?cf|pa-?gf|pa|pc|reçine\w*|naylon|poliamid"
              r"|doluluk\w*|dolulukta|dolulukla|dolu|infill|ölçek\w*"
              r"|hassas|test|kolay|hızlı|düz|dikey|yatay)")
_PRINT_ADV = (r"(?:öneril\w*|yeterli\w*|gerektir\w*|kalites\w*|ayar\w*"
              r"|çözünürl\w*|hassasiyet\w*)")
_KART_PRINT_1 = re.compile(r"(\b" + _PRINT_SIG + r"\s+(?:ile\s+)?)(bask[ıi]\w*)", re.I)
_KART_PRINT_2 = re.compile(r"(bask[ıi]\w*)(\s+" + _PRINT_ADV + r")", re.I)
_BASK_DON = {"baskı": "üretim", "baskıya": "üretime", "baskıda": "üretimde",
             "baskıyla": "üretimle", "baskısı": "üretimi",
             "baskıyı": "üretimi", "baskıdan": "üretimden", "baski": "üretim"}


def _bask_don_w(w):
    r = _BASK_DON.get(w.lower(), "üretim")
    if w[:1].isupper():
        r = r[:1].upper() + r[1:]
    return r
# Tekil printing kelime formları (basınç/buton maskelendi/yok). Türkçe ek uyumlu ENUMERE karşılık;
# yoksa kök-bazlı yedek. NOT: bare "baskı"/"basma" YOK (fail-safe koru).
_KART_KELIME = {
    "baskılı": "özel üretim",
    "basılması": "üretilmesi", "basılıp": "üretilip", "basılır": "üretilir",
    "basıldığında": "üretildiğinde", "basılabilir": "üretilebilir", "basılmasını": "üretilmesini",
    "basılan": "üretilen", "basılmaya": "üretilmeye", "basılarak": "üretilerek",
    "basılmış": "üretilmiş", "basılabilen": "üretilebilen", "basıldıktan": "üretildikten",
    "basılmasına": "üretilmesine", "basılmalı": "üretilmeli", "basılmalıdır": "üretilmelidir",
    "basılırsa": "üretilirse", "basılabilmesi": "üretilebilmesi", "basılabilecek": "üretilebilecek",
    "filament": "malzeme", "filamentle": "malzemeyle", "filamentte": "malzemede",
    "filamentlerle": "malzemelerle", "filamentlerde": "malzemelerde",
    "yazıcı": "özel üretim", "yazıcılarda": "özel üretimlerde", "yazıcıların": "özel üretimlerin",
    "yazıcıya": "özel üretime", "yazıcıda": "özel üretimde", "yazıcının": "özel üretimin",
    "yazdırmaya": "üretime", "yazdırma": "üretim", "yazdırılan": "üretilen",
}
# Kök seti: yalnız ÇEVRİLECEKLER — filament, yazıcı, yazdır, baskılı, basıl (production). Bare
# "baskı" ve "basma" KAPSAM DIŞI (fail-safe koru). 'baskılı' 'basıl'dan ÖNCE (baskılı ≠ basıl).
_KART_ROOT_RE = re.compile(
    r"\b(?:filament|yaz[ıi]c[ıi]|yazd[ıi]r|bask[ıi]l[ıi]|bas[ıi]l)\w*", re.I)


def _kart_root_rep(m):
    w = m.group(0)
    dl = _kart_kelime_yardim(w.lower())
    if w[:1].isupper():                              # kapitalizasyonu koru
        dl = dl[:1].upper() + dl[1:]
    return dl


def _kart_kelime_yardim(w):
    if w in _KART_KELIME:
        return _KART_KELIME[w]
    if w.startswith("filament"):
        return "malzeme"
    if w.startswith("baskıl") or w.startswith("baskil"):   # baskılı (printed)
        return "özel üretim"
    if w.startswith("bas") and ("basıl" in w or "basil" in w):
        return "üretilen"
    if w.startswith("yazıc") or w.startswith("yazic"):
        return "özel üretim"
    if w.startswith("yazdır") or w.startswith("yazdir"):
        return "üretim"
    return w


def _kart_temizle(txt):
    """Kart BAŞLIĞINDAKİ AÇIK printing jargonunu temizle. Bare 'baskı' (basınç dahil) +
    'basma' + buton-'basıl' KORUNUR (fail-safe, over-clean YOK)."""
    if not txt:
        return txt
    # hızlı yol: hiçbir tetikleyici alt-dize yoksa dokunma. Tetikleyiciler ÇEVRİLECEK kökleri kapsar:
    # filament · yazıcı · yazdır · "bask" (3D/desteksiz/masaüstü/tabla baskı + baskılı) · print · basıl.
    if not re.search(r"filament|yaz[ıi]c[ıi]|yazd[ıi]r|bask|print|bas[ıi]l", txt, re.I):
        return txt
    masks = []

    def _mask(m):
        masks.append(m.group(0))
        return "\x00%dM\x00" % (len(masks) - 1)

    for pat in _KART_KORU:                           # 1) buton-basıl maskele (koru)
        txt = pat.sub(_mask, txt)
    for pat, rep in _KART_BILESIK:                   # 2) 3D/desteksiz/masaüstü/tabla bileşik
        txt = pat.sub(rep, txt)
    # 3) BAĞLAM-DUYARLI bare "baskı": printing sinyali bitişikse çevir (basınç KORUNUR)
    txt = _KART_PRINT_1.sub(lambda m: m.group(1) + _bask_don_w(m.group(2)), txt)
    txt = _KART_PRINT_2.sub(lambda m: _bask_don_w(m.group(1)) + m.group(2), txt)
    txt = _KART_ROOT_RE.sub(_kart_root_rep, txt)     # 4) filament/yazıcı/yazdır/baskılı/basıl
    for i, o in enumerate(masks):                    # 5) maskeleri geri koy
        txt = txt.replace("\x00%dM\x00" % i, o)
    return txt


def _placeholder(txt):
    """index.html placeholder() portu — görselsiz/kırık görsel yerine SVG (kataloğla aynı)."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
            '<rect width="400" height="300" fill="#1c3a6b"/>'
            '<text x="50%" y="50%" fill="#9db1d4" font-family="Arial" font-size="26" '
            'font-weight="bold" text-anchor="middle" dominant-baseline="middle">PRUVO · '
            + txt + '</text></svg>')


def _ph_data(kat):
    """index.html phData() portu: SVG placeholder -> data URI."""
    return "data:image/svg+xml;utf8," + quote(_placeholder(kat or "Ürün"), safe="")


def _kart_fiyat(ctx, p):
    """index.html kartCiz fiyat mantığı BİREBİR: fiyat -> taban ('X TL'den başlayan') ->
    'Ölçüye özel fiyat'/'Fiyat için sipariş verin'. (metin, empty_mi) döner."""
    fiyat = (p.get("fiyat") or "").strip()
    parametrik = bool(p.get("parametrik"))
    if fiyat:
        return fiyat, False
    taban = None
    if parametrik:
        sema = ctx["konf_sema"](p.get("id"))
        if sema:
            taban = sema.get("tabanFiyatTL")
    if taban is not None:
        return ctx["taban_fiyat_metni"](taban) + "'den başlayan", False
    return ("Ölçüye özel fiyat" if parametrik else "Fiyat için sipariş verin"), True


def _kart(ctx, p):
    """Sitenin STANDART katalog kartı (index.html kartCiz) — SSR/crawlable birebir eşi:
    <a class="card-main" href="/urun/<id>/"> img(card-img, lazy, gerçek görsel) + card-body
    (card-cat/card-title/card-price) + parametrikse card-badge.
    AÇIKLAMA (card-desc) KALDIRILDI (Okan direktifi, 27 Tem): kart yalnız görsel + başlık +
    kategori + fiyat taşır; baskı/filament/yazıcı jargon-kaçağı açıklamada doğduğu için
    KAYNAĞINDA kesildi (bağlam-duyarlı sınıflandırıcı whack-a-mole yerine yapısal çözüm)."""
    esc = ctx["esc"]
    pid = p.get("id")
    # KART-ÖZEL marka-kuralı temizliği (baskı-jargonu -> okunur karşılık; mekanik anlam korunur).
    # YALNIZ kart BAŞLIĞINDA; feed/urun DEĞİŞMEZ.
    baslik = _kart_temizle((p.get("baslik") or "").strip()) or pid
    kategori = (p.get("kategori") or "").strip()
    imgs = ctx["images_of"](p)
    # Görseli olan (neredeyse tümü) gerçek media URL'ini taşır; görselsiz nadir ürün placeholder
    # data-URI'sini SRC olarak alır. NOT: kataloğun kartCiz'i onerror'ı JS'te bağlar; SSR'de her
    # karta gömülen data-URI onerror sayfayı ŞİŞİRİR (ölçüldü: BMW marka 1.5 MB) -> gömülmez.
    cover = imgs[0] if imgs else _ph_data(kategori)
    fiyat_metni, bos = _kart_fiyat(ctx, p)

    badge = ('<span class="card-badge">Ölçüye Özel</span>'
             if p.get("parametrik") else "")
    # data-kat = KAPSAM ekseni (marka × kategori). Kart zaten kategoriyi GÖSTERİYOR ama
    # makine-okunur alan yoktu; ?kategori= kapsamı bu alandan süzülür. Boş/eksik data-kat
    # kapsam aktifken kartı GİZLETİR (fail-closed) — bu yüzden hep basılır.
    return (
        '<div class="card" data-kat="%s"><a class="card-main" href="%s">'
        '<img class="card-img" alt="%s" loading="lazy" src="%s">'
        '<div class="card-body">'
        '<span class="card-cat">%s</span>'
        '<div class="card-title">%s</div>'
        '<div class="card-price%s">%s</div>'
        '</div>%s</a></div>'
        % (esc(kategori), esc(ctx["product_url"](pid)), esc(baslik), esc(cover),
           esc(kategori), esc(baslik),
           " empty" if bos else "", esc(fiyat_metni), badge))


def _kat_sayim_json(urunler):
    """Model grubunun KATEGORİ kırılımı -> data-katsay JSON'u ({"Marin":3,"Motosiklet":5}).
    sort_keys: çıktı deterministik (aynı katalog -> bayt-aynı sayfa)."""
    c = Counter((p.get("kategori") or "").strip() for p in urunler)
    return json.dumps({k: v for k, v in c.items() if k},
                      ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _urun_grid(ctx, urunler):
    parts = [_kart(ctx, p) for p in urunler if p.get("id")]
    if not parts:
        return ""
    return '<div class="grid">' + "".join(parts) + "</div>"


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
def _model_sayfasi(ctx, marka, g, kategoriler):
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
                      "parçayı bize ulaştırın — getirin ya da kargoyla gönderin; "
                      "milimetrik ölçüp, çalışacağı yere göre doğru malzemeyle ölçüye özel "
                      "üretelim. Ölçü sizden, üretim bizden. Parçanızın fotoğrafını "
                      "WhatsApp'tan " + WA_TEL_GORUNUR + " numarasına önceden iletirseniz "
                      "ön teyit veririz.")

    n = len(g["urunler"])
    description = (marka + " " + display + " için bulunamayan ya da kırılan plastik yedek "
                  "parçaları numunenizden ölçüye özel üretiyoruz. " + str(n) + " parça "
                  "listeleniyor; bulamadığınızı WhatsApp'tan üretelim.")

    prefill = ("Merhaba, " + marka + " " + display + " için bir parça arıyorum, sitede "
               "bulamadım. Elimdeki numuneyi ölçüp ölçüye özel üretebilir misiniz? "
               "Fotoğrafını iletiyorum.")

    # breadcrumb (görünür)
    # data-kapsam-tasi: kapsam varsa marka geri-linki de aynı kapsamda kalsın (JS ekler).
    bc = ('<nav class="mm-bc" aria-label="breadcrumb"><a href="/">Ana Sayfa</a> &rsaquo; '
          '<a data-kapsam-tasi href="' + esc(marka_url) + '">' + esc(marka) + '</a> &rsaquo; '
          + esc(display) + '</nav>')

    huni = _huni_blok(esc, marka + " " + display + " parçanızı bulamadınız mı?",
                      huni_govde, prefill, "WhatsApp'tan Yazın")

    body = (bc
            + '<h1>' + esc(h1) + '</h1>'
            + '<p class="lead">' + esc(giris) + '</p>'
            + _kapsam_not_html(esc)
            + '<h2 class="mm-sec-h">' + esc(display) + ' parçaları ('
            + '<span class="mm-sayim-kart">' + str(n) + '</span>)</h2>'
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
    html = _shell(ctx, h1, url, description, breadcrumb_ld, collection_ld, body,
                  kapsam_scripti(kategoriler))
    return url, html


def _marka_sayfasi(ctx, marka, d, buyuk_gruplar, kucuk_urunler, kategoriler):
    esc = ctx["esc"]
    SITE = ctx["SITE"]
    marka_slug = _slug(marka)
    url = SITE + "/marka/" + marka_slug + "/"

    h1 = marka + " Yedek Parça — Ölçüye Özel Üretim"
    toplam = marka_urun_sayisi(d)
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

    # model butonları (>= ESIK). data-katsay = modelin KATEGORİ kırılımı ({"Marin":3,...});
    # kapsam geldiğinde buton o kategorideki sayıya düşer, 0 ise BUTON GİZLENİR — yoksa
    # Marin kapsamında motosiklet modeli butonu görünmeye devam ederdi (sessiz hata).
    btns = []
    for g in buyuk_gruplar:
        murl = "/marka/" + marka_slug + "/" + g["slug"] + "/"
        btns.append('<a class="mm-model-btn" href="%s" data-katsay="%s">'
                    '%s<span class="adet">%d parça</span></a>'
                    % (esc(murl), esc(_kat_sayim_json(g["urunler"])),
                       esc(g["display"]), len(g["urunler"])))
    model_html = '<div class="mm-models">' + "".join(btns) + "</div>" if btns else ""

    # diğer parçalar: <ESIK modeller + yalnız-marka + İKİNCİL (çok markalı uyumluluk) ürünler.
    # İkincil = marka[0]'ı başka marka olan ama marka[] dizisinde bu markayı da taşıyan ürün;
    # index.html marka filtresi onu zaten bu markada gösteriyor -> sayfa da göstermeli.
    diger = list(kucuk_urunler) + list(d["marka_only"]) + list(d.get("ikincil", []))
    diger_html = ""
    if diger:
        diger_html = ('<h2 class="mm-sec-h">Diğer ' + esc(marka)
                      + ' parçaları (<span class="mm-sayim-kart">'
                      + str(len(diger)) + '</span>)</h2>'
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
            + _kapsam_not_html(esc)
            + ('<h2 class="mm-sec-h">Modele göre seçin (<span class="mm-sayim-model">'
               + str(len(btns)) + '</span>)</h2>' if btns else "")
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
    html = _shell(ctx, h1, url, description, breadcrumb_ld, collection_ld, body,
                  kapsam_scripti(kategoriler))
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
            "product_chip_map":{urun_id: "/marka/<marka>/[<model>/]"}, "sayim":{...},
            "chip_markalar":[...], "sayfasiz_cipler":[...]}.
    product_chip_map: render_product ürün sayfasındaki marka çipini crawlable /marka hedefine
    bağlamak için kullanır (sayfası olmayan marka haritada YOK -> /?marka= fallback)."""
    ROOT = ctx["ROOT"]
    SITE = ctx["SITE"]
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        _index_html = f.read()
    evren = MarkaEvreni(_index_html)
    kategoriler = kategori_evreni(_index_html)     # KAPSAM doğrulama evreni (fail-closed)
    veri = gruplandir(products, evren)

    def yaz(url, html):
        yol = url[len(SITE):].strip("/")          # "marka/ford/focus"
        klasor = os.path.join(ROOT, *yol.split("/"))
        os.makedirs(klasor, exist_ok=True)
        with open(os.path.join(klasor, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    # Marka sayfası eşiği: >= ESIK toplam ürünlü kanonik markalar (ince marka sayfası olmasın).
    # Marka toplamı = o markanın SAYFASINDA görünecek ürün sayısı (ikincil ürünler DAHİL) =
    # index.html çip sayımıyla aynı yüklem. Eşik + çip sıralaması bu sayıdan türer.
    marka_toplam = {marka: marka_urun_sayisi(d) for marka, d in veri.items()}
    sayfali_markalar = sorted([m for m, t in marka_toplam.items() if t >= ESIK],
                              key=lambda m: (-marka_toplam[m], m))

    sitemap = []
    slug_gorulen = {}   # (marka_slug, model_slug) -> canon (model collision nöbeti)
    marka_slug_gorulen = {}   # marka_slug -> marka (marka slug collision nöbeti)
    slug_map = {}       # kanonik marka -> slug (JS çip linki için; yalnız sayfası olan markalar)
    # product_chip_map: urun-id -> ürün sayfasındaki marka çipinin GİDECEĞİ crawlable /marka hedefi
    # (discovery kök-fix: /urun -> /marka geri-linki). Ürün >=ESIK bir modeldeyse model sayfasına,
    # değilse marka sayfasına düşer. SAYFASI OLMAYAN marka HARİÇ (render_product o zaman /?marka=
    # fallback'inde kalır). Sayfa üretimiyle BİREBİR aynı slug/eşik mantığı — reinvent YOK.
    product_chip_map = {}
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

        murl, mhtml = _marka_sayfasi(ctx, marka, d, buyuk, kucuk_urunler, kategoriler)
        yaz(murl, mhtml)
        sitemap.append((murl, "0.7", "weekly"))

        marka_yolu = "/marka/" + marka_slug + "/"          # göreli (aynı köken; render_product /?marka= gibi göreli basar)
        for g in buyuk:
            url, html = _model_sayfasi(ctx, marka, g, kategoriler)
            yaz(url, html)
            sitemap.append((url, "0.7", "weekly"))
            model_yolu = marka_yolu + g["slug"] + "/"
            for p in g["urunler"]:                          # >=ESIK model -> ürünleri model sayfasına
                pid = p.get("id")
                if pid:
                    product_chip_map[pid] = model_yolu
        for p in kucuk_urunler:                             # <ESIK model ürünleri -> marka sayfası
            pid = p.get("id")
            if pid:
                product_chip_map[pid] = marka_yolu
        for p in d["marka_only"]:                           # yalnız-marka ürünler -> marka sayfası
            pid = p.get("id")
            if pid:
                product_chip_map[pid] = marka_yolu
        # d["ikincil"] BİLEREK atlanır: ürün sayfasındaki çip TEK hedefe gider; ikincil
        # markadan yazsaydık hedef marka döngü sırasına göre değişir (kararsız çıktı) ve
        # ürünün BİRİNCİL markasından uzaklaşırdı. İkincil ürün o marka sayfasında LİSTELENİR.

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
        "product_chip_map": product_chip_map,
        "chip_markalar": chip_markalar,
        "sayfasiz_cipler": sayfasiz_cipler,
        "sayim": sayim,
        "marka_sayfasi_sayisi": len(sayfali_markalar),
        "model_sayfasi_sayisi": sum(s["model_sayfasi"] for s in sayim.values()),
    }
