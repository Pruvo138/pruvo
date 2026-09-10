#!/usr/bin/env python3
"""KABUL/REGRESYON — `thing-icerik.py` PORTU (emekli CLI -> CANLI uc, 10 Eyl 2026, K399).

NE OLCULUR: portun K398 UC KOLUNU sag getirip getirmedigi. Kollar tasiyici degisince
sessizce tek kola cokebilir; bu dosya her kolu AYRI AYRI, digerlerini KOR birakan bir
vakayla yargilar. Bir kol tek basina tutamiyorsa vaka KIRMIZI yanar.

  kol-1 "durum" : HTTP durum kodu 200 mu           (eski hatta alt surec rc'si)
  kol-2 "yazildi": cikti dosyasi bu DENEMEDE yazildi mi
  kol-3 "govde" : HAM yanitta API hata izi var mi  (durum koduna BAKMAZ)

VAKA TASARIMI (her vakada diger iki kol BILEREK yaniltilir):
  V1 yalniz kol-1 tutabilir : durum=500, temiz govde, arac blogu VAR   -> BASARISIZ olmali
  V2 yalniz kol-2 tutabilir : durum=200, temiz govde, arac blogu YOK   -> BASARISIZ olmali
  V3 yalniz kol-3 tutabilir : durum=200, HATA govdesi, arac blogu VAR  -> BASARISIZ olmali
  V4 yalniz kol-3 (ic-bant) : durum=200, base_resp.status_code!=0      -> BASARISIZ olmali
  V5 BAYAT KAPISI           : onceki kosumdan KALAN dosya + arac blogu YOK -> BASARISIZ
  V6 POZITIF KONTROL        : durum=200, temiz, arac blogu VAR         -> BASARILI + icerik

AG YOK: `_uc_istek` (ag dikisi) ve `_uc_ayari` (uc tablosu) sahtelenir. Test bu yuzden
kosucunun diskine/anahtarina BAGLI DEGILDIR
([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]]).

Kosum:  python3 tools/thing-icerik-port-kabul.py            (vakalar)
        python3 tools/thing-icerik-port-kabul.py --mutasyon (izole golge batarya)
# CI-ALT-KUME: --mutasyon
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(DIR)
FAILS = []


def _chk(ad, kosul, ayrinti=""):
    print(("  ok  " if kosul else "  HATA ") + ad + (("  [%s]" % ayrinti) if not kosul and ayrinti else ""))
    if not kosul:
        FAILS.append(ad)


def _yukle():
    yol = os.path.join(DIR, "thing-icerik.py")
    spec = importlib.util.spec_from_file_location("thing_icerik_port", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(yol):
    return hashlib.sha256(open(yol, "rb").read()).hexdigest()


# Uc ayari SAHTE: gercek tablo/anahtar kosucunun diskinde OLABILIR DE OLMAYABILIR DE.
SAHTE_UC = ("https://ornek.gecersiz/anthropic", "/yok/boyle/bir/anahtar", "SAHTE-MODEL")

# SEMA'nin TUM zorunlu alanlarini tasiyan GECERLI yuk.
TEMIZ_ICERIK = {"sec_gorseller": ["g1.jpg"], "elenen": [], "baslik": "Test Parca",
                "aciklama": "test aciklama", "kategori": "Otomobil", "marka": [],
                "fiyat_oneri": "300 TL", "not": "stub"}


def _yanit(arac_adi, arac_var=True, hata=False, ic_bant=False,
           metin=None, icerik=None):
    """Uc yanitini kurar.

    `arac_var`  -> tool_use blogu (cikti YAZILIR; kol-2 yanilir)
    `metin`     -> METIN blogu (ucun OLCULEN kararsiz davranisi: ayni JSON'u
                   arac yerine duz metin olarak dondurur)"""
    d = {"id": "x", "type": "message", "role": "assistant", "content": []}
    if arac_var:
        d["content"].append({"type": "tool_use", "id": "t1", "name": arac_adi,
                             "input": TEMIZ_ICERIK if icerik is None else icerik})
    if metin is not None:
        d["content"].append({"type": "text", "text": metin})
    if hata:
        d["error"] = {"type": "invalid_request_error", "message": "model not supported"}
    d["base_resp"] = {"status_code": 1004 if ic_bant else 0, "status_msg": ""}
    return json.dumps(d)


def _kos(tc, durum, ham, bayat=None):
    """motor_cagir'i SAHTE uc ile kosar; (ok, hata, cikti_var, icerik) doner."""
    tmp = tempfile.mkdtemp(prefix="ti-port-")
    try:
        cikti = os.path.join(tmp, "oneri.json")
        if bayat is not None:
            with open(cikti, "w", encoding="utf-8") as f:
                json.dump(bayat, f)
        g_istek, g_ayar = tc._uc_istek, tc._uc_ayari
        tc._uc_istek, tc._uc_ayari = (lambda govde: (durum, ham)), (lambda: SAHTE_UC)
        try:
            ok, hata = tc.motor_cagir("prompt", [], cikti)
        finally:
            tc._uc_istek, tc._uc_ayari = g_istek, g_ayar
        var = os.path.exists(cikti)
        icerik = json.load(open(cikti)) if var else None
        return ok, hata, var, icerik
    finally:
        # Yalniz BU turun tempfile dizini; gercek ev yolu bu yukte GECMEZ.
        shutil.rmtree(tmp, ignore_errors=True)


def vakalar():
    tc = _yukle()
    A = tc.ARAC_ADI
    print("=== PORT KABUL: K398 UC KOLU (her vakada digerleri KOR) ===")

    # --- V1: yalniz kol-1 (durum) tutabilir --------------------------------
    ok, hata, var, _ = _kos(tc, 500, _yanit(A, arac_var=True))
    _chk("V1 durum=500 + TEMIZ govde + cikti YAZILDI -> BASARISIZ (kol-1 tek basina tuttu)",
         ok is False, "ok=%r hata=%r" % (ok, (hata or "")[:80]))
    _chk("V1 basarisiz turda hata metni durumu ADIYLA tasir", "durum=500" in (hata or ""),
         repr(hata)[:100])

    # --- V2: yalniz kol-2 (yazildi) tutabilir ------------------------------
    ok, hata, var, _ = _kos(tc, 200, _yanit(A, arac_var=False))
    _chk("V2 durum=200 + TEMIZ govde + arac blogu YOK -> BASARISIZ (kol-2 tek basina tuttu)",
         ok is False, "ok=%r" % ok)
    _chk("V2 cikti dosyasi ORTADA YOK", var is False)

    # --- V3: yalniz kol-3 (hata govdesi) tutabilir -------------------------
    ok, hata, var, _ = _kos(tc, 200, _yanit(A, arac_var=True, hata=True))
    _chk("V3 durum=200 + cikti YAZILDI + HATA govdesi -> BASARISIZ (kol-3 tek basina tuttu)",
         ok is False, "ok=%r" % ok)
    _chk("V3 hata metni API govdesini ADIYLA tasir",
         "invalid_request_error" in (hata or ""), repr(hata)[:100])
    _chk("V3 hata govdesi varken YAZILMIS cikti SILINIR (bayat kanit birakma)", var is False)

    # --- V4: ic-bant hata kanali (200 ile gelir) ---------------------------
    ok, hata, var, _ = _kos(tc, 200, _yanit(A, arac_var=True, ic_bant=True))
    _chk("V4 durum=200 + ic-bant status_code!=0 -> BASARISIZ (fail-open kapatildi)",
         ok is False, "ok=%r" % ok)
    _chk("V4 ic-bant hatada da cikti SILINIR", var is False)

    # --- V5: BAYAT CIKTI KAPISI -------------------------------------------
    # Onceki kosumdan KALAN dosya vardir; bu denemede arac blogu GELMEZ. Kapi
    # calisiyorsa dosya cagridan ONCE silinir -> kol-2 tutar. Kapi sokulurse
    # bayat dosya "bu kosumun kaniti" sayilir ve hat SAHTE YESIL doner.
    ok, hata, var, icerik = _kos(tc, 200, _yanit(A, arac_var=False),
                                 bayat={"baslik": "BAYAT-ONCEKI-KOSUM"})
    _chk("V5 BAYAT dosya bu kosumun kaniti SAYILMAZ -> BASARISIZ", ok is False, "ok=%r" % ok)
    _chk("V5 bayat icerik SIZMADI (dosya ortada yok)", var is False,
         repr(icerik)[:80])

    # --- V6: POZITIF KONTROL ----------------------------------------------
    ok, hata, var, icerik = _kos(tc, 200, _yanit(A, arac_var=True))
    _chk("V6 durum=200 + TEMIZ + arac blogu -> BASARILI", ok is True, "ok=%r hata=%r" % (ok, hata))
    _chk("V6 semali icerik cikti dosyasina AYNEN yazildi", icerik == TEMIZ_ICERIK, repr(icerik)[:120])

    # --- V7..V10: SEMA SOZLESMESI YEREL KAPIDA ----------------------------
    # OLCULEN: bu ucta `tool_choice` zorlamasi KARARSIZ (7 cagrinin 5'i arac yerine
    # METIN dondu). Metin yolu bir GEVSEKLIK OLMAMALI: ayni sozlesmeden gecmeli.
    ok, hata, var, icerik = _kos(tc, 200, _yanit(A, arac_var=False,
                                                 metin=json.dumps(TEMIZ_ICERIK)))
    _chk("V7 arac blogu YOK ama METIN gecerli JSON -> BASARILI (ikinci tasiyici)",
         ok is True, "hata=%r" % (hata or "")[:80])
    _chk("V7 metin yolundan gelen icerik AYNEN yazildi", icerik == TEMIZ_ICERIK)

    ok, _, var, _ = _kos(tc, 200, _yanit(A, arac_var=False,
                                         metin="```json\n" + json.dumps(TEMIZ_ICERIK) + "\n```"))
    _chk("V8 markdown citli METIN de ayristirilir", ok is True)

    eksik = dict(TEMIZ_ICERIK)
    del eksik["kategori"]
    ok, _, var, _ = _kos(tc, 200, _yanit(A, arac_var=False, metin=json.dumps(eksik)))
    _chk("V9 METIN yolunda ZORUNLU alan eksikse REDDEDILIR (fail-closed)",
         ok is False and var is False, "ok=%r var=%r" % (ok, var))

    kirli = dict(TEMIZ_ICERIK, kategori="Uzay Mekigi")
    ok, _, var, _ = _kos(tc, 200, _yanit(A, arac_var=True, icerik=kirli))
    _chk("V10 ARAC yolunda liste-disi kategori de REDDEDILIR (uzak uca guvenilmez)",
         ok is False and var is False, "ok=%r var=%r" % (ok, var))

    _chk("V10b sema_ihlali temiz yuke YANLIS-POZITIF vermez",
         tc.sema_ihlali(TEMIZ_ICERIK) is None, repr(tc.sema_ihlali(TEMIZ_ICERIK)))

    # --- Turetim kollari ---------------------------------------------------
    print("=== TURETIM: motor adi/uc tablosu ELLE YAZILMADI ===")
    govde = open(os.path.join(DIR, "thing-icerik.py"), encoding="utf-8").read()
    mk = os.path.join(DIR, "mimar_kimlik.py")
    spec = importlib.util.spec_from_file_location("mk_port", mk)
    mkm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mkm)
    canli = tuple(mkm.CANLI_ISCI_MOTORLARI)
    _chk("motor adi kanonik CANLI kumeden TURETILDI", tc.CANLI_MOTOR == canli[0],
         "%r vs %r" % (tc.CANLI_MOTOR, canli))
    _chk("CANLI motor adi gövdede LITERAL dizge olarak GECMIYOR",
         tc.CANLI_MOTOR not in govde, tc.CANLI_MOTOR)
    for emekli in tuple(mkm.EMEKLI_ISCI_MOTORLARI):
        _chk("EMEKLI motor '%s' CAGRI YOLUNDA degil" % emekli,
             tc.CANLI_MOTOR != emekli)
    _chk("emekli model sabiti ('gpt-') gövdeden KALKTI", "gpt-" not in govde)
    _chk("uc tablosu TEK KAYNAK (ikinci base_url listesi acilmadi)",
         govde.count("https://") == 0 or "UC_TABLOSU" in govde)


# =============================================================================
# MUTASYON BATARYASI — IZOLE golge agac (CANLI govde ASLA degistirilmez)
# =============================================================================
# Her giris: (ad, eski, yeni, oldurucu_mu, HEDEF KOL ATFI)
MUTANTLAR = [
    ("MA kol-1 (durum) SOKULDU",
     "if durum == 200 and os.path.exists(cikti_yolu) and govde is None:",
     "if os.path.exists(cikti_yolu) and govde is None:",
     True,
     "V1: uc 500 doner, govde temiz, dosya yazilmis -> hat SAHTE YESIL doner"),
    ("MB kol-3 (hata govdesi) SOKULDU",
     "if durum == 200 and os.path.exists(cikti_yolu) and govde is None:",
     "if durum == 200 and os.path.exists(cikti_yolu):",
     True,
     "V3/V4: 200 ile gelen API hatasi SESSIZCE basarili sayilir (K398 fail-open)"),
    ("MC bayat-cikti unlink SOKULDU",
     "        if os.path.exists(cikti_yolu):\n            os.unlink(cikti_yolu)",
     "        if False:\n            os.unlink(cikti_yolu)",
     True,
     "V5: onceki kosumdan kalan oneri.json BU kosumun kaniti sayilir"),
    ("MD yerel SEMA dogrulayici SOKULDU",
     "    if icerik is None or sema_ihlali(icerik) is not None:",
     "    if icerik is None:",
     True,
     "V9/V10: eksik alanli / liste-disi kategorili cikti sessizce gecer -> urunler.json'a iner"),
    ("ME KONTROL — yalniz serbest metin", "token diyeti", "jeton diyeti", False,
     "hicbir iddia bu metne capalanmamali; kirmizi yanarsa batarya BATTANIYE kirmizidir"),
]


def _golge_agac():
    """Depo kokunun symlink golgesi; yalniz `tools/` gercek dizin olarak kurulur.

    TUM kok tasinir (tek dosya DEGIL): `kategori-kapisi.py` kok dizindeki index.html'i
    okur ve modul kendi dizinini sys.path'e koyar
    ([[pythonpath-mutanti-modulun-kendi-syspath-insertiyle-olur]])."""
    golge = tempfile.mkdtemp(prefix="ti-port-golge-")
    for ad in os.listdir(KOK):
        if ad == "tools":
            continue
        os.symlink(os.path.join(KOK, ad), os.path.join(golge, ad))
    hedef = os.path.join(golge, "tools")
    os.mkdir(hedef)
    for ad in os.listdir(DIR):
        os.symlink(os.path.join(DIR, ad), os.path.join(hedef, ad))
    return golge, hedef


def _golgede_kos(hedef):
    return subprocess.run(
        [sys.executable, os.path.join(hedef, os.path.basename(__file__))],
        capture_output=True, text=True)


def mutasyon_bataryasi():
    print("\n=== MUTASYON BATARYASI (izole golge agac) ===")
    onceki = _sha(os.path.join(DIR, "thing-icerik.py"))

    # 🔴 TABAN KOLU ONCE: mutasyonsuz golge YESIL degilse her mutant "oldu" gorunur
    # ve batarya HICBIR SEY olcmez ([[taban-kirmizisi-nobetciyi-susturur]]).
    golge, hedef = _golge_agac()
    try:
        taban = _golgede_kos(hedef)
        _chk("TABAN: mutasyonsuz golge agac YESIL", taban.returncode == 0,
             (taban.stderr or taban.stdout or "")[-300:])
        if taban.returncode != 0:
            print("  -> TABAN KIRMIZI: mutantlar KOSULMADI (olcum YAPILAMADI).")
            return
    finally:
        shutil.rmtree(golge, ignore_errors=True)

    oldu = kontrol_yesil = 0
    for ad, eski, yeni, oldurucu, atif in MUTANTLAR:
        golge, hedef = _golge_agac()
        try:
            kaynak = os.path.join(DIR, "thing-icerik.py")
            govde = open(kaynak, encoding="utf-8").read()
            if eski not in govde:
                print("  KALDI  %s -> CAPA BULUNAMADI (mutant hedefe ULASMADI)" % ad)
                FAILS.append(ad + " (capa yok)")
                continue
            os.unlink(os.path.join(hedef, "thing-icerik.py"))
            with open(os.path.join(hedef, "thing-icerik.py"), "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni, 1))
            r = _golgede_kos(hedef)
            kirmizi = r.returncode != 0
            if oldurucu and kirmizi:
                oldu += 1
                print("  ok  %s -> OLDU (kirmizi)  | %s" % (ad, atif))
            elif oldurucu:
                print("  KALDI  %s -> HAYATTA (yesil kaldi!)  | %s" % (ad, atif))
                FAILS.append(ad + " HAYATTA")
            elif not kirmizi:
                kontrol_yesil += 1
                print("  ok  %s -> KONTROL yesil kaldi  | %s" % (ad, atif))
            else:
                print("  KALDI  %s -> KONTROL KIRMIZI (battaniye kirmizi!)" % ad)
                FAILS.append(ad + " KONTROL kirmizi")
        finally:
            shutil.rmtree(golge, ignore_errors=True)

    print("  OLDURUCU oldu: %d/%d · KONTROL yesil: %d"
          % (oldu, sum(1 for m in MUTANTLAR if m[3]), kontrol_yesil))
    _chk("CANLI GOVDE sha256 ONCE == SONRA: thing-icerik.py",
         _sha(os.path.join(DIR, "thing-icerik.py")) == onceki)


def main():
    vakalar()
    if "--mutasyon" in sys.argv:
        mutasyon_bataryasi()
    print()
    if FAILS:
        print("KIRMIZI: %d kontrol DUSTU" % len(FAILS))
        for f in FAILS:
            print("   - " + f)
        sys.exit(1)
    print("YESIL: tum kontroller gecti")


if __name__ == "__main__":
    main()
