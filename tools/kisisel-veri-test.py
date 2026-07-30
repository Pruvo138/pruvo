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
  3) İÇ RAPOR SIZINTI NÖBETÇİSİ (27 Tem) — KÜRESEL NEGATİF kural: repoda
     İZLENEN (git ls-files) hiçbir dosya işçi→mimar iç rapor ADLANDIRMA
     ailesine uymayacak. Ayrıntı ve gerekçe için aşağıdaki bölüm başlığına bak.

Çalıştırma:  python3 tools/kisisel-veri-test.py   (çıkış kodu 0 = geçti)
"""
import json
import os
import re
import subprocess
import sys

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
_TR_KATLA = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})
IC_RAPOR_UZANTILARI = (".md", ".markdown", ".txt")
IC_RAPOR_KOKLERI = ("rapor", "curutme", "onarim", "denetim", "olcum")
IC_RAPOR_SONEKLERI = ("rapor", "raporu")
_AYIRAC = "-_. "

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
    if not govde:
        return False
    for kok in IC_RAPOR_KOKLERI:
        if govde == kok:
            return True
        if govde.startswith(kok) and govde[len(kok)] in _AYIRAC:
            return True
    for sonek in IC_RAPOR_SONEKLERI:
        if (govde.endswith(sonek) and len(govde) > len(sonek)
                and govde[-len(sonek) - 1] in _AYIRAC):
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
    for yol, gerekce in _IC_RAPOR_KIRMIZI:
        if not ic_rapor_mu(yol):
            hatalar.append("FIKSTUR(kirmizi) KACTI — kural zayifladi: %s  [%s]"
                           % (yol, gerekce))
    for yol, gerekce in _IC_RAPOR_YESIL:
        if ic_rapor_mu(yol):
            hatalar.append("FIKSTUR(yesil) YANLIS-POZITIF — kural DARALTILMALI: %s  [%s]"
                           % (yol, gerekce))
    return hatalar


def _git_ls_files():
    """Gercek kosucu: (returncode, stdout, stderr). Ag/Drive/canli uc YOK, yalniz yerel git."""
    try:
        r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"],
                           capture_output=True, text=True)
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr


def _izlenen_dosyalar(kosucu=None):
    """(yollar, hata_metni). kosucu enjekte edilebilir -> fail-loud fiksturu icin."""
    rc, cikti, hata = (kosucu or _git_ls_files)()
    if rc != 0:
        return None, "git ls-files basarisiz (rc=%s): %s" % (rc, (hata or "").strip() or "?")
    return [y for y in cikti.split("\0") if y], None


def ic_rapor_nobeti(kosucu=None, fikstur=True):
    """(hatalar, taranan_dosya_sayisi) dondurur.
    fikstur=False YALNIZ ic fail-loud fiksturunun kendini cagirmasi icindir (ozyineleme kapisi)."""
    hatalar = ic_rapor_fikstur_hatalari() if fikstur else []

    for yol, gerekce in IC_RAPOR_ISTISNA.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ istisna girisi: %s" % yol)
        elif not ic_rapor_mu(yol):
            hatalar.append("BAYAT istisna (artik aileye uymuyor — listeden sil): %s" % yol)

    yollar, hata = _izlenen_dosyalar(kosucu)
    if hata:
        # FAIL-LOUD: olculecek sey yoksa sessiz yesil VERILMEZ (sizinti kapisi).
        hatalar.append("OLCULEMEDI — %s" % hata)
        return hatalar, 0

    for yol in ic_rapor_isabetleri(yollar):
        hatalar.append(
            "IZLENEN IC RAPOR: %s — PUBLIC repoya girer (kapi bypass yollari / dal-ajan "
            "kimlikleri / ic olcum). Cozum: git rm --cached '%s' + adi RAPOR-MIMARA.md yap."
            % (yol, yol))
    return hatalar, len(yollar)


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


def main():
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

    # 4) TEDARIKCI/URUN ADI SIZINTI NOBETCISI (kuresel negatif ICERIK kurali)
    tedarikci_hatalari, ted_taranan = tedarikci_nobeti()

    # 5) PARMAKIZI KAYIT ADI NOBETCISI (O7 — adlar JENERIK kalmali)
    pk_hatalari, pk_taranan = parmakizi_ad_nobeti()

    if pk_hatalari:
        print("KIRMIZI — parmakızı kayıt adı nöbetçisi %d hata:" % len(pk_hatalari))
        for h in pk_hatalari:
            print("  - " + h)

    if hatalar or rapor_hatalari or tedarikci_hatalari or pk_hatalari:
        if hatalar:
            print("KIRMIZI — kişisel veri testi %d hata:" % len(hatalar))
            for h in hatalar:
                print("  - " + h)
        if rapor_hatalari:
            print("KIRMIZI — iç rapor sızıntı nöbetçisi %d hata:" % len(rapor_hatalari))
            for h in rapor_hatalari:
                print("  - " + h)
        if tedarikci_hatalari:
            print("KIRMIZI — tedarikçi/ürün adı sızıntı nöbetçisi %d hata:"
                  % len(tedarikci_hatalari))
            for h in tedarikci_hatalari:
                print("  - " + h)
        sys.exit(1)
    print("YEŞİL — kişisel veri testi geçti (%d sayfa, %d kalıp, "
          "%d sayfada pozitif kontrol)."
          % (len(dosyalar), len(KALIPLAR), len(BEKLENEN)))
    print("YEŞİL — iç rapor sızıntı nöbetçisi geçti (%d izlenen dosya tarandı, "
          "%d kırmızı + %d yeşil fikstür, %d istisna)."
          % (taranan, len(_IC_RAPOR_KIRMIZI), len(_IC_RAPOR_YESIL),
             len(IC_RAPOR_ISTISNA)))
    print("YEŞİL — tedarikçi/ürün adı sızıntı nöbetçisi geçti "
          "(%d izlenen dosya içeriği tarandı, %d dar literal)."
          % (ted_taranan, len(_TED_KALIPLAR)))
    print("YEŞİL — parmakızı kayıt adı nöbetçisi geçti (%d ad tarandı, %d kırmızı + "
          "%d yeşil fikstür)." % (pk_taranan, len(_PK_KIRMIZI), len(_PK_YESIL)))


if __name__ == "__main__":
    main()
