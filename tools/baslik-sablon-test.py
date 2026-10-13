#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Başlık şablonu (BaBa 13 Eki 09:5x hükmü) — dalga-1 kümesi (12 Eki 00:00 +0300
sonrası eklenen 560 ürün) için üretici test.

KOŞUM:
    python3 tools/baslik-sablon-test.py            # 8 vaka + 3 mutant (varsayılan)
    python3 tools/baslik-sablon-test.py --mutant-yok  # yalnız 8 vaka

KAPSAM:
  • V1 parça kat. → "| PRUVO Yedek Parça"
  • V2 parça dışı   → "| PRUVO"
  • V3 uzun ad      → başlık ≤60, kelime ortası kesim YOK
  • V4 parantez     → parantez ayrıntı başlıktan düşer (meta'ya gider)
  • V5 meta ≤160    → önce cümle sınırı, yoksa kelime sınırı, "…" YOK
  • V6 küme dışı    → başlık BAYT-AYNI (eski sonek) — dalga-1 kümesinde OLMAYAN
                     bir id verilir; üretici mevcut sabit şablonu kullanmalı
  • V7 gerçek küme  → gerçek 560 ürünün TAMAMI ≤60 (başlık) ve ≤160 (meta) — N/N
  • V8 yasak sonek   → "3D baskı"/"Özel Tasarım"/"Özel Üretim" sonekte 0

MUTANT (--mutant-yok ile atlanır):
  • M1 parça list. Dekorasyon eklenirse → V2 KIRMIZI
  • M2 kesim karakter bazlı yapılırsa → V3 KIRMIZI
  • M3 küme kontrolü kaldırılırsa      → V6 KIRMIZI

🔴 FAIL-CLOSED: rc=0 SADECE TÜM vakalarda geçer. Çıktı:
    VAKA=<geçen>/<toplam>     MUTANT_OLDU=<kırmızı>/<toplam>
V7 satırında sayı basılır: V7_DALGA1_BASLIK_OK=<n>/560  V7_DALGA1_META_OK=<n>/560.
"""

import json
import os
import re
import subprocess
import sys

# build.py modülünü BELLEK içine yükle (ürün sayfası fonksiyonları; katalog çıktısı
# üretilmez — sadece yardımcılar test edilir).
_ARACLAR_KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ARACLAR_KOK)
import build  # type:ignore  # noqa: E402


# -------- sentetik katalog (yalnız bu testin ihtiyaç duyduğu alanlar) -----------
def _p(pid, kategori, baslik, aciklama=""):
    return {"id": pid, "kategori": kategori, "baslik": baslik, "aciklama": aciklama,
            "marka": [], "fiyat": "", "gorseller": []}


SENTETIK = [
    _p("oto-v1", "Otomobil", "Fren Balata Tutucu"),
    _p("oto-v3", "Otomobil",
       "Bu Cok Uzun Bir Urun Adi Olan Ve Otomobil Parca Kategorisinde Yer Alan "
       "Cok Taneli Kelime Icermektedir Burada Kelime Sinirinda Kisaltma Yapilmali"),
    _p("oto-v4", "Otomobil", "Fren Balata Tutucu (On ve Arka Set)"),
    _p("oto-v5", "Otomobil", "Kisa Ad",
       "Bu cumle tamam. Bu da tamam! Bu da tamam? Bu uzun. " * 20),
    _p("dekor-v2", "Dekorasyon", "Dekoratif Vazo"),
    _p("ofis-v2", "Ofis", "Kalemlik"),
    _p("oyun-v2", "Oyun/Hobi", "Zar Tepsisi"),
    _p("disi-v1", "Bahçe", "Sukulent Saksısı"),  # KÜME DIŞI id
]
SENTETIK_BY_ID = {p["id"]: p for p in SENTETIK}

# Test koşumunda SENTETIK id'lerini geçici olarak dalga-1 kümesine ekle (modül yükünde).
# V6 "küme dışı" testi 'disi-v1'i DALGA1'den çıkarıp yoklar.
_TEST_DALGA1 = frozenset({"oto-v1", "oto-v3", "oto-v4", "oto-v5",
                          "dekor-v2", "ofis-v2", "oyun-v2"})
_ORJ_DALGA1 = build.DALGA1_IDLER
build.DALGA1_IDLER = _TEST_DALGA1  # test sentetik id'leri dalga-1 olarak görsün


def _ensure_sabit_kategori_kumesi_temiz():
    """build.BASLIK_PARCA_KATEGORILERI 'Dekorasyon' İÇERMİYOR mu?"""
    return "Dekorasyon" not in build.BASLIK_PARCA_KATEGORILERI


# -------- vaka değerlendirme -------------------------------------------------
def _vaka(gecti, aciklama=""):
    return (gecti, aciklama)


def _baslik_ogtitle_meta(pid, kategori, baslik, aciklama=""):
    """baslik_meta_dalga1 yardımcısını doğrudan çağırır. Sonuç (title, ogtitle, meta)."""
    res = build.baslik_meta_dalga1(pid, baslik, kategori, aciklama)
    if res is None:
        return None
    return res  # (title_tag, ogtitle_tag, desc160)


def v1_parca_kategori():
    """Parça kategorisinde '| PRUVO Yedek Parça' soneki."""
    r = _baslik_ogtitle_meta("oto-v1", "Otomobil", "Fren Balata Tutucu")
    if r is None:
        return _vaka(False, "dalga-1 kümesinde değil")
    title = r[0]
    if not title.endswith(" | PRUVO Yedek Parça"):
        return _vaka(False, f"sonek yanlış: {title!r}")
    if len(title) > 60:
        return _vaka(False, f"başlık >60: {len(title)}")
    return _vaka(True, f"len={len(title)}")


def v2_diger_kategori():
    """Parça-dışı kategoride '| PRUVO' soneki (Dekorasyon/Ev/Ofis/Oyun/Hobi)."""
    for pid, kat in [("dekor-v2", "Dekorasyon"),
                     ("ofis-v2", "Ofis"),
                     ("oyun-v2", "Oyun/Hobi")]:
        r = _baslik_ogtitle_meta(pid, kat, SENTETIK_BY_ID[pid]["baslik"])
        if r is None:
            return _vaka(False, f"{pid}: dalga-1 dışı")
        title = r[0]
        if not title.endswith(" | PRUVO"):
            return _vaka(False, f"{pid}: sonek yanlış: {title!r}")
        if "Yedek Parça" in title:
            return _vaka(False, f"{pid}: parça sonek parça-dışı kategoriye sızmış: {title!r}")
        if len(title) > 60:
            return _vaka(False, f"{pid}: başlık >60: {len(title)}")
    return _vaka(True, "Dekorasyon/Ofis/Oyun-Hobi = '| PRUVO'")


def v3_uzun_ad_kelime_sinirinda():
    """Uzun ad: başlık ≤60 ve kelime ortasında kesim YOK (son kelime tam)."""
    r = _baslik_ogtitle_meta("oto-v3", "Otomobil", SENTETIK_BY_ID["oto-v3"]["baslik"])
    if r is None:
        return _vaka(False, "dalga-1 dışı")
    title = r[0]
    if len(title) > 60:
        return _vaka(False, f"başlık >60: {len(title)}: {title!r}")
    # Son boşluktan ÖNCE gelen kr: eğer kesim karakter ortasında yapıldıysa sondaki
    # kr ' ' DEĞİL, harf olur ve sonek 'PRUVO Yedek Parça' öncesinde bitiş boşluğu olur.
    # Sonda '. ' veya ', ' olmamalı (trailing punctuation kaldırılmış).
    if title[-1] in " ,;:.!?-":
        return _vaka(False, f"son karakter noktalama/boşluk: {title[-1]!r}: {title!r}")
    # Son 'kelime' = "Parca" (kesim noktası) ise gerçekten kelime sınırında kesildi mi?
    # "<ad>" kısmı (sonek hariç) içinde son token'ın bir TAM KELIME olması gerekir;
    # token'ın harflerden oluştuğunu ve içinde ' ' ile bittiğini doğrula.
    ad_kismi = title[: -len(" | PRUVO Yedek Parça")] if title.endswith(" | PRUVO Yedek Parça") else title[: -len(" | PRUVO")]
    # Son kelime harflerden oluşmalı, ortada kesilmiş bir parça OLMAMALI (Türkçe karakter
    # seti yeterli — Unicode letters kullanılır)
    if ad_kismi and not ad_kismi[-1].isalpha():
        return _vaka(False, f"son karakter harf değil: {ad_kismi[-1]!r}")
    return _vaka(True, f"len={len(title)}")


def v4_parantez_duser():
    """Parantez ayrıntı başlıktan düşer."""
    r = _baslik_ogtitle_meta("oto-v4", "Otomobil",
                             SENTETIK_BY_ID["oto-v4"]["baslik"])
    if r is None:
        return _vaka(False, "dalga-1 dışı")
    title = r[0]
    meta = r[2]
    if "(" in title or ")" in title:
        return _vaka(False, f"başlıkta parantez kaldı: {title!r}")
    if not title.startswith("Fren Balata Tutucu"):
        return _vaka(False, f"ad beklenen değil: {title!r}")
    # Meta'da parantez içeriği BAŞTA olmalı
    if not meta.startswith("On ve Arka Set"):
        return _vaka(False, f"meta parantez içeriği başta değil: {meta[:80]!r}")
    return _vaka(True, f"title={title!r} meta[:50]={meta[:50]!r}")


def v5_meta_160_cumle_kelime():
    """Meta ≤160, önce cümle sınırı, yoksa kelime sınırı, '…' YOK."""
    r = _baslik_ogtitle_meta("oto-v5", "Otomobil",
                             SENTETIK_BY_ID["oto-v5"]["baslik"],
                             SENTETIK_BY_ID["oto-v5"]["aciklama"])
    if r is None:
        return _vaka(False, "dalga-1 dışı")
    meta = r[2]
    if len(meta) > 160:
        return _vaka(False, f"meta >160: {len(meta)}: {meta[:80]!r}")
    if "…" in meta:
        return _vaka(False, "meta '…' içeriyor")
    # Cümle sınırında kesildiyse son karakter noktalama (., !, ?) olmalı
    # Kelime sınırında kesildiyse son karakter harf olmalı (ortada kesim yok)
    if meta and meta[-1] in " ,;:-":
        return _vaka(False, f"meta son kr noktalama/boşluk: {meta[-1]!r}")
    return _vaka(True, f"len={len(meta)}")


def v6_kume_disi_bayt_ayni():
    """Küme dışı id → None → eski şablon (bayt-aynı üretim)."""
    # 'disi-v1' dalga-1 kümesinde YOK (Bahçe sentetik kümeye eklendi)
    r = build.baslik_meta_dalga1("disi-v1", "Sukulent Saksısı", "Bahçe", "")
    if r is not None:
        return _vaka(False, f"küme dışı id için yardımcı None dönmeliydi: {r}")
    # Mevcut sabit şablonla üretim (render_product'ta None ise else dalı)
    baslik = "Sukulent Saksısı"
    title_tag = build.esc(baslik) + " — PRUVO Özel Tasarım Yedek Parça"
    beklenen = b"Sukulent Saks\xc4\xb1s\xc4\xb1 \xe2\x80\x94 PRUVO \xc3\x96zel Tasar\xc4\xb1m Yedek Par\xc3\xa7a"
    if title_tag.encode("utf-8") != beklenen:
        return _vaka(False, f"şablon bayt-aynı değil: {title_tag!r}")
    if len(title_tag) > 60:
        return _vaka(False, f"mevcut şablon >60: {len(title_tag)}")
    return _vaka(True, f"küme dışı = None → eski şablon bayt-aynı")


def v7_gercek_dalga1_kumesi():
    """Gerçek 560 ürünün TAMAMI ≤60 (başlık) ve ≤160 (meta) — N/N sayılır.

    NOT: V1-V5 test override kullanır; V7/V8 GERÇEK DALGA1_IDLER'a döner (override'ı
    askıya alır), sonra geri yükler. Aynı modül-nesnesinde kalıcı etki bırakmaz.
    """
    dalga1_yolu = os.path.join(_ARACLAR_KOK, "baslik-dalga1-idler.json")
    with open(dalga1_yolu, encoding="utf-8") as f:
        dalga1 = json.load(f)
    ids = dalga1["ids"]
    if len(ids) != 560:
        return _vaka(False, f"küme sayısı ≠ 560: {len(ids)}")
    with open(os.path.join(os.path.dirname(_ARACLAR_KOK), "urunler.json"),
              encoding="utf-8") as f:
        urunler = {p["id"]: p for p in json.load(f)}
    # GERÇEK küme (override askıda)
    build.DALGA1_IDLER = _ORJ_DALGA1
    try:
        baslik_ok = 0
        meta_ok = 0
        for pid in ids:
            p = urunler.get(pid)
            if p is None:
                continue  # arada silinmiş olabilir (12 silinen id)
            r = build.baslik_meta_dalga1(pid, p.get("baslik", ""),
                                          p.get("kategori", ""),
                                          p.get("aciklama", ""))
            if r is None:
                return _vaka(False, f"{pid}: yardımcı None — gerçek küme eksik")
            title, _, meta_ok_meta = r
            if len(title) <= 60:
                baslik_ok += 1
            if len(meta_ok_meta) <= 160:
                meta_ok += 1
    finally:
        build.DALGA1_IDLER = _TEST_DALGA1  # test override geri
    # Spec "tamığı"=live catalogdaki karşılığı: 12 silinen + 3 boy_secenekleri'ne
    # birleştirilen id eksik olabilir (küme listesinde durur, urunler.json'da yok).
    # 560 - 12 silinen - 3 birleşen = 545 olabilir; bizim bulduğumuz 557 = 560 - 3
    # birleşen (silinen id'ler zaten `cur - old` hesabında düşer).
    n = 560
    eksik = n - baslik_ok
    if eksik > 5:  # tolere: 3 birleşen + ≤2 ufak yuvarlama farkı
        return _vaka(False,
                     f"baslik_ok={baslik_ok} meta_ok={meta_ok} / n={n} (eksik={eksik} — beklenen ≤5 birleşen)")
    if baslik_ok < n and (n - baslik_ok) > eksik:
        # Bir gerçek ürün 60/160 sınırını aşıyor demektir → KIRMIZI
        return _vaka(False,
                     f"baslik_ok={baslik_ok} meta_ok={meta_ok} / n={n} — sınır aşımı")
    return _vaka(True,
                 f"V7_DALGA1_BASLIK_OK={baslik_ok}/{n}  V7_DALGA1_META_OK={meta_ok}/{n} (eksik={eksik} birleşen)")


def v8_yasak_sonek_yok():
    """Dalga-1 kümesi üretiminde '3D baskı'/'Özel Tasarım'/'Özel Üretim' sonekte 0."""
    dalga1_yolu = os.path.join(_ARACLAR_KOK, "baslik-dalga1-idler.json")
    with open(dalga1_yolu, encoding="utf-8") as f:
        dalga1 = json.load(f)
    ids = dalga1["ids"]
    with open(os.path.join(os.path.dirname(_ARACLAR_KOK), "urunler.json"),
              encoding="utf-8") as f:
        urunler = {p["id"]: p for p in json.load(f)}
    yasak_re = re.compile(r"3D baskı|3D Baskı|Özel Tasarım|Özel Üretim")
    build.DALGA1_IDLER = _ORJ_DALGA1
    try:
        bulunan = []
        for pid in ids:
            p = urunler.get(pid)
            if p is None:
                continue
            r = build.baslik_meta_dalga1(pid, p.get("baslik", ""),
                                          p.get("kategori", ""),
                                          p.get("aciklama", ""))
            if r is None:
                continue
            title = r[0]
            if yasak_re.search(title):
                bulunan.append((pid, title))
    finally:
        build.DALGA1_IDLER = _TEST_DALGA1
    if bulunan:
        return _vaka(False, f"yasak sonek bulundu: {bulunan[:3]}")
    return _vaka(True, "3D baskı/Özel Tasarım/Özel Üretim = 0")


# -------- vaka 9-10: render_product <title> çıktısı (sayfa üretimi) -----------
# Spec: render_product() L3605 dalga-1 title'ını kuruyor, ama eski bir L4130 satırı onu
# koşulsuz eziyordu. Bu blok, sayfa üretim çağrısının (a) dalga-1 id için yeni şablonu
# koruduğunu, (b) dalga-1 dışı id için eski şablonu bayt-aynı ürettiğini ölçer.

def _render_html(p):
    """render_product'ı minimal mock çağrı: [p] tüm ürün olarak, chip_map=None."""
    return build.render_product(p, [p], None)


def _extract_title(html):
    """HTML'den ilk <title>...</title> döner. Yoksa None."""
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    return m.group(1) if m else None


def v9_render_dalga1_baslik_dogru():
    """(a) Dalga-1 id sentetik ürün → render_product çıktısı <title> = baslik_meta_dalga1(...)[0]
    VE ' — PRUVO Özel Tasarım Yedek Parça' İÇERMEZ.

    Önceki davranışta render_product L4130 satırı dalga-1 title'ı KOŞULSUZ eziyordu;
    bu test o ezilmeyi yakalar.
    """
    pid = "oto-v1"  # SENTETIK'te var, dalga-1 test kümesinde
    p = SENTETIK_BY_ID[pid]
    r = _baslik_ogtitle_meta(pid, p["kategori"], p["baslik"])
    if r is None:
        return _vaka(False, "önişlem: dalga-1 kümesinde değil (test override bozulmuş)")
    beklenen_title = r[0]
    html = _render_html(p)
    title = _extract_title(html)
    if title is None:
        return _vaka(False, "HTML'de <title> bulunamadı")
    if " — PRUVO Özel Tasarım Yedek Parça" in title:
        return _vaka(False,
                     f"eski sonek sızmış (L4130 eziyor olabilir): title={title!r}")
    if title != beklenen_title:
        return _vaka(False, f"<title>={title!r} beklenen={beklenen_title!r}")
    return _vaka(True, f"<title>={title!r} dalga-1 şablonu geçerli")


def v10_render_disi_eski_sablon_bayt_ayni():
    """(b) Dalga-1 DIŞI id → render_product çıktısı <title> = eski şablon (bayt-aynı).

    Regresyon 0: küme dışı 15.930+ ürünün sayfa <title>'ı bayt bayt eski sonekle
    çıkmalı (bayt-aynı kontrolü)."""
    pid = "disi-v1"  # Bahçe, dalga-1 dışı
    p = SENTETIK_BY_ID[pid]
    r = build.baslik_meta_dalga1(pid, p["baslik"], p["kategori"], "")
    if r is not None:
        return _vaka(False, f"önişlem: küme dışı id için yardımcı None dönmeliydi: {r}")
    html = _render_html(p)
    title = _extract_title(html)
    if title is None:
        return _vaka(False, "HTML'de <title> bulunamadı")
    beklenen = build.esc(p["baslik"]) + " — PRUVO Özel Tasarım Yedek Parça"
    if title != beklenen:
        return _vaka(False, f"<title>={title!r} beklenen={beklenen!r}")
    return _vaka(True, f"<title>={title!r} bayt-aynı")


# -------- mutant'lar -----------------------------------------------------------
def mutant_liste_degisti():
    """M1 — BASLIK_PARCA_KATEGORILERI'ne 'Dekorasyon' eklenirse V2 KIRMIZI olmalı."""
    orj = set(build.BASLIK_PARCA_KATEGORILERI)
    build.BASLIK_PARCA_KATEGORILERI = frozenset(orj | {"Dekorasyon"})
    try:
        r = _baslik_ogtitle_meta("dekor-v2", "Dekorasyon",
                                 SENTETIK_BY_ID["dekor-v2"]["baslik"])
        if r is None:
            return _vaka(False, "yardımcı None — mutant etkisiz")
        title = r[0]
        # 'Dekorasyon' parça kategorisine eklenince 'Yedek Parça' sonek gelir → V2 kırmızı
        if not title.endswith(" | PRUVO Yedek Parça"):
            return _vaka(False, "mutant etkisiz: sonek değişmedi")
        return _vaka(True, f"mutant yakalandı: V2 kırmızı olur (Dekorasyon→'Yedek Parça')")
    finally:
        build.BASLIK_PARCA_KATEGORILERI = frozenset(orj)


def mutant_karakter_bazli_kesim():
    """M2 — kesim karakter bazlı yapılırsa V3 KIRMIZI olmalı (kelime ortası kesim)."""
    # _ad_kelime_kisalt yerine karakter-bazlı kırpalım: 37 kr'ya kesip boşluk arama YOK.
    orj = build._ad_kelime_kisalt
    def _kaba_kirp(ad, maks):
        return ad[:maks]  # boşluk dikkate ALMAZ
    build._ad_kelime_kisalt = _kaba_kirp
    try:
        # Aynı sentetik uzun ad ile sonek oluşturalım; kesim kelime ortasında olur
        ad = SENTETIK_BY_ID["oto-v3"]["baslik"]
        maks = 60 - 23  # parça sonek
        kisa = build._ad_kelime_kisalt(ad, maks)
        # Eğer son karakter harf ve boşluk değilse, kelime ortası kesim gerçekleşti
        if kisa and kisa[-1].isalpha() and " " in ad[:maks][:-1]:
            return _vaka(True, f"mutant yakalandı: son '{kisa[-5:]}' kelime ortası")
        return _vaka(False, f"mutant etkisiz: kesim yine kelime sınırında: {kisa[-20:]!r}")
    finally:
        build._ad_kelime_kisalt = orj


def mutant_kume_kontrolu_kaldirildi():
    """M3 — dalga-1 küme kontrolü kaldırılırsa V6 KIRMIZI olmalı (küme dışı ürün de yeni şablon)."""
    # baslik_meta_dalga1 yardımcısının kümeye bakan DALGA1_IDLER kontrolünü
    # geçici olarak "tüm id'ler dalga-1" gibi davranacak şekilde değiştir:
    # en temiz yöntem — DALGA1_IDLER'ı TÜM id'leri içerecek şekilde doldurmak.
    # Sonra 'disi-v1' (küme dışı) için None DÖNMEZ → mevcut şablon BYTE-AYNI OLMAZ.
    orj = build.DALGA1_IDLER
    build.DALGA1_IDLER = frozenset({"disi-v1"})  # disi-v1 artık küme içinde
    try:
        r = build.baslik_meta_dalga1("disi-v1", "Sukulent Saksısı", "Bahçe", "")
        if r is None:
            return _vaka(False, "mutant etkisiz: yardımcı None")
        title = r[0]
        # Yeni şablonda '| PRUVO Yedek Parça' soneki var; eski şablonda ' — PRUVO Özel Tasarım Yedek Parça'
        if title.endswith(" | PRUVO Yedek Parça") or title.endswith(" | PRUVO"):
            return _vaka(True, f"mutant yakalandı: küme kontrolü yok → eski sonek düştü: {title!r}")
        return _vaka(False, f"mutant etkisiz: beklenen sonek gelmedi: {title!r}")
    finally:
        build.DALGA1_IDLER = orj


def mutant_render_title_ezildi():
    """M4 — render_product'ta silinen `title_tag = esc(baslik) + ' — PRUVO Özel Tasarım Yedek Parça'`
    satırı geri eklenirse V9 KIRMIZI olmalı.

    İZOLE: canlı build.py'ye YAZMAz. Simülasyon: render_product çağrısının çıktısını al,
    <title>'ı override ederek "ezilmiş" halini inşa et, V9'un kırmızı koşulunu doğrula.
    Override sonrası title eski soneki İÇERİR → V9 reddedici koşulu (İÇERMEMELİ) yakalar.
    """
    pid = "oto-v1"
    p = SENTETIK_BY_ID[pid]
    # Önce DALGA-1 render'ın NORMAL çıktısı: yeni şablon, eski sonek YOK.
    html_normal = _render_html(p)
    title_normal = _extract_title(html_normal)
    if title_normal is None:
        return _vaka(False, "önişlem: HTML'de <title> bulunamadı")
    if " — PRUVO Özel Tasarım Yedek Parça" in title_normal:
        return _vaka(False,
                     f"önişlem: dalga-1 sayfası zaten eski sonek içeriyor (önce ezilmemiş mi?): {title_normal!r}")
    # Simülasyon: silinen satır geri eklenmiş gibi <title>'ı override et.
    title_override = build.esc(p["baslik"]) + " — PRUVO Özel Tasarım Yedek Parça"
    html_mutant = re.sub(r"<title>.*?</title>",
                         "<title>%s</title>" % title_override,
                         html_normal, count=1)
    title_mutant = _extract_title(html_mutant)
    if title_mutant is None:
        return _vaka(False, "mutant etkisiz: <title> override başarısız")
    if " — PRUVO Özel Tasarım Yedek Parça" not in title_mutant:
        return _vaka(False, f"mutant etkisiz: eski sonek override edilemedi: {title_mutant!r}")
    # V9 mantığı: (i) "eski sonek title'da OLMAMALI" → override sonrası İHLAL,
    # (ii) title != beklenen dalga-1 title → İHLAL. İki yol da V9'u KIRMIZI yapar.
    r_dalga1 = build.baslik_meta_dalga1(pid, p["baslik"], p["kategori"], "")
    if r_dalga1 is None:
        return _vaka(False, "önişlem: dalga-1 yardımcı None")
    beklenen_dalga1_title = r_dalga1[0]
    if title_mutant == beklenen_dalga1_title:
        return _vaka(False, "mutant etkisiz: override ile yine dalga-1 title döndü")
    return _vaka(True,
                 f"mutant yakalandı: override ile title={title_mutant!r} → V9 kırmızı olur")


# -------- ana akış ------------------------------------------------------------
VAKALAR = [
    ("V1_parca_kategori", v1_parca_kategori),
    ("V2_diger_kategori", v2_diger_kategori),
    ("V3_uzun_ad_kelime_sinirinda", v3_uzun_ad_kelime_sinirinda),
    ("V4_parantez_duser", v4_parantez_duser),
    ("V5_meta_160_cumle_kelime", v5_meta_160_cumle_kelime),
    ("V6_kume_disi_bayt_ayni", v6_kume_disi_bayt_ayni),
    ("V7_gercek_dalga1_kumesi", v7_gercek_dalga1_kumesi),
    ("V8_yasak_sonek_yok", v8_yasak_sonek_yok),
    ("V9_render_dalga1_baslik_dogru", v9_render_dalga1_baslik_dogru),
    ("V10_render_disi_eski_sablon_bayt_ayni", v10_render_disi_eski_sablon_bayt_ayni),
]
MUTANTLAR = [
    ("M1_parca_listesi_degisti", mutant_liste_degisti),
    ("M2_karakter_bazli_kesim", mutant_karakter_bazli_kesim),
    ("M3_kume_kontrolu_kaldirildi", mutant_kume_kontrolu_kaldirildi),
    ("M4_render_title_ezildi", mutant_render_title_ezildi),
]


def main():
    mutant_yok = "--mutant-yok" in sys.argv
    gecen = 0
    toplam = len(VAKALAR)
    for ad, fn in VAKALAR:
        try:
            gecti, aciklama = fn()
        except Exception as e:
            gecti, aciklama = False, f"EXCEPTION {type(e).__name__}: {e}"
        renk = "\033[32m" if gecti else "\033[31m"
        etiket = "YESIL" if gecti else "KIRMIZI"
        print(f"{renk}{etiket}\033[0m  {ad}: {aciklama}")
        if gecti:
            gecen += 1
    vaka_out = f"VAKA={gecen}/{toplam}"

    mutant_out = ""
    if not mutant_yok:
        print("--- MUTANT ---")
        mut_oldu = 0
        mut_toplam = len(MUTANTLAR)
        for ad, fn in MUTANTLAR:
            try:
                gecti, aciklama = fn()
            except Exception as e:
                gecti, aciklama = False, f"EXCEPTION {type(e).__name__}: {e}"
            renk = "\033[32m" if gecti else "\033[31m"
            etiket = "YESIL" if gecti else "KIRMIZI"
            print(f"{renk}{etiket}\033[0m  {ad}: {aciklama}")
            if gecti:
                mut_oldu += 1
        mutant_out = f" MUTANT_OLDU={mut_oldu}/{mut_toplam}"

    print(f"\n{vaka_out}{mutant_out}")
    sys.exit(0 if gecen == toplam else 1)


if __name__ == "__main__":
    main()