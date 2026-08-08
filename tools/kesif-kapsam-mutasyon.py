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
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_YOLU = os.path.join(TOOLS, "ci-kapsam-test.py")
NOBET_YOLU = os.path.join(ROOT, ".github", "workflows", "nobet.yml")
DEPLOY_YOLU = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
DOKUNULMAZ = (KAPI_YOLU, NOBET_YOLU, DEPLOY_YOLU)

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
