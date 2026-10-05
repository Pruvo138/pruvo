#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — parite fiksturu KENDI OLCUM ORTAMINI dogru kuruyor mu?

  Kapi: tools/parite-fikstur-test.js  (senaryo S8)

  6 Eki 2026: Ege (emekli bot) senaryolari S17-S21/S26-S28/SM1-SM3 fiksturden
  kaldirildi; SM1'e capali mutantlar S8'e yeniden capalandi (S8'i oldurmeyen
  mutant Ege-yalniz sayilip kaldirildi). Senaryo kumesi artik ORTAMA BAGLI DEGIL.

NEDEN VAR (6 Eyl 2026, OLCULDU — iki senaryo 3 turdur kirmiziydi ve KOKU AYNIYDI):
`tools/parite-marka-sinifi.js` katalog yolunu (`PARITE_URUNLER` ya da agacin
`urunler.json`'u) MODUL YUKLENIRKEN cozuyordu. Fikstur harness'i tek surecte SENTETIK
kataloglar kurup sahte `/ara` ucunu bu govdeyle besler; ama harness'in KENDI surecinde
`PARITE_URUNLER` YOKTU -> sentetik katalogun `marka_kanon` haritasi 20 bin urunluk
URETIM katalogundan cozuluyordu. Iki ayri arizayi ayni kok dogurdu:

  * SM1 (marka ekseni): olculdu — sentetik katalogtan `capa-3-3 -> ["Volvo","Opel"]`
    (baslıktaki TAM JETONDAN turer), URETIM katalogundan `capa-3-3 -> null` (29.298
    kayit, sentetik id'lerin HICBIRI orada yok). Sahte ucun `uyeMi`si sessizce FALSE,
    cocugunki TRUE -> `?q=Opel&marka=Opel` ucta 3 / yerelde 4 -> "gerileme" RAPOR EDILDI.
    Kusur URETIMDE DEGIL, OLCUM ORTAMININ SEKLINDEYDI.
  * S8 (uc susuyor): `markaKanonHaritasiAl` `marka-kanon-uret.py`yi `execFileSync` ile
    kosar (SENKRON -> node olay dongusu BLOKE). Uretim katalogunda olculdu **~22 sn** ve
    bu bedel ISTEK ISLEYICISININ ICINDE odeniyordu: `288ms ISTEK -> 21860ms YANIT`, ilk
    partideki 8 eszamanli istegin hepsi arkasinda kuyrukta. Zaman asimi esigi 22 sn'nin
    ALTINDA olan her senaryo (S8: 400 ms) TEK SORGU siniflandirilmadan oluyordu:
    `ACIKLANAMAYAN: 0` + `0/220 sorgu` -> cikis 3. Bu yuzden `susSonraAra` esigini
    yukseltmek ya da zaman asimini 15.000 ms yapmak ISE YARAMADI — olculen sey ucun
    ENJEKTE EDILEN sessizligi degil, fiksturun KENDI soguk baslangicidir.

ONARIM: yol CAGRI ANINDA cozulur (`urunlerYoluCoz`) ve fikstur her senaryoda
`PARITE_URUNLER`i o senaryonun `canli` katalogunu tutan gecici dosyaya isaret ettirir.
Tek satirlik gorunen bu degisiklik IKI KOLU birden tasir; asagidaki mutantlar bunu
KOL KOL kanitlar (M1-M4 -> SM1 kolu, M5 -> S8 zamanlama kolu).

🔴 KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali — yoksa kapi "her
degisiklige kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve fikstur
O AYNADAN kosulur. Gercek ev yoluna `rm -rf`/`rmtree`/`unlink` YOK.

Calistir:  python3 tools/parite-fikstur-olcum-ortami-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
FIKSTUR = "parite-fikstur-test.js"

# 🔴 CAPA ADLA, POZISYONLA DEGIL (7 Eyl 2026 — K196 ekseni, OLCULDU).
# ESKIDEN buradaki sabitler SENARYO INDEKSIYDI (SM1="29", S8="8"). Fikstur senaryo
# kumesini ORTAMA gore kurar: kardes bot deposu (`/Users/okan/dev/pruvo-bot/...`) YOKSA
# S17-S21 + S26-S28 + SM1-SM3 HIC KAYDOLMAZ -> yerelde 32 senaryo, CI'da 21. Indeks 29
# CI'da MENZIL DISI kaliyor, fikstur hicbir senaryo kosmadan "IDDIA: 0 gecti | 0 KALDI"
# basip CIKIS 0 veriyordu; batarya bunu COKME sayip 6 mutanti "KALDI" ilan ediyordu.
# Sonuc: hijyen-a3 CI'da KIRMIZI, ayni agac yerelde YESIL — teshis edilemeyen bir sinif.
# ONARIM iki bacakli: (1) fikstur menzil disi indekse cikis 3 (OLCULEMEDI) verir,
# (2) batarya senaryoyu ADIN ILK JETONUYLA (TAM ESITLIK, onek DEGIL) cozer ve senaryo
# kayitli degilse UC KOVAYA ayirir — asagidaki `capa_coz`.
S8 = "S8"    # S8 (K2) KIRMIZI + uc SUSUYOR

# 🔴 ORTAM MAZERETI YOK: ortama bagli senaryo kalmadi (Ege, 6 Eki 2026). "senaryo kayitli
# degil" hali TOPTAN mazur gorulmez ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]):
# kayit defterinde olmayan capa DUSMUSTUR -> KIRMIZI.

# Bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir: tek senaryo 7-9 iddia olcer.
TABAN_IDDIA = 5

# (ad, dosya, eski, yeni, senaryo, beklenen, eksen)
# `eksen`: mutant KIRMIZI yanmakla kalmayip O SENARYOYU dusurmeli. Yoksa "kirmizi yandi"
# hukmu baska bir kolun artigi olabilir ([[beyan-edilmis-survivor]]).
MUTANTLAR = [
    # ── KANON KOLU: kanon haritasi HANGI katalogtan turuyor? (S8 uzerinden) ─────
    ("OLDURUCU M1 YOLU MODUL YUKLENIRKEN COZ (bayat hal: harness uretim katalogunu olcer)",
     "parite-marka-sinifi.js",
     "function urunlerYoluCoz() {\n"
     "  return process.env.PARITE_URUNLER || path.join(__dirname, \"..\", \"urunler.json\");\n"
     "}",
     "const _YUKLEME_ANI_YOL = process.env.PARITE_URUNLER ||"
     " path.join(__dirname, \"..\", \"urunler.json\");\n"
     "function urunlerYoluCoz() { return _YUKLEME_ANI_YOL; }",
     S8, "KIRMIZI", "S8"),
    # ── ESKI KOR NOKTA K0 -> OLDURUCU M2 (6 Eki 2026, OLCULDU) ────────────────────
    # SM1 bir ANLASMA iddiasiydi: `PARITE_URUNLER`i IKI tarafta da yok saymak ebeveyni ve
    # cocugu AYNI uretim kataloguna baglar, ayrisma DOGMAZDI -> SM1'de KONTROL (YESIL)
    # olarak beyan edilmis kor noktaydi. SM1 Ege ile kaldirildi; ayni mutant S8'de
    # OLDURUR: uretim katalogu kanon uretimini ~22 sn'ye cikarir, S8 zaman asimi asilir
    # (olculdu: senaryo=8 gecti=5 KALDI=2, M1/M4/M5 ile ayni imza). Kor nokta bu capada
    # KAPALIDIR; beklenti KIRMIZI + eksen S8 (yalniz "kirmizi yandi" yetmez).
    ("OLDURUCU M2 ENV'I IKI TARAFTA DA YOK SAY (uretim katalogu S8 istek yoluna girer)",
     "parite-marka-sinifi.js",
     "  return process.env.PARITE_URUNLER || path.join(__dirname, \"..\", \"urunler.json\");",
     "  return path.join(__dirname, \"..\", \"urunler.json\");",
     S8, "KIRMIZI", "S8"),
    ("OLDURUCU M3 FIKSTUR ENV'I HIC KURMASIN (sahte uc kendi D1'ini modellemez)",
     FIKSTUR,
     "  process.env.PARITE_URUNLER = kanonKatalog;",
     # Atama SATIRI dusurulur (env hic kurulmaz). Eski yazim `= oncekiUrunlerEnv` env
     # yokken process.env'e "undefined" DIZGESINI yaziyordu -> yol "undefined" olur,
     # cocuk COKER (olculdu 6 Eki: COKME, IDDIA satiri YOK); mutantin niyeti bu degildi.
     "  /* M3: PARITE_URUNLER kurulmadi */",
     S8, "KIRMIZI", "S8"),
    ("OLDURUCU M4 ENV'I COCUK KOSMADAN GERI AL (kurulum var, KOSUM aninda yok)",
     FIKSTUR,
     "  const sunucu = http.createServer((req, res) => {",
     "  envGeriAl();\n  const sunucu = http.createServer((req, res) => {",
     S8, "KIRMIZI", "S8"),
    # ── S8 KOLU: soguk baslangic ISTEK YOLUNDA mi? ──────────────────────────────
    # Kanon katalogu URETIM katalogu yapilirsa `marka-kanon-uret.py` yine 20 bin urun
    # uzerinde kosar (~22 sn, SENKRON) ve bedel ilk istegin isleyicisinde odenir.
    ("OLDURUCU M5 KANON KATALOGU URETIM KATALOGU OLSUN (22 sn ISTEK YOLUNA geri doner)",
     FIKSTUR,
     "  process.env.PARITE_URUNLER = kanonKatalog;",
     "  process.env.PARITE_URUNLER = path.join(TOOLS, \"..\", \"urunler.json\");",
     S8, "KIRMIZI", "S8"),
    # ── KONTROL: iddia edilmeyen eksen / davranissiz yazim ──────────────────────
    ("KONTROL K1 davranissiz yazim (sinif govdesinde yerel degisken adi)",
     "parite-marka-sinifi.js",
     "  const yol = urunlerYoluCoz();",
     "  const yol = String(urunlerYoluCoz());",
     S8, "YESIL", None),
    ("KONTROL K2 iddia edilmeyen eksen (fikstur yorum metni)",
     FIKSTUR,
     "// 🔴 SAHTE UC KENDI D1'INI MODELLER:",
     "// 🔴 SAHTE UC KENDI D1'INI MODELLER :",
     S8, "YESIL", None),
    ("KONTROL K3 davranissiz yazim (gecici dizin oneki)",
     FIKSTUR,
     "\"parite-fikstur-kanon-\"",
     "\"parite-fikstur-kanon2-\"",
     S8, "YESIL", None),
]


def ayna_kur(tmp):
    """ROOT'un SALT OKUNUR aynasi: tools/ gercek bir dizin, digerleri symlink.

    🔴 `.js` DOSYALARI SYMLINK DEGIL GERCEK KOPYA OLMAK ZORUNDA (6 Eyl 2026, OLCULDU).
    Node `require`'i varsayilan olarak SYMLINK'i COZER: aynadaki `parite-fikstur-test.js`
    bir symlink olsaydi `require("./parite-marka-sinifi.js")` GERCEK agactaki dosyaya
    coreler ve mutant HIC YUKLENMEZDI. Ilk kosumda tam bu oldu — `parite-marka-sinifi.js`
    mutantlari (M1/M2) "KACTI" gorundu, KONTROL K1 de "YESIL" diye SAHTE gecti; yani
    batarya olcuyor gibi yapip HICBIR SEY olcmuyordu ([[mutant-canli-govdede-yasamaz]]).
    `.js` kopyalanip digerleri symlink kalinca cozum aynanin ICINDE kapanir.
    Python araclari yol ile cagrildigi icin symlink olarak kalabilir (21 MB kopyalanmaz).
    """
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        hedef = os.path.join(kok, "tools", ad)
        if ad.endswith(".js") and os.path.isfile(kaynak):
            shutil.copy2(kaynak, hedef)
        else:
            os.symlink(kaynak, hedef)
    return kok


def kayit_defteri(kok=None):
    """Fiksturun O ORTAMDAKI senaryo kayit defteri: {ilk_jeton: indeks} + ortam satiri.

    TEK KAYNAK fiksturun kendisidir (`--senaryolar`); batarya kendi kopyasini TUTMAZ,
    yoksa iki taraf bayatlar. Jeton = senaryo adinin ILK bosluga kadarki parcasi ve
    esleme TAM ESITLIKTIR — onek eslemesi olsaydi "S1" capasi "S10"/"S11"i de yakalardi
    ([[arac-adi-onek-eslesmesi-komsu-araci-keser]]).
    """
    r = subprocess.run(
        ["node", os.path.join(kok or TOOLS, FIKSTUR), "--senaryolar"],
        capture_output=True, text=True, cwd=kok or ROOT, timeout=600)
    cikti = r.stdout + r.stderr
    defter = {}
    for m in re.finditer(r"^SENARYO: (\d+)\t(\S+)", cikti, re.M):
        defter[m.group(2)] = m.group(1)
    ortam = re.search(r"^OLCUM-ORTAMI: .*$", cikti, re.M)
    return defter, (ortam.group(0) if ortam else "(OLCUM-ORTAMI satiri YOK)")


def capa_coz(jeton, defter):
    """IKI HAL — capa cozulur ya da KAYIP (kirmizi). Ortam mazereti (eski ATLANDI kovasi,
    Ege bot deposuna bagliydi) kalmadi: kayit defterinde olmayan capa DUSMUSTUR."""
    if jeton in defter:
        return "VAR", defter[jeton]
    return "KAYIP", ("CAPA DUSTU: '%s' senaryosu kayit defterinde YOK (kayit=%d)"
                     % (jeton, len(defter)))


def main():
    defter, ortam_satiri = kayit_defteri()
    print("\n" + ortam_satiri)
    tmp = tempfile.mkdtemp(prefix="parite-fikstur-olcum-ortami-")
    sonuc = []
    try:
        for ad, dosya, eski, yeni, jeton, beklenen, eksen in MUTANTLAR:
            hal, senaryo = capa_coz(jeton, defter)
            if hal == "KAYIP":
                sonuc.append((ad, beklenen, "CAPA-DUSTU — " + senaryo))
                continue
            kaynak_yolu = os.path.join(TOOLS, dosya)
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if taban.count(eski) != 1:
                # 🔴 CAPA TAM BIR KEZ ESLESMELI. Kaymissa "mutant uygulanamadi" YESIL
                # sayilmaz; kanit OLCULEMEDI'dir.
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(os.path.join(tmp, str(len(sonuc))))
            hedef = os.path.join(kok, "tools", dosya)
            os.unlink(hedef)   # kopya da olsa symlink de olsa: yerine mutant yazilir
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run(
                ["node", os.path.join(kok, "tools", FIKSTUR), senaryo],
                capture_output=True, text=True, cwd=kok, timeout=1800)
            cikti = r.stdout + r.stderr
            m = re.search(r"^IDDIA: (\d+) gecti \| (\d+) KALDI", cikti, re.M)
            if not m:
                gozlem = "COKME(IDDIA satiri YOK: %s)" % cikti.strip().split("\n")[-1][:90]
            else:
                gecti, kaldi = int(m.group(1)), int(m.group(2))
                if gecti + kaldi < TABAN_IDDIA:
                    gozlem = "COKME(olculen iddia sayisi dusuk: %d)" % (gecti + kaldi)
                elif kaldi:
                    gozlem = "KIRMIZI"
                else:
                    gozlem = "YESIL"
                if eksen and gozlem == "KIRMIZI":
                    # TEKIL EKSEN SARTI: kirmizi yeterli DEGIL, O SENARYO dusmus olmali.
                    # Esleme ILK JETONDA TAM ESITLIK (onek olsaydi "S1" -> "S10"u yakalardi).
                    dusen = re.findall(r"^KALAN-SENARYO: (.*)$", cikti, re.M)
                    if not any(s.split(" ")[0] == eksen for s in dusen):
                        gozlem = "EKSEN-YOK(%s dusmedi)" % eksen
                gozlem += " (senaryo=%s gecti=%d KALDI=%d%s)" % (
                    senaryo, gecti, kaldi, " eksen=" + eksen if eksen else "")
            sonuc.append((ad, beklenen, gozlem))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: tools/%s — senaryo S8)" % FIKSTUR)
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-84s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    olculen = len(sonuc)
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    if olculen == 0:
        # 🔴 HICBIR SEY OLCULMEDIYSE YESIL YAZILAMAZ. Cikis kodu sozlesmesi TEK KAYNAK:
        # tools/parite-ortak.js (CIKIS_OLCULEMEDI). "0 mutant kosuldu" ile "8 mutant
        # gecti" ayni cikis kodunu ASLA veremez.
        print("\nSONUC: OLCULEMEDI ⚪  (0 mutant kosuldu — batarya bu ortamda KOR)")
        return 3
    print("\nSONUC: YESIL ✅  (%d mutant olculdu: her OLDURUCU kirmizi, her KONTROL yesil)"
          % olculen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
