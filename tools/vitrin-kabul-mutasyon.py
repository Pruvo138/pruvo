#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — vitrin kabul testi 6 (ON BLOK slot duzeni) GERCEK gerilemeyi
yakiyor mu?

  Kapi: jenerator/test/vitrin-kabul.js  (test 6)

NEDEN VAR (5 Agu 2026): test 6 KARARSIZDI — degismemis main'de 25 ardisik kosumun 21'i
yesil, 4'u kirmizi. Iddia "ana sayfanin ilk 4 karti PARAMETRIK" idi ve vitrin sirasi
`VITRIN_SEED = Math.random()` ile her yuklemede degisiyordu; parametrik OLMAYAN tek
Jeneratör karti 4 slottan birine 4/24 = %16,7 ihtimalle dusuyordu. Olcum SABIT TOHUM
SUPRUMUNE cevrildi ve iddia gercek invaryanta (on blok uyeligi) baglandi.

🔴 BU SURUCUNUN ISI: kararsizligi susturan duzeltme cogu zaman GERCEK ALARMI da susturur
([[duzeltme-fail-open-cevirebilir]]). Asagidaki mutantlar "sari seri vitrinin on
slotlarindan dusuyor" gerilemesini FIILEN uygular; test 6 hala KIRMIZI yanmali. Anlatilan
batarya kanit degildir, surucu repoda durur ([[mutasyon-kaniti-yeniden-uretilebilir]]).

KONTROL mutanti iddia edilmeyen eksende YESIL kalmali — yoksa kapi nobetci degil,
"her degisiklige kirmizi yanan" gurultu kaynagidir.

CAPA DISIPLINI: her capa index.html'de TAM BIR KEZ gecmeli. Gecmezse sonuc "YESIL" degil
"CAPA-YOK"tur.

COKME ILE KIRMIZI KARISMAZ: kabul, cikis kodu degil OLCULEN test satiridir. Kosum
"6 vitrin" satirini hic basmadiysa (altyapi hatasi) sonuc COKME'dir.

NASIL: mutant DAIMA KOPYAYA uygulanir. ROOT gecici bir dizine symlink'lenir; index.html
gercek (mutasyonlu) kopya olur. jenerator/test/vitrin-kabul.js de GERCEK KOPYA olmalidir:
node symlink'in realpath'ini cozer ve __dirname gercek agaci gosterirdi -> mutant hic
okunmazdi (sessiz yesil).

Calistir:  python3 tools/vitrin-kabul-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join("jenerator", "test", "vitrin-kabul.js")
# Bunun altina dusen kosum "kirmizi" degil COKME'dir (saglam kosum 9 GECTI basar).
TABAN_GECTI = 5

# (ad, eski, yeni, beklenen)  — hepsi index.html uzerinde
MUTANTLAR = [
    # 🔴 SINIR MUTANTI — BU EKSEN BU KAPININ DEGIL, ve bu bir BEYAN degil OLCUMDUR.
    # "Siralayici cagrisini tamamen kaldir" mutanti test 6'yi KIRMIZI YAKMAZ: ozet.json
    # havuz sirasinda parametrik havuz zaten basta geldigi icin ilk slotlar yine on blok
    # kartlaridir. ONEMLI: bu bir KORELME DEGIL — ESKI (kararsiz) test 6 de ayni mutantla
    # 15/15 YESIL yaniyordu (olculdu 5 Agu 2026), yani eksen hicbir zaman burada degildi.
    # EKSENIN SAHIBI OLCULDU: tools/vitrin-siralama-test.js ayni mutantla rc=2 ile duser
    # (siralayici cagri capasi bulunamaz -> fail-closed). Sahibi kirmizi yakabildigi icin
    # burada YESIL beklemek delik degildir ([[beyan-edilmis-survivor]]).
    ("SINIR V1 SIRALAYICI CAGRISINI KALDIR — eksen sahibi vitrin-siralama-test.js (olculdu)",
     "        cizilecek = vitrinSirala(edgeListe, VITRIN_SEED).slice(0, edgeGoster);",
     "        cizilecek = edgeListe.slice(0, edgeGoster);", "YESIL"),
    ("OLDURUCU V2 ON BLOGU TAMAMEN KALDIR (sari seri vitrinden duser)",
     "  var VITRIN_BLOKLAR = [\n"
     "    {\"kategori\":\"Jeneratör\",\"adet\":4,\"havuz\":0,\"kaynak\":\"parametrik\"},",
     "  var VITRIN_BLOKLAR = [", "KIRMIZI"),
    ("OLDURUCU V3 ON BLOK SLOTUNU 0'A INDIR (iddiayi BOSA dusurme denemesi)",
     "    {\"kategori\":\"Jeneratör\",\"adet\":4,\"havuz\":0,\"kaynak\":\"parametrik\"},",
     "    {\"kategori\":\"Jeneratör\",\"adet\":0,\"havuz\":0,\"kaynak\":\"parametrik\"},",
     "KIRMIZI"),
    ("OLDURUCU V4 ON BLOGU BASKA KATEGORIYE VER (sari seri on sloti kaybeder)",
     "    {\"kategori\":\"Jeneratör\",\"adet\":4,\"havuz\":0,\"kaynak\":\"parametrik\"},",
     "    {\"kategori\":\"Marin\",\"adet\":4,\"havuz\":0,\"kaynak\":\"parametrik\"},",
     "KIRMIZI"),
    # TANI YUZEYI: kalkarsa test tohumu SABITLEYEMEZ; o zaman olcum yine rastgele olur ve
    # "deterministik" iddiasi SESSIZCE yalan olur. Kapi bunu YESIL gecmemeli.
    ("OLDURUCU V5 TANI YUZEYINI DUSUR (seedAl yok -> tohum sabitlenemez)",
     "      sirala: vitrinSirala,\n"
     "      seedAl: function(){ return VITRIN_SEED; },",
     "      sirala: vitrinSirala,", "KIRMIZI"),
    # KONTROL: davranissiz metin degisikligi (iddia edilmeyen eksen).
    ("KONTROL VK1 davranissiz yorum degisikligi (iddia edilmeyen eksen)",
     "  // Sayfa yüklemesi başına TEK seed.",
     "  // Sayfa yüklemesi basina TEK seed.", "YESIL"),
]


def ayna_kur(tmp):
    """ROOT'un aynasi: index.html + jenerator/test/vitrin-kabul.js GERCEK kopya, gerisi
    symlink. Uretilen artefaktlar (ozet.json / taban-fiyatlar.js) aynaya TAZE yazilsin
    diye symlink'lenmez — bayat artefakt uzerinden sessiz yesil olmasin."""
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "jenerator", "test"))
    atla_kok = {".git", "jenerator", "index.html", "ozet.json", "taban-fiyatlar.js"}
    for ad in os.listdir(ROOT):
        if ad in atla_kok:
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    jen = os.path.join(ROOT, "jenerator")
    for ad in os.listdir(jen):
        if ad == "test":
            continue
        os.symlink(os.path.join(jen, ad), os.path.join(kok, "jenerator", ad))
    jent = os.path.join(jen, "test")
    for ad in os.listdir(jent):
        hedef = os.path.join(kok, "jenerator", "test", ad)
        if ad == "vitrin-kabul.js":
            shutil.copy2(os.path.join(jent, ad), hedef)
        else:
            os.symlink(os.path.join(jent, ad), hedef)
    return kok


def main():
    index_yolu = os.path.join(ROOT, "index.html")
    taban = open(index_yolu, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="vitrin-kabul-mutasyon-")
    sonuc = []
    try:
        for ad, eski, yeni, beklenen in MUTANTLAR:
            if taban.count(eski) != 1:
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(os.path.join(tmp, str(len(sonuc))))
            with open(os.path.join(kok, "index.html"), "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run(["node", os.path.join(kok, KAPI)],
                               capture_output=True, text=True, cwd=kok)
            cikti = r.stdout + r.stderr
            gecti = len(re.findall(r"✅ GECTI ", cikti))
            t6 = re.search(r"^ *(✅ GECTI|❌ KALDI) 6 .*$", cikti, re.M)
            if t6 is None:
                gozlem = "COKME(6. test satiri HIC basilmadi: %s)" % (
                    cikti.strip().split("\n")[-1][:80],)
            elif gecti < TABAN_GECTI:
                gozlem = "COKME(olculen GECTI sayisi dusuk: %d)" % gecti
            else:
                gozlem = "KIRMIZI" if "KALDI" in t6.group(1) else "YESIL"
            sonuc.append((ad, beklenen, "%s (test6 GECTI toplam=%d)" % (gozlem, gecti)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: %s :: test 6)" % KAPI)
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-72s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
