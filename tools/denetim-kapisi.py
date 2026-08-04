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
  2. MAKET / LOGO (OLCUM ile iki katman — kanit muhendis raporunda):
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

# --- KAPI 2: maket/logo tiers (OLCUM temelli — bkz. muhendis raporu) ----------
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
# KAPI 7: FIYAT TABANI — 200 TL, TUM KATALOG (Okan karari 31 Tem 2026)
# TEK KAYNAK: Okan karari 31 Tem — "200 TL taban artik TUM urunlere uygulanir".
# ONCEKI HAL: kural YALNIZ `kategori == "Marin"` kapsamindaydi
#             (/Users/okan/dev/pruvo-hasat/kalibrasyon/POLITIKA-KARARLARI.md, 30 Tem).
#
# 🔴 KAPSAM ARTIK TUM KATEGORILER. TEK ISTISNA = PARAMETRIK/SARI SERI:
#     (a) `parametrik` alani true OLAN kayit, VE/VEYA
#     (b) kategorisi Jeneratör (= sari seri kovasi) OLAN kayit,
#     (c) ...ve fiyat alani BOS olan kayit (sari seride fiyat `taban-fiyatlar.js`'ten gelir,
#         `urunler.json`'daki `fiyat` bilerek BOS birakilir).
#   OLCULDU (31 Tem, canli katalog 15.930 urun): (a) 23 · (b) 23 · (c) 23 kayit ve UCU DE
#   AYNI 23 kayda denk geliyor (parametrik-ama-fiyatli 0, bos-ama-parametrik-degil 0).
#   Yani istisna kumesi bugun TEK ve tutarli; ucunu de yazmak fail-safe (biri kayarsa
#   digeri tutar).
#
# ⚠️ KAPSAM GENISLETMESININ OLCULEN BEDELI (31 Tem): kapsam ici 15.907 kaydin 1.761'i
#   taban ALTINDA (Otomobil 1.758 · Oyun/Hobi 2 · Ev 1; en yogun 150 TL'de 1.109, 180 TL'de
#   392, 100 TL'de 65). Bu kayitlar DUZELTILMEDEN kapi tam katalogda kirmizidir. VERI
#   DUZELTMESI AYRI DUZLEM (MaCiT/duzelt.py) — kapi yalniz OLCER ve bloklar.
#   Kapi CI'ya `--commit-farki` ile baglidir: onceden VAR OLAN ihlal bloklamaz (bkz. main()
#   'onceden' filtresi), YENI/DEGISEN taban-alti fiyat BLOKLAR.
#
# 🔵 MARIN EKSENI KAYBOLMADI (eski davranis korunur):
#   - Kademeli esleme ONERISI (asagidaki kademeli_hedef) ihlal mesajinda DURUR.
#   - Marin'de fiyati BOS ve parametrik OLMAYAN kayit HALA fail-closed ihlaldir
#     (FIYAT_BOS_FAILCLOSED_KATEGORI). Okan'in "bos fiyat kapsam disi" istisnasi SARI
#     SERI gerekcelidir; Marin'in olculmus fail-closed ekseni bilerek YERINDE BIRAKILDI —
#     kapsam genislerken pozitif nobetci sessizce oldurulmez.
#
# KADEMELI ESLEME (orijinal fiyat -> hedef) + BUCKET kurali (POLITIKA-KARARLARI.md):
#     <150 -> 200 · [150,200) -> 300 · [200,250) -> 350 · [250,500) -> 500 · 500+ dokunulmaz
#   ("170 TL" tabloda yoktu; [150,200) sayilip 150 ile ayni hedefe = 300 TL eslendi.)
#   Yani FIILI ALT SINIR 200 TL'dir — 500 DEGIL.
#
# ⚠️ ESLEME ILERI-YONLU INVARYANT OLARAK KULLANILAMAZ (idempotent DEGIL): esleme 100->200
#   ve 200->350 der; yani kendi CIKTISI yeniden eslenirse daha yukari kayar. Canli Marin
#   dagilimi (OLCULDU): 300(5) · 350(627) · 500(291) · 600(2) · 650(9) · 900(1) — "hedefe
#   ESIT olmali" seklinde bir kural 632 CANLI kaydi yanlislikla kirmizi yakardi. Bu yuzden
#   ileri-yonlu kural TABANDIR (>=200); kademeli hedef yalnizca ihlal mesajinda ONERI olarak
#   raporlanir (isciye "kac TL olmali" der), karar verici degildir.
#
# MAKINE-KESIN + FAIL-CLOSED: karar tek bir SAYI karsilastirmasi; belirsizlik YOK.
#   Fiyat metninden sayi AYIKLANAMIYORSA (or. "sorunuz", "fiyat icin arayin") kayit
#   "gecerli" SAYILMAZ -> ihlal. "Belki yuksektir" varsayimi YOK.
# Ihlal SILME degil DUZELTME ister -> auto_sil'e DEGIL 'ihlal'e gider.
# OZEL-FORMAT NITELEYICI KORUNUR (OLCULDU: canli katalogda 2 kayit) — "400 TL/adel",
#   "300 TL (30 cm)": desen bastaki sayiya capalanir, niteleyici kuyruguna DOKUNMAZ ->
#   400/300 olarak okunur = taban ustu = GECER.
# =============================================================================
FIYAT_TABANI = 200.0                 # kademeli eslemenin URETTIGI en dusuk hedef = TABAN
# (eski `MARIN_FIYAT_TABANI` adi KALDIRILDI: kapsam artik Marin degil — Marin'i ima eden
#  bayat ad birakmak, kurali yeniden daraltan bir okuma davetiyesidir.)
# SARI/parametrik seri kovasi — kategori adi hem Turkce hem ASCII yazimla karsilanir
FIYAT_MUAF_KATEGORI = frozenset(("jeneratör", "jenerator"))
# Marin'in OLCULMUS fail-closed bos-fiyat ekseni (kapsam genislemesinde KORUNDU)
FIYAT_BOS_FAILCLOSED_KATEGORI = "Marin"
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


# --- MUAF-1 (ESLESME DUZEYI, 31 Tem — eskiden KAYIT duzeyiydi) ------------------------
# Urunun HEDEF CIHAZI bir 3D yazici olabilir (yazici parcasi satiyoruz). O zaman CIHAZIN
# KENDI SOZLUGU ("baski tablasi", "baski kafasi", "ekstruder", "filament beslemesi",
# "OctoPrint", "uzun baskilarda isinan anakart") ZORUNLU ve MESRU UYUM bilgisidir —
# PRUVO'nun kendi uretim sureci DEGIL.
#
# 🔴 NEDEN ARTIK KAYIT DUZEYI DEGIL (OLCULDU, canli katalog 15.755 kayit):
#   Eski surumde `_yazici_hedef_urun()` True donunce `kapi_ifsa()` HIC desen kosturmadan
#   bos donuyordu = ALL-OR-NOTHING. Olculdu: 6 muaf kaydin 3'unde kapinin KENDI SERT deseni
#   ateslIyordu (`filament` x2, `baski tabla` x2) ve muafiyet bunlari SESSIZCE yutuyordu.
#   Yutulanlarin arasinda GERCEK ihlal de vardi: `raspberry-pi-kamera-mount-chiron`
#   "az filament harcar" = BIZIM uretim EKONOMIMIZ, cihazin ozelligi degil.
#   ARTIK: muafiyet tek tek ESLESMEYE uygulanir; yalniz (a) kural _CIHAZ_MUAF_KURAL'daysa
#   VE (b) o CUMLEDE uretim-ekonomisi dili YOKSA. Kaydin geri kalani normal denetlenir.
_YAZICI_HEDEF_RE = re.compile(r"(3\s*[db]|3\s*boyutlu)\s*yaz[ıi]c[ıi]", re.UNICODE)
# KACAK DELIGI (31 Tem): eski desen YALNIZ ileri yonluydu (yazici -> fiil) ve yalniz
# `basıl/üretil/imal edil` FIILINI goruyordu. Kacaklar: ters siralama ("PETG ile basilir,
# 3D yazici uyumlu") ve baski'nin ISIM/cekim hali ("yazicida baskisi yapilir").
# ⚠️ CIPLAK `baski` BILEREK EKLENMEDI: "3D yazicilarin BASKI KAFASI" hedef cihaz parcasidir
#   (canli kayit: ctc-yazici-ust-kablo-tutucu) — ciplak `baski` o kaydi yanlislikla "BIZIM
#   surecimiz" sayip TUM cihaz sozlugu muafiyetini dusururdu. Yalniz surec ANLAMI tasiyan
#   cekimli bicimler alinir: baskisi / baskiya / baskida(n) / baskiyla / baski ile.
#   OLCULDU: 6 yazici-hedef kaydin HICBIRI bu genisletmeyle muafiyetini kaybetmiyor.
_YAZICI_BIZIM_RE = re.compile(
    r"yaz[ıi]c[ıi]\w*[^\n.]{0,40}?(?:bas[ıi]l|[üu]retil|imal\s*edil"
    r"|bask[ıi](?:s[ıi]|ya|d[ae]|yl[ae])|bask[ıi]\s+ile)"
    r"|(?:bas[ıi]l|[üu]retil|imal\s*edil)[^\n.]{0,40}?yaz[ıi]c[ıi]",
    re.UNICODE)

# Muafiyetin uygulanabilecegi KURAL adlari (cihaz sozlugu). Bunun DISINDAKI hicbir kural
# (dolgu/katman/malzeme-tavsiye/dilimleyici/dosya/3D-baski...) hedef-cihaz kaydinda bile
# muaf DEGILDIR — onlar hangi urunde gecerse gecsin BIZIM surecimizi anlatir.
# ⚠️ `makine-parametresi` (duvar/kabuk sayisi, brim, raft) BILEREK LISTEDE DEGIL: onlar
#   hedef cihazi yazici olan urunde de DILIMLEYICI ayaridir = BIZIM surecimiz. Bu yuzden
#   `baski tabla` / `isitmali tabla` (cihazin FIZIKSEL parcasi) o kuraldan cikarilip
#   muaf-edilebilir `baski-hacmi` kuraline tasindi.
_CIHAZ_MUAF_KURAL = frozenset((
    "filament", "filament-ekosistem", "baski-hacmi", "cihaz-baski-terimi",
))
# ... ve ayni CUMLEDE uretim EKONOMISI dili varsa muafiyet DUSER: "az filament harcar"
# cihazin ozelligi degil BIZIM maliyetimizdir (olculdu: chiron kaydi).
_URETIM_EKONOMISI_RE = re.compile(r"harca|t[üu]ket|tasarruf", re.UNICODE)


def _yazici_hedef_urun(metin):
    """Urunun hedefi bir 3D yazici mi? -> ESLESME duzeyi cihaz-sozlugu muafiyetinin ON
    KOSULU (kaydin tamamini SUSTURMAZ; bkz. kapi_ifsa._kayit)."""
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

# press-anlami: "dugme/tus/butona basilir" = BASMA, baski DEGIL (ayni cumlede aranir).
# 🔴 FAIL-OPEN KAPATILDI (31 Tem): desen SINIRSIZDI ve `tu[şs]` masum kelimelerin ICINDE
#   eslesiyordu — "kuTUSu" (585), "tuTUŞ" (162), cacTUS/loTUS/karTUŞu/röTUŞ... Bu, o cumledeki
#   GERCEK baski ifsasini SESSIZCE susturuyordu: susturucu kural, ihlali gorunmez yapiyordu.
#   Yuzey olculdu (tam katalog, 15930 kayit): 664 kayitta kelime-ICI eslesme, 32 farkli sarma
#   kelime — HICBIRI gercek press sozcugu degil.
# ✅ SOL kelime siniri (`\b`) eklendi; SAG sinir BILEREK YOK: Turkce eklemeli — "tuşuna",
#   "düğmesine", "butonuna", "pedalı" eslesmeye DEVAM etmeli.
# OLCULDU (fix oncesi/sonrasi, tam katalog): SERT 0 -> 0, UYARI 17 -> 17, yanlis-pozitif 0;
#   _BASMA_RE cumlelerinde GERCEK press susturmasi 8 -> 8 (kapsam DARALMADI), fail-open
#   susturmasi 0 (bugun net kacak yok — sinif acik, yuzey 664).
_PRESS_RE = re.compile(
    r"\b(?:d[üu][ğg]me|tu[şs]|buton|korna|pedal|fitil|ayak\s*day)", re.UNICODE)

# --- SERT (KESIN-YASAK -> ihlal, BLOKLAR) ---------------------------------------------
# Her biri TEK BASINA kesin: Turkce'de baska mesru okumasi OLCULMEDI.
# BICIM: (kural_adi, desen, gerekce, eleme|None)
#   `eleme` = O KURALA OZEL, cumle kapsamli yanlis-pozitif suzgeci. 🔴 KURAL-YEREL OLMAK
#   ZORUNDA: ayni suzgec _IFSA_MUAF gibi TUM kurallar icin yazilsaydi "dolgu contasi"
#   iceren bir cumledeki GERCEK malzeme-tavsiyesi ihlalini de susturur (fail-open).
_IFSA_SERT = (
    ("dolgu-orani",
     r"(dolgu|doluluk)\s*oran|%\s*\d+\s*(dolgu|doluluk)|y[üu]ksek\s*(dolgu|doluluk)",
     "dolgu/doluluk orani = dilimleyici parametresi",
     None),
    ("katman-yuksekligi",
     r"katman\s*y[üu]ksekli|bask[ıi]\s*katman",
     "katman yuksekligi = dilimleyici parametresi",
     None),
    ("baski-yonu",
     r"bask[ıi]\s*y[öo]n|stl\s*y[öo]nlendirme|dilimleme\s*(s[ıi]ras[ıi]nda|[öo]neril|yap)",
     "baski yonu / dilimleme = uretim sureci",
     None),
    ("baskiya-uygunluk",
     r"bask[ıi]ya\s*uygun|kolay\s*bask[ıi]|bask[ıi]\s*kolayl|bask[ıi]\s*alan",
     "baskiya uygunluk/baski alani = uretim sureci",
     None),
    # ⚠️ 'nozzle/nozul' ve 'SLS' BILEREK BU LISTEDE DEGIL — OLCULDU (30 Tem, canli katalog):
    #   'nozul' OTOMOTIV parcasidir (far yikama nozulu BMW E46/Z4, sprey nozzle Audi e-tron,
    #   sanziman yagi degisim nozulu Toyota/Subaru, supurge nozulu Mercedes, silecek nozul
    #   hortumu VW) — 9 mesru canli kayit; 'SLS' Mercedes W126 SELF-LEVELLING SUSPENSION.
    #   Duz kelime olarak yasaklanirsa bu kayitlar SESSIZCE bloklanir. Dilimleyici anlamini
    #   yalniz OLCU ile birlikte gecen 'nozul capi' tasir -> asagida DAR desen.
    ("surec-teknolojisi",
     r"\bfdm\b|\bsla\b|\binfill\b|3\s*[db]\s*bas[ıi]l|3\s*boyutlu\s*bas[ıi]l"
     r"|\d+[.,]?\d*\s*mm\s*noz[uüz]l|noz[uüz]l\s*[çc]ap",
     "uretim teknolojisi adi (FDM/SLA/'3D basilabilir'/nozul CAPI)",
     None),
    # --- 31 Tem: KAPININ HIC GORMEDIGI SINIF (olculdu, canli katalog) ----------------
    # Eski kapi malzeme adini YALNIZ 'basil-' fiiliyle birlikte goruyordu; fiilsiz gecen
    # surec dili hicbir kovaya dusmuyordu. Olculen kacaklar: 'filament' (10 kayit),
    # 'TPU/PETG ana govde onerilir', 'iplik yonleri boyuna gelecek', 'baski tablasi',
    # 'duvar sayisi', 'STL dosyasi dahildir', 'baskisi daha kolay'.
    ("filament",
     r"filaman\w*|filament\w*",
     "'filament' = MAKINENIN yemi, musterinin aldigi malzeme DEGIL",
     None),
    ("katman-iplik-yonu",
     r"iplik\s*y[öo]n|katman\s*y[öo]n|lif\s*y[öo]n|katman\s*[çc]izgi"
     r"|boyuna\s+gelecek\s+bi[çc]imde\s+[üu]retil",
     "katman/iplik YONU = yerlesim parametresi (kapi katman YUKSEKLIGINI goruyordu, YONU gormuyordu)",
     None),
    # ⚠️ 'raft'/'brim' \b ile: 'Alumicraft'/'Starcraft' icinde sinir YOK -> eslesmez (olculdu).
    # ⚠️ 31 Tem: 'baski tabla' / 'isitmali tabla' BU KURALDAN CIKARILDI -> muaf-edilebilir
    #   `baski-hacmi` kuralina tasindi. Gerekce: tabla hedef cihazin FIZIKSEL parcasidir
    #   (yazici urununde MESRU), duvar/kabuk sayisi ise her urunde DILIMLEYICI ayaridir.
    ("makine-parametresi",
     r"duvar\s*say|kabuk\s*say|perimeter|\bbrim\b|\braft\b",
     "duvar-kabuk sayisi / brim-raft = dilimleyici parametresi (hedef cihaz yazici OLSA BILE)",
     None),
    # ⚠️ 'cura' \b ILE: 'Acura' (Honda) 6 mesru canli kayitta geciyor — sinirsiz desen
    #    onlari SESSIZCE bloklardi (olculdu).
    ("dilimleyici",
     r"prusaslicer|\bcura\b|slic3r|superslicer|orcaslicer|bambu\s*studio"
     r"|ideamaker|simplify3d|dilimleyici|\bslicer\b",
     "dilimleyici (slicer) adi = uretim zinciri",
     None),
    # ⚠️ 'step' TEK BASINA yasak DEGIL (ingilizce/teknik metinde gecer); yalniz
    #    'STEP dosya' bigrami dosya ifsasidir.
    ("dosya-ifsasi",
     r"\bstl\b|\b3mf\b|\bgcode\b|\bg-code\b|\.f3d\b|\.stp\b|\b3dm\s*dosya|123dx"
     r"|step\s*dosya|fusion\s*360|solidworks|tinkercad|freecad|openscad|\bscad\b"
     r"|(?:cad|kaynak|d[üu]zenlenebilir|[çc]izim|proje)\s+dosya\w*"
     r"|dosya\w*\s+(?:dahil|i[çc]erir|verilir|eklidir)",
     "CAD/STL dosya ifsasi ya da dosya TESLIMI vaadi — PRUVO fiziksel parca satar",
     None),
    ("baskiya-uygunluk-2",
     r"bask[ıi]s[ıi]\s+(?:daha\s+)?kolay|bas[ıi]lmas[ıi]\s+(?:daha\s+)?kolay",
     "'baskisi daha kolay' — eski 'baski kolayl' deseninin KACIRDIGI bicimbirim",
     None),
    # =====================================================================================
    # 31 Tem — IKINCI TUR: ISIM/SIFAT EKSENI (kapinin OLCULMUS kor noktasi)
    # -------------------------------------------------------------------------------------
    # Kapi surec dilini FIIL ekseninde taniyordu ("3D basıl-", "dolgu oranı", "katman
    # yüksekliği"); katalogdaki sizinti ISIM/SIFAT ekseninde yaziliydi ("3D baskı",
    # "tam dolguda", "ince katmanla", "ekonomik baskı", "baskı yatağı", "yazıcı toleransı").
    # OLCULDU (canli katalog, 15.755 kayit): kapi SERT'te 0 kayit buluyordu, bagimsiz
    # tarama 112 kayit / 121 cumlede GERCEK ihlal buluyordu. Asagidaki 8 sinif o farki kapatir.
    #
    # 🔴 CIPLAK `bask[ıi]` KELIMESI BILEREK YOK — OLCULDU: 140 kayda carpar, 96'si MESRU
    #   (baski balata, baskiyla oturur, su baskini, baskili devre karti) = %69 yanlis-pozitif;
    #   ciplak `basıl-` %77, ciplak `dolgu` %44, ciplak `katman` %50, ciplak `yazıcı` %47.
    #   Bu yuzden HER desen DAR tamlamadir + kendi `eleme` suzgecini tasir.
    #   OLCULEN TOPLAM YANLIS-POZITIF (canli katalog, elle yargi): 0.
    # =====================================================================================
    ("3d-baski-isim",
     r"3\s*[db]\s*bask[ıi]|3\s*boyutlu\s*bask[ıi]|\b3d\s*print",
     "'3D baskı' ISIM hali — marka dil kuralinin DOGRUDAN ihlali (kapi yalniz FIILI goruyordu)",
     None),
    # ⚠️ `y[üu]ksek` BILEREK YOK: `dolgu-orani` zaten "yuksek dolgu"yu goruyor (mukerrer olmasin).
    ("dolgu-bicimleri",
     r"(?:tam|d[üu][şs][üu]k|hafif)\s*dolgu\w*|dolgu\w*\s+[üu]retil|dolgu\s*y[üu]zde"
     r"|%\s*\d+\s*doluluk|doluluk\s*ve\s*\d+\s*derece",
     "dolgu BICIMI ('tam dolguda uretilir') = dilimleyici parametresi",
     # canli yanlis-pozitif: 'icine hafif dolgu MALZEMESI konularak' (dalis yelegi tutamagi)
     r"dolgu\s*(?:malzeme|panel|conta|par[çc]a|klips|kapa|plaka|profil|eleman|uyum|ama[çc]l)"
     r"|dolgusu\b|dolgun\b|silikon\s*dolgu|s[üu]nger\s*dolgu|hava\s*dolgusuz|aral[ıi]k\s*dolgu"),
    ("katman-bicimleri",
     r"[ıi]nce\s*katman|katman\s*ayar|\d+[.,]\d+\s*mm\s*katman|katman\s*iz\w*",
     "katman BICIMI ('ince katmanla', '0,16 mm katman', 'katman izi') = dilimleyici parametresi",
     # 'katman ayrilmasi' = karbon fiberde FIZIKSEL tabaka ayrilmasi (canli Marin kaydi)
     r"katman\s*ayr[ıi]l|katmanl[ıi]\s*[şs]ekilde|iki\s*katman\s*aras"
     r"|y[üu]kselen\s*katman|ba[şs]ka\s*bir\s*katman"),
    ("yazici-makine-parki",
     r"yaz[ıi]c[ıi]\w*\s*(?:tolerans|ayar|tabla|y[üu]ksekli|limit|s[ıi]n[ıi]r)"
     r"|yaz[ıi]c[ıi]lar[ıa]\w*\s*(?:uygun|s[ıi][ğg]|uyar)|baz[ıi]\s*yaz[ıi]c[ıi]lar"
     r"|yaz[ıi]c[ıi]larda\s*bas[ıi]l",
     "MAKINE PARKI ifsasi ('bazi yazicilarda olcek ayari', 'buyuk yazicilara sigmayabilir') — "
     "musteriye degil USTAYA yazilmis",
     None),
    # ⚠️ MUAF-EDILEBILIR (bkz _CIHAZ_MUAF_KURAL): hedef cihazi 3D yazici olan urunde
    #   "baski tablasi" cihazin FIZIKSEL parcasidir (canli: iki Raspberry Pi kamera montaji).
    ("baski-hacmi",
     r"bask[ıi]\s*(?:yata[ğg]|platform|tabla|boyut\s*s[ıi]n[ıi]r|limit|hacim)"
     r"|masa[üu]st[üu]\s*bask[ıi]|bask[ıi]\s*s[üu]re|bask[ıi]\s*maliyet"
     r"|[ıi]s[ıi]tmal[ıi]\s*tabla",
     "baski HACMI / makine siniri ('baski yatagi boyutu', 'masaustu baski limiti', 'baski suresi')",
     r"bask[ıi]\s*(?:balata|plaka|pim|c[ıi]vata|bur[çc]|disk|nokta|apar|merkez)"
     r"|su\s*bask[ıi]n|bask[ıi]l[ıi]\s*devre|debriyaj"),
    # ⚠️ `tolerans` BU LISTEDE DEGIL -> UYARI kovasinda. OLCULDU: canli katalogdaki 2
    #   'baski tolerans' kaydinin IKISI DE BASINÇ okumasi (pres/gecme, termal zorlanma).
    ("baski-parametre",
     r"(?:ekonomik|h[ıi]zl[ıi]|hassas|basit|standart|dikey|yatay|d[üu]z|p[üu]r[üu]zl[üu]"
     r"|[çc]ok\s*renkli|iki\s*renkli|[çc]ok\s*malzemeli|deneme|[öo]rnek"
     r"|y[üu]ksek\s*[çc][öo]z[üu]n[üu]rl[üu]kl[üu])\s*bask[ıi]\w*"
     r"|bask[ıi]\s*(?:ayar|hassasiyet|deste|geometri|a[çc][ıi]s[ıi]|y[üu]zde|planlan"
     r"|teknik|yaz[ıi]l[ıi]m|kolayl)"
     r"|bask[ıi]\s*plastik|bask[ıi]\s*damga|bask[ıi]\s*d[ıi][şs][ıi]\s*par[çc]a"
     r"|bask[ıi]dan\s*[çc][ıi]kt|bask[ıi]\s*i[çc]inde|print-?in-?place|bask[ıi]\s*[öo]rnek",
     "baski PARAMETRE/SIFAT es-dizimi ('ekonomik baski', 'baski ayari', 'baski plastik') = surec dili",
     r"bask[ıi]\s*(?:balata|plaka|pim|c[ıi]vata|bur[çc]|disk|nokta|apar|merkez)"
     r"|bask[ıi]y[la]a?\s*(?:otur|tutun|ge[çc]|tak[ıi]l|s[ıi]k[ıi][şs]|yerle)"
     r"|su\s*bask[ıi]n|bask[ıi]l[ıi]\s*devre|sanat\s*bask[ıi]|debriyaj|bask[ıi]\s*ge[çc]me"),
    # ⚠️ MUAF-EDILEBILIR: bunlar hedef cihazi yazici olan urunde CIHAZIN sozlugudur
    #   ("baski kafasi kablo demeti", "baskilarinizi kameradan izleyin", "uzun baskilarda
    #   isinan anakart"); BASKA her urunde BIZIM surecimizdir.
    ("cihaz-baski-terimi",
     r"bask[ıi]\s*kafa|bask[ıi]\s*takip|bask[ıi]lar[ıi]n[ıi]z|uzun\s*bask[ıi]",
     "cihaz-baski terimi (baski kafasi/takibi, uzun baskilar) — hedef cihaz 3D yazici DEGILSE ifsa",
     None),
    # ⚠️ `ekstr[uü]zyon` DISARIDA: aluminyum EKSTRUZYON profili 2 mesru canli kayitta geciyor.
    ("filament-ekosistem",
     r"octoprint|\bspool\b|\bhotend\b|\bheatsink\b|ekstr[uü]der",
     "filament ekosistemi (OctoPrint/spool/hotend/heatsink/ekstruder) = uretim zinciri",
     None),
    ("basil-print",
     r"par[çc]a\s*(?:olarak|h[âa]linde)\s*bas[ıi]l|bas[ıi]labilen|bas[ıi]lmaya\s*uygun"
     r"|bas[ıi]l[ıi]p\s*yap[ıi][şs]",
     "'basıl-' PRINT anlaminda ('parca olarak basilabilen') — konjonksiyon kolu SUREC JETONU "
     "istedigi icin kaciyordu",
     # press-anlami: "dugmeye basilabilen" = BASMA.
     # ⚠️ KELIME SINIRI ZORUNLU: sinirsiz `tu[şs]` "kuTUSu" icinde eslesir ve GERCEK ihlali
     #   susturur (OLCULDU: 'kayak-trolling-motoru-direksiyon-montaji' — "servo KUTUSU ust ve
     #   alt yarim parca olarak basilir" sinirsiz desende sessizce dusuyordu = fail-open).
     r"\bd[üu][ğg]me\w*|\btu[şs]\w*|\bbuton\w*|\bkorna\w*|\bpedal\w*|\bfitil\w*|ayak\s*day"),
)

# --- UYARI (SUPHELI -> eskalasyon; BLOKLAMAZ) -----------------------------------------
# Ayni bicim: (kural_adi, desen, gerekce, eleme|None). Buraya konan bir sinif YAYINI
# DURDURMAZ, yalnizca mimar/isci onune duser.
_IFSA_UYARI = (
    ("baski-tolerans-belirsiz",
     r"bask[ıi]\s*tolerans",
     "'baskı toleransı' — PRINT toleransi da BASINÇ/gecme toleransi da olabilir; INSAN karari "
     "(olculdu: canli katalogdaki 2 kaydin ikisi de BASINÇ okumasi)",
     None),
)

# --- MUTASYON CAPASI (kendini-test BELLEKTE bu iki satirin arasina neutralize satiri
#     enjekte eder; diske mutant YAZILMAZ). Bu iki satiri BIRLESTIRME/SILME.
_IFSA_DESEN_ARA = {ad: d for ad, d, _g, _e in (_IFSA_SERT + _IFSA_UYARI)}
# --- MUTASYON CAPASI SONU ---
_IFSA_SERT_RE = tuple(
    (ad, re.compile(_IFSA_DESEN_ARA[ad], re.UNICODE), g,
     (re.compile(e, re.UNICODE) if e else None))
    for ad, _d, g, e in _IFSA_SERT)
_IFSA_UYARI_RE = tuple(
    (ad, re.compile(_IFSA_DESEN_ARA[ad], re.UNICODE), g,
     (re.compile(e, re.UNICODE) if e else None))
    for ad, _d, g, e in _IFSA_UYARI)

# --- MALZEME BEYANI  <->  MALZEME SECIM TAVSIYESI (KraL karari, 31 Tem) ---------------
# Malzeme ADI ihlal DEGIL: "PETG malzemededir" musteriye TESLIM EDILEN PARCANIN
# ozelligini bildirir ve ayri bir eksende ([[malzeme-envanteri-beyan-karari]],
# tools/malzeme-dayanak-test.py) zaten denetlenir. IHLAL olan, malzemenin URETICIYE
# bir SECIM olarak TAVSIYE edilmesidir ("PETG onerilir", "TPU ile uretilmesi onerilir"):
# bu musteriye degil USTAYA yazilmis bir baski-isi talimatidir.
# Olculdu (canli katalog, 31 Tem): 482 kayitta malzeme kisaltmasi var; bunlarin
# 128'i TAVSIYE kalibi (temizlendi), 70'i SAF BEYAN (dokunulmadi).
#
# ⚠️ 'ABS' DISAMBIGUASYONU: ABS ayni zamanda ANTI-LOCK FREN sistemidir — canli
#    katalogda 23 fren-baglamli vurus olculdu (ABS unitesi braketi, ABS sensor
#    kablosu, ABS kor tapa contasi). Fren nesnesi izleyen 'abs' MALZEME SAYILMAZ.
#    Bu ayrim BURADA (jeton duzeyinde) yapilir; cumle duzeyinde MUAF olarak
#    yazilsaydi ayni cumledeki GERCEK malzeme ihlalini de susturur (fail-open).
# ⚠️ HER IKI PARCA DA (?:...) ILE SARILI OLMAK ZORUNDA. Icinde ust-duzey '|' tasiyan
#    bir parcayi sarmadan bitistirmek, bitisigi YALNIZ SON alternatife baglar ve desen
#    "ciplak malzeme adi" haline gelir. Olculdu: sarmasiz surum canli katalogda
#    350 YANLIS-POZITIF verdi ("PETG malzemededir" gibi SAF BEYAN kayitlari).
_MALZEME_ADI = (r"(?:\bpla\+?\b|\bpetg(?:-cf)?\b|\btpu\b|\basa\b|\btpe\b|\bpctg\b|\bhips\b"
                r"|\bninjaflex\b"
                r"|\babs\b(?!\s*(?:fren|sens[öo]r|[üu]nite|pompa|pikap|hidrolik|mod[üu]l|kablo)))")
_TAVSIYE = (r"(?:öneril\w*|oneril\w*|tavsiye\s+edil\w*|tercih\s+edil\w*|gerekir|gerekli\w*"
            r"|kullan[ıi]lmas[ıi])")
_MALZ_TAVSIYE_RE = re.compile(
    _MALZEME_ADI + r"[^.\n;]{0,80}?" + _TAVSIYE +
    r"|" + _TAVSIYE + r"[^.\n;]{0,40}?" + _MALZEME_ADI, re.UNICODE)

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


def fiyat_muaf(urun):
    """SARI/PARAMETRIK SERI mi? -> fiyat taban kurali bu kayda UYGULANMAZ.
    (a) `parametrik` true VE/VEYA (b) kategori Jeneratör. Sari seride fiyat
    `taban-fiyatlar.js`'ten gelir, `urunler.json`'daki alan bilerek BOStur."""
    if bool(urun.get("parametrik")):
        return True
    return tr_lower(str(urun.get("kategori") or "")).strip() in FIYAT_MUAF_KATEGORI


def kapi_fiyat(urun):
    """(ihlal_kapi|None, gerekce) — KAPI 7. MAKINE-KESIN + FAIL-CLOSED sayi karsilastirmasi.

    🔴 KAPSAM = TUM KATEGORILER (Okan karari 31 Tem). Tek istisna parametrik/sari seri
    (fiyat_muaf) ve fiyat alani BOS olan kayit. Fiyat metninden sayi AYIKLANAMAZSA kayit
    'gecerli' SAYILMAZ -> ihlal (fail-closed; sessizce gecmez).

    🔵 Marin ekseni KORUNDU: Marin'de BOS fiyat + parametrik DEGIL hala fail-closed ihlal;
    kademeli esleme ONERISI ihlal mesajinda durur."""
    if fiyat_muaf(urun):
        return None, ""                           # SARI SERI — taban kurali kapsam disi
    ham = urun.get("fiyat")
    if ham is None or (isinstance(ham, str) and not ham.strip()):
        if urun.get("kategori") == FIYAT_BOS_FAILCLOSED_KATEGORI:
            return "fiyat", ("%s urununde fiyat BOS ve urun parametrik degil (fail-closed)"
                             % FIYAT_BOS_FAILCLOSED_KATEGORI)
        return None, ""                           # Okan: BOS fiyat kapsam DISI
    if not isinstance(ham, str):
        # ⚠️ "BOS" DEGIL, OKUNAMAYAN: sayi/liste/sozluk gelirse alan bozuktur. Canli katalogda
        #   bugun 15.930/15.930 kayit metin (OLCULDU) — yine de sessizce GECERLI sayilmaz.
        return "fiyat", "fiyat alani metin DEGIL: %r (fail-closed)" % (ham,)
    n = _fiyat_sayi(ham)
    if n is None:
        return "fiyat", "fiyat ayristirilamadi: %r (fail-closed — 'gecerli' SAYILMAZ)" % ham
    if n < FIYAT_TABANI:
        return "fiyat", ("fiyat %s = %g TL < taban %g TL -> kademeli eslemeye gore "
                         "%g TL olmali" % (ham, n, FIYAT_TABANI, kademeli_hedef(n)))
    return None, ""


def _ifsa_muaf_eslesme(cumle):
    """Bu cumlede eslesmeyi MESRU kilan olculmus bir es-dizim var mi? -> gerekce|None."""
    for rx, gerekce in _IFSA_MUAF_RE:
        if rx.search(cumle):
            return gerekce
    return None


def kapi_ifsa(urun):
    """KAPI 8 — uretim-sureci ifsasi. ({sert:[...], uyari:[...], muaf:[...]}) dondurur.
      sert  = KESIN-YASAK -> ihlal (BLOKLAR); duzeltilmeden parti gecmez.
      uyari = SUPHELI ama BELIRSIZ -> yalnizca isaretlenir, insan/isci karar verir.
      muaf  = ESLESTI ama olculmus bir gerekceyle DUSURULDU (denetim izi; hukme girmez).

    🔴 MUAFIYET DUZEYI = ESLESME (31 Tem). Eskiden kayit duzeyiydi: hedef cihazi 3D yazici
    olan bir urunde kapi HIC desen kosturmuyordu ve kendi SERT desenleri ateslese bile
    sessizce yutuluyordu (olculdu: 6 muaf kaydin 3'unde). Artik yalniz CIHAZ SOZLUGU
    kurallari (_CIHAZ_MUAF_KURAL) ve yalniz uretim-EKONOMISI dili tasimayan cumlelerde
    dusurulur; kaydin geri kalani normal denetlenir."""
    metin = _metin(urun)
    cihaz_hedef = _yazici_hedef_urun(metin)     # ESLESME muafiyetinin ON KOSULU
    sert, uyari, muaf = [], [], []

    def _kayit(hedef, ad, m, gerekce, eleme=None):
        c = _cumle(metin, m.start(), m.end())
        if _ifsa_muaf_eslesme(c):
            return
        if eleme is not None and eleme.search(c):
            return
        kayit = {"kural": ad, "ifade": m.group(0).strip(),
                 "cumle": c.strip()[:160], "gerekce": gerekce}
        if (cihaz_hedef and ad in _CIHAZ_MUAF_KURAL
                and not _URETIM_EKONOMISI_RE.search(c)):
            kayit["neden"] = ("hedef cihaz 3D yazici — CIHAZ SOZLUGU (uyum bilgisi), "
                              "PRUVO'nun uretim sureci DEGIL")
            muaf.append(kayit)
            return
        hedef.append(kayit)

    # 1) tek basina KESIN olan desenler
    for ad, rx, gerekce, eleme in _IFSA_SERT_RE:
        for m in rx.finditer(metin):
            _kayit(sert, ad, m, gerekce, eleme)

    # 1b) SUPHELI desenler -> uyari (bloklamaz)
    for ad, rx, gerekce, eleme in _IFSA_UYARI_RE:
        for m in rx.finditer(metin):
            _kayit(uyari, ad, m, gerekce, eleme)

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

    # 4) KONJONKSIYON: MALZEME ADI + TAVSIYE fiili ayni cumlede -> KESIN surec ifsasi.
    #    Malzeme adi TEK BASINA burada ARANMAZ: saf BEYAN ("PETG malzemededir") mesrudur.
    for m in _MALZ_TAVSIYE_RE.finditer(metin):
        _kayit(sert, "malzeme-tavsiye", m,
               "malzeme SECIMI ureticiye TAVSIYE ediliyor (baski-isi talimati); "
               "malzeme BEYANI serbest, TAVSIYESI degil")
    return {"sert": sert, "uyari": uyari, "muaf": muaf}


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
    ifsa_muaf = []                                # KAPI 8: ESLESTI ama gerekceyle dusuruldu (iz)
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
        # muafiyet IZI: hangi eslesme hangi gerekceyle dusuruldu (hukme GIRMEZ, gorunur olsun)
        for mf in ifsa.get("muaf") or ():
            ifsa_muaf.append({"id": uid, "kapi": "ifsa-muaf/" + mf["kural"],
                              "neden": "%s: %r — %s" % (mf["neden"], mf["ifade"], mf["cumle"])})
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
        "ifsa_muaf": ifsa_muaf,
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
    import types

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

    # --- N4b/N4c/P4b: KAPSAM GENISLEMESI (31 Tem) — taban artik TUM kategorilerde ---
    #     Marin DISI bir kategoride taban-alti YENI urun de BLOKLAMALI; sari seri
    #     (parametrik/Jeneratör, fiyat BOS) BLOKLAMAMALI. CI kolunun kapsam nobeti.
    yaz(n3)
    commit("geri alindi")
    oto_ucuz = _kt_urun("o1", kategori="Otomobil", fiyat="150 TL")
    yaz(n3 + [oto_ucuz])
    commit("otomobil taban alti fiyat")
    rc, out = kos()
    iddia("N4b Otomobil (Marin DISI) taban ALTI -> rc 1", rc == 1 and "fiyat" in out, "rc=%d" % rc)

    yaz(n3)
    commit("geri alindi")
    oto_okunmaz = _kt_urun("o2", kategori="Otomobil", fiyat="sorunuz")
    yaz(n3 + [oto_okunmaz])
    commit("ayristirilamayan fiyat")
    rc, out = kos()
    iddia("N4c fiyat AYIKLANAMIYOR -> rc 1 (fail-closed)", rc == 1 and "fiyat" in out, "rc=%d" % rc)

    yaz(n3)
    commit("geri alindi")
    sari = _kt_urun("s1", kategori="Jeneratör", fiyat="", parametrik=True,
                    baslik="Olcuye Ozel Ara Parca s1")
    yaz(n3 + [sari])
    commit("sari seri (parametrik, fiyat BOS)")
    rc, out = kos()
    iddia("P4b SARI seri (parametrik/Jeneratör, fiyat BOS) -> rc 0", rc == 0, "rc=%d" % rc)

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

    # =========================================================================
    # URETIM-DILI KOVASI (31 Tem) — POZITIF + NEGATIF + MUTASYON, kapi-ici
    # -------------------------------------------------------------------------
    # AYRIM: malzeme ADI ihlal DEGIL (BEYAN serbest); malzemenin URETICIYE SECIM
    # olarak TAVSIYE edilmesi ihlal. Kanaryalar bu ayrimin ve olculmus es-dizim
    # muafiyetlerinin (ABS=fren, Acura, Alumicraft/Starcraft, Shelly, otomotiv
    # nozul, gida dilimleme, yazici-hedef urun) bekcisidir.
    _T = ("Araca birebir oturan dayanikli baglanti parcasi. "
          "Yaklasik dis olculer: 40 × 30 × 12 mm.")

    def _sert(aciklama):
        return [s["kural"] for s in kapi_ifsa(_kt_urun("x1", aciklama=aciklama))["sert"]]

    _MUTANT = [
        ("malzeme-tavsiye/onerilir", "Dayaniklilik icin PETG onerilir. " + _T),
        ("malzeme-tavsiye/uretilmesi", "- TPU gibi esnek malzemeyle uretilmesi onerilir. " + _T),
        ("malzeme-tavsiye/ikili", "- TPU tampon iceriri, PETG ana govde onerilir. " + _T),
        ("malzeme-tavsiye/kullanilmasi", "Dayanikli bir malzeme (or. ABS) kullanilmasi onerilir. " + _T),
        ("malzeme-tavsiye/gerekir", "Esnek (flexible / TPU) malzemeyle uretilmesi gerekir. " + _T),
        ("filament", "- Deniz ortami icin ASA filament onerilir. " + _T),
        ("filament/ascii", "- Seffaf kirmizi filamanla uretilmesi onerilir. " + _T),
        ("katman-iplik-yonu", "Iplik yonleri boyuna gelecek bicimde uretildiginde dayanimi artirir. " + _T),
        ("katman-cizgisi", "Iki yari parca yapistirilarak katman cizgilerine dik yuk tasir. " + _T),
        ("baski-tablasi", "- V2 versiyonu kucuk baski tablalarina uygundur. " + _T),
        ("duvar-sayisi", "Tabani kalin tutulmus, duvar sayisi artirilmistir. " + _T),
        ("dilimleyici/prusa", "PrusaSlicer'da hazirlanmistir. " + _T),
        ("dilimleyici/cura", "Cura profili ile hazirlanmistir. " + _T),
        ("dosya/stl-step-f3d", "- STL/STEP/Fusion360 (.f3d) dosyalari dahildir. " + _T),
        ("dosya/cad-icerir", "- Farkli olculere uyarlanabilir CAD dosyasi icerir. " + _T),
        ("dosya/openscad", "OpenSCAD ile parametrik tasarlanmistir. " + _T),
        ("dosya/tinkercad", "Tinkercad ile modellenmistir. " + _T),
        ("baskisi-daha-kolay", "Tek yuzu duz (baskisi daha kolay, yine uyan) model. " + _T),
    ]
    _KANARYA = [
        ("saf malzeme BEYANI", "PETG malzemededir. " + _T),
        ("malzeme etiketi", "- Malzeme: PLA, mat yuzey. " + _T),
        ("malzeme + fayda", "ABS malzeme UV ve hava kosullarina dayaniklilik saglar. " + _T),
        ("malzeme + fayda 2", "TPU esnekligi sayesinde dayaniklidir. " + _T),
        ("musteri dili", "Dayanikli malzemeyle uretilir. " + _T),
        ("ABS = anti-lock FREN", "ABS sensor kablosunu tutan braket; montaj icin gerekir. " + _T),
        ("ABS = fren UNITESI", "ABS hidrolik unitesini sabitler; saglam montaj gerekir. " + _T),
        ("Acura (cura DEGIL)", "Honda ve Acura araclarda kullanilir; dikkat gerekir. " + _T),
        ("Alumicraft (raft DEGIL)", "Alumicraft teknelerin tahliye deliklerine takilir. " + _T),
        ("Starcraft (raft DEGIL)", "Starcraft Seaflite 12 yelkenlisine ozeldir. " + _T),
        ("Shelly (shell DEGIL)", "Akilli ev otomasyon butonu (Shelly) montajini barindirir. " + _T),
        ("otomotiv nozulu", "Far yikama nozulunu temizce kapatir. " + _T),
        ("step (dosya DEGIL)", "Step by step montaj anlatimi vardir. " + _T),
        ("gida dilimleme makinesi", "Dilimleme makinesi bicagi icin koruyucu. " + _T),
        ("temiz taban", _T),
    ]
    _sag = [ad for ad, m in _MUTANT if not _sert(m)]
    _fp = [(ad, _sert(m)) for ad, m in _KANARYA if _sert(m)]
    iddia("UD-MUT %d mutant KIRMIZI (sag kalan=olu iddia)" % len(_MUTANT),
          not _sag, "sag kalan: %s" % (_sag or "yok"))
    iddia("UD-KAN %d kanarya YESIL (yanlis-pozitif nobeti)" % len(_KANARYA),
          not _fp, "yanlis-pozitif: %s" % (_fp or "yok"))

    # yazici HEDEF urun muafiyeti YASIYOR mu (fail-open olmasin diye AYRI iddia)
    _yz = _sert("3D yazici filament makarasi tutucusu; filament beslemesini iyilestirir. " + _T)
    iddia("UD-MUAF yazici-hedef urunde 'filament' MESRU", not _yz, "kural: %s" % (_yz or "yok"))
    # ... ama ayni urun BIZIM surecimizi anlatirsa muafiyet DUSMELI
    _yz2 = _sert("3D yazici ile uretilir; dayaniklilik icin PETG onerilir. " + _T)
    iddia("UD-MUAF kacak deligi KAPALI ('yazici ile uretilir' -> muafiyet duser)",
          bool(_yz2), "kural: %s" % (_yz2 or "YOK — KACAK"))

    # =========================================================================
    # ISIM/SIFAT EKSENI (31 Tem, IKINCI TUR) — kapinin OLCULMUS kor noktasi
    # -------------------------------------------------------------------------
    # Kapi surec dilini FIIL ekseninde taniyordu; katalogdaki sizinti ISIM/SIFAT
    # ekseninde yaziliydi. Asagidaki mutantlarin HEPSI canli katalogdan alinmis
    # GERCEK cumlelerdir; kanaryalar ise ayni kelimelerin MESRU (basinc/fiziksel/
    # hedef-cihaz) okumalaridir — ciplak kelime taramasinin %44-96 yanlis-pozitif
    # verdigi olculdugu icin her desen DARDIR ve kendi eleme suzgecini tasir.
    _MUTANT2 = [
        ("A/3d-baski-isim", "⚠️ Yalnizca 3D baski parca satilmaktadir. " + _T),
        ("B/tam-dolguda", "Sert malzemeyle, tam dolguda uretilir. " + _T),
        ("B/dusuk-dolguyla", "Esnek malzemeden dusuk dolguyla uretilir. " + _T),
        ("B/dolgulu-uretilir", "Kalin cidarli ve dolgulu uretilir. " + _T),
        ("B/doluluk-derece", "Kurulumda 100% doluluk ve 80 derece degerleri ile. " + _T),
        ("C/ince-katmanla", "Sert malzemeyle, ince katmanla uretilir. " + _T),
        ("C/mm-katman", "TPU, 0.16 mm katman ile kullanim omru hedeflenmistir. " + _T),
        ("C/katman-ayari", "Dusuk katman ayariyla saglam oturus rapor edilmistir. " + _T),
        ("C/katman-izi", "Ozel doku yuzeyiyle katman izlerinin gorunmedigi kalemlik. " + _T),
        ("D/yazicilara-sigmaz", "Tam model buyuk yazicilara sigmayabilir. " + _T),
        ("D/bazi-yazicilar", "Bazi yazicilarda %1 civari olcek ayari gerekebilir. " + _T),
        ("D/yazici-toleransi", "Farkli yazici toleranslari icin iki delik olcusu icerir. " + _T),
        ("E/masaustu-limit", "Masaustu baski limitine gore iki parcaya bolunmustur. " + _T),
        ("E/baski-yatagi", "Kucuk, orta ve buyuk baski yatagi boyutlarina gore 3 secenek. " + _T),
        ("E/baski-suresi", "Kisa baski suresiyle hizli uretilebilir. " + _T),
        ("F/ekonomik-baski", "- Hizli ve ekonomik baski. " + _T),
        ("F/deneme-baskisi", "Kucuk bir deneme baskisi tavsiye edilir. " + _T),
        ("F/baski-yazilimi", "Yolcu kapisi icin baski yaziliminda ayna alinarak kullanilir. " + _T),
        ("F/baski-plastik", "Not: baski plastik rulmanlar dusuk hiz icindir. " + _T),
        ("F/print-in-place", "Baski-icinde-mentese (print-in-place) teknigiyle uretilir. " + _T),
        ("F/cozunurluklu", "Daha iyi sonuc icin yuksek cozunurluklu baski onerilir. " + _T),
        ("G/cihaz-terimi-baski-kafa", "Baski kafasi kablo demetini tutan ust destek. " + _T),
        ("G/cihaz-terimi-uzun-baski", "Uzun baskilarda isinan anakarti ufleyerek sogutur. " + _T),
        ("G/ekosistem", "Hotend ve heatsink icin koruyucu kapak; spool yuvasi vardir. " + _T),
        ("H/parca-olarak-basilir", "Servo kutusu ust ve alt yarim parca olarak basilir. " + _T),
        ("H/basilabilen", "Iki yarim halinde de basilabilen govdesi vardir. " + _T),
    ]
    _KANARYA2 = [
        ("dolgu PANELI (parca)", "Toyota Tacoma far dolgu paneli klipsi. " + _T),
        ("dolgu MALZEMESI konul", "Icine hafif dolgu malzemesi konularak suda yuzmesi saglanir. " + _T),
        ("dolgu contasi", "Dolgu contasi olarak kullanilan sizdirmazlik parcasi. " + _T),
        ("hava dolgusuz", "Hava dolgusuz tekerlek gobegi kapagi. " + _T),
        ("katman AYRILMASI (fiziksel)", "Karbon fiberin katman ayrilmasini onler. " + _T),
        ("iki katman arasi", "Iki katman arasinda conta gorevi gorur. " + _T),
        ("baskiyla oturur (BASINÇ)", "Yuvaya baskiyla oturur ve sabit kalir. " + _T),
        ("baski BALATA", "Baski balata merkezleme pimi seti. " + _T),
        ("su BASKINI", "Su baskinina karsi tahliye kapagi. " + _T),
        ("baskiLI DEVRE", "Baskili devre karti (PCB) tutucusu. " + _T),
        ("debriyaj baski plakasi", "Debriyaj baski plakasi hizalama aleti. " + _T),
        ("aluminyum EKSTRUZYON", "Aluminyum ekstruzyon profiline geciyor. " + _T),
        ("dugmeye BASILabilen (press)", "Dugmeye basilabilen kapak mandali. " + _T),
        ("baski TOLERANSI (SERT degil, UYARI)",
         "Cam kenari oturusunda daralan baski toleranslarina gore islevseldir. " + _T),
        ("sicaklik baski toleransi", "Naylon malzemede yuksek sicaklik baski toleransi. " + _T),
    ]
    _sag2 = [ad for ad, m in _MUTANT2 if not _sert(m)]
    _fp2 = [(ad, _sert(m)) for ad, m in _KANARYA2 if _sert(m)]
    iddia("IS-MUT %d isim/sifat mutanti KIRMIZI (sag kalan=olu iddia)" % len(_MUTANT2),
          not _sag2, "sag kalan: %s" % (_sag2 or "yok"))
    iddia("IS-KAN %d kanarya YESIL (yanlis-pozitif nobeti)" % len(_KANARYA2),
          not _fp2, "yanlis-pozitif: %s" % (_fp2 or "yok"))

    # 'baski tolerans' SERT DEGIL ama SESSIZ de DEGIL -> UYARI kovasinda gorunmeli
    def _uyari_ad(aciklama):
        return [w["kural"] for w in kapi_ifsa(_kt_urun("x2", aciklama=aciklama))["uyari"]]

    _tol = _uyari_ad("Cam kenari oturusunda daralan baski toleranslarina gore islevseldir. " + _T)
    iddia("IS-UYARI 'baski tolerans' UYARI kovasinda (sessizce dusmuyor)",
          "baski-tolerans-belirsiz" in _tol, "uyari: %s" % (_tol or "YOK — SESSIZ"))

    # --- MUAFIYET DUZEYI: ESLESME mi KAYIT mi (olculmus 6 canli kayit ekseni) -------
    _YZ = "Anet A6 3D yazici anakart fan tutucusu. "

    def _mf(aciklama):
        r = kapi_ifsa(_kt_urun("x3", aciklama=aciklama))
        return [s["kural"] for s in r["sert"]], [m["kural"] for m in r["muaf"]]

    _s, _m = _mf(_YZ + "Kamera kolu baski tablasini yandan gorecek sekilde kisaltilmistir. " + _T)
    iddia("ES-1 yazici-hedef: 'baski tablasi' MUAF (susturulmuyor, IZ birakiliyor)",
          not _s and "baski-hacmi" in _m, "sert=%s muaf=%s" % (_s, _m))
    _s, _m = _mf(_YZ + "Klipsler profile gecmeli, az filament harcar. " + _T)
    iddia("ES-2 yazici-hedef ama URETIM EKONOMISI ('az filament harcar') -> SERT",
          "filament" in _s, "sert=%s muaf=%s" % (_s, _m))
    _s, _m = _mf(_YZ + "Sert malzemeyle, tam dolguda uretilir. " + _T)
    iddia("ES-3 yazici-hedef kayitta 'tam dolguda' MUAF DEGIL (kural cihaz sozlugu disi)",
          "dolgu-bicimleri" in _s, "sert=%s muaf=%s" % (_s, _m))
    _s, _m = _mf(_YZ + "Tabani kalin tutulmus, duvar sayisi artirilmistir. " + _T)
    iddia("ES-4 yazici-hedef kayitta 'duvar sayisi' MUAF DEGIL (dilimleyici ayari)",
          "makine-parametresi" in _s, "sert=%s muaf=%s" % (_s, _m))
    _s, _m = _mf("3D yazicilarin baski kafasi kablo demetini tutan ust destek. " + _T)
    iddia("ES-5 'yazicilarin BASKI KAFASI' hedef cihaz sayiliyor (muafiyet AYAKTA)",
          not _s and "cihaz-baski-terimi" in _m, "sert=%s muaf=%s" % (_s, _m))
    _s, _m = _mf("PETG ile basilir; 3D yazici uyumlu braket. Baski tablasina duz oturur. " + _T)
    iddia("ES-6 KACAK: TERS siralama ('basilir ... 3D yazici') muafiyeti DUSURUYOR",
          "baski-hacmi" in _s, "sert=%s muaf=%s" % (_s, _m))
    _s, _m = _mf("3D yazicida baskisi yapilir. Baski tablasina duz oturur. " + _T)
    iddia("ES-7 KACAK: 'yazicida BASKISI yapilir' (isim hali) muafiyeti DUSURUYOR",
          "baski-hacmi" in _s, "sert=%s muaf=%s" % (_s, _m))

    # =========================================================================
    # KOD MUTASYONU — BELLEKTE (diske mutant YAZILMAZ)
    # -------------------------------------------------------------------------
    # 🔴 NEDEN BELLEKTE: diske yazilan mutant dosya dalda CANLI KALIR (olculdu).
    # Kaynak okunur, tek bir satir donusturulur, ayri bir modul olarak exec edilir;
    # repo dosyasina DOKUNULMAZ. Her mutant icin: SAGLAM kopya kurali YAKALAMALI,
    # MUTANT kopya SESSIZ kalmali. Mutantsiz kopya da AYRICA yesil dogrulanir.
    _KENDI = os.path.abspath(__file__)
    _CAPA = "# --- MUTASYON CAPASI SONU ---"

    def _yukle(donusum=None):
        with open(_KENDI, encoding="utf-8") as f:
            src = f.read()
        if donusum is not None:
            yeni = donusum(src)
            if yeni == src:
                return None                       # capa tutmadi -> OLCULEMEDI
            src = yeni
        mod = types.ModuleType("dk_mutant")
        mod.__file__ = _KENDI
        exec(compile(src, _KENDI + "#mutant", "exec"), mod.__dict__)
        return mod

    def _desen_olsun(ad):
        return lambda s: s.replace(_CAPA, _CAPA + '\n_IFSA_DESEN_ARA[%r] = r"(?!x)x"' % ad, 1)

    def _satir(eski, yeni):
        return lambda s: s.replace(eski, yeni, 1)

    _YZF = "Anet A6 3D yazici anakart fan tutucusu. "
    # (ad, kaynak donusumu, prob metni, kova, beklenen kural)
    _KOD_MUTANT = [
        ("K1 desen 3d-baski-isim olduruldu", _desen_olsun("3d-baski-isim"),
         "Yalnizca 3D baski parca satilmaktadir. " + _T, "sert", "3d-baski-isim"),
        ("K2 desen dolgu-bicimleri olduruldu", _desen_olsun("dolgu-bicimleri"),
         "Sert malzemeyle, tam dolguda uretilir. " + _T, "sert", "dolgu-bicimleri"),
        ("K3 desen katman-bicimleri olduruldu", _desen_olsun("katman-bicimleri"),
         "Sert malzemeyle, ince katmanla uretilir. " + _T, "sert", "katman-bicimleri"),
        ("K4 desen yazici-makine-parki olduruldu", _desen_olsun("yazici-makine-parki"),
         "Tam model buyuk yazicilara sigmayabilir. " + _T, "sert", "yazici-makine-parki"),
        ("K5 desen baski-hacmi olduruldu", _desen_olsun("baski-hacmi"),
         "Masaustu baski limitine gore iki parcaya bolunmustur. " + _T, "sert", "baski-hacmi"),
        ("K6 desen baski-parametre olduruldu", _desen_olsun("baski-parametre"),
         "- Hizli ve ekonomik baski. " + _T, "sert", "baski-parametre"),
        ("K7 desen cihaz-baski-terimi olduruldu", _desen_olsun("cihaz-baski-terimi"),
         "Baski kafasi kablo demetini tutan ust destek. " + _T, "sert", "cihaz-baski-terimi"),
        ("K8 desen filament-ekosistem olduruldu", _desen_olsun("filament-ekosistem"),
         "Hotend ve heatsink icin koruyucu kapak. " + _T, "sert", "filament-ekosistem"),
        ("K9 desen basil-print olduruldu", _desen_olsun("basil-print"),
         "Iki yarim halinde de basilabilen govdesi vardir. " + _T, "sert", "basil-print"),
        ("K10 UYARI deseni baski-tolerans olduruldu", _desen_olsun("baski-tolerans-belirsiz"),
         "Daralan baski toleranslarina gore islevseldir. " + _T, "uyari",
         "baski-tolerans-belirsiz"),
        ("K11 muafiyet KAYIT duzeyine dondu (all-or-nothing)",
         _satir("    sert, uyari, muaf = [], [], []",
                "    sert, uyari, muaf = [], [], []\n"
                "    if cihaz_hedef:\n"
                "        return {'sert': [], 'uyari': [], 'muaf': []}"),
         _YZF + "Klipsler profile gecmeli, az filament harcar. " + _T, "sert", "filament"),
        ("K12 _CIHAZ_MUAF_KURAL asiri genis (dolgu da muaf)",
         _satir('_CIHAZ_MUAF_KURAL = frozenset((\n    "filament"',
                '_CIHAZ_MUAF_KURAL = frozenset((\n    "dolgu-bicimleri", "filament"'),
         _YZF + "Sert malzemeyle, tam dolguda uretilir. " + _T, "sert", "dolgu-bicimleri"),
        ("K13 uretim-ekonomisi suzgeci olduruldu",
         _satir('_URETIM_EKONOMISI_RE = re.compile(r"harca|t[üu]ket|tasarruf", re.UNICODE)',
                '_URETIM_EKONOMISI_RE = re.compile(r"(?!x)x", re.UNICODE)'),
         _YZF + "Klipsler profile gecmeli, az filament harcar. " + _T, "sert", "filament"),
        ("K14 _YAZICI_BIZIM_RE kacak fixi geri alindi (ters siralama)",
         _satir('    r"yaz[ıi]c[ıi]\\w*[^\\n.]{0,40}?(?:bas[ıi]l|[üu]retil|imal\\s*edil"\n'
                '    r"|bask[ıi](?:s[ıi]|ya|d[ae]|yl[ae])|bask[ıi]\\s+ile)"\n'
                '    r"|(?:bas[ıi]l|[üu]retil|imal\\s*edil)[^\\n.]{0,40}?yaz[ıi]c[ıi]",',
                '    r"yaz[ıi]c[ıi]\\w*[^\\n.]{0,40}?(?:bas[ıi]l|[üu]retil|imal\\s*edil)",'),
         "PETG ile basilir; 3D yazici uyumlu braket. Baski tablasina duz oturur. " + _T,
         "sert", "baski-hacmi"),
        ("K15 basil-print elemesinde kelime siniri kaldirildi ('kuTUSu' fail-open)",
         _satir(r'r"\bd[üu][ğg]me\w*|\btu[şs]\w*|\bbuton\w*|\bkorna\w*|\bpedal\w*|\bfitil\w*'
                r'|ayak\s*day")',
                r'r"d[üu][ğg]me|tu[şs]|buton|korna|pedal|fitil|ayak\s*day")'),
         "Servo kutusu ust ve alt yarim parca olarak basilir. " + _T, "sert", "basil-print"),
        # K15'in IKIZI: ayni fail-open sinifi _PRESS_RE'de (konjonksiyon kolunun susturucusu)
        # 31 Tem'e kadar ONARILMAMISTI. Probe BILEREK dar: yalniz 'basil- + surec jetonu'
        # ('ters bas') kolunun yakalayabilecegi bir cumle — basil-print/malzeme-tavsiye
        # kovalari kapsamaz, boylece iddia baska kovanin sirtina binip OLU kalmaz.
        ("K16 _PRESS_RE kelime siniri kaldirildi ('kuTUSu' susturucu fail-open)",
         _satir(r'r"\b(?:d[üu][ğg]me|tu[şs]|buton|korna|pedal|fitil|ayak\s*day)", re.UNICODE)',
                r'r"d[üu][ğg]me|tu[şs]|buton|korna|pedal|fitil|ayak\s*day", re.UNICODE)'),
         "Sigorta kutusu ters basilir. " + _T, "sert", "baski-fiili"),
    ]

    _saglam_mod = _yukle()

    def _kural(mod, kova, aciklama):
        return [x["kural"] for x in mod.kapi_ifsa(_kt_urun("k1", aciklama=aciklama))[kova]]

    _capasiz, _saglam_sessiz, _mutant_konustu = [], [], []
    for ad, don, prob, kova, beklenen in _KOD_MUTANT:
        if beklenen not in _kural(_saglam_mod, kova, prob):
            _saglam_sessiz.append(ad)
            continue
        mut = _yukle(don)
        if mut is None:
            _capasiz.append(ad)
            continue
        if beklenen in _kural(mut, kova, prob):
            _mutant_konustu.append(ad)
    iddia("KM-SAGLAM mutantsiz kopya %d/%d probu YAKALIYOR (YESIL)"
          % (len(_KOD_MUTANT) - len(_saglam_sessiz), len(_KOD_MUTANT)),
          not _saglam_sessiz, "sessiz: %s" % (_saglam_sessiz or "yok"))
    iddia("KM-CAPA %d kod mutasyonunun capasi TUTTU" % len(_KOD_MUTANT),
          not _capasiz, "capa tutmayan: %s" % (_capasiz or "yok"))
    iddia("KM-MUT %d/%d kod mutanti KIRMIZI (sag kalan=olculmemis eksen)"
          % (len(_KOD_MUTANT) - len(_mutant_konustu) - len(_capasiz) - len(_saglam_sessiz),
             len(_KOD_MUTANT)),
          not _mutant_konustu, "sag kalan: %s" % (_mutant_konustu or "yok"))

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
    ap.add_argument("--envanter", action="store_true",
                    help="ENVANTER KOLU (BLOKLAMAZ): --tum-katalog ile birlikte kullanilir; "
                         "onceden var olan ihlalleri kural kural sayar ve rc 0 doner. "
                         "Yayin yolunu (deploy) BEKLETMEZ — ayri, bagimsiz bir CI isidir.")
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
    print("  IHLAL        : %d (fiyat tabani / uretim-sureci ifsasi%s)"
          % (len(rapor["ihlal"]), " — RAPORLAR, BLOKLAMAZ" if args.envanter else " — BLOKLAR"))
    print("  ifsa muaf    : %d (eslesti ama CIHAZ SOZLUGU gerekcesiyle dusuruldu)"
          % len(rapor.get("ifsa_muaf") or ()))
    if args.commit_farki:
        print("  onceden var  : %d (HEAD^'te de vardi — bu itme GETIRMEDI, bloklamaz; "
              "ayri temizlik isi)" % len(onceden))
    print("  rapor -> %s" % args.rapor)

    # === ENVANTER KOLU: BLOKLAMAYAN kural-kural dokum + rc 0 ==========================
    # 🔴 NEDEN BLOKLAMAZ (OLCULDU, 31 Tem): bu depoda kapi birikmesi yayin suresini 21 gunde
    # 15,6x uzatti ve musteriye 404 olarak yansidi. Katalogda ONCEDEN VAR OLAN ihlaller
    # (temizlik isi, ayri parti) bloklayici baglanirsa TUM EKIBIN yayini durur. Kural:
    # yeni/degisen kayit (--commit-farki) BLOKLAR · tam katalog RAPORLAR.
    if args.envanter:
        kural = defaultdict(set)
        for it in rapor["ihlal"]:
            kural[it["kapi"]].add(it["id"])
        print("\n=== ENVANTER (tum katalog, ONCEDEN VAR OLAN ihlaller — YAYINI DURDURMAZ) ===")
        print("  %-34s | %s" % ("kural", "kayit"))
        for k in sorted(kural, key=lambda x: (-len(kural[x]), x)):
            print("  %-34s | %d" % (k, len(kural[k])))
        print("  %-34s | %d" % ("TOPLAM AYRIK KAYIT",
                                len({it["id"] for it in rapor["ihlal"]})))
        print("  %-34s | %d" % ("TOPLAM VURUS", len(rapor["ihlal"])))
        print("  temizlik partisi -> tools/duzelt.py --toplu (ayri is; bu kol RAPORDUR)")
        return 0

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
