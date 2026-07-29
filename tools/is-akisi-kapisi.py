#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/is-akisi-kapisi.py — IS AKISI BICIM KAPISI + iki-govde CAGRI NOBETI.

NEDEN VAR (29-30 Tem, GERCEK HASAR OLCULDU): deploy.yml'e eklenen bir adim ADI
TIRNAKSIZ yazildi ve icinde ": " (iki nokta + BOSLUK) tasiyordu:

    - name: Iki govde eslem kapisi (2-renk: -D farki yalniz Output)

YAML plain scalar'da bu bir AYRISTIRMA HATASIDIR. Sonuc: GitHub "workflow file issue"
deyip isi HIC baslatmadi -> kosum 0 saniyede `startup_failure`, is sayisi 0. Yani
`urun/` uretimi, sitemap, **butun kapilar** ve Pages yayini KOSMADI; ~7 dakika TUM
EKIBIN yayini durdu. Onarim: b7e9f845 (adi tirnaklandi), kosum 30492882992 SUCCESS.

🔴 HICBIR KAPI YAKALAMADI. Sebep: `tools/ci-kapsam-test.py` (ve `paket-tazelik-kapisi.py`)
is akisi dosyalarinda **METIN arar, YAML AYRISTIRMAZ** — yani "kapi var" sanilan yerde
bu sinif icin koruma YOKTU. Bu dosya o bosluga GERCEK bir ayristirici koyar.

ISLER (iki bolum, ayri eksenler):

  BOLUM A — BICIM: `.github/workflows/*.yml|*.yaml` altindaki TUM dosyalar GERCEK bir
    YAML ayristiricisiyla (PyYAML) ayristirilir. Ayristirma hatasi = KIRMIZI. Ek olarak
    `startup_failure` ureten BILINEN tuzaklar olculur:
      A1 ayristirma hatasi (tirnaksiz `": "`, kapanmamis tirnak, TAB, bozuk girinti...)
      A2 TEKRARLANAN ANAHTAR (PyYAML'in KENDISI bunu SESSIZCE yer: son deger kazanir;
         GitHub ise "workflow file issue" verir -> ozel Loader ile yakalanir)
      A3 govde yapisi: kok mapping · `on:` VAR · `jobs:` VAR + mapping + BOS DEGIL
      A4 job yapisi: mapping · (`runs-on` VEYA `uses`) · `steps` liste + bos degil
      A5 step yapisi: mapping · (`uses` VEYA `run`) · `run` BOS DEGIL

  BOLUM B — CAGRI NOBETI: `onizleme/test/iki-govde-olcum.py` GERCEKTEN kosuyor mu.
    Olculen delik (mimar, 30 Tem): bu testin `onizleme-imaj.yml`'deki cagri satiri
    NOBETSIZDI — cagriyi sil / yoruma al / `|| true` ekle -> DORT denetci de rc=0.
    `ci-kapsam-test.py` bu dosyayi "muaf" tutuyor ve muafiyet gerekcesi cagri satirinin
    "paket-tazelik-kapisi.py'nin imaj-akisi nobetiyle ayni dosyada durdugunu" soyluyordu;
    OLCULDU: paket-tazelik-kapisi.py'nin `CAGRI_CAPASI` sabiti YALNIZ KENDI cagri
    satirini ("tools/paket-tazelik-kapisi.py --paket") izliyor -> iddia YANLISTI.

KAPSAM GENISLETME TUZAGINDAN KACINMA ([[kapi-kapsam-genisletme-tuzagi]]): Bolum B
`ci-kapsam-test.py`'nin KURESEL `kosulan()` kapsamina onizleme-imaj.yml EKLEMEZ. Eklenseydi
`onizleme/test/iki-govde-olcum.py` + `duman_toka_kabul.py` bir anda "kosuluyor" sayilir,
kural 4 (BAYAT izin) yanar, muafiyetler soklurdu ve o dosyanin muaf SAYACI kayardi. Onun
yerine burada **DOSYA-BAZLI POZITIF nobetci** var: tek hedef, tek is akisi, tek iddia.
(Depoda olculmus kural: negatif kapsam kuresel, POZITIF kapsam SAYFA/DOSYA BAZLI olmali.)

🔴 KAPI KENDINI KILITLEMESIN — kapsam BILEREK DAR: A yalnizca is akisi dosyalarinin
AYRISTIRILABILIRLIGINE + GitHub'in ZORUNLU kildigi iskelete bakar. Bilinmeyen/yeni
GitHub anahtarlari, ifade (`${{ }}`) icerigi, kabuk sozdizimi, action surumleri, `if:`
mantigi DENETLENMEZ — hepsi yanlis-pozitif yuzeyidir ve bu kapi deploy.yml'de
continue-on-error'SUZ kosar (tek sahte-kirmizi TUM ekibin yayinini durdurur,
[[kapi-kapsam-eksen-secimi]]).

⚠️ CI'YA KOYMAK TEK BASINA YETMEZ: deploy.yml'in KENDISI bozulursa hicbir adim kosmaz —
bu kapi da kosmaz. CI'daki degeri (a) DIGER is akislarini (onizleme-imaj.yml) korumak,
(b) bozulmayi bir sonraki YESIL push'ta yakalamak. GERCEK koruma PUSH ONCESIDIR:
    python3 tools/is-akisi-kapisi.py
tek komut olarak kosar (ag YOK, dosya YAZMAZ, ~0,1 s). Onerilen .git/hooks/pre-push
satiri RAPOR-MIMARA.md'de (hook'lar bu depoda COMMIT EDILMEZ).

AYRISTIRICI YOKSA: `import yaml` basarisizsa kapi **YESIL SAYMAZ** -> exit 2 +
"OLCULEMEDI" basligi + yuksek sesli uyari (kurtarma: `pip install pyyaml`).

KENDINI TEST (BOLUM C — bayraksiz/BLOKLAYICI kolda da kosar): kapinin olcum govdeleri
SENTETIK bozuk/gecerli is akislarina karsi ARIZA ENJEKSIYONU ile sinanir. Govde no-op
yapilirsa (or. `return []`) sentetik-bozuk iddialari duser -> kapi KIRMIZI. Bu yuzden
nobetci `--kendini-test` KOLUNDA YASAMAZ (o adim silinirse kol hic kosmaz) — bayraksiz
kosumun icinden cagrilir; `--kendini-test` yalnizca AYRINTILI raporlar.

Kullanim:
    python3 tools/is-akisi-kapisi.py                  # bloklayici kapi (CI adimi)
    python3 tools/is-akisi-kapisi.py --kendini-test   # ariza-enjeksiyon raporu
    python3 tools/is-akisi-kapisi.py --dizin /gecici/mutant-workflows   # mutasyon olcumu

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI · 2 = OLCULEMEDI (ayristirici yok).
"""
import argparse
import collections.abc
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORKFLOW_DIZIN = os.path.join(ROOT, ".github", "workflows")

OLCULEMEDI = 2

# ---------------------------------------------------------------------------
# AYRISTIRICI — GERCEK YAML, taklit YOK ([[mimar-kapi-parser-taklidi]]).
# ---------------------------------------------------------------------------
try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - ortama bagli
    _yaml = None

AYRISTIRICI_YOK_TANI = (
    "🔴 OLCULEMEDI — PyYAML YOK, bu kapi HICBIR SEY olcemedi ve YESIL SAYILMADI.\n"
    "   is akisi dosyalari AYRISTIRILMADI: bugunku `startup_failure` sinifi (tirnaksiz\n"
    "   \": \" iceren adim adi) SU AN korunmasizdir.\n"
    "   KURTARMA: pip install pyyaml   (CI'da deploy.yml'in 'Python bagimliliklari' adimi)")


class TekrarlananAnahtar(Exception):
    """A2 — ayni mapping'de AYNI anahtar iki kez. PyYAML bunu sessizce yer (son deger
    kazanir), GitHub ise "workflow file issue" verir -> ozel olarak yakalanmasi SART."""

    def __init__(self, anahtar, ilk_mark, ikinci_mark):
        self.anahtar = anahtar
        self.ilk_satir = ilk_mark.line + 1
        self.ikinci_satir = ikinci_mark.line + 1
        super().__init__("tekrarlanan anahtar %r (satir %d ve %d)"
                         % (anahtar, self.ilk_satir, self.ikinci_satir))


def _loader_sinifi():
    """Tekrarlanan anahtari YAKALAYAN SafeLoader alt sinifi (PyYAML varsa)."""
    if _yaml is None:
        return None

    class TekrarKontrolluLoader(_yaml.SafeLoader):
        pass

    def _mapping(loader, node, deep=False):
        # ⚠️ TEKRAR DENETIMI flatten_mapping()'DEN ONCE, HAM node.value uzerinde yapilir.
        # Sebep: merge anahtari (`<<: *anchor`) YAML'da MESRUDUR ve flatten sonrasi
        # birlestirilen ciftler node.value'ya EKLENIR -> hem acikca yazilan hem miras
        # alinan bir anahtar iki kez gorunur ve SAHTE-KIRMIZI yanardi. Ham denetim
        # yalnizca ACIKCA IKI KEZ YAZILMIS anahtari yakalar (istenen tam olarak bu).
        gorulen = {}
        for anahtar_node, _deger in node.value:
            if anahtar_node.tag == "tag:yaml.org,2002:merge":
                continue
            try:
                anahtar = loader.construct_object(anahtar_node, deep=True)
            except Exception:
                continue  # anahtar cozulemiyorsa tekrar iddiasi kurulamaz -> sus
            if not isinstance(anahtar, collections.abc.Hashable):
                continue
            if anahtar in gorulen:
                raise TekrarlananAnahtar(anahtar, gorulen[anahtar], anahtar_node.start_mark)
            gorulen[anahtar] = anahtar_node.start_mark
        return _yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    TekrarKontrolluLoader.add_constructor("tag:yaml.org,2002:map", _mapping)
    return TekrarKontrolluLoader


def ayristir(metin):
    """(govde, hata_metni) — GERCEK ayristirma. Hata varsa govde None."""
    if _yaml is None:
        raise RuntimeError("PyYAML yok")
    loader = _loader_sinifi()
    try:
        return _yaml.load(metin, Loader=loader), None
    except TekrarlananAnahtar as e:
        return None, "TEKRARLANAN ANAHTAR: %s" % e
    except _yaml.YAMLError as e:
        # PyYAML tanisi satir/kolon + baglam tasir; ham haliyle basilir (en faydali mesaj).
        return None, "AYRISTIRMA HATASI: %s" % str(e).replace("\n", " | ")


# ---------------------------------------------------------------------------
# BOLUM A — BICIM OLCUMU
# ---------------------------------------------------------------------------
# YAML 1.1'de cikplak `on` anahtari BOOLEAN True'ya cozulur (PyYAML boyle yapar).
# GitHub `on:` yazimini kabul eder -> ikisi de gecerli sayilmali. `"on"` tirnakli
# yazim ise dize olarak gelir.
ON_ANAHTARLARI = (True, "on", "On", "ON")


def _on_var(govde):
    for a in ON_ANAHTARLARI:
        if a in govde:
            return True
    return False


def bicim_hatalari(yol, metin):
    """<yol> is akisi dosyasinin BICIM hatalarini (liste) dondur. Bos liste = temiz.

    Kapsam BILEREK DAR (kapi kendini kilitlemesin): yalnizca (1) ayristirilabilirlik,
    (2) tekrarlanan anahtar, (3) GitHub'in ZORUNLU iskeleti. Bilinmeyen anahtar,
    ifade icerigi, kabuk sozdizimi, action surumu DENETLENMEZ."""
    ad = os.path.basename(yol)
    govde, hata = ayristir(metin)
    if hata:
        return ["%s: %s" % (ad, hata)]

    hatalar = []
    if govde is None:
        return ["%s: dosya BOS ya da yalniz yorum -> GitHub is akisi olarak gecersiz" % ad]
    if not isinstance(govde, dict):
        return ["%s: kok govde mapping DEGIL (%s) -> gecersiz is akisi"
                % (ad, type(govde).__name__)]

    # A3 — zorunlu iskelet
    if not _on_var(govde):
        hatalar.append("%s: `on:` tetikleyicisi YOK -> GitHub is akisini baslatamaz" % ad)
    if "jobs" not in govde:
        hatalar.append("%s: `jobs:` YOK -> gecersiz is akisi" % ad)
        return hatalar
    jobs = govde["jobs"]
    if not isinstance(jobs, dict):
        hatalar.append("%s: `jobs:` mapping DEGIL (%s) -> gecersiz"
                       % (ad, type(jobs).__name__))
        return hatalar
    if not jobs:
        hatalar.append("%s: `jobs:` BOS -> hicbir is tanimli degil" % ad)
        return hatalar

    # A4/A5 — job + step iskeleti
    for job_id, job in jobs.items():
        etiket = "%s [job %s]" % (ad, job_id)
        if not isinstance(job, dict):
            hatalar.append("%s: job govdesi mapping DEGIL (%s)"
                           % (etiket, type(job).__name__))
            continue
        if "uses" in job:
            continue  # yeniden kullanilabilir is akisi cagrisi: runs-on/steps ISTEMEZ
        if "runs-on" not in job:
            hatalar.append("%s: `runs-on` YOK (ve `uses` de yok) -> is baslatilamaz" % etiket)
        if "steps" not in job:
            hatalar.append("%s: `steps` YOK" % etiket)
            continue
        steps = job["steps"]
        if not isinstance(steps, list):
            hatalar.append("%s: `steps` liste DEGIL (%s) -> girinti hatasi olabilir"
                           % (etiket, type(steps).__name__))
            continue
        if not steps:
            hatalar.append("%s: `steps` BOS liste" % etiket)
            continue
        for i, step in enumerate(steps, 1):
            s_etiket = "%s adim %d" % (etiket, i)
            if not isinstance(step, dict):
                hatalar.append("%s: adim mapping DEGIL (%s) -> girinti hatasi olabilir"
                               % (s_etiket, type(step).__name__))
                continue
            if "uses" not in step and "run" not in step:
                hatalar.append("%s (%r): ne `run` ne `uses` var -> gecersiz adim"
                               % (s_etiket, step.get("name", "")))
                continue
            if "run" in step:
                govde_run = step["run"]
                if govde_run is None or not isinstance(govde_run, str) \
                        or not govde_run.strip():
                    hatalar.append("%s (%r): `run:` BOS -> gecersiz adim"
                                   % (s_etiket, step.get("name", "")))
    return hatalar


def is_akisi_dosyalari(dizin):
    """<dizin> altindaki is akisi dosyalarini (tam yol, sirali) dondur."""
    if not os.path.isdir(dizin):
        return []
    return sorted(
        os.path.join(dizin, ad) for ad in os.listdir(dizin)
        if ad.endswith((".yml", ".yaml")) and os.path.isfile(os.path.join(dizin, ad)))


def bolum_a(dizin):
    """(hatalar, olculen_dosya_sayisi)."""
    dosyalar = is_akisi_dosyalari(dizin)
    if not dosyalar:
        return ["is akisi dizininde HIC .yml/.yaml yok: %s -> olculecek sey bulunamadi "
                "(dizin yolu degistiyse kapiyi guncelle)" % dizin], 0
    hatalar = []
    for yol in dosyalar:
        with open(yol, encoding="utf-8") as f:
            hatalar.extend(bicim_hatalari(yol, f.read()))
    return hatalar, len(dosyalar)


# ---------------------------------------------------------------------------
# BOLUM B — iki-govde CAGRI NOBETI
# ---------------------------------------------------------------------------
B_HEDEF = "onizleme/test/iki-govde-olcum.py"
B_IS_AKISI = "onizleme-imaj.yml"

# Cagri capasi: komut satiri `python3 <hedef>` ile BASLAR. Negatif ileri-bakis
# (?![\w./-]) uzun bir baska yolun on-eki olarak yanlis eslesmeyi engeller, ama
# `<hedef> --url ...` biciminde BAYRAKLI cagriyi DOGRU eslestirir
# (ci-kapsam-test.py `_onek_re` ile ayni desen).
B_ONEK = re.compile(r"^python3\s+" + re.escape(B_HEDEF) + r"(?![\w./-])")
# Etkisizlestirme: kabuk duzeyinde cikis kodunu yutan formlar.
# ⚠️ SON EK `\b` DEGIL (olculdu, bu kapinin KENDI ariza kaydi): `\b` bir KELIME karakteri
# komsulugu ister -> satir sonundaki `|| :` HIC eslesmiyordu ve `|| :` mutasyonu kapidan
# YESIL geciyordu (nobetci o bicimde OLU). Negatif ileri-bakis `(?![\w./-])` hem satir
# sonunu hem `;`/bosluk komsulugunu kapsar, `|| true2` gibi baska komutu ise eslestirmez.
B_ETKISIZ = re.compile(r"\|\|\s*(?:true|/bin/true|:)(?![\w./-])")


def _dogru_mu(deger):
    """YAML'da `true` bool gelir; `"true"` dize gelir — ikisi de GitHub icin dogrudur."""
    if isinstance(deger, bool):
        return deger
    if isinstance(deger, str):
        return deger.strip().lower() == "true"
    return False


def _yanlis_mu(deger):
    """YALNIZ HARFI HARFINE `false` (bool ya da dize). `${{ ... }}` ifadeleri
    DEGERLENDIRILMEZ — ifade taklidi yapmak sahte-kirmizi yuzeyidir."""
    if isinstance(deger, bool):
        return not deger
    if isinstance(deger, str):
        return deger.strip().lower() == "false"
    return False


def etkili_cagrilar(metin):
    """<metin> (bir is akisi dosyasinin TAM metni) icinde B_HEDEF'i FIILEN kosan
    (etkili) cagrilari dondur: [(job_id, adim_no, komut_satiri), ...].

    ETKILI DEGIL sayilan haller (mimarin istedigi 3 mutasyon + iki komsu):
      * cagri satiri SILINDI                     -> hic eslesme yok
      * cagri satiri YORUMA alindi (`# python3 ...`) -> satir suzulur
      * satirda `|| true` / `|| :` var            -> cikis kodu yutulur
      * adimda (ya da job'da) `continue-on-error: true`
      * adimda (ya da job'da) `if:` HARFI HARFINE `false`
    Ayristirma GERCEK YAML uzerinden yapilir (adim/job sinirlari TAHMIN EDILMEZ);
    `run: |` blogunun ICINDEKI kabuk yorumlari satir bazinda suzulur."""
    govde, hata = ayristir(metin)
    if hata or not isinstance(govde, dict):
        return []
    jobs = govde.get("jobs")
    if not isinstance(jobs, dict):
        return []
    bulunan = []
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if _dogru_mu(job.get("continue-on-error")) or _yanlis_mu(job.get("if")):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for i, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                continue
            if _dogru_mu(step.get("continue-on-error")) or _yanlis_mu(step.get("if")):
                continue
            run = step.get("run")
            if not isinstance(run, str):
                continue
            for ham in run.splitlines():
                s = ham.strip()
                if not s or s.startswith("#"):
                    continue  # kabuk yorumu -> ICRA DEGIL
                if not B_ONEK.match(s):
                    continue
                if B_ETKISIZ.search(s):
                    continue  # `|| true` cikis kodunu yutar -> nobetci OLU
                bulunan.append((job_id, i, s))
    return bulunan


B_TANI = (
    "CAGRI NOBETI KIRMIZI: %s dosyasinda `python3 %s` ETKILI olarak kosmuyor.\n"
    "   Etkisiz sayilan haller: satir SILINMIS · YORUMA alinmis (`# python3 ...`) ·\n"
    "   `|| true` / `|| :` eklenmis · adim/job'da `continue-on-error: true` ya da\n"
    "   `if: false` var.\n"
    "   NEDEN BLOKLAYICI: bu olcum 2-renk (iki govde) GEOMETRISINI openscad ile GERCEKTEN\n"
    "   olcen tek nobetci. Cagri etkisizlesirse musteri yazisi STL'e islenmeden teslim\n"
    "   edilebilir ve HICBIR kapi konusmaz (30 Tem olcumu: 4 denetci de rc=0).\n"
    "   GERI KOY: `%s` adiminin `run:` blogunda `python3 %s --url http://127.0.0.1:18080`."
) % (B_IS_AKISI, B_HEDEF, "Imaj duman testi", B_HEDEF)


OZ_CAGRI_TANI = (
    "OZ-CAGRI NOBETI KIRMIZI: bu dosyanin main() govdesinde `kendini_test()` cagrisinin "
    "SONUCU bir atamaya baglanmiyor -> BOLUM C (ariza enjeksiyonu) bloklayici kolda "
    "kosmuyor demektir ve kapinin olcum govdeleri sessizce no-op yapilabilir.\n"
    "   OLCULDU (30 Tem, bu kapinin KENDI mutasyon turu): `c_hata, c_iddia = kendini_test()` "
    "satiri silinince 7 govde mutasyonundan 6'si yakalanmaya devam ediyor ama BU biri "
    "KACIYORDU (hem --kendini-test hem bloklayici kol rc=0).\n"
    "   GERI KOY: main() icinde `c_hata, c_iddia = kendini_test()` (atama SART; sonucu "
    "atilan cikplak cagri sayilmaz).")


def oz_cagri_kontrol():
    """OZ-CAGRI NOBETI — main() BLOKLAYICI kolunda kendini_test() GERCEKTEN cagriliyor mu.

    YONTEM: AST (metin capasi DEGIL). Kendi kaynagini ayristirir, `main` fonksiyonunu bulur
    ve govdesinde degeri `kendini_test(...)` cagrisi olan bir ATAMA arar. Atama sarti
    bilincli: sonucu atilan cikplak bir cagri hatalari toplamaya girmez, yani nobetci yine
    olur. AST secildi cunku metin capasi (satiri harfiyen aramak) bu dosyanin kendi
    bicimlendirmesine kilitlenir ve mesru bir yeniden-adlandirmada sahte-kirmizi yakar
    ([[kapi-anchor-coupling-ikilemi]]: anchor-BAGIMSIZ olcum tercih edilir).

    🔴 KABUL EDILEN SINIR (sonsuz geriye gidis burada KESILIR — ci-kapsam-test.py ile ayni
    beyan): BU fonksiyonun bolum_b()'den yapilan cagrisi kendi basina nobetsizdir. Yani
    "hem oz_cagri_kontrol() cagrisini hem kendini_test() cagrisini birden silen" IKI ADIMLI
    bir mutasyon kacar. Tek-adimli mutasyon kapsanir; ustu bir harness sorusudur
    (tools/nobetci-mutasyon-test.py sinifi)."""
    import ast
    kaynak_yol = os.path.abspath(__file__)
    try:
        with open(kaynak_yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return ["OZ-CAGRI NOBETI OLCULEMEDI: kendi kaynagi ayristirilamadi (%s)" % e]
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == "main"):
            continue
        for alt in ast.walk(dugum):
            if not isinstance(alt, ast.Assign):
                continue
            deger = alt.value
            if isinstance(deger, ast.Call) and isinstance(deger.func, ast.Name) \
                    and deger.func.id == "kendini_test":
                return []
        return [OZ_CAGRI_TANI]
    return ["OZ-CAGRI NOBETI OLCULEMEDI: main() fonksiyonu bulunamadi (dosya yeniden "
            "duzenlendiyse bu nobetciyi guncelle)"]


def bolum_b(dizin):
    """(hatalar, etkili_cagri_sayisi).

    Bolum B'nin semantigi "BIR CAGRI GERCEKTEN KOSUYOR MU" oldugu icin kapinin KENDI ic
    self-test cagrisi da BURADA olculur (oz_cagri_kontrol) — ayni sinif, ayni bolum."""
    yol = os.path.join(dizin, B_IS_AKISI)
    if not os.path.exists(yol):
        return ["CAGRI NOBETI: %s bulunamadi (%s) -> hedefin kostugu is akisi kalkmis, "
                "olcum yapilamadi (fail-closed KIRMIZI)" % (B_IS_AKISI, yol)], 0
    hedef_yol = os.path.join(ROOT, B_HEDEF)
    hatalar = list(oz_cagri_kontrol())
    if not os.path.exists(hedef_yol):
        hatalar.append("CAGRI NOBETI: hedef betik YOK (%s) -> nobetci bayat, hedef "
                       "yeniden adlandirildiysa B_HEDEF sabitini guncelle" % B_HEDEF)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    cagrilar = etkili_cagrilar(metin)
    if not cagrilar:
        hatalar.append(B_TANI)
    return hatalar, len(cagrilar)


# ---------------------------------------------------------------------------
# BOLUM C — KENDINI TEST (ARIZA ENJEKSIYONU; bayraksiz kolda BLOKLAYICI)
# ---------------------------------------------------------------------------
# Sentetik fikstur: GECERLI ama "alisilmadik" bir is akisi. Sentetik olmasi SART —
# gercek dosyalarin icerigi degistikce nobetci bayatlamasin.
GECERLI_ORNEK = """\
name: "Sentetik: gecerli is akisi"

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  UZUN: "deger"
  IKINCI: 3

jobs:
  temel: &ortak
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: "Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"
        if: ${{ github.ref == 'refs/heads/main' && !cancelled() }}
        env:
          COK: |
            satir1
            satir2
        run: |
          echo "cok satirli"
          python3 -c 'print(1)'
          echo bitti   # satir sonu yorumu
      - name: Katlanan blok
        run: >-
          echo tek
          satira
  klon:
    <<: *ortak
  matrisli:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest]
        surum: ["20", "22"]
    steps:
      - run: echo "${{ matrix.surum }}"
"""

# Mutasyon capasi: matrisli job'un TEK adimi (fikstur icinde biricik satir).
SON_ADIM = '      - run: echo "${{ matrix.surum }}"'

# Ariza enjeksiyonu fiksturleri: (ad, metin, beklenen_hata_alt_dizesi)
BOZUK_ORNEKLER = (
    # 1) BUGUNKU GERCEK OLAY: tirnaksiz adim adinda ": " -> plain scalar ayristirma hatasi.
    ("gercek olay — tirnaksiz adim adinda \": \"",
     GECERLI_ORNEK.replace(
         '      - name: "Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"',
         "      - name: Turkce + emoji: sicak ogun cigdem 🚀 (2-renk: -D)"),
     "AYRISTIRMA HATASI"),
    # 2) PyYAML'in KENDISI bunu sessizce yer -> ozel Loader olmasa YESIL gecerdi.
    ("tekrarlanan anahtar (`runs-on` iki kez)",
     GECERLI_ORNEK.replace("    runs-on: ubuntu-latest",
                           "    runs-on: ubuntu-latest\n    runs-on: ubuntu-22.04", 1),
     "TEKRARLANAN ANAHTAR"),
    ("bos `run:`", GECERLI_ORNEK.replace(SON_ADIM, "      - run:"), "`run:` BOS"),
    ("`on:` blogu yok",
     GECERLI_ORNEK.replace("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
                           ""),
     "`on:` tetikleyicisi YOK"),
    ("`jobs:` yok", GECERLI_ORNEK.split("jobs:")[0], "`jobs:` YOK"),
    # 6) GIRINTI: adim listesi bir seviye kaydirilinca blok mapping cakisir.
    ("girinti bozuk (adim tiresi kaydi)",
     GECERLI_ORNEK.replace("    steps:\n      - uses: actions/checkout@v4",
                           "    steps:\n      uses: actions/checkout@v4", 1),
     "AYRISTIRMA HATASI"),
    # 7) YAPISAL girinti: `steps` liste yerine skalar -> ayristirma GECER, iskelet BOZUK.
    ("`steps` liste degil (skalar)",
     GECERLI_ORNEK.replace("    steps:\n" + SON_ADIM + "\n", "    steps: bozuk\n"),
     "liste DEGIL"),
    # 8) Adimda ne `run` ne `uses` -> GitHub "workflow file issue".
    ("adimda ne `run` ne `uses`",
     GECERLI_ORNEK.replace(SON_ADIM, "      - name: bos adim"),
     "ne `run` ne `uses`"),
    # 9) TAB karakteri: YAML girintide TAB KABUL ETMEZ (klasik startup_failure).
    ("girintide TAB karakteri",
     GECERLI_ORNEK.replace("    runs-on: ${{ matrix.os }}",
                           "\truns-on: ${{ matrix.os }}", 1),
     "AYRISTIRMA HATASI"),
)

# B ekseni ariza enjeksiyonu: gercek cagri satiri uzerinde 3 etkisizlestirme.
B_ORNEK_CAGRI = "python3 " + B_HEDEF + " --url http://127.0.0.1:18080"
B_FIKSTUR = """\
name: "Sentetik cagri fiksturu"
on: workflow_dispatch
jobs:
  imaj:
    runs-on: ubuntu-latest
    steps:
      - name: Imaj duman testi
        run: |
          echo hazir
          %s
          docker stop x
""" % B_ORNEK_CAGRI

B_MUTANTLAR = (
    ("cagri SILINDI", B_FIKSTUR.replace("          %s\n" % B_ORNEK_CAGRI, "")),
    ("cagri YORUMA alindi", B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                                              "          # %s" % B_ORNEK_CAGRI)),
    ("cagriya `|| true` eklendi", B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                                                    "          %s || true" % B_ORNEK_CAGRI)),
    # `|| :` — kabugun "hicbir sey yap, 0 don" komutu. Bu bicim ILK YAZIMDA KACIYORDU
    # (B_ETKISIZ'de `\b` kullanilmisti); nobetci olarak KALIR ki geri gelmesin.
    ("cagriya `|| :` eklendi", B_FIKSTUR.replace("          %s" % B_ORNEK_CAGRI,
                                                 "          %s || :" % B_ORNEK_CAGRI)),
    ("job'a `continue-on-error: true`",
     B_FIKSTUR.replace("    runs-on: ubuntu-latest",
                       "    runs-on: ubuntu-latest\n    continue-on-error: true")),
    ("adima `continue-on-error: true`",
     B_FIKSTUR.replace("      - name: Imaj duman testi",
                       "      - name: Imaj duman testi\n        continue-on-error: true")),
)


def kendini_test():
    """(hatalar, calisan_iddia_sayisi) — kapinin OLCUM GOVDELERI gercekten olcuyor mu.

    GOVDE NO-OP OLURSA KIRMIZI: bicim_hatalari() `return []` yapilirsa 6 bozuk
    fiksturun HICBIRI hata uretmez -> 6 iddia birden duser. etkili_cagrilar()
    `return []` yapilirsa POZITIF iddia duser; `return [1]` gibi sabit donerse 4
    mutant iddiasi birden duser. Yani hem sessiz-yesil hem sabit-donus kapatilir."""
    hatalar = []
    iddia = 0

    # A-POZITIF: gecerli ama ALISILMADIK YAML (anchor/alias, matrix, `if:` ifadesi,
    # cok satirli `run: |`, katlanan `>-`, uzun `env:`, Turkce karakter, emoji,
    # satir sonu yorumu) YANMAMALI. Yanma = tum ekibin yayini durur.
    iddia += 1
    pozitif = bicim_hatalari("sentetik-gecerli.yml", GECERLI_ORNEK)
    if pozitif:
        hatalar.append("A-POZITIF YANDI (YANLIS-POZITIF): gecerli sentetik is akisi %d hata "
                       "uretti -> %s" % (len(pozitif), " ; ".join(pozitif)))

    # A-NEGATIF: her bozuk fikstur KIRMIZI olmali VE dogru taniyi vermeli.
    for ad, metin, beklenen in BOZUK_ORNEKLER:
        iddia += 1
        bulgu = bicim_hatalari("sentetik-bozuk.yml", metin)
        if not bulgu:
            hatalar.append("A-NEGATIF SESSIZ: %r mutasyonu hic hata uretmedi "
                           "(olcum govdesi no-op mu?)" % ad)
        elif not any(beklenen in h for h in bulgu):
            hatalar.append("A-NEGATIF TANI KAYDI: %r icin %r bekleniyordu, gelen: %s"
                           % (ad, beklenen, " ; ".join(bulgu)))

    # B-POZITIF: sentetik fiksturde cagri ETKILI sayilmali.
    iddia += 1
    if len(etkili_cagrilar(B_FIKSTUR)) != 1:
        hatalar.append("B-POZITIF BOZUK: sentetik fiksturde tam 1 etkili cagri bekleniyordu, "
                       "%d bulundu -> capa (B_ONEK) bozulmus"
                       % len(etkili_cagrilar(B_FIKSTUR)))

    # B-NEGATIF: 4 etkisizlestirme biciminin HEPSI 0 etkili cagri vermeli.
    for ad, metin in B_MUTANTLAR:
        iddia += 1
        n = len(etkili_cagrilar(metin))
        if n != 0:
            hatalar.append("B-NEGATIF SESSIZ: %r mutasyonundan sonra cagri HALA etkili "
                           "sayildi (%d) -> nobetci bu bicimde OLU" % (ad, n))
    return hatalar, iddia


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizin", default=WORKFLOW_DIZIN,
                    help="is akisi dizini (kirmizi-mutasyon icin gecici kopya verilebilir)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YALNIZ ariza-enjeksiyon nobetcilerini AYRINTILI raporlar "
                         "(bayraksiz kosumda da BLOKLAYICI olarak kosarlar)")
    args = ap.parse_args()

    if _yaml is None:
        print("IS AKISI BICIM KAPISI")
        print(AYRISTIRICI_YOK_TANI)
        print("SONUC: OLCULEMEDI ⚪ (YESIL DEGIL)")
        return OLCULEMEDI

    # 🔴 TEK CAGRI NOKTASI (bilincli, olculdu 30 Tem): kendini_test() main() icinde
    # YALNIZ BURADA cagrilir ve iki kol da bu sonucu kullanir. Eskiden iki ayri cagri
    # vardi ve oz_cagri_kontrol() (AST) `--kendini-test` kolundaki cagriyi gorup tatmin
    # oluyordu -> BLOKLAYICI koldaki cagri silinse bile nobetci SUSUYORDU (olculdu: M7
    # mutasyonu iki kolda da rc=0). Tek cagri noktasi bu delige yer BIRAKMAZ.
    c_hata, c_iddia = kendini_test()

    if args.kendini_test:
        print("IS AKISI KAPISI — ARIZA ENJEKSIYONU (%d iddia)" % c_iddia)
        print("  PyYAML %s" % _yaml.__version__)
        if c_hata:
            for h in c_hata:
                print("  ❌ " + h)
            print("SONUC: KIRMIZI ❌")
            return 1
        print("  ✅ A-POZITIF: gecerli/alisilmadik YAML yanmiyor (anchor/alias, matrix, "
              "`if:`, `run: |`, `>-`, uzun env, Turkce, emoji)")
        print("  ✅ A-NEGATIF: %d bozuk fikstur KIRMIZI + tani dogru" % len(BOZUK_ORNEKLER))
        print("  ✅ B-POZITIF: sentetik cagri etkili sayiliyor")
        print("  ✅ B-NEGATIF: %d etkisizlestirme biciminde cagri OLU sayiliyor"
              % len(B_MUTANTLAR))
        print("SONUC: YESIL ✅")
        return 0

    hatalar = []
    a_hata, dosya_sayisi = bolum_a(args.dizin)
    hatalar.extend(a_hata)
    b_hata, cagri_sayisi = bolum_b(args.dizin)
    hatalar.extend(b_hata)

    # BOLUM C bayraksiz (bloklayici) kolda da BLOKLAR — `--kendini-test` adimi silinse
    # bile nobetci yasar (ci-kapsam-test.py'nin 27 Tem'de olctugu delik).
    for h in c_hata:
        hatalar.append("KENDINI-TEST: " + h)

    print("IS AKISI BICIM KAPISI")
    print("  Ayristirici              : PyYAML %s" % _yaml.__version__)
    print("  Ayristirilan is akisi    : %d  (%s)" % (
        dosya_sayisi,
        ", ".join(os.path.basename(y) for y in is_akisi_dosyalari(args.dizin)) or "-"))
    print("  Etkili iki-govde cagrisi : %d  (%s)" % (cagri_sayisi, B_IS_AKISI))
    print("  Kendini-test iddiasi     : %d" % c_iddia)
    print("-" * 70)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("-" * 70)
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(hatalar))
        return 1
    print("SONUC: YESIL ✅  — tum is akislari ayristirilabilir + iki-govde cagrisi etkili.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
