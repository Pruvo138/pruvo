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
    # (ad, eski, yeni, beklenen)
    ("OLDURUCU M1 sayfa evrenini kuratorluge geri dondur (cip evreni kopar)",
     "veri = gruplandir(products, evren, ek_markalar)",
     "veri = gruplandir(products, evren)", "KIRMIZI"),
    # 🔴 ÇAPALAR 3 Ağu'da TAŞINDI (üreteç yeniden düzenlendi: model üyeliği pozisyondan
    # kurtarıldı, birincil marka `birincil_marka()`ya çıktı). Mutantın KENDİSİ aynı ihlali
    # anlatır; yalnız tutunduğu satır güncellendi — "çapa yok" gözlemi kanıt DEĞİLDİR.
    ("OLDURUCU M2 uyelik yalniz marka[0]'dan dogsun (ikincil marka uyeligi olur)",
     "    uyeler = []\n    for x in marka_dizisi:",
     "    uyeler = []\n    for x in marka_dizisi[:1]:", "KIRMIZI"),
    ("OLDURUCU M3 cip haritasi IKINCIL markaya kaysin",
     "    return ham0 if (evren.taninmis_mi(ham0) or ham0 in ek_markalar) else uyeler[0]",
     "    return uyeler[-1]", "KIRMIZI"),
    ("OLDURUCU M4 model uyeligini yeniden marka[1]'e sabitle (olculen eski sessiz hata)",
     "    for x in marka_dizisi:\n        t = (x or \"\").strip()",
     "    for x in marka_dizisi[1:2]:\n        t = (x or \"\").strip()", "KIRMIZI"),
    ("KONTROL K1 iddia edilmeyen eksen (meta description metni)",
     '<meta name="description" content="{desc}">',
     '<meta name="description" content="{desc} ">', "YESIL"),
    ("KONTROL K2 davranisi degistirmeyen yazim (uyeler = [] -> list())",
     "    uyeler = []\n    for x in marka_dizisi:",
     "    uyeler = list()\n    for x in marka_dizisi:", "YESIL"),
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
        for ad, eski, yeni, beklenen in MUTANTLAR:
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
            fail_sayisi = len(re.findall(r"^  FAIL ", cikti, re.M))
            pass_sayisi = len(re.findall(r"^  PASS ", cikti, re.M))
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d)" % r.returncode
            elif r.returncode == 1 and fail_sayisi == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif pass_sayisi < TABAN_PASS:
                gozlem = "COKME(olculen iddia sayisi dusuk: %d)" % pass_sayisi
            else:
                gozlem = "KIRMIZI" if r.returncode == 1 else "YESIL"
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
