#!/usr/bin/env python3
r"""denetim-kapisi.py — urun-ekleme PARTISININ otomatik denetim kapisi.

Amac: mimar her partide ELLE yaptigi lisans/logo/olcu/dedup/gorsel/marka denetimini
KODA dokmek. Otonom ekleme hattinin temeli (kuyruk+cron ILERIDE, bu pakette YOK).

PARTI (yeni, stage'lenmis, commit'siz urunler) = working-tree urunler.json'da olup
`git show HEAD:urunler.json` ciktisinda OLMAYAN id'ler. Alternatif: --idler ile
dogrudan id listesi.

KAPILAR (her biri ayri, tek tek test edilebilir fonksiyon):
  1. LISANS (fail-closed): .urun-kaynaklari.json'daki lisanstan bak; satilamaz -> auto_sil.
     Muaf: satin-alma (satin aldik), parametrik/uyelik/kendi jeneratorumuz (kendi IP).
     printables-api.satilabilir() KULLANILIR (DEGISTIRILMEZ) — serbest-metin lisans adi
     once lisans_kisaltma() ile kisaltmaya cevrilir.
  2. MAKET / LOGO (OLCUM ile iki katman — RAPOR-MIMARA.md):
     - TIER-A auto_sil: olcekli-model/maket ARAÇ (maket/olcekli/diorama/minyatur/figur/
       "model araç"/"1/N olcek") — YASAK sinif, yanlis-pozitif dusuk.
     - TIER-B/C ESKALASYON (silme YOK): baslikta logo/amblem/plaket/rozet/koleksiyon
       ("logoyu cikar -> urun kalir mi" YARGISI mimara); + marka + kabartma/rolyef/
       detayli form (logo imasi ama 'logo' kelimesi yok). Islevsel parca logoyu
       TASIYABILIR -> auto-silme yanlis olur (olculdu: 68/102 aciklama-mention islevsel).
  3. OLCU: aciklamada olcu satiri ("A × B × C mm" / "Yaklasik dis olculer") yoksa -> auto_sil.
     Muaf: satin-alma (STL siparişte olculur), parametrik (olcuye ozel).
  4. GORSEL CAKISMA: gorseller[0] dosya adi iki urunde paylasiliyorsa -> eskalasyon (silme).
  5. PLATFORMLAR-ARASI + JENERIK DEDUP: normalize baslikla grupla. Grup>1:
     - Uyeler aciklama olarak BENZER (gercek ikiz) -> EN IYIYI tut, gerisi auto_sil.
     - BELIRGIN FARKLI (varyant) -> eskalasyon (mimar ayristir/sil karar versin).
     Esik: aciklama token-Jaccard >= DEDUP_ESIK (0.75) VEYA ayni kaynak linki -> ikiz.
     Altindaysa/kararsizsa -> ESKALASYON (muhafazakar: yanlis oto-silmektense eskale et).
  6. MARKA KIRLILIGI: marka dizisinde arac-markasi-olmayan tokenlar (Apple/GoPro/Yeti...)
     -> eskalasyon/temizlik onerisi (asla oto-silme).

CIKTI: .thing-cache/denetim-kapisi-rapor.json
  {auto_sil:[{id,kapi,gerekce}], dedup:[{baslik,tut,sil:[]}],
   eskalasyon:[{id/grup,kapi,neden}], marka_kirli:[{id,kirli_token,onerilen_marka}]}
VARSAYILAN report-only (hicbir sey silmez). --uygula ile auto_sil + dedup.sil,
tools/duzelt.py --sil ile UYGULANIR (flock+manifest+guard uyumlu; baska yolla
urunler.json'a yazilmaz). Eskalasyon HER ZAMAN sadece raporlanir.

Kullanim:
  python3 tools/denetim-kapisi.py                 # partiyi denetle, rapor yaz (report-only)
  python3 tools/denetim-kapisi.py --idler a b c   # bu id'leri "yeni" say
  python3 tools/denetim-kapisi.py --uygula        # auto_sil + dedup.sil'i duzelt.py ile uygula
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAKLAR = os.path.join(ROOT, ".urun-kaynaklari.json")
DUZELT = os.path.join(ROOT, "tools", "duzelt.py")
CACHE = os.path.join(ROOT, ".thing-cache")
RAPOR = os.path.join(CACHE, "denetim-kapisi-rapor.json")

# printables-api.py: satilabilir() + tr_lower() TEK KAYNAK (bu dosyanin yaninda; DEGISTIRME).
_spec = importlib.util.spec_from_file_location(
    "pr_api", os.path.join(os.path.dirname(os.path.abspath(__file__)), "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)
tr_lower = pr.tr_lower

# --- olcu ifadesi (parti-kontrol.py ile ayni desen) --------------------------
_OLCU_RE = re.compile(r"\d[\d\s.,×xX*+-]*mm\b", re.IGNORECASE)

# --- KAPI 2: maket/logo tiers (OLCUM temelli — bkz. RAPOR-MIMARA.md) ----------
# metin tr_lower'lanmis (kucuk, Turkce-duyarli) verilir; desenler de oyle yazilir.
#
# TIER-A auto_sil = MAKET/olcekli arac (YASAK: Okan 16 Tem "olcekli model / maket
#   ARAÇLAR EKLENMEZ"). Gercek katalogda bu terimler ~230 urune degiyor ve HEPSI
#   gercek olcekli-model (Suzuki model araç ailesi) — yanlis-pozitif dusuk -> auto_sil.
_MAKET_RE = re.compile(
    r"\bmaket\w*|\bölçekli\b|\bolcekli\b|\bdiorama\w*|\bminyatür\w*|\bminyatur\w*"
    r"|\bfigür\w*|\bfigur\w*|\bgösterim modeli\b|\bgosterim modeli\b"
    r"|\bmodel (araç|araba|arac|gövde|govde|kiti|seti|kit)\b"
    r"|1\s*[/:]\s*\d+\s*(ölçek|olcek)", re.UNICODE)
#
# TIER-B eskalasyon = LOGO/amblem/plaket/rozet/koleksiyon. OLCUM: baslik+aciklamada
#   102 urune degiyor ama 68'i SADECE aciklamada gecen ISLEVSEL parca ("Honda jant
#   gobegi kapagi", "buz kaziyici" — logoyu TASIYAN ama urunun kendisi degil). Okan
#   ilkesi: "logoyu CIKAR -> satilir urun kalir mi?". Bu YARGI otomatiklestirilemez
#   -> auto_sil DEGIL, ESKALASYON (mimar: logoyu duzelt mi, sil mi). Yuksek sinyal
#   icin SADECE BASLIK'ta aranir (34 urun; aciklama-ici mention islevsel parcada gurultu).
_LOGO_ESK_RE = re.compile(
    r"\blogo\w*|\bamblem\w*|\bemblem\w*|\bplaket\w*|\bmonogram\w*|\brozet\w*"
    r"|\bkoleksiyon\w*", re.UNICODE)
#
# TIER-C dusuk-guven eskalasyon = marka + kabartma/rolyef/detayli form ("logo"
#   gecmeden logo/kabartma imasi; ornek "Ford detaylı form"). OLCUM: dar kume
#   (kabartma/rolyef/detayli form) 12 urun — genis kume (form/sekil) 70 = gurultu,
#   bilerek DAR tutuldu (eskalasyon actionable kalsin).
_FORM_RE = re.compile(r"\bkabartma\w*|\bdetaylı form\b|\bdetayli form\b|\bform detay\w*"
                      r"|\brölyef\w*|\brolyef\w*", re.UNICODE)

# --- KAPI 6: arac-markasi OLMAYAN, marka dizisini kirleten AKSESUAR markalari ---
# SADECE eskalasyon/temizlik ONERISI (asla oto-silme/oto-temizlik) — mimar karar verir.
# KAPSAM: telefon/tablet/kamera/ses-aksesuari/oyun/giyilebilir/telsiz markalari — bunlar
# arac parcasinin marka dizisine "kirlilik" olarak girer (or. Ford telefon tutucu -> 'iPhone').
# BILINCLI DISARIDA: Bosch/Makita/Philips/Dyson/Sony/IKEA gibi beyaz-esya/alet ureticileri —
# bunlar Elektronik/Ev/Tamirat urununun MESRU birincil markasi olabilir (yanlis-pozitif olur).
# NOT: Yeti (Skoda modeli) ve Alpine (Renault alt-markasi) AYNI ZAMANDA arac adi -> yine
# listede (Okan ornek verdi) ama bunlar ozellikle YARGI ister; oneri koru, mimar suzsun.
_KIRLI_MARKA = {
    "apple", "iphone", "ipad", "airpods", "magsafe", "carplay", "android auto",
    "gopro", "dji", "insta360",
    "samsung", "galaxy", "xiaomi", "huawei", "oneplus",
    "nintendo", "playstation", "ps4", "ps5", "xbox", "steam deck",
    "yeti", "hertz", "alpine", "hella", "baofeng",
    "raspberry pi", "arduino",
    "garmin", "tomtom", "jbl", "anker", "logitech", "razer", "lego",
}

# --- KAPI 5: dedup esigi ------------------------------------------------------
# aciklama token-Jaccard >= bu deger (ya da ayni kaynak linki) -> GERCEK IKIZ (auto_sil).
# altinda -> BELIRGIN FARKLI/kararsiz -> ESKALASYON. Muhafazakar: esigi yuksek tut,
# supheliyi silmektense eskale et (yanlis oto-silme en pahali hata).
DEDUP_ESIK = 0.75
_STOP = set("ve ile için icin bir bu da de ki mm için icin".split())


# =============================================================================
# yardimcilar
# =============================================================================
def _kaynak_dict(kayit):
    return kayit if isinstance(kayit, dict) else {}


def _satin_alma(kayit):
    return isinstance(kayit, dict) and kayit.get("tur") == "satin-alma"


def _kendi_urunumuz(urun, kayit):
    """Kendi/uyelik IP'miz mi? (lisans/olcu kapisindan MUAF) — parametrik, uyelik (*****),
    ya da kendi jeneratorumuz."""
    if bool(urun.get("parametrik")):
        return True
    if isinstance(kayit, dict):
        if kayit.get("uyelik"):
            return True
        if "pruvo-jenerator" in str(kayit.get("kaynak") or "").lower():
            return True
    return False


def lisans_kisaltma(raw):
    """.urun-kaynaklari.json'daki serbest-metin lisans adini satilabilir()'in anladigi
    kisaltmaya cevirir ('Creative Commons - Attribution' -> 'CC-BY',
    'GNU General Public License v3.0' -> 'GPL'). Bilinmeyen -> ham deger dondurulur
    (satilabilir() zaten fail-closed)."""
    s = tr_lower(raw).strip() if isinstance(raw, str) else ""
    if not s:
        return ""
    nc = ("noncommercial" in s or "non-commercial" in s or "non commercial" in s or "-nc" in s)
    if "cc0" in s or "public domain" in s:
        return "CC-BY-NC" if nc else "CC0"        # NC+CC0 pratikte olmaz; guvenlik agi
    cc = ("creative commons" in s or "cc-by" in s or "cc by" in s
          or re.search(r"\bcc\b", s) is not None)
    by = ("attribution" in s or re.search(r"\bby\b", s) is not None)
    if cc and by:
        parts = ["CC", "BY"]
        if nc:
            parts.append("NC")
        if ("share" in s and "alike" in s) or "-sa" in s:
            parts.append("SA")
        if "noderiv" in s or "no deriv" in s or "-nd" in s:
            parts.append("ND")
        return "-".join(parts)
    if "gpl" in s or "general public license" in s:
        return "GPL"
    if "bsd" in s:
        return "BSD"
    if re.search(r"\bmit\b", s) is not None:
        return "MIT"
    return raw                                     # Standard Digital File / OCL / bilinmeyen


def _lisans_ham(kayit):
    d = _kaynak_dict(kayit)
    return d.get("lisans")


def _kaynak_link(kayit):
    if isinstance(kayit, dict):
        return str(kayit.get("link") or "").strip()
    if isinstance(kayit, str):
        return kayit.split(None, 1)[0].strip() if kayit.strip() else ""
    return ""


def _printables_kaynak(kayit):
    if isinstance(kayit, dict) and str(kayit.get("kaynak") or "").lower() == "printables":
        return True
    return "printables.com" in _kaynak_link(kayit).lower()


def _olculu(urun):
    a = urun.get("aciklama")
    return isinstance(a, str) and _OLCU_RE.search(a) is not None


def _gorsel_key(urun):
    """gorseller[0] URL'sinin dosya adi (cakisma karsilastirmasi icin)."""
    g = urun.get("gorseller")
    if not isinstance(g, list) or not g or not isinstance(g[0], str):
        return None
    return g[0].rstrip("/").rsplit("/", 1)[-1]


def _metin(urun):
    return tr_lower((urun.get("baslik") or "") + " \n " + (urun.get("aciklama") or ""))


def _norm_baslik(s):
    s = tr_lower(s or "")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def _tokset(s):
    s = tr_lower(s or "")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return {t for t in s.split() if t and t not in _STOP}


def _jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# =============================================================================
# KAPILAR (saf fonksiyonlar — fixture ile test edilebilir)
# =============================================================================
def kapi_lisans(urun, kayit):
    """(auto_sil_kapi|None, gerekce). Satin-alma/kendi urunumuz -> muaf."""
    if _satin_alma(kayit) or _kendi_urunumuz(urun, kayit):
        return None, ""
    ham = _lisans_ham(kayit)
    if not ham or not str(ham).strip():
        return "lisans", "lisans kaydi yok/tanimsiz (fail-closed)"
    abbr = lisans_kisaltma(ham)
    if not pr.satilabilir(abbr):
        return "lisans", "satilamaz lisans: %r (norm: %s)" % (ham, abbr)
    return None, ""


def kapi_maket_auto(urun):
    """TIER-A: olcekli-model/maket ARAÇ (YASAK) anahtar kelimesi baslik+aciklamada
    varsa eslesen ifadeyi dondur (auto_sil), yoksa None."""
    m = _MAKET_RE.search(_metin(urun))
    return m.group(0) if m else None


def kapi_logo_eskalasyon(urun):
    """TIER-B/C eskalasyon (SILME YOK). Sirayla:
      B) BASLIK'ta logo/amblem/plaket/rozet/koleksiyon -> "logoyu cikar" yargisi mimara.
      C) marka baglami + kabartma/rolyef/detayli form (logo imasi ama 'logo' kelimesi yok).
    Gerekce metni dondurur; hicbiri yoksa None."""
    baslik = tr_lower(urun.get("baslik") or "")
    mb = _LOGO_ESK_RE.search(baslik)
    if mb:
        return ("baslikta '%s' (logo/amblem/plaket/rozet) — logoyu cikarinca satilir "
                "urun kalir mi? mimar: duzelt mi sil mi" % mb.group(0).strip())
    marka = urun.get("marka")
    if isinstance(marka, list) and marka:
        mc = _FORM_RE.search(_metin(urun))
        if mc:
            return "marka + '%s' (logo/kabartma imasi; 'logo' kelimesi yok) — incele" % mc.group(0).strip()
    return None


def kapi_olcu(urun, kayit):
    """(auto_sil_kapi|None, gerekce). Satin-alma/parametrik -> muaf."""
    if _satin_alma(kayit) or bool(urun.get("parametrik")):
        return None, ""
    if _olculu(urun):
        return None, ""
    return "olcu", "aciklamada olcu (mm) satiri yok"


def kapi_marka_kirli(urun):
    """marka dizisinde arac-markasi-olmayan token varsa {id,kirli_token,onerilen_marka}."""
    marka = urun.get("marka")
    if not isinstance(marka, list):
        return None
    kirli = [m for m in marka if isinstance(m, str) and tr_lower(m).strip() in _KIRLI_MARKA]
    if not kirli:
        return None
    return {"id": urun.get("id"), "kirli_token": kirli,
            "onerilen_marka": [m for m in marka if m not in kirli]}


def kapi_gorsel_cakisma(yeni, tum):
    """Yeni urunlerden gorseller[0] dosya adini (yeni ya da mevcut) baska urunle paylasan
    her biri icin eskalasyon kaydi. Silme."""
    key_map = defaultdict(list)
    for u in tum:
        k = _gorsel_key(u)
        if k:
            key_map[k].append(u.get("id"))
    esk = []
    for u in yeni:
        k = _gorsel_key(u)
        if k and len(key_map[k]) > 1:
            digerleri = [i for i in key_map[k] if i != u.get("id")]
            esk.append({"id": u.get("id"), "kapi": "gorsel-cakisma",
                        "neden": "gorseller[0] dosya adi paylasiliyor: %s (diger: %s)"
                                 % (k, ", ".join(str(d) for d in digerleri))})
    return esk


def kapi_dedup(yeni, tum, head_ids, kaynaklar, haric):
    """(dedup, eskalasyon, sil_ids). haric = gate1-3'te zaten auto_sil edilen id'ler
    (dedup'a sokulmaz). En-iyi onceligi: canli(HEAD) > olcu var > cok gorsel > Printables."""
    yeni_ids = {u.get("id") for u in yeni if u.get("id") not in haric}
    gruplar = defaultdict(list)
    for u in tum:
        gruplar[_norm_baslik(u.get("baslik"))].append(u)

    def oncelik(u):
        return (1 if u.get("id") in head_ids else 0,
                1 if _olculu(u) else 0,
                len(u.get("gorseller") or []),
                1 if _printables_kaynak(kaynaklar.get(u.get("id"))) else 0)

    dedup, esk, sil_ids = [], [], []
    for norm, uyeler in gruplar.items():
        if not norm:
            continue
        uyeler_ok = [u for u in uyeler if u.get("id") not in haric]
        if len(uyeler_ok) < 2:
            continue
        grup_yeni = [u for u in uyeler_ok if u.get("id") in yeni_ids]
        if not grup_yeni:
            continue  # gruptaki hicbir yeni urun yok -> partiyle ilgisiz
        best = max(uyeler_ok, key=oncelik)
        best_tok = _tokset(best.get("aciklama"))
        best_link = _kaynak_link(kaynaklar.get(best.get("id")))
        sil_grup = []
        for u in grup_yeni:
            if u.get("id") == best.get("id"):
                continue
            u_link = _kaynak_link(kaynaklar.get(u.get("id")))
            ayni_kaynak = bool(best_link) and best_link == u_link
            j = _jaccard(best_tok, _tokset(u.get("aciklama")))
            if ayni_kaynak or j >= DEDUP_ESIK:
                sil_grup.append(u.get("id"))
            else:
                esk.append({"grup": norm, "id": u.get("id"), "kapi": "dedup",
                            "neden": "ayni baslik, aciklama belirgin farkli "
                                     "(jaccard=%.2f < %.2f); ayristir mi sil mi -> mimar" % (j, DEDUP_ESIK)})
        if sil_grup:
            dedup.append({"baslik": best.get("baslik"), "tut": best.get("id"), "sil": sil_grup})
            sil_ids.extend(sil_grup)
    return dedup, esk, sil_ids


# =============================================================================
# orkestrator
# =============================================================================
def denetle(urunler, yeni_ids, head_ids, kaynaklar):
    """Tum kapilari calistirip yapilandirilmis rapor sozlugu dondurur (saf; dosya yazmaz)."""
    yeni = [u for u in urunler if isinstance(u, dict) and u.get("id") in yeni_ids]
    auto_sil, eskalasyon, marka_kirli = [], [], []
    haric = set()
    gerekce_map = {}

    for u in yeni:
        uid = u.get("id")
        kayit = kaynaklar.get(uid)
        # 1 lisans
        kapi, g = kapi_lisans(u, kayit)
        if kapi:
            auto_sil.append({"id": uid, "kapi": kapi, "gerekce": g})
            haric.add(uid); gerekce_map.setdefault(uid, g)
        # 2 maket (auto_sil)
        hit = kapi_maket_auto(u)
        if hit:
            g2 = "olcekli-model/maket (YASAK): %r" % hit
            auto_sil.append({"id": uid, "kapi": "maket", "gerekce": g2})
            haric.add(uid); gerekce_map.setdefault(uid, g2)
        # 3 olcu (auto_sil)
        kapi, g = kapi_olcu(u, kayit)
        if kapi:
            auto_sil.append({"id": uid, "kapi": kapi, "gerekce": g})
            haric.add(uid); gerekce_map.setdefault(uid, g)
        # 2b logo eskalasyon — SADECE zaten auto_sil edilmediyse (gurultuyu kes)
        if uid not in haric:
            e = kapi_logo_eskalasyon(u)
            if e:
                eskalasyon.append({"id": uid, "kapi": "logo", "neden": e})
        # 6 marka kirli (rapor)
        mk = kapi_marka_kirli(u)
        if mk:
            marka_kirli.append(mk)

    # 4 gorsel cakisma (eskalasyon)
    eskalasyon.extend(kapi_gorsel_cakisma(yeni, urunler))

    # 5 dedup
    dedup, dedup_esk, dedup_sil = kapi_dedup(yeni, urunler, head_ids, kaynaklar, haric)
    eskalasyon.extend(dedup_esk)
    for d in dedup:
        for sid in d["sil"]:
            gerekce_map.setdefault(sid, "dedup: '%s' ikizi (tut: %s)" % (d["baslik"], d["tut"]))

    sil_ids = sorted(set([a["id"] for a in auto_sil] + dedup_sil))
    return {
        "yeni_sayi": len(yeni),
        "auto_sil": auto_sil,
        "dedup": dedup,
        "eskalasyon": eskalasyon,
        "marka_kirli": marka_kirli,
        "_sil_ids": sil_ids,
        "_gerekce": gerekce_map,
    }


# =============================================================================
# I/O + CLI
# =============================================================================
def _git(*args):
    try:
        p = subprocess.run(["git", "-C", ROOT, *args], capture_output=True)
        return p.returncode, p.stdout
    except Exception:
        return 1, b""


def _head_ids():
    rc, out = _git("show", "HEAD:urunler.json")
    if rc != 0:
        return None
    try:
        d = json.loads(out.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(d, list):
        return None
    return {u.get("id") for u in d if isinstance(u, dict) and u.get("id") is not None}


def _oku_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _uygula(sil_ids, gerekce_map):
    """auto_sil + dedup.sil id'lerini duzelt.py --sil ile SIRAYLA uygular (flock+guard)."""
    ok, hata = [], []
    for uid in sil_ids:
        gerekce = "denetim-kapisi: " + gerekce_map.get(uid, "otomatik eleme")
        p = subprocess.run(["python3", DUZELT, str(uid), "--sil", gerekce],
                           capture_output=True, text=True)
        if p.returncode == 0:
            ok.append(uid)
            print("  SILINDI %s" % uid)
        else:
            hata.append(uid)
            print("  HATA %s: %s" % (uid, (p.stderr or p.stdout).strip()), file=sys.stderr)
    return ok, hata


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--idler", nargs="*", help="'yeni' sayilacak id listesi (HEAD farki yerine)")
    ap.add_argument("--uygula", action="store_true",
                    help="auto_sil + dedup.sil'i duzelt.py --sil ile UYGULA (varsayilan: report-only)")
    ap.add_argument("--rapor", default=RAPOR, help="rapor JSON cikti yolu")
    args = ap.parse_args()

    urunler = _oku_json(URUNLER, None)
    if not isinstance(urunler, list):
        print("HATA: urunler.json okunamadi/dizi degil.", file=sys.stderr)
        return 2
    kaynaklar = _oku_json(KAYNAKLAR, {})
    if not isinstance(kaynaklar, dict):
        kaynaklar = {}

    head_ids = _head_ids()
    if head_ids is None:
        head_ids = set()

    if args.idler is not None:
        yeni_ids = set(args.idler)
    else:
        working_ids = {u.get("id") for u in urunler if isinstance(u, dict) and u.get("id") is not None}
        yeni_ids = working_ids - head_ids

    rapor = denetle(urunler, yeni_ids, head_ids, kaynaklar)

    # rapor dosyasini yaz (ic alanlari _'li disi)
    disa = {k: v for k, v in rapor.items() if not k.startswith("_")}
    try:
        os.makedirs(os.path.dirname(args.rapor), exist_ok=True)
        with open(args.rapor, "w", encoding="utf-8") as f:
            json.dump(disa, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print("UYARI: rapor yazilamadi: %s" % e, file=sys.stderr)

    print("=== DENETIM KAPISI === yeni urun: %d" % rapor["yeni_sayi"])
    print("  auto_sil     : %d" % len(rapor["auto_sil"]))
    print("  dedup grubu  : %d (silinecek %d)"
          % (len(rapor["dedup"]), sum(len(d["sil"]) for d in rapor["dedup"])))
    print("  eskalasyon   : %d" % len(rapor["eskalasyon"]))
    print("  marka_kirli  : %d" % len(rapor["marka_kirli"]))
    print("  rapor -> %s" % args.rapor)

    if args.uygula:
        sil_ids = rapor["_sil_ids"]
        if not sil_ids:
            print("uygulanacak silme yok.")
            return 0
        print("--uygula: %d urun duzelt.py --sil ile kaldiriliyor..." % len(sil_ids))
        ok, hata = _uygula(sil_ids, rapor["_gerekce"])
        print("uygulandi: %d silindi, %d hata" % (len(ok), len(hata)))
        return 1 if hata else 0

    print("(report-only — silmek icin --uygula)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
