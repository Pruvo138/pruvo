#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR NOBETCISI (tools/konfigur-test.py) MUTASYON + YANLIS-POZITIF HARNESS'I.

NE ISE YARAR: konfigur-test.py'nin KENDISI bir nobetcidir; onun iddialarinin GERCEKTEN
tasiyici olup olmadigini bu betik olcer. "Nobetci yesil yaniyor" bir sey KANITLAMAZ —
kanit, bozulmayi enjekte edince KIRMIZI yanmasi (mutasyon) VE ilgisiz rutin duzenlemede
YESIL kalmasidir (yanlis-pozitif fiksturu).

BOLUMLER
  A) KIRMIZI MUTASYON — KATEGORI EKSENI. Her kategori icin build.py'nin
     FONKSIYONEL_KATEGORILER satirindan o kategori DUSURULUR (canliya sizabilecek gercek
     bir hata: yeniden adlandirma / iki kopya listenin ayrismasi). O kategorinin butun
     urun sayfalari malzeme/renk secicisini + sepet ikonunu kaybeder, sayfa-alti buyuk
     butonlara doner. Kabul: nobetci KIRMIZI (cikis 1) VE kirmizi satir O KATEGORIYI
     adiyla soyler (isaret sarti — mutant baska bir nobetciyi tetikleyip "kaza eseri
     kirmizi" olamaz).
  B) KIRMIZI MUTASYON — OLU IDDIA / BOLGE KURALI. Govdedeki malzeme bilgileri silinir
     ama footer nav / sepet ikonu AYNEN kalir. Iddia TUM sayfada arandigi surece footer
     kopyasiyla karsilanir ve YESIL yanar (olu iddia); bolge daraltmasiyla KIRMIZI yanar.
  C) YANLIS-POZITIF FIKSTURU — bu depoda en pahali hata (nobetci deploy'u bloklar;
     yanlis-pozitif TUM SITE yayinini durdurur). Konfigur/kategori eksenine DOKUNMAYAN
     rutin duzenlemeler: CSS, yeni <script src>, footer nav metni, yeni kategori, yeni
     filament, govde metni. Kabul: hepsi YESIL (cikis 0, hic ❌ yok). ⚪ OLCULEMEDI
     yanlis-pozitif SAYILMAZ (sozlesme: --anahat ile bloklamaz), ❌ sayilir.
  D) HERMETIKLIK — ayni girdiyle N kosum AYNI sonuc (flaky CI = yayin kilidi).
  E) CAPA TARAMASI — kategori ekseni kodunda sabit sayi / SHA / tarih capasi YOK
     (katalog her gun buyur; capa yarin kirmizi yanip yayini durdurur).

MUTASYON DAIMA GECICI SYMLINK AYNASINA uygulanir — canli tools/ dizinine YAZMA YOK
(bu depoda yasandi: kesinti calisma agacinda mutant birakti). Ayna ayrica .git tasimaz,
bu yuzden konfigur-test c4 referansini bulamaz -> ⚪ OLCULEMEDI; harness bu yuzden
nobetciyi DAIMA "--anahat" ile kosar (⚪ bloklamaz, KIRMIZI/YESIL ayrimi bozulmaz).

Offline: ag YOK, urunler.json OKUNMAZ, canli uc/D1/R2/Drive OKUNMAZ.
Kullanim:  python3 tools/konfigur-nobet-mutasyon.py     (0 = hepsi gecti, 1 = en az bir kusur)
"""
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable or "python3"
NOBETCI = "konfigur-test.py"
FAILS = []

# Aynaya TASINMAYAN kok girdileri: urun VERISI (nobetci okumaz, kazayla okursa gorulsun),
# git dizini (c4 referansi kasitli olarak ALINMAZ) ve agir/gereksiz agaclar.
AYNA_HARIC = {".git", ".claude", "urun", "urunler.json", ".urun-kaynaklari.json",
              ".urunler.lock", "node_modules", "stl"}


def check(etiket, kosul, detay=""):
    print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", etiket,
                           ("  -> " + detay) if detay else ""))
    if not kosul:
        FAILS.append(etiket)
    return kosul


# ---------------------------------------------------------------- ayna (mutasyon KOPYASI)
def ayna_kur(hedef_kok, mutasyonlar=None):
    """<hedef_kok>/tools/ = canli tools/ symlink aynasi; <hedef_kok>/ = kok agacin aynasi.

    mutasyonlar: {dosya_adi: [(eski, yeni), ...]} -> o dosya GERCEK KOPYA olarak yazilir.
    Mutasyonun metni GERCEKTEN degistirdigi DOGRULANIR; degistirmiyorsa harness BAYATTIR
    (kod degismis, mutasyon artik bir sey bozmuyor) -> SystemExit ile gurultulu olur."""
    mutasyonlar = mutasyonlar or {}
    tools_h = os.path.join(hedef_kok, "tools")
    os.makedirs(tools_h, exist_ok=True)
    for ad in os.listdir(HERE):
        kaynak = os.path.join(HERE, ad)
        if not os.path.isfile(kaynak):
            continue
        hedef = os.path.join(tools_h, ad)
        if ad in mutasyonlar:
            with open(kaynak, encoding="utf-8") as f:
                metin = f.read()
            for eski, yeni in mutasyonlar[ad]:
                if eski not in metin:
                    raise SystemExit(
                        "HARNESS BAYAT: %s icinde mutasyon dayanagi bulunamadi: %r\n"
                        "(kod degismis olabilir — mutasyonu guncelle; yoksa bu harness "
                        "HICBIR SEY olcmuyor demektir)" % (ad, eski[:120]))
                metin = metin.replace(eski, yeni)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin)
        else:
            os.symlink(kaynak, hedef)
    # KOK GIRDILERI: dosyalar symlink (yalniz OKUNUR), DIZINLER ise KOPYA.
    # ⚠️ Ölçüldü (bu iş sırasında yaşandı): kök dizinleri symlink'lersen aynada koşan bir
    # betiğin yazması symlink'i AŞARAK CANLI checkout'u kirletir (elle yazılmış yasal
    # sayfalar ` M` oldu). Dizin kopyası bu yolu fiziksel olarak kapatır (kök ağacı küçük).
    for ad in os.listdir(ROOT):
        if ad in AYNA_HARIC or ad == "tools":
            continue
        kaynak = os.path.join(ROOT, ad)
        hedef = os.path.join(hedef_kok, ad)
        if os.path.isdir(kaynak) and not os.path.islink(kaynak):
            shutil.copytree(kaynak, hedef, symlinks=True)
        else:
            os.symlink(kaynak, hedef)
    return tools_h


def kos(mutasyonlar=None):
    """Nobetciyi mutasyonlu aynada kosar. Doner: (cikis_kodu, stdout, kirmizi_satirlar)."""
    tmp = tempfile.mkdtemp(prefix="konfigur-nobet-")
    try:
        tools_h = ayna_kur(tmp, mutasyonlar)
        r = subprocess.run([PY, os.path.join(tools_h, NOBETCI), "--anahat"],
                           capture_output=True, text=True, timeout=300)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    cikti = (r.stdout or "") + (r.stderr or "")
    kirmizi = [s.strip() for s in cikti.splitlines() if "❌" in s]
    return r.returncode, cikti, kirmizi


# ---------------------------------------------------------------- A) kategori ekseni
BUILD = "build.py"
SAYFALAR = "sayfalar.py"
FILAMENTLER = "filamentler.json"
_FONK_SATIR = "FONKSIYONEL_KATEGORILER = ["


def _satir(dosya, onek):
    with open(os.path.join(HERE, dosya), encoding="utf-8") as f:
        for satir in f:
            if satir.startswith(onek):
                return satir.rstrip("\n")
    raise SystemExit("HARNESS BAYAT: %s icinde %r ile baslayan satir yok" % (dosya, onek))


def fonk_dusur(kat):
    """build.py FONKSIYONEL_KATEGORILER satirindan <kat> ogesini dusuren mutasyon."""
    eski = _satir(BUILD, _FONK_SATIR)
    yeni = eski.replace('"%s", ' % kat, "", 1)
    if yeni == eski:
        yeni = eski.replace(', "%s"' % kat, "", 1)
    if yeni == eski:
        raise SystemExit("HARNESS BAYAT: %r FONKSIYONEL_KATEGORILER satirinda yok "
                         "(kategori adi degismis olabilir)" % kat)
    return {BUILD: [(eski, yeni)]}


def bolum_a():
    print("\nA) KIRMIZI MUTASYON — KATEGORI EKSENI (FONKSIYONEL_KATEGORILER'den dusurme)")
    print("   Kabul: cikis 1 (KIRMIZI) + kirmizi satir O KATEGORIYI adiyla soyluyor.")
    # Nobetcinin KENDI fikstur listesi tek kaynak — burada ikinci kopya YOK.
    kategoriler = _fikstur_kategorileri()
    print("   Olculen kategori: %s" % ", ".join(kategoriler))
    for kat in kategoriler:
        rc, cikti, kirmizi = kos(fonk_dusur(kat))
        isaretli = [s for s in kirmizi if kat in s]
        check("MUT-KAT[%s] -> KIRMIZI + kendi adiyla" % kat,
              rc == 1 and bool(isaretli),
              "cikis=%d kirmizi=%d isaretli=%s"
              % (rc, len(kirmizi), (isaretli[0][:110] if isaretli else "YOK")))


def _fikstur_kategorileri():
    """konfigur-test.py'nin KATEGORI_FIKSTURLERI listesini KAYNAKTAN okur (ikinci kopya YOK).
    Liste bulunamazsa harness bayattir -> gurultulu duser."""
    with open(os.path.join(HERE, NOBETCI), encoding="utf-8") as f:
        metin = f.read()
    m = re.search(r"^KATEGORI_FIKSTURLERI = \[(.*?)\]", metin, re.S | re.M)
    if not m:
        raise SystemExit("HARNESS BAYAT: %s icinde KATEGORI_FIKSTURLERI listesi yok "
                         "(kategori ekseni kaldirilmis olabilir)" % NOBETCI)
    return re.findall(r'"([^"]+)"', m.group(1))


# ---------------------------------------------------------------- B) olu iddia / bolge
# Govdedeki "Malzeme Rehberi" linkini KALDIRIR, footer nav'daki AYNI linki DOKUNMADAN
# birakir. Eski (bolgesiz) iddia footer kopyasiyla karsilanip YESIL yanardi.
OLU_REHBER = {BUILD: [(
    """        return ('<div class="malzeme-blok">%s'
                '<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede kullanılır? '
                'Malzeme Rehberi &rarr;</a>'
                '</div>' % wa_html)""",
    """        return ('<div class="malzeme-blok">%s'
                '</div>' % wa_html)""")]}

# Govdedeki WhatsApp notunun wa.me hedefini bozar; sayfadaki WhatsApp IKON butonu
# (ayni numarayi tasir) DOKUNULMAZ -> eski iddia ikon butonla karsilanip YESIL yanardi.
OLU_WA_NOT = {BUILD: [(
    """'üretim için <a href="https://wa.me/' + WHATSAPP""",
    """'üretim için <a href="https://ornek.test/' + WHATSAPP""")]}


def bolum_b():
    print("\nB) KIRMIZI MUTASYON — OLU IDDIA / BOLGE KURALI (govde silinir, footer kalir)")
    for etiket, mut, isaret in (
            ("MUT-OLU-REHBER (govdedeki Malzeme Rehberi linki silindi, footer nav duruyor)",
             OLU_REHBER, "Malzeme Rehberi"),
            ("MUT-OLU-WA-NOT (govde notunun wa.me hedefi bozuldu, ikon buton duruyor)",
             OLU_WA_NOT, "WhatsApp notu")):
        rc, cikti, kirmizi = kos(mut)
        isaretli = [s for s in kirmizi if isaret in s]
        check(etiket + " -> KIRMIZI", rc == 1 and bool(isaretli),
              "cikis=%d kirmizi=%d isaretli=%s"
              % (rc, len(kirmizi), (isaretli[0][:110] if isaretli else "YOK")))


# ---------------------------------------------------------------- C) yanlis-pozitif
def yanlis_pozitif_senaryolari():
    """Konfigur/kategori eksenine DOKUNMAYAN rutin duzenlemeler -> hepsi YESIL kalmali."""
    kat_satir = _satir(BUILD, "CATEGORIES = [")
    return [
        ("FP-CSS (salt gorsel sinif kurali degisti)", {BUILD: [(
            ".fil-cip:hover{border-color:var(--navy-2)}",
            ".fil-cip:hover{border-color:var(--navy)}")]}),
        ("FP-SCRIPT-SRC (urun sayfasina yeni harici betik eklendi)", {BUILD: [(
            '<script src="/secenekler.js"></script>',
            '<script src="/secenekler.js"></script>\n'
            '<script src="/analitik-deneme.js"></script>')]}),
        ("FP-FOOTER-NAV (footer nav linki + metni degisti)", {SAYFALAR: [(
            '<a href="/malzeme-rehberi/">Malzeme Rehberi</a> &middot; ',
            '<a href="/malzeme-kilavuzu/">Malzeme Kılavuzu</a> &middot; ')]}),
        ("FP-YENI-KATEGORI (CATEGORIES'e yeni kategori eklendi = katalog buyumesi)",
         {BUILD: [(kat_satir, kat_satir[:-1] + ', "Deneme"]')]}),
        ("FP-YENI-FILAMENT (filamentler.json'a satista yeni malzeme = cip sayisi degisti)",
         {FILAMENTLER: [('      "ad": "TPU",\n      "site": true,\n'
                         '      "uzunAd": "TPU (esnek)",',
                         '      "ad": "Deneme Malzeme",\n'
                         '      "site": true,\n'
                         '      "kisaEtiket": "Deneme",\n'
                         '      "isiDayanimi": "~60-65°C",\n'
                         '      "uv": "Düşük",\n'
                         '      "su": "Düşük",\n'
                         '      "darbe": "Düşük",\n'
                         '      "kisa": "Harness fiksturu.",\n'
                         '      "uzun": "Harness fiksturu."\n'
                         '    },\n'
                         '    {\n'
                         '      "ad": "TPU",\n      "site": true,\n'
                         '      "uzunAd": "TPU (esnek)",')]}),
        ("FP-GOVDE-METNI (gorunen govde metni degisti)", {BUILD: [(
            '<div class="malzeme-baslik">Malzeme</div>',
            '<div class="malzeme-baslik">Malzeme seçimi</div>')]}),
    ]


def bolum_c():
    print("\nC) YANLIS-POZITIF FIKSTURU — ilgisiz rutin degisiklik YESIL kalmali")
    print("   (bu nobetci deploy'u bloklar: bir yanlis-pozitif TUM SITE yayinini durdurur)")
    for etiket, mut in yanlis_pozitif_senaryolari():
        rc, cikti, kirmizi = kos(mut)
        check(etiket + " -> YESIL", rc == 0 and not kirmizi,
              "cikis=%d kirmizi=%d %s" % (rc, len(kirmizi),
                                          (kirmizi[0][:110] if kirmizi else "")))


# ---------------------------------------------------------------- D) hermetiklik
TEKRAR = 10


def bolum_d():
    print("\nD) HERMETIKLIK — ayni girdiyle %d kosum AYNI sonuc (flaky CI = yayin kilidi)"
          % TEKRAR)
    parmak = []
    for _ in range(TEKRAR):
        rc, cikti, kirmizi = kos()
        parmak.append((rc, cikti.count("✅"), cikti.count("❌"), cikti.count("⚪")))
    tekil = sorted(set(parmak))
    check("%d/%d kosum ayni (cikis, ✅, ❌, ⚪)" % (parmak.count(parmak[0]), TEKRAR),
          len(tekil) == 1, "gorulen parmak izleri: %s" % (tekil,))
    # URUN VERISI BAGIMSIZLIGI — GRAMER DEGIL ICRA kaniti: ayna urunler.json'u
    # (ve .urun-kaynaklari.json'u) HIC TASIMAZ. Taban yesil oldugu icin nobetci o
    # dosyalari okumuyor demektir; okusaydi acilis hatasiyla duserdi. Yani katalog
    # buyumesi/degismesi bu nobetciyi YAPISAL OLARAK etkileyemez.
    check("ayna urun verisi TASIMIYOR (urunler.json + gizli kayit yok) ve taban YESIL",
          "urunler.json" in AYNA_HARIC and ".urun-kaynaklari.json" in AYNA_HARIC,
          "haric tutulanlar: %s" % ", ".join(sorted(AYNA_HARIC)))
    # Ag/canli-uc bagimliligi kaynakta ARANIR (kosumda tesadufen tetiklenmemis olabilir).
    # Jetonlar CAGRI/IMPORT bicimindedir: fikstur icindeki gorsel URL'i (asla fetch edilmez)
    # ya da "urunler.json OKUNMAZ" aciklamasi yanlis-pozitif olmasin.
    with open(os.path.join(HERE, NOBETCI), encoding="utf-8") as f:
        kaynak = f.read()
    yasak = [d for d in (r"import\s+urllib", r"import\s+requests", r"import\s+socket",
                         r"from\s+urllib", r"urlopen\s*\(", r"requests\.\w+\s*\(",
                         r"build\.JSON_PATH", r"load_products\s*\(",
                         r"open\([^)]*urunler\.json")
             if re.search(d, kaynak)]
    check("nobetci kaynaginda ag cagrisi / urun verisi okuma cagrisi yok",
          not yasak, "bulunan: %s" % (yasak or "-"))


# ---------------------------------------------------------------- E) capa taramasi
CAPA_DESENLERI = [
    (r"[=!<>]=\s*\d+", "sayisal esik/karsilastirma capasi"),
    (r"\b\d{3,}\b", "uc haneli+ sabit sayi (urun/kategori adedi capasi)"),
    (r"\b[0-9a-f]{7,}\b", "SHA benzeri sabit"),
    (r"\b\d{4}-\d{2}-\d{2}\b", "ISO tarih capasi"),
]


def bolum_e():
    print("\nE) CAPA TARAMASI — kategori ekseni + bolge kodunda sabit sayi/SHA/tarih YOK")
    sys.path.insert(0, HERE)
    import importlib.util
    spec = importlib.util.spec_from_file_location("konfigur_test_modul",
                                                 os.path.join(HERE, NOBETCI))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    parcalar = {}
    for ad in ("govde", "blok", "_slug", "kategori_fiksturleri", "kategori_yoklamasi"):
        parcalar[ad] = inspect.getsource(getattr(modul, ad))
    parcalar["KATEGORI_FIKSTURLERI"] = repr(modul.KATEGORI_FIKSTURLERI)
    parcalar["KART_SECIM_CEKIRDEK"] = repr(modul.KART_SECIM_CEKIRDEK)
    for ad, metin in sorted(parcalar.items()):
        # Yorumlar cikarilir: capa ANLAMI KODDA olur, aciklamada olcum notu serbesttir.
        kod = "\n".join(s.split("#")[0] for s in metin.splitlines())
        # Metin sabitlerinin ICI de bosaltilir: fiksture VERILEN deger (or. fiyat metni)
        # bir esik/beklenti capasi degildir; capa, KOD konumundaki sabittir (or. "== 14").
        kod = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'', '""', kod)
        bulunan = []
        for desen, aciklama in CAPA_DESENLERI:
            for isabet in re.findall(desen, kod):
                bulunan.append("%s (%s)" % (isabet, aciklama))
        check("capa yok: %s" % ad, not bulunan, "; ".join(bulunan[:4]))


# ---------------------------------------------------------------- ana akis
def _canli_agac_parmagi():
    """CANLI checkout'un izlenen dosyalarinin (ad, boyut, mtime) parmak izi — harness
    hicbir dosyayi degistirmemeli. git KULLANMAZ (harness'in kendisi de hermetik kalir)."""
    parmak = {}
    for kok, dizinler, dosyalar in os.walk(ROOT):
        dizinler[:] = [d for d in dizinler if d not in AYNA_HARIC and d != "tools"]
        for d in dosyalar:
            y = os.path.join(kok, d)
            try:
                st = os.stat(y)
            except OSError:
                continue
            parmak[os.path.relpath(y, ROOT)] = (st.st_size, int(st.st_mtime))
    return parmak


def main():
    print("KONFIGUR NOBETCISI MUTASYON + YANLIS-POZITIF HARNESS'I")
    print("(mutasyon DAIMA gecici aynada — canli tools/ dizinine yazma YOK)")
    agac_once = _canli_agac_parmagi()
    rc, cikti, kirmizi = kos()
    print("\nTABAN (mutasyonsuz ayna): cikis=%d ✅=%d ❌=%d ⚪=%d"
          % (rc, cikti.count("✅"), cikti.count("❌"), cikti.count("⚪")))
    if not check("TABAN YESIL (mutasyonsuz ayna bozuk degil)", rc == 0 and not kirmizi,
                 kirmizi[0][:140] if kirmizi else ""):
        print("\nTaban kirmizi -> mutasyon sonuclari anlamsiz olur, DURDU.")
        return 1
    bolum_a()
    bolum_b()
    bolum_c()
    bolum_d()
    bolum_e()
    print("\nF) CANLI AGAC DOKUNULMAZLIGI — harness hicbir repo dosyasini degistirmedi")
    agac_sonra = _canli_agac_parmagi()
    degisen = sorted(y for y in set(agac_once) | set(agac_sonra)
                     if agac_once.get(y) != agac_sonra.get(y))
    check("canli checkout'ta degisen dosya YOK", not degisen,
          "degisen: %s" % (degisen[:6] or "-"))
    print("\n" + "-" * 70)
    if FAILS:
        print("SONUC: KIRMIZI ❌  (%d kusur)" % len(FAILS))
        for f in FAILS:
            print("   ❌ " + f)
        return 1
    print("SONUC: YESIL ✅  (mutasyonlar kirmizi yaniyor, ilgisiz degisiklikler yesil kaliyor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
