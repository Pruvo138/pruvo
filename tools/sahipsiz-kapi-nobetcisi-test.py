#!/usr/bin/env python3
"""sahipsiz-kapi-nobetcisi-test.py — K408 sozlesmesinin kabul bataryasi + mutantlari.

CAGRI: `python3 tools/sahipsiz-kapi-nobetcisi.py --kendini-test` (kapi bu modulu yukler).

🔴 TEST YUKU YIKICI OLAMAZ: her fikstur `tempfile.mkdtemp` altinda SAHTE bir agactir
(tools/ + .github/workflows/). GERCEK ev yoluna (`/Users/okan/dev/pruvo`) hicbir vaka
YAZMAZ; mutantlar CANLI govdede degil, yuklenmis modulun KOPYA fonksiyonlarinda kosar.

CIKIS KODU EKSENI IKI YONLU CIVILIDIR (K407 dersi): `❌>0 ⇒ rc≠0` VE `❌=0 ⇒ rc=0`.
Govde "KIRMIZI" derken rc=0 donen bir batarya, kosulsa bile YESIL sanilir.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KAPI_YOLU = os.path.join(BURASI, "sahipsiz-kapi-nobetcisi.py")


def _kapi():
    spec = importlib.util.spec_from_file_location("shk", KAPI_YOLU)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _agac(tools_dosyalari, workflow_dosyalari):
    """Izole sahte agac kurar; (kok, tools_dizini, akis_dizini) doner."""
    kok = tempfile.mkdtemp(prefix="shk-fikstur-")
    t = os.path.join(kok, "tools")
    w = os.path.join(kok, ".github", "workflows")
    os.makedirs(t)
    os.makedirs(w)
    for ad, govde in tools_dosyalari.items():
        with open(os.path.join(t, ad), "w", encoding="utf-8") as f:
            f.write(govde)
    for ad, govde in workflow_dosyalari.items():
        with open(os.path.join(w, ad), "w", encoding="utf-8") as f:
            f.write(govde)
    return kok, t, w


def _ci_kapsam_fiksturu(kok, muaf_adlari):
    """IZIN_LISTESI tasiyan sahte ci-kapsam-test.py — muafiyet TEK KAYNAGI."""
    yol = os.path.join(kok, "sahte-ci-kapsam.py")
    govde = ["IZIN_LISTESI = {"]
    for ad in muaf_adlari:
        govde.append('    "tools/%s": ("gerekce metni",),' % ad)
    govde.append("}")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(govde) + "\n")
    return yol


CLI_GOVDE = 'if __name__ == "__main__":\n    pass\n'
MODUL_GOVDE = 'def yardim():\n    return 1\n'


def kos():
    m = _kapi()
    gecti, dusen = [], []

    def iddia(ad, kosul, detay=""):
        (gecti if kosul else dusen).append(ad)
        print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", ad,
                               (" — " + detay) if detay else ""))

    temizlenecek = []

    def kur(tools_dosyalari, workflow_dosyalari, muaf=()):
        kok, t, w = _agac(tools_dosyalari, workflow_dosyalari)
        temizlenecek.append(kok)
        ci = _ci_kapsam_fiksturu(kok, muaf)
        return m.denetle(tools_dizini=t, akis_dizini=w, ci_kapsam_yolu=ci)

    def kovada(kovalar, kova, ad):
        return any(x[0] == ad for x in kovalar[kova])

    try:
        # ---- IDDIA-1: workflow `run:` satirindaki TAM AD -> KOSAN
        k, _ = kur({"a-kapisi.py": CLI_GOVDE},
                   {"x.yml": "jobs:\n  j:\n    steps:\n"
                             "      - run: python3 tools/a-kapisi.py\n"})
        iddia("IDDIA-1 run-satiri-kosan-sayilir", kovada(k, "kosan", "a-kapisi.py"))

        # ---- IDDIA-2: YORUM satirindaki atif KOSUM DEGILDIR
        k, _ = kur({"b-kapisi.py": CLI_GOVDE},
                   {"x.yml": "jobs:\n  j:\n    steps:\n"
                             "      # - run: python3 tools/b-kapisi.py\n"})
        iddia("IDDIA-2 yorum-atfi-kosum-degil", kovada(k, "sahipsiz", "b-kapisi.py"),
              "yorumdaki atif govdeyi KOSAN yapmamali")

        # ---- IDDIA-3: ONEK TUZAGI — altkategori atfi kategoriyi kurtarmaz
        k, _ = kur({"kategori-kapisi.py": CLI_GOVDE, "altkategori-kapisi.py": CLI_GOVDE},
                   {"x.yml": "      - run: python3 tools/altkategori-kapisi.py\n"})
        iddia("IDDIA-3 onek-tuzagi-elenir",
              kovada(k, "sahipsiz", "kategori-kapisi.py")
              and kovada(k, "kosan", "altkategori-kapisi.py"),
              "alt-dize eslesmesi komsu araci KOSAN gostermemeli")

        # ---- IDDIA-4: IZIN_LISTESI muafiyeti TEK KAYNAKTAN okunur
        k, _ = kur({"c-kapisi.py": CLI_GOVDE}, {"x.yml": "jobs: {}\n"},
                   muaf=("c-kapisi.py",))
        iddia("IDDIA-4 muafiyet-tek-kaynaktan", kovada(k, "muaf", "c-kapisi.py"))

        # ---- IDDIA-5: CLI'siz + import edilen govde YARDIMCI (sahipsiz DEGIL)
        k, _ = kur({"d_kapisi.py": MODUL_GOVDE,
                    "tuketici-test.py": "import d_kapisi\n" + CLI_GOVDE},
                   {"x.yml": "      - run: python3 tools/tuketici-test.py\n"})
        iddia("IDDIA-5 clisiz-import-edilen-yardimci",
              kovada(k, "yardimci", "d_kapisi.py"),
              "CI atfi 0 olmasi bir MODUL icin sahipsizlik kaniti degildir")

        # ---- KONTROL-A: CLI'si OLAN govde import edilse de YARDIMCI sayilmaz
        k, _ = kur({"e-kapisi.py": CLI_GOVDE,
                    "tuketici-test.py": "import e_kapisi\n" + CLI_GOVDE},
                   {"x.yml": "      - run: python3 tools/tuketici-test.py\n"})
        iddia("KONTROL-A cli-varsa-yardimci-degil",
              kovada(k, "sahipsiz", "e-kapisi.py"),
              "CLI'si olan bir kapi kutuphane bahanesiyle kacamaz")

        # ---- IDDIA-6: EVREN GLOB'dan turer — 2 dosyaya capalanmaz (K408'in dogum sebebi)
        k, _ = kur({"f-nobetci.py": CLI_GOVDE},
                   {"deploy.yml": "jobs: {}\n", "nobet.yml": "jobs: {}\n",
                    "ucuncu-alarmi.yml": "      - run: python3 tools/f-nobetci.py\n"})
        iddia("IDDIA-6 evren-glob-tum-workflowlar",
              kovada(k, "kosan", "f-nobetci.py"),
              "deploy.yml+nobet.yml disindaki dosyada kosan govde SAHIPSIZ sayilmamali")

        # ---- KONTROL-B: .yaml uzantisi da evrendedir
        k, _ = kur({"g-nobeti.py": CLI_GOVDE},
                   {"z.yaml": "      - run: python3 tools/g-nobeti.py\n"})
        iddia("KONTROL-B yaml-uzantisi-sayilir", kovada(k, "kosan", "g-nobeti.py"))

        # ---- KONTROL-C: sinif izi TASIMAYAN dosya evrene hic girmez
        k, _ = kur({"arama.py": CLI_GOVDE}, {"x.yml": "jobs: {}\n"})
        iddia("KONTROL-C sinif-izsiz-dosya-evren-disi",
              not any(kovada(k, kv, "arama.py") for kv in k),
              "kapi/nobetci/test olmayan govde bu sozlesmeye tabi degil")

        # ---- IDDIA-7: FAIL-CLOSED — muafiyet kaydi okunamazsa hukum VERILMEZ
        kovalar, sebep = m.denetle(tools_dizini=BURASI, akis_dizini=None,
                                   ci_kapsam_yolu=os.path.join(BURASI, "yok-boyle-dosya.py"))
        iddia("IDDIA-7 muafiyet-okunamazsa-olculemedi",
              kovalar is None and sebep is not None,
              "IZIN_LISTESI okunamadan sahipsizlik hukmu verilemez")

        # ---- IDDIA-8: kovalar ORTUSMEZ, aritmetik TAM
        k, _ = kur({"h-kapisi.py": CLI_GOVDE, "i-kapisi.py": CLI_GOVDE,
                    "j_kapisi.py": MODUL_GOVDE,
                    "tuketici-test.py": "import j_kapisi\n" + CLI_GOVDE},
                   {"x.yml": "      - run: python3 tools/h-kapisi.py\n"},
                   muaf=("i-kapisi.py",))
        toplam = sum(len(v) for v in k.values())
        adlar = [ad for v in k.values() for ad, _ in v]
        iddia("IDDIA-8 kovalar-ortusmez-aritmetik-tam",
              toplam == 4 and len(set(adlar)) == 4,
              "olculen=%d benzersiz=%d (beklenen 4/4)" % (toplam, len(set(adlar))))

        # ---- IDDIA-9 (K411): `spec_from_file_location` ile YUKLENEN CLI'siz govde YARDIMCI
        YUKLEYICI = ('import importlib.util, os\n'
                     '_s = importlib.util.spec_from_file_location("k_kapisi", '
                     'os.path.join(os.path.dirname(__file__), "k_kapisi.py"))\n')
        YORUM_MENSIYON = "# bkz k_kapisi.py (yalniz mensiyon, yukleme DEGIL)\n"
        k, _ = kur({"k_kapisi.py": MODUL_GOVDE,
                    "urun-ekle.py": YUKLEYICI + YORUM_MENSIYON + CLI_GOVDE},
                   {"x.yml": "jobs: {}\n"})
        iddia("IDDIA-9 spec-from-file-location-yardimci", kovada(k, "yardimci", "k_kapisi.py"))

        # ---- IDDIA-10 (K411): sarmalayici `_load("x", "x.py")` bicimi de YUKLEMEDIR
        SARMALAYICI = ('import importlib.util, os\n'
                       'def _load(ad, dosya):\n'
                       '    s = importlib.util.spec_from_file_location(ad, dosya)\n'
                       '    return s\n'
                       'gbk = _load("l_kapisi", "l_kapisi.py")\n')
        k, _ = kur({"l_kapisi.py": MODUL_GOVDE,
                    "makerworld-ekle.py": SARMALAYICI + CLI_GOVDE},
                   {"x.yml": "jobs: {}\n"})
        iddia("IDDIA-10 sarmalayici-yukleyici-yardimci", kovada(k, "yardimci", "l_kapisi.py"))

        # ---- MUTANT-M3 (K411 kabulu): YUKLEYICI SATIRI SILINDI, yorum mensiyonu KALDI
        #      -> govde SAHIPSIZ'e DUSMELI. Eski `modul in g` olcutu burada YARDIMCI derdi.
        k, _ = kur({"k_kapisi.py": MODUL_GOVDE,
                    "urun-ekle.py": YORUM_MENSIYON + CLI_GOVDE},
                   {"x.yml": "jobs: {}\n"})
        iddia("MUTANT-M3 yukleyici-silinince-sahipsiz", kovada(k, "sahipsiz", "k_kapisi.py"),
              "adini ANMAK yukleme degildir — mensiyon govdeyi YARDIMCI yapmamali")

        # ---- MUTANT-M4: eski GEVSEK olcutu (`ad in g`) geri koy -> M3 vakasi YARDIMCI'ya
        #      kaymali; kaymadiysa M3 iddiasi OLU.
        asil_yukluyor = m.yukluyor_mu
        m.yukluyor_mu = lambda govde, ad: ad in govde or ad[:-3] in govde
        k, _ = kur({"k_kapisi.py": MODUL_GOVDE,
                    "urun-ekle.py": YORUM_MENSIYON + CLI_GOVDE},
                   {"x.yml": "jobs: {}\n"})
        m4_oldurdu = kovada(k, "yardimci", "k_kapisi.py")
        m.yukluyor_mu = asil_yukluyor
        iddia("MUTANT-M4 gevsek-mensiyon-olcutu-oldurulur", m4_oldurdu,
              "gevsek olcut M3 vakasini YARDIMCI yapmali — yapmadiysa M3 OLU")

        # ---- KONTROL-D: CLI'si OLAN govde spec_from_file_location ile yuklense de SAHIPSIZ
        #      (gorsel_boyut_kapisi / gorsel_mukerrer_kapisi'nin GERCEK hali, 13 Eyl olcumu)
        k, _ = kur({"k_kapisi.py": CLI_GOVDE,
                    "urun-ekle.py": YUKLEYICI + CLI_GOVDE},
                   {"x.yml": "jobs: {}\n"})
        iddia("KONTROL-D cli-li-yuklenen-govde-sahipsiz", kovada(k, "sahipsiz", "k_kapisi.py"),
              "yukleme bicimi CLI'li kapiyi kutuphane yapmaz (KONTROL-A ile ayni sozlesme)")

        # ---- MUTANT M1: YORUM elemesini oldur -> IDDIA-2 DUSMELI
        asil = m.kosan_atiflar

        def mutant_yorum_korlugu(akis_dizini=None):
            import re as _re
            d = akis_dizini
            atif = {}
            for wf in sorted(os.listdir(d)):
                if not wf.endswith((".yml", ".yaml")):
                    continue
                with open(os.path.join(d, wf), encoding="utf-8") as f:
                    for satir in f:                      # YORUM ELEMESI YOK (mutant)
                        for ad in _re.findall(r"[A-Za-z0-9_.-]+\.py", satir):
                            atif.setdefault(os.path.basename(ad), []).append(wf)
            return atif

        m.kosan_atiflar = mutant_yorum_korlugu
        k, _ = kur({"b-kapisi.py": CLI_GOVDE},
                   {"x.yml": "      # - run: python3 tools/b-kapisi.py\n"})
        m1_oldurdu = kovada(k, "kosan", "b-kapisi.py")
        m.kosan_atiflar = asil
        iddia("MUTANT-M1 yorum-elemesi-canli",
              m1_oldurdu,
              "yorum elemesi kaldirilinca IDDIA-2 DUSMELI — dusmediyse o iddia OLU")

        # ---- MUTANT M2: TAM AD eslemesini alt-dizeye cevir -> IDDIA-3 DUSMELI
        def mutant_alt_dize(akis_dizini=None):
            d = akis_dizini
            metin = ""
            for wf in sorted(os.listdir(d)):
                if wf.endswith((".yml", ".yaml")):
                    with open(os.path.join(d, wf), encoding="utf-8") as f:
                        metin += f.read()
            out = {}
            for ad in ("kategori-kapisi.py", "altkategori-kapisi.py"):
                if ad.replace(".py", "") in metin:       # ALT-DIZE (mutant)
                    out[ad] = ["x.yml"]
            return out

        m.kosan_atiflar = mutant_alt_dize
        k, _ = kur({"kategori-kapisi.py": CLI_GOVDE, "altkategori-kapisi.py": CLI_GOVDE},
                   {"x.yml": "      - run: python3 tools/altkategori-kapisi.py\n"})
        m2_oldurdu = kovada(k, "kosan", "kategori-kapisi.py")
        m.kosan_atiflar = asil
        iddia("MUTANT-M2 tam-ad-eslemesi-canli", m2_oldurdu,
              "alt-dize eslemesi komsuyu KOSAN yapmali — yapmadiysa IDDIA-3 OLU")

        # ---- META: mutantlarin KONTROLU — asil govde geri yuklendi mi
        k, _ = kur({"a-kapisi.py": CLI_GOVDE},
                   {"x.yml": "      - run: python3 tools/a-kapisi.py\n"})
        iddia("META-K asil-govde-geri-yuklendi", kovada(k, "kosan", "a-kapisi.py"),
              "mutant sizdiysa sonraki tum olcumler GECERSIZDIR")

    finally:
        for kok in temizlenecek:
            shutil.rmtree(kok, ignore_errors=True)

    print("\nDUSEN: %s" % (", ".join(dusen) if dusen else "-"))
    print("HATA_SAYISI: %d" % len(dusen))
    print("VAKA_SAYISI: %d" % (len(gecti) + len(dusen)))
    print("TOPLAM: %d/%d gecti" % (len(gecti), len(gecti) + len(dusen)))
    # CIKIS KODU EKSENI — iki yonlu civi (K407)
    rc = 1 if dusen else 0
    print("SONUC: %s (rc=%d)" % ("KIRMIZI" if dusen else "YESIL ✅", rc))
    return rc


if __name__ == "__main__":
    sys.exit(kos())
