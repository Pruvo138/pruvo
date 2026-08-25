#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IKIZ-TANIM DRIFT KAPISI — tools/marka_katla.py ile index.html'in MARKA KURATORLUGU
blogu DAVRANIS bazinda ayni mi?

  kosum:  python3 tools/marka-katla-ikiz-kapisi.py
  ortam:  PRUVO_MARKA_KATLA  (olculecek port dosyasi; mutasyon kosumu bunu kullanir)
  cikis:  0 gecti · 1 iddia kirmizi · 3 OLCULEMEDI (fail-closed: node yok / capa yok)

─── NIYE VAR (olculmus kusur, 10 Agu 2026) ────────────────────────────────────
tools/marka_katla.py docstring'inde "index.html MARKA KURATORLUGU blogunun BIREBIR
karsiligi" yaziyordu ve DEGILDI, iki eksende:
  1. Aksan kolu ELLE bir listeydi (`é/è/ë/ä`); site 6 Agu'da NFD + birlesen-isaret
     (U+0300-U+036F) GENEL kuralina gecmisti. Listede olmayan HER aksan sessizce
     ayrisiyordu: caron "Skoda", tilde "Senor", halka "Akerman", akut, macron, breve.
  2. `MARKA_ALIAS` (Vauxhall -> Opel) portta HIC YOKTU: site "Vauxhall"i Opel kalemine
     indiriyor, port ayri birakiyordu.
Bu fonksiyon `marka_kanon` D1 kolonunu besliyor — ayrisma HATA da LOG da uretmez.
AYNI SINIF bu evde UCUNCU tekrardi ([[ikiz-tanim-sessiz-ayrisma]]), o yuzden cozum
"daha dikkatli port et" DEGIL: iddia CALISTIRILABILIR bir kapiya baglandi.

─── BU KAPININ SEKLI ──────────────────────────────────────────────────────────
Karsilastirma METIN degil DAVRANIS eksenindedir (index.html'de yorum/bosluk degisince
yanmaz; gurultulu kapi sokulur). Sitenin gövdesi KOSUM ANINDA index.html'den SUSLU
PARANTEZ SAYARAK kesilir (regex ile DEGIL: ic ice suslu iceren bir govdede regex
sessizce yanlis yerde biter) ve `node` alt-sureciyle GERCEKTEN calistirilir — yani
kopyaya degil SITENIN KENDISINE bakilir.

Olculen ayri iddialar:
  (A)  KATLAMA IKIZI     — korpustaki HER degerde site.markaKatla == port.markaKatla
  (A2) KORPUS AYIRT EDICI— korpusta gercekten katlanan deger sayisi esigi asiyor mu
                           (asmiyorsa A vakumda kosuyordur)
  (B)  NORM IKIZI        — korpustaki HER degerde site.markaNorm == port.markaNorm
  (C)  AKSAN KURALI      — alti aksan vakasinin BEKLENEN ASCII karsiligi PINLENMIS
                           (ikiz karsilastirmasi tek basina totolojiye kayabilir: iki
                            taraf BIRLIKTE bozulursa yesil kalirdi)
  (C2) VAKALAR AYIRT EDICI— o alti vaka ESKI elle-liste kuraliyla AYRISMALI, yoksa
                           vakalar bu kusur sinifini TEMSIL ETMIYOR demektir
  (D)  ALIAS             — site MARKA_ALIAS tablosunun HER girisi iki tarafta da ayni
                           katlaniyor + port tabloyu index.html'den TURETIYOR
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX = os.path.join(ROOT, "index.html")
URUNLER = os.path.join(ROOT, "urunler.json")
PORT_YOL = os.environ.get("PRUVO_MARKA_KATLA") or os.path.join(TOOLS, "marka_katla.py")

# index.html'deki sozlesmeli isaret satirlari (site tarafinda "marker satirini
# degistirme" notuyla korunuyor; marka-liste-test.py de AYNI iki satiri kullanir).
BLOK_BAS = "// --- MARKA KÜRATÖRLÜĞÜ BAŞ"
BLOK_SON = "// --- MARKA KÜRATÖRLÜĞÜ SON ---"
NORM_CAPA = "  function norm(s){"

# Canli korpus tavani. Bugun katalogda 2.582 tekil ham marka degeri var (10 Agu 2026),
# yani tavan HENUZ CARPMIYOR — carparsa kapi bunu AYRICA basar (sessiz kirpma yasak).
URUNLER_TAVAN = 5000
AYIRT_EDICI_ESIK = 100  # (A2) korpusta katlanmasi gereken en az deger sayisi

# 🔴 ALTI AKSAN VAKASI — her satir AYRI bir birlesen-isaret sinifi. Eski elle liste
# (`[éèë]` + `ä`) bunlarin HICBIRINI gormuyordu; NFD genel kurali ALTISINI DE goruyor.
# Beklenen deger BURAYA SABIT yazilir (bkz C/C2 gerekcesi docstring'de).
AKSAN_VAKALARI = [
    ("Škoda", "skoda"),              # caron        U+030C
    ("Señor", "senor"),              # tilde        U+0303
    ("Åkerman", "akerman"),          # ustte halka  U+030A
    ("Peugeot Ćar", "peugeot car"),  # C-akut       U+0301
    ("Nū", "nu"),                    # macron       U+0304
    ("Mănana", "manana"),            # breve        U+0306
]

# Elle yazilmis sinir vakalari: aksan ikizleri, Turkce I, ayirac ucgeni, alt-dize
# tuzaklari (MAN/Haval/Rover/3M — bkz marka-panel-test.py (f) bolumu), bos/uzun/cop.
SINIR = [
    "", " ", "  ", "-", "3", "0",
    "Citroën", "Citroen", "CITROËN", "Citroën C5", "Škoda", "Skoda", "SKODA",
    "Black+Decker", "Black & Decker", "Black and Decker", "BLACK+DECKER",
    "Kärcher", "Karcher", "KÄRCHER", "DeLonghi", "Raspberry Pi", "Raspberry Pi 4",
    "Vauxhall", "VAUXHALL", "vauxhall", "Vauxhall Astra", "Vauxhall-Astra",
    "Opel", "Opel Astra", "Opelx",
    "MAN", "MAN TGA", "Mandalı", "Mandali", "Havalandırma", "Haval",
    "Land Rover", "Land Rover 90", "Rover", "Rover 75", "43mm", "3M",
    "İkea", "IKEA", "Ikea", "ıkea", "MINI", "Mini", "Miniatur",
    "Mercedes-Benz", "Mercedes Benz", "Mercedes-AMG", "Mazda 3", "Mazda3",
    "Toyota 86", "Volvo Penta", "Volvo-Penta", "Peugeot 5008", "Renault 5 E-Tech",
    "Arçelik", "ARÇELİK", "arçelik", "jant kapağı", "menteşe",
    "yok böyle bir marka", "x" * 300,
]

_gecen = 0
_dusen = 0


def kontrol(ad, sonuc, detay=""):
    global _gecen, _dusen
    if sonuc:
        _gecen += 1
        print("   PASS  %s" % ad)
    else:
        _dusen += 1
        print("   FAIL  %s" % ad)
        if detay:
            for satir in str(detay).rstrip().split("\n"):
                print("         %s" % satir)


def olculemedi(mesaj):
    """FAIL-CLOSED: kaynak ulasilamazsa SESSIZ YESILE dusme. 'olcemedim' ile
    'kural degismedi' ASLA karistirilmamali."""
    print("\nÖLÇÜLEMEDİ (fail-closed KIRMIZI): %s" % mesaj)
    sys.exit(3)


# ─── Site govdesini index.html'den kes ───────────────────────────────────────
def govde_kes(src, capa):
    """`capa` ile baslayan fonksiyon govdesini SUSLU PARANTEZ SAYARAK kes."""
    bas = src.find(capa)
    if bas == -1:
        return None
    i = src.find("{", bas)
    if i == -1:
        return None
    derinlik = 0
    while i < len(src):
        c = src[i]
        if c == "{":
            derinlik += 1
        elif c == "}":
            derinlik -= 1
            if derinlik == 0:
                return src[bas:i + 1]
        i += 1
    return None


def blok_kes(src):
    bas = src.find(BLOK_BAS)
    if bas == -1:
        return None
    son = src.find(BLOK_SON, bas)
    if son == -1:
        return None
    return src[bas:son + len(BLOK_SON)]


NODE = shutil.which("node")
if not NODE:
    olculemedi("`node` binary'si YOK — site gövdesi çalıştırılamıyor.\n"
               "  ÇÖZÜM: node kur (brew install node) ve tekrar koş.")
if not os.path.exists(INDEX):
    olculemedi("index.html bulunamadı: %s" % INDEX)

_src = open(INDEX, encoding="utf-8").read()
_norm_govde = govde_kes(_src, NORM_CAPA)
if _norm_govde is None:
    olculemedi("index.html'de norm() çapası bulunamadı (%r).\n"
               "  Site tarafı tanımı değiştiyse ÇAPAYI güncelle — sessizce eski "
               "gövdeyle devam ETME." % NORM_CAPA)
_kurator = blok_kes(_src)
if _kurator is None:
    olculemedi("index.html'de MARKA KÜRATÖRLÜĞÜ BAŞ/SON işaretleri bulunamadı "
               "(%r / %r)." % (BLOK_BAS, BLOK_SON))

_tmpd = tempfile.mkdtemp(prefix="marka-katla-ikiz-")
_surucu = os.path.join(_tmpd, "site.mjs")
with open(_surucu, "w", encoding="utf-8") as f:
    f.write('import fs from "node:fs";\n')
    f.write(_norm_govde + "\n\n")
    f.write(_kurator + "\n\n")
    f.write(
        'const mod = process.argv[2];\n'
        'if (mod === "meta") {\n'
        '  console.log(JSON.stringify({ taninmis: TANINMIS_MARKALAR, alias: MARKA_ALIAS }));\n'
        '} else {\n'
        '  const korpus = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));\n'
        '  console.log(JSON.stringify({\n'
        '    katla: korpus.map((v) => markaKatla(v)),\n'
        '    norm: korpus.map((v) => markaNorm(v)),\n'
        '  }));\n'
        '}\n')


def node_kos(*argv):
    r = subprocess.run([NODE, _surucu] + list(argv), capture_output=True, text=True)
    if r.returncode != 0:
        olculemedi("site gövdesi node ile çalıştırılamadı (rc=%d):\n%s\n%s"
                   % (r.returncode, r.stdout[-2000:], r.stderr[-2000:]))
    try:
        return json.loads(r.stdout)
    except Exception as e:
        olculemedi("node çıktısı JSON değil (%s): %s" % (e, r.stdout[-500:]))


# ─── Port modulu ─────────────────────────────────────────────────────────────
if not os.path.exists(PORT_YOL):
    olculemedi("ölçülecek port dosyası yok: %s" % PORT_YOL)
try:
    _spec = importlib.util.spec_from_file_location("marka_katla_olculen", PORT_YOL)
    port = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(port)
except Exception as e:
    olculemedi("port modülü yüklenemedi (%s): %s: %s" % (PORT_YOL, type(e).__name__, e))

print("KAYNAK  site  : %s" % INDEX)
print("KAYNAK  port  : %s" % PORT_YOL)

# ─── Korpus ──────────────────────────────────────────────────────────────────
_meta = node_kos("meta")
SITE_TANINMIS = _meta["taninmis"]
SITE_ALIAS = _meta["alias"]

KALIPLAR = [
    lambda b: b,                 # markanin kendisi
    lambda b: b.upper(),         # "KIA" ikizi
    lambda b: b.lower(),
    lambda b: b + " 3",          # BOSLUK onekli -> KATLANIR
    lambda b: b + "-Benz",       # TIRE onekli   -> KATLANIR
    lambda b: b + " Penta",
    lambda b: b + "X",           # AYIRACSIZ     -> KATLANMAZ (negatif vaka)
    lambda b: "Süper " + b,      # marka SONDA   -> KATLANMAZ (negatif vaka)
]
yapisal = [k(b) for b in SITE_TANINMIS for k in KALIPLAR]

alias_vakalari = []
for _k, _v in SITE_ALIAS.items():
    alias_vakalari += [_k, _k.upper(), _k.lower(), _k + " Astra", _k + "-Astra", _v]

canli = []
canli_tavan_carpti = False
canli_hata = None
try:
    with open(URUNLER, encoding="utf-8") as f:
        _urunler = json.load(f)
    _gorulen = set()
    for _p in _urunler:
        for _m in (_p.get("marka") or []):
            if isinstance(_m, str) and _m not in _gorulen:
                _gorulen.add(_m)
                canli.append(_m)
    _canli_tekil = len(canli)
    if len(canli) > URUNLER_TAVAN:
        canli_tavan_carpti = True
        canli = canli[:URUNLER_TAVAN]
except Exception as e:
    canli_hata = "%s: %s" % (type(e).__name__, e)
    _canli_tekil = 0

korpus = []
_g = set()
for v in (list(AKSAN_VAKALARI and [a for a, _b in AKSAN_VAKALARI]) + SINIR +
          alias_vakalari + yapisal + canli):
    if v not in _g:
        _g.add(v)
        korpus.append(v)

_json_korpus = os.path.join(_tmpd, "korpus.json")
with open(_json_korpus, "w", encoding="utf-8") as f:
    json.dump(korpus, f, ensure_ascii=False)
_site = node_kos("eval", _json_korpus)
SITE_KATLA = dict(zip(korpus, _site["katla"]))
SITE_NORM = dict(zip(korpus, _site["norm"]))

print("KORPUS  %d tekil değer  (aksan %d · sınır %d · alias %d · yapısal %d · canlı %d)"
      % (len(korpus), len(AKSAN_VAKALARI), len(SINIR), len(alias_vakalari),
         len(yapisal), len(canli)))
if canli_tavan_carpti:
    print("        ⚠ CANLI KORPUS TAVANA ÇARPTI: urunler.json'da %d tekil ham marka "
          "değeri var, ilk %d alındı (sessiz kırpma DEĞİL — raporda belirt)."
          % (_canli_tekil, URUNLER_TAVAN))

print("\n(A) KATLAMA İKİZİ — site.markaKatla == port.markaKatla")
_ayrisan = []
for v in korpus:
    s, p = SITE_KATLA[v], port.markaKatla(v)
    if s != p:
        _ayrisan.append((v, s, p))
kontrol("korpusun TAMAMINDA birebir (%d/%d)" % (len(korpus) - len(_ayrisan), len(korpus)),
        not _ayrisan,
        "\n".join("%r  site=%r  port=%r" % a for a in _ayrisan[:15]) +
        ("\n… %d tane daha" % (len(_ayrisan) - 15) if len(_ayrisan) > 15 else "") +
        "\nÇÖZÜM: tools/marka_katla.py markaKatla/markaNorm gövdesi site ile AYRIŞTI.")

print("(A2) KORPUS AYIRT EDİCİ Mİ (iddia vakumda mı koşuyor?)")
_katlanan = [v for v in korpus if SITE_KATLA[v] != v]
kontrol("site.markaKatla(v) != v olan değer sayısı >= %d (ölçülen %d)"
        % (AYIRT_EDICI_ESIK, len(_katlanan)), len(_katlanan) >= AYIRT_EDICI_ESIK)

print("(B) NORM İKİZİ — site.markaNorm == port.markaNorm")
_ayrisanN = []
for v in korpus:
    s, p = SITE_NORM[v], port.markaNorm(v)
    if s != p:
        _ayrisanN.append((v, s, p))
kontrol("korpusun TAMAMINDA birebir (%d/%d)" % (len(korpus) - len(_ayrisanN), len(korpus)),
        not _ayrisanN,
        "\n".join("%r  site=%r  port=%r" % a for a in _ayrisanN[:15]) +
        ("\n… %d tane daha" % (len(_ayrisanN) - 15) if len(_ayrisanN) > 15 else "") +
        "\nÇÖZÜM: markaNorm aksan kolu GENEL KURAL olmalı (NFD + U+0300-U+036F silme), "
        "elle liste DEĞİL.")

print("(C) AKSAN KURALI — PİNLENMİŞ beklenen ASCII karşılığı (totoloji kırılır)")
_sapan = []
for ham, beklenen in AKSAN_VAKALARI:
    s, p = SITE_NORM[ham], port.markaNorm(ham)
    if s != beklenen or p != beklenen:
        _sapan.append((ham, beklenen, s, p))
kontrol("%d/%d vaka beklenen ASCII karşılığını veriyor (caron·tilde·halka·akut·macron·breve)"
        % (len(AKSAN_VAKALARI) - len(_sapan), len(AKSAN_VAKALARI)), not _sapan,
        "\n".join("%r  beklenen=%r  site=%r  port=%r" % a for a in _sapan))


def _eski_elle_kural(s):
    """10 Ağu ÖNCESİ markaNorm'un BİREBİR kendisi — KASTEN KOPYA: neyin geri gelmesini
    yasakladığımızı gösteren referans. C2 bunu ölçüt olarak kullanır."""
    n = (s or "").lower()
    n = (n.replace("ı", "i").replace("İ", "i")
          .replace("ç", "c").replace("ğ", "g").replace("ö", "o")
          .replace("ş", "s").replace("ü", "u").replace("â", "a").replace("î", "i"))
    n = n.replace("é", "e").replace("è", "e").replace("ë", "e").replace("ä", "a")
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    return re.sub(r"\s+", " ", n).strip()


print("(C2) VAKALAR AYIRT EDİCİ Mİ — eski elle-liste kuralıyla AYRIŞMALI")
_ayni = [ham for ham, _b in AKSAN_VAKALARI if _eski_elle_kural(ham) == port.markaNorm(ham)]
kontrol("%d/%d vaka ESKİ elle-liste kuralıyla ayrışıyor"
        % (len(AKSAN_VAKALARI) - len(_ayni), len(AKSAN_VAKALARI)), not _ayni,
        ("ESKİ kuralla AYNI çıkan vaka(lar): %s — bu vakalar kusur sınıfını TEMSİL "
         "ETMİYOR." % ", ".join(repr(v) for v in _ayni)) if _ayni else "")

print("(D) MARKA_ALIAS — site tablosunun HER girişi iki tarafta da aynı katlanıyor")
kontrol("site MARKA_ALIAS tablosu BOŞ DEĞİL (%d giriş) — iddia vakumda değil"
        % len(SITE_ALIAS), len(SITE_ALIAS) > 0)
kontrol("port MARKA_ALIAS == site MARKA_ALIAS (port tabloyu index.html'den TÜRETİYOR)",
        dict(getattr(port, "MARKA_ALIAS", {})) == dict(SITE_ALIAS),
        "port=%r  site=%r" % (dict(getattr(port, "MARKA_ALIAS", {})), dict(SITE_ALIAS)))
_alias_sapan = []
for _k, _v in SITE_ALIAS.items():
    for _giris in (_k, _k.upper(), _k.lower(), _k + " Astra", _k + "-Astra"):
        if SITE_KATLA[_giris] != _v or port.markaKatla(_giris) != _v:
            _alias_sapan.append((_giris, _v, SITE_KATLA[_giris], port.markaKatla(_giris)))
    if SITE_KATLA[_v] != _v or port.markaKatla(_v) != _v:
        _alias_sapan.append((_v, _v, SITE_KATLA[_v], port.markaKatla(_v)))
kontrol("alias girdileri (kendisi · BÜYÜK · küçük · boşluk-önekli · tire-önekli · hedef) "
        "iki tarafta da hedefe katlanıyor", not _alias_sapan,
        "\n".join("%r  beklenen=%r  site=%r  port=%r" % a for a in _alias_sapan[:15]))

if canli_hata:
    kontrol("urunler.json canlı korpusu okunabildi", False, canli_hata)
else:
    kontrol("urunler.json canlı korpusu okundu (%d tekil ham marka değeri)" % _canli_tekil,
            _canli_tekil > 0)

shutil.rmtree(_tmpd, ignore_errors=True)
print("\nSONUC: %d gecti · %d dustu" % (_gecen, _dusen))
print("KIRMIZI" if _dusen else "GECTI")
sys.exit(1 if _dusen else 0)
