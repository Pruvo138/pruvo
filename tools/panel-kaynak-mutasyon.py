#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PANEL URETICI-KAYNAK + ACILIR/KAPANIR KART NOBETCISININ MUTASYON HARNESS'I.

  python3 tools/panel-kaynak-mutasyon.py

NE ISE YARAR: `node shop/test/panel-kaynak.mjs` 40 iddiayla YESIL yaniyor. "Yesil" tek
basina hicbir sey kanitlamaz — kanit, davranisi BOZUNCA iddianin KIRMIZI yanmasi VE
ilgisiz bir degisiklikte YESIL kalmasidir ([[mutasyon-kaniti-yeniden-uretilebilir]]:
anlatilan batarya kanit DEGILDIR, repoda KOSAN surucu kanittir). Depo konvansiyonu:
tools/uretim-kaynak-mutasyon.py · tools/yonet-cerez-mutasyon.py.

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Calisma agacindaki shop/src/yonet.js'i bozup
`finally` ile geri alma deseni bu evde YASAK: tek bir kesinti agacta MUTANT birakir —
yani deploy edilebilir bir bozukluk. Mutant gecici dizine yazilir, test PRUVO_YONET_KAYNAK
ile oraya bakar; kaynak dosyanin sha256'si basta alinir ve HER kosumdan sonra dogrulanir.

KABUL (cikis kodu degil, OLCULEN SAYI): her mutant icin BEKLENEN ve GERCEKLESEN durum
birebir esit olmali. rc=1 (KIRMIZI) ile rc=3 (OLCULEMEDI: capa bulunamadi) AYRI tutulur —
ikisi de sifir disidir ama biri kanit, digeri kor nokta. En az bir NOTR mutant YESIL
kalmali; hepsi kirmizi yanan batarya "her degisiklige kirmizi" demektir, iddia degil.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "shop", "src", "yonet.js")
TEST = os.path.join(KOK, "shop", "test", "panel-kaynak.mjs")

KIRMIZI = "KIRMIZI"
YESIL = "YESIL"
OLCULEMEDI = "OLCULEMEDI"

# (ad, beklenen, aciklama, [(eski, yeni), ...])
MUTANTLAR = [
    ("N1 SESSIZ BOSLUK (SPEC OLDURUCUSU)", KIRMIZI,
     "kaynak kaydi yokken panel HIC bir sey yazmaz -> 'kaynak YOK' ile 'OLCULEMEDI' "
     "ayni bos hucreye duser; Okan bosluga bakip 'kaynagi yok' sanir",
     [("""  return '<span class="yok">kaynak kaydı yok</span>';""",
       """  return '';""")]),

    ("N2 <details> YERINE DUZ <div> (SPEC OLDURUCUSU)", KIRMIZI,
     "kart acilir/kapanir olmaktan cikar; Okan'in acik istegi (siparisler kapanip "
     "acilsin) sessizce kaybolur ve musteri verisi hep ekranda durur",
     [("""'<details class="kart"'+acik+' ontoggle="kartAc(this)">'+ozet+""",
       """'<div class="kart">'+ozet+"""),
      ("""  '</details>';""", """  '</div>';""")]),

    ("N3 KALEM NESNESINE `tasarimci` EKLENDI (SPEC OLDURUCUSU)", KIRMIZI,
     "G3 ihlali: link disinda ticari/gizli alan da panele tasinir -> sizma yuzeyi "
     "gereksiz buyur (tedarikci/tasarimci adi hicbir yuzeyde olmaz)",
     [("""        kaynak_link: kaynakLinkSuz(kaynakMap.get(k.id)),""",
       """        kaynak_link: kaynakLinkSuz(kaynakMap.get(k.id)),
        tasarimci: (k.tasarimci || ""),""")]),

    ("N4 SUZGEC GEVSEDI (her dize gecer)", KIRMIZI,
     "`javascript:`/`data:` tasiyan bozuk deger href'e girer -> yetkili panelde "
     "tiklanabilir kod; suzgec ayni zamanda GUVENLIK kapisiydi",
     [("""  return (typeof deger === "string" && /^https:\\/\\//i.test(deger)) ? deger : "";""",
       """  return (typeof deger === "string") ? deger : "";""")]),

    ("N5 KACIS (esc) KALKTI — kaynak linki", KIRMIZI,
     "link ham basilir -> tirnak tasiyan bir deger href attributunu kirar (XSS)",
     [(""" return '<a class="indir" href="'+esc(u)+'" title="'+esc(u)+""",
       """ return '<a class="indir" href="'+(u)+'" title="'+(u)+""")]),

    ("N6 target=_blank / rel=noopener DUSTU", KIRMIZI,
     "kaynak linki ayni sekmede acilir -> panel oturumu ekrandan kaybolur",
     [("""  '" target="_blank" rel="noopener">kaynak sayfası</a>';""",
       """  '">kaynak sayfası</a>';""")]),

    ("N7 TUM KARTLAR ACIK DOGAR", KIRMIZI,
     "'varsayilan kapali, yalniz odendi acik' kurali olur -> omuz-ustu gizliligi ve "
     "lazy yukleme kazanci ikisi birden kaybolur",
     [(""" var acik=s.durum==="odendi"?" open":"";""", """ var acik=" open";""")]),

    ("N8 MUSTERI ADI KAPALI BASLIGA SIZDI", KIRMIZI,
     "kart kapaliyken bile musteri adi ekranda durur -> omuz-ustu gizliligi yok olur",
     [("""  '<span class="kucuk">'+tl(s.tutar_kurus)+' · '+(s.kalemler||[]).length+' kalem</span>'+""",
       """  '<span class="kucuk">'+esc(s.musteri.ad)+' · '+tl(s.tutar_kurus)+' · '+(s.kalemler||[]).length+' kalem</span>'+""")]),

    ("N9 D1 SELECT'I GENISLEDI", KIRMIZI,
     "ayri tablodan link disinda alan da cekilir -> G3 (yalniz link tasinir) delinir",
     [('''        "SELECT id, link FROM urun_kaynak WHERE id IN (" + yertut + ")").bind(...idler).all(),''',
       '''        "SELECT id, link, tasarimci FROM urun_kaynak WHERE id IN (" + yertut + ")").bind(...idler).all(),''')]),

    ("N10 LAZY DAMGASI KALKTI (her acilista yeniden ceker)", KIRMIZI,
     "kart her acilip kapandiginda R2/D1'e yeniden gidilir -> spec'in lazy sarti olur",
     [(""" if(!el||!el.open||el.dataset.yuklendi)return;
 el.dataset.yuklendi="1";""",
       """ if(!el||!el.open)return;""")]),

    ("N13 SABLONA BACKTICK SIZDI", KIRMIZI,
     "SAYFA_HTML sablon dizesine tek bir backtick girer -> sablon ERKEN KAPANIR ve "
     "yonet.js modulu IMPORT EDILEMEZ (13 Agu'da bu isin ilk kosumunda GERCEKLESTI; "
     "dilimleme yontemi gormedigi icin kirmizi yalnizca kardes testlerde yanmisti)",
     [(""" // open ile DOGAN kartlarda (odendi) tarayici 'toggle' olayini ATESLEMEZ —""",
       """ // `open` ile DOGAN kartlarda (odendi) tarayici 'toggle' olayini ATESLEMEZ —""")]),

    ("N11 NOTR: yalnizca yorum eklendi (KONTROL)", YESIL,
     "davranis degismiyor; batarya 'her degisiklige kirmizi' DEGIL",
     [("""export function kaynakLinkSuz(deger) {""",
       """export function kaynakLinkSuz(deger) {\n  // notr mutant: davranis degismez\n""")]),

    ("N12 NOTR: summary ok isareti CSS'i degisti (KONTROL)", YESIL,
     "gorsel detay; iddialarin hicbiri ok karakterini olcmuyor",
     [("""summary.ust::after{content:"▸";color:#6b7280;font-size:14px}""",
       """summary.ust::after{content:"+";color:#6b7280;font-size:14px}""")]),
]


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kosu(kaynak_yolu):
    """Testi verilen kaynak dosyasina karsi kosar. Doner: (durum, son_satir)."""
    ortam = dict(os.environ)
    ortam["PRUVO_YONET_KAYNAK"] = kaynak_yolu
    p = subprocess.run([shutil.which("node") or "node", TEST],
                       capture_output=True, text=True, env=ortam, cwd=KOK)
    satirlar = [s for s in (p.stdout or "").strip().splitlines() if s.strip()]
    son = satirlar[-1] if satirlar else ((p.stderr or "").strip().splitlines()[-1:] or [""])[0]
    if p.returncode == 0:
        return YESIL, son
    if p.returncode == 3:
        return OLCULEMEDI, son
    if p.returncode == 1:
        return KIRMIZI, son
    return OLCULEMEDI, "beklenmeyen cikis kodu %d | %s" % (p.returncode, son)


def main():
    if not os.path.exists(KAYNAK) or not os.path.exists(TEST):
        print("KAYNAK ya da TEST yok — OLCULEMEDI")
        return 3
    basta = sha(KAYNAK)
    with open(KAYNAK, encoding="utf-8") as f:
        temiz = f.read()

    tmp = tempfile.mkdtemp(prefix="pruvo-panel-kaynak-mut-")
    sonuclar = []
    try:
        # 0) TABAN: mutasyonsuz aynada test YESIL olmali (yoksa batarya anlamsiz).
        taban_yol = os.path.join(tmp, "taban-yonet.js")
        with open(taban_yol, "w", encoding="utf-8") as f:
            f.write(temiz)
        taban_durum, taban_son = kosu(taban_yol)
        print("TABAN (mutasyonsuz ayna): %s | %s" % (taban_durum, taban_son))
        if taban_durum != YESIL:
            print("🔴 Taban yesil degil — mutant sonuclari yorumlanamaz. DUR.")
            return 3

        for i, (ad, beklenen, neden, yamalar) in enumerate(MUTANTLAR):
            metin = temiz
            uygulanmayan = []
            for eski, yeni in yamalar:
                if eski not in metin:
                    uygulanmayan.append(eski[:60])
                    continue
                metin = metin.replace(eski, yeni, 1)
            if uygulanmayan:
                # 🔴 SESSIZ ATLAMA YOK: capa tutmadiysa mutant UYGULANMADI demektir;
                # onu "kirmizi yanmadi" diye raporlamak yanlis-yesil olurdu.
                sonuclar.append((ad, beklenen, OLCULEMEDI,
                                 "capa tutmadi: " + " | ".join(uygulanmayan)))
                print("  %-46s beklenen=%-10s gercek=%s (capa tutmadi)"
                      % (ad, beklenen, OLCULEMEDI))
                continue
            if metin == temiz:
                sonuclar.append((ad, beklenen, OLCULEMEDI, "mutant metni kaynakla AYNI"))
                continue
            yol = os.path.join(tmp, "n%02d-yonet.js" % i)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin)
            durum, son = kosu(yol)
            sonuclar.append((ad, beklenen, durum, son))
            print("  %-46s beklenen=%-10s gercek=%-10s | %s" % (ad, beklenen, durum, son))
            if sha(KAYNAK) != basta:
                print("🔴 KAYNAK DOSYA DEGISTI — mutasyon calisma agacina sizdi. DUR.")
                return 3
    finally:
        # DISKTE IZ BIRAKMA: hata alsak da gecici ayna dizini SILINIR.
        shutil.rmtree(tmp, ignore_errors=True)

    if sha(KAYNAK) != basta:
        print("🔴 KAYNAK DOSYA DEGISTI (kapanista) — DUR.")
        return 3

    uyusmaz = [s for s in sonuclar if s[1] != s[2]]
    kirmizi_sayisi = sum(1 for s in sonuclar if s[2] == KIRMIZI)
    yesil_sayisi = sum(1 for s in sonuclar if s[2] == YESIL)
    print("")
    print("MUTANT: %d | beklendigi gibi: %d | uyusmayan: %d | kirmizi: %d | notr-yesil: %d"
          % (len(sonuclar), len(sonuclar) - len(uyusmaz), len(uyusmaz),
             kirmizi_sayisi, yesil_sayisi))
    print("kaynak sha256 degismedi: %s" % (sha(KAYNAK) == basta))
    for ad, bek, ger, son in uyusmaz:
        print("  🔴 %s: beklenen %s, gercek %s | %s" % (ad, bek, ger, son))
    if yesil_sayisi == 0:
        print("  🔴 Hicbir notr mutant yesil kalmadi — batarya 'her degisiklige kirmizi' olabilir.")
        return 1
    return 0 if not uyusmaz else 1


if __name__ == "__main__":
    sys.exit(main())
