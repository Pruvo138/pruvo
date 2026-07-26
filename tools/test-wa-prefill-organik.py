#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kabul testi — ORGANİK ürün-sayfası WhatsApp butonu (help-cta-btn) prefill'i.

Sorun: organik "Bizimle İletişime Geçin" (help-cta-btn) butonunun wa.me ?text=
prefill'i BAĞLAM-KÖRdü (ürün adı/URL yok) -> Ege hangi ürün olduğunu bilemiyor,
lead düşüyor. Bu test, organik butonun prefill'inde ürün ADI + canonical URL'in
DOĞRU URL-kodlanmış (Türkçe karakter dahil) biçimde bulunduğunu kanıtlar.

REF/reklam-atıf butonu (orderAlt "WhatsApp'tan Sor") FARKLI ve zaten doğru —
bu test onun BOZULMADIĞINI da (ad+URL hâlâ var) regresyon olarak doğrular.

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


def _wa_text(href):
    """wa.me href'inden ?text= parametresini alıp URL-decode eder.
    Önce HTML-unescape (attribute bağlamı), sonra percent-decode."""
    href = _html.unescape(href)
    parts = href.split("?text=", 1)
    if len(parts) != 2:
        return None
    return unquote(parts[1])


def main():
    html_doc = build.render_product(URUN, [URUN])
    url = build.product_url(URUN["id"])
    baslik = URUN["baslik"]
    fails = []

    # --- ORGANİK buton: class="help-cta-btn"
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
        # (a) ürün başlığı içermeli
        if baslik not in organik_text:
            fails.append("organik prefill ürün BAŞLIĞINI içermiyor: %r" % baslik)
        # (b) canonical URL içermeli
        if url not in organik_text:
            fails.append("organik prefill canonical URL'i içermiyor: %r" % url)

    # Doğru numara (WHATSAPP sabiti), arama numarası (4005) ASLA wa.me'de olmamalı.
    if ("wa.me/" + build.WHATSAPP) not in organik_href:
        fails.append("organik href doğru WhatsApp numarasını kullanmıyor")
    if "4005" in organik_href:
        fails.append("organik href'te arama numarası (4005) var — yasak")

    # Türkçe karakterler DOĞRU kodlanmış olmalı: ham (kodlanmamış) ç/ğ/ı vb. URL'de
    # görünmemeli (double-encode ya da eksik-encode sessiz-hatasını yakalar).
    for ham in u"çğıöşü ":
        if ham in organik_href:
            fails.append("organik href'te HAM kodlanmamış karakter var: %r" % ham)
            break
    # Decode edilen metin tekrar tam olmalı (double-encode olsaydı %C3 gibi kalıntı olurdu).
    if organik_text and "%" in organik_text:
        fails.append("decode sonrası metinde '%' kalıntısı var — double-encode şüphesi")

    # --- REGRESYON: REF/atıf butonu (orderAlt) BOZULMAMALI — ad+URL hâlâ olmalı.
    mo = re.search(r'id="orderAlt"[^>]*\shref="(https://wa\.me/[^"]+)"', html_doc)
    if not mo:
        fails.append("orderAlt (REF butonu) wa.me href bulunamadı — regresyon")
    else:
        ref_text = _wa_text(mo.group(1))
        print("REF (orderAlt) decoded text=:")
        print("   ", repr(ref_text))
        if ref_text is None or baslik not in ref_text or url not in ref_text:
            fails.append("orderAlt (REF) prefill ad+URL bağlamını KAYBETTİ — regresyon")

    if fails:
        print("\nFAIL (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("\nPASS: organik prefill ürün adı + canonical URL içeriyor; REF butonu sağlam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
