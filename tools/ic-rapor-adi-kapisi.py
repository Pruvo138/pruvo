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

🔴 HANGI AGACI OLCER — 5 Agu 2026 OLCULEN KUSUR ("kapi yanlis agacta yesil yakiyor"):
Bu kapi taranacak kokunu ONCEDEN `git rev-parse --show-toplevel` ile CWD'den
turetiyordu. Sonuc: DALIN dosyalarini yargiladigi SANILAN kosum aslinda ANA
CHECKOUT'u tariyordu ve `exit 0` veriyordu. Olculen zarar: bir merge kapisi turunda
izlenen bir kaynak dosyada ic isci-raporu protokol adi sizmisken kapi ana
checkout'tan YESIL yandi; ayni dal yalniz `cwd=dal worktree` ile kosuldugunda rc=1
verdi. Kapi CI'da BLOKLAYICIDIR (continue-on-error YOK) -> sizinti merge edilseydi
yayinlanacakti.

ONARIM — KOK ARTIK CWD'DEN TUREMEZ:
  1. `--kok YOL` ile olculecek agac ACIKCA verilebilir (her yerden kosar).
  2. Bayraksiz varsayilan = BETIGIN KENDI AGACI (`__file__` -> `git -C ... --show-toplevel`),
     CWD DEGIL. CI'da betik zaten checkout edilen agacta yasar -> bayraksiz davranis
     DOGRUDUR; bir worktree'nin KENDI kopyasi da her zaman KENDI agacini olcer.
  3. BELIRSIZLIK FAIL-CLOSED'DIR: bayrak verilmemis VE cwd'nin agaci betigin
     agacindan FARKLIYSA hukum verilmez -> rc 2 (OLCULEMEDI). Cunku o an hangi
     agacin sorulduğu betikten ANLASILAMAZ; sessiz bir yesil/kirmizi YANLIS AGACA
     atfedilebilir. Cikis yolu susturma degil, `--kok` ile agaci SOYLEMEKTIR.
  4. Olculen kok + taranan dosya sayisi HER kosumda (yesilde de) BASILIR — bir
     yesil artik sessizce baska bir agaca atfedilemez.

🔴 KOK TURETIMI ORTAMDAN BAGIMSIZDIR (6 Agu 2026 onarimi, gizil kusur):
Kok `git -C <yol> rev-parse --show-toplevel` ile turer. Bir GIT KANCASI icinden
kosuldugunda cagiran surec git baglam degiskenlerini IHRAC EDER; linked worktree
kancasinda GIT_DIR MUTLAK gelir ve GIT_WORK_TREE bostur -> git depo KESFINI ATLAR,
CARI DIZINI agacin tepesi sayar ve ACIK `-C` hedefi SESSIZCE EZILIR. Olculdu (sentetik
depo + gercek `git worktree add` + gercek `git commit`): kanca icinden kosan bu kapi
"betik agaci = <worktree>/tools" bulup rc=2 OLCULEMEDI veriyordu — commit BLOKLANIR,
isci `--no-verify`ye itilir (yani kusur kapinin KENDISINI atlatmayi normallestirir).
CARE: git cagrilari miras alinan git baglami SILINMIS ortamda kosar; scrub'in TEK
tanimi tools/git_ortami.py'dir (FALLBACK YOK — modul yoksa cagri coker).
Kabul: IDDIA-6, mutant MUT-KOK-ORTAM.

🔴 UZAK DAL GECMISI EKSENI — 10 Agu 2026 OLCULEN KUSUR ("kapi yesilken sizinti PUBLIC"):
Yukaridaki kol YALNIZ `git ls-files` ile IZLENEN CALISMA AGACINI tarar. Bir dal
push'landiktan sonra o dalin AGACI uzakta (PUBLIC) durur ve bu kapinin gorus alanina
HIC girmez. Olculdu (55 uzak dal, `ls-tree` ile fiilen tarandi): UC yabancı uzak dalda
ic curutme raporu duruyordu ve HER iki kapi da (bu kol + tools/kisisel-veri-test.py'nin
calisma-agaci kolu) YESIL yaniyordu. tools/kisisel-veri-test.py'nin GECMIS kolu da bu
sinifi kapatMAZ: o kol PRE-PUSH kancasidir ve YALNIZ o itmenin GETIRDIGI araligi olcer
-> kanca kurulu OLMAYAN makineden, `--no-verify` ile ya da kanca yazilmadan ONCE
push'lanmis dallar hicbir zaman olculmez. Bu kol o KALICI DURUMU olcer: "su anda uzakta
ne duruyor".

  * EVREN: `git ls-remote --heads <uzak>` -> her dalin `git ls-tree -r` AGACI.
  * DESEN ELLE TUTULMAZ: ic rapor ADLANDIRMA ailesinin TEK KAYNAGI
    tools/kisisel-veri-test.py'dir (`ic_rapor_mu`); buradan IMPORT edilir, KOPYALANMAZ
    ([[ikiz-tanim-sessiz-ayrisma]], [[kapsam-evrenini-cagri-grafindan-turet]]). Kanonik
    kaynak yoksa / API'si taninmiyorsa / KENDI kirmizi-yesil fiksturlerini karsilamiyorsa
    hukum VERILMEZ -> rc 2. Yerel bir "yedek desen" YAZILMAZ: o dusus yolu ikizin ta
    kendisidir ve gevsek yonde ayrisir.
  * FAIL-CLOSED: taninmayan `ls-remote` satiri, okunamayan agac (SIG/shallow klon ->
    nesne yok), BOS dal listesi ve BOS agac "temiz" DEGIL, OLCULEMEDI'dir.
  * 🔴 CI'DA BLOKLAYICI DEGIL — GEREKCE OLCULDU: (a) AG ister (tek gecici oran-siniri/
    DNS hatasi tum ekibin yayinini durdururdu); (b) YARIS: checkout'tan SONRA push'lanan
    bir dalin NESNELERI yerelde YOKTUR -> kol o kosumda fail-closed rc=2 verir, yani
    kirmizisi ARALIKLI ve yayindan BAGIMSIZ bir sebeple gelir; (c) TAMIR DEGERI SIFIR:
    olculen sey UZAKTA DURAN bir daldir, main'e girmez, siteye cikmaz — tek onarim uzak
    dali silmektir ([[fail-slow-fail-opendir]], [[maliyet-tasimasi-serit-dusurur]]).
    ⚠️ DUZELTME (10 Agu, kaynaktan olculdu): "deploy.yml fetch-depth VERMEDEN checkout
    eder" iddiasi YANLISTI — bu aracin bloklayici kollarini tasiyan `serit-a3` (ayrica
    `build` ve `serit-a2`) `fetch-depth: 0` kullanir; fetch-depth'siz olan yalniz
    `serit-a4` ve `yayin`'dir. Serit secimi (a)+(b)+(c)'ye dayanir, klon DERINLIGINE degil.
    Bagli oldugu yer: nobet.yml SERIT B (`fetch-depth: 0`, yayini BLOKLAMAZ).
  * ONLEME DEGIL TESPIT: onleme kolu pre-push kancasidir (tools/kisisel-veri-test.py
    --pre-push). Bu kol o kolun kacirdigi KALICI durumu gorunur kilar.
  * 🔴 EKSIK NESNE YARISI (11 Agu 2026 OLCULDU, kosum 31433971660 / serit-b): `ls-remote`
    CANLI uzagi okur, yerel klon ise CHECKOUT anindaki nesneleri tasir. Kosum arasinda
    ilerleyen bir dalin SHA'si yerelde YOKTUR -> `ls-tree` "not a tree object" ile duser
    -> rc=2 OLCULEMEDI. O turda GERCEK ihlal YOKTU (bir sonraki kosum 31435535409 yesil,
    52 dal / 0 isabet); yani bu, her ESZAMANLI push'ta tekrarlayan bir YARISTIR.
    ONARIM: `ls-tree` duserse KOSUM BASINA BIR KEZ dar bir `git fetch` denenir ve
    `ls-tree` BIR kez tekrarlanir (52 dal icin 52 fetch YASAK: sonuc hatirlanir).
    🔴 FAIL-CLOSED KORUNUR: tekrar da duserse hukum yine OLCULEMEDI'dir — AYNI hata
    ailesi + fetch'in rc'si EKLENIR; "temiz"e DONULMEZ. 🔴 AGA CIKMA KAPISI: fetch
    yalniz GERCEK `_git_ls_tree` kullanilirken ya da kosucu TESTTEN enjekte edilmisken
    denenir; kanned `ls_tree` ile kosan kendini-test/mutasyon cagrilari ASLA aga cikmaz.
    Kabul: IDDIA-11..IDDIA-14 + KONTROL-I.

Kullanim:
    python3 tools/ic-rapor-adi-kapisi.py                 # BETIGIN agacini tarar, exit 0/1
    python3 tools/ic-rapor-adi-kapisi.py --kok /yol/dal  # ACIKCA verilen agaci tarar
    python3 tools/ic-rapor-adi-kapisi.py --uzak          # UZAK DAL AGACLARINI tarar (ag)
    python3 tools/ic-rapor-adi-kapisi.py --kendini-test   # offline kabul testi (izole git)

Cikis kodu: 0 = temiz (ihlal yok), 1 = en az bir IZLENEN dosyada muafiyet-disi
yeni bir "RAPOR-MIMARA" gecisi bulundu (harf-duyarsiz) ya da bir UZAK DALIN agacinda
ic rapor ADLANDIRMA ailesine uyan dosya duruyor, 2 = OLCULEMEDI (fail-closed: agac
belirsiz / verilen yol git agaci degil / kanonik aile kaynagi okunamadi / uzak evren
taninmadi).
"""
import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # SALT-OKUNUR tarama: hedef repoya __pycache__ yazma.

# Betigin KENDI dizini. Kok bundan turer -> CWD ne olursa olsun AYNI agac olculur.
BETIK_DIZINI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BETIK_DIZINI)
# 🔴 TEK KAYNAK ([[ikiz-tanim-sessiz-ayrisma]]): git baglam scrub'i ve onunla kok
# turetimi tools/git_ortami.py'de TANIMLIDIR. Burada `try/except ImportError -> yerel
# tanim` YAZILMAZ: o dusus yolu ikizin ta kendisidir ve gevsek yonde ayrisir.
from git_ortami import git_kok, git_ortami, sentetik_git   # noqa: E402
from git_ortami import worktree_kanca_kok_olcumu   # noqa: E402

DESEN = "rapor-mimara"  # kucuk harfe cevrilmis satirda aranir (harf-duyarsiz)

RC_TEMIZ = 0
RC_IHLAL = 1
RC_OLCULEMEDI = 2  # fail-closed: hangi agacin sorulduğu belirsiz / yol git agaci degil

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
    ('tools/paket-ozet-butce.md', '- Dal: `muh/ozet-butce-payi`. Rapor: dalda `RAPOR-MIMARA.md` (başka ad YASAK, izlenen bırakılmaz).',
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


def _git_kok(dizin):
    """dizin'in AIT OLDUGU git agacinin kokunu doner ("" = git agaci degil).

    🔴 `-C dizin` ZORUNLU: argumansiz `git rev-parse --show-toplevel` CWD'ye bakar —
    5 Agu 2026'da olculen kusur tam olarak buydu. Burada cwd'nin HICBIR etkisi yoktur.
    🔴 ORTAM ACIKCA TEMIZ VERILIR: miras alinan GIT_DIR/GIT_WORK_TREE acik `-C` hedefini
    SESSIZCE ezer (kanca + linked worktree baglami; 6 Agu 2026 onarimi, IDDIA-6).
    Scrub'in TANIMI tools/git_ortami.py'dedir; burasi yalniz o secimi TASIR."""
    return git_kok(dizin, git_ortami())


def kok_coz(arg_kok, cwd, betik_dizini=BETIK_DIZINI):
    """Olculecek agaci belirler. Dondurur: (kok, hata).

    hata != None -> hukum VERILMEZ, rc RC_OLCULEMEDI (fail-closed).
      * arg_kok verilmisse O agac olculur (cwd de betik dizini de ETKISIZ).
      * verilmemisse BETIGIN agaci olculur; ancak cwd BASKA bir git agacindaysa
        hangi agacin soruldugu belirsizdir -> OLCULEMEDI (sessiz yanlis-atif yerine
        gurultulu durus)."""
    if arg_kok:
        k = _git_kok(arg_kok)
        if not k:
            return None, ("--kok ile verilen yol bir git agaci DEGIL: %s" % arg_kok)
        return k, None
    betik_kok = _git_kok(betik_dizini)
    if not betik_kok:
        return None, ("betigin bulundugu agac bir git deposu DEGIL: %s "
                      "(cozum: --kok ile olculecek agaci ver)" % betik_dizini)
    cwd_kok = _git_kok(cwd)
    if cwd_kok and os.path.realpath(cwd_kok) != os.path.realpath(betik_kok):
        return None, (
            "AGAC BELIRSIZ (fail-closed) — betigin agaci ile calisma dizininin agaci "
            "FARKLI:\n  betik agaci: %s\n  cwd  agaci : %s\n"
            "Hangi agacin olculecegi betikten anlasilamaz; sessiz bir YESIL yanlis "
            "agaca atfedilebilir (5 Agu 2026'da olculen kusur budur).\n"
            "COZUM: agaci ACIKCA soyle -> --kok %s" % (betik_kok, cwd_kok, cwd_kok))
    return betik_kok, None


def _git_izlenen_dosyalar(kok):
    # Ortam ayni sebeple temiz: kanca baglamindan kosuldugunda miras alinan GIT_DIR
    # `-C kok` hedefini ezip BASKA bir agacin indeksini listeleyebilir.
    r = subprocess.run(["git", "-C", kok, "ls-files", "-z"], capture_output=True,
                       text=True, env=git_ortami())
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
    """GERCEK repo taramasi: `kok` AGACINDA `git -C kok ls-files` ile IZLENEN dosyalar.
    KENDI_YOLU (bu betigin kendisi) HARIC tutulur — bkz. yukaridaki gerekce.
    Dondurur: (ihlaller, taranan_dosya_sayisi) — sayi cikti'da BASILIR ki bir
    "temiz" hukmu hangi agacta/kac dosyada olculdugu bilinmeden atfedilemesin."""
    ciftler = []
    for yol in _git_izlenen_dosyalar(kok):
        if yol == KENDI_YOLU:
            continue
        icerik = _oku(kok, yol)
        if icerik is not None:
            ciftler.append((yol, icerik))
    return tara(ciftler), len(ciftler)


# ===========================================================================
# UZAK DAL GECMISI KOLU (`--uzak`) — bkz. dosya basligindaki gerekce.
# ===========================================================================
# Ic rapor ADLANDIRMA ailesinin KANONIK kaynagi. Bu dosyada aile YENIDEN TANIMLANMAZ:
# desen bir DEFTER degildir, bayatlar; kanonik kaynak ne diyorsa o olculur.
KANON_DOSYA = "kisisel-veri-test.py"
# Kanonik kaynaktan BEKLENEN API. Biri yoksa BICIM TANINMIYOR demektir -> OLCULEMEDI.
# (Predikat + kaynagin KENDI kirmizi/yesil fiksturleri; sozlesme onlarla dogrulanir.)
_KANON_API = ("ic_rapor_mu", "_IC_RAPOR_KIRMIZI", "_IC_RAPOR_YESIL")
UZAK_REF_ONEKI = "refs/heads/"


def kanonik_aile(kanon_dizin=BETIK_DIZINI):
    """(predikat, hata). Ic rapor ADLANDIRMA ailesini KANONIK kaynaktan TURETIR.

    🔴 FALLBACK YOK: kaynak yoksa/yuklenemiyorsa/API'si taninmiyorsa hukum VERILMEZ.
    Burada yerel bir "yedek desen" yazmak IKIZ TANIM uretir ve sessizce ayrisir.
    SOZLESME AYAGI: kanonik kaynak KENDI kirmizi/yesil fiksturlerini karsilamiyorsa
    (olu/bozuk predikat) yine OLCULEMEDI — "yesil" o hale atfedilemez."""
    yol = os.path.join(kanon_dizin, KANON_DOSYA)
    if not os.path.isfile(yol):
        return None, ("KANONIK AILE KAYNAGI YOK: %s — desen bu dosyada YENIDEN "
                      "YAZILMAZ (ikiz tanim). Cozum: --kanon-dizin ile kaynagi ver."
                      % yol)
    try:
        spec = importlib.util.spec_from_file_location("_pruvo_ic_rapor_kanon", yol)
        modul = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = modul
        eski_yol = list(sys.path)
        sys.path.insert(0, kanon_dizin)
        try:
            spec.loader.exec_module(modul)
        finally:
            sys.path[:] = eski_yol
    except BaseException as e:                                # noqa: BLE001
        return None, ("KANONIK AILE KAYNAGI YUKLENEMEDI (%s): %r" % (yol, e))
    eksik = [a for a in _KANON_API if not hasattr(modul, a)]
    if eksik:
        return None, ("KANONIK AILE API'si TANINMIYOR (%s): eksik %s — bicim degismis "
                      "olabilir; hukum VERILMEZ" % (yol, eksik))
    predikat = getattr(modul, "ic_rapor_mu")
    kirmizi = list(getattr(modul, "_IC_RAPOR_KIRMIZI"))
    yesil = list(getattr(modul, "_IC_RAPOR_YESIL"))
    if not callable(predikat) or not kirmizi or not yesil:
        return None, ("KANONIK AILE SOZLESMESI BOS/TANINMIYOR (%s): predikat=%r "
                      "kirmizi=%d yesil=%d" % (yol, predikat, len(kirmizi), len(yesil)))
    for kayit in kirmizi:
        if not predikat(kayit[0]):
            return None, ("KANONIK AILE OLU/BOZUK (%s): kendi KIRMIZI fiksturu "
                          "yakalanmiyor (%r)" % (yol, kayit[0]))
    for kayit in yesil:
        if predikat(kayit[0]):
            return None, ("KANONIK AILE ASIRI GENIS (%s): kendi YESIL fiksturu "
                          "yaniyor (%r)" % (yol, kayit[0]))
    return predikat, None


def uzak_dallari_ayristir(ham):
    """`git ls-remote --heads <uzak>` ciktisi -> ([(sha, dal), ...], hata).

    GERCEK BICIM: '<sha>\\t refs/heads/<ad>' satirlari. TANINMAYAN satir ATLANMAZ:
    atlamak evreni SESSIZCE kucultur ve "0 isabet" hukmunu yanlis atfeder."""
    dallar = []
    hatali = []
    for satir in (ham or "").splitlines():
        if not satir.strip():
            continue
        parca = satir.split("\t")
        if (len(parca) != 2 or len(parca[0].strip()) < 7
                or not parca[1].strip().startswith(UZAK_REF_ONEKI)):
            hatali.append(satir[:70])
            continue
        ad = parca[1].strip()[len(UZAK_REF_ONEKI):]
        if not ad:
            hatali.append(satir[:70])
            continue
        dallar.append((parca[0].strip(), ad))
    if hatali:
        return None, ("TANINMAYAN `ls-remote` SATIR BICIMI (fail-closed): %d satir "
                      "cozulemedi, ornek %r" % (len(hatali), hatali[:3]))
    return dallar, None


def _git_ls_remote(kok, uzak):
    """(rc, stdout, stderr). AG GEREKTIRIR. Ortam ayni sebeple temiz (kanca baglami)."""
    try:
        r = subprocess.run(["git", "-C", kok, "ls-remote", "--heads", uzak],
                           capture_output=True, text=True, env=git_ortami())
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr


def _git_ls_tree(kok, sha):
    """(rc, stdout, stderr). NUL-ayrilmis, OZYINELI dosya yolu listesi."""
    try:
        r = subprocess.run(["git", "-C", kok, "ls-tree", "-r", "--name-only", "-z", sha],
                           capture_output=True, text=True, env=git_ortami())
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    return r.returncode, r.stdout, r.stderr


# EKSIK NESNE YARISI icin TAZELEME (bkz. dosya basligi): dar + deterministik.
# Etiket CEKILMEZ, cikti YUTULUR, SURE SINIRLIDIR — ag arizasinda kol asilamaz.
FETCH_ZAMAN_ASIMI = 120  # saniye
# 🔴 REFSPEC ACIKCA VERILIR, YAPILANDIRMAYA GUVENILMEZ: CI checkout'u (ve
# `clone --depth`) `remote.origin.fetch`'i TEK DALA daraltir; yapilandirilmis
# refspec'e birakilan bir fetch, olculen evrenin (TUM uzak dallar) nesnelerini
# GETIRMEZ ve tazeleme sessizce ETKISIZ kalirdi. Hedef, origin'in izleme
# dallarini EZMEYEN AYRI bir ad alanidir; `--prune` ile kendi kendini toplar
# ve `uzak` bir AD yerine URL oldugunda da gecerli bir ref adi uretir.
FETCH_REFSPEC = "+refs/heads/*:refs/pruvo-uzak-kapi/*"


def _git_fetch(kok, uzak):
    """(rc, stdout, stderr). AG GEREKTIRIR — YALNIZ eksik nesne yarisinda, KOSUM
    BASINA BIR KEZ cagrilir. Ortam ayni sebeple temiz (kanca baglami)."""
    try:
        r = subprocess.run(["git", "-C", kok, "fetch", "--no-tags", "--prune",
                            "--quiet", uzak, FETCH_REFSPEC],
                           capture_output=True, text=True, env=git_ortami(),
                           timeout=FETCH_ZAMAN_ASIMI)
    except OSError as e:
        return 127, "", "git calistirilamadi: %s" % e
    except subprocess.TimeoutExpired:
        return 124, "", "fetch ZAMAN ASIMI (%s sn)" % FETCH_ZAMAN_ASIMI
    return r.returncode, r.stdout, r.stderr


def yeni_fetch_durumu():
    """KOSUM BASINA TEK fetch muhasebesi. 52 dalin her biri icin fetch kosmak
    kolu kullanilamaz hale getirirdi; ilk eksik nesnede BIR kez kosulur, sonuc
    HATIRLANIR, kalan dallar ayni tazelenmis klondan okunur.
    {'sayac': kac kez kosuldu, 'rc': o kosumun rc'si, 'hata': stderr ozeti}."""
    return {"sayac": 0, "rc": None, "hata": ""}


def uzak_agac_yollari(kok, sha, ls_tree=None, fetch=None, fetch_durumu=None,
                      uzak="origin"):
    """(yollar, hata). OZYINELI olmali: alt dizindeki rapor da EVRENE girer.

    `ls-tree` duserse (olculen sebep: checkout'tan SONRA push'lanan dalin NESNESI
    yerelde YOK) KOSUM BASINA BIR KEZ `fetch` denenir ve `ls-tree` BIR kez
    tekrarlanir. Fail-closed KORUNUR: ikinci deneme de duserse hata AYNI ailedendir
    ve fetch'in rc'sini TASIR — hicbir kolda "temiz" hukmune DUSULMEZ.

    🔴 AGA CIKMA KAPISI: fetch yalniz `fetch` kosucusu ENJEKTE edilmisken ya da
    GERCEK `_git_ls_tree` kullanilirken (ls_tree is None) denenir. Kanned `ls_tree`
    ile kosan cagrilar (kendini-test/mutasyon) aga CIKMAZ.
    🔴 TETIK rc'dir, git'in HATA METNI DEGIL: mesaj metni bir DEFTERDIR ve bayatlar
    ("not a tree object" / "bad object" / "Not a valid object name"); tek fetch
    tavani zaten ucuz tuttugu icin her rc!=0 tazeleme denemesini hak eder."""
    kosucu = ls_tree or _git_ls_tree
    rc, cikti, hata = kosucu(kok, sha)
    fetch_notu = ""
    if rc != 0 and (fetch is not None or ls_tree is None):
        durum = fetch_durumu if fetch_durumu is not None else yeni_fetch_durumu()
        if durum["sayac"] == 0:
            durum["sayac"] += 1
            f_rc, _f_cikti, f_hata = (fetch or _git_fetch)(kok, uzak)
            durum["rc"] = f_rc
            durum["hata"] = (f_hata or "").strip()[:120]
        fetch_notu = ("\nTAZELEME: `git fetch` bu kosumda 1 kez kosuldu (rc=%s) %s"
                      % (durum["rc"], durum["hata"]))
        if durum["rc"] == 0:
            rc, cikti, hata = kosucu(kok, sha)
    if rc != 0:
        return None, ("UZAK DAL AGACI OKUNAMADI (fail-closed, sha=%s): %s\nSIG "
                      "(shallow) klonda uzak dal NESNELERI yoktur. Cozum: "
                      "git fetch --prune origin%s"
                      % (sha[:12], (hata or "").strip()[:120], fetch_notu))
    yollar = [y for y in cikti.split("\0") if y]
    if not yollar:
        return None, ("BOS AGAC (fail-closed, sha=%s): 0 dosya listelendi — 'temiz' "
                      "DEGIL, OLCULEMEDI" % sha[:12])
    return yollar, None


def uzak_tarama(kok, uzak="origin", predikat=None, ls_remote=None, ls_tree=None,
                fetch=None):
    """(isabetler, dal_sayisi, hata). isabet = (dal, sha, yol).

    Hukum SIRASI fail-closed'dir: kanonik aile -> evren -> her dalin agaci. Herhangi
    biri olculemezse "0 isabet" BASILMAZ. Tazeleme muhasebesi TUM dallar icin ORTAK
    tutulur -> fetch KOSUM BASINA en fazla 1 kez kosar."""
    if predikat is None:
        predikat, kanon_hata = kanonik_aile()
        if kanon_hata:
            return None, 0, kanon_hata
    rc, cikti, hata = (ls_remote or _git_ls_remote)(kok, uzak)
    if rc != 0:
        return None, 0, ("`git ls-remote --heads %s` BASARISIZ (rc=%s): %s"
                         % (uzak, rc, (hata or "").strip()[:200]))
    dallar, ayristirma_hatasi = uzak_dallari_ayristir(cikti)
    if ayristirma_hatasi:
        return None, 0, ayristirma_hatasi
    if not dallar:
        return None, 0, ("BOS KAPSAM (fail-closed): `%s` uzaginda 0 dal listelendi — "
                         "rc=0 + bos cikti 'temiz' DEGIL" % uzak)
    isabetler = []
    fetch_durumu = yeni_fetch_durumu()
    for sha, dal in dallar:
        yollar, agac_hatasi = uzak_agac_yollari(kok, sha, ls_tree=ls_tree, fetch=fetch,
                                                fetch_durumu=fetch_durumu, uzak=uzak)
        if agac_hatasi:
            return None, len(dallar), ("dal %s: %s" % (dal, agac_hatasi))
        for yol in yollar:
            if predikat(yol):
                isabetler.append((dal, sha, yol))
    return sorted(isabetler), len(dallar), None


def _uzak_kolu(kok, uzak, kanon_dizin):
    """`--uzak` kolunun cikis kodu. Olculen evren HER kosumda (yesilde de) BASILIR."""
    predikat, kanon_hata = kanonik_aile(kanon_dizin)
    if kanon_hata:
        print("UZAK DAL KAPISI: OLCULEMEDI (fail-closed KIRMIZI)", file=sys.stderr)
        print(kanon_hata, file=sys.stderr)
        return RC_OLCULEMEDI
    isabetler, dal_sayisi, hata = uzak_tarama(kok, uzak, predikat=predikat)
    if hata:
        print("UZAK DAL KAPISI: OLCULEMEDI (fail-closed KIRMIZI)", file=sys.stderr)
        print(hata, file=sys.stderr)
        return RC_OLCULEMEDI
    print("UZAK DAL KAPISI: olculen uzak = %s (%d dal agaci tarandi), yerel agac = %s"
          % (uzak, dal_sayisi, kok))
    if not isabetler:
        print("UZAK DAL KAPISI: temiz (0 ic rapor dosyasi).")
        return RC_TEMIZ
    print("UZAK DAL KAPISI: %d UZAK DAL ISABETI (PUBLIC repoda DURUYOR):"
          % len(isabetler))
    for dal, sha, yol in isabetler:
        print("  dal=%s sha=%s dosya=%s" % (dal, sha[:12], yol))
    print()
    print("COZUM: dalin main'de OLMAYAN isini once YEREL bir yedek dalda emniyete al")
    print("(varligini `git rev-parse` ile KANITLA), sonra uzak dali sil. Dal artik/")
    print("zombi ise dogrudan sil. Kapanis olcumu 'sildim' degil, bu kolun TEKRAR")
    print("kosulmus 0 isabetidir.")
    return RC_IHLAL


# ===========================================================================
# KENDINI-TEST — izole gecici git deposunda offline kabul testi.
# IDDIA-1..IDDIA-14: mutasyon testinin "TEK KIRMIZI" hedefledigi, SABIT SAYIDA
# (14) DECLARE EDILMIS ana iddia — surucusu REPODA durur: `--mutasyon` kolu.
#   1-2 = desen/muafiyet ekseni · 3-5 = KOK ekseni (5 Agu 2026 olculen "yanlis agacta
#   yesil" kusuru) · 6 = WORKTREE+KANCA baglami (6 Agu 2026 olculen "kok ortamdan
#   turuyor" kusuru; DAVRANISSAL: gercek worktree + gercek commit + gercek kanca)
#   · 7-10 = UZAK DAL GECMISI ekseni (10 Agu 2026 olculen "kapi yesilken 3 uzak dalda
#   ic rapor PUBLIC" kusuru): 7 isabet, 8 taninmayan evren fail-closed, 9 GERCEK git
#   ozyineli agac, 10 kanonik aile kaynagi fail-closed (ikiz tanim yasagi)
#   · 11-14 = EKSIK NESNE YARISI ekseni (11 Agu 2026 olculen "yayin YARISTA rc=2"
#   kusuru): 11 tazeleme+tekrar sonrasi hukum VERILIR, 12 tazelemeye RAGMEN okunamayan
#   agac hala OLCULEMEDI (fail-closed), 13 kanned kosuculu kollar AGA CIKMAZ, 14 fetch
#   KOSUM BASINA en fazla 1 kez.
#   KONTROL-*: ek saglamlik/yanlis-pozitif kontrolleri; IDDIA kumesinin
# PARCASI DEGILDIR. KONTROL-C E2E oldugu icin IDDIA-2 ile AYNI alt fonksiyonu
# (_desenler_bul) paylasir — "desen kontrolunu no-op yap" mutantinda YAN ETKI
# olarak o da kirmizi yanabilir; bu, IDDIA kumesindeki TEK-KIRMIZI sartini
# BOZMAZ (mutasyon eslemesi yalniz IDDIA-* etiketlerine bakar).
# ===========================================================================
def _kendini_test(kanon_dizin=BETIK_DIZINI):
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
        g = lambda *a: sentetik_git(d, *a, capture_output=True, text=True,
                                    kimlik_ad="t", kimlik_eposta="t@t.local")
        g("init", "-q")
        os.makedirs(os.path.join(d, "tools"), exist_ok=True)
        with open(os.path.join(d, "tools", "durum.py"), "w", encoding="utf-8") as f:
            f.write(kayitli_satir + "\n")
        with open(os.path.join(d, "yeni-dosya.py"), "w", encoding="utf-8") as f:
            f.write("# gordu: RAPOR-MIMARA.md burada YENI bir yerde geciyor\n")
        g("add", "-A")
        e2e, _sayi = ana_tarama(d)
        e2e_muaf_yesil = not any(y == "tools/durum.py" for y, _sn, _s in e2e)
        e2e_yeni_kirmizi = any(y == "yeni-dosya.py" for y, _sn, _s in e2e)
        kontrol_c = e2e_muaf_yesil and e2e_yeni_kirmizi
        sonuclar.append(("KONTROL-C uctan-uca-git-akisi", kontrol_c,
                          "e2e: kayitli satir yesil, yeni satir kirmizi (isabet=%r)" % (e2e,)))

    # --- KOK EKSENI (5 Agu 2026 olculen kusur: kapi YANLIS AGACTA yesil yakiyordu) ---
    # Ucu de kok_coz()/main() uzerinden AYRI birer davranisi olcer; her birinin
    # AYIRT EDICI mutanti vardir (bkz. tools/ic-rapor-adi-mutasyon.py).
    with tempfile.TemporaryDirectory() as kok_d:
        depo_a = os.path.join(kok_d, "depo-a")   # "betigin agaci"
        depo_b = os.path.join(kok_d, "depo-b")   # "cwd'nin agaci" (BASKA agac)
        for yol in (depo_a, depo_b):
            os.makedirs(os.path.join(yol, "tools"))
            sentetik_git(yol, "init", "-q", capture_output=True,
                          kimlik_ad="t", kimlik_eposta="t@t.local")
        a_tools = os.path.join(depo_a, "tools")

        # IDDIA-3 (--kok USTUNDUR): acikca verilen agac kazanir; cwd de betik dizini
        # de sonucu DEGISTIREMEZ.
        k3, h3 = kok_coz(depo_b, cwd=depo_a, betik_dizini=a_tools)
        iddia3 = h3 is None and k3 is not None and \
            os.path.realpath(k3) == os.path.realpath(depo_b)
        sonuclar.append(("IDDIA-3 acik-kok-ustundur", iddia3,
                          "--kok verilince O agac olculur (cwd=%r -> k=%r, hata=%r)"
                          % (depo_a, k3, h3)))

        # IDDIA-4 (BELIRSIZLIK FAIL-CLOSED): bayrak YOK ve cwd BASKA bir agacta ->
        # hukum VERILMEZ. Sessizce cwd'ye (ya da betige) dusmek, olculen kusurun ta
        # KENDISIDIR: yanlis agacta bir hukum uretilir ve dogru agaca atfedilir.
        k4, h4 = kok_coz(None, cwd=depo_b, betik_dizini=a_tools)
        iddia4 = h4 is not None and k4 is None
        sonuclar.append(("IDDIA-4 belirsizlik-fail-closed", iddia4,
                          "bayraksiz + cwd BASKA agac -> OLCULEMEDI olmali (k=%r)" % (k4,)))

        # IDDIA-5 (E2E: OLCULEN AGAC = BETIGIN AGACI, CWD DEGIL): kapinin bir kopyasi
        # depo-a'ya konur; IHLAL depo-a'dadir, depo-b TEMIZDIR. Kosum cwd=depo-a ile
        # yapilir (belirsizlik yok) ve rc=1 beklenir; kok CWD'den turetilseydi de ayni
        # sonucu verirdi -> AYIRT EDICI kosum ikincisidir: cwd GIT AGACI OLMAYAN bir
        # dizin iken kapi HALA depo-a'yi olcmeli (cwd tabanli kod burada COKER/yesil verir).
        kopya = os.path.join(a_tools, "ic-rapor-adi-kapisi.py")
        with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
            _kaynak = f.read()
        with open(kopya, "w", encoding="utf-8") as f:
            f.write(_kaynak)
        # Kopya TEK KAYNAK modulunu import eder -> modul de yaninda olmali (fallback YOK).
        shutil.copyfile(os.path.join(BETIK_DIZINI, "git_ortami.py"),
                        os.path.join(a_tools, "git_ortami.py"))
        with open(os.path.join(depo_a, "ihlal.md"), "w", encoding="utf-8") as f:
            # 🔴 FIKSTUR BILEREK KUCUK HARF: IDDIA-5 KOK eksenini olcer, harf-duyarsizligi
            # DEGIL. Buyuk harfle yazilsaydi harf-duyarsizlik mutanti (IDDIA-2'nin
            # oldurucusu) bu iddiayi da dusururdu ve "TEK KIRMIZI" sarti bozulurdu.
            f.write("bkz. rapor" + "-mimara.md (fikstur ihlali)\n")
        sentetik_git(depo_a, "add", "-A", capture_output=True)
        gitsiz = os.path.join(kok_d, "gitsiz")   # HICBIR git agacinda olmayan cwd
        os.makedirs(gitsiz)
        p5 = subprocess.run([sys.executable, kopya], cwd=gitsiz,
                            capture_output=True, text=True)
        iddia5 = p5.returncode == RC_IHLAL and "ihlal.md" in p5.stdout
        sonuclar.append(("IDDIA-5 e2e-olculen-agac-betigin-agaci", iddia5,
                          "gitsiz cwd'den kosulunca BETIGIN agacindaki ihlal bulunmali "
                          "(rc=%d)" % p5.returncode))

        # KONTROL-D: ACIKCA verilen TEMIZ agac yesil kalir (yanlis-pozitif nobeti) —
        # "her sey kirmizi" mutantini yakalar, IDDIA kumesinin PARCASI DEGILDIR.
        sentetik_git(depo_b, "add", "-A", capture_output=True)
        p6 = subprocess.run([sys.executable, kopya, "--kok", depo_b], cwd=gitsiz,
                            capture_output=True, text=True)
        kontrol_d = p6.returncode == RC_TEMIZ
        sonuclar.append(("KONTROL-D acik-temiz-agac-yesil", kontrol_d,
                          "--kok ile verilen TEMIZ agac rc=0 vermeli (rc=%d)" % p6.returncode))

    # --- IDDIA-6 (WORKTREE + KANCA BAGLAMI, DAVRANISSAL): kokun ORTAMDAN BAGIMSIZLIGI.
    # Sentetik depo + GERCEK `git worktree add` + GERCEK `git commit` ile tetiklenen
    # GERCEK pre-commit kancasi kurulur (ortam ELLE set edilip kanca TAKLIT EDILMEZ).
    # Kapinin bu KOPYASI iki baglamda kosar ve BASTIGI KOK olculur:
    #   (a) kancasiz, cwd = worktree koku      (b) kanca icinden (GIT_DIR MUTLAK miras)
    # 🔴 IDDIA BASILAN KOKE baglidir, ihlal SAYISINA degil: boylece desen/muafiyet
    # eksenlerinin mutantlarindan BAGIMSIZ duser ve "TEK KIRMIZI" sozlesmesi korunur.
    # Onarim ONCESI olculen davranis: (a) DOGRU kok, (b) rc=2 OLCULEMEDI + kok BASILMAZ
    # (betik agaci `<worktree>/tools` sanilir).
    try:
        s6 = worktree_kanca_kok_olcumu(os.path.abspath(__file__), "ic-rapor-adi-kapisi.py")
        iddia6 = s6["kanca_kosti"] and s6["kancasiz"][2] and s6["kanca"][2]
        detay6 = "wt=%s kancasiz=%r kanca=%r" % (s6["wt"], s6["kancasiz"], s6["kanca"])
    except Exception as e:                                   # pragma: no cover
        iddia6, detay6 = False, "sonda kurulamadi: %r" % (e,)
    sonuclar.append(("IDDIA-6 worktree-kanca-kok-ortamdan-bagimsiz", iddia6, detay6))

    # ----------------------------------------------------------------- UZAK DAL EKSENI
    # AG YOK: `ls-remote`/`ls-tree` kosuculari ENJEKTE edilir (kanned) + BIR ayak GERCEK
    # git ile capalanir (kanned bicim gercek git ciktisindan kayarsa yakalanir).
    kanon_predikat, kanon_hata = kanonik_aile(kanon_dizin)

    # KONTROL-G: kanonik aile kaynagi GERCEKTEN yuklenebiliyor mu (aksi halde asagidaki
    # uzak iddialar "hep OLCULEMEDI" olur ve hicbir sey ayirt etmez).
    sonuclar.append(("KONTROL-G kanonik-aile-yuklenir", kanon_hata is None,
                      "kanon_dizin=%s hata=%s" % (kanon_dizin, kanon_hata)))
    _p = kanon_predikat if kanon_predikat else (lambda _y: False)

    _sha_a = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
    _sha_b = "b1c2d3e4f5061728394a5b6c7d8e9f0123456789"
    _ham_dal = ("%s\trefs/heads/worktree-agent-ornek\n%s\trefs/heads/main\n"
                % (_sha_a, _sha_b))

    def _sahte_ls_remote(_kok, _uzak):
        return 0, _ham_dal, ""

    def _agac(*yollar):
        return "\0".join(yollar) + "\0"

    # IDDIA-7 (UZAK ISABET YAKALANIR): uzak bir dalin agacindaki ic rapor dosyasi
    # bulunmali. Calisma agaci kolu bu senaryoda SESSIZDIR (dosya yerelde YOK).
    _kirli = _agac("index.html", "tools/build.py", "CURUTME" + "-RAPORU.md")
    _temiz = _agac("index.html", "tools/build.py", "README.md")

    def _sahte_ls_tree_kirli(_kok, sha):
        return (0, _kirli if sha == _sha_a else _temiz, "")

    i7, d7, h7 = uzak_tarama("/yok", "origin", predikat=_p,
                             ls_remote=_sahte_ls_remote, ls_tree=_sahte_ls_tree_kirli)
    iddia7 = (h7 is None and d7 == 2 and i7 is not None and len(i7) == 1
              and i7[0][0] == "worktree-agent-ornek")
    sonuclar.append(("IDDIA-7 uzak-dal-isabeti-yakalanir", iddia7,
                      "uzak dal agacindaki ic rapor bulunmali (dal=%d isabet=%r hata=%r)"
                      % (d7, i7, h7)))

    # IDDIA-8 (TANINMAYAN EVREN FAIL-CLOSED): `ls-remote` ciktisi cozulemiyorsa hukum
    # VERILMEZ. Satiri ATLAMAK evreni sessizce kucultur -> "0 isabet" yanlis atfedilir.
    def _bozuk_ls_remote(_kok, _uzak):
        return 0, "BU BIR REF SATIRI DEGIL\n%s\trefs/heads/main\n" % _sha_b, ""

    i8, _d8, h8 = uzak_tarama("/yok", "origin", predikat=_p,
                              ls_remote=_bozuk_ls_remote, ls_tree=_sahte_ls_tree_kirli)
    iddia8 = h8 is not None and i8 is None
    sonuclar.append(("IDDIA-8 taninmayan-evren-fail-closed", iddia8,
                      "cozulemeyen ls-remote satiri OLCULEMEDI olmali (isabet=%r)" % (i8,)))

    # KONTROL-E (YANLIS-POZITIF NOBETI): AILEYE BENZEYEN ama KAPSAM DISI adlar
    # (raporlama/onarimlar/... ve mesru belgeler) uzak dalda YANMAMALI. Bu kol
    # bloklayici bir alarm uretir; genis yanlis-pozitif TUM dallari supheli yapar.
    _fp = _agac("index.html", "RAPORLAMA-NOTU.md", "raporlama.md", "onarimlar.md",
                "README.md", "tools/paket-shop-odeme.md", "urunler.json")

    def _sahte_ls_tree_fp(_kok, _sha):
        return 0, _fp, ""

    iE, _dE, hE = uzak_tarama("/yok", "origin", predikat=_p,
                              ls_remote=_sahte_ls_remote, ls_tree=_sahte_ls_tree_fp)
    kontrol_e = hE is None and iE == []
    sonuclar.append(("KONTROL-E uzak-yanlis-pozitif-yesil", kontrol_e,
                      "kapsam disi benzer adlar YANMAMALI (isabet=%r hata=%r)" % (iE, hE)))

    # IDDIA-9 (GERCEK GIT + OZYINELI AGAC): kanned kosucu bicim kaymasini goremez ve
    # OZYINESIZ bir `ls-tree` ALT DIZINDEKI raporu kacirir. Bu ayak GERCEK depo kurar.
    # 🔴 IDDIA predikattan BAGIMSIZ: ham yol listesi olculur -> IDDIA-7'nin oldurucusu
    # bunu DUSURMEZ (ayirt edici mutant sarti).
    with tempfile.TemporaryDirectory(prefix="pruvo-uzak-") as ud:
        sentetik_git(ud, "init", "-q", capture_output=True, text=True,
                      kimlik_ad="t", kimlik_eposta="t@t.local")
        os.makedirs(os.path.join(ud, "alt", "dizin"))
        with open(os.path.join(ud, "alt", "dizin", "CURUTME" + "-RAPORU.md"),
                  "w", encoding="utf-8") as f:
            f.write("ic rapor govdesi (fikstur)\n")
        with open(os.path.join(ud, "index.html"), "w", encoding="utf-8") as f:
            f.write("<p>taban</p>\n")
        sentetik_git(ud, "add", "-A", capture_output=True, text=True,
                      kimlik_ad="t", kimlik_eposta="t@t.local")
        sentetik_git(ud, "commit", "-q", "-m", "fikstur", capture_output=True, text=True,
                      kimlik_ad="t", kimlik_eposta="t@t.local")
        _r = sentetik_git(ud, "rev-parse", "HEAD", capture_output=True, text=True,
                           kimlik_ad="t", kimlik_eposta="t@t.local")
        _hedef = (_r.stdout or "").strip()
        _yollar, _yh = uzak_agac_yollari(ud, _hedef)
        iddia9 = (_yh is None and _yollar is not None
                  and "alt/dizin/CURUTME" + "-RAPORU.md" in _yollar)
        sonuclar.append(("IDDIA-9 gercek-git-ozyineli-agac", iddia9,
                          "alt dizindeki dosya ham agac listesinde olmali (hata=%r, "
                          "yollar=%r)" % (_yh, _yollar)))

        # KONTROL-H (GERCEK `ls-remote` BICIM CAPASI): ayristirici kanned metne DEGIL
        # gercek git ciktisina capalanir. Yerel depo bir "uzak" olarak kullanilir (ag YOK).
        _rc, _ham, _hata = _git_ls_remote(ud, ud)
        _gercek_dallar, _gh = uzak_dallari_ayristir(_ham)
        kontrol_h = (_rc == 0 and _gh is None and _gercek_dallar
                     and all(s == _hedef for s, _a in _gercek_dallar))
        sonuclar.append(("KONTROL-H gercek-ls-remote-bicimi", bool(kontrol_h),
                          "gercek ls-remote ciktisi cozulmeli (rc=%s dallar=%r hata=%r)"
                          % (_rc, _gercek_dallar, _gh or _hata)))

    # IDDIA-10 (KANONIK AILE FAIL-CLOSED / IKIZ TANIM YASAGI): aile kaynagi YOKSA
    # yerel bir yedek desene DUSULMEZ, hukum VERILMEZ. Dususun kendisi ikizdir.
    with tempfile.TemporaryDirectory(prefix="pruvo-kanonsuz-") as kd:
        _p10, _h10 = kanonik_aile(kd)
        iddia10 = _p10 is None and _h10 is not None
        sonuclar.append(("IDDIA-10 kanonik-aile-fail-closed", iddia10,
                          "kanonik kaynak yokken yedek desene DUSULMEMELI (p=%r)" % (_p10,)))

    # ------------------------------------------------- EKSIK NESNE YARISI EKSENI
    # 11 Agu 2026 OLCULEN kusur (kosum 31433971660 / serit-b): checkout'tan SONRA
    # ilerleyen dalin nesnesi yerelde YOK -> `ls-tree` duser -> rc=2, GERCEK ihlal YOK.
    # AG YOK: hem `ls_tree` hem `fetch` kosuculari ENJEKTE edilir; fetch SAYACI
    # "kosum basina 1" sozlesmesini OLCER.
    def _sayacli_fetch(rc=0, hata=""):
        kayit = {"n": 0}

        def _kosucu(_kok, _uzak):
            kayit["n"] += 1
            return rc, "", hata
        return kayit, _kosucu

    def _yarisan_ls_tree(gecince=None):
        """Her sha icin ILK cagriyi "not a tree object" ile dusurur (yarisin ta
        kendisi). `gecince` verilirse SONRAKI cagrilar rc=0 + o agaci doner
        (tazelenmis klon); verilmezse HER cagri duser."""
        gorulen = set()

        def _kosucu(_kok, sha):
            if sha in gorulen and gecince is not None:
                return 0, gecince, ""
            gorulen.add(sha)
            return 128, "", "fatal: not a tree object"
        return _kosucu

    def _tek_dal_ls_remote(_kok, _uzak):
        return 0, "%s\trefs/heads/main\n" % _sha_b, ""

    # IDDIA-11 (YARIS ONARILDI): ilk `ls-tree` duser, fetch rc=0, ikinci `ls-tree`
    # gecer -> HUKUM VERILIR (OLCULEMEDI DEGIL) ve fetch TAM 1 kez kosar.
    _kayit11, _fetch11 = _sayacli_fetch(rc=0)
    i11, _d11, h11 = uzak_tarama("/yok", "origin", predikat=_p,
                                 ls_remote=_tek_dal_ls_remote,
                                 ls_tree=_yarisan_ls_tree(_temiz), fetch=_fetch11)
    iddia11 = h11 is None and i11 is not None and _kayit11["n"] == 1
    sonuclar.append(("IDDIA-11 eksik-nesne-yarisi-onarildi", iddia11,
                      "fetch+tekrar sonrasi hukum VERILMELI (fetch=%d isabet=%r hata=%r)"
                      % (_kayit11["n"], i11, h11)))

    # IDDIA-12 (FAIL-CLOSED KORUNDU): tazelemeden SONRA da okunamayan agac
    # OLCULEMEDI'dir; sessizce "temiz"e DONULMEZ.
    _kayit12, _fetch12 = _sayacli_fetch(rc=0)
    i12, _d12, h12 = uzak_tarama("/yok", "origin", predikat=_p,
                                 ls_remote=_tek_dal_ls_remote,
                                 ls_tree=_yarisan_ls_tree(), fetch=_fetch12)
    iddia12 = i12 is None and h12 is not None and "UZAK DAL AGACI OKUNAMADI" in h12
    sonuclar.append(("IDDIA-12 tazeleme-sonrasi-fail-closed", iddia12,
                      "iki deneme de duserse OLCULEMEDI kalmali (isabet=%r hata=%r)"
                      % (i12, (h12 or "")[:90])))

    # KONTROL-I (FETCH BASARISIZLIGI YUTULMAZ): fetch duserse hukum yine OLCULEMEDI
    # ve fetch'in rc'si hata metninde GORUNUR (sessiz yesile DONMEZ).
    _kayit_i, _fetch_i = _sayacli_fetch(rc=5, hata="fatal: could not read from remote")
    iI, _dI, hI = uzak_tarama("/yok", "origin", predikat=_p,
                              ls_remote=_tek_dal_ls_remote,
                              ls_tree=_yarisan_ls_tree(), fetch=_fetch_i)
    kontrol_i = iI is None and hI is not None and "rc=5" in hI
    sonuclar.append(("KONTROL-I fetch-basarisiz-yine-olculemedi", kontrol_i,
                      "fetch rc'si hata metnine yazilmali (isabet=%r hata=%r)"
                      % (iI, (hI or "")[:90])))

    # IDDIA-13 (AGA CIKMA YOK): (a) kanned kosucu rc=0 verirken fetch HIC cagrilmaz;
    # (b) kanned kosucu DUSSE bile fetch kosucusu ENJEKTE EDILMEMISSE gercek fetch
    # denenmez -> kendini-test/mutasyon kollari AGA CIKMAZ.
    _kayit13, _fetch13 = _sayacli_fetch(rc=0)
    _i13, _d13, h13 = uzak_tarama("/yok", "origin", predikat=_p,
                                  ls_remote=_sahte_ls_remote,
                                  ls_tree=_sahte_ls_tree_kirli, fetch=_fetch13)
    _durum13 = yeni_fetch_durumu()
    _y13, _h13b = uzak_agac_yollari("/yok", _sha_a, ls_tree=_yarisan_ls_tree(),
                                    fetch_durumu=_durum13)
    iddia13 = (h13 is None and _kayit13["n"] == 0
               and _h13b is not None and _durum13["sayac"] == 0)
    sonuclar.append(("IDDIA-13 enjekte-kosucu-aga-cikmaz", iddia13,
                      "kanned kolda fetch sayaci 0 olmali (rc0-kol=%d, dusen-kol=%d)"
                      % (_kayit13["n"], _durum13["sayac"])))

    # IDDIA-14 (KOSUM BASINA TEK FETCH): 3 dalin HEPSI ilk denemede duse bile fetch
    # sayaci 1'i GECMEZ (52 dal icin 52 fetch YASAK); kalan dallar tazelenmis
    # klondan okunur.
    _uc_dal = ("%s\trefs/heads/a\n%s\trefs/heads/b\n%s\trefs/heads/c\n"
               % (_sha_a, _sha_b, "c1d2e3f405162738495a6b7c8d9e0f1234567890"))

    def _uc_dal_ls_remote(_kok, _uzak):
        return 0, _uc_dal, ""

    _kayit14, _fetch14 = _sayacli_fetch(rc=0)
    _i14, d14, h14 = uzak_tarama("/yok", "origin", predikat=_p,
                                 ls_remote=_uc_dal_ls_remote,
                                 ls_tree=_yarisan_ls_tree(_temiz), fetch=_fetch14)
    iddia14 = _kayit14["n"] == 1
    sonuclar.append(("IDDIA-14 fetch-kosum-basina-tek", iddia14,
                      "3 dal / 1 fetch olmali (fetch=%d dal=%d hata=%r)"
                      % (_kayit14["n"], d14, h14)))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


# ===========================================================================
# MUTASYON BATARYASI (`--mutasyon`) — [[mutasyon-kaniti-yeniden-uretilebilir]]:
# "batarya kostu" ANLATISI kanit DEGILDIR; surucu REPODA durur ve yeniden kosar.
# Kabul cikis kodu degil OLCULEN SAYIDIR: her mutant TEK bir IDDIA'yi dusurmeli,
# capa kaynakta TAM BIR KEZ eslesmelidir, KONTROL mutanti YESIL kalmalidir
# (yoksa batarya "hep kirmizi"dir ve hicbir sey ayirt etmez).
# 🔴 CANLI DOSYAYA YAZILMAZ: mutant GECICI dizindeki KOPYAYA uygulanir; kaynagin
# sha256'si once/sonra olculur ("yazmadim" iddiasi da OLCULUR).
# ===========================================================================
# (ad, eski_metin, yeni_metin, dusmesi_beklenen_TEK_iddia | None = KONTROL)
MUTANTLAR = (
    # --- KOK EKSENI: onarimi GERI ALAN mutantlar ---
    ("MUT-KOK-ARG-KOR", "    if arg_kok:\n        k = _git_kok(arg_kok)",
     "    if False:\n        k = _git_kok(arg_kok)", "IDDIA-3"),
    ("MUT-KOK-CWD-DUS",
     "    if cwd_kok and os.path.realpath(cwd_kok) != os.path.realpath(betik_kok):",
     "    if False:", "IDDIA-4"),
    # Onarimin TA KENDISINI geri alir: kok yine CWD'den turer.
    ("MUT-KOK-CWD-GERI", '    kok, hata = kok_coz(args.kok, os.getcwd())',
     '    kok, hata = _git_kok(os.getcwd()) or None, None', "IDDIA-5"),
    # 6 Agu 2026 onarimini geri alir: git cagrisi MIRAS ALINAN git baglamiyla kosar.
    # Kancasiz vaka (temiz ortam) etkilenmez -> yalniz KANCA ayagi duser: TEK KIRMIZI.
    ("MUT-KOK-ORTAM", "    return git_kok(dizin, git_ortami())",
     "    return git_kok(dizin, os.environ.copy())", "IDDIA-6"),
    # --- DESEN/MUAFIYET ekseni (onarim ONCESI de var olan iddialar) ---
    ("MUT-MUAF-YOL", "    return (dosya, _satir_hash(satir_metni)) in muafiyet_kumesi",
     "    return any(d == dosya for d, _h in muafiyet_kumesi)", "IDDIA-1"),
    # Harf-duyarsizligi oldurur: IDDIA-2'nin KARISIK harfli fiksturu kacar. IDDIA-5'in
    # fiksturu KUCUK harflidir -> ondan BAGIMSIZ duser (ayirt edici mutant).
    ("MUT-DESEN-HARF", "        if DESEN in satir.lower():",
     "        if DESEN in satir:", "IDDIA-2"),
    # --- UZAK DAL EKSENI: 10 Agu 2026 onarimini geri alan mutantlar ---
    # Isabet suzgecini oldurur: uzak dal agaci taranir ama HICBIR SEY isaretlenmez
    # (kolun "hep yesil" hali). IDDIA-9 ham yol listesini olcer -> ondan BAGIMSIZ duser.
    ("MUT-UZAK-SUZGEC", "            if predikat(yol):",
     "            if False:", "IDDIA-7"),
    # Fail-closed'i fail-OPEN yapar: cozulemeyen ls-remote satiri sessizce ATLANIR,
    # evren kucultur ve "0 isabet" hukmu yanlis atfedilir.
    ("MUT-UZAK-FAIL-OPEN", "    if hatali:\n        return None, (\"TANINMAYAN",
     "    if False:\n        return None, (\"TANINMAYAN", "IDDIA-8"),
    # Ozyinelemeyi oldurur: ALT DIZINDEKI rapor evrene GIRMEZ. Kanned kosuculu
    # iddialar (7/8) bu bayragi hic kullanmaz -> yalniz GERCEK git ayagi duser.
    ("MUT-UZAK-LSTREE-DUZ",
     '["git", "-C", kok, "ls-tree", "-r", "--name-only", "-z", sha]',
     '["git", "-C", kok, "ls-tree", "--name-only", "-z", sha]', "IDDIA-9"),
    # 🔴 IKIZ TANIM MUTANTI: kanonik aile kaynagi yokken YEREL bir yedek desene duser.
    # Bu, [[ikiz-tanim-sessiz-ayrisma]] dersinin ta kendisidir; kapi bunu gormeli.
    ("MUT-KANON-IKIZ",
     '        return None, ("KANONIK AILE KAYNAGI YOK: %s',
     '        return (lambda y: y.rsplit("/", 1)[-1].lower().startswith("rapor")), ("%s',
     "IDDIA-10"),
    # --- EKSIK NESNE YARISI EKSENI: 11 Agu 2026 onarimini geri alan mutantlar ---
    # Tekrari oldurur: fetch kosar ama `ls-tree` BIR DAHA denenmez -> yaris yine rc=2.
    # 12/KONTROL-I zaten OLCULEMEDI bekler, 14 yalniz SAYACA bakar -> TEK KIRMIZI.
    ("MUT-UZAK-YARIS-YOK", '        if durum["rc"] == 0:', "        if False:",
     "IDDIA-11"),
    # Fail-closed'i fail-OPEN yapar: tazelemeden sonraki okuma SAHTE bir temiz agac
    # dondurur. IDDIA-11 (tekrar zaten geciyordu) ve 13/14 (fetch muhasebesi) BUNDAN
    # ETKILENMEZ -> yalniz "tazelemeye ragmen okunamadi" iddiasi duser.
    ("MUT-UZAK-TAZELEME-SAHTE", "            rc, cikti, hata = kosucu(kok, sha)",
     '            rc, cikti, hata = 0, "index.html\\0", ""', "IDDIA-12"),
    # AGA CIKMA KAPISINI oldurur: kanned kosucu dustugunde de GERCEK fetch denenir
    # (kendini-test/mutasyon kollari aga cikar). Fetch ENJEKTE edilen iddialar bu
    # kapiyi zaten aciyor -> yalniz "aga cikma yok" iddiasi duser.
    ("MUT-UZAK-FETCH-KAPI",
     "    if rc != 0 and (fetch is not None or ls_tree is None):", "    if rc != 0:",
     "IDDIA-13"),
    # Tek-fetch tavanini oldurur: her dusen dal icin YENIDEN fetch (52 dal -> 52 fetch).
    # Tek dalli iddialar (11/12/KONTROL-I) sayiyi degistirmez -> yalniz tavan iddiasi duser.
    ("MUT-UZAK-FETCH-HER-DAL", '        if durum["sayac"] == 0:', "        if True:",
     "IDDIA-14"),
    # --- KONTROL: davranisi DEGISTIRMEYEN degisiklik -> batarya YESIL kalmali.
    #     Bu mutant kirmizi yakarsa batarya ayirt edici degil, sadece hassastir.
    ("KONTROL-METIN", 'print("COZUM: yorum/docstring METNINDEN dosya adini kaldir, anlamini koruyarak")',
     'print("COZUM: yorum/docstring metninden dosya adini kaldir; anlami koru.")', None),
    # UZAK kolunun KENDI no-op kontrolu: yeni eksen "hep kirmizi" degil, AYIRT EDICI mi.
    ("KONTROL-UZAK-METIN", 'print("UZAK DAL KAPISI: temiz (0 ic rapor dosyasi).")',
     'print("UZAK DAL KAPISI: temiz — 0 ic rapor dosyasi.")', None),
)


_TABLO_BAS = "MUTANTLAR = ("
_TABLO_SON = "def _mutasyon_bataryasi():"


def _tablo_disi(govde):
    """Kaynagi (tablo_oncesi, tablo, tablo_sonrasi) diye ayirir.

    🔴 NEDEN: MUTANTLAR tablosu capa metinlerini KENDISI tasir. Capalar ham kaynakta
    sayilirsa her biri EN AZ 2 kez eslesir ve "capa TAM BIR KEZ" sarti hicbir zaman
    saglanamaz; tabloyu sayimdan/degistirmeden HARIC tutmak sarttir (aksi halde
    mutant tablonun KENDISINI bozar, olculen kodu DEGIL)."""
    bas = govde.index(_TABLO_BAS)
    son = govde.index(_TABLO_SON, bas)
    return govde[:bas], govde[bas:son], govde[son:]


def _sha256_dosya(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _mutasyon_bataryasi():
    kaynak_yolu = os.path.abspath(__file__)
    modul_yolu = os.path.join(BETIK_DIZINI, "git_ortami.py")
    with open(kaynak_yolu, "r", encoding="utf-8") as f:
        govde = f.read()
    once_hash = hashlib.sha256(govde.encode("utf-8")).hexdigest()
    modul_once = _sha256_dosya(modul_yolu)
    _on, _tablo, _arka = _tablo_disi(govde)

    def kos(yol):
        # 🔴 `--kanon-dizin`: mutant KOPYA gecici dizinde yasar; ic rapor AILE tanimini
        # tasiyan kanonik kaynak (tools/kisisel-veri-test.py) oraya KOPYALANMAZ —
        # kopyalanirsa kendi bagimliliklariyla birlikte IKINCI bir kaynak dogar.
        # Mutasyon YALNIZ kapiya uygulanir; aile tanimi HER kosumda AYNI tek kaynaktan
        # gelir (bu yolun kendisi de MUT-KANON-IKIZ ile nobetlidir).
        r = subprocess.run([sys.executable, yol, "--kendini-test",
                            "--kanon-dizin", BETIK_DIZINI],
                            capture_output=True, text=True)
        cikti = r.stdout + r.stderr
        dusen = set(re.findall(r"^\s*\[FAIL\]\s+(\S+?)\s", cikti, re.M))
        etiket = re.findall(r"^\s*\[(?:PASS|FAIL)\]\s+(\S+?)\s", cikti, re.M)
        return dusen, len(etiket), ("Traceback" in cikti)

    def iddialar(kume):
        """TEK-KIRMIZI hukmu YALNIZ beyan edilmis IDDIA-* etiketleri uzerinden verilir.
        KONTROL-* saglamlik nobetleridir ve bir mutantin YAN ETKISI olarak birlikte
        dusebilir (dosya basligindaki KONTROL-C notuyla ayni sozlesme)."""
        return {e for e in kume if e.startswith("IDDIA-")}

    hatalar = []
    with tempfile.TemporaryDirectory() as d:
        # Kopyalar TEK KAYNAK modulunu import eder; mutasyon YALNIZ kapi kopyasina
        # uygulanir, modul kopyasi DEGISTIRILMEZ (capa kapinin KENDI cagri yerindedir).
        shutil.copyfile(os.path.join(BETIK_DIZINI, "git_ortami.py"),
                        os.path.join(d, "git_ortami.py"))
        taban_yolu = os.path.join(d, "taban.py")
        with open(taban_yolu, "w", encoding="utf-8") as f:
            f.write(govde)
        t_dusen, t_sayi, t_cokme = kos(taban_yolu)
        print("TABAN: %d iddia, %d dusen, cokme=%s" % (t_sayi, len(t_dusen), t_cokme))
        if t_dusen or t_cokme:
            hatalar.append("TABAN temiz DEGIL: dusen=%s cokme=%s" % (sorted(t_dusen), t_cokme))

        beyan = [m[3] for m in MUTANTLAR if m[3]]
        if len(set(beyan)) != len(beyan):
            hatalar.append("IKI mutant AYNI iddiaya isaret ediyor: %s" % beyan)

        for ad, eski, yeni, bekle in MUTANTLAR:
            # 🔴 CAPA TAM BIR KEZ: 0 -> bayat tablo (sessiz yesil), >1 -> mutant
            # birden fazla yeri bozar, "TEK KIRMIZI" hukmu anlamini yitirir.
            n = _on.count(eski) + _arka.count(eski)
            if n != 1:
                hatalar.append("%s: capa %d kez eslesti (TAM 1 olmali)" % (ad, n))
                print("  [CAPA-HATASI] %-18s eslesme=%d" % (ad, n))
                continue
            m_yolu = os.path.join(d, "mutant.py")
            with open(m_yolu, "w", encoding="utf-8") as f:
                f.write(_on.replace(eski, yeni, 1) + _tablo + _arka.replace(eski, yeni, 1))
            dusen, sayi, cokme = kos(m_yolu)
            dusen = iddialar(dusen) if bekle else dusen
            if cokme:
                hatalar.append("%s COKTU (cokme kirmiziyla karisir)" % ad)
            if sayi != t_sayi:
                hatalar.append("%s: iddia sayisi %d, taban %d" % (ad, sayi, t_sayi))
            if bekle is None:
                ok = not dusen
                if not ok:
                    hatalar.append("KONTROL mutanti %s KIRMIZI yakti (dusen=%s) — batarya "
                                   "ayirt edici degil" % (ad, sorted(dusen)))
                print("  [%s] %-18s dusen=%s (KONTROL: YESIL kalmali)"
                      % ("YESIL" if ok else "SAPMA", ad, sorted(dusen)))
            else:
                ok = dusen == {bekle}
                if not ok:
                    hatalar.append("%s: dusen=%s, beyan={%s}" % (ad, sorted(dusen), bekle))
                print("  [%s] %-18s dusen=%s sayi=%d cokme=%s"
                      % ("OLDU" if ok else "SAPMA", ad, sorted(dusen), sayi, cokme))

    with open(kaynak_yolu, "r", encoding="utf-8") as f:
        sonra_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
    modul_sonra = _sha256_dosya(modul_yolu)
    print("CANLI DOSYA sha256 once==sonra: %s" % (once_hash == sonra_hash))
    print("PAYLASILAN MODUL (git_ortami.py) sha256 once==sonra: %s"
          % (modul_once == modul_sonra))
    if once_hash != sonra_hash:
        hatalar.append("CANLI DOSYA DEGISTI — mutasyon kopyaya uygulanmali")
    if modul_once != modul_sonra:
        hatalar.append("PAYLASILAN MODUL DEGISTI — mutasyon yalniz KOPYAYA uygulanmali")
    print()
    if hatalar:
        print("MUTASYON BATARYASI KIRMIZI:")
        for h in hatalar:
            print("  - " + h)
        return 1
    oldurucu = len([m for m in MUTANTLAR if m[3]])
    print("MUTASYON BATARYASI YESIL: %d oldurucu mutant TEK KIRMIZI + beyana esit, "
          "%d KONTROL mutanti YESIL; iddia sayisi %d sabit; Traceback 0."
          % (oldurucu, len(MUTANTLAR) - oldurucu, t_sayi))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true",
                     help="offline kabul testi (izole gecici git deposu, ag YOK)")
    ap.add_argument("--kok", metavar="YOL", default=None,
                     help="OLCULECEK agac (varsayilan: BETIGIN kendi agaci; CWD ASLA)")
    ap.add_argument("--mutasyon", action="store_true",
                     help="kabul bataryasinin mutasyon kanitini kostur (kopyaya uygular)")
    ap.add_argument("--uzak", action="store_true",
                     help="UZAK DAL AGACLARINI tara (ag ister; SIG klonda rc=2)")
    ap.add_argument("--uzak-adi", metavar="AD", default="origin",
                     help="taranacak uzagin adi/URL'si (varsayilan: origin)")
    ap.add_argument("--kanon-dizin", metavar="YOL", default=None,
                     help="ic rapor AILE tanimini tasiyan kanonik kaynagin dizini "
                          "(varsayilan: BETIGIN dizini). Aile burada YENIDEN YAZILMAZ.")
    args = ap.parse_args()

    kanon_dizin = args.kanon_dizin or BETIK_DIZINI
    if args.kendini_test:
        return _kendini_test(kanon_dizin)
    if args.mutasyon:
        return _mutasyon_bataryasi()

    kok, hata = kok_coz(args.kok, os.getcwd())
    if hata:
        print("IC RAPOR ADI KAPISI: OLCULEMEDI (fail-closed KIRMIZI)", file=sys.stderr)
        print(hata, file=sys.stderr)
        return RC_OLCULEMEDI
    if args.uzak:
        return _uzak_kolu(kok, args.uzak_adi, kanon_dizin)
    ihlaller, dosya_sayisi = ana_tarama(kok)
    # 🔴 OLCULEN AGAC HER ZAMAN BASILIR (yesilde de): bir "temiz" ciktisi artik
    # sessizce BASKA bir agaca atfedilemez.
    print("IC RAPOR ADI KAPISI: olculen agac = %s (%d izlenen dosya tarandi)"
          % (kok, dosya_sayisi))
    if not ihlaller:
        print("IC RAPOR ADI KAPISI: temiz (0 muafiyet-disi isabet).")
        return RC_TEMIZ
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
