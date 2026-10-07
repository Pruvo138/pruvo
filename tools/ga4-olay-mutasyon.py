#!/usr/bin/env python3
"""GA4 OLAY KAPISI — MUTASYON SURUCUSU (kanit repoda durur, anlatiya guvenilmez).

tools/ga4-olay-kapisi.py'nin GERCEKTEN olcup olcmedigini kanitlar: her mutant kaynagi
tek bir eksende bozar, kapiyi kosar ve KIRMIZI bekler. Kontrol mutanti (yalniz yorum
metni) YESIL beklenir — batarya "her seye kirmizi yanan" bir alarm degil.

🔴 Kabul: her oldurucu mutant TEK BASINA kirmizi + kontrol mutanti YESIL. Cikis kodu
tek basina yeterli DEGIL; basilan MUTANT=n/n sayisi da okunur ([[beyan-edilmis-survivor]]).

🔴 IZOLE KOPYA (7 Eki 2026): eskiden mutant CANLI `tools/build.py`, `index.html`,
`shop/src/olcum.js`'e yazilir, geri alma finally'ye birakilirdi. Surec SIGKILL / oturum
olumuyle dusunce finally KOSMADI ve canli agacta `olcum.js` icinde
`purchase→satin_alma` mutant artigi kaldi. Artik her mutant `tempfile.mkdtemp()`
altinda KENDI kopya kokunde kurulur (`kopya_kok` + hedeflerin GERCEK kopyasi), kapi
KOPYADAN kosar (ROOT'u kendi __file__'indan turetir) ve kopya silinir. Canli agaca
tek bayt yazilmaz; olum aninda geride yalniz gecici dizin kalir. Olcen kol:
tools/ga4-olay-mutasyon-izole-test.py (SIGKILL sonrasi canli ozet esitligi).
Alt surec -B ile kosar, kopya `__pycache__` tasimaz [[mutasyon-bytecode-onbellegi]].

KOSUM: python3 tools/ga4-olay-mutasyon.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "ga4-olay-kapisi.py"
sys.path.insert(0, TOOLS)

from mutasyon_kopya import gercek_dosya, kopya_kok, kopyada_mi  # noqa: E402

# IKI BICIM (9 Eyl 2026, K388):
#   klasik  : (ad, dosya, eski, yeni, beklenen_kirmizi)
#   cok-yerli: (ad, [(dosya, eski, yeni), ...], beklenen_kirmizi)
# Cok-yerli bicim, ayni iddianin BIRDEN COK uretecte tasindigi hallerde gerekir:
# tek uretecte sokulen bir cagri yeri, oteki uretecler onu hala tasidigi icin
# kapiyi kirmiziya YAKMAZ — o mutant "sag kaldi" diye degil, EKSIK KURULDUGU icin
# kacar ([[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]).
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

    # 🔴 CAPA (9 Eyl 2026): beyaz liste satiri `generate_lead` ile BUYUDU (K388).
    # Eski capa satirin ESKI halini tasidigi icin M5 "CAPA YOK" verip SESSIZCE
    # dusmustu — mutant olmedi, KACTI. Capa artik satirin KAPANISINA nisanli:
    # yeni bir olay eklendiginde de yerinde kalir.
    ("M5 satin alma beyaz listeye eklenir (cift sayim yolu acilir)",
     "tools/build.py",
     "'generate_lead'];",
     "'generate_lead','purchase'];",
     True),

    # --- K388 yeni guard: beyaz liste == huni ayagi ∪ BEYAN EDILEN GA4-only kume ---
    ("M11 BEYAN EDILMEMIS bir olay beyaz listeye eklenir (kapsam genislemesi)",
     "tools/build.py",
     "'generate_lead'];",
     "'generate_lead','beyan_edilmemis_olay'];",
     True),

    ("M12 beyan edilen GA4-only olay beyaz listeden DUSER (beyan <-> liste ayrisir)",
     "tools/build.py",
     "'begin_checkout','generate_lead'];",
     "'begin_checkout'];",
     True),

    ("M13 beyan VAR ama cagri yeri YOK (olu beyan) — UC uretecin UCUNDE de sokulur",
     [("tools/build.py",
       "window.pruvoGA4Track('generate_lead',{{method:'help_cta'}});",
       "/* sokuldu */"),
      ("tools/marka_model_build.py",
       "window.pruvoGA4Track('generate_lead',{method:'help_cta'});",
       "/* sokuldu */"),
      # index.html'de IKI ayri temas noktasi var (help_cta | satir_soru; sepetin toplu
      # WhatsApp butonu ve onun cart_order cagrisi Okan emriyle 7 Eki'de SILINDI);
      # BIRI kalirsa "olu beyan" kolu hakli olarak YESIL kalir ve mutant EKSIK kurulur.
      ("index.html",
       "window.pruvoGA4Track('generate_lead',{method:'help_cta'});",
       "/* sokuldu */"),
      ("index.html",
       "window.pruvoGA4Track('generate_lead',{method:'satir_soru'});",
       "/* sokuldu */")],
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


def duzenlemeler(m):
    """Mutant kaydini (klasik ya da cok-yerli) [(dosya, eski, yeni), ...] yapar."""
    if len(m) == 5:
        return [(m[1], m[2], m[3])]
    return list(m[1])


def kirmizi_bekleniyor(m):
    return m[-1]


def kopya_kur(rel_listesi):
    """Gecici bir depo koku kurar: `tools/` kopya, mutasyon hedefleri GERCEK kopya.

    Donus: (tmp, kopya). `tmp` cagiran tarafindan finally ile silinir; surec SIGKILL ile
    duserse geride yalniz gecici dizin kalir — CANLI agacta tek bayt degismis olmaz."""
    tmp = tempfile.mkdtemp(prefix="ga4-mutant-")
    kopya = kopya_kok(tmp)
    for rel in rel_listesi:
        gercek_dosya(kopya, rel)
    return tmp, kopya


def kapi_kos(kopya):
    """Kapiyi KOPYADAN kosar: kapi ROOT'u kendi __file__'indan turetir, yani kopyayi gorur."""
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-B", os.path.join(kopya, "tools", KAPI_ADI)],
                       cwd=kopya, env=ortam, capture_output=True, text=True, timeout=1800)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ozet(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    print("=" * 70)
    print("GA4 OLAY KAPISI — MUTASYON BATARYASI (izole kopya)")
    print("=" * 70)

    # Canli agacin dokunulacak her dosyasinin ozeti: mutasyon yalniz kopyaya yazilsa da
    # "canliya dokunmadim" bir BEYANDIR; kanit bas/son ozet esitligidir
    # ([["olculdu" diyen hukum kaniti]]). Esit degilse batarya KIRMIZI biter.
    hedefler = sorted({rel for m in MUTANTLAR for rel, _, _ in duzenlemeler(m)})
    ozetler = {rel: ozet(os.path.join(ROOT, rel)) for rel in hedefler}

    tmp, kopya = kopya_kur(hedefler)
    try:
        rc, cikti = kapi_kos(kopya)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if rc != 0:
        print("TABAN KIRMIZI/OLCULEMEDI (rc=%d) — mutasyon anlamsiz. Son satirlar:" % rc)
        print("\n".join(cikti.strip().splitlines()[-12:]))
        return 3
    print("  taban: kapi YESIL (rc=0) — mutasyon baslayabilir\n")

    oldurucu = [m for m in MUTANTLAR if kirmizi_bekleniyor(m)]
    dusen, hatali = 0, []
    for m in MUTANTLAR:
        ad, kirmizi_bekle = m[0], kirmizi_bekleniyor(m)
        duzen = duzenlemeler(m)
        tmp, kopya = kopya_kur(sorted({rel for rel, _, _ in duzen}))
        try:
            yollar = {rel: gercek_dosya(kopya, rel) for rel, _, _ in duzen}
            asillar, eksik = {}, []
            for rel, eski, _ in duzen:
                with open(yollar[rel], encoding="utf-8") as f:
                    asillar[rel] = f.read()
                if asillar[rel].count(eski) < 1:
                    eksik.append(rel)
            # 🔴 Cok-yerli mutantta TEK bir capa bile dusmusse mutant EKSIK kurulur ve
            # "sag kaldi" gibi degil, CAPA YOK olarak raporlanir — sessiz kacis YOK.
            if eksik:
                hatali.append("%s — capa bulunamadi (%s)" % (ad, ", ".join(eksik)))
                print("  ⚠️  %s -> CAPA YOK (%s)" % (ad, ", ".join(eksik)))
                continue
            # 🔴 Yazma oncesi FAIL-CLOSED: hedef bag ya da kopya disi ise yazilmaz.
            disarida = [rel for rel, y in yollar.items() if not kopyada_mi(y, kopya)]
            if disarida:
                hatali.append("%s — hedef kopya DISINDA (%s), yazilmadi" % (ad, ", ".join(disarida)))
                print("  ❌  %s -> HEDEF KOPYA DISI (%s)" % (ad, ", ".join(disarida)))
                continue
            # 🔴 AYNI DOSYAYA BIRDEN COK duzenleme birikerek uygulanir. Her duzenlemeyi
            # asil govde uzerinden yazmak, ayni dosyanin ikinci duzenlemesi birinciyi
            # GERI ALDIGI icin mutanti EKSIK kurar ve "sag kaldi" gibi gorunur.
            yeni_govde = dict(asillar)
            for rel, eski, yeni in duzen:
                yeni_govde[rel] = yeni_govde[rel].replace(eski, yeni, 1)
            for rel, govde in yeni_govde.items():
                with open(yollar[rel], "w", encoding="utf-8") as f:
                    f.write(govde)
            rc, _ = kapi_kos(kopya)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
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

    for rel, beklenen in sorted(ozetler.items()):
        if ozet(os.path.join(ROOT, rel)) != beklenen:
            hatali.append("%s CANLI agacta DEGISTI (mutant kopya disina tasti)" % rel)
            print("  ❌  CANLI AGAC: %s ozet degisti" % rel)
    print("  ok  canli agac: %d hedef dosya bayt-birebir AYNI (mutasyon yalniz kopyada)"
          % len(ozetler))
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
