#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Landing / içerik sayfası JSON-LD kabul kapısı.

🔴 NEDEN VAR: 6 Eyl 2026 GEO denetimi 5 landing örneğinin 5'inde de JSON-LD
bulamadı. 7 Eyl'de sayıyla ölçüldü — `render_content_page` ile basılan **476**
sayfanın **432**'sinde JSON-LD YOKTU (44'ünde elle yazılmış blok vardı).
Üretici `tools/landing_jsonld.py`'ye yazıldı; bu kapı üreticinin fiilen
CANLI ÜRETİM YOLUNDAN geçtiğini ölçer.

🔴 ÇAPA GERÇEK ÜRETİM YOLUDUR, KOPYASI DEĞİL: kapı `sayfalar.CONTENT_PAGES`'i
okuyup HER kayıt için `build.render_content_page(...)` fonksiyonunu ÇAĞIRIR ve
dönen HTML'i ölçer. Kendi HTML'ini kurup ölçmez — o, kapının kendi kopyasını
doğrulaması olurdu ve `render_content_page`'ten çağrı düşse bile yeşil yanardı.

ÜÇ KOL (üçü de bağımsız KIRMIZI yakabilir):
  K1 KAPSAM  — her sayfada EN AZ BİR JSON-LD bloğu var mı? (kapsam 476/476)
  K2 GEÇERLİ — her blok JSON olarak ayrışıyor ve `landing_jsonld.dogrula()`
               şema kurallarını geçiyor mu? (zorunlu alan / @context / @type /
               headline tavanı / url sayfayı gösteriyor mu)
  K3 İKİZ    — aynı sayfada AYNI `@type`'tan iki blok var mı? (üretici gövdedeki
               elle yazılmış bloğu görmezse ikiz tanım doğar; K1+K2 buna KÖRDÜR
               — ikiz sayfada da kapsam dolu ve her iki blok da geçerlidir)

Kullanım:
  python3 tools/landing-jsonld-kapisi.py              → ölçüm, rc=0 YEŞİL / rc=1 KIRMIZI
  python3 tools/landing-jsonld-kapisi.py --mutasyon   → mutant bataryası (izole kopya)
"""
import json
import os
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARACLAR = os.path.join(KOK, "tools")

# TABAN (7 Eyl 2026, onarımdan ÖNCE ölçüldü): 476 sayfanın 44'ünde JSON-LD vardı.
# Kapsam bu sayının ALTINA düşerse sınıf-geneli gerileme olmuştur.
TABAN_ELLE_YAZILMIS = 44


def _olc():
    """Üretim yolunu koşturur; (rapor sözlüğü) döner."""
    sys.dont_write_bytecode = True
    if ARACLAR not in sys.path:
        sys.path.insert(0, ARACLAR)
    import sayfalar
    import build
    import landing_jsonld

    kapsamsiz = []       # K1
    gecersiz = []        # K2
    ikizler = []         # K3
    uretilen = 0         # üreticinin bastığı sayfa
    elle = 0             # gövdesinde elle yazılmış blok taşıyan sayfa

    for slug, baslik, meta, fn in sayfalar.CONTENT_PAGES:
        govde = fn()
        # ÜRETİM YOLU: gerçek fonksiyon çağrılır.
        html = build.render_content_page(slug, baslik, meta, govde)
        bloklar = landing_jsonld.LD_RE.findall(html)
        if not bloklar:
            kapsamsiz.append(slug)
            continue
        if landing_jsonld.LD_RE.search(govde):
            elle += 1
        else:
            uretilen += 1

        beklenen = landing_jsonld.sayfa_url(build.SITE, slug)
        tipler = []
        for ham in bloklar:
            try:
                obj = json.loads(ham)
            except Exception as e:
                gecersiz.append((slug, "JSON ayristirilamadi: %s" % str(e)[:70]))
                tipler.append(None)
                continue
            tipler.append(obj.get("@type") if isinstance(obj, dict) else None)
            for ihlal in landing_jsonld.dogrula(obj, beklenen):
                gecersiz.append((slug, ihlal))
        dolu = [t for t in tipler if t]
        if len(set(dolu)) != len(dolu):
            ikizler.append((slug, tipler))

    return {
        "toplam": len(sayfalar.CONTENT_PAGES),
        "kapsamsiz": kapsamsiz,
        "gecersiz": gecersiz,
        "ikizler": ikizler,
        "uretilen": uretilen,
        "elle": elle,
    }


def _rapor_bas(r):
    kapsam = r["toplam"] - len(r["kapsamsiz"])
    print("landing JSON-LD kapisi — TOPLAM SAYFA: %d" % r["toplam"])
    print("  K1 KAPSAM  : %d/%d sayfada JSON-LD VAR (uretilen %d + elle yazilmis %d)"
          % (kapsam, r["toplam"], r["uretilen"], r["elle"]))
    print("  K2 GECERLI : %d sema ihlali" % len(r["gecersiz"]))
    print("  K3 IKIZ    : %d sayfada ayni @type'tan iki blok" % len(r["ikizler"]))
    for s in r["kapsamsiz"][:10]:
        print("     KAPSAMSIZ: %s" % s)
    if len(r["kapsamsiz"]) > 10:
        print("     ... +%d sayfa daha" % (len(r["kapsamsiz"]) - 10))
    for s, i in r["gecersiz"][:10]:
        print("     GECERSIZ : %s — %s" % (s, i))
    if len(r["gecersiz"]) > 10:
        print("     ... +%d ihlal daha" % (len(r["gecersiz"]) - 10))
    for s, t in r["ikizler"][:10]:
        print("     IKIZ     : %s — %s" % (s, t))
    if len(r["ikizler"]) > 10:
        print("     ... +%d sayfa daha" % (len(r["ikizler"]) - 10))


def olc_ve_hukum():
    r = _olc()
    _rapor_bas(r)
    kirmizi = []
    if r["kapsamsiz"]:
        kirmizi.append("K1: %d sayfa JSON-LD'siz" % len(r["kapsamsiz"]))
    if r["gecersiz"]:
        kirmizi.append("K2: %d sema ihlali" % len(r["gecersiz"]))
    if r["ikizler"]:
        kirmizi.append("K3: %d sayfada ikiz tanim" % len(r["ikizler"]))
    # SINIF-GENELİ GERİLEME: elle yazılmış bloklar sessizce düşerse K1/K2/K3
    # yeşil kalır (üretici boşluğu doldurur) ama içerik KAYBOLMUŞ olur.
    if r["elle"] < TABAN_ELLE_YAZILMIS:
        kirmizi.append("GERILEME: elle yazilmis blok tasiyan sayfa %d < taban %d"
                       % (r["elle"], TABAN_ELLE_YAZILMIS))
    if kirmizi:
        print("\nKIRMIZI — " + " · ".join(kirmizi))
        return 1
    print("\nYESIL — %d/%d sayfada gecerli JSON-LD, ikiz 0" % (r["toplam"], r["toplam"]))
    return 0


# --------------------------------------------------------------- mutasyon
# 🔴 MUTANT İZOLE GÖLGE AĞAÇTA KOŞAR: canlı `tools/landing_jsonld.py` HİÇ değişmez.
#
# 🔴 NEDEN PYTHONPATH YETMEZ (7 Eyl'de ölçüldü — ilk denemede 4 mutantın DÖRDÜ DE
# HAYATTA kaldı, yani mutant koda hiç ULAŞMADI): `build.py:33` kendi import'undan
# ÖNCE `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` yapar.
# Yani build.py hangi dizinden yüklendiyse O dizini sys.path'in BAŞINA koyar ve
# `import landing_jsonld` daima ORADAN çözülür. PYTHONPATH de, kapının kendi
# `sys.path.insert`'i de bunu yenemez.
#
# ÇÖZÜM: geçici dizinde SEMBOLİK BAĞLARDAN bir gölge depo kurulur —
#   <gecici>/<kok girdileri>  -> gerçeğe symlink (tools HARİÇ)
#   <gecici>/tools/<girdiler> -> gerçeğe symlink (landing_jsonld.py HARİÇ)
#   <gecici>/tools/landing_jsonld.py -> MUTASYONLU GERÇEK DOSYA
# Kapı bu gölge ağaçtan koşturulur; build.py `abspath(__file__)` ile gölge
# tools'u sys.path[0]'a koyar (abspath symlink ÇÖZMEZ) ve mutantı yükler.
# Tek bayt bile canlı ağaca yazılmaz; PYTHONDONTWRITEBYTECODE=1 ile .pyc izi de
# bırakılmaz (Okan disk kuralı).
MUTANTLAR = [
    ("M1-uretici-susturuldu",
     "def blok(slug, baslik, meta, govde_html, site=\"https://pruvo3d.com\"):",
     "def blok(slug, baslik, meta, govde_html, site=\"https://pruvo3d.com\"):\n    return \"\"",
     "K1"),
    ("M2-ikiz-korumasi-kaldirildi",
     "    if govde_html and LD_RE.search(govde_html):\n        return \"\"",
     "    if False:\n        return \"\"",
     "K3"),
    ("M3-description-alani-dusuruldu",
     '        "description": meta,\n',
     "",
     "K2"),
    ("M4-url-yanlis-sayfayi-gosteriyor",
     '    return site + "/" + slug + "/"',
     '    return site + "/yanlis-sayfa/"',
     "K2"),
]

KONTROL = [
    ("K-yorum-eklendi", "import json", "import json  # kontrol mutanti (davranis degismez)"),
]


def _golge_kur(gecici, mutant_kaynak):
    """Symlink'lerden gölge depo kurar; mutasyonlu landing_jsonld.py GERÇEK dosyadır.

    Döner: gölge ağaçtaki kapı betiğinin yolu.
    """
    golge_tools = os.path.join(gecici, "tools")
    os.mkdir(golge_tools)
    for ad in os.listdir(KOK):
        if ad == "tools":
            continue
        os.symlink(os.path.join(KOK, ad), os.path.join(gecici, ad))
    for ad in os.listdir(ARACLAR):
        if ad in ("landing_jsonld.py", "__pycache__"):
            continue
        os.symlink(os.path.join(ARACLAR, ad), os.path.join(golge_tools, ad))
    with open(os.path.join(golge_tools, "landing_jsonld.py"), "w",
              encoding="utf-8") as f:
        f.write(mutant_kaynak)
    return os.path.join(golge_tools, os.path.basename(os.path.abspath(__file__)))


def _mutant_kos(kaynak_metin, etiket):
    """Mutasyonlu kaynağı izole gölge ağaca kurar, kapıyı ALT SÜREÇTE koşar."""
    with tempfile.TemporaryDirectory(prefix="landing-jsonld-mutant-") as gecici:
        kapi = _golge_kur(gecici, kaynak_metin)
        ortam = dict(os.environ)
        ortam["PYTHONDONTWRITEBYTECODE"] = "1"
        sonuc = subprocess.run([sys.executable, kapi],
                               env=ortam, capture_output=True, text=True)
        return sonuc.returncode, sonuc.stdout + sonuc.stderr


def mutasyon_bataryasi():
    canli = os.path.join(ARACLAR, "landing_jsonld.py")
    with open(canli, "r", encoding="utf-8") as f:
        ham = f.read()
    print("mutasyon bataryasi — canli kaynak: %s (%d bayt, DEGISTIRILMEZ)"
          % (canli, len(ham)))

    hata = 0
    for ad, capa, yeni, beklenen_kol in MUTANTLAR:
        if capa not in ham:
            print("  %-34s CAPA YOK — mutant kaynaga ULASMADI (KIRMIZI)" % ad)
            hata += 1
            continue
        if ham.count(capa) != 1:
            print("  %-34s CAPA %d KEZ — belirsiz (KIRMIZI)" % (ad, ham.count(capa)))
            hata += 1
            continue
        rc, cikti = _mutant_kos(ham.replace(capa, yeni, 1), ad)
        kol_yandi = ("KIRMIZI" in cikti) and (beklenen_kol + ":" in cikti)
        if rc != 0 and kol_yandi:
            print("  %-34s OLDU (rc=%d, %s kolu yandi)" % (ad, rc, beklenen_kol))
        else:
            print("  %-34s HAYATTA (rc=%d, beklenen kol %s yanmadi) — KIRMIZI"
                  % (ad, rc, beklenen_kol))
            print("      cikti: %s" % cikti.strip().replace("\n", " | ")[:300])
            hata += 1

    for ad, capa, yeni in KONTROL:
        if capa not in ham:
            print("  %-34s CAPA YOK (KIRMIZI)" % ad)
            hata += 1
            continue
        rc, _ = _mutant_kos(ham.replace(capa, yeni, 1), ad)
        if rc == 0:
            print("  %-34s YESIL kaldi (kontrol dogru)" % ad)
        else:
            print("  %-34s KIRMIZI yandi — kapi ASIRI HASSAS" % ad)
            hata += 1

    # Canlı kaynak gerçekten dokunulmamış mı?
    with open(canli, "r", encoding="utf-8") as f:
        if f.read() != ham:
            print("  CANLI KAYNAK DEGISTI — mutasyon izole degil (KIRMIZI)")
            hata += 1
        else:
            print("  canli kaynak bayt-ayni (mutasyon izole)")

    print("\n%s — %d/%d mutant + %d kontrol"
          % ("KIRMIZI" if hata else "YESIL", len(MUTANTLAR) - hata if hata <= len(MUTANTLAR) else 0,
             len(MUTANTLAR), len(KONTROL)))
    return 1 if hata else 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(mutasyon_bataryasi())
    sys.exit(olc_ve_hukum())
