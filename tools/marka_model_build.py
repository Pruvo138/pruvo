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
import sys
import json
import unicodedata
from urllib.parse import quote
from collections import Counter

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_kanon                                                  # noqa: E402

WHATSAPP = "905451386526"
WA_TEL_GORUNUR = "+90 545 138 6526"
ESIK = 3                       # model sayfası + marka sayfası yalnız >= ESIK ürünlü için (spec §3.4)

# Sitemap'e girebilen sayfa sınıflarının TEK kanonik kaynağı. Üretici her kaydı bu
# tablodan geçirir; kabul testi de üretilen manifestin sınıf evrenini bu tablodan okur.
# Böylece yeni bir koleksiyon sınıfı yalnız sitemap'e eklenip sayaçtan kaçamaz.
SITEMAP_SAYFA_SINIFLARI = {
    "marka": ("0.7", "weekly"),
    "model": ("0.7", "weekly"),
    "diger": ("0.6", "weekly"),
    "dizin": ("0.6", "weekly"),
}
# Marka sayfasında SSR'de basılan TAM KART sayısı; kalanı aynı sayfada artımlı çizilir.
# 🔴 N ÖLÇÜMLE SEÇİLDİ (gerekçe: tools/paket-marka-tek-sayfa.md). Kısıt:
# en büyük marka sayfasının HTML baytı index.html'i AŞMAMALI. Yerel kalemleri (model sayfası
# olmayan, bu yüzden HTML'de linklenmek ZORUNDA olan ürünler) kart yerine düz bağ olarak
# basmak asıl kazancı verir; N ilk boyanın kalitesini belirler.
#
# 🔴 N NEDEN 80 (ölçüldü, 8 Ağu):
#   · CRAWL YÜZEYİ N'DEN BAĞIMSIZ. Büyük markalarda yerel kalem sayısı N'i aştığı için
#     kart + düz bağ == yerel kalem sayısıdır: N'i düşürmek bir kalemi KART'tan BAĞ'a
#     taşır, ikisi de <a href="/urun/…"> olduğundan sayfadaki iç link sayısı DEĞİŞMEZ.
#     Yani N yalnız İLK BOYANIN görsel zenginliğini belirler, SEO'yu belirlemez.
#   · TAVAN PAYI. En büyük sayfa: N=120 -> 201.845 B (tavana 11.310 B pay ≈ 100 kalem),
#     N=80 -> 189.795 B (pay 23.360 B ≈ 210 kalem). Katalog HER PARTİDE büyüyor; 80
#     payı İKİYE KATLIYOR ve kazandığı tek şey 40 görsel karttır.
#   · 80 kart mobilde ~3-4 ekran; kaydırma o noktaya gelmeden artım kolu bir parti daha
#     çizdiği için kullanıcı kesintiyi GÖRMEZ.
# Tavan nöbetçisi: tools/marka-sayac-kapisi.py `AGIRLIK/<sayfa>` (HTML_TAVAN).
MARKA_KART_N = 80

# 🔴 KANONİK EŞLEME TABLOLARI BURADA TANIMLANMAZ — index.html'deki TEK KAYNAK bloğundan
# (tools/model_kanon.py) gelir. Kopya tutulsaydı ana sayfa filtresi ile /marka/ sayfası
# yeniden sessizce ayrışırdı ([[ikiz-tanim-sessiz-ayrisma]]; ölçüm için model_kanon docstring'i).
# MARKA_ALIAS: aynı markanın iki adı (Vauxhall = Opel) — modül düzeyinde geriye dönük okuyucular
# (tools/cip-sayfa-bagi.py) için; evren nesnesi kendi index.html'inden AYRICA okur.
MARKA_ALIAS = model_kanon.MARKA_ALIAS

# Türkçe harf -> ascii (slug için; model kanonu model_kanon.kanon'dan gelir)
_TR = {"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
       "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
       "â": "a", "î": "i", "û": "u"}


def _ascii_lower(s):
    s = (s or "").strip().lower()
    return "".join(_TR.get(ch, ch) for ch in s)


def _canon(s):
    """Gruplama anahtarı — index.html modelKanon() ile TEK KAYNAK (model_kanon.kanon).
    'F-150'/'F150'/'F 150' -> 'f150'; 'S-Max'/'S-MAX' -> 'smax'."""
    return model_kanon.kanon(s)


def _slug(s):
    """URL slug'ı: küçük harf, alfanümerik dışı -> tek '-'. 'F-150'->'f-150',
    'Focus ST'->'focus-st', 'i3'->'i3', '1 Serisi'->'1-serisi'.
    '+' anlamlıdır (Peugeot 206+ != 206) -> 'plus'; yoksa iki farklı model AYNI URL'e düşer."""
    s = _ascii_lower(s).replace("+", " plus ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _strip_marka_oneki(marka, model_ham, evren):
    """Model değerinin BAŞINDAKI gereksiz marka token'ını sıyır (kanonik marka'ya katlanan):
    'Peugeot 206'->'206', 'Renault 5 E-Tech'->'5 E-Tech', 'Alfa Romeo Giulia'->'Giulia',
    'Vauxhall Astra' (Opel)->'Astra'. TAM-TOKEN eşleşme (en uzun marka öneki önce) + folded marka
    ile aynı olma şartı — substring/yanlış-marka sıyrılmaz. Model TÜMÜYLE markaysa '' döner
    (çağıran marka-only sayar). Böylece 'peugeot206'->'206' mükerreri BİRLEŞİR (spec §9.1),
    'Peugeot Peugeot 206' gibi çift-marka H1 doğmaz. urunler.json DEĞİŞMEZ (yalnız build-anı).

    🔴 GÖVDE BURADA DEĞİL: index.html modelOnekSiyir() ile TEK KAYNAK (model_kanon.onek_siyir)."""
    return model_kanon.onek_siyir(marka, model_ham, evren)


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
    """index.html markaNorm() portu: norm + AKSAN ÇÖZÜMÜ + ayıraç ('and'/&/+) sadeleştirme.

    🔴 AKSAN GENEL KURALLA (6 Ağu, H4): elle liste (`é/è/ë/ä`) `Škoda` gibi caron/tilde
    taşıyan yazımları görmüyordu ve `modelKanon`un aksan kuralıyla AYRIŞIYORDU. Aynı
    NFD + birleşen-işaret kuralı iki eksende de koşar; ayrışma K10/K13'te node ile ölçülür."""
    n = unicodedata.normalize("NFD", _norm(s))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    return re.sub(r"\s+", " ", n).strip()


# Artım kolunun kart verisini çektiği EDGE yolu — ana sayfanın kullandığı MEVCUT yol.
# 🔴 TEK KAYNAK index.html'in `EDGE_UC`'si; burada KOPYA TUTULMAZ (ayrışırsa marka sayfası
# ölü bir uca istek atar ve tek kart çizmez — hatası SESSİZ). Kapı bu değeri BAĞIMSIZ
# ayıklayıp sayfanın BEYAN ettiğiyle karşılaştırır → [[ikiz-tanim-sessiz-ayrisma]].
EDGE_KATALOG_YOLU = "/katalog?ids="
EDGE_PARTI = 100          # /katalog?ids= tek istekte en çok 100 id (ana sayfa da 100 kullanıyor)


def edge_ucu(index_html):
    """index.html'deki `EDGE_UC` — kart verisinin çekileceği edge kökü (TEK KAYNAK).

    🔴 NEDEN AYIKLANIR, GÖMÜLMEZ: marka sayfası ilk açılışta hiçbir veri çekmez, kalan
    kartları KULLANICI istediğinde (kaydırma / "tümünü göster" / model filtresi) çizer ve
    o veriyi ana sayfanın kullandığı AYNI uçtan, YALNIZ gereken id'ler için alır
    (`/katalog?ids=`). Tüm katalogu (`urunler.json`, ölçüldü: 21.330.991 B ham /
    3.133.127 B gzip) indirmek KABUL EDİLEMEZ — ana sayfa o deseni `EDGE_KATALOG=true`
    ile bilerek terk etti (gerekçe index.html'de: mobil ilk açılış + bellek).
    Bulunamazsa HATA (fail-closed): sessizce boş uca düşerse hiç kart çizilmez."""
    m = re.search(r'var\s+EDGE_UC\s*=\s*"([^"]+)"', index_html)
    if not m:
        raise SystemExit("HATA: index.html'de EDGE_UC bulunamadı "
                         "(marka sayfası artım kolunun veri ucu tek kaynağı bozuk).")
    return m.group(1).rstrip("/")


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
        # Alias tabloları AYNI index.html'den (evrenin okuduğu belgeden) gelir — modül
        # düzeyi sabit KULLANILMAZ: geçici ROOT ile koşan testte iki farklı belge okunurdu.
        self.marka_alias, self.model_alias = model_kanon.tablolar(index_html)
        # ÇOK KELİMELİ kanonik marka adları (bölünmez). Otorite tools/arama.py KAPALI MARKA
        # KÜMESİ; buradaki ayna ile ayrışması model-uyelik-kapisi.py'de KIRMIZI yanar.
        self.bilesik = model_kanon.bilesik_markalar(index_html)
        self.bilesik_normlu = frozenset(model_kanon._marka_norm(x) for x in self.bilesik)
        # KUŞAK KATLAMASI tabloları — AYNI belgeden (modül düzeyi sabit KULLANILMAZ).
        (self.kusak_donanim, self.kusak_disi,
         self.kusak_esleme) = model_kanon.kusak_tablolari(index_html)
        self._kusak_bellek = {}

    def taninmis_mi(self, m):
        return _marka_norm(m) in self._kanonik

    def katla(self, m):
        """index.html markaKatla() portu (marka-düzeyi alias DAHİL: Vauxhall->Opel)."""
        n = _marka_norm(m)
        base = self._kanonik.get(n)
        if base is None:
            base = m
            for i, mn in enumerate(self._normlu):
                if n.startswith(mn + " ") or n.startswith(mn + "-"):
                    base = self.taninmis[i]
                    break
        return self.marka_alias.get(base, base)

    def model_anahtari(self, marka, deger):
        """index.html modelAnahtar() portu — model ÜYELİK anahtarı (tek kaynak)."""
        return model_kanon.anahtar(marka, deger, self, self.model_alias)

    def kusak_tabanlari(self, marka, deger):
        """index.html kusakTabanlari() portu — jetonun KUŞAK okumaları (tek kaynak).
        [(taban anahtarı, kuşak etiketi)], uzun tabandan kısaya; boş = varyant değil.
        Bellek JS tarafındaki `_kusakBellek` ile aynı desen (saf fonksiyon; tablolar donmuş)."""
        anahtar = (marka, deger)
        sonuc = self._kusak_bellek.get(anahtar)
        if sonuc is None:
            sonuc = model_kanon.kusak_tabanlari(marka, deger, self, self.model_alias,
                                                self.kusak_donanim, self.kusak_disi,
                                                self.kusak_esleme)
            self._kusak_bellek[anahtar] = sonuc
        return sonuc


# Semantik model alias'ı (kanon'un yakalayamadığı TR/EN birleşmesi) index.html'de yaşar;
# burada YALNIZ geriye dönük okuyucular için modül düzeyi kopyası dururdu -> TUTULMAZ.
# Kullanım: evren.model_alias / evren.model_anahtari().
_ALIAS = model_kanon.MODEL_ALIAS

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
    # 🔴 ÇIPLAK TEK HARF JETON (4 Ağu, kararsız jeton SINIF 1): `K` ile `K Serisi` yazımları
    # MODEL_ALIAS ile TEK kovada birleşti; sıklık EŞİT olduğu için (1-1) deterministik
    # tie-break ALFABETİK davranır ve kova adı "K" olurdu — mimar hükmü tam yazımdır
    # ("TEK HARF ÇIPLAK KULLANILMAZ"). Zorlama olmadan sayfa/çip etiketi tek harfe düşer.
    ("BMW", "kserisi"): "K Serisi",
    # 🔴 ÇIPLAK TEK HARF JETON — `BMW|kserisi` ile BİREBİR AYNI SINIF (6 Ağu, hüküm C):
    # `V` + `V-Class` + `V-Klasse` MODEL_ALIAS ile tek kovada birleşti; üç yazımın sıklığı
    # da 1 olduğu için deterministik tie-break ALFABETİK davranır ve kova adı TEK HARFE
    # ("V") düşerdi -> sayfa `/marka/mercedes/v/` olurdu. Gösterim YENİ BİR KURALLA
    # SEÇİLMEDİ: deponun mevcut çivileme deseni kullanıldı ve katalogda ZATEN VAR OLAN
    # yazımlardan biri (`V-Class`) çivilendi — hedef kanon da odur (`vclass`).
    # `A` ailesinde çivi GEREKMEDİ: `A-Class` yazımı sıklıkla kendiliğinden kazanıyor.
    ("Mercedes", "vclass"): "V-Class",
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
def _cip_indeks_yukle():
    """tools/cip-indeks.py — modul adinda tire var, importlib ile yuklenir (emsal: build.py).
    FAIL-CLOSED: yuklenemezse marka sayfasi evreni cip evreninden AYRISIRDI."""
    import importlib.util
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cip-indeks.py")
    spec = importlib.util.spec_from_file_location("cip_indeks_mm", yol)
    if spec is None:
        raise SystemExit("HATA: tools/cip-indeks.py bulunamadi — marka sayfasi evreni cip "
                         "evreninden turetilemez (fail-closed: cipte gorunup sayfasi 404 "
                         "donen marka dogardi).")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cip_evreni_markalari(products, index_html):
    """🔴 TEK KAYNAK: /marka/<slug>/ evreni ANASAYFA CIP EVRENINDEN turer.

    OLCULEN SESSIZ HATA (3 Agu): cip evreni artik kategorinin `uyum` kapsamina gore
    kuratorluk gevsetiyor (cip-indeks.ESIK_UYUM_KAPSAM) ama marka sayfasi ureteci hala
    YALNIZ index.html TANINMIS_MARKALAR'i okuyordu -> IKIZ TANIM. Sonuc: Marin'de
    Teleflex(149) · Sierra(141) · NGK(117) · Tecnoseal(106) · Jabsco(44) ·
    International(43) · 3M(22) cip olarak DOGDU ama /marka/<slug>/ sayfalari 404 doner
    hale geldi ([[ikiz-tanim-sessiz-ayrisma]]).
    ONARIM: ikinci bir kural YAZILMAZ — evren dogrudan URETILEN INDEKSTEN okunur. Cip
    evreni nasil degisirse degissin sayfa evreni onu takip eder; ayrisma imkansiz olur."""
    ci = _cip_indeks_yukle()
    ix = ci.indeks_uret(products, index_html)
    return set(b for kd in ix["kat"].values() for b in kd)


def marka_uyelikleri(marka_dizisi, evren, ek_markalar=()):
    """Ürünün marka[] dizisinden ÜYE OLDUĞU kanonik marka sayfalarını çıkarır — index.html
    marka FİLTRESİYLE birebir aynı yüklem: `(p.marka||[]).some(b => markaKatla(b) === hedef)`.
    Yani HER eleman (yalnız marka[0] değil) katlanır, tanınmışsa üyelik doğar; sıra korunur,
    tekrar tekilleşir. İkinci bir katlama tablosu YOK — kaynak evren.katla (index.html portu).

    ÖLÇÜLEN SESSİZ HATA (31 Tem): eski kod üyeliği HAM marka[0] ile ölçüyordu
    (taninmis_mi(ham0)); "Volvo Penta" (21 Marin) ve "Mercedes-Benz" (20) ham hâlde tanınmış
    listede olmadığı için 41 ürün HİÇBİR marka sayfasına girmiyordu — katalogda var, marka
    sayfasında yok, kimse görmüyordu.

    `ek_markalar`: çip evreninden gelen ve TANINMIS listede OLMAYAN kanonik markalar
    (cip_evreni_markalari). Üyelik yüklemi AYNI kalır, yalnız kabul kümesi genişler."""
    uyeler = []
    for x in marka_dizisi:
        kan = evren.katla((x or "").strip())
        if kan and (evren.taninmis_mi(kan) or kan in ek_markalar) and kan not in uyeler:
            uyeler.append(kan)
    return uyeler


def ek_marka_normlu(ek_markalar):
    """Çip evreninden gelen markaların {normalleşmiş ad: kanonik ad} indeksi.
    Aramada ürün başına yeniden kurulmasın diye BİR KEZ hazırlanır (18.312 ürün × ~10 jeton
    × 3 pencere; lineer tarama ölçüldüğünde ~26M karşılaştırma ederdi)."""
    return {_marka_norm(x): x for x in (ek_markalar or ())}


def marka_adi_kanonu(deger, evren, ek_normlu=None):
    """Değer TAM OLARAK bir markanın adı mı? -> kanonik ad | None.

    🔴 `marka_uyelikleri`/`evren.katla` İLE FARKI BİLEREKTİR: katlama ÖNEK kuralı işletir
    ("Volvo Penta" -> Volvo), çünkü orada girdi ürünün `marka[]` ALANIDIR ve tek bir markayı
    adlandırır. Burada girdi SERBEST METİNDİR (sorgu ya da başlık penceresi); önek kuralı
    çalışsaydı "Yamaha Mercury" bigramı tek başına "Yamaha"ya katlanır ve "Mercury" jetonu
    YUTULURDU. Bu yüzden yalnız TAM AD eşleşmesi kabul edilir.

    Kanonik yazım + marka-düzeyi alias (Vauxhall -> Opel) İKİNCİ KEZ YAZILMAZ: eşleşme
    doğrulandıktan sonra değer `evren.katla`dan geçirilir (tek gövde).
    """
    ad = " ".join((deger or "").split())
    if not ad:
        return None
    if evren.taninmis_mi(ad):
        return evren.katla(ad)
    kan = (ek_normlu or {}).get(_marka_norm(ad))
    return evren.katla(kan) if kan else None


def birincil_marka(marka_dizisi, evren, ek_markalar=()):
    """Ürünün BİRİNCİL kanonik markası — TEK KAYNAK (gruplandir + ürün çip haritası aynı
    yüklemi kullanır; iki yerde yazılsaydı çipin gittiği sayfa ile ürünün sayıldığı sayfa
    ayrışırdı). marka[0]'ın katlanmışı görünür evrendeyse O; değilse SIRA korunarak ilk üye."""
    uyeler = marka_uyelikleri(marka_dizisi, evren, ek_markalar)
    if not uyeler:
        return None
    ham0 = evren.katla((marka_dizisi[0] or "").strip())
    return ham0 if (evren.taninmis_mi(ham0) or ham0 in ek_markalar) else uyeler[0]


def _kapali_marka_kumesi():
    """tools/arama.py KAPALI MARKA KÜMESİ (UYUM_MARKA_IZINLI ∪ URETICI_MARKA), normalleşmiş.

    🔴 TEK KAYNAK, İKİNCİ LİSTE YOK: "hangi jeton MARKA'dır" yargısı bu depoda zaten
    verilmiş ve mimar eliyle yargılanmış bir kümedir (`UYUM_MARKA_MIMAR_EKI` dahil).
    Model üreteci onu OKUR — kendi marka/model yargısını UYDURMAZ.
    FAIL-CLOSED: küme okunamazsa SystemExit (boş kümeye düşmek 'Volvo Penta'/'Yanmar' gibi
    üretici markalarını yeniden MODEL sayfası yapardı)."""
    try:
        import arama                                                # noqa: PLC0415
        kume = (set(arama.UYUM_MARKA_IZINLI) | set(arama.URETICI_MARKA)
                | set(arama.MODEL_OLMAYAN_JETON))
    except Exception as e:                                          # noqa: BLE001
        raise SystemExit("HATA: tools/arama.py KAPALI MARKA KÜMESİ okunamadı (%r) — model "
                         "üreteci marka/model ayrımını yapamaz (fail-closed)." % (e,))
    if len(kume) < 50:
        raise SystemExit("HATA: KAPALI MARKA KÜMESİ şüpheli küçük (%d) — model üreteci "
                         "marka jetonlarını eleyemez (fail-closed)." % len(kume))
    return frozenset(model_kanon._marka_norm(m) for m in kume)


KAPALI_MARKA_NORMLU = _kapali_marka_kumesi()


def _rozet_disi_ciftler():
    """tools/arama.py ROZET_DISI_CIFT — /marka/X/M/ sayfası AÇILMAYAN (marka, model) çiftleri.

    Anahtar KANONİK model anahtarına indirilir: tabloya "Golf" yazmak yeter, katalogdaki
    "GOLF"/"Golf IV" gibi yazımlar aynı kovaya düştüğü sürece kural tutar.
    FAIL-CLOSED: tablo okunamazsa SystemExit (sessizce boş kümeye düşmek, mimarın kapattığı
    sayfaları geri açardı)."""
    try:
        import arama                                                # noqa: PLC0415
        return set((mk, model_kanon.kanon(md)) for mk, md in arama.ROZET_DISI_CIFT)
    except Exception as e:                                          # noqa: BLE001
        raise SystemExit("HATA: tools/arama.py ROZET_DISI_CIFT okunamadı (%r) — rozet dışı "
                         "sayfalar kapatılamaz (fail-closed)." % (e,))


ROZET_DISI = _rozet_disi_ciftler()


def _model_olmayan_ciftler():
    """tools/arama.py MODEL_OLMAYAN_CIFT — (marka, KANONİK jeton) çiftleri.

    Marka-KÖR `MODEL_OLMAYAN_JETON`'dan AYRI tutulur: oraya `ST`/`GS` yazmak bütün
    markalarda aynı jetonu öldürürdü (`/marka/bmw/gs/` ile `/marka/citroen/gs/` ayrı sınıf).
    FAIL-CLOSED: tablo okunamazsa SystemExit (sessizce boş kümeye düşmek, mimarın kapattığı
    donanım/motor sayfalarını geri açardı)."""
    try:
        import arama                                                # noqa: PLC0415
        return set((mk, model_kanon.kanon(jt)) for mk, jt in arama.MODEL_OLMAYAN_CIFT)
    except Exception as e:                                          # noqa: BLE001
        raise SystemExit("HATA: tools/arama.py MODEL_OLMAYAN_CIFT okunamadı (%r) — donanım/"
                         "motor jetonları yeniden MODEL sayfası olurdu (fail-closed)." % (e,))


MODEL_OLMAYAN_CIFTLER = _model_olmayan_ciftler()


def degistirici_jetonu_mu(kelime):
    """Kelime bir KUŞAK/DONANIM DEĞİŞTİRİCİSİ mi — TEK KAYNAK index.html `kusakSonekMi()`.

    'ST'/'GTI'/'4'/'Mk4'/'IV'/'H' evet · 'E-Tech'/'Life'/'EcoBoost'/'iPhone'/'Transporter'
    hayır. İkinci bir "değiştirici listesi" YAZILMAZ: gramer index.html'deki kanonik
    bloktan (model_kanon.kusak_sonek_mi + KUSAK_DONANIM) AYIKLANIR."""
    return model_kanon.kusak_sonek_mi((kelime or "").lower(), model_kanon.KUSAK_DONANIM)


def donanim_kuyruklu_mu(deger):
    """Değer `<taban> <DONANIM>` biçiminde mi ("Focus ST", "206 GTI", "Megane RS")?

    🔴 H3 AYRIMI (6 Ağu, mimar hükmü): taban modele YAPIŞIK geçen donanım/rozet soneki
    ayrı bir aracı ADLANDIRMAZ — aynı araç, aynı parça; kuşak katlamasıyla ana modelin
    varyant bölümünde görünür ve KENDİ SAYFASINI AÇMAZ. AYRI bir aracı adlandıran değer
    (`Zafira Life`, `Transporter T4`, `Corsa D`) bu yüklemin DIŞINDADIR ve sayfa alır.
    Ölçüt KAPALI DONANIM GRAMERİDİR (`KUSAK_DONANIM`), kuşak/sayı/harf grameri DEĞİL:
    `Golf 4` · `Astra H` · `Megane 2` bugün YAYINDA olan meşru KUŞAK sayfalarıdır
    (`DEGISTIRICI_SAYFA_IZNI` emsali) — onları kapatmak SEO yüzeyini geri sarardı."""
    toks = (deger or "").strip().split()
    if len(toks) < 2:
        return False
    return (toks[-1] or "").lower() in set(x.lower() for x in model_kanon.KUSAK_DONANIM)


def model_olmayan_cift_mi(marka, deger):
    """(marka, jeton) çifti MODEL DEĞİL mi — ÇIPLAK yazım + DEĞİŞTİRİCİ kuyruğu.

    🔴 BİLEŞİK YAZIM ŞART (ölçülen boşluk): `marka_jetonu_mu("Focus ST")` False dönüyordu,
    çünkü o yüklem yalnız değerin TAMAMINA bakıyor. Donanım/kuşak jetonu katalogda çoğu
    zaman `<model> <jeton>` biçiminde geçer (`Focus ST`, `Focus Mk1`) — bu yüzden SON
    KELİME de sınanır. `EcoBoost` gibi çıplak yazım ilk sınamada yakalanır.

    🔴 SON-KELİME KOLU YALNIZ DEĞİŞTİRİCİLERE İŞLER (6 Ağu, mimar hükmü H2 — ölçülmüş
    yan hasar): kol kayıtsız şartsız koşarken `("Renault","E-Tech")` deny'i yazılamıyordu,
    çünkü aynı kol MEŞRU `/marka/renault/5-e-tech/` (4 ürün) ve `/marka/renault/megane-e-tech/`
    sayfalarını da kapatıyordu — "kaybolan sayfa 0" şartı bozuluyordu. Ayrım KURALDIR,
    istisna listesi DEĞİL: `<taban> <jeton>` bileşiği ancak jeton bir KUŞAK/DONANIM
    DEĞİŞTİRİCİSİYSE tabana yapışıktır (`ST`, `Mk1`, `Mk2`, `Mk4`); `E-Tech` gibi bir
    ROZET/güç aktarma adı bileşikte AYRI BİR ARACI adlandırır ve o sayfa kapanmaz.
    ÖLÇÜLDÜ (katalog 19.999): bugün son-kelime koluyla ölen 13 kovanın 13'ü de değiştirici
    kuyrukludur — daraltma bugünkü davranışı DEĞİŞTİRMEZ (diriltilen sayfa 0)."""
    t = (deger or "").strip()
    if not marka or not t:
        return False
    if (marka, model_kanon.kanon(t)) in MODEL_OLMAYAN_CIFTLER:
        return True
    toks = t.split()
    if len(toks) < 2 or not degistirici_jetonu_mu(toks[-1]):
        return False
    return (marka, model_kanon.kanon(toks[-1])) in MODEL_OLMAYAN_CIFTLER


def marka_jetonu_mu(deger, evren):
    """Değer BAŞLI BAŞINA bir MARKA mı (dolayısıyla MODEL olamaz)?

    Üç kaynak, üçü de MEVCUT küratörlükler (yeni yargı burada UYDURULMAZ):
      (1) index.html TANINMIS_MARKALAR (`marka_mi`),
      (2) tools/arama.py KAPALI MARKA KÜMESİ (UYUM_MARKA_IZINLI ∪ URETICI_MARKA),
      (3) tools/arama.py MODEL_OLMAYAN_JETON (grup kısaltması / parça üreticisi / kardeş marque).
    (2) olmadan ölçülen 12 anlamsız sayfa doğuyordu: /marka/jabsco/volvo-penta/,
    /marka/toyota/scion/, /marka/yamaha/mariner/, /marka/volvo/penta/ ...; (3) olmadan
    10 tane daha: /marka/peugeot/psa/, /marka/audi/vag/, /marka/land-rover/carling/,
    /marka/toyota/aem/, /marka/yamaha/roland/, /marka/suzuki/geo/ ... — hepsi bir MARKA'yı
    ya da grup kısaltmasını MODEL diye sunuyordu."""
    t = (deger or "").strip()
    if not t:
        return False
    return marka_mi(t, evren) or model_kanon._marka_norm(t) in KAPALI_MARKA_NORMLU


def marka_mi(deger, evren):
    """marka[1] MODEL mi yoksa (çok markalı uyumluluktan gelen) BAŞKA BİR MARKA mı?
    KATI ölçüt: değerin KENDİSİ tanınmış marka listesinde olmalı ("Citroen", "Vauxhall",
    "Lexus"). "Peugeot 206"/"Volvo 240" gibi marka ÖNEKLİ değerler MODEL kalır — katlanmış
    hâline bakmak model kırılımını (SEO'nun ana ekseni) yok ederdi."""
    return bool((deger or "").strip()) and evren.taninmis_mi(deger.strip())


def marka_sahiplik_tablosu(products, evren, ek_markalar=()):
    """Üç tablo (TEK GEÇİŞ, TEK GÖVDE):
      kova        : (marka, model_canon) -> o jetonu taşıyan ürünlerin HAM `marka[0]` dağılımı
      ham0_sayaci : katalog genelinde her ham `marka[0]` değerinin ürün sayısı
      jeton       : jeton canon -> o jetonu taşıyan TÜM ürünlerin ham `marka[0]` dağılımı
                    (marka üyeliğinden BAĞIMSIZ — `jeton_sahibi` bunun üstünde çalışır)

    🔴 KOVA ÜYELİĞİNDEN BAĞIMSIZ (bilerek): tabloyu hem sayfa üreteci (`gruplandir`) hem
    anasayfa çip indeksi (`tools/cip-indeks.py`) türetir. Kova üyeliğine dayansaydı iki
    yüzey iki farklı yargı verir, biri çipi basar diğeri sayfayı kapatırdı — bu depoda
    ölçülmüş sessiz sınıf ([[ikiz-tanim-sessiz-ayrisma]])."""
    kova, ham0_sayaci, jeton = {}, {}, {}
    for p in products:
        m = p.get("marka") or []
        if not m:
            continue
        h = _canon(m[0])
        ham0_sayaci[h] = ham0_sayaci.get(h, 0) + 1
        jetonlar = uyelik_jetonlari(p)
        for t in jetonlar:
            jc = _canon(t)
            if not jc:
                continue
            jd = jeton.setdefault(jc, {})
            jd[h] = jd.get(h, 0) + 1
        uyeler = marka_uyelikleri(m, evren, ek_markalar)
        if not uyeler:
            continue
        for marka in uyeler:
            for t in jetonlar:
                c = evren.model_anahtari(marka, t)
                if not c:
                    continue
                d = kova.setdefault((marka, c), {})
                d[h] = d.get(h, 0) + 1
    return kova, ham0_sayaci, jeton


def ciplak_sayi_mi(display):
    """Jeton tümüyle SAYISAL mı (`916`, `86`, `660`)? H1 bu sınıfı BİLEREK dışarıda tutar
    (harf şartı); (d) kolu da tutar — yoksa çıplak sayı KURAL koluyla doğmuş olurdu.
    ÖLÇÜLDÜ 12 Ağu: (d) ilk yazımında `Alfa Romeo|916` doğuyordu ve kardeş kapı
    (`model-uyelik-kapisi.py::K21 ÇIPLAK SAYI`) KIRMIZI yandı."""
    j = "".join(_kelimeler(display or ""))
    return bool(j) and j.isdigit()


def jeton_sahibi(display, tablo):
    """Jetonun KATALOGDAKİ SAHİBİ markası — ya da SAHİPSİZ (None).

    Sahip = jetonu taşıyan ürünlerin ham `marka[0]` dağılımında payı **>= 1/2** olan marka.
    Çoğunluk yoksa jeton SAHİPSİZDİR ve hiçbir markanın modeli sayılmaz (fail-closed).

    🔴 12 Ağu 2026, KraL hükmü (kapsama lehine gevşetme, ŞARTLI): `BASLIK_DOGAN_ALLOW` elle
    tutulan bir envanterdi ve her katalog partisinde bayatlıyordu — ölçüldü: eşiği ve
    birincilliği FAZLASIYLA geçen 80 kova / 588 ürün yalnızca "envanterde yok" diye çipsiz
    ve sayfasız kalıyordu (`Hyundai|Accent` 39 ürün, `Hyundai|Elantra` 49...). Bu, bu
    depoda adı konmuş bir sınıftır ([[envanter-drift-parti-basina]]).

    KANIT ZAYIFSA ÇİP DOĞMAZ: kural yalnız katalogda SAHİBİ BELLİ jetonları doğurur.
    Ölçülen ayırt edicilik (jeton -> sahip): `golf -> volkswagen` (Audi|Golf KAPALI kalır),
    `trafic -> renault`, `primastar -> opel`, `fiorino -> fiat`, `ranger -> ford`,
    `stellantis -> psa`, `iphone -> SAHİPSİZ` (Toyota|iPhone KAPALI kalır)."""
    _kova, _ham0, jeton = tablo
    if ciplak_sayi_mi(display):
        return None                       # çıplak sayı KURAL koluyla doğmaz (H1 sınırı)
    say = jeton.get(_canon(display or ""))
    if not say:
        return None
    toplam = sum(say.values())
    tepe, n = sorted(say.items(), key=lambda t: (-t[1], t[0]))[0]
    return tepe if n * 2 >= toplam else None


def yabanci_marka_mi(marka, display, canon, tablo):
    """GÜRÜLTÜ SINIFI — çip etiketi bu markanın MODELİ değil, AYRI BİR MARKA mı?

    🔴 12 Ağu 2026, Okan (canlı): `/marka/hyundai/` çipleri arasında `Genesis` duruyordu;
    Genesis bir MODEL değil AYRI BİR MARKADIR ve o kovadaki 8 ürünün 7'sinin ham `marka[0]`
    alanı zaten `Genesis`. Aynı sınıf `/marka/suzuki/` içinde `Sierra` ile tekrar ediyor
    (16 ürünün 12'si deniz donanımı markası `Sierra`'nın).

    🔴 KURAL, KARA LİSTE DEĞİL (spec): hiçbir marka adı koda yazılmaz. İKİ ŞART BİRDEN,
    ikisi de KATALOGDAN ölçülür:
      (1) etiket katalogda ham `marka[0]` olarak >= ESIK üründe geçiyor -> BİR MARKADIR,
      (2) o jetonu taşıyan ürünlerin ÇOĞUNLUĞUNUN ham `marka[0]`'ı ETİKET, ve sayfanın
          markası ÇOĞUNLUK DEĞİL.
    (2) olmasaydı `Ford|Sierra` (Ford Sierra GERÇEK bir Ford modelidir; 5 ürünün 5'i Ford
    birincilli) de düşerdi — ölçüldü, tek şartlı sürüm 4 çip kesiyordu, ikisi YANLIŞ.
    Ürün KAYBOLMAZ: kovanın ürünleri marka sayfasının kart yüzeyinde durmaya devam eder."""
    kova, ham0_sayaci, _jeton = tablo
    etiket = _canon(display or canon)
    if not etiket or etiket == _canon(marka):
        return False
    if ham0_sayaci.get(etiket, 0) < ESIK:
        return False
    say = kova.get((marka, canon))
    if not say:
        return False
    n = sum(say.values())
    return say.get(etiket, 0) * 2 > n and say.get(_canon(marka), 0) * 2 <= n


def marka_urun_sayisi(d):
    """Bir marka kovasının SAYFASINDA görünecek TEKİL ürün sayısı — TEK KAYNAK.
    Eşik (ESIK), çip sıralaması, sayfa metni ve kabul testleri AYNI bu fonksiyonu çağırır;
    ikinci bir toplama formülü YAZILMAZ (formül kopyası kaçınılmaz olarak ayrışır: 31 Tem'de
    ölçüldü — ikincil ürünler eklenince jeneratör ile testin sayısı ayrıştı).

    🔴 TEKİL sayılır (3 Ağu): model üyeliği artık pozisyona bağlı değil, bir ürün AYNI
    markanın birden çok modelinde olabilir (['Opel','Astra','Zafira'] hem Astra'ya hem
    Zafira'ya girer). Grupları toplayan eski formül o ürünü iki kez sayar, marka toplamını
    ve çip sıralamasını sessizce şişirirdi."""
    gorulen = set()
    n = 0
    for kaynak in ([g["urunler"] for g in d["gruplar"].values()]
                   + [d["marka_only"], d.get("ikincil", [])]):
        for p in kaynak:
            pid = p.get("id") or id(p)
            if pid in gorulen:
                continue
            gorulen.add(pid)
            n += 1
    return n


def _baslik_dogan_allow():
    """tools/arama.py BASLIK_DOGAN_ALLOW — SAYFASI YALNIZ BAŞLIK KOLU sayesinde doğan
    (marka, canon) kovalarının YARGILANMIŞ envanteri.

    🔴 YARGISIZ SAYFA DOĞMAZ (5 Ağu, mimar hükmü — K19 doktrininin başlık ekseni):
    başlık kolu olmadan eşiği/birincilliği SAĞLAMAYAN bir kova ancak bu envanterde
    açıkça yargılanmışsa yayımlanır. Envanterde olmayan kova SESSİZCE doğmaz; ürünü
    KAYBOLMAZ (marka sayfasında ve kendi gerçek model sayfasında durur).
    FAIL-CLOSED: tablo okunamazsa SystemExit — boş kümeye düşmek "hiçbir kova doğmaz"
    demek olurdu ve sessizce SEO yüzeyi kırpardı; sessiz genişleme kadar sessiz daralma
    da kabul edilmez."""
    try:
        import arama                                                # noqa: PLC0415
        return set((mk, model_kanon.kanon(jt)) for mk, jt in arama.BASLIK_DOGAN_ALLOW)
    except Exception as e:                                          # noqa: BLE001
        raise SystemExit("HATA: tools/arama.py BASLIK_DOGAN_ALLOW okunamadı (%r) — başlık "
                         "kolundan doğan sayfalar yargılanamaz (fail-closed)." % (e,))


BASLIK_DOGAN_ALLOW = _baslik_dogan_allow()


def _sekil_kurali_muaf():
    """tools/arama.py SEKIL_KURALI_MUAF — H1/H3 KURALININ yargı VERMEDİĞİ çiftler.

    🔴 6 Ağu, mimar hükmü (E): şekil kuralı jetonun ŞEKLİNE bakar, "bu bir ARAÇ mı"
    sorusunu bilemez. Araç DIŞI olduğu yargılanmış çiftte kural susar; sayfa yalnız
    `BASLIK_DOGAN_ALLOW`'daki TEKİL girişle doğar. İki eksen AYRI: muafiyet sayfa
    KAPATMAZ (envanterde varsa doğar), envanter kuralı GEVŞETMEZ.
    FAIL-CLOSED: tablo okunamazsa SystemExit — sessizce boş kümeye düşmek kuralı
    araç dışı jetonlara yeniden açardı."""
    try:
        import arama                                                # noqa: PLC0415
        return set((mk, model_kanon.kanon(jt)) for mk, jt in arama.SEKIL_KURALI_MUAF)
    except Exception as e:                                          # noqa: BLE001
        raise SystemExit("HATA: tools/arama.py SEKIL_KURALI_MUAF okunamadı (%r) — H1/H3 "
                         "şekil kuralı araç dışı jetonlara yeniden yargı verirdi "
                         "(fail-closed)." % (e,))


SEKIL_MUAF = _sekil_kurali_muaf()


# ---------------------------------------------------------- BAŞLIK KOLU (5 Ağu, mimar hükmü)
# ÜYELİK YÜKLEMİ = marka üyeliği ∧ model; model disjunkt'ı =
#     ham `uyum[].model`  ∪  `model_kanon` (kuşak/kanon katlaması)  ∪  BAŞLIKTA TAM KELİME
# ÖLÇÜLEN BOŞLUK (5 Ağu): `?ara=Vitara` 68 ürün getirirken /marka/suzuki/vitara/ 27
# gösteriyordu — arama SERBEST METİN evreninden, sayfa RESMİ `marka[]` üyeliğinden sayıyordu.
# Başlıkta tam-kelime Vitara taşıyan 66 ürünün 66'sı da Suzuki üyesi; yani kayıp tamamen
# ÜYELİK BOŞLUĞUYDU (başlıkta model var, `marka[]`de yok).
def _kelimeler(metin):
    """Başlık/jeton -> normalleşmiş KELİME dizisi (Türkçe-duyarlı; alfanümerik dışı ayırıcı).
    `_norm` ana sayfanın kendi normalleştirmesidir (tek kaynak); kelime sınırı burada
    ayırıcıya indirgenir, böylece "F-150" ile "F 150" AYNI diziye düşer.

    🔴 AKSAN ÇÖZÜLÜR (ölçüldü 5 Ağu — 39 KAÇAN eşleşme): `_norm` yalnız Türkçe harfleri
    sadeleştirir; "Citroën C3" başlığında `ë` ayırıcıya düşüp marka adı "citro"+"n" diye
    İKİYE bölünüyordu ve `Citroen` ile BİTİŞİKLİK kurulamıyordu ("Citroën C3" 8 üründe,
    "Renault Zoé" 1 üründe...). Yanlış-negatifti (ürün eklenmiyordu, yanlış ürün girmiyordu)
    ama müşteri C3 sayfasında eksik görüyordu. Çözüm genel: NFKD + birleşen işaretleri at."""
    t = unicodedata.normalize("NFKD", _norm(metin or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [w for w in re.split(r"[^a-z0-9]+", t) if w]


def tehlike_jetonu_mu(jeton):
    """Jeton TEHLİKE SINIFINDA mı — çıplak tam-kelime YETMEZ, marka+model BİTİŞİK şart.

    🔴 SABİT LİSTE YOK, KURAL TÜRETİR (mimar hükmü): ikinci bir ikiz tanım doğmasın diye
    tehlike kümesi bir dosyada tutulmaz, jetonun ŞEKLİNDEN hesaplanır —
        · GÜVENLİ  : uzunluk >= 4  VE  tamamen sayısal DEĞİL   -> çıplak tam-kelime yeter
        · TEHLİKE  : uzunluk <= 3  YA DA  tamamen sayısal      -> yalnız bitişik ifade
    ÖLÇÜLEN GEREKÇE (5 Ağu): kısa/sayısal model adı katalogda 260 adet (`5`,`A`,`V`,`205`,
    `300`,`C5`,`E30`,`T4`,`FL`…). Renault ∧ çıplak `5` ∧ üye-değil turnusolunda 7 ürün
    çıkıyordu; içinde hem GERÇEK yakalama ("Renault 5 E-Tech") hem YANLIŞ pozitif
    ("Clio 5", "Espace 5" = kuşak sayısı) vardı. Bitişiklik şartı üçünü de doğru ayırır."""
    j = "".join(_kelimeler(jeton))
    return (not j) or len(j) <= 3 or j.isdigit()


def sasi_motor_kodu_mu(deger):
    """Değer bir ŞASİ/MOTOR KODU (harf+rakam karışık ARAÇ TANIMLAYICISI) mı?

    🔴 H1 (6 Ağu, mimar hükmü — SAYFA ALIR): `E46`, `M54`, `M57`, `N47`, `T4`, `W638`,
    `SW20`, `4AGE` … Bu katalogda müşteri parçayı şasi/motor koduyla arıyor; emsal ZATEN
    YAYINDA (`/marka/bmw/e46/`, `e36`, `e30`, `e39`).

    🔴 KURAL, LİSTE DEĞİL: desen jetonun ŞEKLİNDEN türer — TEK jeton + normalleşmiş
    gövdede EN AZ BİR HARF ve EN AZ BİR RAKAM. Elle envanter yazılsaydı katalog büyüdükçe
    bayatlar ve yeni bir şasi kodu sessizce yargısız kalırdı ([[ikiz-tanim-sessiz-ayrisma]]).

    🔴 ÇIPLAK SAYI BU HÜKMÜN DIŞINDADIR (mimar hükmü, açık): `57`, `86`, `17`, `660`
    HARF TAŞIMADIĞI için False döner. Onlar TEHLİKE sınıfında kalır (`tehlike_jetonu_mu`)
    ve yalnız marka+model BİTİŞİK ifadeyle eşleşir; `Renault|5` turnusolu bunu ölçer.
    İki eksen bilerek ayrıdır: bu yüklem SAYFA yargısıdır, tehlike sınıfı EŞLEŞME kuralı.

    🔴 BİLEŞİK YAZIM DIŞARIDA: `E46 M3`, `Skyline R32`, `Civic EP3` çok jetonludur ve
    H3 ekseninde (`<taban> <değiştirici>`) yargılanır — iki hükmün kırmızı kümesi
    ayrışsın diye tek jeton şartı KONULDU."""
    toks = (deger or "").strip().split()
    if len(toks) != 1:
        return False
    j = "".join(_kelimeler(deger))
    return bool(j) and any(c.isalpha() for c in j) and any(c.isdigit() for c in j)


def ayri_arac_adi_mi(deger):
    """Değer `<taban> <değiştirici>` biçiminde AYRI BİR ARACI mı adlandırıyor?

    🔴 H3 (6 Ağu, mimar hükmü): çok jetonlu bir kova, kuyruğu KAPALI DONANIM grameri
    DEĞİLSE ayrı bir aracı adlandırır ve SAYFA ALIR (`Zafira Life`, `Transporter T4`,
    `Corsa D`, `Megane II`, `Passat B8`); kuyruğu donanım/rozet soneki ise taban modele
    YAPIŞIKTIR, katlanır ve sayfa AÇMAZ (`Focus ST`, `Fiesta ST`, `206 GTI`).
    Emsal: `DEGISTIRICI_SAYFA_IZNI` bugün `Golf 4`, `Astra H`, `Megane 2`, `Corsa C`
    kuşak sayfalarını AÇIK tutuyor — kuşak işareti bu depoda meşru bir sayfadır."""
    return len((deger or "").strip().split()) >= 2 and not donanim_kuyruklu_mu(deger)


def sekil_kurali_yargisi(marka, canon, ad):
    """YALNIZ ŞEKİL KURALININ (H1 ∪ H3) yargısı — envanter SORULMAZ.

    🔴 AYRI GÖVDE OLMASININ SEBEBİ ÖLÇÜLEBİLİRLİKTİR (6 Ağu, hüküm E): "sayfa şekil
    kuralıyla mı yoksa tekil girişle mi doğdu" sorusu `baslik_yargisi_var_mi` bileşiğine
    bakarak CEVAPLANAMAZ (ikisi de True döner). Kapı bu gövdeyi ayrıca sorar ve muafiyetin
    GERÇEKTEN iş yaptığını ölçer — muafiyeti düşüren mutant burada KIRMIZI yakar.

    🔴 ARAÇ DIŞI MUAFİYETİ (`SEKIL_MUAF`): kural jetonun ŞEKLİNE bakar, "bu bir ARAÇ mı"
    sorusunu bilemez. Araç dışı olduğu yargılanmış çiftte kural SUSAR."""
    if (marka, canon) in SEKIL_MUAF:
        return False
    return sasi_motor_kodu_mu(ad) or ayri_arac_adi_mi(ad)


def baslik_yargisi_var_mi(marka, canon, ad, sahip):
    """BAŞLIK KOLUYLA doğan (marka, canon) kovası YARGILANMIŞ mı — TEK KAYNAK.

    🔴 `sahip` PARAMETRESİ ZORUNLUDUR (varsayılanı YOK, bilerek): varsayılan `None` yazsaydık
    parametreyi geçirmeyi UNUTAN bir çağıran (d) kolunu SESSİZCE kaybeder ve iki yüzey
    ayrışırdı. Eksik çağrı artık TypeError ile build'i DURDURUR (fail-closed).

    🔴 İKİNCİ TANIM YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]): aynı yargıyı hem sayfa
    üreteci (`yayimlanir_mi`) hem çip elemesi (`tools/cip-indeks.py::_elendi`) sorar.
    İki gövde ayrışırsa sayfası OLAN kova çipsiz, çipi OLAN kova sayfasız kalır — ikisi de
    SESSİZ. Yargı üç kaynaktan gelir:
      (a) `BASLIK_DOGAN_ALLOW` envanteri — tekil, elle yargılanmış çiftler,
      (b) H1 `sasi_motor_kodu_mu` — harf+rakam ŞASİ/MOTOR kodu (kural),
      (c) H3 `ayri_arac_adi_mi` — `<taban> <değiştirici>` AYRI araç adı (kural).
    (b)+(c) `sekil_kurali_yargisi` gövdesinde toplanır ve ARAÇ DIŞI muafiyetine tabidir:
    muaf çift ancak (a) ile doğar — kural araç dışı jetonlara açık kalmaz (hüküm E).
      (d) `jeton_sahibi` — jetonun KATALOGDAKİ SAHİBİ bu marka (kural, 12 Ağu; KraL hükmü).

    🔴 (d) NEDEN EKLENDİ — (a)'nın YERİNE GEÇMEK İÇİN DEĞİL, (a)'yı BÜYÜTMEMEK için:
    envanter elle tutuluyordu ve her partide bayatlıyordu; 80 kova / 588 ürün yalnız
    "envanterde yok" diye çipsiz kalıyordu. (d) katalogdan türer, marka-BAĞIMSIZDIR ve
    kanıt zayıfsa (jeton SAHİPSİZSE) SUSAR. Envanterin BAYATLADIĞINI ölçen fail-closed
    nöbetçi: `tools/marka-cip-kapisi.py::ENVANTER/*`."""
    return ((marka, canon) in BASLIK_DOGAN_ALLOW
            or sekil_kurali_yargisi(marka, canon, ad)
            or (sahip is not None and sahip == _canon(marka)))


def _dizi_iceriyor(hepsi, parca):
    """`parca` kelime dizisi, `hepsi` içinde BİTİŞİK alt-dizi olarak geçiyor mu?
    TAM KELİME ölçütü budur: alt-dize taraması "Golf"u "Golfçü"de bulurdu."""
    n, m = len(hepsi), len(parca)
    if m == 0 or m > n:
        return False
    for i in range(n - m + 1):
        if hepsi[i:i + m] == parca:
            return True
    return False


def _onek_kovasi(jeton_kelimeleri, kova_yazimi):
    """Kova yazımı, jetonun BAŞ kelimeleriyle birebir mi ("Ami 6" -> "Ami")?
    Kuşak-dışı istisnasının başlık kolundaki karşılığı: taban okuması budur."""
    yw = _kelimeler(kova_yazimi)
    return bool(yw) and jeton_kelimeleri[:len(yw)] == yw


def marka_yazimlari(marka, evren):
    """Kanonik markanın BİTİŞİKLİK ifadesinde kullanılabilecek GÖRÜNEN adları
    ({"Opel","Vauxhall"} gibi). Yalnız AD LİSTESİ üretir; başlık metnine katlama UYGULANMAZ."""
    adlar = {marka}
    for x in getattr(evren, "taninmis", ()):
        if evren.marka_alias.get(x, x) == marka:
            adlar.add(x)
    return sorted(adlar)


def baslikta_tam_kelime(baslik_kelimeleri, marka_ad_kelimeleri, jeton):
    """Jeton, başlıkta KABUL EDİLEBİLİR biçimde geçiyor mu (kademeli kural)?

    🔴 BİTİŞİKLİK `evren.katla()`/`markaKatla()` İLE YAZILMAZ — mimar hükmü, ölçülmüş tuzak:
    katlama ÖNEK kuralı işletir, `katla("renault espace") -> "Renault"` döner. Bitişikliği
    "jetondan önceki kelimeleri katla, markaya eşit mi" diye yazsaydık "Renault Espace 5"
    testi GEÇER ve tehlike koruması SESSİZCE ölürdü (turnusol 3 -> 6). Burada yapılan şey
    DÜZ İFADE eşleşmesidir: `<marka adı> <jeton>` kelime dizisi başlıkta BİTİŞİK geçmeli."""
    jw = _kelimeler(jeton)
    if not jw or not baslik_kelimeleri:
        return False
    if not tehlike_jetonu_mu(jeton):
        return _dizi_iceriyor(baslik_kelimeleri, jw)
    for aw in marka_ad_kelimeleri:
        if aw and _dizi_iceriyor(baslik_kelimeleri, aw + jw):
            return True
    return False


def uyelik_jetonlari(p):
    """Ürünün MODEL ADAYI jetonları = `marka[]` ∪ ham `uyum[].model`.

    `uyum[].model` disjunkt'ı bugünkü katalogda ÖLÜ ölçüldü (5 Ağu: 0 yeni sayfa, 0 yeni
    kalem) — çünkü model taşıyan her `uyum` öğesinin jetonu zaten `marka[]`de kanonik
    olarak geçiyor. YİNE DE OKUNUR: veri partileri `uyum`u `marka[]`den ÖNCE dolduruyor
    ve kolun düşmesi o gün SESSİZ bir üyelik boşluğu açardı. Ölü kalması bir ÖLÇÜMDÜR,
    bir garanti değil."""
    out = [(x or "").strip() for x in (p.get("marka") or [])]
    for o in (p.get("uyum") or []):
        t = (o.get("model") or "").strip()
        if t:
            out.append(t)
    return [x for x in out if x]


def model_jetonlari(marka, marka_dizisi, evren):
    """`marka` SAYFASI altında ürünün üye olduğu model anahtarları -> {anahtar: Counter(yazım)}.

    🔴 ÜYELİK POZİSYONDAN BAĞIMSIZ (ölçülen sessiz hata, 3 Ağu): eski kural modeli YALNIZ
    `marka[1]`'den okuyordu. ['Opel','Vauxhall','Corsa'] gibi kayıtlarda marka[1] başka bir
    marka adı olduğu için ürün HİÇBİR model sayfasına giremiyordu (429 çiftin 123'ünde sayfa
    filtreden dar, 366 ürün etkileniyordu). Artık dizinin HER elemanı model adayıdır; ürün
    birden çok model sayfasında görünebilir — bu mükerrer DEĞİL, doğru üyeliktir.

    Model SAYILMAYAN değerler:
      * değerin KENDİSİ bir MARKA ("Citroen", "Volvo Penta", "Yanmar", "Scion") —
        `marka_jetonu_mu`: index.html küratörlüğü + arama.py KAPALI MARKA KÜMESİ,
      * marka öneki sıyrıldıktan sonra geriye bir şey kalmayan değer ("Peugeot"),
      * bütünüyle markanın bir yazımı olan değer ("Mercedes-Benz" -> Mercedes,
        "Champion" -> Champion): anahtar markanın kendisine eşit olurdu.
    İlk madde ana sayfa filtresini DARALTMAZ: filtre yalnız ANAHTAR karşılaştırır, bu kural
    hangi kovanın DOĞACAĞINI belirler (sayfa evreni) — kovası olmayan çift ölçülmez.

    `uyum[]` AYRI bir üyelik kaynağı olarak OKUNMAZ — okunmasına gerek olmadığı ÖLÇÜLDÜ
    (3 Ağu, 17032 ürün): `uyum[].model` jetonlarının 6762'sinin TAMAMI zaten `marka`
    dizisinde kanonik olarak geçiyor, yalnız-uyumda kalan jeton sayısı 0. Okunsaydı sayfa,
    ana sayfa filtresinin (yalnız `marka` dizisine bakar) göremediği ürünü listeler ve
    ayrışma TERS yönde doğardı. `uyum` marka<->model BAĞI için kullanılmaya devam eder
    (tools/cip-indeks.py)."""
    out = {}
    marka_kanon = _canon(marka)
    for x in marka_dizisi:
        t = (x or "").strip()
        if not t or marka_jetonu_mu(t, evren):
            continue
        kalan = _strip_marka_oneki(marka, t, evren)
        if not kalan:
            continue
        if kalan == t and evren.katla(t) == marka:
            continue
        k = evren.model_anahtari(marka, t)
        if not k or k == marka_kanon:
            continue
        out.setdefault(k, Counter())[kalan] += 1
    return out


def gruplandir(products, evren, ek_markalar=()):
    """Katalogdaki markaları topla:
    kanonik_marka -> {"marka_only":[p...], "ikincil":[p...], "gruplar":{canon:{...}}}.
    Grup: {"display":str, "slug":str, "canon":str, "urunler":[p...], "birincil":bool}.
    urunler.json DEĞİŞMEZ (normalize yalnız build anında).

    ÜYELİK (marka) : marka_uyelikleri() — index.html filtresiyle birebir (KATLANMIŞ ad; her eleman).
    ÜYELİK (model) : model_jetonlari() — dizinin HER elemanı, kanonik anahtarla. Bir ürün aynı
                     markanın birden çok modelinde olabilir. Kural, ana sayfa filtresiyle
                     (index.html modelEsler/modelAnahtar) TEK KAYNAKTAN türer.
    BİRİNCİL       : marka[0]'ın katlanmışı (tanınmıyorsa ilk üye). SAYFA EVRENİNİ o belirler:
                     bir model kovası ancak en az bir ürünün BİRİNCİL markasıysa yayımlanır
                     (`g["birincil"]`). Üyelik ise evrenden BAĞIMSIZ ve tamdır: yayımlanan
                     kovada filtrenin gösterdiği HER ürün bulunur (kapı: SAYFA_DAR=0).
    """
    veri = {}

    def kova(marka):
        d = veri.get(marka)
        if d is None:
            d = {"marka_only": [], "ikincil": [], "gruplar": {}, "_spelling": {},
                 "birincil_ids": set()}
            veri[marka] = d
        return d

    bekleyen = []                        # (kanonik marka, marka dizisi, birincil, p, jetonlar)
    for p in products:
        m = p.get("marka") or []
        if not m:
            continue
        uyeler = marka_uyelikleri(m, evren, ek_markalar)
        if not uyeler:
            continue
        birincil = birincil_marka(m, evren, ek_markalar)
        # MODEL disjunkt'ının ilk iki kolu (ham `uyum[].model` ∪ `model_kanon`) AYNI jeton
        # listesinden beslenir; marka ÜYELİĞİ yalnız `marka[]`den türemeye devam eder
        # (`uyum` marka açmaz — o ayrı bir yargı).
        ham_marka = list(m)
        m = uyelik_jetonlari(p)
        for kan in uyeler:
            d = kova(kan)
            if kan == birincil and p.get("id"):
                # BİRİNCİLLİK BURADA KAYDEDİLİR (ürün çip haritasının tek kaynağı): uret()
                # yeniden hesaplasaydı, gruplandir'ı bozan bir mutasyon çip haritasına
                # YANSIMAZ ve mutasyon bataryası körelirdi ([[beyan-edilmis-survivor]]).
                d["birincil_ids"].add(p["id"])
            jetonlar = model_jetonlari(kan, m, evren)
            # 🔴 AD OYU YALNIZ `marka[]`DEN GELİR: `uyum` kolu ÜYELİK açar, İSİM VERMEZ.
            # Ölçülen risk (5 Ağu): `uyum[].model` yazımları gösterim oyuna karışınca
            # `FJR1300` kovasının adı `FJR 1300`e döndü — H1 ve SLUG değişir, yani
            # /marka/yamaha/fjr1300/ URL'i sessizce taşınırdı (SEO regresyonu).
            # Kova YALNIZ `uyum`dan doğduysa (marka[]'de hiç yazımı yok) oy oradan alınır —
            # aksi halde kovanın adı olmazdı.
            ad_jetonlari = model_jetonlari(kan, ham_marka, evren)
            bekleyen.append((kan, m, birincil, p, jetonlar))
            if not jetonlar:                     # model kırılımı YOK (marka-only / çok markalı)
                (d["marka_only"] if kan == birincil else d["ikincil"]).append(p)
                continue
            for canon, yazimlar in jetonlar.items():
                g = d["gruplar"].get(canon)
                if g is None:
                    g = {"canon": canon, "urunler": [], "birincil": False, "marka": kan,
                         "kusak": {}}
                    d["gruplar"][canon] = g
                    d["_spelling"][canon] = Counter()
                g["urunler"].append(p)           # jeton başına DEĞİL, anahtar başına tek kez
                d["_spelling"][canon].update(ad_jetonlari.get(canon) or yazimlar)
                if kan == birincil:
                    g["birincil"] = True

    # ---- FAZ 2: KUŞAK/VARYANT KATLAMASI (4 Ağu, KraL hükmü) -------------------------
    # `Golf 4`/`Golf Mk4`/`Golf IV`/`Golf R` ürünleri ANA `Golf` kovasına da girer.
    # 🔴 NEDEN AYRI FAZ: katlama YALNIZCA katalogda ZATEN VAR OLAN taban kovasına yapılır
    # (yeni kova uydurulmaz — "Type 2" -> "Type" kovası yok, katlanmaz). Taban kovalarının
    # tamamı ancak birinci faz bittiğinde bilinir; tek fazda ürün SIRASI sonucu belirlerdi.
    # 🔴 ÜYELİK KURALI JETON BAŞINADIR, KOVA BAŞINA DEĞİL: ana sayfa filtresi de ürünün HAM
    # jetonlarına bakar. Kova düzeyinde katlasaydık, aynı kovadaki boşluksuz yazım
    # ("GolfMk4") sayfada katlanır, filtrede katlanmazdı -> FILTRE_DAR.
    # 🔴 ANA LİSTE KİRLENMEZ: katlanan ürün `g["kusak"]` altında KAYNAK kovasıyla kaydedilir;
    # sayfa onu ayrı bölümde ("Golf 4 parçaları") gösterir — katlama UYUM VAADİ DEĞİLDİR.
    for _marka, _d in veri.items():
        for _g in _d["gruplar"].values():
            _g["ana"] = list(_g["urunler"])      # TAM eşleşmeyle giren ürünler (ana liste)
    for kan, m, birincil, p, jetonlar in bekleyen:
        d = veri.get(kan)
        if d is None:
            continue
        katlar = {}                              # taban canon -> {kaynak varyant canon}
        for x in m:
            t = (x or "").strip()
            if not t or marka_jetonu_mu(t, evren):
                continue
            kaynak = evren.model_anahtari(kan, t)
            if not kaynak:
                continue
            for taban, _etiket in evren.kusak_tabanlari(kan, t):
                if taban in jetonlar or taban not in d["gruplar"] or taban == kaynak:
                    continue                     # zaten TAM eşleşmeyle üye / taban kovası YOK
                katlar.setdefault(taban, set()).add(kaynak)
        for taban, kaynaklar in katlar.items():
            g = d["gruplar"][taban]
            g["urunler"].append(p)
            # Birden çok varyant jetonu aynı tabana katlanırsa ürün TEK bölümde görünür
            # (deterministik: alfabetik ilk kaynak) — aksi halde sayfada mükerrer kart olurdu.
            g["kusak"].setdefault(sorted(kaynaklar)[0], []).append(p)
            if kan == birincil:
                g["birincil"] = True

    # kanonik gösterim + slug
    for marka, d in veri.items():
        for canon, g in d["gruplar"].items():
            display = _KANONIK_GOSTERIM.get((marka, canon))
            if not display:
                # deterministik: en sık yazım, eşitlikte alfabetik (Counter sırası girdiye bağlı)
                display = sorted(d["_spelling"][canon].items(),
                                 key=lambda t: (-t[1], t[0]))[0][0]
            g["display"] = display
            g["slug"] = _slug(display)

    # ---- FAZ 3: BAŞLIK KOLU (5 Ağu, mimar hükmü) ------------------------------------
    # Model disjunkt'ının ÜÇÜNCÜ kolu: ürünün BAŞLIĞINDA modelin adı TAM KELİME geçiyorsa
    # (tehlike sınıfında yalnız marka+model BİTİŞİK ifadeyle) ürün o kovaya girer.
    # 🔴 YENİ KOVA UYDURULMAZ (FAZ 2 ile aynı disiplin): eşleşme yalnız katalogda ZATEN VAR
    # OLAN kovalara yapılır. Serbest metinden jeton türetmek "hangi kelime modeldir"
    # yargısını kodun eline verirdi; kova evreni `marka[]`/`uyum[]` küratörlüğünde kalır.
    # 🔴 SAYFA EVRENİ AYRICA YARGILANIR: yalnız bu kol sayesinde eşiği/birincilliği geçen
    # kova `g["baslik_dogan"]` ile işaretlenir ve yayımı BASLIK_DOGAN_ALLOW'a bağlanır.
    _urun_uyelik = []                        # (id, üye markalar, birincil, başlık kelimeleri)
    for p in products:
        pid = p.get("id")
        m = p.get("marka") or []
        if not pid or not m:
            continue
        uyeler = marka_uyelikleri(m, evren, ek_markalar)
        if not uyeler:
            continue
        _urun_uyelik.append((pid, p, set(uyeler), birincil_marka(m, evren, ek_markalar),
                             _kelimeler(p.get("baslik") or "")))
    for marka, d in veri.items():
        ad_kelimeleri = [_kelimeler(a) for a in marka_yazimlari(marka, evren)]
        # KÜRATÖRLÜ "FARKLI ARAÇ" İSTİSNASI BAŞLIK KOLUNDA DA GEÇERLİDİR (ölçülen sızıntı,
        # 5 Ağu): `Citroen|Ami 6` kuşak-dışı ilan edilmiştir (1961 Ami 6 ≠ 2020 Ami), ama
        # ürünün BAŞLIĞI "Citroen Ami 6 …" olduğu için çıplak tam-kelime `Ami` eşleşiyor ve
        # istisna sessizce ÖLÜYORDU. Kural yazılabilir, ikinci tablo YOK: ürün kuşak-dışı
        # bir jeton taşıyorsa, o jetonun ÖNEKİ olan kovalara başlıktan GİRMEZ.
        kusak_disi_jetonlari = []
        for _kayit in getattr(evren, "kusak_disi", []):
            _p = _kayit.split("|", 1)
            if len(_p) == 2 and _p[0] == marka:
                kusak_disi_jetonlari.append((_kelimeler(_p[1]),
                                             evren.model_anahtari(marka, _p[1])))
        kovalar = []
        for canon, g in d["gruplar"].items():
            # Kovanın ARANACAK yazımları: kanonik gösterim + katalogda görülen yazımlar.
            # Her yazım tehlike sınıfına AYRI AYRI bakılır (kova "C5" yazımını da taşıyorsa
            # o yazım için bitişiklik şartı ayrıca işler).
            yazimlar = set(x for x in (d["_spelling"].get(canon) or ()) if x)
            yazimlar.add(g["display"])
            g["baslik_dogan"] = not (g.get("birincil") and len(g["urunler"]) >= ESIK)
            kovalar.append((g, sorted(yazimlar),
                            set(x.get("id") for x in g["urunler"] if x.get("id"))))
        for pid, p, uyeler, birincil, baslik_kelimeleri in _urun_uyelik:
            if marka not in uyeler or not baslik_kelimeleri:
                continue
            yasak = []                       # bu ürüne KAPALI kova anahtarları (kuşak-dışı)
            if kusak_disi_jetonlari:
                _urun_jetonlari = uyelik_jetonlari(p)
                for _tw, _tk in kusak_disi_jetonlari:
                    if any(evren.model_anahtari(marka, _t) == _tk for _t in _urun_jetonlari):
                        yasak.append((_tw, _tk))
            for g, yazimlar, mevcut in kovalar:
                if pid in mevcut:
                    continue
                if any(g["canon"] != _tk and _onek_kovasi(_tw, y)
                       for _tw, _tk in yasak for y in yazimlar):
                    continue
                if not any(baslikta_tam_kelime(baslik_kelimeleri, ad_kelimeleri, y)
                           for y in yazimlar):
                    continue
                mevcut.add(pid)
                g["urunler"].append(p)
                g["ana"].append(p)               # TAM ADIYLA eşleşti -> ana liste (kuşak DEĞİL)
                g.setdefault("baslik_ekli", set()).add(pid)
                if marka == birincil:
                    g["birincil"] = True

    # KUŞAK BÖLÜMLERİ — başlık/slug ancak TÜM display'ler atandıktan sonra kurulabilir.
    # Sıra deterministik: çok üründen aza, eşitlikte alfabetik (aynı katalog -> bayt-aynı sayfa).
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            bolumler = []
            for kaynak, urunler in g.get("kusak", {}).items():
                kg = d["gruplar"].get(kaynak)
                bolumler.append({
                    "canon": kaynak,
                    "display": (kg or {}).get("display") or kaynak,
                    "slug": (kg or {}).get("slug") or _slug(kaynak),
                    # Kuşağın KENDİ sayfası kapanmaz; varsa alt bölüm başlığı oraya link olur.
                    "sayfa": bool(kg) and yayimlanir_mi(kg),
                    "urunler": urunler,
                })
            g["kusak_bolum"] = sorted(bolumler,
                                      key=lambda b: (-len(b["urunler"]), b["display"]))

    # ---- GÜRÜLTÜ SINIFI DAMGASI (12 Ağu, Okan hükmü) --------------------------------
    # Yargı KOVAYA damgalanır; `yayimlanir_mi` onu OKUR. Yüklemi yayımlama anında yeniden
    # hesaplasaydık tabloyu iki kez kurar ve iki gövde sessizce ayrışabilirdi.
    _sahiplik = marka_sahiplik_tablosu(products, evren, ek_markalar)
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            g["yabanci_marka"] = yabanci_marka_mi(marka, g.get("display"), g["canon"],
                                                  _sahiplik)
            # (d) kolunun girdisi de KOVAYA damgalanır: `yayimlanir_mi` tabloyu yeniden
            # kurmaz, OKUR. İkinci kurulum = ikinci gövde = sessiz ayrışma riski.
            g["jeton_sahibi"] = None

    # ---- (d) KOLU: ÇAPRAZ-MARKA ÇARPIŞMASINDA SUSAR (fail-closed) --------------------
    # 🔴 ÖLÇÜLDÜ 12 Ağu: (d) ilk yazımında `Mazda|B-Serisi` doğdu; aynı kanon Honda'da
    # ZATEN yayımdaydı (H3 kolu) ve ortaya YARGISIZ bir ÇAPRAZ-MARKA çifti çıktı — kardeş
    # kapı (`model-uyelik-kapisi.py::K19`) KIRMIZI yandı. Çapraz çift bu depoda küratörlü
    # bir yargıdır (`arama.ROZET_CAPRAZ_IZINLI`) ve KraL'in 12 Ağu gevşetmesi YALNIZ
    # başlık-doğan eksenini kapsar. Çözüm elle liste büyütmek DEĞİL: (d) kolu, kanonu
    # BAŞKA bir markada zaten yayımda olan kovalarda SUSAR. Kanıt zayıfsa çip DOĞMAZ.
    _taban_canon = set()                 # (d) KAPALIYKEN yayımlanan kanonlar
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            if yayimlanir_mi(g):         # g["jeton_sahibi"] halen None -> (d) kapalı
                _taban_canon.add(g["canon"])
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            if g["canon"] in _taban_canon:
                continue                 # çapraz çarpışma riski -> (d) susar
            g["jeton_sahibi"] = jeton_sahibi(g.get("display") or g["canon"], _sahiplik)
    return veri


def yayimlanir_mi(g):
    """Model kovası SAYFA olur mu — TEK KAYNAK (üretici, kabul testi ve kapı aynı yüklemi
    kullanır; ikinci bir eşik ifadesi yazılırsa sayfa sayısı ile kapının saydığı ayrışır).

    ROZET KAPISI (4 Ağu, KraL hükmü): model o markanın ROZETİYLE satılmamışsa sayfa
    AÇILMAZ — `/marka/audi/golf/` (Golf VW rozetidir) gibi. Küme küratörlü ve kimliği
    donmuş: `arama.ROZET_DISI_CIFT`. Ürün KAYBOLMAZ: sayfası açılmayan kovanın ürünleri
    marka sayfasında ve kendi gerçek model sayfasında listelenmeye devam eder."""
    if (g.get("marka"), g.get("canon")) in ROZET_DISI:
        return False
    # AYRI MARKA (12 Ağu, Okan — canlıdan): çip etiketi bu markanın MODELİ değil, katalogda
    # KENDİ ürünleri olan BAŞKA BİR MARKA (`Hyundai|Genesis`, `Suzuki|Sierra`). Yargı
    # `gruplandir`da damgalanır (bkz. yabanci_marka_mi); kural marka-BAĞIMSIZDIR.
    if g.get("yabanci_marka"):
        return False
    # MODEL OLMAYAN ÇİFT (4 Ağu, mimar hükmü): donanım paketi / motor ailesi SAYFA OLMAZ
    # (`Focus ST`, `Fiesta ST`, `EcoBoost`). Ürün KAYBOLMAZ: kuşak katlamasıyla ana modelin
    # varyant bölümünde, her hâlükârda marka sayfasında durur (kapı ölçer).
    if model_olmayan_cift_mi(g.get("marka"), g.get("display") or g.get("canon")):
        return False
    # H3 DENY KOLU (6 Ağu, mimar hükmü): taban modele YAPIŞIK donanım/rozet soneki taşıyan
    # kova AYRI BİR ARACI adlandırmaz -> SAYFA AÇMAZ. Ürün KAYBOLMAZ: kuşak katlaması onu
    # ana modelin varyant bölümünde, her hâlükârda marka sayfasında gösterir.
    # 🔴 ENVANTERDEN BAĞIMSIZ, MARKA-KÖR: `("Ford","ST")` gibi marka-özel deny kayıtları
    # yalnız ELLE girilen çiftleri kapatır; bu kol kuralı KATALOG GENELİNDE işletir
    # (ölçüldü: bugün donanım kuyruklu 16 kova var, 14'ü eşik altında -> etkisi 0 sayfa,
    # ama kural yarın eşiği geçen `Clio GT`/`Yaris RS` için ÖNCEDEN kapalıdır).
    if donanim_kuyruklu_mu(g.get("display") or g.get("canon")):
        return False
    if not (bool(g.get("birincil")) and len(g["urunler"]) >= ESIK):
        return False
    # YARGISIZ SAYFA DOĞMAZ (5 Ağu, mimar hükmü): kova SAYFA eşiğini/birincilliğini YALNIZ
    # başlık kolu sayesinde geçiyorsa, o (marka, canon) çifti açıkça yargılanmış olmalı.
    # Yargısız kova yayımlanmaz; ürünü KAYBOLMAZ (marka sayfasında ve kendi gerçek model
    # sayfasında durur — kapı bunu ölçer).
    # 🔴 YARGI ÜÇ KAYNAKTAN GELİR (6 Ağu, mimar hükmü — envanter TEK yol değil):
    #   (a) `BASLIK_DOGAN_ALLOW` — tekil, elle yargılanmış çiftler,
    #   (b) H1 `sasi_motor_kodu_mu` — harf+rakam ŞASİ/MOTOR kodu (kural, liste değil),
    #   (c) H3 `ayri_arac_adi_mi` — `<taban> <değiştirici>` AYRI araç adı (kural).
    # (b) ve (c) KURAL olduğu için katalog büyüdükçe bayatlamaz; envanter yalnız kuralın
    # kapsamadığı tekil yargıları taşır ve böylece sessizce ŞİŞMEZ.
    if g.get("baslik_dogan") and not baslik_yargisi_var_mi(
            g.get("marka"), g.get("canon"), g.get("display") or g.get("canon"),
            g.get("jeton_sahibi")):
        return False
    return True


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
  /* SAYFA-İÇİ MODEL FİLTRESİ: çip tıklanınca adres DEĞİŞMEZ, kartlar burada süzülür. */
  .mm-model-btn.mm-aktif{border-color:var(--navy);background:var(--navy);color:#fff}
  .mm-model-btn.mm-aktif .adet{color:#c9d6ea}
  /* İSKELET: çip tıklanınca kart verisi gelene kadar ekranı BOŞ bırakmayan yer tutucu.
     Sınıfı BİLEREK `card` DEĞİL — kart sayan nöbetçiler bunu kart sanmasın. */
  .mm-iskelet{border:1px solid #e2e7f0;border-radius:12px;background:#eef1f6;min-height:270px;
    animation:mmNabiz 1.1s ease-in-out infinite}
  @keyframes mmNabiz{0%,100%{opacity:.5}50%{opacity:.85}}
  @media (prefers-reduced-motion:reduce){.mm-iskelet{animation:none}}
  .mm-filtre-sifirla{margin:2px 0 0;font-size:13px}
  .mm-filtre-sifirla a{color:var(--navy-2)}
  /* ARTIMLI KART ÇİZİMİ (ilk N kart HTML'de, kalanı aynı sayfada) */
  .mm-artim{margin:16px 0 4px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .mm-tumu-btn{background:var(--navy);color:#fff;border:0;border-radius:10px;
    padding:11px 20px;font-weight:700;font-size:15px;cursor:pointer;font-family:inherit}
  .mm-tumu-btn:hover{background:var(--navy-2)}
  .mm-artim-durum{font-size:13px;color:var(--gray-text)}
  /* Model sayfası OLMAYAN kalemlerin düz bağ listesi: JS-siz erişim + iç link (öksüz yok) */
  .mm-kalan-bag{margin:10px 0 4px;padding:0 0 0 2px;list-style:none;columns:2;column-gap:26px;
    font-size:13.5px}
  .mm-kalan-bag li{margin:0 0 5px;break-inside:avoid}
  .mm-kalan-bag a{color:var(--navy-2);text-decoration:none}
  .mm-kalan-bag a:hover{text-decoration:underline}
  @media (max-width:640px){ .mm-kalan-bag{columns:1} }
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
  /* Sayfanın KANONİK toplamı (kart + model kovası TEKİL birleşimi; kapsam varken JS düşürür) */
  .mm-toplam{margin:0 0 10px;font-size:14px;color:var(--gray-text)}
  .mm-toplam .mm-sayim-toplam{font-weight:700;color:var(--navy)}
  /* KAPSAM şeridi (?kategori=<Kategori> ile gelindiğinde JS açar; kanonik/parametresiz
     sayfada display:none kalır → crawler tam koleksiyonu görür, SEO regresyonu yok). */
  .mm-kapsam{margin:0 0 14px;padding:10px 14px;border:1px solid var(--gray-line);
    border-radius:9px;background:var(--gray-card);font-size:14px;color:var(--navy)}
  .mm-kapsam a{color:var(--navy-2);font-weight:600;margin-left:8px}
  .mm-bos{margin:18px 0;color:var(--gray-text);font-size:15px}
  /* Marka/model sayfası arama kutusu — ana sayfadakiyle AYNI görsel dil, YENİ arama motoru
     kurmaz: salt HTML GET formu ana katalog aramasına (/?ara=…) yönlendirir. Bağlam (marka=)
     gizli alanla korunur; "Tüm katalogda ara" görünür çıkışı daraltmayı temizler. */
  .mm-arama{position:relative;display:flex;align-items:center;gap:0;margin:16px 0 6px;
    max-width:480px}
  .mm-arama-ikon{position:absolute;left:13px;width:18px;height:18px;fill:#8996ad;
    pointer-events:none}
  .mm-arama-kutu{flex:1;padding:11px 14px 11px 40px;border:1px solid var(--gray-line);
    border-radius:9px 0 0 9px;font-size:14.5px;font-family:inherit;background:#fff;
    color:var(--navy);min-width:0}
  .mm-arama-kutu:focus{outline:none;border-color:var(--navy-2)}
  .mm-arama-btn{padding:11px 18px;border:1px solid var(--navy);border-left:none;
    border-radius:0 9px 9px 0;background:var(--navy);color:#fff;font-weight:700;
    font-size:14.5px;cursor:pointer}
  .mm-arama-btn:hover{background:var(--navy-2);border-color:var(--navy-2)}
  .mm-arama-tumu{display:inline-block;margin:0 0 18px;font-size:13px;color:var(--gray-text);
    text-decoration:underline}
  .mm-arama-tumu:hover{color:var(--navy-2)}
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
  // SAYFANIN KANONİK TOPLAMI (7 Ağu — Okan'ın bildirdiği "eksik görünüyor" kusuru).
  // 🔴 BİRİM: ekrandaki "N parça" sayısı KART SAYISI DEĞİLDİR. Marka sayfasında ürünlerin
  // bir kısmı yalnızca MODEL BUTONLARININ ARDINDADIR; kart saymak ölçülen bir sayfada 201
  // yazdırıyordu, sayfadan ulaşılabilen gerçek küme 330'du. "kart + Σ buton" da yanlış:
  // iki küme ÇAKIŞIR (o sayfada 40 ürün ikisinde de; naif toplam 373). Doğru sayı SSR'de
  // tek Python fonksiyonundan (sayfa_kalemleri) türeyen TEKİL kategori kırılımıdır ve
  // buradan AYNI sayimla() ile okunur — ikinci bir sayma kuralı yok.
  // FAIL-CLOSED: kırılım yoksa/tekil değilse null döner (yanlış sayı basmaktansa sayı basma).
  function toplamla(dok, c){
    var el = dok.querySelectorAll(".mm-toplam[data-katsay]");
    if(!el || el.length !== 1){ return null; }
    var ham = el[0].getAttribute("data-katsay");
    if(!ham){ return null; }
    try{ if(!JSON.parse(ham)){ return null; } }catch(e){ return null; }
    return sayimla(ham, c);
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
  // BÖLÜM SAYAÇLARI — başlıklardaki "(N)" sayıları. 🔴 DOM SAYIMI DEĞİL, KIRILIMDAN:
  // marka sayfasının kartları artımlı çizilir, bu yüzden görünen DÜĞÜM sayısı o an
  // BASILANI verir, kullanıcının ERİŞEBİLDİĞİNİ değil (canlıda ölçüldü: beyan 593 ↔
  // başlık 80; kapsam kolunda 575 ↔ 304). Her başlık KENDİ kümesinin kırılımını taşır ve
  // beyan cümlesiyle AYNI sayimla() ile okunur — ikinci sayma kuralı yok.
  // FAIL-CLOSED: kırılım yok/bozuksa "—" (yanlış sayı basmaktansa sayı basma).
  function bolumSayaclari(dok, c){
    var el = dok.querySelectorAll(".mm-sayim-kart[data-katsay]"), i, ham, saglam;
    for(i = 0; i < el.length; i++){
      ham = el[i].getAttribute("data-katsay");
      saglam = false;
      try{ saglam = !!ham && !!JSON.parse(ham); }catch(e){ saglam = false; }
      el[i].textContent = saglam ? String(sayimla(ham, c)) : "—";
    }
    return el.length;
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
    // DÜZ BAĞ ÖĞELERİ (model sayfası olmayan kalemlerin liste girdileri): kart DEĞİL ama
    // sayfada GÖRÜNÜR -> AYNI `gorunur()` yüklemiyle süzülür ve AYNI sayaca girer.
    // 🔴 EK SEÇİCİ, DEĞİŞTİRİLEN SEÇİCİ DEĞİL: `.card[data-kat]` davranışı bayt-aynı kalır.
    // 🔴 AYRI SAYAÇ (gorunenBag), gorunenKart'a EKLENMEZ: düz bağ girdileri kartlarla AYNI
    // ürünleri gösterir. Artım kalanı çizdikten sonra aynı ürün HEM kart HEM bağ olarak
    // görünür; naif toplam kanonik toplamı AŞAR ve aşağıdaki tutarlılık kapısı sayıyı
    // sessizce "—"ye düşürürdü (fail-closed ama YANLIŞ sebeple). İki küme AYRI AYRI
    // toplamın alt kümesidir; kapı ikisini de ayrı ölçer.
    var gorunenBag = 0;
    var duzler = dok.querySelectorAll(".mm-kalan-oge[data-kat]");
    for(i = 0; i < duzler.length; i++){
      var ad2 = gorunur(duzler[i].getAttribute("data-kat"), c);
      duzler[i].style.display = ad2 ? "" : "none";
      if(ad2){ gorunenBag++; }
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
    // KANONİK TOPLAM. Tutarlılık kapısı: toplam görünen karttan KÜÇÜK olamaz (kartlar
    // toplamın alt kümesidir) — ihlal = kırılım bayat/bozuk demektir, sayı BASILMAZ.
    var toplam = toplamla(dok, c);
    if(toplam !== null && (toplam < gorunenKart || toplam < gorunenBag)){ toplam = null; }
    // GERİYE DÖNÜK KOL: `data-katsay` TAŞIMAYAN bir sayım rozeti eski davranışta kalır
    // (görünen kart sayısı). ÜRETİLEN her sayfada attribute ZORUNLUDUR; kapı bunu TÜM
    // sayfa evreninde ölçer (fail-closed), yani üretimde bu kol hiç çalışmaz.
    yazSayim(dok, ".mm-sayim-kart", gorunenKart);
    bolumSayaclari(dok, c);
    yazSayim(dok, ".mm-sayim-model", gorunenModel);
    yazSayim(dok, ".mm-sayim-toplam", toplam === null ? "—" : toplam);

    // GÖRÜNÜR kapsam şeridi + kapsamı KALDIRMA yolu (kanonik, parametresiz adres).
    // Metin textContent ile yazılır (innerHTML YOK) -> URL'den gelen değer kod olamaz.
    var not = dok.getElementById("kapsamNot");
    if(not){ not.style.display = ""; }
    var metin = dok.getElementById("kapsamNotMetin");
    if(metin){
      metin.textContent = c.gecerli
        ? ("Kapsam: yalnız " + c.kategori + " kategorisi — " +
           (toplam === null ? "parça sayısı ölçülemedi" : (toplam + " parça")))
        : ("Geçersiz kapsam: “" + c.kategori + "” bir kategori değil — " +
           "sonuç gösterilmiyor.");
    }
    var sifirla = dok.getElementById("kapsamNotSifirla");
    if(sifirla && loc && loc.pathname){ sifirla.setAttribute("href", loc.pathname); }
    var bos = dok.getElementById("kapsamBos");
    if(bos){
      bos.style.display = (gorunenKart === 0 && gorunenBag === 0 && gorunenModel === 0)
        ? "" : "none";
    }
    return c;
  }
  g.PRUVO_KAPSAM = {coz: coz, gorunur: gorunur, sayimla: sayimla, sorgu: sorgu,
                    toplamla: toplamla, bolumSayaclari: bolumSayaclari,
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


# ---- ARAMA BAĞLAMI TAŞIMA (index.html marka çipi -> /marka/<slug>/?ara=… -> ana katalog) ----
# NEDEN VAR (Okan, 3 Ağu — ölçülen müşteri hatası): ana sayfada "Kapı Kolu" aranıp sonuçta
# Volvo çipine basılınca arama sorgusu (q) DÜŞÜYORDU; marka sayfası statik, kendi arama motoru
# YOK. index.html'in markaKapsamSorgusu() TEK üreticisi artık `ara=` parametresini de bu
# sayfaya taşır — burada AYNI sorguyu, bu sayfanın markasını (+varsa kategori) koruyarak ana
# katalog aramasına (`/?ara=…&marka=…`) geri yönlendiririz. Yeni bir arama mantığı KURULMAZ,
# YALNIZ mevcut çalışan uca (index.html /?ara=) yönlendirilir. Test buradan MARKER'larla
# ayıklayıp node ile GERÇEKTEN koşar (kapsam scripti ile AYNI desen) → tools/arama-tasi-test.py.
_ARA_TASI_JS_BAS = "/* PRUVO ARAMA TASI BAS */"
_ARA_TASI_JS_SON = "/* PRUVO ARAMA TASI SON */"

_ARA_TASI_JS_GOVDE = r"""
(function(){
  var MARKA = __MARKA__;
  var p;
  try { p = new URLSearchParams(window.location.search); } catch(e){ return; }
  var ara = p.get("ara");
  if(!ara){ return; }   // kanonik/parametresiz adres -> sayfaya HİÇ dokunulmaz (SEO regresyonu yok)
  var hedef = new URLSearchParams();
  hedef.set("ara", ara);
  if(MARKA){ hedef.set("marka", MARKA); }
  var kat = p.get("kategori");
  if(kat){ hedef.set("kategori", kat); }
  window.location.replace("/?" + hedef.toString());
})();
"""


def ara_tasi_scripti(marka):
    """Sayfaya gömülecek ARAMA-TAŞI scripti (marker'lı; test buradan ayıklayıp node'da koşar)."""
    govde = _ARA_TASI_JS_GOVDE.replace(
        "__MARKA__", json.dumps(marka or "", ensure_ascii=False, separators=(",", ":")))
    return "<script>" + _ARA_TASI_JS_BAS + govde + _ARA_TASI_JS_SON + "</script>"


# ---- ARTIMLI KART ÇİZİMİ + SAYFA-İÇİ MODEL FİLTRESİ (marka sayfası) ----
# 🔴 NEDEN VAR (Okan hükmü, 8 Ağu): marka sayfası markanın TÜM parçalarını KART olarak
# listeler ve model çipleri AYRI ADRESE GİTMEZ, sayfa İÇİNDE filtreler. Ama tüm kartları
# SSR'de basmak kabul edilemez ağırlık üretiyordu (ölçüldü: en büyük marka 2582 kart
# ≈ 1,27 MB; ikinci sıradaki sayfa bugün 770 KB ile index.html'i (235 KB) ZATEN aşıyor).
# ÇÖZÜM: ilk N kart HTML'de (SEO + ilk boya, JS-siz halde de görünür), kalanı AYNI SAYFADA
# artımlı çizilir. HARİCİ KÜTÜPHANE/CDN YOK, saf JS.
#
# 🔴 KART VERİSİ EDGE'DEN, TÜM KATALOGDAN DEĞİL (ölçüldü, 8 Ağu): ilk yazımda artım kolu
# `/urunler.json` çekiyordu = 21.330.991 B ham / 3.133.127 B gzip, 32 sayfada, kaydırmada
# OTOMATİK. Ana sayfa bu deseni `EDGE_KATALOG=true` ile BİLEREK terk etti (gerekçe
# index.html'de yazılı: mobil ilk açılış + bellek). Marka sayfası da AYNI mevcut yolu
# kullanır: `EDGE_UC + /katalog?ids=` ile YALNIZ çizilecek id'ler, 100'lük partiler hâlinde.
# İlk açılışta HİÇ veri isteği YOK (kartlar SSR'de); istek ancak kullanıcı kaydırınca /
# "tümünü göster"e basınca / model filtresi seçince atılır.
# Sayfaya ait kalem listesi + model üyeliği + override'lar sayfa yanındaki `parcalar.json`
# (SSR türevi, LAZY çekilir).
# 🔴 KART GÖVDESİ TEK KAYNAK: `kartHtml` Python `_kart` ile BAYT-AYNI dize üretir; kapı
# bunu node'da koşturup her kalem için Python çıktısıyla KARŞILAŞTIRIR (ikiz tanım sessizce
# ayrışamaz → [[ikiz-tanim-sessiz-ayrisma]]).
_ARTIM_JS_BAS = "/* PRUVO ARTIM BAS */"
_ARTIM_JS_SON = "/* PRUVO ARTIM SON */"

_ARTIM_JS_GOVDE = r"""
(function(g){
  var PARTI = 60;               // her artımda çizilecek kart sayısı
  function esc(s){
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }
  // Python `_kart` ile BAYT-AYNI kart gövdesi. `o` = sayfanın override kaydı (bkz.
  // _kart_yuk_kaydi): istemcinin katalog kaydından TÜRETEMEDİĞİ alanlar.
  function kartHtml(u, o, site, ekAttr){
    o = o || {};
    var kat = String(u.kategori || "").replace(/^\s+|\s+$/g, "");
    var baslik = o.b !== undefined ? o.b
               : (String(u.baslik || "").replace(/^\s+|\s+$/g, "") || String(u.id || ""));
    // KAPAK: edge ucu (`/katalog?ids=`) TEKİL `gorsel` alanı döner (ölçüldü: 100/100 ürün,
    // `gorseller` dizisi EDGE'de YOK); `urunler.json` ise `gorseller` dizisi taşır. İki
    // şekil de okunur -> veri yolu değişse bile kart kapağı sessizce boşalmaz.
    var gorseller = u.gorseller || [];
    var hamKapak = u.gorsel || (gorseller.length ? gorseller[0] : "");
    var cover = o.g !== undefined ? o.g : hamKapak;
    var fiyat, bos;
    if(o.f !== undefined){ fiyat = o.f; bos = !!o.e; }
    else {
      var ham = String(u.fiyat || "").replace(/^\s+|\s+$/g, "");
      fiyat = ham || "Fiyat için sipariş verin";
      bos = !ham;
    }
    var badge = u.parametrik ? '<span class="card-badge">Ölçüye Özel</span>' : "";
    // 🔴 ŞABLON BİLEREK PARÇALI YAZILIR: bu depodaki ölçüm araçları üretilen HTML'i
    // düzenli ifadeyle tarıyor ve script gövdesini soymayanlar bu şablonu GERÇEK BİR KART
    // sayıyordu (ölçüldü: her marka sayfasında +1 hayalet kart, iki ayrı nöbetçi 80/81
    // basıp kırmızı yandı). Parçalar birleşince çıktı BAYT-AYNI kalır, ama kaynakta
    // `<div class="card" data-kat="` dizesi HİÇ oluşmaz -> hayalet eşleşme YAPISAL olarak
    // imkânsızdır (her nöbetçiyi tek tek yamamak yerine kaynağında kesildi).
    var KART_ACIK = '<div class="card' + '" data-kat="';
    var ANA_ACIK = '><a class="card' + '-main" href="';
    return KART_ACIK + esc(kat) + '"' + (ekAttr || "")
      + ANA_ACIK + esc(site + "/urun/" + u.id + "/") + '">'
      + '<img class="card-img" alt="' + esc(baslik) + '" loading="lazy" src="' + esc(cover) + '">'
      + '<div class="card-body">'
      + '<span class="card-cat">' + esc(kat) + '</span>'
      + '<div class="card-title">' + esc(baslik) + '</div>'
      + '<div class="card-price' + (bos ? " empty" : "") + '">' + esc(fiyat) + '</div>'
      + '</div>' + badge + '</a></div>';
  }
  // Kalem kaydı -> kartın data-mm değeri (model üyeliği; sayfa-içi filtre bu alandan süzer).
  function mmAttr(kayit){
    var ix = kayit[2] || [];
    return ix.length ? ' data-mm="' + ix.join(" ") + '"' : "";
  }
  // Sayfanın yükünden GÖSTERİLECEK kalemleri süz. FAIL-CLOSED: yük tanınmazsa boş küme
  // (yanlış kart basmaktansa hiç basma).
  function suz(yuk, modelIx, kategori){
    if(!yuk || !yuk.k){ return []; }
    var out = [], i, kayit;
    for(i = 0; i < yuk.k.length; i++){
      kayit = yuk.k[i];
      if(!kayit || !kayit[0]){ continue; }
      if(kategori !== null && kategori !== undefined
         && (yuk.kat || [])[kayit[1]] !== kategori){ continue; }
      if(modelIx !== null && modelIx !== undefined
         && (kayit[2] || []).indexOf(modelIx) === -1){ continue; }
      out.push(kayit);
    }
    return out;
  }
  function manifest(dok){
    var el = dok.getElementById("mmManifest");
    if(!el){ return null; }
    var v;
    try{ v = JSON.parse(el.textContent || "null"); }catch(e){ return null; }
    // FAIL-CLOSED: edge ucu / yol / parti beyanı EKSİKSE hiç istek atılmaz (yanlış uca
    // istek atıp sessizce boş kalmaktansa kol hiç kurulmaz).
    if(!v || !v.yuk || !v.uc || !v.yol || !v.parti || !v.site){ return null; }
    return v;
  }
  // Çizilecek id'leri PARTİLERE böl (edge ucu tek istekte en çok `parti` id alır).
  function partile(idler, parti){
    var out = [], i;
    for(i = 0; i < idler.length; i += parti){ out.push(idler.slice(i, i + parti)); }
    return out;
  }
  // Bir partinin istek adresi. TEK YERDE kurulur; kapı bu fonksiyonun ürettiği adresi
  // kanonik değerle karşılaştırır.
  function istekAdresi(man, idler){
    return man.uc + man.yol + encodeURIComponent(idler.join(","));
  }
  g.PRUVO_ARTIM = {esc: esc, kartHtml: kartHtml, mmAttr: mmAttr, suz: suz,
                   manifest: manifest, partile: partile, istekAdresi: istekAdresi,
                   PARTI: PARTI};

  // ---------------------------------------------------------------- tarayıcı kolu
  // (node'da `document` yok -> kurulmaz; yukarıdaki saf fonksiyonlar test edilebilir kalır)
  if(typeof document === "undefined" || !g.addEventListener){ return; }
  g.addEventListener("DOMContentLoaded", function(){
    var man = manifest(document);
    var grid = document.getElementById("mmGrid");
    if(!man || !grid){ return; }
    var dugme = document.getElementById("mmTumu");
    var durum = document.getElementById("mmDurum");
    var yuk = null, cizilen = man.basili, mesgul = false, aktifModel = null;
    var katalog = {};        // id -> edge kaydı (yalnız ÇEKİLENLER; tüm katalog İNMEZ)
    var istekSayisi = 0;     // ölçüm: kaç ağ isteği atıldı (kapı bunu iddia ediyor)
    function kapsamKategorisi(){
      var K = g.PRUVO_KAPSAM;
      if(!K){ return null; }
      var c;
      try{ c = K.coz(new URLSearchParams(g.location.search).get("kategori"), K.KATEGORILER); }
      catch(e){ return null; }
      return (c && c.aktif && c.gecerli) ? c.kategori : null;
    }
    // Sayfanın kalem listesi (SSR türevi, sayfanın YANINDA). Bir kez çekilir.
    function yukuGetir(){
      if(yuk){ return Promise.resolve(true); }
      istekSayisi++;
      return fetch(man.yuk).then(function(r){ return r.json(); })
        .then(function(d){ yuk = d; return true; });
    }
    // Yalnız ÇİZİLECEK id'lerin kart verisini edge'den al (100'lük partiler).
    // 🔴 TÜM KATALOG İNDİRİLMEZ: eksik olan id yoksa HİÇ istek atılmaz.
    function kartlariGetir(idler){
      var eksik = [], gorulen = {}, i;
      for(i = 0; i < idler.length; i++){
        if(!katalog[idler[i]] && !gorulen[idler[i]]){ gorulen[idler[i]] = true; eksik.push(idler[i]); }
      }
      if(!eksik.length){ return Promise.resolve(true); }
      var partiler = partile(eksik, man.parti);
      return Promise.all(partiler.map(function(p){
        istekSayisi++;
        return fetch(istekAdresi(man, p), {cache: "no-cache"})
          .then(function(r){ return r.ok ? r.json() : null; })
          .then(function(d){
            var arr = (d && d.urunler) || [], j;
            for(j = 0; j < arr.length; j++){
              if(arr[j] && arr[j].id){ katalog[arr[j].id] = arr[j]; }
            }
          });
      })).then(function(){ return true; });
    }
    function getir(idler){
      return yukuGetir().then(function(){ return kartlariGetir(idler || []); })
        .catch(function(e){
          if(durum){ durum.textContent = "Kalan parçalar yüklenemedi."; }
          console.error("Artim yuklenemedi:", e);
          return false;
        });
    }
    // Kalemleri çiz. `bastan` true ise HTML'de basılı kartlar da yeniden değerlendirilir
    // (model filtresi): basılı kartlar GİZLENİR/GÖSTERİLİR, kalanlar çizilir.
    function ciz(kalemler, bas, adet){
      var parcalar = [], i, kayit, u;
      for(i = bas; i < kalemler.length && i < bas + adet; i++){
        kayit = kalemler[i];
        u = katalog[kayit[0]];
        if(!u){ continue; }             // fail-closed: kataloğda yok -> kart basma
        // data-artim: JS'in çizdiği kartın işareti (filtre sıfırlanınca bunlar kaldırılır).
        // İşaret `ciz`de eklenir, `kartHtml`de DEĞİL -> kart gövdesi Python `_kart` ile
        // BAYT-AYNI kalır (kapı bunu karşılaştırıyor).
        parcalar.push(kartHtml(u, (yuk.o || {})[kayit[0]], man.site,
                               mmAttr(kayit) + ' data-artim=""'));
      }
      if(parcalar.length){ grid.insertAdjacentHTML("beforeend", parcalar.join("")); }
      return Math.min(bas + adet, kalemler.length);
    }
    function sayilariTazele(){
      if(g.PRUVO_KAPSAM){
        try{ g.PRUVO_KAPSAM.uygula(document, g.location); }catch(e){ /* sayaç kolu */ }
      }
    }
    // "Tümünü göster" / kaydırma: sayfanın KALANINI aynı sayfada çizer.
    function devam(hepsi){
      if(mesgul){ return; }
      mesgul = true;
      // Sıra ÖNEMLİ: önce kalem listesi (hangi id'ler), sonra YALNIZ çizilecek id'lerin
      // kart verisi. Tersi tüm katalogu çekmek olurdu.
      yukuGetir().then(function(){
        var kalemler = suz(yuk, aktifModel, kapsamKategorisi());
        var adet = hepsi ? kalemler.length : PARTI;
        var dilim = kalemler.slice(cizilen, cizilen + adet);
        return kartlariGetir(dilim.map(function(k){ return k[0]; })).then(function(){
          cizilen = ciz(kalemler, cizilen, adet);
          if(durum){
            durum.textContent = cizilen >= kalemler.length
              ? "" : (cizilen + " / " + kalemler.length + " parça gösteriliyor");
          }
          if(dugme && cizilen >= kalemler.length){ dugme.style.display = "none"; }
          sayilariTazele();
        });
      }).catch(function(e){
        if(durum){ durum.textContent = "Kalan parçalar yüklenemedi."; }
        console.error("Artim yuklenemedi:", e);
      }).then(function(){ mesgul = false; });
    }
    if(dugme){
      dugme.addEventListener("click", function(e){ e.preventDefault(); devam(true); });
    }
    // kaydırmada artımlı: sayfa sonuna yaklaşınca bir parti daha
    g.addEventListener("scroll", function(){
      if(mesgul || !dugme || dugme.style.display === "none"){ return; }
      var kalan = document.body.scrollHeight - (g.scrollY + g.innerHeight);
      if(kalan < 800){ devam(false); }
    }, {passive: true});
    // MODEL ÇİPİ = SAYFA-İÇİ FİLTRE (adres DEĞİŞMEZ). JS yoksa çip model sayfasına gider
    // (iç link + JS-siz erişim korunur) -> aşağıdaki preventDefault YALNIZ JS varken çalışır.
    var cipler = document.querySelectorAll(".mm-model-btn[data-mm]");
    function artimKartlariniSil(){
      var eski = document.querySelectorAll("#mmGrid .card[data-artim]"), j;
      for(j = 0; j < eski.length; j++){ eski[j].parentNode.removeChild(eski[j]); }
    }
    function cipleriIsaretle(ix){
      for(var i = 0; i < cipler.length; i++){
        var kendi = ix !== null && cipler[i].getAttribute("data-mm") === String(ix);
        cipler[i].className = "mm-model-btn" + (kendi ? " mm-aktif" : "");
      }
    }
    // ÇİPİN KENDİ BASTIĞI SAYI — ikinci bir sayım noktası DEĞİL, sayfanın o çipte zaten
    // yazdığı beyanın OKUNMASI. Yükleniyor metni bunu yankılar; KESİN sayı yük gelince
    // hükmü besleyen kümeden (`kalemler.length`) tazelenir ve kapı ikisinin EŞİTLİĞİNİ ölçer.
    function cipBeyani(ix){
      for(var i = 0; i < cipler.length; i++){
        if(cipler[i].getAttribute("data-mm") === String(ix)){
          var s = cipler[i].querySelector(".adet");
          var n = s ? parseInt(String(s.textContent).replace(/[^0-9]/g, ""), 10) : NaN;
          return isNaN(n) ? null : n;
        }
      }
      return null;
    }
    // ---- BEYAN EDİLEN SAYI == O AN ERİŞİLEBİLEN KÜME (12 Ağu, Okan hükmünün MODEL ekseni)
    // Ölçüldü (canlı): model filtresi "4 parça" gösterirken bölüm başlığı hâlâ "… (355)"
    // diyordu. Bu, `?kategori=` ekseninde kapatılan sınıfın AYNISI: kullanıcıya gösterilen
    // sayı, gösterilen kümeden türemiyordu. Sayılar TEK yerden yazılır.
    var kalanBolum = document.getElementById("mmKalan");
    var beyanDugumleri = [];
    (function(){
      var i, ds = document.querySelectorAll(".mm-sayim-kart"), t;
      for(i = 0; i < ds.length; i++){
        beyanDugumleri.push({el: ds[i], bolum: ds[i].getAttribute("data-bolum"),
                             ilk: ds[i].textContent});
      }
      t = document.querySelector(".mm-sayim-toplam");
      if(t){ beyanDugumleri.push({el: t, bolum: "erisim", ilk: t.textContent}); }
    })();
    function beyaniYaz(n){
      // n === null -> SSR/kapsam koluna geri dön (kapsam modülü kendi sayısını yazar)
      for(var i = 0; i < beyanDugumleri.length; i++){
        var b = beyanDugumleri[i];
        b.el.textContent = (n === null) ? b.ilk : String(b.bolum === "alt" ? 0 : n);
      }
      if(kalanBolum){ kalanBolum.style.display = (n === null) ? "" : "none"; }
    }
    // ---- İSKELET: ekran BOŞ KALMAZ ------------------------------------------------
    // Kart verisi ağdan gelene kadar (ölçüldü: 1,0-6,5 sn) grid tamamen boşalıyordu.
    // Tıklamayla AYNI KAREDE yer tutucu çizilir; gerçek kartlar gelince kaldırılır.
    var ISKELET_TAVAN = 12;             // görünür alanı doldurmaya yeter; 2000 düğüm basmaz
    function iskeletSil(){
      var e = document.querySelectorAll("#mmGrid .mm-iskelet");
      for(var i = 0; i < e.length; i++){ e[i].parentNode.removeChild(e[i]); }
    }
    function iskeletCiz(n){
      iskeletSil();
      var adet = Math.max(1, Math.min(n || 1, ISKELET_TAVAN)), p = [], i;
      for(i = 0; i < adet; i++){ p.push('<div class="mm-iskelet" aria-hidden="true"></div>'); }
      grid.insertAdjacentHTML("beforeend", p.join(""));
    }
    function filtreUygula(ix){
      if(mesgul){ return; }
      aktifModel = ix;
      cipleriIsaretle(ix);
      artimKartlariniSil();
      iskeletSil();
      // 🔴 BOŞ EKRAN + BAYAT SAYI YASAK (ölçüldü 12 Ağu, CANLI TARAYICI, cache-bust'sız):
      // çipe basılınca SSR kartlarının TAMAMI gizleniyordu — basılı kartlar sayfanın YEREL
      // kalemleridir ve model üyeliği TAŞIMAZLAR — ve yük gelene kadar ekranda 0 kart
      // kalıyordu (üç ayrı sayfada 1,9 sn · ~1-3 sn · >6,5 sn ölçüldü). Durum metni bu
      // pencerede ya BOŞTU ya da BİR ÖNCEKİ çipin sayısını gösteriyordu (seçili çip
      // "7 parça" iken ekranda "54 parça" yazıyordu). Kullanıcının gördüğü şey tam olarak
      // "çipe tıklanınca hedef açılmıyor"dur. Metin tıklama ANINDA tazelenir.
      var beyan = (ix === null) ? null : cipBeyani(ix);
      if(durum){
        if(ix === null){ durum.textContent = ""; }
        else {
          durum.textContent = (beyan === null ? "Parçalar yükleniyor…"
                                              : beyan + " parça yükleniyor…");
        }
      }
      beyaniYaz(beyan);
      if(ix !== null){ iskeletCiz(beyan); }
      if(ix === null){                        // SIFIRLA: SSR kartları geri, sayaç tazelenir
        var hepsiKart = document.querySelectorAll("#mmGrid .card"), i;
        for(i = 0; i < hepsiKart.length; i++){ hepsiKart[i].style.display = ""; }
        cizilen = man.basili;
        if(dugme){ dugme.style.display = ""; }
        if(durum){ durum.textContent = ""; }
        sayilariTazele();
        return;
      }
      // FİLTRE ETKİN: SSR kartlarından üye OLMAYANLAR gizlenir, modelin kalemleri çizilir.
      var kartlar = document.querySelectorAll("#mmGrid .card"), k;
      for(k = 0; k < kartlar.length; k++){
        var ham = kartlar[k].getAttribute("data-mm");
        var uyeli = ham ? ham.split(" ").indexOf(String(ix)) !== -1 : false;
        kartlar[k].style.display = uyeli ? "" : "none";
      }
      mesgul = true;
      yukuGetir().then(function(){
        var kalemler = suz(yuk, ix, kapsamKategorisi());
        // SSR'de basılı ve BU modele üye olan kalemler zaten görünür -> onları atla
        var basiliIds = {}, i, ss = document.querySelectorAll("#mmGrid .card:not([data-artim])");
        for(i = 0; i < ss.length; i++){
          var a = ss[i].querySelector(".card-main");
          var h = a ? a.getAttribute("href") : "";
          var pid = h ? h.replace(/\/$/, "").split("/").pop() : "";
          if(pid){ basiliIds[decodeURIComponent(pid)] = 1; }
        }
        var eksik = [];
        for(i = 0; i < kalemler.length; i++){
          if(!basiliIds[kalemler[i][0]]){ eksik.push(kalemler[i]); }
        }
        // YALNIZ bu modelin eksik kalemleri çekilir (tüm katalog DEĞİL)
        return kartlariGetir(eksik.map(function(k){ return k[0]; })).then(function(){
          iskeletSil();                       // yer tutucular gerçek kartlara BIRAKIR
          ciz(eksik, 0, eksik.length);
          if(durum){ durum.textContent = kalemler.length + " parça (model filtresi etkin)"; }
          if(dugme){ dugme.style.display = "none"; }
          // 🔴 KESİN SAYI HÜKMÜ BESLEYEN KÜMEDEN: `kalemler.length`. Çipin bastığı sayı
          // yalnız YÜKLENİRKEN gösterilen geçici yankıydı; ikisi ayrışırsa kapı
          // (SAYI/filtre) KIRMIZI yanar — burada sessizce uzlaştırılmaz.
          beyaniYaz(kalemler.length);
          sayilariTazele();
        });
      }).catch(function(e){
        iskeletSil();                         // hata hâlinde yer tutucu ASILI KALMAZ
        if(durum){ durum.textContent = "Kalan parçalar yüklenemedi."; }
        console.error("Artim filtresi yuklenemedi:", e);
      }).then(function(){ mesgul = false; });
    }
    for(var c = 0; c < cipler.length; c++){
      cipler[c].addEventListener("click", function(e){
        e.preventDefault();
        var ix = parseInt(this.getAttribute("data-mm"), 10);
        filtreUygula(aktifModel === ix ? null : ix);
      });
    }
    // BOŞ PENCERENİN KAYNAĞI AĞ TURUDUR: yük ancak TIKLAMADAN SONRA istenirdi. Kullanıcı
    // çip şeridine DOKUNUR DOKUNMAZ (işaretçi çipin üstüne gelince / basılınca) yükü
    // çekmeye başla — tıklama geldiğinde tur çoktan ilerlemiştir. Sayfa AÇILIŞINDA hâlâ
    // HİÇ istek YOK (ilk boya kararı bozulmaz); istek ancak NİYET belirince atılır.
    var onYuklendi = false;
    function onYukle(){
      if(onYuklendi){ return; }
      onYuklendi = true;
      yukuGetir().catch(function(){ onYuklendi = false; });
    }
    for(var oy = 0; oy < cipler.length; oy++){
      cipler[oy].addEventListener("pointerenter", onYukle);
      cipler[oy].addEventListener("pointerdown", onYukle);
    }
    var sifirla = document.getElementById("mmFiltreSifirla");
    if(sifirla){
      sifirla.addEventListener("click", function(e){ e.preventDefault(); filtreUygula(null); });
    }
    // ÖLÇÜM KANCASI: kaç ağ isteği atıldı, kaç kalem belleğe girdi, kaç kart çizildi.
    // Kapı/nöbetçi bunu okuyup "fetch GERÇEKTEN çağrıldı ve kart ÇİZDİ" iddiasını kurar
    // (yalnız "fonksiyon var" yeterli DEĞİL).
    g.PRUVO_ARTIM_DURUM = function(){
      var n = 0, k;
      for(k in katalog){ if(Object.prototype.hasOwnProperty.call(katalog, k)){ n++; } }
      return {istek: istekSayisi, bellek: n, cizilen: cizilen, aktifModel: aktifModel};
    };
  });
})(typeof window !== "undefined" ? window : globalThis);
"""


def artim_scripti():
    """Sayfaya gömülecek ARTIM scripti (marker'lı; kapı buradan ayıklayıp node'da koşar)."""
    return "<script>" + _ARTIM_JS_BAS + _ARTIM_JS_GOVDE + _ARTIM_JS_SON + "</script>"


def _arama_kutusu_html(esc, marka=None):
    """Marka/model sayfası arama kutusu — YENİ arama motoru KURULMAZ: salt HTML GET formu
    ana katalog aramasına (/?ara=…) yönlendirir (index.html'deki TEK çalışan arama yolu).
    `marka` verilmişse gizli alanla bağlam (marka=) korunur; altındaki "Tüm katalogda ara"
    linki daraltmayı temizleyen GÖRÜNÜR çıkıştır (Okan, 3 Ağu: müşteri kilitlenmesin — bazı
    marka+sorgu bileşimleri 0 sonuç dönebilir, ölçüldü)."""
    hidden = ('<input type="hidden" name="marka" value="%s">' % esc(marka)) if marka else ""
    yer_tutucu = (marka + " içinde ara…") if marka else "Ürün, marka veya parça numarası ara…"
    etiket = (marka + " içinde ürün ara") if marka else "Ürün ara"
    cikis = ('<a class="mm-arama-tumu" href="/">Tüm katalogda ara</a>' if marka else "")
    return (
        '<form class="mm-arama" action="/" method="get" role="search">'
        '<svg class="mm-arama-ikon" viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm'
        '-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>'
        '<input type="search" name="ara" class="mm-arama-kutu" autocomplete="off" placeholder="%s" '
        'aria-label="%s">'
        '%s'
        '<button type="submit" class="mm-arama-btn" aria-label="Ara">Ara</button>'
        '</form>%s'
    ) % (esc(yer_tutucu), esc(etiket), hidden, cikis)


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
{top_btn}
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
        top_btn=ctx["TOP_BTN_BLOCK_HTML"],
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
        # SATIŞ KAPISI (2026-08-04): hacmi doğrulanmamış ailede tutar BASILMAZ —
        # o ürün bugün satılamıyor (Worker sepeti 400 `hacim-dogrulanmamis`).
        # Karar TEK KAYNAK build.aile_satis_kapali_mi; ana sayfa kartı + ürün
        # sayfası da aynı kararı kullanır. Bugün bu daldan geçen kart 0 (parametrik
        # ürünler marka/model sayfalarında listelenmiyor) -> çıktı bayt-eşit.
        if sema and ctx["aile_satis_kapali_mi"](sema):
            return ctx["FIYATSIZ_METIN"], True
        if sema:
            taban = sema.get("tabanFiyatTL")
    if taban is not None:
        return ctx["taban_fiyat_metni"](taban) + "'den başlayan", False
    return ("Ölçüye özel fiyat" if parametrik else "Fiyat için sipariş verin"), True


def _kart(ctx, p, ek_attr=""):
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
        '<div class="card" data-kat="%s"%s><a class="card-main" href="%s">'
        '<img class="card-img" alt="%s" loading="lazy" src="%s">'
        '<div class="card-body">'
        '<span class="card-cat">%s</span>'
        '<div class="card-title">%s</div>'
        '<div class="card-price%s">%s</div>'
        '</div>%s</a></div>'
        % (esc(kategori), ek_attr, esc(ctx["product_url"](pid)), esc(baslik), esc(cover),
           esc(kategori), esc(baslik),
           " empty" if bos else "", esc(fiyat_metni), badge))


def _kart_yuk_kaydi(ctx, p):
    """İSTEMCİNİN kart çizerken `urunler.json`'dan TÜRETEMEDİĞİ alanlar (yalnız SAPMA yazılır).

    🔴 NEDEN OVERRIDE, NEDEN PORT DEĞİL: kart başlığı `_kart_temizle` (bağlam-duyarlı,
    maskeli, ~60 kurallı) ve fiyatı `_kart_fiyat` (parametrik/satış kapısı) ile üretilir.
    Bunları JS'e PORT etmek ikiz tanım kurardı ve sessizce ayrışırdı
    ([[ikiz-tanim-sessiz-ayrisma]]). Bunun yerine: istemci BASİT kuralı uygular
    (başlık = `baslik`, fiyat = `fiyat` ya da "Fiyat için sipariş verin"), Python o basit
    kuralın SONUCUYLA kanonik `_kart` sonucunu KARŞILAŞTIRIR ve YALNIZ ayrıştığında
    override yazar. Böylece tek kaynak Python'da kalır, yük de küçüktür (ölçüldü: 22376
    ürünün 3'ünde başlık, 23'ünde fiyat sapıyor)."""
    kayit = {}
    ham_baslik = (p.get("baslik") or "").strip()
    kanonik_baslik = _kart_temizle(ham_baslik) or (p.get("id") or "")
    if kanonik_baslik != (ham_baslik or (p.get("id") or "")):
        kayit["b"] = kanonik_baslik
    fiyat_metni, bos = _kart_fiyat(ctx, p)
    basit_fiyat = (p.get("fiyat") or "").strip() or "Fiyat için sipariş verin"
    basit_bos = not (p.get("fiyat") or "").strip()
    if fiyat_metni != basit_fiyat or bool(bos) != basit_bos:
        kayit["f"] = fiyat_metni
        kayit["e"] = 1 if bos else 0
    # Kapak: Python `images_of` BOŞ/geçersiz girdileri süzer, istemci ham `gorseller[0]`
    # okur -> ikisi ayrışabilir (ilk girdi boş dize olan ürün). Ayrışıyorsa override yaz.
    imgs = ctx["images_of"](p)
    kanonik_kapak = imgs[0] if imgs else _ph_data((p.get("kategori") or "").strip())
    ham_liste = p.get("gorseller") or []
    basit_kapak = ham_liste[0] if ham_liste else ""
    if kanonik_kapak != basit_kapak:
        kayit["g"] = kanonik_kapak
    return kayit


def _kat_sayim_json(urunler):
    """Model grubunun KATEGORİ kırılımı -> data-katsay JSON'u ({"Marin":3,"Motosiklet":5}).
    sort_keys: çıktı deterministik (aynı katalog -> bayt-aynı sayfa)."""
    c = Counter((p.get("kategori") or "").strip() for p in urunler)
    return json.dumps({k: v for k, v in c.items() if k},
                      ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _tekil(*kaynaklar):
    """id bazında TEKİLLEŞTİRİLMİŞ ürün listesi — İLK GÖRÜLEN KALIR (sıra BOZULMAZ).

    🔴 NEDEN VAR (7 Ağu, ölçüldü): marka sayfasının kart birleşimi
    (`kucuk_urunler + marka_only + ikincil`) tekilleştirilmiyordu; FAZ 3 (başlık kolu)
    `marka_only`'deki bir ürünü eşik-altı bir model kovasına da soktuğunda ürün AYNI
    sayfaya İKİ KEZ basılıyordu (31 marka sayfasında 282 fazla kart). Sıra korunur:
    kart dizilimi = katalog sırası, tekilleştirme onu yeniden dizmez."""
    out, gorulen = [], set()
    for kaynak in kaynaklar:
        for p in kaynak or ():
            anahtar = p.get("id") or ("#obj:%d" % id(p))
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            out.append(p)
    return out


def sayfa_kalemleri(kart_urunleri, kova_listeleri=()):
    """Bir marka/model sayfasından ULAŞILABİLİR TEKİL ürünler — SAYACIN TEK KAYNAĞI.

    🔴 SAYAÇ BİRİMİ (7 Ağu, Okan'ın bildirdiği kusur): ekrandaki "N parça" sayısı
    KART SAYISI DEĞİLDİR. Marka sayfasında ürünlerin bir kısmı kart olarak basılır
    (`diger`), bir kısmı yalnızca model butonlarının ARDINDADIR. Ölçülen bir sayfa 202 kart
    basarken sayfadan ulaşılabilen gerçek küme 330 kalemdi; şerit "201 parça" yazıyordu.
    "kart + Σ buton" da YANLIŞTIR: kart kümesi ile kova kümesi ÇAKIŞIR (aynı sayfada 40 ürün
    hem kart hem kovada; naif toplam 373 verir). Doğru birim TEKİL BİRLEŞİMDİR.

    Bu fonksiyon o birleşimi üretir; sayfa metni, meta açıklaması ve istemcideki kapsam
    şeridi AYNI bu listeden türer (`_kat_sayim_json` ile kategori kırılımı olarak gömülür).
    İkinci bir toplama formülü YAZILMAZ → [[ikiz-tanim-sessiz-ayrisma]]."""
    return _tekil(kart_urunleri, *list(kova_listeleri))


def bolum_ayrimi(kart_kollari, kova_listeleri):
    """Sayfanın İKİ BÖLÜMÜNÜ AYRIK kurar; sayfanın HER sayısı bu tek kaynaktan türer.

    🔴 NEDEN VAR (8 Ağu 2026, Okan İKİ KEZ bildirdi — hatası SESSİZ): marka sayfasının iki
    bölümü ("Modele göre seçin" butonları + yerel kartlar) ÇAKIŞIYORDU. `kucuk_urunler` kolu
    yayımlanan model kovasındaki ürünü eliyordu, ama `marka_only` ve `ikincil` kolları
    ELEMİYORDU → "Diğer" kelimesi TÜMLEYEN vaat ederken küme kovalarla kesişiyordu ve
    kullanıcı ekranda gördüğü sayılardan sayfa toplamını TÜRETEMİYORDU (ölçülen bir sayfada
    26 ürün hem
    kartta hem kovada; 32 marka sayfası sapıyordu, sapma DAİMA pozitif).

    🔴 KURULAN DEĞİŞMEZ (ESKİ KURALIN TERSİ): kart kolu ∪kova ile AYRIKTIR.
    Eskiden çakışma "normal" sayılır, `sayfa_kalemleri`nin tekilleştirmesiyle yutulurdu; o
    yükleme kapı bile "çakışma doğru davranış" diye İDDİA EDİYORDU. Artık çakışma İHLALDİR:
    kovada görünen ürün kart kolundan ELENİR.

        |kart| + |∪kova| == |toplam|          ("yerel bölüm" GERÇEK tümleyendir)

    ÜRÜN KAYBOLMAZ: eleme yalnız ürünün hangi BÖLÜMDE sayıldığını belirler; sayfadan
    ulaşılabilen tekil küme (`kalemler`) DEĞİŞMEZ.

    Dönüş: (kart_urunleri, kalemler, sayilar);
    `sayilar` = {"toplam", "kart", "kova", "kova_sayisi"}."""
    kova_listeleri = list(kova_listeleri)
    kova_ids = set()
    for lst in kova_listeleri:
        for p in lst or ():
            pid = p.get("id")
            if pid:
                kova_ids.add(pid)
    kart_urunleri = [p for p in _tekil(*kart_kollari) if p.get("id") not in kova_ids]
    kalemler = sayfa_kalemleri(kart_urunleri, kova_listeleri)
    sayilar = {"toplam": len(kalemler), "kart": len(kart_urunleri),
               "kova": len(kova_ids), "kova_sayisi": len(kova_listeleri)}
    # FAIL-CLOSED: kimlik yapısal olarak tutmalı; tutmuyorsa `_tekil`/eleme bozulmuş demektir
    # (mutasyon bataryası bu dalı ayrı bir düşüş imzası olarak ölçer).
    if sayilar["kart"] + sayilar["kova"] != sayilar["toplam"]:
        raise SystemExit(
            "HATA: bölüm kimliği ayrıştı — kart %d + kova %d != toplam %d (sayfanın "
            "bölümleri çakışıyor; ekrandaki sayılar toplamı vermez)."
            % (sayilar["kart"], sayilar["kova"], sayilar["toplam"]))
    return kart_urunleri, kalemler, sayilar


def _toplam_bloku(esc, kalemler, oncul):
    """Sayfanın KANONİK toplamı: görünür cümle + istemcinin okuyacağı kategori kırılımı.

    `data-katsay` ADI BİLEREK model butonlarıyla AYNI: istemci tarafında da AYNI
    `sayimla()` fonksiyonu okur (tek sayma kuralı, iki ayrı okuyucu yok)."""
    return ('<p class="mm-toplam" data-katsay="%s">%s <span class="mm-sayim-toplam">%d</span> '
            '%s</p>' % (esc(_kat_sayim_json(kalemler)), esc(oncul), len(kalemler),
                        esc("parça listeleniyor.")))


def _bolum_sayaci(esc, urunler, bolum):
    """BÖLÜM SAYACI — bir başlığın taşıdığı sayı, o bölümün KENDİ kategori kırılımından.

    🔴 NEDEN VAR (12 Ağu 2026, Okan canlıda bildirdi — SESSİZ kusur): bu sayı O AN BASILAN
    kart sayısını (`MARKA_KART_N` tavanı) yazıyordu, sayfadan ERİŞİLEBİLEN kalem sayısını
    DEĞİL. Aynı sayfada iki sayı görünüyordu: beyan cümlesi "593 parça listeleniyor",
    başlık "… parçaları (80)". Kapsam kolunda ÜÇÜNCÜ bir sayı doğuyordu (beyan 575 ↔
    başlık 304): istemci başlığa GÖRÜNEN DOM DÜĞÜMÜ sayısını yazıyordu ve artımlı çizilecek
    kalemler henüz DOM'da değildi. Sayfa "çalışıyor" görünür, kimse kırmızı yakmaz, müşteri
    kataloğu eksik sanır.

    🔴 ÇÖZÜM MARKA-BAĞIMSIZ VE TEK NOKTADIR: her başlık KENDİ kümesinin kategori kırılımını
    taşır (`data-katsay`), istemci onu model butonlarıyla ve beyan cümlesiyle AYNI
    `sayimla()` fonksiyonundan okur. DOM sayımı bir daha başlığa YAZILMAZ; ikinci bir sayma
    kuralı doğamaz → [[ikiz-tanim-sessiz-ayrisma]].

    `bolum` = kapının okuduğu SEMANTİK sınıf (marka-özel dal değil, sayfa-türü bağımsız):
      "erisim" — sayfanın TÜM erişilebilir kart yüzeyi (beyan ile EŞİT olmak ZORUNDA),
      "parca"  — sayfayı BÖLEN ayrık bölüm (bölümlerin toplamı erişim kümesini verir),
      "alt"    — erişim kümesinin ALT kümesi (aynı ürünleri düz bağ olarak listeler)."""
    return ('<span class="mm-sayim-kart" data-bolum="%s" data-katsay="%s">%d</span>'
            % (bolum, esc(_kat_sayim_json(urunler)), len(urunler)))


def _urun_grid(ctx, urunler, attr_of=None, grid_attr=""):
    parts = [_kart(ctx, p, attr_of(p) if attr_of else "") for p in urunler if p.get("id")]
    if not parts:
        return ""
    return '<div class="grid"' + grid_attr + '>' + "".join(parts) + "</div>"


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


def _kusak_bolumleri_html(ctx, marka_slug, g):
    """KUŞAK/VARYANT alt bölümleri — katlanan ürünler ana listeden AYRI listelenir.

    🔴 NEDEN AYRI BÖLÜM (Okan'ın `Zafira Life` kararında onayladığı desen): katlama sayfa
    toplamını büyütür ama UYUM VAADİ DEĞİLDİR — Golf Mk4 parçası Mk6'ya takılmaz. Müşteri
    parçayı Golf sayfasında BULUR, hangi kuşağa ait olduğunu da GÖRÜR.
    Kuşağın kendi sayfası varsa başlık oraya link olur (iç link + ürün iki yerde görünür;
    bu mükerrer değil, hiyerarşidir)."""
    esc = ctx["esc"]
    parts = []
    for b in g.get("kusak_bolum", []):
        if not b["urunler"]:
            continue
        ad = esc(b["display"]) + " parçaları"
        if b["sayfa"]:
            ad = ('<a href="/marka/' + marka_slug + '/' + b["slug"] + '/">' + ad + '</a>')
        parts.append('<h2 class="mm-sec-h mm-kusak-h" data-kusak="' + esc(b["display"]) + '">'
                     + ad + ' (' + _bolum_sayaci(esc, b["urunler"], "parca") + ')</h2>'
                     + _urun_grid(ctx, b["urunler"]))
    return "".join(parts)


# --------------------------------------------------------------------- sayfa üreticileri
# kontrol mutantı: yalnız yorum (davranış DEĞİŞMEZ)
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

    # Model sayfasının KANONİK toplamı: ana liste + kuşak bölümleri, TEKİL (model butonu yok).
    # Marka sayfasıyla AYNI fonksiyon — sayaç birimi iki sayfa türünde ayrışmasın.
    _kalemler = sayfa_kalemleri(g.get("ana", g["urunler"]),
                                [b["urunler"] for b in g.get("kusak_bolum", [])])
    if len(_kalemler) != len(_tekil(g["urunler"])):
        raise SystemExit("HATA: model sayfası toplamı ayrıştı — %s %s: sayfadan ulaşılabilen "
                         "%d kalem, kova tekil %d (sayaç birimi bozuk)."
                         % (marka, display, len(_kalemler), len(_tekil(g["urunler"]))))
    n = len(_kalemler)
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

    # ANA LİSTE = modelin KENDİ jetonunu taşıyan ürünler. Kuşak/varyant jetonundan KATLANAN
    # ürünler ana listeye KARIŞMAZ (katlama uyum vaadi değildir: Golf Mk4 parçası Mk6'ya
    # takılmaz) — her kuşak kendi başlığı altında, kendi sayfasına linkle listelenir.
    # Ayrım RENDER EDİLMİŞ HTML üzerinden ölçülür (tools/model-uyelik-kapisi.py K14).
    ana = g.get("ana", g["urunler"])
    body = (bc
            + '<h1>' + esc(h1) + '</h1>'
            + '<p class="lead">' + esc(giris) + '</p>'
            + _arama_kutusu_html(esc, marka)
            + _kapsam_not_html(esc)
            + _toplam_bloku(esc, _kalemler, "Bu sayfada")
            + '<h2 class="mm-sec-h">' + esc(display) + ' parçaları ('
            + _bolum_sayaci(esc, ana, "parca") + ')</h2>'
            + _urun_grid(ctx, ana)
            + _kusak_bolumleri_html(ctx, marka_slug, g)
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
                  kapsam_scripti(kategoriler) + ara_tasi_scripti(marka))
    return url, html


def _marka_sayfasi(ctx, marka, d, buyuk_gruplar, kucuk_urunler, kategoriler):
    esc = ctx["esc"]
    SITE = ctx["SITE"]
    marka_slug = _slug(marka)
    url = SITE + "/marka/" + marka_slug + "/"

    h1 = marka + " Yedek Parça — Ölçüye Özel Üretim"
    # YEREL bölüm: <ESIK modeller + yalnız-marka + İKİNCİL (çok markalı uyumluluk) ürünler.
    # İkincil = marka[0]'ı başka marka olan ama marka[] dizisinde bu markayı da taşıyan ürün;
    # index.html marka filtresi onu zaten bu markada gösteriyor -> sayfa da göstermeli.
    # 🔴 AYRIK KURULUR (bkz. bolum_ayrimi): kovada zaten görünen ürün yerel bölümden ELENİR.
    # Eskiden üç kol yalnız TEKİLLEŞTİRİLİYORDU; `marka_only`/`ikincil` kovadan elenmediği
    # için "Diğer" bölümü kovalarla ÇAKIŞIYORDU (32 marka sayfası, sapma daima pozitif).
    kova_listeleri = [g["urunler"] for g in buyuk_gruplar]
    yerel, kalemler, sayilar = bolum_ayrimi(
        [kucuk_urunler, d["marka_only"], d.get("ikincil", [])], kova_listeleri)
    toplam = sayilar["toplam"]
    # FAIL-CLOSED İKİZ KONTROLÜ: sayfadan ulaşılabilen küme ile marka kovasının kanonik
    # sayısı AYRIŞAMAZ. Ayrışırsa sayfa yanlış sayı basar ve kimse GÖRMEZ -> build durur.
    if toplam != marka_urun_sayisi(d):
        raise SystemExit("HATA: marka sayfası toplamı ayrıştı — %s: sayfadan ulaşılabilen "
                         "%d kalem, kova kanonik %d (sayaç birimi bozuk)."
                         % (marka, toplam, marka_urun_sayisi(d)))
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
    # data-mm = model İNDEKSİ: çip artık AYRI ADRESE GİTMEZ, sayfa İÇİNDE filtreler (Okan
    # hükmü). `href` KORUNUR: JS yoksa çip model sayfasına gider (iç link + JS-siz erişim +
    # crawl hedefi bozulmaz), JS varsa preventDefault ile sayfa-içi filtre çalışır.
    btns = []
    for i, g in enumerate(buyuk_gruplar):
        murl = "/marka/" + marka_slug + "/" + g["slug"] + "/"
        btns.append('<a class="mm-model-btn" href="%s" data-katsay="%s" data-mm="%d">'
                    '%s<span class="adet">%d parça</span></a>'
                    % (esc(murl), esc(_kat_sayim_json(g["urunler"])), i,
                       esc(g["display"]), len(g["urunler"])))
    model_html = '<div class="mm-models">' + "".join(btns) + "</div>" if btns else ""

    # ------------------------------------------------------- KART YÜZEYİ (Okan hükmü)
    # 🔴 KART YÜZEYİ = markanın TÜM parçaları (`kalemler`), model kovasındakiler DAHİL.
    # Ama hepsini SSR'de basmak ağırlık olarak kabul edilemez (ölçüldü: en büyük marka
    # 2582 kart ≈ 1,27 MB, ikincisi bugün 770 KB ile index.html'i ZATEN aşıyor). Bu yüzden:
    #   · ilk MARKA_KART_N kalem TAM KART olarak HTML'de (SEO + ilk boya + JS-siz görünürlük),
    #   · kalanı AYNI SAYFADA artımlı çizilir (parcalar.json + urunler.json, saf JS).
    # `kalemler` sırası = _tekil(yerel, *kovalar) -> YEREL kalemler BAŞTA gelir; bu tesadüf
    # değil, ORPHAN GÜVENLİĞİNİN dayanağıdır (aşağıya bak).
    model_uyelik = {}
    for i, g in enumerate(buyuk_gruplar):
        for p in g["urunler"]:
            pid = p.get("id")
            if pid:
                model_uyelik.setdefault(pid, []).append(i)

    def _mm_attr(p):
        ix = model_uyelik.get(p.get("id")) or []
        return (' data-mm="%s"' % " ".join(str(x) for x in ix)) if ix else ""

    basili = kalemler[:MARKA_KART_N]
    basili_ids = set(p.get("id") for p in basili)
    # 🔴 ORPHAN GÜVENLİĞİ (fail-closed): YEREL kalemlerin model sayfası YOKTUR — /marka/<m>/
    # dışında hiçbir yerde linklenmezler. Kart olarak basılmayan yerel kalemler bu yüzden
    # HTML'de düz bir link listesinde durmak ZORUNDA (yoksa marka hiyerarşisinde öksüz
    # kalırlar; tools/marka-model-test.py bunu ölçüyor). Kova kalemleri öksüz OLAMAZ:
    # çipin işaret ettiği model sayfası onları listeler.
    yerel_kalan = [p for p in yerel if p.get("id") not in basili_ids]
    kalan_html = ""
    if yerel_kalan:
        # data-kat: bu kalemler de KAPSAM ekseninde (?kategori=) süzülür — kart olmasalar da
        # sayfada GÖRÜNÜR öğedirler; süzülmezlerse Marin kapsamında motosiklet parçasının adı
        # ekranda kalırdı (kartlarda kapatılan sessiz kusurun aynısı).
        baglar = "".join(
            '<li class="mm-kalan-oge" data-kat="%s"><a href="%s">%s</a></li>'
            % (esc((p.get("kategori") or "").strip()),
               esc(ctx["product_url"](p.get("id"))),
               esc(_kart_temizle((p.get("baslik") or "").strip()) or p.get("id")))
            for p in yerel_kalan)
        # Başlık sayısı KENDİ kümesinin kırılımını taşır: kapsam gelince düz bağ listesi
        # süzülüyor ama başlıktaki sayı SSR'de donuyordu (kapsam dışı kalemleri sayan
        # yalan sayı). Artık istemci onu da AYNI `sayimla()` ile düşürür.
        # 🔴 BÖLÜM SARMALANIR (`#mmKalan`): model filtresi etkinken bu bölümün TAMAMI
        # kapanır — düz bağ girdileri sayfanın YEREL kalemleridir, hiçbir modelin üyesi
        # DEĞİLDİR. Sarmalayıcı olmasaydı başlık "… parça listesi (0)" diye ekranda kalırdı.
        kalan_html = ('<div id="mmKalan"><h2 class="mm-sec-h">' + esc(marka)
                      + ' parça listesi ('
                      + _bolum_sayaci(esc, yerel_kalan, "alt") + ')</h2>'
                      + '<ul class="mm-kalan-bag">' + baglar + '</ul></div>')

    kart_html = _urun_grid(ctx, basili, attr_of=_mm_attr, grid_attr=' id="mmGrid"')
    # Artım manifesti. `uc`/`yol`/`parti` = kart verisinin EDGE yolu; TEK KAYNAK
    # index.html'in `EDGE_UC`'si (ctx'e `uret` koyar). Tüm katalog İNDİRİLMEZ.
    # (Yük sayfanın YANINDA duran parcalar.json'dur; HTML baytını şişirmez ve ancak
    # kullanıcı kalanı isteyince çekilir.)
    manifest = {"yuk": "/marka/" + marka_slug + "/parcalar.json", "uc": ctx["EDGE_UC"],
                "yol": EDGE_KATALOG_YOLU, "parti": EDGE_PARTI,
                "site": SITE, "toplam": toplam, "basili": len(basili)}
    artim_html = ""
    if len(basili) < toplam:
        artim_html = (
            '<script type="application/json" id="mmManifest">'
            + json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + '</script>'
            + '<p class="mm-artim"><button type="button" id="mmTumu" class="mm-tumu-btn">'
            # Düğmedeki sayı da KAPSAMA DÜŞER: kapsam kolunda "Tümünü göster (593 parça)"
            # yazarken düğme yalnız kapsam içi kalemleri çiziyordu (yalan sayı).
            + esc("Tümünü göster (") + _bolum_sayaci(esc, kalemler, "erisim")
            + esc(" parça)") + '</button>'
            + '<span id="mmDurum" class="mm-artim-durum"></span></p>')
    filtre_html = ('<p class="mm-filtre-sifirla"><a href="#" id="mmFiltreSifirla">'
                   + esc("Model filtresini temizle") + '</a></p>') if btns else ""

    # Sayfanın YANINDA yazılacak yük (uret yazar). Kalem listesi KANONİK `kalemler`den
    # türer — ikinci bir küme kurulmaz.
    kat_tablosu = sorted(set((p.get("kategori") or "").strip() for p in kalemler))
    kat_ix = {k: i for i, k in enumerate(kat_tablosu)}
    override = {}
    for p in kalemler:
        kayit = _kart_yuk_kaydi(ctx, p)
        if kayit:
            override[p.get("id")] = kayit
    yuk = {
        "toplam": toplam,
        "basili": len(basili),
        "kat": kat_tablosu,
        "m": [g["slug"] for g in buyuk_gruplar],
        "k": [[p.get("id"), kat_ix[(p.get("kategori") or "").strip()],
               model_uyelik.get(p.get("id")) or []] for p in kalemler],
        "o": override,
    }

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
            + _arama_kutusu_html(esc, marka)
            + _kapsam_not_html(esc)
            + _toplam_bloku(esc, kalemler, "Bu markada")
            + ('<h2 class="mm-sec-h">Modele göre seçin (<span class="mm-sayim-model">'
               + str(len(btns)) + '</span>)</h2>' if btns else "")
            + model_html
            + filtre_html
            # 🔴 BAŞLIK SAYISI = ERİŞİLEBİLİR KART YÜZEYİ (`kalemler`), O AN BASILAN
            # (`basili`) DEĞİL. Okan hükmü korunur: sayfa markanın TÜM parçalarını kart
            # olarak gösterir; `MARKA_KART_N` yalnız İLK BOYA kararıdır, VAAT DEĞİL.
            # Vaadi 80'e çekmek yalanı düzeltmek değil vaadi düşürmek olurdu.
            + ('<h2 class="mm-sec-h">' + esc(marka) + ' parçaları ('
               + _bolum_sayaci(esc, kalemler, "erisim") + ')</h2>')
            + kart_html
            + artim_html
            + kalan_html
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
                  kapsam_scripti(kategoriler) + ara_tasi_scripti(marka) + artim_scripti())
    return url, html, yuk, yerel_kalan


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
    # Artım kolunun veri ucu — index.html TEK KAYNAĞINDAN (kopya tutulmaz, fail-closed)
    ctx["EDGE_UC"] = edge_ucu(_index_html)
    # 🔴 SAYFA EVRENİ = ÇİP EVRENİ (tek kaynak). Küratörlük dışı çip markaları (Marin:
    # Teleflex/Sierra/NGK/Tecnoseal/Jabsco/International/3M...) buradan gelir; olmasaydı
    # çipte görünür, sayfası 404 dönerdi.
    ek_markalar = cip_evreni_markalari(products, _index_html)
    veri = gruplandir(products, evren, ek_markalar)

    def yaz(url, html):
        yol = url[len(SITE):].strip("/")          # "marka/ford/focus"
        klasor = os.path.join(ROOT, *yol.split("/"))
        os.makedirs(klasor, exist_ok=True)
        with open(os.path.join(klasor, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    def yaz_json(url, obj):
        """Sayfanın yanındaki istemci verisi (parcalar.json). Deterministik: sort_keys."""
        yol = url[len(SITE):].strip("/")          # "marka/ford/parcalar.json"
        parcalar = yol.split("/")
        klasor = os.path.join(ROOT, *parcalar[:-1])
        os.makedirs(klasor, exist_ok=True)
        with open(os.path.join(klasor, parcalar[-1]), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    # Marka sayfası eşiği: >= ESIK toplam ürünlü kanonik markalar (ince marka sayfası olmasın).
    # Marka toplamı = o markanın SAYFASINDA görünecek ürün sayısı (ikincil ürünler DAHİL) =
    # index.html çip sayımıyla aynı yüklem. Eşik + çip sıralaması bu sayıdan türer.
    marka_toplam = {marka: marka_urun_sayisi(d) for marka, d in veri.items()}
    sayfali_markalar = sorted([m for m, t in marka_toplam.items() if t >= ESIK],
                              key=lambda m: (-marka_toplam[m], m))

    sitemap = []
    sitemap_sayfalari = []

    def sitemap_ekle(sinif, url):
        """Sitemap kaydı + sınıf manifesti; sınıf kanonik değilse fail-closed."""
        if sinif not in SITEMAP_SAYFA_SINIFLARI:
            raise SystemExit("HATA: tanımsız sitemap sayfa sınıfı: %r" % (sinif,))
        priority, changefreq = SITEMAP_SAYFA_SINIFLARI[sinif]
        sitemap.append((url, priority, changefreq))
        sitemap_sayfalari.append((sinif, url))
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

        buyuk = sorted([g for g in gruplar if yayimlanir_mi(g)],
                       key=lambda g: (-len(g["urunler"]), g["slug"]))
        # SAYFASI OLMAYAN kovaların ürünleri marka sayfasında listelenir. TEKİLLEŞTİRİLİR:
        # bir ürün birden çok kovada olabilir (['Opel','Astra','Zafira']); yayımlanan bir
        # kovada zaten görünüyorsa marka sayfasında İKİNCİ kez basılmaz.
        yayimda = set()
        for g in buyuk:
            yayimda.update(p.get("id") for p in g["urunler"] if p.get("id"))
        kucuk_urunler, _gorulen = [], set()
        for g in gruplar:
            if yayimlanir_mi(g):
                continue
            for p in g["urunler"]:
                pid = p.get("id")
                if pid in yayimda or pid in _gorulen:
                    continue
                _gorulen.add(pid)
                kucuk_urunler.append(p)

        murl, mhtml, myuk, yerel_kalan = _marka_sayfasi(
            ctx, marka, d, buyuk, kucuk_urunler, kategoriler)
        yaz(murl, mhtml)
        # Artım yükü sayfanın YANINA yazılır (HTML baytını şişirmez, sitemap'e GİRMEZ:
        # crawl hedefi değil, istemci verisidir). /marka/ gitignore'da -> repoya girmez.
        yaz_json(murl + "parcalar.json", myuk)
        sitemap_ekle("marka", murl)

        # İlk 80 SSR kartın dışında kalan ve yayımlanmış bir model sayfası olmayan ürünler
        # düz bağ olarak marka kökünde kalır. Ayrıca JS'siz/kart-semantikli erişim için tek
        # bir "Diğer" koleksiyonunda tam kartla yayımlanır; böylece artımlı ana sayfanın
        # 80 kart tavanı bozulmadan marka ağacı katalog üyeliğini eksiksiz taşır.
        if yerel_kalan:
            diger = {"display": "Diğer", "slug": "diger", "canon": "diger",
                     "urunler": yerel_kalan}
            durl, dhtml = _model_sayfasi(ctx, marka, diger, kategoriler)
            yaz(durl, dhtml)
            sitemap_ekle("diger", durl)

        marka_yolu = "/marka/" + marka_slug + "/"          # göreli (aynı köken; render_product /?marka= gibi göreli basar)
        for g in buyuk:
            url, html = _model_sayfasi(ctx, marka, g, kategoriler)
            yaz(url, html)
            sitemap_ekle("model", url)
            model_yolu = marka_yolu + g["slug"] + "/"
            for p in g["urunler"]:                          # >=ESIK model -> ürünleri model sayfasına
                pid = p.get("id")
                # 🔴 YALNIZ BİRİNCİL markanın sayfası yazar: ürün artık birden çok markanın
                # model kovasında olabilir; hepsi yazsaydı çipin hedefi döngü sırasına göre
                # değişir (kararsız çıktı) ve ürünün birincil markasından uzaklaşırdı.
                if pid and pid in d["birincil_ids"]:
                    product_chip_map[pid] = model_yolu
        for p in kucuk_urunler:                             # sayfasız model ürünleri -> marka sayfası
            pid = p.get("id")
            if pid and pid in d["birincil_ids"]:
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
    sitemap_ekle("dizin", iurl)

    # 🔴 ALIAS'LI ÇİP HEDEFİ: `MARKA_ALIAS` (Vauxhall -> Opel) bu üreteçte marka sayfalarını
    # BİRLEŞTİRİR ama anasayfa çip evreni (index.html markaKatla) alias TANIMAZ — "Vauxhall"
    # AYRI bir çip olarak doğar. İkisi birleştirilmezse çip görünür, hedefi 404'tür
    # ([[ikiz-tanim-sessiz-ayrisma]]; ölçüldü 3 Ağu: Vauxhall 71 ürünlü çip, sayfa YOK).
    # ÇÖZÜM ikinci sayfa ÜRETMEK DEĞİL (yinelenen içerik) — çipin hedefini alias'ın işaret
    # ettiği SAYFAYA bağlamak. Alias hedefinin sayfası yoksa hiçbir şey yazılmaz (fail-closed:
    # 404 link üretmektense çip buton olarak kalır).
    for _ad, _hedef in MARKA_ALIAS.items():
        if _ad not in slug_map and _hedef in slug_map:
            slug_map[_ad] = slug_map[_hedef]

    # Anasayfa çipleri: JS sortedBrands ile AYNI = TANINMIS + ürün sayısına göre azalan, top MARKA_LIMIT.
    # Yalnız SAYFASI OLAN markalar link olur; sayfası olmayan (çok nadir, <3 ürün) NOT'a düşer.
    chip_sirasi = sorted(marka_toplam.keys(), key=lambda m: (-marka_toplam[m], m))
    chip_markalar = chip_sirasi[:evren.limit]
    chip_links = "".join(_chip_link_html(ctx["esc"], m, slug_map[m])
                         for m in chip_markalar if m in slug_map)
    sayfasiz_cipler = [m for m in chip_markalar if m not in slug_map]

    ctx.setdefault("_mm_sayim", {}).update(sayim)
    sinif_sayilari = {sinif: sum(1 for kayit_sinifi, _url in sitemap_sayfalari
                                 if kayit_sinifi == sinif)
                      for sinif in SITEMAP_SAYFA_SINIFLARI}
    return {
        "sitemap": sitemap,
        "sitemap_sayfalari": sitemap_sayfalari,
        "dizinler": ["marka"],
        "chip_links": chip_links,
        "slug_map": slug_map,
        "product_chip_map": product_chip_map,
        "chip_markalar": chip_markalar,
        "sayfasiz_cipler": sayfasiz_cipler,
        "sayim": sayim,
        "marka_sayfasi_sayisi": sinif_sayilari["marka"],
        # "Diğer" de /marka/<marka>/<koleksiyon>/ biçiminde gerçek bir model-katmanı
        # sayfasıdır; aynı kanonik manifestten sayılır, ayrı elde tutulan +N yoktur.
        "model_sayfasi_sayisi": sinif_sayilari["model"] + sinif_sayilari["diger"],
        "diger_sayfasi_sayisi": sinif_sayilari["diger"],
    }
