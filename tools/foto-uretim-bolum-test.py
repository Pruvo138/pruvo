#!/usr/bin/env python3
"""PRUVO — "Fotoğrafından özel üretim" ana sayfa bölümü KABUL KAPISI (istemci tarafı).

    python3 tools/foto-uretim-bolum-test.py

Okan kararı (5 Eki 2026, aynen): "anasayfada 2 browseren altına kategorilerin üzerine kursun
mobil uyumlu tam sayfayı kaplasın örnek çıktılarda görünsün müşteri abartılı hayallere
kapılmasın". Sunucu tarafı ayrı kapıda (shop/test/foto-uretim.mjs); bu dosya ekranın
SÖZLEŞMESİNİ ölçer:

  Y1 YER      : bölüm kabı iki banner'ın (#bannerRow) DIŞINDA ve ALTINDA, kategori vitrininin
                (#katPanels) ÜSTÜNDE; varsayılan `hidden` (gerçek örnek yoksa görünmez)
  Y2 GÖRÜNÜM  : renderGrid ana sayfa dışı görünümde bölümü gizleyen listeye kabı alır
  Y3 YÜKLEME  : veri dosyası bölümden ÖNCE, ikisi de defer; ikisi de yayın beyaz listesinde
                (build.py SOYULACAK_JS — değer olarak okunur, metin araması değil)
  Y4 DÜRÜSTLÜK: bölüm "önizlemenin 4 renkli yorumu" ifadesini taşır; "3D baskı" demez;
                örnek kaydı üç görseli (foto/önizleme/BASILMIŞ) şart koşar (veri dosyası)
  Y5 SEPET    : ödeme dönüşünde sepeti koruyan oturum anahtarı iki dosyada AYNI dize
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
uygulanır (diske yazılmaz): kap kategorilerin altına taşınır · görünüm listesinden düşer ·
dürüstlük ifadesi silinir · beyaz listeden düşer · oturum anahtarı ayrışır. Her mutant en az
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


def yorumsuz(metin):
    """JS yorumlarini (// satir, /* */ blok) temizle; string literal'lara DOKUNMA.

    Y10 'gerçek fotoğraf' 0 ölçümü bunu kullanır: yasaklı ifade yalnız yorumlarda geçer;
    string'lere veya koda girerse 'kullanici gorecek' sayilir ve kapı kırar.
    """
    out, i, n = [], 0, len(metin)
    while i < n:
        c = metin[i]
        if c == '"' or c == "'":
            quote = c
            out.append(c)
            i += 1
            while i < n and metin[i] != quote:
                if metin[i] == '\\' and i + 1 < n:
                    out.append(metin[i])
                    out.append(metin[i+1])
                    i += 2
                else:
                    out.append(metin[i])
                    i += 1
            if i < n:
                out.append(metin[i])
                i += 1
            continue
        if c == '/' and i + 1 < n and metin[i+1] == '*':
            i += 2
            while i + 1 < n and not (metin[i] == '*' and metin[i+1] == '/'):
                i += 1
            if i + 1 < n:
                i += 2
            else:
                i = n
            continue
        if c == '/' and i + 1 < n and metin[i+1] == '/':
            while i < n and metin[i] != '\n':
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def kontroller(index, bolum, veri, build):
    """[(ad, gecti, ayrinti)] — metin girdileri; disk/ag yok (mutantlar da bunu kullanir)."""
    s = []
    kap = re.search(r'<section\b[^>]*\bid="fotoUretim"[^>]*>', index)
    banner = index.find('id="bannerRow"')
    kat = index.find('id="katPanels"')
    if not kap or banner < 0 or kat < 0:
        s.append(("Y1 kap + banner + kategori vitrini bulundu", False, "kap/banner/katPanels eksik"))
    else:
        # Sayim banner satirinin KENDI <div acilisindan baslar: kap disaridaysa acik == kapali.
        ara = index[index.rfind("<div", 0, banner):kap.start()]
        acik, kapali = len(re.findall(r"<div\b", ara)), len(re.findall(r"</div>", ara))
        s.append(("Y1 kap iki banner'in ALTINDA ve banner satirinin DISINDA",
                  banner < kap.start() and acik == kapali, "div ac/kapa=%d/%d" % (acik, kapali)))
        s.append(("Y1 kap kategori vitrininin USTUNDE", kap.start() < kat, ""))
        s.append(("Y1 kap varsayilan gizli (hidden)", re.search(r"\shidden\b", kap.group(0)) is not None, kap.group(0)))
        s.append(("Y1 tek kap", len(re.findall(r'id="fotoUretim"', index)) == 1, ""))
    liste = re.search(r'\[\s*"katPanels"[^\]]*\]\.forEach', index)
    s.append(("Y2 renderGrid gorunum listesinde fotoUretim",
              bool(liste) and '"fotoUretim"' in liste.group(0), liste.group(0) if liste else "liste yok"))
    sv = index.find('<script src="/foto-uretim-veri.js" defer>')
    sb = index.find('<script src="/foto-uretim.js" defer>')
    se = index.find('<script src="/secenekler.js">')
    s.append(("Y3 veri dosyasi bolumden ONCE, ikisi defer, secenekler.js'ten sonra",
              0 <= se < sv < sb, "secenekler=%d veri=%d bolum=%d" % (se, sv, sb)))
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
    s.append(("Y5 oturum anahtari iki dosyada ayni", OTURUM_ANAHTARI in bolum and
              ('sessionStorage.getItem("%s")' % OTURUM_ANAHTARI) in index, ""))
    s.append(("Y6 bolum innerHTML kullanmaz", "innerHTML" not in bolum, ""))
    uclar = set(re.findall(r'"(/api/[a-z/]+)', bolum))
    beklenen = {"/api/shop/foto/acik", "/api/shop/foto/onizleme", "/api/shop/foto/durum", "/api/shop/baslat"}
    s.append(("Y6 bolum uclari = foto uclari + baslat (aynı köken)",
              beklenen <= uclar and all(u.startswith("/api/shop/") for u in uclar), str(sorted(uclar))))
    harici = sorted(set(re.findall(r"https?://[A-Za-z0-9.-]+", bolum)))
    izinli = {"https://challenges.cloudflare.com", "https://wa.me"}
    s.append(("Y6 harici adres yalniz bot dogrulayici + WhatsApp", set(harici) <= izinli, str(harici)))
    # Y8 PLAKET (BaBa 5 Eki 21:4x(b)): veri dosyasinin `turler` dizisinde plaket + figur VAR (saglayici
    # kolunda IKINCI tur, 24 kategori programi #8); metal gerektiren turler (anahtarlik/magnet) YOK.
    tb = re.search(r"\bturler:\s*\[(.*?)\n\s*\],", veri, re.S)
    kodlar = re.findall(r'\bkod:\s*"([^"]+)"', tb.group(1)) if tb else []
    # 8 Eki: figur saglayici kolunda; metal gerektiren turler SUNULMAZ.
    s.append(("Y8 plaket + figur VAR ve anahtarlik/magnet turu 0",
              "plaket" in kodlar and "figur" in kodlar and
              not any(k in kodlar for k in ("anahtarlik", "magnet")), str(kodlar)))
    eski = [k for k in ("anahtarl", "magnet", "mıknatıs", "miknatis")
            if k in bolum.lower() or k in (tb.group(1).lower() if tb else "")]
    s.append(("Y8 anahtarlik/magnet secenegi ekranda + tur listesinde 0", not eski, ",".join(eski)))
    # Y9 13:5x (Okan 13:5x: tek tur dali kaldirildi — tur secimi GALERIDEN, 24 kucuk resim izgarasi).
    # Ayri radyo grubu yok; tiklanan kart = secim (function galeriSec).
    s.append(("Y9 13:5x tur secimi galeriden (tek tur dali kaldirildi, Okan 13:5x)",
              re.search(r"function galeriSec\(n\)\s*\{", bolum) is not None
              and "galeriSec(n)" in bolum, ""))
    s.append(("Y9 adim cubugu tur sayisina gore 'Ölçü' der",
              'F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"' in bolum, ""))
    # Y10 RENDER ORNEGI (Okan 7 Eki): kanit izni tur kaydinda, izin kontrolu sayacta.
    izinler = dict(re.findall(r'kod:\s*"([a-z]+)",.*?ornek_kanit_izni:\s*(\[[^\]]*\])', veri, re.S))
    s.append(("Y10 kanit izni: plaket [baski,render] · litofan [baski,render] (Okan 7 Eki G1)",
              izinler.get("plaket") == '["baski", "render"]' and izinler.get("litofan") == '["baski", "render"]', str(izinler)))
    s.append(("Y10 sayac izin disi kaniti saymaz (izin kontrolu veri dosyasinda)",
              re.search(r"if \(!k \|\| izin\.indexOf\(k\) < 0\) \{ return false; \}", veri) is not None, ""))
    # Y10 RENDER ORNEGI — 50cb58fe sonrasi: `if (it.kanit === "render") { ... } else {` ESKI dali YOK.
    # Render kartta "önizleme/render" etiketi, lightbox'ta tur kaydinin ornek_notu'su basiliyor;
    # "gerçek fotoğraf" ifadesi (yasakli, hukuk kapisi 13:4x) yorum/string ikisinde de 0.
    bolum_cleaned = yorumsuz(bolum)
    notlar = dict(re.findall(r'kod:\s*"([a-z]+)",.*?ornek_notu:\s*"([^"]*)"', veri, re.S))
    s.append(("Y10 render kartinda 'önizleme/render' etiketi VAR (galeri)",
              '"önizleme/render"' in bolum_cleaned, ""))
    s.append(("Y10 lightbox ornek_notu tur kaydindan (it.tur.ornek_notu) · bolumde sabit 'kabartmalı' cumlesi 0",
              "it.tur.ornek_notu" in bolum_cleaned and "kabartmalı" not in bolum, ""))
    s.append(("Y10 plaket ornek_notu = karar cumlesi AYNEN", notlar.get("plaket") == RENDER_CUMLE, str(notlar.get("plaket"))))
    s.append(("Y11 litofan ornek_notu = litofan cumlesi AYNEN ('kabartmalı' 0)",
              notlar.get("litofan") == LITOFAN_CUMLE, str(notlar.get("litofan"))))
    s.append(("Y10 'gerçek fotoğraf' metni 0 (yorum haric, kodda yok)",
              "gerçek fotoğraf" not in bolum_cleaned, ""))
    # Y12 SERIT: ol etiketi numara basilmasin (375 px mimar olcumunde 1./2. gorunuyordu).
    s.append(("Y12 serit kuralinda list-style: none VAR (ol numara basilmasin)",
              re.search(r"\.foto-uretim-serit\{[^}]*list-style\s*:\s*none", bolum) is not None, ""))
    # Y13 TEK YUKLEME ALANI (Okan 7 Eki 21:5x): ustteki "Foto ekle" kutusu tek dosya girdisi; tiklama
    # ve birakma ayni yoldan (dosyaKoy); tur + 15 MB denetimi orada. Davranis: foto-uretim.mjs S5.
    # 8 Eki 00:3x h.1(e): ses form-parametresinin audio/* girdisi AYNI dosyada olabilir — sayaç
    # FOTOĞRAF yükleme kutusunun TEK'liğini tutar (`inp.id = "foto-dosya"`); ses/konum/tarih HARİÇ.
    girdi = len(re.findall(r'inp\.id\s*=\s*"foto-dosya"', bolum))
    s.append(("Y13a kaynakta dosya girdisi (type=file) TAM 1 yerde olusturulur", girdi == 1, "adet=%d" % girdi))
    s.append(("Y13a formdaki eski 'Fotoğraf (JPEG' etiketi 0", "Fotoğraf (JPEG" not in bolum, ""))
    s.append(("Y13a dosya girdisinde capture YOK (mobilde galeri kapanmaz)", "capture" not in bolum, ""))
    ch = re.search(r'inp\.id = "foto-dosya";\s*inp\.addEventListener\("change", function \(e\) \{(.*?)\n    \}\);', bolum, re.S)
    dr = re.search(r'kutu\.addEventListener\("drop", function \(e\) \{(.*?)\n    \}\);', bolum, re.S)
    govde = (ch.group(1) if ch else "") + (dr.group(1) if dr else "")
    s.append(("Y13b change ve drop isleyicisi AYNI fonksiyonu (dosyaKoy) cagirir, S.dosya'ya kendi yazmaz",
              bool(ch and dr) and "dosyaKoy(" in ch.group(1) and "dosyaKoy(" in dr.group(1) and "S.dosya" not in govde,
              "change=%s drop=%s" % (bool(ch), bool(dr))))
    dk = re.search(r"function dosyaKoy\(f\) \{(.*?)\n  \}\n", bolum, re.S)
    g = dk.group(1) if dk else ""
    s.append(("Y13c 15 MB ve tur denetimi dosyaKoy icinde",
              "f.size > MAKS_DOSYA_BAYT" in g and r"/^image\/(jpeg|png|webp)$/" in g and '"image/svg+xml"' in g, ""))
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
    kap = re.search(r'\s*<!-- FOTOĞRAFINDAN ÖZEL ÜRETİM.*?</section>\n', index, re.S)
    mutantlar = []
    if kap:
        tasinmis = index.replace(kap.group(0), "\n")
        tasinmis = tasinmis.replace('<div id="katPanels" class="kat-panels"></div>',
                                    '<div id="katPanels" class="kat-panels"></div>' + kap.group(0), 1)
        mutantlar.append(("M1 kap kategorilerin ALTINA tasindi", (tasinmis, bolum, veri, build), True))
    mutantlar += [
        ("M2 gorunum listesinden dustu", (index.replace(', "fotoUretim"]', "]"), bolum, veri, build), True),
        ("M3 durustluk ifadesi silindi", (index, bolum, veri.replace(DURUSTLUK, "önizlemenin yorumu"), build), True),
        ("M14 bolum sabit durustluk metnine dondu",
         (index, bolum.replace("t && t.durustluk ? t.durustluk : \"\"", "\"Ürün en çok 4 renkle kabartma olarak üretilir\""), veri, build), True),
        ("M4 beyaz listeden dustu", (index, bolum, veri, build.replace('"foto-uretim.js", ', "", 1).replace(', "foto-uretim.js"', "", 1)), True),
        ("M5 oturum anahtari ayristi", (index, bolum.replace(OTURUM_ANAHTARI, "pruvo_foto_sip"), veri, build), True),
        ("M6 anahtarlik tur listesine geri eklendi",
         (index, bolum, veri.replace('kod: "plaket",', 'kod: "plaket",\n      },\n      {\n        kod: "anahtarlik",', 1), build), True),
        ("M7 galeri tur secici kaldirildi (tek tur dali yerine)",
         (index, re.sub(r"\bgaleriSec\b", "galeriSecYOK", bolum), veri, build), True),
        ("M8 izin kontrolu silindi",
         (index, bolum, veri.replace("if (!k || izin.indexOf(k) < 0) { return false; }", "if (!k) { return false; }", 1), build), True),
        ("M9 abarti cumlesi degisti", (index, bolum, veri.replace("kabartmalı hâlidir, birebir aynısı değildir.", "kabartmalı hâlidir.", 1), build), True),
        ("M12 litofan cumlesi plaketinkiyle degisti", (index, bolum, veri.replace(LITOFAN_CUMLE, RENDER_CUMLE, 1), build), True),
        ("M13 bolum sabit cumleye dondu",
         (index, bolum.replace("it.tur.ornek_notu", '"' + RENDER_CUMLE + '"', 1), veri, build), True),
        ("M10 render etiketi 'gerçek fotoğraf' oldu",
         (index, bolum.replace('"önizleme/render"', '"gerçek fotoğraf"'), veri, build), True),
        ("M11 litofanin render izni geri alindi",
         (index, bolum, veri.replace('arkadan ışıklı render\'ı).\n        ornek_kanit_izni: ["baski", "render"]',
                                     'arkadan ışıklı render\'ı).\n        ornek_kanit_izni: ["baski"]', 1), build), True),
        ("K0 kontrol: yorum eklendi", (index.replace("</body>", "<!-- k0 -->\n</body>", 1), bolum, veri, build), False),
        ("M15 serit kuralindan list-style: none kaldirildi",
         (index, bolum.replace(".foto-uretim-serit{list-style:none;", ".foto-uretim-serit{", 1), veri, build), True),
    ]
    # Y13 mutantlari: capa tutmazsa (metin degismezse) mutant KIRMIZI sayilir — sessizce gecmez.
    def bm(eski, yeni):
        return bolum.replace(eski, yeni, 1) if eski in bolum else None
    y13 = [
        ("M16 ikinci dosya girdisi eklendi",
         # 8 Eki 00:3x h.1(e): Y13a artık `inp.id = "foto-dosya"` sayısını ölçer; ikinci FOTO
         # yükleme kutusu simülasyonu aynı sayacı 2 yapar ve kapıyı kırar.
         bm('inp.id = "foto-dosya";', 'inp.id = "foto-dosya";\n    var ikinci = el("input"); ikinci.id = "foto-dosya";')),
        ("M17 drop isleyicisi ayri yola cekildi",
         bm("      dosyaKoy(fl && fl[0] ? fl[0] : null);", "      S.dosya = fl && fl[0] ? fl[0] : null; guncelleS1Buton();")),
        ("M18 15 MB denetimi dosyaKoy'dan cikti",
         bm("      else if (f.size > MAKS_DOSYA_BAYT) hata = ", "      else if (false) hata = ")),
        ("M19 tur denetimi gevsedi (her image/*)", bm(r"/^image\/(jpeg|png|webp)$/.test(tip)", r"/^image\//.test(tip)")),
        ("M20 girdiye capture eklendi",
         bm('    inp.id = "foto-dosya";', '    inp.id = "foto-dosya";\n    inp.setAttribute("capture", "environment");')),
        ("M21 formdaki eski etiket geri geldi",
         bm("    cizUretimNotu();\n  }", '    S.alanDosya.appendChild(el("label", null, "Fotoğraf (JPEG, PNG veya WEBP — en çok 15 MB)"));\n    cizUretimNotu();\n  }')),
    ]
    for ad, mb in y13:
        if mb is None:
            print("  ❌ " + ad + " — capa bulunamadi (mutant kurulamadi)")
            kirmizi += 1
        else:
            mutantlar.append((ad, (index, mb, veri, build), True))
    taban = kirmizi_sayisi(index, bolum, veri, build)
    for ad, girdi, olmeli in mutantlar:
        n = kirmizi_sayisi(*girdi)
        gecti = (n > taban) if olmeli else (n == taban)
        print(("  ✅ " if gecti else "  ❌ ") + ad + (" -> KIRMIZI yanar" if olmeli else " -> degismez") +
              ("" if gecti else " (kirmizi=%d taban=%d)" % (n, taban)))
        kirmizi += 0 if gecti else 1
    if not kap:
        print("  ❌ M1 capa (kap yorumu + section) bulunamadi")
        kirmizi += 1
    print("\nSONUC: " + ("YESIL ✅" if kirmizi == 0 else "KIRMIZI ❌ (%d)" % kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
