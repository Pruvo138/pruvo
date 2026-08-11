#!/usr/bin/env python3
"""GA4 OLAY KAPISI — MUTASYON SURUCUSU (kanit repoda durur, anlatiya guvenilmez).

tools/ga4-olay-kapisi.py'nin GERCEKTEN olcup olcmedigini kanitlar: her mutant kaynagi
tek bir eksende bozar, kapiyi kosar ve KIRMIZI bekler. Kontrol mutanti (yalniz yorum
metni) YESIL beklenir — batarya "her seye kirmizi yanan" bir alarm degil.

🔴 Kabul: her oldurucu mutant TEK BASINA kirmizi + kontrol mutanti YESIL. Cikis kodu
tek basina yeterli DEGIL; basilan MUTANT=n/n sayisi da okunur ([[beyan-edilmis-survivor]]).

Yazdigi her seyi finally ile GERI ALIR; __pycache__ her kosumda silinir ve alt surec
-B ile kosar (ayni saniyede ayni boyutta mutasyon bayat bytecode ile kosmasin
[[mutasyon-bytecode-onbellegi]]).

KOSUM: python3 tools/ga4-olay-mutasyon.py
"""
import hashlib
import os
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "ga4-olay-kapisi.py")

# (ad, dosya, eski, yeni, beklenen_kirmizi)
MUTANTLAR = [
    ("M1 urun goruntuleme olayi sokulur",
     "tools/build.py",
     'if(typeof window.pruvoGA4Track==="function"){ window.pruvoGA4Track("view_item", ',
     'if(false){ window.pruvoGA4TrackYok("view_item", ', True),

    ("M2 sepete ekleme olayi sokulur",
     "tools/build.py",
     'if(typeof window.pruvoGA4Track === "function"){{ window.pruvoGA4Track("add_to_cart", gAtcVeri); }}',
     '/* sokuldu */', True),

    ("M3 odemeye baslama olayi sokulur",
     "index.html",
     'if(typeof window.pruvoGA4Track === "function"){ window.pruvoGA4Track("begin_checkout", gIcVeri); }',
     '/* sokuldu */', True),

    ("M4 gonderici TEK kopyadan (ana sayfa) dusurulur",
     "index.html",
     "  window.pruvoGA4Track = function(olay, veri){",
     "  window.pruvoGA4TrackBaskaAd = function(olay, veri){", True),

    ("M5 satin alma beyaz listeye eklenir (cift sayim yolu acilir)",
     "tools/build.py",
     "window.PRUVO_GA4_OLAYLARI = ['view_item','add_to_cart','begin_checkout'];",
     "window.PRUVO_GA4_OLAYLARI = ['view_item','add_to_cart','begin_checkout','purchase'];",
     True),

    ("M6 riza kapisi gondericiden kaldirilir",
     "index.html",
     "    try { if(localStorage.getItem('pruvo_onay_analitik') !== 'kabul'){ return; } } catch(e){ return; }\n"
     "    var a = window.PRUVO_GA4_OLAYLARI, i;",
     "    var a = window.PRUVO_GA4_OLAYLARI, i;", True),

    ("M7 kalem kimligi katalog kimliginden KOPARILIR",
     "tools/build.py",
     'gvi_kalem = {"item_id": feed_id(pid), "item_name": baslik,',
     'gvi_kalem = {"item_id": "sabit-kimlik", "item_name": baslik,', True),

    ("M8 sunucu tarafi satin alma olayi kaybolur",
     "shop/src/olcum.js",
     'events: [{ name: "purchase", params: params }] };',
     'events: [{ name: "satin_alma", params: params }] };', True),

    ("M9 olay parametresine musteri alani sizar",
     "index.html",
     "      var gIcVeri = { currency: \"TRY\", items: gIcKalemler };",
     "      var gIcVeri = { currency: \"TRY\", items: gIcKalemler, musteri_adi: \"Ahmet Yilmaz\" };",
     True),

    ("M10 GA4 ikizi OLMAYAN yeni bir Meta huni noktasi eklenir",
     "index.html",
     '      if(typeof window.pruvoMetaTrack === "function"){ window.pruvoMetaTrack("InitiateCheckout", icVeri); }',
     '      if(typeof window.pruvoMetaTrack === "function"){ window.pruvoMetaTrack("InitiateCheckout", icVeri); }\n'
     '      if(typeof window.pruvoMetaTrack === "function"){ window.pruvoMetaTrack("AddPaymentInfo", icVeri); }',
     True),

    ("K1 KONTROL yalniz yorum metni degisir (davranis AYNI)",
     "index.html",
     "         Müşteri alanları (ad/telefon/e-posta/adres) buraya GİRMEZ. */",
     "         Müşteri alanları hiçbir koşulda buraya GİRMEZ. */", False),
]


def kapi_kos():
    kok_cache = os.path.join(TOOLS, "__pycache__")
    shutil.rmtree(kok_cache, ignore_errors=True)
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-B", KAPI], cwd=ROOT, env=ortam,
                       capture_output=True, text=True, timeout=1800)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    print("=" * 70)
    print("GA4 OLAY KAPISI — MUTASYON BATARYASI")
    print("=" * 70)

    # Dokunulacak her dosyanin ONCEKI ozeti: batarya bitince BIREBIR geri gelmis mi
    # AYRICA olculur. "finally ile geri aliyorum" bir BEYANDIR; kanit ozet esitligidir
    # ([["olculdu" diyen hukum kaniti]]). Geri gelmediyse batarya KIRMIZI biter.
    ozetler = {}
    for _, rel, _, _, _ in MUTANTLAR:
        yol = os.path.join(ROOT, rel)
        with open(yol, "rb") as f:
            ozetler[rel] = hashlib.sha256(f.read()).hexdigest()

    rc, cikti = kapi_kos()
    if rc != 0:
        print("TABAN KIRMIZI/OLCULEMEDI (rc=%d) — mutasyon anlamsiz. Son satirlar:" % rc)
        print("\n".join(cikti.strip().splitlines()[-12:]))
        return 3
    print("  taban: kapi YESIL (rc=0) — mutasyon baslayabilir\n")

    oldurucu = [m for m in MUTANTLAR if m[4]]
    dusen, hatali = 0, []
    for ad, rel, eski, yeni, kirmizi_bekle in MUTANTLAR:
        yol = os.path.join(ROOT, rel)
        with open(yol, encoding="utf-8") as f:
            asil = f.read()
        if asil.count(eski) < 1:
            hatali.append("%s — capa bulunamadi (%s)" % (ad, rel))
            print("  ⚠️  %s -> CAPA YOK (%s)" % (ad, rel))
            continue
        try:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(asil.replace(eski, yeni, 1))
            rc, _ = kapi_kos()
        finally:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(asil)
        if kirmizi_bekle:
            if rc != 0:
                dusen += 1
                print("  ok  %s -> KIRMIZI (rc=%d)" % (ad, rc))
            else:
                hatali.append("%s — mutant SAG KALDI (kapi yesil)" % ad)
                print("  ❌  %s -> SAG KALDI" % ad)
        else:
            if rc == 0:
                print("  ok  %s -> YESIL (kontrol)" % ad)
            else:
                hatali.append("%s — KONTROL mutanti kirmizi yandi (kapi asiri hassas)" % ad)
                print("  ❌  %s -> KONTROL KIRMIZI (rc=%d)" % (ad, rc))

    shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)
    for rel, beklenen in sorted(ozetler.items()):
        with open(os.path.join(ROOT, rel), "rb") as f:
            simdi = hashlib.sha256(f.read()).hexdigest()
        if simdi != beklenen:
            hatali.append("%s BIREBIR geri gelmedi (mutant diskte KALDI)" % rel)
            print("  ❌  GERI ALMA: %s ozet degisti" % rel)
    print("  ok  geri alma: %d dosya bayt-birebir eski haline dondu" % len(ozetler))
    print("-" * 70)
    print("MUTANT=%d/%d  KONTROL_MUTANT=%s"
          % (dusen, len(oldurucu),
             "YESIL" if not any("KONTROL" in h for h in hatali) else "KIRMIZI"))
    if hatali:
        print("SONUC: KIRMIZI ❌")
        for h in hatali:
            print("   · " + h)
        return 1
    print("SONUC: YESIL ✅ — oldurucu mutantlarin hepsi TEK BASINA kirmizi, kontrol YESIL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
