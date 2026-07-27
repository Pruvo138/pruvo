#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — onizleme-imaj.yml "Imaj duman testi" adiminda TOKA duman curl'u.

KANAMA (27 Tem 2026, canlida olculdu): onizleme derleyici imaji toka'siz cikti,
/saglik toka'yi tanimadi, musteri "Onizleme olusturulamadi" gordu. CI YINE YESIL
yandi cunku imaj duman testi toka'yi HIC sormuyordu. Bu test o bosluğu kapatir.

SAF metin/yapi analizi — Docker / R2 / openscad GEREKMEZ. Sadece workflow YML'inin
metnini okur; "Imaj duman testi" adiminin run govdesinde toka duman curl'unun
eksiksiz durdugunu kanitlar.

UC KAT + negatif kontrol:
  (A) YAPISAL          — run govdesinde: toka /derle POST ('"aile":"olcuye-ozel-toka"'),
                         uc parametre (kemer_genisligi + kalinlik + kayis_baglanti),
                         '-o duman-toka.stl', 'wc -c' satirinda duman-toka.stl,
                         sondaki 'test -s' zincirinde 'test -s duman-toka.stl'.
  (B) MUTASYON         — toka curl'u (ve ayrica 'test -s duman-toka.stl') CIKARILAN
                         kopya YAPISAL kontrolu KIRMIZI vermeli. Vermezse kapi
                         lastik damgadir (kor) -> test KIRMIZI.
  (C) YANLIS-POZITIF   — ilgisiz rutin duzenleme (zararsiz yorum + sahte 12. aile
                         curl'u) EKLENEN kopya YAPISAL kontrolu YINE YESIL kalmali.
                         Kalmazsa kapi fazla genis/kirilgan -> test KIRMIZI.
  (NK) NEGATIF KONTROL — checker'in kendisi sentetik IYI govdeyi gecirir, sentetik
                         BOZUK govdeyi reddeder (yapisal_kusurlar ayrimci mi).

Kullanim: python3 onizleme/test/duman_toka_kabul.py
Cikis: 0 = YESIL, 1 = KIRMIZI (her kusur ayri satirda; ne kontrol edildigi basilir).
"""
import os
import re
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
# onizleme/test -> repo koku iki ust dizin
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
YML = os.path.join(REPO, ".github", "workflows", "onizleme-imaj.yml")

ADIM_ADI = "Imaj duman testi"
TOKA_AILE = '"aile":"olcuye-ozel-toka"'
TOKA_PARAMS = ("kemer_genisligi", "kalinlik", "kayis_baglanti")
TOKA_STL = "duman-toka.stl"
DERLE = "/derle"


# ------------------------------------------------------------ metin yardimcilari

def mantiksal_satirlar(metin):
    """Ters-bolu (\\) ile devam eden fiziksel satirlari TEK mantiksal satira birlestirir.
    'wc -c ... \\ ...' ve 'test -s ... \\ ...' zincirleri boylece tek satirda gorunur."""
    out = []
    tampon = ""
    acik = False
    for ham in metin.splitlines():
        s = ham.rstrip("\n")
        govde = s.rstrip()
        if govde.endswith("\\"):
            tampon += govde[:-1].rstrip() + " "
            acik = True
        else:
            tampon += s.strip() if acik else s
            out.append(tampon)
            tampon = ""
            acik = False
    if tampon:
        out.append(tampon)
    return out


def adim_govdesi(metin):
    """"Imaj duman testi" adimini bulur; (adim_metni, run_govdesi) dondurur.
    Adim ya da run govdesi yoksa ilgili deger None olur."""
    satirlar = metin.splitlines()
    bas = None
    for i, s in enumerate(satirlar):
        if re.match(r"^      - name:", s) and ADIM_ADI in s:
            bas = i
            break
    if bas is None:
        return None, None
    # Adim sonu: sonraki '      - ' (ayni girintili yeni adim) ya da job/steps
    # seviyesine (girinti < 6, bos olmayan satir) cikis.
    son = len(satirlar)
    for j in range(bas + 1, len(satirlar)):
        s = satirlar[j]
        if re.match(r"^      - ", s):
            son = j
            break
        if s.strip() and not s.startswith("      "):
            son = j
            break
    adim = satirlar[bas:son]
    # run: | (ya da run: >) govdesi = run anahtarindan daha girintili satirlar.
    run_idx = None
    run_girinti = None
    for k, s in enumerate(adim):
        m = re.match(r"^(\s*)run:\s*[|>]", s)
        if m:
            run_idx = k
            run_girinti = len(m.group(1))
            break
    if run_idx is None:
        return "\n".join(adim), None
    govde = []
    for s in adim[run_idx + 1:]:
        if s.strip() == "":
            govde.append(s)
            continue
        girinti = len(s) - len(s.lstrip(" "))
        if girinti <= run_girinti:
            break
        govde.append(s)
    return "\n".join(adim), "\n".join(govde)


# ------------------------------------------------------------ yapisal denetim

def yapisal_kusurlar(govde):
    """Toka duman curl'unun run govdesinde EKSIKSIZ oldugunu dogrular.
    Kusur listesi dondurur (bos liste = YESIL)."""
    if govde is None:
        return ["run govdesi bulunamadi (adim ya da 'run: |' yok)"]
    kusurlar = []

    if TOKA_AILE not in govde:
        kusurlar.append("toka /derle POST yok: %s gecmiyor" % TOKA_AILE)
    if DERLE not in govde:
        kusurlar.append("%s ucu run govdesinde yok" % DERLE)

    for p in TOKA_PARAMS:
        if p not in govde:
            kusurlar.append("toka govdesinde parametre eksik: %s" % p)

    if ("-o " + TOKA_STL) not in govde:
        kusurlar.append("cikti bayragi yok: -o %s" % TOKA_STL)

    ls = mantiksal_satirlar(govde)
    if not any(("wc -c" in x) and (TOKA_STL in x) for x in ls):
        kusurlar.append("'wc -c' listesinde %s yok" % TOKA_STL)

    hedef = "test -s " + TOKA_STL
    if not any((hedef in x) for x in ls):
        kusurlar.append("sondaki 'test -s' zincirinde '%s' yok" % hedef)

    return kusurlar


# ------------------------------------------------------------ mutasyon uretenler

def mutasyon_toka_curl_cikar(metin):
    """Toka curl'unu (aile -d satiri + '-o duman-toka.stl' satiri) siler."""
    yeni = []
    for s in metin.splitlines():
        if TOKA_AILE in s:
            continue
        if s.strip() == ("-o " + TOKA_STL):
            continue
        yeni.append(s)
    return "\n".join(yeni)


def mutasyon_test_s_cikar(metin):
    """Sondaki zincirden 'test -s duman-toka.stl' parcasini siler."""
    hedef = "test -s " + TOKA_STL
    # Once ' && test -s duman-toka.stl' bicimini, sonra ciplak hedefi kaldir.
    t = metin.replace(" && " + hedef, "")
    t = t.replace(hedef + " && ", "")
    t = t.replace(hedef, "")
    return t


def mutasyon_ilgisiz_ekleme(metin):
    """YANLIS-POZITIF fikstur: run govdesine zararsiz bir yorum + ilgisiz sahte
    12. aile curl'u ekler (toka'ya dokunmadan). Toka yapisal kontrolu YESIL kalmali."""
    ek = (
        "          # rutin yorum (ilgisiz rutin duzenleme — toka'ya dokunmaz)\n"
        "          curl -sf -X POST http://127.0.0.1:18080/derle \\\n"
        "            -H 'Content-Type: application/json' \\\n"
        "            -d '{\"aile\":\"olcuye-ozel-sahte-aile\",\"parametreler\":{\"x\":1}}' \\\n"
        "            -o duman-sahte.stl\n"
    )
    anahtar = "          -o " + TOKA_STL + "\n"
    if anahtar in metin:
        return metin.replace(anahtar, anahtar + ek, 1)
    # Toka -o satiri bulunamazsa wc satirindan once ekle (fikstur yine ilgisiz kalir).
    return re.sub(r"(?m)^(          wc -c )", ek + r"\1", metin, count=1)


# ------------------------------------------------- yerlesik negatif kontrol (NK)
# Checker "her seye YESIL diyen" lastik damga olmasin: sentetik IYI govde gecmeli,
# sentetik BOZUK govde reddedilmeli.

IYI_GOVDE = (
    "          curl -sf -X POST http://127.0.0.1:18080/derle \\\n"
    "            -H 'Content-Type: application/json' \\\n"
    "            -d '{\"aile\":\"olcuye-ozel-toka\",\"parametreler\":"
    "{\"kemer_genisligi\":25,\"kalinlik\":10.8,\"kayis_baglanti\":\"dikis\"}}' \\\n"
    "            -o duman-toka.stl\n"
    "          wc -c duman-oring.stl duman-toka.stl\n"
    "          test -s duman-oring.stl && test -s duman-toka.stl\n"
)

BOZUK_GOVDE = (
    "          curl -sf -X POST http://127.0.0.1:18080/derle \\\n"
    "            -d '{\"aile\":\"olcuye-ozel-oring-conta\",\"parametreler\":{\"ic_cap\":30}}' \\\n"
    "            -o duman-oring.stl\n"
    "          wc -c duman-oring.stl\n"
    "          test -s duman-oring.stl\n"
)


def negatif_kontrol(hatalar):
    if yapisal_kusurlar(IYI_GOVDE):
        hatalar.append(
            "negatif kontrol: SENTETIK IYI govde yapisal kontrolden GECMEDI: %s"
            % "; ".join(yapisal_kusurlar(IYI_GOVDE)))
    if not yapisal_kusurlar(BOZUK_GOVDE):
        hatalar.append(
            "negatif kontrol KOR: SENTETIK BOZUK govde (toka'siz) kusursuz sayildi")


# ------------------------------------------------------------------------ main

def main():
    hatalar = []
    print("kontrol edilen dosya: %s" % YML)

    if not os.path.isfile(YML):
        print("KIRMIZI: workflow dosyasi yok: %s" % YML)
        return 1

    with open(YML, "r", encoding="utf-8") as f:
        metin = f.read()

    if "\t" in metin:
        hatalar.append("YML'de sekme (TAB) karakteri var — YAML'de yasak")

    adim, govde = adim_govdesi(metin)
    if adim is None:
        print("KIRMIZI: '%s' adimi bulunamadi" % ADIM_ADI)
        return 1
    if govde is None:
        print("KIRMIZI: '%s' adiminda 'run:' govdesi yok" % ADIM_ADI)
        return 1

    # (NK) once checker'in ayrimci oldugunu kanitla.
    negatif_kontrol(hatalar)
    if not any(h.startswith("negatif kontrol") for h in hatalar):
        print("  [OK ] (NK) negatif kontrol: checker sentetik iyi'yi gecirdi, bozugu reddetti")

    # (A) YAPISAL — gercek dosya.
    a_kusur = yapisal_kusurlar(govde)
    if a_kusur:
        for k in a_kusur:
            hatalar.append("(A) YAPISAL: " + k)
    else:
        print("  [OK ] (A) YAPISAL: toka /derle POST + 3 parametre + -o + wc + test -s tam")

    # (B) MUTASYON — bag(layici) mi? Iki mutasyon da KIRMIZI vermeli.
    m1 = yapisal_kusurlar(*adim_govdesi(mutasyon_toka_curl_cikar(metin))[1:])
    m2 = yapisal_kusurlar(*adim_govdesi(mutasyon_test_s_cikar(metin))[1:])
    mutasyon_bagliyor = bool(m1) and bool(m2)
    if not m1:
        hatalar.append("(B) MUTASYON KOR: toka curl'u cikinca yapisal kontrol YINE gecti "
                       "(kapi lastik damga)")
    if not m2:
        hatalar.append("(B) MUTASYON KOR: 'test -s duman-toka.stl' cikinca yapisal kontrol "
                       "YINE gecti (kapi lastik damga)")
    if mutasyon_bagliyor:
        print("  [OK ] (B) MUTASYON: toka curl'u VE 'test -s duman-toka.stl' cikinca "
              "kontrol KIRMIZI -> kapi BAGLAYICI")

    # (C) YANLIS-POZITIF — ilgisiz rutin ekleme YESIL kalmali.
    c_kusur = yapisal_kusurlar(adim_govdesi(mutasyon_ilgisiz_ekleme(metin))[1])
    falsepos_yesil = not c_kusur
    if c_kusur:
        hatalar.append("(C) YANLIS-POZITIF: ilgisiz rutin ekleme sonrasi kontrol KIRMIZI "
                       "oldu (kapi kirilgan): " + "; ".join(c_kusur))
    else:
        print("  [OK ] (C) YANLIS-POZITIF: yorum + sahte 12. aile eklenince toka kontrolu "
              "YINE YESIL")

    # Ozet satirlari (donus semasi icin makine-okunur).
    print("OZET: mutation_bind_fails=%s falsepos_stays_green=%s"
          % (str(mutasyon_bagliyor).lower(), str(falsepos_yesil).lower()))

    if hatalar:
        print("\n".join("KIRMIZI: " + h for h in hatalar))
        return 1

    print("YESIL: onizleme-imaj.yml duman adimi toka'yi eksiksiz derletir "
          "(imaj toka'siz cikarsa CI KIRMIZI).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
