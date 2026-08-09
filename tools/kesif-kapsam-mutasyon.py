#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — CI KAPSAM KAPISININ **KESIF** EKSENI GERCEKTEN OLCUYOR MU (8 Agu 2026).

    python3 tools/kesif-kapsam-mutasyon.py

NEDEN VAR (OLCULEN ACIK)
────────────────────────
`tools/ci-kapsam-test.py` kesif predikati `*-test.py` / `test-*.py` / `*-kapisi.py`
ariyordu; `*-mutasyon.py` bu desene GIRMIYORDU. Envanter (8 Agu 2026, `git ls-files`):
    43 mutasyon surucusu · 8'i OTOMATIK is akisinda kosuyor · 35'i kosmuyor
    kosmayanlarin 31'i kesif predikatinin HIC gormedigi dosyalardi
Iki yonlu bedel olculdu:
  (a) Kosmayan surucu CURUYUNCE kimse duymuyor — ZATEN CURUMUS iki ornek temiz
      checkout'ta rc=1: `tools/d1-sapma-mutasyon.py` (capa bulunamiyor) ve
      `tools/gecmis-geri-donus-mutasyon.py` (kendi raporunda "arac bayat").
  (b) KOSAN iki surucu (`tools/varlik-mutasyon.py` deploy.yml, `tools/yayin-sinyali-
      mutasyon.py` nobet.yml) kesif disi oldugu icin RATCHET'SIZDI: cagri satirlari
      silinse kapi UYARMAZDI. Sinif: [[nobetci-cagri-satiri-nobetsiz]].

BU BATARYA NE ISPATLAR
──────────────────────
Kesif genislemesinin "kagit uzerinde" degil HUKUMDE yasadigini. Her mutant TEK BASINA
kirmizi yakmali; kontrol mutantlari YESIL kalmali.

🔴 KABUL = OLCULEN IDDIA + ISARET, cikis kodu DEGIL: bir mutant COKERSE (istisna)
kirmizi SAYILMAZ ([[mutasyon-kaniti-yeniden-uretilebilir]]). Her oldurucu mutant
BEKLENEN TANI PARCASINI da bastirmak zorundadir.

🔴 IKI YONLU: yalniz "daraltma" (mutasyon surucusu dusurulur) degil, "gevsetme"
(predikat jokerlesir) de olculur. Tek yonlu nobetci olu nobetcidir — bir kapiyi
`^tools/.*$` yapmak da kapsam kapisini islevsiz kilar.

CANLI DOSYALARA DOKUNULMAZ: her mutasyon BELLEKTE (modul sabiti / metin kopyasi)
uygulanir ve hemen geri alinir; kosum sonunda kaynak dosyalarin sha256'si
karsilastirilir ([[mutasyon-diske-yazma-tuzagi]]).
"""
import hashlib
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_YOLU = os.path.join(TOOLS, "ci-kapsam-test.py")
NOBET_YOLU = os.path.join(ROOT, ".github", "workflows", "nobet.yml")
DEPLOY_YOLU = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
KANCA_YOLU = os.path.join(TOOLS, "kancalar", "pre-push")
DOKUNULMAZ = (KAPI_YOLU, NOBET_YOLU, DEPLOY_YOLU, KANCA_YOLU)

# 8 Agu 2026 ONCESI kesif predikati (mutasyon kolu YOK) — M1'in tabani.
ESKI_TOOLS_PAT = re.compile(
    r"^tools/([^/]*-test\.(?:py|js)|test-[^/]*\.(?:py|js)|[^/]*-kapisi\.py)$")


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kapi_modulu():
    spec = importlib.util.spec_from_file_location("_ci_kapsam", KAPI_YOLU)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ci_kapsam"] = mod
    spec.loader.exec_module(mod)
    return mod


KAP = _kapi_modulu()


def _yeni_yakalananlar():
    """Kesif genislemesinin GETIRDIGI dosyalar (yeni kume - eski kume)."""
    eski = set()
    yeni = set(KAP.kesfet())
    r = KAP.subprocess.run(["git", "-C", ROOT, "ls-files"],
                           capture_output=True, text=True)
    for yol in r.stdout.splitlines():
        if yol.startswith("tools/arsiv/"):
            continue
        if ESKI_TOOLS_PAT.match(yol) or KAP.DIR_PAT.match(yol) or yol in KAP.ACIK_KESIF:
            eski.add(yol)
    return eski, yeni


def _denetle(kesif, izin, akislar):
    """kontroller=False: bu batarya KESIF eksenini olcer; kapinin OTEKI oz-nobetcileri
    (bulgu1/muaf/suzgec ...) GERCEK dosyalari okur ve mutasyondan ETKILENMEZ — onlari
    her mutantta yeniden kosturmak sadece sureyi buyutur ve kirmiziyi BULANIKLASTIRIR
    ([[beyan-edilmis-survivor]]: kirmizi TEK eksenden gelmeli)."""
    with open(DEPLOY_YOLU, encoding="utf-8") as f:
        deploy_metin = f.read()
    return KAP.denetle(deploy_metin, kesif, izin, kontroller=False, akislar=akislar)


def _akislari_al():
    return KAP.is_akislari()


def _akis_satiri_sil(akislar, akis_adi, kapi_yolu):
    """<akis_adi> metninden <kapi_yolu>'nu KOSAN icra satirlarini siler (BELLEKTE)."""
    yeni, silinen = [], 0
    for yol, metin, sinif in akislar:
        if os.path.basename(yol) == akis_adi:
            mutant, n = KAP._silme_mutanti(metin, kapi_yolu)
            silinen = n
            yeni.append((yol, mutant, sinif))
        else:
            yeni.append((yol, metin, sinif))
    return yeni, silinen


def _mutant_modul(ad, eski, yeni, beklenen_adet=1):
    """KAYNAK METNI BELLEKTE mutasyona ugratip AYRI bir modul olarak yukler.

    🔴 DISKE YAZILMAZ ([[mutasyon-diske-yazma-tuzagi]]): dosya okunur, string
    uzerinde degistirilir, `compile`+`exec` ile taze bir modul nesnesine kosulur.
    Kosum sonunda ana main() zaten KAPI_YOLU'nun sha256'sini karsilastirir.
    🔴 BYTECODE ONBELLEGI DEVRE DISI: kaynak diskten degil string'den derlenir, bu
    yuzden ayni saniyede/ayni uzunlukta mutasyon tuzagi ([[mutasyon-bytecode-
    onbellegi]]) bu kolda OLUSAMAZ.
    🔴 CAPA SAYISI DOGRULANIR: capa kaynakta beklenen adette gecmiyorsa mutasyon
    UYGULANMAMIS demektir -> RuntimeError (olc() bunu COKME sayar, KIRMIZI DEGIL).
    """
    with open(KAPI_YOLU, encoding="utf-8") as f:
        kaynak = f.read()
    adet = kaynak.count(eski)
    if adet != beklenen_adet:
        raise RuntimeError(
            "%s OLCULEMEDI: capa kaynakta %d kez gecti (beklenen %d) -> mutasyon "
            "UYGULANMADI; kirmizi/yesil hukmu ANLAMSIZ olurdu" % (ad, adet, beklenen_adet))
    mutant_kaynak = kaynak.replace(eski, yeni)
    mod = types.ModuleType("_ci_kapsam_mutant_%s" % ad)
    mod.__file__ = KAPI_YOLU
    exec(compile(mutant_kaynak, "%s#%s" % (KAPI_YOLU, ad), "exec"), mod.__dict__)
    return mod


def _iz_fikstur(mod):
    """<mod>.izlenmeyen_fikstur_kontrol() -> olc() sozlesmesine (kod, satirlar)."""
    ok, hatalar = mod.izlenmeyen_fikstur_kontrol()
    return (0 if ok else 1), hatalar


def _kablo_fikstur(mod):
    """<mod>.main_kablosu_kontrol() -> olc() sozlesmesine (kod, satirlar)."""
    ok, hatalar = mod.main_kablosu_kontrol()
    return (0 if ok else 1), hatalar


PRE_PUSH_YOLU = os.path.join(TOOLS, "kancalar", "pre-push")


def _pp_mutant(capa, ikame, ek=None):
    """pre-push govdesini GECICI bir kopyada mutasyona ugratip hukmu olcer.

    🔴 IZLENEN KANCA KAYNAGINA DOKUNULMAZ: mutant `tempfile` dizinine yazilir ve
    modulun `PRE_PUSH_YOLU` sabiti gecici olarak oraya cevrilir. Kosum sonunda
    main() zaten kanca kaynaginin sha256'sini karsilastirir."""
    with open(PRE_PUSH_YOLU, encoding="utf-8") as f:
        govde = f.read()
    if capa is not None:
        adet = govde.count(capa)
        if adet != 1:
            raise RuntimeError("PRE-PUSH MUTANTI OLCULEMEDI: capa %d kez gecti "
                               "(beklenen 1) -> mutasyon UYGULANMADI" % adet)
        govde = govde.replace(capa, ikame)
    else:
        govde = govde + ikame
    if ek is not None:
        ek_capa, ek_ikame = ek
        if govde.count(ek_capa) != 1:
            raise RuntimeError("PRE-PUSH EK MUTANTI OLCULEMEDI: capa %d kez gecti "
                               "(beklenen 1)" % govde.count(ek_capa))
        govde = govde.replace(ek_capa, ek_ikame)
    gecici = tempfile.mkdtemp(prefix="pruvo-pp-mutant-")
    try:
        yol = os.path.join(gecici, "pre-push")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(govde)
        eski = KAP.PRE_PUSH_YOLU
        KAP.PRE_PUSH_YOLU = yol
        try:
            ok, hatalar = KAP.pre_push_kablo_kontrol()
        finally:
            KAP.PRE_PUSH_YOLU = eski
        return (0 if ok else 1), hatalar
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _serit_mutant(capa, ikame, ek=None):
    """deploy.yml'i GECICI kopyada mutasyona ugratip SERIT hukmunu olcer.

    🔴 IZLENEN deploy.yml'e DOKUNULMAZ: mutant tempfile'a yazilir ve modulun
    `DEPLOY_VARSAYILAN` sabiti gecici olarak oraya cevrilir."""
    with open(DEPLOY_YOLU, encoding="utf-8") as f:
        metin = f.read()
    for c, i in [(capa, ikame)] + ([ek] if ek else []):
        if metin.count(c) != 1:
            raise RuntimeError("SERIT MUTANTI OLCULEMEDI: capa %r %d kez gecti "
                               "(beklenen 1)" % (c[:50], metin.count(c)))
        metin = metin.replace(c, i)
    gecici = tempfile.mkdtemp(prefix="pruvo-serit-mutant-")
    try:
        yol = os.path.join(gecici, "deploy.yml")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
        eski = KAP.DEPLOY_VARSAYILAN
        KAP.DEPLOY_VARSAYILAN = yol
        try:
            ok, hatalar = KAP.kanca_kablo_serit_kontrol()
        finally:
            KAP.DEPLOY_VARSAYILAN = eski
        return (0 if ok else 1), hatalar
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _adim_mutant(capa, ikame):
    """deploy.yml GECICI kopyasinda `--kanca-kablo` ADIMI nobetini olcer."""
    with open(DEPLOY_YOLU, encoding="utf-8") as f:
        metin = f.read()
    if metin.count(capa) != 1:
        raise RuntimeError("ADIM MUTANTI OLCULEMEDI: capa %d kez gecti (beklenen 1)"
                           % metin.count(capa))
    metin = metin.replace(capa, ikame)
    gecici = tempfile.mkdtemp(prefix="pruvo-adim-mutant-")
    try:
        yol = os.path.join(gecici, "deploy.yml")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
        eski = KAP.DEPLOY_VARSAYILAN
        KAP.DEPLOY_VARSAYILAN = yol
        try:
            ok, hatalar = KAP.kanca_kablo_adimi_kontrol()
        finally:
            KAP.DEPLOY_VARSAYILAN = eski
        return (0 if ok else 1), hatalar
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _akisa_yorum_ekle(akislar, akis_adi):
    """KONTROL: ilgisiz bir YAML yorum satiri ekler (hukum DEGISMEMELI)."""
    yeni = []
    for yol, metin, sinif in akislar:
        if os.path.basename(yol) == akis_adi:
            metin = "# KONTROL MUTANTI — ilgisiz yorum satiri\n" + metin
        yeni.append((yol, metin, sinif))
    return yeni


def main():
    basta = {y: _sha(y) for y in DOKUNULMAZ}
    eski_kume, yeni_kume = _yeni_yakalananlar()
    dusen = sorted(eski_kume - yeni_kume)
    yeni_yakalanan = sorted(yeni_kume - eski_kume)

    print("KESIF KAPSAMI — ONCE/SONRA")
    print("  Kesfedilen (ESKI predikat) : %d" % len(eski_kume))
    print("  Kesfedilen (CARI predikat) : %d" % len(yeni_kume))
    print("  YENI YAKALANAN             : %d" % len(yeni_yakalanan))
    print("  DUSEN (olmamali)           : %d" % len(dusen))
    for y in dusen:
        print("      🔴 DUSTU: %s" % y)
    print("-" * 70)

    kesif = KAP.kesfet()
    izin = dict(KAP.IZIN_LISTESI)
    akislar = _akislari_al()

    iddia, dusenler = 0, []

    def olc(ad, fn, beklenen_kirmizi, tani_parcasi=None):
        """Tek mutant. COKME kirmizi SAYILMAZ; kirmizi ISARET SARTIYLA sayilir."""
        nonlocal iddia
        iddia += 1
        try:
            kod, satirlar = fn()
        except Exception as e:  # noqa: BLE001 — cokme kirmiziyla KARISTIRILMAZ
            dusenler.append("%s: COKTU (%s: %s) — cokme kirmizi SAYILMAZ"
                            % (ad, type(e).__name__, e))
            print("  FAIL %s -> COKTU (%s)" % (ad, type(e).__name__))
            return
        rapor = "\n".join(satirlar)
        kirmizi = (kod == 1)
        isaret = True
        if beklenen_kirmizi and tani_parcasi:
            isaret = tani_parcasi in rapor
        if kirmizi == beklenen_kirmizi and isaret:
            print("  ok  %s -> rc=%d%s" % (ad, kod,
                                           " (tani ISARETI var)" if tani_parcasi else ""))
            return
        dusenler.append("%s: rc=%d (beklenen %s) isaret=%s"
                        % (ad, kod, "KIRMIZI" if beklenen_kirmizi else "YESIL", isaret))
        print("  FAIL %s -> rc=%d isaret=%s" % (ad, kod, isaret))

    # ---- TABAN: cari hal YESIL olmali (yoksa batarya "hep kirmizi"dan ayirt edilemez)
    olc("TABAN cari kesif+izin+akislar", lambda: _denetle(kesif, izin, akislar), False)

    # ---- M1: kesif predikatinden `mutasyon` kolu DUSURULUR ------------------
    # Yeni yakalanan dosyalar kesiften duser -> onlar icin yazilan muafiyetler
    # "BAYAT izin (artik kesfedilmiyor)" olur.
    def m1():
        eski_kesif = sorted(eski_kume)
        return _denetle(eski_kesif, izin, akislar)
    olc("M1 kesif predikatinden `-mutasyon` kolu DUSURULDU", m1, True,
        "BAYAT izin (artik kesfedilmiyor")

    # ---- M2: predikat JOKERLESTIRILIR (gevsetme yonu) -----------------------
    def m2():
        eski_pat = KAP.TOOLS_PAT
        KAP.TOOLS_PAT = re.compile(r"^tools/.*$")
        try:
            ok, hatalar = KAP.kesif_predikat_kontrol()
        finally:
            KAP.TOOLS_PAT = eski_pat
        return (0 if ok else 1), hatalar
    olc("M2 kesif predikati JOKERLESTI (`^tools/.*$`)", m2, True,
        "KESIF PREDIKATI FIKSTURU DUSTU")

    # ---- M3: yeni muafiyetin GEREKCESI bosaltilir (joker muafiyet yonu) -----
    def m3():
        hedef = yeni_yakalanan[0] if yeni_yakalanan else None
        muaf_hedef = next((y for y in yeni_yakalanan if y in izin), hedef)
        bozuk = dict(izin)
        bozuk[muaf_hedef] = ""
        return _denetle(kesif, bozuk, akislar)
    olc("M3 yeni muafiyetin GEREKCESI bosaltildi", m3, True,
        "GEREKCESIZ izin girisi")

    # ---- M4: yeni yakalanan bir dosya SESSIZCE atlanir ----------------------
    def m4():
        muaf_hedef = next(y for y in yeni_yakalanan if y in izin)
        bozuk = dict(izin)
        bozuk.pop(muaf_hedef)
        return _denetle(kesif, bozuk, akislar)
    olc("M4 yeni yakalanan dosyanin muafiyeti SILINDI (sessiz atlama)", m4, True,
        "KAPSAMSIZ (ne kosuluyor ne izin listesinde)")

    # ---- M5: CI'ya KABLOLANAN surucunun cagri satiri silinir (RATCHET) ------
    # Bu, isin CEKIRDEK IDDIASI: artik kesifte oldugu icin cagri satirinin silinmesi
    # kapiyi KIRMIZI yakar. Eskiden bu mutant SESSIZCE YESIL geciyordu.
    kablolu = sorted(y for y in yeni_yakalanan if y not in izin)

    def m5():
        mutant_akislar, silinen = _akis_satiri_sil(akislar, "nobet.yml", kablolu[0])
        if not silinen:
            raise RuntimeError("M5 OLCULEMEDI: %s icin nobet.yml'de icra satiri "
                               "BULUNAMADI (mutasyon uygulanamadi)" % kablolu[0])
        return _denetle(kesif, izin, mutant_akislar)
    if kablolu:
        olc("M5 kablolanan surucunun nobet.yml cagri satiri SILINDI (%s)"
            % os.path.basename(kablolu[0]), m5, True,
            "KAPSAMSIZ (ne kosuluyor ne izin listesinde): %s" % kablolu[0])
    else:
        dusenler.append("M5 OLCULEMEDI: CI'ya kablolanmis YENI surucu YOK -> ratchet "
                        "iddiasi kanitlanamaz (fail-closed)")

    # ---- M6: predikat fikstur tablosu BOSALTILIR ----------------------------
    def m6():
        eski_tablo = KAP.KESIF_PREDIKAT_FIKSTURLERI
        KAP.KESIF_PREDIKAT_FIKSTURLERI = ()
        try:
            ok, hatalar = KAP.kesif_predikat_kontrol()
        finally:
            KAP.KESIF_PREDIKAT_FIKSTURLERI = eski_tablo
        return (0 if ok else 1), hatalar
    olc("M6 kesif predikati FIKSTUR TABLOSU bosaltildi", m6, True,
        "FIKSTUR TABLOSU KUCULDU")

    # ---- IZLENMEYEN KOVA EKSENI (9 Agu 2026) --------------------------------
    # OLCULEN KORLUK: kesif YALNIZ `git ls-files` uzerinden yuruyordu -> `git add`
    # EDILMEMIS yeni bir `tools/<x>-kapisi.py` ile kapi rc=0 YESIL veriyordu.
    # Asagidaki uc mutant o ekseni AYRI AYRI kirar; her biri TEK BASINA kirmizi.
    # TABAN (mutasyonsuz modul) once olculur: yesil olmayan bir taban uzerinde
    # "mutant kirmizi yakti" iddiasi ANLAMSIZDIR.
    olc("IZ-TABAN izlenmeyen fikstur (mutasyonsuz)",
        lambda: _iz_fikstur(KAP), False)

    # M-IZ1: `--others` dusunce kova IZLENEN dosyalarla dolar. AYIRT EDICILIK NOTU
    # (9 Agu, curutucu bulgusu): eskiden bu mutant TABAN iddiasini da dusuruyordu
    # ("kova bozuldu" ile "her sey bozuldu" ayrilmiyordu). Fikstur A1 iddiasi A1a
    # (taban HUKMU) + A1b (taban KOVASI) olarak IKIYE bolundu; artik bu mutant
    # A1b'yi dusurur, A1a YESIL kalir -> taban zehirlenmiyor.
    olc("M-IZ1 kesiften `--others` bayragi DUSURULDU (kova IZLENEN dosyayla doluyor)",
        lambda: _iz_fikstur(_mutant_modul(
            "iz1",
            'LS_FILES_IZLENMEYEN = ("ls-files", "--others", "--exclude-standard")',
            'LS_FILES_IZLENMEYEN = ("ls-files", "--exclude-standard")')),
        True, "A1b TABAN KOVASI BOS DEGIL")

    olc("M-IZ1b kova BOSALTILDI (taban HUKMUNU bozmadan — ayirt edici)",
        lambda: _iz_fikstur(_mutant_modul(
            "iz1b",
            "    return sorted(y for y in r.stdout.splitlines() "
            "if _kesif_adayi_mi(y)), None",
            "    return [], None")),
        True, "IZLENMEYEN KOVA YANLIS")

    olc("M-IZ4 (KISMI KAPSAM) kova yalniz `*-kapisi.py` goruyor",
        lambda: _iz_fikstur(_mutant_modul(
            "iz4",
            "    return sorted(y for y in r.stdout.splitlines() "
            "if _kesif_adayi_mi(y)), None",
            '    return sorted(y for y in r.stdout.splitlines() '
            'if _kesif_adayi_mi(y) and y.endswith("-kapisi.py")), None')),
        True, "IZLENMEYEN KOVA YANLIS")

    olc("M-IZ5 `--exclude-standard` DUSURULDU (.gitignore'lu artefakt siziyor)",
        lambda: _iz_fikstur(_mutant_modul(
            "iz5",
            'LS_FILES_IZLENMEYEN = ("ls-files", "--others", "--exclude-standard")',
            'LS_FILES_IZLENMEYEN = ("ls-files", "--others")')),
        True, "IZLENMEYEN KOVA YANLIS")

    olc("M-IZ6 (FAIL-CLOSED URETIM) git patlayinca sebep yerine None donuyor",
        lambda: _iz_fikstur(_mutant_modul(
            "iz6",
            '        return [], ("git %s basarisiz (rc=%d): %s"\n'
            '                    % (" ".join(LS_FILES_IZLENMEYEN), r.returncode,\n'
            '                       r.stderr.strip() or "-"))',
            "        return [], None")),
        True, "A8 FAIL-OPEN (URETIM)")

    # ---- KABLO EKSENI: main() olcumu denetle()'ye FIILEN geciriyor mu ---------
    # Curutucu olcumu: bu iki mutantta kapi rc=0 TAM KOR kalirken DORT batarya da
    # YESIL geciyordu ([[nobetci-cagri-satiri-nobetsiz]]).
    olc("KABLO-TABAN main() kablo fiksturu (mutasyonsuz)",
        lambda: _kablo_fikstur(KAP), False)

    olc("M-KB1 (Y4) main() olcumu GECIRMIYOR (`izlenmeyen=None`)",
        lambda: _kablo_fikstur(_mutant_modul(
            "kb1",
            "        izlenmeyen=izlenmeyen, izlenmeyen_sebep=izlenmeyen_sebep)",
            "        izlenmeyen=None, izlenmeyen_sebep=izlenmeyen_sebep)")),
        True, "KABLO KOPUK")

    olc("M-KB2 (Y8) main() kovayi BOSALTIYOR (`izlenmeyen = []`)",
        lambda: _kablo_fikstur(_mutant_modul(
            "kb2",
            "    izlenmeyen, izlenmeyen_sebep = kesfet_izlenmeyen()",
            "    izlenmeyen, izlenmeyen_sebep = [], None")),
        True, "KABLO KOPUK")

    olc("M-KB3 (Y9) main() uretim SEBEBINI yutuyor",
        lambda: _kablo_fikstur(_mutant_modul(
            "kb3",
            "        izlenmeyen=izlenmeyen, izlenmeyen_sebep=izlenmeyen_sebep)",
            "        izlenmeyen=izlenmeyen, izlenmeyen_sebep=None)")),
        True, "K3 SEBEP YUTULDU")

    # ---- PUSH KABLOSU: pre-push blogunun DAVRANISI (varligi degil) -----------
    olc("M-PP4 (P4) pre-push cagrisi `--kendini-test` koluna cevrildi",
        lambda: _pp_mutant('ci-kapsam-test.py" 2>&1 </dev/null)',
                           'ci-kapsam-test.py" --kendini-test 2>&1 </dev/null)'),
        True, "PRE-PUSH FIKSTURU DUSTU (SAGLAM")

    olc("M-PP5 (P5) pre-push kosulu ASLA ateslenmiyor (`-eq 12345`)",
        lambda: _pp_mutant('if [ "$pruvo_kapsam_rc" -ne 0 ]; then',
                           'if [ "$pruvo_kapsam_rc" -eq 12345 ]; then'),
        True, "PRE-PUSH FIKSTURU DUSTU (SAGLAM")

    olc("M-PP6 pre-push varlik kapisi POZITIFE cevrildi (arac yoksa sessiz atlar)",
        lambda: _pp_mutant(
            'if [ -z "$pruvo_kapsam_kok" ] || [ ! -f "$pruvo_kapsam_kok/tools/'
            'ci-kapsam-test.py" ]; then',
            'if [ -n "$pruvo_kapsam_kok" ] && [ -f "$pruvo_kapsam_kok/tools/'
            'ci-kapsam-test.py" ]; then'),
        True, "PRE-PUSH FIKSTURU DUSTU (SAGLAM")

    olc("KONTROL-4 pre-push govdesine ILGISIZ yorum (hukum degismemeli)",
        lambda: _pp_mutant(None, "\n# KONTROL MUTANTI — ilgisiz yorum satiri\n"),
        False)

    # ---- KABLONUN KABLOSU (IKINCI TUR) --------------------------------------
    # Curutucu olcumu: iki yeni nobetciyi GOVDESINDEN sokmak yakalaniyordu, ama
    # BLOKLAYICI koldan CAGRI SATIRINI silmek (KB-C/KB-D) ya da `--kendini-test`
    # hukmundeki PAYINI dusurmek (KB-E) DORT bataryayi da YESIL birakiyordu.
    # 🔴 KAYNAK METNI GECIRILIR, MODUL DEGIL: `suzgec_kablosu_kontrol()` KENDI
    # dosyasini okur; mutant modul yuklemek kabloyu OLCMEZDI (mutant modul yine
    # PRISTINE dosyayi okur — olculdu: uc mutant da rc=0 verdi). Nobetcinin
    # `kaynak=` test seami tam bu yuzden var.
    def _kablo_nobetcisi(*degisiklikler):
        """degisiklikler: (capa, ikame) ciftleri; her biri TAM 1 kez gecmeli."""
        with open(KAPI_YOLU, encoding="utf-8") as f:
            kaynak = f.read()
        for capa, ikame in degisiklikler:
            gecen = kaynak.count(capa)
            if gecen != 1:
                raise RuntimeError("KABLO MUTANTI OLCULEMEDI: capa %r %d kez gecti "
                                   "(beklenen 1)" % (capa[:60], gecen))
            kaynak = kaynak.replace(capa, ikame)
        ok, hatalar = KAP.suzgec_kablosu_kontrol(kaynak=kaynak)
        return (0 if ok else 1), hatalar

    olc("KABLO-NOBETCI-TABAN suzgec_kablosu_kontrol (mutasyonsuz)",
        _kablo_nobetcisi, False)

    olc("M-KB4 (KB-C) denetle()'den MAIN-KABLO cagrisi SILINDI",
        lambda: _kablo_nobetcisi(
            ("        _, kablo_hata = main_kablosu_kontrol()",
             "        kablo_hata = []")),
        True, "NOBETCI KABLOSU KOPMUS")

    olc("M-KB5 (KB-D) BAYRAKSIZ koldan PRE-PUSH-CAPA cagrisi SILINDI",
        lambda: _kablo_nobetcisi(
            ("        _, pp_hata = pre_push_capa_kontrol()",
             "        pp_hata = []")),
        True, "NOBETCI KABLOSU KOPMUS")

    olc("M-KB7 `--kanca-kablo` kolundan AGIR DAVRANIS ayagi SILINDI",
        lambda: _kablo_nobetcisi(
            ("        ok, hatalar = pre_push_kablo_kontrol()",
             "        ok, hatalar = True, []")),
        True, "NOBETCI KABLOSU KOPMUS")

    # 🔴 YUZEY KUCULMESI EKSENI: bir adimi koldan kola tasimak iki kolu da rc=0
    # birakip TOPLAM olculen yuzeyi kucultebilir ([[kapi-yan-etkisi-gizli-onkosul]]).
    olc("M-KB8 BLOKLAYICI kol defterinden kayit silindi + taban dusuruldu",
        lambda: _kablo_nobetcisi(
            ('                 "pre_push_capa_kontrol", "suzgec_fikstur_kontrol",',
             '                 "suzgec_fikstur_kontrol",'),
            ("KOL_BIRLESIM_TABANI = 18", "KOL_BIRLESIM_TABANI = 9")),
        True, "KAYIT DEFTERI EKSIK")

    olc("M-KB6 (KB-E) `--kendini-test` hukmu `and` yerine `or`",
        lambda: _kablo_nobetcisi(
            ("                and ok10 and ok11 and ok12 and ok13):",
             "                or ok10 or ok11 or ok12 or ok13):")),
        True, "KENDINI-TEST HUKMU `and` DEGIL")

    # ---- UCUNCU TUR: ORTAM SADAKATI · SEAM · BAYRAK SIZINTISI ---------------
    olc("M-PP7 (X4) pre-push blogu `[ -z \"$GIT_EXEC_PATH\" ]` sarmalinda",
        lambda: _pp_mutant(
            "pruvo_kapsam_kok=$(git rev-parse --show-toplevel 2>/dev/null)",
            "if [ -z \"$GIT_EXEC_PATH\" ]; then\n"
            "pruvo_kapsam_kok=$(git rev-parse --show-toplevel 2>/dev/null)",
            ek=("# >>> PRUVO GECMIS GERI-DONUS NOBETI BLOGU",
                "fi\n# >>> PRUVO GECMIS GERI-DONUS NOBETI BLOGU")),
        True, "PRE-PUSH FIKSTURU DUSTU (SAGLAM")

    olc("M-S1 seam uretim yolu CALISAN dosya yerine `git show HEAD:` okuyor",
        lambda: _kablo_nobetcisi(
            ("        kaynak_yol = os.path.abspath(__file__)\n"
             "        try:\n"
             "            with open(kaynak_yol, encoding=\"utf-8\") as f:\n"
             "                kaynak = f.read()\n"
             "        except OSError as e:",
             "        try:\n"
             "            kaynak = subprocess.run(\n"
             "                [\"git\", \"-C\", ROOT, \"show\", \"HEAD:tools/\"\n"
             "                 \"ci-kapsam-test.py\"],\n"
             "                capture_output=True, text=True).stdout\n"
             "        except OSError as e:")),
        True, "SEAM SIZINTISI")

    olc("M-Z2 yeniden giris bayragi `finally`de SIFIRLANMIYOR",
        lambda: _kablo_fikstur(_mutant_modul(
            "z2",
            "        _KABLO_FIKSTURU_ICINDE = False\n"
            "        shutil.rmtree(gecici, ignore_errors=True)",
            "        shutil.rmtree(gecici, ignore_errors=True)")),
        True, "SIZINTI")

    # ---- BESINCI TUR: SERIT · ok11 EZME · SEAM KAPSAMI · DEFTER ESITLIGI ----
    olc("M-E3i `ok11 = True` (cagri DURUYOR, hukum tek satirda ATILIYOR)",
        lambda: _kablo_nobetcisi(
            ("        ok11, hata11 = kanca_kablo_serit_kontrol()",
             "        ok11, hata11 = kanca_kablo_serit_kontrol()\n"
             "        ok11 = True")),
        True, "CAGRIDAN TUREMEYEN")

    olc("M-E3iv seam `if` DISINDA eziliyor (kapsam ekseni)",
        lambda: _kablo_nobetcisi(
            ("    try:\n        agac = ast.parse(kaynak)",
             "    kaynak = subprocess.run(\n"
             "        [\"git\", \"-C\", ROOT, \"show\", \"HEAD:tools/ci-kapsam-test.py\"],\n"
             "        capture_output=True, text=True).stdout\n"
             "    try:\n        agac = ast.parse(kaynak)")),
        True, "SEAM SIZINTISI")

    olc("M-E5a defterden kayit SILINDI (taban da dusurulse gizlenemez)",
        lambda: _kablo_nobetcisi(
            ('"izlenmeyen_fikstur_kontrol", "kanca_kablo_serit_kontrol",',
             '"izlenmeyen_fikstur_kontrol",'),
            ("KOL_BIRLESIM_TABANI = 18", "KOL_BIRLESIM_TABANI = 9")),
        True, "KAYIT DEFTERI EKSIK")

    olc("M-SERIT agir ayak adimi BLOKLAMAYAN job'a tasindi",
        lambda: _serit_mutant('  serit-a3:\n', '  serit-b-alarm:\n'),
        True, "S3 ZORLAMA YOK")

    olc("KONTROL-6 bloklayici job ADI degisti ama `deploy: needs` GUNCELLENDI",
        lambda: _serit_mutant('  serit-a3:\n', '  serit-a3-yeni:\n',
                              ek=("needs: [build, serit-a2, serit-a3, serit-a4]",
                                  "needs: [build, serit-a2, serit-a3-yeni, serit-a4]")),
        False)

    # ---- ALTINCI TUR: SAHTE-KIRMIZI · UCUNCU KOLUN ADIMI · ok/ok_s KAPSAMI ----
    # 🔴 UC MESRU YAZIM YESIL KALMALI (F3): kural SOZDIZIMSEL degil ANLAMSAL.
    # Bunlar KONTROL mutantidir; kirmizi yakarlarsa nobetci mesru bir refactor'da
    # TUM EKIBIN itmesini durdurur ([[kapi-anchor-coupling-ikilemi]]).
    _OK4 = "        ok4, hata4 = bayraksiz_adim_kontrol()"
    olc("KONTROL-N1 `try/except` — IKI dal da CAGRIDAN (yesil kalmali)",
        lambda: _kablo_nobetcisi(
            (_OK4,
             "        try:\n"
             "            ok4, hata4 = bayraksiz_adim_kontrol()\n"
             "        except Exception:\n"
             "            ok4, hata4 = bayraksiz_adim_kontrol()")),
        False)

    olc("KONTROL-N2 KOSULLU atama — iki dal da CAGRIDAN (yesil kalmali)",
        lambda: _kablo_nobetcisi(
            (_OK4,
             "        if args.deploy:\n"
             "            ok4, hata4 = bayraksiz_adim_kontrol()\n"
             "        else:\n"
             "            ok4, hata4 = bayraksiz_adim_kontrol()")),
        False)

    olc("KONTROL-N3 ARA DEGISKEN uzerinden atama (yesil kalmali)",
        lambda: _kablo_nobetcisi(
            (_OK4,
             "        _s4 = bayraksiz_adim_kontrol()\n"
             "        ok4, hata4 = _s4")),
        False)

    olc("M-P1 `ok4 = True` (hukum ezme — KIRMIZI olmali)",
        lambda: _kablo_nobetcisi((_OK4, _OK4 + "\n        ok4 = True")),
        True, "CAGRIDAN TUREMEYEN")

    olc("M-P2 `ok4, hata4 = True, []` (cagri HIC yok — KIRMIZI olmali)",
        lambda: _kablo_nobetcisi(
            (_OK4, "        ok4, hata4 = bayraksiz_adim_kontrol()\n"
                   "        ok4, hata4 = True, []")),
        True, "CAGRIDAN TUREMEYEN")

    # 8. tur: hukum ezme sinifinin ASIL hakimi DAVRANIS ayagidir; AST kurali
    # yalniz SABIT-LITERAL ezmeyi gorur (`ok_s = True`). Ikisi de olculur.
    olc("M-D1 ucuncu kolun hukmu sabit literalle eziliyor (AST ekseni)",
        lambda: _kablo_nobetcisi(
            ("        ok_s, hata_s = kanca_kablo_serit_kontrol()",
             "        ok_s, hata_s = kanca_kablo_serit_kontrol()\n"
             "        ok_s = True")),
        True, "CAGRIDAN TUREMEYEN")

    def _davranis(kaynak=None, capa=None, ikame=None):
        with open(KAPI_YOLU, encoding="utf-8") as f:
            k = f.read()
        if capa is not None:
            if k.count(capa) != 1:
                raise RuntimeError("DAVRANIS MUTANTI OLCULEMEDI: capa %d kez gecti"
                                   % k.count(capa))
            k = k.replace(capa, ikame)
        ok, hatalar = KAP.hukum_davranis_kontrol(kaynak=k)
        return (0 if ok else 1), hatalar

    olc("DAVRANIS-TABAN hukum davranis ayagi (mutasyonsuz)",
        lambda: _davranis(), False)

    olc("M-H1b (7. tur kacisi) hukum `if ok or True:` — DAVRANIS ekseni",
        lambda: _davranis(
            capa="        if ok and ok_s and ok_d:",
            ikame="        if ok or True:"),
        True, "HUKUM EZILIYOR")

    # ---- DOKUZUNCU TUR: FAIL-FAST + EVREN TABANI --------------------------
    # 🔴 Eski surum bos evrende hata EKLIYOR ama RETURN ETMIYORDU: stub
    # uygulanmadan gercek is kosuyor, `--kendini-test` kolu ayagi YENIDEN cagirip
    # ozyineleme uretiyor ve UC KOL DA >150 sn ASILIYORDU. Asilma, bloklayici bir
    # kapida kirmizi DEGILDIR — hukumsuzluktur.
    _EVREN_CAPA = (
        "    kaynak = getattr(mod, \"__pruvo_kaynak__\", None)\n"
        "    if kaynak is None:")

    # 🔴 MUTANT MODUL SART: evren CANLI `_nobetci_evreni()`/`_sozlesme_evreni()`
    # ile hesaplanir; yalniz KAYNAK gecirmek onlari degistirmez.
    def _davranis_govdesi(mod):
        ok, hatalar = mod.hukum_davranis_kontrol()
        return (0 if ok else 1), hatalar

    olc("M-I1d BOS EVREN (fail-fast: hukum VERILMELI, ASILMAMALI)",
        lambda: _davranis_govdesi(_mutant_modul(
            "i1d", _EVREN_CAPA,
            "    kaynak = \"\"\n    if False:")),
        True, "NOBETCI EVRENI KUCULDU")

    olc("M-I3c EVREN [:15]e KIRPILDI (taban KAYIT DEFTERINDEN turer)",
        lambda: _davranis_govdesi(_mutant_modul(
            "i3c", "    return sorted(_sozlesme_evreni(kaynak))",
            "    return sorted(_sozlesme_evreni(kaynak))[:15]")),
        True, "NOBETCI EVRENI KUCULDU")

    olc("M-H3-1 (7. tur kacisi) `_ = nobetci()` + sabit atama",
        lambda: _davranis(
            capa="        ok_s, hata_s = kanca_kablo_serit_kontrol()",
            ikame="        _ = kanca_kablo_serit_kontrol()\n"
                  "        ok_s, hata_s = True, []"),
        True, "HUKUM EZILIYOR")

    olc("M-B1 (F2) `--kanca-kablo` ADIMI deploy.yml'den SILINDI",
        lambda: _adim_mutant(
            "        run: python3 tools/ci-kapsam-test.py --kanca-kablo",
            "        run: echo atlandi"),
        True, "KANCA-KABLO ADIMI YOK")

    olc("M-B3 (F2) `--kanca-kablo` adimi ECHO'ya sarildi",
        lambda: _adim_mutant(
            "        run: python3 tools/ci-kapsam-test.py --kanca-kablo",
            "        run: echo python3 tools/ci-kapsam-test.py --kanca-kablo"),
        True, "KANCA-KABLO ADIMI YOK")

    # 🔴 BU IKISI MUTANT MODUL ISTER (kaynak gecirmek YETMEZ): olculen sey nobetcinin
    # KENDI GOVDESIDIR; `kaynak=` seami yalniz YARGILANAN metni degistirir, govdeyi
    # degil. Ic fikstur mutant govdeyle kosunca sessizce oldurulen kolu gorur.
    def _kablo_govdesi(mod):
        ok, hatalar = mod.suzgec_kablosu_kontrol()
        return (0 if ok else 1), hatalar

    olc("M-D3 defter esitligi TEK YONLU yapildi (defter-eksik kolu dusuruldu)",
        lambda: _kablo_govdesi(_mutant_modul(
            "d3",
            "        defter_eksik = sorted(cagrilan - kayitli)",
            "        defter_eksik = []  # no-op")),
        True, "IC FIKSTUR (DEFTER) DUSTU")

    olc("M-D4 seam YASAK LISTESI bosaltildi",
        lambda: _kablo_govdesi(_mutant_modul(
            "d4",
            '_SEAM_YASAK_CAGRI = ("run", "check_output", "Popen", "check_call", '
            '"getoutput",\n                     "urlopen", "loads")',
            "_SEAM_YASAK_CAGRI = ()")),
        True, "IC FIKSTUR (SEAM) DUSTU")

    # ---- YEDINCI TUR: kural NOBETCI cagrisina bagli mi · fuzz tablosu civili mi --
    def _fuzz(mod):
        ok, hatalar = mod.hukum_fuzz_kontrol()
        return (0 if ok else 1), hatalar

    olc("FUZZ-TABAN 30 varyantlik iki yonlu tablo (mutasyonsuz)",
        lambda: _fuzz(KAP), False)

    olc("M-G1 `_cagridan_mi` NOBETCI yerine HERHANGI bir cagriyi kabul ediyor",
        lambda: _fuzz(_mutant_modul(
            "g1",
            "    if _nobetci_cagrisi_mi(deger):\n        return True",
            "    if any(isinstance(c, ast.Call) for c in ast.walk(deger)):\n"
            "        return True")),
        True, "HUKUM FUZZ DUSTU")

    olc("M-G2 sabit-nokta derinligi `range(8)` -> `range(1)`",
        lambda: _fuzz(_mutant_modul("g2", "    for _ in range(8):",
                                    "    for _ in range(1):")),
        True, "HUKUM FUZZ DUSTU")

    olc("M-G3 `Name` OLMAYAN hedef fail-closed kolu dusuruldu",
        lambda: _fuzz(_mutant_modul(
            "g3",
            "                if isinstance(alt, (ast.Subscript, ast.Attribute)):",
            "                if False and isinstance(alt, (ast.Subscript, "
            "ast.Attribute)):")),
        True, "HUKUM FUZZ DUSTU"),

    olc("M-G4 `if <sabit>:` yasagi dusuruldu",
        lambda: _fuzz(_mutant_modul(
            "g4",
            "        if isinstance(d, ast.If) and isinstance(d.test, ast.Constant):",
            "        if False and isinstance(d, ast.If):")),
        True, "HUKUM FUZZ DUSTU")

    olc("M-G5 FUZZ TABLOSU budandi (ilk 6 varyant)",
        lambda: _fuzz(_mutant_modul(
            "g5",
            "def hukum_fuzz_kontrol():",
            "HUKUM_FUZZ_FIKSTURLERI = HUKUM_FUZZ_FIKSTURLERI[:6]\n\n\n"
            "def hukum_fuzz_kontrol():")),
        True, "HUKUM FUZZ TABLOSU KUCULDU")

    # 🔴 MUTANT MODUL SART: taban CANLI sabitten okunur; kaynak gecirmek onu
    # degistirmez (olculdu: `_kablo_nobetcisi` ile rc=0).
    olc("M-G6 KOL_BIRLESIM_TABANI dusuruldu (esitlik sarti)",
        lambda: _kablo_govdesi(_mutant_modul(
            "g6", "KOL_BIRLESIM_TABANI = 18", "KOL_BIRLESIM_TABANI = 12")),
        True, "KOL BIRLESIMI TABANLA UYUSMUYOR")

    olc("KONTROL-5 hukumdeki `okN` sirasi degisti (SEMANTIK AYNI, yesil kalmali)",
        lambda: _kablo_nobetcisi(
            ("        if (ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 and ok8 "
             "and ok9\n                and ok10 and ok11 and ok12 and ok13):",
             "        if (ok11 and ok10 and ok9 and ok8 and ok7 and ok6 and ok5 and "
             "ok4 and ok3\n                and ok2 and ok1):")),
        False)

    olc("M-IZ2 izlenmeyen kova UYARI'ya cevrildi (exit koduna dokunmuyor)",
        lambda: _iz_fikstur(_mutant_modul(
            "iz2",
            "    for yol in izlenmeyen_kapsamsiz:\n        hatalar.append(",
            "    for yol in izlenmeyen_kapsamsiz:\n        satirlar.append(")),
        True, "SESSIZ YESIL")

    olc("M-IZ3 (GEVSETME) kova predikati jokerlesti (`.md`/arsiv siziyor)",
        lambda: _iz_fikstur(_mutant_modul(
            "iz3",
            "    return sorted(y for y in r.stdout.splitlines() "
            "if _kesif_adayi_mi(y)), None",
            '    return sorted(y for y in r.stdout.splitlines() '
            'if y.startswith("tools/")), None')),
        True, "IZLENMEYEN KOVA YANLIS")

    # KONTROL-3: kaynaga ILGISIZ bir yorum satiri girer -> hukum DEGISMEZ.
    # Bu, "mutant modul yukleme duzenegi kendiliginden kirmizi yakiyor" ihtimalini
    # eler; olmasaydi yukaridaki uc kirmizi tautoloji olurdu.
    olc("KONTROL-3 mutant yukleyiciye ILGISIZ yorum (hukum degismemeli)",
        lambda: _iz_fikstur(_mutant_modul(
            "k3", "import argparse",
            "# KONTROL MUTANTI — ilgisiz yorum satiri\nimport argparse")),
        False)

    # ---- KONTROL 1: ilgisiz YAML yorumu -> hukum DEGISMEZ -------------------
    olc("KONTROL-1 nobet.yml'e ilgisiz yorum satiri",
        lambda: _denetle(kesif, izin, _akisa_yorum_ekle(akislar, "nobet.yml")), False)

    # ---- KONTROL 2: muafiyet gerekcesine ilgisiz metin eklenir --------------
    def k2():
        muaf_hedef = next(y for y in yeni_yakalanan if y in izin)
        genis = dict(izin)
        genis[muaf_hedef] = genis[muaf_hedef] + " (KONTROL: ilgisiz ek cumle.)"
        return _denetle(kesif, genis, akislar)
    olc("KONTROL-2 muafiyet gerekcesine ilgisiz cumle eklendi", k2, False)

    # ---- kaynak butunlugu ---------------------------------------------------
    print("-" * 70)
    bozulan = [y for y in DOKUNULMAZ if _sha(y) != basta[y]]
    if bozulan:
        print("🔴 CANLI DOSYA DEGISMIS (mutasyon diske sizdi): %s"
              % ", ".join(bozulan))
        return 1
    print("  kaynak butunlugu: SAGLAM (sha256 basta=sonda, %d dosya)" % len(DOKUNULMAZ))
    print("KESIF=%d->%d  DUSEN=%d  YENI=%d  KABLOLANAN=%d"
          % (len(eski_kume), len(yeni_kume), len(dusen), len(yeni_yakalanan),
             len(kablolu)))
    print("MUTANT=%d/%d iddia" % (iddia - len(dusenler), iddia))
    if dusen:
        print("SONUC: KIRMIZI ❌ — kesif kumesinden dosya DUSTU (kapi GEVSEDI)")
        return 1
    if dusenler:
        for d in dusenler:
            print("  · %s" % d)
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅ — kesif genislemesi HUKUMDE yasiyor; daraltma VE gevsetme "
          "yonu TEK BASINA kirmizi, kontroller yesil.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
