#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI — MARKA-MODEL SAYFASI ile ANA SAYFA FİLTRESİ AYNI ÜRÜNLERİ GÖSTERİYOR MU?

  python3 tools/model-uyelik-kapisi.py                 # kabul (sayı basar, eşik uygular)
  python3 tools/model-uyelik-kapisi.py --dokum         # sapan her çifti tek tek listele
  python3 tools/model-uyelik-kapisi.py --kendini-test  # mutasyon bataryası (öldürücü+kontrol)
  python3 tools/model-uyelik-kapisi.py --kok /yol      # BAŞKA ağaçtan oku (mutasyon için)

NE ÖLÇER: her yayımlanan /marka/<marka>/<model>/ sayfası için
    SAYFA  = jeneratörün (tools/marka_model_build.py) o sayfaya koyduğu ürünler
    FİLTRE = index.html'in ?marka=<marka>&model=<display> ile göstereceği ürünler
ve şunu basar:
    CIFT=N TEMIZ=N SAYFA_DAR=N FILTRE_DAR=N ETKILENEN_URUN=N
  SAYFA_DAR  : filtre gösteriyor, sayfada YOK (müşteri sayfada parçayı bulamaz)
  FILTRE_DAR : sayfa gösteriyor, filtre bulamıyor (çipe/deep-link'e tıklayan kaybeder)
  CAPRAZ     : iki yönde birden sapan çift (ayrı sayılır, TEMIZ'e karışmaz)
KABUL EŞİĞİ: SAYFA_DAR=0 · FILTRE_DAR=0 · CAPRAZ=0.

🔴 FİLTRE TARAFI YENİDEN YAZILMAZ: index.html'in GERÇEK kodu (norm + MARKA KÜRATÖRLÜĞÜ +
KANONİK MODEL EŞLEMESİ blokları) AYIKLANIP node ile koşturulur. Python'da bir "filtre portu"
yazsaydık kapı, üretimi değil kendi varsayımını aynalardı — ve iki gövde ayrıştığında yeşil
yanardı ([[ikiz-tanim-sessiz-ayrisma]], [[nobetci-fikstur-sekli]]).

FAIL-CLOSED: node yoksa, blok ayıklanamazsa, katalog boşsa ya da harness çökerse SONUC
OLCULEMEDI (çıkış 2) — "sapma bulamadım" diye YEŞİL denmez.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)


# ---------------------------------------------------------------- yardımcı
def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def _bagimsiz_kanon(s):
    """YANLIŞ-POZİTİF ekseni için BAĞIMSIZ normalleştirme (spec §4.4).

    Bilerek model_kanon'dan FARKLI yazılmıştır: aksan çözümü unicodedata ile yapılır ve
    alfanümerik DIŞI her şey atılır. Amaç, "yeni giren ürün gerçekten o modelin parçası mı"
    sorusunu ölçülen kuralın KENDİSİYLE cevaplamamak — aynı fonksiyon iki tarafta da
    kullanılsaydı iddia totoloji olurdu."""
    t = unicodedata.normalize("NFKD", (s or "").replace("ı", "i").replace("İ", "i").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t)


# ---------------------------------------------------------------- KUŞAK KATLAMASI (4 Ağu)
# BAĞIMSIZ kuşak soneki dilbilgisi — üretimin `kusakSonekMi()`/`KUSAK_DONANIM` tablosu
# ÇAĞRILMAZ, burada ELLE yazılır (aynı fonksiyon iki tarafta kullanılsaydı iddia totoloji
# olurdu, [[beyan-edilmis-survivor]]). Üretim tablosu genişlerse bu eksen KIRMIZI yanar —
# istenen budur: katlamanın kapsamı GÖRÜNÜR karardır (K9/K12 kimlik donması ile aynı ilke).
_BAGIMSIZ_KUSAK_RE = re.compile(
    r"^(mk\d{1,2}|\d{1,2}|i|ii|iii|iv|v|vi|vii|viii|ix|x|[a-z]|gt|gtc|gtd|gti|rs|st)$")
# BAĞIMSIZ DONANIM soneki (KUSAK_DONANIM aynası; üretim tablosu ÇAĞRILMAZ). H3 hükmünün
# DENY kolu bu alt kümedir: `Focus ST` katlanır ve sayfa AÇMAZ, `Corsa D` sayfa ALIR.
_BAGIMSIZ_DONANIM_RE = re.compile(r"^(gt|gtc|gtd|gti|rs|st)$")


def _bagimsiz_donanim_kuyruklu(display):
    """`<taban> <DONANIM>` mi (H3 DENY kolu, kapının kendi dilbilgisi)?"""
    toks = (display or "").split()
    return len(toks) >= 2 and bool(_BAGIMSIZ_DONANIM_RE.match(_bagimsiz_kanon(toks[-1])))


def _bagimsiz_sasi_kodu(display):
    """H1 ŞASİ/MOTOR KODU şekli — TEK jeton + en az bir HARF ve en az bir RAKAM.
    🔴 ÇIPLAK SAYI DIŞARIDA (`86`, `660`, `5`): harf taşımayan jeton False döner."""
    if len((display or "").split()) != 1:
        return False
    j = _bagimsiz_kanon(display)
    return bool(j) and any(c.isalpha() for c in j) and any(c.isdigit() for c in j)


def _bagimsiz_ayri_arac(display):
    """H3 ALLOW kolu — çok jetonlu ve kuyruğu DONANIM DEĞİL (`Corsa D`, `Transporter T5`)."""
    return len((display or "").split()) >= 2 and not _bagimsiz_donanim_kuyruklu(display)


def _bagimsiz_ciplak_sayi(display):
    """Jeton tümüyle SAYISAL mı (`86`, `660`, `5`) — H1'in DIŞINDA kalan sınıf."""
    j = _bagimsiz_kanon(display)
    return bool(j) and j.isdigit()


def _bagimsiz_baslik_yargisi(marka, canon, display, izin_anahtar):
    """Başlık-doğan kova YARGILANMIŞ mı — kapının KENDİ gövdesi (üretim ÇAĞRILMAZ).
    Üç kaynak: envanter · H1 şasi/motor kodu · H3 ayrı araç adı."""
    return ("%s|%s" % (marka, canon) in izin_anahtar
            or _bagimsiz_sasi_kodu(display) or _bagimsiz_ayri_arac(display))

# KATLAMA FİKSTÜRÜ — kural GERÇEK jetonlarla çivilenir (JS ve Python AYNI cevabı vermeli).
# (marka, ham jeton, beklenen taban anahtarı) — taban BOŞ ise "katlanmaz" demektir.
# 🔴 KATLANMAZ satırları ayrı ayrı FARKLI korumayı ölçer:
#   Zafira Life / Megane E-Tech -> GRAMER (kapalı sonek kümesi) — "life"/"etech" sonek değil
#   Ami 6                       -> KUSAK_DISI istisnası (1961 klasik ≠ 2020 dörtteker)
#   Golf / Corsa / Evolution    -> TEK YÖN + KELİME SINIRI (taban varyanta düşmez;
#                                  sınırsız önek eşleşmesi "Golf"u "Gol"+"f" diye katlardı)
# ---------------------------------------------------------------- BAŞLIK KOLU (5 Ağu)
# BAĞIMSIZ başlık dilbilgisi — üretimin `baslikta_tam_kelime()`/`tehlike_jetonu_mu()`
# gövdesi ÇAĞRILMAZ, burada ELLE yazılır. Aynı fonksiyon iki tarafta kullanılsaydı iddia
# totoloji olurdu ([[beyan-edilmis-survivor]]); üretim kuralı gevşerse (tehlike koruması
# düşerse, bitişiklik `markaKatla` ile yazılırsa) bu eksen KIRMIZI yanar.
# Normalleştirme de BİLEREK farklıdır: `_bagimsiz_kanon` ile aynı ailedendir (unicodedata),
# üretim `_norm` tablosunu kullanır.
def _bagimsiz_kelimeler(metin):
    t = unicodedata.normalize("NFKD", (metin or "").replace("ı", "i").replace("İ", "i").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [w for w in re.split(r"[^a-z0-9]+", t) if w]


def _bagimsiz_tehlike(jeton):
    """TEHLİKE sınıfı ölçütü BAĞIMSIZ yazılır: uzunluk <= 3 YA DA tamamen sayısal."""
    j = "".join(_bagimsiz_kelimeler(jeton))
    return (not j) or len(j) <= 3 or j.isdigit()


def _bagimsiz_altdizi(hepsi, parca):
    n, m = len(hepsi), len(parca)
    return m > 0 and m <= n and any(hepsi[i:i + m] == parca for i in range(n - m + 1))


def _bagimsiz_baslik_tasiyor(baslik, marka_adlari, jeton):
    """Başlık, jetonu KABUL EDİLEBİLİR biçimde taşıyor mu (kademeli kural, bağımsız gövde)?
    🔴 BİTİŞİKLİK DÜZ İFADEDİR: `<marka adı> <jeton>` kelime dizisi bitişik geçmeli.
    Marka önekini KATLAYARAK ("Renault Espace" -> Renault) yazan bir üretim mutantı bu
    ölçütü GEÇEMEZ — ayırt edici mutant M4'ün dayanağı budur."""
    bw = _bagimsiz_kelimeler(baslik)
    jw = _bagimsiz_kelimeler(jeton)
    if not bw or not jw:
        return False
    if not _bagimsiz_tehlike(jeton):
        return _bagimsiz_altdizi(bw, jw)
    for ad in marka_adlari:
        aw = _bagimsiz_kelimeler(ad)
        if aw and _bagimsiz_altdizi(bw, aw + jw):
            return True
    return False


KATLAMA_FIKSTURU = [
    ("Volkswagen", "Golf 4", "golf"),
    ("Volkswagen", "Golf Mk4", "golf"),
    ("Volkswagen", "Golf IV", "golf"),
    ("Volkswagen", "Golf R", "golf"),
    ("Opel", "Astra H", "astra"),
    ("Opel", "Corsa C", "corsa"),
    ("Renault", "Megane II", "megane"),
    ("Ford", "Fiesta ST", "fiesta"),
    ("Peugeot", "206 GTI", "206"),
    ("Opel", "Zafira Life", ""),
    ("Renault", "Megane E-Tech", ""),
    ("Citroen", "Ami 6", ""),
    ("Volkswagen", "Golf", ""),
    ("Opel", "Corsa", ""),
    ("Mitsubishi", "Evolution", ""),
    # KÜRATÖRLÜ KUŞAK EŞLEMESİ (gramerin göremediği bağ; kuşak etiketi ÇIPLAK jeton)
    ("Volkswagen", "T4", "transporter"),
    ("Volkswagen", "T6.1", "transporter"),
    ("Volkswagen", "Transporter T5", "transporter"),
    # 🔴 MARKA-ÖZEL: Mercedes T1 (Bremer) AYRI ARAÇTIR — VW T1'e katlanmaz.
    ("Mercedes", "T1", ""),
    ("Volkswagen", "Transporter", ""),      # taban jeton kuşağa DÜŞMEZ (tek yön)
]


# ---------------------------------------------------------------- ÇIPLAK TEK HARF (SINIF 1)
# KARARSIZ JETON SINIF 1 — mimar hükmü: "ÇIPLAK TEK HARF model adı OLMAZ; o ailenin kanonik
# adı TAM YAZIMDIR (`R Serisi` / `K Serisi`)". Ölçüldü (4 Ağu, 17.962 ürün): BMW altında
# `K` (1 ürün) ve `K Serisi` (1 ürün) AYRI kovalardı — aynı aile iki öksüz kovaya bölünmüş,
# `K` kovası ESIK'i geçtiği gün /marka/bmw/k/ TEK HARFLİ sayfası sessizce doğacaktı.
#
# 🔴 FİKSTÜR: (marka, çıplak jeton, tam yazım, beklenen anahtar, beklenen GÖRÜNEN ad).
# KATLAMA_FIKSTURU ile AYNI disiplin: kural GERÇEK jetonlarla çivilenir ve İKİ TARAFTA
# (JS gövdesi + Python portu) ayrı ayrı ölçülür.
# 🔴 KONTROL SATIRLARI (`birlesir=False`) AYNI fikstürde durur — kural marka-KÖR yazılsaydı
# `Opel Astra K` (12 ürün, CANLI sayfa) ve `Renault 5` (11 ürün, RAKAM = gerçek model) ölürdü.
# Ölçüldü; bu yüzden kontrol satırları iddianın PARÇASIDIR, ayrı bir "not" değil.
TEK_HARF_FIKSTURU = [
    # (marka, ham jeton, beklenen anahtar, beklenen görünen ad, çıplak-tek-harf mi)
    ("BMW", "K", "kserisi", "K Serisi", True),
    ("BMW", "K Serisi", "kserisi", "K Serisi", False),
    # KONTROL: tek KARAKTER ama RAKAM — Renault 5 gerçek bir modeldir, birleşmez/ölmez.
    ("Renault", "5", "5", "5", False),
    # KONTROL: son kelimesi tek harf olan BİLEŞİK model adı — kuşak sayfası, dokunulmaz.
    ("Opel", "Astra K", "astrak", "Astra K", False),
]


def _kusak_tasiyor(jetonlar, hedef):
    """Ürünün jetonlarından biri, hedef modelin BİR KUŞAĞI mı (bağımsız ölçüt)?
    'astrah' -> hedef 'astra' + sonek 'h' ✔ · 'golfmk4' -> 'golf'+'mk4' ✔ ·
    'zafiralife' -> sonek 'life' dilbilgisinde YOK ✘."""
    if not hedef:
        return False
    for j in jetonlar:
        ix = j.rfind(hedef)
        if ix < 0:
            continue
        if _BAGIMSIZ_KUSAK_RE.match(j[ix + len(hedef):]):
            return True
    return False


# ---------------------------------------------------------------- node koşumu (FİLTRE tarafı)
HARNESS = r"""
"use strict";
/* index.html'den AYIKLANMIS GERCEK kod (kopya DEGIL) */
__NORM__
__KURATORLUK__
__MODEL_KANON__

const girdi = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
const urunler = girdi.urunler;          // [{i, m:[ham marka...]}]
const ciftler = girdi.ciftler;          // [[marka, display], ...]
const sondalar = girdi.sondalar || [];  // [[marka, deger], ...] — anahtar SONDASI
const kusaklar = girdi.kusaklar || [];  // [[marka, deger], ...] — KUSAK KATLAMA SONDASI
const birlesmeler = girdi.birlesmeler || []; // [[marka, ciplak jeton], ...] — ALIAS BIRLESMESI

/* marka -> o markanin UYESI urun indeksleri (filtered() brandOk yuklemi) */
const markaIx = new Map();
for (const u of urunler) {
  const gorulen = new Set();
  for (const b of u.m) {
    const k = markaKatla(b);
    if (gorulen.has(k)) { continue; }
    gorulen.add(k);
    if (!markaIx.has(k)) { markaIx.set(k, []); }
    markaIx.get(k).push(u);
  }
}

const cikti = {};
for (const [marka, display] of ciftler) {
  const liste = markaIx.get(marka) || [];
  const ids = [];
  for (const u of liste) {
    /* filtered() model yuklemi — GERCEK modelEsler cagrilir */
    if (modelEsler(u.m, display, marka)) { ids.push(u.i); }
  }
  cikti[marka + "\t" + display] = ids;
}
/* ANAHTAR SONDASI: Python portu ile JS'in AYNI anahtari uretip uretmedigi dogrudan olculur.
   Bu eksen olmadan, iki taraftaki bilesik-marka korumasi hicbir mutantla TEK BASINA
   kirmizi yakilamiyordu (olculdu 3 Agu) -> beyan edilmis survivor. */
const sonda = {};
for (const [marka, deger] of sondalar) { sonda[marka + "\t" + deger] = modelAnahtar(marka, deger); }
/* KUSAK SONDASI: kusakTabanlari() JS gövdesi ile Python portu AYNI okumayi mi uretiyor?
   Bu eksen olmadan tek-tarafli katlama mutantlari (yalniz Python tablo okumayi birakir)
   ancak paritede gorunurdu; gramer/istisna ayrismasi ise SESSIZ kalirdi. */
const kusak = {};
for (const [marka, deger] of kusaklar) { kusak[marka + "\t" + deger] = kusakTabanlari(marka, deger); }
/* BIRLESME SONDASI: ciplak tek harf jeton ("K") ile tam yazim ("K Serisi") AYNI anahtara mi
   dusuyor? Iki taraf (JS govdesi + Python portu) AYRI olculur — tek taraf alias'i okumayi
   birakirsa kova sessizce IKIYE bolunur ve TEK HARFLI bir sayfa dogar. */
const birlesme = {};
for (const [marka, deger] of birlesmeler) { birlesme[marka + "\t" + deger] = modelAnahtar(marka, deger); }
process.stdout.write(JSON.stringify({ok: true, sonuc: cikti, sonda: sonda, kusak: kusak,
  birlesme: birlesme,
  anahtarOrnek: {f150: modelAnahtar("Ford", "F150"), fSerisi: modelAnahtar("Ford", "F-Series")}}));
"""


class Olculemedi(Exception):
    pass


def _blok_ayikla(index_html):
    """index.html'den GERÇEK JS parçaları (fail-closed)."""
    m = re.search(r"function norm\(s\)\{[\s\S]*?\n  \}", index_html)
    if not m:
        raise Olculemedi("index.html norm() ayıklanamadı")
    norm_src = m.group(0)

    def arasi(bas, son, ad):
        b, s = index_html.find(bas), index_html.find(son)
        if b == -1 or s == -1 or s <= b:
            raise Olculemedi("index.html %s bloğu ayıklanamadı (marker yok/taşınmış)" % ad)
        return index_html[index_html.index("\n", b) + 1:s]

    kurator = arasi("// --- MARKA KÜRATÖRLÜĞÜ BAŞ", "// --- MARKA KÜRATÖRLÜĞÜ SON ---",
                    "MARKA KÜRATÖRLÜĞÜ")
    kanon = arasi("// --- KANONİK MODEL EŞLEMESİ BAŞ", "// --- KANONİK MODEL EŞLEMESİ SON ---",
                  "KANONİK MODEL EŞLEMESİ")
    for imza in ("function modelKanon", "function modelOnekSiyir", "function modelAnahtar",
                 "function modelEsler", "MODEL_ALIAS",
                 "function kusakTabanlari", "function kusakSonekMi",
                 "KUSAK_DONANIM", "KUSAK_DISI"):
        if imza not in kanon:
            raise Olculemedi("KANONİK MODEL EŞLEMESİ bloğunda %s YOK" % imza)
    if "MARKA_ALIAS" not in kurator:
        raise Olculemedi("MARKA KÜRATÖRLÜĞÜ bloğunda MARKA_ALIAS YOK")
    return norm_src, kurator, kanon


def filtre_kumeleri(index_html, urunler, ciftler, sondalar=(), kusaklar=(), birlesmeler=()):
    """{(marka, display): set(urun_id)} — index.html'in GERÇEK yüklemiyle (node)."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        raise Olculemedi("node bulunamadı — filtre tarafı GERÇEK kodla koşturulamaz "
                         "(Python portu yazmak kapıyı totolojiye çevirirdi)")
    norm_src, kurator, kanon = _blok_ayikla(index_html)
    js = (HARNESS.replace("__NORM__", norm_src)
                 .replace("__KURATORLUK__", kurator)
                 .replace("__MODEL_KANON__", kanon))
    tmp = tempfile.mkdtemp(prefix="model-uyelik-node-")
    try:
        jsyol = os.path.join(tmp, "kosum.js")
        veriyol = os.path.join(tmp, "girdi.json")
        with open(jsyol, "w", encoding="utf-8") as f:
            f.write(js)
        with open(veriyol, "w", encoding="utf-8") as f:
            json.dump({"urunler": [{"i": p.get("id"),
                                    "m": [(x or "").strip()
                                          for x in (p.get("marka") or []) if (x or "").strip()]}
                                   for p in urunler if p.get("id")],
                       "ciftler": [[a, b] for a, b in ciftler],
                       "sondalar": [[a, b] for a, b in sondalar],
                       "kusaklar": [[a, b] for a, b in kusaklar],
                       "birlesmeler": [[a, b] for a, b in birlesmeler]}, f, ensure_ascii=False)
        p = subprocess.run(["node", jsyol, veriyol], capture_output=True, text=True, timeout=900)
        if p.returncode != 0 or not (p.stdout or "").strip():
            raise Olculemedi("node koşumu çöktü (rc=%d): %s"
                             % (p.returncode, ((p.stderr or "").strip().splitlines() or [""])[-1][:200]))
        veri = json.loads(p.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not veri.get("ok"):
        raise Olculemedi("node koşumu ok=false döndü")
    return (dict(((k.split("\t")[0], k.split("\t")[1]), set(v))
                 for k, v in veri["sonuc"].items()),
            veri.get("anahtarOrnek", {}),
            dict((tuple(k.split("\t")), v) for k, v in (veri.get("sonda") or {}).items()),
            dict((tuple(k.split("\t")), [tuple(x) for x in (v or [])])
                 for k, v in (veri.get("kusak") or {}).items()),
            dict((tuple(k.split("\t")), v) for k, v in (veri.get("birlesme") or {}).items()))


# ---------------------------------------------------------------- ölçüm
def olc(kok, modul_yolu=None):
    """(satir, ayrinti) — hüküm VERMEZ, sayı üretir."""
    araclar = os.path.join(kok, "tools")
    if araclar not in sys.path:
        sys.path.insert(0, araclar)
    mm = _modul(modul_yolu or os.path.join(araclar, "marka_model_build.py"), "mm_model_kapisi")
    try:
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("katalog/index.html okunamadı: %r" % (e,))
    if not urunler:
        raise Olculemedi("urunler.json BOŞ — üyelik ölçülemez")

    try:
        evren = mm.MarkaEvreni(index_html)
        ek = mm.cip_evreni_markalari(urunler, index_html)
        veri = mm.gruplandir(urunler, evren, ek)
    except SystemExit as e:                                       # noqa: BLE001
        raise Olculemedi("jeneratör fail-closed durdu: %r" % (e,))
    if not veri:
        raise Olculemedi("jeneratör HİÇ marka kovası üretmedi")

    # yayımlanan çiftler (üreticinin TEK KAYNAK yüklemi)
    yayimla = getattr(mm, "yayimlanir_mi", None)
    if yayimla is None:
        raise Olculemedi("jeneratörde yayimlanir_mi() YOK — sayfa evreni ölçülemez")
    ciftler, sayfa = [], {}
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            if not yayimla(g):
                continue
            ciftler.append((marka, g["display"]))
            sayfa[(marka, g["display"])] = (
                set(p.get("id") for p in g["urunler"] if p.get("id")), g["canon"])
    if not ciftler:
        raise Olculemedi("yayımlanan model sayfası YOK — parite ölçülemez (fail-closed)")

    # ANAHTAR SONDALARI — bileşik marka adının anahtarı İKİ TARAFTA da BÖLÜNMEMİŞ olmalı.
    # Sonda listesi UYDURULMAZ: aynadan (index.html BILESIK_MARKA) türer ve yalnız TANINMIŞ
    # marka önekiyle başlayan üyeler alınır (bölünme riski GERÇEKTEN olanlar).
    sondalar = []
    for _ad in getattr(evren, "bilesik", []):
        _toks = _ad.split()
        for _k in range(len(_toks) - 1, 0, -1):
            _onek = " ".join(_toks[:_k])
            if evren.taninmis_mi(_onek):
                sondalar.append((evren.katla(_onek), _ad))
                break

    # KUŞAK SONDALARI — fikstür + KATALOGDAKİ tüm ÇOK KELİMELİ model jetonları. Fikstür
    # kuralı çiviler, katalog süpürmesi JS↔Python ayrışmasını GERÇEK veride arar (uydurma
    # jeton listesi değil: sondanın kaynağı katalogun kendisidir).
    # (Üyelik ikinci kez HESAPLANMAZ: jeneratörün kendi kovalarından okunur — kapının
    #  kendi marka evrenini kurması hem yavaş hem de ikinci tanım olurdu.)
    kusak_sondalar = [(mk, dg) for mk, dg, _b in KATLAMA_FIKSTURU]
    _gorulen_sonda = set(kusak_sondalar)
    for _kan, _d in veri.items():
        _liste = [_d["marka_only"], _d.get("ikincil", [])] + \
                 [_g["urunler"] for _g in _d["gruplar"].values()]
        for _kaynak in _liste:
            for p in _kaynak:
                for _t in (p.get("marka") or []):
                    _t = (_t or "").strip()
                    if len(_t.split()) < 2 or (_kan, _t) in _gorulen_sonda:
                        continue
                    _gorulen_sonda.add((_kan, _t))
                    kusak_sondalar.append((_kan, _t))

    birlesme_sondalar = [(mk, jt) for mk, jt, _a, _d, _b in TEK_HARF_FIKSTURU]
    filtre, ornek, sonda, kusak_js, birlesme_js = filtre_kumeleri(
        index_html, urunler, ciftler, sondalar, kusak_sondalar, birlesme_sondalar)

    # JS ↔ Python kuşak okuması BİREBİR mi (gramer + istisna + kelime sınırı)?
    kusak_sapan = []
    for cift in kusak_sondalar:
        js = [tuple(x) for x in (kusak_js.get(cift) or [])]
        py = [tuple(x) for x in evren.kusak_tabanlari(cift[0], cift[1])]
        if js != py:
            kusak_sapan.append((cift[0], cift[1], "js=%s" % (js,), "py=%s" % (py,)))

    # FİKSTÜR — kural GERÇEK jetonla çivili mi (İKİ tarafta da)?
    fikstur_sapan = []
    for mk, dg, beklenen in KATLAMA_FIKSTURU:
        for taraf, okuma in (("js", [tuple(x) for x in (kusak_js.get((mk, dg)) or [])]),
                             ("py", [tuple(x) for x in evren.kusak_tabanlari(mk, dg)])):
            tabanlar = [t for t, _e in okuma]
            if beklenen:
                ok = beklenen in tabanlar
            else:
                ok = not tabanlar
            if not ok:
                fikstur_sapan.append((taraf, mk, dg, "beklenen=%s" % (beklenen or "KATLANMAZ"),
                                      "gercek=%s" % (tabanlar or "-",)))

    urun_ix = dict((p["id"], p) for p in urunler if p.get("id"))

    # --- BAŞLIK KOLU AÇIKLAMASI (5 Ağu) — BAĞIMSIZ gövdeyle ölçülür.
    # Model sayfası artık üyeliği `marka[]` ∪ `uyum[].model` ∪ BAŞLIKTA TAM KELİME'den
    # alıyor; index.html'in `?marka=&model=` filtresi ise (bugün) yalnız `marka[]`ye bakıyor.
    # Bu YAPISAL bir fark: bu koldan gelen üyeliği filtre GÖREMEZ.
    # 🔴 KAPI GEVŞEMEZ, EKSEN DEĞİŞİR: "FILTRE_DAR=0" yerine "AÇIKLANAMAYAN FILTRE_DAR=0"
    # ölçülür. Sayı-tabanı yazsaydık (FILTRE_DAR<=N) katalog büyüdükçe taban bayatlar,
    # yeni bir GERÇEK ayrışma da tabanın altında saklanırdı ([[hukum-yanlis-birimde]]).
    # Ölçüt bağımsızdır: üretimin başlık gövdesi çağrılmaz, kapı kendi dilbilgisini koşar.
    # 🟡 AÇIK BORÇ (ADIM 2): üçüncü yüzey (index.html filtresi + uç `?model=`) bu yüklemi
    # HENÜZ almadı; kapı farkı SAYIYLA raporlar, sıfır saymaz.
    def _marka_adlari(mk):
        adlar = {mk}
        for x in getattr(evren, "taninmis", ()):
            if evren.marka_alias.get(x, x) == mk:
                adlar.add(x)
        return sorted(adlar)

    _ad_bellek = {}
    _yazim_bellek = {}
    for _mk, _d in veri.items():
        for _canon, _g in _d["gruplar"].items():
            _yz = set(x for x in (_d["_spelling"].get(_canon) or ()) if x)
            _yz.add(_g.get("display") or _canon)
            _yazim_bellek[(_mk, _canon)] = sorted(_yz)

    def _baslik_aciklar(pid, mk, canon):
        """Ürünün o kovadaki üyeliği BAŞLIK KOLUYLA açıklanıyor mu (bağımsız ölçüt)?"""
        p = urun_ix.get(pid) or {}
        baslik = p.get("baslik") or ""
        if not baslik:
            return False
        adlar = _ad_bellek.get(mk)
        if adlar is None:
            adlar = _ad_bellek[mk] = _marka_adlari(mk)
        return any(_bagimsiz_baslik_tasiyor(baslik, adlar, y)
                   for y in _yazim_bellek.get((mk, canon), ()))

    temiz = sayfa_dar = filtre_dar = capraz = 0
    etkilenen = set()
    dokum = []
    baslik_aciklanan = 0
    baslik_aciklanamayan = []
    for cift in ciftler:
        s, canon = sayfa[cift]
        f = filtre.get(cift, set())
        eksik_sayfada, eksik_filtrede = f - s, s - f
        # BAŞLIK KOLUYLA AÇIKLANAN üyelik parite farkından DÜŞÜLÜR (açıklanamayan kalır).
        if eksik_filtrede:
            _aciklanan = set(pid for pid in eksik_filtrede
                             if _baslik_aciklar(pid, cift[0], canon))
            baslik_aciklanan += len(_aciklanan)
            for pid in sorted(eksik_filtrede - _aciklanan):
                baslik_aciklanamayan.append((cift[0], cift[1], pid))
            eksik_filtrede = eksik_filtrede - _aciklanan
        if not eksik_sayfada and not eksik_filtrede:
            temiz += 1
            continue
        etkilenen |= eksik_sayfada | eksik_filtrede
        if eksik_sayfada and eksik_filtrede:
            capraz += 1
            tur = "CAPRAZ"
        elif eksik_sayfada:
            sayfa_dar += 1
            tur = "SAYFA_DAR"
        else:
            filtre_dar += 1
            tur = "FILTRE_DAR"
        dokum.append({"tur": tur, "marka": cift[0], "model": cift[1], "canon": canon,
                      "sayfa": len(s), "filtre": len(f),
                      "sayfada_yok": sorted(eksik_sayfada)[:5],
                      "filtrede_yok": sorted(eksik_filtrede)[:5]})

    # --- YANLIŞ-POZİTİF EKSENİ (spec §4.4): sayfaya giren HER ürün o modeli GERÇEKTEN taşıyor mu?
    # Kural: ürünün `marka` dizisinde ya da `uyum[].model`'inde, sayfanın adıyla BAĞIMSIZ
    # normalleştirme altında eşleşen bir jeton bulunmalı. Eşleşmeyen tek istisna sınıfı,
    # KÜRATÖRLÜ semantik alias'tır (MODEL_ALIAS: "F-Series" = "F-Serisi") — o da sessizce
    # muaf tutulmaz, alias KAYNAĞINDAN türetilir ve raporda AYRI listelenir.
    alias_kaynaklari = {}
    for (mk, kaynak), hedef_canon in (evren.model_alias or {}).items():
        alias_kaynaklari.setdefault((mk, hedef_canon), set()).add(kaynak)
    sahte, alias_aciklamali = [], []
    kusak_aciklamali, esleme_aciklamali, baslik_aciklamali = [], [], []
    # KÜRATÖRLÜ KUŞAK EŞLEMESİ ile açıklanan üyelik (MODEL_ALIAS ile AYNI muamele): `T4`
    # jetonu `Transporter` metnini İÇERMEZ, dolayısıyla hiçbir bağımsız dilbilgisi bu
    # üyeliği türetemez — türetebilseydi zaten küratörlü tabloya gerek olmazdı. Bu yüzden
    # muafiyet listesi DEĞİL, tablonun KAYNAĞINDAN türetilir ve raporda AYRI listelenir;
    # tablonun kimliği/etkisi K18'de ayrıca ölçülür (sessiz genişleme KIRMIZI).
    esleme_kaynaklari = {}
    for _kayit in getattr(evren, "kusak_esleme", []):
        _p = _kayit.split("|")
        if len(_p) == 3:
            esleme_kaynaklari.setdefault(
                (_p[0], evren.model_anahtari(_p[0], _p[2])), set()).add(_p[1])

    def _tasiyor(jetonlar, hedef):
        # marka öneki taşıyan yazım da sayılır ("peugeot206" -> "206")
        return bool(hedef) and (hedef in jetonlar
                                or any(j.endswith(hedef) and j != hedef for j in jetonlar))

    for (marka, display), (ids, canon) in sayfa.items():
        hedef = _bagimsiz_kanon(display)
        aliaslar = alias_kaynaklari.get((marka, canon), set())
        for pid in ids:
            p = urun_ix.get(pid) or {}
            jetonlar = set(_bagimsiz_kanon(x) for x in (p.get("marka") or []) if x)
            jetonlar |= set(_bagimsiz_kanon(o.get("model"))
                            for o in (p.get("uyum") or []) if (o.get("model") or "").strip())
            if _tasiyor(jetonlar, hedef):
                continue
            if any(_tasiyor(jetonlar, _bagimsiz_kanon(a)) for a in aliaslar):
                alias_aciklamali.append((marka, display, pid, sorted(aliaslar)))
                continue
            # KUŞAK KATLAMASI ile açıklanan üyelik: ürün modelin bir KUŞAĞINI taşıyor
            # ("Astra H" -> Astra). Muafiyet DEĞİL: ölçüt BAĞIMSIZ dilbilgisiyle kurulur
            # (üretimin tablosu çağrılmaz) ve bu ürünlerin sayfada AYRI bölümde durduğu
            # K14'te ayrıca ölçülür — "katlandı ama ana listeye karıştı" yeşil geçemez.
            if _kusak_tasiyor(jetonlar, hedef):
                kusak_aciklamali.append((marka, display, pid))
                continue
            _kaynaklar = esleme_kaynaklari.get((marka, canon), set())
            if any(_tasiyor(jetonlar, _bagimsiz_kanon(k)) for k in _kaynaklar):
                esleme_aciklamali.append((marka, display, pid, sorted(_kaynaklar)))
                continue
            # BAŞLIK KOLU ile açıklanan üyelik (5 Ağu): ürünün `marka[]`/`uyum[]` alanında
            # jeton YOK ama BAŞLIĞINDA model adı TAM KELİME geçiyor. Muafiyet DEĞİL: ölçüt
            # kapının KENDİ bağımsız dilbilgisiyle kurulur (üretim gövdesi çağrılmaz), yani
            # tehlike korumasını düşüren ya da bitişikliği `markaKatla` ile yazan bir mutant
            # bu eksende YANLIŞ-POZİTİF üretir ve KIRMIZI yakar.
            if _baslik_aciklar(pid, marka, canon):
                baslik_aciklamali.append((marka, display, pid))
                continue
            sahte.append((marka, display, pid, sorted(jetonlar)[:4]))

    # --- BİLEŞİK MARKA / MARKA-JETONU EKSENİ (3 Ağu, KraL denetimi) --------------------
    # Ölçüt BAĞIMSIZ: yargı doğrudan tools/arama.py'nin KAPALI MARKA KÜMESİ'nden okunur,
    # üretecin `marka_jetonu_mu()` fonksiyonu ÇAĞRILMAZ — çağırsaydık kuralı bozan mutant
    # iddiayı da kendi lehine büker ve kapı totolojiye düşerdi.
    try:
        araclar_yolu = os.path.join(kok, "tools")
        if araclar_yolu not in sys.path:
            sys.path.insert(0, araclar_yolu)
        import arama as _arama                                      # noqa: PLC0415
        _mk_kanon = __import__("model_kanon").kanon
        kapali = set(_arama.UYUM_MARKA_IZINLI) | set(_arama.URETICI_MARKA)
        model_olmayan = dict(_arama.MODEL_OLMAYAN_JETON)
        kapali_n = set(_arama.model_normalize(m) for m in kapali)
        olmayan_n = set(_arama.model_normalize(m) for m in model_olmayan)
        cok_kelimeli = sorted(m for m in kapali if len(m.split()) > 1)
        red_imza = (_arama.model_olmayan_imzasi(), _arama.MODEL_OLMAYAN_IMZA,
                    len(model_olmayan), _arama.MODEL_OLMAYAN_SAYISI)
    except Exception as e:                                          # noqa: BLE001
        raise Olculemedi("tools/arama.py marka kümeleri okunamadı: %r" % (e,))

    # (a) MARKA JETONU SAYFA OLMAMALI — bir MARKA'yı MODEL diye sunan kova YOK.
    marka_kovasi = []
    for (marka, display), (_ids, canon) in sayfa.items():
        n = _arama.model_normalize(display)
        if n in kapali_n or n in olmayan_n:
            marka_kovasi.append((marka, display,
                                 model_olmayan.get(display, "KAPALI MARKA KÜMESİ üyesi")))

    # (a2) ROZET KAPISI (4 Ağu, KraL hükmü): rozet dışı (marka, model) çifti SAYFA OLMAZ.
    #      Yargı yine BAĞIMSIZ okunur (arama.ROZET_DISI_CIFT), üretecin yüklemi çağrılmaz.
    #      Ayrıca ELENEN kovanın ürünleri KAYBOLMAMALI: marka ağacında (başka bir yayımlanan
    #      kovada ya da marka sayfasının listesinde) durmalı — "sayfa kapattık, ürün gitti"
    #      sessiz hatası bu eksende ölçülür.
    rozet_disi = dict(((mk, _mk_kanon(md)), (mk, md, sebep))
                      for (mk, md), sebep in _arama.ROZET_DISI_CIFT.items())
    rozet_imza = (_arama.rozet_disi_imzasi(), _arama.ROZET_DISI_IMZA,
                  len(_arama.ROZET_DISI_CIFT), _arama.ROZET_DISI_SAYISI)
    rozet_ihlal = [(mk, dsp) for (mk, dsp), (_i, canon) in sayfa.items()
                   if (mk, canon) in rozet_disi]
    # elenen kovalar + ürünlerin nereye düştüğü
    yayin_id = set()
    for (_mk, _dsp), (_ids, _c) in sayfa.items():
        yayin_id |= _ids
    rozet_elenen, rozet_kaybolan = [], []
    for (mk, canon), (_ham_mk, ham_md, sebep) in rozet_disi.items():
        g = (veri.get(mk) or {}).get("gruplar", {}).get(canon)
        if not g:
            continue
        ids = set(p.get("id") for p in g["urunler"] if p.get("id"))
        # marka AĞACINDA duruyor mu: ya başka bir yayımlanan kovada ya da marka sayfasının
        # listesinde (yayımlanmayan kova ürünleri uret() tarafından oraya basılır).
        marka_agaci = set()
        for g2 in (veri.get(mk) or {}).get("gruplar", {}).values():
            marka_agaci |= set(p.get("id") for p in g2["urunler"] if p.get("id"))
        marka_agaci |= set(p.get("id") for p in
                           (veri.get(mk) or {}).get("marka_only", [])
                           + (veri.get(mk) or {}).get("ikincil", []) if p.get("id"))
        kaybolan = sorted(pid for pid in ids if pid not in marka_agaci)
        rozet_kaybolan.extend(kaybolan)
        rozet_elenen.append({
            "url": "/marka/%s/%s/" % (mm._slug(mk), mm._slug(g.get("display") or ham_md)),
            "n": len(ids), "sebep": sebep,
            "gercek_sayfada": sum(1 for pid in ids if pid in yayin_id),
            "kaybolan": len(kaybolan)})

    # (a3) ÇAPRAZ-MARKA (ROZET) TUTARLILIK KAPISI — K19 (4 Ağu, mimar hükmü)
    #      ÖLÇÜLEN SINIF: `ROZET_DISI_CIFT` bugüne kadar ELLE bulunmuş örnekleri tutuyordu;
    #      yeni bir rozet ihlali ancak biri CANLIDA görünce yakalanıyordu. Ölçüldü: 17.914
    #      üründe `(Peugeot, Berlingo)` 9 ürünle, `(Peugeot, DS)` 3 ürünle YAYINDAYDI;
    #      `(Opel, Berlingo)` 3 ürünle eşiğin DİBİNDE bekliyordu (veri partisi yazılınca
    #      sessizce doğacaktı).
    #      YÜKLEM (İLERİYE DÖNÜK): aynı KANONİK model anahtarı İKİ ya da daha çok markada
    #      sayfa eşiğini geçiyorsa, o (marka, canon) çifti ya ROZET_DISI_CIFT'te (deny) ya
    #      ROZET_CAPRAZ_IZINLI'de (allow) olmalı. İkisinde de yoksa KIRMIZI — karar istenir.
    #      🔴 BİRİM KÜME (sayı DEĞİL): bir çift ölüp biri doğunca sayı sabit kalır ve sapma
    #      gizlenirdi ([[hukum-yanlis-birimde]]) — K16 ile aynı disiplin.
    #      🔴 EŞİK ÖLÇÜTÜ "sayfa doğuracak mı" olmalı, "sayfa doğdu mu" DEĞİL: deny'e alınan
    #      çift yayından düşer, ölçüt yayına baksaydı tablo KENDİ kanıtını siler (totoloji).
    #      🟡 BAŞLIK YARGISI ÖLÇÜTE DAHİLDİR (5 Ağu): "yalnız başlık kolu sayesinde eşiği
    #      geçen ama BASLIK_DOGAN_ALLOW'a girmemiş" kova bir SAYFA ADAYI DEĞİLDİR — o kova
    #      zaten yargı bekliyor ve mimarın önüne TEK karar olarak gidiyor. Ölçüte alınsaydı
    #      aynı bekleyen karar İKİ ayrı tabloda ayrı ayrı yazılmak zorunda kalırdı.
    #      🔴 ROZET DENY'i ÖLÇÜTTEN DÜŞMEZ (M28 totoloji koruması aynen durur).
    capraz_aday = {}
    for _mk, _d in veri.items():
        for _canon, _g in _d["gruplar"].items():
            if _g.get("baslik_dogan") and (_mk, _canon) not in mm.BASLIK_DOGAN_ALLOW:
                continue
            if _g.get("birincil") and len(_g["urunler"]) >= mm.ESIK:
                capraz_aday.setdefault(_canon, []).append((_mk, _g.get("display") or _canon,
                                                           len(_g["urunler"])))
    capraz_cift = set()
    for _canon, _lst in capraz_aday.items():
        if len(_lst) >= 2:
            for _mk, _dsp, _n in _lst:
                capraz_cift.add("%s|%s" % (_mk, _canon))
    try:
        _izin = dict(_arama.ROZET_CAPRAZ_IZINLI)
        capraz_imza = (_arama.rozet_capraz_imzasi(), _arama.ROZET_CAPRAZ_IZINLI_IMZA,
                       len(_izin), _arama.ROZET_CAPRAZ_IZINLI_SAYISI)
    except Exception as e:                                          # noqa: BLE001
        raise Olculemedi("tools/arama.py ROZET_CAPRAZ_IZINLI okunamadı: %r" % (e,))
    _deny_anahtar = set("%s|%s" % (mk, canon) for (mk, canon) in rozet_disi)
    # (1) YARGISIZ ÇİFT = SIZINTI: ne deny'de ne allow'da -> sessiz sayfa doğuyor.
    capraz_yargisiz = sorted(capraz_cift - set(_izin) - _deny_anahtar)
    # (2) ENVANTER BAYAT: allow'da duran ama artık ÇAPRAZ OLMAYAN kayıt (küme birebir).
    capraz_bayat = sorted(set(_izin) - capraz_cift)
    # (3) ÇELİŞKİ: aynı çift hem deny hem allow -> hangi hüküm geçerli belirsiz.
    capraz_celiski = sorted(set(_izin) & _deny_anahtar)
    # (4) BEKLEYEN HÜKÜM: allow'da "BEKLER" sınıfı — hata DEĞİL, GÖRÜNÜR rapor kalemi.
    capraz_bekler = sorted(k for k, v in _izin.items() if v[0] == "BEKLER")
    capraz_ozet = []
    for _canon in sorted(capraz_aday):
        _lst = capraz_aday[_canon]
        if len(_lst) < 2:
            continue
        capraz_ozet.append((_canon, sorted(_lst, key=lambda t: -t[2])))

    # (b) AYNA DRIFT — index.html BILESIK_MARKA == arama.py'nin ÇOK KELİMELİ üyeleri.
    #     Otorite arama.py; index.html yalnızca JS'in çalışma anı kopyasıdır.
    ayna = list(getattr(evren, "bilesik", []))
    ayna_fark = (sorted(set(cok_kelimeli) - set(ayna)), sorted(set(ayna) - set(cok_kelimeli)))

    # (c) ANAHTAR SONDASI — bileşik marka adı İKİ TARAFTA da BÖLÜNMEMİŞ anahtar üretmeli.
    #     Bu eksen olmadan iki taraftaki koruma katmanı TEK BAŞINA kırmızı yakılamıyordu
    #     (ölçüldü: kapalı-küme kuralı sayfa evrenini zaten kalkanlıyor) — [[beyan-edilmis-survivor]].
    #     "Bölünmemiş" ölçütü BAĞIMSIZ normalleştirmeyle kurulur (kanon fonksiyonunun
    #     kendisiyle değil): üretilen anahtar, DEĞERİN TAMAMINA denk gelmeli — bir parçası
    #     kırpılmışsa (Volvo Penta -> penta) eşitlik bozulur.
    sonda_sapan = []
    for (marka, deger) in sondalar:
        js = sonda.get((marka, deger))
        py = evren.model_anahtari(marka, deger)
        if js != py or _bagimsiz_kanon(py) != _bagimsiz_kanon(deger):
            sonda_sapan.append((marka, deger, "js=%s" % js, "py=%s" % py,
                                "beklenen=%s" % _bagimsiz_kanon(deger)))

    # --- DISPLAY SORGULANABİLİR Mİ: sayfanın adı kendi kovasının anahtarına dönmeli
    #     (dönmezse o sayfa için ?model=<display> HİÇBİR ZAMAN doğru küme getirmez).
    sorgulanamaz = []
    for (marka, display), (_ids, canon) in sayfa.items():
        if evren.model_anahtari(marka, display) != canon:
            sorgulanamaz.append((marka, display, canon,
                                 evren.model_anahtari(marka, display)))

    # --- KUŞAK İSTİSNASI (KUSAK_DISI) AYNASI + KİMLİĞİ + ETKİSİ ------------------------
    # Otorite tools/arama.py KUSAK_DISI_JETON; index.html'deki dizi JS'in çalışma anı
    # AYNASIDIR (K8 bileşik marka deseninin kuşak ekseni karşılığı).
    kusak_ayna = list(getattr(evren, "kusak_disi", []))
    kusak_otorite = sorted("%s|%s" % (a, b) for a, b in _arama.KUSAK_DISI_JETON)
    kusak_ayna_fark = (sorted(set(kusak_otorite) - set(kusak_ayna)),
                       sorted(set(kusak_ayna) - set(kusak_otorite)))
    kusak_disi_imza = (_arama.kusak_disi_imzasi(), _arama.KUSAK_DISI_IMZA,
                       len(_arama.KUSAK_DISI_JETON), _arama.KUSAK_DISI_SAYISI)
    # ETKİ ÖLÇÜMÜ: istisnanın ürünleri taban modelin SAYFASINA SIZMAMALI (asıl iddia bu;
    # "tablo duruyor" demek yetmez — [[beyan-edilmis-survivor]]).
    sayfa_ids = dict(((mk, canon), ids) for (mk, _d), (ids, canon) in sayfa.items())
    kusak_disi_sizan = []
    for (mk, jeton) in sorted(_arama.KUSAK_DISI_JETON):
        toks = jeton.split()
        if len(toks) < 2:
            continue
        taban_k = evren.model_anahtari(mk, " ".join(toks[:-1]))
        jeton_k = evren.model_anahtari(mk, jeton)
        hedef_ids = sayfa_ids.get((mk, taban_k))
        if not taban_k or not hedef_ids:
            continue
        for p in urunler:
            m = [(x or "").strip() for x in (p.get("marka") or []) if (x or "").strip()]
            if mk not in mm.marka_uyelikleri(m, evren, ek):
                continue
            anahtarlar = set(evren.model_anahtari(mk, t) for t in m)
            if jeton_k in anahtarlar and taban_k not in anahtarlar \
                    and p.get("id") in hedef_ids:
                kusak_disi_sizan.append((mk, jeton, p.get("id")))

    # --- SIZINTI EKSENİ (A): DEĞİŞTİRİCİ ŞEKİLLİ YAYIN KÜMESİ == DONMUŞ ENVANTER --------
    # 🔴 BİRİM KÜME, SAYI DEĞİL: bir sayfa ölüp biri doğunca sayı sabit kalır ve sapma
    # gizlenirdi ([[hukum-yanlis-birimde]]). Şekil ölçütü BAĞIMSIZ (üretimin tablosu değil,
    # kapının kendi dilbilgisi) — aksi halde iddia totoloji olurdu.
    # 🔴 YAYIN KÜMESİ JENERATÖRÜ KOŞTURARAK çıkar (tabloyu OKUYARAK değil).
    izin = dict(_arama.DEGISTIRICI_SAYFA_IZNI)
    izin_imza = (_arama.degistirici_izni_imzasi(), _arama.DEGISTIRICI_SAYFA_IZNI_IMZA,
                 len(izin), _arama.DEGISTIRICI_SAYFA_IZNI_SAYISI)
    deny = dict(_arama.MODEL_OLMAYAN_CIFT)
    deny_imza = (_arama.model_olmayan_cift_imzasi(), _arama.MODEL_OLMAYAN_CIFT_IMZA,
                 len(deny), _arama.MODEL_OLMAYAN_CIFT_SAYISI)
    deny_n = set((mk, _bagimsiz_kanon(jt)) for mk, jt in deny)

    def _degistirici_sekilli(display):
        toks = (display or "").split()
        return len(toks) >= 2 and bool(_BAGIMSIZ_KUSAK_RE.match(_bagimsiz_kanon(toks[-1])))

    yayin_degistirici = set()
    yayin_degistirici_yargisiz = set()
    for (mk, dsp), (_i, canon) in sayfa.items():
        if not _degistirici_sekilli(dsp):
            continue
        yayin_degistirici.add("%s|%s" % (mk, canon))
        # 🔴 H3 KURALI ENVANTERİN YERİNE GEÇER (6 Ağu, mimar hükmü): kuyruğu DONANIM
        # OLMAYAN değiştirici-şekilli ad AYRI BİR ARACI adlandırır ve sayfa alır — bu
        # KURALDIR, tekil yargı değil; envantere yazılması gerekmez (yazılsaydı katalog
        # büyüdükçe elle bakım gerektirir ve sessizce bayatlardı).
        # Envanter yalnız kuralın AÇIKLAMADIĞI (donanım kuyruklu) sayfalar için yargıdır.
        if _bagimsiz_donanim_kuyruklu(dsp):
            yayin_degistirici_yargisiz.add("%s|%s" % (mk, canon))
    izin_fark = (sorted(set(izin) - yayin_degistirici),        # envanterde VAR, yayında YOK
                 sorted(yayin_degistirici_yargisiz - set(izin)))  # DONANIM kuyruklu SIZINTI
    # deny ile allow ÇELİŞMEMELİ (bir çift hem kapatılıp hem izinli olamaz)
    izin_deny_celiski = []
    for anahtar_metin in sorted(izin):
        _mk, _cn = anahtar_metin.split("|", 1)
        for (dmk, djt) in deny_n:
            if dmk == _mk and _cn.endswith(djt):
                izin_deny_celiski.append((anahtar_metin, djt))

    # --- DENY EKSENİ (B): kapatılan çiftin YAYIMLANAN kovası 0 (ürünü de kaybolmadı) -----
    # 🔴 SON-KELİME KOLU YALNIZ DEĞİŞTİRİCİLERE İŞLER (6 Ağu, mimar hükmü H2 — kapının
    # KENDİ dilbilgisiyle yazılır, üretim yüklemi çağrılmaz): `<taban> <jeton>` bileşiği
    # ancak jeton bir KUŞAK/DONANIM DEĞİŞTİRİCİSİYSE tabana yapışıktır (`Focus ST`,
    # `Focus Mk1`); `E-Tech` gibi bir ROZET adı bileşikte AYRI BİR ARACI adlandırır ve
    # `/marka/renault/5-e-tech/` KAPANMAZ. Kol kayıtsız yazılsaydı bu iki sayfa "sızıntı"
    # sayılırdı (ölçüldü) ve `("Renault","E-Tech")` hükmü hiç yazılamazdı.
    def _deny_vuruyor(dsp, dn):
        if _bagimsiz_kanon(dsp) == dn:
            return True
        toks = (dsp or "").split()
        return (len(toks) >= 2 and _bagimsiz_kanon(toks[-1]) == dn
                and bool(_BAGIMSIZ_KUSAK_RE.match(_bagimsiz_kanon(toks[-1]))))

    deny_sizan, deny_kaybolan, deny_etkilenen = [], [], []
    for (dmk, djt) in sorted(deny):
        dn = _bagimsiz_kanon(djt)
        vurus = 0
        for (mk, dsp), (ids, canon) in sayfa.items():
            if mk != dmk:
                continue
            if _deny_vuruyor(dsp, dn):
                deny_sizan.append((mk, dsp))
        # kapatılan kovaların ürünleri marka AĞACINDA duruyor mu (K11 deseni)
        for canon, g in (veri.get(dmk) or {}).get("gruplar", {}).items():
            dsp = g.get("display") or canon
            if not _deny_vuruyor(dsp, dn):
                continue
            vurus += 1
            agac = set()
            for g2 in veri[dmk]["gruplar"].values():
                if mm.yayimlanir_mi(g2):
                    agac |= set(p.get("id") for p in g2["urunler"] if p.get("id"))
            agac |= set(p.get("id") for p in (veri[dmk]["marka_only"]
                                              + veri[dmk].get("ikincil", [])
                                              + g["urunler"]) if p.get("id"))
            for p in g["urunler"]:
                if p.get("id") and p["id"] not in agac:
                    deny_kaybolan.append((dmk, dsp, p["id"]))
        deny_etkilenen.append((dmk, djt, vurus))

    # --- BAŞLIK-DOĞAN SAYFA YARGISI — K21 (5 Ağu, mimar hükmü: "yargısız sayfa DOĞMAZ") ---
    # İDDİA ÜÇ PARÇALI (K16/K19 disiplini):
    #   (1) SIZINTI: yalnız başlık kolu sayesinde YAYIMLANAN her kova envanterde OLMALI,
    #   (2) BAYAT : envanterdeki her giriş üretimde GERÇEKTEN başlık-doğan bir kova OLMALI,
    #   (3) ÇELİŞKİ: aynı çift hem allow'da hem deny'de (MODEL_OLMAYAN_CIFT) olamaz,
    #   + KİMLİK DONMUŞ (sessiz genişleme/daralma KIRMIZI).
    # 🔴 ÖLÇÜT YAYINA BAKAR AMA TABLOYU OKUMAZ: yayımlanan küme jeneratör KOŞTURULARAK
    # çıkar. Ayrıca YARGISIZ BEKLEYENLER ayrı sayılır — "sayfa doğmadı" sessiz kalmasın.
    try:
        _b_izin = dict(_arama.BASLIK_DOGAN_ALLOW)
        baslik_izin_imza = (_arama.baslik_dogan_allow_imzasi(),
                            _arama.BASLIK_DOGAN_ALLOW_IMZA,
                            len(_b_izin), _arama.BASLIK_DOGAN_ALLOW_SAYISI)
    except Exception as e:                                          # noqa: BLE001
        raise Olculemedi("tools/arama.py BASLIK_DOGAN_ALLOW okunamadı: %r" % (e,))
    _b_izin_anahtar = set("%s|%s" % (mk, _mk_kanon(jt)) for mk, jt in _b_izin)
    baslik_yayin, baslik_bekleyen = set(), []
    # 🔴 YARGI ÜÇ KAYNAKLI (6 Ağu, mimar hükmü H1+H3): envanter ∪ ŞASİ/MOTOR KODU kuralı ∪
    # AYRI ARAÇ ADI kuralı. Kapı bu üç kolu KENDİ bağımsız dilbilgisiyle kurar (üretimin
    # `baslik_yargisi_var_mi` gövdesi ÇAĞRILMAZ — çağrılsaydı iddia totoloji olurdu,
    # [[beyan-edilmis-survivor]]). Üretim kuralı gevşerse/sıkışırsa bu eksen KIRMIZI yanar.
    baslik_sizinti, baslik_ciplak_sayi, baslik_donanim = [], [], []
    baslik_kural_dogan = 0
    for _mk, _d in veri.items():
        for _canon, _g in _d["gruplar"].items():
            if not _g.get("baslik_dogan"):
                continue
            _dsp = _g.get("display") or _canon
            if mm.yayimlanir_mi(_g):
                baslik_yayin.add("%s|%s" % (_mk, _canon))
                if not _bagimsiz_baslik_yargisi(_mk, _canon, _dsp, _b_izin_anahtar):
                    baslik_sizinti.append("%s|%s" % (_mk, _canon))
                elif "%s|%s" % (_mk, _canon) not in _b_izin_anahtar:
                    baslik_kural_dogan += 1
                # H1 SINIRI: ÇIPLAK SAYI kural koluyla DOĞAMAZ (yalnız envanterle).
                if _bagimsiz_ciplak_sayi(_dsp) \
                        and "%s|%s" % (_mk, _canon) not in _b_izin_anahtar:
                    baslik_ciplak_sayi.append("%s|%s" % (_mk, _dsp))
                # H3 DENY KOLU: donanım kuyruklu kova SAYFA AÇMAZ.
                if _bagimsiz_donanim_kuyruklu(_dsp):
                    baslik_donanim.append("%s|%s" % (_mk, _dsp))
            elif _g.get("birincil") and len(_g["urunler"]) >= mm.ESIK \
                    and (_mk, _canon) not in mm.ROZET_DISI \
                    and not mm.model_olmayan_cift_mi(_mk, _dsp):
                baslik_bekleyen.append((_mk, _dsp, len(_g["urunler"])))
    baslik_sizinti = sorted(baslik_sizinti)
    # BAYAT ekseni ENVANTERE dairdir: kuralla doğan sayfalar envanterde ARANMAZ.
    baslik_bayat = sorted(_b_izin_anahtar - baslik_yayin)
    # ÇELİŞKİ: allow'daki bir çift AYNI ZAMANDA deny yüklemini tetikliyor mu? Ölçüt
    # üretimin deny yüklemiyle AYNI birimde kurulur (çıplak jeton + SON KELİME); düz
    # `endswith` yazsaydık "everest" -> "st" gibi kelime-içi eşleşme yanlış alarm verirdi.
    baslik_celiski = []
    for mk, jt in sorted(_b_izin):
        _dn = _bagimsiz_kanon(jt)
        _toks = jt.split()
        if (mk, _dn) in deny_n or (len(_toks) >= 2
                                   and (mk, _bagimsiz_kanon(_toks[-1])) in deny_n
                                   and bool(_BAGIMSIZ_KUSAK_RE.match(
                                       _bagimsiz_kanon(_toks[-1])))):
            baslik_celiski.append("%s|%s" % (mk, _mk_kanon(jt)))

    # --- KÜRATÖRLÜ KUŞAK EŞLEMESİ: ayna + kimlik + ETKİ ---------------------------------
    esleme_ayna = list(getattr(evren, "kusak_esleme", []))
    esleme_otorite = sorted("%s|%s|%s" % (a, b, t)
                            for (a, b), t in _arama.KUSAK_ESLEME.items())
    esleme_fark = (sorted(set(esleme_otorite) - set(esleme_ayna)),
                   sorted(set(esleme_ayna) - set(esleme_otorite)))
    esleme_imza = (_arama.kusak_esleme_imzasi(), _arama.KUSAK_ESLEME_IMZA,
                   len(_arama.KUSAK_ESLEME), _arama.KUSAK_ESLEME_SAYISI)
    # ETKİ 1: eşlenen jetonun ürünü TABAN sayfada mı · ETKİ 2: kuşağın kendi sayfası KAPANMADI
    esleme_ulasmayan, esleme_kapanan = [], []
    for (emk, ejt), etaban in sorted(_arama.KUSAK_ESLEME.items()):
        taban_k = evren.model_anahtari(emk, etaban)
        jeton_k = evren.model_anahtari(emk, ejt)
        gk = (veri.get(emk) or {}).get("gruplar", {}).get(jeton_k)
        if not gk:
            continue
        hedef_ids = sayfa_ids.get((emk, taban_k))
        if hedef_ids is not None:
            # İDDİA KÜRATÖRLÜ EŞLEMENİN ETKİSİNE DAİRDİR: eşleme yalnız JETON YOLUNA
            # (marka[]/uyum[]) uygulanır, dolayısıyla ölçüm de o yolla üye olan ürünlerle
            # sınırlıdır. Kovaya YALNIZ BAŞLIK KOLUNDAN giren ürün (ör. "VW T1 Beetle …")
            # eşlemenin konusu değildir — onu tabana taşımak Beetle parçasını Transporter
            # sayfasına sızdırırdı. Eşleme yoluyla gelen ürünün tabana ULAŞMAMASI hâlâ
            # KIRMIZI (kolun kendisi ölçülüyor).
            _baslik_ekli = set(gk.get("baslik_ekli") or ())
            for p in gk["urunler"]:
                if p.get("id") and p["id"] not in hedef_ids \
                        and p["id"] not in _baslik_ekli:
                    esleme_ulasmayan.append((emk, ejt, p["id"]))
        # "kuşak sayfaları KAPANMAZ" (mimar hükmü): eşik+birincil şartını sağlayan kova
        # yayımda OLMALI — eşleme bir sayfayı sessizce öldürmemeli.
        # 🟡 BAŞLIK YARGISI HARİÇ (5 Ağu, K19 ile aynı gerekçe): eşiği YALNIZ başlık kolu
        # sayesinde geçen ve henüz yargılanmamış kova hiç var olmadı — "kapandı" denemez;
        # o kova mimarın önünde TEK karar olarak bekliyor (K21 sayar).
        if gk.get("baslik_dogan") and (emk, jeton_k) not in mm.BASLIK_DOGAN_ALLOW:
            continue
        if gk.get("birincil") and len(gk["urunler"]) >= mm.ESIK \
                and (emk, jeton_k) not in mm.ROZET_DISI \
                and not mm.model_olmayan_cift_mi(emk, gk.get("display") or ejt) \
                and (emk, jeton_k) not in set((a, b) for (a, _d), (_i, b) in sayfa.items()):
            esleme_kapanan.append((emk, ejt, len(gk["urunler"])))

    # --- ÇIPLAK TEK HARF JETON BİRLEŞMESİ — K20 (4 Ağu, kararsız jeton SINIF 1) ---------
    # İDDİA ÜÇ PARÇALI: (1) kural fikstürle çivili ve JS↔Python AYNI · (2) ETKİSİ ölçülür
    # (çıplak jetonlu ürün TAM YAZIM kovasına ULAŞTI, çıplak yazımın AYRI kovası KALMADI,
    # ürün KAYBOLMADI) · (3) POZİTİF ÇAPA (marka-kör bir kuralın öldüreceği CANLI sayfalar
    # duruyor). Yalnız (1) yazılsaydı "tablo duruyor" demiş olurduk — [[beyan-edilmis-survivor]].
    tekharf_sapan, tekharf_ulasmayan, tekharf_ayri_kova, tekharf_kaybolan = [], [], [], []
    for mk, jt, beklenen_a, beklenen_d, _ciplak in TEK_HARF_FIKSTURU:
        js, py = birlesme_js.get((mk, jt)), evren.model_anahtari(mk, jt)
        if js != beklenen_a or py != beklenen_a:
            tekharf_sapan.append((mk, jt, "js=%s" % js, "py=%s" % py,
                                  "beklenen=%s" % beklenen_a))
            continue
        g = (veri.get(mk) or {}).get("gruplar", {}).get(beklenen_a)
        if not g:
            tekharf_sapan.append((mk, jt, "KOVA YOK (%s)" % beklenen_a, "", ""))
        elif (g.get("display") or "") != beklenen_d:
            tekharf_sapan.append((mk, jt, "gosterim=%r" % g.get("display"),
                                  "beklenen=%r" % beklenen_d, ""))
    for mk, jt, beklenen_a, _bd, ciplak in TEK_HARF_FIKSTURU:
        if not ciplak:
            continue
        ciplak_k = _bagimsiz_kanon(jt)
        hedef = (veri.get(mk) or {}).get("gruplar", {}).get(beklenen_a) or {}
        hedef_ids = set(p.get("id") for p in hedef.get("urunler", []) if p.get("id"))
        agac = set()
        for _g2 in (veri.get(mk) or {}).get("gruplar", {}).values():
            agac |= set(p.get("id") for p in _g2["urunler"] if p.get("id"))
        agac |= set(p.get("id") for p in ((veri.get(mk) or {}).get("marka_only", [])
                                          + (veri.get(mk) or {}).get("ikincil", []))
                    if p.get("id"))
        for p in urunler:
            m = [(x or "").strip() for x in (p.get("marka") or []) if (x or "").strip()]
            if not any(_bagimsiz_kanon(t) == ciplak_k for t in m):
                continue
            if mk not in mm.marka_uyelikleri(m, evren, ek):
                continue
            if p.get("id") not in hedef_ids:
                tekharf_ulasmayan.append((mk, jt, p.get("id")))
            if p.get("id") not in agac:
                tekharf_kaybolan.append((mk, jt, p.get("id")))
        # ÇIPLAK yazımın KENDİ (ayrı) kovası KALMAMALI — kalsaydı eşiği geçtiği gün TEK
        # HARFLİ bir sayfa doğardı (ölçülen sessiz doğum sınıfı).
        for canon, g2 in (veri.get(mk) or {}).get("gruplar", {}).items():
            if canon != beklenen_a and _bagimsiz_kanon(g2.get("display") or canon) == ciplak_k:
                tekharf_ayri_kova.append((mk, g2.get("display"), canon, len(g2["urunler"])))
    # POZİTİF ÇAPA — marka-KÖR bir "tek harf" kuralı bunları öldürürdü (ölçüldü: Renault 5
    # RAKAM ve gerçek model · Opel Astra K meşru kuşak sayfası). İkisi de YAYINDA kalmalı.
    tekharf_capa_dusen = []
    for mk, dsp in (("Renault", "5"), ("Opel", "Astra K")):
        ids = sayfa.get((mk, dsp), (set(), None))[0]
        if not ids:
            tekharf_capa_dusen.append((mk, dsp))

    # --- ALT BÖLÜM AYRIM KANITI: RENDER EDİLMİŞ HTML üzerinden -------------------------
    # 🔴 NEDEN HTML (veri değil): ayrımı `g["kusak_bolum"]` sözlüğünden ölçseydik, bölümleri
    # GÖRMEZDEN gelip hepsini tek listeye döken bir RENDERER mutantı veriyi bozmadığı için
    # YEŞİL geçerdi. Ölçüm müşterinin GÖRDÜĞÜ sayfadan yapılır.
    try:
        _b = _modul(os.path.join(kok, "tools", "build.py"), "build_model_kapisi")
        _ctx = _b.marka_model_ctx()
        _ctx["ROOT"] = kok
        _kategoriler = mm.kategori_evreni(index_html)
    except Exception as e:                                          # noqa: BLE001
        raise Olculemedi("build.py marka_model_ctx() alınamadı, ayrım ölçülemez: %r" % (e,))

    bolum_sayfa = bolum_urun = 0
    bolum_sapan = []
    for (marka, display), (ids, canon) in sorted(sayfa.items()):
        g = veri[marka]["gruplar"][canon]
        if not g.get("kusak_bolum"):
            continue
        try:
            _url, _html = mm._model_sayfasi(_ctx, marka, g, _kategoriler)
        except Exception as e:                                      # noqa: BLE001
            raise Olculemedi("model sayfası render edilemedi (%s/%s): %r" % (marka, display, e))
        kesitler = _sayfa_kesitleri(_html)
        if not kesitler:
            bolum_sapan.append((marka, display, "H2 bölümü YOK (ayrım render'da kayıp)"))
            continue
        bolum_sayfa += 1
        ana_ids = set(p.get("id") for p in g.get("ana", []) if p.get("id"))
        # KATLAMA YENİ KOVA UYDURMAZ: hedef kova TAM eşleşmeyle DOĞMUŞ olmalı (ana liste
        # dolu). Ayırt edici mutantı YOK (bugünkü katalogda katlama-doğumlu kova üretmek
        # için üretecin akışını yeniden yazmak gerekir) — iddia değil, NÖBET olarak durur.
        if not ana_ids:
            bolum_sapan.append((marka, display, "KATLAMA-DOĞUMLU KOVA (ana liste boş)"))
        ana_baslik, ana_kartlar = kesitler[0]
        if ana_kartlar != ana_ids:
            bolum_sapan.append((marka, display, "ana liste kümesi sapıyor: html=%d veri=%d"
                                % (len(ana_kartlar), len(ana_ids))))
        # ANA LİSTEDE KUŞAK-ÖZEL ÜRÜN 0 (bağımsız ölçüt — üretimin tablosu çağrılmaz)
        hedef = _bagimsiz_kanon(display)
        for pid in sorted(ana_kartlar):
            p = urun_ix.get(pid) or {}
            jet = set(_bagimsiz_kanon(x) for x in (p.get("marka") or []) if x)
            # BAŞLIK KOLUYLA gelen üyelik kuşak-özel SAYILMAZ: ürün modelin adını BAŞLIĞINDA
            # TAM KELİME taşıyor (katlanmadı, TAM eşleşti) — ana listede durması doğrudur.
            # Ölçüt yine bağımsız gövdeden gelir; "katlandı ama ana listeye karıştı" sınıfı
            # (jetonu yalnız varyant olan ürün) KIRMIZI yakmaya devam eder.
            if not _tasiyor(jet, hedef) and _kusak_tasiyor(jet, hedef) \
                    and not _baslik_aciklar(pid, marka, canon):
                bolum_sapan.append((marka, display,
                                    "ANA LİSTEDE kuşak-özel ürün: %s %s" % (pid, sorted(jet)[:3])))
        html_bolum = dict((b, k) for b, k in kesitler[1:])
        for b in g["kusak_bolum"]:
            bolum_urun += len(b["urunler"])
            bek = set(p.get("id") for p in b["urunler"] if p.get("id"))
            baslik = b["display"] + " parçaları"
            bulunan = None
            for hb, hk in html_bolum.items():
                if hb.startswith(baslik):
                    bulunan = hk
                    break
            if bulunan is None:
                bolum_sapan.append((marka, display, "kuşak bölümü BASILMADI: %r" % baslik))
            elif bulunan != bek:
                bolum_sapan.append((marka, display, "kuşak bölümü kümesi sapıyor (%s): "
                                    "html=%d veri=%d" % (b["display"], len(bulunan), len(bek))))
        # BÖLÜMLER AYRIK: bir ürün sayfada TEK bölümde görünür (aynı kart iki kez basılırsa
        # müşteri mükerrer görür; küme karşılaştırması bunu TEK BAŞINA yakalamaz).
        toplam_html = set()
        _mukerrer = 0
        for _hb, _hk in kesitler:
            _mukerrer += len(toplam_html & _hk)
            toplam_html |= _hk
        if _mukerrer:
            bolum_sapan.append((marka, display,
                                "AYNI ÜRÜN BİRDEN ÇOK BÖLÜMDE: %d kart" % _mukerrer))
        if toplam_html != ids:
            bolum_sapan.append((marka, display, "SAYFADAKİ ÜRÜN KÜMESİ sapıyor: html=%d kova=%d"
                                % (len(toplam_html), len(ids))))

    satir = ("CIFT=%d TEMIZ=%d SAYFA_DAR=%d FILTRE_DAR=%d ETKILENEN_URUN=%d"
             % (len(ciftler), temiz, sayfa_dar, filtre_dar, len(etkilenen)))
    return satir, {"cift": len(ciftler), "temiz": temiz, "sayfa_dar": sayfa_dar,
                   "filtre_dar": filtre_dar, "capraz": capraz,
                   "etkilenen": len(etkilenen), "dokum": dokum, "sahte": sahte,
                   "alias_aciklamali": alias_aciklamali,
                   "baslik_aciklanan": baslik_aciklanan,
                   "baslik_aciklanamayan": baslik_aciklanamayan,
                   "baslik_aciklamali": len(baslik_aciklamali),
                   "sorgulanamaz": sorgulanamaz, "marka_sayisi": len(veri),
                   "anahtar_ornek": ornek, "marka_kovasi": marka_kovasi,
                   "ayna_fark": ayna_fark, "ayna": ayna, "red_imza": red_imza,
                   "sonda_sapan": sonda_sapan, "sonda_sayisi": len(sondalar),
                   "rozet_ihlal": rozet_ihlal, "rozet_elenen": rozet_elenen,
                   "rozet_kaybolan": rozet_kaybolan, "rozet_imza": rozet_imza,
                   "capraz_cift": sorted(capraz_cift), "capraz_yargisiz": capraz_yargisiz,
                   "capraz_bayat": capraz_bayat, "capraz_celiski": capraz_celiski,
                   "capraz_bekler": capraz_bekler, "capraz_imza": capraz_imza,
                   "capraz_ozet": capraz_ozet,
                   "kusak_sapan": kusak_sapan, "kusak_sonda_sayisi": len(kusak_sondalar),
                   "fikstur_sapan": fikstur_sapan, "fikstur_sayisi": len(KATLAMA_FIKSTURU),
                   "kusak_aciklamali": len(kusak_aciklamali),
                   "esleme_aciklamali": len(esleme_aciklamali),
                   "kusak_ayna_fark": kusak_ayna_fark, "kusak_ayna": kusak_ayna,
                   "kusak_disi_imza": kusak_disi_imza, "kusak_disi_sizan": kusak_disi_sizan,
                   "bolum_sayfa": bolum_sayfa, "bolum_urun": bolum_urun,
                   "bolum_sapan": bolum_sapan, "katlama_envanteri": _katlama_envanteri(veri),
                   "izin_fark": izin_fark, "izin_imza": izin_imza,
                   "izin_deny_celiski": izin_deny_celiski,
                   "yayin_degistirici": len(yayin_degistirici),
                   "deny_imza": deny_imza, "deny_sizan": deny_sizan,
                   "deny_kaybolan": deny_kaybolan, "deny_etkilenen": deny_etkilenen,
                   "baslik_izin_imza": baslik_izin_imza, "baslik_yayin": len(baslik_yayin),
                   "baslik_sizinti": baslik_sizinti, "baslik_bayat": baslik_bayat,
                   "baslik_celiski": baslik_celiski,
                   "baslik_ciplak_sayi": sorted(baslik_ciplak_sayi),
                   "baslik_donanim": sorted(baslik_donanim),
                   "baslik_kural_dogan": baslik_kural_dogan,
                   "baslik_bekleyen": sorted(baslik_bekleyen, key=lambda t: (-t[2], t[0])),
                   "esleme_fark": esleme_fark, "esleme_imza": esleme_imza,
                   "tekharf_sapan": tekharf_sapan, "tekharf_ulasmayan": tekharf_ulasmayan,
                   "tekharf_ayri_kova": tekharf_ayri_kova,
                   "tekharf_kaybolan": tekharf_kaybolan,
                   "tekharf_capa_dusen": tekharf_capa_dusen,
                   "tekharf_sayisi": len(TEK_HARF_FIKSTURU),
                   "esleme_ayna": esleme_ayna, "esleme_ulasmayan": esleme_ulasmayan,
                   "esleme_kapanan": esleme_kapanan,
                   "envanter": _envanter(urunler, veri, evren, mm, sayfa),
                   "cok_kelimeli": cok_kelimeli}


_H2_RE = re.compile(r'<h2 class="mm-sec-h[^"]*"[^>]*>(.*?)</h2>', re.S)


def _sayfa_kesitleri(html):
    """[(başlık metni, {ürün id})] — model sayfasının H2 bölümleri ve o bölümdeki kartlar.
    İlk kesit ANA listedir; sonrakiler kuşak bölümleridir."""
    yerler = [(m.start(), m.end(), re.sub(r"<[^>]+>", "", m.group(1)).strip())
              for m in _H2_RE.finditer(html)]
    out = []
    for i, (_bas, son, baslik) in enumerate(yerler):
        bit = yerler[i + 1][0] if i + 1 < len(yerler) else len(html)
        out.append((baslik, set(re.findall(r'href="[^"]*?/urun/([^/"]+)/"', html[son:bit]))))
    return out


def _katlama_envanteri(veri):
    """[(marka, taban display, kuşak display, ürün, kuşağın kendi sayfası var mı)] —
    hangi HAM kuşak jetonu hangi kanonik modele katlandı (rapor ekseni)."""
    out = []
    for marka, d in veri.items():
        for g in d["gruplar"].values():
            for b in g.get("kusak_bolum", []):
                out.append((marka, g["display"], b["display"], len(b["urunler"]),
                            "SAYFA" if b["sayfa"] else "-"))
    return sorted(out, key=lambda r: (-r[3], r[0], r[2]))


def _envanter(urunler, veri, evren, mm, sayfa):
    """SPEC §2 (KraL): model türetmesi KAÇ jetonu böldü / KAÇ jetonu bileşik diye korudu?

    Dönüş: {"bolunen": [...], "korunan": [...]} — her satır
    (ham jeton, marka, -> model, anahtar, ürün sayısı, sayfa var mı)."""
    bolunen, korunan = {}, {}
    yayin_anahtar = set((mk, c) for (mk, _d), (_i, c) in sayfa.items())
    # Üyelik evreni jeneratörün KENDİ kovalarından okunur — ikinci bir marka evreni kurulmaz.
    marka_evreni = set(veri)
    bilesik = set(getattr(evren, "bilesik", []))
    for p in urunler:
        m = [(x or "").strip() for x in (p.get("marka") or []) if (x or "").strip()]
        if not m:
            continue
        uyeler = set(evren.katla(x) for x in m) & marka_evreni
        for B in uyeler:
            for t in m:
                kalan = mm._strip_marka_oneki(B, t, evren)
                if kalan and kalan != t:
                    # GERÇEK bölünme: "<marka öneki> <kalan>" -> "<kalan>"
                    bolunen.setdefault((t, B, kalan, evren.model_anahtari(B, t)),
                                       set()).add(p.get("id"))
                elif t in bilesik and evren.katla(t) == B:
                    # BİLEŞİK MARKA: bölünebilirdi ama koruma tek parça bıraktı
                    korunan.setdefault((t, B), set()).add(p.get("id"))
    return {
        "bolunen": sorted(((t, B, k, a, len(ids),
                            "YAYIN" if (B, a) in yayin_anahtar else "-")
                           for (t, B, k, a), ids in bolunen.items()),
                          key=lambda r: (-r[4], r[0])),
        "korunan": sorted(((t, B, len(ids)) for (t, B), ids in korunan.items()),
                          key=lambda r: (-r[2], r[0])),
    }


# ---------------------------------------------------------------- kabul
def kabul(kok, dokum=False, modul_yolu=None, envanter=False):
    kaldi, gecen = [], []

    def dogrula(ad, kosul, detay=""):
        (gecen if kosul else kaldi).append(ad)
        print("  %s %s%s" % ("GECTI" if kosul else "KALDI", ad, (" — " + detay) if detay else ""))

    satir, a = olc(kok, modul_yolu)
    print("  " + satir + "  (CAPRAZ=%d · marka kovası=%d)" % (a["capraz"], a["marka_sayisi"]))
    print("  KANON ORNEK: modelAnahtar(Ford,'F150')=%s · modelAnahtar(Ford,'F-Series')=%s"
          % (a["anahtar_ornek"].get("f150"), a["anahtar_ornek"].get("fSerisi")))

    dogrula("K0 FAIL-CLOSED: ÖLÇÜLEN ÇİFT VAR", a["cift"] > 0,
            "cift=%d (0 çift 'sapma yok' diye YEŞİL geçemez)" % a["cift"])
    dogrula("K1 SAYFA_DAR=0 (filtrenin gösterdiği her ürün sayfada VAR)", a["sayfa_dar"] == 0,
            "sayfa_dar=%d" % a["sayfa_dar"])
    dogrula("K2 FILTRE_DAR: sayfanın gösterdiği her ürünü filtre BULUR ya da fark BAŞLIK "
            "KOLUYLA açıklanır", a["filtre_dar"] == 0 and not a["baslik_aciklanamayan"],
            "açıklanamayan filtre_dar=%d %s · başlık koluyla açıklanan üyelik=%d "
            "(🟡 ADIM 2 borcu: index.html filtresi bu yüklemi HENÜZ almadı)"
            % (a["filtre_dar"], [x[:2] for x in a["baslik_aciklanamayan"][:3]] or "-",
               a["baslik_aciklanan"]))
    dogrula("K3 CAPRAZ=0 (iki yönde birden sapan çift YOK)", a["capraz"] == 0,
            "capraz=%d" % a["capraz"])
    dogrula("K4 YANLIŞ-POZİTİF YOK: sayfaya giren her ürün o model jetonunu GERÇEKTEN taşıyor",
            not a["sahte"], "sahte=%d %s" % (len(a["sahte"]), a["sahte"][:4]))
    if a["baslik_aciklamali"]:
        print("  BILGI BAŞLIK KOLU ile açıklanan üyelik: %d ürün (muafiyet listesi DEĞİL, "
              "kapının KENDİ bağımsız başlık dilbilgisiyle ölçülür; tehlike koruması ya da "
              "bitişiklik gevşerse bu eksen yanlış-pozitif üretir)" % a["baslik_aciklamali"])
    if a["alias_aciklamali"]:
        print("  BILGI KÜRATÖRLÜ ALIAS ile açıklanan üyelik: %d ürün (muafiyet listesi DEĞİL, "
              "MODEL_ALIAS tablosundan türer) örnek: %s"
              % (len(a["alias_aciklamali"]), a["alias_aciklamali"][:2]))
    dogrula("K5 HER SAYFA KENDİ ADIYLA SORGULANABİLİR (display -> kova anahtarı)",
            not a["sorgulanamaz"],
            "sorgulanamaz=%d %s" % (len(a["sorgulanamaz"]), a["sorgulanamaz"][:3]))
    # K7 — BİLEŞİK MARKA / MARKA JETONU: bir MARKA'yı MODEL diye sunan sayfa YOK.
    # Yargı tools/arama.py KAPALI MARKA KÜMESİ + MODEL_OLMAYAN_JETON'dan BAĞIMSIZ okunur.
    dogrula("K7 MARKA JETONU SAYFA OLMAZ (bileşik marka bölünmemiş, üretici/grup kısaltması "
            "model sayılmamış)", not a["marka_kovasi"],
            "marka-kovası=%d %s" % (len(a["marka_kovasi"]), a["marka_kovasi"][:4]))
    # K8 — AYNA: index.html BILESIK_MARKA, arama.py'nin ÇOK KELİMELİ üyeleriyle BİREBİR.
    dogrula("K8 BİLEŞİK MARKA AYNASI OTORİTEYLE BİREBİR (arama.py KAPALI MARKA KÜMESİ)",
            not a["ayna_fark"][0] and not a["ayna_fark"][1] and len(a["ayna"]) > 0,
            "aynada eksik=%s · fazla=%s · ayna=%d otorite=%d"
            % (a["ayna_fark"][0] or "-", a["ayna_fark"][1] or "-",
               len(a["ayna"]), len(a["cok_kelimeli"])))
    # K10 — ANAHTAR SONDASI: bileşik marka adı İKİ TARAFTA da tek parça anahtar üretir.
    #       (İki koruma katmanı da bu eksende TEK BAŞINA kırmızı yakılabilir.)
    dogrula("K10 BİLEŞİK MARKA ANAHTARI BÖLÜNMÜYOR ve JS ile Python AYNI (%d sonda)"
            % a["sonda_sayisi"],
            a["sonda_sayisi"] > 0 and not a["sonda_sapan"],
            "sapan=%d %s" % (len(a["sonda_sapan"]), a["sonda_sapan"][:3])
            if a["sonda_sayisi"] else "SONDA YOK — eksen ÖLÇÜLEMEDİ (fail-closed)")
    # K9 — MODEL_OLMAYAN_JETON kimliği DONMUŞ: sessiz büyüme/daralma KIRMIZI yakar.
    _ri = a["red_imza"]
    dogrula("K9 MODEL_OLMAYAN_JETON KİMLİĞİ DONMUŞ (sessiz genişleme yok)",
            _ri[0] == _ri[1] and _ri[2] == _ri[3],
            "imza=%s beklenen=%s sayı=%d beklenen=%d" % _ri)
    # K11 — ROZET KAPISI: rozet dışı çift SAYFA OLMAZ **ve** ürünleri KAYBOLMAZ.
    dogrula("K11 ROZET DIŞI ÇİFTİN SAYFASI YOK ve ürünü KAYBOLMADI (kaybolan=%d)"
            % len(a["rozet_kaybolan"]),
            not a["rozet_ihlal"] and not a["rozet_kaybolan"] and len(a["rozet_elenen"]) > 0,
            "ihlal=%s · elenen kova=%d · kaybolan ürün=%d"
            % (a["rozet_ihlal"] or "-", len(a["rozet_elenen"]), len(a["rozet_kaybolan"])))
    for _e in a["rozet_elenen"]:
        print("        ELENEN %-34s %2d ürün · gerçek model sayfasında %d · kaybolan %d"
              % (_e["url"], _e["n"], _e["gercek_sayfada"], _e["kaybolan"]))
    # K12 — ROZET_DISI_CIFT kimliği DONMUŞ.
    _zi = a["rozet_imza"]
    dogrula("K12 ROZET_DISI_CIFT KİMLİĞİ DONMUŞ (sessiz sayfa kapatma/açma yok)",
            _zi[0] == _zi[1] and _zi[2] == _zi[3],
            "imza=%s beklenen=%s sayı=%d beklenen=%d" % _zi)
    # K19 — ÇAPRAZ-MARKA (ROZET) TUTARLILIK KAPISI: sayfa DOĞMADAN ÖNCE yakalar.
    #       Aynı model adı iki markada da sayfa eşiğini geçiyorsa çiftin YARGISI olmalı
    #       (deny ya da allow). Birim KÜME; envanter bayatlaması da KIRMIZI yakar.
    _ci = a["capraz_imza"]
    dogrula("K19 ÇAPRAZ-MARKA ÇİFTİNİN YARGISI VAR (yargısız sayfa doğmaz; %d çift/%d model)"
            % (len(a["capraz_cift"]), len(a["capraz_ozet"])),
            not a["capraz_yargisiz"] and not a["capraz_bayat"] and not a["capraz_celiski"]
            and len(a["capraz_cift"]) > 0 and _ci[0] == _ci[1] and _ci[2] == _ci[3],
            "YARGISIZ (sızıntı)=%s · envanterde var üretimde yok=%s · deny/allow çelişkisi=%s"
            " · imza=%s beklenen=%s sayı=%d beklenen=%d"
            % (a["capraz_yargisiz"] or "-", a["capraz_bayat"] or "-",
               a["capraz_celiski"] or "-", _ci[0], _ci[1], _ci[2], _ci[3]))
    if a["capraz_bekler"]:
        print("  BILGI ÇAPRAZ-MARKA 'BEKLER' sınıfı — bugünkü CANLI sayfayı korumak için açık, "
              "rozet hükmü MİMAR/İŞLETME kararı (%d çift): %s"
              % (len(a["capraz_bekler"]), a["capraz_bekler"]))
    # ═══ KUŞAK/VARYANT KATLAMASI (4 Ağu, KraL hükmü) ═══════════════════════════════════
    # K13 — KURAL FİKSTÜRLE ÇİVİLİ: "Golf 4"/"Astra H" TABAN modele katlanır; "Zafira Life"/
    #       "Ami 6"/"Golf" KATLANMAZ. İki taraf (JS gövdesi + Python portu) AYRI AYRI ölçülür.
    dogrula("K13 KATLAMA KURALI FİKSTÜRE UYUYOR (%d satır × 2 taraf) ve JS↔Python AYNI "
            "(%d sonda)" % (a["fikstur_sayisi"], a["kusak_sonda_sayisi"]),
            not a["fikstur_sapan"] and not a["kusak_sapan"]
            and a["kusak_sonda_sayisi"] > len(KATLAMA_FIKSTURU),
            "fikstür sapan=%d %s · js/py sapan=%d %s"
            % (len(a["fikstur_sapan"]), a["fikstur_sapan"][:3],
               len(a["kusak_sapan"]), a["kusak_sapan"][:2]))
    # K14 — AYRIM: katlanan ürün ana listeye KARIŞMAZ, kendi kuşak bölümünde durur.
    #       Ölçüm RENDER EDİLMİŞ HTML'den (veriden değil) — renderer mutantı yakalanabilsin.
    dogrula("K14 KUŞAK AYRIMI RENDER'DA DURUYOR (ana listede kuşak-özel ürün 0; %d sayfa, "
            "%d katlanan ürün)" % (a["bolum_sayfa"], a["bolum_urun"]),
            not a["bolum_sapan"] and a["bolum_sayfa"] > 0 and a["bolum_urun"] > 0,
            "sapan=%d %s" % (len(a["bolum_sapan"]), a["bolum_sapan"][:3]))
    # K15 — İSTİSNA (KUSAK_DISI): ayna otoriteyle birebir, kimlik donmuş, ürün taban
    #       sayfasına SIZMAMIŞ (tablo duruyor demek yetmez, ETKİSİ ölçülür).
    _ki = a["kusak_disi_imza"]
    dogrula("K15 KUŞAK İSTİSNASI AYNASI+KİMLİĞİ DONMUŞ ve ÜRÜNÜ TABAN SAYFAYA SIZMIYOR",
            not a["kusak_ayna_fark"][0] and not a["kusak_ayna_fark"][1]
            and len(a["kusak_ayna"]) > 0 and not a["kusak_disi_sizan"]
            and _ki[0] == _ki[1] and _ki[2] == _ki[3],
            "aynada eksik=%s fazla=%s · sızan=%s · imza=%s beklenen=%s sayı=%d beklenen=%d"
            % (a["kusak_ayna_fark"][0] or "-", a["kusak_ayna_fark"][1] or "-",
               a["kusak_disi_sizan"] or "-", _ki[0], _ki[1], _ki[2], _ki[3]))
    # K16 — SIZINTI EKSENİ: değiştirici şekilli YAYIN kümesi, donmuş envanterle BİREBİR.
    _ii = a["izin_imza"]
    dogrula("K16 DEĞİŞTİRİCİ ŞEKİLLİ SAYFA KÜMESİ DONMUŞ ENVANTERLE BİREBİR (%d sayfa)"
            % a["yayin_degistirici"],
            not a["izin_fark"][0] and not a["izin_fark"][1] and not a["izin_deny_celiski"]
            and a["yayin_degistirici"] > 0 and _ii[0] == _ii[1] and _ii[2] == _ii[3],
            "envanterde var yayında yok=%s · yayında var envanterde yok (SIZINTI)=%s · "
            "deny/allow çelişkisi=%s · imza=%s beklenen=%s"
            % (a["izin_fark"][0] or "-", a["izin_fark"][1] or "-",
               a["izin_deny_celiski"] or "-", _ii[0], _ii[1]))
    # K17 — DENY EKSENİ: kapatılan (marka, jeton) çiftinin yayımlanan kovası 0, ürünü sağ.
    _di = a["deny_imza"]
    dogrula("K17 MODEL OLMAYAN ÇİFTİN SAYFASI YOK ve ürünü KAYBOLMADI (%d çift)" % _di[2],
            not a["deny_sizan"] and not a["deny_kaybolan"] and _di[0] == _di[1]
            and _di[2] == _di[3] and sum(v for _m, _j, v in a["deny_etkilenen"]) > 0,
            "sızan sayfa=%s · kaybolan ürün=%d · imza=%s beklenen=%s"
            % (a["deny_sizan"] or "-", len(a["deny_kaybolan"]), _di[0], _di[1]))
    for _m, _j, _v in a["deny_etkilenen"]:
        print("        KAPATILAN %-10s %-10s -> eşleşen kova %d (sayfa 0)" % (_m, _j, _v))
    # K18 — KÜRATÖRLÜ KUŞAK EŞLEMESİ: ayna+kimlik donmuş, ürün TABAN sayfaya ULAŞTI,
    #       kuşağın KENDİ sayfası KAPANMADI (mimar hükmü).
    _ei = a["esleme_imza"]
    dogrula("K18 KÜRATÖRLÜ KUŞAK EŞLEMESİ AYNASI+KİMLİĞİ DONMUŞ, ürün TABAN sayfada, "
            "kuşak sayfası KAPANMADI (%d eşleme)" % _ei[2],
            not a["esleme_fark"][0] and not a["esleme_fark"][1] and len(a["esleme_ayna"]) > 0
            and not a["esleme_ulasmayan"] and not a["esleme_kapanan"]
            and _ei[0] == _ei[1] and _ei[2] == _ei[3],
            "aynada eksik=%s fazla=%s · tabana ulaşmayan ürün=%d %s · KAPANAN kuşak sayfası=%s"
            " · imza=%s beklenen=%s"
            % (a["esleme_fark"][0] or "-", a["esleme_fark"][1] or "-",
               len(a["esleme_ulasmayan"]), a["esleme_ulasmayan"][:2],
               a["esleme_kapanan"] or "-", _ei[0], _ei[1]))
    if a["esleme_aciklamali"]:
        print("  BILGI KÜRATÖRLÜ KUŞAK EŞLEMESİ ile açıklanan üyelik: %d ürün (muafiyet "
              "listesi DEĞİL, KUSAK_ESLEME kaynağından türer; kimliği/etkisi K18'de ölçülür)"
              % a["esleme_aciklamali"])
    # K20 — ÇIPLAK TEK HARF JETON: tam yazımla TEK kovada birleşir, AYRI kovası KALMAZ,
    #       ürünü KAYBOLMAZ; marka-KÖR bir kuralın öldüreceği CANLI sayfalar YERİNDE.
    #       Ölçüldü (4 Ağu): BMW `K` (1) ile `K Serisi` (1) ayrı kovalardı — `K` eşiği geçtiği
    #       gün /marka/bmw/k/ TEK HARFLİ sayfası sessizce doğacaktı (mimar hükmü: çıplak tek
    #       harf model adı OLMAZ, kanonik ad TAM YAZIMDIR).
    dogrula("K20 ÇIPLAK TEK HARF JETON TAM YAZIMA BİRLEŞİYOR (%d fikstür × 2 taraf; ayrı "
            "kova=%d, tabana ulaşmayan ürün=%d)"
            % (a["tekharf_sayisi"], len(a["tekharf_ayri_kova"]), len(a["tekharf_ulasmayan"])),
            not a["tekharf_sapan"] and not a["tekharf_ulasmayan"]
            and not a["tekharf_ayri_kova"] and not a["tekharf_kaybolan"]
            and not a["tekharf_capa_dusen"] and a["tekharf_sayisi"] > 0,
            "fikstür sapan=%s · ayrı kova (tek harfli sayfa adayı)=%s · tabana ulaşmayan=%s · "
            "kaybolan ürün=%d · DÜŞEN POZİTİF ÇAPA=%s"
            % (a["tekharf_sapan"][:2] or "-", a["tekharf_ayri_kova"][:2] or "-",
               a["tekharf_ulasmayan"][:2] or "-", len(a["tekharf_kaybolan"]),
               a["tekharf_capa_dusen"] or "-"))
    # K21 — BAŞLIK-DOĞAN SAYFA YARGISI: yargısız sayfa DOĞMAZ, envanter BAYATLAMAZ.
    _bi = a["baslik_izin_imza"]
    dogrula("K21 BAŞLIK KOLUNDAN DOĞAN SAYFA KÜMESİ YARGILANMIŞ ENVANTERLE BİREBİR (%d sayfa; "
            "%d kova yargı BEKLİYOR ve DOĞMADI)" % (a["baslik_yayin"], len(a["baslik_bekleyen"])),
            not a["baslik_sizinti"] and not a["baslik_bayat"] and not a["baslik_celiski"]
            and not a["baslik_ciplak_sayi"] and not a["baslik_donanim"]
            and _bi[0] == _bi[1] and _bi[2] == _bi[3],
            "YARGISIZ DOĞMUŞ (SIZINTI)=%s · envanterde var üretimde yok (BAYAT)=%s · "
            "allow/deny çelişkisi=%s · ÇIPLAK SAYI doğmuş=%s · DONANIM kuyruklu doğmuş=%s · "
            "imza=%s beklenen=%s sayı=%d beklenen=%d"
            % (a["baslik_sizinti"][:3] or "-", a["baslik_bayat"][:3] or "-",
               a["baslik_celiski"][:3] or "-", a["baslik_ciplak_sayi"][:3] or "-",
               a["baslik_donanim"][:3] or "-", _bi[0], _bi[1], _bi[2], _bi[3]))
    print("  BILGI BAŞLIK-DOĞAN SAYFA YARGISININ KAYNAĞI: envanter %d · KURAL (H1 şasi/motor "
          "kodu ∪ H3 ayrı araç adı) %d — kural kolu katalog büyüdükçe BAYATLAMAZ"
          % (a["baslik_yayin"] - a["baslik_kural_dogan"], a["baslik_kural_dogan"]))
    if a["baslik_bekleyen"]:
        print("  BILGI MİMAR HÜKMÜ BEKLEYEN KOVA: %d (sayfa DOĞMADI; ürünleri marka "
              "sayfasında ve kendi gerçek model sayfasında duruyor) ilk 5: %s"
              % (len(a["baslik_bekleyen"]), a["baslik_bekleyen"][:5]))
    if a["kusak_aciklamali"]:
        print("  BILGI KUŞAK KATLAMASI ile açıklanan üyelik: %d ürün (muafiyet listesi DEĞİL, "
              "bağımsız kuşak dilbilgisiyle ölçülür; ayrımı K14 doğrular)"
              % a["kusak_aciklamali"])
    # KONTROL: kapı gerçekten AYRIŞMA ölçüyor mu — ölçülen küme boş/dejenere olmasın.
    dogrula("K6 KONTROL: ölçülen çiftlerin çoğu DOLU (dejenere ölçüm değil)",
            a["temiz"] + a["sayfa_dar"] + a["filtre_dar"] + a["capraz"] == a["cift"]
            and a["cift"] >= 50,
            "temiz=%d cift=%d" % (a["temiz"], a["cift"]))

    if envanter:
        e = a["envanter"]
        print("\n  ENVANTER — MODEL TÜRETMESİNİN BÖLDÜĞÜ JETONLAR (%d):" % len(e["bolunen"]))
        print("    %-26s %-12s %-20s %-12s %5s %s"
              % ("HAM JETON", "MARKA", "-> MODEL", "ANAHTAR", "N", "SAYFA"))
        for t, B, kalan, anahtar, n, yayin in e["bolunen"]:
            print("    %-26s %-12s %-20s %-12s %5d %s" % (t, B, kalan, anahtar, n, yayin))
        print("\n  ENVANTER — BİLEŞİK MARKA DİYE KORUNAN (bölünmeyen) JETONLAR (%d):"
              % len(e["korunan"]))
        for t, B, n in e["korunan"]:
            print("    %-26s %-12s %5d ürün (tek parça kalır)" % (t, B, n))
        ke = a["katlama_envanteri"]
        print("\n  ENVANTER — ANA MODELE KATLANAN KUŞAK/VARYANT JETONLARI (%d bölüm, %d ürün):"
              % (len(ke), sum(r[3] for r in ke)))
        print("    %-14s %-20s %-22s %5s %s"
              % ("MARKA", "TABAN MODEL", "KUŞAK BÖLÜMÜ", "N", "KUŞAĞIN SAYFASI"))
        for marka, taban, kusak, n, sayfa_var in ke:
            print("    %-14s %-20s %-22s %5d %s" % (marka, taban, kusak, n, sayfa_var))

    if dokum and a["dokum"]:
        print("\n  SAPAN ÇİFTLER (%d):" % len(a["dokum"]))
        for x in a["dokum"]:
            print("    %-10s %s / %s (canon=%s) sayfa=%d filtre=%d | sayfada yok: %s | filtrede yok: %s"
                  % (x["tur"], x["marka"], x["model"], x["canon"], x["sayfa"], x["filtre"],
                     x["sayfada_yok"], x["filtrede_yok"]))

    toplam = len(gecen) + len(kaldi)
    if kaldi:
        print("\nSONUC: %d/%d iddia KALDI ❌" % (len(kaldi), toplam))
        return 1
    print("\nSONUC: %d/%d iddia GECTI ✔" % (toplam, toplam))
    return 0


# ---------------------------------------------------------------- mutasyon
# (dosya, eski, yeni, beklenen, açıklama)
MUTANTLAR = [
    # --- ÖLDÜRÜCÜ ---
    ("tools/marka_model_build.py",
     "    for x in marka_dizisi:\n        t = (x or \"\").strip()",
     "    for x in marka_dizisi[1:2]:\n        t = (x or \"\").strip()", "KIRMIZI",
     "M1 ÜYELİĞİ marka[1]'E GERİ SABİTLE (ölçülen eski hata) -> sayfa filtreden daralır"),
    ("tools/marka_model_build.py",
     "    return model_kanon.onek_siyir(marka, model_ham, evren)",
     "    return (model_ham or \"\").strip()", "KIRMIZI",
     "M2 MARKA ÖNEKİNİ SIYIRMA: 'Peugeot 206' ayrı kovaya düşer -> sayfa/filtre ayrışır"),
    ("index.html",
     "    if(mk.indexOf(model) !== -1){ return true; }       // BUGÜNKÜ ham eşitlik — asla daralma\n"
     "    var hedef = modelAnahtar(hedefMarka, model);",
     "    return mk.indexOf(model) !== -1;\n"
     "    var hedef = modelAnahtar(hedefMarka, model);", "KIRMIZI",
     "M3 FİLTREYİ HAM EŞİTLİĞE DÖNDÜR (ölçülen eski hata) -> 'F150' vs 'F-150' ayrışır"),
    # 🔴 M4/M5/M7 KUPLAJI KIRAR, DEĞERİ DEĞİL: tabloyu index.html'de değiştiren mutant iki
    # tarafı BİRDEN kaydırdığı için parite bozulmaz (tek kaynağın tam olarak istenen etkisi;
    # ölçüldü — MARKA_ALIAS'ı index.html'den silmek CIFT'i 504->505 yapar ama TEMIZ kalır).
    # Ayrışmayı doğuran şey, BİR tarafın kaynağı okumayı bırakmasıdır; öldürücü mutant onu
    # taklit eder ([[beyan-edilmis-survivor]]: iddia ancak tek başına kırmızı yakılabiliyorsa kanıttır).
    ("tools/model_kanon.py", '    marka = _obje_ayikla(index_html, "MARKA_ALIAS")',
     "    marka = {}", "KIRMIZI",
     "M4 PYTHON TARAFI MARKA ALIAS'INI OKUMAYI BIRAKIR -> sayfa Vauxhall'ı ayırır, filtre katlar"),
    ("tools/model_kanon.py", "    return marka, model", "    return marka, {}", "KIRMIZI",
     "M5 PYTHON TARAFI MODEL ALIAS'INI OKUMAYI BIRAKIR -> F-Series/F-Serisi kovası ikiye bölünür"),
    ("tools/model_kanon.py", '    return _AYIRAC.sub("", t)', "    return t", "KIRMIZI",
     "M7 PYTHON KANONU AYIRAÇ ATMAYI BIRAKIR -> 'F-150'/'F150' sayfada ayrışır, filtrede birleşik"),
    ("index.html", 'return t.replace(/[\\s\\-\\._\\/]/g, "");', "return t;", "KIRMIZI",
     "M6 KANON AYIRAÇ ATMAYI KALDIR -> JS anahtarı Python anahtarından ayrışır"),
    # --- BİLEŞİK MARKA EKSENİ (3 Ağu, KraL denetimi) ---
    # 🔴 KANIT: bu üç mutant EKLENMEDEN ÖNCE batarya bu sınıfı YAKALAMIYORDU — "Volvo Penta"
    # marka+model diye bölünmüşken kapı 7/7 YEŞİL geçti (CIFT=504 TEMIZ=504) ve
    # /marka/volvo/penta/ + 11 benzeri sayfa sessizce doğdu. Ölçülen delik, kapatıldı.
    ("tools/model_kanon.py",
     "    if _marka_norm(t) in evren.bilesik_normlu:\n        return t",
     "    if False:\n        return t", "KIRMIZI",
     "M8 BİLEŞİK MARKA KORUMASINI KALDIR (Python) -> 'Volvo Penta' Volvo+Penta diye bölünür"),
    ("tools/marka_model_build.py",
     "    return marka_mi(t, evren) or model_kanon._marka_norm(t) in KAPALI_MARKA_NORMLU",
     "    return marka_mi(t, evren)", "KIRMIZI",
     "M9 KAPALI MARKA KÜMESİNİ OKUMAYI BIRAK -> marka jetonları (Yanmar/Scion/Mariner) "
     "MODEL sayfası olur"),
    ("index.html", '"Teak Wonder","Twin Disc","Volvo Penta"];',
     '"Teak Wonder","Twin Disc"];', "KIRMIZI",
     "M10 AYNADAN BİR BİLEŞİK MARKAYI DÜŞÜR -> ayna otoriteyle (arama.py) ayrışır"),
    ("index.html", "    if(bilesikMarkaMi(t)){ return t; }        // bileşik marka BÖLÜNMEZ (tek parça kalır)",
     "    if(false){ return t; }", "KIRMIZI",
     "M11 BİLEŞİK MARKA KORUMASINI KALDIR (JS) -> anahtar sondası iki tarafta ayrışır"),
    # --- ROZET EKSENİ (4 Ağu, KraL hükmü) ---
    ("tools/marka_model_build.py",
     "    if (g.get(\"marka\"), g.get(\"canon\")) in ROZET_DISI:\n        return False",
     "    if False:\n        return False", "KIRMIZI",
     "M12 ROZET KURALINI `marka` DİZİSİ YAN YANALIĞINA GEVŞET -> /marka/audi/golf/ + "
     "/marka/volkswagen/octavia/ geri doğar"),
    ("tools/marka_model_build.py",
     "        return set((mk, model_kanon.kanon(md)) for mk, md in arama.ROZET_DISI_CIFT)",
     "        return set()", "KIRMIZI",
     "M13 ROZET TABLOSUNU OKUMAYI BIRAK -> aynı iki sayfa geri doğar (kuplaj ekseni)"),
    # --- KUŞAK/VARYANT KATLAMA EKSENİ (4 Ağu, KraL hükmü) ---
    # 🔴 KANIT: bu mutantlar EKLENMEDEN ÖNCE batarya bu sınıfı GÖRMÜYORDU — katlamayı TEK
    # KAYNAKTAN (index.html) kaldıran mutant pariteyi bozmaz (iki tarafı birden kaydırır) ve
    # 16/16 YEŞİL geçerdi; kural fikstürle çivilenmeseydi katlama sessizce ölürdü.
    ("index.html", "  function kusakSonekMi(w){\n    var t = (w || \"\").toLowerCase();",
     "  function kusakSonekMi(w){\n    if(w){ return false; }\n    var t = (w || \"\").toLowerCase();",
     "KIRMIZI",
     "M14 KATLAMAYI KALDIR (tek kaynak) -> 'Golf 4'/'Astra H' ana modele düşmez, fikstür kırılır"),
    ("index.html", 'var KUSAK_DONANIM = ["gt","gtc","gtd","gti","rs","st"];',
     'var KUSAK_DONANIM = ["gt","gtc","gtd","gti","rs","st","life"];', "KIRMIZI",
     "M15 KATLAMAYI FARKLI ARACA GENİŞLET ('life') -> 'Zafira Life' Zafira'ya katlanır "
     "(fikstür + bağımsız kuşak dilbilgisi iki ayrı eksende kırmızı)"),
    ("index.html", "    var toks = kalan.split(/\\s+/);\n    var i = toks.length;",
     "    var toks = kalan.split(/\\s*/);\n    var i = toks.length;", "KIRMIZI",
     "M16 KELİME SINIRINI KALDIR -> 'Golf' = 'Gol'+'f' diye katlanır (ölçülen 100 yanlış "
     "eşleşme sınıfı geri gelir)"),
    ("index.html", 'var KUSAK_DISI = ["Citroen|Ami 6"];', "var KUSAK_DISI = [];", "KIRMIZI",
     "M17 FARKLI ARAÇ İSTİSNASINI AYNADAN DÜŞÜR -> 1961 Ami 6 parçası 2020 Ami sayfasına "
     "sızar; ayna otoriteyle (arama.py) ayrışır"),
    ("tools/model_kanon.py",
     '    return (_dizi_ayikla(index_html, "KUSAK_DONANIM"),\n'
     '            _dizi_ayikla(index_html, "KUSAK_DISI"),\n'
     '            _dizi_ayikla(index_html, "KUSAK_ESLEME"))',
     '    return ([], _dizi_ayikla(index_html, "KUSAK_DISI"),\n'
     '            _dizi_ayikla(index_html, "KUSAK_ESLEME"))', "KIRMIZI",
     "M18 PYTHON TARAFI DONANIM TABLOSUNU OKUMAYI BIRAKIR -> 'Focus ST' sayfada katlanmaz, "
     "filtrede katlanır (SAYFA_DAR)"),
    ("tools/marka_model_build.py",
     '    ana = g.get("ana", g["urunler"])',
     '    ana = g["urunler"]', "KIRMIZI",
     "M19 ALT BÖLÜM AYRIMINI KALDIR (renderer tek listeye döker) -> kuşak-özel ürün ANA "
     "listeye karışır, kart mükerrer basılır"),
    # --- SIZINTI / DENY / KÜRATÖRLÜ EŞLEME EKSENİ (4 Ağu, mimar hükmü) ---
    # 🔴 KANIT: bu mutantlar EKLENMEDEN ÖNCE batarya bu sınıfı GÖRMÜYORDU — /marka/ford/
    # focus-st/ CANLIDA duruyordu ve kapı 16/16 YEŞİL geçiyordu.
    ("tools/arama.py",
     '    ("Yamaha", "Stage"): "\'Stage 2\' tuning asamasi ifadesi — model degil",\n}',
     '    ("Yamaha", "Stage"): "\'Stage 2\' tuning asamasi ifadesi — model degil",\n'
     '    ("Volkswagen", "T4"): "MUTANT",\n}', "KIRMIZI",
     "M21 KUŞAK SAYFASINI DENY'E AL (Volkswagen T4) -> yayın kümesi tam olarak "
     "volkswagen/t4'ü kaybeder; 'kuşak sayfaları KAPANMAZ' hükmü kırılır"),
    ("tools/arama.py",
     '    ("Ford", "ST"): "donanim/performans paketi (Focus ST, Fiesta ST) — model degil; "\n'
     '                    "urunler ana modelin varyant bolumunde",\n',
     "", "KIRMIZI",
     "M22 `Ford ST` DENIAL'INI KALDIR -> /marka/ford/focus-st/ + /fiesta-st/ geri doğar "
     "(sızıntı ekseni: yayında var, envanterde yok)"),
    ("tools/marka_model_build.py",
     "        return set((mk, model_kanon.kanon(jt)) for mk, jt in arama.MODEL_OLMAYAN_CIFT)",
     "        return set()", "KIRMIZI",
     "M23 DENY TABLOSUNU OKUMAYI BIRAK (kuplaj ekseni; tablo kimliği BOZULMADAN) -> aynı "
     "iki sayfa geri doğar, SIZINTI ekseni TEK BAŞINA kırmızı yakmalı"),
    ("index.html", '"Volkswagen|T1|Transporter"', '"Mercedes|T1|Transporter"', "KIRMIZI",
     "M24 KÜRATÖRLÜ EŞLEMEYİ FARKLI ARACA KAYDIR -> Mercedes T1 (Bremer) VW Transporter'a "
     "katlanır; fikstür + ayna iki ayrı eksende kırmızı"),
    # 🔴 İDDİA EDİLMEYEN EKSEN (dürüst kayıt, [[beyan-edilmis-survivor]]): gruplandir'daki
    # `taban in jetonlar` (ürün zaten TAM eşleşmeyle üye) koruması bugünkü katalogda 0 kez
    # ateşliyor — ölçüldü 4 Ağu: hem TABAN hem VARYANT jetonu taşıyan ürün YOK. Kaldıran
    # mutant DAVRANIŞI DEĞİŞTİRMEZ (eşdeğer mutant), o yüzden bataryaya KONMADI ve "mükerrer
    # kart engelleniyor" diye bir iddia SAYILMIYOR. Veri o sınıfı üretmeye başlarsa K14'ün
    # bölüm-ayrıklığı ölçümü onu yakalar (kesitler AYRIK olmalı).
    # --- ÇAPRAZ-MARKA (ROZET) TUTARLILIK EKSENİ — K19 (4 Ağu, mimar hükmü) ---
    # 🔴 KANIT: bu mutantlar EKLENMEDEN ÖNCE batarya bu sınıfı GÖRMÜYORDU — `(Peugeot,
    # Berlingo)` 9 ürünle CANLIDA duruyordu ve kapı 19/19 YEŞİL geçiyordu. Rozet ihlali
    # ancak bir insan ana sayfada görünce yakalanabiliyordu.
    ("tools/arama.py",
     '    ("Peugeot", "Berlingo"): "Berlingo Citroen rozetidir; Peugeot\'daki karsiligi Partner/"\n'
     '                             "Rifter — gercek sayfa /marka/citroen/berlingo/",\n',
     "", "KIRMIZI",
     "M25 `(Peugeot, Berlingo)` ÇİFTİNİ SAYFA DOĞURACAK HALE GETİR (deny'den düşür) -> "
     "çapraz-marka çifti YARGISIZ kalır; K19 sızıntıyı sayfa DOĞMADAN yakalamalı"),
    ("tools/arama.py",
     '    "Peugeot|boxer": ("ROZET", "Peugeot Boxer gercek rozet (SEVEL ucuzu; her marka KENDI adiyla)"),\n',
     "", "KIRMIZI",
     "M26 ENVANTERDEN BİR ÇAPRAZ ÇİFTİ DÜŞÜR -> allow'da da deny'de de olmayan çift doğar "
     "(yargısız = sessiz sayfa); kimlik imzası da kayar"),
    ("tools/arama.py",
     '    "Citroen|berlingo": ("ROZET", "Berlingo Citroen\'in kendi rozeti"),',
     '    "Citroen|berlingo": ("ROZET", "Berlingo Citroen\'in kendi rozeti"),\n'
     '    "Peugeot|xyzyok": ("ROZET", "MUTANT — uretimde KARSILIGI YOK"),', "KIRMIZI",
     "M27 ENVANTERE ÜRETİMDE KARŞILIĞI OLMAYAN ÇİFT EKLE -> envanter BAYAT (küme birebir "
     "değil); sayı ölçütü olsaydı bu sapma gizlenirdi ([[hukum-yanlis-birimde]])"),
    # 🔴 ÇAPA İKİ SATIRLI: tek satırlık hâli bu listenin KENDİSİNDE de geçiyordu (kendine
    # atıf) ve mutant hangi kopyaya vurduğu belirsiz kalırdı.
    ("tools/model-uyelik-kapisi.py",
     '                continue\n'
     '            if _g.get("birincil") and len(_g["urunler"]) >= mm.ESIK:\n'
     '                capraz_aday.setdefault',
     '                continue\n'
     "            if mm.yayimlanir_mi(_g):\n"
     '                capraz_aday.setdefault', "KIRMIZI",
     "M28 ÖLÇÜTÜ 'SAYFA DOĞDU MU'YA ÇEVİR -> deny'e alınan çift ölçümden DÜŞER, karşısındaki "
     "gerçek rozet tek başına kalır ve tablo KENDİ kanıtını siler (totoloji koruması)"),
    # --- ÇIPLAK TEK HARF (SINIF 1) EKSENİ — K20 (4 Ağu, mimar hükmü) ---
    # 🔴 KANIT: bu mutantlar EKLENMEDEN ÖNCE batarya bu sınıfı GÖRMÜYORDU — BMW `K` (1 ürün)
    # ile `K Serisi` (1 ürün) AYRI kovalardı ve kapı 20/20 YEŞİL geçiyordu; `K` kovası ESIK'i
    # geçtiği gün /marka/bmw/k/ TEK HARFLİ sayfası SESSİZCE doğacaktı.
    ("index.html", 'var MODEL_ALIAS = {"BMW|k":"kserisi","Ford|fseries":"fserisi"};',
     'var MODEL_ALIAS = {"Ford|fseries":"fserisi"};', "KIRMIZI",
     "M29 ÇIPLAK TEK HARF BİRLEŞMESİNİ KALDIR -> `K` yeniden AYRI kova olur (tek harfli "
     "sayfa adayı), ürün TAM YAZIM kovasına ULAŞMAZ; K20 TEK BAŞINA kırmızı yakmalı"),
    ("tools/marka_model_build.py", '    ("BMW", "kserisi"): "K Serisi",\n', "", "KIRMIZI",
     "M30 KANONİK GÖSTERİM ZORLAMASINI DÜŞÜR -> 1-1 sıklıkta alfabetik tie-break kazanır ve "
     "kovanın adı TEK HARFE ('K') düşer; birleşme doğru, AD yanlış olurdu"),
    # --- ÇAPRAZ-MARKA `GS` HÜKMÜNÜN KANITI (SINIF 1 ön ölçümü) ---
    # ÖLÇÜLDÜ (4 Ağu, 17.962 ürün): BMW `GS` 13 ürünle YAYINDA, Citroën `GS` 1 ürün (ESIK=3
    # ALTINDA) -> `gs` bugün ÇAPRAZ bir çift DEĞİL. Bu yüzden ROZET_CAPRAZ_IZINLI'ye bir
    # `BMW|gs` girişi yazmak ÖLÜ giriştir ve envanteri BAYATLATIR. Mutant tam da bunu yapar:
    # hüküm ("bugün allow yazma; K19 ileriye dönük bekçidir") böylece ÇALIŞTIRILABİLİR olur.
    ("tools/arama.py", '    "Volkswagen|golf": ("ROZET", "Golf VW\'nin kendi rozeti"),',
     '    "Volkswagen|golf": ("ROZET", "Golf VW\'nin kendi rozeti"),\n'
     '    "BMW|gs": ("ROZET", "MUTANT — Citroen GS 1 urun, ESIK altinda: capraz cift DEGIL"),',
     "KIRMIZI",
     "M31 `GS` İÇİN ÖLÜ ALLOW GİRİŞİ YAZ -> envanter bayat (küme birebir değil); K19 TEK "
     "BAŞINA kırmızı yakar. Ön ölçümün hükmünün kanıtı: GS allow girişi BUGÜN yazılamaz"),
    # --- BAŞLIK KOLU / YARGI KAPISI EKSENİ — K21 + K4 (5 Ağu, mimar hükmü) ---
    # 🔴 KANIT: bu mutantlar EKLENMEDEN ÖNCE batarya bu sınıfı GÖRMÜYORDU — başlık kolu
    # 4.046 yeni üyelik ve 173 yeni sayfa açıyor; yargı kapısı ya da tehlike koruması
    # sessizce ölseydi kapı YEŞİL yanmaya devam ederdi.
    # 🔴 ÇAPA 6 Ağu'da TAZELENDİ: `yayimlanir_mi` yargı bloğu H1/H3 kural kollarını da
    # okuyacak şekilde yeniden yazıldı; eski çapa 0 eşleşmeye düşmüştü ve eksen SESSİZCE
    # ölçülmez olmuştu ([[mutasyon-kaniti-yeniden-uretilebilir]]).
    ("tools/marka_model_build.py",
     '    if g.get("baslik_dogan") and not baslik_yargisi_var_mi(\n'
     '            g.get("marka"), g.get("canon"), g.get("display") or g.get("canon")):\n'
     "        return False",
     "    if False:\n        return False", "KIRMIZI",
     "M38 YARGI KAPISINI KALDIR -> mimar hükmü BEKLEYEN 340 kovanın eşiği geçenleri sayfa "
     "olur; K21 SIZINTI eksenini TEK BAŞINA kırmızı yakmalı"),
    ("tools/arama.py", '    ("Suzuki", "Escudo"): "arac/motosiklet model adi",\n', "",
     "KIRMIZI",
     "M39 ALLOW ENVANTERİNDEN BİR GİRİŞ DÜŞÜR -> /marka/suzuki/escudo/ sessizce ölür; "
     "K21 BAYAT ekseni (küme birebir değil) + kimlik imzası kırmızı yakar"),
    ("tools/marka_model_build.py",
     '    j = "".join(_kelimeler(jeton))\n    return (not j) or len(j) <= 3 or j.isdigit()',
     '    j = "".join(_kelimeler(jeton))\n    return not j', "KIRMIZI",
     "M40 TEHLİKE SINIFI KORUMASINI DÜŞÜR -> çıplak `5`/`86`/`C5` başlıkta eşleşir; kapının "
     "BAĞIMSIZ başlık dilbilgisi bunu açıklayamaz -> K4 yanlış-pozitif KIRMIZI"),
    # --- KONTROL (YEŞİL bekleniyor) ---
    ("tools/arama.py",
     '    ("Audi", "Q3"): "arac/motosiklet model adi",\n'
     '    ("Audi", "TT"): "arac/motosiklet model adi",',
     '    ("Audi", "TT"): "arac/motosiklet model adi",\n'
     '    ("Audi", "Q3"): "arac/motosiklet model adi",', "YESIL",
     "K21 KONTROL: allow envanterini YENİDEN SIRALA -> küme, kimlik ve davranış AYNI "
     "(daima-kırmızı bir K21 M38/M39'u da geçerdi; kontrol bunu ayırt eder)"),
    ("index.html", 'var MODEL_ALIAS = {"BMW|k":"kserisi","Ford|fseries":"fserisi"};',
     'var MODEL_ALIAS = {"Ford|fseries":"fserisi","BMW|k":"kserisi"};', "YESIL",
     "K20 KONTROL: MODEL_ALIAS'ı YENİDEN SIRALA -> tablo ve davranış AYNI (daima-kırmızı bir "
     "K20 M29/M30'u da geçerdi; kontrol bunu ayırt eder)"),
    ("tools/arama.py",
     '    "Subaru|brz": ("ROZET", "Subaru BRZ gercek rozet"),\n'
     '    "Citroen|c1": ("ROZET", "Citroen C1 gercek rozet"),',
     '    "Citroen|c1": ("ROZET", "Citroen C1 gercek rozet"),\n'
     '    "Subaru|brz": ("ROZET", "Subaru BRZ gercek rozet"),', "YESIL",
     "K19 KONTROL: çapraz envanteri YENİDEN SIRALA -> küme ve kimlik AYNI, davranış AYNI "
     "(daima-kırmızı bir K19 M25-M28'i de geçerdi; kontrol bunu ayırt eder)"),
    ("tools/marka_model_build.py",
     '            g["kusak_bolum"] = sorted(bolumler,\n'
     '                                      key=lambda b: (-len(b["urunler"]), b["display"]))',
     '            g["kusak_bolum"] = sorted(bolumler, key=lambda b: b["display"])', "YESIL",
     "K4 KONTROL: kuşak bölümlerinin SIRASI değişir, AYRIM değişmez -> iddia bozulmamalı "
     "(eksen sıralamaya değil ayrıma duyarlı olmalı)"),
    ("tools/arama.py",
     '    ("Ford", "ST Line"): "gorunum paketi — ST ile ayni sinif, ayri yazim",\n'
     '    ("Ford", "EcoBoost"): "motor ailesi (1.0/1.5/2.3 EcoBoost) — arac modeli degil",',
     '    ("Ford", "EcoBoost"): "motor ailesi (1.0/1.5/2.3 EcoBoost) — arac modeli degil",\n'
     '    ("Ford", "ST Line"): "gorunum paketi — ST ile ayni sinif, ayri yazim",', "YESIL",
     "K5 KONTROL: deny tablosunu YENİDEN SIRALA -> küme ve kimlik AYNI, davranış AYNI "
     "(daima-kırmızı bir kapı M21/M22'yi de geçerdi; kontrol bunu ayırt eder)"),
    # 🔴 ESKİDEN KONTROLDÜ, ARTIK ÖLDÜRÜCÜ (4 Ağu): eşik SAYFA EVRENİNİ kaydırır ve donmuş
    # envanter ekseni (K16) bunu GÖRÜR — parite (K1/K2/K3) YEŞİL kalırken. Mutant tam da bu
    # ayrımı kanıtlar: "sayfa sayısı değişti ama parite bozulmadı" artık sessiz DEĞİL.
    # ⚠️ BAĞIMLILIK (dürüst kayıt): bugün envanterdeki 17 kovanın 8'i TAM eşikte (3 ürün)
    # duruyor; katalog hepsini 4+'a taşırsa bu mutant EŞDEĞERE düşer ve batarya "beklentiyi
    # tutmayan" diye KENDİ raporlar — o gün yerine başka bir küme-kaydıran mutant yazılır.
    ("tools/marka_model_build.py", "ESIK = 3", "ESIK = 4", "KIRMIZI",
     "M25 EŞİĞİ YÜKSELT -> yayımlanan değiştirici-şekilli kova kümesi DARALIR (8 sayfa "
     "sessizce ölür); parite YEŞİL kalır, donmuş envanter ekseni KIRMIZI yakar"),
    ("tools/cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "K2 İLGİSİZ: indeks sürüm alanı model üyeliğinde rol OYNAMAZ"),
    ("index.html", 'var MODEL_TR = {"ı":"i"', 'var MODEL_TR = {"Û":"u","ı":"i"', "YESIL",
     "K3 İLGİSİZ: küçültmeden SONRA hiç görülmeyen büyük harf girdisi davranışı DEĞİŞTİRMEZ"),
]


def _kok_kur(tmp):
    """tools/ + index.html KOPYALANIR (mutant oraya uygulanır), gerisi SYMLINK."""
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in os.listdir(os.path.join(GERCEK_KOK, "tools")):
        k = os.path.join(GERCEK_KOK, "tools", ad)
        if os.path.isfile(k):
            shutil.copy2(k, os.path.join(tmp, "tools", ad))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))


def kendini_test():
    print("MUTASYON — model üyeliği (mutant KOPYAYA uygulanır; gerçek ağaç DEĞİŞMEZ)")
    basarisiz, olcum = [], []
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = tempfile.mkdtemp(prefix="model-uyelik-mut-")
        try:
            _kok_kur(tmp)
            yol = os.path.join(tmp, *dosya.split("/"))
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            # 🔴 ÇAPA TAM BİR KEZ EŞLEŞMELİ (4 Ağu, kardeş harness ile HİZALAMA).
            # ÖNCEDEN yalnız `eski not in metin` bakılıyordu; tools/cip-indeks-test.py ise
            # `count(...) == 1` istiyordu. İKİZ TANIM: bugün zararsız, yarın biri gevşeyince
            # sessizce ayrışır ([[ikiz-tanim-sessiz-ayrisma]]). ÖLÇÜLDÜ: K19 mutantının tek
            # satırlık çapası bu dosyada 2 kez geçiyordu (MUTANTLAR listesinin KENDİSİNDE de)
            # ve gevşek kontrol bunu SESSİZCE geçiriyordu — mutantın hangi kopyaya vurduğu
            # belirsizdi. Çapa kayması "geçti" DEĞİL, o eksen ÖLÇÜLMEMİŞ demektir.
            sayi = metin.count(eski)
            if sayi != 1:
                print("  HATA M%02d: mutant ÇAPASI %s (%d eşleşme, %s) | EKSEN ÖLÇÜLMEDİ -> %s"
                      % (i, "BULUNAMADI" if sayi == 0 else "ÇOK EŞLEŞTİ", sayi, dosya, aciklama))
                basarisiz.append("M%02d capa %d eslesme" % (i, sayi))
                continue
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.join(tmp, "tools", "model-uyelik-kapisi.py"),
                                "--kok", tmp], capture_output=True, text=True, timeout=1800)
            kirmizi = [s for s in (p.stdout or "").splitlines() if s.strip().startswith("KALDI")]
            # 🔴 ÇÖKME KIRMIZIYLA KARIŞMAZ: kabul ölçütü çıkış kodu DEĞİL, ölçülen iddia + işaret.
            if p.returncode not in (0, 1) or (p.returncode == 1 and not kirmizi):
                print("  HATA M%02d [%s] %s -> COKME/OLCULEMEDI (rc=%d) | %s"
                      % (i, beklenen, dosya, p.returncode, aciklama))
                print("        " + ((p.stderr or p.stdout or "").strip().splitlines() or [""])[-1][:180])
                basarisiz.append("M%02d [cokme]" % i)
                continue
            gercek = "YESIL" if p.returncode == 0 else "KIRMIZI"
            ok = gercek == beklenen
            sayi = [s for s in (p.stdout or "").splitlines() if "CIFT=" in s]
            print("  %-4s M%02d [%s] -> %s (%d iddia kırmızı) | %s"
                  % ("OK" if ok else "HATA", i, beklenen, gercek, len(kirmizi), aciklama))
            if sayi:
                print("        " + sayi[0].strip()[:140])
            for s in kirmizi[:2]:
                print("        " + s.strip()[:150])
            olcum.append((i, beklenen, gercek, len(kirmizi)))
            if not ok:
                basarisiz.append("M%02d" % i)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    oldurucu = sum(1 for _i, b, _g, _n in olcum if b == "KIRMIZI")
    kontrol = sum(1 for _i, b, _g, _n in olcum if b == "YESIL")
    print("\nMUTASYON: %d öldürücü + %d kontrol koştu · beklentiyi tutmayan: %d %s"
          % (oldurucu, kontrol, len(basarisiz), basarisiz or ""))
    return 1 if basarisiz else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK)
    ap.add_argument("--modul", default=None, help="marka_model_build.py yerine BAŞKA modül")
    ap.add_argument("--dokum", action="store_true")
    ap.add_argument("--envanter", action="store_true",
                    help="model türetmesinin BÖLDÜĞÜ ve bileşik diye KORUDUĞU jetonlar")
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    try:
        return kabul(a.kok, a.dokum, a.modul, a.envanter)
    except Olculemedi as e:
        print("\nSONUC: OLCULEMEDI ❓  %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
