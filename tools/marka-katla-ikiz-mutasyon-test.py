#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON KANITI — tools/marka-katla-ikiz-kapisi.py GERCEKTEN olcuyor mu?

  kosum:  python3 tools/marka-katla-ikiz-mutasyon-test.py   (0 = gecti, 1 = delik var)

"Kapi yazdim, yesil yaniyor" TEK BASINA kanit DEGILDIR: yesil, kapinin neyi olctugune
baglidir ([[test-hatali-davranisi-kutsar]]). Bu surucu portu (tools/marka_katla.py) TEK
TEK bozar ve HER bozmanin kapiyi KIRMIZI yaktigini OLCER. Ayrica anlatilan batarya kanit
degildir ([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu REPODA durur, sayiyi kendi
basar.

Tuzaklar kapatildi:
  * Mutasyon DAIMA GECICI bir kopyaya uygulanir; calisma agacina YAZILMAZ.
  * Mutant GERCEKTEN uygulandi mi olculur: capa metni kaynakta TAM 1 kez gecmeli.
    Gecmezse "KURULAMADI" — bu da KIRMIZI'dir ve "yakalandi" ile KARISTIRILMAZ.
  * Cokme kirmiziyla karismasin ([[mutasyon-kaniti-yeniden-uretilebilir]]): kapinin
    cikis kodu 1 ise "iddia dustu" (gercek yakalama), 3 ise "OLCULEMEDI" (altyapi
    olumu) — ikincisi yakalama SAYILMAZ, ayri raporlanir. Ayrica kapinin kendi
    "SONUC:" satiri ciktida ARANIR.
  * Bytecode onbellegi ([[mutasyon-bytecode-onbellegi]]): her mutant TAZE dizinde +
    PYTHONDONTWRITEBYTECODE=1.
  * M00 KONTROL: mutasyonsuz kopya YESIL yanmali — yanmazsa harness bozuktur ve TUM
    mutant sonuclari YALANCI olurdu.
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
PORT = os.path.join(TOOLS, "marka_katla.py")
KABUL = os.path.join(TOOLS, "marka-katla-ikiz-kapisi.py")

# (ad, ne olcuyor, aranan_metin, yerine)
MUTANTLAR = [
    ("M1 NFD aksan kurali ELLE listeye geri doner",
     "asil kusurun KENDISI: caron/tilde/halka/akut/macron/breve tasiyan her yazim "
     "site markaNorm'undan sessizce ayrisir",
     "    n = _aksan_sil(n)\n",
     '    n = n.replace("é", "e").replace("è", "e").replace("ë", "e").replace("ä", "a")\n'),

    ("M2 MARKA_ALIAS UYGULAMASI dusuyor",
     "tablo TURETILSE bile markaKatla icinde uygulanmazsa: 'Vauxhall' Opel kalemine "
     "inmez, site ile ayri kanonik ad uretilir",
     "    sonuc = _katla_alias_oncesi(m)\n"
     "    if sonuc in MARKA_ALIAS:\n"
     "        sonuc = MARKA_ALIAS[sonuc]\n"
     "    return sonuc\n",
     "    sonuc = _katla_alias_oncesi(m)\n"
     "    return sonuc\n"),

    ("M3 MARKA_ALIAS TURETIMI kesilir (BAYAT elle sozluk)",
     "index.html'den PARSE etmek yerine elle sozluk yazilirsa: bugun bos, yarin bayat — "
     "kapatmaya calistigimiz sinifin TA KENDISI",
     "MARKA_ALIAS = _parse_alias()\n",
     "MARKA_ALIAS = {}\n"),

    ("M4 KONTROL: onek kurali ALT-DIZE'ye gevsetilir",
     "YENI kusur DEGIL — kapinin aksan/alias eksenine KILITLENMEDIGINI, katlama "
     "kuralinin genelinde de duyarli oldugunu gosterir",
     '        if n.startswith(nm + " ") or n.startswith(nm + "-"):\n',
     "        if nm in n:\n"),
]


def ayna_kur(kaynak_metin):
    """Gecici kok: tools/marka_katla.py (mutasyonlu GERCEK dosya) + index.html ve
    urunler.json symlink'leri. marka_katla.py index.html'i KENDI konumundan turetir,
    o yuzden ikisi de baglanmali."""
    kok = tempfile.mkdtemp(prefix="marka-katla-mut-")
    os.makedirs(os.path.join(kok, "tools"))
    os.symlink(os.path.join(ROOT, "index.html"), os.path.join(kok, "index.html"))
    os.symlink(os.path.join(ROOT, "urunler.json"), os.path.join(kok, "urunler.json"))
    hedef = os.path.join(kok, "tools", "marka_katla.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak_metin)
    return kok, hedef


def kapiyi_kos(port_yolu):
    env = dict(os.environ)
    env["PRUVO_MARKA_KATLA"] = port_yolu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, KABUL], capture_output=True, text=True,
                          env=env, timeout=600)


src = open(PORT, encoding="utf-8").read()
satirlar = []
kacan = 0

# ── M00 KONTROL: mutasyonsuz kopya YESIL yanmali ─────────────────────────────
_kok, _hedef = ayna_kur(src)
_r = kapiyi_kos(_hedef)
shutil.rmtree(_kok, ignore_errors=True)
if _r.returncode == 0 and "SONUC:" in _r.stdout:
    satirlar.append("kontrol OK  M00 mutasyonsuz kopya YESIL (harness saglam)")
else:
    kacan += 1
    satirlar.append("HARNESS BOZUK  M00 mutasyonsuz kopya KIRMIZI (cikis %d) — asagidaki "
                    "tum mutant sonuclari YALANCI olurdu" % _r.returncode)
    satirlar.append("               " + (_r.stdout[-1500:] or _r.stderr[-1500:]).replace(
        "\n", "\n               "))

# ── Mutantlar ────────────────────────────────────────────────────────────────
for ad, ne, eski, yeni in MUTANTLAR:
    sayi = src.count(eski)
    if sayi != 1:
        kacan += 1
        satirlar.append("KURULAMADI  %s  — capa metni kaynakta %d kez geciyor (1 olmali); "
                        "mutasyon HIC uygulanmadi" % (ad, sayi))
        continue
    mutant = src.replace(eski, yeni, 1)
    if mutant == src:
        kacan += 1
        satirlar.append("KURULAMADI  %s  — mutasyon metni DEGISTIRMEDI" % ad)
        continue
    kok, hedef = ayna_kur(mutant)
    try:
        r = kapiyi_kos(hedef)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    if r.returncode == 1 and "SONUC:" in r.stdout:
        durum = "yakalandi  "
    elif r.returncode == 3:
        kacan += 1
        durum = "ALTYAPI    "   # OLCULEMEDI: yakalama SAYILMAZ (cokme kirmiziyla karisir)
    elif r.returncode == 0:
        kacan += 1
        durum = "KACTI      "
    else:
        kacan += 1
        durum = "COKTU      "
    satirlar.append("%s%s  (cikis %d)  — %s" % (durum, ad, r.returncode, ne))
    if durum != "yakalandi  ":
        satirlar.append("            " + (r.stdout[-1200:] or r.stderr[-1200:]).replace(
            "\n", "\n            "))

print("\n".join(satirlar))
print("\nOZET: %d mutant · kacan %d" % (len(MUTANTLAR), kacan))
print("KIRMIZI — kabul kapisinda delik var" if kacan else "GECTI — her mutant kirmizi yandi")
sys.exit(1 if kacan else 0)
