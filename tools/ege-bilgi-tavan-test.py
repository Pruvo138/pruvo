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
  EDEMEZ. Kismi koruma: asagidaki ILAN kontrolu + bot reposundaki
  pruvo-bot/worker/test/ege-bilgi-nobetci.mjs (tavani index.js'ten CANLI okur, ama
  yalniz yerelde kosar).

HUKUM (deploy.yml'de continue-on-error YOK -> sifir-disi cikis TUM YAYINI bloke eder;
bu yuzden KIRMIZI kumesi BILEREK DAR tutulur — gerekce asagida):
  KIRMIZI (exit 1) — yalniz iki hal:
    K1. uzunluk > TAVAN                     (metin GERCEKTEN kesiliyor: icerik kaybi)
    K2. ilanda AYRISTIRILABILEN TEK sayi var VE o sayi TAVAN'dan FARKLI
        (belgeyi yazan insanin inandigi tavan ile makinenin denetledigi tavan ayrismis;
         biri bayat -> ikisi de yanlis hukum uretir)
    + fail-loud: dosya yok / okunamiyor / UTF-8 degil (olculecek sey YOK -> sessiz yesil
      VERILMEZ; bu "olcum yapilamadi" halidir, icerik hukmu degil)
  UYARI (exit 0, gurultulu) — hukum DEGIL:
    U1. dar pay (TAVAN - uzunluk < GUVENLIK_MARJI)
    U2. ILAN YOK (bastaki satirlarda tavan ilani ayristirilamadi)
    U3. CELISKILI ILAN (bastaki satirlarda birden fazla FARKLI tavan sayisi)
    U4. ILAN BASTA DEGIL (ilan var ama bastaki pencerenin altina kaymis)

🔴 UYARILAR NEDEN KIRMIZI DEGIL (bu kapinin en kritik ayari — 21 Tem bagimsiz curutucu
   dort tetikleyici olctu; hepsi MASUM duzenlemeydi ve TUM EKIBIN yayinini durduruyordu):
     A1  bastaki satirlarda baska bir sayi iceren uslup kurali ("her cevabi 300 karakter
         altinda tutar") -> eski surum "CELISKILI ILAN" deyip exit 1
     A2  kozmetik binlik ayraci: "ilk 6000" -> "ilk 6.000" -> eski regex '000' yakalayip
         "dosya '0 karakter' diyor" diyerek exit 1 (YANILTICI TESHIS ustune yanlis kirmizi)
     A3  yer acmak icin ilan cumlesinin silinmesi -> "ILAN YOK" exit 1
     A4  basa icindekiler eklenmesi, ilanin 15. satirin ALTINA kaymasi -> "ILAN YOK" exit 1
   Ustelik kapi dar payda "yer ac / kisalt" tavsiyesi veriyor; kisaltilacak en bariz metin
   ILANIN KENDISI -> kapi kendi tavsiyesiyle kendi yanlis-pozitifine yonlendiriyordu.
   Ilke (kardes repoda YASANDI: pruvo-bot/worker/test/ege-bilgi-nobetci.mjs:1148):
   "Nobetci DOGRU dosyayi reddederse kimse ona bakmaz; sonra GERCEK kirmizi da gorulmez.
   Uyari degerli, kapi degil." Kirmizi yalniz GERCEK zararda: metin KESILIYORSA ya da
   tek ve net bir ilan sayisi sabitle ACIKCA celisiyorsa.

ILAN AYRISTIRMA (parser taklidi YAPMA ilkesi — [[mimar-kapi-parser-taklidi]]):
  Ilan cumlesi tam baglama demirlenir: "<onek: ilk / en fazla / azami> <SAYI> karakter
  ... <fiil: ulasir / okunur / keser / gider ...>". Binlik ayracli sayi ("6.000", "6 000")
  DOGRU ayristirilir. Baglami tutmayan rastgele sayi ("300 karakter altinda tutar")
  TOPLANMAZ. Supheliyse ILAN YOK sayilir ve UYARILIR — supheden KIRMIZI URETILMEZ.

KENDI MANTIGINI KORUYAN IC NOBETCI:
    python3 tools/ege-bilgi-tavan-test.py --ic-nobetci
  Kapinin kendi hukmunu gecici fiksturlerle olcer (tavan asimi, sinir 6000/6001,
  astral/UTF-16 ayrismasi, dar pay/genis pay, dosya yok, UTF-8 degil, ilan sapmasi,
  binlik ayrac, A1-A4 masum duzenlemeler). Fiksturler tempfile'da uretilir; repodaki
  hicbir dosyaya DOKUNULMAZ. Kod mutasyonu (tavan hukmunu oldur / UTF-16'yi len(str)
  yap / marji oynat / fail-loud dalini return 0 yap / ilan nobetcisini oldur) bu
  bayrakla KIRMIZI yanar.

Kullanim:
    python3 tools/ege-bilgi-tavan-test.py
    python3 tools/ege-bilgi-tavan-test.py --dosya /gecici/mutant-ege-bilgi.md
    python3 tools/ege-bilgi-tavan-test.py --ic-nobetci
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
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

# Ilan BASTA olmali: HUKUM icin yalniz ilk ILAN_SATIR_SAYISI satir taranir.
ILAN_SATIR_SAYISI = 15

# Binlik ayracli sayi ONCE denenir ("6.000" -> 6000). Duz sayi 3-6 hane.
# Ayrac kumesi: nokta, normal bosluk, NBSP (U+00A0), dar NBSP (U+202F).
_SAYI = "[0-9]{1,3}(?:[.   ][0-9]{3})+|[0-9]{3,6}"
# Tavan ilanini ACAN onek — bunlarsiz bir sayi ILAN SAYILMAZ (A1'in cozumu).
_ONEK = ("ilk(?:\\s+olarak)?|en\\s+fazla|en\\s+[cç]ok|azami|"
         "yaln[iı]z(?:ca)?\\s+ilk|sadece\\s+ilk|ba[sş]tan\\s+ilk")
# Ilani KAPATAN fiil/isim: metnin Ege'ye ULASMASI / KESILMESI baglami.
_FIIL = ("ula[sş]|eri[sş]|oku|g[oö]r|al[iı]r|gider|iletil|"
         "g[oö]nderil|kes|k[iı]rp|s[iı]n[iı]r|tavan|kadar")
# ILAN_RE = TAM CUMLE BAGLAMI: <onek> <SAYI> karakter ... <fiil>, TEK satir icinde.
# Tek YAKALAMA grubu vardir (sayi) -> findall dogrudan sayi metinlerini dondurur.
ILAN_RE = re.compile(
    "\\b(?:" + _ONEK + ")\\s+(" + _SAYI + ")\\s*karakter[^\n]{0,80}?(?:" + _FIIL + ")",
    re.IGNORECASE)

# Binlik ayraclarini silmek icin (str.translate haritasi).
_AYRAC_SIL = {ord("."): None, ord(" "): None, ord(" "): None, ord(" "): None}


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


def sayi_coz(ham):
    """'6.000' / '6 000' / '6000' -> 6000. Ayristirilamazsa None (KIRMIZI URETMEZ)."""
    try:
        return int(ham.translate(_AYRAC_SIL))
    except ValueError:
        return None


def ilan_edilen_tavan(metin):
    """Metinde ILAN EDILEN tavan sayilari (ayristirilamayan eslesme DUSURULUR)."""
    return [s for s in (sayi_coz(h) for h in ILAN_RE.findall(metin)) if s is not None]


def _bas_bolge(metin):
    return "\n".join(metin.splitlines()[:ILAN_SATIR_SAYISI])


def degerlendir(dosya):
    """(cikis_kodu, rapor_satirlari) — hukum burada, yazdirma main'de.

    Ic nobetci hem CIKIS KODUNU hem RAPOR METNINI dogruladigi icin hukum ile yazdirma
    ayri tutulur."""
    t0 = time.perf_counter()
    r = []

    # fail-loud: dosya yok / okunamiyor / UTF-8 degil
    if not os.path.exists(dosya):
        r.append("EGE-BILGI TAVAN KAPISI")
        r.append("  ❌ DOSYA BULUNAMADI: %s" % dosya)
        r.append("SONUC: KIRMIZI ❌ — olculecek dosya yok. Ege'nin bilgi kaynagi silinmis ya da "
                 "tasinmis olabilir; sessiz yesil VERILMEZ.")
        return 1, r
    try:
        with open(dosya, "rb") as f:
            ham = f.read()
    except OSError as hata:
        r.append("EGE-BILGI TAVAN KAPISI")
        r.append("  ❌ DOSYA OKUNAMADI: %s -> %s" % (dosya, hata))
        r.append("SONUC: KIRMIZI ❌")
        return 1, r
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError as hata:
        r.append("EGE-BILGI TAVAN KAPISI")
        r.append("  ❌ UTF-8 olarak cozulemedi: %s" % hata)
        r.append("SONUC: KIRMIZI ❌ — bot dosyayi UTF-8 bekliyor.")
        return 1, r

    bayt = len(ham)
    kod_noktasi = len(metin)
    uzunluk = utf16_birim(metin)
    pay = TAVAN - uzunluk

    hatalar = []
    uyarilar = []

    # ---- ILAN: HUKUM yalniz "TEK sayi var ve TAVAN'dan FARKLI" halinde ----
    bas_ilanlar = ilan_edilen_tavan(_bas_bolge(metin))
    tekil = sorted(set(bas_ilanlar))
    if len(tekil) == 1:
        if tekil[0] != TAVAN:
            hatalar.append(
                "ILAN/SABIT UYUSMAZLIGI: dosya '%d karakter' ilan ediyor, kapi sabiti "
                "TAVAN=%d. Gercek tavan pruvo-bot/worker/src/index.js:2232'de — hangisi "
                "bayat? Ikisini hizala." % (tekil[0], TAVAN))
    elif len(tekil) > 1:
        uyarilar.append(
            "CELISKILI ILAN (uyari, kapi DEGIL): bastaki %d satirda birden fazla FARKLI "
            "tavan sayisi ayristirildi: %s. Hangisinin gercek tavan oldugu belirsiz -> "
            "supheden KIRMIZI uretilmez. Tavan cumlesini tekillestir."
            % (ILAN_SATIR_SAYISI, tekil))
    else:
        govde_ilanlar = sorted(set(ilan_edilen_tavan(metin)))
        if govde_ilanlar:
            uyarilar.append(
                "ILAN BASTA DEGIL (uyari, kapi DEGIL): tavan ilani ilk %d satirda YOK, "
                "asagida bulundu: %s. Ilan BASTA olsun ki dosyayi acan insan tavani gorsun "
                "(kapi bu halde ilan/sabit karsilastirmasi YAPMAZ)."
                % (ILAN_SATIR_SAYISI, govde_ilanlar))
        else:
            uyarilar.append(
                "ILAN YOK (uyari, kapi DEGIL): ilk %d satirda '<onek> <N> karakter ... "
                "<ulasir/okunur/keser>' bicimli tavan ilani ayristirilamadi. Belge tavani "
                "artik anmiyorsa yazan insan tavandan habersizdir -> ilani geri koy (ya da "
                "ILAN_RE desenini BILEREK guncelle). Ilan yoklugu tek basina icerik kaybi "
                "DEGIL, bu yuzden yayin durdurulmaz." % ILAN_SATIR_SAYISI)

    # ---- K1: tavan asimi -> KIRMIZI ----
    if uzunluk > TAVAN:
        kesilen = utf16_kuyruk(metin, TAVAN)
        onizleme = kesilen[:300].replace("\n", "\\n")
        hatalar.append(
            "TAVAN ASILDI: dosya %d UTF-16 birimi, tavan %d -> son %d karakter Ege'ye HIC "
            "ULASMIYOR (sessiz kirpma). Kesilen bolgenin basi: %r%s"
            % (uzunluk, TAVAN, uzunluk - TAVAN, onizleme,
               "…" if len(kesilen) > 300 else ""))
    # ---- U1: dar pay -> UYARI (exit 0), hukum DEGIL ----
    elif pay < GUVENLIK_MARJI:
        uyarilar.append(
            "DAR PAY (uyari, kapi DEGIL): pay %d < marj %d — ege-bilgi.md tavana YAKIN. "
            "Bugun kesilen bir sey YOK, ama bu dosyaya %d karakterden fazla ekleyen bir "
            "degisiklik Ege'nin bilgisini SESSIZCE kirpar (once kuyruk bolumleri duser). "
            "Ekleme yapacaksan once yer ac / kisalt — AMA tavan ilan cumlesini SILME "
            "(kapi onu arar; silinirse ILAN YOK uyarisi verir)."
            % (pay, GUVENLIK_MARJI, pay))

    sure_ms = (time.perf_counter() - t0) * 1000.0

    r.append("EGE-BILGI TAVAN KAPISI")
    r.append("  Dosya                 : %s" % dosya)
    r.append("  TAVAN (kopya sabit)   : %d  [gercegi: pruvo-bot/worker/src/index.js:2232 slice(0, 6000)]" % TAVAN)
    r.append("  GUVENLIK_MARJI        : %d  [bot nobetcisi ege-bilgi-nobetci.mjs:310 ile AYNI sayi]" % GUVENLIK_MARJI)
    r.append("  Ilan edilen tavan     : %s"
             % (tekil if tekil else "YOK (bastaki %d satirda)" % ILAN_SATIR_SAYISI))
    r.append("  Olcu — bayt           : %d   (JS slice BUNU saymaz; bayt sayan kapi sahte-kirmizi yakar)" % bayt)
    r.append("  Olcu — kod noktasi    : %d   (Python len(str); astral karakterde EKSIK sayar -> sahte-yesil)" % kod_noktasi)
    r.append("  Olcu — UTF-16 birimi  : %d   <- HUKUM BUNA GORE (JS String.slice birimi)" % uzunluk)
    r.append("  Tavana kalan pay      : %d" % pay)
    r.append("  Kosum suresi          : %.2f ms" % sure_ms)
    r.append("-" * 70)

    for u in uyarilar:
        r.append("  ⚠️  " + u)
    if hatalar:
        for h in hatalar:
            r.append("  ❌ " + h)
        r.append("-" * 70)
        r.append("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1, r
    if uyarilar:
        r.append("-" * 70)
        r.append("SONUC: YESIL (UYARILI) ⚠️  — yayin durdurulmuyor; metin kesilmiyor.")
        return 0, r
    r.append("-" * 70)
    r.append("SONUC: YESIL ✅  — dosya tavanin altinda, pay marjin ustunde, ilan/sabit uyusuyor.")
    return 0, r


# ---------------------------------------------------------------------------
# IC NOBETCI — kapinin KENDI mantigini koruyan, COMMIT EDILMIS fiksturler
# ---------------------------------------------------------------------------
ILAN_ORNEK = "Ege'nin canli bilgi kaynagi. Ege'ye ilk 6000 karakter ulasir; kritik olan BASTA."


def _fikstur_metni(kod_hedef, astral_adet=0, ilan=ILAN_ORNEK, ek_satirlar=(), on_satirlar=()):
    """Kod noktasi sayisi TAM kod_hedef olan fikstur metni uretir.

    UTF-16 uzunlugu = kod_hedef + astral_adet (her astral karakter 2 kod birimi tutar)."""
    parcalar = ["# EGE — Sirket & Isleyis Bilgisi", ""]
    parcalar.extend(on_satirlar)
    if ilan:
        parcalar.append(ilan)
    parcalar.extend(ek_satirlar)
    parcalar.append("")
    bas = "\n".join(parcalar) + "\n"
    dolgu = kod_hedef - len(bas) - astral_adet
    if dolgu < 0:
        raise ValueError("fikstur hedefi bas metinden kucuk: %d" % kod_hedef)
    return bas + ("y" * dolgu) + ("\U0001F9E9" * astral_adet)


def _yaz(dizin, ad, metin):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return yol


def _fiksturler(dizin):
    """[(ad, yol, beklenen_kod, iceren, icermeyen)] — hepsi tempfile, repoya DOKUNMAZ."""
    f = []

    # K1 — tavan asimi KIRMIZI (mutasyon: tavan hukmunu oldur)
    f.append(("K1 tavan asimi (UTF-16 6200 > 6000) -> KIRMIZI",
              _yaz(dizin, "k1.md", _fikstur_metni(6200)), 1,
              ["TAVAN ASILDI", "SONUC: KIRMIZI"], []))

    # K1b — SINIR: tam 6000 kesilmez (slice(0,6000) 6000 birimin TAMAMINI alir)
    f.append(("K1b sinir: tam 6000 -> kesilmiyor, exit 0",
              _yaz(dizin, "k1b.md", _fikstur_metni(6000)), 0,
              ["SONUC: YESIL"], ["TAVAN ASILDI"]))

    # K1c — SINIR: 6001 KIRMIZI
    f.append(("K1c sinir: 6001 -> KIRMIZI",
              _yaz(dizin, "k1c.md", _fikstur_metni(6001)), 1,
              ["TAVAN ASILDI"], []))

    # K1d — ASTRAL: kod noktasi 5931 (<6000) ama UTF-16 6081 (>6000)
    #       (mutasyon: UTF-16 olcusunu len(str) yap -> bu fikstur sahte-yesil yanardi)
    f.append(("K1d astral: kod noktasi 5931 / UTF-16 6081 -> KIRMIZI",
              _yaz(dizin, "k1d.md", _fikstur_metni(5931, astral_adet=150)), 1,
              ["TAVAN ASILDI", "kod noktasi    : 5931", "UTF-16 birimi  : 6081"], []))

    # K2 — ilan sayisi TAVAN'dan farkli -> KIRMIZI (mutasyon: ilan nobetcisini oldur)
    f.append(("K2 ilan 4000 != TAVAN 6000 -> KIRMIZI",
              _yaz(dizin, "k2.md", _fikstur_metni(3000,
                   ilan="Ege'ye ilk 4000 karakter ulasir.")), 1,
              ["ILAN/SABIT UYUSMAZLIGI", "'4000 karakter'", "SONUC: KIRMIZI"], []))

    # FAIL-LOUD — dosya YOK (mutasyon: fail-loud dalini return 0 yap)
    f.append(("FL1 dosya YOK -> fail-loud KIRMIZI",
              os.path.join(dizin, "olmayan-dosya.md"), 1,
              ["DOSYA BULUNAMADI", "SONUC: KIRMIZI"], []))

    # FAIL-LOUD — UTF-8 degil
    bozuk = os.path.join(dizin, "fl2.md")
    with open(bozuk, "wb") as fh:
        fh.write(b"# EGE\n\xff\xfe gecersiz bayt dizisi\n")
    f.append(("FL2 UTF-8 degil -> fail-loud KIRMIZI", bozuk, 1,
              ["UTF-8 olarak cozulemedi", "SONUC: KIRMIZI"], []))

    # U1 — DAR PAY: pay 399 (<400) UYARI + exit 0 (mutasyon: marji DUSUR)
    f.append(("U1 dar pay 399 < marj 400 -> UYARI, exit 0",
              _yaz(dizin, "u1.md", _fikstur_metni(TAVAN - 399)), 0,
              ["DAR PAY", "SONUC: YESIL (UYARILI)"], ["SONUC: KIRMIZI"]))

    # U1b — GENIS PAY: pay 401 (>400) uyari YOK (mutasyon: marji YUKSELT)
    f.append(("U1b genis pay 401 > marj 400 -> uyari YOK",
              _yaz(dizin, "u1b.md", _fikstur_metni(TAVAN - 401)), 0,
              ["SONUC: YESIL ✅"], ["DAR PAY"]))

    # U1c — cok genis pay: tamamen sessiz yesil, hicbir ❌ yok
    f.append(("U1c genis pay (4000) -> sessiz YESIL",
              _yaz(dizin, "u1c.md", _fikstur_metni(4000)), 0,
              ["SONUC: YESIL ✅"], ["DAR PAY", "ILAN YOK", "CELISKILI ILAN", "❌"]))

    # A1 — bastaki satirlarda baska sayi iceren USLUP KURALI: exit 0, celiski SAYILMAZ
    f.append(("A1 uslup kurali '300 karakter altinda tutar' -> exit 0, celiski YOK",
              _yaz(dizin, "a1.md", _fikstur_metni(4000, ek_satirlar=[
                  "Uslup: her cevabi 300 karakter altinda tutar; kisa ve net yaz."])), 0,
              ["SONUC: YESIL ✅", "Ilan edilen tavan     : [6000]"],
              ["CELISKILI ILAN", "ILAN YOK", "❌"]))

    # A2 — binlik ayrac "6.000": DOGRU ayristirilmali, "'0 karakter'" teshisi CIKMAMALI
    f.append(("A2 binlik ayrac 'ilk 6.000 karakter' -> 6000 ayristirilir, exit 0",
              _yaz(dizin, "a2.md", _fikstur_metni(4000,
                   ilan="Ege'ye ilk 6.000 karakter ulasir; kritik olan BASTA.")), 0,
              ["Ilan edilen tavan     : [6000]", "SONUC: YESIL ✅"],
              ["'0 karakter'", "ILAN YOK", "❌"]))

    # A2b — bosluklu binlik ayrac "6 000"
    f.append(("A2b bosluklu ayrac 'ilk 6 000 karakter' -> 6000 ayristirilir, exit 0",
              _yaz(dizin, "a2b.md", _fikstur_metni(4000,
                   ilan="Ege'ye ilk 6 000 karakter ulasir.")), 0,
              ["Ilan edilen tavan     : [6000]"], ["'0 karakter'", "ILAN YOK", "❌"]))

    # A3 — ilan cumlesi SILINDI: uyari, exit 0
    f.append(("A3 ilan cumlesi silindi -> ILAN YOK uyarisi, exit 0",
              _yaz(dizin, "a3.md", _fikstur_metni(4000, ilan="")), 0,
              ["ILAN YOK", "SONUC: YESIL (UYARILI)"], ["SONUC: KIRMIZI"]))

    # A4 — ilan bastaki pencerenin ALTINA kaydi (basa icindekiler eklendi): uyari, exit 0
    on = ["## Icindekiler"] + ["- bolum %d" % i for i in range(1, 20)]
    f.append(("A4 ilan 15. satirin altinda -> ILAN BASTA DEGIL uyarisi, exit 0",
              _yaz(dizin, "a4.md", _fikstur_metni(4000, on_satirlar=on)), 0,
              ["ILAN BASTA DEGIL", "SONUC: YESIL (UYARILI)"], ["SONUC: KIRMIZI"]))

    # U3 — GERCEK celiski (iki FARKLI tavan ilani): uyari, exit 0
    f.append(("U3 iki farkli tavan ilani -> CELISKILI uyarisi, exit 0",
              _yaz(dizin, "u3.md", _fikstur_metni(4000, ek_satirlar=[
                  "Bota en fazla 5000 karakter okunur."])), 0,
              ["CELISKILI ILAN", "SONUC: YESIL (UYARILI)"], ["SONUC: KIRMIZI"]))

    return f


def ic_nobetci():
    dizin = tempfile.mkdtemp(prefix="ege-tavan-fikstur-")
    satirlar = ["EGE-BILGI TAVAN KAPISI — IC NOBETCI (kapinin kendi mantigi)",
                "  Fiksturler tempfile'da uretildi; repodaki dosyalara DOKUNULMADI.",
                "-" * 70]
    basarisiz = []
    try:
        fiks = _fiksturler(dizin)
        for ad, yol, beklenen, iceren, icermeyen in fiks:
            kod, rapor = degerlendir(yol)
            metin = "\n".join(rapor)
            sorun = []
            if kod != beklenen:
                sorun.append("cikis %d bekleniyordu, %d geldi" % (beklenen, kod))
            for parca in iceren:
                if parca not in metin:
                    sorun.append("rapor %r ICERMELIYDI" % parca)
            for parca in icermeyen:
                if parca in metin:
                    sorun.append("rapor %r ICERMEMELIYDI" % parca)
            if sorun:
                basarisiz.append(ad)
                satirlar.append("  ❌ %s" % ad)
                for s in sorun:
                    satirlar.append("       - %s" % s)
            else:
                satirlar.append("  ✅ %s" % ad)
        satirlar.append("-" * 70)
        satirlar.append("  Fikstur sayisi : %d" % len(fiks))
        satirlar.append("  Basarisiz      : %d" % len(basarisiz))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
    if basarisiz:
        satirlar.append("SONUC: KIRMIZI ❌ — kapinin kendi hukmu bozulmus. Yukaridaki "
                        "fiksturler kapinin SOZ VERDIGI davranistir; once onlari oku.")
        return 1, satirlar
    satirlar.append("SONUC: YESIL ✅ — kapi kendi hukmunu koruyor.")
    return 0, satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dosya", default=VARSAYILAN_DOSYA,
                    help="ege-bilgi.md yolu (kirmizi-mutasyon icin gecici kopya verilebilir)")
    ap.add_argument("--ic-nobetci", action="store_true", dest="ic_nobetci",
                    help="kapinin kendi mantigini gecici fiksturlerle olcer (repoya dokunmaz)")
    args = ap.parse_args()

    if args.ic_nobetci:
        kod, satirlar = ic_nobetci()
    else:
        kod, satirlar = degerlendir(args.dosya)
    for s in satirlar:
        print(s)
    return kod


if __name__ == "__main__":
    sys.exit(main())
