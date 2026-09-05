#!/usr/bin/env python3
"""K260 KABUL BATARYASI — kat secimi UC KOVA + arizi-jeton/emekli-kat kilidi.

CHIP: KraL-K260KatSec.

NE OLCER
  A  Sinif jetonu ARIZI BAGLAMDA (hafiza linki / dosya adi / tirnakli adim adi)
     gectiginde kalem MIMAR katina KILITLENMEZ; jeton SERBEST METINDE gecerse
     kilitlenir (NEGATIF kol).
  B  OKAN KAPISI DOKUNULMAZ (hukum 3): `kime=Okan`, Okan jetonu ve insan
     kapisinda bekleyen kalem dagitima GIRMEZ. Maskeleme Okan kapisini
     DARALTMAZ — jeton kod acikliginda bile gecerse kalem OKAN'dir.
  C  EMEKLI kat adi CANLI kata gocer (hukum 1); insan katlari kapsam DISI;
     EMEKLI kume OLCULEMEDIYSE hicbir sey gocmez (FAIL-CLOSED).
  D  Uc kova PARTISYONDUR: her kalem TAM BIR kovada, toplam = kalem sayisi
     (KAYIP YOK). Kat kaynagi olculemediyse HER kalem MIMAR_KATI_GERCEK
     (fail-closed) — supheli kalem DAGITILABILIR sayilmaz.
  E  CAGRI YERI: canli nobet turu (`tur_kapat`) kova dagilimini GERCEKTEN
     cagirir ve basar ([[kapinin-menzili-cagri-yeridir]]).

KOSUM
    python3 nobet-kat-kovasi-test.py              # kabul
    python3 nobet-kat-kovasi-test.py --mutasyon   # mutant + KONTROL
    python3 nobet-kat-kovasi-test.py --canli      # GERCEK defter/geri-iz olcumu

🔴 MUTASYON GECICI KOPYAYA UYGULANIR; canli `nobet-kapi.py`ye ASLA.
"""

import argparse
import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
DEFTER_YOLU = ("/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/"
               "acik-kalemler.md")
GERI_IZ = os.path.join(CRON_KOKU, "nobet-geri-iz.json")

VAKALAR = []


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-40s BEKLENEN=%-20s OLCULEN=%-20s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


_SAYAC = [0]


def modul_yukle(yol):
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    _SAYAC[0] += 1
    ad = "_k260_nk_%d" % _SAYAC[0]
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def _kalem(nk, kalem_id, is_metni, kime="KraL"):
    return {"id": kalem_id, "tarih": "24 Agu", "kimden_kime": "KraL → %s" % kime,
            "kime": kime, "is": is_metni, "durum_ham": nk.ONARIM_DURUMU,
            "durum": nk.ONARIM_DURUMU, "kanit_ham": "", "kabul": "",
            "satir_no": 1}


# --- GERCEK kalemlerden alinmis metin PARCALARI (elle uydurulmadi) ----------
# Kaynak: memory/acik-kalemler.md, 24 Agu 2026.
M_K77 = ("Mail nobetinin IKI hukmu de nobetin KONTROL ETMEDIGI paylasilan bir "
         "yuzeye (Cop kutusu) bagli. Sinif: "
         "[[pencere-goreli-alarm-kendini-sonduruyor]] + "
         "[[kapi-ozeti-hukumden-ayrisir]]")
M_K262 = ("N2'nin 4 SAATLIK OTOMATIK DEVIRi HIC KURULMAMIS. `14400` / "
          "`DEVREDILDI` / `ihlal_sayaci` jetonlari `~/.claude/cron/gozcu.py` + "
          "`nobet-kapi.py` + `nobet-tetik.py` dosyalarinda TOPLAM 0 kez geciyor. "
          "Bu kalem bir JETON TARAMASI degil DAVRANIS kalemidir")
M_K70 = ("Bu turda merge edilen kapi, projenin MANDAT ETTIGI commit biciminde "
         "KOR; kol GERCEK index'i okuyor ve bosta yesil veriyor")
M_K86 = ("SERIT B'de UC mutasyon bataryasi ayni anda kapsam deligi bildiriyor; "
         "deploy'u bloklamiyor ama her push'ta Run failed maili uretiyor")
M_K98 = ("K85 sinif tekrari + K80 ortak zincir; Build & deploy BLOKLU, "
         "`ebebb966` HEAD")
M_K49 = ("`d1-sync.py` YAZICI yolunda kilit YOK — iki eszamanli tam-katalog "
         "yazicisini hicbir sey engellemiyor; flock/PID kilidi + yazici ucusta "
         "fail-closed kapisi gerekiyor")
# Okan jetonu KOD ACIKLIGINDA — maskeleme burayi GORMEMELI (fail-closed).
M_OKAN_KOD = "Bu is bir `okan kapisi` kalemidir; karar Okan'da"


# ===========================================================================
# A — ARIZI JETON BAGLAMI
# ===========================================================================

def bolum_a(nk, ek=""):
    print("--- BOLUM A%s: ARIZI JETON BAGLAMI ---" % ek)
    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    vaka("A0-canli-kume-dolu%s" % ek, "dolu", "dolu" if canli else "BOS")
    vaka("A0b-emekli-kume-dolu%s" % ek, "dolu",
         "dolu" if tuple(nk.EMEKLI_ISCI_MOTORLARI) else "BOS")

    # A1/A2 — jeton YALNIZ arizi baglamda: kalem DAGITILABILIR.
    vaka("A1-K77-hafiza-linki-kilitlemez%s" % ek, nk.KOVA_DAGITILABILIR,
         nk.kova_sec(_kalem(nk, "K77", M_K77)))
    vaka("A2-K262-dosya-adi-kilitlemez%s" % ek, nk.KOVA_DAGITILABILIR,
         nk.kova_sec(_kalem(nk, "K262", M_K262)))

    # A3/A4 — NEGATIF KOL: jeton SERBEST metinde -> GERCEK mimar kati.
    vaka("A3-K70-serbest-kapi-kilitler%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(_kalem(nk, "K70", M_K70)))
    vaka("A4-K86-serbest-mutasyon-kilitler%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(_kalem(nk, "K86", M_K86)))

    # A5 — maskeleme YALNIZ maskeli bolgeyi siler, metnin kalanini DEGIL.
    vaka("A5-maske-serbest-metni-yemez%s" % ek, "VAR",
         "VAR" if "mandat" in nk._serbest_metin(M_K70.lower()) else "YOK")
    vaka("A6-maske-linki-siler%s" % ek, "YOK",
         "VAR" if "kapi-ozeti" in nk._serbest_metin(M_K77.lower()) else "YOK")
    vaka("A7-maske-kod-acikligini-siler%s" % ek, "YOK",
         "VAR" if "nobet-kapi.py" in nk._serbest_metin(M_K262.lower())
         else "YOK")

    # A8 — kat ekseni: arizi jetonlu kalem CANLI bir motora dusuyor.
    vaka("A8-K77-kat-canli%s" % ek, "CANLI",
         "CANLI" if nk.kat_sec(_kalem(nk, "K77", M_K77)) in canli
         else str(nk.kat_sec(_kalem(nk, "K77", M_K77))))


# ===========================================================================
# B — OKAN KAPISI (NEGATIF KONTROL, hukum 3)
# ===========================================================================

def bolum_b(nk, ek=""):
    print("--- BOLUM B%s: OKAN KAPISI DOKUNULMAZ ---" % ek)
    # B1 — `kime=Okan` sutunu: metin ne olursa olsun OKAN.
    vaka("B1-kime-okan%s" % ek, nk.KOVA_OKAN,
         nk.kova_sec(_kalem(nk, "K98", M_K98, kime="Okan")))
    vaka("B1b-kime-okan-kat%s" % ek, nk.KAT_OKAN,
         nk.kat_sec(_kalem(nk, "K98", M_K98, kime="Okan")))
    # B2 — Okan jetonu KOD ACIKLIGINDA: maskeleme Okan kapisini DARALTMAZ.
    vaka("B2-okan-jetonu-kod-acikliginda%s" % ek, nk.KOVA_OKAN,
         nk.kova_sec(_kalem(nk, "KX1", M_OKAN_KOD)))
    # B3 — insan kapisinda bekleyen (eskale) kalem dagitima GIRMEZ.
    dagitilmaz = tuple(nk.MERDIVEN.DAGITILMAZ_DURUMLAR)
    vaka("B3a-dagitilmaz-durum-var%s" % ek, "dolu",
         "dolu" if dagitilmaz else "BOS")
    gi = {"tur_no": 1, "kalemler": {"K77": {"id": "K77",
                                            "durum": dagitilmaz[0]}}}
    vaka("B3b-eskale-kalem-okan-kovasinda%s" % ek, nk.KOVA_OKAN,
         nk.kova_sec(_kalem(nk, "K77", M_K77), gi))
    # B3c — ayni kalem eskale DEGILSE dagitilabilir (kolun tekil oldugu kaniti).
    vaka("B3c-eskale-degilse-dagitilabilir%s" % ek, nk.KOVA_DAGITILABILIR,
         nk.kova_sec(_kalem(nk, "K77", M_K77), {"tur_no": 1, "kalemler": {}}))


# ===========================================================================
# C — EMEKLI KAT GOCU (hukum 1)
# ===========================================================================

def bolum_c(nk, ek=""):
    print("--- BOLUM C%s: EMEKLI KAT GOCU ---" % ek)
    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    emekli = tuple(nk.EMEKLI_ISCI_MOTORLARI)
    for i, motor in enumerate(emekli):
        vaka("C1-%d-emekli-%s-gocer%s" % (i, motor, ek), "CANLI",
             "CANLI" if nk._emekli_kat_gocur(motor) in canli
             else str(nk._emekli_kat_gocur(motor)))
    # C2 — insan katlari emekli OLMAZ, kapsam DISI.
    vaka("C2a-mimar-gocmez%s" % ek, nk.KAT_MIMAR,
         nk._emekli_kat_gocur(nk.KAT_MIMAR))
    vaka("C2b-okan-gocmez%s" % ek, nk.KAT_OKAN,
         nk._emekli_kat_gocur(nk.KAT_OKAN))
    # C3 — CANLI kat DEGISMEZ (goc yalniz emekliye uygulanir).
    vaka("C3-canli-kat-degismez%s" % ek, canli[0],
         nk._emekli_kat_gocur(canli[0]))
    # C4 — FAIL-CLOSED: EMEKLI kume BOS ise hicbir sey gocmez.
    eski = nk.EMEKLI_ISCI_MOTORLARI
    try:
        nk.EMEKLI_ISCI_MOTORLARI = ()
        vaka("C4-emekli-kume-bos-gocmez%s" % ek, emekli[0],
             nk._emekli_kat_gocur(emekli[0]))
    finally:
        nk.EMEKLI_ISCI_MOTORLARI = eski
    # C5 — hicbir kalem EMEKLI bir kata dusmez.
    ornekler = [_kalem(nk, "KA", M_K77), _kalem(nk, "KB", M_K262),
                _kalem(nk, "KC", M_K70), _kalem(nk, "KD", "tasima sayim isi")]
    dusen = [k["id"] for k in ornekler if nk.kat_sec(k) in emekli]
    vaka("C5-emekli-kata-dusen-kalem%s" % ek, 0, len(dusen))


# ===========================================================================
# D — UC KOVA PARTISYON + FAIL-CLOSED
# ===========================================================================

def bolum_d(nk, ek=""):
    print("--- BOLUM D%s: UC KOVA PARTISYONU ---" % ek)
    kalemler = [_kalem(nk, "K77", M_K77), _kalem(nk, "K262", M_K262),
                _kalem(nk, "K70", M_K70), _kalem(nk, "K86", M_K86),
                _kalem(nk, "K98", M_K98, kime="Okan")]
    dagilim = nk.kova_dagilimi(kalemler)
    toplam = sum(len(v) for v in dagilim.values())
    vaka("D1-kayip-yok%s" % ek, len(kalemler), toplam)
    vaka("D2-kova-sayisi%s" % ek, 3, len(dagilim))
    # Her kalem TAM BIR kovada.
    hepsi = [kid for v in dagilim.values() for kid in v]
    vaka("D3-mukerrer-yok%s" % ek, len(hepsi), len(set(hepsi)))
    vaka("D4-dagitilabilir%s" % ek, 2, len(dagilim[nk.KOVA_DAGITILABILIR]))
    vaka("D5-mimar-gercek%s" % ek, 2, len(dagilim[nk.KOVA_MIMAR_GERCEK]))
    vaka("D6-okan%s" % ek, 1, len(dagilim[nk.KOVA_OKAN]))
    # D7 — FAIL-CLOSED: kat kaynagi olculemediyse HICBIRI dagitilabilir degil.
    eski = nk.KAT_KAYNAGI_OLCULDU
    try:
        nk.KAT_KAYNAGI_OLCULDU = False
        d2 = nk.kova_dagilimi(kalemler)
        vaka("D7-kaynak-olculemedi-dagitim-yok%s" % ek, 0,
             len(d2[nk.KOVA_DAGITILABILIR]))
        vaka("D7b-hepsi-mimar%s" % ek, len(kalemler),
             len(d2[nk.KOVA_MIMAR_GERCEK]))
    finally:
        nk.KAT_KAYNAGI_OLCULDU = eski


# ===========================================================================
# F — HUKUM-1: EMEKLI ISCI KATINDAN GOCMUS KALEM MIMAR'A KILITLENMEZ
# ===========================================================================

# GERCEK kayit sekli (nobet-geri-iz.json, 24 Agu 2026):
#   "K49": {"durum":"BAYAT_GOC","motor":"kimi","kat":"kimi",
#           "eskalasyon_bayat":{"eski_motor":"codex",...},"dagitim_sayisi":3}
def _goc_izi(nk, kalem_id, eski_motor="codex", yeni_motor=None, damgali=True):
    yeni_motor = yeni_motor or nk.CANLI_ISCI_MOTORLARI[-1]
    kayit = {"id": kalem_id, "durum": "BAYAT_GOC", "motor": yeni_motor,
             "kat": yeni_motor, "dagitim_sayisi": 3, "tur": 269}
    if damgali:
        kayit["eskalasyon_bayat"] = {"eski_motor": eski_motor,
                                     "eski_durum": "ESKALASYON", "damga": "D"}
    return {"tur_no": 644, "kalemler": {kalem_id: kayit}}


def bolum_f(nk, ek=""):
    print("--- BOLUM F%s: HUKUM-1 (EMEKLI KATTAN GOC) ---" % ek)
    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    # K49 metni: "kilit"/"flock"/"fail-closed"/"kapisi" SERBEST metinde geciyor,
    # yani maskeleme onu KURTARMAZ — kurtaran YAPISAL goc izidir.
    k49 = _kalem(nk, "K49", M_K49)
    vaka("F0-metin-tek-basina-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(k49))
    gi = _goc_izi(nk, "K49")
    # F1 — YAPISAL goc izi VARSA kalem DAGITILABILIR.
    vaka("F1-goc-izi-dagitilabilir%s" % ek, nk.KOVA_DAGITILABILIR,
         nk.kova_sec(k49, gi))
    # F8 — ve gidecegi kat B4'un sectigi CANLI motordur (MIMAR DEGIL).
    vaka("F8-kat-canli-motor%s" % ek, canli[-1], nk.kat_sec(k49, gi))
    vaka("F8b-kat-mimar-degil%s" % ek, "DEGIL",
         "MIMAR" if nk.kat_sec(k49, gi) == nk.KAT_MIMAR else "DEGIL")

    # --- NEGATIF KOL: yuklem DAR mi? Her sarti AYRI AYRI dusur. ---
    # F2: geri-iz VERILMEDI -> geriye donuk uyum, kalem MIMAR'da kalir.
    vaka("F2-geri-iz-yok-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(k49, None))
    # F3: kayit VAR ama B4 goc damgasi YOK -> emekli kattan gelmemis.
    vaka("F3-damga-yok-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(k49, _goc_izi(nk, "K49", damgali=False)))
    # F4: eski motor EMEKLI kumede DEGIL -> gerekce emekli-ad DEGIL.
    vaka("F4-eski-motor-canli-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(k49, _goc_izi(nk, "K49", eski_motor=canli[0])))
    # F5: yeni motor CANLI DEGIL -> goc tamamlanmamis.
    vaka("F5-yeni-motor-emekli-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(k49, _goc_izi(nk, "K49", yeni_motor="codex")))
    # F6: BASKA kalemin goc izi BU kalemi kurtarmaz (id eslesmesi).
    vaka("F6-baska-id-kurtarmaz%s" % ek, nk.KOVA_MIMAR_GERCEK,
         nk.kova_sec(k49, _goc_izi(nk, "K999")))
    # F7 — 🔴 HUKUM 3: OKAN kalemi goc izi TASISA BILE dagitima GIRMEZ.
    k98 = _kalem(nk, "K98", M_K98, kime="Okan")
    vaka("F7-okan-goc-izine-ragmen%s" % ek, nk.KOVA_OKAN,
         nk.kova_sec(k98, _goc_izi(nk, "K98")))
    vaka("F7b-okan-kat-degismez%s" % ek, nk.KAT_OKAN,
         nk.kat_sec(k98, _goc_izi(nk, "K98")))
    # F9 — FAIL-CLOSED: EMEKLI kume OLCULEMEDIYSE goc yuklemi ATESLEMEZ.
    eski = nk.EMEKLI_ISCI_MOTORLARI
    try:
        nk.EMEKLI_ISCI_MOTORLARI = ()
        vaka("F9-emekli-kume-bos-mimar%s" % ek, nk.KOVA_MIMAR_GERCEK,
             nk.kova_sec(k49, gi))
    finally:
        nk.EMEKLI_ISCI_MOTORLARI = eski
    # F10 — insan kapisinda bekleyen kalem goc izine ragmen OKAN kovasinda.
    dagitilmaz = tuple(nk.MERDIVEN.DAGITILMAZ_DURUMLAR)
    gi_eskale = _goc_izi(nk, "K49")
    gi_eskale["kalemler"]["K49"]["durum"] = dagitilmaz[0]
    vaka("F10-eskale-goc-izine-ragmen%s" % ek, nk.KOVA_OKAN,
         nk.kova_sec(k49, gi_eskale))


# ===========================================================================
# E — CAGRI YERI ([[kapinin-menzili-cagri-yeridir]])
# ===========================================================================

def _cagri_var(kaynak, fonksiyon, aranan):
    try:
        agac = ast.parse(kaynak)
    except SyntaxError:
        return False
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == fonksiyon):
            continue
        for alt in ast.walk(dugum):
            if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                    and alt.func.id == aranan:
                return True
        return False
    return False


def bolum_e(yol, ek=""):
    print("--- BOLUM E%s: CAGRI YERI ---" % ek)
    with open(yol, encoding="utf-8") as d:
        kaynak = d.read()
    vaka("E1-tur-kova-cagiriyor%s" % ek, True,
         _cagri_var(kaynak, "tur_kapat", "kova_dagilimi"))
    vaka("E2-kat-sec-maskeyi-cagiriyor%s" % ek, True,
         _cagri_var(kaynak, "kat_sec", "_serbest_metin"))
    vaka("E3-kova-satiri-basiliyor%s" % ek, True,
         "K260_KOVA DAGITILABILIR=" in kaynak)
    # E4 — OKAN kapisi HAM metinde (maskeli metinde DEGIL): fail-closed kaniti.
    vaka("E4-okan-ham-metinde%s" % ek, True,
         "_jeton_var(ham, OKAN_JETONLARI)" in kaynak)
    # E5/E6 — hukum-1 DAGITIM KARARINA ulasiyor mu? (N4B kalintisi tam buydu:
    # goc kaydi tasindi ama karar EZILMEDI.)
    vaka("E5-fanout-geri-izi-goruyor%s" % ek, True,
         "kat_sec(k, geri_iz) == KAT_MIMAR" in kaynak)
    vaka("E6-dagitim-geri-izi-goruyor%s" % ek, True,
         "kat = kat_sec(kalem, geri_iz)" in kaynak)
    vaka("E7-basilan-kat-secilen-kat%s" % ek, True,
         'kalem["id"], kat_sec(kalem, geri_iz),' in kaynak)


# ===========================================================================
# CANLI OLCUM — gercek defter + gercek geri-iz
# ===========================================================================

def _eski_kat_sec(nk, kalem):
    """K260 ONCESI kural (TABAN olcumu icin DONDURULMUS kopya).

    Uretimde KULLANILMAZ; yalniz "bugunku kuyruk" sayisini olcmek icin var.
    Farki tek satir: jetonlar HAM metinde aranir, maskeleme YOK.
    """
    metin = ((kalem.get("is") or "") + " " +
             (kalem.get("durum_ham") or "")).lower()
    kime = (kalem.get("kime") or "").lower()
    if kime.startswith("okan") or nk._jeton_var(metin, nk.OKAN_JETONLARI):
        return nk.KAT_OKAN
    if nk._jeton_var(metin, nk.EMEKLI_MOTOR_JETONLARI):
        return nk.KAT_MIMAR
    if nk._jeton_var(metin, nk.PRO_JETONLARI):
        return nk.KAT_PRO
    if nk._jeton_var(metin, nk.FLASH_JETONLARI):
        return nk.KAT_FLASH
    return nk.VARSAYILAN_KAT


def canli_olcum(nk):
    print("--- CANLI OLCUM (gercek defter + gercek geri-iz) ---")
    with open(DEFTER_YOLU, encoding="utf-8") as d:
        kalemler = nk.onarim_kalemleri(nk.defter_ayristir(d.read()))
    try:
        with open(GERI_IZ, encoding="utf-8") as d:
            geri_iz = json.load(d)
    except (OSError, ValueError) as hata:
        print("GERI_IZ=OLCULEMEDI sebep=%s" % hata)
        geri_iz = {"kalemler": {}}
    eskale = set(nk.eskale_kalemler(geri_iz))
    ucusta = set(nk.ucusta_kalemler(geri_iz))

    # (i) ESKI kural: bugunku [DAGITILMAZ] kuyrugu.
    eski_dagitilmaz = [k for k in kalemler
                       if _eski_kat_sec(nk, k) in (nk.KAT_MIMAR, nk.KAT_OKAN)
                       or k["id"] in eskale]
    print("ESKI_DAGITILMAZ=%d KALEM=%s"
          % (len(eski_dagitilmaz),
             ",".join(sorted(k["id"] for k in eski_dagitilmaz))))
    for k in eski_dagitilmaz:
        print("  ESKI %s -> %s%s" % (k["id"], _eski_kat_sec(nk, k),
                                     " [ESKALE]" if k["id"] in eskale else ""))

    # (ii) YENI kural: ayni kuyruk UC KOVAYA ayrilir.
    dagilim = nk.kova_dagilimi(eski_dagitilmaz, geri_iz)
    toplam = sum(len(v) for v in dagilim.values())
    for ad in nk.KOVA_ADLARI:
        print("KOVA_%s=%d KALEM=%s"
              % (ad, len(dagilim[ad]), ",".join(sorted(dagilim[ad])) or "-"))
    print("KOVA_TOPLAM=%d ESKI_DAGITILMAZ=%d KAYIP=%d"
          % (toplam, len(eski_dagitilmaz), len(eski_dagitilmaz) - toplam))

    # (iii) TUM acik kalemler uzerinde partisyon (ikinci eksen).
    tum = nk.kova_dagilimi(kalemler, geri_iz)
    print("TUM_ACIK=%d TUM_DAGITILABILIR=%d TUM_MIMAR_GERCEK=%d TUM_OKAN=%d"
          % (len(kalemler), len(tum[nk.KOVA_DAGITILABILIR]),
             len(tum[nk.KOVA_MIMAR_GERCEK]), len(tum[nk.KOVA_OKAN])))
    print("UCUSTA=%d" % len(ucusta))
    print("K260_CANLI= DAGITILABILIR=%d MIMAR_KATI_GERCEK=%d OKAN_KAPISI=%d "
          "(toplam=%d)"
          % (len(dagilim[nk.KOVA_DAGITILABILIR]),
             len(dagilim[nk.KOVA_MIMAR_GERCEK]),
             len(dagilim[nk.KOVA_OKAN]), toplam))
    return 0 if toplam == len(eski_dagitilmaz) else 1


# ===========================================================================
# MUTASYON — GECICI KOPYAYA
# ===========================================================================

# (ad, eski, yeni, hedef vaka onekleri, kontrol mu?)
MUTANTLAR = (
    ("M1_MASKE_KALDIRILDI",
     "    metin = _serbest_metin(ham)\n",
     "    metin = ham\n",
     ("A1-", "A2-", "A6-", "A7-"), False),
    ("M2_MIMAR_KOVASI_DAGITILABILIRE_KAYDI",
     "    if kat == KAT_MIMAR:\n        return KOVA_MIMAR_GERCEK\n",
     "    if kat == KAT_MIMAR:\n        return KOVA_DAGITILABILIR\n",
     ("A3-", "A4-", "D5-"), False),
    ("M3_OKAN_KAPISI_KALDIRILDI",
     '    if kime.startswith("okan") or _jeton_var(ham, OKAN_JETONLARI):\n',
     "    if _jeton_var(ham, OKAN_JETONLARI):\n",
     ("B1-", "B1b-", "D6-", "F7-", "F7b-"), False),
    ("M4_EMEKLI_KAT_GOCU_KALDIRILDI",
     "    return canli_kata_goc(kat) or (\n",
     "    return kat or (\n",
     ("C1-",), False),
    ("M5_HUKUM1_YAPISAL_GOC_KALDIRILDI",
     "        if _emekli_kattan_gocmus(kalem, geri_iz):\n"
     "            return _gocmus_kat(kalem, geri_iz)\n",
     "        if False:\n            return _gocmus_kat(kalem, geri_iz)\n",
     ("F1-", "F8-", "F8b-"), False),
    ("M6_GOC_YUKLEMI_GENISLEDI_EMEKLI_SARTI_DUSTU",
     "    if damga.get(\"eski_motor\") not in EMEKLI_ISCI_MOTORLARI:\n"
     "        return False\n",
     "    if damga.get(\"eski_motor\") is None:\n        return False\n",
     ("F4-",), False),
    ("K0_KONTROL_ILGISIZ_KOL",
     "    if _jeton_var(metin, FLASH_JETONLARI):\n"
     "        return _emekli_kat_gocur(KAT_FLASH)\n",
     "    if False:\n        return _emekli_kat_gocur(KAT_FLASH)\n",
     (), True),
)


def _batarya(nk, yol, ek):
    del VAKALAR[:]
    bolum_a(nk, ek)
    bolum_b(nk, ek)
    bolum_c(nk, ek)
    bolum_d(nk, ek)
    bolum_f(nk, ek)
    bolum_e(yol, ek)
    return list(VAKALAR)


def mutasyon():
    print("=== K260 MUTASYON BATARYASI (GECICI KOPYA) ===")
    with open(NOBET_KAPI, encoding="utf-8") as d:
        taban_kaynak = d.read()
    gecici = tempfile.mkdtemp(prefix="k260-mut-")
    try:
        # TABAN: mutasyonsuz kopya YESIL olmali (harness saglam mi?).
        taban_yol = os.path.join(gecici, "nobet_kapi_taban.py")
        shutil.copy2(NOBET_KAPI, taban_yol)
        taban = _batarya(modul_yukle(taban_yol), taban_yol, "-taban")
        taban_dusen = [v[0] for v in taban if not v[3]]
        print("TABAN_IDDIA=%d TABAN_DUSEN=%d" % (len(taban), len(taban_dusen)))
        if taban_dusen:
            print("HARNESS=BAYAT dusen=%s" % ",".join(taban_dusen))
            print("HUKUM=OLCULEMEDI sebep=taban_kirmizi")
            return 2

        oldu = 0
        hedefli = 0
        kontrol_yesil = True
        for ad, eski, yeni, hedefler, kontrol_mu in MUTANTLAR:
            if taban_kaynak.count(eski) != 1:
                print("MUTANT=%-40s DURUM=CAPA_YOK sayi=%d (OLCULEMEDI)"
                      % (ad, taban_kaynak.count(eski)))
                continue
            yol = os.path.join(gecici, "nk_%s.py" % ad.lower())
            with open(yol, "w", encoding="utf-8") as d:
                d.write(taban_kaynak.replace(eski, yeni, 1))
            try:
                mod = modul_yukle(yol)
                sonuc = _batarya(mod, yol, "-" + ad)
                dusen = [v[0] for v in sonuc if not v[3]]
            except Exception as hata:            # noqa: BLE001
                dusen = ["YUKLENEMEDI:%s" % type(hata).__name__]
            if kontrol_mu:
                # KONTROL: ilgisiz kol bozulunca kovalar AYAKTA kalmali.
                yesil = not dusen
                kontrol_yesil = kontrol_yesil and yesil
                print("MUTANT=%-40s KONTROL SONUC=%s dusen=%s"
                      % (ad, "YESIL" if yesil else "KIRMIZI",
                         ",".join(dusen) or "-"))
                continue
            # HEDEF-KOL ATFI: mutant KENDI hedefini oldurmus mu?
            hedef_dusen = [v for v in dusen
                           if any(v.startswith(h) for h in hedefler)]
            oldurdu = bool(hedef_dusen)
            oldu += 1 if oldurdu else 0
            hedefli += 1
            print("MUTANT=%-40s SONUC=%s hedef_dusen=%s tum_dusen=%d"
                  % (ad, "OLDU" if oldurdu else "HAYATTA(OLCULEMEDI)",
                     ",".join(hedef_dusen) or "-", len(dusen)))
        print("MUTANT=%d/%d" % (oldu, hedefli))
        print("KONTROL=%s" % ("YESIL" if kontrol_yesil else "KIRMIZI"))
        print("HUKUM=%s" % ("YESIL" if oldu == hedefli and kontrol_yesil
                            else "KIRMIZI"))
        return 0 if (oldu == hedefli and kontrol_yesil) else 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        print("TEMIZLIK=%s silindi" % gecici)


def kabul():
    print("=== K260 KABUL BATARYASI ===")
    nk = modul_yukle(NOBET_KAPI)
    sonuc = _batarya(nk, NOBET_KAPI, "")
    dusen = [v[0] for v in sonuc if not v[3]]
    print("IDDIA=%d GECTI=%d KALDI=%d" % (len(sonuc), len(sonuc) - len(dusen),
                                          len(dusen)))
    if dusen:
        print("KALAN=%s" % ",".join(dusen))
    print("HUKUM=%s" % ("YESIL" if not dusen else "KIRMIZI"))
    return 0 if not dusen else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="K260 kat kovasi bataryasi")
    ap.add_argument("--mutasyon", action="store_true")
    ap.add_argument("--canli", action="store_true")
    args = ap.parse_args(argv)
    if args.mutasyon:
        return mutasyon()
    if args.canli:
        return canli_olcum(modul_yukle(NOBET_KAPI))
    return kabul()


if __name__ == "__main__":
    sys.exit(main())
