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
  (C) FIYAT SOZU: kesin VEYA yaklasik/tahmini fiyat taahhudu
Uctu; dordunculeri buraya EKLEME. Kapsam buyutmek pozitif nobetciyi sessizce
oldurur (olculdu, bu repoda: [[kapi-kapsam-genisletme-tuzagi]]).

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
    r"ölçü|ölçüler|çizim|teknik\s+detay|teknik\s+çizim|\bmm\b|kumpas"
    r"|merkez-\s*merkez|şerit\s*metre",
    re.IGNORECASE)

# ISTEK fiili — YALNIZ musteriden girdi talep eden EMIR kipleri.
# "netleştir" BILEREK YOK: l.11 ("ölçü/koşul belirsizse önce netleştir") mesru bir
# ic reflekstir, musteriden olcu talebi degil. Bu bir KOR NOKTA, asagida ilan edilir.
ISTEK_RE = re.compile(
    r"\biste\b|\bisteyin\b|\bistersin\b|\btopla\b|\btoplayın\b|\baldır\b"
    r"|\bölçtür\b|\bölçün\b|\bgönder\b|\bgönderin\b|\bgöndersin\b"
    r"|\biletin\b|\byazın\b|\bpaylaşın\b|\bsor\b|\bsorun\b",
    re.IGNORECASE)

# URETIM SOZU — 1. cogul taahhut kipi. "üretilir/üretip/üretiyoruz/ürettiğimiz"
# BILEREK YOK: bunlar firma-kimligi/akis anlatimidir ve SISTEM_TALIMATI:2467 kimlik
# cumlesini ACIKCA serbest birakir ("ozel uretim yapan bir firmayiz, AMA ... sozunu
# SEN verme"). Yasak olan, MUSTERININ PARCASI icin verilen soz.
URETIM_SOZ_RE = re.compile(
    r"\büretiriz\b|\büretebiliriz\b|\büretiveririz\b|\byaparız\b|\bbasarız\b"
    r"|\btasarlarız\b|sıfır\s+toleransla",
    re.IGNORECASE)

# FIYAT SOZU — kesin VEYA yaklasik. Yaklasik/tahmini yalniz PARA jetonuna yakinsa
# sayilir (l.22'deki "yaklasik aralik" isi dayanimi icindir, fiyat degil).
YAKLASIK_RE = re.compile(r"yaklaşık|tahmini|aşağı\s*yukarı|civarında", re.IGNORECASE)
PARA_RE = re.compile(r"\bfiyat|\bTL\b|\btutar|\bücret|\bmaliyet", re.IGNORECASE)
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

# Cumlecik ayirici: nokta/noktali virgul/virgul + satir sonu.
CUMLECIK_AYIRICI = re.compile(r"[.;,]|\n")


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
                if FIYAT_SOZ_RE.search(c) or (YAKLASIK_RE.search(c) and PARA_RE.search(c)):
                    out.append((no, "C/FIYAT-SOZU", c,
                                "kesin ya da yaklasik fiyat taahhudu "
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
        print("  Kapsam: (A) olcu/cizim ISTEGI · (B) uretim sozu · (C) fiyat sozu")
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
  · Bu kapi PROSE ONAYI VERMEZ. Yesil = "bilinen uc yasak sozdizimi yok" demektir;
    "metin dogru" demek DEGILDIR. Bu repoda olculdu: anlami tersine ceviren 25
    mutasyonun 22'si kelime arayan testten YESIL gecti.
  · KOR NOKTA — "netleştir": l.11 "ölçü/koşul belirsizse önce netleştir" ISTEK
    fiili saymaz (mesru ic refleks kabul edildi). Biri olcu talebini "netleştir"
    diye yazarsa bu kapi GORMEZ. Bilincli sinir; genisletmek l.11/l.18/l.38'i
    sahte-kirmizi yakar.
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

FIKSTURLER = [
    # (ad, metin, KIRMIZI_bekleniyor_mu, aciklama)
    ("M1 eski dal metni (26 Tem kazasi)", ESKI_DAL_SATIR, True,
     "'olcu/cizim iste' EMRI — ayni satirda 'verme' olmasina ragmen yakalanmali "
     "(satir duzeyi olumsuzlama maskeleme testi)"),
    ("M2 main eski l.43", MAIN_SATIR, True, "'yoksa ozel uretiriz' = uretim taahhudu"),
    ("M3 duzeltilmis satir", YENI_SATIR, False, "dort sarti da saglayan metin YESIL olmali"),
    ("M4 teshis fotosu (yanlis-pozitif testi)",
     "- Ne olduğunu anlamak için tek bir net fotoğraf ya da ek açı isteyebilirsin.",
     False, "TESHIS fotosu SERBEST (:52 istisnasi) — kapi buna dokunmamali"),
    ("M5 kosul sorma (yanlis-pozitif testi)",
     "- motor/ısı → kaç dereceye dayanmalı sor · yük/darbe → tok+sağlam.",
     False, "KOSUL sormak :12 ile serbest — olcu degil"),
    ("M6 mm degeri isteme",
     "- Deliğin çapını mm olarak gönderin, ona göre üretelim.", True,
     "'mm ... gonderin' = olcu talebi"),
    ("M7 yaklasik fiyat", "- Yaklaşık 800 TL tutar, ona göre planlayın.", True,
     ":57 'yaklasik su kadar tutar' DEME"),
    ("M8 isi araligindaki 'yaklasik' (yanlis-pozitif testi)",
     "- ısı dayanımı = HDT @ 0.45 MPa, yaklaşık aralık; abartma, taahhüt sayılır.",
     False, "'yaklasik' PARA jetonu olmadan fiyat sozu degildir"),
    ("M9 olumsuz emir", "- Müşteriden ölçü isteme, çizim toplama.", False,
     "olumsuz kipte yasak metni YESIL olmali"),
    ("M10 kumpasla olctur", "- Kumpasla merkez-merkez mesafeyi ölçtür ve yaz.", True,
     "kumpas/merkez-merkez olcu talebi"),
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
    print("SONUC: YESIL ✅ — (A) olcu/cizim istegi, (B) uretim sozu, (C) fiyat sozu YOK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
