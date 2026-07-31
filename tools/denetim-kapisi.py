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
     KAYNAGA-OZEL: her platform lisansi KENDI natif biciminde saklar (MakerWorld/MMF CC'yi CIPLAK
     "BY"/"BY-SA"/"CC0" yazar, Cults3D code/insan-adi) -> o kaynagin KENDI satilabilir()'i HAM
     string'e uygulanir (makerworld/cults3d/myminifactory-api.py; tespit _kaynak_satilabilir_fn).
     Fallback (Printables/Thingiverse/bilinmeyen): serbest-metin lisans adi once lisans_kisaltma()
     ile kisaltmaya cevrilip printables-api.satilabilir() ile denetlenir. Her iki yol FAIL-CLOSED.
  2. MAKET / LOGO (OLCUM ile iki katman — RAPOR-MIMARA.md):
     - TIER-A auto_sil: olcekli-model/maket ARAÇ (maket/olcekli/diorama/minyatur/figur/
       "model araç"/"1/N olcek") — YASAK sinif, yanlis-pozitif dusuk.
     - TIER-B/C ESKALASYON (silme YOK): baslikta logo/amblem/plaket/rozet/koleksiyon
       ("logoyu cikar -> urun kalir mi" YARGISI mimara); + marka + kabartma/rolyef/
       detayli form (logo imasi ama 'logo' kelimesi yok). Islevsel parca logoyu
       TASIYABILIR -> auto-silme yanlis olur (olculdu: 68/102 aciklama-mention islevsel).
  3. OLCU: aciklamada olcu satiri ("A × B × C mm" / "Yaklasik dis olculer") yoksa -> auto_sil.
     Muaf: satin-alma (STL siparişte olculur), parametrik (olcuye ozel), VE ekleme aninda
     olculemeyen kaynaklar (MakerWorld/Cults3D/MyMiniFactory/CGTrader — login/OAuth-gated indirme;
     bkz _olcu_muaf_kaynak). Printables/Thingiverse MUAF DEGIL (olculu gelir) -> olcusuzu auto_sil.
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

# --- kaynak adaptorleri: her platformun KENDI satilabilir() TEK KAYNAK (bu dosyanin yaninda;
# DEGISTIRME). Printables = ortak yardimci (tr_lower) + fallback lisans yolu (serbest-metin ->
# lisans_kisaltma -> satilabilir); MakerWorld/Cults3D/MyMiniFactory KENDI natif-bicim lisanslarini
# dogru okuyan satilabilir()'i verir (bkz _kaynak_satilabilir_fn). Import ANINDA hicbiri ag/kimlik
# cagirmaz — hepsi tembel (satilabilir saf fonksiyon).
_TOOLS = os.path.dirname(os.path.abspath(__file__))


def _load_adaptor(dosya, modad):
    s = importlib.util.spec_from_file_location(modad, os.path.join(_TOOLS, dosya))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


pr = _load_adaptor("printables-api.py", "pr_api")
_mw = _load_adaptor("makerworld-api.py", "mw_api")
_c3 = _load_adaptor("cults3d-api.py", "c3_api")
_mmf = _load_adaptor("myminifactory-api.py", "mmf_api")
tr_lower = pr.tr_lower

# --- olcu ifadesi: OTOMATIK URETILEN CAPALI IFADEye baglan -------------------
# KUSUR-1 (MaCiT teshisi): eski gevsek desen (r"\d[\d\s.,×xX*+-]*mm\b") "aciklamada HERHANGI
#   mm-degeri var mi" bakiyordu -> gercek olcu satiriyla, aciklamadaki KISMI spec-mm degerini
#   ("M32×3.5 vida disi, ~31 mm dis cap") AYIRT EDEMIYOR; olcusuz urun "olculu" sayilip
#   auto_sil'den YANLIS-NEGATIF kaciyordu.
# KUSUR-2 (bagimsiz curutucu, GERCEK-VERI regresyonu): otomatik uretici iki-noktadan SONRA
#   etiket/parantez koyabiliyor: "... : taban 137 × 135 × 70 mm.", "... : iç parça 42 × 30 × 8 mm",
#   "Yaklaşık dış ölçüler (15 cm boyda): 113 × 117 × 150 mm.". Iki-noktadan HEMEN sonra \s*\d
#   isteyen bir desen bunlari KACIRIR -> gercekten olculu 40+ canli urun "olcusuz" sanilir
#   (Ictihat 71 kitlesel-silme).
# FIX: TAM capa ifadesine ("Yaklasik dis olculer" + eski ASCII yazim) baglan; sonra AYNI SATIRDA
#   (newline YOK) araya giren etiket/parantez metnine izin verip ilk "<sayi> … mm" boyut tokenina
#   lazy [^\n]*? ile ilerle. Capa ifadesinin kendisi ayirt edici — otomatik uretici bunu YALNIZ
#   gercek boyutla basar. Boylece:
#     * Turkce ("Yaklaşık dış ölçüler", 9990+ urun) + eski ASCII ("Yaklasik dis olculer"): her
#       Turkce harf icin ASCII fallback. Placeholder ("… : yok." / "- × - × - mm." / "Belirtilmemiş
#       × … mm") DIJIT tasimadigi icin eslesMEZ -> gercekten olcusuz kalir (dogru).
#     * Kismi spec-mm capa ifadesi TASIMADIGI icin hala False (KUSUR-1 giderme korunur).
#     * Gomulu/etiketli mesru satir (.search, satir-ici) hala True (Ictihat 71 korumasi + KUSUR-2).
_OLCU_PREFIX = r"Yakla[şs][ıi]k\s+d[ıi][şs]\s+[öo]l[çc][üu]ler"
_OLCU_RE = re.compile(_OLCU_PREFIX + r"[^\n]*?\d[\d\s.,×xX*+-]*mm\b", re.UNICODE)

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
# KAPI 7: MARIN FIYAT TABANI (Okan karari 30 Tem + AYNI GUN DUZELTME)
# TEK KAYNAK: /Users/okan/dev/pruvo-hasat/kalibrasyon/POLITIKA-KARARLARI.md
#             "2026-07-30 — DUZELTME: fiyat tabani karari YANLIS KAPSAMDA uygulanmisti"
#
# 🔴 KAPSAM YALNIZ `kategori == "Marin"`. BASKA KATEGORIYE DOKUNMAZ.
#   Ilk uygulama (commit 68837f62) kurali TUM katalogda duz 500 TL taban sanip 12.458 kaydi
#   yuvarladi; YANLISTI ve geri alindi (commit 1606e166: Otomobil 10.541 + Motosiklet 825 +
#   diger ~207 = 11.573 kayit ORIJINAL fiyatina donduruldu). Okan'in talebi bastan beri
#   YALNIZ Marin icindi ve duz taban degil KADEMELI ESLEME idi.
#   ⚠️ KAPSAM SIZMASININ BEDELI OLCULDU (30 Tem, 14.809 urun): Marin DISINDA 200 TL altinda
#   1.761 canli kayit var (100 TL'de 65 kayit dahil). Kapsam sizarsa bu kayitlar SESSIZCE
#   kirmizi yanar = tum ekibin urun akisi durur. Bu yuzden kategori kontrolu kapinin ILK
#   ifadesidir ve kapsam-sizmasi fikstoru (denetim-kapisi-test.py) bunu curutur.
#
# KADEMELI ESLEME (orijinal fiyat -> hedef) + BUCKET kurali (POLITIKA-KARARLARI.md):
#     <150 -> 200 · [150,200) -> 300 · [200,250) -> 350 · [250,500) -> 500 · 500+ dokunulmaz
#   ("170 TL" tabloda yoktu; [150,200) sayilip 150 ile ayni hedefe = 300 TL eslendi.)
#   Yani Marin'de FIILI ALT SINIR 200 TL'dir — 500 DEGIL.
#
# ⚠️ ESLEME ILERI-YONLU INVARYANT OLARAK KULLANILAMAZ (idempotent DEGIL): esleme 100->200
#   ve 200->350 der; yani kendi CIKTISI yeniden eslenirse daha yukari kayar. Canli Marin
#   dagilimi (OLCULDU): 300(5) · 350(627) · 500(291) · 600(2) · 650(9) · 900(1) — "hedefe
#   ESIT olmali" seklinde bir kural 632 CANLI kaydi yanlislikla kirmizi yakardi. Bu yuzden
#   ileri-yonlu kural TABANDIR (>=200); kademeli hedef yalnizca ihlal mesajinda ONERI olarak
#   raporlanir (isciye "kac TL olmali" der), karar verici degildir.
#
# MAKINE-KESIN + FAIL-CLOSED: karar tek bir SAYI karsilastirmasi; belirsizlik YOK.
# Ihlal SILME degil DUZELTME ister -> auto_sil'e DEGIL 'ihlal'e gider.
# OZEL-FORMAT NITELEYICI KORUNUR (OLCULDU: 2 kayit) — "500 TL/adel", "500 TL (30 cm)":
#   desen bastaki sayiya capalanir, niteleyici kuyruguna DOKUNMAZ -> ikisi de 500 = GECER.
# =============================================================================
FIYAT_KAPSAM_KATEGORI = "Marin"      # kapsam KILIDI — genisletme = 1.761 kaydi kirmizi yakar
MARIN_FIYAT_TABANI = 200.0           # kademeli eslemenin URETTIGI en dusuk hedef
_FIYAT_RE = re.compile(r"^\s*(\d[\d.,]*)\s*(?:tl|₺)", re.UNICODE)


def _fiyat_sayi(ham):
    """'850 TL'->850.0 · '1.250 TL'->1250.0 · '500 TL/adel'->500.0 · '500 TL (30 cm)'->500.0.
    Turkce bicim: '.' binlik ayirici, ',' ondalik. Ayristirilamayan -> None (cagiran
    FAIL-CLOSED davranir: None = ihlal, "belki yuksektir" varsayimi YOK)."""
    if not isinstance(ham, str):
        return None
    m = _FIYAT_RE.match(tr_lower(ham).strip())
    if not m:
        return None
    s = m.group(1)
    s = s.replace(".", "").replace(",", ".") if "," in s else s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


# =============================================================================
# KAPI 8: URETIM-SURECI IFSASI (Okan kurali, 30 Tem) — baslik/aciklamada baski ya da
# uretim SURECINE dair dil GECMEZ. ISLEV ve UYUM bilgisi KORUNUR.
#
# 🔴 NEDEN IKI KADEME (SERT vs UYARI): yanlis-pozitifin bedeli URUN AKISINI DURDURUR.
# Turkce cok-anlamlilik OLCULDU (30 Tem, canli katalog) — duz kelime taramasi MESRU
# kaydi yakalar:
#   * "destek" = hem DILIMLEYICI destegi hem KURULUM destegi hem FIZIKSEL destek parcasi
#     ("profesyonel destek gerektirmez" = usta destegi — 17 canli Otomobil kaydi;
#      "kaput destek cubugu" = fiziksel parca; "desteksiz direklerde" = YELKEN donanimi
#      terimi/istralsiz direk — 1 canli Marin kaydi).
#   * "basil-" = hem BASKI (print) hem BASMA (press) — "dugmeye basilmasini onler",
#     "tusa kazara basilmasi", "fitil yerine basilir" (OLCULDU: 8 canli kayit press).
#   * "baski" = hem PRINT hem BASINC ("yay baski olusturur").
#   * "dilimleme" = hem SLICER hem GIDA DILIMLEME MAKINESI (1 canli Elektronik kaydi).
#   * "3D yazici" = urunun HEDEF CIHAZI olabilir (yazici parcasi satiyoruz) — PRUVO'nun
#     kendi uretim sureci DEGIL (OLCULDU: 6 canli Elektronik/Kamera kaydi).
# Bu yuzden: iddia DAR tutulur. Kesin olan BLOKLAR (sert), supheli olan yalnizca
# ISARETLENIR (uyari) ve insan/isci karar verir. Supheli ifade OTOMATIK REDDEDILMEZ.
# =============================================================================

# --- cumle sinirlari: "0.10-0.20mm" gibi ondalik nokta cumle SONU sayilmaz -------------
_CUMLE_SON_RE = re.compile(r"[.!?](?=\s|$)|[\n;]", re.UNICODE)


def _cumle(metin, i, j):
    """[i,j) eslesmesini iceren CUMLEyi dondurur. Konjonksiyon kurallari 'ayni cumle'
    ister — pencere/karakter mesafesi degil (olculdu: 90-karakter penceresi komsu
    cumledeki alakasiz 'uretilir'i yanlis baglayip mesru kaydi SERT yakiyordu)."""
    bas, son = 0, len(metin)
    for m in _CUMLE_SON_RE.finditer(metin):
        if m.end() <= i:
            bas = m.end()
        elif m.start() >= j:
            son = m.start()
            break
    return metin[bas:son]


# --- MUAF-1 (KAYIT DUZEYI): urunun HEDEF CIHAZI bir 3D yazici -------------------------
# Yazici parcasi satarken "3D yazici" demek ZORUNLU ve MESRU — bu PRUVO'nun kendi uretim
# sureci DEGIL, urunun UYUM bilgisidir. Ama muafiyet KOSULLU: ayni metinde "yazici ILE/DA
# URETILIR/BASILIR" gecerse o BIZIM surecimizdir -> muafiyet DUSER (kacak deligi kapali).
_YAZICI_HEDEF_RE = re.compile(r"(3\s*[db]|3\s*boyutlu)\s*yaz[ıi]c[ıi]", re.UNICODE)
_YAZICI_BIZIM_RE = re.compile(r"yaz[ıi]c[ıi]\w*[^\n.]{0,40}?(bas[ıi]l|[üu]retil|imal\s*edil)",
                              re.UNICODE)


def _yazici_hedef_urun(metin):
    """Urunun hedefi bir 3D yazici mi (-> ifsa kapisi bu kayitta CALISMAZ)?"""
    if not _YAZICI_HEDEF_RE.search(metin):
        return False
    return _YAZICI_BIZIM_RE.search(metin) is None


# --- MUAF-2 (ESLESME DUZEYI): olculmus MESRU es-dizimler ------------------------------
# Her giris CANLI katalogda sayilmis bir yanlis-pozitif sinifidir; gerekce zorunlu.
_IFSA_MUAF = (
    (r"profesyonel\s+destek", "kurulumda USTA/servis destegi — dilimleyici destegi DEGIL"),
    (r"desteksiz\s+direk", "yelken donanimi terimi (istralsiz direk)"),
    (r"destek\s+(çubu|cubu|klips|braket|parça|parca|ayağ|ayag|kolu|pimi|halka|burc|burç|"
     r"eleman|mili|teli|sacı|saci|plaka)", "FIZIKSEL destek PARCASI (urunun kendisi)"),
    (r"dilimleme\s+makine", "GIDA dilimleme makinesi — slicer DEGIL"),
)
_IFSA_MUAF_RE = tuple((re.compile(d, re.UNICODE), g) for d, g in _IFSA_MUAF)

# press-anlami: "dugme/tus/butona basilir" = BASMA, baski DEGIL (ayni cumlede aranir)
_PRESS_RE = re.compile(r"d[üu][ğg]me|tu[şs]|buton|korna|pedal|fitil|ayak\s*day", re.UNICODE)

# --- SERT (KESIN-YASAK -> ihlal, BLOKLAR) ---------------------------------------------
# Her biri TEK BASINA kesin: Turkce'de baska mesru okumasi OLCULMEDI.
_IFSA_SERT = (
    ("dolgu-orani",
     r"(dolgu|doluluk)\s*oran|%\s*\d+\s*(dolgu|doluluk)|y[üu]ksek\s*(dolgu|doluluk)",
     "dolgu/doluluk orani = dilimleyici parametresi"),
    ("katman-yuksekligi",
     r"katman\s*y[üu]ksekli|bask[ıi]\s*katman",
     "katman yuksekligi = dilimleyici parametresi"),
    ("baski-yonu",
     r"bask[ıi]\s*y[öo]n|stl\s*y[öo]nlendirme|dilimleme\s*(s[ıi]ras[ıi]nda|[öo]neril|yap)",
     "baski yonu / dilimleme = uretim sureci"),
    ("baskiya-uygunluk",
     r"bask[ıi]ya\s*uygun|kolay\s*bask[ıi]|bask[ıi]\s*kolayl|bask[ıi]\s*alan",
     "baskiya uygunluk/baski alani = uretim sureci"),
    # ⚠️ 'nozzle/nozul' ve 'SLS' BILEREK BU LISTEDE DEGIL — OLCULDU (30 Tem, canli katalog):
    #   'nozul' OTOMOTIV parcasidir (far yikama nozulu BMW E46/Z4, sprey nozzle Audi e-tron,
    #   sanziman yagi degisim nozulu Toyota/Subaru, supurge nozulu Mercedes, silecek nozul
    #   hortumu VW) — 9 mesru canli kayit; 'SLS' Mercedes W126 SELF-LEVELLING SUSPENSION.
    #   Duz kelime olarak yasaklanirsa bu kayitlar SESSIZCE bloklanir. Dilimleyici anlamini
    #   yalniz OLCU ile birlikte gecen 'nozul capi' tasir -> asagida DAR desen.
    ("surec-teknolojisi",
     r"\bfdm\b|\bsla\b|\binfill\b|3\s*[db]\s*bas[ıi]l|3\s*boyutlu\s*bas[ıi]l"
     r"|\d+[.,]?\d*\s*mm\s*noz[uüz]l|noz[uüz]l\s*[çc]ap",
     "uretim teknolojisi adi (FDM/SLA/'3D basilabilir'/nozul CAPI)"),
)
_IFSA_SERT_RE = tuple((ad, re.compile(d, re.UNICODE), g) for ad, d, g in _IFSA_SERT)

# --- KONJONKSIYON (tek basina BELIRSIZ, birlikte KESIN — ayni cumlede) ----------------
_BASMA_RE = re.compile(
    r"bas[ıi]l(ab[ıi]l[ıi]r|ab[ıi]lece|[ıi]r|mas[ıi]|m[ıi][şs]|[ıi]p|mal[ıi]|an|"
    r"d[ıi][ğg][ıi]nda|d[ıi]ktan|acak|[ıi]nca)|\bbas[ıi]m\b", re.UNICODE)
# baski anlamini KESINLESTIREN surec jetonlari (malzeme / dilimleyici / yerlesim)
_SUREC_TOKEN_RE = re.compile(
    r"\bpla\b|\bpetg\b|\babs\b|\btpu\b|\basa\b|\btpe\b|filaman|filament"
    r"|dolgu|doluluk|destek|katman|yaz[ıi]c[ıi]|tabla|[çc][öo]z[üu]n[üu]rl[üu]k"
    r"|par[çc]a\s*halinde|par[çc]ada|par[çc]a\s*bas|ters\s*bas|yan\s*yat[ıi]r"
    r"|k[öo]pr[üu]|saatte|dakikada|solid|a[çc][ıi]yla|a[şs]a[ğg][ıi]\s*bakacak"
    r"|yatay\s*bas|dikey\s*bas|b[öo]l[üu]nerek", re.UNICODE)
_DESTEK_RE = re.compile(
    r"desteksiz|destek\s*gerektir|destek\s*olmadan|destek\s*malzeme|ek\s*destek"
    r"|destek\s*gereksinim", re.UNICODE)
_URETIM_FIILI_RE = re.compile(r"bas[ıi]l|bask[ıi]|[üu]retil|imal\s*edil", re.UNICODE)


# =============================================================================
# yardimcilar
# =============================================================================
def _kaynak_dict(kayit):
    return kayit if isinstance(kayit, dict) else {}


def _satin_alma(kayit):
    return isinstance(kayit, dict) and kayit.get("tur") == "satin-alma"


def _kendi_urunumuz(urun, kayit):
    """Kendi/uyelik IP'miz mi? (lisans/olcu kapisindan MUAF) — parametrik, uyelik (odemeli
    tedarikci), ya da kendi jeneratorumuz."""
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


# --- KAPI 1 (lisans) KAYNAGA-OZEL denetim — her platform lisansi KENDI natif biciminde saklar ----
# MakerWorld/MMF CC'yi CIPLAK yazar ("BY","BY-SA","CC0" — "CC-" oneki YOK); Cults3D code/insan-adi
# ("cc_by" / "CC BY - Attribution"). Bu bicimler pr.satilabilir()'in bekledigi "CC-BY" formuna UYMAZ
# ve lisans_kisaltma() de bunlari tanimaz -> HAM deger fail-closed False'a duser = GECERLI urun
# yanlislikla auto_sil (2026-07-18 Dacia partisi: 16/24 MakerWorld urunu yanlis-pozitif). COZUM: her
# kaynak KENDI adaptorunun satilabilir()'i ile denetlenir (kaynak-tespiti _olcu_muaf_kaynak deseniyle
# AYNI: once kayit['kaynak'], sonra link domaini). Fallback (Printables/Thingiverse/bilinmeyen) eski
# yol. CGTrader burada YOK — tur=satin-alma zaten lisans kapisindan MUAF (kapi_lisans basi).
_KAYNAK_SATILABILIR = {
    "makerworld": _mw.satilabilir,
    "cults3d": _c3.satilabilir,
    "myminifactory": _mmf.satilabilir,
}
_DOMAIN_SATILABILIR = (
    ("makerworld.com", _mw.satilabilir),
    ("cults3d.com", _c3.satilabilir),
    ("myminifactory.com", _mmf.satilabilir),
)


def _kaynak_satilabilir_fn(kayit):
    """Bu kaydin platformuna ait NATIF satilabilir() (HAM lisans string'ini DOGRUDAN alir; kisaltma
    YOK), yoksa None (-> fallback: lisans_kisaltma + pr.satilabilir). Tespit _olcu_muaf_kaynak ile
    AYNI desen: once kayit['kaynak'] (tr_lower), sonra _kaynak_link() domaini."""
    if isinstance(kayit, dict):
        fn = _KAYNAK_SATILABILIR.get(tr_lower(str(kayit.get("kaynak") or "")).strip())
        if fn is not None:
            return fn
    link = tr_lower(_kaynak_link(kayit))
    for dom, fn in _DOMAIN_SATILABILIR:
        if dom in link:
            return fn
    return None


# --- KAPI 3 (olcu) MUAF KAYNAKLAR — ekleme aninda VARSAYILAN olarak olcusuz gelen platformlar.
# MakerWorld/Cults3D/MyMiniFactory adaptorleri urunu OLCUSUZ ekler (indirme login/hesap/OAuth-gated;
# bkz makerworld-ekle.py / cults3d-ekle.py / myminifactory-ekle.py). Bunlar olcu kapisindan MUAF
# tutulmazsa gecerli urun yanlislikla auto_sil olur = urun kaybi. CGTrader zaten tur=satin-alma ile
# muaf; saglamlik icin kaynak adi/domaini de listede.
#   ⚠️ Printables/Thingiverse BU KUMEDE DEGIL — onlar ekleme aninda OLCULU gelir; olcusuzu HALA
#   auto_sil edilmeli (kapinin KALBI). Bu kumeye o iki kaynagi ASLA ekleme (bkz kaynak-entegrasyon-test.py).
_OLCU_MUAF_KAYNAK = {"makerworld", "cults3d", "myminifactory", "cgtrader"}
_OLCU_MUAF_DOMAIN = ("makerworld.com", "cults3d.com", "myminifactory.com", "cgtrader.com")


def _olcu_muaf_kaynak(kayit):
    """Kaynak, ekleme aninda VARSAYILAN olarak olculemeyen bir platform mu? (_printables_kaynak
    deseni) — tespit HEM kayit['kaynak'] alanindan (tr_lower) HEM _kaynak_link() domaininden.
    kayit dict VEYA string olabilir (ikisi de karsilanir). True -> olcu kapisi bu urunu auto_sil
    ETMEZ (olcu, siparis/indirme sonrasi alinir)."""
    if isinstance(kayit, dict) and tr_lower(str(kayit.get("kaynak") or "")).strip() in _OLCU_MUAF_KAYNAK:
        return True
    link = tr_lower(_kaynak_link(kayit))
    return any(dom in link for dom in _OLCU_MUAF_DOMAIN)


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
    """(auto_sil_kapi|None, gerekce). Satin-alma/kendi urunumuz -> muaf. Lisans HAM okunur; kaynak
    natif-bicim saklayan bir adaptorse (MakerWorld/Cults3D/MyMiniFactory) o platformun satilabilir()'i
    HAM string'e uygulanir, degilse (Printables/Thingiverse/bilinmeyen) lisans_kisaltma() ->
    pr.satilabilir() yolu kullanilir (bkz _kaynak_satilabilir_fn). Her iki yol da FAIL-CLOSED."""
    if _satin_alma(kayit) or _kendi_urunumuz(urun, kayit):
        return None, ""
    ham = _lisans_ham(kayit)
    if not ham or not str(ham).strip():
        return "lisans", "lisans kaydi yok/tanimsiz (fail-closed)"
    fn = _kaynak_satilabilir_fn(kayit)
    if fn is not None:                                  # kaynak-ozel natif kontrol (kisaltma YOK)
        if not fn(ham):
            return "lisans", "satilamaz lisans: %r (kaynak natif kontrol)" % ham
        return None, ""
    abbr = lisans_kisaltma(ham)                         # fallback: serbest-metin -> kisaltma
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
    """(auto_sil_kapi|None, gerekce). MUAF: satin-alma, parametrik, ya da ekleme aninda
    olculemeyen kaynak (MakerWorld/Cults3D/MyMiniFactory/CGTrader — bkz _olcu_muaf_kaynak).
    Printables/Thingiverse olcusuzu MUAF DEGIL -> auto_sil."""
    if _satin_alma(kayit) or bool(urun.get("parametrik")) or _olcu_muaf_kaynak(kayit):
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


def kademeli_hedef(n):
    """POLITIKA-KARARLARI.md bucket kurali: orijinal fiyat -> kademeli hedef.
    YALNIZ ihlal mesajinda ONERI uretmek icin (karar verici DEGIL — bkz. idempotentlik notu)."""
    if n >= 500:
        return n
    if n < 150:
        return 200.0
    if n < 200:
        return 300.0
    if n < 250:
        return 350.0
    return 500.0


def kapi_fiyat(urun):
    """(ihlal_kapi|None, gerekce) — KAPI 7. MAKINE-KESIN + FAIL-CLOSED sayi karsilastirmasi.

    🔴 KAPSAM KILIDI: kural YALNIZ kategori == 'Marin' urunlerine uygulanir. Diger her
    kategori KOSULSUZ gecer — Marin disinda fiyat kurali YOKTUR (POLITIKA-KARARLARI.md
    30 Tem DUZELTME). Bu ilk kontroldur; genisletilirse 1.761 canli kayit kirmizi yanar."""
    if urun.get("kategori") != FIYAT_KAPSAM_KATEGORI:
        return None, ""                           # KAPSAM DISI — kural bu kategoride YOK
    ham = urun.get("fiyat")
    if not isinstance(ham, str) or not ham.strip():
        if bool(urun.get("parametrik")):
            return None, ""                       # sari seri: fiyat BOS olmasi DOGRU
        return "fiyat", "Marin urununde fiyat BOS ve urun parametrik degil (fail-closed)"
    n = _fiyat_sayi(ham)
    if n is None:
        return "fiyat", "Marin urununde fiyat ayristirilamadi: %r (fail-closed)" % ham
    if n < MARIN_FIYAT_TABANI:
        return "fiyat", ("Marin fiyati %s = %g TL < taban %g TL -> kademeli eslemeye gore "
                         "%g TL olmali" % (ham, n, MARIN_FIYAT_TABANI, kademeli_hedef(n)))
    return None, ""


def _ifsa_muaf_eslesme(cumle):
    """Bu cumlede eslesmeyi MESRU kilan olculmus bir es-dizim var mi? -> gerekce|None."""
    for rx, gerekce in _IFSA_MUAF_RE:
        if rx.search(cumle):
            return gerekce
    return None


def kapi_ifsa(urun):
    """KAPI 8 — uretim-sureci ifsasi. ({sert:[...], uyari:[...]}) dondurur.
      sert  = KESIN-YASAK -> ihlal (BLOKLAR); duzeltilmeden parti gecmez.
      uyari = SUPHELI ama BELIRSIZ -> yalnizca isaretlenir, insan/isci karar verir.
    Kayit duzeyinde MUAF: urunun hedef cihazi bir 3D yazici (bkz _yazici_hedef_urun)."""
    metin = _metin(urun)
    if _yazici_hedef_urun(metin):
        return {"sert": [], "uyari": [],
                "muaf": "urunun HEDEF CIHAZI 3D yazici — baski sozlugu UYUM bilgisi"}
    sert, uyari = [], []

    def _kayit(hedef, ad, m, gerekce):
        c = _cumle(metin, m.start(), m.end())
        muaf = _ifsa_muaf_eslesme(c)
        if muaf:
            return
        hedef.append({"kural": ad, "ifade": m.group(0).strip(),
                      "cumle": c.strip()[:160], "gerekce": gerekce})

    # 1) tek basina KESIN olan desenler
    for ad, rx, gerekce in _IFSA_SERT_RE:
        for m in rx.finditer(metin):
            _kayit(sert, ad, m, gerekce)

    # 2) KONJONKSIYON: 'destek' + ayni cumlede URETIM FIILI -> KESIN (dilimleyici destegi)
    #    'destek' tek basina -> BELIRSIZ (fiziksel destek / kurulum destegi olabilir) -> uyari
    for m in _DESTEK_RE.finditer(metin):
        c = _cumle(metin, m.start(), m.end())
        if _ifsa_muaf_eslesme(c):
            continue
        if _URETIM_FIILI_RE.search(c):
            _kayit(sert, "destek-baski", m, "destek + uretim fiili ayni cumlede = dilimleyici destegi")
        else:
            _kayit(uyari, "destek-belirsiz", m,
                   "'destek' uretim fiili OLMADAN — fiziksel/kurulum destegi olabilir; INSAN karari")

    # 3) KONJONKSIYON: 'basil-' + ayni cumlede SUREC JETONU -> KESIN baski
    #    jetonsuz 'basil-' -> BELIRSIZ (press/basma anlami olabilir) -> uyari
    for m in _BASMA_RE.finditer(metin):
        c = _cumle(metin, m.start(), m.end())
        if _ifsa_muaf_eslesme(c) or _PRESS_RE.search(c):
            continue                              # "dugmeye basilmasi" = BASMA, baski DEGIL
        if _SUREC_TOKEN_RE.search(c):
            _kayit(sert, "baski-fiili", m, "baski fiili + surec jetonu ayni cumlede")
        else:
            _kayit(uyari, "basma-belirsiz", m,
                   "'basil-' surec jetonu OLMADAN — press/basma anlami olabilir; INSAN karari")
    return {"sert": sert, "uyari": uyari, "muaf": None}


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
    ihlal = []                                    # KAPI 7/8: BLOKLAR ama SILMEZ (duzeltilir)
    haric = set()
    gerekce_map = {}

    for u in yeni:
        uid = u.get("id")
        kayit = kaynaklar.get(uid)
        # 7 FIYAT TABANI (ihlal — silme DEGIL, tabana yuvarlama ister)
        kapi, g = kapi_fiyat(u)
        if kapi:
            ihlal.append({"id": uid, "kapi": "fiyat", "gerekce": g})
        # 8 URETIM-SURECI IFSASI: sert -> ihlal (bloklar), uyari -> eskalasyon (bloklamaz)
        ifsa = kapi_ifsa(u)
        for s in ifsa["sert"]:
            ihlal.append({"id": uid, "kapi": "ifsa/" + s["kural"],
                          "gerekce": "%s: %r — %s" % (s["gerekce"], s["ifade"], s["cumle"])})
        for w in ifsa["uyari"]:
            eskalasyon.append({"id": uid, "kapi": "ifsa-uyari/" + w["kural"],
                               "neden": "%s: %r — %s" % (w["gerekce"], w["ifade"], w["cumle"])})
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
        "ihlal": ihlal,
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


def _urunler_at(rev):
    """`git show <rev>:urunler.json` -> liste, okunamazsa None (fail-closed sinyali)."""
    rc, out = _git("show", "%s:urunler.json" % rev)
    if rc != 0:
        return None
    try:
        d = json.loads(out.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return d if isinstance(d, list) else None


def _commit_farki_ids():
    """CI KOLU: bu push'un urunler.json'a EKLEDIGI + DEGISTIRDIGI id'ler (HEAD^ -> HEAD).

    NEDEN AYRI KOL (31 Tem, OLCULDU): varsayilan PARTI tanimi calisma-agaci EKSI HEAD'dir.
    CI fresh checkout'unda calisma agaci HEAD ILE AYNIDIR -> parti DAIMA BOS -> kapi
    "yeni urun: 0 / IHLAL: 0" basip rc 0 doner. Yani bayraksiz kol CI'ya baglansaydi
    OLU NOBETCI olurdu (olculdu: git archive HEAD ile kurulan temiz checkout'ta rc=0,
    tum sayaclar 0). Bu kol ayni soruyu CI'da ANLAMLI olan eksende sorar: bu itme
    katalogda neyi degistirdi?

    Merge commit'inde HEAD^ = BIRINCI ata (onceki main) -> "bu itme main'e ne getirdi"
    semantigi korunur.

    FAIL-CLOSED: iki taraftan biri okunamazsa (shallow checkout / ilk commit / bozuk JSON)
    None doner ve cagiran OLCULEMEDI ile exit 3 verir — sessiz YESIL yok.
    """
    yeni = _urunler_at("HEAD")
    eski = _urunler_at("HEAD^")
    if yeni is None or eski is None:
        return None, None
    eski_map = {}
    for u in eski:
        if isinstance(u, dict) and u.get("id") is not None:
            eski_map[u["id"]] = json.dumps(u, sort_keys=True, ensure_ascii=False)
    ids = set()
    for u in yeni:
        if not isinstance(u, dict) or u.get("id") is None:
            continue
        uid = u["id"]
        imza = json.dumps(u, sort_keys=True, ensure_ascii=False)
        if uid not in eski_map or eski_map[uid] != imza:
            ids.add(uid)
    return ids, {u["id"]: u for u in eski
                 if isinstance(u, dict) and u.get("id") is not None}


def _urun_ihlalleri(u):
    """Tek urunun IHLAL kumesi -> {(kapi, gerekce)}. denetle()'deki 7/8 kollariyla AYNI
    fonksiyonlari cagirir (kopya kural YOK); 'onceden var miydi' karsilastirmasi icin."""
    s = set()
    if not isinstance(u, dict):
        return s
    kapi, g = kapi_fiyat(u)
    if kapi:
        s.add(("fiyat", g))
    ifsa = kapi_ifsa(u)
    for it in ifsa["sert"]:
        s.add(("ifsa/" + it["kural"],
               "%s: %r — %s" % (it["gerekce"], it["ifade"], it["cumle"])))
    return s


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


# =============================================================================
# KENDINI TEST — sentetik git deposu; repo dosyasi DEGISMEZ, ag/gizli kayit GEREKMEZ
# =============================================================================
def _kt_urun(uid, **kw):
    u = {"id": uid, "kategori": "Otomobil", "marka": ["Audi"],
         "baslik": "Audi A4 Uyumlu Braket %s" % uid,
         "aciklama": ("Araca birebir oturan dayanikli baglanti parcasi. "
                      "Yaklasik dis olculer: 40 × 30 × 12 mm."),
         "fiyat": "850 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}
    u.update(kw)
    return u


def kendini_test():
    """POZITIF (yanlis-pozitif nobeti) + NEGATIF (olu nobetci nobeti) + OLCULEMEDI + mutasyon."""
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="denetim-kapisi-kt-")
    depo = os.path.join(tmp, "depo")
    os.makedirs(depo)
    shutil.copytree(_TOOLS, os.path.join(depo, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    kapi = os.path.join(depo, "tools", os.path.basename(os.path.abspath(__file__)))
    urunler_yolu = os.path.join(depo, "urunler.json")

    def g(*a):
        subprocess.run(["git", "-C", depo, *a], capture_output=True)

    def yaz(liste):
        with open(urunler_yolu, "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False)

    def commit(mesaj):
        g("add", "-A")
        g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", mesaj)

    def kos(betik=None, ek=None):
        cmd = [sys.executable, betik or kapi, "--commit-farki",
               "--rapor", os.path.join(tmp, "rapor.json")]
        if ek:
            cmd += ek
        p = subprocess.run(cmd, cwd=depo, capture_output=True, text=True)
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    g("init", "-q")
    sonuc = []

    def iddia(ad, kosul, detay=""):
        sonuc.append((ad, bool(kosul), detay))

    # --- O1: HEAD^ YOK (tek commit) -> OLCULEMEDI, YESIL SAYILMAZ -----------------
    temiz = [_kt_urun("a1"), _kt_urun("a2")]
    yaz(temiz)
    commit("ilk")
    rc, out = kos()
    iddia("O1 HEAD^ YOK (shallow/ilk commit) -> OLCULEMEDI", rc == 3, "rc=%d" % rc)

    # --- P1: TEMIZ urun eklendi -> rc 0 ------------------------------------------
    yaz(temiz + [_kt_urun("a3")])
    commit("temiz urun eklendi")
    rc, out = kos()
    iddia("P1 temiz urun eklendi -> rc 0", rc == 0, "rc=%d" % rc)

    # --- P2: urunler.json HIC degismedi -> parti BOS, rc 0 ------------------------
    with open(os.path.join(depo, "not.md"), "w", encoding="utf-8") as f:
        f.write("urun disi degisiklik\n")
    commit("urun disi degisiklik")
    rc, out = kos()
    iddia("P2 urunler.json degismedi -> rc 0", rc == 0 and "yeni urun: 0" in out, "rc=%d" % rc)

    # --- P3: MESRU alan degisikligi (gorsel) -> rc 0 (yanlis-pozitif nobeti) ------
    taban = temiz + [_kt_urun("a3")]
    degisen = [dict(u) for u in taban]
    degisen[0]["gorseller"] = ["https://media.pruvo3d.com/urunler/a1-1-v2.jpg"]
    yaz(degisen)
    commit("gorsel guncellendi")
    rc, out = kos()
    iddia("P3 mesru alan degisikligi (gorsel) -> rc 0", rc == 0, "rc=%d" % rc)

    # --- N1: YENI urunde uretim-sureci ifsasi (dolgu orani) -> rc 1 ---------------
    kirli = _kt_urun("b1", aciklama="Saglamlik icin yuksek dolguyla (%100 dolgu) uretilir. "
                                    "Yaklasik dis olculer: 40 × 30 × 12 mm.")
    yaz(degisen + [kirli])
    commit("ifsali urun eklendi")
    rc, out = kos()
    iddia("N1 yeni urunde dolgu-orani ifsasi -> rc 1", rc == 1 and "ifsa" in out, "rc=%d" % rc)

    # temizle (sonraki vakalar icin taban)
    yaz(degisen)
    commit("ifsali urun geri alindi")

    # --- N2: YENI urunde baski fiili -> rc 1 --------------------------------------
    kirli2 = _kt_urun("b2", aciklama="Iki parca halinde basilip yapistirilarak birlestirilir. "
                                     "Yaklasik dis olculer: 40 × 30 × 12 mm.")
    yaz(degisen + [kirli2])
    commit("baski fiili iceren urun eklendi")
    rc, out = kos()
    iddia("N2 yeni urunde baski fiili ifsasi -> rc 1", rc == 1 and "ifsa" in out, "rc=%d" % rc)
    yaz(degisen)
    commit("geri alindi")

    # --- N3: VAR OLAN urun DEGISTIRILIP ifsa kazandi -> rc 1 ----------------------
    #     (bu iddia 'eklenen' degil 'DEGISEN' eksenini tasir; mutasyon bolumu bunu olcer)
    n3 = [dict(u) for u in degisen]
    n3[1] = dict(n3[1])
    n3[1]["aciklama"] = ("Yuksek dolgu ile uretilir. Yaklasik dis olculer: 40 × 30 × 12 mm.")
    yaz(n3)
    commit("var olan urun ifsa kazandi")
    rc, out = kos()
    iddia("N3 DEGISEN urun ifsa kazandi -> rc 1", rc == 1 and "ifsa" in out, "rc=%d" % rc)

    # --- N4: Marin fiyat tabani ihlali -> rc 1 ------------------------------------
    yaz(n3)
    commit("taban")
    marin = _kt_urun("m1", kategori="Marin", fiyat="150 TL",
                     baslik="Tekne Uyumlu Kilit Braketi m1")
    yaz(n3 + [marin])
    commit("marin taban alti fiyat")
    rc, out = kos()
    iddia("N4 Marin fiyati taban ALTI -> rc 1", rc == 1 and "fiyat" in out, "rc=%d" % rc)

    # --- P4: Marin fiyati taban USTU -> rc 0 (yanlis-pozitif nobeti) --------------
    yaz(n3)
    commit("geri alindi")
    marin_ok = _kt_urun("m2", kategori="Marin", fiyat="850 TL",
                        baslik="Tekne Uyumlu Kilit Braketi m2")
    yaz(n3 + [marin_ok])
    commit("marin taban ustu fiyat")
    rc, out = kos()
    iddia("P4 Marin fiyati taban USTU -> rc 0", rc == 0, "rc=%d" % rc)

    # --- P5: ONCEDEN VAR OLAN ihlale dokunan TOPLU islem -> rc 0 (metin DEGISMEDI) --
    #     (olculmus vaka: fiyat yuvarlama 12.458 kayda dokunup 417 eski ihlali kapsama sokar)
    yaz(n3)
    commit("p5 tabani")
    p5 = [dict(u) for u in n3]
    for i, u in enumerate(p5):
        p5[i] = dict(u)
        p5[i]["fiyat"] = "900 TL"          # TOPLU fiyat guncellemesi; aciklama DOKUNULMADI
    yaz(p5)
    commit("toplu fiyat guncellemesi (eski ifsa metni AYNEN duruyor)")
    rc, out = kos()
    _onceden_sifir = "onceden var  : 0" in out
    iddia("P5 toplu islem eski ihlale dokundu, metin AYNI -> rc 0 (bloklamaz)",
          rc == 0 and "onceden var" in out and not _onceden_sifir, "rc=%d" % rc)

    # --- N5: ONCEDEN ihlalli urun YENI/FARKLI bir ihlal kazandi -> rc 1 ------------
    n5 = [dict(u) for u in p5]
    n5[1] = dict(n5[1])
    n5[1]["aciklama"] = ("Yuksek dolgu ile uretilir; iki parca halinde basilip yapistirilir. "
                         "Yaklasik dis olculer: 40 × 30 × 12 mm.")
    yaz(n5)
    commit("eski ihlalli urun YENI ihlal kazandi")
    rc, out = kos()
    iddia("N5 eski ihlalli urun YENI ihlal kazandi -> rc 1", rc == 1, "rc=%d" % rc)

    # --- P6: temizlik commit'i (ihlal KALDIRILDI) -> rc 0 --------------------------
    p6 = [dict(u) for u in n5]
    p6[1] = dict(p6[1])
    p6[1]["aciklama"] = "Dayanikli baglanti parcasi. Yaklasik dis olculer: 40 × 30 × 12 mm."
    yaz(p6)
    commit("temizlik: ifsa kaldirildi")
    rc, out = kos()
    iddia("P6 temizlik commit'i (ifsa kaldirildi) -> rc 0", rc == 0, "rc=%d" % rc)

    # --- MUTASYON 2: 'onceden' filtresi HER SEYI susturursa N1 SESSIZ gecmeli ------
    with open(kapi, encoding="utf-8") as f:
        kaynak2 = f.read()
    hedef2 = ('if eski_u is not None and (it["kapi"], it["gerekce"]) in '
              '_urun_ihlalleri(eski_u):')
    mutant2 = os.path.join(depo, "tools", "_mutant2-denetim-kapisi.py")
    if hedef2 in kaynak2:
        with open(mutant2, "w", encoding="utf-8") as f:
            f.write(kaynak2.replace(hedef2, "if True:"))
        yaz(p6)
        commit("mutasyon2 tabani")
        yaz(p6 + [_kt_urun("z9", aciklama="Yuksek dolguyla uretilir. "
                                          "Yaklasik dis olculer: 40 × 30 × 12 mm.")])
        commit("mutasyon2: YENI ifsali urun")
        rc_s, _ = kos()
        rc_m, _ = kos(betik=mutant2)
        iddia("MU2 'onceden' filtresi ASIRI-SUSTURMA -> saglam KIRMIZI, mutant SESSIZ",
              rc_s == 1 and rc_m == 0, "saglam rc=%d, mutant rc=%d" % (rc_s, rc_m))
        os.remove(mutant2)
        yaz(p6)
        commit("mutasyon2 geri alindi")
    else:
        iddia("MU2 mutasyon capasi bulunamadi (OLCULEMEDI)", False, "capa yok")

    # --- MUTASYON: 'DEGISEN' ekseni NO-OP yapilirsa N3 SESSIZ gecmeli -------------
    with open(kapi, encoding="utf-8") as f:
        kaynak = f.read()
    hedef = "if uid not in eski_map or eski_map[uid] != imza:"
    mutant_yolu = os.path.join(depo, "tools", "_mutant-denetim-kapisi.py")
    if hedef in kaynak:
        with open(mutant_yolu, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(hedef, "if uid not in eski_map:"))
        # N3 vakasini yeniden kur
        yaz(n3)
        commit("mutasyon tabani")
        m3 = [dict(u) for u in n3]
        m3[2] = dict(m3[2])
        m3[2]["aciklama"] = "Yuksek dolgu ile uretilir. Yaklasik dis olculer: 40 × 30 × 12 mm."
        yaz(m3)
        commit("mutasyon: var olan urun ifsa kazandi")
        rc_saglam, _ = kos()
        rc_mutant, _ = kos(betik=mutant_yolu)
        iddia("MU1 'DEGISEN urun' ekseni NO-OP -> saglam KIRMIZI, mutant SESSIZ",
              rc_saglam == 1 and rc_mutant == 0,
              "saglam rc=%d, mutant rc=%d" % (rc_saglam, rc_mutant))
        os.remove(mutant_yolu)
    else:
        iddia("MU1 mutasyon capasi bulunamadi (OLCULEMEDI)", False, "capa yok")

    # --- O2: HEAD'deki urunler.json BOZUK (calisma agaci saglam) -> OLCULEMEDI -----
    with open(urunler_yolu, "w", encoding="utf-8") as f:
        f.write("{bozuk json")
    commit("bozuk katalog")
    yaz(n3)                                   # calisma agaci saglam, HEAD blob'u bozuk
    rc, out = kos()
    iddia("O2 HEAD'deki urunler.json BOZUK -> OLCULEMEDI", rc == 3, "rc=%d" % rc)

    shutil.rmtree(tmp, ignore_errors=True)

    print("DENETIM KAPISI — KENDINI TEST (--commit-farki CI kolu)")
    kalan = 0
    for ad, ok, detay in sonuc:
        print("  %s %-56s %s" % ("✅" if ok else "❌", ad, detay))
        if not ok:
            kalan += 1
    print("-" * 70)
    if kalan:
        print("SONUC: KIRMIZI ❌ — %d/%d iddia GECMEDI" % (kalan, len(sonuc)))
        return 1
    print("SONUC: YESIL ✅ — %d/%d iddia gecti" % (len(sonuc), len(sonuc)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--idler", nargs="*", help="'yeni' sayilacak id listesi (HEAD farki yerine)")
    ap.add_argument("--uygula", action="store_true",
                    help="auto_sil + dedup.sil'i duzelt.py --sil ile UYGULA (varsayilan: report-only)")
    ap.add_argument("--rapor", default=RAPOR, help="rapor JSON cikti yolu")
    ap.add_argument("--tum-katalog", action="store_true",
                    help="KAPI 7/8'i TUM katalogda kostur (denetim/olcum; parti farki yerine)")
    ap.add_argument("--commit-farki", action="store_true",
                    help="CI KOLU: parti = HEAD^ -> HEAD arasinda urunler.json'a eklenen/degisen "
                         "id'ler (fresh checkout'ta calisma-agaci farki DAIMA BOS oldugu icin)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="kapinin kendi kabul testi (sentetik depo; repo dosyasi DEGISMEZ)")
    args = ap.parse_args()

    if args.kendini_test:
        return kendini_test()

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

    if args.tum_katalog:
        yeni_ids = {u.get("id") for u in urunler
                    if isinstance(u, dict) and u.get("id") is not None}
    elif args.commit_farki:
        yeni_ids, onceki_urunler = _commit_farki_ids()
        if yeni_ids is None:
            print("OLCULEMEDI: HEAD ya da HEAD^ icindeki urunler.json okunamadi "
                  "(shallow checkout / ilk commit / bozuk JSON) — YESIL SAYILMAZ.",
                  file=sys.stderr)
            return 3
    elif args.idler is not None:
        yeni_ids = set(args.idler)
    else:
        working_ids = {u.get("id") for u in urunler if isinstance(u, dict) and u.get("id") is not None}
        yeni_ids = working_ids - head_ids

    rapor = denetle(urunler, yeni_ids, head_ids, kaynaklar)

    # --- CI KOLU: yalnizca BU ITMENIN GETIRDIGI ihlaller BLOKLAR --------------------
    # 🔴 GEVSETME DEGIL, AYIRMA (31 Tem, OLCULDU). Katalogda 332 ONCEDEN VAR OLAN ihlal
    # duruyor (canli; ayri temizlik isi). Kapi ham haliyle baglansaydi urun-DISI bir toplu
    # islem bile tum ekibin itmesini durdururdu: olculdu, fiyat yuvarlama commit'i 68837f62
    # 12.458 kayda dokunuyor ve 417 ONCEDEN VAR OLAN ihlali parti kapsamina sokuyor
    # (1606e166: 12.195 kayit / 288 ihlal). Bunlar YANLIS-POZITIF DEGIL — gercek ihlaller —
    # ama o itmenin GETIRDIGI sey de degiller; bloklamak orantisiz ve kapiyi ilk toplu
    # islemde devre disi biraktirirdi.
    # KURAL: ayni (id, kapi, gerekce) ucluSU HEAD^'te de VARSA "onceden" sayilir -> RAPOR
    # edilir, BLOKLAMAZ. Yoksa bu itme GETIRMISTIR -> BLOKLAR. Karsilastirma denetle()'nin
    # kullandigi AYNI fonksiyonlarla yapilir (_urun_ihlalleri), kopya kural yok.
    # Sonuc: yeni urun ifsa ile gelirse BLOKLAR · var olan urun ifsa KAZANIRSA BLOKLAR ·
    # metni degismemis eski ihlale dokunan toplu islem BLOKLAMAZ · temizlik commit'i YESIL.
    onceden = []
    if args.commit_farki:
        kalan = []
        for it in rapor["ihlal"]:
            eski_u = onceki_urunler.get(it["id"])
            if eski_u is not None and (it["kapi"], it["gerekce"]) in _urun_ihlalleri(eski_u):
                onceden.append(it)
            else:
                kalan.append(it)
        rapor["ihlal"] = kalan

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
    print("  IHLAL        : %d (fiyat tabani / uretim-sureci ifsasi — BLOKLAR)"
          % len(rapor["ihlal"]))
    if args.commit_farki:
        print("  onceden var  : %d (HEAD^'te de vardi — bu itme GETIRMEDI, bloklamaz; "
              "ayri temizlik isi)" % len(onceden))
    print("  rapor -> %s" % args.rapor)

    if rapor["ihlal"]:
        print("\n=== IHLAL (duzeltilmeden parti GECMEZ) ===", file=sys.stderr)
        for it in rapor["ihlal"]:
            print("  %-46s [%s] %s" % (it["id"], it["kapi"], it["gerekce"]), file=sys.stderr)

    if args.uygula:
        sil_ids = rapor["_sil_ids"]
        if not sil_ids:
            print("uygulanacak silme yok.")
            return 0
        print("--uygula: %d urun duzelt.py --sil ile kaldiriliyor..." % len(sil_ids))
        ok, hata = _uygula(sil_ids, rapor["_gerekce"])
        print("uygulandi: %d silindi, %d hata" % (len(ok), len(hata)))
        return 1 if (hata or rapor["ihlal"]) else 0

    print("(report-only — silmek icin --uygula)")
    return 1 if rapor["ihlal"] else 0


if __name__ == "__main__":
    sys.exit(main())
