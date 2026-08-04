#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IKI GOVDE (2-RENK) URETIM SOZLESMESI KAPISI — derleyiciye giden -D bayraklari.

NEDEN VAR (Okan, canli, 29 Tem 2026):
  /urun/olcuye-ozel-cerceve/ sayfasi musteriye "Yazı rengi (2. renk)" secenegi
  SUNUYOR ama uretim yolu TEK GOVDE donduruyordu (Output="frame"): yazi cerceveyle
  ayni filamandan basiliyordu. Site satiyor, uretim veremiyordu. Cozum, cerceve
  uretecinin ZATEN destekledigi iki ek Output modunu (frame_no_caption / caption)
  eslem duzeyinde acmak: aile basina iki EK eslem ailesi
    <aile>#govde -> Output="frame_no_caption"   (yazisiz cerceve kabugu)
    <aile>#yazi  -> Output="caption"            (yalniz kabartma yazi govdesi)

NE KANITLAR (dar, dogru etiket — hepsi GERCEK kodla, kopya mantik YOK):
  1. HIZALAMA (yapisal): parca ailelerinin ureteci (.scad) ve derleyiciye giden
     -D BAYRAK KUMESI, taban aileninkiyle `Output` DISINDA BIREBIR AYNIDIR.
     Iki govde ayni uretecten ayni sayilarla ciktigi icin AYNI koordinat
     sistemindedir; kaydirma/olcekleme/merkezleme adimi hicbir yerde YOKTUR.
     (Bu, mesh'lerin bbox'ini OLCMEZ — o olcum openscad ister:
      onizleme/test/iki-govde-olcum.py, onizleme-imaj.yml'de kosar.)
  2. GERIYE DONUK UYUM: taban ailenin eslem blogu ve -D bayraklari, `parcalar`
     blogu EKLENMEDEN ONCEKIYLE BIREBIR AYNI (parcasiz cagri bit-ayni cikti verir).
  3. MUSTERI METNI HER IKI GOVDEDE de ayni parametreye baglidir: farkli yazi ->
     her iki parca ailesinde de FARKLI -D (yazi govdesi baska bir yaziyi basamaz).
  4. TEK KAYNAK: /secenekler.js ONIZLEME_PARCALAR'daki parca adlari ile esleme
     json'undaki `parcalar` anahtarlari BIREBIR AYNI kumedir (biri digerinden
     sapinca worker istegi 400 alir ya da uretilemeyen parca sunulur).
  5. FAIL-CLOSED uretim: taban `sabit`te olmayan degiskeni ezen parca, gecersiz
     parca adi ve bos ezme paket uretimini DURDURUR.

NE KANITLAMAZ (iddia edilmez):
  * Uretilen MESH'lerin gercekten ayristigini/ust uste oturdugunu (openscad gerekir).
  * Iki govdenin birlesiminin tek govdeyle geometrik esdegerligini (ayni sebep).
  * Onbellek anahtari / worker yonlendirmesi (o eksen: onizleme/test/iki-govde-kabul.mjs).
  * Fiyat (2-renk ucreti bu turda DEGISMEDI; sifir).

KIRMIZI-MUTASYON (ham cikti muhendis raporunda):
  (a) `parcalar` blogu esleme json'undan silinir            -> KIRMIZI (kapsam bos)
  (b) parca blogunun `Output`u tabanla ayni yapilir         -> KIRMIZI (ayrisma yok)
  (c) parca blogunun `metin`/`sayisal` bloguna dokunulur    -> KIRMIZI (hizalama)
  (d) ONIZLEME_PARCALAR'dan bir parca adi silinir           -> KIRMIZI (tek kaynak)

Kullanim:
  python3 tools/iki-govde-kapisi.py
  python3 tools/iki-govde-kapisi.py --kendini-test
"""
import argparse
import copy
import importlib.util
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
ESLEME_DIZIN = os.path.join(ROOT, "jenerator", "test", "esleme")
SECENEKLER = os.path.join(ROOT, "secenekler.js")


def _modul(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SERVER = _modul("pruvo_ig_server", os.path.join(ROOT, "onizleme", "derleyici", "server.py"))
PAKET = _modul("pruvo_ig_paket", os.path.join(TOOLS, "onizleme-paket-yukle.py"))

# Iki SOMUT metin (ikisi de beyaz listede + sert tavanin altinda): "fark" iddiasi
# kirpma/temizleme davranisina degil GERCEK baglantiya dayansin.
METIN_A = "OKAN"
METIN_B = "ZZZZZZZZ"


def secenekler_parcalari():
    """/secenekler.js ONIZLEME_PARCALAR -> {aile: [parca, ...]} (metinden ayiklanir).

    JS calistirilmaz (bu kapi python); blok duz ayrastirilir. Blok BULUNAMAZSA
    fail-closed: kapi KIRMIZI yanar (sessizce bos kume donmez)."""
    with open(SECENEKLER, encoding="utf-8") as f:
        kaynak = f.read()
    m = re.search(r"var\s+ONIZLEME_PARCALAR\s*=\s*\{(.*?)\n  \};", kaynak, re.S)
    if not m:
        sys.exit("KIRMIZI: /secenekler.js icinde ONIZLEME_PARCALAR blogu bulunamadi "
                 "(tek kaynak kayboldu ya da bicimi degisti)")
    govde = m.group(1)
    cikti = {}
    for aile, liste in re.findall(r'"([^"]+)"\s*:\s*\[([^\]]*)\]', govde):
        cikti[aile] = re.findall(r'"([^"]+)"', liste)
    return cikti


def bayraklar(blok, parametreler):
    b, sebep = SERVER.d_bayraklari(blok, parametreler)
    if b is None:
        sys.exit("KIRMIZI: -D uretilemedi (%s)" % sebep)
    return sorted(b[i] + "=" + b[i + 1] if False else b[i + 1]
                  for i in range(0, len(b), 2))


def ornek_parametreler(aile_ad, metin):
    """Semadan varsayilan degerler + metin parametrelerine verilen metin."""
    with open(os.path.join(ESLEME_DIZIN, aile_ad + ".json"), encoding="utf-8") as f:
        test_eslem = json.load(f)
    with open(os.path.join(ROOT, "jenerator", "urunler",
                           test_eslem["urunId"] + ".json"), encoding="utf-8") as f:
        sema = json.load(f)
    p = {}
    for tanim in sema["parametreler"]:
        p[tanim["ad"]] = (metin if tanim.get("tip") == "metin"
                          else tanim["varsayilan"])
    return p


def olc(hatalar, ad, kosul, detay=""):
    print(("  [OK ] " if kosul else "  [KIRMIZI] ") + ad + (" -> " + detay if detay else ""))
    if not kosul:
        hatalar.append(ad)


def kos(kontroller=True):
    hatalar = []
    beklenen = secenekler_parcalari()
    # KESIF: elle liste YOK — `parcalar` blogu olan HER acik aile olculur.
    kapsam = []
    for aile_id, ad in sorted(PAKET.ACIK_AILELER.items()):
        with open(os.path.join(ESLEME_DIZIN, ad + ".json"), encoding="utf-8") as f:
            if (json.load(f).get("parcalar") or {}):
                kapsam.append((aile_id, ad))
    print("kesif: %d cok govdeli aile" % len(kapsam))
    olc(hatalar, "0 kapsam bos degil (parcalar blogu olan aile var)", bool(kapsam),
        ", ".join(a for a, _ in kapsam) or "YOK")
    olc(hatalar, "0b /secenekler.js ONIZLEME_PARCALAR bos degil", bool(beklenen),
        json.dumps(beklenen, ensure_ascii=False))

    for aile_id, ad in kapsam:
        print("-- %s (%s.json)" % (aile_id, ad))
        urun_id, taban, scad = PAKET.acik_eslem_uret(ad)
        parcalar = PAKET.parca_bloklari(ad, taban)
        adlar = sorted(k.split(PAKET.PARCA_AYIRAC, 1)[1] for k in parcalar)

        # (4) TEK KAYNAK: secenekler.js listesi ile esleme json'u ayni kume mi
        olc(hatalar, "4 %s: secenekler.js parca listesi == esleme json" % aile_id,
            sorted(beklenen.get(aile_id, [])) == adlar,
            "js=%s json=%s" % (sorted(beklenen.get(aile_id, [])), adlar))

        pa = ornek_parametreler(ad, METIN_A)
        taban_b = bayraklar(taban, pa)
        for tam_id, blok in sorted(parcalar.items()):
            parca = tam_id.split(PAKET.PARCA_AYIRAC, 1)[1]
            # (1a) AYNI URETEC
            olc(hatalar, "1a %s: ayni .scad" % tam_id, blok["scad"] == taban["scad"],
                blok["scad"])
            # (1b) -D kumesi tabanla YALNIZ Output'ta ayrisir
            pb = bayraklar(blok, pa)
            fark_taban = sorted(set(taban_b) - set(pb))
            fark_parca = sorted(set(pb) - set(taban_b))
            sadece_output = (len(fark_taban) == len(fark_parca) == 1 and
                             fark_taban[0].startswith("Output=") and
                             fark_parca[0].startswith("Output="))
            olc(hatalar, "1b %s: -D farki YALNIZ Output" % tam_id, sadece_output,
                "taban=%s parca=%s" % (fark_taban, fark_parca))
            # (1c) Output GERCEKTEN degisti (mutasyon (b) burada kirmizi yanar)
            olc(hatalar, "1c %s: Output tabandan FARKLI" % tam_id,
                sadece_output and fark_taban[0] != fark_parca[0],
                fark_parca[0] if fark_parca else "-")
            # (1d) olcu/metin bloklari AYNEN korunmus (mutasyon (c))
            for anahtar in ("sayisal", "vektor", "secim", "metin"):
                olc(hatalar, "1d %s: `%s` blogu tabanla ayni" % (tam_id, anahtar),
                    (blok["ortak"].get(anahtar) or {}) == (taban["ortak"].get(anahtar) or {}))
            # (3) musteri metni parca govdesine de baglidir
            pb_a = bayraklar(blok, ornek_parametreler(ad, METIN_A))
            pb_b = bayraklar(blok, ornek_parametreler(ad, METIN_B))
            olc(hatalar, "3 %s: farkli yazi -> farkli -D" % tam_id, pb_a != pb_b,
                "%d/%d bayrak, fark var" % (len(pb_a), len(pb_b)))

        # (2) GERIYE DONUK UYUM: taban blok `parcalar`siz uretimle BIREBIR AYNI
        with open(os.path.join(ESLEME_DIZIN, ad + ".json"), encoding="utf-8") as f:
            ham = json.load(f)
        ham.pop("parcalar", None)
        gecici = os.path.join(ESLEME_DIZIN, ".ikigovde-gecici-" + ad + ".json")
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(ham, f, ensure_ascii=False)
        try:
            _, taban2, _ = PAKET.acik_eslem_uret(os.path.basename(gecici)[:-5])
            bos = PAKET.parca_bloklari(os.path.basename(gecici)[:-5], taban2)
        finally:
            os.remove(gecici)
        olc(hatalar, "2a %s: taban blok `parcalar`siz halle BIREBIR AYNI" % aile_id,
            json.dumps(taban, sort_keys=True) == json.dumps(taban2, sort_keys=True))
        olc(hatalar, "2b %s: `parcalar` yoksa EK aile uretilmez" % aile_id, bos == {},
            str(sorted(bos)))
        olc(hatalar, "2c %s: taban -D kumesi degismedi" % aile_id,
            bayraklar(taban2, pa) == taban_b, "%d bayrak" % len(taban_b))

    if kontroller:
        hatalar += fail_closed_kontrol()

    print("\nhata: %d" % len(hatalar))
    return 1 if hatalar else 0


def fail_closed_kontrol():
    """(5) parca_bloklari FAIL-CLOSED mi — hatali tanimlar paket uretimini DURDURMALI.

    Oz-nobetci: govdesi no-op yapilirsa bu kontroller kaybolur ve kapi zayiflar,
    o yuzden HER kosumda bloklayici isler (kontroller=True)."""
    hatalar = []
    ad = "cerceve"
    _, taban, _ = PAKET.acik_eslem_uret(ad)

    def dener(parcalar, etiket):
        ham_yol = os.path.join(ESLEME_DIZIN, ad + ".json")
        with open(ham_yol, encoding="utf-8") as f:
            ham = json.load(f)
        ham["parcalar"] = parcalar
        gecici_ad = ".ikigovde-fc-" + etiket
        gecici = os.path.join(ESLEME_DIZIN, gecici_ad + ".json")
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(ham, f, ensure_ascii=False)
        try:
            PAKET.parca_bloklari(gecici_ad, taban)
            return False          # DURMADI -> fail-open
        except SystemExit:
            return True           # DURDU -> fail-closed
        finally:
            os.remove(gecici)

    print("-- (5) fail-closed uretim")
    olc(hatalar, "5a taban `sabit`te olmayan degiskeni ezen parca DURDURUR",
        dener({"x": {"YokBoyleBirDegisken": 1}}, "yok"))
    olc(hatalar, "5b gecersiz parca adi DURDURUR", dener({"GOV DE": {"Output": "caption"}}, "ad"))
    olc(hatalar, "5c bos ezme DURDURUR", dener({"x": {}}, "bos"))
    return hatalar


def kendini_test():
    """OZ-NOBETCI: kapinin GOVDESI inert olamaz. `parcalar` blogu silinmis bir
    kopyada kapsam BOS kalir ve kapi KIRMIZI yanmali; yanmiyorsa kapi olu."""
    ad = "cerceve"
    yol = os.path.join(ESLEME_DIZIN, ad + ".json")
    with open(yol, encoding="utf-8") as f:
        asil = f.read()
    ham = json.loads(asil)
    ham.pop("parcalar", None)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(ham, f, ensure_ascii=False, indent=2)
    try:
        kod = kos(kontroller=False)
    finally:
        with open(yol, "w", encoding="utf-8") as f:
            f.write(asil)
    if kod == 0:
        print("🔴 OZ-TEST KIRMIZI: `parcalar` silinmisken kapi YESIL yandi (olu kapi)")
        return 1
    print("oz-test YESIL: mutasyon (a) yakalandi (kapi kirmizi yandi)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kendini-test", action="store_true")
    args = ap.parse_args()
    sys.exit(kendini_test() if args.kendini_test else kos())


if __name__ == "__main__":
    main()
