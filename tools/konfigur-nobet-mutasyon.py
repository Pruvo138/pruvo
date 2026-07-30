#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR NOBETCISI (tools/konfigur-test.py) MUTASYON + YANLIS-POZITIF HARNESS'I.

NE ISE YARAR: konfigur-test.py'nin KENDISI bir nobetcidir ve deploy'u BLOKLAR; onun
iddialarinin GERCEKTEN tasiyici olup olmadigini bu betik olcer. "Nobetci yesil yaniyor"
bir sey KANITLAMAZ — kanit, bozulmayi enjekte edince KIRMIZI yanmasi (mutasyon) VE
ilgisiz rutin duzenlemede YESIL kalmasidir (yanlis-pozitif fiksturu).

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
  C) RUTIN DUZENLEME MATRISI — bu deponun EN PAHALI eksenidir (nobetci deploy'u bloklar;
     bir yanlis-pozitif TUM SITE yayinini durdurur). 25 GERCEKCI rutin duzenleme
     KALICI fikstur olarak kosulur; her fikstur BEYAN EDILMIS bir beklentiyle gelir:
       YESIL -> ilgisiz duzenleme, kapi yesil KALMALI (hard assert)
       BORC  -> 🟠 mimar onayli BEYAN EDILMIS bakim borcu, kapi KIRMIZI yanar (assert)
       MIRAS -> 🔴 merge-base'den MIRAS yanlis-pozitif, ayri is olarak ACIK (assert)
     Beklenti ile olculen AYRISIRSA harness KIRMIZI yanar — HER IKI YONDE. Yani bir
     borc/miras sessizce kapanirsa da FAIL olur: kapanan borcun beyani (nobetcideki
     ne_olculmedi()) guncellenmek ZORUNDADIR. "Sessiz drift" boyle kapanir.
     Her fikstur HEM guncel nobetciyle HEM merge-base nobetcisiyle kosulur -> "dalin
     GETIRDIGI yanlis-pozitif" ile "MIRAS" birbirinden ayrisir. Ana hatta iki nobetci
     BAYT AYNI olur (referans totolojisi) -> BASE kolonu ⚪ olarak DUSER, DAL kolonu
     kalici korumadir. ⚪ OLCULEMEDI yanlis-pozitif SAYILMAZ (sozlesme: --anahat ile
     bloklamaz), ❌ sayilir.
  D) HERMETIKLIK — ayni girdiyle N kosum AYNI sonuc (flaky CI = yayin kilidi).
  E) CAPA TARAMASI — kategori ekseni kodunda sabit sayi / SHA / tarih capasi YOK
     (katalog her gun buyur; capa yarin kirmizi yanip yayini durdurur).
  F) AYNA DOKUNULMAZLIGI — aynanin kaynak agaca YAZMA YOLU var mi? Aynadaki HER dosyaya
     ve HER dizine yazma denenir, sonra kaynak agacin TUM dosyalarinin sha256'si
     karsilastirilir. Ayrica her kosumdan sonra ayni sha256 olcumu yapilir.
  G) ANA HAT ETKISI — bugun main'de rutin bir refaktor yayini durduruyor mu? (olcum,
     mimar karari icin; bu bolum FAIL uretmez, BULGU basar.)

⚠️ MUTASYON DAIMA GECICI AYNAYA uygulanir ve AYNA TAMAMEN GERCEK KOPYADIR — kaynak
agaca giden HICBIR symlink yoktur (ne tools/ dosyalari ne kok dosyalar). Bu depoda
ikisi de yasandi: (1) kok DIZINLERI symlink'lerken aynada kosan betik elle yazilmis
yasal sayfalari kirletti; (2) kok DOSYALARI symlink kalinca aynadaki dosyaya yazmak
symlink'i ASIP CANLI checkout'u eziyordu (kum havuzunda kanitlandi: taban-fiyatlar.js).
Ayna ayrica .git tasimaz, bu yuzden konfigur-test c4 referansini bulamaz -> ⚪
OLCULEMEDI; harness bu yuzden nobetciyi DAIMA "--anahat" ile kosar.

Offline: ag YOK, urunler.json canli hali OKUNMAZ (yalniz sha256'lanir), canli uc/D1/R2
OKUNMAZ. Bu harness CI'da KOSMAZ (mimar karari: bedeli + ust uste binen iki savunma
katmani birbirinin testini maskeler) — gelistirici/curutucu araci.
Kullanim:  python3 tools/konfigur-nobet-mutasyon.py     (0 = hepsi gecti, 1 = en az bir kusur)
"""
import hashlib
import importlib.util
import inspect
import json
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

# Aynaya TASINMAYAN kok girdileri: urun VERISI (nobetci okumaz; kazayla okursa acilis
# hatasiyla duser = ICRA kaniti), git dizini (c4 referansi kasitli olarak ALINMAZ) ve
# agir/gereksiz agaclar. ⚠️ Bu kume AYNA icin gecerlidir; DOKUNULMAZLIK parmak izi
# urunler.json'u DA kapsar (aynada yok ama kaynakta korunmasi gereken en degerli dosya).
AYNA_HARIC = {".git", ".claude", "urun", "urunler.json", ".urun-kaynaklari.json",
              ".urunler.lock", "node_modules", "stl"}

# Parmak izinden dislanan yollar: git veritabani, ajan/oturum dizinleri (kendi kendine
# degisir), urun/ (build.py cikti agaci, bu harness uretmez) ve isletim sistemi copu.
# __pycache__ TURETILMIS artefakttir (gitignore) ve bu harness'in KENDI ic-surec importu
# (E bolumu) onu tazeler -> parmak izine girerse HER kosum sahte kirmizi olur. Dislanmasi
# iddiayi zayiflatmaz: "ayna kaynaga yazamaz" iddiasinin TASIYICISI F bolumundeki
# "aynada symlink = 0" olcumudur; sha256 karsilastirmasi onun teyidi. Ayrica E bolumu
# artik sys.dont_write_bytecode ile hic .pyc YAZMAZ.
PARMAK_HARIC_DIZIN = {".git", ".claude", "urun", "node_modules", "stl", "__pycache__"}
PARMAK_HARIC_DOSYA = {".DS_Store", ".git", ".urunler.lock"}


def check(etiket, kosul, detay=""):
    print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", etiket,
                           ("  -> " + detay) if detay else ""))
    if not kosul:
        FAILS.append(etiket)
    return kosul


# ------------------------------------------------- KAYNAK AGAC DOKUNULMAZLIGI (sha256)
def kaynak_parmagi():
    """Kaynak agacin TUM dosyalarinin sha256'si {gorece_yol: sha}. Symlink'ler hedef
    YOLUYLA kaydedilir (yeniden hedeflenme de degisiklik sayilir). urunler.json DAHIL
    (11 MB'lik dosya bile ~0,02 s'de ozetlenir) -> her kosumdan sonra calistirilabilir.
    DOSYA SAYISI CAPASI YOK: sayi kosumda olculur ve raporlanir, kodda karsilastirilmaz."""
    parmak = {}
    for kok, dizinler, dosyalar in os.walk(ROOT):
        dizinler[:] = [d for d in dizinler if d not in PARMAK_HARIC_DIZIN]
        for d in dosyalar:
            if d in PARMAK_HARIC_DOSYA:
                continue
            y = os.path.join(kok, d)
            gy = os.path.relpath(y, ROOT)
            try:
                if os.path.islink(y):
                    parmak[gy] = "LINK:" + os.readlink(y)
                    continue
                with open(y, "rb") as f:
                    parmak[gy] = hashlib.sha256(f.read()).hexdigest()
            except OSError as e:
                parmak[gy] = "OKUNAMADI:%s" % e.errno
    return parmak


KAYNAK_TABAN = {}          # harness basinda alinan referans parmak izi
DOKUNULMAZ_KOSUM = [0, 0]  # [temiz kosum, kirli kosum]


def dokunulmazlik_olc(etiket):
    """Her kosumdan SONRA: kaynak agac degisti mi? Degistiyse ANINDA kirmizi."""
    simdi = kaynak_parmagi()
    degisen = sorted(y for y in set(KAYNAK_TABAN) | set(simdi)
                     if KAYNAK_TABAN.get(y) != simdi.get(y))
    if degisen:
        DOKUNULMAZ_KOSUM[1] += 1
        check("KAYNAK AGAC DEGISTI (ayna kacagi!) [%s]" % etiket, False,
              "%d dosya: %s" % (len(degisen), degisen[:6]))
    else:
        DOKUNULMAZ_KOSUM[0] += 1
    return degisen


# ---------------------------------------------------------------- ayna (TAM KOPYA)
def _mut_yolu(anahtar):
    """Mutasyon/ek-dosya anahtari -> ayna icindeki gorece yol. '/' iceren anahtar
    depo-koku goreceli ('index.html'), icermeyen anahtar tools/ altidir ('build.py')."""
    return anahtar if "/" in anahtar else os.path.join("tools", anahtar)


def ayna_kur(hedef_kok, mutasyonlar=None, ek_dosyalar=None, nobetci_metni=None):
    """<hedef_kok> = canli agacin TAM KOPYA aynasi. KAYNAGA GIDEN SYMLINK YOKTUR.

    mutasyonlar : {anahtar: [(eski, yeni), ...]} -> o dosyanin kopyasinda metin degisimi.
                  Mutasyonun metni GERCEKTEN degistirdigi DOGRULANIR; degistirmiyorsa
                  harness BAYATTIR (kod degismis, mutasyon artik bir sey bozmuyor) ->
                  SystemExit ile gurultulu olur.
    ek_dosyalar : {anahtar: icerik} -> aynada olusturulan/uzerine yazilan dosya (kaynakta
                  olmayabilir; or. AYNA_HARIC'teki sentetik urunler.json).
    nobetci_metni: verilirse aynadaki tools/<NOBETCI> BU metinle yazilir (merge-base
                  nobetcisini kosmak icin)."""
    mutasyonlar = mutasyonlar or {}
    ek_dosyalar = ek_dosyalar or {}
    tools_h = os.path.join(hedef_kok, "tools")
    os.makedirs(tools_h, exist_ok=True)
    # tools/ dosyalari: HEPSI GERCEK KOPYA (symlink YOK -> aynada yazma kaynagi ezemez).
    for ad in os.listdir(HERE):
        kaynak = os.path.join(HERE, ad)
        if not os.path.isfile(kaynak):
            continue
        shutil.copy2(kaynak, os.path.join(tools_h, ad), follow_symlinks=True)
    # kok girdileri: dosyalar KOPYA, dizinler KOPYA AGAC (symlink'ler cozulerek).
    for ad in os.listdir(ROOT):
        if ad in AYNA_HARIC or ad == "tools":
            continue
        kaynak = os.path.join(ROOT, ad)
        hedef = os.path.join(hedef_kok, ad)
        if os.path.isdir(kaynak):
            shutil.copytree(kaynak, hedef, symlinks=False,
                            ignore_dangling_symlinks=True)
        else:
            try:
                shutil.copy2(kaynak, hedef, follow_symlinks=True)
            except OSError:
                pass          # kirik symlink: aynaya HIC tasinmaz (yazma yolu acilmaz)
    # mutasyonlar (kopya uzerinde, metin dogrulamali)
    for anahtar, degisimler in mutasyonlar.items():
        yol = os.path.join(hedef_kok, _mut_yolu(anahtar))
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        for eski, yeni in degisimler:
            if eski not in metin:
                raise SystemExit(
                    "HARNESS BAYAT: %s icinde mutasyon dayanagi bulunamadi: %r\n"
                    "(kod degismis olabilir — mutasyonu guncelle; yoksa bu harness "
                    "HICBIR SEY olcmuyor demektir)" % (anahtar, eski[:160]))
            metin = metin.replace(eski, yeni)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
    # ek dosyalar (aynada olmayan yolu da olusturur)
    for anahtar, icerik in ek_dosyalar.items():
        yol = os.path.join(hedef_kok, _mut_yolu(anahtar))
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
    if nobetci_metni is not None:
        with open(os.path.join(tools_h, NOBETCI), "w", encoding="utf-8") as f:
            f.write(nobetci_metni)
    return tools_h


def kos(mutasyonlar=None, ek_dosyalar=None, nobetci_metni=None, etiket="taban"):
    """Nobetciyi mutasyonlu aynada kosar; SONRA kaynak dokunulmazligini olcer.
    Doner: (cikis_kodu, stdout+stderr, kirmizi_satirlar)."""
    tmp = tempfile.mkdtemp(prefix="konfigur-nobet-")
    try:
        tools_h = ayna_kur(tmp, mutasyonlar, ek_dosyalar, nobetci_metni)
        r = subprocess.run([PY, os.path.join(tools_h, NOBETCI), "--anahat"],
                           capture_output=True, text=True, timeout=300)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    dokunulmazlik_olc(etiket)
    cikti = (r.stdout or "") + (r.stderr or "")
    kirmizi = [s.strip() for s in cikti.splitlines() if "❌" in s]
    return r.returncode, cikti, kirmizi


# ---------------------------------------------------------------- A) kategori ekseni
BUILD = "build.py"
SAYFALAR = "sayfalar.py"
FILAMENTLER = "filamentler.json"
_FONK_SATIR = "FONKSIYONEL_KATEGORILER = ["
_KAT_SATIR = "CATEGORIES = ["


def _satir(dosya, onek):
    with open(os.path.join(HERE, dosya), encoding="utf-8") as f:
        for satir in f:
            if satir.startswith(onek):
                return satir.rstrip("\n")
    raise SystemExit("HARNESS BAYAT: %s icinde %r ile baslayan satir yok" % (dosya, onek))


def _satir_ogeleri(dosya, onek):
    return re.findall(r'"([^"]+)"', _satir(dosya, onek))


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


def fonk_ekle(kat):
    """TERS MUTANT: FONKSIYONEL olmayan kategoriyi (or. semasiz Jeneratör) listeye EKLER.
    O kategorinin sayfalari panelsiz dalindan kart-secim dalina atlar = ayni sinif hata."""
    eski = _satir(BUILD, _FONK_SATIR)
    if ('"%s"' % kat) in eski:
        raise SystemExit("HARNESS BAYAT: %r FONKSIYONEL_KATEGORILER'de ZATEN var -> ters "
                         "mutant anlamsiz (kategori sinifi degismis olabilir)" % kat)
    return {BUILD: [(eski, eski[:-1] + ', "%s"]' % kat)]}


def bolum_a():
    print("\nA) KIRMIZI MUTASYON — KATEGORI EKSENI (FONKSIYONEL_KATEGORILER mutasyonu)")
    print("   Evren = build.py'nin KENDI beyani (CATEGORIES + NAV_GIZLI) — sabit sayi YOK.")
    print("   FONKSIYONEL kategori DUSURULUR; olmayan (semasiz) kategori ters mutantla")
    print("   EKLENIR. Kabul: her kategoride cikis 1 (nobetsiz kategori = 0); nobetcinin")
    print("   KENDI fikstur listesindeki kategorilerde ayrica ADIYLA isaret sarti.")
    beyan = _satir_ogeleri(BUILD, _KAT_SATIR) + _satir_ogeleri(BUILD, "NAV_GIZLI = [")
    fonksiyonel = _satir_ogeleri(BUILD, _FONK_SATIR)
    fikstur_kat = _fikstur_kategorileri()          # nobetcinin tek kaynagi, kopya YOK
    print("   Beyan edilmis kategori (%d): %s" % (len(beyan), ", ".join(beyan)))
    adiyla = 0
    nobetsiz = []
    for kat in beyan:
        ters = kat not in fonksiyonel
        mut = fonk_ekle(kat) if ters else fonk_dusur(kat)
        rc, cikti, kirmizi = kos(mut, etiket="MUT-KAT[%s]" % kat)
        isaretli = [s for s in kirmizi if kat in s]
        if isaretli:
            adiyla += 1
        if rc != 1:
            nobetsiz.append(kat)
        # Fikstur listesindeki kategoride ADIYLA isaret ZORUNLU (kaza eseri kirmizi
        # kabul edilmez). Sayfa-sinifi fiksturuyle kaplanan kategorilerde (Otomobil/Ev/
        # Kamera/Jeneratör) kirmizi satir SAYFA SINIFINI adlandirir -> yalnizca KIRMIZI
        # sarti; teshis eksikligi merge-base'den miras, nobetsizlik DEGIL.
        ad_sarti = kat in fikstur_kat
        check("MUT-KAT[%s]%s -> KIRMIZI%s" % (kat, " (TERS)" if ters else "",
                                              " + kendi adiyla" if ad_sarti else ""),
              rc == 1 and (bool(isaretli) or not ad_sarti),
              "cikis=%d kirmizi=%d isaretli=%s"
              % (rc, len(kirmizi), (isaretli[0][:100] if isaretli else "YOK")))
    print("   --- KATEGORI MATRISI: %d/%d kategori KIRMIZI · adiyla isaret eden %d/%d ---"
          % (len(beyan) - len(nobetsiz), len(beyan), adiyla, len(beyan)))
    check("NOBETSIZ kategori = 0 (mutasyonu sessizce yesil gecen kategori yok)",
          not nobetsiz, "nobetsiz: %s" % (nobetsiz or "-"))


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

# BOLGE FIKSTURLERI — govdedeki link SILINIR, iddia dizgesi YALNIZ hedef bolgeye konur.
# Kabul: nobetci HER DORDUNDE KIRMIZI (bolge disindaki kopyayi karsilanmis SAYMAZ).
# Bunlar ayni zamanda "civi degil BOLGE tasiyor" kanitidir: 2. fikstur footer nav'a TAM
# civili anchor koyar (sinif + oznitelik sirasi + tam metin) ve iddia HALA karsilanmaz.
CIVILI_ANCHOR = ('<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede '
                 'kullanılır? Malzeme Rehberi &rarr;</a>')

OLU_REHBER_CIVILI_FOOTER = {
    BUILD: OLU_REHBER[BUILD],
    SAYFALAR: [('    \'<a href="/malzeme-rehberi/">Malzeme Rehberi</a> &middot; \'',
                "    '" + CIVILI_ANCHOR + " &middot; '")],
}

# head bolgesi: govde silinir, TAM civili anchor <head> icine (og etiketlerinin yanina)
# enjekte edilir. govde() yalniz <main> okudugu icin iddia karsilanmamalidir.
OLU_REHBER_HEAD = {BUILD: OLU_REHBER[BUILD] + [(
    '<meta property="og:type" content="product">',
    '<meta property="og:type" content="product">\n' + CIVILI_ANCHOR)]}

# <main> ICI <script>: govde silinir, anchor <main> icindeki bir inline script'e JS
# DIZGESI olarak konur. Olculdu: urun sayfasinin <main> blogunda normalde hic inline
# script/style YOK -> bu fikstur _BOLGE_DISI (script soyma) savunmasini ENJEKTE EDEREK
# olcer; soyma calismazsa iddia sahte karsilanip YESIL yanardi.
OLU_REHBER_MAIN_SCRIPT = {BUILD: OLU_REHBER[BUILD] + [(
    '<main>\n  <nav class="crumbs" aria-label="breadcrumb">',
    '<main>\n  <script>var _harness = \'' + CIVILI_ANCHOR + '\';</script>\n'
    '  <nav class="crumbs" aria-label="breadcrumb">')]}


def bolum_b():
    print("\nB) OLU IDDIA MUTANTLARI + BOLGE FIKSTURLERI (govde silinir, kopya kalir)")
    print("   Kabul: dordunde de KIRMIZI — bolge disindaki kopya iddiayi KARSILAMAZ.")
    for etiket, mut, isaret in (
            ("BOLGE-1/OLU-REHBER  footer: gercek FOOT_NAV_HTML duruyor",
             OLU_REHBER, "Malzeme Rehberi"),
            ("BOLGE-2/OLU-REHBER  footer nav'a TAM CIVILI anchor kondu",
             OLU_REHBER_CIVILI_FOOTER, "Malzeme Rehberi"),
            ("BOLGE-3             head'e TAM CIVILI anchor kondu",
             OLU_REHBER_HEAD, "Malzeme Rehberi"),
            ("BOLGE-4             <main> ici <script>'e JS dizgesi olarak kondu",
             OLU_REHBER_MAIN_SCRIPT, "Malzeme Rehberi"),
            ("OLU-WA-NOT          govde notunun wa.me hedefi bozuldu, IKON buton duruyor",
             OLU_WA_NOT, "WhatsApp notu")):
        rc, cikti, kirmizi = kos(mut, etiket=etiket[:20])
        isaretli = [s for s in kirmizi if isaret in s]
        check(etiket + " -> KIRMIZI", rc == 1 and bool(isaretli),
              "cikis=%d kirmizi=%d isaretli=%s"
              % (rc, len(kirmizi), (isaretli[0][:100] if isaretli else "YOK")))


# ------------------------------------------------------- C) rutin duzenleme matrisi
# SENTETIK katalog: nobetci urunler.json'u OKUMAZ (D bolumu bunu ICRAYLA kanitliyor:
# ayna dosyayi hic tasimadigi halde taban YESIL). R12/R13 bu bagisikligi TERSTEN olcer —
# ayna urun verisi TASIRSA ve o veri degisirse de kapi kimildamiyor mu? Gercek 12k'lik
# katalog kullanilmaz: (1) parmak izi/ayna maliyeti, (2) veri capasi yasagi.
def _sentetik_katalog(yeni_urun=False, marin_bos=True):
    urunler = [
        {"id": "harness-oto-1", "kategori": "Otomobil", "marka": ["Audi"],
         "baslik": "Harness Oto Parcasi", "aciklama": "Fikstur.", "fiyat": "850 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/harness-1.jpg"]},
        {"id": "harness-ev-1", "kategori": "Ev", "marka": [],
         "baslik": "Harness Ev Parcasi", "aciklama": "Fikstur.", "fiyat": "300 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/harness-2.jpg"]},
    ]
    if not marin_bos:
        urunler.append({"id": "harness-marin-1", "kategori": "Marin", "marka": [],
                        "baslik": "Harness Marin Parcasi", "aciklama": "Fikstur.",
                        "fiyat": "500 TL",
                        "gorseller": ["https://media.pruvo3d.com/urunler/harness-3.jpg"]})
    if yeni_urun:
        urunler.insert(0, {"id": "harness-yeni-urun", "kategori": "Dekorasyon",
                           "marka": [], "baslik": "Harness Yeni Urun",
                           "aciklama": "Dizinin BASINA eklendi.", "fiyat": "199 TL",
                           "gorseller": ["https://media.pruvo3d.com/urunler/harness-4.jpg"]})
    return json.dumps(urunler, ensure_ascii=False, indent=1)


# Sinif etiketleri
YESIL = "YESIL"      # ilgisiz rutin duzenleme: kapi YESIL kalmali
BORC = "BORC"        # 🟠 beyan edilmis bakim borcu: kapi KIRMIZI yanar (mimar onayli)
MIRAS = "MIRAS"      # 🔴 merge-base'den miras yanlis-pozitif: ACIK, ayri is


def rutin_fiksturler():
    """25 GERCEKCI rutin duzenleme. (kod, aciklama, mutasyon, ek_dosya, beklenti, isaret)
    isaret: beklenti KIRMIZI ise, kirmizi satirin ICERMESI gereken jeton (kaza eseri
    kirmiziyi kabul etmemek icin). YESIL beklentide kullanilmaz."""
    kat_satir = _satir(BUILD, _KAT_SATIR)
    fonk_satir = _satir(BUILD, _FONK_SATIR)
    link_anchor = '<a class="malzeme-link" href="/malzeme-rehberi/">'
    wa_p = '<p class="malzeme-not">Karbon fiber'
    crumbs_eski = ('  <nav class="crumbs" aria-label="breadcrumb">\n'
                   '    <a href="/">Ana Sayfa</a><span>&rsaquo;</span>\n'
                   '    <a href="{katq}">{kategori}</a><span>&rsaquo;</span>\n'
                   '    {baslik}\n'
                   '  </nav>')
    crumbs_yeni = ('      <nav class="crumbs" aria-label="breadcrumb">\n'
                   '        <a href="/">Ana Sayfa</a><span>&rsaquo;</span>\n'
                   '        <a href="{katq}">{kategori}</a><span>&rsaquo;</span>\n'
                   '        {baslik}\n'
                   '      </nav>')
    main_ac = '<main>\n  <nav class="crumbs" aria-label="breadcrumb">'
    return [
        ("R01", "CSS DEGER degisimi (.cart-btn:hover rengi)",
         {BUILD: [(".cart-btn:hover{background:var(--navy-2)}",
                   ".cart-btn:hover{background:var(--navy)}")]}, None, YESIL, ""),
        ("R02", "CSS SINIF ADI degisimi (malzeme-link -> malzeme-baglanti; sablon+stil)",
         {BUILD: [("malzeme-link", "malzeme-baglanti")]}, None, YESIL, ""),
        ("R03", "govde NOTUNA ikinci CSS sinifi (class=\"malzeme-not kucuk\")",
         {BUILD: [(wa_p, '<p class="malzeme-not kucuk">Karbon fiber')]}, None, YESIL, ""),
        ("R04", "govde LINKINE ikinci CSS sinifi (class=\"malzeme-link kucuk\")",
         {BUILD: [(link_anchor,
                   '<a class="malzeme-link kucuk" href="/malzeme-rehberi/">')]},
         None, YESIL, ""),
        ("R05", "HTML OZNITELIK SIRASI (href once, class sonra)",
         {BUILD: [(link_anchor,
                   '<a href="/malzeme-rehberi/" class="malzeme-link">')]},
         None, YESIL, ""),
        # R06/R07: eski MIRAS yanlis-pozitifleri KAPANDI — c2 ekseni JS-bayrak metninden
        # #opsiyonlar YAPISINA tasindi (konfigur-test.py). Artik ilgisiz refaktor: YESIL.
        ("R06", "gomulu JS bayragi config objesine tasindi (script-harici refaktoru)",
         {BUILD: [("  var KART_SECIM = {kart_secim};",
                   "  var PRUVO_CFG = {{ kartSecim: {kart_secim} }};\n"
                   "  var KART_SECIM = PRUVO_CFG.kartSecim;")]},
         None, YESIL, ""),
        ("R07", "JS MINIFY: bayraktaki bosluk kaldirildi (KART_SECIM={x})",
         {BUILD: [("var KART_SECIM = {kart_secim};", "var KART_SECIM={kart_secim};")]},
         None, YESIL, ""),
        ("R08", "HTML MINIFY: <main> ile <nav> arasi bosluk kaldirildi",
         {BUILD: [(main_ac, '<main><nav class="crumbs" aria-label="breadcrumb">')]},
         None, YESIL, ""),
        ("R09", "sablon GIRINTISI degisti (crumbs blogu)",
         {BUILD: [(crumbs_eski, crumbs_yeni)]}, None, YESIL, ""),
        ("R10", "FOOTER nav linki + METNI degisti (/malzeme-kilavuzu/)",
         {SAYFALAR: [('<a href="/malzeme-rehberi/">Malzeme Rehberi</a> &middot; ',
                      '<a href="/malzeme-kilavuzu/">Malzeme Kılavuzu</a> &middot; ')]},
         None, YESIL, ""),
        # R11: eski MIRAS KAPANDI — c2 olmamali civisi ciplak 'class="cart-btn"' yerine
        # buyuk-buton ACILIS etiketi '<button class="cart-btn"'; footer <a class="cart-btn">
        # bunu KARSILAMAZ -> ilgisiz refaktor: YESIL.
        ("R11", "FOOTER nav'a .cart-btn sinifli yeni buton eklendi",
         {SAYFALAR: [('    \'<a href="/hakkimizda/">Hakkımızda</a> &middot; \'',
                      '    \'<a class="cart-btn" href="/sepet/">Sepet</a> &middot; \'\n'
                      '    \'<a href="/hakkimizda/">Hakkımızda</a> &middot; \'')]},
         None, YESIL, ""),
        ("R12", "KATALOGDA yeni urun (sentetik urunler.json'un BASINA)",
         None, {"urunler.json": _sentetik_katalog(yeni_urun=True, marin_bos=False)},
         YESIL, ""),
        ("R13", "KATALOGDA Marin kategorisi tamamen bosaltildi (sentetik urunler.json)",
         None, {"urunler.json": _sentetik_katalog(yeni_urun=False, marin_bos=True)},
         YESIL, ""),
        ("R14", "CATEGORIES'e YENI kategori (katalog buyumesi)",
         {BUILD: [(kat_satir, kat_satir[:-1] + ', "Deneme"]')]}, None, YESIL, ""),
        ("R15", "kategori YENIDEN ADLANDIRILDI (Bahçe -> Bahce; CATEGORIES+FONKSIYONEL)",
         {BUILD: [(kat_satir, kat_satir.replace('"Bahçe"', '"Bahce"')),
                  (fonk_satir, fonk_satir.replace('"Bahçe"', '"Bahce"'))]},
         None, BORC, "Bahçe"),
        ("R16b", "BOLUM SIRASI: govde linki WA notunun ONUNE alindi (ikisi de duruyor)",
         {BUILD: [("""        return ('<div class="malzeme-blok">%s'
                '<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede kullanılır? '
                'Malzeme Rehberi &rarr;</a>'
                '</div>' % wa_html)""",
                   """        return ('<div class="malzeme-blok">'
                '<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede kullanılır? '
                'Malzeme Rehberi &rarr;</a>%s'
                '</div>' % wa_html)""")]}, None, YESIL, ""),
        ("R17", "HEAD'e yeni OG/product meta etiketi",
         {BUILD: [('<meta property="og:type" content="product">',
                   '<meta property="og:type" content="product">\n'
                   '<meta property="product:condition" content="new">')]},
         None, YESIL, ""),
        ("R18b", "govde link METNI yeniden yazildi (Malzeme Rehberi -> Malzeme Kılavuzu)",
         {BUILD: [("Malzeme Rehberi &rarr;</a>", "Malzeme Kılavuzu &rarr;</a>")]},
         None, YESIL, ""),
        ("R19", "govde BASLIGI yeniden yazildi (Malzeme -> Malzeme seçimi)",
         {BUILD: [('<div class="malzeme-baslik">Malzeme</div>',
                   '<div class="malzeme-baslik">Malzeme seçimi</div>')]},
         None, YESIL, ""),
        ("R20", "iyzico ODEME BANDI duzenlendi (sayfalar.py PAY_BAND_HTML)",
         {SAYFALAR: [('<span class="pay-label">Güvenli Ödeme</span>',
                      '<span class="pay-label">Güvenli Ödeme &middot; 3D Secure</span>')]},
         None, YESIL, ""),
        ("R21", "<main> etiketine SINIF eklendi (<main class=\"urun\">)",
         {BUILD: [(main_ac,
                   '<main class="urun">\n  <nav class="crumbs" aria-label="breadcrumb">')]},
         None, YESIL, ""),
        ("R22", "<main> -> <div id=\"main\"> (sablon YAPISAL yeniden yazimi)",
         {BUILD: [(main_ac,
                   '<div id="main">\n  <nav class="crumbs" aria-label="breadcrumb">'),
                  ("</main>\n\n{related}", "</div>\n\n{related}")]},
         None, BORC, "ANA GÖVDEDE"),
        ("R23", "urun sayfasina yeni harici <script src>",
         {BUILD: [('<script src="/secenekler.js"></script>',
                   '<script src="/secenekler.js"></script>\n'
                   '<script src="/analitik-deneme.js"></script>')]}, None, YESIL, ""),
        ("R24b", "filamentler.json'a yeni SATISTA malzeme (cip sayisi degisti)",
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
                         '      "uzunAd": "TPU (esnek)",')]}, None, YESIL, ""),
        ("R25b", "govde WA notu <p> -> <div> (etiket degisimi)",
         {BUILD: [(wa_p, '<div class="malzeme-not">Karbon fiber'),
                  ("bize yazın</a>.</p>", "bize yazın</a>.</div>")]}, None, YESIL, ""),
    ]


REF_OLCULDU = "OLCULDU"
REF_TOTOLOJI = "TOTOLOJI"
REF_YOK = "YOK"


def base_nobetci():
    """merge-base'deki (dal ayrim noktasi) tools/konfigur-test.py metni.

    Ana hatta merge-base == HEAD -> metin CALISANLA BAYT AYNI cikar; buna "BASE olctum"
    demek YALAN olurdu (c4'te duzeltilen totolojinin aynisi) -> TOTOLOJI raporlanir."""
    with open(os.path.join(HERE, NOBETCI), "rb") as f:
        calisan = f.read()
    for ref in ("origin/main", "main"):
        mb = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", ref],
                            capture_output=True, text=True)
        if mb.returncode != 0:
            continue
        commit = mb.stdout.strip()
        kaynak = subprocess.run(["git", "-C", ROOT, "show",
                                 commit + ":tools/" + NOBETCI], capture_output=True)
        if kaynak.returncode != 0:
            continue
        taban = "%s (merge-base HEAD..%s)" % (commit[:12], ref)
        if kaynak.stdout == calisan:
            return None, REF_TOTOLOJI, taban
        return kaynak.stdout.decode("utf-8"), REF_OLCULDU, taban
    return None, REF_YOK, "merge-base/git show alinamadi (sig klon / origin-main yok?)"


SINIF_IKON = {YESIL: "✅", BORC: "🟠", MIRAS: "🔴"}


# ---------------------------------------------------------------- H) konfigur kart-kilit
# Bagimsiz curutme C1 sessiz deligini KALICI fiksture baglar: konfigur sayfasinda kart-secim
# malzeme kilidinin YANLISLIKLA ACILMASI (kart_secim=true) regresyonu, EMISYON BICIMINDEN
# BAGIMSIZ yakalanmali. Eski (aec19cbb) negatif iddia yalniz 'KART_SECIM = true' LITERALini
# goruyordu -> bayrak config objesine tasininca (kartSecim: true) kilit-ACIK regresyonu
# SESSIZCE gecti (DAL exit 0, olmasi gereken exit 1). Onarim: KILIT_ACIK_RE hem literal
# hem config-obje bicimini kapsar. Bu bolum DENGEYI kanitlar:
#   kilit-ACIK (true)  -> iki emisyon biciminde de KIRMIZI (delik kapali)
#   kilit-KAPALI (false, config-obje bicim) -> YESIL (FP geri gelmedi)
# FLIP: build.py line ~1714 kart_secim = ... and not konfigur -> 'and not konfigur' cikar =
#   konfigur sayfalari kart_secim=true olur (kilit-ACIK regresyonu; baska sayfa etkilenmez).
_FLIP = ("fonksiyonel and not parametrik and not konfigur",
         "fonksiyonel and not parametrik")
# R06 emisyonu: bayragi config objesine tasir (kartSecim: <deger>) -> C1'in kacan bicimi.
_R06_EMIT = ("  var KART_SECIM = {kart_secim};",
             "  var PRUVO_CFG = {{ kartSecim: {kart_secim} }};\n"
             "  var KART_SECIM = PRUVO_CFG.kartSecim;")
_KILIT_ISARET = "kilidi AÇILMAZ"     # (d)/(e) KILIT_ACIK_RE iddiasinin kirmizi satiri


def bolum_h():
    print("\nH) KONFIGUR KART-KILIT true-flip (EMISYON-BICIMI BAGIMSIZ — C1 sessiz delik)")
    print("   Kabul: kilit-ACIK (kart_secim=true) HER emisyon biciminde KIRMIZI + kendi")
    print("   adiyla ('%s'); kilit-KAPALI config-obje bicim YESIL (FP geri gelmedi)." % _KILIT_ISARET)
    vakalar = [
        ("H1 kilit-ACIK / DIRECT emisyon (var KART_SECIM = true)",
         {BUILD: [_FLIP]}, "KIRMIZI"),
        ("H2 kilit-ACIK / CONFIG-OBJE emisyon (kartSecim: true) [C1 delik]",
         {BUILD: [_FLIP, _R06_EMIT]}, "KIRMIZI"),
        ("H3 kilit-KAPALI / CONFIG-OBJE emisyon (kartSecim: false) — mesru",
         {BUILD: [_R06_EMIT]}, "YESIL"),
    ]
    for etiket, mut, beklenti in vakalar:
        rc, cikti, kirmizi = kos(mut, etiket=etiket[:22])
        if beklenti == "KIRMIZI":
            isaretli = [s for s in kirmizi if _KILIT_ISARET in s]
            gecti = (rc == 1) and bool(isaretli)
            detay = ("cikis=%d kirmizi=%d isaretli=%s"
                     % (rc, len(kirmizi), isaretli[0][:80] if isaretli else "YOK"))
        else:
            gecti = (rc == 0) and not kirmizi
            detay = "cikis=%d kirmizi=%d %s" % (rc, len(kirmizi),
                                                kirmizi[0][:80] if kirmizi else "")
        check("%s -> %s" % (etiket, beklenti), gecti, detay)


def bolum_c():
    print("\nC) RUTIN DUZENLEME MATRISI — 25 gercekci duzenleme, BEYAN EDILMIS beklentiyle")
    print("   (bu nobetci deploy'u bloklar: bir yanlis-pozitif TUM SITE yayinini durdurur)")
    base_metin, base_durum, base_taban = base_nobetci()
    if base_durum == REF_OLCULDU:
        print("   BASE nobetcisi: %s (calisandan FARKLI -> 'dalin getirdigi' ayrisabilir)"
              % base_taban)
    else:
        print("   BASE nobetcisi ⚪ OLCULEMEDI (%s): %s" % (base_durum, base_taban))
        print("   -> ana hatta BEKLENEN durum; kalici koruma DAL kolonudur.")
    fiksturler = rutin_fiksturler()
    satirlar = []
    sayac = {YESIL: 0, BORC: 0, MIRAS: 0}
    dalin_getirdigi = []
    for kod, aciklama, mut, ek, beklenti, isaret in fiksturler:
        rc, cikti, kirmizi = kos(mut, ek, etiket="%s/DAL" % kod)
        dal_kirmizi = rc != 0 or bool(kirmizi)
        base_kirmizi = None
        if base_durum == REF_OLCULDU:
            brc, bcikti, bkirmizi = kos(mut, ek, nobetci_metni=base_metin,
                                        etiket="%s/BASE" % kod)
            base_kirmizi = brc != 0 or bool(bkirmizi)
        if beklenti == YESIL:
            gecti = not dal_kirmizi
            detay = "cikis=%d kirmizi=%d %s" % (rc, len(kirmizi),
                                                kirmizi[0][:100] if kirmizi else "")
            if not gecti and base_kirmizi is False:
                detay += "  ⚠️ BASE YESILDI -> DALIN GETIRDIGI YANLIS-POZITIF"
                dalin_getirdigi.append(kod)
        else:
            isaretli = [s for s in kirmizi if isaret in s]
            gecti = dal_kirmizi and bool(isaretli)
            detay = ("cikis=%d kirmizi=%d isaretli=%s"
                     % (rc, len(kirmizi), isaretli[0][:90] if isaretli else "YOK"))
            if not dal_kirmizi:
                detay += ("  ⚠️ BEYAN EDILMIS %s BORCU KAPANMIS GORUNUYOR -> fiksturu "
                          "%s sinifina cek + nobetcideki ne_olculmedi() beyanini "
                          "guncelle" % (beklenti, YESIL))
        sayac[beklenti] += 1
        check("%s %s [%s] %s" % (SINIF_IKON[beklenti], kod, beklenti, aciklama),
              gecti, detay)
        satirlar.append((kod, aciklama, beklenti,
                         "KIRMIZI" if dal_kirmizi else "YESIL",
                         "-" if base_kirmizi is None
                         else ("KIRMIZI" if base_kirmizi else "YESIL")))
    print("\n   --- MATRIS (BASE = merge-base nobetcisi, DAL = calisan nobetci) ---")
    print("   %-5s %-6s %-8s %-8s %s" % ("kod", "sinif", "BASE", "DAL", "duzenleme"))
    for kod, aciklama, beklenti, dal, base in satirlar:
        print("   %-5s %-6s %-8s %-8s %s" % (kod, SINIF_IKON[beklenti], base, dal,
                                             aciklama[:58]))
    print("   TOPLAM: %d fikstur = %d ✅ temiz-beklentili · %d 🟠 beyan edilmis borc · "
          "%d 🔴 miras yanlis-pozitif" % (len(satirlar), sayac[YESIL], sayac[BORC],
                                          sayac[MIRAS]))
    check("DALIN GETIRDIGI yanlis-pozitif = 0 (BASE yesil + DAL kirmizi olan fikstur)",
          not dalin_getirdigi, "ihlal: %s" % (dalin_getirdigi or "-"))


# ---------------------------------------------------------------- D) hermetiklik
TEKRAR = 10


def bolum_d():
    print("\nD) HERMETIKLIK — ayni girdiyle %d kosum AYNI sonuc (flaky CI = yayin kilidi)"
          % TEKRAR)
    parmak = []
    for i in range(TEKRAR):
        rc, cikti, kirmizi = kos(etiket="HERMETIK-%d" % (i + 1))
        parmak.append((rc, cikti.count("✅"), cikti.count("❌"), cikti.count("⚪")))
    tekil = sorted(set(parmak))
    check("%d/%d kosum ayni (cikis, ✅, ❌, ⚪)" % (parmak.count(parmak[0]), TEKRAR),
          len(tekil) == 1, "gorulen parmak izleri: %s" % (tekil,))
    # URUN VERISI BAGIMSIZLIGI — GRAMER DEGIL ICRA kaniti: ayna urunler.json'u
    # (ve .urun-kaynaklari.json'u) HIC TASIMAZ. Taban yesil oldugu icin nobetci o
    # dosyalari okumuyor demektir; okusaydi acilis hatasiyla duserdi. Yani katalog
    # buyumesi/degismesi bu nobetciyi YAPISAL OLARAK etkileyemez. (C bolumu R12/R13
    # bunu TERSTEN de olcer: veri AYNADA VARSA ve degisirse de kapi kimildamiyor.)
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
    # ⚠️ IC-SUREC IMPORT CANLI AGACA .pyc YAZAR (tools/__pycache__) -> dokunulmazlik
    # olcumu sahte kirmizi verir. Bytecode yazimi bu import boyunca KAPATILIR.
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
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


# ------------------------------------------------- F) ayna dokunulmazligi (symlink kacagi)
def bolum_f():
    print("\nF) AYNA DOKUNULMAZLIGI — aynadan kaynaga YAZMA YOLU var mi?")
    print("   Kabul: aynada symlink 0 + aynadaki HER yola yazma denemesinden sonra")
    print("          kaynak agacin TUM dosyalarinin sha256'si DEGISMEMIS (N/N).")
    tmp = tempfile.mkdtemp(prefix="konfigur-dokunulmazlik-")
    yazilan_dosya = yazilan_dizin = 0
    symlinkler = []
    try:
        ayna_kur(tmp)
        for kok, dizinler, dosyalar in os.walk(tmp):
            for d in dizinler:
                if os.path.islink(os.path.join(kok, d)):
                    symlinkler.append(os.path.relpath(os.path.join(kok, d), tmp))
            for d in dosyalar:
                y = os.path.join(kok, d)
                if os.path.islink(y):
                    symlinkler.append(os.path.relpath(y, tmp))
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not symlinkler, "symlink: %s" % (symlinkler[:6] or "-"))
        # AYNADAKI HER YOLA YAZMA DENEMESI: her dosyaya ek yazma + her dizine yeni dosya.
        # Bir yol symlink olsaydi bu yazma KAYNAGI ezerdi -> sha256 karsilastirmasi yakalar.
        for kok, dizinler, dosyalar in os.walk(tmp):
            try:
                with open(os.path.join(kok, "AYNA-YAZMA-DENEMESI.txt"), "w",
                          encoding="utf-8") as f:
                    f.write("harness yazma denemesi")
                yazilan_dizin += 1
            except OSError:
                pass
            for d in dosyalar:
                if d == "AYNA-YAZMA-DENEMESI.txt":
                    continue
                try:
                    with open(os.path.join(kok, d), "ab") as f:
                        f.write(b"\n# AYNADA-URETILDI (harness dokunulmazlik denemesi)\n")
                    yazilan_dosya += 1
                except OSError:
                    pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    simdi = kaynak_parmagi()
    degisen = sorted(y for y in set(KAYNAK_TABAN) | set(simdi)
                     if KAYNAK_TABAN.get(y) != simdi.get(y))
    check("aynada %d dosya + %d dizin yazildi -> KAYNAK AGAC %d/%d dosya sha256 AYNI"
          % (yazilan_dosya, yazilan_dizin, len(simdi) - len(degisen), len(simdi)),
          not degisen, "degisen: %s" % (degisen[:6] or "-"))
    check("her kosumdan sonraki dokunulmazlik olcumu: %d/%d kosum temiz"
          % (DOKUNULMAZ_KOSUM[0], sum(DOKUNULMAZ_KOSUM)),
          DOKUNULMAZ_KOSUM[1] == 0,
          "kirli kosum: %d" % DOKUNULMAZ_KOSUM[1])


# ------------------------------------------------- G) ana hat etkisi (BULGU, FAIL degil)
DEPLOY_YML = os.path.join(ROOT, ".github", "workflows", "deploy.yml")


def _is_akisi_modulu():
    """Ortak gerçek-icra süzgecini tek kaynağından yükle."""
    yol = os.path.join(ROOT, "tools", "is-akisi-kapisi.py")
    spec = importlib.util.spec_from_file_location("pruvo_is_akisi_kapisi", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _deploy_bloklayici_mi(deploy_metin=None):
    """deploy.yml'de nobetciyi kosan ADIM bloklayici mi? (SALT OKUMA — dosyaya dokunulmaz)"""
    if deploy_metin is None:
        try:
            with open(DEPLOY_YML, encoding="utf-8") as f:
                deploy_metin = f.read()
        except OSError as e:
            return None, "deploy.yml okunamadi: %s" % e
    komutlar = _is_akisi_modulu().gercek_icra_komutlari(deploy_metin)
    for komut in komutlar:
        if re.match(r"^python3\s+tools/konfigur-test\.py(?![\\w./-])", komut):
            return True, "ortak YAML/icra suzgecinde etkili cagri=%r" % komut
    return None, "deploy.yml'de konfigur-test.py kosan adim BULUNAMADI"


def bolum_g():
    print("\nG) ANA HAT ETKISI (BULGU — bu bolum FAIL uretmez, OLCUM basar)")
    bloklayici, ayrinti = _deploy_bloklayici_mi()
    print("   deploy.yml: %s (%s)"
          % ("BLOKLAYICI" if bloklayici else ("BLOKLAMIYOR" if bloklayici is False
                                              else "BELIRSIZ"), ayrinti))
    base_metin, base_durum, base_taban = base_nobetci()
    hangi = "BASE (%s)" % base_taban if base_durum == REF_OLCULDU else "CALISAN (ana hat)"
    metin = base_metin if base_durum == REF_OLCULDU else None
    for kod, aciklama, mut, ek, beklenti, isaret in rutin_fiksturler():
        if kod not in ("R06", "R07", "R11"):
            continue
        rc, cikti, kirmizi = kos(mut, ek, nobetci_metni=metin, etiket="ANAHAT-%s" % kod)
        print("   %s nobetcisi + %s (%s): cikis=%d kirmizi_satir=%d"
              % (hangi, kod, aciklama[:44], rc, len(kirmizi)))
        if kirmizi:
            print("      ornek: %s" % kirmizi[0][:120])
        if rc == 1 and bloklayici:
            print("      🔴 BULGU: bu RUTIN refaktor BUGUN ana hatta TUM SITE yayinini "
                  "DURDURUR (nobetci kirmizi + adim bloklayici).")


# ---------------------------------------------------------------- ana akis
def main():
    print("KONFIGUR NOBETCISI MUTASYON + YANLIS-POZITIF HARNESS'I")
    print("(mutasyon DAIMA gecici TAM-KOPYA aynada — kaynaga giden symlink YOK)")
    KAYNAK_TABAN.update(kaynak_parmagi())
    print("kaynak agac dokunulmazlik tabani: %d dosya sha256'landi" % len(KAYNAK_TABAN))
    rc, cikti, kirmizi = kos(etiket="TABAN")
    print("\nTABAN (mutasyonsuz ayna): cikis=%d ✅=%d ❌=%d ⚪=%d"
          % (rc, cikti.count("✅"), cikti.count("❌"), cikti.count("⚪")))
    if not check("TABAN YESIL (mutasyonsuz ayna bozuk degil)", rc == 0 and not kirmizi,
                 kirmizi[0][:140] if kirmizi else ""):
        print("\nTaban kirmizi -> mutasyon sonuclari anlamsiz olur, DURDU.")
        return 1
    bolum_a()
    bolum_b()
    bolum_h()
    bolum_c()
    bolum_d()
    bolum_e()
    bolum_f()
    bolum_g()
    print("\n" + "-" * 70)
    if FAILS:
        print("SONUC: KIRMIZI ❌  (%d kusur)" % len(FAILS))
        for f in FAILS:
            print("   ❌ " + f)
        return 1
    print("SONUC: YESIL ✅  (mutasyonlar kirmizi yaniyor, ilgisiz degisiklikler yesil "
          "kaliyor, ayna kaynaga yazamiyor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
