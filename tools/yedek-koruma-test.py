#!/usr/bin/env python3
"""Yedek sifir/ani-dusus/surum davranisi ve iki oldurucu mutasyonun hermetik kabulu."""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KANONIK = os.path.join(TOOLS, "yedekle.py")


def sha(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(65536), b""):
            h.update(parca)
    return h.hexdigest()


def yaz_json(yol, sayi, dolgu=80):
    veri = {"k%03d" % n: {"olcu": n, "veri": "x" * dolgu} for n in range(sayi)}
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, sort_keys=True)


def modul_yukle(yol):
    ad = "yedekle_koruma_test_%d" % os.getpid()
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reddedildi_mi(mod, kaynak, yedek):
    try:
        mod._drive_kopyala(kaynak, yedek)
    except mod.YedekKorumaHatasi:
        return True
    return False


def vaka_sifir(mod, kok):
    kaynak = os.path.join(kok, "sifir-kaynak.json")
    yedek = os.path.join(kok, "sifir-yedek.json")
    open(kaynak, "wb").close()
    yaz_json(yedek, 10)
    once = sha(yedek)
    red = reddedildi_mi(mod, kaynak, yedek)
    return red and sha(yedek) == once and os.path.getsize(kaynak) == 0


def vaka_sifir_yeni(mod, kok):
    """0 bayt kaynak + KARSISI BOS/YOK -> gerileme DEGIL, KOPYALANMALI.

    Gercek vaka: `mimar-posta-kutusu.md.lock` mesru olarak daima 0 bayttir; kosulsuz red
    tum yedek kosumunu dusuruyordu. Iki alt hal de olculur: hedef HIC YOK, ve hedef VAR
    ama 0 bayt.
    """
    yok_kaynak = os.path.join(kok, "kilit-yok.lock")
    yok_yedek = os.path.join(kok, "kilit-yok-yedek.lock")
    open(yok_kaynak, "wb").close()
    if reddedildi_mi(mod, yok_kaynak, yok_yedek):
        return False
    if not os.path.isfile(yok_yedek) or os.path.getsize(yok_yedek) != 0:
        return False
    bos_kaynak = os.path.join(kok, "kilit-bos.lock")
    bos_yedek = os.path.join(kok, "kilit-bos-yedek.lock")
    open(bos_kaynak, "wb").close()
    open(bos_yedek, "wb").close()
    if reddedildi_mi(mod, bos_kaynak, bos_yedek):
        return False
    return os.path.isfile(bos_yedek) and os.path.getsize(bos_yedek) == 0


def vaka_ani(mod, kok):
    kaynak = os.path.join(kok, "ani-kaynak.json")
    yedek = os.path.join(kok, "ani-yedek.json")
    yaz_json(kaynak, 2)
    yaz_json(yedek, 10)
    once = sha(yedek)
    red = reddedildi_mi(mod, kaynak, yedek)
    return red and sha(yedek) == once


def vaka_karantina(mod, kok):
    """Reddedilen TEK dosya kosumu OLDURMEZ; komsu dosya yedeklenir, atlama SESSIZ DEGIL.

    Gercek vaka (ayni gun IKI kez): `mimar-posta-kutusu.md.lock` (mesru 0 bayt) ve
    `posta-kutusu-kaan-izleme-ankor.txt` (485 -> 185 mesru dusus) tum yedek kosumunu
    dusurdu. Olculen uc eksen: (1) reddedilenin kanonigi DEGISMEZ, (2) komsu dosya
    YINE DE kopyalanir, (3) atlama karantina defterine YAZILIR.
    """
    del mod._KORUMA_KARANTINA[:]
    kotu_kaynak = os.path.join(kok, "kar-kotu.json")
    kotu_yedek = os.path.join(kok, "kar-kotu-yedek.json")
    yaz_json(kotu_kaynak, 2)
    yaz_json(kotu_yedek, 10)
    kotu_once = sha(kotu_yedek)
    iyi_kaynak = os.path.join(kok, "kar-iyi.json")
    iyi_yedek = os.path.join(kok, "kar-iyi-yedek.json")
    yaz_json(iyi_kaynak, 11)
    iyi_beklenen = sha(iyi_kaynak)
    # (1) reddedilen dosya: kopyalanmadi, kanonik yedek BIREBIR ayni, ISTISNA SIZMADI
    if mod._drive_kopyala_karantinali(kotu_kaynak, kotu_yedek) is not False:
        return False
    if sha(kotu_yedek) != kotu_once:
        return False
    # (2) komsu dosya AYNI kosumda yedeklendi
    if mod._drive_kopyala_karantinali(iyi_kaynak, iyi_yedek) is not True:
        return False
    if sha(iyi_yedek) != iyi_beklenen:
        return False
    # (3) atlama SESSIZ degil: karantina defterinde TAM 1 giris, dogru dosya adiyla
    if len(mod._KORUMA_KARANTINA) != 1:
        return False
    yol, sebep = mod._KORUMA_KARANTINA[0]
    return yol == kotu_yedek and "REDDEDILDI" in sebep


def _beyan_kur(mod, kok, harita):
    """Gecici beyan dosyasi kurar ve modulu ona baglar. Doner: yol."""
    yol = os.path.join(kok, ".yedek-dusus-izin.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(harita, f, ensure_ascii=False)
    mod.DUSUS_BEYAN_YOLU = yol
    del mod._BEYAN_KULLANILDI[:]
    del mod._BEYAN_UYARISI[:]
    return yol


def vaka_beyan(mod, kok):
    """Beyan BAGLAYICIDIR: ilan edilen dusus gecer, ilan edilmeyen/sartsiz REDDEDILIR.

    Dort eksen olculur; herhangi biri kayarsa beyan ya arka kapiya ya da olu harfe doner:
      1. tek-seferlik + ILAN EDILEN boyut  -> GECER (yedek guncellenir, kayit tutulur)
      2. tek-seferlik + BASKA boyut        -> REDDEDILIR (beyan blanket DEGIL)
      3. surekli + tavan ALTI              -> GECER
      4. surekli + tavan USTU              -> REDDEDILIR (tavan baglayici)
    """
    onceki_yol = mod.DUSUS_BEYAN_YOLU
    try:
        # --- 1 + 2: tek-seferlik, boyuta bagli
        kaynak = os.path.join(kok, "beyan-tek.json")
        yedek = os.path.join(kok, "beyan-tek-yedek.json")
        yaz_json(yedek, 40)
        yaz_json(kaynak, 2)
        ilan_boyut = os.path.getsize(kaynak)
        _beyan_kur(mod, kok, {"beyan-tek.json": {
            "tur": "tek-seferlik", "kaynak_bayt": ilan_boyut,
            "gerekce": "kasitli sikistirma (test)"}})
        yeni = sha(kaynak)
        if reddedildi_mi(mod, kaynak, yedek):
            return False
        if sha(yedek) != yeni:                      # yedek GERCEKTEN guncellendi mi
            return False
        if len(mod._BEYAN_KULLANILDI) != 1:         # kullanim SESSIZ olamaz
            return False
        ad, tur, _ = mod._BEYAN_KULLANILDI[0]
        if ad != "beyan-tek.json" or tur != "tek-seferlik":
            return False
        # kaynak BASKA bir boyuta duserse ayni beyan ARTIK ESLESMEZ
        yaz_json(yedek, 40)
        yaz_json(kaynak, 3)
        if os.path.getsize(kaynak) == ilan_boyut:   # fikstur gercekten farklilasmali
            return False
        korunan = sha(yedek)
        if not reddedildi_mi(mod, kaynak, yedek):
            return False
        if sha(yedek) != korunan:
            return False
        # --- 3 + 4: surekli, tavana bagli
        rol_kaynak = os.path.join(kok, "beyan-rolling.json")
        rol_yedek = os.path.join(kok, "beyan-rolling-yedek.json")
        yaz_json(rol_yedek, 40)
        yaz_json(rol_kaynak, 1)
        kucuk = os.path.getsize(rol_kaynak)
        _beyan_kur(mod, kok, {"beyan-rolling.json": {
            "tur": "surekli", "azami_bayt": kucuk + 10,
            "gerekce": "rolling ankor (test)"}})
        beklenen = sha(rol_kaynak)
        if reddedildi_mi(mod, rol_kaynak, rol_yedek):
            return False
        if sha(rol_yedek) != beklenen or len(mod._BEYAN_KULLANILDI) != 1:
            return False
        # tavanin USTUNDEKI bir dusus AYNI beyanla gecemez
        yaz_json(rol_yedek, 400)
        yaz_json(rol_kaynak, 60)
        if os.path.getsize(rol_kaynak) <= kucuk + 10:   # fikstur tavani gercekten asmali
            return False
        korunan = sha(rol_yedek)
        if not reddedildi_mi(mod, rol_kaynak, rol_yedek):
            return False
        return sha(rol_yedek) == korunan
    finally:
        mod.DUSUS_BEYAN_YOLU = onceki_yol


def _yaz_bayt(yol, bayt):
    with open(yol, "w", encoding="utf-8") as f:
        f.write("x" * bayt)


def vaka_beyan_tasima(mod, kok):
    """`tasima` turu KORUNUM olcer: silinen icerik GECEMEZ, tasinan icerik GECER.

    Bu turun varlik sebebi, digerlerinin kacirdigi invaryanttir: ortak kutunun
    dogru olcusu bir BOYUT degil, "kutudan cikan bayt arsive girdi mi"dir. Dort
    eksen ayri ayri olculur — biri kayarsa tur ya blanket muafiyete ya olu harfe doner:
      1. hedef, kaynagin kaybi KADAR (ya da fazlasi) buyumus  -> GECER
      2. hedef HIC buyumemis (icerik SILINMIS)                -> REDDEDILIR
      3. `hedef` alani beyanda YOK                            -> REDDEDILIR (fail-closed)
      4. hedef iki duzlemin BIRINDE yok -> OLCULEMEZ          -> REDDEDILIR

    🔴 FIKSTUR IKI DIZINLIDIR ve bu ZORUNLUDUR: uretimde kaynak `memory/`, kanonik
    yedek `<backup>/memory/` altindadir ve `tasima` hedefi HER IKI duzlemde arar.
    Tek dizinli bir fikstur `hedef_canli` ile `hedef_yedek`i AYNI dosyaya cozer,
    fark daima 0 cikar ve 1. eksen HIC gecmezdi (yani vaka sessizce ters olcerdi).
    """
    onceki_yol = mod.DUSUS_BEYAN_YOLU
    canli = os.path.join(kok, "tasima-canli")
    yedek_d = os.path.join(kok, "tasima-yedek")
    os.makedirs(canli, exist_ok=True)
    os.makedirs(yedek_d, exist_ok=True)
    kaynak = os.path.join(canli, "kutu.md")
    varis = os.path.join(yedek_d, "kutu.md")
    hedef_canli = os.path.join(canli, "arsiv.md")
    hedef_yedek = os.path.join(yedek_d, "arsiv.md")
    try:
        # --- 1: KORUNUM TUTAR (kutudan cikan 900 bayt arsive girdi) -> GECER
        _yaz_bayt(varis, 1000)
        _yaz_bayt(kaynak, 100)                 # kaynak_dusus = 900
        _yaz_bayt(hedef_yedek, 5000)
        _yaz_bayt(hedef_canli, 5900)           # hedef_artis  = 900
        _beyan_kur(mod, kok, {"kutu.md": {
            "tur": "tasima", "hedef": "arsiv.md",
            "gerekce": "ortak kutu -> arsiv (test)"}})
        beklenen = sha(kaynak)
        if reddedildi_mi(mod, kaynak, varis):
            return False
        if sha(varis) != beklenen:             # yedek GERCEKTEN guncellendi mi
            return False
        if len(mod._BEYAN_KULLANILDI) != 1:    # kullanim SESSIZ olamaz
            return False
        ad, tur, gerekce = mod._BEYAN_KULLANILDI[0]
        if ad != "kutu.md" or tur != "tasima":
            return False
        # Gerekce SAYI tasimali: "gecti" demek yetmez, NEYIN gecirdigi gorunmeli.
        if "900" not in gerekce or "KORUNUM TUTTU" not in gerekce:
            return False

        # --- 2: KORUNUM TUTMAZ (arsiv HIC buyumemis = icerik SILINMIS) -> RED
        _yaz_bayt(varis, 1000)
        _yaz_bayt(kaynak, 100)
        _yaz_bayt(hedef_yedek, 5000)
        _yaz_bayt(hedef_canli, 5000)           # hedef_artis = 0 < 900
        _beyan_kur(mod, kok, {"kutu.md": {
            "tur": "tasima", "hedef": "arsiv.md",
            "gerekce": "ortak kutu -> arsiv (test)"}})
        korunan = sha(varis)
        if not reddedildi_mi(mod, kaynak, varis):
            return False
        if sha(varis) != korunan:              # kanonik yedek KORUNDU mu
            return False
        if len(mod._BEYAN_KULLANILDI) != 0:    # gecmeyen beyan KULLANILDI sayilamaz
            return False
        # Red SESSIZ olamaz: sebep sayiyla uyari defterine dusmeli.
        if not any("KORUNUM TUTMADI" in u for u in mod._BEYAN_UYARISI):
            return False

        # --- 1b: AYRAC GURULTUSU YAKIN-KACISI (oran GERCEK olcumden)
        # 🔴 BU VAKA BIR REGRESYONU CIVILER: ilk yazimda karsilastirma tam `>=` idi ve
        # KAYIPSIZ bir rotasyonu REDDEDIYORDU. Olculen gercek sapmalar (10 Eyl):
        # TUR-2 kutu -18.785 B / arsiv +18.737 B = oran 0,9974 (48 B EKSIK) · 9 Eyl
        # kutu -55.680 B / arsiv +55.761 B = oran 1,0015 (81 B FAZLA). Blok ayraclari
        # iki tarafta ayni sayilmaz ve fark ISARET DEGISTIRIR. Tolerans 1,0'a cekilirse
        # bu vaka KIRMIZI yanar (M11 o yonu olcer).
        # ⚠️ BUYUKLUK OLCEKLENDI, ORAN DEGIL: gercek TUR-2 tek basina %40'lik bir dusus
        # ve `_ciddi_dusus_var` esigini (%50) HIC gecmiyor — yani o tur beyana zaten
        # UGRAMIYOR. Beyan kolunu olcebilmek icin dusus ciddi esigin USTUNE tasindi
        # (60.000 -> 25.000 = %58), sapma orani OLCULEN degerde (0,9974) TUTULDU.
        _yaz_bayt(varis, 60000)
        _yaz_bayt(kaynak, 25000)               # kaynak_dusus = 35000 (ciddi: %58)
        _yaz_bayt(hedef_yedek, 700000)
        _yaz_bayt(hedef_canli, 700000 + 34909)  # hedef_artis = 34909 (oran 0,9974)
        _beyan_kur(mod, kok, {"kutu.md": {
            "tur": "tasima", "hedef": "arsiv.md",
            "gerekce": "gercek TUR-2 (test)"}})
        beklenen = sha(kaynak)
        if reddedildi_mi(mod, kaynak, varis):
            return False
        if sha(varis) != beklenen or len(mod._BEYAN_KULLANILDI) != 1:
            return False

        # --- 3: `hedef` alani YOK -> fail-closed RED
        _yaz_bayt(varis, 1000)
        _yaz_bayt(kaynak, 100)
        _yaz_bayt(hedef_canli, 5900)
        _beyan_kur(mod, kok, {"kutu.md": {
            "tur": "tasima", "gerekce": "hedefsiz (test)"}})
        korunan = sha(varis)
        if not reddedildi_mi(mod, kaynak, varis):
            return False
        if sha(varis) != korunan:
            return False

        # --- 4: hedef iki duzlemin BIRINDE yok -> OLCULEMEZ, RED
        _yaz_bayt(varis, 1000)
        _yaz_bayt(kaynak, 100)
        os.unlink(hedef_yedek)
        _beyan_kur(mod, kok, {"kutu.md": {
            "tur": "tasima", "hedef": "arsiv.md",
            "gerekce": "olculemez (test)"}})
        korunan = sha(varis)
        if not reddedildi_mi(mod, kaynak, varis):
            return False
        return sha(varis) == korunan
    finally:
        mod.DUSUS_BEYAN_YOLU = onceki_yol


def vaka_beyan_bozuk(mod, kok):
    """Beyan dosyasi BOZUKSA koruma TAM GUCTE kalir (bozuk beyan kapi ACMAZ)."""
    onceki_yol = mod.DUSUS_BEYAN_YOLU
    try:
        yol = os.path.join(kok, ".yedek-dusus-izin-bozuk.json")
        with open(yol, "w", encoding="utf-8") as f:
            f.write("{ bu gecerli json DEGIL")
        mod.DUSUS_BEYAN_YOLU = yol
        del mod._BEYAN_KULLANILDI[:]
        del mod._BEYAN_UYARISI[:]
        kaynak = os.path.join(kok, "bozuk-kaynak.json")
        yedek = os.path.join(kok, "bozuk-yedek.json")
        yaz_json(kaynak, 2)
        yaz_json(yedek, 40)
        once = sha(yedek)
        if not reddedildi_mi(mod, kaynak, yedek):
            return False
        return sha(yedek) == once and len(mod._BEYAN_UYARISI) >= 1
    finally:
        mod.DUSUS_BEYAN_YOLU = onceki_yol


def vaka_normal(mod, kok):
    kaynak = os.path.join(kok, "normal-kaynak.json")
    yedek = os.path.join(kok, "normal-yedek.json")
    yaz_json(yedek, 10)
    eski = sha(yedek)
    yaz_json(kaynak, 11)
    yeni = sha(kaynak)
    mod._drive_kopyala(kaynak, yedek)
    ilk_surum = glob.glob(os.path.join(kok, "normal-yedek.[0-9]*.json"))
    if sha(yedek) != yeni or len(ilk_surum) != 1 or sha(ilk_surum[0]) != eski:
        return False
    for sayi in range(12, 36):
        yaz_json(kaynak, sayi)
        mod._drive_kopyala(kaynak, yedek)
    surumler = glob.glob(os.path.join(kok, "normal-yedek.[0-9]*.json"))
    return len(surumler) == mod.SURUM_SAKLA == 20


def tek_vaka(modul_yolu, vaka):
    mod = modul_yukle(modul_yolu)
    with tempfile.TemporaryDirectory(prefix="pruvo-yedek-koruma-") as kok:
        sonuc = {"sifir": vaka_sifir, "sifir-yeni": vaka_sifir_yeni,
                 "ani": vaka_ani, "karantina": vaka_karantina,
                 "beyan": vaka_beyan, "beyan-tasima": vaka_beyan_tasima,
                 "beyan-bozuk": vaka_beyan_bozuk,
                 "normal": vaka_normal}[vaka](mod, kok)
    print("VAKA=%s RC=%d" % (vaka, 0 if sonuc else 1))
    return 0 if sonuc else 1


def mutant_yaz(kok, ad, eski, yeni):
    with open(KANONIK, "r", encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(eski) != 1:
        raise RuntimeError("mutasyon ankraji tekil degil: %s" % ad)
    yol = os.path.join(kok, ad + ".py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(eski, yeni, 1))
    return yol


def tam_batarya():
    mod = modul_yukle(KANONIK)
    with tempfile.TemporaryDirectory(prefix="pruvo-yedek-koruma-") as kok:
        davranislar = [vaka_sifir(mod, kok), vaka_sifir_yeni(mod, kok),
                       vaka_ani(mod, kok), vaka_karantina(mod, kok),
                       vaka_beyan(mod, kok), vaka_beyan_tasima(mod, kok),
                       vaka_beyan_bozuk(mod, kok), vaka_normal(mod, kok)]
        mutant_sifir = mutant_yaz(
            kok, "mutant-sifir",
            "    _yedek_korumasi(kaynak, varis)\n    if os.path.isfile",
            "    pass  # MUTANT: koruma cagrisi olduruldu\n    if os.path.isfile")
        mutant_ani = mutant_yaz(
            kok, "mutant-ani",
            "return eski > 0 and yeni < eski * ANI_DUSUS_ESIGI",
            "return False")
        # Onarimin TERS yonu: sifir kolu yeniden KOSULSUZ redde donerse mesru bos nobetci
        # dosyasi yine tum kosumu dusurur -> `sifir-yeni` vakasi KIRMIZI yanmali.
        mutant_sifir_kosulsuz = mutant_yaz(
            kok, "mutant-sifir-kosulsuz",
            "        if os.path.isfile(varis) and os.path.getsize(varis) > 0:",
            "        if True:  # MUTANT: kosulsuz redde donus")
        # Karantinanin IKI yonu ayri ayri oldurulur:
        #  M4 — atlama SESSIZ kalirsa ("yedek alindi" yalan olur) KIRMIZI yanmali;
        #  M5 — karantina istisnayi yeniden atarsa (kosum yine oluyor) KIRMIZI yanmali.
        mutant_sessiz = mutant_yaz(
            kok, "mutant-karantina-sessiz",
            "        _KORUMA_KARANTINA.append((varis, str(e)))",
            "        pass  # MUTANT: atlama sessiz kaldi")
        # 🔴 CAPA KOMSUYA DEGIL FONKSIYONUN KENDI GOVDESINE BAGLI (27 Agu 2026,
        # K308 turunda OLCULDU): eski capa `"        return False\n\n\ndef
        # _kopyala_gerekliyse"` idi — yani "atlama kolunun HEMEN ARDINDAN gelen
        # fonksiyon" varsayimina. 26 Agu'da araya `karantina_etiketi()` girince
        # capa 1 -> 0 esleseme dustu, `mutant_yaz` RuntimeError atti ve TUM
        # batarya (7 vaka + 12 mutant) o gunden beri HIC KOSMADI: rc=1, ama
        # sebep "koruma bozuldu" degil "capa bayat"ti. Bir mutant capasi, test
        # ettigi kolun KOMSULUGUNU olcmemelidir
        # ([[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]] ·
        #  [[capa-cokmesi-arkasindaki-capalari-gizler]]).
        mutant_yeniden_at = mutant_yaz(
            kok, "mutant-karantina-yeniden-at",
            "    except YedekKorumaHatasi as e:\n"
            "        _KORUMA_KARANTINA.append((varis, str(e)))",
            "    except YedekKorumaHatasi as e:\n"
            "        raise  # MUTANT: kosum yine oluyor\n"
            "        _KORUMA_KARANTINA.append((varis, str(e)))")
        # Beyanin UC yonu ayri ayri oldurulur:
        #  M6 — beyan blanket olursa (her cagriya EVET) tur/boyut sarti olur, vaka KIRMIZI;
        #  M7 — "surekli" tavani kalkarsa 10 MB'lik dosya rolling ilan edilebilirdi, KIRMIZI;
        #  M8 — beyanla gecen dusus KAYDEDILMEZSE sessiz arka kapi olur, KIRMIZI.
        mutant_beyan_blanket = mutant_yaz(
            kok, "mutant-beyan-blanket",
            "    kayit = beyanlar.get(os.path.basename(kaynak))",
            "    return (True, 'tek-seferlik', 'MUTANT: blanket beyan')\n"
            "    kayit = beyanlar.get(os.path.basename(kaynak))")
        mutant_beyan_tavansiz = mutant_yaz(
            kok, "mutant-beyan-tavansiz",
            "        if isinstance(tavan, int) and kaynak_boyut <= tavan:",
            "        if True:  # MUTANT: surekli tavani kalkti")
        mutant_beyan_sessiz = mutant_yaz(
            kok, "mutant-beyan-sessiz",
            "        _BEYAN_KULLANILDI.append((os.path.basename(kaynak), tur, gerekce))",
            "        pass  # MUTANT: beyan kullanimi kaydedilmedi")
        # `tasima` turunun IKI oldurucu yonu (10 Eyl):
        #  M9  — KORUNUM karsilastirmasi kalkarsa tur BLANKET muafiyete doner: silinen
        #        icerik de "tasindi" sayilir, yani turun VARLIK SEBEBI olur. KIRMIZI.
        #  M10 — fail-closed yon: hedef OLCULEMEDIGINDE (iki duzlemden biri yok / `hedef`
        #        alani yok) True donerse, olcum yoklugu MUAFIYETE cevrilir. KIRMIZI.
        # 🔴 Capalar `_tasima_korunumu`nun KENDI govdesindedir, komsusunda degil.
        mutant_tasima_blanket = mutant_yaz(
            kok, "mutant-tasima-blanket",
            "    if hedef_artis < esik:",
            "    if False:  # MUTANT: korunum karsilastirmasi kalkti")
        mutant_tasima_olcumsuz = mutant_yaz(
            kok, "mutant-tasima-olcumsuz",
            '        return (False, "hedef adi YOK/gecersiz -> olculemez")',
            '        return (True, "MUTANT: olcum yoklugu muafiyete cevrildi")')
        #  M11 — TOLERANSIN TERS YONU: oran 1.0'a cekilirse ayrac gurultusu yuzunden
        #        KAYIPSIZ rotasyonlar reddedilir (10 Eyl TUR-2 olculdu: 48 B eksik).
        #        Bu yon olculmezse tolerans sessizce daralir ve yedek bayatlar.
        mutant_tasima_tolerans = mutant_yaz(
            kok, "mutant-tasima-tolerans",
            "TASIMA_KORUNUM_ORANI = 0.98",
            "TASIMA_KORUNUM_ORANI = 1.0  # MUTANT: ayrac toleransi kalkti")
        komut = [sys.executable, os.path.abspath(__file__), "--modul"]
        sifir = subprocess.run(komut + [mutant_sifir, "--vaka", "sifir"],
                               capture_output=True, text=True)
        ani = subprocess.run(komut + [mutant_ani, "--vaka", "ani"],
                             capture_output=True, text=True)
        kosulsuz = subprocess.run(komut + [mutant_sifir_kosulsuz, "--vaka", "sifir-yeni"],
                                  capture_output=True, text=True)
        sessiz = subprocess.run(komut + [mutant_sessiz, "--vaka", "karantina"],
                                capture_output=True, text=True)
        yeniden = subprocess.run(komut + [mutant_yeniden_at, "--vaka", "karantina"],
                                 capture_output=True, text=True)
        blanket = subprocess.run(komut + [mutant_beyan_blanket, "--vaka", "beyan"],
                                 capture_output=True, text=True)
        tavansiz = subprocess.run(komut + [mutant_beyan_tavansiz, "--vaka", "beyan"],
                                  capture_output=True, text=True)
        beyan_sessiz = subprocess.run(komut + [mutant_beyan_sessiz, "--vaka", "beyan"],
                                      capture_output=True, text=True)
        tasima_blanket = subprocess.run(
            komut + [mutant_tasima_blanket, "--vaka", "beyan-tasima"],
            capture_output=True, text=True)
        tasima_olcumsuz = subprocess.run(
            komut + [mutant_tasima_olcumsuz, "--vaka", "beyan-tasima"],
            capture_output=True, text=True)
        tasima_tolerans = subprocess.run(
            komut + [mutant_tasima_tolerans, "--vaka", "beyan-tasima"],
            capture_output=True, text=True)
    mutantlar = [sifir.returncode != 0, ani.returncode != 0, kosulsuz.returncode != 0,
                 sessiz.returncode != 0, yeniden.returncode != 0,
                 blanket.returncode != 0, tavansiz.returncode != 0,
                 beyan_sessiz.returncode != 0,
                 tasima_blanket.returncode != 0, tasima_olcumsuz.returncode != 0,
                 tasima_tolerans.returncode != 0]
    print("KORUMA_TEST=%d" % sum(1 for sonuc in davranislar if sonuc))
    print("MUTASYON_KIRMIZI=%d" % sum(1 for sonuc in mutantlar if sonuc))
    print("MUTASYON_RC=%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d" % (
        sifir.returncode, ani.returncode, kosulsuz.returncode, sessiz.returncode,
        yeniden.returncode, blanket.returncode, tavansiz.returncode,
        beyan_sessiz.returncode, tasima_blanket.returncode,
        tasima_olcumsuz.returncode, tasima_tolerans.returncode))
    print("SURUM_TAVANI=%d" % mod.SURUM_SAKLA)
    return 0 if all(davranislar) and all(mutantlar) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modul")
    ap.add_argument("--vaka", choices=("sifir", "sifir-yeni", "ani", "karantina",
                                       "beyan", "beyan-tasima", "beyan-bozuk",
                                       "normal"))
    a = ap.parse_args()
    if a.modul or a.vaka:
        if not a.modul or not a.vaka:
            return 2
        return tek_vaka(a.modul, a.vaka)
    return tam_batarya()


if __name__ == "__main__":
    sys.exit(main())
