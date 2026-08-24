#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-tasima-birimi-test.py — K243 + K258 KABUL BATARYASI.

OLCULEN ARIZA (20 Agu 2026, KraL-KotaAcma teshisi):
  * K243 — kanonik rotasyon SEKIZ tur boyunca `TASINAN=0 TASINAN_MADDE=0`
    dondu. Sebep yetki/tavan/tarih DEGILDI: defterin KALICI BOLUM BASLIKLARI
    (`## ACIK KALEMLER`, `## KraL ACIK ARTIKLAR`, `## OKAN'DA`, `## ARSIVDE`)
    ayni zamanda ACIK jetonudur; blok yuklemi onlari KENDI icerikleri sanip
    blogu vetoluyordu. Basliklar KALEM degil KAPSAYICIDIR.
  * K258 — kota kapilarinin BASTIGI carenin kendisi mimarin komut kumesinde
    YASAKTI (`defter-rotasyon.py` her bayragi kesiyordu, `kutu-arsivle.py`
    kapida HIC gecmiyordu).

BU BATARYA NE OLCER:
  1. Kapsayici/kalem ayrimi (fail-closed SIKILASTIRMA — eskiden kapsayici
     TUMUYLE supurulebiliyordu).
  2. Acik kalem KAYBOLMAZ (negatif kontrol).
  3. Ucuncu kova (SINIFLANAMAZ) + dorduncu kova (ARSIV_ISARETCISI) GORUNUR
     ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
  4. Kapinin DEFTER BAKIMI kovasi: izinli bayrak GECER, kume DISI RED,
     kapinin geri kalan yasaklari (curl / sort / genel python) DURUYOR.

MUTANT DISIPLINI:
  * Her mutant iddiayi OLDURMELI **ve** HEDEF KOLUNU oldurdugunu AYRICA
    kanitlamali ([[ad-iki-rolde-mutanti-golgeler]], K182). "Kirmizi geldi"
    tek basina kanit DEGILDIR: ayni mutant altinda hedef-DISI vakanin
    DEGISMEDIGI de olculur.
  * KONTROL mutanti: ilgisiz kol bozulunca hedef vakalar YASAR (tautoloji yok).
  * CAPA SAGLIGI: capa bayatlarsa hukum sessiz "YASADI" degil `OLCULEMEDI`
    ([[capa-cokmesi-arkasindaki-capalari-gizler]]) ve rc != 0.
  * KIMLIK EKSENI SOKULUR: kapi probu ISCI kimliginde kosarsa kapi hicbir
    kural uygulamaz ve prob kendi baglamini olcer ([[prob-kendi-baglamini-olcer]]).
    Bu yuzden `PRUVO_ISCI_KOSUMU` / `PRUVO_CLAUDE_ISCI_IZNI` dusurulur VE
    sokumun gerceklestigi POZITIF KONTROLLE dogrulanir (bilinen-yasak komut
    RED gelmeli); dogrulanamazsa `MUAF_BAGLAM` basilir.

Cikis: 0 = hepsi gecti · 1 = en az bir vaka/mutant KIRMIZI ·
       2 = OLCULEMEDI (capa bayat / kimlik sokulemedi) — sessiz yesil YOK.
Son satir: KAPSAM VAKA=<n> MUTANT=<n> KONTROL=<n> KAPI=<n> KIRMIZI=<n> OLCULEMEDI=<n>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROTASYON = os.path.join(TOOLS, "defter-rotasyon.py")
KAPI = os.path.join(TOOLS, "mimar-icra-kapisi.py")
TABAN = os.path.join(TOOLS, "defter-kota-taban.py")
KIMLIK = os.path.join(TOOLS, "mimar_kimlik.py")

# Kapi TAM-YOL sabitleri ana checkout'a capalidir (REPO_ONEKI); prob komutlari
# da o yollari kullanir — yoksa kapi yolu tanimaz ve prob kendi kurgusunu olcer.
ANA = "/Users/okan/dev/pruvo"
CARE_DEFTER = ("python3 " + ANA + "/tools/defter-rotasyon.py "
               + ANA + "/DEVAM.md " + ANA + "/DEVAM-ARSIV.md "
               "--tavan-kaynaktan --isaretciye-indir")
KANONIK_BAYRAKSIZ = ("python3 " + ANA + "/tools/defter-rotasyon.py "
                     + ANA + "/DEVAM.md " + ANA + "/DEVAM-ARSIV.md")
CARE_KUTU = "python3 " + ANA + "/tools/kutu-arsivle.py --kuru"
YASAK_TAVAN_SAYI = ("python3 " + ANA + "/tools/defter-rotasyon.py "
                    + ANA + "/DEVAM.md " + ANA + "/DEVAM-ARSIV.md "
                    "--tavan-sayi 130")
YASAK_TARIH = ("python3 " + ANA + "/tools/defter-rotasyon.py "
               + ANA + "/DEVAM.md " + ANA + "/DEVAM-ARSIV.md "
               "--tarih 2026-08-20")
YASAK_ESITLIKLI = ("python3 " + ANA + "/tools/defter-rotasyon.py "
                   + ANA + "/DEVAM.md " + ANA + "/DEVAM-ARSIV.md "
                   "--tavan-sayi=130")
YASAK_KUTU_TAVAN = "python3 " + ANA + "/tools/kutu-arsivle.py --tavan 300"
YASAK_CURL = "curl -s https://example.com"
YASAK_SORT = "sort " + ANA + "/DEVAM.md"
YASAK_GENEL_PY = "python3 " + ANA + "/tools/defter-kota-kapisi.py"
SERBEST_DURUM = "python3 " + ANA + "/tools/durum.py"


# ---------------------------------------------------------------------------
# FIKSTURLER
# ---------------------------------------------------------------------------
# F1 — KAPSAYICI FAIL-OPEN: `## ARSIVDE` ACIK jetonu TASIMAZ ama govdesinde
# `KAPANDI` gecer. ESKI kod blogu TUMUYLE supururdu (sinifi belirsiz satir
# dahil). YENI kod: kapsayici BUTUN olarak tasinmaz, yalniz KAPALI maddesi iner.
F1 = (
    "# DEFTER\n"
    "\n"
    "## ARSIVDE\n"
    "- ✅ KAPANDI: eski indeks satiri.\n"
    "- Jetonsuz satir: sinifi belirsiz.\n"
)

# F2 — NEGATIF KONTROL: acik kalem ASLA arsive gitmez.
# 🔴 X5 KRITIK VAKA — GERCEK DEFTERDEN alinmis desen: BASI kapanis jetonu,
# GOVDESI acik artik ("- ✅ ... KAPANANLAR ... **KALAN ACIK ARTIKLAR:** ...").
# Madde ACIK vetosu kalkarsa YALNIZ bu madde supurulur ve icindeki acik artik
# (X6) KAYBOLUR — MUT-B'nin oldurdugu vaka budur. Bas jetonu 🔴/🔧 olan
# maddeler zaten `_ilk_satirda_kapanis` kolunda takilir, o yuzden veto kolunu
# ancak KARISIK madde olcer.
F2 = (
    "# DEFTER\n"
    "\n"
    "## ACIK KALEMLER\n"
    "- 🔴 **X1 K901:** durmali.\n"
    "- 🔧 **X2 K902:** durmali.\n"
    "- ✅ KAPANDI: X3 kapali kalem.\n"
    "- ✅ KAPANDI: X5 listesi — kalan 🟠 **X6 K904** durmali.\n"
    "\n"
    "## KraL ACIK ARTIKLAR\n"
    "- 🟠 **X4 K903:** durmali.\n"
)

# F3 — HEDEF-DISI VAKA: kapsayici OLMAYAN kapali blok BUTUN olarak tasinmaya
# devam eder. MUT-A altinda BU vaka DEGISMEMELI (hedef-kol atfi).
F3 = (
    "# DEFTER\n"
    "\n"
    "## KAPALI SERI ✅\n"
    "- ✅ KAPANDI: Y1.\n"
    "- ✅ KAPANDI: Y2.\n"
)

# F4 — UCUNCU + DORDUNCU KOVA gorunurlugu.
F4 = (
    "# DEFTER\n"
    "\n"
    "## OKAN'DA\n"
    "- Bir satir, jeton yok.\n"
    "- ✅ KAPANDI (arsivde): eski indeks.\n"
)


# ---------------------------------------------------------------------------
# KOSUM YARDIMCILARI
# ---------------------------------------------------------------------------
def _taban_kopyala(dizin):
    """Mutant, tavan TEK KAYNAGINI kendi dizininden yukler; yaninda olmali."""
    shutil.copy2(TABAN, os.path.join(dizin, os.path.basename(TABAN)))


def _kos_rotasyon(rotasyon_yol, defter_icerik, ek_argv=()):
    """Rotasyonu izole tmpdir'de kosar.

    Donus: dict(rc, cikti, hata, defter, arsiv)
    """
    with tempfile.TemporaryDirectory(prefix="k243-vaka-") as tmp:
        if os.path.dirname(os.path.abspath(rotasyon_yol)) != TOOLS:
            _taban_kopyala(os.path.dirname(os.path.abspath(rotasyon_yol)))
        defter = os.path.join(tmp, "DEVAM.md")
        arsiv = os.path.join(tmp, "DEVAM-ARSIV.md")
        with open(defter, "w", encoding="utf-8") as f:
            f.write(defter_icerik)
        with open(arsiv, "w", encoding="utf-8") as f:
            f.write("")
        r = subprocess.run(
            [sys.executable, rotasyon_yol, defter, arsiv,
             "--tarih", "2026-08-20"] + list(ek_argv),
            capture_output=True, text=True, timeout=90)
        with open(defter, encoding="utf-8") as f:
            defter_son = f.read()
        with open(arsiv, encoding="utf-8") as f:
            arsiv_son = f.read()
    return {"rc": r.returncode, "cikti": r.stdout, "hata": r.stderr,
            "defter": defter_son, "arsiv": arsiv_son}


def _kova(cikti):
    """`MADDE_KOVALARI ...` satirini dict'e cevirir. Satir yoksa None."""
    for satir in cikti.splitlines():
        if satir.startswith("MADDE_KOVALARI "):
            d = {}
            for parca in satir.split()[1:]:
                if "=" in parca:
                    ad, _, deger = parca.partition("=")
                    try:
                        d[ad] = int(deger)
                    except ValueError:
                        d[ad] = deger
            return d
    return None


def _ozet_sayi(cikti, ad):
    """`TASINAN=` ile baslayan OZET satirindan alan okur. Yoksa None."""
    for satir in cikti.splitlines():
        if satir.startswith("TASINAN="):
            for parca in satir.split():
                if parca.startswith(ad + "="):
                    try:
                        return int(parca.split("=", 1)[1])
                    except ValueError:
                        return None
    return None


def _mutant_kur(kaynak_yol, eski, yeni, tmp):
    """Mutant kopyayi yazar. (yol, None) ya da (None, 'CAPA BAYAT: ...')."""
    with open(kaynak_yol, encoding="utf-8") as f:
        govde = f.read()
    adet = govde.count(eski)
    if adet != 1:
        return None, ("CAPA BAYAT (%s): beklenen 1 isabet, bulunan %d — %r"
                      % (os.path.basename(kaynak_yol), adet, eski[:70]))
    yol = os.path.join(tmp, os.path.basename(kaynak_yol))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni, 1))
    return yol, None


# ---------------------------------------------------------------------------
# KAPI PROBU — KIMLIK EKSENI SOKULUR ve SOKUM DOGRULANIR
# ---------------------------------------------------------------------------
def _kapi_ortami():
    ortam = dict(os.environ)
    ortam.pop("PRUVO_ISCI_KOSUMU", None)
    ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)
    mevcut = ortam.get("PYTHONPATH", "")
    ortam["PYTHONPATH"] = (TOOLS + os.pathsep + mevcut) if mevcut else TOOLS
    return ortam


def _kapi_sor(kapi_yol, komut):
    """Kapiya bir Bash komutu yollar; 'allow' / 'deny' / hata jetonu doner."""
    yuk = {
        "session_id": "k243-kabul",
        "cwd": ANA,
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut},
    }
    try:
        r = subprocess.run(
            [sys.executable, kapi_yol], input=json.dumps(yuk),
            capture_output=True, text=True, timeout=30, env=_kapi_ortami())
    except subprocess.TimeoutExpired:
        return "ZAMAN_ASIMI"
    if r.returncode != 0:
        return "COKTU"
    cikti = (r.stdout or "").strip()
    if not cikti:
        return "allow" if "MIMAR-KAPISI allow" in (r.stderr or "") else "IZSIZ"
    try:
        veri = json.loads(cikti)
    except Exception:
        return "PARSE_HATASI"
    karar = ((veri.get("hookSpecificOutput") or {}).get("permissionDecision")
             or veri.get("permissionDecision") or veri.get("decision"))
    if karar in ("deny", "block"):
        return "deny"
    if karar in ("allow", "approve"):
        return "allow"
    return "BILINMEYEN:" + str(karar)


def _kimlik_sokuldu_mu(kapi_yol):
    """POZITIF KONTROL: kimlik ekseni gercekten sokuldu mu?

    ISCI kimliginde kapi HICBIR kural uygulamaz — o baglamda 'curl' bile
    ALLOW gelir ve butun kapi vakalari sahte-yesil yanar. Bilinen-yasak iki
    komut RED gelmiyorsa olcum YAPILAMAZ (MUAF_BAGLAM).
    """
    return (_kapi_sor(kapi_yol, YASAK_CURL) == "deny"
            and _kapi_sor(kapi_yol, YASAK_SORT) == "deny")


# ---------------------------------------------------------------------------
# VAKALAR (rotasyon ekseni)
# ---------------------------------------------------------------------------
def vaka_f1(rotasyon_yol):
    """F1 — kapsayici BUTUN olarak tasinmaz; yalniz KAPALI maddesi iner."""
    s = _kos_rotasyon(rotasyon_yol, F1)
    kova = _kova(s["cikti"])
    if kova is None:
        return False, "MADDE_KOVALARI satiri BASILMADI (K243 kapsam satiri yok)"
    hatalar = []
    if _ozet_sayi(s["cikti"], "TASINAN") != 0:
        hatalar.append("TASINAN=%s (0 beklenir — kapsayici BUTUN tasinamaz)"
                       % _ozet_sayi(s["cikti"], "TASINAN"))
    if _ozet_sayi(s["cikti"], "TASINAN_MADDE") != 1:
        hatalar.append("TASINAN_MADDE=%s (1 beklenir)"
                       % _ozet_sayi(s["cikti"], "TASINAN_MADDE"))
    if "## ARSIVDE" not in s["defter"]:
        hatalar.append("kapsayici baslik DEFTERDEN GITTI")
    if "Jetonsuz satir" not in s["defter"]:
        hatalar.append("sinifi belirsiz satir DEFTERDEN GITTI (fail-closed ihlali)")
    if "eski indeks satiri" not in s["arsiv"]:
        hatalar.append("KAPALI madde ARSIVE INMEDI")
    if kova.get("KAPSAYICI_BLOK") != 1:
        hatalar.append("KAPSAYICI_BLOK=%s (1 beklenir)" % kova.get("KAPSAYICI_BLOK"))
    if kova.get("SINIFLANAMAZ") != 1:
        hatalar.append("SINIFLANAMAZ=%s (1 beklenir)" % kova.get("SINIFLANAMAZ"))
    if kova.get("KAPALI") != 1:
        hatalar.append("KAPALI=%s (1 beklenir)" % kova.get("KAPALI"))
    return (not hatalar), "; ".join(hatalar) or "kapsayici korundu, kapali madde indi"


def vaka_f2(rotasyon_yol):
    """F2 — NEGATIF KONTROL: acik kalem sayisi DEGISMEZ."""
    once = F2.count("🔴") + F2.count("🔧") + F2.count("🟠")
    s = _kos_rotasyon(rotasyon_yol, F2)
    sonra = s["defter"].count("🔴") + s["defter"].count("🔧") + s["defter"].count("🟠")
    kova = _kova(s["cikti"])
    hatalar = []
    if once != sonra:
        hatalar.append("ACIK KALEM SAYISI DEGISTI: once=%d sonra=%d" % (once, sonra))
    for ad in ("X1 K901", "X2 K902", "X4 K903", "X6 K904"):
        if ad not in s["defter"]:
            hatalar.append("acik kalem KAYBOLDU: %s" % ad)
        if ad in s["arsiv"]:
            hatalar.append("acik kalem ARSIVE GITTI: %s" % ad)
    if _ozet_sayi(s["cikti"], "TASINAN_MADDE") != 1:
        hatalar.append("TASINAN_MADDE=%s (1 beklenir — yalniz X3)"
                       % _ozet_sayi(s["cikti"], "TASINAN_MADDE"))
    if kova is None:
        hatalar.append("MADDE_KOVALARI satiri BASILMADI")
    else:
        # 🔴 K267 (24 Agu): X6 satiri (`- ✅ KAPANDI: X5 listesi — kalan 🟠
        # **X6 K904** durmali.`) artik ACIK degil SINIFLANAMAZ kovasindadir.
        # Sebep GEVSEME DEGIL SIKILASTIRMA: satir kapanis HALI tasidigi halde
        # icinde ACIK kalem de var; "ortak satir" kolu onu fail-closed tutar VE
        # sebebini ADIYLA basar (mimar hukmu 3: "sessizce acik sayilmaz").
        # Maddi invaryant DEGISMEDI ve YUKARIDA olculuyor: X6 defterde KALIR,
        # arsive GITMEZ, TASINAN_MADDE=1. Bucket beklentisi o yuzden 4 -> 3+1
        # olarak TASINDI ve uzerine SEBEP BASIMI sarti EKLENDI.
        if kova.get("ACIK") != 3:
            hatalar.append("ACIK=%s (3 beklenir)" % kova.get("ACIK"))
        if kova.get("SINIFLANAMAZ") != 1:
            hatalar.append("SINIFLANAMAZ=%s (1 beklenir — X6 ortak satiri)"
                           % kova.get("SINIFLANAMAZ"))
        if not any(satir.startswith("TASINMADI-MADDE (SINIFLANAMAZ)")
                   and "SEBEP: ortak satir:" in satir
                   for satir in s["cikti"].splitlines()):
            hatalar.append("ORTAK SATIR SEBEBI BASILMADI (sessiz veto)")
        if kova.get("KAPSAYICI_BLOK") != 2:
            hatalar.append("KAPSAYICI_BLOK=%s (2 beklenir)" % kova.get("KAPSAYICI_BLOK"))
        if kova.get("TUTARSIZ") != 0:
            hatalar.append("TUTARSIZ=%s (0 beklenir — ikiz tanim ayristi)"
                           % kova.get("TUTARSIZ"))
    return (not hatalar), "; ".join(hatalar) or "acik kalem 3/3 yerinde, yalniz X3 indi"


def vaka_f3(rotasyon_yol):
    """F3 — HEDEF-DISI: kapsayici OLMAYAN kapali blok BUTUN olarak tasinir."""
    s = _kos_rotasyon(rotasyon_yol, F3)
    hatalar = []
    if _ozet_sayi(s["cikti"], "TASINAN") != 1:
        hatalar.append("TASINAN=%s (1 beklenir)" % _ozet_sayi(s["cikti"], "TASINAN"))
    if "## KAPALI SERI" in s["defter"]:
        hatalar.append("kapali blok defterde KALDI")
    if "## KAPALI SERI" not in s["arsiv"]:
        hatalar.append("kapali blok ARSIVE GITMEDI")
    return (not hatalar), "; ".join(hatalar) or "kapsayici olmayan kapali blok BUTUN tasindi"


def vaka_f4(rotasyon_yol):
    """F4 — UCUNCU ve DORDUNCU kova GORUNUR (0 olsa bile satir basar)."""
    s = _kos_rotasyon(rotasyon_yol, F4)
    kova = _kova(s["cikti"])
    if kova is None:
        return False, "MADDE_KOVALARI satiri BASILMADI"
    hatalar = []
    if kova.get("SINIFLANAMAZ") != 1:
        hatalar.append("SINIFLANAMAZ=%s (1 beklenir)" % kova.get("SINIFLANAMAZ"))
    if kova.get("ARSIV_ISARETCISI") != 1:
        hatalar.append("ARSIV_ISARETCISI=%s (1 beklenir)" % kova.get("ARSIV_ISARETCISI"))
    if kova.get("KAPALI") != 0:
        hatalar.append("KAPALI=%s (0 beklenir)" % kova.get("KAPALI"))
    if kova.get("INCELENEN") != 2:
        hatalar.append("INCELENEN=%s (2 beklenir)" % kova.get("INCELENEN"))
    if "TASINMADI-MADDE (SINIFLANAMAZ)" not in s["cikti"]:
        hatalar.append("SINIFLANAMAZ madde ADIYLA basilmadi")
    if _ozet_sayi(s["cikti"], "TASINAN_MADDE") != 0:
        hatalar.append("TASINAN_MADDE=%s (0 beklenir — supheli TASINMAZ)"
                       % _ozet_sayi(s["cikti"], "TASINAN_MADDE"))
    return (not hatalar), "; ".join(hatalar) or "ucuncu+dorduncu kova gorunur, ikisi de TASINMADI"


ROTASYON_VAKALARI = (
    ("F1 kapsayici/kalem ayrimi", vaka_f1),
    ("F2 acik kalem kaybolmaz", vaka_f2),
    ("F3 kapsayici-disi kapali blok", vaka_f3),
    ("F4 ucuncu+dorduncu kova", vaka_f4),
)


# ---------------------------------------------------------------------------
# MUTANT TANIMLARI
# ---------------------------------------------------------------------------
CAPA_A_ESKI = (
    "    if _blok_kapsayici_mi(blok):\n"
    "        return False\n"
    "    tum = blok[\"baslik\"] + \"\\n\" + \"\\n\".join(blok[\"govde\"])\n")
CAPA_A_YENI = (
    "    if False:  # MUT-A: kapsayici/kalem ayrimi kaldirildi\n"
    "        return False\n"
    "    tum = blok[\"baslik\"] + \"\\n\" + \"\\n\".join(blok[\"govde\"])\n")

# 🔴 K267 (24 Agu): MUT-B'nin hedefi DEGISMEDI — "madde ACIK vetosu" — ama o
# veto ARTIK `_madde_tasinir_mi` icinde ciplak `_acik_eslesiyor` cagrisi DEGIL:
# kapalilik yuklemi HALDEN okunmaya gecince acik jetonun tasimayi durdurmasi
# ORTAK SATIR koluna tasindi (`_ortak_satir_sebebi`, hal + basliktan SONRA acik
# jeton -> SINIFLANAMAZ, fail-closed). Capa YENI KOLA nisanlandi; eski ada
# nisanli kalsa mutant `OLCULEMEDI` verip F2/X6 vakasini olcusuz birakirdi
# ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
CAPA_B_ESKI = (
    "    if _ortak_satir_sebebi(metin) is not None:\n"
    "        return False\n")
CAPA_B_YENI = (
    "    if False:  # MUT-B: madde ACIK vetosu (ortak satir kolu) kaldirildi\n"
    "        return False\n")

CAPA_KONTROL_ESKI = (
    "def _blok_anlamli_govde_satiri(blok):\n"
    "    return len([s for s in blok[\"govde\"] if s.strip()])\n")
CAPA_KONTROL_YENI = (
    "def _blok_anlamli_govde_satiri(blok):\n"
    "    return 0  # KONTROL MUTANTI: ilgisiz kol (yalniz isaretciye-indirme okur)\n")

CAPA_C_ESKI = (
    "        if not _bakim_bayraklari_izinli(DEFTER_ROTASYON_YOL, argumanlar[1:]):\n"
    "            return False\n")
CAPA_C_YENI = (
    "        if any(a.startswith(\"-\") for a in argumanlar[1:]):\n"
    "            return False  # MUT-C: DEFTER BAKIMI kovasi kaldirildi\n")

CAPA_D_ESKI = "    return all(b in izinli for b in bayraklar)\n"
CAPA_D_YENI = "    return True  # MUT-D: bayrak TAM ESITLIGI kaldirildi\n"

CAPA_E_ESKI = "    if ilk == KUTU_ARSIVLE_YOL:\n"
CAPA_E_YENI = "    if False:  # MUT-E: kutu bakim kolu kaldirildi\n"

CAPA_KAPI_KONTROL_ESKI = (
    "    if ilk == D1_YOL:\n"
    "        return len(argumanlar) == 2 and argumanlar[1] == \"--durum\"\n")
CAPA_KAPI_KONTROL_YENI = (
    "    if ilk == D1_YOL:\n"
    "        return False  # KONTROL MUTANTI: ilgisiz kol (d1-sync --durum)\n")


# ---------------------------------------------------------------------------
def _rotasyon_mutant_kosumu(ad, eski, yeni, hedef_vakalar, disi_vakalar):
    """Mutant kur, HEDEF vakalari OLDURMELI, HEDEF-DISI vakalar YASAMALI.

    Donus: (durum, aciklama). durum: 'OLDURDU' | 'YASADI' | 'OLCULEMEDI'
    """
    with tempfile.TemporaryDirectory(prefix="k243-mut-") as tmp:
        yol, hata = _mutant_kur(ROTASYON, eski, yeni, tmp)
        if yol is None:
            return "OLCULEMEDI", hata
        _taban_kopyala(tmp)
        olen = []
        yasayan = []
        for vad, fn in hedef_vakalar:
            try:
                gecti, _ = fn(yol)
            except Exception as e:                       # noqa: BLE001
                return "OLCULEMEDI", "%s mutant kosumu COKTU: %s" % (vad, e)
            (yasayan if gecti else olen).append(vad)
        # HEDEF-KOL ATFI: mutant hedef kolunu mu oldurdu, yoksa genel bir
        # cokme mi? Hedef-DISI vakalar mutant altinda AYNEN gecmeli.
        atif_bozuk = []
        for vad, fn in disi_vakalar:
            try:
                gecti, mesaj = fn(yol)
            except Exception as e:                       # noqa: BLE001
                atif_bozuk.append("%s COKTU: %s" % (vad, e))
                continue
            if not gecti:
                atif_bozuk.append("%s de dustu: %s" % (vad, mesaj))
        if not olen:
            return "YASADI", "hedef vaka(lar) OLMEDI: %s" % ", ".join(yasayan)
        if atif_bozuk:
            return "OLCULEMEDI", ("HEDEF-KOL ATFI YOK — mutant hedef-DISI vakayi "
                                  "da dusurdu: " + "; ".join(atif_bozuk))
        return "OLDURDU", ("hedef olen=%s · hedef-disi YASADI=%s (atif TAMAM)"
                           % (",".join(olen), ",".join(v for v, _ in disi_vakalar)))


def _kapi_mutant_kosumu(ad, eski, yeni, olmeli, yasamali):
    """Kapi mutanti. olmeli/yasamali: [(komut_adi, komut, beklenen_karar)]."""
    with tempfile.TemporaryDirectory(prefix="k258-mut-") as tmp:
        yol, hata = _mutant_kur(KAPI, eski, yeni, tmp)
        if yol is None:
            return "OLCULEMEDI", hata
        shutil.copy2(KIMLIK, os.path.join(tmp, os.path.basename(KIMLIK)))
        if not _kimlik_sokuldu_mu(yol):
            return "OLCULEMEDI", "MUAF_BAGLAM: kimlik ekseni sokulemedi"
        degisen = []
        for kad, komut, taban_karar in olmeli:
            simdi = _kapi_sor(yol, komut)
            if simdi != taban_karar:
                degisen.append("%s %s->%s" % (kad, taban_karar, simdi))
        atif_bozuk = []
        for kad, komut, taban_karar in yasamali:
            simdi = _kapi_sor(yol, komut)
            if simdi != taban_karar:
                atif_bozuk.append("%s %s->%s" % (kad, taban_karar, simdi))
        if not degisen:
            return "YASADI", "hedef komutlarin karari DEGISMEDI"
        if atif_bozuk:
            return "OLCULEMEDI", ("HEDEF-KOL ATFI YOK — hedef-DISI komut da "
                                  "degisti: " + "; ".join(atif_bozuk))
        return "OLDURDU", ("hedef degisti: %s · hedef-disi SABIT: %s"
                           % (", ".join(degisen),
                              ", ".join(k for k, _, _ in yasamali)))


# ---------------------------------------------------------------------------
def _taban_kiyas():
    """TABAN KIYASI — ONARIM ONCESI arac (ana checkout) AYNI vakalarda ne yapar?

    [[olcut-civilenirken-taban-olculmeli]]: "sonra yesil" tek basina kanit
    degildir; ONCE'nin KIRMIZI oldugu da olculur. Bu kol yalnizca RAPORLAR,
    hukum vermez (ana checkout merge sonrasi ONARILMIS olacaktir).
    """
    taban_arac = os.path.join(ANA, "tools", "defter-rotasyon.py")
    print("=" * 78)
    print("TABAN KIYASI — ana checkout araci: %s" % taban_arac)
    print("=" * 78)
    if not os.path.exists(taban_arac):
        print("  OLCULEMEDI: taban arac yok")
        return 2
    if os.path.abspath(taban_arac) == os.path.abspath(ROTASYON):
        print("  OLCULEMEDI: taban ile hedef AYNI dosya (worktree disinda kosuldu)")
        return 2
    for ad, fn in ROTASYON_VAKALARI:
        try:
            gecti, mesaj = fn(taban_arac)
        except Exception as e:                           # noqa: BLE001
            print("  TABAN-OLCULEMEDI %-30s %s" % (ad, e))
            continue
        print("  TABAN-%-7s %-30s %s"
              % ("YESIL" if gecti else "KIRMIZI", ad, mesaj))
    s = _kos_rotasyon(taban_arac, F1)
    print("  TABAN F1 ayrintisi: TASINAN=%s TASINAN_MADDE=%s · "
          "defterde '## ARSIVDE' %s · defterde 'Jetonsuz satir' %s"
          % (_ozet_sayi(s["cikti"], "TASINAN"),
             _ozet_sayi(s["cikti"], "TASINAN_MADDE"),
             "VAR" if "## ARSIVDE" in s["defter"] else "YOK",
             "VAR" if "Jetonsuz satir" in s["defter"] else "YOK"))
    print("  TABAN MADDE_KOVALARI satiri: %s"
          % ("VAR" if _kova(s["cikti"]) else "YOK (teshis yuzeyi hic yoktu)"))
    return 0


def main():
    if "--taban-kiyas" in sys.argv[1:]:
        return _taban_kiyas()
    print("=" * 78)
    print("K243 + K258 KABUL BATARYASI — tasima birimi + defter bakimi kovasi")
    print("=" * 78)

    kirmizi = 0
    olculemedi = 0
    vaka_sayisi = 0
    mutant_sayisi = 0
    kontrol_sayisi = 0
    kapi_vaka_sayisi = 0

    # --- 1) TABAN: gercek arac uzerinde vakalar --------------------------
    print("\n--- 1) VAKALAR (gercek arac) ---")
    for ad, fn in ROTASYON_VAKALARI:
        vaka_sayisi += 1
        try:
            gecti, mesaj = fn(ROTASYON)
        except Exception as e:                           # noqa: BLE001
            olculemedi += 1
            print("  OLCULEMEDI %-32s %s" % (ad, e))
            continue
        if not gecti:
            kirmizi += 1
        print("  %-6s %-32s %s" % ("YESIL" if gecti else "KIRMIZI", ad, mesaj))

    # --- 2) ROTASYON MUTANTLARI (hedef-kol atifli) -----------------------
    print("\n--- 2) ROTASYON MUTANTLARI (her biri hedef kolunu oldurdugunu AYRICA kanitlar) ---")
    rot_mutantlar = (
        ("MUT-A kapsayici/kalem ayrimi", CAPA_A_ESKI, CAPA_A_YENI,
         (("F1 kapsayici/kalem ayrimi", vaka_f1),),
         (("F3 kapsayici-disi kapali blok", vaka_f3),
          ("F2 acik kalem kaybolmaz", vaka_f2))),
        ("MUT-B madde ACIK vetosu", CAPA_B_ESKI, CAPA_B_YENI,
         (("F2 acik kalem kaybolmaz", vaka_f2),),
         (("F1 kapsayici/kalem ayrimi", vaka_f1),
          ("F3 kapsayici-disi kapali blok", vaka_f3))),
    )
    for ad, eski, yeni, hedef, disi in rot_mutantlar:
        mutant_sayisi += 1
        durum, mesaj = _rotasyon_mutant_kosumu(ad, eski, yeni, hedef, disi)
        if durum == "OLCULEMEDI":
            olculemedi += 1
        elif durum == "YASADI":
            kirmizi += 1
        print("  %-11s %-30s %s" % (durum, ad, mesaj))

    # --- 3) KONTROL MUTANTI (rotasyon) -----------------------------------
    print("\n--- 3) KONTROL MUTANTI — ilgisiz kol bozulur, HEDEF VAKALAR YASAMALI ---")
    kontrol_sayisi += 1
    with tempfile.TemporaryDirectory(prefix="k243-kontrol-") as tmp:
        yol, hata = _mutant_kur(ROTASYON, CAPA_KONTROL_ESKI, CAPA_KONTROL_YENI, tmp)
        if yol is None:
            olculemedi += 1
            print("  OLCULEMEDI  KONTROL (rotasyon)          %s" % hata)
        else:
            _taban_kopyala(tmp)
            dusen = []
            for ad, fn in ROTASYON_VAKALARI:
                try:
                    gecti, mesaj = fn(yol)
                except Exception as e:                   # noqa: BLE001
                    dusen.append("%s COKTU: %s" % (ad, e))
                    continue
                if not gecti:
                    dusen.append("%s: %s" % (ad, mesaj))
            if dusen:
                kirmizi += 1
                print("  KIRMIZI     KONTROL (rotasyon)          TAUTOLOJI: ilgisiz "
                      "kol vakalari dusurdu -> %s" % "; ".join(dusen))
            else:
                print("  YESIL       KONTROL (rotasyon)          ilgisiz kol bozuldu, "
                      "%d/%d hedef vaka YASADI (tautoloji yok)"
                      % (len(ROTASYON_VAKALARI), len(ROTASYON_VAKALARI)))

    # --- 4) KAPI VAKALARI ------------------------------------------------
    print("\n--- 4) KAPI (DEFTER BAKIMI kovasi) ---")
    if not _kimlik_sokuldu_mu(KAPI):
        olculemedi += 1
        print("  OLCULEMEDI  MUAF_BAGLAM: kimlik ekseni sokulemedi (prob ISCI "
              "kimliginde kosuyor olabilir) — kapi vakalari OLCULMEDI")
        kapi_taban = None
    else:
        print("  (kimlik ekseni SOKULDU ve DOGRULANDI: curl + sort RED geldi)")
        kapi_taban = (
            ("CARE-defter (izinli bayraklar)", CARE_DEFTER, "allow"),
            ("kanonik bayraksiz", KANONIK_BAYRAKSIZ, "allow"),
            ("CARE-kutu --kuru", CARE_KUTU, "allow"),
            ("durum.py (eski serbest)", SERBEST_DURUM, "allow"),
            ("NEG --tavan-sayi 130", YASAK_TAVAN_SAYI, "deny"),
            ("NEG --tavan-sayi=130", YASAK_ESITLIKLI, "deny"),
            ("NEG --tarih", YASAK_TARIH, "deny"),
            ("NEG kutu --tavan 300", YASAK_KUTU_TAVAN, "deny"),
            ("NEG curl", YASAK_CURL, "deny"),
            ("NEG sort", YASAK_SORT, "deny"),
            ("NEG genel python", YASAK_GENEL_PY, "deny"),
        )
        for ad, komut, beklenen in kapi_taban:
            kapi_vaka_sayisi += 1
            gorulen = _kapi_sor(KAPI, komut)
            uydu = (gorulen == beklenen)
            if not uydu:
                kirmizi += 1
            print("  %-6s %-32s beklenen=%s gorulen=%s"
                  % ("YESIL" if uydu else "KIRMIZI", ad, beklenen, gorulen))

    # --- 5) KAPI MUTANTLARI ----------------------------------------------
    print("\n--- 5) KAPI MUTANTLARI (hedef-kol atifli) ---")
    kapi_mutantlar = (
        ("MUT-C bakim kovasi kaldirilir", CAPA_C_ESKI, CAPA_C_YENI,
         (("CARE-defter", CARE_DEFTER, "allow"),),
         (("kanonik bayraksiz", KANONIK_BAYRAKSIZ, "allow"),
          ("NEG curl", YASAK_CURL, "deny"))),
        ("MUT-D bayrak TAM ESITLIGI", CAPA_D_ESKI, CAPA_D_YENI,
         # Duzeltme (20 Agu): --tavan-sayi 130'un '130'u 3. konumsal arg olur ve
         # `_bakim_konumlari_izinli` len 3 vs 2 diyegeri RED; mutant return True
         # olsa bile o kol yine RED verir, kapinin karari DEGISMEZ -> YASADI.
         # `--tavan-sayi=130` ise TEK token olarak bayrak setine girer, konumlar
         # yalniz [file, arsiv] kalir; mutant altinda bayrak TAM ESITLIGI gecer,
         # konum TAM ESITLIGI de gecer -> ALLOW. HEDEF KOLU gercekten ortaya cikarir.
         (("NEG --tavan-sayi=130", YASAK_ESITLIKLI, "deny"),),
         (("NEG curl", YASAK_CURL, "deny"),
          ("NEG genel python", YASAK_GENEL_PY, "deny"))),
        ("MUT-E kutu kolu kaldirilir", CAPA_E_ESKI, CAPA_E_YENI,
         (("CARE-kutu --kuru", CARE_KUTU, "allow"),),
         (("CARE-defter", CARE_DEFTER, "allow"),
          ("NEG curl", YASAK_CURL, "deny"))),
    )
    for ad, eski, yeni, olmeli, yasamali in kapi_mutantlar:
        mutant_sayisi += 1
        durum, mesaj = _kapi_mutant_kosumu(ad, eski, yeni, olmeli, yasamali)
        if durum == "OLCULEMEDI":
            olculemedi += 1
        elif durum == "YASADI":
            kirmizi += 1
        print("  %-11s %-30s %s" % (durum, ad, mesaj))

    # --- 6) KONTROL MUTANTI (kapi) ---------------------------------------
    print("\n--- 6) KONTROL MUTANTI (kapi) — ilgisiz kol bozulur, BAKIM VAKALARI YASAMALI ---")
    kontrol_sayisi += 1
    with tempfile.TemporaryDirectory(prefix="k258-kontrol-") as tmp:
        yol, hata = _mutant_kur(KAPI, CAPA_KAPI_KONTROL_ESKI,
                                CAPA_KAPI_KONTROL_YENI, tmp)
        if yol is None:
            olculemedi += 1
            print("  OLCULEMEDI  KONTROL (kapi)               %s" % hata)
        elif not _kimlik_sokuldu_mu(yol):
            olculemedi += 1
            print("  OLCULEMEDI  KONTROL (kapi)               MUAF_BAGLAM")
        else:
            shutil.copy2(KIMLIK, os.path.join(tmp, os.path.basename(KIMLIK)))
            sapan = []
            for ad, komut, beklenen in (
                    ("CARE-defter", CARE_DEFTER, "allow"),
                    ("CARE-kutu --kuru", CARE_KUTU, "allow"),
                    ("NEG --tavan-sayi 130", YASAK_TAVAN_SAYI, "deny"),
                    ("NEG curl", YASAK_CURL, "deny")):
                gorulen = _kapi_sor(yol, komut)
                if gorulen != beklenen:
                    sapan.append("%s %s->%s" % (ad, beklenen, gorulen))
            if sapan:
                kirmizi += 1
                print("  KIRMIZI     KONTROL (kapi)               TAUTOLOJI: %s"
                      % "; ".join(sapan))
            else:
                print("  YESIL       KONTROL (kapi)               ilgisiz kol bozuldu, "
                      "4/4 bakim vakasi YASADI (tautoloji yok)")

    print("\n" + "=" * 78)
    print("KAPSAM VAKA=%d MUTANT=%d KONTROL=%d KAPI=%d KIRMIZI=%d OLCULEMEDI=%d"
          % (vaka_sayisi, mutant_sayisi, kontrol_sayisi, kapi_vaka_sayisi,
             kirmizi, olculemedi))
    if olculemedi:
        return 2
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
