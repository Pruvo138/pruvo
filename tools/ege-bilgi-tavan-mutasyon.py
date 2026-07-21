#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EGE-BILGI TAVAN KAPISI — KIRMIZI-MUTASYON HARNESS (kapinin nobetciligini olcer).

NEDEN VAR: "ic nobetci yesil" tek basina kanit DEGILDIR — fiksturler kapinin mantigini
GERCEKTEN kilitliyor mu, yoksa kapi sessizce olduruldugunde de yesil mi yaniyor? Bu betik
kapi kaynagina TEK SATIRLIK bozmalar (mutant) uygular ve ic nobetcinin KIRMIZI yandigini
olcer. Hayatta kalan (yesil kalan) mutant = fikstur setinde DELIK.

🔴 GUVENLIK KURALI (yasanmis kaza, 21 Tem): mutasyon CANLI dosyaya uygulanip finally ile
geri alinmaz — bir kesinti (timeout/iptal) canliya MUTANT birakir. Burada mutasyon daima
tempfile'daki KOPYAYA uygulanir; canli tools/ege-bilgi-tavan-test.py'ye YAZILMAZ, sadece
okunur. Kopya kendi basina kosar (ic nobetci fiksturleri tempfile'da urettigi icin kopyanin
repo icinde durmasi gerekmez).

Kullanim:
    python3 tools/ege-bilgi-tavan-mutasyon.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "ege-bilgi-tavan-test.py")

# (etiket, aciklama, eski_parca, yeni_parca, "bu mutanti YAKALAMASI beklenen fikstur")
MUTASYONLAR = [
    ("B1", "tavan hukmunu oldur (uzunluk > TAVAN asla dogru olmasin)",
     "    if uzunluk > TAVAN:",
     "    if uzunluk > TAVAN * 100:",
     "K1 / K1c / K1d"),
    ("B2", "UTF-16 olcusunu len(str) yap (astral karakterde sahte-yesil)",
     '    return len(metin.encode("utf-16-le")) // 2',
     "    return len(metin)",
     "K1d (astral)"),
    # NOT: desenler BENZERSIZ olmali (adet != 1 -> harness KIRMIZI yanar, sessizce
    # atlanmaz). Sabit adlari yorumlarda da gectigi icin ATAMA satiri \n ile demirlenir.
    ("B3", "GUVENLIK_MARJI'ni dusur (dar pay uyarisi susar)",
     "\nGUVENLIK_MARJI = 400\n",
     "\nGUVENLIK_MARJI = 50\n",
     "U1"),
    ("B4", "fail-loud dalini sessiz-yesil yap (dosya yoksa exit 0)",
     '                 "tasinmis olabilir; sessiz yesil VERILMEZ.")\n        return 1, r',
     '                 "tasinmis olabilir; sessiz yesil VERILMEZ.")\n        return 0, r',
     "FL1"),
    ("B5", "ilan/sabit nobetcisini oldur (sapma KIRMIZI uretmesin)",
     "        if tekil[0] != TAVAN:",
     "        if tekil[0] != TAVAN and False:",
     "K2 / M13b"),
    ("M10", "kuyruk onizlemesini kod-noktasi dilimine cevir (astralde BOS onizleme)",
     "        kesilen = utf16_kuyruk(metin, TAVAN)",
     "        kesilen = metin[TAVAN:]",
     "K1d/M10"),
    ("M13", "ilan tekillestirmesini kaldir (mukerrer ilan CELISKI uydurur)",
     "    tekil = sorted(bas_kesin)",
     "    tekil = sorted([s for s, _, k in bas_adaylar if k])",
     "M13a"),
    ("M14", "A5 suzgecini oldur (her aday KESIN sayilsin = SART-1 oncesi davranis)",
     '       (a) buyukluk TAVAN bandinda, (b) satirda ilanin OZNESI (dosya / Ege\'ye) var."""\n'
     "    if not (TAVAN // ILAN_BANT <= sayi <= TAVAN * ILAN_BANT):",
     '       (a) buyukluk TAVAN bandinda, (b) satirda ilanin OZNESI (dosya / Ege\'ye) var."""\n'
     "    return True\n"
     "    if not (TAVAN // ILAN_BANT <= sayi <= TAVAN * ILAN_BANT):",
     "A5a-A5e"),
    ("M15", "BAND suzgecini oldur (her buyukluk kabul)",
     "\nILAN_BANT = 3\n",
     "\nILAN_BANT = 100000\n",
     "A5f"),
    ("M16", "OZNE suzgecini oldur (her satir capa sayilsin)",
     '    "\\\\bege\\\\s*[\'’`´]?\\\\s*(?:ye|n[iı]n|den)\\\\b|"',
     '    "|"',
     "A5e"),
]


def kos(yol, bayrak):
    r = subprocess.run([sys.executable, yol] + bayrak, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    with open(KAPI, "r", encoding="utf-8") as f:
        kaynak = f.read()

    dizin = tempfile.mkdtemp(prefix="ege-tavan-mutasyon-")
    print("EGE-BILGI TAVAN KAPISI — KIRMIZI-MUTASYON OLCUMU")
    print("  Kapi (SALT OKUNUR) : %s" % KAPI)
    print("  Mutant kopyalar    : %s" % dizin)
    print("-" * 78)

    hayatta = []
    uygulanamayan = []
    try:
        # TABAN: mutasyonsuz kopya YESIL mi (harness'in kendi dogrulugu)
        taban = os.path.join(dizin, "taban.py")
        with open(taban, "w", encoding="utf-8") as f:
            f.write(kaynak)
        kod, cikti = kos(taban, ["--ic-nobetci"])
        print("  TABAN (mutasyonsuz kopya) --ic-nobetci -> exit %d  %s"
              % (kod, "✅ YESIL" if kod == 0 else "❌ (harness bozuk!)"))
        if kod != 0:
            print(cikti[-2000:])
            return 1
        print("-" * 78)

        for etiket, aciklama, eski, yeni, bekleyen in MUTASYONLAR:
            adet = kaynak.count(eski)
            if adet != 1:
                uygulanamayan.append((etiket, adet))
                print("  ⚠️  %-4s UYGULANAMADI (desen %d kez gecti) — %s"
                      % (etiket, adet, aciklama))
                continue
            yol = os.path.join(dizin, "mutant-%s.py" % etiket)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            kod, cikti = kos(yol, ["--ic-nobetci"])
            if kod == 0:
                hayatta.append(etiket)
                print("  ❌ %-4s HAYATTA (ic nobetci YESIL yandi) — %s" % (etiket, aciklama))
            else:
                yakalayan = [s.strip()[:70] for s in cikti.splitlines()
                             if s.strip().startswith("❌")][:3]
                print("  ✅ %-4s OLDU (exit %d) — %s" % (etiket, kod, aciklama))
                print("        beklenen nobetci: %s" % bekleyen)
                for y in yakalayan:
                    print("        yakalayan: %s" % y)
    finally:
        shutil.rmtree(dizin, ignore_errors=True)

    print("-" * 78)
    print("  Mutasyon sayisi : %d" % len(MUTASYONLAR))
    print("  Hayatta kalan   : %d %s" % (len(hayatta), hayatta if hayatta else ""))
    print("  Uygulanamayan   : %d %s" % (len(uygulanamayan),
                                         uygulanamayan if uygulanamayan else ""))
    if hayatta or uygulanamayan:
        print("SONUC: KIRMIZI ❌ — fikstur setinde delik var ya da mutasyon deseni bayat "
              "(kapi kaynagi degistiyse desenleri guncelle).")
        return 1
    print("SONUC: YESIL ✅ — her mutant ic nobetci tarafindan yakalandi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
