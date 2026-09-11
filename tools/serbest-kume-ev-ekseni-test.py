#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — SERBEST CAGRI TABLOSUNUN **EV EKSENI** ve **YONLENDIRME EKSENI**.

=== NEDEN VAR (olculmus ariza, 10 Eyl 2026 — BaBa hukmu 23:2x, KraL kalem ③) ===
`tools/serbest_cagrilar.py` repo kokunu MUTLAK SABIT olarak tasiyordu
(`REPO_ONEKI = "/Users/okan/dev/pruvo/"`). `tools/kapi_dagitim.py` kardes evlere bir
SHIM kurar ve o shim `mimar-icra-kapisi.py`nin KENDI capasini eve cevirir — ama kapi
hemen ardindan `DURUM_YOL = SC.DURUM_YOL ...` diyerek dogru cevrilmis degerleri
BU MODULDEN gelen KraL'a civili yollarla EZIYORDU.

TABAN (bu turda GERCEK kurulu shim'ler uzerinden KOSULARAK olculdu — kanonik govde
uzerinden degil; iki olcum ayni sonucu verdi):

    ev        arac  'defter-rotasyon.py <kendi DEVAM.md>'  '... 2>&1'
    KraL      VAR   ALLOW                                   DENY   <-- EKSEN 2
    ArTisT    VAR   DENY   <-- EKSEN 1                      DENY
    TeKiN     VAR   DENY   <-- EKSEN 1                      DENY
    MaCiT     YOK   KAPSAM DISI (arac yoklugu)
    HocA      YOK   KAPSAM DISI (arac yoklugu)

BEDELI: ArTisT/MaCiT/TeKiN defterlerini UC TURDUR ELLE kisaltti; ArTisT bunu kendi
devir blogunda ENGEL olarak yazdi.

🔴 IKI AYRI EKSEN, AYNI DOSYA — TEK YAMA IKISINI KAPATMAZ:
  * EKSEN 1 (EV):  kok sabit -> her kardes evde YANLIS AGAC olculur.
  * EKSEN 2 (EK):  serbest listede BIREBIR yazili komut, kabuk yonlendirme eki
    (`2>&1`) yuzunden RED alir. Mekanizma OLCULDU: segmentleyici '&' uzerinden
    boldugu icin geriye '2>' ARTIGI kalir ve '-' ile baslamadigi icin KONUMSAL
    ARGUMAN sayilir; konum sayisi sisince sekil TAM ESITLIKTE duser. Yetim '1'
    segmenti ZARARSIZDIR (olculdu: 'git status 2>&1' -> ALLOW).

🔴 IZOLASYON: hicbir mutant CANLI govdede kosmaz. Her vaka, gecici dizine cikarilmis
IZOLE bir kopya uzerinde ve SHIM'in yaptigi capa cevirisi TAKLIT EDILEREK olculur
([[mutant-canli-govdede-yasamaz]]). Gercek ev agaclarina YAZILMAZ, hicbir sey silinmez.

🔴 ONEK TUZAGI: '-Users-okan-dev-pruvo' damgasi '-Users-okan-dev-pruvo-pazarlama'nin
ONEKIDIR. Kisa eslesme once alinirsa ArTisT'in oturumu KraL'a cozulur ve ariza YER
DEGISTIRIR ([[arac-adi-onek-eslesmesi-komsu-araci-keser]]). E5 tam bunu olcer.

CI-ALT-KUME: kendini-test
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import serbest_cagrilar as SC          # noqa: E402
import kapi_dagitim as KD              # noqa: E402
import mimar_kimlik as MK              # noqa: E402

KAPI_ADI = "mimar-icra-kapisi.py"

# IZOLE kopyaya tasinacak dosyalar. Eksik biri, kapinin kopyasini import'ta COKERTIR
# ve her vaka "DENY" diye okunur — yani ariza MASKELENIR
# ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
KOPYALANAN = (
    KAPI_ADI,
    "serbest_cagrilar.py",
    "mimar_kimlik.py",
    "kapi_dagitim.py",
)

# `kapi_dagitim.py`nin BES EVIN shim'ine vaat ettigi capa. Metni degisirse bes ev
# birden fail-closed DENY'a duser; bu test o capayi da OLCER (E7).
CAPA_REPO = KD.CAPA_REPO


# --------------------------------------------------------------------------
def _izole_kopya(kok_hedef, mutasyonlar=()):
    """Kapiyi gecici dizine cikarir ve SHIM'in capa cevirisini TAKLIT eder.

    `mutasyonlar`: (dosya, eski, yeni) uclusu. Eski metin BULUNAMAZSA hata atar —
    sessizce INERT kalan bir mutant "oldurulemedi"yi gizlerdi
    ([[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]])."""
    dizin = tempfile.mkdtemp(prefix="ev-ekseni-")
    for ad in KOPYALANAN:
        shutil.copy2(os.path.join(TOOLS, ad), os.path.join(dizin, ad))

    kapi_yolu = os.path.join(dizin, KAPI_ADI)
    with open(kapi_yolu, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(CAPA_REPO) != 1:
        raise AssertionError(
            "CAPA_REPO govde icinde TAM BIR KEZ gecmiyor (%d) — shim sozlesmesi "
            "KIRIK, bes ev fail-closed DENY'a duser." % govde.count(CAPA_REPO))
    govde = govde.replace(
        CAPA_REPO, 'REPO_ONEKI = "' + kok_hedef.rstrip("/") + '/"')
    with open(kapi_yolu, "w", encoding="utf-8") as f:
        f.write(govde)

    for dosya, eski, yeni in mutasyonlar:
        yol = os.path.join(dizin, dosya)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        if eski not in metin:
            raise AssertionError(
                "MUTANT CAPASI BULUNAMADI (%s): %r — mutant INERT olurdu." %
                (dosya, eski[:60]))
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni, 1))
    return dizin


def _karar(dizin, kok, komut, damga=None):
    """IZOLE kapiyi GERCEK PreToolUse yuku ile kosturur. Doner: 'ALLOW'/'DENY'."""
    girdi = {"tool_name": "Bash", "tool_input": {"command": komut}, "cwd": kok}
    if damga is not None:
        girdi[MK.ROL_KANALI] = damga
    p = subprocess.run([sys.executable, os.path.join(dizin, KAPI_ADI)],
                       input=json.dumps(girdi), capture_output=True, text=True)
    if p.returncode != 0:
        return "COKTU:" + (p.stderr or "")[-200:]
    if not p.stdout.strip():
        return "ALLOW"
    try:
        return json.loads(p.stdout)["hookSpecificOutput"][
            "permissionDecision"].upper()
    except Exception:
        return "COZULEMEDI"


def _ana_damgasi(kok):
    """O evin ANA oturumunun transcript_path'i — Claude Code'un kendi kurali."""
    return ("/Users/okan/.claude/projects/" + SC._proje_damgasi(kok)
            + "/oturum.jsonl")


def _klasik(kok):
    """O evin KENDI defterini rotasyona sokan cagri (iki konumlu klasik form)."""
    return ("python3 tools/defter-rotasyon.py "
            + os.path.join(kok, "DEVAM.md") + " "
            + os.path.join(kok, "DEVAM-ARSIV.md"))


# === 11 EYL 2026 — GOZLENEN SEY "DENY" DEGIL, PREDIKAT ========================
# 🔴 OKAN EMRI (11 Eyl, "tum tikayicilari kaldir"): `mimar-icra-kapisi.py`in
# python/node ALLOWLIST kolu ARTIK REDDETMIYOR, RAPOR EDIYOR. Bu testin E2/E4/E6
# kollari gozlenebilir olarak gate'in DENY'ini kullaniyordu; o DENY kaldirildigi an
# dort vaka birden kirmizi yandi — ama OLCULMEK ISTENEN MEKANIZMA (ev-koklu sekil
# tablosu + yonlendirme eki soyma) AYNEN YASIYOR.
# CARE: gozlem noktasi bir KATMAN ASAGIYA, PREDIKATIN KENDISINE indirildi
# (`serbest_cagrilar.eslesen_sekil`). Boylece:
#   * ev ekseni (kok -> tablo koklendirme) OLCULMEYE DEVAM EDER,
#   * yonlendirme soyma kolu ve onun IKI mutanti OLCULMEYE DEVAM EDER,
#   * ve bunlarin hicbiri bir REDDETME YETKISI varsaymaz.
# [[sinif-adi-kol-adi-olarak-basilirsa-yanlis-alan-dogrulanir]]: olculen kolun ADI
# "predikat", "kapi karari" DEGIL — vaka basliklari da oyle yazilir.
def _predikat(dizin, kok, komut):
    """Izole kopyadaki `serbest_cagrilar` ile sekil eslesmesi: ALLOW | DENY.

    `dizin` = _izole_kopya cikisi (capasi `kok`a cevrilmis kopya). Kapi surecini
    baslatmaz; sekil tablosunu O KOPYADAN yukler, yani mutasyonlar AYNEN etkilidir.
    """
    import importlib.util as _ilu
    _s = _ilu.spec_from_file_location(
        "sc_izole_%d" % abs(hash(dizin)), os.path.join(dizin, "serbest_cagrilar.py"))
    _sc = _ilu.module_from_spec(_s)
    _s.loader.exec_module(_sc)

    tokenlar = shlex.split(komut)
    # yorumlayici adini dus (python3/node ...), kalan argumanlar sekle verilir
    argumanlar = tokenlar[1:]

    def _coz(yol, cwd):
        if os.path.isabs(yol):
            return os.path.normpath(yol)
        return os.path.normpath(os.path.join(cwd, yol))

    sekil = _sc.eslesen_sekil(argumanlar, _coz, kok, kok=kok)
    return "ALLOW" if sekil is not None else "DENY"


def _evler():
    """Kapali EV KUMESI — TEK KAYNAK kapi_dagitim.EVLER (elle liste TUTULMAZ)."""
    return [(ad, os.path.normpath(kok)) for ad, kok, _g, _m in KD.EVLER]


# === VAKALAR ==============================================================
def e0_damga_ikizi():
    """SC ve mimar_kimlik ayni damga kuralini mi uyguluyor? (ikiz ayrisma kolu)"""
    hatalar = []
    for yol in ("/Users/okan/dev/pruvo", "/Users/okan/dev/pruvo-pazarlama",
                "/a/b--c/d.e", "", "/x/.claude/worktrees/serene-ellis-8690c8"):
        if SC._proje_damgasi(yol) != MK._proje_damgasi(yol):
            hatalar.append("damga AYRISTI: %r" % yol)
    return hatalar


def e1_ev_ekseni():
    """Her evde, o evin KENDI defteri cagrisi GECMELI (arac VARSA)."""
    hatalar = []
    for ad, kok in _evler():
        dizin = _izole_kopya(kok)
        try:
            k = _karar(dizin, kok, _klasik(kok), _ana_damgasi(kok))
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
        if k != "ALLOW":
            hatalar.append("E1 %s (%s): kendi defteri cagrisi -> %s" % (ad, kok, k))
    return hatalar


def e2_mutant_ev_ekseni():
    """MUTANT (pazarlama yolu): kok SABITE geri donerse ArTisT'te RED yanmali."""
    kok = "/Users/okan/dev/pruvo-pazarlama"
    dizin = _izole_kopya(kok, mutasyonlar=(
        # 🔴 "sabiti geri koy": tablo artik hicbir eve koklendirilemez.
        ("serbest_cagrilar.py",
         "    if not kok:\n        return SEKILLER\n",
         "    if True:\n        return SEKILLER\n"),
    ))
    try:
        # PREDIKAT ekseni (gate DENY'i 11 Eyl'de kaldirildi — bkz. `_predikat` notu)
        k = _predikat(dizin, kok, _klasik(kok))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
    if k == "ALLOW":
        return ["E2 MUTANT OLMEDI: kok sabite dondugu halde pazarlama sekli "
                "hala ESLESIYOR — bu test EV EKSENINI OLCMUYOR."]
    return []


def e3_yonlendirme_pozitif():
    """Serbest listedeki komut + `2>&1` -> GECMELI (bugunku taban: RED)."""
    hatalar = []
    for ad, kok in _evler():
        dizin = _izole_kopya(kok)
        try:
            k = _karar(dizin, kok, _klasik(kok) + " 2>&1", _ana_damgasi(kok))
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
        if k != "ALLOW":
            hatalar.append("E3 %s: serbest cagri + 2>&1 -> %s" % (ad, k))
    return hatalar


def e4_yonlendirme_ters():
    """TERS KOL — normalize etmek kapiyi DELMEMELI."""
    kok = os.path.normpath(KD.EVLER[0][1])
    dizin = _izole_kopya(kok)
    damga = _ana_damgasi(kok)
    hatalar = []
    try:
        # (a) ALLOWLIST DISI bir arac + 2>&1 -> PREDIKAT ESLESMEMELI.
        # 🔴 NOT: kapi bunlari ARTIK REDDETMEZ (Okan 11 Eyl); olculen sey kapinin
        # karari degil, sekil tablosunun bunlari TANIMAMASI — yani raporun "allowlist
        # disindan kostu" diyebilmesi. Tablo bunlari tanirsa rapor da yalan olur.
        for komut in ("python3 tools/build.py 2>&1",
                      "python3 tools/build.py",
                      # DISARIDA birakilmis bayrak + 2>&1 -> hala ESLESMEZ
                      "python3 tools/defter-rotasyon.py --tavan-sayi 130 2>&1"):
            k = _predikat(dizin, kok, komut)
            if k != "DENY":
                hatalar.append("E4a DELINDI: %r -> %s" % (komut, k))
        # (b) DOSYA ADI TASIYAN yonlendirme normalize EDILMEMELI
        for ek in (" 2>/dev/null", " >/tmp/x.txt", " > /tmp/x.txt"):
            k = _predikat(dizin, kok, _klasik(kok) + ek)
            if k != "DENY":
                hatalar.append("E4b DELINDI (yol tasiyan yonlendirme): %r -> %s"
                               % (ek, k))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
    return hatalar


def e5_onek_tuzagi():
    """Damga cozumu ONEK yuzunden komsu evi kesmemeli (en UZUN eslesme kazanir)."""
    hatalar = []
    kokler = {kok for _ad, kok in _evler()}
    for _ad, kok in _evler():
        cozulen = SC.ev_koku_turet(_ana_damgasi(kok), kokler)
        if cozulen != kok:
            hatalar.append("E5 damga YANLIS EVE cozuldu: %s -> %s" % (kok, cozulen))
    # cip/worktree oturumu da KENDI evine cozulmeli
    for _ad, kok in _evler():
        cip = _ana_damgasi(os.path.join(kok, ".claude", "worktrees", "abc-123"))
        cozulen = SC.ev_koku_turet(cip, kokler)
        if cozulen != kok:
            hatalar.append("E5 CIP damgasi YANLIS EVE cozuldu: %s -> %s"
                           % (kok, cozulen))
    # eslesmeyen damga -> None (FAIL-CLOSED; "olculemedi" gecis gerekcesi DEGIL)
    for damga in ("", None, "/x/-Users-okan-dev-baskaproje/y.jsonl"):
        if SC.ev_koku_turet(damga, kokler) is not None:
            hatalar.append("E5 FAIL-CLOSED KIRIK: %r bir eve cozuldu" % (damga,))
    return hatalar


def e6_mutant_yonlendirme():
    """IKI mutant: (a) soyma kolu olurse E3 olmeli, (b) kalip GENISLERSE E4b olmeli."""
    kok = os.path.normpath(KD.EVLER[0][1])
    damga = _ana_damgasi(kok)
    hatalar = []

    # (a) soyma kolunu OLDUR -> serbest cagri + 2>&1 yeniden RED olmali
    dizin = _izole_kopya(kok, mutasyonlar=(
        ("serbest_cagrilar.py",
         "    if len(argumanlar) >= 2 and _YONLENDIRME_ARTIGI.match(argumanlar[-1]):\n"
         "        return argumanlar[:-1]\n",
         "    if False:\n        return argumanlar[:-1]\n"),
    ))
    try:
        if _predikat(dizin, kok, _klasik(kok) + " 2>&1") == "ALLOW":
            hatalar.append("E6a MUTANT OLMEDI: soyma kolu olduruldugu halde "
                           "2>&1 hala ESLESIYOR — E3 bu kolu OLCMUYOR.")
    finally:
        shutil.rmtree(dizin, ignore_errors=True)

    # (b) kalibi GENISLET (yol tasiyan yonlendirmeyi de yutar) -> E4b olmeli
    dizin = _izole_kopya(kok, mutasyonlar=(
        ("serbest_cagrilar.py",
         '_YONLENDIRME_ARTIGI = re.compile(r"^\\d*>$")',
         '_YONLENDIRME_ARTIGI = re.compile(r"^\\d*>.*$")'),
    ))
    try:
        if _predikat(dizin, kok, _klasik(kok) + " 2>/dev/null") != "ALLOW":
            hatalar.append("E6b MUTANT OLMEDI: kalip genisletildigi halde "
                           "'2>/dev/null' hala ESLESMIYOR — E4b bu kolu OLCMUYOR.")
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
    return hatalar


def e7_tuketici_envanteri():
    """🔴 TUM OKUYUCULAR SAYILIR — bir tuketici yazilirken hepsi sayilmazsa ariza
    YER DEGISTIRIR, onarilmis sanilir ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).

    Envanter git'ten okunur (os.walk DEGIL: uretilmis dosyalar yerelde gorunup
    CI'da gorunmez, sapma yaratirdi)."""
    hatalar = []
    try:
        cikti = subprocess.run(
            ["git", "-C", KOK, "grep", "-l", "serbest_cagrilar", "--", "tools/"],
            capture_output=True, text=True)
        okuyucular = sorted(
            s for s in cikti.stdout.strip().splitlines() if s.strip())
    except Exception as hata:
        return ["E7 ENVANTER OLCULEMEDI: " + repr(hata)]
    if not okuyucular:
        return ["E7 ENVANTER BOS — git grep kolu kirik, sayim hukumsuz."]

    # Karari VEREN tuketici koku GECIRMEK ZORUNDA. Gecirmezse tablo kanonik evde
    # kalir ve ariza sessizce geri doner.
    kapi = os.path.join(TOOLS, KAPI_ADI)
    with open(kapi, encoding="utf-8") as f:
        govde = f.read()
    if "eslesen_sekil(argumanlar, _coz, cwd, kok=" not in govde:
        hatalar.append("E7 KARAR KOLU KOKSUZ: mimar-icra-kapisi.py "
                       "`eslesen_sekil`e kok GECIRMIYOR — ev ekseni olu.")
    if "serbest_python_metni(ev_kok)" not in govde:
        hatalar.append("E7 RED METNI KOKSUZ: metin kararla AYNI eve baglanmiyor "
                       "([[kapi-red-metni-ikinci-kopyadir]]).")

    # Hicbir okuyucu, SEKIL tablosu icin KENDI mutlak ev kokunu DONDURMAMALI.
    for dosya in okuyucular:
        if os.path.basename(dosya) in ("serbest_cagrilar.py",
                                       os.path.basename(__file__)):
            continue
        with open(os.path.join(KOK, dosya), encoding="utf-8") as f:
            metin = f.read()
        if "SC.SEKILLER" in metin and "eve_gore" not in metin:
            # Tabloyu HAM okuyan bir tuketici: kanonik evde kalir. Bu bir HATA
            # degil ama SAYILMALI — metin/gorunum kolu ise zararsiz, KARAR kolu
            # ise arizayi geri getirir.
            if "_py_izinli" in metin or "permissionDecision" in metin:
                hatalar.append(
                    "E7 KARAR VEREN tuketici tabloyu HAM okuyor (ev ekseni "
                    "kor): " + dosya)
    print("   ENVANTER: serbest_cagrilar okuyan %d dosya -> %s"
          % (len(okuyucular), ", ".join(os.path.basename(d) for d in okuyucular)))
    return hatalar


VAKALAR = (
    ("E0 damga ikizi (SC == mimar_kimlik)", e0_damga_ikizi),
    ("E1 EV EKSENI — her ev kendi defterini rotasyona sokabiliyor", e1_ev_ekseni),
    ("E2 MUTANT (pazarlama) — kok sabite donerse KIRMIZI", e2_mutant_ev_ekseni),
    ("E3 YONLENDIRME + — serbest cagri + 2>&1 geciyor", e3_yonlendirme_pozitif),
    ("E4 YONLENDIRME - — yasak/yol tasiyan formlar PREDIKATTA ESLESMEZ", e4_yonlendirme_ters),
    ("E5 ONEK TUZAGI — damga en UZUN eve cozuluyor", e5_onek_tuzagi),
    ("E6 MUTANT (yonlendirme) — iki kol da olduruluyor", e6_mutant_yonlendirme),
    ("E7 TUKETICI ENVANTERI — tum okuyucular sayildi", e7_tuketici_envanteri),
)


def main():
    print("=== SERBEST CAGRI TABLOSU — EV EKSENI + YONLENDIRME EKSENI ===")
    print("EVLER (tek kaynak kapi_dagitim.EVLER): %s"
          % ", ".join(ad for ad, _k in _evler()))
    tum = []
    for ad, fn in VAKALAR:
        try:
            hatalar = fn()
        except Exception as hata:
            hatalar = ["%s COKTU: %r" % (ad, hata)]
        print(("  %-58s %s" % (ad, "TAMAM" if not hatalar else "KIRMIZI")))
        for h in hatalar:
            print("      - " + h)
        tum.extend(hatalar)
    print("BULGU=%d" % len(tum))
    return 0 if not tum else 1


if __name__ == "__main__":
    sys.exit(main())
