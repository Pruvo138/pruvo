#!/usr/bin/env python3
"""kategori-kapisi-mutasyon.py — `kategori-kapisi.py --kendini-test` GERCEKTEN olcuyor mu?

NEDEN VAR (K405, 11 Eyl 2026): bir bataryanin YESIL yanmasi, olctugunu KANITLAMAZ.
Bu harness kapinin GOVDESINI bozar ve bataryanin KIRMIZI yandigini + OLDURDUGU VAKA
KUMESINI ADIYLA bastigini dogrular. Beklenen kume BIREBIR esitlikle karsilanir: mutant
"bir seyleri" kirmizi yakiyor olabilir ama YANLIS vakalari kiriyorsa o da KIRMIZI'dir
([[sinif-adi-kol-adi-olarak-basilirsa-yanlis-alan-dogrulanir]]).

🔴 MUTANT CANLI GOVDEDE YASAMAZ: her mutant, tempfile ile acilan IZOLE bir sahte kokte
kosar (index.html + tools/build.py BIREBIR kopyalanir, kapi dosyasi MUTASYONLU yazilir).
Gercek agaca HICBIR yazma yapilmaz; harness bitince gecici kok kendini toplar.

🔴 CAPA FAIL-CLOSED: bir mutasyonun capa metni kaynakta bulunamazsa mutant SESSIZCE
no-op'a donusurdu (mutasyon uygulanmadigi icin batarya yesil kalir ve "oldurucu yok"
sanilir). Capa bulunamazsa bu harness ANINDA kirmizi yanar
([[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]).

🔴 RC <-> ❌ TUTARLILIGI AYRI SATIRDIR: vaka SAYISI ekseni cikis kodu eksenini OLCMEZ.
M4 tam da bu fail-open'i kurar (`_rc_hesapla` hep 0 doner): batarya metinde KIRMIZI
derken rc=0 verir. Asagidaki `rc<->metin` kontrolu o mutanti yakalayan kolddur
([[vaka-sayisi-ekseni-cikis-kodu-eksenini-olcmez]] · [[fail-closed-kol-arkasindaki-kolu-maskeler]]).

Kullanim:
  python3 tools/kategori-kapisi-mutasyon.py     # 4 OLDURUCU mutant + 2 KONTROL (exit 1 = kirmizi)
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAPI = os.path.join(ROOT, "tools", "kategori-kapisi.py")
INDEX = os.path.join(ROOT, "index.html")
BUILD = os.path.join(ROOT, "tools", "build.py")

# (ad, capa, yerine, beklenen_olen_vaka_kumesi)  — bos kume = KONTROL (yesil kalmali)
MUTANTLAR = [
    ("M1/gecerli-kumeye-'Ev & Yaşam'-eklenir",
     "    return i_nav + i_gizli",
     "    return i_nav + i_gizli + [\"Ev & Yaşam\"]",
     {"VAKA-02/gecersiz-kategori-EvYasam-YANAR",
      "VAKA-09/karisik-kayitta-YALNIZ-bozuk-sayilir",
      "VAKA-10/uctan-uca-main-kirli-rc1"}),

    ("M2/gizli-kategoriler-dusurulur",
     "    return i_nav + i_gizli",
     "    return i_nav",
     {"VAKA-03/gizli-Jenerator-YANMAZ",
      "VAKA-04/gizli-SkanArt-YANMAZ",
      "VAKA-09/karisik-kayitta-YALNIZ-bozuk-sayilir"}),

    # 🔴 VAKA-08 BU MUTANTTA BILEREK YOK — OLCULDU, tahmin DEGIL: `<obje-degil>` kolu
    # `continue` ile AYRI bir daldir ve `if kat not in gecerli` satirina HIC ugramaz.
    # M3 onu oldurmez; oldurseydi iki vaka ayni kolu olcuyor demekti. VAKA-08'in
    # bagimsiz bir arm olctugunun kaniti tam da buradaki YOKLUGUDUR.
    ("M3/ihlal-kosulu-hic-yanmaz",
     "        if kat not in gecerli:",
     "        if False:",
     {"VAKA-02/gecersiz-kategori-EvYasam-YANAR",
      "VAKA-05/bos-kategori-YANAR",
      "VAKA-06/eksik-alan-YANAR",
      "VAKA-07/ascii-Bahce-YANAR",
      "VAKA-09/karisik-kayitta-YALNIZ-bozuk-sayilir",
      "VAKA-10/uctan-uca-main-kirli-rc1"}),

    # M4 iki iddiayi birden oldurur: KONTROL-B civiyi DOGRUDAN olcer, TUTARLILIK kolu
    # ise kapinin fail-closed dususunu kanitlar (metin KIRMIZI iken rc=0 KALAMAZ).
    ("M4/rc-civisi-fail-open (hep 0 doner)",
     "    return 1 if dusen else 0",
     "    return 0",
     {"KONTROL-B/rc-civisi-dolu-kume-birden-buyuk",
      "TUTARLILIK/rc-civisi-bozuk"}),

    # --- KONTROLLER: harness her seye kirmizi yanmiyor, mutasyona DUYARLI -------
    ("KONTROL-1/degistirilmemis-kopya",
     None, None, set()),

    ("KONTROL-2/yalniz-yorum-eklenir (no-op)",
     "import argparse",
     "import argparse  # no-op mutasyon (davranis degismez)",
     set()),
]


def _izole_kok(gecici, kaynak_metin):
    """Sahte kok kurar: index.html + tools/build.py BIREBIR, kapi MUTASYONLU."""
    os.makedirs(os.path.join(gecici, "tools"), exist_ok=True)
    shutil.copyfile(INDEX, os.path.join(gecici, "index.html"))
    shutil.copyfile(BUILD, os.path.join(gecici, "tools", "build.py"))
    hedef = os.path.join(gecici, "tools", "kategori-kapisi.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak_metin)
    return hedef


def _dusen_kumesi(cikti):
    """Bataryanin bastigi `DUSEN KUMESI:` satirini kumeye cevirir."""
    for satir in cikti.splitlines():
        if satir.startswith("DUSEN KUMESI:"):
            govde = satir.split(":", 1)[1].strip()
            if govde == "<bos>":
                return set()
            return {p.strip() for p in govde.split(",") if p.strip()}
    return None  # satir HIC basilmadi -> batarya cokmus olabilir


def main():
    with open(KAPI, encoding="utf-8") as f:
        kaynak = f.read()

    dusen = []
    print("KATEGORI KAPISI — MUTASYON BATARYASI")
    print("  hedef kol: tools/kategori-kapisi.py --kendini-test")

    for ad, capa, yerine, beklenen in MUTANTLAR:
        if capa is None:
            mutant_kaynak = kaynak
        else:
            # FAIL-CLOSED: capa yoksa mutant sessizce no-op olurdu.
            if kaynak.count(capa) != 1:
                print("  DUSEN: %s — CAPA BULUNAMADI/COKLU (%d kez): %r"
                      % (ad, kaynak.count(capa), capa))
                dusen.append(ad + " [capa]")
                continue
            mutant_kaynak = kaynak.replace(capa, yerine)

        with tempfile.TemporaryDirectory() as gecici:
            hedef = _izole_kok(gecici, mutant_kaynak)
            sonuc = subprocess.run([sys.executable, hedef, "--kendini-test"],
                                   capture_output=True, text=True)
        cikti = sonuc.stdout + sonuc.stderr
        gercek = _dusen_kumesi(cikti)
        metin_kirmizi = "SONUC: KIRMIZI" in cikti
        rc_kirmizi = sonuc.returncode != 0

        if gercek is None:
            print("  DUSEN: %s — batarya `DUSEN KUMESI:` satirini HIC basmadi (rc=%d); "
                  "izole kopya COKTU, mutasyon OLCULEMEDI" % (ad, sonuc.returncode))
            dusen.append(ad + " [cokme]")
            continue

        # (a) OLDURULEN KUME ADIYLA esitlik
        if gercek != beklenen:
            print("  DUSEN: %s — DUSEN kumesi beklenenle eslesmiyor\n"
                  "         beklenen: %s\n         gercek  : %s"
                  % (ad, sorted(beklenen) or "<bos>", sorted(gercek) or "<bos>"))
            dusen.append(ad + " [kume]")
        # (b) OLDURUCU mutantta DUSEN=0 olamaz
        elif beklenen and not gercek:
            print("  DUSEN: %s — OLDURUCU mutant hicbir vakayi oldurmedi (DUSEN=0)" % ad)
            dusen.append(ad + " [dusen-sifir]")
        else:
            print("  ok   %s — DUSEN=%d (%s)"
                  % (ad, len(gercek), ", ".join(sorted(gercek)) or "<bos>"))

        # (c) rc <-> ❌ TUTARLILIGI: AYRI satir, AYRI iddia
        beklenen_kirmizi = bool(beklenen)
        if rc_kirmizi != metin_kirmizi:
            print("  DUSEN: %s — rc<->metin TUTARSIZ (rc=%d, metin_kirmizi=%s) — FAIL-OPEN"
                  % (ad, sonuc.returncode, metin_kirmizi))
            dusen.append(ad + " [rc<->metin]")
        elif rc_kirmizi != beklenen_kirmizi:
            print("  DUSEN: %s — rc yonu yanlis (beklenen kirmizi=%s, rc=%d)"
                  % (ad, beklenen_kirmizi, sonuc.returncode))
            dusen.append(ad + " [rc-yonu]")

    oldurucu = sum(1 for m in MUTANTLAR if m[3])
    kontrol = len(MUTANTLAR) - oldurucu
    print("MUTANT: %d oldurucu · %d kontrol" % (oldurucu, kontrol))
    if dusen:
        print("DUSEN KUMESI: %s" % ", ".join(dusen))
        print("SONUC: KIRMIZI")
        return 1
    print("DUSEN KUMESI: <bos>")
    print("SONUC: YESIL — batarya %d oldurucu mutantin HEPSINI, dogru vaka kumesiyle yakaladi."
          % oldurucu)
    return 0


if __name__ == "__main__":
    sys.exit(main())
