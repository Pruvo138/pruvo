#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SÜRÜCÜSÜ — tools/marka-uyelik-test.py gerçek ihlali HÂLÂ yakıyor mu?

NEDEN REPODA DURUYOR: anlatılan batarya kanıt değildir ([[mutasyon-kaniti-yeniden-uretilebilir]]).
3 Ağu'da bu kapı 13 marka + 727 çip için YANLIŞ-POZİTİF kırmızı yaktı ve `deploy`/`yayin`
işlerini atlatarak TÜM ekibin yayınını durdurdu; kapı beklentisi daraltıldı. Daraltma =
gevşetme olmadığının kanıtı bu sürücüdür: gerçek bozulmalar hâlâ TEK BAŞINA kırmızı yakmalı.

NASIL: mutant DAİMA KOPYAYA uygulanır (gerçek ağaç değişmez), kapı `--modul <kopya>` ile koşar.
⚠️ `--modul` kopyası komşu dosya arar (`cip-indeks.py`) — bu yüzden kopya, tools/ AYNASI olan
geçici bir dizinde yaşar; ayna symlink'tir, gerçek tools/ ağacına HİÇBİR ŞEY yazılmaz.
🔴 ÇÖKME KIRMIZIYLA KARIŞTIRILMAZ: rc 0/1 dışı, "kırmızı ama ölçülen FAIL yok" ya da ölçülen
PASS sayısı tabanın altına düşmüş koşum ÇÖKME sayılır — çöken mutant "öldürüldü" DEĞİLDİR.
🔴 HEDEF KOL ATFI (5. alan `hedef_iz`, 19 Ağu 2026 K216): "kırmızı geldi" tek başına kanıt
DEĞİLDİR; iz verilen mutantta FAIL satırlarından EN AZ BİRİ o izi taşımalı, yoksa gözlem
`KIRMIZI-YANLIS-KOL` olur ve mutant öldürülmüş SAYILMAZ. Kolun kendi KONTROL'ü (K3) de
zorunlu: aynı satıra dokunan ama davranışı değiştirmeyen yazım YEŞİL kalmalı.

Kabul: her ÖLDÜRÜCÜ KIRMIZI + her KONTROL YEŞİL (rc 0). Koşum dakikalar sürer —
CI yolunda DEĞİL, kapı ya da üreteç değiştiğinde elle koşulur.

Çalıştır:  python3 tools/marka-uyelik-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAYNAK = os.path.join(TOOLS, "marka_model_build.py")
KAPI = os.path.join(TOOLS, "marka-uyelik-test.py")
TABAN_PASS = 10          # bunun altına düşen koşum "yeşil/kırmızı" değil ÇÖKME'dir

MUTANTLAR = [
    # (ad, eski, yeni, beklenen, hedef_iz)
    # 🔴 `hedef_iz` (19 Agu 2026, K216): "KIRMIZI geldi" KANIT DEGILDIR — kirmizinin SEBEBI
    # hedef kol mu, onu gostermek gerekir. Iz verilen mutantta, FAIL satirlarindan EN AZ BIRI
    # bu dizeyi TASIMALI; tasimiyorsa gozlem "KIRMIZI" degil "KIRMIZI-YANLIS-KOL"dur ve
    # mutant OLDURULMUS SAYILMAZ. (Olculdu: hedefle birlikte dusen bir tautoloji, iddiayi
    # bosaltirken tabloyu yesil birakabiliyor — [[isci-yesil-tablo-ic-olcumu-bosaltir]].)
    ("OLDURUCU M1 sayfa evrenini kuratorluge geri dondur (cip evreni kopar)",
     "veri = gruplandir(products, evren, ek_markalar)",
     "veri = gruplandir(products, evren)", "KIRMIZI", None),
    # 🔴 ÇAPALAR 3 Ağu'da TAŞINDI (üreteç yeniden düzenlendi: model üyeliği pozisyondan
    # kurtarıldı, birincil marka `birincil_marka()`ya çıktı). Mutantın KENDİSİ aynı ihlali
    # anlatır; yalnız tutunduğu satır güncellendi — "çapa yok" gözlemi kanıt DEĞİLDİR.
    ("OLDURUCU M2 uyelik yalniz marka[0]'dan dogsun (ikincil marka uyeligi olur)",
     "    uyeler = []\n    for x in marka_dizisi:",
     "    uyeler = []\n    for x in marka_dizisi[:1]:", "KIRMIZI", None),
    ("OLDURUCU M3 cip haritasi IKINCIL markaya kaysin",
     "    return ham0 if (evren.taninmis_mi(ham0) or ham0 in ek_markalar) else uyeler[0]",
     "    return uyeler[-1]", "KIRMIZI", None),
    ("OLDURUCU M4 model uyeligini yeniden marka[1]'e sabitle (olculen eski sessiz hata)",
     "    for x in marka_dizisi:\n        t = (x or \"\").strip()",
     "    for x in marka_dizisi[1:2]:\n        t = (x or \"\").strip()", "KIRMIZI", None),
    # ---- K216 UZUN-ONCE KOLU (19 Agu 2026): uc mutant, ucu de AYNI kolu ayri yerinden
    # kirar ve ucu de `hedef_iz="K216"` ile HEDEF KOL ATFI tasir.
    ("OLDURUCU M5/K216 tuketimi ekleme yargisina geri bagla (olculen ASIL kusur)",
     "            vuruldu = n\n"
     "            if kan not in uyeler and kan not in eklendi:\n"
     "                eklendi.add(kan)\n"
     "                sonuc.append(kan)\n"
     "            break",
     "            if kan not in uyeler and kan not in eklendi:\n"
     "                eklendi.add(kan)\n"
     "                sonuc.append(kan)\n"
     "                vuruldu = n\n"
     "                break",
     "KIRMIZI", "K216"),
    ("OLDURUCU M6/K216 eksik tuketim (uzun eslesme 1 jeton yutsun)",
     "            vuruldu = n\n            if kan not in uyeler and kan not in eklendi:",
     "            vuruldu = 1\n            if kan not in uyeler and kan not in eklendi:",
     "KIRMIZI", "K216"),
    ("OLDURUCU M7/K216 ilerletmede tuketimi at (i daima 1 artsin)",
     "        i += vuruldu or 1\n    return sonuc",
     "        i += 1\n    return sonuc", "KIRMIZI", "K216"),
    ("KONTROL K1 iddia edilmeyen eksen (meta description metni)",
     '<meta name="description" content="{desc}">',
     '<meta name="description" content="{desc} ">', "YESIL", None),
    ("KONTROL K2 davranisi degistirmeyen yazim (uyeler = [] -> list())",
     "    uyeler = []\n    for x in marka_dizisi:",
     "    uyeler = list()\n    for x in marka_dizisi:", "YESIL", None),
    # K216 kolunun KENDI kontrolu: davranisi degistirmeyen yazim (n -> (n)) — kol canli
    # olcumde ama batarya "her dokunusa kirmizi yakan" bir damga DEGIL.
    ("KONTROL K3/K216 davranisi degistirmeyen yazim (vuruldu = n -> vuruldu = (n))",
     "            vuruldu = n\n            if kan not in uyeler and kan not in eklendi:",
     "            vuruldu = (n)\n            if kan not in uyeler and kan not in eklendi:",
     "YESIL", None),
]


def main():
    taban = open(KAYNAK, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="marka-uyelik-mutasyon-")
    ayna = os.path.join(tmp, "tools-ayna")
    os.makedirs(ayna)
    for ad in os.listdir(TOOLS):
        if ad != "marka_model_build.py":
            os.symlink(os.path.join(TOOLS, ad), os.path.join(ayna, ad))
    sonuc = []
    try:
        for ad, eski, yeni, beklenen, hedef_iz in MUTANTLAR:
            if taban.count(eski) != 1:
                # Çapa kaymış: "mutant uygulanamadı" YEŞİL sayılmaz, kanıt ÖLÇÜLEMEDİ'dir.
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski), 0))
                continue
            yol = os.path.join(ayna, "marka_model_build.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, KAPI, "--modul", yol],
                               capture_output=True, text=True, cwd=ROOT)
            cikti = r.stdout + r.stderr
            fail_satirlari = re.findall(r"^  FAIL  (.*)$", cikti, re.M)
            fail_sayisi = len(fail_satirlari)
            pass_sayisi = len(re.findall(r"^  PASS ", cikti, re.M))
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d)" % r.returncode
            elif r.returncode == 1 and fail_sayisi == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif pass_sayisi < TABAN_PASS:
                gozlem = "COKME(olculen iddia sayisi dusuk: %d)" % pass_sayisi
            elif r.returncode == 0:
                gozlem = "YESIL"
            elif hedef_iz and not any(hedef_iz in s for s in fail_satirlari):
                # 🔴 HEDEF KOL ATFI: kirmizi var ama BASKA bir eksenden geliyor. Bu mutant
                # "olduruldu" SAYILMAZ — aksi halde kolu hic olcmeyen bir batarya, yan
                # etkiyle kirmizi yakan her mutasyonu kanit diye sayardi.
                gozlem = "KIRMIZI-YANLIS-KOL(%s yok)" % hedef_iz
            else:
                gozlem = "KIRMIZI"
            sonuc.append((ad, beklenen, gozlem, fail_sayisi))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    degismedi = open(KAYNAK, encoding="utf-8").read() == taban
    print("GERCEK marka_model_build.py DEGISMEDI: %s" % degismedi)
    tamam = degismedi
    for ad, beklenen, gozlem, fs in sonuc:
        ok = (beklenen == gozlem)
        tamam = tamam and ok
        print("%-5s %-62s beklenen=%-8s gozlem=%-38s FAIL=%d"
              % ("OK" if ok else "HATA", ad, beklenen, gozlem, fs))
    print("\nBATARYA: %s (%d mutant)" % ("GECTI" if tamam else "KALDI", len(sonuc)))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())
