#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CTA DENGE KAPISI — MUTASYON SURUCUSU (kanit repoda durur, anlatiya guvenilmez).

`tools/cta-denge-kapisi.py`nin GERCEKTEN olcup olcmedigini kanitlar: her mutant duzeni
tek bir eksende bozar, kapiyi kosar ve KIRMIZI (rc != 0) bekler. KONTROL mutantlari
(yalniz yorum metni · ilgisiz CSS) YESIL beklenir — batarya "her seye kirmizi yanan"
bir alarm degildir.

🔴 MUTASYON DAIMA KOPYAYA: canli calisma agacina HICBIR yazma yapilmaz. Her mutant
icin gecici bir kok kurulur; kok, gercek agacin SEMBOLIK BAGLI aynasidir ve yalnizca
mutasyona ugrayan dosyalar GERCEK KOPYADIR (861 MB'lik agac kopyalanmaz). Batarya
sonunda canli agacin sha256 ozetleri bas=son karsilastirilir.

🔴 CAPA JETONLARI AYRIK: kapinin yedi kolu `CTA-A1-ORAN`, `CTA-A2-BANT-PAYI`,
`CTA-A3-SEPET-ALAN`, `CTA-A4-DOKUNMA-44`, `CTA-A5-KANAL-WA`, `CTA-A6-GECIS-ORAN`,
`CTA-A7-ETIKET-SIGDI` jetonlariyla konusur; hicbiri digerinin alt dizesi DEGILDIR
(bu depoda olculmus tuzak).

🔴 DARALTMA VAKASI (11 Agu 2026): Okan "buton metne gore daralsin" dedi. Daraltma iki
YENI sessiz bozulma sinifi acar ve batarya ikisini de kovalar — (a) buton WhatsApp
hapinin ALTINA duser (M12), (b) etiket kutuya SIGMAZ ve
`white-space:nowrap` yuzunden SARMADAN KIRPILIR, yani yukseklik ayni kalir ve oran
saglikli gorunur (M13). M13'un oldurucu oldugu tek kol CTA-A7'dir: A1 o mutantta
YESIL kalir, cunku buton kaba yayilip ALANCA buyur.

🔴 IKINCI TUR (11 Agu, ayni gun — Okan karari): hap ETIKETI kisaltildi. Uzun on-ek artik
GLOBAL gizlenir (mobil-only DEGIL), masaustu hapi 11.131 -> 8.340 px²'ye dustu ve
`.ikon-sepet`in min-width DENGE TABANI GEREKSIZLESIP kaldirildi: masaustunde de GERCEK
fit-content. Sonuc: M12 yeniden tasarlandi — artik TABANI degil, dengeyi TUTAN gizleme
kuralini deler. M1/M8/M14 capalari da kuralin YENI metnine tasindi; eski min-width
capalari kaynakta artik YOK ve birebir birakilsalardi sessizce no-op olur, batarya
korelirdi (dosyanin kendi `_capa_tekil` nobeti bunu ARIZA sayar).

🔴 CANLI VAKA FIKSTURU (11 Agu 2026): M10 + M11, canlida OLCULEN iki bozulmayi geri
getirir — (a) sepet CTA'larinin `transition`i `all`a doner, yani sinif takasinin ilk
karesinde ikincil WhatsApp birincil odemeden BUYUK render edilir (gorunmeyen sekmede
KALICI); (b) WhatsApp etiketi 375 px'te SARAR ve buton 44 -> 63,5 px'e uzar. Kapi bu
onarimlardan ONCE ikisini de GOREMIYORDU: yalniz yerlesmis hal ve yalniz YUKSEKLIK
olculdugu icin CTA-A3 YESIL yaniyordu.

🔴 BYTECODE ONBELLEGI: alt surec `-B` ile ve `PYTHONDONTWRITEBYTECODE=1` ile kosar,
her kosumda `__pycache__` silinir — ayni saniyede ayni uzunlukta yazilan mutasyonun
bayat bytecode ile kosmasi sinifi kapali ([[mutasyon-bytecode-onbellegi]]).

Kabul: her oldurucu mutant TEK BASINA kirmizi + KONTROL mutantlari YESIL. Cikis kodu
tek basina yeterli DEGIL; basilan MUTANT=n/n sayisi da okunur ([[beyan-edilmis-survivor]]).

KOSUM: python3 tools/cta-denge-mutasyon.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_REL = "tools/cta-denge-kapisi.py"

# Mutasyona acilan dosyalar: gecici kokte GERCEK KOPYA olurlar (digerleri symlink).
KOPYALANAN = ("tools/build.py", "index.html", KAPI_REL)

# (ad, [(dosya, eski, yeni), ...], kirmizi_bekleniyor_mu)
MUTANTLAR = [
    ("M1 oran TERS cevrilir (Sepete Ekle yeniden 44x44 ikon olur)",
     [("tools/build.py",
       ".ikon-sepet{background:var(--navy);width:fit-content;height:56px;",
       ".ikon-sepet{background:var(--navy);width:44px;min-width:44px;height:44px;")],
     True),

    ("M2 sticky bant eski %16,6 payina sisirilir",
     [("tools/build.py",
       ".help-cta-inner{padding:8px 14px;gap:10px;flex-wrap:nowrap;",
       ".help-cta-inner{padding:38px 14px;gap:10px;flex-wrap:nowrap;")],
     True),

    ("M3 Sepete Ekle ETIKETI sokulur (ikon-only'ye donus)",
     [("tools/build.py",
       "'<span class=\"cart-label\">Sepete Ekle</span></button>'",
       "'</button>'")],
     True),

    ("M4 sepette WhatsApp odeme CTA'sini EZER (tam genislik + buyuk)",
     [("index.html",
       "padding:10px 16px;font-size:13.5px;width:fit-content;min-height:44px;"
       "margin:8px auto 0}",
       "padding:20px 16px;font-size:15.5px;width:100%;min-height:44px;"
       "margin:8px auto 0}")],
     True),

    ("M9 ikincil WhatsApp `auto`ya doner (blok flex kabi satiri DOLDURUR)",
     [("index.html",
       "padding:10px 16px;font-size:13.5px;width:fit-content;min-height:44px;"
       "margin:8px auto 0}",
       "padding:10px 16px;font-size:13.5px;width:auto;min-height:44px;"
       "margin:8px auto 0}")],
     True),

    ("M5 WhatsApp dokunma hedefi 44 px'in ALTINA duser",
     [("tools/build.py",
       ".help-cta-btn{padding:11px 14px;font-size:13px;gap:6px;min-height:44px;flex:none}",
       ".help-cta-btn{padding:11px 14px;font-size:13px;gap:6px;flex:none}")],
     True),

    ("M6 olcum capasi kirilir -> OLCULEMEDI (sessiz yesil OLMAMALI)",
     [("index.html", 'id="cartOrder"', 'id="cartSiparisBaglantisi"')],
     True),

    ("M7 M6 + kapinin OLCULEMEDI kolu sessiz YESILE cevrilir",
     [("index.html", 'id="cartOrder"', 'id="cartSiparisBaglantisi"'),
      (KAPI_REL, "YESIL, KIRMIZI, OLCULEMEDI_RC = 0, 1, 3",
       "YESIL, KIRMIZI, OLCULEMEDI_RC = 0, 1, 0")],
     True),

    ("M8 pozitif kanit kaynagi silinir (.ikon-sepet olcu kurali)",
     [("tools/build.py",
       "  .ikon-sepet{background:var(--navy);width:fit-content;height:56px;\n"
       "    padding:0 14px;gap:9px;color:#fff;font-size:16px;font-weight:700;"
       "font-family:inherit}\n",
       "")],
     True),

    # 🔴 M10 — CANLI VAKA (a): gecis penceresi geri acilir. `transition:.15s` kisayolu
    # `transition-property` tasimadigi icin `all` demektir; sinif takasinin ilk karesinde
    # odeme hala `.disabled` font-size'inde, WhatsApp hala `.ikincil` ONCESI dolgusunda
    # render edilir ve ikincil kanal birincili GECER. Kapi bu kareyi gormezse mutant
    # SAG KALIR — CTA-A6'nin var olma sebebi tam olarak budur.
    ("M10 sepet CTA'larinda gecis yeniden `all` olur (ters render karesi geri gelir)",
     [("index.html",
       "transition:background-color .15s,color .15s,border-color .15s;",
       "transition:.15s;")],
     True),

    # 🔴 M11 — CANLI VAKA (b): WhatsApp etiketi 375 px'te SARACAK kadar uzar. `fit-content`
    # kullanilabilir genislige kilitlenir, metin iki satira boluner ve buton 44 -> 63,5 px'e
    # cikar. Kapi sarmayi modellemezse buton yine 44 px sanilir ve mutant SAG KALIR.
    ("M11 WhatsApp etiketi 375 px'te SARAR (buton uzar, oran duser)",
     [("index.html",
       "      WhatsApp ile Sipariş Ver\n",
       "      WhatsApp ile Hemen Sipariş Ver ve Bilgi Al\n")],
     True),

    # 🔴 M12 — DARALTMA VAKASI (a): masaustu dengeyi TUTAN sey delinir.
    #
    # TARIHCE (capa neden degisti): 11 Agu'nun ILK turunda masaustu dengeyi
    # `.ikon-sepet`in min-width TABANI (210 px) tutuyordu ve M12 o tabani deliyordu.
    # Okan ayni gun "hap etiketini kisalt" dedi: uzun on-ek GLOBAL gizlendi, masaustu
    # hapi 11.131 -> 8.340 px² dustu ve taban GEREKSIZLESIP KALDIRILDI. Yani eski capa
    # (`min-width:210px`) artik kaynakta YOK; birebir birakilsaydi mutant no-op olur ve
    # batarya SESSIZCE korelirdi ([[beyan-edilmis-survivor]]).
    #
    # YENI VAKA: dengeyi artik KISA ETIKET tutuyor. Mutant global gizleme kuralini
    # yeniden MOBIL-ONLY'ye daraltir (11 Agu oncesi hal). Mobil AYNI kalir — bozulan
    # eksen yalnizca MASAUSTUDUR: hap "Bizimle Iletisime Gecin"e geri buyur
    # (254,4 x 43,75 = 11.131 px²), buton gercek fit-content'inde kalir
    # (155,8 x 56 = 8.725 px²) ve masaustu orani 1,05 -> 0,78'e duser.
    # Kapi gizleme kuralini VIEWPORT'a gore cozmezse (yani global kurali masaustunde de
    # tuketmezse) mutant SAG KALIR — `gorunur_metin`/`stil` cifti tam bunun icin var.
    # ⚠️ CAPA CSS'E KILITLI: iki adim da kuralin kendi satir baglamini tasir; capa
    # metnini ANLATAN yorumlar bilerek bu dizeleri BIREBIR icermez ve `_capa_tekil`
    # nobeti coklu/sifir eslesmeyi TOPTAN reddeder.
    ("M12 masaustu denge kaynagi delinir (gizleme yeniden MOBIL-ONLY'ye daraltilir)",
     [("tools/build.py",
       "\n  .wa-uzun{display:none}\n",
       "\n"),
      ("tools/build.py",
       "    .help-cta-btn{padding:11px 14px;font-size:13px;gap:6px;min-height:44px;"
       "flex:none}\n",
       "    .help-cta-btn{padding:11px 14px;font-size:13px;gap:6px;min-height:44px;"
       "flex:none}\n    .wa-uzun{display:none}\n")],
     True),

    # 🔴 M13 — DARALTMA VAKASI (b): etiket kutuya SIGMAZ. `.cart-label{white-space:nowrap}`
    # oldugu icin metin SARMAZ, KIRPILIR: buton yuksekligi 56'da kalir, kap genisligine
    # yayildigi icin ALAN da BUYUR ve CTA-A1 YESIL yanar. Bu mutanti yalniz
    # CTA-A7-ETIKET-SIGDI oldurur — "satir sayisi 1" diye bakan bir kol da kanardi.
    ("M13 Sepete Ekle etiketi kutuya SIGMAZ (nowrap yuzunden sarmadan KIRPILIR)",
     [("tools/build.py",
       "'<span class=\"cart-label\">Sepete Ekle</span></button>'",
       "'<span class=\"cart-label\">Sepete Ekle ve Siparisi Hemen Tamamla</span></button>'")],
     True),

    # M14 — yukseklik ekseni. Capa, denge tabani kalkinca `.ikon-sepet`in YENI olcu
    # metnine tasindi (`width:fit-content;height:56px;`); vaka DEGISMEDI.
    ("M14 Sepete Ekle dokunma yuksekligi 44 px'in ALTINA duser",
     [("tools/build.py", "width:fit-content;height:56px;",
       "width:fit-content;height:40px;")],
     True),

    # 🔴 M15 — YENI TURETMENIN FAIL-CLOSED KANITI: eylem satirinin genisligi artik
    # `main` + `.detail` + `.opsiyonlar` zincirinden turer. Grid kolonlari cozulemeyen
    # bir yazima (`repeat(2,1fr)`) donunce kapi SARMAYI ve FLEX BUYUMESINI modelleyemez
    # ve "gecti" DEMEZ -> OLCULEMEDI. Sessiz yesil bu yolda da kapali.
    ("M15 eylem satiri genislik capasi kirilir -> OLCULEMEDI (sessiz yesil OLMAMALI)",
     [("tools/build.py",
       "  .detail{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:start}",
       "  .detail{display:grid;grid-template-columns:repeat(2,1fr);gap:34px;align-items:start}")],
     True),

    ("K1 KONTROL — yalniz yorum metni degisir (davranis AYNI)",
     [("tools/build.py",
       "# `.cart-label` sinifi ZORUNLU: sayfa scripti sepetteki/sepette-degil durumunu O spanin",
       "# `.cart-label` sinifi ZORUNLU: sayfa scripti sepet durumunu O spanin")],
     False),

    ("K2 KONTROL — ilgisiz CSS degisir (ilgili urun kartinin yazi boyu)",
     [("tools/build.py",
       "  .rel-title{font-size:14px;font-weight:700;line-height:1.35;margin-bottom:6px}",
       "  .rel-title{font-size:13.5px;font-weight:700;line-height:1.35;margin-bottom:6px}")],
     False),
]


def gecici_kok(hedef):
    """Gercek agacin SEMBOLIK BAGLI aynasi; KOPYALANAN dosyalar gercek kopyadir."""
    os.makedirs(hedef, exist_ok=True)
    gercek_dizinler = {os.path.dirname(r) for r in KOPYALANAN if os.path.dirname(r)}
    for ad in os.listdir(ROOT):
        if ad == ".git":
            continue
        kaynak = os.path.join(ROOT, ad)
        varis = os.path.join(hedef, ad)
        if ad in gercek_dizinler:
            os.makedirs(varis, exist_ok=True)
            for alt in os.listdir(kaynak):
                if alt == "__pycache__":
                    continue
                alt_rel = ad + "/" + alt
                if alt_rel in KOPYALANAN:
                    shutil.copy2(os.path.join(kaynak, alt), os.path.join(varis, alt))
                else:
                    os.symlink(os.path.join(kaynak, alt), os.path.join(varis, alt))
        elif ad in KOPYALANAN:
            shutil.copy2(kaynak, varis)
        else:
            os.symlink(kaynak, varis)


def kapi_kos(kok):
    shutil.rmtree(os.path.join(kok, "tools", "__pycache__"), ignore_errors=True)
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-B", os.path.join(kok, KAPI_REL),
                        "--kok", kok],
                       cwd=kok, env=ortam, capture_output=True, text=True, timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _ozet(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    print("=" * 74)
    print("CTA DENGE KAPISI — MUTASYON BATARYASI (mutasyon DAIMA kopyaya)")
    print("=" * 74)

    izlenen = sorted({d for _, adimlar, _ in MUTANTLAR for d, _, _ in adimlar}
                     | set(KOPYALANAN))
    ozetler = {rel: _ozet(rel) for rel in izlenen}

    with tempfile.TemporaryDirectory(prefix="cta-denge-taban-") as taban:
        kok = os.path.join(taban, "agac")
        gecici_kok(kok)
        rc, cikti = kapi_kos(kok)
    if rc != 0:
        print("TABAN KIRMIZI/OLCULEMEDI (rc=%d) — mutasyon anlamsiz. Son satirlar:" % rc)
        print("\n".join(cikti.strip().splitlines()[-14:]))
        return 3
    print("  taban: kapi YESIL (rc=0) — mutasyon baslayabilir\n")

    oldurucu = [m for m in MUTANTLAR if m[2]]
    dusen, hatali = 0, []
    for ad, adimlar, kirmizi_bekle in MUTANTLAR:
        with tempfile.TemporaryDirectory(prefix="cta-denge-mutant-") as gecici:
            kok = os.path.join(gecici, "agac")
            gecici_kok(kok)
            capa_yok = None
            for rel, eski, yeni in adimlar:
                yol = os.path.join(kok, rel)
                with open(yol, encoding="utf-8") as f:
                    metin = f.read()
                # 🔴 CAPA TEKIL OLMALI (_capa_tekil): `replace(..., 1)` ILK eslesmeyi
                # degistirir. Capa hem kurala hem onu ANLATAN yoruma uyuyorsa mutasyon
                # yoruma iner, davranis DEGISMEZ ve mutant sessizce SAG KALIR — bu
                # bataryada olculdu (M12). Coklu eslesme artik ARIZA sayilir.
                sayi = metin.count(eski)
                if sayi != 1:
                    capa_yok = "%s (%s) — %d eslesme (tam 1 bekleniyor)" % (ad, rel, sayi)
                    break
                with open(yol, "w", encoding="utf-8") as f:
                    f.write(metin.replace(eski, yeni, 1))
            if capa_yok:
                hatali.append("%s — capa gecersiz" % capa_yok)
                print("  ⚠️  %s -> CAPA GECERSIZ" % capa_yok)
                continue
            rc, _ = kapi_kos(kok)
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
        if _ozet(rel) != beklenen:
            hatali.append("%s CANLI AGACTA degisti (mutasyon kopyada kalmadi)" % rel)
            print("  ❌  CANLI AGAC: %s ozet degisti" % rel)
    print("  ok  canli agac: %d dosya bayt-birebir ayni (hicbir mutasyon sizmadi)"
          % len(ozetler))
    print("-" * 74)
    print("MUTANT=%d/%d  KONTROL=%s"
          % (dusen, len(oldurucu),
             "YESIL" if not any("KONTROL" in h for h in hatali) else "KIRMIZI"))
    if hatali:
        print("SONUC: KIRMIZI ❌")
        for h in hatali:
            print("   · " + h)
        return 1
    print("SONUC: YESIL ✅ — oldurucu mutantlarin hepsi TEK BASINA kirmizi, "
          "kontroller YESIL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
