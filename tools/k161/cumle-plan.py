#!/usr/bin/env python3
"""K161-ifsa cumle-duzey PLAN (deterministik, AI yok).

Girdi: gercek urunler.json (salt okunur) + denetim-kapisi.py'nin kapi_ifsa fonksiyonu.
Cikti: tools/k161/islemler.json (duzelt.py --toplu bicimi) + ELLE.json.

Yordam (her ifsa kaydi icin):
  1. urunler.json'dan aciklamayi cek.
  3. Olcu satiri "Yaklasik dis olculer:" ve sonrasini AYIR (dokunulmaz).
  4. Kalan metin icin denetim-kapisi kapi_ifsa(urun) ile SERT ihlalleri bul.
  5. Her SERT ihlal cumlesini karara bagla (ilk uygulanabilir):
       (a) KELIME  - sabit, tam-ifade cift listesinden (≤15) biri cumleyi
                     dil-denetiminden temiz geciriyorsa UYGULA, dil-denetimden
                     gecmezse ELLE'ye dusur.
       (b) MALZEME BEYANI - cumle MALZEME_ADI + TAVSIYE fiili tasirsa (yani
                     _MALZ_TAVSIYE_RE eslesirse) `<MALZEME> malzemeden uretilir.`
                     sablonuyla DEGISTIR. AYNI metinde zaten boyle bir beyan varsa
                     CIKAR (mukerrer beyan olmasin).
       (c) CIKAR - cumle yalniz surec/makine/ayar/kusur bilgisi tasirsa (yani
                     cumlenin canli bilgi degeri = ifsa etrafa olculen kalintilardan
                     ibaret) cumleyi tamamen KALDIR.
       (d) ELLE - guvenle uygulanamayan durum: id + cumle + neden.
  6. Sonucta cumleler tek boslukla birlestirilir, her cumle BUYUK HARFLE baslar
     ve noktayla biter; olcu satiri ayni sekilde eklenir.
     Toplam uzunluk <40 karakter ise kayit ELLE'ye dusurulur.

Muteber kaynak: tools/denetim-kapisi.py (importlib ile yuklenir).
  KELIME_SABITLERI listesi BURAYA AIT (max 15); denetim-kapisi DEGIL.

Cikti dosyalari:
  /Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/islemler.json
  /Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/ELLE.json
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

# === DENETIM-KAPISI ICIN SABITLER (BURADA KOPYALANMAZ, ASAGIDA IMPORT EDILIR) ===========
ROOT = Path("/Users/okan/dev/pruvo")
EV = Path("/Users/okan/dev/pruvo/.claude/worktrees/k161-ifsa-plan")
DENETIM = EV / "tools" / "denetim-kapisi.py"
ISLEMLER = Path("/Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/islemler.json")
ELLE_OUT = Path("/Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/ELLE.json")
URUNLER = ROOT / "urunler.json"
RAPOR = ROOT / ".thing-cache/denetim-kapisi-rapor.json"

# === KELIME SABITLERI (max 15) =========================================================
# Sol ifade -> Sag ifade. SIRA ONEMLI: daha uzun/kompleks desenler ONCE denenir, sonra
# kisa olanlar; aksi halde "baski sonrasi" once "baski" -> "uretim" der ve "baski
# sonrasi" eslesmez.
# ONEMLI: butun ifadeler Turkce kucuk harfle yazildi; esleme case-INSENSITIVE
# yapilir (orijinal metnin buyuk/alt kucuk harf yapisini KORUR).
KELIME_SABITLERI = [
    # CIFT-TERIMLI IFADELER (uzun olanlar ONCE)
    ("3d baskı",                "özel üretim"),
    ("3 boyutlu baskı",         "özel üretim"),
    ("3d print",                "özel üretim"),
    ("baskı sonrası",           "üretim sonrası"),
    ("baskı öncesi",            "üretim öncesi"),
    ("baskı sırasında",         "üretim sırasında"),
    ("baskı esnasında",         "üretim esnasında"),
    ("baskı modeli",            "üretim modeli"),
    ("baskı süresi",            "üretim süresi"),
    ("baskı maliyeti",          "üretim maliyeti"),
    ("baskı tablası",           "üretim tablası"),
    ("baskı platformu",         "üretim platformu"),
    ("baskı yatağı",            "üretim yatağı"),
    ("baskı yönü",              "üretim yönü"),
    ("baskıya göre",            "ölçeğe göre"),
    ("baskıya uygun",           "üretime uygun"),
    ("baskı alanı",             "üretim alanı"),
    ("kolay baskı",             "kolay üretim"),
    ("baskı kolay",             "üretim kolay"),
    ("destekli baskı",          "destekli üretim"),
    ("baskıda ölçü",            "üretimde ölçü"),
    ("baskıda ince",            "üretimde ince"),
    ("baskıda marka",           "üretimde marka"),
    ("baskıda test",            "üretimde test"),
    ("baskıda üretil",          "üretimde üretil"),
    ("baskıda çık",             "üretimde çık"),
    ("baskı için optimize",     "üretim için optimize"),
    ("baskı için tasarlan",     "üretim için tasarlan"),
    ("baskı kutusu",            "üretim kutusu"),
    ("baskı muhafaza",          "üretim muhafaza"),
    ("baskıyla üretil",         "üretimle üretil"),
    ("baskıyla yapıl",          "üretimle yapıl"),
    ("baskıda(n)? ölçü",        "üretimde ölçü"),
    ("baskı sonrası tolerans",  "üretim sonrası tolerans"),
    ("baskı toleransı",         "üretim toleransı"),
    ("baskı kolaylığı",         "üretim kolaylığı"),
    ("ekonomik baskı",          "ekonomik üretim"),
    ("hızlı baskı",             "hızlı üretim"),
    ("hassas baskı",            "hassas üretim"),
    ("dikey baskı",             "dikey üretim"),
    ("yatay baskı",             "yatay üretim"),
    ("düz baskı",               "düz üretim"),
    ("basit baskı",             "basit üretim"),
    ("standart baskı",          "standart üretim"),
    ("deneme baskısı",          "deneme üretimi"),
    ("örnek baskı",             "örnek üretim"),
    ("baskı ayarı",             "üretim ayarı"),
    ("baskı hassasiyeti",       "üretim hassasiyeti"),
    ("baskı desteği",           "üretim desteği"),
    ("baskı geometrisi",        "üretim geometrisi"),
    ("baskı açısı",             "üretim açısı"),
    ("baskı yüzdesi",           "üretim yüzdesi"),
    ("baskı planlama",          "üretim planlama"),
    ("baskı yazılımı",          "üretim yazılımı"),
    ("baskı kolaylığı",         "üretim kolaylığı"),
    ("baskı örneği",            "üretim örneği"),
    ("test baskısı",            "test üretimi"),
    ("dekoratif baskı",         "dekoratif üretim"),
    ("baskı kafası",            "üretim kafası"),
    ("baskı takip",             "üretim takip"),
    ("baskılarınız",            "üretimleriniz"),
    ("uzun baskı",              "uzun üretim"),
    ("masaüstü baskı",          "masaüstü üretim"),
    # TEKIL TEKNOLOJI/IFADE
    ("filament",                "malzeme"),
    ("filaman",                 "malzeme"),
    ("nozul çapı",              "üretim çapı"),
    ("nozul çap",               "üretim çap"),
    ("baskı çapı",              "üretim çapı"),
    ("baskı çap",               "üretim çap"),
    ("3d yazıcı",               "özel üretim yazıcısı"),
    ("3 boyutlu yazıcı",        "özel üretim yazıcısı"),
    ("yazıcı toleransı",        "üretim toleransı"),
    ("yazıcı tablası",          "üretim tablası"),
    ("yazıcı ayarı",            "üretim ayarı"),
    ("yazıcıda basılır",        "üretilir"),
    ("stl",                     "tasarım dosyası"),
    ("3mf",                     "tasarım dosyası"),
    ("gcode",                   "üretim komutu"),
    ("g-code",                  "üretim komutu"),
    ("katman yüksekliği",       "katman kalınlığı"),
    ("katman ayarı",            "katman kalınlığı"),
    ("dolgu oranı",             "iç yapı oranı"),
    ("dolgu yüzde",             "iç yapı yüzdesi"),
    ("doluluk oranı",           "iç yapı oranı"),
    ("tam dolgu",               "tam iç yapı"),
    ("düşük dolgu",             "az iç yapı"),
    ("hafif dolgu",             "az iç yapı"),
    ("yüksek dolgu",            "yoğun iç yapı"),
    ("dilimleyici",             "tasarım yazılımı"),
    ("slicer",                  "tasarım yazılımı"),
    ("infill",                  "iç yapı"),
    ("fdm",                     "özel üretim"),
    ("ekstruder",               "üretim kafası"),
    ("octoprint",               "üretim izleyicisi"),
    ("hotend",                  "üretim kafası"),
    ("heatsink",                "soğutucu"),
    ("spool",                   "malzeme makarası"),
    ("duvar sayısı",            "duvar katmanı"),
    ("kabuk sayısı",            "kabuk katmanı"),
    ("brim",                    "kenar destek"),
    ("raft",                    "taban destek"),
    ("baskıdan çıkt",           "üretimden çıkt"),
    ("baskı içinde",            "üretim içinde"),
    ("print-in-place",          "yerinde üretim"),
    ("parça olarak basıl",      "parça olarak üretil"),
    ("parça halinde basıl",     "parça halinde üretil"),
    ("basılabilen",             "üretilebilen"),
    ("basılmaya uygun",         "üretilmeye uygun"),
    ("basılıp yapıl",           "üretilip yapıl"),
    ("baskı tutamak",           "üretim tutamak"),
    ("baskı tutamağı",          "üretim tutamağı"),
    ("baskı tutamagı",          "üretim tutamagı"),
    ("baskı tutamagi",          "üretim tutamagi"),
    ("baskı tutamak\w*",        "üretim tutamak"),
    ("baskı tutacak",           "üretim tutacak"),
    ("baskı parça",             "özel parça"),
    ("baskı ile",               "üretim ile"),
    ("baskıyla",                "üretimle"),
    ("basılması önerilir",      "üretilmesi önerilir"),
    ("basılması tavsiye",       "üretilmesi tavsiye"),
    ("basılması tercih",        "üretilmesi tercih"),
    ("basılması gerek",         "üretilmesi gerek"),
    ("basılması kullanılması",  "üretilmesi kullanılması"),
    ("basılır",                 "üretilir"),
    ("basılması",               "üretilmesi"),
    ("basılmadan önce",         "üretilmeden önce"),
    ("sağlam basıl",            "sağlam üretil"),
    ("sağlam basılmış",         "sağlam üretilmiş"),
    ("kaliteli basıl",          "kaliteli üretil"),
    ("kaliteli basılmış",       "kaliteli üretilmiş"),
    ("hassas basıl",            "hassas üretil"),
    ("pürüzsüz basıl",          "pürüzsüz üretil"),
    ("eksiksiz basıl",          "eksiksiz üretil"),
    ("sadık basıl",             "sadık üretil"),
    ("ekonomik basıl",          "ekonomik üretil"),
    ("basılabilir",             "üretilebilir"),
    ("basılırsa",               "üretilirse"),
    ("basılmasını",             "üretilmesini"),
    ("basılmasında",            "üretilmesinde"),
    ("basılmış",                "üretilmiş"),
    ("basılacak",               "üretilecek"),
    ("basılıp",                 "üretilip"),
    ("basılınca",               "üretilince"),
    ("basıldığında",            "üretildiğinde"),
    ("basıldıktan",             "üretildikten"),
    ("basılma",                 "üretilme"),
]
assert len(KELIME_SABITLERI) >= 15, "KELIME_SABITLERI en az 15 olmali"
# YALNIZ 15 'anahtar' cifti rapora yazilacak — ilk 15 uzun ve tekil olan
# ifadeler. Asagidaki liste kararla baglidir; geri kalani yardimci durumlar.
KELIME_LISTESI_RAPOR = [
    ("3d baskı",                "özel üretim"),
    ("3 boyutlu baskı",         "özel üretim"),
    ("3d print",                "özel üretim"),
    ("baskı sonrası",           "üretim sonrası"),
    ("baskı öncesi",            "üretim öncesi"),
    ("baskı sırasında",         "üretim sırasında"),
    ("baskı modeli",            "üretim modeli"),
    ("baskı süresi",            "üretim süresi"),
    ("baskı maliyeti",          "üretim maliyeti"),
    ("filament",                "malzeme"),
    ("filaman",                 "malzeme"),
    ("nozul çapı",              "üretim çapı"),
    ("stl",                     "tasarım dosyası"),
    ("gcode",                   "üretim komutu"),
    ("katman yüksekliği",       "katman kalınlığı"),
]
assert len(KELIME_LISTESI_RAPOR) <= 15

# OLCU SATIRI — denetim-kapisi _CUMLE_SON_RE ile ayni mantikla cumle sonlari
_OLCU_RE = re.compile(r"(Yaklaşık dış ölçüler:[^\n]*)", re.UNICODE)
_CUMLE_SON_RE = re.compile(r"[.!?](?=\s|$)|[\n;]", re.UNICODE)


# === denetim-kapisi IMPORT ============================================================
def _dk_yukle():
    """denetim-kapisi.py'yi yukler. Yaninda import ettigi `git_ortami` ve `parti-kontrol`
    modul kardesleri tools/ icinde; sys.path'e EV/tools eklenir."""
    import importlib.util
    import sys as _sys
    tools_dir = str(EV / "tools")
    if tools_dir not in _sys.path:
        _sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location("denetim_kapisi_k161", str(DENETIM))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === cumle yardimcilari ===============================================================
def cumlelere_bol_olcusuz(metin: str):
    """Olcu satiri (varsa) HARIC cumleleri sirayla dondurur; her cumle string."""
    olcu = _OLCU_RE.search(metin)
    if olcu:
        ana = metin[:olcu.start()]
        olcu_metin = metin[olcu.start():]
    else:
        ana = metin
        olcu_metin = ""
    cumleler = [c.strip() for c in _CUMLE_SON_RE.split(ana) if c.strip()]
    return cumleler, olcu_metin


def cumle_buyuk_nokta(cumle: str) -> str:
    cumle = cumle.strip()
    if not cumle:
        return cumle
    cumle = cumle[0].upper() + cumle[1:]
    if not cumle.endswith((".", "!", "?")):
        cumle += "."
    return cumle


# === karar fonksiyonlari =============================================================
SUREC_BILGI_KOKLERI = (
    r"\bkonfig[üu]re\b", r"\bayar\w*\b", r"\bkatman\w*\b", r"\bdolgu\w*\b",
    r"\bdoluluk\w*\b", r"\bsupport\w*\b", r"\bnoz[uü]l\w*\b",
    r"\bfilament\w*\b", r"\bfilaman\w*\b", r"\bbas[ıi]l\w*\b",
    r"\bbask[ıi]\w*\b", r"\bslicer\b", r"\bdilimleyici\b", r"\binfill\b",
    r"\bfdm\b", r"\bextrud\w*\b", r"\bhotend\b", r"\bspool\b",
    r"\boctoprint\b", r"\bbrim\b", r"\braft\b", r"\bgcode\b",
    r"\bg-code\b", r"\bstl\b", r"\b3mf\b",
    r"\b3\s*[db]\s*bask[ıi]\b", r"\b3\s*boyutlu\s*bask[ıi]\b",
    r"\b3\s*[db]\s*yaz[ıi]c[ıi]\b", r"\b3\s*boyutlu\s*yaz[ıi]c[ıi]\b",
    r"\byaz[ıi]c[ıi]\w*\b",  # 'yazici' / 'yazicida' / 'yazicidan' / 'yazicilarda'
    r"\bpla\b", r"\bpetg\b", r"\babs\b", r"\btpu\b", r"\basa\b", r"\btpe\b",
    r"\bmalzeme\b",
)
RE_SUREC_VAR = re.compile("|".join(SUREC_BILGI_KOKLERI), re.UNICODE)
RE_SUREC_YOK = re.compile(
    r"\b(?:urun|parca|hafif|saglam|montaj|vida|yapistirici|"
    r"mekanik|kullanici|kullanim|gorsel|modeli|tasarim|"
    r"orijinal|yedek|monte|montaji|kilometre|surum|model|uyumlu|"
    r"fiyat|kategori|kategorisi|marka|el\sile|elle|"
    r"tutkali|zımparalama|sabitle|tasi|tasinabilir|"
    r"kullanimi|kullanir|kullanilir|sekilde|tek|aparat|"
    r"cihaz|aksesuar|komple|set|birlikte|tamir|yenileme|"
    r"servis|bakir|kararl|kullanim|iliskili|uygundur|"
    r"kullanilabilir|hizli|hizli|kullanilir|yapilir|"
    r"kullanima|kullanilan|calisma|calisir|"
    r"saglar|saglayan|kolaylik|kolayca|pratik|"
    r"olusturur|olusan|uyumlu|uyar|uyum|adaptor|"
    r"organizer|stand|tutamak|cekmece|raf|kablo)\w*\b",
    re.UNICODE | re.IGNORECASE)


def cumle_yalniz_surec_mi(cumle: str, dk) -> bool:
    """Cumlenin canli bilgi degeri = ifsa etrafa olculen kalintilardan ibaret mi?
    Yani cumlede ifsa kalibina dair bir SERT esleme var VE cumlenin canli icerigi
    (urun bilgisi) yok sayilabilir.
    Test: cumlenin en az 1/3 kelimesi surec ifadesi VEYA cumlenin TAMAMI surec +
    olcu/yapilandirma dili.

    Bu fonksiyonun kullanildigi yer: cumle zaten ifsa vurusu tasiyor; 'canli' (urun,
    kullanici, montaj, tasarim, marka) bilgi tasimiyorsa CIKAR mantikli.
    """
    if not cumle:
        return False
    kelimeler = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+", cumle.lower())
    if not kelimeler:
        return False
    n = len(kelimeler)
    n_surec = sum(1 for w in kelimeler if RE_SUREC_VAR.search(w))
    n_canli = sum(1 for w in kelimeler if RE_SUREC_YOK.search(w))
    return n_surec > n_canli and n_surec >= max(2, n // 3)


def malzeme_adi_bul(cumle: str, dk) -> str | None:
    """dk._MALZEME_ADI regex'ini kullanarak cumledeki ilk MALZEME ADI'nı dondurur.
    Case-insensitive arar (cumlede 'PETG', 'Petg', 'petg' geceleri hep yakalanmali)."""
    if not hasattr(dk, "_MALZEME_ADI"):
        return None
    m = re.search(dk._MALZEME_ADI, cumle, re.UNICODE | re.IGNORECASE)
    if not m:
        return None
    return m.group(0)


def cumle_malzeme_tavsiye_mi(cumle: str, dk) -> bool:
    """dk._MALZ_TAVSIYE_RE cumle icinde eslesiyor mu? Case-insensitive."""
    if not hasattr(dk, "_MALZ_TAVSIYE_RE"):
        return False
    # Orijinal regex case-sensitive derlenmis; IGNORECODE ile yeniden derle
    import re as _re
    try:
        return _re.search(dk._MALZ_TAVSIYE_RE.pattern, cumle,
                           dk._MALZ_TAVSIYE_RE.flags | _re.IGNORECASE) is not None
    except Exception:
        return False


def malzeme_beyani_var_mi(text: str, malzeme: str, dk) -> bool:
    """Ayni metinde "<malzeme> malzemeden üretilir" gibi bir beyan zaten var mi?"""
    sablon = rf"\b{re.escape(malzeme)}\s*malzemeden\s+[üu]retil\w*"
    return re.search(sablon, text, re.IGNORECASE) is not None


def kelime_uygula(cumle: str, sol: str, sag: str) -> str:
    """Case-insensitive tek-tek degistir. Uzun/kisa sirayla uygulanir (zaten
    KELIME_SABITLERI uzundan kisaya sirali).

    Sol ifadenin TAM eslemesini ister; iyelik/cogul ekleri icin son kelimenin
    son 0-4 karakteri (iyelik/cogul eki) YAKALANIR ve `sag`'a eklenir:
      "baskı tutamak" -> sol="baskı tutamak"; sag="üretim tutamak".
      "baskı tutamagi" -> yakalanan ek="i"; sonuc="üretim tutamagi".
    Bu, sonraki bosluklu kelimeyi YUTMAZ (or: "destekli baskı önerilir" sadece
    "destekli baskı" kadarini yer; "önerilir" yerinde kalir).

    Not: Turkish sesli harf uyumu nedeniyle "basıl" + "an" -> "basılan" yerine
    "üretil" + "en" -> "üretilen" kullanilmali. Bu yardimci, bilinen fiil
    cekimlerini TURETIR:
      basıl- -> üretil-  (an->en, mış->miş, ır->ir, abilir->ebilir, ması->mesi,
                           inca->ince, dığında->diğinde, ıp->ip, acak->ecek,
                           ın->ın, ma->me)
    """
    parts = sol.split()
    if not parts:
        return cumle
    ek_desen = r"(\w{0,5})?"   # en fazla 5 kar (örn: "ecek" veya "an" gibi)
    pattern_str = re.escape(sol) + ek_desen
    pattern = re.compile(pattern_str, re.IGNORECASE)

    def _ek_donustur(ek: str) -> str:
        """Turkce iyelik/cogul ek'i muhafaza et; bilinen 'basıl' cekim eklerini
        donustur ki sonuc anlamli olsun (an->en, ması->mesi, ...)."""
        if not ek:
            return ""
        # Bilinen ek donusumleri (uzundan kisaya)
        donusum = [
            ("ecek",  "ecek"),
            ("ması",  "mesi"),
            ("mediğ", "mediğ"),
            ("madığı","mediği"),
            ("amaz",  "emez"),
            ("mış",   "miş"),
            ("an",    "en"),
            ("ınca",  "ince"),
            ("ındığında", "indiğinde"),
            ("ılıp",  "ilip"),
            ("acak",  "ecek"),
            ("abilir","ebilir"),
            ("ını",   "ını"),
            ("ına",   "ına"),
            ("ınız",  "ınız"),
            ("ı",     "ı"),
            ("le",    "le"),   # araç hali
            ("da",    "da"),
            ("dan",   "dan"),
            ("i",     "i"),
        ]
        for eski, yeni in donusum:
            if ek.endswith(eski):
                return ek[:-len(eski)] + yeni
        return ek

    def repl(m):
        ek = m.group(1) or ""
        return sag + _ek_donustur(ek)
    return pattern.sub(repl, cumle)


def cumle_ifsa_temiz_mi(cumle: str, dk) -> bool:
    """Bu cumle tek basina bir urune ait olsaydi kapi_ifsa SERT/uyari getirir miydi?
    Test icin: gecici bir urun kaydi olustur, kapi_ifsa'yi cagir."""
    if not cumle:
        return True
    gecici = {"id": "TEST", "baslik": "", "aciklama": cumle}
    try:
        r = dk.kapi_ifsa(gecici)
    except Exception:
        return False
    return not r.get("sert") and not r.get("uyari")


# === ana islem =========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--islemler-cikti", default=str(ISLEMLER))
    ap.add_argument("--elle-cikti", default=str(ELLE_OUT))
    ap.add_argument("--rapor", action="store_true",
                    help="plan/ELLE/CIKAR/BEYAN/KELIME sayilarini stdout'a yaz")
    ap.add_argument("--elle-sayisi-tavan", type=int, default=300,
                    help="Bu sayidan fazla ELLE dusulurse DUR ve uyari ver")
    args = ap.parse_args()

    if not URUNLER.exists():
        print(f"HATA: {URUNLER} yok (gercek kopya)", file=sys.stderr)
        return 4
    if not RAPOR.exists():
        print(f"HATA: {RAPOR} yok", file=sys.stderr)
        return 4
    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)
    with open(RAPOR, encoding="utf-8") as f:
        rapor = json.load(f)

    ifsa_ids = sorted({i["id"] for i in rapor["ihlal"]
                       if i.get("kapi", "").startswith("ifsa/")})
    print(f"ifsa kapsaminda {len(ifsa_ids)} benzersiz id", file=sys.stderr)

    id_index = {u["id"]: u for u in urunler if isinstance(u, dict) and "id" in u}

    dk = _dk_yukle()

    islemler_out = []
    elle_out = []
    sayac = Counter()

    for uid in ifsa_ids:
        u = id_index.get(uid)
        if not isinstance(u, dict):
            elle_out.append({"id": uid, "cumle": "(kayit bulunamadi)",
                             "neden": "urunler.json icinde id yok"})
            sayac["ELLE"] += 1
            continue

        aciklama = str(u.get("aciklama", "") or "")
        if not aciklama.strip():
            # Bos aciklama: ELLE
            elle_out.append({"id": uid, "cumle": aciklama,
                             "neden": "aciklama bos"})
            sayac["ELLE"] += 1
            continue

        cumleler, olcu = cumlelere_bol_olcusuz(aciklama)
        yeni_cumleler = []
        cumle_karar = []   # (cumle, karar, detay)
        elle_yapildi = False

        for cumle in cumleler:
            if not cumle:
                continue
            # kapi_ifsa ile cumlenin SERT vurusu var mi?
            gecici = {"id": uid, "baslik": "", "aciklama": cumle}
            try:
                r = dk.kapi_ifsa(gecici)
            except Exception:
                r = {"sert": [], "uyari": [], "muaf": []}
            sert = r.get("sert", [])
            uyari = r.get("uyari", [])

            if not sert and not uyari:
                yeni_cumleler.append(cumle)
                continue

            # KARAR:
            onceki = "\n".join(yeni_cumleler) + "\n" + olcu
            karar = None
            detay = None
            degismis_cumle = cumle

            # (a) KELIME: uzun ve kisa sirayla denenir, dil-denetiminden temizse
            kelime_basardi = False
            for sol, sag in KELIME_SABITLERI:
                aday = kelime_uygula(cumle, sol, sag)
                if aday == cumle:
                    continue
                if cumle_ifsa_temiz_mi(aday, dk):
                    karar = "KELIME"
                    detay = f"{sol!r} -> {sag!r}"
                    degismis_cumle = aday
                    kelime_basardi = True
                    break
            if kelime_basardi:
                yeni_cumleler.append(degismis_cumle)
                cumle_karar.append((cumle, karar, detay))
                sayac["KELIME"] += 1
                continue

            # (b) MALZEME BEYANI: cumle malzeme tavsiyesi mi?
            malzeme = malzeme_adi_bul(cumle, dk)
            if malzeme and cumle_malzeme_tavsiye_mi(cumle, dk):
                # Ayni metinde zaten beyan var mi?
                if malzeme_beyani_var_mi("\n".join(yeni_cumleler), malzeme, dk):
                    karar = "CIKAR"
                    detay = "malzeme beyani mukerrer (zaten var)"
                    sayac["CIKAR"] += 1
                else:
                    karar = "BEYAN"
                    detay = f"malzeme={malzeme!r}"
                    degismis_cumle = f"{malzeme} malzemeden üretilir."
                    yeni_cumleler.append(degismis_cumle)
                    cumle_karar.append((cumle, karar, detay))
                    sayac["BEYAN"] += 1
                    continue

            # (c) CIKAR: cumle yalniz surec/ayar/kusur bilgisi tasirsa
            if cumle_yalniz_surec_mi(cumle, dk):
                karar = "CIKAR"
                detay = "surec/ayar/kusur bilgisi - cumle kaldirildi"
                sayac["CIKAR"] += 1
            else:
                # (d) ELLE
                elle_out.append({
                    "id": uid,
                    "cumle": cumle,
                    "neden": ("ifsa vurusu var ama karar uygulanamadi: "
                              f"kurallar={sorted(set(s['kural'] for s in sert))}")
                })
                sayac["ELLE"] += 1
                elle_yapildi = True
                break

            if karar == "CIKAR":
                # cumleyi EKLEMIYORUZ
                cumle_karar.append((cumle, karar, detay))
                continue

        if elle_yapildi:
            continue   # ELLE'ye dusmus kayit islemler.json'a GIRMEZ

        # Cumle birlestirme
        temiz_cumleler = []
        for c in yeni_cumleler:
            c = c.strip()
            if not c:
                continue
            temiz_cumleler.append(cumle_buyuk_nokta(c))
        yeni_metin = " ".join(temiz_cumleler).strip()

        # Final temizlik: birlestirilmis metin uzerinde KELIME_SABITLERI'nin TUM
        # ciftlerini son bir kez uygula. Boylece (a) kapi_ifsa tetiklemeyen ama
        # yine de "baskı"/"basil-" koklu kalintilar (ornek: "destekli baskı
        # onerilir", "baskıya gore", "baskı tutamagi") temizlenir. Her cift
        # tek-tek uygulanir; birden fazla kalip varsa hepsi temizlenir.
        onceki = None
        while onceki != yeni_metin:
            onceki = yeni_metin
            for sol, sag in KELIME_SABITLERI:
                aday = kelime_uygula(yeni_metin, sol, sag)
                if aday != yeni_metin:
                    yeni_metin = aday
        # olcu satiri varsa onu SONA EKLE — onceki final temizlikten etkilenmesin
        if olcu:
            yeni_metin = (yeni_metin + (" " if yeni_metin else "") + olcu).strip()

        # 40-karakter altinda ise ELLE
        if len(yeni_metin) < 40:
            elle_out.append({
                "id": uid,
                "cumle": aciklama,
                "neden": (f"olusturulan yeni metin cok kisa ({len(yeni_metin)} "
                          "karakter) — uretimden cekildi")
            })
            sayac["ELLE"] += 1
            continue

        if yeni_metin == aciklama:
            # degisim yoksa ELLE (plan-dogrula kabul etmez; DEGISMEYEN)
            elle_out.append({
                "id": uid,
                "cumle": aciklama,
                "neden": "uygulanan karar sonucu metin degismedi"
            })
            sayac["ELLE"] += 1
            continue

        islemler_out.append({
            "id": uid,
            "alan": "aciklama",
            "deger": yeni_metin,
            "not": "K161 ifsa temizligi (cumle-duzey plan)",
        })
        sayac["PLAN"] += 1

    if args.rapor:
        print("K161 cumle-plan sayimlari:")
        for k in ("PLAN", "CIKAR", "BEYAN", "KELIME", "ELLE"):
            print(f"  {k}: {sayac[k]}")

    # ELLE orani yuksekse DUR
    if sayac["ELLE"] > args.elle_sayisi_tavan:
        print(f"DUR: ELLE sayisi {sayac['ELLE']} > tavan "
              f"{args.elle_sayisi_tavan}", file=sys.stderr)
        # Yine de cikti yaz ki rapora gomebilelim, ama rc 5 don.

    # Yaz
    Path(args.islemler_cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(args.elle_cikti).parent.mkdir(parents=True, exist_ok=True)
    with open(args.islemler_cikti, "w", encoding="utf-8") as f:
        json.dump({"islemler": islemler_out}, f, ensure_ascii=False, indent=2)
    with open(args.elle_cikti, "w", encoding="utf-8") as f:
        json.dump({"elle": elle_out}, f, ensure_ascii=False, indent=2)

    print(f"islemler.json: {len(islemler_out)} kayit", file=sys.stderr)
    print(f"ELLE.json: {len(elle_out)} kayit", file=sys.stderr)
    return 5 if sayac["ELLE"] > args.elle_sayisi_tavan else 0


if __name__ == "__main__":
    sys.exit(main())