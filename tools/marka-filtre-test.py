#!/usr/bin/env python3
r"""KABUL TESTI — marka TAM-KELIME (\bMARKA\b) arama filtresi.

Sorun (Ford derin pull, 2026-07-18): marka aramasi basligi ALT-DIZE eslesen
alakasiz urunleri getiriyor ("Oxford", "afford", "Food" -> 896/1214 gurultu);
maraba kendi filtresini kurmak zorunda kaldi. Cozum: printables-api.py'de
marka_kelime_gecer(baslik, marka) -> baslikta marka Unicode kelime siniriyla
(\bMARKA\b, Turkce-duyarli, buyuk/kucuk duyarsiz) geciyorsa True.

Bu test:
  1. marka_kelime_gecer'i karisik basliklarla sinar (Ford GECER, Oxford/afford/Food ELENIR).
  2. printables-ara.py VE thing-ara.py'nin ayni fonksiyonu KULLANDIGINI dogrular
     (kaynak-grep: filtre gercekten baglanmis mi — birinde unutulursa yakalanir).

Calistir:  python3 tools/marka-filtre-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


IDDIA = []          # olculen iddia sayisi — batarya KUCULURSE gorulsun diye basilir


def check(ad, kosul):
    IDDIA.append(ad)
    if not kosul:
        FAILS.append(ad)
        print("TEST KALDI:", ad, file=sys.stderr)


pr = _load("printables-api.py", "pr_api")
gec = pr.marka_kelime_gecer

# --- 1. Fonksiyon davranisi: karisik baslik listesi ---------------------------
# "Ford" markasi: tam kelime GECER, alt-dize ELENIR.
GECMELI_FORD = [
    "Ford Focus orta konsol duzenleyici",
    "ford fiesta debriyaj pedali",          # kucuk harf
    "FORD Transit kapi tutamaci",           # buyuk harf
    "Kapak (Ford Focus icin)",              # parantez/kelime-ortasi degil
    "Ford-Focus vites korukleme",           # tire ile sinir
    "yeni ford",                            # baslik sonu
]
ELENMELI_FORD = [
    "Oxford pen holder",                    # alt-dize: ...ford...
    "I can afford this bracket",            # alt-dize: af-ford
    "Food container lid",                   # hic ilgisiz
    "Stanford lab mount",                   # alt-dize
    "Bradford bike clip",                   # alt-dize
    "fordable box",                         # kelime-ici (ford + able)
]
for t in GECMELI_FORD:
    check("Ford GECMELI: %r" % t, gec(t, "Ford") is True)
for t in ELENMELI_FORD:
    check("Ford ELENMELI: %r" % t, gec(t, "Ford") is False)

# Turkce-duyarli buyuk/kucuk: "BMW" vs govde; ve Turkce I/İ katmani
check("BMW tam kelime gecer", gec("BMW e46 far braketi", "BMW") is True)
check("BMW alt-dize elenir", gec("ABMWX rastgele", "BMW") is False)

# Cok kelimeli marka: "Alfa Romeo" tam ifade
check("Alfa Romeo gecer", gec("Alfa Romeo Giulia kalorifer", "Alfa Romeo") is True)
check("Alfa (tek) Romeosuz gecmez-degil", gec("Alfa Romeo Giulia", "Alfa") is True)  # "Alfa" tek kelime de var
check("Romeo baska baglamda elenir", gec("Romeo and Juliet statue", "Alfa Romeo") is False)

# Kisa/bos marka -> filtre uygulanmaz (asiri eleme onlenir): True
check("bos marka filtre yok", gec("herhangi baslik", "") is True)
check("tek harf marka filtre yok", gec("X-wing", "X") is True)

# Turkce karakterli marka kelime siniri (ı ç ş): "Şahin" govde icinde degilse elenir
check("Turkce marka tam kelime", gec("Şahin torpido kapagi", "Şahin") is True)
check("Turkce marka alt-dize elenir", gec("Kırşahinler kutu", "Şahin") is False)

# --- 1b. TUMU-BUYUK LATIN MARKA ADI (2026-08-04 kusuru) -----------------------
# KUSUR: tr_lower 'I'->'ı' cevirir (Turkce'de DOGRU); ama TUMU-BUYUK yazilmis LATIN marka
# adinda YANLIS -> 'NISSAN' -> 'nıssan', 'nissan' ile eslesmez. Canlida IKI KEZ goruldu
# (Nissan x MakerWorld, Nissan x Printables). Zarar tesadufen 0 kaldi; alarm YOKTU.
# FIX: marka_katlamalari() — Turkce katlama HER ZAMAN, latin katlama marka adinda 'ı'/'İ'
# YOKSA EK OLARAK denenir. Asagida IKI YON de nobetlenir (tek yon = olu nobetci).
# DIKKAT: yalnizca marka adinda 'I' GECEN markalar kusurluydu ('I'->'ı'). 'SKODA'/'BMW'
# gibi I'siz markalar ESKIDEN DE calisiyordu -> onlar POZITIF degil KONTROL vakasidir
# (asagida ayri). Kusur vakasini I'siz markayla karistirmak mutasyon kanitini korlestirir.
POZITIF_BUYUK = [                                # ONCE KIRMIZI idi (hepsi False donuyordu)
    ("NISSAN GTR arka klips", "nissan"),
    ("MITSUBISHI Lancer torpido klipsi", "mitsubishi"),
    ("FIAT Egea konsol kapagi", "fiat"),
    ("MINI Cooper bardaklik", "mini"),
    ("CITROEN C3 kapi tutamaci", "citroen"),
]
for t, m in POZITIF_BUYUK:
    check("TUMU-BUYUK latin marka GECMELI: %r ~ %r" % (t, m), gec(t, m) is True)

# KONTROL: 'I' TASIMAYAN TUMU-BUYUK marka eskiden de geciyordu, hala gecmeli.
KONTROL_BUYUK = [("SKODA Octavia menteşe", "skoda"), ("FORD Transit kapak", "ford"),
                 ("BMW E46 far braketi", "bmw")]
for t, m in KONTROL_BUYUK:
    check("KONTROL (I'siz) TUMU-BUYUK marka GECMELI: %r ~ %r" % (t, m), gec(t, m) is True)

# Karisik/kucuk yazim REGRESYONU: eskiden de calisiyordu, hala calismali.
check("regr: karisik yazim", gec("Nissan GTR arka klips", "nissan") is True)
check("regr: kucuk yazim", gec("nissan gtr arka klips", "NISSAN") is True)
# Alt-dize gurultusu HALA elenmeli (gevsetme kelime-sinirini DELMEDI).
check("regr: alt-dize NISSAN icinde", gec("UNISSANO parca", "nissan") is False)

# NEGATIF NOBET — Turkce I/ı ayrimi KORUNUYOR mu? (tek yonlu test = olu nobetci)
# 'kısa' (noktasiz ı) ile 'kisa' (noktali i) FARKLI kelimelerdir; eslesmemeli.
# Bu iddia, "aksani soy / ı->i normalize et" seklindeki NAIF fixi KIRMIZI yakar.
check("TR ayrim: 'kısa kollu' ~ 'kisa' ESLESMEMELI",
      gec("kısa kollu kutu", "kisa") is False)
check("TR ayrim: 'kisa devre' ~ 'kısa' ESLESMEMELI",
      gec("kisa devre kapagi", "kısa") is False)
check("TR ayrim: 'ışıklı panel' ~ 'isikli' ESLESMEMELI",
      gec("ışıklı panel", "isikli") is False)
# Turkce katlama HALA calisiyor: TUMU-BUYUK Turkce sozcuk -> Turkce okunusuyla eslesir.
check("TR katlama: 'IŞIK lamba' ~ 'ışık' ESLESMELI", gec("IŞIK lamba", "ışık") is True)
# Marka adinda 'İ' varsa latin katlama DENENMEZ -> Turkce semantik bozulmaz.
check("TR ayrim: 'ISTANBUL plaka' ~ 'İstanbul' ESLESMEMELI",
      gec("ISTANBUL plaka", "İstanbul") is False)

# --- 1c. KIRMIZI-MUTASYON (defect 1) ------------------------------------------
# Mutantlar CANLI dosyaya DOKUNMAZ; burada birebir yeniden yazilir ve KIRMIZI yakmalari
# olculur. Mutasyon kaniti yeniden-uretilebilir olsun diye surucu repoda durur.
def _mut_eski_katlama(baslik, marka):
    """MUTANT 1 = FIX ONCESI hal (yalniz tr_lower). POZITIF_BUYUK vakalarini KACIRMALI."""
    m = pr.tr_lower(marka).strip()
    if len(m) < 2:
        return True
    return re.search(r"\b%s\b" % re.escape(m), pr.tr_lower(baslik), re.UNICODE) is not None


def _mut_aksan_soy(baslik, marka):
    """MUTANT 2 (NAIF ALTERNATIF FIX) = 'ı'yi 'i'ye katla, yani Turkce ayrimi YOK ET.
    POZITIF vakalari GECIRIR ama TR-ayrim vakalarini yanlislikla ESLESTIRIR -> KIRMIZI."""
    def katla(s):
        return (s or "").replace("İ", "i").replace("I", "i").lower().replace("ı", "i")
    m = katla(marka).strip()
    if len(m) < 2:
        return True
    return re.search(r"\b%s\b" % re.escape(m), katla(baslik), re.UNICODE) is not None


def _mut_kontrol(baslik, marka):
    """KONTROL MUTANT = davranissal olarak CANLI kodun AYNISI (latin katlamada 'I'->'i'
    Python varsayilani yerine ACIKCA yazildi). YESIL KALMALI — kalmiyorsa batarya
    davranisi degil kaynak metnini olcuyor demektir."""
    def tr(s):
        return (s or "").replace("İ", "i").replace("I", "ı").lower()

    def lat(s):
        return (s or "").replace("İ", "i").replace("I", "i").lower()
    ham = marka or ""
    ciftler = [(tr(ham).strip(), tr)]
    if "ı" not in ham and "İ" not in ham:
        ciftler.append((lat(ham).strip(), lat))
    if len(ciftler[0][0]) < 2:
        return True
    for m, katla in ciftler:
        if re.search(r"\b%s\b" % re.escape(m), katla(baslik), re.UNICODE):
            return True
    return False


TR_AYRIM = [("kısa kollu kutu", "kisa"), ("kisa devre kapagi", "kısa"),
            ("ışıklı panel", "isikli"), ("ISTANBUL plaka", "İstanbul")]

# MUT-1 KIRMIZI kaniti: eski katlama TUMU-BUYUK vakalarin EN AZ birini kacirmali.
_m1_kacan = [t for t, m in POZITIF_BUYUK if _mut_eski_katlama(t, m) is not True]
check("MUT-1 (eski katlama) TUM pozitif vakalari KACIRMALI", len(_m1_kacan) == len(POZITIF_BUYUK))
check("MUT-1 canli kod YESIL", all(gec(t, m) is True for t, m in POZITIF_BUYUK))
# MUT-1 AYIRT EDICI mi: kontrol vakalarini (I'siz marka) mutant da GECIRMELI. Gecirmiyorsa
# mutant her seyi kiriyordur ve "kusuru yakaladi" kaniti degersizdir.
check("MUT-1 ayirt edici (I'siz kontrol vakalari mutantta da YESIL)",
      all(_mut_eski_katlama(t, m) is True for t, m in KONTROL_BUYUK))

# MUT-2 KIRMIZI kaniti: aksan-soyan naif fix TR-ayrim vakalarini yanlis eslestirmeli.
_m2_yanlis = [t for t, m in TR_AYRIM if _mut_aksan_soy(t, m) is True]
check("MUT-2 (aksan-soy) KIRMIZI yakmali", len(_m2_yanlis) > 0)
check("MUT-2 canli kod TR-ayrimi koruyor", all(gec(t, m) is False for t, m in TR_AYRIM))

# KONTROL MUTANT: TUM iddialarda canli kodla AYNI cevabi vermeli -> YESIL kalir.
_kontrol_sapma = [(t, m) for t, m in (POZITIF_BUYUK + TR_AYRIM)
                  if _mut_kontrol(t, m) != gec(t, m)]
check("KONTROL MUTANT YESIL kalmali (sapma yok)", not _kontrol_sapma)

# --- 1d. KOSULLU DUVAR-SUSU: VARSAYILAN RED, gevsetme POZITIF KANITA bagli -------
# KUSUR 3 ve onun ILK (yanlis) onarimi:
#   base   : "wall art" KOSULSUZ eliyordu -> logosuz gercek siluet de eleniyordu.
#   1. fix : "logo/wordmark sinyali varsa ele, yoksa GECIR" -> kapi FAIL-OPEN oldu.
#            Logoyu HALK DILIYLE adlandiran 15 baslik base'de eleniyordu, o halde ELENMIYORDU.
#   2. fix : VARSAYILAN ELE; RED'i yalniz POZITIF SILUET KANITI deler ve o da
#            logo/wordmark/sembol-adi sinyali YOKKEN. Supheli = RED.
# 🚫 Politika (Okan, 2026-07-20) baglayici: baskida logo/wordmark tasiyan urun EKLENMEZ.
# ⚠️ Gorsel kapisi bu depoda DOGRULANAMIYOR -> "savunma derinligi" kanit sayilmaz; metin
#    kapisi TEK BASINA fail-closed olmali. Asagidaki 15 baslik bunun nobetidir.

# (a) NEGATIF NOBET — curutmede sizan 15 basligin TAMAMI ELENMELI.
SIZAN_15 = [
    "Audi rings wall art", "Mercedes star wall art", "Peugeot lion wall art",
    "Ferrari cavallino wall art", "Alfa Romeo shield wall art", "Porsche crest wall art",
    "BMW propeller wall art", "Lamborghini bull wall art", "Cadillac wreath wall art",
    "Bentley winged b wall art", "Mini wings wall art", "Subaru stars wall art",
    "Toyota ellipses wall art", "Audi four rings", "Mercedes three pointed star",
]
for t in SIZAN_15:
    check("SIZAN-15 ELENMELI: %r" % t, pr.is_nobypass(t) is True)
check("SIZAN-15 hepsi elendi (15/15)", sum(1 for t in SIZAN_15 if pr.is_nobypass(t)) == 15)

# (b) POZITIF NOBET — GERCEK canli Printables basliklari (9 sorgu / 233 baslik olcumunden
#     alindi, uydurma DEGIL). Tek yon = olu nobetci; bunlar ELENMEMELI.
SILUET_GERCEK = [
    "Porsche Carrera 911 (992) Silhouette Wall Art",
    "BMW E90 Car Outline Wall Art",
    "Japanese Car Wall decoration Line Art JDM",
    "Car silhouette wall art - Ford Mustang GT3 2024",
    "BMW E36 Style Car Silhouette – Flat Automotive Wall Art",
    "Car silhouette wall art - DMC Delorean back to the future",
]
for t in SILUET_GERCEK:
    check("SILUET GECMELI: %r" % t[:52], pr.is_nobypass(t) is False)
check("SILUET hepsi gecti (6/6)", sum(1 for t in SILUET_GERCEK if not pr.is_nobypass(t)) == 6)

# (c) KANIT var AMA sembol adi/logo da var -> RED kazanir (sira nobeti).
for t in ("Audi four rings silhouette wall art", "Mercedes star silhouette wall art",
          "Nissan logo silhouette wall art", "Ferrari cavallino outline wall art"):
    check("KANIT+SEMBOL yine ELENIR: %r" % t, pr.is_nobypass(t) is True)

# (d) Kanitsiz duvar-susu (temiz gorunse bile) ELENIR — fail-closed varsayilan.
for t in ("Nissan GTR wall art", "Porsche Carrera GT Wall Art", "Classic Car Wall art"):
    check("KANITSIZ duvar-susu ELENIR: %r" % t, pr.is_merch(t) is True)

# (e) KONTROL: kosulsuz merch listesi DEGISMEDI.
for t in ("BMW keychain", "Audi keyring", "Ford anahtarlik", "VW wall plaque",
          "Opel trophy", "Seat fridge magnet", "Renault sticker"):
    check("kosulsuz merch HALA elenir: %r" % t, pr.is_merch(t) is True)
check("logo tek basina HALA elenir", pr.is_logo("Nissan emblem") is True)
# (f) KONTROL: duvar-susu terimi GECMEYEN sira disi urun etkilenmedi (kapsam sizmasi yok).
for t in ("Nissan GTR kaput klipsi", "Ford Focus konsol duzenleyici",
          "Yildiz tornavida ucu", "Marine propeller shaft anode"):
    check("duvar-susu DISI urun etkilenmedi: %r" % t, pr.is_merch(t) is False)


def _mut_fail_open(name):
    """MUTANT 3 = ILK (CURUTULEN) onarim: kosullu terim varsa yalniz logo/wordmark eler,
    yoksa GECIRIR (fail-open). SIZAN_15'i gecirmeli -> KIRMIZI."""
    n = " " + (name or "").lower() + " "
    if any(c in n for c in pr.COP_MERCH):
        return True
    if any(c in n for c in pr.COP_MERCH_KOSULLU):
        return pr.is_logo(name) or pr.is_wordmark(name)
    return False


def _mut_kanitsiz_gecir(name):
    """MUTANT 4 = sembol-adi katmanini KALDIR (yalniz kanit ara). 'Audi four rings
    silhouette wall art' gibi KANIT+SEMBOL vakalarini gecirmeli -> KIRMIZI."""
    n = " " + (name or "").lower() + " "
    if any(c in n for c in pr.COP_MERCH):
        return True
    if any(c in n for c in pr.COP_MERCH_KOSULLU):
        if pr.is_logo(name) or pr.is_wordmark(name):
            return True
        return not pr.is_siluet_kaniti(name)
    return False


def _mut_merch_kontrol(name):
    """KONTROL MUTANT = canli is_merch ile DAVRANISSAL olarak ayni; kosulsuz listeye
    fikstyurde HIC gecmeyen bir terim, kanit listesine de hic gecmeyen bir terim eklendi.
    YESIL kalmali — kalmiyorsa batarya davranisi degil kaynak metnini olcuyor."""
    n = " " + (name or "").lower() + " "
    if any(c in n for c in (pr.COP_MERCH + ("bobblehead",))):
        return True
    if any(c in n for c in pr.COP_MERCH_KOSULLU):
        if pr.is_logo(name) or pr.is_wordmark(name) or pr.is_sembol_adi(name):
            return True
        return not (pr.is_siluet_kaniti(name)
                    or "zzz-olmayan-terim" in n)
    return False


TUM_MERCH_VAKA = SIZAN_15 + SILUET_GERCEK + [
    "Audi four rings silhouette wall art", "Nissan GTR wall art", "BMW keychain",
    "VW wall plaque", "Nissan GTR kaput klipsi"]

# MUT-3 (fail-open, curutulen onarim): SIZAN_15'in COGUNU gecirmeli.
_m3_sizan = [t for t in SIZAN_15 if _mut_fail_open(t) is False]
check("MUT-3 (fail-open) KIRMIZI yakmali — SIZAN_15 sizmali", len(_m3_sizan) >= 13)
check("MUT-3 canli kod SIZAN_15'i ELIYOR", all(pr.is_nobypass(t) for t in SIZAN_15))
# MUT-3 AYIRT EDICI mi: gercek siluet basliklarini mutant da GECIRMELI (her seyi kirmiyor).
check("MUT-3 ayirt edici (gercek siluet mutantta da geciyor)",
      all(_mut_fail_open(t) is False for t in SILUET_GERCEK))

# MUT-4 (sembol-adi katmani yok): KANIT+SEMBOL vakasini gecirmeli.
# ⚠️ Fikstyur SECIMI onemli: "four rings"/"cavallino" GLOBAL COP_LOGO'da oldugundan mutant
# onlari yine eler ve katmani AYIRT ETMEZ. Ayirt edici fikstyur, sembol adi YALNIZ
# COP_SEMBOL_ADI'nda olan basliktir ("star" globalde YOK, baglamda VAR).
MUT4_AYIRTEDICI = "Mercedes star silhouette wall art"
check("MUT-4 fikstyuru gercekten ayirt edici (sembol GLOBAL logoda degil)",
      pr.is_logo(MUT4_AYIRTEDICI) is False and pr.is_sembol_adi(MUT4_AYIRTEDICI) is True)
check("MUT-4 (sembol katmani yok) KIRMIZI yakmali",
      _mut_kanitsiz_gecir(MUT4_AYIRTEDICI) is False)
check("MUT-4 canli kod KANIT+SEMBOL'u ELIYOR", pr.is_merch(MUT4_AYIRTEDICI) is True)
# MUT-4 ayirt edici mi: kanitsiz duvar-susunu mutant da ELEMELI (her seyi gecirmiyor).
check("MUT-4 ayirt edici (kanitsiz duvar-susu mutantta da eleniyor)",
      _mut_kanitsiz_gecir("Nissan GTR wall art") is True)

# KONTROL MUTANT: TUM vakalarda canli kodla ayni cevap -> YESIL kalir.
_merch_kontrol_sapma = [t for t in TUM_MERCH_VAKA if _mut_merch_kontrol(t) != pr.is_merch(t)]
check("KONTROL MUTANT (merch) YESIL kalmali (sapma yok)", not _merch_kontrol_sapma)

# --- 1e. B2: LISTEDE OLMAYAN sembol adi + KANIT sozcugu (2. curutme turu) ---------
# KUSUR: "sinyal once, kanit sonra" sirasi DOGRU calisiyordu ama SEMBOL ADI LISTESI eksikti.
# Kapi olctu: listede olmayan sembol adi + kanit sozcugu -> 75 denemede 70 KACAK.
# ONARIM: 13 ad GLOBAL COP_LOGO'ya eklendi. Olcut DEGISMEDI (tek anlamli + katalogda 0 vurus):
# 13'unun de katalog vurusu 0 (18.080 kayit, baslik+aciklama). Belirsizler (star 156, bull 14,
# shield 6) BILEREK baglamda kaldi; "propeller" katalogda 0 olsa da EN metinde gercek marin
# parca adi oldugu icin global'e ALINMADI.
B2_YENI_ADLAR = ("bowtie", "bow tie", "biscione", "scorpion", "pleiades", "blitz",
                 "coat of arms", "leaper", "ram head", "three diamonds", "winged arrow",
                 "tri shield", "prancing pony")
# Capa: 13 ad GERCEKTEN global COP_LOGO'da mi (baglam listesinde DEGIL)?
for _ad in B2_YENI_ADLAR:
    check("13 ad GLOBAL COP_LOGO'da: %r" % _ad, _ad in pr.COP_LOGO)
check("13 ad baglam listesine SIZMADI",
      not [a for a in B2_YENI_ADLAR if a in pr.COP_SEMBOL_ADI])
# Kiyas capasi: bilerek BAGLAMDA birakilanlar global'e TASINMADI (o karar degismedi).
for _ad in ("star", "bull", "shield", "propeller"):
    check("belirsiz ad BAGLAMDA kaldi: %r" % _ad,
          _ad in pr.COP_SEMBOL_ADI and _ad not in pr.COP_LOGO)

B2_PARLAR = [
    ("Chevrolet", "bowtie"), ("Chevrolet", "bow tie"), ("Abarth", "scorpion"),
    ("Fiat", "scorpion"), ("Alfa Romeo", "biscione"), ("Porsche", "coat of arms"),
    ("Mitsubishi", "three diamonds"), ("Jaguar", "leaper"), ("Dodge", "ram head"),
    ("Subaru", "pleiades"), ("Opel", "blitz"), ("Vauxhall", "blitz"),
    ("Skoda", "winged arrow"), ("Buick", "tri shield"), ("Ford", "prancing pony"),
]
B2_KANIT = ["silhouette", "outline", "line art", "stencil", "side view"]
B2 = ["%s %s %s wall art" % (m, sem, k) for (m, sem) in B2_PARLAR for k in B2_KANIT]
for t in B2:
    check("B2 ELENMELI: %r" % t, pr.is_nobypass(t) is True)
check("B2 batarya boyutu 75", len(B2) == 75)
check("B2 hepsi elendi (75/75)", sum(1 for t in B2 if pr.is_nobypass(t)) == 75)
# POZITIF koruma: 13 ad eklendi diye GERCEK siluet basliklari olmemeli.
check("B2 eklemesi gercek silueti OLDURMEDI (6/6 hala geciyor)",
      sum(1 for t in SILUET_GERCEK if not pr.is_nobypass(t)) == 6)
check("gercek siluet basliklari 13 adin HICBIRINI tasimiyor (fikstyur bagimsiz)",
      not [t for t in SILUET_GERCEK
           if any(a in " " + t.lower() + " " for a in B2_YENI_ADLAR)])

# --- 1f. KALAN B2 KUYRUGU — ILAN EDILMIS SURVIVOR (kapatilMADI, GIZLENMEDI) --------
# 🔴 NEDEN BU BLOK VAR: yukaridaki B2 bataryasi (B2_PARLAR) ONARIMDAN SONRA, eklenen 13
# ada gore yeniden yazildi. Bu haliyle batarya YALNIZ duzeltilen adlari sinar -> "75/75
# elendi" TOTOLOJIYE yakin durur ve kalan kuyrugu GIZLER ([[test-hatali-davranisi-kutsar]],
# [[beyan-edilmis-survivor]]). Bagimsiz olcum (merge kapisi, 2026-08-04) ILK B2 kumesiyle
# kosuldugunda 75 denemenin 20'si HALA KACIYOR: sembol adlari `pony` · `ovals` · `flag` ·
# `laurel`. Bunlar 13'un DISINDA kaldi.
#
# 🔴 NEDEN KAPATILMADI (liste kovalama burada BITIYOR — olculdu):
#   * `pony`   -> katalogda 2 vurus  (belirsiz: "pony car"/oyuncak) -> global'e KONAMAZ
#   * `laurel` -> katalogda 1 vurus  (defne motifi)                 -> global'e KONAMAZ
#   * `flag`   -> katalog 0 ama EN'de tamamen genel (yaris/ulke bayragi); global elese
#                 mesru bayrak duvar susunu olduru
#   * `ovals`  -> katalog 0; tek basina eklenebilirdi ama yalniz bu kuyrugun 1/4'unu kapatir
#   Yani kalan kuyruk METIN kapisinin INDIRGENEMEZ artigidir; kapatmak icin sonsuz sembol
#   listesi gerekir. Bilinen ve ILAN EDILEN bir bosluktur.
#
# 🔴 NEDEN KABUL EDILEBILIR: sinifin GERCEK insidansi 0. 448 benzersiz canli baslik
#   (13'u dogrudan bu kuyrugu avlayan dusmanca sorgu: "pony wall art" 40 sonuc, "flag wall
#   art" 16 sonuc dahil) tarandi; kapidan GECEN 111 duvar-susu basliginin HICBIRI bu 4
#   sembol adini marka logosu olarak tasimiyor (vuran 0).
#
# ⚠️ BU BLOK CIRCIRDIR: asagidaki iddia "bu 20 baslik BUGUN GECIYOR" der. Biri kuyrugu
#    kapatirsa (or. `ovals`i global'e eklerse) iddia KIRMIZI yanar ve bu beyanin
#    GUNCELLENMESINI zorlar. Boylece bosluk sessizce ne buyur ne de sessizce kapanir.
B2_KALAN_PARLAR = [("Ford", "pony"), ("Toyota", "ovals"),
                   ("Lancia", "flag"), ("Fiat", "laurel")]
B2_KALAN = ["%s %s %s wall art" % (m, sem, k)
            for (m, sem) in B2_KALAN_PARLAR for k in B2_KANIT]
_kalan_gecen = [t for t in B2_KALAN if not pr.is_nobypass(t)]
check("KALAN B2 kuyrugu batarya boyutu 20", len(B2_KALAN) == 20)
check("ILAN: kalan B2 kuyrugunun 20/20'si BUGUN GECIYOR (bilinen, olculmus bosluk; "
      "gercek insidans 0/448). Bu sayi DEGISTIYSE beyani guncelle.",
      len(_kalan_gecen) == 20)
# Kuyrugun 4 sembol adi GERCEKTEN hicbir listede degil (beyan kaynaktan dogrulanir).
for _ad in ("pony", "ovals", "flag", "laurel"):
    check("kalan kuyruk adi hicbir listede DEGIL: %r" % _ad,
          _ad not in pr.COP_LOGO and _ad not in pr.COP_SEMBOL_ADI)
# AYIRT EDICILIK: kuyruk ACIK logo sozcugu tasiyinca YINE de elenmeli (kapi calisiyor).
check("kalan kuyruk + ACIK logo sozcugu -> HALA ELENIR (kapi olu degil)",
      all(pr.is_nobypass("%s %s logo silhouette wall art" % (m, sem))
          for (m, sem) in B2_KALAN_PARLAR))


def _mut_13ad_yok(name):
    """MUTANT 5 = 13 ad GLOBAL COP_LOGO'ya EKLENMEMIS hali. Bu KATMANI tek basina olcer:
    B2 denemelerini gecirmeli -> KIRMIZI."""
    eski_logo = tuple(c for c in pr.COP_LOGO if c not in B2_YENI_ADLAR)

    def _logo(x):
        n = " " + (x or "").lower() + " "
        return any(c in n for c in eski_logo)

    def _merch(x):
        n = " " + (x or "").lower() + " "
        if any(c in n for c in pr.COP_MERCH):
            return True
        if any(c in n for c in pr.COP_MERCH_KOSULLU):
            if _logo(x) or pr.is_wordmark(x) or pr.is_sembol_adi(x):
                return True
            return not pr.is_siluet_kaniti(x)
        return False
    return _logo(name) or _merch(name) or pr.is_firearm(name)


_m5_kacan = [t for t in B2 if _mut_13ad_yok(t) is False]
check("MUT-5 (13 ad yok) KIRMIZI yakmali — B2 sizmali", len(_m5_kacan) >= 60)
check("MUT-5 canli kod B2'yi ELIYOR", all(pr.is_nobypass(t) for t in B2))
# MUT-5 AYIRT EDICI mi: gercek siluet basliklarini mutant da GECIRMELI (her seyi kirmiyor).
check("MUT-5 ayirt edici (gercek siluet mutantta da geciyor)",
      all(_mut_13ad_yok(t) is False for t in SILUET_GERCEK))
# MUT-5 kapsam nobeti: 13 ad SADECE bu katmani acti, kosulsuz merch'e dokunmadi.
check("MUT-5 kapsam: kosulsuz merch mutantta da eleniyor",
      _mut_13ad_yok("BMW keychain") is True)


def _mut_13ad_kontrol(name):
    """KONTROL MUTANT = COP_LOGO'ya fikstyurde HIC gecmeyen bir ad eklenmis hali.
    Davranis AYNI kalmali -> YESIL."""
    genis = pr.COP_LOGO + ("zzz-olmayan-sembol",)
    n = " " + (name or "").lower() + " "
    logo = any(c in n for c in genis)

    def _merch(x):
        m = " " + (x or "").lower() + " "
        if any(c in m for c in pr.COP_MERCH):
            return True
        if any(c in m for c in pr.COP_MERCH_KOSULLU):
            if logo or pr.is_wordmark(x) or pr.is_sembol_adi(x):
                return True
            return not pr.is_siluet_kaniti(x)
        return False
    return logo or _merch(name) or pr.is_firearm(name)


_m13_sapma = [t for t in (B2 + SILUET_GERCEK + SIZAN_15)
              if _mut_13ad_kontrol(t) != pr.is_nobypass(t)]
check("KONTROL MUTANT (13 ad) YESIL kalmali (sapma yok)", not _m13_sapma)

# --- 2. Iki arama araci da fonksiyonu KULLANIYOR mu (kaynak-grep) --------------
for f in ("printables-ara.py", "thing-ara.py"):
    src = open(os.path.join(DIR, f), encoding="utf-8").read()
    check("%s marka_kelime_gecer cagiriyor" % f, "marka_kelime_gecer" in src)
    check("%s --tam-kelime bayragi var" % f, "--tam-kelime" in src)

# --- 2b. CAPA: fix gercekten CANLI kaynakta ve TEK KOPYA mi? -------------------
# Capa TAM BIR KEZ eslesmeli — ikinci kopya = ikiz tanim = sessiz ayrisma riski.
_api_src = open(os.path.join(DIR, "printables-api.py"), encoding="utf-8").read()
for capa in ("def latin_lower(", "def marka_katlamalari(", "COP_MERCH_KOSULLU = (",
             "COP_WORDMARK = (", "def is_wordmark(", "def obj_bbox("):
    check("printables-api.py capa TAM BIR KEZ: %r" % capa, _api_src.count(capa) == 1)
# tr_lower Turkce yuzeyi icin DEGISMEDEN kalmali (denetim-kapisi/yayin-ic-dil ona bagli).
check("tr_lower Turkce kurali korunuyor",
      'replace("İ", "i").replace("I", "ı").lower()' in _api_src)

# makerworld-ara.py kendi katlama KOPYASINI tutmamali (ikiz tanim tuzagi).
_mw_src = open(os.path.join(DIR, "makerworld-ara.py"), encoding="utf-8").read()
check("makerworld-ara.py kendi _tr_lower kopyasini TUTMUYOR", "def _tr_lower" not in _mw_src)
check("makerworld-ara.py ortak katlamayi cagiriyor TAM BIR KEZ",
      _mw_src.count("_pr.marka_katlamalari(") == 1)

# makerworld-ara.marka_geciyor DAVRANIS nobeti (kaynak-grep tek basina yeterli degil).
_mw_spec = importlib.util.spec_from_file_location("mw_ara", os.path.join(DIR, "makerworld-ara.py"))
_mw = importlib.util.module_from_spec(_mw_spec)
_mw_spec.loader.exec_module(_mw)
check("MW: 'NISSAN GTR' ~ 'nissan' GECER", _mw.marka_geciyor("nissan", "NISSAN GTR") is True)
check("MW: karisik yazim regresyonu", _mw.marka_geciyor("nissan", "Nissan GTR") is True)
check("MW: alt-dize HALA elenir", _mw.marka_geciyor("ford", "Oxford box") is False)
check("MW: TR ayrimi korunuyor", _mw.marka_geciyor("kisa", "kısa kollu kutu") is False)
check("MW: bos marka False", _mw.marka_geciyor("", "herhangi") is False)

if FAILS:
    print("\nIDDIA: %d | KALAN: %d" % (len(IDDIA), len(FAILS)), file=sys.stderr)
    print("\n%d KONTROL KALDI" % len(FAILS), file=sys.stderr)
    sys.exit(1)
print("TEST GECTI — olculen iddia: %d" % len(IDDIA))
sys.exit(0)
