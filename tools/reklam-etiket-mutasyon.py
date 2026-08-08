#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — reklam etiket kapsam nobetciligi GERCEKTEN kirmizi yaniyor mu.

    python3 tools/reklam-etiket-mutasyon.py

NEDEN REPODA DURUYOR: anlatilan bir mutasyon bataryasi KANIT DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]). Surucu burada durur ki hukum yeniden
uretilebilsin. CI ADIMI DEGILDIR (elde kosulan kanit araci) — kapinin kendi ic
nobetcisi `tools/reklam-etiket-kapisi.py --kendini-test` CI'da kosar.

NASIL CALISIR: izlenen `*.py` + `*.html` dosyalari GECICI bir agaca kopyalanir
(`git init` -> kapinin `git ls-files` turetimi orada da calisir), mutasyon YALNIZ o
kopyaya uygulanir. CANLI depoya YAZMA YOKTUR.

KABUL (iki yonlu):
  · Her OLDURUCU mutant TEK BASINA kirmizi yakmali (gate rc=1 veya davranis testi rc=1).
  · ÇOKME KIRMIZI SAYILMAZ: gate icin rc=3 (OLCULEMEDI) ve traceback REDDEDILIR; davranis
    testinde "SONUC: KIRMIZI" imzasi aranir. Yoksa mutant DUSMEMIS sayilir.
  · KONTROL mutanti (davranisi degistirmeyen yorum duzenlemesi) YESIL KALMALI — yoksa
    batarya "her degisiklige kirmizi" halinden ayirt edilemez ve her mesru bakim
    duzenlemesi yayini durdurur.
"""

import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAPI = os.path.join(KOK, "tools", "reklam-etiket-kapisi.py")


def _izlenen(desen):
    sonuc = subprocess.run(["git", "-C", KOK, "ls-files", desen],
                           capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise SystemExit("git ls-files basarisiz: %s" % sonuc.stderr.strip())
    return [s for s in sonuc.stdout.splitlines() if s.strip()]


def ayna_kur(hedef):
    """Izlenen .py + .html + davranis testini gecici agaca kopyala, git deposu yap."""
    for rel in _izlenen("*.py") + _izlenen("*.html") + ["tools/reklam-url-test.js"]:
        kaynak = os.path.join(KOK, rel)
        if not os.path.isfile(kaynak):
            continue
        varis = os.path.join(hedef, rel)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        shutil.copyfile(kaynak, varis)
    for komut in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", "-C", hedef] + komut, capture_output=True, text=True)


def uygula(agac, rel, eski, yeni):
    """Tek dosyada tek degisim. Capa bulunamazsa mutant GECERSIZ (sessiz gecilmez)."""
    yol = os.path.join(agac, rel)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    if metin.count(eski) < 1:
        raise SystemExit("MUTANT CAPASI YOK -> %s :: %r" % (rel, eski[:70]))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin.replace(eski, yeni, 1))


def kapi_kos(agac):
    return subprocess.run([sys.executable, KAPI, "--kok", agac],
                          capture_output=True, text=True)


def davranis_kos(agac):
    return subprocess.run(["node", os.path.join(agac, "tools", "reklam-url-test.js")],
                          capture_output=True, text=True)


# --- MUTANTLAR ---------------------------------------------------------------
# (ad, oldurucu_mu, [(dosya, eski, yeni), ...])
PASSTHROUGH = "  gtag('set', 'url_passthrough', true);\n"
REDACTION = "  gtag('set', 'ads_data_redaction', true);\n"
KORUMA_DONGUSU = """    try{
      var mevcutQ = new URLSearchParams(location.search);
      var korunan = PRUVO_ATIF.urlKorunan();"""

MUTANTLAR = [
    ("M1 index.html'de url_passthrough sessizce kalkar (ikiz ayrismasi)", True,
     [("index.html", PASSTHROUGH, "")]),
    ("M2 tek kaynakta (build.py) ads_data_redaction kalkar", True,
     [("tools/build.py", REDACTION, "")]),
    ("M3 marka/model sablonundan {ga_head} capasi kalkar", True,
     [("tools/marka_model_build.py", "{ga_head}\n", "")]),
    ("M4 syncUrl reklam parametrelerini korumayi birakir", True,
     [("index.html", KORUMA_DONGUSU,
       """    try{
      var mevcutQ = new URLSearchParams(location.search);
      var korunan = [];""")]),
    ("M5 kanonik korunan kume daraltilir (gbraid/wbraid duser)", True,
     [("index.html", '"fbc","fbclid","gclid","gbraid","wbraid","ttclid","msclkid"',
       '"fbc","fbclid","gclid","ttclid","msclkid"')]),
    ("M6 syncUrl KAPSAMI GENISLER (her parametreyi tasir)", True,
     [("index.html", "        var kad = korunan[ki];",
       "        var kad = korunan[ki];\n"
       "        mevcutQ.forEach(function(v,n){ if(!params.has(n)){ params.set(n,v); } });")]),
    ("M7 bir yasal sayfanin GA cekirdegi tek kaynaktan ayrisir", True,
     [("sss/index.html", REDACTION, "")]),
    # --- FAZ 2 (riza bandi reklam iznini de ister) ------------------------------
    ("M8 grant kumesinden ad_storage dusurulur", True,
     [("index.html", "['analytics_storage', 'ad_storage', 'ad_user_data',",
       "['analytics_storage', 'ad_user_data',")]),
    ("M9 VARSAYILAN gevsetilir (ad_storage granted baslar)", True,
     [("index.html", "    'ad_storage': 'denied',", "    'ad_storage': 'granted',")]),
    ("M10 bant kanonik grant yerine DAR grant yapar", True,
     [("index.html",
       "    if(typeof window.pruvoRizaUygula === \"function\"){ window.pruvoRizaUygula('granted'); }",
       "    if(typeof gtag === \"function\"){ gtag('consent','update',{'analytics_storage':'granted'}); }")]),
    ("M11 ESKI DAR riza kaydi sessizce reklam iznine genisletilir", True,
     [("index.html",
       """      if (localStorage.getItem('pruvo_onay_kapsam') === window.PRUVO_RIZA_KAPSAMI) {
        window.pruvoRizaUygula('granted');
      } else {
        gtag('consent', 'update', { 'analytics_storage': 'granted' });
      }""",
       "      window.pruvoRizaUygula('granted');")]),
    ("M12 bant riza KAPSAM kaydini yazmayi birakir", True,
     [("index.html",
       "      if(deger === \"kabul\" && kapsamAdi()){ localStorage.setItem(KAPSAM_ANAHTARI, kapsamAdi()); }\n"
       "      else { localStorage.removeItem(KAPSAM_ANAHTARI); }\n",
       "")]),
    # KONTROL: davranisi DEGISTIRMEYEN duzenleme -> YESIL KALMALI.
    ("K1 KONTROL yorum metni degisir (davranis AYNI)", False,
     [("index.html", "/* filtre adıyla çakışırsa filtre kazanır */",
       "/* çakışma halinde görünüm durumu kazanır */")]),
]


def main():
    if shutil.which("node") is None:
        print("OLCULEMEDI: node yok -> davranis kolu kosulamaz (fail-closed)")
        return 3

    # 0) Mutasyonsuz KONTROL kosumu: batarya "hep kirmizi" olamaz.
    taban = tempfile.mkdtemp(prefix="reklam-mutasyon-taban-")
    try:
        ayna_kur(taban)
        t_kapi, t_dav = kapi_kos(taban), davranis_kos(taban)
    finally:
        shutil.rmtree(taban, ignore_errors=True)
    if t_kapi.returncode != 0 or t_dav.returncode != 0:
        print("TABAN KIRMIZI — mutasyonsuz ayna zaten dusuyor (kapi rc=%d, davranis rc=%d)"
              % (t_kapi.returncode, t_dav.returncode))
        print(t_kapi.stdout[-1500:])
        print(t_dav.stdout[-1500:])
        return 1
    print("  ok  TABAN (mutasyonsuz ayna) YESIL — kapi rc=0, davranis rc=0")

    oldurucu_toplam = sum(1 for _, o, _ in MUTANTLAR if o)
    dusen, hatalar = 0, []
    kontrol_durumu = "YESIL"

    for ad, oldurucu, degisimler in MUTANTLAR:
        agac = tempfile.mkdtemp(prefix="reklam-mutasyon-")
        try:
            ayna_kur(agac)
            for rel, eski, yeni in degisimler:
                uygula(agac, rel, eski, yeni)
            k, d = kapi_kos(agac), davranis_kos(agac)
        finally:
            shutil.rmtree(agac, ignore_errors=True)

        # ÇÖKME KIRMIZI SAYILMAZ: kapi icin YALNIZ rc=1 (KIRMIZI hukmu) kabul edilir;
        # rc=3 (OLCULEMEDI) ya da traceback "mutant dustu" DEMEK DEGILDIR.
        # ⚠️ Davranis testi hukmunu STDERR'e basar (console.error) — yalniz stdout'a
        # bakan bir kontrol onu "sag kaldi" sanar (olculdu: M4/M6 sahte-sag kaliyordu).
        kapi_kirmizi = (k.returncode == 1 and "SONUC: KIRMIZI" in (k.stdout + k.stderr))
        dav_kirmizi = (d.returncode == 1 and "SONUC: KIRMIZI" in (d.stdout + d.stderr))
        cokme = ("Traceback" in k.stderr) or (k.returncode not in (0, 1, 3))
        kirmizi = (kapi_kirmizi or dav_kirmizi) and not cokme

        kol = ("kapi" if kapi_kirmizi else "") + ("+davranis" if dav_kirmizi else "")
        if oldurucu:
            if kirmizi:
                dusen += 1
                print("  ok  %s -> KIRMIZI (%s)" % (ad, kol.strip("+")))
            else:
                hatalar.append("%s SAG KALDI (kapi rc=%d, davranis rc=%d, cokme=%s)"
                               % (ad, k.returncode, d.returncode, cokme))
                print("  FAIL %s -> SAG KALDI (kapi rc=%d, davranis rc=%d)"
                      % (ad, k.returncode, d.returncode))
        else:
            if kirmizi or k.returncode != 0 or d.returncode != 0:
                kontrol_durumu = "KIRMIZI"
                hatalar.append("%s KIRMIZI YANDI — batarya her degisiklige kirmizi veriyor "
                               "(kapi rc=%d, davranis rc=%d)" % (ad, k.returncode, d.returncode))
                print("  FAIL %s -> KIRMIZI (kontrol mutanti yesil kalmaliydi)" % ad)
            else:
                print("  ok  %s -> YESIL (kontrol)" % ad)

    print("-" * 70)
    print("MUTANT=%d/%d  KONTROL_MUTANT=%s" % (dusen, oldurucu_toplam, kontrol_durumu))
    if hatalar:
        for h in hatalar:
            print("  · %s" % h)
        return 1
    print("SONUC: YESIL ✅ — oldurucu mutantlarin hepsi TEK BASINA kirmizi, kontrol YESIL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
