#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA -> MODEL KABUL KAPISI (anasayfa çip-marka evreni: Ford/BMW + Volkswagen/Toyota/Mercedes...).

marka_model_build jeneratörünü İZOLE temp ROOT'a çalıştırır ve üretilen HTML'i spec kabul
kriterleriyle ölçer. Ayrıca anasayfa marka çiplerinin SSR link enjeksiyonunu (build._marka_cip_enjekte)
doğrular. build.py'nin urun/ çıktısına MUHTAÇ DEĞİL (modülü doğrudan çağırır). FAIL-CLOSED.

Ölçülen:
  1. Marka evreni index.html TANINMIS_MARKALAR'dan; folding (Mercedes-Benz->Mercedes, Vauxhall->Opel).
  2. Collision: Ford F-150/F150 tek 'f-150' URL; marka slug + model slug eşsiz.
  3. Eşik: yalnız >=3-ürünlü marka SAYFASI + >=3-ürünlü model sayfası; <3 marka/model AYRI sayfa DEĞİL.
  4. Örnek marka/model URL'leri: SSR H1 + ürün <a> + self-canonical + ItemList/CollectionPage/
     BreadcrumbList JSON-LD + sitemap lastmod + huni prefill + attribution modülü.
  5. Öksüz yok: sayfası olan markanın TÜM (folded) ürünleri linkli.
  6. Marka kuralları: authored copy'de yasaklı token 0; telefon yalnız 905451386526.
  7. Anasayfa çipleri: chip_links her biri <a href="/marka/<slug>/">; SSR enjeksiyon #brandChips'i
     doldurur + window.PRUVO_MARKA_SLUG gömülür; her çip markasının SAYFASI var (sayfasız=0 ya da NOT).

Kullanım: python3 tools/marka-model-test.py
"""
import os
import re
import sys
import json
import html
import tempfile
import shutil
from urllib.parse import unquote

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import build                    # noqa: E402
import marka_model_build as mm  # noqa: E402

HATALAR = []
BILGI = []


def bekle(kosul, mesaj):
    if not kosul:
        HATALAR.append(mesaj)


BANNED = [
    r"3\s*d\s*bask", r"3\s*boyutlu\s*bask", r"3d\s*print", r"\bbask[ıi]l?[ıi]?\b",
    r"\byaz[ıi]c[ıi]", r"\bfilament", r"\bfethiye\b", r"\bg[öo]cek\b",
    r"her\s+renk", r"makerworld", r"openscad", r"jenerat[öo]r",
]
BANNED_RE = [re.compile(p, re.I) for p in BANNED]


def authored(page):
    """Yalnız SAYFANIN AUTHORED copy'sini (H1/giriş/başlık/breadcrumb/huni/model-buton +
    meta description) toplar. Ürün kartları (<div class="grid"> — KATALOG verisi: başlık/
    açıklama /urun/ sayfasında aynen görünür) marka-lint KAPSAMI DIŞI (koordinatör notu).
    Extract yaklaşımı: kart div'leri iç içe olduğundan strip yerine authored bölgeleri ayıklar."""
    parts = re.findall(r'<h1>.*?</h1>', page, re.S)
    parts += re.findall(r'<p class="lead">.*?</p>', page, re.S)
    parts += re.findall(r'<h2 class="mm-sec-h">.*?</h2>', page, re.S)
    parts += re.findall(r'<nav class="mm-bc".*?</nav>', page, re.S)
    parts += re.findall(r'<div class="mm-huni">.*?</div>', page, re.S)
    parts += re.findall(r'<a class="mm-model-btn"[^>]*>.*?</a>', page, re.S)
    parts += re.findall(r'<meta name="description" content="[^"]*">', page)
    return " ".join(parts)


def main():
    tmp = tempfile.mkdtemp(prefix="mm-kabul-")
    try:
        with open(build.JSON_PATH, encoding="utf-8") as f:
            products = json.load(f)
        with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
            index_html = f.read()

        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        # index.html'i temp ROOT'a da koy (uret oradan marka evrenini okur)
        with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        sonuc = mm.uret(products, ctx)
        bekle(isinstance(sonuc, dict), "uret dict döndürmedi")
        sitemap = sonuc["sitemap"]
        loclar = {loc for loc, _p, _f in sitemap}
        sm_str = build.render_sitemap(products, extra_urls=sitemap)
        bekle(sonuc["dizinler"] == ["marka"], "üst dizin ['marka'] değil")

        evren = mm.MarkaEvreni(index_html)
        veri = mm.gruplandir(products, evren)

        # ===== 1: folding =====
        bekle("Ford" in veri and "BMW" in veri, "Ford/BMW evrende yok")
        bekle("Vauxhall" not in veri, "Vauxhall ayrı marka (Opel'e katlanmadı)")
        bekle("Opel" in veri, "Opel evrende yok")
        vaux = [p for p in products if (p.get("marka") or [""])[0] == "Vauxhall"]
        if vaux:
            opel_ids = {p.get("id") for p in veri["Opel"]["marka_only"]}
            for g in veri["Opel"]["gruplar"].values():
                opel_ids |= {p.get("id") for p in g["urunler"]}
            bekle(all(p.get("id") in opel_ids for p in vaux),
                  "Vauxhall ürünleri Opel'e katlanmadı")

        # ===== 2: collision (YAPISAL — sabit katalog sayısına bağlı DEĞİL, drift'e dayanıklı) =====
        ford_gruplar = veri["Ford"]["gruplar"]
        f150 = next((g for g in ford_gruplar.values() if g["slug"] == "f-150"), None)
        # F-150 model sayfası DİSKTE var + ürün sayısı >= eşik (201 gibi sabit sayı DEĞİL) +
        # AYRI f150/f-series slug YOK -> collision birleşmesi yapısal olarak kanıtlanır.
        bekle(f150 is not None and len(f150["urunler"]) >= mm.ESIK, "F-150 grubu yok / <eşik")
        bekle(os.path.exists(os.path.join(tmp, "marka", "ford", "f-150", "index.html")),
              "F-150 model sayfası DİSKTE yok")
        bekle(not any(g["slug"] == "f150" for g in ford_gruplar.values()),
              "ayrı 'f150' slug (collision folded değil)")
        bekle(not any(g["slug"] == "f-series" for g in ford_gruplar.values()),
              "F-Series ayrı slug (alias uygulanmadı)")
        # Peugeot 206 TEK URL (çift-marka/collision regresyon kanıtı): '206' var, 'peugeot-206' YOK.
        if "Peugeot" in veri:
            psl = {g["slug"] for g in veri["Peugeot"]["gruplar"].values()}
            bekle("peugeot-206" not in psl and "peugeot-205" not in psl,
                  "Peugeot çift-marka slug (peugeot-206/205) hâlâ var")
        # ÇİFT-MARKA H1 GUARD (§9.1): hiçbir grup display'i markayla başlamamalı
        # ("Peugeot Peugeot 206" gibi). Yapısal — katalog sayısından bağımsız.
        cift_marka = []
        for mk, dd in veri.items():
            for g in dd["gruplar"].values():
                t = g["display"].split()
                if len(t) > 1 and evren.taninmis_mi(t[0]) and evren.katla(t[0]) == mk:
                    cift_marka.append((mk, g["display"]))
        bekle(not cift_marka, "çift-marka H1 var: %s" % cift_marka[:5])
        # Model slug her marka içinde eşsiz (global collision nöbeti)
        for mk, dd in veri.items():
            sl = [g["slug"] for g in dd["gruplar"].values()]
            bekle(len(sl) == len(set(sl)), "%s: model slug collision" % mk)
        marka_sluglar = [mm._slug(m) for m in sonuc["slug_map"]]
        bekle(len(marka_sluglar) == len(set(marka_sluglar)), "marka slug'ları eşsiz değil")

        # ===== 3: eşik + sayfa envanteri =====
        marka_dizinleri = []
        marka_kok = os.path.join(tmp, "marka")
        for ad in os.listdir(marka_kok):
            alt = os.path.join(marka_kok, ad)
            if os.path.isdir(alt) and os.path.exists(os.path.join(alt, "index.html")):
                marka_dizinleri.append(ad)
        bekle(len(marka_dizinleri) == sonuc["marka_sayfasi_sayisi"],
              "marka dizini sayısı raporla uyuşmuyor (%d != %d)"
              % (len(marka_dizinleri), sonuc["marka_sayfasi_sayisi"]))
        for m, slug in sonuc["slug_map"].items():
            tot = sum(len(g["urunler"]) for g in veri[m]["gruplar"].values()) + len(veri[m]["marka_only"])
            bekle(tot >= mm.ESIK, "%s marka sayfası aldı ama <%d ürün" % (m, mm.ESIK))
        ince = None
        for m, d in veri.items():
            tot = sum(len(g["urunler"]) for g in d["gruplar"].values()) + len(d["marka_only"])
            if tot < mm.ESIK:
                ince = m
                break
        if ince:
            bekle(not os.path.exists(os.path.join(tmp, "marka", mm._slug(ince))),
                  "<3 ürünlü marka AYRI sayfa aldı: %s" % ince)
        BILGI.append("marka sayfası: %d · model sayfası: %d · ince marka örneği: %s"
                     % (sonuc["marka_sayfasi_sayisi"], sonuc["model_sayfasi_sayisi"], ince))

        # ===== 4: örnek marka/model URL derin ölçüm =====
        ornek_markalar = ["Ford", "BMW", "Volkswagen", "Toyota", "Mercedes"]
        for marka in ornek_markalar:
            if marka not in veri:
                continue
            marka_slug = mm._slug(marka)
            myol = os.path.join(tmp, "marka", marka_slug, "index.html")
            bekle(os.path.exists(myol), "%s marka sayfası yok" % marka)
            if os.path.exists(myol):
                with open(myol, encoding="utf-8") as f:
                    mp = f.read()
                murl = "https://pruvo3d.com/marka/%s/" % marka_slug
                bekle(('<link rel="canonical" href="%s">' % murl) in mp, "%s marka canonical yok" % marka)
                bekle("{model}" not in mp and "{marka}" not in mp, "%s marka token sızıntı" % marka)
                bekle("wa.me/905451386526" in mp, "%s marka huni yok" % marka)
                for rex in BANNED_RE:
                    mt = rex.search(authored(mp))
                    bekle(mt is None, "%s marka yasaklı token '%s'" % (marka, mt.group(0) if mt else ""))
            buyuk = sorted([g for g in veri[marka]["gruplar"].values() if len(g["urunler"]) >= mm.ESIK],
                           key=lambda g: -len(g["urunler"]))
            if not buyuk:
                continue
            g = buyuk[0]
            yol = os.path.join(tmp, "marka", marka_slug, g["slug"], "index.html")
            bekle(os.path.exists(yol), "%s/%s model sayfası yok" % (marka_slug, g["slug"]))
            if not os.path.exists(yol):
                continue
            with open(yol, encoding="utf-8") as f:
                page = f.read()
            url = "https://pruvo3d.com/marka/%s/%s/" % (marka_slug, g["slug"])
            bekle("<h1>" in page and "Yedek Parça" in page, "%s SSR H1 yok" % g["slug"])
            bekle(len(re.findall(r'href="https://pruvo3d\.com/urun/', page)) >= mm.ESIK,
                  "%s ürün linki < %d" % (g["slug"], mm.ESIK))
            # GÖRSELLİ KART (düz-yazı regresyon nöbeti): standart katalog kartı = card-main +
            # card-img (lazy, gerçek görsel src) + card-cat/card-title/card-price (kartCiz ile aynı).
            bekle(len(re.findall(r'<a class="card-main" href="', page)) >= mm.ESIK,
                  "%s card-main < eşik (kart bileşeni yok)" % g["slug"])
            imglar = re.findall(r'<img class="card-img"[^>]*\bloading="lazy"[^>]*\bsrc="([^"]+)"', page)
            bekle(len(imglar) >= mm.ESIK,
                  "%s card-img < eşik — DÜZ YAZIYA regresyon?" % g["slug"])
            bekle(any(s.startswith("https://") for s in imglar),
                  "%s gerçek görsel src yok (hepsi placeholder?)" % g["slug"])
            for kls in ('card-cat', 'card-title', 'card-desc', 'card-price'):
                bekle(('class="%s"' % kls) in page, "%s katalog kart sınıfı '%s' yok" % (g["slug"], kls))
            bekle('<div class="grid">' in page, "%s kart grid container'ı yok" % g["slug"])
            bekle(('<link rel="canonical" href="%s">' % url) in page, "%s self-canonical yok" % g["slug"])
            bekle('<meta name="robots" content="index,follow">' in page, "%s robots yok" % g["slug"])
            for t in ('"ItemList"', '"CollectionPage"', '"BreadcrumbList"'):
                bekle(t in page, "%s %s JSON-LD yok" % (g["slug"], t))
            bekle(("<loc>%s</loc>" % url) in sm_str and url in loclar and "<lastmod>" in sm_str,
                  "%s sitemap lastmod yok" % g["slug"])
            was = re.findall(r'https://wa\.me/905451386526\?text=([^"]+)', page)
            bekle(len(was) >= 1, "%s wa.me CTA yok" % g["slug"])
            if was:
                dec = unquote(was[0])
                bekle((marka + " " + g["display"]) in dec, "%s prefill marka+model yok" % g["slug"])
                bekle("REF:" not in dec, "%s statik prefill REF içeriyor" % g["slug"])
            bekle("PRUVO attribution module: start" in page and "window.pruvoRef" in page,
                  "%s attribution modülü yok" % g["slug"])
            bekle("{model}" not in page and "{marka}" not in page, "%s token sızıntı" % g["slug"])
            for rex in BANNED_RE:
                mt = rex.search(authored(page))
                bekle(mt is None, "%s yasaklı token '%s'" % (g["slug"], mt.group(0) if mt else ""))
            bekle("532" not in authored(page), "%s authored 532" % g["slug"])
            for waurl in re.findall(r'wa\.me/(\d+)', page):
                bekle(waurl == "905451386526", "%s yanlış wa numarası %s" % (g["slug"], waurl))
            for blok in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
                try:
                    json.loads(blok)
                except Exception as e:
                    HATALAR.append("%s JSON-LD parse hatası: %s" % (g["slug"], e))

        # ===== 5: öksüz yok (örnek markalarda) =====
        for marka in ornek_markalar:
            if marka not in veri:
                continue
            beklenen = set()
            for p in products:
                mk = p.get("marka") or []
                if mk and evren.taninmis_mi(mk[0]) and evren.katla(mk[0]) == marka and p.get("id"):
                    beklenen.add(p["id"])
            linkli = set()
            for dp, _d, fs in os.walk(os.path.join(tmp, "marka", mm._slug(marka))):
                for fn in fs:
                    if fn == "index.html":
                        with open(os.path.join(dp, fn), encoding="utf-8") as f:
                            pg = f.read()
                        for pid in re.findall(r'href="https://pruvo3d\.com/urun/([^/"]+)/"', pg):
                            linkli.add(html.unescape(pid))
            eksik = beklenen - linkli
            bekle(not eksik, "%s: %d ürün öksüz (linkli değil)" % (marka, len(eksik)))
            BILGI.append("%s: %d ürün, öksüz=%d" % (marka, len(beklenen), len(eksik)))

        # ===== 6: /marka/ index =====
        idx = os.path.join(tmp, "marka", "index.html")
        bekle(os.path.exists(idx), "/marka/ index yok")
        if os.path.exists(idx):
            with open(idx, encoding="utf-8") as f:
                ip = f.read()
            bekle('href="/marka/ford/"' in ip and 'href="/marka/bmw/"' in ip,
                  "/marka/ index marka linkleri eksik")

        # ===== 7: anasayfa çipleri SSR + enjeksiyon =====
        chip_links = sonuc["chip_links"]
        bekle(bool(chip_links), "chip_links boş")
        chip_hrefs = re.findall(r'<a class="brand-btn brand-link[^"]*" href="(/marka/[^"]+/)">', chip_links)
        bekle(len(chip_hrefs) >= 20, "SSR çip linki az (%d)" % len(chip_hrefs))
        for m in sonuc["chip_markalar"]:
            if m in sonuc["slug_map"]:
                slug = sonuc["slug_map"][m]
                bekle(('/marka/%s/' % slug) in chip_links, "%s çipi linkli değil" % m)
                # Çip-hedef sayfası DİSKTE var mı — slug_map'e körü körüne GÜVENME (dangling link nöbeti)
                bekle(os.path.exists(os.path.join(tmp, "marka", slug, "index.html")),
                      "%s çip-hedefi /marka/%s/ DİSKTE yok (dangling link)" % (m, slug))
        bekle(len(sonuc["sayfasiz_cipler"]) == 0, "sayfasız çip var: %s" % sonuc["sayfasiz_cipler"])
        enj = build._marka_cip_enjekte(index_html, chip_links, sonuc["slug_map"])
        bekle('<div class="brand-chips" id="brandChips"><a class="brand-btn brand-link' in enj,
              "SSR enjeksiyon #brandChips'i doldurmadı")
        bekle("window.PRUVO_MARKA_SLUG=" in enj, "PRUVO_MARKA_SLUG gömülmedi")
        bekle('href="/marka/ford/"' in enj and 'href="/marka/bmw/"' in enj,
              "enjekte HTML'de ford/bmw çip linki yok (JS-siz SSR)")
        BILGI.append("SSR çip: %d marka linki (JS-siz), sayfasız çip: %d"
                     % (len(chip_hrefs), len(sonuc["sayfasiz_cipler"])))

        # ===== 8: KART MARKA-LINT (temizleme sonrası) — baskı-jargonu 0, over-clean YOK =====
        # Kart title/desc = KATALOG metni; sanitize (mm._kart_temizle) baskı-jargonunu okunur
        # karşılığa çevirir, mekanik anlamı (baskı plakası/basma butonu/baskı altında) KORUR.
        # Bağımsız doğrulama: üretilen TÜM /marka/ kartlarını tarar; temizleyici baypaslanırsa
        # jargon görünür -> KIRMIZI (sabotaj nöbeti, tautoloji değil — çıktıyı tarar).
        card_re = re.compile(r'<div class="card-(?:title|desc)">(.*?)</div>', re.S)
        toplam_jargon = 0
        jargon_ornek = []
        # basınç/mekanik KORUMA sayaçları (over-clean nöbeti — bu terimler ÇIKTIDA durmalı)
        koru = {"3D-Tarama": r"3\s*d\s*tara", "baskı-plakası": r"bask[ıi]\w*\s+plaka",
                "baskı-balata": r"bask[ıi]\w*\s+(?:ve\s+)?balata", "baskı-uygula": r"bask[ıi]\w*\s+uygula",
                "baskı-altında": r"bask[ıi]\w*\s+alt[ıi]", "baskıyı": r"\bbaskıyı\b",
                "basma-buton/düğme": r"basma\s+buton|basmal[ıi]\s+düğme"}
        koru_say = {k: 0 for k in koru}
        # MANGLE dedektörü (DAR — false-positive'siz): basınç-"baskı plakası/balata/altında"nın
        # "üretim ..."e mangle'ı ancak POSSESSIF/kesin biçimde görünür. "üretilen plaka tutucu"
        # (meşru ürün) gibi biçimler HARİÇ (plakas≠plaka, üretilen≠üretim+balata).
        mangle_re = re.compile(r"üretim\s+plakas|üreti[lm]\w*\s+balata|üretim\s+ve\s+balata"
                               r"|üretim\s+alt[ıi]nda", re.I)
        mangle_toplam = 0
        mangle_ornek = []
        kart_sayisi = 0
        for dp, _d, fs in os.walk(os.path.join(tmp, "marka")):
            for fn in fs:
                if fn != "index.html":
                    continue
                with open(os.path.join(dp, fn), encoding="utf-8") as f:
                    b = f.read()
                for cm in card_re.finditer(b):
                    kart_sayisi += 1
                    txt = html.unescape(cm.group(1))
                    ihl = mm.kart_lint_ihlaller(txt)
                    if ihl:
                        toplam_jargon += len(ihl)
                        if len(jargon_ornek) < 6:
                            jargon_ornek.append((ihl, txt[:70]))
                    low = txt.lower()
                    for k, rx in koru.items():
                        if re.search(rx, low):
                            koru_say[k] += 1
                    mg = mangle_re.findall(txt)
                    if mg:
                        mangle_toplam += len(mg)
                        if len(mangle_ornek) < 6:
                            mangle_ornek.append((mg, txt[:70]))
        # (1) JARGON-KAÇAĞI 0 (kesin printing token; temizleyici baypas -> KIRMIZI)
        bekle(toplam_jargon == 0,
              "kartlarda printing-jargonu %d (temizleyici baypas?): %s" % (toplam_jargon, jargon_ornek))
        # (2a) BİRİM-DÜZEY MANGLE KİLİDİ (kesin, false-positive'siz): temizleyici basınç/mekanik
        # "baskı" kolokasyonlarını DEĞİŞTİRMEMELİ (çürütücünün bulduğu 16 mangle sınıfı). Sabotaj
        # (bare-baskı çevirisi geri eklenirse) bu ifadeler değişir -> KIRMIZI.
        basinc_ifade = [
            "debriyaj diski ve baskıyı hizalamak", "baskı plakasına tam merkezli",
            "cama baskı uygulanmaması önerilir", "baskı balatayı kusursuz şekilde hizalama",
            "baskı ve balatanın kusursuz", "rulmana baskı yaparak", "baskı altında zayıf",
            "volan/baskı merkezine", "baskıyla oturtularak", "rulman baskısı için",
            "kontrollü baskı uygulanmasına", "basmalı düğmenin", "basma butonunun",
        ]
        for ifade in basinc_ifade:
            bekle(mm._kart_temizle(ifade) == ifade,
                  "PRESSURE/BUTTON mangle: %r -> %r" % (ifade, mm._kart_temizle(ifade)))
        # (2b) ÇIKTI HEURİSTİĞİ (dar): basınç-baskı mangle imzası çıktıda 0.
        bekle(mangle_toplam == 0,
              "MANGLE %d: basınç-baskı 'üretim'e mangle edilmiş (over-clean): %s"
              % (mangle_toplam, mangle_ornek))
        # (3) KORUMA yapısal: basınç/mekanik kolokasyonlar çıktıda KORUNMUŞ olmalı (>0)
        for k in ("3D-Tarama", "baskı-plakası", "baskı-balata", "baskı-uygula", "basma-buton/düğme"):
            bekle(koru_say[k] > 0, "'%s' hiçbir kartta korunmadı — aşırı-temizleme şüphesi" % k)
        BILGI.append("kart marka-lint: %d kart · printing-jargon=%d · MANGLE=%d · korundu: %s"
                     % (kart_sayisi, toplam_jargon, mangle_toplam,
                        " ".join("%s=%d" % (k, koru_say[k]) for k in koru)))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n".join("  · " + b for b in BILGI))
    if HATALAR:
        print("\nKIRMIZI — %d ihlal:" % len(HATALAR))
        for h in HATALAR:
            print("  X " + h)
        sys.exit(1)
    print("\nHEPSI GECTI")


if __name__ == "__main__":
    main()
