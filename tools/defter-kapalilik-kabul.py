#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-kapalilik-kabul.py — K267 KABUL BATARYASI.

OLCTUGU HUKUM (mimar, 24 Agu 2026):
  1. KAPALILIK YUKLEMI HALDEN OKUNUR, JETONDAN DEGIL. Kalem basliginda
     kapanis hali varsa satir bayat 🔴/🔧 jetonu tasisa BILE KAPALI sayilir.
  2. UCUNCU KOVA KORUNUR: `SINIFLANAMAZ` yutulmaz, SAYISI BASILIR, fail-closed.
  3. ORTAK SATIR: kapali kalem ACIK kalemlerle ayni satirdaysa ve tek basina
     cikarilamiyorsa madde `SINIFLANAMAZ`a duser ve SEBEP ADIYLA basilir.
  4. ACIK KALEM ASLA TASINMAZ.

YAPISI
  * ATOMIK vakalar (V1..V8): tek maddenin KOVASI + TASINIR mi. Mutant
    ATFI YALNIZ bu kume uzerinden yapilir — bilesik vakalar (rotasyon, 1:1,
    idempotens, canli negatif kontrol) bir mutant altinda TOPLU kayar ve
    hedef-kol atfini golgeler ([[ad-iki-rolde-mutanti-golgeler]]).
  * BILESIK vakalar (B1..B5): fikstur defteri uzerinde gercek rotasyon —
    kova dagilimi, ORTAK SATIR sebebinin BASILDIGI, 1:1 kayipsizlik (satir +
    bayt), idempotens (sha256), canli defter kopyasinda NEGATIF KONTROL.
  * MUTANTLAR: her biri HEDEF vaka kumesini ADIYLA beyan eder; olcut
    "kirmizi yandi" DEGIL **`olen == hedef`** kume esitligidir (K182).
    KONTROL mutanti ilgisiz bir kolu bozar ve batarya YESIL kalmalidir.
  * CAPA BAYATLIGI COKME DEGIL KAYITTIR ([[capa-cokmesi-arkasindaki-capalari-gizler]]):
    bulunamayan/tekil olmayan capa `BAYAT_CAPALAR`a yazilir, kalan mutantlar
    yine olculur, rc yine 1 olur.

KULLANIM
    python3 tools/defter-kapalilik-kabul.py [--rapor <yol>]

CIKTI (son satirlar)
    ATOMIK=<g>/<t> BILESIK=<g>/<t> MUTANT=<g>/<t> BAYAT_CAPA=<n>
    DUSEN=<n>
rc = 0 (DUSEN=0 ve BAYAT_CAPA=0) / 1 (aksi)
"""
import argparse
import collections
import hashlib
import importlib.util as _ilu
import os
import shutil
import subprocess
import sys
import tempfile

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_DEPO = os.path.dirname(_TOOLS)
_ROTASYON = os.path.join(_TOOLS, "defter-rotasyon.py")
_KOTA_TABAN = os.path.join(_TOOLS, "defter-kota-taban.py")
_CANLI_DEFTER = os.path.join(_DEPO, "DEVAM.md")
_CANLI_ARSIV = os.path.join(_DEPO, "DEVAM-ARSIV.md")

BAYAT_CAPALAR = []


def _yukle(yol, ad="rot"):
    spec = _ilu.spec_from_file_location(ad, yol)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rot = _yukle(_ROTASYON)


# =========================================================================
# ATOMIK VAKALAR — (ad, madde metni, beklenen kova, beklenen tasinir_mi)
# Fiksturler CANLI defterin GERCEK yazim bicimlerinden turetildi; ikinci
# sigorta tasiyan bicimler KASITLA sadelestirildi (V3'te `ARSIVDE` kelimesi
# YOK ki ortak-satir kolu TEK BELIRLEYICI olsun).
# =========================================================================
ATOMIK = [
    # KOL-1: HAL kalem BASLIGINDAN okunur (canli bicim: `- **K254 KAPANDI** ...`)
    ("V1-hal-baslikta",
     "- **K254 KAPANDI** canli 7/7 R2 7/7=200 deploy 7d7dbd2a",
     "KAPALI", True),
    # KOL-2: HAL > JETON — basliktan ONCE duran bayat acik jeton VETO ETMEZ
    ("V2-hal-jetonu-yener",
     "- \U0001F534 **K261 KAPANDI (YAYINI DURDURUR):** pre-push rc=4 kolu iki\n"
     "  yonlu olculdu; tek kaynak baglandi.",
     "KAPALI", True),
    # KOL-3: ORTAK SATIR — basliktan SONRA acik jeton => fail-closed + SEBEP
    ("V3-ortak-satir",
     "- ✅ **19 Agu KAPANANLAR: liste hazir.** **KALAN ACIK ARTIKLAR:** T3\n"
     "  sahipsiz sayimi K188 kancasi BAGLI DEGIL.",
     "SINIFLANAMAZ", False),
    # YASAK 4: acik kalem ASLA tasinmaz
    ("V4-acik-kalem",
     "- \U0001F527 **K233:** batarya beklenen kumeleri ELLE tasiniyor (SINIF).",
     "ACIK", False),
    # HUKUM 2: ucuncu kova YUTULMAZ (ne acik ne kapali jeton)
    ("V5-siniflanamaz",
     "- **K999** kimlik var, hicbir jeton yok",
     "SINIFLANAMAZ", False),
    # ARSIV_ISARETCISI kovasi KORUNUR (arsive isaret eden ozet satiri)
    ("V6-arsiv-isaretcisi",
     "- ✅ **24 Agu KAPANANLAR: K243 (tam metin ARSIVDE)** — 5/9 tasindi",
     "ARSIV_ISARETCISI", False),
    # K128: DEVAM satirindaki kapanis atfi TASIMA GEREKCESI OLAMAZ
    ("V7-k128-devam-satiri",
     "- \U0001F527 **K900:** eski yedek klasoru duruyor\n"
     "  (Motor tarifesi kalemi 20 Agu KAPANDI: ayri kalem.)",
     "ACIK", False),
    # K128 ikinci yuz: ILK SATIRDA ama BASLIK DISINDA parantezli kapanis atfi
    # (canli K247 satirinin birebir sekli)
    ("V8-k128-baslik-disi",
     "- \U0001F527 **K901:** kabul listesi ile CI kapsami ayrisiyor. "
     "(K243 KAPANDI `951059fa`.) Tam metinler KUTUDA.",
     "ACIK", False),
    # KOL-3b: BASLIK yalniz BASTAKI bold cifttir. Satirin ortasindaki bold
    # (baska bir kalemin basligi) BASLIK SAYILIRSA acik jeton basligin ICINE
    # duser ve ortak-satir kolu KORLESIR — ACIK X6 arsive supurulur.
    ("V9-baslik-bastaki-bold",
     "- ✅ KAPANDI: X5 listesi — kalan \U0001F7E0 **X6 K904** durmali.",
     "SINIFLANAMAZ", False),
]

ATOMIK_ADLAR = [a[0] for a in ATOMIK]


def _atomik_olc(modul):
    """Verilen rotasyon modulu ile ATOMIK vakalari olcer.
    Donus: {vaka_adi: (gecti_mi, gorulen_kova, gorulen_tasinir)}"""
    sonuc = {}
    for ad, metin, bek_kova, bek_tasinir in ATOMIK:
        try:
            kova = modul._madde_sinifi(metin)
            tasinir = bool(modul._madde_tasinir_mi(metin))
        except Exception as e:                       # mutant cokerse VAKA DUSER
            sonuc[ad] = (False, "COKTU:%s" % type(e).__name__, None)
            continue
        sonuc[ad] = (kova == bek_kova and tasinir == bek_tasinir, kova, tasinir)
    return sonuc


# =========================================================================
# FIKSTUR DEFTERI — bilesik vakalar icin
# =========================================================================
def _fikstur_defter():
    satirlar = [
        "# DEVAM (fikstur) — K267",
        "",
        "> Kapanmis islerin TAM metni arsivde.",
        "",
        "## ACIK KALEMLER (kapsayici)",
    ]
    for _ad, metin, _k, _t in ATOMIK:
        satirlar.extend(metin.split("\n"))
        satirlar.append("")
    return "\n".join(satirlar) + "\n"


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _bayt(yol):
    return os.path.getsize(yol) if os.path.exists(yol) else 0


def _satir(yol):
    if not os.path.exists(yol):
        return 0
    with open(yol, "rb") as f:
        return len(f.read().splitlines())


def _rotasyon_kos(defter, arsiv):
    r = subprocess.run([sys.executable, _ROTASYON, defter, arsiv,
                        "--tarih", "2026-08-24"],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def _kova_oku(cikti):
    for satir in cikti.splitlines():
        if satir.startswith("MADDE_KOVALARI "):
            d = {}
            for parca in satir.split()[1:]:
                k, _, v = parca.partition("=")
                d[k] = int(v)
            return d
    return {}


def _bilesik_vakalar(sonuclar):
    """B1..B5 — fikstur rotasyonu + canli defter kopyasinda negatif kontrol."""
    calisma = tempfile.mkdtemp(prefix="k267-kabul-")
    try:
        defter = os.path.join(calisma, "DEVAM.md")
        arsiv = os.path.join(calisma, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(_fikstur_defter())
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("# ARSIV (fikstur)\n")

        d_bayt0, a_bayt0 = _bayt(defter), _bayt(arsiv)
        d_satir0, a_satir0 = _satir(defter), _satir(arsiv)
        rc, cikti = _rotasyon_kos(defter, arsiv)
        kova = _kova_oku(cikti)
        d_bayt1, a_bayt1 = _bayt(defter), _bayt(arsiv)
        d_satir1, a_satir1 = _satir(defter), _satir(arsiv)

        # ---- B1: KAPALI kovasi > 0 ve TASINAN_MADDE > 0 -------------------
        tasinan = 0
        for s in cikti.splitlines():
            if s.startswith("TASINAN="):
                for parca in s.split():
                    if parca.startswith("TASINAN_MADDE="):
                        tasinan = int(parca.split("=")[1])
        sonuclar.append((
            "B1-kapali-kovasi-dolu",
            rc == 0 and kova.get("KAPALI", 0) == 2 and tasinan == 2,
            "rc=%d KAPALI=%s TASINAN_MADDE=%d (2/2 beklenir: V1+V2)"
            % (rc, kova.get("KAPALI"), tasinan)))

        # ---- B2: kova dagilimi TAM (ucuncu kova yutulmadi) -----------------
        beklenen_kova = {"ACIK": 3, "ARSIV_ISARETCISI": 1, "KAPALI": 2,
                         "SINIFLANAMAZ": 3, "TUTARSIZ": 0, "INCELENEN": 9}
        kova_tam = all(kova.get(k) == v for k, v in beklenen_kova.items())
        sonuclar.append((
            "B2-kova-dagilimi",
            kova_tam,
            "gorulen=%s beklenen=%s" % (
                {k: kova.get(k) for k in beklenen_kova}, beklenen_kova)))

        # ---- B3: ORTAK SATIR sebebi ADIYLA basildi -------------------------
        sebep_basildi = any(
            s.startswith("TASINMADI-MADDE (SINIFLANAMAZ)")
            and "SEBEP: ortak satir:" in s
            for s in cikti.splitlines())
        sonuclar.append((
            "B3-ortak-satir-sebebi-basildi", sebep_basildi,
            "TASINMADI-MADDE + 'SEBEP: ortak satir:' satiri %s"
            % ("VAR" if sebep_basildi else "YOK")))

        # ---- B4: 1:1 KAYIPSIZLIK — satir ekseni + bayt ekseni --------------
        # 🔴 "dusen = giren" ARSIVIN MUHASEBE SATIRLARI DUSULEREK okunur:
        # arsiv her rotasyonda bir `## <tarih> — ROTASYON: ...` ayiraci ve
        # ayirac bos satirlarini da kazanir (aracin kendi `arsiv_muhasebe`
        # sayaci tam bunu olcer). Ham `arsiv+n`i tasinan icerige esitlemek
        # YANLIS bir olcuttur — ilk turda tam bu yuzden kirmizi yandi.
        lossless = "LOSSLESS=EVET" in cikti
        cift = [s for s in cikti.splitlines() if s.startswith("ROTASYON_CIFTI")]
        c = {}
        if cift:
            for parca in cift[0].split()[1:]:
                k, _, v = parca.partition("=")
                c[k] = v
        d_dusen_satir = d_satir0 - d_satir1
        a_giren_satir = a_satir1 - a_satir0
        d_dusen_bayt = d_bayt0 - d_bayt1
        a_giren_bayt = a_bayt1 - a_bayt0
        with open(defter, encoding="utf-8") as f:
            defter_son = f.read()
        with open(arsiv, encoding="utf-8") as f:
            arsiv_son = f.read()
        tasinan_metinler = [ATOMIK[0][1], ATOMIK[1][1]]
        # bayt ekseninin BEKLENEN degeri fikstur metninden TURETILIR
        beklenen_bayt = sum(len((t + "\n").encode("utf-8"))
                            for t in tasinan_metinler)
        muhasebe_satir = int(c.get("arsiv_muhasebe", "-1"))
        arsivde_var = all(t in arsiv_son for t in tasinan_metinler)
        defterde_yok = all(t not in defter_son for t in tasinan_metinler)
        satir_ekseni = (d_dusen_satir == int(c.get("defter_dusen", "-1"))
                        == int(c.get("tasinan_icerik", "-2"))
                        == a_giren_satir - muhasebe_satir)
        bayt_ekseni = (d_dusen_bayt == beklenen_bayt
                       and a_giren_bayt >= d_dusen_bayt)
        temiz = (c.get("kayip") == "0" and c.get("fazla_dusen") == "0"
                 and c.get("uydurulan") == "0")
        sonuclar.append((
            "B4-kayipsizlik-iki-eksen",
            lossless and temiz and satir_ekseni and bayt_ekseni
            and arsivde_var and defterde_yok,
            "%s | SATIR defter-%d arsiv+%d muhasebe=%d net_giren=%d | "
            "BAYT defter-%d beklenen-%d arsiv+%d | arsivde_birebir=%s "
            "defterde_yok=%s"
            % (cift[0] if cift else "ROTASYON_CIFTI YOK",
               d_dusen_satir, a_giren_satir, muhasebe_satir,
               a_giren_satir - muhasebe_satir,
               d_dusen_bayt, beklenen_bayt, a_giren_bayt,
               arsivde_var, defterde_yok)))

        # ---- B5: IDEMPOTENS — ikinci kosum dosyalari DEGISTIRMEZ ----------
        d_sha1, a_sha1 = _sha(defter), _sha(arsiv)
        rc2, cikti2 = _rotasyon_kos(defter, arsiv)
        d_sha2, a_sha2 = _sha(defter), _sha(arsiv)
        ikinci_tasinan = "TASINAN=0 TASINAN_MADDE=0" in cikti2
        sonuclar.append((
            "B5-idempotens",
            rc2 == 0 and ikinci_tasinan and d_sha1 == d_sha2 and a_sha1 == a_sha2,
            "rc=%d TASINAN=0 %s defter_sha %s arsiv_sha %s"
            % (rc2, ikinci_tasinan,
               "AYNI" if d_sha1 == d_sha2 else "DEGISTI",
               "AYNI" if a_sha1 == a_sha2 else "DEGISTI")))
    finally:
        shutil.rmtree(calisma, ignore_errors=True)


# 🔴 NEGATIF KONTROL — bu kimlikler ACIK; rotasyondan SONRA defterde KALMALI
# ve arsive GITMEMIS olmali.
ACIK_KALMASI_GEREKEN = ["K86", "K70", "K260", "K264", "K266", "K228", "K220",
                        "K206", "K184", "K222", "K256", "K255"]


def _canli_negatif_kontrol(sonuclar):
    """B6 — CANLI defterin KOPYASI uzerinde rotasyon: 12 acik kimlik defterde
    KALIR ve arsive GIRMEZ. Canli dosyalara DOKUNULMAZ."""
    if not os.path.exists(_CANLI_DEFTER):
        sonuclar.append(("B6-canli-negatif-kontrol", False,
                         "OLCULEMEDI: %s yok" % _CANLI_DEFTER))
        return
    calisma = tempfile.mkdtemp(prefix="k267-canli-")
    try:
        defter = os.path.join(calisma, "DEVAM.md")
        arsiv = os.path.join(calisma, "DEVAM-ARSIV.md")
        shutil.copy(_CANLI_DEFTER, defter)
        if os.path.exists(_CANLI_ARSIV):
            shutil.copy(_CANLI_ARSIV, arsiv)
        else:
            with open(arsiv, "w", encoding="utf-8") as f:
                f.write("")
        with open(arsiv, encoding="utf-8") as f:
            arsiv_once = f.read()
        with open(defter, encoding="utf-8") as f:
            defter_once = f.read()
        rc, cikti = _rotasyon_kos(defter, arsiv)
        with open(defter, encoding="utf-8") as f:
            defter_son = f.read()
        with open(arsiv, encoding="utf-8") as f:
            arsiv_son = f.read()
        yeni_arsiv = arsiv_son[:len(arsiv_son) - len(arsiv_once)]
        # 🔴 KIMLIK LISTESI DEFTERDEN BUYUK OLABILIR: mimarin verdigi 12
        # kimligin bir kismi bugunku DEFTERDE HIC YOK (baska sicilde acik).
        # "Yoktu" ile "tasindi" AYNI SEY DEGILDIR — ikisi ayri kovada SAYILIR
        # ve ADIYLA basilir; yok olani sessizce "gecti" saymak da, "dustu"
        # saymak da olcumu yalanlar.
        vardi = [k for k in ACIK_KALMASI_GEREKEN if k in defter_once]
        yoktu = [k for k in ACIK_KALMASI_GEREKEN if k not in defter_once]
        kayboldu = [k for k in vardi if k not in defter_son]
        sizan = [k for k in ACIK_KALMASI_GEREKEN if k in yeni_arsiv]
        kova = _kova_oku(cikti)
        sonuclar.append((
            "B6-canli-negatif-kontrol",
            rc == 0 and not kayboldu and not sizan,
            "rc=%d DEFTERDE_VARDI=%d/%d %s | DEFTERDE_YOKTU=%d %s | "
            "ROTASYONDA_KAYBOLAN=%s | ARSIVE_SIZAN=%s | kova=%s"
            % (rc, len(vardi), len(ACIK_KALMASI_GEREKEN), vardi,
               len(yoktu), yoktu, kayboldu or "YOK", sizan or "YOK",
               {k: kova.get(k) for k in
                ("INCELENEN", "ACIK", "ARSIV_ISARETCISI", "KAPALI",
                 "SINIFLANAMAZ", "TUTARSIZ")})))
    finally:
        shutil.rmtree(calisma, ignore_errors=True)


# =========================================================================
# MUTANTLAR — her biri HEDEF vaka kumesini beyan eder; olcut `olen == hedef`
# =========================================================================
MUTANTLAR = [
    {
        "ad": "M-A hal>jeton onceligi TERS",
        "capa": (
            "    if _ortak_satir_sebebi(metin) is not None:\n"
            "        return False\n"
            "    if not _kapanis_hali(metin):\n"
            "        return False\n"
            "    if _madde_arsiv_vetolu(metin):\n"
            "        return False\n"
            "    return True\n"),
        "yerine": (
            "    if _acik_eslesiyor(metin):   # M-A: eski JETON onceligi geri\n"
            "        return False\n"
            "    if _ortak_satir_sebebi(metin) is not None:\n"
            "        return False\n"
            "    if not _kapanis_hali(metin):\n"
            "        return False\n"
            "    if _madde_arsiv_vetolu(metin):\n"
            "        return False\n"
            "    return True\n"),
        "hedef": {"V2-hal-jetonu-yener"},
    },
    {
        "ad": "M-B SINIFLANAMAZ kovasi KAPALI'ya kaydirildi",
        "capa": (
            "        sinif = MADDE_ACIK if _acik_eslesiyor(metin) "
            "else MADDE_SINIFLANAMAZ\n"),
        "yerine": (
            "        sinif = MADDE_ACIK if _acik_eslesiyor(metin) "
            "else MADDE_KAPALI   # M-B: ucuncu kova YUTULDU\n"),
        "hedef": {"V5-siniflanamaz"},
    },
    {
        "ad": "M-C ORTAK SATIR korumasi KALDIRILDI",
        "capa": (
            "    if not _kapanis_hali(metin):\n"
            "        return None\n"
            "    ilk = _ilk_satir(metin)\n"),
        "yerine": (
            "    if True:   # M-C: ortak satir korumasi KALDIRILDI\n"
            "        return None\n"
            "    ilk = _ilk_satir(metin)\n"),
        "hedef": {"V3-ortak-satir", "V9-baslik-bastaki-bold"},
    },
    {
        "ad": "M-E BASLIK 'BASTAKI bold' sarti KALDIRILDI",
        "capa": (
            "    if any(c.isalnum() for c in s[:a]):"
            "        # bold BASTA DEGIL -> baslik YOK\n"
            "        return None, s\n"),
        "yerine": (
            "    if False:   # M-E: bastaki-bold sarti KALDIRILDI\n"
            "        return None, s\n"),
        "hedef": {"V9-baslik-bastaki-bold"},
    },
    {
        "ad": "M-D HAL kalem BASLIGINDAN okunmuyor",
        "capa": (
            "    baslik, _kalan = _kalem_basligi(ilk)\n"
            "    if baslik is None:\n"
            "        return False\n"
            "    return any(j in baslik for j in KAPANIS_ISARETCILER)\n"),
        "yerine": (
            "    return False   # M-D: HAL yalniz ILK TOKEN kolundan okunur\n"),
        "hedef": {"V1-hal-baslikta", "V2-hal-jetonu-yener"},
    },
    {
        "ad": "M-KONTROL ilgisiz kol (isaretciye indirme esigi)",
        "capa": "_ISARETCI_ASGARI_GOVDE = 3\n",
        "yerine": "_ISARETCI_ASGARI_GOVDE = 4\n",
        "hedef": set(),
    },
]


def _mutant_olc(mutant, sonuclar):
    with open(_ROTASYON, encoding="utf-8") as f:
        govde = f.read()
    sayi = govde.count(mutant["capa"])
    if sayi != 1:
        BAYAT_CAPALAR.append("%s — capa bayat (sayi=%d): %r"
                             % (mutant["ad"], sayi, mutant["capa"][:60]))
        sonuclar.append((mutant["ad"], False,
                         "CAPA BAYAT (sayi=%d) — mutant OLCULEMEDI" % sayi))
        return
    calisma = tempfile.mkdtemp(prefix="k267-mutant-")
    try:
        mut_yol = os.path.join(calisma, "defter-rotasyon.py")
        with open(mut_yol, "w", encoding="utf-8") as f:
            f.write(govde.replace(mutant["capa"], mutant["yerine"], 1))
        shutil.copy(_KOTA_TABAN, os.path.join(calisma, "defter-kota-taban.py"))
        try:
            mut = _yukle(mut_yol, "rot_mutant")
        except Exception as e:
            sonuclar.append((mutant["ad"], False,
                             "mutant YUKLENEMEDI: %s" % e))
            return
        gorulen = _atomik_olc(mut)
        olen = {ad for ad, (gecti, _k, _t) in gorulen.items() if not gecti}
        hedef = mutant["hedef"]
        sonuclar.append((
            mutant["ad"], olen == hedef,
            "olen=%s hedef=%s (kume ESITLIGI sart) | ayrinti=%s"
            % (sorted(olen) or "YOK", sorted(hedef) or "YOK",
               {ad: (gorulen[ad][1], gorulen[ad][2])
                for ad in sorted(olen | hedef)})))
    finally:
        shutil.rmtree(calisma, ignore_errors=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rapor", default=None,
                   help="ham ciktinin yazilacagi dosya (varsayilan: yalniz stdout)")
    a = p.parse_args(argv)

    satirlar = []

    def yaz(s):
        satirlar.append(s)
        print(s)

    yaz("K267 KABUL BATARYASI — arac=%s" % _ROTASYON)

    # ---- ATOMIK ---------------------------------------------------------
    atomik_sonuc = _atomik_olc(rot)
    atomik_gecen = 0
    for ad, metin, bek_kova, bek_tasinir in ATOMIK:
        gecti, kova, tasinir = atomik_sonuc[ad]
        atomik_gecen += 1 if gecti else 0
        yaz("  %s %-24s kova=%-17s tasinir=%-5s (beklenen kova=%s tasinir=%s)"
            % ("✓" if gecti else "✗", ad, kova, tasinir, bek_kova, bek_tasinir))

    # ---- BILESIK --------------------------------------------------------
    bilesik = []
    _bilesik_vakalar(bilesik)
    _canli_negatif_kontrol(bilesik)
    bilesik_gecen = 0
    for ad, gecti, detay in bilesik:
        bilesik_gecen += 1 if gecti else 0
        yaz("  %s %-28s %s" % ("✓" if gecti else "✗", ad, detay))

    # ---- MUTANT ---------------------------------------------------------
    mutant = []
    for m in MUTANTLAR:
        _mutant_olc(m, mutant)
    mutant_gecen = 0
    for ad, gecti, detay in mutant:
        mutant_gecen += 1 if gecti else 0
        yaz("  %s %-46s %s" % ("✓" if gecti else "✗", ad, detay))

    for b in BAYAT_CAPALAR:
        yaz("  BAYAT_CAPA: %s" % b)

    dusen = ((len(ATOMIK) - atomik_gecen) + (len(bilesik) - bilesik_gecen)
             + (len(mutant) - mutant_gecen))
    yaz("KAPSAM ATOMIK_VAKA=%d BILESIK_VAKA=%d MUTANT=%d KONTROL_MUTANT=1 "
        "NEGATIF_KIMLIK=%d"
        % (len(ATOMIK), len(bilesik), len(MUTANTLAR) - 1,
           len(ACIK_KALMASI_GEREKEN)))
    yaz("ATOMIK=%d/%d BILESIK=%d/%d MUTANT=%d/%d BAYAT_CAPA=%d"
        % (atomik_gecen, len(ATOMIK), bilesik_gecen, len(bilesik),
           mutant_gecen, len(mutant), len(BAYAT_CAPALAR)))
    yaz("DUSEN=%d" % dusen)

    if a.rapor:
        with open(a.rapor, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar) + "\n")

    return 0 if (dusen == 0 and not BAYAT_CAPALAR) else 1


if __name__ == "__main__":
    sys.exit(main())
