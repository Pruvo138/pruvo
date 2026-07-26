#!/usr/bin/env python3
"""EGE KABILIYET-SINIRI KAPISI — ege-bilgi.md musteriden URETIM olcusu/cizimi
ISTIYOR mu, ya da URETIM/FIYAT SOZU veriyor mu?

NEDEN VAR (26 Tem, mimar hukmu):
Ege'nin canli agzi (pruvo-bot/worker/src/index.js, SISTEM_TALIMATI) katalogda
esleme CIKMAYAN dalda uc yerde sunu yasakliyor:
  :41   "Musteriden uretim icin OLCU ya da teknik detay TOPLAMA ... URETIM ya da
         FIYAT SOZU VERME"
  :52   "URETIM icin musteriye olcu ALDIRMA: kumpas/serit metreyle olcu, mm degeri
         ya da merkez-merkez mesafe ISTEME"  (ISTISNA: TESHIS icin tek net foto /
         ek aci SERBEST — olcu/cizim degil)
  :2467 katalog-bos enjeksiyonu, ayni yasak
  :57   "yaklasik su kadar tutar' DEME"  -> tahmini fiyat da yasak, yalniz "kesin" degil
ege-bilgi.md her konusmada bu talimatin YANINA enjekte edilir. Oradaki bir satir
"olcu/cizim iste" ya da "ozel uretiriz" derse, ayni prompt icinde iki zit talimat
olusur ve model rastgele birini secer — yani yasak SESSIZCE delinir.

BU HATA SINIFINI OLCEN BASKA TEST YOKTU (olculdu, 26 Tem):
  · worker/test/ege-bilgi-nobetci.mjs -> 5 ekseni var (ODEME/TESLIM/KARGO/MALZEME/
    FIYAT); kabiliyet-siniri ekseni YOK.
  · worker/test/musteri-bacagi-nobetci.mjs -> sentetik fikstur okur, GERCEK
    ege-bilgi.md'ye bakmaz.
Sonuc: tam bu sinif, merge sonrasi tum testler YESIL yanarken canliya gecebiliyordu.
26 Tem'de bir kez gecti (dal metni "foto/olcu/cizim iste" idi) — bu kapi o dersin
cikti.

NE OLCER (KAPSAM DAR — bilerek):
  (A) ISTEK: musteriden URETIM icin olcu / cizim / teknik detay isteyen EMIR
  (B) URETIM SOZU: "ozel uretiriz" sinifi 1. cogul uretim taahhudu
  (C) YAKLASIK-FIYAT SOZU: "yaklasik/tahminen/civari/ortalama/bandinda ... TL"
      tipi TAHMIN taahhudu + acik "fiyat sozu ver" kaliplari
  🔴 (C) DUZ KESIN FIYAT BEYANINI KAPSAMAZ ("Bu parca 1.200 TL."). Kapsayamaz:
  belgenin MESRU icerigi fiyat/TL dolu (l.9 kargo esigi + ornek hesap), duz rakam
  yakalayan bir kural TUM SITE deploy'unu sahte-kirmizi ile durdururdu. Bu bir
  ILAN EDILMIS KOR NOKTADIR; fikstur M21 onu kalici olarak nobetler.
Uctu; dordunculeri buraya EKLEME. Kapsam buyutmek pozitif nobetciyi sessizce
oldurur (olculdu, bu repoda: [[kapi-kapsam-genisletme-tuzagi]]).

⚠️ BU KAPI `build` ISINDE KOSAR VE `deploy: needs: build` -> bir YANLIS-POZITIF
yalnizca Ege'yi degil TUM pruvo3d.com yayinini durdurur. Yeni desen eklerken
yanlis-pozitif fiksturlerini (M11-M15, M21) MUTLAKA koştur.

Kullanim:
  python3 tools/ege-kabiliyet-kapisi.py                 # repo ege-bilgi.md
  python3 tools/ege-kabiliyet-kapisi.py --dosya <yol>
  python3 tools/ege-kabiliyet-kapisi.py --ic-nobetci    # kapinin KENDI hukmunu olcer
Cikis: 0 YESIL · 1 KIRMIZI · 2 kullanim hatasi
"""

import argparse
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARSAYILAN = os.path.join(KOK, "ege-bilgi.md")

# --- jeton eksenleri -------------------------------------------------------
# OLCU/CIZIM jetonu: musteriden ISTENDIGINDE yasak olan SAYISAL/GEOMETRIK girdi.
# Dikkat: "kosul" (derece, nerede kullanilacak, UV, yuk) BU LISTEDE DEGIL —
# kosul sormak SISTEM_TALIMATI:12 ile ACIKCA SERBEST. Karistirirsan l.18/l.38
# gibi mesru satirlar sahte-kirmizi yanar.
OLCU_RE = re.compile(
    r"ölçü|ölçüler|çizim|teknik\s+resim|teknik\s+detay|teknik\s+çizim"
    r"|\bmm\b|\bcm\b|\bsantim|\bçap\b|\bçapı\b|kumpas"
    r"|merkez-\s*merkez|şerit\s*metre",
    re.IGNORECASE)

# ISTEK fiili — YALNIZ musteriden girdi talep eden EMIR kipleri.
# "netleştir" BILEREK YOK: l.11 ("ölçü/koşul belirsizse önce netleştir") mesru bir
# ic reflekstir, musteriden olcu talebi degil. Bu bir KOR NOKTA, asagida ilan edilir.
# 🔴 "\bsorun\b" BILEREK YOK: emir kipi "sor-un" ile Turkcenin en sik ismi "sorun"
#    (=problem) HOMOGRAF. "Olcuyle ilgili bir sorun olursa" cumlesi TUM SITE
#    deploy'unu durduruyordu (fikstur M11). Tek kelime ugruna deploy riski alinmaz.
ISTEK_RE = re.compile(
    r"\biste\b|\bisteyin\b|\bistersin\b|\btalep\s+et\b|\btalep\s+edin\b"
    r"|\btopla\b|\btoplayın\b|\baldır\b|\bölçtür\b|\bölçün\b"
    r"|\bgönder\b|\bgönderin\b|\bgöndersin\b|\bgöndermeniz\b|\bgönderiniz\b"
    r"|\biletin\b|\byaz\b|\byazın\b|\bpaylaşın\b|\bsor\b",
    re.IGNORECASE)

# URETIM SOZU — 1. cogul taahhut kipi. "üretilir/üretip/üretiyoruz/ürettiğimiz"
# BILEREK YOK: bunlar firma-kimligi/akis anlatimidir ve SISTEM_TALIMATI:2467 kimlik
# cumlesini ACIKCA serbest birakir ("ozel uretim yapan bir firmayiz, AMA ... sozunu
# SEN verme"). Yasak olan, MUSTERININ PARCASI icin verilen soz.
URETIM_SOZ_RE = re.compile(
    r"\büretiriz\b|\büretebiliriz\b|\büretiveririz\b|\byaparız\b|\byapabiliriz\b"
    r"|\byaptırabiliriz\b|\bhallederiz\b|\büstleniriz\b|\bbasarız\b|\btasarlarız\b"
    r"|sıfır\s+toleransla",
    re.IGNORECASE)

# FIYAT SOZU — kesin VEYA yaklasik. Yaklasik/tahmini yalniz PARA jetonuna yakinsa
# sayilir (l.22'deki "yaklasik aralik" isi dayanimi icindir, fiyat degil).
# Morfoloji varyantlari: "tahmini" yazip "tahminen"i, "civarinda" yazip "civari"yi
# kacirmak OLCULDU (mimar denetimi 26 Tem) — kapi ilan ettigini yakalamiyordu.
YAKLASIK_RE = re.compile(
    r"yaklaşık|tahmini|tahminen|aşağı\s*yukarı|civar\w*|bandında|banda"
    r"|ortalama|gibi\s+düşün",
    re.IGNORECASE)
PARA_RE = re.compile(r"\bfiyat|\bTL\b|\btutar|\bücret|\bmaliyet", re.IGNORECASE)

# 🔴 BETIMLEME BASTIRICI — (C)'nin KOSULSUZ yanmasi uc sahte-kirmizi uretiyordu:
#   "Sepette yaklasik tutar odeme oncesi GORUNUR."         -> arayuz betimlemesi
#   "Kargo ucreti yaklasik 250 TL olarak sepete EKLENIR."  -> sabit ucret betimlemesi
# Bunlar TAAHHUT degil BETIMLEME; belgenin kendi l.9'u da bu sinifa bir tik uzakta.
# Edilgen/betimleyici yuklem varsa (C) yanmaz. Taahhut kipleri (tutar/olur/deriz/
# diyebiliriz) bu listede YOKTUR — onlar yanmaya devam eder.
BETIMLEME_RE = re.compile(
    r"görünür|görüntülenir|gösterilir|eklenir|yazar\b|hesaplanır|yansır"
    r"|listelenir|belirtilir|geçerlidir",
    re.IGNORECASE)
FIYAT_SOZ_RE = re.compile(
    r"kesin\s+fiyat\s+(ver|söyle|yaz)\b|fiyat\s+(sözü|garantisi)\s+ver\b"
    r"|\bşu\s+kadar\s+tutar\b",
    re.IGNORECASE)

# OLUMSUZLAMA — Turkce -ma/-me emir olumsuzu + yasak isaretleri.
# Cumlecik (clause) duzeyinde bakilir. SATIR duzeyinde bakmak OLUMCUL: 26 Tem'in
# hatali satiri hem "iste" hem "verme" iceriyordu; satir duzeyi olumsuzlama
# "verme"yi gorup "iste"yi MASKELER ve kapi sahte-yesil yanardi (olculdu: fikstur M1).
OLUMSUZ_RE = re.compile(
    r"\bisteme\b|\btoplama\b|\baldırma\b|\bverme\b|\betme\b|\bgeçirme\b|\bsorma\b"
    r"|\bdeme\b|\bsunma\b|\buydurma\b|\bASLA\b|\bYASAK\b|\bDEĞİL\b|\bYOK\b"
    r"|\bkapsam\s+dışı\b|\bmez\b|\bmaz\b",
    re.IGNORECASE)

# Cumlecik ayirici: noktalama + BAGLAC.
# 🔴 Baglaclar (cunku/ama/fakat/ancak/zira) 26 Tem denetiminde eklendi: olumsuzlama
# maskesi bypass'i OLCULDU -> "Olcuyu gonderin CUNKU tahmin yeterli DEGIL" tek
# cumlecik sayiliyor, sondaki "degil" bastaki zararli EMRI susturuyordu (M16).
# Baglac sinirinda bolununce emir kendi cumleciginde degerlendirilir.
CUMLECIK_AYIRICI = re.compile(
    r"[.;,]|\n|\bçünkü\b|\bama\b|\bfakat\b|\bancak\b|\bzira\b", re.IGNORECASE)


def cumlecikler(satir):
    """Satiri cumleciklere boler. Olumsuzlama BU pencerede aranir."""
    return [p.strip() for p in CUMLECIK_AYIRICI.split(satir) if p.strip()]


def olumsuz(c):
    return bool(OLUMSUZ_RE.search(c))


def bulgular(metin):
    """(satir_no, sinif, cumlecik, gerekce) listesi dondurur."""
    out = []
    satirlar = metin.split("\n")
    i = 0
    while i < len(satirlar):
        satir = satirlar[i]
        no = i + 1
        j = 0
        parcalar = cumlecikler(satir)
        while j < len(parcalar):
            c = parcalar[j]
            if not olumsuz(c):
                if OLCU_RE.search(c) and ISTEK_RE.search(c):
                    out.append((no, "A/ISTEK", c,
                                "musteriden URETIM olcusu/cizimi isteniyor "
                                "(SISTEM_TALIMATI :41/:52/:2467 YASAKLIYOR)"))
                if URETIM_SOZ_RE.search(c):
                    out.append((no, "B/URETIM-SOZU", c,
                                "musterinin parcasi icin uretim taahhudu "
                                "(uretecegimize Okan karar verir — :41/:2467)"))
                yaklasik_taahhut = bool(
                    YAKLASIK_RE.search(c) and PARA_RE.search(c)
                    and not BETIMLEME_RE.search(c))
                if FIYAT_SOZ_RE.search(c) or yaklasik_taahhut:
                    out.append((no, "C/FIYAT-SOZU", c,
                                "yaklasik/tahmini fiyat taahhudu "
                                "(:57 'yaklasik su kadar tutar' DEME)"))
            j += 1
        i += 1
    return out


def olcumu_bas(yol, metin, sessiz=False):
    b = bulgular(metin)
    if not sessiz:
        print("EGE KABILIYET-SINIRI KAPISI")
        print("  Dosya : %s" % yol)
        print("  Olcum : %d satir, %d karakter" % (len(metin.split("\n")), len(metin)))
        print("  Kapsam: (A) olcu/cizim ISTEGI · (B) uretim sozu · (C) YAKLASIK fiyat sozu")
        print("          (C) duz kesin fiyat beyanini OLCMEZ — ilan edilmis kor nokta)")
        print("-" * 70)
        if not b:
            print("  Bulgu YOK.")
        k = 0
        while k < len(b):
            no, sinif, c, gerekce = b[k]
            print("  KIRMIZI [%s] satir %d" % (sinif, no))
            print("     cumlecik: %s" % c[:180])
            print("     gerekce : %s" % gerekce)
            k += 1
        print("-" * 70)
    return b


def ne_olculmedi():
    print("""
NE OLCULMEDI (durust liste — bu bir KELIME kapisidir, ANLAM onaylamaz):
  · Bu kapi PROSE ONAYI VERMEZ. Yesil = "aranan uc kalip bulunamadi" demektir;
    "metin dogru" demek DEGILDIR. Bu repoda olculdu: anlami tersine ceviren 25
    mutasyonun 22'si kelime arayan testten YESIL gecti.
  · 🔴 DUZ KESIN FIYAT BEYANI OLCULMEZ. "Bu parca 1.200 TL." · "Fiyat 900-1100 TL."
    gibi RAKAMLI DUZ beyanlar bu kapidan YESIL gecer. Kapsanamaz: belgenin MESRU
    icerigi fiyat/TL dolu (l.9 kargo esigi + ornek hesap), duz rakam yakalayan bir
    kural TUM SITE deploy'unu sahte-kirmizi ile durdururdu. (C) yalnizca YAKLASIK/
    TAHMIN kalibini + acik "fiyat sozu ver" kaliplarini olcer. Fikstur M21 bunu
    KALICI olarak nobetler — "duzeltmeye" calisan l.9'u kirar.
  · 🔴 OLUMSUZLAMA MASKESI TAMAMEN KAPANMADI. Zararli emirle olumsuzlama AYNI
    cumlecikte kalirsa emir susturulur. Baglac sinirlari (cunku/ama/fakat/ancak/
    zira) 26 Tem'de ayirici yapildi (M16), AMA noktalama ya da baglac ICERMEYEN
    tek cumlecikte olumsuzlama HALA maskeler — or. "Olcuyu gonderin tahmin yeterli
    degil". Belgenin uslubu DEGIL/YOK/ASLA vurgusuyla dolu oldugu icin bu GERCEK
    bir risktir; prose degisikliginde INSAN okumasi sart.
  · KOR NOKTA — "netleştir": l.11 "ölçü/koşul belirsizse netleştir" ISTEK
    fiili saymaz (mesru ic refleks kabul edildi). Biri olcu talebini "netleştir"
    diye yazarsa bu kapi GORMEZ. Bilincli sinir; genisletmek l.11/l.18/l.38'i
    sahte-kirmizi yakar.
  · KOR NOKTA — "sorun": emir kipi "sor-un" desenden CIKARILDI, cunku "sorun"
    (=problem) ismiyle homograf ve sahte-kirmizi uretiyordu (M11). "Olculeri bize
    sorun" gibi bir cumle bu kapidan GECER. Deploy riski > tek kelime kazanci.
  · KAPSAM DISI — ege-bilgi.md l.14 ("siparis sonrasi size ozel uretilir"):
    KOSULSUZ uretim taahhudu olarak mimar tarafindan AYRI bir acik madde olarak
    alindi (26 Tem). Pasif "üretilir" bilerek desende YOK — SISTEM_TALIMATI:2467
    firma-kimligi cumlesini serbest birakir. Bu kapi o maddeyi COZMEZ.
  · Yalniz ege-bilgi.md okunur. SISTEM_TALIMATI'nin kendisi, deploy edilmis worker,
    site sayfalari ve Ege'nin bu metni gercekten UYGULADIGI OLCULMEZ.
  · Olumsuzlama Turkce -ma/-me + yasak jetonu listesidir; listede olmayan
    olumsuzlama sekli (ornegin "istemekten kacin") sahte-KIRMIZI yakar.""")


# --------------------------------------------------------------------------
# IC NOBETCI — kapinin KENDI hukmunu fiksturlerle olcer (kirmizi-mutasyon sarti).
# Bu repoda bir kapi ancak boyle kabul edilir: yesil yanabildigi kadar KIRMIZI da
# yanabildigi GOSTERILMELIDIR.
# --------------------------------------------------------------------------
ESKI_DAL_SATIR = ("- *Yapabilir misiniz?* → Önce parçayı tanı; katalogda benzeri varsa "
                  "oradan git. Yoksa foto/ölçü/çizim iste, araştırıp döneceğini söyle "
                  "+ [DEVRET]; özel üretim ya da kesin fiyat sözü verme.")
MAIN_SATIR = ("- *Yapabilir misiniz?* → Foto/ölçü/çizim varsa kolaylaşır; katalogda "
              "benzeri varsa oradan git, yoksa özel üretiriz.")
YENI_SATIR = ("- *Yapabilir misiniz?* → Parçayı tanı; katalogdakine yönlendir, yoksa "
              "araştırıp döneceğini söyle + [DEVRET]. Ölçü/çizim isteme, "
              "üretim/fiyat sözü verme.")

# Belgenin KENDI mesru satirlari — canli metnin (C)/(A) sinifina en yakin cumleleri.
BELGE_L9 = ('- **Kargo — NET söyle, "siparişte netleşir" DEME:** 2.500 TL ve üzeri '
            'ücretsiz; altında gönderi başına **250 TL** toplama eklenir '
            '(ör. 1.500 TL + 250 TL kargo = 1.750 TL).')
BELGE_L11 = ("- **Doğru parça:** ölçü/koşul belirsizse netleştir, belirsizken "
             "sepete/siparişe geçirme.")

FIKSTURLER = [
    # (ad, metin, KIRMIZI_bekleniyor_mu, aciklama)
    # ═══ DOGRU-POZITIF (yakalama) ═══
    ("M1 eski dal metni (26 Tem kazasi)", ESKI_DAL_SATIR, True,
     "'olcu/cizim iste' EMRI — ayni satirda 'verme' olmasina ragmen yakalanmali "
     "(satir duzeyi olumsuzlama maskeleme testi)"),
    ("M2 main eski l.43", MAIN_SATIR, True, "'yoksa ozel uretiriz' = uretim taahhudu"),
    ("M6 mm degeri isteme",
     "- Deliğin çapını mm olarak gönderin, ona göre üretelim.", True,
     "'mm ... gonderin' = olcu talebi"),
    ("M7 yaklasik fiyat", "- Yaklaşık 800 TL tutar, ona göre planlayın.", True,
     ":57 'yaklasik su kadar tutar' DEME"),
    ("M10 kumpasla olctur", "- Kumpasla merkez-merkez mesafeyi ölçtür ve yaz.", True,
     "kumpas/merkez-merkez olcu talebi"),
    ("M16 baglac maskesi (MUST3)", "- Ölçüyü gönderin çünkü tahmin yeterli değil.",
     True, "'cunku' ayirici olmasa sondaki 'degil' bastaki EMRI maskelerdi"),
    ("M17 'tahminen' morfolojisi", "- Tahminen 700 TL tutar.", True,
     "'tahmini' yazip 'tahminen'i kacirmak olculdu"),
    ("M18 'civari' morfolojisi", "- 800 TL civarı olur.", True,
     "'civarinda' yazip 'civari'yi kacirmak olculdu"),
    ("M19 'ortalama ... diyebiliriz'", "- Ortalama 500 TL diyebiliriz.", True,
     "1. cogul tahmin taahhudu"),
    ("M20 'bandinda' tahmini", "- Fiyat 900-1100 TL bandında olur.", True,
     "bant tahmini de taahhuttur"),
    ("M22 teknik resim talebi", "- Teknik resim gönderin.", True, "cizim sinifi"),
    ("M23 cap/cm talebi", "- Çapı cm olarak yazın.", True, "olcu sinifi"),
    ("M24 ortuk uretim sozu", "- Sizin için yapabiliriz.", True,
     "ortuk 1. cogul uretim sozu"),
    # ═══ YANLIS-POZITIF NOBETCILERI ═══
    # ⚠️ Bu kapi `build` isinde kosar, `deploy: needs: build` -> asagidakilerden biri
    # KIRMIZI yanarsa yalniz Ege degil TUM pruvo3d.com yayini durur.
    ("M3 duzeltilmis satir", YENI_SATIR, False, "dort sarti da saglayan metin YESIL olmali"),
    ("M4 teshis fotosu",
     "- Ne olduğunu anlamak için tek bir net fotoğraf ya da ek açı isteyebilirsin.",
     False, "TESHIS fotosu SERBEST (:52 istisnasi) — kapi buna dokunmamali"),
    ("M5 kosul sorma",
     "- motor/ısı → kaç dereceye dayanmalı sor · yük/darbe → tok+sağlam.",
     False, "KOSUL sormak :12 ile serbest — olcu degil"),
    ("M8 isi araligindaki 'yaklasik'",
     "- ısı dayanımı = HDT @ 0.45 MPa, yaklaşık aralık; abartma, taahhüt sayılır.",
     False, "'yaklasik' PARA jetonu olmadan fiyat sozu degildir"),
    ("M9 olumsuz emir", "- Müşteriden ölçü isteme, çizim toplama.", False,
     "olumsuz kipte yasak metni YESIL olmali"),
    ("M11 'sorun' homografi", "- Ölçüyle ilgili bir sorun olursa [DEVRET] yap.",
     False, "'sorun'=problem ismi; emir sanilirsa TUM SITE yayini durur"),
    ("M12 arayuz betimlemesi", "- Sepette yaklaşık tutar ödeme öncesi görünür.",
     False, "BETIMLEME (gorunur), taahhut DEGIL"),
    ("M13 sabit ucret betimlemesi",
     "- Kargo ücreti yaklaşık 250 TL olarak sepete eklenir.", False,
     "BETIMLEME (eklenir), taahhut DEGIL"),
    ("M14 belgenin KENDI l.9 kargo cumlesi", BELGE_L9, False,
     "canli mesru metin — bu sinif (C)'ye bir tik uzakta, kirmizi yanmamali"),
    ("M15 belgenin KENDI l.11 'netlestir' dili", BELGE_L11, False,
     "mesru ic refleks; ISTEK fiili degil"),
    ("M21 duz kesin fiyat = ILAN EDILMIS KOR NOKTA", "- Bu parça 1.200 TL.", False,
     "KAPSAM DISI ve OYLE ILAN EDILDI — burayi 'duzeltmek' belgenin l.9'unu "
     "sahte-kirmizi yakar ve tum siteyi durdurur"),
]


def ic_nobetci():
    print("EGE KABILIYET KAPISI — IC NOBETCI (kirmizi-mutasyon)")
    print("=" * 70)
    gecen = 0
    kalan = []
    i = 0
    while i < len(FIKSTURLER):
        ad, metin, kirmizi_bekle, aciklama = FIKSTURLER[i]
        b = bulgular(metin)
        oldu = len(b) > 0
        ok = (oldu == kirmizi_bekle)
        print("  [%s] %-42s bekleniyor=%-7s gercek=%-7s" % (
            "OK" if ok else "HATA", ad,
            "KIRMIZI" if kirmizi_bekle else "YESIL",
            "KIRMIZI" if oldu else "YESIL"))
        print("        %s" % aciklama)
        if b:
            j = 0
            while j < len(b):
                print("        -> [%s] %s" % (b[j][1], b[j][2][:110]))
                j += 1
        if ok:
            gecen += 1
        else:
            kalan.append(ad)
        i += 1
    print("=" * 70)
    print("  %d/%d fikstur gecti" % (gecen, len(FIKSTURLER)))
    if kalan:
        print("  KIRMIZI — gecemeyen: %s" % ", ".join(kalan))
        return 1
    print("SONUC: YESIL ✅ — kapi hem yakaliyor hem yanlis-pozitif uretmiyor.")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--dosya", default=VARSAYILAN)
    ap.add_argument("--ic-nobetci", action="store_true", dest="ic")
    a = ap.parse_args()

    if a.ic:
        return ic_nobetci()

    try:
        metin = open(a.dosya, "rb").read().decode("utf-8")
    except OSError as e:
        print("okunamadi: %s" % e)
        return 2

    b = olcumu_bas(a.dosya, metin)
    ne_olculmedi()
    print()
    if b:
        print("SONUC: KIRMIZI ❌ — %d bulgu. ege-bilgi.md, Ege'nin canli talimatiyla "
              "CELISEN bir kabiliyet/fiyat sozu iceriyor." % len(b))
        print("  Dogrusu: tani -> katalogdakine yonlendir -> yoksa arastirip donecegini")
        print("  soyle + [DEVRET]. Olcu/cizim isteme, uretim/fiyat sozu verme.")
        return 1
    # 🔴 "fiyat sozu YOK" DEME — kapi duz kesin fiyat beyanini OLCMUYOR.
    # Bir kapi olcmedigi seyi olcmus gibi raporlayamaz (mimar hukmu 26 Tem).
    print("SONUC: YESIL ✅ — aranan uc kalip BULUNAMADI:")
    print("  (A) olcu/cizim istegi · (B) uretim sozu · (C) YAKLASIK/tahmini fiyat taahhudu")
    print("  ⚠️  BU 'fiyat sozu yok' DEMEK DEGILDIR: duz kesin fiyat beyani")
    print("      ('Bu parca 1.200 TL') bu kapiyla OLCULMEZ — ustteki listeye bak.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
