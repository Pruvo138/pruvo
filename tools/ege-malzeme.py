#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ege-bilgi.md "MALZEME KAPSAMI" bolumunu tools/filamentler.json'dan uretir/gunceller.

Kullanim:  python3 tools/ege-malzeme.py

NEDEN: Ege'nin malzeme anlatimi ile sitedeki filament rehberi AYNI referanstan
beslensin (tek kaynak) — ikisi asla celismesin. Bolum, dosyadaki isaretciler
arasina yazilir; isaretci yoksa (ilk calisma) "### MALZEME KAPSAMI" basligindan
bir sonraki "## " basligina kadar olan blok isaretcili blokla DEGISTIRILIR.
Dosyanin geri kalanina DOKUNULMAZ. Idempotent: ayni girdiyle ikinci calisma
dosyayi degistirmez. (ege-bilgi.md public — sir icermez; pruvo-bot reposuna dokunmaz.)
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filament_ortak

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EGE = os.path.join(ROOT, "ege-bilgi.md")
BASLA = "<!-- FILAMENT-REF-BASLA (tools/ege-malzeme.py uretir; ELLE DUZENLEME — kaynak tools/filamentler.json) -->"
BITIR = "<!-- FILAMENT-REF-BITIR -->"


def bolum_uret():
    ref = filament_ortak.referans()
    satirlar = []
    for f in ref["filamentler"]:
        if not f.get("site"):
            continue
        satirlar.append("- **%s** (%s) — ısı %s — %s"
                        % (f.get("uzunAd") or f["ad"], f["kisaEtiket"],
                           f["isiDayanimi"], f["kisa"]))
    ozel_satirlar = []
    for f in ref["filamentler"]:
        if f.get("site"):
            continue
        ozel_satirlar.append(
            "- **%s** (%s) — ısı %s — standart sipariş akışında YOK, WhatsApp özel "
            "talebiyle değerlendirilir — üretim kararıdır, koşulu netleştir + [DEVRET]"
            % (f.get("uzunAd") or f["ad"], f["kisaEtiket"], f["isiDayanimi"]))

    # Kategori -> varsayilan tavsiye ozeti (ayni listeyi paylasanlar gruplanir)
    gruplar, sira = {}, []
    for kat, liste in ref["kategoriTavsiye"].items():
        anahtar = repr(liste)
        if anahtar not in gruplar:
            gruplar[anahtar] = ([], liste)
            sira.append(anahtar)
        gruplar[anahtar][0].append(kat)
    oneriler = []
    for anahtar in sira:
        katlar, liste = gruplar[anahtar]
        parca = liste[0]["ad"]
        for t in liste[1:]:
            # .lower() KULLANMA: Python "Isınan"->"isınan" yapar (Turkce I/ı hatasi)
            parca += "; %s %s" % (t.get("not") or "alternatif", t["ad"])
        oneriler.append("%s → %s" % ("/".join(katlar), parca))

    return "\n".join([
        BASLA,
        "Bizim malzemelerimiz özel üretim **filamentleri**. Ege SADECE bu aileden seçenek sunar; "
        "uygun filament(ler)i önerebilir, adını da söyleyebilir. Standart (sitede doğrudan "
        "sipariş edilen) ailemiz ve dürüst değerleri (ısı dayanımı = HDT @ 0.45 MPa, yaklaşık "
        "aralık; abartma, taahhüt sayılır):",
    ] + satirlar + [
        "",
        "Mühendislik malzemeleri (standart ailenin dışında, üretim kararı gerektirir):",
    ] + ozel_satirlar + [
        "- **Daha yüksek ısı / mukavemet:** Naylon (PA), PC (polikarbonat) ve elyaf katkılı türler "
        "tedarik edilebilir — üretim kararıdır, koşulu netleştir + [DEVRET]",
        "",
        "Kategoriye göre varsayılan tavsiyemiz: " + " · ".join(oneriler) + ".",
        "ÖNEMLİ: karbon katkı ISI dayanımını ARTIRMAZ (taşıyıcının değerini korur; PETG-CF ~70°C) — "
        "karbonu mukavemet/sertlik için öner, ısı sorulursa taşıyıcıya bak.",
        "",
        "**ASLA filament DIŞI malzeme sunma / taahhüt etme:** kalıp/döküm KAUÇUK-elastomer "
        "(NBR, FKM/Viton, EPDM, silikon), metal, cam vb. Bunlar bizim sürecimizde YOK; "
        "sunulması yakışık almaz, yalan söz olur.",
        "",
        "- Malzemenin KRİTİK olduğu iş (yakıt/yağ/kimyasal teması, yüksek ısı, gıda, yüksek yük): "
        "bir filamentin o şartı tam karşılayıp karşılamayacağı üretim kararıdır. Koşulu net topla "
        "(hangi sıvı/yakıt · sürekli mi ara sıra mı · kaç derece · esnek mi sert mi), uygun "
        "filamenti + fiyatı belirleyip ileteceğini söyle + [DEVRET]. Kesin performans garantisi verme.",
        "- Uzmanlığını doğru soruları sorarak göster; eğitici olabilirsin (\"yanlış malzeme yakıtta "
        "şişer/bozulur, o yüzden koşulu netleştiriyorum\") ama filament-dışı bir malzemeyi çözüm "
        "diye sunma.",
        BITIR,
    ])


def main():
    with io.open(EGE, encoding="utf-8") as f:
        icerik = f.read()
    blok = bolum_uret()

    if BASLA in icerik and BITIR in icerik:
        yeni = re.sub(re.escape(BASLA) + r".*?" + re.escape(BITIR), lambda m: blok,
                      icerik, count=1, flags=re.S)
    else:
        # Ilk calisma: "### MALZEME KAPSAMI" basligindan sonraki "## " basligina kadar degistir
        m = re.search(r"(### MALZEME KAPSAMI[^\n]*\n).*?(?=^## )", icerik, flags=re.S | re.M)
        if not m:
            sys.exit("ege-bilgi.md'de '### MALZEME KAPSAMI' bolumu bulunamadi — dosyaya dokunulmadi.")
        yeni = icerik[:m.start()] + m.group(1) + blok + "\n\n" + icerik[m.end():]

    if yeni == icerik:
        print("ege-bilgi.md zaten guncel (degisiklik yok).")
        return
    with io.open(EGE, "w", encoding="utf-8") as f:
        f.write(yeni)
    print("ege-bilgi.md MALZEME KAPSAMI bolumu filamentler.json'dan guncellendi.")


if __name__ == "__main__":
    main()
