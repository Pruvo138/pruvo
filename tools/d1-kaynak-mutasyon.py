#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — d1-sync KATALOG KAYNAGI bayragi (`--head` / `--kaynak`) gercekten
olculuyor mu?

  python3 tools/d1-kaynak-mutasyon.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]). Bu bayragin en buyuk riski SESSIZ ETKISIZLIK:
`--head` verilir, arac "HEAD'den okudum" der ama fiilen CALISMA AGACINDAN okur — yani
operator commit'lenmemis urunleri canliya yazarken yazmadigini sanir. OLDURUCU mutantlar
tam o hali kurar. Ikinci risk TERS YONDE: bayrak VERILMEDIGINDE davranisin kaymasi (5 evin
push kancasi bugunku davranisa bagli) — M3 onu olcer.

🔴 KABUL CIKIS KODU DEGIL, KIRMIZI IDDIA KODLARININ KUMESIDIR ([[hukum-yanlis-birimde]]):
kapinin mutasyonsuz kirmizi kod kumesi TABAN olarak olculur, mutantin onu TAM OLARAK hangi
kodlarla buyuttugune bakilir. Iddia sayisi tabandan saparsa COKME sayilir (coken mutant
"oldurulmus" DEGILDIR). Capa TAM BIR KEZ eslesmeli; `CAPA-YOK` yesil degil OLCULEMEDI'dir.

Mutant DAIMA KOPYAYA uygulanir (ROOT symlink aynasi); gercek agaca / D1'e DOKUNULMAZ.
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = "d1-kaynak-test.py"

# (kod, dosya, eski, yeni, beyan_kod_listesi, aciklama)
MUTANTLAR = [
    ("M1", "d1-sync.py",
     "    if head:\n"
     "        yol, sha = head_katalogu()\n",
     "    if head:\n"
     "        yol, sha = URUNLER, ''\n",
     ["A2a", "A2", "A4", "A5", "A6"],
     "SESSIZ ETKISIZLIK: --head verilince arac yine CALISMA AGACINDAN okur ama 'HEAD' "
     "der -> operator commit'lenmemis urunleri canliya yazarken yazmadigini sanir"),
    ("M2", "d1-sync.py",
     '        if not os.path.exists(yol):\n'
     '            sys.exit("!! --kaynak dosyasi YOK: %s" % yol)\n',
     '        if not os.path.exists(yol):\n'
     '            return None, "calisma agaci (dusuldu)", False\n',
     ["B2"],
     "FAIL-CLOSED KALKAR: yanlis yazilmis --kaynak yolu SESSIZCE calisma agacina duser — "
     "bayragin var olma sebebi yok olur"),
    ("M3", "d1-sync.py",
     '    return None, "calisma agaci (%s)" % URUNLER, False\n',
     '    return URUNLER, "calisma agaci (%s)" % URUNLER, False\n',
     ["C1", "C5"],
     "VARSAYILAN DAVRANIS KAYAR: bayraksiz kosumda da kaynak blogu calisir; 5 evin push "
     "kancasinin bagli oldugu cikti/yol degisir (bayt-ayni sozlesmesi kirilir)"),
    ("M4", "d1-sync.py",
     "    return (sorted(set(a) - set(b)), sorted(set(b) - set(a)),\n"
     "            sorted(i for i in set(a) & set(b) if a[i] != b[i]))\n",
     "    return (sorted(set(a) - set(b)), sorted(set(b) - set(a)), [])\n",
     ["A6"],
     "SAPMA OLCUMU KORELIR: id kumesi ayni ama ICERIGI degismis urun gorunmez olur — "
     "'commit'lenmemis veri yazilmadi' kaniti sessizce eksik olcer"),
    ("M5", "d1-sync.py",
     "    if kaynak and head:\n",
     "    if kaynak and head and False:\n",
     ["B1"],
     "BELIRSIZLIK KAPISI KALKAR: --kaynak ve --head birlikte kabul edilir, hangisinin "
     "kostugu koda gomulu sirayla belirlenir (operator goremez)"),
    ("K1", "d1-sync.py",
     '        return yol, "--kaynak %s" % yol, False\n',
     '        return yol, "--kaynak {}".format(yol), False\n',
     [],
     "KONTROL: davranisi degistirmeyen bicimlendirme — kapi gurultu kaynagi olmamali"),
    ("K2", KAPI,
     "NE OLCULMEDI (beyan):", "NE OLCULMEDI (beyan) :", [],
     "KONTROL: iddia edilmeyen eksen (kapinin beyan metni)"),
]


def ayna_kur(tmp):
    """ROOT'un SALT OKUNUR aynasi. 🔴 `.git` de BAGLANIR (diger surucularin aksine):
    olculen sey `git show HEAD:urunler.json` yolu, yani git'siz bir aynada C6/C7
    MUTANTSIZ da kirmizi yanar ve butun batarya OLCULEMEZ olurdu. Kullanim SALT OKUNUR
    (rev-parse / show); mutant hicbir git nesnesine yazmaz."""
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad == "tools":
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def iddia_kodlari(cikti):
    kirmizi, toplam = set(), 0
    for satir in cikti.splitlines():
        s = satir.strip()
        for bas, kirmizi_mi in (("GECTI ", False), ("KALDI ", True)):
            if s.startswith(bas):
                p = s[len(bas):].split()
                toplam += 1
                if kirmizi_mi and p:
                    kirmizi.add(p[0])
    return kirmizi, toplam


def kos(kok):
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI)],
                       capture_output=True, text=True, cwd=kok)
    return r, (r.stdout or "") + (r.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="d1-kaynak-mutasyon-")
    try:
        kok0 = ayna_kur(os.path.join(tmp, "taban"))
        r0, c0 = kos(kok0)
        t_kirmizi, t_adet = iddia_kodlari(c0)
        print("  TABAN %-20s rc=%d · iddia=%d · KIRMIZI kod=%s"
              % (KAPI, r0.returncode, t_adet, sorted(t_kirmizi) or "-"))
        if t_adet == 0 or t_kirmizi:
            print("\nMUTASYON SONUCU: OLCULEMEDI — mutasyonsuz taban temiz degil "
                  "(harness bozuksa butun 'KIRMIZI' sonuclari YALANCI olur).")
            return 2

        sonuc = []
        for kod, dosya, eski, yeni, beyan, aciklama in MUTANTLAR:
            metin = open(os.path.join(TOOLS, dosya), encoding="utf-8").read()
            if metin.count(eski) != 1:
                sonuc.append((kod, beyan, "CAPA-YOK(%d)" % metin.count(eski), aciklama))
                continue
            kok = ayna_kur(os.path.join(tmp, kod))
            hedef = os.path.join(kok, "tools", dosya)
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            r, cikti = kos(kok)
            kirmizi, adet = iddia_kodlari(cikti)
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode,
                                               cikti.strip().split("\n")[-1][:70])
            elif adet != t_adet:
                gozlem = "COKME(iddia sayisi %d != taban %d)" % (adet, t_adet)
            elif kirmizi == set(beyan):
                gozlem = "UYDU(%s)" % (sorted(kirmizi) or "taban degismedi")
            else:
                gozlem = "SAPTI(gozlenen=%s)" % (sorted(kirmizi) or "-")
            sonuc.append((kod, beyan, gozlem, aciklama))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kabul: cikis kodu DEGIL, KIRMIZI IDDIA KODLARI)")
    kalan = 0
    for kod, beyan, gozlem, aciklama in sonuc:
        tamam = gozlem.startswith("UYDU")
        kalan += 0 if tamam else 1
        print("  %s %-3s beyan=%-24s %s"
              % ("OK   " if tamam else "KALDI", kod, sorted(beyan) or "KONTROL", gozlem))
        print("        %s" % aciklama)
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen kod kumesini vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU beyan ettigi kodlari yakti, her "
          "KONTROL tabani degistirmedi)" % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
