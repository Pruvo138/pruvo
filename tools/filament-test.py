#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FILAMENT REHBERI KABUL TESTLERI — tools/paket-filament-rehberi.md'deki 7 test.

Kullanim:
    python3 tools/filament-test.py              # 7 testin hepsi (parite dahil, ag gerekir)
    PARITE=0 python3 tools/filament-test.py     # test 5 (parite, ag) atlanir

Once tools/build.py'yi CALISTIRIR (uretilen sayfalar taze olsun), sonra sirayla:
  1. urunler.json DEGISMEMIS (git diff bos — paket urun verisine dokunmaz)
  2. 20 rastgele urun sayfasi (+ EN AZ BIR parametrik ZORLA dahil): sitede satilan filament
     cipleri (ABS/Karbon HARIC) + tavsiye rozeti + balon metni filamentler.json ile birebir +
     kategori haritasina gore dogru tavsiye (parametrik urunde OZEL KILIF YOK — F kalemi)
  3. hicbir uretilen sayfada "3d bask" / "her renk" yok
  4. /malzeme-rehberi/ uretildi, footer linki var, sitemap'te
  5. node tools/parite-test.js 300 + node tools/parite-ege.js 200 YESIL (aciklama degismedi)
  6. override: tavsiyeFilament alanli sahte urunle render -> harita degil override basiliyor
  7. mobil tooltip: DOM/CSS duzeyinde dogrulama (balon + .acik toggle JS + aria-expanded)
  8. ABS/Karbon Katkili urun sayfasinda CIP OLARAK basilmiyor (site seceneği degil, sadece
     /malzeme-rehberi/ + WhatsApp notu)

KART-SECIM (Okan, 16 Tem — malzeme dropdown -> kart secici):
  9  (a) fonksiyonel sayfada malzeme dropdown YOK; kartlar data-malzeme tasir; tiklama SECER
 10  (b) sayfa acilisinda secili kart YOK + fiyat "…'den baslayan" halinde
 11  (c) secimsiz "Sepete Ekle" -> sepete eklenmez + titreme/kirmizi sinifi eklenir (CSS+JS)
 12  (d) secimle fiyat KATSAYILI guncellenir (JS wiring + secenekler.js kuruş matematigi)
 13  (e) alt paragraf ("Sepete ekleyip…") HICBIR urun sayfasinda yok
 14  (f) "WhatsApp'tan Sor" secim SARTI ARAMAZ (link her zaman calisir)

KART SADELESTIRME (Okan, 16 Tem — liste kartlarindan iki oge kalkti):
 20  ana sayfa kartlarinda "Sepete Ekle" butonu ve "Tavsiye:" cipi YOK (hizli-ekleme yolu
     tamamen kalkti -> hicbir UI yolu malzemesiz/varsayilan-PLA kalem ekleyemez); urun
     sayfasinda cartBtn + malzeme kartlari DURUYOR (regresyon)

EYLEM IKONLARI (Okan madde 7, 16 Tem — buyuk butonlar -> Adet satirinda ikon cifti):
 21  (l) kart-secim sayfasinda sayfa alti buyuk buton YOK; Adet satirinda aria-label+title'li
     2 ikon buton VAR (44px dokunma alani CSS'te); SEMALI PARAMETRIK (sari) sayfa da ayni
     kart-secim duzeninde (F kalemi, 16 Tem gece — commit 68cf6939 ile Okan karari)
 22  (m) ikon sepet butonu ayni cartBtn — secimsiz ekleme kapisi + titreme AYNEN calisiyor
 23  (n) WhatsApp ikonu dogru wa.me hedefine gidiyor (statik href + JS canli mesaj guncelleme)
 24  NOBETCI: buyuk buton yolu (build.py BUYUK_BUTONLAR_HTML) hala CANLI — panelsiz
     (Dekorasyon / Oyun-Hobi) sayfada buyuk butonlar YERINDE, ikon cifti YOK. Test 21'den
     parametrik iddiasi kalkinca bu kod dalini olcen tek test burasidir.
 25  KAPI: urunler.json'da FIILEN kullanilan her kategori ya tavsiye uretir ya da testin
     icindeki BILINCLI-BOS listesinde yer alir (yeni kategori sessizce tavsiyesiz kalamaz).
"""
import html
import json
import os
import random
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import filament_ortak

# BUILD SIZINTISI: adim 0'da kosan build.py, asagidaki 4 IZLENEN yasal sayfaya Meta
# piksel enjekte eder ve ana checkout'u KIRLETIR (git status M gizlilik/... vb.). Testler
# uretilmis sayfalara karsi kosulduktan SONRA bu 4 dosyayi HEAD'e geri yukleyip calisma
# agacini temiz birakiyoruz (aksi halde baska bir oturumun genis commit'i uretilmis izleme
# kodunu KAYNAGA sokabilir). Bu liste build.py'nin dokundugu TEK tracked dosya kumesidir
# (urun/, sitemap.xml, robots.txt vb. gitignore'da).
YASAL_SAYFALAR = [
    "gizlilik/index.html", "hakkimizda/index.html",
    "iletisim/index.html", "sss/index.html",
]


def _yasal_sayfalari_geri_yukle():
    """build.py'nin Meta-piksel enjeksiyonuyla kirlettigi 4 yasal sayfayi HEAD'e geri yukle.
    Bu adim KALDIRILIRSA 'git status' KIRLI doner (kirmizi-mutasyon nobeti — kabul testi #5)."""
    subprocess.run(["git", "checkout", "--", *YASAL_SAYFALAR],
                   cwd=ROOT, capture_output=True, text=True)

SONUC = []


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti, detay))
    print("  %s TEST %d — %s%s" % ("✅" if gecti else "❌", no, ad,
                                   (" | " + detay) if detay else ""), flush=True)


def sayfa(pid):
    with open(os.path.join(ROOT, "urun", pid, "index.html"), encoding="utf-8") as f:
        return f.read()


def main():
    print("0) tools/build.py calisiyor (uretim taze olsun)...", flush=True)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "build.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        sys.exit("build.py HATA verdi — testler kosulmadi.")
    print("   " + r.stdout.strip())

    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    ref = filament_ortak.referans()
    site_fil = [f for f in ref["filamentler"] if f.get("site")]
    ozel_fil = [f for f in ref["filamentler"] if not f.get("site")]

    # ---- 1) urunler.json degismemis
    d = subprocess.run(["git", "diff", "--name-only", "--", "urunler.json"],
                       capture_output=True, text=True, cwd=ROOT)
    kayit(1, "urunler.json degismemis (git diff bos)", d.stdout.strip() == "",
          d.stdout.strip() or "temiz")

    # ---- 2) 20 rastgele urun sayfasi (parametrik KAPSAMI garantili): cipler + rozet + balon
    # DETERMINIZM: 7903 urunun yalnizca 21'i parametrik -> duz random.sample parametrigi
    # ~%5 olasilikla yakalar; test o yuzden yazi-tura kirmizi/yesil olurdu. Rastgeleligi
    # koruyoruz (genis kapsam) ama en az BIR parametrik urunu ZORLA orneklemin icine koyuyoruz.
    par_hepsi = [u for u in urunler if u.get("parametrik")]
    ornek = random.sample(urunler, 20)
    if par_hepsi and not any(u.get("parametrik") for u in ornek):
        ornek[random.randrange(len(ornek))] = random.choice(par_hepsi)
    hatalar = []
    for p in ornek:
        s = sayfa(p["id"])
        cip_n = len(re.findall(r'class="fil-cip( tavsiyeli)?"', s))
        if cip_n != len(site_fil):
            hatalar.append("%s: cip sayisi %d != %d" % (p["id"], cip_n, len(site_fil)))
            continue
        for f in site_fil:
            if html.escape(f["uzun"], quote=True) not in s:
                hatalar.append("%s: '%s' balon metni birebir degil" % (p["id"], f["ad"]))
        for f in ozel_fil:
            if html.escape(f["uzun"], quote=True) in s:
                hatalar.append("%s: '%s' (ozel talep) urun sayfasinda cip olarak var" % (p["id"], f["ad"]))
        # OZEL KILIF YOK: F kalemi (Okan, 16 Tem gece) sonrasi parametrik (sari) sayfa normal
        # sayfayla BIREBIR -> rozet beklentisi HER uronde ayni sekilde kategoriden turer.
        # Bugun "Jeneratör" kategoriTavsiye haritasinda olmadigi icin sonuc bos liste cikiyor
        # (ayni bosluk TEST 25 kapisinda BILINCLI olarak kayitli); harita doldurulunca bu
        # test rozeti gormek isteyecek.
        beklenen = [t["ad"] for t in filament_ortak.tavsiyeler(
            p.get("kategori"), p.get("tavsiyeFilament"))]
        rozetli = [m.group(1) for m in re.finditer(
            r'fil-cip tavsiyeli[^>]*>.*?<span class="fil-ad">([^<]+)</span>', s)]
        if sorted(rozetli) != sorted(beklenen):
            hatalar.append("%s (%s): rozet %s != beklenen %s"
                           % (p["id"], p.get("kategori"), rozetli, beklenen))
    kayit(2, "20 rastgele sayfa (+en az 1 parametrik): %d cip (ABS/Karbon HARIC) + rozet + "
          "balon birebir + dogru tavsiye" % len(site_fil), not hatalar, "; ".join(hatalar[:4]))

    # ---- 3) yasak ifadeler: uretilen HICBIR sayfada "3d bask" / "her renk" yok
    yasak = []
    for pat in ["3d bask", "her renk"]:
        g = subprocess.run(["grep", "-rli", pat, "urun", "malzeme-rehberi",
                            "teslimat-iade", "mesafeli-satis", "filament-veri.js",
                            "sitemap.xml", "index.html", "sss", "hakkimizda",
                            "iletisim", "gizlilik"],
                           capture_output=True, text=True, cwd=ROOT)
        if g.stdout.strip():
            yasak.append("%r: %s" % (pat, g.stdout.strip().splitlines()[:3]))
    kayit(3, "'3D bask' ve 'her renk' hicbir uretilen sayfada yok", not yasak,
          "; ".join(yasak))

    # ---- 4) /malzeme-rehberi/ uretildi + footer linki + sitemap
    reh_yol = os.path.join(ROOT, "malzeme-rehberi", "index.html")
    reh_var = os.path.exists(reh_yol)
    reh = open(reh_yol, encoding="utf-8").read() if reh_var else ""
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    ornek_sayfa = sayfa(urunler[0]["id"])
    kosullar = {
        "sayfa uretildi": reh_var,
        "%d malzemenin hepsi rehberde" % len(ref["filamentler"]):
            reh_var and all((f.get("uzunAd") or f["ad"]) in reh for f in ref["filamentler"]),
        "karsilastirma tablosu": "karsilastirma" in reh and "HDT @ 0.45 MPa" in reh,
        "urun sayfasi footer linki": '/malzeme-rehberi/' in ornek_sayfa,
        "sitemap kaydi": "https://pruvo3d.com/malzeme-rehberi/" in sm,
    }
    kayit(4, "/malzeme-rehberi/ + footer + sitemap", all(kosullar.values()),
          ", ".join(k for k, v in kosullar.items() if not v) or "hepsi tamam")

    # ---- 5) parite testleri (ag gerekir; PARITE=0 ile atlanabilir)
    if os.environ.get("PARITE", "1") == "0":
        kayit(5, "parite testleri", True, "ATLANDI (PARITE=0)")
    else:
        p1 = subprocess.run(["node", os.path.join(TOOLS, "parite-test.js"), "300"],
                            capture_output=True, text=True, cwd=ROOT)
        p2 = subprocess.run(["node", os.path.join(TOOLS, "parite-ege.js"), "200"],
                            capture_output=True, text=True, cwd=ROOT)
        ok = p1.returncode == 0 and p2.returncode == 0
        det = "site:%s ege:%s" % ("YESIL" if p1.returncode == 0 else "KIRMIZI",
                                  "YESIL" if p2.returncode == 0 else "KIRMIZI")
        if not ok:
            det += " | " + (p1.stdout + p1.stderr + p2.stdout + p2.stderr).strip()[-300:]
        kayit(5, "parite (site + ege) — aciklama degismedi kaniti", ok, det)

    # ---- 6) override: sahte urunle render -> harita degil override basiliyor
    import importlib
    build = importlib.import_module("build")
    sahte = {"id": "test-override-sahte", "kategori": "Ev", "marka": [],
             "baslik": "Override Test", "aciklama": "test", "fiyat": "100 TL",
             "gorseller": [], "tavsiyeFilament": ["ASA"]}
    h = build.render_product(sahte, [sahte])
    rozetli = [m.group(1) for m in re.finditer(
        r'fil-cip tavsiyeli[^>]*>.*?<span class="fil-ad">([^<]+)</span>', h)]
    kayit(6, "tavsiyeFilament override haritayi eziyor (Ev+override[ASA] -> rozet ASA)",
          rozetli == ["ASA"], "rozetli=%s" % rozetli)

    # ---- 7) mobil tooltip: DOM/CSS duzeyinde dogrulama
    s = ornek_sayfa
    blok = s.split('class="malzeme-blok"', 1)[1].split("</a></div>", 1)[0] \
        if 'class="malzeme-blok"' in s else ""
    kosullar7 = {
        "balon her cipte": s.count('class="fil-balon"') == len(site_fil),
        "CSS: .acik ile balon acilir": ".fil-cip.acik .fil-balon{display:block}" in s,
        "CSS: hover ile balon acilir": ".fil-cip:hover .fil-balon" in s,
        "JS: dokunma toggle": 'classList.toggle("acik")' in s,
        "JS: disari dokununca kapanir": 'document.addEventListener("click"' in s,
        "aria-expanded var": 'aria-expanded="false"' in blok,
        "title= kullanilmamis (mobilde calismaz)": blok != "" and "title=" not in blok,
    }
    kayit(7, "mobil tooltip DOM/CSS dogrulamasi", all(kosullar7.values()),
          ", ".join(k for k, v in kosullar7.items() if not v) or "hepsi tamam")

    # ---- 8) ABS/Karbon Katkili urun sayfasinda SITE SECENEGI OLARAK sunulmuyor
    hatalar8 = []
    for f in ozel_fil:
        if ('value="%s"' % f["ad"]) in ornek_sayfa:
            hatalar8.append("%s: <option> olarak dropdown'da var" % f["ad"])
    if "wa.me/905451386526" not in ornek_sayfa:
        hatalar8.append("WhatsApp muhendislik-malzeme linki yok")
    kayit(8, "ABS/Karbon Katkili SITE SECENEGI olarak sunulmuyor (cip/dropdown yok, WA notu var)",
          not hatalar8, "; ".join(hatalar8) or "temiz")

    # ================= KART-SECIM (malzeme dropdown -> kart secici) =================
    FONK = {"Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin",
            "Bisiklet", "Bahçe", "Ofis", "Kamera"}
    fonk_urun = next((u for u in urunler
                      if u.get("kategori") in FONK and not u.get("parametrik")), None)
    fs = sayfa(fonk_urun["id"]) if fonk_urun else ""

    # ---- 9 (a) dropdown YOK + kartlar data-malzeme + tiklama SECER
    h9 = []
    if not fonk_urun:
        h9.append("fonksiyonel non-parametrik urun bulunamadi")
    else:
        if 'id="malzemeSec"' in fs:
            h9.append("malzeme dropdown hala var")
        for f in site_fil:
            if ('data-malzeme="%s"' % html.escape(f["ad"], quote=True)) not in fs:
                h9.append("%s karti data-malzeme tasimıyor" % f["ad"])
        for parca in ["var KART_SECIM = true;",
                      'seciliMalzeme = this.getAttribute("data-malzeme")',
                      'classList.toggle("secili"']:
            if parca not in fs:
                h9.append("secim JS eksik: %s" % parca)
    kayit(9, "(a) malzeme dropdown YOK + kartlar data-malzeme + tiklama secim JS'i",
          not h9, "; ".join(h9[:4]) or "temiz")

    # ---- 10 (b) acilista secili kart YOK + fiyat "baslayan"
    h10 = []
    if 'class="fil-cip secili' in fs or 'class="fil-cip tavsiyeli secili' in fs:
        h10.append("acilista bir kart 'secili' isaretli (onden secim olmamali)")
    m10 = re.search(r'id="opsiyonFiyat">([^<]*)<', fs)
    if not (m10 and "başlayan" in m10.group(1)):
        h10.append("opsiyonFiyat 'baslayan' halinde degil: %r" % (m10.group(1) if m10 else None))
    kayit(10, "(b) acilista secili kart yok + fiyat '…den baslayan'", not h10,
          "; ".join(h10) or "temiz")

    # ---- 11 (c) secimsiz Sepete Ekle -> eklenmez + titreme/kirmizi
    h11 = []
    for parca in ["var eksikM = !seciliMalzeme;",
                  "if(eksikM){ titret(cipler); }",
                  'el.classList.add("titre", kutu ? "hata" : "hata-vurgu")',
                  "@keyframes pruvoTitre",
                  ".titre{animation:pruvoTitre",
                  ".hata-vurgu .fil-cip,.hata-vurgu .renk-btn{border-color:var(--red)"]:
        if parca not in fs:
            h11.append("eksik: %s" % parca)
    kayit(11, "(c) secimsiz Sepete Ekle -> eklenmez + titreme/kirmizi (CSS+JS)",
          not h11, "; ".join(h11[:3]) or "temiz")

    # ---- 12 (d) secimle fiyat KATSAYILI guncellenir (JS wiring + kuruş matematigi)
    h12 = []
    if 'fiyatEl.textContent = ozet.fiyatMetni + "' not in fs and \
       "fiyatEl.textContent = ozet.fiyatMetni +" not in fs:
        h12.append("secimsiz 'baslayan' fiyat JS dali yok")
    if "fiyatEl.textContent = ozet.fiyatMetni;" not in fs:
        h12.append("secili kesin fiyat JS dali yok")
    # secenekler.js kuruş matematigi: PETG (+%30) PLA tabanindan farkli olmali
    r12 = subprocess.run(
        ["node", "-e",
         "require('./secenekler.js');var P=globalThis.PRUVO_SECENEK;"
         "var b=P.hesaplaFiyatKurus(350,'PLA','Siyah',0);"
         "var g=P.hesaplaFiyatKurus(350,'PETG','Siyah',0);"
         "if(b===35000 && g===45500 && g===Math.round(b*1.30)){console.log('OK')}"
         "else{console.error('base',b,'petg',g);process.exit(1)}"],
        capture_output=True, text=True, cwd=ROOT)
    if r12.returncode != 0:
        h12.append("kuruş matematigi: " + (r12.stdout + r12.stderr).strip())
    kayit(12, "(d) secimle fiyat KATSAYILI guncellenir (JS wiring + PETG +%30 kuruş)",
          not h12, "; ".join(h12[:3]) or "temiz")

    # ---- 13 (e) alt paragraf HICBIR urun sayfasinda yok
    g13 = subprocess.run(["grep", "-rl", "Sepete ekleyip birden çok", "urun"],
                         capture_output=True, text=True, cwd=ROOT)
    kayit(13, "(e) alt paragraf ('Sepete ekleyip…') hicbir urun sayfasinda yok",
          g13.stdout.strip() == "", g13.stdout.strip().splitlines()[:3])

    # ---- 14 (f) WhatsApp'tan Sor secim SARTI ARAMAZ
    #   (madde 7 sonrasi: kart-secim sayfasinda link IKON olarak Adet satirinda; hala <a href>)
    h14 = []
    if 'id="orderAlt"' not in fs or '<a class="ikon-btn ikon-wa" id="orderAlt"' not in fs:
        h14.append("orderAlt (WhatsApp'tan Sor) ikon linki yok")
    # titret/gate yalniz cartBtn tiklamasinda; orderAlt bir <a href> ve kilitlenmiyor
    if "orderAlt.disabled" in fs or "orderAlt.classList.add(\"kilitli\")" in fs:
        h14.append("orderAlt secime kilitlenmis")
    kayit(14, "(f) WhatsApp'tan Sor secim sarti aramaz (link her zaman calisir)",
          not h14, "; ".join(h14) or "temiz")

    # ================= RENK BUTONLARI (dropdown -> buton, Okan ek madde) =================
    # Renk listesi TEK KAYNAK secenekler.js (build.py da oradan okur).
    sec_js = open(os.path.join(ROOT, "secenekler.js"), encoding="utf-8").read()
    RENK_SECENEKLERI = json.loads(re.search(r'var RENK_SECENEKLERI = (\[.*?\]);', sec_js).group(1))

    # ---- 15 (g) renk dropdown YOK + 4 buton var + Diger'de gradyan
    h15 = []
    if 'id="renkSec"' in fs:
        h15.append("renk dropdown hala var")
    if fs.count('class="renk-btn"') != len(RENK_SECENEKLERI):
        h15.append("renk-btn sayisi %d != %d" % (fs.count('class="renk-btn"'), len(RENK_SECENEKLERI)))
    for r in RENK_SECENEKLERI:
        if ('data-renk="%s"' % html.escape(r, quote=True)) not in fs:
            h15.append("data-renk=%s butonu yok" % r)
    if "renk-yuvar-gokkusagi" not in fs or "conic-gradient" not in fs:
        h15.append("Diger gokkusagi gradyan yuvarlagi yok")
    kayit(15, "(g) renk dropdown yok + %d buton + Diger gradyan" % len(RENK_SECENEKLERI),
          not h15, "; ".join(h15[:4]) or "temiz")

    # ---- 16 (h) acilista renk seçimsiz
    h16 = []
    if 'class="renk-btn secili' in fs:
        h16.append("acilista bir renk butonu 'secili' (onden secim olmamali)")
    if "var seciliRenk = \"\";" not in fs:
        h16.append("seciliRenk bos baslamiyor")
    # renkOzel kutusu acilista gizli
    m16 = re.search(r'id="renkOzel"[^>]*style="display:none"', fs)
    if not m16:
        h16.append("renkOzel kutusu acilista gizli degil")
    kayit(16, "(h) acilista renk secimsiz + renkOzel gizli", not h16, "; ".join(h16) or "temiz")

    # ---- 17 (i) Diger seçince metin kutusu görünür + boşken sepete eklenmez
    h17 = []
    for parca in ['renkOzel.style.display = (seciliRenk === "Diğer") ? "block" : "none"',
                  'var eksikO = seciliRenk === "Diğer" && renkOzel && !renkOzel.value.trim();',
                  "if(eksikO){ titret(renkOzel); }",
                  ".renk-ozel.hata{border-color:var(--red)"]:
        if parca not in fs:
            h17.append("eksik: %s" % parca)
    kayit(17, "(i) Diger -> metin kutusu gorunur; bosken sepete eklenmez (titrer)",
          not h17, "; ".join(h17[:3]) or "temiz")

    # ---- 18 (j) Diger + metin dolu -> not alaniyla sepete + fiyat +%15
    #   Veri modeli: r="Diğer" kalir, musteri metni renk_ozel'de tasinir; secenekler.js
    #   satirOzeti bunu WhatsApp mesajina koyar ve +%15 uygular. Runtime (node) ile dogrula.
    r18 = subprocess.run(
        ["node", "-e",
         "require('./secenekler.js');var P=globalThis.PRUVO_SECENEK;"
         "var u={id:'x',kategori:'Marin',fiyat:'350 TL'};"
         "var s={id:'x',malzeme:'PLA',renk:'Diğer',renk_ozel:'turuncu',boy_etiket:null,adet:1};"
         "var o=P.satirOzeti(u,s);"
         # +%15: 350*100*100*115/10000 = 40250 kuruş
         "var beklenen=Math.round(350*100*100*115/10000);"
         "if(o.birimKurus===beklenen && o.detay.indexOf('turuncu')>=0){console.log('OK')}"
         "else{console.error('birim',o.birimKurus,'bek',beklenen,'detay',o.detay);process.exit(1)}"],
        capture_output=True, text=True, cwd=ROOT)
    h18 = [] if r18.returncode == 0 else [(r18.stdout + r18.stderr).strip()]
    # JS wiring: renk_ozel'i satira 30 karakterle yaziyor (istemci de sinirliyor)
    if "renkOzel.value.trim().slice(0, 30)" not in fs:
        h18.append("renkOzel istemci tarafi 30 karakter sinir yok")
    kayit(18, "(j) Diger + metin dolu -> renk_ozel not alaniyla sepete + fiyat +%15",
          not h18, "; ".join(h18[:3]) or "temiz")

    # ---- 19 (k) Siyah seçiminde fiyata renk farki BINMEZ (PLA/Siyah = taban)
    r19 = subprocess.run(
        ["node", "-e",
         "require('./secenekler.js');var P=globalThis.PRUVO_SECENEK;"
         "var u={id:'x',kategori:'Marin',fiyat:'350 TL'};"
         "var siyah=P.satirOzeti(u,{id:'x',malzeme:'PLA',renk:'Siyah',renk_ozel:'',boy_etiket:null,adet:1});"
         "var diger=P.satirOzeti(u,{id:'x',malzeme:'PLA',renk:'Diğer',renk_ozel:'mor',boy_etiket:null,adet:1});"
         "if(siyah.birimKurus===35000 && diger.birimKurus===40250){console.log('OK')}"
         "else{console.error('siyah',siyah.birimKurus,'diger',diger.birimKurus);process.exit(1)}"],
        capture_output=True, text=True, cwd=ROOT)
    h19 = [] if r19.returncode == 0 else [(r19.stdout + r19.stderr).strip()]
    kayit(19, "(k) Siyah/Beyaz/Gri renk farki binmez; Diger +%15 (kuruş)",
          not h19, "; ".join(h19[:2]) or "temiz")

    # ---- 20 liste kartlari sade: "Sepete Ekle" butonu + "Tavsiye:" cipi YOK; urun sayfasi regresyonsuz
    ih = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    h20 = []
    # Hizli-ekleme yolunun TUM parcalari kalkti (buton, toggle, sync, cip, veri script'i).
    for yasak in ["setCartBtn", "syncCardButtons", "toggleCart(",
                  '"Tavsiye: "', "card-fil", 'src="/filament-veri.js"']:
        if yasak in ih:
            h20.append("index.html'de hala var: %s" % yasak)
    # bosSatir SADECE goc icin secenekler.js'te kalir; index.html'de dogrudan cagri kalmadi.
    if "bosSatir(" in ih:
        h20.append("index.html hala bosSatir cagiriyor (varsayilan-PLA ekleme yolu)")
    # build.py ilgili-urunler kartlari da temiz (rel-card yalniz gorsel+baslik+fiyat).
    m20 = re.search(r'<section class="related">.*?</section>', fs, re.S)
    rel_html = m20.group(0) if m20 else ""
    if "Sepete Ekle" in rel_html:
        h20.append("ilgili-urunler kartinda Sepete Ekle var")
    if "Tavsiye:" in rel_html:
        h20.append("ilgili-urunler kartinda Tavsiye cipi var")
    # REGRESYON: urun sayfasinda sepete ekleme + malzeme kartlari DURUYOR.
    for gerekli in ['id="cartBtn"', 'id="filCipler"', "data-malzeme="]:
        if gerekli not in fs:
            h20.append("urun sayfasinda kayip: %s" % gerekli)
    kayit(20, "liste kartlarinda Sepete Ekle + Tavsiye yok; urun sayfasi regresyonsuz",
          not h20, "; ".join(h20[:4]) or "temiz")

    # ================= EYLEM IKONLARI (madde 7: buyuk butonlar -> Adet satirina ikon) ==========
    # ---- 21 (l) buyuk butonlar yok + Adet satirinda 2 aria-label'li ikon; PARAMETRIK DE AYNI
    h21 = []
    if 'class="cart-btn"' in fs or 'class="order-wa"' in fs:
        h21.append("kart-secim sayfasinda buyuk buton hala var")
    if not re.search(r'opsiyon-adet-eylem.*?id="adetArti".*?eylem-ikonlar.*?'
                     r'ikon-sepet" id="cartBtn"[^>]*aria-label="Sepete Ekle" title="Sepete Ekle".*?'
                     r'ikon-wa" id="orderAlt"[^>]*aria-label="WhatsApp\'tan Sor"[^>]*title="WhatsApp\'tan Sor"', fs, re.S):
        h21.append("Adet satirinda aria-label+title'li ikon cifti eksik/sirasiz")
    if ".ikon-btn{width:44px;height:44px" not in fs:
        h21.append("44x44 dokunma alani CSS'i yok")
    # SEMALI PARAMETRIK (sari) SAYFA DA KART-SECIM MODUNDA — F kalemi (Okan, 16 Tem gece;
    # commit 68cf6939 "Faz D ek kalemler E+F"): parametrik sayfa duzeni normal sayfayla
    # ESITLENDI. build.py:1197 `kart_secim = bool(sema) or (fonksiyonel and not parametrik)`
    # -> semali parametrikte butonlar Adet satirinda, sayfa altina buyuk buton BASILMAZ.
    # (16 Tem 15:44'te yazilan "parametrik duzene dokunulmadi" iddiasi Okan'in SONRAKI
    #  karariyla gecersiz kaldi; test o gun bayatladi.) Buyuk buton yolunun NOBETCISI -> TEST 24.
    par_u = next((u for u in urunler if u.get("parametrik")), None)
    ps21 = sayfa(par_u["id"]) if par_u else ""
    if not par_u:
        h21.append("parametrik urun bulunamadi (kapsam olculemedi)")
    if par_u and "ikon-btn ikon-sepet" not in ps21:
        h21.append("parametrik sayfada ikon sepet yok (kart-secim duzeni bekleniyor)")
    if par_u and "ikon-btn ikon-wa" not in ps21:
        h21.append("parametrik sayfada ikon WhatsApp yok (kart-secim duzeni bekleniyor)")
    if 'class="cart-btn" id="cartBtn"' in ps21 or 'class="order-wa" id="orderAlt"' in ps21:
        h21.append("parametrik sayfada eski BUYUK butonlar geri gelmis (F kalemi geri alinmis)")
    kayit(21, "(l) buyuk butonlar kalkti, Adet satirinda 2 ikon (aria+title+44px); "
          "semali parametrik sayfa da AYNI kart-secim duzeninde",
          not h21, "; ".join(h21[:4]) or "temiz")

    # ---- 22 (m) ikon sepet = ayni cartBtn -> secimsiz kapi + titreme AYNEN (id + kapi JS'i)
    h22 = []
    if fs.count('id="cartBtn"') != 1:
        h22.append("cartBtn id'si tek degil (%d)" % fs.count('id="cartBtn"'))
    for parca in ["var eksikM = !seciliMalzeme;",          # kapi ayni kodla duruyor
                  "if(eksikM){ titret(cipler); }",
                  '"Sepette ✓ — çıkarmak için tıklayın"']:  # ikonda durum title/aria ile
        if parca not in fs:
            h22.append("eksik: %s" % parca)
    kayit(22, "(m) ikon sepet butonu = ayni kapi (secimsiz eklemez + titrer) + durum aria/title",
          not h22, "; ".join(h22[:3]) or "temiz")

    # ---- 23 (n) WhatsApp ikonu dogru hedef: statik href + JS canli guncelleme
    h23 = []
    m23 = re.search(r'id="orderAlt" href="([^"]+)"', fs)
    if not (m23 and m23.group(1).startswith("https://wa.me/905451386526?text=")):
        h23.append("statik href wa.me/905451386526 degil: %r" % (m23.group(1)[:60] if m23 else None))
    if 'orderAlt.href = "https://wa.me/905451386526?text=" + encodeURIComponent(mesaj);' not in fs:
        h23.append("JS canli mesaj guncellemesi yok")
    kayit(23, "(n) WhatsApp ikonu dogru wa.me hedefi (statik + JS)", not h23,
          "; ".join(h23[:2]) or "temiz")

    # ---- 24 NOBETCI: BUYUK buton yolu hala CANLI (panelsiz Dekorasyon/Oyun-Hobi sayfasi)
    # TEST 21'den parametrik iddiasi kalkinca build.py BUYUK_BUTONLAR_HTML dalini olcen
    # baska hicbir iddia kalmiyordu -> dal silinse/bosalsa kimse yakalamazdi. Panelsiz sayfa
    # = ne FONKSIYONEL kategoride ne parametrik (bugun Dekorasyon + Oyun/Hobi): opsiyon paneli
    # basilmaz, eylem butonlari sayfa altinda BUYUK halde kalir.
    h24 = []
    pnl_u = next((u for u in urunler
                  if u.get("kategori") not in FONK and not u.get("parametrik")), None)
    if not pnl_u:
        h24.append("panelsiz (Dekorasyon/Oyun-Hobi) urun bulunamadi — nobetci olcemiyor")
    else:
        pnls = sayfa(pnl_u["id"])
        if 'class="cart-btn" id="cartBtn"' not in pnls:
            h24.append("%s: buyuk 'Sepete Ekle' butonu yok" % pnl_u["id"])
        if 'class="order-wa" id="orderAlt"' not in pnls:
            h24.append("%s: buyuk 'WhatsApp'tan Sor' butonu yok" % pnl_u["id"])
        if "ikon-btn ikon-sepet" in pnls:
            h24.append("%s: panelsiz sayfaya ikon cifti tasinmis" % pnl_u["id"])
    kayit(24, "NOBETCI: panelsiz (%s) sayfada BUYUK butonlar yerinde, ikon yok"
          % ((pnl_u or {}).get("kategori") or "?"), not h24, "; ".join(h24[:3]) or "temiz")

    # ---- 25 KAPI: kategori <-> tavsiye haritasi boslugu FAIL-CLOSED
    # urunler.json'da FIILEN kullanilan her kategori icin ya filament_ortak.tavsiyeler()
    # bir tavsiye uretecek, ya da kategori asagidaki BILINCLI-BOS listesinde olacak.
    # Yarin yeni bir kategori acilip tavsiyesiz kalirsa bu test KIRMIZI yanar (sessiz gecmez).
    BILINCLI_BOS = {
        # Jeneratör = sari/parametrik seri. F kalemi eski "konusarak belirleriz" notunu
        # kaldirdi, yerine kategori-geneli tavsiye HENUZ KARARLASTIRILMADI (OKAN KAPISI).
        # Karar verilince filamentler.json kategoriTavsiye'ye eklenip buradan cikarilacak.
        "Jeneratör",
    }
    h25 = []
    kullanilan_kat = sorted({(u.get("kategori") or "").strip() for u in urunler} - {""})
    for k in kullanilan_kat:
        if filament_ortak.tavsiyeler(k):
            continue
        if k in BILINCLI_BOS:
            continue
        h25.append("%s: tavsiye uretmiyor + BILINCLI_BOS listesinde de degil" % k)
    # ters yon — liste bayatlamasin: haritaya eklendiyse BILINCLI_BOS'tan cikarilmali
    for k in sorted(BILINCLI_BOS):
        if filament_ortak.tavsiyeler(k):
            h25.append("%s: artik tavsiye uretiyor -> BILINCLI_BOS listesinden cikarilmali" % k)
    kayit(25, "KAPI: kullanilan %d kategorinin hepsi ya tavsiye uretir ya BILINCLI_BOS'ta "
          "(bugun bilincli bos: %s)" % (len(kullanilan_kat), ", ".join(sorted(BILINCLI_BOS))),
          not h25, "; ".join(h25[:4]) or "temiz")

    print("-" * 70)
    kaldi = [x for x in SONUC if not x[2]]
    if kaldi:
        print("SONUC: %d/%d test KIRMIZI ❌" % (len(kaldi), len(SONUC)))
        sys.exit(1)
    print("SONUC: %d/%d test YESIL ✅" % (len(SONUC), len(SONUC)))


if __name__ == "__main__":
    try:
        main()
    finally:
        # main() sys.exit ile de cikabilir (SystemExit) ya da istisna atabilir; finally her
        # iki durumda da kosar -> kosum SONRASI checkout DAIMA temiz (kabul testi #5).
        _yasal_sayfalari_geri_yukle()
