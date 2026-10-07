#!/usr/bin/env python3
"""PRUVO — "Fotoğrafından özel üretim" ana sayfa bölümü KABUL KAPISI (istemci tarafı).

    python3 tools/foto-uretim-bolum-test.py

Okan kararı (5 Eki 2026, aynen): "anasayfada 2 browseren altına kategorilerin üzerine kursun
mobil uyumlu tam sayfayı kaplasın örnek çıktılarda görünsün müşteri abartılı hayallere
kapılmasın". Sunucu tarafı ayrı kapıda (shop/test/foto-uretim.mjs); bu dosya ekranın
SÖZLEŞMESİNİ ölçer:

  🔴 OKAN EMRİ (7 Eki 2026, aynen): "ana sayfaya eklediğin herşeyi kaldır sistem hazır değil".
  Y1-Y3 + Y5'in ANA SAYFA kolları ters yöne çevrildi: index.html'de bölüm kabı, iki betik,
  renderGrid liste girdisi, ödeme dönüşü foto kolu ve atıf köprüsü YOK. Biri geri eklenirse
  KIRMIZI (mutantlar M1/M2/M5/M15/M16). Bölüm dosyası + veri dosyası REPODA kalır.

  Y1 YOK      : index.html'de `fotoUretim` kabı / `foto-uretim` adı 0
  Y2 GÖRÜNÜM  : renderGrid görünüm listesi foto öncesiyle AYNI (fotoUretim girdisi 0)
  Y3 YÜKLEME  : ana sayfa iki betiği ÇAĞIRMAZ; dosyalar yayın beyaz listesinde kalabilir
                (build.py SOYULACAK_JS — değer olarak okunur, metin araması değil)
  Y4 DÜRÜSTLÜK: bölüm "önizlemenin 4 renkli yorumu" ifadesini taşır; "3D baskı" demez;
                örnek kaydı üç görseli (foto/önizleme/BASILMIŞ) şart koşar (veri dosyası)
  Y5 SEPET    : ana sayfa ödeme dönüşü foto kolu taşımaz (oturum anahtarı / `ozel-foto` /
                atıf köprüsü 0) — sepet siparişi foto öncesi davranışta
  Y6 GÜVENLİK : bölüm DOM'a innerHTML ile veri basmaz; yalnız aynı köken /api/shop uçları
  Y7 SÖZDİZİMİ: node --check (node yoksa OLCULEMEDI, yeşil sayılmaz)
  Y8 PLAKET   : veri dosyasında plaket VAR, anahtarlık/magnet/figür türü 0; anahtarlık/magnet ekranda 0
                (BaBa 5 Eki 21:4x(b) — "yalnız plastik üretiyoruz")
  Y9 TEK TÜR  : tek türde tür grubu gizlenir, adım çubuğu "Ölçü" der (DAVRANIŞ ölçümü sahte
                DOM'da: shop/test/foto-uretim.mjs S bölümü; bu dosya sözleşmeyi tutar)
  Y10 RENDER  : (Okan 7 Eki: plaket gerçek baskı beklemeden açılır) türe göre `ornek_kanit_izni`
                (plaket baski+render · litofan baski+render — Okan 7 Eki G1) + izin kontrolü veri dosyasında; render
                dalında "önizleme/render" etiketi + abartı cümlesi AYNEN, "gerçek fotoğraf" 0
                (DAVRANIŞ: shop/test/foto-uretim.mjs RO/ES bölümü)

ÖNCE-KIRMIZI: aynı kontrol fonksiyonları dosyanın sonunda BELLEKTEKİ mutant metinlere
uygulanır (diske yazılmaz): kap ana sayfaya geri eklenir · görünüm listesine geri girer ·
betik geri çağrılır · ödeme dönüşü foto kolu geri gelir · dürüstlük ifadesi silinir ·
beyaz listeden düşer. Her mutant en az
bir kontrolü kırmızıya çevirmeli; K0 kontrol mutantı (yorum ekleme) hiçbirini çevirmemeli.

Çıkış: 0 yeşil · 1 kırmızı · 3 ÖLÇÜLEMEDİ.
"""
import ast
import os
import re
import shutil
import subprocess
import sys

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OKU = lambda rel: open(os.path.join(KOK, rel), encoding="utf-8").read()

OTURUM_ANAHTARI = "pruvo_foto_siparis"
DURUSTLUK = "önizlemenin 4 renkli yorumu"
RENDER_CUMLE = ("Önizleme ve üretim dosyasının görüntüsüdür; basılmış ürün bu yorumun kabartmalı hâlidir, "
                "birebir aynısı değildir.")
LITOFAN_CUMLE = ("Üretim dosyasının arkadan ışıkla görüntüsüdür; basılmış panel ışık geldiğinde bu görüntüyü verir, "
                 "birebir aynısı değildir.")


def soyulacak_js(build_metin):
    m = re.search(r"^SOYULACAK_JS\s*=\s*(\([^)]*\))", build_metin, re.M | re.S)
    if not m:
        return None
    try:
        return ast.literal_eval(m.group(1))
    except (ValueError, SyntaxError):
        return None


def kontroller(index, bolum, veri, build):
    """[(ad, gecti, ayrinti)] — metin girdileri; disk/ag yok (mutantlar da bunu kullanir)."""
    s = []
    # Okan 7 Eki: "ana sayfaya eklediğin herşeyi kaldır" — ana sayfa kolları YOKLUĞU ölçer.
    s.append(("Y1 ana sayfada fotoUretim kabi YOK", 'id="fotoUretim"' not in index and "fotoUretim" not in index,
              "fotoUretim=%d" % index.count("fotoUretim")))
    s.append(("Y1 ana sayfada 'foto-uretim' adi YOK (kap sinifi / betik)", "foto-uretim" not in index,
              "foto-uretim=%d" % index.count("foto-uretim")))
    liste = re.search(r'\[\s*"katPanels"[^\]]*\]\.forEach', index)
    s.append(("Y2 renderGrid gorunum listesi foto oncesiyle AYNI",
              bool(liste) and re.sub(r"\s+", "", liste.group(0)) ==
              '["katPanels","bannerRow","jenBanner","skanBanner"].forEach',
              liste.group(0) if liste else "liste yok"))
    s.append(("Y3 ana sayfa foto betiklerini CAGIRMAZ",
              not re.search(r'<script[^>]*src="/foto-uretim(-veri)?\.js"', index), ""))
    js = soyulacak_js(build) or ()
    s.append(("Y3 iki dosya yayin beyaz listesinde (SOYULACAK_JS degeri)",
              "foto-uretim-veri.js" in js and "foto-uretim.js" in js, str(js)))
    s.append(("Y4 durustluk ifadesi manifestte (plaket turu `durustluk`)", DURUSTLUK in veri, ""))
    s.append(("Y4b bolum ust kutuyu secili turun `durustluk`undan basar, sabit metin YOK",
              "t.durustluk" in bolum and "durustlukGuncelle();" in bolum and DURUSTLUK not in bolum
              and "4 renkle kabartma olarak" not in bolum, ""))
    yasak = [k for k in ("3d bask", "3 boyutlu bask", "fethiye", "göcek", "gocek")
             if k in bolum.lower() or k in veri.lower()]
    s.append(("Y4 '3D baski' / sehir adi YOK", not yasak, ",".join(yasak)))
    s.append(("Y4 ornek sayaci uc gorseli (foto+onizleme+baski) sart kosar",
              re.search(r"o\.foto\s*&&\s*o\.onizleme\s*&&\s*o\.baski", veri) is not None, ""))
    kalinti = [k for k in (OTURUM_ANAHTARI, "ozel-foto", "fotoSiparisi", "pruvoAtifTopla") if k in index]
    s.append(("Y5 ana sayfa odeme donusunde foto kolu / atif koprusu YOK", not kalinti, ",".join(kalinti)))
    s.append(("Y6 bolum innerHTML kullanmaz", "innerHTML" not in bolum, ""))
    uclar = set(re.findall(r'"(/api/[a-z/]+)', bolum))
    beklenen = {"/api/shop/foto/acik", "/api/shop/foto/onizleme", "/api/shop/foto/durum", "/api/shop/baslat"}
    s.append(("Y6 bolum uclari = foto uclari + baslat (aynı köken)",
              beklenen <= uclar and all(u.startswith("/api/shop/") for u in uclar), str(sorted(uclar))))
    harici = sorted(set(re.findall(r"https?://[A-Za-z0-9.-]+", bolum)))
    izinli = {"https://challenges.cloudflare.com", "https://wa.me"}
    s.append(("Y6 harici adres yalniz bot dogrulayici + WhatsApp", set(harici) <= izinli, str(harici)))
    # Y8 PLAKET (BaBa 5 Eki 21:4x(b)): veri dosyasinin `turler` dizisinde TEK tur = plaket.
    tb = re.search(r"\bturler:\s*\[(.*?)\n\s*\],", veri, re.S)
    kodlar = re.findall(r'\bkod:\s*"([^"]+)"', tb.group(1)) if tb else []
    # 6 Eki (kategori kaydi): tek-tur yerine "plaket VAR + metal gerektiren tur 0".
    s.append(("Y8 plaket VAR ve anahtarlik/magnet/figur turu 0",
              "plaket" in kodlar and not any(k in kodlar for k in ("anahtarlik", "magnet", "figur")), str(kodlar)))
    eski = [k for k in ("anahtarl", "magnet", "mıknatıs", "miknatis")
            if k in bolum.lower() or k in (tb.group(1).lower() if tb else "")]
    s.append(("Y8 anahtarlik/magnet secenegi ekranda + tur listesinde 0", not eski, ",".join(eski)))
    # Y9 TEK TUR: tur secimi cizilmez + adim cubugu "Olcu" der (davranis: foto-uretim.mjs S).
    s.append(("Y9 tek turde tur grubu gizlenir ve radyo cizilmeden donulur",
              re.search(r"if \(S\.acikVeri\.turler\.length === 1\) \{[^}]*S\.alanTur\.hidden = true;\s*return;", bolum)
              is not None, ""))
    s.append(("Y9 adim cubugu tur sayisina gore 'Ölçü' der",
              'F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"' in bolum, ""))
    # Y10 RENDER ORNEGI (Okan 7 Eki): kanit izni tur kaydinda, izin kontrolu sayacta.
    izinler = dict(re.findall(r'kod:\s*"([a-z]+)",.*?ornek_kanit_izni:\s*(\[[^\]]*\])', veri, re.S))
    s.append(("Y10 kanit izni: plaket [baski,render] · litofan [baski,render] (Okan 7 Eki G1)",
              izinler.get("plaket") == '["baski", "render"]' and izinler.get("litofan") == '["baski", "render"]', str(izinler)))
    s.append(("Y10 sayac izin disi kaniti saymaz (izin kontrolu veri dosyasinda)",
              re.search(r"if \(!k \|\| izin\.indexOf\(k\) < 0\) \{ return false; \}", veri) is not None, ""))
    dal = "".join(re.findall(r'if \(it\.kanit === "render"\) \{(.*?)\} else \{', bolum, re.S))
    # Cumle tur kaydinda (`ornek_notu`, mimar karari 7 Eki): bolum yalniz kayittan basar.
    notlar = dict(re.findall(r'kod:\s*"([a-z]+)",.*?ornek_notu:\s*"([^"]*)"', veri, re.S))
    s.append(("Y10 render dalinda 'önizleme/render' etiketi + tur cumlesi (ornek_notu) kayittan",
              '"önizleme/render"' in dal and "it.tur.ornek_notu" in dal and "kabartmalı" not in bolum, ""))
    s.append(("Y10 plaket ornek_notu = karar cumlesi AYNEN", notlar.get("plaket") == RENDER_CUMLE, str(notlar.get("plaket"))))
    s.append(("Y11 litofan ornek_notu = litofan cumlesi AYNEN ('kabartmalı' 0)",
              notlar.get("litofan") == LITOFAN_CUMLE, str(notlar.get("litofan"))))
    s.append(("Y10 render dalinda 'gerçek fotoğraf' metni 0", bool(dal) and "gerçek fotoğraf" not in dal.lower(), ""))
    return s


def main():
    try:
        index, veri, build = OKU("index.html"), OKU("foto-uretim-veri.js"), OKU("tools/build.py")
        bolum = OKU("foto-uretim.js")
    except OSError as e:
        print("OLCULEMEDI: dosya okunamadi — %s" % e)
        return 3
    kirmizi = 0
    for ad, gecti, ek in kontroller(index, bolum, veri, build):
        print(("  ✅ " if gecti else "  ❌ ") + ad + ("" if gecti or not ek else " — " + ek))
        kirmizi += 0 if gecti else 1
    node = shutil.which("node")
    if not node:
        print("  ❌ Y7 OLCULEMEDI: node yok (yesil sayilmaz)")
        kirmizi += 1
    else:
        for rel in ("foto-uretim.js", "foto-uretim-veri.js"):
            p = subprocess.run([node, "--check", os.path.join(KOK, rel)], capture_output=True, text=True)
            print(("  ✅ " if p.returncode == 0 else "  ❌ ") + "Y7 node --check " + rel)
            kirmizi += 0 if p.returncode == 0 else 1

    # ---- mutantlar (bellekte) ----
    def kirmizi_sayisi(i, b, v, bu):
        return sum(1 for _, g, _ in kontroller(i, b, v, bu) if not g)
    # Geri-ekleme mutantlari: kaldirilan her ana sayfa parcasi tek tek geri konur.
    capa_kat = '<div id="katPanels" class="kat-panels"></div>'
    capa_sec = '<script src="/secenekler.js"></script>'
    capa_liste = '"skanBanner"].forEach'
    capa_sepet = 'cart = []; saveCart(); updateCartFab();\n      // KDV dokumu'  # odeme donusu (tekil)
    mutantlar = [
        ("M1 kap ana sayfaya geri eklendi",
         (index.replace(capa_kat, '<section id="fotoUretim" class="foto-uretim" hidden></section>\n  ' + capa_kat, 1),
          bolum, veri, build), True),
        ("M2 gorunum listesine geri girdi",
         (index.replace(capa_liste, '"skanBanner", "fotoUretim"].forEach', 1), bolum, veri, build), True),
        ("M15 betik ana sayfaya geri eklendi",
         (index.replace(capa_sec, capa_sec + '\n<script src="/foto-uretim.js" defer></script>', 1), bolum, veri, build), True),
        ("M5 odeme donusu foto kolu geri geldi",
         (index.replace(capa_sepet, 'if(sessionStorage.getItem("%s") === no){} else ' % OTURUM_ANAHTARI + capa_sepet, 1),
          bolum, veri, build), True),
        ("M16 atif koprusu geri geldi",
         (index.replace("</body>", "<script>window.pruvoAtifTopla = function(){};</script>\n</body>", 1), bolum, veri, build), True),
        ("M3 durustluk ifadesi silindi", (index, bolum, veri.replace(DURUSTLUK, "önizlemenin yorumu"), build), True),
        ("M14 bolum sabit durustluk metnine dondu",
         (index, bolum.replace("t && t.durustluk ? t.durustluk : \"\"", "\"Ürün en çok 4 renkle kabartma olarak üretilir\""), veri, build), True),
        ("M4 beyaz listeden dustu", (index, bolum, veri, build.replace('"foto-uretim.js", ', "", 1).replace(', "foto-uretim.js"', "", 1)), True),
        ("M6 anahtarlik tur listesine geri eklendi",
         (index, bolum, veri.replace('kod: "plaket",', 'kod: "plaket",\n      },\n      {\n        kod: "anahtarlik",', 1), build), True),
        ("M7 tek tur dali silindi",
         (index, re.sub(r"if \(S\.acikVeri\.turler\.length === 1\) \{[^}]*\}\n", "", bolum, count=1), veri, build), True),
        ("M8 izin kontrolu silindi",
         (index, bolum, veri.replace("if (!k || izin.indexOf(k) < 0) { return false; }", "if (!k) { return false; }", 1), build), True),
        ("M9 abarti cumlesi degisti", (index, bolum, veri.replace("kabartmalı hâlidir, birebir aynısı değildir.", "kabartmalı hâlidir.", 1), build), True),
        ("M12 litofan cumlesi plaketinkiyle degisti", (index, bolum, veri.replace(LITOFAN_CUMLE, RENDER_CUMLE, 1), build), True),
        ("M13 bolum sabit cumleye dondu",
         (index, bolum.replace("it.tur.ornek_notu", '"' + RENDER_CUMLE + '"', 1), veri, build), True),
        ("M10 render etiketi 'gerçek fotoğraf' oldu",
         (index, bolum.replace('"foto-uretim-ornek-etiket", "önizleme/render"', '"foto-uretim-ornek-etiket", "Basılmış ürün (gerçek fotoğraf)"', 1), veri, build), True),
        ("M11 litofanin render izni geri alindi",
         (index, bolum, veri.replace('arkadan ışıklı render\'ı).\n        ornek_kanit_izni: ["baski", "render"]',
                                     'arkadan ışıklı render\'ı).\n        ornek_kanit_izni: ["baski"]', 1), build), True),
        ("K0 kontrol: yorum eklendi", (index.replace("</body>", "<!-- k0 -->\n</body>", 1), bolum, veri, build), False),
    ]
    taban = kirmizi_sayisi(index, bolum, veri, build)
    for ad, girdi, olmeli in mutantlar:
        n = kirmizi_sayisi(*girdi)
        gecti = (n > taban) if olmeli else (n == taban)
        print(("  ✅ " if gecti else "  ❌ ") + ad + (" -> KIRMIZI yanar" if olmeli else " -> degismez") +
              ("" if gecti else " (kirmizi=%d taban=%d)" % (n, taban)))
        kirmizi += 0 if gecti else 1
    for ad, capa in (("katPanels", capa_kat), ("secenekler", capa_sec), ("liste", capa_liste), ("sepet", capa_sepet)):
        if index.count(capa) != 1:
            print("  ❌ mutant capasi '%s' index.html'de tekil degil (%d) — mutant olu" % (ad, index.count(capa)))
            kirmizi += 1
    print("\nSONUC: " + ("YESIL ✅" if kirmizi == 0 else "KIRMIZI ❌ (%d)" % kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
