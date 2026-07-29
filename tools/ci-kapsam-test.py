#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI KAPSAM KAPISI — her kabul testi ya CI'da kosuluyor ya da GEREKCELI olarak muaf.

NEDEN VAR (denetim, 20 Tem): .github/workflows/deploy.yml uzun sure YALNIZ 2 test kosuyordu
(kisisel-veri + kategori-parite). Repodaki onlarca kabul testi hicbir push'ta kosmadigi icin
"olu nobetci" bir test CI'dan YESIL/success alarak gecebiliyordu (B paketi olu sepet nobetcisi
son 4 kosumda success aldi). Bu kapi FAIL-CLOSED bir kapsam bekcisidir: repoda IZLENEN
(git ls-files) her kabul-testi dosyasi ya deploy.yml'de FIILEN kosulur, ya da asagidaki
IZIN_LISTESI'nde GEREKCE ile muaf tutulur. Ucuncu bir hal yoktur -> yeni bir test sessizce
CI-disi kalamaz.

KESIF (discovery) — git ls-files uzerinden (CI checkout == yerel; os.walk kullanılmaz cunku
gitignore'lu/uretilmis dosyalar yerelde gorunup CI'da gorunmez, sapma yaratirdi):
  * tools/  (arsiv/ HARIC):  <ad>-test.(py|js)  VEYA  test-<ad>.(py|js)  VEYA  <ad>-kapisi.py
    (META-DELIK ONARIMI, 21 Tem: kesif uzun sure yalniz "-test"/"test-" adlarina bakiyordu ->
     ADI "-kapisi.py" olan NOBETCILER — odeme-beyani-kapisi, landing-hukuk-kapisi,
     enjeksiyon-kapisi ... — kesfe HIC girmiyordu. Sonuc: biri deploy.yml'den silinse bu kapi
     UYARMAZ, YESIL kalirdi; olculdu: "run: python3 tools/odeme-beyani-kapisi.py" satiri
     silinmis mutant deploy.yml'de kapi eski desenle exit 0 veriyordu. Artik kapsam kurali
     nobetcilere de uygulanir.)
  * shop/test, onizleme/test, jenerator/test:  o dizinin DOGRUDAN altindaki .py/.js/.mjs/.cjs
    (alt dizinler — jenerator/test/aileler, esleme — fikstur/aile verisi, kosulabilir suite degil)

KABUL (bu dosyanin kendi kabul testleri):
  1. IZLENEN her kabul testi ya kosuluyor ya IZIN_LISTESI'nde -> degilse exit 1 (KAPSAMSIZ).
  2. IZIN_LISTESI'nde GEREKCESIZ (bos) giris -> exit 1.
  3. IZIN_LISTESI'nde olup artik KESFEDILMEYEN (silinmis/yeniden adlandirilmis) giris -> exit 1
     (liste curumesin).
  4. IZIN_LISTESI'nde olup AYNI ZAMANDA deploy.yml'de kosulan giris -> exit 1 (bayat muafiyet;
     kosuluyorsa listeden cikarilmali).
KIRMIZI-MUTASYON: deploy.yml'den bir "python3 tools/<x>-test.py" satiri silinirse o test
kapsamsiz kalir -> kapi KIRMIZI (exit 1). (--deploy <yol> ile alternatif/mutasyonlu bir kopyaya
isaret ederek GERCEK deploy.yml'e dokunmadan kanitlanabilir.)

KENDI NOBETCILERI (kontroller=True iken BLOKLAYICI, yani CI'da fiilen kosar):
  * bulgu1_mutasyon_kontrol() — yalniz-yorum mensiyonu 'kosuluyor' sayilmasin.
  * muaf_sayaci_kontrol()     — rapordaki "Muaf (izin listesi)" sayisi GERCEKTEN izin
    listesini saysin (kapsamsiz dosya o sayiya sizmasin, muafiyet eklenince sayi artsin).
  * kendini_test_adimi_kontrol() — deploy.yml'de YORUM OLMAYAN bir icra govdesinin
    metninde "--kendini-test" ALT-DIZESI geciyor mu (ZINCIRIN SON HALKASI). Duz `in`
    aramasi; bagimsiz eslestirici YOK. IDDIA BILEREK DAR: "metin duruyor" der, "adim
    kosuyor + blokluyor" DEMEZ. Kabul edilen bedel (mensiyon da sayilir) + kapsam disi
    birakilan sessiz-yesil siniflar fonksiyon docstring'inde.

Kullanim:
    python3 tools/ci-kapsam-test.py
    python3 tools/ci-kapsam-test.py --deploy /gecici/mutant-deploy.yml
    python3 tools/ci-kapsam-test.py --kendini-test
"""
import argparse
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DEPLOY_VARSAYILAN = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

# ---- KESIF PREDIKATLARI ----------------------------------------------------
TOOLS_PAT = re.compile(
    r"^tools/([^/]*-test\.(?:py|js)|test-[^/]*\.(?:py|js)|[^/]*-kapisi\.py)$")
DIR_PAT = re.compile(r"^(?:shop/test|onizleme/test|jenerator/test)/[^/]+\.(?:py|js|mjs|cjs)$")


def kesfet():
    """git ls-files uzerinden IZLENEN kabul-testi dosyalarini (repo-rel yol) dondur."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("git ls-files basarisiz: " + r.stderr.strip())
    bulunan = []
    for yol in r.stdout.splitlines():
        if yol.startswith("tools/arsiv/"):
            continue
        if TOOLS_PAT.match(yol) or DIR_PAT.match(yol):
            bulunan.append(yol)
    return sorted(bulunan)


def _icra_govdesi(ham_satir):
    """TEK KAYNAK — bir deploy.yml satirini FIILEN kosan komut govdesine indirger.

    Yorum satiri (strip -> '#'), bos satir ve ADIM ADI ('- name:' / 'name:') ELENIR;
    'run:' oneki soyulur. Icra degilse None. _icra_komutlari(), _icra_satir_indeksleri()
    ve mutant ureticileri HEP bunu kullanir -> repoda iki farkli 'satir icra mi' mantigi
    TUTULMAZ. Kaba ve fail-closed: YAML ayristiricisi taklit ETMEZ (bkz.
    mimar-kapi-parser-taklidi).

    'name:' ELEMESI NEDEN BURADA (28 Tem, curutucu turu): bir step ADI HICBIR ZAMAN icra
    degildir — T7'nin ('mensiyon kosuluyor sayilmasin') ta kendisidir. Eskiden yalniz
    yorumlar eleniyordu; 'run:' satiri silinip komut metni step ADINA tasinirsa
    (`- name: python3 tools/x-test.py`) satir icra govdesi olarak listeye giriyordu.
    Bu, paylasilan capayi (kosulan() dahil) DOGRU yonde sertlestirir; olculdu: kosulan
    sayisi ve bulgu1/muaf nobetcileri DEGISMEDI (rapor TUR 3)."""
    s = ham_satir.strip()
    if not s or s.startswith("#"):
        return None  # bos satir ya da YAML yorumu -> icra degil
    if s.startswith("- name:") or s.startswith("name:"):
        return None  # step ADI -> icra degil (mensiyon, T7 sinifi)
    if s.startswith("run:"):
        s = s[4:].strip()  # inline 'run: <komut>' ya da blok basi 'run: |'
    return s or None


def _icra_komutlari(deploy_metin):
    """deploy.yml'de FIILEN kosan komut govdelerini (satir satir) dondur.
    Bir 'python3 <yol>' mensiyonu YORUM icinde ya da echo-string icinde geciyorsa
    bu listede komutun BASINDA yer almaz -> kosulan() onu 'kosuluyor' saymaz."""
    komutlar = []
    for ham in deploy_metin.splitlines():
        g = _icra_govdesi(ham)
        if g:
            komutlar.append(g)
    return komutlar


# Kesif predikati .py YANINDA .js/.mjs/.cjs dosyalarini da buluyor (DIR_PAT); bunlar
# python3 ile DEGIL node ile kosulur. Yorumlayici DOSYA UZANTISINDAN turetilir — capa yine
# TEK ve dar kalir (serbest komut kabul edilmez).
YORUMLAYICI = {".py": "python3", ".js": "node", ".mjs": "node", ".cjs": "node"}


def _yorumlayici(yol):
    """<yol> hangi yorumlayiciyla kosulur? Bilinmeyen uzanti -> python3 (fail-closed:
    eslesme DARALIR, yani dosya 'kosulmuyor' sayilir ve kapsam kapisi konusur)."""
    return YORUMLAYICI.get(os.path.splitext(yol)[1], "python3")


def _onek_re(yol):
    """TEK KAYNAK — 'bu komut govdesi <yol>'u kosuyor' capasi.

    Komut govdesi '<yorumlayici> <yol>' ile BASLAMALI (yorumlayici uzantidan: .py ->
    python3, .js/.mjs/.cjs -> node); negatif ileri-bakis (?![\\w./-]) uzun bir baska yolun
    on-eki olarak yanlis eslesmeyi engeller (ve '<yol> --bayrak' biciminde BAYRAKLI cagriyi
    DOGRU sekilde ESLESTIRIR — bkz. bulgu1 docstring'i).

    NODE EKSENI (28 Tem): eski capa SABIT 'python3' idi -> deploy.yml'e node ile kosulan bir
    kabul testi eklense bile kapi onu 'kosulmuyor' sayardi; tek cikis yolu GERCEKTE KOSAN bir
    testi 'muaf' diye izin listesine yazmakti (yalan kayit) ya da testi hic baglamamakti
    (cagrisiz nobetci). Olculdu: 'run: node shop/test/konfigur-fail-closed.mjs' adimi
    eklendigi halde kapi KAPSAMSIZ diyordu. Kapsam KURALI degismedi, yalnizca capanin
    yorumlayicisi dosya uzantisindan turetilir hale geldi."""
    return re.compile(r"^" + _yorumlayici(yol) + r"\s+" + re.escape(yol) + r"(?![\w./-])")


def _icra_satir_indeksleri(deploy_metin, yol):
    """<yol>'u FIILEN kosan satirlarin (0-tabanli) indekslerini dondur.

    kosulan() ile AYNI semantik (_icra_govdesi + _onek_re) — mutant ureticileri
    bunu kullanir, boylece 'kapinin saydigi satir' ile 'mutasyonun sildigi satir'
    ayrisamaz. Ayni yol BIRDEN COK adimda kosuluyorsa HEPSI dondurulur."""
    onek = _onek_re(yol)
    idx = []
    for i, ham in enumerate(deploy_metin.splitlines()):
        g = _icra_govdesi(ham)
        if g and onek.match(g):
            idx.append(i)
    return idx


def _silme_mutanti(deploy_metin, yol):
    """(mutant_metin, silinen_satir_sayisi) — <yol>'u kosan TUM icra satirlari silinir."""
    satirlar = deploy_metin.splitlines(keepends=True)
    idx = set(_icra_satir_indeksleri(deploy_metin, yol))
    kalan = [s for i, s in enumerate(satirlar) if i not in idx]
    return "".join(kalan), len(idx)


def _yorum_mutanti(deploy_metin, yol):
    """(mutant_metin, cevrilen_satir_sayisi) — <yol>'u kosan TUM icra satirlari
    '<girinti># python3 <yol> ...' biciminde YORUMA cevrilir (girinti + satir sonu korunur).
    T7 kanaryasi: python3-onekli bir yorum 'kosuluyor' SAYILMAMALIDIR."""
    satirlar = deploy_metin.splitlines(keepends=True)
    idx = set(_icra_satir_indeksleri(deploy_metin, yol))
    yeni = []
    for i, ham in enumerate(satirlar):
        if i not in idx:
            yeni.append(ham)
            continue
        govde = _icra_govdesi(ham)
        girinti = ham[:len(ham) - len(ham.lstrip())]
        son = "\n" if ham.endswith("\n") else ""
        yeni.append("%s# %s%s" % (girinti, govde, son))
    return "".join(yeni), len(idx)


def kosulan(deploy_metin, kesif):
    """deploy.yml'de FIILEN ICRA edilen (kosulan) kesif dosyalarini dondur.

    BULGU 1 + T7 (curutucu/olcum kanitladi): eski regex TUM metni tariyordu ->
    bir YORUM / step-name / echo-string'de gecen ad da 'kosuluyor' sayiliyordu;
    biri 'run: python3 tools/x-test.py' satirini silip yerine '# python3
    tools/x-test.py' yorumu birakinca kapi SAHTE-YESIL kaliyordu (olu nobetci
    CI'dan success gecerdi). 072c0294 eslesmeyi 'python3 <yol>' on-ekine daraltti
    ama YORUM SATIRLARINI hala eliyordu degil -> python3 onekli bir yorum yine
    eslesiyordu. FIX: eslesmeyi GERCEK KOMUT GOVDESINE ve komutun BASINA capala
    (_icra_komutlari yorumlari eler, 'run:' onekini soyar). Negatif ileri-bakis
    (?![\\w./-]): uzun bir baska yolun on-eki olarak yanlis eslesmesin.
    CAPA TEK KAYNAKTAN: _onek_re() — mutant ureticileri de ayni fonksiyonu kullanir."""
    kos = set()
    komutlar = _icra_komutlari(deploy_metin)
    for yol in kesif:
        onek = _onek_re(yol)
        if any(onek.match(k) for k in komutlar):
            kos.add(yol)
    return kos


# T8: kosulan()'in capasina uyan "bare" form — komut govdesi 'python3 <duz-gorece-yol>'
# ile baslar (yol '-' bayragiyla, './' ile ya da '/' tam-yolla BASLAMAZ).
SAYILABILIR_PY3 = re.compile(r"^python3\s+[A-Za-z0-9_][\w./-]*(?:\s|$)")


def sayilamayan_python3(deploy_metin):
    """T8 GELECEK-ROBUSTLUK UYARISI (BLOKLAMAZ — exit kodunu ETKILEMEZ).

    T7 capasi ('^python3 <yol>') su GERCEK-ICRA formlarini SAYAMAZ: 'env X=1 python3 ...',
    'cd x && python3 ...', 'python3 -X utf8 tools/x.py' (bayrak araya), 'python3 ./tools/x.py',
    '/usr/bin/python3 ...'. Cari deploy.yml'de hepsi bare form (18/18, olculdu T8) -> cari
    sorun YOK. RISK: gelecekte biri kapiyi bu formlarla eklerse kosulan() onu 'kosulmuyor'
    sanir -> YANLIS-POZITIF KIRMIZI tum yayini durdurur ve kapi suclanir. Bu fonksiyon
    _icra_komutlari()'ndan gecen (YORUM OLMAYAN) satirlarda 'python3' gecen ama bare capaya
    uymayan satirlari dondurur; main() bunlari BLOKLAMAYAN uyari olarak basar."""
    supheli = []
    for k in _icra_komutlari(deploy_metin):
        if "python3" not in k:
            continue
        if SAYILABILIR_PY3.match(k):
            continue
        supheli.append(k)
    return supheli


# ---- GEREKCE SABITLERI -----------------------------------------------------
R_AYRI = ("Ayri alt-proje/dagitim hedefi (shop=Cloudflare Worker, onizleme, jenerator kendi "
          "harness'i). Bu is akisi YALNIZ GitHub Pages site build'i; bu suite o projenin CI "
          "hattinda kosulur, Pages job'una girmez.")
R_NODE = ("CI build job'u Python-only (setup-node yok) -> JS/Node suite'i kosamaz. Ayri bir "
          "node job'u gerekir (RAPOR onerisi).")
R_AG = ("Ag/uzak platform erisimi gerektirir (parite CDN'e vurur) -> CI'da deterministik degil; "
        "ag-izinli ayri adim gerekir (RAPOR onerisi).")
R_YOL = ("Mimar-disiplin kapisi: mutlak /Users/okan/dev/pruvo yoluna VE commit EDILMEYEN "
         ".claude/settings.json + .git/hooks kablolamasina bagli -> GitHub fresh checkout'ta "
         "yapisal olarak KIRMIZI. Yerel gelistirici disiplini araci, deploy CI adimi degil.")
R_YAVAS = ("Yerelde >30s (build+ag ya da mutasyon harness) -> tek build job'unu blokar; "
           "izole/ayri job olmadan Pages hattina alinmaz (RAPOR onerisi).")
R_SONRA = ("Offline + yerelde YESIL, ama Paket C kapsami YALNIZ mimarin verdigi cekirdek "
           "eklemeleri CI'ya aldi. Bu test sonraki turda (ubuntu path/env dogrulamasi sonrasi) "
           "CI'ya alinabilir — kod-kilidi ornegi 'yerel-yesil / CI-kirmizi' tuzagini kanitladi, "
           "o yuzden kor-ekleme yapilmadi.")
R_HOOK = ("Claude Code PreToolUse KANCASI, kosulabilir kabul testi DEGIL: stdin'den JSON alir, "
          "karar objesi dondurur (argumansiz kosunca girdi yok -> exit 0, hicbir sey kanitlamaz). "
          "Yerel ajan disiplin cihazi; GitHub Pages build'inde karsiligi yok.")
R_GIZLI = ("Gizli/izlenmeyen girdiye bagli: .urun-kaynaklari.json (gitignore) + working-tree'de "
           "stage'lenmis PARTI farki. CI fresh checkout'unda ikisi de YOK -> kapi bos parti "
           "gorup anlamsiz YESIL yakar (sahte nobetci). Urun-ekleme hattinda (MaCiT) yerel "
           "kosulur; deploy hattinin girdisi degil.")
R_TASARIM = ("TASARIM GEREGI yayin-disi (kendi dosyasindaki not): 'bu kapi build.py'ye BAGLANMAZ "
             "— tek kotu kategori TUM yayini kirmasin'. Kategori drifti urunu katalogda birakir, "
             "yalniz filtreden dusurur; yayini bloklamak orantisiz. Bagimsiz calistirilabilir "
             "kabul testi olarak yerelde/duzeltme akisinda kosulur.")
R_YEREL_HIJYEN = ("Yerel calisma-agaci hijyeni: .gitignore blogunun CONTENT_PAGES ile ortusmesini "
                  "denetler. Drift CI'da GORUNMEZ (uretilen dizinler fresh checkout'ta yok) ve "
                  "canli siteyi bozmaz — yalniz gelistiricinin `git status`ini kirletir/kazara "
                  "commit riski dogurur. Yayini bloklamasi orantisiz; commit oncesi yerel kapi.")
R_FTS5 = ("Yerel fts5-trigram sqlite gerektirir (sema-yukleme adiminda CREATE VIRTUAL TABLE ... "
          "USING fts5(tokenize='trigram')). CI ubuntu stok sqlite3'unde fts5-trigram tokenizer'i "
          "yok -> test daha sema yuklerken patlar (yerel-yesil / CI-kirmizi). R_YAVAS/R_YOL ile "
          "ayni sinif: yapisal olarak CI-disi, deploy.yml'e EKLENMEZ; canli D1 dogrulamasi ayri "
          "go-live fazinda yapilir.")

# ---- IZIN LISTESI (muaf test -> GEREKCE). Bos gerekce = exit 1. ----------
IZIN_LISTESI = {
    # --- Ayri dagitim hedefleri (shop / onizleme / jenerator) ---
    "shop/test/eposta.mjs": R_AYRI,
    "shop/test/kabul.js": R_AYRI,
    "shop/test/olcum-kapisi.cjs": R_AYRI,
    "shop/test/olcum.mjs": R_AYRI,
    "shop/test/ref-route.mjs": R_AYRI,
    "shop/test/sepet-panel.js": R_AYRI,  # B paketi YESILLEDI; shop ayri Worker hedefi (kardesleri gibi)
    "onizleme/test/eslem-olcum.py": R_AYRI,
    "onizleme/test/kabul.js": R_AYRI,
    "onizleme/test/kapi1.js": R_AYRI,
    "onizleme/test/duman_toka_kabul.py": R_AYRI,  # onizleme ayri deploy hedefi (onizleme-imaj.yml + wrangler); duman adimi statik kabul testi (toka govdesi), ana site deploy.yml'e ait degil — KaaN, Okan onayli 27 Tem
    "onizleme/test/iki-govde-olcum.py": (
        "2-renk MESH olcumu OPENSCAD ister (ucgen/bbox/hacim); ana site deploy.yml'de "
        "openscad YOK ve yerel Mac'te SIGABRT veriyor -> onizleme-imaj.yml'de imaj "
        "konteyneri ayaktayken kosar (duman adiminin icinde). "
        "🔴 DUZELTME (30 Tem, OLCULDU): bu gerekcenin eski son cumlesi 'cagri satiri "
        "paket-tazelik-kapisi.py'nin imaj-akisi nobetiyle ayni dosyada durur' diyordu — "
        "YANLISTI. paket-tazelik-kapisi.py'nin CAGRI_CAPASI sabiti YALNIZ KENDI cagri "
        "satirini ('tools/paket-tazelik-kapisi.py --paket') izliyor; iki-govde cagrisi "
        "NOBETSIZDI (cagriyi sil / yoruma al / `|| true` ekle -> dort denetci de rc=0). "
        "Cagri satiri ARTIK tools/is-akisi-kapisi.py BOLUM B tarafindan izleniyor "
        "(deploy.yml'de bloklayici adim; silme/yorum/`|| true`/`|| :`/"
        "`continue-on-error: true`/`if: false` -> KIRMIZI)."),
    "onizleme/test/fiyat-taban-olcum.mjs": "Kabul KAPISI DEGIL — fiyat regresyonu icin dokum/karsilastirma ARACI (--yaz / --karsilastir). Sabit bir taban dosyasi repoda tutulmadigi icin CI'da tek basina anlamli bir iddiasi yoktur; fiyat kapilari ayri ve bloklayicidir (tools/konfigur-test.py, shop/test/fiyat-prova.mjs, shop/test/iki-renk-ucret.mjs).",
    "jenerator/test/birlestir.py": R_AYRI,
    "jenerator/test/dogrula.py": R_AYRI,
    "jenerator/test/fiyat-tablosu-uret.py": R_AYRI,
    "jenerator/test/fiyat-test.js": R_AYRI,
    "jenerator/test/hacim-eval.js": R_AYRI,
    "jenerator/test/kabul.py": R_AYRI,
    "jenerator/test/kalibrasyon-referans-uret.py": R_AYRI,
    "jenerator/test/kalibrasyon-senkron.js": R_AYRI,
    "jenerator/test/stl_hacim.py": R_AYRI,
    "jenerator/test/vida-referans-uret.py": R_AYRI,
    "jenerator/test/vitrin-kabul.js": R_AYRI,
    # --- tools/ JS (CI'da node yok) ---
    "tools/attribution-ref-test.js": R_NODE,
    "tools/marka-limit-test.js": R_NODE,
    "tools/riza-tikkimligi-test.js": R_NODE,
    "tools/parite-test.js": R_AG,
    # --- parite karar-cekirdegi harness'leri (27 Tem): AGSIZ + yerelde YESIL ---
    # ⚠️ NOT (durust gerekce): CI'da setup-node VAR, yani bu ucu TEKNIK olarak deploy.yml'e
    # eklenebilirdi. Eklenmemelerinin sebebi teknik degil SURECSEL: bu turda deploy.yml'e
    # 0 HUNK sarti var (dosyanin yazari paralel bir isci dali). Sonraki turda eklenmeli —
    # onerilen sira: parite-sozlesme-test.py (0,3 s) -> parite-fikstur-test.js (6,7 s) ->
    # parite-mutasyon-test.js (217 s, ayri/izole job).
    "tools/parite-fikstur-test.js": (
        R_SONRA + " Somut: AGSIZ karar-cekirdegi fiksturu (29 senaryo + 1 birim blogu, "
        "224 iddia, 6,7 s olculdu, canliya 0 istek). deploy.yml'e 0-hunk sarti nedeniyle "
        "bu turda eklenmedi."),
    "tools/parite-mutasyon-test.js": (
        R_YAVAS + " OLCULDU: 14 mutant x fikstur kosumu = 217 s (tek build job'unu blokar; "
        "M14 asilma nobeti tek basina ~120 s). Ayrica deploy.yml'e 0-hunk sarti nedeniyle "
        "bu turda eklenmedi; izole/ayri job'a alinmasi onerilir."),
    "tools/parite-sozlesme-test.py": (
        R_SONRA + " Somut: 4 tuketicinin cikis-kodu eslemesini olcer (47 iddia, 0,2 s, "
        "agsiz). deploy.yml'e 0-hunk sarti nedeniyle bu turda eklenmedi — CI'ya alinacak "
        "ILK aday budur (en ucuz, en yuksek getirili)."),
    "tools/url-senkron-test.js": R_NODE,  # E paketi YESILLEDI; JS suite, CI'da node yok
    # --- tools/ python: mimar-disiplin (mutlak yol + commit'siz kablolama) ---
    "tools/mimar-kilit-test.py": R_YOL,
    "tools/mimar-commit-kapisi-test.py": R_YOL,
    "tools/mimar-kapi-mutasyon-test.py": R_YOL,
    # MAKINEYE BAGIMLI: kardes mimar evi dizinleri (~/dev/pruvo-hasat, -jenerator, -pazarlama,
    # -bot, -advisor) CI runner'inda YOK -> fail-closed test orada yapisal KIRMIZI yanar ve
    # bloklayici adim olarak TUM yayini durdurur (yedekle-test.py / yedek-hook-test.py emsali).
    "tools/mimar-kapi-6ev-test.py": (
        R_YOL + " Somut olarak: olcum girdisi 5 KARDES MIMAR EVININ dizini (~/dev/pruvo-hasat, "
        "-jenerator, -pazarlama, -bot, -advisor) ve o evlerin commit EDILMEYEN "
        ".claude/mimar-icra-kapisi.py kapilari. CI fresh checkout'unda bu evlerin hicbiri "
        "YOKTUR -> 6 evin 5'i olculemez, fail-closed test KIRMIZI yanar."),
    "tools/kapi-envanteri-test.py": R_YOL,
    "tools/kod-kilidi-test.py": R_YOL,  # E paketi YESILLEDI; mutlak /Users/okan/dev/pruvo yoluna bagli -> fresh checkout'ta yapisal KIRMIZI
    "tools/agent-kapisi-test.py": (
        R_SONRA + " Somut: AGENT-KAPISI kabul testi (28 Tem) — mimar-icra-kapisi.py'nin "
        "Agent/Task kolu + mimar-kapi-kur.py kablosu; mimar-kilit/6ev/mutasyon/kod-kilidi ile "
        "AYNI aile. Bolum A (gate davranisi; cwd STRING olarak verilir, gercek repo yoluna bagli "
        "DEGIL) + Bolum B (kur.py gecici settings KOPYALARI) offline-YESIL. Bolum C (6-EV "
        "enjeksiyon) girdisi kardes mimar evi gate'leri (/Users/okan/dev/pruvo-hasat, -advisor "
        ".claude/mimar-icra-kapisi.py); CI fresh checkout'ta bu evler YOK -> C guarded-CEVRE-ATLANAN "
        "(mimar-kapi-6ev-test.py R_YOL girdisiyle AYNI kaynak, ama orasi fail-closed KIRMIZI, "
        "burasi skip=exit 0). Yani CI'da yalniz A+B kapsanabilirdi; deploy.yml'e 0-hunk merge "
        "turunda kor-eklenmedi (kod-kilidi'nin kanitladigi yerel-yesil/CI-kirmizi tuzagi) -> A+B "
        "sonraki turda CI'ya alinacak ilk adaylardan."),
    # --- tools/ NOBETCILER (*-kapisi.py) — kesif 21 Tem genisletildi, CI'da kosmayanlar ---
    "tools/komut-stili-kapisi.py": R_HOOK,
    "tools/mimar-icra-kapisi.py": R_HOOK,
    "tools/mimar-commit-kapisi.py": (
        R_HOOK + " Ayrica git commit backstop'u olarak commit EDILMEYEN .git/hooks kablolamasina "
        "ve ana-checkout/worktree ayrimina bagli (R_YOL ile ayni sinif)."),
    "tools/denetim-kapisi.py": R_GIZLI,
    "tools/kategori-kapisi.py": R_TASARIM,
    "tools/gitignore-kapisi.py": R_YEREL_HIJYEN,
    "tools/regresyon-kapisi.py": (
        R_YOL + " Ek olarak varsayilan suite'i node tools/parite-test.js + parite-ege.js icerir "
        "(CI'da node YOK + ag gerekir, R_NODE/R_AG) ve kapsadigi testler zaten tek tek bu "
        "listede muhasebeli -> CI'da kosmasi cift-sayim olurdu."),
    # --- tools/ python: yavas/harici (>30s) ---
    "tools/feed-cache-bust-test.py": (
        R_YAVAS + " OLCULDU (F2 raporu): test build.py'yi 2 KEZ kosuyor -> tek build 108,0 s, "
        "test toplam 227,9 s (mutasyon kosumlarinda 148-302 s). Tek build job'una ~4-5 dk "
        "eklerdi, kendisi de deploy'un ZATEN kosturdugu build.py'nin ciktisini yeniden uretir. "
        "CI'YA ALINMA KOSULU (RAPOR onerisi): test build.py'yi alt-surec olarak degil "
        "render_merchant_feed'i import edip 2 kez cagirarak kosarsa sure saniyeye iner ve "
        "bloklayici adim olarak eklenebilir."),
    "tools/filament-test.py": R_YAVAS,
    "tools/kaynak-akis-test.py": R_YAVAS,
    "tools/test-bbox-3mf.py": R_YAVAS,
    # --- tools/ python: fts5-trigram sqlite gerektiren (CI ubuntu'da yok) ---
    "tools/taban-fiyat-d1-test.py": R_FTS5,
    # --- tools/ python: offline-yesil, sonraki turda alinabilir ---
    "tools/d1-sync-durum-test.py": R_SONRA,
    "tools/denetim-kapisi-test.py": R_SONRA,
    "tools/derin-cap-test.py": R_SONRA,
    "tools/durum-edge-test.py": R_SONRA,
    "tools/durum-test.py": R_SONRA,
    "tools/gorsel-anahtar-test.py": R_SONRA,
    "tools/gorsel-kapisi-test.py": R_SONRA,
    "tools/kaynak-entegrasyon-test.py": R_SONRA,
    "tools/lisans-havuz-test.py": R_SONRA,
    "tools/makerworld-ara-test.py": R_SONRA,
    "tools/makerworld-lisans-test.py": R_SONRA,
    "tools/marka-filtre-test.py": R_SONRA,
    "tools/meta-piksel-test.py": R_SONRA,
    "tools/olculmemis-siparis-test.py": R_SONRA,
    "tools/printables-lisans-test.py": R_SONRA,
    "tools/siparisler-test.py": R_SONRA,
    "tools/stl-bbox-binary-test.py": R_SONRA,  # harvest-adaptor birim testi (printables-api.py stl_bbox); sentetik/offline/<1s -> ayni sinif printables-lisans-test.py / test-bbox-3mf muaf, deploy.yml'ye kor-eklenmedi
    "tools/thing-hazirla-bbox-test.py": (
        "thing-hazirla.py import aninda hardcoded ROOT=/Users/okan/dev/pruvo altindan .thingiverse-token "
        "okur -> CI fresh-checkout'ta import PATLAR (yapisal CI-kirmizi, R_YOL sinifi). bbox() "
        "BELIRSIZ-BIRIM birim testi (metre-sezgisi 2. kopyasi, stl-bbox testi bu ayri fonksiyonu "
        "kapsamaz); sentetik/offline/<1s, yerelde YESIL. test-bbox-3mf emsali: deploy.yml'e kor-eklenmedi."),
    "tools/surum-test.py": R_SONRA,
    "tools/test-baski-senkron.py": R_SONRA,
    "tools/test-merchant-feed.py": R_SONRA,
    "tools/thing-codex-test.py": R_SONRA,
    "tools/thingiverse-gallery-test.py": R_SONRA,
    "tools/yargi-firearm-test.py": R_SONRA,
    "tools/yazdir-test.py": R_SONRA,
    # NOT: tools/durum-yedek-test.py 27 Tem'de MUAFIYETTEN CIKARILDI -> deploy.yml'de
    # bloklayici adim olarak kosuyor. Olcum: CI taklidinde (bos HOME, Drive yok, sadece
    # takip edilen dosyalar) YESIL (cikis 0). "Hermetik" DEGIL: ortam eksenleri
    # (`ps`/`git`/kaynak kumesi) sorgulandigi icin bir kismi ⚪ OLCULEMEDI olur ve
    # kontrol SAYISI makineye gore degisir. Kontrol SAYISI buraya YAZILMAZ —
    # sayi betigin KENDI ciktisindadir; sabit sayi bir VERI CAPASIDIR ve her yeni
    # nobetci eklendiginde sessizce bayatlar (olculdu: yorumdaki "88/88" gerceginde
    # 89'du, "89/89 ~2 s" ise 4,6 s). Buraya GERI EKLEME: iki yerde birden sayilirsa
    # bu kapi "hem kosuluyor hem muaf" celiskisini yakalar.
    "tools/yedek-hook-test.py": (
        R_YOL + " Somut olarak: .git/hooks/pre-push commit EDILMEZ (per-makine) -> CI "
        "fresh checkout'unda kurulu blok YOKTUR, 'olu konum' nobetcisi orada yapisal "
        "olarak kirmizi yanar. Yerel push disiplini araci; deploy CI adimi degil."),
    "tools/yedekle-test.py": (
        "Olcum girdisi MAKINEYE OZGU ve git DISI: ~/.claude/skills agaci (yedeklenen sey) ile "
        "Google Drive mount'u. CI fresh checkout'unda ikisi de YOK -> kapsam kontrolleri "
        "yapisal olarak KIRMIZI yanar (R_YOL sinifi; sentetik sir/mutasyon bolumleri offline "
        "yesil olsa da testin cekirdek iddiasi 'gercek skill agaci planda mi' CI'da "
        "olculemez). Ayrica yedekle.py yayin hattinin parcasi degil: yerel disk-kaybi "
        "sigortasi -> Pages build'ini bloklamasi orantisiz."),
}


def bulgu1_mutasyon_kontrol():
    """BULGU 1 KALICI MUTASYON NOBETCISI (curutucu kanitladi):
    Bir testin 'run: python3 <yol>' ICRA satiri deploy.yml'den silinip ADI yalniz bir
    YORUM/step-name'de kalirsa, kosulan() o testi 'kosuluyor' SAYMAMALIDIR. Eski regex tum
    metni tariyordu -> yalniz-yorum mensiyonu sahte-yesil yapiyordu (olu nobetci CI'dan
    success gecerdi). Bu kontrol GERCEK deploy.yml'den mutant uretir ve uc sarti dogrular:
      + POZITIF: gercek deploy o yolu SAYAR (run: ile gecer).
      + SILME MUTANTI: icra satir(lar)i silinip ad yalniz yorumda kalinca SAYMAZ.
      + YORUM MUTANTI (T7): icra satir(lar)i '# python3 <yol>' yorumuna cevrilince SAYMAZ
        -> yorum-bypass (olculdu: B/C/D/E/F kanaryalari) geri gelirse KIRMIZI yanar.

    NEDEN COK-SATIR CAPASI GEREKTI (olculdu 27 Tem, bu nobetcinin KENDI ariza kaydi):
    mutant uretimi eskiden TEK bir duz metin sabitini ('        run: python3 <hedef>\\n')
    replace(..., 1) ile YALNIZ 1 KEZ siliyordu. deploy.yml'e hedefi ikinci kez kosan bir
    adim ('run: python3 tools/ci-kapsam-test.py --kendini-test') eklenince o satir kosulan()
    capasina UYUYOR (yolun ardindan BOSLUK var -> (?![\\w./-]) negatif ileri-bakisi geciyor),
    ama mutasyon onu GORMUYORDU: mutantta yol HALA 'kosuluyor' sayiliyor ve nobetci
    "BULGU 1 GERI GELDI" + "T7 YORUM-BYPASS GERI GELDI" ile SAHTE-KIRMIZI yaniyordu.
    Yani harness kendi hedefinin cagri sayisina KIRILGANDI. FIX: mutasyon SATIR BAZLI ve
    kosulan() ile AYNI semantikten (_icra_govdesi + _onek_re) turetilir; hedefin TUM icra
    satirlari kapsanir. Ikinci bir eslesme mantigi YAZILMAZ (capa tek kaynak).

    BAYAT-HARNESS KORUMASI (fail-closed): hedefi kosan HIC icra satiri bulunamazsa ya da
    mutasyon sonrasi geriye kosan satir KALIRSA sessizce yesil GECMEZ -> (False, tani).
    (ok, hata_satirlari) dondurur."""
    hedef = "tools/ci-kapsam-test.py"
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()

    icra_idx = _icra_satir_indeksleri(gercek, hedef)
    if not icra_idx:
        return False, ["gercek deploy.yml'de %s'yi KOSAN hicbir icra satiri yok "
                       "(cagri bicimi degistiyse bu nobetciyi guncelle)" % hedef]

    mutant, silinen = _silme_mutanti(gercek, hedef)
    yorum_mutant, cevrilen = _yorum_mutanti(gercek, hedef)
    if silinen == 0 or cevrilen == 0:
        return False, ["mutant uretimi HICBIR satiri degistirmedi (silinen=%d, cevrilen=%d) "
                       "-> harness bayat, bu nobetciyi guncelle" % (silinen, cevrilen)]
    # Fail-closed post-kosul: mutantlarda hedefi kosan satir KALMAMALI. Kalirsa mutasyon
    # eksiktir ve asagidaki iddialar 'sahte-kirmizi' uretir (tam da 27 Tem arizasi).
    kalan_silme = _icra_satir_indeksleri(mutant, hedef)
    kalan_yorum = _icra_satir_indeksleri(yorum_mutant, hedef)
    if kalan_silme or kalan_yorum:
        return False, ["mutant uretimi EKSIK: %s'yi kosan satir mutantta KALDI "
                       "(silme mutanti %d, yorum mutanti %d) -> mutasyon capasi cok dar, "
                       "bu nobetciyi guncelle" % (hedef, len(kalan_silme), len(kalan_yorum))]
    if hedef not in mutant:
        return False, ["mutantta yorum mensiyonu kalmadi -> mutasyon testi anlamsiz "
                       "(deploy.yml yorumu %s'yi artik anmiyor)" % hedef]

    kesif = kesfet()
    if hedef not in kesif:
        return False, ["%s kesif predikatiyla bulunamadi (predikat bozulmus)" % hedef]
    hata = []
    if hedef not in kosulan(gercek, kesif):
        hata.append("POZITIF KONTROL BASARISIZ: gercek deploy.yml %s'yi kosulan saymadi" % hedef)
    if hedef in kosulan(mutant, kesif):
        hata.append("BULGU 1 GERI GELDI: %d icra satiri silinip yalniz yorumda kalan %s "
                    "hala 'kosuluyor' sayildi (regex icra baglamina daralmali)"
                    % (silinen, hedef))
    if hedef in kosulan(yorum_mutant, kesif):
        hata.append("T7 YORUM-BYPASS GERI GELDI: %d icra satiri '# python3 <yol>' yorumuna "
                    "cevrilince %s hala 'kosuluyor' sayildi (yorum satirlari elenmeli)"
                    % (cevrilen, hedef))
    return (not hata), hata


# Yalniz BELLEKTE kesif listesine enjekte edilen sentetik yol. Repoda BOYLE BIR DOSYA YOK
# (ve olmamali): gercek bir kapsamsiz test dosyasi yaratmak kapinin kendi 1. kuralini
# tetikler ve kapiyi kalici kirmiziya cakardi.
SENTETIK_KAPSAMSIZ = "tools/zzz-sentetik-kapsamsiz-test.py"

# Iddia RAPOR SATIRININ KENDISINE capalanir (etiketi degistiren biri nobetciyi de
# guncellemek zorunda kalsin diye) — degeri gövde degiskeninden degil, basilan metinden oku.
# CAPA SATIR SONUNA DEGIL SAYIYA (3. tur curutucu olcumu): eski `\s*$` capasi asiri
# kirilgandi — rapor satirinin SONUNA kozmetik bir ek yapilsa ('kosulan' satirindaki gibi
# parantezli detay listesi) SAYI DOGRU basildigi halde regex eslesmiyor -> n is None ->
# kapi SAHTE-KIRMIZI, ustelik teshis "etiket degistiyse guncelle" diyor ama etiket
# DEGISMEMIS oluyor. Bu kapi deploy.yml'de continue-on-error'suz kosar; yanlis-pozitif TUM
# yayini durdurur ([[kapi-kapsam-eksen-secimi]]). `\b` ile etiket GERCEKTEN degisirse hala
# eslesmez ve dogru teshisi verir — istenen davranis odur, o KALIR.
MUAF_SATIR_RE = re.compile(r"^\s*Muaf \(izin listesi\)\s*:\s*(\d+)\b")


def _muaf_sayisi(satirlar):
    """Rapor satirlarindan "Muaf (izin listesi)" degerini oku; yoksa None."""
    for s in satirlar:
        m = MUAF_SATIR_RE.match(s)
        if m:
            return int(m.group(1))
    return None


def muaf_sayaci_kontrol():
    """MUAF SAYACI KALICI NOBETCISI (27 Tem olcumu).

    OLCULEN HATA: rapor satiri `muaf = [y for y in kesif if y not in kos]` ile
    uretiliyordu -> "Muaf (izin listesi)" etiketiyle basilan sayi, IZIN_LISTESI'nde
    OLMAYAN (yani KAPSAMSIZ) dosyalari da iceriyordu. Somut: bir merge sirasinda
    tools/mimar-kapi-6ev-test.py kapsamsizken satir "Muaf: 71" yazdi; gercek muafiyet
    eklendikten SONRA (IZIN_LISTESI 70 -> 71) satir YINE "71" yazdi. Yani basilan sayi
    muafiyet eklemesine KOR ve kapsamsiz dosya sessizce "muaf" etiketleniyordu.

    NEDEN BLOKLAYICI: merge prosedürü (~/.claude/skills/merge-kapisi/SKILL.md) bu sayiyi
    dalin ONCE/SONRA olcumu olarak rapor ettirir. Sayi etiketine uymayinca "kac muafiyet
    eklendi" sorusu bu ciktidan cevaplanamaz hale gelir ve IZIN_LISTESI'ni elle AST okumak
    gerekir (27 Tem'de aynen bu yasandi). Yani bu bir kozmetik degil, OLCUM kanali hatasi.

    YONTEM: GERCEK deploy.yml + GERCEK kesif uzerine yalniz bellekte SENTETIK bir kapsamsiz
    yol enjekte edilir ve denetle(..., kontroller=False) cagrilir -> CI'da kosan kodun TA
    KENDISI olculur, kopya mantik yazilmaz. (kontroller=False sart: ozyineleme korumasi.)
      TEMEL: sentetiksiz kosum; basilan Muaf sayisi = N, exit kodu = TEMEL_KOD.
      MUTLAK: TEMEL_KOD == 0 iken N == len(IZIN_LISTESI) OLMAK ZORUNDA (asagida gerekcesi).
      (a) kesif + SENTETIK, izin = IZIN_LISTESI
          -> exit 1 + SENTETIK icin KAPSAMSIZ satiri + Muaf sayisi HALA N (sizmamali).
      (b) kesif + SENTETIK, izin = IZIN_LISTESI + {SENTETIK: gerekce}
          -> exit TEMEL_KOD (muafiyet kapiyi temelin verdigi hale geri dondurur)
             + Muaf sayisi TAM OLARAK N+1 (muafiyete kor olmamali).
    (a)/(b) DELTA iddialaridir; tek baslarina sabit bir kaydirmayi (or. satiri `len(muaf)-1`
    basmak) YAKALAYAMAZ — merge prosedürü MUTLAK sayiyi okudugu icin MUTLAK capa sarttir.

    TEMEL KIRMIZI OLSA DA CALISIR (duzeltme, 27 Tem): iddialar MUTLAK degil TEMELE GORELI
    DELTA'dir -> "temel kirmizi, olcum anlamsiz" diye erken donmez. Eski hali tam da bu
    bug'in gorundugu senaryoda (repoda GERCEK bir kapsamsiz test dosyasi varken) kapiya
    IKINCI bir ❌ satiri ekliyordu: kapi zaten KAPSAMSIZ ile kirmiziyken "SONUC: KIRMIZI
    (2 sorun)" cikiyordu. merge prosedürü bu SORUN SAYISINI okur -> olcum kanalini duzeltmek
    icin yazilan nobetci, kirmizi halde olcum kanalini yeniden kirletiyordu; ustelik nobetci
    en cok ise yarayacagi anda (kapsamsiz VARKEN) kendini kapatiyordu. Tek istisna n is None:
    etiket/regex kaymasinda gercekten olculecek sey yoktur, orada erken donus KALIR."""
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()
    kesif = kesfet()
    if SENTETIK_KAPSAMSIZ in kesif:
        return False, ["sentetik yol repoda GERCEKTEN var: %s -> nobetci anlamsizlasti "
                       "(dosyayi sil ya da sentetik adi degistir)" % SENTETIK_KAPSAMSIZ]

    temel_kod, temel_satirlar = denetle(gercek, kesif, IZIN_LISTESI, kontroller=False)
    n = _muaf_sayisi(temel_satirlar)
    if n is None:
        # TEK mesru erken donus: etiket/regex kaymissa olculecek sayi YOKTUR.
        return False, ["temel raporda 'Muaf (izin listesi)' satiri bulunamadi "
                       "(etiket degistiyse MUAF_SATIR_RE'yi guncelle)"]
    # NOT: temel_kod KIRMIZI olabilir (repoda gercek bir kapsamsiz dosya varken normaldir).
    # Erken DONULMEZ; asagidaki iddialar temel_kod'a GORELI kurulur -> nobetci o halde de
    # olcer ve kapinin sorun sayisini SISIRMEZ.

    kesif_sentetik = sorted(list(kesif) + [SENTETIK_KAPSAMSIZ])
    hata = []

    # MUTLAK CAPA (3. tur curutucu olcumu): asagidaki (a)/(b) iddialari DELTA'dir ve n, n_a,
    # n_b UCU DE AYNI rapor satirindan okunur -> sabit bir KAYDIRMA (olculdu: satiri
    # `len(muaf) - 1` basacak sekilde degistirmek) delta'lari BOZMAZ, nobetci HIC KONUSMAZ,
    # ama basilan mutlak sayi (70) yalan olur. merge prosedürü tam da bu MUTLAK sayiyi olcum
    # olarak okudugu icin delta korunumu YETMEZ.
    # NEDEN GECERLI: kapi YESIL iken kural 3 (bayat izin: artik kesfedilmiyor) ve kural 4
    # (bayat izin: artik kosuluyor) ZATEN sifirdir -> izin ⊆ kesif ve izin ∩ kos = bos ->
    # tanim geregi muaf == IZIN_LISTESI. Yani yesil kosumda basilan sayi len(IZIN_LISTESI)'ne
    # ESIT OLMAK ZORUNDA. temel_kod != 0 iken bu esitlik GECERLI DEGILDIR (bayat girisler
    # sapma yaratir) -> capa YALNIZ yesil temelde uygulanir; (a)/(b) delta iddialari her iki
    # halde de aynen kalir.
    if temel_kod == 0 and n != len(IZIN_LISTESI):
        hata.append("MUTLAK SAYI YALAN: basilan %r, gercek izin listesi %d -> delta korunmus "
                    "olsa da rapor sayisi merge olcumunu yaniltir"
                    % (n, len(IZIN_LISTESI)))

    # (a) sentetik yol KAPSAMSIZ: red semantigi korunmali VE muaf sayisina SIZMAMALI
    kod_a, satir_a = denetle(gercek, kesif_sentetik, IZIN_LISTESI, kontroller=False)
    n_a = _muaf_sayisi(satir_a)
    if kod_a != 1:
        hata.append("(a) KAPSAMSIZ TESPITI BOZUK: sentetik kapsamsiz yol eklenince exit 1 "
                    "bekleniyordu, exit %r geldi" % kod_a)
    if not any(("KAPSAMSIZ" in s and SENTETIK_KAPSAMSIZ in s) for s in satir_a):
        hata.append("(a) KAPSAMSIZ SATIRI YOK: %s icin 'KAPSAMSIZ' hatasi beklenmisti"
                    % SENTETIK_KAPSAMSIZ)
    if n_a != n:
        hata.append("(a) MUAF SAYACI SIZDIRIYOR: kapsamsiz dosya 'Muaf (izin listesi)' "
                    "sayisina girdi (beklenen %d, basilan %r) -> sayi etiketine uymuyor "
                    "(27 Tem hatasinin ta kendisi)" % (n, n_a))

    # (b) sentetik yol GEREKCELI MUAF: kabul semantigi korunmali VE sayi TAM 1 artmali.
    #     Iddia TEMELE GORELI: gerekceli muafiyet kapiyi TEMELIN verdigi hale geri dondurur
    #     (temel yesilse 0, temel kirmiziysa 1 kalir) -> temel kirmizi iken de kirilgan degil.
    izin_b = dict(IZIN_LISTESI)
    izin_b[SENTETIK_KAPSAMSIZ] = ("SENTETIK NOBETCI GIRISI — yalniz bellekte, repoda "
                                  "karsilik gelen dosya yok.")
    kod_b, satir_b = denetle(gercek, kesif_sentetik, izin_b, kontroller=False)
    n_b = _muaf_sayisi(satir_b)
    if kod_b != temel_kod:
        hata.append("(b) MUAFIYET KABULU BOZUK: sentetik yol gerekceyle izin listesine "
                    "eklenince kapi temel verdigi exit %r'e donmeliydi, exit %r geldi (%s)"
                    % (temel_kod, kod_b,
                       "; ".join(s.strip() for s in satir_b if s.strip().startswith("❌"))))
    if n_b != n + 1:
        hata.append("(b) MUAF SAYACI KOR: muafiyet eklenince sayi %d -> %d olmaliydi, "
                    "basilan %r (27 Tem'de olculen 71 -> 71 kor sayaci)" % (n, n + 1, n_b))
    return (not hata), hata


# ---- OZ-NOBETCI ADIMI (zincirin son halkasi) -------------------------------
KENDINI_TEST_BAYRAGI = "--kendini-test"
KENDINI_TEST_TANI = (
    "deploy.yml'de YORUM OLMAYAN hicbir icra govdesinde `--kendini-test` metni GECMIYOR "
    "-> oz-nobetci adimi kalkmis ya da bayragi dusmus. GERI KOY: 'CI kapsam kapisi "
    "oz-nobetcileri' adimi, `run: python3 tools/ci-kapsam-test.py --kendini-test` "
    "(BICIM SERBEST: inline / tirnakli skalar / `run: |` / `>-` / `bash -c` / `python3 -u` "
    "hepsi gecerli). Bayrak adi bilerek degistiyse KENDINI_TEST_BAYRAGI sabitini guncelle.")
KENDINI_TEST_SABIT_TANI = (
    "KENDINI_TEST_BAYRAGI sabiti BOZULMUS (deger: %r). Bos ya da `--` ile baslamayan bir "
    "sabit duz alt-dize aramasini ANLAMSIZ kilar: bos dize HER govdede gecer -> adim "
    "silinse bile nobetci YESIL kalirdi. Sabiti gercek bayrak metnine geri koy "
    "(`--kendini-test`).")


def kendini_test_adimi_kontrol():
    """OZ-NOBETCI ADIMI KALICI NOBETCISI (3. tur curutucu olcumu, 27 Tem).

    OLCULEN DELIK: 791b0366 deploy.yml'e `python3 tools/ci-kapsam-test.py --kendini-test`
    adimini ekledi ve CI'da yesil kostu — AMA EKLENEN ADIMIN KENDISI NOBETCISIZDI.
    Iki mutant sinifi repoda TEK BIR KIRMIZI bile yakmiyordu (olculdu: ikisinde de
    bayraksiz kosum 0, --kendini-test kosumu 0):
      (1) `--kendini-test` adimi deploy.yml'den SILINDI,
      (2) adim duruyor ama `--kendini-test` BAYRAGI dusuruldu (adim ikinci kez duz
          `python3 tools/ci-kapsam-test.py` kosuyor).
    Yani biri oz-nobetci adimini kaldirsa zincir SESSIZCE kopuyordu: bulgu1 +
    muaf sayaci nobetcileri hala denetle(kontroller=True) yolundan cagriliyor gorunse
    de, o adimin korudugu IKI mutant sinifi (nobetci CAGRILARININ silinmesi ve
    denetle()'nin kirmizi cikis yolunun sakatlanmasi) yeniden ORTULU hale geliyordu.

    NEDEN BAYRAKSIZ (BLOKLAYICI) KOLDA YASAR: bu nobetci `--kendini-test` kolunda
    OLURDU — adim silindiginde o kol CI'da ZATEN kosmaz, yani kendi olumunu haber
    veremezdi. Kanit hala kosan DUZ adimdan gelmek ZORUNDA; bu yuzden
    denetle(..., kontroller=True) icinden cagrilir. (--kendini-test kolunda AYRICA
    raporlanir, ama tek GERCEK kapi bayraksiz kosumdur.)

    IDDIA (TEK — mimar hukmu TUR 4): `--kendini-test` ALT-DIZESI, _icra_govdesi()
    suzgecinden gecen (YORUM DEGIL, `name:` DEGIL) govdelerin metninde GECIYOR MU.
    Duz `in` aramasi. Jetonlama YOK, tirnak mantigi YOK, startswith YOK, satir
    birlestirme YOK, regex YOK. Bu fonksiyonun BAGIMSIZ eslestiricisi YOKTUR — capa
    tamamen _icra_komutlari()/_icra_govdesi() ortak suzgecidir.

    🔴 NEDEN BU KADAR DUZ (bu depoda UCUNCU kez ayni delik — [[mimar-kapi-parser-taklidi]]):
    Iki tur boyunca "daha akilli" capalar denendi ve HER IKISI de MESRU yazimlari
    KIRMIZI yakti. Olculen sahte-kirmizilar:
      TUR 2 (`^python3 <yol>` on-eki):  `run: >-` katlanan blok · `run: |` + kabuk
        satir devami (`\\`) · `python3 -u tools/...`
      TUR 3 (elle yazilmis tirnak/jeton ayristiricisi): `run: "..."` cift-tirnakli YAML
        skalari · `run: '...'` tek-tirnakli skalar · `bash -c "..."` · `run: |` blogunda
        satir sonunda `;`  (kapanis tirnagi/noktalama jetonu bozuyordu)
    Bu kapi deploy.yml'de continue-on-error'SUZ kosar -> tek bir sahte-kirmizi TUM
    ekibin yayinini durdurur ([[kapi-kapsam-eksen-secimi]]). Kabuk/YAML yazimini TAHMIN
    eden her capa bu kapida tasinamaz risktir; ayristirici taklidi YAPILMAZ.

    🔴 KABUL EDILEN BEDEL (bilincli daraltma, [[kapi-disiplin-ilkesi]] — kapi disiplin
    cihazidir, hapishane degil): duz alt-dize aramasi MENSIYONU da "duruyor" sayar.
    Somut olarak su hal(ler) artik YESIL gecer ve bu BEKLENEN davranistir:
      * tirnaksiz `echo` mensiyonu:  `run: echo python3 tools/x.py --kendini-test`
      * bayragin BASKA bir betige verilmesi: `run: python3 tools/baska.py --kendini-test`
      * bayragin herhangi bir icra govdesinde serbest metin olarak gecmesi

    MENSIYON ELEMESININ GERCEK SINIRI (olculdu TUR 5; onceki surumde bu cumle FAZLA
    IDDIALIYDI): suzgec yalnizca SATIR BASINI eler — strip() sonrasi `#`, `- name:` ya da
    `name:` ile BASLAYAN satirlar. Dolayisiyla YAKALANAN sey "kanonik yazilmis yorum /
    step adi" mensiyonudur; su UC MESRU YAML biciminde mensiyon SUZGECTEN GECER ve kapi
    YESIL kalir (olculdu, kapi yanlis davranmiyor — iddia zaten "METIN DURUYOR"):
      * `-  name:`   (tireden sonra IKI bosluk)
      * `- "name":`  (tirnakli anahtar)
      * SATIR SONU yorumu:  `run: echo ok   # ... --kendini-test`
    ⚠️ Suzgec bu yuzden GENISLETILMEZ: her genisletme yeni bir bicim-tahmini, yani yeni
    bir sahte-kirmizi yuzeyidir (TUR 2/3 dersi).

    BEYAN — argparse KISALTMALARI: `--kendini` / `--kend` gibi kisaltmalar argparse'ta
    CALISAN komutlardir, ama bayrak metni harfiyen gecmedigi icin bu nobetci onlari
    KIRMIZI yakar. Tani zaten dogru seyi soyler ("adim kalkmis ya da bayragi dusmus" ->
    tam metni yaz). Bilincli tercih: kisaltma yazmak ucuzdur, bicim tahmin eden bir
    esneklik ise pahalidir.

    NE KANITLAR / NE KANITLAMAZ: bu nobetci "adim KOSUYOR ve BLOKLUYOR" demez —
    yalnizca "METIN DURUYOR" der. Kapsam disi kalan SESSIZ-YESIL komsu siniflar
    (BILEREK kapatilmadi): nobetci GOVDESI `return True, []` (ust-harness sorusu,
    nobetci-mutasyon-test.py sinifi) · adima `if: false` · adima
    `continue-on-error: true` · komuta `|| true`. Son ucu deponun 30+ adiminin HEPSI
    icin gecerlidir -> bu nobetcinin gerilemesi DEGIL, ayri ve daha buyuk bir is.

    OLCULDU (28 Tem TUR 4, gecici worktree'de; canli dosyaya mutasyon UYGULANMADI):
      YESIL 11/11 mesru bicim: cift-tirnakli skalar · tek-tirnakli skalar · `bash -c "..."`
        · `run: |` + satir sonunda `;` · `run: >-` katlanan · backslash devami ·
        `python3 -u` · fazla bosluk/TAB · `run: |` blok · `if:`/`env:` bloklu adim ·
        baska job'a tasima.
      KIRMIZI 4/4: adim silindi · bayrak dustu · `name:` icinde tam komut · yalniz
        YAML YORUMU mensiyonu.
    (ok, hata_satirlari) dondurur."""
    # FAIL-CLOSED SABIT DAYANAGI (TUR 5, duz-`in`'in getirdigi yeni yuzey): bos bir sabit
    # HER govdede gecer -> adim silinse bile nobetci YESIL kalirdi. Sahte-kirmizi riski
    # YOK (sabit hep `--kendini-test`), sessiz-yesil riski buyuktu.
    if not KENDINI_TEST_BAYRAGI or not KENDINI_TEST_BAYRAGI.startswith("--"):
        return False, [KENDINI_TEST_SABIT_TANI % (KENDINI_TEST_BAYRAGI,)]
    if not os.path.exists(DEPLOY_VARSAYILAN):
        return False, ["gercek deploy.yml bulunamadi: %s" % DEPLOY_VARSAYILAN]
    with open(DEPLOY_VARSAYILAN, encoding="utf-8") as f:
        gercek = f.read()
    for govde in _icra_komutlari(gercek):
        if KENDINI_TEST_BAYRAGI in govde:
            return True, []
    return False, [KENDINI_TEST_TANI]


# ---- SAF DENETIM GOVDESI ---------------------------------------------------
# main() eskiden hem karar veriyor hem BASIYORDU -> govdeyi disaridan (nobetciden)
# olcmek imkansizdi ve "CI'da kosan kod" ile "test edilen kod" ayrisiyordu.
# denetle() saftir: girdisini parametreden alir, hicbir sey basmaz, (kod, satirlar) dondurur.
# Boylece muaf_sayaci_kontrol() TA KENDISINI olcer (kopya mantik yazmaz).
def denetle(deploy_metin, kesif, izin_listesi, kontroller=True):
    """(exit_kodu, rapor_satirlari) dondurur. Hicbir sey BASMAZ.

    kontroller=True iken kendi mutasyon nobetcilerini (bulgu1 + muaf sayaci) BLOKLAYICI
    olarak kosar. muaf_sayaci_kontrol() bu fonksiyonu tekrar cagirdigi icin oradan
    DAIMA kontroller=False ile girilir (OZYINELEME KORUMASI)."""
    satirlar = []
    kos = kosulan(deploy_metin, kesif)
    kesif_kume = set(kesif)

    # T8: bloklamayan gelecek-robustluk uyarisi (hatalar listesine GIRMEZ, exit degismez).
    for satir in sayilamayan_python3(deploy_metin):
        satirlar.append("UYARI: python3 iceren ama sayilamayan icra satiri "
                        "(bare 'python3 tools/x.py' formu kullan): %s" % satir)

    hatalar = []

    # 2) gerekcesiz izin girisi
    for yol, gerekce in izin_listesi.items():
        if not (gerekce and gerekce.strip()):
            hatalar.append("GEREKCESIZ izin girisi (bos gerekce): %s" % yol)

    # 3) bayat izin: kesfedilmeyen (silinmis/yeniden adlandirilmis) yol
    for yol in izin_listesi:
        if yol not in kesif_kume:
            hatalar.append("BAYAT izin (artik kesfedilmiyor — sil ya da yolu duzelt): %s" % yol)

    # 4) bayat izin: hem izinde hem kosuluyor
    for yol in izin_listesi:
        if yol in kos:
            hatalar.append("BAYAT izin (test ARTIK KOSULUYOR — izinden cikar): %s" % yol)

    # 1) kapsamsiz: kesfedilmis ama ne kosuluyor ne izinli
    kapsamsiz = []
    for yol in kesif:
        if yol in kos:
            continue
        if yol in izin_listesi:
            continue
        kapsamsiz.append(yol)
    for yol in kapsamsiz:
        hatalar.append("KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % yol)

    # 5) kendi mutasyon nobetcileri — yalniz GERCEK deploy.yml'e karsi (mutant --deploy
    #    verildiginde pozitif kontrol anlamsiz olur, o yuzden atlanir) ve nobetcinin
    #    kendi ic cagrilarinda (ozyineleme) atlanir.
    if kontroller:
        _, mutasyon_hata = bulgu1_mutasyon_kontrol()
        for h in mutasyon_hata:
            hatalar.append("BULGU1-MUTASYON: " + h)
        _, muaf_hata = muaf_sayaci_kontrol()
        for h in muaf_hata:
            hatalar.append("MUAF-SAYACI: " + h)
        # ZINCIRIN SON HALKASI: oz-nobetci ADIMI deploy.yml'de duruyor mu. BURADA
        # (bayraksiz/bloklayici kolda) yasamak ZORUNDA — --kendini-test kolunda olsa,
        # adim silindiginde o kol kosmayacagi icin nobetci OLU olurdu.
        _, adim_hata = kendini_test_adimi_kontrol()
        for h in adim_hata:
            hatalar.append("KENDINI-TEST-ADIMI: " + h)

    # ---- rapor ----
    # FIX (27 Tem, olculdu): eski hal `[y for y in kesif if y not in kos]` idi -> etiket
    # "Muaf (izin listesi)" derken KAPSAMSIZ dosyalari da sayiyordu. Somut olcum:
    # tools/mimar-kapi-6ev-test.py kapsamsizken satir "Muaf: 71" yazdi; gercek muafiyet
    # eklenince (IZIN_LISTESI 70 -> 71) satir YINE "71" yazdi -> sayi muafiyet eklemesine
    # KOR, kapsamsiz dosya sessizce "muaf" etiketleniyordu. merge prosedürü bu sayiyi
    # ONCE/SONRA olcumu olarak rapor ettirdigi icin yanlis etiket olcumu bozuyordu.
    # (Kabul/ret semantigi DEGISMEDI: kapsamsiz tespiti yukarida, ayri ve aynen duruyor.)
    muaf = [y for y in kesif if y not in kos and y in izin_listesi]
    satirlar.append("CI KAPSAM KAPISI")
    satirlar.append("  Kesfedilen kabul testi : %d" % len(kesif))
    satirlar.append("  deploy.yml'de kosulan  : %d  (%s)" % (
        len(kos), ", ".join(sorted(kos)) or "-"))
    satirlar.append("  Muaf (izin listesi)    : %d" % len(muaf))
    satirlar.append("-" * 70)
    if hatalar:
        for h in hatalar:
            satirlar.append("  ❌ " + h)
        satirlar.append("-" * 70)
        satirlar.append("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1, satirlar
    satirlar.append("SONUC: YESIL ✅  — her kabul testi ya kosuluyor ya gerekceli muaf.")
    return 0, satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", default=DEPLOY_VARSAYILAN,
                    help="deploy.yml yolu (kirmizi-mutasyon icin alternatif kopya verilebilir)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YALNIZ kendi mutasyon nobetcilerini kosar: bulgu1 + muaf sayaci "
                         "(gercek deploy.yml uzerinden)")
    args = ap.parse_args()

    if args.kendini_test:
        ok1, hata1 = bulgu1_mutasyon_kontrol()
        print("BULGU 1 MUTASYON NOBETCISI")
        if ok1:
            print("  ✅ gercek deploy sayiyor; yalniz-yorum mutanti saymiyor")
        else:
            for h in hata1:
                print("  ❌ " + h)
        ok2, hata2 = muaf_sayaci_kontrol()
        print("MUAF SAYACI NOBETCISI")
        if ok2:
            print("  ✅ kapsamsiz dosya 'Muaf' sayilmiyor; muafiyet eklenince sayi 1 artiyor")
        else:
            for h in hata2:
                print("  ❌ " + h)
        # 3. nobetci BU KOLDA yalnizca RAPORLANIR — gercek kapisi bayraksiz kosumdadir
        # (bu adim silinirse bu kol CI'da hic kosmaz; bkz. kendini_test_adimi_kontrol).
        ok3, hata3 = kendini_test_adimi_kontrol()
        print("OZ-NOBETCI ADIMI NOBETCISI")
        if ok3:
            print("  ✅ deploy.yml'de yorum-olmayan bir icra govdesinin metninde `%s` "
                  "geciyor (bicim serbest; 'kosuyor+blokluyor' IDDIA EDILMEZ)"
                  % KENDINI_TEST_BAYRAGI)
        else:
            for h in hata3:
                print("  ❌ " + h)
        if ok1 and ok2 and ok3:
            print("SONUC: YESIL ✅")
            return 0
        print("SONUC: KIRMIZI ❌")
        return 1

    if not os.path.exists(args.deploy):
        sys.exit("deploy.yml bulunamadi: " + args.deploy)
    with open(args.deploy, encoding="utf-8") as f:
        deploy_metin = f.read()

    kod, satirlar = denetle(
        deploy_metin, kesfet(), IZIN_LISTESI,
        kontroller=os.path.abspath(args.deploy) == os.path.abspath(DEPLOY_VARSAYILAN))
    for satir in satirlar:
        print(satir)
    return kod


if __name__ == "__main__":
    sys.exit(main())
