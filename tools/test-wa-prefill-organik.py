#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kabul testi — ürün-sayfası BAĞLAM-KÖR WhatsApp prefill'leri (organik + malzeme notu).

Sorun: bu iki buton wa.me ?text= prefill'inde ürün adı/URL taşımıyordu -> Ege hangi ürün
sayfasından gelindiğini bilemiyor, lead düşüyor.

⚠️ NİYET EKSENİ (yalnız ad+URL YETMEZ):
  * help-cta-btn'in KENDİ metni "Aradığınız parçayı bulamadınız mı? ... üretelim!" ->
    butona basan müşteri SAYFADAKİ ürünü İSTEMİYOR, bulamadığı BAŞKA parçayı arıyor.
    Prefill "bu ürünü istiyorum" derse Ege yanlış niyetle o ürün için fiyat/malzeme
    akışı başlatır — bağlamsız olmasından BETER. Bu test bağlamın VAR olduğunu VE
    yanlış niyetin OLMADIĞINI BİRLİKTE assert eder.
  * malzeme-not linkinin niyeti AYRI (mühendislik malzemesi / özel üretim sorusu) ->
    o niyet KORUNMALI, help-cta'nın "bulamadım" niyetiyle karıştırılmamalı.

REF/reklam-atıf butonu (orderAlt "WhatsApp'tan Sor") FARKLI ve zaten doğru — bu test
onun BOZULMADIĞINI da (ad+URL hâlâ var) regresyon olarak doğrular.

Çalıştır:  python3 tools/test-wa-prefill-organik.py
Başarı = çıkış 0 + "PASS". Herhangi bir assert kırmızı = çıkış 1 + "FAIL".
"""
import os
import re
import sys
import html as _html
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

# Türkçe karakterlerin TAMAMINI (ç ğ ı ö ş ü İ) + boşluk + em-dash içeren örnek ürün.
URUN = {
    "id": "test-turkce-baglanti-parcasi",
    "kategori": "Otomobil",
    "marka": ["Ford"],
    "baslik": u"Çğıöşü Bağlantı Parçası — Ön Döşeme İç",
    "aciklama": u"Test açıklaması.\nYaklaşık dış ölçüler: 10 × 20 × 30 mm",
    "fiyat": "850 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/test-1.jpg"],
}

# help-cta prefill'inde BULUNMAMASI gereken "bu ürünü istiyorum" niyet kalıpları.
# (Buton "aradığını bulamayan" müşteri içindir — sayfadaki ürünü talep ETMEZ.)
YANLIS_NIYET = [
    u"bu ürünü istiyorum",
    u"bu parça hakkında bilgi almak istiyorum",
    u"bu ürün hakkında bilgi almak istiyorum",
    u"şu ürünle ilgileniyorum",
    u"bu ürünle ilgileniyorum",
]


def _wa_text(href):
    """wa.me href'inden ?text= parametresini alıp URL-decode eder.
    Önce HTML-unescape (attribute bağlamı), sonra percent-decode."""
    href = _html.unescape(href)
    parts = href.split("?text=", 1)
    if len(parts) != 2:
        return None
    return unquote(parts[1])


def _kodlama_kontrol(ad, href, metin, fails):
    """Ortak kodlama/numara nöbetleri (her wa.me linki için aynı sözleşme)."""
    if ("wa.me/" + build.WHATSAPP) not in href:
        fails.append("%s: doğru WhatsApp numarasını kullanmıyor" % ad)
    if "4005" in href:
        fails.append("%s: arama numarası (4005) var — yasak" % ad)
    # Ham (kodlanmamış) Türkçe karakter / boşluk URL'de OLMAMALI.
    for ham in u"çğıöşü ":
        if ham in href:
            fails.append("%s: HAM kodlanmamış karakter var: %r" % (ad, ham))
            break
    # Decode sonrası '%' kalıntısı = double-encode şüphesi.
    if metin and "%" in metin:
        fails.append("%s: decode sonrası '%%' kalıntısı — double-encode şüphesi" % ad)


def main():
    html_doc = build.render_product(URUN, [URUN])
    url = build.product_url(URUN["id"])
    baslik = URUN["baslik"]
    fails = []

    # ------------------------------------------------ ORGANİK buton (help-cta-btn)
    m = re.search(r'class="help-cta-btn"[^>]*\shref="(https://wa\.me/[^"]+)"', html_doc)
    if not m:
        print("FAIL: help-cta-btn wa.me href bulunamadı (buton kayıp mı?)")
        return 1
    organik_href = m.group(1)
    organik_text = _wa_text(organik_href)
    print("ORGANİK (help-cta-btn) decoded text=:")
    print("   ", repr(organik_text))

    if organik_text is None:
        fails.append("organik href'te ?text= yok")
    else:
        # (a) BAĞLAM: ürün başlığı + canonical URL
        if baslik not in organik_text:
            fails.append("organik prefill ürün BAŞLIĞINI içermiyor: %r" % baslik)
        if url not in organik_text:
            fails.append("organik prefill canonical URL'i içermiyor: %r" % url)
        # (b) NİYET: "bu ürünü istiyorum" DEMEMELİ (butonun anlamı bunun TERSİ)
        dusuk = organik_text.lower()
        for kotu in YANLIS_NIYET:
            if kotu.lower() in dusuk:
                fails.append(
                    "organik prefill YANLIŞ NİYET taşıyor (%r) — buton 'aradığını "
                    "bulamayan' müşteri için, sayfadaki ürünü TALEP ETMEZ" % kotu)
        # (c) NİYET: "bulamadım/üretebilir misiniz" niyetini TAŞIMALI
        if not (u"bulamad" in dusuk and (u"üretebilir" in dusuk or u"üretelim" in dusuk)):
            fails.append("organik prefill 'aradığımı bulamadım, üretebilir misiniz?' "
                         "niyetini taşımıyor")
    _kodlama_kontrol("organik", organik_href, organik_text, fails)

    # ------------------------------------------------ MALZEME NOTU (malzeme-not)
    mm = re.search(r'class="malzeme-not"(?:.(?!</p>))*?href="(https://wa\.me/[^"]+)"',
                   html_doc, re.S)
    if not mm:
        fails.append("malzeme-not wa.me href bulunamadı")
    else:
        malz_href = mm.group(1)
        malz_text = _wa_text(malz_href)
        print("MALZEME NOTU (malzeme-not) decoded text=:")
        print("   ", repr(malz_text))
        if malz_text is None:
            fails.append("malzeme-not href'te ?text= yok")
        else:
            # BAĞLAM eklenmiş olmalı
            if baslik not in malz_text:
                fails.append("malzeme-not prefill ürün BAŞLIĞINI içermiyor")
            if url not in malz_text:
                fails.append("malzeme-not prefill canonical URL'i içermiyor")
            # KENDİ niyeti (malzeme/özel üretim) KORUNMALI
            md = malz_text.lower()
            if not (u"malzeme" in md and u"özel üretim" in md):
                fails.append("malzeme-not KENDİ niyetini (mühendislik malzemesi / "
                             "özel üretim sorusu) KAYBETTİ")
            # help-cta'nın niyeti buraya SIZMAMALI
            if u"bulamad" in md:
                fails.append("malzeme-not'a help-cta niyeti ('bulamadım') SIZDI")
        _kodlama_kontrol("malzeme-not", malz_href, malz_text, fails)

    # ------------------------------------------------ REGRESYON: REF butonu (orderAlt)
    mo = re.search(r'id="orderAlt"[^>]*\shref="(https://wa\.me/[^"]+)"', html_doc)
    if not mo:
        fails.append("orderAlt (REF butonu) wa.me href bulunamadı — regresyon")
    else:
        ref_text = _wa_text(mo.group(1))
        print("REF (orderAlt) decoded text=:")
        print("   ", repr(ref_text))
        if ref_text is None or baslik not in ref_text or url not in ref_text:
            fails.append("orderAlt (REF) prefill ad+URL bağlamını KAYBETTİ — regresyon")
        # REF butonu ÜRÜN TALEBİ butonudur: onun "ilgileniyorum" niyeti KALMALI.
        if ref_text and u"ilgileniyorum" not in ref_text.lower():
            fails.append("orderAlt (REF) 'ilgileniyorum' niyetini kaybetti — regresyon")

    if fails:
        print("\nFAIL (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("\nPASS: organik + malzeme-not prefill'leri sayfa bağlamı taşıyor, niyetleri "
          "DOĞRU ve AYRI; REF butonu sağlam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
