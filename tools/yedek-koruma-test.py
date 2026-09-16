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


# ---------------------------------------------------------------- K338 (16 Eyl)
# 28 Agu 2026'da CANLI beyan dosyasinda duran BLANKET kayit. Fikstur icinde
# KANIT olarak durur: yeni mekanizmanin daralttigi seyin ne oldugu, iddia degil
# VERIDIR. Bu hal `beyan-yol` vakasinda AYNI fiksture uygulanir ve KraL kaynaginin
# dususunu YESIL gecirdigi OLCULUR; dar hal ayni dusus icin KIRMIZI verir.
K338_BLANKET_28AGU = {"mimar-icra-kapisi.py": {
    "tur": "surekli", "azami_bayt": 4096,
    "gerekce": "28 Agu 2026 blanket kaydinin fikstur kopyasi (tarihsel kanit)"}}


def _k338_ev_kur(kok, ev, rel, kaynak_bayt, yedek_bayt):
    """<kok>/<ev>/<rel> kaynagi + yanina kanonik yedegi kurar. Doner: (kaynak, yedek)."""
    kaynak = os.path.join(kok, ev, *rel.split("/"))
    os.makedirs(os.path.dirname(kaynak), exist_ok=True)
    _yaz_bayt(kaynak, kaynak_bayt)
    yedek = os.path.join(kok, "yedek", ev.replace("/", "_") + "__"
                         + rel.replace("/", "_"))
    os.makedirs(os.path.dirname(yedek), exist_ok=True)
    _yaz_bayt(yedek, yedek_bayt)
    return kaynak, yedek


def vaka_beyan_yol(mod, kok):
    """K338 ①③④ — beyan anahtari YOL ekseni tasiyor mu?

    Ayni ADI tasiyan iki ROL ayni fiksturde durur:
      KAYNAK  <ev>/pruvo/tools/mimar-icra-kapisi.py      (106820 -> 2000 B = ARIZA)
      SHIM    <ev>/pruvo-{bot,pazarlama,jenerator,advisor,hasat}/.claude/...
                                                        (2658..2680 B = MESRU)
    Olculen dort eksen:
      1. TARIHSEL KANIT — 28 Agu'nun AD eksenli blanket beyani KAYNAK dususunu
         YESIL geciriyor (delik GERCEKTI, iddia degil).
      2. DAR BEYAN — ayni dusus yol ekseninde REDDEDILIR (③ MUTANT sarti).
      3. KONTROL — bes shim dar beyanla YESIL kalmaya devam eder (④).
      4. OZGULLUK — genis (ad) ve dar (yol) kayit YAN YANA dururken DAR olan kazanir;
         yoksa daraltma, eski kaydi silmeyi zorunlu kilardi ve gecis yolu olmazdi.
    """
    onceki_yol = mod.DUSUS_BEYAN_YOLU
    try:
        kaynak, kaynak_yedek = _k338_ev_kur(
            kok, "pruvo", "tools/mimar-icra-kapisi.py", 2000, 106820)
        shimler = []
        for ev, bayt in (("pruvo-bot", 2658), ("pruvo-pazarlama", 2680),
                         ("pruvo-jenerator", 2678), ("pruvo-advisor", 2670),
                         ("pruvo-hasat", 2666)):
            shimler.append(_k338_ev_kur(
                kok, ev, ".claude/mimar-icra-kapisi.py", bayt, 56617))

        # --- 1: TARIHSEL KANIT. Blanket beyan KAYNAGI da kapsiyor -> dusus GECER.
        _beyan_kur(mod, kok, K338_BLANKET_28AGU)
        if reddedildi_mi(mod, kaynak, kaynak_yedek):
            return False                      # delik yoksa bu vaka bos yere kosuyor
        if len(mod._BEYAN_KULLANILDI) != 1:
            return False

        # --- 2: DAR BEYAN. Ayni dusus, yol eksenli kayitlarla REDDEDILIR.
        dar = {}
        for ev in ("pruvo-bot", "pruvo-pazarlama", "pruvo-jenerator",
                   "pruvo-advisor", "pruvo-hasat"):
            dar[ev + "/.claude/mimar-icra-kapisi.py"] = {
                "tur": "surekli", "azami_bayt": 4096, "gerekce": "shim (test)"}
        _yaz_bayt(kaynak_yedek, 106820)       # fikstur tabani geri kurulur
        _beyan_kur(mod, kok, dar)
        korunan = sha(kaynak_yedek)
        if not reddedildi_mi(mod, kaynak, kaynak_yedek):
            return False
        if sha(kaynak_yedek) != korunan:      # kanonik yedek DEGISMEMELI
            return False
        if len(mod._BEYAN_KULLANILDI) != 0:   # gecmeyen beyan KULLANILDI sayilamaz
            return False

        # --- 3: KONTROL. Bes shim AYNI dar beyanla YESIL kalir.
        for shim_kaynak, shim_yedek in shimler:
            del mod._BEYAN_KULLANILDI[:]
            beklenen = sha(shim_kaynak)
            if reddedildi_mi(mod, shim_kaynak, shim_yedek):
                return False
            if sha(shim_yedek) != beklenen:
                return False
            if len(mod._BEYAN_KULLANILDI) != 1:
                return False
            anahtar, tur, _ = mod._BEYAN_KULLANILDI[0]
            # Deftere ESLESEN ANAHTAR yazilir; ad yazilsaydi hangi beyanin isirdigi
            # okunamaz, daraltma sessizce geri alinabilirdi.
            if not anahtar.endswith("/.claude/mimar-icra-kapisi.py"):
                return False
            if tur != "surekli":
                return False

        # --- 4: OZGULLUK. Genis + dar YAN YANA; DAR kazanir (kaynak yine REDDEDILIR).
        karisik = dict(dar)
        karisik.update(K338_BLANKET_28AGU)
        karisik["pruvo/tools/mimar-icra-kapisi.py"] = {
            "tur": "tek-seferlik", "kaynak_bayt": 999999,
            "gerekce": "kaynak icin DAR kayit — eslesmeyen boyut (test)"}
        _yaz_bayt(kaynak_yedek, 106820)
        _beyan_kur(mod, kok, karisik)
        korunan = sha(kaynak_yedek)
        if not reddedildi_mi(mod, kaynak, kaynak_yedek):
            return False
        return sha(kaynak_yedek) == korunan
    finally:
        mod.DUSUS_BEYAN_YOLU = onceki_yol


def vaka_beyan_kume(mod, kok):
    """K338 ② — `tek-seferlik` KUME ve ARALIK kabul ediyor, ama blanket'e DONMUYOR.

      1. KUME: ilan edilen bes boyuttan HER BIRI gecer.
      2. KUME: kumede OLMAYAN boyut REDDEDILIR (kume blanket degil).
      3. ARALIK: sinirlar DAHIL gecer, disi REDDEDILIR.
      4. FAIL-CLOSED: tek uclu aralik (acik uclu) ve bool ilan ESLESMEZ.
    """
    onceki_yol = mod.DUSUS_BEYAN_YOLU
    try:
        kaynak, yedek = _k338_ev_kur(kok, "kume-ev", "shim.py", 2658, 56617)
        kume = [2658, 2666, 2670, 2678, 2680]
        _beyan_kur(mod, kok, {"kume-ev/shim.py": {
            "tur": "tek-seferlik", "kaynak_bayt": kume,
            "gerekce": "bes evin shim boyutu (test)"}})
        for bayt in kume:
            _yaz_bayt(kaynak, bayt)
            _yaz_bayt(yedek, 56617)
            del mod._BEYAN_KULLANILDI[:]
            beklenen = sha(kaynak)
            if reddedildi_mi(mod, kaynak, yedek):
                return False
            if sha(yedek) != beklenen or len(mod._BEYAN_KULLANILDI) != 1:
                return False
        # kumede OLMAYAN boyut -> RED
        _yaz_bayt(kaynak, 2659)
        _yaz_bayt(yedek, 56617)
        korunan = sha(yedek)
        if not reddedildi_mi(mod, kaynak, yedek):
            return False
        if sha(yedek) != korunan:
            return False

        # --- ARALIK: 2650..2690 dahil
        _beyan_kur(mod, kok, {"kume-ev/shim.py": {
            "tur": "tek-seferlik", "kaynak_bayt": {"en_az": 2650, "en_cok": 2690},
            "gerekce": "shim araligi (test)"}})
        for bayt, gecmeli in ((2650, True), (2690, True), (2649, False),
                              (2691, False)):
            _yaz_bayt(kaynak, bayt)
            _yaz_bayt(yedek, 56617)
            red = reddedildi_mi(mod, kaynak, yedek)
            if red == gecmeli:
                return False

        # --- FAIL-CLOSED: acik uclu aralik + bool ilan ESLESMEZ
        for bozuk in ({"en_az": 2650}, {"en_cok": 2690},
                      {"en_az": 2690, "en_cok": 2650}, True, "2658"):
            _beyan_kur(mod, kok, {"kume-ev/shim.py": {
                "tur": "tek-seferlik", "kaynak_bayt": bozuk,
                "gerekce": "fail-closed (test)"}})
            _yaz_bayt(kaynak, 2658)
            _yaz_bayt(yedek, 56617)
            if not reddedildi_mi(mod, kaynak, yedek):
                return False
        return True
    finally:
        mod.DUSUS_BEYAN_YOLU = onceki_yol


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
                 "beyan-yol": vaka_beyan_yol, "beyan-kume": vaka_beyan_kume,
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
                       vaka_beyan_bozuk(mod, kok), vaka_beyan_yol(mod, kok),
                       vaka_beyan_kume(mod, kok), vaka_normal(mod, kok)]
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
        # 🔴 CAPA K338 ONARIMIYLA TAZELENDI (16 Eyl 2026): eski capa
        # `kayit = beyanlar.get(os.path.basename(kaynak))` idi — o satir AD ekseninin
        # KENDISIYDI ve yol ekseni gelince kayboldu. Capa artik cozucu CAGRISINA bagli.
        mutant_beyan_blanket = mutant_yaz(
            kok, "mutant-beyan-blanket",
            "    _anahtar, kayit = _beyan_anahtari_sec(kaynak, beyanlar)",
            "    return (True, 'tek-seferlik', 'MUTANT: blanket beyan')\n"
            "    _anahtar, kayit = _beyan_anahtari_sec(kaynak, beyanlar)")
        mutant_beyan_tavansiz = mutant_yaz(
            kok, "mutant-beyan-tavansiz",
            "        if isinstance(tavan, int) and kaynak_boyut <= tavan:",
            "        if True:  # MUTANT: surekli tavani kalkti")
        mutant_beyan_sessiz = mutant_yaz(
            kok, "mutant-beyan-sessiz",
            "        _BEYAN_KULLANILDI.append(\n"
            "            (anahtar or os.path.basename(kaynak), tur, gerekce))",
            "        pass  # MUTANT: beyan kullanimi kaydedilmedi")
        # K338'in UC oldurucu yonu (16 Eyl 2026):
        #  M12 — cozucu AD eksenine geri donerse KAYNAK ile SHIM yeniden ayrilamaz
        #        ve blanket beyan KraL kaynagini gene sessizce muaf yapar -> KIRMIZI.
        #  M13 — OZGULLUK sirasi bozulursa (dar kayit yerine GENIS kayit kazanir) ayni
        #        delik ACIK kalir, ustelik dar kayit yazilmis gibi GORUNUR -> KIRMIZI.
        #  M14 — `tek-seferlik` kume kolu blanket'e donerse (her boyut gecer) tam
        #        esitlik sarti olur; kume, muafiyetin genis kapisi olur -> KIRMIZI.
        mutant_beyan_yol_adi = mutant_yaz(
            kok, "mutant-beyan-yol-adi",
            "    parcalar = os.path.abspath(kaynak).replace(os.sep, \"/\")"
            ".strip(\"/\").split(\"/\")",
            "    parcalar = [os.path.basename(kaynak)]  # MUTANT: AD eksenine donus")
        mutant_beyan_ozgullik = mutant_yaz(
            kok, "mutant-beyan-ozgullik",
            "        if en_iyi is None or derinlik > en_iyi[0]:",
            "        if en_iyi is None or derinlik < en_iyi[0]:  # MUTANT: genis kazanir")
        mutant_tek_seferlik_kume = mutant_yaz(
            kok, "mutant-tek-seferlik-kume",
            "        return any(_sayi(x) and x == boyut for x in ilan)",
            "        return True  # MUTANT: kume blanket'e dondu")
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
        yol_adi = subprocess.run(
            komut + [mutant_beyan_yol_adi, "--vaka", "beyan-yol"],
            capture_output=True, text=True)
        ozgullik = subprocess.run(
            komut + [mutant_beyan_ozgullik, "--vaka", "beyan-yol"],
            capture_output=True, text=True)
        kume_blanket = subprocess.run(
            komut + [mutant_tek_seferlik_kume, "--vaka", "beyan-kume"],
            capture_output=True, text=True)
        # 🔴 KONTROL KOLU (mutant harness'i gercekten AYIRIYOR mu): K338 mutantlari
        # KENDI vakalarini oldurmeli ama MESRU `beyan` vakasini oldurmemelidir. Bu
        # kol olmasaydi "her mutant her vakayi kirmizi yakiyor" hali de YESIL gorunurdu.
        kontrol_yol = subprocess.run(
            komut + [mutant_beyan_yol_adi, "--vaka", "beyan"],
            capture_output=True, text=True)
    mutantlar = [sifir.returncode != 0, ani.returncode != 0, kosulsuz.returncode != 0,
                 sessiz.returncode != 0, yeniden.returncode != 0,
                 blanket.returncode != 0, tavansiz.returncode != 0,
                 beyan_sessiz.returncode != 0,
                 tasima_blanket.returncode != 0, tasima_olcumsuz.returncode != 0,
                 tasima_tolerans.returncode != 0,
                 yol_adi.returncode != 0, ozgullik.returncode != 0,
                 kume_blanket.returncode != 0]
    print("KORUMA_TEST=%d" % sum(1 for sonuc in davranislar if sonuc))
    print("MUTASYON_KIRMIZI=%d" % sum(1 for sonuc in mutantlar if sonuc))
    print("MUTASYON_RC=%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d" % (
        sifir.returncode, ani.returncode, kosulsuz.returncode, sessiz.returncode,
        yeniden.returncode, blanket.returncode, tavansiz.returncode,
        beyan_sessiz.returncode, tasima_blanket.returncode,
        tasima_olcumsuz.returncode, tasima_tolerans.returncode,
        yol_adi.returncode, ozgullik.returncode, kume_blanket.returncode))
    print("K338_KONTROL_RC=%d (0 beklenir: mutant MESRU vakayi oldurmuyor)"
          % kontrol_yol.returncode)
    davranislar.append(kontrol_yol.returncode == 0)
    print("SURUM_TAVANI=%d" % mod.SURUM_SAKLA)
    return 0 if all(davranislar) and all(mutantlar) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modul")
    ap.add_argument("--vaka", choices=("sifir", "sifir-yeni", "ani", "karantina",
                                       "beyan", "beyan-tasima", "beyan-bozuk",
                                       "beyan-yol", "beyan-kume", "normal"))
    a = ap.parse_args()
    if a.modul or a.vaka:
        if not a.modul or not a.vaka:
            return 2
        return tek_vaka(a.modul, a.vaka)
    return tam_batarya()


if __name__ == "__main__":
    sys.exit(main())
