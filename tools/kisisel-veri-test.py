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

    if hatalar or rapor_hatalari:
        if hatalar:
            print("KIRMIZI — kişisel veri testi %d hata:" % len(hatalar))
            for h in hatalar:
                print("  - " + h)
        if rapor_hatalari:
            print("KIRMIZI — iç rapor sızıntı nöbetçisi %d hata:" % len(rapor_hatalari))
            for h in rapor_hatalari:
                print("  - " + h)
        sys.exit(1)
    print("YEŞİL — kişisel veri testi geçti (%d sayfa, %d kalıp, "
          "%d sayfada pozitif kontrol)."
          % (len(dosyalar), len(KALIPLAR), len(BEKLENEN)))
    print("YEŞİL — iç rapor sızıntı nöbetçisi geçti (%d izlenen dosya tarandı, "
          "%d kırmızı + %d yeşil fikstür, %d istisna)."
          % (taranan, len(_IC_RAPOR_KIRMIZI), len(_IC_RAPOR_YESIL),
             len(IC_RAPOR_ISTISNA)))


if __name__ == "__main__":
    main()
