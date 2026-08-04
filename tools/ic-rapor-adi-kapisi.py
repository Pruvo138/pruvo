#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ic-rapor-adi-kapisi.py — IC ISCI-RAPORU PROTOKOL ADININ ("RAPOR-MIMARA.md")
IZLENEN dosyalarda YORUM/DOKUMANTASYON METNI olarak YENIDEN BELIRMESINI KIRMIZI yakan
regresyon nobetcisi.

NEDEN VAR (4 Agu 2026 olcumu): repo PUBLIC (Pruvo138/pruvo). Isci->mimar rapor
dosyasinin protokol adi (CLAUDE.md ILETISIM PROTOKOLU: "RAPOR ADI: yalniz
RAPOR-MIMARA.md") 20 izlenen dosyada 24 yerde yorum/docstring METNI icinde ATIF
olarak geciyordu ("kanit RAPOR-MIMARA.md'de", "bkz. RAPOR-MIMARA.md" vb.). Bu bir
KISISEL VERI sizintisi DEGIL (tools/kisisel-veri-test.py bu eksende zaten yesildi,
ic olcum/kapi-bypass detayi tasimiyor) — sadece ic is akisinin bir parcasi (rapor
dosyasinin adi) disariya GORUNUYORDU. Bu 24 yer o gun NOTRLESTIRILDI (dosya adi
yerine "muhendis raporunda" gibi anlamini KORUYAN genel ifade). Bu nobetci o
temizligin GERI GELMEMESI icin REGRESYON bekcisidir.

MUAF TUTULAN — 31 isabet, DOKUNULMADI, asagidaki _MUAFIYET_GOVDESI'nde KAYITLI:
  * tools/durum.py (2) — protokol adini FIILEN ARAYAN KOD (os.path.join) + ona
    bagli print etiketi; degistirilirse durum panosunun DAVRANISI degisir.
  * tools/kisisel-veri-test.py (22) — IC RAPOR SIZINTI nobetcisinin KENDI
    fikstur/hata-mesaji VERISI; bu string'ler o nobetcinin gercek KIRMIZI/YESIL
    davranisini ve kullaniciya yazdigi cozum metnini olusturur.
  * tools/olculmemis-siparis-test.py (1) — print() argumani: CALISAN KOD, yorum
    ya da docstring DEGIL.
  * tools/paket-*.md (6) — mimar->muhendis DELEGASYON spec'leri: "rapor adi
    ZORUNLU RAPOR-MIMARA.md" talimatinin KENDISI (protokolun tanimi); genel
    ifadeye cevrilirse gelecekteki iscilerin dogru rapor adini KAYBETMESINE yol
    acar.
  * tools/ic-rapor-adi-kapisi.py — BU DOSYANIN KENDISI: yukaridaki govde,
    docstring ornekleri ve kendini-test fiksturleri deseni DOGRUDAN tasir
    (nobetci deseni TANIMLAMAK icin onu YAZMAK ZORUNDADIR). KENDI_YOLU sabitiyle
    ana_tarama()'da TEK path olarak ELENIR — icerik-hash govdesine GIRMEZ.

Muafiyet GENEL bir desen kacisi DEGILDIR: her kayit (dosya, o SATIRIN TAM
METNININ sha256'si, gerekce) UCLUSUDUR. Satir tek karakter degisirse (baska bir
soze tasinsa/kirpilsa/genisletilse bile) ya da baska bir dosyaya kopyalansa
muafiyet ARTIK GECERSIZDIR ve o satir KIRMIZI yanar — muafiyet KAYITLI GOVDEDEN
turer, path bazli genel bir "bu dosyaya dokunma" kacisi DEGILDIR.

Kullanim:
    python3 tools/ic-rapor-adi-kapisi.py                 # ana repoyu tarar, exit 0/1
    python3 tools/ic-rapor-adi-kapisi.py --kendini-test   # offline kabul testi (izole git)

Cikis kodu: 0 = temiz (ihlal yok), 1 = en az bir IZLENEN dosyada muafiyet-disi
yeni bir "RAPOR-MIMARA" gecisi bulundu (harf-duyarsiz).
"""
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # SALT-OKUNUR tarama: hedef repoya __pycache__ yazma.

DESEN = "rapor-mimara"  # kucuk harfe cevrilmis satirda aranir (harf-duyarsiz)

# KENDI DOSYASI ISTISNASI (govde-disi, TEK path, GEREKCELI): bu nobetci deseni
# TANIMLAMAK icin onu DOGRUDAN tasimak ZORUNDADIR (docstring ornekleri, asagidaki
# _MUAFIYET_GOVDESI'nin literal verisi, kendini-test fiksturleri). Aksi halde
# nobetci KENDI KENDINI kirmizi yakar (bkz. "Nobetci kendi dosyasinda sizdirir"
# dersi — tools/kisisel-veri-test.py de AYNI sebeple KENDI dosyasini tarima disi
# birakir, orada IC RAPOR AILESI regex'i disindaki kendi kaynagini gormez). Bu,
# _muaf_mi() icerik-hash mekanizmasindan TAMAMEN AYRI, tek path'e ozel bir
# kod-yolu istisnasidir — mutasyon eslemesini (IDDIA-1/IDDIA-2) ETKILEMEZ.
KENDI_YOLU = "tools/ic-rapor-adi-kapisi.py"

# ---------------------------------------------------------------------------
# KAYITLI MUAFIYET GOVDESI — 4 Agu 2026 olcumunden turer (31 mesru isabet).
# Her kayit: (repo-gorece dosya, satirin TAM METNI [\n haric], gerekce).
# sha256 asagida OTOMATIK hesaplanir (elle tutulan hash yok -> govde TEK KAYNAK).
# ---------------------------------------------------------------------------
_MUAFIYET_GOVDESI = [
    ('tools/durum.py', '    yol = os.path.join(worktree_yolu, "RAPOR-MIMARA.md")',
     "fiilen kullanilan kod: worktree'deki rapor dosyasini bu adla arar (durum panosu)"),
    ('tools/durum.py', '            print("      RAPOR-MIMARA.md: %s — %s"',
     "yukaridaki aramaya bagli print etiketi (kod, yorum degil)"),
    ('tools/kisisel-veri-test.py', "# KOK SEBEP: mimar spec'lerinde rapor adi standart DEGILDI (RAPOR-MIMARA /",
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '      KIRMIZI: RAPOR-MIMARA.md · CURUTME-RAPORU.md · curutme.md · ONARIM-RAPORU.md ·',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("RAPOR-MIMARA.md", "protokol adi — isci raporu"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("RAPOR-MIMARA.txt", "uzanti degistirerek kacis"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '#     CURUTME-RAPORU-TUR4.md, RAPOR-MIMARA.md).',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("RAPOR-MIMARA.md", "protokol adi; gitignore\'da ama IZLENIRSE B de yakalamali"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', "    'RAPOR-MIMARA.md' gecirir -> substring testi HER mesaji RAPOR-MIMARA ihlali",
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                     "CURUTME-RAPORU.md", "RAPOR-MIMARA.md"]',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                           "CURUTME-RAPORU.md", "RAPOR-MIMARA.md"])',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            "kimlikleri / ic olcum). Cozum: git rm --cached \'%s\' + adi RAPOR-MIMARA.md yap."',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            "Cozum: (a) ic rapor ise \'git rm --cached %s\' + adi RAPOR-MIMARA.md yap "',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '# RAPOR-MIMARA.md hem tools/yedek-topolojisi-raporu.md icin True donuyor. Sorun TANIMA',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("protokol adi RAPOR-MIMARA.md dal push\'unda eklenmis",',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '     _gc(("a" * 40, ["tools/build.py", "RAPOR-MIMARA.md"])),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '     [("a" * 40, "RAPOR-MIMARA.md")]),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '    ("MESRU 4: gitignore\'lu dosya (CLAUDE.md/DEVAM.md/RAPOR-MIMARA.md izlenmez) -> "',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            for ad, icerik in [("RAPOR-MIMARA.md", "ic rapor govdesi\\n"),',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            os.remove(os.path.join(d, "RAPOR-MIMARA.md"))',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            elif isabet != [(ekleyen, "RAPOR-MIMARA.md")]:',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                    "GECMIS KOLU OLU/BOZUK (GERCEK git): silinmis RAPOR-MIMARA.md "',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '                    % ([(ekleyen, "RAPOR-MIMARA.md")], isabet))',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/kisisel-veri-test.py', '            "IZLENMEYEN birak; ad protokolu: RAPOR-MIMARA.md + .gitignore."',
     "IC RAPOR SIZINTI nobetcisinin KENDI fikstur/hata-mesaji verisi"),
    ('tools/olculmemis-siparis-test.py', '    print("      --- CANLI CIKTI (RAPOR-MIMARA.md\'ye aynen yapistir) ---")',
     "print() argumani (calisan kod, yorum/docstring degil)"),
    ('tools/paket-bilesik-marka.md', 'Dalda `RAPOR-MIMARA.md` (bu ad ZORUNLU): iddia sayısı önce/sonra, mutant tablosu',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-durum-panosu.md', '**Dal:** `claude/durum-panosu` (worktree). **Rapor:** `RAPOR-MIMARA.md` + `DEVAM.md`, mesaj YOK.',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-durum-panosu.md', '   `RAPOR-MIMARA.md` var mı (varsa mtime + ilk başlık satırı).',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-durum-panosu.md', '2. `RAPOR-MIMARA.md`: ne yapıldı, 2. madde kırmızı→yeşil kanıtı, araştırma kalemi sonucu,',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-kararsiz-jeton-sinif1.md', "- Dalını `git push -u origin <dal>` ile it, `RAPOR-MIMARA.md`'yi **dalda** bırak (izlenen",
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
    ('tools/paket-uyum-yazma-yolu.md', 'Dalda `RAPOR-MIMARA.md` (başka ad YASAK, izlenen bırakılma): her iddianın ölçülen sayısı, mutant',
     "mimar->muhendis delegasyon speci: rapor adi ZORUNLU talimati (protokolun kendisi)"),
]


def _satir_hash(satir_metni):
    return hashlib.sha256(satir_metni.encode("utf-8")).hexdigest()


def _muafiyet_kumesi_uret(govde):
    """(dosya, sha256(satir)) ciftlerinden KUME uretir — icerik-bagli karsilastirma."""
    return {(dosya, _satir_hash(satir)) for dosya, satir, _gerekce in govde}


def _desenler_bul(icerik):
    """Verilen metin icindeki (satir_no, satir_metni) ciftlerini, DESEN'i (harf-duyarsiz)
    tasiyanlar icin dondurur. Satir sonu \\n HARIC tutulur (hash karsilastirmasi buna gore)."""
    sonuc = []
    for i, satir in enumerate(icerik.splitlines(), start=1):
        if DESEN in satir.lower():
            sonuc.append((i, satir))
    return sonuc


def _muaf_mi(dosya, satir_metni, muafiyet_kumesi):
    """Icerik-bagli muafiyet: (dosya, satirin TAM METNININ hash'i) kayitli mi."""
    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi


def tara(dosya_icerik_ciftleri, govde=_MUAFIYET_GOVDESI):
    """dosya_icerik_ciftleri: iterable[(repo-gorece yol, icerik_str)].
    Dondurur: [(yol, satir_no, satir_metni), ...] — muafiyet-disi TUM isabetler."""
    kume = _muafiyet_kumesi_uret(govde)
    ihlaller = []
    for yol, icerik in dosya_icerik_ciftleri:
        for satir_no, satir in _desenler_bul(icerik):
            if not _muaf_mi(yol, satir, kume):
                ihlaller.append((yol, satir_no, satir))
    return ihlaller


def _git_izlenen_dosyalar(kok):
    r = subprocess.run(["git", "-C", kok, "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    return [y for y in r.stdout.split("\0") if y]


def _oku(kok, yol):
    tam = os.path.join(kok, yol)
    try:
        with open(tam, "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None  # binary / okunamayan dosya -> atla (bu desen yalniz metinde anlamli)


def ana_tarama(kok):
    """GERCEK repo taramasi: yalniz `git ls-files` ile IZLENEN dosyalar. KENDI_YOLU
    (bu betigin kendisi) HARIC tutulur — bkz. yukaridaki gerekce."""
    ciftler = []
    for yol in _git_izlenen_dosyalar(kok):
        if yol == KENDI_YOLU:
            continue
        icerik = _oku(kok, yol)
        if icerik is not None:
            ciftler.append((yol, icerik))
    return tara(ciftler)


# ===========================================================================
# KENDINI-TEST — izole gecici git deposunda offline kabul testi.
# IDDIA-1 / IDDIA-2: mutasyon testinin "TEK KIRMIZI" hedefledigi, SABIT SAYIDA
# (2) DECLARE EDILMIS ana iddia — bkz. tools/mutasyon-dogrulama sureci (bu dosyaya
# YAZMAZ). KONTROL-*: ek saglamlik/yanlis-pozitif kontrolleri; IDDIA kumesinin
# PARCASI DEGILDIR. KONTROL-C E2E oldugu icin IDDIA-2 ile AYNI alt fonksiyonu
# (_desenler_bul) paylasir — "desen kontrolunu no-op yap" mutantinda YAN ETKI
# olarak o da kirmizi yanabilir; bu, IDDIA kumesindeki TEK-KIRMIZI sartini
# BOZMAZ (mutasyon eslemesi yalniz IDDIA-* etiketlerine bakar).
# ===========================================================================
def _kendini_test():
    sonuclar = []  # [(etiket, gecti_mi, detay)]

    # --- Birim-seviyeli iddialar (tara() alt-fonksiyonlarini DOGRUDAN cagirir;
    #     boylece her mutant TEK bir fonksiyonu vurur, TEK bir iddiayi kirar.) ---
    kume = _muafiyet_kumesi_uret(_MUAFIYET_GOVDESI)

    # IDDIA-1 (icerik-bagli muafiyet): kayitli DOSYA + DEGISTIRILMIS satir ->
    # MUAF SAYILMAMALI (yalniz path'e degil, TAM ICERIGE bakar).
    kayitli_dosya, kayitli_satir, _g = _MUAFIYET_GOVDESI[0]
    degistirilmis = kayitli_satir + " EKSTRA-KELIME"
    iddia1 = not _muaf_mi(kayitli_dosya, degistirilmis, kume)
    sonuclar.append(("IDDIA-1 icerik-bagli-muafiyet", iddia1,
                      "ayni dosya, degistirilmis satir muaf SAYILMAMALI"))

    # IDDIA-2 (yeni ihlal yakalanir): daha once hic gorulmemis bir satirda,
    # KARISIK BUYUK/KUCUK harfle DESEN gecerse yakalanmali.
    yeni_satir_no_eslesme = _desenler_bul("bir satir\nkanit RaPoR-MiMaRa'da olculdu\nbaska satir")
    iddia2 = len(yeni_satir_no_eslesme) == 1 and yeni_satir_no_eslesme[0][0] == 2
    sonuclar.append(("IDDIA-2 yeni-ihlal-yakalanir", iddia2,
                      "harf-duyarsiz yeni gecis satir 2'de yakalanmali"))

    # --- KONTROL'ler: mutasyona hedef DEGIL, genel saglamlik/yanlis-pozitif nobeti. ---
    kontrol_a = _muaf_mi(kayitli_dosya, kayitli_satir, kume)
    sonuclar.append(("KONTROL-A kayitli-satir-yesil", kontrol_a,
                      "govdedeki satir BIREBIR ise muaf sayilmali"))

    kontrol_b = _desenler_bul("bu satirda ilgili desen yok\nbaska bir baslik ## Ozet") == []
    sonuclar.append(("KONTROL-B desensiz-satir-yesil", kontrol_b,
                      "desen gecmeyen metin hic isaretlenmemeli"))

    # KONTROL-C: uctan-uca (gercek gecici git deposu + `git ls-files`) — kayitli
    # muafiyet GERCEK bir tarama akisinda da yesil kalir; kayit-disi yeni satir
    # GERCEK akiste de kirmizi yanar. E2E oldugu icin mutasyon eslemesine DAHIL
    # EDILMEZ (birden fazla ic fonksiyonu birden aynı anda sinar).
    with tempfile.TemporaryDirectory() as d:
        g = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)
        g("init", "-q")
        g("config", "user.email", "test@test.local")
        g("config", "user.name", "test")
        os.makedirs(os.path.join(d, "tools"), exist_ok=True)
        with open(os.path.join(d, "tools", "durum.py"), "w", encoding="utf-8") as f:
            f.write(kayitli_satir + "\n")
        with open(os.path.join(d, "yeni-dosya.py"), "w", encoding="utf-8") as f:
            f.write("# gordu: RAPOR-MIMARA.md burada YENI bir yerde geciyor\n")
        g("add", "-A")
        e2e = ana_tarama(d)
        e2e_muaf_yesil = not any(y == "tools/durum.py" for y, _sn, _s in e2e)
        e2e_yeni_kirmizi = any(y == "yeni-dosya.py" for y, _sn, _s in e2e)
        kontrol_c = e2e_muaf_yesil and e2e_yeni_kirmizi
        sonuclar.append(("KONTROL-C uctan-uca-git-akisi", kontrol_c,
                          "e2e: kayitli satir yesil, yeni satir kirmizi (isabet=%r)" % (e2e,)))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true",
                     help="offline kabul testi (izole gecici git deposu, ag YOK)")
    args = ap.parse_args()

    if args.kendini_test:
        return _kendini_test()

    kok = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip()
    if not kok:
        sys.exit("git kok dizini bulunamadi (bu bir git deposu mu?)")
    ihlaller = ana_tarama(kok)
    if not ihlaller:
        print("IC RAPOR ADI KAPISI: temiz (0 muafiyet-disi isabet).")
        return 0
    print("IC RAPOR ADI KAPISI: %d muafiyet-disi isabet bulundu:" % len(ihlaller))
    for yol, satir_no, satir in ihlaller:
        print("  %s:%d: %s" % (yol, satir_no, satir.strip()))
    print()
    print("COZUM: yorum/docstring METNINDEN dosya adini kaldir, anlamini koruyarak")
    print("genel ifadeyle yeniden yaz (or. 'muhendis raporunda'). Fiilen kullanilan")
    print("kod / delegasyon speci ise (bkz. bu dosyanin basligindaki MUAF listesi)")
    print("yukaridaki _MUAFIYET_GOVDESI'ne GEREKCEYLE ekle.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
