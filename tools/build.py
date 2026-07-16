#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUVO statik sayfa üreticisi.

urunler.json'u okur ve her ürün için Google'da çıkabilen, tam SEO'lu
kendi adresine sahip statik bir sayfa üretir:  /urun/<id>/index.html

Ayrıca sitemap.xml, robots.txt, .nojekyll ve Google Merchant Center ürün
feed'ini (merchant-feed.xml — sadece sabit fiyatlı ürünler) üretir.

Ürün ekleme akışı (LOKALDE ÇALIŞTIRMA — CI üretir):
  1) urunler.json'un başına yeni ürünü ekle
  2) git add urunler.json && commit && push
  3) GitHub Actions (deploy.yml) bu betiği sunucuda çalıştırıp Pages'e yayınlar.
     Üretilenler (urun/, sitemap.xml, robots.txt, merchant-feed.xml, .nojekyll)
     gitignore'dadır; git'e GİRMEZ.

Harici bağımlılık YOK (saf Python 3 standart kütüphane).
"""

import os
import re
import json
import shutil
import html
import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sayfalar import (SELLER, PAY_BAND_HTML, FOOT_NAV_HTML,
                      CONTENT_CSS, CONTENT_PAGES, SITEMAP_SLUGS)

# ------------------------------------------------------------------ ayarlar
SITE = "https://pruvo3d.com"
WHATSAPP = "905451386526"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "urunler.json")
URUN_DIR = os.path.join(ROOT, "urun")
# Parametrik ("Ölçüye Özel" sarı seri) konfigüratör şemaları — jenerator/urunler/<id>.json.
# Şeması olan parametrik ürünün sayfasına konfigüratör UI basılır; olmayana dokunulmaz.
JEN_URUN_DIR = os.path.join(ROOT, "jenerator", "urunler")
CATEGORIES = ["Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev", "Ofis", "Elektronik", "Kamera", "Bahçe", "Dekorasyon", "Oyun/Hobi"]
# Malzeme/renk/boy seçicisi bu kategorilerde gösterilir (Dekorasyon, Oyun/Hobi HARİÇ).
# secenekler.js'deki FONKSIYONEL_KATEGORILER ile BİRLİKTE güncelle (tek karar iki yerde).
FONKSIYONEL_KATEGORILER = ["Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin", "Bisiklet", "Bahçe", "Ofis", "Kamera"]

TODAY = datetime.date.today().isoformat()
PRICE_VALID = (datetime.date.today().replace(month=12, day=31)
               + datetime.timedelta(days=365)).isoformat()

# ------------------------------------------------------------------ Google Merchant feed
# /merchant-feed.xml — Google Merchant Center'a gonderilecek urun feed'i (ucretsiz listelemeler).
# SADECE parametrik OLMAYAN, SABIT sayisal fiyatli, gorseli olan urunler girer.
# Parametrik "sari seri" (net fiyati yok -> "Olcuye ozel") feed'e GIRMEZ (Merchant reddeder).
MERCHANT_FEED = "merchant-feed.xml"
FEED_BRAND = "PRUVO"
# Urunler talep uzerine ozel uretilir ama sabit fiyatli kalem her zaman uretilebilir -> in_stock.
# (Uretim-sonrasi teslim vurgulanmak istenirse "backorder" yapilabilir.)
FEED_AVAILABILITY = "in_stock"
# Kendi kategorimiz -> Google urun taksonomisi (kaba, gecerli ust dugumler; eslesmeyen atlanir).
GOOGLE_PRODUCT_CATEGORY = {
    "Otomobil": "Vehicles & Parts > Vehicle Parts & Accessories",
    "Motosiklet": "Vehicles & Parts > Vehicle Parts & Accessories",
    "Marin": "Vehicles & Parts > Vehicle Parts & Accessories",
    "Bisiklet": "Sporting Goods > Cycling",
    "Tamirat": "Hardware > Tools",
    "Ev": "Home & Garden",
    "Ofis": "Office Supplies",
    "Elektronik": "Electronics",
    "Kamera": "Cameras & Optics",
    "Bahçe": "Home & Garden > Lawn & Garden",
    "Dekorasyon": "Home & Garden > Decor",
    "Oyun/Hobi": "Toys & Games",
}
# Marka kurali: "3D baski"/"3D printed" -> "ozel tasarim uretim". SADECE uretim iddiasi olan
# ifadeler; kasa kodu (Passat 3B), "3D perspektif", "3D yazici" gibi masum kullanimlara DOKUNMAZ.
_MARKA_SUB = [
    (re.compile(r"3\s*[d]\s*[-\s]?bask[ıi](?:l[ıi])?", re.I), "özel tasarım üretim"),
    (re.compile(r"3\s*boyutlu\s+bask[ıi](?:l[ıi])?", re.I), "özel tasarım üretim"),
    (re.compile(r"3\s*[d]\s*print(?:ed|ing)?", re.I), "özel tasarım üretim"),
]

# Kaynak model CC lisanslıysa (MakerWorld / Thingiverse / Printables) atıf ZORUNLU.
# urunler.json'da ürüne "lisans": {"tasarimci": "Ad", "tur": "CC BY 4.0"} eklenir;
# "url" verilmezse tür kodundan aşağıdaki tablodan otomatik CC linki türetilir.
# (******** royalty-free lisanslı ürünlerde CC atıfı yoktur; "lisans" alanı eklenmez.)
CC_URLS = {
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-ND 4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
    "CC BY-NC 4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "CC BY-NC-SA 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "CC BY-NC-ND 4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
}

FAVICON = ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 100 100'><rect width='100' height='100' rx='20' "
           "fill='%2312294d'/><text x='50' y='55' font-family='Arial,"
           "Helvetica,sans-serif' font-size='72' font-weight='800' "
           "fill='%23ffffff' text-anchor='middle' dominant-baseline='central'"
           ">P</text></svg>")

WA_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12.04 2C6.58 '
           '2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 '
           '9.9 0 0 0 4.79 1.22h.01c5.46 0 9.9-4.45 9.9-9.91 0-2.65-1.03-5.14-'
           '2.9-7.01A9.82 9.82 0 0 0 12.04 2zm5.8 14.13c-.24.68-1.42 1.31-1.96 '
           '1.35-.5.05-.98.24-3.3-.69-2.77-1.09-4.56-3.9-4.7-4.08-.14-.19-1.12-'
           '1.49-1.12-2.84 0-1.35.71-2.02.96-2.29.24-.27.53-.34.71-.34.18 0 .35 '
           '0 .51.01.16.01.38-.06.6.46.24.56.79 1.94.86 2.08.07.14.12.31.02.5-'
           '.09.19-.14.31-.28.48-.14.17-.29.37-.42.5-.14.14-.28.29-.12.57.16.28'
           '.72 1.18 1.54 1.91 1.06.94 1.95 1.24 2.23 1.38.28.14.44.12.6-.07.16-'
           '.19.69-.8.87-1.08.18-.28.36-.23.6-.14.24.09 1.55.73 1.81.86.27.14.45'
           '.21.51.32.06.11.06.64-.18 1.32z"/></svg>')

# Malzeme/renk satırları — klasik opsiyon bloğu ve parametrik konfigüratör AYNI
# bileşeni kullanır (tek kaynak; secenekler.js FILAMENT_FARK/RENK ile uyumlu).
MALZEME_RENK_HTML = """
      <div class="opsiyon-row">
        <label for="malzemeSec">Malzeme</label>
        <select id="malzemeSec">
          <option value="PLA">PLA (standart)</option>
          <option value="PETG">PETG (+%30)</option>
          <option value="ASA">ASA (+%60)</option>
          <option value="TPU">TPU (+%55)</option>
        </select>
      </div>
      <p class="malzeme-not">Karbon fiber veya diğer mühendislik malzemeleriyle üretim için <a href="https://wa.me/905451386526?text=Merhaba%2C%20m%C3%BChendislik%20malzemesiyle%20%C3%B6zel%20%C3%BCretim%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." target="_blank" rel="noopener">WhatsApp'tan bize yazın</a>.</p>
      <div class="opsiyon-row">
        <label for="renkSec">Renk</label>
        <select id="renkSec">
          <option value="Siyah">Siyah</option>
          <option value="Beyaz">Beyaz</option>
          <option value="Gri">Gri</option>
          <option value="Diğer">Diğer (+%15)</option>
        </select>
        <input type="text" id="renkOzel" placeholder="istediğiniz rengi yazın" style="display:none">
      </div>"""


def konf_sema(pid):
    """Parametrik ürünün konfigüratör şeması (jenerator/urunler/<id>.json); yoksa None."""
    yol = os.path.join(JEN_URUN_DIR, "%s.json" % pid)
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


CART_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 '
             '7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 '
             '0-.25-.11-.25-.25l.03-.12L8.1 15h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1 1 0 0 0 20 6H5.21l-.94-2H1zm16 '
             '16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/></svg>')

# ------------------------------------------------------------------ ortak CSS
PAGE_CSS = """
  :root{
    --navy:#12294d;--navy-2:#1c3a6b;--navy-dark:#0d1e3a;
    --gray-bg:#eef1f5;--gray-card:#fff;--gray-line:#d7dde6;
    --gray-text:#5b6675;--red:#d1332e;--red-dark:#b12723;
    --radius:10px;--shadow:0 2px 10px rgba(18,41,77,.08);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--gray-bg);color:var(--navy);line-height:1.5}
  a{color:inherit}
  header{background:var(--navy);color:#fff;padding:20px;box-shadow:var(--shadow)}
  .header-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;
    justify-content:space-between;gap:16px;flex-wrap:wrap}
  .brand-link{text-decoration:none;color:#fff;display:block}
  .brand{font-size:34px;font-weight:800;letter-spacing:3px;line-height:1}
  .brand-sub{font-size:12px;letter-spacing:2px;text-transform:uppercase;
    color:#b9c6dc;margin-top:5px}
  .top-back{color:#cdd8ea;text-decoration:none;font-weight:600;font-size:14px;
    white-space:nowrap}
  .top-back:hover{color:#fff}

  .help-cta{background:var(--gray-card);border-bottom:1px solid var(--gray-line);box-shadow:var(--shadow);
    position:sticky;top:0;z-index:100}
  .help-cta-inner{max-width:1100px;margin:0 auto;padding:16px 20px;display:flex;align-items:center;
    justify-content:center;flex-wrap:wrap;gap:12px 18px;text-align:center}
  .help-cta-text{font-size:15.5px;color:var(--navy)}
  .help-cta-text strong{font-weight:800}
  .info-strip{background:#fff;border-bottom:1px solid var(--gray-line)}
  .info-strip-inner{max-width:1100px;margin:0 auto;padding:12px 20px;text-align:center}
  .info-strip p{font-size:14px;color:var(--gray-text);line-height:1.5;margin:0}
  .info-strip strong{color:var(--navy);font-weight:700}
  .help-cta-btn{background:#25D366;color:#fff;border:none;border-radius:24px;padding:11px 22px;font-size:14.5px;
    font-weight:700;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:8px;
    white-space:nowrap;box-shadow:0 3px 10px rgba(37,211,102,.35);transition:.15s}
  .help-cta-btn:hover{background:#1ebe5a}
  .help-cta-btn svg{width:19px;height:19px;fill:#fff}

  main{max-width:1100px;margin:0 auto;padding:28px 20px 50px}
  .crumbs{font-size:13px;color:var(--gray-text);margin-bottom:18px}
  .crumbs a{color:var(--navy-2);text-decoration:none}
  .crumbs a:hover{text-decoration:underline}
  .crumbs span{color:var(--gray-line);margin:0 6px}

  .detail{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:start}
  .gallery{position:sticky;top:78px}
  .main-img{width:100%;aspect-ratio:1/1;object-fit:contain;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:var(--radius);display:block}
  .thumbs{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
  .thumb{width:74px;height:74px;object-fit:cover;border-radius:8px;
    border:2px solid transparent;cursor:pointer;background:var(--gray-card)}
  .thumb:hover{border-color:var(--gray-line)}
  .thumb.active{border-color:var(--navy)}

  .cat{display:inline-block;background:var(--navy);color:#fff;font-size:11px;
    font-weight:600;letter-spacing:.5px;text-transform:uppercase;padding:4px 11px;
    border-radius:20px}
  .ozel-badge{display:inline-block;background:#f7b500;color:#12294d;font-size:11px;
    font-weight:800;letter-spacing:.3px;padding:4px 11px;border-radius:20px;margin-left:8px}
  h1{font-size:27px;font-weight:800;margin:14px 0 10px;color:var(--navy);line-height:1.25}
  .brands{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:14px}
  .brand-chip{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:20px;padding:5px 12px;font-size:12.5px;font-weight:600;
    color:var(--navy);text-decoration:none}
  .brand-chip:hover{border-color:var(--navy-2)}
  .price{font-size:26px;font-weight:800;color:var(--navy);margin:4px 0 20px}
  .price.empty{font-size:15px;font-weight:600;color:var(--gray-text)}
  .opsiyonlar{margin:4px 0 20px;padding:14px 16px;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:var(--radius)}
  .opsiyon-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
  .opsiyon-row:last-of-type{margin-bottom:0}
  .opsiyon-row label{font-size:13px;font-weight:700;color:var(--navy);min-width:64px}
  .opsiyon-row select,.opsiyon-row input[type=text]{padding:8px 10px;border:1px solid var(--gray-line);
    border-radius:7px;font-size:14px;background:#fff;color:var(--navy)}
  .opsiyon-fiyat{font-size:19px;font-weight:800;color:var(--navy);margin-top:10px}
  .konf-baslik{font-size:14px;font-weight:800;color:var(--navy);margin-bottom:12px}
  .konf-row label{min-width:130px}
  .konf-sayi{width:110px;padding:8px 10px;border:1px solid var(--gray-line);
    border-radius:7px;font-size:14px;background:#fff;color:var(--navy)}
  .konf-birim{font-size:12.5px;color:var(--gray-text);font-weight:600}
  .konf-kaydirici-satir{margin:-4px 0 10px;padding-left:140px}
  .konf-kaydirici{width:100%;max-width:260px;accent-color:var(--navy-2)}
  .konf-row select,.konf-row input[type=text]{max-width:220px}
  .konf-hata{flex-basis:100%;font-size:12px;font-weight:600;color:var(--red);min-height:0}
  .konf-row .hatali{border-color:var(--red);background:#fff5f5;outline:1px solid var(--red)}
  .konf-hacim{font-size:12.5px;color:var(--gray-text);margin-top:4px}
  .cart-btn.kilitli{opacity:.45;cursor:not-allowed}
  .desc{font-size:15px;color:#39434f;line-height:1.7;margin-bottom:26px}
  .order-btn{background:var(--red);color:#fff;border:none;border-radius:9px;
    padding:15px 22px;font-size:16px;font-weight:700;cursor:pointer;
    text-decoration:none;display:inline-flex;align-items:center;justify-content:center;
    gap:9px;transition:.15s;max-width:320px;width:100%}
  .order-btn:hover{background:var(--red-dark)}
  .order-btn svg{width:19px;height:19px;fill:#fff}
  .cart-btn{background:var(--navy);color:#fff;border:none;border-radius:9px;
    padding:15px 22px;font-size:16px;font-weight:700;cursor:pointer;
    display:inline-flex;align-items:center;justify-content:center;gap:9px;
    transition:.15s;max-width:320px;width:100%}
  .cart-btn:hover{background:var(--navy-2)}
  .cart-btn svg{width:19px;height:19px;fill:#fff}
  .cart-btn.added{background:#e8f6ee;color:#178a44}
  .cart-btn.added svg{fill:#178a44}
  .order-wa{background:#25D366;color:#fff;border:none;border-radius:9px;
    padding:13px 22px;font-size:15px;font-weight:700;cursor:pointer;
    text-decoration:none;display:inline-flex;align-items:center;justify-content:center;
    gap:9px;transition:.15s;max-width:320px;width:100%;margin-top:11px}
  .order-wa:hover{background:#1ebe5a}
  .order-wa svg{width:19px;height:19px;fill:#fff}
  .malzeme-not{font-size:12.5px;color:var(--gray-text);line-height:1.5;margin:2px 0 2px}
  .malzeme-not a{color:#178a44;font-weight:600;text-decoration:underline}
  .cart-fab{position:fixed;right:18px;bottom:18px;z-index:60;background:#25a35a;color:#fff;
    border-radius:30px;padding:12px 20px;font-size:15px;font-weight:700;text-decoration:none;
    box-shadow:0 6px 18px rgba(0,0,0,.22);align-items:center;gap:8px;display:none}
  .cart-fab:hover{background:#1ebe5a}
  .cart-fab svg{width:19px;height:19px;fill:#fff}
  .note{font-size:12.5px;color:var(--gray-text);margin-top:12px}

  .related{max-width:1100px;margin:0 auto;padding:0 20px 60px}
  .related h2{font-size:19px;font-weight:700;margin-bottom:16px}
  .rel-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
  .rel-card{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:var(--radius);overflow:hidden;text-decoration:none;color:var(--navy);
    display:flex;flex-direction:column;box-shadow:var(--shadow);transition:transform .15s,box-shadow .15s}
  .rel-card:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(18,41,77,.14)}
  .rel-img{width:100%;aspect-ratio:4/3;object-fit:cover;background:#dbe2ec;display:block}
  .rel-body{padding:12px 13px 14px}
  .rel-title{font-size:14px;font-weight:700;line-height:1.35;margin-bottom:6px}
  .rel-price{font-size:14px;font-weight:800;color:var(--navy)}

  footer{background:var(--navy-dark);color:#aeb9cd;text-align:center;padding:22px 20px;
    font-size:13.5px;letter-spacing:.5px}
  .foot-nav{margin-top:8px}
  .foot-nav a{color:#c7d2e4;text-decoration:none;margin:0 8px}
  .foot-nav a:hover{color:#fff;text-decoration:underline}
  .attribution{margin-top:12px;font-size:11px;letter-spacing:.3px;color:#7d8aa3}
  .attribution a{color:#93a1bd;text-decoration:underline}

  @media (max-width:760px){
    .detail{grid-template-columns:1fr;gap:22px}
    .gallery{position:static}
    h1{font-size:22px}.price{font-size:22px}
    .order-btn,.cart-btn{max-width:none}
  }
"""
PAGE_CSS += CONTENT_CSS


# ------------------------------------------------------------------ yardımcılar
def esc(s):
    return html.escape(s or "", quote=True)


def meta_desc(p):
    """Ürün açıklamasından ~160 karakterlik temiz meta açıklama üret."""
    txt = re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip()
    if len(txt) > 158:
        txt = txt[:158].rsplit(" ", 1)[0] + "…"
    return txt


def price_number(fiyat):
    """'1250 TL' -> '1250' (rakam yoksa None)."""
    if not fiyat:
        return None
    digits = re.sub(r"[^0-9]", "", fiyat)
    return digits or None


def marka_temiz(txt):
    """Feed metni marka kurali: '3D baski/printed' -> 'ozel tasarim uretim' (hedefli)."""
    s = txt or ""
    for pat, rep in _MARKA_SUB:
        s = pat.sub(rep, s)
    return s


def feed_price(fiyat):
    """Feed icin net sayisal TL fiyati: '650 TL'->'650', '1.250 TL'->'1250',
    '350 TL (12 cm)'->'350'. Sayisal fiyat yoksa (parametrik/'olcuye ozel') None."""
    if not fiyat:
        return None
    m = re.search(r"(\d[\d.]*)\s*(?:tl|try|₺)", fiyat, re.I) or re.search(r"(\d[\d.]*)", fiyat)
    if not m:
        return None
    raw = m.group(1).replace(".", "")          # Turkce binlik ayraci ('1.250' -> '1250')
    return raw if raw.isdigit() and int(raw) > 0 else None


def images_of(p):
    imgs = p.get("gorseller") or []
    return [i for i in imgs if i]


def wa_href(p, url):
    msg = u"Merhaba, şu ürünle ilgileniyorum: " + (p.get("baslik") or "") + "\n" + url
    from urllib.parse import quote
    return "https://wa.me/" + WHATSAPP + "?text=" + quote(msg)


def product_url(pid):
    return SITE + "/urun/" + pid + "/"


def attribution_html(p):
    """CC lisanslı kaynaklar için tasarımcı + lisans atıfı (küçük, sayfa altı).
    Format: 'Design by <Ad>, licensed under <CC BY 4.0>.'  (isim linksiz,
    lisans türü creativecommons linkine bağlı)."""
    lis = p.get("lisans")
    if not lis:
        return ""
    tasarimci = (lis.get("tasarimci") or "").strip()
    tur = (lis.get("tur") or "").strip()
    url = (lis.get("url") or CC_URLS.get(tur) or "").strip()
    if not tur:
        return ""
    if url:
        lic = ('<a href="%s" target="_blank" rel="license noopener nofollow">%s</a>'
               % (esc(url), esc(tur)))
    else:
        lic = esc(tur)
    if not tasarimci:
        # Tasarimci hesabi silinmis/anonim olabilir; CC atifi lisans linkiyle yine verilir.
        return '<div class="attribution">Licensed under %s.</div>' % lic
    return ('<div class="attribution">Design by %s, licensed under %s.</div>'
            % (esc(tasarimci), lic))


# ------------------------------------------------------------------ ürün sayfası
def render_product(p, all_products):
    pid = p["id"]
    url = product_url(pid)
    baslik = p.get("baslik") or ""
    kategori = p.get("kategori") or ""
    fiyat = (p.get("fiyat") or "").strip()
    markalar = p.get("marka") or []
    imgs = images_of(p)
    cover = imgs[0] if imgs else (SITE + "/favicon.png")
    desc160 = meta_desc(p)
    pnum = price_number(fiyat)

    aciklama_html = esc(p.get("aciklama") or "").replace("\n", "<br>")

    # --- JSON-LD Product
    offer = {
        "@type": "Offer",
        "url": url,
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "priceCurrency": "TRY",
        "seller": {"@type": "Organization", "name": "PRUVO"},
    }
    if pnum:
        offer["price"] = pnum
        offer["priceValidUntil"] = PRICE_VALID

    product_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": baslik,
        "image": imgs or [cover],
        "description": re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip(),
        "sku": pid,
        "category": kategori,
        "offers": offer,
    }
    if markalar:
        product_ld["brand"] = [{"@type": "Brand", "name": b} for b in markalar]

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": kategori,
             "item": SITE + "/?kategori=" + kategori},
            {"@type": "ListItem", "position": 3, "name": baslik, "item": url},
        ],
    }

    def ld(obj):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    # --- galeri
    main_img = ('<img class="main-img" id="mainImg" src="%s" alt="%s" '
                'width="800" height="800">') % (esc(cover), esc(baslik))
    thumbs_html = ""
    if len(imgs) > 1:
        parts = []
        for i, src in enumerate(imgs):
            cls = "thumb active" if i == 0 else "thumb"
            parts.append(
                '<img class="%s" src="%s" alt="%s görsel %d" '
                'onclick="pv(this,\'%s\')" loading="lazy">'
                % (cls, esc(src), esc(baslik), i + 1, esc(src)))
        thumbs_html = '<div class="thumbs">' + "".join(parts) + "</div>"

    # --- marka çipleri (ana sayfada o markayı filtreler)
    brand_html = ""
    if markalar:
        chips = "".join(
            '<a class="brand-chip" href="/?marka=%s">%s</a>' % (esc(b), esc(b))
            for b in markalar)
        brand_html = '<div class="brands">' + chips + "</div>"

    # --- parametrik ("ölçüye özel") rozeti
    parametrik = bool(p.get("parametrik"))
    badge_html = '<span class="ozel-badge">Ölçüye Özel</span>' if parametrik else ''

    # --- fiyat metni (JS'siz/tarayıcı öncesi durum + fonksiyonel OLMAYAN ürünlerin tek gösterimi)
    if fiyat:
        price_text = fiyat
    elif parametrik:
        price_text = "Ölçüye özel fiyat — teklif için sipariş verin"
    else:
        price_text = "Fiyat için sipariş verin"

    # --- malzeme/renk/boy seçicisi (fonksiyonel kategoriler) / konfigüratör (parametrik+şemalı)
    fonksiyonel = kategori in FONKSIYONEL_KATEGORILER
    boy_secenekleri = p.get("boy_secenekleri") or []
    sema = konf_sema(pid) if parametrik else None
    if sema:
        # Konfigüratör: müşteri ölçü/parametre girer, hacim + fiyat canlı hesaplanır
        # (jenerator/hacim.js + jenerator/konfigurator.js). Kategoriden bağımsız —
        # sarı seride malzeme/renk seçimi de müşteride. tabanFiyatTL=null iken
        # fiyat "—" kalır (Okan taban fiyatları verene kadar altyapı hazır bekler).
        opsiyonlar_html = ("""
    <div class="opsiyonlar konf" id="opsiyonlar">
      <div class="konf-baslik">Ölçülerinizi girin</div>
      <div id="konfAlanlar"></div>
      {malzeme_renk}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">&mdash;</div>
      <div class="konf-hacim" id="konfHacim"></div>
    </div>
    """).format(malzeme_renk=MALZEME_RENK_HTML)
        price_html = ""
    elif fonksiyonel:
        boy_html = ""
        if boy_secenekleri:
            boy_opts = "".join(
                '<option value="%s">%s%s</option>' % (
                    esc(b.get("etiket") or ""), esc(b.get("etiket") or ""),
                    (" (+%d TL)" % b["fark_tl"]) if b.get("fark_tl") else "")
                for b in boy_secenekleri)
            boy_html = ('<div class="opsiyon-row"><label for="boySec">Boy</label>'
                        '<select id="boySec">%s</select></div>' % boy_opts)
        opsiyonlar_html = ("""
    <div class="opsiyonlar" id="opsiyonlar">
      {malzeme_renk}
      {boy}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>
    </div>
    """).format(malzeme_renk=MALZEME_RENK_HTML, boy=boy_html,
                fiyat_metni=esc(price_text))
        price_html = ""
    else:
        opsiyonlar_html = ""
        price_html = '<div class="price%s">%s</div>' % (
            "" if fiyat else " empty", esc(price_text))

    # --- ilgili ürünler (aynı kategori, kendisi hariç, en fazla 8)
    rel = [x for x in all_products
           if x.get("kategori") == kategori and x["id"] != pid][:8]
    rel_html = ""
    if rel:
        cards = []
        for r in rel:
            rimgs = images_of(r)
            rcov = rimgs[0] if rimgs else cover
            rfiyat = (r.get("fiyat") or "").strip()
            rprice = ('<div class="rel-price">%s</div>' % esc(rfiyat)) if rfiyat else ""
            cards.append(
                '<a class="rel-card" href="%s">'
                '<img class="rel-img" src="%s" alt="%s" loading="lazy" '
                'width="400" height="300">'
                '<div class="rel-body"><div class="rel-title">%s</div>%s</div></a>'
                % (product_url(r["id"]), esc(rcov), esc(r.get("baslik") or ""),
                   esc(r.get("baslik") or ""), rprice))
        rel_html = (
            '<section class="related"><h2>Diğer %s ürünleri</h2>'
            '<div class="rel-grid">%s</div></section>'
            % (esc(kategori), "".join(cards)))

    title_tag = esc(baslik) + " — PRUVO Özel Tasarım Yedek Parça"

    # --- JS'e (opsiyonlar bloğu + fiyat hesabı) aktarılacak ürün verisi
    urun_json = json.dumps(
        {"id": pid, "baslik": baslik, "kategori": kategori, "fiyat": fiyat,
         "parametrik": parametrik, "boy_secenekleri": boy_secenekleri},
        ensure_ascii=False, separators=(",", ":")).replace("</script>", "<\\/script>")

    # Konfigüratör şeması sayfaya inline gömülür (tek kaynak jenerator/urunler/<id>.json,
    # build her push'ta yeniden gömer); hacim fonksiyonları ise /jenerator/hacim.js'ten
    # AYNI DOSYA olarak yüklenir (kopya yasak — kabul testi #4).
    sema_json = "null"
    konf_scripts = ""
    if sema:
        sema_json = json.dumps(sema, ensure_ascii=False, separators=(",", ":")
                               ).replace("</script>", "<\\/script>")
        konf_scripts = ('<script src="/jenerator/hacim.js"></script>\n'
                        '<script src="/jenerator/konfigurator.js"></script>')

    doc = u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="product">
<meta property="og:site_name" content="PRUVO">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ogtitle}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{img}">
<script type="application/ld+json">{product_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<style>{css}</style>
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

<section class="help-cta">
  <div class="help-cta-inner">
    <span class="help-cta-text">Aradığınız parçayı bulamadınız mı? <strong>Bizimle iletişime geçin, üretelim!</strong></span>
    <a class="help-cta-btn" href="https://wa.me/905451386526?text=Merhaba%2C%20arad%C4%B1%C4%9F%C4%B1m%20bir%20yedek%20par%C3%A7a%20var.%20%C3%9Cretebilir%20misiniz%3F" target="_blank" rel="noopener">{icon} Bizimle İletişime Geçin</a>
  </div>
</section>

<section class="info-strip">
  <div class="info-strip-inner">
    <p><strong>Model numarasını</strong> biliyorsanız gönderin, <strong>araştıralım</strong>; ya da <strong>parçanın bir eşini</strong> (kırık olsa da) gönderin, <strong>endüstriyel tarayıcıyla modelleyelim</strong>.</p>
  </div>
</section>

<main>
  <nav class="crumbs" aria-label="breadcrumb">
    <a href="/">Ana Sayfa</a><span>&rsaquo;</span>
    <a href="/?kategori={katq}">{kategori}</a><span>&rsaquo;</span>
    {baslik}
  </nav>

  <div class="detail">
    <div class="gallery">
      {main_img}
      {thumbs}
    </div>
    <div class="info">
      <span class="cat">{kategori}</span>{badge}
      <h1>{h1}</h1>
      {brands}
      {price}
      {opsiyonlar}
      <p class="desc">{aciklama}</p>
      <button class="cart-btn" id="cartBtn" data-id="{pid}">{cart_icon}<span class="cart-label">Sepete Ekle</span></button>
      <a class="order-wa" id="orderAlt" href="{wa}" target="_blank" rel="noopener">{icon}WhatsApp'tan Sor</a>
      <div class="note">Sepete ekleyip birden çok ürünü tek WhatsApp mesajıyla sipariş edebilirsiniz. Ürünler talep üzerine özel üretilir.</div>
    </div>
  </div>
</main>

{related}

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi | Fethiye
  {foot_nav}
  {pay_band}
  {attribution}
</footer>

<a id="cartFab" class="cart-fab" href="/?sepet=1">{cart_icon}Sepetim (<span id="cartCount">0</span>)</a>

<script src="/secenekler.js"></script>
{konf_scripts}
<script>
function pv(el,src){{
  document.getElementById('mainImg').src=src;
  var t=document.querySelectorAll('.thumb');
  for(var i=0;i<t.length;i++){{t[i].className='thumb';}}
  el.className='thumb active';
}}
var URUN = {urun_json};
var URUN_SEMA = {sema_json};
/* Sepet: bu ürünü index.html ile ortak localStorage sepetine (secenekler.js: PRUVO_SECENEK) ekle/çıkar.
   Malzeme/renk/boy seçiliyse (opsiyonlar bloğu varsa) seçilen TAM konfigürasyon bileşik anahtarla
   toggle edilir; farklı bir konfigürasyonla eklenmiş başka bir satıra dokunulmaz. */
(function(){{
  var btn=document.getElementById("cartBtn"); if(!btn){{ return; }}
  var id=URUN.id;
  var label=btn.querySelector(".cart-label");
  var fab=document.getElementById("cartFab");
  var count=document.getElementById("cartCount");
  var orderAlt=document.getElementById("orderAlt");
  var malzemeSec=document.getElementById("malzemeSec");
  var renkSec=document.getElementById("renkSec");
  var renkOzel=document.getElementById("renkOzel");
  var boySec=document.getElementById("boySec");
  var fiyatEl=document.getElementById("opsiyonFiyat");

  function currentSatir(){{
    var s = PRUVO_SECENEK.bosSatir(id);
    if(malzemeSec){{ s.malzeme = malzemeSec.value; }}
    if(renkSec){{
      s.renk = renkSec.value;
      s.renk_ozel = (renkSec.value === "Diğer" && renkOzel) ? renkOzel.value : "";
    }}
    if(boySec){{ s.boy_etiket = boySec.value || null; }}
    if(URUN_SEMA && window.PRUVO_KONF && PRUVO_KONF.hazir()){{ PRUVO_KONF.satiraYaz(s); }}
    return s;
  }}
  function render(){{
    var c = PRUVO_SECENEK.sepetYukle();
    var satir = currentSatir();
    var anahtar = PRUVO_SECENEK.satirAnahtari(satir);
    var has = c.some(function(s){{ return PRUVO_SECENEK.satirAnahtari(s) === anahtar; }});
    btn.classList.toggle("added", has);
    if(label){{ label.textContent = has ? "Sepette ✓" : "Sepete Ekle"; }}
    if(count){{ count.textContent = c.length; }}
    if(fab){{ fab.style.display = c.length ? "inline-flex" : "none"; }}
    var ozet = PRUVO_SECENEK.satirOzeti(URUN, satir);
    /* Konfigüratörlü sayfada fiyat alanını konfigüratör yönetir (kuruşlu canlı hesap,
       taban fiyat yoksa "—"); geçersiz ölçüde sepete ekleme kilitlenir. */
    if(fiyatEl && !URUN_SEMA){{ fiyatEl.textContent = ozet.fiyatMetni; }}
    if(URUN_SEMA && window.PRUVO_KONF && PRUVO_KONF.hazir()){{
      PRUVO_KONF.tazele();
      var gecerli = PRUVO_KONF.gecerliMi();
      btn.disabled = !gecerli;
      btn.classList.toggle("kilitli", !gecerli);
    }}
    if(orderAlt){{
      var mesaj = "Merhaba, şu ürünle ilgileniyorum: " + URUN.baslik +
                  (ozet.detay ? ("\\n" + ozet.detay) : "") + "\\n" + location.href;
      orderAlt.href = "https://wa.me/{whatsapp}?text=" + encodeURIComponent(mesaj);
    }}
  }}
  btn.addEventListener("click", function(){{
    var c = PRUVO_SECENEK.sepetYukle();
    var satir = currentSatir();
    var anahtar = PRUVO_SECENEK.satirAnahtari(satir);
    var i=-1;
    for(var j=0;j<c.length;j++){{ if(PRUVO_SECENEK.satirAnahtari(c[j])===anahtar){{ i=j; break; }} }}
    if(i===-1){{ c.push(satir); }} else {{ c.splice(i,1); }}
    PRUVO_SECENEK.sepetKaydet(c); render();
  }});
  [malzemeSec, renkSec, boySec].forEach(function(el){{
    if(!el){{ return; }}
    el.addEventListener("change", function(){{
      if(renkSec && renkOzel){{ renkOzel.style.display = renkSec.value === "Diğer" ? "inline-block" : "none"; }}
      render();
    }});
  }});
  if(renkOzel){{ renkOzel.addEventListener("input", render); }}
  if(URUN_SEMA && window.PRUVO_KONF && window.PRUVO_HACIM){{
    PRUVO_KONF.kur(URUN_SEMA, document.getElementById("konfAlanlar"), render);
  }}
  render();
}})();
</script>
</body>
</html>
""".format(
        title=title_tag,
        desc=esc(desc160),
        url=esc(url),
        favicon=FAVICON,
        ogtitle=esc(baslik),
        img=esc(cover),
        product_ld=ld(product_ld),
        breadcrumb_ld=ld(breadcrumb_ld),
        css=PAGE_CSS,
        katq=esc(kategori),
        kategori=esc(kategori),
        baslik=esc(baslik),
        main_img=main_img,
        thumbs=thumbs_html,
        h1=esc(baslik),
        brands=brand_html,
        price=price_html,
        opsiyonlar=opsiyonlar_html,
        badge=badge_html,
        aciklama=aciklama_html,
        wa=esc(wa_href(p, url)),
        icon=WA_ICON,
        pid=esc(p.get("id") or ""),
        cart_icon=CART_ICON,
        related=rel_html,
        foot_nav=FOOT_NAV_HTML,
        pay_band=PAY_BAND_HTML,
        attribution=attribution_html(p),
        urun_json=urun_json,
        sema_json=sema_json,
        konf_scripts=konf_scripts,
        whatsapp=WHATSAPP,
    )
    return doc


# ------------------------------------------------------------------ içerik/yasal sayfa
def render_content_page(slug, title, meta, body_html):
    title_tag = esc(title) + " — PRUVO"
    url = SITE + "/" + slug + "/"
    return u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
<style>{css}</style>
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

<main class="content">
{body}
</main>

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi | Fethiye
  {foot_nav}
  {pay_band}
</footer>
</body>
</html>
""".format(
        title=title_tag,
        desc=esc(meta),
        ogtitle=esc(title),
        url=esc(url),
        favicon=FAVICON,
        css=PAGE_CSS,
        body=body_html,
        foot_nav=FOOT_NAV_HTML,
        pay_band=PAY_BAND_HTML,
    )


# ------------------------------------------------------------------ sitemap
def render_sitemap(products):
    urls = []
    urls.append((SITE + "/", "1.0", "daily"))
    for slug in SITEMAP_SLUGS:
        urls.append((SITE + "/" + slug + "/", "0.4", "monthly"))
    for p in products:
        urls.append((product_url(p["id"]), "0.8", "weekly"))
    items = []
    for loc, prio, freq in urls:
        items.append(
            "  <url>\n"
            "    <loc>%s</loc>\n"
            "    <lastmod>%s</lastmod>\n"
            "    <changefreq>%s</changefreq>\n"
            "    <priority>%s</priority>\n"
            "  </url>" % (esc(loc), TODAY, freq, prio))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(items) + "\n</urlset>\n")


# ------------------------------------------------------------------ Google Merchant feed
def render_merchant_feed(products):
    """Google Merchant Center urun feed'i (RSS 2.0 + g: namespace).
    SADECE parametrik OLMAYAN, sabit sayisal fiyatli, gorseli olan urunler girer;
    parametrik "sari seri" (net fiyati yok) HARIC tutulur. Dondurulen (xml, adet)."""
    items = []
    for p in products:
        if p.get("parametrik"):
            continue                                   # sari seri -> feed disi
        price = feed_price((p.get("fiyat") or "").strip())
        if not price:
            continue                                   # net sayisal fiyati yok -> feed disi
        imgs = images_of(p)
        if not imgs:
            continue                                   # gorselsiz urun feed'e girmez

        pid = p["id"]
        url = product_url(pid)
        title = marka_temiz((p.get("baslik") or "").strip())[:150]
        desc = marka_temiz(re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip())[:5000] or title
        kategori = p.get("kategori") or ""
        markalar = p.get("marka") or []

        row = [
            "    <g:id>%s</g:id>" % esc(pid),
            "    <title>%s</title>" % esc(title),
            "    <description>%s</description>" % esc(desc),
            "    <link>%s</link>" % esc(url),
            "    <g:image_link>%s</g:image_link>" % esc(imgs[0]),
        ]
        for extra in imgs[1:11]:                        # Google en fazla 10 ek gorsel
            row.append("    <g:additional_image_link>%s</g:additional_image_link>" % esc(extra))
        row += [
            "    <g:availability>%s</g:availability>" % FEED_AVAILABILITY,
            "    <g:condition>new</g:condition>",
            "    <g:price>%s TRY</g:price>" % price,
            # Urunu BIZ uretiyoruz -> marka PRUVO (OEM uyum bilgisi baslik/product_type'ta).
            "    <g:brand>%s</g:brand>" % FEED_BRAND,
            "    <g:mpn>%s</g:mpn>" % esc(pid),          # GTIN yok; brand+mpn gecerli kimlik cifti
        ]
        gpc = GOOGLE_PRODUCT_CATEGORY.get(kategori)
        if gpc:
            row.append("    <g:google_product_category>%s</g:google_product_category>" % esc(gpc))
        ptype = kategori + (" > " + markalar[0] if markalar else "")
        if ptype:
            row.append("    <g:product_type>%s</g:product_type>" % esc(ptype))
        items.append("  <item>\n" + "\n".join(row) + "\n  </item>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
           '<channel>\n'
           '  <title>PRUVO — Özel Tasarım Üretim Yedek Parça</title>\n'
           '  <link>' + SITE + '</link>\n'
           '  <description>PRUVO özel tasarım üretim yedek parça ürün listesi.</description>\n'
           + "\n".join(items) + "\n</channel>\n</rss>\n")
    return xml, len(items)


# ------------------------------------------------------------------ ana akış
def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    # eski urun/ klasörünü temizle (silinen ürünler kalmasın)
    if os.path.isdir(URUN_DIR):
        shutil.rmtree(URUN_DIR)
    os.makedirs(URUN_DIR, exist_ok=True)

    for p in products:
        pdir = os.path.join(URUN_DIR, p["id"])
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_product(p, products))

    # içerik/yasal sayfalar (/<slug>/index.html)
    for slug, title, meta, fn in CONTENT_PAGES:
        cdir = os.path.join(ROOT, slug)
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_content_page(slug, title, meta, fn()))

    # sitemap.xml
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(render_sitemap(products))

    # merchant-feed.xml  (Google Merchant Center — sadece sabit fiyatli urunler)
    feed_xml, feed_n = render_merchant_feed(products)
    with open(os.path.join(ROOT, MERCHANT_FEED), "w", encoding="utf-8") as f:
        f.write(feed_xml)

    # robots.txt
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: " + SITE + "/sitemap.xml\n")

    # .nojekyll  (GitHub Pages tüm dosyaları olduğu gibi sunsun)
    open(os.path.join(ROOT, ".nojekyll"), "w").close()

    print("OK: %d urun sayfasi + sitemap.xml + robots.txt + merchant-feed.xml (%d urun) uretildi."
          % (len(products), feed_n))


if __name__ == "__main__":
    main()
