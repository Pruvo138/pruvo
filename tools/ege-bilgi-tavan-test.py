#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EGE-BILGI TAVAN KAPISI — ege-bilgi.md'nin SESSIZ kirpilma tavanina olcum nobetcisi.

NEDEN VAR: WhatsApp botu Ege, sirket/isleyis bilgisini canli olarak
https://pruvo3d.com/ege-bilgi.md adresinden ceker ve okurken KESER:

    pruvo-bot/worker/src/index.js:2232
        return (await r.text()).slice(0, 6000);

Kirpma SESSIZDIR: log yok, uyari yok, hata yok. Dosya tavani asarsa metnin KUYRUGU
(bugun "Sik sorulanlar" + "Ege'ye ozel notlar" bolumleri) Ege'nin gozunden kaybolur ve
musteriye EKSIK/YANLIS beyan gider. Bu kapi olcumu CI'ya baglar.

OLCU BIRIMI (kritik — olculdu 21 Tem; bugunku dosyada bayt=6349, kod noktasi=5781,
UTF-16 birimi=5781):
  JavaScript'in String.prototype.slice'i **UTF-16 kod birimi** sayar. Dogru olcu
  len(metin.encode("utf-16-le")) // 2'dir.
    * bayt sayan bir kapi (wc -c) BUGUN 6349 > 6000 gorup SAHTE KIRMIZI yakardi.
    * Python len(str) (kod noktasi) sayan bir kapi, metne emoji/astral karakter
      (U+10000 ustu) girdigi anda UTF-16'da 2 birim tutan karakteri 1 sayar ->
      tavan gercekten asilmisken SAHTE YESIL yakar.
  Bu kapi UTF-16 kod birimini sayar; uc olcuyu de rapora basar ki sapma gorunur olsun.

🔴 CAPRAZ-REPO BAYATLIK ACIGI (KAPATILAMAZ — kapatilmis gibi gosterme):
  GERCEK tavan bu repoda DEGIL, pruvo-bot/worker/src/index.js icindedir. Bu repo (pruvo)
  CI'sinin checkout'unda o dosya YOK; ayrica pruvo-bot reposunda .github dizini de YOK
  (orada CI kosmuyor — olculdu). Yani asagidaki TAVAN sabiti bot reposundaki gercek
  degerin bir KOPYASIDIR. HocA (pruvo-bot mimari) index.js'teki 6000'i degistirirse BU
  SABIT BAYATLAR ve kapi yanlis sayiya gore hukum verir — kapi bunu KENDI BASINA fark
  EDEMEZ. Kismi koruma: asagidaki (3) numarali ILAN kontrolu (belgenin kendi ilan ettigi
  tavan ile sabit ayrisirsa kirmizi) + bot reposundaki
  pruvo-bot/worker/test/ege-bilgi-nobetci.mjs (tavani index.js'ten CANLI okur, ama
  yalniz yerelde kosar).

HUKUM (deploy.yml'de continue-on-error YOK -> sifir-disi cikis TUM YAYINI bloke eder):
  1. uzunluk > TAVAN                -> KIRMIZI, exit 1  (metin GERCEKTEN kesiliyor)
  2. ILAN <-> SABIT uyusmazligi     -> KIRMIZI, exit 1  (belgeyi yazan insanin inandigi
     tavan ile makinenin denetledigi tavan ayrisirsa sessiz kalmasin)
  3. pay (TAVAN - uzunluk) < MARJI  -> exit 0 + GURULTULU UYARI (hukum DEGIL)
  4. dosya yok / UTF-8 degil        -> KIRMIZI, exit 1  (fail-loud; sessiz yesil YOK)

🔴 (3) NEDEN KIRMIZI DEGIL (katman duzeltmesi — bu kapinin en kritik ayari):
  Dar pay "henuz kimseye bir sey OLMADI" demektir; kesilen icerik YOKTUR. Kapi burada
  exit 1 verirse, DOGRU bir dosya CI'yi kirar ve TUM EKIBIN push'u durur. Bugun pay=219;
  marj 400 ile exit 1 verilseydi bu kapi ilk kosumda CI'yi kirardi. Ayni hata kardes
  repoda YASANDI ve duzeltildi: pruvo-bot/worker/test/ege-bilgi-nobetci.mjs:1148
  "dar pay ESKIDEN TEK BASINA KAPI-KIRMIZI idi. YANLIS KATMANDI ... Nobetci DOGRU dosyayi
  reddederse kimse ona bakmaz; sonra GERCEK kirmizi da gorulmez. Uyari degerli, kapi degil."

Kullanim:
    python3 tools/ege-bilgi-tavan-test.py
    python3 tools/ege-bilgi-tavan-test.py --dosya /gecici/mutant-ege-bilgi.md
"""
import argparse
import os
import re
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
VARSAYILAN_DOSYA = os.path.join(ROOT, "ege-bilgi.md")

# GERCEK tavan: pruvo-bot/worker/src/index.js:2232 -> (await r.text()).slice(0, 6000)
# (yukaridaki CAPRAZ-REPO BAYATLIK ACIGI notuna bak — bu bir KOPYADIR.)
TAVAN = 6000

# GUVENLIK_MARJI = 400: keyfi DEGIL. Bot reposundaki mevcut nobetci
# pruvo-bot/worker/test/ege-bilgi-nobetci.mjs:310 ayni sabiti
# `const GUVENLIK_MARJI = 400;` olarak kullaniyor. Iki nobetci celismesin diye BILEREK
# ayni sayi. Degistirilecekse IKISI BIRDEN degistirilmeli.
GUVENLIK_MARJI = 400

# Dosyanin bas kisminda ILAN EDILEN tavan ("Ege'ye ilk 6000 karakter ulasir").
# Yalniz ilk ILAN_SATIR_SAYISI satira bakilir: ilan BASTA olmali (govdedeki rastgele bir
# sayiyi ilan sanmayalim). "ilk" oneki OPSIYONEL tutuldu — "en fazla 6000 karakter" gibi
# masum bir yeniden yazim ILAN YOK sanilip TUM EKIBIN push'unu kirmasin.
ILAN_SATIR_SAYISI = 15
ILAN_RE = re.compile(r"(?:ilk|en\s+fazla|ilk\s+olarak)?\s*([0-9]{3,6})\s*karakter",
                     re.IGNORECASE)


def utf16_birim(metin):
    """JS String.prototype.slice'in saydigi birim: UTF-16 kod birimi."""
    return len(metin.encode("utf-16-le")) // 2


def utf16_kuyruk(metin, tavan):
    """TAVAN'inci UTF-16 kod biriminden SONRASI (Ege'ye ULASMAYAN bolge).

    Kod noktasiyla dilimlemek YANLIS olur: astral karakter iceren metinde kod-noktasi
    indeksi UTF-16 indeksinden kucuktur (olculdu: emoji mutasyonunda metin[6000:] BOS
    donuyordu, oysa 81 UTF-16 birimi gercekten kesiliyordu). Kesim bir surrogate ciftini
    ortadan bolebilecegi icin errors='replace'."""
    ham16 = metin.encode("utf-16-le")
    return ham16[tavan * 2:].decode("utf-16-le", errors="replace")


def ilan_edilen_tavan(metin):
    """Dosyanin bas kisminda ILAN EDILEN tavan sayilari (liste)."""
    bas = "\n".join(metin.splitlines()[:ILAN_SATIR_SAYISI])
    return [int(m) for m in ILAN_RE.findall(bas)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dosya", default=VARSAYILAN_DOSYA,
                    help="ege-bilgi.md yolu (kirmizi-mutasyon icin gecici kopya verilebilir)")
    args = ap.parse_args()

    t0 = time.perf_counter()

    # (4) fail-loud: dosya yok / okunamiyor / UTF-8 degil
    if not os.path.exists(args.dosya):
        print("EGE-BILGI TAVAN KAPISI")
        print("  ❌ DOSYA BULUNAMADI: %s" % args.dosya)
        print("SONUC: KIRMIZI ❌ — olculecek dosya yok. Ege'nin bilgi kaynagi silinmis ya da "
              "tasinmis olabilir; sessiz yesil VERILMEZ.")
        return 1
    try:
        with open(args.dosya, "rb") as f:
            ham = f.read()
    except OSError as hata:
        print("EGE-BILGI TAVAN KAPISI")
        print("  ❌ DOSYA OKUNAMADI: %s -> %s" % (args.dosya, hata))
        print("SONUC: KIRMIZI ❌")
        return 1
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError as hata:
        print("EGE-BILGI TAVAN KAPISI")
        print("  ❌ UTF-8 olarak cozulemedi: %s" % hata)
        print("SONUC: KIRMIZI ❌ — bot dosyayi UTF-8 bekliyor.")
        return 1

    bayt = len(ham)
    kod_noktasi = len(metin)
    uzunluk = utf16_birim(metin)
    pay = TAVAN - uzunluk

    hatalar = []
    uyarilar = []

    # (2) ILAN <-> SABIT uyusmasi
    ilanlar = ilan_edilen_tavan(metin)
    if not ilanlar:
        hatalar.append(
            "ILAN YOK: dosyanin ilk %d satirinda '<N> karakter' tavan ilani bulunamadi. "
            "Belge tavani artik anmiyorsa yazan insan tavandan habersizdir -> ilani geri koy "
            "(ya da bu kapinin ILAN_RE desenini BILEREK guncelle)." % ILAN_SATIR_SAYISI)
    elif len(set(ilanlar)) > 1:
        hatalar.append(
            "CELISKILI ILAN: dosyanin basinda birden fazla FARKLI tavan ilan ediliyor: %s"
            % sorted(set(ilanlar)))
    elif ilanlar[0] != TAVAN:
        hatalar.append(
            "ILAN/SABIT UYUSMAZLIGI: dosya '%d karakter' diyor, kapi sabiti TAVAN=%d. "
            "Gercek tavan pruvo-bot/worker/src/index.js:2232'de — hangisi bayat? Ikisini hizala."
            % (ilanlar[0], TAVAN))

    # (1) tavan asimi -> KIRMIZI
    if uzunluk > TAVAN:
        kesilen = utf16_kuyruk(metin, TAVAN)
        onizleme = kesilen[:300].replace("\n", "\\n")
        hatalar.append(
            "TAVAN ASILDI: dosya %d UTF-16 birimi, tavan %d -> son %d karakter Ege'ye HIC "
            "ULASMIYOR (sessiz kirpma). Kesilen bolgenin basi: %r%s"
            % (uzunluk, TAVAN, uzunluk - TAVAN, onizleme,
               "…" if len(kesilen) > 300 else ""))
    # (3) dar pay -> UYARI (exit 0), hukum DEGIL
    elif pay < GUVENLIK_MARJI:
        uyarilar.append(
            "UYARI: pay %d < marj %d — ege-bilgi.md tavana YAKIN. Bugun kesilen bir sey YOK "
            "(bu yuzden KIRMIZI degil), ama bu dosyaya %d karakterden fazla ekleyen bir "
            "degisiklik Ege'nin bilgisini SESSIZCE kirpar (once kuyruk bolumleri duser). "
            "Ekleme yapacaksan once yer ac / kisalt."
            % (pay, GUVENLIK_MARJI, pay))

    sure_ms = (time.perf_counter() - t0) * 1000.0

    print("EGE-BILGI TAVAN KAPISI")
    print("  Dosya                 : %s" % args.dosya)
    print("  TAVAN (kopya sabit)   : %d  [gercegi: pruvo-bot/worker/src/index.js:2232 slice(0, 6000)]" % TAVAN)
    print("  GUVENLIK_MARJI        : %d  [bot nobetcisi ege-bilgi-nobetci.mjs:310 ile AYNI sayi]" % GUVENLIK_MARJI)
    print("  Ilan edilen tavan     : %s" % (ilanlar if ilanlar else "YOK"))
    print("  Olcu — bayt           : %d   (JS slice BUNU saymaz; bayt sayan kapi sahte-kirmizi yakar)" % bayt)
    print("  Olcu — kod noktasi    : %d   (Python len(str); astral karakterde EKSIK sayar -> sahte-yesil)" % kod_noktasi)
    print("  Olcu — UTF-16 birimi  : %d   <- HUKUM BUNA GORE (JS String.slice birimi)" % uzunluk)
    print("  Tavana kalan pay      : %d" % pay)
    print("  Kosum suresi          : %.2f ms" % sure_ms)
    print("-" * 70)

    for u in uyarilar:
        print("  ⚠️  " + u)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("-" * 70)
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1
    if uyarilar:
        print("-" * 70)
        print("SONUC: YESIL (UYARILI) ⚠️  — dosya kesilmiyor ama pay dar.")
        return 0
    print("-" * 70)
    print("SONUC: YESIL ✅  — dosya tavanin altinda, pay marjin ustunde, ilan/sabit uyusuyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
