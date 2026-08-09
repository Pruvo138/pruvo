#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kişisel veri koruması KABUL TESTİ + İÇ RAPOR SIZINTI NÖBETÇİSİ.

Neyi doğrular:
  1) NEGATİF — üretilen içerik sayfaları (teslimat-iade, mesafeli-satis,
     malzeme-rehberi; sayfalar.py+build.py'den TAZE render edilir) ve statik
     sayfalarda (index, hakkimizda, iletisim, sss, gizlilik) satıcının kişisel
     bilgileri HAM KAYNAKTA düz metin olarak GEÇMEZ.
     Tek istisna: <script type="application/ld+json"> blokları (SEO takası —
     bilinçli karar, mimar kaydında).
  2) POZİTİF — korumalı .pv span'larının parçaları (data-a..l) doğru sırada
     birleştirilince beklenen değerler birebir geri çıkar (sayfa müşteriye
     doğru bilgiyi göstermeye devam ediyor) ve her sayfada beklenen sayıda
     korumalı değer var.
  3) İÇ RAPOR SIZINTI NÖBETÇİSİ (27 Tem) — İKİ KURAL, TEK git taraması:
     KURAL A (küresel negatif, ad ekseni): İZLENEN (git ls-files) hiçbir dosya
       işçi→mimar iç rapor ADLANDIRMA ailesine uymayacak (dizinden bağımsız).
     KURAL B (kök belge kapısı, ad-BAĞIMSIZ): repo KÖKÜNDE izlenen her
       .md/.markdown/.txt, ADI NE OLURSA OLSUN, küçük bir İZİN LİSTESİNDE
       değilse kırmızı. Kural A'nın ad-ailesi deliğini kapatır (TESLIM-NOTU.md).
     Ayrıntı ve gerekçe için aşağıdaki bölüm başlıklarına bak.

  4) GEÇMİŞ EKSENİ (30 Tem) — (3)'ün aynı kuralı COMMIT GEÇMİŞİNE uygulanır:
     bir dosya eklenip aynı gün silinirse çalışma ağacı temizdir ama commit
     KALICIDIR ve PUBLIC repodan anonim çekilebilir. Ayrıntı: "GECMIS EKSENI".

Çalıştırma:
    python3 tools/kisisel-veri-test.py            # 5 nöbetçi + geçmiş fikstürleri
    python3 tools/kisisel-veri-test.py --pre-push # pre-push kancası (aralık stdin'den)
    python3 tools/kisisel-veri-test.py --aralik origin/main..HEAD   # BLOKLAYICI
    python3 tools/kisisel-veri-test.py --gecmis   # TÜM geçmişi tara — RAPOR (bloklamaz)
(çıkış kodu 0 = geçti)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from git_ortami import sentetik_git

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402  (render_content_page + CONTENT_PAGES)

# ------------------------------------------------------------------ aranan düz metin kalıpları
# Not: kalıplar boşluksuz NORMALİZE metinde aranır (boşluk/nbsp/tire farkları
# kaçamak yaratmasın diye). Hepsi kişisel veri; JSON-LD dışında SIFIR olmalı.
KALIPLAR = [
    "okangemalmaz", "gemalmaz",
    "+905325954005", "905325954005", "05325954005", "5325954005",
    "info@pruvo3d.com",
    "akarca", "adnanmenderes",
    "3910052435",
    "fethiyevergidairesi",
]

# ------------------------------------------------------------------ pozitif kontrol beklentileri
TEL = "+90 532 595 4005"
EPOSTA = "info@pruvo3d.com"
ADRES_KISA = "Adnan Menderes Blv. No:303, 48300 Fethiye/Muğla"
ADRES_TAM = "Akarca Mah. Adnan Menderes (BBT) Blv. No:303 Daire No:203, Fethiye / Muğla"
UNVAN = "Okan Gemalmaz"
VKN = "3910052435"
VD = "Fethiye Vergi Dairesi"

# sayfa -> o sayfada geri kurulabilmesi ŞART değerler
BEKLENEN = {
    "iletisim": [TEL, EPOSTA, ADRES_KISA],
    "gizlilik": [EPOSTA, ADRES_KISA],
    "teslimat-iade": [UNVAN, ADRES_TAM, VD, VKN, TEL, EPOSTA],
    "mesafeli-satis": [UNVAN, ADRES_TAM, VD, VKN, TEL, EPOSTA],
}

LD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>.*?</script>', re.S)
PV_RE = re.compile(r'<span class="pv[^"]*"([^>]*)></span>')
ATTR_RE = re.compile(r'data-([a-l])="([^"]*)"')


# ==================================================================================
# IC RAPOR SIZINTI NOBETCISI — KURESEL NEGATIF KURAL
# ==================================================================================
# NEDEN BURADA: bu dosya deploy.yml'in ILK bloklayici adimi ve zaten "PUBLIC repoya
# ne sizdi" ekseninde calisan sizinti/gizlilik kapisi. Nobetci buraya gomuldu ki
# CI'da kossun ve deploy.yml'e HIC hunk acilmasin (paralel isci o dosyada calisiyor).
#
# NEDEN VAR (olculdu, 27 Tem — AYNI HATA UC KEZ):
#   * RAPOR-*.md dislaniyordu (eski desen).
#   * Bir bagimsiz curutucu raporunu CURUTME-RAPORU.md yazdi -> deseni KACIRDI,
#     kendi dalinda IZLENEN olarak commit'lendi; .gitignore'a CURUTME-*.md eklendi.
#   * Ayni gun ONARIM-RAPORU.md de kacti; bir dal onu IZLENEN tasiyordu ve merge
#     edilseydi PUBLIC repoya girecekti (merge iscisi son anda izlemeden cikardi).
# KOK SEBEP: mimar spec'lerinde rapor adi standart DEGILDI (RAPOR-MIMARA /
# CURUTME-RAPORU / ONARIM-RAPORU). .gitignore deseni kovalamak bitmez -> kalici
# koruma NEGATIF + KURESEL bir nobetci olmali. Bu raporlar kapi bypass yollari,
# dal/ajan kimlikleri ve ic olcum detayi tasir; repo PUBLIC (Pruvo138/pruvo).
#
# EKSEN SECIMI (yanlis-pozitif = TUM SITE yayini durur, o yuzden DAR tutuldu):
#   * Kural DOSYA ADI ekseninde; icerik taramasi YOK (icerik ekseni her .md'yi
#     supheli yapar, mesru paket/rehber dosyalarini yakar).
#   * Yalniz BELGE uzantilari (.md/.markdown/.txt). OLCULDU: kural her uzantiya
#     acilsaydi bugun 5 MESRU izlenen dosya kirmizi yanardi (shop/src/olcum.js,
#     shop/test/olcum.mjs, shop/test/olcum-kapisi.cjs, tools/denetim-kapisi.py,
#     tools/denetim-kapisi-test.py) ve tum ekibin yayini dururdu.
#   * Onek kurali AYIRAC SARTLI ("rapor" + '-_. ' ya da tam esitlik) -> "raporlama.md",
#     "onarimlar.md" gibi mesru turevler YESIL kalir.
#   * Sonek kurali YALNIZ rapor/raporu (denetimi/olcumu'ye genisletmek
#     tools/paket-*.md gibi mesru mimar belgelerini yakma riski tasir).
# VERI CAPASI YOK: sabit dosya sayisi / SHA / tarih iddiasi yoktur; kural saf
# adlandirmadir, katalog buyudukce/kuculdukce degismez.
#
# ⚠️ BILINEN + BEYAN EDILEN KAPSAM SINIRLARI (30 Tem olcumu — KASITLA ACIK BIRAKILDI):
#   (K2) DIZIN ADI EKSENI KAPSANMIYOR. Kural yalniz TEKIL dosya adina bakar
#        (`yol.rsplit("/", 1)[-1]`). Olculdu: `CURUTME-RAPORU/notlar.md`,
#        `tools/raporlar/x.md`, `denetim-raporu/ek.txt` YESIL kalir. (Tesadufen
#        `raporlar/olcum.md` KIRMIZIDIR — ama dizin adindan degil, dosya adi
#        'olcum.md' oldugu icin.) NEDEN ACIK: dizin ekseni butun bir agaci tek
#        adla kirmizi yakar; `raporlar/` gibi mesru bir dizin adi altindaki HER
#        dosya (izlenen sablonlar dahil) bloklanirdi. Kapatilmasi istenirse ayri
#        bir yanlis-pozitif butcesi olculmelidir.
#   (K3) KALIP GENISLETME = PARSER TAKLIDI SINIFI. Bu kapi BLOKLAYICIDIR: bir
#        yanlis-pozitif TUM ekibin push'unu (ve main'de tum sitenin yayinini)
#        durdurur. Kok/sonek listesini "daha cok kelime" ile buyutmek (denetimi,
#        olcumu, inceleme, tutanak...) mesru mimar belgelerini yakar. Bu yuzden
#        kural SINIF bazinda genisletildi (bkz. SINIR KURALI) ama SOZLUK bazinda
#        DONDURULDU. Yeni kok/sonek eklemek = yeni FP butcesi olcmek.
_TR_KATLA = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})
IC_RAPOR_UZANTILARI = (".md", ".markdown", ".txt")
IC_RAPOR_KOKLERI = ("rapor", "curutme", "onarim", "denetim", "olcum")
IC_RAPOR_SONEKLERI = ("rapor", "raporu")

# ----------------------------------------------------------------- SINIR (ayirac) KURALI
# 30 Tem OLCUMU — DAR EŞLEŞME KUSURU (kusur 1): ayirac kumesi sabit dort karakterlik
# bir literal listesiydi ("-_. ") ve 8/8 su ad KACIYORDU:
#   rapor(1).md · raporMimara.md · RAPOR–1.md (U+2013 en-dash) · curutme–turu.md ·
#   yedekTopolojisiRaporu.md · olcum(2).md · tools/denetim(kopya).md · onarim—turu.md
# Sebep: parantez, en-dash/em-dash ve camelCase birer AYIRACTIR ama listede yoklardi.
# Bir "yasakli noktalama listesi" kovalamak da ayni bitmeyen oyundur -> kural
# SINIFA cevrildi:
#   (a) ALFANUMERIK OLMAYAN her karakter ayiractir (parantez, tire cesitleri, bosluk,
#       alt cizgi, nokta, tilde... hepsi tek kuralla kapanir);
#   (b) camelCase siniri: KUCUK harften sonra gelen BUYUK harf yeni parca baslatir.
# 🔴 (b) KASITLA DAR: yalniz kucuk->BUYUK gecisi sayilir. "RAPORLAMA.md" gibi TAMAMI
# BUYUK mesru bir adda 'L' onceki harf de buyuk oldugu icin sinir SAYILMAZ -> yesil
# kalir. (Sart 'i>0 and orijinal[i-1].islower()' olmasaydi tum-buyuk mesru adlar yanardi.)
# YANLIS-POZITIF BUTCESI: bu genisleme sonrasi 352 izlenen dosyanin tamami + 31 yesil
# fikstur yeniden olculdu, YANAN 0 (bkz. _IC_RAPOR_YESIL).


def _ayirac_karakter(c):
    """Alfanumerik OLMAYAN her karakter ad sinirridir (dar literal liste YOK)."""
    return not c.isalnum()


def _camel_sinir(orijinal, i):
    """orijinal[i] camelCase'de YENI parcanin ilk harfi mi (kucuk -> BUYUK gecisi)?
    Katlanmamis ad uzerinde bakilir; _TR_KATLA tek karakteri tek karaktere esler,
    bu yuzden indeksler katlanmis govdeyle BIREBIR hizalidir."""
    return 0 < i < len(orijinal) and orijinal[i].isupper() and orijinal[i - 1].islower()

# ISTISNA: aileye uyan ama MESRU olan izlenen dosya (yol -> GEREKCE). Bugun BOS.
# Buraya bir giris eklemek SIZINTI RISKI ustlenmektir; gerekce zorunlu (bos gerekce
# = kirmizi) ve aileye artik uymayan bayat giris de kirmizi (liste curumesin).
IC_RAPOR_ISTISNA = {}


def _ad_katla(ad):
    """Dosya adini karsilastirma icin normalize eder: Turkce harf katlama + kucuk harf.
    Git desenleri harf-DUYARLIDIR (bugun kacan 'curutme.md' kucuk harf hali kapsam
    disiydi); nobetci harf ve Turkce diakritik uzerinden kacisi kapatir."""
    return ad.translate(_TR_KATLA).lower()


def ic_rapor_mu(yol):
    """repo-gorece yol ic rapor ADLANDIRMA ailesine uyuyor mu (DIZINDEN BAGIMSIZ).

    Aile: <kok>[ayirac...] ya da <...ayirac>rapor|raporu   (kok = rapor/curutme/
    onarim/denetim/olcum), yalniz belge uzantilarinda. Ornekler:
      KIRMIZI: RAPOR-MIMARA.md · CURUTME-RAPORU.md · curutme.md · ONARIM-RAPORU.md ·
               OLCUM_NOTLARI.md · tools/yedek-topolojisi-raporu.md · ÇÜRÜTME-RAPORU.md
      YESIL  : CLAUDE.md · DEVAM-ARSIV.md · README.md · MEMORY.md · raporlama.md ·
               tools/paket-shop-odeme.md · shop/src/olcum.js
    """
    tekil = yol.rsplit("/", 1)[-1]
    ad = _ad_katla(tekil)
    uzanti = None
    for u in IC_RAPOR_UZANTILARI:
        if ad.endswith(u):
            uzanti = u
            break
    if uzanti is None:
        return False
    govde = ad[: -len(uzanti)]
    orijinal = tekil[: -len(uzanti)]      # katlanmamis hali (camelCase icin)
    if not govde:
        return False
    for kok in IC_RAPOR_KOKLERI:
        if govde == kok:
            return True
        if govde.startswith(kok) and (_ayirac_karakter(govde[len(kok)])
                                      or _camel_sinir(orijinal, len(kok))):
            return True
    for sonek in IC_RAPOR_SONEKLERI:
        bas = len(govde) - len(sonek)
        if (govde.endswith(sonek) and bas > 0
                and (_ayirac_karakter(govde[bas - 1]) or _camel_sinir(orijinal, bas))):
            return True
    return False


# --- KIRMIZI FIKSTURLER: kural bozulursa/oldurulurse bunlar KACAR -> kapi kirmizi.
_IC_RAPOR_KIRMIZI = [
    ("RAPOR-MIMARA.md", "protokol adi — isci raporu"),
    ("CURUTME-RAPORU.md", "27 Tem 1. kacak (dalda izlenen commit'lendi)"),
    ("ONARIM-RAPORU.md", "27 Tem 2. kacak (merge oncesi son anda yakalandi)"),
    ("curutme.md", "TIRESIZ + KUCUK HARF hali (olculdu: kapsam disiydi)"),
    ("CURUTME.md", "tiresiz tek kelime"),
    ("RAPOR.md", "tiresiz tek kelime"),
    ("CURUTME-RAPORU-TUR4.md", "olculdu: bir dalda izlenen"),
    ("tools/DENETIM-RAPORU.md", "alt dizinde — kural dizinden BAGIMSIZ olmali"),
    ("tools/yedek-topolojisi-raporu.md", "sonek kurali (kucuk harf -raporu)"),
    ("OLCUM_NOTLARI.md", "alt cizgi ayirac"),
    ("ÇÜRÜTME-RAPORU.md", "Turkce diakritik katlama"),
    # ⚠️ Asagidaki IKISI SONEK kuralinin ERISEMEDIGI hallerdir: yalniz Turkce harf
    # katlama yakalar. Olculdu (mutasyon M2): katlama oldurulunce ÇÜRÜTME-RAPORU.md
    # sonek kuralindan ("-raporu") gecip HAYATTA kaliyordu -> katlama nobetsiz kaliyordu.
    ("ÇÜRÜTME.md", "yalniz katlama yakalar (sonek yok)"),
    ("ÖLÇÜM-NOTLARI.md", "yalniz katlama yakalar (sonek yok)"),
    ("RAPOR-MIMARA.txt", "uzanti degistirerek kacis"),
    ("onarim-turu-3.markdown", "markdown uzantisi"),
    # --- 30 Tem, KUSUR 1 (DAR ESLESME): olculdu, 8/8 KACIYORDU. Sinif kurali kapatti.
    ("rapor(1).md", "kusur1: parantez ayirac (kopya adi)"),
    ("olcum(2).md", "kusur1: parantez ayirac"),
    ("tools/denetim(kopya).md", "kusur1: parantez + alt dizin"),
    ("raporMimara.md", "kusur1: camelCase siniri (kucuk->BUYUK)"),
    ("yedekTopolojisiRaporu.md", "kusur1: camelCase SONEK siniri"),
    ("RAPOR–1.md", "kusur1: U+2013 en-dash"),
    ("curutme–turu.md", "kusur1: U+2013 en-dash"),
    ("onarim—turu.md", "kusur1: U+2014 em-dash"),
]

# --- YESIL FIKSTURLER: "ILGISIZ RUTIN DUZENLEME YESIL KALIR". Bu kapi BLOKLAYICI —
# bir yanlis-pozitif TUM pruvo3d.com yayinini durdurur. Ilk alti madde mimarin
# saydigi rutin senaryolardir; kalani olculmus MESRU adlardir (24 izlenen .md +
# olcum/denetim adli mesru kod dosyalari).
_IC_RAPOR_YESIL = [
    ("urunler.json", "RUTIN 1: yeni urun eklendi"),
    ("mesafeli-satis/index.html", "RUTIN 2: yeni/duzenlenen yasal sayfa"),
    ("tools/sayfalar.py", "RUTIN 2: yasal sayfa kaynagi"),
    ("README.md", "RUTIN 3: README duzenlemesi"),
    ("tools/arsiv/README.md", "RUTIN 3: alt dizindeki README"),
    ("tools/yeni-kapisi.py", "RUTIN 4: tools/ icinde yeni .py"),
    ("olcuye-ozel-yeni-parca-uretimi/index.html", "RUTIN 5: CONTENT_PAGES dizini"),
    ("filamentler.json", "RUTIN 6: filament envanteri guncellemesi"),
    ("CLAUDE.md", "mesru: proje baglam dosyasi"),
    ("AGENTS.md", "mesru: CLAUDE.md symlink adi"),
    ("DEVAM.md", "mesru: ic not defteri"),
    ("DEVAM-ARSIV.md", "mesru: ic not arsivi"),
    ("MEMORY.md", "mesru: hafiza indeksi"),
    ("tools/URUN-EKLEME-REHBERI.md", "mesru: rehber"),
    ("tools/paket-shop-odeme.md", "mesru: mimar paketi"),
    ("tools/paket-durum-panosu.md", "mesru: mimar paketi"),
    ("tools/taban-fiyat-tablosu.md", "mesru: fiyat tablosu"),
    ("tools/edge-katalog-tetik.md", "mesru: izlenen tools belgesi"),
    ("tools/faz3-onbellek-purge.md", "mesru: izlenen tools belgesi"),
    ("ege-bilgi.md", "mesru: yayinlanan bot bilgi dosyasi"),
    ("jenerator/KURULUM.md", "mesru: kurulum belgesi"),
    ("jenerator/test/SOZLESME.md", "mesru: sozlesme belgesi"),
    ("shop/src/olcum.js", "OLCULDU FP: kural uzantiya acilirsa yanar"),
    ("shop/test/olcum.mjs", "OLCULDU FP: ayni sinif"),
    ("shop/test/olcum-kapisi.cjs", "OLCULDU FP: ayni sinif"),
    ("tools/denetim-kapisi.py", "OLCULDU FP: ayni sinif"),
    ("tools/denetim-kapisi-test.py", "OLCULDU FP: ayni sinif"),
    ("raporlama.md", "onek AYIRAC SARTLI olmali (turev kelime yanmaz)"),
    ("onarimlar.md", "onek AYIRAC SARTLI olmali"),
    ("denetimsiz-liste.md", "onek AYIRAC SARTLI olmali"),
    ("tools/paket-olcumleme.md", "onek degil govde ici — yanmamali"),
    # --- 30 Tem, kusur 1 genislemesinin YANLIS-POZITIF butcesi (camelCase DAR kalmali)
    ("RAPORLAMA.md", "TUM BUYUK mesru ad: 'L' oncesi de BUYUK -> camel siniri DEGIL"),
    ("ONARIMLAR.md", "TUM BUYUK mesru turev"),
    ("DENETIMSIZ.md", "TUM BUYUK mesru turev"),
    ("Raporlama.md", "bas harf buyuk mesru turev (kok sonrasi kucuk harf)"),
]


def ic_rapor_isabetleri(yollar):
    """Yol listesi -> ic rapor ailesine uyan (istisna DISI) yollar, sirali.
    GERCEK tarama ve fikstur oz-kontrolu AYNI fonksiyonu kullanir: biri oldurulurse
    (or. 'return []') fikstur oz-kontrolu de kirmizi yanar (olu tarayici korumasi)."""
    return sorted(y for y in yollar
                  if ic_rapor_mu(y) and y not in IC_RAPOR_ISTISNA)


def ic_rapor_fikstur_hatalari():
    """Nobetcinin KENDI hukmunu olcer (olu nobetci + asiri-genisleme korumasi).
    Bellekte calisir, diske/aga DOKUNMAZ."""
    hatalar = []
    # (0) TARAYICI OZ-KONTROLU: yol listesi -> isabet eslemesi CANLI mi.
    _sentetik = ["tools/build.py", "index.html", "README.md",
                 "CURUTME-RAPORU.md", "alt/dizin/ONARIM-RAPORU.md"]
    _beklenen = ["CURUTME-RAPORU.md", "alt/dizin/ONARIM-RAPORU.md"]
    _bulunan = ic_rapor_isabetleri(_sentetik)
    if _bulunan != _beklenen:
        hatalar.append("TARAYICI OLU/BOZUK: sentetik yol listesinde beklenen %r "
                       "yerine %r bulundu" % (_beklenen, _bulunan))
    # (0b) FAIL-LOUD nobeti: git okunamadiginda SESSIZ YESIL verilemez. Sahte bir
    # "basarisiz git" kosucusu enjekte edilir; nobetci OLCULEMEDI hatasi uretmeli.
    # (Olculdu: bu satirlar silinince kapi git'siz ortamda sessizce yesil yaniyordu.)
    _h, _ = ic_rapor_nobeti(kosucu=lambda: (128, "", "fatal: not a git repository"),
                            fikstur=False)
    if not any("OLCULEMEDI" in x for x in _h):
        hatalar.append("FAIL-LOUD OLDU: git ls-files basarisiz oldugunda nobetci "
                       "hata uretmiyor (olculemeyen hal sessiz yesile donmus)")
    # (0c) BOS KAPSAM nobeti (30 Tem, kusur 4): rc=0 + BOS cikti da OLCULEMEDI'dir.
    # (Olculdu: bu satirlar silinince kapi 'taranan: 0' ile SESSIZCE yesil yaniyordu.)
    _h2, _t2 = ic_rapor_nobeti(kosucu=lambda: (0, "", ""), fikstur=False)
    if not any("OLCULEMEDI" in x for x in _h2):
        hatalar.append("BOS KAPSAM SESSIZ YESIL: git ls-files rc=0 + BOS cikti "
                       "verdiginde nobetci hata uretmiyor (taranan=%d) — tarama "
                       "hicbir dosya gormezse kapi 'temiz' diyor" % _t2)
    # (0c-2) CANLILIK NOBETI (TUR 2 / D3) — KAPSAM AYRIMI (birlesim karari, 30 Tem):
    # BOS liste vakasinin SAHIBI yukaridaki (0c) kisa devresidir (_izlenen_dosyalar
    # bos listede hata dondurur, nobetci "OLCULEMEDI" deyip ERKEN DONER; o dal zaten
    # fail-loud). Bu yuzden canlilik capasi BOS listeye DEGIL, bugun hicbir nobetcinin
    # KORUMADIGI vakaya nisan alir: KISMI (sparse) liste — git rc=0, liste DOLU ama
    # beklenenden DAR (sparse/partial checkout, yanlis ROOT, PATH'te git shim, bozuk
    # index). O halde tarama sessizce DARALIR ve kapi "temiz" der. Iki dal olculur:
    # (a) kapinin kendi yolunu icermeyen KISMI liste -> CANLILIK hatasi ZORUNLU,
    # (b) normal liste -> canlilik hatasi YOK (yanlis-pozitif nobeti).
    # Fikstur BILEREK Kural A'nin (her zaman kosan) fikstur fonksiyonunda durur:
    # Kural B'nin fikstur cagrisi silinse bile canlilik nobeti nobetsiz kalmasin.
    _kismi = "\0".join(["index.html", "README.md", "urunler.json"])
    _h, _ = ic_rapor_nobeti(kosucu=lambda: (0, _kismi, ""), fikstur=False)
    if not any("CANLILIK" in x for x in _h):
        hatalar.append("CANLILIK NOBETI OLDU: kapinin KENDI yolunu icermeyen KISMI "
                       "liste (sparse/partial checkout) sessiz YESIL'e donmus")
    _tam = "\0".join(["index.html", "README.md", "urunler.json", KAPI_YOLU])
    _h, _ = ic_rapor_nobeti(kosucu=lambda: (0, _tam, ""), fikstur=False)
    if any("CANLILIK" in x for x in _h):
        hatalar.append("CANLILIK NOBETI YANLIS-POZITIF: normal listede canlilik "
                       "hatasi uretti -> %r" % _h)
    # (0d) CAPRAZ CANLILIK — KURAL B'nin YARGISI canli mi?
    # BILEREK Kural A'nin (HER ZAMAN kosan) fikstur fonksiyonunda durur. OLCULDU
    # (mutasyon D3, TUZAK): Kural B'nin fikstur cagrisini
    # `hatalar.extend(kok_belge_fikstur_hatalari())` ile YARGISINI birlikte oldurmek
    # Kural B'yi TAMAMEN sessizlestiriyordu — kendi fiksturleri de susturuldugu icin
    # kimse fark etmiyordu ve kokteki gercek bir sizinti YESIL geciyordu.
    # Bu iki satirlik capraz prob o tuzagi kapatir: Kural B'nin fikstur katmani
    # susturulsa bile yargisinin oldugu buradan gorulur.
    if not kok_belge_ihlali_mi("TESLIM-NOTU.md") or kok_belge_ihlali_mi("README.md"):
        hatalar.append("KURAL B YARGISI OLU/BOZUK: kok belge kapisi temel vakalari "
                       "ayirt edemiyor (TESLIM-NOTU.md YAKALANMALI, README.md "
                       "yakalanMAMALI) — Kural B sessizce devre disi kalmis olabilir")
    for yol, gerekce in _IC_RAPOR_KIRMIZI:
        if not ic_rapor_mu(yol):
            hatalar.append("FIKSTUR(kirmizi) KACTI — kural zayifladi: %s  [%s]"
                           % (yol, gerekce))
    for yol, gerekce in _IC_RAPOR_YESIL:
        if ic_rapor_mu(yol):
            hatalar.append("FIKSTUR(yesil) YANLIS-POZITIF — kural DARALTILMALI: %s  [%s]"
                           % (yol, gerekce))
    return hatalar


# ==================================================================================
# KOK BELGE KAPISI — AD-BAGIMSIZ IZIN LISTESI ("KURAL B", 27 Tem)
# ==================================================================================
# KURAL A'NIN ACIK KALAN DELIGI: A hala AD ekseninde calisir, sadece ailesi genis.
# Aile DISINDA bir ad secen rapor yine kacar. OLCULDU: ic_rapor_mu("TESLIM-NOTU.md")
# False dondurur (kok yok, sonek yok) -> Kural A ile YESIL gecerdi. Ayni sinif:
# NOTLAR.md, BULGULAR.md, OZET.md, HANDOFF.txt, worker-notu.md, devir.txt.
#
# KARAR (mimar): kok seviyede AD-BAGIMSIZ, fail-closed IZIN LISTESI. Kural B kokte
# ekseni ADdan KONUM+IZIN'e tasir; Kural A alt dizinlerde ad ailesiyle calismaya
# devam eder. Ikisi birlikte: kok -> ad ne olursa olsun yakalanir; alt dizin -> ad
# ailesiyle yakalanir. (Kanonik `.raporlar/` dizini SECILMEDI: dizini kullanmayi
# unutmak tam olarak uc kez olan hatanin kendisidir -> zorlayici degil.)
#
# NEDEN KOK GURULTUSUZ (mimar olcumu, git ls-files + git log --diff-filter=A):
#   * Bugun izlenen KOK belge dosyasi yalnizca README.md ve ege-bilgi.md
#     (kokte izlenen .txt/.markdown yok; kokte izlenen dosyalarin geri kalani
#     .gitignore/.driveignore/CNAME/index.html/urunler.json ve uc .js).
#   * Depo tarihinde kok .md EKLEME olaylarinin mesru olani yalniz bu iki dosya;
#     geri kalanlarin HEPSI ic rapor sizintisi (ONARIM-RAPORU.md, CURUTME-RAPORU.md,
#     CURUTME-RAPORU-TUR4.md, RAPOR-MIMARA.md).
#   * 3/3 gercek sizinti vakasi worktree KOKUNDE yazildi (worktree koku = repo koku).
#   Yani kokte yeni izlenen belge = tarihsel olarak COGUNLUKLA sizinti; mesru olay
#   cok seyrek -> TAM IZIN LISTESI gurultusuz kalir.
#
# KAPSAM SINIRI (BEYAN EDILEN KOR NOKTA): Kural B YALNIZ kokle sinirlidir. Alt
# dizindeki aile-disi bir ad (or. tools/TESLIM-NOTU.md) Kural A'ya da uymaz ->
# BILINCLI olarak yesil kalir. Alt dizine genisletmek tools/*.md mimar paketlerini
# (paket-*.md, taban-fiyat-tablosu.md, edge-katalog-tetik.md, ...) izin listesine
# doldurur; liste sisip bakimsiz kalir ve kapi OLUR. Yesil fiksturlerde isaretlidir.
#
# UZANTI SECIMI (TUR 2'de GENISLETILDI — her aday TEK TEK olculdu):
#   * Ilk surumde yalnizca .md/.markdown/.txt vardi; bagimsiz curutucu OLCTU ki
#     NOT.rst · NOT.org · TESLIM-NOTU.mdown · TESLIM-NOTU.text · TESLIM-NOTU.adoc
#     KACIYORDU. "Uzanti genisletmek yanlis-pozitif uretir" gerekcesi .html/.json/
#     uzantisiz icin DOGRU ama BELGE uzantilari icin GECERSIZDI.
#   * Asagidaki BELGE uzantilarinin her biri icin depo GENELINDE izlenen dosya
#     sayisi olculdu ve HEPSI SIFIR cikti -> hicbiri yanlis-pozitif uretemez.
#     (Olcum: git ls-files -z | uzantiya gore say. Yeni bir uzanti eklenmeden ONCE
#     ayni olcum TEKRARLANIR; sifir degilse EKLENMEZ.)
#
# 🔴 BEYAN EDILEN KAPSAM DISI (GERCEK yanlis-pozitif — bilincli birakildi):
#   KOD/VARLIK uzantilari kapsam DISIDIR: .html .json .js .css .xml .svg .ico
#   .jpg .png .webp. Sebep olculdu: kokte index.html + urunler.json + uc .js
#   IZLENIYOR (depo genelinde .json=48, .js=59, .html=5). Bunlari kapsama almak
#   kapiyi bloklayici bir yanlis-pozitife cevirir ve tum pruvo3d.com yayinini
#   durdurur. Dolayisiyla TESLIM-NOTU.html / TESLIM-NOTU.json KACAR — bilinen sinir.
# 🔴 IKINCI KAPSAM DISI: listede olmayan RASTGELE bir uzanti (TESLIM-NOTU.bak,
#   .note, .yaml) da kacar; kural uzanti IZIN listesiyle degil BELGE listesiyle
#   calisiyor (mimar karari). Kapatmak isteniyorsa eksen tersine cevrilmeli
#   (kod/varlik uzantilari DISINDA her sey ihlal) — ayri karar, ayri olcum.
#
# UZANTISIZ KOK DOSYALARI (TUR 2, D2): "TESLIM-NOTU" (uzantisiz) ve "NOT.md."
# (sondaki nokta) de kaciyordu. Artik kokte UZANTISIZ ya da NOKTAYLA BITEN her
# izlenen dosya ihlaldir; bugun izlenen uzantisiz kok dosyalarinin UCU DE
# (CNAME, .gitignore, .driveignore) izin listesine GEREKCEYLE alindi. Yeni bir
# uzantisiz kok dosyasinin (Makefile, LICENSE) kirmizi yakmasi DOGRU davranistir —
# gozden gecirilip gerekceyle listeye alinsin diye.
#
# VERI CAPASI YOK: kodda sabit dosya SAYISI / SHA / tarih iddiasi yoktur. Izin
# listesi ADlardan olusur. BAYAT giris BILEREK kirmizi DEGIL: listedeki bir dosya
# bir gun silinirse kapi kirmizi yanmamali (README.md silinirse yayin durmasin).
# Yalniz GEREKCESIZ giris kirmizidir — liste "neden" alani bos birakilarak curumesin.
KOK_BELGE_UZANTILARI = (
    ".md", ".markdown", ".txt",          # ilk surum
    ".mdown", ".mkd", ".text",           # markdown/metin lehceleri
    ".rst", ".org", ".adoc",             # reStructuredText / org-mode / asciidoc
    ".rtf", ".doc", ".docx", ".odt", ".pdf",   # ofis + tasinabilir belge
)

# IZIN LISTESI: yol -> GEREKCE. TAM AD ve HARF-DUYARLI esleme (liste kucuk ve kesin).
# ⚠️ CLAUDE.md / AGENTS.md BILEREK BURADA DEGIL: gitignore'dadirlar ve IZLENIR hale
# gelirlerse kirmizi yanmasi DOGRU davranistir (tedarikci adlari, uyelik bilgisi,
# WhatsApp numarasi, ticari mahremiyet kurali tasirlar).
# 🔴 DEVAM.md ISTISNASI (Okan karari, 31 Tem 2026): devralanin yarim isi gormesi icin
# IZLENIR yapildi; hassas bloklar DEVAM-ARSIV.md'ye (gitignore'da KALIR) tasindi. Bu
# giris SARTLIDIR — DEVAM.md'ye tedarikci adi/vitrin alan adi, iskonto-kur formulu,
# gizli dosya adi, sir envanteri ayrintisi, guvenlik bulgusu/kapi bypass'i YAZILMAZ.
# Kural B (ad ekseni) artik DEVAM.md'yi gecirir; ICERIK ekseni acik kalir (tedarikci
# nobetcisi izlenen dosyalarin icini tarar, DEVAM.md dahil).
KOK_BELGE_IZIN = {
    "README.md": "depo tanitim dosyasi — GitHub'da GORUNMESI amac, ic bilgi tasimaz",
    "ege-bilgi.md": "WhatsApp botu Ege'nin YAYINLANAN bilgi dosyasi (musteriye donen icerik)",
    "CNAME": "GitHub Pages ozel alan adi kaydi — uzantisiz, SILINIRSE yayin adresi duser",
    ".gitignore": "git yoksayma kurallari — uzantisiz (nokta-dosyasi), depo isleyisi icin sart",
    ".driveignore": "Drive yedekleme yoksayma kurallari — uzantisiz (nokta-dosyasi)",
    "DEVAM.md": "devir defteri — Okan karari 31 Tem 2026 IZLENIR; hassas blok DEVAM-ARSIV.md'de",
}


def _kok_uzanti(ad):
    """Katlanmis KOK dosya adindan uzantiyi cikarir. Bastaki noktalar ATILIR ki
    '.gitignore' UZANTILI degil UZANTISIZ sayilsin (bastaki nokta gizli-dosya
    isaretidir, uzanti degil). Doner:
      None -> govdede hic nokta YOK      (CNAME · Makefile · LICENSE · TESLIM-NOTU)
      "."  -> ad NOKTAYLA BITIYOR        (NOT.md. — olculmus kacis denemesi)
      ".x" -> normal uzanti              (.md · .rst · .html · .json)
    """
    govde = ad.lstrip(".")
    if "." not in govde:
        return None
    return "." + govde.rsplit(".", 1)[-1]


def kok_belge_ihlali_mi(yol):
    """repo-gorece yol KOK seviyede IZINSIZ bir belge mi (AD-BAGIMSIZ yargi).

    Ihlal = (yolda '/' YOK) VE (izin listesinde DEGIL) VE
            (BELGE uzantisi  YA DA  uzantisiz  YA DA  noktayla biten ad).
    Uzanti tespiti Kural A'nin _ad_katla'siyla katlanir -> '.MD'/'.Md'/'.RST'
    kacamaz. Izin karsilastirmasi HAM yol uzerinde ve HARF-DUYARLI: 'readme.md'
    README.md'nin izninden yararlanamaz (fail-closed; supheli hal kirmizi).
      KIRMIZI: TESLIM-NOTU.md · NOT.rst · TESLIM-NOTU (uzantisiz) · NOT.md. · OZET.md
      YESIL  : README.md · CNAME · .gitignore · index.html · tools/paket-x.md
    """
    if "/" in yol:
        return False
    if yol in KOK_BELGE_IZIN:
        return False
    uzanti = _kok_uzanti(_ad_katla(yol))
    if uzanti is None:
        return True   # UZANTISIZ kok dosyasi -> gozden gecirilsin (fail-closed)
    if uzanti == ".":
        return True   # ad noktayla bitiyor -> uzanti kacisi denemesi
    return uzanti in KOK_BELGE_UZANTILARI


def kok_belge_isabetleri(yollar):
    """Yol listesi -> kokte IZINSIZ belge yollari, sirali.
    GERCEK tarama ve fikstur oz-kontrolu AYNI fonksiyonu kullanir: biri oldurulurse
    (or. 'return []') fikstur oz-kontrolu de kirmizi yanar (olu tarayici korumasi)."""
    return sorted(y for y in yollar if kok_belge_ihlali_mi(y))


# --- KIRMIZI FIKSTURLER: Kural B zayiflatilirsa bunlar KACAR -> kapi kirmizi.
_KOK_BELGE_KIRMIZI = [
    ("TESLIM-NOTU.md", "MIMAR SARTI: Kural A'nin KACIRDIGI ad (kok yok, sonek yok)"),
    ("TESLIM-NOTU.markdown", "ayni ad, uzanti degistirerek kacis"),
    ("TESLIM-NOTU.MD", "BUYUK HARF uzanti — _ad_katla katlamasi olmazsa kacar"),
    ("NOTLAR.md", "aile-disi genel ad"),
    ("BULGULAR.md", "aile-disi genel ad"),
    ("OZET.md", "aile-disi genel ad"),
    ("HANDOFF.txt", "aile-disi ad + .txt uzantisi"),
    ("worker-notu.md", "isci kimligi tasiyan kucuk-harf ad"),
    ("devir.txt", "aile-disi ad + .txt uzantisi"),
    ("readme.md", "HARF-DUYARLI izin: kucuk harf hali README.md izninden yararlanamaz"),
    ("ONARIM-RAPORU.md", "27 Tem gercek kacak — B de yakalamali (A'ya bagimli kalmasin)"),
    ("CURUTME-RAPORU.md", "27 Tem gercek kacak — B de yakalamali"),
    ("RAPOR-MIMARA.md", "protokol adi; gitignore'da ama IZLENIRSE B de yakalamali"),
    # --- TUR 2 / D1: bagimsiz curutucunun GERCEK dosya + gercek 'git add' ile
    # KACTIGINI olctugu uzantilar. Her birinin depo genelinde izlenen sayisi 0.
    ("NOT.rst", "D1 olculmus kacak: reStructuredText"),
    ("NOT.org", "D1 olculmus kacak: org-mode"),
    ("TESLIM-NOTU.mdown", "D1 olculmus kacak: markdown lehcesi"),
    ("TESLIM-NOTU.text", "D1 olculmus kacak: .text"),
    ("TESLIM-NOTU.adoc", "D1 olculmus kacak: asciidoc"),
    ("TESLIM-NOTU.pdf", "D1: disa aktarilmis rapor (PDF ic olcum tasir)"),
    ("TESLIM-NOTU.docx", "D1: ofis belgesi"),
    ("NOT.mkd", "D1: markdown lehcesi"),
    ("NOT.rtf", "D1: zengin metin"),
    ("NOT.doc", "D1: eski ofis belgesi"),
    ("NOT.odt", "D1: acik ofis belgesi"),
    ("TESLIM-NOTU.RST", "D1 + BUYUK HARF uzanti (katlama olmazsa kacar)"),
    # --- TUR 2 / D2: uzantisiz ve noktayla biten kok adlari.
    ("TESLIM-NOTU", "D2 olculmus kacak: UZANTISIZ kok dosyasi"),
    ("NOT.md.", "D2 olculmus kacak: ad NOKTAYLA bitiyor (uzanti kacisi)"),
    ("HANDOFF", "D2: uzantisiz ikinci vaka"),
]

# --- YESIL FIKSTURLER: "ILGISIZ RUTIN DUZENLEME YESIL KALIR". Bu kapi BLOKLAYICI —
# bir yanlis-pozitif TUM pruvo3d.com yayinini durdurur. Ilk grup KOKTE GERCEKTEN
# IZLENEN dosyalardir (uzanti genisletilirse yanarlar), ikinci grup ALT DIZIN.
_KOK_BELGE_YESIL = [
    ("README.md", "IZIN LISTESI: depo tanitimi"),
    ("ege-bilgi.md", "IZIN LISTESI: yayinlanan bot bilgi dosyasi"),
    ("index.html", "OLCULDU: kokte izlenen — uzanti genisletilirse yanar"),
    ("urunler.json", "OLCULDU: kokte izlenen — TUM katalog"),
    ("CNAME", "IZIN LISTESI: kokte izlenen UZANTISIZ dosya (D2 sonrasi izin sart)"),
    ("konfigur.js", "OLCULDU: kokte izlenen"),
    ("secenekler.js", "OLCULDU: kokte izlenen"),
    ("attribution-ref.js", "OLCULDU: kokte izlenen"),
    (".gitignore", "IZIN LISTESI: kokte izlenen UZANTISIZ nokta-dosyasi"),
    (".driveignore", "IZIN LISTESI: kokte izlenen UZANTISIZ nokta-dosyasi"),
    ("filamentler.json", "RUTIN: filament envanteri guncellemesi"),
    # 🔴 BEYAN EDILEN KAPSAM DISI (GERCEK yanlis-pozitif riski yuzunden birakildi —
    # yukaridaki "KAPSAM DISI" notuna bak). Bunlar KACAR ve bu BILINCLIDIR:
    # kokte index.html + urunler.json + uc .js IZLENIYOR; kod/varlik uzantilarini
    # kapsama almak kapiyi bloklayici yanlis-pozitife cevirir.
    ("TESLIM-NOTU.html", "KOR NOKTA: kod/varlik uzantisi — BILINCLI yesil"),
    ("TESLIM-NOTU.json", "KOR NOKTA: kod/varlik uzantisi — BILINCLI yesil"),
    ("TESLIM-NOTU.bak", "KOR NOKTA: listede olmayan RASTGELE uzanti — BILINCLI yesil"),
    ("tools/paket-shop-odeme.md", "ALT DIZIN — Kural B kapsami degil (mimar paketi)"),
    ("jenerator/KURULUM.md", "ALT DIZIN — mesru kurulum belgesi"),
    ("shop/KURULUM.md", "ALT DIZIN — mesru kurulum belgesi"),
    ("tools/arsiv/README.md", "ALT DIZIN — derin yol"),
    ("tools/sayfalar.py", "ALT DIZIN + belge olmayan uzanti"),
    # 🔴 BEYAN EDILEN KOR NOKTA (bilincli kapsam siniri — mimar karari, yukaridaki
    # "KAPSAM SINIRI" notuna bak): alt dizindeki aile-disi ad ne Kural A'ya ne
    # Kural B'ye takilir, YESIL gecer. Genisletme yapilmadi cunku tools/*.md mimar
    # paketleri izin listesini sisirir -> liste bakimsiz kalir, kapi OLUR.
    # 3/3 gercek sizinti vakasi KOKTE yazildi; koru kapatmak vakalarin %100'unu kapatir.
    ("tools/TESLIM-NOTU.md", "KOR NOKTA: alt dizinde aile-disi ad — BILINCLI yesil"),
]


def _ihlal_yolu(mesaj):
    """Nobetci hata mesajindan ihlal edilen YOLU cikarir (E2E fiksturu icin).
    ⚠️ Naif 'yol in mesaj' testi YASAK: her iki hata mesaji da COZUM metninde
    'RAPOR-MIMARA.md' gecirir -> substring testi HER mesaji RAPOR-MIMARA ihlali
    sanar (olculdu: 4 ihlal 'TAM 1 mesaj' testinden sahte gecerdi)."""
    for onek in ("IZLENEN IC RAPOR: ", "KOK BELGE IZINSIZ: "):
        if mesaj.startswith(onek):
            return mesaj[len(onek):].split(" ", 1)[0]
    return None


def kok_belge_fikstur_hatalari():
    """Kural B'nin KENDI hukmunu + git ciktisindan hata mesajina kadar ZINCIRI olcer
    (olu nobetci + asiri-genisleme korumasi). Bellekte calisir, diske/aga DOKUNMAZ."""
    hatalar = []
    # (0) TARAYICI OZ-KONTROLU: yol listesi -> isabet eslemesi CANLI mi.
    _sentetik = ["index.html", "README.md", "tools/paket-x.md",
                 "TESLIM-NOTU.md", "NOTLAR.txt", "alt/dizin/OZET.md"]
    _beklenen = ["NOTLAR.txt", "TESLIM-NOTU.md"]
    _bulunan = kok_belge_isabetleri(_sentetik)
    if _bulunan != _beklenen:
        hatalar.append("KOK TARAYICI OLU/BOZUK: sentetik yol listesinde beklenen %r "
                       "yerine %r bulundu" % (_beklenen, _bulunan))
    # (1) UCTAN UCA ENJEKSIYON: sahte 'git ls-files -z' ciktisi verilir; git
    #     ciktisindan HATA MESAJINA kadar zincir olculur (saf fonksiyon degil).
    #     Ozyineleme kapisi: fikstur=False. Sayilar SENTETIK listenin kendisinden
    #     gelir — depo verisine capa DEGIL (katalog buyuse de degismez).
    # KAPI_YOLU listede SART: canlilik nobeti (D3) aksi halde hakli olarak durdurur;
    # bu ayni zamanda canlilik nobetinin normal listede yanlis-pozitif URETMEDIGINI
    # de uctan uca gosterir.
    _sahte_yollar = ["README.md", "ege-bilgi.md", "tools/paket-x.md", "index.html",
                     KAPI_YOLU, "TESLIM-NOTU.md", "ONARIM-RAPORU.md",
                     "CURUTME-RAPORU.md", "RAPOR-MIMARA.md"]
    _bekle_ihlal = sorted(["TESLIM-NOTU.md", "ONARIM-RAPORU.md",
                           "CURUTME-RAPORU.md", "RAPOR-MIMARA.md"])
    _h, _n = ic_rapor_nobeti(kosucu=lambda: (0, "\0".join(_sahte_yollar), ""),
                             fikstur=False)
    if _n != len(_sahte_yollar):
        hatalar.append("E2E: taranan dosya sayisi %d yerine %r (git ciktisi "
                       "ayristirilamiyor)" % (len(_sahte_yollar), _n))
    _bulunan_ihlal = sorted(y for y in (_ihlal_yolu(m) for m in _h) if y)
    if _bulunan_ihlal != _bekle_ihlal:
        hatalar.append("E2E: ihlal yollari %r beklenirken %r bildirildi "
                       "(kural zayifladi ya da yanlis-pozitif uretti)"
                       % (_bekle_ihlal, _bulunan_ihlal))
    if len(_h) != len(_bekle_ihlal):
        hatalar.append("E2E: TAM %d ihlal mesaji beklenirken %d mesaj uretildi -> %r"
                       % (len(_bekle_ihlal), len(_h), _h))
    # (2) FIKSTUR HUKUMLERI
    for yol, gerekce in _KOK_BELGE_KIRMIZI:
        if not kok_belge_ihlali_mi(yol):
            hatalar.append("KOK FIKSTUR(kirmizi) KACTI — kural zayifladi: %s  [%s]"
                           % (yol, gerekce))
    for yol, gerekce in _KOK_BELGE_YESIL:
        if kok_belge_ihlali_mi(yol):
            hatalar.append("KOK FIKSTUR(yesil) YANLIS-POZITIF — kural DARALTILMALI: "
                           "%s  [%s]" % (yol, gerekce))
    return hatalar


# ---------------------------------------------------------------- CANLILIK CAPASI (TUR 2 / D3)
# OLCULDU (bagimsiz curutucu): `git ls-files` rc=0 dondugu halde BOS ya da KISMI
# liste verdiginde kapi "YESIL — 0 izlenen dosya tarandi" basip exit 0 veriyordu.
# Yani TARAMA HIC YAPILMAMISKEN kapi gecmis sayiliyordu (sizinti kapisi icin en
# tehlikeli hal: sessiz yesil). Gercek tetikleyiciler: sparse/partial checkout,
# yanlis ROOT cozumu, PATH'te bir `git` shim'i, bozuk index.
# NOBET: liste KAPININ KENDI YOLUNU icermiyorsa tarama YAPILMAMIS sayilir ->
# OLCULEMEDI sinifi hata + exit 1. Kural A ve Kural B'yi BIRLIKTE korur (ortak
# tarama noktasinda durur).
# ⚠️ BU VERI CAPASI DEGILDIR: sabit dosya SAYISI / SHA / tarih iddiasi yok, esik
# yok. Yalnizca "kapinin kendi dosyasi izleniyor mu" sorulur; katalog buyudukce
# ya da kuculdukce degismez. (Dosya sayisi esigi KOYULMADI — o veri capasi olurdu.)
KAPI_YOLU = "tools/kisisel-veri-test.py"


def _git_ls_files():
    """Gercek kosucu: (returncode, stdout, stderr). Ag/Drive/canli uc YOK, yalniz yerel git."""
    try:
        r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"],
                           capture_output=True, text=True)
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr


def _izlenen_dosyalar(kosucu=None):
    """(yollar, hata_metni). kosucu enjekte edilebilir -> fail-loud fiksturu icin.

    🔴 BOS KAPSAM = OLCULEMEDI (30 Tem, kusur 4): git rc=0 dondurup BOS cikti
    verdiginde (yanlis kok, bozuk indeks, ls-files'in sessizce hicbir sey gormedigi
    her hal) eski surum 'taranan: 0' ile YESIL yaniyordu — yani tarama hicbir dosya
    gormezse kapi 'temiz' diyordu. Bu, gecmis ekseni kusurunun tam kardesi:
    KAPSAM BOSSA NOBETCI YOKMUS GIBI DAVRANIR. Bu depoda izlenen dosya sayisi hicbir
    zaman 0 olamaz (kaynak kodun kendisi izlenir) -> bos cikti KIRMIZIDIR.
    Not: bu bir VERI CAPASI DEGILDIR (sabit sayi/SHA iddiasi yok); yalniz 'kapsam
    bos olamaz' kurali."""
    rc, cikti, hata = (kosucu or _git_ls_files)()
    if rc != 0:
        return None, "git ls-files basarisiz (rc=%s): %s" % (rc, (hata or "").strip() or "?")
    yollar = [y for y in cikti.split("\0") if y]
    if not yollar:
        return None, ("git ls-files BOS liste dondurdu (rc=0) — taranacak izlenen dosya "
                      "YOK. Bu depoda bu imkansizdir; kapsam kaybolmus demektir "
                      "(yanlis kok / bozuk indeks). Bos kapsam SESSIZ YESIL SAYILMAZ.")
    return yollar, None


def ic_rapor_nobeti(kosucu=None, fikstur=True):
    """(hatalar, taranan_dosya_sayisi) dondurur.

    KURAL A (ad ailesi, dizinden bagimsiz) ve KURAL B (kok seviye izin listesi)
    AYNI `git ls-files -z` ciktisi uzerinde kosar — IKINCI git cagrisi ACILMAZ, boylece
    fail-loud (OLCULEMEDI) davranisi Kural B'ye bedavaya miras kalir.
    fikstur=False YALNIZ ic fiksturlerin kendini cagirmasi icindir (ozyineleme kapisi)."""
    hatalar = ic_rapor_fikstur_hatalari() if fikstur else []
    if fikstur:
        hatalar.extend(kok_belge_fikstur_hatalari())

    for yol, gerekce in IC_RAPOR_ISTISNA.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ istisna girisi: %s" % yol)
        elif not ic_rapor_mu(yol):
            hatalar.append("BAYAT istisna (artik aileye uymuyor — listeden sil): %s" % yol)

    # Kural B izin listesi: gerekce ZORUNLU. BAYAT giris (dosya artik yok) BILEREK
    # kirmizi DEGIL — veri capasi yasagi (README.md silinirse yayin durmamali).
    for yol, gerekce in KOK_BELGE_IZIN.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ kok belge izni: %s" % yol)

    yollar, hata = _izlenen_dosyalar(kosucu)
    if hata:
        # FAIL-LOUD: olculecek sey yoksa sessiz yesil VERILMEZ (sizinti kapisi).
        hatalar.append("OLCULEMEDI — %s" % hata)
        return hatalar, 0
    if KAPI_YOLU not in yollar:
        # CANLILIK: git rc=0 dedi ama liste BOS/KISMI -> tarama yapilmadi sayilir.
        hatalar.append(
            "OLCULEMEDI (CANLILIK) — izlenen dosya listesi kapinin KENDI yolunu (%s) "
            "icermiyor: git basarili dondu ama liste BOS ya da KISMI (sparse/partial "
            "checkout, yanlis ROOT, PATH'te git shim, bozuk index). rc=0 geldi diye "
            "SESSIZ YESIL verilmez." % KAPI_YOLU)
        return hatalar, len(yollar)

    a_isabet = ic_rapor_isabetleri(yollar)
    for yol in a_isabet:
        hatalar.append(
            "IZLENEN IC RAPOR: %s — PUBLIC repoya girer (kapi bypass yollari / dal-ajan "
            "kimlikleri / ic olcum). Cozum: git rm --cached '%s' + adi RAPOR-MIMARA.md yap."
            % (yol, yol))
    # Kural B: ayni dosya iki kez BILDIRILMEZ (tek ihlal = tek mesaj); A zaten
    # yakaladiysa onun cozum metni gecerlidir.
    a_kume = set(a_isabet)
    for yol in kok_belge_isabetleri(yollar):
        if yol in a_kume:
            continue
        hatalar.append(
            "KOK BELGE IZINSIZ: %s — PUBLIC repo koku izin listesiyle korunuyor. "
            "Cozum: (a) ic rapor ise 'git rm --cached %s' + adi RAPOR-MIMARA.md yap "
            "(gitignore'da, izlenmez); (b) gercekten yayinlanacak bir belge ise "
            "KOK_BELGE_IZIN'e GEREKCEYLE ekle." % (yol, yol))
    return hatalar, len(yollar)


# ==================================================================================
# GECMIS EKSENI — COMMIT ARALIGINDA *EKLENEN* DOSYALAR (30 Tem, 4. KACAK)
# ==================================================================================
# 🔴 KOK NEDEN (olculdu 30 Tem): yukaridaki ic_rapor_mu() DOGRU calisiyordu — hem
# RAPOR-MIMARA.md hem tools/yedek-topolojisi-raporu.md icin True donuyor. Sorun TANIMA
# degil KAPSAM idi: nobetci yalniz `git ls-files` = MEVCUT CALISMA AGACINI tariyordu.
# Bir dosya eklenip AYNI GUN silinirse calisma agaci tertemiz olur, nobetci hicbir sey
# gormez — ama commit'ler KALICIDIR. Depo PUBLIC (Pruvo138/pruvo): silinmis dosyanin
# blob'u raw.githubusercontent.com'dan anonim olarak HALA cekilebilir.
#
# OLCULMUS OLAY: tools/yedek-topolojisi-raporu.md 2b6373ec ile eklendi, d058a11c ile
# cikarildi (ikisi de 21 Tem, ikisi de origin/main'in ATASI) -> bugun hala anonim
# HTTP 200. Ayni sinif hata bundan once UC kez yasandi; bu 4.'su ve main'e girdi.
# Ilk tarama origin/main gecmisinde UC kayit buldu (tek degil): 2b6373ec + iki
# ONARIM-RAPORU.md commit'i (1138da5b, 3bc7a965). Bu tur o kayitlari TEMIZLEMEZ
# (gecmis yeniden yazma = Okan kapisi); yalniz YENI kacagi durdurur ve raporlar.
#
# EKSEN: `git log --diff-filter=A` = "bu aralikta EKLENEN dosya yollari". Silinmis
# olmasi umursanmaz — sizinti EKLENDIGI anda olusur.
#
# KURAL AYNI FONKSIYONDAN GECER: ic_rapor_mu() + IC_RAPOR_ISTISNA yeniden yazilmadi,
# KULLANILDI. Boylece yanlis-pozitif yuzeyi calisma-agaci koluyla BIREBIR ayni kalir
# (ayni yesil/kirmizi fikstur ailesi iki kolu da korur).
#
# NEREYE BAGLANDI: PRE-PUSH KANCASI (kurulum: tools/gecmis-nobeti-hook-kur.py).
# CI'ya BAGLANMADI, iki OLCULMUS sebeple:
#   1) deploy.yml `actions/checkout@v4`i fetch-depth VERMEDEN kullanir -> SIG (depth=1)
#      klon: `origin/main..HEAD` gibi bir aralik CI'da COZULEMEZ, taranacak gecmis YOK.
#   2) deploy.yml `on: push: branches: [main]` -> yalniz main'e, yalniz PUSH'TAN SONRA
#      kosar. O anda commit ZATEN public remote'tadir; yayini durdurmak sizmis blob'u
#      geri getirmez. 27 Tem'in iki kacagi da DAL push'unda olmustu — CI o dallari
#      hic gormez. Bu eksenin tum degeri ONLEMEDIR -> kapi push'tan ONCE olmali.
# Bunun bedeli: kanca .git/hooks altinda yasar ve GIT'E GIRMEZ -> her makinede
# `python3 tools/gecmis-nobeti-hook-kur.py` ile kurulur; kurulu mu, asagidaki
# varsayilan kosumun son satiri soyler.
#
# CI'DA NE KOSAR: gecmis_fikstur_hatalari() — GERCEK git ile GECICI bir depo kurup
# "ekle + ayni aralikta sil" olayini yeniden oynatir (bicim capasi: kanned metin
# gercek git ciktisindan kayarsa yakalanir) + 4 kirmizi/12 yesil kanned senaryo.
# Yani parser/kural/gercek-git zinciri CI'da nobetsiz KALMAZ; nobetsiz kalan tek
# halka kancanin KENDISIDIR (commit edilemez).

_GECMIS_AYRAC = "\x02"        # commit basligi oneki (git log --format=%x02%H)


def gecmis_ayristir(ham):
    """`git log --format=%x02%H --name-only -z --diff-filter=A` ciktisi -> [(sha, yol)].

    GERCEK BICIM (olculdu): '\\x02<sha>\\x00\\n<yol>\\x00<yol>\\x00\\x02<sha>\\x00\\n...'
    Eklenen dosyasi OLMAYAN commit git tarafindan hic basilmaz. Bu ayristirici
    kanned fiksturlerle DEGIL, gecici GERCEK depo fiksturuyle capalanir (asagida)."""
    kayitlar = []
    for blok in (ham or "").split(_GECMIS_AYRAC):
        if not blok:
            continue
        parcalar = blok.split("\0")
        sha = parcalar[0].strip()
        if not sha:
            continue
        for yol in parcalar[1:]:
            yol = yol.strip("\n")
            if yol:
                kayitlar.append((sha, yol))
    return kayitlar


def gecmis_isabetleri(ham):
    """Ham git ciktisi -> ic rapor ailesine uyan (istisna DISI) (sha, yol) isabetleri.

    GERCEK tarama ve fikstur oz-kontrolu AYNI fonksiyonu kullanir: govdesi no-op
    yapilirsa (or. 'return []') fikstur oz-kontrolu de kirmizi yanar."""
    return sorted(set((sha, yol) for sha, yol in gecmis_ayristir(ham)
                      if ic_rapor_mu(yol) and yol not in IC_RAPOR_ISTISNA))


def _git_log_eklenen(kapsam, kok=None):
    """Gercek kosucu: (rc, stdout, stderr). Ag YOK, yalniz yerel git nesneleri.
    kapsam = git rev-list argumanlari listesi (or. ['origin/main..HEAD'] ya da ['--all'])."""
    try:
        r = subprocess.run(
            ["git", "-C", kok or ROOT, "log", "--no-renames", "--diff-filter=A",
             "--name-only", "-z", "--format=%x02%H"] + list(kapsam),
            capture_output=True, text=True)
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr


def gecmis_tara(kapsam, kosucu=None, kok=None):
    """(isabetler, hata_metni). Fail-loud: git patlarsa SESSIZ YESIL VERILMEZ."""
    rc, cikti, hata = (kosucu or _git_log_eklenen)(kapsam, kok)
    if rc != 0:
        return None, ("git log --diff-filter=A basarisiz (rc=%s, kapsam=%s): %s"
                      % (rc, " ".join(kapsam), (hata or "").strip() or "?"))
    return gecmis_isabetleri(cikti), None


# ---------------------------------------------------------------- kanned fiksturler
def _gc(*commitler):
    """(sha, [yollar]) ciftlerinden GERCEK git -z bicimini taklit eder (bkz. gecmis_ayristir)."""
    parca = []
    for sha, yollar in commitler:
        if not yollar:
            continue            # git eklenen dosyasi olmayan commit'i hic basmaz
        parca.append(_GECMIS_AYRAC + sha + "\0\n" + "\0".join(yollar) + "\0")
    return "".join(parca)


# KIRMIZI: bu aralikleri kacirirsak sizinti PUBLIC repoya girer.
_GECMIS_KIRMIZI = [
    ("GERCEK OLAY (21 Tem): ekle -> AYNI GUN sil; calisma agaci kolu SESSIZ kalir",
     _gc(("2b6373ec80fa232cea88a7db5166576ef9ed624c",
          ["tools/yedek-topolojisi-raporu.md"]),
         ("d058a11c00000000000000000000000000000000", [])),
     [("2b6373ec80fa232cea88a7db5166576ef9ed624c",
       "tools/yedek-topolojisi-raporu.md")]),
    ("protokol adi RAPOR-MIMARA.md dal push'unda eklenmis",
     _gc(("a" * 40, ["tools/build.py", "RAPOR-MIMARA.md"])),
     [("a" * 40, "RAPOR-MIMARA.md")]),
    ("27 Tem 1./2. kacak sinifi — alt dizinde + tiresiz kucuk harf",
     _gc(("b" * 40, ["alt/dizin/CURUTME-RAPORU.md"]), ("c" * 40, ["curutme.md"])),
     [("b" * 40, "alt/dizin/CURUTME-RAPORU.md"), ("c" * 40, "curutme.md")]),
    ("iki commit: once eklendi, sonra silindi — sadece EKLEME kaydi kalir",
     _gc(("d" * 40, ["ONARIM-RAPORU.md", "urunler.json"]),
         ("e" * 40, ["tools/yeni.py"])),
     [("d" * 40, "ONARIM-RAPORU.md")]),
]

# YESIL: 12 MESRU push senaryosu. Bu kol BLOKLAYICI — bir yanlis-pozitif TUM
# ekibin push'unu durdurur, o yuzden yuzey olculerek genis tutuldu.
_GECMIS_YESIL = [
    ("MESRU 1: normal kod commit'i (site kodu + arac)",
     _gc(("11" * 20, ["tools/build.py", "index.html", "konfigur.js"]))),
    ("MESRU 2: urun partisi (MaCiT dilimi)",
     _gc(("12" * 20, ["urunler.json"]), ("13" * 20, ["urunler.json"]))),
    ("MESRU 3: .md belge guncellemesi (izlenen mimar paketleri)",
     _gc(("14" * 20, ["tools/paket-shop-odeme.md", "tools/URUN-EKLEME-REHBERI.md",
                      "README.md", "tools/arsiv/README.md"]))),
    ("MESRU 4: gitignore'lu dosya (CLAUDE.md/DEVAM.md/RAPOR-MIMARA.md izlenmez) -> "
     "git log'da HIC gorunmez, cikti bos",
     _gc()),
    ("MESRU 5: raporlar/ altindaki IZLENMEYEN dosya -> commit'e girmez, cikti bos",
     _gc(("15" * 20, []))),
    ("MESRU 6: yeni/duzenlenen yasal sayfa",
     _gc(("16" * 20, ["mesafeli-satis/index.html", "tools/sayfalar.py"]))),
    ("MESRU 7: tools/ icinde yeni .py kapisi + kabul testi",
     _gc(("17" * 20, ["tools/yeni-kapisi.py", "tools/denetim-kapisi-test.py"]))),
    ("MESRU 8: filament envanteri + fiyat tablosu",
     _gc(("18" * 20, ["filamentler.json", "tools/taban-fiyat-tablosu.md"]))),
    ("MESRU 9: 'olcum/denetim' ADLI mesru kod dosyalari (olculdu FP sinifi)",
     _gc(("19" * 20, ["shop/src/olcum.js", "shop/test/olcum.mjs",
                      "shop/test/olcum-kapisi.cjs", "tools/denetim-kapisi.py"]))),
    ("MESRU 10: turev kelimeler (onek AYIRAC SARTLI olmali)",
     _gc(("1a" * 20, ["raporlama.md", "onarimlar.md", "denetimsiz-liste.md",
                      "tools/paket-olcumleme.md"]))),
    ("MESRU 11: bos aralik (push edilecek yeni commit yok)",
     ""),
    ("MESRU 12: karisik buyuk parti (urun + kod + belge + jenerator)",
     _gc(("1b" * 20, ["urunler.json", "tools/d1-sync.py", "jenerator/KURULUM.md",
                      "jenerator/test/SOZLESME.md", "ege-bilgi.md",
                      "olcuye-ozel-yeni-parca-uretimi/index.html"]))),
]


def _gecmis_gercek_depo_fiksturu():
    """BICIM CAPASI: GERCEK git ile gecici bir depo kurup 21 Tem olayini yeniden oynatir.

    Neden kanned metin YETMEZ: fikstur metni gercek `git log -z` bicimindan kayarsa
    (git surumu / bayrak degisikligi) ayristirici kanned metni okumaya devam eder ve
    kapi CANLI ARALIKTA sessizce bos doner. Bu fikstur ayristiriciyi GERCEK git
    ciktisina capalar. Ag YOK, imza YOK, tempdir disina yazmaz, ~0,2 sn."""
    hatalar = []
    ortam = dict(os.environ)
    ortam.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                  "GIT_TERMINAL_PROMPT": "0"})
    # ⚠️ `-c` GIT SEVIYESI bir bayraktir: alt komuttan ONCE gelmeli. (Olculdu: alt
    # komuttan sonra verilince `git init` sessizce kimliksiz kosuyor ve fikstur
    # deposu HIC commit almiyordu -> fikstur "yesil" gorunurken hicbir sey olcmuyordu.)
    kimlik = ["-c", "user.name=pruvo-fikstur", "-c", "user.email=fikstur@example.invalid",
              "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]

    def g(kok, *a):
        return sentetik_git(kok, *a, ayarlar=tuple(kimlik[4:]),
                             capture_output=True, text=True,
                             kimlik_ad="pruvo-fikstur",
                             kimlik_eposta="fikstur@example.invalid")

    try:
        with tempfile.TemporaryDirectory(prefix="pruvo-gecmis-fikstur-") as d:
            r = sentetik_git(d, "init", "-q", ayarlar=tuple(kimlik[4:]),
                              capture_output=True, text=True,
                              kimlik_ad="pruvo-fikstur",
                              kimlik_eposta="fikstur@example.invalid")
            if r.returncode != 0:
                return ["OLCULEMEDI (gecmis bicim capasi) — git init: %s"
                        % (r.stderr or "").strip()]
            # taban commit (aralik disi)
            with open(os.path.join(d, "index.html"), "w") as f:
                f.write("<p>taban</p>\n")
            g(d, "add", "-A")
            g(d, "commit", "-q", "-m", "taban")
            taban = g(d, "rev-parse", "HEAD").stdout.strip()
            if len(taban) < 7:
                return ["OLCULEMEDI (gecmis bicim capasi) — fikstur deposunda taban "
                        "commit olusmadi (git kimligi/izin?): %r" % taban]
            # (1) IC RAPOR + iki mesru dosya AYNI commit'te eklenir (cok dosyali bicim)
            for ad, icerik in [("RAPOR-MIMARA.md", "ic rapor govdesi\n"),
                               ("tools/yeni-kapisi.py", "# kapi\n"),
                               ("urunler.json", "[]\n")]:
                tam = os.path.join(d, ad)
                os.makedirs(os.path.dirname(tam), exist_ok=True) if "/" in ad else None
                with open(tam, "w") as f:
                    f.write(icerik)
            g(d, "add", "-A")
            g(d, "commit", "-q", "-m", "ekle")
            ekleyen = g(d, "rev-parse", "HEAD").stdout.strip()
            # (2) AYNI ARALIKTA silinir -> calisma agaci TERTEMIZ olur
            os.remove(os.path.join(d, "RAPOR-MIMARA.md"))
            g(d, "add", "-A")
            g(d, "commit", "-q", "-m", "izlemeden cikar")

            # (a) ONCE-KIRMIZI KANITI: calisma agaci kolu (git ls-files) SESSIZ mi?
            ls = g(d, "ls-files", "-z")
            agac_yollar = [y for y in ls.stdout.split("\0") if y]
            if ic_rapor_isabetleri(agac_yollar):
                hatalar.append(
                    "GECMIS FIKSTURU GECERSIZ: calisma agaci kolu bu senaryoda ZATEN "
                    "kirmizi yaniyor -> fikstur 'gecmis eksenini' olcmuyor (yollar=%r)"
                    % agac_yollar)
            # (b) SONRA-KIRMIZI: gecmis kolu GERCEK git ile yakalamali
            isabet, hata = gecmis_tara(["%s..HEAD" % taban], kok=d)
            if hata:
                hatalar.append("OLCULEMEDI (gecmis bicim capasi) — %s" % hata)
            elif isabet != [(ekleyen, "RAPOR-MIMARA.md")]:
                hatalar.append(
                    "GECMIS KOLU OLU/BOZUK (GERCEK git): silinmis RAPOR-MIMARA.md "
                    "aralikta yakalanmadi — beklenen %r, bulunan %r"
                    % ([(ekleyen, "RAPOR-MIMARA.md")], isabet))
            # (c) DARLIK: mesru dosyalar ayni ciktida YANMAMALI (yukarida zaten
            #     tek isabet bekleniyor; burada ciktinin cok-dosyali oldugunu teyit et)
            rc, ham, _ = _git_log_eklenen(["%s..HEAD" % taban], kok=d)
            tum = [y for _s, y in gecmis_ayristir(ham)]
            if rc == 0 and not {"tools/yeni-kapisi.py", "urunler.json"} <= set(tum):
                hatalar.append(
                    "AYRISTIRICI COK-DOSYALI COMMIT'I OKUYAMIYOR: gercek git ciktisinda "
                    "beklenen mesru yollar yok (bulunan=%r)" % tum)
    except OSError as e:
        hatalar.append("OLCULEMEDI (gecmis bicim capasi) — %s" % e)
    return hatalar


def gecmis_fikstur_hatalari():
    """Nobetcinin KENDI hukmunu olcer (olu nobetci + asiri-genisleme korumasi)."""
    hatalar = []
    for ad, ham, beklenen in _GECMIS_KIRMIZI:
        bulunan = gecmis_isabetleri(ham)
        if bulunan != sorted(beklenen):
            hatalar.append("GECMIS FIKSTUR(kirmizi) KACTI — kol olu/zayif: %s "
                           "[beklenen %r, bulunan %r]" % (ad, sorted(beklenen), bulunan))
    for ad, ham in _GECMIS_YESIL:
        bulunan = gecmis_isabetleri(ham)
        if bulunan:
            hatalar.append("GECMIS FIKSTUR(yesil) YANLIS-POZITIF — MESRU push "
                           "bloklanirdi: %s -> %r" % (ad, bulunan))
    # FAIL-LOUD: git patlayinca sessiz yesil VERILMEZ.
    _i, _h = gecmis_tara(["x..y"],
                         kosucu=lambda k, kok: (128, "", "fatal: bad revision"))
    if not _h:
        hatalar.append("FAIL-LOUD OLDU: git log basarisiz oldugunda gecmis kolu hata "
                       "uretmiyor (olculemeyen hal sessiz yesile donmus)")
    hatalar.extend(_gecmis_gercek_depo_fiksturu())
    return hatalar


def gecmis_nobeti(kapsam, kosucu=None, fikstur=True, kok=None):
    """(hatalar, isabetler). BLOKLAYICI kullanim icin (--pre-push / --aralik)."""
    hatalar = gecmis_fikstur_hatalari() if fikstur else []
    isabet, hata = gecmis_tara(kapsam, kosucu=kosucu, kok=kok)
    if hata:
        hatalar.append("OLCULEMEDI (gecmis ekseni) — %s" % hata)
        return hatalar, []
    for sha, yol in isabet:
        hatalar.append(
            "GECMISTE IC RAPOR EKLENMIS: %s (commit %s) — dosya SONRADAN SILINSE BILE "
            "commit kalicidir ve PUBLIC repodan anonim cekilebilir. Cozum: bu commit'i "
            "daldan cikar (interaktif olmayan rebase/reset ile yeniden yaz) ve raporu "
            "IZLENMEYEN birak; ad protokolu: RAPOR-MIMARA.md + .gitignore."
            % (yol, sha[:12]))
    return hatalar, isabet


# ------------------------------------------------------- pre-push aralik hesabi
_SIFIR = ("0" * 40, "0" * 64)


def pre_push_araliklari(stdin_metni):
    """git pre-push stdin ('<local_ref> <local_sha> <remote_ref> <remote_sha>' satirlari)
    -> taranacak `git rev-list` kapsam listeleri. SAF fonksiyon (test edilebilir).

    * local_sha sifir  -> dal SILINIYOR, taranacak yeni commit yok.
    * remote_sha sifir -> uzakta YENI dal: uzakta zaten olan her seyi disla
                          (`<sha> --not --remotes`), yoksa TUM gecmis taranir ve
                          bugunku eski kayitlar her yeni dal push'unu bloklardi.
    * aksi halde       -> `<remote_sha>..<local_sha>`
    """
    kapsamlar = []
    for satir in (stdin_metni or "").splitlines():
        alan = satir.split()
        if len(alan) < 4:
            continue
        _yerel_ref, yerel_sha, _uzak_ref, uzak_sha = alan[0], alan[1], alan[2], alan[3]
        if yerel_sha in _SIFIR:
            continue
        if uzak_sha in _SIFIR:
            kapsamlar.append([yerel_sha, "--not", "--remotes"])
        else:
            kapsamlar.append(["%s..%s" % (uzak_sha, yerel_sha)])
    return kapsamlar


def _kanca_kurulu_mu():
    """(kurulu_mu, yol) — pre-push kancasinda GECMIS NOBETI blogu var mi.
    Yalniz GORUNURLUK icindir; kanca commit EDILEMEDIGI icin bloklayici DEGIL."""
    p = subprocess.run(["git", "-C", ROOT, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None, None
    yol = os.path.join(p.stdout.strip(), "hooks", "pre-push")
    if not os.path.isfile(yol):
        return False, yol
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError:
        return False, yol
    return ("kisisel-veri-test.py" in metin and "--pre-push" in metin), yol


# ==================================================================================
# TEDARIKCI/URUN ADI SIZINTI NOBETCISI — KURESEL NEGATIF ICERIK KURALI
# ==================================================================================
# NEDEN VAR (olculdu, 27 Tem): parametrik sari serinin uretecinin turedigi ucuncu
# taraf tedarikci/urun adi, aile kaynagindaki bir yoruma yazilmisti; birlestir.py
# onu jenerator/hacim.js'e tasiyor ve build.py hacim.js'i HER parametrik urun
# sayfasina <script> ile gomuyor -> merge edilseydi CANLIYA + PUBLIC repoya
# (Pruvo138/pruvo) tedarikci adi sizardi. Guvenlik-para-gizlilik: para odenen
# kaynagin adi hicbir public yerde gecmez (CLAUDE.md kurali). Aile kaynagi
# temizlendi; bu nobetci REGRESYONU kapatir (adi geri koyan degisiklik kirmizi yanar).
#
# EKSEN: DOSYA ICERIGI (rapor nobetcisinden farkli — o dosya ADI ekseninde). Izlenen
# (git ls-files) dosyalarin ICERIGINDE, kucuk-harf normalize edilmis, DAR 3 literal
# aranir. Literal listesi kasitla PARCALARDAN kurulur: boylece bu kaynak dosyanin
# KENDISI (izlenen) kendi kalibiyla eslesmez (aksi halde tarayici kendi kaynagini
# kirmizi yakardi). Fikstur kirmizi/yesil ornekleri de calisma-aninda kurulur.
# YANLIS-POZITIF DARLIGI: 3 tam literal; near-miss (framework, kool maker) yesil.
_TED_PARCALAR = (("koo", "lm"), ("frame", "maker"), ("frame ", "maker"))
_TED_KALIPLAR = tuple("".join(p) for p in _TED_PARCALAR)


def _ted_eslesme(metin):
    """metin icinde gizli tedarikci/urun adi kaliplarindan gecenler (kucuk harf, sirali).
    Kalip listesi DAR (3 tam literal) -> alakasiz icerikte yanlis-pozitif 0."""
    d = metin.lower()
    return [k for k in _TED_KALIPLAR if k in d]


def _dosya_oku(yol):
    with open(os.path.join(ROOT, yol), "rb") as f:
        return f.read()


def tedarikci_isabetleri(yollar, oku=None):
    """Izlenen yol listesi -> (yol, kalip) isabetleri, sirali. GERCEK tarama ve fikstur
    oz-kontrolu AYNI fonksiyonu kullanir: govdesi no-op yapilirsa (or. 'return []')
    fikstur oz-kontrolu de kirmizi yanar (olu tarayici korumasi)."""
    oku = oku or _dosya_oku
    isabet = []
    for yol in yollar:
        try:
            ham = oku(yol)
        except OSError:
            continue
        metin = ham.decode("utf-8", "ignore")
        for k in _ted_eslesme(metin):
            isabet.append((yol, k))
    return sorted(isabet)


def tedarikci_fikstur_hatalari():
    """Nobetcinin KENDI hukmunu olcer (olu nobetci + asiri-genisleme korumasi).
    Bellekte calisir, diske/aga DOKUNMAZ."""
    hatalar = []
    # (0) TARAYICI OZ-KONTROLU: sentetik izlenen icerik -> isabet eslemesi CANLI mi.
    _kirmizi = "// cerceve.scad " + _TED_KALIPLAR[0] + " tureviyle uretilir"
    _yesil = "picture framework and a kool tool: makers of frames"
    _sahte = {"a/kirmizi.js": _kirmizi.encode("utf-8"),
              "b/yesil.js": _yesil.encode("utf-8")}
    _beklenen = [("a/kirmizi.js", _TED_KALIPLAR[0])]
    _bulunan = tedarikci_isabetleri(sorted(_sahte), oku=lambda y: _sahte[y])
    if _bulunan != _beklenen:
        hatalar.append("TARAYICI OLU/BOZUK: sentetik icerik taramasi beklenen %r "
                       "yerine %r bulundu" % (_beklenen, _bulunan))
    # (1) DESEN CANLI: her tam literal bir eslesme yakalamali.
    for k in _TED_KALIPLAR:
        if _ted_eslesme("x " + k + " y") != [k]:
            hatalar.append("DESEN OLU: %r yakalanmiyor" % k)
    # (2) DARLIK: near-miss (tam literal olmayan) YANMAMALI.
    for nm in ("framework", "kool maker", "makers of frames", "a frame and a maker"):
        if _ted_eslesme(nm):
            hatalar.append("YANLIS-POZITIF near-miss: %r yandi (kural DARALTILMALI)" % nm)
    return hatalar


def tedarikci_nobeti():
    """(hatalar, taranan_dosya_sayisi). Fail-loud: git okunamazsa sessiz yesil VERILMEZ."""
    hatalar = tedarikci_fikstur_hatalari()
    yollar, hata = _izlenen_dosyalar()
    if hata:
        hatalar.append("OLCULEMEDI (tedarikci nobeti) — %s" % hata)
        return hatalar, 0
    for yol, _k in tedarikci_isabetleri(yollar):
        hatalar.append(
            "TEDARIKCI ADI SIZINTISI: %s icinde gizli tedarikci/urun adi kalibi gecti — "
            "PUBLIC repoya girer (para odenen kaynak adi hicbir public yerde gecmez). "
            "Cozum: kaynak yorumunu notrlestir (hacim.js icin aile kaynagi + birlestir.py)."
            % yol)
    return hatalar, len(yollar)


# ---------------------------------------------------------------------------
# PARMAKIZI KAYIT ADI NOBETCISI (O7 — mimar hukmu 30 Tem)
# ---------------------------------------------------------------------------
# MIMAR HUKMU: onizleme/derleyici/paket-parmakizi.json'daki 25 .scad ADI kayitta
# KALIR. Gerekce: adlar JENERIK parca adlaridir (tedarikci/uyelik markasi degil) ve
# teshis degeri yuksektir — drift mesaji dosyayi ADIYLA soyler, aksi halde uyelik
# ureteclerinde hata mesaji "bir dosya degisti" demekle kalirdi.
# AMA hukum SARTLIDIR: adlarin JENERIK KALMASI zorunludur. Bu nobetci o sarti makineye
# baglar — kayit bir marka/tedarikci adi, e-posta, URL, kisi adi ya da DOSYA YOLU
# tasirsa KIRMIZI yanar (depo PUBLIC; para odenen kaynagin adi hicbir public yerde
# gecmez).
#
# 🔴 KURAL BICIM EKSENINDE (isim listesi DEGIL) — bilincli: bu PUBLIC bir depodur,
# bir "yasakli marka adlari" listesi nobetcinin KENDISINDE o adlari sizdirirdi.
# Bicim kurallari (kucuk harf + dar karakter kumesi + yol/@/:// yasagi + uzunluk)
# markali/kisisel/yol iceren adlari yapisal olarak eler, hicbir gizli ad yazmadan.
_PK_KAYIT = os.path.join("onizleme", "derleyici", "paket-parmakizi.json")
_PK_AD_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")
_PK_UZANTILAR = (".scad", ".json", ".txt", ".md")
_PK_OZET_RE = re.compile(r"^[0-9a-f]{64}$")
# `paket_anahtar` 30 Tem (tur 5/O9) eklendi: kaydin uretildigi R2 nesne anahtari.
# Serbest metin oldugu icin ayni gizlilik nobetine BAGLANIR — mutlak yol / e-posta /
# URL tasiyamaz (anahtar `onizleme/paket-v7.tar.gz` gibi GORECE bir yoldur; gorece yol
# SERBESTTIR, mutlak yol degildir).
_PK_METIN_ALANLARI = ("not", "aciklama", "paket_anahtar")


def _pk_yol_jetonu(metin):
    """Metinde MUTLAK yol gorunumlu bir jeton var mi (gizli calisma dizinini sizdirir)."""
    for jeton in re.split(r"\s+", metin or ""):
        if jeton.startswith("/") or jeton.startswith("~/") or "\\" in jeton:
            return jeton
    return None


def parmakizi_ad_kusurlari(veri):
    """KAPI GOVDESI — parmakizi kaydinin ADLARI jenerik mi (GERCEK tarama ve fikstur
    oz-kontrolu AYNI fonksiyonu kullanir; govdesi no-op yapilirsa fikstur de kirmizi)."""
    kusurlar = []
    if not isinstance(veri, dict):
        return ["parmakizi kaydi sozluk DEGIL -> okunamadi (fail-closed)"]
    # Kayit surum 1'de 'scad', surum 2'de 'dosyalar' anahtarini kullanir; nobetci
    # HANGISI VARSA onu tarar (surum gecisinde sessizce bosa dusmesin).
    adlar = None
    for anahtar in ("dosyalar", "scad"):
        if isinstance(veri.get(anahtar), dict):
            adlar = veri[anahtar]
            break
    if adlar is None:
        return ["parmakizi kaydinda 'dosyalar'/'scad' sozlugu YOK -> ad nobeti hicbir "
                "sey olcemedi (fail-closed)"]
    for ad in sorted(adlar):
        if not isinstance(ad, str) or not _PK_AD_RE.match(ad):
            kusurlar.append(
                "PARMAKIZI KAYIT ADI JENERIK DEGIL: %r -> yalniz kucuk harf/rakam/"
                "'.', '_', '-' iceren, en fazla 40 karakterlik DUZ dosya adi kabul "
                "edilir. Yol ayraci, bosluk, '@', buyuk harf ya da uzun ad; marka/"
                "tedarikci/kisi adi ya da calisma dizini sizintisi isaretidir." % (ad,))
            continue
        if not ad.endswith(_PK_UZANTILAR):
            kusurlar.append(
                "PARMAKIZI KAYIT ADI BEKLENMEDIK UZANTI: %r (beklenen: %s) -> pakete "
                "ait olmayan bir sey kayda girmis olabilir."
                % (ad, ", ".join(_PK_UZANTILAR)))
        ozet = adlar[ad]
        if not isinstance(ozet, str) or not _PK_OZET_RE.match(ozet):
            kusurlar.append(
                "PARMAKIZI KAYIT DEGERI OZET DEGIL: %r -> %r. Kayitta yalniz 64 haneli "
                "sha256 durur; serbest metin (yol/aciklama/kaynak) DURMAZ." % (ad, ozet))
    for alan in _PK_METIN_ALANLARI:
        metin = veri.get(alan)
        if not isinstance(metin, str):
            continue
        if "@" in metin or "://" in metin:
            kusurlar.append(
                "PARMAKIZI KAYIT METNI ILETISIM/URL TASIYOR: '%s' alaninda '@' ya da "
                "'://' gecti -> e-posta/adres PUBLIC repoya girmez." % alan)
        jeton = _pk_yol_jetonu(metin)
        if jeton:
            kusurlar.append(
                "PARMAKIZI KAYIT METNI MUTLAK YOL TASIYOR: '%s' alaninda %r -> yerel "
                "calisma dizini (gizli uretec kaynaklarinin yeri) sizar." % (alan, jeton))
    return kusurlar


# --- FIKSTURLER: kural oldurulurse/gevsetilirse bunlar KACAR -> kapi kirmizi.
_PK_KIRMIZI = (
    ("marka/tedarikci gorunumlu ad (buyuk harf + bosluk)",
     {"dosyalar": {"AcmeCorp Widget.scad": "a" * 64}}),
    ("dosya YOLU kayda girdi",
     {"dosyalar": {"/Users/okan/.uyelik-kodlar/x.scad": "b" * 64}}),
    ("e-posta gorunumlu ad",
     {"dosyalar": {"tasarimci@ornek.com.scad": "c" * 64}}),
    ("URL gorunumlu ad",
     {"dosyalar": {"https://ornek.com/x.scad": "d" * 64}}),
    ("deger ozet DEGIL, serbest metin",
     {"dosyalar": {"kutu.scad": "/Users/okan/gizli/kutu.scad"}}),
    ("'not' alaninda mutlak yol",
     {"dosyalar": {"kutu.scad": "e" * 64},
      "not": "kaynak /Users/okan/.uyelik-kodlar dizininden alindi"}),
    ("'not' alaninda e-posta",
     {"dosyalar": {"kutu.scad": "f" * 64}, "not": "soran: biri@ornek.com"}),
    ("kayitta 'dosyalar'/'scad' sozlugu YOK (fail-closed)", {"surum": 2}),
    ("'paket_anahtar' alaninda mutlak yol (tur 5/O9)",
     {"dosyalar": {"kutu.scad": "a" * 64},
      "paket_anahtar": "/Users/okan/dev/pruvo/.uyelik-kodlar/paket-v7.tar.gz"}),
    ("'paket_anahtar' alaninda URL (tur 5/O9)",
     {"dosyalar": {"kutu.scad": "b" * 64},
      "paket_anahtar": "https://ornek.com/pruvo-ozel/paket-v7.tar.gz"}),
)
# --- YESIL FIKSTURLER: bugunku gercek kaydin BICIMI + rutin jenerik adlar YANMAZ.
_PK_YESIL = (
    ("bugunku bicim: jenerik uretec adlari + eslem",
     {"dosyalar": {"kutu.scad": "0" * 64, "oringgenerator.scad": "1" * 64,
                   "eslem-ozel.json": "2" * 64},
      "not": "paket eslem surumu v5",
      "aciklama": "TEK YAZAR: tools/onizleme-paket-yukle.py — gorece yol SERBEST"}),
    ("surum 1 kaydi ('scad' anahtari) hala taranir",
     {"scad": {"toka.scad": "3" * 64, "damga-kase.scad": "4" * 64}}),
    ("surum 2 kaydi + GORECE R2 anahtari (tur 5/O9) — mesru, yanmamali",
     {"dosyalar": {"kutu.scad": "5" * 64},
      "paket_anahtar": "onizleme/paket-v7.tar.gz"}),
)


def parmakizi_ad_fikstur_hatalari():
    """Nobetcinin KENDI hukmunu olcer (olu nobetci + asiri-genisleme korumasi).
    Bellekte calisir, diske/aga DOKUNMAZ."""
    hatalar = []
    for ad, veri in _PK_KIRMIZI:
        if not parmakizi_ad_kusurlari(veri):
            hatalar.append("PARMAKIZI AD NOBETI OLU: %r fiksturu KIRMIZI yakmadi "
                           "(kural gevsetilmis ya da govde no-op)" % ad)
    for ad, veri in _PK_YESIL:
        bulgu = parmakizi_ad_kusurlari(veri)
        if bulgu:
            hatalar.append("PARMAKIZI AD NOBETI YANLIS-POZITIF: %r fiksturu KIRMIZI "
                           "yandi -> %s" % (ad, " ; ".join(bulgu)))
    return hatalar


def parmakizi_ad_nobeti():
    """(hatalar, taranan_ad_sayisi). Fail-loud: kayit varsa OKUNAMAMASI sessiz yesil DEGIL.
    Kayit dosyasi YOKSA nobetci sessizdir (dosya opsiyonel: paket hic yuklenmemis olabilir);
    fikstur oz-kontrolu yine de kosar, yani nobetci hicbir kosulda 'olu' olamaz."""
    hatalar = parmakizi_ad_fikstur_hatalari()
    yol = os.path.join(ROOT, _PK_KAYIT)
    if not os.path.exists(yol):
        return hatalar, 0
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        hatalar.append("OLCULEMEDI (parmakizi ad nobeti) — %s okunamadi: %s"
                       % (_PK_KAYIT, e))
        return hatalar, 0
    bulgu = parmakizi_ad_kusurlari(veri)
    for b in bulgu:
        hatalar.append("%s: %s" % (_PK_KAYIT, b))
    adlar = veri.get("dosyalar") if isinstance(veri.get("dosyalar"), dict) \
        else veri.get("scad")
    return hatalar, len(adlar) if isinstance(adlar, dict) else 0


# ==================================================================================
# ILETISIM YUZEYI NOBETCISI — IZLENEN DOSYA ICERIGI (7 Agu 2026)
# ==================================================================================
# 🔴 OLCULEN KOR NOKTA (bu bolumun VAR OLMA sebebi — sayilarla):
#   Bu depoda "yasakli ad" IKI AYRI YERDE tanimliydi ve TEK BIR IDDIA onlari birbirine
#   baglamiyordu ([[ikiz-tanim-sessiz-ayrisma]]):
#     (1) KANONIK kaynak: tools/sizinti-desen-ozetleri.json (PBKDF2 ozetleri, IZLENEN,
#         her klonda ve CI'da var). Tuketicisi: tools/commit-mesaji-kapisi.py — ve
#         YALNIZ COMMIT MESAJLARI ekseninde.
#     (2) IKIZ kaynak: yukaridaki `_TED_PARCALAR` — 3 duz literal, elle yazilmis, dosya
#         ICERIGI ekseninde 532 izlenen dosyada kosuyor.
#   Kesisimleri BOS; (2) hicbir zaman (1)'i okumadi. Yani bir tedarikci/vitrin adi
#   commit MESAJINA yazilirsa yakalanir, AYNI ad bir .py YORUMUNA yazilirsa GECER.
#
#   AYNI KOR NOKTANIN IKINCI YARISI — ALAN ADI EKSENI: commit-mesaji-kapisi.py'de olgun
#   bir BICIM kurali var (PUBLIC_ALAN + katalog markasi muafiyeti + gizli desen onceligi).
#   O kural da YALNIZ commit mesajina bakiyordu. OLCULDU (7 Agu 2026): ayni kuralin
#   E-POSTA kolu izlenen dosya ICERIGINE cevrildiginde 15 benzersiz host cikti ve
#   bunlardan BIRI gercek bir sizintiydi — baska bir ticari olusuma ait ONCEKI hesabin
#   alan adi tools/drive_yolu.py'nin docstring'inde duruyordu (bu dalda adsizlastirildi).
#   Yani kural ZATEN DEPODAYDI, yalnizca bu YUZEYE dogrultulmamisti.
#
#   UCUNCU KOR NOKTA — TELEFON BAGLAM AYRIMI: CLAUDE.md kurali kesin ("4005 asla
#   wa.me'de, 6526 arama/tel:'de olmaz") ama HICBIR kapi bunu olcmuyordu. Taban
#   (7 Agu 2026): 386 satir WA numarasi, 5 satir arama numarasi tasiyor; capraz ihlal 0.
#   Bugun temiz -> bu bir REGRESYON kapisidir, onarim degil. Beyan bu.
#
# 🔴 NEDEN OZET (AD) EKSENI DOSYA ICERIGININ TAMAMINA BAGLANMADI — OLCULDU, TAHMIN
#   EDILMEDI: kanonik desenler PBKDF2/5000 ile eslesir ve dosya icerigi 532 izlenen
#   dosyada 3 996 480 BENZERSIZ aday uretir (n=8: 1 233 757, n=12: 2 762 723).
#   8 cekirdekte TAM tarama 188 saniye surdu (tek cekirdekte ~1600 s). Bloklayici bir
#   kapiya bu maliyet KONULAMAZ: kapi birikmesi bu depoda OLCULMUS bir ariza sinifidir
#   ([[kapi-birikimi-yayin-gecikmesi]]) ve yavas kapi devre disi birakilir.
#   O TAM TARAMA BIR KEZ KOSTURULDU (7 Agu 2026, 532 dosya / 3 996 480 aday): ISABET 0.
#   Yani bugunku icerik TEMIZ; kapatilamayan sey gelecekteki bir regresyonun UCUZ
#   olcumudur. Ucuzlatmanin yolu bellidir ve BURADA YAZILAMAZ: ozet artefaktina ucuz
#   bir on-elek alani eklemek gerekir, o alan ancak DUZ desen kaynagini
#   (.sizinti-desenleri.txt, GITIGNORE'LU) elinde tutan makinede uretilebilir.
#   Bu yuzden ad ekseni burada DAR ama KANONIK bir yuzeye baglandi: E-POSTA HOST'LARI
#   (bugun 15 aday -> milisaniyeler). Gizlenen kapsam yok, sinir beyan edildi.
_CMK_YOL = os.path.join(ROOT, "tools", "commit-mesaji-kapisi.py")
_CMK_ONBELLEK = {}


def _cmk():
    """KANONIK modul (commit-mesaji-kapisi.py) -> (modul, hata). TEK kaynak.

    Dosya adinda tire var -> duz `import` calismaz, importlib ile yuklenir.
    FAIL-CLOSED: yuklenemezse bu nobetci YESIL VERMEZ."""
    if "m" in _CMK_ONBELLEK:
        return _CMK_ONBELLEK["m"], _CMK_ONBELLEK["h"]
    m = h = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pruvo_cmk", _CMK_YOL)
        if spec is None or spec.loader is None:
            h = "kanonik modul yuklenemedi (spec yok): %s" % _CMK_YOL
        else:
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
    except Exception as e:                                    # noqa: BLE001
        m, h = None, "kanonik modul yuklenemedi: %s (%s)" % (_CMK_YOL, e)
    _CMK_ONBELLEK["m"], _CMK_ONBELLEK["h"] = m, h
    return m, h


# ----------------------------------------------------------------- TELEFON BAGLAM EKSENI
# 🔴 NUMARALAR PARCALARDAN KURULUR: bu dosyanin KENDI kaynagi da izlenen ve PUBLIC'tir
# ([[nobetci-kendi-dosyasinda-sizinti]]). Parcalar zaten sitede acik olan WhatsApp
# numarasi ile JSON-LD'deki arama numarasidir; kural onlarin VARLIGI degil BAGLAMI
# hakkindadir, o yuzden tam numarayi yeni bir duz literal olarak eklemeye gerek yok.
_WA_PARCA = ("545", "138", "6526")
_ARAMA_PARCA = ("532", "595", "4005")


def _numara_deseni(parcalar):
    """Parcalardan, aralarinda en fazla 3 rakam-disi karakter kabul eden desen kurar.
    Bastaki 0/90/+90 opsiyoneldir; komsu RAKAM varsa eslesme YOK (baska bir numaranin
    ortasina rastlamasin)."""
    govde = r"\D{0,3}".join(parcalar)
    return re.compile(r"(?<!\d)(?:\+?90|0)?\D{0,3}" + govde + r"(?!\d)")


_WA_RE = _numara_deseni(_WA_PARCA)
_ARAMA_RE = _numara_deseni(_ARAMA_PARCA)
# Baglam isaretleri. DAR tutuldu: bu kapi BLOKLAYICI, bir yanlis-pozitif TUM yayini durdurur.
# 🔴 `tel:` DEGIL `tel:<rakam|+>` — OLCULDU: cıplak "tel:" JavaScript/JSON ANAHTARINI da
# yakaliyordu (shop/test/wa-siparis.mjs'de `tel: "0545..."` musteri alani) ve 4 MESRU
# fikstur satirini kirmiziya boyuyordu. Gercek arama baglami `tel:` URI SEMASIDIR ve
# ardindan bosluksuz `+` ya da rakam gelir (`href="tel:+90..."`).
_ARAMA_BAGLAM_RE = re.compile(r"tel:[+0-9]|telephone|contact_?point", re.I)
_WA_BAGLAM_RE = re.compile(r"wa\.me|whats_?app|wa_?me", re.I)


def _satir(metin, konum):
    """konum indeksini iceren SATIRI dondurur (baglam yargisi satir duzeyindedir)."""
    bas = metin.rfind("\n", 0, konum) + 1
    son = metin.find("\n", konum)
    return metin[bas:] if son < 0 else metin[bas:son]


def telefon_baglam_kusurlari(yol, metin):
    """[(iddia, mesaj), ...] — CAPRAZ baglam ihlalleri.

    IDDIA T1: WhatsApp numarasi ARAMA baglaminda (tel: / telephone / contactPoint) GECMEZ.
    IDDIA T2: ARAMA numarasi WhatsApp baglaminda (wa.me / whatsapp) GECMEZ.
    🔴 KURAL CAPRAZ SECILDI (numaranin KENDI baglaminda OLMASI sarti DEGIL): olculdu,
    "kendi baglaminda olmali" kurali bugun 8 MESRU satiri kirmiziya boyardi
    (attribution-ref.js TARGET_PHONE sabiti, 4 statik sayfadaki ayni sabit, test
    docstring'leri). Capraz kural ise CLAUDE.md'nin YAZILI hukmunun birebir kendisidir."""
    kusurlar = []
    for m in _WA_RE.finditer(metin):
        if _ARAMA_BAGLAM_RE.search(_satir(metin, m.start())):
            kusurlar.append(("T1", "TELEFON BAGLAM IHLALI (T1): %s — WhatsApp numarasi "
                                   "ARAMA baglaminda (tel:/telephone/contactPoint) geciyor. "
                                   "CLAUDE.md: WhatsApp numarasi arama/tel:'de olmaz." % yol))
    for m in _ARAMA_RE.finditer(metin):
        if _WA_BAGLAM_RE.search(_satir(metin, m.start())):
            kusurlar.append(("T2", "TELEFON BAGLAM IHLALI (T2): %s — ARAMA numarasi "
                                   "WhatsApp baglaminda (wa.me/whatsapp) geciyor. "
                                   "CLAUDE.md: arama numarasi asla wa.me'de olmaz." % yol))
    return kusurlar


# ----------------------------------------------------------------- E-POSTA HOST EKSENI
# MUAFIYET (host, yol) CIFTIDIR — salt host DEGIL. Gerekce ZORUNLU (bos gerekce =
# kirmizi). Cift olmasi bilincli: bir fikstur alan adinin BIR dosyada mesru olmasi onu
# TUM depoda mesru yapmaz. Muafiyeti genisletmek = sizinti riski USTLENMEKTIR.
_EPOSTA_MUAFIYET = {
    ("gizli" + "vitrin.com", "tools/commit-mesaji-kapisi.py"):
        "kanonik kapinin KENDI uydurma fiksturu (gercek ad degil; o dosyada beyan edilmis)",
    ("ornek" + "musteri.com", "shop/test/olcum.mjs"):
        "shop olcum testinin uydurma musteri e-postasi",
    ("hotmail.com", "urunler.json"):
        "urunler.json lisans.tasarimci ATIF degeri — URUN VERI DUZLEMI (tek yazar MaCiT); "
        "KraL dokunmaz, bulgu muhendis raporuyla ilgili mimara bildirildi",
}
# ORNEK/REZERVE alan adlari — SINIF kurali, "yasakli ad" listesi degil. RFC 2606 rezerve
# ucluye bu deponun Turkce fikstur karsiligi eklendi: `ornek.com` depo genelinde ORNEK
# degeri sozlesmesidir (shop testleri, parmakizi fiksturleri). Hicbiri gercek bir
# tedarikciye ait olamaz -> muafiyet listesini sismekten korur.
_REZERVE_ALAN = frozenset(("example.com", "example.net", "example.org", "ornek.com"))


def _eposta_hostlari(metin, cmk):
    """metin -> [(host, konum), ...]. AYRISTIRMA KANONIK: cmk._EPOSTA_RE kullanilir;
    ikinci bir e-posta deseni YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]])."""
    return [(m.group(1).lower().strip("."), m.start(1))
            for m in cmk._EPOSTA_RE.finditer(metin)]


def _host_elenir_mi(host, cmk):
    """Host GERCEK bir alan adi gorunumunde DEGIL mi (hukme girmez)?

    Son etiket kanonik UZANTI listesindeyse DOSYA ADIdir ('x@ornek.com.scad');
    kanonik TLD listesinde DEGILSE alan adi degildir ('@ornek.gecersiz', '@t.local',
    '@x.invalid', '@x.test'). Iki liste de commit-mesaji-kapisi.py'den gelir — ikiz
    tanim ACILMAZ, TLD/UZANTI politikasi tek yerde degisir."""
    etiketler = [e for e in host.split(".") if e]
    if len(etiketler) < 2:
        return True
    son = etiketler[-1]
    return son in cmk.UZANTI or son not in cmk.TLD


def eposta_host_kusurlari(yol, metin, cmk, kayit, markalar):
    """[(iddia, mesaj), ...] — izlenen dosya ICERIGINDEKI e-posta host'larinin hukmu.

    IDDIA E1: taninmayan (PUBLIC olmayan, katalog markasi olmayan, muaf olmayan) host YOK.
    IDDIA E2: hicbir host KANONIK gizli desenle eslesmiyor (ad TESHISE YAZILMAZ).
    🔴 SIRA SABIT (kanonik kapiyla AYNI): once gizli desen, sonra muafiyet. Gizli bir ad
    muafiyet listesine (kazara ya da kasten) girse bile desen isabeti muafiyeti EZER."""
    kusurlar = []
    for host, konum in _eposta_hostlari(metin, cmk):
        no = cmk._host_desen_isabeti(host, kayit)
        if no is not None:
            # 🔴 HOST YAZILMAZ: burada gorunen ad, ozet artefaktinin gizledigi adin ta
            # kendisidir ve CI gunlugu PUBLIC'tir ([[maskeleme-kismi-kapatma]]).
            kusurlar.append(("E2", "TEDARIKCI/SATICI ALAN ADI (E2): %s icinde, KANONIK "
                                   "gizli desen #%d ile eslesen bir e-posta alan adi "
                                   "geciyor (konum %d). Ad BILEREK yazilmiyor. Cozum: "
                                   "notr ifadeye cevir ('kaynak platform')."
                             % (yol, no, konum)))
            continue
        if _host_elenir_mi(host, cmk):
            continue
        if host in _REZERVE_ALAN:
            continue
        if cmk._public_mi(host):
            continue
        if (host, yol) in _EPOSTA_MUAFIYET:
            continue
        govde = cmk._kayitli_govde(host)
        if govde is not None and govde in markalar:
            continue
        kusurlar.append(("E1", "TANINMAYAN E-POSTA ALAN ADI (E1): %s icinde %s (konum %d) "
                               "— izlenen dosya iceriginde yalniz PUBLIC_ALAN, katalog "
                               "markasi, RFC-rezerve ornek alan adi ve GEREKCELI muafiyet "
                               "gecebilir. Satici/vitrin/tedarikci alan adi PUBLIC depoya "
                               "girmez." % (yol, cmk.maskele(host), konum)))
    return kusurlar


# ----------------------------------------------------------------- IDDIA DEFTERI
# 🔴 SAYAC DEGIL DEFTER: "kac iddia kostu" SABIT YAZILAMAZ — her iddia kendi ADIYLA
# deftere islenir ve asagidaki kapi BEKLENEN AD KUMESINI arar. Boylece "sayaci sabitle
# + bir iddiayi atla" mutasyonu kirmizi yanar (sayi tutar, AD eksilir).
_BEKLENEN_IDDIA = frozenset(("K1", "T1", "T2", "E1", "E2"))


def iletisim_fikstur_hatalari(cmk, kayit, markalar):
    """Nobetcinin KENDI hukmunu olcer (olu nobetci + asiri-genisleme korumasi).
    Bellekte calisir, diske/aga DOKUNMAZ. Fikstur metinleri PARCALARDAN kurulur ve
    alan adlari UYDURMADIR — bu dosya kendi kaliplarini duz metin olarak tasimaz."""
    hatalar = []
    wa = "".join(_WA_PARCA)
    ara = "".join(_ARAMA_PARCA)
    # --- T1/T2 KIRMIZI fiksturler
    for iddia, satir, gerekce in (
            ("T1", 'contactPoint telephone "+90' + wa + '"', "WA numarasi arama baglaminda"),
            ("T1", 'href="tel:+90' + wa + '"', "WA numarasi tel: baglaminda"),
            ("T2", "https://wa.me/90" + ara, "arama numarasi wa.me baglaminda"),
            ("T2", "WhatsApp hatti: 0" + ara, "arama numarasi whatsapp baglaminda")):
        if iddia not in [i for i, _m in telefon_baglam_kusurlari("f/fikstur.py", satir)]:
            hatalar.append("FIKSTUR(kirmizi) KACTI — %s zayifladi: %s" % (iddia, gerekce))
    # --- T1/T2 YESIL fiksturler (yanlis-pozitif butcesi: bugun MESRU olan satirlar)
    for satir, gerekce in (
            ('href="https://wa.me/90' + wa + '?text=Merhaba"', "WA numarasi KENDI baglaminda"),
            ('"telephone":"+90' + ara + '"', "arama numarasi KENDI baglaminda"),
            ('var TARGET_PHONE = "90' + wa + '";', "baglamsiz sabit — capraz ihlal DEGIL"),
            ("# numara sabitinden turetilen yazim: 90" + wa, "yorum icinde baglamsiz"),
            ("tel: destek hatti 0850 000 0000", "ILGISIZ numara, arama baglami")):
        bulunan = telefon_baglam_kusurlari("f/fikstur.py", satir)
        if bulunan:
            hatalar.append("FIKSTUR(yesil) YANLIS-POZITIF — kural DARALTILMALI: %s -> %r"
                           % (gerekce, [i for i, _m in bulunan]))
    # --- E1 KIRMIZI fiksturler. 🔴 ALAN ADLARI UYDURMA *VE* PARCALARDAN KURULU: aksi
    # halde bu dosyanin KENDISI (izlenen) kendi E1 kuralini tetiklerdi
    # ([[nobetci-kendi-dosyasinda-sizinti]] — olculdu: ilk surumde 5 self-hit).
    _uv = "uydurma" + "vitrin.com"
    _bo = "baska" + "olusum.com.tr"
    for satir, gerekce in (
            ("iletisim: satis@" + _uv, "taninmayan ticari alan adi"),
            ("hesap: info@" + _bo, "taninmayan alan adi, cok parcali uzanti"),
            ("bakim: admin@shop." + _uv, "alt alan — kayitli govde muaf degil")):
        if "E1" not in [i for i, _m in eposta_host_kusurlari(
                "f/fikstur.py", satir, cmk, kayit, markalar)]:
            hatalar.append("FIKSTUR(kirmizi) KACTI — E1 zayifladi: %s" % gerekce)
    # --- E1 YESIL fiksturler (yanlis-pozitif butcesi)
    for satir, gerekce in (
            ("iletisim: info@pruvo3d.com", "kendi PUBLIC alan adimiz"),
            ("git config user.email t@example.invalid", "rezerve TLD -> alan adi degil"),
            ("git config user.email test@example.com", "RFC 2606 rezerve ornek alan adi"),
            ("fikstur: kt@pruvo.test", "rezerve .test -> alan adi degil"),
            ('{"dosyalar": {"tasarimci@ornek.com.scad": "c"}}', "son etiket UZANTI -> dosya adi"),
            ("noreply@anthropic.com kimlik trailer'i", "PUBLIC_ALAN kimlik alani")):
        bulunan = eposta_host_kusurlari("f/fikstur.py", satir, cmk, kayit, markalar)
        if bulunan:
            hatalar.append("FIKSTUR(yesil) YANLIS-POZITIF — kural DARALTILMALI: %s -> %r"
                           % (gerekce, [i for i, _m in bulunan]))
    # --- MUAFIYET SAGLIGI: cift bicimi ZORUNLU, gerekce ZORUNLU (liste curumesin).
    for anahtar, gerekce in _EPOSTA_MUAFIYET.items():
        if not (isinstance(anahtar, tuple) and len(anahtar) == 2):
            hatalar.append("MUAFIYET BICIMI BOZUK — (host, yol) cifti degil: %r" % (anahtar,))
            continue
        if not (gerekce and str(gerekce).strip()):
            hatalar.append("GEREKCESIZ e-posta muafiyeti: %r" % (anahtar,))
    # --- E2 CANLILIK: kanonik desen yargisi ISLIYOR mu? GERCEK desen KULLANILMADAN
    #     olculur (sahte tuz + uydurma ad) — fikstur gercek sirri hic gormez.
    _tuz = b"\x11" * 16
    _ad = "uydurmagizli"
    _sahte = {"dongu": 1000, "tuz": _tuz,
              "desenler": [(len(_ad), cmk._ozetle(_ad, _tuz, 1000))]}
    if "E2" not in [i for i, _m in eposta_host_kusurlari(
            "f/fikstur.py", "iletisim: satis@" + _ad + ".com", cmk, _sahte, markalar)]:
        hatalar.append("E2 YARGISI OLU: host'un KENDISI gizli desen oldugunda kapi kirmizi "
                       "yakmiyor (kanonik desen ekseni kopmus)")
    # --- SIRA KANITI: desen isabeti MUAFIYETI EZMELI (gizli ad muafiyete girse bile).
    _gv = "gizli" + "vitrin"
    _sahte2 = {"dongu": 1000, "tuz": _tuz,
               "desenler": [(len(_gv), cmk._ozetle(_gv, _tuz, 1000))]}
    if "E2" not in [i for i, _m in eposta_host_kusurlari(
            "tools/commit-mesaji-kapisi.py", "iletisim: satis@" + _gv + ".com", cmk,
            _sahte2, markalar)]:
        hatalar.append("SIRA BOZUK: muafiyet listesindeki bir host gizli desenle eslestigi "
                       "halde MUAF sayildi — desen ONCE bakilmali")
    # --- E2E ENJEKSIYON: SENTETIK bir dosya korpusu verilir ve TARAMA DONGUSUNUN kendisi
    # olculur (saf fonksiyon degil). 🔴 BU KATMAN "SAYACI SABITLE + IDDIAYI ATLA"
    # MUTASYONUNU OLDURUR: defter kapisi susturulsa bile, planlanmis ihlalleri BULMAYAN
    # bir tarama burada kirmizi yanar. Ozyineleme kapisi: fikstur=False.
    _korpus = {
        "s/tel1.html": 'x <a href="tel:+90' + wa + '">ara</a>',          # T1 ihlali
        "s/tel2.js": 'const u = "https://wa.me/90' + ara + '";',          # T2 ihlali
        "s/mail.py": "# iletisim: satis@" + _uv,                          # E1 ihlali
        "s/temiz.js": 'href="https://wa.me/90' + wa + '?text=Merhaba"',   # YESIL
        "s/temiz2.py": "# bildirim: info@pruvo3d.com",                    # YESIL
        KAPI_YOLU: "# canlilik capasi",
    }
    _h, _t = iletisim_tara(_korpus, cmk, kayit, markalar)
    _bekle_iddia = {"T1", "T2", "E1", "E2"}
    _bulunan = {i for i, _m in _h}
    if _bulunan != {"T1", "T2", "E1"}:
        hatalar.append("E2E: sentetik korpusta beklenen ihlal kumesi %r yerine %r bulundu "
                       "(tarama dongusu ihlalleri GORMUYOR ya da yanlis-pozitif uretti)"
                       % (sorted({"T1", "T2", "E1"}), sorted(_bulunan)))
    if _t["dosya"] != len(_korpus):
        hatalar.append("E2E: taranan dosya sayisi %d yerine %d (tarama yuzeyi daralmis)"
                       % (len(_korpus), _t["dosya"]))
    if not _bekle_iddia <= _t["iddia"]:
        hatalar.append("E2E: iddia defteri %r bekleniyordu, %r islendi (bir iddia HIC "
                       "kosmadi — sayac sabitlense bile bu katman gorur)"
                       % (sorted(_bekle_iddia), sorted(_t["iddia"])))
    if _t["wa"] != 2 or _t["arama"] != 1:
        hatalar.append("E2E: taban sayaclari bozuk — WA vurusu 2 bekleniyordu %d, arama "
                       "vurusu 1 bekleniyordu %d" % (_t["wa"], _t["arama"]))
    return hatalar


def iletisim_tara(dosyalar, cmk, kayit, markalar):
    """KAPI GOVDESI — {yol: metin} korpusu -> ([(iddia, mesaj), ...], taban).

    GERCEK tarama ve E2E fikstur oz-kontrolu AYNI fonksiyonu kullanir: govdesi no-op
    yapilirsa (or. 'return [], taban') fikstur de kirmizi yanar (olu tarayici korumasi).
    Defter YALNIZ FIILEN KOSAN iddialarla doldurulur — sabit bir liste degil."""
    defter = set()
    taban = {"dosya": 0, "wa": 0, "arama": 0, "host": 0, "iddia": defter}
    kusurlar = []
    for yol in sorted(dosyalar):
        metin = dosyalar[yol]
        taban["dosya"] += 1
        taban["wa"] += len(_WA_RE.findall(metin))
        taban["arama"] += len(_ARAMA_RE.findall(metin))
        defter.update(("T1", "T2"))
        kusurlar.extend(telefon_baglam_kusurlari(yol, metin))
        hostlar = _eposta_hostlari(metin, cmk)
        taban["host"] += len(hostlar)
        if hostlar:
            defter.update(("E1", "E2"))
        kusurlar.extend(eposta_host_kusurlari(yol, metin, cmk, kayit, markalar))
    for iddia, _m in kusurlar:
        defter.add(iddia)
    return kusurlar, taban


def iletisim_nobeti():
    """(hatalar, taban) — izlenen dosya ICERIGI uzerinde iletisim yuzeyi nobeti.

    taban: olculen sayilar (dosya · WA vurusu · arama vurusu · e-posta host · iddia adlari).
    FAIL-CLOSED: kanonik modul ya da kanonik desen kaydi okunamazsa YESIL VERILMEZ."""
    defter = set()
    taban = {"dosya": 0, "wa": 0, "arama": 0, "host": 0, "iddia": defter}
    cmk, cmk_hata = _cmk()
    if cmk is None:
        return ["OLCULEMEDI (iletisim nobeti) — %s" % cmk_hata], taban

    # IDDIA K1 — KANONIK DESEN KAYNAGI: ikiz tanim YOK; tek kaynak YUKLENIR ve BOS DEGIL.
    kayit, kayit_hata = cmk.ozet_kaydi_yukle()
    if kayit is None:
        return (["OLCULEMEDI (K1) — kanonik desen kaydi okunamadi: %s. Bu depoda ozet "
                 "artefakti IZLENEN bir dosyadir; yoklugu normal calisma hali DEGIL "
                 "(fail-closed)." % kayit_hata], taban)
    defter.add("K1")

    yollar, hata = _izlenen_dosyalar()
    if hata:
        return ["OLCULEMEDI (iletisim nobeti) — %s" % hata], taban
    if KAPI_YOLU not in yollar:
        return (["OLCULEMEDI (CANLILIK, iletisim nobeti) — izlenen dosya listesi kapinin "
                 "KENDI yolunu (%s) icermiyor; tarama yuzeyi BOS ya da KISMI." % KAPI_YOLU],
                taban)

    markalar = cmk.katalog_markalari()
    hatalar = iletisim_fikstur_hatalari(cmk, kayit, markalar)

    korpus = {}
    for yol in yollar:
        try:
            with open(os.path.join(ROOT, yol), "rb") as f:
                korpus[yol] = f.read().decode("utf-8", "ignore")
        except OSError:
            continue
    kusurlar, olculen = iletisim_tara(korpus, cmk, kayit, markalar)
    hatalar.extend(m for _i, m in kusurlar)
    # TABAN SAYILARI = iddianin GERCEKTEN bir sey uzerinde kostugunun kaniti.
    for k in ("dosya", "wa", "arama", "host"):
        taban[k] = olculen[k]
    defter.update(olculen["iddia"])

    # 🔴 DEFTER KAPISI: beklenen iddialarin HEPSI kosmus olmali.
    eksik = sorted(_BEKLENEN_IDDIA - defter)
    if eksik:
        hatalar.append("IDDIA KOSMADI — beklenen iddia kumesi %s, EKSIK: %s. Bir iddia "
                       "atlandi ya da tarama yuzeyi o iddiaya hic ulasmadi (sessiz yesil)."
                       % (sorted(_BEKLENEN_IDDIA), eksik))
    # ⚠️ VERI CAPASI DEGIL: sabit sayi/SHA/tarih iddiasi YOK, esik YOK. Yalniz
    # "hic olculdu mu" sorulur; katalog buyudukce/kuculdukce degismez.
    if not taban["wa"] or not taban["host"]:
        hatalar.append("TABAN BOS — WA numarasi vurusu %d, e-posta host %d. Bu depoda "
                       "ikisi de sifir olamaz; tarama yuzeyi daralmis demektir."
                       % (taban["wa"], taban["host"]))
    return hatalar, taban


def normalize(metin):
    metin = metin.lower()
    for c in (" ", "\t", "\n", " ", "-", "(", ")"):
        metin = metin.replace(c, "")
    return metin


def pv_birlestir(html):
    """Kaynaktaki .pv span'larını (karışık sıralı data-a..l) sırayla birleştirir;
    ardışık span'lar tek değere ait olabilir → tam metin döner."""
    parca_metinler = []
    for m in PV_RE.finditer(html):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        parca_metinler.append("".join(attrs.get(k, "")
                                      for k in "abcdefghijkl"))
    return "".join(parca_metinler)


def _yaz_hatalar(baslik, hatalar):
    print("KIRMIZI — %s %d hata:" % (baslik, len(hatalar)))
    for h in hatalar:
        print("  - " + h)


def aralik_kapisi(kapsamlar, etiket):
    """BLOKLAYICI geçmiş kolu (--aralik / --pre-push). Çıkış kodu döner.

    🔴 KAPSAM GORUNURLUGU (kusur 4 kardesi): her kapsam icin commit sayisi HER ZAMAN
    basilir. Cozulemeyen kapsam = KIRMIZI (fail-closed). Commit sayisi 0 olan bir
    kapsam KIRMIZI DEGILDIR ve bu bilincli bir yanlis-pozitif karari: geri saran
    (force-push/rewind) ya da zaten guncel bir ref icin git pre-push'u BOS aralikla
    cagirir; bunu bloklamak her mesru rewind'i durdururdu. Ama SESSIZ de degildir —
    satir ekrana basilir."""
    if not kapsamlar:
        _yaz_hatalar("geçmiş ekseni",
                     ["OLCULEMEDI — taranacak kapsam URETILEMEDI (%s). Bos kapsam "
                      "SESSIZ YESIL sayilmaz; push durduruldu." % etiket])
        return 1
    hatalar = gecmis_fikstur_hatalari()
    toplam_commit = 0
    for kapsam in kapsamlar:
        s = subprocess.run(["git", "-C", ROOT, "rev-list", "--count"] + list(kapsam),
                           capture_output=True, text=True)
        if s.returncode != 0:
            hatalar.append("OLCULEMEDI — kapsam cozulemedi (%s): %s"
                           % (" ".join(kapsam), (s.stderr or "").strip() or "?"))
            continue
        sayi = int((s.stdout.strip() or "0").split()[0])
        toplam_commit += sayi
        print("  kapsam: %-52s -> %d commit" % (" ".join(kapsam), sayi))
        h, _isabet = gecmis_nobeti(kapsam, fikstur=False)
        hatalar.extend(h)
    if hatalar:
        _yaz_hatalar("geçmiş ekseni (iç rapor / commit geçmişi)", hatalar)
        print("  (bu kapı PUSH'U DURDURUR: sızıntı ancak push'tan ÖNCE önlenebilir; "
              "commit uzak depoya gittikten sonra geri alınamaz.)")
        return 1
    print("YEŞİL — geçmiş ekseni geçti (%s: %d commit, %d kırmızı + %d yeşil fikstür + "
          "gerçek-git biçim çapası)."
          % (etiket, toplam_commit, len(_GECMIS_KIRMIZI), len(_GECMIS_YESIL)))
    return 0


def pre_push_ana():
    """git pre-push kancası: stdin'den ref satırlarını okur, aralıkları tarar."""
    ham = sys.stdin.read()
    satirlar = [s for s in (ham or "").splitlines() if s.strip()]
    kapsamlar = pre_push_araliklari(ham)
    if not satirlar:
        print("YEŞİL — geçmiş ekseni: push edilecek ref yok (stdin boş).")
        return 0
    if not kapsamlar:
        # Tum satirlar dal SILME ise mesru; degilse kapsam uretimi bozulmus demektir.
        silme = all(len(s.split()) >= 4 and s.split()[1] in _SIFIR for s in satirlar)
        if silme:
            print("YEŞİL — geçmiş ekseni: yalnız dal silme (%d ref), yeni commit yok."
                  % len(satirlar))
            return 0
        _yaz_hatalar("geçmiş ekseni",
                     ["OLCULEMEDI — %d ref satiri geldi ama HIC kapsam uretilemedi "
                      "(pre-push girdisi bicimi degismis olabilir). Bos kapsam SESSIZ "
                      "YESIL sayilmaz; push durduruldu." % len(satirlar)])
        return 1
    return aralik_kapisi(kapsamlar, "pre-push")


def gecmis_raporu():
    """--gecmis: TÜM yerel geçmişi tarar ve RAPOR eder. BLOKLAMAZ (çıkış 0).

    🔴 NEDEN BLOKLAMAZ: main'in geçmişinde BUGÜN zaten kayıt var (aşağıda listelenir);
    bloklayıcı olsaydı her push kırılırdı. Bu kip envanter/karar aracıdır — sızmış
    içeriğin temizliği geçmiş yeniden yazma demektir ve OKAN KAPISIDIR.
    Ölçülemezse çıkış 2 (rapor üretilemedi ≠ temiz)."""
    hepsi, hata = gecmis_tara(["--all"])
    if hata:
        _yaz_hatalar("geçmiş raporu", ["OLCULEMEDI — %s" % hata])
        return 2
    uzak, hata2 = gecmis_tara(["--remotes"])
    if hata2:
        uzak = None
    uzak_kume = set(uzak or [])
    print("GEÇMİŞ RAPORU — tüm yerel referanslardan erişilebilen commit'lerde EKLENMİŞ "
          "iç rapor dosyaları")
    print("  (bu kip BLOKLAMAZ; temizlik = geçmiş yeniden yazma = Okan kapısı)")
    if not hepsi:
        print("  kayıt YOK.")
        return 0
    for sha, yol in hepsi:
        nerede = "PUBLIC (uzak referanstan erişilebilir)" if (sha, yol) in uzak_kume \
            else "yerel (henüz uzağa gitmemiş)"
        print("  - %s  %s  [%s]" % (sha[:12], yol, nerede))
    print("  TOPLAM: %d kayıt (%d'i PUBLIC)." % (len(hepsi), len(uzak_kume & set(hepsi))))
    return 0


def main():
    argv = sys.argv[1:]
    if "--gecmis" in argv:
        sys.exit(gecmis_raporu())
    if "--pre-push" in argv:
        sys.exit(pre_push_ana())
    if "--yalniz-iletisim" in argv:
        # MUTASYON SURUCUSU icin dar kol: yalniz iletisim yuzeyi nobetcisi kosar
        # (327 sayfa render edilmez). Hukum ve cikis kodu TAM kolla AYNIdir.
        h, t = iletisim_nobeti()
        if h:
            _yaz_hatalar("iletişim yüzeyi nöbetçisi (içerik ekseni)", h)
            sys.exit(1)
        print("YEŞİL — iletişim yüzeyi nöbetçisi geçti (%d iddia: %s / taban: %d dosya · "
              "%d WA vuruşu · %d arama vuruşu · %d e-posta host · %d gerekçeli muafiyet)."
              % (len(t["iddia"]), ",".join(sorted(t["iddia"])), t["dosya"], t["wa"],
                 t["arama"], t["host"], len(_EPOSTA_MUAFIYET)))
        sys.exit(0)
    if "--aralik" in argv:
        i = argv.index("--aralik")
        aralik = argv[i + 1:]
        if not aralik:
            print("KULLANIM: --aralik <git rev-list kapsami>  (or. origin/main..HEAD)",
                  file=sys.stderr)
            sys.exit(2)
        sys.exit(aralik_kapisi([aralik], " ".join(aralik)))

    hatalar = []
    dosyalar = {}

    # üretilen sayfalar — diskten değil, üreticiden taze render
    for slug, title, meta, fn in build.CONTENT_PAGES:
        dosyalar[slug] = build.render_content_page(slug, title, meta, fn())

    # statik sayfalar
    for slug, yol in [("index", "index.html"),
                      ("hakkimizda", "hakkimizda/index.html"),
                      ("iletisim", "iletisim/index.html"),
                      ("sss", "sss/index.html"),
                      ("gizlilik", "gizlilik/index.html")]:
        with open(os.path.join(ROOT, yol), encoding="utf-8") as f:
            dosyalar[slug] = f.read()

    for slug, html in sorted(dosyalar.items()):
        # 1) NEGATİF: JSON-LD hariç ham kaynakta düz metin yok
        temiz = LD_RE.sub("", html)
        norm = normalize(temiz)
        for kalip in KALIPLAR:
            if normalize(kalip) in norm:
                hatalar.append("%s: '%s' HAM KAYNAKTA düz metin geçiyor"
                               % (slug, kalip))

        # 2) POZİTİF: korumalı değerler parçalardan birebir geri çıkıyor
        butun = pv_birlestir(html)
        for deger in BEKLENEN.get(slug, []):
            if deger not in butun:
                hatalar.append("%s: '%s' pv parçalarından GERİ KURULAMADI "
                               "(müşteri göremez!)" % (slug, deger))

    # 3) IC RAPOR SIZINTI NOBETCISI (kuresel negatif kural + kendi fiksturleri)
    rapor_hatalari, taranan = ic_rapor_nobeti()
    # NOBETCININ GERCEKTEN KOSTUGUNUN KANITI (TUR 2 / D4 kor noktasi):
    # basarili bir tarama en az kapinin KENDI dosyasini gorur (KAPI_YOLU canlilik
    # capasi) -> taranan SIFIR olamaz. Cagri silinip yerine sabit sonuc konursa
    # (olculdu: `rapor_hatalari, taranan = [], 0`) burasi KIRMIZI yanar.
    # ⚠️ VERI CAPASI DEGIL: sabit sayi/SHA/tarih iddiasi yok, esik yok — yalnizca
    # "tarama HIC yapildi mi" sorulur; katalog buyudukce/kuculdukce degismez.
    if not rapor_hatalari and not taranan:
        rapor_hatalari = ["NOBETCI KOSMADI — tarama 0 izlenen dosya bildirdi ve hicbir "
                          "hata da uretmedi; ic rapor nobetcisinin cagrisi kopmus olmali "
                          "(sessiz yesil). Kapi bu haliyle HICBIR SEY olcmuyor."]

    # 4) TEDARIKCI/URUN ADI SIZINTI NOBETCISI (kuresel negatif ICERIK kurali)
    tedarikci_hatalari, ted_taranan = tedarikci_nobeti()

    # 4b) ILETISIM YUZEYI NOBETCISI (icerik ekseni: telefon baglami + e-posta alan adi,
    #     KANONIK desen kaynagina bagli). Kor nokta gerekcesi icin bolum basligina bak.
    iletisim_hatalari, iletisim_taban = iletisim_nobeti()

    # 5) PARMAKIZI KAYIT ADI NOBETCISI (O7 — adlar JENERIK kalmali)
    pk_hatalari, pk_taranan = parmakizi_ad_nobeti()

    # 6) GECMIS EKSENI — CI'da FIKSTURLER kosar (gercek-git bicim capasi dahil).
    #    CANLI ARALIK TARANMAZ: deploy.yml `actions/checkout@v4`i fetch-depth vermeden
    #    kullanir -> SIG klon, `origin/main..HEAD` CI'da COZULEMEZ. Canli tarama
    #    pre-push kancasindadir (bkz. GECMIS EKSENI bolumu).
    gecmis_hatalari = gecmis_fikstur_hatalari()

    if pk_hatalari:
        print("KIRMIZI — parmakızı kayıt adı nöbetçisi %d hata:" % len(pk_hatalari))
        for h in pk_hatalari:
            print("  - " + h)

    if (hatalar or rapor_hatalari or tedarikci_hatalari or pk_hatalari
            or gecmis_hatalari or iletisim_hatalari):
        if hatalar:
            _yaz_hatalar("kişisel veri testi", hatalar)
        if rapor_hatalari:
            _yaz_hatalar("iç rapor sızıntı nöbetçisi", rapor_hatalari)
        if tedarikci_hatalari:
            _yaz_hatalar("tedarikçi/ürün adı sızıntı nöbetçisi", tedarikci_hatalari)
        if iletisim_hatalari:
            _yaz_hatalar("iletişim yüzeyi nöbetçisi (içerik ekseni)", iletisim_hatalari)
        if gecmis_hatalari:
            _yaz_hatalar("geçmiş ekseni fikstürleri", gecmis_hatalari)
        sys.exit(1)
    print("YEŞİL — kişisel veri testi geçti (%d sayfa, %d kalıp, "
          "%d sayfada pozitif kontrol)."
          % (len(dosyalar), len(KALIPLAR), len(BEKLENEN)))
    print("YEŞİL — iç rapor sızıntı nöbetçisi geçti (%d izlenen dosya tarandı; "
          "KURAL A: %d kırmızı + %d yeşil fikstür / %d istisna; "
          "KURAL B kök belge: %d kırmızı + %d yeşil fikstür / %d izin)."
          % (taranan, len(_IC_RAPOR_KIRMIZI), len(_IC_RAPOR_YESIL),
             len(IC_RAPOR_ISTISNA), len(_KOK_BELGE_KIRMIZI),
             len(_KOK_BELGE_YESIL), len(KOK_BELGE_IZIN)))
    print("YEŞİL — tedarikçi/ürün adı sızıntı nöbetçisi geçti "
          "(%d izlenen dosya içeriği tarandı, %d dar literal)."
          % (ted_taranan, len(_TED_KALIPLAR)))
    print("YEŞİL — iletişim yüzeyi nöbetçisi geçti (%d iddia: %s / taban: %d dosya · "
          "%d WA vuruşu · %d arama vuruşu · %d e-posta host · %d gerekçeli muafiyet · "
          "%d kanonik desen)."
          % (len(iletisim_taban["iddia"]), ",".join(sorted(iletisim_taban["iddia"])),
             iletisim_taban["dosya"], iletisim_taban["wa"], iletisim_taban["arama"],
             iletisim_taban["host"], len(_EPOSTA_MUAFIYET),
             len((_cmk()[0].ozet_kaydi_yukle()[0] or {}).get("desenler", ()))))
    kurulu, kanca_yolu = _kanca_kurulu_mu()
    print("YEŞİL — geçmiş ekseni fikstürleri geçti (%d kırmızı + %d yeşil senaryo + "
          "gerçek-git biçim çapası). Canlı aralık taraması pre-push kancasında: %s"
          % (len(_GECMIS_KIRMIZI), len(_GECMIS_YESIL),
             "KURULU" if kurulu else
             ("KURULU DEĞİL → python3 tools/gecmis-nobeti-hook-kur.py"
              if kurulu is False else "ölçülemedi (git yok?)")))
    if kanca_yolu and not kurulu:
        print("        (kanca yolu: %s — .git/hooks git'e GİRMEZ, her makinede kurulur)"
              % kanca_yolu)
    print("YEŞİL — parmakızı kayıt adı nöbetçisi geçti (%d ad tarandı, %d kırmızı + "
          "%d yeşil fikstür)." % (pk_taranan, len(_PK_KIRMIZI), len(_PK_YESIL)))


if __name__ == "__main__":
    main()
