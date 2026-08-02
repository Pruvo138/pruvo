#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — `altkategori` MUSTERI YUZEYI (urun sayfasi + yapilandirilmis veri).

  python3 tools/altkategori-yuzey-test.py              # kabul (CI'da bloklayici)
  python3 tools/altkategori-yuzey-test.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/altkategori-yuzey-test.py --kok /yol   # modulleri BASKA agactan oku

NEDEN VAR (olculdu, 2026-08-01): `altkategori` alani katalogda 935/16.874 kayitta DOLU
ama musteri onu HICBIR yerde gormuyordu — index.html YOK, build.py YOK, shop/src YOK,
canli urun sayfasi YOK, worker /katalog cevabi YOK. Veri VARDI, deger URETMIYORDU.
tools/altkategori-kapisi.py alanin VERI/D1 yolunu koruyor; bu kapi o verinin MUSTERIYE
GORUNEN yuzunu korur. Ikisi ayri eksendir: veri yolu yesilken yuzey sessizce yok olabilir.

OLCULEN SESSIZ-HATA SINIFLARI (hepsi CI'da makineyle olculur):
  A YUZEY    Etiket basilmayi birakirsa (sablondan {altkat} dusmesi, kosulun tersine
             donmesi) hicbir sey COKMEZ: 935 sayfa sessizce eski haline doner ve
             musteri gruba dair tek ipucunu kaybeder.
  B SEMA     Product.category "Ust > Alt" yolunu tasir. Bos degerde de yol basilirsa
             ("Marin > ") yapilandirilmis veri BOZUK gider; anahtar sirasi kayarsa
             gorselli/gorselsiz sayfalarin bayt-esitligi (test-jsonld-*) kirilir.
  C REGRESYON Yuzey PAYLASILAN yere (PAGE_CSS) yazilirsa altkategorisi OLMAYAN 15.939
             sayfanin da bayti degisir. Cikti dogru gorunur, regresyon butcesi patlar.
             Bu kapi "dolu ile bos sayfa arasindaki fark TAM OLARAK iki nokta" der.
  D FAIL-SAFE Bos / alan yok / None / bozuk tip / izinsiz deger / yanlis kategori /
             bosluklu / imza tasiyan deger -> URETIM COKMEZ ve deger SIZMAZ. Sizarsa
             public repoda + canli sayfada + JSON-LD'de tedarikci imzasi gorunur.
  E TEK      Sayfada gorunen etiket ile D1'e giden deger AYNI fonksiyondan
    KAYNAK   (arama.altkategori_kanonik) turemeli. build.py ikinci bir izinli-kume
             kopyasi tasirsa iki taraf sessizce ayrisir -> [[ikiz-tanim-sessiz-ayrisma]].

AGA/D1'e/wrangler'a DOKUNMAZ, DISKE YAZMAZ: gercek build.render_product BELLEKTE
cagrilir, urunler.json yalnizca OKUNUR.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

GERCEK_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + str(detay)[:400] if detay else ""))


def yukle(kok, ad, dosya):
    """tools/<dosya>'yi MODUL olarak yukle (kok parametrik -> mutasyon kopyasi da olculur).

    arama.py BILEREK ONCE yuklenir ve sys.modules'e "arama" adiyla konur: build.py kendi
    icinde `import arama` yapar ve AYNI modul objesini alir. E ekseni (tek kaynak) bu
    ozdesliğe dayanir — izinli kumeyi burada genisletince sayfa da gostermeli.
    """
    spec = importlib.util.spec_from_file_location(ad, os.path.join(kok, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _urun(uid="yuzey-test-1", kategori="Marin", altkategori=..., baslik="Deneme urun"):
    """Sentetik urun. altkategori=... (Ellipsis) => ALAN HIC YOK."""
    u = {"id": uid, "baslik": baslik, "kategori": kategori, "marka": ["Marka"],
         "fiyat": "100 TL", "aciklama": "deneme aciklama",
         "gorseller": ["https://media.pruvo3d.com/urunler/x-1.jpg"]}
    if altkategori is not ...:
        u["altkategori"] = altkategori
    return u


_CIP_RE = re.compile(r'<span class="cat"[^>]*>([^<]*)</span>')
_LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _cipler(html):
    return _CIP_RE.findall(html)


def _ld_bloklari(html):
    return [json.loads(s) for s in _LD_RE.findall(html)]


def _product_ld(html):
    for o in _ld_bloklari(html):
        if o.get("@type") == "Product":
            return o
    return {}


def _breadcrumb_ld(html):
    for o in _ld_bloklari(html):
        if o.get("@type") == "BreadcrumbList":
            return o
    return {}


def kabul(kok):
    arama = yukle(kok, "arama", "arama.py")
    build = yukle(kok, "build", "build.py")
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        katalog = json.load(f)

    def ciz(p, havuz=None):
        return build.render_product(p, havuz if havuz is not None else [p], None)

    # ══ A EKSENI — GORUNUR YUZEY ══════════════════════════════════════════════════
    print("\n[A] GORUNUR YUZEY — urun sayfasindaki etiket")
    p_dolu = _urun(altkategori="Elektrik")
    p_bos = _urun(altkategori="")
    p_yok = _urun()
    h_dolu, h_bos, h_yok = ciz(p_dolu), ciz(p_bos), ciz(p_yok)

    dogrula("A1 DOLU kayitta altkategori sayfada GORUNUYOR (kategori cipinin yaninda)",
            "Elektrik" in _cipler(h_dolu), _cipler(h_dolu))
    dogrula("A2 cip METNI arama.altkategori_kanonik ciktisiyla BIREBIR (tek kaynak, "
            "ikinci yazim yok)",
            _cipler(h_dolu) == ["Marin", arama.altkategori_kanonik(p_dolu)],
            _cipler(h_dolu))
    dogrula("A3 BOS degerde HICBIR SEY basilmiyor — bos etiket/bos cip YOK "
            "(gorselsiz urun kurali: kirik yuzey yerine durust eksiklik)",
            _cipler(h_bos) == ["Marin"] and "Elektrik" not in h_bos, _cipler(h_bos))
    dogrula("A4 ALAN HIC YOKKEN cikti, alan BOS iken ciktiyla BAYT-ESIT "
            "(iki hal ayni sayfayi uretir)", h_yok == h_bos,
            "%d vs %d bayt" % (len(h_yok), len(h_bos)))

    # Gercek katalog: her tekil deger icin GERCEK bir urun sayfasi.
    gercek_dolu = [u for u in katalog
                   if isinstance(u.get("altkategori"), str) and u["altkategori"].strip()]
    gercek_bos = [u for u in katalog if u not in gercek_dolu]
    tekil = sorted({u["altkategori"] for u in gercek_dolu})
    dogrula("A5 KATALOGTA olculecek dolu kayit VAR (yoksa bu kapi TAUTOLOJI olurdu)",
            len(gercek_dolu) > 0, len(gercek_dolu))
    ornekler = {}
    for d in tekil:
        ornekler[d] = next(u for u in gercek_dolu if u["altkategori"] == d)
    kayip = [d for d, u in ornekler.items() if d not in _cipler(ciz(u, katalog[:200]))]
    dogrula("A6 GERCEK katalogtaki %d tekil degerin HEPSI kendi gercek urun sayfasinda "
            "GORUNUYOR" % len(tekil), not kayip, kayip)
    print("  OLCUM: katalog %d kayit · altkategori DOLU %d · BOS/eksik %d · tekil deger %d"
          % (len(katalog), len(gercek_dolu), len(gercek_bos), len(tekil)))

    # ══ B EKSENI — YAPILANDIRILMIS VERI ═══════════════════════════════════════════
    print("\n[B] YAPILANDIRILMIS VERI — JSON-LD gecerli kalir")
    ld_dolu = _product_ld(h_dolu)
    ld_bos = _product_ld(h_bos)
    dogrula("B1 dolu sayfadaki HER JSON-LD blogu GECERLI JSON olarak ayrisiyor "
            "(etiket blogu bozmuyor)", len(_ld_bloklari(h_dolu)) >= 2,
            len(_ld_bloklari(h_dolu)))
    dogrula("B2 Product.category DOLU kayitta 'Ust > Alt' yolu",
            ld_dolu.get("category") == "Marin > Elektrik", ld_dolu.get("category"))
    dogrula("B3 Product.category BOS kayitta SADECE kategori — 'Marin > ' gibi ucu acik "
            "yol YOK", ld_bos.get("category") == "Marin", ld_bos.get("category"))
    dogrula("B4 YENI ANAHTAR EKLENMEDI: dolu ve bos sayfanin Product anahtar LISTESI "
            "ve SIRASI ayni (feed/JSON-LD bayt-esitlik testleri kaymaz)",
            list(ld_dolu) == list(ld_bos), (list(ld_dolu), list(ld_bos)))
    dogrula("B5 BOS deger hicbir JSON-LD alanina SIZMIYOR (bos dize degeri YOK)",
            all(v != "" for v in ld_bos.values() if isinstance(v, str)),
            {k: v for k, v in ld_bos.items() if v == ""})
    bc_dolu, bc_bos = _breadcrumb_ld(h_dolu), _breadcrumb_ld(h_bos)
    dogrula("B6 BreadcrumbList DEGISMEDI (3 dugum) — altkategorinin URL'i HENUZ YOK, "
            "URL'siz ARA dugum basmak yerine dugum HIC acilmiyor",
            len(bc_dolu["itemListElement"]) == 3 and bc_dolu == bc_bos,
            len(bc_dolu["itemListElement"]))
    dogrula("B7 BreadcrumbList'teki HER ara dugumun `item` URL'i VAR (Google ara dugumde "
            "URL bekler)",
            all(x.get("item") for x in bc_dolu["itemListElement"]), bc_dolu["itemListElement"])

    # ══ C EKSENI — REGRESYON / CERRAHI FARK ═══════════════════════════════════════
    print("\n[C] REGRESYON — altkategorisiz sayfa DEGISMEZ, fark CERRAHI")
    # 🔴 EN KRITIK EKSEN. Dolu sayfadan SADECE iki bilinen parcayi geri alinca cikti
    # bos sayfayla BAYT-ESIT olmali. Esit degilse degisiklik UCUNCU bir yere de dokunmustur
    # (PAGE_CSS, kart, feed, script...) ve 15.939 altkategorisiz sayfanin bayti kaymistir.
    cip_html = ('<span class="cat" style="margin-left:8px;background:var(--navy-2)">'
                'Elektrik</span>')
    geri = h_dolu.replace(cip_html, "", 1).replace('"category":"Marin > Elektrik"',
                                                   '"category":"Marin"', 1)
    dogrula("C1 DOLU sayfa − (cip + category yolu) == BOS sayfa, BAYT-ESIT — fark TAM "
            "OLARAK iki noktada, baska hicbir yerde", geri == h_bos,
            "fark %d bayt" % abs(len(geri) - len(h_bos)))
    dogrula("C2 PAYLASILAN CSS'e kural EKLENMEDI (PAGE_CSS altkategoriye dair tek jeton "
            "tasimiyor) — eklenseydi 15.939 sayfanin bayti da degisirdi",
            "altkat" not in build.PAGE_CSS.lower(), "PAGE_CSS'te 'altkat' gecti")
    # KOMSU IZOLASYONU: A urununun sayfasi, KATALOGTAKI BASKA bir urunun altkategorisi
    # dolu olsa da olmasa da AYNI olmali (ilgili-urun kartlari alani sizdirmiyor).
    a = _urun("yuzey-komsu-a")
    b1 = _urun("yuzey-komsu-b", altkategori=...)
    b2 = _urun("yuzey-komsu-b", altkategori="Elektrik")
    dogrula("C3 KOMSU IZOLASYONU: altkategorisiz urunun sayfasi, KOMSUSUNUN altkategorisi "
            "dolu olsa da BAYT-ESIT (ilgili-urun kartlari alani sizdirmiyor)",
            build.render_product(a, [a, b1], None) == build.render_product(a, [a, b2], None))
    # Gercek katalogtan bir altkategorisiz urun: dort bozuk hal de BIREBIR ayni sayfa.
    # 🔴 COKME DE SAPMADIR: render_product'in ATMASI da bu iddiayi KIRMIZI yakmali,
    # sureci OLDURMEMELI. Oldurseydi mutasyon turunda "rc!=0 ama hicbir iddia KALDI
    # demedi" cikardi — yani mutant OLDURULDU degil, KAPI COKTU (yalanci kanit).
    ger_bos = dict(gercek_bos[0])
    esitler = []
    for etiket, deger in (("bos", ""), ("None", None), ("liste", ["Elektrik"]),
                          ("sayi", 7), ("sozluk", {"ad": "Elektrik"})):
        v = dict(ger_bos)
        v["altkategori"] = deger
        try:
            esitler.append((etiket, ciz(v, katalog[:200])))
        except Exception as e:  # noqa: BLE001 — cokme SINIFI olculuyor
            esitler.append(("%s/COKTU:%s" % (etiket, type(e).__name__), None))
    temel = ciz(ger_bos, katalog[:200])
    sapan = [e for e, h in esitler if h != temel]
    dogrula("C4 GERCEK altkategorisiz urunde bes bozuk hal (bos/None/liste/sayi/sozluk) "
            "sayfayi DEGISTIRMIYOR — hepsi bugunku bayta esit", not sapan, sapan)

    # ══ D EKSENI — FAIL-SAFE (cokme yok + sizma yok) ══════════════════════════════
    print("\n[D] FAIL-SAFE — bozuk/izinsiz deger URETIMI COKERTMEZ ve SIZMAZ")
    # 🔴 OLCUM SEKLI: "deger metni sayfada geciyor mu" DEGIL — o olcum YANLIS-POZITIF
    # uretir (sayfa zaten '7' rakamini ve '<script' jetonunu tasir). Dogru ve tam olcum:
    # cikti, ALANI HIC OLMAYAN urunun ciktisiyla BAYT-ESIT olmali. Bayt-esitlik hem
    # "cokmedi" hem "hicbir yere sizmadi" (govde + JSON-LD + feed kimligi + script blogu)
    # demektir; tek bir karakter kaysa iddia kirmizi yanar.
    vakalar = [
        ("D1 BOS dize", ""),
        ("D2 ALAN HIC YOK", ...),
        ("D3 None", None),
        ("D4 BOZUK TIP (liste)", ["Elektrik"]),
        ("D5 BOZUK TIP (sayi)", 7),
        ("D6 BOZUK TIP (sozluk)", {"ad": "Elektrik"}),
        ("D7 IZINLI KUME DISI deger", "Uydurma Grup"),
        ("D8 BOSLUKLU (kanonik degil)", " Elektrik"),
        ("D9 IMZA TASIYAN (rakam) deger", "Grup 2K"),
        ("D10 IMZA TASIYAN (TAMAMI BUYUK) deger", "ABC Grubu"),
        ("D11 HTML/JS ENJEKSIYONU denemesi", '<script>x</script>'),
        ("D12 TEDARIKCI IMZASI (alan adi) denemesi", "tedarikci.com Grubu"),
    ]
    for ad, deger in vakalar:
        try:
            h = ciz(_urun(altkategori=deger))
        except Exception as e:  # noqa: BLE001 — cokme SINIFI olculuyor
            dogrula(ad + " -> COKMEDI", False, "%s: %s" % (type(e).__name__, e))
            continue
        dogrula(ad + " -> COKMEDI ve cikti ALANSIZ sayfayla BAYT-ESIT (hicbir yere "
                "sizmadi)", h == h_yok, "cip=%s · fark=%d bayt"
                % (_cipler(h), abs(len(h) - len(h_yok))))
    # YANLIS KATEGORI: gecerli bir Marin degeri BASKA kategoride basilmamali.
    h_yanlis = ciz(_urun(kategori="Ev", altkategori="Elektrik"))
    dogrula("D13 YANLIS KATEGORIYE ait gecerli deger basilmiyor (Ev + 'Elektrik')",
            _cipler(h_yanlis) == ["Ev"], _cipler(h_yanlis))

    # ══ E EKSENI — TEK KAYNAK (yuzey ile veri kapisi AYNI kumeden besleniyor) ═════
    print("\n[E] TEK KAYNAK — yuzey, izinli kumeyi arama.py'den okur")
    kaynak = open(os.path.join(kok, "tools", "build.py"), encoding="utf-8").read()
    dogrula("E1 build.py IKINCI bir izinli-kume kopyasi TASIMIYOR (ALTKATEGORI_IZINLI "
            "yalniz arama.py'de tanimli)",
            "ALTKATEGORI_IZINLI" not in kaynak, "build.py'de ALTKATEGORI_IZINLI gecti")
    dogrula("E2 build.py degeri arama.altkategori_kanonik'ten aliyor (ham p['altkategori'] "
            "okumuyor)", "arama.altkategori_kanonik(p)" in kaynak)
    # CANLI BAGLILIK: izinli kume GENISLEYINCE yuzey de otomatik gosterir. Kopya bir kume
    # olsaydi bu iddia KIRMIZI yanardi.
    _yedek = arama.ALTKATEGORI_IZINLI["Marin"]
    try:
        arama.ALTKATEGORI_IZINLI["Marin"] = _yedek + ("Deneme Grubu",)
        h_yeni = ciz(_urun(altkategori="Deneme Grubu"))
    finally:
        arama.ALTKATEGORI_IZINLI["Marin"] = _yedek
    dogrula("E3 CANLI BAGLILIK: arama.py izinli kumesi genisleyince sayfa YENI degeri "
            "ANINDA gosteriyor (kopya kume olsaydi gostermezdi)",
            "Deneme Grubu" in _cipler(h_yeni), _cipler(h_yeni))
    h_geri = ciz(_urun(altkategori="Deneme Grubu"))
    dogrula("E4 kume geri alininca deger YINE basilmiyor (test kendi yan etkisini "
            "temizledi, sonraki iddialar kirlenmedi)", _cipler(h_geri) == ["Marin"],
            _cipler(h_geri))

    print("\nSONUC: %s — gecen %d · kalan %d"
          % ("YESIL" if not kalan[0] else "KIRMIZI", gecen[0], kalan[0]))
    return 1 if kalan[0] else 0


# ══════════════════════════════════════════════════════════════════════════════════
# CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA.
# Beklenen "KIRMIZI" = mutant OLDURULMELI; "YESIL" = ilgisiz degisiklik kapiyi
# gereksiz yere kirmizi yakmamali (asiri-baglanma nobetcisi).
MUTANTLAR = [
    ("build.py", "altkategori = arama.altkategori_kanonik(p)",
     'altkategori = p.get("altkategori") or ""', "KIRMIZI",
     "D EKSENI: fail-closed kanonik atlanir -> izinsiz/imzali deger SIZAR"),
    ("build.py", "% esc(altkategori)) if altkategori else ''",
     "% esc(altkategori)) if True else ''", "KIRMIZI",
     "A3/C1: bos degerde de cip basilir -> bos etiket + 15.939 sayfa bayti kayar"),
    ("build.py", '<span class="cat">{kategori}</span>{altkat}{badge}',
     '<span class="cat">{kategori}</span>{badge}', "KIRMIZI",
     "A1: sablondan {altkat} duser -> yuzey SESSIZCE yok olur"),
    ("build.py", '"category": (kategori + " > " + altkategori) if altkategori else kategori,',
     '"category": kategori + " > " + altkategori,', "KIRMIZI",
     "B3: bos degerde 'Marin > ' ucu acik yol basilir -> bozuk yapilandirilmis veri"),
    ("build.py", '"category": (kategori + " > " + altkategori) if altkategori else kategori,',
     '"category": kategori,', "KIRMIZI",
     "B2: yapilandirilmis veri altkategoriyi TASIMAZ (yalniz gorunur yuzey kalir)"),
    ("build.py", 'style="margin-left:8px;background:var(--navy-2)"',
     'class-yerine-yeni-sinif="altkat-cip"', "KIRMIZI",
     "C1: cip biciminin yeri degisir -> cerrahi fark iddiasi capasini kaybeder"),
    ("arama.py", 'ALTKATEGORI_AZAMI_KELIME = 4', 'ALTKATEGORI_AZAMI_KELIME = 5', "YESIL",
     "ILGISIZ: imza nobetinin kelime tavani — yuzey iddialarina DOKUNMAZ"),
    # 🔴 ASIRI-BAGLANMA NOBETCISI: bu mutant HER sayfanin baytini degistirir (paylasilan
    # CSS). Kapi YESIL kalmali — kalmazsa iddialar mutlak sayfa baytina PINLENMIS demektir
    # ve her ilgisiz tasarim degisikliginde yayin durur ([[kapi-kapsam-eksen-secimi]]).
    ("build.py", ".thumb:hover{border-color:var(--gray-line)}",
     ".thumb:hover{border-color:var(--navy)}", "YESIL",
     "ILGISIZ: paylasilan CSS'te renk — TUM sayfalarin bayti degisir, iddialar goreceli"),
]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kopya_kur():
    """tools/ KOPYALANIR, kokteki diger girdiler SYMLINK (urunler.json 14 MB)."""
    tmp = tempfile.mkdtemp(prefix="pruvo-altkat-yuzey-mut-")
    shutil.copytree(os.path.join(GERCEK_KOK, "tools"), os.path.join(tmp, "tools"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", ".git", ".claude"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                          capture_output=True, text=True)


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    izlenen = ["build.py", "arama.py"]
    once = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in izlenen}
    basarisiz = []

    # M00 MUTASYONSUZ KONTROL (ZORUNLU ON-KOSUL): kopya agac mutasyonsuz YESIL vermezse
    # butun "KIRMIZI" sonuclari YALANCIDIR (mutant degil, cokme olculur).
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s (harness saglam mi)"
          % ("OK  " if p0.returncode == 0 else "HATA",
             "YESIL" if p0.returncode == 0 else "KIRMIZI"))
    if p0.returncode != 0:
        print("     " + ((p0.stderr or p0.stdout).strip().splitlines() or [""])[-1][:300])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk, mutant sonuclari YALANCI.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)

    uygulanan = 0
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = _kopya_kur()
        hedef = os.path.join(tmp, "tools", dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        sayi = metin.count(eski)
        # 🔴 CAPA KAYMASI = KIRMIZI, "gecti" DEGIL: eslesmeyen capa o ekseni OLCMEMISTIR.
        if sayi != 1:
            basarisiz.append("M%02d CAPA BAYAT (%d eslesme) %s: %s" % (i, sayi, dosya, eski[:70]))
            print("  HATA M%02d [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, sayi, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        mutant = metin.replace(eski, yeni, 1)
        if mutant == metin and beklenen == "KIRMIZI":
            basarisiz.append("M%02d MUTANT UYGULANMADI (metin DEGISMEDI) %s" % (i, dosya))
            print("  HATA M%02d [%s] %s -> MUTANT UYGULANMADI | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(mutant)
        uygulanan += 1
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        if goruldu != beklenen:
            basarisiz.append("M%02d %s: beklenen %s, goruldu %s" % (i, dosya, beklenen, goruldu))
        # 🔴 KIRMIZI YETMEZ, ADLI IDDIA SART: mutant COKEREK de rc!=0 verebilir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("M%02d %s: KIRMIZI ama HICBIR iddia KALDI demedi — kapi "
                             "COKTU (yalanci kanit)" % (i, dosya))
        print("  %s M%02d [%s] %s -> %s (%d iddia kirmizi) | %s"
              % ("OK  " if goruldu == beklenen else "HATA", i, beklenen, dosya, goruldu,
                 len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:150])
        shutil.rmtree(tmp, ignore_errors=True)

    sonra = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in izlenen}
    bozuk = [d for d in once if once[d] != sonra[d]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    print("  MUTANT FIILEN UYGULANDI: %d/%d" % (uygulanan, len(MUTANTLAR)))
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK, help="modulleri bu agactan oku")
    ap.add_argument("--mutasyon", action="store_true", help="cift yonlu mutasyon (elle)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== ALT KATEGORI MUSTERI YUZEYI KAPISI (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())
