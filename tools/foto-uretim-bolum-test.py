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
  Y8 PLAKET   : veri dosyasında sunulan tür TEK (plaket); anahtarlık/magnet ekranda 0
                (BaBa 5 Eki 21:4x(b) — "yalnız plastik üretiyoruz")
  Y9 TEK TÜR  : tek türde tür grubu gizlenir, adım çubuğu "Ölçü" der (DAVRANIŞ ölçümü sahte
                DOM'da: shop/test/foto-uretim.mjs S bölümü; bu dosya sözleşmeyi tutar)

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
    s.append(("Y4 bolum durustluk ifadesini tasir", DURUSTLUK in bolum, ""))
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
    # Y8 PLAKET (BaBa 5 Eki 21:4x(b)): veri dosyasinin `turler` dizisinde TEK tur = plaket.
    tb = re.search(r"\bturler:\s*\[(.*?)\n\s*\],", veri, re.S)
    kodlar = re.findall(r'\bkod:\s*"([^"]+)"', tb.group(1)) if tb else []
    s.append(("Y8 sunulan tur sayisi 1 ve kodu plaket", kodlar == ["plaket"], str(kodlar)))
    eski = [k for k in ("anahtarl", "magnet", "mıknatıs", "miknatis")
            if k in bolum.lower() or k in (tb.group(1).lower() if tb else "")]
    s.append(("Y8 anahtarlik/magnet secenegi ekranda + tur listesinde 0", not eski, ",".join(eski)))
    # Y9 TEK TUR: tur secimi cizilmez + adim cubugu "Olcu" der (davranis: foto-uretim.mjs S).
    s.append(("Y9 tek turde tur grubu gizlenir ve radyo cizilmeden donulur",
              re.search(r"if \(S\.acikVeri\.turler\.length === 1\) \{[^}]*S\.alanTur\.hidden = true;\s*return;", bolum)
              is not None, ""))
    s.append(("Y9 adim cubugu tur sayisina gore 'Ölçü' der",
              'F.turler.length > 1 ? "Tür ve ölçü" : "Ölçü"' in bolum, ""))
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
        ("M3 durustluk ifadesi silindi", (index, bolum.replace(DURUSTLUK, "önizlemenin yorumu"), veri, build), True),
        ("M4 beyaz listeden dustu", (index, bolum, veri, build.replace('"foto-uretim.js", ', "", 1).replace(', "foto-uretim.js"', "", 1)), True),
        ("M5 oturum anahtari ayristi", (index, bolum.replace(OTURUM_ANAHTARI, "pruvo_foto_sip"), veri, build), True),
        ("M6 anahtarlik tur listesine geri eklendi",
         (index, bolum, veri.replace('kod: "plaket",', 'kod: "plaket",\n      },\n      {\n        kod: "anahtarlik",', 1), build), True),
        ("M7 tek tur dali silindi",
         (index, re.sub(r"if \(S\.acikVeri\.turler\.length === 1\) \{[^}]*\}\n", "", bolum, count=1), veri, build), True),
        ("K0 kontrol: yorum eklendi", (index.replace("</body>", "<!-- k0 -->\n</body>", 1), bolum, veri, build), False),
    ]
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
