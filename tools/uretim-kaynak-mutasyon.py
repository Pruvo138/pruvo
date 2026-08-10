#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URETIM DOSYASI DRIVE BAGLANTISI NOBETCISININ MUTASYON HARNESS'I.

  python3 tools/uretim-kaynak-mutasyon.py

NE ISE YARAR: `node shop/test/uretim-kaynak.mjs` 42 iddiayla YESIL yaniyor. "Yesil"
tek basina hicbir sey kanitlamaz — kanit, davranisi BOZUNCA iddianin KIRMIZI yanmasi
(mutant) VE ilgisiz bir degisiklikte YESIL kalmasidir (kontrol mutanti). Bu surucu
olmasa, ileride iddialarin icini bosaltan bir degisiklik nobetciyi SESSIZCE oldururdu
ve kimse fark etmezdi (depo konvansiyonu: tools/yonet-cerez-mutasyon.py,
tools/wa-yetki-mutasyon.py — SURUCU REPODA DURUR).

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Calisma agacindaki shop/src/yonet.js'i bozup
`finally` ile geri alma deseni bu evde YASAK: tek bir kesinti (Ctrl-C, kota bitmesi)
agacta MUTANT birakir — yani deploy edilebilir bir bozukluk. Burada mutant gecici bir
dizine yazilir, test PRUVO_YONET_KAYNAK ile oraya bakar; kaynak dosyanin sha256'si basta
alinir ve HER kosumdan sonra + en sonda yeniden dogrulanir.

KABUL (cikis kodu degil, OLCULEN SAYI): her mutant icin BEKLENEN ve GERCEKLESEN durum
birebir esitse rc=0. Ayrica:
  - rc=1 (KIRMIZI) ile rc=3 (OLCULEMEDI: test capalari bulunamadi) AYRI tutulur —
    ikisi de "sifir disi"dir ama biri kanit, digeri kor nokta.
  - En az bir NOTR (kontrol) mutant YESIL kalmali; hepsi kirmizi yanan bir batarya
    "her degisiklige kirmizi" demektir, iddia degil.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "shop", "src", "yonet.js")
TEST = os.path.join(KOK, "shop", "test", "uretim-kaynak.mjs")

KIRMIZI = "KIRMIZI"
YESIL = "YESIL"
OLCULEMEDI = "OLCULEMEDI"

# (ad, beklenen, aciklama, [(eski, yeni), ...])
MUTANTLAR = [
    ("M1 SESSIZ BOSLUK (SPEC KONTROL MUTANTI)", KIRMIZI,
     "kaynak yokken panel HIC bir sey yazmaz -> 'dosya yok' ile 'olculemedi' ayni "
     "bos hucreye duser; Okan bosluga bakip 'kaynak yok' sanir",
     [("""  return '<span class="yok">kaynak yok — üretim notunda Drive bağlantısı (fileId) geçmiyor</span>';""",
       """  return '';""")]),

    ("M2 ARSIV FAIL-LOUD KOLU SILINDI", KIRMIZI,
     "fileId'i olmayan 'ARSIVDE, BASILMAZ' isareti hic donmez -> panel arsiv surumu "
     "YOKMUS gibi gorunur; yanlis dosyanin basilmasi = pahali uretim hatasi",
     [("""    if (idler.some((x) => x.konum >= bas && x.konum < son)) { continue; }""",
       """    if (true) { continue; }""")]),

    ("M3 SESSIZ 'kanonik' VARSAYIMI", KIRMIZI,
     "sinif isareti bulunamayan dosya 'belirsiz' yerine KANONIK sayilir -> panel "
     "olcemedigi seyi 'basilacak dosya' diye beyan eder",
     [("""    return secili || SINIF_BELIRSIZ;""",
       """    return secili || SINIF_ISARET[2];""")]),

    ("M4 target=_blank / rel=noopener DUSTU", KIRMIZI,
     "Okan'in acik istegi: baglantilar yeni sekmede acilsin (panel oturumu kaybolmasin)",
     [("""'<a class="indir" href="'+esc(x.url)+'" target="_blank" rel="noopener">'+ad+'</a></div>';""",
       """'<a class="indir" href="'+esc(x.url)+'">'+ad+'</a></div>';""")]),

    ("M5 KACIS (esc) KALKTI", KIRMIZI,
     "sinif/etiket/dosya/url ham basilir -> yetkili panelde HTML enjeksiyonu",
     [("""  var sinif=esc(x.sinif||"belirsiz");""", """  var sinif=(x.sinif||"belirsiz");"""),
      ("""  var ad=x.dosya?esc(x.dosya):"(dosya adı notta yok)";""",
       """  var ad=x.dosya?(x.dosya):"(dosya adı notta yok)";""")]),

    ("M6 fileId DILBILGISI GEVSEDI", KIRMIZI,
     "id yerine bosluksuz her sey kabul edilir -> tirnak/`javascript:` tasiyan bir dizi "
     "href'e girer (regex ayni zamanda GUVENLIK kapisiydi)",
     [("""([A-Za-z0-9_-]{16,200})/gi;""", """([^\\s]{4,200})/gi;""")]),

    ("M7 SINIF = EN YAKIN degil ILK isaret", KIRMIZI,
     "yedek dosya da 'kanonik' etiketi alir -> yanlis dosya basilir",
     [("""    for (const i of isaretler) { if (i.konum <= konum) { secili = i; } else { break; } }""",
       """    for (const i of isaretler) { if (i.konum <= konum && !secili) { secili = i; } }""")]),

    ("M8 fileId GOVDESI KAPISI KALKTI", KIRMIZI,
     "rastgele id icinde gecen 'yedek'/'kanonik' dizisi sinif isareti sayilir -> "
     "dosya kendi id'sinin harflerine gore siniflanir",
     [("""      if (!idIcinde(m.index)) {""", """      if (true) {""")]),

    ("M9 NOTR: yalnizca yorum eklendi (KONTROL)", YESIL,
     "davranis degismiyor; batarya 'her degisiklige kirmizi' DEGIL",
     [("""export function driveKaynaklari(metin) {""",
       """export function driveKaynaklari(metin) {\n  // notr mutant: davranis degismez\n""")]),

    ("M10 NOTR: CSS rengi degisti (KONTROL)", YESIL,
     "gorsel detay; iddialarin hicbiri renk olcmuyor",
     [(""".sinif.kanonik{color:#166534}""", """.sinif.kanonik{color:#15803d}""")]),
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
    son = satirlar[-1] if satirlar else (p.stderr or "").strip().splitlines()[-1:] or ""
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

    tmp = tempfile.mkdtemp(prefix="pruvo-uretim-kaynak-mut-")
    sonuclar = []

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
            # 🔴 SESSIZ ATLAMA YOK: capa tutmadiysa mutant UYGULANMADI demektir; onu
            # "kirmizi yanmadi" diye raporlamak yanlis-yesil olurdu.
            sonuclar.append((ad, beklenen, OLCULEMEDI,
                             "capa tutmadi: " + " | ".join(uygulanmayan)))
            print("  %-42s beklenen=%-10s gercek=%s (capa tutmadi)" % (ad, beklenen, OLCULEMEDI))
            continue
        if metin == temiz:
            sonuclar.append((ad, beklenen, OLCULEMEDI, "mutant metni kaynakla AYNI"))
            continue
        yol = os.path.join(tmp, "m%02d-yonet.js" % i)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
        durum, son = kosu(yol)
        sonuclar.append((ad, beklenen, durum, son))
        print("  %-42s beklenen=%-10s gercek=%-10s | %s" % (ad, beklenen, durum, son))
        if sha(KAYNAK) != basta:
            print("🔴 KAYNAK DOSYA DEGISTI — mutasyon calisma agacina sizdi. DUR.")
            return 3

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
