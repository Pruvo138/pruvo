#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — ANASAYFA CIPI <-> /marka/<slug>/ SAYFASI: gorunen her cipin sayfasi VAR ve DOLU.

  python3 tools/cip-sayfa-bagi.py              # kabul (dogrudan)
  python3 tools/cip-sayfa-bagi.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/cip-sayfa-bagi.py --kok /yol   # BASKA agactan oku (mutasyon icin)

ADI BILEREK "-test.py" DEGIL: CI kapsam kesfi (tools/ci-kapsam-test.py) ikinci bir CI
girisi beklemesin — bu iddialar CI'da ZATEN kosan tools/marka-model-test.py icinden
cagrilir (emsal: tools/cip-indeks-kosum.js). Kapi BLOKLAYICIDIR, yalnizca cagrildigi
yer farklidir.

NEDEN VAR (olculen sessiz hata, 3 Agu — canli):
  Anasayfa cip evreni kategorinin `uyum` KAPSAMINA gore kuratorluk gevsetiyor
  (tools/cip-indeks.py :: ESIK_UYUM_KAPSAM). Marka SAYFASI ureteci ise YALNIZ
  index.html TANINMIS_MARKALAR'i okuyordu -> IKIZ TANIM. Sonuc olculdu:
  Teleflex(149) · Sierra(141) · NGK(117) · Tecnoseal(106) · Jabsco(44) ·
  International(43) · 3M(22) · TMC · Champion · Johnson Pump · Sika · Raymarine
  cip olarak GORUNUYOR, /marka/<slug>/ adresleri 404 donuyordu (13 cip / 45).
  Ayrica Vauxhall (71 urun) MARKA_ALIAS ile Opel sayfasina katlaniyor ama cipte AYRI
  duruyor -> onun da hedefi yoktu.

BU KAPININ IDDIASI (musteri yolu, DOM'da element aramak DEGIL):
  1. Cip evrenindeki HER marka ya kendi sayfasina ya alias hedefinin sayfasina COZULUR
     (slug_map'te hedefi VAR).
  2. Cozulen her hedef sayfasinda >0 urun listelenir (bos sayfa = olu uc).
  3. KONTROL: sayfa evreni cip evrenini KAPSAR ama ondan IBARET DEGILDIR — kuratorlu
     kategorilerdeki <15 urunlu taninmis markalarin sayfasi (cip olmasa da) DURUR.
     Bu eksen olmasaydi "sayfa evrenini cip evrenine esitle" mutanti da yesil gecerdi.
  4. FAIL-CLOSED: cip evreni URETILEMEZSE (indeks bos) kapi KIRMIZI yanar — sessizce
     "0 cip, 0 ihlal" diye yesil gecmez.

TEK KAYNAK: cip evreni tools/cip-indeks.py'nin URETTIGI indeksten okunur; sayfa evreni
marka_model_build.gruplandir + ESIK'ten. Ikinci bir liste TUTULMAZ.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)


def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def olc(kok):
    """(cipler, hedef, toplam, sayfali, mm) — hukum vermez, SAYI uretir.

    🔴 COZUMLEME BURADA YENIDEN YAZILMAZ. Ilk yazimda `hedef` bu dosyada
    `MARKA_ALIAS`tan turetiliyordu; sonuc: alias cozumlemesini UREtecten SILEN mutant
    YESIL gecti (test kendi varsayimini aynaliyordu, uretimi degil). Artik GERCEK
    uretec (`marka_model_build.uret`) GECICI bir ROOT'ta kosturulur ve musteriye giden
    `slug_map` ile `product_chip_map` OKUNUR. Sayfalar tempdir'e yazilir; GERCEK agac
    DEGISMEZ."""
    araclar = os.path.join(kok, "tools")
    if araclar not in sys.path:
        sys.path.insert(0, araclar)
    mm = _modul(os.path.join(araclar, "marka_model_build.py"), "mm_kabul")
    ci = _modul(os.path.join(araclar, "cip-indeks.py"), "ci_kabul")
    build = _modul(os.path.join(araclar, "build.py"), "build_kabul")
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_html = f.read()

    ix = ci.indeks_uret(urunler, index_html)
    cipler = sorted(set(b for kd in ix["kat"].values() for b in kd))

    tmp = tempfile.mkdtemp(prefix="cip-sayfa-uret-")
    try:
        shutil.copy2(os.path.join(kok, "index.html"), os.path.join(tmp, "index.html"))
        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        sonuc = mm.uret(urunler, ctx)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    slug_map = sonuc.get("slug_map", {})
    sayim = sonuc.get("sayim", {})
    toplam = dict((m, v.get("toplam_parca", 0)) for m, v in sayim.items())
    sayfali = set(slug_map.values())            # URETILEN sayfa slug'lari
    # Cipin hedefi = uretecin ONA verdigi slug (yoksa hedef YOK -> 404 riski).
    hedef = dict((b, slug_map[b]) for b in cipler if b in slug_map)
    # slug -> o sayfada listelenen urun sayisi (marka adindan degil SLUG'dan turetilir,
    # cunku alias'li cip hedefin SLUG'una cozulur).
    slug_toplam = {}
    for m, s in slug_map.items():
        if m in toplam:
            slug_toplam[s] = max(slug_toplam.get(s, 0), toplam[m])
    return cipler, hedef, slug_toplam, sayfali, mm, slug_map


def kabul(kok):
    kaldi, gecen = [], []

    def dogrula(ad, kosul, detay=""):
        (gecen if kosul else kaldi).append(ad)
        print("  %s %s%s" % ("GECTI" if kosul else "KALDI", ad, (" — " + detay) if detay else ""))

    cipler, hedef, slug_toplam, sayfali, mm, slug_map = olc(kok)
    print("  OLCUM: cip evreni=%d · URETILEN marka sayfasi=%d" % (len(cipler), len(sayfali)))

    dogrula("C0 FAIL-CLOSED: CIP EVRENI BOS DEGIL", len(cipler) > 0,
            "cip=%d (bos evren 'ihlal yok' diye YESIL gecemez)" % len(cipler))

    cozulmeyen = [b for b in cipler if b not in hedef]
    dogrula("C1 GORUNEN HER CIPIN SAYFA HEDEFI VAR (404 YOK)", not cozulmeyen,
            "cip=%d cozulmeyen=%d %s" % (len(cipler), len(cozulmeyen), cozulmeyen[:5]))

    bos = [b for b in cipler if b in hedef and slug_toplam.get(hedef[b], 0) <= 0]
    dogrula("C2 HER HEDEF SAYFA >0 URUN LISTELER (bos sayfa YOK)", not bos,
            "bos=%d %s" % (len(bos), bos[:5]))

    # KONTROL: sayfa evreni cip evreninden GENIS olmali (cipsiz taninmis markalarin
    # sayfasi durmali). Esitlenirse SEO yuzeyi sessizce daralir.
    fazla = sorted(sayfali - set(hedef.values()))
    dogrula("C3 KONTROL: SAYFA EVRENI CIP EVRENINDEN GENIS (cipsiz marka sayfasi DURUR)",
            len(fazla) > 0,
            "yalniz-sayfa slug=%d ornek=%s" % (len(fazla), fazla[:4]))

    # ALIAS (3 Ago'da DEGISTI): alias tablosu artik index.html'de TEK KAYNAK ve cip evreni
    # onu OKUYOR (tools/cip-indeks.py :: MarkaEvreni.katla). Yani "Vauxhall" artik AYRI cip
    # olarak DOGMAZ — kaynagi katlanir. Eski iddia ("alias'li CIP hedefe cozulur") bu yuzden
    # BOS KUMEDE calisirdi ve sessizce anlamsizlasirdi; iddia yeni gercege tasindi:
    #   C4  alias ANAHTARI cip evreninde GORUNMEZ (tek kaynak gercekten katliyor)
    #   C4b buna ragmen slug_map'te hedefin slug'ina COZULUR (eski link/dis referans 404 olmasin)
    alias = getattr(mm, "MARKA_ALIAS", {})
    dogrula("C4-0 FAIL-CLOSED: ALIAS TABLOSU BOS DEGIL (iddia gercekten olculuyor)",
            bool(alias), "alias=%s" % alias)
    sizan_alias = [b for b in cipler if b in alias]
    dogrula("C4 ALIAS ANAHTARI CIP EVRENINDE GORUNMEZ (kaynagi katlanir)",
            not sizan_alias,
            "cipte gorunen alias anahtari=%s (hedefi ayri sayfa DEGIL -> 404 olurdu)"
            % (sizan_alias or "-"))
    cozulmeyen_alias = [b for b, h in alias.items()
                        if slug_map.get(b) is None or slug_map.get(b) != slug_map.get(h)]
    dogrula("C4b ALIAS ANAHTARI YINE DE HEDEFIN SLUG'INA COZULUR (fail-safe geri-link)",
            not cozulmeyen_alias,
            "cozulmeyen=%s · %s" % (cozulmeyen_alias or "-",
                                    dict((b, slug_map.get(b)) for b in alias)))

    toplam_iddia = len(gecen) + len(kaldi)
    if kaldi:
        print("\nSONUC: %d/%d iddia KALDI" % (len(kaldi), toplam_iddia))
        return 1
    print("\nSONUC: %d/%d iddia GECTI ✔" % (toplam_iddia, toplam_iddia))
    return 0


MUTANTLAR = [
    ("marka_model_build.py",
     "        uyeler = marka_uyelikleri(m, evren, ek_markalar)",
     "        uyeler = marka_uyelikleri(m, evren)", "KIRMIZI",
     "SAYFA EVRENINI KURATORLUGE GERI DONDUR: cip evreni genis kalir, 12 cip 404 olur"),
    ("marka_model_build.py",
     "        if _ad not in slug_map and _hedef in slug_map:\n            slug_map[_ad] = slug_map[_hedef]",
     "        if False:\n            slug_map[_ad] = slug_map[_hedef]", "KIRMIZI",
     "ALIAS GERI-LINKINI KALDIR: alias anahtari (Vauxhall) hicbir sayfaya cozulmez"),
    ("cip-indeks.py", "        sonuc = self._alias.get(sonuc, sonuc)", "        pass", "KIRMIZI",
     "CIP EVRENI ALIAS'I OKUMAYI BIRAKIR: Vauxhall AYRI cip dogar, sayfasi YOK (404)"),
    ("marka_model_build.py", "ESIK = 3", "ESIK = 100000", "KIRMIZI",
     "SAYFA ESIGINI TAVANA CEK: hicbir marka sayfasi uretilmez -> her cip 404"),
    # KONTROL (YESIL bekleniyor)
    ("marka_model_build.py", "ESIK = 3", "ESIK = 2", "YESIL",
     "ILGISIZ: esigi 3->2 yapmak cip hedeflerini DUSURMEZ (yalniz ince sayfa ekler)"),
    ("cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "ILGISIZ: indeks surum alani — cip<->sayfa baginda rol OYNAMAZ"),
]


def _hedef_yol(tmp, dosya):
    return os.path.join(tmp, "tools", dosya)


def mutasyon():
    print("MUTASYON — cip<->sayfa bagi (mutant KOPYAYA uygulanir; canli agac DEGISMEZ)")
    basarisiz = []
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = tempfile.mkdtemp(prefix="cip-sayfa-mut-")
        try:
            # 🔴 TAM KOK KURULUR: `olc()` gercek uretici zinciri (build.py + sayfalar.py +
            # secenekler.js + taban-fiyatlar.js...) uzerinden kosar. Ilk yazimda yalniz
            # tools/ + 3 dosya kopyalanmisti; mutant kosumlari ICE ATILMIS bagimlilik
            # yuzunden COKUYOR ve cokme "KIRMIZI" ile karisiyordu (kontrol mutantlari da
            # kirmizi yandi -> batarya ayirt ediciligini kaybetmisti).
            # tools/ KOPYALANIR (mutant oraya uygulanir), gerisi SYMLINK (hizli + salt-okunur).
            os.makedirs(os.path.join(tmp, "tools"))
            for ad in os.listdir(os.path.join(GERCEK_KOK, "tools")):
                k = os.path.join(GERCEK_KOK, "tools", ad)
                if os.path.isfile(k):
                    shutil.copy2(k, os.path.join(tmp, "tools", ad))
            for ad in os.listdir(GERCEK_KOK):
                if ad in ("tools", ".git"):
                    continue
                os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))
            yol = _hedef_yol(tmp, dosya)
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if eski not in metin:
                print("  HATA M%02d: mutant capasi BULUNAMADI -> %s" % (i, aciklama))
                basarisiz.append("M%02d capa yok" % i)
                continue
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.join(tmp, "tools", "cip-sayfa-bagi.py"),
                                "--kok", tmp], capture_output=True, text=True, timeout=1800)
            kirmizi_satir = [s for s in (p.stdout or "").splitlines()
                             if s.strip().startswith("KALDI")]
            # 🔴 COKME KIRMIZIYLA KARISMAZ: rc 0/1 disi ya da "KIRMIZI ama hicbir iddia
            # KALDI demedi" = COKME. Kabul olcutu cikis kodu DEGIL, OLCULEN IDDIA + isaret.
            if p.returncode not in (0, 1) or (p.returncode == 1 and not kirmizi_satir):
                print("  HATA M%02d [%s] %s -> COKME (rc=%d, olculen iddia YOK) | %s"
                      % (i, beklenen, dosya, p.returncode, aciklama))
                print("        " + ((p.stderr or p.stdout or "").strip().splitlines() or [""])[-1][:180])
                basarisiz.append("M%02d [cokme]" % i)
                continue
            gercek = "YESIL" if p.returncode == 0 else "KIRMIZI"
            ok = gercek == beklenen
            print("  %-4s M%02d [%s] %s -> %s (%d iddia kirmizi) | %s"
                  % ("OK" if ok else "HATA", i, beklenen, dosya, gercek,
                     len(kirmizi_satir), aciklama))
            for s in kirmizi_satir[:2]:
                print("        " + s.strip()[:150])
            if not ok:
                basarisiz.append("M%02d" % i)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI -> %s"
              % (len(basarisiz), len(MUTANTLAR), basarisiz))
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK)
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())
